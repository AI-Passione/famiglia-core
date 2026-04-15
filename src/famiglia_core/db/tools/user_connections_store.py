"""
user_connections_store.py
Persists OAuth tokens for human-facing service connections (GitHub, Google, etc.).
Tokens are Fernet-encrypted before storage and decrypted on retrieval.
"""
import os
import json
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from famiglia_core.db.agents.context_store import context_store


_SECRETS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "secrets")
_FERNET_KEY_FILE = os.path.join(_SECRETS_DIR, "fernet.key")


def _get_fernet():
    """
    Load or generate the Fernet encryption key.

    Priority:
      1. FERNET_SECRET env var (production / CI override)
      2. secrets/fernet.key local file (auto-created on first run)
    """
    from cryptography.fernet import Fernet

    # 1. Env var override (production / Docker / CI)
    secret = os.getenv("FERNET_SECRET")
    if secret:
        return Fernet(secret.encode() if isinstance(secret, str) else secret)

    # 2. Persistent local key file
    key_path = os.path.abspath(_FERNET_KEY_FILE)
    if os.path.exists(key_path):
        with open(key_path, "r") as f:
            secret = f.read().strip()
    else:
        secret = Fernet.generate_key().decode()
        os.makedirs(os.path.dirname(key_path), exist_ok=True)
        with open(key_path, "w") as f:
            f.write(secret)
        print(
            f"[UserConnectionsStore] Generated new Fernet key → {key_path}\n"
            "  Back this file up — losing it means stored credentials cannot be decrypted."
        )

    return Fernet(secret.encode())


class UserConnectionsStore:
    """Store and retrieve encrypted OAuth connections for the dashboard owner."""

    # ------------------------------------------------------------------ #
    #  Write                                                                #
    # ------------------------------------------------------------------ #

    def upsert_connection(
        self,
        service: str,
        access_token: str,
        username: Optional[str] = None,
        avatar_url: Optional[str] = None,
        scopes: Optional[str] = None,
    ) -> bool:
        """Encrypt and persist (or update) an OAuth connection for a service."""
        try:
            fernet = _get_fernet()
            encrypted_token = fernet.encrypt(access_token.encode()).decode()

            with context_store.db_session() as cursor:
                if cursor is None:
                    return False
                cursor.execute(
                    """
                    INSERT INTO user_connections
                        (service, username, avatar_url, access_token, scopes, connected_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, NOW(), NOW())
                    ON CONFLICT (service) DO UPDATE SET
                        username     = EXCLUDED.username,
                        avatar_url   = EXCLUDED.avatar_url,
                        access_token = EXCLUDED.access_token,
                        scopes       = EXCLUDED.scopes,
                        updated_at   = NOW();
                    """,
                    (service, username, avatar_url, encrypted_token, scopes),
                )
            print(f"[UserConnectionsStore] Upserted connection for service='{service}' user='{username}'")
            return True
        except Exception as e:
            print(f"[UserConnectionsStore] Error upserting connection for '{service}': {e}")
            return False

    # ------------------------------------------------------------------ #
    #  Read                                                                 #
    # ------------------------------------------------------------------ #

    def get_connection(self, service: str) -> Optional[Dict[str, Any]]:
        """Retrieve a connection, decrypting the token. Returns None if not found."""
        try:
            with context_store.db_session(commit=False) as cursor:
                if cursor is None:
                    return None
                cursor.execute(
                    """
                    SELECT service, username, avatar_url, access_token, scopes, connected_at, updated_at
                    FROM user_connections
                    WHERE service = %s;
                    """,
                    (service,),
                )
                row = cursor.fetchone()

            if not row:
                return None

            fernet = _get_fernet()
            try:
                decrypted_token = fernet.decrypt(row["access_token"].encode()).decode()
            except Exception:
                print(f"[UserConnectionsStore] Failed to decrypt token for '{service}' — token may be stale.")
                return None

            return {
                "service": row["service"],
                "username": row["username"],
                "avatar_url": row["avatar_url"],
                "access_token": decrypted_token,
                "scopes": row["scopes"],
                "connected_at": row["connected_at"].isoformat() if row["connected_at"] else None,
                "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
            }
        except Exception as e:
            print(f"[UserConnectionsStore] Error retrieving connection for '{service}': {e}")
            return None

    def get_connection_status(self, service: str) -> Dict[str, Any]:
        """Return a safe (no token) status dict for the frontend."""
        try:
            with context_store.db_session(commit=False) as cursor:
                if cursor is None:
                    return {"connected": False}
                cursor.execute(
                    """
                    SELECT username, avatar_url, scopes, connected_at
                    FROM user_connections
                    WHERE service = %s;
                    """,
                    (service,),
                )
                row = cursor.fetchone()

            if not row:
                return {"connected": False}

            return {
                "connected": True,
                "username": row["username"],
                "avatar_url": row["avatar_url"],
                "scopes": row["scopes"],
                "connected_at": row["connected_at"].isoformat() if row["connected_at"] else None,
            }
        except Exception as e:
            print(f"[UserConnectionsStore] Error retrieving status for '{service}': {e}")
            return {"connected": False}

    # ------------------------------------------------------------------ #
    #  Delete                                                               #
    # ------------------------------------------------------------------ #

    def delete_connection(self, service: str) -> bool:
        """Remove the stored connection for a service."""
        try:
            with context_store.db_session() as cursor:
                if cursor is None:
                    return False
                cursor.execute(
                    "DELETE FROM user_connections WHERE service = %s;",
                    (service,),
                )
            print(f"[UserConnectionsStore] Deleted connection for service='{service}'")
            return True
        except Exception as e:
            print(f"[UserConnectionsStore] Error deleting connection for '{service}': {e}")
            return False


# Singleton
user_connections_store = UserConnectionsStore()
