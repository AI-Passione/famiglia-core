# Commanding Center API - Technical Reference

This document covers the low-level technical implementation of the FastAPI backend.

## 🛠️ Tech Specs
- **Runtime**: Python 3.12+ (managed with `uv`)
- **Main Script**: `src/command_center/backend/main.py`
- **Slack Interaction**: Houses the Slack bot logic in `src/command_center/backend/slack/`.
- **Context Integration**: Imports `AgentContextStore` from `src.db.context_store`.

## 🔌 API Specification
| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `/agents` | GET | Returns a list of `AgentStatus` models with `msg_count`. |
| `/actions` | GET | Returns `ActionLog[]` limited to latest N. |
| `/tasks` | GET | Returns `TaskInstance[]` with optional status filtering. |
| `/insights` | GET | Returns `InsightSummary[]` from the newsletters table. |
| `/health` | GET | Connectivity check for DB and Redis. |

## 🐳 Docker Internals
- **Dockerfile**: `src/command_center/backend/Dockerfile`
- **Pattern**: Re-uses root project as context to allow imports from `src.*`.
- **Environment**: Requires `.env` with DB and Redis credentials.

## 🚧 Manual Dev Setup
```bash
python -m venv .venv && source .venv/bin/activate
uv sync
python src/command_center/backend/main.py
```
