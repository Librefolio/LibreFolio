# LibreFolio — Frontend Testing Reference (Playwright E2E)

## 📁 Struttura Test

```text
frontend/
├── e2e/                        # 181+ Playwright E2E tests
│   ├── fixtures/               # Helpers condivisi
│   │   ├── auth-helpers.ts     # login(), logout(), setLanguage(), navigateTo()
│   │   ├── db-helpers.ts       # resetDatabase(), populateDatabase()
│   │   ├── test-users.ts       # TEST_USER, TEST_ADMIN, TEST_USER_2, ...
│   │   └── i18n-data.ts        # Dati traduzioni attese per test i18n
│   ├── auth.spec.ts            # Login, register, logout
│   ├── settings.spec.ts        # User & global settings
│   ├── files.spec.ts           # File management
│   ├── select-components.spec.ts # UI select components
│   ├── image-crop.spec.ts      # Image crop modal
│   ├── gallery.spec.ts         # Screenshot automatici per docs
│   ├── fx/                     # FX-specific tests
│   │   ├── fx-list.spec.ts
│   │   ├── fx-detail.spec.ts
│   │   ├── fx-csv-import.spec.ts
│   │   └── fx-helpers.ts
│   ├── assets/                 # Asset-specific tests
│   │   ├── asset-list.spec.ts
│   │   ├── asset-detail.spec.ts
│   │   ├── asset-modal.spec.ts
│   │   ├── asset-data-editor.spec.ts
│   │   └── assets-helpers.ts
│   └── brokers/                # Broker-specific tests
│       └── ...
├── playwright.config.ts        # Config (2 projects: desktop + mobile)
└── playwright-report/          # HTML report generato
```

---

## ▶️ Come Eseguire

```bash
# Categorie di test frontend (via dev.py)
./dev.py test front-utility all     # auth, settings, files, select, image-crop
./dev.py test front-user all        # brokers, multi-user, sharing
./dev.py test front-fx all          # unit (Vitest) + E2E fx
./dev.py test front-asset all       # list, detail, modal, data-editor

# Singola sotto-categoria
./dev.py test front-fx fx-list      # Solo FX list page
./dev.py test front-asset asset-detail  # Solo asset detail

# Con backend coverage tracking
./dev.py test --coverage front-fx all

# Con UI interattiva Playwright
./dev.py test front-fx fx-list --ui

# Con browser visibile
./dev.py test front-fx fx-list --headed

# Con debug step-by-step
./dev.py test front-fx fx-list --debug

# Lista test disponibili
./dev.py test front-fx fx-list --list

# Generare screenshot gallery per documentazione
./dev.py mkdocs gallery
```

---

## 🏗️ Architettura

### Playwright Config (`playwright.config.ts`)

- **2 progetti**: `desktop` (1280×720, Chrome) + `mobile` (iPhone 14 Pro Max viewport, Chromium)
- **Mobile usa Chromium**: il device descriptor `iPhone 14 Pro Max` fornisce viewport/isMobile/hasTouch, ma usiamo Chromium come browser (WebKit su Linux ha problemi di stabilità con click/touch)
- **Workers**: 1 (test sequenziali — stato condiviso nel DB)
- **Timeout**: 30s per test, 3s per singola assertion
- **Web Server auto-start**: `./dev.py server --test --force` (porta 8001)
- **Backend coverage**: se `COVERAGE_BACKEND=1` nell'env, aggiunge `--coverage` al server command
- **Retry**: 0 locale, 2 in CI

⚠️ **Linux**: Playwright richiede librerie di sistema aggiuntive:
```bash
sudo npx playwright install-deps
# oppure: sudo apt-get install libgstreamer-plugins-bad1.0-0 libflite1 libavif16 gstreamer1.0-libav
```

### Fixtures (`e2e/fixtures/`)

```typescript
// auth-helpers.ts
import {login, logout, setLanguage, navigateTo, openMobileMenu} from '../fixtures/auth-helpers';

// Uso tipico
await login(page);                    // Login con TEST_USER default
await login(page, TEST_ADMIN);        // Login come admin
await setLanguage(page, 'it');        // Cambia lingua
await navigateTo(page, '/assets');    // Navigazione diretta
await logout(page);
```

```typescript
// db-helpers.ts
import {resetDatabase, populateDatabase} from '../fixtures/db-helpers';

// Reset completo (create-clean + populate)
await resetDatabase();

// Solo populate (senza ricreare)
await populateDatabase();
```

```typescript
// test-users.ts
import {TEST_USER, TEST_ADMIN, TEST_USER_2} from '../fixtures/test-users';

// Utenti standard
TEST_USER  = { username: 'e2e_test_user',  password: 'E2eTestPass123!' }
TEST_ADMIN = { username: 'e2e_test_admin', password: 'E2eAdminPass123!' }
```

---

## 🏗️ Come Creare un Test

### Pattern Base

```typescript
import {test, expect} from '@playwright/test';
import {login} from '../fixtures/auth-helpers';

test.describe('Feature Name', () => {
    test.beforeEach(async ({page}) => {
        await login(page);
    });

    test('should do something', async ({page}) => {
        // Navigate
        await page.goto('/assets');
        
        // Assert visibility (usa data-testid)
        await expect(page.getByTestId('assets-page')).toBeVisible({timeout: 10_000});
        
        // Interact
        await page.getByTestId('some-button').click();
        
        // Assert result
        await expect(page.getByTestId('result-element')).toContainText('Expected');
    });
});
```

### Graceful Skip (quando dati mancanti)

```typescript
test('should edit data', async ({page}) => {
    // Try to find required element
    const btn = page.getByTestId('edit-button');
    if (!await btn.isVisible({timeout: 5000}).catch(() => false)) {
        test.skip(true, 'Edit button not available (no data in test DB)');
        return;
    }
    // ... rest of test
});
```

### Helper per-feature (pattern domain-specific)

```typescript
// assets/assets-helpers.ts
export async function goToAssetsPage(page) {
    await navigateTo(page, '/assets');
    await page.waitForSelector('[data-testid="assets-page"]', {timeout: 15_000});
    await page.waitForTimeout(1000);
}

export async function navigateToAssetByName(page, assetName: string) {
    const searchInput = page.getByTestId('assets-search-input');
    if (await searchInput.isVisible({timeout: 3000}).catch(() => false)) {
        await searchInput.fill(assetName);
        await page.waitForTimeout(800);
    }
    const card = page.locator('[data-testid^="asset-card-"]').first();
    await card.click();
    await page.waitForSelector('[data-testid="asset-detail-page"]', {timeout: 10_000});
}
```

---

## 📸 Gallery (Screenshot per Docs)

`gallery.spec.ts` cattura screenshot automatici per la documentazione MkDocs:
- Light + Dark mode
- Desktop + Mobile viewport (entrambi via Chromium)
- Dati deterministici (DB resettato con `--with-static --with-reports`)

**Prerequisiti**:
- `./dev.py db populate --force` prima della generazione
- Su Linux: `sudo npx playwright install-deps` per librerie di rendering

```bash
# Genera gallery completa
./dev.py mkdocs gallery

# Solo desktop
./dev.py mkdocs gallery --desktop-only

# Filtra per nome
./dev.py mkdocs gallery -f "assets"

# Lista screenshot disponibili
./dev.py mkdocs gallery -l
```

Output: `mkdocs_src/docs/assets/img/gallery/` (usato in documentazione utente).

---

## 📊 Backend Coverage durante E2E

I test Playwright possono tracciare la coverage del codice backend eseguito durante i test E2E:

```bash
# Eseguire test frontend con backend coverage
./dev.py test --coverage front-fx all
./dev.py test --coverage front-user all
./dev.py test --coverage all-frontend

# Il report viene generato in htmlcov-frontend/
./dev.py test coverage show frontend
```

### Come funziona — Architettura SIGTERM a 3 livelli

Il tracciamento della coverage richiede che `coverage run` riceva **SIGTERM** alla fine dei test
per scrivere il file `.coverage.<pid>`. Senza configurazione specifica, Playwright invia
**SIGKILL** (non intercettabile) al webServer, rendendo impossibile il salvataggio dei dati.

La soluzione richiede **4 elementi**, tutti necessari:

1. **`gracefulShutdown`** in `playwright.config.ts`: configura Playwright per inviare SIGTERM
   (invece di SIGKILL) al webServer, con fallback a SIGKILL dopo 5s
2. **`exec`** nel comando webServer: `/bin/sh` si sostituisce con `dev.py` (elimina la shell intermedia)
3. **`os.execvpe()`** in `dev.py`: dev.py si sostituisce con `pipenv run coverage run`
4. **`os.execvpe()`** in `pipenv run`: pipenv si sostituisce con `coverage run` (comportamento POSIX standard)

```text
Playwright gracefulShutdown SIGTERM ──────────────────────────→ SIGTERM
        │                                                          │
        ▼                                                          ▼
   /bin/sh -c "cd .. && exec ./dev.py server --coverage"     coverage run
        │  exec (livello 1: shell si sostituisce)            riceve SIGTERM
        ▼                                                    scrive .coverage.*
   dev.py → os.execvpe(pipenv, ...)
        │  exec (livello 2: dev.py si sostituisce)
        ▼
   pipenv run → os.execvpe(coverage, ...)
        │  exec (livello 3: pipenv si sostituisce)
        ▼
   coverage run -m uvicorn   ← STESSO PID di /bin/sh!
```

**Flusso completo:**

1. `./dev.py test --coverage front-fx all` setta `_COVERAGE_MODE=True`
2. `_run_playwright()` setta `COVERAGE_BACKEND=1` nell'env di Playwright
3. `playwright.config.ts` rileva `COVERAGE_BACKEND`:
   - Aggiunge `--coverage` al webServer command
   - Setta `reuseExistingServer: false` (forza un server fresco, non riutilizza uno non-coverage)
4. Il webServer command usa `exec`: `cd .. && exec ./dev.py server --test --force --coverage`
5. `dev.py` in coverage mode usa `os.execvpe()` per sostituirsi con `pipenv run coverage run ...`
6. `pipenv run` (su POSIX) usa `os.execvpe()` per sostituirsi con `coverage run -m uvicorn`
7. Alla fine dei test, Playwright manda SIGTERM al PID del webServer
8. Grazie alla catena di exec, quel PID **è** `coverage run`
9. `.coveragerc` ha `sigterm = true` → coverage intercetta SIGTERM e scrive `.coverage.<pid>`
10. Il test runner fa `coverage combine` + `coverage html -d htmlcov-frontend/`

> ⚠️ **CRITICO**: Senza `gracefulShutdown` nella config di Playwright, il webServer viene
> terminato con SIGKILL (non intercettabile) — nessun dato di coverage viene scritto.
> Senza `exec` a qualsiasi livello, SIGTERM raggiunge solo il processo padre
> e il figlio (`coverage run`) diventa orfano.

> **Garanzia**: La coverage viene catturata sia in caso di successo che di fallimento dei test.
> L'unico caso di perdita è un crash totale del server (segfault, OOM, SIGKILL manuale).

### File chiave

| File | Ruolo nella pipeline |
|------|---------------------|
| `playwright.config.ts` | `gracefulShutdown: {signal: 'SIGTERM', timeout: 5000}` + `exec` nel command + `reuseExistingServer: false` |
| `dev.py` (cmd_server) | `os.execvpe()` in coverage mode (sostituisce dev.py con pipenv) |
| `.coveragerc` | `sigterm = true` + `parallel = true` + `source = backend/app` |
| `scripts/test_runner.py` | `_dispatch_test_command()` fa `coverage combine` + `coverage html` |

---

## ⚠️ Convenzioni

- **`data-testid` sempre**: mai selezionare per classe CSS o testo (fragile con i18n)
- **Timeout espliciti**: usare `{timeout: N}` su expect/waitFor — non lasciare i default
- **`waitForTimeout` minimo**: usare solo dove necessario (animazioni, debounce)
- **Graceful skip**: se un test dipende da dati mock, usare `test.skip()` con messaggio chiaro
- **Mobile awareness**: molti test girano sia su desktop che mobile — gestire hamburger menu con `openMobileMenu()`
- **Nessun login hardcoded**: usare sempre `login()` da `auth-helpers.ts`
- **Nomi test descrittivi**: `test('should create asset with valid data', ...)`

---

## 📍 Dove Trovare Cosa

| Cosa cerchi? | Dove guardare |
|--------------|---------------|
| Test per Assets | `frontend/e2e/assets/` (4 spec + 1 helper) |
| Test per FX | `frontend/e2e/fx/` |
| Test per Brokers | `frontend/e2e/brokers/` |
| Auth/Settings | `frontend/e2e/auth.spec.ts`, `settings.spec.ts` |
| Gallery screenshot | `frontend/e2e/gallery.spec.ts` |
| Fixtures condivise | `frontend/e2e/fixtures/` |
| Config Playwright | `frontend/playwright.config.ts` |
| Report HTML | `frontend/playwright-report/` |



