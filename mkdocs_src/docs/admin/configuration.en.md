# 📝 Configuration

LibreFolio uses a `.env` file for configuration, powered by Pydantic's `BaseSettings`. This allows for easy management of environment variables for both local development and
Docker deployments.

## 📄 `.env` File

The `.env` file is located at the root of the project. A sample file, `.env.example`, is provided. To get started, simply copy it:

```bash
cp .env.example .env
```

### 🔑 Key Environment Variables

- **`PORT`**: The port on which the FastAPI server will run.
    - Default: `6040`

- **`TEST_PORT`**: The port on which the test server will run when test mode is enabled.
    - Default: `6041`

- **`LIBREFOLIO_DATA_DIR`**: The directory path where production data (SQLite database, logs, uploads) is stored.
    - Default: `./backend/data/prod`

- **`JWT_SECRET`**: The secret key used for signing JWTs (JSON Web Tokens) for user sessions.
    
    !!! note "Important"
        This must be set to a stable value if you want to prevent clients from losing their sessions across server restarts. (Note that multiple uvicorn workers spawned on the same host share the parent process's memory space, which contains the dynamically generated secret, meaning session persistence is naturally maintained across workers without a static key). However, for maximum security, leaving it empty and allowing it to be dynamically recomputed at runtime is the recommended choice.

- **`LOG_LEVEL`**: The logging level for the application.
    - Options: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`
    - Default: `INFO`

- **`PORTFOLIO_BASE_CURRENCY`**: The default base currency for the portfolio calculations.
    - Default: `EUR`

- **`PREVIEW_CACHE_MAX_MB`**: Maximum size (in MB) for the in-memory image preview cache.
    - Default: `50`
    - Cached thumbnails are evicted using LRU when limit is reached.

- **`BACKEND_CORS_ORIGINS`**: A JSON list of permitted CORS origins for development.
    - Default: `["http://localhost:3000", "http://localhost:5173"]`

- **`LIBREFOLIO_TEST_MODE`**: A flag to indicate if the application is running in test mode (forcing isolation using the test database).
    - Set to `1` to enable test mode.

## 🔝 Resolution Priority

When resolving configuration variables, LibreFolio respects an order of precedence from lowest (code defaults) to highest (Docker Compose overrides). For a detailed priority map and diagram, see the [Docker Resolution Priority Section](docker_advanced.md#resolution-priority).

## 📂 Data Separation

LibreFolio uses separate data directories for production and test:

- **Production**: `backend/data/prod/` (sqlite, custom-uploads, broker_reports, logs)
- **Test**: `backend/data/test/` (same structure, completely isolated)

The `get_data_dir()` function in `config.py` automatically selects the correct path based on `LIBREFOLIO_TEST_MODE`.

## ⚙️ How it Works

The settings are loaded into a Pydantic `Settings` class located in `backend/app/config.py`. This class automatically reads variables from the `.env` file and validates their types.

This approach provides:

- **Type Safety**: Settings are validated at application startup.
- **Centralized Configuration**: All settings are defined in one place.
- **Flexibility**: Settings can be provided via a `.env` file or as actual environment variables, making it easy to configure in different environments (local, Docker, etc.).
