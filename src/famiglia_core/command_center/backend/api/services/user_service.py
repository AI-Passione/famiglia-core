from typing import Optional, Dict, Any
from famiglia_core.db.agents.context_store import context_store

class UserService:
    """Service for managing centralized user identities across platforms."""

    def get_user_by_platform_id(self, platform: str, platform_user_id: str) -> Optional[Dict[str, Any]]:
        """Resolve a central user by their platform-specific ID."""
        try:
            with context_store.db_session(commit=False) as cursor:
                if cursor is None: return None
                cursor.execute(
                    """
                    SELECT u.* 
                    FROM users u
                    JOIN user_platform_identities upi ON upi.user_id = u.id
                    WHERE upi.platform = %s AND upi.platform_user_id = %s;
                    """,
                    (platform, platform_user_id)
                )
                return cursor.fetchone()
        except Exception as e:
            print(f"[UserService] Error fetching user by platform ID: {e}")
            return None

    def get_don(self) -> Optional[Dict[str, Any]]:
        """Get the primary 'Don' user profile."""
        try:
            with context_store.db_session(commit=False) as cursor:
                if cursor is None: return None
                cursor.execute("SELECT * FROM users WHERE role = 'don' LIMIT 1;")
                return cursor.fetchone()
        except Exception as e:
            print(f"[UserService] Error fetching Don: {e}")
            return None

    def ensure_user_platform_identity(self, user_id: int, platform: str, platform_user_id: str):
        """Ensure a platform identity exists for a central user."""
        try:
            with context_store.db_session() as cursor:
                if cursor is None: return
                cursor.execute(
                    """
                    INSERT INTO user_platform_identities (user_id, platform, platform_user_id)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (platform, platform_user_id) DO NOTHING;
                    """,
                    (user_id, platform, platform_user_id)
                )
        except Exception as e:
            print(f"[UserService] Error ensuring identity: {e}")

user_service = UserService()
