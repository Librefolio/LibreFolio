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
- **AI Export API**: Runtime catalog, versioned snapshots, authorization,
  applicability, typed problems, and cross-domain request contracts.

## 🧠 AI Export Test Stack

AI Export spans API, service, probe, frontend unit, and live Playwright layers:

```bash
# Catalog, snapshots, authorization, typed API problems
./dev.py test api ai-export

# Backend components, datasets, analyses, sampling, runtime, and composition
./dev.py test services ai-export

# Real-prompt probe orchestration and metrics
./dev.py test utils ai-export-probe

# Frontend runtime, renderer, clipboard, memory, and Signal unit tests
./dev.py test front-ai-export unit

# Focused live UI concerns
./dev.py test front-ai-export panel
./dev.py test front-ai-export catalog
./dev.py test front-ai-export memory
./dev.py test front-ai-export contract

# Compatibility alias for all four Playwright concerns
./dev.py test front-ai-export cutover

# Canonical frontend AI Export gate: unit + Playwright
./dev.py test front-ai-export all
```

## 🚀 Running

```bash
# All API tests
./dev.py test api all

# AI Export API only
./dev.py test api ai-export
```
