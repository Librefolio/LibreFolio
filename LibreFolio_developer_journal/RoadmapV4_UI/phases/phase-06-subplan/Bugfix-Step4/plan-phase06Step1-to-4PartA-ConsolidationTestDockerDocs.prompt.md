# Phase 06 Step 4 Part B — Consolidamento, Test, Docker & Documentazione

**Status**: ✅ COMPLETATO  
**Ultimo aggiornamento**: 10 Aprile 2026

Fase di consolidamento post Step 4 Part A. 6 blocchi: fix tema dark/light, splash screen, test completa (backend + E2E), fix populate, documentazione + gallery, Dockerfile runtime-only. Il Docker è un'immagine singola di runtime (build frontend su host, non in Docker). Health check: `GET /api/v1/system/health`.

### Progresso

| Blocco | Descrizione | Status |
|--------|-------------|--------|
| **4** | Fix populate (Gold Spot + BTP Italia) | ✅ Completato |
| **6A** | `--host`/`--port` in dev.py + `.env` | ✅ Completato |
| **1** | ThemeStore centralizzato + anti-FOUC | ✅ Completato |
| **2** | Splash screen VPN/lento | ✅ Completato |
| **3A** | Test backend mancanti (+5 test) | ✅ Completato |
| **3B pre-req** | `data-testid` in AssetModal | ✅ Completato |
| **6B** | Dockerfile + docker-compose + .dockerignore | ✅ Completato |
| **6B+** | Comandi `./dev.py docker build/up/down/logs/status` | ✅ Completato |
| **3B** | Test E2E assets (helpers + 3 spec files) | ✅ Struttura creata |
| **3B+** | `front-asset` in test_runner.py + E2E reorg (`brokers/`) | ✅ Completato |
| **5A** | Audit e fix documentazione | ✅ Completato (EN-only, traduzioni via LLM pipeline) |
| **5B** | Gallery assets in gallery.spec.ts | ✅ Completato (8 scene Assets) |
| **Block 6** | Developer docs backend (architecture, events, system providers, plugin guide, test walkthrough) | ✅ Completato |

---

## Blocco 1 — Fix Dark/Light Mode (ciclo giorno/notte)

**Root cause**: due chiavi localStorage divergenti. `ThemeToggle` e `PreferencesTab` usano `librefolio-theme`, `auth.ts` usa `theme`. Al cambio ciclo giorno/notte dell'OS, il listener `prefers-color-scheme` non riesce a reagire perché la priorità di lettura è inconsistente.

### Steps
1. **Creare `frontend/src/lib/stores/themeStore.ts`** — modulo centralizzato: `applyTheme(mode)`, `getCurrentResolvedTheme()`, `getStoredThemePreference()`, `initThemeListener()`. Unica chiave: `librefolio-theme`. Valori: `'light' | 'dark' | ''` (vuoto = auto).
2. **Refactor `ThemeToggle.svelte`** (`frontend/src/lib/components/ui/ThemeToggle.svelte`) — delegare logica a `themeStore`.
3. **Refactor `auth.ts`** (`frontend/src/lib/stores/auth.ts` righe 74-93) — usare `applyTheme()` da themeStore, eliminare chiave `'theme'`.
4. **Refactor `PreferencesTab.svelte`** (`frontend/src/lib/components/settings/tabs/PreferencesTab.svelte`) — usare `themeStore`.
5. **Script inline anti-FOUC in `app.html`** (`frontend/src/app.html` `<head>`) — ~10 righe: legge `librefolio-theme`, applica classe `dark`/`light` su `<html>` prima del primo paint.

### File coinvolti
- `frontend/src/lib/stores/themeStore.ts` (nuovo)
- `frontend/src/lib/components/ui/ThemeToggle.svelte`
- `frontend/src/lib/stores/auth.ts`
- `frontend/src/lib/components/settings/tabs/PreferencesTab.svelte`
- `frontend/src/app.html`

---

## Blocco 2 — Splash Screen per Connessioni Lente (VPN)

### Problema
Su connessioni lente (VPN), il bundle CSS di Tailwind arriva dopo l'HTML renderizzato → pagina login appare sformattata (testo nudo senza stile).

### Steps
1. **Splash HTML + CSS inline in `app.html`** (`frontend/src/app.html`) — `<div id="app-splash">` con `position: fixed; z-index: 9999`, sfondo + logo SVG inline + spinner CSS-only (no dipendenze Tailwind).
2. **Tema splash**: lo script del Blocco 1 setta anche `--splash-bg` (bianco o `#0f172a`) sullo splash.
3. **Rimozione splash in root `+layout.svelte`** (`frontend/src/routes/+layout.svelte`) — dopo `$i18nLoading === false`, rimuovi `#app-splash` con fade-out.

### File coinvolti
- `frontend/src/app.html`
- `frontend/src/routes/+layout.svelte`

---

## Blocco 3 — Suite di Test Completa

### 3A — Test Backend Mancanti

| Test | File | Cosa copre | Step coperto |
|------|------|-----------|-------------|
| Sync idempotenza asset | `test_assets_prices.py` | Sync + re-sync → `points_changed == 0` | Step 4 (Bugfix 5) |
| Sync con `include_events: true` | `test_assets_prices.py` | Eventi presenti nel payload | Step 4 (Bugfix 7) |
| Provider probe con params errati | `test_assets_provider.py` | Config CSS malformata → errore chiaro | Step 3 |
| ScheduledInvestment via API | `test_assets_provider.py` | Assign + sync → curva calcolata | Step 3 |
| Bulk sync multi-asset | `test_assets_prices.py` | 3+ asset in un unico sync request | Step 2c |

**Nota copertura Step 1-3**: la copertura backend è già buona (CRUD: 19 test, metadata: 4, patch: 8, provider: 14, prices: 6, CSS scraper: 1, countries: 5). Le lacune specifiche sono coperte sopra.

### File coinvolti (backend)
- `backend/test_scripts/test_api/test_assets_prices.py`
- `backend/test_scripts/test_api/test_assets_provider.py`

---

### 3B — Test E2E Frontend (Playwright) — Completamente Assenti

**Stato attuale**: zero test E2E per assets. Nessuna directory `e2e/assets/`, nessun helper, nessun spec. Solo `asset-picker-modal` (picker media file, non correlato). La `AssetModal` non ha nemmeno `data-testid`.

#### Pre-requisiti: aggiungere `data-testid` a `AssetModal.svelte`
Aggiungere `data-testid` ai campi chiave della modale: form container, display_name input, currency select, asset_type select, identifier fields, provider section, distribution editors, save button, cancel button.

#### File da creare

1. **`frontend/e2e/assets/assets-helpers.ts`** — helper:
   - `goToAssetsPage(page)` → `navigateTo('/assets')` + `waitForSelector('[data-testid="assets-page"]')`
   - `goToAssetDetailPage(page, assetId)` → `navigateTo('/assets/${id}')` + `waitForSelector('[data-testid="asset-detail-page"]')`
   - `openCreateAssetModal(page)` → click `assets-add-button` + wait modal
   - `openEditAssetModal(page)` → click `asset-detail-edit-btn` + wait modal

2. **`frontend/e2e/assets/asset-list.spec.ts`** (~10 test):
   - Lista visibile con asset cards
   - Filtro ricerca testo
   - Filtro per tipo asset
   - Toggle attivi/tutti
   - Bulk sync-all button
   - Refresh-all button
   - Navigazione a detail page via click card

3. **`frontend/e2e/assets/asset-detail.spec.ts`** (~12 test):
   - Pagina caricata con header + chart
   - Filter bar: badge date range, currency select
   - Sync singolo + verifica metadata reload
   - Edit modale si apre (no `effect_update_depth_exceeded`)
   - Bottoni responsive (abs/%, edit, sync, refresh)
   - Signal panel toggle + aggiunta segnale
   - Measure panel toggle
   - Classificazione: pie chart settori + mappa visibili
   - Back button navigazione
   - Event markers visibili su asset con eventi

4. **`frontend/e2e/assets/asset-modal.spec.ts`** (~8 test):
   - Creazione asset base (nome + valuta)
   - Creazione con tipo + identifier
   - Edit asset: campi pre-popolati
   - Ask provider: probe + risultati
   - Distribuzione settori: aggiungere/rimuovere voci
   - Distribuzione geografica: aggiungere/rimuovere voci

#### Gallery `gallery.spec.ts` — `test.describe('Assets')`

Replicare esattamente il pattern FX (scene × 4 lingue × 2 temi × 2 viewport):

| Scene | data-testid chiave |
|-------|-------------------|
| List view | `assets-page` |
| List filtered | `assets-search-input` + `assets-type-filter` |
| Detail chart | `asset-detail-chart` + `canvas` |
| Detail signals | `asset-detail-signals-toggle/panel` |
| Detail measures | `asset-detail-measures-toggle` |
| Detail classification | `asset-detail-metadata-toggle/panel` |
| Detail editor | `asset-detail-edit-btn` + `asset-detail-editor-panel` |
| Edit modal | `assets-add-button` / `asset-detail-edit-btn` |

### File coinvolti (frontend)
- `frontend/src/lib/components/assets/AssetModal.svelte` (aggiungere data-testid)
- `frontend/e2e/assets/assets-helpers.ts` (nuovo)
- `frontend/e2e/assets/asset-list.spec.ts` (nuovo)
- `frontend/e2e/assets/asset-detail.spec.ts` (nuovo)
- `frontend/e2e/assets/asset-modal.spec.ts` (nuovo)
- `frontend/e2e/gallery.spec.ts` (aggiungere sezione Assets)

---

## Blocco 4 — Fix Dati Populate (BTP Italia + Gold Spot)

### Bug Gold Spot
In `populate_mock_data.py` riga 722, le chiavi sono **sbagliate**:
- `css_selector` → dovrebbe essere `current_css_selector` (come validato da `CSSScraperProvider.validate_params()`)
- `decimal_separator` → dovrebbe essere `decimal_format`
- Manca `currency` (required!)

### Bug BTP Italia
Da diagnosticare: il ScheduledInvestmentProvider potrebbe non accettare la configurazione attuale. La config sembra corretta a livello schema, ma il sync potrebbe fallire per un errore nell'engine di calcolo.

### Steps
1. **Correggere Gold Spot**: `{"current_css_selector": "#sp-last", "currency": "USD", "decimal_format": "us"}`.
2. **Diagnosticare BTP Italia**: run test manuale, aggiustare parametri se necessario.
3. **Test di validazione**: coperti dal Blocco 3A.

### File coinvolti
- `backend/test_scripts/test_db/populate_mock_data.py`

---

## Blocco 5 — Documentazione (EN-only) + Gallery

Traduzioni IT/FR/ES saranno fatte in un passo successivo con `./dev.py mkdocs translate`.

### 5A — Audit e Fix Documentazione

1. **`mkdocs_src/docs/user/installation.en.md`**: URL GitHub `ea-enel` → `Alfystar`, rimuovere `docker-compose` inesistente, aggiornare con nuovo Dockerfile.
2. **`mkdocs_src/docs/developer/dev-installation.md`**: Python `3.11+` → `3.13+`, Node.js `18+` → `20.19+`, documentare `--host`/`--port`.
3. **`mkdocs_src/docs/admin/docker_advanced.en.md`**: allineare con Docker reale.
4. **Creare `mkdocs_src/docs/user/assets/`**: overview asset management con screenshot gallery.
5. **`README.md`**: prerequisiti, sezione Docker, verificare se `dev.sh` è deprecato.

### 5B — Gallery
Sezione `Assets` completa (come FX): 8+ scene × 4 lingue × 2 temi × 2 viewport.

### File coinvolti
- `mkdocs_src/docs/user/installation.en.md`
- `mkdocs_src/docs/developer/dev-installation.md`
- `mkdocs_src/docs/admin/docker_advanced.en.md`
- `mkdocs_src/docs/user/assets/` (nuovo, directory + file)
- `README.md`
- `frontend/e2e/gallery.spec.ts`

---

## Blocco 6 — `--host`/`--port` in dev.py + Dockerfile

### 6A — `--host` e `--port` per dev.py

1. **Aggiungere `HOST=0.0.0.0`** in `.env` e `.env.example`.
2. **Aggiornare `dev.py` `cmd_server`** (riga 238-241) — leggere `HOST` da env, aggiungere args `--host` e `--port` (override env). Passare a uvicorn.
3. **Aggiornare parser** (riga 866-872): aggiungere `--host` e `--port` come argomenti opzionali.

### 6B — Dockerfile (runtime-only)

1. **Creare `Dockerfile`** — singolo stage `python:3.13-slim`. Copia `backend/`, `frontend/build/`, `mkdocs_src/site/`, `Pipfile*`, `dev.py`, `scripts/`. Installa dipendenze Python. Entrypoint: uvicorn.
2. **Creare `docker-compose.yml`** — servizio `librefolio`, volume per data, porta da `${PORT}`, health check `GET /api/v1/system/health`.
3. **Creare `.dockerignore`** — escludi `node_modules/`, `__pycache__/`, `data/test/`, `.git/`, `htmlcov/`, `LibreFolio_developer_journal/`, `e2e/`.

### File coinvolti
- `.env`
- `.env.example`
- `dev.py`
- `scripts/cli_base.py` (eventuale `get_server_host()`)
- `Dockerfile` (nuovo)
- `docker-compose.yml` (nuovo)
- `.dockerignore` (nuovo)

---

## Ordine di Esecuzione

1. **Blocco 4** — Fix populate (5 min)
2. **Blocco 6A** — `--host`/`--port` in dev.py
3. **Blocco 1** — ThemeStore centralizzato
4. **Blocco 2** — Splash screen
5. **Blocco 3A** — Test backend
6. **Blocco 3B pre-req** — Aggiungere `data-testid` a `AssetModal`
7. **Blocco 6B** — Dockerfile + docker-compose
8. **Blocco 3B** — Test E2E assets
9. **Blocco 5** — Documentazione + gallery (ultimo)

---

## Riepilogo Copertura Test Pre vs Post

### Backend

| Area | Test pre-piano | Test post-piano |
|------|---------------|----------------|
| Asset CRUD | 19 | 19 (invariato) |
| Asset metadata | 4 | 4 (invariato) |
| Asset patch | 8 | 8 (invariato) |
| Asset provider | 14 | 16 (+scheduled_investment, +probe errato) |
| Asset prices | 6 | 9 (+idempotenza, +eventi, +bulk sync) |
| Countries | 5 | 5 (invariato) |
| **Totale asset** | **56** | **61** |

### Frontend E2E

| Area | Test pre-piano | Test post-piano |
|------|---------------|----------------|
| Asset list | 0 | ~10 |
| Asset detail | 0 | ~12 |
| Asset modal | 0 | ~8 |
| Gallery assets | 0 | ~8 scene × 8 combo = ~64 screenshot |
| **Totale** | **0** | **~30 test + ~64 screenshot** |

