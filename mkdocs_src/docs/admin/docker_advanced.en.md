# 🐳 Advanced Docker Guide

This guide is for administrators who customize their Docker deployment, build their own image, or run maintenance on the container. For a first installation, start from the [Installation guide](../user/installation.md).

LibreFolio comes with two Compose files:

- **`docker-compose.prod.yml`** runs the official image from GHCR: the installation guide saves it as `docker-compose.yml`.
- **`docker-compose.yml`**, in the repository, runs an image you build yourself with `./dev.py docker build`.

## ⚠️ Prerequisites

**Docker group (Linux).** Your user must be in the `docker` group to run Docker commands without `sudo`:

```bash
sudo usermod -aG docker $USER
```

Then **log out and log back in**, or run `newgrp docker` to activate the group in the current session. Without this, all `docker` and `docker compose` commands fail with a permission error.

**`.env` file.** LibreFolio requires a `.env` file next to the Compose file, and `./dev.py docker build` refuses to proceed without it. In a checkout of the repository:

```bash
cp .env.example .env
$EDITOR .env          # review and customize parameters
```

## 🏗️ Architecture

The image is **runtime-only**: the web app (SvelteKit) and the documentation (MkDocs) are built on the host and copied into it, and `./dev.py docker build` runs those builds for you. Build stages, image contents and startup sequence: [Architecture overview → Docker image](../developer/architecture/overview.md#docker-image).

## 📄 `docker-compose.yml`

The Compose file defines the `librefolio` service and its persistent data directory.

### 🔝 Resolution Priority {: #resolution-priority }

When resolving configuration variables, LibreFolio respects the following order of precedence (from lowest to highest priority):

```mermaid
graph LR
    CodeDefaults[1. Code Defaults] --> EnvFile[2. .env File]
    HostShell[3. Host Env Variables]
    DockerCompose[4. docker-compose.yml environment block]

    EnvFile --> HostShell
    HostShell --> DockerCompose
```

In Docker, `.env` reaches the container through `env_file`, and the `environment:` block overrides it. For the `${…}` placeholders of the Compose file, such as `${PORT:-6040}`, a variable set in your shell wins over `.env`.

### 🔧 Service: `librefolio`

- 🏷️ **`image`**: the official `ghcr.io/librefolio/librefolio:latest` (production file) or your local `librefolio:latest` (repository file); `LIBREFOLIO_IMAGE` in `.env` picks another tag.
- 🏗️ **`build`** (repository file only): builds the root `Dockerfile` with the `UID`, `GID` and `DOCS_VARIANT` arguments.
- 🔌 **`ports`**: host `${PORT:-6040}` → container `6040`, the only port the image listens on. `PORT` chooses the host side; inside the container the server always listens on `6040`.
- 📂 **`volumes`**: the bind mount `./LibreFolio-data` → `/app/backend/data/prod-docker`.
- 📝 **`env_file: .env`**: loads your configuration (copied from `.env.example`).
- 🌍 **`environment`**: the Docker-specific `LIBREFOLIO_DATA_DIR` (container path), `HOST=0.0.0.0` and `PORT=6040`; leave them as they are. Inside the container, `PORT=6040` replaces the host port your `.env` may set, so the `dev.py` commands you run there ([`docker exec`](#docker-exec)) look for the server on the port it listens on: `db upgrade`, for example, sees it running and refuses to start.
- 🩺 **`healthcheck`**: polls `GET /api/v1/system/health` every 30 seconds.

!!! tip "📈 Monitoring LibreFolio: `/api/v1/system/ready`"

    The health check only tells Docker that the server answers. To know whether LibreFolio can actually serve requests, point a monitor such as **Uptime Kuma**, an orchestrator or a hosting panel at `GET /api/v1/system/ready`, for example `http://your-server:6040/api/v1/system/ready` (with your `PORT` if you changed it). It needs no sign-in, and the status code is all a monitor needs:

    - **`200`**: ready. The database answers, and its structure matches this version of LibreFolio: `{"status": "ready", "checks": {"database": "ok", "migrations": "ok"}, "mode": "normal"}`.
    - **`503`**: not ready. `status` is `not_ready`, and `checks` shows what is not `ok`: `database` is `unreachable` when the database does not answer; `migrations` is `mismatch` when the database is at another migration than this version of LibreFolio expects, and `unknown` when it cannot tell, for example while the database is `unreachable`.

    The answer never includes error details: LibreFolio writes them to its log (`docker compose logs librefolio`) as `Instance not ready`, once each time the state changes. `db current` shows the migration the database is at ([Apply Migrations](cli_tools.md#apply-migrations)).

### 💾 Data Directory: `LibreFolio-data/`

A **bind mount** directory next to the Compose file, holding the SQLite database, custom uploads, broker reports and log files. It survives container stop, restart and removal, and you back it up straight from the host.

### 👤 User & Permissions

The container starts as root only to hand the data directory over to the LibreFolio user, then runs the server as that **non-root** user: files it creates in `LibreFolio-data/` belong to that UID/GID on the host. The hand-over runs at every start and covers everything in the directory. Commands run with `./dev.py docker exec` use the same UID/GID ([details](#docker-exec)).

That UID/GID comes from the `UID` and `GID` **build arguments**: the image keeps them as `LIBREFOLIO_UID` and `LIBREFOLIO_GID`, which the entrypoint reads at every start. The official GHCR image is built with `1000:1000`. `./dev.py docker build` uses the ids of the user who runs it, whatever `.env` says, while `docker compose build` reads `UID` and `GID` from `.env` (default `1000`): set them to match the host user, or dedicated user, that should own the data files:

```bash
UID=1000
GID=1000
```

Changing them in `.env` takes effect only when `docker compose build` rebuilds the image: `.env` also reaches the container through `env_file`, but a restart does not change the ids. With the official image, which you do not build, these two lines have no effect.

- On the **host**, `ls -l LibreFolio-data/` shows the user and group that own that UID/GID on the host (resolved via `/etc/passwd` and `/etc/group`).
- **Inside the container**, the same files usually show as `librefolio:librefolio`: the same numeric UID/GID, resolved against the container's own `/etc/passwd` and `/etc/group`.

??? tip "Linux cheatsheet: users, groups, and IDs"

    **Discover your current UID and GID:**

    ```bash
    id -u              # your user ID (e.g. 1000)
    id -g              # your primary group ID (e.g. 1000)
    id                 # full info: uid, gid, groups
    ```

    **Find the UID/GID of any user:**

    ```bash
    id -u username     # UID of 'username'
    id -g username     # primary GID of 'username'
    ```

    **Create a new group:**

    ```bash
    sudo groupadd librefolio          # create group (auto-assigns GID)
    sudo groupadd -g 1500 librefolio  # create group with specific GID
    ```

    **Create a new user:**

    ```bash
    # System user (no home, no login — ideal for services)
    sudo useradd --system --no-create-home --gid librefolio --shell /usr/sbin/nologin librefolio

    # Regular user with home directory
    sudo useradd -m -g librefolio librefolio
    ```

    **Check the assigned IDs:**

    ```bash
    id librefolio
    # → uid=998(librefolio) gid=998(librefolio) groups=998(librefolio)
    ```

    **Add your existing user to a group:**

    ```bash
    sudo usermod -aG librefolio $USER
    newgrp librefolio    # activate in current session (or log out/in)
    ```

    **Verify group membership:**

    ```bash
    groups $USER         # list all groups for your user
    ```

    **Set ownership of the data directory:**

    ```bash
    sudo chown -R librefolio:librefolio ./LibreFolio-data
    ```

    Then set the matching UID/GID in `.env` and rebuild the image with `docker compose build`: at every start the container hands the directory back to the image's UID/GID.

## 🛠️ CLI Commands

In a checkout of the repository, `dev.py` wraps the Docker operations:

```bash
./dev.py docker build          # Build image (auto-builds frontend + docs)
./dev.py docker build --light  # Light variant: no documentation screenshots (tagged *-light)
./dev.py docker build --no-cache  # Full rebuild without Docker cache
./dev.py docker rebuild        # Build → stop → restart (one-step deploy)
./dev.py docker up             # Start containers
./dev.py docker down           # Stop containers
./dev.py docker logs -f        # Follow container logs
./dev.py docker status         # Show container status
./dev.py docker exec <cmd>     # Run a dev.py command inside the container
```

Without a checkout, the plain commands do the day-to-day work: `docker compose up -d`, `docker compose down`, `docker compose logs -f` and `docker compose ps`.

- `--light` builds the image without the documentation screenshots, which then load from the online docs site (see [Image Variants](../user/installation.md#image-variants-full-and-light)).
- Local tags: `librefolio:<version>` and `librefolio:latest` for the full image, `librefolio:<version>-light` and `librefolio:latest-light` for the light one, `<version>` being the git version of your checkout. On the registry instead, `latest` is the light variant and there is no `latest-light`.
- To run your light build with the repository's Compose file, set `LIBREFOLIO_IMAGE=librefolio:latest-light` in `.env`.

??? warning "🧱 When `./dev.py docker build` stops"

    **A resource cannot be downloaded.** The build caches a few external resources, such as the Noto Color Emoji font (flags on Windows) and MathJax (formulas in the documentation), so that the image works fully offline. If one cannot be downloaded and no cached copy exists yet, the build stops instead of shipping a broken image:

    ```text
    ❌ Resource cache incomplete — the build would ship without these:
       - noto-color-emoji: ...
    ```

    The **first build requires internet access** (or a pre-warmed cache). Once the network is back, run the build again; `./dev.py cache js` refreshes the cache by hand (`--force` re-downloads everything).

    **The frontend is a debug build.** The image must ship the production build of the web app. `./dev.py docker build` sees to it: it rebuilds `frontend/build/` in production mode when the last build was a debug one (for example by `./dev.py server --test`, `./dev.py server --debug` or the test runner), when its sources have changed, or when it was not built for this version ([details](../developer/dev_workflow.md#docker-build-steps)). An image built directly with `docker build` or `docker compose build` skips that step: if `frontend/build/` was last built in debug mode or instrumented for coverage, the image build stops with an error like:

    ```text
    ERROR: /build is not a production frontend build: it is a debug build (.build-debug = 1)
    Rebuild it with './dev.py front build', then build the image again.
    ```

    Run `./dev.py front build`, then build the image again, or build it with `./dev.py docker build`.

??? tip "🖼️ Building a full image with the documentation screenshots"

    A full image contains the documentation screenshots only if they were generated, and the documentation rebuilt with them, **before** the image build: otherwise a local full image and a light one are the same apart from their tag. The complete sequence is:

    ```bash
    ./dev.py mkdocs gallery   # generate the screenshots
    ./dev.py mkdocs build     # rebuild the documentation with the screenshots
    ./dev.py docker build     # build the full image; it rebuilds for production the debug frontend the gallery leaves
    ```

    `./dev.py mkdocs gallery` requires a fully installed environment (with `pipenv`) and Playwright browsers. It starts its own test server and populates the test database automatically (`--no-populate` skips reseeding). Gallery generation takes a few minutes.

### 📡 `docker exec` — Running Commands Inside the Container {: #docker-exec }

`./dev.py docker exec <cmd>` runs a `dev.py` command inside the **running** container, as the same user as the server: the numeric `LIBREFOLIO_UID:LIBREFOLIO_GID` of the image (see User & Permissions above), not root. Files a command creates in `LibreFolio-data/` therefore belong to that user straight away, like the server's own. For example, to manage users:

```bash
./dev.py docker exec user create admin admin@example.com Pass123!
./dev.py docker exec user list
```

Behind the scenes, `./dev.py docker exec user list` runs the line below, which also works without a checkout. `gosu`, which the entrypoint uses too, switches to the image's ids before `dev.py` starts:

```bash
docker compose exec librefolio sh -c 'exec gosu "${LIBREFOLIO_UID:-1000}:${LIBREFOLIO_GID:-1000}" python dev.py "$@"' sh user list
```

A plain `docker compose exec librefolio python dev.py <cmd>` runs the command as root instead: what it creates in `LibreFolio-data/` belongs to root until the container's next start, when the entrypoint hands the directory back to the image's user.

In the image, `user`, `db`, `info` and `backup` work ([Back Up with Docker](cli_tools.md#backup-docker)). The development commands (`test`, `i18n`, `mkdocs translate` and `mkdocs translate-validate`) are listed too, but they only answer that they are *not available in this installation*: the image ships the application, not the development tree.

The test-mode commands do not run in the container either; like `./dev.py mkdocs gallery`, they belong to a development checkout:

- `./dev.py docker exec test db populate` gets the same *not available* answer as every `test` command;
- `./dev.py docker exec server --test` stops with `Frontend build failed. Server not started.`: test mode first tries to rebuild the web app in debug mode, which needs Node.js and the web app's sources, while the image ships only the production build, without Node.js.

**Database migrations need no command.** The server applies pending migrations every time it starts: after `docker compose pull` and `docker compose up -d` there is nothing else to run, and `docker compose restart librefolio` retries them after a failure. A restart does not help when the 1.3 upgrade stops because two accounts share an email address apart from its capitals: separate the accounts first, as «Two Accounts with the Same Email Address» in [Command-Line Tools](cli_tools.md) explains. Do not use `./dev.py docker exec db upgrade`: `db upgrade` needs the server stopped, and in the container the server is the main process, always running.

## 🩹 Post-Migration Fixes {: #post-migration-fixes }

Every time the server starts, right after applying any pending database migration, it runs the **post-migration fixes**: repairs that a migration cannot make. What they repair, and what the log says about them, is explained in [Command-Line Tools → Post-Migration Fixes](cli_tools.md#post-migration-fixes). In Docker:

- the log is the container output (`./dev.py docker logs` or `docker compose logs`), also saved in `LibreFolio-data/logs/`;
- a copy kept by a failed fix sits next to the database, in `LibreFolio-data/sqlite/`, for example `app.db.pre-autoincrement-20261008T101500Z.bak`.

### ⏹️ Running the Fixes with the Server Stopped

To preview the fixes, or to retry one that failed at startup and read its error, run them by hand with the server stopped. `docker exec` needs the running container, so use `docker compose run` instead: the command you pass replaces the server in a one-off container. Always preview with `--dry-run` first:

```bash
docker compose stop librefolio
docker compose run --rm librefolio python -m backend.app.db.post_migration --dry-run   # preview: changes nothing
docker compose run --rm librefolio python -m backend.app.db.post_migration             # apply the fixes
docker compose start librefolio
```

The script works on the same database and data directory as the server and reports what it found, for example:

```text
Database: /app/backend/data/prod-docker/sqlite/app.db
Integrity check: ok
Fix autoincrement: would_apply
Orphan broker folder: broker_reports/uploaded/broker_7
```

Each fix is `clean` (nothing to do), `would_apply` (dry run), `applied` or `failed`; a kept backup and any error are listed as well, and so is each transfer of securities sent to a deleted broker, with the cost it takes or the reason it stays as it is ([details](cli_tools.md#post-migration-fixes)). The exit code is `0` when nothing failed, a dry run included, and `1` when a fix, the integrity check or the conversion of those transfers failed.

## 🧪 Test Mode

The image has no test mode: it listens only on `6040`, the production server started with the container, and both Compose files publish only that port. The test server (`./dev.py server --test`, on port `6041` by default) is a developer tool that runs from a source checkout, on the host. Its database, `backend/data/test/sqlite/app.db` by default, is separate from `LibreFolio-data/`: `./dev.py test db populate --force` deletes and recreates it with mock data.

How to start it, and why it does not start in the container, is in the [Developer Workflow](../developer/dev_workflow.md#docker-test-mode).

## 🏭 Production Considerations

### 🎮 1. Customizing `docker-compose.yml`

The most common changes:

| # | What | How |
|---|------|-----|
| (1) | Match host UID/GID | Rebuild the image with them: run `./dev.py docker build` as the user who should own the files, or set `UID=1001` and `GID=1001` in `.env` and run `docker compose build` |
| (2) | Change production port | Set `PORT=3000` in `.env` |
| (3) | Custom data path | Change bind mount: `./my-data:/app/backend/data/prod-docker` |
| (4) | All configuration | Edit `.env` file (copied from `.env.example`) |
| (5) | Run another image tag | Set `LIBREFOLIO_IMAGE` in `.env`, for example `LIBREFOLIO_IMAGE=ghcr.io/librefolio/librefolio:1.1.0` |

The first account created in the browser automatically becomes the administrator: no command needed. To have LibreFolio create the administrator at its first start instead, from `LIBREFOLIO_ADMIN_EMAIL`, see [The Initial Administrator](configuration.md#initial-admin).

??? example "📄 The repository's `docker-compose.yml`, annotated"

    ```yaml
    services:
      librefolio:
        image: ${LIBREFOLIO_IMAGE:-librefolio:latest}  # (5) Built by ./dev.py docker build
        build:
          context: .
          args:
            UID: ${UID:-1000}              # (1) UID owning the data files (build time only)
            GID: ${GID:-1000}              # (1) GID owning the data files (build time only)
            DOCS_VARIANT: ${DOCS_VARIANT:-full}  # light = no documentation screenshots
        container_name: librefolio
        # No 'user:' directive — entrypoint starts as root, fixes permissions,
        # then drops to the numeric LIBREFOLIO_UID:LIBREFOLIO_GID via gosu, like ./dev.py docker exec.
        restart: unless-stopped
        ports:
          - "${PORT:-6040}:6040"           # (2) Production port — change via PORT in .env
        volumes:
          - ./LibreFolio-data:/app/backend/data/prod-docker  # (3) Persistent data (bind mount)
        env_file: .env                     # (4) All config from .env file
        environment:
          - LIBREFOLIO_DATA_DIR=/app/backend/data/prod-docker  # Docker-specific override
          - HOST=0.0.0.0
          - PORT=6040                      # The container's port; (2) sets the host side
        healthcheck:
          test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:6040/api/v1/system/health')"]
          interval: 30s
          timeout: 10s
          start_period: 15s
          retries: 3
    ```

    `docker-compose.prod.yml` has the same service without `build:`, and its image defaults to `ghcr.io/librefolio/librefolio:latest`.

### 🔒 2. Security and Exposure (Tailscale and Reverse Proxy)

Expose LibreFolio securely through **Tailscale** (recommended, and the simplest choice) or behind a classic reverse proxy such as **Nginx** or **Traefik**:

- **Tailscale (recommended)**: secure access with automatic HTTPS, without opening router ports or setting up public DNS records. See the detailed **[Tailscale Exposure Guide](service_exposure.md)**.
- **Classic reverse proxy (Nginx/Traefik)**: useful if you already have a web infrastructure, or want to manage custom SSL/TLS certificates, serve several applications on one server, or add custom security headers and rate limiting.

Once LibreFolio is exposed, [Checking Connection Security](connection_checks.md) shows how to verify that your users connect securely and, [behind a reverse proxy](connection_checks.md#reverse-proxy), that the session cookie is marked `Secure`.

Behind a classic reverse proxy, also tell LibreFolio which proxy to trust (`FORWARDED_ALLOW_IPS`) or which header holds the visitor's address (`LIBREFOLIO_CLIENT_IP_HEADER`): otherwise LibreFolio sees every visitor with the proxy's address, and warns about it in its log and in its security checks. See [The Visitor's Address](connection_checks.md#client-address).

LibreFolio already gzip-compresses its responses (API JSON, the web app's JavaScript and CSS, documentation pages) and sends images and the live asset-search stream as they are: the proxy does not need to compress them again.

### 💾 3. Database Backup

The database is stored in the `LibreFolio-data/` directory alongside `docker-compose.yml`. No `docker cp` needed — the data directory is a bind mount accessible from the host.

!!! warning "Do not copy `app.db` from a running container"

    LibreFolio runs SQLite in **WAL mode** (`PRAGMA journal_mode=WAL`): recent transactions live in the `app.db-wal` sidecar file, so a plain `cp` of `app.db` alone while the server is up can produce an inconsistent or stale backup. Use one of the two safe procedures below.

**Option A — Stop the container, then copy** (simplest):

```bash
#!/bin/bash
docker compose stop librefolio
cp ./LibreFolio-data/sqlite/app.db /path/to/backups/app.db-$(date +%F)
docker compose start librefolio
```

**Option B — Online backup with the SQLite CLI** (no downtime, requires the `sqlite3` tool on the host):

```bash
#!/bin/bash
sqlite3 ./LibreFolio-data/sqlite/app.db ".backup '/path/to/backups/app.db-$(date +%F)'"
```

SQLite's `.backup` command uses the online backup API, which is safe against a live WAL database.

`backup create` needs neither a stop nor `sqlite3` on the host: `docker compose exec librefolio python dev.py backup create` puts a consistent copy of the database, the uploaded files, the broker reports and your own stress scenarios in one archive, in `LibreFolio-data/backups/`, while the server keeps running ([Back Up with Docker](cli_tools.md#backup-docker)). A clear archive leaves out `secrets/`, which holds the instance key: back that folder up as [What to Back Up](filesystem.md#what-to-back-up) explains. A [secure archive](backup_restore.md#secure), with `--encrypt`, carries the key LibreFolio generated, encrypted with your password.

For the full list of what is worth backing up (uploaded files, original broker reports), see the [Filesystem Layout](filesystem.md) page.

Files you may find next to the database:

- `app.db.pre-<fix>-<UTC time>.bak`: a copy kept by a [post-migration fix](#post-migration-fixes) that failed; delete it when you no longer need it.
- `app.db.post-migration.lock`: the empty lock file of the [post-migration fixes](#post-migration-fixes), reused at every start. It is harmless: leave it in place, since deleting it while the server is starting could let two runs overlap.

### 🔑 4. Environment Variables

All configuration is managed in the `.env` file (copied from `.env.example`); leave the Docker-specific overrides of the `environment:` block as they are. For every variable and its effect, see the **[Configuration Guide](configuration.md)**.

🔐 **Keep users signed in across restarts**: set `JWT_SECRET` in `.env` to a long random string, for example the output of `openssl rand -hex 32`. Without it, LibreFolio generates a new key at every start, so each restart or update of the container signs every user out.

### ✅ 5. Verify the Image You Pull {: #verify-image }

Every image LibreFolio publishes on GHCR (`ghcr.io/librefolio/librefolio`, the full and the light variant) comes with a **build attestation**: a statement, signed by the release pipeline of the project's repository, that this exact image was built there from this code. It is signed without any key of ours to keep or lose (GitHub proves the identity of the run, and Sigstore records it), so anyone can check it.

Take the digest of the image you pulled, then ask GitHub to verify it with the [GitHub CLI](https://cli.github.com/):

```bash
# The digest of a tag (the line "Digest: sha256:…")
docker buildx imagetools inspect ghcr.io/librefolio/librefolio:1.3.0

# Verify the attestation of that digest
gh attestation verify oci://ghcr.io/librefolio/librefolio@sha256:<digest> --owner Librefolio
```

A verified image prints `✓ Verification succeeded!` with the repository and the workflow that built it. Nothing printed but an error means this digest was not built by LibreFolio's pipeline: do not run it. The attestation covers every tag that points to the same digest (`1.3.0`, `latest`...). Releases published before this check was added carry none.
