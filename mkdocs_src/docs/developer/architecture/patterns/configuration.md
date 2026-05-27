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

- **`DATABASE_URL`**: The connection string for the main application database.
    - Default: `sqlite:///./backend/data/prod/sqlite/app.db`

- **`TEST_DATABASE_URL`**: The connection string for the test database.
    - Default: `sqlite:///./backend/data/test/sqlite/app.db`

- **`SECRET_KEY`**: A secret key used for signing JWTs (JSON Web Tokens) for authentication.
    - **Important**: For production, this should be changed to a long, random, and secret string.

- **`ACCESS_TOKEN_EXPIRE_MINUTES`**: The expiration time for access tokens in minutes.
    - Default: `30`

- **`LOG_LEVEL`**: The logging level for the application.
    - Options: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`
    - Default: `INFO`

- **`LIBREFOLIO_TEST_MODE`**: A flag to indicate if the application is running in test mode. This is used internally by the test suite.
    - Set to `1` to enable test mode.

- **`PREVIEW_CACHE_MAX_MB`**: Maximum size (in MB) for the in-memory image preview cache.
    - Default: `50`
    - Cached thumbnails are evicted using LRU when limit is reached.

## 📂 Data Separation

LibreFolio uses separate data directories for production and test:

- **Production**: `backend/data/prod/` (sqlite, custom-uploads, broker_reports, logs)
- **Test**: `backend/data/test/` (same structure, completely isolated)

The `get_data_dir()` function in `config.py` automatically selects the correct path based on `LIBREFOLIO_TEST_MODE`.

## ⚙️ How it Works

The settings are loaded into a Pydantic `Settings` class located in `backend/app/config.py`. This class automatically reads variables from the `.env` file and validates their
types.

This approach provides:

- **Type Safety**: Settings are validated at application startup.
- **Centralized Configuration**: All settings are defined in one place.
- **Flexibility**: Settings can be provided via a `.env` file or as actual environment variables, making it easy to configure in different environments (local, Docker, etc.).
