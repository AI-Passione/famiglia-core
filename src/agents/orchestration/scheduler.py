import os
import threading
import time
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from src.agents.base_agent import BaseAgent
from src.db.agents.context_store import context_store
from src.command_center.backend.slack.client import slack_queue
from src.agents.orchestration.utils.task_helpers import Task, TASK_TYPE_REMINDER

class TaskOrchestrator:
    def __init__(self):
        self._agents: Dict[str, BaseAgent] = {}
        self._running = False
        self._threads: List[threading.Thread] = []
        
        self.poll_seconds = max(1, int(os.getenv("TASK_POLL_SECONDS", "10")))
        self.scheduler_poll_seconds = 60 # Templates don't need highly frequent polling
        self._wakeup_event = threading.Event()

    def configure(self, agents: Dict[str, BaseAgent]):
        self._agents = {
            (agent_id or "").strip().lower(): agent_obj
            for agent_id, agent_obj in (agents or {}).items()
        }

    def start(self):
        if self._running:
            return
        if not self._agents:
            print("[TaskOrchestrator] No agents registered. Orchestrator not started.")
            return
        
        self._running = True
        
        # Start Worker thread
        worker_thread = threading.Thread(target=self._worker_loop, daemon=True, name="TaskWorker")
        worker_thread.start()
        self._threads.append(worker_thread)
        
        # Start Scheduler thread
        scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True, name="TaskScheduler")
        scheduler_thread.start()
        self._threads.append(scheduler_thread)
        
        print(f"[TaskOrchestrator] Started (poll={self.poll_seconds}s, scheduler_poll={self.scheduler_poll_seconds}s).")

    def stop(self):
        self._running = False
        for t in self._threads:
            if t.is_alive():
                t.join(timeout=2)
        self._threads = []
        print("[TaskOrchestrator] Stopped.")

    def _scheduler_loop(self):
        """Polls for recurring task templates and spawns tasks."""
        while self._running:
            try:
                self._check_and_spawn_recurring()
            except Exception as e:
                print(f"[TaskOrchestrator::Scheduler] Error: {e}")
            time.sleep(self.scheduler_poll_seconds)

    def _worker_loop(self):
        """Polls for queued tasks and executes them."""
        eligible_agents = list(self._agents.keys())
        while self._running:
            try:
                task_data = context_store.claim_next_scheduled_task(eligible_agents=eligible_agents)
                if not task_data:
                    # Wait for next poll OR until signaled by scheduler
                    self._wakeup_event.wait(timeout=self.poll_seconds)
                    self._wakeup_event.clear()
                    continue

                task = Task.from_dict(task_data)
                self._execute_task(task)
            except Exception as e:
                print(f"[TaskOrchestrator::Worker] Error: {e}")
                time.sleep(self.poll_seconds)

    def _check_and_spawn_recurring(self):
        now = datetime.now(timezone.utc)
        templates = context_store.list_recurring_tasks()
        
        for t_data in templates:
            task = Task.from_dict(t_data)
            if self._should_spawn(task, now):
                self._spawn_task(task, now)

    def _should_spawn(self, task: Task, now: datetime) -> bool:
        schedule = task.schedule_config or {}
        if not schedule:
            return False

        interval_minutes = schedule.get("interval_minutes")
        target_days = schedule.get("days", [])
        target_hour = schedule.get("hour")
        target_minute = schedule.get("minute", 0)

        # 1. De-bounce: Check last_spawned_at relative to interval
        last_spawned = task.last_spawned_at
        if last_spawned:
            if isinstance(last_spawned, str):
                try:
                    last_spawned = datetime.fromisoformat(last_spawned.replace("Z", "+00:00"))
                except ValueError:
                    return True # If unparseable, allow spawn
            
            # Ensure last_spawned is timezone-aware for comparison with 'now'
            if last_spawned.tzinfo is None:
                last_spawned = last_spawned.replace(tzinfo=timezone.utc)
            
            # Use interval as guide, or default to 50min for daily tasks
            debounce_mins = (interval_minutes * 0.8) if interval_minutes else 50
            if (now - last_spawned) < timedelta(minutes=debounce_mins):
                return False

        # 2. Case A: Interval-based (e.g. every minute, every 60 mins)
        if interval_minutes:
            if not last_spawned:
                return True
            elapsed = (now - last_spawned).total_seconds() / 60
            return elapsed >= interval_minutes

        # 3. Case B: Time-based (Daily/Weekly at specific hour:minute)
        # Check day
        if target_days and now.weekday() not in target_days:
            return False

        # Current local time check
        local_now = datetime.now()
        # If hour is specified, we must match it
        if target_hour is not None and local_now.hour != target_hour:
             return False
        # If minute is specified, we must be at or past it
        if local_now.minute < target_minute:
             return False

        return True

    def _spawn_task(self, task: Task, now: datetime):
        print(f"[TaskOrchestrator::Scheduler] Spawning task: {task.title}")
        context_store.create_scheduled_task(
            title=task.title,
            task_payload=task.task_payload,
            created_by_type="ai_agent",
            created_by_name="TaskOrchestrator::Scheduler",
            priority=task.priority,
            expected_agent=task.expected_agent,
            eta_pickup_at=now,  # Pass datetime object directly
            metadata=task.metadata,
            recurring_task_id=task.id,
        )
        context_store.update_recurring_task_last_spawned(task.id, now)
        self._wakeup_event.set() # Wake up the worker immediately

    def _execute_task(self, task: Task):
        print(f"[TaskOrchestrator::Worker] Claimed task #{task.id}: {task.title}")
        
        available_ids = list(self._agents.keys())
        assignee_id = task.resolve_assignee(available_ids)
        
        if not assignee_id:
            msg = f"❌ Scheduled Task #{task.id} FAILED: No eligible AI agents available for assignment."
            self._notify_slack(task, "system", msg)
            context_store.complete_scheduled_task(
                task_id=task.id,
                assigned_agent="",
                status="failed",
                error_details="No eligible AI agents available for assignment.",
            )
            return

        context_store.assign_scheduled_task(task_id=task.id, assigned_agent=assignee_id)
        agent = self._agents[assignee_id]

        try:
            # Check for specialized internal workflows first (e.g. reminders)
            if self._try_internal_workflow(task, assignee_id):
                return

            # Consolidated Supervisor Path: Run autonomous task
            result = agent.execute_scheduled_task(task)

            is_failed = task.result_looks_failed(result)
            status = task.get_completion_status(is_failed)
            
            # Post to channel (Mandatory for success acknowledgement)
            safe_result = (result or "").strip() or "No summary provided by agent."
            msg = f"Scheduled Task #{task.id} ({task.task_type}) {status.capitalize()}.\n\n{safe_result}"
            
            slack_ts = self._notify_slack(task, assignee_id, msg)
            
            if not slack_ts and task.get_output_channel():
                # If a channel was expected but notification failed, we downgrade success to failure
                print(f"[TaskOrchestrator::Worker] Downgrading task #{task.id} to failed due to Slack notification failure.")
                status = "failed"
                is_failed = True
                error_details = "Execution finished but Slack notification failed after multiple attempts."
            else:
                error_details = None

            context_store.complete_scheduled_task(
                task_id=task.id,
                assigned_agent=assignee_id,
                status=status,
                result_summary=(result or "")[:8000] if not is_failed else None,
                error_details=(error_details or (result or "")[:2000]) if is_failed else None,
            )
            print(f"[TaskOrchestrator::Worker] Finished task #{task.id} (status={status})")

        except Exception as e:
            print(f"[TaskOrchestrator::Worker] Execution failed for task #{task.id}: {e}")
            self._notify_slack(task, assignee_id or "system", f"❌ Scheduled Task #{task.id} EXCEPTION: {e}")
            context_store.complete_scheduled_task(
                task_id=task.id,
                assigned_agent=assignee_id or "",
                status="failed",
                error_details=str(e)[:2000],
            )

    def _notify_slack(self, task: Task, agent_id: str, message: str) -> Optional[str]:
        """Central helper to notify Slack with retries/pokes."""
        channel = task.get_output_channel()
        if not channel:
            # Fallback to coordination channel
            channel = "C0AGFEBPBJ8" # Coordination Channel
        
        slack_ts = None
        for attempt in range(3):
            try:
                slack_ts = slack_queue.post_message(
                    agent=agent_id,
                    channel=channel,
                    message=message[:3500]
                )
                if slack_ts:
                    return slack_ts
            except Exception as e:
                print(f"[TaskOrchestrator::Worker] Slack notification attempt {attempt+1} failed: {e}")
            
            if attempt < 2:
                time.sleep(2)
        
        return None

    def _try_internal_workflow(self, task: Task, assignee_id: str) -> bool:
        """Handle tasks that don't need a full LLM agent loop."""
        if task.task_type == TASK_TYPE_REMINDER:
            channel = task.get_output_channel()
            target_user = (task.safe_metadata.get("target_user_id") or "").strip()
            msg = (task.safe_metadata.get("reminder_message") or "Scheduled reminder.").strip()
            thread_ts = (task.safe_metadata.get("slack_thread_ts") or "").strip() or None

            if not channel or not target_user:
                raise ValueError("Missing channel or target_user_id for reminder.")

            slack_queue.enqueue_message(
                agent="alfredo",
                channel=channel,
                message=f"<@{target_user}> {msg}",
                thread_ts=thread_ts,
            )
            
            context_store.complete_scheduled_task(
                task_id=task.id,
                assigned_agent=assignee_id,
                status="completed",
                result_summary=f"Reminder sent to <@{target_user}> in {channel}."
            )
            return True
        
        # Add more internal workflows here if needed (e.g. reporting)
        return False

task_orchestrator = TaskOrchestrator()
