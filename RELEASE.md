# Release Process - Famiglia Core

This document outlines the release process for the `famiglia-core` engine, powered by `semantic-release` and GitHub Actions.

## 🚀 Single Branch Strategy

To ensure simplicity and stability, we use the `main` branch for both staging and production releases.

### 1. Staging builds
- **Purpose**: All development features and bug fixes are merged into `main` after review.
- **Automation**: Every push to `main` triggers a GitHub Action to build and push the `:staging` image.
- **Output**: A Docker image tagged with `staging` and the short git SHA is pushed to GHCR.

### 2. Production releases
- **Purpose**: Formal releases with versioned tags (e.g., `v1.2.3`).
- **Automation**: These releases are manually triggered via GitHub Actions.
- **Manual Trigger**: 
  1. Go to the **Actions** tab.
  2. Select **Manual Production Release**.
  3. Click **Run workflow** and select the `main` branch.
- **Output**: 
  - A new GitHub Release and Tag (e.g., `v1.2.3`).
  - An updated `CHANGELOG.md`.
  - A production Docker image tagged with the version number (e.g., `:1.2.3`), `:production`, and `:latest`.

---

## 🛠 Semantic Release

We use `semantic-release` to automate versioning based on [Conventional Commits](https://www.conventionalcommits.org/).

- `fix(scope): ...` -> Triggers a **Patch** release (0.0.1)
- `feat(scope): ...` -> Triggers a **Minor** release (0.1.0)
- `feat(scope)!: ...` or `BREAKING CHANGE: ...` -> Triggers a **Major** release (1.0.0)

---

## 📦 Docker Container Registry

All images are hosted on GHCR: `ghcr.io/AI-Passione/famiglia-core`.

To pull the latest production image:
```bash
docker pull ghcr.io/AI-Passione/famiglia-core:latest
```

To pull the latest staging image:
```bash
docker pull ghcr.io/AI-Passione/famiglia-core:staging
```

---

## 🔐 Environment Variables

The release workflows and the Docker images rely on environment variables. See [.env.example](.env.example) for the required configuration.

> [!IMPORTANT]
> The `GH_TOKEN` (or `GITHUB_TOKEN`) must have `contents: write`, `packages: write`, and `issues: write` permissions to perform a full semantic release.
