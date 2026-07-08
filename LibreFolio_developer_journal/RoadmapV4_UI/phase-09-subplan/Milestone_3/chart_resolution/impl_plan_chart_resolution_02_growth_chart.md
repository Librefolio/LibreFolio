# Piano Implementativo: Chart Resolution 02 — GrowthChart (Milestone_3)

> **Deriva da**: [`study_chart_dynamic_resolution.md`](./study_chart_dynamic_resolution.md) — sezioni [3. Risoluzione iniziale](./study_chart_dynamic_resolution.md#3-risoluzione-iniziale-al-primo-rendering), [4. Switch senza animazione](./study_chart_dynamic_resolution.md#4-switch-di-risoluzione-senza-animazione), [7. Debounce dataZoom](./study_chart_dynamic_resolution.md#7-debounce-sugli-eventi-datazoom), [11.1 Linee/NAV fine-periodo](./study_chart_dynamic_resolution.md#111-linee-prezzo-nav-e-serie-cumulative), [14. Tooltip bucket-aware](./study_chart_dynamic_resolution.md#14-tooltip-bucket-aware), [18. Badge](./study_chart_dynamic_resolution.md#18-badge-di-aggregazione), [19. Flusso apertura](./study_chart_dynamic_resolution.md#19-flusso-completo-allapertura), [20. Flusso zoom/pan/resize](./study_chart_dynamic_resolution.md#20-flusso-completo-durante-zoompanresize).
>
> **Prerequisito vincolante**: [`impl_plan_chart_resolution_00_foundation.md`](./impl_plan_chart_resolution_00_foundation.md) — contratto condiviso `timeSeriesAggregation.ts`, soglie isteresi `1.30 / 0.80`, debounce `200ms`, cache locale keyed by resolution.
>
> **Integrazione UI obbligatoria**: [`impl_plan_chart_resolution_05_badge_i18n.md`](./impl_plan_chart_resolution_05_badge_i18n.md) — badge top-left, solo `weekly`/`monthly`, testi i18n condivisi.
>
> **Ambito**: solo `frontend/src/lib/components/dashboard/GrowthChart.svelte`, con implementazione autonoma. Nessun riuso di `chartCoreHelpers.ts` / `lineChartHelpers.ts` per questo grafico, coerente con responsabilità dedicate già fissate per `GrowthChart` nello studio (`study_chart_dynamic_resolution.md:1317-1325`).

## Principio guida

> Inserire semantic zoom in `GrowthChart` con minima invasività: riusare lifecycle, differenza full-init vs partial-update, `ResizeObserver`, wrapper DOM già presenti; introdurre solo stato locale, cache locale, listener `dataZoom`, adapter serie e tooltip bucket-aware strettamente necessari. Nessun nuovo store globale, nessuna convergenza forzata con pipeline `PriceChartFull`.

## Stato attuale verificato

- `history` entra come `PortfolioHistoryPoint[]`; `dates` deriva direttamente da `history.map((pt) => pt.date)` (`frontend/src/lib/components/dashboard/GrowthChart.svelte:32-39,117`).
- Modalità EUR già costruita come 5 array numerici puri (`bookAssetLike`, `cashContributed`, `cashGenerated`, `nav`, `capitalBaseline`) più `totalPnl`, tutti derivati localmente da `history` (`frontend/src/lib/components/dashboard/GrowthChart.svelte:134-141`).
- Modalità `%` già costruita come 3 serie indipendenti (`mwrrCum`, `twrr`, `roi`), poi filtrate via `pctSeries` se interamente nulle (`frontend/src/lib/components/dashboard/GrowthChart.svelte:166-190`).
- Pattern render esistente già distingue:
  - **full init** su cambio `viewMode` / dark mode (`needsFullInit`) (`frontend/src/lib/components/dashboard/GrowthChart.svelte:256-260`);
  - **partial update data-only** via `chartInstance.setOption({ series: ... })` in entrambi i branch EUR / `%` (`frontend/src/lib/components/dashboard/GrowthChart.svelte:275-323,330-345`).
- Le prime 3 serie EUR sono stacked con `stack: 'bookValue'`; NAV e baseline sono linee overlay separate (`frontend/src/lib/components/dashboard/GrowthChart.svelte:277-315`).
- Tooltip attuale è **inline/manuale** dentro `applyFullOption().tooltip.formatter`; gli helper condivisi `buildTooltipTheme`, `buildDot`, `buildTooltipHeader`, `buildTooltipRow`, `buildTooltipDivider` sono importati ma non usati realmente nel formatter corrente (`frontend/src/lib/components/dashboard/GrowthChart.svelte:23-27,376-445`).
- `dataZoom` oggi è solo configurazione statica `inside` con `start: 0, end: 100`; nel file non esiste alcun `chartInstance.on('dataZoom', ...)` (`frontend/src/lib/components/dashboard/GrowthChart.svelte:455`; verifica grep sull’intero file: nessun listener registrato).
- `ResizeObserver` esiste già e chiama `chartInstance?.resize()`; quindi `chartInstance.getWidth()` è misurabile senza nuova infra di resize (`frontend/src/lib/components/dashboard/GrowthChart.svelte:51,228-235`).
- Area chart è già dentro wrapper `.relative`, adatto a badge overlay top-left senza toccare canvas ECharts (`frontend/src/lib/components/dashboard/GrowthChart.svelte:571-581`).

## Gap rispetto al contratto shared

- Manca stato locale `resolution` + cache locale memoizzata keyed by resolution e invalidata al cambio riferimento `history`.
- Manca scelta risoluzione iniziale **prima** del primo rendering utile, come richiesto dallo studio (`study_chart_dynamic_resolution.md:366-399,1178-1202`).
- Manca listener `dataZoom` con debounce `200ms`, calcolo density via `chartInstance.getWidth()`, isteresi `daily ↔ weekly ↔ monthly`, preservazione range logico con date assolute (`study_chart_dynamic_resolution.md:470-549,597-633,1206-1228`).
- Manca aggregazione fine-periodo delle 5 serie EUR e delle 3 serie `%` (`study_chart_dynamic_resolution.md:679-715`).
- Manca switch semantic zoom senza animazione: oggi il branch partial update è esplicitamente pensato per transizione “smooth” (`frontend/src/lib/components/dashboard/GrowthChart.svelte:319,342`; `study_chart_dynamic_resolution.md:402-420`).
- Manca tooltip bucket-aware weekly/monthly; oggi header = singola data puntuale (`frontend/src/lib/components/dashboard/GrowthChart.svelte:397-445`; `study_chart_dynamic_resolution.md:915-949`).
- Manca badge non-daily top-left (`study_chart_dynamic_resolution.md:1140-1174`).

## Decisioni prese (non più aperte)

| Decisione | Scelta |
|---|---|
| Cache aggregazioni | **Locale al componente**, keyed by `resolution`, invalida solo quando cambia il riferimento di `history` in ingresso; nessun nuovo store globale |
| Risoluzione iniziale | Calcolata dopo `echarts.init()` ma **prima** di costruire `series` per il primo render; niente render daily→switch immediato |
| Switch di risoluzione | Riuso del path **partial update esteso** (serie + riallineamento zoom + stato tooltip/badge), **non** full dispose/init; motivazione: struttura serie/stili restano invariati per singolo `viewMode` |
| Animazione nello switch | **Disabilitata** per ogni cambio `daily/weekly/monthly`; animazione iniziale resta solo sul primo render già nella risoluzione corretta |
| Regola aggregazione linee | `aggregateLineSeries(..., resolution)` con valore **fine-periodo** per tutte le 5 serie EUR e tutte le 3 serie `%` |
| Fonte canonica | `history` daily resta sorgente unica; viste weekly/monthly solo derivate client-side |
| Tooltip aggregato | Header bucket-aware derivato dalla risoluzione corrente: daily = data singola; weekly = range ISO week + “valore al …”; monthly = mese + “valore al …” |
| Badge | Overlay DOM nel wrapper `.relative`, visibile solo per `weekly` / `monthly`; testi e token grafici demandati al doc 05 |

## Ordine di implementazione

```text
Doc 00 foundation (prerequisito)
        │
        ▼
STEP 1 Stato locale + invalidazione cache + selezione risoluzione iniziale
        │
        ▼
STEP 2 Listener dataZoom + debounce 200ms + density + isteresi + range assoluto
        │
        ▼
STEP 3 Aggregazione serie EUR / % + riuso partial-update senza animazione
        │
        ▼
STEP 4 Tooltip bucket-aware
        │
        ▼
STEP 5 Badge non-daily (integrazione doc 05)
```

---

## STEP 1 — Stato locale, cache, bootstrap iniziale

### 1.1 Stato minimo nuovo

- **Riuso**: `renderChart()`, `chartInstance`, `lastRenderedMode`, `lastRenderedDark`, `dates`, `eurStackedData`, `pctSeries`, lifecycle già presente (`frontend/src/lib/components/dashboard/GrowthChart.svelte:117,134-190,198-220,238-351`).
- **Nuovo**:
  - `currentResolution: ChartResolution = 'daily'`;
  - `lastHistoryRef: PortfolioHistoryPoint[] | null`;
  - cache locale per risoluzione (entry contenente almeno date aggregate + serie EUR + serie `%`);
  - stato range logico assoluto (`visibleStartDate`, `visibleEndDate`);
  - timer debounce per `dataZoom`.

### 1.2 Invalidation contract

- **Nuovo**: se `history !== lastHistoryRef`, svuotare cache locale, resettare `currentResolution`/range logico, aggiornare riferimento sorgente.
- **Motivo**: il parent ricarica già `history` fresco su cambio broker/periodo/valuta/refresh; non serve altra invalidazione cross-component.

### 1.3 Primo render nella risoluzione corretta

- **Riuso**: `echarts.init(...)` e `setupResizeObserver()` già esistono (`frontend/src/lib/components/dashboard/GrowthChart.svelte:248-254,228-235`).
- **Nuovo**:
  1. inizializzare `chartInstance`;
  2. leggere `plotWidthPx = chartInstance.getWidth()`;
  3. calcolare `counts.{dailyCount,weeklyCount,monthlyCount}` sul range iniziale visibile (di default
     l'intero dataset, dato che `dataZoom` parte 0→100), raggruppando le date con `mapDateToBucket()`;
  4. calcolare densità via `computeDensity(...)` (fatto internamente da `chooseResolution`);
  5. scegliere `currentResolution = chooseResolution('daily', counts, plotWidthPx)`;
  6. materializzare dati della risoluzione scelta prima di `applyFullOption(...)`.
- **Vincolo**: nessun render intermedio daily se il range iniziale richiede weekly/monthly (`study_chart_dynamic_resolution.md:366-399`).

---

## STEP 2 — dataZoom, debounce, isteresi, range logico

### 2.1 Listener mancante

- **Riuso**: `dataZoom: [{ type: 'inside', start: 0, end: 100 }]` esiste già (`frontend/src/lib/components/dashboard/GrowthChart.svelte:455`).
- **Nuovo**: registrare `chartInstance.on('dataZoom', ...)` subito dopo init / full bind eventi, con cleanup coerente in dispose/unmount.

### 2.2 Debounce 200ms

- **Nuovo**: handler debounced a `200ms` fisso, allineato al contratto shared; durante drag/scroll ECharts continua a gestire vista corrente, la logica di risoluzione scatta solo a stabilizzazione (`study_chart_dynamic_resolution.md:527-549`).

### 2.3 Range logico assoluto

- **Nuovo**:
  - leggere range visibile corrente da ECharts;
  - convertirlo in `visibleStartDate` / `visibleEndDate` assoluti;
  - conservarli separati dalla serie renderizzata;
  - su switch di risoluzione, rimappare il range logico su bucket target, mai su percentuali nude.
- **Motivo**: numero punti cambia tra daily/weekly/monthly; preservare solo `start/end` percentuali sarebbe instabile (`study_chart_dynamic_resolution.md:597-633`).

### 2.4 Density + chooseResolution

- **Riuso**: `ResizeObserver` già garantisce `chartInstance.resize()`; il width aggiornato è quindi leggibile da `chartInstance.getWidth()` (`frontend/src/lib/components/dashboard/GrowthChart.svelte:228-235`).
- **Nuovo**:
  - calcolo `counts.{dailyCount,weeklyCount,monthlyCount}` nel range logico corrente (raggruppando con
    `mapDateToBucket()`);
  - `plotWidthPx = chartInstance.getWidth()`;
  - `targetResolution = chooseResolution(currentResolution, counts, plotWidthPx)`.

### 2.5 Resize path

- **Nuovo**: rieseguire la stessa pipeline di scelta risoluzione anche dopo resize stabile significativo, senza duplicare logica separata dal branch `dataZoom`.
- **Riuso**: observer esistente, nessun nuovo observer parallelo.

---

## STEP 3 — Aggregazione serie e switch no-animation

### 3.1 Adapter daily → LineDataPoint[] per GrowthChart

- **Riuso**: sorgenti daily già disponibili come array numerici puri + `dates` (`frontend/src/lib/components/dashboard/GrowthChart.svelte:117,134-141,166-187`).
- **Nuovo**: adapter locale che converte ogni serie in input `aggregateLineSeries()` e riconverte output in `namedPoint(...)` per ECharts.
- **Nota**: questo adapter vive nel componente; non introduce helper condivisi extra oltre al contratto doc 00.

### 3.2 Aggregazione EUR

- **Riuso**: struttura 5 serie/stili/stack già esistente (`frontend/src/lib/components/dashboard/GrowthChart.svelte:267-315`).
- **Nuovo**: aggregare tutte le 5 serie EUR con `aggregateLineSeries(..., currentResolution)`:
  1. `bookAssetLike`
  2. `cashContributed`
  3. `cashGenerated`
  4. `nav`
  5. `capitalBaseline`
- **Regola**: fine-periodo per ogni bucket, coerente con GrowthChart/NAV/serie cumulative (`study_chart_dynamic_resolution.md:679-699`).

### 3.3 Aggregazione %

- **Riuso**: nomi serie già definiti come `mwrrCum`, `twrr`, `roi` e filtro `pctSeries` già presente (`frontend/src/lib/components/dashboard/GrowthChart.svelte:166-187`).
- **Nuovo**: aggregare ciascuna serie `%` con la stessa utility fine-periodo, senza cambiare etichette, colori o lineStyle.

### 3.4 Cache locale per resolution

- **Nuovo**: memoizzare risultati per `daily`, `weekly`, `monthly`; `daily` può essere trattata come vista passthrough memoizzata per uniformità.
- **Motivo**: evitare ricalcolo su ogni pan/zoom; ricalcolo solo primo accesso per risoluzione o dopo invalidazione dataset.

### 3.5 Riuso partial-update, ma senza animazione di switch

- **Riuso**: path `chartInstance.setOption({ series: ... })` già esistente per update dati (`frontend/src/lib/components/dashboard/GrowthChart.svelte:320-323,343-345`).
- **Nuovo**:
  - branch dedicato `resolutionChanged`;
  - aggiornare serie aggregate + riallineare zoom/range logico sul nuovo dataset;
  - forzare switch **senza animazione**;
  - evitare dispose/init completo perché struttura serie, stack e assi restano uguali nel singolo `viewMode`.
- **Nota**: il commento attuale “smooth transition” va considerato incompatibile col semantic zoom (`frontend/src/lib/components/dashboard/GrowthChart.svelte:319,342`; `study_chart_dynamic_resolution.md:402-420`).

---

## STEP 4 — Tooltip bucket-aware

### 4.1 Spostare formatter su semantica bucket-aware

- **Riuso**: `tooltipPositionSide`, `setupTooltipAutoHide`, tema/shared builders disponibili in `echartsTooltipHelpers.ts` (`frontend/src/lib/components/dashboard/GrowthChart.svelte:26,251-253,391`; `frontend/src/lib/components/charts/echartsTooltipHelpers.ts:22-61,184-212`).
- **Nuovo**:
  - header giornaliero: data singola (invariato, nessuna chiave nuova);
  - header weekly: `chart.tooltip.weekRange` (`{start}`/`{end}`) + riga `chart.tooltip.valueAt` (`{date}`) —
    stesse chiavi i18n fissate in `impl_plan_chart_resolution_05_badge_i18n.md`, non testo locale;
  - header monthly: `chart.tooltip.monthLabel` (`{month}`) + riga `chart.tooltip.valueAt` (`{date}`).

### 4.2 EUR mode

- **Riuso**: contenuto economico attuale del tooltip (NAV, baseline, total P&L, breakdown stacked) (`frontend/src/lib/components/dashboard/GrowthChart.svelte:404-432`).
- **Nuovo**: cambiare solo intestazione/semantica bucket-aware, mantenendo breakdown e colori esistenti.

### 4.3 % mode

- **Riuso**: elenco serie con dot colorati (`frontend/src/lib/components/dashboard/GrowthChart.svelte:435-444`).
- **Nuovo**: stesso header bucket-aware del branch EUR; corpo resta lista serie `%`.

### 4.4 Direzione implementativa

- **Scelta**: convergere il formatter sugli helper `buildTooltipTheme` / `buildTooltipHeader` / `buildTooltipRow` / `buildTooltipDivider` già importati, così il bucket-aware non resta altro HTML hardcoded duplicato.

---

## STEP 5 — Badge non-daily

### 5.1 Overlay DOM, non graphic ECharts

- **Riuso**: wrapper `.relative` della chart area (`frontend/src/lib/components/dashboard/GrowthChart.svelte:571-581`).
- **Nuovo**: badge assoluto top-left come sibling DOM del container chart, visibile solo quando `currentResolution !== 'daily'`.

### 5.2 Integrazione doc 05

- **Nuovo**: testi/chiavi i18n/stile finale presi dal doc 05 senza ridefinirli qui.
- **Regola**:
  - `daily` → nessun badge
  - `weekly` → badge “Settimanale”
  - `monthly` → badge “Mensile”

---

## Riepilogo Nuovo vs Riuso

### Riuso invariato

- `history` daily come sorgente canonica.
- `eurStackedData`, `pctSeries`, colori, stack EUR, toggle `viewMode`.
- `renderChart()` come punto centrale.
- distinzione `needsFullInit` vs `setOption({series})`.
- `ResizeObserver`, mobile tooltip auto-hide, wrapper DOM `.relative`.

### Nuovo minimo indispensabile

- stato `currentResolution`;
- cache locale keyed by resolution;
- invalidazione su cambio riferimento `history`;
- listener `dataZoom` debounced `200ms`;
- calcolo density / isteresi via contratto doc 00;
- aggregazione fine-periodo 5 serie EUR + 3 serie `%`;
- riallineamento range logico con date assolute;
- tooltip bucket-aware;
- badge non-daily.

## Nota finale

Documento di pianificazione soltanto. **Nessuna riga di codice scritta in questo task.**
