from typing import Any, Dict, List, Optional, TypedDict
from langgraph.graph import StateGraph, END
import os
import re

from famiglia_core.agents.orchestration.utils.state import AgentState
from famiglia_core.agents.llm.client import client
from famiglia_core.agents.tools.notion import notion_client
from famiglia_core.command_center.backend.slack.client import slack_queue

class PRDDraftingState(AgentState):
    """Extension of AgentState for specialized PRD Drafting tasks."""
    product_context: str
    product_subject: str
    prd_title: str
    notion_intelligence: str
    notion_summary: str
    github_intelligence: str
    github_summary: str
    web_intelligence: str
    web_summary: str
    synthesis: str
    prd_markdown: str
    notion_page_id: str
    notion_url: str
    slack_channel: str
    retry_count: int
    last_error: str
    notion_success: bool

class PRDDraftingWorkflow:
    """
    Logic for the PRD Drafting LangGraph.
    """
    
    def __init__(self, agent):
        self.agent = agent
        self.name = agent.name
        self.model_config = agent.model_config
        self.personality = self._load_rossini_personality()
        self.template_path = os.path.join(
            os.getcwd(), 
            "src/agents/orchestration/features/templates/prd_template.md"
        )

    def _load_rossini_personality(self) -> str:
        """Loads Dr. Rossini's persona for context."""
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

    def understand_context(self, state: PRDDraftingState) -> PRDDraftingState:
        """Node 1: Extract and refine the product context from the task."""
        print(f"[{self.name}] PRD Node: understand_context")
        task = state.get("task")
        
        prompt = f"""
        {self.personality}
        
        Task: Analyze the following request: "{task}"
        
        Extract:
        1. "Product Subject": The literal name or noun of the product/feature (e.g., 'Jimwurst', 'Loyalty App').
        2. "Product Context": A clear description based strictly on the user's words.
        3. "PRD Title": A short, punchy title (max 5 words).
        
        Output format:
        SUBJECT: [Literal Name]
        CONTEXT: [Description]
        TITLE: [Short PRD Title]
        """
        
        res, _ = client.complete(prompt, self.agent.get_model_config(state), agent_name=self.name)
        
        updates = {}
        subject_match = re.search(r"SUBJECT:\s*(.*)", res, re.IGNORECASE)
        context_match = re.search(r"CONTEXT:\s*(.*)", res, re.IGNORECASE)
        title_match = re.search(r"TITLE:\s*(.*)", res, re.IGNORECASE)
        
        if subject_match:
            updates["product_subject"] = subject_match.group(1).strip()
        else:
            updates["product_subject"] = "Unknown"
            
        if context_match:
            updates["product_context"] = context_match.group(1).strip()
        else:
            updates["product_context"] = res.strip()
            
        if title_match:
            updates["prd_title"] = title_match.group(1).strip()
        else:
            updates["prd_title"] = updates.get("product_subject", "New PRD")[:30]
            
        return updates

    def gather_notion_intelligence(self, state: PRDDraftingState) -> PRDDraftingState:
        """Node 2a: Read from Notion (Market Researches)."""
        print(f"[{self.name}] PRD Node: gather_notion_intelligence")
        subject = state.get("product_subject", "")
        
        intelligence = ""
        try:
            # Use general search focusing on the subject name
            results = notion_client.search(query=subject, agent_name=self.name)
            if results:
                # Filter for things that look like research or match the context well
                page_id = results[0]["id"]
                content_dict = notion_client.read_page(page_id, agent_name=self.name)
                # content_dict is {"page_properties": {}, "blocks": []}
                blocks = content_dict.get("blocks", [])
                body = "\n".join(blocks)
                intelligence = f"Related Notion Content Found ({results[0].get('url')}):\n{body}"
        except Exception as e:
            print(f"[{self.name}] Notion Intelligence gathering failed: {e}")

        return {"notion_intelligence": intelligence or "No specific Notion intelligence found."}

    def gather_github_intelligence(self, state: PRDDraftingState) -> PRDDraftingState:
        """Node 2b: Deep-dive into Github for technical context."""
        print(f"[{self.name}] PRD Node: gather_github_intelligence (Deep-dive)")
        subject = state.get("product_subject", "")
        
        intelligence_parts = []
        try:
            # 1. Find the best repo
            repos_str = self.agent.list_accessible_repos()
            pick_prompt = f"Given the product subject '{subject}', which repository from this list is most likely to contain its source code?\n\nRepos: {repos_str}\n\nOutput ONLY the repository name. If none match, output 'NONE'."
            repo_name, _ = client.complete(pick_prompt, self.agent.get_model_config(state), agent_name=self.name)
            repo_name = repo_name.strip()
            
            if repo_name and repo_name != "NONE":
                print(f"[{self.name}] GitHub Deep-dive: {repo_name}")
                
                # 2. Get Repo Metadata
                repo_info = self.agent.read_github_repo(repo_name)
                intelligence_parts.append(f"### Repository Metadata\n{repo_info}")
                
                # 3. Read README
                readme = self.agent.read_github_file(repo_name, "README.md")
                intelligence_parts.append(f"### README.md\n{readme}")
                
                # 4. Check Issues (Activity Context)
                issues = self.agent.manage_github_issue(repo_name, action="list")
                intelligence_parts.append(f"### Recent Issues/Activity\n{issues}")
                
                # 5. Check Pull Requests (Development Context)
                prs = self.agent.manage_github_pull_request(repo_name, action="list")
                intelligence_parts.append(f"### Recent Pull Requests\n{prs}")
                
                intelligence = "\n\n".join(intelligence_parts)
            else:
                intelligence = f"No specific matching repository found. Accessible repos: {repos_str}"
        except Exception as e:
            print(f"[{self.name}] GitHub Deep-dive failed: {e}")
            intelligence = f"GitHub gathering failed partially: {e}"

        return {"github_intelligence": intelligence or "No GitHub intelligence found."}
        
    def gather_web_intelligence(self, state: PRDDraftingState) -> PRDDraftingState:
        """Node 2c: Search the web for market context and trends."""
        print(f"[{self.name}] PRD Node: gather_web_intelligence")
        subject = state.get("product_subject", "")
        
        intelligence = ""
        try:
            query = f"{subject} product market research trends competitors"
            res = self.agent.web_search(query)
            intelligence = f"Web Intelligence for '{subject}':\n{res}"
        except Exception as e:
            print(f"[{self.name}] Web research failed: {e}")
            intelligence = f"Web research failed: {e}"

        return {"web_intelligence": intelligence or "No web intelligence found."}

    def summarize_notion(self, state: PRDDraftingState) -> PRDDraftingState:
        """Node 2d: Summarize Notion intelligence."""
        print(f"[{self.name}] PRD Node: summarize_notion")
        intelligence = state.get("notion_intelligence", "")
        if not intelligence or "No specific Notion intelligence" in intelligence:
            return {"notion_summary": "No Notion intelligence available."}
        
        prompt = f"Summarize the following Notion research content for a PRD drafting context:\n\n{intelligence}"
        res, _ = client.complete(prompt, self.agent.get_model_config(state), agent_name=self.name)
        return {"notion_summary": res}

    def summarize_github(self, state: PRDDraftingState) -> PRDDraftingState:
        """Node 2e: Summarize GitHub intelligence."""
        print(f"[{self.name}] PRD Node: summarize_github")
        intelligence = state.get("github_intelligence", "")
        if not intelligence or "No specific matching repository" in intelligence:
            return {"github_summary": "No technical GitHub intelligence available."}
            
        prompt = f"Summarize the following GitHub technical data (README, issues, PRs) for a PRD drafting context:\n\n{intelligence}"
        res, _ = client.complete(prompt, self.agent.get_model_config(state), agent_name=self.name)
        return {"github_summary": res}

    def summarize_web(self, state: PRDDraftingState) -> PRDDraftingState:
        """Node 2f: Summarize Web intelligence."""
        print(f"[{self.name}] PRD Node: summarize_web")
        intelligence = state.get("web_intelligence", "")
        if not intelligence or "No web intelligence found" in intelligence:
            return {"web_summary": "No market web intelligence available."}
            
        prompt = f"Summarize the following web search research for a PRD drafting context:\n\n{intelligence}"
        res, _ = client.complete(prompt, self.agent.get_model_config(state), agent_name=self.name)
        return {"web_summary": res}

    def synthesize(self, state: PRDDraftingState) -> PRDDraftingState:
        """Node 3: Synthesize intelligence and context using both summaries and raw data."""
        print(f"[{self.name}] PRD Node: synthesize")
        context = state.get("product_context")
        notion_summary = state.get("notion_summary", "")
        notion_raw = state.get("notion_intelligence", "")
        github_summary = state.get("github_summary", "")
        github_raw = state.get("github_intelligence", "")
        web_summary = state.get("web_summary", "")
        web_raw = state.get("web_intelligence", "")
        
        prompt = f"""
        {self.personality}
        
        Task: Synthesize the technical and market foundation for a PRD using the following sources.
        
        Use the SUMMARIES as your primary lens for the strategic overview, but refer to the RAW DATA for specific technical details, URLs, or specific market figures.
        
        CRITICAL RULE: Prioritize the GATHERED INTELLIGENCE over your internal general knowledge. 
        
        Original Context: {context}
        
        --- NOTION ---
        Summary: {notion_summary}
        Raw Data Snippet: {notion_raw[:2000] if notion_raw else "N/A"}
        
        --- GITHUB ---
        Summary: {github_summary}
        Raw Data Snippet: {github_raw[:3000] if github_raw else "N/A"}
        
        --- WEB ---
        Summary: {web_summary}
        Raw Data Snippet: {web_raw[:2000] if web_raw else "N/A"}
        
        Your Goal:
        1. Resolve exactly what this product/feature IS based on the evidence.
        2. Identify the core problem it solves.
        3. Outline technical feasibility or existing infrastructure found in GitHub.
        4. Define strategic value.
        
        Output the synthesis in structured Markdown.
        """
        
        res, _ = client.complete(prompt, self.agent.get_model_config(state), agent_name=self.name)
        return {"synthesis": res}

    def draft_prd(self, state: PRDDraftingState) -> PRDDraftingState:
        """Node 4: Draft the PRD using a template."""
        print(f"[{self.name}] PRD Node: draft_prd")
        synthesis = state.get("synthesis")
        context = state.get("product_context")
        
        # Load template
        template = ""
        if os.path.exists(self.template_path):
            with open(self.template_path, "r") as f:
                template = f.read()
        
        prompt = f"""
        {self.personality}
        
        Task: Draft a professional Product Requirement Document (PRD) for: {context}
        
        Use the following template:
        {template}
        
        Strategic Foundation:
        {synthesis}
        
        > [!IMPORTANT]
        > **Verification Status:** 🔴 Unverified (Awaiting Approval)
        > **Last Updated:** 2026-03-17
        
        CRITICAL: If you include tables, do NOT add blank lines between the table header and the separator row, or between data rows. 
        Ensure tables are strictly formatted as standard Markdown.
        
        Output only the Markdown PRD.
        """
        
        res, _ = client.complete(prompt, self.agent.get_model_config(state), agent_name=self.name)
        return {"prd_markdown": res}

    def save_to_notion(self, state: PRDDraftingState) -> PRDDraftingState:
        """Node 5: Save to Notion under PRD parent."""
        print(f"[{self.name}] PRD Node: save_to_notion")
        
        prd_parent_id = "325f5d41fe9780529f34c16d78e252c8" # Provided by user
        title = f"PRD: {state.get('prd_title')}"
        content = state.get("prd_markdown")
        
        updates = {}
        try:
            result_str = notion_client.create_page(prd_parent_id, title, content, agent_name=self.name)
            import re
            id_match = re.search(r"ID:\s*([^\s.]+)", result_str)
            url_match = re.search(r"URL:\s*([^\s]+)", result_str)
            
            if id_match:
                updates["notion_page_id"] = id_match.group(1)
            if url_match:
                updates["notion_url"] = url_match.group(1)
                
            updates["notion_success"] = True
            return updates
        except Exception as e:
            print(f"[{self.name}] Notion Save Failed: {e}")
            return {
                "last_error": str(e),
                "notion_success": False
            }

    def notify_slack(self, state: PRDDraftingState) -> PRDDraftingState:
        """Node 6: Notify Slack #product-rossini."""
        print(f"[{self.name}] PRD Node: notify_slack")
        
        channel = state.get("slack_channel") or "C0AL8GW2VAL" # #product-rossini
        context = state.get("product_context")
        notion_url = state.get("notion_url", "")
        notion_success = state.get("notion_success", False)
        
        notion_status = f"PRD has been drafted and saved to Notion: {notion_url}" if notion_success else "⚠️ Note: I encountered an error saving the PRD to Notion, but it is ready for review."
        
        summary_prompt = f"""
        {self.personality}
        
        Task: Create a concise, professional Slack announcement for Don Jimmy about the new PRD.
        Product: {context}
        Status: {notion_status}
        
        Rules:
        - Do NOT include headers like "Slack Message:" or "Subject:".
        - Use emojis sparingly and professionally.
        - Be direct and warm.
        - Output ONLY the message text itself.
        """
        
        slack_msg, _ = client.complete(summary_prompt, self.agent.get_model_config(state), agent_name=self.name)
        
        try:
            message = f"🔬 *PRD Drafting Update: {context}*\n\n{slack_msg}"
            if notion_success:
                message += f"\n\n🔗 *Access Document:* {notion_url}"
                
            slack_queue.post_message(
                agent=self.agent.agent_id,
                channel=channel,
                message=message
            )
        except Exception as e:
            print(f"[{self.name}] Slack Notification Failed: {e}")
        return {
            "final_response": f"I have completed the PRD draft for '{context}'.\n\nNotification sent to #product-rossini. " + (f"Link: {notion_url}" if notion_success else "Notion save failed.")
        }

from famiglia_core.db.observability.checkpointer import PostgresCheckpointer

def setup_prd_drafting_graph(agent):
    """Builds and compiles the PRD Drafting StateGraph with persistence."""
    print(f"[{agent.name}] PRD Drafting: Setting up graph...", flush=True)
    workflow_logic = PRDDraftingWorkflow(agent)
    
    workflow = StateGraph(PRDDraftingState)
    
    # ... (nodes and edges stay the same)
    workflow.add_node("understand_context", workflow_logic.understand_context)
    workflow.add_node("gather_notion_intelligence", workflow_logic.gather_notion_intelligence)
    workflow.add_node("gather_github_intelligence", workflow_logic.gather_github_intelligence)
    workflow.add_node("gather_web_intelligence", workflow_logic.gather_web_intelligence)
    workflow.add_node("summarize_notion", workflow_logic.summarize_notion)
    workflow.add_node("summarize_github", workflow_logic.summarize_github)
    workflow.add_node("summarize_web", workflow_logic.summarize_web)
    workflow.add_node("synthesize", workflow_logic.synthesize)
    workflow.add_node("draft_prd", workflow_logic.draft_prd)
    workflow.add_node("save_to_notion", workflow_logic.save_to_notion)
    workflow.add_node("notify_slack", workflow_logic.notify_slack)
    
    workflow.add_edge("understand_context", "gather_notion_intelligence")
    workflow.add_edge("understand_context", "gather_github_intelligence")
    workflow.add_edge("understand_context", "gather_web_intelligence")
    workflow.add_edge("gather_notion_intelligence", "summarize_notion")
    workflow.add_edge("gather_github_intelligence", "summarize_github")
    workflow.add_edge("gather_web_intelligence", "summarize_web")
    workflow.add_edge("summarize_notion", "synthesize")
    workflow.add_edge("summarize_github", "synthesize")
    workflow.add_edge("summarize_web", "synthesize")
    workflow.add_edge("synthesize", "draft_prd")
    workflow.add_edge("draft_prd", "save_to_notion")
    workflow.add_edge("save_to_notion", "notify_slack")
    workflow.add_edge("notify_slack", END)
    
    workflow.set_entry_point("understand_context")
    
    print(f"[{agent.name}] PRD Drafting: Compiling with PostgresCheckpointer...", flush=True)
    checkpointer = PostgresCheckpointer()
    return workflow.compile(checkpointer=checkpointer)
