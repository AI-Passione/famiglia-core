import pytest
from main import should_handle_message, should_process_message_event, _format_reply_for_sender

def test_should_handle_message_production_non_dev_channel():
    # In production, handle messages in non-dev channels
    assert should_handle_message("production", "C_GENERAL", "C_DEV") is True

def test_should_handle_message_production_dev_channel():
    # In production, ignore messages in dev channel
    assert should_handle_message("production", "C_DEV", "C_DEV") is False

def test_should_handle_message_development_non_dev_channel():
    # In development, ignore messages in non-dev channels
    assert should_handle_message("development", "C_GENERAL", "C_DEV") is False

def test_should_handle_message_development_dev_channel():
    # In development, handle messages in dev channel
    assert should_handle_message("development", "C_DEV", "C_DEV") is True

def test_should_handle_message_no_dev_channel_id():
    # If no dev channel ID is provided, handle everything (default behavior)
    assert should_handle_message("production", "C_ANY", None) is True
    assert should_handle_message("development", "C_ANY", None) is True

def test_should_handle_message_case_insensitive():
    # Environment names should be case-insensitive
    assert should_handle_message("DEVELOPMENT", "C_DEV", "C_DEV") is True
    assert should_handle_message("PRODUCTION", "C_DEV", "C_DEV") is False

def test_format_reply_for_sender_includes_footer(monkeypatch):
    # Mock environment variable
    monkeypatch.setenv("APP_ENV", "development")
    
    result = _format_reply_for_sender("Hello", "U123")
    assert "_Env: Development_" in result
    assert result.startswith("<@U123> Hello")
    
    monkeypatch.setenv("APP_ENV", "production")
    result = _format_reply_for_sender("Hello", "U123")
    assert "_Env: Production_" in result


def test_should_process_message_event_allows_direct_message():
    event = {"channel_type": "im", "text": "hello", "user": "U123"}
    assert should_process_message_event(event, "UBOT", "production", is_dev_channel=False) is True


def test_should_process_message_event_allows_direct_mention():
    event = {"channel_type": "channel", "text": "hi <@UBOT>", "user": "U123"}
    assert should_process_message_event(event, "UBOT", "production", is_dev_channel=False) is True


def test_should_process_message_event_allows_dev_thread_reply_in_development():
    event = {"channel_type": "channel", "text": "follow-up", "thread_ts": "123.456", "user": "U123"}
    assert should_process_message_event(event, "UBOT", "development", is_dev_channel=True) is True


def test_should_process_message_event_blocks_non_thread_message_without_mention():
    event = {"channel_type": "channel", "text": "plain message", "user": "U123"}
    assert should_process_message_event(event, "UBOT", "development", is_dev_channel=True) is False


def test_should_process_message_event_blocks_subtype_and_bot_messages():
    edited_event = {"subtype": "message_changed", "text": "edit", "user": "U123"}
    bot_event = {"bot_id": "B123", "text": "bot", "user": "U123"}
    assert should_process_message_event(edited_event, "UBOT", "development", is_dev_channel=True) is False
    assert should_process_message_event(bot_event, "UBOT", "development", is_dev_channel=True) is False


def test_should_process_message_event_blocks_known_bot_users():
    event = {"channel_type": "channel", "text": "<@UBOT> hi", "user": "U_BOT_USER"}
    assert (
        should_process_message_event(
            event,
            "UBOT",
            "development",
            is_dev_channel=True,
            known_bot_user_ids={"U_BOT_USER"},
        )
        is False
    )
