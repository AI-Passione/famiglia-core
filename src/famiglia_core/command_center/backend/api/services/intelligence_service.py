from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from famiglia_core.db.agents.context_store import context_store
from famiglia_core.command_center.backend.api.models.intelligence import IntelligenceItem, IntelligenceItemCreate, IntelligenceItemUpdate

class IntelligenceService:
    def list_items(self, item_type: Optional[str] = None) -> List[Dict[str, Any]]:
        query = "SELECT * FROM intelligence_items"
        params = []
        if item_type:
            query += " WHERE item_type = %s"
            params.append(item_type)
        query += " ORDER BY updated_at DESC"
        
        try:
            with context_store.db_session(commit=False) as cursor:
                if cursor is None: return []
                cursor.execute(query, params)
                return list(cursor.fetchall())
        except Exception as e:
            print(f"[IntelligenceService] Failed to list items: {e}")
            return []

    def get_item(self, item_id: int) -> Optional[Dict[str, Any]]:
        try:
            with context_store.db_session(commit=False) as cursor:
                if cursor is None: return None
                cursor.execute("SELECT * FROM intelligence_items WHERE id = %s", (item_id,))
                return cursor.fetchone()
        except Exception as e:
            print(f"[IntelligenceService] Failed to get item {item_id}: {e}")
            return None

    def create_item(self, item: IntelligenceItemCreate) -> Optional[Dict[str, Any]]:
        try:
            with context_store.db_session() as cursor:
                if cursor is None: return None
                cursor.execute(
                    """
                    INSERT INTO intelligence_items (title, content, summary, status, item_type, reference_id, metadata, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
                    RETURNING *
                    """,
                    (
                        item.title,
                        item.content,
                        item.summary,
                        item.status,
                        item.item_type,
                        item.reference_id,
                        context_store._safe_json(item.metadata)
                    ),
                )
                return cursor.fetchone()
        except Exception as e:
            print(f"[IntelligenceService] Failed to create item: {e}")
            return None

    def update_item(self, item_id: int, update: IntelligenceItemUpdate) -> Optional[Dict[str, Any]]:
        # Build dynamic update query
        fields = []
        params = []
        update_data = update.model_dump(exclude_unset=True)
        
        if not update_data:
            return self.get_item(item_id)
            
        for key, value in update_data.items():
            fields.append(f"{key} = %s")
            if key == "metadata":
                params.append(context_store._safe_json(value))
            else:
                params.append(value)
        
        fields.append("updated_at = NOW()")
        params.append(item_id)
        
        query = f"UPDATE intelligence_items SET {', '.join(fields)} WHERE id = %s RETURNING *"
        
        try:
            with context_store.db_session() as cursor:
                if cursor is None: return None
                cursor.execute(query, params)
                return cursor.fetchone()
        except Exception as e:
            print(f"[IntelligenceService] Failed to update item {item_id}: {e}")
            return None

    def delete_item(self, item_id: int) -> bool:
        try:
            with context_store.db_session() as cursor:
                if cursor is None: return False
                cursor.execute("DELETE FROM intelligence_items WHERE id = %s", (item_id,))
                return cursor.rowcount > 0
        except Exception as e:
            print(f"[IntelligenceService] Failed to delete item {item_id}: {e}")
            return False

intelligence_service = IntelligenceService()
