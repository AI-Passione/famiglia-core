import os
import json
from datetime import datetime, timezone
from famiglia_core.db.agents.context_store import context_store

def seed_don():
    # Use the USER_SLACK_ID from environment if available, otherwise a placeholder
    user_slack_id = os.getenv("USER_SLACK_ID", "U0AG886GJCV")
    don_username = "don_jimmy"
    don_full_name = "Don Jimmy"
    
    print(f"Seeding '{don_full_name}' with Slack ID '{user_slack_id}'...")
    
    try:
        with context_store.db_session() as cursor:
            if cursor is None:
                print("Error: Context store is not enabled or connection failed.")
                return
            
            # 1. Insert/Update the Don in the users table
            cursor.execute(
                """
                INSERT INTO users (full_name, username, role, metadata)
                VALUES (%s, %s, 'don', %s)
                ON CONFLICT (username) DO UPDATE SET
                    full_name = EXCLUDED.full_name,
                    updated_at = NOW()
                RETURNING id;
                """,
                (don_full_name, don_username, json.dumps({"is_primary": True}))
            )
            row = cursor.fetchone()
            if not row:
                print("Failed to insert/update Don.")
                return
            user_id = row['id']
            
            # 2. Insert/Update Slack identity
            cursor.execute(
                """
                INSERT INTO user_platform_identities (user_id, platform, platform_user_id)
                VALUES (%s, 'slack', %s)
                ON CONFLICT (platform, platform_user_id) DO UPDATE SET
                    updated_at = NOW()
                RETURNING id;
                """,
                (user_id, user_slack_id)
            )
            print(f"Successfully seeded Don Jimmy (User ID: {user_id})")
            
    except Exception as e:
        print(f"Error during seeding: {e}")

if __name__ == "__main__":
    seed_don()
