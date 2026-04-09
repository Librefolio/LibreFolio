# 🛠️ Installation (Development)

This guide covers setting up a local development environment. For production deployment, see the [User Manual Installation](../user/installation.md).

## ✅ Prerequisites

- 🐍 **Python 3.13+**
- 📦 **Node.js 20.19+** (includes npm)
- 📋 **Pipenv** (`pip install pipenv`)
- 🐳 **Docker** (Optional, for production deployment)

## 📋 Setup Instructions

The project includes a main orchestration script, `dev.py`, to automate all tasks.

### 📦 1. Install Dependencies

This command installs all Python and Node.js dependencies for both the backend and frontend.

```bash
./dev.py install
```

This will:

1. Install backend packages via `pipenv`.
2. Install frontend packages via `npm`.
3. Install Playwright browsers for E2E testing.

### 🗃️ 2. Initialize the Database

Before starting the server for the first time, create the database:

```bash
./dev.py db create-clean
```

This command creates a fresh SQLite database with the initial schema.

### ⚙️ 3. Configure Environment

Copy the example environment file:

```bash
cp .env.example .env
```

The default settings work out of the box. Edit `.env` if you need to change port or data directory.

### 🚀 4. Start the Server

To start the FastAPI server with auto-reload:

```bash
./dev.py server
```

The server will be available at `http://localhost:8000`.

#### Server Options

| Flag | Description |
|------|-------------|
| `--host HOST` | Bind address (default: `HOST` env var or `0.0.0.0`) |
| `--port PORT` | Bind port (default: `PORT` env var or `8000`) |
| `--test` / `-t` | Use test database (port 8001) |
| `--debug` / `-d` | Debug mode: verbose logging + frontend debug build |
| `--rebuild` / `-r` | Force rebuild frontend before starting |
| `--force` / `-f` | Kill blocking processes on the port before starting |
| `--workers N` | Number of uvicorn workers (default: 1, disables reload) |

For frontend development with Hot Module Replacement, start a second terminal:

```bash
./dev.py front dev
```

The dev server runs at `http://localhost:5173` and proxies API calls to the backend.

### 👤 5. Create a User

The first time you access LibreFolio in the browser, you'll see a **registration page** — you can create your first account directly from the frontend. The first user registered automatically becomes the administrator.

Alternatively, you can create users from the CLI:

```bash
./dev.py user create <username> <email> <password>
```

!!! note "Admin promotion requires CLI"

    While any user can register from the frontend, **promoting a user to administrator** (superuser) can only be done from the command line:

    ```bash
    ./dev.py user promote <username>
    ```

---

## 🔄 Development Workflow

Once installed, `dev.py` is your single entry point for every development task.
Run `./dev.py --help` for the full command tree.

### 🖥️ Frontend

| Command | Description | Details |
|---------|-------------|---------|
| `./dev.py front dev` | Start Vite dev server with HMR | [Frontend Development](frontend/index.md) |
| `./dev.py front build` | Production build (or `--debug` for source maps) | [Frontend Development](frontend/index.md) |
| `./dev.py front check` | Run `svelte-check` type checker | [Frontend Development](frontend/index.md) |
| `./dev.py front preview` | Preview production build locally | |

### 🔗 API Client

| Command | Description | Details |
|---------|-------------|---------|
| `./dev.py api schema` | Export OpenAPI JSON from backend | [API Overview](api/overview.md) |
| `./dev.py api client` | Generate TypeScript client from schema | [API Overview](api/overview.md) |
| `./dev.py api sync` | Schema export + client generation in one step | [API Overview](api/overview.md) |

### 🌍 Internationalization

| Command | Description | Details |
|---------|-------------|---------|
| `./dev.py i18n audit` | Audit missing/extra keys across all languages | [i18n](frontend/i18n.md) |
| `./dev.py i18n audit --duplicates` | Also report duplicate values | [i18n](frontend/i18n.md) |
| `./dev.py i18n add KEY --en … --it …` | Add a new key to all language files | [i18n](frontend/i18n.md) |
| `./dev.py i18n remove KEY` | Remove a key from all files | [i18n](frontend/i18n.md) |
| `./dev.py i18n search QUERY` | Search keys/values | [i18n](frontend/i18n.md) |
| `./dev.py i18n tree [PREFIX]` | Show key tree structure | [i18n](frontend/i18n.md) |

### 🗃️ Database

| Command | Description | Details |
|---------|-------------|---------|
| `./dev.py db create-clean` | Delete DB and recreate with latest migration | [Alembic](architecture/patterns/alembic.md) |
| `./dev.py db upgrade` | Apply pending Alembic migrations | [Alembic](architecture/patterns/alembic.md) |
| `./dev.py db migrate MESSAGE` | Create new auto-generated migration | [Alembic](architecture/patterns/alembic.md) |
| `./dev.py db downgrade` | Rollback one migration step | [Alembic](architecture/patterns/alembic.md) |
| `./dev.py db check` | Verify CHECK constraints | |
| `./dev.py db current` | Show current migration revision | |

### 🧪 Testing

| Command | Description | Details |
|---------|-------------|---------|
| `./dev.py test all` | Run all test categories in optimal order | [Test Walkthrough](test-walkthrough/index.md) |
| `./dev.py test <category> all` | Run a single category (e.g., `api`, `e2e`, `front-fx`) | [Test Walkthrough](test-walkthrough/index.md) |
| `./dev.py test <category> --list` | List available tests without running them | [Test Walkthrough](test-walkthrough/index.md) |

### 🧰 Other Tools

| Command | Description |
|---------|-------------|
| `./dev.py format` | Format Python code with `black` |
| `./dev.py lint` | Lint Python code with `ruff` |
| `./dev.py mkdocs serve` | Start MkDocs dev server |
| `./dev.py mkdocs build` | Build MkDocs static site |
| `./dev.py info api` | Show API info (routes, models) |
| `./dev.py info version` | Show application version (from git tags) |
| `./dev.py cache js` | Update JS library cache |
| `./dev.py shell` | Open `pipenv` shell |

### 🐳 Docker

| Command | Description |
|---------|-------------|
| `./dev.py docker build` | Build Docker image (auto-builds frontend + docs if needed) |
| `./dev.py docker rebuild` | Build → stop containers → restart with new image |
| `./dev.py docker up` | Start containers (`docker compose up -d`) |
| `./dev.py docker down` | Stop containers |
| `./dev.py docker logs` | Show container logs (`-f` to follow) |
| `./dev.py docker status` | Show container status |

