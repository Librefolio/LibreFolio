---
name: devpy-server
description: "Use this skill when the user needs to start/stop the development server, manage the database (create, migrate, populate), build the frontend, or sync the API client. Covers server, db, front, and api dev.py subcommands."
---

# Server, Database, Frontend Build & API Sync

## Server

```bash
./dev.py server                        # Production mode (port 6040)
./dev.py server --test                 # Test mode (port 6041, debug=true)
./dev.py server --debug                # Debug mode (port 6040, debug=true)
./dev.py server --force                # Kill zombie processes on the port first
./dev.py server --workers 4            # Multi-worker (default: 1)
./dev.py server --coverage             # Start under Python coverage tracking (boolean — no language argument)
./dev.py server --rebuild              # Force frontend rebuild before start
./dev.py server --test --build-only    # Only the builds the server does before binding, then exit (no port, no uvicorn)
./dev.py server --host 0.0.0.0        # Override host
./dev.py server --port 9000           # Override port
./dev.py server --data-dir /tmp/lf-b  # Override this server's data root
./dev.py server --test --port 6151 --data-dir /tmp/lf-test-b
```

### Independent worktree runtimes

Use a unique **pair** for every concurrent worktree:

```bash
./dev.py server --test --port 6151 --data-dir /tmp/librefolio-r2-b
./dev.py test --test-port 6151 --data-dir /tmp/librefolio-r2-b api all
```

The second command propagates the lane to pytest, the shared backend,
Playwright and setup children. Defaults remain `6041` +
`backend/data/test`. Never reuse a port or data directory in two active lanes;
the test runner fails closed on an occupied port. Use `server --force` only as
an explicit manual cleanup of a port you own.
Test data is kept in `LIBREFOLIO_TEST_DATA_DIR`, never
`LIBREFOLIO_DATA_DIR`, and production paths are rejected.

### What `server` does automatically
1. Auto-builds frontend if missing/outdated (a debug build under `--test`)
2. Auto-builds MkDocs if missing/outdated
3. Updates JS library cache
4. Checks if port is in use, right before binding (with `--force`: kills blockers)
5. Starts uvicorn with the app

`--build-only` stops after step 3 and exits: 0, or the frontend build's exit code. The test runner and
`mkdocs gallery` run `dev.py server --test --build-only` in the foreground before they start a test server,
with its output visible, so a rebuild after a merge never counts against the server's startup timeout
(300 s, `LIBREFOLIO_TEST_STARTUP_TIMEOUT`), which measures the start only.

### Coverage mode
When `--coverage` is used, `dev.py` replaces itself via `os.execvpe()` with `coverage run -m uvicorn`. This enables backend coverage tracking during E2E tests via the SIGTERM chain (see testing-frontend skill).

⚠️ **`server --coverage` stays boolean**, unlike `test --coverage [py|js|all]`. A
server process can only measure Python — there is no JS to instrument in it. Passing
a language here is an error, and the argv normaliser that makes `test --coverage api all`
work is deliberately scoped to the `test` sub-command so it cannot corrupt the
Playwright `webServer` command line.

## Database

```bash
./dev.py db create-clean               # Recreate prod DB from 001_initial.py
./dev.py db create-clean --test        # Recreate test DB
./dev.py db check                      # Verify the model CHECK constraints exist in the DB
./dev.py db current                    # Show current revision
./dev.py db migrate "Add new table"    # Create new migration
./dev.py db upgrade                    # Apply pending migrations
./dev.py db downgrade                  # Revert last migration
```

### Rules
- **Released — use incremental Alembic migrations**: schema changes ship as new migrations to protect existing installs
- Edit `backend/alembic/versions/001_initial.py` only for brand-new never-shipped tables
- `./dev.py db create-clean` only for fresh installs / test DBs, not to evolve an existing schema
- Every migration needs working `upgrade()` + `downgrade()`, tested on a populated DB
- **Name it `00N_<target release or scope>`** — `db migrate` emits a random hex id, so rename
  file *and* `revision` before committing: `004_release_1_2_0_schema` (target version) or
  `003_scheduler_timezone` (self-contained scope). Safe only while unreleased: once an id is
  inside a published tag it lives in users' `alembic_version` and must never change.
- **One migration per release**: before tagging, the cycle's unreleased migrations are folded into one
  `00N_release_<version>_schema` (004, 005), tested against the schema of the chain it replaces
- **Only the indexes a query uses**: a `UNIQUE` constraint already has its index; no index that is the
  left prefix of another; every new index needs a query proven with `EXPLAIN QUERY PLAN`. `db validate`
  refuses duplicates (`.github/instructions/backend-db.instructions.md`, «Indexes»)
- **Never `alembic merge`.** Two heads make startup skip migrations entirely and boot anyway
  (see `.github/instructions/backend-db.instructions.md`). Re-parent instead.
- Test DB and prod DB are completely isolated (`backend/data/test/` by default,
  or a lane-specific `--data-dir`, vs `backend/data/prod/`)

### Populate test data
```bash
./dev.py test db populate --force              # Basic mock data
./dev.py test db populate --force --clean      # Clean + populate
./dev.py test db populate --force --clean --with-static --with-reports  # Full (for gallery)
```

## Frontend Build

```bash
./dev.py front dev                     # Start Vite HMR dev server (port 5173)
./dev.py front build                   # Production build → frontend/build/
./dev.py front build --debug           # Debug build (sourcemaps, no minification)
./dev.py front check                   # Run svelte-check (type checking)
./dev.py front preview                 # Preview production build locally
```

`front build` and `api client` (so also `api sync`) first check `frontend/node_modules/.bin`
(`openapi-zod-client`, `svelte-check`, `vite`; the client only its generator). If one is missing they stop
with exit 1, naming it and `cd frontend && npm ci`, before any npm or npx call: npx would otherwise fetch
an unpinned version from the registry.

### Development workflow
Terminal 1: `./dev.py server` (backend on 6040, serves static build)
Terminal 2: `./dev.py front dev` (Vite HMR on 5173, proxies API to 6040)

## API Sync

After modifying backend API endpoints or Pydantic schemas, regenerate the TypeScript client:

```bash
./dev.py api sync       # Export OpenAPI schema + generate Zodios TypeScript client
./dev.py api schema     # Only export OpenAPI JSON
./dev.py api client     # Only regenerate TypeScript client from existing schema
```

### What `api sync` does
1. `api schema` runs `scripts/list_api_endpoints.py`, which imports the FastAPI app
   **in-process** and calls `app.openapi()`
2. Writes `frontend/src/lib/api/openapi.json` and
   `frontend/src/lib/api/tool-contracts.openapi.json`
3. `api client` runs `npm run generate-api`, feeding the **local** `openapi.json`
   to `openapi-zod-client` → `frontend/src/lib/api/generated.ts`
4. That same script chains `npm run generate-tools` →
   `frontend/src/lib/api/generated-tools.ts`

**No server is started and no port is bound.** `api sync` is therefore safe to run in
any worktree lane, concurrently with other lanes, without coordination.

### Regenerate before you trust a measurement

The five generated client files are git-ignored, so a merge never refreshes them: they
stay at whatever age the last build left them, and keep answering.

| Command | Regenerates the client? |
|---------|------------------------|
| `./dev.py api sync` | yes — both `generated.ts` and `generated-tools.ts`, no compile, no port |
| `./dev.py front build` | yes — it calls `api sync` first, then pays for a full compile |
| `./dev.py front check` | **no** — `svelte-check` only reads |

Running `front check` against a stale client reports type errors in the files that
*consume* the contract, never in the artifact that is wrong. Run `api sync` first, or
the number describes a contract that no longer exists.
