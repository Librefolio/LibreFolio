# Database Layer Tests (`db`)

These tests interact directly with the SQLite database file to verify its integrity and behavior. They do **not** require the backend server to be running.

## Purpose

To ensure the database schema, constraints, and data persistence are working correctly.

## Key Tests

-   **Schema Validation**: Checks that all tables, columns, and constraints exist as defined in the SQLAlchemy models.
-   **Data Integrity**: Verifies that `CHECK` constraints (e.g., positive quantities) and foreign keys are enforced.
-   **Persistence**: Tests basic CRUD (Create, Read, Update, Delete) operations on models like `Asset`, `Transaction`, etc.

## Running

```bash
./dev.sh test db all
```
