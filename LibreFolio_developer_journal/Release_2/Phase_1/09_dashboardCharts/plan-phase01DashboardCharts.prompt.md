# Piano — fase 01, 09: Y · Cruscotto e grafici (1.3.0)

> **Stato**: 🧊 **Y1 consegnato FROZEN** (2026-10-15, 14:40), in attesa del commit del coordinatore; il cancello
> d'ingresso è la galleria filtrata, dopo il commit. Y2 in preparazione in sola lettura, fino alla conferma
> dell'annuncio. Autorizzati solo **Y1** e **Y2** (§0.2).
>
> - **Workstream Y** · worktree `LibreFolio-worktrees/e-alfy-redesigned-spork` · ramo `e-alfy-y-cruscotto-e-grafici`
>   (rinominato dall'app all'avvio; prima `e-alfy-redesigned-spork`).
> - **Base**: `1e9e567f79488cfb5630f3c05e1bd2727bf856d7` (avanzamento veloce del coordinatore dal `23f6578f3`
>   dell'analisi: Designer Lab, chiusura di R, la 1.2.1 di sicurezza; nessun file del perimetro di Y).
> - **Corsia**: `--test-port 6189 --data-dir /tmp/librefolio-r13-y`, con
>   `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test …`; un comando alla volta; mai 6040 né
>   6041, mai `--force`, mai `./dev.py` nudo.
> - **Coordinatore**: «Release 1.3 planning», `928ffa97-f0c3-4975-a442-3de0c2c20fc7`.
> - **Fonti**:
>   - il [piano generale della fase](../plan-phase01Release13.prompt.md): §4 «Y», §6 (regole comuni, «Taglio
>     dichiarato»), §7 (regola «chi parte prima»), §8, §9;
>   - le [decisioni delle analisi](../decisioni-analisi-20261014.md), punti 26–30;
>   - il [piano 43](../../Phase_0/43_financialMathHome/plan-phase00FinancialMathHome.prompt.md), §2 (inventario delle U)
>     e P2.4 (FE2–FE11);
>   - il [backlog dopo la 1.2](../../Phase_0/BACKLOG_POST_1.2.md) (sezioni C, I, T) e il
>     [backlog 38](../../Phase_0/38_postReleaseBacklog/README.md) (K-13, K-15, C-15, C-34, C-38, I-01, I-03, O-16);
>   - il [README della 13](../../Phase_0/13_pacAllocator/implementation/README.md), difetti 2 e 5;
>   - il programma colori, in sola lettura: [`10_colorSystem/`](../10_colorSystem/README.md), piani di R e di T.
> - **Wiki**: grafo assente nella worktree (atteso). Lette direttamente: `problems/datatable-actions-column-on-mobile`,
>   `problems/datatable-column-resize-noop`, `decisions/html-escape-at-the-source`.

## 0. Mandato e autorizzazioni

### 0.1 Mandato (kickoff del coordinatore, 15/10, 11:28)

Perimetro del §4 del piano generale: spostamenti di cartella di segnali e rischio (FE2), dashboard (FE6), broker e lotti
(FE7), file (FE3), per ultimi FE9–FE11; i tagli annunciati di `table/DataTable.svelte` e `dashboard/GrowthChart.svelte`,
prima delle ondate W5 e W6 della conversione dei colori (T); frontend di sola presentazione (U8) con i campi di J;
C-85; K-13; K-15, C-34, C-15; I-01, I-03, 47-1, 54-1, B10, 48-1, O-16; C-38 con i difetti 2 e 5 del PAC; C-62.
Il riordino non blocca il rilascio; la conversione dei colori di queste cartelle sì.

### 0.2 Autorizzazione (15/10, ~12:47)

Parole del developer, alla lettera, inoltrate dal coordinatore: «Sì: avvia tu Y (i due tagli) e Z (Z6a subito, Z1
quando decido il 31)».

**Autorizzati: Y1 (taglio di `GrowthChart`) e Y2 (taglio di `DataTable`).** Gli altri lotti dopo.

### 0.3 Decisioni del coordinatore sulle proposte dell'analisi (15/10)

| # | Decisione |
|---|---|
| D-Y1 | Prima `GrowthChart` (Y1), poi `DataTable` (Y2) |
| D-Y2 | `DataTable` tagliata come FE8a: figli di template con props esplicite; stato, effetti, gestori e API pubblica restano nel padre; il CSS segue il markup; ogni figlio importa `table.css` |
| D-Y3 | `GrowthChart` tagliato sul posto in tre moduli puri (`growthChartData.ts`, `growthChartSeries.ts`, `growthChartTooltip.ts`); nel componente restano stato, effetti, ciclo di vita di ECharts e template; poi lo spostamento (FE6b). **B10 entra in Y1** |
| D-Y4 | FE6b subito dopo i tagli; FE7 e FE3 dopo l'ingresso di FE8a di W; FE2 dopo FE4 e FE5a di X e prima di FE5c (lo concorda il coordinatore con X) |
| D-Y5 | Niente barili nuovi; le cose che restano al loro posto si elencano qui (§3) |
| D-Y6 | Per ogni lotto, via del coordinatore con le righe esatte dei file del runner degli altri (`_frontend_utility.py`, `_frontend_asset.py`, `_frontend_ai_export.py`) |
| D-Y7 | `npm ci` dal lock, `front build --debug`, `mkdocs build` solo dopo l'avviso di fine della finestra della galleria (verso le 13:00) |
| D-Y8 | Le gallerie filtrate le mette in calendario il coordinatore con il coordinatore colori, al checkpoint |
| D-Y9 | 48-1 con l'ok di J, più avanti; i due `title` di C-15 vanno a W |
| — | K-12, K-14 e I-02 restano fuori |
| — | C-85, 54-1 e difetto 5 del PAC: al developer, nel file delle decisioni (lotti dopo Y2) |

### 0.4 Condizioni del coordinatore per il taglio di `GrowthChart` (15/10, dopo l'ok del coordinatore colori)

Nessun annuncio aperto sul file; T lo converte più avanti, nell'ondata W5.

1. `node frontend/scripts/theme/theme-roles.mjs --split <vecchio>:<pezzi>` nello stesso commit, poi `--check` pulito.
   Il record in baseline è ancora quello di prima di R (m1 86, molti letterali); i moduli `.ts` nuovi non aggiungono
   letterali né classi legacy: i colori dei grafici vivono in `lib/theme/chart*.ts`.
2. Restano invariati `data-testid="growth-chart"` e la forma dell'opzione di ECharts: la E2E dal vivo del Designer Lab
   (`designer-lab-live.spec.ts`) apre il grafico e ne legge i colori.
3. Validazione anche con `front-designer-lab`, insieme a `front-utility theme-roles` o `--check`.
4. Galleria filtrata del checkpoint, dopo la fine della finestra, nella corsia:
   `scripts/visual_review/gallery_snapshot.sh <etichetta> --checkout <worktree> --port 6189 --data-dir
   /tmp/librefolio-r13-y -- -f "Dashboard|Brokers" --workers 6`; confronto con il riferimento `g-final3-r1` di oggi,
   `--common-only --ignore-masks $W/diffs/g-final3__r1__vs__r2/masks --stability
   $W/diffs/g-final3__r1__vs__r2/stability.json`. Rumore noto: `static-grid`, `import-modal` e gli scatti instabili.

Per Y2: annuncio al coordinatore quando ci arrivo. Il lotto C di R ha portato `DataTable` sui token `--lf-cmp-*`, e la
E2E del Lab legge il token della sua intestazione.

## 1. Stato reale (verificato sul codice a `23f6578f3`; identico a `1e9e567f7` nel perimetro)

- Lotti A–D di R in `dev_release2`: `lib/theme/{chartTheme,chartPalettes,chartColorScales,themeMode,colorAlpha}.ts`,
  `--lf-cmp-*` in `lib/theme/components/*.css`.
- Cartelle: `components/charts` 63 file / 30k righe; `dashboard` 29 / 20,7k; `risk` 91 / 37,9k; `brokers` 38 / 18,4k
  (`lots` 25); `files` 6 / 3,9k; `table` 15 / 9,7k; `lib/charts` 39 / 8,2k; `lib/risk` 4; `stores/risk` 6;
  `stores/portfolio` 8. Nessuna `features/{dashboard,risk,signals,brokers,files}`; nessun barile nelle feature.
- `GrowthChart.svelte`, 2 678 righe: script 20–2521, template 2522–2678, nessuno `<style>`. Lo usano la Dashboard e
  la pagina broker.
- `DataTable.svelte`, 2 431 righe: script 13–960, template 961–1559, `<style>` 1560–2431. 56 importatori.
- Accoppiamenti per percorso:
  - `charts/chartCoreHelpers.test.ts` legge 24 volte `../dashboard/GrowthChart.svelte` e ne reimplementa a mano
    alcune funzioni locali, legate al testo con ancore;
  - gate: `htmlSink` (3 sink di DataTable + «≥10»), `htmlInterpolation:905`, `themeComponentTokens:420`,
    `themeModeReads:500`, registro della privacy `utils/privacy/moneyRenderSites.test.ts` (riga del tooltip di
    GrowthChart);
  - runner: i test di GrowthChart stanno in `_frontend_asset.py` (X: `asset-unit`, `growth-chart-memo`).

## 2. Voci

| Voce | Stato all'analisi | Dove | Lotto |
|---|---|---|---|
| Taglio `GrowthChart` (FE6a) | ✗ | `components/dashboard/GrowthChart.svelte` | Y1 |
| B10 | ✗ | `GrowthChart.svelte:601-608`, `periodBasePnl` mai letto | Y1 |
| Taglio `DataTable` | ✗ | `components/table/DataTable.svelte` | Y2 |
| FE6b, FE2a, FE2b, FE7, FE3 | ✗ | §3 | Y3–Y6 |
| C-38 e difetti 2, 5 del PAC | ✗ / ⚠ | `DataTable.svelte:1621` contro `:2303-2307`, `:1665`; `TargetsStep` | Y7 |
| C-62 | ◐ | `DataTable.svelte:735-743`, `:1582-1587` | Y7 |
| I-01 | ✗ | `charts/timeSeriesAggregation.ts:192` | Y8 |
| I-03 | ◐ | `GrowthChart.svelte:785-789` (solo vista ripristinata), `:2539-2546` | Y8 |
| 47-1 | ✗ | `CandlestickChart:252`, `LineChart:361`, `PriceChartFull:585` | Y8 |
| O-16 | ✗ | `brokers/lots/LotGanttChart.svelte:706-707` | Y8 |
| 48-1 | ✗ | `features/ai-export/AiExportMenu.svelte:299` (file di J) | Y8, con l'ok di J |
| K-15, C-34, C-15 (parte di Y) | ✗ | formatter dei grafici; `CorrelationHeatmap.svelte:330`; `translateOr`, `LABEL_BUNDLE` | Y9 |
| K-13 | ✗ | 15 componenti con `echarts.init` (+2 del PAC) | Y9 |
| 54-1 | ⚠ | `AllocationHistoryChart` 627/630/779, 707, 806; `AllocationPanel:64` | Y10, dopo il developer |
| C-85 | ✗ | nessun componente comune | Y11, se c'è spazio, dopo il developer |
| U8 | ✗ | inventario del 43 (R17, W7, W8, P4, P5, V11; `LotCustodyModal:236`; dichiarazioni) | Y12 a/b; b dopo CP-13 di J |
| FE9, FE10, FE11 | ✗ | — | Y13, per ultimi |

## 3. Confini (D-Y5)

**Nessun barile nuovo**: fra feature si importa dal file che definisce (D-P4 del 43 rinviato a FE9).

**Si spostano** (Y3–Y6):
- `features/dashboard`: `components/dashboard/**` (con i moduli nuovi di Y1), `stores/portfolio/dashboardViewStore.ts`,
  `stores/dateRangeController.svelte.ts`;
- `features/signals`: `lib/charts/**`, `stores/signalCatalogStore.svelte.ts`, la UI dei segnali di `components/charts`
  (`ChartSignalsSection`, `SignalAssetParamControl`, `SignalOptionContent`, `SignalParamControl`, `SignalStyleEditor`,
  `SignalTreeSelect`, `SignalVisualLegend`, `chartSignalsHelpers`; elenco chiuso al lotto);
- `features/risk`: `components/risk/**`, `lib/risk/**`, `stores/risk/**`;
- `features/brokers`: `components/brokers/**` (con `lots/`), `stores/portfolio/lotsAnalysisStore.svelte.ts`;
- `features/files`: `components/files/**`, `utils/files/{filePreview,pdfPreviewState,pdfViewerAssets}.ts`,
  `utils/urlFilters.ts`.

**Restano al loro posto**, con il motivo:
- le primitive di `components/charts` (`LineChart`, `CandlestickChart`, `PriceChartFull`, gli aiuti, l'aggregazione):
  UI generica;
- `components/table/**`: UI generica (il taglio di Y2 non sposta);
- `utils/broker/**`: 35 importatori in tutti i domini (FE9);
- `utils/files/{upload,imageCrop}.ts` e `stores/files/imagePreviewCache.ts`: li usano `DataTable` e `ui/media` (FE9);
- `stores/portfolio/{portfolioStore.svelte,portfolioMutation}.ts`: stato condiviso; l'import di `portfolioMutation` a
  `api/zodios-client.ts:21` è attaccato alla riga del CP6 di H (FE10);
- `stores/dateRangeStore.svelte.ts`, `stores/chartSettingsStore.svelte.ts`: stato globale di più pagine.

## 4. Lotti

Ognuno si chiude con un handoff `FROZEN`; commit e merge li fa il coordinatore.

### Y1 — `GrowthChart` tagliato sul posto (FE6a) [autorizzato; via del 15/10]

Forma (D-Y3): il componente tiene props, stato, `$derived`, effetti, ciclo di vita di ECharts (render, aggiornamento
parziale, opzione completa, zoom, scala delle candele) e template. Escono, in moduli puri accanto:
- `growthChartData.ts` — tipi dei dati aggregati; mappature degli input (gli `$derived` restano nel componente e
  chiamano questi aiuti); secchi della cascata e della scala; metriche (ultimo valore, flussi, OHLC); dati per
  risoluzione e per gradino; conteggi dei secchi; offerta dei gradini; geometria della finestra di zoom;
- `growthChartSeries.ts` — punti delle candele, segno, riferimento del P&L; serie per l'aggiornamento parziale e per
  l'opzione completa (stile invariato);
- `growthChartTooltip.ts` — intestazione del secchio, riga del periodo parziale, HTML del tooltip; il formattatore
  mascherato, la traduzione e lo stato letto all'hover arrivano dal componente come funzioni (le letture restano
  pigre, come oggi).

Passi:
1. Base e corsia (dopo l'avviso di fine finestra): `npm ci` dal lock, `front build --debug`, `mkdocs build`; base di
   `front check`, `front format --check`, `theme-roles.mjs --check`, `check-orphans`, `front-utility core-unit`,
   `front-asset asset-unit growth-chart-memo`.
2. Estrazione del codice, comportamento e opzione di ECharts invariati; B10 (via `periodBasePnl`).
3. `theme-roles.mjs --split lib/components/dashboard/GrowthChart.svelte:<il file e i tre moduli>`, poi `--check`.
4. Test (`test-author`): i legami al sorgente di `chartCoreHelpers.test.ts` sulle funzioni uscite diventano import delle
   funzioni vere (le reimplementazioni spariscono); le ancore sulle funzioni rimaste si riallineano; il contratto i18n
   di GrowthChart legge anche i moduli; il registro della privacy segue le righe del tooltip; test dei moduli nuovi.
   `GrowthChart.test.ts` e `GrowthChart.tooltip.test.ts` fanno da oracolo e non cambiano.
5. Registrazioni: i test nuovi in `_frontend_portfolio.py`; le righe di `_frontend_asset.py` e `_frontend_utility.py`
   solo col via del coordinatore (D-Y6).
6. Validazione: svelte-check 0/0, Prettier, knip invariato, `git diff --check`; `front-utility core-unit
   component-unit`, `front-asset asset-unit growth-chart-memo`, `front-portfolio dashboard dashboard-cache`,
   `front-broker detail`, `front-designer-lab`; galleria filtrata (§0.4).
7. Doc: `developer/frontend/components/charts.md` (i moduli di GrowthChart, `docs-writer`), tabella «Source files» di
   `features/F-055` nella devWiki.

Fatto quando: oracoli invariati e verdi; `--check` pulito con la riga `~split`; galleria identica salvo il rumore noto;
handoff `FROZEN` con il messaggio di commit proposto.

### Y2 — `DataTable` tagliata [autorizzato; annuncio al coordinatore prima di iniziare]

Forma (D-Y2): `DataTableHead`, `DataTableBodyRow`, `DataTableCellContent`, `DataTableFoot`; stato, effetti, gestori
e API pubblica nel padre; `<th>` e `<td>` nei figli di riga, il contenuto nel figlio di cella; il CSS segue il markup;
ogni figlio importa `table.css`. Prima un test d'oro del DOM (`test-author`), poi il taglio, `--split`, i gate per
percorso, il confronto del CSS compilato con gli hash normalizzati, la galleria delle tabelle. C-38 e C-62 dopo (Y7).

### Y3–Y13 — non autorizzati

Y3 FE6b; Y4 FE2a e FE2b; Y5 FE7 (dopo FE8a); Y6 FE3 (dopo FE8a); Y7 C-38 e C-62; Y8 I-01, I-03, 47-1, O-16, 48-1;
Y9 K-15, C-34, C-15, K-13; Y10 54-1; Y11 C-85; Y12 U8 a/b; Y13 FE9–FE11. Dettagli nell'analisi del 15/10 (cartella di
sessione) e nel §2; si scrivono qui quando partono.

## 5. Test e specialisti

- `test-author` per ogni test nuovo o riscritto, su file distinti, con le regole della corsia nel prompt (mai
  `./dev.py` nudo, nessuna installazione, nessun `--force`, nessuna run senza il mio via).
- `docs-writer` per le pagine MkDocs per sviluppatori, in inglese.
- `test-triage` prima di chiamare instabile un rosso.
- Una invocazione alla volta nella corsia 6189.

## 6. Conflitti e rischi (Y1, Y2)

- Y1: i legami al sorgente (24 letture di GrowthChart), l'invariante della cache (`aggregationInputs` letto solo
  dalla memo), la maschera della privacy nel tooltip e la sua reattività; nessun file di altri figli.
- Y2: l'ambito del CSS di Svelte fra figli (`:global`, specificità), colonne sticky, sink `{@html}` spostati, 56
  consumatori, il Designer Lab che legge il token dell'intestazione.
- Baseline del cricchetto: righe `~split`; su un conflitto, `--resolve` e poi `--check`.

## 7. Avanzamento

### Analisi ✅ (2026-10-15, 11:28–12:45)

> **Note implementazione**: analisi in sola lettura consegnata al coordinatore (testo intero nella cartella di
> sessione); decisioni del coordinatore e autorizzazione del developer nel §0.
>
> **Fuori pista**: l'app ha rinominato il ramo all'avvio in `e-alfy-y-cruscotto-e-grafici`; il README della fase lo
> riporta con il prossimo commit di journal del coordinatore.

### Y1 — passo 1, base e corsia ✅ (2026-10-15, 13:01–13:10)

> **Note implementazione**: dopo l'avviso di fine finestra (13:01), sempre con `nice -n 10`: `npm ci` dal lock (exit 0;
> npm 11 non esegue gli script d'installazione, come negli altri worktree), `dev.py front build --debug` (exit 0:
> `api sync`, svelte-check **0 errori e 0 avvisi** con il taglio già applicato, build in `frontend/build/`),
> `dev.py mkdocs build` (exit 0, 3 020 URL relativi risolti).
>
> **Fuori pista**: dalle 13:10 finestra delle dipendenze Python (il developer installa `cryptography`): niente
> `dev.py`, pytest, `api sync`, `mkdocs build` né server fino all'avviso del coordinatore; solo Vitest e svelte-check
> dal `node_modules` della worktree, uno alla volta.

### Y1 — passi 2 e 3, estrazione e taglio dichiarato ✅ (2026-10-15)

> **Note implementazione**:
> - `GrowthChart.svelte` 2 678 → 1 495 righe. Nuovi, accanto: `growthChartData.ts` (666 righe), `growthChartSeries.ts`
>   (487), `growthChartTooltip.ts` (260). Corpi copiati alla lettera; cambiano solo i parametri (ciò che prima veniva
>   dalla chiusura del componente: `dates`, gli input, la vista) e, nel tooltip, `$_('…')` → `t('…')`, con il componente
>   che passa il proprio `$_`.
> - Nel componente restano props, stato, gli `$derived` (che chiamano le funzioni di mappatura), la memo
>   (`getResolutionData` e `getLadderData` → `buildResolutionData` e `buildLadderData`), zoom, ciclo di vita di ECharts,
>   template; più tre adattatori senza logica: `seriesContext()` con `buildChartUpdateSeries`/`buildFullSeries` (stesse
>   firme di prima, quindi i punti di chiamata di `renderChart`, `updateChartData` e `applyFullOption` non cambiano),
>   `tooltipView()` (letto a ogni hover, come prima) e `computeBucketCounts(start, end)`.
> - Le letture pigre restano pigre: il formattatore costruisce la vista a ogni hover (entry sullo schermo, modo,
>   etichette, traduttore, valuta); il tema è quello con cui l'opzione è stata costruita, come prima.
> - **B10**: tolto `periodBasePnl`, mai letto.
> - `theme-roles.mjs --split lib/components/dashboard/GrowthChart.svelte:<il componente e i tre moduli>`: riga `~split`
>   in baseline, record del componente stretto a m1 86 senza letterali (il template non cambia); `--check` pulito («80
>   files dropped below their record»). I moduli nuovi non hanno classi legacy né letterali.
> - Prettier: solo un import riflesso su più righe nel componente.
>
> **Prove leggere** (Vitest dal `node_modules`, `nice -n 10`):
> - oracoli **invariati**: `GrowthChart.test.ts` + `GrowthChart.tooltip.test.ts` → **165/165 verdi**;
> - gate: `htmlInterpolation`, `htmlSink`, `themeModeReads`, `themeRoles`, `themeComponentTokens`, `flagFont`,
>   `clipboardSink`, più `growthLadderAxis`, `growthLadderBuckets`, `timeSeriesAggregation` → verdi;
> - rossi attesi, tutti legami al testo del codice spostato: 12 in `chartCoreHelpers.test.ts` (246 verdi su 258) e 2 nel
>   registro della privacy (`moneyRenderSites.test.ts`, la riga del totale P&L del tooltip Abs ora in
>   `growthChartTooltip.ts`).

### Y1 — passo 4, test ✅ (2026-10-15)

> **Note implementazione** (`test-author`, verificato da me con Vitest un file alla volta, `nice -n 10`):
> - `chartCoreHelpers.test.ts`: le copie delle funzioni private (`toCandlestickPointImpl`, `clipToSignImpl`,
>   `splitBySignImpl`, `findReferenceTotalPnlImpl`, l'allineamento dei flussi, `aggregateFlowMetric`, il ramo Income del
>   tooltip, le sentinelle) sono sparite: i casi di comportamento girano sulle funzioni esportate dai moduli, con gli
>   stessi nomi e le stesse asserzioni. I legami al testo del codice spostato sono diventati prove di comportamento sui
>   moduli (secchi 1:1 nella cascata e nella scala; tre posti fissi della Linea e candela sola; i sei posti di Income
>   con etichette, stack e colori nei due temi; somme dei flussi per secchio; righe del tooltip Income). Restano legami
>   al sorgente solo sul codice rimasto nel componente (il lettore della finestra, ancorato ora a `lastLadderPlanKey`;
>   il cablaggio dei sei allineamenti). Il contratto i18n legge anche le chiamate `t('…')` dei tre moduli, con un
>   controllo positivo. **258 → 265 test, tutti verdi**; nessuna asserzione di comportamento persa.
> - `moneyRenderSites.test.ts`: la voce del totale P&L del tooltip Abs passa a `growthChartTooltip.ts`, `masked`;
>   6/6 verdi.
> - Oracoli invariati: `GrowthChart.test.ts` 159, `GrowthChart.tooltip.test.ts` 6; `themeRoles.gate` 36/36.
> - Ogni export nuovo ha un lettore (componente, modulo fratello o test), come vuole knip con
>   `ignoreExportsUsedInFile`. Nessun file di test nuovo, quindi nessuna registrazione nel runner.
>
> **Fuori pista**: dalle 13:36 il coordinatore stringe il carico: nella mia corsia solo test di un file alla volta;
> svelte-check, build, `mkdocs build`, E2E e galleria si chiedono prima. Due reperti di `test-author`, preesistenti,
> nel backlog di Y: Y-2 (cascata settimanale e linea di broker che finisce a metà settimana) e Y-3 (`t(` non è una
> chiamata di traduzione per il gate della privacy).

### Y1 — passi 6 e 7, validazione e documentazione ⏳

> **Note implementazione** (via del coordinatore alle ~14:05 per i punti 1–3, `nice -n 15`, in fila):
> - `npm run check` (svelte-kit sync + svelte-check, test compresi): **0 errori e 0 avvisi**;
> - `dev.py lint --dead-code --scope frontend` (knip): exit 1 sui reperti di sempre (2 file, 19 export, 28 tipi, 4 e 20
>   dipendenze), **nessuno** in un file di questo lotto né causato da esso;
> - doc: `docs-writer` in `developer/frontend/components/charts.md` (pagina solo inglese, senza traduzioni): tabella
>   «Where GrowthChart's code lives» (componente e tre moduli) con la regola di `AggregationInputs`; lo snippet di
>   `needsFullInit` riallineato al codice (`lastRenderedSeriesKey !== seriesKey`, assente dal piano 47) con la sua riga
>   nella tabella dei trigger;
> - `dev.py mkdocs build` (stretto): exit 0, 3 020 URL relativi risolti; `dev.py mkdocs check-links`: 95 link validi;
> - devWiki: tabelle «Source files» di `features/F-055`, `concepts/chart-resolution-semantic-zoom`,
>   `decisions/portfolio-pnl-series-contracts`; `check_source_paths.py`: 5 percorsi mancanti, gli stessi di prima.
>
> **Aspettano uno slot del coordinatore**: la galleria filtrata `Dashboard|Brokers` contro `g-final3-r1`.
>
> **E2E** (slot pesante 1 del coordinatore, 14:11; `--workers 2`, `nice -n 10`, corsia 6189, in fila), tutte verdi:
> `front-portfolio dashboard` 27 (2,4 min), `front-portfolio dashboard-cache` 6 (27 s), `front-broker detail` 37
> (1,4 min), `front-designer-lab live` 7 (14,5 s; legge i colori dell'opzione di ECharts di `growth-chart`). Il runner
> ha giudicato aggiornata la build delle 13:05, che contiene il taglio; dopo, solo un import riflesso da Prettier e i
> test. Porta 6189 libera dopo le run.

### Y1 — checkpoint 🧊 FROZEN (2026-10-15, 14:40)

> **Note implementazione**: handoff al coordinatore con due commit proposti:
> `refactor(dashboard): cut GrowthChart into modules` (codice, test, baseline del cricchetto, doc per sviluppatori,
> devWiki) e `docs(journal): Y plan and Y1 checkpoint` (questo piano, sezione Y del backlog con Y-1, Y-2, Y-3).
> Nessuna voce rivolta all'utente: niente CHANGELOG.
>
> **Conflitto previsto**: `frontend/src/themeRoles.baseline.tsv`. Le righe dei file non si toccano, ma `dev_release2`
> (`~split` di X FE5b) e Y1 (`~split` di GrowthChart) aggiungono tutti e due una riga in coda: si risolve con
> `node frontend/scripts/theme/theme-roles.mjs --resolve` (la riga aggiunta da ogni lato resta), poi `--check`.
>
> **Non eseguiti**: le azioni intere `front-utility core-unit`/`component-unit` e `front-asset asset-unit`, di cui ho
> girato uno per uno i file toccati; la galleria filtrata, cancello d'ingresso dopo il commit.
