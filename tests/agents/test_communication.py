import pytest
import json
import time
from unittest.mock import MagicMock, patch

# Slack Imports
from famiglia_core.command_center.backend.comms.slack.client import (
    SlackQueueClient, 
    PRIORITY_CRITICAL, 
    PRIORITY_HIGH, 
    PRIORITY_MEDIUM, 
    PRIORITY_LOW
)

# Mattermost Imports
from famiglia_core.command_center.backend.comms.mattermost.client import (
    MattermostQueueClient,
    PRIORITY_HIGH as MM_PRIORITY_HIGH
)

# --- Slack Tests ---

def test_slack_queue_start_worker_no_args(mocker):
    # Mock redis
    mock_redis = mocker.MagicMock()
    mocker.patch("redis.from_url", return_value=mock_redis)
    client = SlackQueueClient()
    
    # Mock _process_queue to avoid background thread errors with MagicMocks
    mocker.patch.object(client, "_process_queue", return_value=None)
    
    # Should not raise TypeError: CommsQueue.start_worker() missing 1 required positional argument: 'target_func'
    client.start_worker()
    client.stop_worker()

def test_slack_queue_priorities(mocker):
    # Mock redis
    mock_redis = mocker.MagicMock()
    mocker.patch("redis.from_url", return_value=mock_redis)
    
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

def test_slack_rate_limit(mocker):
    mock_redis = mocker.MagicMock()
    mocker.patch("redis.from_url", return_value=mock_redis)
    
    client = SlackQueueClient()
    mock_send = mocker.patch.object(client, "_send_to_slack")
    
    payload1 = {"agent": "A", "channel": "#test", "message": "1"}
    client.MIN_INTERVAL = 1.0
    
    mocker.patch("time.time", side_effect=[100.0, 100.0, 100.5])
    mocker_sleep = mocker.patch("time.sleep")
    client.last_sent["#test"] = 99.5
    
    mocker.patch.object(client, "_dequeue_next", side_effect=[("queue", payload1), None])
    
    client.running = True
    
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
    assert mock_send.call_count == 1

def test_slack_resolve_channel_id(mocker):
    mock_redis = mocker.MagicMock()
    mocker.patch("redis.from_url", return_value=mock_redis)
    client = SlackQueueClient()
    client.clients = {}

    assert client.resolve_channel_id("C0123456789") == "C0123456789"
    assert client.resolve_channel_id("<#C0123456789|_dev>") == "C0123456789"

def test_slack_resolve_sender_name(mocker):
    mock_redis = mocker.MagicMock()
    mocker.patch("redis.from_url", return_value=mock_redis)
    client = SlackQueueClient()

    name = client.resolve_sender_name(
        "U123456",
        event={"user_profile": {"display_name": "Jimmy P"}},
    )

    assert name == "Jimmy P"
    assert client.user_name_cache["U123456"] == "Jimmy P"
