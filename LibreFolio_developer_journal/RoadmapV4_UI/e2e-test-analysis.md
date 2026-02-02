# E2E Test Analysis - LibreFolio Frontend

**Data**: 2 Febbraio 2026  
**Ultimo aggiornamento**: 2 Febbraio 2026  
**Status**: ✅ Fase 1 Completata, 🔄 Fase 2 in pianificazione  
**Obiettivo**: Valutare copertura, ridondanze e gap nei test E2E

---

## 📊 Stato Attuale dei Test

| Suite              | Test | Status   | Note                           |
|--------------------|------|----------|--------------------------------|
| auth.spec.ts       | 10   | ✅ PASS   | Completamente riscritto        |
| settings.spec.ts   | 13   | ✅ PASS   | Completamente riscritto        |
| files.spec.ts      | 9    | ✅ PASS   | Completamente riscritto        |
| brokers.spec.ts    | 7    | ✅ PASS   | Completamente riscritto        |
| multi-user.spec.ts | 2    | ✅ PASS   | Test isolamento + unicità nomi |
| gallery.spec.ts    | ~12  | 🔧 11/12 | Mobile menu fix in corso       |

**Totale**: 51 test passanti + 12 gallery (11 pass, 1 skip)

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

| Funzionalità                      | Testata | Note                                               |
|-----------------------------------|---------|----------------------------------------------------|
| Login form rendering              | ✅       |                                                    |
| Login success                     | ✅       |                                                    |
| Login failure                     | ✅       |                                                    |
| Logout                            | ✅       |                                                    |
| Language switch                   | ✅       | Dinamico per tutte le lingue                       |
| Register modal                    | ❌       | **MANCANTE** - goto-register esiste ma non testato |
| Forgot password modal             | ❌       | **MANCANTE** - flow non testato                    |
| Auto-redirect se già autenticato  | ❌       | **MANCANTE**                                       |
| Remember me / session persistence | ❌       | N/A (non implementato)                             |

**Ridondanze**: Nessuna

**Raccomandazioni**:

1. ➕ Aggiungere test per RegisterModal (apertura, form, validazione password strength)
2. ➕ Aggiungere test per ForgotPasswordModal
3. ➕ Test auto-redirect quando già autenticato

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

| Funzionalità                 | Testata | Note                                 |
|------------------------------|---------|--------------------------------------|
| Tab navigation               | ✅       |                                      |
| Profile display              | ✅       |                                      |
| Profile edit mode (unlock)   | ❌       | **MANCANTE** - solo verifica locked  |
| Profile save changes         | ❌       | **MANCANTE**                         |
| Change password flow         | ❌       | **MANCANTE** - solo bottone visibile |
| Delete account flow          | ❌       | **MANCANTE** - solo bottone visibile |
| Preferences change & save    | ❌       | **MANCANTE** - solo visibilità       |
| Language change persists     | ❌       | Testato in auth, non in settings     |
| Theme change                 | ❌       | **MANCANTE**                         |
| Currency change              | ❌       | **MANCANTE**                         |
| Global settings edit (admin) | ❌       | **MANCANTE**                         |
| About tab content            | ❌       | **MANCANTE**                         |

**Ridondanze**: Nessuna evidente

**Raccomandazioni**:

1. ➕ Test unlock/edit mode per profile
2. ➕ Test save changes (username, email)
3. ➕ Test change password modal flow completo
4. ➕ Test preferences save & persist (almeno 1 per tipo)
5. ➖ I test "button is visible" sono deboli - meglio testare l'azione

---

### 3. files.spec.ts (9 test) ❌ 1 fallisce

**Cosa testa**:

- Accesso pagina files
- Entrambi i tab visibili (static, brim)
- Switch tra tab
- URL deep-linking (tab=static, tab=brim)
- Static tab: table visibile, upload button visibile
- BRIM tab: table O empty state

**Criteri di successo**:

- `files-page` visibile
- `files-tab-static`, `files-tab-brim` visibili con aria-selected corretto
- `files-table-static` visibile
- `files-table-brim` O `brim-empty-state` visibile
- `upload-button` visibile

**Problema attuale**:
Il test BRIM fallisce perché cerca `files-table-brim` O `brim-empty-state`, ma nessuno dei due è trovato. Probabile problema di timing o di rendering condizionale.

**Copertura funzionalità**:

| Funzionalità                       | Testata | Note                                 |
|------------------------------------|---------|--------------------------------------|
| Page access                        | ✅       |                                      |
| Tab navigation                     | ✅       |                                      |
| URL deep-linking                   | ✅       |                                      |
| Static files table                 | ✅       | Solo visibilità                      |
| BRIM files table                   | ⚠️      | Fallisce                             |
| File upload                        | ❌       | **MANCANTE** - solo bottone visibile |
| File download                      | ❌       | **MANCANTE**                         |
| File delete                        | ❌       | **MANCANTE**                         |
| File preview                       | ❌       | **MANCANTE**                         |
| Broker filter (BRIM)               | ❌       | **MANCANTE**                         |
| URL filters (filename, size, date) | ❌       | **MANCANTE**                         |
| View mode toggle (grid/list)       | ❌       | **MANCANTE**                         |

**Ridondanze**:

- `can switch to BRIM tab` e `can switch back to static tab` potrebbero essere un unico test

**Raccomandazioni**:

1. 🔧 Fix test BRIM - aggiungere wait o verificare rendering
2. ➕ Test upload file (almeno mock)
3. ➕ Test delete file
4. ➖ Rimuovere test ridondanti di switch tab (tenerne 1)

---

### 4. brokers.spec.ts (7 test) ⏳

**Cosa testa**:

- Accesso pagina brokers
- Add broker button visibile
- Refresh button visibile
- Apertura create broker modal
- Chiusura modal (click outside)
- Creazione broker con nome
- Click su broker card (se esistono)

**Criteri di successo**:

- `brokers-page` visibile
- `add-broker-button`, `brokers-refresh` visibili
- `broker-modal` si apre/chiude
- Broker card appare dopo creazione

**Copertura funzionalità**:

| Funzionalità                | Testata | Note                               |
|-----------------------------|---------|------------------------------------|
| Page access                 | ✅       |                                    |
| Create broker               | ✅       | Solo nome base                     |
| Create with initial balance | ❌       | **MANCANTE**                       |
| Edit broker                 | ❌       | **MANCANTE**                       |
| Delete broker               | ❌       | **MANCANTE**                       |
| Broker detail page          | ⚠️      | Solo click, non verifica contenuto |
| Cash deposit/withdraw       | ❌       | **MANCANTE**                       |
| Import files modal          | ❌       | **MANCANTE**                       |
| Broker card info display    | ❌       | **MANCANTE**                       |

**Ridondanze**: Nessuna

**Raccomandazioni**:

1. ➕ Test edit broker
2. ➕ Test delete broker con conferma
3. ➕ Test broker detail page contenuto
4. ➕ Test cash operations (se implementate)

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

### Alta Priorità (funzionalità core non testate)

1. **RegisterModal** - form completo, validazione, password strength
2. **ForgotPasswordModal** - flow completo
3. **Profile edit & save** - unlock, modifica, salvataggio
4. **Change password** - modal, validazione, submit
5. **File upload** - almeno static upload
6. **File delete** - con conferma
7. **Broker edit** - modal edit
8. **Broker delete** - con conferma

### Media Priorità

9. Preferences save & persist
10. Theme/language change in settings
11. Broker detail page content
12. BRIM broker filter
13. URL filters su files

### Bassa Priorità

14. About tab content
15. View mode toggle (grid/list)
16. File preview
17. File download

---

## 🎯 Piano di Azione Proposto

### Fase 1: Fix test esistenti

1. ✅ auth.spec.ts - OK
2. ✅ settings.spec.ts - OK
3. 🔧 files.spec.ts - Fix test BRIM
4. 🔧 brokers.spec.ts - Verificare che passino
5. 🔧 multi-user.spec.ts - Verificare che passino

### Fase 2: Aggiungere test mancanti critici

1. ➕ auth.spec.ts: Register modal, Forgot password
2. ➕ settings.spec.ts: Profile edit flow, Change password flow
3. ➕ files.spec.ts: Upload, Delete
4. ➕ brokers.spec.ts: Edit, Delete, Detail page

### Fase 3: Test secondari

- Preferences persistence
- Multi-user file isolation
- URL filters

---

## 📝 data-testid Inventory

### Già implementati ✅

```
# Auth
login-page, login-modal, login-form, login-username, login-password
login-submit, login-error, goto-register

# Layout
sidebar, logout-button, mobile-menu-toggle
language-selector, language-selector-button
dashboard-page

# Settings
settings-page, settings-tab-{profile,preferences,about,admin}
profile-tab, profile-username, profile-email
change-password-button, delete-account-button
preference-language, preference-currency, preference-theme
global-settings-tab

# Files
files-page, files-tab-static, files-tab-brim
files-table-static, files-table-brim
upload-button, brim-empty-state

# Brokers
brokers-page, add-broker-button, brokers-refresh
broker-card-{id}, broker-modal
```

### Da aggiungere per nuovi test

```
# Auth (per Register/Forgot)
register-modal, register-form, register-submit
register-username, register-email, register-password
password-strength-meter
forgot-modal, forgot-email, forgot-submit

# Settings (per edit flows)
profile-edit-toggle, profile-save-button
password-change-modal, password-current, password-new
password-confirm, password-change-submit

# Files (per upload/delete)
file-upload-zone, file-row-{id}, file-delete-{id}
delete-confirm-modal, delete-confirm-button

# Brokers (per edit/delete)
broker-edit-button-{id}, broker-delete-button-{id}
broker-detail-page, broker-name, broker-cash-balances
delete-broker-modal, delete-broker-confirm
```

---

## ✅ Lavoro Completato in Questa Sessione

### Componenti modificati con data-testid

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

### Test riscritti

- [x] auth.spec.ts - Language-agnostic + test dinamici lingua
- [x] settings.spec.ts - Language-agnostic
- [x] files.spec.ts - Language-agnostic (1 test ancora fallisce)
- [x] brokers.spec.ts - Language-agnostic
- [x] multi-user.spec.ts - Aggiornato selettori

### Fixture create

- [x] i18n-data.ts - Auto-discovery lingue da i18n/*.json

### Configurazione

- [x] playwright.config.ts - timeout 3s, open: 'never'
- [x] auth-helpers.ts - Aggiornato per usare data-testid

---

## 🤔 Domande Aperte

1. **Test upload file**: Serve mock del backend o test reale? (Playwright supporta file upload)
2. **Test delete**: Testare conferma dialog o assumere che funzioni?
3. **Coverage multilingua**: Il pattern con `SUPPORTED_LANGUAGES` è corretto o meglio testare solo 1 lingua per i test funzionali?
4. **Test negativi**: Aggiungere test per errori (es. creazione broker senza nome)?
