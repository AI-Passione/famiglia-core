import pytest

from src.agents.llm.client import LLMClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_client(monkeypatch, remote_host="http://192.168.178.166:11434"):
    """Return a fresh LLMClient with OLLAMA_REMOTE_HOST set."""
    monkeypatch.setenv("OLLAMA_REMOTE_HOST", remote_host)
    return LLMClient()


# ---------------------------------------------------------------------------
# Existing tests (updated for new tuple return signature)
# ---------------------------------------------------------------------------

def test_llm_client_primary_success(monkeypatch):
    client = _make_client(monkeypatch)
    monkeypatch.setenv("GEMINI_API_KEY", "test")

    config = {"primary": "gemini-2.0-flash", "global_fallback": "ollama-gemma3"}
    response, model = client.complete("Hello", config)
    assert "Gemini mock" in response
    assert model == "gemini-2.0-flash"


def test_llm_client_fallback_to_local_ollama(monkeypatch):
    client = _make_client(monkeypatch)

    monkeypatch.setattr(client, "_is_provider_available", lambda m: m == "ollama-gemma3")
    monkeypatch.setattr(client, "_dispatch", lambda p, m, o: ("[Ollama Gemma3] hello" if m == "ollama-gemma3" else (_ for _ in ()).throw(Exception("nope"))))

    config = {"primary": "nonexistent", "global_fallback": "ollama-gemma3"}
    response, model = client.complete("Hello", config)
    assert "[Ollama Gemma3]" in response


def test_llm_client_appends_local_fallback(monkeypatch):
    client = _make_client(monkeypatch)
    attempted = []

    def fake_available(model):
        attempted.append(model)
        return model.startswith("ollama-")

    monkeypatch.setattr(client, "_is_provider_available", fake_available)
    monkeypatch.setattr(client, "_dispatch", lambda p, m, o: "[Ollama local] default")

    config = {"primary": "claude-code", "global_fallback": "gemini-2.0-flash"}
    response, _ = client.complete("Hello", config)

    assert "[Ollama local] default" in response
    assert any(model.startswith("ollama-") for model in attempted)


def test_llm_client_all_fail_returns_mock_if_all_ollama_down(monkeypatch):
    client = _make_client(monkeypatch)

    monkeypatch.setattr(client, "_is_provider_available", lambda m: False)
    monkeypatch.setattr(client, "_is_ollama_service_available", lambda: False)
    monkeypatch.setattr(client, "_is_remote_ollama_available", lambda: False)

    config = {"primary": "nonexistent", "global_fallback": "also-nonexistent"}
    response, model = client.complete("Hello", config)
    assert "Ollama mock" in response
    assert model == "mock-fallback"


def test_llm_client_all_fail_raises_if_any_ollama_up(monkeypatch):
    client = _make_client(monkeypatch)

    monkeypatch.setattr(client, "_is_provider_available", lambda m: False)
    monkeypatch.setattr(client, "_is_ollama_service_available", lambda: False)
    monkeypatch.setattr(client, "_is_remote_ollama_available", lambda: True)

    config = {"primary": "nonexistent", "global_fallback": "also-nonexistent"}
    with pytest.raises(ValueError, match="All configured LLM providers failed"):
        client.complete("Hello", config)


def test_ensure_ollama_ready_falls_back_to_remote_when_local_unavailable(monkeypatch):
    client = _make_client(monkeypatch)

    monkeypatch.setattr(client, "_ensure_local_ollama_ready", lambda auto_pull=True: False)
    monkeypatch.setattr(client, "_is_remote_ollama_available", lambda: True)
    monkeypatch.setattr(client, "_ensure_model_pulled", lambda model, host=None: None)

    assert client.ensure_ollama_ready(auto_pull=True) is True


# ---------------------------------------------------------------------------
# NEW: 3-tier ordering tests
# ---------------------------------------------------------------------------

def test_build_attempts_order_cloud_before_local_before_remote(monkeypatch):
    """_build_attempts must always return cloud < local ollama < remote-ollama."""
    client = _make_client(monkeypatch)
    attempts = client._build_attempts(
        primary="gemini-2.0-flash",
        secondary="ollama-gemma3",
        global_fallback="remote-ollama-gemma3",
    )
    cloud = [m for m in attempts if m.startswith("gemini")]
    local = [m for m in attempts if m.startswith("ollama-")]
    remote = [m for m in attempts if m.startswith("remote-ollama-")]

    assert cloud, "Should have at least one cloud model"
    assert local, "Should have at least one local ollama model"
    assert remote, "Should have at least one remote-ollama model"

    # Every cloud index < every local index < every remote index
    assert max(attempts.index(m) for m in cloud) < min(attempts.index(m) for m in local)
    assert max(attempts.index(m) for m in local) < min(attempts.index(m) for m in remote)


def test_local_ollama_used_before_remote_when_cloud_fails(monkeypatch):
    """When cloud is unavailable and local Ollama is reachable, local is chosen before remote."""
    client = _make_client(monkeypatch)

    calls = []

    def fake_available(model):
        if any(model.startswith(p) for p in ("gemini", "perplexity", "claude")):
            return False
        if model.startswith("ollama-"):
            return True
        if model.startswith("remote-ollama-"):
            return True  # reachable, but should not be chosen first
        return False

    def fake_dispatch(prompt, model, options):
        calls.append(model)
        if model.startswith("ollama-"):
            return "local ollama response"
        raise RuntimeError("should not reach remote")

    monkeypatch.setattr(client, "_is_provider_available", fake_available)
    monkeypatch.setattr(client, "_dispatch", fake_dispatch)

    config = {"primary": "gemini-2.0-flash", "global_fallback": "ollama-gemma3"}
    response, model_used = client.complete("Hello", config)

    assert "local ollama" in response
    assert model_used.startswith("ollama-")
    # Make sure we never tried remote ollama
    assert not any(c.startswith("remote-ollama-") for c in calls)


def test_remote_ollama_used_when_local_is_down(monkeypatch):
    """When cloud/local are unavailable and remote Ollama is reachable, remote Ollama is used."""
    client = _make_client(monkeypatch)

    def fake_available(model):
        if model.startswith("remote-ollama-"):
            return True
        if model.startswith("ollama-"):
            return False
        return False  # no cloud keys

    def fake_dispatch(prompt, model, options):
        if model.startswith("remote-ollama-"):
            return "remote ollama response"
        raise RuntimeError("should not reach here")

    monkeypatch.setattr(client, "_is_provider_available", fake_available)
    monkeypatch.setattr(client, "_dispatch", fake_dispatch)
    monkeypatch.setattr(client, "_is_ollama_service_available", lambda: False)
    monkeypatch.setattr(client, "_is_remote_ollama_available", lambda: True)

    config = {"primary": "perplexity-sonar-pro", "global_fallback": "ollama-gemma3"}
    response, model_used = client.complete("Hello", config)

    assert "remote ollama" in response
    assert model_used.startswith("remote-ollama-")


def test_remote_ollama_sentinel_added_automatically(monkeypatch):
    """_build_attempts must auto-insert a remote-ollama sentinel even when not in model_config."""
    client = _make_client(monkeypatch)
    attempts = client._build_attempts(
        primary="gemini-2.0-flash",
        secondary=None,
        global_fallback="ollama-gemma3",
    )
    remote = [m for m in attempts if m.startswith("remote-ollama-")]
    assert remote, "A remote-ollama sentinel must be auto-inserted"


def test_is_remote_ollama_available_returns_false_on_unreachable(monkeypatch):
    """_is_remote_ollama_available returns False when the host is unreachable."""
    client = LLMClient()
    client.ollama_remote_host = "http://0.0.0.0:19999"  # nothing listening here
    assert client._is_remote_ollama_available() is False


def test_ollama_complete_retries_once_on_empty_response(monkeypatch):
    client = _make_client(monkeypatch)

    monkeypatch.setattr(client, "_ensure_model_pulled", lambda model, host=None: None)
    monkeypatch.setattr(client, "_ensure_offloaded", lambda target_model=None, timeout_secs=30.0, host=None: True)
    monkeypatch.setattr("src.agents.llm.client.time.sleep", lambda _seconds: None)
    monkeypatch.setenv("OLLAMA_EMPTY_RESPONSE_RETRIES", "1")

    class FakeResponse:
        def __init__(self, lines):
            self.lines = lines

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def __iter__(self):
            return iter(self.lines)

    calls = {"count": 0}

    def fake_urlopen(_req, timeout=300):
        calls["count"] += 1
        if calls["count"] == 1:
            return FakeResponse([b'{"done": true}\n'])
        return FakeResponse([b'{"response": "ok", "done": true}\n'])

    monkeypatch.setattr("src.agents.llm.client.urllib.request.urlopen", fake_urlopen)

    response = client._ollama_complete(
        prompt="hi",
        model="qwen3.5:4b",
        host="http://ollama:11434",
    )

    assert response == "ok"
    assert calls["count"] == 2
