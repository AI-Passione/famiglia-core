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
        """Load Command Center settings from the dedicated user_settings table."""
        try:
            with context_store.db_session(commit=False) as cursor:
                if cursor is None:
                    return DEFAULT_SETTINGS.copy()
                cursor.execute(
                    """
                    SELECT
                        us.honorific,
                        us.notifications_enabled,
                        us.background_animations_enabled
                    FROM user_settings us
                    JOIN users u ON u.id = us.user_id
                    WHERE u.role = 'don'
                    LIMIT 1;
                    """
                )
                row = cursor.fetchone()
                if not row:
                    return DEFAULT_SETTINGS.copy()

                return {
                    "honorific": row.get("honorific") or DEFAULT_SETTINGS["honorific"],
                    "notificationsEnabled": row.get("notifications_enabled")
                    if row.get("notifications_enabled") is not None
                    else DEFAULT_SETTINGS["notificationsEnabled"],
                    "backgroundAnimationsEnabled": row.get("background_animations_enabled")
                    if row.get("background_animations_enabled") is not None
                    else DEFAULT_SETTINGS["backgroundAnimationsEnabled"],
                }
        except Exception as e:
            print(f"[UserService] Error loading Don settings: {e}")
            return DEFAULT_SETTINGS.copy()

    def update_don_settings(self, settings: Dict[str, Any]) -> Dict[str, Any]:
        """Persist Command Center settings into the dedicated user_settings table."""
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
                    SELECT id
                    FROM users
                    WHERE role = 'don'
                    LIMIT 1;
                    """
                )
                don_row = cursor.fetchone()
                if not don_row:
                    cursor.execute(
                        """
                        INSERT INTO users (full_name, username, role)
                        VALUES (%s, %s, 'don')
                        ON CONFLICT (username) DO UPDATE
                        SET updated_at = NOW()
                        RETURNING id;
                        """,
                        ("Don Jimmy", "don_jimmy"),
                    )
                    don_row = cursor.fetchone()

                if not don_row:
                    return normalized_settings

                don_user_id = don_row["id"]
                cursor.execute(
                    """
                    INSERT INTO user_settings (
                        user_id,
                        honorific,
                        notifications_enabled,
                        background_animations_enabled,
                        updated_at
                    )
                    VALUES (%s, %s, %s, %s, NOW())
                    ON CONFLICT (user_id) DO UPDATE
                    SET
                      honorific = EXCLUDED.honorific,
                      notifications_enabled = EXCLUDED.notifications_enabled,
                      background_animations_enabled = EXCLUDED.background_animations_enabled,
                      updated_at = NOW()
                    RETURNING id;
                    """,
                    (
                        don_user_id,
                        normalized_settings["honorific"],
                        normalized_settings["notificationsEnabled"],
                        normalized_settings["backgroundAnimationsEnabled"],
                    ),
                )
                return normalized_settings
        except Exception as e:
            print(f"[UserService] Error updating Don settings: {e}")
            return normalized_settings

user_service = UserService()
