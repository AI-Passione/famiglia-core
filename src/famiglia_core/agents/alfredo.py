import re
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, List, Optional

from famiglia_core.agents.base_agent import (
    BaseAgent,
    TASK_TYPE_CODING_CODE_ANALYSIS,
    TASK_TYPE_CODING_IMPLEMENTATION,
    TASK_TYPE_FEATURE_REQUEST,
    TASK_TYPE_MARKET_RESEARCH,
    TASK_TYPE_PRD_DRAFTING,
    TASK_TYPE_REMINDER,
    TASK_TYPE_TO_EXPECTED_AGENT,
    TASK_TYPE_TO_PRIORITY,
    TASK_TYPE_ALFREDO_GREETING,
)
from famiglia_core.agents.llm.models_registry import GEMMA3_4B
from famiglia_core.db.agents.context_store import context_store

class Alfredo(BaseAgent):
    def __init__(self):
        super().__init__(
            agent_id="alfredo",
            name="Alfredo",
            role="Agent orchestrator & workflow automation",
            model_config={
                "primary": "gemini-2.0-flash",
                "secondary": GEMMA3_4B,
            }
        )
        self.register_tool("get_scheduled_tasks_status", self.get_scheduled_tasks_status)
        self.register_tool("list_scheduled_tasks", self.list_scheduled_tasks_tool)
        self.register_tool("cancel_scheduled_task", self.cancel_scheduled_task_tool)

    def coordinate(self, request: str):
        if self.propose_action(f"Coordinate request: {request}"):
             print(f"[Alfredo 🎩] Certo, Don Jimmy. Coordinating: {request}")
             return self.complete_task(request)

    def _is_schedule_creation_request(self, request: str) -> bool:
        normalized = (request or "").strip().lower()
        if not normalized:
            return False
        if self._is_schedule_cancellation_request(request) or self._is_scheduled_tasks_status_request(request):
            return False
        has_reminder_signal = any(
            term in normalized
            for term in ("remind", "reminder", "ping me", "set a reminder")
        )
        has_creation_signal = any(
            term in normalized
            for term in ("schedule", "queue", "enqueue", "create", "add", "new task", "set up")
        )
        inferred_type = self._infer_scheduled_task_type(normalized)
        return has_reminder_signal or (
            has_creation_signal and (inferred_type is not None or "task" in normalized)
        )

    def _is_scheduled_tasks_status_request(self, request: str) -> bool:
        normalized = (request or "").strip().lower()
        if not normalized:
            return False
        has_queue_ref = any(
            term in normalized
            for term in (
                "scheduled",
                "scheduled task",
                "scheduled tasks",
                "batch",
                "batched",
                "queue",
                "backlog",
                "queued jobs",
                "queued tasks",
            )
        )
        has_status_ref = any(
            term in normalized
            for term in (
                "status",
                "latest",
                "update",
                "overview",
                "progress",
                "ongoing",
                "running",
                "pending",
                "in progress",
                "pick up",
                "eta",
                "line",
                "list",
                "show",
                "what's",
                "what is",
            )
        )
        asks_creation = any(
            term in normalized
            for term in ("create", "add", "new task", "queue this", "enqueue")
        )
        asks_cancellation = any(
            term in normalized
            for term in ("cancel", "stop", "abort", "remove", "delete", "drop")
        )
        return has_queue_ref and has_status_ref and not asks_creation and not asks_cancellation

    def _infer_scheduled_task_type(self, request: str) -> Optional[str]:
        normalized = (request or "").strip().lower()
        if not normalized:
            return None

        if any(term in normalized for term in ("remind", "reminder", "ping me", "set a reminder")):
            return TASK_TYPE_REMINDER
        if "feature request" in normalized:
            return TASK_TYPE_FEATURE_REQUEST
        if any(term in normalized for term in ("code analysis", "code analyais", "bug hunt", "analyze codebase")):
            return TASK_TYPE_CODING_CODE_ANALYSIS
        if any(term in normalized for term in ("coding implementation", "coding impl", "implmentation", "implementation", "implement issues")):
            return TASK_TYPE_CODING_IMPLEMENTATION
        if any(
            term in normalized
            for term in (
                "market research",
                "market reserach",
                "market reseach",
                "research brief",
                "research task",
            )
        ):
            return TASK_TYPE_MARKET_RESEARCH
        if any(term in normalized for term in ("prd", "product requirements document", "product requirement doc", "draft prd")):
            return TASK_TYPE_PRD_DRAFTING
        return None

    def _extract_delay_seconds(self, request: str) -> Optional[int]:
        normalized = (request or "").strip().lower()
        if not normalized:
            return None

        seconds_match = re.search(r"\b(\d+)\s*(second|seconds|sec|secs)\b", normalized)
        if seconds_match:
            return max(1, int(seconds_match.group(1)))

        minute_match = re.search(r"\b(\d+)\s*(minute|minutes|min|mins)\b", normalized)
        if minute_match:
            return max(1, int(minute_match.group(1)) * 60)

        hour_match = re.search(r"\b(\d+)\s*(hour|hours|hr|hrs)\b", normalized)
        if hour_match:
            return max(1, int(hour_match.group(1)) * 3600)

        word_to_seconds = {
            "one minute": 60,
            "a minute": 60,
            "an minute": 60,
            "two minutes": 120,
            "five minutes": 300,
            "ten minutes": 600,
            "fifteen minutes": 900,
            "thirty minutes": 1800,
            "one hour": 3600,
            "an hour": 3600,
        }
        for phrase, seconds in word_to_seconds.items():
            if phrase in normalized:
                return seconds
        return None

    def _extract_delay_minutes(self, request: str) -> Optional[int]:
        delay_seconds = self._extract_delay_seconds(request)
        if delay_seconds is None:
            return None
        return max(1, (delay_seconds + 59) // 60)

    def _extract_schedule_config(self, request: str) -> Optional[Dict[str, Any]]:
        normalized = (request or "").strip().lower()
        if not normalized:
            return None

        # 1. Check for "every X minutes/hours"
        interval_match = re.search(r"\bevery\s+(\d+)\s*(minute|minutes|min|mins|hour|hours|hr|hrs)\b", normalized)
        if interval_match:
            value = int(interval_match.group(1))
            unit = interval_match.group(2)
            if "hour" in unit or "hr" in unit:
                return {"interval_minutes": value * 60}
            return {"interval_minutes": max(1, value)}

        # 2. Check for "every minute" or "hourly"
        if "every minute" in normalized:
            return {"interval_minutes": 1}
        if "every hour" in normalized or "hourly" in normalized:
            return {"interval_minutes": 60}

        # 3. Check for "daily"
        if "daily" in normalized or "every day" in normalized:
            # Default to current time daily if not specified, 
            # but usually time-based schedule handles hour/minute
            return {"hour": datetime.now().hour, "minute": datetime.now().minute}

        return None

    def _is_schedule_cancellation_request(self, request: str) -> bool:
        normalized = (request or "").strip().lower()
        if not normalized:
            return False
        has_cancel_signal = any(
            term in normalized
            for term in ("cancel", "stop", "abort", "remove", "delete")
        )
        has_task_ref = any(
            term in normalized
            for term in ("task", "report", "research", "prd", "reminder", "queue", "scheduled")
        )
        # Check for task ID like #123 or task 123
        has_id = re.search(r"(#|task\s+|id\s+)(\d+)", normalized) is not None
        return has_cancel_signal and (has_task_ref or has_id)

    def _extract_task_id(self, request: str) -> Optional[int]:
        normalized = (request or "").strip().lower()
        match = re.search(r"(?:#|task\s+|id\s+)(\d+)", normalized)
        if match:
            return int(match.group(1))
        # Try generic number if cancellation request is clear
        match = re.search(r"\b(\d+)\b", normalized)
        if match:
            return int(match.group(1))
        return None

    def _get_recent_thread_messages(self, conversation_key: Optional[str], limit: int = 12) -> List[Dict[str, Any]]:
        if not context_store.enabled or not conversation_key:
            return []
        try:
            return context_store.get_recent_messages(conversation_key=conversation_key, limit=limit)
        except Exception:
            return []

    def _infer_scheduled_task_type_from_thread(self, conversation_key: Optional[str]) -> Optional[str]:
        recent = self._get_recent_thread_messages(conversation_key=conversation_key, limit=12)
        for message in reversed(recent):
            if (message.get("role") or "").lower() != "user":
                continue
            inferred = self._infer_scheduled_task_type(message.get("content") or "")
            if inferred:
                return inferred
        return None

    def _thread_has_scheduling_intent(self, conversation_key: Optional[str]) -> bool:
        recent = self._get_recent_thread_messages(conversation_key=conversation_key, limit=12)
        if not recent:
            return False
        keywords = (
            "schedule",
            "scheduled task",
            "queue",
            "reminder",
            "market research",
            "prd",
            "feature request",
            "coding",
        )
        for message in recent:
            content = (message.get("content") or "").strip().lower()
            if any(keyword in content for keyword in keywords):
                return True
        return False

    def _is_schedule_followup_message(self, request: str) -> bool:
        normalized = (request or "").strip().lower()
        if not normalized:
            return False
        followup_hints = (
            "go ahead",
            "do it",
            "yes",
            "ok",
            "okay",
            "please just",
            "simple search",
            "complex search",
            "for @dr. rossini",
            "for rossini",
            "for @riccardo",
            "for riccardo",
            "create the task",
            "queue it",
        )
        return any(hint in normalized for hint in followup_hints)

    def _is_schedule_related_text(self, text: str) -> bool:
        normalized = (text or "").strip().lower()
        if not normalized:
            return False
        keywords = (
            "schedule",
            "scheduled task",
            "queue",
            "remind",
            "reminder",
            "market research",
            "market reserach",
            "prd",
            "feature request",
            "coding",
            "rossini",
            "riccardo",
            "simple search",
            "complex search",
            "minute",
            "second",
            "hour",
        )
        return any(keyword in normalized for keyword in keywords)

    def _compose_schedule_request_text(self, task: str, conversation_key: Optional[str]) -> str:
        current = (task or "").strip()
        recent = self._get_recent_thread_messages(conversation_key=conversation_key, limit=12)
        user_texts: List[str] = []
        for message in recent:
            if (message.get("role") or "").lower() != "user":
                continue
            content = (message.get("content") or "").strip()
            if content and self._is_schedule_related_text(content):
                user_texts.append(content)
        if current and self._is_schedule_related_text(current):
            user_texts.append(current)
        if not user_texts:
            return current

        deduped: List[str] = []
        seen = set()
        for item in user_texts:
            key = item.lower()
            if key in seen:
                continue
            seen.add(key)
            deduped.append(item)
        return " | ".join(deduped[-4:])

    def _log_direct_turn(
        self,
        task: str,
        response: str,
        sender: str,
        conversation_key: Optional[str],
    ) -> None:
        if not context_store.enabled:
            return
        scoped_conversation_key = self._build_conversation_key(sender, conversation_key)
        context_store.log_message(
            agent_name=self.name,
            conversation_key=scoped_conversation_key,
            role="user",
            content=task,
            sender=sender,
            metadata={"source": "scheduled_task_intake"},
        )
        context_store.log_message(
            agent_name=self.name,
            conversation_key=scoped_conversation_key,
            role="assistant",
            content=response,
            sender=self.name,
            metadata={"source": "scheduled_task_intake"},
        )

    def _return_direct_response(
        self,
        task: str,
        response: str,
        sender: str,
        conversation_key: Optional[str],
    ) -> str:
        self._log_direct_turn(task, response, sender, conversation_key)
        return response

    def _extract_sender_identity(self, sender: str, conversation_key: Optional[str]) -> tuple[str, Optional[str]]:
        raw_sender = (sender or "Unknown").strip()
        mention_match = re.search(r"<@([A-Z0-9]+)>", raw_sender)
        user_id = mention_match.group(1) if mention_match else None
        sender_name = re.sub(r"\s*\(<@[A-Z0-9]+>\)\s*$", "", raw_sender).strip() or "Unknown"

        if not user_id and conversation_key:
            parts = conversation_key.split(":")
            if len(parts) >= 4 and parts[0] == "slack":
                user_part = parts[3].strip()
                if user_part and user_part.lower() != "unknown":
                    user_id = user_part
        return sender_name, user_id

    def _extract_slack_location(self, conversation_key: Optional[str]) -> tuple[Optional[str], Optional[str]]:
        if not conversation_key:
            return None, None
        parts = conversation_key.split(":")
        if len(parts) < 4 or parts[0] != "slack":
            return None, None
        channel_id = parts[1].strip() or None
        thread_ts = parts[2].strip() or None
        return channel_id, thread_ts

    def _extract_repo_name(self, request: str) -> Optional[str]:
        match = re.search(r"\b([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)\b", request or "")
        return match.group(1) if match else None

    def _extract_prd_reference(self, request: str) -> Optional[str]:
        raw = (request or "").strip()
        if not raw:
            return None
        url_match = re.search(r"https?://[^\s)]+", raw)
        if url_match:
            return url_match.group(0)
        normalized = raw.lower()
        if "prd" in normalized or "product requirement" in normalized:
            return "provided-in-request"
        return None

    def _extract_title_topic(self, request: str) -> str:
        cleaned = re.sub(r"\s+", " ", (request or "").strip())
        if not cleaned:
            return "General task"
        cleaned = re.sub(r"^[^a-zA-Z0-9]+", "", cleaned)
        return cleaned[:90]

    def _build_typed_task_payload(self, task_type: str, task: str) -> str:
        if task_type == TASK_TYPE_MARKET_RESEARCH:
            return (
                "Perform market research using web search. Create a Notion page with findings. "
                "Post the final summary and Notion page link in Slack channel C0AGQPGNP09 "
                "(research-insights)."
            )
        if task_type == TASK_TYPE_PRD_DRAFTING:
            return (
                "Draft a PRD using web search. Create a Notion page containing the draft. "
                "Post the PRD summary and Notion link in Slack channel C0AL8GW2VAL "
                "(product-rossini), explicitly asking Don Jimmy for approval. "
                "This task must remain in drafted state until approved."
            )
        if task_type == TASK_TYPE_FEATURE_REQUEST:
            return (
                "Use the provided PRD to open GitHub project(s), milestone(s), and issues for the "
                "feature request in the relevant repository. If anything fails, report an error "
                "in Slack channel C0AGQPHEX7T (agents-coordination). After successful setup, "
                "notify Riccardo in C0AGQPHEX7T and queue a follow-up coding implementation task "
                "for Riccardo."
            )
        if task_type == TASK_TYPE_CODING_CODE_ANALYSIS:
            return (
                "Analyze the full target GitHub repository and create GitHub issues for bugs found. "
                "All bug issues must include the Bug label."
            )
        if task_type == TASK_TYPE_CODING_IMPLEMENTATION:
            return (
                "Read open GitHub issues by priority and implement them one by one. "
                "Open PRs for completed work and post review requests in Slack channel C0AH64QTG2U "
                "(tech-riccardo)."
            )
        return task

    def _create_typed_scheduled_task(
        self,
        task_type: str,
        task: str,
        sender: str,
        conversation_key: Optional[str],
    ) -> str:
        sender_name, sender_user_id = self._extract_sender_identity(sender, conversation_key)
        channel_id, thread_ts = self._extract_slack_location(conversation_key)
        expected_agent = TASK_TYPE_TO_EXPECTED_AGENT.get(task_type, "alfredo")
        priority = TASK_TYPE_TO_PRIORITY.get(task_type, "medium")
        repo_name = self._extract_repo_name(task)
        prd_reference = self._extract_prd_reference(task)
        delay_seconds = self._extract_delay_seconds(task)
        eta_pickup_at = None
        eta_completion_at = None
        if delay_seconds is not None:
            pickup_dt = datetime.now(timezone.utc) + timedelta(seconds=delay_seconds)
            eta_pickup_at = pickup_dt.isoformat()
            eta_completion_at = (pickup_dt + timedelta(minutes=30)).isoformat()

        if task_type == TASK_TYPE_FEATURE_REQUEST and not prd_reference:
            return (
                "Certo, Don Jimmy. Before I queue a Feature Request task, I need a PRD reference. "
                "Please share an existing PRD link or ask me to schedule a PRD Drafting task first."
            )

        title_prefix = {
            TASK_TYPE_MARKET_RESEARCH: "Market Research",
            TASK_TYPE_PRD_DRAFTING: "PRD Drafting",
            TASK_TYPE_FEATURE_REQUEST: "Feature Request Setup",
            TASK_TYPE_CODING_CODE_ANALYSIS: "Coding - Code Analysis",
            TASK_TYPE_CODING_IMPLEMENTATION: "Coding - Implementation",
        }.get(task_type, "Scheduled Task")
        title = f"{title_prefix}: {self._extract_title_topic(task)}"

        schedule_config = self._extract_schedule_config(task)

        created = context_store.create_scheduled_task(
            title=title,
            task_payload=self._build_typed_task_payload(task_type, task),
            created_by_type="human_user",
            created_by_name=sender_name,
            priority=priority,
            expected_agent=expected_agent,
            eta_pickup_at=eta_pickup_at,
            eta_completion_at=eta_completion_at,
            metadata={
                "task_type": task_type,
                "requested_text": task,
                "slack_channel": channel_id,
                "slack_thread_ts": thread_ts,
                "target_user_id": sender_user_id,
                "repo_name": repo_name,
                "prd_reference": prd_reference,
            },
            schedule_config=schedule_config,
        )
        if not created:
            return "Con permesso, Boss. I could not create this scheduled task."

        eta_pickup = created.get("eta_pickup_at") or "n/a"
        eta_done = created.get("eta_completion_at") or "n/a"
        expected_label = {
            "rossini": "Dr. Rossini",
            "riccardo": "Riccardo",
            "alfredo": "Alfredo",
        }.get(expected_agent, expected_agent)
        return (
            f"Certo, Don Jimmy. Scheduled Task #{created['id']} ({task_type}) has been queued. "
            f"Expected assignee: {expected_label}. "
            f"ETA pickup: `{eta_pickup}`. ETA done: `{eta_done}`."
        )

    def _create_scheduled_reminder(
        self,
        task: str,
        sender: str,
        conversation_key: Optional[str],
    ) -> str:
        if not context_store.enabled:
            return (
                "Con permesso, Boss. I cannot schedule this reminder because "
                "PostgreSQL context storage is disabled (`AGENT_CONTEXT_ENABLED=false`)."
            )

        delay_minutes = self._extract_delay_minutes(task)
        if delay_minutes is None:
            return (
                "Certo, Don Jimmy. I need a concrete time delay for scheduling. "
                "Please specify it like 'in 1 minute' or 'in 10 minutes.'"
            )

        sender_name, sender_user_id = self._extract_sender_identity(sender, conversation_key)
        channel_id, thread_ts = self._extract_slack_location(conversation_key)

        now = datetime.now(timezone.utc)
        eta_pickup_at = now + timedelta(minutes=delay_minutes)
        eta_completion_at = eta_pickup_at + timedelta(minutes=1)

        reminder_message = (
            f"{sender_name}, this is your scheduled reminder from Alfredo: {task}"
        )

        schedule_config = self._extract_schedule_config(task)

        created = context_store.create_scheduled_task(
            title=f"Reminder for {sender_name}",
            task_payload=(
                "Send a Slack reminder to the requester at the scheduled time."
            ),
            created_by_type="human_user",
            created_by_name=sender_name,
            priority="high",
            expected_agent="alfredo",
            eta_pickup_at=eta_pickup_at.isoformat(),
            eta_completion_at=eta_completion_at.isoformat(),
            metadata={
                "task_type": TASK_TYPE_REMINDER,
                "kind": "slack_reminder",
                "slack_channel": channel_id,
                "slack_thread_ts": thread_ts,
                "target_user_id": sender_user_id,
                "reminder_message": reminder_message,
                "requested_text": task,
                "delay_minutes": delay_minutes,
            },
            schedule_config=schedule_config,
        )
        if not created:
            return "Con permesso, Boss. I could not create the scheduled reminder task."

        eta_pickup = created.get("eta_pickup_at") or "n/a"
        eta_done = created.get("eta_completion_at") or "n/a"
        return (
            f"Certo, Don Jimmy. Scheduled Task #{created['id']} has been queued. "
            f"I will ping you in approximately {delay_minutes} minute(s). "
            f"ETA pickup: `{eta_pickup}`. ETA done: `{eta_done}`."
        )

    def get_scheduled_tasks_status(self, user_prompt: Optional[str] = None) -> str:
        """Return latest queue status for all scheduled tasks."""
        _ = user_prompt
        if not context_store.enabled:
            return (
                "Con permesso, Boss. I cannot read scheduled task status because "
                "PostgreSQL context storage is disabled (`AGENT_CONTEXT_ENABLED=false`)."
            )
        overview = context_store.get_scheduled_tasks_overview(queue_limit=10)
        counts = overview.get("counts", {})
        queue_line = overview.get("queue_line", [])
        finished = overview.get("recently_finished", [])

        lines = [
            "Certo, Don Jimmy. Latest scheduled task status:",
            (
                f"- queued={counts.get('queued', 0)}, "
                f"in_progress={counts.get('in_progress', 0)}, "
                f"drafted={counts.get('drafted', 0)}, "
                f"completed={counts.get('completed', 0)}, "
                f"failed={counts.get('failed', 0)}, "
                f"cancelled={counts.get('cancelled', 0)}"
            ),
        ]

        if queue_line:
            lines.append("- Queue line:")
            lines.append("```")
            lines.append("| ID | Priority | Title | Type | Creator | Expected | Assigned | ETA Pickup | ETA Done |")
            lines.append("| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |")
            for task in queue_line[:5]:
                metadata = task.get("metadata") if isinstance(task.get("metadata"), dict) else {}
                task_type = metadata.get("task_type") or metadata.get("kind") or "general"
                lines.append(
                    f"| #{task['id']} | {task['priority']} | {task['title']} | "
                    f"{task_type} | "
                    f"{task['created_by_type']}:{task['created_by_name']} | "
                    f"{task.get('expected_agent') or 'auto'} | "
                    f"{task.get('assigned_agent') or 'unassigned'} | "
                    f"{task.get('eta_pickup_at') or 'n/a'} | "
                    f"{task.get('eta_completion_at') or 'n/a'} |"
                )
            lines.append("```")
        else:
            lines.append("- Queue line: empty.")

        if finished:
            lines.append("- Most recent finished task:")
            lines.append("```")
            lines.append("| ID | Status | Title | Agent | Completed At |")
            lines.append("| :--- | :--- | :--- | :--- | :--- |")
            task = finished[0]
            lines.append(
                f"| #{task['id']} | {task['status']} | {task['title']} | "
                f"{task.get('assigned_agent') or 'unassigned'} | "
                f"{task.get('completed_at') or 'n/a'} |"
            )
            lines.append("```")

        return "\n".join(lines)

    def _handle_alfredo_greeting_task(self) -> str:
        """Handle the specialized weekday greeting task for Don Jimmy."""
        greeting = "Buongiorno, <@U0AG886GJCV>! 🎩 I hope you are having a productive week."
        
        # Penting tasks overview
        status_report = self.get_scheduled_tasks_status()
        
        # Provide options
        options = (
            "\nWould you like to add any new scheduled tasks for the coming week?\n"
            "- *Market Research*: 'Alfredo, schedule market research for [Topic]'\n"
            "- *PRD Drafting*: 'Alfredo, schedule a PRD draft for [Feature]'\n"
            "- *Code Analysis*: 'Alfredo, schedule code analysis for [Repo]'\n"
            "- *Implementation*: 'Alfredo, queue implementation for [Issues]'"
        )
        
        return f"{greeting}\n\n{status_report}\n{options}"


    def complete_task(
        self,
        task: str,
        sender: str = "Unknown",
        conversation_key: Optional[str] = None,
        on_intermediate_response: Optional[Callable[[str], None]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        if f"({TASK_TYPE_ALFREDO_GREETING})" in task:
             return self._handle_alfredo_greeting_task()

        if self._is_schedule_cancellation_request(task):
            task_id = self._extract_task_id(task)
            if task_id is None:
                response = "Certo, Don Jimmy. I need the Task ID (e.g. #123) to cancel it."
            else:
                print(f"[Alfredo] Scheduled task cancellation detected for #{task_id}.")
                response = self.cancel_scheduled_task_tool(task_id=task_id, user_prompt=task)

            return self._return_direct_response(
                task=task,
                response=response,
                sender=sender,
                conversation_key=conversation_key,
            )

        if self._is_scheduled_tasks_status_request(task):
            print("[Alfredo] Scheduled task status request detected. Fetching from PostgreSQL.")
            response = self.get_scheduled_tasks_status(user_prompt=task)
            return self._return_direct_response(
                task=task,
                response=response,
                sender=sender,
                conversation_key=conversation_key,
            )

        explicit_task_type = self._infer_scheduled_task_type(task)
        context_task_type = self._infer_scheduled_task_type_from_thread(conversation_key)
        schedule_creation_request = self._is_schedule_creation_request(task)
        schedule_followup_request = (
            not schedule_creation_request
            and self._thread_has_scheduling_intent(conversation_key)
            and (
                explicit_task_type is not None
                or self._is_schedule_followup_message(task)
                or context_task_type is not None
            )
        )

        if schedule_creation_request or schedule_followup_request:
            task_type = explicit_task_type or context_task_type
            if task_type is None:
                response = (
                    "Certo, Don Jimmy. Please specify one Scheduled Task type: "
                    "Reminder, Market Research, PRD Drafting, Feature Request, "
                    "Coding - Code Analysis, or Coding - Implementation."
                )
                return self._return_direct_response(
                    task=task,
                    response=response,
                    sender=sender,
                    conversation_key=conversation_key,
                )
            effective_task = self._compose_schedule_request_text(task, conversation_key)
            print(f"[Alfredo] Scheduled task request detected ({task_type}). Creating task.")
            if task_type == TASK_TYPE_REMINDER:
                response = self._create_scheduled_reminder(
                    task=effective_task,
                    sender=sender,
                    conversation_key=conversation_key,
                )
                return self._return_direct_response(
                    task=task,
                    response=response,
                    sender=sender,
                    conversation_key=conversation_key,
                )
            if not context_store.enabled:
                response = (
                    "Con permesso, Boss. I cannot queue scheduled tasks because "
                    "PostgreSQL context storage is disabled (`AGENT_CONTEXT_ENABLED=false`)."
                )
                return self._return_direct_response(
                    task=task,
                    response=response,
                    sender=sender,
                    conversation_key=conversation_key,
                )
            response = self._create_typed_scheduled_task(
                task_type=task_type,
                task=effective_task,
                sender=sender,
                conversation_key=conversation_key,
            )
            return self._return_direct_response(
                task=task,
                response=response,
                sender=sender,
                conversation_key=conversation_key,
            )

        return super().complete_task(
            task=task,
            sender=sender,
            conversation_key=conversation_key,
            on_intermediate_response=on_intermediate_response,
            metadata=metadata
        )
