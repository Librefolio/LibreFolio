# Piano Implementativo: Downsample output segnali overlay (Milestone_3 — Step 4)

> **Deriva da**: [`./study_chart_dynamic_resolution.md`](./study_chart_dynamic_resolution.md) — sezioni
> [16](./study_chart_dynamic_resolution.md#16-segnali-overlay),
> [16.1](./study_chart_dynamic_resolution.md#161-ema--rsi--macd--segnali-linea),
> [16.2](./study_chart_dynamic_resolution.md#162-bollinger-bands).
> **Prerequisito concettuale**: [`./impl_plan_chart_resolution_00_foundation.md`](./impl_plan_chart_resolution_00_foundation.md)
> (contratto condiviso `ChartResolution` + `aggregateEnvelope()` + `downsampleRenderedSignal()` in
> `frontend/src/lib/components/charts/timeSeriesAggregation.ts`).
> **Punto di integrazione**: [`./impl_plan_chart_resolution_01_price_candlestick.md`](./impl_plan_chart_resolution_01_price_candlestick.md)
> — il dispatcher viene chiamato nei consumer `PriceChartFull` / `CandlestickChart`, subito prima di
> `buildOverlaySignalSeries()`.
> **Ambito**: solo tabella di dispatch per i 9 tipi registrati in
> `frontend/src/lib/charts/signals/registry.ts` + regole di wiring locale nei due chart che consumano
> `overlaySignals`. Nessun calcolo segnale viene spostato a monte, nessun file sorgente viene toccato in
> questo task.

## Principio guida

> I segnali restano **sempre** calcolati sulla serie daily completa tramite `computePoints()` /
> `render()` / `renderMulti()`. In vista `weekly|monthly` si downsamplea **solo** il `RenderedSignal`
> già prodotto, preservando la semantica finanziaria originale (es. `EMA(14)` resta a 14 giorni reali,
> non diventa EMA a 14 settimane/mesi) come fissato nello studio §16
> (`LibreFolio_developer_journal/RoadmapV4_UI/phase-09-subplan/Milestone_3/chart_resolution/study_chart_dynamic_resolution.md:1010-1029`).

Ogni step sotto dichiara esplicitamente cosa è **Riuso** vs cosa è **Nuovo**.

## Stato attuale (verificato sui sorgenti reali)

- **Riuso — contratto runtime già esistente**: `RenderedSignal` espone `data`, `yAxisIndex`, `seriesType`,
  `bandData` e metadati visuali, ma **non** conserva `signalType`; quindi il dispatcher runtime non può
  branchare per classe concreta, deve farlo per **shape renderizzata**
  (`frontend/src/lib/charts/signals/ChartSignal.ts:122-162`).
- **Riuso — i 9 tipi registrati sono esattamente questi**: `fx-pair`, `asset-comparison`, `linear`,
  `compound`, `sine`, `ema`, `macd`, `rsi`, `bollinger`
  (`frontend/src/lib/charts/signals/registry.ts:35-45`).
- **Riuso — famiglia lineare semplice**:
  - `EmaSignal` usa `computePoints()` lineare e il `render()` base (`frontend/src/lib/charts/signals/EmaSignal.ts:26-93`,
    `frontend/src/lib/charts/signals/ChartSignal.ts:267-297`);
  - `LinearSignal`, `CompoundSignal`, `SineSignal` producono una sola `LineDataPoint[]` ciascuno
    (`frontend/src/lib/charts/signals/LinearSignal.ts:17-72`,
    `frontend/src/lib/charts/signals/CompoundSignal.ts:23-94`,
    `frontend/src/lib/charts/signals/SineSignal.ts:25-88`);
  - `FxPairSignal` overridea `render()` ma restituisce comunque una singola serie lineare
    (`frontend/src/lib/charts/signals/FxPairSignal.ts:33-87`);
  - `AssetComparisonSignal` restituisce una linea principale ed eventualmente una ghost line FX-converted,
    ma entrambe restano `RenderedSignal` lineari indipendenti
    (`frontend/src/lib/charts/signals/AssetComparisonSignal.ts:62-99,111-165`).
- **Riuso — RSI non cambia shape, cambia solo segmentazione**: `RsiSignal.renderMulti()` spezza la linea in
  più `RenderedSignal` contigui, tutti con `yAxisIndex = 1`; ogni segmento resta comunque una serie lineare
  indipendente
  (`frontend/src/lib/charts/signals/RsiSignal.ts:21-27,108-170`).
- **Riuso — MACD è composito a 3 output già flattenati**: `renderMulti()` produce tre `RenderedSignal`
  separati con id suffix `-macd` / `-signal` / `-hist`; i primi due sono linee, il terzo è `seriesType:'bar'`,
  tutti su `yAxisIndex = 2`
  (`frontend/src/lib/charts/signals/MacdSignal.ts:33-39,101-147`).
- **Riuso — Bollinger usa shape dedicata `band`**: `render()` marca `seriesType = 'band'` e popola
  `bandData.upper/middle/lower`, allineati a `data[].date`
  (`frontend/src/lib/charts/signals/BollingerSignal.ts:74-99`).
- **Riuso — consumer finale già shape-driven**: `buildOverlaySignalSeries()` brancha oggi per
  `seriesType ?? 'line'`, con path distinti `band` / `bar` / `line`; non conosce le classi segnale
  (`frontend/src/lib/components/charts/chartCoreHelpers.ts:166-253`).
- **Riuso — call-site daily da lasciare invariati**: i `renderMulti()` applicativi stanno a monte nelle pagine
  asset/fx e in `ChartSettingsModal`, quindi il calcolo dei segnali resta daily come oggi
  (`frontend/src/routes/(app)/assets/[id]/+page.svelte:553`,
  `frontend/src/routes/(app)/assets/+page.svelte:841`,
  `frontend/src/routes/(app)/fx/[pair]/+page.svelte:293`,
  `frontend/src/routes/(app)/fx/+page.svelte:456`,
  `frontend/src/lib/components/charts/ChartSettingsModal.svelte:201`).
- **Riuso — unici consumer overlay in scope**:
  - `PriceChartFull` passa `overlaySignals` al child candlestick e li usa direttamente nel path linea
    (`frontend/src/lib/components/charts/PriceChartFull.svelte:888-905,541-542`);
  - `CandlestickChart` riceve la stessa prop e la inoltra a `buildOverlaySignalSeries()`
    (`frontend/src/lib/components/charts/CandlestickChart.svelte:45-46,87,326-327`).
- **Fuori scope esplicito**: `GrowthChart` e `AllocationHistoryChart` non hanno overlay signals in questa
  milestone; la logica qui documentata vale solo per `PriceChartFull` / `CandlestickChart`.

## Gap

1. `frontend/src/lib/components/charts/timeSeriesAggregation.ts` non esiste ancora, quindi oggi mancano sia il
   dispatcher `downsampleRenderedSignal()` sia l’aggregatore envelope dedicato a Bollinger
   (`./impl_plan_chart_resolution_00_foundation.md:31-63`).
2. Non esiste una mappa canonica **tipo registrato → shape renderizzata → regola di downsample**: oggi questa
   conoscenza è sparsa tra `registry.ts`, subclassi `ChartSignal` e helper ECharts.
3. `buildOverlaySignalSeries()` riceve sempre `overlaySignals` daily grezzi; nessun consumer locale applica
   ancora `resolution` + `bucketedDates` prima del render
   (`frontend/src/lib/components/charts/PriceChartFull.svelte:541-542`,
   `frontend/src/lib/components/charts/CandlestickChart.svelte:326-327`).
4. Senza una regola esplicita per `bar` vs `band`, weekly/monthly rischierebbero due errori semantici opposti:
   sommare istogrammi MACD (sbagliato) oppure schiacciare Bollinger a un singolo end-point (troppo povero).

## Decisioni prese (non più aperte)

| Tipo registrato | Shape `RenderedSignal` effettiva | Dispatch output | Motivo |
|---|---|---|---|
| `ema` | 1 serie `line` | **fine-periodo** via `aggregateLineSeries()` | indicatore continuo; deve mostrare valore daily dell’end-date bucket |
| `linear` | 1 serie `line` | **fine-periodo** via `aggregateLineSeries()` | benchmark continuo, stessa semantica della serie prezzo |
| `compound` | 1 serie `line` | **fine-periodo** via `aggregateLineSeries()` | benchmark continuo, confronto stabile tra zoom |
| `sine` | 1 serie `line` | **fine-periodo** via `aggregateLineSeries()` | benchmark continuo; nessuna aggregazione speciale richiesta |
| `fx-pair` | 1 serie `line` | **fine-periodo** via `aggregateLineSeries()` | confronto daily già normalizzato/renderizzato; weekly/monthly mostra snapshot bucket |
| `asset-comparison` | 1 o 2 serie `line` indipendenti (main + eventuale ghost) | **fine-periodo** via `aggregateLineSeries()` per ciascuna serie | entrambe sono linee continue; ghost non richiede path separato |
| `rsi` | 1..N serie `line` segmentate, `yAxisIndex=1` | **fine-periodo** via `aggregateLineSeries()` per ogni segmento | oscillatore già daily; segmentazione visiva non cambia regola di bucket |
| `macd` | 3 serie flattenate: `line` + `line` + `bar`, tutte `yAxisIndex=2` | **fine-periodo** via `aggregateLineSeries()` per ciascuna delle 3 serie | studio §16.1 fissa snapshot end-date anche per histogram; **vietato** sommare bucket |
| `bollinger` | 1 serie `band` con `bandData.upper/middle/lower` | **envelope** via `aggregateEnvelope()` | upper=max, lower=min, middle=end-date: banda = intervallo, non singolo punto |

Ulteriori regole fissate:

- `yAxisIndex` **non cambia mai** col downsample: va solo preservato/passato attraverso invariato
  (`frontend/src/lib/charts/signals/ChartSignal.ts:133-142`,
  `frontend/src/lib/charts/signals/RsiSignal.ts:26,150-167`,
  `frontend/src/lib/charts/signals/MacdSignal.ts:38,122-145`).
- `label` resta invariata: `EMA(14)`, `RSI(14)`, `MACD(12,26,9)`, `BB(20,2σ)` continuano a descrivere periodi
  **daily reali**, non bucket visuali
  (`frontend/src/lib/charts/signals/EmaSignal.ts:88-93`,
  `frontend/src/lib/charts/signals/RsiSignal.ts:104-106`,
  `frontend/src/lib/charts/signals/MacdSignal.ts:81-86`,
  `frontend/src/lib/charts/signals/BollingerSignal.ts:102-106`).
- `buildOverlaySignalSeries()` resta helper puro shape-driven; il downsample avviene **prima** della chiamata,
  non dentro la costruzione ECharts
  (`frontend/src/lib/components/charts/chartCoreHelpers.ts:166-253`).

## Ordine di implementazione

```text
PREREQ
  └─ doc 00: contratto shared + timeSeriesAggregation.ts
          │
          ▼
STEP 1 Tabella canonica tipo → shape → regola
          │
          ▼
STEP 2 downsampleRenderedSignal(): branch per 'line'/'bar'/'band'
          │
          ▼
STEP 3 Integrazione locale nei 2 consumer overlay (consumata da doc 01, non prerequisito di questo documento)
  ├─ PriceChartFull: prima di buildOverlaySignalSeries(...)
  └─ CandlestickChart: prima di buildOverlaySignalSeries(...)
          │
          ▼
STEP 4 Verifica invarianti: call-site renderMulti() untouched, label/assi preservati
```

Questo documento dipende **solo** da `[00]` (tipi/contratto `ChartResolution`, `RenderedSignal`,
`downsampleRenderedSignal()`) — non da `impl_plan_chart_resolution_01_price_candlestick.md`. La tabella
dispatch per-tipo e la firma di `downsampleRenderedSignal()` sono definibili indipendentemente da come/dove
`resolution` viene calcolato. **Doc 01 è invece il consumer**: dipende da questo documento (oltre che da
`[00]`) per sapere come e dove agganciare la chiamata al dispatcher, non viceversa — nessuna dipendenza
circolare (correzione post-audit: la stesura precedente dichiarava erroneamente una dipendenza reciproca
doc01↔doc04).

---

## STEP 1 — Tabella canonica runtime: shape renderizzata prima del tipo sorgente

### 1.1 Verità runtime = `RenderedSignal`, non classe `ChartSignal`

- **Riuso**: il flattening è già fatto a monte da `render()` / `renderMulti()`; i chart ricevono solo
  `RenderedSignal[]`
  (`frontend/src/lib/charts/signals/ChartSignal.ts:267-313`).
- **Nuovo**: il dispatcher va progettato come funzione **shape-driven**:
  ```ts
  downsampleRenderedSignal(signal, resolution, bucketedDates)
  ```
  non come `switch(signalType)`, perché `signalType` non è più disponibile nel payload runtime
  (`frontend/src/lib/charts/signals/ChartSignal.ts:122-162`).

### 1.2 Mappa pratica da usare in implementazione

- **Line family** → `seriesType` assente oppure `'line'`:
  `ema`, `linear`, `compound`, `sine`, `fx-pair`, `asset-comparison`, `rsi`, più i due sotto-output lineari
  di MACD.
- **Bar family** → `seriesType === 'bar'`:
  solo MACD histogram oggi
  (`frontend/src/lib/charts/signals/MacdSignal.ts:135-146`).
- **Band family** → `seriesType === 'band' && bandData`:
  solo Bollinger oggi
  (`frontend/src/lib/charts/signals/BollingerSignal.ts:78-99`).

### 1.3 Implicazione importante per i casi composti

- **Nuovo**: i casi composti non richiedono coordinamento multi-serie dentro il dispatcher:
  - MACD arriva già come **3 chiamate indipendenti**;
  - RSI arriva già come **N segmenti indipendenti**;
  - AssetComparison ghost arriva già come **seconda linea indipendente**.
- **Conclusione**: una singola funzione `RenderedSignal -> RenderedSignal` basta; la logica di flattening resta
  responsabilità delle subclassi `renderMulti()`.

---

## STEP 2 — `downsampleRenderedSignal()` nel modulo shared

### 2.1 Firma e invarianti

- **Nuovo**: la firma canonica è quella fissata da doc 00:
  ```ts
  function downsampleRenderedSignal(
      signal: RenderedSignal,
      resolution: ChartResolution,
      bucketedDates: string[],
  ): RenderedSignal;
  ```
  (`./impl_plan_chart_resolution_00_foundation.md:55-63`).
- **Riuso**: `bucketedDates` è l’asse X **già risolto** della serie principale del chart chiamante; il
  dispatcher non decide i bucket, li riceve dal caller che ha già aggregato `data`.

### 2.2 Fast-path `daily`

- **Nuovo**: per `resolution === 'daily'`, ritorno immediato del `signal` originale senza clone profondo.
- **Motivo**: nessun bucket change, zero trasformazioni, nessun rischio di drift rispetto al comportamento attuale.

### 2.3 Path `line` e `bar` = fine-periodo

- **Riuso**: doc 00 fissa `aggregateLineSeries(points, resolution)` come regola canonica end-periodo
  (`./impl_plan_chart_resolution_00_foundation.md:55-57,203-215`).
- **Nuovo**: il dispatcher usa **lo stesso** aggregatore sia per `'line'` sia per `'bar'`:
  1. `aggregated = aggregateLineSeries(signal.data, resolution)`;
  2. filtra `aggregated` sui soli `bucketedDates`;
  3. restituisce un clone shallow di `signal` con `data = filtered`.
- **Decisione esplicita MACD histogram**: anche `seriesType:'bar'` resta fine-periodo, **mai somma/media per
  bucket**, perché lo studio §16.1 richiede snapshot daily all’end-date anche per l’istogramma
  (`LibreFolio_developer_journal/RoadmapV4_UI/phase-09-subplan/Milestone_3/chart_resolution/study_chart_dynamic_resolution.md:1049-1062`).

### 2.4 Path `band` = envelope

- **Riuso**: doc 00 introduce `aggregateEnvelope(upper, middleData, lower, resolution)` proprio per Bollinger
  (`./impl_plan_chart_resolution_00_foundation.md:58-59,78-79`).
- **Nuovo**: per `seriesType === 'band' && signal.bandData` il dispatcher:
  1. chiama `aggregateEnvelope(signal.bandData.upper, signal.data, signal.bandData.lower, resolution)`;
  2. ottiene `{upper, middle, lower}` già bucketizzati;
  3. filtra i bucket sul set `bucketedDates`;
  4. ricostruisce:
     - `data = filteredMiddle`;
     - `bandData.middle = filteredMiddle.map((p) => p.value)`;
     - `bandData.upper = filteredUpper`;
     - `bandData.lower = filteredLower`.
- **Motivo**: la banda visualizza un intervallo di confidenza; comprimere tutto a solo end-date perderebbe
  l’escursione intra-bucket che lo studio §16.2 vuole esplicitamente preservare
  (`LibreFolio_developer_journal/RoadmapV4_UI/phase-09-subplan/Milestone_3/chart_resolution/study_chart_dynamic_resolution.md:1066-1107`).

### 2.5 Fallback difensivo

- **Nuovo**: se `seriesType === 'band'` ma `bandData` manca, il dispatcher **non** deve inventare envelope
  parziale; degrada al path lineare su `signal.data`.
- **Motivo**: oggi il caso non dovrebbe verificarsi perché `BollingerSignal.render()` popola sempre `bandData`
  quando marca `seriesType:'band'`
  (`frontend/src/lib/charts/signals/BollingerSignal.ts:74-99`), ma fallback lineare evita crash su payload corrotti.

### 2.6 Metadati da preservare 1:1

- **Riuso**: il dispatcher non ricalcola né muta:
  `id`, `label`, `color`, `lineWidth`, `lineType`, `markerStart`, `markerEnd`, `yAxisIndex`, `iconUrl`,
  `assetType`, `opacity`, `currency`, `currencyFlag`
  (`frontend/src/lib/charts/signals/ChartSignal.ts:122-162`).
- **Nuovo**: unico campo trasformato sempre = `data`; `bandData` solo per path `'band'`.

---

## STEP 3 — Regole speciali da non violare

### 3.1 MACD: tre serie indipendenti, nessuna aggregazione congiunta

- **Riuso**: `MacdSignal.renderMulti()` restituisce già tre `RenderedSignal` separati
  (`frontend/src/lib/charts/signals/MacdSignal.ts:101-147`).
- **Nuovo**: implementazione e test mentali devono assumere **tre invocazioni distinte** del dispatcher:
  - `...-macd` → path `line`;
  - `...-signal` → path `line`;
  - `...-hist` → path `bar`.
- **Divieto**: nessun merge dei tre output prima/dopo il dispatcher.

### 3.2 RSI: segmenti lineari indipendenti

- **Riuso**: segmentazione overbought/neutral/oversold è già modellata come array di `RenderedSignal`
  (`frontend/src/lib/charts/signals/RsiSignal.ts:108-170`).
- **Nuovo**: ogni segmento passa nel dispatcher da solo; se un bucket elimina tutti i punti di un segmento,
  quel `RenderedSignal` può risultare vuoto ed essere filtrato dal caller.

### 3.3 AssetComparison ghost: stessa regola della linea principale

- **Riuso**: la ghost line è solo un secondo `RenderedSignal` con `opacity` e label dedicata
  (`frontend/src/lib/charts/signals/AssetComparisonSignal.ts:111-159`).
- **Nuovo**: nessun trattamento speciale; stesso path lineare fine-periodo della serie principale.

### 3.4 Marker e label restano coerenti

- **Riuso**: i marker start/end vengono applicati da `buildOverlaySignalSeries()` scansionando primo/ultimo
  punto non-null della serie già fornita
  (`frontend/src/lib/components/charts/chartCoreHelpers.ts:212-247`).
- **Nuovo**: downsampleando `data` prima del render, i marker si riallineano automaticamente al primo/ultimo
  bucket visibile senza cambiare alcuna logica ECharts nel helper shared.

---

## STEP 4 — Integrazione locale in `PriceChartFull` / `CandlestickChart`

### 4.1 Punto esatto di chiamata

- **Riuso**: i due consumer chiamano già `buildOverlaySignalSeries(overlaySignals, dates, ...)`
  (`frontend/src/lib/components/charts/PriceChartFull.svelte:541-542`,
  `frontend/src/lib/components/charts/CandlestickChart.svelte:326-327`).
- **Nuovo**: subito prima di quel punto, ciascun consumer crea un array locale:
  ```ts
  const resolvedOverlaySignals =
      resolution === 'daily'
          ? overlaySignals
          : overlaySignals
                .map((signal) => downsampleRenderedSignal(signal, resolution, dates))
                .filter((signal) => signal.data.length > 0);
  ```
  dove `dates` è già l’asse bucketizzato della serie principale del chart corrente.

### 4.2 `PriceChartFull`

- **Integrazione (non dipendenza)**: doc 01 introduce stato `resolution` condiviso nel parent; questo
  documento non ridefinisce quel wiring, ne descrive solo il punto di aggancio per chi implementerà doc 01
  (`./impl_plan_chart_resolution_01_price_candlestick.md:102-119,124-170`).
- **Nuovo**: nel path linea di `PriceChartFull`, `resolvedOverlaySignals` diventa l’input di
  `buildOverlaySignalSeries()` al posto della prop raw daily.
- **Nota di confine**: i call-site a monte (`renderMulti()` nelle route e nella modal preview) restano intatti;
  il downsample vive **solo** nel chart consumer, sulla prop già ricevuta.

### 4.3 `CandlestickChart`

- **Riuso**: `CandlestickChart` già riceve `overlaySignals` dal parent come prop
  (`frontend/src/lib/components/charts/CandlestickChart.svelte:45-46,87`).
- **Nuovo**: il child applica la stessa trasformazione locale prima della chiamata al helper shared.
- **Requisito di integrazione per doc 01** (non un prerequisito di *questo* documento): il child deve
  ricevere anche `resolution` come prop, perché senza quel contesto non può distinguere daily vs weekly vs
  monthly — è doc 01 a dover cablare questo passaggio, la regola di downsample stessa è già completa qui.

### 4.4 `buildOverlaySignalSeries()` resta invariato

- **Riuso**: il helper shared conosce già perfettamente come tradurre `line` / `bar` / `band` in serie ECharts
  (`frontend/src/lib/components/charts/chartCoreHelpers.ts:171-249`).
- **Decisione**: qui **non** si modifica il helper; si cambia solo il contratto del caller:
  `overlaySignals` in ingresso a `buildOverlaySignalSeries()` devono essere già coerenti con `dates`.

## Nota finale

Nessuna riga di codice scritta in questo task: documento di pianificazione soltanto.
