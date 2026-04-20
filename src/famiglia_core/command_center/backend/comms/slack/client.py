import time
import json
import os
import re
import redis
import requests
import threading
from collections import defaultdict
from typing import Dict, Any, List, Optional

from dotenv import load_dotenv
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from famiglia_core.command_center.backend.comms.queue import (
    CommsQueue, 
    PRIORITY_CRITICAL, 
    PRIORITY_HIGH, 
    PRIORITY_MEDIUM, 
    PRIORITY_LOW, 
    BATCH_INTERVALS
)

SLACK_CHANNEL_ID_RE = re.compile(r"^[CGD][A-Z0-9]{8,}$")
SLACK_CHANNEL_MENTION_RE = re.compile(r"^<#(?P<id>[CGD][A-Z0-9]{8,})(?:\|[^>]+)?>$")
SLACK_ARCHIVES_URL_RE = re.compile(r"/archives/(?P<id>[CGD][A-Z0-9]{8,})")

AGENT_EMOJIS = {
    "alfredo": "🎩",
    "vito": "🦅",
    "riccardo": "🔧",
    "rossini": "🔬",
    "tommy": "🔫",
    "bella": "💋",
    "kowalski": "📊",
    "giuseppina": "📢",
    "system": "⚙️"
}

class SlackQueueClient(CommsQueue):
    def __init__(self, redis_url: Optional[str] = None):
        super().__init__(platform="slack", redis_url=redis_url)
        # Ensure dot‑env file is read as early as possible.
        load_dotenv()
               # 1. Initialize from Environment (Fallback/Legacy)
        self.agent_tokens = {
            agent: os.getenv(f"SLACK_BOT_TOKEN_{agent.upper()}")
            for agent in AGENT_EMOJIS.keys() if agent != "system"
        }
        
        self.agent_app_tokens = {
            agent: os.getenv(f"SLACK_APP_TOKEN_{agent.upper()}")
            for agent in AGENT_EMOJIS.keys() if agent != "system"
        }

        self.agent_transports = {} # {agent_id: 'socket' | 'http'}

        # 2. Overlay from Database (The Soul of the Famiglia)
        from famiglia_core.db.tools.user_connections_store import user_connections_store
        
        db_bot_tokens = user_connections_store.list_connections("slack_bot:")
        print(f"[SlackQueue 🔍] Found {len(db_bot_tokens)} agent tokens in database.")
        for service, conn in db_bot_tokens.items():
            agent_id = service.replace("slack_bot:", "")
            self.agent_tokens[agent_id] = conn["access_token"]
            
        db_socket_tokens = user_connections_store.list_connections("slack_socket:")
        for service, conn in db_socket_tokens.items():
            agent_id = service.replace("slack_socket:", "")
            self.agent_app_tokens[agent_id] = conn["access_token"]

        db_creds = user_connections_store.list_connections("slack_creds:")
        for service, conn in db_creds.items():
            agent_id = service.replace("slack_creds:", "")
            try:
                cdata = json.loads(conn["access_token"])
                self.agent_transports[agent_id] = cdata.get("transport", "socket")
            except Exception:
                self.agent_transports[agent_id] = "socket"
        
        # Fallback to general SLACK_BOT_TOKEN if specific ones aren't set
        default_token = os.getenv("SLACK_BOT_TOKEN")
        self.app_token = os.getenv("SLACK_APP_TOKEN")
        
        self.clients = {}
        self.bot_ids = {} # {agent_name: bot_user_id}
        self.bot_id_to_name = {} # {bot_user_id: agent_name}
        
        seen_tokens: dict[str, str] = {}
        seen_user_ids: dict[str, str] = {}
        for agent, token in self.agent_tokens.items():
            if not token and not default_token:
                continue

            active_token = token or default_token
            if not active_token:
                continue

            # detect duplicate tokens to avoid cross-agent impersonation
            if active_token in seen_tokens:
                other = seen_tokens[active_token]
                if agent != other: # Only log if it's actually a different agent name
                    print(f"[SlackQueue ⚠️] Skipping '{agent}' because its token is identical to '{other}'. Check for duplicate app installs.")
                continue
            seen_tokens[active_token] = agent

            client = WebClient(token=active_token)
            try:
                auth = client.auth_test()
                user_id = auth.get("user_id")

                if user_id in seen_user_ids:
                    other_agent = seen_user_ids[user_id]
                    print(f"[SlackQueue] Skipping '{agent}' because it authenticates as the same user as '{other_agent}'.")
                    continue
                seen_user_ids[user_id] = agent

                self.clients[agent] = client
                self.bot_ids[agent] = user_id
                self.bot_id_to_name[user_id] = agent
                print(f"[SlackQueue 🔌] [{agent}] Authenticated successfully as {user_id}")
            except SlackApiError as e:
                print(f"[SlackQueue 🔌] [{agent}] Auth failed: {e.response['error']}")
        
        self.user_id = os.getenv("USER_SLACK_ID")
        self.user_name_cache: Dict[str, str] = {}
        
        if self.user_id:
            configured_user_name = self._lookup_slack_user_name(self.user_id)
            if configured_user_name:
                self.user_name_cache[self.user_id] = configured_user_name
        
        self.app_env = os.getenv("APP_ENV", "production").lower()
        self.channel_name_cache: Dict[str, str] = {}
        self.dev_channel_name = os.getenv("DEV_CHANNEL_NAME", "_dev").strip().lstrip("#").lower()
        self.dev_channel_raw = os.getenv("DEV_CHANNEL_ID")
        normalized_dev_ref = self._normalize_channel_reference(self.dev_channel_raw)
        if normalized_dev_ref and not self._is_channel_id(normalized_dev_ref):
            self.dev_channel_name = normalized_dev_ref.lstrip("#").lower()
        self.dev_channel_id = self.resolve_channel_id(self.dev_channel_raw)
        if not self.dev_channel_id and self.clients and self.dev_channel_name:
            self.dev_channel_id = self.resolve_channel_id(f"#{self.dev_channel_name}")
            if self.dev_channel_id:
                print(f"[SlackQueue] Auto-resolved dev channel #{self.dev_channel_name} -> {self.dev_channel_id}")
        if self.dev_channel_raw and not self.dev_channel_id:
            print(
                f"[SlackQueue] WARNING: could not resolve DEV_CHANNEL_ID={self.dev_channel_raw!r}. "
                "Use a Slack channel ID like C0123456789."
            )

    @staticmethod
    def _normalize_channel_reference(channel_ref: Optional[str]) -> Optional[str]:
        """Normalize configured channel references into a canonical candidate string."""
        if not channel_ref:
            return None

        value = channel_ref.strip().strip("\"'")
        if not value:
            return None

        mention_match = SLACK_CHANNEL_MENTION_RE.match(value)
        if mention_match:
            return mention_match.group("id")

        archives_match = SLACK_ARCHIVES_URL_RE.search(value)
        if archives_match:
            return archives_match.group("id")

        return value

    @staticmethod
    def _is_channel_id(value: str) -> bool:
        return bool(SLACK_CHANNEL_ID_RE.match(value))

    def _channel_name_for_id(self, channel_id: str) -> Optional[str]:
        """Resolve a channel name by ID and cache results (including misses)."""
        if channel_id in self.channel_name_cache:
            cached = self.channel_name_cache[channel_id]
            return cached or None

        if not self._is_channel_id(channel_id):
            return None

        for client in self.clients.values():
            try:
                info = client.conversations_info(channel=channel_id)
            except SlackApiError:
                continue

            name = (info.get("channel") or {}).get("name")
            if name:
                self.channel_name_cache[channel_id] = name
                return name

        self.channel_name_cache[channel_id] = ""
        return None

    def resolve_channel_id(self, channel_ref: Optional[str]) -> Optional[str]:
        """
        Resolve a configured channel reference to a Slack channel ID.
        Accepts raw IDs, <#ID|name>, Slack archive URLs, or #channel-name.
        """
        normalized = self._normalize_channel_reference(channel_ref)
        if not normalized:
            return None

        if self._is_channel_id(normalized):
            return normalized

        # Name-based lookup requires authenticated clients.
        lookup_name = normalized[1:] if normalized.startswith("#") else normalized
        if not lookup_name or not self.clients:
            return None

        for client in self.clients.values():
            cursor: Optional[str] = None
            while True:
                try:
                    resp = client.conversations_list(
                        types="public_channel,private_channel",
                        exclude_archived=True,
                        limit=1000,
                        cursor=cursor,
                    )
                except SlackApiError:
                    break

                for chan in resp.get("channels", []):
                    if chan.get("name") == lookup_name and chan.get("id"):
                        return chan["id"]

                cursor = (resp.get("response_metadata") or {}).get("next_cursor")
                if not cursor:
                    break

        return None

    def is_dev_channel(self, channel_ref: Optional[str]) -> bool:
        """Return True if this channel reference maps to the configured dev channel."""
        normalized = self._normalize_channel_reference(channel_ref)
        if not normalized:
            return False

        if self._is_channel_id(normalized):
            if self.dev_channel_id and normalized == self.dev_channel_id:
                return True
            channel_name = self._channel_name_for_id(normalized)
            return bool(channel_name and channel_name.lower() == self.dev_channel_name)

        normalized_name = normalized.lstrip("#").lower()
        return normalized_name == self.dev_channel_name

    def resolve_sender_name(self, user_id: Optional[str], event: Optional[Dict[str, Any]] = None) -> str:
        """Resolve a readable sender name for prompts/logging."""
        if not user_id:
            return "Unknown"

        if user_id in self.bot_id_to_name:
            return self.bot_id_to_name[user_id]

        # Prefer names that may be present directly in the event payload.
        if event:
            profile = event.get("user_profile") or {}
            name_from_event = (
                profile.get("display_name")
                or profile.get("real_name")
                or profile.get("name")
                or event.get("username")
            )
            if name_from_event:
                self.user_name_cache[user_id] = name_from_event
                return name_from_event

        if user_id in self.user_name_cache:
            return self.user_name_cache[user_id]

        resolved_name = self._lookup_slack_user_name(user_id)
        if resolved_name:
            self.user_name_cache[user_id] = resolved_name
            return resolved_name

        # Do not expose raw Slack IDs to the model in normal conversation.
        fallback_name = "Slack member"
        self.user_name_cache[user_id] = fallback_name
        return fallback_name

    def refresh_bot_id(self, agent_id: str) -> Optional[str]:
        """Manually refresh the bot_id for a specific agent by calling auth_test."""
        token = self.agent_tokens.get(agent_id)
        if not token:
            print(f"[SlackQueue] 🔍 Refresh failed: No token found for {agent_id}")
            return None
            
        try:
            client = WebClient(token=token)
            auth = client.auth_test()
            user_id = auth.get("user_id")
            if user_id:
                self.clients[agent_id] = client
                self.bot_ids[agent_id] = user_id
                self.bot_id_to_name[user_id] = agent_id
                print(f"[SlackQueue 🔄] Refreshed {agent_id} bot_id: {user_id}")
                return user_id
        except Exception as e:
            print(f"[SlackQueue 🔄] Error refreshing {agent_id}: {e}")
        return None

    def _lookup_slack_user_name(self, user_id: str) -> Optional[str]:
        """Try to resolve a Slack user's display/real name via users.info."""
        for client in self.clients.values():
            try:
                info = client.users_info(user=user_id)
                user = info.get("user", {})
                profile = user.get("profile", {})
                resolved_name = (
                    profile.get("display_name")
                    or profile.get("real_name")
                    or user.get("real_name")
                    or user.get("name")
                )
                if resolved_name:
                    return resolved_name
            except SlackApiError:
                continue
        return None

    def download_file(self, file_info: Dict[str, Any], agent_name: str) -> Optional[str]:
        """Download a file from Slack and return the local path."""
        url = file_info.get("url_private_download") or file_info.get("url_private")
        filename = file_info.get("name")
        if not url or not filename:
            print(f"[SlackQueue 📂] WARNING: No download URL found for file: {file_info.get('id')}")
            return None

        # Get the token directly instead of from the client object
        token = self.agent_tokens.get(agent_name) or self.agent_tokens.get("alfredo") or os.getenv("SLACK_BOT_TOKEN")
        if not token:
            print(f"[SlackQueue 📂] WARNING: No token found for {agent_name}. Cannot download.")
            return None

        # Mask token for logging: xoxb-123...456
        token_mask = f"{token[:9]}...{token[-4:]}" if len(token) > 10 else "invalid-token"
        print(f"[SlackQueue 📂] Using token ({token_mask}) for {agent_name} to download {filename}.", flush=True)

        save_dir = os.getenv("UPLOAD_DIR", os.path.abspath(os.path.join(os.getcwd(), "data/incoming_files")))
        os.makedirs(save_dir, exist_ok=True)

        # Ensure unique filename to avoid collisions
        unique_filename = f"{int(time.time())}_{filename}"
        file_path = os.path.join(save_dir, unique_filename)

        try:
            # 1. Try URL with Authorization Header (Modern)
            print(f"[SlackQueue 📂] Attempting Header Auth for {filename}...", flush=True)
            response = requests.get(url, headers={"Authorization": f"Bearer {token}"}, stream=True, timeout=30)
            
            # Check for success and not HTML
            first_chunk = next(response.iter_content(chunk_size=512), b"")
            is_html = b"<!DOCTYPE html>" in first_chunk or b"<html" in first_chunk

            if response.status_code == 200 and not is_html:
                with open(file_path, "wb") as f:
                    f.write(first_chunk)
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                print(f"[SlackQueue 📂] SUCCESS: {filename} downloaded via Header Auth.", flush=True)
                return file_path
            
            # 2. Try Fallback: Query Parameter Auth (Older/Alternative)
            print(f"[SlackQueue 📂] Header Auth failed or returned HTML. Attempting Query Param Auth...", flush=True)
            fallback_url = f"{url}?token={token}" if "?" not in url else f"{url}&token={token}"
            response = requests.get(fallback_url, stream=True, timeout=30)
            
            first_chunk = next(response.iter_content(chunk_size=512), b"")
            is_html = b"<!DOCTYPE html>" in first_chunk or b"<html" in first_chunk
            
            if response.status_code == 200 and not is_html:
                with open(file_path, "wb") as f:
                    f.write(first_chunk)
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                print(f"[SlackQueue 📂] SUCCESS: {filename} downloaded via Query Param Auth.", flush=True)
                return file_path
            
            print(f"[SlackQueue 📂] FATAL: Authentication failed with both patterns for {filename}. Response status: {response.status_code}. Content-Type: {response.headers.get('Content-Type')}", flush=True)
            return None
        except Exception as e:
            print(f"[SlackQueue 📂] WARNING: Error downloading file {filename}: {e}", flush=True)
            return None

    def format_agent_message(self, agent: str, text: str, actions: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
        """
        Formats a plain text agent message into a premium Block Kit layout.
        """
        emoji = AGENT_EMOJIS.get(agent.lower(), "🤖")
        header_text = f"{emoji} *{agent.capitalize()}*"
        
        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": header_text
                }
            },
            {
                "type": "divider"
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": text
                }
            }
        ]
        
        # Add context block (footer)
        app_env = os.getenv("APP_ENV", "production").capitalize()
        blocks.append({
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"_Env: {app_env} | Agent: {agent.capitalize()} | La Famiglia Core_"
                }
            ]
        })
        
        # Add actions if provided
        if actions:
            action_block = {
                "type": "actions",
                "elements": actions
            }
            blocks.append(action_block)
            
        return blocks

    def create_button(self, text: str, action_id: str, value: str = "1", style: Optional[str] = None) -> Dict[str, Any]:
        """Utility to create a Block Kit button."""
        btn = {
            "type": "button",
            "text": {
                "type": "plain_text",
                "text": text,
                "emoji": True
            },
            "action_id": action_id,
            "value": value
        }
        if style:
            btn["style"] = style # "primary" or "danger"
        return btn

    def enqueue_message(self, agent: str, channel: str, message: str, priority: int = PRIORITY_MEDIUM, blocks: Optional[List[Dict[str, Any]]] = None, **extra) -> Optional[str]:
        """Puts a message in the priority outgoing queue."""
        payload = {
            "agent": agent,
            "channel": channel,
            "message": message,
            "blocks": blocks,
            "priority": priority,
            "timestamp": time.time(),
            **extra
        }
        queue_key = f"{self.outgoing_queue_base}{priority}"
        self.redis.rpush(queue_key, json.dumps(payload))
        return None

    def post_message(self, agent: str, channel: str, message: str, thread_ts: Optional[str] = None, blocks: Optional[List[Dict[str, Any]]] = None) -> Optional[str]:
        """
        Sends a message to Slack immediately and synchronously.
        Returns the Slack message 'ts' (timestamp) on success, or None on failure.
        """
        payload = {
            "agent": agent,
            "channel": channel,
            "message": message,
            "blocks": blocks,
            "priority": PRIORITY_CRITICAL, # Treat as immediate
            "thread_ts": thread_ts,
            "timestamp": time.time()
        }
        return self._send_to_slack(payload, thread_ts=thread_ts)

    def _process_queue(self):
        while self.running:
            item = self._dequeue_next()
            
            # Process any pending batches if interval reached
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
                # Add to batch (Threading is disabled for batches currently as they aggregate messages)
                thread_ts = payload.get("thread_ts")
                batch_key = (channel, priority, thread_ts)
                if not self.batches[batch_key]:
                    self.last_batch_time[batch_key] = time.time()
                self.batches[batch_key].append(payload)

    def _flush_batches(self):
        """Checks if any batches are ready to be sent"""
        now = time.time()
        for batch_key, messages in list(self.batches.items()):
            if not messages: continue
            
            channel, priority, thread_ts = batch_key
            interval = BATCH_INTERVALS.get(priority, 30)
            
            if now - self.last_batch_time.get(batch_key, 0) >= interval:
                self._send_batch(channel, priority, messages, thread_ts=thread_ts)
                self.batches[batch_key] = []
                self.last_batch_time[batch_key] = now

    def _send_immediately(self, payload: dict):
        channel = payload["channel"]
        thread_ts = payload.get("thread_ts")
        self._rate_limit(channel)
        self._send_to_slack(payload, thread_ts=thread_ts)

    def _send_batch(self, channel: str, priority: int, messages: List[dict], thread_ts: Optional[str] = None):
        if not messages: return
        
        # Send messages directly without technical header
        ts = thread_ts
        for msg in messages:
            self._rate_limit(channel)
            ts = self._send_to_slack(msg, thread_ts=ts)

    def upload_file(self, agent: str, channel: str, file_path: str, title: Optional[str] = None, initial_comment: Optional[str] = None, thread_ts: Optional[str] = None) -> bool:
        """
        Uploads a file to Slack using files_upload_v2.
        """
        client = self.clients.get(agent.lower()) or self.clients.get("alfredo")
        if not client:
            return False
            
        try:
            print(f"[{agent}] Uploading file {file_path} to {channel}...")
            client.files_upload_v2(
                channel=channel,
                file=file_path,
                title=title or os.path.basename(file_path),
                initial_comment=initial_comment,
                thread_ts=thread_ts
            )
            return True
        except SlackApiError as e:
            print(f"[{agent}] Slack API error during upload: {e.response['error']}")
            return False
        except Exception as e:
            print(f"[{agent}] Error during file upload: {e}")
            return False

    def _send_to_slack(self, payload: dict, thread_ts: Optional[str] = None) -> Optional[str]:
        agent_name = payload.get("agent", "system").lower()
        channel = payload.get("channel")
        message = payload.get("message")
        
        # Handle file upload if present
        file_path = payload.get("file_path")
        if file_path:
            self.upload_file(
                agent=agent_name,
                channel=channel,
                file_path=file_path,
                title=payload.get("file_title"),
                initial_comment=message,
                thread_ts=thread_ts
            )
            return "file_uploaded"

        # Determine client (fallback to alfredo for system messages or if agent client missing)
        client = self.clients.get(agent_name)
        
        if not client and agent_name != "system":
            # Attempt a lazy refresh if the client is missing (e.g. provisioned after start)
            print(f"[SlackQueue 🔍] Client for '{agent_name}' missing in cache. Attempting DB refresh...")
            refreshed_id = self.refresh_bot_id(agent_name)
            if refreshed_id:
                client = self.clients.get(agent_name)
            
            if not client:
                if agent_name != "alfredo":
                    print(f"[SlackQueue] WARNING: No client for agent '{agent_name}'. Falling back to 'alfredo'.")
                    client = self.clients.get("alfredo")
                else:
                    print(f"[SlackQueue] WARNING: Alfredo client is missing from cache.")
        elif not client:
            client = self.clients.get("alfredo")
        
        if channel != "system":
            # Direct message or channel post, just send the message content
            formatted_message = message
        else:
            # For system/mock logs, we can keep the prefix for clarity in logs
            formatted_message = f"[{agent_name.capitalize()}]: {message}"
        
        if client:
            try:
                # Use blocks if provided, fallback to text
                blocks = payload.get("blocks")
                
                if blocks:
                    response = client.chat_postMessage(
                        channel=channel,
                        text=message, # Fallback text for notifications
                        blocks=blocks,
                        thread_ts=thread_ts
                    )
                else:
                    response = client.chat_postMessage(
                        channel=channel,
                        text=formatted_message,
                        thread_ts=thread_ts
                    )
                return response["ts"]
            except SlackApiError as e:
                print(f"[{agent_name}] Slack API error: {e.response['error']}")
                return None
        else:
            print(f"MOCK SLACK SEND [{agent_name}] -> {channel} (Thread: {thread_ts}): {formatted_message}")
            return str(time.time())

    def start_worker(self):
        """Standard parameterless start for the backend main loop."""
        super().start_worker(self._process_queue)
# Singleton instance
slack_queue = SlackQueueClient()
