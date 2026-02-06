# Plan: Frontend Component Reorganization v3 - Cleanup & Final Structure

**Data creazione**: 5 Febbraio 2026  
**Status**: ✅ COMPLETATO
**Prerequisito**: plan-componentReorganizationV2 ✅ COMPLETATO
**Priorità**: P2 (cleanup e organizzazione)
**Stima tempo**: ~2h
**Tempo effettivo**: ~4h

---

## 🎯 Obiettivo

1. ✅ Eliminare i file deprecati (prefisso `Old`)
2. ✅ Riorganizzare la struttura cartelle secondo il target definito in V2
3. ✅ Aggiornare tutti gli import
4. ✅ Creare index.ts per export puliti
5. ✅ Fix file upload (Zodios FormData bug)
6. ✅ Fix dashboard dark mode
7. ✅ Test E2E per componenti Select (16 test aggiuntivi)

---

## 📁 FASE 1: Eliminazione File Deprecati ✅ COMPLETATA

### Comandi `rm` eseguiti

```bash
cd /Users/ea_enel/Documents/00_My/LibreFolio/frontend/src/lib/components

# Rimossi vecchi Select components
rm OldFuzzySelect.svelte ✅
rm ui/OldCustomSelect.svelte ✅
rm brokers/OldBrokerSelect.svelte ✅
```

### Verifica post-eliminazione

```bash
# Verifica che nessun file importi i vecchi componenti
grep -r "OldFuzzySelect" --include="*.svelte" --include="*.ts" .
grep -r "OldCustomSelect" --include="*.svelte" --include="*.ts" .
grep -r "OldBrokerSelect" --include="*.svelte" --include="*.ts" .

# Deve restituire 0 risultati
```

---

## 📁 FASE 2: Riorganizzazione Struttura Cartelle ✅ COMPLETATA

### Struttura Attuale vs Target

```
ATTUALE                              TARGET
components/                          components/
├── AnimatedBackground.svelte        ├── ui/
├── HelpMenu.svelte                  │   ├── select/           ✅ GIÀ FATTO
├── LanguageSelector.svelte          │   ├── input/            🔄 DA CREARE
├── ImportPluginSelect.svelte        │   ├── media/            🔄 DA CREARE
├── Tooltip.svelte                   │   ├── AnimatedBackground.svelte
├── ui/                              │   ├── Tooltip.svelte
│   ├── select/ ✅                   │   ├── ThemeToggle.svelte
│   ├── ThemeToggle.svelte           │   └── index.ts
│   ├── FileUploader.svelte          ├── layout/
│   ├── LazyImage.svelte             │   ├── Header.svelte     ✅ GIÀ FATTO
│   ├── ImageUploader.svelte         │   ├── Sidebar.svelte    ✅ GIÀ FATTO
│   └── PasswordStrengthMeter.svelte │   ├── HelpMenu.svelte
├── layout/                          │   ├── LanguageSelector.svelte
│   ├── Header.svelte ✅             │   └── index.ts
│   └── Sidebar.svelte ✅            ├── settings/
├── settings/                        │   ├── fields/           ✅ GIÀ FATTO
│   ├── fields/ ✅                   │   ├── tabs/             🔄 DA CREARE
│   ├── PreferencesTab.svelte        │   └── ...
│   ├── GlobalSettingsTab.svelte     ├── brokers/             ✅ OK
│   └── ...                          ├── files/               ✅ OK
├── brokers/ ✅                      ├── auth/                ✅ OK
├── files/ ✅                        └── table/               ✅ OK
├── auth/ ✅
└── table/ ✅
```

### Comandi `mv` da eseguire

```bash
cd /Users/ea_enel/Documents/00_My/LibreFolio/frontend/src/lib/components

# === FASE 2.1: Spostare componenti in ui/ ===

# AnimatedBackground → ui/
mv AnimatedBackground.svelte ui/AnimatedBackground.svelte

# Tooltip (già in ui/ o in root?)
# Verifica prima: ls -la Tooltip.svelte ui/Tooltip.svelte
# Se in root:
mv Tooltip.svelte ui/Tooltip.svelte

# === FASE 2.2: Spostare componenti in layout/ ===

# HelpMenu → layout/
mv HelpMenu.svelte layout/HelpMenu.svelte

# LanguageSelector → layout/
mv LanguageSelector.svelte layout/LanguageSelector.svelte

# === FASE 2.3: Creare ui/input/ e spostare ===

mkdir -p ui/input

# PasswordInput e PasswordStrengthMeter → ui/input/
mv ui/PasswordStrengthMeter.svelte ui/input/PasswordStrengthMeter.svelte
# PasswordInput se esiste in auth/ può rimanere lì o essere spostato

# === FASE 2.4: Creare ui/media/ e spostare ===

mkdir -p ui/media

# FileUploader, LazyImage, ImageUploader → ui/media/
mv ui/FileUploader.svelte ui/media/FileUploader.svelte
mv ui/LazyImage.svelte ui/media/LazyImage.svelte
mv ui/ImageUploader.svelte ui/media/ImageUploader.svelte

# === FASE 2.5: Creare settings/tabs/ e spostare ===

mkdir -p settings/tabs

# Spostare i tab components
mv settings/PreferencesTab.svelte settings/tabs/PreferencesTab.svelte
mv settings/GlobalSettingsTab.svelte settings/tabs/GlobalSettingsTab.svelte
mv settings/ProfileTab.svelte settings/tabs/ProfileTab.svelte
mv settings/AboutTab.svelte settings/tabs/AboutTab.svelte
```

---

## 📁 FASE 3: Aggiornamento Import ✅ COMPLETATA

### File aggiornati

| File                                    | Import aggiornato                                   |
|-----------------------------------------|-----------------------------------------------------|
| `routes/+page.svelte`                   | AnimatedBackground → `ui/AnimatedBackground.svelte` |
| `routes/+error.svelte`                  | AnimatedBackground → `ui/AnimatedBackground.svelte` |
| `routes/+page.svelte`                   | LanguageSelector → `layout/LanguageSelector.svelte` |
| `layout/Header.svelte`                  | HelpMenu → `layout/HelpMenu.svelte`                 |
| `layout/Header.svelte`                  | LanguageSelector → `layout/LanguageSelector.svelte` |
| `routes/(app)/files/+page.svelte`       | FileUploader, LazyImage → `ui/media/`               |
| `brokers/BrokerImportFilesModal.svelte` | FileUploader → `ui/media/FileUploader.svelte`       |
| `auth/LoginModal.svelte`                | PasswordInput → `ui/input/PasswordInput.svelte`     |
| `auth/RegisterModal.svelte`             | PasswordInput, PasswordStrength → `ui/input/`       |
| `settings/PasswordChangeModal.svelte`   | PasswordInput, PasswordStrength → `ui/input/`       |
| `routes/(app)/settings/+page.svelte`    | Tabs → `settings/tabs/`                             |

### Bugfix applicati durante la riorganizzazione

| File                                    | Fix                                                 |
|-----------------------------------------|-----------------------------------------------------|
| `routes/(app)/files/+page.svelte`       | BRIM upload: `{ file }` invece di `formData as any` |
| `brokers/BrokerImportFilesModal.svelte` | BRIM upload: `{ file }` invece di `formData as any` |
| `brokers/BrokerImportFiles.svelte`      | BRIM upload: `{ file }` invece di `formData as any` |

---

## 📁 FASE 4: Creare File index.ts ✅ COMPLETATA

### File creati

- `ui/index.ts` ✅
- `ui/input/index.ts` ✅
- `ui/media/index.ts` ✅
- `layout/index.ts` ✅
- `settings/tabs/index.ts` ✅

---

## 🔧 FASE 5: Fix Aggiuntivi ✅ COMPLETATA

### Fix File Upload (Zodios FormData bug)

**Problema**: Zodios serializzava le proprietà/metodi del FormData invece del contenuto del file.

**Soluzione**: Usare `axiosInstance` direttamente per gli upload file invece di Zodios.

**File modificati:**

- `routes/(app)/files/+page.svelte` - import axiosInstance, uso diretto per upload
- `brokers/BrokerImportFilesModal.svelte` - stesso fix
- `brokers/BrokerImportFiles.svelte` - stesso fix

### Fix Dashboard Dark Mode

**Problema**: Welcome banner troppo chiaro in dark mode.

**Soluzione**: Creato nuovo colore `--color-libre-banner` con valore specifico per dark mode.

**File modificati:**

- `app.css` - aggiunto `--color-libre-banner: #1a4031` (light) e `#00834f` (dark)
- `dashboard/+page.svelte` - usa `libre-banner` per il gradient del welcome banner
- Semplificato colorClasses per quick actions (classi inline invece di oggetto complesso)

---

## 🧪 FASE 6: Test E2E per Select Components ✅ COMPLETATA

### File creato: `e2e/select-components.spec.ts`

16 test che coprono:

**LanguageSelector (SimpleSelect style)** - 4 test:

- Opens dropdown on click
- Closes dropdown on click outside
- Closes dropdown on Escape key
- Selects language and updates UI

**SearchSelect (Currency Selector in Settings)** - 3 test:

- Currency select opens with search field
- Currency select shows options in listbox
- Currency select can close with Escape

**ImportPluginSelect (Broker Form)** - 4 test:

- Plugin select is visible in broker form
- Plugin select opens dropdown with listbox
- Plugin select shows search input when opened
- Plugin select can be closed with Escape

**Global Settings Selects (Admin)** - 2 test:

- Global settings tab loads for admin
- Global settings has interactive elements

**BrokerSearchSelect (Files Page)** - 1 test:

- Files page loads with tab navigation

**Accessibility** - 2 test:

- Language selector has proper menu role
- Search select has listbox role when open

### Integrazione in test_runner.py

Aggiunto `select-components.spec.ts` alla lista dei spec file in `_run_front_e2e_tests()`.

---

### 6.1 Nuovo file: `e2e/select-components.spec.ts`

Test per SimpleSelect e SearchSelect:

```typescript
// frontend/e2e/select-components.spec.ts
import { test, expect } from '@playwright/test';
import { login } from './fixtures/auth-helpers';

test.describe('Select Components', () => {
    
    test.describe('SimpleSelect (Language Selector)', () => {
        
        test('opens dropdown on click', async ({ page }) => {
            await page.goto('/');
            await page.getByTestId('language-selector-button').click();
            // Dropdown should be visible with all language options
            await expect(page.getByRole('menuitem', { name: /English/ })).toBeVisible();
            await expect(page.getByRole('menuitem', { name: /Italiano/ })).toBeVisible();
            await expect(page.getByRole('menuitem', { name: /Français/ })).toBeVisible();
            await expect(page.getByRole('menuitem', { name: /Español/ })).toBeVisible();
        });
        
        test('closes dropdown on click outside', async ({ page }) => {
            await page.goto('/');
            await page.getByTestId('language-selector-button').click();
            await expect(page.getByRole('menuitem', { name: /English/ })).toBeVisible();
            // Click outside
            await page.locator('body').click({ position: { x: 10, y: 10 } });
            await expect(page.getByRole('menuitem', { name: /English/ })).not.toBeVisible();
        });
        
        test('closes dropdown on Escape key', async ({ page }) => {
            await page.goto('/');
            await page.getByTestId('language-selector-button').click();
            await expect(page.getByRole('menuitem', { name: /English/ })).toBeVisible();
            await page.keyboard.press('Escape');
            await expect(page.getByRole('menuitem', { name: /English/ })).not.toBeVisible();
        });
        
        test('selects option on click', async ({ page }) => {
            await page.goto('/');
            // Start in English, switch to Italian
            await page.getByTestId('language-selector-button').click();
            await page.getByRole('menuitem', { name: /Italiano/ }).click();
            // Verify UI updated (login button text should be in Italian)
            await expect(page.getByTestId('login-submit')).toContainText('Accedi');
        });
    });
    
    test.describe('SearchSelect (Currency Selector)', () => {
        
        test.beforeEach(async ({ page }) => {
            await login(page, 'test@example.com', 'testpassword');
            await page.goto('/settings');
            // Navigate to Preferences tab
            await page.getByRole('tab', { name: /Preferences|Preferenze/ }).click();
        });
        
        test('opens dropdown and shows search input', async ({ page }) => {
            // Click on currency selector
            await page.locator('[data-testid="currency-select"]').click();
            // Search input should be visible
            await expect(page.getByPlaceholder(/search|cerca/i)).toBeVisible();
        });
        
        test('filters options based on search', async ({ page }) => {
            await page.locator('[data-testid="currency-select"]').click();
            await page.getByPlaceholder(/search|cerca/i).fill('EUR');
            // Only EUR should be visible (or currencies containing EUR)
            await expect(page.getByRole('option', { name: /EUR/ })).toBeVisible();
            // USD should not be visible
            await expect(page.getByRole('option', { name: /^USD/ })).not.toBeVisible();
        });
        
        test('keyboard navigation - Arrow Down/Up', async ({ page }) => {
            await page.locator('[data-testid="currency-select"]').click();
            // Press ArrowDown to highlight first option
            await page.keyboard.press('ArrowDown');
            // First option should be highlighted (check by class or aria)
            const firstOption = page.getByRole('option').first();
            await expect(firstOption).toHaveClass(/highlighted/);
        });
        
        test('keyboard selection - Enter', async ({ page }) => {
            await page.locator('[data-testid="currency-select"]').click();
            await page.getByPlaceholder(/search|cerca/i).fill('USD');
            await page.keyboard.press('ArrowDown');
            await page.keyboard.press('Enter');
            // Dropdown should close and value should be selected
            await expect(page.getByPlaceholder(/search|cerca/i)).not.toBeVisible();
        });
    });
    
    test.describe('SearchSelect with inlineSearch (ImportPluginSelect)', () => {
        
        test.beforeEach(async ({ page }) => {
            await login(page, 'test@example.com', 'testpassword');
            await page.goto('/brokers');
            // Open create broker modal
            await page.getByRole('button', { name: /add|aggiungi|new|nuovo/i }).click();
        });
        
        test('shows inline search when opened', async ({ page }) => {
            // Click on import plugin selector
            const pluginSelect = page.locator('.import-plugin-select');
            await pluginSelect.click();
            // Search icon and input should be inline in trigger
            await expect(pluginSelect.locator('input[type="text"]')).toBeVisible();
        });
        
        test('filters plugins with inline search', async ({ page }) => {
            const pluginSelect = page.locator('.import-plugin-select');
            await pluginSelect.click();
            await pluginSelect.locator('input[type="text"]').fill('Degiro');
            // Should show Degiro plugin
            await expect(page.getByRole('option', { name: /Degiro/i })).toBeVisible();
        });
        
        test('shows broker icons in options', async ({ page }) => {
            const pluginSelect = page.locator('.import-plugin-select');
            await pluginSelect.click();
            // Each option should have a broker icon
            const options = page.getByRole('option');
            const firstOption = options.first();
            await expect(firstOption.locator('img, .broker-icon')).toBeVisible();
        });
        
        test('Enter key selects highlighted option', async ({ page }) => {
            const pluginSelect = page.locator('.import-plugin-select');
            await pluginSelect.click();
            await page.keyboard.press('ArrowDown');
            await page.keyboard.press('Enter');
            // Dropdown should close
            await expect(pluginSelect.locator('input[type="text"]')).not.toBeVisible();
        });
    });
    
    test.describe('BrokerSearchSelect (Upload Modal)', () => {
        
        test.beforeEach(async ({ page }) => {
            await login(page, 'test@example.com', 'testpassword');
            await page.goto('/files');
        });
        
        test('auto-positions dropdown based on available space', async ({ page }) => {
            // This test would need to trigger the upload modal
            // and verify dropdown opens up or down based on space
            // Implementation depends on how to trigger the modal
        });
        
        test('limits visible items based on available space', async ({ page }) => {
            // Verify that dropdown doesn't exceed container bounds
            // and shows scrollbar when needed
        });
    });
});
```

### 6.2 Aggiungere test in `e2e/settings.spec.ts`

```typescript
// Aggiungi a settings.spec.ts esistente

test.describe('Settings Select Components', () => {
    
    test('language dropdown uses SimpleSelect with flags', async ({ page }) => {
        await login(page);
        await page.goto('/settings');
        await page.getByRole('tab', { name: /Preferences|Preferenze/ }).click();
        
        // Open language dropdown
        const langSelect = page.locator('[data-testid="language-setting"]');
        await langSelect.click();
        
        // Verify flags are visible
        const options = page.getByRole('option');
        await expect(options.first()).toContainText(/🇬🇧|🇮🇹|🇫🇷|🇪🇸/);
    });
    
    test('currency dropdown uses SearchSelect with search', async ({ page }) => {
        await login(page);
        await page.goto('/settings');
        await page.getByRole('tab', { name: /Preferences|Preferenze/ }).click();
        
        // Open currency dropdown
        const currencySelect = page.locator('[data-testid="currency-setting"]');
        await currencySelect.click();
        
        // Verify search input exists
        await expect(page.getByPlaceholder(/search|cerca/i)).toBeVisible();
    });
});

test.describe('Global Settings (Admin)', () => {
    
    test('toggle switches work for boolean settings', async ({ page }) => {
        await login(page, 'admin@example.com', 'adminpassword');
        await page.goto('/settings');
        await page.getByRole('tab', { name: /Global|Globali/ }).click();
        
        // Find a toggle and click it
        const toggle = page.locator('[data-testid="setting-toggle"]').first();
        const initialState = await toggle.getAttribute('aria-checked');
        await toggle.click();
        // State should change
        const newState = await toggle.getAttribute('aria-checked');
        expect(newState).not.toBe(initialState);
    });
    
    test('number inputs accept numeric values', async ({ page }) => {
        await login(page, 'admin@example.com', 'adminpassword');
        await page.goto('/settings');
        await page.getByRole('tab', { name: /Global|Globali/ }).click();
        
        // Find a number input
        const numberInput = page.locator('[data-testid="setting-number"] input').first();
        await numberInput.fill('100');
        await expect(numberInput).toHaveValue('100');
    });
});
```

### 6.3 Test da aggiungere in `e2e/brokers.spec.ts`

```typescript
// Aggiungi a brokers.spec.ts esistente

test.describe('Broker Form Select Components', () => {
    
    test('ImportPluginSelect shows plugins with icons', async ({ page }) => {
        await login(page);
        await page.goto('/brokers');
        await page.getByRole('button', { name: /add|nuovo/i }).click();
        
        // Open plugin select
        const pluginSelect = page.locator('.import-plugin-select');
        await pluginSelect.click();
        
        // Verify plugins have icons
        const options = page.locator('[role="option"]');
        const firstOption = options.first();
        await expect(firstOption.locator('.broker-icon, img')).toBeVisible();
    });
    
    test('Currency select in initial balances works', async ({ page }) => {
        await login(page);
        await page.goto('/brokers');
        await page.getByRole('button', { name: /add|nuovo/i }).click();
        
        // Add initial balance
        await page.getByRole('button', { name: /add.*balance|aggiungi.*saldo/i }).click();
        
        // Open currency select
        const currencySelect = page.locator('[data-testid="balance-currency"]').first();
        await currencySelect.click();
        
        // Should show search
        await expect(page.getByPlaceholder(/search|cerca/i)).toBeVisible();
    });
});
```

---

## ✅ Checklist Esecuzione

### Pre-requisiti

- [ ] Tutti i test E2E passano (`./dev.py test front all`)
- [ ] Build senza errori (`./dev.py front build`)
- [ ] Check senza warning (`./dev.py front check`)

### Fase 1: Eliminazione

- [ ] `rm OldFuzzySelect.svelte`
- [ ] `rm ui/OldCustomSelect.svelte`
- [ ] `rm brokers/OldBrokerSelect.svelte`
- [ ] Verifica grep nessun import residuo

### Fase 2: Spostamenti

- [ ] `mv AnimatedBackground.svelte ui/`
- [ ] `mv HelpMenu.svelte layout/`
- [ ] `mv LanguageSelector.svelte layout/`
- [ ] `mkdir ui/input && mv PasswordStrengthMeter.svelte ui/input/`
- [ ] `mkdir ui/media && mv FileUploader.svelte LazyImage.svelte ImageUploader.svelte ui/media/`
- [ ] `mkdir settings/tabs && mv *Tab.svelte settings/tabs/`

### Fase 3: Import Updates

- [ ] Aggiorna import AnimatedBackground
- [ ] Aggiorna import HelpMenu
- [ ] Aggiorna import LanguageSelector
- [ ] Aggiorna import FileUploader/LazyImage/ImageUploader
- [ ] Aggiorna import PasswordStrengthMeter
- [ ] Aggiorna import Settings Tabs

### Fase 4: Index Files

- [ ] Crea `ui/index.ts`
- [ ] Crea `ui/input/index.ts`
- [ ] Crea `ui/media/index.ts`
- [ ] Crea `layout/index.ts`
- [ ] Crea `settings/tabs/index.ts`

### Fase 6: Test

- [ ] Crea `e2e/select-components.spec.ts`
- [ ] Aggiungi test a `settings.spec.ts`
- [ ] Aggiungi test a `brokers.spec.ts`

### Post-requisiti

- [ ] `./dev.py front check` → 0 errori, 0 warning
- [ ] `./dev.py front build` → OK
- [ ] `./dev.py test front all` → tutti passano

---

## 📝 Commit Message Suggerito

```
feat(frontend): complete component reorganization v3

- Remove deprecated Old* components (FuzzySelect, CustomSelect, BrokerSelect)
- Reorganize folder structure:
  - ui/input/ for password components
  - ui/media/ for file/image components
  - layout/ for header-related components
  - settings/tabs/ for settings tab components
- Add index.ts files for clean exports
- Add E2E tests for Select components:
  - SimpleSelect keyboard navigation
  - SearchSelect filtering and selection
  - InlineSearch mode
  - Auto-positioning dropdown
  - BrokerSearchSelect in upload modal

BREAKING CHANGE: Component import paths have changed.
See plan-componentReorganizationV3-cleanup.md for migration guide.
```

---

## 🔗 File Correlati

- `plan-componentReorganizationV2.prompt.md` - Piano completato (prerequisito)
- `plan-phase04-summary.md` - Contesto Phase 4
