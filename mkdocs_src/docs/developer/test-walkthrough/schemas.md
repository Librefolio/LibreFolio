# Schema Validation Tests (`schemas`)

These tests verify the Pydantic models used for data validation.

## Purpose

To ensure that invalid data is rejected before it reaches the business logic or database.

## Key Tests

-   **Input Validation**: Verifies that API request models correctly reject invalid inputs (e.g., negative prices, invalid dates).
-   **Serialization**: Verifies that models can be correctly serialized to JSON.

## Running

```bash
./dev.sh test schemas
```
