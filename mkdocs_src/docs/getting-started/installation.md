# 🛠️ Installation (Development)

This guide covers setting up a local development environment. For production deployment, see the [User Manual Installation](../user/installation.md).

## Prerequisites

-   **Python 3.11+**
-   **Node.js 18+**
-   **Pipenv** (Python package manager)
-   **Docker** (Optional, for running a clean database)

## Setup Instructions

The project includes a helper script, `dev.sh`, to automate most tasks.

### 1. Install Dependencies

This command installs all Python and Node.js dependencies for both the backend and frontend.

```bash
./dev.sh install
```

This will:
1.  Install backend packages via `pipenv`.
2.  Install frontend packages via `npm`.
3.  Install Playwright browsers for E2E testing.

### 2. Initialize the Database

Before starting the server for the first time, you need to apply the database migrations.

```bash
./dev.sh db:upgrade
```

This command uses **Alembic** to create the SQLite database and apply all schema changes.

### 3. Start the Server

To start the FastAPI server with auto-reload:

```bash
./dev.sh server
```

The server will be available at `http://localhost:8000`.

The first time you run this, it will automatically build the frontend. On subsequent runs, it will only rebuild if it detects changes in the `frontend/src` directory.

### 4. Create a Superuser

To log in, you need to create a user account.

```bash
./dev.sh user:create <username> <email> <password>
```

Replace `<username>`, `<email>`, and `<password>` with your desired credentials.

---

You are now ready to start developing!
