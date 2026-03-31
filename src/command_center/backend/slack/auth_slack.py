"""
auth_slack.py
Slack OAuth 2.0 client for the Command Center user connection flow.
Handles: authorization URL generation, code exchange, and user profile retrieval.
"""
import os
import requests
from typing import Dict, Any, Optional

SLACK_AUTHORIZE_URL = "https://slack.com/oauth/v2/authorize"
SLACK_TOKEN_URL = "https://slack.com/api/oauth.v2.access"
SLACK_USER_PROFILE_URL = "https://slack.com/api/users.profile.get"

# We request user-level scopes to act or read on behalf of the user.
# identify: basic identity
# users.profile:read: to get the display name and avatar
DEFAULT_USER_SCOPES = "identify,users.profile:read"


class SlackOAuthClient:
    """Handles the Slack OAuth 2.0 flow for human user connections."""

    def __init__(self):
        self.client_id = os.getenv("SLACK_OAUTH_CLIENT_ID", "")
        self.client_secret = os.getenv("SLACK_OAUTH_CLIENT_SECRET", "")
        
        # This must match the redirect URI configured in the Slack App settings
        self.redirect_uri = os.getenv(
            "SLACK_OAUTH_REDIRECT_URI",
            "http://localhost:8000/auth/slack/callback",
        )

    def is_configured(self) -> bool:
        """Check whether the required OAuth credentials are present in the environment."""
        return bool(self.client_id and self.client_secret)

    def get_authorization_url(self, state: Optional[str] = None) -> str:
        """Build the Slack authorization URL to redirect the user to."""
        if not self.is_configured():
            raise ValueError(
                "Slack OAuth is not configured. "
                "Set SLACK_OAUTH_CLIENT_ID and SLACK_OAUTH_CLIENT_SECRET in your .env file."
            )
        
        # Slack v2 OAuth uses 'user_scope' for user-level tokens (xoxp-)
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "user_scope": DEFAULT_USER_SCOPES,
        }
        if state:
            params["state"] = state

        query = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{SLACK_AUTHORIZE_URL}?{query}"

    def exchange_code_for_token(self, code: str) -> Dict[str, Any]:
        """
        Exchange the OAuth authorization code for an access token.
        Returns the full Slack response dict.
        """
        if not self.is_configured():
            raise ValueError("Slack OAuth is not configured.")

        response = requests.post(
            SLACK_TOKEN_URL,
            data={
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "code": code,
                "redirect_uri": self.redirect_uri,
            },
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()

        if not data.get("ok"):
            raise ValueError(
                f"Slack OAuth token exchange failed: {data.get('error', 'unknown_error')}"
            )
            
        # For user connections, we look into the 'authed_user' field
        if "authed_user" not in data or "access_token" not in data["authed_user"]:
            raise ValueError(f"Slack OAuth: unexpected response — no user access_token in: {data}")

        return data

    def get_user_info(self, user_token: str) -> Dict[str, Any]:
        """
        Fetch the authenticated Slack user's profile.
        Returns a dict with at least: display_name, real_name, image_512.
        """
        response = requests.get(
            SLACK_USER_PROFILE_URL,
            headers={
                "Authorization": f"Bearer {user_token}",
            },
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()
        
        if not data.get("ok"):
             raise ValueError(f"Slack profile fetch failed: {data.get('error')}")
             
        return data.get("profile", {})


# Singleton
slack_oauth_client = SlackOAuthClient()
