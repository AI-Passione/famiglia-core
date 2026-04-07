from typing import List, Optional
from fastapi import APIRouter, HTTPException
from famiglia_core.command_center.backend.api.services.intelligence_service import intelligence_service
from famiglia_core.command_center.backend.api.models.intelligence import IntelligenceItem, IntelligenceItemCreate, IntelligenceItemUpdate

router = APIRouter(prefix="/intelligence", tags=["intelligence"])

@router.get("/", response_model=List[IntelligenceItem])
async def list_intelligence_items(item_type: Optional[str] = None):
    """List all intelligence items, optionally filtered by type."""
    return intelligence_service.list_items(item_type)

@router.get("/{item_id}", response_model=IntelligenceItem)
async def get_intelligence_item(item_id: int):
    """Retrieve a specific intelligence item."""
    item = intelligence_service.get_item(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Intelligence item not found")
    return item

@router.post("/", response_model=IntelligenceItem)
async def create_intelligence_item(item: IntelligenceItemCreate):
    """Create a new intelligence item."""
    created = intelligence_service.create_item(item)
    if not created:
        raise HTTPException(status_code=500, detail="Failed to create intelligence item")
    return created

@router.patch("/{item_id}", response_model=IntelligenceItem)
async def update_intelligence_item(item_id: int, update: IntelligenceItemUpdate):
    """Update an existing intelligence item."""
    updated = intelligence_service.update_item(item_id, update)
    if not updated:
        raise HTTPException(status_code=404, detail="Intelligence item not found or update failed")
    return updated

@router.delete("/{item_id}")
async def delete_intelligence_item(item_id: int):
    """Delete an intelligence item."""
    success = intelligence_service.delete_item(item_id)
    if not success:
        raise HTTPException(status_code=404, detail="Intelligence item not found")
    return {"status": "success", "message": f"Item {item_id} deleted"}

@router.post("/sync")
async def sync_intelligence_with_notion():
    """Trigger a sync with Notion to refresh intelligence items."""
    result = intelligence_service.sync_with_notion()
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "Sync failed"))
    return result
