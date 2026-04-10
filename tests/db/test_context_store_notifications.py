import pytest
from unittest.mock import MagicMock, patch
from famiglia_core.db.agents.context_store import AgentContextStore
from datetime import datetime, timezone

@pytest.fixture
def store():
    # Mocking the connection pool to avoid actual PG connections
    with patch("famiglia_core.db.agents.context_store.pool.SimpleConnectionPool"):
        return AgentContextStore()

def test_log_app_notification(store):
    mock_cursor = MagicMock()
    store.db_session = MagicMock()
    store.db_session.return_value.__enter__.return_value = mock_cursor
    
    # Setup mock return for INSERT RETURNING id
    mock_cursor.fetchone.return_value = {"id": 123}
    
    notif_id = store.log_app_notification(
        source="workflow",
        agent_name="alfredo",
        title="Mission Dispatched",
        message="Directive received.",
        type="info",
        task_id=1,
        metadata={"prio": "high"}
    )
    
    assert notif_id == 123
    assert mock_cursor.execute.called
    query = mock_cursor.execute.call_args[0][0]
    args = mock_cursor.execute.call_args[0][1]
    
    assert "INSERT INTO app_notifications" in query
    assert args[0] == "workflow"
    assert args[1] == "alfredo"
    assert args[2] == "Mission Dispatched"
    assert args[4] == "info"

def test_get_app_notifications(store):
    mock_cursor = MagicMock()
    store.db_session = MagicMock()
    store.db_session.return_value.__enter__.return_value = mock_cursor
    
    mock_cursor.fetchall.return_value = [
        {
            "id": 1,
            "source": "workflow",
            "title": "Alert 1",
            "message": "Message 1",
            "type": "success",
            "created_at": datetime.now(timezone.utc)
        },
        {
            "id": 2,
            "source": "system",
            "title": "Alert 2",
            "message": "Message 2",
            "type": "error",
            "created_at": datetime.now(timezone.utc)
        }
    ]
    
    notifs = store.get_app_notifications(limit=5)
    assert len(notifs) == 2
    assert notifs[0]["title"] == "Alert 1"
    assert notifs[1]["source"] == "system"
    assert "LIMIT %s" in mock_cursor.execute.call_args[0][0]
    assert mock_cursor.execute.call_args[0][1] == (5,)

def test_mark_app_notification_as_read(store):
    mock_cursor = MagicMock()
    store.db_session = MagicMock()
    store.db_session.return_value.__enter__.return_value = mock_cursor
    
    mock_cursor.rowcount = 1
    
    success = store.mark_app_notification_as_read(123)
    assert success is True
    assert "UPDATE app_notifications SET is_read = TRUE" in mock_cursor.execute.call_args[0][0]
    assert mock_cursor.execute.call_args[0][1] == (123,)
