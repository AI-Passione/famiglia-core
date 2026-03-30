import pytest
from unittest.mock import MagicMock, patch
from src.agents.orchestration.scheduler import TaskOrchestrator
from src.agents.orchestration.utils.task_helpers import Task

@pytest.fixture
def orchestrator():
    orchestrator = TaskOrchestrator()
    agent = MagicMock()
    orchestrator.configure({"alfredo": agent})
    return orchestrator, agent

@patch("src.agents.orchestration.scheduler.slack_queue")
@patch("src.agents.orchestration.scheduler.context_store")
def test_execute_task_retries_slack_notification(mock_store, mock_slack, orchestrator):
    orchestrator_obj, agent = orchestrator
    
    # Mock task
    task_data = {
        "id": 1,
        "title": "Test Task",
        "task_payload": "Do something",
        "status": "queued",
        "priority": "medium",
        "created_by_type": "ai_agent",
        "created_by_name": "Test",
        "metadata": {"task_type": "alfredo_greeting"}
    }
    task = Task.from_dict(task_data)
    
    # Mock agent success
    agent.complete_task.return_value = "Done!"
    
    # Mock Slack failure then success
    mock_slack.post_message.side_effect = [None, "ts_123"]
    
    orchestrator_obj._execute_task(task)
    
    # Verify 2 calls to post_message (retry)
    assert mock_slack.post_message.call_count == 2
    # Verify task completed as "completed"
    mock_store.complete_scheduled_task.assert_called_once()
    args, kwargs = mock_store.complete_scheduled_task.call_args
    assert kwargs["status"] == "completed"

@patch("src.agents.orchestration.scheduler.slack_queue")
@patch("src.agents.orchestration.scheduler.context_store")
def test_execute_task_fails_if_slack_fails_after_retries(mock_store, mock_slack, orchestrator):
    orchestrator_obj, agent = orchestrator
    
    # Mock task
    task_data = {
        "id": 2,
        "title": "Test Task Failure",
        "task_payload": "Do something",
        "status": "queued",
        "priority": "medium",
        "created_by_type": "ai_agent",
        "created_by_name": "Test",
        "metadata": {"task_type": "alfredo_greeting"}
    }
    task = Task.from_dict(task_data)
    
    # Mock agent success
    agent.complete_task.return_value = "Done!"
    
    # Mock Slack total failure
    mock_slack.post_message.return_value = None
    
    orchestrator_obj._execute_task(task)
    
    # Verify 3 calls to post_message (max retries)
    assert mock_slack.post_message.call_count == 3
    # Verify task completed as "failed"
    mock_store.complete_scheduled_task.assert_called_once()
    args, kwargs = mock_store.complete_scheduled_task.call_args
    assert kwargs["status"] == "failed"
    assert "Slack notification failed" in kwargs["error_details"]

@patch("src.agents.orchestration.scheduler.slack_queue")
@patch("src.agents.orchestration.scheduler.context_store")
def test_execute_task_notifies_on_exception(mock_store, mock_slack, orchestrator):
    orchestrator_obj, agent = orchestrator
    
    # Mock task
    task_data = {
        "id": 3,
        "title": "Exception Task",
        "task_payload": "Break",
        "status": "queued",
        "priority": "medium",
        "created_by_type": "ai_agent",
        "created_by_name": "Test",
        "metadata": {"task_type": "alfredo_greeting"}
    }
    task = Task.from_dict(task_data)
    
    # Mock agent exception
    agent.complete_task.side_effect = Exception("Agent broke!")
    
    orchestrator_obj._execute_task(task)
    
    # Verify Slack was notified about exception
    mock_slack.post_message.assert_called()
    msg = mock_slack.post_message.call_args[1]["message"]
    assert "EXCEPTION: Agent broke!" in msg
    
    # Verify task completed as "failed"
    mock_store.complete_scheduled_task.assert_called_once()
    args, kwargs = mock_store.complete_scheduled_task.call_args
    assert kwargs["status"] == "failed"
    assert "Agent broke!" in kwargs["error_details"]
