# Plan: Documentation Audit — Phase 06 Step 4 Part A (Post-Assets)

> Base tag: `v0.5.9` → HEAD (34 commit, 220 file, +32K righe)
> EN-only — translations deferred to LLM pipeline
> **Status: ✅ COMPLETED** (April 9, 2026)

---

## Block 1 — `installation.en.md`: rimuovere creazione utente CLI ✅
**Priorità: ALTA** | **Effort: piccolo**

- **File**: `mkdocs_src/docs/user/installation.en.md`
- Rimuovere **Step 6** (CLI user creation `docker compose exec ... user create`)
- Rinumerare Step 7 → Step 6 ("Access LibreFolio")
- Aggiungere nota: "Il primo utente si crea direttamente dalla pagina di registrazione nel browser"
- Aggiungere admonition `!!! tip` con link all'Admin Manual per gestione utenti da CLI

---

## Block 2 — `dev-installation.md`: chiarire creazione utente ✅
**Priorità: ALTA** | **Effort: piccolo**

- **File**: `mkdocs_src/docs/developer/dev-installation.md`
- Nella sezione utenti, specificare: "Il primo utente può essere creato dal frontend. Il CLI è necessario per promuovere un utente ad admin (`./dev.py user promote <username>`)."
- Verificare che `user promote` esista in dev.py, altrimenti descrivere il workflow corretto

---

## Block 3 — `assets/index.en.md`: ristrutturazione in sub-file (stile FX) ✅
**Priorità: CRITICA** | **Effort: grande**

### 3a. Ridurre `assets/index.en.md` a overview
- Aggiungere screenshot lista asset in cima
- Ridurre a: What is an Asset, Asset List overview, links alle sotto-pagine
- Modello: `fx/index.en.md` (36 righe)

### 3b. Creare nuovi file

| File | Contenuto | Modello FX |
|------|-----------|------------|
| `assets/create-edit.en.md` | Creazione asset step-by-step, editing, test provider, fetch interval | — |
| `assets/detail/index.en.md` | Overview pannelli: chart, signals, measures, classification, data editor | `fx/detail/index.en.md` |
| `assets/detail/chart.en.md` | Date range filter, currency selector, abs/% toggle, event markers | `fx/detail/chart.en.md` |
| `assets/detail/signals.en.md` | EMA, MACD, RSI, Bollinger, Asset Comparison — intro + link financial-theory | `fx/detail/signals.en.md` |
| `assets/detail/measures.en.md` | Measure tool click-to-click | `fx/detail/measures.en.md` |
| `assets/detail/classification.en.md` | Sector pie, geographic map, geographic pie | — (nuovo) |
| `assets/detail/data-editor.en.md` | Pannello Edit Data | `fx/detail/data-editor.en.md` |
| `assets/detail/events.en.md` | AssetEvent vs Transaction, tipi, marker sul chart | — (nuovo) |

### 3c. Aggiornare `mkdocs.yml` nav
```yaml
- Assets:
    - Overview: user/assets/index.md
    - Create & Edit: user/assets/create-edit.md
    - Asset Detail:
        - Overview: user/assets/detail/index.md
        - Interactive Chart: user/assets/detail/chart.md
        - Signals: user/assets/detail/signals.md
        - Measures: user/assets/detail/measures.md
        - Classification: user/assets/detail/classification.md
        - Data Editor: user/assets/detail/data-editor.md
        - Events: user/assets/detail/events.md
    - Providers:
        - Overview: user/assets/providers/index.md
        - Yahoo Finance: user/assets/providers/yahoo-finance.md
        - justETF: user/assets/providers/justetf.md
        - CSS Scraper: user/assets/providers/css-scraper.md
        - Scheduled Investment: user/assets/providers/scheduled-investment.md
```

### Dipendenze source
- `frontend/src/routes/(app)/assets/[id]/+page.svelte` — pannelli disponibili
- `backend/app/db/models.py` — `AssetEventType` enum
- `fx/detail/signals.en.md` — template per link financial-theory

---

## Block 4 — `docker_advanced.en.md`: sezione demo compose ✅
**Priorità: MEDIA** | **Effort: piccolo**

- **File**: `mkdocs_src/docs/admin/docker_advanced.en.md`
- Aggiungere sezione `## 🎮 Demo Deployment` dopo Test Mode
- Includere `docker-compose.yml` completo come code block commentato
- Spiegare come personalizzare: porta, volume path, base currency, log level
- Nota: primo utente creabile da frontend

---

## Block 5 — `assets_pricing.md`: aggiungere `ASSET_EVENT` al ER diagram ✅
**Priorità: ALTA** | **Effort: piccolo**

- **File**: `mkdocs_src/docs/developer/architecture/database/assets_pricing.md`
- Aggiungere relazione `ASSET ||--o{ ASSET_EVENT : "has events"` nel diagramma Mermaid
- Aggiungere entità `ASSET_EVENT` con campi: id, asset_id, date, type (enum), value, currency, provider_assignment_id, notes
- Aggiungere sezione `### 📅 ASSET_EVENT` con spiegazione semantica (eventi asset-level vs transazioni)
- **Source**: `backend/app/db/models.py` righe 719-764

---

## Block 6 — Developer backend docs: review e allineamento ✅
**Priorità: ALTA** | **Effort: medio** | **Status: ✅ COMPLETED** (April 10, 2026)

Completato nella sessione del 10 Aprile 2026:

- Riscritto `architecture.md`: 3-phase sync pipeline, 18-endpoint API table, provider probe, cache/performance
- Creato `events.md`: event types con emoji, Mermaid ER, dedup strategy, auto-generated events
- Creato pagine per-provider: `provider_yahoo_finance.md`, `provider_justetf.md` (nuovi), riscritti `provider_cssscraper.md`, `provider_scheduled_investment.md`
- Mergiato `system_providers.md` + `providers_list.md` in unica overview page
- Aggiornato `asset_plugin_guide.md`: Mermaid orizzontale, optional methods, SSE streaming search, probe
- Aggiornato test walkthrough: api.md test counts, services.md nuove descrizioni
- Docker: env_file + bind mount in compose, .env check in dev.py, riscritto docker_advanced.en.md, aggiornato installation.en.md e README.md

### 6a. `architecture.md`
- Verificare `AssetSourceManager` vs +636 righe in `asset_source.py`
- Aggiornare event sync flow nel diagramma Mermaid
- Verificare `AssetEvent Table` — aggiungere MATURITY_SETTLEMENT e SPLIT se mancanti
- Aggiungere nota su cache redesign (`cache_utils.py` +154)

### 6b. `system_providers.md`
- Sezione Scheduled Investment vs +1127 righe di rewrite
- Verificare campi: compounding frequency, day count, late interest, MATURITY_SETTLEMENT
- Verificare formula prezzo (riga 54)

### 6c. `providers_list.md`
- Verificare feature di ogni provider (Yahoo +88, justETF +68, CSS +37)
- Yahoo Finance supporta eventi/dividendi? Aggiornare tabella

### Source da leggere
- `asset_source.py`, `scheduled_investment.py`, `yahoo_finance.py`, `justetf.py`, `css_scraper.py`, `cache_utils.py`

---

## Block 7 — Gallery: navigare ad Apple Inc. ✅
**Priorità: ALTA** | **Effort: medio**

- **File**: `frontend/e2e/gallery.spec.ts` sezione Assets (righe 1025-1273)
- **File**: `frontend/e2e/assets/assets-helpers.ts`
- In tutti i 6 test detail, sostituire `.first()` con navigazione ad Apple Inc.
- Approccio: cercare "Apple" nel campo search → click prima card risultante
- Creare helper `goToAppleDetailPage(page)` in `assets-helpers.ts`
- Apple ha 30 giorni di price history → chart saranno popolati
- **Rigenerare**: tutti screenshot `assets/` (8 scene × 4 lang × 2 theme × 2 viewport = 128 screenshot)

---

## Block 8 — Logo & Favicon rework ✅
**Priorità: MEDIA** | **Effort: medio** | **Completato: 2026-04-09**

### 8a. Favicon generation
- Logo `logo.png` è 765×944 (non quadrato) → usato anche come favicon → distorto nel browser tab e in Settings
- Creata `generate_favicon()` in `dev.py`: centra in quadrato trasparente + resize 48×48
- Chiamata automaticamente in `cmd_fe_build()` e `copy_docs_assets()`

### 8b. Logo container — white square everywhere
- Il logo non quadrato va incorniciato in un **contenitore quadrato bianco** (`style="background:#fff"`)
- Necessario `style` inline perché `bg-white` di Tailwind viene sovrascritto da `html.dark .bg-white { ... !important }` in `app.css`
- Applicato a: `app.html` splash (80×80), `Sidebar.svelte` (32×32), `LoginCard` / `RegisterCard` / `ForgotPasswordCard` (40×40), `AboutTab` (56×56)
- MkDocs: `extra.css` con `aspect-ratio: 1/1`, `background: #fff`, `border-radius`, `padding` per header, homepage e burger menu mobile

### 8c. Tailwind 4 dark mode fix
- Aggiunto `@custom-variant dark (&:where(.dark, .dark *));` in `app.css`
- Senza questa riga, le utility `dark:` di Tailwind 4 usano `@media prefers-color-scheme` anziché la classe `html.dark`

### 8d. Rimossa griglia asset-icons dalle homepage MkDocs
- Rimosse le 8 card asset-type icon (Stocks, ETFs, Crypto, Bonds, P2P, Funds, Commodities, Other) da `index.en.md`, `index.it.md`, `index.fr.md`, `index.es.md`

### 8e. Cleanup logo_black.png
- Tentato approccio dual-logo (`logo_black.png` per dark mode) — abbandonato per complessità e incompatibilità cross-browser (`content: url()` non funziona in Firefox su `<img>`)
- Rimossi tutti i riferimenti a `logo_black.png` da: `app.html`, `Sidebar.svelte`, `extra.css`, `app-sync.js`, `dev.py copy_docs_assets()`

### Files modified
- `frontend/src/app.html` — splash screen con contenitore quadrato bianco
- `frontend/src/app.css` — `@custom-variant dark`
- `frontend/src/lib/components/layout/Sidebar.svelte` — logo in quadrato bianco
- `frontend/src/lib/components/auth/LoginCard.svelte` — logo in quadrato bianco
- `frontend/src/lib/components/auth/RegisterCard.svelte` — logo in quadrato bianco
- `frontend/src/lib/components/auth/ForgotPasswordCard.svelte` — logo in quadrato bianco
- `frontend/src/lib/components/settings/tabs/AboutTab.svelte` — logo in quadrato bianco
- `frontend/static/favicon.png` — rigenerato 48×48
- `mkdocs_src/docs/static/extra.css` — logo quadrato bianco per header, homepage, burger menu
- `mkdocs_src/docs/javascripts/app-sync.js` — rimossa `swapLogos()`
- `mkdocs_src/docs/index.{en,it,fr,es}.md` — rimossa griglia asset-icons
- `dev.py` — `generate_favicon()` + integrazione in build

---

## Block 9 — E2E Login fix ✅
**Priorità: ALTA** | **Effort: piccolo** | **Completato: 2026-04-09**

- `frontend/e2e/fixtures/auth-helpers.ts`: login verification cambiato da `toHaveURL(/.*dashboard.*/)` a `expect(login-page).not.toBeVisible()` — più robusto su mobile dove il redirect URL può variare

---

## Ordine di esecuzione (completato)

```
Block 5 (ER diagram)           → ✅
Block 1 (installation)         → ✅
Block 2 (dev-installation)     → ✅
Block 7 (Gallery Apple)        → ✅
Block 9 (E2E login fix)        → ✅
Block 3 (Restructure assets)   → ✅
Block 4 (Docker demo compose)  → ✅
Block 8 (Logo & Favicon)       → ✅
Block 6 (Dev docs review)      → ✅ (April 10, 2026)
```

---

## Note

- **Eventi nel frontend**: `AssetEvent` appare solo come `EventMarker` sul chart — non esiste un pannello "Events" dedicato. La pagina `events.en.md` documenta i marker + la configurazione nel Scheduled Investment Editor
- **Provider docs utente**: `scheduled-investment.en.md` (70 righe) va verificata contro le 1127 righe di rewrite
- **Traduzioni**: solo EN. Pipeline Aphra per it/fr/es in un secondo momento

