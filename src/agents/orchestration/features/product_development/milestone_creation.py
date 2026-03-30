from typing import Any, Dict, List, Optional, TypedDict
from langgraph.graph import StateGraph, END
import os
import re
import json

from src.agents.orchestration.utils.state import AgentState
from src.agents.llm.client import client
from src.agents.tools.notion import notion_client
from src.agents.tools.github import github_client
from src.db.tools.github_store import github_store
from src.db.observability.checkpointer import PostgresCheckpointer
from src.command_center.backend.slack.client import slack_queue


class MilestoneCreationState(AgentState):
    """State for the Milestone & Issue Creation workflow."""
    notion_page_id: str
    prd_title: str
    prd_markdown: str
    notion_url: str
    repo_name: str
    github_repo_id: Optional[int]
    repository_id: str         # GraphQL Node ID
    owner_id: str              # GraphQL Node ID
    owner_type: str            # "Organization" or "User"
    github_project_id: Optional[str]
    github_project_url: Optional[str]
    project_error: Optional[str]
    repo_source: str          # "memory" | "llm"
    milestones: List[Dict[str, Any]]   # [{title, description, issues:[{title,body}]}]
    issues: List[Dict[str, Any]]       # flat list for reference
    existing_milestones: Dict[str, int] # title.lower() -> number
    existing_issues: List[Dict[str, Any]] # raw existing issue summaries
    semantic_mapping: Dict[str, Any]    # mapping of planned_title -> existing_info
    creation_results: List[str]        # human-readable log of what was created/skipped
    created_count: int
    skipped_count: int
    error_count: int
    slack_channel: str
    thread_ts: Optional[str]
    notion_success: bool
    last_error: str


class MilestoneCreationWorkflow:
    """
    Logic for the GitHub Milestone & Issue Creation LangGraph.

    Flow:
      load_prd → select_repo → select_or_create_project → parse_prd_into_plan
              → check_existing → create_items → notify_slack
    """

    def __init__(self, agent):
        self.agent = agent
        self.name = agent.name
        self.model_config = agent.model_config
        self.personality = self._load_rossini_personality()

    def _load_rossini_personality(self) -> str:
        try:
            soul_path = os.path.join(os.getcwd(), "src/agents/souls/rossini.md")
            if os.path.exists(soul_path):
                with open(soul_path, "r") as f:
                    content = f.read()
                persona_match = re.search(r"## PERSONA & TONE(.*?)(##|$)", content, re.DOTALL)
                if persona_match:
                    return persona_match.group(1).strip()
        except Exception:
            pass
        return "A professional product strategist named Dr. Rossini."

    # ------------------------------------------------------------------
    # Node 1: load_prd
    # ------------------------------------------------------------------
    def load_prd(self, state: MilestoneCreationState) -> MilestoneCreationState:
        """Load the PRD from Notion and verify it is approved."""
        print(f"[{self.name}] Milestone Node: load_prd")
        page_id = state.get("notion_page_id")

        # 1. Try UUID extraction
        if not page_id:
            task = state.get("task", "")
            uuid_match = re.search(r"([a-f0-9]{32})", task)
            if uuid_match:
                page_id = uuid_match.group(1)

        # 2. Fallback: search Notion by name extracted from task
        if not page_id:
            task = state.get("task", "")
            name_match = re.search(
                r"(?:milestones?\s+(?:from|for)\s+(?:the\s+)?prd\s+(?:of|for|on|named|titled)?\s*[\"']?([^\"'?.]+)[\"']?|prd\s*[:\s]+([^?.]+))",
                task, re.IGNORECASE
            )
            if name_match:
                target_name = (name_match.group(1) or name_match.group(2) or "").strip()
                if target_name:
                    print(f"[{self.name}] Searching Notion for PRD: '{target_name}'")
                    results = notion_client.search(query=target_name, agent_name=self.name)
                    if results:
                        page_id = results[0]["id"]

        # 3. Guessing logic: If only one repo is accessible, and it has mappings
        if not page_id:
            repos = github_store.get_accessible_repos(self.name)
            if len(repos) == 1:
                repo_name = repos[0]["repo_name"]
                print(f"[{self.name}] Only one repo accessible ('{repo_name}'). Checking for mapped PRDs...")
                all_mappings = github_store.get_all_prd_mappings()
                repo_mappings = [m for m in all_mappings if m["repo_name"] == repo_name]
                
                if len(repo_mappings) == 1:
                    page_id = repo_mappings[0]["notion_page_id"]
                    print(f"[{self.name}] Guessing PRD: '{repo_mappings[0]['prd_title']}' ({page_id})")
                elif len(repo_mappings) > 1:
                    # Check history to see if the user already answered which one
                    history = state.get("history", [])
                    task_lower = state.get("task", "").lower()
                    
                    last_bot_msg = None
                    for msg in reversed(history):
                        if msg.get("role") == "assistant" and f"found multiple PRDs for repo '{repo_name}'" in msg.get("content"):
                            last_bot_msg = msg.get("content")
                            break
                    
                    if last_bot_msg and len(task_lower.split()) < 6:
                        index = None
                        if re.search(r"\b1\b|first", task_lower): index = 0
                        elif re.search(r"\b2\b|second", task_lower): index = 1
                        elif re.search(r"\b3\b|third", task_lower): index = 2
                        
                        if index is not None and index < len(repo_mappings):
                            page_id = repo_mappings[index]["notion_page_id"]
                            print(f"[{self.name}] Contextual Selection: {repo_mappings[index]['prd_title']} (Index {index})")
                    
                    if not page_id:
                        options = [f"{i+1}. '{m['prd_title']}' (ID: {m['notion_page_id'][:8]})" for i, m in enumerate(repo_mappings)]
                        titles_msg = "\n".join(options)
                        return {"last_error": f"I found multiple PRDs for repo '{repo_name}':\n{titles_msg}\nWhich one should I use? (Reply with the number)"}

        if not page_id:
            return {
                "last_error": "Could not determine which Notion PRD to use. Please provide a Title, URL, or Page ID.",
                "notion_success": False
            }

        try:
            page_data = notion_client.read_page(page_id, agent_name=self.name)
            blocks = page_data.get("blocks", [])
            props = page_data.get("page_properties", {})
            prd_title = props.get("title", "Untitled PRD")
            print(f"[{self.name}] load_prd: Extracted title '{prd_title}'")
            prd_markdown = "\n".join(
                [b.get("text", "") if isinstance(b, dict) else str(b) for b in blocks]
            )
            notion_url = page_data.get("url", "")

            # Verify the PRD is approved before proceeding
            # User wants to denote approval by adding "[Approved]" to the title (case-insensitive)
            if not re.search(r"\[Approved\]", prd_title, re.IGNORECASE):
                return {
                    "last_error": (
                        f"🚨 [DEV-TEST-v1.2] PRD '{prd_title}' is not yet approved. "
                        "Please add '[Approved]' to the Notion page title before creating GitHub milestones."
                    ),
                    "notion_success": False,
                    "notion_page_id": page_id,
                    "prd_title": prd_title,
                    "notion_url": notion_url,
                }

            print(f"[{self.name}] PRD loaded and verified: '{prd_title}' ({page_id})")
            return {
                "notion_page_id": page_id,
                "prd_title": prd_title,
                "prd_markdown": prd_markdown,
                "notion_url": notion_url,
                "notion_success": True,
            }

        except Exception as e:
            print(f"[{self.name}] load_prd failed: {e}")
            return {"last_error": str(e), "notion_success": False, "notion_page_id": page_id}

    # ------------------------------------------------------------------
    # Node 2: select_repo
    # ------------------------------------------------------------------
    def select_repo(self, state: MilestoneCreationState) -> MilestoneCreationState:
        """
        Check PostgreSQL for a cached PRD↔repo mapping first.
        If no mapping exists, use the LLM to pick the best repo from the
        accessible list, then persist the result for future runs.
        """
        print(f"[{self.name}] Milestone Node: select_repo")
        page_id = state.get("notion_page_id", "")
        prd_title = state.get("prd_title", "")

        # --- Phase 1: Check memory ---
        print(f"[{self.name}] select_repo: looking up mapping for page_id='{page_id}'")
        cached_data = github_store.get_repo_for_prd(page_id)
        
        repo_name = None
        repo_id = None
        proj_id = None
        proj_url = None
        
        if cached_data:
            repo_name = cached_data.get("repo_name")
            repo_id = cached_data.get("github_repo_id")
            proj_id = cached_data.get("github_project_id")
            proj_url = cached_data.get("github_project_url")
            print(f"[{self.name}] select_repo: found cached mapping → {repo_name}")

        # --- Phase 2: No mapping found or missing IDs – ask LLM / Fetch IDs ---
        if not repo_name:
            print(f"[{self.name}] select_repo: no cached mapping found, falling back to LLM selection")
            try:
                repos = github_client.list_accessible_repos(self.name)
                repos_str = "\n".join([f"- {r['full_name']}" for r in repos])
                
                prd_context = state.get("prd_markdown", "")[:500]
                prompt = (
                    f"You are a senior software engineer. Given the PRD titled '{prd_title}' "
                    f"with the following summary:\n{prd_context}\n\n"
                    f"Pick the single most relevant GitHub repository from this list:\n{repos_str}\n\n"
                    "Output ONLY the full repository name (e.g. 'org/repo'). "
                    "If none match, output 'NONE'."
                )
                repo_name_llm, _ = client.complete(prompt, self.agent.get_model_config(state), agent_name=self.name)
                repo_name = repo_name_llm.strip().strip("'\"")

                if not repo_name or repo_name.upper() == "NONE":
                    return {
                        "last_error": "Could not identify a matching GitHub repository for this PRD.",
                        "notion_success": False
                    }

                # Find the REST ID for the selected repo
                for r in repos:
                    if r["full_name"].lower() == repo_name.lower():
                        repo_id = r.get("id")
                        break
            except Exception as e:
                print(f"[{self.name}] select_repo failed: {e}")
                return {"last_error": str(e), "notion_success": False}

        # Always fetch Node IDs (GraphQL) to ensure they are available
        try:
            node_ids = github_client.get_node_ids(repo_name, agent_name=self.name)
            repository_id = node_ids["repository_id"]
            owner_id = node_ids["owner_id"]
            owner_type = node_ids["owner_type"]
        except Exception as e:
            print(f"[{self.name}] Failed to fetch Node IDs for {repo_name}: {e}")
            return {"last_error": f"Failed to resolve repository Node IDs: {e}", "notion_success": False}

        # Persist (or update) the mapping with whatever we have
        github_store.upsert_prd_repo_mapping(
            notion_page_id=page_id,
            repo_name=repo_name,
            github_repo_id=repo_id,
            github_project_id=proj_id,
            github_project_url=proj_url,
            prd_title=prd_title
        )

        return {
            "repo_name": repo_name,
            "github_repo_id": repo_id,
            "repository_id": repository_id,
            "owner_id": owner_id,
            "owner_type": owner_type,
            "github_project_id": proj_id,
            "github_project_url": proj_url,
            "repo_source": "memory" if cached_data else "llm"
        }

    # ------------------------------------------------------------------
    # Node 2.5: select_or_create_project [DISABLED]
    # ------------------------------------------------------------------
    def select_or_create_project(self, state: MilestoneCreationState) -> MilestoneCreationState:
        """
        [DISABLED] GitHub Apps require Organization-level installation and specific 
        'Projects: Read & Write' organization permissions to manage Projects V2.
        Users often encounter 'Resource not accessible by integration' errors 
        because personal accounts or repo-only installations lack this scope.
        """
        return {}

    # ------------------------------------------------------------------
    # Node 3: parse_prd_into_plan
    # ------------------------------------------------------------------
    def parse_prd_into_plan(self, state: MilestoneCreationState) -> MilestoneCreationState:
        """Use the LLM to extract milestones and issues from the PRD markdown."""
        print(f"[{self.name}] Milestone Node: parse_prd_into_plan")
        prd_markdown = state.get("prd_markdown", "")
        prd_title = state.get("prd_title", "")

        prompt = f"""
{self.personality}

Task: Analyse the following PRD and extract a structured GitHub project plan.

PRD Title: {prd_title}

PRD Content:
{prd_markdown[:6000]}

Output a JSON array of milestones. Each milestone must have:
- "title": short milestone name (max 60 chars)
- "description": one-sentence summary
- "issues": array of objects with "title" (max 60 chars) and "body" (2–4 sentences of context)

Rules:
1. Map each major PRD section or phase to one Milestone.
2. Each Milestone should have 3–7 GitHub Issues. BREAK DOWN features into atomic, actionable dev tasks.
3. Issue titles must be action-oriented (e.g. "Implement user login flow").
4. Output ONLY valid JSON. Do not include markdown fences or any extra text.

Example shape:
[
  {{
    "title": "Milestone 1: Core Auth",
    "description": "Deliver the authentication subsystem.",
    "issues": [
      {{"title": "Implement JWT login endpoint", "body": "Build POST /auth/login returning a JWT token. Validate credentials against the users table. Return 401 on failure."}}
    ]
  }}
]
"""
        res, _ = client.complete(prompt, self.agent.get_model_config(state), agent_name=self.name)

        milestones: List[Dict[str, Any]] = []
        try:
            # Strip any accidental markdown fences
            clean = re.sub(r"^```(?:json)?\s*", "", res.strip(), flags=re.MULTILINE)
            clean = re.sub(r"```\s*$", "", clean.strip(), flags=re.MULTILINE)
            milestones = json.loads(clean.strip())
        except json.JSONDecodeError as e:
            print(f"[{self.name}] parse_prd_into_plan: JSON parse failed ({e}). Raw output:\n{res[:500]}")
            return {"last_error": f"LLM returned invalid JSON: {e}", "notion_success": False}

        # Flatten issues for convenience
        all_issues = []
        for ms in milestones:
            for issue in ms.get("issues", []):
                all_issues.append({**issue, "_milestone_title": ms["title"]})

        print(f"[{self.name}] Parsed {len(milestones)} milestones, {len(all_issues)} issues total.")
        return {"milestones": milestones, "issues": all_issues}

    # ------------------------------------------------------------------
    # Node 4: check_existing
    # ------------------------------------------------------------------
    def check_existing(self, state: MilestoneCreationState) -> MilestoneCreationState:
        """Fetch current milestones & issues from GitHub and use LLM for semantic mapping."""
        print(f"[{self.name}] Milestone Node: check_existing")
        repo_name = state.get("repo_name", "")
        planned_milestones = state.get("milestones", [])

        # 1. Fetch ALL existing items (pagination already handled in github_client)
        ms_data = []
        existing_issues = []
        existing_ms_dict: Dict[str, int] = {}

        try:
            ms_data = github_client.list_milestones(repo_name, agent_name=self.name, state="all")
            for m in ms_data:
                title = m.get("title", "").lower()
                num = m.get("number")
                if title and num:
                    existing_ms_dict[title] = num
            print(f"[{self.name}] check_existing: {len(ms_data)} milestones found.")
        except Exception as e:
            print(f"[{self.name}] check_existing: list_milestones failed: {e}")

        try:
            existing_issues = github_client.list_issues(repo_name, agent_name=self.name, state="all")
            print(f"[{self.name}] check_existing: {len(existing_issues)} issues found.")
        except Exception as e:
            print(f"[{self.name}] check_existing: list_issues failed: {e}")

        # 2. Semantic Mapping using LLM
        # We pass titles and descriptions to help semantic matching
        existing_ms_list = [
            {"title": m.get("title"), "number": m.get("number"), "description": m.get("description", "")} 
            for m in ms_data
        ]
        existing_iss_list = [
            {
                "title": i.get("title"), 
                "number": i.get("number"), 
                "milestone": i.get("milestone_title"),
                "body": (i.get("body", "") or "")[:200] # Pass snippet for semantic context
            } 
            for i in existing_issues
        ]

        mapping_prompt = f"""
{self.personality}

Task: Compare my PLANNED milestones/issues with EXISTING items in the GitHub repository.
Confirm which planned items are ALREADY present (semantically identical), even if titles vary slightly.

PLANNED PROJECT (From PRD):
MILESTONES:
{json.dumps([{"title": m["title"], "description": m.get("description", "")} for m in planned_milestones], indent=2)}

ISSUES:
{json.dumps([{"title": i.get("title", ""), "body": i.get("body", ""), "milestone": i.get("_milestone_title", "")} for i in state.get("issues", [])], indent=2)}

EXISTING REPO STATE (From GitHub):
MILESTONES:
{json.dumps(existing_ms_list, indent=2)}

ISSUES:
{json.dumps(existing_iss_list, indent=2)}

Rules:
1. Compare PLANNED milestones and issues with EXISTING ones. Matches should be semantically identical, even if phrasing differs.
2. If a planned item already exists, return its number. Otherwise return null.
3. CRITICAL: Milestone mapping numbers MUST only come from the 'MILESTONES' list.
4. CRITICAL: Issue mapping numbers MUST only come from the 'ISSUES' list.

Output Shape:
{{
  "milestones": {{ "Planned Milestone Title": existing_number or null }},
  "issues": {{ "Planned Issue Title": existing_number or null }}
}}

Output ONLY valid JSON.
"""
        mapping_res: Dict[str, Any] = {"milestones": {}, "issues": {}}
        try:
            res, _ = client.complete(mapping_prompt, self.agent.get_model_config(state), agent_name=self.name)
            clean = re.sub(r"^```(?:json)?\s*", "", res.strip(), flags=re.MULTILINE)
            clean = re.sub(r"```\s*$", "", clean.strip(), flags=re.MULTILINE)
            mapping_res = json.loads(clean.strip())
        except Exception as e:
            print(f"[{self.name}] check_existing: Semantic mapping failed ({e}). Falling back to empty mapping.")

        # 3. Validation: Ensure LLM didn't hallucinate milestone numbers (e.g. using issue numbers instead)
        ms_mapping = mapping_res.get("milestones", {})
        valid_ms_numbers = set(existing_ms_dict.values())
        for title, num in list(ms_mapping.items()):
            if num and num not in valid_ms_numbers:
                print(f"[{self.name}] check_existing: LLM hallucinated milestone #{num} for '{title}'. Setting to null.")
                ms_mapping[title] = None
        mapping_res["milestones"] = ms_mapping

        ms_matches = sum(1 for v in mapping_res.get("milestones", {}).values() if v)
        iss_matches = sum(1 for v in mapping_res.get("issues", {}).values() if v)
        print(f"[{self.name}] check_existing: Semantic Mapping validated. Found {ms_matches} milestone matches and {iss_matches} issue matches.")

        return {
            "existing_milestones": existing_ms_dict,
            "existing_issues": existing_issues,
            "semantic_mapping": mapping_res
        }

    # ------------------------------------------------------------------
    # Node 5: create_items
    # ------------------------------------------------------------------
    def create_items(self, state: MilestoneCreationState) -> MilestoneCreationState:
        """Create milestones and issues using semantic mapping to avoid duplicates."""
        print(f"[{self.name}] Milestone Node: create_items")
        repo_name = state.get("repo_name", "")
        milestones = state.get("milestones", [])
        mapping = state.get("semantic_mapping", {})
        ms_mapping = mapping.get("milestones", {})
        issue_mapping = mapping.get("issues", {})
        results = []
        created_count = 0
        skipped_count = 0
        error_count = 0

        for ms in milestones:
            ms_title: str = ms.get("title", "")
            ms_desc: str = ms.get("description", "")
            ms_number: Optional[int] = ms_mapping.get(ms_title)

            if ms_number:
                ms_url = f"https://github.com/{repo_name}/milestone/{ms_number}"
                print(f"[{self.name}] Semantic Match: Milestone '{ms_title}' exists as #{ms_number}")
                results.append(f"⏭️ Milestone already exists: <{ms_url}|*{ms_title}*>")
                skipped_count += 1
            else:
                try:
                    created_ms = github_client.create_milestone(
                        repo_name, ms_title, ms_desc, agent_name=self.name
                    )
                    ms_number = created_ms.get("number")
                    ms_url = f"https://github.com/{repo_name}/milestone/{ms_number}"
                    print(f"[{self.name}] Created milestone #{ms_number}: '{ms_title}'")
                    results.append(f"✅ Created milestone #{ms_number}: <{ms_url}|*{ms_title}*>")
                    created_count += 1
                except Exception as e:
                    print(f"[{self.name}] Failed to create milestone '{ms_title}': {e}")
                    results.append(f"❌ Error creating milestone '{ms_title}': {e}")
                    error_count += 1

            # --- Aggregate issues for this milestone ---
            ms_issue_links = []
            for issue in ms.get("issues", []):
                issue_title: str = issue.get("title", "")
                issue_body: str = issue.get("body", "")
                issue_num_match = issue_mapping.get(issue_title)

                if issue_num_match:
                    issue_url = f"https://github.com/{repo_name}/issues/{issue_num_match}"
                    ms_issue_links.append(f"<{issue_url}|#{issue_num_match}>")
                    skipped_count += 1
                else:
                    try:
                        created_issue = github_client.create_issue(
                            repo_name,
                            issue_title,
                            issue_body,
                            agent_name=self.name,
                            milestone=ms_number
                        )
                        issue_num = created_issue.get("number")
                        issue_url = f"https://github.com/{repo_name}/issues/{issue_num}"
                        ms_issue_links.append(f"<{issue_url}|#{issue_num}>")
                        created_count += 1
                    except Exception as e:
                        print(f"[{self.name}] Failed to create issue '{issue_title}': {e}")
                        error_count += 1
            
            if ms_issue_links:
                results.append(f"   _Issues: {', '.join(ms_issue_links)}_")

        return {
            "creation_results": results, 
            "created_count": created_count, 
            "skipped_count": skipped_count,
            "error_count": error_count
        }

    def mark_all_skipped(self, state: MilestoneCreationState) -> MilestoneCreationState:
        """Node to use when everything is already synced. Just populates the results for the report."""
        print(f"[{self.name}] Milestone Node: mark_all_skipped")
        repo_name = state.get("repo_name", "")
        milestones = state.get("milestones", [])
        mapping = state.get("semantic_mapping", {})
        ms_mapping = mapping.get("milestones", {})
        issue_mapping = mapping.get("issues", {})
        
        results = []
        skipped_count = 0
        for ms in milestones:
            ms_title = ms['title']
            ms_num = ms_mapping.get(ms_title)
            ms_url = f"https://github.com/{repo_name}/milestone/{ms_num}" if ms_num else ""
            
            if ms_url:
                results.append(f"⏭️ Milestone already exists: <{ms_url}|*{ms_title}*>")
                skipped_count += 1
            else:
                results.append(f"⏭️ Milestone already exists: *{ms_title}*")
                skipped_count += 1

            ms_issue_links = []
            for issue in ms.get("issues", []):
                iss_title = issue['title']
                iss_num = issue_mapping.get(iss_title)
                if iss_num:
                    iss_url = f"https://github.com/{repo_name}/issues/{iss_num}"
                    ms_issue_links.append(f"<{iss_url}|#{iss_num}>")
                skipped_count += 1
            
            if ms_issue_links:
                results.append(f"   _Issues: {', '.join(ms_issue_links)}_")

        return {
            "creation_results": results, 
            "created_count": 0, 
            "skipped_count": skipped_count,
            "error_count": 0
        }

    # ------------------------------------------------------------------
    # Node 6: notify_slack
    # ------------------------------------------------------------------
    def notify_slack(self, state: MilestoneCreationState) -> MilestoneCreationState:
        """Post a Slack summary of created/skipped items and the GitHub Project URL."""
        print(f"[{self.name}] Milestone Node: notify_slack")
        channel = state.get("slack_channel") or "C0AL8GW2VAL"
        thread_ts = state.get("thread_ts")
        prd_title = state.get("prd_title", "Unknown PRD")
        repo_name = state.get("repo_name", "")
        results = state.get("creation_results", [])
        error = state.get("last_error")
        repo_source = state.get("repo_source", "")

        if error:
            msg = f"⚠️ *Milestone Creation Error* for '{prd_title}':\n{error}"
        else:
            created_count = state.get("created_count", 0)
            skipped_count = state.get("skipped_count", 0)
            error_count = state.get("error_count", 0)

            repo_src_note = " _(repo recalled from memory)_" if repo_source == "memory" else " _(repo selected by LLM & saved to memory)_"
            results_text = "\n".join(results) if results else "_No items processed._"
            github_url = f"https://github.com/{repo_name}/milestones" if repo_name else ""

            msg = (
                f"🧪 *Milestone & Issue Sync Complete* for '{prd_title}'\n"
                f"📦 Repository: `{repo_name}`{repo_src_note}\n"
            )
            
            # GitHub Project board link was removed here.
                
            msg += f"\n*Summary:* {created_count + skipped_count} items synced ({skipped_count} existing, {created_count} new) · {error_count} errors\n\n"
            msg += f"{results_text}"
            if github_url:
                msg += f"\n\n🔗 <{github_url}|View Milestones on GitHub>"

        try:
            slack_queue.post_message(
                agent=self.agent.agent_id,
                channel=channel,
                message=msg,
                thread_ts=thread_ts
            )
        except Exception as e:
            print(f"[{self.name}] Slack notification failed: {e}")

        return {
            "final_response": msg,
            "thread_ts": thread_ts
        }

    # ------------------------------------------------------------------
    # Routing helpers
    # ------------------------------------------------------------------
    def route_load_prd(self, state: MilestoneCreationState) -> str:
        if state.get("last_error"):
            return "error"
        return "continue"

    def route_select_repo(self, state: MilestoneCreationState) -> str:
        if state.get("last_error") or not state.get("repo_name"):
            return "error"
        return "continue"

    def route_parse(self, state: MilestoneCreationState) -> str:
        if state.get("last_error") or not state.get("milestones"):
            return "error"
        return "continue"

    def route_check_existing(self, state: MilestoneCreationState) -> str:
        """Route to create_items OR mark_all_skipped based on semantic mapping."""
        mapping = state.get("semantic_mapping", {})
        ms_mapping = mapping.get("milestones", {})
        issue_mapping = mapping.get("issues", {})
        
        milestones = state.get("milestones", [])
        
        all_synced = True
        for ms in milestones:
            if not ms_mapping.get(ms["title"]):
                all_synced = False
                break
            for issue in ms.get("issues", []):
                if not issue_mapping.get(issue["title"]):
                    all_synced = False
                    break
            if not all_synced:
                break
                
        return "synced" if all_synced else "create"


def setup_milestone_creation_graph(agent):
    """Build and compile the Milestone Creation StateGraph."""
    print(f"[{agent.name}] Milestone Creation: Setting up graph...", flush=True)
    workflow_logic = MilestoneCreationWorkflow(agent)

    workflow = StateGraph(MilestoneCreationState)

    workflow.add_node("load_prd", workflow_logic.load_prd)
    workflow.add_node("select_repo", workflow_logic.select_repo)
    workflow.add_node("select_or_create_project", workflow_logic.select_or_create_project)
    workflow.add_node("parse_prd_into_plan", workflow_logic.parse_prd_into_plan)
    workflow.add_node("check_existing", workflow_logic.check_existing)
    workflow.add_node("create_items", workflow_logic.create_items)
    workflow.add_node("mark_all_skipped", workflow_logic.mark_all_skipped)
    workflow.add_node("notify_slack", workflow_logic.notify_slack)

    workflow.set_entry_point("load_prd")

    workflow.add_conditional_edges(
        "load_prd",
        workflow_logic.route_load_prd,
        {"continue": "select_repo", "error": "notify_slack"}
    )
    workflow.add_conditional_edges(
        "select_repo",
        workflow_logic.route_select_repo,
        {"continue": "parse_prd_into_plan", "error": "notify_slack"}
    )
    # workflow.add_node("select_or_create_project", workflow_logic.select_or_create_project)
    # workflow.add_edge("select_or_create_project", "parse_prd_into_plan")
    workflow.add_conditional_edges(
        "parse_prd_into_plan",
        workflow_logic.route_parse,
        {"continue": "check_existing", "error": "notify_slack"}
    )
    workflow.add_conditional_edges(
        "check_existing",
        workflow_logic.route_check_existing,
        {"create": "create_items", "synced": "mark_all_skipped"}
    )
    workflow.add_edge("create_items", "notify_slack")
    workflow.add_edge("mark_all_skipped", "notify_slack")
    workflow.add_edge("notify_slack", END)

    print(f"[{agent.name}] Milestone Creation: Compiling with PostgresCheckpointer...", flush=True)
    checkpointer = PostgresCheckpointer()
    return workflow.compile(checkpointer=checkpointer)
