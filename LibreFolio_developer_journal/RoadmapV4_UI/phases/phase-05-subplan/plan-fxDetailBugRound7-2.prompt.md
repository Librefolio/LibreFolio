# Plan: Round 7.2 — Fix feedback utente post Round 7.1

**Dipendenze**: [`plan-fxDetailBugRound7-1.prompt.md`](plan-fxDetailBugRound7-1.prompt.md)

Refinements basati su feedback utente dopo Round 7.1.

**Stato**: ✅ Completato → Seguito da hotfix Round 7.2.1 (stessa sessione) → [`plan-fxDetailBugRound7-3.prompt.md`](plan-fxDetailBugRound7-3.prompt.md)

---

## Steps

### 1. FxDataEditorSection Cancel button — Dark mode leggibilità

**File**: `frontend/src/lib/components/fx/FxDataEditorSection.svelte`

**Problema**: Il bottone Cancel ha `bg-gray-200 dark:bg-slate-600 text-gray-700 dark:text-gray-300` — in dark mode il testo grigio chiaro su sfondo grigio è quasi illeggibile.

**Soluzione**: Cambiare il testo del Cancel in dark mode a un colore più contrastante:
- `dark:text-gray-300` → `dark:text-gray-100` (bianco quasi puro su sfondo scuro)

---

### 2. ColumnVisibilityToggle — Close on scroll (ancoraggio)

**File**: `frontend/src/lib/components/table/ColumnVisibilityToggle.svelte`

**Problema**: Scrollando la pagina il dropdown resta fermo (è `position: fixed` e non segue il trigger).

**Soluzione**: Aggiungere `$effect` con listener `scroll` (capture) che chiude il dropdown quando la pagina scrolla:
```ts
$effect(() => {
    if (!open) return;
    const handleScroll = () => close();
    window.addEventListener('scroll', handleScroll, true);
    return () => window.removeEventListener('scroll', handleScroll, true);
});
```

---

### 3. DateRangePicker — Ripristino width + max-w-fit per compact

**File**: `frontend/src/lib/components/ui/DateRangePicker.svelte`

**Problema duplice**:
- Il fix `inline-block`/`inline-flex` di Round 7.1 per il caso `stacked` ha rotto il DateRangePicker nel filtro DataTable (si restringe al centro, occupa 1/3 del pannello).
- Il DateRangePicker nel MeasurePanel (compact, non stacked) si allarga a tutta larghezza pagina.

**Soluzione**: Riportare il container e il trigger a `w-full` in TUTTI i casi (come era originalmente). Il contenimento nel MeasurePanel avviene tramite il parent `max-w-[300px]` che già lo vincola. Nessun `inline-block` o `max-w-fit`.

Concretamente:
- Container: `<div class="relative drp-trigger w-full">` (sempre `w-full`)
- Trigger: `<button class="w-full flex {stacked ? 'flex-col' : ''} ...">` (sempre `w-full flex`)

---

### 4. DataTable — Rimuovere column visibility dalla toolbar, tenere solo selection counter + bulk actions

**File**: `frontend/src/lib/components/table/DataTable.svelte`, `frontend/src/lib/components/table/DataTableToolbar.svelte`

**Problema**: `showToolbar={false}` nasconde l'intera `DataTableToolbar` che contiene sia il dropdown colonne sia il counter selezione + bulk actions. L'utente seleziona righe ma non vede feedback.

**Analisi — nessuna istanza usa il dropdown colonne interno**:

| # | Componente | `showToolbar` | `enableColumnVisibility` | `bulkActions` | Column Visibility |
|---|---|---|---|---|---|
| 1 | **FilesTable** | `false` | `true` | ✅ Download+Delete | **esterna** (`ColumnVisibilityToggle` in `+page.svelte`) |
| 2 | **DataEditor** | `false` | `true` | ✅ Delete | **esterna** (`ColumnVisibilityToggle` nel toolbar custom) |
| 3 | **MeasurePanel** | `false` | `true` | ❌ | **esterna** (`ColumnVisibilityToggle` nel header) |
| 4 | **AssetPickerModal** | `true` (default) | `false` | ❌ | non serve |
| 5 | **BrokerImportFilesModal** | via FilesTable → `false` | `true` | ✅ | **esterna** (via FilesTable) |

Nessuna DataTable nel progetto usa il dropdown colonne INTERNO della toolbar. Tutte usano il componente esterno `ColumnVisibilityToggle`.

**Soluzione — semplificare radicalmente**:

1. **DataTableToolbar.svelte** — **rimuovere completamente** il dropdown colonne:
   - Rimuovere le props `columns`, `columnVisibility`, `onToggleColumn`, `onResetColumns`, `onReorderColumns`
   - Rimuovere tutto il codice drag & drop, `showColumnDropdown`, `handleClickOutside`, etc.
   - Rimuovere tutta la sezione `<div class="column-dropdown-container">` dal template
   - Rimuovere tutti i CSS relativi (`.column-dropdown`, `.column-option`, `.col-drag`, etc.)
   - **Tenere solo**: `selectedCount`, `bulkActions`, `onClearSelection`
   - Il componente mostra: `[N selected ×] [bulk action buttons]`

2. **DataTable.svelte** — semplificare la condizione e le props:
   ```svelte
   <!-- PRIMA: -->
   {#if showToolbar && (enableColumnVisibility || bulkActions.length > 0)}
       <DataTableToolbar columns={...} columnVisibility={...} ... />

   <!-- DOPO: -->
   {#if selectedRows.length > 0 && bulkActions.length > 0}
       <DataTableToolbar
           selectedCount={selectedRows.length}
           bulkActions={...}
           onClearSelection={clearAllSelection}
       />
   {/if}
   ```
   La toolbar si mostra **solo** quando ci sono righe selezionate e bulk actions disponibili.
   La prop `showToolbar` e `enableColumnVisibility` non influenzano più la toolbar (restano per backward compat ma non controllano la selezione).

3. **Rimozione prop `showToolbar`**: valutare se rimuoverla del tutto o lasciarla come no-op. Per ora la lasciamo ma non la usiamo più per la condizione toolbar.

**Risultato**: La `DataTableToolbar` diventa un componente compatto (solo counter + bulk actions), sempre visibile quando ci sono righe selezionate. Funziona identicamente per tutte le tabelle senza configurazione.

---

### 5. DataEditor / FxDataEditorSection / +page — Scroll al click punto grafico (chart → table)

**File**: `frontend/src/lib/components/ui/data-editor/DataEditor.svelte`, `frontend/src/lib/components/fx/FxDataEditorSection.svelte`, `frontend/src/routes/(app)/fx/[pair]/+page.svelte`

**Problema**: Cliccando su un punto del grafico mentre si è in edit mode, la tabella non scrolla al corrispondente dato.

**Soluzione a 3 livelli**:
1. **DataEditor**: la funzione `scrollToDate(date)` esistente deve usare `dataTableRef?.navigateToRowId(date)` (che ora include auto-scroll)
2. **FxDataEditorSection**: esporre `scrollToDate(date)` che delega al DataEditor interno
3. **+page.svelte**: nel handler click del grafico, se `showDataEditor` è true, chiamare `fxDataEditorSectionRef.scrollToDate(clickedDate)`

**Nota**: Da verificare se il chart emette già un evento click con la data del punto cliccato. Se no, va aggiunto il handler click al chart.

---

### 6. ColumnVisibilityToggle — Allineamento posizione (troppo a sinistra)

**File**: `frontend/src/lib/components/table/ColumnVisibilityToggle.svelte`

**Problema**: Il dropdown si apre traslato a sinistra (`left: 576px` con `rect.right - 220`) lasciando un gap vuoto a destra.

**Soluzione**: Usare `right` nel CSS fixed per allineare il bordo destro del dropdown al bordo destro del trigger:
```ts
const right = window.innerWidth - rect.right;
dropdownStyle = `position:fixed; right:${right}px; top:${top}; bottom:${bottom}; z-index:9999;`;
```
Rimuovere `left` dal calcolo.

---

### 7. MeasurePanel header — Layout responsive a 2 breakpoint

**File**: `frontend/src/lib/components/charts/MeasurePanel.svelte`

Layout del measure card header in 2 breakpoint implementati (+ 1 pianificato, non implementato fino a conferma utente):

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
WIDE (≥640px) — tutto su una riga:
┌────────────────────────────────────────────────────────────────────┐
│ ▾  📅 From: Jul 21 | To: Mar 23  -5.59%  · 245d   ██──────── 👁 🗑│
└────────────────────────────────────────────────────────────────────┘
 ↑chevron  ↑DateRangePicker(compact)  ↑stats       ↑style  ↑col ↑del
                                                    ↑allineato a DESTRA
                                                    max-w-[200px]
                                                    min-w-[100px]
                                                    si comprime quando
                                                    i giorni arrivano
                                                    a toccarlo

Elementi in ordine nel flex:
[chevron] [DateRangePicker compact] [stats (Δ% · days)] [spacer flex-1] [style] [👁] [🗑]

Il gruppo style+col+trash è allineato a DESTRA (spacer flex-1 prima di style).
Lo style editor: flex-shrink, min-w-[100px], max-w-[200px].
Si comprime elasticamente quando lo spazio diminuisce, fino a min 100px.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TABLET (<640px) — 2 righe (l'altezza viene dal DRP stacked):
┌──────────────────────────────────────────────────────────────────────┐
│ ▾  📅 From: Jul 21       -5.59%  · 245d                         🗑   │
│       To: Mar 23        ██────────────────────────────────      👁   │
└──────────────────────────────────────────────────────────────────────┘
 ↑chevron | ↑DateRangePicker(stacked) | ↑ blocco con 2 righe:          | ↑blocco con 2 righe:
          |  Allineato a sinistra     |   stats sopra, style sotto     |   cestino sopra, occhio sotto
          |                           |   allineato a destra come      |   allineati a destra come
          |                           |   blocco, stats text-left      |   blocco, in colonna

Il DRP stacked crea naturalmente 2 righe visive di altezza. Gli altri elementi
si organizzano internamente in 2 righe per occupare la stessa altezza.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
MOBILE (<400px) — ⚠️ PIANIFICATO, NON IMPLEMENTARE:
⚠️ Da implementare SOLO dopo conferma utente che il layout tablet
   è troppo stretto su schermi molto piccoli.

┌──────────────────────────────────┐
│ 📅 From: Jul 21 | To: Mar 23  🗑│  ← riga 1: DRP compact orizzontale + trash
│ -5.59%  · 245d                👁 │  ← riga 2: stats
│ ██──────────────────           │  ← riga 3: style + col visibility
└──────────────────────────────────┘

Cestino in alto a destra, occhio appena sotto.
DateRangePicker torna compact (orizzontale) per risparmiare spazio verticale.
```

**Implementazione dettagliata**:

1. **Breakpoint reattivo** — `matchMedia` in MeasurePanel per `isNarrow`:
   ```ts
   let isNarrow = $state(false);
   $effect(() => {
       const mql = window.matchMedia('(max-width: 639px)');
       isNarrow = mql.matches;
       const handler = (e: MediaQueryListEvent) => { isNarrow = e.matches; };
       mql.addEventListener('change', handler);
       return () => mql.removeEventListener('change', handler);
   });
   ```
   Poi passare `stacked={isNarrow}` al DateRangePicker di ogni misura.

2. **Struttura HTML — un unico flex row per entrambi i breakpoint**:
   ```svelte
   <!-- Container: una sola riga flex. L'altezza viene dal DRP stacked (2 righe). -->
   <div class="flex {isNarrow ? 'items-stretch' : 'items-center'} gap-2">

       <!-- 1. Chevron (sempre centrato verticalmente) -->
       <button class="self-center">▾</button>

       <!-- 2. DateRangePicker -->
       <DateRangePicker stacked={isNarrow} />

       <!-- 3. Stats + Style wrapper (flex-1 occupa tutto lo spazio rimanente) -->
       <div class="flex-1 flex {isNarrow
           ? 'flex-col justify-between'     ← narrow: stats sopra, style sotto
           : 'items-center gap-2'           ← wide:  stats e style in riga
       }">
           <span class="whitespace-nowrap text-xs">-5.59% · 245d</span>
           {#if !isNarrow}<div class="flex-1" />{/if}   ← spacer solo in wide
           <SignalStyleEditor class="min-w-[100px] max-w-[200px] flex-shrink" />
       </div>

       <!-- 4. Icons: eye e trash -->
       <div class="flex {isNarrow
           ? 'flex-col-reverse justify-between'  ← narrow: 🗑 sopra, 👁 sotto
           : 'items-center'                      ← wide: 👁, 🗑 in riga
       } gap-1">
           <ColumnVisibilityToggle />   <!-- 👁 -->
           <button>🗑</button>          <!-- trash -->
       </div>
   </div>
   ```

3. **Come funziona il layout tablet senza flex-wrap**:
   - Il container è `flex items-stretch` → tutti i figli hanno la stessa altezza
   - Il DRP stacked è naturalmente alto 2 righe → detta l'altezza del container
   - Il wrapper stats+style è `flex-col justify-between` → stats in alto, style in basso
   - Le icone sono `flex-col-reverse justify-between` → trash (ultimo nel DOM) in alto, eye in basso

4. **Ordine icone nel DOM**: `[👁 eye] [🗑 trash]`
   - Wide (`flex-row`): 👁 poi 🗑 (left-to-right) ✓
   - Narrow (`flex-col-reverse`): 🗑 sopra, 👁 sotto ✓

---

### 8. Tooltip headerTooltip — Formato frazione LaTeX grande

**File**: `frontend/src/lib/components/charts/MeasurePanel.svelte`

**Problema**: La formula `$(1 + \Delta\%)^{365/d} - 1$` mostra `365/d` in riga (non come vera frazione) e il testo è piccolo.

**Soluzione**: Usare `\frac{365}{d}` per una vera frazione e `\large` per ingrandire:
```
$\large (1 + \Delta\%)^{\frac{365}{d}} - 1$
```

---

### 9. MeasurePanel — Auto-delete misura su range invalido (fix corretto)

**File**: `frontend/src/lib/components/charts/MeasurePanel.svelte`

**Problema**: `updateMeasureDates` controllava se ci sono dati generici nel range (`chartData.some(d => d.date >= s && d.date <= e)`), ma la card della misura restava visibile quando `getMeasurement` tornava `null` (le date esatte start/end non avevano un data point). L'utente si aspetta che il cambio date range cancelli automaticamente la misura se invalida.

**Soluzione**: Dopo update date, verificare con `getMeasurement`. Se ritorna `null`, rimuovere la misura:
```ts
m.params.startDate = s;
m.params.endDate = e;
measures = [...measures];
const check = m.getMeasurement(chartData);
if (!check) {
    removeMeasure(id);
    return;
}
emitRendered();
```

---

## Decisioni confermate

| # | Feedback | Decisione |
|---|----------|-----------|
| 1 | Cancel dark mode | `dark:text-gray-100` |
| 2 | ColumnVisibilityToggle scroll | Close on scroll (capture listener) |
| 3 | DateRangePicker width | Riportare `w-full` sempre, parent controlla contenimento |
| 4 | Selection counter | **Rimuovere** column visibility dalla `DataTableToolbar` (nessuna istanza la usa). La toolbar diventa solo counter + bulk actions, mostrata **sempre** quando ci sono righe selezionate. |
| 5 | Chart click → table scroll | Chain: +page → FxDataEditorSection → DataEditor → DataTable.navigateToRowId |
| 6 | ColumnVisibility posizione | Usare `right` per allineare bordo destro |
| 7 | MeasurePanel layout | 2 breakpoint: wide ≥640px (1 riga flex, style allineato a destra con spacer flex-1, min 100px max 200px) + tablet <640px (stessa riga flex ma con DRP stacked che crea 2 righe visive, stats/style in flex-col, icone in flex-col-reverse). Mobile pianificato ma NON implementato. |
| 8 | Formula LaTeX | `\frac{365}{d}` + `\large` |
| 9 | Auto-delete misura | `getMeasurement` check dopo update, remove se null |

---

## File modificati

| File | Modifiche |
|------|-----------|
| `FxDataEditorSection.svelte` | Cancel button dark text, esporre `scrollToDate` |
| `ColumnVisibilityToggle.svelte` | Close on scroll, posizione allineata a destra (`right`) |
| `DateRangePicker.svelte` | Ripristino `w-full` sempre |
| `DataTableToolbar.svelte` | **Rimuovere** dropdown colonne + drag&drop. Tenere solo: `selectedCount`, `bulkActions`, `onClearSelection` |
| `DataTable.svelte` | Condizione toolbar: `selectedRows.length > 0 && bulkActions.length > 0` (indipendente da `showToolbar`) |
| `DataEditor.svelte` | `scrollToDate` via `navigateToRowId` |
| `MeasurePanel.svelte` | `matchMedia` per `isNarrow`, header responsive 2 breakpoint, `stacked={isNarrow}`, formula LaTeX `\frac`, auto-delete |
| `+page.svelte` (fx/[pair]) | Collegamento click chart → scrollToDate |

---

## Domande risolte

| Q | Domanda | Risposta |
|---|---------|----------|
| Q1 | DRP stacked nel tablet | **Opzione A**: `matchMedia('(max-width: 639px)')` → `stacked={isNarrow}`. DEVE essere stacked sotto 640px. |
| Q2 | Cestino posizione tablet | `flex-col-reverse` sul wrapper icone: DOM `[👁] [🗑]` → wide: riga [👁 🗑], narrow: colonna inversa [🗑 sopra, 👁 sotto]. Nessun `absolute`, nessun padding extra. |

---

## Domande aperte

### Q3. Step 5 — Click punto grafico
Il chart emette già un evento click con la data del punto cliccato? Da verificare nel codice di PriceChartFull/LineChart durante l'implementazione. Se non esiste, va aggiunto.
