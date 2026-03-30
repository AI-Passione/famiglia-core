# Observability Stack

This project implements observability in two layers:

## 1. Infrastructure Observability
**Scope:** CPU, RAM, Disk, and logs for all containers (App, PostgreSQL, Redis, Ollama, etc.)
**Tools:** Grafana, Loki, Prometheus, Promtail, Docker Stats Exporter

### Access
- **Grafana Dashboard:** `http://localhost:3000` (Default: `admin`/set in `.env`)
- **Loki URL:** `http://localhost:3100`
- **Prometheus URL:** `http://localhost:9090`

---

## 2. AI Observability (Agent Tracing)
**Scope:** LangGraph orchestration, LLM trace cycles, and token costing.
**Tools:** Langfuse

### Current Architecture (Stable)
- **Server**: **Langfuse v2** (`image: langfuse/langfuse:2`). We use v2 to avoid the heavy ClickHouse/Zookeeper dependencies required by v3.
- **SDK**: **Langfuse Python SDK v2.53.x**. This uses a native REST client rather than OpenTelemetry (OTEL), ensuring compatibility with the v2 server.
- **Compatibility**: To support **LangChain 0.3**, we use a `sys.modules` monkeypatch in `langfuse_util.py` to bridge the legacy SDK's expected imports.

### Configuration
Update these in your `.env` after first setup:
```bash
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_HOST=http://localhost:3001
```

### Access
- **Langfuse Dashboard:** `http://localhost:3001`
- **First Login:** Create a new project and use the keys to update your `.env`.

### Troubleshooting: Schema Wipe
If you experience a Prisma error (e.g. `relation "observations_view" does not exist`) when switching between server versions, you must wipe the database volume:
```bash
docker compose rm -s -f langfuse-db langfuse
docker volume rm la-passione-inc_langfuse_db_data
docker compose up -d langfuse
```



