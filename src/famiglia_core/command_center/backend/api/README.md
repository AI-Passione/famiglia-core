# La Passione Commanding Center - Unified API

This directory contains the core FastAPI implementation for the Famiglia's Commanding Center. It follows a modular structure to ensure maintainability and high-vibe development.

## 🏗 Folder Structure

- **`main.py`**: The central entry point. Orchestrates the FastAPI instance, mounts static files, and includes all sub-routers.
- **`routes/`**: Contains specialized API modules:
    - **`famiglia.py`**: Managing the AI Agent dossiers, including persona edits, capability syncing (Skills, Tools, Workflows), and profile picture uploads.
    - **`chat.py`**: Handles Directives Terminal interactions and SSE streaming.
    - **`auth.py`**: Core authentication and identification logic.
    - **`connections.py`**: Managing external service integrations.
    - **`settings.py`**: Persisted user preferences and system configurations.
- **`services/`**: contains business logic modules (e.g., `engine_room_service.py` for system health and docker orchestration).
- **`graph_parser.py`**: Specialized logic for parsing agentic workflow definitions from the `features/` directory.

## 🚀 Key Endpoints

- `/api/v1/famiglia/agents`: Active roster of AI agents.
- `/api/v1/famiglia/capabilities`: Data for agent specialization dropdowns.
- `/api/v1/famiglia/agents/{id}/avatar`: Multi-part profile picture management.
- `/api/v1/engine-room`: Real-time system diagnostics.

## 🎨 Vibe Coding Norms

1. **Modularity First**: All new features should reside in a dedicated router file.
2. **Type Safety**: Use Pydantic models for all request and response bodies.
3. **Persitence**: Always sync changes back to the PostgreSQL "Source of Truth" via `context_store.py`.
