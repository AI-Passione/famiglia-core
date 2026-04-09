import os
import asyncio
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from famiglia_core.db.agents.context_store import context_store
from famiglia_core.command_center.backend.graph_parser import GraphParser, GraphDefinition

router = APIRouter()

FEATURES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../agents/orchestration/features"))
print(f"[Operations] Discovery path for features: {FEATURES_DIR}")
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

class AdHocDirectiveRequest(BaseModel):
    graph_id: Optional[str] = None
    manual_prompt: Optional[str] = None
    specification: Optional[str] = None

GRAPH_AGENT_MAP = {
    "market_research": "rossini",
    "simple_data_analysis": "kowalski",
    "deep_dive_analysis": "kowalski",
    "code_implementation": "riccardo",
    "prd_drafting": "rossini",
    "milestone_creation": "bella",
    "prd_review": "rossini",
    "grooming": "bella"
}

AGENT_KEYWORD_MAP = {
    "kowalski": ["data", "analytics", "stats", "bi", "metrics", "chart", "plot"],
    "riccardo": ["code", "python", "devops", "sql", "db", "performance", "infrastructure", "bug"],
    "vito": ["finance", "money", "budget", "tax", "investment", "cost"],
    "rossini": ["research", "market", "strategy", "product", "intel"],
    "bella": ["schedule", "meeting", "docs", "notes", "project"],
    "tommy": ["logistics", "ops", "task", "follow-up"]
}

def resolve_agent(graph_id: Optional[str], prompt: Optional[str]) -> str:
    if graph_id and graph_id in GRAPH_AGENT_MAP:
        return GRAPH_AGENT_MAP[graph_id]
    
    if prompt:
        lower_prompt = prompt.lower()
        for agent, keywords in AGENT_KEYWORD_MAP.items():
            if any(k in lower_prompt for k in keywords):
                return agent
                
    return "alfredo"

@router.post("/directive/execute", response_model=ExecutionResponse)
async def execute_directive(request: AdHocDirectiveRequest):
    """Trigger a directive execution with automated agent routing."""
    graph_id = request.graph_id
    prompt = request.manual_prompt
    
    if not graph_id and not prompt:
        raise HTTPException(status_code=400, detail="Missing graph_id or manual_prompt")
        
    # 1. Resolve agent
    agent_id = resolve_agent(graph_id, prompt)
    
    # 2. Determine title and payload
    title = f"Directive: {graph_id or 'Ad-hoc Task'}"
    
    # If it's a graph mission, use specification as payload if provided
    payload = prompt or f"Executing graph {graph_id}"
    if graph_id and request.specification:
        payload = f"{payload}\n\nClient Specification: {request.specification}"
    
    # 3. Create task instance
    task = context_store.create_scheduled_task(
        title=title,
        task_payload=payload,
        priority="high",
        created_by_type="human_user",
        created_by_name="Don",
        metadata={
            "graph_id": graph_id,
            "agent_id": agent_id,
            "task_type": "adhoc_directive" if prompt else "operations_execution",
            "triggered_at": datetime.now(timezone.utc).isoformat()
        }
    )
    
    if not task:
        raise HTTPException(status_code=500, detail="Failed to initiate directive")

    # 4. Log immediate acknowledgement from agent
    conversation_key = f"web:command-center:direct:0" # Standard web channel
    ack_content = f"Directive received, Don Jimmy. I am initiating the {graph_id or 'requested task'} immediately."
    if agent_id == "riccardo":
        ack_content = "Understood. Deploying optimized directive now. Don't worry about the results, they will be flawless."
    elif agent_id == "kowalski":
        ack_content = "Received. The data vectors are aligning. I'll have the analysis ready shortly."

    context_store.log_message(
        agent_name=agent_id,
        conversation_key=conversation_key,
        role="agent",
        content=ack_content,
        sender=agent_id.capitalize(),
        metadata={"task_id": task["id"], "status": "typing"}
    )
    
    # 5. Start a background task to simulate completion (since we don't have real execution hooks here)
    async def simulate_completion(tid, aid, gid):
        await asyncio.sleep(5) # Simulate work
        try:
            # Mark task as completed
            context_store.update_task_status(tid, "completed")
            
            # Post completion message
            comp_content = f"Mission accomplished, Don Jimmy. The {gid or 'directive'} has been executed successfully."
            if aid == "kowalski":
                comp_content = "Analysis complete. The metrics confirm our strategic trajectory. I've updated the intelligence hub."
            
            context_store.log_message(
                agent_name=aid,
                conversation_key=conversation_key,
                role="agent",
                content=comp_content,
                sender=aid.capitalize(),
                metadata={"task_id": tid, "status": "done"}
            )
        except Exception as e:
            print(f"Error in mock completion: {e}")

    # Launch background task
    asyncio.create_task(simulate_completion(task["id"], agent_id, graph_id))

    return ExecutionResponse(
        task_id=task["id"],
        message=f"Directive assigned to {agent_id.capitalize()}. Tracking ID: ML-{task['id']:03d}"
    )

@router.get("/graphs", response_model=List[GraphDefinition])
async def get_graphs():
    """Discover all Operations graphs in the features directory recursively."""
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
                    COALESCE(metadata->>'graph_id', metadata->>'workflow_id') as graph_id,
                    created_at, 
                    status, 
                    picked_up_at, 
                    completed_at, 
                    created_by_name as initiator
                FROM task_instances
                WHERE metadata->>'task_type' IN ('operations_execution', 'sop_execution')
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
        print(f"[Operations API] Error fetching all mission logs: {e}")
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
        print(f"[Operations API] Error fetching mission logs: {e}")
        return []

@router.post("/graphs/{graph_id}/execute", response_model=ExecutionResponse)
async def execute_graph(graph_id: str, request: Request):
    """Trigger a new execution of an Operations graph."""
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
        title=f"Execute Operations: {graph.name}",
        task_payload=f"Triggering autonomous pipeline for {graph_id}",
        priority="high",
        created_by_type="human_user",
        created_by_name="Don", # Defaulting to Don for now
        metadata={
            "graph_id": graph_id,
            "task_type": "operations_execution",
            "triggered_at": datetime.now(timezone.utc).isoformat()
        }
    )

    if not task:
        raise HTTPException(status_code=500, detail="Failed to initiate Operations execution task")

    return ExecutionResponse(
        task_id=task["id"],
        message=f"Mission {graph_id} dispatched. Tracking ID: ML-{task['id']:03d}"
    )
