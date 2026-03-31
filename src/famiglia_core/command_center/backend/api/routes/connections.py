from fastapi import APIRouter, HTTPException
from typing import Dict, Any
from famiglia_core.db.tools.user_connections_store import user_connections_store
from famiglia_core.command_center.backend.github.auth_github import github_oauth_client
from famiglia_core.command_center.backend.slack.auth_slack import slack_oauth_client
from famiglia_core.command_center.backend.notion.auth_notion import notion_oauth_client

router = APIRouter(prefix="/connections", tags=["connections"])

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

@router.delete("/{service}")
async def disconnect_service(service: str):
    """Disconnect a service and remove its stored OAuth token."""
    deleted = user_connections_store.delete_connection(service)
    if deleted:
        return {"success": True, "message": f"{service.capitalize()} account disconnected."}
    raise HTTPException(status_code=500, detail=f"Failed to disconnect {service} account.")
