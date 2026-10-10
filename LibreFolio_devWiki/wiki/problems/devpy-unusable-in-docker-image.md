---
title: "No `dev.py` command worked inside the Docker image (1.1.0): the CLI imported the test tree the image excludes"
category: problem
status: resolved
date: 2026-10-08
tags: [docker, cli, devpy, deployment, imports, healthcheck, self-hosting]
related: [entities/devpy-cli, features/F-062, features/F-063, decisions/single-docker-image, concepts/silent-no-op-option, sources/phase00-dev-cli-image-2026-10]
---

# Problem: `dev.py` unusable in the container

## Symptom

In the 1.1.0 image, `docker compose exec librefolio python dev.py user reset …` — the documented way to reset a
forgotten password on a Docker install — failed with an import error. In fact **no** `dev.py` command worked in the
container, not even `info`.

## Root cause

`dev.py` imported its command groups eagerly. Building the parser imported the test runner, and
`normalize_coverage_argv` imported `backend.test_scripts` — which `.dockerignore` excludes from the image (it ships
the application, not the development tree). Earlier `try/except ImportError` blocks around some groups hid the
dependency instead of stating it.

## Solution (train 19, merge `cdde3bc4d`)

- `_has(paths)` checks, **before importing**, whether what a command group needs is part of this installation; never
  by catching `ImportError`, so that in a full checkout a broken import stays loud.
- A missing group is still listed, by `_add_unavailable()`: "… — not available in this installation"; running it
  explains what is missing and exits with status **2**. The stub parses with `prefix_chars="\x00"`, so `test --help`
  or `test --coverage …` reach the explanation instead of argparse's "unrecognized arguments". It covers `test`,
  `i18n` and `mkdocs translate*`; the old silent `try/except` blocks are gone.
- What works in the container: `user *` and `info` with the server running; `db current` / `db check`; `db upgrade`
  is refused while the server runs, by design. The image carries `backend/` (without tests or data), `scripts/`,
  `dev.py`, `Pipfile`, `frontend/package.json`, `VERSION` and `.env.example` as `.env`, with only the `[packages]`
  dependencies — no pipenv, npm or pytest.
- The forgot-password card shows both commands: the Docker one and the manual-install one.
- **HEALTHCHECK** probed `${PORT}`, but inside the container uvicorn always listens on 6040 (`PORT` is the host side of
  the mapping): a container started with `-e PORT=…` and without compose showed as unhealthy. It now probes
  `localhost:6040`.
- Test: `test_dev_cli_image.py`, registered as `utils dev-cli-image`.

## Prevention

Domain: [[domains/infrastructure]].

- A CLI that ships in two shapes (development tree, runtime image) decides from the filesystem what it can offer, and
  says so; it never swallows an import error.
- Run the image's own CLI in CI (`utils dev-cli-image`), not only the server.

## Impact

Docker users could not reset a password or run any maintenance command from the container in 1.1.0. Backlog N-8
(a `PORT` in `.env` reaching the container through `env_file`) is a related, unproven edge.

## Source files

| Role | Path |
|------|------|
| `_has`, `_add_unavailable`, conditional registration | `dev.py` |
| Image contents, HEALTHCHECK on 6040 | `Dockerfile` |
| Excluded development tree | `.dockerignore` |
| Forgot-password card (both commands) | `frontend/src/lib/components/auth/ForgotPasswordCard.svelte` |
| Test | `backend/test_scripts/test_utilities/test_dev_cli_image.py` |
| Runner registration (`utils dev-cli-image`) | `scripts/test_runner/_backend_utils.py` |
| Admin doc (container commands) | `mkdocs_src/docs/admin/docker_advanced.en.md` |
| Plan | `LibreFolio_developer_journal/Release_2/phases/35_devCliImage/plan-phase00DevCliImage.prompt.md` |
