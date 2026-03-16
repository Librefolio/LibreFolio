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

### 6. ✅ Fix freccia misura (B30)

**File**: `frontend/src/lib/components/charts/PriceChartFull.svelte` (L310–370)

Importare `computeArrowRotation` da `frontend/src/lib/components/charts/lineChartHelpers.ts` (L428–480). Sostituire le chiamate a `segmentArrowRotation(isStart)` con `computeArrowRotation(signalSeriesData, markerIdx, isStart)`. Eliminare la funzione inline custom `segmentArrowRotation`.

La funzione `computeArrowRotation` funziona correttamente ora che `MeasureSignal.computePoints()` interpola tutti i punti tra start/end (fix B31), quindi ci sono vicini non-null su cui calcolare la pendenza.

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

### 9. ✅ Fix cache lingua provider modal (3 sotto-problemi)

**9a — Richieste inutili nonostante cache**

**File**: `frontend/src/lib/stores/currencyGraphStore.ts` (L53–62)

`getCurrencyGraph()` chiama `ensureCurrenciesLoaded(language)` **anche se il grafo è già in cache** (L54 fa return prima quando `cachedGraph` esiste, ma quando non c'è cache la lingua sbagliata causa rebuild). Il grafo usa solo codici currency (non nomi localizzati) → **non serve ricaricare le currency quando il grafo è già costruito**. Fix: se il grafo è già costruito (`cachedGraph` non null), non chiamare `ensureCurrenciesLoaded` e non ricostruire. Per il primo build, usare la lingua corrente dell'UI.

**9b — Parametro lingua sbagliato**

**File**: `frontend/src/lib/components/fx/FxPairAddModal.svelte` (L391)

Passare `language={$currentLanguage}` a `FxProviderSelect` (importare `currentLanguage` dallo store i18n). Attualmente manca la prop → default `'en'` in `FxProviderSelect.svelte` L67 → la chiamata a `ensureCurrenciesLoaded('en')` invalida la cache italiana in `currencyStore.ts` L56–61, sovrascrivendola con dati EN.

**9c — Route già selezionate visibili nel picker**

**File**: `frontend/src/lib/components/ui/select/FxProviderSelect.svelte`

`loadRoutesFromBackend()` (in FxPairAddModal L90–117) carica le route attuali dal backend (via `list_routes` API) e popola `selectedRoutes`. `FxProviderSelect.computeRoutes()` calcola le opzioni disponibili per aggiungerne di nuove. **Non è un problema di race condition** — sono due scopi diversi (opzioni vs selezione corrente). Assicurarsi che le route già selezionate (`selectedKeys`) vengano nascoste dal picker "Aggiungi route" — verificare che `hasUnselectedRoutes` e il filtraggio in FxProviderSelect L182 funzionino correttamente con le route caricate dal backend. Ogni apertura in editMode chiama sempre `list_routes` API per avere le priorità fresh dal backend.

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

