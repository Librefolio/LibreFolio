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

When you run a frontend test category, `dev.py` handles everything automatically:

1. **Builds the frontend** — Runs `front build` to produce a production build
2. **Starts the backend** — Launches the FastAPI server in `--test` mode (isolated test database at `backend/data/test/`)
3. **Serves the frontend** — The backend serves the built frontend at `http://localhost:8001`
4. **Runs Playwright** — Executes the test specs against the live application
5. **Tears down** — Stops the server after tests complete

!!! info "Test isolation"

    Test mode uses a completely separate database (`backend/data/test/sqlite/app.db`). Your production data is never touched.

---

## 🏁 Flags

Frontend test categories (`front-utility`, `front-user`, `front-fx`) support these flags:

| Flag | Effect | When to Use |
|------|--------|-------------|
| `--headed` | Opens a visible browser window instead of headless | Watch the test flow visually, debug layout issues |
| `--debug` | Enables **Playwright Inspector** — pauses before each action | Step through actions one by one, inspect selectors, set breakpoints |
| `--ui` | Opens **Playwright UI Mode** — a full interactive test runner | Explore tests interactively, view timeline/trace, re-run selectively |
| `--list` | Lists available test files without running them | Discover tests, verify naming, plan what to run |
| `--coverage` | Tracks backend code coverage during E2E tests | Generate `htmlcov-frontend/` report |

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
| **[Front-Utility](front-utility.md)** | `./dev.py test front-utility all` | Auth, settings, files, select, image-crop |
| **[Front-User](front-user.md)** | `./dev.py test front-user all` | Brokers, multi-user, sharing |
| **[Front-FX](front-fx.md)** | `./dev.py test front-fx all` | FX list, detail, add-pair, editor, sync |

