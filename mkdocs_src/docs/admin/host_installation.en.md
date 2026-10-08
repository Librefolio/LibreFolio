# 📦 Host Installation (Pipenv)

This guide installs LibreFolio directly on your machine with Python, Node.js and Pipenv, without Docker: handy on low-resource machines, and the first step towards a development environment.

For Docker, see the [User Manual Installation](../user/installation.md) or the [Advanced Docker Guide](docker_advanced.md).

---

## ✅ Prerequisites

Install these three tools first.

??? info "🐍 Python 3.13"

    The backend needs Python 3.13, the version set in the project's `Pipfile`.

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

??? info "📦 Node.js 24+"

    Node.js builds the web interface.

    * **macOS**: Install via Homebrew:
      ```bash
      brew install node@24
      ```
    * **Windows/Linux**: Install using [nvm](https://github.com/nvm-sh/nvm) (Linux/macOS) or [nvm-windows](https://github.com/coreybutler/nvm-windows) (Windows), or download directly from [nodejs.org](https://nodejs.org/).

??? info "📋 Pipenv"

    Pipenv manages the Python virtual environment and its packages.

    * **All Platforms**:
      ```bash
      pip install --user pipenv
      ```
      *Note: Ensure your user-base binary paths (e.g., `~/.local/bin` on Linux/macOS or `%APPDATA%\Python` on Windows) are added to your shell's `PATH` variable.*

---

## 📋 Setup Instructions

!!! tip "Commands run in the Pipenv environment"

    The `dev.py` commands start with `pipenv run`, which runs them in the project's virtual environment. You can also enter it once with `pipenv shell`, then type `./dev.py …` without the prefix.

### 📥 1. Download the Project

```bash
git clone https://github.com/Librefolio/LibreFolio.git
cd LibreFolio
```

Or download the latest release package from [GitHub Releases](https://github.com/Librefolio/LibreFolio/releases) and unzip it.

### 🐍 2. Create the Python Environment

```bash
pipenv install --dev
```

Do this before any `dev.py` command: `dev.py` needs these Python packages, and without them it stops with a `ModuleNotFoundError`.

### 📦 3. Install the Other Dependencies

```bash
pipenv run ./dev.py install
```

In order, it installs:

1. the Python packages again, with `pipenv install --dev`;
2. the project tools, with `npm install`;
3. the web interface dependencies, with `npm ci` in `frontend/`;
4. the Chromium browser of Playwright, used by the end-to-end tests and the documentation screenshots. If only this download fails, the installation still completes.

### ⚙️ 4. Configure the Environment

```bash
cp .env.example .env
```

The defaults work as they are. The main variables:

| Variable | Default | Description |
| --- | --- | --- |
| `PORT` | `6040` | Server bind port. |
| `LIBREFOLIO_DATA_DIR` | `./backend/data/prod` | Directory where the database, uploads and logs are stored (see [Filesystem Structure](filesystem.md)). |
| `LOG_LEVEL` | `INFO` | Logging verbosity. |

The other variables are described in the [Environment Variables Guide](configuration.md).

### 🚀 5. Start the Server

```bash
pipenv run ./dev.py server
```

The first start builds the web interface and the documentation, so it takes a few minutes. Then open `http://localhost:6040`. For workers, another port and the other options, see [Command-Line Tools](cli_tools.md#start-the-server).

### 👤 6. Create Your Account

Open LibreFolio in your browser and choose **Register here** below the login form: the first account registered becomes the administrator. To manage users from the terminal, see [Command-Line Tools](cli_tools.md).

---

## 🗃️ Database Initialization & Reset {: #database-reset }

There is nothing to initialise by hand: at every start, the server creates the database if it is missing and applies any pending migration.

To start again from an **empty database**, use one of the two ways below.

!!! warning "All data is lost"

    Both ways delete the database for good: users, brokers, transactions and settings. Back it up first (see [Backup](filesystem.md#backup)).

### 🧹 With `dev.py`

Stop the server (the command refuses to run while it is up), then:

```bash
pipenv run ./dev.py db create-clean
```

### 🗑️ By Hand

1. Stop the server if it is running.
2. Delete the SQLite database file (by default `backend/data/prod/sqlite/app.db`).
3. Start the server: it creates a fresh database.

Both ways replace only the database: uploaded files, broker reports and logs stay in the data directory. For a completely fresh start, stop the server and delete the whole data directory instead (by default `backend/data/prod/`): the next start recreates it.
