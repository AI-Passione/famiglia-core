# 🏛 The Famiglia Testing Suite
> "In this family, we trust but verify." — *The Don*

Welcome to the central intelligence validation hub. This directory contains the automated test suite for the `famiglia-core` engine, restructured to mirror the source code for maximum scalability.

Run all unit tests (both frontend and backend) from the Command Center:
```bash
npm run test
```

Run all frontend unit tests from the command center:
```bash
npm run test:frontend
```

Run all backend tests using the `uv` environment:
```bash
uv run pytest
```

To run a specific module:
```bash
uv run pytest tests/agents/test_agents.py
```

## 🗺 Test Map (Mirrored Structure)

| Directory | Component | Responsibility |
| :--- | :--- | :--- |
| **`tests/agents/`** | **Agents** | Multi-agent orchestration, trait resolution, LLM mocking. |
| **`tests/command_center/backend/slack/`** | **Slack** | Slack client communication, file downloads, and resolution. |
| **`tests/command_center/backend/mattermost/`** | **Mattermost** | Mattermost client and provisioning logic. |
| **`tests/command_center/backend/api/`** | **Backend API** | FastAPI endpoints, services, and response validation. |
| **`tests/command_center/frontend/`** | **Web Dashboard** | React component validation, Vitest configuration, and UI logic. |
| **`tests/db/`** | **Infrastructure** | Database seeding and schema initialization. |
| **`tests/observability/`** | **Monitoring** | System health checks and execution logging. |
| **`tests/`** | **Core** | Project-wide core utilities (e.g. `test_core.py`). |

## 🛠 Testing Protocols

### 1. The `conftest.py` Soul
We use a centralized `conftest.py` at the root of `tests/` to ensure the testing environment is isolated:
- **Environment Isolation**: `DUCKDB_DWH_PATH` and `UPLOAD_DIR` are automatically set to `/tmp` for all sub-folders.
- **Global Mocking**: Centralized mocks for `DuckDBTool` and `Postgres` connections.

### 2. Mocking Guidelines
Always prioritize `unittest.mock` for external services. 
- **LLMs**: Never call real LLM providers in unit tests.
- **Database**: Use the mocked connection pool provided in `conftest.py`.

### 3. Adding New Tests
When adding a new feature, place the test in a directory mirroring its source location in `src/famiglia_core`. 
Example: `src/famiglia_core/tools/api.py` -> `tests/tools/test_api.py`.

## 🎨 Frontend Testing (Vitest)

The Command Center Dashboard uses **Vitest** and **React Testing Library** for high-fidelity UI validation. 

- **Location**: All frontend tests are centralized in `tests/command_center/frontend/`.
- **Mocks**: Global browser APIs are mocked in `vitest.setup.ts`. 
- **Execution**: Run `npm run test:frontend` from the repository root to verify the dashboard's integrity.

---
*Stay elegant. Stay verified. La Passione.*