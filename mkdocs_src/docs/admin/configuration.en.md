# 📝 Configuration

LibreFolio uses a `.env` file for configuration, powered by Pydantic's `BaseSettings`. This allows for easy management of environment variables for both local development and
Docker deployments.

## 🔧 Quick Start: Initialize Configuration

The `.env` file is located at the root of the project. A sample file, `.env.example`, is provided. To get started, simply copy it:

```bash
cp .env.example .env
```

## ✏️ Configuration Options (`.env` File)

These variables allow you to customize LibreFolio's behavior within the `.env` file. These are the same variables loaded by default by Docker Compose.

| Variable | Default | Description |
| --- | --- | --- |
| `PORT` | `6040` | The port on which the production FastAPI server will run. |
| `TEST_PORT` | `6041` | The port on which the test server will run when test mode is enabled. |
| `LIBREFOLIO_DATA_DIR` | `./backend/data/prod` | The root directory path where persistent data is stored (SQLite database, uploads, logs, etc.). Resolved at the system level: relative paths are resolved to absolute paths relative to the project root, while in Docker it is overridden and forced to `/app/backend/data/prod-docker` via Compose volume mappings. |
| `LOG_LEVEL` | `INFO` | The primary logging level for the application. Options: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`. |
| `PORTFOLIO_BASE_CURRENCY` | `EUR` | The default base currency for the portfolio calculations (ISO 4217 code). |
| `PREVIEW_CACHE_MAX_MB` | `50` | Maximum size (in MB) for the in-memory image preview cache. Entries expire after 1 hour (TTL); when the limit is reached, the oldest entries are evicted first. |

## 💻 System Parameters (Environment Variables)

These variables handle low-level integration between application modules, test isolation, and development CLI scripts. Typically, the user does not need to modify them directly, as the system (Docker Compose or the `dev.py` script) automatically assigns or manages them.

| Variable | Default | Description |
| --- | --- | --- |
| `HOST` | `0.0.0.0` | The network bind address for the FastAPI web server, automatically injected in Docker and CLI commands. |
| `JWT_SECRET` | _auto-generated_ | The secret key used for signing and decrypting user sessions (JSON Web Tokens). This variable is **not** part of the Pydantic `Settings` validation and is read at runtime directly from the operating system environment. If left empty, the application auto-assigns a secure, random key at startup (`secrets.token_urlsafe(64)`). When starting the server locally via `./dev.py server`, the runner script automatically generates and injects a shared secret to ensure session persistence across uvicorn workers. |
| `LIBREFOLIO_TEST_MODE` | — | A flag to indicate if the application is running in test mode. When set to `1` or `true`, it forces the application to completely isolate itself by redirecting the data directory to `backend/data/test/`. This is managed automatically by the test runners. |
| `LIBREFOLIO_LOG_LEVEL` | — | High-priority override for the logging level. If set, it takes absolute precedence and overrides the `LOG_LEVEL` property loaded by Pydantic at runtime (used by `./dev.py server --debug`). |

## 🔎 Asset Search — Web Link-Finder (Optional)

These variables tune the **last-resort external metasearch** used *only* during interactive asset search (Create Asset, and the "create asset" wizard inside broker import) when a provider's own on-site search returns zero results. They are **never** used on automated price fetches. Transport is the [`ddgs`](https://pypi.org/project/ddgs/) metasearch library. **All are optional and ship with safe defaults** — you only need to touch them to tune, diagnose, or disable the feature. See the developer guide [Asset Search & Link-Finder](../developer/backend/assets/search_link_finder.md) for the full design.

| Variable | Default | Description |
| --- | --- | --- |
| `LIBREFOLIO_WEB_LINK_FINDER_ENABLED` | `1` | Master on/off switch. Set to `0` to disable the external fallback entirely; provider on-site search keeps working. |
| `LIBREFOLIO_WEB_LINK_FINDER_ENGINE` | `ddgs` | Search transport. Options: `ddgs`, `apikey`. `ddgs` is the zero-config metasearch aggregator. `apikey` is reserved for a keyed engine (requires `..._API_KEY`); `searxng` is reserved for a future self-hosted phase. |
| `LIBREFOLIO_WEB_LINK_FINDER_DDGS_REGION` | `wt-wt` | `ddgs` region hint. `wt-wt` (worldwide) avoids a US bias so localized pages (e.g. Borsa Italiana) are not down-ranked. Examples: `it-it`, `us-en`. |
| `LIBREFOLIO_WEB_LINK_FINDER_DDGS_BACKEND` | `auto` | Which underlying engine(s) `ddgs` queries. `auto` rotates across many engines per call (max coverage, but **result quality varies call-to-call**). Pin a comma-separated subset (e.g. `google,bing,duckduckgo`) for **more deterministic** results at the cost of coverage. |
| `LIBREFOLIO_WEB_LINK_FINDER_TIMEOUT` | `6` | Per-request timeout, in seconds. |
| `LIBREFOLIO_WEB_LINK_FINDER_MAX` | `5` | Maximum number of candidate URLs returned per search. |
| `LIBREFOLIO_WEB_LINK_FINDER_API_KEY` | _empty_ | API key, used only when `ENGINE=apikey`. |

!!! tip "Non-deterministic results with `auto`"

    With the default `DDGS_BACKEND=auto`, the same query can return different-quality results on consecutive calls, because `ddgs` rotates engines. If an interactive search occasionally returns nothing for an instrument you know is indexed, retry once — or pin `DDGS_BACKEND` to a stable subset such as `google,bing,duckduckgo`.

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
