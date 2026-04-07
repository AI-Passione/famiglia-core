import time
import json
import os
import redis
import threading
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv
from urllib.parse import urlparse
from mattermostdriver import Driver

from famiglia_core.command_center.backend.comms.queue import (
    CommsQueue, 
    PRIORITY_CRITICAL, 
    PRIORITY_HIGH, 
    PRIORITY_MEDIUM, 
    PRIORITY_LOW, 
    BATCH_INTERVALS
)

class MattermostQueueClient(CommsQueue):
    def __init__(self, redis_url: Optional[str] = None):
        super().__init__(platform="mattermost", redis_url=redis_url)
        load_dotenv()
        print("[MattermostQueueClient] Initializing v2 (hostname fix)...")
        
        # Connection settings
        self.url = os.getenv("MATTERMOST_URL", "http://localhost:8065")
        parsed = urlparse(self.url)
        self.scheme = os.getenv("MATTERMOST_SCHEME", parsed.scheme or "http")
        self.port = int(os.getenv("MATTERMOST_PORT", str(parsed.port or 8065)))
        self.hostname = parsed.hostname or "localhost"
        
        # Multi-bot support
        self.agent_tokens = {
            "alfredo": os.getenv("MATTERMOST_BOT_TOKEN_ALFREDO"),
            "vito": os.getenv("MATTERMOST_BOT_TOKEN_VITO"),
            "riccardo": os.getenv("MATTERMOST_BOT_TOKEN_RICCARDO"),
            "rossini": os.getenv("MATTERMOST_BOT_TOKEN_ROSSINI"),
            "tommy": os.getenv("MATTERMOST_BOT_TOKEN_TOMMY"),
            "bella": os.getenv("MATTERMOST_BOT_TOKEN_BELLA"),
            "kowalski": os.getenv("MATTERMOST_BOT_TOKEN_KOWALSKI"),
            "system": os.getenv("MATTERMOST_BOT_TOKEN_SYSTEM"),
        }
        
        self.drivers: Dict[str, Driver] = {}
        self.user_ids: Dict[str, str] = {}
        self.team_ids: Dict[str, str] = {} # Cache for team IDs
        self.channel_ids: Dict[str, str] = {} # Cache for channel IDs
        
        for agent, token in self.agent_tokens.items():
            if not token:
                continue
                
            driver = Driver({
                'url': self.hostname,
                'token': token,
                'scheme': self.scheme,
                'port': self.port,
                'verify': False # Allow self-signed certs for local dev
            })
            
            agent_key = agent.lower()
            try:
                # Login/Test connection
                driver.login()
                user = driver.users.get_user('me')
                self.user_ids[agent_key] = user['id']
                self.drivers[agent_key] = driver
                # Silent init to let main.py handle the "Initializing listener..." log
            except Exception as e:
                print(f"[Mattermost ❌] [{agent}] Auth failed for bot {agent}: {e}")
                # Don't keep broken drivers
                if agent_key in self.drivers:
                    del self.drivers[agent_key]


        self.app_env = os.getenv("APP_ENV", "production").lower()

    def get_driver(self, agent: str) -> Optional[Driver]:
        return self.drivers.get(agent.lower()) or self.drivers.get("alfredo") or self.drivers.get("system")

    def post_message(self, agent: str, channel_id: str, message: str, root_id: Optional[str] = None) -> Optional[str]:
        """Immediate synchronous send. If channel_id looks like a name, it tries to resolve it."""
        driver = self.get_driver(agent)
        if not driver:
            print(f"MOCK MATTERMOST SEND [{agent}] -> {channel_id}: {message}")
            return str(time.time())

        # Simple heuristic: if it doesn't look like a Mattermost ID (26 chars), try resolving
        real_channel_id = channel_id
        if len(channel_id) != 26:
            resolved = self.find_channel_by_name(channel_id, agent)
            if resolved:
                real_channel_id = resolved

        try:
            post = driver.posts.create_post({
                'channel_id': real_channel_id,
                'message': message,
                'root_id': root_id
            })
            return post['id']
        except Exception as e:
            print(f"[Mattermost ❌] [{agent}] Error posting message to {real_channel_id}: {e}")
            return None

    def find_channel_by_name(self, channel_name: str, agent: str = "system") -> Optional[str]:
        """Try to find a channel ID by its name across all teams the bot belongs to"""
        driver = self.get_driver(agent)
        if not driver: return None
        
        # Strip # if present
        name = channel_name.lstrip("#")
        
        try:
            teams = driver.teams.get_user_teams(self.user_ids.get(agent.lower(), 'me'))
            for team in teams:
                try:
                    channel = driver.channels.get_channel_by_name(team['id'], name)
                    return channel['id']
                except:
                    continue
            return None
        except Exception:
            return None

    def add_reaction(self, agent: str, post_id: str, emoji_name: str) -> bool:
        """Add a reaction to a post"""
        driver = self.get_driver(agent)
        user_id = self.user_ids.get(agent.lower())
        
        if not driver or not user_id:
            print(f"[Mattermost] MOCK REACTION [{agent}] (Driver: {bool(driver)}, UserID: {user_id}) -> {post_id}: :{emoji_name}:")
            return True

        try:
            print(f"[Mattermost] Adding reaction :{emoji_name}: to post {post_id} as user {user_id}")
            driver.reactions.create_reaction({
                'user_id': user_id,
                'post_id': post_id,
                'emoji_name': emoji_name.replace(":", "") # Ensure no colons
            })
            return True
        except Exception as e:
            if "already_reacted" not in str(e).lower():
                print(f"[Mattermost ❌] [{agent}] Error adding reaction: {e}")
            return False

    def get_team_id(self, team_name: str, agent: str = "system") -> Optional[str]:
        """Resolve team name to ID"""
        if team_name in self.team_ids:
            return self.team_ids[team_name]
            
        driver = self.get_driver(agent)
        if not driver: return None
        
        try:
            team = driver.teams.get_team_by_name(team_name)
            self.team_ids[team_name] = team['id']
            return team['id']
        except Exception:
            return None

    def get_channel_id(self, team_name: str, channel_name: str, agent: str = "system") -> Optional[str]:
        """Resolve channel name to ID within a team"""
        cache_key = f"{team_name}:{channel_name}"
        if cache_key in self.channel_ids:
            return self.channel_ids[cache_key]
            
        team_id = self.get_team_id(team_name, agent)
        if not team_id: return None
        
        driver = self.get_driver(agent)
        if not driver: return None
        
        try:
            channel = driver.channels.get_channel_by_name(team_id, channel_name)
            self.channel_ids[cache_key] = channel['id']
            return channel['id']
        except Exception:
            return None

    def download_file(self, file_id: str, agent_name: str) -> Optional[str]:
        """Download a file from Mattermost and return the local path"""
        driver = self.get_driver(agent_name)
        if not driver:
            print(f"[Mattermost 📂] WARNING: No driver found for {agent_name}. Cannot download.")
            return None

        save_dir = os.getenv("UPLOAD_DIR", os.path.abspath(os.path.join(os.getcwd(), "data/incoming_files")))
        os.makedirs(save_dir, exist_ok=True)
        
        try:
            # Mattermost file info
            file_info = driver.files.get_file_info(file_id)
            filename = file_info.get("name", "unnamed_file")
            
            # Ensure unique filename
            unique_filename = f"{int(time.time())}_{filename}"
            file_path = os.path.join(save_dir, unique_filename)
            
            print(f"[Mattermost 📂] Downloading {filename} ({file_id})...")
            response = driver.files.get_file(file_id)
            
            with open(file_path, "wb") as f:
                f.write(response.content)
                
            print(f"[Mattermost 📂] SUCCESS: {filename} downloaded.")
            return file_path
        except Exception as e:
            print(f"[Mattermost 📂] WARNING: Error downloading file {file_id}: {e}")
            return None

    def resolve_sender_name(self, user_id: str, agent: str = "system") -> str:
        """Resolve a readable sender name for logging/prompts"""
        driver = self.get_driver(agent)
        if not driver: return "Unknown"
        
        try:
            user = driver.users.get_user(user_id)
            return user.get("username") or user.get("nickname") or user.get("first_name") or "Unknown"
        except Exception:
            return "Unknown"

    def _process_queue(self):
        while self.running:
            item = self._dequeue_next()
            
            # Process any pending batches
            self._flush_batches()

            if not item:
                time.sleep(0.5)
                continue
                
            queue_key, payload = item
            priority = payload["priority"]
            channel = payload["channel"]
            
            if priority in [PRIORITY_CRITICAL, PRIORITY_HIGH]:
                self._send_immediately(payload)
            else:
                # Add to batch
                root_id = payload.get("root_id")
                batch_key = (channel, priority, root_id)
                if batch_key not in self.batches:
                    self.batches[batch_key] = []
                    self.last_batch_time[batch_key] = time.time()
                self.batches[batch_key].append(payload)

    def _flush_batches(self):
        """Checks if any batches are ready to be sent"""
        now = time.time()
        for batch_key, messages in list(self.batches.items()):
            if not messages: continue
            
            channel, priority, root_id = batch_key
            interval = BATCH_INTERVALS.get(priority, 30)
            
            if now - self.last_batch_time.get(batch_key, 0) >= interval:
                self._send_batch(channel, priority, messages, root_id=root_id)
                del self.batches[batch_key]
                del self.last_batch_time[batch_key]

    def _send_batch(self, channel: str, priority: int, messages: List[dict], root_id: Optional[str] = None):
        if not messages: return
        for msg in messages:
            self._rate_limit(channel)
            self.post_message(msg["agent"], channel, msg["message"], root_id=root_id)

    def _send_immediately(self, payload: dict):
        channel = payload["channel"]
        root_id = payload.get("root_id")
        self._rate_limit(channel)
        self.post_message(payload["agent"], channel, payload["message"], root_id=root_id)

    def start_worker(self):
        """Standard parameterless start for the backend main loop."""
        super().start_worker(self._process_queue)

# Singleton instance
mattermost_queue = MattermostQueueClient()
