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

# Auto-size workers to the CPU count — 2 × (cores - 1)
# Both `auto` and `0` trigger the calculation
pipenv run ./dev.py server --workers auto

# Or pass an explicit worker count
pipenv run ./dev.py server --workers 4

# Kill existing process on port before starting
pipenv run ./dev.py server --force
```

!!! tip "Multi-worker"

    For production, use `--workers` to run multiple Uvicorn workers. This improves throughput and is recommended for any deployment with more than 1 CPU core.

---

## 👤 User Management

User management is done via `./dev.py user` subcommands:

```bash
# Create a user (users created from the CLI are always superusers)
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

### 🩹 Post-Migration Fixes {: #post-migration-fixes }

`db upgrade` applies the migrations only. Every time the server starts, right after applying any pending migration, it also runs the **post-migration fixes**: repairs that a migration cannot make.

1. **Integrity check** — a database that fails SQLite's integrity check is never touched; the log warns about it.
2. **Detection** — each fix looks for the anomaly it corrects. If there is none, nothing is written and nothing is logged.
3. **Backup** — a copy of the database is saved next to it, named after the fix and the UTC time: with the default data directory, for example `backend/data/prod/sqlite/app.db.pre-autoincrement-20261008T101500Z.bak`. If the copy cannot be made, no fix runs.
4. **Fix and verify** — each fix runs in a single transaction and is verified before it is committed: no broken references between tables, the same number of rows in every table, plus the fix's own checks.
5. **Outcome** — all verified: the copy is deleted and the log says `Post-migration fixes applied and verified`. Anything failed: the fix is rolled back, leaving the database exactly as it was, the copy is **kept**, and the `Post-migration fix failed` warning in the log gives its path and the error. Both lines also say how long the run took, in `seconds`: on a large database, the start that applies a fix takes longer, but only once.

Either way the server starts normally. A fix that did not complete is tried again at the next start, and a kept copy stays until you delete it. The log is the server's console output, also saved in the `logs/` folder of the data directory.

With `--workers`, each worker runs the fixes as it starts, and they take turns: every run holds an exclusive lock on `app.db.post-migration.lock`, an empty file next to the database that you should leave in place, so the others wait and, once the first has applied the fixes, find nothing left to do. The offline script below takes the same lock, even with `--dry-run`: started while the server is starting, it waits for its turn.

The first fix, **`autoincrement`**, stops LibreFolio from reusing ids. Without it, deleting the newest broker would let the next broker created take its id, together with whatever still pointed at that id: a saved link, a benchmark remembered by the browser, the folder of the broker's uploaded reports. With it, the id of a deleted user, broker, asset, transaction, FX conversion route or asset event is never given out again, and every existing id stays the same. New databases are created with this protection; an existing one is converted once, at the first start after the upgrade, and from then on the fix finds nothing to do. During the conversion, the uploaded-report folders whose broker no longer exists (`broker_reports/<uploaded|parsed|failed>/broker_<n>`) are first renamed in place to `.quarantine-autoincrement-<UTC time>-broker_<n>`, which the app does not list, so that a new broker cannot inherit them; they are deleted once the conversion is verified, or get their name back if it fails.

To preview the fixes, or to retry one that failed at startup and read its error, run them by hand from the project root with the server **stopped** — the script does not check it for you. Always preview with `--dry-run` first:

```bash
# Preview: report what would be fixed, change nothing
pipenv run python -m backend.app.db.post_migration --dry-run

# Apply the fixes
pipenv run python -m backend.app.db.post_migration
```

The script works on the database and data directory the server is configured with (`LIBREFOLIO_DATA_DIR`); `--db PATH` and `--data-dir PATH` select others, and broker folders are only touched when the database is inside the data directory. It prints the integrity check, each fix's outcome — `clean` (nothing to do), `would_apply` (dry run), `applied` or `failed` — the orphan broker folders found, a kept backup and any error. The exit code is `0` when nothing failed, a dry run included, and `1` when a fix or the integrity check failed.

---

## 📚 Documentation

```bash
# Build and deploy MkDocs documentation to GitHub Pages
pipenv run ./dev.py mkdocs deploy

# Generate gallery screenshots (uses Playwright; starts/controls a test server and populates test data unless --no-populate)
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
