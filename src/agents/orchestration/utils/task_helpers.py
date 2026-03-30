import os
import yaml
import re
from pathlib import Path
from dataclasses import dataclass, fields
from typing import Any, Dict, Optional, List
from src.db.agents.context_store import context_store

# --- Constants & Config (Consolidated from tasks_config.py) ---
_HERE = Path(__file__).resolve().parent
_YAML_PATH = _HERE / "tasks.yml"

def _load_config() -> Dict[str, Any]:
    if not _YAML_PATH.exists():
        # Fallback to empty if not found
        return {}
    with open(_YAML_PATH, "r") as f:
        return yaml.safe_load(f) or {}

_CONFIG = _load_config()
_TYPES_CONFIG = _CONFIG.get("task_types", {})

TASK_TYPE_REMINDER = "reminder"
TASK_TYPE_MARKET_RESEARCH = "market_research"
TASK_TYPE_PRD_DRAFTING = "prd_drafting"
TASK_TYPE_FEATURE_REQUEST = "feature_request"
TASK_TYPE_CODING_CODE_ANALYSIS = "coding_code_analysis"
TASK_TYPE_CODING_IMPLEMENTATION = "coding_implementation"
TASK_TYPE_ALFREDO_GREETING = "alfredo_greeting"
TASK_TYPE_PRD_AUTOSCAN = "prd_review_autoscan"

SCHEDULED_TASK_TYPES = tuple(_CONFIG.get("scheduled_task_types", []))

TASK_TYPE_TO_EXPECTED_AGENT = {
    k: v.get("expected_agent") for k, v in _TYPES_CONFIG.items() if v.get("expected_agent")
}
TASK_TYPE_TO_PRIORITY = {
    k: v.get("priority") for k, v in _TYPES_CONFIG.items() if v.get("priority")
}

def get_task_type_config(task_type: str) -> Dict[str, Any]:
    """Retrieve full configuration for a specific task type."""
    return _TYPES_CONFIG.get(task_type, {})

# --- Task Model (Consolidated from task_models.py) ---
@dataclass
class Task:
    id: int
    title: str
    task_payload: str
    status: str = "queued"
    priority: str = "medium"
    created_by_type: str = "ai_agent"
    created_by_name: str = "system"
    expected_agent: Optional[str] = None
    assigned_agent: Optional[str] = None
    eta_pickup_at: Optional[Any] = None
    eta_completion_at: Optional[Any] = None
    picked_up_at: Optional[Any] = None
    completed_at: Optional[Any] = None
    result_summary: Optional[str] = None
    error_details: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    schedule_config: Optional[Dict[str, Any]] = None
    recurring_task_id: Optional[int] = None
    last_spawned_at: Optional[Any] = None
    created_at: Optional[Any] = None
    updated_at: Optional[Any] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Task":
        # Robust filtering: only pass keys that match the dataclass fields
        safe_fields = {f.name for f in fields(cls)}
        filtered_data = {k: v for k, v in data.items() if k in safe_fields}
        return cls(**filtered_data)

    @property
    def safe_metadata(self) -> Dict[str, Any]:
        return self.metadata if isinstance(self.metadata, dict) else {}

    @property
    def task_type(self) -> str:
        tt = (self.safe_metadata.get("task_type") or "").strip().lower()
        if tt:
            return tt
        if self.safe_metadata.get("kind") == "slack_reminder":
            return TASK_TYPE_REMINDER
        return "general"

    def resolve_assignee(self, available_agents: List[str]) -> Optional[str]:
        # 1. Check required agent from config
        config = get_task_type_config(self.task_type)
        required = config.get("expected_agent")
        if required and required in available_agents:
            return required

        # 2. Check task metadata/fields
        expected = (self.expected_agent or "").strip().lower()
        assigned = (self.assigned_agent or "").strip().lower()
        if expected and expected in available_agents:
            return expected
        if assigned and assigned in available_agents:
            return assigned

        # 3. Fallbacks
        if "tommy" in available_agents:
            return "tommy"
        if "alfredo" in available_agents:
            return "alfredo"
        return available_agents[0] if available_agents else None

    def build_execution_prompt(self) -> str:
        repo_name = (self.safe_metadata.get("repo_name") or "").strip()
        prd_reference = (self.safe_metadata.get("prd_reference") or "").strip()
        extras = []
        if repo_name:
            extras.append(f"- Relevant GitHub repo: {repo_name}")
        if prd_reference:
            extras.append(f"- PRD reference: {prd_reference}")
        extras_block = "\n".join(extras) if extras else "- No extra metadata provided."
        
        return (
            f"Scheduled task #{self.id} ({self.task_type}): {self.title}\n\n"
            f"Instructions:\n{self.task_payload}\n\n"
            f"Task metadata:\n{extras_block}\n\n"
            "Execution constraints:\n"
            "- Provide concise execution output.\n"
            "- If blocked, report explicit blockers.\n"
            "- This task is running from the autonomous scheduled queue."
        )

    def result_looks_failed(self, result: str) -> bool:
        lower = (result or "").strip().lower()
        if not lower:
            return False
        if "no errors" in lower or "without errors" in lower:
            return False
        failure_patterns = (
            r"\bfailed to\b",
            r"\berror:",
            r"\bexception\b",
            r"\bpermission denied\b",
            r"\bnot authorized\b",
            r"\bunauthorized\b",
            r"\bcannot\b",
        )
        if lower.startswith("failed"):
            return True
        return any(re.search(pattern, lower) for pattern in failure_patterns)

    def get_output_channel(self) -> Optional[str]:
        config = get_task_type_config(self.task_type)
        direct_id = config.get("output_channel_id")
        if direct_id:
            return direct_id
        
        # Specific overrides or hardcoded fallback for reminders
        if self.task_type == TASK_TYPE_REMINDER:
            return self.safe_metadata.get("slack_channel")
        
        # General Fallback
        return "C0AGFEBPBJ8" # Coordination Channel

    def get_completion_status(self, is_failure: bool) -> str:
        if is_failure:
            return "failed"
        config = get_task_type_config(self.task_type)
        return config.get("completion_status", "completed")

# --- Task Tools (Consolidated from task_tools.py) ---
class TaskTools:
    """Class responsible for scheduled task tools for agents."""

    def create_scheduled_task(
        self,
        title: str,
        task_payload: str,
        priority: str = "medium",
        expected_agent: Optional[str] = None,
        eta_pickup_at: Optional[str] = None,
        eta_completion_at: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        schedule_config: Optional[Dict[str, Any]] = None,
        user_prompt: Optional[str] = None,
    ) -> str:
        """Create a new task to be picked up by an agent later."""
        if not hasattr(self, "propose_action"):
             print(f"[{self.name}] Capability check: propose_action not found.")
             return "Error: Internal agent capability mismatch."

        if self.propose_action(f"Create scheduled task: {title}"):
            print(f"[{self.name}] Tool executing: create_scheduled_task({title!r})")
            try:
                task_data = context_store.create_scheduled_task(
                    title=title,
                    task_payload=task_payload,
                    created_by_type="ai_agent",
                    created_by_name=self.name,
                    priority=priority,
                    expected_agent=expected_agent,
                    eta_pickup_at=eta_pickup_at,
                    eta_completion_at=eta_completion_at,
                    metadata=metadata,
                    schedule_config=schedule_config,
                )
                if task_data:
                    return f"Successfully created scheduled task #{task_data['id']}: {title}"
                return "Failed to create scheduled task."
            except Exception as e:
                return f"Error creating scheduled task: {e}"


    def list_scheduled_tasks_tool(self, status: Optional[str] = None, user_prompt: Optional[str] = None) -> str:
        """List scheduled tasks from the queue."""
        if self.propose_action("Listing scheduled tasks"):
            print(f"[{self.name}] Tool executing: list_scheduled_tasks_tool()")
            try:
                tasks = context_store.get_scheduled_tasks_overview(queue_limit=20)
                queue = tasks.get("queue_line", [])
                if not queue:
                    return "No pending scheduled tasks found."
                
                output = ["Currently Queued Tasks:"]
                for t in queue:
                    assignee = t.get('expected_agent') or 'any'
                    recurring = " [RECURRING]" if t.get('schedule_config') else ""
                    output.append(f"- #{t['id']} [{t['priority']}] {t['title']} (Assignee: {assignee}){recurring}")
                return "\n".join(output)
            except Exception as e:
                return f"Failed to list scheduled tasks: {e}"


    def cancel_scheduled_task_tool(self, task_id: int, user_prompt: Optional[str] = None) -> str:
        """Cancel a queued scheduled task."""
        if self.propose_action(f"Cancel scheduled task #{task_id}"):
            print(f"[{self.name}] Tool executing: cancel_scheduled_task_tool({task_id})")
            try:
                success = context_store.cancel_scheduled_task(task_id)
                if success:
                    return f"Successfully cancelled scheduled task #{task_id}."
                return f"Failed to cancel scheduled task #{task_id}. It might not exist or is already finished."
            except Exception as e:
                return f"Error cancelling scheduled task: {e}"
