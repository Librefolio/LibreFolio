# Piano Implementativo: Chart Resolution 06 — Compact cards Asset/FX (Milestone_3)

> **Deriva da**: [`../study_chart_dynamic_resolution.md`](./study_chart_dynamic_resolution.md) — sez. [3. Risoluzione iniziale al primo rendering](./study_chart_dynamic_resolution.md#3-risoluzione-iniziale-al-primo-rendering) (`:366-399`), [4. Switch di risoluzione senza animazione](./study_chart_dynamic_resolution.md#4-switch-di-risoluzione-senza-animazione) (`:402-420`), [5. Scelta della risoluzione basata su punti/pixel](./study_chart_dynamic_resolution.md#5-scelta-della-risoluzione-basata-su-puntipixel) (`:424-467`), [6. Hysteresis basata su punti/pixel](./study_chart_dynamic_resolution.md#6-hysteresis-basata-su-puntipixel) (`:470-523`, **qui rivalutata perché manca zoom continuo**), [11.1 Linee prezzo, NAV e serie cumulative](./study_chart_dynamic_resolution.md#111-linee-prezzo-nav-e-serie-cumulative) (`:679-715`), [19. Flusso completo all’apertura](./study_chart_dynamic_resolution.md#19-flusso-completo-allapertura) (`:1178-1202`), [20. Flusso completo durante zoom/pan/resize](./study_chart_dynamic_resolution.md#20-flusso-completo-durante-zoompanresize) (`:1206-1228`, da adattare al caso **resize-only**).
> **Prerequisito fondativo**: [`./impl_plan_chart_resolution_00_foundation.md`](./impl_plan_chart_resolution_00_foundation.md) (`[00]`) — contratto condiviso `ChartResolution`, `aggregateLineSeries()`, `computeDensity()`, memoizzazione locale keyed by resolution e soglie 1.30 / 0.80 (`:43-63`, `:70-88`, `:144-159`, `:203-255`, `:354-396`).
> **Riusi vincolati**: [`./impl_plan_chart_resolution_04_signals_overlay.md`](./impl_plan_chart_resolution_04_signals_overlay.md) (`[04]`, dispatch shape-driven overlay già deciso, `:92-120`, `:186-218`) · [`./impl_plan_chart_resolution_05_badge_i18n.md`](./impl_plan_chart_resolution_05_badge_i18n.md) (`[05]`, badge pill shared e anchor assoluti da **valutare, non applicare automaticamente** al caso 80px, `:43-60`, `:128-157`).
> **Ambito**: solo `frontend/src/lib/components/charts/PriceChartCompact.svelte` + `frontend/src/lib/components/charts/LineChart.svelte` nel ramo `compact === true`, come consumati da `frontend/src/lib/components/assets/AssetCard.svelte` e `frontend/src/lib/components/fx/FxCard.svelte` nelle liste `/assets` e `/fx`. Fuori scope: `PriceChartFull`, `CandlestickChart`, `ChartSettingsModal`, backend.

## Principio guida

> Card compatta = **semantic zoom statico per densità**, non “mini grafico interattivo”. Si riusano integralmente da `[00]` semantica bucket (`daily|weekly|monthly`), `aggregateLineSeries()` fine-periodo e `computeDensity()`, ma **non** si trascina meccanicamente l’hysteresis di `chooseResolution(current, ...)` pensata per `dataZoom` continuo. Qui conta solo: dati correnti + larghezza corrente del contenitore.

Ogni step sotto dichiara esplicitamente cosa è **Riuso** vs cosa è **Nuovo**.

## Stato attuale (verificato sui sorgenti reali)

- **Riuso — `PriceChartCompact` è wrapper sottilissimo**: riceve `data`, `height`, `viewMode`, `overlaySignals` e inoltra tutto a `LineChart` con `compact={true}`; non contiene alcuna logica di aggregazione, range o resize policy (`frontend/src/lib/components/charts/PriceChartCompact.svelte:13-36`).
- **Riuso — `LineChart` compact oggi non ha interazione temporale**:
  - `dataZoom: compact ? [] : [...]` → in compact l’array è vuoto, quindi nessun zoom/pan/listener funzionale da cui derivare una risoluzione dinamica (`frontend/src/lib/components/charts/LineChart.svelte:444-457`);
  - tooltip disattivato del tutto con `tooltip: compact ? undefined : {...}` (`frontend/src/lib/components/charts/LineChart.svelte:579-659`);
  - `animation: false` è già globale e soddisfa la regola di switch netto richiesta dallo studio (`frontend/src/lib/components/charts/LineChart.svelte:444-445`, coerente con `study_chart_dynamic_resolution.md:402-420`).
- **Gap concreto nel resize path**: il `ResizeObserver` oggi fa solo `chartInstance?.resize()` + `updateArrowRotations(chartInstance)`; non ricalcola dati aggregati né ricontrolla densità/risoluzione (`frontend/src/lib/components/charts/LineChart.svelte:187-202`).
- **Riuso — asse X/overlay già allineati per date**: `LineChart` costruisce `dates = data.map((d) => d.date)` e riallinea ogni `overlaySignal` su quell’asse tramite `signalLookup` (`frontend/src/lib/components/charts/LineChart.svelte:235-255`, `:280-381`). Questo rende naturale applicare il downsample overlay **prima** di `buildOverlaySignalSeries()`, come già fissato in `[04]`.
- **Riuso — `AssetCard` supporta già overlay e mini-chart**:
  - `chartData` arriva come prop, `displayData` deriva da `chartData`, `overlaySignals` viene renderizzato da `renderSignals(absoluteData, cardViewMode)` (`frontend/src/lib/components/assets/AssetCard.svelte:36-68`, `:89-99`);
  - `PriceChartCompact` è usato con `height="80px"` e passa già `overlaySignals`, `chartSettings?.areaFill`, `chartSettings?.colorByBaseline`, `chartSettings?.gridLines`, `chartSettings?.staleGradient` (`frontend/src/lib/components/assets/AssetCard.svelte:235-239`).
- **Riuso — `FxCard` è simmetrico ad `AssetCard`**:
  - costruisce `chartData`/`absoluteData`/`overlaySignals` localmente (`frontend/src/lib/components/fx/FxCard.svelte:25-55`, `:104-131`);
  - usa `PriceChartCompact` con `height="80px"` e stesso pass-through di `overlaySignals` / chart settings (`frontend/src/lib/components/fx/FxCard.svelte:234-238`).
- **Riuso — `dateStart` / `dateEnd` nelle card oggi servono alla navigazione, non al mini-chart**:
  - `AssetCard` li usa solo per `goto('/assets/{id}?start=...&end=...')` (`frontend/src/lib/components/assets/AssetCard.svelte:46-49`, `:123-126`);
  - `FxCard` idem per `goto('/fx/...?...')` (`frontend/src/lib/components/fx/FxCard.svelte:31-34`, `:147-152`).
- **Riuso — il range di pagina arriva dall’alto via fetch già filtrata**:
  - pagina `/assets`: `DateRangePicker` binda `activePreset`, `end`, `start`; `handleDateRangeChange()` aggiorna store/URL e richiama `fetchAllPriceData()` (`frontend/src/routes/(app)/assets/+page.svelte:137-155`, `:529-541`, `:932-935`); `buildAssetStateFromPrices()` trasforma poi le `prices` filtrate in `chartData` (`frontend/src/routes/(app)/assets/+page.svelte:493-525`); infine la griglia responsive `grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3` passa `chartData`, `dateStart={urlDateStart}`, `dateEnd={urlDateEnd}` ad `AssetCard` (`frontend/src/routes/(app)/assets/+page.svelte:1183-1205`).
  - pagina `/fx`: stesso pattern con `DateRangePicker`, `handleDateRangeChange()` → `fetchAllPairData()`, bulk load `ensureFxRangeLoadedBulk(...)`, griglia responsive `grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3`, passaggio `data`, `dateStart={urlDateStart}`, `dateEnd={urlDateEnd}` a `FxCard` (`frontend/src/routes/(app)/fx/+page.svelte:67-85`, `:316-353`, `:536-547`, `:883-901`).
- **Conclusione verificata**: nelle liste `/assets` e `/fx` la larghezza del plot **non è fissa**; dipende dalla griglia responsive 1/2/3 colonne (`frontend/src/routes/(app)/assets/+page.svelte:1183-1205`, `frontend/src/routes/(app)/fx/+page.svelte:883-901`). Quindi la scelta “punti/px” dello studio è rilevante anche senza `dataZoom`.

## Gap

1. I documenti precedenti avevano escluso `PriceChartCompact` perché senza `dataZoom`; il codebase conferma che il problema prestazionale/visivo però resta, solo in forma **statica** (molti punti daily dentro card basse 80px e larghe quanto concede la griglia responsive).
2. Oggi nessun ramo di `LineChart` compatto sceglie `daily|weekly|monthly` in base alla larghezza reale; `data` viene sempre renderizzato 1:1 (`frontend/src/lib/components/charts/LineChart.svelte:182-255`, `:444-457`).
3. Il resize oggi ridimensiona solo il canvas; manca totalmente il ricalcolo “width → density → resolution → aggregated data” (`frontend/src/lib/components/charts/LineChart.svelte:187-202`).
4. Le card supportano già `overlaySignals`, ma il downsample del loro output per asse bucketizzato compatto non è ancora cablato localmente; qui va riusato `[04]`, non riprogettato.
5. Il badge pill shared di `[05]` nasce per chart grandi con wrapper `.relative` e spazi top-left dedicati; infilato pari-pari su un plot alto 80px risulta invasivo sia per area utile sia per densità visiva complessiva della lista.
6. Costo computazionale moltiplicato per N: una pagina lista può avere decine di card simultanee, quindi la memoizzazione locale raccomandata da `[00]` non è “nice to have”, ma parte della baseline architetturale.

## Decisioni prese (non più aperte)

| Decisione | Scelta |
|---|---|
| Policy di scelta risoluzione nel compact | **Nuovo helper statico dedicato** (`chooseStaticResolution(dailyPointCount, plotWidthPx)`) che riusa `computeDensity()` di `[00]`, ma **non** `chooseResolution(current, ...)`. Motivo: qui non esiste `dataZoom` continuo né stato “corrente” da stabilizzare con hysteresis; la risoluzione va ricalcolata deterministicamente dai soli input correnti. |
| Soglie per compact | **Solo soglia alta 1.30 bucket/px**. Algoritmo: se `densityDaily <= 1.30` → `daily`; altrimenti valuta `weekly`; se `densityWeekly <= 1.30` → `weekly`; altrimenti `monthly`. La banda bassa 0.80 di `[00]` resta valida per i chart interattivi, non per queste preview statiche. |
| Trigger di ricalcolo | `data` ref change **oppure** width change reale del container. Il cambio range pagina (`dateStart`/`dateEnd`) **non richiede nuova prop** verso `PriceChartCompact` / `LineChart`: arriva già come nuovo `data` filtrato via `fetchAllPriceData()` / `fetchAllPairData()` (`assets/+page.svelte:493-541`, `fx/+page.svelte:316-353,536-547`). |
| Aggregazione serie principale | Solo **`aggregateLineSeries()` fine-periodo** di `[00]` (`impl_plan_chart_resolution_00_foundation.md:55-57,203-255`), coerente con studio §11.1 (`study_chart_dynamic_resolution.md:679-715`). **Non applicare** `aggregateOHLCV()` o logiche candlestick: le compact cards sono line-only. |
| Overlay signals | Riutilo integrale di `[04]`: segnali sempre calcolati daily a monte nelle pagine/card, poi output downsampled localmente nel compact branch prima di `buildOverlaySignalSeries()` (`impl_plan_chart_resolution_04_signals_overlay.md:92-120,186-218`). Nessuna nuova semantica segnali in questo doc. |
| Tooltip compact | **Non applicabile**. `LineChart` compact oggi non mostra tooltip (`frontend/src/lib/components/charts/LineChart.svelte:579-659`), quindi qui non si pianifica alcun formatter bucket-aware. Se in futuro il tooltip venisse riattivato nelle mini-card, andrà ereditata allora la strategia dei doc grandi. |
| Badge / indicatore risoluzione | **Nessun badge testuale `ResolutionBadge` nelle compact cards**. La pill di `[05]` è troppo invasiva su 80px (`AssetCard.svelte:235-239`, `FxCard.svelte:234-238`). Raccomandazione netta: nessun overlay in questo step. Eventuale indicatore futuro, se davvero richiesto, dovrà vivere fuori dal plot (es. micro chip header `W`/`M`), non come pill assoluta sopra il grafico. |
| Cache aggregazioni | Memoizzazione locale **per-card** keyed by `resolution`, invalidata quando cambia il riferimento di `data`, come già fissato da `[00]` (`impl_plan_chart_resolution_00_foundation.md:9-10,144-159`). Qui è ancora più importante perché costo × numero di card. |
| Ottimizzazione futura fuori scope | Possibile in futuro una cache/shared batch per lista (`assetId/pairSlug + sourceRef + resolution`), ma **non ora**: questo documento resta su memo locale nel componente, senza introdurre store globali nuovi. |

## Ordine di implementazione

```text
[00] Foundation
  └─ ChartResolution + aggregateLineSeries() + computeDensity() + cache locale
          │
          ▼
STEP 1 Compact policy statica
  └─ chooseStaticResolution() width-aware, senza hysteresis
          │
          ▼
STEP 2 LineChart compact branch
  ├─ memoized daily/weekly/monthly main data
  ├─ first render direttamente nella risoluzione scelta
  └─ resize path: width change → recompute only if resolution target changes
          │
          ▼
STEP 3 Overlay compact
  └─ downsample output segnali via [04], allineato alle date bucketizzate
          │
          ▼
STEP 4 Consumer validation
  ├─ AssetCard: nessuna nuova API pubblica chart/range
  ├─ FxCard: stesso pattern
  └─ /assets + /fx: range pagina continua a propagarsi via dati filtrati
```

`[05]` qui è solo **valutato e scartato** per il badge pill, non dipendenza implementativa.

---

## STEP 1 — Formalizzare policy “static density” per le card compatte

### 1.1 Trigger reali da cui dipende la risoluzione

- **Riuso**: studio §3/§5/§19 chiede scelta iniziale prima del primo render, basata su larghezza reale + densità (`study_chart_dynamic_resolution.md:366-399`, `:424-467`, `:1178-1202`).
- **Riuso**: nelle liste il range pagina produce già nuovi array filtrati:
  - asset: `handleDateRangeChange()` → `fetchAllPriceData()` → `chartData` (`frontend/src/routes/(app)/assets/+page.svelte:505-541`);
  - fx: `handleDateRangeChange()` → `fetchAllPairData()` → `pair.data` (`frontend/src/routes/(app)/fx/+page.svelte:316-353`, `:536-547`).
- **Decisione operativa**: il compact chart **non** riceve `dateStart`/`dateEnd` come input funzionale della risoluzione; usa `data` come proxy canonico del range corrente. Questo evita nuove prop su `PriceChartCompact` / `LineChart` e mantiene invariata la superficie pubblica dei card consumer.

### 1.2 Helper dedicato: `chooseStaticResolution(...)`

- **Nuovo**: helper specifico compact-card, collocato nello stesso perimetro del wiring `LineChart`/`PriceChartCompact` (o in utility locale sorella), che:
  1. misura `plotWidthPx`;
  2. calcola `densityDaily = computeDensity(dailyPointCount, plotWidthPx)`;
  3. se `densityDaily <= 1.30`, ritorna `daily`;
  4. altrimenti valuta bucket count `weekly` e `densityWeekly`;
  5. se `densityWeekly <= 1.30`, ritorna `weekly`;
  6. altrimenti ritorna `monthly`.
- **Riuso**: `computeDensity()` e union `ChartResolution` vengono riusati **senza alias** da `[00]` (`impl_plan_chart_resolution_00_foundation.md:45-63,354-370`).
- **Scarto esplicito**: **non** riusare `chooseResolution(current, ...)` di `[00]` (`impl_plan_chart_resolution_00_foundation.md:60-61,372-396`) passando un finto `current='daily'`. Farlo introdurrebbe uno stato “sticky” artificiale dove il consumer, in realtà, vuole solo una funzione pura degli input correnti.

### 1.3 Prima renderizzazione corretta, non “daily poi switch”

- **Riuso**: studio §3 vieta render daily seguito da immediato swap weekly/monthly (`study_chart_dynamic_resolution.md:368-399`).
- **Nuovo**: il compact branch deve quindi:
  - misurare la larghezza reale del container appena ECharts/DOM è disponibile;
  - scegliere subito la risoluzione target;
  - renderizzare direttamente la serie `daily|weekly|monthly` già giusta.
- **Riuso**: `animation: false` già presente in `LineChart` evita morphing e soddisfa anche la regola §4 (`frontend/src/lib/components/charts/LineChart.svelte:444-445`; `study_chart_dynamic_resolution.md:402-420`).

---

## STEP 2 — Integrare aggregazione + resize nel ramo `compact === true` di `LineChart.svelte`

### 2.1 Memo locale per-card

- **Riuso**: `[00]` fissa memo locale keyed by resolution, invalidata su cambio reference dell’array sorgente (`impl_plan_chart_resolution_00_foundation.md:9-10,144-159`).
- **Nuovo**: nel compact branch la cache minima attesa è:

```text
lastSourceRef
aggregatedByResolution: Map<'daily'|'weekly'|'monthly', LineDataPoint[]>
lastMeasuredWidthPx
lastChosenResolution
```

- **Regola**:
  - `daily` = array sorgente invariato;
  - `weekly` / `monthly` = lazy via `aggregateLineSeries(data, resolution)`;
  - se `data !== lastSourceRef` → `clear()` completo cache + risoluzione.

### 2.2 Main series: solo fine-periodo

- **Riuso**: la regola per linee/NAV/serie cumulative è già fissata dallo studio §11.1 e da `[00]`: valore = ultimo punto disponibile nel bucket (`study_chart_dynamic_resolution.md:681-715`; `impl_plan_chart_resolution_00_foundation.md:76-87,203-255`).
- **Nuovo**: il compact branch passa a `buildMainSeries()` il dataset già aggregato, non il daily pieno.
- **Scarto esplicito**:
  - niente `aggregateOHLCV()` (`impl_plan_chart_resolution_00_foundation.md:57-58,258-281`) perché la card non mostra candele;
  - niente `aggregateEnvelope()` per la serie principale; vale solo per segnali band/Bollinger via `[04]`.

### 2.3 Resize: non solo `chartInstance.resize()`

- **Riuso**: `ResizeObserver` esiste già (`frontend/src/lib/components/charts/LineChart.svelte:187-202`).
- **Nuovo**: nel ramo compact il callback resize deve biforcarsi:
  1. misurare nuova width;
  2. se width invariata (o non significativa) → solo `chartInstance.resize()`;
  3. se width cambiata → ricalcolare `chooseStaticResolution(...)`;
  4. se la risoluzione target resta identica → solo `resize()`;
  5. se cambia (`daily ↔ weekly ↔ monthly`) → recuperare/calcolare serie aggregata da cache e rilanciare `renderChart()`.
- **Motivo**: su pagina lista la griglia responsive 1/2/3 colonne cambia la larghezza card senza cambiare `data`; affidarsi al solo effect su `data` lascerebbe risoluzioni stale (`frontend/src/routes/(app)/assets/+page.svelte:1183-1205`, `frontend/src/routes/(app)/fx/+page.svelte:883-901`).

### 2.4 Costo × N card: ottimizzare il path “no resolution change”

- **Nuovo**: quando il resize non supera la soglia verso una nuova risoluzione, la card non deve rigenerare weekly/monthly inutilmente; basta ridimensionare canvas.
- **Riuso**: questo si appoggia alla cache locale già decisa in `[00]`.
- **Nota architetturale**: è qui che il caso “lista con decine di card” diverge dai chart full-page; il resize può colpire molte istanze insieme, quindi il fast-path “solo resize, nessuna re-aggregazione” è parte del piano, non micro-ottimizzazione opzionale.

---

## STEP 3 — Overlay signals compact: riuso stretto di `[04]`

### 3.1 Nessun ricalcolo matematico dei segnali

- **Riuso**: `AssetCard` e `FxCard` calcolano già `overlaySignals` da dati absolute daily tramite `renderSignals(...)` (`frontend/src/lib/components/assets/AssetCard.svelte:89-99`, `frontend/src/lib/components/fx/FxCard.svelte:116-131`).
- **Riuso**: `[04]` ha già deciso che i segnali restano calcolati daily e si downsamplea solo il `RenderedSignal` output (`impl_plan_chart_resolution_04_signals_overlay.md:20-24,92-120,186-218`).
- **Nuovo**: il compact branch deve quindi:
  - scegliere prima la risoluzione main data;
  - ottenere `bucketedDates` dalla serie aggregata;
  - applicare `downsampleRenderedSignal(signal, resolution, bucketedDates)` a ogni overlay;
  - poi chiamare l’attuale costruzione ECharts overlay.

### 3.2 Allineamento al nuovo asse X bucketizzato

- **Riuso**: `LineChart` allinea già overlay a `dates` via map `date -> value` (`frontend/src/lib/components/charts/LineChart.svelte:291-296`).
- **Nuovo**: quando `dates` non è più daily ma weekly/monthly, passare overlay non downsampled produrrebbe buchi/non-allineamenti sistematici. Quindi il downsample locale non è opzionale: è il prerequisito per far funzionare l’asse compatto aggregato con gli stessi helper esistenti.

### 3.3 Tooltip / markers / measure mode

- **Tooltip**: **non applicabile** nel compact branch (`frontend/src/lib/components/charts/LineChart.svelte:579-659`).
- **Event markers**: non presenti nel mini-chart compatto attuale; nessun piano dedicato qui.
- **Measure mode**: assente nel mini-chart; nessun adattamento richiesto.

---

## STEP 4 — Propagazione minima nei consumer `AssetCard` / `FxCard` e verifica flussi pagina

### 4.1 `AssetCard.svelte`

- **Riuso**: mantiene invariata l’API pubblica corrente (`asset`, `chartData`, `dateStart`, `dateEnd`, `chartSettings`, `renderSignals`, ...), e continua a passare `displayData` + `overlaySignals` a `PriceChartCompact` (`frontend/src/lib/components/assets/AssetCard.svelte:36-68`, `:89-99`, `:235-239`).
- **Decisione**: nessuna nuova prop `resolution`, nessuna nuova prop `dateRange`, nessun badge prop.
- **Motivo**: il dato range-aware è già `chartData`; la risoluzione è responsabilità interna del chart, non della card.

### 4.2 `FxCard.svelte`

- **Riuso**: stesso principio di `AssetCard`; API invariata, `PriceChartCompact` continua a ricevere `chartData` derivato e `overlaySignals` (`frontend/src/lib/components/fx/FxCard.svelte:25-55`, `:104-131`, `:234-238`).
- **Decisione**: nessuna prop nuova anche qui; inversione base/quote e `%/absolute` restano responsabilità della card, aggregazione temporale responsabilità del chart.

### 4.3 Pagine `/assets` e `/fx`

- **Riuso**: i due route file già fanno tutto il necessario lato page-range:
  - picker compact con preset / store / URL sync (`frontend/src/routes/(app)/assets/+page.svelte:137-155,529-541,932-935`; `frontend/src/routes/(app)/fx/+page.svelte:67-85,536-547`);
  - fetch filtrata per range (`frontend/src/routes/(app)/assets/+page.svelte:411-525`; `frontend/src/routes/(app)/fx/+page.svelte:316-378`);
  - griglia responsive che determina la width effettiva delle card (`frontend/src/routes/(app)/assets/+page.svelte:1183-1205`; `frontend/src/routes/(app)/fx/+page.svelte:883-901`).
- **Conclusione**: nessun nuovo wiring pagina→card→chart oltre a quello già esistente. Il comportamento desiderato nasce da dati filtrati + width misurata localmente.

---

## Nota finale

Questo documento pianifica solo integrazione compact-card e **non** ridefinisce il contratto fondativo di `[00]`, né il dispatch overlay di `[04]`, né il componente badge di `[05]`.

**Nessuna riga di codice scritta in questo task.**
