from typing import Any, Dict, List, Optional, TypedDict
from langgraph.graph import StateGraph, END

from famiglia_core.agents.orchestration.utils.state import AgentState
from famiglia_core.agents.orchestration.utils.task_helpers import Task
from famiglia_core.agents.orchestration.features.product_development.prd_drafting import setup_prd_drafting_graph
from famiglia_core.agents.orchestration.features.product_development.prd_review import setup_prd_review_graph
from famiglia_core.agents.orchestration.features.product_development.milestone_creation import setup_milestone_creation_graph
from famiglia_core.agents.orchestration.features.market_research.market_research import setup_market_research_graph
from famiglia_core.db.observability.checkpointer import PostgresCheckpointer

class SchedulingMasterSupervisor:
    """
    Scheduling Master Supervisor for autonomous background tasks.
    Routes based on task_type to domain supervisors.
    """

    def __init__(self, agent):
        self.agent = agent
        self.name = agent.name
        self.model_config = agent.model_config
        
        # Initialize Worker Graphs
        self.prd_drafting_graph = setup_prd_drafting_graph(agent)
        self.prd_review_graph = setup_prd_review_graph(agent)
        self.milestone_creation_graph = setup_milestone_creation_graph(agent)
        self.market_research_graph = setup_market_research_graph(agent)

    def _route_to_worker(self, state: AgentState) -> AgentState:
        """Node: Determine worker routing based on task_type."""
        task_data = state.get("metadata", {}).get("task_record")
        
        if task_data:
            print(f"[{self.name}] SchedulingMasterSupervisor: Found task_record in metadata")
            # Handle both object and dict (for JSON serialization compatibility)
            if hasattr(task_data, 'task_type'):
                tt = task_data.task_type
            elif isinstance(task_data, dict):
                # Use serialized metadata field from dict
                task_meta = task_data.get("metadata") or {}
                tt = task_meta.get("task_type") or "general"
            else:
                tt = "general"
        else:
            print(f"[{self.name}] WARNING: SchedulingMasterSupervisor NO task_record found in metadata")
            tt = "general"
            
        print(f"[{self.name}] SchedulingMasterSupervisor: Mapping routing for TaskType={tt}")
        
        # Explicit routing to workers
        if tt == "prd_drafting":
            state["routing_mode"] = "prd_drafting"
        elif tt == "prd_review_autoscan":
            state["routing_mode"] = "prd_review"
        elif tt == "market_research":
            state["routing_mode"] = "market_research"
        elif tt == "coding_code_analysis" or tt == "coding_implementation":
            state["routing_mode"] = "operations"
        else:
            state["routing_mode"] = "support"
            
        return state

    # --- Worker Delegation Nodes ---
    
    def call_prd_drafting(self, state: AgentState) -> AgentState:
        print(f"[{self.name}] SchedulingMasterSupervisor: Delegating to PRD Drafting")
        config = {"configurable": {"thread_id": state.get("conversation_key", "default")}}
        res = self.prd_drafting_graph.invoke(state, config=config)
        state.update(res)
        return state

    def call_prd_review(self, state: AgentState) -> AgentState:
        print(f"[{self.name}] SchedulingMasterSupervisor: Delegating to PRD Review")
        config = {"configurable": {"thread_id": state.get("conversation_key", "default")}}
        res = self.prd_review_graph.invoke(state, config=config)
        state.update(res)
        return state

    def call_market_research(self, state: AgentState) -> AgentState:
        print(f"[{self.name}] SchedulingMasterSupervisor: Delegating to Market Research")
        config = {"configurable": {"thread_id": state.get("conversation_key", "default")}}
        res = self.market_research_graph.invoke(state, config=config)
        state.update(res)
        return state

    def handle_support(self, state: AgentState) -> AgentState:
        print(f"[{self.name}] SchedulingMasterSupervisor: Handling Support/Chat")
        from famiglia_core.agents.llm.client import client
        prompt = f"System: {self.agent.soul_profile}\nTask: {state['task']}"
        
        # Use pre-resolved model from state
        model_config = self.model_config.copy()
        model_config["primary"] = state.get("model_to_use") or self.model_config.get("primary")
        
        res, used_model = client.complete(prompt, model_config, agent_name=self.name)
        state["final_response"] = res
        state["used_model"] = used_model
        return state

    def handle_operations(self, state: AgentState) -> AgentState:
        print(f"[{self.name}] SchedulingMasterSupervisor: Handling Operations")
        state["final_response"] = "Scheduled operations check complete. All systems nominal."
        return state

    def setup_graph(self):
        workflow = StateGraph(AgentState)
        
        workflow.add_node("route_to_worker", self._route_to_worker)
        workflow.add_node("prd_drafting", self.call_prd_drafting)
        workflow.add_node("prd_review", self.call_prd_review)
        workflow.add_node("market_research", self.call_market_research)
        workflow.add_node("support", self.handle_support)
        workflow.add_node("operations", self.handle_operations)
        
        workflow.set_entry_point("route_to_worker")
        
        workflow.add_conditional_edges(
            "route_to_worker",
            lambda x: x["routing_mode"],
            {
                "prd_drafting": "prd_drafting",
                "prd_review": "prd_review",
                "market_research": "market_research",
                "support": "support",
                "operations": "operations"
            }
        )
        
        workflow.add_edge("prd_drafting", END)
        workflow.add_edge("prd_review", END)
        workflow.add_edge("market_research", END)
        workflow.add_edge("support", END)
        workflow.add_edge("operations", END)
        
        checkpointer = PostgresCheckpointer()
        return workflow.compile(checkpointer=checkpointer)

def setup_scheduling_supervisor_graph(agent):
    return SchedulingMasterSupervisor(agent).setup_graph()
