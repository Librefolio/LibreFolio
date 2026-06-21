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

:material-arrow-right: **Developer deep-dive**: [File Upload Component](../developer/frontend/components/core-ui/file-upload.md)

### 📊 `broker_reports/`

Broker report files for the BRIM (Broker Report Import Manager) system:

- **📥 `uploaded/`** — Raw files as uploaded by users (CSV, Excel)
- **✅ `parsed/`** — Files that have been successfully processed (transactions extracted)
- **❌ `failed/`** — Files that failed parsing (kept for debugging — check logs for details)

:material-arrow-right: **Developer deep-dive**: [BRIM Architecture](../developer/backend/brim/architecture.md)

### 📝 `logs/`

Application logs in structured JSON format (via `structlog`). Log files rotate weekly and are kept for 1 year (compressed with gzip).

The verbosity is controlled by the `LOG_LEVEL` environment variable.

**What each level captures** — each row shows which log levels are visible:

| LOG_LEVEL | 🔬 TRACE (5) | 🐛 DEBUG (10) | ℹ️ INFO (20) | ⚠️ WARNING (30) | ❌ ERROR (40) | 💀 CRITICAL (50) |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| 🔬`TRACE` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 🐛`DEBUG` | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ |
| ℹ️ **`INFO`** *(default)* | ❌ | ❌ | ✅ | ✅ | ✅ | ✅ |
| ⚠️ `WARNING` | ❌ | ❌ | ❌ | ✅ | ✅ | ✅ |
| ❌`ERROR` | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ |
| 💀`CRITICAL` | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |

**What each level means:**

| Level | What it captures |
|-------|-----------------|
|  🔬`TRACE` | High-frequency granular data: individual FX rates parsed, per-asset price points |
|  🐛`DEBUG` | Operational internals: which provider was used, intermediate results, algorithmic decisions |
|  ℹ️`INFO` | Significant user operations: sync completed, import, login, resource created/deleted |
|  ⚠️`WARNING` | Recoverable anomalies: fallback activated, missing optional data, degraded mode |
|  ❌`ERROR` | Handled errors: failed operations, data corruption, provider unreachable |
|  💀`CRITICAL` | Fatal errors that stop the process |

!!! tip "Recommended settings"

    - **Production**: `LOG_LEVEL=INFO` — clean signal, no noise
    - **Troubleshooting**: `LOG_LEVEL=DEBUG` — see what the system is deciding
    - **Deep FX/price debugging**: `LOG_LEVEL=TRACE` — see every individual data point

---

## 🌍 Environment Variables

The storage paths and runtime behaviors of the filesystem are controlled by environment variables (such as `LIBREFOLIO_DATA_DIR` and `LIBREFOLIO_TEST_MODE`). For a complete list of all supported environment variables and how to configure them using the `.env` file, see the [Configuration](configuration.md) page.

---

## 💾 Backup

### 📦 Simple Backup

The easiest way to back up LibreFolio is to copy the entire data directory:

```bash
# Stop the server first (to ensure database consistency)
cp -r backend/data/prod/ /path/to/backup/librefolio-$(date +%Y%m%d)/
```

### 🐳 Docker Backup

If you are running LibreFolio via Docker Compose (the standard deployment method), the production data directory is bind-mounted directly to the `./LibreFolio-data` directory on your host machine (and mapped to `/app/backend/data/prod-docker` inside the container).

Therefore, you do not need any special Docker copy commands; simply backing up the `./LibreFolio-data` folder on your host machine is sufficient to secure your data.

### ✅ What to Back Up

At minimum, back up:

1. **`sqlite/app.db`** — All your data (users, transactions, settings, FX rates)
2. **`custom-uploads/`** — User-uploaded files (avatars, documents)
3. **`broker_reports/uploaded/`** — Original broker reports (in case you need to re-parse)

!!! tip "Database-only backup"

    If storage is limited, backing up just `sqlite/app.db` preserves all structured data. Files can always be re-uploaded.
