# Plan: Fix Bug Round 4 — FX Detail Page (Piano Definitivo Consolidato)

**Dipendenze**: [`plan-fxDetailPageRedesign.prompt.md`](plan-fxDetailPageRedesign.prompt.md) (Rounds 1–3 completati, vedi sezione Bug Report)
**Successivo**: [`plan-fxDetailBugRound5.prompt.md`](plan-fxDetailBugRound5.prompt.md)

Risoluzione di 14 issue: rimozione dataZoom residuo, riordino pannelli, migrazione tabella misure e DataEditor a DataTable, fix freccia/ruler/colori, cache lingua, preview come segnale invisibile, stile condiviso, i18n. Ordine di esecuzione ottimizzato: prima i quick-fix, poi la migrazione misure (valida retrocompatibilità DataTable), poi il DataEditor complesso.

---

## Steps

### 1. ✅ Rimuovere dataZoom slider residuo da PriceChartFull

**File**: `frontend/src/lib/components/charts/PriceChartFull.svelte`

In L441–447: rimuovere `dataZoom[0]` (tipo `slider`), tenere solo `dataZoom[1]` (tipo `inside`). Ridurre `grid[0].bottom` da ~50 a ~20. Aggiornare commento header.

### 2. ✅ Spostare DataEditor sopra Measures

**File**: `frontend/src/routes/(app)/fx/[pair]/+page.svelte`

Muovere il blocco `{#if showDataEditor}` (L711–765) subito dopo il chart (L652), prima del pannello Measures (L654). Ordine finale: Aesthetics → Chart → **DataEditor** → Measures → Signals.

### 3. ✅ Aggiungere `EditableNumberCell` e `getRowClass` al DataTable (retrocompatibile)

**3a — Nuovo tipo cella in types.ts**

**File**: `frontend/src/lib/components/table/types.ts`

Aggiungere `EditableNumberCell` all'unione `CellContent`:

```typescript
interface EditableNumberCell {
    type: 'editable-number';
    value: number | null;
    step?: number;
    placeholder?: string;
    onchange: (newValue: number | null) => void;
}
```

**3b — Rendering in DataTable.svelte**

**File**: `frontend/src/lib/components/table/DataTable.svelte` (~L814–876)

Nel blocco `{#if cellContent.type === ...}`, aggiungere il caso `'editable-number'` che renderizza un `<input type="number">`. Al blur/enter chiama `cellContent.onchange(parsedValue)`.

**3c — Prop `getRowClass` nel DataTable**

**File**: `frontend/src/lib/components/table/DataTable.svelte`

Aggiungere prop opzionale `getRowClass?: (row: T) => string` all'interfaccia Props. Nella renderizzazione `<tr>` (~L788), applicare `class={getRowClass?.(row) ?? ''}`. Stili CSS per le classi:

- `row-deleted`: sfondo rosso barrato
- `row-edited`: sfondo arancio leggero
- `row-appended`: sfondo blu leggero

**Retrocompatibile**: se non passata, nessun effetto sulle tabelle esistenti.

### 4. ✅ Migrare tabella riepilogo misure a DataTable

Completato. `MeasurePanel.svelte` usa `DataTable` con `ColumnDef<MeasureSummaryRow>[]` (6 colonne: Signal, Value@Start, Value@End, ΔAbs, Δ%, Δ%/yr). Formattazione pos/neg con `HtmlCell`, `storageKey="measure-summary-{measure.id}"`.

**Round 4.1 fix**: Abilitati `enableSorting`, `enableColumnVisibility`, `enableColumnResize` (erano tutti false, ora true). Colonne ora sortabili. Colonna visibility icon (👁) visibile nella toolbar DataTable.

### 5. ✅ Migrare DataEditor a DataTable

Completato. `DataEditor.svelte` usa `DataTable` internamente con:
- `DTColumnDef<DataRow>[]` con `editable-number` cells per editing inline
- `dtRowActions` con delete/revert per azioni riga
- `getRowClass` (rowBgClass) per sfondo condizionale status (edited=blu, deleted=rosso barrato, appended=verde)
- `DataImportModal` per import CSV
- Paginazione (25/50/100/all), sorting, column filters, column visibility

**Round 4.1 fix**: Rimossa la vista CSV inline (crash su dataset grandi). Scelta UX: la tabella è l'unica vista, l'import CSV resta disponibile via modale `DataImportModal`. La sync bidirezionale CSV↔Rows (fonte di bug e crash) è stata eliminata.

**5e — Preview come RenderedSignal**: `FxDataEditorSection.svelte` emette un `RenderedSignal` viola (`#a855f7`) con le righe dirty. Il `pendingData` prop è stato rimosso da `PriceChartFull`. Il segnale preview è parte di `allOverlaySignals` nella pagina +page.svelte.

### 6. ✅ Fix freccia misura (B30) — Risolto con convertToPixel post-render

**File**: `frontend/src/lib/components/charts/lineChartHelpers.ts`

**Iterazione 1** (completata): Riscritta `computeArrowRotation` con algoritmo semplificato a 2 punti.

**Iterazione 2** (completata): Identificato root cause: `dx` (indici) e `dy` (valori) in scale diverse → angoli errati. L'angolo visivo dipende dal pixel aspect ratio (cambia con zoom/resize).

**Iterazione 3** (completata): Il caso 2-frecce usava la direzione **globale** start→end per entrambe le frecce, rendendo il marker START dipendente dalla scelta del marker END. Fix: eliminato il caso speciale, ogni freccia processata indipendentemente con pendenza locale.

**Soluzione finale**: `updateArrowRotations(chart)` — approccio unificato:

1. `computeArrowRotation()` **rimossa** (non più placeholder, proprio eliminata)
2. Tutti i call site ora usano `symbolRotate: 0` (placeholder inline)
3. `updateArrowRotations(chart)` post-render:
   - Itera ogni serie → ogni `markPoint.data` con `symbol === 'arrow'`
   - Per **ogni** freccia indipendentemente: trova il vicino non-null più prossimo (backward-first, forward-fallback)
   - `convertToPixel` per i 2 punti (marker + vicino) → angolo in pixel-space
   - `symbolRotate = towardNeighborDeg + 90` (arrow punta AWAY dal vicino, conversione math→ECharts)
   - Nessun caso speciale 1-freccia vs 2-frecce: la logica backward-first identifica automaticamente START (forward fallback → punta a sinistra) vs END (backward trovato → punta a destra)
4. Chiamata in 3 punti: post-setOption, su `dataZoom`, su `ResizeObserver`

**Cleanup**: Rimossi `computeArrowRotation` export + tutti gli import da PriceChartFull e LineChart.

**File modificati**:
- `lineChartHelpers.ts` — `computeArrowRotation()` eliminata, `updateArrowRotations()` unificata
- `PriceChartFull.svelte` — rimosso import `computeArrowRotation`, marker usano `symbolRotate: 0`
- `LineChart.svelte` — rimosso import `computeArrowRotation`, marker usano `symbolRotate: 0`

**Fix aggiuntivo**: `+page.svelte` L138 — ternario rotto `settings.colorByBaseline ? 'absolute' : 'absolute'` → `viewMode` per ricalcolo segnali (EMA, ecc.) su switch abs/%.

### 7. ✅ Fix ruler tick + colori misure distinti

**File**: `frontend/src/routes/(app)/fx/[pair]/+page.svelte` (L577–583)

Aggiungere `await tick()` tra `showMeasures = true` e `measurePanel?.startMeasureMode()`, così il DOM del pannello è montato prima di attivare la modalità add-measure.

```svelte
onclick={async () => {
    if (measureMode) {
        measurePanel?.stopMeasureMode();
    } else {
        showMeasures = true;
        await tick();
        measurePanel?.startMeasureMode();
    }
}}
```

**File**: `frontend/src/lib/components/charts/MeasurePanel.svelte` (L84)

Usare `getIndexColor(measures.length)` da `frontend/src/lib/utils/colors.ts` per generare un colore distinto (golden-ratio hue distribution) per ogni nuova misura. Convertire da `ColorSet.text` (HSL string) → hex. Sostituire il colore fisso `#f97316`.

### 8. ✅ Estrarre SignalStyleEditor + formula LaTeX (B27 + B28)

Completato. `SignalStyleEditor.svelte` estratto da `ChartSignalsSection.svelte` (L391-491). Props: `style: SignalStyle`, `onstylechange: (key, value) => void`, `simplified?: boolean`. Integrato in:
- `ChartSignalsSection.svelte` — sostituisce il codice inline
- `MeasurePanel.svelte` — sostituisce editor semplificato inline (prop `simplified`, nasconde marker grid per misure)

Formula LaTeX annualizzata: `$(1 + \Delta\%)^{365/d} - 1$` via `Tooltip math={true}` (definita come costante script-level `ANNUALIZED_FORMULA` per evitare interpolazione Svelte).

**Round 4.1 fix**: Z-index del popover alzato da z-10/z-20 a z-40/z-50 per evitare troncatura quando il popover esce dal contenitore della card misura. La card usa `overflow-visible` per permettere al popover di uscire.

### 9. ✅ Fix cache lingua provider modal (3 sotto-problemi)

**9a ✅ — Rimosso parametro `language`**: `getCurrencyGraph()` e `findConversionPaths()` in `currencyGraphStore.ts` non accettano più il parametro `language`. Il grafo usa solo codici valuta. `ensureCurrenciesLoaded()` chiamato senza argomento se currencies non sono in cache; se già caricate usa `isCurrenciesLoaded()` per skippare.

**9b ✅ — Sync route timing**: Il `$effect` in `FxProviderSelect.svelte` (L288-306) sincronizza `selectedKeys` con `selectedRoutes` quando entrambi `allRoutes.length > 0` e `selectedRoutes.length > 0`. Funziona reattivamente: sia `computeRoutes()` che `loadRoutesFromBackend()` sono asincroni, ma il sync effect si riattiva quando entrambi completano.

**9c ✅ — list_routes verificato**: `loadRoutesFromBackend()` in `FxPairAddModal.svelte` chiama `list_routes_api` e filtra per coppia. Il timing è gestito dal sistema reattivo Svelte: l'effect si attiva quando `open && editMode && editBase && editQuote` sono tutti truthy.

**Round 4.1 fix — isDirty in edit mode**: Il calcolo `isDirty` ora confronta `selectedRoutes` con un baseline (`baselineRoutesJson`) salvato dopo `loadRoutesFromBackend()`. In edit mode: dirty solo se le route sono cambiate rispetto al backend. In create mode: dirty se qualsiasi campo è stato toccato. Risolve il bug "chiudi senza modificare → chiede conferma discard".

### 10. ✅ Naming i18n + abbreviazioni segnali

- **Provider/Fornitori unificato**: `fxDetail.providers` IT cambiato da "Fornitori" a "Provider" per coerenza con il resto delle chiavi.
- **Abbreviazioni segnali**: Aggiunte 8 chiavi `chartSettings.signals.*Abbr` in tutte e 4 le lingue (EN, IT, FR, ES):
  - `linearAbbr`: Lin / C.Lin / Lin / Lin
  - `compoundAbbr`: Comp / C.Comp / Comp / Comp
  - `sineAbbr`: Sine / Onda Sin / Sin / Sine
  - `fxPairAbbr`: FX / Coppia FX / FX / FX
  - `emaAbbr`, `macdAbbr`, `rsiAbbr`: invarianti (sigle internazionali)
  - `bollingerAbbr`: Boll (tutte le lingue)
- **Funzione `getSignalAbbr()`**: Aggiunta a `ChartSignalsSection.svelte` per uso futuro nelle legende chart.
- **Chiave `common.detail`**: Aggiunta (Detail / Dettaglio / Détail / Detalle).

### 11. ✅ FxPair signal: lista completa + pulsanti Sync/Detail

- **Fix `getRegisteredPairs()` bug**: `configuredPairSlugs` nella pagina `+page.svelte` ora usa `allConfiguredSlugs` derivato dalla response `list_routes` API (caricata in `loadProviders()`), invece di `getRegisteredPairs()` che mostrava solo le coppie visitate.
- **Pulsanti Sync/Detail**: Aggiunti in `ChartSignalsSection.svelte` per le card FxPair signal:
  - 🔄 **Sync**: chiama `sync_rates_api` per la coppia selezionata (callback `onsyncpair`)
  - 🔗 **Detail**: naviga a `/fx/[pair]` (callback `ondetailpair`)
- **Handler in +page.svelte**: `handleSyncPair(slug)` e `handleDetailPair(slug)` collegati ai callback.

---

## Ordine di esecuzione

| Fase | Steps | Stima | Note |
|------|-------|-------|------|
| Quick fixes | 1, 2, 6, 7 | ~2h | Indipendenti, parallelizzabili |
| DataTable extensions | 3 | ~2h | Retrocompatibile, prerequisito per 4 e 5 |
| Migrazione misure | 4 | ~3h | Semplice, valida che DataTable funziona nel contesto |
| Migrazione DataEditor | 5 | ~1.5d | Core del lavoro, include fix CSV crash + preview segnale |
| Stile + LaTeX | 8 | ~3h | Componente nuovo, riuso in 2 posti |
| Cache provider | 9 | ~2h | 3 sotto-fix indipendenti |
| i18n + FxPair signal | 10, 11 | ~3h | Ultime pulizie |

---

## Decisioni confermate in questo round

| Domanda | Decisione |
|---------|-----------|
| Ordine migrazione DataTable? | Misure PRIMA (semplice, valida retrocompatibilità), DataEditor DOPO |
| Signal cards migrano a DataTable? | **NO** — OrderableList con drag-and-drop resta per i segnali |
| Cosa migra a DataTable? | Solo la `<table>` HTML riepilogo misure (MeasurePanel L252–296) e il DataEditor |
| Preview edits sul chart? | Segnale overlay `RenderedSignal` viola, invisibile nel pannello UI, visibile solo sul grafico |
| Tooltip formula LaTeX? | Tooltip supporta già `math={true}`, usare direttamente |
| Provider cache: race condition? | Non è race condition — `computeRoutes` (opzioni) e `loadRoutesFromBackend` (selezione) sono indipendenti. Basta nascondere le route selezionate dal picker |
| Row-folding nel DataEditor? | Rimosso — paginazione DataTable al suo posto. Giorni vuoti = righe con rate null |
| Chart update su edit? | Solo su Save — finché non si salva il chart non ricalcola segnali overlay |
| Formattazione pos/neg nelle colonne DataTable? | Usare `CellContent` custom con snippet HTML (non complicare i tipi generici) |
| Arrow rotation: serve `isStart`? | **No**, eliminato. Ogni freccia processata indipendentemente con backward-first neighbor scan. La direzione emerge dai dati: START non ha predecessore → fallback forward → punta backward. END ha predecessore → punta forward. `convertToPixel` + formula unica `towardNeighborDeg + 90` |
| Provider cache: approccio? | Eliminare param `language` da `getCurrencyGraph`/`findConversionPaths`. Sync route dentro `computeRoutes()` dopo popolamento |
| Measure preview: interpolazione? | No, preview mostra solo start+end. Al 2° click calcola intermedi per la leggenda |
| DatePicker misure: quale componente? | Potenziare DateRangePicker con prop `showPresets={false}`. Usa 2 date (start+end), stesse logiche assegnazione |

---

## Nuovi Feature Request (emersi durante test Round 4)

### F1. ✅ Preview live misura durante piazzamento (B6) — COMPLETATO

Dopo il 1° click, ogni volta che il mouse passa su un nuovo punto del grafico:
- Crea un `pendingMeasure: MeasureSignal` temporaneo con `startDate` e `endDate` aggiornati in tempo reale
- La preview mostra la linea misura completa (interpolazione tramite `render()`)
- Al 2° click, la misura diventa definitiva e il `pendingMeasure` viene cancellato
- Throttling via `requestAnimationFrame` sul handler `mousemove` per evitare troppi re-render

**Implementazione**:
- `MeasurePanel.svelte`: aggiunto `pendingMeasure: MeasureSignal | null`, metodo `export updatePendingEnd(date, value)`. `emitRendered()` include il pending measure nell'output.
- `PriceChartFull.svelte`: aggiunto prop `onMeasureHover?: (date, value) => void`, listener `getZr().on('mousemove')` con throttle rAF. Conversione da % ad assoluto se in viewMode percentage.
- `+page.svelte`: wiring `onMeasureHover` → `measurePanel.updatePendingEnd()`.

### F2. ✅ DatePicker per editare punti misura — COMPLETATO

`DateRangePicker` integrato nell'header della card misura di `MeasurePanel.svelte`:
- Quando la card è espansa, l'header mostra il DateRangePicker al posto del testo date statiche
- Props: `showPresets={false}`, `showCustomWindow={false}`, `compact={true}`
- Limitato a `max-w-[300px]` per non occupare troppo spazio nell'header
- `onchange` chiama `updateMeasureDates(id, start, end)` che aggiorna `params.startDate/endDate` e chiama `emitRendered()`
- Validazione: start !== end (misura a zero giorni non ammessa), auto-swap se start > end
- Quando la card è collassata, l'header mostra il formato compatto: `📏 date1 → date2 +X.XX% · Nd`

**Round 4.1 fix**: Spostato dall'area espansa all'header della card. Quando la card è collassata mostra le date come testo; quando è espansa, il testo viene sostituito dal DateRangePicker inline con Δ% e giorni accanto.
