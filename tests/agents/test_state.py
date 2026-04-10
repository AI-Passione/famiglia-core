import pytest
from famiglia_core.agents.orchestration.utils.state import AgentState

def test_agent_state_instantiation():
    """Verify that AgentState can be instantiated with its expected keys."""
    state: AgentState = {
        "task": "Test task",
        "sender": "Jimmy",
        "conversation_key": "conv_123",
        "memories": [],
        "history": [],
        "action_id": "act_456",
        "routing_mode": "support",
        "model_to_use": "fine-tuned-model",
        "used_model": None,
        "final_response": "Hello!",
        "thread_ts": "ts_123",
        "tool_trigger": {"name": "test_tool"},
        "metadata": {"foo": "bar"}
    }
    
    assert state["task"] == "Test task"
    assert state["sender"] == "Jimmy"
    assert state["metadata"]["foo"] == "bar"

def test_agent_state_optional_fields():
    """Verify that AgentState works with only required fields (if any)."""
    # Since total=False, all fields are optional from a TypedDict perspective
    state: AgentState = {}
    state["task"] = "Minimal task"
    
    assert state["task"] == "Minimal task"
    assert "sender" not in state
