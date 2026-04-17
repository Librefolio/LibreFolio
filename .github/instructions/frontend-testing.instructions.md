---
applyTo: "frontend/e2e/**"
---

# Frontend E2E Testing (Playwright)

## Structure

```text
frontend/e2e/
├── fixtures/               # Shared helpers
│   ├── auth-helpers.ts     # login(), logout(), setLanguage(), navigateTo()
│   ├── db-helpers.ts       # resetDatabase(), populateDatabase()
│   ├── test-users.ts       # TEST_USER, TEST_ADMIN
│   └── i18n-data.ts        # Expected translation data
├── auth.spec.ts
├── settings.spec.ts
├── files.spec.ts
├── gallery.spec.ts         # Auto screenshots for docs
├── fx/                     # FX-specific tests
├── assets/                 # Asset-specific tests
└── brokers/                # Broker-specific tests
```

## Run Commands

```bash
./dev.py test front-utility all     # auth, settings, files
./dev.py test front-user all        # brokers, sharing
./dev.py test front-fx all          # FX tests
./dev.py test front-asset all       # Asset tests
./dev.py test all-frontend          # All frontend categories
```

See skill `testing-frontend` for full details on patterns, fixtures, gallery, and coverage pipeline.

## Conventions

- **Always use `data-testid`** — never CSS classes or text (fragile with i18n)
- **Explicit timeouts**: `{timeout: N}` on expect/waitFor
- **Graceful skip**: `test.skip()` with message when data is missing
- **Mobile awareness**: handle hamburger menu with `openMobileMenu()`
- **Login via helper**: always use `login()` from `auth-helpers.ts`

## Playwright Config

- 2 projects: `desktop` (1280×720) + `mobile` (iPhone 14 Pro Max viewport)
- Both use Chromium (WebKit has stability issues on Linux)
- Workers: 1 (sequential — shared DB state)
- Web Server auto-start: `./dev.py server --test --force`

