# Command-Line Tools

This section provides detailed information on the command-line tools available in LibreFolio.

## `dev.sh`

`dev.sh` is the main orchestration script for development and maintenance tasks. It provides a convenient wrapper around common commands.

### Common Commands

-   **`./dev.sh install`**: Installs all project dependencies (Python and Node.js).
-   **`./dev.sh server`**: Starts the FastAPI server with auto-reload.
-   **`./dev.sh db:upgrade`**: Applies database migrations.
-   **`./dev.sh db:migrate "message"`**: Creates a new database migration.
-   **`./dev.sh test <args>`**: Runs the test suite.
-   **`./dev.sh fe:build`**: Builds the frontend for production.
-   **`./dev.sh info:mk deploy`**: Deploys the documentation to GitHub Pages.

For a full list of commands, run:
```bash
./dev.sh help
```

## `user_cli.py`

`user_cli.py` is a Python script for managing users and system settings from the command line. It is executed via `pipenv run python user_cli.py <command>`.

### User Management

-   **Create a Superuser**:
    ```bash
    ./dev.sh user:create <username> <email> <password>
    ```

-   **Reset a User's Password**:
    ```bash
    ./dev.sh user:reset <username> <new_password>
    ```

-   **List All Users**:
    ```bash
    ./dev.sh user:list
    ```

-   **Promote a User to Admin**:
    ```bash
    ./dev.sh user:promote <username>
    ```

### System Management

-   **Initialize Global Settings**:
    ```bash
    ./dev.sh user:init-settings
    ```
    This command populates the database with default global settings if they don't already exist.

## `test_runner.py`

`test_runner.py` is the entry point for running the project's test suites. It allows you to run specific tests or groups of tests.

### Running Tests

-   **Run all tests**:
    ```bash
    ./dev.sh test all
    ```

-   **Run a specific test group**:
    ```bash
    ./dev.sh test db all  # Run all database tests
    ```

-   **Run tests with coverage**:
    ```bash
    ./dev.sh test:coverage
    ```
    This generates an HTML report in the `htmlcov/` directory.

For more options, see the test runner's help message:
```bash
./dev.sh test --help
```
