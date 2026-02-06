# LibreFolio Frontend

SvelteKit frontend for LibreFolio - self-hosted portfolio tracker.

## Tech Stack

- **SvelteKit 2.x** - Framework
- **Tailwind CSS 4.x** - Styling (configured via `@theme` in CSS)
- **TypeScript** - Type safety
- **Playwright** - E2E testing

## Development

```bash
# From project root, use dev.py:
./dev.py front dev      # Start dev server with HMR (port 5173)
./dev.py front build    # Build for production
./dev.py front check    # TypeScript check
./dev.py front preview  # Preview production build

# Or directly with npm:
cd frontend
npm run dev
npm run build
npm run check
```

## E2E Testing with Playwright

Tests are in `frontend/e2e/` and run against the backend in test mode.

### Running Tests

```bash
# From project root:
./dev.py test front auth       # Run auth tests (headless)
./dev.py test front all        # Run all tests (excludes gallery)
./dev.py test front auth --ui  # Interactive Playwright UI
./dev.py test front auth --headed  # See browser window
./dev.py test front auth --debug   # Step-by-step debugging with Inspector

# Generate documentation screenshots:
./dev.py mkdocs gallery
```

### Filtering Tests by Name (TEST_NAMES)

You can filter tests using the test description text (from `test('...')` or `test.describe('...')`):

```bash
# Run only tests matching "login" in auth.spec.ts
./dev.py test front auth "login"

# Run tests matching multiple patterns (OR logic)
./dev.py test front auth "login" "logout"

# Run only "invalid credentials" test
./dev.py test front auth "invalid credentials"

# Works with --headed or --debug
./dev.py test front auth "login page" --headed
```

The filter matches against test descriptions:

- `test('login page renders correctly', ...)` → matches "login" or "renders"
- `test.describe('Authentication', ...)` → matches "Authentication"

### Test Structure

```
frontend/e2e/
├── fixtures/
│   ├── test-users.ts      # Test credentials
│   ├── auth-helpers.ts    # Login/logout/navigation helpers
│   └── db-helpers.ts      # Database reset helpers
├── auth.spec.ts           # Login, register, logout
├── settings.spec.ts       # User/global settings
├── files.spec.ts          # Files page
├── brokers.spec.ts        # Broker CRUD
├── multi-user.spec.ts     # Data isolation tests
└── gallery.spec.ts        # Screenshot generator (not in 'all')
```

### Writing Tests

Tests use Playwright's `test` and `expect` APIs:

```typescript
import { test, expect } from '@playwright/test';
import { login } from './fixtures/auth-helpers';
import { TEST_USER } from './fixtures/test-users';

test('example test', async ({ page }) => {
    await login(page, TEST_USER);
    await expect(page).toHaveURL(/.*dashboard.*/);
});
```

### Required data-testid Attributes

Components must include these `data-testid` for tests to work:

- `user-menu` - User dropdown menu
- `language-selector` - Language switcher
- `mobile-menu-toggle` - Hamburger menu button
- `broker-card` - Broker card in list
- `locale-preference` - Locale select in settings
- `currency-preference` - Currency select in settings
- `file-drop-zone` - File upload area

## Building for Production

```bash
./dev.py front build
```

The build output goes to `frontend/build/` and is served by FastAPI in production.
