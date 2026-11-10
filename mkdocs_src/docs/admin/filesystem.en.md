# 📂 Filesystem Structure

Everything LibreFolio stores lives in one **data directory**: database, uploaded files, broker reports, logs and the instance key.
Knowing it is all you need for backups and maintenance.

**Where it is.** In the rest of the page, `<data>` is this folder:

| Installation | `<data>` on the host | `<data>` inside the container |
| --- | --- | --- |
| Host (Pipenv) | `backend/data/prod/` in the project folder, or the path in `LIBREFOLIO_DATA_DIR` | — |
| Docker Compose | `LibreFolio-data/` next to `docker-compose.yml` | `/app/backend/data/prod-docker` |

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
│   ├── 💾 backups/                   # Backups kept by LibreFolio, one folder each
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

| Folder | What it holds | Who writes or reads it |
| --- | --- | --- |
| 🗃️ `sqlite/` | `app.db`: users, brokers, transactions, assets, prices, FX rates, settings | The server |
| 🖼️ `custom-uploads/` | Files uploaded in the app (such as those of the **Files** page) and default avatars | The app |
| 📊 `broker_reports/` | The uploaded broker reports, one `broker_<id>/` folder per broker | The import |
| 📝 `logs/` | `librefolio.log` and its weekly archives | The server writes, you read |
| 💾 `backups/` | The backups kept on the server, one folder each | Backup and restore |
| 🎭 `scenario_catalog/` | Your own stress scenarios, if you added any | You |
| 🗄️ `cache/` | Copies that can be downloaded again (`pdf-fonts/`) | The PDF preview |
| 🔐 `secrets/` | `instance.key`, the instance key | LibreFolio, the first time it needs the key |
| 📋 `scheduler_state.json` | Last run and pending retry of the scheduled syncs | The scheduled syncs |

---

## 📖 What's in Each Directory

### 🗃️ `sqlite/`

- 📎 `app.db-wal` and `app.db-shm`: SQLite's working files (WAL mode), present while the server runs. Never copy `app.db` alone while the server is up.
- 🔒 `app.db.post-migration.lock`: empty file used at startup, leave it in place.
- 🗑️ `app.db.pre-<fix>-<UTC time>.bak`: copy kept after a failed [post-migration fix](cli_tools.md#post-migration-fixes). Delete it once you no longer need it.

### 🖼️ `custom-uploads/`

Each file has a random name and a `.json` next to it that describes it: keep the pairs together.

### 📊 `broker_reports/`

Inside `broker_<id>/`, a report moves from `uploaded/` to `parsed/` or `failed/`: the original is always in one of the three.

- **📥 `uploaded/`** — waiting to be read
- **✅ `parsed/`** — read successfully
- **❌ `failed/`** — could not be read, kept so you can check why

### 📝 `logs/`

- 📄 `librefolio.log`: one JSON record per line; the server also prints the log to the console.
- 🗓️ Every Monday (UTC) the file is archived and compressed (`.gz`); the last 52 archives, one year, are kept.

**How much to write.** In LibreFolio's **`.env`** (default `INFO`):

```env
LOG_LEVEL=INFO
```

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

**Reading the log.** Each line is a JSON object: message in `event`, level in `level`, time (UTC) in `timestamp`, traceback in `exception`.
A line written during a request carries its `request_id`; when something fails, the same id reaches the browser: `X-Request-Id` header of the response, body of the server error, `[API]` line in the browser's console (developer tools, **Console**).

1. **Ask for the id** from the user who reports the error.
2. **In the `<data>/logs/` folder**, read its lines with [jq](https://jqlang.org/):

    ```bash
    # Every line of one request
    jq -cR 'fromjson? | select(.request_id == "3f2a9c0d41b7e865")' librefolio.log

    # The errors, each followed by its traceback
    jq -rR 'fromjson? | select(.level == "ERROR" or .level == "CRITICAL") | "\(.timestamp) \(.request_id // "-") \(.event)", (.exception // empty)' librefolio.log
    ```

    A failed-request line names method and path, never query string, headers or body.

- `fromjson?` skips the lines that are not JSON, such as those of the libraries LibreFolio uses.
- Archived week: `gzip -dc librefolio.log.2026-10-12.gz | jq -cR …`.

### 🗄️ `cache/`

`pdf-fonts/`: the Chinese, Japanese and Korean fonts the PDF preview downloads at first use when the PDF uses them, see [The Content-Security-Policy](configuration_security.md#csp).
Deleting it loses nothing; it is not part of a [backup](backup_restore.md).

### 🔐 `secrets/`

- 🔑 `instance.key` is the [instance key](configuration_secrets.md#instance-key), from which LibreFolio derives its encryption keys. If it is missing, LibreFolio treats it as a first use: it creates a new key and what was encrypted with the old one can no longer be read.
- 🔒 Folder `0700`, file `0600`, owned by the user that runs LibreFolio. Otherwise the [start log](configuration_security.md#startup-checks) has a warning, or an error if LibreFolio itself cannot open them.
- ⛔ Never edit, replace or delete the `instance.key` in use. If it is damaged, or if LibreFolio has already replaced a lost key with a new one: stop LibreFolio and put your copy back before anyone enters a plugin secret again, see [The Instance Key](configuration_secrets.md#instance-key).
- ♻️ When you restore the data directory, put `secrets/` back with it before you start LibreFolio. Never start LibreFolio on restored data without its `secrets/`.
- ⚙️ With the key in `LIBREFOLIO_INSTANCE_KEY` or `LIBREFOLIO_INSTANCE_KEY_FILE`, LibreFolio does not use this folder.

🔗 For developers: [Data directory on disk](../developer/architecture/database/index.md#data-directory) — every file, its format and the code that writes it, `scenario_catalog/` included.

---

## 🌍 Environment Variables

**Host, in LibreFolio's `.env`**. A relative path starts from the project folder:

```env
LIBREFOLIO_DATA_DIR=/path/to/data        # production data directory
LIBREFOLIO_TEST_DATA_DIR=/path/to/test   # test data directory
```

**Docker Compose, in `docker-compose.yml`.** The path inside the container is fixed: to keep the data elsewhere on the host, change the left side of the volume.

```yaml
- ./LibreFolio-data:/app/backend/data/prod-docker
```

The other variables and the `.env` file: [Configuration](configuration.md).

---

## 💾 Backup {: #backup }

The recommended way is a backup archive, made while LibreFolio keeps running: [Backup, Restore and Moving Your Instance](backup_restore.md).

- **From the command line**, `./dev.py backup create`: one zip of database, uploaded files, broker reports and stress scenarios, by default in a folder of its own inside `<data>/backups/`. See [Back Up the Instance](cli_backup.md#backup) and, for the command in the container, [Back Up with Docker](cli_backup.md#backup-docker).
- The archive **leaves out `secrets/`**, which you back up separately ([What to Back Up](#what-to-back-up)), unless you make it [secure](backup_restore.md#secure) with `--encrypt`: a secure archive holds the instance key LibreFolio generated.
- The alternative is to copy the data directory by hand, as below.

### 📦 Simple Backup

1. **Stop the server**, for the consistency of the database.
2. **From the project folder**, copy the whole data directory:

    ```bash
    # Stop the server first (to ensure database consistency)
    cp -r backend/data/prod/ /path/to/backup/librefolio-$(date +%Y%m%d)/
    ```

    Result: a complete, dated copy of `<data>`.

This copy, like the Docker one below, also includes `backups/`, with every backup LibreFolio keeps there ([Backups Kept on the Server](backup_restore.md#kept-backups)): delete the ones you no longer need first, set the [automatic clean-up](backup_restore.md#backup-cleanup), or leave the folder out.

### 🐳 Docker Backup

The data directory is the `LibreFolio-data/` folder on the host: no Docker copy command.

1. **From the folder of `docker-compose.yml`**, stop the container, copy, restart:

    ```bash
    docker compose stop librefolio
    cp -r ./LibreFolio-data/ /path/to/backup/librefolio-$(date +%Y%m%d)/
    docker compose start librefolio
    ```

    Result: a consistent copy; the server stays stopped only for the duration of the copy.

??? tip "🔄 Back up the database without stopping the server"

    SQLite's online backup makes a consistent copy while the server runs. It needs the `sqlite3` tool:

    ```bash
    sqlite3 backend/data/prod/sqlite/app.db ".backup '/path/to/backup/app.db'"
    ```

    With Docker, the database is `./LibreFolio-data/sqlite/app.db`. This command copies the database only: copy the folders listed below as usual.

### ✅ What to Back Up {: #what-to-back-up }

At minimum, back up:

1. **`sqlite/app.db`** — All your data (users, transactions, settings, FX rates)
2. **`custom-uploads/`** — User-uploaded files (avatars, documents)
3. **`broker_reports/`** — The original broker reports, in case you need to import them again
4. **`scenario_catalog/`** — Your own stress scenarios, if you added any
5. **`secrets/`** — The instance key, if LibreFolio has created it

!!! warning "🔑 Keep `secrets/` with the data, and keep it private"

    Save `secrets/` together with the database and keep the copies as private as the database. Never change or delete the instance key in use: what is encrypted with it can no longer be read. When you restore, put `secrets/` back with the data before you start LibreFolio.

    Only the user that runs LibreFolio can open `secrets/`. The same goes for `backups/`, created at the first backup, and `.restore/`, created the first time an archive is checked for a restore: LibreFolio creates both as `0700`, and the archives in `backups/` as `0600`. If `cp` reports `Permission denied` in one of them, for example with Docker when your host user is not the container's, copy as root and keep the permissions: `sudo cp -a`. Deleting an old archive from `backups/` fails the same way: use `sudo rm`.

If storage is limited, keep at least `sqlite/app.db`, which holds all the structured data, and the small `secrets/` folder: files and reports can be uploaded again if you still have them.
