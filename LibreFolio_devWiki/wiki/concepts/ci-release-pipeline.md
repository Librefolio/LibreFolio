---
title: "CI/CD Release Pipeline"
category: concept
tags: [ci, github-actions, release, docker, playwright, nodejs, vite, deployment, automation]
related:
  - decisions/single-docker-image
  - problems/ghcr-browser-cors-auth-flow
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

### Release Tag Convention (in-app update prompt)
The F14 "new version" prompt reads GitHub's `releases/latest` and compares `tag_name`
numerically against the running version:
- Tag must be SemVer `vX.Y.Z` (leading `v` tolerated); a non-numeric tag compares as `0.0.0` and silently never prompts.
- Drafts and prereleases are never returned by `releases/latest` — the prompt only fires for **stable** releases.
- The release *name* is free-form (display only); the comparison is per-segment numeric.
- GHCR image tags follow the same SemVer tag (plus `latest` and the `-light` variants), keeping the prompt and the published images aligned.
- Full rules: `mkdocs_src/docs/developer/docs/release-pipeline.md` → "Release Tag Convention"; changelog structure rules in `.github/copilot-instructions.md` → "Changelog Rules".

### Update readiness is a two-probe contract

Release publication and image publication are related but not simultaneous:

1. The browser obtains **stable release metadata** from GitHub Releases,
   validates the tag, and compares it with the running version.
2. For a newer release, the browser asks LibreFolio's authenticated same-origin
   endpoint whether the fixed GHCR image tag is **pullable**.

Only the conjunction "newer stable release + published image" produces
`update-available`. A missing manifest is `image-pending`, not "no release".
Authentication/protocol/transport failures fail closed and never make the
frontend announce an update.

The backend step exists because GHCR's anonymous public-manifest flow still
requires a Bearer challenge and token-backed retry, which cannot be completed
reliably by the browser through CORS. The endpoint is narrowly bounded to the
LibreFolio repository and normalized stable tags, validates the expected realm,
service, and pull scope, requests the public token without credentials, and
uses it only for the manifest retry. See
[[problems/ghcr-browser-cors-auth-flow]] for the solved failure mode and trust
boundary.

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
| GHCR image-availability probe | `backend/app/services/container_registry.py` |
| Same-origin system endpoint | `backend/app/api/v1/system.py` |
| Image status schema | `backend/app/schemas/system.py` |
| Release metadata and image gating | `frontend/src/lib/features/update-check/updateCheck.ts` |
| GHCR probe regressions | `backend/test_scripts/test_services/test_container_registry.py` |
