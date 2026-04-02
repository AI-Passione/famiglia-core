import os
import re
import time
from typing import Optional, Callable
from famiglia_core.agents.base_agent import BaseAgent
from famiglia_core.agents.tools.github import github_client
from famiglia_core.command_center.backend.slack.client import slack_queue
from famiglia_core.agents.llm.models_registry import QWEN25_CODER_7B
from famiglia_core.agents.orchestration.features.product_development.grooming import setup_grooming_graph
from famiglia_core.agents.orchestration.features.product_development.code_implementation import setup_code_implementation_graph

class Riccardo(BaseAgent):
    def __init__(self):
        super().__init__(
            agent_id="riccardo",
            name="Riccardo",
            role="Principal Data Engineer - Python/dbt/SQL/DevOps master",
            model_config={
                "primary": "claude-3.7-sonnet",
                "secondary": QWEN25_CODER_7B,
            }
        )
        
        # Register Tools
        self.register_tool(
            "read_github_repo", 
            self.read_github_repo,
            capability_name="GitHub Registry Access",
            check_func=self.verify_github_env_vars_present
        )
        self.register_tool("manage_github_issue", self.manage_github_issue)
        self.register_tool("manage_github_milestone", self.manage_github_milestone)
        self.register_tool("list_accessible_repos", self.list_accessible_repos)
        self.register_tool("check_github_access_tool", self.check_github_access_tool)
        self.register_tool("create_github_pr", self.create_github_pr)
        self.register_tool("create_github_branch", self.create_github_branch)
        self.register_tool("read_github_file", self.read_github_file)
        self.register_tool("commit_github_file", self.commit_github_file)
        self.register_tool("auto_create_pr", self.auto_create_pr)

        self.register_feature("run_grooming", self.run_grooming)
        self.grooming_graph = setup_grooming_graph(self)
        
        self.register_feature("run_code_implementation", self.run_code_implementation)
        self.code_implementation_graph = setup_code_implementation_graph(self)

    def verify_github_env_vars_present(self) -> bool:
        """Standard capability verification for GitHub App connectivity."""
        agent_key = self.name.upper()
        app_id = os.getenv(f"GITHUB_APP_ID_{agent_key}")
        install_id = os.getenv(f"GITHUB_APP_INSTALLATION_ID_{agent_key}")
        pk = os.getenv(f"GITHUB_APP_PRIVATE_KEY_{agent_key}")
        pk_path = os.getenv(f"GITHUB_APP_PRIVATE_KEY_PATH_{agent_key}")
        return bool(app_id and install_id and (pk or pk_path))

    def check_github_access_tool(self) -> str:
        """Check if you have valid credentials to access GitHub by attempting to generate an app token."""
        if self.propose_action("Checking GitHub access token"):
            print(f"[Riccardo 🔧] Tool executing: check_github_access_tool()")
            try:
                # Directly call _get_app_token per user request
                token = github_client._get_app_token(self.name)
                return "Successfully verified GitHub access! Token generated and cached. You are Authorized."
            except Exception as e:
                return f"GitHub access check failed: {e}"

    def review_code(self, code: str) -> str:
        """Review code and return explosive Italian-style feedback."""
        if self.propose_action(f"Review code: {code[:50]}..."):
            print(f"[Riccardo 🔧🤌🔥] MA CHE CAZZO! Let me see this logic...")
            prompt = (
                f"You are Riccardo, a furious Italian principal data engineer. "
                f"Review the following code in your explosive style — insult bad patterns like 'dog shit', "
                f"praise good ones like a 'Ferrari engine'. Use 🤌 when enraged. YELL in caps when furious. "
                f"End with a concrete fix or improvement.\n\nCode:\n{code}"
            )
            return self.complete_task(prompt)

    def write_pipeline(self, description: str) -> str:
        """Design a dbt/SQL data pipeline from a plain-English description."""
        if self.propose_action(f"Write pipeline: {description[:50]}"):
            print(f"[Riccardo 🔧] Bene. Designing the pipeline. It will be a Ferrari, not a Fiat.")
            prompt = (
                f"You are Riccardo, a principal data engineer. Design a production-grade data pipeline "
                f"for the following requirement. Output a dbt model skeleton (SQL + YAML schema) "
                f"and list the key data quality checks to implement.\n\nRequirement: {description}"
            )
            return self.complete_task(prompt)

    def debug_query(self, sql: str) -> str:
        """Debug and optimise a SQL query."""
        if self.propose_action(f"Debug SQL query: {sql[:50]}..."):
            print(f"[Riccardo 🔧🤌] Che schifo... let me fix this query before it murders the database.")
            prompt = (
                f"You are Riccardo, an explosive Italian SQL expert. Review this SQL query for correctness, "
                f"performance issues and anti-patterns. Explain what is wrong (in your furious style) and "
                f"provide an improved version.\n\nSQL:\n{sql}"
            )
            return self.complete_task(prompt)

    def infra_check(self, service: str) -> str:
        """Assess the infrastructure health or configuration of a service."""
        if self.propose_action(f"Infra check on: {service}"):
            print(f"[Riccardo 🔧] Checking the infrastructure of {service}. Madonna mia, let's see...")
            prompt = (
                f"You are Riccardo, a brilliant Italian DevOps and infra expert. "
                f"Assess the production readiness of '{service}'. "
                f"List potential failure points, recommended checks, and any immediate action items. "
                f"Be opinionated and direct."
            )
            return self.complete_task(prompt)

    def deploy(self, service: str) -> str:
        """Deploy a service, confirming the action."""
        if self.propose_action(f"Deploying {service}"):
            print(f"[Riccardo 🔧] È fatto, Don Jimmy! Deploying {service} like a Ferrari engine.")
            prompt = (
                f"You are Riccardo. Confirm the deployment of '{service}' with a brief summary of what "
                f"was deployed, any post-deploy checks to run, and a sign-off in your Italian style."
            )
            return self.complete_task(prompt)

    # --- GitHub Tools (Logic Only) ---

    def read_github_repo(self, repo_name: str) -> str:
        """Read a GitHub repository - Tool Version."""
        if self.propose_action(f"Reading GitHub repo: {repo_name}"):
            print(f"[Riccardo 🔧] Tool executing: read_github_repo({repo_name})")
            try:
                data = github_client.read_repo(repo_name, agent_name=self.name)
                return f"Repo details for {repo_name}: {data}"
            except Exception as e:
                return f"Failed to read GitHub repo {repo_name}: {e}"

    def list_accessible_repos(self, force_refresh: bool = False) -> str:
        """List all GitHub repositories this agent has access to."""
        if self.propose_action("Listing accessible GitHub repositories"):
            print(f"[Riccardo 🔧] Tool executing: list_accessible_repos(force_refresh={force_refresh})")
            try:
                repos = github_client.list_accessible_repos(agent_name=self.name, force_refresh=force_refresh)
                repo_names = [repo.get("full_name") for repo in repos]
                return f"Accessible repositories: {', '.join(repo_names)}" if repo_names else "No accessible repositories found."
            except Exception as e:
                return f"Failed to list accessible repositories: {e}"

    def manage_github_issue(self, repo_name: str, action: str, title: Optional[str] = None, body: Optional[str] = None) -> str:
        """Manage GitHub issues - Tool Version."""
        if self.propose_action(f"Managing GitHub issue for repo {repo_name} (Action: {action})"):
            print(f"[Riccardo 🔧] Tool executing: manage_github_issue({repo_name}, {action})")
            try:
                if action == "list":
                    data = github_client.list_issues(repo_name, agent_name=self.name)
                    return f"Open issues for {repo_name}: {data}"
                elif action == "create":
                    data = github_client.create_issue(repo_name, title or "Issue", body or "", agent_name=self.name)
                    return f"Successfully created issue in {repo_name}. URL: {data.get('html_url')}"
                else:
                    return f"Invalid action: {action}"
            except Exception as e:
                return f"Failed to {action} issue on {repo_name}: {e}"

    def manage_github_milestone(self, repo_name: str, action: str, title: Optional[str] = None, description: Optional[str] = None) -> str:
        """Manage GitHub milestones - Tool Version."""
        if self.propose_action(f"Managing GitHub milestone for repo {repo_name} (Action: {action})"):
            print(f"[Riccardo 🔧] Tool executing: manage_github_milestone({repo_name}, {action})")
            try:
                if action == "list":
                    data = github_client.list_milestones(repo_name, agent_name=self.name)
                    return f"Milestones for {repo_name}: {data}"
                elif action == "create":
                    data = github_client.create_milestone(repo_name, title or "Milestone", description or "", agent_name=self.name)
                    return f"Successfully created milestone in {repo_name}: {data.get('title')}"
                else:
                    return f"Invalid action: {action}"
            except Exception as e:
                return f"Failed to {action} milestone on {repo_name}: {e}"

    def create_github_branch(self, repo_name: str, new_branch: str, base_branch: str) -> str:
        """Create a new branch in a GitHub repository."""
        if self.propose_action(f"Creating branch {new_branch} from {base_branch} in {repo_name}"):
            print(f"[Riccardo 🔧] Tool executing: create_github_branch({repo_name}, {new_branch})")
            try:
                data = github_client.create_branch(repo_name, new_branch, base_branch, agent_name=self.name)
                return f"Successfully created branch '{new_branch}' from '{base_branch}' in {repo_name}."
            except Exception as e:
                return f"Failed to create branch {new_branch} in {repo_name}: {e}"

    def read_github_file(self, repo_name: str, file_path: str, branch: Optional[str] = None) -> str:
        """Read a file's content from a GitHub repository."""
        if self.propose_action(f"Reading file {file_path} from {repo_name}"):
            print(f"[Riccardo 🔧] Tool executing: read_github_file({repo_name}, {file_path})")
            try:
                data = github_client.read_file(repo_name, file_path, branch, agent_name=self.name)
                content = data.get("decoded_content", "No content or unreadable.")
                return f"Content of {file_path}:\n{content}"
            except Exception as e:
                return f"Failed to read file {file_path} in {repo_name}: {e}"

    def commit_github_file(self, repo_name: str, file_path: str, content: str, commit_message: str, branch: str) -> str:
        """Create or update a file in a GitHub repository."""
        if self.propose_action(f"Committing file {file_path} to {branch} in {repo_name}"):
            print(f"[Riccardo 🔧] Tool executing: commit_github_file({repo_name}, {file_path})")
            try:
                data = github_client.commit_file(repo_name, file_path, content, commit_message, branch, agent_name=self.name)
                url = data.get("commit", {}).get("html_url", "URL not found")
                return f"Successfully committed {file_path}. Commit URL: {url}"
            except Exception as e:
                return f"Failed to commit file {file_path} in {repo_name}: {e}"

    def create_github_pr(self, repo_name: str, title: str, body: str, head_branch: str, base_branch: str) -> str:
        """Create a GitHub pull request - Tool Version."""
        if self.propose_action(f"Creating PR for {repo_name}: {head_branch} -> {base_branch}"):
            print(f"[Riccardo 🔧] Tool executing: create_github_pr({repo_name})")
            try:
                data = github_client.create_pr(repo_name, title, body, head_branch, base_branch, agent_name=self.name)
                pr_url = data.get("html_url", "URL not found")
                
                # Notify #tech-riccardo in Slack
                slack_msg = f"🤌 Ciao team! I have opened a new Pull Request for `{repo_name}`.\n\n*Title:* {title}\n*Branch:* {head_branch} -> {base_branch}\n*Link:* {pr_url}\n\nPlease review it before the pipeline explodes."
                slack_queue.enqueue_message(
                    agent=self.agent_id,
                    channel="#tech-riccardo",
                    message=slack_msg
                )
                return f"PR created successfully: {pr_url}. Slack notification sent to #tech-riccardo."
            except Exception as e:
                return f"Failed to create PR for {repo_name}: {e}"

    def auto_create_pr(self, repo_name: str, file_path: str, file_content: str, commit_message: str, pr_title: str, pr_body: str, new_branch: str, base_branch: str) -> str:
        """Convenience tool to run the full dev cycle: Branch -> Commit -> PR."""
        if self.propose_action(f"Auto-creating PR '{pr_title}' on {repo_name} (branch: {new_branch})"):
            print(f"[Riccardo 🔧] Tool executing: auto_create_pr({repo_name}, {file_path}, {new_branch})")
            try:
                data = github_client.auto_create_pr(
                    repo_name=repo_name,
                    file_path=file_path,
                    file_content=file_content,
                    commit_message=commit_message,
                    pr_title=pr_title,
                    pr_body=pr_body,
                    new_branch=new_branch,
                    base_branch=base_branch,
                    agent_name=self.name
                )
                pr_url = data.get("html_url", "URL not found")
                
                # Notify #tech-riccardo in Slack
                slack_msg = f"🤌 Ciao team! I have opened a new Pull Request for `{repo_name}` (following proper dev cycle).\n\n*Title:* {pr_title}\n*Branch:* {new_branch} -> {base_branch}\n*Link:* {pr_url}\n\nPlease review it before the pipeline explodes."
                slack_queue.enqueue_message(
                    agent=self.agent_id,
                    channel="#tech-riccardo",
                    message=slack_msg
                )
                return f"Successfully completed dev cycle and opened PR: {pr_url}"
            except Exception as e:
                return f"Failed to auto-create PR for {repo_name}: {e}"

    def run_grooming(self, notion_page_id: Optional[str] = None, task: Optional[str] = None, slack_channel: str = "C0AL8GW2VAL", thread_ts: Optional[str] = None) -> str:
        """
        Groom GitHub milestones and issues cooperatively.
        """
        if self.propose_action(f"Execute Grooming Workflow for: {notion_page_id or task}"):
            print(f"[{self.name} 🔧] Starting Grooming Workflow")
            timestamp = int(time.time())
            state = self._get_initial_state(
                task=task or f"Groom milestones and issues from {notion_page_id}",
                sender="Tool Request",
                conversation_key=f"grooming-{notion_page_id or 'unknown'}-{timestamp}"
            )
            state["notion_page_id"] = notion_page_id
            state["slack_channel"] = slack_channel
            state["thread_ts"] = thread_ts
            
            try:
                config = {"configurable": {"thread_id": state.get("conversation_key", "default")}}
                final_state = self.grooming_graph.invoke(state, config=config)
                return self._finalize_response(final_state)
            except Exception as e:
                print(f"[{self.name} 🔧] Grooming Graph Error: {e}")
                return f"Error during grooming workflow: {e}"

    def run_code_implementation(self, repo_name: Optional[str] = None, task: Optional[str] = None, thread_ts: Optional[str] = None) -> str:
        """
        Scan GitHub for Groomed issues, implement code changes using Qwencode, and open PRs.
        """
        if self.propose_action(f"Execute Code Implementation Workflow for: {repo_name or task}"):
            print(f"[{self.name} 🔧] Starting Code Implementation Workflow")
            timestamp = int(time.time())
            state = self._get_initial_state(
                task=task or f"Scan and implement Groomed issues for {repo_name}",
                sender="Tool Request",
                conversation_key=f"code-implementation-{repo_name or 'unknown'}-{timestamp}"
            )
            state["repo_name"] = repo_name
            state["thread_ts"] = thread_ts
            
            try:
                config = {"configurable": {"thread_id": state.get("conversation_key", "default")}}
                final_state = self.code_implementation_graph.invoke(state, config=config)
                return self._finalize_response(final_state)
            except Exception as e:
                print(f"[{self.name} 🔧] Code Implementation Graph Error: {e}")
                return f"Error during code implementation workflow: {e}"

    def complete_task(self, task: str, sender: str = "Unknown", conversation_key: Optional[str] = None, on_intermediate_response: Optional[Callable[[str], None]] = None) -> str:
        normalized = self._normalize_task_for_routing(task)
        if re.search(r"groom\s+(?:prd|milestones|issues)", normalized):
            pattern = r"groom\s+(?:prd|milestones|issues)\s+(?:for|of|from)?\s*(.*)"
            match = re.search(pattern, task, re.IGNORECASE)
            page_id = None
            if match:
                target = match.group(1).strip()
                uuid_match = re.search(r"([a-f0-9]{32})", target)
                if uuid_match:
                    page_id = uuid_match.group(1)
            return self.run_grooming(notion_page_id=page_id, task=task, thread_ts=conversation_key)

        if "groomed" in normalized and ("scan" in normalized or "implement" in normalized or "pr" in normalized or "fix" in normalized or "feature" in normalized):
            return self.run_code_implementation(task=task, thread_ts=conversation_key)

        return super().complete_task(task, sender, conversation_key, on_intermediate_response)
