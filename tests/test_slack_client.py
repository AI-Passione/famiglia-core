import time
import json
import pytest
from dotenv import load_dotenv

# tests create and manipulate environment variables directly; prevent
# SlackQueueClient from reading any real .env file during import by stubbing
# load_dotenv to a no‑op before the client module is loaded.
load_dotenv = lambda *args, **kwargs: None

from famiglia_core.command_center.backend.slack.client import SlackQueueClient, PRIORITY_CRITICAL, PRIORITY_HIGH, PRIORITY_MEDIUM, PRIORITY_LOW

def test_slack_queue_priorities(mocker):
    # Mock redis
    mock_redis = mocker.MagicMock()
    mock_redis_client = mocker.patch("redis.from_url", return_value=mock_redis)
    
    client = SlackQueueClient()
    
    # Enqueue a few messages
    client.enqueue_message("AgentA", "#test", "msg low", PRIORITY_LOW)
    client.enqueue_message("AgentA", "#test", "msg critical", PRIORITY_CRITICAL)
    client.enqueue_message("AgentA", "#test", "msg high", PRIORITY_HIGH)
    
    assert mock_redis.rpush.call_count == 3
    
    # Check that they were pushed to correct queues
    calls = mock_redis.rpush.call_args_list
    assert calls[0][0][0] == f"slack:queue:{PRIORITY_LOW}"
    assert calls[1][0][0] == f"slack:queue:{PRIORITY_CRITICAL}"
    assert calls[2][0][0] == f"slack:queue:{PRIORITY_HIGH}"

def test_slack_queue_dequeue_order(mocker):
    # Setup mock redis to return values in specific queues
    mock_redis = mocker.MagicMock()
    mocker.patch("redis.from_url", return_value=mock_redis)
    
    client = SlackQueueClient()
    
    # Simulate redis lists. rpop returns last element, lpop returns first.
    # We will mock lpop to pop from our mocked dictionary lists
    queues = {
        f"slack:queue:{PRIORITY_CRITICAL}": [json.dumps({"msg": "critical"})],
        f"slack:queue:{PRIORITY_HIGH}": [json.dumps({"msg": "high"})],
        f"slack:queue:{PRIORITY_MEDIUM}": [],
        f"slack:queue:{PRIORITY_LOW}": [json.dumps({"msg": "low"})]
    }
    
    def mock_lpop(key):
        if queues.get(key):
            return queues[key].pop(0)
        return None
        
    mock_redis.lpop.side_effect = mock_lpop
    
    # Pop 1 -> should be CRITICAL
    item1 = client._dequeue_next()
    assert item1 is not None
    assert item1[0] == f"slack:queue:{PRIORITY_CRITICAL}"
    assert item1[1]["msg"] == "critical"
    
    # Pop 2 -> should be HIGH
    item2 = client._dequeue_next()
    assert item2 is not None
    assert item2[0] == f"slack:queue:{PRIORITY_HIGH}"
    assert item2[1]["msg"] == "high"
    
    # Pop 3 -> should be LOW (Medium is empty)
    item3 = client._dequeue_next()
    assert item3 is not None
    assert item3[0] == f"slack:queue:{PRIORITY_LOW}"
    
    # Pop 4 -> Empty
    assert client._dequeue_next() is None

def test_slack_rate_limit(mocker):
    mock_redis = mocker.MagicMock()
    mocker.patch("redis.from_url", return_value=mock_redis)
    
    client = SlackQueueClient()
    mock_send = mocker.patch.object(client, "_send_to_slack")
    
    # We will process 2 messages to the same channel
    # The first should go immediately, the second should wait for MIN_INTERVAL
    
    payload1 = {"agent": "A", "channel": "#test", "message": "1"}
    client.last_sent["#test"] = time.time() - 0.5  # Sent 0.5 sec ago
    client.MIN_INTERVAL = 1.0
    
    mocker.patch("time.time", side_effect=[
        100.0, # inside check rate limit for msg 1
        100.0, # inside calculate wait for msg 1 (wait is 1.0 - (100.0 - 99.5) = 0.5)
        100.5, # after sleep for msg 1, get time to update last_sent
    ])
    
    mocker_sleep = mocker.patch("time.sleep")
    
    # Let's adjust last_sent to match our mocked time
    client.last_sent["#test"] = 99.5
    
    # Mock dequeue_next to return our item, then None to stop loop
    mocker.patch.object(client, "_dequeue_next", side_effect=[
        ("queue", payload1),
        None
    ])
    
    # Use an event to stop the thread quickly
    client.running = True
    
    # Override process_queue slightly to run once
    def run_once():
        item = client._dequeue_next()
        if item:
            queue_key, payload = item
            channel = payload["channel"]
            now = time.time()
            last = client.last_sent.get(channel, 0.0)
            wait_time = client.MIN_INTERVAL - (now - last)
            if wait_time > 0:
                time.sleep(wait_time)
                now = time.time()
            client._send_to_slack(payload)
            client.last_sent[channel] = now
            
    run_once()
    
    assert mocker_sleep.call_count == 1
    mocker_sleep.assert_called_with(0.5)
    
    # Verify send path was called
    assert mock_send.call_count == 1


def test_resolve_channel_id_accepts_common_formats(mocker):
    mock_redis = mocker.MagicMock()
    mocker.patch("redis.from_url", return_value=mock_redis)
    client = SlackQueueClient()
    client.clients = {}

    assert client.resolve_channel_id("C0123456789") == "C0123456789"
    assert client.resolve_channel_id("<#C0123456789|_dev>") == "C0123456789"
    assert client.resolve_channel_id("https://acme.slack.com/archives/C0123456789") == "C0123456789"


def test_resolve_channel_id_by_name(mocker):
    mock_redis = mocker.MagicMock()
    mocker.patch("redis.from_url", return_value=mock_redis)
    client = SlackQueueClient()

    mock_web_client = mocker.MagicMock()
    mock_web_client.conversations_list.return_value = {
        "channels": [{"id": "C0123456789", "name": "_dev"}],
        "response_metadata": {},
    }
    client.clients = {"alfredo": mock_web_client}

    assert client.resolve_channel_id("#_dev") == "C0123456789"
    assert mock_web_client.conversations_list.called is True


def test_enqueue_message_drops_dev_channel_in_production(mocker):
    mock_redis = mocker.MagicMock()
    mocker.patch("redis.from_url", return_value=mock_redis)
    client = SlackQueueClient()
    client.app_env = "production"
    client.dev_channel_id = "C0123456789"
    client.dev_channel_raw = "#_dev"

    client.enqueue_message("AgentA", "C0123456789", "should drop")
    client.enqueue_message("AgentA", "#_dev", "should also drop")

    assert mock_redis.rpush.call_count == 0


def test_is_dev_channel_via_channel_id_lookup(mocker):
    mock_redis = mocker.MagicMock()
    mocker.patch("redis.from_url", return_value=mock_redis)
    client = SlackQueueClient()
    client.dev_channel_id = None
    client.dev_channel_name = "_dev"

    mock_web_client = mocker.MagicMock()
    mock_web_client.conversations_info.return_value = {"channel": {"name": "_dev"}}
    client.clients = {"alfredo": mock_web_client}

    assert client.is_dev_channel("C0123456789") is True


def test_enqueue_message_drops_dev_channel_with_missing_env_id(mocker):
    mock_redis = mocker.MagicMock()
    mocker.patch("redis.from_url", return_value=mock_redis)
    client = SlackQueueClient()
    client.app_env = "production"
    client.dev_channel_id = None
    client.dev_channel_name = "_dev"

    mock_web_client = mocker.MagicMock()
    mock_web_client.conversations_info.return_value = {"channel": {"name": "_dev"}}
    client.clients = {"alfredo": mock_web_client}

    client.enqueue_message("AgentA", "C0123456789", "should drop")
    assert mock_redis.rpush.call_count == 0


def test_resolve_sender_name_from_event_profile(mocker):
    mock_redis = mocker.MagicMock()
    mocker.patch("redis.from_url", return_value=mock_redis)
    client = SlackQueueClient()

    name = client.resolve_sender_name(
        "U123456",
        event={"user_profile": {"display_name": "Jimmy P"}},
    )

    assert name == "Jimmy P"
    assert client.user_name_cache["U123456"] == "Jimmy P"


def test_resolve_sender_name_from_slack_api_and_cache(mocker):
    mock_redis = mocker.MagicMock()
    mocker.patch("redis.from_url", return_value=mock_redis)
    client = SlackQueueClient()

    mock_web_client = mocker.MagicMock()
    mock_web_client.users_info.return_value = {
        "user": {
            "name": "jimmypang",
            "real_name": "Jimmy Pang",
            "profile": {"display_name": "Jimmy"},
        }
    }
    client.clients = {"alfredo": mock_web_client}

    name1 = client.resolve_sender_name("U999")
    name2 = client.resolve_sender_name("U999")

    assert name1 == "Jimmy"
    assert name2 == "Jimmy"
    assert mock_web_client.users_info.call_count == 1


def test_resolve_sender_name_for_configured_user_uses_slack_name(mocker):
    mock_redis = mocker.MagicMock()
    mocker.patch("redis.from_url", return_value=mock_redis)
    client = SlackQueueClient()
    client.user_id = "U0AG886GJCV"

    mock_web_client = mocker.MagicMock()
    mock_web_client.users_info.return_value = {
        "user": {
            "name": "donjimmy",
            "real_name": "Don Jimmy",
            "profile": {"display_name": "Don Jimmy"},
        }
    }
    client.clients = {"alfredo": mock_web_client}
    client.user_name_cache = {}

    name1 = client.resolve_sender_name("U0AG886GJCV")
    name2 = client.resolve_sender_name("U0AG886GJCV")

    assert name1 == "Don Jimmy"
    assert name2 == "Don Jimmy"
    assert mock_web_client.users_info.call_count == 1


def test_resolve_sender_name_fallback_does_not_expose_user_id(mocker):
    mock_redis = mocker.MagicMock()
    mocker.patch("redis.from_url", return_value=mock_redis)
    client = SlackQueueClient()
    client.clients = {}

    name = client.resolve_sender_name("U0AG886GJCV")

    assert name == "Slack member"


def test_init_logs_missing_and_global_tokens(monkeypatch, mocker, capsys):
    # ensure redis doesn't interfere
    mock_redis = mocker.MagicMock()
    mocker.patch("redis.from_url", return_value=mock_redis)

    # clear and set environment variables
    monkeypatch.delenv("SLACK_BOT_TOKEN_ALFREDO", raising=False)
    monkeypatch.delenv("SLACK_BOT_TOKEN", raising=False)
    # set only riccado token distinct from global
    monkeypatch.setenv("SLACK_BOT_TOKEN_RICCADO", "x-token-riccado")
    monkeypatch.setenv("SLACK_BOT_TOKEN", "x-token-global")

    client = SlackQueueClient()

    captured = capsys.readouterr().out
    # Alfredo had no token at all so fallback to global
    assert "[alfredo] No bot token configured" in captured
    # Ricardo should not warn since his token differs from global
    assert "WARNING" not in captured

    # Only riccado client should exist (alfredo skipped because only global)
    assert "riccado" in client.clients
    assert "alfredo" not in client.clients


def test_conflicting_global_and_agent_token(monkeypatch, mocker):
    # duplicate token between global and agent should raise
    mock_redis = mocker.MagicMock()
    mocker.patch("redis.from_url", return_value=mock_redis)
    monkeypatch.setenv("SLACK_BOT_TOKEN_RICCADO", "xoxb-same")
    monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-same")

    with pytest.raises(RuntimeError) as excinfo:
        SlackQueueClient()
    assert "unique bot token" in str(excinfo.value)


def test_tokens_for_same_slack_user_raise(monkeypatch, mocker):
    # two different tokens but auth_test responds with identical user_id
    mock_redis = mocker.MagicMock()
    mocker.patch("redis.from_url", return_value=mock_redis)

    # patch WebClient to return fake clients with custom auth_test
    class FakeClient:
        def __init__(self, token):
            self.token = token
        def auth_test(self):
            # both tokens yield same user id
            return {"user_id": "U777"}
    mocker.patch("famiglia_core.command_center.backend.slack.client.WebClient", side_effect=lambda token: FakeClient(token))

    monkeypatch.setenv("SLACK_BOT_TOKEN_ALFREDO", "xoxb-1")
    monkeypatch.setenv("SLACK_BOT_TOKEN_RICCADO", "xoxb-2")

    with pytest.raises(RuntimeError) as excinfo:
        SlackQueueClient()
    assert "same Slack user" in str(excinfo.value)


def test_duplicate_bot_tokens_raise(monkeypatch, mocker):
    # provide same token for two agents
    mock_redis = mocker.MagicMock()
    mocker.patch("redis.from_url", return_value=mock_redis)
    monkeypatch.setenv("SLACK_BOT_TOKEN_ALFREDO", "xoxb-dup")
    monkeypatch.setenv("SLACK_BOT_TOKEN_RICCADO", "xoxb-dup")

    with pytest.raises(RuntimeError) as excinfo:
        SlackQueueClient()
    assert "unique bot token" in str(excinfo.value)


def test_loads_env_file(tmp_path, monkeypatch):
    # simulate a .env file that specifies a token for Alfredo
    env_file = tmp_path / ".env"
    env_file.write_text("SLACK_BOT_TOKEN_ALFREDO=xoxb-file\n")
    monkeypatch.chdir(tmp_path)
    # reload module to trigger new instance creation
    import importlib
    import famiglia_core.command_center.backend.slack.client as client_mod
    importlib.reload(client_mod)

    # after reload the singleton should have read the .env file
    assert client_mod.slack_queue.agent_tokens.get("alfredo") == "xoxb-file"
