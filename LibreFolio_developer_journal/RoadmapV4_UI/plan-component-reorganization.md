# Plan: Frontend Component Reorganization

**Data creazione**: 3 Febbraio 2026  
**Status**: 📋 PIANIFICATO (da fare dopo gallery)  
**Priorità**: P2  
**Dipendenze**: Completamento gallery e test E2E

---

## 🎯 Obiettivo

Riorganizzare i componenti frontend per:

1. Ridurre duplicazione di codice
2. Strutturare le cartelle in modo logico
3. Creare componenti base riutilizzabili con specializzazioni concrete

---

## 📊 Analisi Stato Attuale

### Componenti Select Esistenti

| Componente                  | Posizione                  | Funzionalità                      | Note                        |
|-----------------------------|----------------------------|-----------------------------------|-----------------------------|
| `FuzzySelect.svelte`        | `/lib/components/`         | Select con ricerca fuzzy          | Usato per valute            |
| `CustomSelect.svelte`       | `/lib/components/ui/`      | Select semplice senza ricerca     | Usato per lingue            |
| `BrokerSelect.svelte`       | `/lib/components/brokers/` | Select broker con ricerca + icone | Duplica logica FuzzySelect  |
| `ImportPluginSelect.svelte` | `/lib/components/brokers/` | Select plugin BRIM con ricerca    | Duplica logica FuzzySelect  |
| `LanguageSelector.svelte`   | `/lib/components/`         | Header language selector          | Potrebbe usare CustomSelect |

### Struttura Cartelle Attuale

```
frontend/src/lib/components/
├── auth/                    # Login, Register, Password modals
├── brokers/                 # Broker-specific components
├── files/                   # File management
├── layout/                  # Header, Sidebar, Footer
├── settings/                # Settings tabs and controls
├── table/                   # DataTable components
├── ui/                      # UI primitives (CustomSelect, etc.)
├── AnimatedBackground.svelte
├── FuzzySelect.svelte       # ❌ Dovrebbe essere in ui/
├── HelpMenu.svelte          # ❌ Dovrebbe essere in layout/
├── LanguageSelector.svelte  # ❌ Dovrebbe essere in ui/ o layout/
├── ThemeToggle.svelte       # ❌ Dovrebbe essere in ui/ o layout/
└── Tooltip.svelte           # ❌ Dovrebbe essere in ui/
```

---

## 🏗️ Architettura Proposta

### 1. Gerarchia Select Components

```
ui/select/
├── BaseSelect.svelte        # Logica comune: click outside, keyboard nav, dropdown
├── SimpleSelect.svelte      # Senza ricerca (ex CustomSelect)
├── SearchableSelect.svelte  # Con ricerca fuzzy (ex FuzzySelect)
└── index.ts                 # Re-export tipi e componenti
```

### 2. Componenti Specializzati (usano SearchableSelect)

```
brokers/
├── BrokerSelect.svelte      # Usa SearchableSelect + broker options
└── ImportPluginSelect.svelte # Usa SearchableSelect + plugin options

settings/
└── LanguageSelect.svelte    # Usa SimpleSelect + language options

layout/
└── LanguageSelector.svelte  # Header dropdown (usa SimpleSelect internamente)
```

### 3. Struttura Cartelle Target

```
frontend/src/lib/components/
├── auth/                    # Auth modals
│   ├── LoginModal.svelte
│   ├── RegisterModal.svelte
│   ├── ForgotPasswordModal.svelte
│   └── PasswordChangeModal.svelte
│
├── brokers/                 # Broker management
│   ├── BrokerCard.svelte
│   ├── BrokerModal.svelte
│   ├── BrokerForm.svelte
│   ├── BrokerSelect.svelte
│   ├── BrokerIcon.svelte
│   ├── BrokerImportFilesModal.svelte
│   └── ImportPluginSelect.svelte
│
├── files/                   # File management
│   ├── FilesTable.svelte
│   └── FileUploader.svelte
│
├── layout/                  # App structure
│   ├── Header.svelte
│   ├── Sidebar.svelte
│   ├── Footer.svelte
│   ├── HelpMenu.svelte      # 🔄 Move here
│   ├── LanguageSelector.svelte  # 🔄 Move here
│   └── ThemeToggle.svelte   # 🔄 Move here
│
├── settings/                # Settings components
│   ├── tabs/
│   │   ├── ProfileTab.svelte
│   │   ├── PreferencesTab.svelte
│   │   ├── AboutTab.svelte
│   │   └── GlobalSettingsTab.svelte
│   ├── SettingsLayout.svelte
│   ├── SettingSelect.svelte
│   ├── SettingCurrency.svelte
│   ├── SettingTheme.svelte
│   └── PasswordChangeModal.svelte
│
├── table/                   # DataTable system
│   ├── DataTable.svelte
│   ├── DataTableToolbar.svelte
│   ├── DataTablePagination.svelte
│   ├── DataTableColumnFilter.svelte
│   └── index.ts
│
├── ui/                      # UI primitives
│   ├── select/
│   │   ├── BaseSelect.svelte
│   │   ├── SimpleSelect.svelte
│   │   ├── SearchableSelect.svelte
│   │   └── index.ts
│   ├── AnimatedBackground.svelte  # 🔄 Move here
│   ├── Tooltip.svelte       # 🔄 Move here
│   ├── PasswordInput.svelte
│   └── index.ts
│
└── index.ts                 # Root exports
```

---

## 📋 Piano di Implementazione

### Fase 1: Creare BaseSelect (1h)

Estrarre logica comune da FuzzySelect e CustomSelect:

- Click outside handling
- Keyboard navigation (Escape, Arrow keys, Enter)
- Dropdown positioning
- Open/close state management
- Disabled/loading states

```svelte
<!-- BaseSelect.svelte - Slot-based approach -->
<script>
  export let isOpen = false;
  export let disabled = false;
  // ... common logic
</script>

<div class="relative" use:clickOutside={() => isOpen = false}>
  <slot name="trigger" {isOpen} {toggleOpen} />
  {#if isOpen}
    <div class="dropdown">
      <slot name="content" {close} />
    </div>
  {/if}
</div>
```

### Fase 2: Refactor SimpleSelect e SearchableSelect (1.5h)

- `SimpleSelect`: Usa BaseSelect, niente ricerca
- `SearchableSelect`: Usa BaseSelect + input ricerca + filtro fuzzy

### Fase 3: Aggiornare Componenti Specializzati (1h)

- `BrokerSelect` → usa `SearchableSelect`
- `ImportPluginSelect` → usa `SearchableSelect`
- `SettingSelect` → usa `SimpleSelect`
- `LanguageSelector` → usa `SimpleSelect`

### Fase 4: Riorganizzare Cartelle (30min)

Spostare file nelle cartelle corrette e aggiornare import.

### Fase 5: Aggiornare Import e Test (1h)

- Aggiornare tutti gli import nei file che usano i componenti spostati
- Verificare che tutti i test E2E passino
- Aggiornare documentazione

---

## ✅ Criteri di Successo

1. Zero duplicazione di logica dropdown
2. Struttura cartelle logica e prevedibile
3. Tutti i test E2E passano
4. Build senza warning
5. Componenti facilmente trovabili e riutilizzabili

---

## ⏱️ Stima Tempo Totale

| Fase                      | Tempo   |
|---------------------------|---------|
| Fase 1: BaseSelect        | 1h      |
| Fase 2: Simple/Searchable | 1.5h    |
| Fase 3: Specializzazioni  | 1h      |
| Fase 4: Riorganizzazione  | 30min   |
| Fase 5: Import e Test     | 1h      |
| **Totale**                | **~5h** |

---

## 📝 Note

- Questo refactoring NON è bloccante per altre feature
- Può essere fatto incrementalmente
- Priorità più bassa rispetto a completare Phase 4
- Da fare dopo stabilizzazione gallery e test E2E

---

## 🔗 File Correlati

- `plan-settings-mobile-gallery.md` - Dipendenza da completare prima
- `e2e-test-analysis.md` - Test da verificare dopo refactoring
