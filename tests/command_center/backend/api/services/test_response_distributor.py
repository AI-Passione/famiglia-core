import pytest
from unittest.mock import patch, ANY
from famiglia_core.command_center.backend.api.services.response_distributor import response_distributor

@patch("famiglia_core.command_center.backend.api.services.response_distributor.context_store")
@patch("famiglia_core.command_center.backend.api.services.response_distributor.slack_queue")
@patch("famiglia_core.command_center.backend.api.services.response_distributor.mattermost_queue")
def test_response_distributor_dispatch_web_only(mock_mm_queue, mock_slack_queue, mock_store):
    # Setup
    agent_id = "alfredo"
    text = "Hello, I am ready."
    conversation_key = "web:web-dashboard:new-thread:0"
    metadata = {"platform": "web"}
    
    # Execute
    response_distributor.dispatch(agent_id, text, conversation_key, metadata)
    
    # Verify DB logging (First class citizen)
    mock_store.log_message.assert_called_once_with(
        role="agent",
        conversation_key=conversation_key,
        agent_name=agent_id,
        content=text,
        metadata=metadata
    )
    
    # Verify no external dispatch if not configured in metadata
    mock_slack_queue.enqueue_message.assert_not_called()
    mock_mm_queue.enqueue_message.assert_not_called()

@patch("famiglia_core.command_center.backend.api.services.response_distributor.context_store")
@patch("famiglia_core.command_center.backend.api.services.response_distributor.slack_queue")
def test_response_distributor_dispatch_slack_mirror(mock_slack_queue, mock_store):
    # Setup
    agent_id = "alfredo"
    text = "Mirror this to slack."
    conversation_key = "slack:C123:T123:U123"
    metadata = {
        "platform": "slack",
        "slack_channel": "C123",
        "slack_thread_ts": "T123"
    }
    
    # Mock slack configured
    mock_slack_queue.clients = {"some_token"}
    
    # Execute
    response_distributor.dispatch(agent_id, text, conversation_key, metadata)
    
    # Verify DB logging (Always first)
    mock_store.log_message.assert_called_once()
    
    # Verify Slack Mirroring
    mock_slack_queue.enqueue_message.assert_called_once_with(
        agent=agent_id,
        channel="C123",
        message=text,
        blocks=ANY,
        file_path=None,
        file_title=None,
        thread_ts="T123",
        priority=2
    )

@patch("famiglia_core.command_center.backend.api.services.response_distributor.context_store")
@patch("famiglia_core.command_center.backend.api.services.response_distributor.mattermost_queue")
def test_response_distributor_dispatch_mattermost_mirror(mock_mm_queue, mock_store):
    # Setup
    agent_id = "alfredo"
    text = "Mirror this to mattermost."
    conversation_key = "mattermost:C456:T456:U456"
    metadata = {
        "platform": "mattermost",
        "mattermost_channel": "C456",
        "mattermost_root_id": "T456"
    }
    
    # Mock mattermost configured
    mock_mm_queue.drivers = {"some_token"}
    
    # Execute
    response_distributor.dispatch(agent_id, text, conversation_key, metadata)
    
    # Verify DB logging (Always first)
    mock_store.log_message.assert_called_once()
    
    # Verify Mattermost Mirroring
    mock_mm_queue.enqueue_message.assert_called_once_with(
        agent=agent_id,
        channel="C456",
        message=text,
        root_id="T456",
        priority=2
    )
