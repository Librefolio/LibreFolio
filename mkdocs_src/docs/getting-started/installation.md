# 🛠️ Installation (Development)

This guide covers setting up a local development environment. For production deployment, see the [User Manual Installation](../user/installation.md).

## Prerequisites

- **Python 3.11+**
- **Node.js 18+**
- **Pipenv** (Python package manager)
- **Docker** (Optional, for production deployment)

## Setup Instructions

The project includes a main orchestration script, `dev.py`, to automate all tasks.

### 1. Install Dependencies

This command installs all Python and Node.js dependencies for both the backend and frontend.

```bash
./dev.py install
```

This will:

1. Install backend packages via `pipenv`.
2. Install frontend packages via `npm`.
3. Install Playwright browsers for E2E testing.

### 2. Initialize the Database

Before starting the server for the first time, create the database:

```bash
./dev.py db create-clean
```

This command creates a fresh SQLite database with the initial schema.

### 3. Configure Environment

Copy the example environment file:

```bash
cp .env.example .env
```

The default settings work out of the box. Edit `.env` if you need to change port or data directory.

### 4. Start the Server

To start the FastAPI server with auto-reload:

```bash
../dev.py server
```

The server will be available at `http://localhost:8000`.

For frontend development with Hot Module Replacement, start a second terminal:

```bash
./dev.py front dev
```

The dev server runs at `http://localhost:5173` and proxies API calls to the backend.

### 5. Create a User

To log in, you need to create a user account. The first user automatically becomes the superuser.

```bash
./dev.py user create <username> <email> <password>
```

Replace `<username>`, `<email>`, and `<password>` with your desired credentials.

---

You are now ready to start developing! Run `./dev.py --help` for the full command tree.
