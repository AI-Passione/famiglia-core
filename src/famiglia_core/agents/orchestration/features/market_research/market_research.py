from typing import Any, Dict, List, Optional, TypedDict
from langgraph.graph import StateGraph, END
import os

from famiglia_core.agents.orchestration.utils.state import AgentState
from famiglia_core.agents.llm.client import client
from famiglia_core.agents.tools.web_search import web_search_client
# from famiglia_core.agents.tools.notion import notion_client
from famiglia_core.command_center.backend.api.services.intelligence_service import intelligence_service
from famiglia_core.command_center.backend.api.models.intelligence import IntelligenceItemCreate
from famiglia_core.command_center.backend.comms.slack.client import slack_queue

class MarketResearchState(AgentState):
    """Extension of AgentState for specialized Market Research tasks."""
    research_topic: str
    search_results: str
    curated_markdown: str
    notion_page_id: str
    notion_url: str
    business_ideas: str
    slack_channel: str
    retry_count: int = 0
    search_retry_count: int = 0
    last_error: str = ""
    notion_success: bool = False
    search_success: bool = False
    search_query: str = ""

class MarketResearchWorkflow:
    """
    Logic for the Market Research LangGraph.
    Encapsulated in a class to easily share the agent instance and personality.
    """
    
    def __init__(self, agent):
        self.agent = agent
        self.name = agent.name
        self.model_config = agent.model_config
        self.personality = self._load_rossini_personality()
        self.template_path = os.path.join(
            os.getcwd(), 
            "src/famiglia_core/agents/orchestration/features/templates/research_template.md"
        )

    def _extract_research_goal(self, task: str) -> str:
        """Isolate the actual research topic from meta-prompts or directive wrappers."""
        if not task: return "General Market Research"

        # 1. Handle Situation Room "Client Specification:" format
        if "Client Specification:" in task:
            parts = task.split("Client Specification:")
            if len(parts) > 1:
                spec = parts[1].strip()
                if spec: return spec

        # 2. Strip autonomous queue metadata wrapper (everything after \n\nTask metadata:)
        import re
        clean_task = re.split(r'\n\s*\n\s*(?:Task metadata|Execution constraints):', task, flags=re.IGNORECASE)[0].strip()

        # 3. Handle "Executing graph market_research" boilerplate
        clean_task = clean_task.replace("Executing graph market_research", "").strip()
        if clean_task:
            return clean_task

        return task

    def _load_rossini_personality(self) -> str:
        """Loads and summarizes Dr. Rossini's soul file for context."""
        try:
            soul_path = os.path.join(os.getcwd(), "src/famiglia_core/agents/souls/rossini.md")
            if os.path.exists(soul_path):
                with open(soul_path, "r") as f:
                    content = f.read()
                # Take the first ~2000 chars or just the PERSONA & TONE section
                import re
                persona_match = re.search(r"## PERSONA & TONE(.*?)(##|$)", content, re.DOTALL)
                if persona_match:
                    return persona_match.group(1).strip()
                return content[:2000]
        except Exception as e:
            print(f"Error loading Rossini soul: {e}")
        return "A professional researcher and strategist named Dr. Rossini."

    def perform_search(self, state: MarketResearchState) -> MarketResearchState:
        """Node 1: Perform Web Search on the research topic."""
        # Extract topic, isolating it from directive boilerplate if necessary
        raw_topic = state.get("research_topic") or state.get("task")
        topic = self._extract_research_goal(raw_topic)
        state["research_topic"] = topic # Persist the cleaned topic
        
        query = state.get("search_query") or topic
        
        print(f"[{self.name}] Research Node: perform_search(query={query!r}, attempt={state.get('search_retry_count', 0) + 1})")
        
        try:
            results = web_search_client.search(query, agent_name=self.name)
            if "Error" in results or "not set" in results:
                raise Exception(results)
                
            state["search_results"] = results
            state["search_success"] = True
            state["search_query"] = query # Store the successful query
        except Exception as e:
            error_msg = str(e)
            print(f"[{self.name}] Search Node Failed: {error_msg}")
            state["search_results"] = f"Error during search: {error_msg}"
            state["last_error"] = error_msg
            state["search_success"] = False
        
        return state

    def refine_search_query(self, state: MarketResearchState) -> MarketResearchState:
        """Node: Use LLM to refine the search query based on previous failure."""
        print(f"[{self.name}] Research Node: refine_search_query")
        
        state["search_retry_count"] = state.get("search_retry_count", 0) + 1
        topic = state.get("research_topic") or state.get("task")
        error = state.get("last_error", "No results found or generic error.")
        last_query = state.get("search_query") or topic
        
        prompt = f"""
        Dr. Rossini, our web search for '{topic}' failed or returned poor results.
        
        Last Query Used: {last_query}
        Error/Issue: {error}
        
        Please refine the search query to be more specific or use alternative keywords that might yield better marketing intelligence and strategic data.
        
        Output only the new search query string.
        """
        
        new_query, _ = client.complete(
            prompt, 
            self.agent.get_model_config(state), 
            agent_name=self.name, 
            routing_mode="WORKFLOW"
        )

        state["search_query"] = new_query.strip().strip('"')
        return state

    def curate_results(self, state: MarketResearchState) -> MarketResearchState:
        """Node 2: Curate Web Search results into a Markdown template."""
        print(f"[{self.name}] Research Node: curate_results")
        
        results = state.get("search_results", "No results found.")
        topic = state.get("research_topic") or state.get("task")
        
        topic = state.get("research_topic") or state.get("task")
        
        # Load template
        template = ""
        if os.path.exists(self.template_path):
            with open(self.template_path, "r") as f:
                template = f.read()
            
        prompt = f"""
        Task: Curate the following web search results into a professional Market Research Markdown report.
        Topic: {topic}
        
        Search Results:
        {results}
        
        Template Requirements:
        {template}
        
        Output only the Markdown content.
        """
        
        res_text, _ = client.complete(
            prompt, 
            self.agent.get_model_config(state), 
            agent_name=self.name, 
            routing_mode="WORKFLOW"
        )

        state["curated_markdown"] = res_text
        return state

    def save_to_intelligence(self, state: MarketResearchState) -> MarketResearchState:
        """Node 3: Save curated results in Intelligence DB."""
        print(f"[{self.name}] Research Node: save_to_intelligence")
        
        topic = state.get("research_topic") or state.get("task") or "Unknown Topic"
        title = f"Market Research: {topic}"
        content = state.get("curated_markdown", "")
        summary = content[:300] + "..." if len(content) > 300 else content
        
        if not content:
            print(f"[{self.name}] Warning: Attempting to save research with empty content for '{topic}'")
        
        try:
            # Use raw dictionary for metadata to ensure Psycopg2/Postgres JSONB compatibility
            metadata = {"topic": topic}
            
            item = IntelligenceItemCreate(
                title=title,
                content=content,
                summary=summary,
                status="Completed",
                item_type="market_research",
                metadata=metadata
            )
            created_row = intelligence_service.create_item(item)
            
            if created_row:
                print(f"[{self.name}] Success: Research item #{created_row['id']} persisted to Intelligence DB.")
                state["db_success"] = True
                state["final_response"] = f"Research saved to Intelligence Center."
            else:
                raise Exception("DB Service failed: No row returned after insert.")
                
        except Exception as e:
            error_msg = str(e)
            print(f"[{self.name}] DB Save Failed for '{topic}': {error_msg}")
            state["last_error"] = error_msg
            state["db_success"] = False
            # Append error to final response for visibility in the terminal
            state["final_response"] = f"Research completed but persistence FAILED: {error_msg}"
            
        return state

    # def save_to_notion(self, state: MarketResearchState) -> MarketResearchState:
    #     """Node 3: Save curated results in Notion."""
    #     print(f"[{self.name}] Research Node: save_to_notion (Attempt {state.get('retry_count', 0) + 1})")
    #     
    #     parent_page_id = os.getenv("NOTION_RESEARCH_PARENT_ID", "31ff5d41fe97808d9530f49bff903f92")
    #     title = f"Market Research: {state.get('research_topic') or state.get('task')}"
    #     content = state.get("curated_markdown", "")
    #     
    #     try:
    #         result_str = notion_client.create_page(parent_page_id, title, content, agent_name=self.name)
    #         import re
    #         id_match = re.search(r"ID:\s*([^\s.]+)", result_str)
    #         url_match = re.search(r"URL:\s*([^\s]+)", result_str)
    #         
    #         if id_match:
    #             state["notion_page_id"] = id_match.group(1)
    #         if url_match:
    #             state["notion_url"] = url_match.group(1)
    #             
    #         state["notion_success"] = True
    #         state["final_response"] = f"Research saved to Notion. {result_str}"
    #     except Exception as e:
    #         error_msg = str(e)
    #         print(f"[{self.name}] Notion Save Failed: {error_msg}")
    #         state["last_error"] = error_msg
    #         state["notion_success"] = False
    #         
    #     return state

    def fix_notion_error(self, state: MarketResearchState) -> MarketResearchState:
        """Node: Use LLM to self-correct the Markdown based on the Notion error."""
        print(f"[{self.name}] Research Node: fix_notion_error")
        
        state["retry_count"] = state.get("retry_count", 0) + 1
        error = state.get("last_error", "Unknown error")
        content = state.get("curated_markdown", "")
        
        prompt = f"""
        The following Market Research Markdown failed to save to Notion.
        
        Error from Notion API:
        {error}
        
        Please correct the Markdown content to resolve this error. 
        Possible issues:
        - Content might be too long for certain block types (though the client chunks it, perhaps the structure is bad).
        - Invalid characters in headings.
        - Unclosed formatting tags.
        
        Original Content:
        {content}
        
        Output only the fixed Markdown.
        """
        
        res_text, _ = client.complete(
            prompt, 
            self.agent.get_model_config(state), 
            agent_name=self.name, 
            routing_mode="WORKFLOW"
        )

        state["curated_markdown"] = res_text
        return state

    def generate_ideas(self, state: MarketResearchState) -> MarketResearchState:
        """Node 4: Add proposed business ideas based on the research."""
        print(f"[{self.name}] Research Node: generate_ideas")
        
        research = state.get("curated_markdown", "")
        topic = state.get("research_topic") or state.get("task")
        
        prompt = f"""
        Based on this Market Research for '{topic}', propose 3-5 innovative business ideas or strategic opportunities.
        
        Research Content:
        {research}
        
        Output:
        ### Proposed Business Ideas
        - [Idea Name]: [Brief Description & Why it works based on findings]
        ...
        """
        
        res_text, _ = client.complete(
            prompt, 
            self.agent.get_model_config(state), 
            agent_name=self.name, 
            routing_mode="WORKFLOW"
        )

        state["business_ideas"] = res_text
        
        # Append to Notion if we have a page ID (DISABLED)
        # page_id = state.get("notion_page_id")
        # if page_id:
        #     try:
        #         notion_client.append_text_to_page(page_id, f"\n\n{res_text}", agent_name=self.name)
        #     except Exception as e:
        #         print(f"[{self.name}] Idea Append Failed: {e}")
                
        return state

    def deliver_results(self, state: MarketResearchState) -> MarketResearchState:
        """Node 5: Set final_response for the Directive Terminal and optionally notify Slack."""
        print(f"[{self.name}] Research Node: deliver_results")
        
        channel = state.get("slack_channel") or "C0AGQPGNP09" # #Research-Insights
        topic = state.get("research_topic") or state.get("task")
        notion_url = state.get("notion_url", "")
        db_success = state.get("db_success", False)
        ideas = state.get("business_ideas", "")
        
        db_status = f"Report saved in Intelligence Center." if db_success else "⚠️ Note: Full report saving failed."
        
        summary_prompt = f"""
        {self.personality}
        
        Task: Summarize the following business ideas into a single catchy Slack message (max 250 words) for the #Research-Insights channel. 
        Remember to speak ENTIRELY in English as per your constraints.
        
        Include this status: {db_status}
        
        Topic: {topic}
        Ideas: {ideas}
        """
        
        slack_msg, _ = client.complete(
            summary_prompt, 
            self.agent.get_model_config(state), 
            agent_name=self.name, 
            routing_mode="WORKFLOW"
        )

        
        # Convert Markdown to Slack mrkdwn
        import re
        formatted_slack_msg = slack_msg
        # Convert #, ##, ### Heading to *Heading*
        formatted_slack_msg = re.sub(r'^#+\s+(.*)$', r'*\1*', formatted_slack_msg, flags=re.MULTILINE)
        # Convert **bold** to *bold*
        formatted_slack_msg = formatted_slack_msg.replace("**", "*")
        # Convert [label](url) to <url|label>
        formatted_slack_msg = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<\2|\1>', formatted_slack_msg)
        # Convert Markdown bullets (- or *) to Slack bullets (•)
        formatted_slack_msg = re.sub(r'^(\s*)(?:[-*])\s+', r'\1• ', formatted_slack_msg, flags=re.MULTILINE)
        
        try:
            channel_msg = f"🔬 *Market Research Update: {topic}*\n\n{formatted_slack_msg}"
            if db_success:
                channel_msg += f"\n\n🔗 *Full Report is available in the Intelligence Center.*"
                
            slack_queue.post_message(
                agent=self.agent.agent_id,
                channel=channel,
                message=channel_msg
            )
        except Exception as e:
            print(f"[{self.name}] Slack Notification Failed: {e}")
            
        # Final response for the orchestrator
        final_report_msg = f"Full Report saved to Intelligence Center." if db_success else "⚠️ Full Report saving failed."
        state["final_response"] = f"I have completed the market research on '{topic}'.\n\n{final_report_msg}\n\nInsights & Ideas have been posted to Slack."
        return state

from famiglia_core.db.observability.checkpointer import PostgresCheckpointer

def setup_market_research_graph(agent):
    """Builds and compiles the Market Research StateGraph with persistence."""
    print(f"[{agent.name}] Market Research: Setting up graph...", flush=True)
    workflow_logic = MarketResearchWorkflow(agent)
    
    workflow = StateGraph(MarketResearchState)
    
    # Add Nodes
    workflow.add_node("perform_search", workflow_logic.perform_search)
    workflow.add_node("refine_search_query", workflow_logic.refine_search_query)
    workflow.add_node("curate_results", workflow_logic.curate_results)
    # workflow.add_node("save_to_notion", workflow_logic.save_to_notion)
    workflow.add_node("save_to_intelligence", workflow_logic.save_to_intelligence)
    # workflow.add_node("fix_notion_error", workflow_logic.fix_notion_error)
    workflow.add_node("generate_ideas", workflow_logic.generate_ideas)
    workflow.add_node("deliver_results", workflow_logic.deliver_results)

    def route_search(state: MarketResearchState):
        if state.get("search_success"):
            return "success"
        if state.get("search_retry_count", 0) >= 2:
            return "fail"
        return "retry"

    workflow.add_conditional_edges(
        "perform_search",
        route_search,
        {
            "success": "curate_results",
            "retry": "refine_search_query",
            "fail": "curate_results"
        }
    )
    
    workflow.add_edge("refine_search_query", "perform_search")
    
    workflow.add_edge("curate_results", "save_to_intelligence")
    workflow.add_edge("save_to_intelligence", "generate_ideas")
    
    # def route_notion(state: MarketResearchState):
    #     if state.get("notion_success"):
    #         return "success"
    #     if state.get("retry_count", 0) >= 2:
    #         return "fail"
    #     return "retry"
    #     
    # workflow.add_conditional_edges(
    #     "save_to_notion",
    #     route_notion,
    #     {
    #         "success": "generate_ideas",
    #         "retry": "fix_notion_error",
    #         "fail": "generate_ideas"
    #     }
    # )
    # workflow.add_edge("fix_notion_error", "save_to_notion")
    
    workflow.add_edge("generate_ideas", "deliver_results")
    workflow.add_edge("deliver_results", END)
    
    workflow.set_entry_point("perform_search")
    
    print(f"[{agent.name}] Market Research: Compiling with PostgresCheckpointer...", flush=True)
    checkpointer = PostgresCheckpointer()
    return workflow.compile(checkpointer=checkpointer)

