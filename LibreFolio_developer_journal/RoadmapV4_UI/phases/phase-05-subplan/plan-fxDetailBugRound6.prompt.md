# Plan: Fix Bug Round 6 — FX Detail Page & DataTable

**Dipendenze**: [`plan-fxDetailBugRound5.prompt.md`](plan-fxDetailBugRound5.prompt.md) (Round 5 completato)
**Successivo**: [`plan-fxDetailBugRound6-2.prompt.md`](plan-fxDetailBugRound6-2.prompt.md)

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

## Round 6.1 — Fix feedback da test utente (17 Mar 2026)

### Risultato test utente sugli Step 1-7

| Step | Esito | Note |
|------|-------|------|
| 1 | ✅ OK | Colori riga corretti |
| 2 | ✅ Parziale | Filtri visibili, ma date column usa search testuale anziché DateRangePicker. Rate manca slider logaritmico. Regressione: Status column non più hidden by default |
| 3 | ✅ Parziale | SignalStyleEditor in header, ma border-t spuria. Color picker non allineato al primo render. Eye icon occupa solo spazio |
| 4 | ✅ OK | min-height rimossa |
| 5 | ⚠️ | Colonne visibili ma più larghe del necessario, scrollbar orizzontale |
| 6 | ⚠️ | DateRangePicker funziona. SingleDatePicker tagliato dalla riga, no auto-focus su Add Row, formato data americano |
| 7 | ⚠️ | Come step 6 |
| BUG | 🐛 | Upload da files/broker reports non funziona (nessun POST), funziona da broker detail |

### Fix applicati

#### 2a. ✅ Colonna Date type → 'date' per DateRangePicker filter
**File**: `DataEditor.svelte`
- Cambiato tipo colonna date da `'text'` a `'date'` per attivare il filtro data range nel DataTableColumnFilter

#### 2b. ✅ Fix regressione Status column `hiddenByDefault`
**File**: `DataTable.svelte`
- `onMount`: merge della visibility salvata in localStorage con i default, rispettando `hiddenByDefault` per colonne nuove non presenti nello stato salvato

#### 3a. ✅ Fix border-t spuria SignalStyleEditor
**File**: `SignalStyleEditor.svelte`, `ChartSignalsSection.svelte`
- Rimosso `border-t` e `pt-1.5` da SignalStyleEditor (componente generico)
- Aggiunto wrapper `<div class="pt-1.5 border-t ...">` nel parent ChartSignalsSection (unico luogo dove serve)

#### 5a. ✅ Fix larghezza colonne in `tableLayout="auto"`
**File**: `DataTable.svelte`
- Per `tableLayout="auto"`: usa `column.width` diretto (non `columnWidths` da localStorage che potrebbe avere valori stale/larghi)

#### 6a. ✅ Fix SingleDatePicker z-index e clipping
**File**: `SingleDatePicker.svelte`
- Cambiato a `position: fixed` con `getBoundingClientRect()` per posizionamento + `z-index: 9999`
- Formato data cambiato da MM/DD/YYYY a ISO YYYY-MM-DD

#### 6b. ✅ Auto-scroll su Add Row
**File**: `DataEditor.svelte`
- Dopo `handleAddRow`: `tick().then()` + `scrollIntoView({ behavior: 'smooth', block: 'center' })` sulla nuova riga

#### CSS. ✅ Fix 7 warning CSS unused selectors
**File**: `DataTableColumnFilter.svelte`
- Rimossi selettori `.date-row`, `.date-label`, `.date-input` inutilizzati dai selettori combinati `.range-row, .date-row` → `.range-row`

#### Upload Bug — files/+page.svelte
**File**: `files/+page.svelte`
- Aggiunto `$: canConfirmBrim` reactive var per tracking reattivo dello stato del pulsante Upload
- **Nota**: il bug è pre-esistente, non introdotto dai round 6. Causa root ancora da investigare (nessun POST emesso dopo click Upload). Il componente usa sintassi Svelte 4 (`on:click`, `$:`) e componenti child Svelte 5 (BrokerSearchSelect con `onchange` prop). Non è possibile mescolare `onclick` e `on:click` nello stesso file Svelte.

### Fix NON ancora applicati (prossima iterazione)

| Issue | Descrizione | Priorità |
|-------|-------------|----------|
| Date filter DateRangePicker | Filtro date dovrebbe usare DateRangePicker (non text/date input nativo) | Media |
| Rate filter slider | Rate dovrebbe avere slider logaritmico come il filtro Size | Media |
| Eye icon posizione | Spostare eye (visibilità colonne) accanto a trash nel MeasurePanel header | Bassa |
| SignalStyleEditor color sync | Color picker non allineato al primo render, si allinea dopo primo cambio | Media |
| Auto-focus chart click | Click su punto grafico → scroll alla riga corrispondente in DataEditor | Media |
| Upload bug root cause | Investigare perché `confirmBrimUpload` non emette POST da files/+page | Alta |

---

## File modificati (aggiornamento Round 6.1)

| File | Modifiche Round 6.1 |
|------|---------------------|
| `frontend/src/lib/components/table/DataTable.svelte` | Fix hiddenByDefault merge onMount, fix column width per tableLayout auto |
| `frontend/src/lib/components/table/DataTableColumnFilter.svelte` | Rimossi 7 selettori CSS unused (.date-row, .date-label, .date-input) |
| `frontend/src/lib/components/ui/data-editor/DataEditor.svelte` | Date column type 'date', auto-scroll su Add Row |
| `frontend/src/lib/components/ui/SingleDatePicker.svelte` | position: fixed, z-index 9999, formato ISO |
| `frontend/src/lib/components/charts/SignalStyleEditor.svelte` | Rimosso border-t e pt-1.5 |
| `frontend/src/lib/components/charts/ChartSignalsSection.svelte` | Aggiunto wrapper border-t per SignalStyleEditor |
| `frontend/src/routes/(app)/files/+page.svelte` | Aggiunto $: canConfirmBrim reactive |
