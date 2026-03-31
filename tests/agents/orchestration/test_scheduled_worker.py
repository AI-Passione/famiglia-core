from unittest.mock import MagicMock, patch

from famiglia_core.agents.orchestration.tasks.batched_worker import ScheduledTaskWorker


@patch("famiglia_core.agents.orchestration.tasks.batched_worker.context_store.complete_scheduled_task")
@patch("famiglia_core.agents.orchestration.tasks.batched_worker.slack_queue.enqueue_message")
def test_scheduled_worker_handles_slack_reminder_tasks(
    mock_enqueue_message,
    mock_complete_task,
):
    worker = ScheduledTaskWorker()
    task = {
        "id": 44,
        "metadata": {
            "kind": "slack_reminder",
            "slack_channel": "C123",
            "slack_thread_ts": "1741520880.123456",
            "target_user_id": "U123",
            "reminder_message": "Test reminder",
        },
    }

    handled = worker._try_handle_slack_reminder(task, assigned_agent_id="alfredo")

    assert handled is True
    mock_enqueue_message.assert_called_once_with(
        agent="alfredo",
        channel="C123",
        message="<@U123> Test reminder",
        thread_ts="1741520880.123456",
    )
    mock_complete_task.assert_called_once()


@patch("famiglia_core.agents.orchestration.tasks.batched_worker.context_store.complete_scheduled_task")
def test_scheduled_worker_rejects_incomplete_reminder_metadata(mock_complete_task):
    worker = ScheduledTaskWorker()
    task = {
        "id": 45,
        "metadata": {"kind": "slack_reminder", "slack_channel": "C123"},
    }

    handled = worker._try_handle_slack_reminder(task, assigned_agent_id="alfredo")

    assert handled is True
    mock_complete_task.assert_called_once()


def test_scheduled_worker_enforces_task_type_assignee():
    worker = ScheduledTaskWorker()
    worker.configure(
        {
            "alfredo": MagicMock(),
            "rossini": MagicMock(),
            "riccado": MagicMock(),
            "tommy": MagicMock(),
        }
    )
    task = {
        "id": 91,
        "expected_agent": "alfredo",
        "assigned_agent": None,
        "metadata": {"task_type": "market_research"},
    }

    assignee = worker._resolve_assignee(task)

    assert assignee == "rossini"


@patch("famiglia_core.agents.orchestration.tasks.batched_worker.context_store.complete_scheduled_task")
@patch("famiglia_core.agents.orchestration.tasks.batched_worker.slack_queue.enqueue_message")
def test_scheduled_worker_marks_prd_tasks_as_drafted(
    mock_enqueue_message,
    mock_complete_task,
):
    worker = ScheduledTaskWorker()
    rossini = MagicMock()
    rossini.complete_task.return_value = "PRD draft created: https://notion.so/prd-draft"
    task = {
        "id": 52,
        "title": "PRD Drafting",
        "task_payload": "Draft PRD",
        "created_by_name": "Don Jimmy",
        "metadata": {"task_type": "prd_drafting"},
    }

    handled = worker._try_handle_prd_drafting(
        task,
        assigned_agent_id="rossini",
        assigned_agent=rossini,
    )

    assert handled is True
    mock_enqueue_message.assert_called_once()
    kwargs = mock_complete_task.call_args.kwargs
    assert kwargs["status"] == "drafted"
    assert kwargs["task_id"] == 52


@patch("famiglia_core.agents.orchestration.tasks.batched_worker.context_store.complete_scheduled_task")
@patch("famiglia_core.agents.orchestration.tasks.batched_worker.context_store.create_scheduled_task")
@patch("famiglia_core.agents.orchestration.tasks.batched_worker.slack_queue.enqueue_message")
def test_feature_request_creates_followup_for_riccado(
    mock_enqueue_message,
    mock_create_task,
    mock_complete_task,
):
    worker = ScheduledTaskWorker()
    rossini = MagicMock()
    rossini.complete_task.return_value = "GitHub setup completed successfully."
    mock_create_task.return_value = {"id": 211}
    task = {
        "id": 99,
        "title": "Feature Request",
        "task_payload": "Create milestone and issues",
        "created_by_name": "Don Jimmy",
        "metadata": {
            "task_type": "feature_request",
            "repo_name": "acme/platform",
            "prd_reference": "https://notion.so/prd-123",
        },
    }

    handled = worker._try_handle_feature_request(
        task,
        assigned_agent_id="rossini",
        assigned_agent=rossini,
    )

    assert handled is True
    create_kwargs = mock_create_task.call_args.kwargs
    assert create_kwargs["expected_agent"] == "riccado"
    assert create_kwargs["metadata"]["task_type"] == "coding_implementation"
    complete_kwargs = mock_complete_task.call_args.kwargs
    assert complete_kwargs["status"] == "completed"
    assert mock_enqueue_message.call_count == 1
