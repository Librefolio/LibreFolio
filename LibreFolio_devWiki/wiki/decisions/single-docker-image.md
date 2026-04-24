---
title: "Single Docker image: FastAPI serves static frontend"
category: decision
status: resolved
date: 2026-01-01
tags: [deployment, docker, fastapi, sveltekit, ops]
related: [decisions/sveltekit-over-react]
---

# Decision: Single Docker Image — FastAPI Serves Static Frontend

## Context
LibreFolio needs a self-hosted deployment model that is simple to run for non-technical users. The choice of deployment architecture affects complexity, port exposure, and the development workflow (pre-build requirements).

## Options Considered
1. **Separate containers (FastAPI + nginx + frontend)** — standard but more complex; nginx config, multiple ports, docker-compose orchestration overhead.
2. **Single container: FastAPI serves static files** — FastAPI's `StaticFiles` mount serves the SvelteKit build at `/*`. One container, one port, one image.
3. **Dedicated CDN/edge for frontend** — overkill for self-hosted use case.

## Decision
**Single Docker image** with FastAPI serving both API and static files. Key reasons:
- Zero nginx configuration complexity for the user
- Single `docker run` or `docker-compose up` to start
- `adapter-static` SvelteKit build is pure HTML/JS/CSS — no SSR needed
- Volumes provide data persistence without Docker complexity

## Consequences
- **Frontend must be pre-built on host** before `docker build`: `./dev.py front build`
- **MkDocs must be pre-built on host** before `docker build`: `./dev.py mkdocs build`
- `COPY frontend/build/ ./frontend/build/` and `COPY mkdocs_src/site/ ./mkdocs_src/site/` in Dockerfile
- Base image: `python:3.13-slim`
- Single `CMD`: `uvicorn backend.app.main:app --host 0.0.0.0 --port 8000`
- `EXPOSE 8000` (prod) and `8001` (test mode)
- Volume mount: `/app/backend/data/prod/` for SQLite + uploaded files
- FastAPI routes: `/api/v1/*` for API, `/*` for static SvelteKit SPA

## Links
- Source: `Dockerfile`

## Source files

| Role | Path |
|------|------|
| Dockerfile | `Dockerfile` |
| docker-compose | `docker-compose.yml` |
| Frontend build | `frontend/build/` |
| MkDocs build | `mkdocs_src/site/` |
