# 🐳 Advanced Docker Guide

This guide provides a deeper look into the Docker configuration for LibreFolio, intended for users who want to customize their deployment.

## 🏗️ Architecture

LibreFolio uses a **runtime-only Docker image**. The frontend (SvelteKit) and documentation (MkDocs) are built on the host and then copied into the image. The `./dev.py docker build` command handles this automatically.

```text
Host (build)                    Docker Image (runtime)
┌──────────────┐                ┌──────────────────────┐
│ frontend/src │──npm build──▶  │ frontend/build/      │
│ mkdocs_src/  │──mkdocs ───▶   │ mkdocs_src/site/     │
│ backend/     │──copy──────▶   │ backend/             │
│ Pipfile*     │──pipenv ───▶   │ Python packages      │
└──────────────┘                └──────────────────────┘
```

## 📄 `docker-compose.yml`

The `docker-compose.yml` file defines the service and persistent volume.

### 🔧 Service: `librefolio`

- 🏗️ **`build: .`**: Builds from the `Dockerfile` in the project root.
- 🔌 **`ports`**: Maps the host port (`${PORT:-8000}`) to the container's port `8000`, and `${TEST_PORT:-8001}` to `8001` for test mode.
- 📂 **`volumes`**: A named volume `librefolio-data` is mounted at `/app/backend/data/prod-docker` to persist database, uploads, broker reports, and logs.
- 🌍 **`environment`**: Sets `HOST`, `PORT`, `LIBREFOLIO_DATA_DIR`, `LOG_LEVEL`, and `PORTFOLIO_BASE_CURRENCY`.
- 🩺 **`healthcheck`**: Polls `GET /api/v1/system/health` every 30 seconds.

### 💾 Volume: `librefolio-data`

A named Docker volume that persists the SQLite database, custom uploads, broker reports, and log files. Data survives container stop/restart/removal.

## 🛠️ CLI Commands

All Docker operations are available through `dev.py`:

```bash
./dev.py docker build          # Build image (auto-builds frontend + docs)
./dev.py docker build --no-cache  # Full rebuild without Docker cache
./dev.py docker rebuild        # Build → stop → restart (one-step deploy)
./dev.py docker up             # Start containers
./dev.py docker down           # Stop containers
./dev.py docker logs -f        # Follow container logs
./dev.py docker status         # Show container status
./dev.py docker exec <cmd>     # Run a dev.py command inside the container
```

### 📡 `docker exec` — Running Commands Inside the Container

The `docker exec` subcommand forwards any `dev.py` command into the running container:

```bash
./dev.py docker exec user create admin admin@example.com Pass123!
./dev.py docker exec user list
./dev.py docker exec db upgrade
./dev.py docker exec server --test
```

This is equivalent to running `docker compose exec librefolio python dev.py <cmd>`.

## 🧪 Test Mode

The Docker Compose configuration exposes **two ports**:

| Port | Purpose | Database |
|------|---------|----------|
| `8000` | Production server (started by container CMD) | `prod-docker/sqlite/app.db` (persistent volume) |
| `8001` | Test server (started manually via `docker exec`) | `test/sqlite/app.db` (ephemeral) |

### Starting the Test Server

1. **Start the container** (production server starts automatically on `:8000`):

    ```bash
    docker compose up -d
    ```

2. **Populate the test database** with mock data:

    ```bash
    ./dev.py docker exec test db populate --force --with-static
    ```

3. **Start the test server** on port 8001:

    ```bash
    ./dev.py docker exec server --test
    ```

4. **Access** at **`http://localhost:8001`**

    Test credentials:

    | Username | Password |
    |----------|----------|
    | `e2e_test_user` | `E2eTestPass123!` |
    | `e2e_test_admin` | `E2eAdminPass123!` |

!!! warning "Test data is ephemeral"

    The test database lives inside the container's **writable layer**, not on a persistent Docker volume. This means:

    - ✅ Data survives `docker compose stop` / `docker compose start` (container is paused, not removed).
    - ❌ Data is **lost** with `docker compose down` (container is removed and recreated).

    If you need persistent test data, add a dedicated volume in `docker-compose.yml`:

    ```yaml
    volumes:
      - librefolio-data:/app/backend/data/prod-docker
      - librefolio-test-data:/app/backend/data/test    # ← add this
    ```

    And declare the volume:

    ```yaml
    volumes:
      librefolio-data:
        driver: local
      librefolio-test-data:       # ← add this
        driver: local
    ```

## 🏭 Production Considerations

### 🔒 1. Reverse Proxy

It is highly recommended to run LibreFolio behind a reverse proxy like **Nginx** or **Traefik**. This allows you to:

- 🔐 Easily manage SSL/TLS certificates for HTTPS.
- 🖥️ Serve multiple applications on the same server.
- 🛡️ Add security headers and rate limiting.

### 💾 2. Database Backup

The database is stored in the `librefolio-data` Docker volume. Set up a `cron` job to back it up regularly:

```bash
#!/bin/bash
docker cp librefolio:/app/backend/data/prod-docker/sqlite/app.db /path/to/backups/app.db-$(date +%F)
```

### 🔑 3. Environment Variables

For production, consider setting these in `docker-compose.yml` or via `docker compose --env-file`:

| Variable | Default | Description |
|----------|---------|-------------|
| `PORT` | `8000` | Host port for production server |
| `TEST_PORT` | `8001` | Host port for test server |
| `LOG_LEVEL` | `INFO` | Logging verbosity (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |
| `PORTFOLIO_BASE_CURRENCY` | `EUR` | Base currency for portfolio calculations |
| `PREVIEW_CACHE_MAX_MB` | `50` | Max in-memory image preview cache (MB) |
