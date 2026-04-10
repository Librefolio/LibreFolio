# 🐳 Advanced Docker Guide

This guide provides a deeper look into the Docker configuration for LibreFolio, intended for users who want to customize their deployment.

## ⚠️ Prerequisites

!!! warning "Docker group (Linux)"

    On Linux, your user must be in the `docker` group to run Docker commands without `sudo`:

    ```bash
    sudo usermod -aG docker $USER
    ```

    Then **log out and log back in**, or run `newgrp docker` to activate the group in the current session. Without this, all `docker` and `docker compose` commands will fail with a permission error.

!!! warning "`.env` file required"

    LibreFolio requires a `.env` file in the project root. If it's missing, `./dev.py docker build` will refuse to proceed.

    ```bash
    cp .env.example .env
    $EDITOR .env          # review and customize parameters
    ```

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

The `docker-compose.yml` file defines the service and persistent data directory.

### 🔧 Service: `librefolio`

- 🏗️ **`build: .`**: Builds from the `Dockerfile` in the project root.
- 🔌 **`ports`**: Maps the host port (`${PORT:-8000}`) to the container's port `8000`, and `${TEST_PORT:-8001}` to `8001` for test mode.
- 📂 **`volumes`**: A bind mount `./LibreFolio-data` → `/app/backend/data/prod-docker` persists database, uploads, broker reports, and logs **in the same directory as `docker-compose.yml`**.
- 📝 **`env_file: .env`**: Loads all configuration from the `.env` file (copied from `.env.example`).
- 🌍 **`environment`**: Overrides only Docker-specific values: `LIBREFOLIO_DATA_DIR` (container path) and `HOST=0.0.0.0`.
- 🩺 **`healthcheck`**: Polls `GET /api/v1/system/health` every 30 seconds.

### 💾 Data Directory: `LibreFolio-data/`

A **bind mount** directory created alongside `docker-compose.yml`. Contains the SQLite database, custom uploads, broker reports, and log files. Data survives container stop/restart/removal. You can back it up directly from the host filesystem.

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

!!! tip "Documentation with screenshots"

    If you are building the documentation and want complete screenshots in the gallery, run:

    ```bash
    ./dev.py mkdocs --gallery
    ```

    This requires a fully installed environment (with `pipenv`) and a running server with populated test data. Be patient — gallery generation takes a few minutes.

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

    The test database lives inside the container's **writable layer**, not on a persistent bind mount. This means:

    - ✅ Data survives `docker compose stop` / `docker compose start` (container is paused, not removed).
    - ❌ Data is **lost** with `docker compose down` (container is removed and recreated).

    If you need persistent test data, add a dedicated bind mount in `docker-compose.yml`:

    ```yaml
    volumes:
      - ./LibreFolio-data:/app/backend/data/prod-docker
      - ./LibreFolio-test-data:/app/backend/data/test    # ← add this
    ```

## 🏭 Production Considerations

### 🎮 1. Customizing `docker-compose.yml`

The repository includes a ready-to-use `docker-compose.yml`. Here is the full file with annotations showing what you can customize:

```yaml
services:
  librefolio:
    image: librefolio:latest           # Built by ./dev.py docker build
    build: .
    container_name: librefolio
    restart: unless-stopped
    ports:
      - "${PORT:-8000}:8000"           # (1) Production port — change via PORT in .env
      - "${TEST_PORT:-8001}:8001"      # (2) Test server port (optional)
    volumes:
      - ./LibreFolio-data:/app/backend/data/prod-docker  # (3) Persistent data (bind mount)
    env_file: .env                     # (4) All config from .env file
    environment:
      - LIBREFOLIO_DATA_DIR=/app/backend/data/prod-docker  # Docker-specific override
      - HOST=0.0.0.0
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/v1/system/health')"]
      interval: 30s
      timeout: 10s
      start_period: 15s
      retries: 3
```

**Common customizations:**

| # | What | How |
|---|------|-----|
| (1) | Change production port | Set `PORT=3000` in `.env` |
| (2) | Disable test port | Remove the `TEST_PORT` line from `ports:` |
| (3) | Custom data path | Change bind mount: `./my-data:/app/backend/data/prod-docker` |
| (4) | All configuration | Edit `.env` file (copied from `.env.example`) |

!!! tip "First user"

    The first time you access LibreFolio in the browser, you'll see a registration page. Create your account directly — the first user automatically becomes the administrator. No CLI needed.

### 🔒 2. Reverse Proxy

It is highly recommended to run LibreFolio behind a reverse proxy like **Nginx** or **Traefik**. This allows you to:

- 🔐 Easily manage SSL/TLS certificates for HTTPS.
- 🖥️ Serve multiple applications on the same server.
- 🛡️ Add security headers and rate limiting.

### 💾 3. Database Backup

The database is stored in the `LibreFolio-data/` directory alongside `docker-compose.yml`. Back it up directly from the host filesystem:

```bash
#!/bin/bash
cp ./LibreFolio-data/sqlite/app.db /path/to/backups/app.db-$(date +%F)
```

No `docker cp` needed — the data directory is a bind mount accessible from the host.

### 🔑 4. Environment Variables

All configuration is managed in the `.env` file (copied from `.env.example`). The Docker-specific overrides in the `environment:` block should not be changed:

| Variable | Default | Description | Where |
|----------|---------|-------------|-------|
| `PORT` | `8000` | Host port for production server | `.env` |
| `TEST_PORT` | `8001` | Host port for test server | `.env` |
| `LOG_LEVEL` | `INFO` | Logging verbosity (`DEBUG`, `INFO`, `WARNING`, `ERROR`) | `.env` |
| `PORTFOLIO_BASE_CURRENCY` | `EUR` | Base currency for portfolio calculations | `.env` |
| `PREVIEW_CACHE_MAX_MB` | `50` | Max in-memory image preview cache (MB) | `.env` |
| `LIBREFOLIO_DATA_DIR` | `/app/backend/data/prod-docker` | Container path for data (do not change) | `docker-compose.yml` |
| `HOST` | `0.0.0.0` | Container bind address (do not change) | `docker-compose.yml` |
