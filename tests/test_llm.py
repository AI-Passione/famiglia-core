import pytest
from unittest.mock import MagicMock, patch
from famiglia_core.agents.llm.client import LLMClient
from famiglia_core.agents.souls.soul_registry import load_agent_soul, resolve_agent_id

def test_llm_client_fallback_logic(monkeypatch):
    client = LLMClient()
    monkeypatch.setenv("GEMINI_API_KEY", "test")
    
    # Mock provider availability
    monkeypatch.setattr(client, "_is_provider_available", lambda m: m == "ollama-gemma3")
    monkeypatch.setattr(client, "_dispatch", lambda p, m, o: "[Ollama Gemma3]" if m == "ollama-gemma3" else "fail")

    config = {"primary": "nonexistent", "global_fallback": "ollama-gemma3"}
    response, model = client.complete("Hello", config)
    assert "[Ollama Gemma3]" in response
    assert model == "ollama-gemma3"

def test_llm_client_3_tier_ordering():
    client = LLMClient()
    attempts = client._build_attempts(
        primary="gemini-2.0-flash",
        secondary="ollama-gemma3",
        global_fallback="remote-ollama-gemma3",
    )
    
    # Cloud < Local < Remote
    attempts_list = list(attempts)
    idx_cloud = next(i for i, m in enumerate(attempts_list) if "gemini" in m)
    idx_local = next(i for i, m in enumerate(attempts_list) if m.startswith("ollama-"))
    idx_remote = next(i for i, m in enumerate(attempts_list) if m.startswith("remote-ollama-"))
    
    assert idx_cloud < idx_local < idx_remote

def test_soul_registry_resolution():
    assert resolve_agent_id(agent_name="Alfredo") == "alfredo"
    assert resolve_agent_id(agent_name="Dr. Rossini") == "rossini"
    
    # Correct way to test resolution failure
    with pytest.raises(ValueError):
        resolve_agent_id(agent_name="Unknown Person")

@patch("famiglia_core.db.agents.context_store.context_store.get_agent_soul", return_value={"persona": "Test soul"})
@patch("famiglia_core.db.agents.context_store.context_store.get_agent_traits", return_value={"skills": [], "tools": [], "workflows": [], "resources": []})
def test_load_agent_soul_success(mock_traits, mock_soul):
    soul = load_agent_soul(agent_id="alfredo", agent_name="Alfredo")
    assert "Test soul" in soul
