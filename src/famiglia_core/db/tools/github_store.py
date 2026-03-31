import json
from typing import Dict, Any, Optional, List
from famiglia_core.db.agents.context_store import context_store

class GithubStore:
    def log_github_action(
        self,
        agent_name: str,
        action_type: str,
        repo_name: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> int:
        """Logs a GitHub interaction to the database."""
        try:
            with context_store.db_session() as cursor:
                if cursor is None: return -1
                
                metadata_json = json.dumps(metadata) if metadata else None
                cursor.execute("""
                    INSERT INTO github_interactions (agent_name, action_type, repo_name, metadata)
                    VALUES (%s, %s, %s, %s)
                    RETURNING id;
                """, (agent_name, action_type, repo_name, metadata_json))
                
                row = cursor.fetchone()
                return row["id"] if row else -1
        except Exception as e:
            print(f"[GithubStore] Error logging github action: {e}")
            return -1

    def upsert_github_repo_access(self, agent_name: str, repo_name: str, permissions: Optional[Dict[str, Any]] = None) -> bool:
        """Stores or updates repository access for an agent."""
        try:
            with context_store.db_session() as cursor:
                if cursor is None: return False
                
                permissions_json = json.dumps(permissions) if permissions else None
                cursor.execute("""
                    INSERT INTO agent_github_repos (agent_name, repo_name, permissions, updated_at)
                    VALUES (%s, %s, %s, NOW())
                    ON CONFLICT (agent_name, repo_name)
                    DO UPDATE SET
                        permissions = EXCLUDED.permissions,
                        updated_at = NOW();
                """, (agent_name, repo_name, permissions_json))
                return True
        except Exception as e:
            print(f"[GithubStore] Error upserting github repo access: {e}")
            return False

    def get_accessible_repos(self, agent_name: str) -> List[Dict[str, Any]]:
        """Retrieves known cached accessible repositories for an agent."""
        try:
            with context_store.db_session(commit=False) as cursor:
                if cursor is None: return []
                
                cursor.execute("""
                    SELECT repo_name, permissions, updated_at
                    FROM agent_github_repos
                    WHERE agent_name = %s
                    ORDER BY repo_name ASC;
                """, (agent_name,))
                return list(cursor.fetchall())
        except Exception as e:
            print(f"[GithubStore] Error retrieving accessible repos: {e}")
            return []

    def upsert_prd_repo_mapping(self, 
                                notion_page_id: str, 
                                repo_name: str, 
                                github_repo_id: Optional[int] = None, 
                                github_project_id: Optional[str] = None, 
                                github_project_url: Optional[str] = None, 
                                prd_title: Optional[str] = None) -> bool:
        """Persist or update the 1:1 mapping between a Notion PRD page and a GitHub repository/project."""
        try:
            with context_store.db_session() as cursor:
                if cursor is None: return False
                
                cursor.execute("""
                    INSERT INTO prd_github_mappings (notion_page_id, repo_name, github_repo_id, github_project_id, github_project_url, prd_title, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, NOW())
                    ON CONFLICT (notion_page_id)
                    DO UPDATE SET
                        repo_name  = EXCLUDED.repo_name,
                        github_repo_id = EXCLUDED.github_repo_id,
                        github_project_id = EXCLUDED.github_project_id,
                        github_project_url = EXCLUDED.github_project_url,
                        prd_title  = EXCLUDED.prd_title,
                        updated_at = NOW();
                """, (notion_page_id, repo_name, github_repo_id, github_project_id, github_project_url, prd_title))
                return True
        except Exception as e:
            print(f"[GithubStore] Error upserting PRD-repo mapping: {e}")
            return False

    def get_repo_for_prd(self, notion_page_id: str) -> Optional[Dict[str, Any]]:
        """Return the GitHub repo data previously mapped to this Notion PRD page."""
        try:
            with context_store.db_session(commit=False) as cursor:
                if cursor is None: return None
                
                cursor.execute("""
                    SELECT repo_name, github_repo_id, github_project_id, github_project_url FROM prd_github_mappings
                    WHERE notion_page_id = %s;
                """, (notion_page_id,))
                return cursor.fetchone()
        except Exception as e:
            print(f"[GithubStore] Error retrieving PRD-repo mapping: {e}")
            return None

    def get_all_prd_mappings(self) -> List[Dict[str, Any]]:
        """Return all persisted PRD-to-repo mappings."""
        try:
            with context_store.db_session(commit=False) as cursor:
                if cursor is None: return []
                
                cursor.execute("SELECT notion_page_id, repo_name, prd_title FROM prd_github_mappings ORDER BY updated_at DESC;")
                return list(cursor.fetchall())
        except Exception as e:
            print(f"[GithubStore] Error retrieving all PRD mappings: {e}")
            return []

# Singleton instance
github_store = GithubStore()
