# 🎭 Frontend Tests Overview (Playwright)

LibreFolio's frontend tests use **[Playwright](https://playwright.dev/)** to drive a real browser and interact with the application exactly as a user would.

## 🧰 Tools & Framework

| Tool | Role |
|------|------|
| **Playwright** | Browser automation engine (Chromium, headless by default) |
| **`@playwright/test`** | Test runner with `test()`, `expect()`, fixtures |
| **`page`** | Playwright's page fixture — represents a browser tab |
| **`expect`** | Assertion library with auto-retry and web-first semantics |

### ⚙️ How Tests Work

Each test file (`.spec.ts`) contains scenarios that:

1. Navigate to a URL (`page.goto('/fx')`)
2. Interact with elements (`page.click()`, `page.fill()`, `page.getByRole()`)
3. Assert outcomes (`expect(page.getByText('EUR/USD')).toBeVisible()`)

Playwright automatically waits for elements and retries assertions, making tests resilient to timing issues.

```typescript
// Example: verify broker creation
test('create a new broker', async ({ page }) => {
    await page.goto('/brokers');
    await page.getByRole('button', { name: 'New Broker' }).click();
    await page.getByLabel('Name').fill('My Broker');
    await page.getByRole('button', { name: 'Save' }).click();
    await expect(page.getByText('My Broker')).toBeVisible();
});
```

---

## 🤖 Automated Setup

When you run a frontend test category, everything the Playwright specs need is prepared for you (the
category's Vitest files need none of it):

- **Builds the frontend, when needed** — `front build`, which syncs the API client before building, runs only when there is no build yet, when the frontend sources, its configuration or the Tool codegen inputs changed since the last build, or when the existing build is not of the kind needed: instrumented for JS coverage or plain, and a debug build for `dev.py server --test`. The runner checks before the specs, the test backend when it starts.
- **Uses a test backend** — `dev.py server --test`, serving the API and the built frontend on the run's test port. By default it is the shared backend the runner starts once for the whole invocation; with `--no-shared-server`, Playwright's `webServer` starts its own for each Playwright run.
- **Prepares the test data** — repopulates the test database with mock data and creates the E2E users, in the runner or in Playwright's `globalSetup`.
- **Runs Playwright** — executes the specs against the live application at `http://localhost:<test port>`: `6041` unless `--test-port` or `TEST_PORT` says otherwise.
- **Tears down** — stops the backend it started: the shared one at the end of the invocation, Playwright's own at the end of its run.

!!! info "Test isolation"

    The test backend works on the run's test data root: `backend/data/test/` in the checkout unless
    `--data-dir` or `LIBREFOLIO_TEST_DATA_DIR` says otherwise, with the database in `sqlite/app.db`
    under it. The runner refuses a test data root that overlaps the production data, so your
    production data is never touched. See [Isolated Runtime Lanes](index.md#isolated-runtime-lanes).

---

## 🏁 Flags

Every frontend test category — `front-utility`, `front-broker`, `front-user`, `front-fx`,
`front-asset`, `front-transaction`, `front-portfolio`, `front-ai-export` — supports these flags.
`--headed`, `--debug`, `--ui` and `--list` follow the category (`./dev.py test front-fx all --headed`);
`--coverage` belongs to `./dev.py test` and comes before it (`./dev.py test --coverage js front-fx all`).

| Flag | Effect | When to Use |
|------|--------|-------------|
| `--headed` | Opens a visible browser window instead of headless | Watch the test flow visually, debug layout issues |
| `--debug` | Runs headed with the **Playwright Inspector** (`PWDEBUG=1`), which pauses the test so you can step through its actions | Step through actions one by one, inspect selectors, set breakpoints |
| `--ui` | Opens **Playwright UI Mode** — a full interactive test runner | Explore tests interactively, view timeline/trace, re-run selectively |
| `--list` | Lists the category's Playwright spec files and the test titles they declare, without running anything (`all` for the whole category, an action name for its specs only) | Discover tests, verify naming, plan what to run |
| `--coverage [py\|js\|all]` | Tracks Python and/or JS coverage: the backend's Python while the E2E tests drive it, the frontend's JS in the browser and in the category's Vitest files | `py` → `htmlcov-backend-e2e/`, `js` → `frontend/coverage-js/` (`e2e/`, `unit-combined/`, and `combined/` when both ran), `all` (default) → both |

!!! tip "E2E runs are the only ones that measure both languages"

    A Playwright run exercises the frontend in the browser *and* the backend over
    HTTP, so it is the only suite where `--coverage all` produces two reports. See
    [Coverage Model](coverage-model.md).

### 🎨 Playwright UI Mode (`--ui`)

The UI mode provides a rich interactive experience:

- **Timeline view** — See every action (click, fill, navigate) on a visual timeline
- **DOM snapshot** — Inspect the page state at any point during the test
- **Network tab** — Monitor API calls and responses
- **Re-run** — Click to re-run a single test or a filtered subset
- **Filter** — Filter by file name, test title, or `describe` block

```bash
# Open UI mode for FX tests
./dev.py test front-fx all --ui
```

---

## 📋 Test Categories

| Category | Command | What's Tested |
|----------|---------|---------------|
| **[Front-Utility](front-utility.md)** | `./dev.py test front-utility all` | Auth, settings, files, select, image crop, onboarding, layout, scheduler (Playwright) + core and component units (Vitest) |
| **Front-Broker** | `./dev.py test front-broker all` | Broker list, CRUD, detail page, deletion recovery (Playwright) + broker helpers (Vitest) |
| **[Front-User](front-user.md)** | `./dev.py test front-user all` | Multi-user isolation, broker sharing (Playwright) + auth and client-session stores (Vitest) |
| **[Front-FX](front-fx.md)** | `./dev.py test front-fx all` | FX list, detail, add-pair, editor, CSV import, sync, bulk actions (Playwright) + EditBuffer, TimeSeriesStore, fxStoreRegistry (Vitest) |
| **Front-Asset** | `./dev.py test front-asset all` | Asset list, detail, modal, data editor, merge, classification (Playwright) + price store, chart aggregation (Vitest) |
| **Front-Transaction** | `./dev.py test front-transaction all` | Transaction modals, table, bulk operations, WAC, import wizard (Playwright) + payload and commit helpers (Vitest) |
| **Front-Portfolio** | `./dev.py test front-portfolio all` | Dashboard charts, banners, page cache, privacy masking, risk analysis (Playwright) + portfolio and risk stores (Vitest) |
| **Front-AI-Export** | `./dev.py test front-ai-export all` | AI Export panel, catalog, session memory, contracts (Playwright) + AI Export and signal units (Vitest) |

The categories without a walkthrough page list their actions with `./dev.py test <category> -h`.

