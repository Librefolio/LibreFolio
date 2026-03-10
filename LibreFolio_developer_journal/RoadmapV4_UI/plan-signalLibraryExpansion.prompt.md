# Plan: Signal Library Expansion — Indicatori Tecnici + UX Polish + Documentazione

## TL;DR

Espansione della libreria segnali con 4 nuovi indicatori tecnici (EMA, MACD, RSI, Bollinger),
refactoring del generatore dati sintetici per usare SineSignal, aggiunta offset % a tutti i sintetici,
migrazione del selettore FX Pair al componente custom con bandiere, restructuring della UI "Add Signal"
in 3 dropdown categorizzati (usando i componenti `SimpleSelect` esistenti), dual-axis Y per segnali a
scala indipendente (RSI, MACD), tooltip informativi con supporto LaTeX (KaTeX), e documentazione MkDocs
completa sulla teoria finanziaria con equivalenze signal processing / controlli automatici.

**Stato**: 🔄 IN PROGRESS — Steps 1-4K ✅, Steps 5-7 TODO
**Data creazione**: 9 Marzo 2026
**Ultimo aggiornamento**: 10 Marzo 2026 (MACD scaleNote 2 decimali, Signal Line unified popover, marker support)
**Dipendenze**: `plan-fxCardRedesignChartSettings.prompt.md` (Steps 1-6 done, signal library esiste)
**Link parent**: `plan-phase05Fx.prompt.md` (master plan Phase 5)
**Nota i18n**: Le traduzioni di Step 1 sono state aggiunte manualmente ai JSON. Per le prossime, usare `./dev.py i18n add`.

---

## Contesto

La libreria segnali in `frontend/src/lib/charts/signals/` è stata creata nel plan
`fxCardRedesignChartSettings` con 4 tipi: `FxPairSignal`, `LinearSignal`, `CompoundSignal`,
`SineSignal`. La classe base `ChartSignal` (in `ChartSignal.ts`) definisce l'interfaccia astratta
con `paramDescriptors`, `SignalStyle` (colore, spessore, lineType, markerStart, markerEnd),
`SignalConfig` (serializzabile), `RenderedSignal` (output per chart). Il registry in `registry.ts`
gestisce factory e serializzazione.

Il `ChartSettingsModal` in `frontend/src/lib/components/charts/ChartSettingsModal.svelte` renderizza
gli switch estetici (baselineColors, areaFill, gridLines, staleGradient) e l'OrderableList dei segnali,
con supporto per drag&drop, popover unificato stile/marker, e preview chart.

Il `LineChart` in `frontend/src/lib/components/charts/LineChart.svelte` accetta `overlaySignals: RenderedSignal[]`
e li renderizza come serie ECharts aggiuntive. Attualmente ha un singolo `yAxis` (oggetto), non un array.

I componenti select custom sono in `frontend/src/lib/components/ui/select/`:
- `SimpleSelect.svelte` — dropdown senza search, snippet personalizzabili, keyboard navigation
- `SearchSelect.svelte` — dropdown con fuzzy search, snippet, maxVisibleItems
- `CurrencySearchSelect.svelte` — specializzato per valute con bandiere + filtri
- `BaseDropdown.svelte`, `BrokerSearchSelect.svelte`, `FxProviderSelect.svelte`, `ImportPluginSelect.svelte`

Il `Tooltip.svelte` in `frontend/src/lib/components/ui/Tooltip.svelte` accetta solo `text: string`
e renderizza come testo puro. Non supporta HTML o LaTeX.

MkDocs ha MathJax configurato (`mkdocs_src/docs/javascripts/mathjax.js`). Il frontend non ha
KaTeX né MathJax installato.

---

## Step 1 — ✅ Refactoring base e fix immediati (Completato 9 Mar)

Nessuna dipendenza esterna. Correzioni alla libreria segnali esistente.

### 1A. `generateSyntheticData()` deve usare `SineSignal`

In `ChartSettingsModal.svelte`, la funzione `generateSyntheticData()` (riga ~250) genera manualmente
una sinusoide. Deve invece:
- Creare un'istanza temporanea di `SineSignal` con ampiezza **±20%** (non 10%, per entrare nei
  negativi e testare baseline colors), periodo 120gg, offset 0%
- Generare le date (365 giorni) come array di `LineDataPoint` con valore costante 1.0
- Chiamare `sineInstance.computePoints(baseDates)` per ottenere i dati sintetici
- Questo garantisce che se `SineSignal` viene aggiornato, anche il demo si aggiorna

### 1B. Aggiungere parametro `offset` (%) a `LinearSignal` e `CompoundSignal`

Come già ha `SineSignal`. Sposta verticalmente il segnale:
- `LinearSignal`: formula diventa `y = y0 × (1 + offset/100 + rate × t)`
- `CompoundSignal`: formula diventa `y = y0 × (1 + offset/100) × (1 + rate)^t`
  (calcolo iterativo: ogni punto moltiplica il precedente per il daily rate)
- Aggiungere nei `paramDescriptors`:
  `{ key: 'offset', label: 'Offset', type: 'number', default: 0, min: -100, max: 100, step: 0.5, suffix: '%' }`

### 1C. Migrare selettore FX Pair al componente custom con bandiere

Il `<select>` nativo per `FxPairSignal.pairSlug` nel `ChartSettingsModal` (riga ~510, blocco
`{:else if desc.type === 'select'}`) va sostituito con un `SimpleSelect` dal progetto
(`frontend/src/lib/components/ui/select/SimpleSelect.svelte`). Le opzioni devono mostrare
bandiere emoji + codice coppia (es. "🇪🇺 EUR → 🇬🇧 GBP") usando il snippet `item` del
`SimpleSelect`. Aggiungere pulsante `[⇄]` accanto al selettore per invertire la coppia.
In `mode === 'pair'`, iniettare `_resolvedData` dalla coppia corrente per far comparire il
segnale FX nel preview.

Per discriminare il rendering speciale del selettore FX vs un select generico, il
`ChartSettingsModal` può controllare `desc.dynamicOptionsKey === 'configuredFxPairs'` e
renderizzare un `SimpleSelect` personalizzato al posto del `<select>` nativo.

### 1D. Grid lines più contrastate

In `LineChart.svelte`, `splitLine.lineStyle.color` (riga ~527):
- Light mode: da `#e5e7eb` → `#d1d5db` (gray-300)
- Dark mode: da `#334155` → `#4b5563` (gray-600)

### 1E. Nomi segnali e parametri tradotti (i18n)

Aggiungere sezione `signals` nei 4 file JSON i18n (`en.json`, `it.json`, `fr.json`, `es.json`):
```json
"signals": {
  "linear": "Linear Growth",
  "compound": "Compound Growth",
  "sine": "Sine Wave",
  "fxPair": "FX Pair",
  "ema": "EMA",
  "macd": "MACD",
  "rsi": "RSI",
  "bollinger": "Bollinger Bands",
  "params": {
    "annualRate": "Annual Rate",
    "amplitude": "Amplitude",
    "period": "Period",
    "offset": "Offset",
    "currencyPair": "Currency Pair",
    "fastPeriod": "Fast Period",
    "slowPeriod": "Slow Period",
    "signalPeriod": "Signal Period",
    "component": "Component",
    "multiplier": "Multiplier",
    "overbought": "Overbought",
    "oversold": "Oversold"
  },
  "categories": {
    "indicator": "Technical Indicators",
    "comparison": "Data Comparison",
    "benchmark": "Synthetic Benchmarks"
  }
}
```

Nel `ChartSettingsModal`, sostituire `st.displayName` con `$t('signals.' + st.type)` (con fallback
su displayName per robustezza). Per i parametri, `desc.label` diventa chiave i18n:
`$t('signals.params.' + desc.key)` con fallback su `desc.label`.

**File coinvolti Step 1:**
- `frontend/src/lib/components/charts/ChartSettingsModal.svelte`
- `frontend/src/lib/charts/signals/LinearSignal.ts`
- `frontend/src/lib/charts/signals/CompoundSignal.ts`
- `frontend/src/lib/components/charts/LineChart.svelte`
- `frontend/src/lib/i18n/en.json`, `it.json`, `fr.json`, `es.json`

---

## Step 2 — ✅ Nuovi segnali tecnici (Completato 9 Mar)

Tutti i calcoli restano nel frontend perché operano sui dati già scaricati dal backend.
I segnali tecnici ricevono `baseData: LineDataPoint[]` e calcolano iterativamente.

**File creati:**
- `EmaSignal.ts` — EMA (IIR Low-Pass, α = 2/(N+1)), yAxisIndex=0
- `MacdSignal.ts` — MACD (Band-Pass, fast−slow EMA + signal line), yAxisIndex=1
- `RsiSignal.ts` — RSI (Wilder's SMMA, duty-cycle indicator 0-100), yAxisIndex=1
- `BollingerSignal.ts` — Bollinger (SMA ± kσ sliding window), yAxisIndex=0
- Tutti registrati in `registry.ts` e `index.ts`

### 2A. `EMASignal` — Media Mobile Esponenziale

**File:** `frontend/src/lib/charts/signals/EMASignal.ts`

**Equivalenza controlli automatici:** Filtro passa-basso IIR del primo ordine.

**Formula ricorsiva (docstring):**
```
// α = 2 / (N + 1)
// EMA[0] = Close[0]
// EMA[t] = α × Close[t] + (1 − α) × EMA[t−1]
//
// Performance: essendo interessati a tutti i punti, calcoliamo iterativamente.
// Ogni punto è una singola moltiplicazione-somma: O(N) totale.
//
// α derivata da equiparazione dell'età media con SMA:
//   Età media SMA = (N-1)/2
//   Età media EMA = (1-α)/α
//   → α = 2/(N+1)
//
// For detailed mathematical theory and signal processing equivalents, see:
// docs/financial-theory/technical-indicators.md#ema
```

**Parametri:**
- `period` (N): tipo `number`, default 14, min 2, max 500, suffix `d`
- `offset`: tipo `number`, default 0, min -100, max 100, step 0.5, suffix `%`

**Categoria:** `indicator`
**Asse Y:** `0` (primario — stessa scala del prezzo)

### 2B. `MACDSignal` — Moving Average Convergence Divergence

**File:** `frontend/src/lib/charts/signals/MACDSignal.ts`

**Equivalenza controlli automatici:** Filtro passa-banda (rimuove componente DC / trend
di fondo e rumore HF), equivalente a una derivata smussata.

**Formula (docstring):**
```
// MACD line = EMA_fast(Close) − EMA_slow(Close)
// Signal line = EMA_signal(MACD line)
// Histogram = MACD − Signal
//
// Performance: 3 EMA calcolate sequenzialmente, ogni una O(N) → totale O(N).
//
// For detailed theory: docs/financial-theory/technical-indicators.md#macd
```

Il segnale produce una linea alla volta. Il parametro `component` (select: `'macd' | 'signal' | 'histogram'`)
permette di scegliere quale linea mostrare. L'utente aggiunge 2-3 istanze per avere tutte le linee
con stili diversi.

**Parametri:**
- `fastPeriod`: tipo `number`, default 12, min 2, max 100, suffix `d`
- `slowPeriod`: tipo `number`, default 26, min 2, max 200, suffix `d`
- `signalPeriod`: tipo `number`, default 9, min 2, max 50, suffix `d`
- `component`: tipo `select`, options: `macd/signal/histogram`, default `'macd'`
- `offset`: tipo `number`, default 0, min -100, max 100, step 0.5, suffix `%`

**Categoria:** `indicator`
**Asse Y:** `1` (secondario — scala propria, centrata su 0)

### 2C. `RSISignal` — Relative Strength Index

**File:** `frontend/src/lib/charts/signals/RSISignal.ts`

**Equivalenza controlli automatici:** Misuratore del duty-cycle / indicatore di saturazione
del sistema. Normalizza il rapporto gains/losses in range 0-100 con funzione asintotica.

**Formula (docstring):**
```
// deltas[t] = Close[t] − Close[t−1]
// gains[t] = max(deltas[t], 0)
// losses[t] = abs(min(deltas[t], 0))
// avgGain[0..N-1] = SMA(gains[0..N-1])
// avgLoss[0..N-1] = SMA(losses[0..N-1])
// for t >= N:
//   avgGain[t] = (avgGain[t-1] × (N-1) + gains[t]) / N   (SMMA)
//   avgLoss[t] = (avgLoss[t-1] × (N-1) + losses[t]) / N
// RS = avgGain / avgLoss
// RSI = 100 − 100/(1+RS)
//
// Performance: calcolo iterativo SMMA, O(N) totale.
//
// For detailed theory: docs/financial-theory/technical-indicators.md#rsi
```

**Parametri:**
- `period`: tipo `number`, default 14, min 2, max 100, suffix `d`
- `overbought`: tipo `number`, default 70, min 50, max 95, step 5
  (futuro: linea orizzontale di riferimento nel chart)
- `oversold`: tipo `number`, default 30, min 5, max 50, step 5

**Categoria:** `indicator`
**Asse Y:** `1` (secondario — scala 0-100, completamente indipendente dal prezzo)

### 2D. `BollingerSignal` — Bande di Bollinger

**File:** `frontend/src/lib/charts/signals/BollingerSignal.ts`

**Equivalenza controlli automatici:** Inseguitore del valore atteso con intervallo di
confidenza adattivo basato sulla varianza σ del segnale. Quando le bande si stringono
("Squeeze"), la varianza è minima: nei sistemi caotici precede esplosioni direzionali.

**Formula (docstring):**
```
// MB[t] = SMA_N(Close[t-N+1..t])        (Middle Band)
// σ[t]  = sqrt(var(Close[t-N+1..t]))    (Rolling standard deviation)
// Upper = MB + k×σ
// Lower = MB − k×σ
//
// SMA calcolata con sliding window a somma parziale: O(N) totale.
// σ calcolata con formula incrementale (Welford) o running sum of squares.
//
// For detailed theory: docs/financial-theory/technical-indicators.md#bollinger-bands
```

Produce 3 linee (middle/upper/lower) selezionate via param `component`. L'utente aggiunge
3 istanze per avere tutte e 3 le bande con stili diversi.

**Parametri:**
- `period`: tipo `number`, default 20, min 2, max 200, suffix `d`
- `multiplier` (k): tipo `number`, default 2.0, min 0.5, max 5, step 0.1, suffix `σ`
- `component`: tipo `select`, options: `middle/upper/lower`, default `'middle'`
- `offset`: tipo `number`, default 0, min -100, max 100, step 0.5, suffix `%`

**Categoria:** `indicator`
**Asse Y:** `0` (primario — stessa scala del prezzo)

### 2E. Registrazione nel registry

In `frontend/src/lib/charts/signals/registry.ts`:
- Importare `EMASignal`, `MACDSignal`, `RSISignal`, `BollingerSignal`
- Aggiungere al `SIGNAL_REGISTRY`

In `frontend/src/lib/charts/signals/index.ts`:
- Aggiungere le 4 nuove export

**File coinvolti Step 2:**
- `frontend/src/lib/charts/signals/EMASignal.ts` (nuovo)
- `frontend/src/lib/charts/signals/MACDSignal.ts` (nuovo)
- `frontend/src/lib/charts/signals/RSISignal.ts` (nuovo)
- `frontend/src/lib/charts/signals/BollingerSignal.ts` (nuovo)
- `frontend/src/lib/charts/signals/registry.ts`
- `frontend/src/lib/charts/signals/index.ts`

---

## Step 3 — ✅ Dual-axis Y in LineChart (Completato 9 Mar)

**Implementato:**
- `yAxis` convertito da singolo oggetto ad array di 2 assi
- Axis 0 (primario): scala del prezzo, posizione left/right come prima
- Axis 1 (secondario): posizione right, visibile solo se ci sono overlay con `yAxisIndex=1`
- `mainSeries` ha esplicito `yAxisIndex: 0`
- Overlay series passano `signal.yAxisIndex ?? 0`
- Grid right padding aumentato quando asse secondario attivo

Attualmente `LineChart.svelte` ha un singolo `yAxis: {...}` (riga ~503). ECharts supporta
nativamente `yAxis: [{...}, {...}]` come array, e ogni serie può specificare `yAxisIndex`.

### 3A. Aggiungere campo `yAxisIndex` in `RenderedSignal`

In `ChartSignal.ts`:
```typescript
export interface RenderedSignal {
    // ...existing fields...
    /** Y-axis index: 0 = primary (right), 1 = secondary (left). Default 0. */
    yAxisIndex?: number;
}
```

### 3B. Aggiungere campo statico `yAxisIndex` nelle classi segnale

Nella base class `ChartSignal`:
```typescript
/** Y-axis index for rendered output. 0 = primary (same scale as data), 1 = secondary (independent scale). */
static yAxisIndex: number = 0;
```

Override nelle sottoclassi:
- `RSISignal`: `static override yAxisIndex = 1` (scala 0-100)
- `MACDSignal`: `static override yAxisIndex = 1` (scala propria centrata su 0)
- Tutti gli altri: default `0` (non serve override)

Il metodo `render()` nella base class propaga il campo:
```typescript
render(...): RenderedSignal {
    return {
        // ...existing...
        yAxisIndex: (this.constructor as typeof ChartSignal).yAxisIndex,
    };
}
```

### 3C. Modificare `LineChart.svelte` per supportare dual-axis

**Logica:**
1. Determinare se serve il secondo asse: `const hasSecondaryAxis = overlaySignals.some(s => s.yAxisIndex === 1)`
2. `yAxis` diventa un array di 2 oggetti:

**Asse 0 (primario, DESTRA)** — dati principali + overlay sulla stessa scala:
```javascript
{
    type: 'value',
    position: 'right',
    // ...configurazione attuale (labels, splitLine, scale: true, etc.)
}
```

**Asse 1 (secondario, SINISTRA)** — segnali con scala indipendente (RSI 0-100, MACD):
```javascript
{
    type: 'value',
    position: 'left',
    show: hasSecondaryAxis,
    axisLine: { show: hasSecondaryAxis, lineStyle: { color: isDark ? '#6366f1' : '#4f46e5' } },
    axisLabel: {
        show: hasSecondaryAxis,
        color: isDark ? '#a5b4fc' : '#6366f1',  // indigo per distinguere dall'asse primario
        fontSize: 11,
        formatter: (v) => Math.round(v).toString(),  // RSI: interi
    },
    splitLine: { show: false },  // evitare sovraffollamento di grid lines
    scale: true,
}
```

3. Nella costruzione delle serie overlay, aggiungere `yAxisIndex`:
```javascript
const overlaySeries = {
    // ...existing...
    yAxisIndex: signal.yAxisIndex ?? 0,
};
```

4. Grid: aggiungere margine sinistro quando l'asse secondario è visibile:
```javascript
const gridConfig = compact ? {...} : {
    top: 35,
    right: 15,
    bottom: 35,
    left: hasSecondaryAxis ? 60 : 15,
    containLabel: true,
};
```

5. Tooltip: formattare correttamente i valori dei due assi (RSI senza decimali con %, prezzo con 4
   decimali). Usare `seriesName` o `yAxisIndex` dal params per decidere il formato.

**Note:**
- In modalità `compact` (card FX), l'asse secondario è nascosto (niente label) ma i dati
  sono comunque plottati sulla scala corretta.
- L'asse primario resta a **destra** coerentemente con il layout attuale delle card (mini-axis
  a destra in compact mode).

**File coinvolti Step 3:**
- `frontend/src/lib/charts/signals/ChartSignal.ts` (RenderedSignal + campo statico base)
- `frontend/src/lib/charts/signals/RSISignal.ts` (override yAxisIndex = 1)
- `frontend/src/lib/charts/signals/MACDSignal.ts` (override yAxisIndex = 1)
- `frontend/src/lib/components/charts/LineChart.svelte` (dual-axis rendering)

---

## Step 4 — Restructuring UI "Add Signal" in 3 dropdown categorizzati

Con 8 tipi di segnale (4 esistenti + 4 nuovi) i pulsanti piatti diventano caotici.
Usare i componenti select custom del progetto per creare 3 dropdown a tendina.

### 4A. Aggiungere campo `category` nella base class

In `ChartSignal.ts`:
```typescript
/** Category for UI grouping in ChartSettingsModal dropdown selectors */
static category: 'indicator' | 'comparison' | 'benchmark' = 'benchmark';
```

Override in ogni sottoclasse:
- `EMASignal`, `MACDSignal`, `RSISignal`, `BollingerSignal`: `'indicator'`
- `FxPairSignal`: `'comparison'`
- `LinearSignal`, `CompoundSignal`, `SineSignal`: `'benchmark'`

### 4B. Aggiornare `SignalTypeInfo` nel registry

In `registry.ts`:
```typescript
export interface SignalTypeInfo {
    type: string;
    displayName: string;
    icon: string;
    category: 'indicator' | 'comparison' | 'benchmark';  // ← nuovo
}
```

`getRegisteredSignalTypes()` include la categoria di ogni segnale registrato.

### 4C. 3 `SimpleSelect` come dropdown per aggiungere segnali

Nel `ChartSettingsModal`, sostituire i pulsanti piatti con 3 istanze di `SimpleSelect`
(`frontend/src/lib/components/ui/select/SimpleSelect.svelte`):

```
[📊 Indicatori Tecnici ▼] [💱 Confronto Dati ▼] [📐 Benchmark Sintetici ▼]
```

Ogni `SimpleSelect`:
- `placeholder` = titolo categoria tradotto (es. `$t('signals.categories.indicator')`)
- `options` = lista segnali della categoria, con `icon + displayName` come label
- `value` = `''` (sempre resettato dopo ogni selezione)
- `onchange` = `(type) => { addSignal(type); value = ''; }` — aggiunge il segnale e
  resetta il dropdown al placeholder, pronto per un'altra aggiunta
- Snippet `item` opzionale per mostrare l'icona emoji + nome tradotto

Layout: i 3 dropdown su una riga flex-wrap, con gap. Su mobile wrappano naturalmente.
Posizionati **subito sotto** il titolo "Overlay Signals", prima della OrderableList.

### 4D. i18n per categorie

Chiavi già definite in Step 1E: `signals.categories.indicator`, `.comparison`, `.benchmark`.

**File coinvolti Step 4:**
- `frontend/src/lib/charts/signals/ChartSignal.ts` (campo `category`)
- Tutti i file segnale (override `category`)
- `frontend/src/lib/charts/signals/registry.ts` (esporre categoria)
- `frontend/src/lib/components/charts/ChartSettingsModal.svelte` (3 SimpleSelect)
- `frontend/src/lib/i18n/*.json` (già coperte in Step 1E)

### 4E. ✅ Fix critici % conversion, dropdown auto-position, FxPair invert (Completato 9 Mar)

**Problema 1 — Conversione % nel preview chart:**
Il `ChartSettingsModal` passava `previewData` (dati assoluti ~1.0) direttamente al `PriceChartCompact`
anche in modalità percentuale. Il LineChart non fa conversione % internamente. Risultato: in % mode
il grafico mostrava valori tipo "1.0" anziché "0%".

**Soluzione:** Introdotto `previewDataAbs` (dati assoluti invariati) e `previewData` derivato che
converte in % con formula `((value - p0) / p0) × 100` quando `previewViewMode === 'percentage'`.
I segnali overlay usano `previewDataAbs` come input per `render()`.

**Problema 2 — Offset annullato in modalità %:**
Il `render()` centralizzato in `ChartSignal.ts` usava `p0 = absData[0].value` (primo punto del
segnale) per la conversione %. Con offset +5%, il segnale partiva da `y0 * 1.05`, e la conversione
faceva `(1.05 - 1.05) / 1.05 = 0%` — l'offset spariva.

**Soluzione:** Cambiato `p0` da `absData[0].value` a `baseData[0].value` (primo punto del dato
principale). Ora: `(y0*1.05 - y0) / y0 = 5%` — l'offset è visibile anche in % mode.

**Problema 3 — SimpleSelect dropdown si nascondevano sotto footer:**
I 3 `SimpleSelect` di categoria (indicator/comparison/benchmark) non avevano `dropdownPosition="auto"`.
Si aprivano sempre verso il basso, nascondendosi sotto il footer della modale.

**Soluzione:** Aggiunto `dropdownPosition="auto"` a tutti i `SimpleSelect` nella modale. Inoltre,
in `SimpleSelect.svelte`, aggiunta variabile reattiva `dropdownMaxHeight` che limita l'altezza del
dropdown allo spazio effettivamente disponibile (min 120px, max 240px), calcolato considerando il
parent scrollabile più vicino.

**Problema 4 — FxPair ⇄ invert non funzionava nel preview:**
Il pulsante ⇄ cercava la coppia inversa (`GBP-EUR`) nelle opzioni configurate. Se non esisteva
come coppia separata, non faceva nulla.

**Soluzione:** Aggiunto parametro `_inverted: boolean` in `FxPairSignal`. Quando true,
`computePoints()` restituisce `1/rate` anziché `rate`. Il pulsante ⇄ nel modal ora toglie
`_inverted` invece di cercare lo slug invertito. `getLabel()` mostra la coppia invertita
(es. "GBP/EUR" invece di "EUR/GBP"). Reset automatico di `_inverted` al cambio di coppia.

**File modificati:**
- `frontend/src/lib/charts/signals/ChartSignal.ts` (`render()`: p0 da baseData)
- `frontend/src/lib/charts/signals/FxPairSignal.ts` (`_inverted` support)
- `frontend/src/lib/components/charts/ChartSettingsModal.svelte` (previewDataAbs, dropdownPosition, invert logic)
- `frontend/src/lib/components/ui/select/SimpleSelect.svelte` (dropdownMaxHeight adattiva)

### 4F. ✅ Segment-based baseline coloring + Tooltip + Arrow markers (Completato 10 Mar)

**Problema 1 — `visualMap` crash con asse secondario (errore "coord undefined"):**
L'approccio precedente usava `visualMap` piecewise con dati in formato tupla `[index, value]`
per colorare la linea principale verde/rosso sopra/sotto baseline. Questo causava crash ECharts
quando venivano aggiunti segnali su `yAxisIndex: 1` (RSI, MACD) perché `visualMap` tentava di
risolvere coordinate su un asse non ancora completamente renderizzato, generando l'errore
`TypeError: Cannot read properties of undefined (reading 'coord')`.

Il two-phase rendering (Pass 1 senza visualMap, Pass 2 con `requestAnimationFrame`) era una
soluzione parziale che funzionava solo senza asse secondario.

**Soluzione definitiva:** Eliminato completamente `visualMap` e il formato dati tupla `[i, value]`.
I dati ora sono sempre valori semplici (`number | null`). La colorazione baseline è ottenuta
**spezzando la serie principale in 2 serie separate**: una verde (valori ≥ baseline) e una rossa
(valori < baseline). Ai punti di incrocio della baseline, il valore viene duplicato in entrambe
le serie per garantire continuità visiva. L'area fill viene applicata separatamente a ciascuna
serie con colore appropriato.

**Risultati:**
- Nessun crash con asse secondario
- Rendering in un singolo `setOption()` (niente `requestAnimationFrame`)
- Area fill colorata correttamente (verde sopra, rossa sotto)
- Tooltip con deduplicazione tramite `Set<string>` per evitare voci duplicate
  (le serie segmentate condividono lo stesso nome)

**Problema 2 — Tooltip troncato dalla modale:**
Il tooltip ECharts veniva renderizzato come div interno al container del chart, ma la modale
aveva `overflow: hidden`, troncando il tooltip quando si avvicinava ai bordi.

**Soluzione:** Aggiunto `appendToBody: true` nella config tooltip di ECharts. Il tooltip ora
viene renderizzato come figlio di `<body>`, uscendo dal contesto della modale.

**Problema 3 — Frecce marker sempre verticali (su/giù):**
Le frecce dei marker start/end degli overlay signal puntavano sempre verso l'alto o il basso
(`symbolRotate: 0` o `180`), indipendentemente dalla direzione della linea. L'utente si aspetta
che la freccia segua la pendenza della linea.

**Soluzione:** Implementato calcolo della rotazione basato sulla pendenza (slope) della linea
al punto del marker. Per il marker start, si cerca il primo punto valido successivo e si
calcola `atan2(-dy, dx)` per ottenere l'angolo in screen coordinates (y invertita). Per il
marker end, si cerca il punto precedente. La freccia start viene ruotata di 180° aggiuntivi
perché deve puntare "all'indietro" (indica l'inizio della linea).

**File modificati:**
- `frontend/src/lib/components/charts/LineChart.svelte` (segment coloring, tooltip, markers)

---

## Step 5 — Tooltip informativi con supporto LaTeX (KaTeX)

### 5A. Installare KaTeX nel frontend

Aggiungere `katex` al `package.json` frontend:
```bash
cd frontend && npm install katex
```

KaTeX è ~300KB gzip, molto più leggero di MathJax (~1MB), e adatto per rendering inline sincrono.

### 5B. Evolvere `Tooltip.svelte` per supportare HTML/LaTeX

Il componente attuale (`frontend/src/lib/components/ui/Tooltip.svelte`) accetta solo `text: string`
e usa `{text}` come contenuto testo puro. Evolvere:

1. Aggiungere prop opzionale `html?: string` (alternativa a `text`)
2. Se `html` è fornito, renderizzare con `{@html html}` anziché `{text}`
3. Aggiungere prop opzionale `math?: boolean` (default `false`)
4. Se `math === true`, processare il contenuto con una funzione helper che trova i pattern
   `$...$` nel testo e li sostituisce con il rendering KaTeX:

```typescript
import katex from 'katex';

function renderMathInline(text: string): string {
    return text.replace(/\$([^$]+)\$/g, (_, formula) => {
        try {
            return katex.renderToString(formula, { throwOnError: false, displayMode: false });
        } catch {
            return formula;
        }
    });
}
```

5. Importare il CSS di KaTeX: `import 'katex/dist/katex.min.css'` nel componente (o nel layout globale)
6. Quando `math === true`, il contenuto diventa: `{@html renderMathInline(textOrHtml)}`

### 5C. Aggiungere campo `tooltip` in `SignalParamDescriptor`

In `ChartSignal.ts`:
```typescript
export interface SignalParamDescriptor {
    // ...existing...
    /** i18n key for tooltip text. May contain $...$ inline LaTeX. */
    tooltip?: string;
}
```

### 5D. Rendere tooltip nel `ChartSettingsModal`

Accanto a ogni input parametro nell'OrderableList, se `desc.tooltip` è definito, mostrare
un'icona `ⓘ` (lucide `Info`, size 12) wrappata in `<Tooltip text={$t(desc.tooltip)} math>`.

Esempio rendering:
```svelte
{#if desc.tooltip}
    <Tooltip text={$t(desc.tooltip)} math position="top">
        <Info size={12} class="text-gray-400 hover:text-libre-green cursor-help" />
    </Tooltip>
{/if}
```

### 5E. Testi tooltip per tutti i parametri (i18n, con LaTeX inline)

Aggiungere sezione `signals.tooltips` nei file JSON i18n. Esempi (en):
```json
"signals": {
  "tooltips": {
    "annualRate": "Annual growth rate in percent.",
    "amplitude": "Peak-to-peak oscillation range around the base value.",
    "period": "Memory length of the filter in days. Higher values = smoother but slower response.",
    "offset": "Vertical offset as percentage of the base value.",
    "currencyPair": "Select an FX pair to overlay its exchange rate data.",
    "fastPeriod": "Short-term EMA period. Standard: 12 days. Maps to $\\alpha = 2/13$.",
    "slowPeriod": "Long-term EMA period. Standard: 26 days.",
    "signalPeriod": "EMA smoothing applied to the MACD line. Standard: 9 days.",
    "component": "Which component of the indicator to display.",
    "multiplier": "Number of standard deviations ($k \\cdot \\sigma$). 2 ≈ 95% confidence interval.",
    "overbought": "Level above which the asset is considered overbought. Standard: 70.",
    "oversold": "Level below which the asset is considered oversold. Standard: 30.",
    "emaPeriod": "Lookback window. Maps to filter coefficient $\\alpha = 2/(N+1)$."
  }
}
```

### 5F. Bottone `?` per aprire la documentazione MkDocs

Aggiungere campo statico opzionale nelle classi segnale:
```typescript
static docsPath?: string; // e.g. 'financial-theory/technical-indicators/#ema'
```

Nel row dell'OrderableList in `ChartSettingsModal`, accanto al titolo del tipo segnale,
bottone piccolo `?`:
```svelte
{#if typeInfo?.docsPath}
    <button
        type="button"
        class="p-0.5 rounded text-gray-400 hover:text-libre-green transition-colors"
        title="Documentation"
        onclick={() => window.open(`/docs/${typeInfo.docsPath}`, '_blank')}
    >
        <HelpCircle size={12} />
    </button>
{/if}
```

**File coinvolti Step 5:**
- `frontend/package.json` (aggiungere `katex`)
- `frontend/src/lib/components/ui/Tooltip.svelte` (supporto html + math)
- `frontend/src/lib/charts/signals/ChartSignal.ts` (tooltip in descriptor, docsPath)
- Tutti i file segnale (aggiungere tooltip keys e docsPath)
- `frontend/src/lib/components/charts/ChartSettingsModal.svelte` (rendere tooltip + bottone ?)
- `frontend/src/lib/i18n/*.json` (testi tooltip 4 lingue)

---

## Step 6 — Documentazione MkDocs: Technical Indicators & Signal Processing

Interamente in **inglese**. Nuova sezione sotto Financial Theory.

### 6A. `mkdocs_src/docs/financial-theory/technical-indicators.md`

Struttura per ogni indicatore (EMA, MACD, RSI, Bollinger):

1. **Financial Meaning**: cos'è, come lo usano i trader
2. **Mathematical Formula**: formule LaTeX con `$$ ... $$`
3. **Parameters**: tabella con parametro, default, significato intuitivo
4. **Signal Processing Equivalent**: traduzione in terminologia controlli automatici / signal processing

Sezioni signal processing (il differenziatore chiave della documentazione):

- **EMA → IIR Low-Pass Filter (1° ordine)**:
  Equazione alle differenze `y[n] = αx[n] + (1−α)y[n−1]`. Spiegare come `α = 2/(N+1)` deriva
  dall'equiparazione dell'età media dei dati con la SMA. Funzione di trasferimento H(z),
  posizione del polo, risposta in frequenza. Frequenza di taglio approssimata.

- **MACD → Band-Pass Filter / Smoothed Derivative**:
  Differenza di due passa-basso = cancella DC (trend baseline) e attenua HF (rumore giornaliero).
  Quello che resta è la "banda media" del momentum. Signal Line = ulteriore smoothing per
  ridurre falsi positivi (come un filtro anti-alias post-demodulazione).

- **RSI → Duty-Cycle / Saturation Indicator**:
  Isola componenti positiva e negativa dei delta (rettificatore + filtro). Rapporto delle medie
  normalizzato con funzione asintotica `100 − 100/(1+RS)` per comprimere in [0, 100].
  Analogia con il duty cycle di un segnale PWM.

- **Bollinger Bands → Adaptive Confidence Interval (σ-tracker)**:
  Banda mobile che insegue la distribuzione locale del segnale. Middle Band = valore atteso
  (SMA = E[X]), Upper/Lower = E[X] ± kσ. Se distribuzione Gaussiana, k=2 → 95.4% contenimento.
  Code grasse nei mercati → breaching più frequente. Squeeze = bassa varianza → precede
  esplosione di volatilità (transizione di regime).

### 6B. `mkdocs_src/docs/financial-theory/synthetic-benchmarks.md`

Documentare i benchmark sintetici:
- **Linear Growth**: retta `y = y0(1 + r×t)`, uso come reference per crescita costante
- **Compound Growth**: esponenziale `y = y0(1+r)^t`, calcolo iterativo per performance,
  interesse composto giornaliero
- **Sine Wave**: oscillazione `y = y0 + A×sin(2πt/T + φ)`, uso come reference per volatilità periodica
- Per tutti: spiegare il parametro `offset` (%)

### 6C. Aggiornare `mkdocs.yml` nav

Aggiungere le nuove pagine nella sezione Financial Theory:
```yaml
- Financial Theory:
    # ...existing entries...
    - Technical Indicators: financial-theory/technical-indicators.md
    - Synthetic Benchmarks: financial-theory/synthetic-benchmarks.md
```

### 6D. Aggiornare `financial-theory/index.md`

Aggiungere i nuovi link nella lista "Key Concepts":
```markdown
- **[Technical Indicators](technical-indicators.md)**: EMA, MACD, RSI, Bollinger Bands — with signal processing equivalents.
- **[Synthetic Benchmarks](synthetic-benchmarks.md)**: Linear, Compound, and Sine wave reference signals.
```

### 6E. Code-to-Doc linking

In ogni classe segnale, aggiornare il docstring con link alla sezione MkDocs:
```typescript
/**
 * EMASignal — Exponential Moving Average overlay.
 * ...
 * For detailed mathematical theory and signal processing equivalents, see:
 * docs/financial-theory/technical-indicators.md#ema
 */
```

**File coinvolti Step 6:**
- `mkdocs_src/docs/financial-theory/technical-indicators.md` (nuovo)
- `mkdocs_src/docs/financial-theory/synthetic-benchmarks.md` (nuovo)
- `mkdocs_src/docs/financial-theory/index.md` (aggiornare)
- `mkdocs_src/mkdocs.yml` (aggiornare nav)
- Tutti i file segnale (docstring con link)

---

## Step 7 — Fix UX pendenti

### 7A. Preview pair mode: titolo coppia con bandiere + pulsante inversione

Quando `mode === 'pair'` nel `ChartSettingsModal`, sotto il titolo "Preview" mostrare:
- Bandiera base + codice → Bandiera quote + codice (es. "🇪🇺 EUR → 🇬🇧 GBP")
- Pulsante `[⇄]` per invertire il rate (locale alla modale)
- L'inversione diventa effettiva solo al click "Apply"
- Toggle Abs/% nel preview (già implementato)

### 7B. Stale Gradient: predisposizione

Nel `generateSyntheticData()`, marcare artificialmente alcuni punti con `staleDays > 0`
per testare il gradient stale nel preview. `LineChart` già supporta `staleDays` e calcola
opacità — verificare che funzioni con le impostazioni della modale.

### 7C. Verificare Apply → onsave salva effettivamente

Il callback `onsave` nella pagina FX deve chiamare `setGlobalSettings()` o `setPairSettings()`
dal `chartSettingsStore` e lo stato si deve propagare a tutte le card / al detail.
Verificare che il round-trip funzioni: modifica → apply → chiudi → riapri → impostazioni mantenute.

**File coinvolti Step 7:**
- `frontend/src/lib/components/charts/ChartSettingsModal.svelte`
- `frontend/src/routes/(app)/fx/+page.svelte` (handler save)

---

## Ordine di esecuzione (senza dipendenze cross-step)

```
Stream A:  Step 1 → Step 2 → Step 3 → Step 4
Stream B:  Step 6 (in parallelo con Stream A)
Converge:  Step 5 (dopo Step 4 + Step 6 — serve doc per i link e i nuovi segnali per i tooltip)
Step 7:    Indipendente, eseguibile in qualsiasi momento
```

### Parallelo ottimale:
```
  t0          t1          t2          t3          t4          t5
  ├── Step 1 ──┼── Step 2 ──┼── Step 3 ──┼── Step 4 ──┼── Step 5 ──┤
  │                                                                  │
  ├── Step 6 (docs) ────────────────────────────────────┘            │
  │                                                                  │
  ├── Step 7 (fix UX) ──────────────────────────────────────────────┤
```

---

## Step 4B — 🔄 Bug fix e UX polish da review utente (9 Mar)

Feedback dalla prima review dopo Steps 1-4. Questi fix sono prerequisito per procedere con Step 5+.

### 4B.1 — ✅ Dropdown categorizzati: layout + colori
**Problema**: I 3 dropdown occupano troppo spazio verticale e il grigio li fa sembrare readonly.
**Fix**:
- Layout compatto su 1 riga: ciascuno con titolo breve bold sopra e label piccola sotto
- In mobile: centrati in colonna verticale
- Colore: usare border colorato (verde) o stile "add" (non grigio spento)
- Modale `maxWidth` da `xl` (36rem) a `3xl` (48rem) in desktop
- In mobile: colonna singola centrata, in desktop: griglia 3 colonne

### 4B.2 — ✅ MACD: auto-bundle 3 componenti
**Problema**: MACD mostra solo 1 componente per volta. L'utente vuole MACD line + Signal + Histogram sovrapposti.
**Fix**:
- Rimuovere il param `component` dalla SignalParamDescriptor del MACD
- `computePoints` restituisce i punti della MACD line (principale)
- Aggiungere override `render()` che restituisce array di 3 `RenderedSignal`:
  - MACD line (colore principale)
  - Signal line (colore più chiaro, dashed)
  - Histogram (bar chart con colore trasparente)
- **Alternativa più semplice**: Quando si aggiunge MACD, auto-aggiungere 3 segnali separati
  (MACD line, Signal, Histogram) come sibling nella lista. L'utente può rimuoverne singoli.
  **→ Implementato: `addSignal('macd')` auto-inserisce 3 SignalConfig con colori/stili diversi.**
- Migrare il `<select>` dei componenti rimasti (Bollinger) a `SimpleSelect` custom **→ Done**

### 4B.3 — ✅ Bollinger: auto-bundle 3 componenti
**Problema**: Mostra una sola linea alla volta. L'utente vuole le 3 linee + area shaded.
**Fix**: Stesso approccio del MACD — auto-aggiungere 3 segnali (Upper, Middle, Lower).
Per l'area shaded tra upper e lower: usare la markArea ECharts o `areaStyle` con `stack`.
La soluzione più pratica: Bollinger auto-inserisce 3 RenderedSignal, e nel LineChart riconoscere
una coppia upper/lower dello stesso bollinger per disegnare l'area shaded tra le due linee.
**→ Implementato: `addSignal('bollinger')` auto-inserisce 3 SignalConfig (Upper/cyan dashed, Middle/viola solid, Lower/cyan dashed).**
TODO futuro: area shaded tra upper e lower (richiede supporto ECharts areaStyle/markArea).

### 4B.4 — ✅ RSI / MACD: scala assoluta sempre (già funzionante)
**Problema**: RSI schiaccia tutti i segnali in % mode perché usa lo stesso asse.
**Fix**: L'RSI è in scala assoluta (0-100) SEMPRE, non va mai in % mode. In `computePoints`,
ignorare `viewMode` e restituire sempre i valori RSI grezzi (0-100). Lo yAxisIndex=1 li isola.
Verificare che il LineChart mostri l'asse secondario quando ci sono segnali su yAxisIndex=1.
Il MACD similmente: la scala MACD è in unità prezzo differenziali, non %, quindi anche MACD
deve ignorare viewMode.

### 4B.5 — ✅ FX Pair selector: sizing da w-40 a w-48
**Problema**: Prima di selezionare → troppo alto; dopo → testo troncato.
**Fix**: Dare `w-48` (wider) al contenitore del SimpleSelect per FX pair, e assicurarsi che il
placeholder sia compatto ("Select pair...") e il valore selezionato non trunchi le bandiere.

### 4B.6 — 📋 404 `/api/v1/fx/currencies/convert` — non bloccante
**Problema**: L'endpoint è nello schema OpenAPI (generated.ts) ma NON esiste nel backend.
Chiamato da `fxStoreRegistry.ts` e da `+page.svelte` (fx list e detail).
**Fix a breve termine**: Wrappare le chiamate in try/catch con silent fallback.
Nessun cambio backend — la feature sarà implementata nel plan `fxSyncApiRedesign`.
**Fix permanente**: Pianificato in `plan-fxSyncApiRedesign.prompt.md`.

### 4B.7 — ✅ ECharts crash `coord` — xAxis/yAxis + resize guard (Fix 9 Mar)
**Problema**: `Cannot read properties of undefined (reading 'coord')` su apertura Settings e resize.
Due cause: (1) `markPoint` usava `coord: [index, value]` che ECharts non riesce a risolvere su
resize o quando l'asse non è pronto; (2) `ResizeObserver` scattava prima di `setOption()`.
**Fix 1**: Sostituito `coord: [i, v]` con `{ xAxis: dates[i], yAxis: v }` nei markPoint — ECharts
risolve correttamente le coordinate usando i valori dell'asse category.
**Fix 2**: Aggiunto flag `chartOptionSet` che blocca `resize()` fino al primo `setOption()`.
Reset nel `cleanup()`. Il `ResizeObserver` ora controlla `if (chartOptionSet) chartInstance?.resize()`.

### 4B.8 — ✅ Select nativi → SimpleSelect custom
**Fix applicato**: Tutti i `<select>` nativi nel ChartSettingsModal sostituiti con `SimpleSelect`.

### 4B.9 — 📋 Console violations (passive event listeners)
Warning benigni dalla libreria ECharts. Non bug di LibreFolio.

---

## Step 4C — ✅ Chart Evolution: bar/band/FxPair rendering (Completato 9 Mar)

Evoluzione del LineChart per supportare tipi di rendering diversi dalle sole linee,
risoluzione dati FX Pair, e tooltip avanzati.

### 4C.1 — ✅ `RenderedSignal.seriesType` — nuovo campo
**Aggiunto** in `ChartSignal.ts`:
```typescript
seriesType?: 'line' | 'bar' | 'band';
bandData?: { upper: number[]; middle: number[]; lower: number[] };
```
- `'line'` (default): linea standard (comportamento esistente)
- `'bar'`: barre verticali colorate (usato da MACD histogram)
- `'band'`: confidence band con area shaded (usato da Bollinger)

### 4C.2 — ✅ MACD Histogram → barre
**Modifica** in `MacdSignal.ts`:
- Override `render()`: quando `component === 'histogram'`, imposta `seriesType = 'bar'`
- Il LineChart lo renderizza come `type: 'bar'` ECharts con colorazione automatica:
  positivo → verde, negativo → rosso, `barWidth: '60%'`
- Auto-bundle dal ChartSettingsModal: quando si aggiunge MACD, vengono creati 3 segnali
  separati (MACD line, Signal, Histogram) con stili e colori diversi

### 4C.3 — ✅ Bollinger → confidence band (area shaded)
**Riscrittura** completa di `BollingerSignal.ts`:
- Rimosso param `component` — ora il segnale calcola sempre tutte e 3 le bande
- Override `render()`: restituisce `seriesType = 'band'` + `bandData {upper, middle, lower}`
- Il LineChart usa la tecnica "stacked area" di ECharts:
  - Serie 1: Lower bound (linea invisibile, base dello stack)
  - Serie 2: Delta (Upper−Lower) con `areaStyle` shaded (stack su serie 1)
  - Serie 3: Middle (SMA) linea visibile con stile dell'utente
- **Rimosso** auto-bundle dal ChartSettingsModal: un singolo segnale Bollinger produce tutte e 3 le bande

### 4C.4 — ✅ LineChart: rendering multi-tipo
**Modifica** del loop overlay in `LineChart.svelte`:
- Branch `sType === 'band'`: genera 3 serie ECharts (Lower + Delta + Middle) con stack ID unico
- Branch `sType === 'bar'`: genera serie `type: 'bar'` con colori red/green per valore
- Branch default: comportamento linea esistente (con marker start/end)

### 4C.5 — ✅ FX Pair: data injection da TimeSeriesStore
**Problema**: FxPairSignal richiedeva `_resolvedData` iniettato, ma nessuno lo faceva.
**Fix** in `+page.svelte` (FX list):
- In `getRenderedSignals()`: per ogni `cfg.signalType === 'fx-pair'`, recupera i dati
  dal `getFxStore(pairSlug).getAllSorted()` e li inietta come `_resolvedData`
**Fix** in `ChartSettingsModal.svelte`:
- Nuova prop `pairsDataMap: Record<string, LineDataPoint[]>` — mappa slug→dati
- In `previewSignals` derived: per FxPair, risolve `_resolvedData` da `pairsDataMap`
- La pagina FX passa `pairsDataMap` con tutti i dati delle coppie caricate

### 4C.6 — ✅ Tooltip avanzato
**Migliorato** il formatter del tooltip in `LineChart.svelte`:
- Nasconde serie helper Bollinger (Lower/Band) nel tooltip
- Per i segnali band, mostra Upper/Lower come riga secondaria sotto il valore Middle
- Per segnali su asse secondario: aggiunge badge `[2nd]` accanto al valore
- Lookup asse secondario tramite mappa `signalAxisMap`

**File coinvolti Step 4C:**
- `frontend/src/lib/charts/signals/ChartSignal.ts` (+seriesType, +bandData)
- `frontend/src/lib/charts/signals/MacdSignal.ts` (render() override per histogram bar)
- `frontend/src/lib/charts/signals/BollingerSignal.ts` (riscrittura completa: band rendering)
- `frontend/src/lib/components/charts/LineChart.svelte` (rendering multi-tipo + tooltip avanzato)
- `frontend/src/lib/components/charts/ChartSettingsModal.svelte` (+pairsDataMap, FxPair data injection)
- `frontend/src/routes/(app)/fx/+page.svelte` (FxPair data injection + pairsDataMap prop)

---

## Step 4D — ✅ Centralizzazione % conversion + Dropdown auto + FxCard reattiva (Completato 9 Mar)

### Problema: conversione abs↔% inconsistente tra segnali

Ogni segnale gestiva `viewMode` internamente nel proprio `computePoints()`, con formule diverse.
Alcuni usavano `offset` nella formula %, altri `(value/y0 - 1) * 100`, altri ignoravano viewMode.
Risultato: passando da abs a %, segnali sintetici si rompevano o mostravano scale incongrue.

### Soluzione: centralizzazione nella base class

- **`ChartSignal.computePoints(baseData)`** — firma semplificata, calcola SOLO valori assoluti.
  Rimosso il parametro `viewMode` da tutti gli 8 segnali (Linear, Compound, Sine, EMA, MACD,
  RSI, Bollinger, FxPair).
- **`ChartSignal.render(baseData, viewMode)`** — conversione % centralizzata:
  ```
  pct = ((value − p0) / p0) × 100
  ```
  dove `p0` è il primo punto del segnale. Segnali su asse secondario (yAxisIndex=1, RSI/MACD)
  saltano la conversione: sono già in scala propria (RSI 0-100, MACD centrato su 0).
- **`BollingerSignal.render()`** — override speciale: applica la stessa formula % anche ai
  dati `bandData.upper/middle/lower` per coerenza con la band shaded area.

### Problema: Dropdown si apre sotto il footer

I `SimpleSelect` nella ChartSettingsModal si aprivano sempre verso il basso, nascondendosi
sotto il footer della modale.

### Soluzione: `dropdownPosition="auto"` su SimpleSelect

- Aggiunto mode `'auto'` a `SimpleSelect.svelte` (come già esisteva in `SearchSelect.svelte`)
- Calcola spazio disponibile sopra/sotto usando `getBoundingClientRect()` + scrollable parent
- Se lo spazio sotto è < 200px e c'è più spazio sopra → apre verso l'alto
- Tutti i `SimpleSelect` in `ChartSettingsModal` ora usano `dropdownPosition="auto"`

### Problema: Invert rate e % locale non aggiornano i segnali overlay

La pagina FX pre-renderizzava i segnali con `globalViewMode` e li passava come prop statica
`overlaySignals` alla FxCard. Quando l'utente invertiva il rate (⇄) o cambiava la % locale
nella card, il grafico si aggiornava ma i segnali overlay restavano calcolati sulla vista
vecchia (non invertita, viewMode globale).

### Soluzione: callback `renderSignals` reattivo

- FxCard non riceve più `overlaySignals: RenderedSignal[]` (prop statica)
- Riceve `renderSignals: (chartData, viewMode) => RenderedSignal[]` (callback)
- FxCard calcola `absoluteData` (post-inversione) come `$derived`
- `overlaySignals` è ora un `$derived` interno che chiama `renderSignals(absoluteData, cardViewMode)`
- Si ricalcola automaticamente quando `inverted` o `cardViewMode` cambiano
- La pagina FX passa: `renderSignals={(chartData, vm) => getRenderedSignals(slug, chartData, vm)}`
- `getRenderedSignals` ora accetta `LineDataPoint[]` (dati assoluti post-inversione) anziché `FxDataPoint[]`

**File coinvolti Step 4D:**
- `frontend/src/lib/charts/signals/ChartSignal.ts` (refactor computePoints/render)
- `frontend/src/lib/charts/signals/LinearSignal.ts` (abs-only)
- `frontend/src/lib/charts/signals/CompoundSignal.ts` (abs-only)
- `frontend/src/lib/charts/signals/SineSignal.ts` (abs-only)
- `frontend/src/lib/charts/signals/EMASignal.ts` (abs-only)
- `frontend/src/lib/charts/signals/MacdSignal.ts` (abs-only)
- `frontend/src/lib/charts/signals/RSISignal.ts` (abs-only)
- `frontend/src/lib/charts/signals/BollingerSignal.ts` (abs-only + band % override)
- `frontend/src/lib/charts/signals/FxPairSignal.ts` (abs-only)
- `frontend/src/lib/components/ui/select/SimpleSelect.svelte` (+auto position)
- `frontend/src/lib/components/fx/FxCard.svelte` (renderSignals callback, reactive overlays)
- `frontend/src/routes/(app)/fx/+page.svelte` (renderSignals prop, LineDataPoint import)
- `frontend/src/lib/components/charts/ChartSettingsModal.svelte` (dropdownPosition auto, computePoints signature)

---

## Bug Fix — ECharts visualMap + coord crash (10 Mar 2026)

### Problema
All'apertura della modale Settings (e anche dei chart card in modalità `%`), ECharts crashava con:
```
TypeError: Cannot read properties of undefined (reading 'coord')
```
Il crash avveniva dentro `markLine.render()` / `visualMap` perché il coordinateSystem non era ancora
completamente inizializzato al momento del primo `setOption()`.

### Root Cause
Il `visualMap` con `type: 'piecewise'`, `dimension: 1` e dati in tuple format `[index, value]`
richiede che il coordinateSystem sia completamente laid out per risolvere le coordinate. Al primo
render (specialmente dentro una modale in apertura), gli assi non hanno ancora bounds validi.

Il `markLine` con `{yAxis: baselineValue}` sulla stessa serie del `visualMap` amplificava il problema
perché anch'esso richiede la risoluzione delle coordinate.

### Soluzione: Two-Phase Rendering

**Fase 1**: `setOption()` SENZA `visualMap` → stabilisce assi, dati, coordinate.

**Fase 2**: In un `queueMicrotask()` (dopo il rendering sincrono), aggiunge il `visualMap`
come aggiornamento incrementale con `setOption({visualMap}, false)` (merge mode).

In aggiunta, il `markLine` è stato sostituito da una **serie flat-line dedicata** (`__baseline__`)
che disegna una linea orizzontale tratteggiata al valore baseline, evitando il bug ECharts
markLine+visualMap. La serie `__baseline__` è esclusa dal tooltip e ha `silent: true`.

Fallback: se la fase 1 fallisce, stripa markPoint/markLine e visualMap e retenta. Se anche il
retry fallisce, arrende silenziosamente.

### File modificati
- `frontend/src/lib/components/charts/LineChart.svelte` — two-phase setOption, baseline series

---

## Step 4G — ✅ Stale Gradient Smooth Linear Fade (10 Mar 2026)

### Problema
La sfumatura stale mostrava transizioni a gradini visibili: il `roundOpacity()` creava step
discreti di 0.02, producendo molti micro-segmenti con opacità leggermente diversa. L'effetto
visivo era una serie di "salti" di opacità anziché un gradiente lineare smooth.

### Root Cause
`roundOpacity()` arrotondava ogni valore di opacità a step di 0.02, creando ~50 livelli possibili.
Ogni cambio di livello creava un nuovo segmento ECharts con colore costante, causando transizioni
discrete visibili. Inoltre, i segmenti si estendevano ±1 punto ai confini per continuità, ma la
sovrapposizione delle aree fill causava un "flash" di opacità doppia ai boundary.

### Soluzione: Binary Segmentation + Horizontal Gradient
1. **`roundOpacity()` semplificato a binario**: tutti i punti freschi (staleDays=0) → opacity 1.0,
   tutti i punti stale → sentinel 0.5. Questo produce al massimo 2 segmenti per sezione continua
   (fresh + stale), senza micro-segmentazione.

2. **Horizontal LinearGradient per segmenti stale**: anziché un colore solido uniforme, ogni
   segmento stale usa `echarts.graphic.LinearGradient(0,0,1,0, [...])` che sfuma orizzontalmente
   dall'opacità del primo punto stale a quella dell'ultimo. L'opacità per ogni punto è calcolata
   da `getStaleOpacity(staleDays)` che interpola linearmente da 1.0 (0 giorni) a 0.15 (14+ giorni).

3. **Area fill stale**: anche l'area sotto la linea usa un gradiente orizzontale, con opacità
   proporzionale a quella della linea per mantenere coerenza visiva.

4. **Bridge forward-only**: i segmenti si estendono solo in AVANTI (+1 punto), non indietro.
   Il segmento fresh "copre" il punto boundary, evitando che il segmento stale sovrapponga
   la sua opacità ridotta su un punto che dovrebbe essere fresco.

### Risultato
La transizione fresh→stale è ora completamente liscia: la linea sfuma progressivamente
da piena opacità fino a quasi trasparente, senza salti discreti. L'area fill segue lo
stesso gradiente.

### File modificati
- `frontend/src/lib/components/charts/lineChartHelpers.ts` — roundOpacity binary, segment gradient

---

## Step 4H — ✅ MACD Axis Fix & Card Redesign (10 Mar 2026)

### Problema 1: Valori MACD tutti a 0 sull'asse primario
I valori MACD per coppie FX sono tipicamente ~0.001–0.01 (differenza tra due EMA di prezzi ≈0.8–1.3).
Mettendoli sull'asse primario (scala ~0.8–1.3) senza scaling, le linee MACD erano appiattite sullo 0.

### Soluzione Asse — Auto-Scale su Asse Primario
**Aggiornamento 10 Mar 2026**: Abbandonata la strategia "MACD su asse secondario" perché RSI e MACD
avevano scale completamente diverse (RSI 0-100, MACD ~0.001) condividendo lo stesso asse secondario.
Nuova soluzione:

- **Tutte e 3 le componenti MACD** → `yAxisIndex: 0` (asse primario)
- **Auto-scale**: quando `histogramScale = 0` (default), il multiplier viene calcolato automaticamente
   affinché il valore massimo assoluto MACD occupi circa il 25% del range del dato base.
   `histScale = (baseRange × 0.25) / maxMacdValue`
- Lo stesso moltiplicatore viene applicato uniformemente a MACD Line, Signal Line E Histogram.
- Nel tooltip, ogni label include `[Nx×]` per indicare il fattore di scala.
- Solo **RSI** usa `yAxisIndex: 1` (asse secondario, scala 0-100 indipendente).

### Soluzione Card Modale
La card MACD nel ChartSettingsModal mostra:
1. Riga parametri: Fast Period, Slow Period, Signal Period, Histogram Scale (0=auto)
2. Due righe di personalizzazione stile:
   - Riga 1: "MACD Line" — color picker + style popover (per la linea principale)
   - Riga 2: "Signal Line" — color picker + style/width buttons (stesso colore di default)
3. L'histogram non ha personalizzazione stile (colori red/green automatici)

### Parametri aggiuntivi in MacdSignal
- `histogramScale`: tipo `number`, default **0** (auto), min 0, max 100000, step 100
- `_signalColor`: colore della Signal Line (default = colore card principale)
- `_signalLineWidth`: spessore della Signal Line
- `_signalLineType`: tipo tratto della Signal Line

### File coinvolti
- `frontend/src/lib/charts/signals/MacdSignal.ts` — yAxisIndex → 0, histogramScale param, style params per signal line
- `frontend/src/lib/components/charts/ChartSettingsModal.svelte` — card MACD con 2 righe stile
- `frontend/src/lib/i18n/*.json` — chiavi per "MACD Line", "Signal Line", "Histogram Scale"

---

## Step 4I — 🔄 i18n Tree Command (10 Mar 2026)

### Problema
L'utente (e l'agente) hanno spesso bisogno di capire la struttura gerarchica delle chiavi i18n
per trovare quelle giuste. Attualmente bisogna cercare chiave per chiave o leggere il JSON grezzo.

### Soluzione
Aggiungere un subcomando `tree` a `./dev.py i18n tree` che stampa l'albero delle chiavi i18n:
```
📦 i18n Keys (en.json — 387 keys)
├── common (24 keys)
│   ├── loading, save, cancel, confirm, ...
├── chart (8 keys)
│   ├── tooltip (4 keys)
│   │   ├── stale, percentNote, secondaryAxis, upper, lower
│   ├── ...
├── chartSettings (18 keys)
│   ├── title, subtitle, aesthetics, ...
│   ├── categories (3 keys)
│   │   ├── indicator, comparison, benchmark
│   ├── params (12 keys)
│   │   ├── annualRate, amplitude, period, ...
├── signals (15 keys)
│   ├── linear, compound, sine, fxPair, ema, macd, rsi, bollinger
│   ├── params (12 keys)
│   ├── tooltips (12 keys)
...
```

### Parametri CLI
- `./dev.py i18n tree` — mostra albero con conteggio foglie per nodo (default: en.json)
- `./dev.py i18n tree --lang it` — mostra albero di it.json
- `./dev.py i18n tree --depth 2` — limita la profondità dell'albero
- `./dev.py i18n tree --values` — mostra anche i valori delle foglie (troncati a 40 char)

### File coinvolti
- `frontend/scripts/i18n-audit.py` — aggiungere `cmd_tree()` + registrazione in `register_subparser()`

---

## Step 4J — ✅ Stale Gradient Reactivity + MACD Auto-Scale Primary Axis (10 Mar 2026)

### Bug 1: Stale gradient toggle non reattivo
Attivare/disattivare lo switch "Gradiente Dati Vecchi" non aggiornava il grafico preview
finché non si switchava abs/%. Causa: la prop `showGradient` non era elencata tra le
dipendenze reattive nel `$effect()` di `LineChart.svelte`.

**Fix**: Aggiunto `void showGradient;` tra le dipendenze nel `$effect()` — ora il toggle ha
effetto immediato.

### Bug 2: RSI e MACD sullo stesso asse secondario
Con la precedente strategia (MACD su asse 1, RSI su asse 1), entrambi condividevano un
asse con scale radicalmente diverse (MACD ~±0.01 vs RSI 0-100), rendendo uno dei due illeggibile.

**Soluzione**: MACD → asse primario (0) con auto-scale. Solo RSI resta su asse secondario (1).
- `histogramScale=0` (nuovo default) → auto-calcola il multiplier: `targetSize / maxMacdValue`
  dove `targetSize = baseRange × 25%`. Il fattore è applicato uniformemente a tutte e 3 le componenti.
- Nel tooltip label: `MACD(12,26,9) [42×]` per indicare il fattore.
- Signal Line colore di default: eredita dalla card (era hardcoded #f59e0b amber).

### File modificati
- `frontend/src/lib/components/charts/LineChart.svelte` — `showGradient` nel $effect
- `frontend/src/lib/charts/signals/MacdSignal.ts` — yAxisIndex=0, auto-scale, default color
- `frontend/src/lib/components/charts/ChartSettingsModal.svelte` — Signal Line color fallback

---

## Step 4K — ✅ MACD scaleNote 2 decimali + Signal Line unified popover (10 Mar 2026)

### Bug 1: Moltiplicatore MACD arrotondato al primo intero nella leggenda
Il `scaleNote` nella label del tooltip MACD mostrava il multiplier arrotondato con `Math.round()`
(es. "2×" anziché "1.66×"). L'utente voleva vedere 2 cifre decimali per chiarezza.

**Fix**: In `MacdSignal.ts`, la funzione `scaleNote` ora usa sempre `.toFixed(2)` per qualsiasi
valore, eliminando il branch con `Math.round()`. Per valori ≥1000 usa `(v/1000).toFixed(2)k×`.

### Bug 2: Signal Line del MACD non usava lo stesso componente della MACD Line
La Signal Line nella card MACD aveva un controllo stile semplificato (3 pulsanti per lineType
e 3 per lineWidth, senza popover unificato e senza marker). L'utente voleva lo stesso
componente della riga MACD Line con il popover completo (start marker, line type/width, end marker).

**Soluzione**:
1. Rimosso completamente il vecchio blocco Signal Line (pulsanti stile/width inline)
2. Sostituito con layout **side-by-side**: 2 colonne flex identiche, una per MACD Line e una per Signal Line
3. Ogni colonna ha: label ("MACD Line" / "Signal Line"), color picker, SVG preview (con marker start/end + linea)
4. Cliccando sulla SVG preview si apre il popover unificato identico, con griglia 2×3 marker start, line type/width, griglia 2×3 marker end
5. Il popover MACD Line usa ID `signal.id + '-macd'`, il Signal Line usa `signal.id + '-signal'`
6. Il Row 3 originale (style strip generico) è ora skippato per `signal.signalType === 'macd'`
7. In `MacdSignal.ts`, aggiunti params `_signalMarkerStart` e `_signalMarkerEnd` (tipo `MarkerType`),
   propagati nel `RenderedSignal` output della Signal Line

**Le `{@const}` Svelte** per le variabili Signal Line (sigColor, sigLW, sigLT, sigMS, sigME) sono
wrappate in `{#if true}` perché Svelte richiede `{@const}` come figli diretti di blocchi logici,
non di elementi HTML.

### File modificati
- `frontend/src/lib/charts/signals/MacdSignal.ts` — scaleNote toFixed(2), +MarkerType import, +signalMarkerStart/End
- `frontend/src/lib/components/charts/ChartSettingsModal.svelte` — MACD side-by-side style rows with unified popovers

---

## Riepilogo file coinvolti

| Tipo | Categoria | Icona | Parametri | Asse Y | Note |
|------|-----------|-------|-----------|--------|------|
| `fx-pair` | comparison | 💱 | pairSlug, (invert) | 0 (primario/destra) | Dati reali dal backend |
| `linear` | benchmark | 📈 | annualRate, offset | 0 | Retta pendenza costante |
| `compound` | benchmark | 📊 | annualRate, offset | 0 | Crescita esponenziale iterativa |
| `sine` | benchmark | 〰️ | amplitude, period, offset | 0 | Oscillazione sinusoidale |
| `ema` | indicator | 📉 | period, offset | 0 | IIR low-pass 1° ordine |
| `macd` | indicator | 📶 | fastPeriod, slowPeriod, signalPeriod, histogramScale | **0** (primario, auto-scaled) | Band-pass, auto-bundle 3 segnali. histogramScale=0 → auto (15% del range base). Histogram: seriesType='bar' red/green |
| `rsi` | indicator | ⚡ | period, overbought, oversold | **1** (secondario, 0-100) | Duty-cycle, unico indicatore su asse secondario |
| `bollinger` | indicator | 📏 | period, multiplier, offset | 0 | Confidence band: Upper+Middle(SMA)+Lower, seriesType='band' |

---

## Nota dual-axis Y

L'asse Y secondario (indice 1) è posizionato a **destra**, visibile solo quando almeno un
segnale con `yAxisIndex === 1` è presente tra gli overlaySignals. L'asse primario (indice 0)
resta a **sinistra**.

Attualmente **solo RSI** usa l'asse secondario (scala 0-100, indipendente).

**MACD**: tutte e 3 le componenti (MACD Line, Signal Line, Histogram) usano l'asse primario (0)
con un multiplier auto-calcolato (`histogramScale=0` → auto). Il scale fa sì che i valori
MACD tiny (~0.001) vengano amplificati per occupare ~15% del range del dato base. Nel tooltip
le label includono `[Nx×]` per indicare il fattore di scala.

Tutti gli altri segnali (EMA, Bollinger, FX Pair, benchmark sintetici) condividono l'asse 0.

---

## Files Coinvolti (overview)

### Nuovi
| File | Descrizione |
|------|-------------|
| `frontend/src/lib/charts/signals/EMASignal.ts` | EMA indicator |
| `frontend/src/lib/charts/signals/MACDSignal.ts` | MACD indicator |
| `frontend/src/lib/charts/signals/RSISignal.ts` | RSI indicator |
| `frontend/src/lib/charts/signals/BollingerSignal.ts` | Bollinger Bands |
| `mkdocs_src/docs/financial-theory/technical-indicators.md` | Documentazione indicatori |
| `mkdocs_src/docs/financial-theory/synthetic-benchmarks.md` | Documentazione benchmark |

### Modificati
| File | Modifica |
|------|----------|
| `frontend/src/lib/charts/signals/ChartSignal.ts` | +`category`, +`yAxisIndex`, +`docsPath`, +`tooltip` in descriptor |
| `frontend/src/lib/charts/signals/LinearSignal.ts` | +`offset` param, +category, +docsPath |
| `frontend/src/lib/charts/signals/CompoundSignal.ts` | +`offset` param, +category, +docsPath |
| `frontend/src/lib/charts/signals/SineSignal.ts` | +category, +docsPath |
| `frontend/src/lib/charts/signals/FxPairSignal.ts` | +category, +docsPath |
| `frontend/src/lib/charts/signals/registry.ts` | +4 nuovi segnali, +category in `SignalTypeInfo` |
| `frontend/src/lib/charts/signals/index.ts` | +4 nuove export |
| `frontend/src/lib/components/charts/ChartSettingsModal.svelte` | Refactor synth data, 3 SimpleSelect categorie, tooltip, help button, FX selector custom |
| `frontend/src/lib/components/charts/LineChart.svelte` | Grid contrast fix, dual-axis Y |
| `frontend/src/lib/components/ui/Tooltip.svelte` | +html prop, +math prop (KaTeX) |
| `frontend/package.json` | +katex dependency |
| `frontend/src/lib/i18n/en.json` | +sezione `signals` |
| `frontend/src/lib/i18n/it.json` | +sezione `signals` |
| `frontend/src/lib/i18n/fr.json` | +sezione `signals` |
| `frontend/src/lib/i18n/es.json` | +sezione `signals` |
| `mkdocs_src/mkdocs.yml` | +2 pagine in nav |
| `mkdocs_src/docs/financial-theory/index.md` | +link ai nuovi articoli |

---

## Link ad altri plan

- **`plan-fxCardRedesignChartSettings.prompt.md`** — base del sistema segnali (Steps 1-6 done)
- **`plan-fxSyncApiRedesign.prompt.md`** — sync pair-based (da completare, indipendente)
- **`plan-phase05Fx.prompt.md`** — master plan Phase 5, aggiungere riferimento a questo plan
- **`plan-fxUiRefinementsRound2.prompt.md`** — Step 8 (settings ⚙️, overlay, benchmark) → coperto qui
- Le pagine MkDocs (Step 6) coprono anche il TODO §Documentazione del plan Phase 5

