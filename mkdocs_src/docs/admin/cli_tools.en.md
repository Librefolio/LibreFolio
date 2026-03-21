# 🛠️ Command-Line Tools

LibreFolio provides the `dev.py` script for administration tasks. This page covers the commands most relevant to **system administrators**.

!!! info "👩‍💻 For Developers"
    For development-specific commands (frontend build, test runner, API sync, i18n audit), see the [Developer Installation Guide](../developer/dev-installation.md).

---

## 🚀 Installation

Install all project dependencies (Python and Node.js):

```bash
./dev.py install
```

---

## 🖥️ Server (Production)

### ▶️ Starting the Server

```bash
# Standard start
./dev.py server

# With auto-calculated workers (2 × (CPU-1))
./dev.py server --workers N

# Kill existing process on port before starting
./dev.py server --force
```

!!! tip "Multi-worker"
    For production, use `--workers` to run multiple Uvicorn workers. This improves throughput and is recommended for any deployment with more than 1 CPU core.

---

## 👤 User Management

User management is done via `./dev.py user` subcommands:

```bash
# Create a user (first user becomes admin automatically)
./dev.py user create <username> <email> <password>

# List all users
./dev.py user list

# Reset a user's password
./dev.py user reset <username> <new_password>

# Promote a user to admin
./dev.py user promote <username>

# Demote an admin to regular user
./dev.py user demote <username>
```

---

## ⚙️ System Management

### 🔧 Initialize Global Settings

```bash
./dev.py user init-settings
```

Populates the database with default [Global Settings](settings.md) if they don't already exist.

### 🗄️ Database Migrations

```bash
# Apply pending migrations
./dev.py db upgrade
```

!!! warning "🗄️ Database reset"
    `./dev.py db create-clean` recreates the database from scratch — **all data is lost**. Use only if you need a fresh start.

---

## 📚 Documentation

```bash
# Build and deploy MkDocs documentation to GitHub Pages
./dev.py mkdocs deploy

# Generate gallery screenshots (requires running server + test data)
./dev.py mkdocs gallery
```

---

## 📋 Full Command Tree

For a complete list of all available commands:

```bash
./dev.py --help
```

!!! info "👩‍💻 Developer Commands"
    Additional commands for development workflows:

    - **Frontend**: `./dev.py front build`, `front dev`, `front check` — see [Frontend Development](../developer/frontend/index.md)
    - **Testing**: `./dev.py test all` — see [Test Walkthrough](../developer/test-walkthrough/index.md)
    - **API Client**: `./dev.py api sync` — see [API Overview](../developer/api/overview.md)
    - **i18n**: `./dev.py i18n audit` — see [Internationalization](../developer/frontend/i18n.md)
