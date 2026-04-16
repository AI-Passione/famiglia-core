import os
import json
import requests as http_requests
from fastapi import APIRouter, HTTPException
from typing import Dict, Any
from pydantic import BaseModel
from famiglia_core.db.tools.user_connections_store import user_connections_store
from famiglia_core.command_center.backend.github.auth_github import github_oauth_client
from famiglia_core.command_center.backend.comms.slack.auth_slack import slack_oauth_client
from famiglia_core.command_center.backend.notion.auth_notion import notion_oauth_client
from famiglia_core.command_center.backend.comms.slack.agent_auth import router as agent_auth_router

router = APIRouter(prefix="/connections", tags=["connections"])
router.include_router(agent_auth_router)

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

@router.get("/ollama/test")
async def test_ollama_connection():
    """Test the stored Ollama API key by probing the Ollama /api/tags endpoint."""
    status = user_connections_store.get_connection_status("ollama")
    if not status.get("connected"):
        raise HTTPException(status_code=404, detail="No Ollama API key stored.")

    connection = user_connections_store.get_connection("ollama")
    if not connection:
        raise HTTPException(
            status_code=500,
            detail="API key exists but could not be decrypted — FERNET_SECRET in your .env may be missing or changed.",
        )

    ollama_host = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")
    url = f"{ollama_host}/api/tags"
    headers = {"Authorization": f"Bearer {connection['access_token']}"}

    try:
        response = http_requests.get(url, headers=headers, timeout=5)
    except http_requests.exceptions.ConnectionError:
        raise HTTPException(status_code=503, detail=f"Could not reach Ollama at {ollama_host}. Is it running?")
    except http_requests.exceptions.Timeout:
        raise HTTPException(status_code=504, detail=f"Ollama at {ollama_host} timed out.")

    if response.status_code == 401:
        raise HTTPException(status_code=401, detail="API key rejected by Ollama. Check your key.")
    if not response.ok:
        raise HTTPException(status_code=response.status_code, detail=f"Ollama returned {response.status_code}.")

    models = [m["name"] for m in response.json().get("models", [])]
    return {"success": True, "host": ollama_host, "models": models}

@router.post("/slack/provision")
async def provision_slack_famiglia(payload: Dict[str, str]):
    """Trigger bulk creation of Slack apps using an App-Level Token."""
    token = payload.get("app_level_token")
    
    if not token:
        # Fallback: check if we have a stored bootstrap token
        conn = user_connections_store.get_connection("slack_bootstrap")
        if conn and conn.get("access_token"):
            token = conn["access_token"]
        else:
            raise HTTPException(status_code=422, detail="App-Level Token is required.")
    else:
        # Persist the new token so we can use it for retries/background tasks
        user_connections_store.upsert_connection(
            service="slack_bootstrap",
            access_token=token,
            username="Bootstrapper"
        )
    
    from famiglia_core.command_center.backend.comms.slack.provisioning import slack_provisioning
    try:
        apps = slack_provisioning.provision_famiglia(token)
        return {"success": True, "apps": apps}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/slack/finalize")
async def finalize_slack_agent(payload: Dict[str, str]):
    """Save finalized tokens (Bot + Socket) for a specific agent."""
    agent_id = payload.get("agent_id")
    bot_token = payload.get("bot_token")
    app_token = payload.get("app_token")
    
    if not all([agent_id, bot_token, app_token]):
        raise HTTPException(status_code=422, detail="agent_id, bot_token, and app_token are required.")
    
    from famiglia_core.command_center.backend.comms.slack.provisioning import slack_provisioning
    success = slack_provisioning.finalize_agent(agent_id, bot_token, app_token)
    if success:
        return {"success": True}
    raise HTTPException(status_code=500, detail="Failed to save tokens.")

@router.get("/slack/status")
async def get_slack_famiglia_status():
    """Report connection status for all 8 agent bots."""
    agents = ["alfredo", "vito", "riccardo", "rossini", "tommy", "bella", "kowalski", "giuseppina"]
    status = {}
    for agent_id in agents:
        bot_check = user_connections_store.get_connection_status(f"slack_bot:{agent_id}")
        socket_check = user_connections_store.get_connection_status(f"slack_socket:{agent_id}")
        bot_connected = bool(bot_check.get("connected"))
        socket_connected = bool(socket_check.get("connected"))
        # Check transport mode
        creds_conn = user_connections_store.get_connection(f"slack_creds:{agent_id}")
        transport = "socket" # Default
        public_url = None
        if creds_conn:
            try:
                cdata = json.loads(creds_conn["access_token"])
                transport = cdata.get("transport", "socket")
                public_url = cdata.get("public_url")
            except:
                pass

        status[agent_id] = {
            "connected": bot_connected,
            "bot_connected": bot_connected,
            "socket_connected": socket_connected,
            "transport": transport,
            "public_url": public_url,
            "name": agent_id.capitalize()
        }
    return status

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
