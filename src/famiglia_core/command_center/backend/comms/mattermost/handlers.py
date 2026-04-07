import os
import time
import json
import traceback
from typing import Optional
from famiglia_core.command_center.backend.comms.mattermost.client import mattermost_queue
from famiglia_core.command_center.backend.utils import LLM_SEMAPHORE
from famiglia_core.agents.base_agent import BaseAgent

def process_mattermost_event(
    agent_obj: BaseAgent,
    event: dict,
    bot_id: str,
    ack_emoji: str,
    app_env: str,
):
    """
    Process a single incoming Mattermost event.
    """
    try:
        # Mattermost events from websocket are often 'posted' events
        if event.get('event') != 'posted':
            return

        data = event.get('data', {})
        if isinstance(data, str):
            data = json.loads(data)
        
        post_data = data.get('post')
        if not post_data: 
            print(f"[Mattermost] [{agent_obj.name}] No post data in event: {event.get('event')}")
            return
        
        post = post_data
        if isinstance(post, str):
            post = json.loads(post)

        post_id = post.get('id')
        channel_id = post.get('channel_id')
        sender_id = post.get('user_id')
        message = post.get('message', '')
        root_id = post.get('root_id') or post.get('id')

        print(f"[Mattermost] [{agent_obj.name}] Processing post {post_id} from {sender_id} in {channel_id}: {message[:50]}...")

        # 1. Filtering
        if sender_id == bot_id:
            return

        # 1.5 Immediate acknowledgment with reaction
        print(f"[{agent_obj.name}] [Mattermost] Adding reaction to {post_id} in {channel_id}...")
        mattermost_queue.add_reaction(agent_obj.agent_id, post_id, ack_emoji)

        # 1.6 Handle files
        file_ids = post.get('file_ids', [])
        if file_ids:
            file_paths = []
            for f_id in file_ids:
                local_path = mattermost_queue.download_file(f_id, agent_obj.agent_id)
                if local_path:
                    file_paths.append(local_path)
            
            if file_paths:
                file_meta = "\n".join([f"[Attached File]: {p}" for p in file_paths])
                message = f"{message}\n\n{file_meta}"

        # 2. Processing logic
        # Resolve sender name
        sender_name = mattermost_queue.resolve_sender_name(sender_id, agent=agent_obj.agent_id)
        sender_context = f"{sender_name} (Mattermost:{sender_id})"

        conversation_key = f"mattermost:{channel_id}:{root_id}:{sender_id}"

        def on_intermediate(text: str):
            mattermost_queue.enqueue_message(
                agent=agent_obj.agent_id,
                channel_id=channel_id,
                message=text,
                root_id=root_id,
                priority=1,
            )

        # 3. Gated LLM completion
        print(f"[{agent_obj.name}] [Mattermost] Waiting for LLM slot for request from {sender_name}...")
        response = None
        try:
            with LLM_SEMAPHORE:
                response = agent_obj.complete_task(
                    message,
                    sender=sender_context,
                    conversation_key=conversation_key,
                    on_intermediate_response=on_intermediate,
                )
        except Exception as e:
            print(f"[{agent_obj.name}] [Mattermost] CRITICAL ERROR in complete_task: {e}")
            traceback.print_exc()
            response = f"I'm sorry, I encountered a critical internal error while processing your Mattermost request: {e}"

        if response:
            mattermost_queue.enqueue_message(
                agent=agent_obj.agent_id,
                channel_id=channel_id,
                message=response,
                root_id=root_id,
                priority=2,
            )
    except Exception as e:
        print(f"[Mattermost ❌] [{agent_obj.name}] Error processing event: {e}")
        traceback.print_exc()

def incoming_event_worker(agents: dict, ack_emoji: str, app_env: str):
    """Background thread that pulls events from Redis and processes them in parallel."""
    from concurrent.futures import ThreadPoolExecutor
    print("[MattermostWorker] Started.")
    
    with ThreadPoolExecutor(max_workers=50) as executor:
        while True:
            try:
                payload = mattermost_queue.dequeue_incoming()
                if not payload:
                    time.sleep(0.1)
                    continue

                event = payload.get("event")
                agent_id = payload.get("agent_id")
                bot_id = payload.get("bot_id")
                
                agent_obj = agents.get(agent_id)
                if agent_obj:
                    executor.submit(
                        process_mattermost_event,
                        agent_obj=agent_obj,
                        event=event,
                        bot_id=bot_id,
                        ack_emoji=ack_emoji,
                        app_env=app_env,
                    )
            except Exception as e:
                print(f"[MattermostWorker] Loop Error: {e}")
                time.sleep(1)
