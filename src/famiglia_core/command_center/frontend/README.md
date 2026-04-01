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

## 🌍 Public Demo (via GitHub Pages)
The frontend can now be deployed through `.github/workflows/pages.yml`.

This GitHub Pages path is meant for **demo/showcase usage only**. It is useful for exposing the visual Command Center shell on the public internet, but it is not the primary production deployment model for the full platform.

- Static assets use a relative Vite base so the build works on both repo-scoped Pages URLs and a custom domain.
- `public/CNAME` is set to `aipassione.com`. Change that file if you want a subdomain instead.
- Production API calls are controlled through Vite env vars:
  - `VITE_API_BASE`: full API prefix, for example `https://api.aipassione.com/api/v1`
  - `VITE_BACKEND_BASE`: optional alternative that expands to `${VITE_BACKEND_BASE}/api/v1`
- The workflow defaults `VITE_API_BASE` to `https://api.aipassione.com/api/v1`, but a GitHub repository variable with the same name will override it.

For a live demo that still calls backend services, the backend must also be public and configured with:
- `FRONTEND_BASE_URL=https://aipassione.com`
- `BACKEND_BASE_URL=https://api.aipassione.com`
- `CORS_ALLOW_ORIGINS=https://aipassione.com,https://ai-passione.github.io`

For the main production system, prefer the containerized deployment path described in the root project documentation.
