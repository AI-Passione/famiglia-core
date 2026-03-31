import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Iterator, Tuple

from langgraph.checkpoint.base import BaseCheckpointSaver, Checkpoint, CheckpointMetadata, CheckpointTuple
from src.db.agents.context_store import context_store

class PostgresJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, Exception):
            return str(obj)
        return super().default(obj)

class PostgresCheckpointer(BaseCheckpointSaver):
    """
    A LangGraph checkpointer that uses PostgreSQL for persistence.
    Reuses the connection pool from context_store.
    """

    def __init__(self):
        super().__init__()
        # Connection test happens via context_store on first use

    def get_tuple(self, config: Dict[str, Any]) -> Optional[CheckpointTuple]:
        """Get a checkpoint tuple from the database."""
        thread_id = config.get("configurable", {}).get("thread_id")
        checkpoint_id = config.get("configurable", {}).get("checkpoint_id")
        
        if not thread_id: return None

        try:
            with context_store.db_session(commit=False) as cursor:
                if cursor is None: return None

                if checkpoint_id:
                    cursor.execute(
                        "SELECT thread_id, checkpoint_id, parent_id, checkpoint, metadata FROM langgraph_checkpoints WHERE thread_id = %s AND checkpoint_id = %s",
                        (thread_id, checkpoint_id)
                    )
                else:
                    cursor.execute(
                        "SELECT thread_id, checkpoint_id, parent_id, checkpoint, metadata FROM langgraph_checkpoints WHERE thread_id = %s ORDER BY created_at DESC LIMIT 1",
                        (thread_id,)
                    )

                row = cursor.fetchone()
                if row:
                    # Fetch pending writes
                    cursor.execute(
                        "SELECT task_id, channel, value FROM langgraph_writes WHERE thread_id = %s AND checkpoint_id = %s ORDER BY task_id, idx",
                        (row["thread_id"], row["checkpoint_id"])
                    )
                    pending_writes = [(w["task_id"], w["channel"], w["value"]) for w in cursor.fetchall()]
                    
                    return CheckpointTuple(
                        config={
                            "configurable": {
                                "thread_id": row["thread_id"],
                                "checkpoint_id": row["checkpoint_id"]
                            }
                        },
                        checkpoint=row["checkpoint"],
                        metadata=row["metadata"],
                        parent_config={
                            "configurable": {
                                "thread_id": row["thread_id"],
                                "checkpoint_id": row["parent_id"]
                            }
                        } if row["parent_id"] else None,
                        pending_writes=pending_writes
                    )
                return None
        except Exception as e:
            print(f"[PostgresCheckpointer] Error getting checkpoint: {e}")
            return None

    def list(self, 
             config: Dict[str, Any], *, 
             filter: Optional[Dict[str, Any]] = None, 
             before: Optional[Dict[str, Any]] = None, 
             limit: Optional[int] = None) -> Iterator[CheckpointTuple]:
        """List checkpoints from the database."""
        thread_id = config.get("configurable", {}).get("thread_id")
        if not thread_id: return

        try:
            with context_store.db_session(commit=False) as cursor:
                if cursor is None: return

                query = "SELECT thread_id, checkpoint_id, parent_id, checkpoint, metadata FROM langgraph_checkpoints WHERE thread_id = %s"
                params = [thread_id]

                if before:
                    query += " AND created_at < (SELECT created_at FROM langgraph_checkpoints WHERE thread_id = %s AND checkpoint_id = %s)"
                    params.extend([thread_id, before["configurable"]["checkpoint_id"]])

                query += " ORDER BY created_at DESC"
                if limit:
                    query += " LIMIT %s"
                    params.append(limit)

                cursor.execute(query, tuple(params))
                rows = cursor.fetchall()
                
                for row in rows:
                    # Fetch pending writes for each
                    cursor.execute(
                        "SELECT task_id, channel, value FROM langgraph_writes WHERE thread_id = %s AND checkpoint_id = %s ORDER BY task_id, idx",
                        (row["thread_id"], row["checkpoint_id"])
                    )
                    pending_writes = [(w["task_id"], w["channel"], w["value"]) for w in cursor.fetchall()]
                    
                    yield CheckpointTuple(
                        config={
                            "configurable": {
                                "thread_id": row["thread_id"],
                                "checkpoint_id": row["checkpoint_id"]
                            }
                        },
                        checkpoint=row["checkpoint"],
                        metadata=row["metadata"],
                        parent_config={
                            "configurable": {
                                "thread_id": row["thread_id"],
                                "checkpoint_id": row["parent_id"]
                            }
                        } if row["parent_id"] else None,
                        pending_writes=pending_writes
                    )
        except Exception as e:
            print(f"[PostgresCheckpointer] Error listing checkpoints: {e}")

    def put(self, config: Dict[str, Any], checkpoint: Checkpoint, metadata: CheckpointMetadata, *args) -> Dict[str, Any]:
        """Save a checkpoint to the database."""
        thread_id = config.get("configurable", {}).get("thread_id")
        checkpoint_id = checkpoint.get("id")

        if not thread_id:
            print("[PostgresCheckpointer] Error: No thread_id provided in config")
            return config

        parent_id = config.get("configurable", {}).get("checkpoint_id")

        try:
            with context_store.db_session() as cursor:
                if cursor is None: return config
                
                checkpoint_json = json.dumps(checkpoint, cls=PostgresJSONEncoder)
                metadata_json = json.dumps(metadata, cls=PostgresJSONEncoder)
                
                cursor.execute(
                    """
                    INSERT INTO langgraph_checkpoints (thread_id, checkpoint_id, parent_id, checkpoint, metadata)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (thread_id, checkpoint_id) DO UPDATE SET
                        checkpoint = EXCLUDED.checkpoint,
                        metadata = EXCLUDED.metadata
                    """,
                    (thread_id, checkpoint_id, parent_id, checkpoint_json, metadata_json)
                )
                return {
                    "configurable": {
                        "thread_id": thread_id,
                        "checkpoint_id": checkpoint_id
                    }
                }
        except Exception as e:
            print(f"[PostgresCheckpointer] FAILED to save checkpoint: {e}")
            return config

    def put_writes(self, config: Dict[str, Any], writes: List[Tuple[str, Any]], task_id: str) -> None:
        """Save intermediate writes to the database."""
        thread_id = config.get("configurable", {}).get("thread_id")
        checkpoint_id = config.get("configurable", {}).get("checkpoint_id")
        
        if not thread_id or not checkpoint_id: return

        try:
            with context_store.db_session() as cursor:
                if cursor is None: return
                
                for idx, (channel, value) in enumerate(writes):
                    value_json = json.dumps(value, cls=PostgresJSONEncoder)
                    cursor.execute(
                        """
                        INSERT INTO langgraph_writes (thread_id, checkpoint_id, task_id, idx, channel, value)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        ON CONFLICT (thread_id, checkpoint_id, task_id, idx) DO UPDATE SET
                            channel = EXCLUDED.channel,
                            value = EXCLUDED.value
                        """,
                        (thread_id, checkpoint_id, task_id, idx, channel, value_json)
                    )
        except Exception as e:
            print(f"[PostgresCheckpointer] FAILED to save writes: {e}")
