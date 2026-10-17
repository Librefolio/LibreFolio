---
title: "A direct Playwright run in a test lane: the setup that wipes the DB, and the script that changed under bash"
category: problem
status: workaround
date: 2026-10-17
tags: [e2e, playwright, test-lane, runner, bash, coordination]
related: [concepts/page-busy-refresh-button, problems/e2e-chained-waits-outlast-the-test-budget]
---

# Problem: A direct Playwright run in a test lane

## Symptom

`./dev.py test` has no `--grep`, so running **one** E2E test (several times, or with `--trace on`) means launching
Playwright directly. On the night of 16→17/10 that came within one step of two different mistakes:

1. **The DB wipe.** Without `LF_SETUP_DONE=1`, `frontend/e2e/global-setup.ts` takes its full path:
   `populate_mock_data --force --with-reports`, which recreates the test DB of the lane it is pointed at.
   - The runner sets `LF_SETUP_DONE=1` because it has already populated the DB.
   - A hand-run command does not set it, so it destroys the lane's data, possibly while a neighbour's assumptions rest
     on them.
2. **The script that changed under bash.** A trace script was edited and launched in the same batch of commands.
   - bash reads a script **incrementally, by offset**. The edit inserted a line above the cursor, and bash went on
     reading from the middle of a line: `line 14: -iTCP:6189: command not found`.
   - The new `export TEST_PORT=… LIBREFOLIO_TEST_DATA_DIR=…` was never executed.
   - Playwright's `webServer` would have started `dev.py server --test` on the **default** port 6041, with the default
     data dir: outside the lane, in a coordinated session.
   - Stopped during `--build-only`, before Playwright started. Nothing ran outside the lane.

## Root Cause

- `global-setup.ts` is built for two callers: the runner, which prepares everything, and a developer running
  Playwright by hand on a throwaway DB. A coordinated lane is neither.
- `playwright.config.ts` falls back to `TEST_PORT=6041` and `backend/data/test` when the variables are missing.
- bash does not load a script before running it.

## Solution

The direct-run script (`y22_trace.sh` in Y's session; the shape is what matters):

```bash
export PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc
export TEST_PORT=<lane port> LIBREFOLIO_TEST_DATA_DIR=<lane data dir>     # at the top, for every step
lsof -nP -iTCP:$TEST_PORT -sTCP:LISTEN && exit 2                          # a busy port is a collision
nice -n 10 pipenv run python dev.py server --test --build-only            # build outside the startup timeout
[ "$TEST_PORT" = <lane port> ] && [ "$LIBREFOLIO_TEST_DATA_DIR" = <lane data dir> ] || exit 3   # guard
cd frontend && LF_SETUP_DONE=1 nice -n 10 pipenv run npm run test:e2e -- <spec> --project desktop \
    -g "<title>" --trace on --repeat-each 4 --workers 2
```

- `pipenv run` around `npm` makes the `webServer`'s `./dev.py` resolve to the venv's Python.
- Never edit a script in the same batch that runs it. Write it, check it with `bash -n`, then launch it as a separate
  step; if it must change, use a temp file and `mv`, with no run in flight.
- Read the traces' `trace.trace` (JSON lines, `before`/`after`/`log` events): per-action durations and the
  actionability log of a click answer «where did the time go» without a viewer.

## Prevention

- In a coordinated lane, a direct Playwright run always carries the lane's port and data dir **and**
  `LF_SETUP_DONE=1`, behind a guard that refuses to start without them.
- A `--grep` in the runner (`scripts/test_runner/`) would remove the need for direct runs: not done, since the runner
  files are shared.

## Impact

None: both caught before any test or populate ran. About 15 minutes, and one incident written up in the coordinator's
report.

## Source files

| Role | Path |
|------|------|
| The destructive full path, and `LF_SETUP_DONE` | `frontend/e2e/global-setup.ts` |
| The port and data-dir fallbacks, the `webServer` command | `frontend/playwright.config.ts` |
| The runner that sets `LF_SETUP_DONE` for its own Playwright runs | `scripts/test_runner/_frontend_common.py` |
| The runner's per-category options: no `--grep` | `scripts/test_runner/_cli.py` |
| History (Y-22) | `LibreFolio_developer_journal/Release_2/Phase_1/09_dashboardCharts/plan-phase01DashboardCharts.prompt.md` |
