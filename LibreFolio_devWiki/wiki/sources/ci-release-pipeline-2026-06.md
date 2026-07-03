---
title: "CI/CD Release Pipeline (GitHub Actions)"
category: source
source_type: commits
date_ingested: 2026-06-30
original_path: .github/workflows/release.yml
tags: [ci, github-actions, release, docker, playwright, nodejs24, vite, package-lock, polyfill, gallery]
related:
  - concepts/ci-release-pipeline
  - decisions/single-docker-image
---

# Source: CI/CD Release Pipeline (GitHub Actions)

## Summary

A GitHub Actions release pipeline (`release.yml`) was introduced (commit `a688bcb9`) and refined through 8 subsequent commits (up to `b79735e2`). The pipeline automates the full build→test→docker→push→release sequence. Trigger modes: push to `dev`, published releases, manual `workflow_dispatch`. Node.js upgraded to 24 in CI; Vite upgraded to 7.3.5; `package-lock.json` added for reproducible frontend builds; `crypto.randomUUID` polyfill added for older browser compatibility. Playwright gallery generation: workers reduced to 8, network-idle timeout added; screenshot cache enabled in CI for faster re-runs.

## Key Takeaways

- **Pipeline stages**: Checkout → Python 3.13 + Pipenv → Node.js 24 → DB setup → Backend tests → Frontend build → Playwright E2E + gallery → Docker build → Docker push to GHCR → MkDocs deploy → GitHub Release.
- **Trigger modes**: `push: dev`, `release: [published]`, `workflow_dispatch` (manual, with `force_gallery` boolean input).
- **Docker `:test` tag**: pre-release Docker images tagged `:test` (not `:latest`) until release confirmed. Published releases promote to `:latest` and `:vX.Y.Z`.
- **Volume path fix**: Docker volume path corrected in `docker-compose.yml`.
- **Node.js 24**: Upgraded from 20/22 to 24 in CI to match local development environment.
- **Vite 7.3.5**: Upgraded from 6.x; no breaking changes needed.
- **`package-lock.json`**: Added to repo to pin all transitive npm dependencies. `npm ci` used in CI (instead of `npm install`) for reproducibility.
- **`crypto.randomUUID` polyfill**: Added for browsers that don't support the API natively (needed for UUID-based link generation in transaction modals on older Android).
- **Playwright optimizations**: reduced gallery workers from 16 to 8 (stability); added `networkidle` timeout strategy for screenshot stability; screenshot cache layer in CI (keyed by commit hash).
- **`formatMoney` refactor**: function signature simplified (breaking internal change, no API impact).
- **Playwright version retrieval**: updated to use new Playwright CLI method.

## Wiki Pages Created/Updated

- [[concepts/ci-release-pipeline]] — new: pipeline architecture overview

## Source files

| Role | Path |
|------|------|
| Release workflow | `.github/workflows/release.yml` |
| Package lock | `package-lock.json` |
| Docker compose | `docker-compose.yml` |
| Dockerfile | `Dockerfile` |
| Vite config | `frontend/vite.config.ts` |
| dev.py (debug diagnostics) | `dev.py` |
