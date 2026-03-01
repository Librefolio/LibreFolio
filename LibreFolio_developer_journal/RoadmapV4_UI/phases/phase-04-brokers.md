# Phase 4: Brokers Management

**Status**: ✅ COMPLETATO  
**Durata**: 45+ giorni (originariamente pianificato 3 — espanso enormemente con consolidamento, Image Crop, Component Reorg, Data Separation, MkDocs Gallery, Broker Sharing)  
**Priorità**: P0 (MVP)  
**Dipendenze**: Phase 3  
**Ultimo aggiornamento**: 1 Marzo 2026

> **📌 Dettagli completi**: Vedere [plan-phase04-summary.md](phase-04-subplan/plan-phase04-summary.md) per il riepilogo di tutto il lavoro svolto,
> inclusi 28+ sub-plan, 109+ E2E test, Image Crop, ModalBase, code dedup, e Broker Sharing GUI con ECharts.

---

## Obiettivo

Implementare la gestione completa dei broker: lista, creazione, modifica, vista dettaglio con cash balances, holdings, BRIM import, e sistema di condivisione multi-utente (OWNER/EDITOR/VIEWER).

---

## ⚠️ Riferimento Phase 9

Se vengono creati componenti riutilizzabili, seguire le linee guida in [Phase 9: Polish](./phase-09-polish.md) e aggiornare quella fase con i dettagli del componente.

---

## Step Completati

### 4.1 Brokers List Page ✅

- [x] `src/routes/(app)/brokers/+page.svelte` — Lista card broker
- [x] `src/lib/components/brokers/BrokerCard.svelte` — Card con icona, nome, cash balances, holdings count, role badge
- [x] Button Add/Edit/Delete con conferme
- [x] BrokerCard cliccabile ovunque (navigazione al dettaglio)
- [x] Hover animation, filtri e ricerca
- [x] **Role badge**: icona colorata con ruolo utente (OWNER/EDITOR/VIEWER) su ogni card
- [x] **Responsive**: nome broker troncato se necessario su mobile

**API**: `GET /api/v1/brokers` (lista con access info per l'utente corrente)

### 4.2 Add/Edit Broker Modal ✅

- [x] `BrokerForm.svelte` — Form riutilizzabile con tutti i campi
- [x] Validazione client-side
- [x] Initial balances multi-currency con SearchSelect
- [x] Prima valuta suggerita = default currency utente
- [x] Import plugin selector (`ImportPluginSelect`) con icone e ricerca
- [x] Toggle per Conto Attivo, Leva, Short
- [x] Data apertura default = oggi
- [x] Conferma se si chiude modal con modifiche non salvate
- [x] Form reattivo a `initialData` (fix edit da detail page)
- [x] `ModalBase.svelte` usato come base

**API**: `POST /api/v1/brokers` (crea), `PATCH /api/v1/brokers` (modifica)

### 4.3 Broker Detail Page ✅

- [x] `src/routes/(app)/brokers/[id]/+page.svelte` — Dettaglio completo
- [x] Header con `BrokerIcon`, nome, pulsanti Edit/Share/Portal/Refresh
- [x] **Cash Balances**: card per valuta con Deposit/Withdraw
- [x] **Holdings**: tabella con asset, quantità, costo, valore, P&L
- [x] **Recent Transactions**: ultime transazioni
- [x] **Import Files**: sezione BRIM con upload rapido
- [x] **Broker Info**: card con metadata (stato, leva, short, data creazione)
- [x] **Role badge**: badge in header che mostra il ruolo dell'utente corrente
- [x] **VIEWER gating**: pulsanti Edit, Deposit, Withdraw disabilitati per VIEWER
- [x] **Responsive mobile**: layout 2×2 per pulsanti azione su mobile (Edit, Share sopra; Portal, Refresh sotto), icone centrate

**API**: `GET /api/v1/brokers/{id}/summary`, `GET /api/v1/transactions?broker_id={id}`

### 4.4 BrokerIcon Component ✅

- [x] Fallback chain: `icon_url` → `portal_url` favicon → plugin icon API → Briefcase
- [x] Reattivo e gestisce errori automaticamente
- [x] Plugin icon caricato senza flash fallback (timing fix)
- [x] `imageKey` + `{#key}` per forzare re-render

### 4.5 BRIM Multi-User Integration ✅

> **Piano dettagliato**: `phase-04-subplan/plan-brim-multiuser-implementation.md`

- [x] `broker_id` obbligatorio all'upload
- [x] `uploaded_by_user_id` per tracciare chi ha caricato
- [x] Permessi basati su ruolo (EDITOR+ per upload/parse/delete)
- [x] Sottocartelle broker per organizzazione file
- [x] Caching risultato parsing nel metadata JSON
- [x] Endpoint `GET /files/{id}/last-parse`
- [x] Frontend: modale assegnazione broker per-file, colonna broker con badge colorati
- [x] VIEWER non può selezionare broker in Files page (grigio, non cliccabile)
- [x] 22 test API BRIM passati

### 4.6 DataTable Component Suite ✅

> **Piano dettagliato**: `phase-04-subplan/plan-table-improvements.md`

- [x] `DataTable.svelte` generico con TanStack Table v8
- [x] Sorting, filtri Excel-style (text, enum, number, size, date)
- [x] Column resize con localStorage persistence
- [x] Column visibility toggle, reorder (drag + mobile buttons)
- [x] Row selection con bulk operations
- [x] Pagination sticky, page sizes, infinite mode
- [x] `FileUploader.svelte` — Upload multiplo con validazione

### 4.7 Zodios Migration ✅

> **Piano dettagliato**: `phase-04-subplan/plan-types-library.md`

- [x] Client API migrato da manuale a Zodios
- [x] Tipi TypeScript derivati da Zod schemas
- [x] Validazione runtime risposte API
- [x] Fix datetime serialization con `UTCDateTime`

### 4.8 Frontend Testing Infrastructure ✅

> **Piano dettagliato**: `phase-04-subplan/plan-frontendTesting.md`

- [x] Playwright configurato con progetti desktop/mobile
- [x] `data-testid` su tutti i componenti interattivi
- [x] Helper: `loginAs()`, `navigateTo()`, `setTheme()`, `setLanguage()`
- [x] `dev.py test front <action>` — CLI integrata
- [x] Test dinamici per lingue (auto-generati da file i18n)
- [x] 109+ test E2E suddivisi in 8 suite: auth, settings, files, brokers, multi-user, select-components, image-crop, broker-sharing

### 4.9 Component Reorganization ✅

> **Piano dettagliato**: `phase-04-subplan/plan-componentReorganizationV2.prompt.md` + V3

- [x] Famiglia Select unificata: `ui/select/` con BaseDropdown, SimpleSelect, SearchSelect
- [x] LanguageSelector, ImportPluginSelect, BrokerSearchSelect
- [x] SettingToggle, SettingNumber per GlobalSettings
- [x] Riorganizzazione cartelle: `ui/input/`, `ui/media/`, `layout/`, `settings/tabs/`
- [x] Fix file upload (Zodios FormData bug → uso axiosInstance)
- [x] Dashboard dark mode fix (`libre-banner`)

### 4.10 Data Separation prod/test ✅

> **Piano dettagliato**: `phase-04-subplan/plan-data-separation.md`

- [x] `backend/data/prod/` e `backend/data/test/` completamente isolati
- [x] `config.py`: `get_data_dir()`, `get_uploads_dir()`, `ensure_data_dirs()`
- [x] Tutti i servizi usano path dinamici basati su `LIBREFOLIO_TEST_MODE`
- [x] Script migrazione dati

### 4.11 Image Crop Component ✅

> **Piano dettagliato**: `phase-04-subplan/plan-imageCropModal.prompt.md`

- [x] `cropperjs v2` — crop interattivo con zoom, rotate, flip
- [x] `ImageCropper.svelte`, `ImageEditModal.svelte`, `FileEditModal.svelte`
- [x] `AssetPickerModal.svelte` — picker URL/Existing/Upload con DataTable single-select
- [x] `ImagePickerWrapper.svelte` — wrapper flusso completo
- [x] `ModalBase.svelte` — componente base per tutte le modali del progetto
- [x] Integrazione: Files Page, Broker Icon, Avatar Utente
- [x] Avatar visibile in Sidebar con link a Settings
- [x] 42 test E2E in `e2e/image-crop.spec.ts`

### 4.12 MkDocs Gallery & Dark Mode ✅

> **Piano dettagliato**: `phase-04-subplan/plan-settings-mobile-gallery.md`

- [x] Gallery Playwright: screenshot automatici per documentazione (19 test, ~280+ screenshot)
- [x] 4 lingue × 2 temi × 2 viewport = copertura completa
- [x] `gallery-img-loader.js` con fallback lingua automatico
- [x] MkDocs dark mode allineato con variabili frontend
- [x] Sidebar, header, tabs, admonitions stilizzati per dark mode
- [x] `dev.py mkdocs gallery [-f FILTER] [--list]` — CLI con filtro test

### 4.13 Config & Schema Cleanup ✅

- [x] `.env` pulito: `LIBREFOLIO_DATA_DIR`, sezioni prod/test separate
- [x] `config.py`: `get_version()` da git, `PROJECT_NAME` e `API_V1_PREFIX` come costanti
- [x] `BaseListResponse[T]`, `BaseBulkResponse[T]` standardizzati in `schemas/common.py`
- [x] `count` rimosso da tutte le response (usa `len(items)` lato consumer)
- [x] `UploadListResponse`, `FXCurrenciesResponse`, ecc. migrati a classi comuni

### 4.14 Broker Sharing GUI (Phase 4.8) ✅

> **Piano dettagliato**: `phase-04-subplan/plan-brokerSharing.md`

**Backend**:
- [x] `GET /api/v1/users/search` — ricerca utenti per username
- [x] `PUT /api/v1/brokers/{id}/access` — bulk update accessi (`List[BRAccessBulkItem]`)
- [x] `share_percentage` validato ≤ 100% (somma per broker), stored come fraction 0-1 nel DB
- [x] CHECK constraint DB su `share_percentage` (0 ≤ x ≤ 1)
- [x] `avatar_url` in `BRAccessItem`, `user_role` in `BRSummary`

**Frontend**:
- [x] `BrokerSharingModal.svelte` — modale configurazione accessi
- [x] **Half-Donut Chart** (Apache ECharts): distribuzione ownership con avatar circolari sugli archi
- [x] **3-column layout**: Owners (con %), Editors, Viewers — badge cliccabili per edit
- [x] **Add User Modal**: ricerca utente (SearchSelect style), selezione ruolo, share%
- [x] **Edit User Modal**: modifica ruolo e share%, delete access
- [x] **BATCH SAVE**: tutte le modifiche locali, invio con PUT unico
- [x] Warning banner sopra se somma > 100%
- [x] Success toast / Error banner
- [x] Dark mode completo
- [x] Bottone "Share" in broker detail (solo OWNER visibile)
- [x] VIEWER gating completo in broker detail e Files page

**DB Populate**:
- [x] 8 utenti test con avatar
- [x] Coinbase: 3 OWNER + 2 EDITOR + 3 VIEWER per demo
- [x] 2 utenti "liberi" per test add-user

**i18n**: 30+ chiavi `brokers.sharing.*` in 4 lingue

**E2E Test**: 15 test in `e2e/broker-sharing.spec.ts`

**Gallery**: screenshot `sharing-modal` in tutte le lingue/temi

---

## 🐛 Bug Fix Risolti

Durante Phase 4 sono stati risolti 19+ bug organizzati in 4 round. I principali:

| ID | Area | Descrizione | Status |
|---|---|---|---|
| BUG-001 | Backend | Messaggio errore broker duplicato | ✅ |
| BUG-002 | Frontend | BrokerSelect icona errata durante ricerca | ✅ |
| BUG-003 | Frontend | Max upload size hardcoded "10MB" | ✅ |
| BUG-004 | i18n | Bytes in francese: KB→Ko, MB→Mo, GB→Go | ✅ |
| BUG-005 | Docs | MkDocs dark mode non allineato | ✅ |
| BUG-008 | Backend | Broker altri utenti GDPR | ⏸️ (coperto da Broker Sharing) |
| BUG-009 | Backend | 404 su refresh broker detail (SPA routing) | ✅ |

---

## 📊 Metriche Finali

| Metrica | Valore |
|---|---|
| Sub-plan creati | 28+ |
| Test E2E | 109+ (8 suite) |
| Screenshot gallery | ~280+ |
| Lingue supportate | 4 (EN, IT, FR, ES) |
| Componenti UI creati | 30+ |
| Bug risolti | 19+ |
| Endpoint API | 84+ |

---

## 📁 Sub-Plan in `phase-04-subplan/`

| File | Descrizione | Status |
|---|---|---|
| `plan-phase04-summary.md` | Riepilogo completo Phase 4 con step dettagliati | ✅ |
| `plan-brokerSharing.md` | GUI condivisione broker con ECharts | ✅ |
| `plan-brim-multiuser-implementation.md` | BRIM multi-utente | ✅ |
| `plan-imageCropModal.prompt.md` | Image Crop Modal sistema | ✅ |
| `plan-image-crop.md` | Piano iniziale Image Crop | ✅ |
| `plan-componentReorganizationV2.prompt.md` | Famiglia Select unificata | ✅ |
| `plan-componentReorganizationV3-cleanup.md` | Cleanup + test Select | ✅ |
| `plan-data-separation.md` | Separazione dati prod/test | ✅ |
| `plan-settings-mobile-gallery.md` | Settings mobile + Gallery | ✅ |
| `plan-frontendTesting.md` | Infrastruttura test Playwright | ✅ |
| `plan-e2e-test-remediation.md` | Remediation test E2E | ✅ |
| `plan-files-ux-refactor.md` | Refactor UX Files page | ✅ |
| `plan-i18n-cli-improvements.md` | CLI traduzioni | ✅ |
| `plan-table-improvements.md` | DataTable TanStack | ✅ |
| `plan-settings-unification.md` | Unificazione Settings | ✅ |
| `plan-types-library.md` | Zodios migration | ✅ |
| `plan-ui-fixes.md` | Bug UI + versioning | ✅ |
| `plan-broker-icon-auth-fix.md` | Fix icone e auth | ✅ |
| `plan-bulk-download-v2.md` | Bulk download (low priority) | 📋 |
| `analysis-brim-multiuser.md` | Analisi BRIM | ✅ |
| `analysis-code-duplication.md` | Analisi code dedup | ✅ |
| `analysis-db-populate.md` | Analisi DB populate | ✅ |
| `e2e-test-analysis.md` | Analisi test E2E | ✅ |
| `GUIDA-DARK-MODE.md` | Guida variabili dark mode | ✅ |

---

## Dipendenze

- **Richiede**: Phase 3 (Layout)
- **Sblocca**: Phase 5 (FX Management) — `plan-phase05-to-08-upgrade.md` §4

---

## 📚 Contesto per Agent

Quando si lavora su fix/miglioramenti di Phase 4:

| Scenario | Files da allegare |
|---|---|
| Overview | `phase-04-subplan/plan-phase04-summary.md` |
| BRIM/Files | `+ phase-04-subplan/plan-brim-multiuser-implementation.md` |
| Tipi/API | `+ phase-04-subplan/plan-types-library.md` |
| Test E2E | `+ phase-04-subplan/plan-frontendTesting.md` |
| Select components | `+ phase-04-subplan/plan-componentReorganizationV2.prompt.md` |
| Image upload | `+ phase-04-subplan/plan-imageCropModal.prompt.md` |
| Broker Sharing | `+ phase-04-subplan/plan-brokerSharing.md` |
| Separazione dati | `+ phase-04-subplan/plan-data-separation.md` |

---

## ✅ Checklist Pre-Commit

- [x] `./dev.py front build` senza errori
- [x] `./dev.py front check` 0 errori
- [x] `./dev.py i18n audit` — 100% coverage
- [x] `./dev.py test front all` — 8/8 suite passano (109+ test)
- [x] `./dev.py test api all` — 17/17 suite passano
- [x] `./dev.py mkdocs gallery` — tutti gli screenshot generati
- [x] `./dev.py mkdocs build` — documentazione buildata senza errori
