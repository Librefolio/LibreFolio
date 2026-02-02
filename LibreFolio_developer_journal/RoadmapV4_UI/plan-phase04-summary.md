# Phase 4 - Brokers Management: Summary & Next Steps

**Data creazione**: 30 Gennaio 2026  
**Status**: 🔄 IN PROGRESS (Bug fixes in corso, core features complete)

---

## 📋 Riepilogo Lavoro Svolto

### Obiettivo Originale

Implementare gestione completa dei broker: lista, CRUD, vista dettaglio con cash balances e holdings.

### Features Completate ✅

1. **Broker List Page** (`/brokers`)
    - Lista card broker con icona, cash balances, holdings count
    - Filtri e ricerca
    - Button Add/Edit/Delete

2. **Broker Detail Page** (`/brokers/[id]`)
    - Header con icona, nome, azioni
    - Cash balances con deposit/withdraw
    - Holdings table
    - Recent transactions
    - Import Files section (BRIM)

3. **Broker CRUD Operations**
    - Create con initial balances
    - Edit con conferma modifiche non salvate
    - Delete con conferma

4. **BrokerIcon Component**
    - Fallback chain: icon_url → portal favicon → plugin icon → Briefcase
    - Reattivo e gestisce errori automaticamente

5. **BRIM Multi-User Integration** (vedi `plan-brim-multiuser-implementation.md`)
    - Upload file associato a broker
    - Permessi basati su ruolo (OWNER/EDITOR/VIEWER)
    - Filtro multi-broker
    - Storage per sottocartelle broker

6. **Zodios Migration** (vedi `plan-types-library.md`)
    - Migrazione da client API manuale a Zodios
    - Tipi TypeScript derivati da Zod schemas
    - Validazione runtime delle risposte API
    - Fix datetime serialization con `UTCDateTime`

---

## 🔀 Deviazioni dal Piano Originale

1. **Zodios Migration**: Non prevista inizialmente, necessaria per type-safety e validazione
2. **BRIM Multi-User**: Espansa significativamente per supportare multi-utenza
3. **DataTable Component**: Creato componente riutilizzabile per tabelle con filtri avanzati
4. **BrokerSelect Component**: Creato per selezione broker con ricerca fuzzy e icone

---

## 🐛 Bug Risolti (Round 1-4)

| ID      | Descrizione                                           | Status   |
|---------|-------------------------------------------------------|----------|
| BUG-001 | Backend error message migliorato per broker esistente | ✅        |
| BUG-002 | Table: click badge counter per deselezionare          | ✅        |
| BUG-003 | BRIM upload: endpoint path corretto                   | ✅        |
| BUG-004 | FR Bytes: traduzione unità nei filtri                 | ✅        |
| BUG-005 | MkDocs dark mode CSS                                  | 🔲 TODO  |
| BUG-006 | Copy Link con feedback toast                          | ✅        |
| BUG-007 | Traduzioni broker import files                        | ✅        |
| BUG-008 | Broker altri utenti GDPR                              | ⏸️ PAUSA |
| BUG-009 | 404 su refresh broker detail                          | ✅        |
| BUG-010 | Filtro size slider inizializzazione                   | ✅        |
| BUG-011 | Global Settings max_file_upload_mb unit selector      | ✅        |
| BUG-012 | Copy Link path relativo + toast in alto               | ✅        |
| BUG-013 | BRIM upload endpoint in BrokerImportFiles             | ✅        |
| BUG-014 | Svelte warnings per prop capture in slider            | ✅        |
| BUG-015 | Reset Default max_file_upload_mb                      | ✅        |
| BUG-016 | Translation key files.upload → uploads.upload         | ✅        |
| BUG-017 | BRIM upload broker_id in query string                 | ✅        |
| BUG-018 | Translation key sbagliata per upload button           | ✅        |
| BUG-019 | Svelte warnings con svelte-ignore                     | ✅        |

---

## 📦 Bug/Improvements Pendenti

### 🔲 BUG-005: MkDocs Dark Mode (bassa priorità)

- I CSS della documentazione non sono allineati col frontend
- Colori simili ma diversi in dark mode

### ⏸️ BUG-008: Broker Altri Utenti - GDPR Rethink

- Superuser vede "Broker #N (other user)" per file di altri
- Richiede ripensamento GDPR-compliant del sistema permessi

---

## 📁 Organizzazione File Plan

### Plans Completati (in `phase-04-subplan/`)

| File                                    | Descrizione                           |
|-----------------------------------------|---------------------------------------|
| `plan-brim-multiuser-implementation.md` | ✅ BRIM multi-user con permessi broker |
| `plan-types-library.md`                 | ✅ Migrazione Zodios + tipi TypeScript |
| `plan-settings-unification.md`          | ✅ Unificazione settings UI            |
| `analysis-brim-multiuser.md`            | ✅ Analisi iniziale BRIM               |
| `plan-broker-icon-auth-fix.md`          | ✅ Fix icone broker e auth             |
| `plan-table-improvements.md`            | ✅ Miglioramenti DataTable             |
| `plan-phase4Consolidation.prompt.md`    | ✅ Consolidamento fase 4               |
| `GUIDA-DARK-MODE.md`                    | ✅ Guida variabili dark mode           |
| `plan-frontendTesting.md`               | ✅ Infrastruttura test E2E Playwright  |
| `plan-i18n-cli-improvements.md`         | ✅ CLI per gestione traduzioni         |
| `plan-files-ux-refactor.md`             | ✅ Refactor UX pagina Files            |

### Plans DA IMPLEMENTARE (in `RoadmapV4_UI/`)

| File                                 | Descrizione                            | Priorità    |
|--------------------------------------|----------------------------------------|-------------|
| `plan-e2e-test-remediation.md`       | Remediation test E2E per features      | P1          |
| `plan-image-crop.md`                 | Componente crop immagini con cropperjs | P2          |
| `plan-data-separation.md`            | Separazione cartelle dati prod/test    | P2          |
| `plan-frontendDevelopment.prompt.md` | Linee guida sviluppo frontend          | Riferimento |

### Plans DA CREARE

| Piano                              | Descrizione                          | Priorità |
|------------------------------------|--------------------------------------|----------|
| `plan-gdpr-permissions-rethink.md` | Ripensamento permessi GDPR-compliant | P3       |

---

## 🗺️ Step Completati

### Step 1: i18n CLI Improvements (30 min) ✅ COMPLETATO

**Riferimento**: `phases/phase-04-subplan/plan-i18n-cli-improvements.md`
**Obiettivo**: Aggiungere funzioni CLI per gestione traduzioni

- `./dev.py i18n add <key> --en <en> --it <it> --fr <fr> --es <es>` - Aggiunge chiave (tutte required)
- `./dev.py i18n remove <key>` - Rimuove chiave da tutte le lingue
- `./dev.py i18n update <key> [--en <en>] [--it <it>] [--fr <fr>] [--es <es>]` - Modifica traduzione
- `./dev.py i18n search <query>` - Cerca nelle traduzioni
- **Output formattato come tabelle** (miglioramento extra)

### Step 2: Files Page URL Filters (1h) ✅ COMPLETATO

**Riferimento**: `phases/phase-04-subplan/plan-files-ux-refactor.md` (Step 2)
**Obiettivo**: Permettere deep-linking ai filtri della pagina `/files`

- Sistema URL filters dinamico con `urlKey` per ogni colonna DataTable
- Creato `$lib/utils/urlFilters.ts` con utility parseUrlFilters/buildUrlFilters
- Aggiunto `initialFilters` e `onFiltersChange` props a DataTable e FilesTable
- URL params: `?tab=static|brim&filename=X&broker=1,2&status=Y&size=min-max&date=from,to`
- Lettura params da URL all'apertura pagina
- Aggiornamento URL quando si cambiano filtri (senza reload)
- **Fix extra**: Tab sempre in URL, focus preservato, matchMode in URL
- **Fix extra**: Custom `paramsSerializer` in Axios per formato array FastAPI (`key=1&key=2`)

### Step 3: Files UX Refactoring (1h) ✅ COMPLETATO

**Riferimento**: `phases/phase-04-subplan/plan-files-ux-refactor.md` (Step 3)
**Obiettivo**: Migliorare UX sezione import files in broker detail

- Creato `BrokerImportFilesModal.svelte` con DataTable integrato
- Filtra solo file del broker corrente (non più tutti i file)
- Colonna broker nascosta (implicita dal contesto)
- Upload auto-assegnati al broker corrente
- Sostituita sezione inline con bottone che apre modale
- Link "Gestisci tutti i file" → `/files?tab=brim&broker={id}`
- Sostituito tutte le chiamate `fetch()` dirette con client Zodios

### Step 4: Frontend Testing Infrastructure ✅ COMPLETATO

**Riferimento**: `phases/phase-04-subplan/plan-frontendTesting.md`
**Obiettivo**: Setup Playwright per test E2E automatici

- Playwright installato e configurato
- Test specs: auth, settings, files, brokers, multi-user, gallery
- Integrazione con `./dev.py test front [action] [test_names] [--ui|--headed|--debug]`
- Comando `./dev.py mkdocs gallery` per screenshot documentazione
- TEST_NAMES filtering con `--grep` di Playwright

### Step 4.1: E2E Test Remediation 📋 DA FARE

**Riferimento**: `plan-e2e-test-remediation.md`
**Obiettivo**: Aggiornare test E2E per coprire funzionalità implementate

- Aggiungere `data-testid` ai componenti frontend
- Riscrivere test per selettori realistici
- Ordine: auth → settings → files → brokers → multi-user
- Far passare tutti i test E2E
- Stima: ~7h

### Step 5: Image Crop Component (2h) 📋

**Riferimento**: `plan-image-crop.md`
**Obiettivo**: Componente avanzato crop/resize immagini

- Libreria: cropperjs (svelte-cropperjs)
- Aspect ratio forzato (1:1 per avatar, custom per altri)
- Preview in tempo reale
- Usabile per: avatar utente, icone broker, logo asset

### Step 6: Data Separation prod/test (2h) 📋

**Riferimento**: `plan-data-separation.md`
**Obiettivo**: Isolare completamente dati produzione e test

- `backend/data/prod/` vs `backend/data/test/`
- Configurazione automatica in base a `TEST_MODE`
- Script cleanup test data sicuro

### Step 7: MkDocs Dark Mode (30 min) 🔲

**Obiettivo**: Allineare CSS dark mode documentazione con frontend

- File: `mkdocs_src/docs/stylesheets/extra.css`
- Variabili colore coerenti con tema app

### Step 8: GDPR Permissions Analysis (planning only) ⏸️

**Obiettivo**: Documentare problematiche e proporre soluzioni

- File: `plan-gdpr-permissions-rethink.md`
- Analisi requisiti GDPR per accesso dati utenti
- Proposte architetturali

---

## 📚 Contesto per Agent

Quando si lavora su questa fase, allegare:

| Scenario         | Files da allegare                                                  |
|------------------|--------------------------------------------------------------------|
| Bug fix generici | `plan-phase04-summary.md`                                          |
| BRIM/Files       | `+ phases/phase-04-subplan/plan-brim-multiuser-implementation.md`  |
| Tipi/API         | `+ phases/phase-04-subplan/plan-types-library.md`                  |
| Test frontend    | `+ phases/phase-04-subplan/plan-frontendTesting.md`                |
| Test remediation | `+ plan-e2e-test-remediation.md`                                   |
| Image upload     | `+ plan-image-crop.md`                                             |
| Separazione dati | `+ plan-data-separation.md`                                        |
| i18n CLI         | `+ phases/phase-04-subplan/plan-i18n-cli-improvements.md`          |
| Files UX/URL     | `+ phases/phase-04-subplan/plan-files-ux-refactor.md`              |

---

## ✅ Checklist Pre-Commit

- [ ] `./dev.py front build` senza errori/warnings
- [ ] `./dev.py front check` senza errori
- [ ] `./dev.py i18n audit` - 100% coverage
- [ ] Test funzionale features modificate
- [ ] (Futuro) `./dev.py test front` - tutti i test passano
