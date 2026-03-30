from unittest.mock import patch

from src.agents.alfredo import Alfredo


@patch("src.agents.alfredo.context_store.get_scheduled_tasks_overview")
@patch("src.agents.alfredo.BaseAgent.complete_task")
def test_alfredo_status_request_uses_batched_overview_directly(
    mock_super_complete,
    mock_overview,
):
    mock_super_complete.return_value = "fallback-llm-response"
    mock_overview.return_value = {
        "generated_at": "2026-03-09T12:00:00+00:00",
        "counts": {
            "queued": 4,
            "in_progress": 2,
            "drafted": 1,
            "completed": 10,
            "failed": 1,
            "cancelled": 0,
        },
        "queue_line": [
            {
                "id": 77,
                "title": "Run postmortem analysis",
                "priority": "critical",
                "created_by_type": "ai_agent",
                "created_by_name": "Alfredo",
                "expected_agent": "rossini",
                "assigned_agent": "rossini",
                "eta_pickup_at": "2026-03-09T12:05:00+00:00",
                "eta_completion_at": "2026-03-09T13:35:00+00:00",
            }
        ],
        "recently_finished": [],
    }

    alfredo = Alfredo()
    response = alfredo.complete_task("Alfredo, what is the latest status of all scheduled tasks?")

    assert "queued=4" in response
    assert "in_progress=2" in response
    assert "drafted=1" in response
    assert "```" in response
    assert "| #77 |" in response
    assert "| ai_agent:Alfredo |" in response
    mock_super_complete.assert_not_called()


@patch("src.agents.alfredo.context_store.get_scheduled_tasks_overview")
@patch("src.agents.alfredo.BaseAgent.complete_task")
def test_alfredo_ongoing_phrase_triggers_db_status_lookup(
    mock_super_complete,
    mock_overview,
):
    mock_super_complete.return_value = "fallback-llm-response"
    mock_overview.return_value = {
        "generated_at": "2026-03-09T12:00:00+00:00",
        "counts": {
            "queued": 2,
            "in_progress": 1,
            "completed": 4,
            "failed": 0,
            "cancelled": 0,
        },
        "queue_line": [],
        "recently_finished": [],
    }

    alfredo = Alfredo()
    response = alfredo.complete_task("Alfredo, what ongoing scheduled tasks are running now?")

    assert "queued=2" in response
    assert "in_progress=1" in response
    mock_super_complete.assert_not_called()
    mock_overview.assert_called_once()


@patch("src.agents.alfredo.context_store.enabled", new=False)
@patch("src.agents.alfredo.BaseAgent.complete_task")
def test_alfredo_reports_when_context_store_disabled(mock_super_complete):
    mock_super_complete.return_value = "fallback-llm-response"
    alfredo = Alfredo()
    response = alfredo.complete_task("Show me the scheduled queue status")

    assert "cannot read scheduled task status" in response
    mock_super_complete.assert_not_called()
