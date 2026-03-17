# Plan: Round 6.2 — Fix feedback test utente FX Detail Page

**Dipendenze**: [`plan-fxDetailBugRound6.prompt.md`](plan-fxDetailBugRound6.prompt.md) (Round 6 + 6.1 completati)

Bug-fix round basato sul feedback utente post Round 6/6.1. Corregge 10 aree: CSS righe DataTable, positioning filtri, sostituzione select nativi con `SimpleSelect`, popover DateRangePicker, larghezza SingleDatePicker, errore 422 su save, auto-scroll con pagination, eye icon (componente standalone), colore HSL→hex, auto-fit colonne Files, headerTooltip per formula.

**Stato**: ✅ Completato — check 0 errori, build OK

---

## Steps

### 1. ✅ DataTable — Row colors: rimuovi line-through, dark mode più acceso

**File**: `frontend/src/lib/components/table/DataTable.svelte`

- ✅ **Rimosso** `text-decoration: line-through;` e `opacity: 0.7;` da `tr.row-deleted td`
- ✅ **Aumentata** opacità dark mode da `0.15` → `0.25` per `row-deleted`, `row-edited`, `row-appended`
- Non toccato `row-stale` (opacità dinamica via CSS custom property `--stale-opacity`)

---

### 2. ✅ DataTableColumnFilter — Scroll-aware positioning + numero slider labels

**File**: `frontend/src/lib/components/table/DataTableColumnFilter.svelte`

#### 2a. ✅ Chiusura su window scroll

- ✅ Aggiunto `window.addEventListener('scroll', handleScroll, true)` (capture) in `onMount()`
- ✅ Cleanup nel return di `onMount()`

#### 2b. ✅ Smart top/bottom positioning

- ✅ Aggiunta logica: se `spaceBelow < popH && rect.top > popH` → posiziona **sopra** l'anchor
- ✅ Aggiunto `requestAnimationFrame(updatePosition)` per ri-misurare dopo il primo render

#### 2c. ✅ Labels sullo slider numerico

- ✅ Aggiunto `<div class="size-slider-labels">` con 5 valori
- ✅ Aggiunta funzione `fmtNum()` per formattare i valori

---

### 3. ✅ CalendarMonth — Replace native `<select>` con SimpleSelect

**File**: `frontend/src/lib/components/ui/CalendarMonth.svelte`

- ✅ Importato `SimpleSelect`, aggiunte opzioni derivate `monthSelectOptions` e `yearSelectOptions`
- ✅ Sostituiti i 2 `<select>` nativi con `<SimpleSelect>` con `dropdownPosition="auto"`

---

### 4. ✅ DateRangePicker — Popover clipping, default custom 3Y, granularity select

**File**: `frontend/src/lib/components/ui/DateRangePicker.svelte`

#### 4a. ✅ Popover clipping → `position: fixed` con viewport clamping

- ✅ Aggiunto `triggerEl` e `popoverStyle` state
- ✅ Aggiunta funzione `updatePopoverPosition()` con clamping bordo destro
- ✅ Popover cambiato da `absolute z-50 top-full mt-2 left-1/2 -translate-x-1/2` a `position: fixed` via `popoverStyle`
- ✅ `bind:this={triggerEl}` aggiunto al button trigger
- ✅ `requestAnimationFrame(updatePopoverPosition)` in `openCalendar()`
- ✅ Importato `SimpleSelect` da `$lib/components/ui/select`

#### 4b. ✅ Default Custom: `'months'` → `'years'`

- ✅ Cambiato `customGranularity` da `'months'` → `'years'` e `_prev` tracker aggiornato

#### 4c. ✅ SimpleSelect per granularity

- ✅ Sostituito `<select>` nativo con `<SimpleSelect>` con `class="inline-block w-auto"` e `dropdownPosition="auto"`

---

### 5. ✅ SingleDatePicker — Larghezza eccessiva del popover

- ✅ Aggiunto `w-[280px]` al div `.sdp-popover`

---

### 6. ✅ FxDataEditorSection — Fix errore 422 su save + Cancel button

#### 6a. ✅ Errore 422 — rate undefined → NaN → validazione `validUpserts`

- ✅ Aggiunta validazione `validUpserts` con filtro `!isNaN(rate) && rate > 0`
- ✅ Aggiunto early return con messaggio errore se tutti invalidi e nessun delete
- ✅ `rateItems` usa `validUpserts` al posto di `upsertRows`, `deleteRows` spostato prima della validazione

#### 6b. ✅ Cancel button — `prevChartData` guard referenziale nell'`$effect`

- ✅ Aggiunto `prevChartData` guard referenziale nell'`$effect`
- ✅ L'effect esegue solo quando `chartData` cambia per reference, `handleCancel()` non triggera re-init

---

### 7. ✅ DataTable/DataEditor — Auto-scroll con pagination + eye icon + hiddenByDefault

#### 7a. ✅ Auto-scroll che rispetta la paginazione

- ✅ `DataTable.svelte`: `export function navigateToRowId(rowId)` — trova indice in sortedData, calcola pagina, setta pageIndex
- ✅ `DataEditor.svelte`: `dataTableRef.navigateToRowId(newRow.date)` → `tick()` → `scrollIntoView`

#### 7b. ✅ Eye icon — componente standalone `ColumnVisibilityToggle`

- ✅ **Nuovo componente** `ColumnVisibilityToggle.svelte` — riceve `tableRef` (DataTable instance) come prop, bottone eye + dropdown `position: fixed`, checkbox list per ogni colonna
- ✅ Esportato in `table/index.ts`
- ✅ **DataTable**: `showToolbar` prop (default `true`), `getColumnsForVisibility()`, `toggleColumnVisibilityById()` export methods
- ✅ **DataEditor**: usa `ColumnVisibilityToggle` nella propria toolbar, `showToolbar={false}` su DataTable
- ✅ **FilesTable**: espone `getTableRef()`, `showToolbar={false}`
- ✅ **files/+page.svelte**: `ColumnVisibilityToggle` sulla riga dei tab (solo in vista lista)

#### 7c. ✅ hiddenByDefault con localStorage stale

- ✅ Post-merge loop: forza `merged[col.id] = false` per colonne con `hiddenByDefault: true` non in `storedVisibility`

---

### 8. ✅ MeasurePanel — SignalStyleEditor width + eye toggle + HSL→hex

#### 8a. ✅ SignalStyleEditor `min-w-[60px]` → `min-w-[100px]`
#### 8b. ✅ Eye toggle tabella misure — `hiddenTableIds` + `Eye`/`EyeOff` nel card header
#### 8c. ✅ HSL → hex — `hslToHex()` in `colors.ts`, sostituito in MeasurePanel (riga 91 + 115), cleanup import

---

### 9. ✅ FilesTable — Auto-fit colonne

- ✅ `tableLayout="auto"` sul `<DataTable>`

---

### 10. ✅ DataTable — headerTooltip con info icon

**File**: `types.ts`, `DataTable.svelte`, `MeasurePanel.svelte`

- ✅ Aggiunto `headerTooltip?: string | (() => string)` a `ColumnDef` in `types.ts`
- ✅ Helper `getColumnTooltip()` + `CircleHelp` icon renderizzata tra sort e filter button
- ✅ CSS `.header-tooltip-icon` con `cursor: help` e dark mode
- ✅ MeasurePanel colonna `annualizedPct`: `headerTooltip: '(1 + Δ%)^(365/days) − 1'`

---

## Decisioni confermate

| # | Domanda | Decisione |
|---|---------|-----------|
| 1 | CalendarMonth selects | **SimpleSelect** — leggero, 12+13 opzioni non necessitano search |
| 2 | DateRangePicker popover | **`position: fixed`** con `getBoundingClientRect()` — evita clipping |
| 3 | Number filter labels | **5 labels** (min, 25%, 50%, 75%, max) con `sliderPosToNum()` + formatter |
| 4 | hiddenByDefault fix | **Force-hide** al primo incontro se non era nel localStorage precedente |
| 5 | HSL→hex conversion | Utility in `$lib/utils/colors.ts` (integrata, no file separato) |
| 6 | Eye icon | **Componente standalone `ColumnVisibilityToggle`** — riusabile, connesso via `tableRef` |
| 7 | Filter popover on scroll | **Chiudere su scroll** (window scroll con capture) |
| 8 | Cancel button fix | **Guard referenziale** nell'`$effect` |
| 9 | Header tooltip | **`headerTooltip`** field + icona `CircleHelp` con `title` nativo |

---

## File modificati

| File | Modifiche |
|------|-----------|
| `frontend/src/lib/components/table/DataTable.svelte` | Row colors dark, `navigateToRowId()`, `getColumnsForVisibility()`, `toggleColumnVisibilityById()`, hiddenByDefault fix, `showToolbar` prop, `headerTooltip` + `CircleHelp` icon |
| `frontend/src/lib/components/table/DataTableColumnFilter.svelte` | Scroll close, smart top/bottom, slider labels |
| `frontend/src/lib/components/table/ColumnVisibilityToggle.svelte` | **NUOVO** — Eye icon + dropdown standalone |
| `frontend/src/lib/components/table/index.ts` | Export `ColumnVisibilityToggle` |
| `frontend/src/lib/components/table/types.ts` | `headerTooltip` in `ColumnDef` |
| `frontend/src/lib/components/ui/CalendarMonth.svelte` | SimpleSelect per mese e anno |
| `frontend/src/lib/components/ui/DateRangePicker.svelte` | Fixed popover, default 3Y, SimpleSelect granularity |
| `frontend/src/lib/components/ui/SingleDatePicker.svelte` | `w-[280px]` |
| `frontend/src/lib/components/ui/data-editor/DataEditor.svelte` | `navigateToRowId`, `ColumnVisibilityToggle`, `showToolbar={false}` |
| `frontend/src/lib/components/fx/FxDataEditorSection.svelte` | Rate validation, $effect cancel fix |
| `frontend/src/lib/components/charts/MeasurePanel.svelte` | Eye toggle, HSL→hex, `headerTooltip` Δ%/yr, cleanup |
| `frontend/src/lib/components/charts/SignalStyleEditor.svelte` | min-width 100px |
| `frontend/src/lib/utils/colors.ts` | `hslToHex()` |
| `frontend/src/lib/components/files/FilesTable.svelte` | `tableLayout="auto"`, `getTableRef()`, `showToolbar={false}` |
| `frontend/src/routes/(app)/files/+page.svelte` | `ColumnVisibilityToggle` nella riga tab |

---

## Feature rimandati

| Feature | Motivo |
|---------|--------|
| Upload bug files/+page.svelte | Pre-esistente, richiede debug interattivo con DevTools |
| Date filter con DateRangePicker inline | Funziona, nessun problema segnalato |
| Auto-focus su click punto grafico | Richiede coordinazione chart→DataEditor non ancora implementata |
