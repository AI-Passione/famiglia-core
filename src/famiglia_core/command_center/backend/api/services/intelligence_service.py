from typing import List, Optional, Dict, Any
import logging
from famiglia_core.db.agents.context_store import context_store
from famiglia_core.command_center.backend.api.models.intelligence import IntelligenceItemCreate, IntelligenceItemUpdate

logger = logging.getLogger(__name__)

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
            logger.error(f"[IntelligenceService] Failed to list items (type={item_type}): {e}")
            return []

    def get_item(self, item_id: int) -> Optional[Dict[str, Any]]:
        try:
            with context_store.db_session(commit=False) as cursor:
                if cursor is None: return None
                cursor.execute("SELECT * FROM intelligence_items WHERE id = %s", (item_id,))
                return cursor.fetchone()
        except Exception as e:
            logger.error(f"[IntelligenceService] Failed to get item {item_id}: {e}")
            return None

    def create_item(self, item: IntelligenceItemCreate) -> Optional[Dict[str, Any]]:
        logger.info(f"[IntelligenceService] Creating item: {item.title}")
        try:
            with context_store.db_session() as cursor:
                if cursor is None: 
                    logger.error("[IntelligenceService] Failed to create item: DB session is None")
                    return None
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
                row = cursor.fetchone()
                if row:
                    logger.info(f"[IntelligenceService] Item created successfully: ID {row['id']}")
                else:
                    logger.warning(f"[IntelligenceService] No row returned after INSERT for '{item.title}'")
                return row
        except Exception as e:
            logger.error(f"[IntelligenceService] Failed to create item '{item.title}': {e}", exc_info=True)
            return None

    def update_item(self, item_id: int, update: IntelligenceItemUpdate) -> Optional[Dict[str, Any]]:
        logger.info(f"[IntelligenceService] Updating item {item_id}")
        # Build dynamic update query
        fields = []
        params = []
        update_data = update.model_dump(exclude_unset=True)
        
        if not update_data:
            return self.get_item(item_id)
            
        for key, value in update_data.items():
            fields.append(f"{key} = %s")
            if key in ("metadata", "properties", "icon", "cover", "parent", "created_by", "last_edited_by"):
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
                row = cursor.fetchone()
                if row:
                    logger.info(f"[IntelligenceService] Item {item_id} updated successfully")
                return row
        except Exception as e:
            logger.error(f"[IntelligenceService] Failed to update item {item_id}: {e}")
            return None

    def delete_item(self, item_id: int) -> bool:
        logger.warning(f"[IntelligenceService] Deleting item {item_id}")
        try:
            with context_store.db_session() as cursor:
                if cursor is None: return False
                cursor.execute("DELETE FROM intelligence_items WHERE id = %s", (item_id,))
                success = cursor.rowcount > 0
                if success:
                    logger.info(f"[IntelligenceService] Item {item_id} deleted successfully")
                return success
        except Exception as e:
            logger.error(f"[IntelligenceService] Failed to delete item {item_id}: {e}")
            return False

    def sync_with_notion(self) -> Dict[str, Any]:
        """Disabled for now to prevent local data loss. Truncate was previous logic."""
        logger.warning("[IntelligenceSync] Sync requested, but currently disabled to protect local data.")
        return {
            "success": True, 
            "message": "Notion integration is currently dormant to protect local records. All local researches are preserved.",
            "synced_count": 0
        }
        
        # from famiglia_core.agents.tools.notion import notion_client
        # 
        # try:
        #     # 1. Truncate (REMOVED: This was causing data loss)
        #     # with context_store.db_session() as cursor:
        #     #     if cursor is None: return {"success": False, "error": "DB connection failed"}
        #     #     cursor.execute("TRUNCATE TABLE intelligence_items RESTART IDENTITY CASCADE")
        #     #     logger.warning("[IntelligenceSync] Local table truncated for full resync.")
        # 
        #     # 2. Search Notion
        #     # ... (rest of the logic commented out)

intelligence_service = IntelligenceService()
