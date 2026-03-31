import os
import re
import json
import time
from typing import Any, Dict, List, Optional
from langgraph.graph import StateGraph, END

from src.agents.orchestration.utils.state import AgentState
from src.agents.llm.client import client
from src.agents.tools.notion import notion_client
from src.agents.tools.github import github_client
from src.db.tools.github_store import github_store
from src.db.observability.checkpointer import PostgresCheckpointer
from src.command_center.backend.slack.client import slack_queue

class GroomingState(AgentState):
    """State for the GitHub Grooming workflow."""
    notion_page_id: str
    prd_title: str
    prd_markdown: str
    repo_name: str
    repository_id: str
    github_repo_id: Optional[int]
    github_project_id: Optional[str]
    github_project_url: Optional[str]
    milestones: List[Dict[str, Any]]
    issues: List[Dict[str, Any]]
    project_fields: List[Dict[str, Any]]
    rossini_evaluation: str
    riccado_evaluation: str
    synthesized_actions: Dict[str, Any]
    discrepancies: List[str]
    slack_channel: str
    thread_ts: Optional[str]
    last_error: str
    creation_results: List[str]

class GroomingWorkflow:
    def __init__(self, agent):
        self.agent = agent
        self.name = agent.name
        self.model_config = agent.model_config
        self.rossini_personality = self._load_personality("rossini")
        self.riccado_personality = self._load_personality("riccado")

    def _load_personality(self, name: str) -> str:
        try:
            soul_path = os.path.join(os.getcwd(), f"src/agents/souls/{name}.md")
            if os.path.exists(soul_path):
                with open(soul_path, "r") as f:
                    content = f.read()
                persona_match = re.search(r"## PERSONA & TONE(.*?)(##|$)", content, re.DOTALL)
                if persona_match:
                    return persona_match.group(1).strip()
        except Exception:
            pass
        return f"A professional persona for {name.capitalize()}."

    def load_context(self, state: GroomingState) -> GroomingState:
        print(f"[{self.name}] Grooming Node: load_context")
        page_id = state.get("notion_page_id")
        task = state.get("task", "")
        
        # 1. Try UUID extraction
        if not page_id:
            uuid_match = re.search(r"([a-f0-9]{32})", task)
            if uuid_match:
                page_id = uuid_match.group(1)

        # 2. Try Title extraction and Notion Search
        if not page_id:
            title_match = re.search(r"(?:groom|review|prd)\s+(?:for|on|named|titled)?\s*[\"']?([^\"'?.]+)[\"']?", task, re.IGNORECASE)
            if title_match:
                target_name = title_match.group(1).strip()
                print(f"[{self.name}] Searching Notion for PRD title: '{target_name}'")
                results = notion_client.search(query=target_name, agent_name=self.name)
                if results:
                    # Only take it if it's mapped, otherwise we'll try guessing
                    temp_id = results[0]["id"]
                    if github_store.get_repo_for_prd(temp_id):
                        page_id = temp_id
                        print(f"[{self.name}] Found mapped page '{results[0].get('title')}' with ID {page_id}")
                    else:
                        print(f"[{self.name}] Search found '{results[0].get('title')}' but it's not mapped. Checking for alternatives...")

        # 3. Guessing/Mapping logic: Try to find a mapped PRD for the relevant repo
        if not page_id:
            repos = github_store.get_accessible_repos(self.name)
            repo_name = None
            
            # Identify the repo: either from task or if only one exists
            task_lower = task.lower()
            for r in repos:
                if r["repo_name"].lower() in task_lower:
                    repo_name = r["repo_name"]
                    break
            
            if not repo_name and len(repos) == 1:
                repo_name = repos[0]["repo_name"]

            if repo_name:
                print(f"[{self.name}] Filtering mappings for repo '{repo_name}'...")
                all_mappings = github_store.get_all_prd_mappings()
                repo_mappings = [m for m in all_mappings if m["repo_name"] == repo_name]
                
                if len(repo_mappings) == 1:
                    page_id = repo_mappings[0]["notion_page_id"]
                    print(f"[{self.name}] Resolved mapping: '{repo_mappings[0]['prd_title']}' ({page_id}) for repo '{repo_name}'")
                elif len(repo_mappings) > 1:
                    # Check history for index-based selection
                    history = state.get("history", [])
                    task_lower_msg = state.get("task", "").lower()
                    
                    last_bot_msg = None
                    for msg in reversed(history):
                        if msg.get("role") == "assistant" and f"found multiple PRDs for repo '{repo_name}'" in msg.get("content"):
                            last_bot_msg = msg.get("content")
                            break
                    
                    if last_bot_msg and len(task_lower_msg.split()) < 6:
                        index = None
                        if re.search(r"\b1\b|first", task_lower_msg): index = 0
                        elif re.search(r"\b2\b|second", task_lower_msg): index = 1
                        elif re.search(r"\b3\b|third", task_lower_msg): index = 2
                        
                        if index is not None and index < len(repo_mappings):
                            page_id = repo_mappings[index]["notion_page_id"]
                            print(f"[{self.name}] Contextual Selection: {repo_mappings[index]['prd_title']} (Index {index})")
                    
                    if not page_id:
                        options = [f"{i+1}. '{m['prd_title']}' (ID: {m['notion_page_id'][:8]})" for i, m in enumerate(repo_mappings)]
                        titles_msg = "\n".join(options)
                        return {"last_error": f"I found multiple PRDs for repo '{repo_name}':\n{titles_msg}\nWhich one should I groom? (Reply with the number)"}

        if not page_id:
            return {"last_error": "Could not determine which Notion PRD to groom. Please provide a Title, URL, or Page ID."}

        # 4. Load PRD
        try:
            page_data = notion_client.read_page(page_id, agent_name=self.name)
            blocks = page_data.get("blocks", [])
            prd_title = page_data.get("page_properties", {}).get("title", "Untitled PRD")
            prd_markdown = "\n".join([b.get("text", "") if isinstance(b, dict) else str(b) for b in blocks])
        except Exception as e:
            return {"last_error": f"Failed to read PRD with ID {page_id}: {e}"}

        # 5. Get final mapping data
        cached_data = github_store.get_repo_for_prd(page_id)
        if not cached_data:
            return {"last_error": f"PRD '{prd_title}' is not yet mapped to a GitHub repository. Please run Milestone Creation first."}

        return {
            "notion_page_id": page_id,
            "prd_title": prd_title,
            "prd_markdown": prd_markdown,
            "repo_name": cached_data.get("repo_name"),
            "github_repo_id": cached_data.get("github_repo_id"),
            "github_project_id": cached_data.get("github_project_id")
        }

    def fetch_github_state(self, state: GroomingState) -> GroomingState:
        if state.get("last_error"): return {}
        print(f"[{self.name}] Grooming Node: fetch_github_state")
        repo_name = state.get("repo_name")
        
        try:
            milestones = github_client.list_milestones(repo_name, agent_name=self.name, state="all")
            issues = github_client.list_issues(repo_name, agent_name=self.name, state="open")
        except Exception as e:
            return {"last_error": f"Failed to fetch GitHub state: {e}"}

        # Also fetch comments for each open issue to provide context for debate
        # (PRs are already filtered out by github_client.list_issues)
        
        for issue in issues:
            try:
                num = issue.get("number")
                url = f"https://api.github.com/repos/{repo_name}/issues/{num}/comments"
                # Doing a direct call here for simplicity
                res = github_client.session.get(url, headers=github_client._get_headers(self.name))
                if res.status_code == 200:
                    comments = res.json()
                    issue["comments"] = [{"user": c["user"]["login"], "body": c["body"]} for c in comments]
                else:
                    issue["comments"] = []
            except Exception:
                issue["comments"] = []

        project_fields = []
        proj_id = state.get("github_project_id")
        if proj_id:
            try:
                project_fields = github_client.get_project_v2_fields(proj_id, agent_name=self.name)
            except Exception as e:
                print(f"[{self.name}] Could not fetch Project V2 fields: {e}")

        return {
            "milestones": list(milestones),
            "issues": list(issues),
            "project_fields": project_fields
        }

    def rossini_review(self, state: GroomingState) -> GroomingState:
        if state.get("last_error"): return {}
        print(f"[{self.name}] Grooming Node: rossini_review")
        
        prd = state.get("prd_markdown", "")
        issues = state.get("issues", [])
        milestones = state.get("milestones", [])
        
        prompt = f"""
{self.rossini_personality}

Task: As the Product Director, review the current GitHub Milestones and Issues against the Notion PRD from a PRODUCT perspective.
1. **Milestones**: Ensure they cover the PRD. Each Milestone MUST follow the classic User Story format: "As a ___, In order to do ABC, I wanna have XYZ." They must also include clear Acceptance Criteria.
2. **Issues/Tickets**: Focus on the most business-impactful items. Ensure each issue has appropriate Labels, Type, and Priority (P0, P1, P2).
3. **Product Logic**: Are issue relationships (blocking/blocked) logical from a product value perspective?
4. **Confidence Level**: For the current state of each Milestone and Issue, explicitly state your **Confidence Level (0-100%)**. Explain why.

PRD Summary:
{prd[:5000]}

Existing Milestones (Note the 'number' for each):
{json.dumps([{"number": m.get("number"), "title": m.get("title"), "description": m.get("description")} for m in milestones], indent=2)}

Existing Issues (with recent comments):
{json.dumps([{"number": i.get("number"), "title": i.get("title"), "milestone": i.get("milestone_title"), "comments": i.get("comments", [])[-3:]} for i in issues], indent=2)}

Output your product evaluation in clear terms. Mention specific Issue and Milestone numbers. Ensure missing User Story formats, Acceptance Criteria, or low confidence (why) are called out.
"""
        res, _ = client.complete(prompt, self.agent.get_model_config(state), agent_name="Rossini")
        return {"rossini_evaluation": res}

    def riccado_review(self, state: GroomingState) -> GroomingState:
        if state.get("last_error"): return {}
        print(f"[{self.name}] Grooming Node: riccado_review")
        
        prd = state.get("prd_markdown", "")
        issues = state.get("issues", [])
        milestones = state.get("milestones", [])
        
        prompt = f"""
{self.riccado_personality}

Task: As the Principal Data Engineer / Tech Lead, review the current GitHub Milestones and Issues from an ENGINEERING perspective.
1. **Technical Depth**: For each issue, provide or refine solid **Acceptance Criteria** and define a clear **Definition of Done (DoD)**.
2. **Engineering Excellence**: Evaluate scalability, maintenance effort, potential tech debt, and adherence to best practices.
3. **Pragmatism**: While maintaining high standards, prioritize **business outcomes** over purely engineering-perfect considerations.
4. **Technical Tasks**: Ensure all technical tasks (including debt/refactoring) are represented. Identify technical blockers.
5. **Estimation**: Estimate efforts/size for each open issue (XS, S, M, L, XL).
6. **Confidence Level**: For the current state of each Milestone and Issue, explicitly state your **Confidence Level (0-100%)**. Explain why.

PRD Summary:
{prd[:5000]}

Existing Milestones (Note the 'number' for each):
{json.dumps([{"number": m.get("number"), "title": m.get("title"), "description": m.get("description")} for m in milestones], indent=2)}

Existing Issues (with recent comments):
{json.dumps([{"number": i.get("number"), "title": i.get("title"), "body": str(i.get("body"))[:200], "comments": i.get("comments", [])[-3:]} for i in issues], indent=2)}

Output your technical evaluation in your explosive, direct style. Mention specific Issue and Milestone numbers. Explicitly call for AC and DoD where missing, and state your confidence clearly.
"""
        res, _ = client.complete(prompt, self.agent.get_model_config(state), agent_name="Riccado")
        return {"riccado_evaluation": res}

    def synthesize(self, state: GroomingState) -> GroomingState:
        if state.get("last_error"): return {}
        print(f"[{self.name}] Grooming Node: synthesize")
        
        rossini = state.get("rossini_evaluation", "")
        riccado = state.get("riccado_evaluation", "")
        
        # Identify valid issue numbers to prevent hallucinations (e.g. PRs or wrong IDs)
        valid_issue_numbers = {i["number"] for i in state.get("issues", [])}
        
        prompt = f"""
Task: You are an impartial Orchestrator. Synthesize the findings of Dr. Rossini (Product) and Riccado (Tech).
Extract the AGREED UPON actions and any DISCREPANCIES that need debate.
Identify any duplicate Milestones or Issues that should be removed or closed.

**CRITICAL RULE: STATUS "READY"**:  
- An issue can ONLY be marked as `"status": "Ready"` if BOTH Dr. Rossini and Riccado have a **Confidence Level > 80%** for that issue.
- If either confidence is <= 80%, the status should be "In Progress" or "Needs Work".
- Capture and mention the confidence levels in the `new_comments` section.

**SAFETY RULE: IDENTIFIERS**:
- VALID ISSUE NUMBERS: {list(valid_issue_numbers)}
- VALID MILESTONE NUMBERS: {[m.get("number") for m in state.get("milestones", [])]}
- Ensure `items_to_remove` uses the correct numbers from these lists.

Rossini's Evaluation:
{rossini}

Riccado's Evaluation:
{riccado}

Output exactly in this JSON format:
{{
  "agreed_updates": [
    {{
      "issue_number": 12,
      "priority": "P1",
      "size": "M",
      "blocks": [13, 14],
      "blocked_by": [],
      "status": "Ready",
      "new_comments": ["Rossini (Confidence: 90%) & Riccado (Confidence: 85%) agreed: Size M, Priority P1. [AC/DoD details if any]"]
    }}
  ],
  "items_to_remove": [
    {{"type": "issue", "number": 99, "reason": "Duplicate of #12"}},
    {{"type": "milestone", "number": 5, "reason": "No longer relevant to PRD"}}
  ],
  "discrepancies": [
    {{
      "issue_number": 15,
      "debate_topic": "Rossini wants P0 (Conf: 95%), Riccado says XL and P2 (Conf: 40%). Riccado demands specific DoD.",
      "suggested_rossini_comment": "Riccado, we need this for launch. My confidence is 95% on the product value. Can we scope it down? - Rossini",
      "suggested_riccado_comment": "Rossini, my confidence is only 40% because the DB schema is unclear. We need a Definition of Done that includes zero-downtime verification. - Riccado"
    }}
  ]
}}
Ensure the output is ONLY valid JSON.
"""
        res, _ = client.complete(prompt, self.agent.get_model_config(state), agent_name=self.name)
        try:
            clean = re.sub(r"^```(?:json)?\s*", "", res.strip(), flags=re.MULTILINE)
            clean = re.sub(r"```\s*$", "", clean.strip(), flags=re.MULTILINE)
            data = json.loads(clean.strip())
            return {
                "synthesized_actions": data,
                "discrepancies": data.get("discrepancies", [])
            }
        except Exception as e:
            return {"last_error": f"Failed to parse synthesis JSON: {e}"}

    def debate_in_github(self, state: GroomingState) -> GroomingState:
        if state.get("last_error"): return {}
        print(f"[{self.name}] Grooming Node: debate_in_github")
        
        discrepancies = state.get("discrepancies", [])
        repo_name = state.get("repo_name")
        results = state.get("creation_results", [])
        
        if not discrepancies:
            print(f"[{self.name}] No discrepancies to debate.")
            return {}
            
        valid_issues = {i["number"] for i in state.get("issues", [])}
        
        for disc in discrepancies:
            issue_num = disc.get("issue_number")
            rossini_c = disc.get("suggested_rossini_comment")
            riccado_c = disc.get("suggested_riccado_comment")
            
            if issue_num not in valid_issues:
                print(f"[{self.name}] Skipping debate for invalid/PR issue number: {issue_num}")
                continue
                
            try:
                if issue_num and rossini_c:
                    print(f"[{self.name}] Posting Rossini comment on #{issue_num} in {repo_name}...")
                    github_client.create_issue_comment(repo_name, issue_num, rossini_c, agent_name="Rossini")
                    results.append(f"💬 Rossini commented on #{issue_num}")
                if issue_num and riccado_c:
                    print(f"[{self.name}] Posting Riccado comment on #{issue_num} in {repo_name}...")
                    github_client.create_issue_comment(repo_name, issue_num, riccado_c, agent_name="Riccado")
                    results.append(f"💬 Riccado commented on #{issue_num}")
            except Exception as e:
                print(f"[{self.name}] Tool Error in debate (Issue #{issue_num}, Repo: {repo_name}): {e}")
                return {"last_error": f"Failed to post debate comments (Issue #{issue_num}): {e}", "creation_results": results}
                
        return {
            "creation_results": results
        }

    def consolidate_and_refine(self, state: GroomingState) -> GroomingState:
        if state.get("last_error"): return {}
        print(f"[{self.name}] Grooming Node: consolidate_and_refine")
        valid_issues = {i["number"] for i in state.get("issues", [])}
        
        rossini_eval = state.get("rossini_evaluation", "")
        riccado_eval = state.get("riccado_evaluation", "")
        issues = state.get("issues", [])
        initial_actions = state.get("synthesized_actions", {})
        
        prompt = f"""
Task: You are the Final Consolidator. Review the initial evaluations, the debate comments, and decide on the FINAL actions.
Ensure that finalized issues include necessary Acceptance Criteria and Definition of Done as suggested by Riccado or Rossini.
Include any issues or milestones that should be removed/closed if they are redundant or irrelevant.

VALID ISSUE NUMBERS (ONLY TARGET THESE): {list(valid_issues)}
(Pull Requests are EXCLUDED, do not target them).

Existing Issues (with comments):
{json.dumps([{"number": i.get("number"), "title": i.get("title"), "comments": i.get("comments", [])} for i in issues], indent=2)}

Rossini's Evaluation: {rossini_eval}
Riccado's Evaluation: {riccado_eval}

Initial Synthesized Actions: {json.dumps(initial_actions, indent=2)}

Output exactly in this JSON format:
{{
  "agreed_updates": [...],
  "items_to_remove": [
    {{"type": "issue", "number": 123, "reason": "Duplicate"}},
    {{"type": "milestone", "number": 10, "reason": "Redundant"}}
  ]
}}
Ensure the output is ONLY valid JSON.
"""
        res, _ = client.complete(prompt, self.agent.get_model_config(state), agent_name=self.name)
        try:
            clean = re.sub(r"^```(?:json)?\s*", "", res.strip(), flags=re.MULTILINE)
            clean = re.sub(r"```\s*$", "", clean.strip(), flags=re.MULTILINE)
            data = json.loads(clean.strip())
            return {"synthesized_actions": data}
        except Exception as e:
            return {"last_error": f"Failed to parse final consolidation JSON: {e}"}

    def apply_updates(self, state: GroomingState) -> GroomingState:
        if state.get("last_error"): return {}
        print(f"[{self.name}] Grooming Node: apply_updates")
        
        repo_name = state.get("repo_name", "")
        valid_issues = {i["number"] for i in state.get("issues", [])}
        valid_milestones = {m["number"] for m in state.get("milestones", [])}
        actions = state.get("synthesized_actions", {})
        results = state.get("creation_results", [])
        proj_id = state.get("github_project_id")
        fields = state.get("project_fields", [])
        
        # 1. Handle Removals/Closures
        removals = actions.get("items_to_remove", [])
        for item in removals:
            num = item.get("number")
            itype = item.get("type")
            
            # Safety checks
            if itype == "issue" and num not in valid_issues:
                print(f"[{self.name}] Skipping removal of invalid/PR issue number: {num}")
                continue
            if itype == "milestone" and num not in valid_milestones:
                print(f"[{self.name}] Skipping removal of invalid milestone number: {num}")
                continue
                
            try:
                reason = item.get("reason", "No reason provided")
                if itype == "issue" and num:
                    github_client.update_issue(repo_name, num, agent_name=self.name, state="closed")
                    github_client.create_issue_comment(repo_name, num, f"🚫 Closing as part of grooming: {reason}", agent_name=self.name)
                    results.append(f"🚫 Closed redundant issue #{num}")
                elif itype == "milestone" and num:
                    github_client.delete_milestone(repo_name, num, agent_name=self.name)
                    results.append(f"🔥 Deleted redundant milestone #{num}")
            except Exception as e:
                print(f"[{self.name}] Failed to remove item: {e}")

        # 2. Handle Agreed Updates
        def get_field_mutation(field_name: str, value: str) -> Optional[tuple]:
            for f in fields:
                if f.get("name", "").lower() == field_name.lower():
                    if "options" in f:
                        for opt in f["options"]:
                            if opt["name"].lower() == value.lower():
                                return (f["id"], {"singleSelectOptionId": opt["id"]})
                    else:
                        return (f["id"], {"text": value})
            return None

        agreed = actions.get("agreed_updates", [])
        for update in agreed:
            issue_number = update.get("issue_number")
            if not issue_number or issue_number not in valid_issues:
                if issue_number: print(f"[{self.name}] Skipping update for invalid/PR issue number: {issue_number}")
                continue
            
            # 0. Update title/body if specified in refinement
            updated_title = update.get("updated_title")
            updated_body = update.get("updated_body")
            if updated_title or updated_body:
                try:
                    payload = {}
                    if updated_title: payload["title"] = updated_title
                    if updated_body: payload["body"] = updated_body
                    github_client.update_issue(repo_name, issue_number, agent_name=self.name, **payload)
                    results.append(f"✍️ Refined issue #{issue_number}")
                except Exception as e:
                    print(f"[{self.name}] Failed refinement update on #{issue_number}: {e}")

            # 1. Update issue body for relationships
            blocks = update.get("blocks", [])
            blocked_by = update.get("blocked_by", [])
            
            if blocks or blocked_by:
                try:
                    iss_data = github_client.get_issue(repo_name, issue_number, agent_name=self.name)
                    current_body = iss_data.get("body") or ""
                    
                    additions = "\n\n--- \n**Grooming Relationships**\n"
                    additions += "*(Note: Since GitHub lacks native relationship fields, we append them here as a workaround)*\n"
                    if blocks: additions += f"- **Blocks:** {', '.join([f'#{b}' for b in blocks])}\n"
                    if blocked_by: additions += f"- **Blocked by:** {', '.join([f'#{b}' for b in blocked_by])}\n"
                    
                    if "**Grooming Relationships**" not in current_body:
                        new_body = current_body + additions
                        github_client.update_issue(repo_name, issue_number, agent_name=self.name, body=new_body)
                        results.append(f"🔗 Updated relationships for #{issue_number}")
                except Exception as e:
                    print(f"[{self.name}] Failed body update on #{issue_number}: {e}")

            # 2. Add agreed comments
            for c in update.get("new_comments", []):
                try:
                    github_client.create_issue_comment(repo_name, issue_number, c, agent_name=self.name)
                except Exception as e:
                    print(f"[{self.name}] Failed comment on #{issue_number}: {e}")

            # 3. Handle Label Updates (Groomed, Priority, Size)
            # Fetch current labels from state
            current_labels = next((i.get("labels", []) for i in state.get("issues", []) if i.get("number") == issue_number), [])
            
            priority = update.get("priority")
            size = update.get("size")
            status = update.get("status")
            
            # Identify labels to ADD
            labels_to_add = []
            if status == "Ready" and "Groomed" not in current_labels:
                labels_to_add.append("Groomed")
            
            if priority:
                new_p_label = f"Priority: {priority}"
                if new_p_label not in current_labels:
                    labels_to_add.append(new_p_label)
            
            if size:
                new_s_label = f"Size: {size}"
                if new_s_label not in current_labels:
                    labels_to_add.append(new_s_label)

            # Identify labels to REMOVE
            labels_to_remove = []
            if status != "Ready" and "Groomed" in current_labels:
                labels_to_remove.append("Groomed")
            
            if priority:
                # Remove any existing Priority labels that aren't the new one
                for label in current_labels:
                    if label.startswith("Priority: ") and label != f"Priority: {priority}":
                        labels_to_remove.append(label)
            
            if size:
                # Remove any existing Size labels that aren't the new one
                for label in current_labels:
                    if label.startswith("Size: ") and label != f"Size: {size}":
                        labels_to_remove.append(label)

            # Execute removals
            for label in labels_to_remove:
                try:
                    github_client.remove_issue_label(repo_name, issue_number, label, agent_name=self.name)
                    results.append(f"🗑️ Removed label: '{label}' from #{issue_number}")
                except Exception as e:
                    print(f"[{self.name}] Failed to remove label '{label}' on #{issue_number}: {e}")

            # Execute additions
            if labels_to_add:
                try:
                    github_client.add_issue_labels(repo_name, issue_number, labels_to_add, agent_name=self.name)
                    results.append(f"🏷️ Added labels: {', '.join(labels_to_add)} to #{issue_number}")
                except Exception as e:
                    print(f"[{self.name}] Failed to add labels to #{issue_number}: {e}")

            # 4. Mutate Project V2 Fields (Legacy/Optional backup)
            if proj_id:
                try:
                    # Get Item ID for this issue
                    item_data = github_client.get_issue_project_items(repo_name, issue_number, agent_name=self.name)
                    item_id = None
                    if item_data.get("project_items"):
                        # Find the item ID matching our project
                        for pi in item_data["project_items"]:
                            if pi.get("project", {}).get("id") == proj_id:
                                item_id = pi["id"]
                                break
                    
                    if not item_id and item_data.get("issue_id"):
                        # Add item to project if missing
                        print(f"[{self.name}] Adding issue #{issue_number} to project {proj_id}")
                        item_id = github_client.add_item_to_project(proj_id, item_data["issue_id"], agent_name=self.name)
                        
                    if item_id:
                        if priority:
                            mut = get_field_mutation("Priority", priority)
                            if mut: 
                                github_client.update_project_v2_item_field(proj_id, item_id, mut[0], mut[1], agent_name=self.name)
                                
                        if size:
                            mut = get_field_mutation("Size", size)
                            if mut: 
                                github_client.update_project_v2_item_field(proj_id, item_id, mut[0], mut[1], agent_name=self.name)
                                
                        if status:
                            mut = get_field_mutation("Status", status)
                            if mut: 
                                github_client.update_project_v2_item_field(proj_id, item_id, mut[0], mut[1], agent_name=self.name)
                                
                except Exception as e:
                    print(f"[{self.name}] Failed to update Project V2 properties for #{issue_number}: {e}")

        # Note: we skip creating new milestones/issues here to keep the complexity manageable,
        # relying on milestone_creation workflow for initial generation. But it can be added.
        
        return {"creation_results": results}

    def notify_slack(self, state: GroomingState) -> GroomingState:
        print(f"[{self.name}] Grooming Node: notify_slack")
        channel = state.get("slack_channel") or "C0AL8GW2VAL"
        thread_ts = state.get("thread_ts")
        prd_title = state.get("prd_title", "Unknown")
        repo_name = state.get("repo_name", "")
        results = state.get("creation_results", [])
        error = state.get("last_error")

        if error:
            msg = f"⚠️ *Grooming Error* for '{prd_title}':\n{error}"
        else:
            res_str = "\n".join(results) if results else "_No specific updates made._"
            msg = f"🧪 *Grooming Complete* for '{prd_title}' (Repo: `{repo_name}`)\nDr. Rossini and Riccado have finished their review.\n\n*Updates:*\n{res_str}"
            
        try:
            slack_queue.post_message(agent=self.agent.agent_id, channel=channel, message=msg, thread_ts=thread_ts)
        except Exception as e:
            print(f"[{self.name}] Slack notification failed: {e}")

        return {"final_response": msg}


def setup_grooming_graph(agent):
    workflow_logic = GroomingWorkflow(agent)
    workflow = StateGraph(GroomingState)

    workflow.add_node("load_context", workflow_logic.load_context)
    workflow.add_node("fetch_github_state", workflow_logic.fetch_github_state)
    workflow.add_node("rossini_review", workflow_logic.rossini_review)
    workflow.add_node("riccado_review", workflow_logic.riccado_review)
    workflow.add_node("synthesize", workflow_logic.synthesize)
    workflow.add_node("debate_in_github", workflow_logic.debate_in_github)
    workflow.add_node("consolidate_and_refine", workflow_logic.consolidate_and_refine)
    workflow.add_node("apply_updates", workflow_logic.apply_updates)
    workflow.add_node("notify_slack", workflow_logic.notify_slack)

    workflow.set_entry_point("load_context")
    workflow.add_edge("load_context", "fetch_github_state")
    
    # Parallelize Rossini and Riccado reviews
    workflow.add_edge("fetch_github_state", "rossini_review")
    workflow.add_edge("fetch_github_state", "riccado_review")
    
    # Fan-in to synthesize
    workflow.add_edge("rossini_review", "synthesize")
    workflow.add_edge("riccado_review", "synthesize")
    
    workflow.add_edge("synthesize", "debate_in_github")
    workflow.add_edge("debate_in_github", "consolidate_and_refine")
    
    workflow.add_edge("consolidate_and_refine", "apply_updates")
    workflow.add_edge("apply_updates", "notify_slack")
    workflow.add_edge("notify_slack", END)

    checkpointer = PostgresCheckpointer()
    return workflow.compile(checkpointer=checkpointer)
