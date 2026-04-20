import os
import time
import re
import json
import asyncio
import threading
from typing import Optional, List
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from dotenv import load_dotenv

# Load configuration from .env as early as possible
load_dotenv()

from famiglia_core.command_center.backend.comms.slack.client import slack_queue
from famiglia_core.db.agents.context_store import context_store
from famiglia_core.db.init_db import init_db
from famiglia_core.agents.alfredo import Alfredo
from famiglia_core.agents.vito import Vito
from famiglia_core.agents.riccardo import Riccardo
from famiglia_core.agents.rossini import Rossini
from famiglia_core.agents.tommy import Tommy
from famiglia_core.agents.bella import Bella
from famiglia_core.agents.kowalski import Kowalski
from famiglia_core.agents.llm.client import client
from famiglia_core.agents.llm.models_registry import get_all_models, TASK_ROUTING
from famiglia_core.agents.orchestration.scheduler import task_orchestrator
from famiglia_core.agents.base_agent import (
    BaseAgent, 
    TASK_TYPE_ALFREDO_GREETING, 
    TASK_TYPE_MARKET_RESEARCH
)
from famiglia_core.agents.orchestration.utils.task_helpers import TASK_TYPE_PRD_AUTOSCAN
from famiglia_core.command_center.backend.utils import LLM_SEMAPHORE
from famiglia_core.command_center.backend.comms.slack.handlers import (
    incoming_event_worker as slack_worker, 
    process_incoming_event, 
    should_handle_message
)

apps = {} # Global registry for Socket Mode apps

def main():
    print("🎩 Starting Passione Inc. Agent Famiglia...")
    global apps
    
    ack_emoji = os.getenv("SLACK_ACK_EMOJI", "eyes")
    app_env = os.getenv("APP_ENV", "production").lower()
    raw_dev_channel = os.getenv("DEV_CHANNEL_ID")
    dev_channel_id = slack_queue.resolve_channel_id(raw_dev_channel)
    
    if app_env != "development" and not dev_channel_id:
        pass

    # 0. Wait for Ollama service
    print("\n[Startup] Synchronizing with Ollama service...")
    max_wait = 30
    ready = False
    for i in range(max_wait):
        if client._is_ollama_service_available():
            ready = True
            break
        print(f"[Startup] Waiting for Ollama to stabilize... ({i+1}/{max_wait})")
        time.sleep(1)
    
    if not ready:
        print("[Startup] WARNING: Ollama service not reachable.")

    # 1. Ensure local Ollama fallback is ready
    client.ensure_ollama_ready(auto_pull=True)

    # 2. Initialize DB
    init_db()

    # 3. Register Agents
    agents = {
        "alfredo": Alfredo(),
        "vito": Vito(),
        "riccardo": Riccardo(),
        "rossini": Rossini(),
        "tommy": Tommy(),
        "bella": Bella(),
        "kowalski": Kowalski()
    }
    
    # Register recurring tasks
    recurring_tasks = context_store.list_recurring_tasks()
    if not any(t["title"].startswith("Daily Greeting") for t in recurring_tasks):
        context_store.create_recurring_task(
            title="Daily Greeting & Status Overview",
            task_payload="Greet Don Jimmy and show the latest scheduled task status.",
            schedule_config={"days": [0, 1, 2, 3, 4], "hour": 9, "minute": 0},
            expected_agent="alfredo",
            priority="high",
            metadata={"task_type": TASK_TYPE_ALFREDO_GREETING}
        )
        
    print(f"Registered {len(agents)} agents: {', '.join(agents.keys())}")

    # Start autonomous orchestration
    scheduled_enabled = os.getenv("SCHEDULED_TASKS_ENABLED", "true").lower() == "true"
    if scheduled_enabled:
        task_orchestrator.configure(agents)

    # 3.5 Pull models
    print("\n[Registry] Ensuring all registered models are installed...")
    if client._is_ollama_service_available():
        for model_entry in get_all_models():
            tag = model_entry["tag"]
            client._ensure_model_pulled(tag, host=client.ollama_host)
    
    # Emission of readiness signal
    try:
        with open("/tmp/famiglia_engine_ready", "w") as f:
            f.write("ready")
    except OSError:
        pass

    # 4. Start Slack Worker
    print("Starting Slack message queue worker...")
    slack_queue.start_worker()
    
    # 5. Start Socket Mode Handlers
    app_token = slack_queue.app_token
    handlers = []
    
    def setup_agent_events(current_app, current_agent_id, current_bot_id):
        def enqueue_event(event):
            print(f"[{current_agent_id}] Received event {event.get('ts')}, enqueuing...")
            payload = {
                "event": event,
                "agent_id": current_agent_id,
                "bot_id": current_bot_id
            }
            slack_queue.enqueue_incoming(payload)

        @current_app.event("app_mention")
        def handle_mention(event, say):
            enqueue_event(event)

        @current_app.event("message")
        def handle_messages(event, say):
            enqueue_event(event)
        
        @current_app.action(re.compile(".*"))
        def handle_actions(ack, body, say):
            ack()
            payload = {"event": body, "agent_id": current_agent_id, "bot_id": current_bot_id, "event_type": "action"}
            slack_queue.enqueue_incoming(payload)
    
    # 4a. Initial Listeners
    for agent_id, token in slack_queue.agent_tokens.items():
        agent_app_token = slack_queue.agent_app_tokens.get(agent_id) or app_token
        if not token or not agent_app_token: continue
            
        bot_id = slack_queue.bot_ids.get(agent_id)
        if not bot_id: continue
            
        transport = slack_queue.agent_transports.get(agent_id, "socket")
        if transport == "http":
            print(f"[{agent_id}] HTTP Mode active. skipping socket listener.")
            continue

        print(f"Initializing listener for {agent_id}...")
        app = App(token=token)
        setup_agent_events(app, agent_id, bot_id)
        apps[agent_id] = app
        
        handler = SocketModeHandler(app, agent_app_token)
        handler.connect()
        handlers.append(handler)

    def dynamic_listener_watcher():
        nonlocal handlers
        while True:
            time.sleep(10)
            try:
                from famiglia_core.db.tools.user_connections_store import user_connections_store
                db_bot_tokens = user_connections_store.list_connections("slack_bot:")
                db_socket_tokens = user_connections_store.list_connections("slack_socket:")
                
                for service, conn in db_bot_tokens.items():
                    agent_id = service.replace("slack_bot:", "")
                    token = conn["access_token"]
                    socket_token = db_socket_tokens.get(f"slack_socket:{agent_id}", {}).get("access_token")
                    
                    if not socket_token or agent_id in apps:
                        continue
                    
                    creds_conn = user_connections_store.get_connection(f"slack_creds:{agent_id}")
                    transport = "socket"
                    if creds_conn:
                        try:
                            cdata = json.loads(creds_conn["access_token"])
                            transport = cdata.get("transport", "socket")
                        except (json.JSONDecodeError, KeyError, TypeError):
                            # Invalid/missing stored creds payload: keep default "socket" transport.
                            pass
                    
                    if transport == "http":
                        print(f"[DynamicWatcher] {agent_id} is in HTTP mode.")
                        slack_queue.agent_tokens[agent_id] = token
                        apps[agent_id] = "bridge_active"
                        continue

                    print(f"[DynamicWatcher] Starting listener for {agent_id}...")
                    slack_queue.agent_tokens[agent_id] = token
                    slack_queue.agent_app_tokens[agent_id] = socket_token
                    
                    from slack_sdk import WebClient
                    client_tmp = WebClient(token=token)
                    auth = client_tmp.auth_test()
                    bot_id = auth["user_id"]
                    
                    slack_queue.clients[agent_id] = client_tmp
                    slack_queue.bot_ids[agent_id] = bot_id
                    
                    app = App(token=token)
                    setup_agent_events(app, agent_id, bot_id)
                    apps[agent_id] = app
                    
                    handler = SocketModeHandler(app, socket_token)
                    handler.connect()
                    handlers.append(handler)
            except Exception as e:
                print(f"[DynamicWatcher] Error while updating listeners: {e}")

    watcher_thread = threading.Thread(target=dynamic_listener_watcher, daemon=True)
    watcher_thread.start()

    # Incoming Worker
    incoming_worker_thread = threading.Thread(
        target=slack_worker,
        args=(agents, apps, ack_emoji, app_env, dev_channel_id),
        daemon=True
    )
    incoming_worker_thread.start()
    
    if scheduled_enabled:
        task_orchestrator.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Shutting down...")
        for h in handlers:
            h.disconnect()
        task_orchestrator.stop()
        slack_queue.stop_worker()

if __name__ == "__main__":
    main()
