---
title: "Phase 0 / 15 — parallel runtime isolation (`--test-port`, `--data-dir`)"
category: source
source_type: plan
date_ingested: 2026-10-09
original_path: LibreFolio_developer_journal/Release_2/phases/15_parallelRuntimeIsolation/plan-phase00ParallelRuntimeIsolation.prompt.md
tags: [phase0, release2, cli, testing, parallelism, worktrees, isolation]
related:
  - concepts/runtime-lanes
  - entities/devpy-cli
  - features/F-063
  - concepts/test-isolation-classes
---

# Source: Phase 0 / 15 — runtime lanes

## Summary

One plan (~165 lines), shipped in `916f12bdd` (2026-09-10) and archived on 2026-10-09. It made it possible to run
several development servers and test campaigns in parallel — one per worktree or agent — each with its own port and
data directory, guarded against touching production. Every later Release 2 workstream ran in such a lane.

## Key takeaways

- The lane = a unique port **and** a unique data directory; the switches, the guards and the readiness nonce:
  [[concepts/runtime-lanes]].
- Review fixes worth remembering: `pipenv run` reloaded `.env` over the parent's overrides; a `200` from another lane's
  server was accepted as ready; `--force` killed listeners the runner did not own; database paths were frozen at
  import.
- Known limit, written into the plan on 2026-09-22: `mkdocs gallery` takes `--test-port` but not `--data-dir`, and
  always repopulates the configured test directory.
- Worktree gotcha: one empty pipenv venv per worktree path unless `PIPENV_CUSTOM_VENV_NAME` is set.

## Residuals

None besides the accepted gallery limit.

## Wiki pages updated

- [[concepts/runtime-lanes]] — new.
- [[entities/devpy-cli]], [[features/F-063]] — lanes, line count, stale commands corrected.

## Source files

| Role | Path |
|------|------|
| Plan | `LibreFolio_developer_journal/Release_2/phases/15_parallelRuntimeIsolation/plan-phase00ParallelRuntimeIsolation.prompt.md` |
| Lane configuration | `scripts/cli_base.py` |
| Test runner options | `scripts/test_runner/_cli.py` |
| Data-dir guard | `backend/app/config.py` |
| Tests | `backend/test_scripts/test_utilities/test_runtime_isolation.py` |
