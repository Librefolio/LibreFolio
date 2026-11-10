# 📦 Host Installation (Pipenv)

Install LibreFolio on your machine without Docker, with Python, Node.js and Pipenv: handy with few resources, and the first step towards a development environment.

For Docker, see the [User Manual Installation](../user/installation.md) or the [Advanced Docker Guide](docker_advanced.md).

---

## ✅ Prerequisites

Install these three tools first.

??? info "🐍 Python 3.13"

    The version set in the project's `Pipfile`.

    * **macOS**, with Homebrew:
      ```bash
      brew install python@3.13
      ```
    * **Windows**: download the installer from [python.org](https://www.python.org/downloads/) and check "Add Python to PATH".
    * **Linux (Ubuntu/Debian)**:
      ```bash
      sudo apt update
      sudo apt install python3.13 python3.13-venv python3.13-dev
      ```

??? info "📦 Node.js 24+"

    Builds the web interface.

    * **macOS**, with Homebrew:
      ```bash
      brew install node@24
      ```
    * **Windows/Linux**: with [nvm](https://github.com/nvm-sh/nvm) (Linux/macOS) or [nvm-windows](https://github.com/coreybutler/nvm-windows) (Windows), or download from [nodejs.org](https://nodejs.org/).

??? info "📋 Pipenv"

    Manages the Python virtual environment and its packages.

    * **All platforms**:
      ```bash
      pip install --user pipenv
      ```
      Add the user binaries folder (`~/.local/bin` on Linux/macOS, `%APPDATA%\Python` on Windows) to the shell's `PATH`.

---

## 📋 Setup Instructions

!!! tip "Commands run in the Pipenv environment"

    The `dev.py` commands start with `pipenv run`, which runs them in the project's virtual environment.
    Or enter it once with `pipenv shell`, then type `./dev.py …` without the prefix.

### 📥 1. Download the Project

**Where:** terminal, in the folder where you want the project.

```bash
git clone https://github.com/Librefolio/LibreFolio.git
cd LibreFolio
```

Result: the `LibreFolio/` folder. Or download and unzip the latest release from [GitHub Releases](https://github.com/Librefolio/LibreFolio/releases).

### 🐍 2. Create the Python Environment

**Where:** terminal, `LibreFolio/` folder.

```bash
pipenv install --dev
```

Result: the virtual environment with the Python packages. Do this before any `dev.py` command: without it, it stops with `ModuleNotFoundError`.

### 📦 3. Install the Other Dependencies

**Where:** terminal, `LibreFolio/` folder.

```bash
pipenv run ./dev.py install
```

Result, in order:

1. the Python packages again (`pipenv install --dev`);
2. the project tools (`npm ci`);
3. the web interface dependencies (`npm ci` in `frontend/`);
4. the Chromium browser of Playwright, for the end-to-end tests and the documentation screenshots. If only this download fails, the installation still completes.

### ⚙️ 4. Configure the Environment

**Where:** terminal, `LibreFolio/` folder; then the `.env` file just created.

```bash
cp .env.example .env
```

Result: the `.env` file with defaults that work as they are. The main variables:

| Variable | Default | Description |
| --- | --- | --- |
| `PORT` | `6040` | Server bind port. |
| `LIBREFOLIO_DATA_DIR` | `./backend/data/prod` | Directory of the database, uploaded files and logs (see [Filesystem Structure](filesystem.md)). |
| `LOG_LEVEL` | `INFO` | Logging verbosity. |

The other variables: [Environment Variables Guide](configuration.md).

### 🚀 5. Start the Server

**Where:** terminal, `LibreFolio/` folder.

```bash
pipenv run ./dev.py server
```

Result: LibreFolio answers on `http://localhost:6040`. The first start builds the web interface and the documentation: a few minutes. Workers, another port, the other options: [Command-Line Tools](cli_tools.md#start-the-server).

### 👤 6. Create Your Account

**Where:** browser, `http://localhost:6040`, link **Register here** below the login form.

Result: the first account registered becomes the administrator. To manage users from the terminal, see [Command-Line Tools](cli_tools.md). To have LibreFolio create the administrator at its first start, see [The Initial Administrator](configuration_accounts.md#initial-admin).

---

## 🗃️ Database Initialization & Reset {: #database-reset }

There is nothing to initialise: at every start the server creates the database if it is missing and applies the pending migrations.

To start again from an **empty database**, use one of the two ways below.

!!! warning "All data is lost"

    Both ways delete the database for good: users, brokers, transactions and settings. Make a backup first (see [Backup](filesystem.md#backup)).

### 🧹 With `dev.py`

**Where:** terminal, `LibreFolio/` folder, with the server stopped (the command refuses to run while the server is up).

```bash
pipenv run ./dev.py db create-clean
```

Result: a new, empty database.

### 🗑️ By Hand

**Where:** the data directory, by default `backend/data/prod/`.

1. Stop the server if it is running.
2. Delete the SQLite database file, by default `backend/data/prod/sqlite/app.db`.
3. Start the server: it creates a new one.

Both ways replace only the database: uploaded files, broker reports and logs stay in the data directory. For a completely fresh start, stop the server and delete the whole data directory: the next start recreates it.
