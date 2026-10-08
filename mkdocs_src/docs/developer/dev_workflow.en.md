# 🔄 Developer Workflow & Tools

This guide covers developer-specific workflows, tools, and all CLI commands available in LibreFolio.

!!! note "Prerequisite: Host Installation"

    Before using these developer tools, ensure you have set up your local Python, Node.js, and Pipenv environment. For step-by-step setup instructions, see the [Host Installation Guide](../admin/host_installation.md).

---

## 🖥️ SvelteKit Frontend Development

For active frontend development with Hot Module Replacement (HMR), start a second terminal and run:

```bash
./dev.py front dev
```

The Vite development server will run at **`http://localhost:5173`** and automatically proxy all `/api` calls to the FastAPI backend.

!!! note "Frontend Dependency"

    The SvelteKit frontend is heavily dependent on the data returned by the backend. You must keep the backend server running in parallel (via `./dev.py server` in another terminal) to handle API requests.

---

## 🔄 Development Workflow CLI Commands

LibreFolio includes a central orchestration script, `dev.py`, which is your single entry point for all development tasks.
Run `./dev.py --help` for the full command tree.

### 🖥️ Frontend Management

| Command | Description | Details |
|---------|-------------|---------|
| `./dev.py front dev` | Start Vite dev server with HMR | Run at `http://localhost:5173` |
| `./dev.py front build` | Compile frontend into production-ready static assets | static files output to `backend/static` |
| `./dev.py front build --debug` | Compile frontend with source maps | Used for debugging frontend issues |
| `./dev.py front check` | Run `svelte-check` type validator | Checks Svelte components and TS types |
| `./dev.py front preview` | Preview the compiled production build locally | Run Vite preview server |

### 🔗 API Client Synchronization

LibreFolio uses an OpenAPI-first workflow to keep types synchronized between Python (backend) and SvelteKit (frontend):

| Command | Description | Details |
|---------|-------------|---------|
| `./dev.py api schema` | Export OpenAPI JSON schema from FastAPI backend | Generates `openapi.json` |
| `./dev.py api client` | Generate TypeScript client from the exported schema | Generates frontend API client |
| `./dev.py api sync` | Export schema and generate client in one step | Highly recommended after changing models/routes |

### 🌍 Internationalization (i18n)

Manage translations across English, Italian, Spanish, and French:

| Command | Description |
|---------|-------------|
| `./dev.py i18n audit` | Audit missing or extra translation keys across languages |
| `./dev.py i18n audit --duplicates` | Audit and report duplicate translation values |
| `./dev.py i18n add KEY --en "…" --it "…" --es "…" --fr "…"` | Add a new key and its translations to all files |
| `./dev.py i18n remove KEY` | Remove a key from all language files |
| `./dev.py i18n search QUERY` | Search key names or translation values |
| `./dev.py i18n tree [PREFIX]` | Print key tree structure starting with optional prefix |

### 🗃️ Database Migrations (Alembic)

Create and apply database schema changes:

| Command | Description |
|---------|-------------|
| `./dev.py db upgrade` | Apply all pending migrations to the SQLite database |
| `./dev.py db migrate "MESSAGE"` | Auto-generate a new Alembic migration based on SQLAlchemy models |
| `./dev.py db downgrade` | Rollback the database schema by one migration step |
| `./dev.py db create-clean` | Recreate a fresh database and apply all migrations |
| `./dev.py db current` | Show the current database migration revision |

`db migrate`, `db upgrade`, `db downgrade` and `db create-clean` refuse to run while a server listens on the port that serves the target database (`PORT` for the production database, `TEST_PORT` for the test one): stop that server first. The server itself applies pending migrations at startup (`ensure_database_exists()` in `backend/app/main.py`).

### 🧪 Test Runner

Run backend unit/integration tests and frontend Playwright E2E tests:

| Command | Description |
|---------|-------------|
| `./dev.py test all` | Run all test categories in the optimal order |
| `./dev.py test <category> all` | Run tests in a single category (e.g., `api`, `e2e`, `front-fx`) |
| `./dev.py test <category> --list` | List available tests in a category without running them |

### 🧰 Linting, Formatting & Documentation

| Command | Description |
|---------|-------------|
| `./dev.py format` | Format backend Python code with `black` |
| `./dev.py lint` | Lint and auto-fix backend Python issues using `ruff` |
| `./dev.py mkdocs serve` | Start the local MkDocs documentation development server |
| `./dev.py mkdocs build` | Compile the documentation site into static HTML |
| `./dev.py shell` | Open a subshell inside the active `pipenv` virtual environment |

---

## 🐳 Docker Integration

Developers can build and run production-tagged containers locally using the dev CLI:

| Command | Description |
|---------|-------------|
| `./dev.py docker build` | Build production Docker image (compiles frontend + docs first) |
| `./dev.py docker up` | Launch the containerized stack in detached mode |
| `./dev.py docker down` | Stop and remove active Docker containers |
| `./dev.py docker rebuild` | Build, stop, and restart containers with the new image |
| `./dev.py docker exec <cmd>` | Execute a `dev.py` command inside the running container |

For details on local Docker workflows, container settings, and how the host `.env` file integrates with `docker-compose.yml`, see the [Advanced Docker Guide](../admin/docker_advanced.md). How the image itself is built and started: [Architecture overview → Docker image](architecture/overview.md#docker-image).

### 🏗️ What `./dev.py docker build` Does {: #docker-build-steps }

`cmd_docker_build()` checks that `.env` exists, then `_docker_ensure_assets_built()` prepares what the image copies from the host:

1. **Resource cache**: `scripts/update_js_cache.py`, strict. It caches the flags subset of the Noto Color Emoji font (`frontend/static/fonts/noto-color-emoji/`, drawn by the `'LF Flags'` face of `frontend/static/lf-flags.css` on every non-Apple device: Windows has no flag emoji of its own) and MathJax (`mkdocs_src/docs/javascripts/vendor/`); a resource that cannot be downloaded and has no cached copy fails the build (`❌ Resource cache incomplete`). `./dev.py front build` fails only for the resources the frontend ships (`--required-for frontend`), and `./dev.py server` only warns and falls back to the CDN. `./dev.py cache js` (`--force`) refreshes the cache by hand.
2. **Frontend**: rebuilt for production when `check_frontend_needs_build()` finds sources newer than `frontend/build/index.html`. The check reads timestamps, not the build mode: a debug build left by `./dev.py server --test` passes it, and the `Dockerfile`'s `frontend` stage then refuses it.
3. **Documentation**: `mkdocs build` when `mkdocs_src/site/index.html` is missing or older than any `.md` under `mkdocs_src/docs/`.
4. **`requirements.txt`**: regenerated with `pipenv requirements` when missing or older than `Pipfile.lock`.
5. **`VERSION`**: `get_git_version()` frozen into a file, since the image has no `.git/`.

The build then runs `docker build -t librefolio:<version> -t librefolio:latest --build-arg UID=<uid> --build-arg GID=<gid> .`, where `<version>` comes from `get_git_version()` and the UID/GID are those of the user running the command (`os.getuid()`, `os.getgid()`; only `docker compose build` reads `UID`/`GID` from `.env`). `--light` adds `-light` to both tags and `--build-arg DOCS_VARIANT=light`; `--no-cache` is passed through. `./dev.py docker rebuild` runs the same build, then `docker compose down` and `docker compose up -d`; a failed build leaves the running containers alone.

### 🧪 Test Mode in the Container {: #docker-test-mode }

The repository's `docker-compose.yml` maps a second port, `${TEST_PORT:-6041}:6041`, for a test server running next to the production one. The intended flow:

```bash
docker compose up -d                                          # production server on :6040
./dev.py docker exec test db populate --force --with-static   # mock data in the test database
./dev.py docker exec server --test                            # test server on :6041
```

Then open `http://localhost:6041` and sign in as a test user, for example `e2e_test_user` / `E2eTestPass123!` or `e2e_test_admin` / `E2eAdminPass123!`.

!!! warning "Does not start with the current image"

    Each of these blocks it on its own:

    - **`dev.py` cannot start in the container.** `main()` imports `scripts.test_runner` to build its parser, `scripts/test_runner/_common.py` imports `backend.test_scripts`, and `.dockerignore` keeps `backend/test_scripts/` out of the image: `ModuleNotFoundError`. Every `./dev.py docker exec …` fails the same way, as the [Advanced Docker Guide](../admin/docker_advanced.md) tells admins.
    - **`test db populate`** runs `backend.test_scripts.test_db.populate_mock_data`, missing for the same reason.
    - **`server --test`** forces a debug frontend build, while the image ships a production one: `auto_build_frontend()` sees the mode mismatch and rebuilds, which runs `npm` (API client generation, then the build itself), and the image has no Node.js.

The test database is `/app/backend/data/test/sqlite/app.db` (from `LIBREFOLIO_TEST_DATA_DIR=./backend/data/test`), in the container's writable layer: it survives `docker compose stop` and `docker compose start` (the container is stopped, not removed) and is lost with `docker compose down`. To keep it, add a bind mount:

```yaml
volumes:
  - ./LibreFolio-data:/app/backend/data/prod-docker
  - ./LibreFolio-test-data:/app/backend/data/test    # ← add this
```
