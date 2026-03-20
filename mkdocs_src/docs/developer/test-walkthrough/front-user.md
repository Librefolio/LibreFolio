# 👥 Front-User Tests

Frontend E2E tests for user-facing broker and multi-user features.

## 🔍 What's Tested

These Playwright tests cover the broker management UI and multi-user collaboration features:

| Test Suite | Description |
|------------|-------------|
| **Brokers** | Broker CRUD (create, edit, delete), broker list, broker detail page |
| **Multi-User** | Multiple user accounts, visibility rules, data isolation |
| **Sharing** | Broker sharing modal, RBAC roles (Owner, Editor, Viewer), share percentage |

## 🚀 Running

```bash
# Run all front-user tests
./dev.py test front-user all

# List available tests
./dev.py test front-user --list

# Run a specific test file
./dev.py test front-user brokers

# Run with visible browser
./dev.py test front-user all --headed
```

## 📂 Test Location

```
frontend/e2e/
├── brokers.spec.ts       # Broker CRUD operations
├── multi-user.spec.ts    # Multi-user scenarios
└── sharing.spec.ts       # Broker sharing & RBAC
```

