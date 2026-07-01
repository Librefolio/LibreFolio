---
title: "CI/CD Release Pipeline"
category: concept
tags: [ci, github-actions, release, docker, playwright, nodejs, vite, deployment, automation]
related:
  - decisions/single-docker-image
  - sources/ci-release-pipeline-2026-06
---

# Concept: CI/CD Release Pipeline

## Definition

The LibreFolio release pipeline is a GitHub Actions workflow (`.github/workflows/release.yml`) that automates the full build, test, containerize, and publish sequence. It ensures no manual steps are required between a `git push` and a published release with Docker image and updated documentation.

## Trigger Modes

| Trigger | When | Notes |
|---------|------|-------|
| `push: dev` | Every push to `dev` branch | Runs full pipeline but no release |
| `release: [published]` | GitHub release published | Full pipeline + Docker `:latest` + MkDocs deploy |
| `workflow_dispatch` | Manual via GitHub UI | Optional `force_gallery` flag to bypass cache |

## Pipeline Stages

```
1. Checkout (fetch-depth: 0 for MkDocs gh-deploy history)
2. Python 3.13 + Pipenv (cache: Pipenv.lock hash)
3. Node.js 24 + npm ci (cache: package-lock.json hash)
4. DB setup (dev.py db create-clean)
5. Backend tests (pytest)
6. Frontend build (vite build)
7. Playwright E2E + gallery screenshots (8 workers, networkidle)
8. Docker build → tag :test (pre-release) or :latest + :vX.Y.Z (release)
9. Docker push to GHCR (ghcr.io/librefolio/librefolio)
10. MkDocs gh-deploy (on release only)
11. GitHub Release assets upload
```

## Key Design Decisions

### Docker Tags
- Pre-release builds (push to dev): `:test` tag only
- Published releases: `:latest` + `:vX.Y.Z` (semantic version from release tag)
- Ensures production images are always tied to a named release

### Reproducible Frontend Builds
- `package-lock.json` committed to repo
- CI uses `npm ci` (not `npm install`) — installs exactly from lockfile
- Vite 7.3.5 pinned as current production version

### Screenshot Cache
- Gallery screenshots cached in CI by commit hash
- `force_gallery: true` in `workflow_dispatch` bypasses cache
- Reduces CI time by 3–5 minutes on typical runs where screenshots haven't changed

### Playwright Stability
- Workers reduced from 16 to 8 (fewer timeouts on CI runners)
- `networkidle` wait strategy added (was `domcontentloaded`)

## Browser Compatibility
- `crypto.randomUUID` polyfill added for link_uuid generation on older Android browsers that lack the API

## Source files

| Role | Path |
|------|------|
| Release workflow | `.github/workflows/release.yml` |
| Package lock | `package-lock.json` |
| Docker compose | `docker-compose.yml` |
| Dockerfile | `Dockerfile` |
