"""
auth_notion.py
Notion OAuth 2.0 client for the Command Center user connection flow.
Handles: authorization URL generation, code exchange, and workspace info retrieval.
"""
import os
import requests
import base64
from typing import Dict, Any, Optional

NOTION_AUTHORIZE_URL = "https://api.notion.com/v1/oauth/authorize"
NOTION_TOKEN_URL = "https://api.notion.com/v1/oauth/token"


class NotionOAuthClient:
    """Handles the Notion OAuth 2.0 flow for human user connections."""

    def __init__(self):
        self.client_id = os.getenv("NOTION_OAUTH_CLIENT_ID", "")
        self.client_secret = os.getenv("NOTION_OAUTH_CLIENT_SECRET", "")
        self.redirect_uri = os.getenv(
            "NOTION_OAUTH_REDIRECT_URI",
            "http://localhost:8000/auth/notion/callback",
        )

    def is_configured(self) -> bool:
        """Check whether the required OAuth credentials are present in the environment."""
        return bool(self.client_id and self.client_secret)

    def get_authorization_url(self, state: Optional[str] = None) -> str:
        """Build the Notion authorization URL to redirect the user to."""
        if not self.is_configured():
            raise ValueError(
                "Notion OAuth is not configured. "
                "Set NOTION_OAUTH_CLIENT_ID and NOTION_OAUTH_CLIENT_SECRET in your .env file."
            )
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "owner": "user",
        }
        if state:
            params["state"] = state

        query = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{NOTION_AUTHORIZE_URL}?{query}"

    def exchange_code_for_token(self, code: str) -> Dict[str, Any]:
        """
        Exchange the OAuth authorization code for an access token.
        Returns the full Notion response dict.
        """
        if not self.is_configured():
            raise ValueError("Notion OAuth is not configured.")

        # Notion requires Basic Auth for the token request
        auth_str = f"{self.client_id}:{self.client_secret}"
        encoded_auth = base64.b64encode(auth_str.encode()).decode()

        response = requests.post(
            NOTION_TOKEN_URL,
            headers={
                "Authorization": f"Basic {encoded_auth}",
                "Content-Type": "application/json",
            },
            json={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": self.redirect_uri,
            },
            timeout=10,
        )
        
        if not response.ok:
            try:
                err_data = response.json()
                error_msg = err_data.get("error_description") or err_data.get("error") or response.text
            except:
                error_msg = response.text
            raise ValueError(f"Notion OAuth token exchange failed: {error_msg}")

        data = response.json()
        if "access_token" not in data:
            raise ValueError(f"Notion OAuth: unexpected response — no access_token in: {data}")

        return data


# Singleton
notion_oauth_client = NotionOAuthClient()
