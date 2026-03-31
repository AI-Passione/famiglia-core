import os
import re
from typing import Optional, List, Dict, Any

from famiglia_core.agents.tools.github import github_client
from famiglia_core.agents.tools.notion import notion_client
from famiglia_core.agents.tools.web_search import web_search_client
from famiglia_core.db.agents.context_store import context_store


class CommonSkills:
    """Common skills shared by all AI agents."""

    def _check_web_search_access(self) -> bool:
        """Capability check for Web Search API access."""
        return bool(os.getenv("OLLAMA_API_KEY") or os.getenv("PERPLEXITY_API_KEY"))

    # TODO: It is debatable that if Web Search should be a Common Skill here actually. Probably should be moved to another Class in the future.
    def web_search(self, query: str, user_prompt: Optional[str] = None) -> str:
        """Search the web for current market trends, news, and industry data."""
        if self.propose_action(f"Web search: {query}"):
            print(f"[{self.name}] Tool executing: web_search({query!r})")
            try:
                return web_search_client.search(query, agent_name=self.name, user_prompt=user_prompt)
            except Exception as e:
                return f"Web search failed: {e}"

    def search_memory(self, query: str) -> str:
        """Search historical message logs for relevant past discussions."""
        if self.propose_action(f"Search memory: {query}"):
            print(f"[{self.name}] Tool executing: search_memory({query!r})")
            try:
                results = context_store.search_messages(self.name, query)
                if not results:
                    return f"No historical messages found for query: '{query}'"
                
                output = [f"Found {len(results)} historical messages for '{query}':"]
                for r in results:
                    sender = r.get("sender") or r.get("role", "unknown")
                    content = r.get("content", "")
                    date = r.get("created_at")
                    output.append(f"[{date}] {sender}: {content}")
                
                return "\n".join(output)
            except Exception as e:
                return f"Memory search failed: {e}"


class GitHubSkills:
    """Reusable GitHub tools for agents."""

    def verify_github_env_vars_present(self) -> bool:
        """Standard capability verification for GitHub App connectivity."""
        # Using the instance's hardcoded agent_key logic from Rossini, 
        # or defaulting to the agent's name if not defined.
        agent_key = getattr(self, "github_agent_key", self.name.replace(".", "").replace(" ","_").upper())
        app_id = os.getenv(f"GITHUB_APP_ID_{agent_key}")
        install_id = os.getenv(f"GITHUB_APP_INSTALLATION_ID_{agent_key}")
        pk = os.getenv(f"GITHUB_APP_PRIVATE_KEY_{agent_key}")
        pk_path = os.getenv(f"GITHUB_APP_PRIVATE_KEY_PATH_{agent_key}")
        return bool(app_id and install_id and (pk or pk_path))

    def check_github_access_tool(self) -> str:
        """Low-level credential check: verify if the agent can generate a GitHub App token. Use test_github_diagnostic for user-facing status checks."""
        if self.propose_action("Checking GitHub access token"):
            print(f"[{self.name}] Tool executing: check_github_access_tool()")
            try:
                # Directly call _get_app_token per user request
                token = github_client._get_app_token(self.name)
                return "Successfully verified GitHub access! Token generated and cached. You are Authorized."
            except Exception as e:
                return f"GitHub access check failed: {e}"

    def read_github_repo(self, repo_name: str) -> str:
        """Read a GitHub repository - Tool Version."""
        dummy_names = ["OWNER/REPO", "la-passione-inc/test", "your-org/your-repo", ""]
        if repo_name in dummy_names or not repo_name:
            repos = github_client.list_accessible_repos(agent_name=self.name)
            if repos:
                repo_name = repos[0].get("full_name", repo_name)
                
        if self.propose_action(f"Reading GitHub repo: {repo_name}"):
            print(f"[{self.name}] Tool executing: read_github_repo({repo_name})")
            try:
                data = github_client.read_repo(repo_name, agent_name=self.name)
                return f"Repo details for {repo_name}: {data}"
            except Exception as e:
                return f"Failed to read GitHub repo {repo_name}: {e}"

    def list_accessible_repos(self, force_refresh: bool = False) -> str:
        """List all GitHub repositories this agent has access to."""
        if self.propose_action("Listing accessible GitHub repositories"):
            print(f"[{self.name}] Tool executing: list_accessible_repos(force_refresh={force_refresh})")
            try:
                repos = github_client.list_accessible_repos(agent_name=self.name, force_refresh=force_refresh)
                repo_names = [repo.get("full_name") for repo in repos]
                return f"Accessible repositories: {', '.join(repo_names)}" if repo_names else "No accessible repositories found."
            except Exception as e:
                return f"Failed to list accessible repositories: {e}"

    def read_github_file(self, repo_name: str, file_path: str, branch: Optional[str] = None) -> str:
        """Read a file's content from a GitHub repository."""
        dummy_names = ["OWNER/REPO", "la-passione-inc/test", "your-org/your-repo", ""]
        if repo_name in dummy_names or not repo_name:
            repos = github_client.list_accessible_repos(agent_name=self.name)
            if repos:
                repo_name = repos[0].get("full_name", repo_name)
                
        if self.propose_action(f"Reading file {file_path} from {repo_name}"):
            print(f"[{self.name}] Tool executing: read_github_file({repo_name}, {file_path})")
            try:
                data = github_client.read_file(repo_name, file_path, branch, agent_name=self.name)
                content = data.get("decoded_content", "No content or unreadable.")
                return f"Content of {file_path}:\n{content}"
            except Exception as e:
                return f"Failed to read file {file_path} in {repo_name}: {e}"
                
    def manage_github_issue(self, repo_name: str, action: str, title: Optional[str] = None, body: Optional[str] = None, issue_number: Optional[int] = None) -> str:
        """Manage GitHub issues - Tool Version."""
        dummy_names = ["OWNER/REPO", "la-passione-inc/test", "your-org/your-repo", ""]
        if repo_name in dummy_names or not repo_name:
            repos = github_client.list_accessible_repos(agent_name=self.name)
            if repos:
                repo_name = repos[0].get("full_name", repo_name)
                
        if self.propose_action(f"Managing GitHub issue for repo {repo_name} (Action: {action})"):
            print(f"[{self.name}] Tool executing: manage_github_issue({repo_name}, {action})")
            try:
                if action == "list":
                    data = github_client.list_issues(repo_name, agent_name=self.name)
                    return f"Open issues for {repo_name}: {data}"
                elif action == "read":
                    num = issue_number or (int(title) if title and title.isdigit() else 0)
                    if not num:
                        return "For action='read', you must provide an 'issue_number'."
                    data = github_client.get_issue(repo_name, num, agent_name=self.name)
                    return f"Issue #{num} details: {data}"
                elif action == "create":
                    data = github_client.create_issue(repo_name, title or "Issue", body or "", agent_name=self.name)
                    return f"Successfully created issue in {repo_name}. URL: {data.get('html_url')}"
                elif action in ["update", "close"]:
                    num = issue_number or (int(title) if title and title.isdigit() else 0)
                    if not num:
                        return f"For action='{action}', you must provide an 'issue_number'."
                    
                    state = "closed" if action == "close" else None
                    # If issue_number was provided explicitly, 'title' can be used for the actual new title
                    new_title = title if issue_number else None
                    
                    data = github_client.update_issue(repo_name, num, self.name, state=state, title=new_title, body=body)
                    return f"Successfully updated issue #{num}. URL: {data.get('html_url')}"
                else:
                    return f"Invalid action: {action}"
            except Exception as e:
                return f"Failed to {action} issue on {repo_name}: {e}"

    def manage_github_milestone(self, repo_name: str, action: str, title: Optional[str] = None, description: Optional[str] = None) -> str:
        """Manage GitHub milestones - Tool Version."""
        dummy_names = ["OWNER/REPO", "la-passione-inc/test", "your-org/your-repo", ""]
        if repo_name in dummy_names or not repo_name:
            repos = github_client.list_accessible_repos(agent_name=self.name)
            if repos:
                repo_name = repos[0].get("full_name", repo_name)
                
        if self.propose_action(f"Managing GitHub milestone for repo {repo_name} (Action: {action})"):
            print(f"[{self.name}] Tool executing: manage_github_milestone({repo_name}, {action})")
            try:
                if action == "list":
                    data = github_client.list_milestones(repo_name, agent_name=self.name)
                    return f"Open milestones for {repo_name}: {data}"
                elif action == "create":
                    if not title: return "Title is required to create a milestone."
                    data = github_client.create_milestone(repo_name, title, description or "", agent_name=self.name)
                    return f"Successfully created milestone '{title}' in {repo_name}. Number: {data.get('number')}"
                else:
                    return f"Invalid action: {action}. (Supported: list, create)"
            except Exception as e:
                return f"Failed to {action} milestone on {repo_name}: {e}"

    def manage_github_pull_request(self, repo_name: str, action: str) -> str:
        """Read GitHub pull requests - Tool Version. (Read Only)"""
        dummy_names = ["OWNER/REPO", "la-passione-inc/test", "your-org/your-repo", ""]
        if repo_name in dummy_names or not repo_name:
            repos = github_client.list_accessible_repos(agent_name=self.name)
            if repos:
                repo_name = repos[0].get("full_name", repo_name)
                
        if self.propose_action(f"Reading GitHub PRs for repo {repo_name} (Action: {action})"):
            print(f"[{self.name}] Tool executing: manage_github_pull_request({repo_name}, {action})")
            try:
                if action == "list":
                    data = github_client.list_pull_requests(repo_name, agent_name=self.name)
                    pr_summaries = [{"number": pr.get("number"), "title": pr.get("title"), "state": pr.get("state"), "user": pr.get("user", {}).get("login")} for pr in data]
                    return f"Open Pull Requests for {repo_name}: {pr_summaries}"
                else:
                    return f"Invalid action: {action}. (Supported: list)"
            except Exception as e:
                return f"Failed to {action} PRs on {repo_name}: {e}"


class NotionSkills:
    """Reusable Notion tools for agents."""

    def _check_notion_access(self) -> bool:
        """Standard capability verification for Notion connectivity."""
        return bool(os.getenv("NOTION_API_KEY_ROSSINI"))

    def list_accessible_notion_spaces(self) -> str:
        """List all top-level Notion pages and databases that the agent can access."""
        if self.propose_action("Listing accessible Notion spaces"):
            print(f"[{self.name}] Tool executing: list_accessible_notion_spaces()")
            try:
                return notion_client.list_spaces(agent_name=self.name)
            except Exception as e:
                return f"Failed to list Notion spaces: {e}"

    def read_notion_page(self, page_id: str, user_prompt: Optional[str] = None) -> str:
        """Read properties and text blocks of a Notion page."""
        if self.propose_action(f"Reading Notion page: {page_id}"):
            print(f"[{self.name}] Tool executing: read_notion_page({page_id})")
            try:
                data = notion_client.read_page(page_id, agent_name=self.name)
                return f"Page details for {page_id}: {data}"
            except Exception as e:
                return f"Failed to read Notion page {page_id}: {e}"

    def search_notion_database(self, database_id: str, query: str = "", user_prompt: Optional[str] = None) -> str:
        """Query a Notion database, optionally filtering with a query string."""
        if self.propose_action(f"Searching Notion database {database_id} with query '{query}'"):
            print(f"[{self.name}] Tool executing: search_notion_database({database_id}, {query})")
            try:
                data = notion_client.search_database(database_id, query, agent_name=self.name)
                return f"Database results for {database_id}: {data}"
            except Exception as e:
                return f"Failed to search Notion database {database_id}: {e}"

    def write_notion_page(self, page_id: str, content: str, user_prompt: Optional[str] = None) -> str:
        """Append text content to an existing Notion page."""
        if self.propose_action(f"Writing to Notion page {page_id}"):
            print(f"[{self.name}] Tool executing: write_notion_page({page_id})")
            try:
                result = notion_client.append_text_to_page(page_id, content, agent_name=self.name)
                return result
            except Exception as e:
                return f"Failed to write to Notion page {page_id}: {e}"

    def create_notion_page(self, parent_page_id: str, title: str, content: str = "", user_prompt: Optional[str] = None) -> str:
        """Create a new Notion page as a child of an existing page."""
        if self.propose_action(f"Creating Notion page '{title}' under parent {parent_page_id}"):
            print(f"[{self.name}] Tool executing: create_notion_page({parent_page_id}, {title})")
            try:
                result = notion_client.create_page(parent_page_id, title, content, agent_name=self.name)
                return result
            except Exception as e:
                return f"Failed to create Notion page: {e}"
