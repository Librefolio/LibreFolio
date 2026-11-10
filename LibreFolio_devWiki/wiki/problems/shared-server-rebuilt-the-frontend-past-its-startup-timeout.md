---
title: "`all-backend` gave up before pytest: after a production build, the shared test server rebuilt the frontend in debug mode, and under load that outlasted its 300 s startup"
category: problem
status: resolved
date: 2026-10-12
tags: [testing, test-runner, frontend-build, debug-build, timeout, load, environment, workstream-u, release-1.2]
related:
  - problems/release-images-shipped-debug-frontend
  - decisions/plugin-folders-and-split-i18n
  - problems/mutation-restore-keeps-old-mtime-skips-frontend-rebuild
---

# Problem: the server was still building when the runner stopped waiting

## Symptom

Workstream U's first `all-backend` run of U-3 (2026-10-12, 22:48) stopped after five minutes with «Shared backend did
not answer within 300s», before pytest had started. The database had been created correctly.

## Root Cause

- The test server forces debug mode and rebuilds `frontend/build/` when the last build is not a debug one — the same
  mechanism behind [[problems/release-images-shipped-debug-frontend]]. U's own frontend gates had just left a
  production build, so the server started with a debug rebuild of about 3.7 minutes.
- The rebuild ended at 22:52:14 (the `.build-debug` marker); uvicorn then still had to start the app at a load average
  of 36, and the 300 s ran out at 22:53:30.
- The verdict: environment and slowness, not the code under test.

## Solution

With the debug build fresh, the same run was relaunched unchanged: the server started without rebuilding, and the run
passed (7 categories of 7, 12 857 passed, 0 failed). U's rule for next time: run `all-backend` before a production
build, not after — or build in debug first.

2026-11-07 lint: fixed in the runner since `9dc5c407e` (15/10, C-94). `SharedTestServer.start()` first runs
`dev.py server --test --build-only` in the foreground (`build_server_prerequisites` in
`scripts/test_runner/_server.py`), and only then spawns the backend and starts `STARTUP_TIMEOUT` (300 s,
`LIBREFOLIO_TEST_STARTUP_TIMEOUT`): a debug rebuild after a production build is visible and no longer counts against
the startup. The `mkdocs gallery` command runs the same step. The ordering rule above is no longer needed.

## Prevention

- Order the work so the shared server finds the build it wants: debug builds before a backend run, production builds
  last.
- Read a startup timeout against the server's log before blaming the code: here the server had not finished building.

## Source files

| Role | Path |
|------|------|
| The server and its frontend rebuild (`--build-only`) | `dev.py` |
| The foreground build before the startup timeout (`build_server_prerequisites`, `STARTUP_TIMEOUT`) | `scripts/test_runner/_server.py` |
| Plan 45 (§10, U-3, the detour of 22:48) | `LibreFolio_developer_journal/Release_2/Phase_0/45_pluginModules/plan-phase00PluginModules.prompt.md` |
