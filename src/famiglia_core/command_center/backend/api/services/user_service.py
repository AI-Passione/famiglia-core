from typing import Optional, Dict, Any
from famiglia_core.db.agents.context_store import context_store

import os

DEFAULT_SOULS_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "agents", "souls", "souls.md")

def get_shared_baseline_from_souls():
    try:
        if not os.path.exists(DEFAULT_SOULS_PATH):
            return ""
        with open(DEFAULT_SOULS_PATH, "r") as f:
            content = f.read()
            if "## Shared Baseline (All Agents)" in content:
                baseline = content.split("## Shared Baseline (All Agents)")[1].split("##")[0].strip()
                return baseline
            return content.strip()
    except Exception as e:
        print(f"[UserService] Error reading souls.md: {e}")
        return ""

DEFAULT_SETTINGS = {
    "honorific": "Don",
    "famigliaName": "The Family",
    "notificationsEnabled": True,
    "backgroundAnimationsEnabled": True,
    "personalDirective": "",
    "systemPrompt": get_shared_baseline_from_souls(),
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
                    return {**DEFAULT_SETTINGS.copy(), "fullName": "Don Jimmy"}
                cursor.execute(
                    """
                    SELECT
                        u.full_name,
                        us.honorific,
                        us.famiglia_name,
                        us.notifications_enabled,
                        us.background_animations_enabled,
                        us.personal_directive,
                        us.system_prompt
                    FROM user_settings us
                    JOIN users u ON u.id = us.user_id
                    WHERE u.role = 'don'
                    LIMIT 1;
                    """
                )
                row = cursor.fetchone()
                if not row:
                    # Fallback to just the user if settings haven't been created yet
                    don = self.get_don()
                    return {
                        **DEFAULT_SETTINGS.copy(),
                        "fullName": don.get("full_name") if don else "Don Jimmy"
                    }

                return {
                    "fullName": row.get("full_name") or "Don Jimmy",
                    "honorific": row.get("honorific") or DEFAULT_SETTINGS["honorific"],
                    "famigliaName": row.get("famiglia_name") or DEFAULT_SETTINGS["famigliaName"],
                    "notificationsEnabled": row.get("notifications_enabled")
                    if row.get("notifications_enabled") is not None
                    else DEFAULT_SETTINGS["notificationsEnabled"],
                    "backgroundAnimationsEnabled": row.get("background_animations_enabled")
                    if row.get("background_animations_enabled") is not None
                    else DEFAULT_SETTINGS["backgroundAnimationsEnabled"],
                    "personalDirective": row.get("personal_directive") or DEFAULT_SETTINGS["personalDirective"],
                    "systemPrompt": row.get("system_prompt") or DEFAULT_SETTINGS["systemPrompt"],
                }
        except Exception as e:
            print(f"[UserService] Error loading Don settings: {e}")
            return {**DEFAULT_SETTINGS.copy(), "fullName": "Don Jimmy"}

    def update_don_settings(self, settings: Dict[str, Any]) -> Dict[str, Any]:
        """Persist Command Center settings into the dedicated user_settings table."""
        normalized_settings = {
            "fullName": settings.get("fullName", "Don Jimmy"),
            "honorific": settings.get("honorific", DEFAULT_SETTINGS["honorific"]),
            "famigliaName": settings.get("famigliaName", DEFAULT_SETTINGS["famigliaName"]),
            "notificationsEnabled": settings.get("notificationsEnabled", DEFAULT_SETTINGS["notificationsEnabled"]),
            "backgroundAnimationsEnabled": settings.get("backgroundAnimationsEnabled", DEFAULT_SETTINGS["backgroundAnimationsEnabled"]),
            "personalDirective": settings.get("personalDirective", DEFAULT_SETTINGS["personalDirective"]),
            "systemPrompt": settings.get("systemPrompt", DEFAULT_SETTINGS["systemPrompt"]),
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
                        SET full_name = EXCLUDED.full_name, updated_at = NOW()
                        RETURNING id;
                        """,
                        (normalized_settings["fullName"], "don_jimmy"),
                    )
                    don_row = cursor.fetchone()
                else:
                    # Update existing user profile name
                    cursor.execute(
                        "UPDATE users SET full_name = %s, updated_at = NOW() WHERE id = %s",
                        (normalized_settings["fullName"], don_row["id"])
                    )

                if not don_row:
                    return normalized_settings

                don_user_id = don_row["id"]
                cursor.execute(
                    """
                    INSERT INTO user_settings (
                        user_id,
                        honorific,
                        famiglia_name,
                        notifications_enabled,
                        background_animations_enabled,
                        personal_directive,
                        system_prompt,
                        updated_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
                    ON CONFLICT (user_id) DO UPDATE
                    SET
                      honorific = EXCLUDED.honorific,
                      famiglia_name = EXCLUDED.famiglia_name,
                      notifications_enabled = EXCLUDED.notifications_enabled,
                      background_animations_enabled = EXCLUDED.background_animations_enabled,
                      personal_directive = EXCLUDED.personal_directive,
                      system_prompt = EXCLUDED.system_prompt,
                      updated_at = NOW()
                    RETURNING id;
                    """,
                    (
                        don_user_id,
                        normalized_settings["honorific"],
                        normalized_settings["famigliaName"],
                        normalized_settings["notificationsEnabled"],
                        normalized_settings["backgroundAnimationsEnabled"],
                        normalized_settings["personalDirective"],
                        normalized_settings["systemPrompt"],
                    ),
                )
                return normalized_settings
        except Exception as e:
            print(f"[UserService] Error updating Don settings: {e}")
            return normalized_settings

user_service = UserService()
