# End-to-End Tests (`e2e`)

These tests verify the full application stack, from the frontend UI down to the database.

## Purpose

To ensure that user flows (e.g., logging in, viewing the dashboard) work correctly in a real browser environment.

## Prerequisites

1. Backend server running in test mode (`./dev.sh server:test`).
2. Frontend built (`./dev.sh fe:build`).

## Key Tests

- **Login Flow**: Verifies that a user can log in and is redirected to the dashboard.
- **Dashboard**: Verifies that the dashboard loads and displays data.

## Running

```bash
./dev.sh test e2e
```
