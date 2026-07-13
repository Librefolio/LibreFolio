# Piano Implementativo: Fondazione `timeSeriesAggregation.ts` (Milestone_3 — Step 0)

> **Stato: ✅ implementato** — `frontend/src/lib/components/charts/timeSeriesAggregation.ts` esiste con
> test dedicati (`timeSeriesAggregation.test.ts`, 22 test). Contratto condiviso in uso dai 6 documenti
> fratelli, tutti implementati (vedi rispettivi header di stato).

> **Deriva da**: [`./study_chart_dynamic_resolution.md`](./study_chart_dynamic_resolution.md), con riferimento operativo prioritario alle sezioni **1-12**, **17**, **19-21** della parte raffinata (righe 256-1481).
> **Documento fondativo**: questo file fissa il contratto tecnico condiviso per i 5 documenti fratelli scritti in parallelo: [`./impl_plan_chart_resolution_01_price_candlestick.md`](./impl_plan_chart_resolution_01_price_candlestick.md) · [`./impl_plan_chart_resolution_02_growth_chart.md`](./impl_plan_chart_resolution_02_growth_chart.md) · [`./impl_plan_chart_resolution_03_allocation_history.md`](./impl_plan_chart_resolution_03_allocation_history.md) · [`./impl_plan_chart_resolution_04_signals_overlay.md`](./impl_plan_chart_resolution_04_signals_overlay.md) · [`./impl_plan_chart_resolution_05_badge_i18n.md`](./impl_plan_chart_resolution_05_badge_i18n.md).
> **Ambito**: solo progettazione del nuovo modulo condiviso `frontend/src/lib/components/charts/timeSeriesAggregation.ts`. Nessun codice sorgente viene toccato in questo task.

## Principio guida

> Un solo modulo puro condiviso per bucketing + aggregazione + scelta risoluzione; **nessun nuovo store singleton globale** per le viste derivate. Le aggregazioni weekly/monthly vivono come memoizzazione locale del componente, invalidata quando cambia il riferimento dell'array sorgente già ricaricato dal parent.

Ogni step sotto dichiara esplicitamente cosa è **Nuovo** vs cosa è **Riuso**.

## Stato attuale

- **Riuso — cache fetch già esistente, ma a livello daily/raw**: `TimeSeriesStore<T>` è una cache client-side generica per serie temporali con `Map<string, T>`, gap-detection, merge e invalidazione; non contiene alcun concetto di bucket weekly/monthly o aggregazioni derivate (`frontend/src/lib/stores/core/TimeSeriesStore.ts:2-15`, `frontend/src/lib/stores/core/TimeSeriesStore.ts:72-222`).
- **Riuso — registry globale già esistente per prezzi asset**: `assetPriceStoreRegistry.ts` mantiene una `Map<string, TimeSeriesStore<AssetPricePoint>>` keyed per `(assetId, currency)` e usa il backend solo per colmare i gap; anche qui nessuna cache di aggregazione derivata (`frontend/src/lib/stores/assetPriceStoreRegistry.ts:2-10`, `frontend/src/lib/stores/assetPriceStoreRegistry.ts:44-60`, `frontend/src/lib/stores/assetPriceStoreRegistry.ts:123-152`).
- **Riuso — i componenti ricevono già array “freschi” dal parent**:
  - pagina asset: `loadChartData()` rilegge cache/backend, riassegna `chartData`, deriva `lineData` e passa `data={lineData}` a `PriceChartFull` (`frontend/src/routes/(app)/assets/[id]/+page.svelte:191-206`, `frontend/src/routes/(app)/assets/[id]/+page.svelte:866-919`, `frontend/src/routes/(app)/assets/[id]/+page.svelte:1695-1728`);
  - dashboard/broker detail: `GrowthChart` riceve `history` come prop (`frontend/src/lib/components/dashboard/GrowthChart.svelte:32-39`, `frontend/src/routes/(app)/dashboard/+page.svelte:527-536`, `frontend/src/routes/(app)/brokers/[id]/+page.svelte:482-490`);
  - allocation: `AllocationHistoryChart` riceve `data` come prop via `AllocationPanel` (`frontend/src/lib/components/dashboard/AllocationHistoryChart.svelte:36-45`, `frontend/src/lib/components/dashboard/AllocationHistoryChart.svelte:116-129`, `frontend/src/lib/components/dashboard/AllocationPanel.svelte:103-109`).
- **Riuso — `PriceChartFull` ha già i ganci ECharts minimi, ma non la logica semantica**:
  - ascolta già `dataZoom`, oggi solo per `updateArrowRotations()` (`frontend/src/lib/components/charts/PriceChartFull.svelte:369-372`);
  - salva/ripristina lo zoom via percentuali `savedZoom.start/end` (`frontend/src/lib/components/charts/PriceChartFull.svelte:675-714`);
  - ha già `animation: false` globale (`frontend/src/lib/components/charts/PriceChartFull.svelte:700-714`).
- **Riuso — la colorazione baseline è già custom e agnostica rispetto alla spaziatura temporale**: `buildMainSeries()` lavora solo su `values[]` + `staleDays[]`, costruisce segmenti per colore/opacità e non usa `visualMap`; quindi può ricevere dati aggregati senza cambiare algoritmo (`frontend/src/lib/components/charts/lineChartHelpers.ts:118-158`, `frontend/src/lib/components/charts/lineChartHelpers.ts:160-240`).
- **Riuso — `chartInstance.getWidth()` è già API disponibile e già usata nel codebase** (`frontend/src/lib/components/charts/echartsTreemapZoomGuard.ts:126-132`).
- **Nota di contesto per i documenti 02/03**: `GrowthChart` e `AllocationHistoryChart` oggi usano `...CHART_ANIMATION_CONFIG` (che abilita `animation: true`) insieme a `dataZoom: inside`; quindi la regola “switch senza animazione” è già soddisfatta in `PriceChartFull`, ma va verificata/adattata nei documenti dedicati ai chart dashboard (`frontend/src/lib/components/charts/echartsAnimationConfig.ts:27-38`, `frontend/src/lib/components/dashboard/GrowthChart.svelte:372-455`, `frontend/src/lib/components/dashboard/AllocationHistoryChart.svelte:235-279`).

## Gap

- **Nuovo al 100%**: il file `frontend/src/lib/components/charts/timeSeriesAggregation.ts` non esiste oggi (verifica file system: nessun match).
- **Nuovo al 100%**: nel frontend non esistono ancora `ChartResolution`, `BucketMeta`, `mapDateToBucket`, `aggregateLineSeries`, `aggregateOHLCV`, `aggregateEnvelope`, `downsampleRenderedSignal`, `computeDensity`, `chooseResolution`, `bucketEventMarkers` (grep globale: nessun match in `frontend/src`).
- **Gap architetturale**: lo zoom è oggi preservato con percentuali `start/end`; questo si rompe appena il numero di punti cambia passando daily → weekly/monthly (`frontend/src/lib/components/charts/PriceChartFull.svelte:675-714`).
- **Gap funzionale**: non esiste ancora una semantica condivisa per:
  - bucket ISO week / calendar month;
  - aggregazione fine-periodo per linee/NAV/allocazione;
  - aggregazione OHLCV standard;
  - envelope Bollinger;
  - marker eventi bucket-aware;
  - densità `bucket/px` + isteresi;
  - preservazione range logico con date assolute.

## Contratto tecnico canonico del nuovo modulo

```ts
// Nuovo file: frontend/src/lib/components/charts/timeSeriesAggregation.ts
export type ChartResolution = 'daily' | 'weekly' | 'monthly';

interface BucketMeta {
  bucketStart: string; bucketEnd: string; // ISO date — bucketEnd = data rappresentativa del punto aggregato
  resolution: ChartResolution;
  sourcePointCount: number;
}

function mapDateToBucket(date: string, resolution: ChartResolution): {bucketStart: string; bucketEnd: string};
function aggregateLineSeries(points: LineDataPoint[], resolution: ChartResolution): LineDataPoint[]; // regola fine-periodo
function aggregateOHLCV(points: LineDataPoint[], resolution: ChartResolution): LineDataPoint[]; // open=primo,close=ultimo,high/low=max/min,volume=somma
function aggregateEnvelope(upper: number[], middleData: LineDataPoint[], lower: number[], resolution: ChartResolution): {upper:number[]; middle:LineDataPoint[]; lower:number[]}; // SOLO Bollinger (doc 04)
function downsampleRenderedSignal(signal: RenderedSignal, resolution: ChartResolution, bucketedDates: string[]): RenderedSignal; // dispatcher per tipo — dettagliato in doc 04, qui solo la firma/contratto
function computeDensity(bucketCount: number, plotWidthPx: number): number; // bucket/px
function chooseResolution(current: ChartResolution, counts: {dailyCount: number; weeklyCount: number; monthlyCount: number}, plotWidthPx: number): ChartResolution; // applica isteresi internamente — vedi §7.2 per perché servono tutti e 3 i conteggi
function bucketEventMarkers<M extends {date:string}>(markers: M[], resolution: ChartResolution): Map<string, M[]>; // key = bucketEnd
```

### Nota tipizzazione

- **Nuovo**: `BucketMeta` è vocabolario canonico inter-documento.
- **Riuso compatibile**: le funzioni che restituiscono `LineDataPoint[]` mantengono la firma pubblica compatibile coi consumer esistenti; i punti aggregati possono essere oggetti strutturalmente più ricchi (`LineDataPoint & BucketMeta`) senza rompere la compatibilità TypeScript dei call-site esistenti.

## Decisioni prese (non più aperte)

| Decisione | Scelta |
|---|---|
| Bucket settimanale | **Settimana ISO**: lunedì → domenica |
| Bucket mensile | **Mese di calendario**: giorno 1 → ultimo giorno del mese |
| Valore serie linea / NAV / allocazione | **Fine-periodo**: ultimo giorno disponibile nel bucket |
| Candlestick | `open=primo`, `close=ultimo`, `high/low=max/min`, `volume=somma` |
| Bollinger | `upper=max(bucket)`, `middle=end-date`, `lower=min(bucket)` |
| `staleDays` aggregato | Stesso end-date del valore mostrato |
| Colore verde/rosso baseline | Stessa regola end-date del valore mostrato; nessuna logica separata |
| Soglia alta densità | **1.30 bucket/px** |
| Soglia bassa densità | **0.80 bucket/px** |
| Misura larghezza plot | `chartInstance.getWidth()` |
| Debounce `dataZoom` | **200 ms** |
| Switch risoluzione | **Nessuna animazione** |
| Preservazione zoom logico | **Date assolute** `visibleStartDate` / `visibleEndDate`, non percentuali |
| Cache aggregazioni derivate | **Aggiornato dopo lettura codebase**: memoizzazione locale al componente keyed by `resolution`, invalidata quando cambia il riferimento dell'array sorgente; **nessun nuovo store globale singleton** |
| LTTB / sampling ECharts | Invariato; fuori scope di questo modulo |

## Ordine di implementazione

```text
STEP 0 (questo documento, fondazione condivisa)
  └─ timeSeriesAggregation.ts
      ├─ tipi canonici + bucket metadata
      ├─ mapDateToBucket()
      ├─ aggregateLineSeries()
      ├─ aggregateOHLCV()
      ├─ aggregateEnvelope()
      ├─ downsampleRenderedSignal()
      ├─ computeDensity() + chooseResolution()
      └─ bucketEventMarkers()
             │
             ├─ STEP 1 → doc 01 Price/Candlestick
             ├─ STEP 2 → doc 02 GrowthChart
             ├─ STEP 3 → doc 03 AllocationHistoryChart
             ├─ STEP 4 → doc 04 Signals/Overlay/Eventi
             └─ STEP 5 → doc 05 Badge/i18n
```

Questo modulo è il **prerequisito concettuale** degli altri 5 documenti: i consumer possono divergere nel wiring ECharts, ma non nel vocabolario (`ChartResolution`, `BucketMeta`, `bucketEnd`, soglie, debounce, end-period semantics).

---

## STEP 1 — Tipi canonici + strategia cache locale

### 1.1 `ChartResolution`

- **Nuovo**: union canonica `'daily' | 'weekly' | 'monthly'`.
- **Regola**: nessun alias (`day`, `week`, `month`, `1W`, `1M`) dentro il codice condiviso.

### 1.2 `BucketMeta`

- **Nuovo**: metadato standard da allegare ai punti aggregati.
- Campi obbligatori:
  - `bucketStart`: inizio bucket logico;
  - `bucketEnd`: data rappresentativa del punto aggregato (= ultimo punto disponibile nel bucket);
  - `resolution`: risoluzione del punto aggregato;
  - `sourcePointCount`: numero di punti sorgente confluiti nel bucket.

Esempio atteso:

```ts
{
  date: '2026-01-31',
  value: 123.45,
  bucketStart: '2026-01-01',
  bucketEnd: '2026-01-31',
  resolution: 'monthly',
  sourcePointCount: 22
}
```

### 1.3 Memoizzazione locale, non store globale

- **Riuso**: i parent già ricaricano e riassegnano gli array sorgente (`chartData`/`lineData`, `history`, `allocationHistoryData`) quando cambiano asset, broker, valuta, periodo o refresh (`frontend/src/routes/(app)/assets/[id]/+page.svelte:866-919`, `frontend/src/routes/(app)/dashboard/+page.svelte:527-536`, `frontend/src/routes/(app)/brokers/[id]/+page.svelte:482-490`, `frontend/src/lib/components/dashboard/AllocationPanel.svelte:103-109`).
- **Decisione**: ogni chart mantiene cache locale del tipo:

```ts
lastSourceRef
aggregatedByResolution: Map<ChartResolution, ...>
```

- **Invalidazione**:
  - se `data !== lastSourceRef` / `history !== lastSourceRef` → `clear()` completo;
  - se cambia solo zoom/pan/resize → riuso cache già calcolata;
  - nessun nuovo singleton condiviso tra componenti.

Motivo: il livello `TimeSeriesStore<T>` esistente è cache di **fetch daily raw**, non cache di **aggregazione derivata** (`frontend/src/lib/stores/core/TimeSeriesStore.ts:2-15`, `frontend/src/lib/stores/assetPriceStoreRegistry.ts:44-60`).

---

## STEP 2 — `mapDateToBucket(date, resolution)`

- **Nuovo**: utility pura condivisa.
- **Riuso**: input/output ISO `YYYY-MM-DD`, coerente con tutto il codebase chart/store (`frontend/src/lib/stores/core/TimeSeriesStore.ts:24-33`, `frontend/src/routes/(app)/assets/[id]/+page.svelte:191-206`).

### Comportamento atteso

- `daily`:
  - `bucketStart = date`
  - `bucketEnd = date`
- `weekly`:
  - bucket ISO lunedì → domenica
- `monthly`:
  - giorno 1 → ultimo giorno del mese di calendario

### Esempi

```ts
mapDateToBucket('2026-01-05', 'daily')
// {bucketStart:'2026-01-05', bucketEnd:'2026-01-05'}

mapDateToBucket('2026-01-07', 'weekly')
// {bucketStart:'2026-01-05', bucketEnd:'2026-01-11'}

mapDateToBucket('2026-01-07', 'monthly')
// {bucketStart:'2026-01-01', bucketEnd:'2026-01-31'}
```

### Edge case fissati

- input sempre interpretato in UTC/logica ISO date, mai timezone locale;
- attraversamento anno ISO gestito correttamente (`2025-12-31` può appartenere alla ISO week che chiude nel 2026);
- nessun bucket “vuoto” viene creato qui: la funzione mappa una data reale a un bucket logico, non materializza serie.

### Nota importante

Per i punti aggregati finali, `BucketMeta.bucketEnd` coincide con l’**ultimo punto disponibile del bucket**; quindi il consumer dell’aggregazione userà `bucketStart` dal bucket logico e `bucketEnd` come representative date reale del dato aggregato.

---

## STEP 3 — `aggregateLineSeries(points, resolution)`

- **Nuovo**: aggregatore condiviso per prezzo linea, NAV, baseline, serie cumulative, allocation fine-periodo.
- **Riuso**: la regola end-periodo è coerente con lo studio raffinato e con la vista candlestick.

### Comportamento atteso

- `daily` → ritorna i punti originali, stesso ordine, nessun clone inutile;
- `weekly` / `monthly`:
  - raggruppa per bucket;
  - conserva **solo l’ultimo punto disponibile** del bucket come valore mostrato;
  - copia nel punto aggregato tutti i campi puntuali che seguono la stessa semantica di fine-periodo (`value`, `staleDays`, `fxStaleDays`, `originalValue`, `originalCurrency`, ecc.);
  - allega `BucketMeta`.

### Esempio

Input:

```ts
[
  {date:'2026-01-05', value:100, staleDays:0},
  {date:'2026-01-06', value:98,  staleDays:0},
  {date:'2026-01-09', value:105, staleDays:2}
]
```

Output weekly:

```ts
[
  {
    date:'2026-01-09',
    value:105,
    staleDays:2,
    bucketStart:'2026-01-05',
    bucketEnd:'2026-01-09',
    resolution:'weekly',
    sourcePointCount:3
  }
]
```

### Edge case fissati

- bucket con **1 solo punto** → quel punto diventa il bucket aggregato;
- bucket senza punti → **non viene emesso**;
- range logico che parte/finisce nel mezzo del bucket → il bucket è comunque valido se contiene almeno un punto; il range renderizzato potrà quindi “espandersi” al bucket che interseca il range logico;
- input già ordinato per data: il modulo può assumerlo e non re-sortare ad ogni passaggio.

### Motivazione baseline/staleness

La scelta end-periodo vale anche per colore verde/rosso e `staleDays`, perché `buildMainSeries()` segmenta in base a `values[]` + `staleDays[]` senza assumere spaziatura temporale e senza `visualMap` nativo (`frontend/src/lib/components/charts/lineChartHelpers.ts:118-158`, `frontend/src/lib/components/charts/lineChartHelpers.ts:160-240`).

---

## STEP 4 — `aggregateOHLCV(points, resolution)`

- **Nuovo**: aggregatore condiviso per la vista candlestick.
- **Riuso**: `LineDataPoint` porta già `open/high/low/close/volume` nel dettaglio asset (`frontend/src/routes/(app)/assets/[id]/+page.svelte:191-206`).

### Comportamento atteso

- `daily` → ritorna i punti originali;
- `weekly` / `monthly`:
  - `open` = primo `open` disponibile del bucket;
  - `close` = ultimo `close` disponibile del bucket;
  - `high` = massimo `high` del bucket;
  - `low` = minimo `low` del bucket;
  - `volume` = somma dei `volume` numerici del bucket;
  - `date` = stesso valore di `bucketEnd` rappresentativo;
  - `value` = `close` aggregato, per mantenere coerenza col resto del sistema;
  - allega `BucketMeta`.

### Edge case fissati

- bucket con un solo punto → `open/high/low/close` di quel punto;
- se tutti i `volume` del bucket sono `null`, il `volume` aggregato resta `null` (non `0`);
- se alcuni `volume` sono `null`, si sommano solo i valori numerici disponibili;
- nessuna interpolazione di giorni mancanti.

---

## STEP 5 — `aggregateEnvelope(upper, middleData, lower, resolution)`

- **Nuovo**: helper dedicato **solo** a Bollinger.
- **Riuso**: regola envelope dal raffinamento, non da estendere ad altri segnali.

### Comportamento atteso

- `daily` → ritorna input invariato;
- `weekly` / `monthly`:
  - `middle` passa da `aggregateLineSeries(middleData, resolution)` perché segue end-periodo;
  - `upper` = max dei valori del bucket;
  - `lower` = min dei valori del bucket;
  - gli array risultanti devono allinearsi 1:1 ai bucket di `middle`.

### Esempio

```ts
upper  = [110, 112, 111]
middle = [
  {date:'2026-01-05', value:100},
  {date:'2026-01-06', value:101},
  {date:'2026-01-09', value:105}
]
lower  = [90, 89, 92]
```

Output weekly:

```ts
{
  upper:  [112],
  middle: [{date:'2026-01-09', value:105, ...BucketMeta}],
  lower:  [89]
}
```

### Edge case fissati

- lunghezze array disallineate → non supportate; il caller deve inviare dataset coerenti;
- bucket con un solo punto → `upper == middle.value == lower` se i tre valori coincidono nel sorgente di quel giorno.

---

## STEP 6 — `downsampleRenderedSignal(signal, resolution, bucketedDates)`

- **Nuovo**: dispatcher condiviso.
- **Riuso**: la matematica dei segnali resta daily; qui si tocca solo l’**output già renderizzato** (`./study_chart_dynamic_resolution.md`, sez. 16-17).

### Contratto fissato qui

- `daily` → ritorna `signal` invariato;
- `weekly` / `monthly`:
  - linea singola / RSI / EMA / comparison / FX / MACD lines → fine-periodo;
  - istogramma MACD → fine-periodo, non somma;
  - Bollinger → usa `aggregateEnvelope()`;
  - output finale allineato a `bucketedDates` del grafico principale.

### Regole di preservazione

- preservare `label`, `color`, `seriesType`, `yAxisIndex` e ogni metadata non dipendente dal sampling;
- rimuovere eventuali punti che non trovano più un bucket nella vista corrente;
- nessun ricalcolo dell’indicatore matematico dentro questa funzione.

### Confine esplicito con il doc 04

Questo documento fissa **solo firma + semantica**; i dettagli per ogni shape concreta di `RenderedSignal` vengono completati nel documento `04_signals_overlay`.

---

## STEP 7 — `computeDensity(bucketCount, plotWidthPx)` + `chooseResolution(current, counts, plotWidthPx)`

- **Nuovo**: policy helper condivisa.
- **Riuso**: la larghezza arriva da `chartInstance.getWidth()` già disponibile in ECharts e già usata nel repo (`frontend/src/lib/components/charts/echartsTreemapZoomGuard.ts:126-132`).

### 7.1 `computeDensity()`

Formula canonica:

```ts
density = bucketCount / plotWidthPx
```

Regole:

- se `plotWidthPx <= 0`, ritornare `0` per evitare divisioni anomale in fase di mount/hidden container;
- unità sempre `bucket/px`.

### 7.2 `chooseResolution()`

> **Corretto dopo audit incrociato dei 7 documenti derivati** (vedi `impl_plan_chart_resolution_01_price_candlestick.md`,
> `_02_growth_chart.md`, `_03_allocation_history.md`): la firma precedente (`current`, `dailyPointCount`,
> `plotWidthPx`) era sottospecificata — la transizione `current='weekly'` deve valutare **contemporaneamente**
> `densityDaily` (per l'eventuale downgrade a `daily`) e `densityWeekly` (per l'eventuale upgrade a `monthly`):
> un solo conteggio non basta a calcolare entrambe. La firma ora accetta i 3 conteggi bucket rilevanti per il
> range visibile corrente.

Regola di stato:

```text
HIGH = 1.30
LOW  = 0.80
```

Input: `counts.dailyCount` / `counts.weeklyCount` / `counts.monthlyCount` — il numero di bucket ottenuti
raggruppando le STESSE date giornaliere visibili con `mapDateToBucket()` per ciascuna risoluzione candidata.
**Non** sono un'approssimazione aritmetica (`dailyCount/7`, `dailyCount/30`): vanno calcolati raggruppando
realmente le date con la stessa funzione di bucketing usata altrove, per evitare errori ai bordi del range
(settimane/mesi parziali all'inizio/fine). Il caller (doc 01/02/03) calcola i 3 conteggi una sola volta per
range visibile (`O(N)`, stesso costo di un singolo passaggio sui dati già in memoria) e li passa tutti e 3;
`chooseResolution()` sceglie internamente quali confrontare in base a `current`:

Transizioni canoniche:

```text
current=daily
  densityDaily = computeDensity(counts.dailyCount, plotWidthPx)
  if densityDaily > HIGH → weekly
  else stay daily

current=weekly
  densityDaily  = computeDensity(counts.dailyCount, plotWidthPx)
  densityWeekly = computeDensity(counts.weeklyCount, plotWidthPx)
  if densityDaily < LOW → daily
  else if densityWeekly > HIGH → monthly
  else stay weekly

current=monthly
  densityWeekly = computeDensity(counts.weeklyCount, plotWidthPx)
  if densityWeekly < LOW → weekly
  else stay monthly
```

### Nota semantica sul parametro `counts`

I 3 conteggi sono sempre disponibili senza costo aggiuntivo significativo: il caller ha già in memoria
l'array giornaliero completo del range visibile (per costruire `resolvedData`), quindi calcolare
`mapDateToBucket()` su di esso per week/month è un singolo passaggio O(N) già necessario altrove (es. per
costruire `resolvedData` stesso quando la risoluzione scelta non è `daily`). Nessun secondo nome di parametro
divergente tra i documenti 01/02/03: tutti e 3 useranno `counts.{dailyCount,weeklyCount,monthlyCount}`.

### Regole operative fissate

- debounce `dataZoom`: **200ms**;
- primo render: scegliere la risoluzione **prima** del primo `setOption`;
- nessun ricalcolo a ogni tick di zoom: solo dopo il debounce;
- switch senza animazione:
  - già soddisfatto in `PriceChartFull` (`animation: false`, `frontend/src/lib/components/charts/PriceChartFull.svelte:700-714`);
  - da verificare/adeguare in `GrowthChart` e `AllocationHistoryChart`, che oggi partono da `CHART_ANIMATION_CONFIG` (`frontend/src/lib/components/charts/echartsAnimationConfig.ts:32-38`, `frontend/src/lib/components/dashboard/GrowthChart.svelte:372-455`, `frontend/src/lib/components/dashboard/AllocationHistoryChart.svelte:235-279`).

---

## STEP 8 — `bucketEventMarkers<M extends {date:string}>(markers, resolution)`

- **Nuovo**: helper condiviso per marker dividendi/interessi/split e futuri eventi bucket-aware.
- **Riuso**: i marker chart esistenti sono già keyed da `date` (`frontend/src/lib/components/charts/PriceChartFull.svelte:28-46`, `frontend/src/routes/(app)/assets/[id]/+page.svelte:578-640`).

### Comportamento atteso

- `daily`:
  - `Map` con key = data reale evento;
- `weekly` / `monthly`:
  - ogni marker finisce nel bucket che contiene la sua `date`;
  - key della `Map` = `bucketEnd` rappresentativo del bucket aggregato;
  - value = array di marker originali ordinati per `date` ascendente.

### Esempio

```ts
bucketEventMarkers(
  [
    {date:'2026-01-05', type:'DIVIDEND'},
    {date:'2026-01-12', type:'DIVIDEND'},
    {date:'2026-01-21', type:'SPLIT'}
  ],
  'monthly'
)

// Map {
//   '2026-01-31' => [
//     {date:'2026-01-05', ...},
//     {date:'2026-01-12', ...},
//     {date:'2026-01-21', ...}
//   ]
// }
```

### Edge case fissati

- nessun marker → `new Map()` vuota;
- più eventi nello stesso bucket → nessuna deduplica, tutti preservati;
- la data reale non si perde: cambia solo la coordinata X renderizzata.

---

## STEP 9 — Regola trasversale: range logico vs range renderizzato

- **Riuso problematico da correggere nei consumer**: oggi `PriceChartFull` salva lo zoom come percentuali `start/end` (`frontend/src/lib/components/charts/PriceChartFull.svelte:675-714`).
- **Decisione fondativa**:
  - stato logico = `visibleStartDate` / `visibleEndDate`;
  - stato renderizzato = bucket che intersecano quel range nella risoluzione corrente.

Esempio canonico:

```text
visibleStartDate = 2026-01-05
visibleEndDate   = 2026-09-20
resolution       = monthly

range logico      = 2026-01-05 → 2026-09-20
range renderizzato = bucket gennaio 2026 → bucket settembre 2026
```

Motivazione: `50%-100%` su 100 punti daily non equivale a `50%-100%` su 20 punti monthly; quindi la preservazione percentuale è intrinsecamente instabile quando cambia la cardinalità della serie.

---

## Riepilogo Nuovo vs Riuso

- **Nuovo**: `timeSeriesAggregation.ts` intero, tutte le firme del contratto, semantica bucket-aware, policy densità/isteresi, bucketing marker, envelope Bollinger.
- **Riuso**:
  - `TimeSeriesStore<T>` / registry esistenti come livello raw-daily;
  - `buildMainSeries()` invariato;
  - `chartInstance.getWidth()` nativo;
  - parent component già responsabili di refresh/invalidation dati sorgente;
  - LTTB / sampling ECharts invariato.

## Nota finale

**Nessuna riga di codice è stata scritta in questo task — solo questo file `.md` di pianificazione.**
