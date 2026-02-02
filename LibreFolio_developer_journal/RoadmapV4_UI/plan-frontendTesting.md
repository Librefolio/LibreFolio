# Plan: Frontend Testing Infrastructure (v2)

**Data creazione**: Phase 1 (aggiornato 2 Febbraio 2026)  
**Status**: 📋 DA IMPLEMENTARE  
**Priorità**: P2  
**Stima**: 6-8h setup + ongoing test writing

---

## 🎯 Obiettivo

Implementare una suite di test E2E automatici per il frontend LibreFolio che:

1. **Verifica i flussi utente** con browser reale (Playwright su Chromium)
2. **Genera screenshot gallery multilingua** per documentazione mkdocs
3. **Previene regressioni** durante lo sviluppo
4. **Si integra con `test_runner.py`** come nuova categoria "front"
5. **Supporta test multi-utente** per verificare isolamento dati

**Approccio**: Solo Playwright E2E, no Vitest unit tests.  
**Coverage**: Solo backend (pytest-cov). Frontend testa funzionalità E2E.  
**Browser**: Chromium per ora (Safari/Firefox facili da aggiungere dopo).

---

## 📐 Architettura

```
LibreFolio/
├── .env                              # + PORT, TEST_PORT, etc. (da aggiornare)
├── .env.example                      # + stesse variabili
│
├── frontend/
│   ├── e2e/                          # Playwright test scripts
│   │   ├── fixtures/
│   │   │   ├── test-users.ts         # Credenziali utenti test
│   │   │   ├── auth-helpers.ts       # Login/logout helpers
│   │   │   └── db-helpers.ts         # Reset DB, populate
│   │   ├── auth.spec.ts              # Login/Register/Logout
│   │   ├── settings.spec.ts          # User/Global settings
│   │   ├── files.spec.ts             # Files page, URL filters
│   │   ├── brokers.spec.ts           # CRUD broker, import files
│   │   ├── multi-user.spec.ts        # Test isolamento multi-utente
│   │   └── gallery.spec.ts           # Screenshot generator (non in test all)
│   ├── playwright.config.ts
│   └── package.json
│
├── mkdocs_src/docs/gallery/          # Screenshot output per docs
│   ├── desktop/
│   │   └── {lang}/                   # en, it, fr, es
│   │       ├── auth/
│   │       │   ├── login.png
│   │       │   └── register-modal.png
│   │       ├── dashboard/
│   │       │   └── main.png
│   │       ├── settings/
│   │       │   ├── user-preferences.png
│   │       │   └── global-settings.png
│   │       ├── files/
│   │       │   ├── static-tab.png
│   │       │   └── brim-tab.png
│   │       └── brokers/
│   │           ├── list.png
│   │           ├── detail.png
│   │           └── import-modal.png
│   └── mobile/
│       └── {lang}/                   # Stessa struttura di desktop
│           ├── auth/
│           │   └── ...
│           └── ...
│
└── scripts/
    └── test_runner.py                # + categoria "front"
```

---

## 🔧 Step 0: Aggiornare .env

### .env (e .env.example)

Aggiungere le variabili mancanti da `config.py`:

```dotenv
# LibreFolio Configuration

# =============================================================================
# Database
# =============================================================================
DATABASE_URL=sqlite:///./backend/data/sqlite/app.db
TEST_DATABASE_URL=sqlite:///./backend/data/sqlite/test_app.db

# =============================================================================
# Server
# =============================================================================
PORT=8000
TEST_PORT=8001

# =============================================================================
# API
# =============================================================================
API_V1_PREFIX=/api/v1
PROJECT_NAME=LibreFolio
VERSION=0.1.0

# =============================================================================
# Logging
# =============================================================================
LOG_LEVEL=INFO

# =============================================================================
# Portfolio
# =============================================================================
PORTFOLIO_BASE_CURRENCY=EUR

# =============================================================================
# CORS (for frontend development)
# =============================================================================
BACKEND_CORS_ORIGINS=["http://localhost:3000", "http://localhost:5173"]
```

---

## 🔧 Step 1: Setup Playwright

### package.json additions

```json
{
  "devDependencies": {
    "@playwright/test": "^1.50.0"
  },
  "scripts": {
    "test:e2e": "playwright test",
    "test:e2e:ui": "playwright test --ui",
    "test:e2e:headed": "playwright test --headed",
    "test:e2e:debug": "playwright test --debug",
    "test:report": "playwright show-report"
  }
}
```

### playwright.config.ts

```typescript
import { defineConfig, devices } from '@playwright/test';
import * as dotenv from 'dotenv';
import * as path from 'path';

// Load .env from project root
dotenv.config({ path: path.resolve(__dirname, '../.env') });

const PORT = process.env.PORT || '8000';
const BASE_URL = `http://localhost:${PORT}`;

export default defineConfig({
    testDir: './e2e',
    fullyParallel: false,           // Test sequenziali (stato condiviso)
    forbidOnly: !!process.env.CI,
    retries: process.env.CI ? 2 : 0,
    workers: 1,
    reporter: [
        ['html', { outputFolder: 'playwright-report' }],
        ['list']
    ],
    
    timeout: 60000,
    expect: { timeout: 10000 },
    
    use: {
        baseURL: BASE_URL,
        trace: 'on-first-retry',
        screenshot: 'only-on-failure',
        video: 'on-first-retry',
        launchOptions: {
            slowMo: process.env.SLOWMO ? parseInt(process.env.SLOWMO) : 0,
        },
    },
    
    projects: [
        {
            name: 'desktop',
            use: { 
                ...devices['Desktop Chrome'],
                viewport: { width: 1920, height: 1080 },
            },
        },
        {
            name: 'mobile',
            use: { 
                ...devices['iPhone 14 Pro Max'],
                // viewport: { width: 430, height: 932 }  // già incluso nel device
            },
        },
    ],
    
    // Server avviato automaticamente in test mode
    webServer: {
        command: 'cd .. && ./dev.py server --test',
        url: `${BASE_URL}/api/v1/system/health`,
        reuseExistingServer: !process.env.CI,
        timeout: 120 * 1000,
    },
});
```

---

## 🔧 Step 2: Test Fixtures

### e2e/fixtures/test-users.ts

```typescript
/**
 * Test user credentials
 * These users are created by _ensure_test_users() in test_runner.py
 */

export const TEST_USER = {
    username: 'e2e_test_user',
    email: 'e2e@test.example.com',
    password: 'E2eTestPass123!',
};

export const TEST_ADMIN = {
    username: 'e2e_test_admin',
    email: 'e2eadmin@test.example.com',
    password: 'E2eAdminPass123!',
};

// Second user for multi-user tests
export const TEST_USER_2 = {
    username: 'e2e_test_user2',
    email: 'e2e2@test.example.com',
    password: 'E2eTestPass456!',
};

export const SUPPORTED_LANGUAGES = ['en', 'it', 'fr', 'es'] as const;
export type Language = typeof SUPPORTED_LANGUAGES[number];
```

### e2e/fixtures/auth-helpers.ts

```typescript
import { Page, expect } from '@playwright/test';
import { TEST_USER, type Language } from './test-users';

/**
 * Login as specified user
 */
export async function login(page: Page, user = TEST_USER) {
    await page.goto('/');
    
    // Wait for login form
    await expect(page.getByPlaceholder(/username|email/i)).toBeVisible();
    
    // Fill and submit
    await page.getByPlaceholder(/username|email/i).fill(user.username);
    await page.getByPlaceholder(/password/i).fill(user.password);
    await page.getByRole('button', { name: /login|sign in|accedi/i }).click();
    
    // Wait for dashboard
    await expect(page).toHaveURL(/.*dashboard.*/, { timeout: 10000 });
}

/**
 * Logout current user
 */
export async function logout(page: Page) {
    await page.getByTestId('user-menu').click();
    await page.getByRole('menuitem', { name: /logout|sign out|esci/i }).click();
    await expect(page).toHaveURL('/');
}

/**
 * Change UI language
 */
export async function setLanguage(page: Page, lang: Language) {
    await page.getByTestId('language-selector').click();
    const langNames: Record<Language, string> = {
        en: 'English',
        it: 'Italiano', 
        fr: 'Français',
        es: 'Español',
    };
    await page.getByText(langNames[lang]).click();
    await page.waitForTimeout(300); // Wait for i18n update
}

/**
 * Open mobile menu (burger) if on mobile viewport
 */
export async function openMobileMenu(page: Page) {
    const burger = page.getByTestId('mobile-menu-toggle');
    if (await burger.isVisible()) {
        await burger.click();
        await page.waitForTimeout(300); // Wait for animation
    }
}

/**
 * Navigate to a route, handling mobile menu if needed
 */
export async function navigateTo(page: Page, route: string, menuItem?: string) {
    // If menuItem provided, use sidebar navigation
    if (menuItem) {
        await openMobileMenu(page);
        await page.getByRole('link', { name: new RegExp(menuItem, 'i') }).click();
    } else {
        await page.goto(route);
    }
    await page.waitForLoadState('networkidle');
}
```

### e2e/fixtures/db-helpers.ts

```typescript
import { exec } from 'child_process';
import { promisify } from 'util';

const execAsync = promisify(exec);

/**
 * Reset test database to clean state with populate data
 */
export async function resetDatabase(): Promise<void> {
    console.log('[E2E] Resetting test database...');
    await execAsync('cd .. && ./dev.py db create-clean --test');
    await execAsync('cd .. && ./dev.py test db populate --force');
    console.log('[E2E] Database reset complete');
}

/**
 * Just run db populate (without full reset)
 */
export async function populateDatabase(): Promise<void> {
    console.log('[E2E] Populating test database...');
    await execAsync('cd .. && ./dev.py test db populate');
    console.log('[E2E] Database populated');
}
```

---

## 🔧 Step 3: Test Specs

### Ordine esecuzione test

I test sono ordinati per dipendenze crescenti:

1. **auth.spec.ts** - Login/register (base per tutto)
2. **settings.spec.ts** - Preferenze utente (richiede login)
3. **files.spec.ts** - Gestione file (richiede login)
4. **brokers.spec.ts** - CRUD broker (richiede login, può usare files)
5. **multi-user.spec.ts** - Isolamento dati (richiede 2 utenti)

### e2e/auth.spec.ts

```typescript
import { test, expect } from '@playwright/test';
import { login, logout, setLanguage } from './fixtures/auth-helpers';
import { TEST_USER, TEST_ADMIN, SUPPORTED_LANGUAGES } from './fixtures/test-users';

test.describe('Authentication', () => {
    
    test('login page renders correctly', async ({ page }) => {
        await page.goto('/');
        await expect(page.getByPlaceholder(/username|email/i)).toBeVisible();
        await expect(page.getByPlaceholder(/password/i)).toBeVisible();
        await expect(page.getByRole('button', { name: /login|sign in/i })).toBeVisible();
    });

    test('successful login redirects to dashboard', async ({ page }) => {
        await login(page, TEST_USER);
        await expect(page).toHaveURL(/.*dashboard.*/);
        await expect(page.getByRole('heading', { name: /dashboard/i })).toBeVisible();
    });

    test('invalid credentials show error', async ({ page }) => {
        await page.goto('/');
        await page.getByPlaceholder(/username|email/i).fill('wronguser');
        await page.getByPlaceholder(/password/i).fill('wrongpass');
        await page.getByRole('button', { name: /login|sign in/i }).click();
        await expect(page.getByText(/invalid|incorrect|failed|error/i)).toBeVisible();
    });

    test('logout returns to login page', async ({ page }) => {
        await login(page, TEST_USER);
        await logout(page);
        await expect(page.getByPlaceholder(/username|email/i)).toBeVisible();
    });

    test('language selector changes UI', async ({ page }) => {
        await page.goto('/');
        await setLanguage(page, 'it');
        await expect(page.getByRole('button', { name: /accedi/i })).toBeVisible();
    });

    test('admin can login', async ({ page }) => {
        await login(page, TEST_ADMIN);
        await expect(page).toHaveURL(/.*dashboard.*/);
    });
});
```

### e2e/brokers.spec.ts

```typescript
import { test, expect } from '@playwright/test';
import { login, navigateTo } from './fixtures/auth-helpers';
import { TEST_USER } from './fixtures/test-users';

test.describe('Brokers', () => {
    test.beforeEach(async ({ page }) => {
        await login(page, TEST_USER);
    });

    test('can view broker list', async ({ page }) => {
        await navigateTo(page, '/brokers');
        await expect(page.getByRole('heading', { name: /broker/i })).toBeVisible();
    });

    test('can create new broker', async ({ page }) => {
        await navigateTo(page, '/brokers');
        
        // Click add broker button
        await page.getByRole('button', { name: /add|create|new/i }).click();
        
        // Fill form
        const brokerName = `Test Broker ${Date.now()}`;
        await page.getByLabel(/name/i).fill(brokerName);
        await page.getByRole('button', { name: /save|create|confirm/i }).click();
        
        // Verify broker appears
        await expect(page.getByText(brokerName)).toBeVisible();
    });

    test('can view broker detail', async ({ page }) => {
        await navigateTo(page, '/brokers');
        
        // Click first broker card
        await page.getByTestId('broker-card').first().click();
        
        // Should show detail page
        await expect(page.getByText(/cash balance|holdings/i)).toBeVisible();
    });

    test('can open import files modal', async ({ page }) => {
        await navigateTo(page, '/brokers');
        await page.getByTestId('broker-card').first().click();
        
        // Click import files button
        await page.getByRole('button', { name: /import/i }).click();
        
        // Modal should open
        await expect(page.getByRole('dialog')).toBeVisible();
        await expect(page.getByText(/upload|carica/i)).toBeVisible();
    });
});
```

### e2e/multi-user.spec.ts

```typescript
import { test, expect, Browser, BrowserContext, Page } from '@playwright/test';
import { login } from './fixtures/auth-helpers';
import { TEST_USER, TEST_USER_2 } from './fixtures/test-users';

test.describe('Multi-User Isolation', () => {
    let browser: Browser;
    let context1: BrowserContext;
    let context2: BrowserContext;
    let page1: Page;
    let page2: Page;

    test.beforeAll(async ({ browser: b }) => {
        browser = b;
        // Create two separate browser contexts (like incognito windows)
        context1 = await browser.newContext();
        context2 = await browser.newContext();
        page1 = await context1.newPage();
        page2 = await context2.newPage();
    });

    test.afterAll(async () => {
        await context1.close();
        await context2.close();
    });

    test('user cannot see other user broker', async () => {
        // User 1 logs in and creates a broker
        await login(page1, TEST_USER);
        await page1.goto('/brokers');
        await page1.getByRole('button', { name: /add|create/i }).click();
        const brokerName = `Private Broker ${Date.now()}`;
        await page1.getByLabel(/name/i).fill(brokerName);
        await page1.getByRole('button', { name: /save|create/i }).click();
        await expect(page1.getByText(brokerName)).toBeVisible();

        // User 2 logs in - should NOT see the broker
        await login(page2, TEST_USER_2);
        await page2.goto('/brokers');
        await expect(page2.getByText(brokerName)).not.toBeVisible();
    });

    test('duplicate broker name fails for different users', async () => {
        const sharedName = `Shared Name Broker ${Date.now()}`;
        
        // User 1 creates broker
        await login(page1, TEST_USER);
        await page1.goto('/brokers');
        await page1.getByRole('button', { name: /add|create/i }).click();
        await page1.getByLabel(/name/i).fill(sharedName);
        await page1.getByRole('button', { name: /save|create/i }).click();
        await expect(page1.getByText(sharedName)).toBeVisible();

        // User 2 tries same name - should succeed (different user)
        // NOTE: This test verifies name uniqueness is per-user, not global
        await login(page2, TEST_USER_2);
        await page2.goto('/brokers');
        await page2.getByRole('button', { name: /add|create/i }).click();
        await page2.getByLabel(/name/i).fill(sharedName);
        await page2.getByRole('button', { name: /save|create/i }).click();
        
        // Should succeed - each user can have their own broker with same name
        await expect(page2.getByText(sharedName)).toBeVisible();
    });
});
```

---

## 🔧 Step 4: Gallery Screenshot Generator

### e2e/gallery.spec.ts

```typescript
/**
 * Gallery Screenshot Generator
 * 
 * Generates consistent screenshots for mkdocs documentation.
 * NOT included in normal test runs - run separately with:
 *   ./dev.py mkdocs gallery
 * 
 * Screenshots saved to: mkdocs_src/docs/gallery/{desktop|mobile}/{lang}/...
 */
import { test, Page } from '@playwright/test';
import { login, setLanguage, navigateTo, openMobileMenu } from './fixtures/auth-helpers';
import { TEST_USER, TEST_ADMIN, SUPPORTED_LANGUAGES, type Language } from './fixtures/test-users';
import * as path from 'path';
import * as fs from 'fs';

const GALLERY_ROOT = path.join(__dirname, '../../mkdocs_src/docs/gallery');

function ensureDir(dir: string) {
    if (!fs.existsSync(dir)) {
        fs.mkdirSync(dir, { recursive: true });
    }
}

function getGalleryPath(viewport: 'desktop' | 'mobile', lang: Language, category: string): string {
    return path.join(GALLERY_ROOT, viewport, lang, category);
}

async function screenshot(
    page: Page, 
    viewport: 'desktop' | 'mobile',
    lang: Language, 
    category: string, 
    name: string
) {
    const dir = getGalleryPath(viewport, lang, category);
    ensureDir(dir);
    await page.screenshot({ 
        path: path.join(dir, `${name}.png`),
        fullPage: false 
    });
    console.log(`  📸 ${viewport}/${lang}/${category}/${name}.png`);
}

// Helper to run for all languages
async function forEachLanguage(
    page: Page,
    callback: (lang: Language) => Promise<void>
) {
    for (const lang of SUPPORTED_LANGUAGES) {
        await setLanguage(page, lang);
        await callback(lang);
    }
}

// Determine viewport from project name
function getViewport(testInfo: any): 'desktop' | 'mobile' {
    return testInfo.project.name === 'mobile' ? 'mobile' : 'desktop';
}

test.describe('Gallery Screenshots', () => {
    
    test.describe('Auth Pages', () => {
        test('login page - all languages', async ({ page }, testInfo) => {
            const viewport = getViewport(testInfo);
            await page.goto('/');
            
            await forEachLanguage(page, async (lang) => {
                await page.waitForTimeout(300);
                await screenshot(page, viewport, lang, 'auth', 'login');
            });
        });

        test('register modal - all languages', async ({ page }, testInfo) => {
            const viewport = getViewport(testInfo);
            await page.goto('/');
            
            await forEachLanguage(page, async (lang) => {
                await page.getByRole('button', { name: /register|sign up|registrati/i }).click();
                await page.waitForTimeout(300);
                await screenshot(page, viewport, lang, 'auth', 'register-modal');
                // Close modal
                await page.keyboard.press('Escape');
            });
        });
    });

    test.describe('Dashboard', () => {
        test.beforeEach(async ({ page }) => {
            await login(page, TEST_USER);
        });

        test('main dashboard - all languages', async ({ page }, testInfo) => {
            const viewport = getViewport(testInfo);
            
            await forEachLanguage(page, async (lang) => {
                await page.goto('/dashboard');
                await page.waitForLoadState('networkidle');
                await screenshot(page, viewport, lang, 'dashboard', 'main');
            });
        });

        test('mobile menu open', async ({ page }, testInfo) => {
            if (testInfo.project.name !== 'mobile') {
                test.skip();
                return;
            }
            
            await forEachLanguage(page, async (lang) => {
                await page.goto('/dashboard');
                await openMobileMenu(page);
                await screenshot(page, 'mobile', lang, 'dashboard', 'menu-open');
            });
        });
    });

    test.describe('Settings', () => {
        test('user preferences - all languages', async ({ page }, testInfo) => {
            const viewport = getViewport(testInfo);
            await login(page, TEST_USER);
            
            await forEachLanguage(page, async (lang) => {
                await navigateTo(page, '/settings');
                await screenshot(page, viewport, lang, 'settings', 'user-preferences');
            });
        });

        test('global settings (admin) - all languages', async ({ page }, testInfo) => {
            const viewport = getViewport(testInfo);
            await login(page, TEST_ADMIN);
            
            await forEachLanguage(page, async (lang) => {
                await navigateTo(page, '/settings');
                await page.getByRole('tab', { name: /global/i }).click();
                await page.waitForTimeout(300);
                await screenshot(page, viewport, lang, 'settings', 'global-settings');
            });
        });
    });

    test.describe('Files', () => {
        test.beforeEach(async ({ page }) => {
            await login(page, TEST_USER);
        });

        test('static resources tab - all languages', async ({ page }, testInfo) => {
            const viewport = getViewport(testInfo);
            
            await forEachLanguage(page, async (lang) => {
                await page.goto('/files?tab=static');
                await page.waitForLoadState('networkidle');
                await screenshot(page, viewport, lang, 'files', 'static-tab');
            });
        });

        test('broker reports tab - all languages', async ({ page }, testInfo) => {
            const viewport = getViewport(testInfo);
            
            await forEachLanguage(page, async (lang) => {
                await page.goto('/files?tab=brim');
                await page.waitForLoadState('networkidle');
                await screenshot(page, viewport, lang, 'files', 'brim-tab');
            });
        });
    });

    test.describe('Brokers', () => {
        test.beforeEach(async ({ page }) => {
            await login(page, TEST_USER);
        });

        test('broker list - all languages', async ({ page }, testInfo) => {
            const viewport = getViewport(testInfo);
            
            await forEachLanguage(page, async (lang) => {
                await navigateTo(page, '/brokers');
                await screenshot(page, viewport, lang, 'brokers', 'list');
            });
        });

        test('broker detail - all languages', async ({ page }, testInfo) => {
            const viewport = getViewport(testInfo);
            
            await forEachLanguage(page, async (lang) => {
                await navigateTo(page, '/brokers');
                await page.getByTestId('broker-card').first().click();
                await page.waitForLoadState('networkidle');
                await screenshot(page, viewport, lang, 'brokers', 'detail');
            });
        });

        test('import modal - all languages', async ({ page }, testInfo) => {
            const viewport = getViewport(testInfo);
            
            await forEachLanguage(page, async (lang) => {
                await navigateTo(page, '/brokers');
                await page.getByTestId('broker-card').first().click();
                await page.getByRole('button', { name: /import/i }).click();
                await page.waitForTimeout(300);
                await screenshot(page, viewport, lang, 'brokers', 'import-modal');
                await page.keyboard.press('Escape');
            });
        });
    });
});
```

---

## 🔧 Step 5: Integrazione test_runner.py

### Nuova categoria "front" nel TEST_REGISTRY

```python
"front": {
    "_meta": {
        "help": "Frontend E2E tests (Playwright on Chromium)",
        "description": """
Frontend E2E Tests

Browser-based tests using Playwright:
  • Backend server started automatically in test mode
  • Tests run on Chromium (headless by default)
  • Use --ui for interactive Playwright UI
  • Use --headed to see browser
  • Screenshots saved on failure

Note: gallery.spec.ts is NOT included in 'all' - use ./dev.py mkdocs gallery
""",
    },
    "auth": {
        "func": front_auth,
        "test_names": False,
        "name": "Auth Tests",
        "desc": "Login, register, logout, language change",
        "prereq": "Test users created",
        "tests": "auth.spec.ts",
    },
    "settings": {
        "func": front_settings,
        "test_names": False,
        "name": "Settings Tests",
        "desc": "User preferences, global settings (admin)",
        "prereq": "Login working",
        "tests": "settings.spec.ts",
    },
    "files": {
        "func": front_files,
        "test_names": False,
        "name": "Files Tests",
        "desc": "Files page, tabs, URL filters",
        "prereq": "Login working",
        "tests": "files.spec.ts",
    },
    "brokers": {
        "func": front_brokers,
        "test_names": False,
        "name": "Brokers Tests",
        "desc": "CRUD broker, import files modal",
        "prereq": "Login working",
        "tests": "brokers.spec.ts",
    },
    "multi-user": {
        "func": front_multi_user,
        "test_names": False,
        "name": "Multi-User Tests",
        "desc": "Data isolation between users",
        "prereq": "Multiple test users",
        "tests": "multi-user.spec.ts",
    },
    "all": {
        "func": front_all,
        "test_names": False,
        "name": "All Frontend Tests",
        "desc": "Run all E2E tests (excludes gallery)",
    },
},
```

### Implementazione funzioni

```python
def _ensure_test_users() -> bool:
    """Ensure E2E test users exist in test database."""
    print_info("Ensuring E2E test users exist...")
    
    users = [
        ("e2e_test_user", "e2e@test.example.com", "E2eTestPass123!"),
        ("e2e_test_admin", "e2eadmin@test.example.com", "E2eAdminPass123!"),
        ("e2e_test_user2", "e2e2@test.example.com", "E2eTestPass456!"),
    ]
    
    for username, email, password in users:
        result = subprocess.run(
            ["python", "scripts/user_cli.py", "--test-db", "create", 
             username, email, password],
            capture_output=True,
            text=True
        )
        # Ignore "already exists" errors
        if result.returncode != 0 and "already exists" not in result.stderr:
            print_error(f"Failed to create user {username}: {result.stderr}")
            return False
    
    # Promote admin
    subprocess.run(
        ["python", "scripts/user_cli.py", "--test-db", "promote", "e2e_test_admin"],
        capture_output=True
    )
    
    print_success("Test users ready")
    return True


def _run_playwright(
    spec_file: str = None, 
    ui: bool = False, 
    headed: bool = False,
    project: str = "desktop"
) -> bool:
    """Run Playwright tests with given options."""
    cmd = ["npm", "run"]
    
    if ui:
        cmd.append("test:e2e:ui")
    elif headed:
        cmd.append("test:e2e:headed")
    else:
        cmd.append("test:e2e")
    
    # Add extra args after --
    extra_args = []
    if spec_file:
        extra_args.append(spec_file)
    if project and not ui:  # UI mode ignores project
        extra_args.extend(["--project", project])
    
    if extra_args:
        cmd.extend(["--"] + extra_args)
    
    return run_command(cmd, f"Playwright {spec_file or 'all'}", cwd="frontend")


def front_auth(verbose: bool = False, ui: bool = False, headed: bool = False) -> bool:
    """Run auth E2E tests."""
    print_section("Frontend Auth Tests")
    if not _ensure_test_users():
        return False
    return _run_playwright("auth.spec.ts", ui=ui, headed=headed)


def front_settings(verbose: bool = False, ui: bool = False, headed: bool = False) -> bool:
    """Run settings E2E tests."""
    print_section("Frontend Settings Tests")
    return _run_playwright("settings.spec.ts", ui=ui, headed=headed)


def front_files(verbose: bool = False, ui: bool = False, headed: bool = False) -> bool:
    """Run files E2E tests."""
    print_section("Frontend Files Tests")
    return _run_playwright("files.spec.ts", ui=ui, headed=headed)


def front_brokers(verbose: bool = False, ui: bool = False, headed: bool = False) -> bool:
    """Run brokers E2E tests."""
    print_section("Frontend Brokers Tests")
    return _run_playwright("brokers.spec.ts", ui=ui, headed=headed)


def front_multi_user(verbose: bool = False, ui: bool = False, headed: bool = False) -> bool:
    """Run multi-user isolation tests."""
    print_section("Frontend Multi-User Tests")
    return _run_playwright("multi-user.spec.ts", ui=ui, headed=headed)


def front_all(verbose: bool = False, ui: bool = False, headed: bool = False) -> bool:
    """Run all frontend tests (excludes gallery)."""
    if not _ensure_test_users():
        return False
    
    return _run_test_suite(
        suite_name="Frontend E2E Tests",
        tests=[
            ("Auth", lambda: _run_playwright("auth.spec.ts", ui=ui, headed=headed)),
            ("Settings", lambda: _run_playwright("settings.spec.ts", ui=ui, headed=headed)),
            ("Files", lambda: _run_playwright("files.spec.ts", ui=ui, headed=headed)),
            ("Brokers", lambda: _run_playwright("brokers.spec.ts", ui=ui, headed=headed)),
            ("Multi-User", lambda: _run_playwright("multi-user.spec.ts", ui=ui, headed=headed)),
        ],
        verbose=verbose,
    )
```

### Aggiungere frontend a run_all_tests

```python
def run_all_tests(verbose: bool = False) -> bool:
    """Run complete test suite including frontend."""
    return _run_test_suite(
        suite_name="Complete Test Suite",
        tests=[
            # ... existing backend tests ...
            ("External Services", lambda: external_all(verbose)),
            ("Database Layer", lambda: db_all(verbose)),
            ("Schema Validation", lambda: schemas_all(verbose)),
            ("Utility Modules", lambda: utils_all(verbose)),
            ("Services Layer", lambda: services_all(verbose)),
            ("API Endpoints", lambda: api_all(verbose)),
            ("E2E Tests", lambda: e2e_all(verbose)),
            # NEW: Frontend tests at the end
            ("Frontend E2E", lambda: front_all(verbose)),
        ],
        # ...
    )
```

---

## 🔧 Step 6: Comandi dev.py mkdocs

### Estendere mkdocs commands

```python
# In dev.py, mkdocs subparser

def mkdocs_gallery(args) -> bool:
    """Generate gallery screenshots for all languages and viewports."""
    print_header("Gallery Screenshot Generation")
    print_info("Generating screenshots for mkdocs documentation")
    print_info("This runs gallery.spec.ts on both desktop and mobile viewports")
    
    # Ensure test users exist
    if not _ensure_test_users():
        return False
    
    # Run gallery for desktop
    print_section("Desktop Screenshots")
    success = _run_playwright("gallery.spec.ts", headed=True, project="desktop")
    if not success:
        return False
    
    # Run gallery for mobile
    print_section("Mobile Screenshots")
    success = _run_playwright("gallery.spec.ts", headed=True, project="mobile")
    
    if success:
        print_success("Gallery screenshots generated!")
        print_info("Output: mkdocs_src/docs/gallery/")
    
    return success


def mkdocs_build(args) -> bool:
    """Build mkdocs documentation."""
    if args.gallery:
        print_info("Regenerating gallery screenshots first...")
        if not mkdocs_gallery(args):
            print_warning("Gallery generation failed, continuing with build...")
    
    # Normal mkdocs build
    return run_command(["mkdocs", "build"], "MkDocs build")
```

### CLI commands

```bash
# Gallery only
./dev.py mkdocs gallery

# Build with gallery regeneration
./dev.py mkdocs build --gallery

# Normal build (uses existing screenshots)
./dev.py mkdocs build

# Serve locally
./dev.py mkdocs serve
```

---

## 🔧 Step 7: Flag --clean-db

### Aggiungere a test_runner.py

```python
# In create_parser()
parser.add_argument(
    "--clean-db",
    action="store_true",
    help="Reset test database to clean state before running tests",
    default=False
)

# In main() o nelle funzioni test
if args.clean_db:
    print_info("Resetting test database...")
    subprocess.run(["./dev.py", "db", "create-clean", "--test"])
    subprocess.run(["./dev.py", "test", "db", "populate", "--force"])
```

---

## 📋 CLI Commands Summary

```bash
# =============================================================================
# Frontend E2E Tests
# =============================================================================

# Run all frontend tests (headless)
./dev.py test front all

# Run specific test
./dev.py test front auth
./dev.py test front settings
./dev.py test front files
./dev.py test front brokers
./dev.py test front multi-user

# With Playwright UI (interactive debugging)
./dev.py test front all --ui
./dev.py test front auth --ui

# With visible browser (headless=false)
./dev.py test front auth --headed

# With clean database
./dev.py test front all --clean-db

# =============================================================================
# Gallery Screenshots
# =============================================================================

# Generate all screenshots (desktop + mobile, all languages)
./dev.py mkdocs gallery

# Build docs with fresh screenshots
./dev.py mkdocs build --gallery

# =============================================================================
# Complete Test Suite (includes frontend)
# =============================================================================

./dev.py test all                    # Backend + Frontend
./dev.py test all --clean-db         # With fresh database
```

---

## 📋 Principi di Design Test

1. **Indipendenza**: Ogni test può passare partendo da `db populate`
2. **Self-contained**: Test creano i propri dati necessari
3. **Ordine logico**: auth → settings → files → brokers → multi-user
4. **Cleanup opzionale**: `--clean-db` per reset completo
5. **Gallery separata**: Non inclusa in `test all`, comando dedicato
6. **Multi-lingua**: Gallery genera screenshot per EN/IT/FR/ES
7. **Multi-viewport**: Desktop (1920x1080) e Mobile (iPhone 14 Pro Max)

---

## 📋 Checklist Implementazione

### Setup
- [ ] Aggiornare `.env` e `.env.example` con tutte le variabili da config.py
- [ ] `cd frontend && npm install -D @playwright/test dotenv`
- [ ] `npx playwright install chromium`
- [ ] Creare `frontend/e2e/` directory structure

### Playwright Config
- [ ] Creare `frontend/playwright.config.ts`
- [ ] Aggiungere scripts a `frontend/package.json`

### Test Fixtures
- [ ] `e2e/fixtures/test-users.ts`
- [ ] `e2e/fixtures/auth-helpers.ts`
- [ ] `e2e/fixtures/db-helpers.ts`

### Test Specs
- [ ] `e2e/auth.spec.ts`
- [ ] `e2e/settings.spec.ts`
- [ ] `e2e/files.spec.ts`
- [ ] `e2e/brokers.spec.ts`
- [ ] `e2e/multi-user.spec.ts`
- [ ] `e2e/gallery.spec.ts`

### Integration
- [ ] Aggiungere categoria "front" a `test_runner.py`
- [ ] Implementare `_ensure_test_users()`
- [ ] Aggiungere `--ui`, `--headed`, `--clean-db` flags
- [ ] Aggiungere frontend a `run_all_tests()`
- [ ] Estendere `./dev.py mkdocs` con `gallery` e `--gallery` flag

### Gallery
- [ ] Creare `mkdocs_src/docs/gallery/` structure
- [ ] Aggiungere `data-testid` ai componenti necessari

### Documentation
- [ ] Aggiornare dev.py --help
- [ ] Documentare in README

---

## 📚 Note Future

### Aggiungere Safari/Firefox
Playwright supporta nativamente Safari (WebKit) e Firefox. Per aggiungerli:

```typescript
// In playwright.config.ts projects array
{
    name: 'firefox',
    use: { ...devices['Desktop Firefox'] },
},
{
    name: 'webkit',
    use: { ...devices['Desktop Safari'] },
},
```

### Test Condivisione Broker (futuro)
Quando implementeremo la condivisione broker:
- Estendere `multi-user.spec.ts`
- Test: owner condivide → editor vede
- Test: viewer non può modificare
- Test: revoca accesso → non vede più
