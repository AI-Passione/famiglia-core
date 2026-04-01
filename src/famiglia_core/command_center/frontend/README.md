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

## 🌍 GitHub Pages
The frontend can now be deployed through `.github/workflows/pages.yml`.

- Static assets use a relative Vite base so the build works on both repo-scoped Pages URLs and a custom domain.
- `public/CNAME` is set to `ai-passione.com`. Change that file if you want a subdomain instead.
- Production API calls are controlled through Vite env vars:
  - `VITE_API_BASE`: full API prefix, for example `https://api.ai-passione.com/api/v1`
  - `VITE_BACKEND_BASE`: optional alternative that expands to `${VITE_BACKEND_BASE}/api/v1`
- The workflow defaults `VITE_API_BASE` to `https://api.ai-passione.com/api/v1`, but a GitHub repository variable with the same name will override it.

For the deployed site to work end-to-end, the backend must also be public and configured with:
- `FRONTEND_BASE_URL=https://ai-passione.com`
- `BACKEND_BASE_URL=https://api.ai-passione.com`
- `CORS_ALLOW_ORIGINS=https://ai-passione.com,https://ai-passione.github.io`
