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
        app_id: Optional[str] = None,
        refresh_token: Optional[str] = None,
    ) -> bool:
        """Encrypt and persist (or update) an OAuth connection for a service."""
        try:
            fernet = _get_fernet()
            encrypted_token = fernet.encrypt(access_token.encode()).decode()
            encrypted_refresh = fernet.encrypt(refresh_token.encode()).decode() if refresh_token else None

            with context_store.db_session() as cursor:
                if cursor is None:
                    return False
                cursor.execute(
                    """
                    INSERT INTO user_connections
                        (service, username, avatar_url, access_token, scopes, app_id, refresh_token, connected_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
                    ON CONFLICT (service) DO UPDATE SET
                        username     = EXCLUDED.username,
                        avatar_url   = EXCLUDED.avatar_url,
                        access_token = EXCLUDED.access_token,
                        scopes       = EXCLUDED.scopes,
                        app_id       = COALESCE(EXCLUDED.app_id, user_connections.app_id),
                        refresh_token = COALESCE(EXCLUDED.refresh_token, user_connections.refresh_token),
                        updated_at   = NOW();
                    """,
                    (service, username, avatar_url, encrypted_token, scopes, app_id, encrypted_refresh),
                )
            print(f"[UserConnectionsStore] Upserted connection for service='{service}' user='{username}' app_id='{app_id}'")
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
                    SELECT service, username, avatar_url, access_token, scopes, app_id, refresh_token, connected_at, updated_at
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

            decrypted_refresh = None
            if row.get("refresh_token"):
                try:
                    decrypted_refresh = fernet.decrypt(row["refresh_token"].encode()).decode()
                except Exception:
                    pass

            return {
                "service": row["service"],
                "username": row["username"],
                "avatar_url": row["avatar_url"],
                "access_token": decrypted_token,
                "refresh_token": decrypted_refresh,
                "scopes": row["scopes"],
                "app_id": row["app_id"],
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
                    SELECT username, avatar_url, scopes, app_id, refresh_token, connected_at
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
                "app_id": row["app_id"],
                "rotatable": bool(row.get("refresh_token")),
                "connected_at": row["connected_at"].isoformat() if row["connected_at"] else None,
            }
        except Exception as e:
            print(f"[UserConnectionsStore] Error retrieving status for '{service}': {e}")
            return {"connected": False}

    def list_connections(self, service_prefix: str) -> Dict[str, Dict[str, Any]]:
        """Retrieve all connections starting with a specific prefix (e.g. 'slack:')."""
        try:
            with context_store.db_session(commit=False) as cursor:
                if cursor is None:
                    return {}
                cursor.execute(
                    """
                    SELECT service, username, avatar_url, access_token, scopes, app_id, refresh_token, connected_at
                    FROM user_connections
                    WHERE service LIKE %s;
                    """,
                    (f"{service_prefix}%",),
                )
                rows = cursor.fetchall()

            fernet = _get_fernet()
            results = {}
            for row in rows:
                try:
                    decrypted_token = fernet.decrypt(row["access_token"].encode()).decode()
                    decrypted_refresh = None
                    if row.get("refresh_token"):
                         try:
                             decrypted_refresh = fernet.decrypt(row["refresh_token"].encode()).decode()
                         except Exception:
                             pass
                             
                    results[row["service"]] = {
                        "username": row["username"],
                        "avatar_url": row["avatar_url"],
                        "access_token": decrypted_token,
                        "refresh_token": decrypted_refresh,
                        "scopes": row["scopes"],
                        "app_id": row["app_id"],
                        "connected_at": row["connected_at"].isoformat() if row["connected_at"] else None,
                    }
                except Exception:
                    continue
            return results
        except Exception as e:
            print(f"[UserConnectionsStore] Error listing connections for '{service_prefix}': {e}")
            return {}

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

    def delete_connections_by_prefix(self, prefix: str) -> bool:
        """Remove all connections starting with a prefix."""
        try:
            with context_store.db_session() as cursor:
                if cursor is None:
                    return False
                cursor.execute(
                    "DELETE FROM user_connections WHERE service LIKE %s;",
                    (f"{prefix}%",),
                )
            print(f"[UserConnectionsStore] Deleted connections with prefix='{prefix}%'")
            return True
        except Exception as e:
            print(f"[UserConnectionsStore] Error deleting connections for prefix '{prefix}': {e}")
            return False


# Singleton
user_connections_store = UserConnectionsStore()
