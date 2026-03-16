# Plan: Fix Bug Round 4 — FX Detail Page (Piano Definitivo Consolidato)

**Dipendenze**: [`plan-fxDetailPageRedesign.prompt.md`](plan-fxDetailPageRedesign.prompt.md) (Rounds 1–3 completati, vedi sezione Bug Report)

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

### 4. Migrare tabella riepilogo misure a DataTable

> **DA FARE PRIMA** — semplice, valida retrocompatibilità DataTable prima del refactor più grande.

**File**: `frontend/src/lib/components/charts/MeasurePanel.svelte` (L252–296)

Sostituire la `<table>` HTML con `<DataTable>`. Configurazione:

- **Colonne**:
  - Signal (text, con `●` colorato inline)
  - Value @ Start (number)
  - Value @ End (number)
  - Δ Abs (number, con classe colore pos/neg)
  - Δ % (number, colore pos/neg)
  - Δ%/yr (number + Tooltip con `math={true}` e formula `$(1 + \Delta\%)^{365/d} - 1$`)
- **Props DataTable**:
  - `enableSelection={false}`, `enableActions={false}`
  - `enableSorting`, `enableColumnFilters`, `enableColumnVisibility`, `enableColumnResize`
  - `enablePagination={false}` (poche righe)
  - `storageKey="measure-summary"`
- I dati sono costruiti unendo la riga "pair principale" + righe segnali overlay (come ora, L271–294).
- Formattazione colori pos/neg: usare `CellContent` di tipo `custom` con snippet HTML per evitare di complicare i tipi generici.

### 5. Migrare DataEditor a DataTable

> **DA FARE DOPO** — più complesso, sfrutta validazione dello step 4.

**5a — Tipo riga `FxRateRow`**

**File**: `frontend/src/lib/components/ui/data-editor/DataEditorTypes.ts`

```typescript
interface FxRateRow {
    id: string;
    date: string;
    dayOfWeek: string;
    rate: number | null;
    status: 'original' | 'edited' | 'deleted' | 'appended';
    _originalRate: number | null;
}
```

Giorni vuoti (gap) = righe normali con `rate = null`, `status = 'appended'`, inseriti in ordine cronologico. **Niente row-folding** → paginazione DataTable.

**5b — Colonne DataTable**

- **Data** (`date`, sortable): formattata con giorno settimana abbreviato
- **Rate** (`editable-number` dallo step 3): `step=0.0001`
- **Status** (`enum`): badge colorato (verde=original, arancio=edited, rosso=deleted, blu=appended). **Colonna nascosta di default**, filtrabile
- **Azioni**: pulsante 🗑/↩ che alterna delete↔restore. Per righe appended vuote: nessuna azione

**5c — Props DataTable**

`enableSelection={false}`, `enableActions={true}` (solo azione delete/restore), `enableSorting`, `enableColumnFilters`, `enableColumnVisibility`, `enablePagination`, `getRowClass` per sfondo condizionale basato su status.

**5d — Vista CSV asincrona**

**File**: `frontend/src/lib/components/ui/data-editor/DataEditor.svelte` (~L161)

`rowsToCsv()`: rendere lazy con `setTimeout` chunking per evitare il crash 1073ms. Mostrare spinner durante la conversione.

**5e — Preview come segnale overlay (invisibile in UI)**

Le righe dirty (edited/appended con valore) vengono renderizzate come un `RenderedSignal` aggiuntivo nell'array `allOverlaySignals`:

- Label: `'Preview'`, `lineWidth: 3`, `lineType: 'solid'`
- Colore distinto: `#a855f7` (viola)
- I punti del segnale preview usano colori individuali allineati allo status: arancio per edited, blu per appended (`itemStyle` per-point nella serie ECharts)

Questo segnale **non compare** nel pannello Signals/Measures — è aggiunto solo all'array passato a PriceChartFull.

Rimuovere la prop `pendingData` da PriceChartFull e la relativa logica di serie separata.

**Il chart NON ricalcola gli altri segnali overlay finché non si salva** — la preview è un segnale puro sovrapposto.

### 6. ⚠️ Fix freccia misura (B30) — RICHIEDE FIX SCALE

**File**: `frontend/src/lib/components/charts/lineChartHelpers.ts`

**Iterazione 1** (completata): Riscritta `computeArrowRotation` con algoritmo semplificato a 2 punti (punto attuale + precedente non-null). Rimossi: multi-vicini, `allVals.filter()`.

**Iterazione 2** (da fare): L'angolo è ancora sbagliato perché `dx` (indice 0..N) e `dy` (dato es. 0.00..0.09) vivono in scale completamente diverse. `atan2(0.09, 100)` ≈ 0.05° → freccia quasi piatta. In più, l'angolo visivamente corretto dipende dalla finestra di zoom (cambia l'aspect ratio Y/X).

**Analisi del problema**:
- `dx` è in unità indice (0..N punti), `dy` è in unità dato (es. 0.84..0.87)
- Il rapporto `dy/dx` in coordinate dati NON corrisponde alla pendenza visiva
- La pendenza visiva dipende da: larghezza pixel griglia / range X visibile, altezza pixel griglia / range Y visibile
- Quando lo zoom cambia, il range visibile cambia → l'angolo deve cambiare
- Ergo: l'angolo è funzione dello **stato corrente del chart** (zoom, resize, assi), non solo dei dati

**Approcci proposti**:

**A. Post-render con `convertToPixel` + aggiornamento su zoom/resize**
- Dopo ogni render/zoom/resize, iterare tutti i marker con freccia
- Usare `chart.convertToPixel('grid', [dateIndex, value])` per i 2 punti
- Calcolare l'angolo da pixel delta → sempre corretto
- Aggiornare solo `symbolRotate` via `chart.setOption({series: [...]}, {replaceMerge: []})`
- **Pro**: Massima accuratezza, gestisce zoom/resize/axis-change
- **Con**: Richiede accesso all'istanza ECharts dentro la funzione di rotazione; potenziale costo su zoom frequenti (mitigabile con `requestAnimationFrame`)
- **Dove agganciare**: evento `dataZoom` + `resize` su chart, callback in LineChart.svelte

**B. Custom `renderItem` series per i marker**
- Sostituire i `symbol` nativi ECharts con una serie `type: 'custom'` + `renderItem`
- Dentro `renderItem`, `api.coord([x, y])` dà coordinate pixel → calcolo angolo
- ECharts richiama `renderItem` automaticamente a ogni render/zoom
- **Pro**: Più pulito, ECharts gestisce tutto il lifecycle
- **Con**: Refactor significativo di come i segnali renderizzano i marker; la renderizzazione custom è più complessa dei symbol nativi

**C. `markLine` con frecce**
- Usare `markLine` ECharts con `symbol: ['arrow', 'arrow']` ai bordi del segnale
- ECharts gestisce orientamento freccia lungo la linea automaticamente
- **Pro**: Nessun calcolo manuale di angoli, feature built-in
- **Con**: `markLine` è pensato per annotazioni, non per marker per-punto; limitato a coppie di punti; potrebbe non integrarsi con lo stile marker attuale (shape + size configurabili)

**D. Passare le dimensioni pixel e i range assi alla funzione**
- Modificare la signature: `computeArrowRotation(signalData, idx, isStart, xScale, yScale)`
- `xScale = gridWidthPx / visibleIndexRange`, `yScale = gridHeightPx / visibleYRange`
- `dx_px = dx * xScale`, `dy_px = dy * yScale` → `atan2(-dy_px, dx_px)`
- **Pro**: Modifica minimale alla funzione; concettualmente semplice
- **Con**: Il chiamante deve ottenere le dimensioni pixel e i range assi dal chart, e ricalcolare su ogni zoom/resize (stesse dipendenze dell'approccio A ma con più parametri da passare)

**Raccomandazione**: Approccio **A** — `convertToPixel` è la via più diretta e meno invasiva. La funzione attuale resterebbe quasi invariata (cambia solo la fonte di `dx`/`dy`: pixel anziché dati). L'aggiornamento su zoom si aggancia agli eventi ECharts già presenti nel componente. Se il costo su zoom fosse troppo alto, si può fare debounce o `requestAnimationFrame`.

**⏳ In attesa di review utente per decidere approccio.**

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

### 8. Estrarre SignalStyleEditor + formula LaTeX (B27 + B28)

**Nuovo file**: `frontend/src/lib/components/charts/SignalStyleEditor.svelte`

Estrarre dal popover stile in `frontend/src/lib/components/charts/ChartSignalsSection.svelte` (L391–491) — color picker + SVG line preview + popover con marker grid/line type/width. Props:

```typescript
interface Props {
    style: SignalStyle;
    onstylechange: (key: string, value: any) => void;
}
```

Riusarlo in:
- `ChartSignalsSection.svelte` — al posto del codice inline attuale
- `MeasurePanel.svelte` (L211–249) — al posto dell'editor estetico inline semplificato

**Formula LaTeX**: In `MeasurePanel.svelte` L264, usare il Tooltip con prop `math={true}`:

```svelte
<Tooltip text="$(1 + \Delta\%)^{365/d} - 1$" math={true} position="top" maxWidth="220px">
    <CircleHelp size={11} class="text-gray-400 hover:text-libre-green cursor-help transition-colors" />
</Tooltip>
```

### 9. ✅⚠️ Fix cache lingua provider modal (3 sotto-problemi) — RICHIEDE RE-FIX

**Stato dopo primo fix**: Aggiunto `language={$currentLanguage}` a `FxProviderSelect` e sync effect per `selectedKeys`. Ma il test mostra che la chiamata API currencies usa ancora `language=en`, e le route pre-esistenti non vengono mostrate.

**9a — La lingua è ancora 'en' nonostante il fix**

Il problema è più profondo del solo `FxProviderSelect`. La catena di chiamate è:
1. `FxProviderSelect.computeRoutes()` → `findConversionPaths(base, quote, 4, language)`
2. `findConversionPaths()` → `getCurrencyGraph(language)`
3. `getCurrencyGraph(language)` → `ensureCurrenciesLoaded(language)`

Ma `getCurrencyGraph` ha default `language = 'en'` (L53 di currencyGraphStore.ts), e anche `findConversionPaths` (L122). Il grafo usa solo codici currency (non nomi localizzati) → **eliminare il parametro `language` da `getCurrencyGraph` e `findConversionPaths`**, e far sì che `ensureCurrenciesLoaded` dentro `getCurrencyGraph` usi la lingua già caricata in cache, oppure la lingua corrente dallo store. In alternativa, non chiamare affatto `ensureCurrenciesLoaded` da `getCurrencyGraph` se le currencies sono già caricate — verificare con `isCurrenciesLoaded()`.

**9b — Route pre-esistenti non mostrate**

`loadRoutesFromBackend()` in FxPairAddModal chiama l'API `list_routes` e imposta `selectedRoutes`. Ma il sync $effect aggiunto in `FxProviderSelect` potrebbe non attivarsi correttamente: le chiavi generate da `selectedRoutes` potrebbero non matchare quelle in `routeMap` (che è costruito da `computeRoutes`). Il problema è di **timing**: `computeRoutes` è asincrono e potrebbe non aver ancora popolato `directRoutes`/`chainRoutes` quando il sync effect tenta il matching. Serve garantire che il sync avvenga DOPO che `computeRoutes` ha completato.

**9c — Route pre-esistenti non richieste**

Verificare nel network tab se `list_routes_api_v1_fx_providers_routes_get` viene effettivamente chiamato. Se non viene chiamato, il problema è che il `$effect` in FxPairAddModal (L81–88) non si attiva — probabilmente perché `open`, `editMode`, `editBase`, `editQuote` non sono tutti truthy al momento giusto.

### 10. Naming i18n + abbreviazioni segnali

**Provider/Fornitori**: unificare in tutte le lingue.

- IT: `fxDetail.providers` → "Provider" (non "Fornitori"), `fx.addPair.titleEdit` → "Modifica Provider"
- In `frontend/src/lib/i18n/it.json` L797 (`"providers": "Fornitori"`) vs L340 (`"titleEdit": "Modifica Provider Coppia"`) — rendere coerenti
- Analoghi per EN/FR/ES

**Abbreviazioni segnali**: aggiungere chiavi `chartSettings.signals.*.abbr` per ogni lingua:

| Segnale | IT | EN |
|---------|----|----|
| Linear Growth | C.Lin | Lin |
| Compound Growth | C.Comp | Comp |
| Sine Wave | Onda Sin | Sine |
| FX Pair | Coppia FX | FX |
| EMA | EMA | EMA |
| MACD | MACD | MACD |
| RSI | RSI | RSI |
| Bollinger | Boll | Boll |

Usarle nei `getLabel()` dei segnali tramite un helper i18n-aware.

### 11. FxPair signal: lista completa + pulsanti Sync/Detail

**File**: `frontend/src/lib/components/charts/ChartSignalsSection.svelte`

- Verificare che `getRegisteredPairs()` restituisca **tutte** le coppie configurate nel dropdown FxPair signal (non solo il provider corrente).
- Sulla card FxPair (L338–366), aggiungere accanto al 🗑 cestino:
  - Pulsante 🔄 **Sync**: chiama API sync per quella coppia specifica
  - Pulsante 🔗 **Detail**: naviga a `/fx/{slug}` (abbandona il lavoro corrente sulla pagina)

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
| Arrow rotation: serve `isStart`? | Sì. Ma il problema principale è la **mismatch di scala**: `dx` (indici) vs `dy` (dati) producono angoli quasi piatti. L'angolo corretto richiede conversione in pixel-space, e cambia con zoom/resize. 4 approcci proposti (A/B/C/D), raccomandata A (`convertToPixel` + update su zoom) |
| Provider cache: approccio? | Eliminare param `language` da `getCurrencyGraph`/`findConversionPaths`. Sync route dentro `computeRoutes()` dopo popolamento |
| Measure preview: interpolazione? | No, preview mostra solo start+end. Al 2° click calcola intermedi per la leggenda |
| DatePicker misure: quale componente? | Potenziare DateRangePicker con prop `showPresets={false}`. Usa 2 date (start+end), stesse logiche assegnazione |

---

## Nuovi Feature Request (emersi durante test Round 4)

### F1. Preview live misura durante piazzamento (B6) — CONFERMATO

Dopo il 1° click, ogni volta che il mouse passa su un nuovo punto del grafico:
- Distruggere il segnale misura temporaneo precedente
- Crearne uno nuovo con stessa configurazione di stile ma con `endDate` = punto corrente sotto il mouse
- **Semplificazione**: la preview mostra SOLO punto iniziale e finale (nessuna interpolazione intermedia), così il rendering è leggero
- Al 2° click: calcolare tutti i punti intermedi (interpolazione) per avere la leggenda opportuna con dati completi
- La tabella riepilogo mostra i dati della preview in tempo reale (solo start/end, senza annualizzazione durante il drag)

**Implementazione**:
- `MeasurePanel`: aggiungere `pendingMeasure: MeasureSignal | null`, metodo `updatePendingEnd(date, value)` chiamato dal parent
- `PriceChartFull`: collegare `mousemove` ECharts → `onMeasureHover(date, value)` (solo in measureMode e dopo 1° click)
- `+page.svelte`: wiring callback `onMeasureHover` → `measurePanel.updatePendingEnd()`

### F2. DatePicker per editare punti misura — CONFERMATO (potenziare DateRangePicker)

Potenziare il componente `DateRangePicker` esistente per renderlo parametrico:
- Aggiungere prop per nascondere/mostrare i badge con la selezione della finestra temporale (presets 1W/1M/3M/etc.)
- Per le misure servono 2 date (start + end, la misura ha senso solo tra 2 giorni diversi)
- Le logiche di assegnazione (click su giorno, highlight range, validazione) sono identiche al range picker attuale
- In pratica: `DateRangePicker` con `showPresets={false}` usato inline nella card misura per editare `startDate`/`endDate`

