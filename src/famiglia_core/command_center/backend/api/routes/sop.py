from typing import List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from datetime import datetime, timezone

from famiglia_core.db.agents.context_store import context_store

router = APIRouter(prefix="/sop", tags=["SOP"])

# --- Models ---

class SOPNodeBase(BaseModel):
    node_name: str
    description: Optional[str] = None
    node_type: str = "task"

class SOPNode(SOPNodeBase):
    id: Optional[int] = None
    workflow_id: Optional[int] = None

class SOPWorkflowBase(BaseModel):
    name: str
    display_name: Optional[str] = None
    description: Optional[str] = None
    category: str = "General"

class SOPWorkflowCreate(SOPWorkflowBase):
    nodes: List[SOPNodeBase] = []

class SOPWorkflow(SOPWorkflowBase):
    id: int
    node_order: List[str] = []
    nodes: List[SOPNode] = []
    created_at: datetime
    updated_at: datetime

class ExecutionResponse(BaseModel):
    task_id: int
    message: str

# --- Routes ---

@router.get("/workflows", response_model=List[SOPWorkflow])
async def list_workflows(category: Optional[str] = None):
    """List all SOP workflows, optionally filtered by category."""
    workflows_data = context_store.list_sop_workflows(category=category)
    result = []
    for wf in workflows_data:
        # Fetch nodes for each workflow to satisfy the response model
        full_wf = context_store.get_sop_workflow(wf["id"])
        if full_wf:
            result.append(full_wf)
    return result

@router.get("/workflows/{workflow_id}", response_model=SOPWorkflow)
async def get_workflow(workflow_id: int):
    """Fetch a specific SOP workflow by ID."""
    workflow = context_store.get_sop_workflow(workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="SOP Workflow not found")
    return workflow

@router.post("/workflows", response_model=SOPWorkflow)
async def create_workflow(payload: SOPWorkflowCreate):
    """Create a new SOP workflow with its nodes."""
    workflow = context_store.create_sop_workflow(
        name=payload.name,
        display_name=payload.display_name,
        description=payload.description,
        category=payload.category
    )
    if not workflow:
        raise HTTPException(status_code=500, detail="Failed to create SOP workflow")
    
    if payload.nodes:
        nodes_data = [node.dict() for node in payload.nodes]
        context_store.sync_workflow_nodes(workflow["id"], nodes_data)
        
    return context_store.get_sop_workflow(workflow["id"])

@router.put("/workflows/{workflow_id}", response_model=SOPWorkflow)
async def update_workflow(workflow_id: int, payload: SOPWorkflowCreate):
    """Update an existing SOP workflow and its nodes."""
    context_store.update_sop_workflow_metadata(
        workflow_id,
        name=payload.name,
        display_name=payload.display_name,
        description=payload.description,
        category=payload.category
    )
    
    # Even if metadata didn't change, we might want to sync nodes
    context_store.sync_workflow_nodes(workflow_id, [node.dict() for node in payload.nodes])
    
    updated_wf = context_store.get_sop_workflow(workflow_id)
    if not updated_wf:
        raise HTTPException(status_code=404, detail="SOP Workflow not found after update")
        
    return updated_wf

@router.delete("/workflows/{workflow_id}")
async def delete_workflow(workflow_id: int):
    """Delete an SOP workflow."""
    success = context_store.delete_sop_workflow(workflow_id)
    if not success:
        raise HTTPException(status_code=404, detail="SOP Workflow not found")
    return {"message": f"SOP Workflow {workflow_id} deleted successfully"}

@router.post("/workflows/{workflow_id}/execute", response_model=ExecutionResponse)
async def execute_sop(workflow_id: int):
    """Trigger the execution of an SOP workflow."""
    workflow = context_store.get_sop_workflow(workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="SOP Workflow not found")
    
    # Create a task instance to trigger the workflow
    # In a real scenario, this would be picked up by an orchestration agent
    task = context_store.create_scheduled_task(
        title=f"SOP Execution: {workflow['name']}",
        task_payload=f"Executing Standard Operating Procedure: {workflow['name']}. Category: {workflow['category']}",
        priority="high",
        created_by_type="human_user",
        created_by_name="Don", # Defaulting to Don
        metadata={
            "workflow_id": workflow_id,
            "task_type": "sop_execution",
            "triggered_at": datetime.now(timezone.utc).isoformat()
        }
    )
    
    if not task:
        raise HTTPException(status_code=500, detail="Failed to initiate SOP execution")
        
    return ExecutionResponse(
        task_id=task["id"],
        message=f"SOP '{workflow['name']}' dispatched for execution. Tracking ID: {task['id']}"
    )
