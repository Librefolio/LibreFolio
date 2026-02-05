# Plan: Frontend Component Reorganization v2

**Data creazione**: 5 Febbraio 2026  
**Status**: 📋 PIANIFICATO  
**Priorità**: P1 (fondamentale per manutenibilità)
**Stima tempo**: ~8-10h

---

## 🎯 Obiettivo

Riorganizzare completamente i componenti frontend per:
1. Eliminare duplicazioni di codice (5 implementazioni dropdown diverse)
2. Migrare tutto a Svelte 5 runes (`$state`, `$derived`, `$effect`)
3. Struttura cartelle per **categoria funzionale**
4. Componenti slot-based per rendering flessibile
5. Mantenere tutti i test E2E passanti

---

## 📊 Analisi Stato Attuale

### Componenti Select Esistenti (5 implementazioni!)

| Componente | Svelte | Ricerca | Click Outside | Keyboard | Slot Item |
|------------|--------|---------|---------------|----------|-----------|
| `FuzzySelect` | 4 | ✅ fuzzy | ✅ onMount | ✅ full | ❌ hardcoded |
| `CustomSelect` | 4 | ❌ | ✅ onMount | Escape only | ❌ hardcoded |
| `BrokerSelect` | 5 | ✅ inline | ✅ $effect | ✅ full | ❌ hardcoded |
| `ImportPluginSelect` | 4 | ❌ native | - | - | - |
| `LanguageSelector` | 4 | ❌ | ✅ inline | Escape only | ❌ hardcoded |

### Problemi Identificati
- **~800 righe** di logica dropdown duplicata
- `GlobalSettingsTab` è **855 righe** con HTML inline ripetuto
- Mix Svelte 4/5 causa inconsistenze
- File sparsi senza logica (FuzzySelect in root, CustomSelect in ui/)

---

## 🏗️ Architettura Target

### Gerarchia Select Components

```
ui/select/
├── BaseDropdown.svelte      # Logica pura: open/close, click outside, keyboard base
├── SimpleSelect.svelte      # Senza ricerca, slot per items
├── SearchSelect.svelte      # Con ricerca fuzzy, slot per items  
├── types.ts                 # Interfacce comuni
└── index.ts                 # Re-export
```

### Componenti Settings Fields

```
settings/fields/
├── SettingField.svelte      # Base wrapper (label, hint, actions)
├── SettingSelect.svelte     # Usa SimpleSelect
├── SettingSearchSelect.svelte # Usa SearchSelect (currency)
├── SettingToggle.svelte     # Boolean on/off
├── SettingNumber.svelte     # Input numerico con unità
├── SettingText.svelte       # Input testo (esistente, da refactorare)
└── index.ts
```

### Struttura Cartelle Finale

```
components/
├── ui/
│   ├── select/              # NEW: famiglia select unificata
│   ├── input/               # PasswordInput, PasswordStrength
│   ├── media/               # LazyImage, FileUploader, ImageUploader
│   ├── AnimatedBackground.svelte
│   ├── Tooltip.svelte
│   ├── ThemeToggle.svelte   # 🔄 da root
│   └── index.ts
├── layout/
│   ├── Header.svelte
│   ├── Sidebar.svelte
│   ├── HelpMenu.svelte      # 🔄 da root
│   ├── LanguageSelector.svelte  # 🔄 da root (usa SimpleSelect)
│   └── index.ts
├── settings/
│   ├── fields/              # NEW: famiglia setting fields
│   ├── tabs/                # ProfileTab, PreferencesTab, GlobalSettingsTab, AboutTab
│   ├── SettingsLayout.svelte
│   ├── PasswordChangeModal.svelte
│   └── index.ts
├── brokers/                 # Usa ui/select/SearchSelect
├── files/
├── auth/
└── table/
```

---

## 📋 Piano di Implementazione Dettagliato

### FASE 1: Infrastruttura Base Select (2h)

#### Step 1.1: Creare `ui/select/types.ts`
```typescript
export interface SelectOption {
    value: string;           // Chiave univoca
    label: string;           // Testo display
    searchText?: string;     // Testo aggiuntivo per ricerca
    disabled?: boolean;
    data?: unknown;          // Dati custom per slot
}

export interface BaseDropdownProps {
    disabled?: boolean;
    dropdownPosition?: 'top' | 'bottom' | 'auto';
}
```

#### Step 1.2: Creare `ui/select/BaseDropdown.svelte` (Svelte 5)
- Props: `disabled`, `dropdownPosition`
- State: `isOpen` con `$state`
- Logic: click outside con `$effect`, keyboard base (Escape)
- Slots: `trigger`, `content`
- Export `open()`, `close()`, `toggle()` per controllo esterno

#### Step 1.3: Creare `ui/select/SimpleSelect.svelte` (Svelte 5)
- Usa `BaseDropdown`
- Props: `options: SelectOption[]`, `value`, `placeholder`, `loading`
- Snippet: `item` per rendering custom (default: `{option.label}`)
- Keyboard: ArrowUp/Down, Enter per selezione
- Events: `onchange`

#### Step 1.4: Creare `ui/select/SearchSelect.svelte` (Svelte 5)
- Estende logica `SimpleSelect`
- Aggiunge: input ricerca con filtro fuzzy
- Snippet: `item` + `selectedItem` (trigger display)
- Filtro su `label` + `searchText` + `value`

#### Step 1.5: Creare `ui/select/index.ts`
```typescript
export { default as BaseDropdown } from './BaseDropdown.svelte';
export { default as SimpleSelect } from './SimpleSelect.svelte';
export { default as SearchSelect } from './SearchSelect.svelte';
export * from './types';
```

---

### FASE 2: Migrazione Select Consumer (2h)

#### Step 2.1: Aggiornare `LanguageSelector.svelte`
- Rimuovere variante `inline` (usare solo dropdown custom)
- Usare `SimpleSelect` internamente
- Snippet per item con bandiera + nome lingua
- Mantenere stile header esistente

#### Step 2.2: Aggiornare `settings/SettingSelect.svelte`
- Usare `SimpleSelect` invece di `CustomSelect`
- Props esistenti rimangono compatibili

#### Step 2.3: Aggiornare `settings/SettingCurrency.svelte`
- Usare `SearchSelect` invece di `FuzzySelect`
- Snippet per item con simbolo + codice + nome

#### Step 2.4: Creare `brokers/ImportPluginSelect.svelte` (refactor)
- Usare `SearchSelect`
- Snippet per item con nome plugin + descrizione
- Mantiene caricamento API esistente

#### Step 2.5: Aggiornare `brokers/BrokerSelect.svelte`
- Già Svelte 5, refactorare per usare `SearchSelect`
- Snippet per item con `BrokerIcon` + nome
- Riduzione da ~490 righe a ~100 righe

---

### FASE 3: Setting Fields Components (2h)

#### Step 3.1: Creare `settings/fields/SettingToggle.svelte`
- Estrae pattern boolean da `GlobalSettingsTab`
- Props: `value`, `label`, `hint`, `icon`, `isModified`, `isLocked`
- Events: `save`, `undo`, `reset`
- UI: toggle switch con ON/OFF label

#### Step 3.2: Creare `settings/fields/SettingNumber.svelte`
- Estrae pattern int/float da `GlobalSettingsTab`
- Props: `value`, `type: 'int' | 'float'`, `min`, `max`, `step`, `unit`
- Supporta unit selector (MB/GB per file size)
- Warning per valori estremi

#### Step 3.3: Refactorare `GlobalSettingsTab.svelte`
- Da 855 righe a ~300 righe
- Usa composizione di `SettingToggle`, `SettingNumber`, `SettingSelect`, `SettingSearchSelect`
- Mantiene logica di categoria e lock/unlock

---

### FASE 4: Riorganizzazione File (1h)

#### Step 4.1: Spostare file in cartelle corrette
```bash
# Da root components/ a ui/
mv FuzzySelect.svelte → DEPRECATO (sostituito da SearchSelect)
mv AnimatedBackground.svelte → ui/AnimatedBackground.svelte
mv Tooltip.svelte → ui/Tooltip.svelte
mv HelpMenu.svelte → layout/HelpMenu.svelte
mv ThemeToggle.svelte → ui/ThemeToggle.svelte (o layout/)

# Deprecare CustomSelect (sostituito da SimpleSelect)
rm CustomSelect.svelte

# Organizzare settings tabs
mv settings/*.Tab.svelte → settings/tabs/
```

#### Step 4.2: Aggiornare tutti gli import
- Usare regex per find/replace in tutto il frontend
- Pattern: `from '$lib/components/FuzzySelect'` → `from '$lib/components/ui/select'`

#### Step 4.3: Creare file index.ts per export puliti
```typescript
// lib/components/ui/index.ts
export * from './select';
export { default as AnimatedBackground } from './AnimatedBackground.svelte';
export { default as ThemeToggle } from './ThemeToggle.svelte';
export { default as Tooltip } from './Tooltip.svelte';
```

---

### FASE 5: Test e Validazione (2h)

#### Step 5.1: Eseguire test esistenti
```bash
./dev.py test front all
```
- Tutti i 51+ test devono passare
- Fix eventuali regressioni

#### Step 5.2: Aggiungere test specifici per Select
```typescript
// e2e/components.spec.ts (NEW)
test.describe('Select Components', () => {
    test('SimpleSelect - keyboard navigation', ...);
    test('SimpleSelect - click outside closes', ...);
    test('SearchSelect - filters options', ...);
    test('SearchSelect - keyboard selection', ...);
});
```

#### Step 5.3: Test Settings con nuovi componenti
- Verificare `GlobalSettingsTab` con componenti refactorati
- Verificare `PreferencesTab` con nuovi Select
- Verificare persistenza valori

#### Step 5.4: Verificare build e check
```bash
./dev.py front build
./dev.py front check
```
- Zero warning TypeScript
- Zero warning Svelte

---

## 📁 File da Creare

| File | Descrizione | Righe stimate |
|------|-------------|---------------|
| `ui/select/types.ts` | Interfacce comuni | ~30 |
| `ui/select/BaseDropdown.svelte` | Logica dropdown pura | ~80 |
| `ui/select/SimpleSelect.svelte` | Select senza ricerca | ~120 |
| `ui/select/SearchSelect.svelte` | Select con ricerca | ~150 |
| `ui/select/index.ts` | Re-export | ~10 |
| `settings/fields/SettingToggle.svelte` | Toggle boolean | ~80 |
| `settings/fields/SettingNumber.svelte` | Input numerico | ~120 |
| `settings/fields/index.ts` | Re-export | ~15 |
| `e2e/components.spec.ts` | Test componenti | ~100 |

**Totale nuove righe**: ~700

## 📁 File da Modificare

| File | Modifiche | Riduzione righe |
|------|-----------|-----------------|
| `LanguageSelector.svelte` | Usa SimpleSelect | 84 → 60 |
| `BrokerSelect.svelte` | Usa SearchSelect | 490 → 100 |
| `ImportPluginSelect.svelte` | Usa SearchSelect | 69 → 80 |
| `SettingSelect.svelte` | Usa SimpleSelect | 101 → 60 |
| `SettingCurrency.svelte` | Usa SearchSelect | 99 → 60 |
| `GlobalSettingsTab.svelte` | Usa Setting* components | 855 → 300 |

**Riduzione totale**: ~1000 righe eliminate

## 📁 File da Eliminare/Deprecare

| File | Motivo |
|------|--------|
| `FuzzySelect.svelte` | Sostituito da SearchSelect |
| `ui/CustomSelect.svelte` | Sostituito da SimpleSelect |

---

## ⏱️ Stima Tempo

| Fase | Descrizione | Tempo |
|------|-------------|-------|
| Fase 1 | Infrastruttura Base Select | 2h |
| Fase 2 | Migrazione Select Consumer | 2h |
| Fase 3 | Setting Fields Components | 2h |
| Fase 4 | Riorganizzazione File | 1h |
| Fase 5 | Test e Validazione | 2h |
| Buffer | Imprevisti | 1h |
| **Totale** | | **~10h** |

---

## ✅ Criteri di Accettazione

1. ✅ Zero duplicazione logica dropdown
2. ✅ Tutti componenti Select usano Svelte 5 runes
3. ✅ Slot-based rendering per tutti i Select
4. ✅ 51+ test E2E passano
5. ✅ `GlobalSettingsTab` < 350 righe
6. ✅ Build senza warning
7. ✅ Nuovi test per Select keyboard navigation

---

## 🔗 Dipendenze

- Nessuna dipendenza bloccante
- Richiede `./dev.py test front all` funzionante prima di iniziare

---

## 📝 Note Tecniche

### Svelte 5 Snippet Pattern
```svelte
<!-- SearchSelect.svelte -->
<script lang="ts">
    import type { Snippet } from 'svelte';
    import type { SelectOption } from './types';
    
    interface Props {
        options: SelectOption[];
        value: string;
        item?: Snippet<[SelectOption]>; // slot per item
        selectedItem?: Snippet<[SelectOption]>; // slot per trigger
        onchange?: (value: string) => void;
    }
    let { options, value, item, selectedItem, onchange }: Props = $props();
</script>

{#each filteredOptions as option}
    {#if item}
        {@render item(option)}
    {:else}
        <span>{option.label}</span>
    {/if}
{/each}
```

### Esempio Uso con Snippet
```svelte
<!-- Uso in BrokerSelect -->
<SearchSelect {options} bind:value>
    {#snippet item(option)}
        <div class="flex gap-2">
            <BrokerIcon 
                iconUrl={option.data?.icon_url}
                portalUrl={option.data?.portal_url}
                altText={option.label}
                size="sm"
            />
            <span>{option.label}</span>
        </div>
    {/snippet}
    {#snippet selectedItem(option)}
        <div class="flex items-center gap-2">
            <BrokerIcon ... size="sm" />
            <span class="truncate">{option.label}</span>
        </div>
    {/snippet}
</SearchSelect>

<!-- Uso in CurrencySelect -->
<SearchSelect {options} bind:value>
    {#snippet item(option)}
        <div class="flex items-center gap-2">
            <span class="w-8 h-8 bg-libre-green/20 rounded flex items-center justify-center font-medium">
                {option.data?.symbol || option.value}
            </span>
            <div class="min-w-0 flex-1">
                <div class="font-mono text-sm">{option.value}</div>
                <div class="text-xs text-gray-500 truncate">{option.label}</div>
            </div>
        </div>
    {/snippet}
</SearchSelect>
```

### Compatibilità ECharts
- ECharts è vanilla JS, funziona con Svelte 5 senza problemi
- Pattern: `echarts.init(container)` in `$effect`
```svelte
<script lang="ts">
    import * as echarts from 'echarts';
    
    let container: HTMLDivElement;
    let chart: echarts.ECharts;
    
    $effect(() => {
        if (container) {
            chart = echarts.init(container);
            return () => chart?.dispose();
        }
    });
</script>
```

---

## 🔗 File Correlati

- `plan-component-reorganization.md` - Piano originale (da archiviare)
- `plan-phase04-summary.md` - Contesto Phase 4 completata
- `e2e-test-analysis.md` - Gap analysis test esistenti
