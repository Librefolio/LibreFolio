---
title: "System Info empty in Docker (App Version: unknown, 0 dependencies)"
category: problem
status: resolved
date: 2026-07-20
tags: [docker, deployment, system-info, settings, pipfile]
related: [decisions/single-docker-image]
---

# Problem: System Info empty in Docker (App Version: unknown, 0 dependencies)

## Symptom
Settings → About → "Copy for Issue" (and the on-screen "Credits" foldable
lists) showed `App Version: unknown` and empty Backend/Frontend
Dependencies — but **only** when running from the Docker image. Local dev
(`./dev.py server`) always worked correctly.

## Root Cause
`Dockerfile` builds a runtime-only image: it copies `backend/`, `scripts/`,
`dev.py`, the **pre-built** `frontend/build/`, and the **pre-built**
`mkdocs_src/site/` — but never `.git/`, `Pipfile`, or the frontend's
*source* manifest `frontend/package.json` (only the compiled static site).

`backend/app/api/v1/system.py` derives all three broken fields from those
missing sources, and each fails via a silent `try/except: pass` (by
design, so the endpoint never 500s) — it just silently returns empty data:

| Field | Reads | Missing in image |
|---|---|---|
| `app_version` | `version.py::get_git_version()` → `git describe` in `PROJECT_ROOT` | no `.git/` |
| `backend_dependencies` | `system.py::parse_pipfile()` reads `PROJECT_ROOT / "Pipfile"` | not copied |
| `frontend_dependencies` | `system.py::get_frontend_deps()` reads `.../frontend/package.json` | not copied |

The repo already had precedent for this exact class of problem:
`requirements.txt` is also gitignored and generated fresh by
`_docker_ensure_assets_built()` in `dev.py` right before `docker build`
runs, then `COPY`ied in. This fix mirrors that same pattern.

## Solution
- `Dockerfile`: `COPY Pipfile ./`, `COPY frontend/package.json
  ./frontend/package.json`, `COPY VERSION ./` (all copy the *source*/
  manifest, not `node_modules/` or `.git/` — negligible image size
  impact).
- `dev.py::_docker_ensure_assets_built()`: added a step that deletes any
  stale `VERSION` file, clears `get_git_version()`'s `lru_cache`, then
  writes the fresh value — same value already used for the image tag in
  `_get_docker_tag()`.
- `backend/app/utils/version.py::get_git_version()`: checks
  `PROJECT_ROOT / "VERSION"` first (stripped content) before falling back
  to the original `git describe` subprocess logic (local dev unaffected).

### Gotcha: cache the VERSION file bypass would create
Once `get_git_version()` prefers an existing `VERSION` file, a naive
"regenerate" step would just re-read the stale file it's trying to
replace (chicken-and-egg). Fixed by deleting the old `VERSION` file
*before* calling `get_git_version()` again, so it's forced to fall
through to a true `git describe`.

## Bonus fix (found during investigation, unrelated to Docker)
`parse_pipfile()`'s regex `^([a-zA-Z0-9_-]+)\s*=` could never match a
**quoted** package name, e.g. `"borsa-italiana-scraping " = {git = ...}`
(Pipfile has a stray trailing space inside the quotes). "Borsa Italiana
Scraping" never appeared in Backend Dependencies in **either**
environment. Fixed with `^"?([a-zA-Z0-9_-]+)\s*"?\s*=` (handles both
plain and quoted forms, tolerates the trailing space since it's outside
the capture group).

## New field added while fixing this: `deployment_mode`
Added `deployment_mode: "docker" | "local"` to `SystemInfoResponse`,
detected via `Path("/.dockerenv").exists()` — the standard,
dependency-free way to detect running inside any Docker container
regardless of base image.

## Verification
```bash
# Local:
curl http://localhost:6040/api/v1/system/info   # deployment_mode: "local"

# Docker:
./dev.py docker build
docker run --rm librefolio:latest cat /app/VERSION   # non-empty, matches image tag
# deployment_mode: "docker", backend/frontend deps populated,
# "Borsa Italiana Scraping" present in both environments
```

## Related
See [[problems/docker-entrypoint-gid20-collision]] — a *separate*,
unrelated, still-open bug discovered while verifying this fix (blocks
`docker compose up` on macOS hosts).

## Source files

| Role | Path |
|------|------|
| Version resolution | `backend/app/utils/version.py` |
| System info endpoint | `backend/app/api/v1/system.py` |
| VERSION file generation | `dev.py` (`_docker_ensure_assets_built()`) |
| Docker image build | `Dockerfile` |
| Frontend display | `frontend/src/lib/components/settings/tabs/AboutTab.svelte` |
| Regression tests | `backend/test_scripts/test_api/test_system_api.py` |
