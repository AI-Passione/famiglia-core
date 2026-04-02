import os
import sys

# Ensure project root is in path for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../../")))

from famiglia_core.db.agents.context_store import context_store

def migrate_metadata():
    """Migrate legacy 'sop_execution' task_type to 'operations_execution'."""
    print("[Migration] Starting SOP to Operations metadata migration...")
    try:
        with context_store.db_session(commit=True) as cursor:
            if cursor is None:
                print("[Migration] Error: Database session unavailable.")
                return
                
            # Update task_instances metadata
            # We use the || operator for jsonb to update the task_type key
            query = """
                UPDATE task_instances 
                SET metadata = metadata || '{"task_type": "operations_execution"}'::jsonb 
                WHERE metadata->>'task_type' = 'sop_execution';
            """
            cursor.execute(query)
            affected_rows = cursor.rowcount
            print(f"[Migration] Successfully updated {affected_rows} legacy task instances.")
            
    except Exception as e:
        print(f"[Migration] Critical error during database update: {e}")

if __name__ == "__main__":
    migrate_metadata()
