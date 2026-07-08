# Piano Implementativo: Risoluzione dinamica `AllocationHistoryChart` (Milestone_3)

> **Deriva da**: [`./study_chart_dynamic_resolution.md`](./study_chart_dynamic_resolution.md) — sez. 3 _Risoluzione iniziale al primo rendering_ (`:366-398`), sez. 4 _Switch di risoluzione senza animazione_ (`:402-420`), sez. 7 _Debounce sugli eventi dataZoom_ (`:527-553`), sez. 11.3 _AllocationHistoryChart_ (`:735-752`), sez. 14 _Tooltip bucket-aware_ (`:915-950`), sez. 18 _Badge di aggregazione_ (`:1140-1175`), sez. 19 _Flusso completo all’apertura_ (`:1178-1202`), sez. 20 _Flusso completo durante zoom/pan/resize_ (`:1206-1228`).
> **Prerequisito condiviso**: [`./impl_plan_chart_resolution_00_foundation.md`](./impl_plan_chart_resolution_00_foundation.md) (`[00]`, contratto shared `ChartResolution` / `aggregateLineSeries()` / `computeDensity()` / `chooseResolution()` già fissato, da usare senza ridefinizioni).
> **Integrazione correlata**: [`./impl_plan_chart_resolution_05_badge_i18n.md`](./impl_plan_chart_resolution_05_badge_i18n.md) (`[05]`, badge top-left visibile solo in weekly/monthly).
> **Ambito**: solo `frontend/src/lib/components/dashboard/AllocationHistoryChart.svelte`, con implementazione indipendente dagli altri chart lato wiring ECharts.

## Principio guida

> Tenere `AllocationHistoryChart.svelte` autonomo nel wiring locale (`state`, `dataZoom`, `tooltip`, `badge`), ma allineato al contratto comune di `[00]`: risoluzione `daily|weekly|monthly`, densità bucket/px, isteresi 1.30/0.80, debounce 200ms, range logico preservato via date assolute, aggregazione **fine-periodo** per ogni serie stacked, cache locale keyed by resolution e invalidata solo quando cambia il riferimento di `data`.

Ogni step sotto dichiara esplicitamente cosa è **Riuso** vs cosa è **Nuovo**.

## Stato attuale (verificato)

- **Input dati già adatto a un bucketing per serie-categoria**: il componente riceve `AllocationHistoryPoint[]`, dove ogni punto contiene `date` + `components: AllocationComponent[]` (`frontend/src/lib/components/dashboard/AllocationHistoryChart.svelte:25-34, 36-45`).
- **Serie dinamiche per nome categoria**: `categoryNames` nasce da `Set` sui `components`, poi `sortedNames` ordina le categorie e costruisce `seriesDataByName[name]` cercando il valore di quella categoria in ogni giorno (`.../AllocationHistoryChart.svelte:83-90, 167-185`). Questo conferma che l’aggregazione va applicata **per ogni categoria**, non sul totale stacked.
- **Rendering stacked già esplicito**: ogni serie ECharts usa `type: 'line'` + `stack: 'allocation'` (`.../AllocationHistoryChart.svelte:207-215`), quindi la semantica da preservare è “100%-stacked area nel tempo”.
- **Etichette emoji già interne alle serie**: `showLabel` dipende da `avgWeights[name] >= 3` e il `formatter` restituisce solo l’emoji (`.../AllocationHistoryChart.svelte:208-223`). Con meno bucket non serve nuova logica dedicata: basta rigenerare le serie sulla risoluzione attiva.
- **`dimension` è solo asse semantico delle categorie**: prop opzionale `'type' | 'sector' | 'geo'` (`.../AllocationHistoryChart.svelte:36-45`), usata da `getCategoryEmoji()` e `localizeName()` per localizzare/abbellire i nomi (`.../AllocationHistoryChart.svelte:58-81, 131-147`). Non partecipa oggi ad alcuna logica temporale.
- **Tooltip oggi non bucket-aware**: il formatter legge `axisValue`, lo converte in `date`, poi usa `buildTooltipHeader(date, ...)` e righe percentuali calcolate via `rawDataByName[name][idx]` (`.../AllocationHistoryChart.svelte:239-270`). Header e testo implicano una singola data, non settimana/mese.
- **`dataZoom` oggi è solo statico**: `dataZoom: [{type: 'inside', start: 0, end: 100}]` senza listener associati (`.../AllocationHistoryChart.svelte:273-275`). Nell’intero file non esiste alcun `chartInstance.on('dataZoom', ...)` o debounce dedicato (`.../AllocationHistoryChart.svelte:97-129, 149-284`).
- **Misura larghezza già parzialmente presente**: `ResizeObserver` esiste già, ma oggi chiama solo `chartInstance?.resize()` (`.../AllocationHistoryChart.svelte:120-125`). È riusabile per rileggere `chartInstance.getWidth()` senza introdurre un observer nuovo.
- **Nessun badge oggi in markup**: il wrapper finale contiene solo skeleton/no-data/chart container (`.../AllocationHistoryChart.svelte:287-296`).
- **Asse Y già coerente con feature**: `yAxis.max = 100` con formatter percentuale (`.../AllocationHistoryChart.svelte:275`), quindi il bucket aggregato deve rappresentare “% categoria all’ultimo giorno disponibile del bucket”, non una media aritmetica di importi o valori assoluti.

## Gap

- Manca completamente stato locale di risoluzione (`daily|weekly|monthly`), range logico visibile, timer debounce, cache memoizzata per risoluzione.
- Primo render sempre su dati daily grezzi: nessuna scelta iniziale della risoluzione prima di `setOption`, in contrasto con studio sez. 3.
- Manca listener `dataZoom` → nessun ricalcolo densità, nessuna isteresi, nessuna preservazione del range tramite date assolute.
- Serie stacked oggi sono sempre costruite dal dataset raw giornaliero; manca passaggio “daily canonico → serie aggregate per categoria”.
- Tooltip assume data puntuale; manca header esplicito per bucket weekly/monthly.
- Manca badge top-left weekly/monthly.
- `dimension` non crea problemi, ma va dichiarata esplicitamente come **ortogonale** alla risoluzione per evitare accoppiamenti inutili nel piano implementativo.

## Decisioni prese (non più aperte)

| Decisione | Scelta |
|---|---|
| Valore aggregato per `AllocationHistoryChart` | **Fine-periodo, non media**: ogni bucket weekly/monthly mostra la percentuale della categoria all’ultimo giorno disponibile del bucket, in coerenza con studio sez. 11.3 (`study_chart_dynamic_resolution.md:735-752`) e con regola condivisa del semantic zoom. |
| Unità di aggregazione | Aggregazione applicata **per serie/categoria** usando `aggregateLineSeries()` di `[00]` sui punti di ciascun nome in `sortedNames`; nessuna media calcolata sul totale stacked. |
| Risoluzione iniziale | Scelta **prima del primo render** misurando `chartInstance.getWidth()` e usando `chooseResolution(...)`; vietato render daily e sostituire subito dopo. |
| Switch risoluzione | Netto, senza animazione di transizione tra daily/weekly/monthly; l’animazione globale del chart non deve raccontare il cambio di semantica temporale. |
| Trigger di cambio risoluzione | Solo `dataZoom` + `ResizeObserver`, entrambi con ricalcolo mediato da debounce 200ms e isteresi comune del contratto `[00]`. |
| Preservazione finestra | Conservare `visibleStartDate` / `visibleEndDate` assolute; mai affidarsi solo a `start/end` percentuali quando cambia il numero di bucket renderizzati. |
| Cache | Memoizzazione **locale al componente** keyed by `resolution`, invalidata quando cambia il riferimento dell’array `data`; nessun nuovo store globale. |
| `dimension` vs risoluzione | Assi indipendenti: `dimension` cambia nomi/emoji/localizzazione e normalmente anche dataset sorgente, ma non cambia algoritmo di bucketing temporale. |
| Tooltip | Header bucket-aware: daily = data singola; weekly = range ISO week + valore a fine bucket; monthly = mese calendario + valore a fine bucket. |
| Badge | Overlay top-left, mostrato solo se `resolution !== 'daily'`, con integrazione visual/i18n demandata a `[05]`. |

## Ordine di implementazione

```text
[00] shared timeSeriesAggregation contract
            │
            ▼
STEP 1 Stato locale + cache + primo render corretto
            │
            ▼
STEP 2 Aggregazione per N serie stacked dinamiche
            │
            ▼
STEP 3 dataZoom + debounce + isteresi + preserve-range
            │
            ▼
STEP 4 Interazione con `dimension` + tooltip bucket-aware
            │
            ▼
STEP 5 Badge top-left (aggancio a [05])
```

---

## STEP 1 — Stato locale risoluzione, cache, primo render

### 1.1 Stato minimo da introdurre

- **Riuso**: `chartInstance`, `ResizeObserver`, ciclo `onMount`/`$effect` esistenti (`frontend/src/lib/components/dashboard/AllocationHistoryChart.svelte:46-53, 97-129`).
- **Nuovo**:
  - `currentResolution: ChartResolution = 'daily'`;
  - `logicalRange: {startDate: string; endDate: string}` ricavato dal range visibile corrente;
  - cache locale tipo `Map<ChartResolution, AggregatedAllocationDataset>` o record equivalente;
  - riferimento `lastDataRef` per invalidare cache quando `data` cambia per identità;
  - eventuale guard `isResolutionSwitching` / opzione locale per forzare update senza animazione.

### 1.2 Primo render diretto nella risoluzione corretta

- **Riuso**: inizializzazione ECharts in `renderChart()` (`.../AllocationHistoryChart.svelte:149-162`) e misura larghezza via `chartInstance.getWidth()` richiesta dal contratto.
- **Nuovo**:
  1. dopo `echarts.init(...)`, misurare `plotWidthPx = chartInstance.getWidth()`;
  2. determinare `counts.{dailyCount,weeklyCount,monthlyCount}` dal dataset visibile all'apertura (qui, di
     default, storico intero perché `dataZoom` parte `0-100` — `.../AllocationHistoryChart.svelte:273`),
     raggruppando le date con `mapDateToBucket()`;
  3. chiamare `chooseResolution('daily', counts, plotWidthPx)`;
  4. costruire direttamente dataset active-resolution prima di assemblare `series`/`tooltip`/`option`.

Questo step chiude gap vs studio sez. 3 (`study_chart_dynamic_resolution.md:366-398`): niente render daily → rimpiazzo immediato weekly/monthly.

### 1.3 Invalidazione cache

- **Riuso**: il componente riceve già `data` come prop immutabile dall’esterno (`.../AllocationHistoryChart.svelte:44`).
- **Nuovo**: invalidare tutte le viste aggregate quando `data !== lastDataRef`. Nessuna invalidazione separata per `dimension`: se il parent cambia davvero dimensione, normalmente cambia anche il dataset; se cambia solo localizzazione/emoji, basta re-render senza ricostruire cache temporale.

---

## STEP 2 — Aggregazione di N serie stacked dinamiche

### 2.1 Trasformazione dataset daily → dataset per-resolution

- **Riuso**: la pipeline esistente `categoryNames` → `sortedNames` → `seriesDataByName` (`frontend/src/lib/components/dashboard/AllocationHistoryChart.svelte:83-90, 167-185`).
- **Nuovo**:
  - estrarre per ogni `name` una serie daily uniforme di `LineDataPoint` con `date` + `value` percentuale;
  - passare ogni serie a `aggregateLineSeries(points, resolution)` del contratto `[00]`;
  - ricostruire un dataset “per data bucket” usando l’unione delle date aggregate restituite dalla utility, così ogni bucket contiene i valori per tutte le categorie e può tornare a pilotare tooltip + serie stacked.

### 2.2 Regola esplicita “fine-periodo non media”

- **Riuso**: asse Y percentuale 0-100 (`.../AllocationHistoryChart.svelte:275`) e semantica stacked già esistente.
- **Nuovo**: documentare in implementazione che per ogni categoria vale:

  ```text
  valore bucket = percentuale categoria all’ultimo giorno disponibile del bucket
  ```

  non:

  ```text
  media percentuale categoria durante il bucket
  ```

Motivo: stesso semantic zoom degli altri chart, nessun lag percettivo, tooltip più chiaro, niente doppia semantica nascosta nello stesso rollout. La “media di periodo” resta eventualmente una feature analitica futura separata, fuori scope.

### 2.3 Serie stacked + label emoji

- **Riuso**: `stack: 'allocation'`, palette, `showLabel`, `formatter: () => emoji` (`.../AllocationHistoryChart.svelte:207-223`).
- **Nuovo**:
  - rigenerare `avgWeights` e `sortedNames` sul dataset active-resolution, non assumendo più sempre cardinalità daily;
  - mantenere invariata la soglia `avgWeights[name] >= 3` salvo evidenza contraria;
  - nessun fix speciale per le emoji: con meno punti ECharts continua a posizionare label “inside” sul layer stacked del bucket corrente.

### 2.4 Cache locale per risoluzione

- **Riuso**: nessuno store condiviso; l’indipendenza del componente resta intatta.
- **Nuovo**: salvare lazy i dataset `daily`, `weekly`, `monthly` già trasformati per `AllocationHistoryChart`, keyed by resolution. `daily` può essere vista canonica o voce cache pass-through; `weekly` e `monthly` si calcolano solo al primo bisogno.

---

## STEP 3 — `dataZoom`, debounce 200ms, isteresi, preserve-range

### 3.1 Listener `dataZoom`

- **Riuso**: configurazione `dataZoom` già presente (`frontend/src/lib/components/dashboard/AllocationHistoryChart.svelte:273`).
- **Nuovo**:
  - registrare `chartInstance.on('dataZoom', ...)` subito dopo il primo `setOption`/init;
  - leggere dal modello ECharts il range visibile corrente;
  - convertirlo in `visibleStartDate` / `visibleEndDate` assolute;
  - avviare debounce 200ms prima di ogni possibile cambio di risoluzione.

Questo colma gap totale segnalato da studio sez. 7 (`study_chart_dynamic_resolution.md:527-553`).

### 3.2 Calcolo densità + isteresi

- **Riuso**: utility condivise di `[00]`.
- **Nuovo**:
  - `plotWidthPx = chartInstance.getWidth()` ad ogni controllo rilevante;
  - `counts.{dailyCount,weeklyCount,monthlyCount}` riferiti alla finestra logica visibile, non all'intero
    storico, ricalcolati raggruppando con `mapDateToBucket()`;
  - `chooseResolution(currentResolution, counts, plotWidthPx)` come unico arbitro del cambio, ereditando
    soglia alta 1.30 e bassa 0.80 dal contratto.

### 3.3 Preserve-range con date assolute

- **Riuso**: `xAxis.type = 'time'` (`frontend/src/lib/components/dashboard/AllocationHistoryChart.svelte:274`), quindi il chart può ricevere direttamente date rappresentative di bucket.
- **Nuovo**:
  - mantenere nello stato interno sempre date logiche reali;
  - quando si passa di risoluzione, rimappare il range ai bucket weekly/monthly che intersecano quel range;
  - evitare di riapplicare solo percentuali `start/end`, che divergerebbero appena cambia il numero di punti.

### 3.4 Resize path

- **Riuso**: `ResizeObserver` già monta su `chartContainer` (`.../AllocationHistoryChart.svelte:122-125`).
- **Nuovo**: il callback non deve solo fare `resize()`, ma anche schedulare stesso controllo densità/isteresi del `dataZoom`, così resize stretto/largo può promuovere o retrocedere risoluzione senza store globale e senza polling.

### 3.5 Switch senza animazione

- **Riuso**: distinzione esistente tra data-only update e full init (`.../AllocationHistoryChart.svelte:187-199, 235-279`).
- **Nuovo**: introdurre un ramo esplicito “resolution change update” che aggiorna serie/xAxis/tooltip/badge senza animazione di transizione. Serve perché oggi il componente eredita `CHART_ANIMATION_CONFIG` (`.../AllocationHistoryChart.svelte:17, 235-236`), ma cambio di bucket semantico non va animato.

---

## STEP 4 — `dimension` ortogonale + tooltip bucket-aware

### 4.1 `dimension` resta asse indipendente

- **Riuso**: `dimension` governa soltanto emoji/localizzazione (`frontend/src/lib/components/dashboard/AllocationHistoryChart.svelte:58-81, 131-147`).
- **Nuovo**:
  - esplicitare nel codice che la scelta `daily|weekly|monthly` non dipende da `dimension`;
  - tenere separati: (a) pipeline temporale; (b) naming/localization/legend;
  - fare in modo che un eventuale cambio `type ↔ sector ↔ geo` riusi la stessa macchina di risoluzione senza branch dedicati.

### 4.2 Header tooltip bucket-aware

- **Riuso**: `buildTooltipTheme`, `buildTooltipTopN`, `buildTooltipByThreshold`, `tooltipPositionSide` (`frontend/src/lib/components/dashboard/AllocationHistoryChart.svelte:19, 239-270`).
- **Nuovo**:
  - header daily invariato (data singola);
  - header weekly = `chart.tooltip.weekRange` (`{start}`/`{end}`) + `chart.tooltip.valueAt` (`{date}`) —
    stesse chiavi i18n fissate in `impl_plan_chart_resolution_05_badge_i18n.md`;
  - header monthly = `chart.tooltip.monthLabel` (`{month}`) + `chart.tooltip.valueAt` (`{date}`);
  - lettura dei valori dal dataset active-resolution, non più da `rawDataByName` daily implicito.

Qui basta nuovo formatter/header helper locale minimo se quello condiviso non è ancora bucket-aware; nessun refactor trasversale obbligatorio imposto da questo documento.

### 4.3 Contenuto tooltip coerente con stacked allocation

- **Riuso**: ordinamento `sortedNames`, filtri per threshold/top-N, percentuali per riga (`.../AllocationHistoryChart.svelte:255-268`).
- **Nuovo**:
  - mantenere stessa logica di ordinamento/compattazione per non cambiare UX del pannello;
  - cambiare solo l’intestazione e la sorgente dati, che diventano bucket-aware;
  - chiarire nel testo/header che il punto weekly/monthly rappresenta “allocazione al termine del periodo”, non media intra-periodo.

---

## STEP 5 — Badge top-left

### 5.1 Overlay badge

- **Riuso**: wrapper `<div class="relative" ...>` già presente (`frontend/src/lib/components/dashboard/AllocationHistoryChart.svelte:287-296`).
- **Nuovo**:
  - inserire overlay top-left nel wrapper del componente;
  - mostrare badge solo se `currentResolution !== 'daily'`;
  - testo sintetico demandato a `[05]` (`Settimanale` / `Mensile`, non “Vista: ...”).

### 5.2 Momento di aggiornamento

- **Riuso**: stesso stato locale di `currentResolution` introdotto in STEP 1.
- **Nuovo**: badge segue esclusivamente la risoluzione effettivamente renderizzata, quindi si aggiorna insieme allo switch senza logica separata.

---

## Riepilogo Riuso / Nuovo

### Riuso confermato

- `AllocationHistoryPoint` / `AllocationComponent` come sorgente daily (`frontend/src/lib/components/dashboard/AllocationHistoryChart.svelte:25-34`).
- Pipeline categorie dinamiche `categoryNames` / `sortedNames` / `seriesDataByName` (`...:83-90, 167-185`).
- Serie stacked ECharts con palette e label emoji (`...:207-223`).
- `ResizeObserver` e ciclo di mount/render (`...:97-129`).
- Helper tooltip visuali già presenti (`...:19, 239-270`).
- Wrapper markup `relative` per ospitare badge (`...:287-296`).

### Nuovo minimo indispensabile

- Stato locale `currentResolution` + `logicalRange` + debounce timer + cache keyed by resolution.
- Adattatore daily → weekly/monthly per **N serie stacked dinamiche** via `aggregateLineSeries()` di `[00]`.
- Listener `dataZoom` con debounce 200ms.
- Ricalcolo densità/isteresi via `chooseResolution()` + `chartInstance.getWidth()`.
- Preserve-range con date assolute.
- Tooltip bucket-aware.
- Badge top-left weekly/monthly.
- Ramo update “resolution switch” senza animazione.

## Rischi / note aperte

- `AllocationHistoryChart` usa serie dinamiche per nome categoria: serve attenzione a ricostruire correttamente bucket “sparsi” dove una categoria manca in un giorno ma ricompare dopo; il comportamento atteso resta 0 per categoria assente, come oggi (`frontend/src/lib/components/dashboard/AllocationHistoryChart.svelte:181-184, 229-232`).
- `CHART_ANIMATION_CONFIG` è condiviso: in implementazione va evitato che il cambio di risoluzione erediti animazioni non volute dal config globale (`.../AllocationHistoryChart.svelte:17, 235-236`).
- Il documento non apre alcun branch “media periodo”: decisione chiusa qui per evitare doppia semantica nella stessa feature.

## Nota finale

Nessuna riga di codice scritta in questo task: documento di pianificazione soltanto.
