# Plan: FX Detail Page — Redesign Completo (Rev. 3 Finale)

**Data creazione**: 16 Marzo 2026
**Status**: 📋 DETTAGLIATO — pronto per implementazione
**Priorità**: Alta (prossimo plan attivo Phase 5)
**Stima**: ~6 giorni
**Dipendenze**: `plan-fxConversionChain.prompt.md` completato
**Riferimenti**:
- `phases/phase-05-subplan/plan-fxCardRedesignChartSettings.prompt.md` — architettura chart/signal library
- `phases/phase-05-subplan/05FX_outofdate_plan/plan-phase05Fx.prompt.md` Steps 4, 6

---

## Overview

Ristrutturazione della pagina `/fx/[pair]` con: (1) chart unificato in singola istanza ECharts con 2 grid e `dataZoom` nativo condiviso (nessuna sincronizzazione manuale); (2) pannelli foldabili inline per estetica e segnali, realizzati con gli stessi sotto-componenti della `ChartSettingsModal` (zero duplicazione); (3) `DataEditor` generico duale testo/tabella con row-folding, stati riga, import CSV tramite `CsvEditor` evoluto; (4) sistema Measure come segnali overlay multipli con tabella riepilogo valori; (5) provider config via `FxPairAddModal` in modalità edit. Si cancellano `DataZoomBar.svelte`, `MeasureOverlay.svelte`, `EditPopup.svelte`. Si deprecano `CandlestickChart`/`VolumeBar` per Phase 6.

### Grafo dipendenze implementative

```
Step 1 (cleanup)
  ↓
Step 2 (CsvEditor runes) → Step 3 (DataEditor) → Step 4 (FxDataEditorSection)
                                                         ↓
Step 5 (fattorizzazione modale) ──────────────────────→ Step 9 (layout pagina + wiring)
                                                         ↑
Step 6 (chart unificato) → Step 7 (MeasureSignal+Panel) ─┘
                                                         ↑
Step 8 (FxPairAddModal editMode) ────────────────────────┘
                                                         ↓
                                                    Step 10 (i18n, test, cleanup)
```

---

## Step 1 — Deprecare/cancellare componenti obsoleti

**Stima**: 1h

### Cancellare

| File | Motivo |
|------|--------|
| `frontend/src/lib/components/charts/DataZoomBar.svelte` | Usato solo in `PriceChartFull`, sostituito dalla griglia unificata ECharts (Step 6). Componente embrionale. |
| `frontend/src/lib/components/charts/MeasureOverlay.svelte` | Overlay SVG/CSS fragile e disallineato, sostituito da `MeasureSignal` nativo ECharts (Step 7). |
| `frontend/src/lib/components/charts/EditPopup.svelte` | L'edit si fa dalla tabella DataEditor, non da popup su punto chart. |

### Aggiornare

- **`frontend/src/lib/components/charts/index.ts`**: Rimuovere export di `DataZoomBar`, `MeasureOverlay`, `EditPopup`.
- **`frontend/src/lib/components/charts/PriceChartFull.svelte`**: Rimuovere import di `DataZoomBar` e `MeasureOverlay`, tutta la logica di sincronizzazione zoom esterna (`zoomRange`, `handleZoomBarChange`, `handleChartZoomChange`), prop `chartApi`. Il componente diventa temporaneamente un wrapper semplificato di `LineChart` + `ChartToolbar`, prima della ricostruzione in Step 6.
- **`frontend/src/lib/components/charts/LineChart.svelte`**: Rimuovere prop `onChartReady` e relativa interfaccia `ChartApi` (non più necessari senza MeasureOverlay — il piazzamento misure userà `onPointClick` già esistente). Rimuovere commenti riferiti a MeasureOverlay.

### Deprecare (TODO Phase 6)

- **`frontend/src/lib/components/charts/CandlestickChart.svelte`**: Aggiungere commento `// TODO Phase 6 (Assets): Implement for OHLC data. Not applicable to daily FX close rates.`
- **`frontend/src/lib/components/charts/VolumeBar.svelte`**: Stesso commento.
- **`TODO_FUTURI.md`**: Aggiungere sezione:
  ```
  ## 📊 CandlestickChart / VolumeBar — Phase 6 (Assets)

  **Data aggiunta**: 16 Marzo 2026
  **Status**: 📋 PIANIFICATO
  **Priorità**: Media (Phase 6)

  ### Contesto
  Per FX si hanno solo close rate giornalieri — non esiste OHLC reale.
  CandlestickChart e VolumeBar saranno implementati quando avremo dati OHLC
  reali dagli asset source provider (yfinance, JustETF).

  ### File
  - `frontend/src/lib/components/charts/CandlestickChart.svelte` (stub)
  - `frontend/src/lib/components/charts/VolumeBar.svelte` (stub)

  ### Note
  - Per FX il toggle Line/Candlestick resta disabilitato (`disableCandlestick={true}`)
  - L'OHLC sintetizzato (O=prev close) non ha valore informativo per FX
  ```

---

## Step 2 — Evolvere `CsvEditor` a Svelte 5 runes + funzionalità import

**Stima**: 2h
**File**: `frontend/src/lib/components/fx/CsvEditor.svelte`

### Stato attuale

Il `CsvEditor` (263 righe) usa Svelte 4: `export let`, `$:` reactive statements, `createEventDispatcher`. Ha textarea con numeri riga, validazione live per riga, e metodi pubblici `scrollToLine`, `appendRow`, `updateLine`.

### Modifiche

1. **Migrazione Svelte 5 runes**:
   - `export let` → `$props()` con interface `Props`
   - `$:` → `$derived` / `$derived.by()`
   - `createEventDispatcher` → callback props (`onchange`, `oninput`)
   - `export function` → mantenute come metodi pubblici (Svelte 5 supporta)

2. **Nuove funzionalità**:
   - Prop `placeholder?: string` — messaggio guida quando textarea è vuota
   - Callback `onvalidchange?: (validRows: ParsedRow[], errorCount: number, hasDuplicates: boolean) => void` — feedback strutturato
   - Metodo pubblico `setText(text: string)` — per import programmatico (modale import)
   - **Validazione date duplicate**: nella logica di validazione, dopo il parsing di tutte le righe, controllare se ci sono date duplicate. Righe duplicate → highlight giallo (classe `bg-amber-50 dark:bg-amber-900/20`), messaggio errore "Duplicate date: YYYY-MM-DD". Flag `hasDuplicates` esposto nel callback.

3. **Tipo `ParsedRow` aggiornato**: Spostare l'export `ParsedRow` fuori dal `<script context="module">` (deprecato in Svelte 5) — esportarlo da un file separato o inline nel `<script>`.

### Motivazione

Il CsvEditor verrà riusato nel `DataEditor` (vista testo) e nella `DataImportModal`. Migrare a runes allinea con gli standard del progetto. Non ha senso lasciarlo invariato "per usi futuri" — evolverlo ora.

---

## Step 3 — Creare `DataEditor`: componente generico duale Testo ↔ Tabella

**Stima**: 1.5 giorni (componente più complesso del plan)

### 3A — Tipi (`DataEditorTypes.ts`)

**Nuovo file**: `frontend/src/lib/components/ui/DataEditorTypes.ts`

```typescript
/** Status of a row in the DataEditor */
export type RowStatus = 'original' | 'edited' | 'deleted' | 'appended';

/** Definition of a data column (configurable per use-case) */
export interface ColumnDef {
    /** Unique key used in DataRow.values */
    key: string;
    /** Display label for column header */
    label: string;
    /** Data type for input rendering and validation */
    type: 'date' | 'number' | 'string';
    /** Whether the user can edit this column */
    editable: boolean;
    /** Whether a value is required (non-empty) */
    required: boolean;
    /** Number step for type 'number' inputs */
    step?: number;
    /** Placeholder text for empty cells */
    placeholder?: string;
}

/** A single row in the DataEditor */
export interface DataRow {
    /** ISO date YYYY-MM-DD — always present, serves as row key */
    date: string;
    /** Current editing status */
    status: RowStatus;
    /** Original status when the row was loaded (to detect if it can be reverted) */
    originalStatus: 'original' | 'appended';
    /** Column values keyed by ColumnDef.key */
    values: Record<string, unknown>;
    /** Whether this row is selected for bulk operations */
    selected: boolean;
}

/** A folded gap placeholder in the table view */
export interface GapRow {
    type: 'gap';
    startDate: string;
    endDate: string;
    dayCount: number;
    expanded: boolean;
}

/** Union type for table rendering */
export type TableRow = (DataRow & { type: 'data' }) | GapRow;
```

Colonne fisse sempre presenti (non in `ColumnDef[]`, gestite internamente):
- "Date" (YYYY-MM-DD + giorno settimana abbreviato)
- "Status" (dropdown con `SimpleSelect`, opzioni contestuali)

Le colonne dati sono configurabili: FX → `[{key:'rate', label:'Rate', type:'number', ...}]`; Asset futuro → `[{key:'open',...}, {key:'high',...}, {key:'low',...}, {key:'close',...}, {key:'volume',...}]`.

### 3B — `DataEditor.svelte`

**Nuovo file**: `frontend/src/lib/components/ui/DataEditor.svelte`

**Props**:
```typescript
interface Props {
    /** Configurable data columns (e.g., [{key:'rate',...}] for FX) */
    columns: ColumnDef[];
    /** All rows (bindable) */
    rows: DataRow[];
    /** Current view mode */
    viewMode?: 'text' | 'table';
    /** Read-only mode */
    readonly?: boolean;
    /** Base currency for CSV header */
    baseCurrency?: string;
    /** Quote currency for CSV header */
    quoteCurrency?: string;
    /** Emits only dirty rows (status !== 'original') */
    onchange?: (dirtyRows: DataRow[]) => void;
    /** Emits when view mode changes */
    onviewmodechange?: (mode: 'text' | 'table') => void;
}
```

#### Vista Testo (tab "CSV")

- Embed del `CsvEditor` (Step 2) come textarea
- Il testo CSV è la single source of truth nella vista testo
- Parsing bidirezionale: modifica testo → re-parse in `DataRow[]`
- **Blocco switch a tabella** se:
  - Il CSV ha errori di validazione (righe rosse)
  - Ci sono date duplicate (righe gialle) — messaggio: "Fix duplicate dates before switching to table view"

#### Vista Tabella (tab "Table")

- **Colonne**: ☑ Selezione | Data (YYYY-MM-DD + giorno settimana) | [colonne dati da `ColumnDef[]`] | Status (`SimpleSelect`)
- **Row folding**: Gap > 2 giorni tra date consecutive → riga collassata "⋯ N days gap (DD/MM — DD/MM)". Click → espande N righe vuote editabili. Le righe espanse hanno `status: 'appended'` appena si inserisce un valore.
- **Bottone "Add Row"** in fondo: riga con `status: 'appended'`, data = oggi
- **Bottone "Go to date"**: Single-column del `DateRangePicker` (già sviluppato) per navigare a una data specifica
- **Selezione multipla + "Mark as deleted"**: Checkbox su righe in ordine sparso → bottone applica `status: 'deleted'` a tutte le selezionate → sfondo rosso barrato
- **Righe `'deleted'`**: Visibili ma barrate, sfondo rosso tenue, finché non si salva
- **Status dropdown contestuale** (`SimpleSelect`):
  - Riga Original → può diventare Edited (se valore modificato) o Deleted
  - Riga Appended → può diventare Deleted
  - Riga Deleted → può tornare a Original o Appended (ripristino)
  - Riga Edited → può tornare a Original (revert al valore originale) o diventare Deleted
- **Celle dati vuote**: Editabili — appena si inserisce un valore, status → `'edited'`
- **Riga Original con valore modificato**: status → `'edited'` automaticamente

#### Sincronizzazione tra viste

Le due viste non sono mai visibili contemporaneamente. Il switch esegue conversione:
- **Text → Table**: Parse CSV → populate `DataRow[]`. Bloccato se errori/duplicati.
- **Table → Text**: Serialize `DataRow[]` → aggiorna testo CSV (righe `'deleted'` escluse dal CSV).

#### Toolbar

Barra sopra il contenuto con:
- Toggle [CSV | Table] (segmented button)
- [Import CSV] — apre `DataImportModal` (Step 3C)
- [Add Row] (solo in vista tabella)
- Contatore: "N modified, M deleted, K new"
- [Save (N) | Cancel] — a destra

### 3C — `DataImportModal.svelte`

**Nuovo file**: `frontend/src/lib/components/ui/DataImportModal.svelte`

Modale (`ModalBase`) con:
- **Area drag & drop / file picker** in cima: accetta `.csv`, `.txt`. Drop zone con bordo tratteggiato e icona upload.
- **`CsvEditor`** (Step 2) sotto come textarea di anteprima/modifica — NON una textarea grezza
- Il file caricato → `csvEditor.setText(contenuto file)` → sovrascrive contenuto esistente
- **All'OK**: parse righe valide → merge nel `DataEditor`:
  - Date già esistenti come `'original'` → diventano `'edited'`
  - Date nuove → `'appended'`
  - Nessuna delete da import (conservativo, come richiesto)
- **Cancel**: chiude senza fare nulla

### Motivazione nuovo componente

La dualità text/table, row-folding, stati riga, import modale superano la complessità del CsvEditor. Il `DataEditor` è un componente di livello superiore che **compone** il CsvEditor (per la vista testo) e componenti tabella. È in `lib/components/ui/` perché generico — le colonne sono configurabili per riuso in Phase 6 (Asset con colonne OHLC).

---

## Step 4 — Creare `FxDataEditorSection.svelte`: wrapper FX del DataEditor

**Stima**: 0.5 giorni
**Nuovo file**: `frontend/src/lib/components/fx/FxDataEditorSection.svelte`

**Props**:
```typescript
interface Props {
    base: string;
    quote: string;
    chartData: FxDataPoint[];   // dati attuali dal TimeSeriesStore
    saving?: boolean;
    onsave?: () => void;
    oncancel?: () => void;
    /** Dirty rows emitted for chart preview (pending orange points) */
    onpendingchange?: (pendingPoints: LineDataPoint[]) => void;
}
```

### Logica

- **Al mount / cambio `chartData`**: Converte ogni `FxDataPoint` in `DataRow` con `status: 'original'`, colonna `rate` = `dataPoint.rate`. Popola il DataEditor.
- **Espone metodo `scrollToDate(date: string)`**: Il parent chiama questo quando l'utente clicca un punto nel chart in edit mode → DataEditor scrolla e seleziona la riga corrispondente (in vista tabella) o evidenzia la riga (in vista testo via `CsvEditor.scrollToLine()`).
- **Dirty tracking → chart preview**: Quando `onchange` del DataEditor emette righe dirty, converte quelle con `status: 'edited' | 'appended'` in `LineDataPoint[]` e chiama `onpendingchange` → il parent li passa come `pendingData` (punti arancioni) al chart.
- **Al Save**: Filtra righe dirty e invia al backend:
  - `'edited'` + `'appended'` → `POST /api/v1/fx/currencies/rate` (`upsert_rates_endpoint`) con `source: 'MANUAL'`
  - `'deleted'` → `DELETE /api/v1/fx/currencies/rate` (`delete_rates_endpoint`) con data singola per riga
  - Poi: invalidate TimeSeriesStore per il range visualizzato → callback `onsave` → il parent fa refresh

### Sostituisce

`FxEditSection.svelte` — che viene **cancellata** (wrapper molto semplice del CsvEditor, non più adeguata).

### Motivazione

Separa la logica API FX-specifica (endpoint, conversione dati, source MANUAL) dal DataEditor generico. Il DataEditor non sa nulla di FX.

---

## Step 5 — Fattorizzare `ChartSettingsModal` in sotto-componenti riusabili

**Stima**: 0.5 giorni

### Nuovi file (estratti dalla modale)

- **`frontend/src/lib/components/charts/ChartAestheticsSection.svelte`**
  - I 4 toggle (baseline colors, area fill, grid lines, stale gradient) + Y-axis mode (Auto/Include0/Custom con min/max)
  - Props: valori bindable per ogni toggle + callback `onchange`
  - Layout: griglia 2 colonne come nella modale attuale (stessi identici elementi HTML/CSS)

- **`frontend/src/lib/components/charts/ChartSignalsSection.svelte`**
  - I 3 dropdown categorizzati (📊 Indicators, 💱 Comparison, 📐 Benchmarks)
  - `OrderableList` dei segnali con card stile/parametri/popover (marker grid, line type, width)
  - Supporto MACD composito (side-by-side style configurators)
  - Props: `signals: SignalConfig[]` (bindable), `availablePairs`, `pairsDataMap`, callback `onchange`

### Refactor `ChartSettingsModal.svelte`

Diventa thin wrapper:
```
ModalBase
├── Header (title, close button)
├── Scrollable content
│   ├── InfoBanner (global warning, if mode=global)
│   ├── ChartAestheticsSection  ← extracted component
│   ├── Preview Chart (LineChart with synthetic/pair data)
│   └── ChartSignalsSection     ← extracted component
└── Footer (Cancel, Apply)
```

La logica di dirty detection, save, close con confirm-discard resta nella modale.
I sotto-componenti sono puri: ricevono valori, emettono cambiamenti, non gestiscono persistenza.

### Usato nella pagina detail (Step 9)

```svelte
<!-- Pannello foldable sopra il chart -->
<details open={!editMode} class="...">
    <summary>▸ Aesthetics</summary>
    <ChartAestheticsSection {colorByBaseline} {areaFill} {gridLines} {staleGradient} {yAxisMode} ... onchange={handleAestheticsChange} />
</details>

<!-- Chart -->

<!-- Pannello foldable sotto il chart -->
<details open={!editMode} class="...">
    <summary>▸ Signals & Measures</summary>
    <ChartSignalsSection {signals} ... onchange={handleSignalsChange} />
    <MeasurePanel ... />
</details>
```

Le modifiche sono **immediate** — ogni cambio chiama `setPairSettings(slug, ...)` che bumpa `_version` nel `chartSettingsStore` → il chart si aggiorna reattivamente. Non serve bottone "Apply" nella versione inline.

### Motivazione

L'utente ha richiesto esplicitamente zero duplicazione: stessi componenti, cambia solo il contenitore. Estrarre le sezioni è l'unica via per usarle sia nella modale (FX list) che inline (FX detail).

---

## Step 6 — Ricostruire `PriceChartFull` con griglia ECharts unificata

**Stima**: 1 giorno

### Problema attuale

`PriceChartFull` assembla `LineChart` + `DataZoomBar` come 2 istanze ECharts indipendenti. La sincronizzazione zoom avviene tramite `dispatchAction` bidirezionale con `suppressEmit` flag, ma con il mouse le due istanze non si sincronizzano correttamente.

### Soluzione: singola istanza ECharts con 2 grid

Ispirato dall'esempio ECharts `candlestick-sh-2015` fornito dall'utente: un singolo chart con `dataZoom` che controlla multiple grid è il modo idiomatico.

### Nuova architettura

```
Singola istanza ECharts
├── grid[0] (top, ~400px): Chart principale
│   ├── xAxis[0]: tipo 'category', date
│   ├── yAxis[0]: scala primaria (price/rate)
│   ├── yAxis[1]: scala secondaria (RSI 0-100)
│   ├── yAxis[2]: scala terziaria (MACD)
│   ├── series[]: main line(s) + overlay signals + pending edits + measures
│
├── grid[1] (bottom, ~60px): Overview mini-chart
│   ├── xAxis[1]: tipo 'category', stessi dati, nascosto
│   ├── yAxis[3]: nascosto, auto-scale
│   ├── series[]: linea principale mini + segnali con opacity 0.5, lineWidth 0.5
│
├── dataZoom[0]: tipo 'slider', ancorato a grid[1]
│   ├── xAxisIndex: [0, 1]  ← controlla ENTRAMBI
│   ├── Slider visibile nell'overview
│
├── dataZoom[1]: tipo 'inside', su grid[0]
│   ├── xAxisIndex: [0, 1]  ← controlla ENTRAMBI
│   ├── Zoom/pan con mouse wheel + drag nel chart principale
```

Il `dataZoom` condiviso sincronizza nativamente le due grid. **Zero `dispatchAction`, zero flag `suppressEmit`**.

### Nuove props per `PriceChartFull`

```typescript
interface Props {
    data: LineDataPoint[];
    pendingData?: LineDataPoint[];
    currency?: string;
    chartHeight?: string;
    overviewHeight?: string;
    initialChartType?: ChartType;
    initialViewMode?: ViewMode;
    editMode?: boolean;
    onPointClick?: (date: string, value: number) => void;
    /** Overlay signals for the main chart */
    overlaySignals?: RenderedSignal[];
    /** Chart aesthetics from settings store */
    colorByBaseline?: boolean;
    areaFill?: boolean;
    showGridLines?: boolean;
    showGradient?: boolean;
    yAxisMode?: 'auto' | 'include0' | 'custom';
    yAxisMin?: number;
    yAxisMax?: number;
    /** Measure mode: enables click-to-place measurement points */
    measureMode?: boolean;
    onMeasureClick?: (date: string, value: number) => void;
}
```

L'overview mostra **tutti** i segnali (stessa configurazione del main, con linee più sottili e opacità ridotta). Non serve distinzione `targetChart` — un singolo `dataZoom` controlla tutto.

### Componenti rimossi

- `DataZoomBar.svelte` — cancellato in Step 1, non serve come componente separato
- La logica di `zoomRange` state, `handleZoomBarChange`, `handleChartZoomChange` — tutta eliminata, il `dataZoom` ECharts gestisce tutto internamente

### Note implementative

- Il `LineChart` interno potrebbe essere refactored per accettare una configurazione multi-grid, OPPURE il rendering viene fatto direttamente in `PriceChartFull` (usa `echarts.init` direttamente). La seconda opzione è preferibile per evitare di complicare `LineChart` (che resta usabile stand-alone per card compatte).
- Il `ChartToolbar` resta invariato (Line/Candlestick toggle + Abs/%).
- `PriceChartCompact` continua a usare `LineChart` direttamente (nessun overview).

---

## Step 7 — Sistema Measure come segnali overlay

**Stima**: 1 giorno

### 7A — `MeasureSignal.ts`

**Nuovo file**: `frontend/src/lib/charts/signals/MeasureSignal.ts`

```typescript
export class MeasureSignal extends ChartSignal {
    static signalType = 'measure';
    static displayName = 'Measure';
    static icon = '📏';
    static category = 'measure' as const;  // nuova categoria, non nei dropdown
    static yAxisIndex = 0;
    static paramDescriptors: SignalParamDescriptor[] = [
        { key: 'startDate', label: 'Start', type: 'string', default: '' },
        { key: 'endDate', label: 'End', type: 'string', default: '' },
    ];

    computePoints(baseData: LineDataPoint[]): LineDataPoint[] {
        // Restituisce solo 2 punti: lookup dei valori nelle date start/end
        const start = baseData.find(d => d.date === this.params.startDate);
        const end = baseData.find(d => d.date === this.params.endDate);
        if (!start || !end) return [];
        return [
            { date: start.date, value: start.value },
            { date: end.date, value: end.value },
        ];
    }

    getLabel(): string {
        return `📏 ${this.params.startDate} → ${this.params.endDate}`;
    }

    /** Computed measurement values */
    getMeasurement(baseData: LineDataPoint[]): MeasurementResult | null { ... }
}

interface MeasurementResult {
    startDate: string;
    endDate: string;
    startValue: number;
    endValue: number;
    deltaAbs: number;
    deltaPct: number;
    days: number;
    annualizedPct: number;
}
```

Default style: `markerStart: 'pin'`, `markerEnd: 'arrow'`, `lineType: 'solid'`, `lineWidth: 2`.

**Non registrato** nel registry globale (`SIGNAL_REGISTRY`) — non appare nei dropdown "Add signal". Gestito esclusivamente dal `MeasurePanel`.

### 7B — `MeasurePanel.svelte`

**Nuovo file**: `frontend/src/lib/components/charts/MeasurePanel.svelte`

All'interno del pannello "Signals & Measures" (sotto `ChartSignalsSection`):

**Props**:
```typescript
interface Props {
    /** Base chart data for value lookups */
    chartData: LineDataPoint[];
    /** Overlay signals currently shown (for riepilogo table) */
    overlaySignals: RenderedSignal[];
    /** Emits rendered measure signals to be added to chart overlay */
    onmeasureschange?: (measures: RenderedSignal[]) => void;
    /** Emits when measure mode should be toggled */
    onmeasuremodechange?: (active: boolean) => void;
    /** View mode for correct value formatting */
    viewMode?: 'absolute' | 'percentage';
}
```

**Funzionalità**:

1. **Bottone "📏 Add Measure"**: Attiva `measureMode` su `PriceChartFull` via callback. In measure mode, il cursore sul chart diventa crosshair.
   - 1° click sul chart → registra `startDate` + `startValue` (pin marker appare)
   - 2° click → registra `endDate` + `endValue`, crea `MeasureSignal`, aggiunge alla lista `measures[]`, disattiva measure mode

2. **Lista misure**: `OrderableList` riordinabile con bottone rimuovi per ciascuna. Ogni riga mostra: `📏 YYYY-MM-DD → YYYY-MM-DD · Δ+0.45% · 30d`

3. **Tabella riepilogo** (sotto la lista, visibile quando ≥1 misura):
   Per ogni misura attiva, tabella con una riga per ciascun segnale visibile nel chart:

   | Signal | Value @ Start | Value @ End | Δ Abs | Δ % | Days | Δ%/Year |
   |--------|---------------|-------------|-------|-----|------|---------|
   | Main (EUR/USD) | 1.0823 | 1.0912 | +0.0089 | +0.82% | 30 | +9.98% |
   | EMA(20) | 1.0801 | 1.0887 | +0.0086 | +0.80% | 30 | +9.73% |
   | ... | ... | ... | ... | ... | ... | ... |

   I valori dei segnali vengono interpolati/lookupati alle date start/end della misura.

4. **Comportamento in edit mode**: Il pannello si folda automaticamente (come gli altri pannelli).

5. **Ricalcolo**: Modifica/salvataggio dati → ricalcolo immediato di tutti i derivati (segnali + misure). Cancel e Save fanno entrambi refresh dei dati backend → ricalcolo.

### 7C — Integrazione

Le `MeasureSignal` renderizzate vengono aggiunte all'array `overlaySignals` passato a `PriceChartFull`. Il `LineChart` le renderizza come qualsiasi altro segnale overlay (retta con `markerStart: 'pin'` e `markerEnd: 'arrow'` — supporto già presente in `LineChart` via `markPoint`).

### Motivazione

Riusa l'intera infrastruttura segnali esistente (renderizzazione, stile, marker). Nessun overlay SVG/CSS disallineato. La tabella riepilogo è la feature chiave che l'utente ha richiesto — confronta i valori di TUTTI i segnali tra due date.

---

## Step 8 — Provider config: `FxPairAddModal` in modalità edit

**Stima**: 3h
**File**: `frontend/src/lib/components/fx/FxPairAddModal.svelte`

### Nuove props

```typescript
interface Props {
    // ...existing props...
    /** Edit mode: currencies are readonly and pre-populated */
    editMode?: boolean;
    /** Pre-populated base currency (edit mode) */
    initialBase?: string;
    /** Pre-populated quote currency (edit mode) */
    initialQuote?: string;
}
```

### Comportamento `editMode === true`

- `CurrencySearchSelect` per base e quote: **disabilitate** e pre-valorizzate con `initialBase`/`initialQuote`
- Titolo modale: "Edit Provider Configuration" (i18n: `fx.editProviders.title`)
- Carica automaticamente i provider routes correnti per la coppia e li pre-popola nella `FxProviderSelect` + `OrderableList`
- Bottone salva: "Save" (non "Create")
- Logica salvataggio: aggiorna solo i routes (POST upsert + DELETE stale via `applyProviderDiff` — stessa logica già presente nella pagina detail, migrata nella modale)
- Non crea la coppia (già esiste), non fa sync

### Pagina detail

- **Rimuovere**: blocco `<FxProviderConfig>`, import `FxProviderConfig`, funzioni `handleAddProvider`, `handleRemoveProvider`, `handleSaveProviderOrder`, `applyProviderDiff`, variabili `providers`, `availableProviders`, funzioni `loadProviders`, `loadAvailableProviders`
- **Aggiungere**: Bottone "⚙ Providers" nella filter bar che apre `FxPairAddModal` in `editMode`
- **Accanto**: Bottone "Sync" con stessa logica e toast della pagina FX list (`handleSyncPair`)

### Motivazione

`FxPairAddModal` ha già tutta la logica: `FxProviderSelect`, `OrderableList`, chain DFS, info banners, save. Aggiungere `editMode` è ~30 righe vs duplicare ~400 righe di provider config.

---

## Step 9 — Redesign layout pagina FX Detail + wiring completo

**Stima**: 0.5 giorni
**File**: `frontend/src/routes/(app)/fx/[pair]/+page.svelte`

### Layout finale

```
┌─ Header: ← Back to FX List ──────────────────────────────────────┐
└────────────────────────────────────────────────────────────────────┘
┌─ Filter Bar (responsive 3 colonne, come FX list) ────────────────┐
│ Col 1: [DateRangePicker]                                          │
│ Col 2: [🇪🇺 EUR → 🇺🇸 USD · 1.0823 · ▲+0.45% · 2026-03-15]     │
│ Col 3: [Abs/% | ⚙Providers | Sync | Refresh] + [Edit toggle]    │
└───────────────────────────────────────────────────────────────────┘
▸ Aesthetics  (foldable <details>, auto-fold in edit mode)
  └─ ChartAestheticsSection (toggle immediati via setPairSettings)
┌─ Chart ──────────────────────────────────────────────────────────┐
│  grid[0]: Main chart + segnali overlay + misure + pending edits  │
│  grid[1]: Overview + dataZoom slider (nativo, sync perfetto)     │
└──────────────────────────────────────────────────────────────────┘
▸ Signals & Measures  (foldable <details>, auto-fold in edit mode)
  ├─ ChartSignalsSection (segnali overlay riordinabili)
  └─ MeasurePanel (misure + tabella riepilogo)
┌─ Data Editor (visibile SOLO in edit mode) ───────────────────────┐
│  [CSV | Table] [Import CSV] [Add Row]    [Save (N) | Cancel]     │
│  ... FxDataEditorSection → DataEditor ...                         │
└──────────────────────────────────────────────────────────────────┘
```

### Filter bar — 3 colonne

Stessa struttura `filterBarRef` + `ResizeObserver` con 3 layout mode (`wide`, `tablet`, `mobile`) dalla pagina FX list:
- **Col 1** (sinistra): `DateRangePicker` (identico a FX list)
- **Col 2** (centro, opzione A confermata): Pair info compatto — bandiere con `currencyFlag()`, codici valuta, rate attuale (`lastRate.toFixed(4}`), Δ% con icona trend, data ultimo rate. Spostato dall'header attuale.
- **Col 3** (destra): Griglia azioni 2×2 (stessa struttura FX list):
  - Abs/% toggle (segmented button)
  - ⚙ Providers (apre `FxPairAddModal` in `editMode`)
  - Sync (singola coppia, con toast)
  - Refresh (invalida cache + reload)
  - Edit toggle (bottone separato sotto o nella riga, diventa amber in edit mode)

L'header si riduce a solo `← Back to FX List` + titolo minimale (o nessun titolo, il pair info è nel filter bar).

### Pannelli foldabili

Implementati con `<details>` / `<summary>` HTML nativi + styling Tailwind:
- Stato `open` controllato da variabile `$state` collegata a `editMode`
- Quando `editMode = true` → `open = false` su entrambi i pannelli
- Quando `editMode = false` → ripristina stato precedente
- Transizione CSS con `transition-all` per apertura/chiusura smooth

### Wiring reattivo

```
chartSettingsStore.getSettingsForPair(slug)
    ↓
┌───────────────────────────────┐
│ ChartAestheticsSection props  │ ← toggle immediati → setPairSettings()
│ ChartSignalsSection signals   │ ← add/remove/reorder → setPairSettings()
└───────────────────────────────┘
    ↓ (reactive via _version)
┌───────────────────────────────┐
│ PriceChartFull                │
│   overlaySignals = getRenderedSignals(slug, data, viewMode) + measureSignals
│   colorByBaseline, areaFill, showGridLines, showGradient, yAxisMode...
│   pendingData = FxDataEditorSection dirty points (orange diamonds)
│   onPointClick (edit mode) → FxDataEditorSection.scrollToDate(date)
│   onMeasureClick (measure mode) → MeasurePanel.addPoint(date, value)
└───────────────────────────────┘
    ↓
┌───────────────────────────────┐
│ MeasurePanel                  │
│   measures[] → rendered as overlaySignals
│   riepilogo table: all signals × all measures
│   Ricalcolo automatico su data change
└───────────────────────────────┘
    ↓
┌───────────────────────────────┐
│ FxDataEditorSection           │
│   rows = chartData → DataRow[]
│   dirty rows → pendingData (orange) on chart
│   Save → POST upsert + DELETE → invalidate store → refresh chart
│   Cancel → clear edits → restore chart
│   Click su punto chart → scrollToDate()
└───────────────────────────────┘
```

### Refresh e ricalcolo

- **Save**: Invia dirty rows al backend → invalidate TimeSeriesStore → reload chart data → segnali e misure ricalcolati reattivamente
- **Cancel**: Clear edits → pendingData svuotato → chart torna allo stato originale
- **Sync**: Chiama API sync → invalidate store → refresh → ricalcolo segnali e misure
- **Refresh**: Invalidate cache range → re-fetch dal backend → ricalcolo

---

## Step 10 — i18n, cleanup finale, test

**Stima**: 0.5 giorni

### i18n

Aggiungere chiavi via `./dev.py i18n add` (EN/IT/FR/ES):
- DataEditor: `dataEditor.viewText`, `dataEditor.viewTable`, `dataEditor.importCsv`, `dataEditor.addRow`, `dataEditor.goToDate`, `dataEditor.markDeleted`, `dataEditor.status.original`, `dataEditor.status.edited`, `dataEditor.status.deleted`, `dataEditor.status.appended`, `dataEditor.gapDays`, `dataEditor.duplicateDateError`, `dataEditor.fixDuplicates`, `dataEditor.modified`, `dataEditor.importTitle`, `dataEditor.importDesc`, `dataEditor.dropFile`
- MeasurePanel: `measure.title`, `measure.add`, `measure.remove`, `measure.table.signal`, `measure.table.valueStart`, `measure.table.valueEnd`, `measure.table.deltaAbs`, `measure.table.deltaPct`, `measure.table.days`, `measure.table.annualized`
- Pannelli: `fxDetail.aesthetics`, `fxDetail.signalsAndMeasures`
- Provider edit: `fx.editProviders.title`, `fx.editProviders.save`

### File da cancellare

| File | Sostituito da |
|------|---------------|
| `DataZoomBar.svelte` | Griglia unificata in `PriceChartFull` |
| `MeasureOverlay.svelte` | `MeasureSignal` + `MeasurePanel` |
| `EditPopup.svelte` | `DataEditor` (edit in tabella) |
| `FxEditSection.svelte` | `FxDataEditorSection` |

### Aggiornare index.ts

- **`frontend/src/lib/components/charts/index.ts`**: Rimuovere export cancellati. Aggiungere: `ChartAestheticsSection`, `ChartSignalsSection`, `MeasurePanel`.
- **`frontend/src/lib/components/fx/index.ts`**: Rimuovere `FxEditSection`. Aggiungere `FxDataEditorSection`.

### Cleanup riferimenti

- `LineChart.svelte`: Rimuovere prop `onChartReady`, interfaccia `ChartApi`, commenti MeasureOverlay
- `PriceChartFull.svelte`: Già pulito in Step 1 + ricostruito in Step 6

### Test E2E

- Navigazione `/fx/[pair]`
- Pannelli fold/unfold (Aesthetics, Signals & Measures)
- Auto-fold pannelli in edit mode
- Edit mode: switch text/table, validazione, date duplicate
- Import CSV (drag & drop, copia-incolla)
- Row folding (espandi gap, inserisci valore)
- Selezione multipla + mark as deleted
- Save (verifica API call con solo dirty rows)
- Cancel (verifica ripristino)
- Measure: piazzamento (2 click), tabella riepilogo, rimozione
- Measure multipli ordinabili
- Sync singola coppia (con toast)
- Provider edit (FxPairAddModal in editMode)
- Refresh (invalidate + reload)
- Abs/% toggle
- `./dev.py front check` + `./dev.py front build` verdi

---

## Decisioni confermate

| Domanda | Decisione |
|---------|-----------|
| Candlestick/VolumeBar per FX? | No — deprecati per Phase 6 (Assets) |
| DataZoomBar come componente separato? | Cancellato — overview integrata nel chart unificato |
| `targetChart` field per segnali? | Non necessario — griglia unificata mostra tutto |
| Drag verticale su punto chart? | Rimosso — edit solo da tabella, chart per navigare ai punti |
| Settings modale vs inline? | Inline (pannelli foldabili) per detail page, modale per FX list |
| Duplicazione codice settings? | Zero — sotto-componenti condivisi (`ChartAestheticsSection`, `ChartSignalsSection`) |
| Colonna centrale filter bar? | Opzione A: pair info compatto (bandiere, rate, Δ%, data) |
| CsvEditor: evolvere o cancellare? | Evolvere a Svelte 5 runes, riusare nel DataEditor e nella modale import |
| Row folding soglia? | Gap > 2 giorni foldato (weekend non foldato, gap ≥3 giorni sì) |
| Pulsante ⚙ nella filter bar? | ⚙ Providers → apre FxPairAddModal in editMode |
| Edit al posto di settings? | Edit toggle separato nella filter bar, settings inline nei pannelli |

