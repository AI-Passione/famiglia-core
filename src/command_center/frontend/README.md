# Commanding Center Frontend - Technical Reference

This document covers the low-level build details and internal architecture of the React dashboard.

## 🛠️ Tech Specs
- **Framework**: React 19 (TypeScript)
- **Build Tool**: Vite 6
- **Animations**: Framer Motion
- **Icons**: Lucide React

## 🏛️ Project Structure
- `src/App.tsx`: Main application entry and polling logic.
- `src/index.css`: CSS Variables and global glassmorphism tokens.
- `src/main.tsx`: React DOM mount point.

## 🐳 Docker / Build Pipeline
The `Dockerfile` employs a multi-stage production-ready build:
1.  **Stage 1 (Node)**: Installs dependencies and runs `npm run build`.
2.  **Stage 2 (Nginx)**: Copies `dist/` into a slim Alpine Nginx image.

## 🚧 Manual Dev Setup
```bash
cd src/command_center/frontend
npm install
npm run dev
```
Default Dev Port: `5173`.
Dashboard expects API at `localhost:8000` by default.
