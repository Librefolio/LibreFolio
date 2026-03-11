# Plan: FX UI Refinements Round 2 — Chart Colors, Layout, MeasureOverlay, OrderableList, Overlay & Benchmark

**Data creazione**: 2 Marzo 2026
**Status**: 🔄 IN CORSO — Steps 1-7, 9 ✅ completati, Step 8 📋 TODO
**Durata stimata**: ~3-4 giorni
**Ultimo aggiornamento**: 3 Marzo 2026
**Dipendenze**: Phase 5 Step 1-5 completati, Step 6 parzialmente completato
**Riferimenti**:
- `plan-phase05Fx.prompt.md` (piano principale Phase 5)
- `plan-phase05-to-08-upgrade.md` §4
- `phases/phase-05-subplan/plan-fxCardRedesignChartSettings.prompt.md` ← ✅ COMPLETATO — card redesign, signal library base
- `phases/phase-05-subplan/plan-signalLibraryExpansion.prompt.md` ← ✅ COMPLETATO — indicatori tecnici, dual-axis, KaTeX, MkDocs
- `phases/phase-05-subplan/plan-fxCardRedesignChartSettings.prompt.md` (card redesign, chart settings, signal library)
- `plan-fxSyncApiRedesign.prompt.md` (sync API pair-based redesign)

---

## Contesto

Dopo la prima implementazione di Phase 5 (FX pages, chart library, DateRangePicker), l'utente ha fornito feedback iterativi che richiedono fix e miglioramenti in 8 aree distinte. Questo piano dettaglia ogni area con analisi del problema, soluzione tecnica, e file coinvolti.

---

## Analisi: Cache Bidirezionale — Locale vs Doppia Chiamata Backend

Il backend normalizza SEMPRE le coppie in ordine alfabetico: `base < quote`.
Il rate memorizzato nel DB è `1 base = rate × quote`.

Quando il frontend chiede la conversione inversa (es. `from: EUR, to: AUD` ma nel DB c'è `AUD-EUR`), il backend fa `meta["direct"] = False` e calcola `amount / rate` (riga 835 di `backend/app/services/fx.py`).

| Approccio | Latenza | Traffico rete | Calcolo backend | Consistenza |
|-----------|---------|---------------|-----------------|-------------|
| **Locale `1/rate`** | ~0ms | 0 bytes | 0 | ✅ Identico (stessa aritmetica) |
| **Doppia chiamata** | +50-200ms RTT | ×2 payload | ×2 query DB (stesse righe) | ✅ Identico |

**Conclusione**: calcolo locale `1/rate` è la scelta corretta. Il backend fa esattamente lo stesso calcolo (`amount / rate` per la direzione inversa). Zero vantaggi nella doppia chiamata, solo overhead inutile.

**Implementazione**: `fxStoreRegistry` mantiene 1 sola istanza `TimeSeriesStore<FxDataPoint>` per coppia (in ordine canonico alfabetico). Quando l'utente inverte la visualizzazione (swap ⇄), il frontend calcola `1/rate` localmente per ogni punto. La cache è una sola, condivisa tra entrambe le direzioni.

---

## Step 1: Fix LineChart `visualMap` — Passare Dati come Tuple `[index, value]`

**Status**: ✅ COMPLETATO

### Problema

I dati sono passati come array piatto `data: values` (es. `[0.56, 0.57, ...]`), ma il `visualMap` piecewise con `dimension: 1` richiede che i dati abbiano 2 dimensioni. Con un array piatto esiste solo dimension 0 (il valore stesso), quindi il `visualMap` non ha nessuna dimensione 1 su cui discriminare → il colore non cambia mai (sempre verde).

### Root Cause (LineChart.svelte righe 203, 350-362)

```javascript
// Riga 203: dati come array piatto — PROBLEMA
const values = data.map(d => d.value);
mainSeries.data = values; // [0.56, 0.57, ...] → solo dimension 0

// Righe 350-362: visualMap su dimension 1 — NON FUNZIONA
visualMap: {
    dimension: 1,  // ← Non esiste! Array piatto ha solo dim 0
    pieces: [
        {lt: 0, color: redColor},   // mai matchato
        {gte: 0, color: greenColor}, // sempre matchato
    ],
}
```

### Soluzione

Quando `visualMap` è attivo, passare i dati come array di tuple:

```javascript
// Quando visualMap attivo (% mode o abs con baseline color):
mainSeries.data = values.map((v, i) => [i, v]);
// → [[0, 0.56], [1, 0.57], ...] → dimension 0 = index, dimension 1 = value

// Quando visualMap NON attivo (abs mode senza baseline):
mainSeries.data = values;
// → [0.56, 0.57, ...] → più efficiente, nessun overhead
```

Aggiungere anche colorazione baseline in modalità **assoluta** (controllata da prop `colorByBaseline`):

```javascript
if (colorByBaseline && !compact) {
    const baselineValue = isPercentage ? 0 : data[0]?.value ?? 0;
    option.visualMap = {
        show: false,
        seriesIndex: 0,
        type: 'piecewise',
        dimension: 1,
        pieces: [
            {lt: baselineValue, color: redColor},
            {gte: baselineValue, color: greenColor},
        ],
    };
    // markLine tratteggiata al baseline
    mainSeries.markLine = {
        silent: true, symbol: 'none',
        lineStyle: {color: isDark ? '#64748b' : '#9ca3af', type: 'dashed', width: 1},
        data: [{yAxis: baselineValue}],
        label: {show: false},
    };
}
```

### File

- `frontend/src/lib/components/charts/LineChart.svelte` — ✅ Dati ora in formato tuple `[index, value]` quando `useBaselineColoring=true`. `visualMap` dimension:1 funziona. Baseline coloring in abs mode aggiunto.

### Nuovi Props LineChart

```typescript
/** Enable baseline coloring (red below baseline, green above) */
colorByBaseline?: boolean; // default: true
/** Show area fill gradient under the line */
areaFill?: boolean; // already exists
/** Show grid split lines */
showGridLines?: boolean; // new, default: true
```

---

## Step 2: Fix Stale Data Gradient — Opacità Linea e Puntini

**Status**: ✅ COMPLETATO

### Problema

Il tooltip indica correttamente `staleDays` (es. "⚠ Stale: 3 day(s) old"), ma:
1. La **linea** non sbiadisce → il `visualMap` piecewise per gradient usa `opacity` nei pieces, ma ECharts NON applica l'opacità ai segmenti di linea tramite piecewise visualMap (solo il colore viene applicato)
2. I **puntini** (`symbol`) non cambiano opacità

### Root Cause (LineChart.svelte righe 363-381)

```javascript
// Il visualMap stale usa dimension 0 (index) e sets opacity per piece
// MA: ECharts ignora 'opacity' nelle pieces per le line series
pieces.push({
    gt: i, lte: i + 1,
    color: baseColor,
    opacity: opacity,  // ← IGNORATO da ECharts per line type
});
```

### Soluzione

Usare il formato dati per-punto con `itemStyle` e `lineStyle` individuali:

```javascript
// Invece di array piatto, usare oggetti per-punto:
mainSeries.data = data.map((d, i) => {
    const opacity = getOpacity(d.staleDays);
    return {
        value: usesTupleFormat ? [i, d.value] : d.value,
        // Punto (symbol) con opacità
        itemStyle: {
            color: hexToRgba(baseColor, opacity),
            borderColor: hexToRgba(baseColor, opacity),
        },
        // Segmento di linea che PARTE da questo punto
        lineStyle: {
            color: hexToRgba(baseColor, opacity),
        },
    };
});
```

**Interazione con visualMap**: quando il `visualMap` per baseline color è attivo, esso sovrascrive i colori. In quel caso, lo stale gradient deve essere disabilitato (il baseline color ha priorità). L'utente può scegliere via ⚙️ settings. Il prop `showGradient` diventa il toggle:
- `showGradient=true && colorByBaseline=false` → stale gradient attivo
- `colorByBaseline=true` → stale gradient disabilitato (il baseline color sovrascrive)

### File

- `frontend/src/lib/components/charts/LineChart.svelte` — ✅ Per-point opacity tramite `itemStyle.color` e `lineStyle.color` con `hexToRgba(baseColor, opacity)`. Interazione: stale gradient disabilitato quando baseline coloring è attivo.

---

## Step 3: Unificare DateRangePicker — Singola Istanza con Presets + Calendario

**Status**: ✅ COMPLETATO

### Problema

La pagina FX list usa **2 istanze separate** di `DateRangePicker`:
1. Riga 362-368: `showDateFields={false}` → mostra SOLO presets (1W, 1M, 1Y, Custom)
2. Riga 394-402: `showPresets={false}, showCustomWindow={false}` → mostra SOLO calendario From/To

Questo causa:
- Presets e calendario visivamente separati (non uno sopra l'altro)
- Due componenti che bindano le stesse variabili (`dateStart`, `dateEnd`, `activePreset`)

### Soluzione

Eliminare le 2 istanze e usare **un singolo `<DateRangePicker>`** con tutti i props a default (che mostra presets su riga 1 e calendario su riga 2 internamente).

Nello stesso filter bar: spostare Sync All, Refresh All, Add Pair dal header alla filter bar, e aggiungere toggle Abs/% globale.

### Layout Target (Filter Bar)

```
┌─ Filter Bar ─────────────────────────────────────────────────────────┐
│ Row 1: [1W] [1M] [1Y] [Custom·3·months]                             │
│ Row 2: [📅 FROM Dec 02 | TO Mar 02] [💱 Cur1 ▾] [💱 Cur2 ▾]        │
│         [Abs|%]  [⟳ Sync] [↻ Refresh] [+ Add]                       │
└──────────────────────────────────────────────────────────────────────┘
```

- Singolo `DateRangePicker` con `compact={true}` che mostra presets + calendario
- Filtri valuta a fianco del calendario (stessa riga 2)
- Toggle Abs/% come slider button
- Bottoni azione: testo con `<span class="hidden sm:inline">label</span>`, icona sempre visibile
- Su mobile: tutto si impila verticalmente, bottoni solo icona

### Header Semplificato

Solo titolo + sottotitolo, senza bottoni (spostati nella filter bar).

### File

- `frontend/src/routes/(app)/fx/+page.svelte` — righe 326-410 (header + filter bar → unificare)

---

## Step 4: Custom Badge — Effetto Immediato, Niente ✓/✕

**Status**: ✅ COMPLETATO

### Problema

Il badge "Custom" nel DateRangePicker, quando cliccato, mostra un input con amount + granularity + pulsanti ✓ (conferma) e ✕ (annulla). L'utente vuole che i cambi abbiano effetto immediato (senza conferma) e che il badge si chiuda cliccando fuori.

### Soluzione

In `DateRangePicker.svelte`:
1. Rimuovere i pulsanti ✓ e ✕ dal blocco `customEditing`
2. Aggiungere un `$effect` reattivo:
   ```javascript
   $effect(() => {
       if (customEditing && customAmount > 0) {
           applyCustomWindow(); // calcola e applica subito la nuova start date
       }
   });
   ```
3. Il badge si chiude quando:
   - Si clicca su un altro preset (1W, 1M, 1Y) → `customEditing = false`
   - Si clicca fuori dal badge → estendere `handleClickOutside` per gestire anche il custom popover

### File

- `frontend/src/lib/components/ui/DateRangePicker.svelte` — sezione customEditing (righe ~410-430)

---

## Step 5: MeasureOverlay — Rimuovere Toggle, Fix Y, Info Hover

**Status**: ✅ COMPLETATO

### Problema

1. C'è ancora il pulsante "Measure" nella ChartToolbar → l'utente vuole che il measure sia **SEMPRE attivo** (3-click cycle senza bisogno di attivazione)
2. La Y della freccia non segue i dati — usa stime statiche per il grid (`left: 60, top: 35, ...`) che sono imprecise, soprattutto con `containLabel: true` dove ECharts aggiusta i margini
3. In attesa del 1° click, l'utente vuole vedere le info del punto sotto il cursore (il tooltip ECharts standard)

### Soluzione

**5a. Rimuovere pulsante toggle** da ChartToolbar:
- Eliminare il blocco `<!-- Measure Mode Toggle -->` (righe 89-100)
- Rimuovere prop `measureMode` e callback `onMeasureModeChange` dall'interfaccia

**5b. PriceChartFull — measure sempre attivo**:
- Rimuovere la variabile `measureMode` e `handleMeasureModeChange`
- Passare `enabled={true}` sempre a `MeasureOverlay`
- Ottenere le coordinate grid reali: far esporre da LineChart una funzione `getGridBounds()` che accede a `chartInstance` internamente e ritorna le coordinate reali

**5c. LineChart — esporre grid bounds**:
Aggiungere un nuovo prop/callback `onChartReady`:
```javascript
// In LineChart, dopo setOption:
export let onChartReady?: (info: {
    getGridBounds: () => {left: number, right: number, top: number, bottom: number, width: number, height: number},
    dataToPixel: (dataIndex: number, value: number) => {x: number, y: number},
}) => void;

// Dopo renderChart():
onChartReady?.({
    getGridBounds: () => {
        const grid = chartInstance.getModel().getComponent('grid', 0);
        const rect = grid.coordinateSystem.getRect();
        return rect;
    },
    dataToPixel: (dataIndex, value) => {
        const coord = chartInstance.convertToPixel('grid', [dataIndex, value]);
        return {x: coord[0], y: coord[1]};
    },
});
```

**5d. MeasureOverlay — usare coordinate pixel reali**:
Ricevere da PriceChartFull una funzione `dataToPixel(index, value) → {x, y}` e usarla per posizionare la freccia e i pallini alle coordinate corrette. Convertire le coordinate pixel in percentuali relative al container.

**5e. Info hover in attesa click**:
Quando `startIndex === null` (attesa 1° click), NON bloccare gli eventi del mouse → il tooltip ECharts nativo mostra le info del punto. L'overlay intercetta solo il click. Modificare il div dell'overlay per usare `pointer-events: none` quando in attesa del 1° click, e `pointer-events: auto` solo quando c'è un `startIndex` (in fase di drawing o visualizzazione risultato).

### File

- `frontend/src/lib/components/charts/ChartToolbar.svelte` — ✅ Rimosso measure toggle button e props
- `frontend/src/lib/components/charts/PriceChartFull.svelte` — ✅ Measure sempre enabled, usa `ChartApi` via `onChartReady`
- `frontend/src/lib/components/charts/LineChart.svelte` — ✅ Espone `onChartReady` con `getGridBounds` + `dataToPixel` via `chartInstance.convertToPixel`
- `frontend/src/lib/components/charts/MeasureOverlay.svelte` — ✅ Usa `chartApi.dataToPixel()` per coordinate reali, `pointer-events: none` in fase waiting
- `frontend/src/lib/components/charts/index.ts` — ✅ Esportato `ChartApi` type, rimosso `RangePreset`

---

## Step 6: OrderableList + FxProviderConfig Save

**Status**: ✅ COMPLETATO

### Problema

I provider FX possono essere aggiunti e rimossi, ma NON riordinati. Il drag handle (GripVertical) è puramente visuale. Inoltre non c'è un pulsante "Save" per salvare le modifiche all'ordine.

### Soluzione

#### 6a. Creare `OrderableList.svelte`

Nuovo componente riusabile in `src/lib/components/ui/OrderableList.svelte`, estraendo il pattern drag da `DataTableToolbar.svelte` (righe 53-109):

```svelte
<script lang="ts">
    interface Props<T> {
        /** Items to display in orderable list */
        items: T[];
        /** Function to extract unique key from item */
        keyFn: (item: T) => string;
        /** Called when items are reordered */
        onReorder: (newItems: T[]) => void;
        /** Snippet to render each item */
        children: Snippet<[{ item: T; index: number }]>;
    }
</script>
```

Features:
- **Desktop**: HTML5 Drag API (`draggable="true"`, `ondragstart`, `ondragover`, `ondrop`, `ondragend`)
- **Mobile** (breakpoint `md`): frecce ↑↓ con `moveUp(index)` e `moveDown(index)`
- **GripVertical** handle (class `.drag-handle`)
- **Visual feedback**: bordo sinistro verde durante drag-over (stile `drag-over` da DataTableToolbar)
- **Accessibilità**: `role="button"`, `tabindex="0"`, keyboard handlers

#### 6b. Aggiornare FxProviderConfig

In `FxProviderConfig.svelte`:
1. Sostituire il loop `{#each providers as prov, i}` con `<OrderableList items={providers} keyFn={p => p.providerCode} onReorder={handleReorder}>`
2. Aggiungere stato `hasChanges` che diventa `true` quando l'ordine cambia
3. Aggiungere pulsante "Save Order" (visibile solo quando `hasChanges=true`)
4. `handleReorder` aggiorna le priorità localmente (priority = index + 1)
5. Il dispatch `save` invia le providers con le nuove priorità

#### 6c. FX Detail Page — gestire il save

Nel parent `fx/[pair]/+page.svelte`:
- Ascoltare l'evento `save` da `FxProviderConfig`
- Chiamare `POST /api/v1/fx/providers/pair-sources` con le nuove priorità
- Mostrare feedback success/error

### File

- `frontend/src/lib/components/ui/OrderableList.svelte` — NUOVO
- `frontend/src/lib/components/fx/FxProviderConfig.svelte` — usare OrderableList + pulsante Save
- `frontend/src/routes/(app)/fx/[pair]/+page.svelte` — handler save

### Note Future

Documentare in `TODO_FUTURI.md`: "Refactor DataTableToolbar per usare OrderableList al posto del drag inline".

---

## Step 7: Mini-Axis nelle Card FxCard

**Status**: ✅ COMPLETATO

### Problema

Le card mini (80px di altezza) non mostrano asse queY né linee di riferimento. L'utente considera l'asse Y **fondamentale** in un programma di finanza — la scala è un dato importantissimo.

### Soluzione

Aggiungere nuovo prop `showMiniAxis` a LineChart. Quando `compact=true && showMiniAxis=true`:

```javascript
yAxis: {
    type: 'value',
    show: true,
    position: 'right',       // A destra per non sovrapporre la linea
    axisLine: {show: false},  // No riga verticale
    axisTick: {show: false},
    splitNumber: 2,           // Solo 2-3 valori (min, mid, max circa)
    axisLabel: {
        show: true,
        color: isDark ? '#64748b' : '#9ca3af',
        fontSize: 9,
        formatter: (v) => v >= 1000 ? `${(v/1000).toFixed(1)}k` : v.toFixed(2),
    },
    splitLine: {
        show: true,
        lineStyle: {
            color: isDark ? '#334155' : '#e5e7eb',
            type: 'dashed',
            opacity: 0.5,
        },
    },
    scale: true,
},
grid: {
    top: 5,
    right: 40,     // Spazio per i tick labels a destra
    bottom: 5,
    left: 5,
    containLabel: false,
},
```

In `PriceChartCompact.svelte`: passare `showMiniAxis={true}` a LineChart.

### File

- `frontend/src/lib/components/charts/LineChart.svelte` — ✅ Nuovo prop `showMiniAxis`, asse Y a destra con `splitNumber: 2`, `fontSize: 9`, grid `right: 45`
- `frontend/src/lib/components/charts/PriceChartCompact.svelte` — ✅ Passa `showMiniAxis={true}` di default, `colorByBaseline` in % mode

---

## Step 8: Chart Settings ⚙️ + Overlay Confronto + Linea Crescita Sintetica

**Status**: 📋 TODO

### 8a. Settings Popover (⚙️)

Aggiungere icona ingranaggio nella ChartToolbar che apre un piccolo popover con checkbox:

- ☑ **Color by baseline** (rosso/verde rispetto al primo punto) — default ON
- ☑ **Area fill** — default ON
- ☑ **Grid lines** — default ON
- ☑ **Stale gradient** — default ON (disabilitato quando "Color by baseline" è ON)
- ☑ **Show benchmark line** — default OFF
  - Input numerico: `% annual growth` (default 0% per FX, 8% per Asset)

Il popover si chiude cliccando fuori. I valori vengono propagati via callbacks a PriceChartFull → LineChart.

### 8b. Overlay Confronto

Sia in FX list che in FX detail, deve essere possibile sovrapporre un'altra coppia FX sullo stesso grafico per confronto.

**FX Detail**: dropdown nella toolbar per aggiungere una o più coppie FX. Ogni overlay è una serie ECharts aggiuntiva con colore distinto e leggenda.

**Implementazione**:
- Nuovo prop su PriceChartFull: `overlayData?: Array<{label: string, data: LineDataPoint[], color: string}>`
- Ogni overlay diventa una serie `line` aggiuntiva in ECharts
- In modalità %, tutti gli overlay sono normalizzati allo stesso baseline (giorno 0 = 0%)
- In modalità assoluta, ogni overlay usa la sua scala (asse Y secondario opzionale se le scale sono molto diverse)

**FX List**: nelle card, per ora solo un piccolo badge/menu che permette di selezionare quale FX sovrapporre. L'overlay nell'card mini è opzionale e di priorità minore.

### 8c. Linea di Crescita Sintetica (Benchmark)

Una retta che parte dal valore del giorno 0 e cresce con un tasso annuo impostabile.

**Parametri**:
- `benchmarkRate`: tasso di crescita annuo in % (default: 0% per FX, 8% per Asset)
- `showBenchmark`: boolean (default: false, controllato da ⚙️ settings)

**Calcolo per ogni giorno**:
```
benchmarkValue = baseValue × (1 + benchmarkRate / 100) ^ (daysSinceStart / 365)
```

**Rendering ECharts**:
```javascript
{
    type: 'line',
    name: `Benchmark ${benchmarkRate}%/yr`,
    data: data.map((d, i) => {
        const daysSinceStart = (new Date(d.date) - new Date(data[0].date)) / (86400000);
        const value = baseValue * Math.pow(1 + benchmarkRate / 100, daysSinceStart / 365);
        return useTupleFormat ? [i, value] : value;
    }),
    lineStyle: {
        color: isDark ? '#64748b' : '#9ca3af',
        type: 'dashed',
        width: 1.5,
    },
    symbol: 'none',
    // NON influenzato dal visualMap:
    z: 1, // sotto la serie principale
}
```

**In modalità %**: il benchmark diventa una retta che parte da 0% e sale/scende al tasso impostato:
```
benchmarkPct = ((1 + benchmarkRate / 100) ^ (daysSinceStart / 365) - 1) × 100
```

Per le FX con default 0%, la linea è una retta orizzontale a y=0 → coincide con la markLine del baseline. In quel caso non serve mostrarla (è ridondante). Mostrare solo quando `benchmarkRate !== 0`.

**Utilità**:
- FX: mettere in evidenza se una valuta si sta deprezzando/apprezzando rispetto alla "stabilità"
- Asset: confrontare le performance con la crescita media stimata del mercato (~8%/yr)
- Nella pagina globale: mettere in scala le valute tra loro

### File

- `frontend/src/lib/components/charts/ChartToolbar.svelte` — aggiungere icona ⚙️ + popover
- `frontend/src/lib/components/charts/PriceChartFull.svelte` — passare settings a LineChart, gestire overlay e benchmark
- `frontend/src/lib/components/charts/LineChart.svelte` — ricevere props settings, renderare overlay series e benchmark line

---

## Ordine di Esecuzione e Priorità

```
Step 1 (Fix visualMap colori)     ← CRITICO, bloccante per ogni test visivo
    │
    ├──→ Step 2 (Fix stale gradient)  ← dipende da Step 1 (stesso formato dati)
    │
    └──→ Step 7 (Mini-axis card)      ← indipendente, quick win
    
Step 3 (Unificare DateRangePicker layout)  ← ALTA priorità UX
    │
    └──→ Step 4 (Custom badge immediato)   ← dipende da Step 3

Step 5 (Fix MeasureOverlay)        ← MEDIA priorità, indipendente

Step 6 (OrderableList + Save)      ← MEDIA priorità, indipendente

Step 8 (Settings + Overlay + Benchmark)  ← BASSA priorità, dopo gli altri
```

**Blocchi paralleli**:
- [1, 2, 7] possono essere fatti insieme (tutti in LineChart)
- [3, 4] sono sequenziali
- [5] è indipendente
- [6] è indipendente
- [8] va dopo 1-2 (usa gli stessi props/strutture)

---

## Riepilogo File Coinvolti

### File da Creare

| File | Descrizione |
|------|-------------|
| `frontend/src/lib/components/ui/OrderableList.svelte` | Componente riusabile drag-and-drop con frecce mobile |

### File da Modificare

| File | Steps | Modifiche |
|------|-------|-----------|
| `frontend/src/lib/components/charts/LineChart.svelte` | 1, 2, 5c, 7, 8 | Fix formato dati tuple, fix stale gradient per-punto, esporre onChartReady, mini-axis mode, props settings/overlay/benchmark |
| `frontend/src/lib/components/charts/ChartToolbar.svelte` | 5a, 8a | Rimuovere measure toggle, aggiungere ⚙️ settings popover |
| `frontend/src/lib/components/charts/PriceChartFull.svelte` | 5b, 8b, 8c | Measure sempre enabled, passare dataToPixel, gestire overlay + benchmark |
| `frontend/src/lib/components/charts/MeasureOverlay.svelte` | 5d, 5e | Usare coordinate pixel reali, pointer-events condizionale |
| `frontend/src/lib/components/charts/PriceChartCompact.svelte` | 7 | Passare `showMiniAxis={true}` |
| `frontend/src/lib/components/ui/DateRangePicker.svelte` | 4 | Rimuovere ✓/✕, effetto immediato custom |
| `frontend/src/lib/components/fx/FxProviderConfig.svelte` | 6 | Usare OrderableList, aggiungere Save Order |
| `frontend/src/routes/(app)/fx/+page.svelte` | 3 | Singolo DateRangePicker, spostare bottoni in filter bar, toggle Abs/% |
| `frontend/src/routes/(app)/fx/[pair]/+page.svelte` | 6c | Handler save provider order |

### File da Aggiornare (TODO)

| File | Contenuto |
|------|-----------|
| `TODO_FUTURI.md` | "Refactor DataTableToolbar per usare OrderableList", "Overlay confronto tra asset (Phase 6+)" |
| `plan-phase05Fx.prompt.md` | Aggiornare status Step 6, aggiungere riferimento a questo sub-plan |

---

## Nuovi Props e Interfacce

### LineChart Props (aggiornati)

```typescript
interface Props {
    // ...existing props...
    
    /** Enable baseline coloring (red below baseline, green above). Default: true */
    colorByBaseline?: boolean;
    /** Show grid split lines. Default: true */
    showGridLines?: boolean;
    /** Show mini Y-axis in compact mode (2-3 ticks, right side). Default: false */
    showMiniAxis?: boolean;
    /** Called when chart instance is ready (for coordinate mapping) */
    onChartReady?: (api: ChartApi) => void;
    /** Overlay series to render on top of main data */
    overlayData?: OverlaySeries[];
    /** Benchmark growth line */
    benchmark?: { rate: number; show: boolean };
}

interface ChartApi {
    getGridBounds: () => {left: number; right: number; top: number; bottom: number; width: number; height: number};
    dataToPixel: (dataIndex: number, value: number) => {x: number; y: number};
}

interface OverlaySeries {
    label: string;
    data: LineDataPoint[];
    color: string;
}
```

### ChartToolbar Props (aggiornati)

```typescript
interface Props {
    chartType?: ChartType;
    viewMode?: ViewMode;
    // measureMode RIMOSSO
    onChartTypeChange?: (type: ChartType) => void;
    onViewModeChange?: (mode: ViewMode) => void;
    // onMeasureModeChange RIMOSSO
    disableCandlestick?: boolean;
    // NUOVI:
    settings?: ChartSettings;
    onSettingsChange?: (settings: ChartSettings) => void;
}

interface ChartSettings {
    colorByBaseline: boolean;
    areaFill: boolean;
    gridLines: boolean;
    staleGradient: boolean;
    showBenchmark: boolean;
    benchmarkRate: number;
}
```

### OrderableList Props

```typescript
interface Props<T> {
    items: T[];
    keyFn: (item: T) => string;
    onReorder: (newItems: T[]) => void;
    disabled?: boolean;
    // Snippet per renderizzare ogni item
    children: Snippet<[{ item: T; index: number }]>;
}
```

---

## Note Implementative

### Step 9: Fix FX Global Selector — Layout 3 Colonne, Crash Custom, Presets, 404 Navigazione

**Status**: ✅ COMPLETATO (3 Marzo 2026)

**Problemi risolti**:

1. **Crash infinito su click "Custom"**: L'`$effect` in `DateRangePicker` chiamava `handleCustomApply()` che scriveva a `$bindable` props (`activePreset`, `start`, `end`), causando re-render del parent che a sua volta ri-triggerava l'`$effect`. **Fix**: tracciamento prev values con oggetto plain (non `$state`), e `queueMicrotask()` per rompere la catena sincrona.

2. **Presets insufficienti**: Il tipo `QuickPreset` aveva solo `'1W' | '1M' | '1Y'`. FX page usava `activePreset = '3M'` (non valido). **Fix**: espanso a `'1W' | '1M' | '3M' | '6M' | '1Y' | '2Y'` con relativi casi in `computeStartDate`.

3. **Layout Filter Bar**: Il `DateRangePicker` occupava il 100% della larghezza. **Fix**: layout a 3 colonne con `flex` responsive:
   - **Col 1** (`lg:max-w-[36%]`): DateRangePicker (presets + calendario) — allineata a sinistra in desktop
   - **Col 2** (valute): Currency filters fianco a fianco in desktop (`lg:flex-row`), verticali in mobile — centrata in desktop
   - **Col 3** (azioni): Abs/% toggle + ⚙ Settings + Sync All / Refresh All — grid 2×2, allineata a destra in desktop
   - In mobile: tutte e 3 le colonne si impilano verticalmente centrate

4. **"+ Add Pair" spostato nell'header**: Era nella filter bar (3ª colonna), ora è nell'header accanto al titolo (allineato a destra).

5. **404 su navigazione a FX detail**: `window.location.href` causava full page reload → perdita di sessione e 404 sulle API. **Fix**: sostituito con `goto()` (SvelteKit client-side navigation).

6. **Date iniziali non settate**: `dateStart` e `dateEnd` nella FX list page erano inizializzati vuoti (`''`), poi settati via `$:` reactive block. **Fix**: inizializzati direttamente inline (3 mesi fa → oggi), rimosso il blocco reactive.

7. **Custom badge: granularity selector con SimpleSelect**: Il `<select>` nativo OS-dependent per la granularità (days/weeks/months/years) è stato sostituito con il componente custom `SimpleSelect` esistente nel progetto. Il rendering è ora uniforme cross-platform.

8. **Calendario DateRangePicker miglioramenti**:
   - Mesi nel selettore tradotti via i18n (`datePicker.months.*`)
   - Tutti i giorni della settimana tradotti (`datePicker.weekdays.*`)
   - Giorni futuri (dopo oggi) resi grigi e non selezionabili
   - Pulsante "Today" in entrambe le colonne per navigare al mese corrente
   - Colonne indipendenti per mese/anno (non più vincolate a mesi consecutivi)
   - In mobile: le 2 colonne si impilano verticalmente (`flex-wrap`)

9. **I18n completa pagina FX**: Tutti i testi hardcoded tradotti con chiavi i18n (4 lingue EN/IT/FR/ES):
   - `fx.actions.*` — Sync All, Refresh All, Settings, Add Pair
   - `fx.empty.*` — Empty states (no pairs, no matches)
   - `fx.filter.*` — Currency filter labels
   - `common.retry` — Retry button
   - `datePicker.*` — Weekdays, months, From/To labels, Today, tooltip
   - `fx.presets.custom` — Custom preset label
   - `fx.timeWindow.*` — Granularity options (days, weeks, months, years)

10. **Bottoni azione: text visibility breakpoint `xl`**: I testi dei bottoni (Settings, Sync All, Refresh All) usano `hidden xl:inline` per apparire solo da 1280px+, evitando wrapping a larghezze desktop intermedie. Sotto 1280px mostrano solo icone. L'utente può fare fine-tuning cambiando `xl` → `lg` (1024px) o un breakpoint custom.

**Note fine-tuning**: Per regolare la soglia di visibilità del testo nei bottoni azione, modificare in `frontend/src/routes/(app)/fx/+page.svelte` le classi `hidden xl:inline` → scegliere tra `lg:inline` (1024px), `xl:inline` (1280px) o un breakpoint Tailwind custom.

**File modificati**:
- `frontend/src/lib/components/ui/DateRangePicker.svelte` — fix $effect, nuovi presets, SimpleSelect per granularity, i18n mesi/weekdays, giorni futuri grigi, pulsante Today, colonne indipendenti, mobile wrap
- `frontend/src/routes/(app)/fx/+page.svelte` — layout 3-col responsive, goto, date init, i18n completa, text visibility `xl` breakpoint
- `frontend/src/routes/(app)/fx/[pair]/+page.svelte` — activePreset comment fix
- `frontend/src/lib/i18n/locales/{en,it,fr,es}.json` — nuove chiavi datePicker.*, fx.actions.*, fx.empty.*, fx.filter.*, fx.timeWindow.*, common.retry

---
 **Interazione stale gradient ↔ baseline color**: sono mutualmente esclusivi per il colore della linea. Quando `colorByBaseline=true`, il `visualMap` piecewise controlla il colore → la stale opacity non può essere applicata sullo stesso canale. **Proposta**: quando entrambi sono attivi, il baseline color vince per il colore della linea, ma i puntini (`symbol`) mantengono l'opacità stale. Questo dà un feedback visuale misto: linea rossa/verde per la tendenza, puntini sbiaditi per la freschezza del dato.

2. **Overlay + visualMap conflict**: il `visualMap` con `seriesIndex: 0` si applica solo alla serie principale. Le overlay series non sono influenzate dal `visualMap` → mantengono il loro colore fisso. ✅ Funziona senza conflitti.

3. **Benchmark in % mode**: quando `benchmarkRate = 0%`, la linea benchmark coincide con la markLine a y=0 → ridondante. Non mostrarla in quel caso (`benchmarkRate !== 0` come condizione aggiuntiva).

4. **MeasureOverlay pointer-events trick**: fase waiting (nessun click) → `pointer-events: none` sull'overlay div → il tooltip ECharts nativo funziona normalmente. Fase drawing (dopo 1° click) → `pointer-events: auto` → intercetta mouse per posizionare il 2° punto. Fase display (dopo 2° click) → `pointer-events: auto` → intercetta il 3° click per dismiss. Questo evita conflitti tra MeasureOverlay e tooltip.

5. **Mini-axis grid right space**: con `right: 40` e `containLabel: false`, i tick labels a destra hanno ~40px. Se il numero è troppo lungo (es. "1,234.56"), potrebbe essere tagliato. Usare un formatter aggressivo: `toFixed(2)` per numeri < 1000, `1.2k` per numeri >= 1000.
