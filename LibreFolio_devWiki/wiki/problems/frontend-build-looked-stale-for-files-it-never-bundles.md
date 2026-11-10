---
title: "The frontend build looked stale for files it never bundles: a `.DS_Store`, a test file, a `__pycache__/`"
category: problem
status: resolved
date: 2026-10-17
tags: [testing, test-runner, frontend-build, mtime, dev-tooling, macos, workstream-h, release-1.3]
related:
  - problems/mutation-restore-keeps-old-mtime-skips-frontend-rebuild
  - problems/static-site-served-hidden-build-files
---

# Problem: a file the bundle never reads forced a frontend rebuild

## Summary

`check_frontend_needs_build()` (`scripts/cli_base.py`) rebuilds the frontend, minutes of CPU on a machine shared by many
sessions, when an input is newer than `frontend/build/index.html`. It counted files the bundle never reads: the macOS
Finder's `.DS_Store`, the Vitest files, and, through the folders' modification times, Python's `__pycache__/`. Two lots
of workstream H fixed it (release 1.3, 16–17/10): H-24 filters what counts under `frontend/src`; the residual of H-24
(the Tool codegen inputs) needed a **record of the inputs' listing**, because a folder's time cannot tell a `.DS_Store`
from a removed file.

## Details

- **H-24** (reported by E, and by the colour team as AF-13: at 22:29 a `.DS_Store` touched by macOS forced a full
  build, about 7 minutes at load 160). `_counts_for_the_build()` skips a path with a hidden part (`.DS_Store`,
  `.gitignore`, the i18n catalogue's `.generated` stamp), a `.test.`/`.spec.` file, and the `__tests__/`/`__mocks__/`
  folders. Everything else still counts: a build believed fresh by mistake costs more than one rebuild too many.
- **The residual (H-24r).** `_tool_contract_sources()` also compared the times of the eight folders of
  `backend/app/schemas/`, `services/tools/` and `services/tool_plugins/`, to notice a removed `.py`. Measured on macOS
  (17/10): **creating** a `.DS_Store` moves the folder's time, rewriting it in place does not; creating a
  `__pycache__/` moves it; removing a `.py` moves it. A filter on times therefore cannot separate the noise from a
  removal: both are the same event.
- **The cure: a record, not a guess.** `cmd_fe_build` (`dev.py`) takes `tool_contract_fingerprint()`, a SHA-256 of
  the sorted relative paths of the inputs (no hidden part, no `__pycache__/`, with a versioned prefix), **right before
  `cmd_api_sync`** generates the codecs, and writes it to `frontend/build/.tool-contract-inputs` **only when the build
  succeeds**. The check then says stale when an input is newer than the build, or when the listing differs from the
  record (an input added, removed or renamed, even with an old date). A build that recorded nothing (made before the
  record existed, or by `npm run build` alone, which empties `frontend/build/`) falls back on the folders' times: one
  rebuild too many at worst, after which the record exists. The three build paths (`dev.py`, the runner, the Docker
  image) all go through `cmd_fe_build`.
- **Why before the API sync**: the codecs are generated from the listing of that moment; a file added while the build
  runs must still make the next check stale.

## Solution

Proved on the real tree (17/10, coordinator's slot 2), after a real build by the runner:

| Situation | New rule | Old rule |
|---|---|---|
| right after the build | fresh | fresh |
| `.DS_Store` created in `backend/app/schemas` | fresh | stale |
| that `.DS_Store` removed | fresh | stale |
| a `.py` added with a date older than the build | stale (only the listing sees it) | — |
| that `.py` removed again | fresh | stale |

The lane server started afterwards did not rebuild.

## Prevention

- A staleness check counts only what the build reads. When an **absence** matters (a removed input), record what the
  build read instead of inferring it from folder times.
- A bookkeeping file of `frontend/build/` starts with `.`, and no route serves it:
  [[problems/static-site-served-hidden-build-files]].
- The opposite failure, a build believed fresh because a source kept an old time, is
  [[problems/mutation-restore-keeps-old-mtime-skips-frontend-rebuild]].

## Impact

Minutes of CPU per false rebuild on a machine shared by many sessions, sometimes inside another session's test slot.

## Source files

| Role | Path |
|------|------|
| Staleness check, `_counts_for_the_build()`, `_tool_contract_sources()`, the fingerprint and its record | `scripts/cli_base.py` |
| `cmd_fe_build` takes the fingerprint before the API sync and records it on success | `dev.py` |
| Tests of the check and of the record | `backend/test_scripts/test_utilities/test_runtime_isolation.py` |
| Tests of `cmd_fe_build`'s order and of «recorded only on success» | `backend/test_scripts/test_utilities/test_test_server_preparation.py` |
| What the runner counts before a build | `mkdocs_src/docs/developer/test-walkthrough/front-overview.md` |
| The lots, the measurements and the real check (H-24, «Residuo di H-24 e H-28») | `LibreFolio_developer_journal/Release_2/Phase_1/01_platform/plan-phase01Platform.prompt.md` |
