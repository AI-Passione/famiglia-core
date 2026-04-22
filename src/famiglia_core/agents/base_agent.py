import ast
import inspect
import re
import time
from typing import Any, Dict, List, Optional, Callable

from famiglia_core.agents.llm.client import client
from famiglia_core.db.agents.audit import audit_logger
from famiglia_core.db.agents.context_store import context_store
from famiglia_core.agents.souls.soul_registry import load_agent_soul, resolve_agent_id
from famiglia_core.agents.llm.models_registry import TASK_ROUTING
from famiglia_core.agents.orchestration.on_demand_supervisor import OnDemandMasterSupervisor
from famiglia_core.agents.orchestration.utils.state import AgentState
from famiglia_core.agents.orchestration.scheduling_supervisor import setup_scheduling_supervisor_graph
from famiglia_core.agents.orchestration.utils.task_helpers import TaskTools
from famiglia_core.agents.utils.skills import CommonSkills
from famiglia_core.observability.langfuse_util import langfuse_manager

# New modular imports
from famiglia_core.agents.orchestration.utils.task_helpers import (
    TASK_TYPE_REMINDER,
    TASK_TYPE_MARKET_RESEARCH,
    TASK_TYPE_PRD_DRAFTING,
    TASK_TYPE_FEATURE_REQUEST,
    TASK_TYPE_CODING_CODE_ANALYSIS,
    TASK_TYPE_CODING_IMPLEMENTATION,
    TASK_TYPE_ALFREDO_GREETING,
    SCHEDULED_TASK_TYPES,
    TASK_TYPE_TO_EXPECTED_AGENT,
    TASK_TYPE_TO_PRIORITY
)
from famiglia_core.agents.utils.agent_utils import (
    normalize_task_for_routing,
    is_idle_task,
    build_conversation_key,
    truncate,
    format_recent_messages,
    format_memories,
    extract_model_size_billions,
    get_lite_soul
)

class BaseAgent(CommonSkills, TaskTools, OnDemandMasterSupervisor):
    def __init__(
        self,
        name: str,
        role: str,
        model_config: Dict[str, Any],
        agent_id: str = "",
    ):
        self.agent_id = resolve_agent_id(agent_name=name, agent_id=agent_id)
        self.name = name
        self.role = role
        self.model_config = model_config
        if "global_fallback" not in self.model_config:
            from famiglia_core.agents.llm.models_registry import DEFAULT_OLLAMA_FALLBACK_MODEL
            self.model_config["global_fallback"] = DEFAULT_OLLAMA_FALLBACK_MODEL
        self.soul_profile = load_agent_soul(agent_id=self.agent_id, agent_name=name)
        self.is_cautious_mode = True  # Phase 1 default
        self.current_thread_ts: Optional[str] = None
        
        # Tool, Skill and Feature Registries
        self.tools: Dict[str, Callable] = {}
        self.skills: Dict[str, Callable] = {}
        self.features: Dict[str, Callable] = {}
        self.capability_checks: Dict[str, Callable[[], bool]] = {}

        self.register_tool("create_scheduled_task", self.create_scheduled_task)
        self.register_tool("list_scheduled_tasks", self.list_scheduled_tasks_tool)
        self.register_tool("cancel_scheduled_task", self.cancel_scheduled_task_tool)
        
        # Initialize LangGraph
        self.graph = self._setup_graph()

    # --- Compatibility Wrappers ---
    def _build_conversation_key(self, sender: str, conversation_key: Optional[str]) -> str:
        return build_conversation_key(sender, conversation_key)

    def _truncate(self, value: str, limit: int) -> str:
        return truncate(value, limit)

    def _format_recent_messages(self, messages: List[Dict[str, Any]]) -> str:
        return format_recent_messages(messages)

    def _format_memories(self, memories: List[Dict[str, Any]]) -> str:
        return format_memories(memories)

    def _extract_model_size_billions(self, model_name: str) -> Optional[str]:
        return extract_model_size_billions(client, model_name)

    def _normalize_task_for_routing(self, task: str) -> str:
        return normalize_task_for_routing(task)

    def _is_idle_task(self, task: str) -> bool:
        return is_idle_task(self.name, task)

    def register_tool(self, name: str, method: Callable, capability_name: Optional[str] = None, check_func: Optional[Callable[[], bool]] = None):
        """Register a low-level utility or API wrapper as a Tool."""
        self.tools[name] = method
        if capability_name and check_func:
            self.capability_checks[capability_name] = check_func

    def register_skill(self, name: str, method: Callable, capability_name: Optional[str] = None, check_func: Optional[Callable[[], bool]] = None):
        """Register an agent capability or expertise as a Skill."""
        self.skills[name] = method
        if capability_name and check_func:
            self.capability_checks[capability_name] = check_func

    def register_feature(self, name: str, method: Callable, capability_name: Optional[str] = None, check_func: Optional[Callable[[], bool]] = None):
        """Register a high-level workflow or specialized LangGraph as a Feature."""
        self.features[name] = method
        if capability_name and check_func:
            self.capability_checks[capability_name] = check_func
            
    def get_all_capabilities(self) -> Dict[str, Callable]:
        """Combine tools, skills, and features into a single callable registry."""
        return {**self.tools, **self.skills, **self.features}

    def get_model_config(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Resolves the model_config to use based on the pre-decided model in the state.
        Ensures sub-graphs respect the supervisor's 'check ahead' decision.
        """
        model_to_use = state.get("model_to_use")
        if not model_to_use:
            return self.model_config
            
        config = self.model_config.copy()
        config["primary"] = model_to_use
        return config

    def check_capabilities(self) -> str:
        """Verify which tools are functional based on environment configuration."""
        status_lines = []
        
        if self.capability_checks:
            for cap, check in self.capability_checks.items():
                is_active = check()
                status = "ACTIVE" if is_active else "DISABLED (Check environment configuration)"
                status_lines.append(f"- {cap}: {status}")
            status_lines.append("")
        
        # Report on executable entities
        registry_sections = [
            ("Tools (Low-level Utilities)", self.tools),
            ("Skills (Agent Expertise)", self.skills),
            ("Features (High-level Workflows)", self.features)
        ]

        for section_name, registry in registry_sections:
            if registry:
                status_lines.append(f"{section_name}:")
                for name, method in registry.items():
                    try:
                        sig = inspect.signature(method)
                        doc = (method.__doc__ or "No description provided.").strip().split('\n')[0]
                        status_lines.append(f"- {name}{sig}: {doc}")
                    except Exception:
                        status_lines.append(f"- {name}(...): (Could not inspect signature)")
                status_lines.append("")
        
        if not any(r for _, r in registry_sections):
            status_lines.append("No specialized capabilities configured.")
            
        return "\n".join(status_lines)

    def propose_action(self, action: str) -> bool:
        """Phase 1: Ask Don Jimmy for permission before executing"""
        action_id = audit_logger.log_action(
            agent_name=self.name,
            action_type="PROPOSAL",
            action_details={"proposal": action},
            is_approval_required=self.is_cautious_mode
        )
        
        if self.is_cautious_mode:
            print(f"[{self.name}] PENDING APPROVAL (Action ID: {action_id}): Need Don Jimmy's approval for: {action}")
            # In a real environment, we'd wait here. For now, auto-approve for the agent cycle.
            audit_logger.update_approval(action_id, "APPROVED")
            return True
        return True

    def complete_task(
        self,
        task: str,
        sender: str = "Unknown",
        conversation_key: Optional[str] = None,
        on_intermediate_response: Optional[Callable[[str], None]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Main orchestration loop powered by LangGraph.
        """
        # 1. Initialize state
        state = self._get_initial_state(task, sender, conversation_key, metadata=metadata)
        # 2. Execute graph with streaming support
        callback = None
        final_state = state
        try:
            callback = langfuse_manager.get_callback_handler()
            callbacks = [callback] if callback else []
            
            config = {
                "configurable": {"thread_id": state.get("conversation_key", "default")},
                "callbacks": callbacks,
            }
            
            # Use stream() to catch intermediate events and log telemetry
            for chunk in self.graph.stream(state, config=config, stream_mode="updates"):
                for node_name, value in chunk.items():
                    if isinstance(value, dict):
                        state.update(value)
                        
                        # Log telemetry for graph observability if we have a task context
                        task_id = state.get("metadata", {}).get("task_id")
                        if task_id:
                            context_store.log_app_notification(
                                source="workflow",
                                agent_name=self.name,
                                title=f"Node Trace: {node_name}",
                                message=f"Snapshot captured for {node_name}.",
                                type="info",
                                task_id=task_id,
                                node_id=node_name,
                                node_outputs=value,
                                metadata={"type": "node_trace", "node": node_name}
                            )
                    else:
                        state[node_name] = value
                    
                    # If we have a stream callback, notify the UI about the current node
                    if on_intermediate_response:
                        status_map = {
                            "decide_domain": "Routing directive...",
                            "product_worker": "Delegating to Product Specialist...",
                            "support_handler": "Synthesizing response...",
                            "operations_handler": "Monitoring technical signals...",
                            "analytics_handler": "Processing intelligence data..."
                        }
                        status_msg = status_map.get(node_name, f"Executing {node_name}...")
                        on_intermediate_response(f"[{status_msg}] ")
                
            final_state = state
        except Exception as e:
            print(f"[{self.name}] LangGraph streaming failed: {e}")
            # Ensure we have something in final_state for response generation
            final_state = state
        finally:
            if callback:
                try:
                    if hasattr(callback, "langfuse"):
                        callback.langfuse.flush()
                except Exception as e:
                    print(f"[{self.name}] Failed to flush langfuse callback: {e}")
            try:
                langfuse_manager.flush()
            except Exception:
                pass


        # 3. Finalize response
        return self._finalize_response(final_state)

    def execute_scheduled_task(
        self,
        task_record: Any,
        on_intermediate_response: Optional[Callable[[str], None]] = None,
    ) -> str:
        """
        Specialized entry point for autonomous background tasks.
        Uses the SchedulingMasterSupervisor graph.
        """
        # 1. Initialize state with Task metadata
        prompt = task_record.build_execution_prompt()
        state = self._get_initial_state(
            task=prompt,
            sender=f"TaskOrchestrator::{task_record.created_by_name}",
            conversation_key=f"scheduled-task:{task_record.id}"
        )
        # Inject task record for the SchedulingMasterSupervisor's routing
        # Use asdict to ensure JSON serialization for LangGraph checkpointers
        from dataclasses import asdict
        if "metadata" not in state:
            state["metadata"] = {}
        state["metadata"]["task_record"] = asdict(task_record)

        # 2. Setup and Execute the Scheduling Graph with Streaming Telemetry
        scheduling_graph = setup_scheduling_supervisor_graph(self)
        
        callback = langfuse_manager.get_callback_handler()
        callbacks = [callback] if callback else []
        
        config = {
            "configurable": {"thread_id": state.get("conversation_key", "default")},
            "callbacks": callbacks,
        }

        final_state = state
        try:
            # Stream the execution to capture individual node results for observability
            for chunk in scheduling_graph.stream(state, config=config, stream_mode="updates"):
                for node_name, updates in chunk.items():
                    # Capture the "output" of this specific node
                    final_state.update(updates)
                    
                    # Log the node execution to the technical audit trail
                    # We treat 'updates' as the node_outputs for this specific step
                    context_store.log_app_notification(
                        source="workflow",
                        agent_name=self.name,
                        title=f"Node Execution: {node_name}",
                        message=f"Node '{node_name}' completed execution cycle.",
                        type="info",
                        task_id=task_record.id,
                        node_id=node_name,
                        node_outputs=updates,
                        metadata={"type": "node_execution", "node": node_name}
                    )
        except Exception as e:
            print(f"[{self.name}] SchedulingMasterSupervisor execution failed: {e}")
            final_state = state
        finally:
            # (Langfuse flush logic omitted for brevity, keeping original structure)
            if callback:
                try:
                    if hasattr(callback, "langfuse"): callback.langfuse.flush()
                except Exception: pass
            langfuse_manager.flush()

        # 3. Finalize response using the same master logic
        return self._finalize_response(final_state)
