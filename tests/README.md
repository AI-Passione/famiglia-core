# 🏛 The Famiglia Testing Suite
> "In this family, we trust but verify." — *The Don*

Welcome to the central intelligence validation hub. This directory contains the automated test suite for the `famiglia-core` engine, ensuring every agent, endpoint, and tool performs with the precision expected of an elite organization.

## 🚀 Quick Start
Run all tests using the `uv` environment:
```bash
uv run pytest tests/
```

To run a specific module:
```bash
uv run pytest tests/test_backend_api.py
```

## 🗺 Test Map

| Component | Responsibility | Relevant Files |
| :--- | :--- | :--- |
| **API Backend** | FastAPI endpoints, routing, and response validation. | `test_backend_api.py` |
| **Services** | Core business logic, User Management, and Agent Singletons. | `test_backend_services.py` |
| **Agents** | Multi-agent orchestration, trait resolution, and trait logic. | `test_agents.py`, `test_orchestration.py` |
| **Intelligence** | Mocking LLM interactions and message streaming. | `test_llm.py` |
| **Infrastructure** | Database seeding, DuckDB paths, and local file storage. | `test_db_seed.py`, `test_core.py` |
| **Communication** | Slack and Mattermost integration logic (Mocked). | `test_communication.py` |

## 🛠 Testing Protocols

### 1. The `conftest.py` Soul
We use a centralized `conftest.py` to ensure the testing environment is isolated and safe:
- **Environment Isolation**: `DUCKDB_DWH_PATH` and `UPLOAD_DIR` are automatically set to `/tmp` to prevent local data corruption.
- **Global Mocking**: We globally mock the `DuckDBTool` and `Postgres` connection pools to ensure speed and zero external dependencies.

### 2. Mocking Guidelines
Always prioritize `unittest.mock` for external services. 
- **LLMs**: Never call real LLM providers in unit tests.
- **Database**: Use the mocked connection pool provided in `conftest.py`.

### 3. Adding New Tests
When adding a new feature:
1. Create a new `test_*.py` file in this directory.
2. Ensure you use appropriate labels (e.g., `@pytest.mark.smoke` for critical paths).
3. Verify that your tests pass without warnings before committing.

---
*Stay elegant. Stay verified. La Passione.*