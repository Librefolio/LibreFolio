# Command-Line Tools

This section provides detailed information on the command-line tools available in LibreFolio.

## `dev.py`

`dev.py` is the main orchestration script for development and maintenance tasks. It provides a convenient wrapper around common commands with a tree-structured help system.

### Common Commands

- **`./dev.py install`**: Installs all project dependencies (Python and Node.js).
- **`./dev.py server`**: Starts the FastAPI server with auto-reload.
- **`./dev.py server --test`**: Starts in test mode (isolated test data).
- **`./dev.py db upgrade`**: Applies database migrations.
- **`./dev.py db migrate "message"`**: Creates a new database migration.
- **`./dev.py db create-clean`**: Recreate database from scratch.
- **`./dev.py test all`**: Runs the complete test suite.
- **`./dev.py front build`**: Builds the frontend for production.
- **`./dev.py front check`**: Type-checks Svelte/TypeScript.
- **`./dev.py front dev`**: Starts the frontend dev server with HMR.
- **`./dev.py api sync`**: Exports OpenAPI schema + generates TypeScript client.
- **`./dev.py i18n audit`**: Audit translation coverage.
- **`./dev.py mkdocs deploy`**: Deploys the documentation to GitHub Pages.

For a full command tree, run:

```bash
./dev.py --help
```

## User Management

User management is done via `./dev.py user` subcommands:

- **Create a User** (first user becomes admin):
  ```bash
  ./dev.py user create <username> <email> <password>
  ```

- **Reset a User's Password**:
  ```bash
  ./dev.py user reset <username> <new_password>
  ```

- **List All Users**:
  ```bash
  ./dev.py user list
  ```

- **Promote a User to Admin**:
  ```bash
  ./dev.py user promote <username>
  ```

- **Demote an Admin**:
  ```bash
  ./dev.py user demote <username>
  ```

### System Management

- **Initialize Global Settings**:
  ```bash
  ./dev.py user init-settings
  ```
  This command populates the database with default global settings if they don't already exist.

## `test_runner.py`

The test runner orchestrates the complete test suite. It is invoked via `./dev.py test`.

### Test Categories

| Category | Command                      | Description                       |
|----------|------------------------------|-----------------------------------|
| External | `./dev.py test external all` | Provider tests (FX, assets, BRIM) |
| Database | `./dev.py test db all`       | Database layer tests              |
| Services | `./dev.py test services all` | Service logic tests               |
| Utils    | `./dev.py test utils all`    | Utility tests                     |
| Schemas  | `./dev.py test schemas all`  | Schema validation tests           |
| API      | `./dev.py test api all`      | API endpoint tests                |
| E2E      | `./dev.py test e2e all`      | Backend end-to-end tests          |
| Frontend | `./dev.py test front all`    | Playwright E2E tests              |
| **All**  | `./dev.py test all`          | Run everything                    |
