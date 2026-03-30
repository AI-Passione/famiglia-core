from typing import Any, Dict, List, Optional, TypedDict
from langgraph.graph import StateGraph, END
import os
import re
import json

from src.agents.orchestration.utils.state import AgentState
from src.agents.llm.client import client
from src.agents.tools.notion import notion_client
from src.command_center.backend.slack.client import slack_queue
from src.db.observability.checkpointer import PostgresCheckpointer

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
                    print(f"[{self.name}] Page ID missing. Searching Notion for: {target_name}")
                    results = notion_client.search(query=target_name, agent_name=self.name)
                    # Filter for pages with IDs
                    pages = [r for r in results if r.get("id")]
                    
                    if not pages:
                        # Broaden search: just "PRD"
                        print(f"[{self.name}] Specific search for '{target_name}' failed. Trying broader search and split words.")
                        results = notion_client.search(query="PRD", agent_name=self.name)
                        # Look for target_name or any of its words in titles
                        pages = []
                        words = [w.lower() for w in re.split(r"[\s_]+", target_name) if len(w) > 2]
                        
                        for r in results:
                            title = str(r.get("title", "")).lower()
                            # Check if whole target name is in title
                            if target_name.lower() in title:
                                pages.append(r)
                                continue
                            # Check if ANY major word is in title
                            if any(word in title for word in words):
                                pages.append(r)
                    
                    if pages:
                        page_id = pages[0]["id"]
                        found_title = pages[0].get("title", "Unknown")
                        print(f"[{self.name}] Found potential PRD page match: {found_title} ({page_id})")

        if not page_id:
            msg = f"No Notion page ID found. Searched for keywords from: '{task_clean if 'task_clean' in locals() else 'None'}'. Please provide a direct link or ID."
            print(f"[{self.name}] Final Lookup Error: {msg}")
            return {"last_error": msg, "notion_success": False}

        updates = {"notion_page_id": page_id}
        try:
            # 1. Read Page Content (v2.4 metadata)
            page_data = notion_client.read_page(page_id, agent_name=self.name)
            blocks = page_data.get("blocks", [])
            updates["prd_blocks"] = blocks
            updates["notion_url"] = page_data.get("url")
            
            # Simple fallback for standard markdown state
            state_markdown = "\n".join([b.get("text", "") for b in blocks])
            updates["current_prd_markdown"] = state_markdown
            
            # 2. Read Comments
            comments = notion_client.list_comments(page_id, agent_name=self.name, deep_scan=True)
            print(f"[{self.name}] [prd_review.py v2.7] PRD Review Load: Found {len(comments)} comments on page {page_id}")
            print(f"[{self.name}] [prd_review.py v2.7] Page properties: {list(page_data.get('page_properties', {}).keys())}")
            updates["notion_comments"] = comments
            
            # Simple title extraction
            props = page_data.get("page_properties", {})
            updates["prd_title"] = props.get("title", "Updated PRD")
            
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

    def save_to_notion(self, state: PRDReviewState) -> PRDReviewState:
        """Node 4: Update the Notion page surgically (Patch Mode)."""
        if state.get("last_error"):
            return {"notion_success": False}
        
        print(f"[{self.name}] [prd_review.py v2.8] PRD Review Node: save_to_notion (Surgical Mode)")
        page_id = state.get("notion_page_id")
        comments = state.get("notion_comments", [])
        blocks = state.get("prd_blocks", [])
        evaluation = state.get("evaluation_results", "")
        
        try:
            # 1. Map comments to blocks
            block_feedback = {}
            for c in comments:
                bid = c.get("parent_block_id")
                if bid:
                    if bid not in block_feedback:
                        block_feedback[bid] = []
                    block_feedback[bid].append(c["text"])

            if not block_feedback:
                print(f"[{self.name}] No block-level feedback found. Skipping surgical updates.")
                return {"notion_success": True}

            print(f"[{self.name}] Found feedback for {len(block_feedback)} unique IDs. Patching...")
            
            # 2. Patch each block surgically
            for bid, fb_list in block_feedback.items():
                # Check if it is the page itself
                if bid == page_id:
                    print(f"[{self.name}] Handling page-level feedback for {bid}...")
                    # For page-level, we could update title or prepend a block. 
                    # Let's prepend a "Director Note" block if it is on the page.
                    note_prompt = f"Write a short Director's Note based on this page-level feedback:\n{fb_list}"
                    new_note, _ = client.complete(note_prompt, self.agent.get_model_config(state), agent_name=self.name)
                    notion_client.append_text_to_page(page_id, f"> **Director Note:** {new_note.strip()}", agent_name=self.name)
                    continue

                # Find the existing block
                block = next((b for b in blocks if b["id"] == bid), None)
                if not block:
                    print(f"[{self.name}] Block {bid} not found in page blocks. Might be nested correctly but not in initial fetch.")
                    continue
                
                print(f"[{self.name}] Surgically updating block {bid}...")
                prompt = f"""
                {self.personality}
                
                Task: Rewrite this specific PRD block based on the feedback and the Director's evaluation.
                
                Current Content:
                {block['text']}
                
                Feedback on this block:
                - {" - ".join(fb_list)}
                
                Evaluation Context:
                {evaluation}
                
                Requirements:
                1. Output ONLY the updated markdown for this single block.
                2. If the feedback was REJECTED in the evaluation, you may return the ORIGINAL content.
                3. If the feedback clearly requests REMOVAL/DELETION of this specific block and the Director agrees, output exactly "DELETE".
                4. Do not add headers if the block was a paragraph.
                """
                new_text, _ = client.complete(prompt, self.agent.get_model_config(state), agent_name=self.name)
                
                if new_text.strip().upper() == "DELETE":
                    print(f"[{self.name}] Deleting (archiving) block {bid} as requested.")
                    notion_client.archive_block(bid, agent_name=self.name)
                else:
                    notion_client.update_block(bid, new_text.strip(), agent_name=self.name)

            return {"notion_success": True}
        except Exception as e:
            print(f"[{self.name}] PRD Review Surgical Patch Failed: {e}")
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
            if url: msg += f"\n🔗 <{url}|View PRD>"
        else:
            msg = f"🔬 *PRD Update:* I've addressed the comments on '{title}' and surgically updated the Notion page."
            if url: msg += f"\n🔗 <{url}|View Updated PRD>"
            
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
        """Node 6: Reply to all original Notion comment threads individually."""
        print(f"[{self.name}] PRD Review Node: post_replies (Looping)")
        comments = state.get("notion_comments", [])
        evaluation = state.get("evaluation_results", "")
        
        if not comments:
            return {}

        # 1. Group comments by discussion_id
        unique_discussions = {}
        for c in comments:
            did = c.get("discussion_id")
            if did:
                if did not in unique_discussions:
                    unique_discussions[did] = []
                unique_discussions[did].append(c["text"])

        print(f"[{self.name}] Found {len(unique_discussions)} unique threads to reply to.")

        # 2. Iterate and reply to each
        for disc_id, thread_comments in unique_discussions.items():
            print(f"[{self.name}] Generating reply for thread {disc_id}...")
            
            thread_text = "\n".join([f"- {txt}" for txt in thread_comments])
            
            prompt = f"""
            {self.personality}
            
            Task: Write a professional reply to the following Notion comment thread based on the Product Director's evaluation results.
            
            Director's Evaluation Recap:
            {evaluation}
            
            The Thread Content:
            {thread_text}
            
            Requirements for the reply:
            1. Clearly state if the feedback was CARRIED OUT, REJECTED, or ADJUSTED.
            2. Be concise and professional.
            3. Output ONLY the reply text, no placeholders or conversational filler.
            """
            
            reply_text, _ = client.complete(prompt, self.agent.get_model_config(state), agent_name=self.name)
            
            try:
                # Post the reply
                notion_client.create_comment(text=reply_text.strip(), discussion_id=disc_id, agent_name=self.name)
                print(f"[{self.name}] Successfully replied to {disc_id}")
            except Exception as e:
                print(f"[{self.name}] Failed to post reply to {disc_id}: {e}")

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
        """Node 0: Discovery - Find PRDs with unaddressed human comments."""
        print(f"[{self.name}] [prd_review.py v2.9] PRD Review Node: discover_prds")
        
        try:
            # 1. Search for potential PRD pages
            results = notion_client._make_request("POST", "/search", data={
                "query": "PRD",
                "filter": {"property": "object", "value": "page"},
                "page_size": 20
            })
            
            candidates = results.get("results", [])
            print(f"[{self.name}] Discovery found {len(candidates)} candidate pages.")
            
            unaddressed_ids = []
            
            for page in candidates:
                page_id = page["id"]
                title = "".join([t["plain_text"] for t in page.get("properties", {}).get("title", {}).get("title", [])])
                
                comments = notion_client.list_comments(page_id, agent_name=self.name, deep_scan=True)
                
                if not comments:
                    continue
                    
                threads = {}
                for c in comments:
                    did = c["discussion_id"]
                    if did not in threads or c["created_at"] > threads[did]["created_at"]:
                        threads[did] = c
                
                found_unaddressed = False
                for did, last_comment in threads.items():
                    if last_comment.get("author_type") == "person":
                        print(f"[{self.name}] Unaddressed human comment found on '{title}' in thread {did}")
                        found_unaddressed = True
                        break
                
                if found_unaddressed:
                    unaddressed_ids.append(page_id)
            
            print(f"[{self.name}] Discovery finished. Found {len(unaddressed_ids)} unaddressed PRDs.")
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

    # Define Nodes
    workflow.add_node("discover_prds", review_workflow.discover_prds)
    workflow.add_node("load_prd_and_comments", review_workflow.load_prd_and_comments)
    workflow.add_node("summarize_feedback", review_workflow.summarize_feedback)
    workflow.add_node("evaluate_feedback", review_workflow.evaluate_feedback)
    workflow.add_node("update_prd", review_workflow.update_prd)
    workflow.add_node("save_to_notion", review_workflow.save_to_notion)
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
    
    workflow.add_edge("update_prd", "save_to_notion")
    workflow.add_edge("save_to_notion", "post_replies")
    
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
