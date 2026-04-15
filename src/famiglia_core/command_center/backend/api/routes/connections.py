from fastapi import APIRouter, HTTPException
from typing import Dict, Any
from pydantic import BaseModel
from famiglia_core.db.tools.user_connections_store import user_connections_store
from famiglia_core.command_center.backend.github.auth_github import github_oauth_client
from famiglia_core.command_center.backend.comms.slack.auth_slack import slack_oauth_client
from famiglia_core.command_center.backend.notion.auth_notion import notion_oauth_client

router = APIRouter(prefix="/connections", tags=["connections"])

class ApiKeyPayload(BaseModel):
    api_key: str

@router.get("/config")
async def get_connections_config():
    """Returns configuration status for third-party services."""
    return {
        "github": {
            "configured": github_oauth_client.is_configured(),
            "redirect_uri": github_oauth_client.redirect_uri,
            "client_id": github_oauth_client.client_id or None,
        },
        "slack": {
            "configured": slack_oauth_client.is_configured(),
            "redirect_uri": slack_oauth_client.redirect_uri,
            "client_id": slack_oauth_client.client_id or None,
        },
        "notion": {
            "configured": notion_oauth_client.is_configured(),
            "redirect_uri": notion_oauth_client.redirect_uri,
            "client_id": notion_oauth_client.client_id or None,
        }
    }

@router.get("/{service}")
async def get_connection_status(service: str):
    """Retrieve the status of a specific connection."""
    status = user_connections_store.get_connection_status(service)
    if not status:
        return {"connected": False, "service": service}
    return status

@router.post("/ollama/key")
async def save_ollama_api_key(payload: ApiKeyPayload):
    """Store an Ollama API key (encrypted) in the database."""
    if not payload.api_key.strip():
        raise HTTPException(status_code=422, detail="API key cannot be empty.")
    success = user_connections_store.upsert_connection(
        service="ollama",
        access_token=payload.api_key.strip(),
    )
    if success:
        return {"success": True, "message": "Ollama API key saved."}
    raise HTTPException(status_code=500, detail="Failed to save Ollama API key.")

@router.delete("/{service}")
async def disconnect_service(service: str):
    """Disconnect a service and remove its stored OAuth token."""
    deleted = user_connections_store.delete_connection(service)
    if deleted:
        return {"success": True, "message": f"{service.capitalize()} account disconnected."}
    raise HTTPException(status_code=500, detail=f"Failed to disconnect {service} account.")
