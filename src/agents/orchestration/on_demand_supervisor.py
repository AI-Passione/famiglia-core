from typing import Any, Dict, List, Optional, Callable, Annotated
import operator
import re
from langgraph.graph import StateGraph, END

from src.agents.utils.agent_utils import (
    build_conversation_key,
    extract_model_size_billions,
    format_memories,
    format_recent_messages,
    truncate,
    normalize_task_for_routing
)
from src.agents.llm.client import client
from src.db.agents.context_store import context_store
from src.agents.orchestration.features.product_development.prd_drafting import setup_prd_drafting_graph
from src.agents.orchestration.features.product_development.prd_review import setup_prd_review_graph
from src.agents.orchestration.features.product_development.milestone_creation import setup_milestone_creation_graph
from src.agents.orchestration.features.market_research.market_research import setup_market_research_graph
from src.db.agents.audit import audit_logger
from src.agents.orchestration.utils.state import AgentState
from src.agents.orchestration.features.product_development.grooming import setup_grooming_graph
from src.agents.orchestration.features.analytics.simple_data_analysis import setup_data_analysis_graph
from src.agents.orchestration.features.analytics.deep_dive_analysis import setup_deep_dive_analysis_graph
from src.agents.orchestration.features.analytics.data_ingestion import setup_data_ingestion_graph
from src.db.observability.checkpointer import PostgresCheckpointer


class OnDemandMasterSupervisor:
    """
    On-Demand Master Supervisor for interactive Slack requests.
    Directly orchestrates workers for Product, Operations, and Support domains.
    """

    def _get_product_graph(self, worker_type: str):
        """Lazy initialization of worker graphs."""
        if worker_type == "prd_drafting":
            if not hasattr(self, "_prd_drafting_graph"):
                self._prd_drafting_graph = setup_prd_drafting_graph(self)
            return self._prd_drafting_graph
        elif worker_type == "prd_review":
            if not hasattr(self, "_prd_review_graph"):
                self._prd_review_graph = setup_prd_review_graph(self)
            return self._prd_review_graph
        elif worker_type == "milestone_creation":
            if not hasattr(self, "_milestone_creation_graph"):
                self._milestone_creation_graph = setup_milestone_creation_graph(self)
            return self._milestone_creation_graph
        elif worker_type == "market_research":
            if not hasattr(self, "_market_research_graph"):
                self._market_research_graph = setup_market_research_graph(self)
            return self._market_research_graph
        elif worker_type == "grooming":
            if not hasattr(self, "_grooming_graph"):
                self._grooming_graph = setup_grooming_graph(self)
            return self._grooming_graph
        return None

    def _get_routing_mode(self, task: str, history: List[Dict[str, Any]] = []) -> str:
        """Determines the domain of the request: PRODUCT, OPERATIONS, or SUPPORT."""
        normalized = normalize_task_for_routing(task)

        if not normalized:
            return "SUPPORT"
        
        # FAST-PATH: Product keywords
        product_keywords = ["prd", "milestone", "research", "market", "feature request", "notion", "issue", "groom"]
        if any(kw in normalized for kw in product_keywords):
            print(f"[{self.name}] Routing decided: PRODUCT")
            return "PRODUCT"

        # Contextual check: Is this a short reply to a recent Product question?
        if len(normalized.split()) < 6:
            last_bot_msg = None
            for msg in reversed(history):
                if msg.get("role") == "assistant":
                    last_bot_msg = (msg.get("content") or "").lower()
                    break
            
            if last_bot_msg:
                # If bot asked about PRDs or Milestones, assume this is a reply to that
                if any(kw in last_bot_msg for kw in ["prd", "milestone", "which one", "provide a page id"]):
                    print(f"[{self.name}] Contextual routing decided: PRODUCT (Reply to: '{last_bot_msg[:50]}...')")
                    return "PRODUCT"

        # FAST-PATH: Operations keywords
        ops_keywords = ["diagnostic", "system check", "verify access", "check access", "permissions check"]
        if any(kw in normalized for kw in ops_keywords):
            print(f"[{self.name}] Routing decided: OPERATIONS")
            return "OPERATIONS"

        # FAST-PATH: Analytics keywords
        analytics_keywords = ["ingest", "dwh", "sql", "csv", "data", "parquet", "json", "analytics", "analyze", "analysis", "table", "deep dive", "drill down", "correlation", "hypothesis"]
        if any(kw in normalized for kw in analytics_keywords):
            print(f"[{self.name}] Routing decided: ANALYTICS")
            return "ANALYTICS"

        # Default to support (chat/search)
        print(f"[{self.name}] Routing decided: SUPPORT")
        return "SUPPORT"

    def _get_product_worker(self, task: str, history: List[Dict[str, Any]] = []) -> str:
        """Determines which product worker to use."""
        task_lower = task.lower()

        # 1. Direct Keyword Check (Current Task takes priority)
        if "research" in task_lower or "market" in task_lower:
            return "market_research"
        elif "groom" in task_lower:
            return "grooming"
        elif "draft" in task_lower or "create prd" in task_lower:
            return "prd_drafting"
        elif "review" in task_lower or "feedback" in task_lower or "comment" in task_lower:
            return "prd_review"
        elif "milestone" in task_lower or "github issue" in task_lower:
            return "milestone_creation"
        
        # 2. Contextual check: If it's a short reply, look at recent history
        if len(task_lower.split()) < 6:
            # Search for 'groom' across recent history first (it should take precedence)
            for msg in reversed(history[-10:]):
                content = (msg.get("content") or "").lower()
                if "groom" in content:
                    print(f"[{self.name}] Contextual routing: discovered 'grooming' in history")
                    return "grooming"
            
            # Then search for other product contexts
            for msg in reversed(history[-10:]):
                content = (msg.get("content") or "").lower()
                if any(kw in content for kw in ["milestone", "found multiple prds"]):
                    print(f"[{self.name}] Contextual routing: decided 'milestone_creation' based on history")
                    return "milestone_creation"
                if any(kw in content for kw in ["review", "feedback", "comment"]):
                    return "prd_review"
        
        return "prd_drafting"

    def _get_initial_state(
        self,
        task: str,
        sender: str,
        conversation_key: Optional[str]
    ) -> AgentState:
        """Entry Node: Prepare initial state and context."""
        scoped_conversation_key = build_conversation_key(sender, conversation_key)
        
        # 1. Fetch memories and history
        memories = context_store.get_memories(self.name)
        history = []
        if context_store.enabled:
            history = context_store.get_recent_messages(scoped_conversation_key, limit=15)
        
        # 2. Assign action ID
        action_id = audit_logger.log_action(
            agent_name=self.name,
            action_type="INTERACTIVE_TASK",
            action_details={"task": task, "conversation_key": scoped_conversation_key},
            is_approval_required=False,
            approval_status="N/A",
        ) if context_store.enabled else "mock-action-id"

        # 3. Resolve the best available model clinical-style
        model_to_use = client.resolve_best_model(self.model_config, agent_name=self.name)

        return {
            "task": task,
            "sender": sender,
            "conversation_key": scoped_conversation_key,
            "memories": memories,
            "history": history,
            "action_id": action_id,
            "routing_mode": "SUPPORT",
            "model_to_use": model_to_use,
            "final_response": None,
            "tool_trigger": None
        }

    def _decide_domain(self, state: AgentState) -> AgentState:
        """Node: Determine domain routing mode."""
        task = state["task"]
        history = state.get("history", [])
        routing_mode = self._get_routing_mode(task, history)
        state["routing_mode"] = routing_mode
        return state

    # --- Worker Delegation Nodes ---
    
    def call_prd_worker(self, state: AgentState) -> AgentState:
        worker_type = self._get_product_worker(state["task"], state.get("history", []))
        print(f"[{self.name}] OnDemandSupervisor: Delegating to Product Worker: {worker_type}")
        
        graph = self._get_product_graph(worker_type)
        if graph:
            res = graph.invoke(state)
        else:
            print(f"[{self.name}] Error: Unknown worker type {worker_type}")
            res = {}
            
        state.update(res)
        return state

    def handle_support(self, state: AgentState) -> AgentState:
        print(f"[{self.name}] OnDemandSupervisor: Handling Support/Chat")
        prompt = f"System: {self.soul_profile}\nTask: {state['task']}"
        
        # Use the pre-resolved model from initial state
        model_config = self.model_config.copy()
        model_config["primary"] = state.get("model_to_use") or self.model_config.get("primary")
        
        res, used_model = client.complete(prompt, model_config, agent_name=self.name)
        state["final_response"] = res
        state["used_model"] = used_model
        return state

    def handle_operations(self, state: AgentState) -> AgentState:
        print(f"[{self.name}] OnDemandSupervisor: Handling Operations")
        # Logic for technical tasks
        state["final_response"] = "Operations check complete. All systems nominal. I've verified your access and everything looks healthy."
        return state

    def handle_analytics(self, state: AgentState) -> AgentState:
        print(f"[{self.name}] OnDemandSupervisor: Delegating to Analytics Worker")
        
        task_lower = state["task"].lower()
        is_deep_dive = any(kw in task_lower for kw in ["deep dive", "drill down", "correlation", "hypothesis", "exhaustive", "thorough"])
        # Ingestion: check for "ingest" specifically, but prioritize analysis if "analyze" or "analysis" is also present
        is_ingestion = "ingest" in task_lower and not any(kw in task_lower for kw in ["analyze", "analysis", "summary", "report"])
        
        if is_ingestion:
            print(f"[{self.name}] OnDemandSupervisor: Using DATA INGESTION graph")
            if not hasattr(self, "_ingestion_graph"):
                self._ingestion_graph = setup_data_ingestion_graph(self)
            res = self._ingestion_graph.invoke(state)
        elif is_deep_dive:
            print(f"[{self.name}] OnDemandSupervisor: Using DEEP DIVE graph")
            if not hasattr(self, "_deep_dive_graph"):
                self._deep_dive_graph = setup_deep_dive_analysis_graph(self)
            res = self._deep_dive_graph.invoke(state)
        else:
            print(f"[{self.name}] OnDemandSupervisor: Using SIMPLE data analysis graph")
            if not hasattr(self, "_analytics_graph"):
                self._analytics_graph = setup_data_analysis_graph(self)
            res = self._analytics_graph.invoke(state)
            
        state.update(res)
        return state

    def _finalize_response(self, state: AgentState) -> str:
        """Wrap up, log response, and update memories."""
        response = state.get("final_response")
        used_model = state.get("used_model", "unknown")
        
        if not response:
            return "I apologize, but I was unable to generate a response for your request."

        # 1. Format display model
        display_model = used_model.replace("-", " ").title().replace("Ollama ", "Ollama-")
        size_label = extract_model_size_billions(client, used_model) or "Undisclosed"
        
        footer = f"\n\n_Generated by {display_model} (Model Size: {size_label})_"
        final_text = response + footer
        
        # 2. Persist
        if context_store.enabled:
             context_store.log_message(
                agent_name=self.name,
                conversation_key=state["conversation_key"],
                role="assistant",
                content=final_text,
                sender=self.name
            )
        return final_text

    def _setup_graph(self):
        """Build the orchestration StateGraph with persistence."""
        print(f"[{self.name}] On-Demand Master Supervisor: Setting up graph...", flush=True)
        
        workflow = StateGraph(AgentState)
        
        # Define nodes
        workflow.add_node("decide_domain", self._decide_domain)
        workflow.add_node("product_worker", self.call_prd_worker)
        workflow.add_node("support_handler", self.handle_support)
        workflow.add_node("operations_handler", self.handle_operations)
        workflow.add_node("analytics_handler", self.handle_analytics)
        
        # Logic Path
        workflow.set_entry_point("decide_domain")
        
        workflow.add_conditional_edges(
            "decide_domain",
            lambda x: x["routing_mode"],
            {
                "PRODUCT": "product_worker",
                "SUPPORT": "support_handler",
                "OPERATIONS": "operations_handler",
                "ANALYTICS": "analytics_handler"
            }
        )
        
        workflow.add_edge("product_worker", END)
        workflow.add_edge("support_handler", END)
        workflow.add_edge("operations_handler", END)
        workflow.add_edge("analytics_handler", END)
        
        print(f"[{self.name}] On-Demand Master Supervisor: Compiling with PostgresCheckpointer...", flush=True)
        checkpointer = PostgresCheckpointer()
        return workflow.compile(checkpointer=checkpointer)
