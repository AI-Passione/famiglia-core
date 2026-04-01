import json
from typing import Optional, Dict, Any
from famiglia_core.db.agents.context_store import context_store

DEFAULT_SETTINGS = {
    "honorific": "Don",
    "notificationsEnabled": True,
    "backgroundAnimationsEnabled": True,
}

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

    def get_don_settings(self) -> Dict[str, Any]:
        """Load Command Center settings from the Don's user metadata JSONB."""
        try:
            with context_store.db_session(commit=False) as cursor:
                if cursor is None:
                    return DEFAULT_SETTINGS.copy()
                cursor.execute(
                    """
                    SELECT metadata
                    FROM users
                    WHERE role = 'don'
                    LIMIT 1;
                    """
                )
                row = cursor.fetchone()
                if not row:
                    return DEFAULT_SETTINGS.copy()

                metadata = row.get("metadata") or {}
                command_center_settings = metadata.get("command_center_settings") or {}
                return {
                    "honorific": command_center_settings.get(
                        "honorific", DEFAULT_SETTINGS["honorific"]
                    ),
                    "notificationsEnabled": command_center_settings.get(
                        "notificationsEnabled",
                        DEFAULT_SETTINGS["notificationsEnabled"],
                    ),
                    "backgroundAnimationsEnabled": command_center_settings.get(
                        "backgroundAnimationsEnabled",
                        DEFAULT_SETTINGS["backgroundAnimationsEnabled"],
                    ),
                }
        except Exception as e:
            print(f"[UserService] Error loading Don settings: {e}")
            return DEFAULT_SETTINGS.copy()

    def update_don_settings(self, settings: Dict[str, Any]) -> Dict[str, Any]:
        """Persist Command Center settings into the Don's user metadata JSONB."""
        normalized_settings = {
            "honorific": settings.get("honorific", DEFAULT_SETTINGS["honorific"]),
            "notificationsEnabled": settings.get(
                "notificationsEnabled", DEFAULT_SETTINGS["notificationsEnabled"]
            ),
            "backgroundAnimationsEnabled": settings.get(
                "backgroundAnimationsEnabled",
                DEFAULT_SETTINGS["backgroundAnimationsEnabled"],
            ),
        }
        try:
            with context_store.db_session() as cursor:
                if cursor is None:
                    return normalized_settings

                cursor.execute(
                    """
                    UPDATE users
                    SET
                      metadata = COALESCE(metadata, '{}'::jsonb) ||
                                 jsonb_build_object('command_center_settings', %s::jsonb),
                      updated_at = NOW()
                    WHERE id = (
                      SELECT id FROM users WHERE role = 'don' LIMIT 1
                    )
                    RETURNING id;
                    """,
                    (json.dumps(normalized_settings),),
                )
                updated_row = cursor.fetchone()

                if not updated_row:
                    # Create a default Don user if missing, then persist settings.
                    cursor.execute(
                        """
                        INSERT INTO users (full_name, username, role, metadata)
                        VALUES (%s, %s, 'don', %s::jsonb)
                        ON CONFLICT (username) DO UPDATE
                        SET metadata = EXCLUDED.metadata, updated_at = NOW();
                        """,
                        (
                            "Don Jimmy",
                            "don_jimmy",
                            json.dumps(
                                {"command_center_settings": normalized_settings}
                            ),
                        ),
                    )

                return normalized_settings
        except Exception as e:
            print(f"[UserService] Error updating Don settings: {e}")
            return normalized_settings

user_service = UserService()
