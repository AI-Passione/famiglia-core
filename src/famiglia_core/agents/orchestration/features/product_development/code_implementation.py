import os
import re
import json
import time
from typing import Any, Dict, List, Optional
from langgraph.graph import StateGraph, END

from famiglia_core.agents.orchestration.utils.state import AgentState
from famiglia_core.agents.llm.client import client
from famiglia_core.agents.tools.github import github_client
from famiglia_core.db.tools.github_store import github_store
from famiglia_core.db.observability.checkpointer import PostgresCheckpointer
from famiglia_core.command_center.backend.slack.client import slack_queue
from famiglia_core.agents.llm.models_registry import QWEN25_CODER_7B

class CodeImplementationState(AgentState):
    """State for the Code Implementation workflow."""
    repo_name: str
    groomed_issues: List[Dict[str, Any]]
    open_prs_with_comments: List[Dict[str, Any]]
    pr_results: List[str]
    slack_channel: str
    thread_ts: Optional[str]
    last_error: str

class CodeImplementationWorkflow:
    def __init__(self, agent):
        self.agent = agent
        self.name = agent.name
        self.model_config = agent.model_config

    def load_context(self, state: CodeImplementationState) -> CodeImplementationState:
        print(f"[{self.name}] CodeImplementation Node: load_context")
        task = state.get("task", "")
        repos = github_store.get_accessible_repos(self.name)
        repo_name = None
        
        task_lower = task.lower()
        if repos:
            for r in repos:
                if r["repo_name"].lower() in task_lower:
                    repo_name = r["repo_name"]
                    break
            if not repo_name:
                repo_name = repos[0]["repo_name"]
                
        if not repo_name:
            return {"last_error": "Could not determine a valid repository to scan. No accessible repos found."}
            
        return {"repo_name": repo_name, "pr_results": []}

    def fetch_groomed_issues(self, state: CodeImplementationState) -> CodeImplementationState:
        if state.get("last_error"): return {}
        print(f"[{self.name}] CodeImplementation Node: fetch_groomed_issues")
        repo_name = state.get("repo_name")
        
        try:
            issues = github_client.list_issues(repo_name, agent_name=self.name, state="open")
        except Exception as e:
            return {"last_error": f"Failed to fetch GitHub issues: {e}"}

        groomed_issues = [issue for issue in issues if "Groomed" in (issue.get("labels") or [])]
        return {"groomed_issues": groomed_issues}

    def _repair_json_string(self, raw: str) -> str:
        """
        Attempts to repair common LLM JSON errors, especially invalid backslash escapes.
        """
        # 1. Handle common invalid escapes by doubling backslashes that aren't valid JSON escapes
        def replace_invalid_escape(match):
            esc = match.group(0)
            if esc in ['\\"', '\\\\', '\\/', '\\b', '\\f', '\\n', '\\r', '\\t']:
                return esc
            if re.match(r'\\u[0-9a-fA-F]{4}', esc):
                return esc
            # It's an invalid escape, so double the backslash
            return '\\\\' + esc[1:]

        repaired = re.sub(r'\\.', replace_invalid_escape, raw)
        
        # 2. Escape literal newlines within strings (JSON requires \n to be escaped as \\n)
        # This is a bit risky but often necessary for raw LLM outputs
        # We only want to escape newlines that are INSIDE quotes
        return repaired

    def generate_and_create_prs(self, state: CodeImplementationState) -> CodeImplementationState:
        if state.get("last_error"): return {}
        print(f"[{self.name}] CodeImplementation Node: generate_and_create_prs")
        
        repo_name = state.get("repo_name")
        groomed_issues = state.get("groomed_issues", [])
        pr_results = state.get("pr_results", [])
        
        print(f"[{self.name}] Found {len(groomed_issues)} groomed issues to process in {repo_name}")
        
        if not groomed_issues:
            pr_results.append("No 'Groomed' issues found.")
            return {"pr_results": pr_results}

        for issue in groomed_issues:
            num = issue.get("number")
            title = issue.get("title")
            print(f"[{self.name}] Processing Issue #{num}: {title}")
            issue_full = None
            try:
                issue_full = github_client.get_issue(repo_name, num, agent_name=self.name)
            except Exception:
                pass
            
            body = issue_full.get("body", "") if issue_full else ""
            
            prompt = f"""
Task: You are an expert Python engineer. 
Write the code to solve the following GitHub Issue.

Issue Title: {title}
Issue Body:
{body}

You must return ONLY a valid JSON object containing exactly these keys:
- "file_path": The relative path to the file you want to create or modify.
- "file_content": The complete content of the file. IMPORTANT: All backslashes and newlines within this string MUST be properly JSON-escaped (e.g., use \\n for newlines, \\\\ for a literal backslash).
- "commit_message": A concise commit message.
- "pr_title": The Title of the Pull Request.
- "pr_body": The Body of the Pull Request (markdown, explaining the fix).
- "new_branch": The name of the new branch to create (e.g. "fix/issue-{num}").

Do not include any other text outside the JSON block. Ensure the JSON is perfectly valid and parsable.
"""
            try:
                print(f"[{self.name}] Generating code for issue #{num} via {QWEN25_CODER_7B}")
                qwen_config = {"provider": "ollama", "model": QWEN25_CODER_7B, "options": {"temperature": 0.2}}
                res, _ = client.complete(prompt, qwen_config, agent_name=self.name)
                
                # Robust extraction
                json_match = re.search(r"(\{.*\})", res.strip(), re.DOTALL)
                if not json_match:
                    raise ValueError("No JSON object found in response")
                
                clean = json_match.group(1)
                try:
                    data = json.loads(clean)
                except json.JSONDecodeError:
                    print(f"[{self.name}] Initial JSON parse failed, attempting repair...")
                    repaired = self._repair_json_string(clean)
                    data = json.loads(repaired)
                
                print(f"[{self.name}] Successfully generated and parsed code solution for #{num}")
                
                repo_data = github_client.read_repo(repo_name, agent_name=self.name)
                base_branch = repo_data.get("default_branch", "main")
                
                pr_data = github_client.auto_create_pr(
                    repo_name=repo_name,
                    file_path=data.get("file_path"),
                    file_content=data.get("file_content"),
                    commit_message=data.get("commit_message"),
                    pr_title=data.get("pr_title"),
                    pr_body=data.get("pr_body"),
                    new_branch=data.get("new_branch"),
                    base_branch=base_branch,
                    agent_name=self.name
                )
                
                pr_url = pr_data.get("html_url", "URL not found")
                print(f"[{self.name}] PR created successfully for #{num}: {pr_url}")
                pr_results.append(f"• PR for Issue #{num}: {pr_url}")
                
                # Post comment on originating issue
                github_client.create_issue_comment(
                    repo_name, 
                    num, 
                    f"🤌 Ciao! I have opened a Pull Request to address this issue: {pr_url}", 
                    agent_name=self.name
                )
                
                github_client.remove_issue_label(repo_name, num, "Groomed", agent_name=self.name)
                
                # Move to Review in Project V2
                self._move_issue_to_review(repo_name, num)
                
            except Exception as e:
                err_msg = f"• Failed to generate or create PR for Issue #{num}: {e}"
                print(f"[{self.name}] {err_msg}")
                pr_results.append(err_msg)

        return {"pr_results": pr_results}

    def fetch_open_prs_with_comments(self, state: CodeImplementationState) -> CodeImplementationState:
        if state.get("last_error"): return {}
        print(f"[{self.name}] CodeImplementation Node: fetch_open_prs_with_comments")
        repo_name = state.get("repo_name")
        
        try:
            prs = github_client.list_pull_requests(repo_name, agent_name=self.name, state="open")
        except Exception as e:
            return {"last_error": f"Failed to list PRs: {e}"}

        # Broaden discovery: scan ALL open PRs in the repository
        print(f"[{self.name}] Scanning {len(prs)} open PRs for human feedback.")
        
        open_prs_with_comments = []
        for pr in prs:
            num = pr["number"]
            # Fetch general comments and review comments
            issue_comments = github_client.list_issue_comments(repo_name, num, agent_name=self.name)
            review_comments = github_client.list_pull_request_comments(repo_name, num, agent_name=self.name)
            
            all_comments = issue_comments + review_comments
            # Sort all comments by creation date (metadata often has 'created_at')
            all_comments.sort(key=lambda x: x.get("created_at", ""))
            
            human_feedback_items = []
            
            for c in all_comments:
                user = c.get("user", {}).get("login")
                if user and "[bot]" not in user.lower() and "riccado" not in user.lower():
                    # It's a human comment
                    human_feedback_items.append({
                        "id": c.get("id"),
                        "user": user,
                        "body": c.get("body"),
                        "path": c.get("path"), # Store path for review comments
                        "type": "review" if "pull_request_review_id" in c or "path" in c else "issue"
                    })
            
            if human_feedback_items:
                print(f"[{self.name}] Found {len(human_feedback_items)} feedback items for PR #{num}")
                pr["human_feedback_items"] = human_feedback_items
                pr["human_feedback_text"] = "\n".join([f"- {i['user']}: {i['body']}" for i in human_feedback_items])
                # Ensure HTML URL is available
                pr["html_url"] = pr.get("html_url")
                open_prs_with_comments.append(pr)
            else:
                print(f"[{self.name}] PR #{num} has no human feedback in its history.")
                
        return {"open_prs_with_comments": open_prs_with_comments}

    def address_pr_comments(self, state: CodeImplementationState) -> CodeImplementationState:
        if state.get("last_error"): return {}
        print(f"[{self.name}] CodeImplementation Node: address_pr_comments")
        
        repo_name = state.get("repo_name")
        target_prs = state.get("open_prs_with_comments", [])
        pr_results = state.get("pr_results", [])
        
        for pr in target_prs:
            if not isinstance(pr, dict): continue
            num = pr.get("number")
            feedback_text = pr.get("human_feedback_text", "")
            feedback_items = pr.get("human_feedback_items", [])
            if not isinstance(feedback_items, list): feedback_items = []
            
            head_branch = pr.get("head", {}).get("ref")
            print(f"[{self.name}] Orchestrating fix for PR #{num} on branch {head_branch}")
            
            try:
                # 1. Gather all current files and their content in the PR
                files = github_client.list_pull_request_files(repo_name, num, agent_name=self.name)
                pr_context_files = []
                for f in files:
                    path = f["filename"]
                    try:
                        content_data = github_client.read_file(repo_name, path, branch=head_branch, agent_name=self.name)
                        content = content_data.get("decoded_content", "") if isinstance(content_data, dict) else str(content_data)
                        pr_context_files.append({"path": path, "content": content})
                    except Exception as e:
                        print(f"[{self.name}] Could not read file {path} for context: {e}")

                # 2. Ask LLM to address ALL feedback across ALL files
                files_context_str = "\n---\n".join([f"File: {f['path']}\nContent:\n{f['content']}" for f in pr_context_files])
                
                prompt = f"""
Task: You are a lead software engineer addressing code review feedback.
Below is the full history of human feedback on this Pull Request, followed by the current content of all files in the PR.

Human Feedback History:
{feedback_text}

Current PR Files:
{files_context_str}

Please generate the updated code for ANY and ALL files that need changes to address the feedback. 
If a comment requires a new file to be created, include it in your response.

IMPORTANT: 
- EVERY file content you return must end with a POSIX terminal newline (a literal \\n at the very end of the string). 
- This is a strict requirement for the project's linting.

You must return ONLY a JSON object containing a list of file updates:
{{
  "updates": [
    {{
      "file_path": "path/to/file.py",
      "file_content": "complete updated content...",
      "commit_message": "Concise fix description"
    }},
    ...
  ]
}}

IMPORTANT: Properly escape all internal newlines (\\n) and backslashes (\\\\) in the JSON strings.
Do not include any text outside the JSON block.
"""
                qwen_config = {"provider": "ollama", "model": QWEN25_CODER_7B, "options": {"temperature": 0.1}}
                res, _ = client.complete(prompt, qwen_config, agent_name=self.name)
                
                json_match = re.search(r"(\{.*\})", res.strip(), re.DOTALL)
                if not json_match:
                    print(f"[{self.name}] Error: No JSON found in orchestrated response for PR #{num}")
                    continue
                
                try:
                    data = json.loads(json_match.group(1))
                except Exception:
                    data = json.loads(self._repair_json_string(json_match.group(1)))
                
                updates = data.get("updates", [])
                if not isinstance(updates, list):
                    print(f"[{self.name}] Error: 'updates' is not a list in PR #{num}")
                    continue
                
                files_updated = []
                for up in updates:
                    path = up.get("file_path")
                    content = up.get("file_content")
                    msg = up.get("commit_message", f"Address feedback on PR #{num}")
                    if path and content:
                        # Programmatic fail-safe: Ensure POSIX terminal newline
                        if not content.endswith("\n"):
                            content += "\n"
                            
                        github_client.commit_file(
                            repo_name=repo_name, file_path=path, content=content,
                            commit_message=msg, branch=head_branch, agent_name=self.name
                        )
                        files_updated.append(path)

                # 3. Post Replies
                if files_updated:
                    for item in feedback_items:
                        if not isinstance(item, dict): continue
                        item_id = item.get("id")
                        item_path = item.get("path")
                        
                        # If a comment specifically mentions a file we updated, or is a general comment
                        if not item_path or item_path in files_updated:
                            reply = f"🤌 Ciao! I have orchestrated a fix for `{item_path or 'the PR'}` and pushed it to branch `{head_branch}`. Please take another look!"
                            try:
                                if item.get("type") == "review" and item_id:
                                    github_client.create_pull_request_comment_reply(repo_name, num, item_id, reply, self.name)
                                else:
                                    github_client.create_issue_comment(repo_name, num, reply, self.name)
                            except Exception as ce:
                                print(f"[{self.name}] Failed to post orchestrated reply: {ce}")
                    
                    pr_url = pr.get("html_url", "URL not found")
                    pr_results.append(f"• Orchestrated coordinated fixes for PR #{num} (Updated: {', '.join(files_updated)})\n  🔗 {pr_url}")

                    # Moving related issues to 'Review'
                    issue_nums = self._extract_issue_numbers(pr)
                    for inum in issue_nums:
                        self._move_issue_to_review(repo_name, inum)
                else:
                    print(f"[{self.name}] No orchestrated updates generated for PR #{num}")

            except Exception as e:
                pr_url = pr.get("html_url", "URL not found")
                err_msg = f"• Failed orchestrated addressal for PR #{num}: {e}\n  🔗 {pr_url}"
                print(f"[{self.name}] {err_msg}")
                pr_results.append(err_msg)


        return {"pr_results": pr_results}

    def notify_slack(self, state: CodeImplementationState) -> CodeImplementationState:
        print(f"[{self.name}] CodeImplementation Node: notify_slack")
        thread_ts = state.get("thread_ts")
        error = state.get("last_error")
        results = state.get("pr_results", [])
        
        if error:
            msg = f"⚠️ *Code Implementation Error*:\n{error}"
        else:
            res_str = "\n".join(results) if results else "No PRs were created."
            msg = f"🤌 Ciao team! I have successfully generated code for 'Groomed' issues.\n\nHere are the Pull Requests I opened:\n{res_str}\n\nPlease review them before I merge bad code!"
            
        try:
            slack_queue.enqueue_message(
                agent=self.agent.agent_id,
                channel="C0AH64QTG2U", # #tech-riccado channel ID
                message=msg
                # Removed thread_ts because it might belong to a different channel
            )
        except Exception as e:
            print(f"[{self.name}] Slack notification failed: {e}")

        return {"final_response": msg}

    def _extract_issue_numbers(self, pr: Dict[str, Any]) -> List[int]:
        """Extract issue numbers from the PR body or its branch name."""
        nums = set()
        
        # 1. From body
        body = pr.get("body", "") or ""
        body_matches = re.findall(r"(?:#|issue-|issue\s*)(\d+)", body, re.IGNORECASE)
        for m in body_matches: nums.add(int(m))
        
        # 2. From branch name
        branch = pr.get("head", {}).get("ref", "") or ""
        branch_matches = re.findall(r"(?:issue-|#|/|fix-)(\d+)", branch)
        for m in branch_matches: nums.add(int(m))
        
        return list(nums)

    def _move_issue_to_review(self, repo_name: str, issue_number: int):
        """Moves a GitHub issue to the 'Review' status in its connected Project V2."""
        try:
            print(f"[{self.name}] Checking Project V2 status for Issue #{issue_number}...")
            project_data = github_client.get_issue_project_items(repo_name, issue_number, agent_name=self.name)
            issue_id = project_data.get("issue_id")
            project_items = project_data.get("project_items", [])
            
            # If issue is not in any project, try to find a project for the repo and add it
            if not project_items and issue_id:
                print(f"[{self.name}] Issue #{issue_number} is not in a project. Attempting to discover and link...")
                projects = github_client.list_projects_v2(repo_name, agent_name=self.name)
                if projects:
                    # Link to the first project found
                    target_project_id = projects[0]["id"]
                    print(f"[{self.name}] Linking Issue #{issue_number} to Project: {projects[0]['title']} ({target_project_id})")
                    item_id = github_client.add_item_to_project(target_project_id, issue_id, agent_name=self.name)
                    # Create a dummy project item to process below
                    project_items = [{"project": {"id": target_project_id}, "id": item_id}]
                else:
                    print(f"[{self.name}] No Project V2 found for {repo_name} owner.")
                    return

            for item in project_items:
                project_id = item.get("project", {}).get("id")
                item_id = item.get("id")
                if not project_id or not item_id: continue
                
                fields = github_client.get_project_v2_fields(project_id, agent_name=self.name)
                # Look for 'Status' field (smart match)
                status_field = next((f for f in fields if f.get("name", "").lower() == "status"), None)
                if status_field:
                    options = status_field.get("options", [])
                    # Look for 'Review' option (smart match)
                    review_option = next((o for o in options if "review" in o.get("name", "").lower()), None)
                    if review_option:
                        github_client.update_project_v2_item_field(
                            project_id, item_id, status_field["id"], 
                            {"singleSelectOptionId": review_option["id"]}, 
                            agent_name=self.name
                        )
                        print(f"[{self.name}] Successfully moved Issue #{issue_number} to 'Review' in project {project_id}")
                    else:
                        print(f"[{self.name}] Could not find 'Review' option in 'Status' field for project {project_id}")
                else:
                    print(f"[{self.name}] Could not find 'Status' field for project {project_id}")
        except Exception as e:
            print(f"[{self.name}] Failed to move issue #{issue_number} to Review: {e}")

def setup_code_implementation_graph(agent):
    workflow_logic = CodeImplementationWorkflow(agent)
    workflow = StateGraph(CodeImplementationState)

    workflow.add_node("load_context", workflow_logic.load_context)
    workflow.add_node("fetch_groomed_issues", workflow_logic.fetch_groomed_issues)
    workflow.add_node("generate_and_create_prs", workflow_logic.generate_and_create_prs)
    workflow.add_node("fetch_open_prs_with_comments", workflow_logic.fetch_open_prs_with_comments)
    workflow.add_node("address_pr_comments", workflow_logic.address_pr_comments)
    workflow.add_node("notify_slack", workflow_logic.notify_slack)

    workflow.set_entry_point("load_context")
    workflow.add_edge("load_context", "fetch_groomed_issues")
    workflow.add_edge("fetch_groomed_issues", "generate_and_create_prs")
    workflow.add_edge("generate_and_create_prs", "fetch_open_prs_with_comments")
    workflow.add_edge("fetch_open_prs_with_comments", "address_pr_comments")
    workflow.add_edge("address_pr_comments", "notify_slack")
    workflow.add_edge("notify_slack", END)

    checkpointer = PostgresCheckpointer()
    return workflow.compile(checkpointer=checkpointer)
