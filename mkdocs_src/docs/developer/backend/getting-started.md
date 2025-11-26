# Getting Started with Backend Development

This guide will help you get your local environment set up for backend development.

## 1. Local Setup

Make sure you have completed the main [Installation guide](../../getting-started/installation.md). This includes:
- Cloning the repository.
- Installing dependencies with `pipenv`.
- Setting up your `.env` file.
- Creating the initial database with `alembic`.

## 2. Running the Development Server

The backend is a FastAPI application. To run it in development mode with hot-reloading:
```bash
./dev.sh server
```
The server will start on `http://localhost:8000` by default. Any changes you make to the Python code in `backend/app/` will trigger an automatic reload.

## 3. Running Tests

The project has a comprehensive test suite. It's crucial to run tests after making changes to ensure you haven't introduced any regressions.

The main entry point for tests is `test_runner.py`.

### Run All Tests
```bash
./test_runner.py all
```

### Run a Specific Test Category
```bash
# Run all service-layer tests
./test_runner.py services all

# Run all database-related tests
./test_runner.py db all
```

### Run a Single Test File
```bash
./test_runner.py services fx
```

For more details, see the [Testing Guide](./testing.md).

## 4. Database Migrations

When you change a `SQLModel` class in `backend/app/db/models.py`, you must create a database migration.

1.  **Generate the migration file**:
    ```bash
    ./dev.sh db:migrate "Your descriptive message here"
    ```
2.  **Apply the migration**:
    ```bash
    ./dev.sh db:upgrade
    ```

For a detailed guide, refer to the [Alembic Migrations Guide](../../developer/architecture/database.md).

## 🕵️ How to get information for backend development

To get information about backend development an Agent can:

1.  Read this file and the other guides in this section (`backend/`).
2.  Inspect the `dev.sh` script to see available helper commands.
3.  Read the `test_runner.py` script to understand the test structure.
4.  Explore the `backend/app/` directory to understand the project layout.
