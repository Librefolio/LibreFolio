# 📂 Filesystem Structure

LibreFolio keeps everything it stores in one **data directory**: the database, uploaded files, broker reports and logs. Its layout is all you need to know for backups and maintenance.

| Installation | Data directory |
| --- | --- |
| Host (Pipenv) | `backend/data/prod/` in the project folder, or the path in `LIBREFOLIO_DATA_DIR` |
| Docker Compose | `LibreFolio-data/` next to `docker-compose.yml` (`/app/backend/data/prod-docker` inside the container) |

---

## 🗂️ Directory Layout

```text
backend/data/
├── 📂 prod/                          # Production data (default)
│   ├── 🗃️ sqlite/
│   │   └── 📄 app.db                 # Main SQLite database (WAL mode)
│   ├── 🖼️ custom-uploads/            # Files uploaded in the app
│   ├── 📊 broker_reports/
│   │   ├── 📥 uploaded/              # Reports waiting to be read
│   │   ├── ✅ parsed/                # Reports read successfully
│   │   └── ❌ failed/                # Reports that could not be read
│   ├── 📝 logs/                      # Application log files
│   ├── 🎭 scenario_catalog/          # Optional: your own stress scenarios
│   └── 📋 scheduler_state.json       # Last run of the scheduled syncs
│
└── 🧪 test/                          # Test data (completely isolated)
    ├── 🗃️ sqlite/app.db
    ├── 🖼️ custom-uploads/
    ├── 📊 broker_reports/
    └── 📝 logs/
```

---

## 📖 What's in Each Directory

### 🗃️ `sqlite/`

- 📄 `app.db` holds all the structured data: users, brokers, transactions, assets, prices, FX rates and settings.
- 📎 `app.db-wal` and `app.db-shm` are SQLite's working files (WAL mode), expected while the server runs: never copy `app.db` alone while the server is up.
- 🔒 `app.db.post-migration.lock` is an empty file used at startup: leave it in place. A file named `app.db.pre-<fix>-<UTC time>.bak` is a copy kept after a failed [post-migration fix](cli_tools.md#post-migration-fixes): delete it once you no longer need it.

### 🖼️ `custom-uploads/`

Files uploaded in the app, such as those of the **Files** page, and the default avatars. Each file has a random name and a `.json` file next to it that describes it: keep the pairs together.

### 📊 `broker_reports/`

The broker reports uploaded for import, in one `broker_<id>/` folder per broker:

- **📥 `uploaded/`** — waiting to be read
- **✅ `parsed/`** — read successfully
- **❌ `failed/`** — could not be read, kept so you can check why

A report moves from `uploaded/` to `parsed/` or `failed/`, so its original file is always in one of the three.

### 📝 `logs/`

- 📄 `librefolio.log` holds one JSON record per line; the server also prints the log to its console.
- 🗓️ Every Monday (UTC) the file is archived and compressed (`.gz`); the last 52 archives, one year, are kept.
- 🎚️ `LOG_LEVEL` in `.env` sets how much is written (default `INFO`).

??? info "📶 Log levels — what each one records"

    Each level also records all the more serious ones.

    | Level | What it captures |
    |-------|-----------------|
    | 🔬 `TRACE` | High-frequency granular data: individual FX rates parsed, per-asset price points |
    | 🐛 `DEBUG` | Operational internals: which provider was used, intermediate results, algorithmic decisions |
    | ℹ️ `INFO` *(default)* | Significant user operations: sync completed, import, login, resource created/deleted |
    | ⚠️ `WARNING` | Recoverable anomalies: fallback activated, missing optional data, degraded mode |
    | ❌ `ERROR` | Handled errors: failed operations, data corruption, provider unreachable |
    | 💀 `CRITICAL` | Fatal errors that stop the process |

    - **Production**: `LOG_LEVEL=INFO` — clean signal, no noise
    - **Troubleshooting**: `LOG_LEVEL=DEBUG` — see what the system is deciding
    - **Deep FX/price debugging**: `LOG_LEVEL=TRACE` — see every individual data point

🔗 For developers: [Data directory on disk](../developer/architecture/database/index.md#data-directory) — every file, its format and the code that writes it, `scenario_catalog/` included.

---

## 🌍 Environment Variables

- `LIBREFOLIO_DATA_DIR` moves the production data directory, and `LIBREFOLIO_TEST_DATA_DIR` the test one. A relative path starts from the project folder.
- With Docker Compose the path inside the container is fixed: to keep the data elsewhere on the host, change the left side of the `./LibreFolio-data:/app/backend/data/prod-docker` volume in `docker-compose.yml`.

The other variables, and the `.env` file, are described in [Configuration](configuration.md).

---

## 💾 Backup

### 📦 Simple Backup

The easiest way to back up LibreFolio is to copy the entire data directory:

```bash
# Stop the server first (to ensure database consistency)
cp -r backend/data/prod/ /path/to/backup/librefolio-$(date +%Y%m%d)/
```

### 🐳 Docker Backup

With Docker Compose, the data directory is the `LibreFolio-data/` folder on the host, so no Docker copy command is needed. Stop the container for a consistent copy:

```bash
docker compose stop librefolio
cp -r ./LibreFolio-data/ /path/to/backup/librefolio-$(date +%Y%m%d)/
docker compose start librefolio
```

??? tip "🔄 Back up the database without stopping the server"

    SQLite's online backup makes a consistent copy while the server runs. It needs the `sqlite3` tool:

    ```bash
    sqlite3 backend/data/prod/sqlite/app.db ".backup '/path/to/backup/app.db'"
    ```

    With Docker, the database is `./LibreFolio-data/sqlite/app.db`. This copies the database only: copy the folders below as usual.

### ✅ What to Back Up

At minimum, back up:

1. **`sqlite/app.db`** — All your data (users, transactions, settings, FX rates)
2. **`custom-uploads/`** — User-uploaded files (avatars, documents)
3. **`broker_reports/`** — The original broker reports, in case you need to import them again
4. **`scenario_catalog/`** — Your own stress scenarios, if you added any

If storage is limited, `sqlite/app.db` alone keeps all the structured data: files and reports can be uploaded again if you still have them.
