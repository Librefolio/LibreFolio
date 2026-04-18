# Plan: Frontend Development - LibreFolio UI

**Data Creazione**: 8 Gennaio 2026
**Ultimo Aggiornamento**: 6 Febbraio 2026
**Versione**: 4.0 (Aggiornato con stato Phase 4 e deviazioni)
**Target**: Implementazione completa UI per LibreFolio
**Status**: 🟡 PHASE 4 IN PROGRESS - Step 4.4 (Data Separation) completato

---

## 📊 Overview

Questo documento è l'indice principale del piano frontend. Ogni fase ha il proprio file dettagliato nella cartella `phases/`.

**📁 Sotto-Plan Dettagliati**: [`phases/`](./phases/)
**📁 Phase 4 Sub-Plans**: [`phases/phase-04-subplan/`](./phases/phase-04-subplan/)
**📄 Phase 4 Summary**: [`plan-phase04-summary.md`](./phases/phase-04-subplan/plan-phase04-summary.md)

---

## 🔧 Stack Tecnologico

```json
{
  "framework": "SvelteKit 2.48+",
  "styling": "Tailwind CSS 4.1+ (via @theme in CSS)",
  "charts": "Apache ECharts 5.5+ (da implementare)",
  "state": "SvelteKit load functions + Svelte Stores + Runes ($state, $derived)",
  "api_client": "Zodios (type-safe, OpenAPI-generated)",
  "validation": "Zod (auto-generated da OpenAPI)",
  "dates": "date-fns 3.0+",
  "icons": "lucide-svelte 0.559+ + custom SVG",
  "i18n": "svelte-i18n 4.0+ (en/it/fr/es)",
  "testing": "Playwright (E2E) + Vitest (unit)"
}
```

---

## 📐 Design System

| Elemento       | Valore                             |
|----------------|------------------------------------|
| **Primary**    | Dark Forest Green (#1a4031)        |
| **Accent**     | Mint Green (#A8D5BA)               |
| **Background** | Cream/Beige (#f5f4ef)              |
| **Banner**     | libre-banner (dark mode dashboard) |
| **Text**       | Dark Grey (#2C2C2C)                |
| **Layout**     | Sidebar + Main Content             |
| **Responsive** | Mobile-first                       |

**Riferimento**: [`phases/phase-04-subplan/GUIDA-DARK-MODE.md`](./phases/phase-04-subplan/GUIDA-DARK-MODE.md)

---

## 📋 Fasi di Sviluppo

| Fase    | Nome                        | Status         | Link Dettagli                                                               | Giorni |
|---------|-----------------------------|----------------|-----------------------------------------------------------------------------|--------|
| **0**   | Setup & Build Integration   | ✅ COMPLETATA   | [→ phase-00-setup.md](./phases/phase-00-setup.md)                           | 1      |
| **1**   | Foundation & Frontend Auth  | ✅ COMPLETATA   | [→ phase-01-foundation.md](./phases/phase-01-foundation.md)                 | 3      |
| **2**   | Backend Authentication      | ✅ COMPLETATA   | [→ phase-02-backend-auth.md](./phases/phase-02-backend-auth.md)             | 3      |
| **2.5** | Auth Integration (FE ↔ BE)  | ✅ COMPLETATA   | [→ phase-02.5-auth-integration.md](./phases/phase-02.5-auth-integration.md) | 1      |
| **3**   | Layout & Settings           | ✅ COMPLETATA   | [→ phase-03-layout-settings.md](./phases/phase-03-layout-settings.md)       | 1      |
| **3.5** | Settings System (Glob+Pers) | ✅ COMPLETATA   | [→ phase-03.5-settings-system.md](./phases/phase-03.5-settings-system.md)   | 2.5    |
| **4**   | Brokers Management          | 🔄 IN PROGRESS | [→ phase-04-brokers.md](./phases/phase-04-brokers.md)                       | 3+     |
| **5**   | FX Management               | ⏳ TODO         | [→ phase-05-fx.md](./phases/phase-05-fx.md)                                 | 3      |
| **6**   | Assets Management           | ⏳ TODO         | [→ phase-06-assets.md](./phases/phase-06-assets.md)                         | 4      |
| **7**   | Transactions Management     | ⏳ TODO         | [→ phase-07-transactions.md](./phases/phase-07-transactions.md)             | 5      |
| **8**   | Dashboard                   | ⏳ TODO         | [→ phase-08-dashboard.md](./phases/phase-08-dashboard.md)                   | 3      |
| **9**   | Polish & Responsive         | 🔄 ONGOING     | [→ phase-09-polish.md](./phases/phase-09-polish.md)                         | 2      |

**Totale stimato**: ~6 settimane (~31 giorni)
**Tempo effettivo Phase 4**: ~2+ settimane (con tutte le deviazioni)

---

## 🔀 Deviazioni dal Piano Originale

La Phase 4 ha richiesto molto più lavoro del previsto a causa di diverse espansioni necessarie:

### 1. Zodios Migration (non pianificata)

- **Problema**: Client API manuale non type-safe
- **Soluzione**: Migrazione completa a Zodios con tipi auto-generati da OpenAPI
- **File**: [`phases/phase-04-subplan/plan-types-library.md`](./phases/phase-04-subplan/plan-types-library.md)

### 2. BRIM Multi-User System (espansione significativa)

- **Problema**: Il sistema BRIM era single-user
- **Soluzione**: Permessi Owner/Editor/Viewer, storage per broker, filtri multi-broker
- **Files**:
    - [`phases/phase-04-subplan/analysis-brim-multiuser.md`](./phases/phase-04-subplan/analysis-brim-multiuser.md)
    - [`phases/phase-04-subplan/plan-brim-multiuser-implementation.md`](./phases/phase-04-subplan/plan-brim-multiuser-implementation.md)

### 3. E2E Testing Infrastructure (non pianificata)

- **Problema**: Nessun test automatizzato frontend
- **Soluzione**: Playwright con 67+ test, gallery screenshot per docs
- **Files**:
    - [`phases/phase-04-subplan/plan-frontendTesting.md`](./phases/phase-04-subplan/plan-frontendTesting.md)
    - [`phases/phase-04-subplan/plan-e2e-test-remediation.md`](./phases/phase-04-subplan/plan-e2e-test-remediation.md)
    - [`phases/phase-04-subplan/e2e-test-analysis.md`](./phases/phase-04-subplan/e2e-test-analysis.md)

### 4. Component Reorganization (3 iterazioni)

- **Problema**: Componenti Select/Dropdown inconsistenti, warnings Svelte 5
- **Soluzione**: Famiglia Select unificata con BaseDropdown, migrazione a Runes
- **Files**:
    - [`phases/phase-04-subplan/plan-component-reorganization.md`](./phases/phase-04-subplan/plan-component-reorganization.md) (v1, archiviato)
    - [`phases/phase-04-subplan/plan-componentReorganizationV2.prompt.md`](./phases/phase-04-subplan/plan-componentReorganizationV2.prompt.md)
    - [`phases/phase-04-subplan/plan-componentReorganizationV3-cleanup.md`](./phases/phase-04-subplan/plan-componentReorganizationV3-cleanup.md)

### 5. Settings Mobile + Gallery (espansione UX)

- **Problema**: Layout settings non responsive, nessuna gallery per docs
- **Soluzione**: Layout 3-righe mobile, gallery con 224 screenshots light/dark
- **File**: [`phases/phase-04-subplan/plan-settings-mobile-gallery.md`](./phases/phase-04-subplan/plan-settings-mobile-gallery.md)

### 6. Data Separation prod/test (infrastruttura)

- **Problema**: Dati test e prod nella stessa cartella
- **Soluzione**: Separazione completa `backend/data/prod/` e `backend/data/test/`
- **File**: [`phases/phase-04-subplan/plan-data-separation.md`](./phases/phase-04-subplan/plan-data-separation.md)

### 7. i18n CLI Improvements (tooling)

- **Problema**: Gestione traduzioni manuale e error-prone
- **Soluzione**: CLI con audit, add, remove, update, search
- **File**: [`phases/phase-04-subplan/plan-i18n-cli-improvements.md`](./phases/phase-04-subplan/plan-i18n-cli-improvements.md)

### 8. Files UX Refactor (UX)

- **Problema**: Pagina Files poco usabile
- **Soluzione**: URL filters, bulk download, improved table
- **Files**:
    - [`phases/phase-04-subplan/plan-files-ux-refactor.md`](./phases/phase-04-subplan/plan-files-ux-refactor.md)
    - [`phases/phase-04-subplan/plan-table-improvements.md`](./phases/phase-04-subplan/plan-table-improvements.md)

---

## 📁 Phase 4 Sub-Plans Index

### Completati ✅

| File                                        | Descrizione                         |
|---------------------------------------------|-------------------------------------|
| `plan-brim-multiuser-implementation.md`     | BRIM multi-user con permessi broker |
| `plan-types-library.md`                     | Migrazione Zodios + tipi TypeScript |
| `plan-settings-unification.md`              | Unificazione settings UI            |
| `plan-broker-icon-auth-fix.md`              | Fix icone broker e auth             |
| `plan-table-improvements.md`                | Miglioramenti DataTable             |
| `plan-frontendTesting.md`                   | Infrastruttura test E2E Playwright  |
| `plan-i18n-cli-improvements.md`             | CLI per gestione traduzioni         |
| `plan-files-ux-refactor.md`                 | Refactor UX pagina Files            |
| `plan-e2e-test-remediation.md`              | Remediation test E2E                |
| `plan-settings-mobile-gallery.md`           | Settings mobile + Gallery           |
| `plan-componentReorganizationV2.prompt.md`  | Famiglia Select unificata           |
| `plan-componentReorganizationV3-cleanup.md` | Cleanup + test E2E Select           |
| `plan-data-separation.md`                   | Separazione dati prod/test          |

### Reference Docs 📚

| File                         | Descrizione                 |
|------------------------------|-----------------------------|
| `GUIDA-DARK-MODE.md`         | Guida variabili dark mode   |
| `analysis-brim-multiuser.md` | Analisi iniziale BRIM       |
| `analysis-db-populate.md`    | Analisi popolazione DB mock |
| `e2e-test-analysis.md`       | Gap analysis test E2E       |

### Da Implementare 📋 (in `RoadmapV4_UI/`)

| File                 | Descrizione                  | Priorità    |
|----------------------|------------------------------|-------------|
| `plan-ui-fixes.md`   | Bug UI scoperti durante test | 🔜 PROSSIMO |
| `plan-image-crop.md` | Componente crop immagini     | ALTA        |

---

## 🎯 Priorità Aggiornate

- **P0 (MVP)**: Phase 0 ✅, 1 ✅, 2 ✅, 2.5 ✅, 3 ✅, 3.5 ✅, 4 🔄, 6, 7
- **P1 (Important)**: Phase 5, 8
- **P2 (Ongoing)**: Phase 9 (fatto incrementalmente)

---

## 📅 Timeline Aggiornata

| Settimana | Fasi           | Status | Note                                 |
|-----------|----------------|--------|--------------------------------------|
| 1         | 0, 1, 2        | ✅      | Setup, Frontend Auth, Backend Auth   |
| 2         | 2.5, 3, 3.5    | ✅      | Auth Integration, Layout, Settings   |
| 3-4       | 4 (base)       | ✅      | Brokers base, BRIM upload            |
| 4-5       | 4 (espansioni) | ✅      | Zodios, E2E tests, Component reorg   |
| 5-6       | 4 (infra)      | ✅      | Data separation, Gallery, Mobile     |
| 6+        | 4 (fix) → 5    | 🔄     | UI fixes, Image crop → FX Management |

**Nota**: La Phase 4 ha richiesto ~4 settimane invece di 3 giorni a causa delle espansioni necessarie per qualità e manutenibilità.

---

## 🔗 Dipendenze tra Fasi (Aggiornato)

```
Phase 0-3.5 ✅ COMPLETATE
    ↓
Phase 4 (Brokers) 🔄 IN PROGRESS
    ├── BRIM Multi-User ✅
    ├── Zodios Migration ✅
    ├── E2E Testing ✅
    ├── Component Reorganization ✅
    ├── Data Separation ✅
    ├── UI Fixes 📋 TODO
    └── Image Crop 📋 TODO
            ↓
    Phase 5 (FX) ⏳ TODO
            ↓
    Phase 6 (Assets) ⏳ TODO
            ↓
    Phase 7 (Transactions) ⏳ TODO
            ↓
    Phase 8 (Dashboard) ⏳ TODO

Phase 9 (Polish) ← Fatto incrementalmente durante tutte le fasi
```

---

## ⚠️ Regole Importanti

### 1. Componenti Riutilizzabili

Ogni volta che si crea un componente che può essere riutilizzato:

- Seguire le linee guida in [Phase 9: Polish](./phases/phase-09-polish.md)
- Aggiornare quella fase con i dettagli del componente
- Creare in `src/lib/components/ui/` o sottocartelle appropriate

### 2. Famiglia Select Components

Usare la nuova gerarchia in `src/lib/components/ui/select/`:

- `BaseDropdown.svelte` - Base per tutti i dropdown
- `SimpleSelect.svelte` - Select senza ricerca
- `SearchSelect.svelte` - Select con ricerca fuzzy

### 3. Svelte 5 Runes

Preferire Runes ($state, $derived, $effect) per nuovi componenti:

```svelte
let value = $state<string>('');
let derived = $derived(value.toUpperCase());
```

### 4. Test E2E

Ogni nuova feature deve avere test E2E in `frontend/e2e/`:

- Usare `data-testid` per selettori stabili
- Verificare con `./dev.py test front all`

### 5. Traduzioni

Usare CLI per gestire traduzioni:

```bash
./dev.py i18n audit          # Verifica coverage
./dev.py i18n add "key" --en "..." --it "..."
./dev.py i18n search "query"
```

---

## ✅ Acceptance Criteria Globali

### Per ogni pagina:

- [x] Responsive (desktop + mobile)
- [x] Traduzioni en/it/fr/es complete
- [x] Loading states visibili
- [x] Error handling con toast
- [x] Success feedback con toast
- [ ] Accessibility (keyboard, ARIA) - parziale
- [x] Coerente con design system

### Per l'intero frontend:

- [x] `npm run build` senza errori
- [x] Static files serviti da FastAPI
- [x] Session cookie funzionante
- [x] Language setting sync con API
- [x] Protezione route (redirect login)
- [x] No errori console in production
- [x] E2E tests passano (67+ test)
- [x] Gallery screenshot (224 immagini)

---

## 📚 Riferimenti

| Risorsa           | Path                                             |
|-------------------|--------------------------------------------------|
| Phase 4 Summary   | `./phases/phase-04-subplan/plan-phase04-summary.md` |
| Phase 4 Sub-Plans | `./phases/phase-04-subplan/`                     |
| Design Guide      | `/artwork/Prompt_gemini.md`                      |
| Dark Mode Guide   | `./phases/phase-04-subplan/GUIDA-DARK-MODE.md`   |
| API Endpoints     | `./dev.py info api`                              |
| E2E Test Analysis | `./phases/phase-04-subplan/e2e-test-analysis.md` |

---

## 📝 Note di Sviluppo

### Comandi Utili (dev.py)

```bash
# Frontend development
./dev.py front dev       # Dev server con HMR
./dev.py front build     # Build production
./dev.py front check     # Type checking

# Backend con frontend
./dev.py server          # Prod mode (:8000)
./dev.py server --test   # Test mode (:8001)

# API Schema
./dev.py api schema      # Genera openapi.json
./dev.py api sync        # Schema + client TypeScript

# Testing
./dev.py test all        # Tutti i test (8 categorie)
./dev.py test front all  # Solo test frontend E2E

# Documentation
./dev.py mkdocs gallery  # Genera screenshot per docs
./dev.py mkdocs serve    # Preview docs locale

# Traduzioni
./dev.py i18n audit      # Verifica coverage traduzioni
./dev.py i18n add KEY --en "..." --it "..."
```

### Architettura Build

```
Development:
├── Backend:  ./dev.py server     → http://localhost:8000 (prod data)
├── Backend:  ./dev.py server --test → http://localhost:8001 (test data)
└── Frontend: ./dev.py front dev  → http://localhost:5173 (HMR)

Production:
└── Backend:  ./dev.py server     → http://localhost:8000
    ├── /api/v1/*  → FastAPI
    ├── /mkdocs/*  → Docs
    └── /*         → Frontend SPA

Data Structure:
├── backend/data/prod/   → Production data
│   ├── sqlite/app.db
│   ├── broker_reports/
│   ├── custom-uploads/
│   └── logs/
└── backend/data/test/   → Test data (isolated)
    └── (same structure)
```
