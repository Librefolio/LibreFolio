# 🛠️ Command-Line Tools

LibreFolio provides the `dev.py` script for administration tasks. This page covers the commands most relevant to **system administrators**.

!!! tip "Python Virtual Environment Context"

    If you are running LibreFolio directly on the **host machine**, all command-line operations must be executed within the Python virtual environment. You can either prefix each command with `pipenv run` (e.g., `pipenv run ./dev.py server`) or enter the virtual environment once by running `pipenv shell`.

    If you are inside a **Docker container terminal** (for example, accessed via `docker exec`), you **do not** need to use `pipenv run` or `pipenv shell`, as the dependencies are pre-installed globally inside the container image. You can run `./dev.py` commands directly.

!!! info "👩‍💻 For Developers"

    For development-specific commands (frontend build, test runner, API sync, i18n audit), see the [Developer Workflow Guide](../developer/dev_workflow.md).

---
## 🖥️ Server (Production)

### ▶️ Starting the Server

```bash
# Standard start
pipenv run ./dev.py server

# With auto-calculated workers (2 × (CPU-1))
pipenv run ./dev.py server --workers N

# Kill existing process on port before starting
pipenv run ./dev.py server --force
```

!!! tip "Multi-worker"

    For production, use `--workers` to run multiple Uvicorn workers. This improves throughput and is recommended for any deployment with more than 1 CPU core.

---

## 👤 User Management

User management is done via `./dev.py user` subcommands:

```bash
# Create a user (first user becomes admin automatically)
pipenv run ./dev.py user create <username> <email> <password>

# List all users
pipenv run ./dev.py user list

# Reset a user's password
pipenv run ./dev.py user reset <username> <new_password>

# Promote a user to admin
pipenv run ./dev.py user promote <username>

# Demote an admin to regular user
pipenv run ./dev.py user demote <username>
```

---

## ⚙️ System Management

### 🔧 Initialize Global Settings

```bash
pipenv run ./dev.py user init-settings
```

Populates the database with default [Global Settings](settings.md) if they don't already exist.

### 🗄️ Database Migrations

```bash
# Apply pending migrations
pipenv run ./dev.py db upgrade
```

!!! warning "🗄️ Database reset"

    `pipenv run ./dev.py db create-clean` recreates the database from scratch — **all data is lost**. Use only if you need a fresh start.

---

## 📚 Documentation

```bash
# Build and deploy MkDocs documentation to GitHub Pages
pipenv run ./dev.py mkdocs deploy

# Generate gallery screenshots (requires running server + test data)
pipenv run ./dev.py mkdocs gallery
```

---

## 📋 Full Command Tree

For a complete list of all available commands:

```bash
pipenv run ./dev.py --help
```

!!! info "👩‍💻 Developer Commands"

    Additional commands for development workflows:

    - **Frontend**: `pipenv run ./dev.py front build`, `front dev`, `front check` — see [Frontend Development](../developer/frontend/index.md)
    - **Testing**: `pipenv run ./dev.py test all` — see [Test Walkthrough](../developer/test-walkthrough/index.md)
    - **API Client**: `pipenv run ./dev.py api sync` — see [API Overview](../developer/api/overview.md)
    - **i18n**: `pipenv run ./dev.py i18n audit` — see [Internationalization](../developer/frontend/i18n.md)

