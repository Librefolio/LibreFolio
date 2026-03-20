# ⚙️ Backend Services Tests (`services`)

These tests verify the business logic encapsulated in the service layer. They typically mock external dependencies (like the database or APIs) to test logic in isolation.

## 🎯 Purpose

To ensure that complex business rules (e.g., BRIM parsing logic, asset metadata merging) are implemented correctly.

## 🔑 Key Tests

- **BRIM Providers**: Tests parsing of sample CSV files for each supported broker.
- **Asset Metadata**: Tests the logic for merging and patching asset metadata.

## 🚀 Running

```bash
./dev.py test services
```
