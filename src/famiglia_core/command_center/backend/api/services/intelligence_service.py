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

    def sync_with_notion(self) -> Dict[str, Any]:
        """Truncate local DB and import all accessible Notion pages."""
        from famiglia_core.agents.tools.notion import notion_client
        
        try:
            # 1. Truncate
            with context_store.db_session() as cursor:
                if cursor is None: return {"success": False, "error": "DB connection failed"}
                cursor.execute("TRUNCATE TABLE intelligence_items RESTART IDENTITY CASCADE")
                print("[IntelligenceSync] Local table truncated.")

            # 2. Search Notion
            notion_items = notion_client.search()
            print(f"[IntelligenceSync] Found {len(notion_items)} items in Notion.")
            
            synced_count = 0
            for item in notion_items:
                if item.get("type") != "page": continue
                
                try:
                    # Fetch full page details and blocks
                    page_id = item["id"]
                    page_data = notion_client.read_page(page_id, agent_name="SystemSync")
                    
                    # Convert blocks to markdown
                    content_md = notion_client.blocks_to_markdown(page_data.get("blocks", []))
                    
                    # Map properties
                    props = page_data.get("page_properties", {})
                    title = props.get("title") or props.get("Name") or item.get("title") or "Unnamed Intelligence"
                    
                    item_type = 'analysis'
                    if 'Type' in props:
                        val = str(props['Type']).lower()
                        if 'market' in val or 'research' in val:
                            item_type = 'market_research'
                        elif 'prd' in val or 'product requirement' in val:
                            item_type = 'prd'
                        elif 'project' in val:
                            item_type = 'project'
                        elif 'analysis' in val:
                            item_type = 'analysis'
                    
                    status = props.get("Status") or "Active"
                    summary = content_md[:300] + "..." if len(content_md) > 300 else content_md
                    
                    # Prepare metadata and properties
                    metadata = {
                        "notion_url": page_data.get("url"),
                        "tags": props.get("Tags", []),
                    }
                    
                    # Insert into DB
                    with context_store.db_session() as cursor:
                        if cursor is None: continue
                        cursor.execute(
                            """
                            INSERT INTO intelligence_items (
                                notion_id, title, content, summary, status, item_type, 
                                icon, cover, properties, parent, url, public_url, 
                                in_trash, created_time, last_edited_time, created_by, last_edited_by,
                                updated_at
                            )
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                            """,
                            (
                                page_id,
                                title,
                                content_md,
                                summary,
                                str(status),
                                item_type,
                                context_store._safe_json(page_data.get("icon")),
                                context_store._safe_json(page_data.get("cover")),
                                context_store._safe_json(props),
                                context_store._safe_json(page_data.get("parent")),
                                page_data.get("url"),
                                page_data.get("public_url"),
                                page_data.get("in_trash", False),
                                page_data.get("created_time"),
                                page_data.get("last_edited_time"),
                                context_store._safe_json(page_data.get("created_by")),
                                context_store._safe_json(page_data.get("last_edited_by"))
                            )
                        )
                        synced_count += 1
                        print(f"[IntelligenceSync] Synced: {title}")
                except Exception as ex:
                    print(f"[IntelligenceSync] Skipping page {item.get('id')}: {ex}")

            return {"success": True, "synced_count": synced_count}
            
        except Exception as e:
            print(f"[IntelligenceSync] Global sync failed: {e}")
            return {"success": False, "error": str(e)}

intelligence_service = IntelligenceService()
