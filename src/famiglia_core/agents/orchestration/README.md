# Orchestration Layer

The orchestration layer is responsible for routing tasks to the appropriate feature workers. It strictly separates interactive requests from autonomous background tasks.

## Components

### 1. Master Supervisors
- **On-Demand (`on_demand_supervisor.py`)**: Handles interactive Slack requests for Product, Operations, and Analytics.
- **Scheduling (`scheduling_supervisor.py`)**: Handles autonomous background logic.

### 2. Execution Engine
- **Scheduler (`scheduler.py`)**: The background poller that checks the database and triggers the Scheduling Master Supervisor.

### 3. Utils (`utils/`)
- **`task_helpers.py`**: Consolidated data models (`Task`), configuration constants, and agent tools (`TaskTools`).
- **`state.py`**: Shared `AgentState` definitions for LangGraph.
- **`tasks.yml`**: Definition of recurring task schedules and agent assignments.

### 4. Quality Assurance
- **Tests**: Core orchestration logic is validated in `tests/agents/test_orchestration.py`, `tests/agents/test_scheduling_supervisor.py`, and `tests/agents/test_state.py`.

## Architecture

```mermaid
graph TD
    subgraph "Execution Layer (Orchestration/)"
        S[scheduler.py] --> SM[scheduling_supervisor.py]
        Slack[Slack Event] --> OM[on_demand_supervisor.py]
    end

    subgraph "Feature Layer (Features/)"
        F[Worker Graphs]
    end

    subgraph "Shared Infrastructure (Utils/)"
        H[task_helpers.py]
        ST[state.py]
    end

    OM -- Intent Routing: PRODUCT/ANALYTICS --> F
    SM -- TaskType Routing --> F
```

### On-Demand Supervisor Flow
```mermaid
graph TD
    START((Start)) --> DM["_decide_domain (Classifier)"]
    DM -- "Intent: PRODUCT" --> CPW["call_prd_worker"]
    DM -- "Intent: ANALYTICS" --> CA["handle_analytics"]
    DM -- "Intent: SUPPORT" --> HS["handle_support"]
    DM -- "Intent: OPERATIONS" --> HO["handle_operations"]
    
    CPW --> END((End))
    CA --> END
    HS --> END
    HO --> END
```

### Scheduling Supervisor Flow
```mermaid
graph TD
    START((Start)) --> RW["_route_to_worker (TaskType)"]
    RW -- "prd_drafting" --> W1["call_prd_drafting"]
    RW -- "prd_review" --> W2["call_prd_review"]
    RW -- "market_research" --> W3["call_market_research"]
    RW -- "coding_*" --> W4["handle_operations"]
    RW -- "else" --> W5["handle_support"]
    
    W1 --> END((End))
    W2 --> END
    W3 --> END
    W4 --> END
    W5 --> END
```

## Directory Structure
- `features/`: Individual LangGraph workflows for specific capabilities.
- `utils/`: Supporting data models, shared state, and task configuration.
- `on_demand_supervisor.py`: Entry point for interactive user messages.
- `scheduling_supervisor.py`: Entry point for autonomous tasks.
- `scheduler.py`: Background task engine.
