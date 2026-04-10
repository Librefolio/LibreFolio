# 📡 API Endpoint Tests (`api`)

These are integration tests that run against a live backend server. They verify the full request-response cycle.

## 🎯 Purpose

To ensure that the API endpoints are reachable, return the correct status codes, and produce the expected JSON responses.

## ✅ Prerequisites

The backend server must be running in **test mode**:

```bash
./dev.py server --test
```

## 🔑 Key Tests

- **Auth**: Login, token refresh, protected routes.
- **Assets CRUD**: Create, read, update, delete assets via API (19 tests).
- **Assets Metadata**: Classification params, sector/geo distributions (4 tests).
- **Assets Patch**: Partial field updates including identifiers (8 tests).
- **Assets Provider**: Provider assignment, probe with valid/invalid params, Scheduled Investment via API (16 tests).
- **Assets Prices**: Bulk upsert, query with backward-fill, sync idempotency, events in response, bulk multi-asset sync (9 tests).
- **FX**: Currency pair CRUD, conversion, sync, delete (25+ tests).
- **Brokers**: CRUD, sharing, multi-user access control.
- **Transactions**: Import and manage transactions.
- **Uploads**: File upload and media management.
- **Settings**: Global and user settings.
- **Utilities**: Country codes, currency utils.

## 🚀 Running

```bash
# All API tests
./dev.py test api

# Specific test file
./dev.py test api -k test_assets_prices
```
