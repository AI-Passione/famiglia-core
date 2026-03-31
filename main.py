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
from mattermostdriver.websocket import Websocket

from famiglia_core.command_center.backend.slack.client import slack_queue
from famiglia_core.command_center.backend.mattermost.client import mattermost_queue
from famiglia_core.db.agents.context_store import context_store
from famiglia_core.db.init_db import init_db
from famiglia_core.agents.alfredo import Alfredo
from famiglia_core.agents.vito import Vito
from famiglia_core.agents.riccado import Riccado
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
from famiglia_core.command_center.backend.slack.handlers import (
    incoming_event_worker as slack_worker, 
    process_incoming_event, 
    should_handle_message
)
from famiglia_core.command_center.backend.mattermost.handlers import (
    incoming_event_worker as mm_worker, 
    process_mattermost_event
)

# load configuration from .env as early as possible so that any module
# importing slack_queue (which constructs its singleton immediately) can
# read the proper tokens.  main() also calls load_dotenv again later for
# good measure.
load_dotenv()

apps = {} # Global registry for Socket Mode apps


def main():
    print("🎩 Starting Passione Inc. Agent Famiglia...")
    global apps
    
    load_dotenv()
    ack_emoji = os.getenv("SLACK_ACK_EMOJI", "eyes")
    app_env = os.getenv("APP_ENV", "production").lower()
    raw_dev_channel = os.getenv("DEV_CHANNEL_ID")
    dev_channel_id = slack_queue.resolve_channel_id(raw_dev_channel)
    
    print(
        f"[{app_env.upper()} MODE] Initialized with DEV_CHANNEL_ID={raw_dev_channel} "
        f"(resolved={dev_channel_id})"
    )
    if app_env != "development" and not dev_channel_id:
        print("[PRODUCTION MODE] DEV channel ID unresolved; using runtime channel-name guard for #_dev.")

    # 1. Ensure local Ollama fallback is ready
    client.ensure_ollama_ready(auto_pull=True)

    # 2. Initialize DB
    init_db()

    # 3. Register Agents
    agents = {
        "alfredo": Alfredo(),
        "vito": Vito(),
        "riccado": Riccado(),
        "rossini": Rossini(),
        "tommy": Tommy(),
        "bella": Bella(),
        "kowalski": Kowalski()
    }
    
    # Register the Weekday Greeting task if it doesn't exist
    recurring_tasks = context_store.list_recurring_tasks()
    if not any(t["title"].startswith("Daily Greeting") for t in recurring_tasks):
        context_store.create_recurring_task(
            title="Daily Greeting & Status Overview",
            task_payload="Greet Don Jimmy and show the latest scheduled task status.",
            schedule_config={"days": [0, 1, 2, 3, 4], "hour": 9, "minute": 0}, # Mon-Fri 9am
            expected_agent="alfredo",
            priority="high",
            metadata={"task_type": TASK_TYPE_ALFREDO_GREETING}
        )
        
    if not any(t["title"].startswith("Weekly Competitive Intelligence") for t in recurring_tasks):
        context_store.create_recurring_task(
            title="Weekly Competitive Intelligence & Market Trends",
            task_payload="Perform market research on the latest trends in autonomous AI agents for enterprise efficiency.",
            schedule_config={"days": [0], "hour": 10, "minute": 0}, # Mondays at 10am
            expected_agent="rossini",
            priority="medium",
            metadata={"task_type": TASK_TYPE_MARKET_RESEARCH}
        )
    print(f"Registered {len(agents)} agents: {', '.join(agents.keys())}")
    
    if not any(t["title"].startswith("Daily PRD Feedback Scan") for t in recurring_tasks):
        context_store.create_recurring_task(
            title="Daily PRD Feedback Scan",
            task_payload="Scan all Notion PRDs for unaddressed comments (where the last comment is from a human) and address them.",
            schedule_config={"days": [0, 1, 2, 3, 4], "hour": 9, "minute": 30},
            expected_agent="rossini",
            priority="medium",
            metadata={"task_type": TASK_TYPE_PRD_AUTOSCAN}
        )

    # 3.25 Start autonomous scheduled task execution + control panel
    scheduled_enabled = os.getenv(
        "SCHEDULED_TASKS_ENABLED",
        os.getenv("BATCHED_TASKS_ENABLED", "true"),
    ).strip().lower() not in {
        "0",
        "false",
        "no",
    }
    if scheduled_enabled:
        task_orchestrator.configure(agents)
        task_orchestrator.start()
    else:
        print("[ScheduledTasks] Disabled by configuration.")
    
    # 3.5 Pre-pull agent fallback models
    print("Ensuring agent local models are allocated and pulled if RAM permits...")
    client.allocate_resources(list(agents.values()))

    # 3.5b Pull ALL models declared in models.json (registry-driven)
    # This ensures newly-added models (e.g. deepseek-r1:7b) are installed on
    # first boot without any manual ollama pull.
    print("\n[Registry] Ensuring all registered models are installed...")
    for model_entry in get_all_models():
        tag = model_entry["tag"]
        desc = model_entry.get("description", "")
        print(f"[Registry]   Checking {tag} ({desc})")
        if client._is_ollama_service_available():
            client._ensure_model_pulled(tag, host=client.ollama_host)
        if client._is_remote_ollama_available():
            client._ensure_model_pulled(tag, host=client.ollama_remote_host)

    
    # 3.6 Display Famiglia Model Readiness Report
    print("\n" + "="*52)
    print("      🇮🇹  FAMIGLIA MODEL READINESS REPORT  🇮🇹")
    print("="*52)
    report = client.get_model_status_report()
    for model, status in report.items():
        local_s  = "✅ INSTALLED" if status["local"]  else "❌ MISSING"
        remote_s = "✅ INSTALLED" if status["remote"] else "❌ MISSING"
        print(f"Model: {model:25} | Local: {local_s:12} | Remote: {remote_s:12}")
    print("="*52)

    # 3.7 Display Task Routing Table (driven by models_registry)
    print("\n      ⚙️   TASK ROUTING TABLE  ⚙️")
    print("-"*52)
    registered = {m["tag"]: m["description"] for m in get_all_models()}
    for task_mode, model_tag in TASK_ROUTING.items():
        desc = registered.get(model_tag, "")
        print(f"  {task_mode:<8} → {model_tag:<25} {desc}")
    print("="*52 + "\n")
    
    # 4. Start Slack Worker
    print("Starting Slack message queue worker...")
    slack_queue.start_worker()
    
    # 5. Start Socket Mode Handlers for all bots
    app_token = slack_queue.app_token
    handlers = []
    
    # 4a. Start Agent Listeners
    for agent_id, token in slack_queue.agent_tokens.items():
        # Get specific app token for this agent, fallback to global one
        agent_app_token = slack_queue.agent_app_tokens.get(agent_id) or app_token
        
        if not token:
            print(f"[{agent_id}] no bot token found; listener will not start.")
            continue
        if not agent_app_token:
            print(f"[{agent_id}] no app token found; listener will not start.")
            continue
            
        bot_id = slack_queue.bot_ids.get(agent_id)
        if not bot_id:
            print(f"[{agent_id}] authentication failed or bot_id missing; listener will not start.")
            continue

        print(f"Initializing listener for {agent_id} ({bot_id})...")
        app = App(token=token)
        
        # Route mentions to the specific agent
        agent_obj = agents.get(agent_id)
        if agent_obj:
            def setup_agent_events(current_app, current_agent_id, current_bot_id):
                def enqueue_event(event):
                    # Enqueue for background processing. 
                    # We return as fast as possible to Slack to avoid dropping events.
                    # Reactions and processing happen in the worker thread pool.
                    print(f"[{current_agent_id}] Received event {event.get('ts')}, enqueuing...")
                    payload = {
                        "event": event,
                        "agent_id": current_agent_id,
                        "bot_id": current_bot_id
                    }
                    slack_queue.enqueue_incoming(payload)

                # Register for both app_mention and message
                # Purely non-blocking: just enqueue everything to Redis.
                @current_app.event("app_mention")
                def handle_mention(event, say):
                    enqueue_event(event)

                @current_app.event("message")
                def handle_messages(event, say):
                    enqueue_event(event)

            setup_agent_events(app, agent_id, bot_id)
            apps[agent_id] = app

            handler = SocketModeHandler(app, agent_app_token)
            handler.connect()
            handlers.append(handler)

    if handlers:
        print(f"Successfully started {len(handlers)} bot listeners.")
        
        # Start the background worker for incoming events
        incoming_worker_thread = threading.Thread(
            target=slack_worker,
            args=(agents, apps, ack_emoji, app_env, dev_channel_id),
            daemon=True
        )
        incoming_worker_thread.start()
        
        env_label = "(Dev)" if app_env.lower() == "development" else "(Prod)"
        startup_msg = f"{env_label} Alfredo is here, Don Jimmy. The famiglia is ready."
        
        # In development, announce ONLY in the dev channel if provided
        if app_env.lower() == "development" and dev_channel_id:
            print(f"[Alfredo] Announcing in dev channel {dev_channel_id}...")
            slack_queue.enqueue_message("alfredo", dev_channel_id, startup_msg)
        else:
            # In production or if no dev channel is configured, use command-center
            print(f"[Alfredo] Announcing in command-center...")
            slack_queue.enqueue_message("alfredo", "#command-center", startup_msg)

    # 5.5 Start Mattermost Handlers
    print("Starting Mattermost message queue worker...")
    mattermost_queue.start_worker()
    
    mm_started = 0
    # Log missing tokens for Mattermost agents to match Slack style
    all_agent_keys = ["alfredo", "vito", "riccado", "rossini", "tommy", "bella", "kowalski"]
    for a_key in all_agent_keys:
        if not os.getenv(f"MATTERMOST_BOT_TOKEN_{a_key.upper()}"):
            print(f"[Mattermost] [{a_key}] no bot token found; listener will not start.")

    for agent_id, driver in mattermost_queue.drivers.items():
        bot_id = mattermost_queue.user_ids.get(agent_id)
        if not bot_id: continue
        
        print(f"Initializing Mattermost listener for {agent_id} ({bot_id})...")
        mm_started += 1
        
        def setup_mattermost_events(current_agent_id, current_bot_id, current_driver):
            async def handle_event(event_json):
                try:
                    event = json.loads(event_json)
                    event_type = event.get('event')
                    print(f"[{current_agent_id}] [Mattermost] Received WebSocket event: {event_type}")
                    
                    if event_type == 'posted':
                        print(f"[{current_agent_id}] [Mattermost] Detected 'posted' event, enqueuing...")
                        payload = {
                            "event": event,
                            "agent_id": current_agent_id,
                            "bot_id": current_bot_id,
                            "app_env": app_env
                        }
                        mattermost_queue.enqueue_incoming(payload)
                except Exception as e:
                    print(f"[{current_agent_id}] [Mattermost] Error handling event: {e}")

            def run_ws():
                # Create a fresh event loop for this thread — Python 3.10+ has no
                # implicit event loop in non-main threads, so we must do this explicitly
                # instead of relying on init_websocket's internal asyncio.get_event_loop().
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    print(f"[{current_agent_id}] [Mattermost] Starting WebSocket loop...")
                    ws = Websocket(current_driver.options, current_driver.client.token)
                    loop.run_until_complete(ws.connect(handle_event))
                except Exception as e:
                    print(f"[{current_agent_id}] [Mattermost ❌] WebSocket loop terminated: {e}")
                finally:
                    loop.close()

            # Start WebSocket listener in a dedicated thread
            threading.Thread(
                target=run_ws,
                name=f"mm-ws-{current_agent_id}",
                daemon=True
            ).start()

        setup_mattermost_events(agent_id, bot_id, driver)

    if mm_started:
        print(f"Successfully started {mm_started} Mattermost bot listeners.")
        
        # Alfredo announces startup in Mattermost as well
        if "alfredo" in mattermost_queue.drivers:
            mm_startup_msg = f"{env_label} Alfredo is here on Mattermost, Don Jimmy. The famiglia is ready."
            # Note: We use 'command-center' as the default channel name for Mattermost
            print(f"[Alfredo] [Mattermost] Announcing in command-center...")
            mattermost_queue.enqueue_message("alfredo", "command-center", mm_startup_msg)

    # Start the background worker for Mattermost events
    mattermost_worker_thread = threading.Thread(
        target=mm_worker,
        args=(agents, ack_emoji.replace(":", ""), app_env),
        daemon=True
    )
    mattermost_worker_thread.start()
    print("[MattermostWorker] Started.")

    if not handlers and not mattermost_queue.drivers:
        print("No Slack or Mattermost tokens found. Running in PROPOSAL mode.")
        slack_queue.enqueue_message("alfredo", "system", "Alfredo initialized (Mock mode).")

    # 6. Keep the main thread alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Shutting down...")
        for h in handlers:
            h.disconnect()
        # Note: Worker stop is inside finally or handled separately
        task_orchestrator.stop()
        slack_queue.stop_worker()
        mattermost_queue.stop_worker()

if __name__ == "__main__":
    main()
