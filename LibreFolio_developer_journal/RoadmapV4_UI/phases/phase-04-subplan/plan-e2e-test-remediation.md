# Plan: E2E Test Remediation

**Data creazione**: 2 Febbraio 2026  
**Ultimo aggiornamento**: 3 Febbraio 2026  
**Status**: ✅ COMPLETATO (~100 test pass + 28 gallery pass)  
**Priorità**: P1  
**Dipendenze**: plan-frontendTesting.md (infrastruttura completata)

> 📋 **Analisi dettagliata**: Vedi [e2e-test-analysis.md](./e2e-test-analysis.md) per gap analysis completa

---

## 📊 Stato Test (3 Feb 2026)

| Suite              | Test | Status | Note                                          |
|--------------------|------|--------|-----------------------------------------------|
| auth.spec.ts       | 17   | ✅ PASS | +7 test Register/Forgot modals                |
| settings.spec.ts   | 23   | ✅ PASS | +10 test Profile edit, Change password, About |
| files.spec.ts      | 12   | ✅ PASS | +3 test toggle uploader, view mode            |
| brokers.spec.ts    | 18   | ✅ PASS | +11 test edit/delete/detail/import modal      |
| multi-user.spec.ts | 2    | ✅ PASS | Isolamento + unicità nomi globale             |
| gallery.spec.ts    | 28   | ✅ PASS | Light/dark theme, 4 lingue, ~224 screenshots  |

**Totale: ~100 test funzionali + 28 gallery = ~128 test PASS**

### Infrastruttura Aggiunta

- ✅ Build check automatico (`_ensure_frontend_build()` via `cli_base.py`) - ricompila solo se sorgenti cambiati
- ✅ db populate automatico prima di gallery
- ✅ freezeAnimations() per screenshot consistenti
- ✅ Mobile menu toggle fix per gallery

---

## 📝 Changelog

### 2 Febbraio 2026 - Sessione 1 (COMPLETATA)

- ✅ Configurato `playwright.config.ts` con `open: 'never'` per evitare report HTML interattivo
- ✅ Creato `e2e/fixtures/i18n-data.ts` per test dinamici delle lingue
- ✅ Aggiunto `data-testid` a:
    - `LoginModal.svelte`: login-modal, login-form, login-username, login-password, login-submit, login-error, goto-register
    - `RegisterModal.svelte`: register-modal, register-form
    - `Sidebar.svelte`: sidebar, logout-button
    - `Header.svelte`: mobile-menu-toggle
    - `LanguageSelector.svelte`: language-selector, language-selector-button
    - `PasswordInput.svelte`: testId prop
    - `dashboard/+page.svelte`: dashboard-page
    - `settings/+page.svelte`: settings-page, settings-tab-{profile,preferences,about,admin}
    - `ProfileTab.svelte`: profile-tab, profile-username, profile-email, change-password-button, delete-account-button
    - `PreferencesTab.svelte`: preference-language, preference-currency, preference-theme
    - `GlobalSettingsTab.svelte`: global-settings-tab
    - `files/+page.svelte`: files-page, files-tab-static, files-tab-brim, upload-button
    - `FilesTable.svelte`: files-table-{type}
    - `brokers/+page.svelte`: brokers-page, add-broker-button, brokers-refresh
    - `BrokerCard.svelte`: broker-card-{id}
    - `BrokerModal.svelte`: broker-modal
- ✅ Riscritto `auth-helpers.ts`:
    - login usa data-testid (login-form, login-username, login-password, login-submit)
    - logout usa logout-button
    - setLanguage usa language-selector-button
- ✅ Riscritto `auth.spec.ts`:
    - Test language-agnostic con data-testid
    - Test dinamici per tutte le lingue supportate (auto-discovery da i18n/*.json)
- ✅ Riscritto `settings.spec.ts`: Test language-agnostic con data-testid per tabs e campi
- ✅ Riscritto `files.spec.ts`: Test language-agnostic per tabs e tabelle
- ✅ Riscritto `brokers.spec.ts`: Test language-agnostic per CRUD brokers
- ✅ Aggiornato `multi-user.spec.ts`: Usa data-testid per broker creation
- ✅ Aggiornato `gallery.spec.ts`: Usa data-testid dove possibile

---

## Obiettivo

Aggiornare i test E2E Playwright per coprire tutte le funzionalità frontend attualmente implementate e funzionanti.

---

## 📊 Analisi Stato Attuale

### Frontend Implementato (da Phase 0 a Phase 4)

#### Auth System (Phase 0-2)

- ✅ Login page con AnimatedBackground
- ✅ LoginModal con validazione
- ✅ RegisterModal con password strength
- ✅ ForgotPasswordModal
- ✅ Language selector (4 lingue)
- ✅ Auto-redirect se già autenticato

#### Layout (Phase 3)

- ✅ Sidebar con navigazione
- ✅ Header con titolo dinamico
- ✅ Mobile responsive (burger menu)
- ✅ User menu con logout
- ✅ Error page 404 personalizzata

#### Settings (Phase 3 + Phase 4 unification)

- ✅ ProfileTab: username, email, edit inline, delete account
- ✅ PreferencesTab: lingua, valuta, tema
- ✅ GlobalSettingsTab (admin only): max upload size, registration
- ✅ AboutTab: versione, credits
- ✅ PasswordChangeModal

#### Dashboard (Phase 3)

- ✅ Quick stats cards (placeholder values)
- ✅ Quick actions links

#### Brokers (Phase 4)

- ✅ BrokerCard con icona, cash balances
- ✅ BrokerModal per create/edit
- ✅ BrokerForm con initial balances
- ✅ BrokerIcon con fallback chain
- ✅ Broker detail page `/brokers/[id]`
- ✅ CashBalanceCard con deposit/withdraw
- ✅ CashTransactionModal
- ✅ DeleteBrokerDialog
- ✅ BrokerSelect fuzzy search
- ✅ BrokerImportFilesModal

#### Files (Phase 4)

- ✅ FilesTable con DataTable
- ✅ Tabs: static resources, broker reports (BRIM)
- ✅ URL filters (`?tab=brim&broker=1&filename=X`)
- ✅ Upload con drag & drop
- ✅ Preview text/image
- ✅ Download con nome originale
- ✅ Delete con conferma

#### Componenti Condivisi

- ✅ DataTable con filtri avanzati
- ✅ FuzzySelect
- ✅ LanguageSelector
- ✅ Modal base
- ✅ LazyImage
- ✅ Toggle, Tooltip, etc.

---

## 🧪 Test da Aggiornare/Creare

### 1. auth.spec.ts - ✅ Parzialmente funzionante

**Stato attuale**: 2/6 test passano

**Test da aggiornare**:

```typescript
// Questi test richiedono data-testid sui componenti
test('successful login redirects to dashboard')  // Serve data-testid su form
test('logout returns to login page')             // Serve data-testid="user-menu"
test('language selector changes UI')             // Serve data-testid="language-selector"
```

**Azione richiesta**:

- Aggiungere `data-testid` a LoginModal, Sidebar user section, LanguageSelector

### 2. settings.spec.ts - 🔴 Da rifare

**Componenti reali da testare**:

- ProfileTab: edit username/email, delete account
- PreferencesTab: change language, currency, theme
- GlobalSettingsTab: admin only, max upload size
- PasswordChangeModal

**Test da scrivere**:

```typescript
test.describe('Settings', () => {
    test('user can access settings page')
    test('profile tab shows user info')
    test('can edit username with save/undo')
    test('can change language preference')
    test('can change currency preference')
    test('admin can see global settings tab')
    test('non-admin cannot see global settings tab')
    test('can open password change modal')
})
```

### 3. brokers.spec.ts - 🔴 Da rifare

**Componenti reali da testare**:

- BrokerCard click → detail page
- BrokerModal create/edit
- Initial balances in form
- Broker detail page
- CashTransactionModal (deposit/withdraw)
- Delete broker

**Test da scrivere**:

```typescript
test.describe('Brokers', () => {
    test('broker list shows cards')
    test('can create broker with initial balance')
    test('broker card click navigates to detail')
    test('broker detail shows cash balances')
    test('can edit broker via modal')
    test('can delete broker with confirmation')
    test('can deposit cash')
    test('can withdraw cash')
})
```

### 4. files.spec.ts - 🔴 Da rifare

**Componenti reali da testare**:

- FilesTable con tabs
- URL filters funzionanti
- Upload file
- Preview file
- Download file
- Delete file

**Test da scrivere**:

```typescript
test.describe('Files', () => {
    test('files page shows tabs')
    test('tab=static shows static resources')
    test('tab=brim shows broker reports')
    test('URL filter broker works')
    test('can upload file')
    test('can preview text file')
    test('can download file')
    test('can delete file')
})
```

### 5. multi-user.spec.ts - 🟡 Struttura OK, richiede broker funzionanti

**Test attuali**: 2 test, dipendono da broker CRUD

**Azione**: Dopo che brokers.spec.ts funziona, questi dovrebbero passare

### 6. gallery.spec.ts - 🟡 Struttura OK, richiede componenti con data-testid

**Azione**: Screenshot funzioneranno quando i componenti avranno i selettori corretti

---

## 📋 Checklist data-testid da Aggiungere

### Auth Components

- [x] `LoginModal.svelte` → `login-modal`, `login-form`, `login-username`, `login-password`, `login-submit`, `login-error`
- [x] `RegisterModal.svelte` → `register-modal`, `register-form`
- [ ] `ForgotPasswordModal.svelte` → `forgot-form` (da aggiungere)
- [x] `PasswordInput.svelte` → prop `testId`

### Layout Components

- [x] `Sidebar.svelte` → `sidebar`, `logout-button`
- [x] `Header.svelte` → `mobile-menu-toggle`
- [x] `LanguageSelector.svelte` → `language-selector`, `language-selector-button`

### Settings Components

- [x] `ProfileTab.svelte` → `profile-tab`, `profile-username`, `profile-email`, `change-password-button`, `delete-account-button`
- [x] `PreferencesTab.svelte` → `preference-language`, `preference-currency`, `preference-theme`
- [x] `GlobalSettingsTab.svelte` → `global-settings-tab`

### Broker Components

- [x] `BrokerCard.svelte` → `broker-card-{id}`
- [x] `BrokerModal.svelte` → `broker-modal`
- [ ] `BrokerForm.svelte` → `broker-form`, `broker-name-input` (da aggiungere per test avanzati)
- [ ] `DeleteBrokerDialog.svelte` → `delete-broker-confirm` (da aggiungere)
- [ ] `CashTransactionModal.svelte` → `cash-transaction-modal` (da aggiungere)

### Files Components

- [x] `FilesTable.svelte` → `files-table-{type}`
- [x] Tab buttons → `files-tab-static`, `files-tab-brim`
- [x] Upload button → `upload-button`

### Pages

- [x] `dashboard/+page.svelte` → `dashboard-page`
- [x] `settings/+page.svelte` → `settings-page`, `settings-tab-{profile,preferences,about,admin}`
- [x] `files/+page.svelte` → `files-page`
- [x] `brokers/+page.svelte` → `brokers-page`, `add-broker-button`, `brokers-refresh`

---

## 🚀 Piano di Implementazione

### Fase 1: Aggiungere data-testid auth/layout/settings (1h)

1. Auth components (LoginModal, RegisterModal, ForgotPasswordModal)
2. Layout components (Sidebar, Header, LanguageSelector)
3. Settings components (ProfileTab, PreferencesTab, GlobalSettingsTab)

### Fase 2: Fix auth.spec.ts (30min)

1. Aggiornare selettori per usare data-testid
2. Verificare tutti i 6 test passano

### Fase 3: Riscrivere settings.spec.ts (1h)

1. Test realistici basati su componenti esistenti
2. Coprire ProfileTab, PreferencesTab, GlobalSettingsTab

### Fase 4: Aggiungere data-testid files (30min)

1. FilesTable, tabs, upload zone

### Fase 5: Riscrivere files.spec.ts (1h)

1. Test tabs e URL filters
2. Test upload/download/delete
3. **NOTA**: FilesTable è usato anche in BrokerImportFilesModal, quindi va testato prima

### Fase 6: Aggiungere data-testid brokers (30min)

1. BrokerCard, BrokerModal, BrokerForm
2. CashTransactionModal, DeleteBrokerDialog

### Fase 7: Riscrivere brokers.spec.ts (1.5h)

1. Test CRUD broker
2. Test cash transactions
3. Test broker detail
4. Test import files modal (usa FilesTable già testato)

### Fase 8: Verificare multi-user.spec.ts (30min)

1. Dovrebbe passare dopo brokers.spec.ts

### Fase 9: Gallery screenshots (30min)

1. Verificare gallery genera screenshot corretti

---

## 📊 Stima Totale

| Fase                                | Tempo  | Note                                    |
|-------------------------------------|--------|-----------------------------------------|
| 1. data-testid auth/layout/settings | 1h     | Modifiche semplici                      |
| 2. Fix auth.spec.ts                 | 30min  | Selettori da aggiornare                 |
| 3. Riscrivere settings.spec.ts      | 1h     | Test realistici                         |
| 4. data-testid files                | 30min  | FilesTable, tabs                        |
| 5. Riscrivere files.spec.ts         | 1h     | Test tabs/upload - **prima di brokers** |
| 6. data-testid brokers              | 30min  | Più componenti                          |
| 7. Riscrivere brokers.spec.ts       | 1.5h   | Test CRUD + import modal                |
| 8. Verificare multi-user            | 30min  | Dipende da brokers                      |
| 9. Gallery test                     | 30min  | Verifica screenshot                     |
| **TOTALE**                          | **7h** |                                         |

---

## 🎯 Criteri di Successo

### Implementazione Completata ✅

- [x] Tutti i componenti hanno `data-testid` appropriati
- [x] Test riscritti per essere language-agnostic
- [x] Test dinamici per le lingue (auto-discovery da i18n/*.json)
- [x] multi-user.spec.ts aggiornato con data-testid
- [x] gallery.spec.ts aggiornato con data-testid

### Da Verificare con Esecuzione Test

- [ ] `./dev.py test front auth` - 10 test (5 core + 1 lang selector + 4 lingue)
- [ ] `./dev.py test front settings` - 12 test
- [ ] `./dev.py test front files` - 9 test
- [ ] `./dev.py test front brokers` - 7 test
- [ ] `./dev.py test front multi-user` - 2 test
- [ ] `./dev.py test front all` - tutti pass
- [ ] `./dev.py mkdocs gallery` genera screenshot corretti

---

## 📋 Riepilogo data-testid Aggiunti

| Componente        | data-testid                                                                                       |
|-------------------|---------------------------------------------------------------------------------------------------|
| LoginModal        | login-modal, login-form, login-username, login-password, login-submit, login-error, goto-register |
| RegisterModal     | register-modal, register-form                                                                     |
| Sidebar           | sidebar, logout-button                                                                            |
| Header            | mobile-menu-toggle                                                                                |
| LanguageSelector  | language-selector, language-selector-button                                                       |
| PasswordInput     | (prop testId)                                                                                     |
| Dashboard page    | dashboard-page                                                                                    |
| Settings page     | settings-page, settings-tab-{profile,preferences,about,admin}                                     |
| ProfileTab        | profile-tab, profile-username, profile-email, change-password-button, delete-account-button       |
| PreferencesTab    | preference-language, preference-currency, preference-theme                                        |
| GlobalSettingsTab | global-settings-tab                                                                               |
| Files page        | files-page, files-tab-static, files-tab-brim, upload-button                                       |
| FilesTable        | files-table-{static\|brim}                                                                        |
| Brokers page      | brokers-page, add-broker-button, brokers-refresh                                                  |
| BrokerCard        | broker-card-{id}                                                                                  |
| BrokerModal       | broker-modal                                                                                      |
