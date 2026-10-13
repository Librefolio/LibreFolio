# Piano — fase 00, 52: l'ultima etichetta degli assi del tempo sui telefoni, più le date dei tooltip

> **Stato**: ✅ **Checkpoint pronto** (2026-10-13), poi FROZEN. Il coordinatore ha approvato **a3** al posto di (a) (§0) e mi ha portato in fast-forward al treno 93. Gli stadi: a3 con Lots (C1), 3a (C2), 3b con la settimana di Alloc (C3), il periodo in corso di Growth (C3b, §2.3), il commento (C4), la doc (C5) e questo piano (C6); il manifest è al passo 11.
>
> - **Mandato**: coordinatore di Release 2 (`c8328a01-…`), lotto 52. **Origine**: il fratello di R-2 sugli assi del tempo (piano 51 §1), più le date dei tooltip trovate da T (3a, 3b).
> - **Workstream I**. Ramo `e-alfy-performance-charts-plan`. Base `fa6299689` (treno 91), poi **`ef666fdee`** (treno 93, con `bucketSpanUpTo` di T); worktree pulito tranne questa cartella, porta 6157 libera.
> - **Corsia**: `--test-port 6157 --data-dir /tmp/librefolio-r2-i-charts`, con `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test …`; un comando alla volta, **1 worker**. Mai le porte 6040 e 6041, mai `--force`, mai la galleria, mai `mkdocs serve`.
> - **Tocca** (previsto): `frontend/src/lib/components/charts/responsiveXAxis.ts`, `GrowthChart.svelte`, `AllocationHistoryChart.svelte`, `LotComparisonChart.svelte`, i loro test (`chartCoreHelpers.test.ts`, `GrowthChart.test.ts`, `AllocationHistoryChart.test.ts`, un test della comparazione dei lotti), il commento di `frontend/e2e/layout/toolbar-width-sweep.spec.ts`, la pagina `mkdocs_src/docs/developer/frontend/components/charts.md` (via docs-writer).
> - **Non tocca**: `priceChartHelpers.ts` (è di T: `bucketSpanUpTo` lo uso e basta), la devWiki (ha un solo scrittore, W: le proposte vanno al coordinatore), il CHANGELOG (è del coordinatore).
> - **La cartella** `52_timeAxisLastLabel` è una mia proposta: il coordinatore ha dato il numero del lotto, non il nome.

## 0. Autorizzazione (2026-10-13)

Il coordinatore: «**Lotto 52, nella 1.2**: il difetto è nato nella 1.2, quindi va curato prima della galleria.

1. **L'ultima etichetta tagliata sugli assi del tempo** (Growth, AllocationHistory, LotComparison sui telefoni): la tua opzione (a), `outerBoundsMode: 'same'` più `outerBoundsContain: 'axisLabel'`.
   - Sulle prime etichette nascoste (da 34 a 64) guarda a occhio a 320, 360, 390 e 440 px se la lettura dell'asse resta buona. Se peggiora davvero, fermati e dimmelo con gli screenshot.
   - Test sui consumatori e un controllo visivo, con gli screenshot nel rapporto.
2. **Il commento del test della pillola** (`toolbar-width-sweep.spec.ts`, ~`:1089`): sostituiscilo col testo che hai proposto, ora che sei dopo V-27.

**Wiki**: le tue tre proposte (la regola di ECharts, la pagina problema di R-5, la voce del log) le giro a W, che le scrive. La devWiki ha un solo scrittore: la tua modifica a `responsive-4mode-layout` è entrata, ma la prossima passala a W.

Per le prove, spec singole a 1 worker. Checkpoint FROZEN col manifest.»

**Aggiunta del coordinatore, lo stesso giorno (in sintesi)**: T ha trovato due difetti negli stessi tre file, quindi uno scrittore solo, io.

- **3a.** I tooltip di Growth e Alloc stampano le date ISO grezze («2026-10-12»). La cura usa `formatDay` di T. `GrowthChart.test.ts:2171-2189` deve andare rosso prima.
- **3b.** Nel periodo aperto della comparazione dei lotti, «valore al» e la fine della settimana usano `bucketEnd`, un giorno che deve ancora venire, invece della data del punto. La cura usa `bucketSpanUpTo` di T (`priceChartHelpers.ts`), che arriva col treno 93: il coordinatore mi porta in fast-forward quando gli dico che sono fermo fra due comandi.
- **3c.** Per ogni difetto, dire se c'era già nella `v1.1.0`.

**La decisione del coordinatore, dopo lo STOP su (a) (2026-10-13, in sintesi)**:

- **Fast-forward fatto**: HEAD `ef666fdee` (treno 93: `bucketSpanUpTo` di T in `priceChartHelpers.ts`, più una riga del CHANGELOG). Il piano 52 è intatto.
- **a3 approvata al posto di (a).** La misura prima del render (`getTextRect`) deve restare conservativa. Dopo la cura rifaccio la stessa sonda (attesi 0 tagli) e metto nel rapporto **i montaggi en ed es a 320 e 360 px**.
- **LotComparison passa per l'helper**: una regola sola.
- **CHANGELOG** (è del coordinatore):
  - 3a è coperta dalla riga 🔄 che c'è già («Numbers and dates follow the interface language everywhere … chart axes and tooltips»), quindi niente riga nuova;
  - 3b: il coordinatore allarga la riga 🐛 dei periodi aperti a «asset, FX and lot charts».
- **Il commento della pillola**: adesso, dopo il fast-forward.
- **L'ordine**: a3 con Lots, poi 3a, poi 3b, poi il commento. I rossi prima delle cure, via test-author; spec singole a 1 worker; checkpoint FROZEN col manifest.

## 1. Analisi

### 1.1 La causa (assi del tempo)

- In compatto `buildResponsiveXAxisPolicy` (`responsiveXAxis.ts:142-175`) forza `showMinLabel`/`showMaxLabel` con `hideOverlap`. L'etichetta dell'ultimo punto è centrata sul suo tick, quindi metà della sua larghezza sta oltre il bordo del grafico.
- `containLabel: true` è il percorso legacy di ECharts: riserva solo lo spazio perpendicolare delle etichette, mai la metà destra dell'ultima etichetta x, e ignora le chiavi `outerBounds*`.
- Sugli assi a categoria il fratello è curato (R-2, lotto 51) con `alignMaxLabel: 'right'`. Sugli assi del tempo la stessa chiave nascondeva l'ultima etichetta 181 volte (piano 51 §1): scartata.
- Le griglie: Growth `GrowthChart.svelte:2190` (`right: '4%'`), Alloc `AllocationHistoryChart.svelte:706` (`right: '4%'`), Lots `LotComparisonChart.svelte:1111-1117` (`right: 18`), tutte con `containLabel: true`.
- **Provenienza**: nato nella 1.2 (lo dice il mandato). Niente riga nel CHANGELOG.

### 1.2 La sonda a runtime

- **Dove**: fuori dal repo, `/tmp/libreFolio_i_l52_rt/rt-l52.spec.ts` (Playwright, 1 worker), contro il server della corsia 6157 sulla base `fa6299689`.
- **La matrice**: 560 casi per variante. Growth (Abs, %, P&L) e Alloc × 4 lingue × 6 periodi (7, 14, 30, 45, 90, 365 giorni) × 5 larghezze (320, 360, 390, 440, 1280 px), più Lots (gli asset 1 e 6, nei modi valore e rendimento; il 17 non ha il grafico) × 4 lingue × 5 larghezze.
- **La misura**: la scena di zrender. Prendo l'istanza dal suo `_dom`, applico `setOption({animation: false, grid: patch})`, leggo i rettangoli delle etichette (`label_<tick>`, `ignore` per quelle nascoste da `hideOverlap`) e ripristino. Un'etichetta è **tagliata** se il suo rettangolo esce dal canvas.
- **Le varianti**:
  - `as-is`, la build;
  - **(a)**: `containLabel: false`, `outerBoundsMode: 'same'`, `outerBoundsContain: 'axisLabel'`;
  - `a0`: `'auto'`, con `outerBounds` uguali agli inset di oggi e `top: 0`;
  - `a4`: `'auto'`, con `right: 2` e `top: 0`;
  - **a3** (mia, §1.4): `containLabel: true` resta, e `right = max(right di oggi in px, ceil(larghezza dell'etichetta x più larga / 2) + 2)`, in due passate nella pagina.
- **I file**: `/tmp/libreFolio_i_l52_probe/base_rows.json`, `base_analysis.log` (as-is, a, a0, a4) e `a3_rows.json`, `a3_analysis.log`; gli scatti in `/tmp/libreFolio_i_l52_shots/` (`base__*.png` 264, `a3__*.png` 116); i montaggi in `/tmp/libreFolio_i_l52_probe/montage_*.png`.

### 1.3 L'esito di (a): la lettura peggiora davvero

**I numeri** (tagli dell'ultima etichetta; «nuovi» = casi puliti nella build e tagliati con la variante):

| Gruppo | Casi | Tagli as-is | Tagli (a) | **Nuovi con (a)** | Prima etichetta persa con (a) |
|---|---:|---:|---:|---:|---:|
| Growth, telefoni | 288 | 230 | 39 | **30** | 61 |
| Growth, desktop | 72 | 12 | 0 | 0 | 21 |
| Alloc, telefoni | 96 | 72 | 13 | **10** | 22 |
| Alloc, desktop | 24 | 20 | 4 | **2** | 8 |
| Lots, telefoni | 64 | 0 | 0 | 0 | 20 |
| Lots, desktop | 16 | 0 | 0 | 0 | 0 |

- **42 tagli nuovi** (30 + 10 + 2), per esempio Alloc en a 1280 px, periodo di 30 giorni, che oggi è pulito. `a0` e `a4` hanno gli stessi 42.
- **Prime etichette perse**: 103 sui telefoni (61 + 22 + 20), contro le 34–64 previste.
- **Il costo in spazio**: (a) toglie 7,1 px di altezza al grafico (riserva metà dell'etichetta y in alto), sposta le etichette y di 3 px e stringe il grafico di circa 24 px sui telefoni.
- **A occhio** (`montage_growth_en_s30.png`, Growth en, 30 giorni):
  - a 360 e 390 px (a) taglia «Oct 13» in «Oct 1». A 390 l'asse si legge «Oct 1 | Oct 1»: un doppione visivo, proprio quello che il lotto 47 ha tolto;
  - (a) perde anche «Sep 13», la prima etichetta, che la build mostra intera.
- **Il motivo**: il percorso `outerBounds` stima lo spazio delle etichette una volta sola, prima di sapere quali tick sopravvivono a `hideOverlap`. Su un grafico più stretto i tick cambiano e la stima non torna più.

> **⚠️ Fuori pista (2026-10-13)**: STOP su (a), come chiede il mandato («Se peggiora davvero, fermati e dimmelo con gli screenshot»). Nessuna riga di prodotto toccata. La decisione passa al coordinatore (§2).

### 1.4 L'alternativa a3: zero tagli

| Gruppo | Tagli as-is | Tagli a3 | Nuovi | Prima etichetta persa | Larghezza del grafico |
|---|---:|---:|---:|---:|---:|
| Growth, telefoni | 230 | **0** | 0 | 11 | −13,1 px |
| Growth, desktop | 12 | **0** | 0 | 0 | −4,0 px |
| Alloc, telefoni | 72 | **0** | 0 | 3 | −13,0 px |
| Alloc, desktop | 20 | **0** | 0 | 1 | −11,8 px |
| Lots, telefoni | 0 | 0 | 0 | 1 | −4,0 px |
| Lots, desktop | 0 | 0 | 0 | 0 | −4,0 px |

- **Zero tagli in tutti i 560 casi**, zero nuovi.
- Niente altezza persa, le etichette y restano dove sono.
- L'ultima etichetta che `hideOverlap` nasconde resta quella della build (103 su 288 per Growth sui telefoni, in entrambe).
- **L'inset destro cresce**: di 5–25 px per Growth e Alloc (mediana 10–15 px), di 1–6 px per Lots. L'etichetta più larga misura 64,6 px.
- **A occhio** (`montage_a3_growth_en_s30.png`, `montage_a3_mixed.png`): a 320 px «Sep 13 | Sep 22 | Oct 1 | Oct 13», con «Oct 13» intera (l'inset passa da 10,2 a circa 23 px); le altre larghezze uguali alla build; en e it ok.

**Il disegno di produzione proposto** (da confermare, §2):

- Un helper condiviso in `responsiveXAxis.ts` calcola, **prima del render**, metà della larghezza dell'etichetta più larga che il formatter può mettere sul bordo destro. I candidati sono:
  - il formato dei capi (`dayMonth`, o `dayMonthYear` se il periodo attraversa un anno) sull'ultimo punto;
  - giorno e mese, mese o anno sulle date vicine alla fine, per lo zoom.
- **La misura**: `echarts.format.getTextRect(testo, font)`, col font delle etichette dell'asse. Il precedente è `ladderLabelMeasure` (`GrowthChart.svelte:1249-1258`).
- **I consumatori**: `grid.right = max(right di oggi in px, sporgenza)`, e `containLabel: true` resta. È il percorso deterministico, senza la stima di `outerBounds`.
- **Il percorso della scala** (asse a categoria di Growth) tiene la sua gestione.
- **Il limite**: la sonda misura l'etichetta più larga fra quelle della scena; la produzione misura candidati prima del render. Quindi la produzione è conservativa: lo stesso o qualche px in più. La sonda rifatta dopo la cura (stessa matrice, `as-is`) deve dare 0 tagli.

### 1.5 Le date dei tooltip (3a, 3b) e la loro provenienza (3c)

**3a: Growth e Alloc stampano le date ISO grezze.**

- **Growth**, `buildTooltipBucketHeader` (`GrowthChart.svelte:1380-1408`), date grezze in quattro punti:
  - `:1386`: l'intestazione del giorno singolo (`bucket.bucketEnd`);
  - `:1393`: la scala, `${span.start} → ${span.end}`;
  - `:1398` e `:1401`: «valore al» (`bucket.bucketEnd`);
  - `:1404`: «settimana dal … al …».
- **Alloc**, `buildAllocationTooltipHeader` (`AllocationHistoryChart.svelte:557-567`): `:559` («settimana» e «valore al»), `:563` («valore al»), `:566` (l'intestazione giornaliera, `row.date`).
- **La cura**: `formatDay` (`frontend/src/lib/utils/core/formatAxisDate.ts:77`), che è già nella base.
- **Provenienza (3c)**: **dalla v1.0.0** (`222a77c5e`, la risoluzione dinamica). In `v1.1.0` le intestazioni settimanale, mensile e giornaliera di entrambi i grafici stampano già l'ISO. Fa eccezione la sola intestazione della scala di Growth («1W - inizio → fine», `e7773a143`/`8c7b0c0a7`), nata nella 1.2: la scala non c'è nella `v1.1.0`.

**3b: la comparazione dei lotti, nel periodo aperto, nomina un giorno che deve ancora venire.**

- `buildTooltipBucketHeader` (`LotComparisonChart.svelte:403-415`) formatta già le date (`formatLongDate`), ma «valore al» e la fine della settimana leggono `bucket.bucketEnd`, che `pointBucketMeta` (`:298-306`) prende dalla fine del periodo, non dall'ultimo giorno con dati.
- **La cura**: `bucketSpanUpTo` di T, dopo il fast-forward al treno 93.
- **Provenienza (3c)**: **dalla v1.0.0**. In `v1.1.0` (`:421-425`) e in `v1.0.0` (`:652`) «valore al» usa già `formatLongDate(bucket.bucketEnd)`.

**Il CHANGELOG** (del coordinatore): 3a e 3b ci sono dalla v1.0.0, quindi valgono una riga 🐛. Il coordinatore pensava già di unire 3b alla riga 🐛 dei periodi aperti; 3a contraddice la riga 🔄 «Numbers and dates follow the interface language everywhere». **Deciso** (§0): 3a resta nella riga 🔄, 3b entra nella riga 🐛 allargata.

### 1.7 Il periodo in corso di Growth (reperto nuovo, 2026-10-13)

Studiando 3a e 3b sulla base `ef666fdee`, ho trovato due difetti vicini, fuori dal mandato ma sulle stesse righe.

- **Growth, modi Abs, % e P&L a linee** (non la scala), a risoluzione settimanale o mensile:
  - `buildBucketInfos` (`GrowthChart.svelte:809-836`) mette ogni secchio sulla **fine del periodo** (`date: bucketEnd`);
  - `aggregateMetric` (`:934-970`) cerca il valore con quella data fra i punti di `aggregateLineSeries`, che stanno sull'**ultimo giorno con dati**;
  - per un periodo intero le due date coincidono, perché la storia riempie ogni giorno del calendario; per **il periodo in corso** no, quindi il suo valore è `null`.
  - **L'effetto**: la linea si ferma all'ultimo periodo intero, e l'asse finisce su un giorno che deve ancora venire. Il tooltip su quel punto dice «settimana dal 12 al 18 ott, valore al 18 ott», senza valori.
  - **La prova**: la replica `/tmp/libreFolio_i_l52_scratch/check_open.mjs` (con oggi = 13/10/2026) dà settimanale `2026-10-18 => null` e mensile `2026-10-31 => null`. Gli scatti `a3__growth_eur_en_w390_s365_{as-is,a3}.png` (badge «Weekly») mostrano l'ultima etichetta «Oct 18,» tagliata nella build e **«Oct 18, 26» intera con a3**.
  - **Quindi a3 rende leggibile un giorno futuro** sul bordo destro dei telefoni a 1Y.
  - **Provenienza**: dalla `v1.0.0` (`date: bucketEnd` e `lookup.get(bucket.date)`, identici in `v1.0.0` e `v1.1.0`).
- **Alloc, settimanale**: il punto sta sul suo ultimo giorno e «valore al» è giusto, ma «settimana dal … al …» finisce sulla domenica che deve venire (`row.bucketEnd`, `:559`). È il difetto che T ha curato nei grafici dei prezzi. Anche questo c'è dalla `v1.0.0`.

> **⚠️ Fuori pista (2026-10-13)**: reperto fuori mandato, mandato al coordinatore come decisione (§2.3). Intanto vado avanti con a3, che non dipende dalla risposta: l'helper legge gli estremi dai dati.

### 1.6 Il commento della pillola

`toolbar-width-sweep.spec.ts` ~`:1089`, testo approvato:

- prima: `// As in the sweep: login() returns before the post-login routing that brings the language selector.`
- dopo: `// As in the sweep: login() returns once the app has arrived (V-27); the two waits below re-check that landing, then the selector.`

Le due attese restano. Lo faccio dopo il fast-forward, perché il treno 93 potrebbe toccare lo stesso file.

## 2. Decisioni (al coordinatore)

1. ✅ **(a) o a3?** Deciso: **a3** (§0).
2. ✅ **Lots per l'helper**: deciso, una regola sola (§0).
3. ✅ **Il periodo in corso** (§1.7), deciso dal coordinatore il 2026-10-13:
   - **Alloc**: sì, `bucketSpanUpTo(row.date, row)` sulla riga di 3a, dentro C2/C3.
   - **Growth: (A), nella 1.2**, in uno stadio a parte dopo 3b (**C3b**). Il periodo in corso sta sul suo ultimo giorno con dati, come in Alloc, nei lotti e nei prezzi, e l'intestazione usa `bucketSpanUpTo`.
     - **Test**: i rossi prima della cura via test-author, compresi lo zoom e la cascata, che leggono le date dei secchi; più `growth-chart-memo` e gli E2E della Dashboard che toccano il grafico.
     - **Fermarsi e dirlo** se la cura esce da `GrowthChart.svelte` e dai suoi helper (backend, API, altri consumatori), o se va oltre la mezza giornata.
   - **Il CHANGELOG**: la riga 🐛 del periodo aperto la allarga il coordinatore a fine lotto (prezzi, Growth, Alloc, lotti). Nel checkpoint dico per ognuno da quale versione c'era il difetto.
   - **La consegna** può essere a stadi: a3 e 3a/3b prima, Growth dopo.

## 3. Passi

1. ✅ 2026-10-13: analisi del motore di ECharts e sonda a runtime (§1.1–1.4).
   > **Note implementazione**: matrice di 560 casi per variante sulla base `fa6299689`, server della corsia 6157. Montaggi e log in `/tmp/libreFolio_i_l52_probe/`.
2. ✅ 2026-10-13: provenienza di 3a e 3b sui tag `v1.1.0` e `v1.0.0` (§1.5).
3. ✅ 2026-10-13: la decisione del coordinatore (a3, Lots per l'helper, l'ordine, il CHANGELOG) e il fast-forward a `ef666fdee` (§0).
   > **Note implementazione**: il delta dei treni 92–93 non tocca Growth, Alloc, LotComparison, `responsiveXAxis.ts` né `toolbar-width-sweep.spec.ts`. T ha toccato `priceChartHelpers.ts`, `PriceChartFull`, `CandlestickChart` e la pagina della coppia FX; V alcuni E2E; W la wiki.
4. ✅ 2026-10-13: **C1, a3 con Lots**: l'helper in `responsiveXAxis.ts` e i tre consumatori. I rossi via test-author (l'helper con una misura finta, i consumatori), poi la cura, i verdi e l'istantanea.
   > **Disegno rifinito (2026-10-13, lettura del codice sulla base `ef666fdee`)**:
   > - **La causa precisa**: `containLabel` riserva solo l'**altezza** delle etichette x (`estimateLabelUnionRect`), mai la metà dell'ultima etichetta centrata che sporge oltre il bordo destro. L'estensione dell'asse del tempo è min/max dei dati, senza arrotondamenti; con lo zoom **qualunque giorno** del periodo può finire sul bordo.
   > - **`responsiveXAxis.ts`, disegno (c)**: `buildResponsiveXAxisPolicy` e `ResponsiveXAxisPolicy` restano **identici** (il pin letterale del ramo del tempo di `updateChartData` non tollera una chiave in più). Un helper a parte, `timeAxisGridRight({width, values, locale, base, measure})`: `inset = ⌈più larga/2⌉ + 2` (0 senza candidati); `base` in px (numero, o stringa con `%` della larghezza); restituisce `inset > base in px ? inset : base`. La stringa `'4%'` resta sul desktop, così ECharts segue la larghezza da solo; in jsdom (larghezza 0) esce l'inset in px.
   > - **I candidati non dipendono dal modo** (compatto o no): i capi (`dayMonth`, o `dayMonthYear` se il periodo attraversa un anno), e ogni giorno da primo−1 a ultimo+1 nei formati che il formatter gli può dare (giorno e mese; il 1° anche il mese; il 1° gennaio l'anno). Oltre i 366 giorni basta un anno bisestile sintetico. Cache dei candidati per `lingua|primo|ultimo`; la funzione non è esportata, i test la osservano con una misura finta che registra.
   > - **La misura**: `axisLabelMeasure(chart, fontSize)` con `echarts.format.getTextRect` letto solo dentro la chiamata, il font letto dal modello come `ladderLabelMeasure` e, prima del primo `setOption`, la regola di default di ECharts 6 (`sans-serif`, `Microsoft YaHei` su Windows). **Nessuna cache propria delle larghezze**: zrender ne tiene già una (`ensureFontMeasureInfo`, LRU di 100 font × 500 testi).
   > - **Growth** (14 px): una variabile `appliedGridRight` (iniziale `'4%'`). La griglia piena prende `timeAxisGridRight(...)` quando c'è la politica del tempo, `'4%'` sulla scala; il ramo del tempo di `updateChartData` manda `grid: {right}` nello stesso `setOption`, prima di `xAxis`; il resize, dentro il blocco `!ladderActive` esistente, scrive `grid.right` solo quando il valore cambia, **non pigro**, e subito dopo `syncPlotGeometry()`, che legge il rettangolo della griglia.
   > - **Alloc** (14 px): la griglia piena come Growth; il resize scrive solo quando cambia, **pigro** (nessuna geometria da rileggere).
   > - **Lots** (12 px, base `18` in px): solo la griglia del builder; il valore non dipende dalla larghezza, quindi **nessuna patch al resize**, e i pin del resize dei lotti restano intatti. `buildLotXAxisPolicy` non cambia.
   > - **I pin**: si ri-pinna solo l'import di `chartCoreHelpers.test.ts:2221` (ora importa anche l'helper); i due mock senza `format` che arrivano a `echarts.init` (`GrowthChart.tooltip.test.ts`, `AllocationHistoryChart.test.ts`) ricevono `format.getTextRect`.
   > - **I rossi su uno stub inerte**: prima del test-author metto in `responsiveXAxis.ts` le tre funzioni con le firme vere e i corpi inerti (`base`, `''`, `() => 0`), come nel precedente S7. Così i rossi sono asserzioni che falliscono, non `TypeError` d'import.
   > **⚠️ Fuori pista (2026-10-13)**:
   > - **`AllocationPanel.test.ts` non serve.** Passa sempre `allocationHistory: null`, e il grafico storico esce prima di `echarts.init`. I mock da toccare sono due, non tre.
   > - **La precondizione SSR del caso dello screenshot cade in node.** Jul 16→Oct 13 a 360 px non taglia nel rendering lato server: l'ultima etichetta disegnata è «Oct 1». Lo sostituiscono i casi che tagliano davvero col `'4%'`, verificati in `/tmp/libreFolio_i_l52_scratch/ssr_scan_en14.log` e `ssr_scan_lots_en.log`:
   >   - a 14 px, Jul 16→Oct 20 a 360 px;
   >   - a 14 px, Dec 20 2025→Jan 10 2026, a tutte e quattro le larghezze;
   >   - a 14 px, gli zoom Aug 3→Sep 28 e Jul 25→Aug 28, a tutte e quattro le larghezze;
   >   - per i lotti, a 12 px con base 18, Dec 20 2025→Jan 10 2026, a tutte e quattro le larghezze (inset 32).
   >
   >   Dopo la cura, in ogni caso `after_cut` è vuoto e `miss=[]`.
   >
   > **I rossi (2026-10-13)**: il test-author ha scritto +588/−5 righe in quattro file di test, senza toccare il codice di prodotto. Il brief è in `files/l52_briefs/01-c1-reds.md` (stato di sessione); i log sono in `/tmp/libreFolio_i_l52_ta/`.
   > - **I file e i casi**:
   >   - `chartCoreHelpers.test.ts`: l'helper (A1–A10), il font (B1–B4), la parte C (20 precondizioni SSR più 20 casi della cura), il ri-pin dell'import (E1) e i pin dei consumatori (E2×6, E3–E6).
   >   - `GrowthChart.test.ts`: D1 e D2.
   >   - `AllocationHistoryChart.test.ts`: D3. Il mock ora ha `format.getTextRect` e i font misurati.
   >   - `GrowthChart.tooltip.test.ts`: solo il mock, che riceve `format.getTextRect`.
   > - **Il test-author, da solo**:
   >   - prima delle aggiunte (r1), tutto verde: 183, 141, 21 e 6;
   >   - dopo (r2): `chartCoreHelpers` 49 rossi su 257, Growth 1 su 143, Alloc 1 su 22, il tooltip 6 su 6 verdi;
   >   - prettier `--check` e `npm run check` puliti, con 0 errori e 0 avvisi.
   > - **La conferma nella corsia 6157**, a 1 worker, un selettore alla volta:
   >   - `front-asset asset-unit`: 49 rossi e 792 verdi, con 1 file rosso su 20. Ogni riga FAIL contiene «plan 52».
   >   - `front-asset growth-chart-memo`: 1 rosso (D1) e 142 verdi.
   >   - `front-portfolio allocation-unit`: 1 rosso (D3) e 239 verdi, con 1 file rosso su 6.
   >   - `front-utility component-unit`: 3142 verdi su 117 file, come atteso.
   >
   >   I log sono `/tmp/libreFolio_i_l52_red_{asset-unit,growth-chart-memo,allocation-unit,component-unit}.log`.
   > - **Verdi sullo stub, come previsto**: A1, A3 (30), A4, le precondizioni della parte C, D2, D4, E1 ed E5.
   > - **Le note del test-author**:
   >   - il caso pluriennale di A10 è dato dai capi, non dai giorni intermedi;
   >   - D1 e D3 sono rossi solo sul controllo `typeof`: il valore che ricevono dopo la cura è quello dell'helper.
   > - **La mia revisione**: ho riletto i due diff a mano (`review_cch.diff` e `review_dash.diff`). Gli oracoli sono indipendenti dal codice e i pin sono quelli giusti.
   >
   > **Note implementazione (2026-10-13)**:
   > - **`responsiveXAxis.ts`** (+120): i corpi veri al posto dello stub.
   >   - `timeAxisGridRight`: i capi passano da `parseDisplayDate`, e uno nullo restituisce `base` senza misurare; se sono invertiti li scambia; misura ogni candidato una volta sola.
   >   - `timeAxisLabelCandidates`: cache FIFO di 16 voci.
   >   - `insetPx`: un numero resta com'è, una stringa `N%` vale N% della larghezza, altrimenti `parseFloat`.
   >   - `axisLabelFont`: la famiglia del modello, altrimenti il default di ECharts 6.
   >   - `axisLabelMeasure`: risolve il font alla prima misura e legge `echarts.format` solo dentro la chiamata.
   > - **`GrowthChart.svelte`** (+40/−3):
   >   - una variabile `appliedGridRight`;
   >   - `applyFullOption`: l'helper sulla politica del tempo, `'4%'` sulla scala;
   >   - `updateChartData`: nel ramo del tempo `grid: {right}` va nello stesso `setOption` di `xAxis`;
   >   - il resize, dentro `!ladderActive`, scrive solo quando il valore cambia, non pigro, poi `syncPlotGeometry()`.
   >
   >   Ho verificato che il ramo della scala in `updateChartData` non eredita mai un inset del tempo: `ladderActive` deriva dal modo (`:471`), e un cambio di modo passa sempre da `applyFullOption` (`needsFullInit`).
   > - **`AllocationHistoryChart.svelte`** (+24/−1): la griglia di `buildChartOption` prende l'helper su `dataset.dates`; il resize scrive solo quando cambia, pigro, sullo stesso `getResolutionDataset(currentResolution)`.
   > - **`LotComparisonChart.svelte`** (+11/−3): solo `grid.right` del builder, base `18`, 12 px, sui capi di `axisDateRange`. Il resize resta com'era.
   >   - **Effetto collaterale**: il margine destro dei lotti passa da 18 a circa 24 px a ogni larghezza (la più larga, 42,7 px nel browser), perché la base è in px e non cresce col desktop.
   > - **Verdi nella corsia 6157**, a 1 worker, un selettore alla volta:
   >   - `front-asset asset-unit`: 841 su 841, 20 file (prima 49 rossi);
   >   - `front-asset growth-chart-memo`: 143 su 143 (prima 1 rosso);
   >   - `front-portfolio allocation-unit`: 240 su 240, 6 file (prima 1 rosso);
   >   - `front-utility component-unit`: 3142 su 3142, 117 file.
   >
   >   I log sono `/tmp/libreFolio_i_l52_green_{asset-unit,growth-chart-memo,allocation-unit,component-unit}.log`.
   > - **Le prove statiche**: `dev.py front check` dà 0 errori e 0 avvisi (`/tmp/libreFolio_i_l52_c1_front_check.log`); prettier `--check` sugli 8 file è pulito senza riscritture; `git diff --check` è pulito.
   > - **Nessun pin vecchio è caduto.** I due letterali `right: '4%'` ancora nei test (`chartCoreHelpers.test.ts:414`, `growthLadderAxis.test.ts:1689`) sono opzioni costruite a mano dentro i test, non pin del codice.
   > - **L'istantanea** è in `files/l52_c1_snapshot/` (stato di sessione): 8 file più `BLOBS.txt` con gli hash, sulla base `ef666fdee`.
5. ✅ 2026-10-13: **C2, 3a più la settimana di Alloc**: `formatDay` nelle intestazioni di Growth e Alloc; in Alloc la settimana finisce con `bucketSpanUpTo(row.date, row)`, perché è la stessa riga di 3a (§2.3). I rossi via test-author (`GrowthChart.test.ts` e il test di Alloc), poi la cura, i verdi e l'istantanea.
   - **L'àncora dell'E2E**: `dashboard.spec.ts:396` alza il tooltip delle candele cercando una data ISO nell'intestazione (`TOOLTIP_DATE`, usata a `:663`). Dopo la cura l'intestazione è nella lingua della UI, e il locale dipende dalla regione del browser (`en-US` o `en-GB`, `uiLocale.ts`). Quindi l'àncora diventa l'anno, che ogni intestazione porta in ogni lingua e a ogni larghezza. Nella card non c'è altro testo con quattro cifre di fila. L'àncora nuova è compatibile prima e dopo la cura.
   > **I rossi (2026-10-13)**: test-author `c2-reds`, brief in `files/l52_briefs/02-c2-reds.md` (stato di sessione). Nessun file di prodotto toccato: i blob restano quelli di C1.
   > - **`GrowthChart.test.ts`** (+210/−8 rispetto a C1):
   >   - quattro gruppi di pin B3 della scala (6 test) passano dall'ISO a `uiDay`, e lo slot della regex di `anyValueAt` diventa `.+`;
   >   - un describe nuovo in fondo, «Plan 52, C2», con 5 casi: Abs giornaliero, Abs e % settimanale, Abs mensile, it-IT settimanale con `forceInterfaceLocale`.
   > - **`AllocationHistoryChart.test.ts`** (+253/−2): un describe nuovo in fondo, con 5 casi: giornaliero, settimana chiusa, settimana in corso, mensile, fr settimanale con `switchLanguage`.
   > - **`dashboard.spec.ts`** (+9/−3): `TOOLTIP_DATE` diventa `TOOLTIP_YEAR = /\b\d{4}\b/`, con un JSDoc (`:402`, usata a `:669`). Solo modificata: gira negli E2E del passo 8.
   > - **Le fixture** arrivano al settimanale e al mensile con periodi lunghi, senza toccare il prodotto né le soglie:
   >   - Growth settimanale: 1700 giorni dal 2020-01-01, settimana chiusa 2022-03-07..13;
   >   - Growth mensile: 1700 mercoledì dal 1990-01-03, più ogni giorno di giugno 2005;
   >   - Alloc settimanale: 1100 giorni da gio 2022-06-23 a gio 2025-06-26; settimana chiusa 2024-06-03..09; settimana in corso 2025-06-23..26, con la domenica 06-29 ancora da venire;
   >   - Alloc mensile: 1100 mercoledì dal 2000-01-05, più ogni giorno di giugno 2010.
   > - **La mia revisione**:
   >   - `showChartTooltip` (`e2e/fixtures/charts.ts:77`) aspetta `anchor.count() >= minimum`, quindi più anni nella card non danno fastidio;
   >   - la gate `htmlInterpolation.gate.test.ts` non segnala `formatDay(...)`, `span.start` né `row.date` (i suffissi di testo sono a `:171`);
   >   - nessun altro test pinna l'ISO in queste intestazioni (`PerformanceChart`, `AllocationPanel` e `moneyRenderSites` non c'entrano).
   >
   > **⚠️ Fuori pista (2026-10-13)**:
   > - **Un pin vecchio di Alloc pinnava l'ISO.** `it.each(UNTOUCHED)` «today's tooltip» (~`:1236-1258`) controllava l'intestazione giornaliera grezza. Ora pinna `buildTooltipHeader(uiDay(ONE_DATE), …)` più `not.toMatch(ISO)`, col titolo «(D375 leaves it alone; plan 52 C2 writes its day in the interface language)». `dayIn` e `uiDay` sono saliti a livello di file (~`:815-827`).
   > - **Il primo test-author non c'era più** (`write_agent` fallito), quindi il ri-pin l'ha fatto un secondo test-author (`c2-repin`). La copia prima della modifica è in `/tmp/libreFolio_i_l52_ta/AllocationHistoryChart.test.pre-r3.ts`.
   >
   > **La conferma dei rossi nella corsia 6157**, a 1 worker, un selettore alla volta:
   > - `front-asset growth-chart-memo`: 11 rossi e 137 verdi (148), esattamente i nomi attesi;
   > - `front-portfolio allocation-unit`: 7 rossi e 238 verdi (245), cioè 2 UNTOUCHED più 5 di C2.
   >
   > I log sono `/tmp/libreFolio_i_l52_red_c2_{growth,alloc}.log`.
   >
   > **Note implementazione (2026-10-13)**:
   > - **`GrowthChart.svelte`** (+8/−6): l'import di `formatDay`; in `buildTooltipBucketHeader` ogni giorno passa da `formatDay`: il giorno singolo, la scala («1M - Oct 1, 2026 → Oct 31, 2026»), «valore al» (scala e linee), «settimana dal … al …». Il mese resta `formatTooltipMonth`. La scala tiene `bucket.period` (decisione d).
   > - **`AllocationHistoryChart.svelte`** (+10/−3):
   >   - gli import di `formatDay` e di `bucketSpanUpTo`, quest'ultimo da `priceChartHelpers`, come fa `CandlestickChart`. A runtime quel modulo porta solo gli schemi dei segnali, che stanno già nel bundle tramite `$lib/api/generated`;
   >   - settimanale: `bucketSpanUpTo(row.date, row)`, così la settimana in corso finisce sul suo ultimo giorno con dati, e tutte le date passano da `formatDay`;
   >   - mensile e giornaliero: `formatDay` su «valore al» e sul giorno.
   > - **Verdi nella corsia 6157**, a 1 worker, un selettore alla volta:
   >   - `front-asset growth-chart-memo`: 148 su 148;
   >   - `front-portfolio allocation-unit`: 245 su 245, 6 file;
   >   - `front-asset asset-unit`: 841 su 841, 20 file;
   >   - `front-utility component-unit`: 3142 su 3142, 117 file, comprese le gate `htmlInterpolation` e `moneyRenderSites`.
   >
   >   I log sono `/tmp/libreFolio_i_l52_green_c2_{growth,alloc,assetunit,compunit}.log`.
   > - **Le prove statiche**: `dev.py front check` dà 0 errori e 0 avvisi (`/tmp/libreFolio_i_l52_c2_frontcheck.log`); prettier `--check` sui 5 file è pulito; `git diff --check` è pulito.
   > - **L'istantanea** è in `files/l52_c2_snapshot/` (stato di sessione): 5 file più `BLOBS.txt`, sulla base `ef666fdee`. I 4 file del solo C1 restano sui blob di C1.
6. ✅ (2026-10-13; resta solo la corsa canonica in corsia, vedi «Fuori pista») **C3, 3b**: `bucketSpanUpTo` nei lotti. Il rosso via test-author, poi la cura, i verdi e l'istantanea.
   > **Disegno (2026-10-13)**:
   > - **Dove sta il punto**: `toChartSeriesPoints` (`:308`) è `aggregateLineSeries`, che lascia il punto sul suo ultimo giorno con dati, più `namedPoint(date, value)`. Quindi `data.value[0]` e `data.name` sono il giorno del punto, mentre `bucketStart`, `bucketEnd` e `resolution` arrivano da `pointBucketMeta` (`:298`). Il trigger `axis` tiene solo le serie alla distanza minima, quindi i param condividono una x.
   > - **L'helper**: `tooltipBucketInfo(params)` esce dal componente (`:391-401`) ed entra in `lotComparisonChartHelpers.ts`, esportato, accanto a `tooltipRawDate`.
   >   - Sceglie come prima il primo param con i meta del secchio; le serie interne (l'ancora, i punti di hover, i marcatori dei proventi) non li hanno.
   >   - Il suo `date` diventa il giorno del punto: `value[0]`, poi `name`, se è un giorno ISO. Altrimenti resta `bucketEnd`, come prima.
   > - **L'intestazione** (`buildTooltipBucketHeader`, `:403-416`): `const span = bucketSpanUpTo(bucket.date, bucket)`, come in `PriceChartFull`. «Valore al», la settimana e il mese leggono `span`, mai più `bucket.bucketEnd`. Il giornaliero resta com'è.
   > - **I test** stanno tutti in `lotComparisonChartHelpers.test.ts` (`front-utility component-unit`, ambiente node). Nessun file nuovo, quindi il runner non si tocca.
   >   - I casi puri di `tooltipBucketInfo`, dietro una barriera.
   >   - La composizione con `bucketSpanUpTo`, cioè le date che l'intestazione nomina.
   >   - Un pin del sorgente sulla colla, come i pin dei lotti di C1 in `chartCoreHelpers.test.ts`.
   >   - Un test montato vorrebbe un file nuovo e un'imbracatura di ECharts per i lotti: un costo alto per una riga di colla.
   > - **Fuori mandato**: in modo rendimento, se tutte le serie hanno il trigger `item`, l'ancora (`ensureAxisTriggerAnchor`, `:747`) non ha i meta, quindi l'intestazione è giornaliera anche a risoluzione settimanale. Nomina comunque un giorno giusto, quello dell'ancora, e c'è già nella base.
   >
   > **Note implementazione (2026-10-13)**:
   > - **Il rosso** (test-author, brief `files/l52_briefs/03-c3-reds.md`): una sezione nuova in fondo a `lotComparisonChartHelpers.test.ts` (`:946-1233`), 49 test in tre blocchi.
   >   - I casi puri di `tooltipBucketInfo`, dietro la barriera.
   >   - La composizione con `bucketSpanUpTo`, che fissa solo le due date lette dall'intestazione: per un secchio intero `bucketSpanUpTo` rende l'`info` stesso, con le sue 4 chiavi.
   >   - I pin della colla sul sorgente, più un controllo positivo sulla stessa fetta.
   >
   >   Base: 113 su 113 (`/tmp/libreFolio_i_l52_ta/c3_base_r1.log`). Rosso: 48 falliti e 114 verdi su 162 (`c3_red_r1.log`). I 45 casi puri e di composizione cadono sulla barriera; i pin C1, C2 e C3 cadono sul sorgente di oggi; il controllo positivo e i 113 vecchi restano verdi.
   >   - Il test-author ha provato in memoria il blocco contro un'implementazione fedele del contratto (49 su 49) e contro 12 varianti sbagliate, ognuna presa dal test giusto.
   >   - Ha aggiunto 4 casi coerenti col contratto: il giorno fuori dal secchio non viene tagliato, le 4 chiavi esatte con `Object.keys`, e due righe in più sui ripieghi.
   >   - Non è fissato, di proposito, un `value` oggetto con la chiave `0`: la cura lo tratta come «non un array», quindi legge `name`, come vuole A9.
   > - **La cura**:
   >   - `lotComparisonChartHelpers.ts` esporta `tooltipBucketInfo(params)`, con un privato `pointOwnDay` e un `ISO_DAY_PATTERN` locale (nessun predicato ISO esportato nei moduli dei lotti).
   >   - In `LotComparisonChart.svelte`:
   >     - l'helper arriva dall'import dei lotti e `bucketSpanUpTo` da `priceChartHelpers`;
   >     - la copia locale è sparita, e con lei il tipo `BucketInfo`, che non usava più nessuno;
   >     - l'intestazione fa `const span = bucketSpanUpTo(bucket.date, bucket)` e nomina solo `span`.
   > - **I verdi**: il file è a 162 su 162 (`/tmp/libreFolio_i_l52_green_c3_helpers_r1.log`). I quattro vicini che leggono il componente (`chartCoreHelpers`, `resizeWatcher`, `moneyRenderSites`, `currencyFormat`) sono a 296 su 296, 4 file (`/tmp/libreFolio_i_l52_green_c3_neighbours_r1.log`).
   > - **Le prove statiche**:
   >   - `npm run check` dà svelte-check con 0 errori e 0 avvisi (`/tmp/libreFolio_i_l52_c3_npmcheck_r1.log`);
   >   - prettier `--check` sui 3 file è pulito, e `git diff --check` pure.
   > - **L'istantanea** è in `files/l52_c3_snapshot/`, base `ef666fdee`. Blob: componente `4c3e4b5e` (C1 + C3), helper `65e05d0b`, test `c88a0f23`.
   >
   > **⚠️ Fuori pista**: il coordinatore ha dichiarato FREEZE-VENV (2026-10-13), il developer aggiorna il venv condiviso. Fino a UNFREEZE-VENV niente `dev.py`, `pipenv` né server.
   > - Quindi i verdi e il controllo dei tipi sono girati con node puro: `frontend/node_modules/.bin/vitest run <file>` e `npm run check`. Il loro aggancio del catalogo usa il `python3` di sistema, non il venv.
   > - ✅ **Dopo UNFREEZE-VENV** (2026-10-13), le prove canoniche, una alla volta sulla 6157:
   >   - `front-utility component-unit` → 117 file, 3142 test, tutti verdi (`/tmp/libreFolio_i_l52_c3_component_unit.log`);
   >   - `dev.py front check` → svelte-check con 0 errori e 0 avvisi (`/tmp/libreFolio_i_l52_c3_front_check.log`).
6b. ✅ 2026-10-13 (gli E2E della Dashboard restano al passo 8) **C3b, il periodo in corso di Growth** (§2.3, (A)): i rossi via test-author (il punto sull'ultimo giorno con dati, l'intestazione, lo zoom e la cascata), poi la cura in `GrowthChart.svelte`, i verdi (anche `growth-chart-memo` e gli E2E della Dashboard) e l'istantanea.
   > **Disegno (2026-10-13)**, righe allo stato C2:
   > - **A1, il punto**: in `buildBucketInfos` (`:826-852`) un secchio settimanale o mensile prende come `date` **l'ultimo giorno della storia che cade nel secchio**, non la sua fine di calendario. `bucketStart` e `bucketEnd` restano i bordi del calendario, e le ricerche per `bucket.date` (`aggregateMetric` `:951`, `aggregateFlowMetric` `:995`, `aggregateCandleMetric` `:1038`) ora trovano il punto aggregato, che `aggregateLineSeries` mette proprio sull'ultimo giorno con dati.
   >   - Un periodo intero non cambia, perché la storia riempie ogni giorno del calendario: l'ultimo giorno è la sua fine.
   >   - Il periodo in corso sta sul suo ultimo giorno con dati, quindi la linea arriva a oggi e l'asse non finisce più su un giorno che deve venire (`entry.dates` alimenta anche la politica dell'asse e `timeAxisGridRight`).
   > - **A1, l'intestazione** (`buildTooltipBucketHeader`, ramo della cascata, `:1419-1425`): `const upTo = bucketSpanUpTo(bucket.date, bucket)`, come in `PriceChartFull`, Alloc e i lotti. «Valore al», la settimana e il mese leggono `upTo`. La scala non cambia.
   >   - Caso limite: una settimana in corso con un solo giorno dice «Settimana lun – lun», come già i prezzi e Alloc.
   > - **Z2, lo zoom della cascata** (solo se serve, vedi la prova sotto). La percentuale di `dataZoom` su un asse del tempo è lineare nel **tempo** fra il primo e l'ultimo punto della serie (`AxisProxy.calculateDataWindow`), mentre il lettore (`getLogicalRangeFromChart`, `:1211`) e il costruttore (`buildZoomWindow`, `:1236`) la leggono come un **indice** di secchio.
   >   - Oggi i secchi settimanali sono equidistanti, quindi le due letture coincidono. Dopo A1 l'ultimo intervallo si accorcia a d giorni: da settimanale a giornaliero il bordo sinistro può perdere una settimana, e all'indietro, con la fine interna, la finestra finisce fino a 7−d giorni prima del punto della sua ultima settimana, che sparisce. Nel mensile è peggio.
   >   - La cura: solo per la cascata, il lettore e il costruttore mappano in giorni (`t = d0 + p·(dN − d0)`, inizio = l'ultimo secchio con il giorno ≤ t, fine = il primo con il giorno ≥ t, con una tolleranza di 0,1 giorno per l'ora legale e la virgola mobile). La scala, su un asse a categorie, resta a indice. Per i secchi equidistanti il risultato è identico a oggi.
   >   - I pin restano: le quattro righe del lettore (`chartCoreHelpers.test.ts:1924-1927`) e la fetta dal lettore a `buildZoomWindow`, quindi l'helper nuovo va prima del lettore o dopo il costruttore, mai fra i due.
   > - **La prova che decide Z2**: prima applico A1 da solo. Se i rossi dello zoom (T3, T4) restano verdi, Z2 non entra.
   > - **I test** (test-author, brief `files/l52_briefs/04-c3b-reds.md`), in `GrowthChart.test.ts` (`growth-chart-memo`) più un contratto SSR in `chartCoreHelpers.test.ts`, nessun file nuovo:
   >   - T1, il punto: settimanale e mensile, nei modi Abs, % e P&L a linee, l'ultimo punto sta sull'ultimo giorno della storia col suo valore; nessuna x dopo quel giorno. Rosso alla base.
   >   - T2, l'intestazione dell'ultimo secchio: settimana dal lunedì all'ultimo giorno, «valore al» l'ultimo giorno; nel mensile il mese e l'ultimo giorno. Rosso alla base.
   >   - T3, zoom da settimanale a giornaliero e T4, da giornaliero a settimanale con la fine interna: le finestre lette e scritte combaciano col tempo. Verdi alla base, rossi con A1 da solo.
   >   - Il contratto SSR: con l'ECharts vero, su un asse del tempo con le x non equidistanti, l'estensione della finestra è `x0 + p·(xN − x0)`.
   > - **Fuori mandato, da annotare**: i lotti hanno la stessa approssimazione a indice su un asse del tempo dalla v1.0.0 (`lotComparisonChartHelpers.ts:468-545`); i flussi della cascata (`pnl.income`, `costs`, `deposits`, `acquisition`) del secchio in corso valevano 0, ma la cascata non li disegna più (Proventi è della scala), quindi A1 li corregge senza effetto visibile.
   > **Avanzamento (2026-10-13)**:
   > - I rossi (test-author, brief 04): `GrowthChart.test.ts` da 148/148 a 159 test, 9 rossi (T1 ×6, T2 ×3) e T3/T4 verdi (`/tmp/libreFolio_i_l52_ta/c3b_red_growth_r3.log`); `chartCoreHelpers.test.ts` da 257 a 258/258, il contratto SSR verde (`c3b_red_core_r2.log`). Il contratto lo conferma sull'ECharts vero: al 50 % la finestra parte a x0 + 8,5 giorni (il tempo), non a + 10,5 (l'indice). `npm run check` 0/0. Il blocco nuovo: `GrowthChart.test.ts:4219-4591`, `chartCoreHelpers.test.ts:5008-5071`.
   > - A1 applicato (`buildBucketInfos`, l'intestazione con `upTo`, l'import di `bucketSpanUpTo`). **La prova di Z2**: con A1 da solo 157/159, T1 e T2 verdi, **T3 e T4 rossi** come previsto (T3: la finestra giornaliera apre il 2024-07-01, 7 giorni dopo il lunedì atteso; T4: l'inizio cade 0,115 giorni prima del punto), log `/tmp/libreFolio_i_l52_c3b_a1_growth_r1.log`. Quindi **Z2 entra**.
   > **Note implementazione**:
   > - **Z2** in `GrowthChart.svelte`, prima del lettore: `cascadeDayOffsetsOf` (i giorni di ogni punto dal primo, con `daysBetween`, in cache per voce con una `WeakMap`), `ladderIndicesAt` (la scala, `Math.round` sull'indice com'era) e `cascadeIndicesAt` (la cascata nel tempo: inizio = l'ultimo punto con giorno ≤ t + 0,1, fine = il primo con giorno ≥ t − 0,1, costante `ZOOM_EDGE_SNAP_DAYS`). Nel lettore una riga sola sceglie fra i due. Nel costruttore la ricerca degli indici non cambia; per la cascata la percentuale diventa `offset/span·100`, che sui giorni consecutivi è identica bit per bit a `indice/(N−1)·100`.
   > - Verificato prima di scrivere: `planLadderFor` (`visibleStartIndex`) è solo della scala; nella cascata nessuna serie ha x fuori dai secchi (la linea di riferimento del P&L usa i dati della serie 2, niente `markLine`/`markArea`), e l'asse del tempo non ha `min`/`max`, quindi l'estensione è proprio [primo punto, ultimo punto].
   > - Il commento di `chartCoreHelpers.test.ts:1950-1954` (via test-author): la cascata legge la finestra nel tempo, che su date equidistanti si riduce al floor/ceil di `logicalRangeFromBuckets`.
   > - Prettier ha chiesto di andare a capo su una riga mia (`Math.max(0, offsets.findLastIndex(…))`): applicato con `prettier --write`, solo quella riga.
   > - **Prove** (plain node): `GrowthChart.test.ts` 159/159; tooltip + `chartCoreHelpers.test.ts` 264/264; sull'ultima versione dei blob 423/423 (`/tmp/libreFolio_i_l52_c3b_z2_final.log`). **In corsia 6157, a 1 worker, uno alla volta**: `front-asset growth-chart-memo` 159/159 (`/tmp/libreFolio_i_l52_c3b_lane_memo.log`), `front-utility component-unit` 3142/3142 in 117 file (`…_lane_component.log`), `front-asset asset-unit` 842/842 in 20 file, dove sta `chartCoreHelpers.test.ts` (`…_lane_assetunit.log`). `npm run check` 0/0; prettier `--check` pulito sui tre file; `git diff --check` pulito.
   > - **Istantanea `c3b`**: `GrowthChart.svelte` `d9426982`, `GrowthChart.test.ts` `2ad04c21`, `chartCoreHelpers.test.ts` `8eac9634` (`files/l52_c3b_snapshot/`).
   > **⚠️ Fuori pista**:
   > - Il brief 04 aveva un indice sbagliato: la settimana del lun 2024-06-24 è la decima dalla fine (`length − 10`), non `lastIndex − 10`. Corretto prima di consegnarlo.
   > - Z2 non era sicuro in partenza: è entrato solo dopo la prova di A1 da solo (sopra).
   > - Il debito che resta fuori mandato: i lotti mappano ancora l'indice su un asse del tempo (`lotComparisonChartHelpers.ts:468-545`), dalla v1.0.0. Nota per il backlog nel checkpoint.
7. ✅ 2026-10-13 **C4**: il commento della pillola (§1.6).
   > **Note implementazione**: via test-author, una riga sola (`toolbar-width-sweep.spec.ts:1089`) col testo approvato; le due attese restano. Prettier `--check` pulito, `git diff --check` pulito, diff 1+/1−. Istantanea `c4`: `034aba35` (`files/l52_c4_snapshot/`). Il test della pillola gira al passo 8.
8. ✅ 2026-10-13 Gli E2E della Dashboard e dei lotti, `front check`, prettier: un comando alla volta sulla 6157.
   > **Note implementazione** (tutto a 1 worker sulla 6157, uno alla volta, `LIBREFOLIO_TEST_STARTUP_TIMEOUT=900` sui comandi E2E):
   > - `front-portfolio dashboard` r4: **27/27 in 1,6 min** (`/tmp/libreFolio_i_l52_s8_dashboard_r4.log`). Stesso codice di r3: i 5 rossi di r3 erano il carico. Il riscontro sul codice: la scala ha il suo costruttore (`buildLadderBuckets`) e il suo lettore (`ladderIndicesAt`, invariato), quindi A1 e Z2 non la toccano.
   > - `front-broker detail` (i grafici dei lotti e il P&L del broker): **37/37 in 1,5 min** (`…_s8_brokers_detail.log`).
   > - `front-utility core-unit` (contiene `lotComparisonChartHelpers.test.ts`, `_frontend_utility.py:117`): **4189/4189 in 128 file** (`…_s8_core_unit.log`).
   > - `front-portfolio allocation-unit` (contiene `AllocationHistoryChart.test.ts`, `_frontend_portfolio.py:219`): **245/245 in 6 file** (`…_s8_alloc_unit.log`).
   > - `front-utility toolbar-width-sweep "Assets lifecycle pill"`: **4/4** (en, it, fr, es) (`…_s8_pill.log`).
   > - `dev.py front check`: svelte-check **0 errori, 0 avvisi** (`…_s8_front_check.log`); prettier `--check` pulito sui 12 file del lotto (`…_s8_prettier.log`); il worktree non cambia.
   > - `npm run lint:dead` (knip): nessun rilievo sui file del lotto né sugli export nuovi (`axisLabelFont` e `AxisLabelMeasure` li usa il test); l'uscita 1 viene da 101 righe preesistenti (`…_s8_knip.log`).
   > - Già fatte in C3b sugli stessi blob: `front-asset growth-chart-memo` 159/159, `front-utility component-unit` 3142/3142, `front-asset asset-unit` 842/842.
   > **Avanzamento (2026-10-13)**:
   > - `front-portfolio dashboard`, r1 e r2: rossi d'infrastruttura **prima della raccolta**, «Shared backend did not answer within 300s» (`/tmp/libreFolio_i_l52_s8_dashboard{,_r2}.log`). Nessun test eseguito; il DB della corsia non è stato toccato dai test.
   > - r3, a build fresca: **22 passati, 5 rossi in 47,1 min** (`/tmp/libreFolio_i_l52_s8_dashboard_r3.log`), tutti di tipo carico:
   >   - `:86` Performance view e `:1839` S7-E1-1m: il `beforeEach` sfora i 30 s (il login resta visibile dopo 20 s, `auth-helpers.ts:77`);
   >   - `:619` candele pigre: `dashboard-page` non visibile in 15 s (`:440`);
   >   - `:1839` S7-E1-1w e `:1876` S7-E2: il contatore dei ridisegni non sale in 15 s (`:1803`, `:467`).
   >   - Le durate a muro (1,8, 7,6, 16,5, 16,4 e 2,6 min contro i 2–11 s dei verdi vicini) dicono che il processo è stato fermo, non che il grafico è lento.
   > **⚠️ Fuori pista**:
   > - La diagnosi di r1/r2: ho acceso a mano `dev.py server --test` sulla 6157. Il server fa l'export OpenAPI, `generate-api`, svelte-check e, coi sorgenti più nuovi della build, `vite build`: sotto un carico di 17–22 e 5,7 GB di swap la build ha preso **25–27 min**, e il server ha risposto dopo circa 54 min (`/tmp/libreFolio_i_l52_diag_server.log`). Poi l'ho fermato e ho provato la porta libera; nessun file tracciato è cambiato. Nessuna cura: rosso d'infrastruttura segnalato al coordinatore.
   > - Il coordinatore (2026-10-13, sera): macchina libera dalle altre corsie; dopo una modifica ai sorgenti, `LIBREFOLIO_TEST_STARTUP_TIMEOUT=900` nel prefisso (`scripts/test_runner/_server.py:46-48`), oppure `dev.py front build --debug` prima. Il carico residuo (~40 su 10 core) viene dalle app del desktop (Chrome, l'app Copilot, WindowServer) e dallo swap, non dai test.
9. ✅ 2026-10-13 La sonda dopo la cura (stessa matrice, `as-is`), con es fra le lingue degli scatti: attesi 0 tagli. Nel rapporto i montaggi en ed es a 320 e 360 px.
   > **Note implementazione**:
   > - Server acceso a mano sulla 6157 (`dev.py server --test --no-reload --no-scheduler`, build già aggiornata). Poi la sonda con `L52_TAG=fix L52_VARIANTS=as-is L52_SHOT_VARIANTS=as-is L52_SHOT_LOCALES=en,it,es`: **1 passato in 8,8 min**.
   >   - 560 misure più 4 salti: l'asset 17 non ha il grafico dei lotti, come nella base. Nessun caso non assestato.
   >   - I file: `/tmp/libreFolio_i_l52_probe/fix_rows.json` e `fix_run.log`, più 63 scatti `fix__*`.
   > - **L'analisi** (`/tmp/libreFolio_i_l52_analyse_fix.py`, che scrive `fix_analysis.log` e `fix_compare.json`):
   >   - **I tagli dell'ultima etichetta passano da 334 a 0, su 560 casi.** Non c'è nessun taglio nuovo, e nessuna ultima etichetta che nella base era intera è sparita.
   >   - **Come finisce l'asse nei 334 casi curati** (`fix_maxhidden.log`):
   >     - 259 mostrano intera l'etichetta del massimo;
   >     - 61 mostrano la stessa data finale con un tick che coincide col massimo;
   >     - 14 la nascondono, perché `hideOverlap` la toglie quando si sovrappone al tick precedente. È meglio del taglio. 12 di questi sono Growth a 365 giorni a 440 px (più fr a 1280): lì la base mostrava, tagliata, «Oct 18, 26», cioè la settimana aperta che A1 toglie. Ora l'asse finisce con «Sep».
   >   - **Le prime etichette perse rispetto alla base sono 29.**
   >     - 17 sono Growth a 365 giorni a 360 e 390 px. A1 cambia l'estensione (da `10-17` a `10-12`) e quindi i tick: l'asse diventa «2026 | Mar | May | Jul | Oct 13, 26» invece di «Oct 19, 25 | Apr | Jul | Oct 18, 26», con più etichette.
   >     - 6 sono il 29/9 a 14 giorni, due giorni prima di «Oct 1».
   >     - Il resto: Alloc 4, Growth fr a 90 giorni 1, Lots 1.
   >     - Senza le 17 di A1 ne restano 12, contro le 16 della simulazione a3 (§1.4).
   >   - **Un'etichetta in meno in 70 casi su 560**, di solito da 5 a 4 o da 4 a 3, perché il grafico è più stretto. La differenza media: Growth sui telefoni −14,8 px, Alloc −13,2, Lots −5,0.
   >   - **Rispetto alla simulazione a3, 284 casi diversi.** Le cause: A1 (Growth a 365 giorni) e l'inset vero, che differisce di 2–8 px da quello simulato. I tagli restano 0.
   > - **A occhio.** I montaggi sono in `/tmp/libreFolio_i_l52_probe/`: `montage_fix_growth_{en,es}_s30.png`, `montage_fix_alloc_lots_{en,es}.png`, `montage_fix_growth_s14_lostmin.png` e `montage_fix_growth_s45_it.png`.
   >   - A 320 px, la «Oct 1…» tagliata diventa «Oct 13» intera in Growth, Alloc e Lots, anche in es («13 oct») e in it («13 ott»).
   >   - Le altre larghezze mostrano le stesse etichette, o ne perdono una interna.
   >   - Nessun doppione.
   >   - La lettura resta buona, quindi non c'è niente da fermare.
   > **⚠️ Fuori pista**:
   > - **Lo spostamento dei lotti** (`lots_w320_full_base_fix.png`). Negli scatti della base delle 07:15, nella variante `as-is` la serie del valore è compressa al 90% circa dell'asse; nella variante `a`, invece, è il marcatore della vendita a essere fuori posto.
   >   - **Escluso**:
   >     - i dati: l'archivio del mattino e il DB di adesso coincidono nei prezzi, nei cambi e nelle 25 transazioni;
   >     - il diff del lotto, che tocca solo l'intestazione del tooltip e `grid.right`;
   >     - il fast-forward delle 07:37.
   >   - **La prova**: la corsa a3 delle 07:30, **sulla stessa build della base**, disegna la serie allineata a tutte e quattro le larghezze, come la cura (`lots_runs_grid.png`, `lots_runs_grid2_top.png`).
   >   - **Una sonda in più sulla cura** (`/tmp/libreFolio_i_l52_rt/rt-lots-check.spec.ts`): due flussi (allargato e poi stretto, oppure stretto da subito), ciascuno due volte, con tre letture in 2,5 s. Danno sempre 51 punti giornalieri, dal 24/8 al 13/10, che coprono tutto l'asse (`lotscheck_rows.json`, `lotscheck_summary.log`).
   >   - **La conclusione**: è un fotogramma di transizione, catturato sotto il carico del mattino, e non un effetto del lotto. Non lo rivendico come cura.
   > - Il `python3` di sistema non ha PIL, quindi per i montaggi ho usato il Python del venv della corsia, in sola lettura, senza installare nulla.
   > - Il server è fermo, la porta 6157 è libera (`lsof` non trova ascoltatori), e il DB estratto in `/tmp/libreFolio_i_l52_dbcmp/` è cancellato.
10. ✅ 2026-10-13 La documentazione via docs-writer (`charts.md`, «Responsive Date Axis»); `mkdocs build` stretto e `check-links`.
   > **Note implementazione**:
   > - docs-writer ha toccato **solo** `mkdocs_src/docs/developer/frontend/components/charts.md` (+76 −5, 4 blocchi), in inglese:
   >   - dopo il paragrafo sul cambio di risoluzione (`:79-106`), due paragrafi nuovi: **«Weekly and monthly points»** (il periodo in corso sul suo ultimo giorno con dati, A1; lo zoom che resta nel tempo, Z2) e **«Tooltip dates»** (le intestazioni di Growth, Alloc e dei lotti nella lingua della UI, con la settimana in corso che finisce sull'ultimo giorno con dati);
   >   - l'esempio della scala diventa `1M - 1 Oct 2026 → 31 Oct 2026` in `en-GB` (`:177`);
   >   - in «Responsive Date Axis», i punti **«Right inset»** e **«Inset candidates»** (`:352-381`), più un paragrafo sui tre consumatori (`:407-417`): Growth e Alloc con base `4%` e font di 14 px, Lots con base 18 px e 12 px; LotWac e LotGantt tengono `GRID_RIGHT_PX` 18.
   > - **Le prove**:
   >   - `dev.py mkdocs build` (stretto): uscita 0, nessun avviso, «All 3012 relative asset URL(s) in the built site resolve» (`/tmp/libreFolio_i_l52_docs_build.log`);
   >   - `dev.py mkdocs check-links`: **95 link validi**, «All cross-boundary links are valid!»; gli 8 🔵 si risolvono a runtime e non sono del lotto (`/tmp/libreFolio_i_l52_docs_links.log`).
   > - **La mia revisione**, sul diff (`/tmp/libreFolio_i_l52_docs_diff.log`) contro il codice: `GRID_RIGHT_PX = 18` in LotWac e LotGantt; `bucketSpanUpTo` già usato da PriceChartFull e CandlestickChart; `formatLongDate` dei lotti nello stesso formato di `formatDay`; `axisDateRange = xAxisRange ?? fallback` (`LotComparisonChart.svelte:1094`). Tutto vero: pagina accettata.
   > **⚠️ Fuori pista**:
   > - **La lingua degli esempi**: in inglese `uiLocale()` usa `en-GB` (`LANGUAGE_DEFAULTS`), quindi docs-writer ha scritto *1 Oct 2026* per `en-GB` e *Oct 1, 2026* per `en-US`. Il commento di `GrowthChart.svelte:1467` resta nella forma `en-US`: è cosmetico, e lo lascio com'è per non cambiare il blob di C3b.
11. ✅ 2026-10-13 Il checkpoint col manifest, le proposte per la wiki da girare a W, poi FROZEN.
   > **Note implementazione**:
   > - **Il pacchetto** è in `files/timeaxis_commit_bundle/` (stato di sessione): `MANIFEST.txt`, i 7 messaggi in `messages/`, le cartelle `stage_C1` … `stage_C6` (i file di ogni stadio più `BLOBS.txt`) e le prove in `evidence/`, cioè i log `/tmp/libreFolio_i_l52_*` più, in `evidence/probe/`, le analisi, i montaggi e le spec della sonda. Lo script è `/tmp/libreFolio_i_l52_bundle.sh`, il log `/tmp/libreFolio_i_l52_bundle.log`.
   > - **Gli stadi**: 7 commit su 14 percorsi.
   >   - C1 `fix(charts): keep the last time-axis label whole`: l'helper, i tre consumatori e i loro test (8 file).
   >   - C2 `fix(charts): localize dashboard tooltip dates`: Growth, Alloc, i loro test e `dashboard.spec.ts` (5).
   >   - C3 `fix(charts): end running lot buckets on last day`: LotComparison, i suoi helper e il loro test (3).
   >   - C3b `fix(charts): draw Growth's running period to date`: Growth, il suo test e `chartCoreHelpers.test.ts` (3).
   >   - C4 `test(e2e): reword the pill sweep login comment`, C5 `docs: document the time-axis right inset`, C6 `docs(journal): plan 52, time-axis last label` (un file ciascuno; C6 è questo piano).
   >   - Sei file passano per più stadi, col blob di ogni stadio nel manifest: `GrowthChart.svelte` e `GrowthChart.test.ts` (C1, C2, C3b), `chartCoreHelpers.test.ts` (C1, C3b), `AllocationHistoryChart.svelte` e il suo test (C1, C2), `LotComparisonChart.svelte` (C1, C3).
   > - **I controlli dello script**, tutti verdi:
   >   - ogni blob di stadio coincide con la sua istantanea, presa sulla HEAD `ef666fdee`, e il worktree coincide con l'ultimo stadio di ogni file;
   >   - il delta (`git diff` più i non tracciati) è uguale ai 14 percorsi del manifest;
   >   - i messaggi: oggetto entro 50 caratteri, seconda riga vuota, solo ASCII, righe entro 72;
   >   - privacy: 0 rilievi sulle righe aggiunte, su tutto il piano e sui messaggi;
   >   - `git diff --check` pulito, niente in stage, porta 6157 libera.
   > - **Il target** `dev_release2` = `f8dbdddaf` ha 35 commit dopo la mia HEAD, che è la base comune (treni 94–96). Nessuno dei 14 percorsi cambia nel target, e il target non tocca i grafici, la Dashboard, i lotti, `utils/core`, gli E2E del lotto, la pagina della doc né i cataloghi: la fusione non ha sovrapposizioni.
   > - **Al coordinatore, nel messaggio del checkpoint**:
   >   - la provenienza di ogni difetto (a3 e l'intestazione della scala di Growth nuove nella 1.2; 3a, 3b, la settimana di Alloc e il periodo in corso di Growth dalla v1.0.0);
   >   - la riga 🐛 del periodo in corso (`CHANGELOG.md:162` del target), da allargare al grafico Growth, alla storia dell'allocazione e al grafico di comparazione dei lotti, con un testo proposto; 3a è già coperto dalla riga 🔄 «Numbers and dates follow the interface language everywhere» (`:266`);
   >   - la voce del backlog: i lotti leggono lo zoom per indice su un asse del tempo dalla v1.0.0 (`lotComparisonChartHelpers.ts:468-545`, §3 passo 6b);
   >   - la nota per M: sui telefoni cambiano gli scatti della galleria di Growth, Alloc e lotti (l'inset a destra; l'ultimo punto di Growth a risoluzione settimanale o mensile);
   >   - le proposte per la wiki, da girare a W: le regole di ECharts trovate qui (`containLabel` non riserva la mezza sporgenza dell'ultima etichetta; l'estensione dell'asse del tempo non è arrotondata; `hideOverlap` nasconde già con uno scarto di circa 2 px; `outerBounds` stima una volta sola, prima di `hideOverlap`), il periodo in corso sull'ultimo giorno con dati come regola comune dei grafici a secchi, la percentuale di `dataZoom` lineare nel tempo su un asse del tempo (Z2), e le sonde che sotto carico catturano fotogrammi di transizione (§3 passo 9).
   > - Nessun server acceso, porta 6157 libera; la corsia `/tmp/librefolio-r2-i-charts` resta. Poi FROZEN.
