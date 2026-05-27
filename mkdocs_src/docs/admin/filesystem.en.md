# 📂 Filesystem Structure

LibreFolio stores all persistent data in a structured directory under `backend/data/`. Understanding this structure is important for backup, debugging, and maintenance.

---

## 🗂️ Directory Layout

```
backend/data/
├── 📂 prod/                          # Production data (default)
│   ├── 🗃️ sqlite/
│   │   └── 📄 app.db                 # Main SQLite database (WAL mode)
│   ├── 🖼️ custom-uploads/            # User-uploaded files
│   │   ├── 📄 {uuid}.{ext}          # Binary file (image, document, etc.)
│   │   └── 📋 {uuid}.json           # Metadata sidecar (uploader, date, MIME type)
│   ├── 📊 broker_reports/
│   │   ├── 📥 uploaded/              # Reports waiting to be parsed
│   │   ├── ✅ parsed/               # Successfully parsed reports
│   │   └── ❌ failed/               # Reports that failed parsing
│   └── 📝 logs/                      # Application log files
│
└── 🧪 test/                          # Test data (completely isolated)
    ├── 🗃️ sqlite/app.db
    ├── 🖼️ custom-uploads/
    ├── 📊 broker_reports/
    └── 📝 logs/
```

---

## 📖 What's in Each Directory

### 🗃️ `sqlite/app.db`

The main SQLite database. Contains all application data: users, brokers, transactions, FX rates, settings, etc.

- 📝 Uses **WAL (Write-Ahead Logging)** journal mode for better concurrent access
- 📎 The `.db-wal` and `.db-shm` files are temporary WAL files — they're expected and managed by SQLite

:material-arrow-right: **Developer deep-dive**: [Database Schema](../developer/architecture/database/index.md)

### 🖼️ `custom-uploads/`

Files uploaded by users through the Files page. Each upload creates two files:

- 📄 `{uuid}.{ext}` — The actual binary file (e.g., `a1b2c3d4.png`)
- 📋 `{uuid}.json` — Metadata including: original filename, MIME type, file size, upload date, uploader user ID

:material-arrow-right: **Developer deep-dive**: [File Upload Component](../developer/frontend/components/file-upload.md)

### 📊 `broker_reports/`

Broker report files for the BRIM (Broker Report Import Manager) system:

- **📥 `uploaded/`** — Raw files as uploaded by users (CSV, Excel)
- **✅ `parsed/`** — Files that have been successfully processed (transactions extracted)
- **❌ `failed/`** — Files that failed parsing (kept for debugging — check logs for details)

:material-arrow-right: **Developer deep-dive**: [BRIM Architecture](../developer/backend/brim/architecture.md)

### 📝 `logs/`

Application logs in structured JSON format (via `structlog`).

---

## 🌍 Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `LIBREFOLIO_DATA_DIR` | `./backend/data/prod` | Override the production data directory path |
| `LIBREFOLIO_TEST_MODE` | `0` | Set to `1` to use `backend/data/test/` instead of `prod/` |
| `PORT` | `6040` | Production server port |
| `TEST_PORT` | `6041` | Test server port (used when `LIBREFOLIO_TEST_MODE=1`) |

---

## 💾 Backup

### 📦 Simple Backup

The easiest way to back up LibreFolio is to copy the entire data directory:

```bash
# Stop the server first (to ensure database consistency)
cp -r backend/data/prod/ /path/to/backup/librefolio-$(date +%Y%m%d)/
```

### 🐳 Docker Backup

If running via Docker, the data directory is typically mounted as a volume:

```bash
# Find the volume
docker volume inspect librefolio_data

# Copy data out
docker cp librefolio-container:/app/backend/data/prod/ ./backup/
```

### ✅ What to Back Up

At minimum, back up:

1. **`sqlite/app.db`** — All your data (users, transactions, settings, FX rates)
2. **`custom-uploads/`** — User-uploaded files (avatars, documents)
3. **`broker_reports/uploaded/`** — Original broker reports (in case you need to re-parse)

!!! tip "Database-only backup"

    If storage is limited, backing up just `sqlite/app.db` preserves all structured data. Files can always be re-uploaded.

---

## 🔧 Maintenance from Host Terminal

### 🐳 Docker exec

```bash
# Access the container shell
docker exec -it librefolio-container /bin/bash

# Run dev.py commands inside the container
./dev.py user list
./dev.py user reset admin newpassword
./dev.py db upgrade
```

### 💻 Direct access (non-Docker)

```bash
# From the project root
./dev.py user list              # List all users
./dev.py user reset <user> <pw> # Reset a user's password
./dev.py user promote <user>    # Grant superuser privileges
./dev.py user demote <user>     # Remove superuser privileges
./dev.py db upgrade             # Apply pending migrations
./dev.py db create-clean        # Reset database (WARNING: deletes all data)
```

For a full list of CLI commands, see [CLI Tools](cli_tools.md).
