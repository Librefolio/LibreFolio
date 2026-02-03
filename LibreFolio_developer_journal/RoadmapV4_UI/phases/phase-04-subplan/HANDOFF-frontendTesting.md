# 🚀 LibreFolio - Frontend Testing Implementation

## Cosa devi fare

Implementare l'infrastruttura di test E2E frontend con Playwright, seguendo il piano dettagliato.

## 📁 File Chiave da Leggere

1. **Piano completo**: `LibreFolio_developer_journal/RoadmapV4_UI/plan-frontendTesting.md`
    - Contiene TUTTO: architettura, codice, checklist, CLI commands
    - Seguilo step by step

2. **Welcome prompt**: Il system prompt iniziale contiene info sul progetto, comandi `./dev.py`, struttura

## 🎯 Task in Ordine

### Step 0: Setup .env

- Aggiornare `.env` e `.env.example` con variabili da `backend/app/config.py`
- Variabili: PORT, TEST_PORT, TEST_DATABASE_URL, PROJECT_NAME, VERSION, etc.

### Step 1: Playwright Setup

```bash
cd frontend
npm install -D @playwright/test dotenv
npx playwright install chromium
```

- Creare `playwright.config.ts` (codice nel piano)
- Aggiungere scripts a `package.json`

### Step 2: Test Fixtures

Creare in `frontend/e2e/fixtures/`:

- `test-users.ts` - Credenziali utenti test
- `auth-helpers.ts` - Login/logout/setLanguage helpers
- `db-helpers.ts` - Reset DB helpers

### Step 3: Test Specs

Creare in `frontend/e2e/`:

- `auth.spec.ts`
- `settings.spec.ts`
- `files.spec.ts`
- `brokers.spec.ts`
- `multi-user.spec.ts`
- `gallery.spec.ts`

### Step 4: Integration test_runner.py

- Aggiungere categoria "front" a `TEST_REGISTRY`
- Implementare funzioni `_ensure_test_users()`, `_run_playwright()`, `front_*`
- Aggiungere flags `--ui`, `--headed`, `--debug`, `--clean-db`
- Aggiungere frontend a `run_all_tests()`

### Step 5: Comandi mkdocs

- Estendere `./dev.py mkdocs` con comando `gallery`
- Aggiungere flag `--gallery` a `build`

### Step 6: Gallery Structure

- Creare `mkdocs_src/docs/gallery/{desktop,mobile}/{en,it,fr,es}/`

## ⚡ Comandi Utili

```bash
./dev.py server --test          # Server in test mode
./dev.py front check            # Type-check frontend
./dev.py front build            # Build frontend
./dev.py test db populate       # Popola DB test
./dev.py user create --test-db  # Crea utente su test DB
```

## 🔑 Punti Critici

1. **Porta da .env**: `playwright.config.ts` deve leggere PORT da `../.env`
2. **Email valide**: Usare `@test.example.com` (non `.local`)
3. **Mobile burger menu**: Test mobile devono cliccare hamburger prima di navigare
4. **Gallery multilingua**: Screenshot per EN/IT/FR/ES × desktop/mobile
5. **Gallery separata**: NON inclusa in `test all`, comando dedicato `./dev.py mkdocs gallery`
6. **Test indipendenti**: Ogni test deve passare partendo da `db populate`

## 📋 Checklist Rapida

- [x] .env aggiornato
- [x] Playwright installato
- [x] playwright.config.ts creato (con fix ES modules)
- [x] Fixtures creati
- [x] Test specs creati (6 file)
- [x] test_runner.py aggiornato con categoria "front"
- [x] Flags --ui, --headed, --debug (PWDEBUG=1)
- [x] ./dev.py mkdocs gallery funzionante
- [x] Documentazione aggiornata (frontend/README.md)
- [ ] data-testid sui componenti (da fare in Phase 4+)

## 🚨 Prima di Iniziare

```bash
# Verifica che backend funzioni
./dev.py server --test &
curl http://localhost:8000/api/v1/system/health

# Verifica frontend compila
./dev.py front check
```

---

**Vai al piano completo** in `plan-frontendTesting.md` e inizia dall'alto. Il codice è già scritto, devi solo implementarlo file per file.
