"""
auth_github.py
GitHub OAuth 2.0 client for the Command Center user connection flow.
Handles: authorization URL generation, code exchange, and user info retrieval.
"""
import os
import requests
from typing import Dict, Any, Optional


GITHUB_AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_USER_URL = "https://api.github.com/user"

# Default scopes: read user profile + read repository access (no write by default)
DEFAULT_SCOPES = "read:user,repo"


class GitHubOAuthClient:
    """Handles the GitHub OAuth 2.0 flow for human user connections."""

    def __init__(self):
        self.client_id = os.getenv("GITHUB_OAUTH_CLIENT_ID", "")
        self.client_secret = os.getenv("GITHUB_OAUTH_CLIENT_SECRET", "")
        
        self.redirect_uri = os.getenv(
            "GITHUB_OAUTH_REDIRECT_URI",
            "http://localhost:8000/auth/github/callback",
        )

    def is_configured(self) -> bool:
        """Check whether the required OAuth credentials are present in the environment."""
        return bool(self.client_id and self.client_secret)

    def get_authorization_url(self, state: Optional[str] = None) -> str:
        """Build the GitHub authorization URL to redirect the user to."""
        if not self.is_configured():
            raise ValueError(
                "GitHub OAuth is not configured. "
                "Set GITHUB_OAUTH_CLIENT_ID and GITHUB_OAUTH_CLIENT_SECRET in your .env file."
            )
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": DEFAULT_SCOPES,
        }
        if state:
            params["state"] = state

        query = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{GITHUB_AUTHORIZE_URL}?{query}"

    def exchange_code_for_token(self, code: str) -> Dict[str, Any]:
        """
        Exchange the OAuth authorization code for an access token.
        Returns the full GitHub response dict, including 'access_token' and 'scope'.
        """
        if not self.is_configured():
            raise ValueError("GitHub OAuth is not configured.")

        response = requests.post(
            GITHUB_TOKEN_URL,
            headers={"Accept": "application/json"},
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

        if "error" in data:
            raise ValueError(
                f"GitHub OAuth token exchange failed: {data.get('error_description', data['error'])}"
            )
        if "access_token" not in data:
            raise ValueError(f"GitHub OAuth: unexpected response — no access_token in: {data}")

        return data

    def get_user_info(self, access_token: str) -> Dict[str, Any]:
        """
        Fetch the authenticated GitHub user's profile.
        Returns a dict with at least: login, avatar_url, name, email, html_url.
        """
        response = requests.get(
            GITHUB_USER_URL,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/vnd.github.v3+json",
            },
            timeout=10,
        )
        response.raise_for_status()
        return response.json()


# Singleton
github_oauth_client = GitHubOAuthClient()
