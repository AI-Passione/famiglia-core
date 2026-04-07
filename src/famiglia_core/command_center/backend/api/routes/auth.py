from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import RedirectResponse, HTMLResponse
from typing import Optional
import os

from famiglia_core.command_center.backend.github.auth_github import github_oauth_client
from famiglia_core.command_center.backend.comms.slack.auth_slack import slack_oauth_client
from famiglia_core.command_center.backend.notion.auth_notion import notion_oauth_client
from famiglia_core.db.tools.user_connections_store import user_connections_store

router = APIRouter(prefix="/auth", tags=["auth"])

FRONTEND_BASE = os.getenv("FRONTEND_BASE_URL", "http://localhost:5173")

@router.get("/github")
async def github_auth_start():
    url = github_oauth_client.get_authorization_url()
    return {"authorization_url": url}

@router.get("/github/callback")
async def github_auth_callback(code: str, state: Optional[str] = None):
    token_data = github_oauth_client.exchange_code_for_token(code)
    user_info = github_oauth_client.get_user_info(token_data["access_token"])
    user_connections_store.upsert_connection(
        service="github", access_token=token_data["access_token"],
        username=user_info.get("login"), avatar_url=user_info.get("avatar_url"),
        scopes=token_data.get("scope", "")
    )
    return HTMLResponse(content="<html><script>window.opener.postMessage('github_success', '*');window.close();</script></html>")

@router.get("/slack")
async def slack_auth_start():
    url = slack_oauth_client.get_authorization_url()
    return {"authorization_url": url}

@router.get("/slack/callback")
async def slack_auth_callback(code: str, state: Optional[str] = None):
    data = slack_oauth_client.exchange_code_for_token(code)
    authed_user = data["authed_user"]
    profile = slack_oauth_client.get_user_info(authed_user["access_token"])
    user_connections_store.upsert_connection(
        service="slack", access_token=authed_user["access_token"],
        username=profile.get("real_name"), avatar_url=profile.get("image_512"),
        scopes=authed_user.get("scope", "")
    )
    return HTMLResponse(content="<html><script>window.opener.postMessage('slack_success', '*');window.close();</script></html>")

@router.get("/notion")
async def notion_auth_start():
    url = notion_oauth_client.get_authorization_url()
    return {"authorization_url": url}

@router.get("/notion/callback")
async def notion_auth_callback(code: str, state: Optional[str] = None):
    data = notion_oauth_client.exchange_code_for_token(code)
    user_connections_store.upsert_connection(
        service="notion", access_token=data["access_token"],
        username=data.get("workspace_name"), avatar_url=data.get("workspace_icon"),
        scopes=f"bot_id:{data.get('bot_id')}"
    )
    return HTMLResponse(content="<html><script>window.opener.postMessage('notion_success', '*');window.close();</script></html>")
