# Plan: CandlestickChart + VolumeBar — Visualizzazione OHLCV

**Data**: 1 Giugno 2026
**Status**: ✅ DONE (2026-06-01)
**Priority**: P2 (feature visibile, dati OHLCV già nel DB)
**Tipo**: Independent mini-plan (frontend chart, no backend, no transazioni)

## 🤖 Modello Suggerito & Effort

| Parametro | Valore |
|-----------|--------|
| **Modello** | `claude-sonnet-4.6` |
| **Effort stimato** | ~5-6h |
| **Difficoltà** | Media |
| **Rationale** | Richiede creare un nuovo componente ECharts (sintassi candlestick non triviale), capire come `PriceChartFull` gestisce `chartType` e `overlaySignals`, e risolvere l'incognita Step 0 (struttura dati OHLCV). Il rischio principale è la compatibilità segnali secondari (RSI su yAxisIndex=1 in candlestick). Sonnet per la lettura di PriceChartFull (~1000 righe) e per scrivere il nuovo componente senza regressioni. |

---

## 🎯 Obiettivo

I dati OHLCV (Open/High/Low/Close/Volume) sono già salvati nel DB e modificabili dal Data Editor
nella detail page degli asset. Il toggle Line/Candlestick è già presente nell'UI (`ChartToolbar`)
ma è **bloccato** (`disableCandlestick={true}` in `PriceChartFull.svelte` riga 1012).

Questo plan:
1. Crea `CandlestickChart.svelte` (ECharts candlestick series)
2. Integra il volume bar sotto il grafico (nella stessa componente o separata)
3. Sblocca il toggle in `PriceChartFull.svelte` per gli asset (FX rimane bloccato)

---

## Stato Attuale (code-verified 2026-06-01)

| Componente | Stato |
|---|---|
| `ChartToolbar.svelte` — toggle Line/Candlestick | ✅ UI presente, tipo `'line'|'candlestick'` |
| `PriceChartFull.svelte` — `disableCandlestick` | ✅ Passato come `{true}` → toggle disabilitato |
| `CandlestickChart.svelte` | ❌ Non esiste |
| Dati OHLCV nel backend | ✅ `open`, `high`, `low`, `close`, `volume` in `FAHistoricalDataPoint` |
| Dati OHLCV nel frontend (chartData) | ⚠️ Verificare che `PriceChartFull` riceva OHLCV oltre a `close` |
| ECharts candlestick series | ✅ Supportato nativamente |

---

## Step 0 — Verifica struttura dati in `PriceChartFull`

✅ **DONE 2026-06-01** — `chartData` in assets `+page.svelte` contiene già `open/high/low/close/volume` dal backend. La derivazione `lineData` mappava solo `close`; aggiornata per includere tutti i campi OHLCV.

> **Note implementazione**: confermato che `FAHistoricalDataPoint` ha tutti i campi OHLCV. La `lineData` ora include `open/high/low/close/volume` come campi opzionali.

---

## Step 1 — Estendere `LineDataPoint` con campi OHLCV opzionali

✅ **DONE 2026-06-01**

> **Note implementazione**: aggiunti `open?, high?, low?, close?, volume?` a `LineDataPoint` in `LineChart.svelte`. Aggiornata la derivazione `lineData` in `assets/[id]/+page.svelte`.

---

## Step 2 — Creare `CandlestickChart.svelte`

✅ **DONE 2026-06-01** — `frontend/src/lib/components/charts/CandlestickChart.svelte` creato.

> **Note implementazione**: architettura a 2 grid (price + volume). yAxis[0/1/2] per price/RSI/MACD (identico a LineChart), yAxis[3] per volume su grid separato. Overlay signals mantengono il loro yAxisIndex originale. dataZoom sincronizzato su entrambi i grid. Tooltip custom con formato O/H/L/C + volume formattato (K/M). `actualShowVolume = showVolume && hasAnyVolume` per nascondere il volume grid se tutti i valori sono null (asset senza dati volume).

### Interfaccia Props

```typescript
interface Props {
    /** OHLCV data aligned to dateAxis */
    data: LineDataPoint[];
    /** Date strings for the x-axis */
    dateAxis: string[];
    /** Whether dark mode is active */
    isDark: boolean;
    /** Show volume bars (default: true) */
    showVolume?: boolean;
    /** Height in px (default: 400) */
    height?: number;
    /** Signal overlays (same RenderedSignal used by LineChart) */
    overlaySignals?: RenderedSignal[];
}
```

### Struttura ECharts

```typescript
// ECharts option per candlestick con volume
{
    grid: [
        { top: 10, bottom: showVolume ? '25%' : '10%', right: 60 },   // price grid
        { top: '80%', bottom: 20, right: 60 }                          // volume grid
    ],
    xAxis: [
        { type: 'category', data: dateAxis, gridIndex: 0 },
        { type: 'category', data: dateAxis, gridIndex: 1 }
    ],
    yAxis: [
        { type: 'value', scale: true, gridIndex: 0 },  // price
        { type: 'value', gridIndex: 1 }                // volume
    ],
    series: [
        {
            type: 'candlestick',
            data: data.map(d => [d.open, d.close, d.low, d.high]),  // ECharts format: [open, close, low, high]
            xAxisIndex: 0,
            yAxisIndex: 0,
            itemStyle: {
                color: greenColor,       // bullish candle fill
                color0: redColor,        // bearish candle fill
                borderColor: greenColor,
                borderColor0: redColor,
            }
        },
        // Volume bars (if showVolume)
        {
            type: 'bar',
            data: data.map(d => ({
                value: d.volume ?? 0,
                itemStyle: {
                    color: d.close >= d.open ? hexToRgba(greenColor, 0.5) : hexToRgba(redColor, 0.5)
                }
            })),
            xAxisIndex: 1,
            yAxisIndex: 1,
        }
    ]
}
```

> **Nota ECharts**: il formato candlestick è `[open, close, low, high]` (non OHLC standard).
> `color` = bullish (close > open), `color0` = bearish.

### Colori

Riusare le costanti da `lineChartHelpers.ts`:
```typescript
import {COLORS, hexToRgba} from './lineChartHelpers';
const greenColor = isDark ? COLORS.greenDark : COLORS.greenLight;
const redColor   = isDark ? COLORS.redDark   : COLORS.redLight;
```

### Gestione dati mancanti (OHLCV null)

Se un punto ha `open/high/low === null` (es. asset con dati solo close), mostrare `null` nella serie
ECharts (ECharts salta i null automaticamente).

### Overlay signals

Per i segnali overlay (EMA, ecc.) sulla candlestick view, montarli sulla stessa `gridIndex: 0`
con `xAxisIndex: 0, yAxisIndex: 0`. Stessa logica di `LineChart.svelte`.

---

## Step 3 — Integrare in `PriceChartFull.svelte`

✅ **DONE 2026-06-01**

> **Note implementazione**: aggiunto prop `disableCandlestick?: boolean` (default `false`) a `PriceChartFull`. ChartToolbar ora riceve `{disableCandlestick}` dal prop invece di `{true}` hardcoded. Switch `{#if chartType === 'line'}` / `{:else}` nel template mostra `CandlestickChart` in modalità candlestick.

```svelte
<!-- PRIMA -->
<ChartToolbar ... disableCandlestick={true} />

<!-- DOPO -->
<ChartToolbar ... disableCandlestick={false} />
```

### 3b — Switch condizionale nel template

```svelte
{#if chartType === 'line'}
    <LineChart
        overlaySignals={renderedSignals}
        ...
    />
{:else if chartType === 'candlestick'}
    <CandlestickChart
        data={chartData}
        dateAxis={chartData.map(d => d.date)}
        {isDark}
        showVolume={true}
        overlaySignals={renderedSignals}
    />
{/if}
```

### 3c — Persistenza preferenza chart type

Il `chartType` è già gestito in `PriceChartFull` come `$state`. Verificare se viene persistito
in `localStorage` (come `viewMode`). Se no, aggiungere persistenza opzionale per chiave
`librefolio-chart-type-{assetId}`.

---

## Step 4 — Aggiornare `charts/index.ts`

✅ **DONE 2026-06-01** — `export {default as CandlestickChart} from './CandlestickChart.svelte'` aggiunto.

---

## Step 5 — FX: confermare che rimane bloccato

✅ **DONE 2026-06-01** — `disableCandlestick={true}` aggiunto esplicitamente alla chiamata `<PriceChartFull>` in `fx/[pair]/+page.svelte`. La FX page usa anche `hideToolbar={true}` quindi il toggle è già nascosto, ma il prop garantisce protezione futura.

---

## Step 6 — Verifica

✅ **DONE 2026-06-01** — `svelte-check`: 0 errori nuovi. Gli errori pre-esistenti (fxStoreRegistry.test.ts x4, PromoteMergeModal.svelte x1) non sono correlati a questo piano.

---

## File Coinvolti (originali — vedi sezione finale per lista aggiornata)

| File | Modifica |
|------|----------|
| `frontend/src/lib/components/charts/LineChart.svelte` | ✅ Esteso `LineDataPoint` con OHLCV opzionali |
| `frontend/src/lib/components/charts/CandlestickChart.svelte` | ✅ **NUOVO** — componente principale |
| `frontend/src/lib/components/charts/chartCoreHelpers.ts` | ✅ **NUOVO** — shared helpers (refactor) |
| `frontend/src/lib/components/charts/index.ts` | ✅ Export `CandlestickChart` |
| `frontend/src/lib/components/charts/PriceChartFull.svelte` | ✅ Refactored, usa chartCoreHelpers |
| `frontend/src/routes/(app)/assets/[id]/+page.svelte` | ✅ `lineData` include campi OHLCV + chartType state |
| `frontend/src/routes/(app)/fx/[pair]/+page.svelte` | ✅ `disableCandlestick={true}` esplicito |

---

## Note Architetturali

- **Dati OHLCV**: ✅ verificato (code-verified 2026-06-01): `chartData` contiene già `open/high/low/close/volume` dal backend. Basta estendere `lineData`.
- **Componente separato vs switch interno**: componente separato `CandlestickChart.svelte` (più pulito, LineChart non diventa un "super-componente").
- **Signals su candlestick**: i segnali secondari (RSI su yAxisIndex=1, MACD su yAxisIndex=2) vengono **mantenuti** — stessa struttura di yAxis di LineChart. Il volume usa yAxis[3] su un grid separato, così nessun conflitto.
- **`disableCandlestick` come prop di `PriceChartFull`** (aggiunta al piano originale): invece di hardcodare `false`, aggiungere prop con default `false` — la FX page passa esplicitamente `true`.

### Struttura ECharts (aggiornata, rev 2)

```
grid[0]: price  (top ~75%)
  yAxis[0] = price, scale:true
  yAxis[1] = RSI  (right, secondary — identico a LineChart)
  yAxis[2] = MACD (right+offset, tertiary — identico a LineChart)
  xAxis[0] = date categories
  series: candlestick(yAxisIndex=0) + overlay signals(yAxisIndex=0/1/2 originali)

grid[1]: volume (bottom ~20%, se showVolume)
  yAxis[3] = volume (hidden, auto-scale)
  xAxis[1] = date categories
  series: volume bars (yAxisIndex=3, xAxisIndex=1)

dataZoom: inside, xAxisIndex=[0,1]  ← zoom sincronizzato su entrambi i grid
```

---

## Post-Implementation: Bugfix & Refactor (2026-06-01)

Dopo il test dell'utente, diverse iterazioni di fix:

### Bugfix Round 1
| Issue | Fix |
|-------|-----|
| Toggle posizione errata (era in barra azioni) | Spostato a overlay floating top-left dentro PriceChartFull, con icone `ChartLine`/`ChartCandlestick` (lucide), opacity-75, margin-left per non coprire yAxis label |
| Abs/% non funziona su candele | Aggiunto `viewMode` prop → trasforma OHLCV con `pct()` function, y-axis mostra `%` suffix |
| Candele spaziate tra loro | `barWidth: '80%'` sulla serie candlestick |

### Bugfix Round 2
| Issue | Fix |
|-------|-----|
| Candle→Line = schermo bianco | `chartInstance.getDom() !== chartContainer` → dispose + re-init (stale reference) |
| Measure mode non funziona in candela | Aggiunti `measureMode`, `onMeasureClick`, `onMeasureHover` props con click/mousemove handlers |
| Tooltip caotico | Ristrutturato con CSS grid (O/H/L/C righe), smart price formatting, asset name+icon header |
| Settings inapplicabili | `disabledFields: Set<string>` in ChartAestheticsSection → `opacity-40 pointer-events-none` per colorByBaseline, areaFill, staleGradient |

### Bugfix Round 3
| Issue | Fix |
|-------|-----|
| include0 distorce in % | Rimosso `min: 0` hardcoded → solo `scale: !isInclude0` (come line chart) |
| yAxis settings non funzionano | Aggiunti `yAxisMode`/`yAxisMin`/`yAxisMax` props a CandlestickChart |

### Bugfix Round 4
| Issue | Fix |
|-------|-----|
| Double-click in candela non scrolla l'editor alla riga | Aggiunto `onDblClick` prop + handler `getZr().on('dblclick')` in CandlestickChart, passato da PriceChartFull |
| Double-click su volume grid non funziona | Handler dblclick ora controlla sia `gridIndex: 0` che `gridIndex: 1` |
| Asset con solo close (no OHLCV) → pagina bianca | Sintetizza candele: `open = prev close`, `high/low = max/min(open, close)`. Ogni campo DB ha priorità sul calcolato |
| Possibile inserire valori negativi in prezzi/volumi | Frontend: `min` prop su ErasableNumberCell + clamp in commit(). Backend: validator su FAPricePoint rifiuta negativi (eccetto sentinel -1) |

### Refactor: `chartCoreHelpers.ts` (NEW)

Creato `frontend/src/lib/components/charts/chartCoreHelpers.ts` (~297 righe) per eliminare duplicazione tra PriceChartFull e CandlestickChart:

| Helper | Scopo |
|--------|-------|
| `buildPriceYAxis()` | yAxis primario con mode auto/include0/custom |
| `buildSecondaryYAxes()` | Assi RSI + MACD (indices 1,2) |
| `buildOverlaySignalSeries()` | Serie line/band/bar per segnali overlay con markers |
| `buildDataZoom()` | Config zoom inside |
| `computeRightMargin()` | Margine grid da numero assi extra |
| `getChartColors()` | Palette dark/light |

**Risultato**: PriceChartFull 1081 → 934 righe (−147). Qualunque fix a yAxis/overlay si applica automaticamente a entrambi i grafici.

---

## File Coinvolti (aggiornamento finale)

| File | Modifica |
|------|----------|
| `frontend/src/lib/components/charts/LineChart.svelte` | ✅ Esteso `LineDataPoint` con OHLCV opzionali |
| `frontend/src/lib/components/charts/CandlestickChart.svelte` | ✅ **NUOVO** — ~450 righe, usa chartCoreHelpers |
| `frontend/src/lib/components/charts/chartCoreHelpers.ts` | ✅ **NUOVO** — shared helpers (~297 righe) |
| `frontend/src/lib/components/charts/index.ts` | ✅ Export `CandlestickChart` |
| `frontend/src/lib/components/charts/PriceChartFull.svelte` | ✅ Refactored (−147 righe), usa chartCoreHelpers |
| `frontend/src/lib/components/charts/ChartAestheticsSection.svelte` | ✅ `disabledFields` prop |
| `frontend/src/lib/components/charts/ChartToolbar.svelte` | ✅ data-testid attributes |
| `frontend/src/routes/(app)/assets/[id]/+page.svelte` | ✅ chartType state, hasOhlcv, disabledAesthetics |
| `frontend/src/routes/(app)/fx/[pair]/+page.svelte` | ✅ `disableCandlestick={true}` esplicito |
| `frontend/e2e/assets/asset-detail.spec.ts` | ✅ Test 17 & 18 (toggle + no-error) |

---

## Rischi

- **Step 0 ✅ risolto**: OHLCV è già in `chartData` dal backend.
- **Basso — Segnali overlay**: compatibilità mantenuta con yAxis[3] per volume separato.
- **Basso — `disableCandlestick` prop**: aggiunta prop a `PriceChartFull`, FX page passa `true`.
