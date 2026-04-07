from typing import Any, Dict, List, Optional, TypedDict
from langgraph.graph import StateGraph, END
import os
import re
import json

from famiglia_core.agents.orchestration.utils.state import AgentState
from famiglia_core.agents.llm.client import client
# from famiglia_core.agents.tools.notion import notion_client
from famiglia_core.command_center.backend.api.services.intelligence_service import intelligence_service
from famiglia_core.command_center.backend.api.models.intelligence import IntelligenceItemUpdate
from famiglia_core.command_center.backend.comms.slack.client import slack_queue
from famiglia_core.db.observability.checkpointer import PostgresCheckpointer

class PRDReviewState(AgentState):
    """State for the PRD Review workflow."""
    notion_page_id: str
    prd_title: str
    current_prd_markdown: str
    notion_comments: List[Dict[str, Any]]
    feedback_summary: str
    evaluation_results: str # The Product Director's verdict (carry/reject/adjust)
    decision: str # "update" or "skip"
    updated_prd_markdown: str
    notion_url: str
    slack_channel: str
    notion_success: bool
    prd_blocks: List[Dict[str, Any]] # List of {id, text, type}
    user_request: str # The original request text from Slack/User
    last_error: str
    pages_to_review: List[str] # Discovered page IDs during scan
    discovery_mode: bool # True if triggered by scheduled task

class PRDReviewWorkflow:
    """
    Logic for addressing Notion comments and updating the PRD.
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

    def load_prd_and_comments(self, state: PRDReviewState) -> PRDReviewState:
        """Node 1: Load the current PRD and its comments from Notion."""
        print(f"[{self.name}] PRD Review Node: load_prd_and_comments")
        page_id = state.get("notion_page_id")
        
        if not page_id:
            # Try to find page ID from task if not provided (e.g. if passed via URL)
            task = state.get("task", "")
            id_match = re.search(r"([a-f0-9]{32})", task)
            if id_match:
                page_id = id_match.group(1)
        
        target_name = None
        if not page_id:
            # Fallback: Extract name and search
            # Determine the source message for name extraction
            raw_msg = state.get("user_request") or state.get("task") or state.get("user_input") or ""
            
            # Patterns: "PRD: [Name]", "PRD of [Name]", "PRD for [Name]", "PRD on [Name]", "[Name] PRD"
            task_clean = re.sub(r"<@U[A-Z0-9]+>", "", raw_msg) # Remove slack mentions
            print(f"[{self.name}] [prd_review.py] Extracting PRD name from: '{task_clean}'")
            
            # Try specific "PRD of/for/on/at [Name]"
            name_match = re.search(r"prd\s+(?:of|for|on|at|named|titled)\s+([^?.]+)", task_clean, re.IGNORECASE)
            
            # Try "PRD: [Name]"
            if not name_match:
                name_match = re.search(r"prd\s*:\s*([^?.]+)", task_clean, re.IGNORECASE)
                
            # Try "[Name] PRD"
            if not name_match:
                name_match = re.search(r"([^?.\s]+)\s+prd", task_clean, re.IGNORECASE)

            if name_match:
                target_name = name_match.group(1).strip().replace("\"", "").replace("'", "")
                
                # Sanity check for "None" or empty target
                if not target_name or target_name.lower() == "none":
                    target_name = None
                
                    if target_name:
                        print(f"[{self.name}] Searching Intelligence DB for: {target_name}")
                        from famiglia_core.command_center.backend.api.services.intelligence_service import intelligence_service
                        items = intelligence_service.list_items(item_type="prd")
                        for item in items:
                            if target_name.lower() in item.get("title", "").lower():
                                page_id = str(item["id"])
                                found_title = item.get("title", "Unknown")
                                print(f"[{self.name}] Found potential PRD match: {found_title} ({page_id})")
                                break

        if not page_id:
            msg = f"No PRD found. Searched for keywords from: '{task_clean if 'task_clean' in locals() else 'None'}'."
            print(f"[{self.name}] Final Lookup Error: {msg}")
            return {"last_error": msg, "notion_success": False}

        updates = {"notion_page_id": page_id}
        try:
            # 1. Read Item Content
            from famiglia_core.command_center.backend.api.services.intelligence_service import intelligence_service
            item = intelligence_service.get_item(int(page_id))
            if not item:
                raise Exception(f"Item {page_id} not found in DB.")
                
            updates["current_prd_markdown"] = item.get("content", "")
            
            # 2. Read Comments (Dummy for now since DB lacks threads)
            metadata = item.get("metadata", {})
            if isinstance(metadata, str):
                import json
                try:
                    metadata = json.loads(metadata)
                except Exception:
                    metadata = {}
            comments = metadata.get("comments", [])
            updates["notion_comments"] = comments
            updates["prd_title"] = item.get("title", "Updated PRD")
            
        except Exception as e:
            print(f"[{self.name}] PRD Review Load Failed: {e}")
            updates["last_error"] = str(e)
            
        return updates

    def summarize_feedback(self, state: PRDReviewState) -> PRDReviewState:
        """Node 2: Summarize comments to understand what needs to change."""
        print(f"[{self.name}] PRD Review Node: summarize_feedback")
        comments = state.get("notion_comments", [])
        if not comments:
            return {"feedback_summary": "No comments found. No changes requested."}

        comment_text = "\n".join([f"- {c['text']}" for c in comments])
        prompt = f"""
        {self.personality}
        
        Task: Below are comments left on a PRD in Notion. Summarize the requested changes or questions.
        
        Comments:
        {comment_text}
        
        Output a concise bulleted list of focus points for the update.
        """
        res, _ = client.complete(prompt, self.agent.get_model_config(state), agent_name=self.name)
        return {"feedback_summary": res}

    def evaluate_feedback(self, state: PRDReviewState) -> PRDReviewState:
        """Node 2.5: [System 2 Thinking] Evaluate feedback as an experienced Product Director."""
        print(f"[{self.name}] PRD Review Node: evaluate_feedback")
        current_prd = state.get("current_prd_markdown")
        feedback = state.get("feedback_summary")
        
        if "No changes requested" in feedback:
            return {"evaluation_results": "No changes needed."}

        prompt = f"""
        {self.personality}
        
        Task: Act as an extremely experienced Product Director. You are reviewing a set of feedback/comments for a PRD.
        
        Current PRD Content:
        {current_prd}
        
        Gathered Feedback:
        {feedback}
        
        Your Goal: WEED OUT low-quality or counter-productive feedback. Use System 2 thinking (calibrate Pros & Cons).
        
        For each point in the feedback, decide if we should:
        1. CARRY OUT: The instruction is sound and improves the product.
        2. REJECT: The feedback is low quality, technically unfeasible, or contradicts core goals. Provide a strong justification.
        3. ADJUST: The feedback has merit but needs to be calibrated or modified before implementation.
        
        Output your analysis in structured Markdown. 
        
        End with a section exactly titled "FINAL DECISION" followed by either "UPDATE" (if any changes should be applied) or "SKIP" (if all feedback is rejected or no changes are needed).
        
        Example:
        ...
        ## FINAL DECISION
        UPDATE
        """
        res, _ = client.complete(prompt, self.agent.get_model_config(state), agent_name=self.name)
        
        decision = "update"
        upper_res = res.upper()
        if "FINAL DECISION\nSKIP" in upper_res or "FINAL DECISION: SKIP" in upper_res or "FINAL DECISION\nREJECT" in upper_res or "FINAL DECISION: REJECT" in upper_res:
            decision = "skip"
            
        return {"evaluation_results": res, "decision": decision}

    def update_prd(self, state: PRDReviewState) -> PRDReviewState:
        """Node 3: Apply feedback to the existing PRD."""
        if state.get("last_error"):
            return {}
        print(f"[{self.name}] PRD Review Node: update_prd")
        current_prd = state.get("current_prd_markdown")
        feedback = state.get("feedback_summary")
        
        if "No changes requested" in feedback:
            return {"updated_prd_markdown": current_prd}

        prompt = f"""
        {self.personality}
        
        Task: Update the following PRD based on the provided feedback summary.
        
        PRD Markdown:
        {state.get('current_prd_markdown')}
        
        Original Slack/User Request:
        {state.get('user_request', 'No specific instructions.')}
        
        Director's Evaluation & Calibrated Instructions:
        {state.get('evaluation_results')}
        
        Rules:
        1. Preserve the structure and sections of the original PRD.
        2. Incorporate all requested changes from the feedback.
        3. Keep the status as "🔴 Unverified (Awaiting Approval)" unless the feedback explicitly asks to approve it.
        4. Update the "Last Updated" date to 2026-03-17.
        
        Output ONLY the updated Markdown.
        """
        res, _ = client.complete(prompt, self.agent.get_model_config(state), agent_name=self.name)
        return {"updated_prd_markdown": res.strip()}

    def save_to_intelligence(self, state: PRDReviewState) -> PRDReviewState:
        """Node 4: Update the Intelligence DB."""
        if state.get("last_error"):
            return {"notion_success": False}
        
        print(f"[{self.name}] PRD Review Node: save_to_intelligence")
        page_id = state.get("notion_page_id")
        content = state.get("updated_prd_markdown")
        
        try:
            summary = content[:300] + "..." if len(content) > 300 else content
            update_data = IntelligenceItemUpdate(content=content, summary=summary)
            intelligence_service.update_item(int(page_id), update_data)
            return {"notion_success": True}
        except Exception as e:
            print(f"[{self.name}] DB Update Failed: {e}")
            return {"notion_success": False, "last_error": str(e)}

    def notify_slack(self, state: PRDReviewState) -> PRDReviewState:
        """Node 5: Notify Slack of the update."""
        print(f"[{self.name}] PRD Review Node: notify_slack")
        channel = state.get("slack_channel") or "C0AL8GW2VAL"
        title = state.get("prd_title")
        success = state.get("notion_success", False)
        url = state.get("notion_url", "")
        
        feedback = state.get("feedback_summary", "")
        if "No comments found" in feedback or "No changes requested" in feedback:
            msg = f"🔬 *PRD Review:* I've reviewed '{title}' but found no comments or requested changes."
        else:
            msg = f"🔬 *PRD Update:* I've addressed the comments on '{title}' and updated it in the Intelligence Center."
            
        error = state.get("last_error")
        decision = state.get("decision", "update")
        
        if error:
            msg = f"⚠️ *PRD Review Error:* I encountered an issue: {error}"
        elif decision == "skip":
            msg = f"🔬 *PRD Review Finished:* I've reviewed '{title}' and posted replies to the comments. I decided not to modify the PRD content at this time (all feedback was rejected or already addressed)."
        elif not success:
            msg = f"⚠️ *PRD Update Error:* I tried to update '{title}' based on feedback, but encountered an error saving to Notion."

        slack_queue.post_message(agent=self.agent.agent_id, channel=channel, message=msg)
        return {"final_response": msg}

    def post_replies(self, state: PRDReviewState) -> PRDReviewState:
        """Node 6: Reply to threads (Disabled for local Intelligence Center)."""
        print(f"[{self.name}] PRD Review Node: post_replies (Disabled)")
        return {}

    def route_error(self, state: PRDReviewState):
        if state.get("last_error"):
            return "error"
        return "continue"

    def route_feedback(self, state: PRDReviewState):
        if state.get("last_error"):
            return "error"
        decision = state.get("decision", "update")
        print(f"[{self.name}] Routing decision: {decision}")
        return decision

    def discover_prds(self, state: PRDReviewState) -> PRDReviewState:
        """Node 0: Discovery - Find PRDs with unaddressed comments."""
        print(f"[{self.name}] PRD Review Node: discover_prds")
        
        try:
            items = intelligence_service.list_items(item_type="prd")
            unaddressed_ids = []
            
            for item in items:
                metadata = item.get("metadata", {})
                comments = metadata.get("comments", [])
                if comments:
                    unaddressed_ids.append(str(item["id"]))
            
            print(f"[{self.name}] Discovery found {len(unaddressed_ids)} PRDs with comments.")
            return {"pages_to_review": unaddressed_ids, "discovery_mode": True}
        except Exception as e:
            print(f"[{self.name}] Discovery Error: {e}")
            return {"last_error": str(e)}

    def route_discovery(self, state: PRDReviewState):
        """Routing node for discovery path."""
        if state.get("last_error"):
            return "error"
        
        pages = state.get("pages_to_review", [])
        if pages:
            next_page = pages.pop(0)
            return "review_page"
        
        return "done"

def setup_prd_review_graph(agent):
    workflow = StateGraph(PRDReviewState)
    review_workflow = PRDReviewWorkflow(agent)

    workflow.add_node("discover_prds", review_workflow.discover_prds)
    workflow.add_node("load_prd_and_comments", review_workflow.load_prd_and_comments)
    workflow.add_node("summarize_feedback", review_workflow.summarize_feedback)
    workflow.add_node("evaluate_feedback", review_workflow.evaluate_feedback)
    workflow.add_node("update_prd", review_workflow.update_prd)
    # workflow.add_node("save_to_notion", review_workflow.save_to_notion)
    workflow.add_node("save_to_intelligence", review_workflow.save_to_intelligence)
    workflow.add_node("post_replies", review_workflow.post_replies)
    workflow.add_node("notify_slack", review_workflow.notify_slack)

    # Entry decision: Discovery (Scheduled) vs Single PRD (On-demand)
    def entry_router(state: PRDReviewState):
        if state.get("discovery_mode"):
            return "discover"
        if state.get("notion_page_id") or state.get("user_request"):
            return "direct"
        return "discover" # Default to discovery if nothing provided

    workflow.set_conditional_entry_point(
        entry_router,
        {
            "discover": "discover_prds",
            "direct": "load_prd_and_comments"
        }
    )

    # 1. Discovery Path
    def next_page_router(state: PRDReviewState):
        if state.get("last_error"): return "error"
        pages = state.get("pages_to_review", [])
        if not pages: 
            return "end"
        
        # Take the next page ID and put it back in the state
        current_page = pages[0]
        # We need to return a function that updates the state or just handles the routing
        return "process"

    # Robust routing for discovery
    workflow.add_conditional_edges(
        "discover_prds",
        lambda state: "review" if state.get("pages_to_review") else "none",
        {
            "review": "load_prd_and_comments",
            "none": END
        }
    )

    # 2. Main Logic Path
    workflow.add_conditional_edges(
        "load_prd_and_comments",
        review_workflow.route_error,
        {
            "error": "notify_slack",
            "continue": "summarize_feedback"
        }
    )
    workflow.add_edge("summarize_feedback", "evaluate_feedback")
    
    workflow.add_conditional_edges(
        "evaluate_feedback",
        review_workflow.route_feedback,
        {
            "update": "update_prd",
            "skip": "post_replies",
            "error": "notify_slack"
        }
    )
    
    workflow.add_edge("update_prd", "save_to_intelligence")
    workflow.add_edge("save_to_intelligence", "post_replies")
    
    # After posting replies, if in discovery mode, go back to discover_prds to get next page
    # Actually, we can just pop from the list and loop.
    def discovery_loop_router(state: PRDReviewState):
        if state.get("last_error"): return "done"
        if state.get("discovery_mode") and state.get("pages_to_review"):
            # Update notion_page_id for next cycle
            next_id = state["pages_to_review"].pop(0)
            print(f"[Dr. Rossini] Discovery Loop: Moving to next PRD {next_id}")
            state["notion_page_id"] = next_id
            return "loop"
        return "done"

    workflow.add_conditional_edges(
        "post_replies",
        discovery_loop_router,
        {
            "loop": "load_prd_and_comments",
            "done": "notify_slack"
        }
    )

    workflow.add_edge("notify_slack", END)
    
    checkpointer = PostgresCheckpointer()
    return workflow.compile(checkpointer=checkpointer)
