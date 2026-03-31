from unittest.mock import patch

from famiglia_core.agents.alfredo import Alfredo


@patch("famiglia_core.agents.alfredo.context_store.create_scheduled_task")
@patch("famiglia_core.agents.alfredo.context_store.log_message")
@patch("famiglia_core.agents.alfredo.context_store.enabled", new=True)
def test_alfredo_creates_scheduled_reminder_from_slack_request(_mock_log, mock_create_task):
    mock_create_task.return_value = {
        "id": 321,
        "eta_pickup_at": "2026-03-09T13:29:00+00:00",
        "eta_completion_at": "2026-03-09T13:30:00+00:00",
    }
    alfredo = Alfredo()

    response = alfredo.complete_task(
        "could u schedule a test reminder for me, which would ping me 1 minute later?",
        sender="Don Jimmy (<@U0AG886GJCV>)",
        conversation_key="slack:CDEV12345:1741520880.123456:U0AG886GJCV",
    )

    assert "Scheduled Task #321" in response
    assert "1 minute" in response
    assert "`2026-03-09T13:29:00+00:00`" in response
    assert "`2026-03-09T13:30:00+00:00`" in response
    kwargs = mock_create_task.call_args.kwargs
    assert kwargs["created_by_type"] == "human_user"
    assert kwargs["created_by_name"] == "Don Jimmy"
    assert kwargs["expected_agent"] == "alfredo"
    assert kwargs["metadata"]["kind"] == "slack_reminder"
    assert kwargs["metadata"]["target_user_id"] == "U0AG886GJCV"
    assert kwargs["metadata"]["slack_channel"] == "CDEV12345"


@patch("famiglia_core.agents.alfredo.context_store.log_message")
@patch("famiglia_core.agents.alfredo.context_store.enabled", new=True)
def test_alfredo_asks_for_explicit_delay_when_missing(_mock_log):
    alfredo = Alfredo()
    response = alfredo.complete_task("Please schedule a reminder for me")
    assert "need a concrete time delay" in response


@patch("famiglia_core.agents.alfredo.context_store.create_scheduled_task")
@patch("famiglia_core.agents.alfredo.context_store.log_message")
@patch("famiglia_core.agents.alfredo.context_store.enabled", new=True)
def test_alfredo_creates_market_research_task_for_rossini(_mock_log, mock_create_task):
    mock_create_task.return_value = {
        "id": 808,
        "eta_pickup_at": "2026-03-09T13:45:00+00:00",
        "eta_completion_at": "2026-03-09T15:15:00+00:00",
    }
    alfredo = Alfredo()

    response = alfredo.complete_task(
        "Please schedule a market research task on AI copilots for SMB finance teams.",
        sender="Don Jimmy (<@U0AG886GJCV>)",
        conversation_key="slack:CDEV12345:1741520880.123456:U0AG886GJCV",
    )

    assert "Scheduled Task #808" in response
    assert "(market_research)" in response
    kwargs = mock_create_task.call_args.kwargs
    assert kwargs["expected_agent"] == "rossini"
    assert kwargs["metadata"]["task_type"] == "market_research"
    assert kwargs["metadata"]["target_user_id"] == "U0AG886GJCV"


@patch("famiglia_core.agents.alfredo.context_store.log_message")
@patch("famiglia_core.agents.alfredo.context_store.enabled", new=True)
def test_alfredo_feature_request_requires_prd_reference(_mock_log):
    alfredo = Alfredo()
    response = alfredo.complete_task(
        "Please schedule a feature request for acme/platform to improve onboarding."
    )
    assert "need a PRD reference" in response


@patch("famiglia_core.agents.alfredo.context_store.create_scheduled_task")
@patch("famiglia_core.agents.alfredo.context_store.get_recent_messages")
@patch("famiglia_core.agents.alfredo.context_store.log_message")
@patch("famiglia_core.agents.alfredo.context_store.enabled", new=True)
def test_alfredo_uses_thread_context_for_followup_scheduling(
    _mock_log,
    mock_get_recent_messages,
    mock_create_task,
):
    mock_get_recent_messages.return_value = [
        {
            "role": "user",
            "content": "could u schedule a task for @Dr. Rossini, to perform a market reserach about love in 10 seconds later",
            "sender": "Don Jimmy",
        },
        {
            "role": "assistant",
            "content": "Please specify one Scheduled Task type.",
            "sender": "Alfredo",
        },
        {
            "role": "user",
            "content": "market research",
            "sender": "Don Jimmy",
        },
    ]
    mock_create_task.return_value = {
        "id": 901,
        "eta_pickup_at": "2026-03-09T13:29:10+00:00",
        "eta_completion_at": "2026-03-09T13:59:10+00:00",
    }
    alfredo = Alfredo()

    response = alfredo.complete_task(
        "simple search is fine. please just create the task for @Dr. Rossini",
        sender="Don Jimmy (<@U0AG886GJCV>)",
        conversation_key="slack:CDEV12345:1741520880.123456:U0AG886GJCV",
    )

    assert "Scheduled Task #901" in response
    kwargs = mock_create_task.call_args.kwargs
    assert kwargs["expected_agent"] == "rossini"
    assert kwargs["metadata"]["task_type"] == "market_research"
    assert "about love in 10 seconds later" in kwargs["metadata"]["requested_text"]
    assert kwargs["eta_pickup_at"] is not None
