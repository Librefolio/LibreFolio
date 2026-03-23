# 💱 Front-FX Tests

Frontend E2E and unit tests for the FX (Foreign Exchange) module.

## 🔍 What's Tested

The FX module has the most extensive frontend test coverage, with 7 Playwright spec files:

| Test Suite | Description |
|------------|-------------|
| **FX List** | Currency pair list page, filtering, sync-all button |
| **FX Detail** | Detail page chart, data view, measure/signal panels |
| **Add Pair** | Add-pair modal, currency search, route selection |
| **Data Editor** | Inline rate editing, delete, date picker |
| **Sync** | Individual pair sync, provider fallback |
| **FX API** | Backend API integration (rates, routes, providers) |
| **FX Settings** | Chart settings, signal configuration, benchmarks |

## 🚀 Running

```bash
# Run all front-fx tests
./dev.py test front-fx all

# List available tests
./dev.py test front-fx --list

# Run a specific test file
./dev.py test front-fx fx-detail

# Run with Playwright UI mode (interactive)
./dev.py test front-fx all --ui
```

## 📂 Test Location

```
frontend/e2e/
├── fx-list.spec.ts       # FX pair list page
├── fx-detail.spec.ts     # FX detail chart & data
├── fx-add-pair.spec.ts   # Add pair modal
├── fx-editor.spec.ts     # Data editor inline editing
├── fx-sync.spec.ts       # Sync operations
├── fx-api.spec.ts        # Backend API calls
└── fx-settings.spec.ts   # Chart settings & signals
```

