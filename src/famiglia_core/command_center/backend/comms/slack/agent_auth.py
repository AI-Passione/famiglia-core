"""
agent_auth.py
Automated OAuth handshake for dynamically provisioned Slack agents.
Exchanges code for access_token using credentials stored in PostgreSQL.
"""
import requests
from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import HTMLResponse
from famiglia_core.db.tools.user_connections_store import user_connections_store

router = APIRouter(prefix="/auth/slack/agent", tags=["slack_agent_auth"])

SLACK_TOKEN_URL = "https://slack.com/api/oauth.v2.access"

@router.get("/callback")
async def agent_oauth_callback(
    code: str = Query(..., description="The OAuth code from Slack"),
    state: str = Query(..., description="The agent_id being authorized")
):
    """
    Handle the OAuth redirect from a newly provisioned Slack agent.
    'state' should contains the agent_id (e.g., 'giuseppina').
    """
    agent_id = state
    
    # 1. Fetch the provisioned credentials for this agent
    creds = user_connections_store.get_connection(f"slack_creds:{agent_id}")
    if not creds:
        raise HTTPException(status_code=404, detail=f"No credentials found for agent '{agent_id}'. Refresh and try again.")
    
    # client_id and client_secret are stored in the 'access_token' and 'username'?
    # Actually, let's see how we stored them in provisioning.py (I'll define that now).
    # We'll store them as a JSON string in 'access_token' field of the connection.
    try:
        import json
        data = json.loads(creds["access_token"])
        client_id = data.get("client_id")
        client_secret = data.get("client_secret")
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to parse stored credentials.")

    if not client_id or not client_secret:
        raise HTTPException(status_code=500, detail="Incomplete credentials in database.")

    # 2. Exchange code for Bot Token
    response = requests.post(
        SLACK_TOKEN_URL,
        data={
            "client_id": client_id,
            "client_secret": client_secret,
            "code": code
        },
        timeout=10
    )
    
    res_data = response.json()
    if not res_data.get("ok"):
        return HTMLResponse(content=f"<h2>Handshake Failed</h2><p>Slack Error: {res_data.get('error')}</p>", status_code=400)

    # 3. Save the Bot Token
    # We store it in 'slack_bot:{agent_id}'
    bot_token = res_data.get("access_token")
    user_connections_store.upsert_connection(
        service=f"slack_bot:{agent_id}",
        access_token=bot_token,
        username=res_data.get("bot_user_id"),
        scopes=res_data.get("scope")
    )

    # 4. Capture the installer/owner ID if present
    authed_user_id = res_data.get("authed_user", {}).get("id")
    if authed_user_id:
        user_connections_store.upsert_connection(
            service="slack_owner",
            access_token=authed_user_id
        )

    # Note: For HTTP mode, we don't strictly need the xapp- token.
    # If the user is in Choice B (HTTP Mode), we are done here!
    
    return HTMLResponse(content=f"""
        <div style="background: #131313; color: #ffb3b5; font-family: sans-serif; height: 100vh; display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center;">
            <h1 style="font-size: 3rem; margin-bottom: 10px;">Agent Secured</h1>
            <p style="font-size: 1.2rem; opacity: 0.8;">{agent_id.capitalize()}'s spirit has been manifested in the Famiglia.</p>
            <div style="margin-top: 30px; font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.2em; opacity: 0.5;">You can close this tab now.</div>
        </div>
    """)
