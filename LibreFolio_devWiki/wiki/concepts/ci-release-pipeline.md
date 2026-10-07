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

The LibreFolio release pipeline is one GitHub Actions job (`.github/workflows/release.yml`)
that validates the docs, generates the gallery screenshots, builds and pushes the two
Docker image variants, deploys the docs site and annotates the GitHub release. It runs
**no test suite**: tests live in `manual-test-run.yml` and in the developers' lanes.
The developer-facing description is `mkdocs_src/docs/developer/docs/release-pipeline.md`;
`backend/test_scripts/test_utilities/test_release_image_contract.py`
(`dev.py test utils release-image-contract`) pins the rules below.

## Trigger Modes

| Trigger | `run-name` | What it publishes |
|---------|-----------|-------------------|
| `push: dev` | `Nightly (dev)` | images `nightly` (full) and `nightly-light`; no deploy |
| `release: published` | `Release vX.Y.Z` | images `X.Y.Z` (full), `X.Y.Z-light` and `latest` (light); docs deploy; release-notes snippet |
| `workflow_dispatch` | `Manual run (<branch>)` | from `main`: `latest` (light) + docs deploy, the full variant is skipped; from `dev`: like a nightly; from any other branch: no image is pushed |

There is no `push: main` trigger and no `force_gallery` input (both appear in old notes).

## Pipeline Stages (2026-10)

```
1. Checkout (fetch-depth 0), Python 3.13 + Pipenv, Node 24
2. Caches: Pipenv venv, npm, Playwright browsers; keys = runner.os + RUNNER_IMAGE_OS
3. Install (pipenv --dev, dev.py install), VERSION file frozen from git describe
4. Docs checks: translate-diff --issues-only, translate-validate --hide-localized, check-links
5. mkdocs build (before the gallery: the test server starts fast with site/ present)
6. Gallery: dev.py mkdocs gallery --workers 4 (always runs; no screenshot cache)
7. Production frontend rebuild (the gallery's server --test leaves a debug build)
8. mkdocs build again, now with the screenshots
9. Nightly report of soft-failed steps (dev only)
10. Docker metadata → build+push LIGHT first, then FULL (each only if it has tags)
11. gh-pages deploy (main or release), artifacts, release-notes append (release)
```

## Key Design Decisions

### Release gates and nightly tolerance
- Steps 4, 5, 6 (gallery) and 8 are `continue-on-error` **only on `dev`**. A nightly
  continues and lists them in the job summary; on any other run, a published release
  included, they fail the pipeline.
- The gallery became a gate in R12 (2026-10-07): the images bundle the screenshots and a
  release deploys the docs site, so a release must not ship missing or broken shots.
  Before, `|| echo ::warning::` swallowed every failure on every branch.
- Evidence survives a failure: the screenshot artifact runs under `!cancelled()`, and a
  dedicated artifact keeps `frontend/playwright-report/` + `frontend/test-results/` for 3
  days whenever the gallery failed (dev included).

### Docker tags (user guide "Image Variants" is the spec)
- `latest` = **light**; a release publishes the full variant only as `X.Y.Z` and the light
  one as `X.Y.Z-light`; nightlies are `nightly` / `nightly-light`. Image tags never carry
  the `v` of the GitHub release tag (metadata-action `{{version}}`).
- The full metadata step sets `flavor: latest=false`: metadata-action otherwise adds
  `latest` to every `type=semver` release tag, and both variants used to push `latest`
  (the light one won only because it was pushed second). `latest-light` no longer exists.
- Each build runs only if its own metadata produced tags (`if: steps.<meta>.outputs.tags != ''`):
  a push without a tag fails, which used to break manual runs from `main` and other branches.
- Local `dev.py docker build` tags differ on purpose: they come from `git describe` and keep
  the `v` (`librefolio:v1.2.3-light`, aliases `librefolio:latest[-light]`).

### Push order serves the update prompt
The in-app prompt's image gate probes the plain `X.Y.Z` tag, i.e. the **full** variant
(`container_registry.py`). The light build therefore runs first and the full one last:
when admins are prompted, `latest` and `X.Y.Z-light` already exist; if the light build
fails, `X.Y.Z` is never pushed and nobody is told to update to an image `latest` does not
have yet.

### Release Tag Convention (in-app update prompt)
The F14 "new version" prompt reads GitHub's `releases/latest` (admins only, probed at most
once an hour):
- The tag must be a stable `vX.Y.Z` (leading `v` tolerated); any other tag is rejected and
  never prompts. Drafts and prereleases are never returned by `releases/latest`.
- The prompt also requires the image to be pullable (next section).
- Full rules: `mkdocs_src/docs/developer/docs/release-pipeline.md`; changelog structure
  rules in `.github/copilot-instructions.md` → "Changelog Rules".

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
- `frontend/package-lock.json` committed; installs come from the lock (`npm ci` via `dev.py install`).
- The npm and Playwright caches are keyed per runner image as well: `ubuntu-latest` moves from
  24.04 to 26.04 (actions/runner-images#14748, 2026-10-19 → 11-19) and `runner.os` is `Linux`
  on both. The runner itself stays unpinned by the developer's choice.

### Gallery fixture for the dashboard shots
- The dashboard shots mock `POST /api/v1/portfolio/report` with `frontend/e2e/dashboard-report.json`,
  a **real** capture normalized to a 50 000 net worth (`scripts/normalize_dashboard_fixture.py`,
  capture procedure in its docstring). A stale capture made the shots render an empty dashboard
  from 2026-09-11 (`yield_on_cost` became required) until R12; the Vitest guard
  `frontend/src/lib/api/dashboardReportFixture.test.ts` now fails in seconds instead.

## Browser Compatibility
- `crypto.randomUUID` polyfill added for link_uuid generation on older Android browsers that lack the API

## Source files

| Role | Path |
|------|------|
| Release workflow | `.github/workflows/release.yml` |
| Package lock | `frontend/package-lock.json` |
| Docker compose (end users) | `docker-compose.prod.yml` |
| Dockerfile | `Dockerfile` |
| GHCR image-availability probe | `backend/app/services/container_registry.py` |
| Same-origin system endpoint | `backend/app/api/v1/system.py` |
| Image status schema | `backend/app/schemas/system.py` |
| Release metadata and image gating | `frontend/src/lib/features/update-check/updateCheck.ts` |
| GHCR probe regressions | `backend/test_scripts/test_services/test_container_registry.py` |
| Release contract tests | `backend/test_scripts/test_utilities/test_release_image_contract.py` |
| Frontend production guard (image) | `scripts/docker/check_frontend_build.sh` |
| Developer page | `mkdocs_src/docs/developer/docs/release-pipeline.md` |
| Gallery dashboard fixture guard | `frontend/src/lib/api/dashboardReportFixture.test.ts` |
| Fixture normalization | `scripts/normalize_dashboard_fixture.py` |
