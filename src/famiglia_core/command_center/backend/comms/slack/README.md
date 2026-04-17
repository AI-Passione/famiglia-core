# 🎩 Slack Famiglia Integration

Orchestrates the multi-agent network on Slack.

## 🏗 Key Components
- **`provisioning.py`**: Handles App Manifest API (8 agents) and channel sync logic.
- **`client.py`**: Manages outbound messaging queue and channel resolution.
- **`app_manifest/`**: YAML definitions for agent identities and scopes.

## ⚡️ Quick Sync
The **Sync Workspace** logic uses stable codes (e.g., `ALFREDO_HQ`, `FINANCE`) to ensure channels are created, renamed, and bots are invited—maintaining a mirrored environment.

## 🚀 Transport
Supports both **Socket Mode** (local) and **HTTP Webhooks** (prod), auto-detected during provisioning.

*“Keep the code elegant and the vibes high.”*
