# 📦 Host Installation (Pipenv)

This guide covers setting up LibreFolio directly on a host machine using Python, Node.js, and Pipenv. This manual installation method is suitable for users who want to run LibreFolio without Docker (e.g., on low-resource machines) and is also the first step for developers preparing a local development environment.

For containerized deployment, see the [User Manual Installation](../user/installation.md) or [Advanced Docker Guide](docker_advanced.md).

---

## ✅ Prerequisites

Before proceeding, ensure you have the following requirements installed on your system:

??? info "🐍 Python 3.13+"

    Python 3.13 is required for the FastAPI backend.
    
    * **macOS**: Install using Homebrew:
      ```bash
      brew install python@3.13
      ```
    * **Windows**: Download the installer from [python.org](https://www.python.org/downloads/) (make sure to check "Add Python to PATH").
    * **Linux (Ubuntu/Debian)**:
      ```bash
      sudo apt update
      sudo apt install python3.13 python3.13-venv python3.13-dev
      ```

??? info "📦 Node.js 20.19+"

    Node.js is required for building the SvelteKit frontend.
    
    * **macOS**: Install via Homebrew:
      ```bash
      brew install node@20
      ```
    * **Windows/Linux**: Install using [nvm](https://github.com/nvm-sh/nvm) (Linux/macOS) or [nvm-windows](https://github.com/coreybutler/nvm-windows) (Windows), or download directly from [nodejs.org](https://nodejs.org/).

??? info "📋 Pipenv"

    Pipenv manages virtual environments and dependencies for Python.
    
    * **All Platforms**:
      ```bash
      pip install --user pipenv
      ```
      *Note: Ensure your user-base binary paths (e.g., `~/.local/bin` on Linux/macOS or `%APPDATA%\Python` on Windows) are added to your shell's `PATH` variable.*

---

## 📋 Setup Instructions

LibreFolio includes an orchestration script, `dev.py`, to automate common management tasks.

!!! important "Python Environment Pre-requisite"

    Because `dev.py` imports modules from the backend application code, running it directly before installing dependencies will result in `ImportError` exceptions. 
    
    Therefore, the very first time you set up the project on your host, you must initialize the virtual environment by running:
    ```bash
    pipenv install --dev
    ```
    Once this initial environment is set up, you can safely use `dev.py` for all subsequent steps.

!!! tip "Running `dev.py` (Pipenv Context)"

    Since all backend dependencies are installed inside the virtual environment managed by `pipenv`, any command execution on the host must be run in that context:
    
    * **One-off commands**: Prefix your command with `pipenv run` (e.g., `pipenv run ./dev.py server`).
    * **Interactive shell**: Run `pipenv shell` beforehand to enter the virtual environment, after which you can run `./dev.py` directly without prefixes.
    
    *Note: If you are running commands inside a running Docker container (e.g., via `docker exec`), you do **not** need to use `pipenv run` or `pipenv shell`. The production Docker image pre-installs all Python dependencies globally in the container's system environment.*

### 📥 1. Download the Project

Clone the repository:

```bash
git clone https://github.com/Librefolio/LibreFolio.git
cd LibreFolio
```

Or download the latest release package from [GitHub Releases](https://github.com/Librefolio/LibreFolio/releases) and unzip it.

### 📦 2. Install Dependencies

Once your virtual environment is initialized, install all remaining Python, Node.js, and browser dependencies:

```bash
pipenv run ./dev.py install
```

Under the hood, this command will:

1. Initialize the Python virtual environment and install packages via `pipenv`.
2. Install frontend SvelteKit dependencies via `npm`.
3. Install Playwright browser binaries (used for PDF report generation and E2E tests).

### ⚙️ 3. Configure Environment

Copy the example environment file to create your active `.env` configuration:

```bash
cp .env.example .env
```

The default settings work immediately. Below are the key variables:

* **`PORT`**: Server bind port (default: `6040`).
* **`LIBREFOLIO_DATA_DIR`**: Directory path where the database, uploads, and logs are stored (default: `./backend/data/prod`).
* **`LOG_LEVEL`**: Logging verbosity (default: `INFO`).

For a complete description of all supported environment variables, see the [Environment Variables Guide](configuration.md).

### 🚀 4. Start the Server

To start the FastAPI server on the host:

```bash
pipenv run ./dev.py server
```

The server will be available at `http://localhost:6040`.

#### Server Command Options

| Flag | Description |
|------|-------------|
| `--host HOST` | Bind address (default: `HOST` env var or `0.0.0.0`) |
| `--port PORT` / `-p PORT` | Bind port (default: `PORT` env var or `6040`) |
| `--workers N` / `-w N` | Number of uvicorn workers (default: 1, disables reload) |
| `--no-scheduler` | Disable background sync jobs for market data |

### 👤 5. Accessing the App & Creating Users

The first time you access LibreFolio in your browser, you will see a **registration page** where you can create your first account. The first registered user automatically becomes the system administrator.

To manage users or promote them to administrator via the command line, refer to the [User CLI Tools Guide](cli_tools.md).

---

## 🗃️ Database Initialization & Reset

When running the application for the first time, the database is automatically initialized. If you need to reset the database to a clean slate, you can do so in two ways:

### 1. Terminal Command
You can run the clean command from the database CLI:
```bash
pipenv run ./dev.py db create-clean
```
> [!WARNING]
> This command will completely drop the existing SQLite database and recreate the schema from scratch. **All data will be permanently lost.**

### 2. Manual Reset
1. Stop the server if it is running.
2. Delete the SQLite database file (located by default at `backend/data/prod/sqlite/app.db`).
3. Restart the server; it will automatically initialize a fresh SQLite database file.
