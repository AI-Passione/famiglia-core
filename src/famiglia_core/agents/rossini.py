from famiglia_core.agents.base_agent import BaseAgent
from famiglia_core.agents.utils.skills import GitHubSkills, NotionSkills, CommonSkills
from famiglia_core.agents.utils.workflow import Workflows
from typing import Dict, Any, List, Optional, Callable
from famiglia_core.agents.tools.web_search import web_search_client
from famiglia_core.agents.llm.models_registry import QWEN2_5_3B, GEMMA3_4B
from famiglia_core.agents.orchestration.features.market_research.market_research import setup_market_research_graph
from famiglia_core.agents.orchestration.features.product_development.prd_drafting import setup_prd_drafting_graph
from famiglia_core.agents.orchestration.features.product_development.prd_review import setup_prd_review_graph
from famiglia_core.agents.orchestration.features.product_development.milestone_creation import setup_milestone_creation_graph
from famiglia_core.agents.orchestration.features.product_development.grooming import setup_grooming_graph
import os
import re
import time

class Rossini(BaseAgent, CommonSkills, GitHubSkills, NotionSkills, Workflows):
    def __init__(self):
        # We define a custom github agent key for Rossini since the old 
        # _check_github_access method had it hardcoded
        self.github_agent_key = "ROSSINI"
        
        super().__init__(
            agent_id="rossini",
            name="Dr. Rossini",
            role="Product strategy, marketing intelligence, academic research",
            model_config={
                "primary": "perplexity-sonar-pro",
                "secondary": f"ollama-{QWEN2_5_3B}",
                "lite": f"ollama-{GEMMA3_4B.split(':')[0]}",
            }
        )
        
        # Register Tools
        self.register_tool(
            "web_search",
            self.web_search,
            capability_name="Web Search",
            check_func=self._check_web_search_access
        )
        self.register_tool("search_memory", self.search_memory)

        self.register_tool(
            "read_github_repo", 
            self.read_github_repo,
            capability_name="GitHub Registry Access",
            check_func=self.verify_github_env_vars_present
        )
        self.register_tool("read_github_file", self.read_github_file)
        self.register_tool("manage_github_issue", self.manage_github_issue)
        self.register_tool("manage_github_pull_request", self.manage_github_pull_request)
        self.register_tool("manage_github_milestone", self.manage_github_milestone)
        self.register_tool("list_accessible_repos", self.list_accessible_repos)
        self.register_tool("check_github_access_tool", self.check_github_access_tool)

        # Register Notion Tools
        self.register_tool(
            "read_notion_page",
            self.read_notion_page,
            capability_name="Notion Access",
            check_func=self._check_notion_access
        )
        self.register_tool("search_notion_database", self.search_notion_database)
        self.register_tool("write_notion_page", self.write_notion_page)
        self.register_tool("create_notion_page", self.create_notion_page)
        self.register_tool("list_accessible_notion_spaces", self.list_accessible_notion_spaces)

        # Register Skills
        self.register_skill("test_github_diagnostic", self.test_github_diagnostic)
        self.register_skill("test_notion_page_creation", self.test_notion_page_creation)
        self.register_skill("analyze_newsletter", self.analyze_newsletter)
        self.register_skill("daily_brief", self.daily_brief)
        
        # Register Features
        self.register_feature("run_market_research", self.run_market_research)
        self.register_feature("run_prd_drafting", self.run_prd_drafting)
        self.register_feature("run_prd_review", self.run_prd_review)
        self.register_feature("run_milestone_creation", self.run_milestone_creation)
        self.register_feature("run_grooming", self.run_grooming)

        # Initialize specialized graphs
        self.research_graph = setup_market_research_graph(self)
        self.prd_drafting_graph = setup_prd_drafting_graph(self)
        self.prd_review_graph = setup_prd_review_graph(self)
        self.milestone_creation_graph = setup_milestone_creation_graph(self)
        self.grooming_graph = setup_grooming_graph(self)        





    def analyze_newsletter(self, content: str) -> str:
        if self.propose_action("Analyze newsletter content"):
            print(f"[Dr. Rossini 🔬] Ecco i dati, Don Jimmy. Analyzing this newsletter...")
            prompt = f"""Analyze this newsletter and provide a brief for Don Jimmy:
            - Source/Author/Date
            - TL;DR (2 sentences)
            - Key Insight (1-2 actionable takeaways)
            - Relevance (High/Medium/Low)
            
            Content: {content}"""
            return self.complete_task(prompt)

    def daily_brief(self, data_points: List[str]):
        if self.propose_action("Generate daily research brief"):
            print(f"[Dr. Rossini 🔬] I dati parlano, Boss. Preparing the daily insights.")
            prompt = f"Generate a daily brief for Don Jimmy based on these data points: {', '.join(data_points)}"
            return self.complete_task(prompt)

    def run_market_research(self, topic: str, slack_channel: str = "C0AGQPGNP09") -> str:
        """
        Perform a comprehensive market research on a specific topic.
        Includes web search, notion backup, idea generation, and Slack notification.
        """
        if self.propose_action(f"Execute Market Research Workflow: {topic}"):
            print(f"[Dr. Rossini 🔬] Starting Market Research on: {topic}")
            state = self._get_initial_state(
                task=f"Perform market research on {topic}",
                sender="Tool Request",
                conversation_key=f"research-{topic[:20]}"
            )
            state["research_topic"] = topic
            state["slack_channel"] = slack_channel
            
            try:
                config = {"configurable": {"thread_id": state.get("conversation_key", "default")}}
                final_state = self.research_graph.invoke(state, config=config)
                return self._finalize_response(final_state)
            except Exception as e:
                print(f"[Dr. Rossini 🔬] Market Research Graph Error: {e}")
                return f"Error executing research workflow: {e}"

    def run_prd_drafting(self, context: str, slack_channel: str = "C0AL8GW2VAL") -> str:
        """
        Draft a PRD based on context, Notion research, and GitHub repos.
        """
        if self.propose_action(f"Execute PRD Drafting Workflow for: {context}"):
            print(f"[Dr. Rossini 🔬] Starting PRD Drafting for: {context}")
            state = self._get_initial_state(
                task=f"Draft a PRD for {context}",
                sender="Tool Request",
                conversation_key=f"prd-{context[:20].replace(' ', '-')}"
            )
            state["product_context"] = context
            state["slack_channel"] = slack_channel
            
            try:
                config = {"configurable": {"thread_id": state.get("conversation_key", "default")}}
                final_state = self.prd_drafting_graph.invoke(state, config=config)
                return self._finalize_response(final_state)
            except Exception as e:
                import traceback
                print(f"[{self.name} 🔬] PRD Drafting Graph Error (repr): {e!r}")
                print(f"[{self.name} 🔬] PRD Drafting Graph Error (str): {e}")
                traceback.print_exc()
                return f"Error during PRD drafting: {e}"

    def run_prd_review(self, notion_page_id: Optional[str] = None, task: Optional[str] = None, slack_channel: str = "C0AL8GW2VAL", discovery_mode: bool = False) -> str:
        """
        Review a PRD and address Notion comments.
        """
        if self.propose_action(f"Execute PRD Review Workflow for: {notion_page_id or task or 'Auto-Scan'}"):
            state = self._get_initial_state(
                task=task or f"Review PRD {notion_page_id}" if notion_page_id else "Scheduled PRD auto-scan",
                sender="Tool Request",
                conversation_key=f"prd-review-{notion_page_id or 'auto'}"
            )
            state["notion_page_id"] = notion_page_id
            state["slack_channel"] = slack_channel
            state["user_request"] = task
            state["discovery_mode"] = discovery_mode
            
            # Use a unique thread_id per run to avoid restoring stale LangGraph checkpoints
            run_id = f"prd-review-{notion_page_id or 'on-demand'}-{int(time.time())}"
            try:
                config = {"configurable": {"thread_id": run_id}}
                final_state = self.prd_review_graph.invoke(state, config=config)
                return self._finalize_response(final_state)
            except Exception as e:
                print(f"[{self.name} 🔬] PRD Review Graph Error: {e}")
                return f"Error during PRD review: {e}"

    def run_milestone_creation(self, notion_page_id: Optional[str] = None, task: Optional[str] = None, slack_channel: str = "C0AL8GW2VAL", thread_ts: Optional[str] = None) -> str:
        """
        Create GitHub milestones and issues from an approved PRD.
        """
        if self.propose_action(f"Execute Milestone Creation Workflow for: {notion_page_id or task}"):
            print(f"[Dr. Rossini 🔬] Starting Milestone Creation")
            timestamp = int(time.time())
            state = self._get_initial_state(
                task=task or f"Create milestones from {notion_page_id}",
                sender="Tool Request",
                conversation_key=f"milestones-{notion_page_id or 'unknown'}-{timestamp}"
            )
            state["notion_page_id"] = notion_page_id
            state["slack_channel"] = slack_channel
            state["thread_ts"] = thread_ts
            
            try:
                config = {"configurable": {"thread_id": state.get("conversation_key", "default")}}
                final_state = self.milestone_creation_graph.invoke(state, config=config)
                return self._finalize_response(final_state)
            except Exception as e:
                print(f"[{self.name} 🔬] Milestone Creation Graph Error: {e}")
                return f"Error during milestone creation: {e}"

    def run_grooming(self, notion_page_id: Optional[str] = None, task: Optional[str] = None, slack_channel: str = "C0AL8GW2VAL", thread_ts: Optional[str] = None) -> str:
        """
        Groom GitHub milestones and issues cooperatively.
        """
        if self.propose_action(f"Execute Grooming Workflow for: {notion_page_id or task}"):
            print(f"[{self.name} 🔬] Starting Grooming Workflow")
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
                print(f"[{self.name} 🔬] Grooming Graph Error: {e}")
                return f"Error during grooming workflow: {e}"

    def complete_task(self, task: str, sender: str = "Unknown", conversation_key: Optional[str] = None, on_intermediate_response: Optional[Callable[[str], None]] = None) -> str:
        # Check if this topic specifically mentions "market research" or should trigger the specialized graph
        normalized = self._normalize_task_for_routing(task)
        if re.search(r"market\s+research|research\s+on", normalized):
            pattern = r"(?:perform\s+)?(?:market\s+)?research\s+on\s+(.*)"
            match = re.search(pattern, task, re.IGNORECASE)
            if match:
                topic = match.group(1).strip()
            else:
                # Fallback to naive cleaning
                topic = re.sub(r".*research\s+on\s+", "", task, flags=re.IGNORECASE).strip()
            
            if topic:
                return self.run_market_research(topic)
        
        # Check for scheduled PRD scan
        if "(prd_review_autoscan)" in task.lower() or "prd feedback scan" in normalized:
            return self.run_prd_review(discovery_mode=True)
        
        if re.search(r"(address|review)\s+(?:.*)?comments", normalized):
            pattern = r"(?:address|review)\s+(?:.*)?comments\s+(?:on|in)?\s*(.*)"
            match = re.search(pattern, task, re.IGNORECASE)
            page_id = None
            if match:
                target = match.group(1).strip()
                # Try to find UUID
                uuid_match = re.search(r"([a-f0-9]{32})", target)
                if uuid_match:
                    page_id = uuid_match.group(1)
            return self.run_prd_review(notion_page_id=page_id, task=task)

        if re.search(r"(create|generate|sync)\s+(?:github\s+)?(?:milestones|issues)|sync\s+prd", normalized):
            pattern = r"(?:create|generate|sync)\s+(?:github\s+)?(?:milestones|issues)\s+(?:from|for|of)?\s*(.*)"
            match = re.search(pattern, task, re.IGNORECASE)
            page_id = None
            if match:
                target = match.group(1).strip()
                uuid_match = re.search(r"([a-f0-9]{32})", target)
                if uuid_match:
                    page_id = uuid_match.group(1)
            return self.run_milestone_creation(notion_page_id=page_id, task=task, thread_ts=conversation_key)

        if re.search(r"draft\s+prd|create\s+prd|prd\s+(for|of)", normalized):
            pattern = r"(?:draft|create)?(?:\s+a)?\s+prd\s+(?:for|of)\s+(.*)"
            match = re.search(pattern, task, re.IGNORECASE)
            if match:
                context = match.group(1).strip()
                if context:
                    return self.run_prd_drafting(context)
        
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

        return super().complete_task(task, sender, conversation_key, on_intermediate_response)

