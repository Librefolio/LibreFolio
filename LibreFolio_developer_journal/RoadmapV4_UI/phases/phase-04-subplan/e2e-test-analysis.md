# E2E Test Analysis - LibreFolio Frontend

**Data**: 2 Febbraio 2026  
**Ultimo aggiornamento**: 3 Febbraio 2026  
**Status**: ✅ COMPLETATO - Tutte le fasi implementate  
**Obiettivo**: Valutare copertura, ridondanze e gap nei test E2E

---

## 📊 Stato Attuale dei Test

| Suite              | Test | Status | Note                                                       |
|--------------------|------|--------|------------------------------------------------------------|
| auth.spec.ts       | 17   | ✅ PASS | +7 test Register/Forgot modals                             |
| settings.spec.ts   | 26   | ✅ PASS | +13 test Profile edit, Change password, About, Persistence |
| files.spec.ts      | 14   | ✅ PASS | +5 test toggle uploader, view mode, upload/clear           |
| brokers.spec.ts    | 20   | ✅ PASS | +13 test edit/delete/detail/import modal, CRUD completo    |
| multi-user.spec.ts | 2    | ✅ PASS | Test isolamento + unicità nomi                             |
| gallery.spec.ts    | 28   | ✅ PASS | Light/dark theme, 4 lingue                                 |

**Totale**: ~107 test (6/6 suite)

---

## 🔍 Analisi per File

### 1. auth.spec.ts (10 test) ✅

**Cosa testa**:

- Login page rendering (usa data-testid)
- Login success → redirect a dashboard
- Login failure → mostra errore
- Logout → ritorna a login
- Admin login
- Language selector visibile
- 4x test cambio lingua (dinamici da i18n)

**Criteri di successo**:

- `login-page`, `login-modal`, `login-form`, `login-username`, `login-password`, `login-submit` visibili
- `login-error` visibile dopo credenziali errate
- `dashboard-page` visibile dopo login
- `logout-button` funziona
- Testo bottone login cambia per ogni lingua

**Copertura funzionalità**:

| Funzionalità                      | Testata | Note                                        |
|-----------------------------------|---------|---------------------------------------------|
| Login form rendering              | ✅       |                                             |
| Login success                     | ✅       |                                             |
| Login failure                     | ✅       |                                             |
| Logout                            | ✅       |                                             |
| Language switch                   | ✅       | Dinamico per tutte le lingue                |
| Register modal                    | ✅       | Apertura, form, password strength, nav back |
| Forgot password modal             | ✅       | Apertura, nav back to login                 |
| Auto-redirect se già autenticato  | ❌       | **MANCANTE**                                |
| Remember me / session persistence | ❌       | N/A (non implementato)                      |

**Ridondanze**: Nessuna

**Raccomandazioni**:

1. ✅ ~~Aggiungere test per RegisterModal~~ FATTO
2. ✅ ~~Aggiungere test per ForgotPasswordModal~~ FATTO
3. ➕ Test auto-redirect quando già autenticato

Nota:
Attualmente tutti e 3 gli utenti al termine del test risultano super utenti:
└─▶ $ ./dev.py user --test-db list
ℹ️ Operating on TEST database

ID    Username             Email                          Active   Super
---------------------------------------------------------------------------
1 e2e_test_user e2e@test.example.com ✅ 👑       
2 e2e_test_admin e2eadmin@test.example.com ✅ 👑       
3 e2e_test_user2 e2e2@test.example.com ✅ 👑

---

### 2. settings.spec.ts (13 test) ✅

**Cosa testa**:

- Accesso pagina settings
- Tutti i 4 tab visibili (profile, preferences, about, admin)
- Profile tab attivo di default
- Profile tab: username, email, change password button, delete account button
- Campi profile inizialmente disabilitati (locked)
- Preferences tab: switch funziona, language/currency/theme visibili
- Admin tab: admin può accedere, non-admin vede ma non edita

**Criteri di successo**:

- `settings-page` visibile dopo navigazione
- `settings-tab-{profile,preferences,about,admin}` visibili
- `profile-tab`, `profile-username`, `profile-email` visibili
- `preference-language`, `preference-currency`, `preference-theme` visibili
- `global-settings-tab` visibile per admin e non-admin

**Copertura funzionalità**:

| Funzionalità                 | Testata | Note                                       |
|------------------------------|---------|--------------------------------------------|
| Tab navigation               | ✅       |                                            |
| Profile display              | ✅       |                                            |
| Profile edit mode (unlock)   | ✅       | Unlock, modify, undo                       |
| Profile save changes         | ⚠️      | Test UI buttons, non salvataggio effettivo |
| Change password flow         | ✅       | Modal apertura, campi, chiusura, strength  |
| Delete account flow          | ❌       | **MANCANTE** - solo bottone visibile       |
| Preferences change & save    | ❌       | **MANCANTE** - solo visibilità             |
| Language change persists     | ❌       | Testato in auth, non in settings           |
| Theme change                 | ❌       | **MANCANTE**                               |
| Currency change              | ❌       | **MANCANTE**                               |
| Global settings edit (admin) | ❌       | **MANCANTE**                               |
| About tab content            | ✅       | Tab switch, app name, version              |

**Ridondanze**: Nessuna evidente

**Raccomandazioni**:

1. ✅ ~~Test unlock/edit mode per profile~~ FATTO
2. ⚠️ Test save changes effettivo (salvataggio API)
3. ✅ ~~Test change password modal flow~~ FATTO
4. ➕ Test preferences save & persist (almeno 1 per tipo)
5. ➖ I test "button is visible" sono deboli - meglio testare l'azione

---

### 3. files.spec.ts (12 test) ✅

**Cosa testa**:

- Accesso pagina files
- Entrambi i tab visibili (static, brim)
- Switch tra tab
- URL deep-linking (tab=static, tab=brim)
- Static tab: table visibile, upload button visibile
- Toggle uploader visibility
- View mode toggle (grid/list) quando ci sono file
- BRIM tab: table O empty state

**Criteri di successo**:

- `files-page` visibile
- `files-tab-static`, `files-tab-brim` visibili con aria-selected corretto
- `files-table-static` visibile
- `files-table-brim` O `brim-empty-state` visibile
- `upload-button` visibile
- `file-uploader` toggle on/off
- `view-mode-toggle`, `view-mode-grid`, `view-mode-list` (quando file esistono)

**Copertura funzionalità**:

| Funzionalità                       | Testata | Note                               |
|------------------------------------|---------|------------------------------------|
| Page access                        | ✅       |                                    |
| Tab navigation                     | ✅       |                                    |
| URL deep-linking                   | ✅       |                                    |
| Static files table                 | ✅       | Solo visibilità                    |
| BRIM files table                   | ✅       | Table o empty state                |
| Toggle uploader                    | ✅       | Show/hide con bottone              |
| View mode toggle (grid/list)       | ✅       | Condizionale (solo se file)        |
| File upload                        | ❌       | **MANCANTE** - richiede file reale |
| File download                      | ❌       | **MANCANTE**                       |
| File delete                        | ❌       | **MANCANTE**                       |
| File preview                       | ❌       | **MANCANTE**                       |
| Broker filter (BRIM)               | ❌       | **MANCANTE**                       |
| URL filters (filename, size, date) | ❌       | **MANCANTE**                       |

**Ridondanze**: Nessuna

**Raccomandazioni**:

1. ✅ ~~Fix test BRIM~~ FATTO
2. ✅ ~~Test toggle uploader~~ FATTO
3. ➕ Test upload file (richiede fixture file)
4. ➕ Test delete file

---

### 4. brokers.spec.ts (18 test) ✅

**Cosa testa**:

- Accesso pagina brokers
- Add broker button visibile
- Refresh button visibile
- Apertura create broker modal
- Chiusura modal (click outside)
- Creazione broker con nome
- Apertura edit modal da card
- Apertura delete dialog da card
- Navigazione a broker detail
- Broker detail: nome, cash balances, holdings, transactions
- Import files button e modal
- Edit button su detail
- Navigazione back

**Criteri di successo**:

- `brokers-page` visibile
- `add-broker-button`, `brokers-refresh` visibili
- `broker-modal` si apre/chiude
- `delete-broker-dialog` si apre/chiude
- `broker-detail-page` con sezioni visibili
- `import-files-modal` si apre/chiude
- Broker card appare dopo creazione

**Copertura funzionalità**:

| Funzionalità                | Testata | Note                                  |
|-----------------------------|---------|---------------------------------------|
| Page access                 | ✅       |                                       |
| Create broker               | ✅       | Solo nome base                        |
| Create with initial balance | ❌       | **MANCANTE**                          |
| Edit broker (open modal)    | ✅       | Da card e da detail page              |
| Delete broker (open dialog) | ✅       | Apertura e cancel                     |
| Delete broker (confirm)     | ❌       | **MANCANTE** - non conferma realmente |
| Broker detail page          | ✅       | Tutte le sezioni verificate           |
| Cash balances section       | ✅       | Visibilità verificata                 |
| Holdings section            | ✅       | Visibilità verificata                 |
| Transactions section        | ✅       | Visibilità verificata                 |
| Cash deposit/withdraw       | ❌       | **MANCANTE**                          |
| Import files button         | ✅       | Visibilità verificata                 |
| Import files modal          | ✅       | Apertura e chiusura con Escape        |
| Navigate back               | ✅       | Da detail a list                      |

**Ridondanze**: Nessuna

**Raccomandazioni**:

1. ✅ ~~Test edit broker modal~~ FATTO
2. ✅ ~~Test delete broker dialog~~ FATTO
3. ✅ ~~Test broker detail page content~~ FATTO
4. ➕ Test import files modal apertura
5. ➕ Test delete broker con conferma effettiva

---

### 5. multi-user.spec.ts (2 test) ✅

**Cosa testa**:

- User non vede broker di altro user (isolamento dati)
- Nomi broker sono GLOBALMENTE univoci (duplicati rifiutati)

**Criteri di successo**:

- Broker creato da user1 non visibile a user2
- User2 non può creare broker con nome già usato da user1 (errore)

**Copertura funzionalità**:

| Funzionalità           | Testata | Note                                  |
|------------------------|---------|---------------------------------------|
| Broker isolation       | ✅       |                                       |
| Global name uniqueness | ✅       | Duplicati rifiutati                   |
| Shared broker access   | ❌       | **MANCANTE** - feature broker sharing |
| File isolation         | ❌       | **MANCANTE**                          |

**Ridondanze**: Nessuna

**Raccomandazioni**:

1. ➕ Test file isolation tra user
2. ➕ Test broker sharing quando implementato

---

### 6. gallery.spec.ts (~12 test) ✅

**Cosa testa**:

- Screenshot di tutte le pagine per tutte le lingue (EN, IT, FR, ES)
- Animazioni CSS freezate al 10% per consistenza
- Login, register (vuoto e con form compilato), dashboard, settings, files, brokers

**Prerequisiti**:

```bash
# Installare WebKit per mobile screenshots
npx playwright install webkit

# Popolare DB con dati realistici prima della gallery
./dev.py db populate --force
```

**Note**:

- Questo file genera screenshot per documentazione (mkdocs), non è un test funzionale
- Desktop: Chrome, Mobile: WebKit (Safari engine)
- WebKit è cross-platform (macOS/Linux/Windows)

**Screenshot generati**:

| Categoria | Screenshot                                      | Note                                    |
|-----------|-------------------------------------------------|-----------------------------------------|
| auth      | 01-login, 02-register-empty, 03-register-filled | Form compilato mostra password strength |
| dashboard | main, menu-open (solo mobile)                   |                                         |
| settings  | user-preferences, global-settings               |                                         |
| files     | static-tab, brim-tab                            |                                         |
| brokers   | list, detail, import-modal                      | Attende 2s per favicon load             |

**Miglioramenti Pianificati**:

- [ ] Screenshot password change modal
- [ ] Screenshot warning/error modals
- [ ] Screenshot broker create modal con form compilato
- [ ] MkDocs Gallery walkthrough pages (Desktop/Mobile)

---

## 📋 Riepilogo Gap di Copertura

### ✅ Completato

1. **RegisterModal** - apertura, form fields, password strength, back to login
2. **ForgotPasswordModal** - apertura, back to login
3. **Profile edit** - unlock, modify, undo
4. **Change password modal** - apertura, campi, chiusura, password strength
5. **Broker edit modal** - apertura da card e da detail
6. **Broker delete dialog** - apertura e cancel
7. **Broker detail sections** - cash balances, holdings, transactions
8. **File uploader toggle** - show/hide con bottone
9. **About tab** - contenuto, app name, version
10. **View mode toggle** - grid/list (condizionale)
11. **Import files modal** - apertura e chiusura

### ✅ Completato (3 Feb 2026 - Sessione 3)

1. **File upload** - ✅ Upload file da samples BRIM, select/clear
2. **Broker CRUD completo** - ✅ Create → Edit → Delete (flusso intero)
3. **Preferences persistence** - ✅ F5/reload + goto verifica persistenza

### Bassa Priorità (rimandati)

1. ~~Cash deposit/withdraw operations~~ - Richiede sviluppo transazioni (solo POC attuale)
2. BRIM broker filter
3. URL filters su files
4. File preview/download

---

## 🎯 Piano di Azione

### ✅ Fase 1: Fix test esistenti - COMPLETATA

1. ✅ auth.spec.ts - OK
2. ✅ settings.spec.ts - OK
3. ✅ files.spec.ts - OK
4. ✅ brokers.spec.ts - OK
5. ✅ multi-user.spec.ts - OK

### ✅ Fase 2: Test mancanti critici - COMPLETATA

1. ✅ auth.spec.ts: Register modal, Forgot password
2. ✅ settings.spec.ts: Profile edit flow, Change password modal
3. ✅ files.spec.ts: Toggle uploader
4. ✅ brokers.spec.ts: Edit, Delete dialog, Detail page sections

### ✅ Fase 3: Test secondari - COMPLETATA

**File fixture utilizzati**: `backend/app/services/brim_providers/sample_reports/`

1. ✅ **File upload** - Upload file reale da samples BRIM + clear
2. ✅ **Broker CRUD completo** - Create → Edit → Delete (flusso intero)
3. ✅ **Preferences persistence** - F5/reload + goto verifica persistenza
4. ➖ ~~Cash operations~~ - Rimandato (richiede sviluppo transazioni)

---

## 📝 data-testid Inventory

### Già implementati ✅

```
# Auth
login-page, login-modal, login-form, login-username, login-password
login-submit, login-error, goto-register, goto-forgot
register-modal, register-form, register-username, register-email
register-password, register-confirm-password, register-submit, goto-login
forgot-modal, forgot-back-to-login
password-strength-meter, password-strength-bar

# Layout
sidebar, logout-button, mobile-menu-toggle
language-selector, language-selector-button
dashboard-page

# Settings
settings-page, settings-tab-{profile,preferences,about,admin}
profile-tab, profile-username, profile-email
profile-edit-toggle, profile-save-all, profile-undo-all
profile-error, profile-success
change-password-button, delete-account-button
password-change-modal, password-current, password-new, password-confirm
password-change-submit, password-change-cancel
preference-language, preference-currency, preference-theme
global-settings-tab
about-tab, about-app-name, about-version

# Files
files-page, files-tab-static, files-tab-brim
files-table-static, files-table-brim
upload-button, brim-empty-state
file-uploader, file-drop-zone, file-input
view-mode-toggle, view-mode-grid, view-mode-list

# Brokers
brokers-page, add-broker-button, brokers-refresh
broker-card-{id}, broker-edit-{id}, broker-delete-{id}
broker-modal, broker-name-input, broker-form-submit
delete-broker-dialog, delete-broker-cancel, delete-broker-confirm
broker-detail-page, broker-name, broker-description
broker-back-button, broker-refresh, broker-edit-button
broker-cash-balances, broker-holdings, broker-transactions
import-files-button, import-files-modal
```

### Da aggiungere per test futuri (opzionali)

```
# Files (per upload/delete effettivo)
file-row-{id}, file-delete-{id}
delete-file-modal, delete-file-confirm

# Settings (per persistenza)
preference-save-button
```

---

## ✅ Lavoro Completato

### Sessione 1 (2 Feb 2026)

**Componenti modificati con data-testid**:

- [x] LoginModal.svelte
- [x] RegisterModal.svelte (parziale)
- [x] Sidebar.svelte
- [x] Header.svelte
- [x] LanguageSelector.svelte
- [x] PasswordInput.svelte (prop testId)
- [x] dashboard/+page.svelte
- [x] settings/+page.svelte
- [x] ProfileTab.svelte
- [x] PreferencesTab.svelte
- [x] GlobalSettingsTab.svelte
- [x] files/+page.svelte
- [x] FilesTable.svelte
- [x] brokers/+page.svelte
- [x] BrokerCard.svelte
- [x] BrokerModal.svelte
- [x] +page.svelte (login page)

### Sessione 2 (3 Feb 2026)

**Nuovi data-testid aggiunti**:

- [x] ForgotPasswordModal.svelte (forgot-modal, forgot-back-to-login)
- [x] RegisterModal.svelte (register-password, register-confirm-password, register-submit)
- [x] PasswordStrength.svelte (password-strength-meter, password-strength-bar)
- [x] PasswordChangeModal.svelte (password-change-modal, password-current/new/confirm, submit/cancel)
- [x] ProfileTab.svelte (profile-edit-toggle, profile-save-all, profile-undo-all, profile-error/success)
- [x] LoginModal.svelte (goto-forgot)
- [x] BrokerCard.svelte (broker-edit-{id}, broker-delete-{id})
- [x] DeleteBrokerDialog.svelte (delete-broker-dialog, delete-broker-cancel/confirm)
- [x] brokers/[id]/+page.svelte (broker-detail-page, broker-name, broker-back-button, broker-edit-button, broker-cash-balances, broker-holdings, broker-transactions)
- [x] FileUploader.svelte (file-uploader, file-drop-zone, file-input)

**Test aggiunti**:

- [x] auth.spec.ts: 7 nuovi test (Register modal x4, Forgot modal x2, + fix)
- [x] settings.spec.ts: 10 nuovi test (Profile edit x3, Change password x4, About tab x3)
- [x] files.spec.ts: 3 nuovi test (toggle uploader, view mode x2)
- [x] brokers.spec.ts: 11 nuovi test (edit modal x2, delete dialog x1, detail page x6, import modal x2)

**Totale test**: ~100 (vs 69 iniziali)

### Fixture e configurazione

- [x] i18n-data.ts - Auto-discovery lingue da i18n/*.json

- [x] playwright.config.ts - timeout 3s, open: 'never'
- [x] auth-helpers.ts - Aggiornato per usare data-testid

---

## 🤔 Domande e Risposte

1. **Test upload file**: ✅ Usare file reali dai samples BRIM (`backend/app/services/brim_providers/samples/`)
2. **Test delete broker**: ✅ Fare dopo aver creato un broker, verificare anche update nel flusso
3. **Test persistence**: ✅ Testare sia F5/reload che goto (non serve riavviare server)
4. **Cash operations**: ⏸️ Rimandato - richiede prima sviluppo transazioni (attualmente POC)
5. **Coverage multilingua**: Il pattern con `SUPPORTED_LANGUAGES` è corretto per test funzionali
