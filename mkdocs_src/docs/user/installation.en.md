# 🐳 Installation (User)

This guide explains how to deploy LibreFolio for regular use using Docker. This is the recommended method for users who do not intend to modify the source code.

## ✅ Prerequisites

- 🐍 **Python 3.13+**: [Install Python](https://www.python.org/downloads/)
- 📦 **Node.js 20.19+**: [Install Node.js](https://nodejs.org/) (includes npm)
- 📋 **Pipenv**: `pip install pipenv`
- 🐋 **Docker**: [Install Docker](https://docs.docker.com/get-docker/) (includes Docker Compose)

!!! warning "Docker group (Linux)"

    On Linux, your user must be in the `docker` group to run Docker commands without `sudo`:

    ```bash
    sudo usermod -aG docker $USER
    ```

    Then **log out and log back in**, or run `newgrp docker` to activate the group in the current session.

!!! note "Why Python and Node.js?"

    LibreFolio uses a **runtime-only Docker image** — the frontend and documentation are built on the host before packaging into the Docker image. Pre-built images on a container registry are planned for future releases.

## 📥 1. Download the Project

Clone the repository:

```bash
git clone https://github.com/Alfystar/LibreFolio.git
cd LibreFolio
```

Or download the latest release from [GitHub Releases](https://github.com/Alfystar/LibreFolio/releases) and unzip it.

## ⚙️ 2. Configure Environment

1. **Copy the example file** (required — the build will refuse to proceed without `.env`):

    ```bash
    cp .env.example .env
    ```

2. **Edit `.env`** to customize:

    - 🔌 `PORT`: Change the port if `8000` is already in use.
    - 💰 `PORTFOLIO_BASE_CURRENCY`: Your base currency (default: `EUR`).
    - 📊 `LOG_LEVEL`: Logging verbosity (default: `INFO`).

## 📦 3. Install Dependencies

```bash
./dev.py install
```

This installs Python (backend) and Node.js (frontend) dependencies.

## 🏗️ 4. Build the Docker Image

```bash
./dev.py docker build
```

This command automatically:

1. Builds the frontend (SvelteKit production build)
2. Builds the documentation site (MkDocs)
3. Packages everything into a single Docker image tagged `librefolio:latest`

## 🚀 5. Start with Docker Compose

```bash
docker compose up -d
```

- 🔄 `-d` runs the application in detached mode (in the background).

## 🌐 6. Access LibreFolio

Open your browser and go to:

**`http://localhost:8000`**

(Or use the port you configured in `.env`).

The first time you access LibreFolio, you'll be presented with a **registration page** — create your account directly from the browser. The first user registered automatically becomes the administrator.

Available endpoints:

- 🏠 **Frontend**: `http://localhost:8000/`
- 📚 **User Docs**: `http://localhost:8000/mkdocs/`

!!! tip "CLI user management"

    You can also manage users from the command line. See the [Admin Manual — CLI Tools](../admin/cli_tools.en.md) for commands like user creation, promotion, and listing.

## 🔄 Updating LibreFolio

To update to a new version:

1. **Pull the latest code**:

    ```bash
    git pull
    ```

2. **Rebuild the Docker image** (auto-rebuilds frontend and docs if changed):

    ```bash
    ./dev.py docker rebuild
    ```

    This command builds a new image, stops the running containers, and restarts with the new version.

3. **Database migrations** are applied automatically on startup.

## 🧪 Try with Test Data (Optional)

You can start a test server with pre-populated mock data to explore the application before entering real data:

```bash
./dev.py docker exec test db populate --force --with-static
./dev.py docker exec server --test
```

Access at **`http://localhost:8001`** with user `e2e_test_user` / `E2eTestPass123!`.

The test server runs alongside the production one, using a separate database. See the [Advanced Docker Guide](../admin/docker_advanced.en.md#test-mode) for details.

---

!!! tip "Advanced topics"

    For reverse proxy setup, database backups, custom data paths, and production considerations, see the [🐳 Advanced Docker Guide](../admin/docker_advanced.en.md).

