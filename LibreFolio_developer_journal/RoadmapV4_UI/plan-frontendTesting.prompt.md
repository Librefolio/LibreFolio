# Plan: Frontend Testing Infrastructure

Piano per implementare test automatici frontend per no-regression testing.

## Obiettivo

Implementare una suite di test automatici per il frontend che:

- Verifica il corretto rendering dei componenti
- Testa le interazioni utente (click, input, form submission)
- Previene regressioni durante lo sviluppo
- Si integra con `test_runner.py` per esecuzione CI/CD

**NOTA**: Questi test sono automatici, non richiedono intervento manuale o AI agent.
L'AI agent usa Playwright MCP durante lo sviluppo, ma i test di regression sono headless e automatizzati.

---

## Architettura Test

### Approccio Ibrido: Vitest + Playwright

```
frontend/
├── src/
│   └── lib/components/
│       └── ui/
│           ├── LazyImage.svelte
│           └── LazyImage.test.ts     # Unit test Vitest
├── tests/
│   ├── unit/                         # Vitest - test veloci
│   │   ├── components/
│   │   │   ├── LazyImage.test.ts
│   │   │   ├── Tooltip.test.ts
│   │   │   └── FuzzySelect.test.ts
│   │   └── api/
│   │       └── client.test.ts        # Test API client generato
│   └── e2e/                          # Playwright - test browser
│       ├── auth.spec.ts              # Login/Register flow
│       ├── brokers.spec.ts           # CRUD broker
│       ├── settings.spec.ts          # Settings pages
│       └── responsive.spec.ts        # Mobile/tablet views
├── vitest.config.ts
├── playwright.config.ts
└── package.json                      # + scripts test
```

---

## Step 1: Setup Dipendenze

### package.json additions

```json
{
  "devDependencies": {
    "@testing-library/svelte": "^5.0.0",
    "@testing-library/jest-dom": "^6.0.0",
    "vitest": "^2.0.0",
    "jsdom": "^25.0.0",
    "@playwright/test": "^1.48.0"
  },
  "scripts": {
    "test:unit": "vitest run",
    "test:unit:watch": "vitest",
    "test:e2e": "playwright test",
    "test:e2e:ui": "playwright test --ui",
    "test": "npm run test:unit && npm run test:e2e"
  }
}
```

---

## Step 2: Configurazione Vitest

### frontend/vitest.config.ts

```typescript
import { defineConfig } from 'vitest/config';
import { svelte } from '@sveltejs/vite-plugin-svelte';

export default defineConfig({
  plugins: [svelte({ hot: !process.env.VITEST })],
  test: {
    include: ['src/**/*.test.ts', 'tests/unit/**/*.test.ts'],
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./tests/setup.ts'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'html'],
      include: ['src/lib/**/*.svelte', 'src/lib/**/*.ts'],
    },
  },
  resolve: {
    alias: {
      $lib: '/src/lib',
      $app: '/src/app-mocks', // Mock SvelteKit runtime
    },
  },
});
```

### frontend/tests/setup.ts

```typescript
import '@testing-library/jest-dom/vitest';
import { vi } from 'vitest';

// Mock fetch for API tests
global.fetch = vi.fn();

// Mock SvelteKit navigation
vi.mock('$app/navigation', () => ({
  goto: vi.fn(),
  invalidate: vi.fn(),
}));

// Mock SvelteKit stores
vi.mock('$app/stores', () => ({
  page: { subscribe: vi.fn() },
}));
```

---

## Step 3: Configurazione Playwright

[//]: # (TODO: prendere le configurazioni per il server di test da .env)

### frontend/playwright.config.ts

```typescript
import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './tests/e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: 'html',
  
  use: {
    baseURL: 'http://localhost:8000',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },

  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'mobile',
      use: { ...devices['iPhone 13'] },
    },
  ],

  // Avvia backend prima dei test
  webServer: {
    command: 'cd .. && ./dev.sh server:test',
    url: 'http://localhost:8001/api/v1/system/health',
    reuseExistingServer: !process.env.CI,
    timeout: 120 * 1000,
  },
});
```

---

## Step 4: Test Unit Esempio

### frontend/tests/unit/components/LazyImage.test.ts

```typescript
import { render, screen, waitFor } from '@testing-library/svelte';
import { describe, it, expect, vi } from 'vitest';
import LazyImage from '$lib/components/ui/LazyImage.svelte';

describe('LazyImage', () => {
  it('renders placeholder initially', () => {
    render(LazyImage, {
      props: { src: 'https://example.com/image.png', alt: 'Test' }
    });
    
    expect(screen.getByTestId('lazy-placeholder')).toBeInTheDocument();
  });

  it('shows image after load', async () => {
    render(LazyImage, {
      props: { src: 'https://example.com/image.png', alt: 'Test' }
    });
    
    // Simula load dell'immagine
    const img = screen.getByRole('img', { hidden: true });
    img.dispatchEvent(new Event('load'));
    
    await waitFor(() => {
      expect(screen.queryByTestId('lazy-placeholder')).not.toBeInTheDocument();
    });
  });

  it('shows fallback on error', async () => {
    render(LazyImage, {
      props: { src: 'invalid-url', alt: 'Test', fallback: '/fallback.png' }
    });
    
    const img = screen.getByRole('img', { hidden: true });
    img.dispatchEvent(new Event('error'));
    
    await waitFor(() => {
      expect(img).toHaveAttribute('src', '/fallback.png');
    });
  });
});
```

### frontend/tests/unit/components/FuzzySelect.test.ts

```typescript
import { render, screen, fireEvent } from '@testing-library/svelte';
import { describe, it, expect } from 'vitest';
import FuzzySelect from '$lib/components/ui/FuzzySelect.svelte';

describe('FuzzySelect', () => {
  const mockOptions = [
    { code: 'EUR', name: 'Euro', symbol: '€' },
    { code: 'USD', name: 'US Dollar', symbol: '$' },
    { code: 'GBP', name: 'British Pound', symbol: '£' },
  ];

  it('renders search input', () => {
    render(FuzzySelect, { props: { options: mockOptions } });
    expect(screen.getByRole('textbox')).toBeInTheDocument();
  });

  it('filters options on search', async () => {
    render(FuzzySelect, { props: { options: mockOptions } });
    
    const input = screen.getByRole('textbox');
    await fireEvent.input(input, { target: { value: 'euro' } });
    
    expect(screen.getByText('Euro')).toBeInTheDocument();
    expect(screen.queryByText('US Dollar')).not.toBeInTheDocument();
  });

  it('selects option on click', async () => {
    const { component } = render(FuzzySelect, { props: { options: mockOptions } });
    
    let selectedValue = null;
    component.$on('select', (e) => { selectedValue = e.detail; });
    
    const input = screen.getByRole('textbox');
    await fireEvent.focus(input);
    await fireEvent.click(screen.getByText('Euro'));
    
    expect(selectedValue).toEqual(mockOptions[0]);
  });
});
```

---

## Step 5: Test E2E Esempio

### frontend/tests/e2e/auth.spec.ts

```typescript
import { test, expect } from '@playwright/test';

test.describe('Authentication', () => {
  test('login page renders correctly', async ({ page }) => {
    await page.goto('/');
    
    await expect(page.getByRole('heading', { name: /login/i })).toBeVisible();
    await expect(page.getByPlaceholder(/username/i)).toBeVisible();
    await expect(page.getByPlaceholder(/password/i)).toBeVisible();
  });

  test('successful login redirects to dashboard', async ({ page }) => {
    await page.goto('/');
    
    await page.fill('[placeholder*="username" i]', 'testuser');
    await page.fill('[placeholder*="password" i]', 'TestPass123!');
    await page.click('button[type="submit"]');
    
    await expect(page).toHaveURL(/.*dashboard.*/);
  });

  test('invalid credentials show error', async ({ page }) => {
    await page.goto('/');
    
    await page.fill('[placeholder*="username" i]', 'wronguser');
    await page.fill('[placeholder*="password" i]', 'wrongpass');
    await page.click('button[type="submit"]');
    
    await expect(page.getByText(/invalid|incorrect/i)).toBeVisible();
  });

  test('language selector changes UI language', async ({ page }) => {
    await page.goto('/');
    
    // Click language selector
    await page.click('[data-testid="language-selector"]');
    await page.click('text=Italiano');
    
    // Verify Italian text
    await expect(page.getByRole('heading', { name: /accedi/i })).toBeVisible();
  });
});
```

### frontend/tests/e2e/brokers.spec.ts

```typescript
import { test, expect } from '@playwright/test';

test.describe('Brokers Management', () => {
  test.beforeEach(async ({ page }) => {
    // Login before each test
    await page.goto('/');
    await page.fill('[placeholder*="username" i]', 'testadmin');
    await page.fill('[placeholder*="password" i]', 'TestPass123!');
    await page.click('button[type="submit"]');
    await page.waitForURL(/.*dashboard.*/);
  });

  test('can create new broker', async ({ page }) => {
    await page.goto('/brokers');
    
    await page.click('button:has-text("Add Broker")');
    await page.fill('[name="name"]', 'Test Broker');
    await page.fill('[name="portal_url"]', 'https://test.com');
    await page.click('button:has-text("Create")');
    
    await expect(page.getByText('Test Broker')).toBeVisible();
  });

  test('can edit broker', async ({ page }) => {
    await page.goto('/brokers');
    
    // Click edit on first broker
    await page.click('[data-testid="broker-card"]:first-child [data-testid="edit-btn"]');
    await page.fill('[name="name"]', 'Updated Broker Name');
    await page.click('button:has-text("Save")');
    
    await expect(page.getByText('Updated Broker Name')).toBeVisible();
  });

  test('can delete broker', async ({ page }) => {
    await page.goto('/brokers');
    
    const brokerName = await page.textContent('[data-testid="broker-card"]:first-child .broker-name');
    
    await page.click('[data-testid="broker-card"]:first-child [data-testid="delete-btn"]');
    await page.click('button:has-text("Confirm")');
    
    await expect(page.getByText(brokerName!)).not.toBeVisible();
  });
});
```

---

## Step 6: Integrazione test_runner.py

### Aggiungere a test_runner.py

[//]: # TODO: il frontend sarà una nuova categoria, e le varie pagine le action

[//]: # TODO: oltre la categoria del frontend ci sarà anche quella del UX (user experience), che coinsterà in prove sull'interfaccia dei vari path di lavoro.

```python
# ============================================================================
# FRONTEND TESTS
# ============================================================================

def frontend_unit(verbose: bool = False) -> bool:
    """Run frontend Vitest unit tests."""
    print_section("Frontend Unit Tests")
    print_info("Testing Svelte components with Vitest + Testing Library")
    print_info("No backend server required")
    
    cmd = ["npm", "run", "test:unit"]
    return run_command(cmd, "Frontend unit tests", verbose=verbose, cwd="frontend")


def frontend_e2e(verbose: bool = False) -> bool:
    """Run frontend Playwright E2E tests."""
    print_section("Frontend E2E Tests")
    print_info("Testing full user flows with Playwright")
    print_info("Backend server will be started automatically")
    
    cmd = ["npm", "run", "test:e2e"]
    return run_command(cmd, "Frontend E2E tests", verbose=verbose, cwd="frontend")


def frontend_all(verbose: bool = False) -> bool:
    """Run all frontend tests."""
    return _run_test_suite(
        suite_name="Frontend Tests",
        tests=[
            ("Unit Tests (Vitest)", lambda: frontend_unit(verbose)),
            ("E2E Tests (Playwright)", lambda: frontend_e2e(verbose)),
        ],
        verbose=verbose,
        info_msgs=[
            "Testing frontend components and user flows",
            "Unit tests run in jsdom, E2E tests in real browsers",
        ],
    )
```

### Aggiungere alla suite completa

```python
def run_all_tests(verbose: bool = False) -> bool:
    return _run_test_suite(
        suite_name="Complete Test Suite",
        tests=[
            # ... existing tests ...
            ("Frontend Tests", lambda: frontend_all(verbose)),  # NEW
        ],
        # ...
    )
```

---

## Step 7: Test da Scrivere (Priorità)

### Unit Tests (Vitest)

| Componente              | Test Cases                                                    |
|-------------------------|---------------------------------------------------------------|
| LazyImage.svelte        | placeholder, load success, error fallback, skeleton animation |
| Tooltip.svelte          | hover show, click outside close, position auto-adjust         |
| FuzzySelect.svelte      | search filter, selection, keyboard navigation                 |
| ImageUploader.svelte    | drag&drop, file picker, resize preview                        |
| PasswordStrength.svelte | weak/medium/strong indicators, requirements checklist         |
| ThemeToggle.svelte      | toggle state, localStorage persistence                        |

### E2E Tests (Playwright)

| Flow       | Test Cases                                               |
|------------|----------------------------------------------------------|
| Auth       | login, register, logout, password change, session expire |
| Brokers    | create, edit, delete, access management                  |
| Settings   | user preferences, global settings (admin only)           |
| Responsive | mobile menu, tablet layout, touch interactions           |
| i18n       | language change, persistent preference                   |

---

## Esecuzione

```bash
# Frontend unit tests
./dev.sh test frontend unit

# Frontend E2E tests
./dev.sh test frontend e2e

# Tutti i test frontend
./dev.sh test frontend all

# Test completi (incluso frontend)
./dev.sh test all
```

---

## Note Implementative

1. **data-testid**: Aggiungere attributi `data-testid` ai componenti per selettori stabili
2. **Mock API**: Per unit test, mockare le chiamate API con risposte predefinite
3. **Test Database**: E2E usa `server:test` (porta 8001, test_app.db)
4. **Parallelismo**: Vitest parallelo, Playwright sequenziale (condividono stato server)
5. **CI/CD**: Configurare GitHub Actions per eseguire test su ogni PR

---

## Risorse Esistenti da Analizzare

Prima di implementare, verificare:

- [ ] `frontend/src/lib/components/` - componenti esistenti da testare
- [ ] `frontend/src/routes/` - pagine per E2E tests
- [ ] `frontend/src/lib/api/` - client API generato da testare
- [ ] `backend/test_scripts/test_api/` - pattern test esistenti da seguire

