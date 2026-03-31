import os
import time
import requests
import jwt
import redis
import json
from typing import Dict, Any, List, Optional
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
from famiglia_core.db.tools.github_store import github_store

class GithubClient:
    def __init__(self):
        self.static_token = os.getenv("GITHUB_TOKEN")
        self.base_url = "https://api.github.com"
        self.session = requests.Session()
        
        # Redis cache for app tokens
        host = os.getenv("REDIS_HOST", "localhost")
        port = os.getenv("REDIS_PORT", "6379")
        self.redis = redis.from_url(f"redis://{host}:{port}")
        
        # Local fallback cache for app tokens (brief)
        self._cached_tokens: Dict[str, str] = {}
        self._token_expires_at: Dict[str, int] = {}
        
    def _get_app_token(self, agent_name: str) -> str:
        """Generate and retrieve a cached GitHub App installation token."""
        now = int(time.time())
        # Clean up agent_name to match env var format (e.g. "Dr. Rossini" -> "DR_ROSSINI")
        agent_key = agent_name.replace(".", "").replace(" ","_").upper()
        if agent_key == "DR_ROSSINI":
            agent_key = "ROSSINI"  # Specific hardcoded mapping for la-passione-inc

        # 1. Check local cache (buffer of 60 seconds)
        if self._cached_tokens.get(agent_key) and self._token_expires_at.get(agent_key, 0) > (now + 60):
            return self._cached_tokens[agent_key]
            
        # 2. Check Redis cache
        redis_key = f"github:token:{agent_key}"
        try:
            cached_data = self.redis.get(redis_key)
            if cached_data:
                data = json.loads(cached_data)
                token = data.get("token")
                expires_at = data.get("expires_at", 0)
                if token and expires_at > (now + 60):
                    # Sync to local cache
                    self._cached_tokens[agent_key] = token
                    self._token_expires_at[agent_key] = expires_at
                    return token
        except Exception as e:
            print(f"[GitHub] Redis cache check failed: {e}")

        app_id = os.getenv(f"GITHUB_APP_ID_{agent_key}")
        install_id = os.getenv(f"GITHUB_APP_INSTALLATION_ID_{agent_key}")
        
        private_key = os.getenv(f"GITHUB_APP_PRIVATE_KEY_{agent_key}")
        private_key_path = os.getenv(f"GITHUB_APP_PRIVATE_KEY_PATH_{agent_key}")
        if not private_key and private_key_path and os.path.exists(private_key_path):
            with open(private_key_path, "r") as f:
                private_key = f.read()

        if not app_id or not install_id or not private_key:
            raise ValueError(
                f"GITHUB_TOKEN is not set, and GitHub App credentials for {agent_name} (GITHUB_APP_ID_{agent_key}, "
                f"GITHUB_APP_INSTALLATION_ID_{agent_key}, GITHUB_APP_PRIVATE_KEY_{agent_key}) are incomplete. "
                "GitHub integration is disabled."
            )

        # 1. Generate JWT (valid for 10 minutes max, we use 9)
        payload = {
            'iat': now,
            'exp': now + (9 * 60),
            'iss': str(app_id)
        }
        
        # Format the private key
        pk = private_key
        
        # When loaded from .env, it often has literal '\n' that need to be actual newlines
        pk = str(pk).replace("\\n", "\n")
            
        # Remove extra whitespace/quotes that .env might inject
        pk = pk.strip('"').strip("'")
        
        # We also need to collapse any \n\n into a single \n because dotenv might preserve literal extra returns
        while "\n\n" in pk:
            pk = pk.replace("\n\n", "\n")

        # Re-ensure that the key starts and ends correctly
        if not pk.startswith("-----BEGIN RSA PRIVATE KEY-----"):
            raise ValueError("Private key format invalid: missing BEGIN RSA PRIVATE KEY")

        try:
            # Load the key via cryptography to ensure it is in the perfect format for PyJWT
            key_obj = serialization.load_pem_private_key(
                pk.encode('utf-8'),
                password=None,
                backend=default_backend()
            )
            
            jwt_token = jwt.encode(payload, key_obj, algorithm='RS256')
        except Exception as e:
            pk_str = str(pk)
            # Avoid Pyre indexing errors entirely by splitting strings instead of indexing
            pk_preview = pk_str.split("\\n")[0].split("\n")[0]
            raise ValueError(f"Failed to encode JWT: {e}\nKey snapshot: {pk_preview}...")
        
        # 3. Request Installation Access Token
        headers = {
            'Authorization': f'Bearer {jwt_token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        
        print(f"[{agent_name}] GitHub: Generating new app token for {agent_key}...")
        resp = self.session.post(
            f'https://api.github.com/app/installations/{install_id}/access_tokens',
            headers=headers
        )
        self._check_response(resp)
        
        data = resp.json()
        token = data['token']
        # Logging permissions for debugging
        print(f"[{agent_name}] GitHub token permissions for {agent_key}: {data.get('permissions')}")
        
        # Calculate expiration
        expires_at_iso = data.get('expires_at')
        if expires_at_iso:
            from datetime import datetime
            dt = datetime.fromisoformat(expires_at_iso.replace("Z", "+00:00"))
            exp_ts = int(dt.timestamp())
        else:
            exp_ts = now + (55 * 60)

        # Update both caches
        self._cached_tokens[agent_key] = token
        self._token_expires_at[agent_key] = exp_ts
        
        # Store in Redis with TTL (add extra buffer to ensure Redis expires it after we stop using it)
        ttl = exp_ts - now
        if ttl > 0:
            try:
                self.redis.setex(
                    f"github:token:{agent_key}",
                    ttl,
                    json.dumps({"token": token, "expires_at": exp_ts})
                )
            except Exception as e:
                print(f"[GitHub] Redis set failed: {e}")

        return token

    def _get_headers(self, agent_name: str, use_graphql: bool = False) -> Dict[str, str]:
        """Get headers with the appropriate dynamic or static token."""
        token = self._get_app_token(agent_name)
        headers = {
            "Authorization": f"Bearer {token}"
        }
        if not use_graphql:
            headers["Accept"] = "application/vnd.github.v3+json"
        return headers

    def _check_response(self, response: requests.Response) -> requests.Response:
        """Check the response and raise a detailed error if it failed."""
        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            try:
                error_body = response.json()
            except ValueError:
                error_body = response.text
            
            # Log headers on failure for debugging permissions
            headers_info = {k: v for k, v in response.headers.items() if k.lower().startswith("x-")}
            print(f"[GitHub] Error Details - Status: {response.status_code}, Headers: {headers_info}")
            
            raise Exception(f"GitHub API Error: {response.status_code} - {error_body}") from e
        return response

    def list_accessible_repos(self, agent_name: str, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """List all repositories the GitHub App installation has access to."""
        if not force_refresh:
            cached_repos = github_store.get_accessible_repos(agent_name)
            if cached_repos:
                print(f"[{agent_name}] GitHub: list_accessible_repos() (cached)")
                # Map back to match the API structure where 'full_name' is used
                return [{"full_name": repo["repo_name"], "permissions": repo.get("permissions")} for repo in cached_repos]

        url = f"{self.base_url}/installation/repositories"
        print(f"[{agent_name}] GitHub: list_accessible_repos() (API)")
        response = self.session.get(url, headers=self._get_headers(agent_name))
        self._check_response(response)
        data = response.json()
        
        repos = data.get("repositories", [])
        
        # Persist to database cache
        for repo in repos:
            repo_name = repo.get("full_name")
            permissions = repo.get("permissions")
            if repo_name:
                github_store.upsert_github_repo_access(
                    agent_name=agent_name, 
                    repo_name=repo_name, 
                    permissions=permissions
                )

        # Log this broadly as a read action
        github_store.log_github_action(
            agent_name=agent_name,
            action_type="LIST_ACCESSIBLE_REPOS",
            repo_name="all",
            metadata={"count": data.get("total_count")}
        )
        return repos

    def read_repo(self, repo_name: str, agent_name: str) -> Dict[str, Any]:
        """Fetch repository details."""
        url = f"{self.base_url}/repos/{repo_name}"
        print(f"[{agent_name}] GitHub: read_repo('{repo_name}')")
        response = self.session.get(url, headers=self._get_headers(agent_name))
        self._check_response(response)
        data = response.json()
        
        github_store.log_github_action(
            agent_name=agent_name,
            action_type="READ_REPO",
            repo_name=repo_name,
            metadata={"description": data.get("description"), "stars": data.get("stargazers_count")}
        )
        return data

    def list_issues(self, repo_name: str, agent_name: str, state: str = "open") -> List[Dict[str, Any]]:
        """List repository issues (all pages)."""
        issues = []
        page = 1
        per_page = 100
        
        print(f"[{agent_name}] GitHub: list_issues('{repo_name}', state='{state}')")
        while True:
            url = f"{self.base_url}/repos/{repo_name}/issues"
            params = {"state": state, "page": page, "per_page": per_page}
            response = self.session.get(url, headers=self._get_headers(agent_name), params=params)
            self._check_response(response)
            
            page_data = response.json()
            if not page_data:
                break
                
            # GitHub's /issues API returns both issues and pull requests.
            # We filter out PRs by checking for the 'pull_request' key.
            issues_only = [item for item in page_data if "pull_request" not in item]
            
            for issue in issues_only:
                milestone = issue.get("milestone")
                issues.append({
                    "number": issue.get("number"),
                    "title": issue.get("title"),
                    "state": issue.get("state"),
                    "user": issue.get("user", {}).get("login"),
                    "labels": [label.get("name") for label in issue.get("labels", [])],
                    "created_at": issue.get("created_at"),
                    "milestone_title": milestone.get("title") if milestone else None,
                    "milestone_number": milestone.get("number") if milestone else None
                })
            
            if len(page_data) < per_page:
                break
            page += 1
            
        return issues

    def get_issue(self, repo_name: str, issue_number: int, agent_name: str) -> Dict[str, Any]:
        """Get a single issue from a repository."""
        url = f"{self.base_url}/repos/{repo_name}/issues/{issue_number}"
        print(f"[{agent_name}] GitHub: get_issue('{repo_name}', #{issue_number})")
        response = self.session.get(url, headers=self._get_headers(agent_name))
        self._check_response(response)
        data = response.json()
        
        github_store.log_github_action(
            agent_name=agent_name,
            action_type="GET_ISSUE",
            repo_name=repo_name,
            metadata={"issue_number": issue_number, "title": data.get("title")}
        )
        return data

    def update_issue(self, repo_name: str, issue_number: int, agent_name: str, state: Optional[str] = None, title: Optional[str] = None, body: Optional[str] = None) -> Dict[str, Any]:
        """Update an existing issue."""
        url = f"{self.base_url}/repos/{repo_name}/issues/{issue_number}"
        payload = {}
        if state: payload["state"] = state
        if title: payload["title"] = title
        if body is not None: payload["body"] = body
        
        print(f"[{agent_name}] GitHub: update_issue('{repo_name}', #{issue_number})")
        response = self.session.patch(url, headers=self._get_headers(agent_name), json=payload)
        self._check_response(response)
        data = response.json()

        github_store.log_github_action(
            agent_name=agent_name,
            action_type="UPDATE_ISSUE",
            repo_name=repo_name,
            metadata={"issue_number": issue_number, "updated_fields": list(payload.keys())}
        )
        return data

    def create_issue_comment(self, repo_name: str, issue_number: int, body: str, agent_name: str) -> Dict[str, Any]:
        """Create a comment on an issue."""
        url = f"{self.base_url}/repos/{repo_name}/issues/{issue_number}/comments"
        payload = {"body": body}
        print(f"[{agent_name}] GitHub: create_issue_comment('{repo_name}', #{issue_number})")
        response = self.session.post(url, headers=self._get_headers(agent_name), json=payload)
        self._check_response(response)
        data = response.json()
        
        github_store.log_github_action(
            agent_name=agent_name,
            action_type="CREATE_ISSUE_COMMENT",
            repo_name=repo_name,
            metadata={"issue_number": issue_number, "comment_id": data.get("id")}
        )
        return data

    def add_issue_labels(self, repo_name: str, issue_number: int, labels: List[str], agent_name: str) -> List[str]:
        """Add labels to an issue."""
        url = f"{self.base_url}/repos/{repo_name}/issues/{issue_number}/labels"
        payload = {"labels": labels}
        print(f"[{agent_name}] GitHub: add_issue_labels('{repo_name}', #{issue_number}, {labels})")
        response = self.session.post(url, headers=self._get_headers(agent_name), json=payload)
        self._check_response(response)
        data = response.json()
        
        github_store.log_github_action(
            agent_name=agent_name,
            action_type="ADD_ISSUE_LABELS",
            repo_name=repo_name,
            metadata={"issue_number": issue_number, "labels": labels}
        )
        return [label.get("name") for label in data]

    def update_issue_labels(self, repo_name: str, issue_number: int, labels: List[str], agent_name: str) -> List[str]:
        """Replace all labels on an issue."""
        url = f"{self.base_url}/repos/{repo_name}/issues/{issue_number}/labels"
        payload = {"labels": labels}
        print(f"[{agent_name}] GitHub: update_issue_labels('{repo_name}', #{issue_number}, {labels})")
        response = self.session.put(url, headers=self._get_headers(agent_name), json=payload)
        self._check_response(response)
        data = response.json()
        
        github_store.log_github_action(
            agent_name=agent_name,
            action_type="UPDATE_ISSUE_LABELS",
            repo_name=repo_name,
            metadata={"issue_number": issue_number, "labels": labels}
        )
        return [label.get("name") for label in data]

    def remove_issue_label(self, repo_name: str, issue_number: int, label_name: str, agent_name: str) -> bool:
        """Remove a specific label from an issue."""
        import urllib.parse
        encoded_label = urllib.parse.quote(label_name)
        url = f"{self.base_url}/repos/{repo_name}/issues/{issue_number}/labels/{encoded_label}"
        print(f"[{agent_name}] GitHub: remove_issue_label('{repo_name}', #{issue_number}, '{label_name}')")
        response = self.session.delete(url, headers=self._get_headers(agent_name))
        self._check_response(response)
        
        github_store.log_github_action(
            agent_name=agent_name,
            action_type="REMOVE_ISSUE_LABEL",
            repo_name=repo_name,
            metadata={"issue_number": issue_number, "label_name": label_name}
        )
        return response.status_code == 204

    def edit_issue_comment(self, repo_name: str, comment_id: int, body: str, agent_name: str) -> Dict[str, Any]:
        """Edit an existing issue comment."""
        url = f"{self.base_url}/repos/{repo_name}/issues/comments/{comment_id}"
        payload = {"body": body}
        print(f"[{agent_name}] GitHub: edit_issue_comment('{repo_name}', {comment_id})")
        response = self.session.patch(url, headers=self._get_headers(agent_name), json=payload)
        self._check_response(response)
        data = response.json()
        
        github_store.log_github_action(
            agent_name=agent_name,
            action_type="EDIT_ISSUE_COMMENT",
            repo_name=repo_name,
            metadata={"comment_id": comment_id}
        )
        return data

    def delete_issue_comment(self, repo_name: str, comment_id: int, agent_name: str) -> bool:
        """Delete an existing issue comment."""
        url = f"{self.base_url}/repos/{repo_name}/issues/comments/{comment_id}"
        print(f"[{agent_name}] GitHub: delete_issue_comment('{repo_name}', {comment_id})")
        response = self.session.delete(url, headers=self._get_headers(agent_name))
        self._check_response(response)
        
        github_store.log_github_action(
            agent_name=agent_name,
            action_type="DELETE_ISSUE_COMMENT",
            repo_name=repo_name,
            metadata={"comment_id": comment_id}
        )
        return response.status_code == 204

    def create_issue(self, repo_name: str, title: str, body: str, agent_name: str, milestone: Optional[int] = None) -> Dict[str, Any]:
        """Create a new issue in a repository, optionally attached to a milestone."""
        url = f"{self.base_url}/repos/{repo_name}/issues"
        payload: Dict[str, Any] = {"title": title, "body": body}
        if milestone is not None:
            payload["milestone"] = milestone
        print(f"[{agent_name}] GitHub: create_issue('{repo_name}', title='{title}', milestone={milestone})")
        response = self.session.post(url, headers=self._get_headers(agent_name), json=payload)
        self._check_response(response)
        data = response.json()
        
        github_store.log_github_action(
            agent_name=agent_name,
            action_type="CREATE_ISSUE",
            repo_name=repo_name,
            metadata={"issue_number": data.get("number"), "title": title, "milestone": milestone}
        )
        return data

    def list_milestones(self, repo_name: str, agent_name: str, state: str = "open") -> List[Dict[str, Any]]:
        """List repository milestones (all pages)."""
        milestones = []
        page = 1
        per_page = 100
        
        print(f"[{agent_name}] GitHub: list_milestones('{repo_name}')")
        while True:
            url = f"{self.base_url}/repos/{repo_name}/milestones"
            params = {"state": state, "page": page, "per_page": per_page}
            response = self.session.get(url, headers=self._get_headers(agent_name), params=params)
            self._check_response(response)
            
            page_data = response.json()
            if not page_data:
                break
                
            milestones.extend(page_data)
            
            if len(page_data) < per_page:
                break
            page += 1
            
        return milestones

    def create_milestone(self, repo_name: str, title: str, description: str, agent_name: str) -> Dict[str, Any]:
        """Create a new milestone in a repository."""
        url = f"{self.base_url}/repos/{repo_name}/milestones"
        payload = {"title": title, "description": description}
        print(f"[{agent_name}] GitHub: create_milestone('{repo_name}', title='{title}')")
        response = self.session.post(url, headers=self._get_headers(agent_name), json=payload)
        self._check_response(response)
        data = response.json()
        
        github_store.log_github_action(
            agent_name=agent_name,
            action_type="CREATE_MILESTONE",
            repo_name=repo_name,
            metadata={"milestone_number": data.get("number"), "title": title}
        )
        return data

    def delete_milestone(self, repo_name: str, milestone_number: int, agent_name: str) -> bool:
        """Delete a milestone from a repository."""
        url = f"{self.base_url}/repos/{repo_name}/milestones/{milestone_number}"
        print(f"[{agent_name}] GitHub: delete_milestone('{repo_name}', #{milestone_number})")
        response = self.session.delete(url, headers=self._get_headers(agent_name))
        self._check_response(response)
        
        github_store.log_github_action(
            agent_name=agent_name,
            action_type="DELETE_MILESTONE",
            repo_name=repo_name,
            metadata={"milestone_number": milestone_number}
        )
        return response.status_code == 204

    def create_branch(self, repo_name: str, new_branch: str, base_branch: str, agent_name: str) -> Dict[str, Any]:
        """Create a new branch from a base branch."""
        # Get base branch SHA
        url_get_ref = f"{self.base_url}/repos/{repo_name}/git/ref/heads/{base_branch}"
        print(f"[{agent_name}] GitHub: create_branch('{repo_name}', '{new_branch}' from '{base_branch}')")
        res = self.session.get(url_get_ref, headers=self._get_headers(agent_name))
        self._check_response(res)
        sha = res.json()["object"]["sha"]
        
        # Create new branch
        url_create_ref = f"{self.base_url}/repos/{repo_name}/git/refs"
        payload = {
            "ref": f"refs/heads/{new_branch}",
            "sha": sha
        }
        res_create = self.session.post(url_create_ref, headers=self._get_headers(agent_name), json=payload)
        
        if res_create.status_code == 422 and "Reference already exists" in res_create.text:
            print(f"[{agent_name}] GitHub: create_branch('{new_branch}') skipped (already exists).")
            # Return the same structure as create_ref would
            return {"ref": f"refs/heads/{new_branch}", "object": {"sha": sha}}
            
        self._check_response(res_create)
        data = res_create.json()
        
        github_store.log_github_action(
            agent_name=agent_name,
            action_type="CREATE_BRANCH",
            repo_name=repo_name,
            metadata={"new_branch": new_branch, "base_branch": base_branch, "sha": sha}
        )
        return data

    def read_file(self, repo_name: str, file_path: str, branch: str, agent_name: str) -> Dict[str, Any]:
        """Read a file's content from a repository."""
        import base64
        url = f"{self.base_url}/repos/{repo_name}/contents/{file_path}"
        print(f"[{agent_name}] GitHub: read_file('{repo_name}', '{file_path}')")
        params = {"ref": branch} if branch else {}
        res = self.session.get(url, headers=self._get_headers(agent_name), params=params)
        self._check_response(res)
        data = res.json()
        if not isinstance(data, dict):
            # If the API returned a raw string, wrap it in a dict for compatibility
            return {"decoded_content": str(data), "content": str(data)}
            
        if "content" in data and data.get("encoding") == "base64":
            data["decoded_content"] = base64.b64decode(data["content"]).decode("utf-8")
        return data

    def commit_file(self, repo_name: str, file_path: str, content: str, commit_message: str, branch: str, agent_name: str) -> Dict[str, Any]:
        """Create or update a file in a repository."""
        import base64
        # First, try to get the file to get its SHA if it exists
        url = f"{self.base_url}/repos/{repo_name}/contents/{file_path}"
        print(f"[{agent_name}] GitHub: commit_file('{repo_name}', '{file_path}', branch='{branch}')")
        params = {"ref": branch}
        res_get = self.session.get(url, headers=self._get_headers(agent_name), params=params)
        
        file_sha = None
        if res_get.status_code == 200:
            file_sha = res_get.json()["sha"]
            
        payload = {
            "message": commit_message,
            "content": base64.b64encode(content.encode("utf-8")).decode("utf-8"),
            "branch": branch
        }
        if file_sha:
            payload["sha"] = file_sha
            
        res_put = self.session.put(url, headers=self._get_headers(agent_name), json=payload)
        self._check_response(res_put)
        data = res_put.json()
        
        github_store.log_github_action(
            agent_name=agent_name,
            action_type="COMMIT_FILE",
            repo_name=repo_name,
            metadata={"file_path": file_path, "branch": branch, "commit_message": commit_message}
        )
        return data

    def list_pull_requests(self, repo_name: str, agent_name: str, state: str = "open") -> List[Dict[str, Any]]:
        """List pull requests for a repository."""
        url = f"{self.base_url}/repos/{repo_name}/pulls"
        params = {"state": state}
        print(f"[{agent_name}] GitHub: list_pull_requests('{repo_name}')")
        response = self.session.get(url, headers=self._get_headers(agent_name), params=params)
        self._check_response(response)
        return response.json()

    def get_pull_request(self, repo_name: str, pr_number: int, agent_name: str) -> Dict[str, Any]:
        """Fetch a single pull request snippet."""
        url = f"{self.base_url}/repos/{repo_name}/pulls/{pr_number}"
        print(f"[{agent_name}] GitHub: get_pull_request('{repo_name}', #{pr_number})")
        response = self.session.get(url, headers=self._get_headers(agent_name))
        self._check_response(response)
        return response.json()

    def list_issue_comments(self, repo_name: str, issue_number: int, agent_name: str) -> List[Dict[str, Any]]:
        """List comments for an issue (or PR)."""
        url = f"{self.base_url}/repos/{repo_name}/issues/{issue_number}/comments"
        print(f"[{agent_name}] GitHub: list_issue_comments('{repo_name}', #{issue_number})")
        response = self.session.get(url, headers=self._get_headers(agent_name))
        self._check_response(response)
        return response.json()

    def list_pull_request_comments(self, repo_name: str, pr_number: int, agent_name: str) -> List[Dict[str, Any]]:
        """List review comments on a PR (inline in code)."""
        url = f"{self.base_url}/repos/{repo_name}/pulls/{pr_number}/comments"
        print(f"[{agent_name}] GitHub: list_pull_request_comments('{repo_name}', #{pr_number})")
        response = self.session.get(url, headers=self._get_headers(agent_name))
        self._check_response(response)
        return response.json()

    def list_pull_request_files(self, repo_name: str, pr_number: int, agent_name: str) -> List[Dict[str, Any]]:
        """List files changed in a pull request."""
        url = f"{self.base_url}/repos/{repo_name}/pulls/{pr_number}/files"
        print(f"[{agent_name}] GitHub: list_pull_request_files('{repo_name}', #{pr_number})")
        response = self.session.get(url, headers=self._get_headers(agent_name))
        self._check_response(response)
        return response.json()

    def create_pull_request_comment_reply(self, repo_name: str, pr_number: int, comment_id: int, body: str, agent_name: str) -> Dict[str, Any]:
        """Reply to a specific PR review comment."""
        url = f"{self.base_url}/repos/{repo_name}/pulls/{pr_number}/comments/{comment_id}/replies"
        payload = {"body": body}
        print(f"[{agent_name}] GitHub: create_pull_request_comment_reply('{repo_name}', PR #{pr_number}, Comment #{comment_id})")
        response = self.session.post(url, headers=self._get_headers(agent_name), json=payload)
        self._check_response(response)
        return response.json()

    def create_pr(self, repo_name: str, title: str, body: str, head_branch: str, base_branch: str, agent_name: str) -> Dict[str, Any]:
        """Create a pull request."""
        url = f"{self.base_url}/repos/{repo_name}/pulls"
        payload = {
            "title": title,
            "body": body,
            "head": head_branch,
            "base": base_branch
        }
        print(f"[{agent_name}] GitHub: create_pr('{repo_name}', head='{head_branch}', base='{base_branch}')")
        response = self.session.post(url, headers=self._get_headers(agent_name), json=payload)
        
        if response.status_code == 422 and "A pull request already exists" in response.text:
            print(f"[{agent_name}] GitHub: create_pr() skipped (PR already exists for head {head_branch}).")
            # Find and return the existing PR
            existing_prs = self.list_pull_requests(repo_name, agent_name)
            for pr in existing_prs:
                if pr.get("head", {}).get("ref") == head_branch:
                    return pr
            # If we somehow can't find it, raise the original error
            self._check_response(response)

        self._check_response(response)
        data = response.json()
        
        github_store.log_github_action(
            agent_name=agent_name,
            action_type="CREATE_PR",
            repo_name=repo_name,
            metadata={"pr_number": data.get("number"), "title": title, "head": head_branch, "base": base_branch}
        )
        return data

    def auto_create_pr(self, repo_name: str, file_path: str, file_content: str, commit_message: str, pr_title: str, pr_body: str, new_branch: str, base_branch: str, agent_name: str) -> Dict[str, Any]:
        """Convenience method that runs the full Dev cycle: Branch -> Commit -> PR."""
        print(f"[{agent_name}] GitHub: auto_create_pr('{repo_name}', branch='{new_branch}')")
        # 1. Create Branch
        branch_data = self.create_branch(repo_name, new_branch, base_branch, agent_name)
        
        # 2. Commit File
        commit_data = self.commit_file(repo_name, file_path, file_content, commit_message, new_branch, agent_name)
        
        # 3. Create PR
        pr_data = self.create_pr(repo_name, pr_title, pr_body, new_branch, base_branch, agent_name)
        
        # Add context from earlier steps to the returned PR object
        pr_data["commit_url"] = commit_data.get("commit", {}).get("html_url")
        pr_data["branch_ref"] = branch_data.get("ref")
        return pr_data

    # --- GraphQL & Projects V2 Support ---

    def graphql_query(self, query: str, variables: Optional[Dict[str, Any]] = None, agent_name: str = "Rossini") -> Dict[str, Any]:
        """Execute a GitHub GraphQL query."""
        url = "https://api.github.com/graphql"
        payload = {"query": query}
        if variables:
            payload["variables"] = variables
            
        headers = self._get_headers(agent_name, use_graphql=True)
        response = self.session.post(url, headers=headers, json=payload)
        self._check_response(response)
        
        data = response.json()
        if "errors" in data:
            raise Exception(f"GitHub GraphQL Error: {json.dumps(data['errors'], indent=2)}")
        return data

    def get_node_ids(self, repo_name: str, agent_name: str = "Rossini") -> Dict[str, str]:
        """Fetch node IDs for a repository and its owner (Org or User)."""
        owner, name = repo_name.split("/")
        query = """
        query($owner: String!, $name: String!) {
          repository(owner: $owner, name: $name) {
            id
            owner {
              __typename
              id
              login
            }
          }
        }
        """
        data = self.graphql_query(query, {"owner": owner, "name": name}, agent_name=agent_name)
        repo_data = data["data"]["repository"]
        return {
            "repository_id": repo_data["id"],
            "owner_id": repo_data["owner"]["id"],
            "owner_type": repo_data["owner"]["__typename"]
        }

    def create_project_v2(self, owner_id: str, title: str, repository_id: Optional[str] = None, agent_name: str = "Rossini") -> Dict[str, Any]:
        """Create a new GitHub Project (V2)."""
        query = """
        mutation($ownerId: ID!, $title: String!, $repositoryId: ID) {
          createProjectV2(input: {ownerId: $ownerId, title: $title, repositoryId: $repositoryId}) {
            projectV2 {
              id
              number
              url
            }
          }
        }
        """
        variables = {"ownerId": owner_id, "title": title}
        if repository_id:
            variables["repositoryId"] = repository_id
            
        print(f"[{agent_name}] GitHub: create_project_v2(title='{title}')")
        data = self.graphql_query(query, variables, agent_name=agent_name)
        return data["data"]["createProjectV2"]["projectV2"]

    def list_projects_v2(self, repo_name: str, agent_name: str = "Rossini") -> List[Dict[str, Any]]:
        """List Project V2s for an organization or user."""
        owner = repo_name.split("/")[0]
        query = """
        query($owner: String!) {
          organization(login: $owner) {
            projectsV2(first: 20) {
              nodes {
                id
                title
                number
              }
            }
          }
          user(login: $owner) {
            projectsV2(first: 20) {
              nodes {
                id
                title
                number
              }
            }
          }
        }
        """
        variables = {"owner": owner}
        data = self.graphql_query(query, variables, agent_name=agent_name)
        
        projects = []
        if data.get("data", {}).get("organization"):
            projects.extend(data["data"]["organization"]["projectsV2"]["nodes"])
        if data.get("data", {}).get("user"):
            projects.extend(data["data"]["user"]["projectsV2"]["nodes"])
        return projects

    def add_item_to_project(self, project_id: str, content_id: str, agent_name: str = "Rossini") -> str:
        """Add an item (Issue or PR) to a Project V2. Returns the item ID."""
        query = """
        mutation($projectId: ID!, $contentId: ID!) {
          addProjectV2ItemById(input: {projectId: $projectId, contentId: $contentId}) {
            item {
              id
            }
          }
        }
        """
        variables = {"projectId": project_id, "contentId": content_id}
        data = self.graphql_query(query, variables, agent_name=agent_name)
        return data["data"]["addProjectV2ItemById"]["item"]["id"]

    def get_project_v2_fields(self, project_id: str, agent_name: str = "Rossini") -> Dict[str, Any]:
        """Fetch fields and their single-select options for a Project V2."""
        query = """
        query($id: ID!) {
          node(id: $id) {
            ... on ProjectV2 {
              fields(first: 50) {
                nodes {
                  ... on ProjectV2FieldCommon {
                    id
                    name
                    dataType
                  }
                  ... on ProjectV2SingleSelectField {
                    id
                    name
                    dataType
                    options {
                      id
                      name
                    }
                  }
                }
              }
            }
          }
        }
        """
        variables = {"id": project_id}
        data = self.graphql_query(query, variables, agent_name=agent_name)
        return data["data"]["node"]["fields"]["nodes"]

    def get_issue_project_items(self, repo_name: str, issue_number: int, agent_name: str = "Rossini") -> List[Dict[str, Any]]:
        """Fetch project items associated with a specific issue."""
        owner, name = repo_name.split("/")
        query = """
        query($owner: String!, $name: String!, $number: Int!) {
          repository(owner: $owner, name: $name) {
            issue(number: $number) {
              id
              projectItems(first: 10) {
                nodes {
                  id
                  project {
                    id
                  }
                  fieldValues(first: 10) {
                    nodes {
                      ... on ProjectV2ItemFieldSingleSelectValue {
                        name
                        field {
                          ... on ProjectV2FieldCommon {
                            name
                          }
                        }
                      }
                      ... on ProjectV2ItemFieldTextValue {
                        text
                        field {
                          ... on ProjectV2FieldCommon {
                            name
                          }
                        }
                      }
                    }
                  }
                }
              }
            }
          }
        }
        """
        variables = {"owner": owner, "name": name, "number": issue_number}
        data = self.graphql_query(query, variables, agent_name=agent_name)
        
        # We also need the issue's global ID to add it to a project if it's not there
        issue_id = data["data"]["repository"]["issue"]["id"]
        project_items = data["data"]["repository"]["issue"]["projectItems"]["nodes"]
        
        return {"issue_id": issue_id, "project_items": project_items}

    def update_project_v2_item_field(self, project_id: str, item_id: str, field_id: str, value_dict: Dict[str, Any], agent_name: str = "Rossini") -> Dict[str, Any]:
        """
        Update a single field on a Project V2 item.
        `value_dict` format depends on the field type.
        For Single Select: {"singleSelectOptionId": "<option_id>"}
        For Text: {"text": "<string>"}
        """
        query = """
        mutation($projectId: ID!, $itemId: ID!, $fieldId: ID!, $value: ProjectV2FieldValue!) {
          updateProjectV2ItemFieldValue(
            input: {
              projectId: $projectId
              itemId: $itemId
              fieldId: $fieldId
              value: $value
            }
          ) {
            projectV2Item {
              id
            }
          }
        }
        """
        variables = {
            "projectId": project_id,
            "itemId": item_id,
            "fieldId": field_id,
            "value": value_dict
        }
        return self.graphql_query(query, variables, agent_name=agent_name)


# Singleton instance
github_client = GithubClient()
