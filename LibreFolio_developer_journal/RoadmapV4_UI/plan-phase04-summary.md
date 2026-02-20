# Phase 4 - Brokers Management: Summary & Next Steps

**Data creazione**: 30 Gennaio 2026  
**Ultimo aggiornamento**: 20 Febbraio 2026  
**Status**: 🟢 COMPLETATO (Core features, Image Crop + FileEdit funzionanti)

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

13. **Image Crop Modal** 🧪 IN DEBUG (20 Feb 2026)
    - Migrazione da `svelte-easy-crop` a **cropperjs v2** (Web Components) ✅
    - `ImageCropper.svelte` con zoom, rotation LIVE, flip H/V, free crop con maniglie ✅
    - `ImageEditModal.svelte` wrapper con preset (avatar 200×200, broker-icon 64×64, custom) ✅
    - `imageCrop.ts` utility con `getCroppedImageFromCropper()` usa `$toCanvas()` ✅
    - Avatar spostato da PreferencesTab a ProfileTab (editabile in edit mode) ✅
    - Preset ridotti: rimosso "Original", tenuti Avatar/Icon/Custom ✅
    - **FileEditModal.svelte** per rename file non-immagine prima dell'upload ✅ (20 Feb)
    - **Bug freeze fix**: $change() atomico + clampDepth guard + requestAnimationFrame ✅ (20 Feb)
    - **FileUploader** edit button per tutti i file (non solo immagini) ✅ (20 Feb)
    - **Bottom Panel Redesign**: output size editabile, scale factor, quality spinner, preview ellisse ✅ (20 Feb)
    - **Flip nell'overlay**: spostato accanto a zoom/rotate con separatore ✅ (20 Feb)
    - i18n keys aggiunte per tutte le label ✅
    - Feature rimanenti: Grid View improvements (F5), Asset Picker Modal (F6)
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
| BUG-005 | MkDocs dark mode CSS                                   | 🔲 TODO   |
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
| `test-remediation-auth-settings.md`     | ✅ Note remediation auth/settings      |

### Plans COMPLETATI (spostati in `phase-04-subplan/`)

| File                                        | Descrizione                                | Status       |
|---------------------------------------------|--------------------------------------------|--------------|
| `plan-e2e-test-remediation.md`              | Remediation test E2E (Fase 1 ✅)            | ✅ COMPLETATO |
| `plan-settings-mobile-gallery.md`           | Settings mobile + Gallery improvements     | ✅ COMPLETATO |
| `plan-componentReorganizationV2.prompt.md`  | Famiglia Select unificata + Svelte 5 runes | ✅ COMPLETATO |
| `plan-componentReorganizationV3-cleanup.md` | Cleanup + test E2E Select components       | ✅ COMPLETATO |
| `plan-data-separation.md`                   | Separazione cartelle dati prod/test        | ✅ COMPLETATO |
| `plan-ui-fixes.md`                          | Bug UI + Git versioning                    | ✅ COMPLETATO |

### Reference Docs (in `phases/phase-04-subplan/`)

| File                   | Descrizione                                     | Status       |
|------------------------|-------------------------------------------------|--------------|
| `e2e-test-analysis.md` | Gap analysis test E2E - traccia test completati | ✅ COMPLETATO |

### Plans COMPLETATI (in `RoadmapV4_UI/`)

| File                             | Descrizione                            | Status       |
|----------------------------------|----------------------------------------|--------------|
| `plan-imageCropModal.prompt.md`  | Sistema Image Crop Modal unificato     | 🧪 IN TEST (Feature 3+4 rimanenti) |

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
- ✅ Gallery screenshot light + dark theme (28 test, ~224 screenshots)
- ✅ Gallery language selector nell'header MkDocs
- ✅ Gallery usa tema MkDocs per auto-switch immagini
- ✅ desktop.md e mobile.md aggiornati con tutte le sezioni

**Nota**: Gallery completa - tutti gli screenshot vengono generati correttamente (28 test, ~224 screenshots).

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

### Step 4.6: Image Crop Component 🧪 IN TEST

**Riferimento**: `plan-imageCropModal.prompt.md`

**Lavoro completato (18-20 Feb 2026)**:

- ✅ Installato `cropperjs v2` per crop interattivo (Web Components)
- ✅ Creato `utils/imageCrop.ts` con presets e utility `getCroppedImageFromCropper()`
- ✅ Creato `ImageCropper.svelte` - componente crop puro (zoom, rotate, flip, free crop)
- ✅ Creato `ImageEditModal.svelte` - modale wrapper con upload e rename
- ✅ Creato `FileEditModal.svelte` - modale per rename file non-immagine (20 Feb)
- ✅ Integrazione Files Page: upload immagine → editor → upload
- ✅ FileUploader: edit button per tutti i file (immagini + non-immagini) (20 Feb)
- ✅ Integrazione Broker Icon: bottone upload → editor con preset 64x64
- ✅ Integrazione Avatar Utente: sezione in ProfileTab con preset 200x200
- ✅ Avatar visibile in Sidebar con link a Settings
- ✅ Dark mode funzionante
- ✅ Bug fix: freeze selezione oltre bordo ($change atomico + guard) (20 Feb)
- ✅ Mobile-friendly (touch gestures supportati)

**Da completare**:

- 📋 Feature 3: Asset Picker Modal (scegli da URL/file esistenti/upload nuovo)
- 📋 Feature 4: Output Size editabile (input width/height con scale factor)
- 📋 Miglioramenti grid view files page
- 🧪 Test manuali in corso
- 📋 Test E2E da implementare

### Step 4.7: MkDocs Dark Mode (30 min) 🔲

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

**Phase 4 IN TEST** - Image Crop + FileEdit funzionanti, Asset Picker e Output Size da implementare

### ✅ Step Completati

1. ✅ **Data Separation** (6 Feb 2026) - Cartelle prod/test isolate, 8/8 test passano
2. ✅ **Component Reorganization** (5 Feb 2026) - Famiglia Select, 67+ test E2E
3. ✅ **Settings Mobile + Gallery** (3 Feb 2026) - Layout responsive, 224 screenshots
4. ✅ **E2E Test Remediation** (2 Feb 2026) - 51 test, data-testid
5. ✅ **UI Fixes** (18 Feb 2026) - Bug login/settings, modal scroll, versioning

### 🧪 In Test

6. 🧪 **Image Crop Component** (18-20 Feb 2026) - Core funzionante, fix freeze, FileEditModal aggiunto

### 📋 Pianificato

7. 📋 **Asset Picker Modal** - Scegli immagine da URL/file esistenti/upload nuovo
8. 📋 **Output Size editabile** - Input width/height con scale factor in ImageEditModal
9. 📋 **Grid View improvements** - Azioni uniformi, filtro utente, search nome
10. 📋 **File Preview System** (`plan-filePreview.prompt.md`) - ~8h

### 🔲 Optional/Low Priority

- **MkDocs Dark Mode** (`Step 4.7`) - ~30 min
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
| Image upload                 | `+ plan-image-crop.md`                                                                                    |
| Separazione dati             | `+ plan-data-separation.md`                                                                               |
| i18n CLI                     | `+ phases/phase-04-subplan/plan-i18n-cli-improvements.md`                                                 |
| Files UX/URL                 | `+ phases/phase-04-subplan/plan-files-ux-refactor.md`                                                     |

---

## ✅ Checklist Pre-Commit

- [x] `./dev.py front build` senza errori/warnings
- [x] `./dev.py front check` senza errori
- [x] `./dev.py i18n audit` - 100% coverage
- [x] Test funzionale features modificate
- [x] `./dev.py test front all` - tutti i test passano (6/6 suite, 67+ test)
- [x] `./dev.py mkdocs gallery` - tutti gli screenshot generati (28 test, ~224 screenshots)
