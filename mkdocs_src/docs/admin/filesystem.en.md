# 📂 Filesystem Structure

LibreFolio keeps everything it stores in one **data directory**: the database, uploaded files, broker reports, logs and the instance key. Its layout is all you need to know for backups and maintenance.

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
│   ├── 💾 backups/                   # Archives written by ./dev.py backup create
│   ├── 🎭 scenario_catalog/          # Optional: your own stress scenarios
│   ├── 🗄️ cache/                     # Safe to delete: PDF preview fonts, fetched again
│   ├── 🔐 secrets/                   # Created when LibreFolio first needs the key
│   │   └── 🔑 instance.key           # The instance key: back it up, never change it
│   └── 📋 scheduler_state.json       # Scheduled syncs: last run, pending retry
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

**Reading the log.** Each line LibreFolio writes is one JSON object: the message is in `event`, the level in `level`, the time (UTC) in `timestamp`, and the traceback of an error in `exception`. Every line written while the server answers a request carries that request's `request_id`. When something fails, the same id reaches the browser: in the `X-Request-Id` header of the answer, in the body of a server error, and in the `[API]` line the web app writes to the browser's console (developer tools, **Console**). Ask the user who reports an error for that id, then read its lines with [jq](https://jqlang.org/), from the `logs/` folder:

```bash
# Every line of one request
jq -cR 'fromjson? | select(.request_id == "3f2a9c0d41b7e865")' librefolio.log

# The errors, each followed by its traceback
jq -rR 'fromjson? | select(.level == "ERROR" or .level == "CRITICAL") | "\(.timestamp) \(.request_id // "-") \(.event)", (.exception // empty)' librefolio.log
```

`fromjson?` skips the few lines that are not JSON, such as those of the libraries LibreFolio uses. For an archived week, unpack it on the way: `gzip -dc librefolio.log.2026-10-12.gz | jq -cR …`. A line about a failed request names its method and path, never its query string, its headers or its body.

### 🗄️ `cache/`

Copies LibreFolio can fetch again. Today it holds `pdf-fonts/`, the Chinese, Japanese and Korean fonts the PDF preview needs for a PDF that uses them, kept after the first download: see [The Content-Security-Policy](configuration.md#csp). Deleting it loses nothing, and it is not part of a [backup](backup_restore.md).

### 🔐 `secrets/`

- 🔑 `instance.key` holds the [instance key](configuration.md#instance-key), the secret from which LibreFolio derives its encryption keys. LibreFolio creates it the first time it needs the key. After that, a missing `instance.key` looks the same as a first use: LibreFolio creates a new key, and what the old one encrypted can no longer be read.
- 🔒 Only the user that runs LibreFolio can open the folder and the file: the folder is `0700`, the file `0600`. Keep them that way, and owned by that user: otherwise the [start log](configuration.md#startup-checks) has a warning, or an error when LibreFolio itself cannot open them.
- ⛔ Never edit, replace or delete the `instance.key` in use: what was encrypted with it could no longer be read. If it is damaged, or if LibreFolio has already replaced a lost one with a new key, stop LibreFolio and put your copy back before anyone enters a plugin secret again: see [The Instance Key](configuration.md#instance-key).
- ♻️ When you restore the data directory, put `secrets/` back with it before you start LibreFolio again. Never start LibreFolio on restored data without its `secrets/`.
- ⚙️ When the key comes from `LIBREFOLIO_INSTANCE_KEY` or `LIBREFOLIO_INSTANCE_KEY_FILE`, LibreFolio does not use this folder.

🔗 For developers: [Data directory on disk](../developer/architecture/database/index.md#data-directory) — every file, its format and the code that writes it, `scenario_catalog/` included.

---

## 🌍 Environment Variables

- `LIBREFOLIO_DATA_DIR` moves the production data directory, and `LIBREFOLIO_TEST_DATA_DIR` the test one. A relative path starts from the project folder.
- With Docker Compose the path inside the container is fixed: to keep the data elsewhere on the host, change the left side of the `./LibreFolio-data:/app/backend/data/prod-docker` volume in `docker-compose.yml`.

The other variables, and the `.env` file, are described in [Configuration](configuration.md).

---

## 💾 Backup

The recommended way is a backup archive, made while LibreFolio keeps running: see [Backup, Restore and Moving Your Instance](backup_restore.md). From the command line, `./dev.py backup create` writes one zip archive of the database, the uploaded files, the broker reports and your own stress scenarios, by default into the data directory's `backups/` folder: see [Back Up the Instance](cli_tools.md#backup), and [Back Up with Docker](cli_tools.md#backup-docker) for the command in the container. It leaves out `secrets/`, which you back up as [What to Back Up](#what-to-back-up) explains, unless you make it [secure](backup_restore.md#secure) (`--encrypt`): a secure archive carries the instance key LibreFolio generated. Copying the data directory by hand, below, is the alternative.

### 📦 Simple Backup

The easiest way to back up LibreFolio is to copy the entire data directory:

```bash
# Stop the server first (to ensure database consistency)
cp -r backend/data/prod/ /path/to/backup/librefolio-$(date +%Y%m%d)/
```

This copy, like the Docker one below, also takes `backups/`, with every archive `backup create` wrote there: delete the ones you no longer need first, or leave the folder out.

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

### ✅ What to Back Up {: #what-to-back-up }

At minimum, back up:

1. **`sqlite/app.db`** — All your data (users, transactions, settings, FX rates)
2. **`custom-uploads/`** — User-uploaded files (avatars, documents)
3. **`broker_reports/`** — The original broker reports, in case you need to import them again
4. **`scenario_catalog/`** — Your own stress scenarios, if you added any
5. **`secrets/`** — The instance key, if LibreFolio has created it

!!! warning "🔑 Keep `secrets/` with the data, and keep it private"

    Back up `secrets/` together with the database, and keep the copies as private as the database itself. Never change or delete the instance key once in use: what was encrypted with it could no longer be read. When you restore, put `secrets/` back with the data before you start LibreFolio.

    Only the user that runs LibreFolio can open `secrets/`. The same goes for `backups/`, made at the first backup, and `.restore/`, made the first time an archive is checked for a restore: LibreFolio creates both as `0700`, and the archives in `backups/` as `0600`. If `cp` reports `Permission denied` in one of them, for example with Docker when your host user is not the container's, copy as root and keep the permissions: `sudo cp -a`. Deleting an old archive from `backups/` fails the same way: use `sudo rm`.

If storage is limited, keep at least `sqlite/app.db`, which holds all the structured data, and the small `secrets/` folder: files and reports can be uploaded again if you still have them.
