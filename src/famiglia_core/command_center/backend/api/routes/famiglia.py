import os
import shutil
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel, Field

from famiglia_core.db.agents.context_store import context_store

router = APIRouter(tags=["famiglia"])

# --- Models ---

class AgentUpdate(BaseModel):
    name: Optional[str] = None
    persona: Optional[str] = None
    identity: Optional[str] = None
    aliases: Optional[List[str]] = None
    is_active: Optional[bool] = None

class CapabilitySync(BaseModel):
    tools: List[int] = Field(default_factory=list)
    skills: List[int] = Field(default_factory=list)
    workflows: List[int] = Field(default_factory=list)

# --- Routes ---

@router.get("/agents")
async def list_agents():
    """List all agents in the Famiglia (Refactored from main.py)."""
    return context_store.list_famiglia_agents()

@router.get("/capabilities")
async def get_capabilities():
    """Get all available tools, skills, and workflows for selection."""
    return context_store.get_available_capabilities()

@router.patch("/agents/{agent_id}")
async def update_agent(agent_id: str, update: AgentUpdate):
    """Update an agent's basic dossier details."""
    success = context_store.upsert_agent_soul(
        agent_id=agent_id,
        agent_name=update.name or agent_id.capitalize(),
        persona=update.persona,
        identity=update.identity,
        aliases=update.aliases,
        is_active=update.is_active
    )
    if not success:
        raise HTTPException(status_code=500, detail=f"Failed to update agent {agent_id}")
    return {"status": "success", "agent_id": agent_id}

@router.put("/agents/{agent_id}/capabilities")
async def sync_capabilities(agent_id: str, sync: CapabilitySync):
    """Sync an agent's skills, tools, and workflows."""
    results = {
        "tools": context_store.update_agent_traits(agent_id, "tools", sync.tools),
        "skills": context_store.update_agent_traits(agent_id, "skills", sync.skills),
        "workflows": context_store.update_agent_traits(agent_id, "workflows", sync.workflows)
    }
    
    if not all(results.values()):
        failed = [k for k, v in results.items() if not v]
        raise HTTPException(status_code=500, detail=f"Failed to sync: {', '.join(failed)}")
        
    return {"status": "success", "results": results}

@router.post("/agents/{agent_id}/avatar")
async def upload_avatar(agent_id: str, file: UploadFile = File(...)):
    """Upload and save a new profile picture for an agent."""
    # Ensure images directory exists (should be handled by main.py, but safe to be defensive)
    images_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../../docs/images"))
    if not os.path.exists(images_dir):
        os.makedirs(images_dir, exist_ok=True)
    
    # 1. Define filename (sanitize or just use agent_id)
    extension = os.path.splitext(file.filename)[1].lower() or ".png"
    if extension not in [".png", ".jpg", ".jpeg", ".gif", ".webp"]:
        raise HTTPException(status_code=400, detail="Unsupported image format")
        
    filename = f"{agent_id}_custom{extension}"
    file_path = os.path.join(images_dir, filename)
    
    # 2. Save the file
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {e}")
        
    # 3. Update DB
    avatar_url = f"/api/v1/images/{filename}"
    success = context_store.upsert_agent_soul(
        agent_id=agent_id,
        agent_name=agent_id.capitalize(), # Fallback, upsert needs it
        avatar_url=avatar_url
    )
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to save avatar reference to database")
        
    return {"status": "success", "avatar_url": avatar_url}
