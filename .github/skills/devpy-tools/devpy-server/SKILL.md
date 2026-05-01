---
name: devpy-server
description: "Use this skill when the user needs to start/stop the development server, manage the database (create, migrate, populate), build the frontend, or sync the API client. Covers server, db, front, and api dev.py subcommands."
---

# Server, Database, Frontend Build & API Sync

## Server

```bash
./dev.py server                        # Production mode (port 8000)
./dev.py server --test                 # Test mode (port 8001, debug=true)
./dev.py server --debug                # Debug mode (port 8000, debug=true)
./dev.py server --force                # Kill zombie processes on the port first
./dev.py server --workers 4            # Multi-worker (default: 1)
./dev.py server --coverage             # Start under coverage tracking (for E2E tests)
./dev.py server --rebuild              # Force frontend rebuild before start
./dev.py server --host 0.0.0.0        # Override host
./dev.py server --port 9000           # Override port
```

### What `server` does automatically
1. Checks if port is in use (with `--force`: kills blockers)
2. Auto-builds frontend if missing/outdated
3. Auto-builds MkDocs if missing/outdated
4. Updates JS library cache
5. Starts uvicorn with the app

### Coverage mode
When `--coverage` is used, `dev.py` replaces itself via `os.execvpe()` with `coverage run -m uvicorn`. This enables backend coverage tracking during E2E tests via the SIGTERM chain (see testing-frontend skill).

## Database

```bash
./dev.py db create-clean               # Recreate prod DB from 001_initial.py
./dev.py db create-clean --test        # Recreate test DB
./dev.py db check                      # Check Alembic migration status
./dev.py db current                    # Show current revision
./dev.py db migrate "Add new table"    # Create new migration
./dev.py db upgrade                    # Apply pending migrations
./dev.py db downgrade                  # Revert last migration
```

### Rules
- **No incremental Alembic migrations** during early development
- Modify `backend/alembic/versions/001_initial.py` directly
- Then `./dev.py db create-clean` to recreate from scratch
- Test DB and prod DB are completely isolated (`backend/data/test/` vs `backend/data/prod/`)

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

### Development workflow
Terminal 1: `./dev.py server` (backend on 8000, serves static build)
Terminal 2: `./dev.py front dev` (Vite HMR on 5173, proxies API to 8000)

## API Sync

After modifying backend API endpoints or Pydantic schemas, regenerate the TypeScript client:

```bash
./dev.py api sync       # Export OpenAPI schema + generate Zodios TypeScript client
./dev.py api schema     # Only export OpenAPI JSON
./dev.py api client     # Only regenerate TypeScript client from existing schema
```

### What `api sync` does
1. Starts a temporary server instance
2. Fetches `/openapi.json`
3. Writes `frontend/src/lib/api/openapi.json`
4. Runs the Zodios code generator → `frontend/src/lib/api/generated.ts`
5. Stops the temporary server

