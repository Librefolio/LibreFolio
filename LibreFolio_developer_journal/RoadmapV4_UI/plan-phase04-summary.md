# Phase 4 - Brokers Management: Summary & Next Steps

**Data creazione**: 30 Gennaio 2026  
**Ultimo aggiornamento**: 24 Febbraio 2026  
**Status**: 🟢 COMPLETATO (Core features, Image Crop, ModalBase migration, Auth rename, 42 E2E test, avatar seed, gallery, MkDocs dark mode.)

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

7. **E2E Test Infrastructure** (vedi `plan-frontendTesting.md`) ✅
    - Playwright configurato con progetti desktop/mobile
    - ~100 test passanti (5/5 suite)
    - Build check automatico prima dei test
    - Gallery screenshot per documentazione (28/28 test pass, ~224 screenshots)

8. **Image Crop Modal** (vedi `plan-imageCropModal.prompt.md`) ✅ NUOVO (19 Feb 2026)
    - Migrazione da svelte-easy-crop a cropperjs v2
    - Free crop con maniglie trascinabili (L-shaped)
    - Rotazione rispetto al centro selezione
    - Flip H/V, Zoom, Aspect ratio presets
    - Pulsante Edit/Restore in FileUploader
    - Conferma chiusura con modifiche non salvate
    - CSS Variables per Shadow DOM overlay

9. **DB Populate Enhancement** ✅ NUOVO (3 Feb 2026)
    - 6 broker con `brim_plugin_key` e `BrokerUserAccess`
    - 9 asset (stocks, ETFs, crypto, loans)
    - 24 transazioni realistiche
    - Price history per crypto (24/7, no weekend skip)

10. **Settings Mobile Layout** ✅ NUOVO (3 Feb 2026)
    - Dropdown custom per category selector
    - Layout 3 righe per ogni setting
    - CustomSelect component per select semplici
    - FuzzySelect per select con ricerca

11. **Data Separation prod/test** ✅ NUOVO (6 Feb 2026)
    - Separazione completa cartelle dati `backend/data/prod/` e `backend/data/test/`
    - `get_data_dir()` centralizzato in `config.py` per gestione path
    - `ensure_data_dirs()` crea struttura all'avvio
    - Tutti i servizi (BRIM, uploads, logging) usano path dinamico
    - Test isolati non inquinano dati produzione
    - Script migrazione `scripts/migrate_data_structure.py`

12. **UI Fixes + Git Versioning + Settings Stores** ✅ STEP 4.5 (18 Feb 2026)
    - Bug 1: User settings applicate al login (lingua, tema, valuta base)
    - Bug 2: Settings stores centralizzati con sync su salvataggio
      - `userSettings` store con `setDirect()` per update immediato
      - `globalSettings` store **NUOVO** per config app-wide
      - Entrambi caricati in `(app)/+layout.svelte` dopo auth
      - PreferencesTab/GlobalSettingsTab sincronizzano store dopo save
    - Bug 3: Modal BRIM upload scroll corretto
    - Bug 4: Colonna Broker visibile con 2+ broker
    - Feature: Git tag versioning (`./dev.py info version`, sidebar, API)
    - Nuovi file: `globalSettings.ts`, `version.py`, `version.ts`
    - Vedi `phases/phase-04-subplan/plan-ui-fixes.md`

13. **Image Crop Modal** ✅ COMPLETATO (23 Feb 2026)
    - Migrazione da `svelte-easy-crop` a **cropperjs v2** (Web Components) ✅
    - `ImageCropper.svelte` con zoom, rotation LIVE, flip H/V, free crop con maniglie ✅
    - `ImageEditModal.svelte` wrapper con preset (avatar 200×200, broker-icon 64×64, custom) ✅
    - `imageCrop.ts` utility con `getCroppedImageFromCropper()` usa `$toCanvas()` ✅
    - Avatar spostato da PreferencesTab a ProfileTab (editabile in edit mode) ✅
    - Preset ridotti: rimosso "Original", tenuti Avatar/Icon/Custom ✅
    - **FileEditModal.svelte** per rename file non-immagine prima dell'upload ✅
    - **Bug freeze fix**: $change() atomico + clampDepth guard + requestAnimationFrame ✅
    - **FileUploader** edit/restore button per tutti i file ✅
    - **Bottom Panel Redesign**: output size editabile, scale factor, quality spinner, preview ellisse ✅
    - **Flip nell'overlay**: spostato accanto a zoom/rotate con separatore ✅
    - **Feature 4**: 2-column layout, aspect ratio nel panel, quality su filename row ✅
    - **Feature 5 Grid View**: 3-row cards, copy link, red delete, search bar ✅
    - **AssetPickerModal**: 3-tab modale (Existing/URL/Upload) con initialUrl, circularPreview ✅
    - **BrokerForm icon clickable**: rimosso campo URL, click icona → AssetPickerModal ✅
    - **Cancel upload → reopen picker**: annullando ImageEditModal riapre AssetPicker ✅
    - **Active clamping**: pointerdown/up + RAF loop per selezione sempre nei bounds ✅
    - **Zoom unificato**: + riduce selezione → zooma sfondo, - ingrandisce → dezooma ✅
    - **Fix URL validation**: path relativi/locali accettati nel picker ✅
    - **Remove icon button**: link rosso in BrokerForm per cancellare icona ✅
    - **Fix resetAll**: free → dezoom 5%, fixed → max-fit centrato ✅
    - **Chrome wheel warning fix**: listener con `{ passive: false }` ✅
    - **Preview thumbnail nel picker**: `?img_preview=` per grid/lista ✅
    - **Code cleanup**: rimosso codice morto (6 funzioni, 1 import) ✅
    - **Analisi duplicazione**: report in `analysis-code-duplication.md` ✅
    - **Backend img_preview cache**: TTL 1h, size-based 50MB (parametrico), invalidazione su delete ✅
    - **Backend img_preview fix**: ProcessPoolExecutor → resize sincrono (fix pickle error) ✅
    - **Backend img_preview >= original**: serve FileResponse diretto senza processamento ✅
    - **DataTable single-select**: `selectionMode='single'`, `onRowClick`, `onRowDoubleClick` ✅
    - **DataTable ImageCell**: thumbnail con fallback icona + testo opzionale ✅
    - **DataTable svelte:component fix**: deprecation warning risolto (Svelte 5 runes) ✅
    - **FilesTable thumbnail**: immagini mostrano preview 48x48 invece di icona ✅
    - **FilesTable alignment**: immagini centrate, nomi allineati a sinistra in colonna ✅
    - **Files grid bandwidth**: `?img_preview=240x240` per griglia file ✅
    - **AssetPicker URL ellipse**: full image con box-shadow overlay scuro fuori cerchio ✅
    - **Backend PreviewCache class**: classe pubblica con `get/put/invalidate`, size-based (50MB from Settings) ✅
    - **`uploadFile()` utility**: `utils/upload.ts` centralizzata, rimossi 3 duplicati FormData ✅
    - **`formatBytes()` centralizzato**: in `utils/upload.ts`, rimossi 2 duplicati ✅
    - **BRIM file rename**: FileEditModal in BrokerImportFilesModal + BRIM uploader in files/ ✅
    - **DataTable cell-icon-box**: 32×32 wrapper SVG allineato con thumbnail immagini ✅
    - **ModalBase.svelte**: componente base per TUTTE le modali — backdrop, click-outside, Escape, focus, transitions, z-index parametrico ✅
    - **TUTTE 10 modali migrate a ModalBase**: FileEditModal, ConfirmModal, BrokerImportFilesModal, PasswordChangeModal, files/+page ×2, BrokerModal, ImageEditModal, AssetPickerModal, DeleteBrokerDialog, CashTransactionModal ✅
    - **Auth componenti rinominati**: LoginModal→LoginCard, RegisterModal→RegisterCard, ForgotPasswordModal→ForgotPasswordCard (sono card, non modali) ✅
    - **Z-index standardizzato**: layer 50→60→70 (incrementi di 10). Rimossi z-index 100, 1000, 1010, 9999 ✅
    - **AssetPickerModal DataTable**: list view sostituita con DataTable single-select (ImageCell + SizeCell), rimossi ~40 righe CSS custom ✅
    - i18n keys aggiunte per tutte le label ✅
    - **42 test E2E verdi** (7 suite: A-upload, B-controls, C-edge cases, D-asset picker, E-avatar, F-dark mode, G-grid view) ✅
    - **Fix hasChanges propagation**: rotate/flip/zoom ora emettono `dispatchCurrentChange()` per propagare `hasChanges` ✅
    - **Fix PasswordChangeModal testid duplicato**: rimosso `data-testid` dall'inner div ✅
    - **Fix broker close test**: backdrop CSS → `Escape` key ✅
    - **Backend seed_default_avatars()**: copia 30 avatar PNG da `staticResources/Avatars/` a `custom-uploads/` al primo avvio ✅
    - **7/7 frontend test suites verdi**: auth, settings, files, brokers, multi-user, select-components, image-crop ✅
    - Analisi duplicazione in `analysis-code-duplication.md` (3 round, 13 task completati)
    - Vedi `plan-imageCropModal.prompt.md`

---

## 🔀 Deviazioni dal Piano Originale

1. **Zodios Migration**: Non prevista inizialmente, necessaria per type-safety e validazione
2. **BRIM Multi-User**: Espansa significativamente per supportare multi-utenza
3. **DataTable Component**: Creato componente riutilizzabile per tabelle con filtri avanzati
4. **BrokerSelect Component**: Creato per selezione broker con ricerca fuzzy e icone
5. **E2E Test Remediation**: Si è scoperto che i test necessitavano data-testid sui componenti *(in corso)*
6. **Settings Mobile Layout**: Identificato problema responsive durante test gallery *(in corso)*
7. **Gallery Light/Dark Theme**: Richiesto supporto screenshot per entrambi i temi *(pianificato)*

---

## 🐛 Bug Risolti (Round 1-4)

| ID      | Descrizione                                            | Status    |
|---------|--------------------------------------------------------|-----------|
| BUG-001 | Backend error message migliorato per broker esistente  | ✅         |
| BUG-002 | Table: click badge counter per deselezionare           | ✅         |
| BUG-003 | BRIM upload: endpoint path corretto                    | ✅         |
| BUG-004 | FR Bytes: traduzione unità nei filtri                  | ✅         |
| BUG-005 | MkDocs dark mode CSS                                   | ✅         |
| BUG-006 | Copy Link con feedback toast                           | ✅         |
| BUG-007 | Traduzioni broker import files                         | ✅         |
| BUG-008 | Broker altri utenti GDPR                               | ⏸️ PAUSA  |
| BUG-009 | 404 su refresh broker detail                           | ✅         |
| BUG-010 | Filtro size slider inizializzazione                    | ✅         |
| BUG-011 | Global Settings max_file_upload_mb unit selector       | ✅         |
| BUG-012 | Copy Link path relativo + toast in alto                | ✅         |
| BUG-013 | BRIM upload endpoint in BrokerImportFiles              | ✅         |
| BUG-014 | Svelte warnings per prop capture in slider             | ✅         |
| BUG-015 | Reset Default max_file_upload_mb                       | ✅         |
| BUG-016 | Translation key files.upload → uploads.upload          | ✅         |
| BUG-017 | BRIM upload broker_id in query string                  | ✅         |
| BUG-018 | Translation key sbagliata per upload button            | ✅         |
| BUG-019 | Svelte warnings con svelte-ignore                      | ✅         |
| BUG-020 | Form submit handler syntax (on:submit\|preventDefault) | ✅         |
| BUG-021 | Settings mobile layout comprime contenuto              | ✅ RISOLTO |

---

## 📦 Bug/Improvements Pendenti

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
| `test-remediation-auth-settings.md`     | ✅ Note remediation auth/settings      |

### Plans COMPLETATI (in `phase-04-subplan/`)

| File                                        | Descrizione                                | Status       |
|---------------------------------------------|--------------------------------------------|--------------|
| `plan-e2e-test-remediation.md`              | Remediation test E2E (Fase 1 ✅)            | ✅ COMPLETATO |
| `plan-settings-mobile-gallery.md`           | Settings mobile + Gallery improvements     | ✅ COMPLETATO |
| `plan-componentReorganizationV2.prompt.md`  | Famiglia Select unificata + Svelte 5 runes | ✅ COMPLETATO |
| `plan-componentReorganizationV3-cleanup.md` | Cleanup + test E2E Select components       | ✅ COMPLETATO |
| `plan-data-separation.md`                   | Separazione cartelle dati prod/test        | ✅ COMPLETATO |
| `plan-ui-fixes.md`                          | Bug UI + Git versioning                    | ✅ COMPLETATO |
| `plan-imageCropModal.prompt.md`             | Sistema Image Crop Modal unificato         | ✅ COMPLETATO |
| `plan-image-crop.md`                        | Piano iniziale Image Crop                  | ✅ COMPLETATO |
| `analysis-code-duplication.md`              | Analisi e fix duplicazione codice          | ✅ COMPLETATO |

### Reference Docs (in `phases/phase-04-subplan/`)

### Plans PIANIFICATI (in `RoadmapV4_UI/`)

| File                             | Descrizione                            | Status       |
|----------------------------------|----------------------------------------|--------------|
| `plan-filePreview.prompt.md`     | Sistema preview file inline            | 📋 PIANIFICATO |

### Plans Optional/Low Priority

| File                                 | Descrizione                                  | Priorità    |
|--------------------------------------|----------------------------------------------|-------------|
| `plan-frontendDevelopment.prompt.md` | Linee guida sviluppo frontend                | Riferimento |

### Plans ARCHIVIATI (in `phase-04-subplan/`)

| File                               | Descrizione                        | Status        |
|------------------------------------|------------------------------------|---------------|
| `plan-component-reorganization.md` | Piano originale (sostituito da V2) | 📦 ARCHIVIATO |

### Plans DA CREARE

| Piano                              | Descrizione                          | Priorità |
|------------------------------------|--------------------------------------|----------|
| `plan-gdpr-permissions-rethink.md` | Ripensamento permessi GDPR-compliant | P3       |

---

## 🗺️ Step Completati

### Step 1: i18n CLI Improvements (30 min) ✅ COMPLETATO

**Riferimento**: `phases/phase-04-subplan/plan-i18n-cli-improvements.md`

### Step 2: Files Page URL Filters (1h) ✅ COMPLETATO

**Riferimento**: `phases/phase-04-subplan/plan-files-ux-refactor.md` (Step 2)

### Step 3: Files UX Refactoring (1h) ✅ COMPLETATO

**Riferimento**: `phases/phase-04-subplan/plan-files-ux-refactor.md` (Step 3)

### Step 4: Frontend Testing Infrastructure ✅ COMPLETATO

**Riferimento**: `phases/phase-04-subplan/plan-frontendTesting.md`

### Step 4.1: E2E Test Remediation - Fase 1 ✅ COMPLETATO

**Riferimento**: `plan-e2e-test-remediation.md`

**Lavoro svolto (2 Feb 2026)**:

- ✅ Aggiunto `data-testid` a 15+ componenti (auth, layout, settings, files, brokers)
- ✅ 51 test E2E passanti (auth: 10, settings: 13, files: 9, brokers: 7, multi-user: 2)
- ✅ Test dinamici per lingue (genera test da file i18n)
- ✅ Gallery screenshot base per documentazione
- ✅ Build check automatico prima dei test (`_ensure_frontend_build()`)
- ✅ Fix bug form submit (`on:submit|preventDefault`)

### Step 4.2: Settings Mobile + Gallery ✅ COMPLETATO

**Riferimento**: `plan-settings-mobile-gallery.md`

**Lavoro completato (3 Feb 2026)**:

- ✅ `ProfileTab.svelte` - Righe responsive con `flex-col sm:flex-row`
- ✅ `SettingsLayout.svelte` - Dropdown custom per mobile
- ✅ `GlobalSettingsTab.svelte` - Layout responsive
- ✅ `SettingSelect.svelte`, `SettingCurrency.svelte`, `SettingTheme.svelte` - Layout 3 righe mobile
- ✅ `CustomSelect.svelte` - Nuovo componente select semplice
- ✅ Gallery screenshot light + dark theme (18 desktop + 16 mobile tests, ~280+ screenshots)
- ✅ Gallery language selector nell'header MkDocs
- ✅ Gallery usa tema MkDocs per auto-switch immagini
- ✅ desktop.md e mobile.md aggiornati con tutte le sezioni (Profile, Grid View, Media & Upload)

**Nota**: Gallery completa - tutti gli screenshot vengono generati correttamente. Aggiunta sezione Media & Upload con image-edit-modal e file-uploader.

### Step 4.3: Frontend Component Reorganization ✅ COMPLETATO

**Riferimento**: `phases/phase-04-subplan/plan-componentReorganizationV2.prompt.md` + `phases/phase-04-subplan/plan-componentReorganizationV3-cleanup.md`

**Lavoro completato (5 Feb 2026)**:

- ✅ Famiglia Select unificata: `ui/select/` con BaseDropdown, SimpleSelect, SearchSelect
- ✅ Migrazione tutti i consumer a nuovi componenti
- ✅ LanguageSelector con supporto header compatto
- ✅ ImportPluginSelect con inline search e icone broker
- ✅ BrokerSearchSelect con auto-positioning dropdown
- ✅ SettingToggle e SettingNumber per GlobalSettings
- ✅ Fix file upload (Zodios FormData bug → uso axiosInstance)
- ✅ Fix dashboard dark mode (nuovo colore `libre-banner`)
- ✅ Riorganizzazione cartelle: `ui/input/`, `ui/media/`, `layout/`, `settings/tabs/`
- ✅ 16 nuovi test E2E per componenti Select
- ✅ Tutti i test passano (6/6 suite, 67+ test)

### Step 4.4: Data Separation prod/test ✅ COMPLETATO

**Riferimento**: `phases/phase-04-subplan/plan-data-separation.md`

**Lavoro completato (6 Feb 2026)**:

- ✅ Nuova struttura `backend/data/prod/` e `backend/data/test/`
- ✅ `config.py`: `get_data_dir()`, `get_uploads_dir()`, `ensure_data_dirs()`
- ✅ `brim_provider.py`: usa `get_broker_reports_dir()` dinamico
- ✅ `static_uploads.py`: usa `get_uploads_dir()` dinamico
- ✅ `logging_config.py`: logs in `{data_dir}/logs/`
- ✅ `check_constraints_hook.py`: rispetta `LIBREFOLIO_TEST_MODE`
- ✅ `.gitignore` aggiornato per nuova struttura
- ✅ Script migrazione `scripts/migrate_data_structure.py`
- ✅ Tutti i test passano (8/8 categorie)
- ✅ Verifica manuale: dati prod/test completamente isolati

### Step 4.5: UI Fixes Post Data-Separation ✅ COMPLETATO

**Riferimento**: `phases/phase-04-subplan/plan-ui-fixes.md`

**Lavoro completato (18 Feb 2026)**:

- ✅ Bug 1: User preferences applicate al login (lingua, tema, valuta)
- ✅ Bug 2: Settings stores centralizzati (`userSettings` + `globalSettings`)
- ✅ Bug 3: Modal BRIM upload scroll corretto
- ✅ Bug 4: Colonna Broker visibile con 2+ broker
- ✅ Feature: Git tag versioning (`./dev.py info version`, sidebar, API)

### Step 4.6: Image Crop Component ✅ COMPLETATO

**Riferimento**: `plan-imageCropModal.prompt.md`

**Lavoro completato (18-23 Feb 2026)**:

- ✅ Installato `cropperjs v2` per crop interattivo (Web Components)
- ✅ Creato `utils/imageCrop.ts` con presets e utility `getCroppedImageFromCropper()`
- ✅ Creato `ImageCropper.svelte` - componente crop puro (zoom, rotate, flip, free crop)
- ✅ Creato `ImageEditModal.svelte` - modale wrapper con upload e rename
- ✅ Creato `FileEditModal.svelte` - modale per rename file non-immagine
- ✅ Creato `AssetPickerModal.svelte` - modale picker (URL/Existing/Upload) con DataTable single-select
- ✅ Creato `ImagePickerWrapper.svelte` - wrapper che incapsula flusso AssetPicker + ImageEditModal
- ✅ Creato `ModalBase.svelte` - componente base per tutte le 10 modali del progetto
- ✅ Integrazione Files Page: upload immagine → editor → upload
- ✅ FileUploader: edit button per tutti i file (immagini + non-immagini)
- ✅ Integrazione Broker Icon: click icona → AssetPicker → editor con preset 64x64
- ✅ Integrazione Avatar Utente: ProfileTab con AssetPicker → preset 200x200
- ✅ Avatar visibile in Sidebar con link a Settings
- ✅ Dark mode funzionante
- ✅ Bug fix: freeze selezione oltre bordo ($change atomico + guard)
- ✅ Mobile-friendly (touch gestures supportati)
- ✅ Backend preview cache (size-based 50MB, TTL 1h)
- ✅ Auth components rinominati (Modal→Card per LoginCard, RegisterCard, ForgotPasswordCard)
- ✅ Analisi duplicazione codice (3 round, 14/15 task completati)
- ✅ `formatBytes()` centralizzato e i18n-aware
- ✅ `uploadFile()` utility centralizzata

**Da completare**:

- ✅ 42 test E2E implementati in `e2e/image-crop.spec.ts`
- ✅ data-testid aggiunti a tutti i componenti nuovi (27 attributi)
- ✅ FileGrid.svelte estratto e condiviso tra files/ e AssetPicker
- ✅ Analisi duplicazione completata (6/6 task)

### Step 4.7: MkDocs Dark Mode ✅ COMPLETATO

**Lavoro completato (24 Feb 2026)**:

- ✅ Dark mode CSS allineato con variabili frontend (slate-900, green-500, etc.)
- ✅ Gallery screenshot containers con box-shadow corretto in dark mode
- ✅ Tabelle con header e righe alternate stilizzate per dark mode
- ✅ Admonitions (tips, notes, warnings) con background dark mode
- ✅ Gallery markdown con sezioni Media & Upload sia desktop che mobile

### Step 4.8: GDPR Permissions Analysis (planning only) ⏸️

### Step 4.9: File Preview System 📋 PIANIFICATO

**Riferimento**: `plan-filePreview.prompt.md`

**Obiettivo**: Preview inline dei file senza download completo

**Features pianificate**:

- Preview immagini con selector qualità
- Preview testo/codice con range righe selezionabile
- Preview tabelle (CSV/Excel) con DataTable
- Preview Markdown con rendering HTML
- Disponibile in Files Page (Static + BRIM) e Broker Detail

**Stima**: ~8h (1 giorno lavorativo)

---

## 🎯 Prossimi Passi Immediati

**Phase 4 COMPLETATA** - Tutte le feature implementate. Test E2E da scrivere.

### ✅ Step Completati

1. ✅ **Data Separation** (6 Feb 2026) - Cartelle prod/test isolate, 8/8 test passano
2. ✅ **Component Reorganization** (5 Feb 2026) - Famiglia Select, 67+ test E2E
3. ✅ **Settings Mobile + Gallery** (3 Feb 2026) - Layout responsive, 224 screenshots
4. ✅ **E2E Test Remediation** (2 Feb 2026) - 51 test, data-testid
5. ✅ **UI Fixes** (18 Feb 2026) - Bug login/settings, modal scroll, versioning
6. ✅ **Image Crop Component** (18-23 Feb 2026) - Crop, FileEditModal, AssetPicker, ModalBase, ImagePickerWrapper, code dedup

### 📋 Pianificato

7. ✅ **Image Crop E2E Tests** - 42 test scritti, tutti passano
8. ✅ **Gallery Walkthrough** - Nuove sezioni: Profile, Grid View, Media & Upload. Markdown aggiornati.
9. 📋 **File Preview System** (`plan-filePreview.prompt.md`) - ~8h

### 🔲 Optional/Low Priority

- ✅ **MkDocs Dark Mode** (`Step 4.7`) - COMPLETATO (24 Feb 2026)
- **GDPR Permissions Analysis** (`Step 4.8`) - Planning only

### Dopo: Phase 5 (FX Management)

- Lista currency pairs
- Visualizzazione tassi storici
- Grafici con ECharts

---

## 📚 Contesto per Agent

Quando si lavora su questa fase, allegare:

| Scenario                     | Files da allegare                                                                                         |
|------------------------------|-----------------------------------------------------------------------------------------------------------|
| Bug fix generici             | `plan-phase04-summary.md`                                                                                 |
| BRIM/Files                   | `+ phases/phase-04-subplan/plan-brim-multiuser-implementation.md`                                         |
| Tipi/API                     | `+ phases/phase-04-subplan/plan-types-library.md`                                                         |
| Test frontend infra          | `+ phases/phase-04-subplan/plan-frontendTesting.md`                                                       |
| Test remediation             | `+ phases/phase-04-subplan/plan-e2e-test-remediation.md` + `phases/phase-04-subplan/e2e-test-analysis.md` |
| Settings mobile + gallery    | `+ phases/phase-04-subplan/plan-settings-mobile-gallery.md`                                               |
| **Component Reorganization** | `+ plan-componentReorganizationV2.prompt.md`                                                              |
| Image upload                 | `+ phases/phase-04-subplan/plan-imageCropModal.prompt.md`                         |
| Separazione dati             | `+ plan-data-separation.md`                                                                               |
| i18n CLI                     | `+ phases/phase-04-subplan/plan-i18n-cli-improvements.md`                                                 |
| Files UX/URL                 | `+ phases/phase-04-subplan/plan-files-ux-refactor.md`                                                     |

---

## ✅ Checklist Pre-Commit

- [x] `./dev.py front build` senza errori/warnings
- [x] `./dev.py front check` senza errori
- [x] `./dev.py i18n audit` - 100% coverage
- [x] Test funzionale features modificate
- [x] `./dev.py test front all` - tutti i test passano (7+ suite, 109+ test)
- [x] `./dev.py test front image-crop` - 42 test passanti
- [x] `./dev.py mkdocs gallery` - tutti gli screenshot generati (34 test, ~280+ screenshots)
