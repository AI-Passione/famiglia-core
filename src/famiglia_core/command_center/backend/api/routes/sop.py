import os
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from famiglia_core.db.agents.context_store import context_store
from famiglia_core.command_center.backend.graph_parser import GraphParser, GraphDefinition

router = APIRouter()

FEATURES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../../agents/orchestration/features"))
graph_parser = GraphParser(FEATURES_DIR)

class MissionLog(BaseModel):
    id: str
    graph_id: str
    timestamp: str
    status: str
    duration: str
    initiator: str

class ExecutionResponse(BaseModel):
    task_id: int
    message: str

@router.get("/graphs", response_model=List[GraphDefinition])
async def get_graphs():
    """Discover all SOP graphs in the features directory recursively."""
    return graph_parser.parse_all_graphs()

@router.get("/graphs/{graph_id}", response_model=Optional[GraphDefinition])
async def get_graph(graph_id: str):
    """Fetch a specific graph definition by ID."""
    # Since we support nested directories, we might need to find the file first
    for root, _, files in os.walk(FEATURES_DIR):
        if f"{graph_id}.py" in files:
            return graph_parser.parse_file(os.path.join(root, f"{graph_id}.py"))
    
    raise HTTPException(status_code=404, detail="Graph not found")

@router.get("/mission-logs/all", response_model=List[MissionLog])
async def get_all_mission_logs():
    """Fetch global execution history for all SOP graphs from task_instances."""
    try:
        with context_store.db_session(commit=False) as cursor:
            if cursor is None:
                return []
                
            query = """
                SELECT 
                    id, 
                    metadata->>'graph_id' as graph_id,
                    created_at, 
                    status, 
                    picked_up_at, 
                    completed_at, 
                    created_by_name as initiator
                FROM task_instances
                WHERE metadata->>'task_type' = 'sop_execution'
                ORDER BY created_at DESC
                LIMIT 40
            """
            cursor.execute(query)
            rows = cursor.fetchall()
            
            logs = []
            for row in rows:
                duration_str = "N/A"
                if row["picked_up_at"] and row["completed_at"]:
                    diff = row["completed_at"] - row["picked_up_at"]
                    duration_str = f"{diff.total_seconds():.1f}s"
                elif row["status"] == "in_progress" and row["picked_up_at"]:
                    diff = datetime.now(timezone.utc) - row["picked_up_at"]
                    duration_str = f"{diff.total_seconds():.1f}s+"
                
                status = row["status"]
                if status == "completed": status = "success"
                elif status == "failed": status = "failure"
                elif status == "in_progress": status = "running"
                
                logs.append(MissionLog(
                    id=f"ML-{row['id']:03d}",
                    graph_id=row["graph_id"] or "unspecified",
                    timestamp=row["created_at"].strftime("%Y-%m-%d %H:%M:%S"),
                    status=status,
                    duration=duration_str,
                    initiator=row["initiator"] or "System"
                ))
            return logs
    except Exception as e:
        print(f"[SOP API] Error fetching all mission logs: {e}")
        return []

@router.get("/mission-logs/{graph_id}", response_model=List[MissionLog])
async def get_mission_logs(graph_id: str):
    """Fetch execution history for a specific graph from task_instances."""
    try:
        # Re-using the logic from main.py but in a more modular way
        with context_store.db_session(commit=False) as cursor:
            if cursor is None:
                return []
                
            query = """
                SELECT 
                    id, 
                    created_at, 
                    status, 
                    picked_up_at, 
                    completed_at, 
                    created_by_name as initiator
                FROM task_instances
                WHERE (metadata->>'graph_id' = %s OR metadata->>'task_type' = %s OR metadata->>'task_type' LIKE %s)
                ORDER BY created_at DESC
                LIMIT 20
            """
            like_pattern = f"{graph_id}%"
            cursor.execute(query, (graph_id, graph_id, like_pattern))
            rows = cursor.fetchall()
            
            logs = []
            for row in rows:
                duration_str = "N/A"
                if row["picked_up_at"] and row["completed_at"]:
                    diff = row["completed_at"] - row["picked_up_at"]
                    duration_str = f"{diff.total_seconds():.1f}s"
                elif row["status"] == "in_progress" and row["picked_up_at"]:
                    diff = datetime.now(timezone.utc) - row["picked_up_at"]
                    duration_str = f"{diff.total_seconds():.1f}s+"
                
                status = row["status"]
                if status == "completed": status = "success"
                elif status == "failed": status = "failure"
                elif status == "in_progress": status = "running"
                
                logs.append(MissionLog(
                    id=f"ML-{row['id']:03d}",
                    graph_id=graph_id,
                    timestamp=row["created_at"].strftime("%Y-%m-%d %H:%M:%S"),
                    status=status,
                    duration=duration_str,
                    initiator=row["initiator"] or "System"
                ))
            return logs
    except Exception as e:
        print(f"[SOP API] Error fetching mission logs: {e}")
        return []

@router.post("/graphs/{graph_id}/execute", response_model=ExecutionResponse)
async def execute_graph(graph_id: str, request: Request):
    """Trigger a new execution of an SOP graph."""
    # Find the graph to ensure it exists
    graph = None
    for root, _, files in os.walk(FEATURES_DIR):
        if f"{graph_id}.py" in files:
            graph = graph_parser.parse_file(os.path.join(root, f"{graph_id}.py"))
            break
            
    if not graph:
        raise HTTPException(status_code=404, detail=f"Graph {graph_id} not found")

    # Create a task instance for the orchestration layer
    task = context_store.create_scheduled_task(
        title=f"Execute SOP: {graph.name}",
        task_payload=f"Triggering autonomous pipeline for {graph_id}",
        priority="high",
        created_by_type="human_user",
        created_by_name="Don", # Defaulting to Don for now
        metadata={
            "graph_id": graph_id,
            "task_type": "sop_execution",
            "triggered_at": datetime.now(timezone.utc).isoformat()
        }
    )

    if not task:
        raise HTTPException(status_code=500, detail="Failed to initiate SOP execution task")

    return ExecutionResponse(
        task_id=task["id"],
        message=f"Mission {graph_id} dispatched. Tracking ID: ML-{task['id']:03d}"
    )
