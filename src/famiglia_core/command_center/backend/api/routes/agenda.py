from datetime import datetime
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field, ConfigDict

from famiglia_core.db.agents.context_store import context_store

router = APIRouter(tags=["Agenda"])

# --- Models ---

class AgendaEvent(BaseModel):
    id: int
    title: str
    task_payload: str
    eta_pickup_at: datetime
    eta_completion_at: datetime
    status: str
    priority: str
    expected_agent: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    is_scheduled: bool = False

    # Adding user-friendly aliases for Google Calendar style consumption if needed
    @property
    def start(self) -> datetime:
        return self.eta_pickup_at
    
    @property
    def end(self) -> datetime:
        return self.eta_completion_at

class AgendaCreateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    title: str
    description: str = Field(..., alias="description")
    start: datetime = Field(..., alias="start")
    end: datetime = Field(..., alias="end")
    agent_id: Optional[str] = Field(None, alias="agent_id")
    priority: str = "medium"
    workflow_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

class AgendaUpdateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    title: Optional[str] = None
    description: Optional[str] = Field(None, alias="description")
    start: Optional[datetime] = Field(None, alias="start")
    end: Optional[datetime] = Field(None, alias="end")
    agent_id: Optional[str] = Field(None, alias="agent_id")
    priority: Optional[str] = None
    status: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

# --- Routes ---

@router.get("/events", response_model=List[AgendaEvent])
async def get_agenda_events(
    start: datetime = Query(..., description="ISO start date (e.g. 2026-04-20T00:00:00Z)"),
    end: datetime = Query(..., description="ISO end date (e.g. 2026-04-27T23:59:59Z)"),
    status: Optional[List[str]] = Query(None)
):
    """
    Fetch all agent directives (tasks) within a specific time window for the calendar view.
    Aligned with 'The Agenda' UX requirements.
    """
    tasks = context_store.list_tasks_in_range(start, end, status)
    return tasks

@router.post("/events", response_model=AgendaEvent)
async def create_agenda_event(request: AgendaCreateRequest):
    """
    Schedule a new directive for an agent via the Agenda.
    This creates a task instance that will be picked up by the orchestrator at the scheduled time.
    """
    metadata = request.metadata.copy()
    if request.workflow_id:
        metadata["graph_id"] = request.workflow_id
        metadata["task_type"] = request.workflow_id
    
    # Ensure mission visibility
    if "task_type" not in metadata:
        metadata["task_type"] = "scheduled_directive"

    task = context_store.create_scheduled_task(
        title=request.title,
        task_payload=request.description,
        priority=request.priority,
        created_by_type="human_user",
        created_by_name="Don",
        expected_agent=request.agent_id,
        eta_pickup_at=request.start,
        eta_completion_at=request.end,
        metadata=metadata,
        is_scheduled=True
    )
    
    if not task:
        raise HTTPException(status_code=500, detail="Failed to create agenda event")
    
    return task

@router.patch("/events/{event_id}", response_model=AgendaEvent)
async def update_agenda_event(event_id: int, request: AgendaUpdateRequest):
    """
    Update or reschedule an existing directive.
    Supports drag-and-drop rescheduling from the Google Calendar-style UI.
    """
    update_data = {}
    if request.title is not None: update_data["title"] = request.title
    if request.description is not None: update_data["task_payload"] = request.description
    if request.start is not None: update_data["eta_pickup_at"] = request.start
    if request.end is not None: update_data["eta_completion_at"] = request.end
    if request.agent_id is not None: update_data["expected_agent"] = request.agent_id
    if request.priority is not None: update_data["priority"] = request.priority
    if request.status is not None: update_data["status"] = request.status
    if request.metadata is not None: update_data["metadata"] = request.metadata

    updated_task = context_store.update_task_instance(event_id, **update_data)
    if not updated_task:
        raise HTTPException(status_code=404, detail=f"Event {event_id} not found or update failed")
    
    return updated_task

@router.delete("/events/{event_id}")
async def delete_agenda_event(event_id: int):
    """
    Cancel a scheduled directive.
    """
    success = context_store.cancel_scheduled_task(event_id)
    if not success:
        # If it was already completed/failed, we might need a different message, 
        # but for Agenda UX, 'cancel' is the primary action.
        raise HTTPException(status_code=404, detail=f"Event {event_id} not found or cannot be cancelled")
    
    return {"status": "success", "message": f"Event {event_id} cancelled"}
