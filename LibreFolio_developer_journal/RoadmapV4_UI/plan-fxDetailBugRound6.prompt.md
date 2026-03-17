# Plan: Fix Bug Round 6 — FX Detail Page & DataTable

**Dipendenze**: [`plan-fxDetailBugRound5.prompt.md`](plan-fxDetailBugRound5.prompt.md) (Round 5 completato)

Round di fix: colori sfondo celle (root cause trovato: CSS duplicati e invertiti), filtri mancanti, SignalStyleEditor nell'header misura, rimozione min-height, creazione CalendarMonth + SingleDatePicker, gestione date new row, auto-fit colonne misure.

---

## Steps

### 1. ✅ Fix colori sfondo riga DataTable — root cause CSS duplicati e invertiti

**File**: `frontend/src/lib/components/table/DataTable.svelte`, `frontend/src/lib/components/ui/data-editor/DataEditor.svelte`

In `DataTable.svelte` righe 1599-1619 ci sono regole `tr.row-X td` con colori **invertiti**: `row-edited` = amber (#fffbeb), `row-appended` = blue (#eff6ff) — il contrario del voluto. In `DataEditor.svelte` righe 446-471 ci sono regole `:global(.row-*)` concorrenti su `<tr>`.

- **Rimuovere** i CSS `:global(.row-*)` e `:global(.dark .row-*)` da `DataEditor.svelte` (righe 445-471)
- **Correggere** i CSS in `DataTable.svelte` per `tr.row-edited td`, `tr.row-appended td`, `tr.row-deleted td` con i colori giusti:
  - `row-edited td` → `rgba(59, 130, 246, 0.10)` (blue) light / `rgba(59, 130, 246, 0.15)` dark
  - `row-appended td` → `rgba(16, 185, 129, 0.10)` (green) light / `rgba(16, 185, 129, 0.15)` dark
  - `row-deleted td` → `rgba(239, 68, 68, 0.10)` (red) light / `rgba(239, 68, 68, 0.15)` dark
- **Aggiungere** `tr.row-stale td` con gradiente giallo dinamico:
  - Nuova prop `getRowStyle?: (row: T) => string` nel DataTable, applicata sul `<tr style=...>`
  - `DataEditor.svelte` setta `--stale-opacity: X` via `getRowStyle` dove `staleOpacity(days) = Math.min(0.4, days * 0.04)`
  - CSS: `tr.row-stale td { background: rgba(245, 158, 11, var(--stale-opacity, 0.06)) !important; }`
- Per `.td-fixed` (sticky): le regole `tr.row-X td` coprono anche i td sticky. Verificare in browser — se non funziona, aggiungere regole esplicite per `.td-fixed` dentro i `tr.row-X`

### 2. ✅ Abilitare filtri colonne in DataEditor e MeasurePanel

**File**: `frontend/src/lib/components/ui/data-editor/DataEditor.svelte`, `frontend/src/lib/components/charts/MeasurePanel.svelte`

- In `DataEditor.svelte`: `filterable: false` → `filterable: true` sulle colonne date (riga 132) e data columns (righe 153, 167)
- In `MeasurePanel.svelte` riga 396: `enableColumnFilters={false}` → `enableColumnFilters={true}`

### 3. ✅ Spostare SignalStyleEditor nell'header della card misura

**File**: `frontend/src/lib/components/charts/MeasurePanel.svelte`

Rimuovere il blocco dedicato (righe 374-380) dall'area espansa. Nell'header (righe 317-368), ristrutturare il layout con due gruppi flex:

- **Sinistra**: chevron + DateRangePicker + Δ% + days
- **Destra**: SignalStyleEditor + trash (usando `ml-auto`)

SignalStyleEditor visibile solo `{#if isExpanded}`. Tutti gli elementi allineati a sinistra nel loro gruppo.

### 4. ✅ Rimuovere `min-height` dalla `.table-wrapper` di DataTable

**File**: `frontend/src/lib/components/table/DataTable.svelte`

Riga 991: eliminare `min-height: 280px;`. Il filter popover con `position: fixed` + z-index 9999 (round 5) rende il vincolo superfluo.

### 5. ✅ Auto-fit colonne nella tabella misure

**File**: `frontend/src/lib/components/table/DataTable.svelte`, `frontend/src/lib/components/charts/MeasurePanel.svelte`

- Aggiungere prop `tableLayout?: 'fixed' | 'auto'` a `DataTable.svelte`. Default `'fixed'` (comportamento attuale). Quando `'auto'`: `table-layout: auto` nel CSS e le colonne usano `min-width` invece di `width`
- In `MeasurePanel.svelte`: settare `tableLayout="auto"` e aggiungere `width` contenuti alle `summaryColumns` (Signal: 100, numeri: 80-90) come hint per `min-width`
- Le colonne si espandono per riempire lo spazio disponibile

### 6. ✅ Creare `CalendarMonth.svelte` e `SingleDatePicker.svelte`

**Nuovi file**: `frontend/src/lib/components/ui/CalendarMonth.svelte`, `frontend/src/lib/components/ui/SingleDatePicker.svelte`
**Refactor**: `frontend/src/lib/components/ui/DateRangePicker.svelte`

#### 6a — CalendarMonth.svelte

Sotto-componente puro per rendering griglia mese. Estratto dallo `{#snippet monthGridSnippet}` di DateRangePicker (riga 604-647) + header navigazione (prev/mese/anno/next/today).

Props:
```typescript
interface Props {
    year: number;
    month: number;
    weekdayLabels: string[];
    monthLabels: string[];
    onDayClick: (iso: string) => void;
    onDayHover?: (iso: string) => void;
    onPrevMonth: () => void;
    onNextMonth: () => void;
    onSetMonth: (m: number) => void;
    onSetYear: (y: number) => void;
    onGoToToday?: () => void;
    /** Structured highlights — CalendarMonth gestisce le classi internamente */
    highlights?: {
        selected?: string;           // data selezionata (SingleDatePicker)
        rangeStart?: string;         // inizio range (DateRangePicker)
        rangeEnd?: string;           // fine range (DateRangePicker)
        pending?: string;            // data in attesa di 2° click
        hovered?: string;            // data sotto il cursore (per range preview)
    };
    disabledDates?: Set<string>;
}
```

**Non** contiene logica di swap né di selection — il parent decide tutto via callbacks e `highlights`.

Funzioni helper portate dal DateRangePicker: `formatISO`, `getMonthGrid`, `todayISO`, `isFuture`, `yearOptions`.

#### 6b — SingleDatePicker.svelte

Trigger button (Calendar icon + label + data) + popover con UN `CalendarMonth`. Single click = seleziona + chiudi.

Props:
```typescript
interface Props {
    value: string;              // ISO YYYY-MM-DD
    label?: string;             // "Date", "From", "To" — default "Date"
    compact?: boolean;
    onchange: (date: string) => void;
    disabledDates?: Set<string>;
}
```

`highlights` passato a CalendarMonth: `{ selected: value }`. No range, no pending, no hovered.

#### 6c — Refactor DateRangePicker.svelte

Sostituire lo `{#snippet monthGridSnippet}` e le due sezioni di navigazione mese/anno (righe 517-591) con 2 istanze `<CalendarMonth>`.

La logica di auto-swap resta in DateRangePicker (`leftNextMonth`, `setLeftMonth` ecc.) — viene passata come callbacks `onPrevMonth`/`onNextMonth`/`onSetMonth`/`onSetYear` ai 2 CalendarMonth.

`highlights` passato ad entrambi i calendari contiene `rangeStart`, `rangeEnd`, `pending`, `hovered` derivati dalla logica esistente (`isInRange`, `isRangeStart`, `isRangeEnd`).

Il comportamento di auto-swap (se il mese sinistro va oltre il destro, si invertono) resta intatto perché vive nelle funzioni `setLeftMonth`/`leftNextMonth` ecc. che sono passate come callback.

### 7. ✅ Gestione date new row in DataEditor

**File**: `frontend/src/lib/components/ui/data-editor/DataEditor.svelte`, `frontend/src/lib/components/fx/FxDataEditorSection.svelte`

- La colonna "date" per righe `status === 'appended'` renderizza un `SingleDatePicker` (step 6) al posto del testo statico
- `disabledDates` = set di tutte le date presenti nelle `rows` (escludendo la riga corrente)
- Posizionamento: `sortedRows` derivato mette le new rows prima/dopo le originali secondo la data
- **On save** in `FxDataEditorSection.svelte`: `handleSave()` calcola il range min/max delle righe appended. Se fuori dal range attuale, passa `{expandedRange: {start, end}}` al callback `onsave`. Il parent in `+page.svelte` espande il DateRangePicker e fa refresh

---

## Ordine di esecuzione

| Fase | Steps | Note |
|------|-------|------|
| CSS fix + props | 1 (colori), 4 (min-height) | Root cause, impatto visivo immediato |
| Filtri | 2 | Quick fix, sblocca test di z-index |
| Layout misure | 3 (header), 5 (auto-fit) | Migliora UX pannello misure |
| Componenti calendario | 6a (CalendarMonth), 6b (SingleDatePicker), 6c (refactor DateRangePicker) | Prerequisito per step 7 |
| Date editor | 7 | Ultimo, dipende da step 6 |

---

## Decisioni confermate

| Domanda | Decisione |
|---------|-----------|
| Root cause colori sfondo? | CSS duplicati: DataTable ha `tr.row-X td` con colori invertiti (edited=amber, appended=blue). DataEditor ha `:global(.row-X)` su `<tr>` con colori giusti ma overridden. Fix: unico set in DataTable con colori corretti |
| Filtri mancanti dove? | DataEditor: `filterable: false` su tutte le colonne. MeasurePanel: `enableColumnFilters={false}` sulla DataTable |
| SignalStyleEditor posizione? | Nell'header della card misura, allineato a destra (stesso row di DateRangePicker), visibile solo quando espanso |
| min-height tabella? | Rimossa — z-index fixed del filter popover (round 5) rende superflua l'altezza minima |
| Auto-fit colonne misure? | Nuova prop `tableLayout: 'auto'` in DataTable. Colonne usano `min-width` e si espandono per riempire lo spazio |
| Come mantenere auto-swap con semplicità? | Estrarre `CalendarMonth` come sotto-componente puro (griglia + navigazione). DateRangePicker tiene logica di swap nelle sue callbacks (`leftNextMonth`, `setLeftMonth` ecc.) passate ai 2 CalendarMonth. SingleDatePicker usa 1 CalendarMonth senza swap |
| SingleDatePicker — selezione? | Singola: un click = seleziona + chiudi. NO selezione di 2 date |
| Highlights approach? | Props strutturate (`highlights: {selected?, rangeStart?, rangeEnd?, pending?, hovered?}`) — CalendarMonth gestisce le classi CSS internamente. Più leggibile di `getDayClass` callback |
| Stale opacity dinamica? | CSS custom property `--stale-opacity` settata via `getRowStyle` prop. CSS: `rgba(245, 158, 11, var(--stale-opacity))` |
| Date duplicate in new row? | `disabledDates` prop su SingleDatePicker = set di tutte le date esistenti. Date disabilitate non cliccabili |
| Auto-expand range on save? | `onsave` callback riceve `{expandedRange: {start, end}}` se ci sono righe appended fuori dal range attuale |

---

## Feature rimandati (prossima iterazione)

### Import CSV — gestione date fuori selezione

Come deciso: rimandato. Il meccanismo di `expandedRange` (step 7) pone le basi, ma l'import CSV potrebbe portare molte date fuori range → serve feedback UX ("X righe fuori dal range attuale, espandere?").

### Merge strategia per date duplicate via import

Se si importa una data già esistente: attualmente sovrascrittura con status 'edited'. Decidere se chiedere conferma o mostrare diff.

---

## File modificati

| File | Modifiche |
|------|-----------|
| `frontend/src/lib/components/table/DataTable.svelte` | Fix CSS colori riga, nuova prop `getRowStyle`, rimozione `min-height`, nuova prop `tableLayout`, stile `table-layout: auto` |
| `frontend/src/lib/components/table/types.ts` | (se serve) aggiunta `tableLayout` al tipo props |
| `frontend/src/lib/components/ui/data-editor/DataEditor.svelte` | Rimozione CSS `:global(.row-*)`, `filterable: true` su colonne, `getRowStyle` per stale opacity, SingleDatePicker per new rows |
| `frontend/src/lib/components/charts/MeasurePanel.svelte` | `enableColumnFilters={true}`, header restructure con SignalStyleEditor, `tableLayout="auto"`, `width` su colonne |
| `frontend/src/lib/components/ui/CalendarMonth.svelte` | **Nuovo** — griglia mese + navigazione, riusabile |
| `frontend/src/lib/components/ui/SingleDatePicker.svelte` | **Nuovo** — single date picker con 1 CalendarMonth |
| `frontend/src/lib/components/ui/DateRangePicker.svelte` | Refactor: usa 2 CalendarMonth, rimuove snippet duplicato |
| `frontend/src/lib/components/fx/FxDataEditorSection.svelte` | `onsave` con `expandedRange` per auto-expand date range |
| `frontend/src/routes/(app)/fx/[pair]/+page.svelte` | Handler `onsave` con expanded range → aggiorna DateRangePicker |
