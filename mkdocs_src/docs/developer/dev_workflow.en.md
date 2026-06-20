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

For details on local Docker workflows, container settings, and how the host `.env` file integrates with `docker-compose.yml`, see the [Advanced Docker Guide](../admin/docker_advanced.md).
