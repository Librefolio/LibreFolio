# PRIMITIVE.md — cosa esiste già, e come si usa

> **Leggi questa pagina prima di scrivere una riga di superficie.** Non descrive
> cosa *vorremmo* avere: descrive cosa c'è **oggi**, verificato sul codice il
> 2026-09-18 a `2ec19b8f0`. Ogni percorso qui sotto è stato controllato con
> `ls`, non ricordato.
>
> Serve a rispondere a quattro domande e a nessun'altra:
> **cosa esiste già · come si monta una card · come si monta un grafico · cosa NON si costruisce.**
>
> 📌 **Quattro numeri di questa pagina erano sbagliati, e il quarto è il più istruttivo
> perché l'ho scritto io *correggendo* il terzo.**
>
> Il primo: `SingleDatePicker` era dato per 389 righe; ne ha **388**. L'avevo **fatto
> notare a voce** al coordinatore — e poi ho scritto 389 qui, **in due punti**. L'errore è
> entrato nel documento che esiste per impedire agli errori di propagarsi, passando per
> l'unica persona che l'aveva già individuato.
>
> Non cambia nulla — nessuno riscrive un componente per una riga. Cambia che
> **«corretto a voce» e «corretto nell'artefatto» sono due atti diversi, e solo il secondo
> sopravvive alla conversazione.** È esattamente il motivo per cui questa pagina esiste: il
> contratto dentro l'intestazione di `RiskMetricCard` era giusto, e nessuno l'ha letto.
>
> Il secondo e il terzo sono emersi **perché ho riletto ogni cifra dopo il primo**: i
> `toFixed` (§4) e i grafici privi di spec (§3).
>
> **Il quarto è il terzo, sbagliato una seconda volta.** Avevo corretto «sei grafici» in
> «sette» — e **sette era il conteggio di un perimetro che non avevo scritto**
> (`components/charts/`, più la heatmap che sta altrove). Il vero numero, su tutto
> `src/lib`, è **15**. Ho commesso l'errore contro cui avevo appena scritto la regola,
> nel paragrafo in cui la scrivevo.
>
> 🔑 **La regola di questa pagina, pagata quattro volte**: se citi una misura, misurala —
> `wc -l` e `grep -l`, non la memoria — **e scrivi accanto il perimetro.** Un numero senza
> perimetro è un'affermazione **incompleta che ha la forma di una completa**: non si
> riconosce come dubbia, quindi non si ricontrolla. I percorsi qui sotto sono verificati
> con `ls`; ma un percorso che esiste non dice **nulla** sul numero che lo accompagna.

Il *perché* di ogni primitiva resta nell'intestazione del suo file — è là che va
letto quando serve modificarla. Qui c'è solo ciò che serve per **adottarla**,
perché un contratto va dove lo si legge *prima* di aver bisogno del file.

---

## 1. Cosa esiste già

| primitiva | percorso (da `frontend/src/lib/`) | cosa fa |
|---|---|---|
| `RiskMetricCard` | `components/ui/display/RiskMetricCard.svelte` | la card di una metrica |
| `RiskCardGrid` | `components/ui/display/RiskCardGrid.svelte` | **la** disposizione delle card |
| `KpiMetricBar` | `components/ui/display/KpiMetricBar.svelte` | barra 0→100 con riempimento |
| `KpiDivergingFlowBar` | `components/ui/display/KpiDivergingFlowBar.svelte` | barra a due versi attorno allo zero |
| `LineChart` | `components/charts/LineChart.svelte` | **serie temporali, e solo quelle** |
| `ScatterChart` | `components/charts/ScatterChart.svelte` | dispersione rischio/rendimento |
| `CorrelationHeatmap` | `components/risk/CorrelationHeatmap.svelte` | la matrice di correlazione |
| `Tooltip` | `components/ui/feedback/Tooltip.svelte` | **ha già il riposizionamento ai bordi** |
| `SingleDatePicker` | `components/ui/date/SingleDatePicker.svelte` | 388 righe. Non riscriverlo |
| `DocsLink` | `components/ui/DocsLink.svelte` | il link ⓘ alla documentazione |
| `formatPercent` | `utils/core/formatPercent.ts` | percentuali, segno e `-0` già gestiti |
| `formatCurrencyAmountPlain` | `utils/currency/currencyFormat.ts` | importi con simbolo, bandiera, codice |
| `attachChartReady` | `utils/chartReady.ts` | il segnale che l'E2E aspetta |
| `createResizeWatcher` | `utils/core/resizeWatcher.ts` | ridimensionamento del grafico |

### ⚠️ Due righe che circolavano sbagliate

**① `currencyFormat` non è una funzione.** È il *modulo*. Le funzioni sono
`formatCurrencyAmountPlain`, `formatCurrencyAmountHtml`, `formatCurrencyCodeHtml`.
Chi importa `{currencyFormat}` importa un simbolo che non esiste.

**② `LineChart` non ha una prop `seriesType`.** Le sue props sono
`data: LineDataPoint[]` — e `LineDataPoint` è `{date: string; value: number; …}`.
`seriesType?: 'line' | 'area' | 'bar' | 'band'` (**quattro** modi, non tre) vive su
`RenderedSignal`, in `charts/signals/ChartSignal.ts:226`: è il sistema delle
**sovrapposizioni** su una serie temporale, non un selettore di tipo di grafico.

---

## 2. Come si monta una card

```svelte
<script lang="ts">
    import RiskCardGrid from '$lib/components/ui/display/RiskCardGrid.svelte';
    import RiskMetricCard from '$lib/components/ui/display/RiskMetricCard.svelte';
    import {formatPercent} from '$lib/utils/core/formatPercent';
    import {_ as t} from '$lib/i18n';

    let {output, loading = false} = $props();
</script>

<RiskCardGrid testId="l1-metrics">
    <RiskMetricCard
        label={$t('risk.l1.volatility.label')}
        technicalName="σ ann."
        numericValue={output.volatility}
        formatValue={(v) => formatPercent(v, {scale: 100, signed: false})}
        caption={loading ? '' : $t('risk.l1.volatility.caption')}
        sentiment="neutral"
        docsPath="financial-theory/technical-analysis/risk-metrics/volatility/"
        {loading}
        testId="l1-card-volatility"
    />
</RiskCardGrid>
```

### Le props di `RiskMetricCard`

| prop | tipo | nota |
|---|---|---|
| `label` | `string` | **obbligatoria.** La domanda a cui la metrica risponde, in lingua piana |
| `technicalName` | `string?` | il nome tecnico, piccolo, accanto al titolo (`VaR 95%`) |
| `value` | `string?` | valore già formattato. Usato se `numericValue` manca, **e** come larghezza dello scheletro |
| `numericValue` | `number?` | valore grezzo per il numero animato. **Se lo usi, `formatValue` è obbligatoria** |
| `formatValue` | `(v: number) => string` | il formattatore di `numericValue` |
| `caption` | `string?` | seconda riga sotto il valore |
| `sentiment` | `'positive' \| 'negative' \| 'neutral'` | `undefined` = *nessuna opinione*: niente striscia, testo neutro. **È il default giusto**: una metrica di rischio spesso non è né buona né cattiva |
| `docsPath` | `string?` | percorso MkDocs del link ⓘ. Assente → nessun link |
| `loading` | `boolean?` | scheletro al posto del valore |
| `testId` | `string?` | selettore E2E della radice |
| `submetrics` | `Snippet?` | righe secondarie, di norma `KpiMetricBar` |
| `sparkline` | `Snippet?` | **solo dove esiste una serie vera** |

### 🔑 La garanzia anti-salto è per metà tua

La card garantisce che **la riga del valore** non si sposti fra `loading` e valore
caricato: lo scheletro occupa la stessa riga, non un blocco sostitutivo.

**Ma `caption`, `sparkline` e `submetrics` stanno dietro un `{#if}`.** Se li fornisci
*solo* dopo il caricamento, quella metà del contenuto appare dal nulla e la card
cresce — e succede **esattamente nei pannelli più pieni**, dove si nota di più.

> **Regola operativa**: chi fornisce `caption`, `sparkline` o `submetrics` deve
> fornirli **anche durante `loading`** — vuoti o segnaposto, ma presenti.
> Nell'esempio sopra: `caption={loading ? '' : …}`, non `caption={loading ? undefined : …}`.

### La griglia: `RiskCardGrid`, e non una tua

Unica prop: `minWidth` (default `16rem`). Nessun breakpoint, perché la card si
dimensiona da sé con `@container`; la griglia usa
`repeat(auto-fit, minmax(min(minWidth, 100%), 1fr))` e il `gap` è fisso.

**Il `gap` non è esposto di proposito**: un secondo pomello è un secondo asse lungo
cui cinque superfici possono divergere. Se ti serve un `gap` diverso, la domanda
giusta non è «come lo cambio» ma «perché questa superficie è diversa dalle altre
quattro» — e la risposta va discussa, non configurata.

---

## 3. Come si monta un grafico

### Quale grafico per quale forma di dato

| la tua ascissa è… | usa | non usare |
|---|---|---|
| una **data** | `LineChart` | — |
| un **numero continuo** (volatilità, peso) | `ScatterChart` | ❌ `LineChart`: incolla ogni serie a `{type:'category', data: dates}` e **non ha una prop per cambiarlo**. Il risultato non è un grafico rotto, è uno *plausibile* — punti su un asse temporale, giusti d'aspetto e sbagliati |
| una **coppia di categorie** | `CorrelationHeatmap` | — |

### `ScatterChart` — il contratto (fonte: `05-…` §7.5)

```svelte
<ScatterChart
    points={[
        {id: 'pf', name: 'Portafoglio', volatility: 0.18, annualReturn: 0.09, weight: 1, role: 'portfolio'},
        {id: 'bm', name: 'MSCI World', volatility: 0.15, annualReturn: 0.08, role: 'benchmark'},
        {id: 'a1', name: 'VWCE', volatility: 0.16, annualReturn: 0.075, weight: 0.42, role: 'asset'},
    ]}
    labels={{volatility: $t('…'), return: $t('…'), capitalMarketLine: $t('…')}}
    riskFreeRate={0.02}
    testId="l3-risk-return"
/>
```

| prop | tipo | nota |
|---|---|---|
| `points` | `RiskReturnPoint[]` | `volatility` e `annualReturn` sono **frazioni** (0.18 = 18%) |
| `labels` | `{volatility, return, capitalMarketLine}` | **già tradotte.** Il componente non tocca il catalogo i18n |
| `riskFreeRate` | `number?` | frazione. Ancora la Capital Market Line a `x = 0` |
| `height` | `string?` | default `420px` |
| `emptyLabel` | `string?` | mostrato quando nessun punto è disegnabile |
| `testId` | `string?` | anche il namespace del segnale di pronto |

`role` decide la forma: `portfolio` e `asset` sono cerchi dimensionati sul `weight`,
`benchmark` è un rombo di dimensione fissa. **Il raggio va con la radice del peso**,
perché una bolla si legge per *area*: un raggio lineare farebbe sembrare 16× una
posizione 4×.

Punti con coordinate non finite vengono **scartati, non clampati**, e il contenitore
pubblica `data-point-count` e `data-dropped-count`: un punto perso dentro una canvas
è invisibile, e un test che non lo vede non può fallirci sopra.

### Se davvero devi scrivere un grafico nuovo

Il modello approvato è `CorrelationHeatmap.svelte`. Copia il blocco di import
(`:30-41`) e rispetta tre obblighi:

1. **`attachChartReady(chart, container, name)`.** Senza, l'E2E non ha un segnale da
   attendere e torna a dormire un numero fisso di millisecondi: è così che una suite
   diventa lenta e ballerina insieme.
2. **L'aritmetica in un `*Helpers.ts` accanto, con il suo spec.** Non è una mia
   preferenza: **è già la convenzione del repo**, e la prova è nell'unico file che
   sembra un'eccezione (sotto).

   Perimetro: **tutto `src/lib`**, non una cartella.

   | | |
   |---|---:|
   | componenti `.svelte` che chiamano `echarts.init` — **che disegnano** | **15** |
   | di questi, quanti hanno uno spec sul `.svelte` | **0** |
   | file catturati da `grep echarts.init` che hanno uno spec | 1 |

   Quell'uno è `echartsTooltipHelpers.ts`, e **non è un'eccezione: è la conferma.**
   Non disegna — lo nomina in un commento — ed è testato *proprio perché* è aritmetica
   estratta. È esattamente la coppia che devi costruire: `ScatterChart.svelte` (nessuno
   spec) + `scatterChartHelpers.ts` (23 test).

   ⚠️ **Tre trappole di conteggio, tutte già scattate — e la prima è la regola generale,
   non un'eccezione.**

   **① «La cartella dei grafici» è il perimetro sbagliato per la maggioranza dei
   grafici.** Dei 15 che disegnano, `components/charts/` ne contiene **7**; gli altri
   **8** stanno altrove.

   | dove | |
   |---|---:|
   | `components/charts/` | 7 |
   | `components/dashboard/` | 4 |
   | `components/brokers/lots/` | 3 |
   | `components/risk/` | 1 |

   **Chi misura `charts/` per parlare di grafici sbaglia più della metà**, credendo di
   aver scelto il perimetro naturale. Non è una nota a piè di pagina: è il motivo per
   cui qui ogni cifra ha il perimetro scritto accanto.

   **② Non contare i file della cartella.** In `components/charts/` ce ne sono **20**, e
   due (`ChartSignalsSection`, `MeasurePanel`) **hanno** uno spec — non disegnano.

   **③ Non contare le occorrenze del `grep`.** Sono **19 su 17 file**, ma due file
   nominano `echarts.init` **solo in un commento**. E restringere il pattern a
   `echarts\.init(` **non li esclude**, perché un commento che cita una chiamata
   contiene la chiamata:

   ```
   echartsTooltipHelpers.ts:251    * `echarts.init()`. It deliberately avoids…
   echartsDataZoomTouchPan.ts:31   *   element passed to `echarts.init()`).
   ```

   **Il discrimine non è la cartella né il grep: è se il componente disegna.** Dove c'è
   logica si testa, dove c'è una canvas si testa l'opzione che la riempie.

   **Il discrimine non è la cartella né il grep: è se il componente disegna.** Dove c'è
   logica si testa, dove c'è una canvas si testa l'opzione che la riempie.

   Registra lo spec in `scripts/test_runner/_frontend_utility.py` → `front_utility_unit`
   — **il catalogo è un elenco di file, non un glob**: uno spec non registrato non
   viene eseguito, e il conteggio invariato somiglia a «nessuna regressione».
3. **`createResizeWatcher` + `MutationObserver` sul dark**, come fa l'heatmap.

---

## 4. Cosa NON si costruisce

| non costruire | usa | perché |
|---|---|---|
| un date picker | `SingleDatePicker` | 388 righe già scritte e collaudate |
| un popover / tooltip | `Tooltip` | **il riposizionamento ai bordi c'è già** |
| una griglia di card | `RiskCardGrid` | è la deriva che questo documento esiste per fermare |
| un `toFixed` nuovo | `formatPercent` | ⚠️ vedi sotto |
| una formattazione di importo a mano | `formatCurrencyAmountPlain` | ⚠️ vedi sotto |
| un grafico a serie temporali | `LineChart` | — |

### ⚠️ Due debiti che **non sono tuoi da pagare**

Segnalati qui perché tu non li **peggiori**, non perché tu li ripari:

- **`toFixed`**: appartengono a **T4**, e tu non ne aggiungi di nuovi — usa
  `formatPercent`. Non «sistemare» gli altri: invaderesti un mandato trasversale
  credendo di obbedire.
  ⚠️ **Sul quanti siano, non fidarti di nessun numero senza il suo perimetro.** Misurati
  qui: **26** in `components/risk/`, **164** in tutto `src/lib` + `src/routes`. Il
  briefing di T4 ne dichiara **16**, che non è nessuno dei due: conta un perimetro più
  stretto che non ho visto. **Non li riconcilio** — chi deve agire su quel debito parte
  dal perimetro di T4, non da questa riga.
- **il locale degli importi**: `formatCurrencyAmountPlain` chiama
  `toLocaleString(undefined, …)`, cioè il locale del **browser**, non quello scelto
  nell'app. È un `TODO_FUTURI` noto. Usala lo stesso: una seconda formattazione
  parallela raddoppierebbe il problema invece di risolverlo.

### ⚠️ `docsPath`: i link sono sbagliati in **due** modi

Nel round 1 sei `DocsLink` puntavano a `user/analysis/`, **che non esiste**. Ma la
correzione ovvia è sbagliata a sua volta:

- `mkdocs.yml` non imposta `use_directory_urls`, quindi vale il default `true`:
  la forma giusta **non** è `pagina.md#ancora` ma `pagina/#ancora`;
- le pagine vere sono **una per metrica**, sotto
  `financial-theory/technical-analysis/risk-metrics/` (`volatility`, `correlation`,
  `conditional-value-at-risk`, `current-drawdown`, … 22 in tutto), non una pagina unica.

Il contrasto, preso dal codice di oggi:

```diff
- path="user/analysis/risk.md#beta"                     ← rotto due volte
+ path="financial-theory/technical-analysis/risk-metrics/beta-active-return/"
```

```
✅ "user/dashboard/kpi-cards/#card-1-period-pl"          ← funziona: cartella + ancora
✅ "financial-theory/technical-analysis/performance-metrics/weighted-average-cost/"
```

**Verifica che il file esista prima di scrivere il percorso.** Il cancello
`dev.py mkdocs check-links` **non ti copre**: legge i `path="…"` con le virgolette e
salta per costruzione i `path={espressione}`, quindi un `DOC_PATHS[row.id]` passa
inosservato anche quando i valori della mappa sono stringhe statiche. La proprietà
del cancello cieco è di **T2**.

### ⚠️ Un rosso che sembra tuo e non lo è

Se `front check` ti segnala che **un campo dell'API «non esiste»** su un tipo `F…Response`,
prima di cercare il difetto nel tuo codice controlla l'**età del client generato**:

```bash
grep -c il_tuo_campo frontend/src/lib/api/generated.ts   # 0 = client vecchio, non campo assente
```

`frontend/src/lib/api/generated.ts` è **in `.gitignore`** (`frontend/.gitignore:13`): non
viaggia col merge, quindi **un fast-forward pulito non lo aggiorna** e `git status` non può
dirtelo. Ed è ignorato anche `openapi.json`, da cui il client si genera: **è stantia tutta
la catena**, non solo l'ultimo anello. Si rigenera con:

```bash
PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py api sync
```

Non binda porte — esporta lo schema in-process e genera il client offline — quindi **non
tocca la tua corsia** e puoi lanciarlo quando vuoi. Ma va invocato **così**: un `./dev.py`
nudo da un worktree può crearsi un venv vuoto suo invece di usare quello condiviso.

> Costo reale, pagato in questo round: una catena diagnostica di sei anelli, tutti veri
> tranne il primo, che concludeva in una perdita di dati inesistente. **`git status` prova
> l'assenza di modifiche tracciate, non l'assenza di differenze.**

---

## 5. Come si misura se questa pagina ha funzionato

Non dal fatto che sia stata scritta, ma da tre cose che succedono altrove:

- **S1 adotta `RiskMetricCard` senza fare domande.** Se deve chiedere, il documento
  non era abbastanza.
- **S3 monta lo scatter senza costruire un grafico nuovo.**
- **Nessuna superficie introduce un `toFixed`, un date picker o un popover nuovi.**

Se una di queste tre fallisce, il difetto è in questa pagina — non in chi l'ha letta.
