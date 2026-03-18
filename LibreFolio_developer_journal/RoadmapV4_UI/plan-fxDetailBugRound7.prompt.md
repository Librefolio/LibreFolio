# Plan: Round 7 — Fix feedback test utente FX Detail Page

**Dipendenze**: [`plan-fxDetailBugRound6-2.prompt.md`](plan-fxDetailBugRound6-2.prompt.md) (Round 6.2 completato)

Bug-fix round basato sul feedback utente post Round 6.2. Copre 11 aree: trasparenza righe DataTable, scroll e styling CalendarMonth/SimpleSelect, popover DateRangePicker max-width e close-on-scroll, granularity badge styling, SingleDatePicker smart direction, DataEditor future date handling, ColumnVisibilityToggle allineamento e OrderableList, MeasurePanel eye→ColumnVisibilityToggle, SignalStyleEditor responsive width, color picker debounce, headerTooltip con componente Tooltip custom.

**Stato**: ✅ Completato (18 Marzo 2026) → Seguito da [`plan-fxDetailBugRound7-1.prompt.md`](plan-fxDetailBugRound7-1.prompt.md)

---

## Steps

### 1. DataTable — Row colors: aumentare semi-trasparenza

**File**: `frontend/src/lib/components/table/DataTable.svelte`

Le opacità attuali sono `0.10` (light) e `0.25` (dark). Ridurle per un effetto più sottile e trasparente:

- **Light mode**: `row-deleted`, `row-edited`, `row-appended` da `rgba(..., 0.10)` → `rgba(..., 0.06)`
- **Dark mode**: da `rgba(..., 0.25)` → `rgba(..., 0.15)`
- `row-stale` default: da `0.06`/`0.08` → `0.04`/`0.06`

In questo modo il contenuto sottostante (font, bordi celle) è più leggibile e la colorazione rimane visibile come indicatore di stato.

---

### 2. CalendarMonth + DateRangePicker — Scroll, sizing e popover

#### 2a. CalendarMonth — SimpleSelect scroll isolation

**File**: `frontend/src/lib/components/ui/select/SimpleSelect.svelte`

Problema: lo scroll nel dropdown di SimpleSelect (mese/anno) propaga al parent, causando la chiusura del DateRangePicker.

- Aggiungere `onwheel|stopPropagation` sul div dropdown (riga ~211) per impedire la propagazione dello scroll event al parent
- Aggiungere anche `ontouchmove={(e) => e.stopPropagation()}` per mobile

#### 2b. CalendarMonth — SimpleSelect compatto senza chevron

**File**: `frontend/src/lib/components/ui/select/SimpleSelect.svelte`, `frontend/src/lib/components/ui/CalendarMonth.svelte`

- Aggiungere nuove prop a `SimpleSelect.svelte`:
  - `compact?: boolean` (default `false`) — padding `px-1.5 py-0.5`, `text-xs`, border più sottile
  - `showChevron?: boolean` (default `true`) — nasconde l'icona `ChevronDown` nel trigger button
- In `CalendarMonth.svelte` (righe 215-228): passare `compact` e `showChevron={false}` ai due `<SimpleSelect>` di mese e anno

#### 2c. DateRangePicker — max-width sul popover

**File**: `frontend/src/lib/components/ui/DateRangePicker.svelte`, `frontend/src/lib/components/ui/CalendarMonth.svelte`

Problema: il popover dual-calendar si espande senza limite. `CalendarMonth.svelte` riga 208 ha `min-w-[240px] flex-1` che causa crescita illimitata.

- In `DateRangePicker.svelte` riga ~482 (div `.drp-popover`): aggiungere `max-w-[600px]`
- In `CalendarMonth.svelte` riga 208: rimuovere `flex-1` — lasciare solo `min-w-[240px]`

#### 2d. DateRangePicker — Chiusura su scroll

**File**: `frontend/src/lib/components/ui/DateRangePicker.svelte`

Il popover `position: fixed` non segue il trigger quando la pagina scorre.

- Aggiungere `window.addEventListener('scroll', closeCalendar, true)` (capture phase) quando `calendarOpen = true`
- Usare un `$effect` che ascolta `calendarOpen` e registra/rimuove il listener

---

### 3. DateRangePicker — Granularity selector badge compatto

**File**: `frontend/src/lib/components/ui/DateRangePicker.svelte`

Il SimpleSelect della granularity (riga ~431-437) dentro la sezione Custom edit usa il default padding `px-3 py-2` ed ha il chevron.

- Passare `compact` e `showChevron={false}` al `<SimpleSelect>` della granularity
- Il risultato: un selettore inline compatto (badge-style) coerente con i preset buttons `px-2.5 py-1`

---

### 4. SingleDatePicker — Smart popover direction + close on scroll

**File**: `frontend/src/lib/components/ui/SingleDatePicker.svelte`

#### 4a. Smart direction

Attualmente `updatePopoverPosition()` (riga 79-85) posiziona sempre sotto (`rect.bottom + 4`).

- Misurare `spaceBelow = window.innerHeight - rect.bottom - 8` e `spaceAbove = rect.top - 8`
- Altezza popover stimata: `~330px` (280px width calendar + padding)
- Se `spaceBelow < 330 && spaceAbove > spaceBelow`: posizionare sopra (`rect.top - 330 - 4`)
- Altrimenti: posizionare sotto (comportamento attuale)

#### 4b. Close on scroll

- Stesso pattern di DateRangePicker (step 2d): listener `scroll` con capture, registrato quando `calendarOpen = true`
- Chiudere il calendario quando la pagina scorre

---

### 5. DataEditor — Add Row: gestione date future

**File**: `frontend/src/lib/components/ui/data-editor/DataEditor.svelte`

In `handleAddRow()` (riga 318-355), se `newDate > todayISO()`:

- Cap della data a `today`: se la data calcolata (lastDate + 1d) è nel futuro, usare `new Date().toISOString().slice(0, 10)` come data
- Se anche today è già occupata, cercare la prima data libera procedendo all'indietro (today-1, today-2, ecc.)
- Aggiungere un commento: `// Cap to today: future dates cause sync errors ("End date cannot be in the future")`

---

### 6. ColumnVisibilityToggle — Allineamento a destra + OrderableList

#### 6a. Allineamento a destra nel toolbar DataEditor

**File**: `frontend/src/lib/components/ui/data-editor/DataEditor.svelte`

Spostare `<ColumnVisibilityToggle>` dalla riga dei bottoni di azione (sinistra) alla riga dei contatori (destra):

```
<!-- Left: actions -->
<div class="flex items-center gap-2">
    Import CSV | Add Row
</div>
<!-- Right: Counters + Eye -->
<div class="flex items-center gap-3 ...">
    {counters...} <ColumnVisibilityToggle />
</div>
```

#### 6b. Upgrade a OrderableList con drag-drop e Reset

**File**: `frontend/src/lib/components/table/ColumnVisibilityToggle.svelte`, `frontend/src/lib/components/table/DataTable.svelte`

1. **Nuove API esportate da DataTable**:
   - `getColumnOrder(): string[]` — ritorna array ordinato di column IDs
   - `setColumnOrder(newOrder: string[])` — riordina le colonne
   - `resetColumnLayout()` — ripristina visibilità e ordine default

2. **ColumnVisibilityToggle**:
   - Importare `OrderableList` da `$lib/components/ui/OrderableList.svelte`
   - Trasformare i dati da `getColumnsForVisibility()` in items per OrderableList
   - Ogni item ha: drag handle (da OrderableList), checkbox toggle (visibilità), label colonna
   - In fondo al dropdown: bottone "Reset layout" che chiama `tableRef.resetColumnLayout()`
   - `onReorder` chiama `tableRef.setColumnOrder(newIds)`
   - Ampliare dropdown width da `200px` a `~260px`

---

### 7. MeasurePanel — Eye toggle → ColumnVisibilityToggle per DataTable

**File**: `frontend/src/lib/components/charts/MeasurePanel.svelte`

Attualmente l'icona Eye/EyeOff nell'header della card misura togla la visibilità dell'intera tabella. Il requisito è cambiarlo in un `ColumnVisibilityToggle` che controlla le colonne della DataTable del measure.

- Rimuovere la logica `hiddenTableIds` e il toggle Eye/EyeOff inline (righe 375-384)
- Aggiungere `bind:this` sulla DataTable nel blocco expanded → `measureTableRefs[measure.id]`
- Sostituire l'eye toggle con `<ColumnVisibilityToggle tableRef={measureTableRefs[measure.id]} />`
- Importare `ColumnVisibilityToggle` da `$lib/components/table`
- `measureTableRefs` dichiarato come `$state<Record<string, DataTable<MeasureSummaryRow>>>({})` o `Map`

---

### 8. SignalStyleEditor — Larghezza responsive SVG line editor

**File**: `frontend/src/lib/components/charts/SignalStyleEditor.svelte`, `frontend/src/lib/components/charts/MeasurePanel.svelte`

#### 8a. SVG line editor più largo e responsive

- SignalStyleEditor riga 66: cambiare `min-w-[100px]` → `min-w-[50px]` e aggiungere `flex-1` per crescita naturale (il container parent controlla il max)
- MeasurePanel header (riga 364 right-group): rimuovere `shrink-0` per consentire il restringimento
- MeasurePanel header (riga 318 div principale): aggiungere `flex-wrap` per wrapping responsive:
  - Schermo largo: DateRangePicker + Δ% + days + [gap] + color + style + trash → una riga
  - Schermo stretto: DateRangePicker + Δ% + days sulla prima riga, color + style + trash sulla seconda

#### 8b. Style popover scroll anchoring — Verifica

Il popover usa `absolute bottom-full left-1/2` → segue lo scroll perché è `absolute` (non `fixed`). **Nessuna modifica necessaria** — solo conferma manuale durante test.

---

### 9. MeasurePanel — Debounce color picker

**File**: `frontend/src/lib/components/charts/SignalStyleEditor.svelte`

Il color picker `oninput` è ad alta frequenza e causa rallentamenti perché ogni evento triggera `measures = [...measures]` + `emitRendered()` (ricalcolo tutti i segnali).

- Aggiungere debounce all'`oninput` del `<input type="color">` (riga 64) in SignalStyleEditor:
  ```typescript
  let colorDebounceTimer: ReturnType<typeof setTimeout> | null = null;
  function handleColorInput(e: Event) {
      const value = (e.currentTarget as HTMLInputElement).value;
      if (colorDebounceTimer) clearTimeout(colorDebounceTimer);
      colorDebounceTimer = setTimeout(() => onstylechange('color', value), 100);
  }
  ```
- Sostituire `oninput={(e) => onstylechange('color', e.currentTarget.value)}` con `oninput={handleColorInput}`
- Aggiungere `onchange={(e) => onstylechange('color', e.currentTarget.value)}` per il commit finale (drag-end)

---

### 10. DataTable — headerTooltip: icona Info + componente Tooltip custom

**File**: `frontend/src/lib/components/table/DataTable.svelte`

Attualmente (righe 782-786) usa `<span title={...}><CircleHelp /></span>` con native browser tooltip.

- Importare `Tooltip` da `$lib/components/ui/Tooltip.svelte` e `Info` da `lucide-svelte`
- Rimuovere `CircleHelp` dall'import se non usato altrove
- Sostituire il blocco righe 782-786 con:
  ```svelte
  <Tooltip text={getColumnTooltip(column)} position="bottom">
      <span class="header-tooltip-icon">
          <Info size={12} />
      </span>
  </Tooltip>
  ```
- Aggiornare CSS `.header-tooltip-icon`: rimuovere `cursor: help` → usare `cursor: pointer`
- **Nota**: il Tooltip component usa Svelte 4 syntax (`export let`) — funziona come child in parent Svelte 5

---

### 11. Slider scale — Documentazione (nessun codice)

**File**: `frontend/src/lib/components/table/DataTableColumnFilter.svelte`

Nessuna modifica di codice necessaria, solo commenti documentativi.

**Conferma**:
- `type === 'number'` → `sliderPosToNum()` è **LINEARE** (riga 114: `numberMin + (pos / 100) * (numberMax - numberMin)`)
- `type === 'size'` → `sliderPosToBytes()` è **LOGARITMICO** (riga 209: `Math.pow(10, logVal)`)
- Valori negativi e zero: gestiti correttamente dal mapping lineare
- Aggiungere commenti `// LINEAR scale` e `// LOGARITHMIC scale` sopra le rispettive funzioni

---

## Decisioni confermate

| # | Domanda | Decisione |
|---|---------|-----------|
| 1 | Row colors transparency | **Ridurre opacità**: light `0.06`, dark `0.15` — più sottile ma visibile |
| 2 | CalendarMonth scroll | **`stopPropagation` su wheel/touch** nel dropdown di SimpleSelect |
| 3 | CalendarMonth SimpleSelect | **Nuove prop `compact` + `showChevron={false}`** su SimpleSelect |
| 4 | DateRangePicker popover width | **`max-w-[600px]`** + rimuovere `flex-1` da CalendarMonth root |
| 5 | DateRangePicker/SingleDatePicker scroll | **Close on scroll** (listener capture, come DataTableColumnFilter) |
| 6 | Future date in Add Row | **Cap a today** — se il giorno calcolato è futuro, usare today (o prima data libera prima di oggi) |
| 7 | ColumnVisibilityToggle position | **Spostare a destra** nel toolbar DataEditor |
| 8 | ColumnVisibilityToggle features | **OrderableList** + checkbox + Reset layout button |
| 9 | MeasurePanel eye icon | **ColumnVisibilityToggle** connessa alla DataTable del measure |
| 10 | SignalStyleEditor width | **`flex-1 min-w-[50px]`** + header `flex-wrap` per wrapping responsive |
| 11 | Color picker performance | **Debounce `oninput`** di 100ms nel `<input type="color">` di SignalStyleEditor |
| 12 | headerTooltip icon | **`Info`** icon + **Tooltip component** custom (non native `title`) |
| 13 | Number slider scale | **Lineare** — documentare con commenti, nessuna modifica funzionale |

---

## File modificati

| File | Modifiche |
|------|-----------|
| `frontend/src/lib/components/table/DataTable.svelte` | Opacità righe ridotta, `CircleHelp` → `Info` + `Tooltip`, nuove API: `getColumnOrder()`, `setColumnOrder()`, `resetColumnLayout()` |
| `frontend/src/lib/components/table/ColumnVisibilityToggle.svelte` | OrderableList con drag-drop + checkbox visibility + Reset layout button, dropdown più largo |
| `frontend/src/lib/components/table/DataTableColumnFilter.svelte` | Commenti documentazione scala slider |
| `frontend/src/lib/components/ui/CalendarMonth.svelte` | Rimuovere `flex-1` dal root div, passare `compact` e `showChevron={false}` ai SimpleSelect |
| `frontend/src/lib/components/ui/DateRangePicker.svelte` | `max-w-[600px]` popover, close-on-scroll listener, granularity SimpleSelect compatto |
| `frontend/src/lib/components/ui/SingleDatePicker.svelte` | Smart direction (sopra/sotto), close-on-scroll listener |
| `frontend/src/lib/components/ui/select/SimpleSelect.svelte` | Nuove prop `compact`/`showChevron`, padding ridotto in compact, `stopPropagation` scroll dropdown |
| `frontend/src/lib/components/ui/data-editor/DataEditor.svelte` | ColumnVisibilityToggle spostato a destra, future date cap in `handleAddRow()` |
| `frontend/src/lib/components/charts/MeasurePanel.svelte` | Eye → ColumnVisibilityToggle per DataTable, `measureTableRefs`, rimozione `hiddenTableIds`, header `flex-wrap` |
| `frontend/src/lib/components/charts/SignalStyleEditor.svelte` | `min-w-[50px] flex-1`, debounce `oninput` color picker |

---

## Feature rimandati

| Feature | Motivo |
|---------|--------|
| SignalStyleEditor popover fixed positioning | Il positioning `absolute` attuale funziona — confermare con test manuale |
| ColumnVisibilityToggle persistenza ordine in localStorage | Richiede estensione del localStorage schema del DataTable — valutare in round successivo |
| Auto-focus su click punto grafico → editor | Richiede coordinazione chart→DataEditor non ancora implementata |
| FX Sync API Redesign | Endpoint bulk per coppie — piano separato: `plan-fxSyncApiRedesign.prompt.md` |

