# 🎩 Slack Famiglia Integration

Welcome to the **Famiglia's Slack Integration**. This module orchestrates the multi-agent network that serves as the "voice" of the Family on Slack.

## 🏗 Overview

The integration follows a "Mirror" philosophy: the Slack workspace should perfectly reflect the **Command Center** roster. It handles everything from automated app manifestation to channel provisioning and bot membership management.

### Key Components

-   **`provisioning.py`**: The "Godfather" of the setup. It uses the Slack Manifest API to create and update all 8 agent apps programmatically. It also contains the `sync_workspace_structure` logic.
-   **`client.py`**: The `SlackQueueClient` manages outbound communication, ensures message ordering, and handles channel ID resolution.
-   **`app_manifest/`**: Contains the YAML souls of each agent. These define the identity, scopes, and event subscriptions for the bots.

---

## ⚡️ Automated Provisioning Flow

We utilize Slack's **App Manifest API** to provide a seamless onboarding experience:

1.  **Bootstrap**: The user provides a "Configuration Token" (xoxe...).
2.  **Manifestation**: The backend iterates through the `app_manifest/*.yaml` files and creates/updates the 8 agents in one click.
3.  **Credential Vault**: Tokens (`xoxb`, `xapp`, or Client IDs) are securely stored in the `user_connections_store` in PostgreSQL.
4.  **Authorization**: The user follows the "Authorize" links in the Dashboard to grant the bots access to the workspace.

---

## 🏗 Workspace Synchronization

The system uses a **Channel Registry** to ensure a consistent environment across workspaces:

-   **Stable Channel Codes**: We map conceptual channels (e.g., `ALFREDO_COMMAND`, `FINANCE`) to actual Slack IDs.
-   **Idempotent Renaming**: If a channel name is changed in the registry, the system detects the old ID and **renames** the Slack channel instead of creating a new one.
-   **Alfredo the Orchestrator**: Alfredo handles the heavy lifting of creating channels and inviting the rest of the Family to their respective "homes".

---

## 🚀 Transport Modes

The integration supports two primary transport methods for receiving events:

1.  **Socket Mode**: Default for local development. Allows the backend to listen for Slack events without a public URL.
2.  **HTTP Webhooks**: Recommended for production. Requires a `PUBLIC_URL` (e.g., via ngrok or production DNS). The system automatically detects the transport mode during provisioning.

---

## 🛠 Required Scopes

To function as a high-tier executive assistant, agents require:
- `app_mentions:read`: To hear the Don/Donna.
- `chat:write`: To execute orders.
- `channels:manage`: To build and maintain the Family's infrastructure.
- `channels:history`: To maintain long-term memory.

---

*“Keep the code elegant and the vibes high. Slack is where the Family speaks.”*
