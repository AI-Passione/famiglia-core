import json
import os
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Generator

import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()


class AgentContextStore:
    SCHEDULED_TASK_PRIORITIES = ("critical", "high", "medium", "low")
    SCHEDULED_TASK_STATUSES = (
        "queued",
        "in_progress",
        "drafted",
        "completed",
        "failed",
        "cancelled",
    )
    PRIORITY_RANK = {
        "critical": 0,
        "high": 1,
        "medium": 2,
        "low": 3,
    }

    def __init__(self):
        self.enabled = os.getenv("AGENT_CONTEXT_ENABLED", "true").strip().lower() not in {
            "0",
            "false",
            "no",
        }
        self.db_config = {
            "host": os.getenv("DB_HOST", "localhost"),
            "port": os.getenv("DB_PORT", "5432"),
            "user": os.getenv("DB_USER", "passione_admin"),
            "password": os.getenv("DB_PASSWORD", "passione_password"),
            "dbname": os.getenv("DB_NAME", "passione_db"),
        }
        self._pool: Optional[pool.AbstractConnectionPool] = None

    def _get_pool(self) -> pool.AbstractConnectionPool:
        if self._pool is None:
            try:
                self._pool = pool.SimpleConnectionPool(
                    minconn=1,
                    maxconn=20,
                    **self.db_config
                )
            except Exception as e:
                print(f"[ContextStore] Error creating connection pool: {e}")
                raise
        return self._pool

    @contextmanager
    def db_session(self, commit: bool = True) -> Generator[Optional[RealDictCursor], None, None]:
        """Provides a database cursor from the pool with automatic commit/rollback and cleanup."""
        if not self.enabled:
            yield None
            return

        conn = self._get_pool().getconn()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                yield cursor
                if commit:
                    conn.commit()
        except Exception as e:
            conn.rollback()
            print(f"[ContextStore] Database session error: {e}")
            raise
        finally:
            self._get_pool().putconn(conn)

    def _safe_json(self, value: Optional[Dict[str, Any]]) -> Optional[str]:
        if value is None:
            return None
        return json.dumps(value)

    def _normalize_priority(self, priority: Optional[str]) -> str:
        value = (priority or "medium").strip().lower()
        if value in self.SCHEDULED_TASK_PRIORITIES:
            return value
        return "medium"

    def _normalize_statuses(self, statuses: Optional[List[str]]) -> List[str]:
        if not statuses:
            return []
        normalized = []
        for status in statuses:
            value = (status or "").strip().lower()
            if value in self.SCHEDULED_TASK_STATUSES:
                normalized.append(value)
        return list(dict.fromkeys(normalized))

    def _normalize_creator_type(self, created_by_type: Optional[str]) -> str:
        value = (created_by_type or "").strip().lower()
        if value in {"human_user", "human", "user"}:
            return "human_user"
        if value in {"ai_agent", "ai", "agent", "assistant"}:
            return "ai_agent"
        return "human_user"

    def _parse_iso_datetime(self, value: Optional[Any]) -> Optional[datetime]:
        if value is None:
            return None
        if isinstance(value, datetime):
            if value.tzinfo is None:
                return value.replace(tzinfo=timezone.utc)
            return value
        if not isinstance(value, str):
            return None
        candidate = value.strip()
        if not candidate:
            return None
        if candidate.endswith("Z"):
            candidate = f"{candidate[:-1]}+00:00"
        try:
            parsed = datetime.fromisoformat(candidate)
        except ValueError:
            return None
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed

    def _serialize_task_row(self, row: Dict[str, Any]) -> Dict[str, Any]:
        serialized = dict(row)
        for key in (
            "created_at",
            "updated_at",
            "eta_pickup_at",
            "eta_completion_at",
            "picked_up_at",
            "completed_at",
            "last_spawned_at",
        ):
            value = serialized.get(key)
            if isinstance(value, datetime):
                serialized[key] = value.isoformat()
        return serialized

    def _get_or_create_conversation_id(
        self,
        conversation_key: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[int]:
        try:
            with self.db_session() as cursor:
                if cursor is None: return None
                cursor.execute(
                    """
                    INSERT INTO agent_conversations (conversation_key, metadata, updated_at)
                    VALUES (%s, %s, NOW())
                    ON CONFLICT (conversation_key)
                    DO UPDATE SET
                      metadata = COALESCE(EXCLUDED.metadata, agent_conversations.metadata),
                      updated_at = NOW()
                    RETURNING id
                    """,
                    (conversation_key, self._safe_json(metadata)),
                )
                row = cursor.fetchone()
                return row["id"] if row else None
        except Exception as e:
            print(f"[ContextStore] Failed to ensure conversation: {e}")
            return None

    def log_message(
        self,
        agent_name: str,
        conversation_key: str,
        role: str,
        content: str,
        sender: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        parent_id: Optional[int] = None,
    ) -> int:
        conversation_id = self._get_or_create_conversation_id(conversation_key)
        if conversation_id is None:
            return -1

        try:
            with self.db_session() as cursor:
                if cursor is None: return -1
                cursor.execute(
                    """
                    INSERT INTO agent_messages (
                      conversation_id, agent_name, sender, role, content, metadata, parent_id
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (conversation_id, agent_name, sender, role, content, self._safe_json(metadata), parent_id),
                )
                row = cursor.fetchone()
                message_id = row["id"] if row else -1
                cursor.execute(
                    "UPDATE agent_conversations SET updated_at = NOW() WHERE id = %s",
                    (conversation_id,),
                )
                return message_id
        except Exception as e:
            print(f"[ContextStore] Failed to log message: {e}")
            return -1

    def get_global_recent_agent_messages(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Fetch the most recent agent messages across all conversations for global notifications."""
        try:
            with self.db_session(commit=False) as cursor:
                if cursor is None: return []
                cursor.execute(
                    """
                    SELECT m.id, m.parent_id, m.role, m.content, m.sender, m.created_at, c.conversation_key, m.metadata
                    FROM agent_messages m
                    INNER JOIN agent_conversations c ON c.id = m.conversation_id
                    WHERE m.role = 'agent'
                    ORDER BY m.created_at DESC
                    LIMIT %s
                    """,
                    (max(1, limit),),
                )
                return list(cursor.fetchall())
        except Exception as e:
            print(f"[ContextStore] Failed to fetch global recent agent messages: {e}")
            return []

    def log_app_notification(
        self,
        source: str,
        title: str,
        message: str,
        type: str = "info",
        agent_name: Optional[str] = None,
        task_id: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> int:
        """Unified logging for all application-level alerts (Bell notification center)."""
        try:
            with self.db_session() as cursor:
                if cursor is None: return -1
                cursor.execute(
                    """
                    INSERT INTO app_notifications (
                        source, agent_name, title, message, type, task_id, metadata
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (source, agent_name, title, message, type, task_id, self._safe_json(metadata)),
                )
                row = cursor.fetchone()
                return row["id"] if row else -1
        except Exception as e:
            print(f"[ContextStore] Failed to log app notification: {e}")
            return -1

    def get_app_notifications(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Fetch recent unified application notifications."""
        try:
            with self.db_session(commit=False) as cursor:
                if cursor is None: return []
                cursor.execute(
                    "SELECT * FROM app_notifications ORDER BY created_at DESC LIMIT %s",
                    (max(1, limit),),
                )
                return list(cursor.fetchall())
        except Exception as e:
            print(f"[ContextStore] Failed to fetch app notifications: {e}")
            return []

    def mark_app_notification_as_read(self, notification_id: int) -> bool:
        """Mark a specific notification as read."""
        try:
            with self.db_session() as cursor:
                if cursor is None: return False
                cursor.execute(
                    "UPDATE app_notifications SET is_read = TRUE, updated_at = NOW() WHERE id = %s",
                    (notification_id,),
                )
                return cursor.rowcount > 0
        except Exception as e:
            print(f"[ContextStore] Failed to mark notification as read: {e}")
            return False

    def get_recent_messages(
        self,
        conversation_key: str,
        limit: int = 8,
    ) -> List[Dict[str, Any]]:
        try:
            with self.db_session(commit=False) as cursor:
                if cursor is None: return []
                cursor.execute(
                    """
                    SELECT m.id, m.parent_id, m.role, m.content, m.sender, m.created_at, m.metadata
                    FROM agent_messages m
                    INNER JOIN agent_conversations c ON c.id = m.conversation_id
                    WHERE c.conversation_key = %s AND m.parent_id IS NULL
                    ORDER BY m.created_at DESC
                    LIMIT %s
                    """,
                    (conversation_key, max(1, limit)),
                )
                rows = list(cursor.fetchall())
                rows.reverse()
                return rows
        except Exception as e:
            print(f"[ContextStore] Failed to fetch recent messages: {e}")
            return []

    def get_thread_messages(self, parent_id: int) -> List[Dict[str, Any]]:
        try:
            with self.db_session(commit=False) as cursor:
                if cursor is None: return []
                cursor.execute(
                    """
                    SELECT m.id, m.parent_id, m.role, m.content, m.sender, m.created_at, m.metadata
                    FROM agent_messages m
                    WHERE m.parent_id = %s
                    ORDER BY m.created_at ASC
                    """,
                    (parent_id,),
                )
                return list(cursor.fetchall())
        except Exception as e:
            print(f"[ContextStore] Failed to fetch thread messages: {e}")
            return []

    def list_conversations(self, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        try:
            with self.db_session(commit=False) as cursor:
                if cursor is None: return []
                cursor.execute(
                    """
                    SELECT 
                        c.id, 
                        c.conversation_key, 
                        c.metadata, 
                        c.updated_at,
                        (SELECT m.content FROM agent_messages m 
                         WHERE m.conversation_id = c.id 
                         ORDER BY m.created_at DESC LIMIT 1) as latest_message,
                        (SELECT m.agent_name FROM agent_messages m 
                         WHERE m.conversation_id = c.id 
                         ORDER BY m.created_at DESC LIMIT 1) as latest_agent
                    FROM agent_conversations c
                    ORDER BY c.updated_at DESC
                    LIMIT %s OFFSET %s
                    """,
                    (max(1, limit), max(0, offset)),
                )
                return list(cursor.fetchall())
        except Exception as e:
            print(f"[ContextStore] Failed to list conversations: {e}")
            return []

    def get_total_conversation_count(self) -> int:
        try:
            with self.db_session(commit=False) as cursor:
                if cursor is None: return 0
                cursor.execute("SELECT COUNT(*) FROM agent_conversations")
                row = cursor.fetchone()
                return int(row["count"]) if row else 0
        except Exception as e:
            print(f"[ContextStore] Failed to count conversations: {e}")
            return 0

    def search_messages(
        self,
        agent_name: str,
        query: str,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        try:
            with self.db_session(commit=False) as cursor:
                if cursor is None: return []
                cursor.execute(
                    """
                    SELECT m.role, m.content, m.sender, m.created_at
                    FROM agent_messages m
                    WHERE m.agent_name = %s AND m.content ILIKE %s
                    ORDER BY m.created_at DESC
                    LIMIT %s
                    """,
                    (agent_name, f"%{query}%", max(1, limit)),
                )
                return list(cursor.fetchall())
        except Exception as e:
            print(f"[ContextStore] Failed to search messages: {e}")
            return []

    def upsert_memory(
        self,
        agent_name: str,
        memory_key: str,
        memory_value: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        try:
            with self.db_session() as cursor:
                if cursor is None: return False
                cursor.execute(
                    """
                    INSERT INTO agent_memories (agent_name, memory_key, memory_value, metadata, updated_at)
                    VALUES (%s, %s, %s, %s, NOW())
                    ON CONFLICT (agent_name, memory_key)
                    DO UPDATE SET
                      memory_value = EXCLUDED.memory_value,
                      metadata = COALESCE(EXCLUDED.metadata, agent_memories.metadata),
                      updated_at = NOW()
                    """,
                    (agent_name, memory_key, memory_value, self._safe_json(metadata)),
                )
                return True
        except Exception as e:
            print(f"[ContextStore] Failed to upsert memory: {e}")
            return False

    def get_memories(self, agent_name: str, limit: int = 10) -> List[Dict[str, Any]]:
        try:
            with self.db_session(commit=False) as cursor:
                if cursor is None: return []
                cursor.execute(
                    """
                    SELECT memory_key, memory_value, metadata, updated_at
                    FROM agent_memories
                    WHERE agent_name = %s
                    ORDER BY updated_at DESC
                    LIMIT %s
                    """,
                    (agent_name, max(1, limit)),
                )
                return list(cursor.fetchall())
        except Exception as e:
            print(f"[ContextStore] Failed to fetch memories: {e}")
            return []

    def get_web_search_cache(self, query: str) -> Optional[List[Dict[str, Any]]]:
        try:
            with self.db_session(commit=False) as cursor:
                if cursor is None: return None
                cursor.execute(
                    """
                    SELECT results FROM web_search_cache 
                    WHERE query_text = %s 
                    AND (expires_at IS NULL OR expires_at > NOW())
                    """,
                    (query.strip().lower(),),
                )
                row = cursor.fetchone()
                return row["results"] if row else None
        except Exception as e:
            print(f"[ContextStore] Failed to fetch search cache: {e}")
            return None

    def set_web_search_cache(
        self, 
        query: str, 
        results: List[Dict[str, Any]], 
        agent_name: Optional[str] = None,
        user_prompt: Optional[str] = None,
        ttl_days: int = 7
    ) -> bool:
        try:
            with self.db_session() as cursor:
                if cursor is None: return False
                cursor.execute(
                    """
                    INSERT INTO web_search_cache (query_text, results, agent_name, user_prompt, expires_at)
                    VALUES (%s, %s, %s, %s, NOW() + interval '%s day')
                    ON CONFLICT (query_text) DO UPDATE SET
                      results = EXCLUDED.results,
                      agent_name = COALESCE(EXCLUDED.agent_name, web_search_cache.agent_name),
                      user_prompt = COALESCE(EXCLUDED.user_prompt, web_search_cache.user_prompt),
                      expires_at = EXCLUDED.expires_at,
                      created_at = NOW()
                    """,
                    (query.strip().lower(), json.dumps(results), agent_name, user_prompt, ttl_days),
                )
                return True
        except Exception as e:
            print(f"[ContextStore] Failed to set search cache: {e}")
            return False

    def estimate_scheduled_task_eta(
        self,
        priority: str = "medium",
        expected_agent: Optional[str] = None,
    ) -> Dict[str, Any]:
        now = datetime.now(timezone.utc)
        slot_minutes = max(1, int(os.getenv("SCHEDULED_TASK_SLOT_MINUTES", "15")))
        base_pickup_minutes = max(1, int(os.getenv("SCHEDULED_TASK_BASE_PICKUP_MINUTES", "5")))
        duration_minutes = max(1, int(os.getenv("SCHEDULED_TASK_DEFAULT_DURATION_MINUTES", "90")))
        normalized_priority = self._normalize_priority(priority)
        normalized_expected_agent = (expected_agent or "").strip().lower() or None

        try:
            with self.db_session(commit=False) as cursor:
                if cursor is None:
                    pickup_at = now + timedelta(minutes=base_pickup_minutes)
                    return {"eta_pickup_at": pickup_at.isoformat(), "eta_completion_at": (pickup_at + timedelta(minutes=duration_minutes)).isoformat(), "queue_ahead": 0}
                
                cursor.execute(
                    """
                    SELECT priority, COUNT(*) AS total
                    FROM task_instances
                    WHERE status IN ('queued', 'in_progress')
                      AND (%s IS NULL OR expected_agent = %s OR expected_agent IS NULL)
                    GROUP BY priority
                    """,
                    (normalized_expected_agent, normalized_expected_agent),
                )
                rows = cursor.fetchall()
                counts = {row["priority"]: int(row["total"]) for row in rows}
                queue_ahead = sum(count for p, count in counts.items() if self.PRIORITY_RANK.get(p, 3) <= self.PRIORITY_RANK[normalized_priority])
                
                pickup_at = now + timedelta(minutes=base_pickup_minutes + (queue_ahead * slot_minutes))
                completion_at = pickup_at + timedelta(minutes=duration_minutes)
                return {
                    "eta_pickup_at": pickup_at.isoformat(),
                    "eta_completion_at": completion_at.isoformat(),
                    "queue_ahead": queue_ahead,
                }
        except Exception as e:
            print(f"[ContextStore] Failed to estimate task ETA: {e}")
            pickup_at = now + timedelta(minutes=base_pickup_minutes)
            return {"eta_pickup_at": pickup_at.isoformat(), "eta_completion_at": (pickup_at + timedelta(minutes=duration_minutes)).isoformat(), "queue_ahead": 0}

    def create_scheduled_task(
        self,
        title: str,
        task_payload: str,
        priority: str = "medium",
        created_by_type: str = "ai_agent",
        created_by_name: str = "unknown",
        expected_agent: Optional[str] = None,
        eta_pickup_at: Optional[datetime] = None,
        eta_completion_at: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None,
        recurring_task_id: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:
        safe_priority = self._normalize_priority(priority)
        safe_created_by = self._normalize_creator_type(created_by_type)
        now = datetime.now(timezone.utc)
        eta_pickup_at = eta_pickup_at or (now + timedelta(minutes=1))
        eta_completion_at = eta_completion_at or (now + timedelta(hours=1))

        try:
            with self.db_session() as cursor:
                if cursor is None: return None
                cursor.execute(
                    """
                    INSERT INTO task_instances (
                        title, task_payload, status, priority,
                        created_by_type, created_by_name,
                        expected_agent, eta_pickup_at, eta_completion_at,
                        metadata, recurring_task_id, created_at, updated_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
                    RETURNING *
                    """,
                    (title, task_payload, "queued", safe_priority, safe_created_by, created_by_name, expected_agent, eta_pickup_at, eta_completion_at, self._safe_json(metadata), recurring_task_id),
                )
                row = cursor.fetchone()
                return self._serialize_task_row(row) if row else None
        except Exception as e:
            print(f"[ContextStore] Failed to create task instance: {e}")
            return None

    def list_recurring_tasks(self) -> List[Dict[str, Any]]:
        try:
            with self.db_session(commit=False) as cursor:
                if cursor is None: return []
                cursor.execute("SELECT * FROM recurring_tasks ORDER BY created_at DESC")
                return [self._serialize_task_row(row) for row in cursor.fetchall()]
        except Exception as e:
            print(f"[ContextStore] Failed to list recurring tasks: {e}")
            return []

    def update_recurring_task_last_spawned(self, task_id: int, spawned_at: datetime) -> bool:
        try:
            with self.db_session() as cursor:
                if cursor is None: return False
                cursor.execute(
                    "UPDATE recurring_tasks SET last_spawned_at = %s, updated_at = NOW() WHERE id = %s",
                    (spawned_at, task_id)
                )
                return cursor.rowcount > 0
        except Exception as e:
            print(f"[ContextStore] Failed to update recurring task last spawned: {e}")
            return False

    def create_recurring_task(
        self,
        title: str,
        task_payload: str,
        schedule_config: Dict[str, Any],
        priority: str = "medium",
        expected_agent: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        safe_priority = self._normalize_priority(priority)
        try:
            with self.db_session() as cursor:
                if cursor is None: return None
                cursor.execute(
                    """
                    INSERT INTO recurring_tasks (
                        title, task_payload, schedule_config, priority, expected_agent, metadata, created_at, updated_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, NOW(), NOW())
                    RETURNING *
                    """,
                    (title, task_payload, json.dumps(schedule_config), safe_priority, expected_agent, self._safe_json(metadata)),
                )
                row = cursor.fetchone()
                return self._serialize_task_row(row) if row else None
        except Exception as e:
            print(f"[ContextStore] Failed to create recurring task: {e}")
            return None

    def list_scheduled_tasks(
        self,
        statuses: Optional[List[str]] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        normalized_statuses = self._normalize_statuses(statuses)
        query = "SELECT * FROM task_instances"
        params: List[Any] = []
        if normalized_statuses:
            query += " WHERE status = ANY(%s)"
            params.append(normalized_statuses)
        query += """
            ORDER BY 
                CASE priority
                    WHEN 'critical' THEN 0
                    WHEN 'high' THEN 1
                    WHEN 'medium' THEN 2
                    ELSE 3
                END,
                created_at DESC
            LIMIT %s OFFSET %s
        """
        params.append(max(1, min(limit, 500)))
        params.append(max(0, offset))

        try:
            with self.db_session(commit=False) as cursor:
                if cursor is None: return []
                cursor.execute(query, params)
                return [self._serialize_task_row(row) for row in cursor.fetchall()]
        except Exception as e:
            print(f"[ContextStore] Failed to list task instances: {e}")
            return []

    def get_total_task_count(self, statuses: Optional[List[str]] = None) -> int:
        normalized_statuses = self._normalize_statuses(statuses)
        query = "SELECT COUNT(*) FROM task_instances"
        params = []
        if normalized_statuses:
            query += " WHERE status = ANY(%s)"
            params.append(normalized_statuses)
            
        try:
            with self.db_session(commit=False) as cursor:
                if cursor is None: return 0
                cursor.execute(query, params)
                row = cursor.fetchone()
                return int(row["count"]) if row else 0
        except Exception as e:
            print(f"[ContextStore] Failed to count task instances: {e}")
            return 0

    def claim_next_scheduled_task(self, eligible_agents: List[str]) -> Optional[Dict[str, Any]]:
        if not self.enabled or not eligible_agents:
            return None

        normalized_agents = [a.strip().lower() for a in eligible_agents if a.strip()]
        try:
            with self.db_session() as cursor:
                if cursor is None: return None
                cursor.execute(
                    """
                    UPDATE task_instances
                    SET
                        status = 'in_progress',
                        picked_up_at = NOW(),
                        updated_at = NOW()
                    WHERE id = (
                        SELECT id FROM task_instances
                        WHERE status = 'queued'
                        AND (expected_agent IS NULL OR LOWER(expected_agent) = ANY(%s))
                        AND eta_pickup_at <= NOW()
                        ORDER BY 
                            CASE priority
                                WHEN 'critical' THEN 1
                                WHEN 'high' THEN 2
                                WHEN 'medium' THEN 3
                                WHEN 'low' THEN 4
                                ELSE 5
                            END ASC,
                            eta_pickup_at ASC
                        LIMIT 1
                        FOR UPDATE SKIP LOCKED
                    )
                    RETURNING *
                    """,
                    (normalized_agents,),
                )
                row = cursor.fetchone()
                return self._serialize_task_row(row) if row else None
        except Exception as e:
            print(f"[ContextStore] Failed to claim task: {e}")
            return None

    def assign_scheduled_task(self, task_id: int, assigned_agent: str) -> bool:
        safe_agent = (assigned_agent or "").strip().lower()
        if not safe_agent: return False
        try:
            with self.db_session() as cursor:
                if cursor is None: return False
                cursor.execute("UPDATE task_instances SET assigned_agent = %s, updated_at = NOW() WHERE id = %s", (safe_agent, task_id))
                return cursor.rowcount > 0
        except Exception as e:
            print(f"[ContextStore] Failed to assign task: {e}")
            return False

    def complete_scheduled_task(
        self,
        task_id: int,
        assigned_agent: str,
        status: str = "completed",
        result_summary: Optional[str] = None,
        error_details: Optional[str] = None,
    ) -> bool:
        normalized_status = (status or "").strip().lower()
        if normalized_status not in {"drafted", "completed", "failed", "cancelled"}:
            normalized_status = "completed"
        safe_agent = (assigned_agent or "").strip().lower() or None

        try:
            with self.db_session() as cursor:
                if cursor is None: return False
                cursor.execute(
                    """
                    UPDATE task_instances
                    SET
                        status = %s,
                        assigned_agent = COALESCE(%s, assigned_agent),
                        result_summary = %s,
                        error_details = %s,
                        completed_at = CASE
                            WHEN %s IN ('completed', 'failed', 'cancelled') THEN NOW()
                            ELSE completed_at
                        END,
                        updated_at = NOW()
                    WHERE id = %s
                    """,
                    (normalized_status, safe_agent, result_summary, error_details, normalized_status, task_id),
                )
                return cursor.rowcount > 0
        except Exception as e:
            print(f"[ContextStore] Failed to complete task: {e}")
            return False

    def cancel_scheduled_task(self, task_id: int) -> bool:
        return self.complete_scheduled_task(task_id=task_id, assigned_agent="system", status="cancelled", result_summary="Task cancelled by user/agent.")

    def get_scheduled_tasks_overview(self, queue_limit: int = 20) -> Dict[str, Any]:
        default_counts = {status: 0 for status in self.SCHEDULED_TASK_STATUSES}
        try:
            with self.db_session(commit=False) as cursor:
                if cursor is None: return {"generated_at": datetime.now(timezone.utc).isoformat(), "counts": default_counts, "queue_line": [], "recently_finished": []}
                
                cursor.execute("SELECT status, COUNT(*) AS total FROM task_instances GROUP BY status")
                counts = dict(default_counts)
                for row in cursor.fetchall():
                    counts[row["status"]] = int(row["total"])

                cursor.execute(
                    """
                    SELECT * FROM task_instances
                    WHERE status IN ('queued', 'in_progress', 'drafted')
                    ORDER BY 
                        CASE priority
                            WHEN 'critical' THEN 0
                            WHEN 'high' THEN 1
                            WHEN 'medium' THEN 2
                            ELSE 3
                        END,
                        eta_pickup_at ASC
                    LIMIT %s
                    """,
                    (max(1, queue_limit),),
                )
                queue_line = [self._serialize_task_row(row) for row in cursor.fetchall()]

                cursor.execute(
                    """
                    SELECT * FROM task_instances
                    WHERE status IN ('completed', 'failed', 'cancelled')
                    ORDER BY completed_at DESC
                    LIMIT 10
                    """
                )
                recently_finished = [self._serialize_task_row(row) for row in cursor.fetchall()]

                return {
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "counts": counts,
                    "queue_line": queue_line,
                    "recently_finished": recently_finished,
                }
        except Exception as e:
            print(f"[ContextStore] Failed to get task overview: {e}")
            return {"generated_at": datetime.now(timezone.utc).isoformat(), "counts": default_counts, "queue_line": [], "recently_finished": []}

    def get_agent_interaction_stats(self) -> Dict[str, Any]:
        try:
            with self.db_session(commit=False) as cursor:
                if cursor is None: return {}
                cursor.execute(
                    """
                    SELECT agent_name, COUNT(*) as msg_count, MAX(created_at) as last_active
                    FROM agent_messages
                    GROUP BY agent_name
                    """
                )
                rows = cursor.fetchall()
                return {row["agent_name"]: {"msg_count": row["msg_count"], "last_active": row["last_active"]} for row in rows}
        except Exception as e:
            print(f"[ContextStore] Failed to get agent interaction stats: {e}")
            return {}

    def list_agent_actions(self, limit: int = 50, offset: int = 0, agent_name: Optional[str] = None) -> List[Dict[str, Any]]:
        query = "SELECT * FROM agent_actions"
        params = []
        
        if agent_name:
            query += " WHERE LOWER(agent_name) = LOWER(%s)"
            params.append(agent_name)
            
        query += " ORDER BY timestamp DESC LIMIT %s OFFSET %s"
        params.extend([max(1, limit), max(0, offset)])
        
        try:
            with self.db_session(commit=False) as cursor:
                if cursor is None: return []
                cursor.execute(query, params)
                return list(cursor.fetchall())
        except Exception as e:
            print(f"[ContextStore] Failed to list agent actions: {e}")
            return []

    def get_total_agent_action_count(self, agent_name: Optional[str] = None) -> int:
        query = "SELECT COUNT(*) FROM agent_actions"
        params = []
        
        if agent_name:
            query += " WHERE LOWER(agent_name) = LOWER(%s)"
            params.append(agent_name)
            
        try:
            with self.db_session(commit=False) as cursor:
                if cursor is None: return 0
                cursor.execute(query, params)
                row = cursor.fetchone()
                return int(row["count"]) if row else 0
        except Exception as e:
            print(f"[ContextStore] Failed to count agent actions: {e}")
            return 0

    def list_newsletters(self, limit: int = 20) -> List[Dict[str, Any]]:
        try:
            with self.db_session(commit=False) as cursor:
                if cursor is None: return []
                cursor.execute("SELECT * FROM newsletters ORDER BY created_at DESC LIMIT %s", (max(1, limit),))
                return list(cursor.fetchall())
        except Exception as e:
            print(f"[ContextStore] Failed to list newsletters: {e}")
            return []

    def list_famiglia_agents(self) -> List[Dict[str, Any]]:
        try:
            with self.db_session(commit=False) as cursor:
                if cursor is None: return []
                cursor.execute(
                    """
                    WITH skill_map AS (
                        SELECT
                            as_.agent_id,
                            ARRAY_AGG(DISTINCT s.name ORDER BY s.name) AS skills,
                            ARRAY_AGG(DISTINCT s.id ORDER BY s.id) AS skill_ids
                        FROM agent_skills as_
                        INNER JOIN skills s ON s.id = as_.skill_id
                        GROUP BY as_.agent_id
                    ),
                    tool_map AS (
                        SELECT
                            at.agent_id,
                            ARRAY_AGG(DISTINCT t.name ORDER BY t.name) AS tools,
                            ARRAY_AGG(DISTINCT t.id ORDER BY t.id) AS tool_ids
                        FROM agent_tools at
                        INNER JOIN tools t ON t.id = at.tool_id
                        GROUP BY at.agent_id
                    ),
                    workflow_map AS (
                        SELECT
                            aw.agent_id,
                            ARRAY_AGG(DISTINCT w.name ORDER BY w.name) AS workflows,
                            ARRAY_AGG(DISTINCT w.id ORDER BY w.id) AS workflow_ids
                        FROM agent_workflows aw
                        INNER JOIN workflows w ON w.id = aw.workflow_id
                        GROUP BY aw.agent_id
                    ),
                    latest_messages AS (
                        SELECT DISTINCT ON (LOWER(m.agent_name))
                            LOWER(m.agent_name) AS agent_id,
                            LEFT(REGEXP_REPLACE(COALESCE(m.content, ''), '\\s+', ' ', 'g'), 220) AS latest_conversation_snippet,
                            m.created_at AS last_active
                        FROM agent_messages m
                        WHERE COALESCE(BTRIM(m.agent_name), '') <> ''
                        ORDER BY LOWER(m.agent_name), m.created_at DESC
                    )
                    SELECT
                        a.agent_id AS id,
                        a.agent_id,
                        a.agent_name AS name,
                        COALESCE(ar.name, 'Unassigned') AS role,
                        a.is_active,
                        CASE WHEN COALESCE(a.is_active, FALSE) THEN 'active' ELSE 'inactive' END AS status,
                        a.avatar_url,
                        COALESCE(a.aliases, ARRAY[]::TEXT[]) AS aliases,
                        COALESCE(NULLIF(BTRIM(a.persona), ''), 'Soul profile pending.') AS personality,
                        COALESCE(NULLIF(BTRIM(a.identity), ''), 'Identity profile pending.') AS identity,
                        COALESCE(sm.skills, ARRAY[]::TEXT[]) AS skills,
                        COALESCE(sm.skill_ids, ARRAY[]::INTEGER[]) AS skill_ids,
                        COALESCE(tm.tools, ARRAY[]::TEXT[]) AS tools,
                        COALESCE(tm.tool_ids, ARRAY[]::INTEGER[]) AS tool_ids,
                        COALESCE(wm.workflows, ARRAY[]::TEXT[]) AS workflows,
                        COALESCE(wm.workflow_ids, ARRAY[]::INTEGER[]) AS workflow_ids,
                        COALESCE(lm.latest_conversation_snippet, 'No recent conversation snippet available.') AS latest_conversation_snippet,
                        lm.last_active
                    FROM agents a
                    LEFT JOIN archetypes ar ON ar.id = a.archetype_id
                    LEFT JOIN skill_map sm ON sm.agent_id = a.agent_id
                    LEFT JOIN tool_map tm ON tm.agent_id = a.agent_id
                    LEFT JOIN workflow_map wm ON wm.agent_id = a.agent_id
                    LEFT JOIN latest_messages lm ON lm.agent_id = LOWER(a.agent_id)
                    ORDER BY COALESCE(a.is_active, FALSE) DESC, a.agent_name ASC
                    """
                )
                return list(cursor.fetchall())
        except Exception as e:
            print(f"[ContextStore] Failed to list Famiglia agents: {e}")
            return []

    # --- Agent Soul & Capability Management ---

    def get_agent_soul(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Fetch the core persona and identity for an agent."""
        try:
            with self.db_session(commit=False) as cursor:
                if cursor is None: return None
                cursor.execute("""
                    SELECT a.*, ar.name as archetype_name, ar.description as archetype_desc
                    FROM agents a
                    LEFT JOIN archetypes ar ON a.archetype_id = ar.id
                    WHERE a.agent_id = %s
                """, (agent_id,))
                return cursor.fetchone()
        except Exception as e:
            print(f"[ContextStore] Failed to fetch agent for {agent_id}: {e}")
            return None

    def get_agent_traits(self, agent_id: str) -> Dict[str, List[Dict[str, Any]]]:
        """Fetch normalized tools, skills, workflows, and resources for an agent."""
        traits = {
            "tools": [],
            "skills": [],
            "workflows": [],
            "resources": []
        }
        try:
            with self.db_session(commit=False) as cursor:
                if cursor is None: return traits
                
                # Fetch Tools
                cursor.execute("""
                    SELECT t.* FROM tools t
                    JOIN agent_tools at ON at.tool_id = t.id
                    WHERE at.agent_id = %s
                """, (agent_id,))
                traits["tools"] = list(cursor.fetchall())

                # Fetch Skills
                cursor.execute("""
                    SELECT s.* FROM skills s
                    JOIN agent_skills as_ ON as_.skill_id = s.id
                    WHERE as_.agent_id = %s
                """, (agent_id,))
                traits["skills"] = list(cursor.fetchall())

                # Fetch Workflows (with nodes)
                cursor.execute("""
                    SELECT w.* FROM workflows w
                    JOIN agent_workflows aw ON aw.workflow_id = w.id
                    WHERE aw.agent_id = %s
                """, (agent_id,))
                workflows = cursor.fetchall()
                for wf in workflows:
                    cursor.execute("SELECT * FROM workflow_nodes WHERE workflow_id = %s", (wf["id"],))
                    wf["nodes"] = list(cursor.fetchall())
                    traits["workflows"].append(wf)

                # Fetch Resources
                cursor.execute("""
                    SELECT r.* FROM resources r
                    JOIN agent_resources ar ON ar.resource_id = r.id
                    WHERE ar.agent_id = %s
                """, (agent_id,))
                traits["resources"] = list(cursor.fetchall())

                return traits
        except Exception as e:
            print(f"[ContextStore] Failed to fetch agent traits for {agent_id}: {e}")
            return traits

    def upsert_agent_soul(self, agent_id: str, agent_name: str, **kwargs) -> bool:
        """Update or create an agent soul record."""
        allowed_fields = {"persona", "reply_constraints", "identity", "aliases", "archetype_id", "is_active", "avatar_url"}
        update_fields = {k: v for k, v in kwargs.items() if k in allowed_fields}
        
        if not update_fields:
            query = "INSERT INTO agents (agent_id, agent_name) VALUES (%s, %s) ON CONFLICT (agent_id) DO NOTHING"
            params = (agent_id, agent_name)
        else:
            cols = ", ".join(update_fields.keys())
            placeholders = ", ".join(["%s"] * len(update_fields))
            set_clause = ", ".join([f"{k} = EXCLUDED.{k}" for k in update_fields.keys()])
            
            query = f"""
                INSERT INTO agents (agent_id, agent_name, {cols})
                VALUES (%s, %s, {placeholders})
                ON CONFLICT (agent_id) DO UPDATE SET
                agent_name = EXCLUDED.agent_name,
                {set_clause},
                updated_at = NOW()
            """
            params = (agent_id, agent_name, *update_fields.values())

        try:
            with self.db_session() as cursor:
                if cursor is None: return False
                cursor.execute(query, params)
                return True
        except Exception as e:
            print(f"[ContextStore] Failed to upsert agent soul for {agent_id}: {e}")
            return False

    def get_available_capabilities(self) -> Dict[str, List[Dict[str, Any]]]:
        """Fetch all available tools, skills, and workflows from the system."""
        capabilities = {"tools": [], "skills": [], "workflows": []}
        try:
            with self.db_session(commit=False) as cursor:
                if cursor is None: return capabilities
                
                cursor.execute("SELECT id, name, description, plugin FROM tools ORDER BY name")
                capabilities["tools"] = list(cursor.fetchall())
                
                cursor.execute("SELECT id, name, description, category FROM skills ORDER BY name")
                capabilities["skills"] = list(cursor.fetchall())
                
                cursor.execute("SELECT id, name, description, category FROM workflows ORDER BY name")
                capabilities["workflows"] = list(cursor.fetchall())
                
                return capabilities
        except Exception as e:
            print(f"[ContextStore] Failed to fetch available capabilities: {e}")
            return capabilities

    def update_agent_traits(self, agent_id: str, trait_type: str, trait_ids: List[int]) -> bool:
        """Sync junction tables for an agent's traits (tools, skills, workflows)."""
        table_map = {
            "tools": ("agent_tools", "tool_id"),
            "skills": ("agent_skills", "skill_id"),
            "workflows": ("agent_workflows", "workflow_id")
        }
        
        if trait_type not in table_map:
            return False
            
        table_name, col_name = table_map[trait_type]
        
        try:
            with self.db_session() as cursor:
                if cursor is None: return False
                
                # 1. Clear existing relationships
                cursor.execute(f"DELETE FROM {table_name} WHERE agent_id = %s", (agent_id,))
                
                # 2. Insert new relationships
                if trait_ids:
                    values = [(agent_id, tid) for tid in trait_ids]
                    query = f"INSERT INTO {table_name} (agent_id, {col_name}) VALUES %s ON CONFLICT DO NOTHING"
                    psycopg2.extras.execute_values(cursor, query, values)
                
                return True
        except Exception as e:
            print(f"[ContextStore] Failed to update agent {trait_type} for {agent_id}: {e}")
            return False

    # --- SOP (Standard Operating Procedure) Management ---

    def list_workflow_categories(self) -> List[Dict[str, Any]]:
        try:
            with self.db_session(commit=False) as cursor:
                if cursor is None: return []
                cursor.execute("SELECT * FROM workflow_categories ORDER BY display_name ASC")
                return list(cursor.fetchall())
        except Exception as e:
            print(f"[ContextStore] Failed to list workflow categories: {e}")
            return []

    def create_workflow_category(self, name: str, display_name: str) -> Optional[Dict[str, Any]]:
        try:
            with self.db_session() as cursor:
                if cursor is None: return None
                cursor.execute(
                    """
                    INSERT INTO workflow_categories (name, display_name)
                    VALUES (%s, %s)
                    ON CONFLICT (name) DO UPDATE SET
                        display_name = EXCLUDED.display_name
                    RETURNING *
                    """,
                    (name, display_name),
                )
                return cursor.fetchone()
        except Exception as e:
            print(f"[ContextStore] Failed to create workflow category: {e}")
            return None

    def delete_workflow_category(self, category_id: int) -> bool:
        try:
            with self.db_session() as cursor:
                if cursor is None: return False
                cursor.execute("DELETE FROM workflow_categories WHERE id = %s", (category_id,))
                return cursor.rowcount > 0
        except Exception as e:
            print(f"[ContextStore] Failed to delete workflow category: {e}")
            return False

    def list_sop_workflows(self, category_id: Optional[int] = None) -> List[Dict[str, Any]]:
        query = """
            SELECT w.*, c.name as category_name, c.display_name as category_display_name
            FROM workflows w
            LEFT JOIN workflow_categories c ON w.category_id = c.id
        """
        params = []
        if category_id:
            query += " WHERE w.category_id = %s"
            params.append(category_id)
        query += " ORDER BY w.display_name ASC"
        
        try:
            with self.db_session(commit=False) as cursor:
                if cursor is None: return []
                cursor.execute(query, params)
                return list(cursor.fetchall())
        except Exception as e:
            print(f"[ContextStore] Failed to list SOP workflows: {e}")
            return []

    def get_sop_workflow(self, workflow_id: int) -> Optional[Dict[str, Any]]:
        try:
            with self.db_session(commit=False) as cursor:
                if cursor is None: return None
                
                # Fetch workflow details with category info
                cursor.execute(
                    """
                    SELECT w.*, c.name as category_name, c.display_name as category_display_name
                    FROM workflows w
                    LEFT JOIN workflow_categories c ON w.category_id = c.id
                    WHERE w.id = %s
                    """, 
                    (workflow_id,)
                )
                workflow = cursor.fetchone()
                if not workflow:
                    return None
                
                # Fetch associated nodes
                cursor.execute("SELECT * FROM workflow_nodes WHERE workflow_id = %s", (workflow_id,))
                workflow["nodes"] = list(cursor.fetchall())
                
                return workflow
        except Exception as e:
            print(f"[ContextStore] Failed to fetch SOP workflow {workflow_id}: {e}")
            return None

    def create_sop_workflow(self, name: str, display_name: Optional[str] = None, description: Optional[str] = None, category_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
        try:
            display_name = display_name or name
            with self.db_session() as cursor:
                if cursor is None: return None
                cursor.execute(
                    """
                    INSERT INTO workflows (name, display_name, description, category_id, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, NOW(), NOW())
                    ON CONFLICT (name) DO UPDATE SET
                        display_name = COALESCE(EXCLUDED.display_name, workflows.display_name),
                        description = COALESCE(EXCLUDED.description, workflows.description),
                        category_id = COALESCE(EXCLUDED.category_id, workflows.category_id),
                        updated_at = NOW()
                    RETURNING *
                    """,
                    (name, display_name, description, category_id),
                )
                return cursor.fetchone()
        except Exception as e:
            print(f"[ContextStore] Failed to create SOP workflow: {e}")
            return None

    def delete_sop_workflow(self, workflow_id: int) -> bool:
        try:
            with self.db_session() as cursor:
                if cursor is None: return False
                cursor.execute("DELETE FROM workflows WHERE id = %s", (workflow_id,))
                return cursor.rowcount > 0
        except Exception as e:
            print(f"[ContextStore] Failed to delete SOP workflow {workflow_id}: {e}")
            return False

    def sync_workflow_nodes(self, workflow_id: int, nodes: List[Dict[str, Any]]) -> bool:
        """Fully sync the nodes of a workflow, replacing existing ones."""
        try:
            with self.db_session() as cursor:
                if cursor is None: return False
                
                # 1. Clear existing nodes
                cursor.execute("DELETE FROM workflow_nodes WHERE workflow_id = %s", (workflow_id,))
                
                # 2. Insert new nodes
                if nodes:
                    node_values = [(workflow_id, n["node_name"], n.get("description"), n.get("node_type", "task")) for n in nodes]
                    query = "INSERT INTO workflow_nodes (workflow_id, node_name, description, node_type, created_at) VALUES %s"
                    psycopg2.extras.execute_values(cursor, query, node_values)
                
                # 3. Update workflow node_order if provided in the list order
                node_names = [n["node_name"] for n in nodes]
                cursor.execute("UPDATE workflows SET node_order = %s, updated_at = NOW() WHERE id = %s", (node_names, workflow_id))
                
                return True
        except Exception as e:
            print(f"[ContextStore] Failed to sync workflow nodes for {workflow_id}: {e}")
            return False

    def update_sop_workflow_metadata(self, workflow_id: int, **kwargs) -> bool:
        allowed_fields = {"name", "display_name", "description", "category_id"}
        update_fields = {k: v for k, v in kwargs.items() if k in allowed_fields}
        if not update_fields:
            return False
            
        sets = ", ".join([f"{k} = %s" for k in update_fields.keys()])
        query = f"UPDATE workflows SET {sets}, updated_at = NOW() WHERE id = %s"
        params = (*update_fields.values(), workflow_id)
        
        try:
            with self.db_session() as cursor:
                if cursor is None: return False
                cursor.execute(query, params)
                return cursor.rowcount > 0
        except Exception as e:
            print(f"[ContextStore] Failed to update SOP workflow metadata {workflow_id}: {e}")
            return False

    def _get_connection(self):
        """Legacy compatibility method. returns a connection from the pool. 
        WARNING: The caller is expected to call conn.close(), but in this pool setup, 
        it should ideally be returned to the pool via putconn. 
        However, for SimpleConnectionPool, close() works but removes it from pool."""
        return self._get_pool().getconn()


context_store = AgentContextStore()
