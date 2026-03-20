# 🐳 Advanced Docker Guide

This guide provides a deeper look into the Docker configuration for LibreFolio, intended for users who want to customize their deployment.

## `docker-compose.yml`

The `docker-compose.yml` file defines the services, networks, and volumes for the application.

### Services

- **`backend`**: The main FastAPI application.
    - **`build`**: Specifies the Dockerfile in the project root.
    - **`ports`**: Maps the host port (defined by `${PORT}` in `.env`) to the container's port 8000.
    - **`volumes`**:
        - `./backend:/app/backend`: Mounts the backend source code for development (allows for hot-reloading).
        - `./frontend/build:/app/frontend/build`: Mounts the production frontend build.
        - `./mkdocs_src/site:/app/mkdocs_src/site`: Mounts the documentation site.
        - `./logs:/app/logs`: Persists log files.
    - **`env_file`**: Loads environment variables from the `.env` file.

### Volumes

- **`libre-folio-data`**: A named volume used to persist the SQLite database files. This ensures that your data is not lost when you stop or remove the containers.

### Networks

- **`libre-folio-net`**: A custom bridge network to allow services to communicate with each other.

## Production Considerations

For a production deployment, you might consider the following changes:

### 1. Reverse Proxy

It is highly recommended to run LibreFolio behind a reverse proxy like **Nginx** or **Traefik**. This allows you to:

- Easily manage SSL/TLS certificates for HTTPS.
- Serve multiple applications on the same server.
- Add security headers and rate limiting.

### 2. Database Backup

Since the database is stored in a Docker volume, you should have a strategy for backing it up. You can use a simple `cron` job to copy the database file from the volume to a safe
location.

Example backup script:

```bash
#!/bin/bash
docker cp librefolio_backend_1:/app/backend/data/sqlite/app.db /path/to/backups/app.db-$(date +%F)
```

### 3. Disabling Development Mounts

In a production environment, you may not want to mount the source code directly. You can create a separate `docker-compose.prod.yml` file that omits the source code volumes and
relies solely on the built Docker image.
