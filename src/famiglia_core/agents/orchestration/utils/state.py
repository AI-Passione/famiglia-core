from typing import Any, Dict, List, Optional, TypedDict

class AgentState(TypedDict, total=False):
    """Formal state definition for the agent, compatible with LangGraph."""
    task: str
    sender: str
    conversation_key: str
    memories: List[Dict[str, Any]]
    history: List[Dict[str, Any]]
    action_id: str
    routing_mode: str
    model_to_use: str
    used_model: Optional[str]
    final_response: Optional[str]
    thread_ts: Optional[str]
    tool_trigger: Optional[Dict[str, Any]]  # Current tool being executed
    metadata: Dict[str, Any]
