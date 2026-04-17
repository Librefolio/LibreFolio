---
name: testing-frontend
description: "Use this skill when creating, modifying, or running Playwright E2E tests for the frontend, including gallery screenshot generation, test fixtures, and backend coverage tracking during E2E tests."
---

# Frontend Testing Reference (Playwright E2E)

## Test Structure

```text
frontend/
├── e2e/                        # 181+ Playwright E2E tests
│   ├── fixtures/               # Shared helpers
│   │   ├── auth-helpers.ts     # login(), logout(), setLanguage(), navigateTo()
│   │   ├── db-helpers.ts       # resetDatabase(), populateDatabase()
│   │   ├── test-users.ts       # TEST_USER, TEST_ADMIN, TEST_USER_2
│   │   └── i18n-data.ts        # Expected translation data for i18n tests
│   ├── auth.spec.ts            # Login, register, logout
│   ├── settings.spec.ts        # User & global settings
│   ├── files.spec.ts           # File management
│   ├── gallery.spec.ts         # Automatic screenshots for docs
│   ├── fx/                     # FX-specific tests
│   ├── assets/                 # Asset-specific tests
│   └── brokers/                # Broker-specific tests
├── playwright.config.ts        # Config (2 projects: desktop + mobile)
└── playwright-report/          # Generated HTML report
```

## How to Run

```bash
# Frontend test categories (via dev.py)
./dev.py test front-utility all     # auth, settings, files, select, image-crop
./dev.py test front-user all        # brokers, multi-user, sharing
./dev.py test front-fx all          # unit (Vitest) + E2E fx
./dev.py test front-asset all       # list, detail, modal, data-editor

# Single sub-category
./dev.py test front-fx fx-list
./dev.py test front-asset asset-detail

# With interactive UI
./dev.py test front-fx fx-list --ui

# With visible browser
./dev.py test front-fx fx-list --headed

# With backend coverage tracking
./dev.py test --coverage front-fx all

# Gallery screenshots
./dev.py mkdocs gallery
./dev.py mkdocs gallery --desktop-only
./dev.py mkdocs gallery -f "assets"
./dev.py mkdocs gallery -l              # list available tests
```

## Playwright Config

- **2 projects**: `desktop` (1280×720, Chrome) + `mobile` (iPhone 14 Pro Max viewport, Chromium)
- **Workers**: 1 (sequential — shared DB state)
- **Timeout**: 30s per test, 3s per assertion
- **Web Server auto-start**: `./dev.py server --test --force` (port 8001)
- **Retry**: 0 local, 2 in CI

## Fixtures

```typescript
import {login, logout, setLanguage, navigateTo} from '../fixtures/auth-helpers';
import {resetDatabase, populateDatabase} from '../fixtures/db-helpers';
import {TEST_USER, TEST_ADMIN} from '../fixtures/test-users';

await login(page);                    // Login with default TEST_USER
await login(page, TEST_ADMIN);        // Login as admin
await setLanguage(page, 'it');        // Change language
await resetDatabase();                // Full reset (create-clean + populate)
```

## How to Create a Test

### Base Pattern

```typescript
import {test, expect} from '@playwright/test';
import {login} from '../fixtures/auth-helpers';

test.describe('Feature Name', () => {
    test.beforeEach(async ({page}) => {
        await login(page);
    });

    test('should do something', async ({page}) => {
        await page.goto('/assets');
        await expect(page.getByTestId('assets-page')).toBeVisible({timeout: 10_000});
        await page.getByTestId('some-button').click();
        await expect(page.getByTestId('result-element')).toContainText('Expected');
    });
});
```

### Graceful Skip (when data missing)

```typescript
test('should edit data', async ({page}) => {
    const btn = page.getByTestId('edit-button');
    if (!await btn.isVisible({timeout: 5000}).catch(() => false)) {
        test.skip(true, 'Edit button not available (no data in test DB)');
        return;
    }
    // ... rest of test
});
```

## Backend Coverage during E2E

The SIGTERM chain: Playwright `gracefulShutdown` → `exec` in shell → `os.execvpe()` in dev.py → `coverage run -m uvicorn`. All exec calls replace the process so SIGTERM reaches `coverage run` which writes `.coverage.*`.

Key files:
- `playwright.config.ts`: `gracefulShutdown: {signal: 'SIGTERM', timeout: 5000}`
- `dev.py` (cmd_server): `os.execvpe()` in coverage mode
- `.coveragerc`: `sigterm = true`, `parallel = true`

## Conventions

- **`data-testid` always**: never select by CSS class or text (fragile with i18n)
- **Explicit timeouts**: use `{timeout: N}` on expect/waitFor
- **Graceful skip**: if a test depends on mock data, use `test.skip()` with clear message
- **Mobile awareness**: handle hamburger menu with `openMobileMenu()`
- **No hardcoded login**: always use `login()` from `auth-helpers.ts`

