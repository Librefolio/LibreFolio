---
title: "Phase 0 / 35 — `dev.py` inside the Docker image (train 19)"
category: source
source_type: plan
date_ingested: 2026-10-09
original_path: LibreFolio_developer_journal/Release_2/phases/35_devCliImage/plan-phase00DevCliImage.prompt.md
tags: [phase0, release2, docker, cli, devpy, healthcheck, self-hosting]
related:
  - problems/devpy-unusable-in-docker-image
  - entities/devpy-cli
  - features/F-062
  - features/F-063
  - decisions/single-docker-image
---

# Source: Phase 0 / 35 — the CLI in the image

## Summary

One plan (~195 lines), merged in train 19 (`cdde3bc4d`; commits `5dca6e2cf`, `793aab393`, `5fe027f8f`) and archived on
2026-10-09. In 1.1.0 no `dev.py` command worked inside the container — not even the documented password reset —
because the CLI imported the test tree that the image excludes. The fix registers each command group only when its
files are present and turns the others into explicit "not available in this installation" stubs; on the way the
HEALTHCHECK was moved to the port the server really binds.

## Key takeaways

- Root cause, fix, what works through `docker compose exec`, the HEALTHCHECK: [[problems/devpy-unusable-in-docker-image]].
- Decide availability from the filesystem before importing; never hide a broken import behind `except ImportError`.
- The image ships the application, not the development tree: only `[packages]` dependencies, no pipenv, npm or pytest.

## Residuals

None of its own; backlog N-8 (a `PORT` from `.env` inside the container) comes from the `db <path>` plan.

## Wiki pages updated

- [[problems/devpy-unusable-in-docker-image]] — new.
- [[entities/devpy-cli]], [[features/F-062]], [[features/F-063]] — image behaviour, HEALTHCHECK.

## Source files

| Role | Path |
|------|------|
| Plan | `LibreFolio_developer_journal/Release_2/phases/35_devCliImage/plan-phase00DevCliImage.prompt.md` |
| Forgot-password card | `frontend/src/lib/components/auth/ForgotPasswordCard.svelte` |
| Test | `backend/test_scripts/test_utilities/test_dev_cli_image.py` |
| Admin doc | `mkdocs_src/docs/admin/docker_advanced.en.md` |
