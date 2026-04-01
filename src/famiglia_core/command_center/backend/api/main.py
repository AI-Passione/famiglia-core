import os
import sys
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, HTMLResponse
from pydantic import BaseModel, Field
from psycopg2.extras import RealDictCursor

# Ensure project root is in path for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../../")))

from famiglia_core.db.agents.context_store import context_store
from famiglia_core.command_center.backend.graph_parser import GraphParser, GraphDefinition
from famiglia_core.command_center.backend.api.routes import chat, auth, connections, settings
from famiglia_core.command_center.backend.api.services.engine_room_service import engine_room_service

FEATURES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../agents/orchestration/features"))
graph_parser = GraphParser(FEATURES_DIR)

app = FastAPI(
    title="La Passione Commanding Center API",
    description="Unified API for AI Agent Orchestration and Command Center interactions.",
    version="2.0.0"
)

# Enable CORS for the frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify the actual frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(chat.router, prefix="/api/v1")
app.include_router(auth.router, prefix="/api/v1")
app.include_router(connections.router, prefix="/api/v1")
app.include_router(settings.router, prefix="/api/v1")

# --- Consolidated Models ---

class AgentStatus(BaseModel):
    name: str
    last_active: Optional[datetime] = None
    msg_count: int = 0
    status: str = "idle"

class ActionLog(BaseModel):
    id: int
    timestamp: datetime
    agent_name: str
    action_type: str
    action_details: Optional[Dict[str, Any]] = None
    approval_status: Optional[str] = None
    cost_usd: float = 0.0
    duration_seconds: Optional[int] = None
    completed_at: Optional[datetime] = None

class TaskInstance(BaseModel):
    id: int
    title: str
    task_payload: str
    status: str
    priority: str
    expected_agent: Optional[str] = None
    assigned_agent: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None
    result_summary: Optional[str] = None

class RecurringTaskTemplate(BaseModel):
    id: int
    title: str
    task_payload: str
    priority: str
    expected_agent: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    schedule_config: Dict[str, Any] = Field(default_factory=dict)
    last_spawned_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

class InsightSummary(BaseModel):
    id: int
    title: str
    rossini_tldr: Optional[str] = None
    relevance: str = "low"
    processed_at: Optional[datetime] = None

class MissionLog(BaseModel):
    id: str
    graph_id: str
    timestamp: str
    status: str
    duration: str
    initiator: str

class FamigliaAgentProfile(BaseModel):
    id: str
    agent_id: str
    name: str
    role: str
    status: str
    aliases: List[str] = Field(default_factory=list)
    personality: str
    identity: str
    skills: List[str] = Field(default_factory=list)
    tools: List[str] = Field(default_factory=list)
    workflows: List[str] = Field(default_factory=list)
    latest_conversation_snippet: str
    last_active: Optional[datetime] = None

# --- Core Informational Routes ---

@app.get("/")
async def root():
    return {
        "message": "Welcome to the La Passione Commanding Center API", 
        "version": "2.0.0",
        "status": "online"
    }

@app.get("/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc)}

@app.get("/api/v1/agents", response_model=List[AgentStatus])
async def get_agents():
    stats = context_store.get_agent_interaction_stats()
    agents = []
    famiglia = ["alfredo", "vito", "riccado", "rossini", "tommy", "bella", "kowalski"]
    for name in famiglia:
        agent_stat = stats.get(name, {"msg_count": 0, "last_active": None})
        agents.append(AgentStatus(
            name=name,
            last_active=agent_stat["last_active"],
            msg_count=agent_stat["msg_count"],
            status="idle"
        ))
    return agents

@app.get("/api/v1/actions", response_model=List[ActionLog])
async def get_actions(limit: int = 50):
    actions = context_store.list_agent_actions(limit=limit)
    return actions

@app.get("/api/v1/tasks", response_model=List[TaskInstance])
async def get_tasks(status: Optional[str] = None, limit: int = 50):
    statuses = [status] if status else None
    tasks = context_store.list_scheduled_tasks(statuses=statuses, limit=limit)
    return tasks

@app.get("/api/v1/recurring-tasks", response_model=List[RecurringTaskTemplate])
async def get_recurring_tasks():
    return context_store.list_recurring_tasks()

@app.get("/api/v1/insights", response_model=List[InsightSummary])
async def get_insights(limit: int = 20):
    insights = context_store.list_newsletters(limit=limit)
    return insights

@app.get("/api/v1/graphs", response_model=List[GraphDefinition])
async def get_graphs():
    graphs = graph_parser.parse_all_graphs()
    return graphs

@app.get("/api/v1/graphs/{graph_id}", response_model=Optional[GraphDefinition])
async def get_graph(graph_id: str):
    file_path = os.path.join(FEATURES_DIR, f"{graph_id}.py")
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Graph not found")
    return graph_parser.parse_file(file_path)

@app.get("/api/v1/mission-logs/{graph_id}", response_model=List[MissionLog])
async def get_mission_logs(graph_id: str):
    conn = None
    cursor = None
    try:
        conn = context_store._get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
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
        print(f"[API] Error fetching mission logs: {e}")
        return []
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

@app.get("/api/v1/famiglia/agents", response_model=List[FamigliaAgentProfile])
async def get_famiglia_agents():
    return context_store.list_famiglia_agents()


@app.get("/api/v1/engine-room")
async def get_engine_room_snapshot():
    return engine_room_service.get_snapshot()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
