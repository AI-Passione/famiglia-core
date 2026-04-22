import os
import re
import time
import json
import traceback
from typing import Optional, List, Set, Any
from slack_bolt import App
from famiglia_core.command_center.backend.comms.slack.client import slack_queue
from famiglia_core.command_center.backend.utils import LLM_SEMAPHORE
from famiglia_core.agents.base_agent import BaseAgent

def should_handle_message(app_env: str, channel: str, dev_channel_id: Optional[str]) -> bool:
    """
    Determine if the current instance should handle a message based on the environment.
    - In production: handle everything EXCEPT the dev channel.
    - In development: handle ONLY the dev channel.
    """
    if not dev_channel_id:
        # If no dev channel is configured, we can't distinguish. Default to handle.
        return True

    is_dev_channel = (channel == dev_channel_id)
    if app_env.lower() == "development":
        return is_dev_channel
    else:
        # Default to production behavior: ignore dev channel
        return not is_dev_channel

LEADING_RAW_SLACK_ID_RE = re.compile(r"^\s*(?:<@U[A-Z0-9]+>|@U[A-Z0-9]+)[,\-:]*\s*")
RAW_SLACK_ID_RE = re.compile(r"(?<!<)@(?P<id>U[A-Z0-9]+)")

def _format_reply_for_sender(response: str, sender_user_id: Optional[str]) -> str:
    """Ensure replies mention the actual requester instead of hallucinated IDs."""
    text = (response or "").strip()
    if not text:
        return ""
    if not sender_user_id:
        return text

    # Normalize raw @U... to Slack mention format first.
    text = RAW_SLACK_ID_RE.sub(r"<@\g<id>>", text)
    expected_mention = f"<@{sender_user_id}>"
    
    # Append environment footer
    app_env = os.getenv("APP_ENV", "production").capitalize()
    footer = f"\n\n_Env: {app_env}_"
    text = f"{text}{footer}"

    if text.startswith(expected_mention):
        return text

    # Drop any incorrect leading mention and prepend the true sender mention.
    text = LEADING_RAW_SLACK_ID_RE.sub("", text)
    return f"{expected_mention} {text}".strip()

def _strip_bot_mention(text: str, bot_user_id: Optional[str]) -> str:
    """Remove the current bot mention from Slack message text."""
    cleaned = (text or "").strip()
    if not bot_user_id:
        return cleaned
    pattern = rf"<@{re.escape(bot_user_id)}(?:\|[^>]+)?>"
    return re.sub(pattern, "", cleaned).strip()

def should_process_message_event(
    event: dict,
    current_bot_id: str,
    app_env: str,
    is_dev_channel: bool,
    known_bot_user_ids: Optional[Set[str]] = None,
) -> bool:
    """
    Decide whether a generic Slack `message` event should be treated like a command.
    """
    if event.get("subtype") or event.get("bot_id"):
        return False

    user_id = event.get("user")
    if user_id and known_bot_user_ids and user_id in known_bot_user_ids:
        return False

    text = event.get("text", "")
    is_direct_message = event.get("channel_type") == "im"
    
    # Robust mention detection (catches <@U123> and <@U123|name>)
    mention_pattern = r"<@(?P<id>[A-Z0-9]+)(?:\|[^>]+)?>"
    mentioned_ids = set(match.group("id") for match in re.finditer(mention_pattern, text))
    
    is_direct_mention = current_bot_id in mentioned_ids

    # Agent Discipline: If ANY known bot is mentioned, we ONLY proceed if WE are mentioned.
    if known_bot_user_ids:
        other_bots_mentioned = mentioned_ids.intersection(known_bot_user_ids)
        if other_bots_mentioned and current_bot_id not in other_bots_mentioned:
            # Another bot was explicitly tagged, and we were not. Stay out of it.
            return False

    is_dev_thread_reply = (
        app_env.lower() == "development"
        and bool(event.get("thread_ts"))
        and is_dev_channel
    )

    should_handle = is_direct_message or is_direct_mention or is_dev_thread_reply
    
    if not should_handle:
        print(f"[Filter] ⏩ Ignored event for bot {current_bot_id}: DM={is_direct_message}, Mention={is_direct_mention}, DevThread={is_dev_thread_reply}", flush=True)
    else:
        print(f"[Filter] ✅ Processing event for bot {current_bot_id}: (Type: {event.get('type')})", flush=True)

    return should_handle

def process_incoming_event(
    agent_obj: BaseAgent,
    event: dict,
    bot_id: str,
    ack_emoji: str,
    app_env: str,
    dev_channel_id: Optional[str],
    slack_client: Optional[App] = None,
):
    """
    Process a single incoming Slack event. Performs filtering and 
    reaction in the background to keep listeners non-blocking.
    """
    channel = event.get("channel")
    ts = event.get("ts")
    user = event.get("user")
    
    # 1. Thread-safe Filtering
    is_dev_channel_bool = slack_queue.is_dev_channel(channel)
    known_bot_user_ids = set(slack_queue.bot_id_to_name.keys())
    
    is_mention = event.get("type") == "app_mention"
    if not is_mention:
        if not should_process_message_event(
            event=event,
            current_bot_id=bot_id,
            app_env=app_env,
            is_dev_channel=is_dev_channel_bool,
            known_bot_user_ids=known_bot_user_ids,
        ):
            return

    if app_env.lower() != "development" and is_dev_channel_bool:
        return

    if not should_handle_message(app_env, channel, dev_channel_id):
        return

    # 3. Resilient Join & Immediate acknowledgement with reaction
    client_to_use = (slack_client.client if slack_client else None) or slack_queue.clients.get(agent_obj.agent_id)
    
    if client_to_use and channel and ts:
        try:
            # 3a. Ensure we are in the channel (Required for public channels to react/post)
            if not is_mention and not event.get("channel_type") == "im":
                # Regular message flow: we might not be in the channel
                try:
                    # We check if we are in by trying to get info or just join (join is idempotent for public)
                    print(f"[Acknowledge] {agent_obj.name} ensuring channel membership in {channel}")
                    client_to_use.conversations_join(channel=channel)
                except Exception as je:
                    print(f"[Acknowledge] {agent_obj.name} join failed (might be private/already in): {je}")

            # 3b. Add reaction
            print(f"[Acknowledge] {agent_obj.name} reacting with :{ack_emoji}: to msg {ts} in {channel}", flush=True)
            client_to_use.reactions_add(
                name=ack_emoji,
                channel=channel,
                timestamp=ts
            )
            print(f"[Acknowledge] ✅ {agent_obj.name} successfully reacted.", flush=True)
        except Exception as e:
            print(f"[Acknowledge] ❌ {agent_obj.name} reaction failed: {e}", flush=True)
            if "already_reacted" not in str(e):
                print(f"[Acknowledge] {agent_obj.name} failed to add reaction/join: {e}")
    else:
        print(f"[Acknowledge] Skipping reaction for {agent_obj.name}: client={bool(client_to_use)}, channel={channel}, ts={ts}")

    # 4. Processing logic
    text = event.get("text", "")
    
    # Handle files
    files = event.get("files", [])
    if files:
        file_paths = []
        for f_info in files:
            local_path = slack_queue.download_file(f_info, agent_obj.agent_id)
            if local_path:
                file_paths.append(local_path)
        
        if file_paths:
            file_meta = "\n".join([f"[Attached File]: {p}" for p in file_paths])
            text = f"{text}\n\n{file_meta}"

    clean_text = _strip_bot_mention(text, bot_id)

    # Identify speaker
    sender_name = slack_queue.resolve_sender_name(user, event=event)
    sender_context = f"{sender_name} (<@{user}>)" if user else sender_name

    reply_ts = event.get("thread_ts") or ts
    conversation_key = f"slack:{channel}:{reply_ts}:{user or 'unknown'}"

    def on_intermediate(text: str):
        formatted = _format_reply_for_sender(text, user)
        slack_queue.enqueue_message(
            agent=agent_obj.agent_id,
            channel=channel,
            message=formatted,
            thread_ts=reply_ts,
            priority=1,
        )

    # 5. Gated LLM completion
    print(f"[{agent_obj.name}] Waiting for LLM slot for request from {sender_name}...")
    try:
        # Prepare metadata for ResponseDistributor
        metadata = {
            "slack_channel": channel,
            "slack_thread_ts": reply_ts,
            "platform": "slack"
        }
        
        with LLM_SEMAPHORE:
            # Distributor inside complete_task (_finalize_response) will handle the response
            agent_obj.complete_task(
                clean_text,
                sender=sender_context,
                conversation_key=conversation_key,
                on_intermediate_response=on_intermediate,
                metadata=metadata
            )
    except Exception as e:
        print(f"[{agent_obj.name}] CRITICAL ERROR in complete_task: {e}")
        traceback.print_exc()
        error_msg = f"I'm sorry, Don Jimmy. I encountered a critical internal error while processing your request: {e}"
        # For terminal persistence & Slack mirror of the error
        from famiglia_core.command_center.backend.api.services.response_distributor import response_distributor
        response_distributor.dispatch(
            agent_id=agent_obj.agent_id,
            text=error_msg,
            conversation_key=conversation_key,
            sender=agent_obj.name,
            metadata={"slack_channel": channel, "slack_thread_ts": reply_ts}
        )

def process_incoming_action(
    agent_obj: BaseAgent,
    event: dict,
    bot_id: str,
    slack_client: Optional[App] = None,
):
    """
    Process an interactive action (button click, menu selection).
    """
    actions = event.get("actions", [])
    if not actions:
        return

    user = event.get("user", {}).get("id")
    channel = event.get("channel", {}).get("id")
    action = actions[0]
    action_id = action.get("action_id")
    
    print(f"[{agent_obj.name}] Processing action {action_id} from user {user}")
    
    # Handle specific actions
    if action_id == "approve_task":
        # Example logic: trigger a task completion or approval
        slack_queue.post_message(
            agent=agent_obj.agent_id,
            channel=channel,
            message=f"I have received your approval, Don Jimmy. Proceeding at once.",
            thread_ts=event.get("container", {}).get("message_ts")
        )
    elif action_id == "famiglia_status":
        # Handled by command, but could be a button too
        pass
    else:
        # Generic action handling or fallback
        slack_queue.post_message(
            agent=agent_obj.agent_id,
            channel=channel,
            message=f"Action '{action_id}' acknowledged. I'm on it.",
            thread_ts=event.get("container", {}).get("message_ts")
        )

def process_incoming_command(
    agent_obj: BaseAgent,
    event: dict,
    bot_id: str,
    slack_client: Optional[App] = None,
):
    """
    Process a slash command.
    """
    command = event.get("command")
    user = event.get("user_id")
    channel = event.get("channel_id")
    text = event.get("text", "")
    
    print(f"[{agent_obj.name}] Processing command {command} with text: {text}")
    
    if command == "/famiglia":
        # Create a "Cockpit" block
        status_blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "🏟 *La Famiglia Status Cockpit*"
                }
            },
            {
                "type": "divider"
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": "💳 *Vito:* Vigilant"},
                    {"type": "mrkdwn", "text": "🎩 *Alfredo:* Coordinating"},
                    {"type": "mrkdwn", "text": "🔧 *Riccardo:* Optimizing"},
                    {"type": "mrkdwn", "text": "🔬 *Rossini:* Researching"}
                ]
            },
            {
                "type": "context",
                "elements": [
                    {"type": "mrkdwn", "text": "All systems operational. _La Passione_ vibe is high."}
                ]
            }
        ]
        
        slack_queue.post_message(
            agent=agent_obj.agent_id,
            channel=channel,
            message="Famiglia Status",
            blocks=status_blocks
        )

def incoming_event_worker(agents: dict, apps: dict, ack_emoji: str, app_env: str, dev_channel_id: Optional[str]):
    """Background thread that pulls events from Redis and processes them in parallel."""
    from concurrent.futures import ThreadPoolExecutor
    print("[IncomingWorker] Started.")
    
    with ThreadPoolExecutor(max_workers=50) as executor:
        while True:
            try:
                payload = slack_queue.dequeue_incoming()
                if not payload:
                    time.sleep(0.1)
                    continue
                
                event_type = payload.get("event_type", "event")
                event = payload.get("event")
                agent_id = payload.get("agent_id")
                bot_id = payload.get("bot_id")
                
                print(f"[IncomingWorker] Dequeued {event_type} for {agent_id}")

                agent_obj = agents.get(agent_id)
                slack_app = apps.get(agent_id)
                
                if not agent_obj:
                    continue

                if event_type == "action":
                    executor.submit(
                        process_incoming_action,
                        agent_obj=agent_obj,
                        event=event,
                        bot_id=bot_id,
                        slack_client=slack_app,
                    )
                elif event_type == "command":
                    executor.submit(
                        process_incoming_command,
                        agent_obj=agent_obj,
                        event=event,
                        bot_id=bot_id,
                        slack_client=slack_app,
                    )
                else:
                    executor.submit(
                        process_incoming_event,
                        agent_obj=agent_obj,
                        event=event,
                        bot_id=bot_id,
                        ack_emoji=ack_emoji,
                        app_env=app_env,
                        dev_channel_id=dev_channel_id,
                        slack_client=slack_app,
                    )
            except Exception as e:
                print(f"[IncomingWorker] Loop Error: {e}")
                time.sleep(1)
