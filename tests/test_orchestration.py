import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone
from famiglia_core.db.agents.context_store import AgentContextStore
from famiglia_core.agents.orchestration.scheduler import TaskOrchestrator

# --- Unified & Recurring Task Tests ---

def test_unified_recurring_task_lifecycle():
    with patch("famiglia_core.db.agents.context_store.pool.SimpleConnectionPool") as mock_pool_class:
        mock_pool = mock_pool_class.return_value
        mock_conn = MagicMock()
        mock_pool.getconn.return_value = mock_conn
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        
        # RealDictCursor return values
        task_data = {
            "id": 123,
            "title": "Recurring Test",
            "task_payload": "echo 'hello'",
            "status": "queued",
            "schedule_config": {"days": [0], "hour": 10, "minute": 0},
            "last_spawned_at": None,
        }
        mock_cursor.fetchone.return_value = task_data
        
        store = AgentContextStore()
        # Using create_recurring_task as it supports schedule_config
        task = store.create_recurring_task(
            title="Recurring Test",
            task_payload="echo 'hello'",
            schedule_config={"days": [0], "hour": 10, "minute": 0}
        )
        
        assert task["id"] == 123
        assert task["schedule_config"] == {"days": [0], "hour": 10, "minute": 0}

def test_scheduler_task_pickup():
    scheduler = TaskOrchestrator()
    with patch("famiglia_core.agents.orchestration.scheduler.context_store.list_recurring_tasks") as mock_list:
        mock_list.return_value = [{
            "id": 456,
            "title": "Scheduler Task",
            "task_payload": "test",
            "status": "queued",
            "schedule_config": {"days": [0,1,2,3,4,5,6], "hour": 10, "minute": 0},
            "last_spawned_at": None
        }]
        
        # Mocking the actual worker/scheduler logic
        with patch.object(scheduler, "_should_spawn", return_value=True):
            # Mock the Task data class to avoid complex instantiation
            with patch("famiglia_core.agents.orchestration.scheduler.Task") as mock_task_class:
                mock_task = MagicMock()
                mock_task.id = 456
                mock_task.title = "Scheduler Task"
                mock_task_class.from_dict.return_value = mock_task
                
                with patch.object(scheduler, "_spawn_task") as mock_spawn:
                    scheduler._check_and_spawn_recurring()
                    assert mock_spawn.called
