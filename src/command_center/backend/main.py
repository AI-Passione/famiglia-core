from fastapi import FastAPI, Depends, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, HTMLResponse
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime, timezone
from psycopg2.extras import RealDictCursor

import os
import sys

# Add the project root to sys.path to allow importing from src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

from src.db.agents.context_store import context_store
from src.command_center.backend.graph_parser import GraphParser, GraphDefinition
from src.command_center.backend.github.auth_github import github_oauth_client
from src.command_center.backend.slack.auth_slack import slack_oauth_client
from src.command_center.backend.notion.auth_notion import notion_oauth_client
from src.db.tools.user_connections_store import user_connections_store

FEATURES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../agents/orchestration/features"))
graph_parser = GraphParser(FEATURES_DIR)

app = FastAPI(title="La Passione Commanding Center API")

# Enable CORS for the frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify the actual frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Pydantic Models ---

class AgentStatus(BaseModel):
    name: str
    last_active: Optional[datetime] = None
    msg_count: int = 0
    status: str = "idle"  # idle, thinking, error

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
    status: str # 'success', 'failure', 'running'
    duration: str
    initiator: str

@app.get("/")
async def root():
    return {"message": "Welcome to the La Passione Commanding Center API", "version": "1.0.0"}


@app.get("/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.now()}

@app.get("/agents", response_model=List[AgentStatus])
async def get_agents():
    stats = context_store.get_agent_interaction_stats()
    agents = []
    # Known agents from the famiglia
    famiglia = ["alfredo", "vito", "riccado", "rossini", "tommy", "bella"]
    for name in famiglia:
        agent_stat = stats.get(name, {"msg_count": 0, "last_active": None})
        agents.append(AgentStatus(
            name=name,
            last_active=agent_stat["last_active"],
            msg_count=agent_stat["msg_count"],
            status="idle" # TODO: Real-time status from Redis?
        ))
    return agents

@app.get("/actions", response_model=List[ActionLog])
async def get_actions(limit: int = 50):
    actions = context_store.list_agent_actions(limit=limit)
    return actions

@app.get("/tasks", response_model=List[TaskInstance])
async def get_tasks(status: Optional[str] = None, limit: int = 50):
    statuses = [status] if status else None
    tasks = context_store.list_scheduled_tasks(statuses=statuses, limit=limit)
    return tasks

@app.get("/insights", response_model=List[InsightSummary])
async def get_insights(limit: int = 20):
    insights = context_store.list_newsletters(limit=limit)
    return insights

@app.get("/graphs", response_model=List[GraphDefinition])
async def get_graphs():
    graphs = graph_parser.parse_all_graphs()
    return graphs

@app.get("/graphs/{graph_id}", response_model=Optional[GraphDefinition])
async def get_graph(graph_id: str):
    file_path = os.path.join(FEATURES_DIR, f"{graph_id}.py")
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Graph not found")
    return graph_parser.parse_file(file_path)

@app.get("/mission-logs/{graph_id}", response_model=List[MissionLog])
async def get_mission_logs(graph_id: str):
    conn = None
    cursor = None
    try:
        conn = context_store._get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Query task_instances filtering by metadata->'graph_id' or task_type
        # We also want to include relevant initiators and durations
        query = """
            SELECT 
                id, 
                created_at, 
                status, 
                picked_up_at, 
                completed_at, 
                created_by_name as initiator,
                metadata->>'graph_id' as graph_id_meta
            FROM task_instances
            WHERE (metadata->>'graph_id' = %s OR metadata->>'task_type' = %s OR metadata->>'task_type' LIKE %s)
            ORDER BY created_at DESC
            LIMIT 20
        """
        like_pattern = f"{graph_id}%"
        print(f"[API] Querying mission logs for graph_id='{graph_id}', like_pattern='{like_pattern}'")
        cursor.execute(query, (graph_id, graph_id, like_pattern))
        rows = cursor.fetchall()
        print(f"[API] Found {len(rows)} mission logs for '{graph_id}'")
        
        logs = []
        for row in rows:
            # Calculate duration
            duration_str = "N/A"
            if row["picked_up_at"] and row["completed_at"]:
                diff = row["completed_at"] - row["picked_up_at"]
                duration_str = f"{diff.total_seconds():.1f}s"
            elif row["status"] == "in_progress" and row["picked_up_at"]:
                diff = datetime.now(timezone.utc) - row["picked_up_at"]
                duration_str = f"{diff.total_seconds():.1f}s+"
            
            # Normalize status
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

# ---------------------------------------------------------------------------
# GitHub OAuth — User Account Connection
# ---------------------------------------------------------------------------

FRONTEND_BASE = os.getenv("FRONTEND_BASE_URL", "http://localhost:5173")


@app.get("/auth/github", tags=["connections"])
async def github_auth_start():
    """
    Initiate the GitHub OAuth flow.
    Returns the GitHub authorization URL for the frontend to redirect to.
    """
    try:
        url = github_oauth_client.get_authorization_url()
        return {"authorization_url": url}
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))


@app.get("/auth/github/callback", tags=["connections"])
async def github_auth_callback(
    code: str = Query(..., description="Authorization code from GitHub"),
    state: Optional[str] = Query(None),
    error: Optional[str] = Query(None),
):
    """
    GitHub OAuth callback — exchanges the code for a token, stores it, then
    redirects back to the Command Center Connections page with a status flag.
    """
    redirect_base = f"{FRONTEND_BASE}/?tab=connections"

    if error:
        print(f"[Auth] GitHub OAuth denied by user: {error}")
        return RedirectResponse(url=f"{redirect_base}&github_error={error}")

    try:
        # 1. Exchange code for token
        token_data = github_oauth_client.exchange_code_for_token(code)
        access_token = token_data["access_token"]
        scopes = token_data.get("scope", "")

        # 2. Fetch user profile
        user_info = github_oauth_client.get_user_info(access_token)
        username = user_info.get("login")
        avatar_url = user_info.get("avatar_url")

        # 3. Persist encrypted token
        success = user_connections_store.upsert_connection(
            service="github",
            access_token=access_token,
            username=username,
            avatar_url=avatar_url,
            scopes=scopes,
        )

        if not success:
            return RedirectResponse(url=f"{redirect_base}&github_error=db_error")

        # Instead of a full redirect which results in a dashboard-in-a-popup,
        # we return a script that tells the parent window to refresh and then closes the popup.
        return HTMLResponse(content=f"""
            <html>
                <body style="background: #000; color: #fff; font-family: sans-serif; display: flex; align-items: center; justify-content: center; height: 100vh;">
                    <div style="text-align: center;">
                        <h2 style="color: #ffb3b5;">Handshake Complete</h2>
                        <p style="color: #666;">Syncing with the Situation Room...</p>
                    </div>
                    <script>
                        if (window.opener) {{
                            window.opener.postMessage("github_success", "*");
                            window.close();
                        }} else {{
                            window.location.href = "{FRONTEND_BASE}/?tab=connections&github_connected=true";
                        }}
                    </script>
                </body>
            </html>
        """)
    except Exception as e:
        print(f"[Auth] GitHub OAuth callback error: {e}")
        return RedirectResponse(url=f"{redirect_base}&github_error=token_exchange_failed")


# ---------------------------------------------------------------------------
# Slack OAuth — User Account Connection
# ---------------------------------------------------------------------------

@app.get("/auth/slack", tags=["connections"])
async def slack_auth_start():
    """
    Initiate the Slack OAuth flow.
    Returns the Slack authorization URL for the frontend to redirect to.
    """
    try:
        url = slack_oauth_client.get_authorization_url()
        return {"authorization_url": url}
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))


@app.get("/auth/slack/callback", tags=["connections"])
async def slack_auth_callback(
    code: str = Query(..., description="Authorization code from Slack"),
    state: Optional[str] = Query(None),
    error: Optional[str] = Query(None),
):
    """
    Slack OAuth callback — exchanges the code for a user token, stores it, then
    redirects back to the Command Center Connections page.
    """
    redirect_base = f"{FRONTEND_BASE}/?tab=connections"

    if error:
        print(f"[Auth] Slack OAuth denied by user: {error}")
        return RedirectResponse(url=f"{redirect_base}&slack_error={error}")

    try:
        # 1. Exchange code for token
        data = slack_oauth_client.exchange_code_for_token(code)
        authed_user = data["authed_user"]
        access_token = authed_user["access_token"]
        scopes = authed_user.get("scope", "")

        # 2. Fetch user profile
        profile = slack_oauth_client.get_user_info(access_token)
        username = profile.get("display_name") or profile.get("real_name") or profile.get("display_name_normalized")
        avatar_url = profile.get("image_512") or profile.get("image_192")

        # 3. Persist encrypted token
        success = user_connections_store.upsert_connection(
            service="slack",
            access_token=access_token,
            username=username,
            avatar_url=avatar_url,
            scopes=scopes,
        )

        if not success:
            return RedirectResponse(url=f"{redirect_base}&slack_error=db_error")

        return HTMLResponse(content=f"""
            <html>
                <body style="background: #000; color: #fff; font-family: sans-serif; display: flex; align-items: center; justify-content: center; height: 100vh;">
                    <div style="text-align: center;">
                        <h2 style="color: #ffb3b5;">Handshake Complete</h2>
                        <p style="color: #666;">Syncing your Slack identity...</p>
                    </div>
                    <script>
                        if (window.opener) {{
                            window.opener.postMessage("slack_success", "*");
                            window.close();
                        }} else {{
                            window.location.href = "{FRONTEND_BASE}/?tab=connections&slack_connected=true";
                        }}
                    </script>
                </body>
            </html>
        """)
    except Exception as e:
        print(f"[Auth] Slack OAuth callback error: {e}")
        return RedirectResponse(url=f"{redirect_base}&slack_error=token_exchange_failed")


@app.get("/connections/slack", tags=["connections"])
async def get_slack_connection():
    """Return the current Slack connection status."""
    status = user_connections_store.get_connection_status("slack")
    return status


@app.delete("/connections/slack", tags=["connections"])
async def disconnect_slack():
    """Remove the stored Slack OAuth token."""
    deleted = user_connections_store.delete_connection("slack")
    if deleted:
        return {"success": True, "message": "Slack account disconnected."}
    raise HTTPException(status_code=500, detail="Failed to disconnect Slack account.")


@app.get("/connections/github", tags=["connections"])
async def get_github_connection():
    """
    Return the current GitHub connection status for the dashboard owner.
    Never exposes the raw access token — returns username, avatar_url, connected_at.
    """
    status = user_connections_store.get_connection_status("github")
    return status


# ---------------------------------------------------------------------------
# Notion OAuth — User Account Connection
# ---------------------------------------------------------------------------

@app.get("/auth/notion", tags=["connections"])
async def notion_auth_start():
    """
    Initiate the Notion OAuth flow.
    Returns the Notion authorization URL for the frontend to redirect to.
    """
    try:
        url = notion_oauth_client.get_authorization_url()
        return {"authorization_url": url}
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))


@app.get("/auth/notion/callback", tags=["connections"])
async def notion_auth_callback(
    code: str = Query(..., description="Authorization code from Notion"),
    state: Optional[str] = Query(None),
    error: Optional[str] = Query(None),
):
    """
    Notion OAuth callback — exchanges the code for a token, stores it, then
    returns a script to close the popup and notify the parent window.
    """
    redirect_base = f"{FRONTEND_BASE}/?tab=connections"

    if error:
        print(f"[Auth] Notion OAuth denied by user: {error}")
        return RedirectResponse(url=f"{redirect_base}&notion_error={error}")

    try:
        # 1. Exchange code for token
        data = notion_oauth_client.exchange_code_for_token(code)
        access_token = data["access_token"]
        
        # Notion specific fields
        workspace_name = data.get("workspace_name")
        workspace_icon = data.get("workspace_icon")
        bot_id = data.get("bot_id")
        
        # 2. Persist encrypted token
        success = user_connections_store.upsert_connection(
            service="notion",
            access_token=access_token,
            username=workspace_name,
            avatar_url=workspace_icon,
            scopes=f"bot_id:{bot_id}",
        )

        if not success:
            return RedirectResponse(url=f"{redirect_base}&notion_error=db_error")

        return HTMLResponse(content=f"""
            <html>
                <body style="background: #000; color: #fff; font-family: sans-serif; display: flex; align-items: center; justify-content: center; height: 100vh;">
                    <div style="text-align: center;">
                        <h2 style="color: #ffb3b5;">Handshake Complete</h2>
                        <p style="color: #666;">Syncing with the Situation Room...</p>
                    </div>
                    <script>
                        if (window.opener) {{
                            window.opener.postMessage("notion_success", "*");
                            window.close();
                        }} else {{
                            window.location.href = "{FRONTEND_BASE}/?tab=connections&notion_connected=true";
                        }}
                    </script>
                </body>
            </html>
        """)
    except Exception as e:
        print(f"[Auth] Notion OAuth callback error: {e}")
        return RedirectResponse(url=f"{redirect_base}&notion_error=token_exchange_failed")


@app.get("/connections/notion", tags=["connections"])
async def get_notion_connection():
    """Return the current Notion connection status."""
    status = user_connections_store.get_connection_status("notion")
    return status


@app.delete("/connections/notion", tags=["connections"])
async def disconnect_notion():
    """Remove the stored Notion OAuth token."""
    deleted = user_connections_store.delete_connection("notion")
    if deleted:
        return {"success": True, "message": "Notion account disconnected."}
    raise HTTPException(status_code=500, detail="Failed to disconnect Notion account.")



@app.get("/connections/config", tags=["connections"])
async def get_connections_config():
    """Returns whether individual service integrations are configured (have credentials)."""
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


@app.delete("/connections/github", tags=["connections"])
async def disconnect_github():
    """Remove the stored GitHub OAuth token, disconnecting the account."""
    deleted = user_connections_store.delete_connection("github")
    if deleted:
        return {"success": True, "message": "GitHub account disconnected."}
    raise HTTPException(status_code=500, detail="Failed to disconnect GitHub account.")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
