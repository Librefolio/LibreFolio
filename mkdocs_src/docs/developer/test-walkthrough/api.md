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
- **Assets**: Create, read, update, delete assets via API.
- **Transactions**: Import and manage transactions.

## 🚀 Running

```bash
./dev.py test api
```
