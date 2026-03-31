from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from famiglia_core.db.context_store import AgentContextStore


def _sample_task_row(task_id: int = 7):
    now = datetime(2026, 3, 9, 12, 0, tzinfo=timezone.utc)
    return {
        "id": task_id,
        "title": "Audit deployment pipeline",
        "task_payload": "Review rollout safety checks and report gaps.",
        "status": "queued",
        "priority": "high",
        "created_by_type": "human_user",
        "created_by_name": "Don Jimmy",
        "expected_agent": "riccado",
        "assigned_agent": None,
        "eta_pickup_at": now,
        "eta_completion_at": now,
        "picked_up_at": None,
        "completed_at": None,
        "result_summary": None,
        "error_details": None,
        "metadata": {"source": "test"},
        "created_at": now,
        "updated_at": now,
    }


def test_create_scheduled_task_persists_expected_fields():
    with patch("famiglia_core.db.context_store.psycopg2.connect") as mock_connect:
        conn = MagicMock()
        cursor = conn.cursor.return_value
        cursor.fetchone.return_value = _sample_task_row(task_id=17)
        mock_connect.return_value = conn

        store = AgentContextStore()
        result = store.create_scheduled_task(
            title="Audit deployment pipeline",
            task_payload="Review rollout safety checks and report gaps.",
            created_by_type="human_user",
            created_by_name="Don Jimmy",
            priority="high",
            expected_agent="riccado",
            eta_pickup_at=datetime(2026, 3, 9, 12, 0, tzinfo=timezone.utc),
            eta_completion_at=datetime(2026, 3, 9, 15, 0, tzinfo=timezone.utc),
            metadata={"source": "test"},
        )

        assert result is not None
        assert result["id"] == 17
        assert result["created_by_type"] == "human_user"
        assert result["priority"] == "high"
        assert result["expected_agent"] == "riccado"

        sql, params = cursor.execute.call_args[0]
        assert "INSERT INTO task_instances" in sql
        assert params[3] == "high"
        assert params[4] == "human_user"
        assert params[5] == "Don Jimmy"


def test_claim_next_scheduled_task_marks_in_progress():
    with patch("famiglia_core.db.context_store.psycopg2.connect") as mock_connect:
        conn = MagicMock()
        cursor = conn.cursor.return_value
        task_row = _sample_task_row(task_id=22)
        task_row["status"] = "in_progress"
        task_row["picked_up_at"] = datetime(2026, 3, 9, 12, 5, tzinfo=timezone.utc)
        cursor.fetchone.return_value = task_row
        mock_connect.return_value = conn

        store = AgentContextStore()
        claimed = store.claim_next_scheduled_task(eligible_agents=["riccado"])

        assert claimed is not None
        assert claimed["id"] == 22
        assert claimed["status"] == "in_progress"
        assert claimed["picked_up_at"].startswith("2026-03-09T12:05:00")

        sql, _ = cursor.execute.call_args[0]
        assert "UPDATE task_instances" in sql
        assert "status = 'in_progress'" in sql


def test_complete_scheduled_task_updates_status():
    with patch("famiglia_core.db.context_store.psycopg2.connect") as mock_connect:
        conn = MagicMock()
        cursor = conn.cursor.return_value
        cursor.rowcount = 1
        mock_connect.return_value = conn

        store = AgentContextStore()
        success = store.complete_scheduled_task(
            task_id=33,
            assigned_agent="riccado",
            status="completed",
            result_summary="All checks passed.",
        )

        assert success is True
        sql, params = cursor.execute.call_args[0]
        assert "UPDATE task_instances" in sql
        assert "status = %s" in sql
        assert params[0] == "completed"
        assert params[1] == "riccado"
        assert params[2] == "All checks passed."


def test_get_scheduled_tasks_overview_includes_queue_and_history():
    with patch("famiglia_core.db.context_store.psycopg2.connect") as mock_connect:
        conn = MagicMock()
        count_cursor = MagicMock()
        queue_cursor = MagicMock()
        recent_cursor = MagicMock()
        conn.cursor.side_effect = [count_cursor, queue_cursor, recent_cursor]

        count_cursor.fetchall.return_value = [
            {"status": "queued", "total": 5},
            {"status": "completed", "total": 10},
        ]
        queue_cursor.fetchall.return_value = [_sample_task_row(i) for i in range(1, 3)]
        recent_cursor.fetchall.return_value = [_sample_task_row(i) for i in range(10, 12)]

        mock_connect.return_value = conn

        store = AgentContextStore()
        overview = store.get_scheduled_tasks_overview(queue_limit=5)

        assert overview["counts"]["queued"] == 5
        assert overview["counts"]["completed"] == 10
        assert len(overview["queue_line"]) == 2
        assert len(overview["recently_finished"]) == 2

        # Verify first query (counts)
        count_args = count_cursor.execute.call_args[0]
        count_sql = count_args[0]
        assert "FROM task_instances" in count_sql
        
        # Verify second query (queue)
        queue_args = queue_cursor.execute.call_args[0]
        queue_sql = queue_args[0]
        assert "status IN ('queued', 'in_progress', 'drafted')" in queue_sql
        
        # Verify third query (recent)
        recent_args = recent_cursor.execute.call_args[0]
        recent_sql = recent_args[0]
        assert "status IN ('completed', 'failed', 'cancelled')" in recent_sql
