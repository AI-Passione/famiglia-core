import os
import sys
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

# Ensure project root is in path for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../../")))

from famiglia_core.db.agents.context_store import context_store
from famiglia_core.command_center.backend.api.routes import chat, auth, connections, settings, famiglia, operations, sop, intelligence
from famiglia_core.command_center.backend.api.services.engine_room_service import engine_room_service

IMAGES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../../docs/images"))

def _parse_origin_list(*values: str) -> List[str]:
    origins: List[str] = []
    for value in values:
        for raw_origin in value.split(","):
            origin = raw_origin.strip().rstrip("/")
            if origin and origin not in origins:
                origins.append(origin)
    return origins

allowed_origins = _parse_origin_list(
    os.getenv("CORS_ALLOW_ORIGINS", ""),
    os.getenv("FRONTEND_BASE_URL", "http://localhost:5173"),
    os.getenv("BACKEND_BASE_URL", "http://localhost:8000"),
)

app = FastAPI(
    title="La Passione Commanding Center API",
    description="Unified API for AI Agent Orchestration and Command Center interactions.",
    version="2.0.0"
)

# Enable CORS for the frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(chat.router, prefix="/api/v1")
app.include_router(auth.router, prefix="/api/v1")
app.include_router(connections.router, prefix="/api/v1")
app.include_router(settings.router, prefix="/api/v1")
app.include_router(famiglia.router, prefix="/api/v1/famiglia")
app.include_router(operations.router, prefix="/api/v1/operations", tags=["Operations"])
app.include_router(sop.router, prefix="/api/v1", tags=["SOP"])
app.include_router(intelligence.router, prefix="/api/v1", tags=["Intelligence"])

# Serve static images
if os.path.exists(IMAGES_DIR):
    app.mount("/api/v1/images", StaticFiles(directory=IMAGES_DIR), name="images")
else:
    print(f"[API] Warning: Images directory not found at {IMAGES_DIR}")

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

class PaginatedTasks(BaseModel):
    tasks: List[TaskInstance]
    total: int

class PaginatedActions(BaseModel):
    actions: List[ActionLog]
    total: int

class ConversationLog(BaseModel):
    id: int
    conversation_key: str
    metadata: Optional[Dict[str, Any]] = None
    updated_at: datetime
    latest_message: Optional[str] = None
    latest_agent: Optional[str] = None

class PaginatedConversations(BaseModel):
    conversations: List[ConversationLog]
    total: int

@app.post("/api/v1/comms/slack/events/{agent_id}")
async def legacy_slack_event_bridge(agent_id: str, request: Request):
    """Legacy compatibility bridge for Slack events."""
    from famiglia_core.command_center.backend.api.routes.connections import handle_slack_event
    return await handle_slack_event(agent_id, request)

# --- Core Informational Routes ---

@app.get("/")
async def root():
    return {
        "message": "Welcome to the La Passione Commanding Center API", 
        "version": "2.0.0",
        "status": "online"
    }

@app.get("/health")
@app.get("/api/health")
@app.get("/api/v1/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc)}

@app.get("/api/v1/agents")
async def get_agents():
    """Returns the full agent roster enriched with dossier details."""
    return context_store.list_famiglia_agents()

@app.get("/api/v1/actions", response_model=PaginatedActions)
async def get_actions(limit: int = 50, offset: int = 0, agent_name: Optional[str] = None):
    actions_data = context_store.list_agent_actions(limit=limit, offset=offset, agent_name=agent_name)
    total = context_store.get_total_agent_action_count(agent_name=agent_name)
    
    # Map database results to ActionLog models
    actions = []
    for row in actions_data:
        actions.append(ActionLog(**row))
        
    return PaginatedActions(actions=actions, total=total)

@app.get("/api/v1/tasks", response_model=PaginatedTasks)
async def get_tasks(status: Optional[str] = None, limit: int = 50, offset: int = 0):
    statuses = [status] if status else None
    tasks = context_store.list_scheduled_tasks(statuses=statuses, limit=limit, offset=offset)
    total = context_store.get_total_task_count(statuses=statuses)
    return PaginatedTasks(tasks=tasks, total=total)

@app.get("/api/v1/conversations", response_model=PaginatedConversations)
async def get_conversations(limit: int = 50, offset: int = 0):
    conversations = context_store.list_conversations(limit=limit, offset=offset)
    total = context_store.get_total_conversation_count()
    return PaginatedConversations(conversations=conversations, total=total)

@app.get("/api/v1/recurring-tasks", response_model=List[RecurringTaskTemplate])
async def get_recurring_tasks():
    return context_store.list_recurring_tasks()

@app.get("/api/v1/insights", response_model=List[InsightSummary])
async def get_insights(limit: int = 20):
    insights = context_store.list_newsletters(limit=limit)
    return insights

@app.get("/api/v1/engine-room")
async def get_engine_room_snapshot():
    return engine_room_service.get_snapshot()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
