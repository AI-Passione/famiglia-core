import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone
from famiglia_core.db.context_store import AgentContextStore
from famiglia_core.agents.orchestration.scheduler import TaskOrchestrator

def test_create_and_list_unified_recurring_task():
    """Verify that a scheduled task with schedule_config is treated as recurring."""
    with patch("famiglia_core.db.context_store.psycopg2.connect") as mock_connect:
        conn = MagicMock()
        mock_connect.return_value = conn
        cursor = conn.cursor.return_value
        
        # 1. Create task mock return
        cursor.fetchone.return_value = {
            "id": 123,
            "title": "Recurring Test",
            "task_payload": "echo 'hello'",
            "status": "queued",
            "priority": "medium",
            "created_by_type": "ai_agent",
            "created_by_name": "TestRunner",
            "expected_agent": None,
            "assigned_agent": None,
            "eta_pickup_at": None,
            "eta_completion_at": None,
            "picked_up_at": None,
            "completed_at": None,
            "result_summary": None,
            "error_details": None,
            "metadata": None,
            "schedule_config": {"days": [0], "hour": 10, "minute": 0},
            "last_spawned_at": None,
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }
        
        store = AgentContextStore()
        task = store.create_scheduled_task(
            title="Recurring Test",
            task_payload="echo 'hello'",
            created_by_type="ai_agent",
            created_by_name="TestRunner",
            schedule_config={"days": [0], "hour": 10, "minute": 0}
        )
        
        assert task is not None
        assert task["id"] == 123
        assert task["schedule_config"] == {"days": [0], "hour": 10, "minute": 0}
        
        sql, params = cursor.execute.call_args[0]
        assert "schedule_config" in sql
        assert '{"days": [0], "hour": 10, "minute": 0}' in params

        # 2. List recurring tasks mock
        cursor.fetchall.return_value = [task]
        recurring_tasks = store.list_recurring_tasks()
        
        assert len(recurring_tasks) == 1
        assert recurring_tasks[0]["id"] == 123
        assert recurring_tasks[0]["schedule_config"] is not None

def test_scheduler_pickup_unified_task():
    """Verify the TaskOrchestrator picks up the unified task."""
    scheduler = TaskOrchestrator()
    
    with patch("famiglia_core.db.context_store.psycopg2.connect") as mock_connect:
        conn = MagicMock()
        mock_connect.return_value = conn
        cursor = conn.cursor.return_value
        
        # Mock recurring task list from DB
        cursor.fetchall.return_value = [{
            "id": 456,
            "title": "Scheduler Task",
            "task_payload": "test",
            "status": "queued",
            "priority": "medium",
            "created_by_type": "ai_agent",
            "created_by_name": "TestRunner",
            "schedule_config": {"days": [0,1,2,3,4,5,6], "hour": 10, "minute": 0},
            "last_spawned_at": None
        }]
        
        # Mock should_spawn to be True
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(scheduler, "_should_spawn", lambda t, now: True)
            
            # Use a mock for spawn_task or its components
            with patch.object(scheduler, "_spawn_task") as mock_spawn:
                scheduler._check_and_spawn_recurring()
                assert mock_spawn.called
                args, _ = mock_spawn.call_args
                assert args[0].id == 456
