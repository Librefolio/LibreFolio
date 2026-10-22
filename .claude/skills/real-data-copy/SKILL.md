---
name: real-data-copy
description: "Use this skill when a check, a review server, a read-only SQL count or an AI Export probe needs the developer's real (demo) data instead of the test mocks: creating the coordinator's reference copy from production, taking a per-workstream working copy from it, starting a server on it, passing credentials, and deleting it afterwards."
---

# Real-data copies

The test suites run on mocks that the runner recreates at every run. Some questions need
the developer's own data: a review the developer looks at, a count of legacy rows before a
validation rule changes, an AI Export probe, a chart on a long real history. This skill is
the procedure for that, used through Release 2 (1.2 and 1.3).

**The developer authorises it, every time.** His production data in this checkout are a
demo portfolio, but they are still his: no agent starts production, writes to it, or makes
a copy without his OK.

## Two levels

| Level | Path | Who | What it is for |
|---|---|---|---|
| **Reference copy** | `/tmp/librefolio-r2-realdata` | the coordinator | made from production with the server stopped; never served after its refresh, never tested, only copied |
| **Working copy** | `/tmp/librefolio-r2-<code>-realdata` | one workstream | copied from the reference; here you start servers, run queries, experiment |

Why two levels: production is touched once, read-only, while it is stopped. Every
workstream works on its own copy, so one agent's experiment never reaches another's review.

## Never `dev.py test` on a real-data copy

The runner **destroys** the data directory it runs on, by design: before a category it
repopulates it with the mocks its assertions need.

- `scripts/test_runner/_backend_api.py` → `db_populate(force=True)`;
- `scripts/test_runner/_frontend_common.py` → `db_populate(force=True, with_reports=True)`;
- `scripts/test_runner/_backend_services.py` → `db_create()`, which deletes `app.db`,
  `custom-uploads` and `broker_reports`.

So the suites keep their own lane (`--test-port` + `--data-dir`), and the real-data copy
gets a **different port and directory**. Convention: the working port is the lane's suite
port + 10, unless the coordinator assigns another.

## 1. The reference copy (coordinator only)

Production lives in `backend/data/prod/` of the main checkout. Its root holds the marker
`.librefolio-production-data`; `backend/app/config/__init__.py` refuses any test data
directory that contains it («Test data directory is inside a marked production data
directory»). That guard is wanted: **never copy the marker, and never get around the
error by starting without `--test`**.

```bash
PROD=/Users/ea_enel/Documents/00_My/LibreFolio/backend/data/prod
GOLD=/tmp/librefolio-r2-realdata
! lsof -nP -iTCP:6040 -sTCP:LISTEN >/dev/null      # production must be stopped
[ ! -s "$PROD/sqlite/app.db-wal" ]                 # no pending WAL frames (an empty WAL is fine)
[ -e "$GOLD" ] && mv "$GOLD" "$GOLD.prev-$(date +%Y%m%d-%H%M%S)"
umask 077 && mkdir -p "$GOLD/sqlite"
sqlite3 "file:$PROD/sqlite/app.db?mode=ro&immutable=1" ".backup '$GOLD/sqlite/app.db'"
cp -R "$PROD/custom-uploads" "$PROD/broker_reports" "$PROD/scheduler_state.json" "$GOLD"/
test ! -e "$GOLD/.librefolio-production-data"
chmod -R go-rwx "$GOLD"
sqlite3 "$GOLD/sqlite/app.db" "PRAGMA integrity_check; SELECT version_num FROM alembic_version;"
```

- `.backup` from a read-only, immutable URI never writes to production, not even its
  `-shm`.
- Only `app.db` is copied, never `-wal`/`-shm` or lock files.
- A previous reference copy is moved to `.prev-<date>`, never deleted in the same step;
  delete the `.prev` once the new copy is verified.

**Refreshing the prices.** If production has been off for days, the coordinator may start
**one** server on the reference copy, with the scheduler, from the target branch, on a
free port that is not 6040, wait for the catch-up, then stop it:

```bash
pipenv run python dev.py server --test --port <PORT> --host 127.0.0.1 \
  --data-dir /tmp/librefolio-r2-realdata --no-reload
```

That start also migrates the copy to the target branch's schema. Record the resulting
Alembic revision: workstreams on an older base cannot open it (see «Schema» below).

`/tmp` is wiped at every reboot. Keep the creation script in the coordinator's session
folder and recreate the reference copy from production when it is gone.

## 2. A working copy (workstream)

```bash
GOLD=/tmp/librefolio-r2-realdata
COPY=/tmp/librefolio-r2-<code>-realdata
if [ -e "$COPY" ]; then
  lsof +D "$COPY" >/dev/null && { echo "copy in use: stop"; exit 1; }
  rm -rf "$COPY"
fi
umask 077 && mkdir -p "$COPY"
cp -R "$GOLD/." "$COPY"/
test ! -e "$COPY/.librefolio-production-data"
chmod -R go-rwx "$COPY"
```

Copy only while no server runs on the reference copy (the coordinator says when it is
refreshing).

**Start a server** on it from your worktree:

```bash
PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py server --test \
  --port <WORK_PORT> --host 127.0.0.1 --data-dir "$COPY" --no-reload --no-scheduler
```

- `--no-scheduler` unless refreshing prices is the point: several servers syncing the same
  providers at once earn rate limits (HTTP 429) that look like product failures.
- Work on the copy freely. Before handing the server to the developer for a review,
  **take a fresh copy**: he must find his data, not your experiments, unless the experiment
  is what he has to see, and then you tell him.
- At every `FROZEN`, stop the server and prove the port is free.

**Read-only queries** need no server:

```bash
sqlite3 "file:$COPY/sqlite/app.db?mode=ro" < query.sql
```

Report counts and aggregates. Never copy rows, names, amounts or identifiers of the
developer's data into the journal, the backlog, a commit, a test or a fixture.

### Schema

The server migrates the copy to your branch's Alembic head when it starts.

- Your branch is **ahead** of the copy (a new migration): normal, it migrates.
- Your branch is **behind** the copy: the server stops with
  `Can't locate revision '…'`. Do not repair the chain and do not edit `alembic_version`;
  update your base (ask the coordinator) or ask for a copy at your revision.

## 3. Credentials

The developer gives the credentials of his demo users to the coordinator. The coordinator
passes them in a `0600` file outside the repository, next to the reference copy.

- **Never** in the repository, this skill, the journal, the backlog, a log, a report, a
  commit message, a screenshot, or a command line saved to a file.
- Read them into an environment variable for the one command that needs them.
- The suites never need them: they use the `e2e_*` users the runner creates.

**AI Export probe** (`backend/test_scripts/diagnostics/ai_export_real_prompt_probe.py`): it
makes its own snapshot of `--source-db`, opened read-only, and works on that. Point it at
your working copy, not at production. It reads the password from
`LIBREFOLIO_AI_EXPORT_PROBE_PASSWORD_<USER>` (or `LIBREFOLIO_AI_EXPORT_PROBE_PASSWORD`).
Read the skill `ai-export-probe-tuning` and run `--help` before choosing flags.

```bash
LIBREFOLIO_AI_EXPORT_PROBE_PASSWORD_ALFY="$(cat <secret-file>)" \
PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python \
  backend/test_scripts/diagnostics/ai_export_real_prompt_probe.py \
  --source-db "$COPY/sqlite/app.db" --user alfy --port <WORK_PORT> …
```

## 4. Hygiene

- Every copy is `go-rwx` from creation.
- **Delete your working copy at the end of the review** that needed it: `lsof +D` first
  (nothing may hold it), `rm -rf`, then `ls` as proof, and a line in your journal.
- No `.prev` of working copies.
- Files derived from the copy (server logs, probe outputs, query results with values) are
  private data too: keep them in your session folder and delete them with the copy.
- A screenshot of real data leaves the machine only with the developer's OK.
