from famiglia_core.agents.riccado import Riccado
from famiglia_core.db.init_db import init_db
from famiglia_core.db.github_store import github_store

def verify():
    print("Testing Riccado's GitHub capabilities locally...")
    riccado = Riccado()
    
    # 1. Test Read Repo
    print("\n--- Testing read_github_repo ---")
    response1 = riccado.read_github_repo("852-Lab/jimwurst")
    print(f"Riccado: {response1}")
    
    # 2. Test Manage Issue (List)
    print("\n--- Testing manage_github_issue (list) ---")
    response2 = riccado.manage_github_issue("852-Lab/jimwurst", action="list")
    print(f"Riccado: {response2}")
    
    # 3. Check DB logs
    print("\n--- Checking DB Logs ---")
    try:
        with github_store._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT action_type, repo_name FROM github_interactions ORDER BY created_at DESC LIMIT 2;")
                rows = cur.fetchall()
                print(f"Latest GitHub Interactions in DB: {rows}")
    except Exception as e:
        print(f"Could not read DB: {e}")

if __name__ == "__main__":
    verify()
