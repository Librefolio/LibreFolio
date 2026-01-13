# Test Walkthrough

This section guides you through the LibreFolio test suite. Understanding the tests is one of the best ways to understand the codebase.

## Running Tests

The primary way to run tests is using the `dev.sh` helper script:

```bash
./dev.sh test all
```

This runs the `test_runner.py` script, which orchestrates the execution of `pytest`.

## Test Categories

The test suite is divided into several categories:

### 1. Database Tests (`db`)

-   **Purpose**: Verify database schema, migrations, and basic CRUD operations.
-   **Location**: `backend/test_scripts/test_db/`
-   **Key Tests**:
    -   `db_schema_validate.py`: Checks that all tables and columns exist.
    -   `test_fx_rates_persistence.py`: Verifies that FX rates can be saved and retrieved.

### 2. API Tests (`api`)

-   **Purpose**: Test the FastAPI endpoints. These are integration tests that spin up a test server and make HTTP requests.
-   **Location**: `backend/test_scripts/test_api/`
-   **Key Tests**:
    -   `test_auth_api.py`: Login, token generation.
    -   `test_assets_api.py`: Asset creation, retrieval.
    -   `test_transactions_api.py`: Transaction CRUD.

### 3. Service Tests (`services`)

-   **Purpose**: Test the business logic in the service layer, often mocking external dependencies.
-   **Location**: `backend/test_scripts/test_services/`
-   **Key Tests**:
    -   `test_brim_providers.py`: Verifies that BRIM plugins can parse sample files.
    -   `test_asset_providers.py`: Tests asset pricing providers.

### 4. End-to-End Tests (`e2e`)

-   **Purpose**: Test the full application flow using a real browser (via Playwright).
-   **Location**: `backend/test_scripts/test_e2e/`
-   **Note**: These tests require the frontend to be built and the server to be running.

## Coverage

You can generate a code coverage report to see which parts of the code are tested:

```bash
./dev.sh test:coverage
```

This will generate an HTML report in `htmlcov/index.html`.
