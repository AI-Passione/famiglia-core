import json
from datetime import datetime
from typing import Dict, Any, Optional
from famiglia_core.db.agents.context_store import context_store

class AuditLogger:
    def log_action(self, 
                   agent_name: str, 
                   action_type: str, 
                   action_details: Dict[str, Any], 
                   is_approval_required: bool = True,
                   approval_status: str = "PENDING",
                   cost_usd: float = 0.0) -> int:
        try:
            with context_store.db_session() as cursor:
                if cursor is None: return -1
                
                details_json = json.dumps(action_details)
                cursor.execute('''
                    INSERT INTO agent_actions (
                        timestamp, agent_name, action_type, action_details, 
                        is_approval_required, approval_status, cost_usd
                    ) VALUES (NOW(), %s, %s, %s, %s, %s, %s)
                    RETURNING id
                ''', (agent_name, action_type, details_json,
                      is_approval_required, approval_status, cost_usd))

                row = cursor.fetchone()
                return row["id"] if row else -1
        except Exception as exc:
            print(f"[AuditLogger] Failed to log action: {exc}")
            return -1

    def update_approval(self, action_id: int, status: str):
        """status should be APPROVED or REJECTED"""
        if action_id < 0: return

        try:
            with context_store.db_session() as cursor:
                if cursor is None: return
                cursor.execute('UPDATE agent_actions SET approval_status = %s, updated_at = NOW() WHERE id = %s', (status, action_id))
        except Exception as exc:
            print(f"[AuditLogger] Failed to update approval: {exc}")

    def mark_action_completed(self, action_id: int, duration_seconds: int):
        if action_id < 0: return

        try:
            with context_store.db_session() as cursor:
                if cursor is None: return
                cursor.execute('''
                    UPDATE agent_actions 
                    SET completed_at = NOW(), duration_seconds = %s, updated_at = NOW()
                    WHERE id = %s
                ''', (duration_seconds, action_id))
        except Exception as exc:
            print(f"[AuditLogger] Failed to mark action complete: {exc}")

# Singleton instance for agents to use
audit_logger = AuditLogger()
