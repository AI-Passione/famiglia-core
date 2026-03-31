# La Passione Commanding Center

The **Commanding Center** is the primary operational dashboard for monitoring and managing the La Passione AI agent famiglia. Known internally as **"The Silent Concierge,"** it is a cinematic, high-performance environment designed for visual excellence and strategic authority.

---

## ✨ Features
- **The Situation Room**: A centralized hub for real-time monitoring and high-stakes command.
- **Global Operations Pulse**: Live telemetry map providing real-time stats on active agents, priority tasks, and system latency.
- **Intelligence Feed**: A high-fidelity, severity-coded stream of real-time agent decisions and market insights.
- **Directives Terminal**: Integrated task management for issuing and tracking complex instructions.
- **Modern Italian Noir Aesthetic**: Editorial design with tonal layering, Noto Serif typography, and burgandy/gold mechanical accents.

## 🏛️ System Architecture
The Commanding Center follows a modern decoupled architecture:

### 1. [Backend API](backend/README.md)
- **Tech**: FastAPI / Python / PostgreSQL
- **Role**: A robust data layer that interfaces with the existing `AgentContextStore` to expose agent states and logs.

### 2. [Frontend Web](frontend/README.md)
- **Tech**: React 19 / Vite 6 / Tailwind CSS
- **Role**: A high-performance single-page application (SPA) focused on visual excellence and real-time polling.

---

## 🚀 Getting Started

The easiest way to run the entire system is via the root `docker-compose.yml` file.

```bash
docker-compose up --build
```

Access the dashboard at `http://localhost:5173`.

---

## 🐳 Deployment & Containers
Each component is containerized for production reliability. For deep technical details (endpoints, build processes, manual dev setups), see the [Backend](backend/README.md) and [Frontend](frontend/README.md) technical guides.
