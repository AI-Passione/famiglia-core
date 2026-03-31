import pytest

from src.agents.soul_registry import load_agent_soul, resolve_agent_id


def test_resolve_agent_id_by_name():
    assert resolve_agent_id(agent_name="Alfredo") == "alfredo"
    assert resolve_agent_id(agent_name="Dr. Rossini") == "rossini"
    assert resolve_agent_id(agent_name="Riccado") == "riccado"


def test_load_agent_soul_success():
    soul = load_agent_soul(agent_id="alfredo", agent_name="Alfredo")
    assert "You are Alfredo" in soul


def test_load_agent_soul_rejects_name_mismatch():
    with pytest.raises(ValueError):
        load_agent_soul(agent_id="alfredo", agent_name="Vito")
