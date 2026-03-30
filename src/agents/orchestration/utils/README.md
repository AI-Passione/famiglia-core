# Scheduled Tasks

This module manages the autonomous, deferred, and recurring execution of agent tasks within the "La Passione Inc" system.

## Components

### 1. RecurringTaskScheduler
- **File**: `recurring_scheduler.py`
- **Role**: Monitors the `recurring_tasks` table in PostgreSQL.
- **Mechanism**:
    - Polls every 60 seconds (default).
    - Checks `schedule_config` (days, hour, minute) against local time.
    - Spawns a new entry in the `scheduled_tasks` queue when a window is hit.
    - Ensures a task isn't double-spawned within the same window (50-minute buffer).

### 2. ScheduledTaskWorker
- **File**: `batched_worker.py` (aliased as `batched_worker` for legacy compatibility).
- **Role**: Claims and executes tasks from the `scheduled_tasks` queue.
- **Workflow**:
    - Claims next available task based on eligible agents.
    - Resolves the correct agent using `TASK_TYPE_TO_EXPECTED_AGENT` or `expected_agent` metadata.
    - Drives the agent to complete the task via `agent.complete_task`.
    - Routes results to specific Slack channels (Research, Product, Tech) based on task type.

## Task Lifecycle
1. **Creation**: Triggered by the `RecurringTaskScheduler` or created manually/proactively by another agent.
2. **Claiming**: The worker claims the task and assigns it to an idle/qualified agent.
3. **Execution**: The agent performs the request (Web search, PRD drafting, Coding, etc.).
4. **Completion**: Results are posted to Slack and the task status is updated in the database.
