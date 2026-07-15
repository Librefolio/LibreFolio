# Piano Implementativo: Risoluzione dinamica condivisa in `PriceChartFull` + `CandlestickChart` (Milestone_3)

> **Stato: ✅ implementato** — `PriceChartFull.svelte`/`CandlestickChart.svelte` usano il contratto
> condiviso `[00]`; risoluzione ricalcolata su dataZoom/pan/resize (bug di resize-only risolto in un round
> successivo, vedi `plan.md` sessione — `scheduleResolutionRecompute()` mancante nel branch resize di
> `PriceChartFull`, ora allineato a `GrowthChart`/`AllocationHistoryChart`).

> **Deriva da**: [`./study_chart_dynamic_resolution.md`](./study_chart_dynamic_resolution.md) — sezioni
> [3](./study_chart_dynamic_resolution.md#3-risoluzione-iniziale-al-primo-rendering),
> [4](./study_chart_dynamic_resolution.md#4-switch-di-risoluzione-senza-animazione),
> [7](./study_chart_dynamic_resolution.md#7-debounce-sugli-eventi-datazoom),
> [9](./study_chart_dynamic_resolution.md#9-preservazione-del-range-con-date-assolute),
> [11.2](./study_chart_dynamic_resolution.md#112-candlestick-ohlcv),
> [11.4](./study_chart_dynamic_resolution.md#114-staleness),
> [11.5](./study_chart_dynamic_resolution.md#115-colorazione-baseline-verderosso),
> [13](./study_chart_dynamic_resolution.md#13-event-markers),
> [14](./study_chart_dynamic_resolution.md#14-tooltip-bucket-aware),
> [15](./study_chart_dynamic_resolution.md#15-measure-mode),
> [18](./study_chart_dynamic_resolution.md#18-badge-di-aggregazione),
> [19](./study_chart_dynamic_resolution.md#19-flusso-completo-allapertura),
> [20](./study_chart_dynamic_resolution.md#20-flusso-completo-durante-zoompanresize).
> **Prerequisito concettuale**: [`./impl_plan_chart_resolution_00_foundation.md`](./impl_plan_chart_resolution_00_foundation.md)
> (contratto condiviso `ChartResolution` + `timeSeriesAggregation.ts`, in scrittura parallela).
> **Documenti fratelli / integrazioni**:
> [`./impl_plan_chart_resolution_02_growth_chart.md`](./impl_plan_chart_resolution_02_growth_chart.md),
> [`./impl_plan_chart_resolution_03_allocation_history.md`](./impl_plan_chart_resolution_03_allocation_history.md),
> [`./impl_plan_chart_resolution_04_signals_overlay.md`](./impl_plan_chart_resolution_04_signals_overlay.md),
> [`./impl_plan_chart_resolution_05_badge_i18n.md`](./impl_plan_chart_resolution_05_badge_i18n.md).
> **Ambito**: solo orchestrazione della risoluzione condivisa fra vista linea e vista candela in
> `frontend/src/lib/components/charts/PriceChartFull.svelte` +
> `frontend/src/lib/components/charts/CandlestickChart.svelte`.

## Principio guida

> Una sola sorgente di verità per la risoluzione corrente: `PriceChartFull` decide `daily|weekly|monthly`,
> calcola una sola volta i dati risolti e li propaga a entrambe le viste. `CandlestickChart` resta renderer
> passivo (nessuna logica autonoma di scelta soglia/range), così il toggle linea↔candela non può divergere.

Ogni step sotto dichiara esplicitamente cosa **riusa** (già corretto/utile) vs cosa è **nuovo** (minimo
necessario per chiudere i gap).

## Stato attuale (verificato sui sorgenti reali)

- `PriceChartFull.svelte` ha un `renderChart()` monolitico che rigenera tutte le serie/assi/tooltip e chiude con
  `chartInstance.setOption(option, true)` — full replace ad ogni render
  (`frontend/src/lib/components/charts/PriceChartFull.svelte:262-289,700-714,849-852`).
- Lo switch senza animazione è **già soddisfatto** per vista linea: `option.animation = false`
  (`frontend/src/lib/components/charts/PriceChartFull.svelte:700-702`). Anche `CandlestickChart` ha già
  `animation: false` (`frontend/src/lib/components/charts/CandlestickChart.svelte:448-450`).
- L’unico listener `dataZoom` attuale in `PriceChartFull` ruota le frecce overlay, senza logica di risoluzione
  (`frontend/src/lib/components/charts/PriceChartFull.svelte:369-372`).
- La preservazione dello zoom in `PriceChartFull` è oggi basata su percentuali `start/end` lette da
  `chartInstance.getOption().dataZoom[0]` e reiniettate nell’option successiva
  (`frontend/src/lib/components/charts/PriceChartFull.svelte:674-685,714-714`).
- `PriceChartFull` passa oggi la stessa prop `data` alla vista linea (`displayData`) e alla vista candela
  (`<CandlestickChart data={data} .../>`), quindi il parent è già il punto naturale dove calcolare una singola
  `resolvedData` condivisa (`frontend/src/lib/components/charts/PriceChartFull.svelte:182-187,481-489,888-909`).
- Gli event markers di `PriceChartFull` usano matching esatto `date -> index` tramite `dateIndexMap`; ogni marker
  produce uno scatter point sulla data reale ed un tooltip per evento singolo
  (`frontend/src/lib/components/charts/PriceChartFull.svelte:564-666`).
- Il tooltip principale della vista linea usa come header `items[0].axisValue || items[0].name`, cioè una singola
  data già formattata dall’asse, non un bucket-aware header (`frontend/src/lib/components/charts/PriceChartFull.svelte:715-847`,
  in particolare `725-726`).
- Measure mode di `PriceChartFull` converte pixel→indice→`displayData[dateIdx]` sia su click che hover/tap,
  quindi oggi assume mapping 1:1 punto visualizzato ↔ data reale
  (`frontend/src/lib/components/charts/PriceChartFull.svelte:240-256,321-339,341-367,437-456`).
- `CandlestickChart` è già renderer separato ma passivo: riceve `data`, costruisce serie OHLC/volume/overlay e
  ha un listener `dataZoom` che ruota solo le frecce (`frontend/src/lib/components/charts/CandlestickChart.svelte:34-79,160-187,298-327,448-468`).
- Quando OHLC mancano, `CandlestickChart` sintetizza per ogni giorno `open=prevClose`, `high/low=max|min(open,close)`
  prima di costruire la candela ECharts (`frontend/src/lib/components/charts/CandlestickChart.svelte:263-274`).
- `buildOverlaySignalSeries()` resta helper condiviso puro che riceve `overlaySignals` e `dates`; viene invocato
  sia da `PriceChartFull` sia da `CandlestickChart` subito prima di spingere le serie overlay
  (`frontend/src/lib/components/charts/chartCoreHelpers.ts:157-253`,
  `frontend/src/lib/components/charts/PriceChartFull.svelte:541-543`,
  `frontend/src/lib/components/charts/CandlestickChart.svelte:326-327`).
- `buildDataZoom()` è già shared helper con `filterMode: 'filter'`, quindi pan/zoom runtime resta delegato a
  ECharts e non richiede un buffer manuale (`frontend/src/lib/components/charts/chartCoreHelpers.ts:259-271`).
- Il toggle tipo grafico già occupa area overlay `absolute top-2 left-12`
  (`frontend/src/lib/components/charts/PriceChartFull.svelte:867-883`).

## Gap

1. Nessuno stato `resolution` condiviso nel parent, nessun calcolo iniziale al mount, nessun debounce 200ms,
   nessuna isteresi a densità/pixel.
2. Il range logico è perso ai cambi di risoluzione perché oggi sopravvivono solo percentuali `dataZoom.start/end`.
3. Vista linea e vista candela ricevono ancora dati daily grezzi, quindi non esiste un punto unico dove applicare
   `aggregateLineSeries()` / `aggregateOHLCV()`.
4. Event markers, tooltip e measure mode non sono bucket-aware.
5. Overlay signals non vengono ancora downsampled prima di `buildOverlaySignalSeries()`.
6. Badge risoluzione assente; posizione attuale del toggle impone un offset esplicito per evitare collisioni.

## Decisioni prese (non più aperte)

| Decisione | Scelta |
|---|---|
| Sorgente di verità `resolution` | Solo `PriceChartFull`; `CandlestickChart` riceve `resolvedData` + `resolution` ma non decide nulla |
| Strategia render al cambio soglia | **Riusare `renderChart()` full rebuild** in `PriceChartFull` e `setOption(..., true)` in entrambi i renderer; più semplice e logicamente sicuro, costo mitigato da debounce 200ms + isteresi + dataset aggregati |
| Preservazione range | Stato logico a date assolute `{startDate, endDate}`; percentuali `start/end` solo dettaglio ECharts derivato al render |
| Risoluzione iniziale | Calcolata prima del primo `setOption`, misurando `chartInstance.getWidth()` / larghezza plot effettiva; evitare render daily→switch immediato |
| Cache | Memoizzazione locale al componente keyed by `resolution`; nessun nuovo store globale |
| Dati linea | `aggregateLineSeries()` su serie daily già eventualmente trasformata per `viewMode` coerente con line chart |
| Dati candela | OHLC giornalieri completi prima, poi `aggregateOHLCV()`; la sintesi `open/high/low` giornaliera resta quindi **a monte** dell’aggregazione |
| Staleness / baseline color | Ereditano end-date del bucket, in linea con studio §§11.4-11.5 |
| Overlay signals | Calcolo segnali invariato su daily; qui solo integrazione di `downsampleRenderedSignal()` subito prima di `buildOverlaySignalSeries()` |
| Badge | Mostrare solo per `weekly|monthly`; posizione consigliata `absolute top-2 left-28 z-10` per stare a destra del toggle `left-12` senza overlap |

## Ordine di implementazione

```text
PREREQ concettuali
  ├─ doc 00: contratto condiviso + timeSeriesAggregation.ts
  ├─ doc 04: regole downsample overlay
  └─ doc 05: badge/i18n
          │
          ▼
STEP 1 PriceChartFull: stato resolution + logical range + debounce + hysteresis
          │
          ▼
STEP 2 Risoluzione condivisa linea↔candela + resolvedData unico
          │
          ├─ STEP 3 Event markers bucket-aware
          ├─ STEP 4 Tooltip bucket-aware
          ├─ STEP 5 Measure mode bucket-aware
          └─ STEP 6 Badge integration
```

---

## STEP 1 — Stato risoluzione condiviso + dataZoom/logical range/debounce

### 1.1 Stato locale minimo in `PriceChartFull`

- **Nuovo**: stato locale esplicito nel parent, senza store globale:
  ```ts
  type LogicalVisibleRange = {startDate: string; endDate: string};
  ```
  più:
  - `resolution: ChartResolution = 'daily'`;
  - `logicalRange: LogicalVisibleRange | null`;
  - cache locale per `daily|weekly|monthly`;
  - timer debounce `dataZoom` 200ms.
- **Riuso**: il parent ha già tutto ciò che serve per decidere:
  `data`, `displayData`, `chartInstance`, listener `dataZoom`, resize observer
  (`frontend/src/lib/components/charts/PriceChartFull.svelte:182-187,274-286,369-372`).

### 1.2 Primo rendering già nella risoluzione corretta

- **Nuovo**: prima del primo `setOption`, il parent deve:
  1. misurare `plotWidthPx` dalla chart reale (`chartInstance.getWidth()` come da contratto condiviso);
  2. determinare `counts.{dailyCount,weeklyCount,monthlyCount}` sul range iniziale visibile (raggruppando
     le date con `mapDateToBucket()`, **non** con un'approssimazione aritmetica — vedi contratto aggiornato
     in `[00]`);
  3. chiamare `chooseResolution(current, counts, plotWidthPx)`;
  4. produrre `resolvedData` coerente e solo dopo renderizzare.
- **Riuso**: `renderChart()` è già il punto unico in cui vengono costruiti `dates`, `series`, `tooltip`, `dataZoom`
  (`frontend/src/lib/components/charts/PriceChartFull.svelte:262-289,481-543,700-850`).
- **Nota**: questo chiude esplicitamente studio §3; niente render daily iniziale seguito da sostituzione weekly/monthly.

### 1.3 Debounce `dataZoom` + isteresi + range logico assoluto

- **Riuso**: il gancio corretto esiste già e va esteso, non duplicato:
  `chartInstance.on('dataZoom', ...)` (`frontend/src/lib/components/charts/PriceChartFull.svelte:369-372`).
- **Nuovo**:
  - il listener continua a chiamare `updateArrowRotations(chartInstance)`;
  - in più salva/aggiorna `logicalRange` leggendo il range visibile reale;
  - avvia debounce 200ms;
  - allo scadere ricalcola densità corrente con isteresi 1.30 / 0.80;
  - se `targetResolution === resolution`, non fa nulla;
  - se cambia, usa `logicalRange` per rimappare `startDate/endDate` sui bucket target e rilancia il render.
- **Nuovo**: sostituire concettualmente l’attuale `savedZoom: {start,end}` percentuale
  (`frontend/src/lib/components/charts/PriceChartFull.svelte:674-685`) con due livelli distinti:
  ```text
  stato logico     = date reali assolute
  stato ECharts    = start/end percentuali derivati al render corrente
  ```
- **Riuso**: `buildDataZoom()` e `filterMode:'filter'` restano invariati
  (`frontend/src/lib/components/charts/chartCoreHelpers.ts:262-270`).

### 1.4 Raccomandazione architetturale: full rebuild, non path parziale

- **Scelta motivata**: per questo componente conviene **non** introdurre un path separato “solo switch risoluzione”.
- Motivi:
  1. `renderChart()` già centralizza serie linea, ghost series, overlay, baseline, event markers, tooltip e dataZoom
     (`frontend/src/lib/components/charts/PriceChartFull.svelte:487-850`);
  2. `setOption(option, true)` è già coerente con rebuild totale (`frontend/src/lib/components/charts/PriceChartFull.svelte:852-852`);
  3. lo switch è già non animato (`700-702`);
  4. nuova frequenza di switch sarà bassa per debounce + isteresi;
  5. introdurre update parziale separato aumenterebbe rischio di drift fra asse X, markers, tooltip, measure mode e
     vista candela.
- **Conclusione**: costo computazionale accettabile; complessità/bug risk del path parziale non giustificati in questa milestone.

---

## STEP 2 — Una sola `resolvedData` per linea e candela

### 2.1 Parent come punto unico di aggregazione

- **Nuovo**: `PriceChartFull` deve costruire una sola `resolvedData` in base a `resolution` corrente:
  - `daily` → riuso dati daily correnti;
  - `weekly|monthly` → cache locale keyed by `resolution`.
- **Nuovo**: la pipeline dati del parent deve distinguere:
  1. **serie linea**: `aggregateLineSeries(...)`;
  2. **serie candela**: `aggregateOHLCV(...)`.
- **Riuso**: il parent è già punto unico da cui partono entrambe le viste
  (`frontend/src/lib/components/charts/PriceChartFull.svelte:885-909`).

### 2.2 Sequenza raccomandata per OHLC

- **Decisione**: la sintesi OHLC giornaliera di `CandlestickChart` va spostata concettualmente **prima**
  dell’aggregazione, non lasciata come effetto collaterale finale del renderer.
- **Motivo**:
  - oggi la sintesi avviene per singolo giorno in `CandlestickChart.svelte:266-274`;
  - `aggregateOHLCV()` deve ricevere input giornaliero già completo, così weekly/monthly lavorano con regole
    standard indipendenti dalla fonte;
  - farla “dopo” non è equivalente quando il bucket contiene più giorni con OHLC mancanti, perché perderebbe il
    corretto `open` del primo giorno e le escursioni intermedie.
- **Riuso**: stessa regola di sintesi già verificata (`frontend/src/lib/components/charts/CandlestickChart.svelte:263-274`),
  solo anticipata nella pipeline dati.

### 2.3 `CandlestickChart` resta passivo

- **Nuovo**: il child riceve:
  - `data={resolvedCandlestickData}`;
  - `resolution={resolution}` (badge/UI **e** input per il proprio downsample overlay locale — vedi §2.4,
    stesso `resolution` deciso a monte da `PriceChartFull`, mai ricalcolato);
  - `overlaySignals` **invariato** (stessi `RenderedSignal[]` daily calcolati a monte dalle pagine — non
    pre-downsampled dal parent): il downsample avviene localmente in `CandlestickChart` stesso, come
    descritto in §2.4, esattamente allo stesso modo di `PriceChartFull`.
- **Riuso**: nessun listener soglia nel child; il suo `dataZoom` locale continua a servire solo per rotazione frecce
  e interazioni proprie (`frontend/src/lib/components/charts/CandlestickChart.svelte:182-187`).
- **Vincolo esplicito**: nessun doppio calcolo **risoluzione** in `CandlestickChart` (`resolution` è sempre quella
  ricevuta dal parent, mai ricalcolata con `chooseResolution()`), per evitare disallineamenti al toggle
  linea↔candela (rischio #1 dello studio). Il downsample overlay locale (§2.4) è una trasformazione pura data
  la `resolution` già decisa — non è una "seconda decisione di risoluzione", quindi non viola questo vincolo.

### 2.4 Punto di integrazione overlay — owner: ciascun consumer, localmente

- **Riuso**: `buildOverlaySignalSeries()` non va modificato nella semantica dispatch; riceve sempre
  `overlaySignals + dates` (`frontend/src/lib/components/charts/chartCoreHelpers.ts:166-176`).
- **Nuovo**: sia in `PriceChartFull` sia in `CandlestickChart`, immediatamente prima di:
  - `buildOverlaySignalSeries(overlaySignals, dates, ...)`
  si deve passare:
  ```ts
  overlaySignals.map((s) => downsampleRenderedSignal(s, resolution, bucketedDates))
  ```
  usando `bucketedDates = resolvedData.map((d) => d.date)`. **Nessun pre-downsample nel parent**: ogni
  consumer riceve sempre `overlaySignals` daily invariato e applica la trasformazione localmente — questo
  evita un secondo prop derivato (`downsampledOverlaySignals`) che duplicherebbe lo stato e potrebbe
  disallinearsi dal `resolution`/`bucketedDates` correnti del consumer specifico.
- **Punti esatti di aggancio**:
  - `frontend/src/lib/components/charts/PriceChartFull.svelte:541-543`
  - `frontend/src/lib/components/charts/CandlestickChart.svelte:326-327`

---

## STEP 3 — Event markers bucket-aware

### 3.1 Vista daily: riuso totale

- **Riuso**: il ramo daily conserva l’attuale comportamento `dateIndexMap` + scatter per data reale
  (`frontend/src/lib/components/charts/PriceChartFull.svelte:564-666`).

### 3.2 Vista weekly/monthly: bucket + tooltip concatenato

- **Nuovo**:
  - gruppare `eventMarkers` con `bucketEventMarkers()`;
  - per ogni bucket usare come `x` la representative date (`bucketEnd`, coerente col contratto condiviso);
  - usare come `y` il valore aggregato del bucket già visualizzato;
  - conservare nel payload scatter la lista completa degli eventi reali contenuti.
- **Nuovo**: per comparison events (`assetLabel`) il posizionamento `y` continua a leggere la serie overlay
  corrispondente, ma sulla versione già downsampled alla stessa risoluzione, non più sulla daily raw.
- **Riuso**: grouping per `eventType` / `assetLabel` e simboli `EVENT_SYMBOLS` restano invariati
  (`frontend/src/lib/components/charts/PriceChartFull.svelte:48-54,578-589,614-624`).

### 3.3 Tooltip marker

- **Nuovo**: tooltip marker aggregato deve mostrare:
  - label bucket (`chart.tooltip.weekRange` / `chart.tooltip.monthLabel`, stesse chiavi di §4.1);
  - valore di chiusura bucket;
  - elenco concatenato di tutti gli eventi reali nel periodo, introdotto da `chart.tooltip.eventsInPeriod`
    (chiave fissata in `impl_plan_chart_resolution_05_badge_i18n.md`).
- **Riuso**: formattazione dei singoli dettagli evento già presente nell’attuale tooltip item può essere estratta/
  riusata come renderer di riga evento (`frontend/src/lib/components/charts/PriceChartFull.svelte:628-659`).

---

## STEP 4 — Tooltip bucket-aware

### 4.1 Vista linea (`PriceChartFull`)

- **Gap attuale**: header singola data
  (`frontend/src/lib/components/charts/PriceChartFull.svelte:725-726`).
- **Nuovo**: header guidato da `resolution` + metadata bucket, usando le chiavi i18n `chart.*` fissate in
  `impl_plan_chart_resolution_05_badge_i18n.md` (non nomi locali inventati):
  - `daily` → `12/01/2026` (invariato, nessuna chiave nuova);
  - `weekly` → `chart.tooltip.weekRange` con `{start}`/`{end}` → "Settimana 12/01/2026 – 18/01/2026";
  - `monthly` → `chart.tooltip.monthLabel` (`{month}`) + `chart.tooltip.valueAt` (`{date}`) → "Gennaio 2026 —
    Valore al 31/01/2026".
- **Nuovo**: lookup `staleDays` / `fxStaleDays` deve usare la representative date del bucket aggregato
  (end-date), coerente con studio §11.4.
- **Riuso**: corpo tooltip per serie principali/ghost/overlay può restare quasi invariato
  (`frontend/src/lib/components/charts/PriceChartFull.svelte:727-845`), cambiando solo header e sorgente metadata.

### 4.2 Vista candela (`CandlestickChart`)

- **Gap attuale**: header singola data
  (`frontend/src/lib/components/charts/CandlestickChart.svelte:414-416`).
- **Nuovo**: stessa semantica bucket-aware del parent linea, con differenza che il corpo OHLC già mostra
  `O/H/L/C`; va solo chiarito che quei valori appartengono al bucket settimanale/mensile.
- **Riuso**: formatter prezzo e blocco OHLC rimangono corretti anche su dati aggregati
  (`frontend/src/lib/components/charts/CandlestickChart.svelte:391-446`).

### 4.3 Asse X

- **Riuso**: nessun nuovo asse o nuovo `dataZoom`.
- **Nuovo**: se doc 00 aggiunge metadata bucket solo nei dati e non nelle label asse, il tooltip resta fonte
  principale di chiarimento semantico; non è necessario forzare label asse verbose in questa milestone.

---

## STEP 5 — Measure mode bucket-aware

### 5.1 Modello dati misura: resta daily/assoluto

- **Riuso**: `MeasurePanel.svelte` continua a ricevere dati giornalieri completi; nessun nuovo gap nel modello.
- **Vincolo**: non convertire il modello misura a bucket. La riduzione riguarda solo il click sulla chart aggregata.

### 5.2 Click/hover/tap su vista linea

- **Gap attuale**: mapping diretto su `displayData[dateIdx]`
  (`frontend/src/lib/components/charts/PriceChartFull.svelte:240-256,321-339,341-367,437-456`).
- **Nuovo**:
  - quando `resolution='daily'`, comportamento invariato;
  - quando `weekly|monthly`, il click su punto aggregato seleziona `bucketEnd`;
  - hover preview usa anch’esso `bucketEnd`.
- **Riuso**: conversione `% -> absolute` in `handlePointClick()` resta valida, purché il valore passato sia già il
  valore rappresentativo del bucket (`frontend/src/lib/components/charts/PriceChartFull.svelte:240-255`).

### 5.3 Click/hover/dblclick su vista candela

- **Gap attuale**: `CandlestickChart` converte pixel→indice→`data[dateIdx]` e usa `d.date`
  (`frontend/src/lib/components/charts/CandlestickChart.svelte:188-245`).
- **Nuovo**: nessuna logica densità qui, ma quando il parent passa `resolvedCandlestickData`, `d.date` deve già
  essere `bucketEnd`; i gestori click/hover/dblclick diventano automaticamente bucket-aware senza branching extra.
- **Riuso**: questo è vantaggio diretto di far avvenire aggregazione nel parent e non nel child.

---

## STEP 6 — Integrazione badge risoluzione

### 6.1 Regola di visibilità

- **Nuovo**:
  - `daily` → nessun badge;
  - `weekly` → badge sintetico “Settimanale”;
  - `monthly` → badge sintetico “Mensile”.
- **Dipendenza**: testi/i18n/componentino concreto demandati a doc 05.

### 6.2 Posizione precisa senza collisione

- **Vincolo esistente**: toggle chart-type in `PriceChartFull` è già in overlay `absolute top-2 left-12`
  (`frontend/src/lib/components/charts/PriceChartFull.svelte:869-883`).
- **Scelta**: badge a `absolute top-2 left-28 z-10`.
- **Motivo**:
  - resta “alto a sinistra del plot” come richiesto dallo studio §18;
  - si colloca sulla stessa fascia visiva del toggle;
  - evita sovrapposizione con i due pulsanti già presenti;
  - non invade area asse Y sinistro.

### 6.3 Dove renderizzarlo

- **Raccomandazione**:
  - vista linea: badge nel wrapper relativo di `PriceChartFull` (`frontend/src/lib/components/charts/PriceChartFull.svelte:867-910`);
  - vista candela: passare comunque `resolution` a `CandlestickChart` per allineamento con doc 05 e per
    mantenere il child riusabile anche fuori da questo parent, ma senza aggiungergli logica autonoma di scelta.
- **Riuso**: nessuna modifica al toggle esistente, solo un overlay fratello.

---

## Nota finale

Questo task produce **solo** piano Markdown. Nessuna riga di codice scritta o modificata nei file sorgente
`frontend/*.svelte` / `frontend/*.ts`.
