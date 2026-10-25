# Piano — fase 01, 09: Y · Cruscotto e grafici (1.3.0)

> **Stato al 19/10 sera** (HEAD `15603fe69`): tutti i lotti di Y sono entrati in `dev_release2` tranne **Y4a** (fermo:
> il coordinatore ha portato al developer «non nella 1.3, oppure una finestra notturna», 16/10 20:21) e **Y13**
> (parcheggiato fino alla risposta del developer a Y13-1). L'ultimo ingresso è Y-N65 (merge `5cb47395f`, CHANGELOG
> `b1e7a2dd5`, 19/10). Lotto per lotto, con i commit: §4, «Stato dei lotti». La ripresa dopo la pausa generale del
> 19/10 sera (la corsia da ripopolare, le note in coda) è nella sezione «19/10 sera · Pausa generale»; il prossimo
> lavoro, Z-29d, nella sezione «20/10 · Z-29d», in fondo. Dal 19/10 valgono le
> regole nuove del coordinatore: nessuna decisione di prodotto da Y (ogni scelta diventa una domanda, con le opzioni e
> un consiglio), si implementa solo col suo via esplicito, carichi pesanti solo in uno slot.
>
> - **Workstream Y** · worktree `LibreFolio-worktrees/e-alfy-redesigned-spork` · ramo `e-alfy-y-cruscotto-e-grafici`
>   (rinominato dall'app all'avvio; prima `e-alfy-redesigned-spork`).
> - **Base di partenza**: `1e9e567f79488cfb5630f3c05e1bd2727bf856d7` (avanzamento veloce del coordinatore dal `23f6578f3`
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

**Seconda autorizzazione (15/10, 18:36)**: parole del developer, alla lettera, inoltrate dal coordinatore, in risposta
alla domanda sui lotti Y: «Sì, e d'ora in poi decidi tu l'avvio dei lotti di Y». Da allora l'avvio dei lotti lo decide
il coordinatore.
- **Ordine**:
  1. Y8: I-01, I-03, 47-1, O-16; 48-1 solo con l'ok di J, chiesto direttamente;
  2. Y7: C-38 e C-62, cioè le tabelle sul telefono (decisione 50). Tocca `DataTable`, che è nell'ondata W6: va
     annunciato al coordinatore prima del codice;
  3. Y3 e Y4b, dopo l'ingresso di DV;
  4. Y4a, dopo FE4 e FE5a di X;
  5. Y9, Y10 (decisione 49) e Y11 (decisione 48), dopo DV.
- **Regole**: prima i rossi; un checkpoint FROZEN per lotto; le prove pesanti e la galleria si chiedono al coordinatore.

### 0.3 Decisioni del coordinatore sulle proposte dell'analisi (15/10)

| # | Decisione |
|---|---|
| D-Y1 | Prima `GrowthChart` (Y1), poi `DataTable` (Y2) |
| D-Y2 | `DataTable` tagliata come FE8a: figli di template con props esplicite; stato, effetti, gestori e API pubblica restano nel padre; il CSS segue il markup; ogni figlio importa `table.css`. **Proposta del 15/10, approvata dal coordinatore (15/10, ~15:25)**: due figli invece di quattro (`DataTableColumnHeader`, `DataTableCellContent`), con struttura, CSS strutturale e gestori nel padre; motivi e forma in §4, Y2 |
| D-Y3 | `GrowthChart` tagliato sul posto in tre moduli puri (`growthChartData.ts`, `growthChartSeries.ts`, `growthChartTooltip.ts`); nel componente restano stato, effetti, ciclo di vita di ECharts e template; poi lo spostamento (FE6b). **B10 entra in Y1** |
| D-Y4 | FE6b subito dopo i tagli; FE7 e FE3 dopo l'ingresso di FE8a di W; FE2 dopo FE4 e FE5a di X e prima di FE5c (lo concorda il coordinatore con X) |
| D-Y5 | Niente barili nuovi; le cose che restano al loro posto si elencano qui (§3) |
| D-Y6 | Per ogni lotto, via del coordinatore con le righe esatte dei file del runner degli altri (`_frontend_utility.py`, `_frontend_asset.py`, `_frontend_ai_export.py`) |
| D-Y7 | `npm ci` dal lock, `front build --debug`, `mkdocs build` solo dopo l'avviso di fine della finestra della galleria (verso le 13:00) |
| D-Y8 | Le gallerie filtrate le mette in calendario il coordinatore con il coordinatore colori, al checkpoint |
| D-Y9 | 48-1 con l'ok di J, più avanti; i due `title` di C-15 vanno a W |
| — | K-12, K-14 e I-02 restano fuori |
| — | C-85, 54-1 e difetto 5 del PAC: al developer, nel file delle decisioni (lotti dopo Y2) |
| D-Y13 | (15/10, 18:19, analisi di Y3 e Y4) Feature a radice piatta:<br>• dashboard e rischio piatte, il rischio tiene `levels/`;<br>• dei segnali, `lib/charts/signals` sale alla radice e la UI va in `components/`;<br>• l'`index.ts` dei segnali, che esiste già, diventa il file pubblico `$lib/features/signals`;<br>• nessun barile nuovo |
| D-Y14 | `ChartSettingsModal` e `MeasurePanel` vanno in `features/signals`: sono UI dei segnali usata solo dalle pagine. Costo: l'eccezione di `theme-roles.mjs:72`, cioè del programma colori |
| D-Y15 | Resta un'inversione: le primitive di `components/charts` e `chartSettingsStore` importano dai segnali (`type RenderedSignal`, `signalLabelToHtml` e due aiuti dello schema). Va accettata fino a FE9 (backlog Y-7) |
| D-Y16 | `chartCoreHelpers.test.ts` cambia solo i percorsi |
| — | Ordine proposto dal coordinatore al developer, in attesa del suo via:<br>• Y3 dopo l'ingresso di DV (DV ha già cambiato `AllocationHistoryChart` e `AllocationPieChart`);<br>• Y4b dopo DV;<br>• Y4a dopo FE4 e FE5a di X;<br>• intanto Y8 (I-01, I-03, 47-1, O-16; 48-1 con l'ok di J) e Y7 (C-38, C-62).<br>Le dichiarazioni ai colori (scanner del Lab, `theme-roles.mjs:72`, tabella vecchio → nuovo) vanno al coordinatore al checkpoint di ogni lotto |
| D-Y17 | (15/10, 20:52, Y7, C-38) Sotto i 768 px la colonna di selezione e quella delle azioni scorrono con la tabella, intestazione e corpo insieme; l'intestazione resta fissa in alto. Rientra nella decisione 50 («la cura generale»): il coordinatore la riferisce al developer nel riepilogo, e se lui vuole il contrario si cambia |
| D-Y18 | (15/10, 20:52, Y7, C-62) Prima un rosso E2E su una tabella `layout-auto`. Se il rosso c'è: la larghezza trascinata diventa anche il `min-width` del `th`, e le maniglie passano ai Pointer Events. Se non c'è: C-62 si chiude con il test come guardia. In entrambi i casi la causa sbagliata della wiki si corregge. Il layout del PAC da telefono resta fuori da Y7 |
| — | Y7 parte dopo le E2E di Y8, che costruiscono il frontend da questo worktree, e dopo l'ok dei colori su `DataTable` (ondata W6), chiesto dal coordinatore. La galleria mobile d'ingresso l'ha chiesta il coordinatore ai colori, probabilmente dopo G-13 |

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
   /tmp/librefolio-r13-y -- -f "Dashboard|Brokers" --workers 6`.
   - **Il riferimento, dal 19/10, è il trio del 18/10**: `g-r3-prima-ba8e06763-full`, `g-r3-dopo-cd686f445-full` e
     `g-r3-dopo2-cd686f445-full`. Le maschere e la stabilità di `g-final3__r1__vs__r2`, citate qui fino al 19/10,
     sono state cancellate per liberare il disco.
   - Il confronto: `--common-only --ignore-masks $W/diffs/g-r3-dopo-cd686f445__vs__g-r3-dopo2-cd686f445/masks
     --stability $W/diffs/g-r3-dopo-cd686f445__vs__g-r3-dopo2-cd686f445/stability.json`.
   - Un diff di pixel vuole un riferimento preso lo stesso giorno del candidato; il trio serve all'occhio.
   - Rumore noto, classi e scatti instabili: `scripts/visual_review/README.md`, sezione «Known gallery behaviour
     (18/10/2026, the reference trio)», in `dev_release2` da `ccc2a4141` (19/10).
   - Le altre citazioni di `g-final3` in questo piano sono la cronaca di quei giorni, e restano.
   > **Nota 20/10**: righe aggiornate su richiesta del programma colori (19/10, via il coordinatore). Sezione del README
   > letta da `ccc2a4141` con `git show`; uguale in `dev_release2` `a820bd4dd`.

Per Y2: annuncio al coordinatore quando ci arrivo. Il lotto C di R ha portato `DataTable` sui token `--lf-cmp-*`, e la
E2E del Lab legge il token della sua intestazione.

### 0.5 Decisioni del developer 48–50 (15/10, 18:2x–18:34, inoltrate dal coordinatore)

- **48 · C-85 (Y11): niente badge e niente dati attenuati.**
  - Quando una pagina aspetta il server (il cambio del periodo o un altro ricaricamento), il pulsante «Aggiorna» della
    barra in cima diventa grigio e la sua icona gira, come se fosse stato premuto.
  - Alla lettera: «la regola facciamo che è sempre far girare l'aggiorna nella top bar, che per altro dovrebbe essere
    l'unico in pagina».
  - Un pezzo che si ricarica da solo fa girare il pulsante della barra, non uno suo.
  - I pulsanti «Aggiorna» dentro i pannelli (per esempio `RiskPanelHeader`) si verificano uno per uno: si propone di
    toglierli, o si dice perché restano.
  - Il PAC («Calcola») e il wizard d'import tengono i loro indicatori.
  - Va armonizzato con «Aggiornamento in pausa» di Z1, che è un'etichetta e non il pulsante.
- **49 · 54-1 (Y10): approvata la proposta di Y.**
  - La liquidità negativa si disegna sotto lo zero, e l'asse va oltre il 100 % quando serve.
  - Il tooltip mostra la riga negativa.
  - Nella torta restano le quote positive, con la nota «liquidità negativa: −X».
  - Il backend non tocca il totale.
- **50 · Difetto 5 del PAC (Y7): prima la cura generale delle tabelle sul telefono (C-38).** Il layout del PAC da
  telefono si decide dopo, se serve, insieme ad altre note del developer.

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
| Y-6 (dal coordinatore, DV, 15/10) | ✗ | `dashboard/AllocationPanel.svelte:65` (`toAllocEntries`) e il tipo `AllocEntry` (`:23`): `emoji` passato alla torta, che dopo DV non lo legge più. È un dato morto | Y10, dopo DV |
| C-85 | ✗ | nessun componente comune | Y11, se c'è spazio, dopo il developer |
| U8 | ✗ | inventario del 43 (R17, W7, W8, P4, P5, V11; `LotCustodyModal:236`; dichiarazioni) | Y12 a/b; b dopo CP-13 di J |
| FE9, FE10, FE11 | ✗ | — | Y13, per ultimi |
| Y-4 (G-12, dal coordinatore, 15/10) | ✗ | `charts/SignalTreeSelect.test.ts:16-17` e `:306-310`: i commenti descrivono `selectIndicatorFromTree` della galleria che espande la famiglia con un clic e clicca l'opzione; da G-9 (`1470bd693`) la galleria sceglie l'indicatore da tastiera. Solo testo | Y4 (FE2), passando dal file |

Questa tabella è lo stato **all'analisi** del 15/10. Lo stato di oggi di ogni lotto, con il commit d'ingresso: §4, «Stato
dei lotti».

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

### Y1 — `GrowthChart` tagliato sul posto (FE6a) [autorizzato, via del 15/10; entrato in `dev_release2` il 15/10, `badec1465`]

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

### Y2 — `DataTable` tagliata sul posto [autorizzato; forma approvata e taglio annunciato il 15/10; entrato in `dev_release2` il 15/10, `c747a74c3`]

**Stato verificato a `cf8101f29`** (il file non è cambiato dalla base `1e9e567f7`):
- `components/table/DataTable.svelte`, 2 431 righe: script 13–960, template 961–1559, `<style>` 1560–2431. Lo stile
  ha 154 regole e 155 letture `var(--lf-cmp-*)`, e nessun letterale: R (lotto C) li ha portati in `table.css`.
- Cricchetto: m1 4, le classi dell'interruttore `editable-checkbox` (righe 1387 e 1393: `bg-emerald-500`,
  `bg-gray-300`, `dark:bg-slate-600`, `bg-white`). I letterali del record sono già caduti (R5).
- 56 importatori. L'API pubblica (props, metodi esportati, `data-testid`) non cambia.

**Forma: deviazione proposta da D-Y2.** D-Y2 prevede quattro figli (Head, BodyRow, CellContent, Foot), con `<th>` e
`<td>` nei figli di riga. Propongo due figli, con `table`, `thead`, `tbody`, `tfoot`, `tr`, `th` e `td` che restano nel
padre. I motivi:
1. **Una E2E del programma colori.** `designer-lab-picker.spec.ts:216` pretende che la regola `th` che colora
   l'intestazione stia in `lib/components/table/DataTable.svelte`. Con `th` in `DataTableHead` diventerebbe rossa.
2. **CSS strutturale fermo.** Restano dove sono il sticky (`th-fixed`, `td-fixed`), lo z-index, gli stati di riga
   (`selected`, `highlighted`, `row-*`), `:hover`, `:focus-within` e il mobile `.td-actions`.
   - Con D-Y2 andrebbero in due copie `td`, `.td-fixed`, `.td-select`, `.td-actions`, `.checkbox-btn` e `.check-box`.
   - L'ordine delle regole andrebbe ricostruito fra chunk CSS di componenti diversi.
   - `OtherPeriodEffectsTable.svelte:262-321` stila da fuori proprio `.datatable th`, `td` e `tbody tr`: con questa
     forma il suo rapporto con il chunk di DataTable non cambia.
3. **Gestori di riga fermi.** Click, doppio click, auxclick, menu contestuale e tocco lungo non diventano 25 callback
   di un figlio di riga: il comportamento più delicato dei 56 consumatori resta com'è.
4. **Il guadagno resta.**
   - Il template scende da ~600 a ~260 righe, lo stile da 154 a 100 regole.
   - I due blocchi più grossi e autonomi diventano componenti: lo switch delle 13 celle (39 regole) e l'intestazione
     di colonna con filtro e popover (20 regole).
   - Il piede riusa lo switch, quindi spariscono 4 sink `{@html}` duplicati.

**I pezzi**:
- **`DataTableColumnHeader.svelte`** (nuovo, `generics="T"`): il contenuto di `th.th-data`, cioè `div.header-content`
  (righe 1020–1136). Comprende:
  - il bottone d'ordinamento, con e senza Tooltip;
  - l'HTML d'intestazione;
  - l'icona del tooltip, come link o come gesto;
  - il bottone del filtro e la maniglia di ridimensionamento;
  - il popover `DataTableColumnFilter` con i suoi `{@const}`, parola per parola (le opzioni del filtro dipendono da
    `data` e da `boundaryData`: devWiki `datatable-filter-options-disappear`).

  Script:
  - i quattro risolutori puri `getColumnLabel`, `getColumnHeaderHtml`, `getColumnTooltip` e `getColumnTooltipUrl`
    (435–452) e `EMPTY_CURRENCY_MIN_MAX` (433), usati solo qui;
  - un ref locale del bottone del filtro, al posto di `filterBtnRefs` (308), che serviva solo a `bind:this` e ad
    `anchorElement`.

  Props esplicite, con i nomi del padre, così il template si sposta parola per parola:
  - valori: `column`, `sortDir`, `hasFilter`, `enableSorting`, `enableColumnFilters`, `enableColumnResize`,
    `resizing`, `columnFilters`, `data`, `boundaryData`;
  - stato condiviso: `openFilterColumnId` come `$bindable`, perché lo stato resta del padre;
  - gestori: `toggleSort`, `applyColumnFilter`, `startResize` e i cinque gestori del tooltip
    (`handleHeaderTooltip*`, `cancelHeaderTooltipLongPress`). Il timer della pressione lunga resta un `let` del padre,
    chiuso da `onDestroy` (789); la regola della devWiki `svelte5-teardown-reads-stale-state-timers` è rispettata.

  CSS: le 20 regole delle righe 1681–1808.
  - `th:hover .resize-handle` diventa `:global(th:hover) .resize-handle`, e lo stesso per la variante `.dark`.
  - Le 5 regole `.filter-btn` sono copiate: il padre le tiene per il «mostra solo selezionati» di `th-select`.
  - Importa `table.css`, come chiede la regola (b) del gate dei token.
- **`DataTableCellContent.svelte`** (nuovo): lo switch di `td.td-data` (righe 1257–1433) con i suoi 13 tipi di cella.
  - Script: `handleImageError` (496–500) e gli import usati solo qui (`formatCellDate`, `formatBytes`,
    `normalizeDecimalInput`, `decimalArrowStep`, `SimpleSelect`, `ExternalLink`, `ImageIcon`).
  - Una sola prop, `cellContent: CellContent`. Il nome non cambia, quindi il sink resta `cellContent.html`.
  - CSS: le 39 regole `.cell-*` (2003–2056, 2140–2259, 2310–2379, con i loro commenti), nell'ordine originale.
    Importa `table.css`.
  - **Riuso nel piede** (switch 1479–1513): `FooterCellContent = SimpleCellContent | HtmlCell` è un sottoinsieme di
    `CellContent`. Il ramo HTML è identico a quello della cella, salvo `data-testid={cellContent.testId}`, che nessun
    piede imposta oggi. I piedi in produzione sono tre: `AssetTable` del PAC, `DistributionDialog` e
    `UnifiedLotsTable`; due passano la prop in forma breve, `{footerCells}`.
- **`DataTable.svelte`** tiene:
  - lo script: stato, effetti, gestori, API pubblica;
  - `table`, `thead`, `tbody` e `tfoot`;
  - `tr`, `th` e `td`, con attributi, classi, stili e `data-testid`;
  - le colonne di selezione e di azione, il caricamento, il vuoto, la paginazione, il menu contestuale e le modali;
  - 100 regole CSS, cioè le 5 `.filter-btn` del «seleziona tutto» più le 95 strutturali. Le due
    `:has(.cell-editable-select-wrapper)` (1960, 1965) diventano
    `:has(:global(.cell-editable-select-wrapper))`.
- **Niente barili**: `table/index.ts` non esporta i due figli, che sono interni (D-Y5).
- **Cricchetto**: `--split lib/components/table/DataTable.svelte:lib/components/table/DataTable.svelte,lib/components/table/DataTableColumnHeader.svelte,lib/components/table/DataTableCellContent.svelte`,
  poi `--check`.
  - Le 4 classi dell'interruttore passano a `DataTableCellContent` con il record ereditato dal taglio dichiarato
    (R3, `declareSplit`): il totale resta 4, non nasce nessuna classe nuova e nessun letterale.
  - La loro conversione resta a T (W6). Lo dico al coordinatore colori, perché la regola del 14/10 vuole solo ruoli
    nei file nuovi.
- **`table.css` non si tocca.** Il commento di sezione `/* DataTable.svelte */` nomina la famiglia, e il gate dei
  token toglie i commenti prima di leggere.

**Specificità.** In Svelte 5 ogni selettore ha una sola classe di hash a peso pieno; i composti scoped successivi
pesano zero (`:where`).
- Spostare una regola in un figlio sposta l'hash su un altro composto, e la specificità resta uguale.
- `:global()` sul composto che resta fuori dal figlio la conserva: `th:hover .resize-handle` pesa (0,3,1) prima e dopo.
- Dentro `:has()` l'argomento pesa (0,1,0) con o senza `:global`.

Tutto questo va provato sul CSS compilato, non dedotto. Nessun elemento riceve regole da due componenti:
- gli `.header-*` e i `.cell-*` colpiscono solo elementi dei figli;
- il padre colpisce solo la struttura e le colonne di selezione e di azione.

Passi:
0. **Via**: annuncio al coordinatore colori, fatto dal coordinatore.
   - Righe del runner degli altri (D-Y6): nessuna. I test toccati restano registrati dove sono, in
     `_frontend_utility.py:233-235` e `:297`, e l'impalcatura d'oro non si registra.
1. **Oracoli prima del taglio.**
   - **Impalcatura d'oro del DOM** (`test-author`), temporanea: il frontend non usa snapshot, quindi non va nel commit.
     È `components/table/DataTable.golden.test.ts`: monta `DataTable` con una fixture che copre:
     - i 13 tipi di cella;
     - il piede: stringa, numero, HTML con e senza tooltip e click;
     - le intestazioni: HTML, tooltip di testo, link e gesto, ordinabili e no, filtrabili, ridimensionabili, fissate a
       sinistra e a destra, allineate;
     - la selezione multipla, le azioni, il caricamento, il vuoto e il popover del filtro aperto.

     Serializza il DOM normalizzato, senza le classi `svelte-*` e senza i commenti. Con `LF_GOLDEN=record` lo scrive in
     `/tmp/librefolio-r13-y/`, altrimenti lo confronta. Si registra sul codice di oggi.
   - **Confronto del CSS compilato**: uno script nella cartella di sessione che usa `svelte/compiler` del
     `node_modules` locale. Normalizza gli hash e confronta regola per regola: selettore, dichiarazioni e specificità.
2. **Taglio.** I due figli si creano spostando i blocchi parola per parola, e il padre li usa. Poi `:global` sulle
   quattro regole di confine e Prettier.
3. **`--split`**, poi `--check`.
4. **Prove leggere**, un file alla volta.
   - Impalcatura d'oro in confronto: deve essere identica.
   - CSS: stesse regole e stessa specificità. Le sole differenze attese sono le 5 `.filter-btn` in due copie e i
     quattro selettori di confine.
   - Vitest: `DataTable`, `DataTable.rowOrder`, `DataTableHeaderTooltip`, `DataTableColumnFilter`,
     `DataTablePagination`, `dataTableLogic` e `ReportSetCard`.
   - Gate: `htmlInterpolation`, `themeComponentTokens`, `themeRoles.gate` e `moneyRenderSites`.
5. **Test** (`test-author`).
   - `htmlSink.gate.test.ts:63-65`: i sink passano ai figli (`cellContent.html` in `DataTableCellContent`,
     `getColumnHeaderHtml(column)` in `DataTableColumnHeader`). La voce `footerContent.html` esce, perché il codice
     non c'è più.
   - Il controllo positivo `:214` («≥ 10 in DataTable») si riscrive sui due figli.
   - Il commento di `DataTable.test.ts:355` cita la riga 713, che si sposta.
   - L'impalcatura d'oro si toglie.
6. **Validazione.**
   - Con il via: svelte-check 0/0 e knip invariato.
   - Sempre: Prettier e `git diff --check`.
   - E2E con lo slot (vedi sotto).
   - Galleria filtrata con lo slot del programma colori.
7. **Doc.**
   - `developer/frontend/components/core-ui/data-table.md`: «Where DataTable's code lives», a cura di `docs-writer`.
   - devWiki: le tabelle «Source files» di `datatable-filter-options-disappear`, `datatable-column-resize-noop` e
     `datatable-tooltip-custom-cell`.
   - `check_source_paths.py`.

E2E (`--workers 2`, una alla volta, con lo slot):

| Categoria | Azioni | Cosa esercita |
|---|---|---|
| `front-designer-lab` | `picker`, `live` | la regola `th` in `DataTable.svelte`, il token d'intestazione |
| `front-transaction` | `transactions-table`, `tx-bulk-diagnostics`, `transactions-modals`, `tx-import-upload` | filtro, ordinamento, «mostra solo selezionati», tooltip d'intestazione, badge |
| `front-portfolio` | `risk-lab`, `privacy-masking` | tooltip a gesto, seleziona tutto, piede |
| `front-utility` | `files-uploader`, `pac-allocator-real` | filtro, piede |
| `front-asset` | `asset-browse`, `asset-list` | ordinamento, seleziona tutto |
| `front-fx` | `fx-bulk` | seleziona tutto |

Galleria, con lo slot del programma colori: `-f "Dashboard|Tools|Files|Transactions|Brokers|Import report sets|FX|Assets|Risk Analysis"`.
Sono i 10 gruppi su 16 che contengono tabelle. Il confronto si fa con l'ultimo riferimento completo, con le opzioni
del Y1. Note del programma colori (15/10): `--workers 6` finché non entra C-94; contro `g-final3-r1`, più vecchio di
G-10 (`b4533a949`), cambiano per conto loro `media/asset-picker-modal`, `files/static-tab` e `files/static-grid`
(ordine degli avatar), da segnalare come «G-10». Quando entra T, G rifà il riferimento per tutti.

Fatto quando:
- l'impalcatura d'oro è identica;
- il CSS compilato è equivalente regola per regola;
- `--check` è pulito, con la riga `~split`;
- Vitest, gate ed E2E sono verdi;
- la galleria è identica salvo il rumore noto;
- documentazione e devWiki sono allineate;
- l'handoff FROZEN è consegnato.

C-38 e C-62 dopo, in Y7, su `th-actions` e `resize-handle`, che restano facili da trovare.

### Y8 — correzioni dei grafici [autorizzato, 15/10 18:36; entrato in `dev_release2` il 15/10, `160562b56`]

Ogni voce è verificata a `e424e8740`.

| Voce | Stato verificato | Correzione | Test rosso (file già registrato) |
|---|---|---|---|
| I-01 | `aggregateSumSeries` (`charts/timeSeriesAggregation.ts:192-209`) somma anche i punti `missing` e copia `missing` dall'ultimo punto: un ultimo giorno mancante nasconde la somma degli altri. È latente: l'unico chiamante, `growthChartData.aggregateFlowMetric`, non imposta `missing` | sommare solo i punti presenti; il secchio è `missing` solo se lo sono tutti | `charts/__tests__/timeSeriesAggregation.test.ts` |
| I-03 | il ripiego da `%` ad Abs è un controllo una tantum sulla vista ripristinata (`GrowthChart.svelte:129-139`, `:566-570`). Passando a un periodo o a un broker senza dati in `%`, il pulsante resta premuto e disabilitato (`:1356-1361`) | un `$effect` a ogni caricamento completato: ripiego ad Abs e ritorno al `%` quando i dati tornano, salvo una scelta esplicita di un altro modo nel frattempo | `dashboard/GrowthChart.test.ts` |
| 47-1 | in compatto l'`interval` delle categorie si calcola su tutti i punti (`charts/responsiveXAxis.ts:273`), e i gestori di `dataZoom` (`CandlestickChart:252`, `LineChart:361`, `PriceChartFull:585`) non lo ricalcolano | `buildResponsiveXAxisPolicy` accetta `visibleCount`; a zoom fermo i tre grafici riapplicano l'`axisLabel` della finestra visibile, letta dall'evento e non con `getOption` a ogni passo | `charts/chartCoreHelpers.test.ts`, sezione `responsiveXAxis` |
| O-16 | `LotGanttChart.svelte:706-707` concatena la quantità con «shares» o «shares open out of» | chiavi ICU `brokers.lots.tooltip.quantityClosed` e `quantityOpen` nelle 4 lingue, al posto di `shares` e `sharesOpenOutOf`; la riga viene da un aiuto puro in `lotGanttChartHelpers.ts`. Con la privacy accesa la forma è sempre `other`, così non rivela una quantità uguale a 1 | `brokers/lots/lotGanttChartHelpers.test.ts` |
| 48-1 | il pulsante di `AiExportMenu.svelte:299` ha `gap-2 px-3`; i vicini dei dettagli asset, broker e FX hanno `gap-1.5 px-2.5`. Sulla Dashboard il vicino (`sync-button`, `+page.svelte:965`) ha `gap-2 px-3` | il pulsante del menu e il `sync-button` della Dashboard passano a `gap-1.5 px-2.5`. Ok di J (15/10, ~18:45): «make it yourself in Y8», solo quella riga | — (cosmetico; si vede nella galleria) |

Passi:
1. Rossi, a cura di `test-author`: file distinti, solo Vitest su file singolo.
2. Correzioni, nell'ordine I-01, I-03, O-16 (chiavi con la skill `devpy-i18n`), 47-1, 48-1.
3. Prove leggere:
   - i rossi diventano verdi;
   - gate: `moneyRenderSites`, `htmlInterpolation`, `themeRoles.gate`, audit i18n;
   - svelte-check, knip, `theme-roles --check`.
4. Con lo slot del coordinatore:
   - E2E della Dashboard, del dettaglio broker (Gantt) e del dettaglio asset (assi sotto zoom);
   - galleria filtrata su Dashboard, Brokers, Assets e FX, perché 48-1 cambia le barre.
5. Documentazione, se cambia un contratto: l'asse sotto zoom in `charts.md`; tabelle della devWiki.
6. Checkpoint FROZEN.

### Y7 — tabelle sul telefono e ridimensionamento [via del coordinatore e dei colori, 15/10 20:52–21:22; entrato in `dev_release2` il 16/10, `a613a217c`]

Base: `f98c20f1b` (`dev_release2` dopo l'ingresso di Y8). Decisioni D-Y17 e D-Y18 in §0.3. Verificato sul codice dopo
il taglio di Y2.

| Voce | Stato verificato | Correzione | Prova |
|---|---|---|---|
| C-38, difetto 2 del PAC | sotto i 768 px la regola mobile (`table/DataTable.svelte:1693-1699`) sblocca le celle `.td-actions`, ma non l'intestazione: `thead.sticky-header th` (0,1,2, `:1280-1285`) batte `.th-actions` (0,1,0). «Azioni» resta fissata a destra (`:1324-1326`), mentre i ⋮ scorrono via | D-Y17: sotto i 768 px l'intestazione delle azioni scorre con la colonna, con un selettore abbastanza specifico, e resta fissa in alto | E2E da telefono: dopo uno scorrimento orizzontale, l'intestazione «Azioni» e i ⋮ hanno la stessa x |
| D-Y17, selezione | la colonna di selezione (`.th-select`, `.td-select`, `left: 0`, `:1314`, `:1548`) resta fissata a sinistra a ogni larghezza, e copre l'inizio della prima colonna di dati (difetto 5: «APL Apple Inc.») | sotto i 768 px scorre anche lei, intestazione e corpo insieme | la stessa E2E: dopo lo scorrimento la selezione non copre la prima colonna |
| C-62 | la larghezza trascinata va solo nello `width` inline del `th` (`:983`). Con `tableLayout="auto"`, 11 tabelle, è un suggerimento. Le maniglie (`DataTableColumnHeader.svelte:175`, gestori in `DataTable.svelte:688-719`) ascoltano solo il mouse | D-Y18: se il rosso c'è, la larghezza trascinata diventa anche il `min-width` del `th`, e le maniglie passano ai Pointer Events con la cattura del puntatore. Se non c'è, C-62 si chiude con il test come guardia. La cura comprende anche (coordinatore, 22:10) `touch-action: none` sulla maniglia e la larghezza **disegnata** come punto di partenza del trascinamento, al posto di quella configurata | E2E su desktop: un trascinamento su una tabella `layout-auto` cambia la larghezza della colonna del suo delta |
| Wiki | `problems/datatable-column-resize-noop` dà come prima causa «`onColumnResize` non letto dal genitore»: è sbagliata, perché la larghezza vive dentro la tabella | si corregge con l'esito del rosso | — |

Fuori: il layout del PAC da telefono (le larghezze di `TargetsStep`), per la decisione 50.

Vincoli:
- **colori**: `theme-roles --check` pulito nell'handoff, e la riga `~split` di `DataTable` non cambia (condizione del
  coordinatore dei colori, 20:53). Nessun colore nuovo; `app.css` non si tocca;
- **runner**: la registrazione di una spec nuova in un file del runner di altri chiede il via del coordinatore con le
  righe esatte (D-Y6);
- **prove pesanti**: le E2E di Y7 si chiedono al coordinatore, con lo slot.

Passi:
1. Rossi, a cura di `test-author`: E2E da telefono (C-38 e la selezione) ed E2E di trascinamento su una tabella auto
   (C-62). Si scrivono senza lanciarli; poi chiedo lo slot e li lancio sul codice di oggi, per vederli rossi.
2. Correzioni in `DataTable.svelte` (la regola mobile; i gestori del ridimensionamento) e in
   `DataTableColumnHeader.svelte` (la maniglia), solo se il rosso di C-62 c'è.
3. Prove leggere: Vitest della tabella, i gate (`htmlSink`, `themeRoles`, `themeComponentTokens`), svelte-check,
   `theme-roles --check`, Prettier.
4. Con lo slot: i rossi verdi; le E2E che usano la maniglia (`risk-lab`, `risk-analysis`); quelle delle tabelle
   (`transactions-table`, `asset-list`, `fx-bulk`, `designer-lab picker`).
5. Documentazione: `developer/frontend/core-ui/data-table.md`; devWiki `problems/datatable-actions-column-on-mobile` e
   `problems/datatable-column-resize-noop`.
6. Checkpoint FROZEN, con il filtro regex della galleria mobile d'ingresso, che si fa nello slot dei colori dopo G-13
   ed è confrontata con il riferimento di G-13.

### Stato dei lotti (19/10, base `ede7adf75`)

Ogni ingresso è il merge in `dev_release2` (numero del treno nel registro del [README della fase](../README.md)), verificato
antenato della base il 19/10. I titoli ⏳ del §7 sono il registro del momento: lo stato di oggi è questa tabella.

| Lotto | Contenuto | Stato | Ingresso (treno) | Dettagli |
|---|---|---|---|---|
| Y1 | taglio di `GrowthChart` (FE6a), B10 | ✅ 15/10 | `badec1465` (36) | §4 «Y1», §7 |
| Y2 | taglio di `DataTable`, `~split` dichiarato | ✅ 15/10 | `c747a74c3` (45) | §4 «Y2», §7 |
| Y8 | I-01, I-03 (Y-1), 47-1, O-16, 48-1 | ✅ 15/10 | `160562b56` (57) | §4 «Y8», §7 |
| Y7 | C-38 e difetti 2 e 5 del PAC (D-Y17), C-62 (D-Y18) | ✅ 16/10 | `a613a217c` (76) | §4 «Y7», §7 |
| Y4b | FE2b, il rischio in `lib/features/risk/` | ✅ 16/10 | `08efa5ac3` (81) | §7 «Y4b» |
| Y3 | FE6b, la dashboard in `lib/features/dashboard/` | ✅ 16/10 | `4447814ed` (104) | §7 «Y3» |
| Y9 | K-15, C-34 (con la guardia), C-15, K-13 | ✅ 16/10 | `4447814ed` (104) | §7 «Y9», «C-34» |
| Y10 | 54-1, Y-6, decisione 49 | ✅ 16/10 | `4447814ed` (104) | §7 «Y10» |
| Y5 | FE7, broker e lotti in `lib/features/brokers/` | ✅ 16/10 | `4447814ed` (104) | §7 «Y5» |
| Y6 | FE3, i file in `lib/features/files/` | ✅ 16/10 | `4447814ed` (104) | §7 «Y6» |
| Y12a | U8 senza campi nuovi: W7, le dichiarazioni, `LotCustodyModal` | ✅ 16/10 | `0c79932a7` (130) | «Y12a» |
| Y11 | C-85, `pageBusy` (decisione 48, N55): passi 1–4b, poi il lotto `assets` | ✅ 16–17/10 | `0c79932a7` (130), `d32d0f3d9` (191) | «Y11» |
| Y12b | U8 con i campi di J e MF: P19; R17, W8, P4; V11 e P5 | ✅ 16–17/10 | `23f71e739` (140), `1565b6bbb` (202), `d4ecfb692` (255) | «Y12b», «R17 · W8 · P4» |
| Y4a | FE2a, i segnali in `lib/features/signals/` | ⏸ fermo | — | «Y4a · analisi aggiornata»: per il developer, «non nella 1.3, oppure una finestra notturna» (16/10 20:21) |
| Y13 | FE9–FE11 | ⏸ parcheggiato | — | «Y13»: fino alla risposta del developer a Y13-1 (dopo il tag?) |
| Y-N65 | N65: nessun intervallo di un giorno in tutti i selettori; il righello; il cursore del grafico (N65-7) | ✅ 19/10 | `5cb47395f` | «19/10 · Y-N65», «Il lotto Y-N65» (passo 7) |
| Z-29d-0 | `AssetComparisonSignal._basePoint`: la base in % del confronto dal punto iniettato (per Z-29b e Z-29d) | ✅ committato 20/10, entra col treno 2 | `bccf05cbb` (giornale `c19d808fe`) | «20/10 · Z-29d», «Risposte del coordinatore (20/10 09:01) e il lotto Z-29d-0» |
| Z-29d | il dialogo chiede la serie allineata del bersaglio | ⏸ aspetta Z-29a in dev e Z-29b sulla base | — | «20/10 · Z-29d» |
| Y-38 | il selettore dell'asset di confronto fa scorrere il nome lungo | ✅ committato 20/10, entra col treno 2 | `252ddefbd` (giornale `a91ff36cd`) | «20/10 · Y-38» |
| Y-39 | la scheda e la sua anteprima: una funzione dei segnali, l'anteprima sul grafico del dettaglio (rivisto con F-1) | ⏳ via 20/10 13:16. Y-39a ✅ in dev (treno 6, `89e8b2e61`). Y-39b: cura fatta il 21/10, prove leggere e prova a mano verdi; aspetta lo slot E2E | — | «20/10 · La scheda e l'anteprima», «20/10 · Y-39 rivisto e Y-40», «20/10 · Il lotto Y-39» |
| Y-40 | le tre viste: assoluto, percentuale, rendimento mobile (barra, scheda, impostazioni, dettaglio), anche sui cambi (V-9) | ⏸ nella 1.3, dopo Z-29s; V-1…V-8 (a) | — | «20/10 · Y-39 rivisto e Y-40», «20/10 · Il lotto Y-39» (decisioni) |

Fuori dai lotti:
- **Le voci Y-N** della mia sezione del backlog: ognuna ✅ porta il suo commit d'ingresso (rimesse in pari il 19/10). Aperte,
  tutte in attesa del developer: Y-7 (dopo Y4a), Y-9, Y-10, Y-15, Y-18, Y-26, Y-32, Y-35; più Y-36 e Y-37 (19/10, minime).
- **Lavori per altri, fatti da Y**: la metà del pannello di J-12 (`46b5fbc0e`, treno 280), X-R59 lotti A e B (`f317e3a9f`,
  330), J-53 (`fb6d58d17`, 338), Y-30 (`ede7adf75`, 19/10, dopo il sì del developer a N89).

## 5. Test e specialisti

- `test-author` per ogni test nuovo o riscritto, su file distinti, con le regole della corsia nel prompt (mai
  `./dev.py` nudo, nessuna installazione, nessun `--force`, nessuna run senza il mio via).
- `docs-writer` per le pagine MkDocs per sviluppatori, in inglese.
- `test-triage` prima di chiamare instabile un rosso.
- Una invocazione alla volta nella corsia 6189.

## 6. Conflitti e rischi (Y1, Y2)

- Y1: i legami al sorgente (24 letture di GrowthChart), l'invariante della cache (`aggregationInputs` letto solo
  dalla memo), la maschera della privacy nel tooltip e la sua reattività; nessun file di altri figli.
- Y2 (forma proposta):
  - **Ambito del CSS.** Quattro selettori attraversano il confine: le due `:has(.cell-editable-select-wrapper)` del
    padre e le due `th:hover .resize-handle` del figlio. Le 5 `.filter-btn` sono in due copie. La specificità si prova
    sul CSS compilato.
  - **Sink `{@html}` spostati**: il gate `htmlSink` si riscrive con `test-author`.
  - **Il piede che riusa lo switch**: differisce solo per `data-testid`, se un piede imposta `testId`. Oggi nessuno lo
    fa.
  - **Le 4 classi dell'interruttore in un file nuovo** (R3, record ereditato): lo dico al coordinatore colori.
  - **Il Designer Lab**: la regola `th` e il token d'intestazione restano in `DataTable.svelte`.
  - **I 56 consumatori**: la loro API e il loro DOM non cambiano.
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

### Y1 — commit e aggiornamento di base ✅ (2026-10-15, 14:40–14:45)

> **Note implementazione**: committati dal coordinatore `495fe0eae` (`refactor(dashboard): cut GrowthChart into
> modules`) e `374dcca8a` (journal). Aggiornamento di base con `f46a93ffd` (H CP6, X FE5b, E1): unico conflitto
> `frontend/src/themeRoles.baseline.tsv`, come previsto; `theme-roles.mjs --resolve` ha tenuto le due righe `~split`
> (AssetModal e GrowthChart), `--check` pulito, nessun caso R-8; `git add` del solo baseline; merge committato dal
> coordinatore in `ceb0e09a3`. Nessuno dei 104 file fusi in automatico tocca le cartelle di Y.
>
> **Sull'albero unito**: `npm run check` → 1 errore in `features/instance/components/InstanceBlockedPage.svelte` (H),
> perché il client API generato era di prima della merge; dopo `dev.py api sync` (solo file ignorati) **0/0**. Vitest
> del taglio, un file alla volta: 265, 6, 159, 6, 36, verdi.
>
> **Fuori pista**: dopo ogni aggiornamento di base che porta endpoint nuovi va rifatto `api sync` prima di
> svelte-check: il client generato è ignorato da git e non segue la merge.

### Y1 — galleria filtrata, cancello d'ingresso ✅ (2026-10-15, 14:44–15:12)

> **Note implementazione**: slot del programma colori; `gallery_snapshot.sh y1-fe6a-ceb0e09a3` sulla corsia 6189,
> `-f "Dashboard|Brokers" --workers 6`, carico della macchina 45–65. 882 PNG, 55 test passati, 4 rossi di timeout
> sotto carico (desktop `main dashboard`: `waitForLoadState` 20 s nella prima ondata; mobile `growth P&L submodes`:
> click sul pulsante delle candele, in attesa che sia stabile; mobile `allocation charts`: stesso errore su un pannello
> che Y1 non tocca; mobile `fifo lots panel`: «frame still moving», instabilità nota). `live_price_check` exit 0.
> Confronto con `g-final3-r1` (commit `2338aaf79`, 09:14; `--common-only`, maschere e stabilità di
> `g-final3__r1__vs__r2`): 762 identiche, 120 cambiate — 79 low, 29 medium (passi del wizard d'import, fifo-lots), 7
> unstable (`import-nway-compare`), 5 stable minime (`import-modal`, rumore noto; due fifo-lots da 10 px, Δ1;
> `import-bulk-staging` 5 px, Δ1). **GrowthChart**: 46 scatti presi, 3 cambiati (`main-pct` ×2 e `growth-pnl-candles`
> mobile, 4 px, Δ ≤ 4, antialiasing); `brokers/detail` 4 cambiati, low, ≤ 16 px, Δ ≤ 3. **Nessuna differenza dal
> taglio.** Buco di copertura: `main`, `main-pct`, `kpi-top` desktop e 18 dei 24 `growth-pnl` mobile; proposto al
> coordinatore il rilancio isolato dei due test a `--workers 2`.
>
> **Riprese isolate** (via del coordinatore, stesso slot; `--no-populate --workers 2`, `nice -n 10`):
> `y1-fe6a-ceb0e09a3-retry-desktop-main` (`--desktop-only -f "main dashboard - all languages and themes"`): 1 test
> verde in 1,3 min, 24 PNG, **24/24 identiche** a `g-final3-r1`. `y1-fe6a-ceb0e09a3-retry-mobile-growth`
> (`--mobile-only -f "dashboard growth P&L submodes - all languages and themes"`): 1 test verde in 1,4 min, 24 PNG,
> 23 identiche e 1 cambiata, `mobile/en/light/dashboard/growth-pnl-candles`: 4 px, Δ 4, bbox `[1035, 1979, 1042,
> 1983]`, lo stesso scarto della prima run. Lo stesso scarto, nella stessa area, compare già nei confronti di
> `g-final3-r1` con `g-final3-candR` (`87b7c34b8`) e `g-final3-candL` (`c0556a240`): due antenati della HEAD senza il
> taglio. È una variazione mobile già esistente, non di Y1. Copertura completa del grafico: 96 scatti (48 per
> piattaforma). Restano senza ripresa i rossi mobile di `allocation charts` e `fifo lots panel`, componenti che Y1 non
> tocca. `dirty_files: 1` nei `meta.json` è questo piano, fuori dalla build.
>
> **Fuori pista**: uno scarto ripetibile non è per forza del commit sotto esame. Prima di attribuirlo, cerco lo stesso
> scarto nei confronti già fatti su commit antenati (`$W/diffs/g-final3__r1__vs__cand*`).

### Y1 — ingresso in `dev_release2` ✅ (2026-10-15)

> **Note implementazione**: il coordinatore ha committato il journal (`cf8101f29`) e ha fuso Y1 in `dev_release2`:
> `badec1465`, merge di `cf8101f29` sopra `8fc44558c`. Sull'albero unito il controllo dei colori è pulito.

### Y2 — preparazione e piano del taglio ✅ (2026-10-15, 15:12–15:21, sola lettura)

> **Note implementazione**: piano scritto in §4, Y2, senza toccare `DataTable.svelte`. Cosa ho verificato a
> `cf8101f29`:
> - **Il file**: invariato dalla base; stile senza letterali (155 letture `--lf-cmp-*`); m1 4 alle righe 1387 e 1393.
> - **Il gate dei token** (regole a–e): ignora la sezione commentata di `table.css`. Il taglio chiede solo che i figli
>   importino `table.css` (b) e che ogni definizione resti letta (c).
> - **`htmlInterpolation.gate.test.ts:905`**: controlla solo che il file sia letto, quindi non si tocca.
> - **I legami per percorso** del Designer Lab: i test unitari usano il percorso in alberi sintetici. Le due E2E
>   (`picker:216`, `live`) leggono la regola `th` in `DataTable.svelte`.
> - **Il cricchetto**: `declareSplit` (R3) dà ai pezzi il record ereditato.
> - **Il piede**: `FooterCellContent` ⊂ `CellContent`; nessun piede imposta `testId` (tre siti in produzione, vedi §4
>   Y2).
> - **Lo stile da fuori**: solo `OtherPeriodEffectsTable` stila gli interni di DataTable, e solo la struttura.
> - **I blocchi che si spostano**: nessuna regola `@media`, `@keyframes` o `animation`, e nessun gruppo di selettori
>   a cavallo fra padre e figlio.
> - **Le E2E**: 26 spec esercitano intestazioni, filtri, piedi e celle. Le 13 scelte coprono ogni funzione e sono
>   mappate alle azioni del runner.
>
> **Fuori pista**: la forma approvata D-Y2 (quattro figli) farebbe diventare rossa una E2E del programma colori
> (`designer-lab-picker.spec.ts:216`). Propongo al coordinatore due figli, con la struttura nel padre.

### Y2 — via al taglio ✅ (2026-10-15, ~15:35)

> **Note implementazione**: il coordinatore ha approvato la forma nuova di D-Y2: due figli, con struttura, CSS
> strutturale e gestori nel padre. Ha poi annunciato il taglio al coordinatore colori, che non ha annunci aperti; T
> arriva a W6 fra settimane. Le condizioni:
> - Il `--split` eredita le 4 classi di `editable-checkbox` senza `--accept`.
> - Senza chiedere: prove di file singoli, più svelte-check e knip con `nice -n 15`.
> - Con lo slot del coordinatore: le 13 spec E2E.
> - Galleria nello slot del programma colori, dopo L-10 e la ripresa di G-9.
> - Il programma colori lavora su file del perimetro di Y:
>   - il figlio V analizza in sola lettura i colori dei grafici (GR1–GR5: `components/charts/*Allocation*`,
>     `GeographyMap`, `SemiDonutChart`, `dashboard/AllocationHistoryChart`, `AllocationPanel`, `growthChartSeries.ts`,
>     `risk/CorrelationHeatmap`). Prima del suo codice ci si coordina, file per file;
>   - T-8 cambia valori di ruoli e ne aggiunge: chi usa già i ruoli non tocca niente.
>
> Ordine: prima l'impalcatura d'oro registrata sul codice di oggi (`test-author`), poi il taglio.

### Y2 — passo 1, oracoli ✅ (2026-10-15, 15:40–16:15)

> **Note implementazione**:
> - **Impalcatura d'oro**: `test-author` ha scritto `components/table/DataTable.golden.test.ts`, 878 righe, non
>   tracciato, da non committare; una copia sta nella cartella di sessione. 28 stati (tutti i rami dei tre blocchi che
>   si spostano, con l'elenco di quelli non raggiunti e del perché) registrati in `/tmp/librefolio-r13-y/datatable-golden`
>   sul codice di `cf8101f29`.
>   - Registrazione: `LF_GOLDEN=record nice -n 10 node_modules/.bin/vitest run src/lib/components/table/DataTable.golden.test.ts`,
>     28 verdi.
>   - Confronto sullo stesso codice: 28 verdi, quindi il confronto è deterministico.
>   - Controprova: con un file d'oro alterato, 1 rosso con stato, posizione e contesto; poi file ripristinato (somma
>     identica).
>   - Normalizzazioni oltre l'elenco: l'id della listbox di `SimpleSelect`, numerato da un contatore di Svelte, viene
>     rinumerato per ordine di comparsa; il valore vivo di `<input>` e `<select>` e il registro delle callback vengono
>     accodati a ogni stato.
> - **Trappola voluta**: due celle HTML del piede dell'impalcatura hanno un `testId`. Oggi il piede non lo scrive, la
>   cella sì. Dopo il taglio mi aspetto quelle due sole differenze, da provare con una registrazione separata.
> - **Confronto del CSS compilato**: `y2_css_compare.mjs`, nella cartella di sessione. Usa `svelte/compiler` e
>   `css-tree` del `node_modules` locale. Prova a vuoto sul file invariato: 159 voci identiche su 159, nessun avviso,
>   ordine tenuto.
> - **Script del taglio**: `y2_cut_datatable.py`, nella cartella di sessione. Controlla ogni marcatore e ogni riga
>   attesa prima di scrivere, e non scrive nulla se il file non è quello di `cf8101f29`. A vuoto: padre 1 751 righe,
>   intestazione 336, cella 454.
>
> **Fuori pista**:
> - Nel piano avevo contato un solo piede in produzione, ma sono tre: due passano la prop in forma breve. Nessuno
>   imposta `testId`, quindi la conclusione non cambia.
> - Le regole CSS della cella sono 39, non 41, e nel padre ne restano 100. I conteggi in §4 sono corretti.

### Y2 — passi 2–4, taglio, dichiarazione e prove leggere ✅ (2026-10-15, 15:55–16:10)

> **Note implementazione**:
> - **Taglio**: `python3 y2_cut_datatable.py`, dalla cartella di sessione. Il padre passa da 2 431 a 1 751 righe e
>   nascono `DataTableColumnHeader.svelte` (336) e `DataTableCellContent.svelte` (454), con blocchi spostati alla
>   lettera, de-indentati.
>   - Nell'intestazione: un ref locale al posto di `filterBtnRefs`, e `bind:openFilterColumnId`.
>   - Nel padre:
>     - i due `:has(:global(.cell-editable-select-wrapper))`;
>     - le 5 `.filter-btn` del «seleziona tutto», con il loro commento;
>     - via gli import usati solo dai figli.
>   - Prettier (`node_modules/.bin/prettier --write` sui tre file) ha unito in una riga un solo `{@const}` del popover
>     dell'intestazione; le parentesi esplicite non cambiano l'ordine dei ternari.
> - **DOM**: confronto con l'impalcatura d'oro → 26 rossi su 28. I 2 verdi (`loading` ed `empty`) non hanno piede, e la
>   prima differenza di `initial` è il `data-testid="golden-foot-when"` della trappola.
>   - Prova stretta: ho registrato il codice tagliato in `datatable-golden-after`, poi
>     `/tmp/libreFolio_y2_golden_diff.py`.
>   - Risultato: **28 stati su 28 identici byte per byte**, tolti i due attributi della trappola, che compaiono una
>     volta ciascuno in ogni stato con piede (+62 caratteri). Il confronto copre anche i valori vivi degli input e il
>     registro delle callback.
>   - Nessun piede in produzione imposta `testId`, quindi nell'app il DOM non cambia.
> - **CSS compilato**: `y2_css_compare.mjs`, Svelte 5.48.0, nessun avviso del compilatore in nessuno dei tre file.
>   - 155 voci su 159 identiche.
>   - 4 riscritture di selettore con dichiarazioni e specificità identiche:
>
>     | Selettore | Specificità |
>     |---|---|
>     | `th:hover .resize-handle` | (0,3,1) |
>     | la sua variante `.dark` | (0,4,1) |
>     | `td:has(…)` | (0,2,1) |
>     | `tbody tr:has(…)` | (0,2,2) |
>
>   - 5 `.filter-btn` in due copie; 0 mancanti, 0 nuove.
>   - Ordine relativo tenuto in tutti e tre i file: padre 102 voci, intestazione 23, cella 39.
> - **Cricchetto**: `theme-roles.mjs --split lib/components/table/DataTable.svelte:…DataTable.svelte,…DataTableColumnHeader.svelte,…DataTableCellContent.svelte`,
>   poi `--check` pulito.
>   - Baseline: la riga di `DataTable.svelte` sparisce, perché non misura più nulla; `DataTableCellContent.svelte`
>     eredita le sue 4 classi; c'è la riga `~split`.
>   - La nota «79 file sotto il loro record» c'era già prima.
> - **Vitest**, un file alla volta (`/tmp/libreFolio_y2_vitest.sh`):
>   - tabella, tutti verdi: `DataTable` 55, `DataTable.rowOrder` 12, `DataTableHeaderTooltip` 12,
>     `DataTableColumnFilter` 59, `DataTablePagination` 20, `dataTableLogic` 83, `ReportSetCard` 45;
>   - gate verdi: `htmlInterpolation` 26, `themeComponentTokens` 18, `themeRoles.gate` 36, `themeModeReads` 24,
>     `flagFont` 13, `themeTokens` 14, `themeColorMeta` 10, `clipboardSink` 11, `moneyRenderSites` 6;
>   - **`htmlSink` 3 rossi, attesi**: i 6 sink passati ai figli, le 3 voci di DataTable non più valide e il controllo
>     positivo «≥ 10 in DataTable». Il totale dei sink dell'app resta oltre 35. Riscrittura affidata a `test-author`.
> - **devWiki**: tabelle delle fonti aggiornate in `datatable-filter-options-disappear`, `datatable-column-resize-noop`
>   e `datatable-tooltip-custom-cell`. Le altre 9 pagine che citano `DataTable.svelte` parlano di cose rimaste nel
>   padre (td, colonna azioni, timer del tocco, visibilità) o del componente intero.
>
> **Fuori pista**: il commento di `DataTable.test.ts:355` puntava già prima del taglio alla riga sbagliata (la 713 era in
> `applyColumnFilter`). Lo riscrive `test-author` col nome della funzione, `toggleAllPageRows`.

### Y2 — passi 5–6, test e validazione statica ✅ (2026-10-15, 16:10–16:25)

> **Note implementazione**:
> - **`test-author`** ha cambiato solo le righe indicate.
>   - `htmlSink.gate.test.ts`: due voci rivedute al posto delle tre di DataTable, con la stessa ragione `COLUMN_DEFS`:
>     `DataTableCellContent.svelte` `cellContent.html` (celle e piede) e `DataTableColumnHeader.svelte`
>     `getColumnHeaderHtml(column)`.
>   - Il controllo positivo misura ≥ 4 sink nella cella e ≥ 2 nell'intestazione; la storia è nel commento.
>     `sinks.length > 35` resta: oggi sono 39 sink in 21 componenti.
>   - Controprova: con un'`expr` alterata il gate va rosso e nomina i due sink e la voce scaduta; ripristinata, torna
>     verde.
>   - `DataTable.test.ts:355`: il commento cita `toggleAllPageRows` invece della riga.
>   - Prettier pulito.
> - **Verifica mia**: `htmlSink.gate` 7/7.
> - **`npm run check`** (`nice -n 15`, sull'albero tagliato, impalcatura compresa): **0 errori, 0 avvisi**.
> - **knip** (`npm run lint:dead`, `nice -n 15`): stesse 63 voci del Y1, nessuna nei file della tabella oltre ai tre
>   tipi già noti di `types.ts`. L'unica differenza è di formato: knip nudo nomina i sottopercorsi di `@embedpdf` e il
>   binario `pipenv`, mentre il Y1 usava il wrapper.
> - **devWiki**: `check_source_paths.py` → le pagine toccate da Y2 sono pulite. I 5 percorsi mancanti (`htmlcov-*`,
>   `frontend/coverage-js/` e una cartella di sonde di AI Export) c'erano già, in pagine che Y2 non tocca.
> - **Documentazione**: `data-table.md` affidata a `docs-writer`. `mkdocs build` e `check-links` aspettano il via del
>   coordinatore.
>
> **`docs-writer`**, solo `core-ui/data-table.md`, nessun comando:
> - «Where DataTable's code lives», in testa in grassetto dentro «📦 State Management (Internal)», come per
>   GrowthChart: tabella dei quattro file e cosa tiene ciascuno, l'import di `table.css`, i due selettori `:global` di
>   confine («Svelte non li controlla contro il markup dell'altro lato: un rinomina li rompe in silenzio») e le
>   `.filter-btn` in due copie.
> - L'avviso «`html` is rendered as-is» dice dove stanno i sink e che sono voci del gate `htmlSink`.
> - Seconda passata: corretta la riga `headerTooltip`/`headerTooltipUrl` di «🔧 Column Definition». Diceva un'icona,
>   ma `headerTooltip` da solo mette un tooltip sull'etichetta e l'icona compare solo con l'URL. Nuova riga
>   `headerTooltipLinkMode` (`'direct' | 'gesture'`).
> - La pagina non ha traduzioni né un indicatore di aggiornamento.
>
> **Fuori pista**: `docs-writer` ha trovato due commenti fuorvianti nei file nuovi, e li ho corretti.
> - Le `.filter-btn` del padre e dell'intestazione nominavano il «seleziona tutto», ma il bottone è il «mostra solo
>   selezionati» dell'intestazione di selezione.
> - Il commento dell'icona d'informazione, spostato alla lettera, diceva il contrario della sua condizione.
> - Prova che erano solo commenti: CSS compilato con lo stesso referto del primo confronto; golden 28/28 contro la
>   registrazione dopo il taglio; Prettier pulito sui 5 file.
> - Il commento di `types.ts:291` («(info icon)») è sbagliato allo stesso modo, ma `types.ts` è fuori dal taglio:
>   backlog Y-5.

### Y2 — passo 6, E2E e documentazione ✅ (2026-10-15, 16:20–16:40)

> **Note implementazione**:
> - **E2E**: slot pesante 1 del coordinatore. 13 spec in fila con `/tmp/libreFolio_y2_e2e.sh`, ciascuna
>   `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc nice -n 10 pipenv run python dev.py test --test-port 6189 --data-dir /tmp/librefolio-r13-y --workers 2 <categoria> <azione>`.
>   La prima ha rifatto la build del frontend.
>
>   | Categoria | Azione | Esito |
>   |---|---|---|
>   | `front-designer-lab` | `picker` | 3 verdi |
>   | `front-designer-lab` | `live` | 7 verdi |
>   | `front-transaction` | `transactions-table` | 25 verdi |
>   | `front-transaction` | `tx-bulk-diagnostics` | 2 verdi |
>   | `front-transaction` | `transactions-modals` | 25 verdi |
>   | `front-transaction` | `tx-import-upload` | 10 verdi |
>   | `front-portfolio` | `risk-lab` | 44 verdi |
>   | `front-portfolio` | `privacy-masking` | 18 verdi |
>   | `front-utility` | `files-uploader` | **8 rossi**, non di Y2 (sotto) |
>   | `front-utility` | `pac-allocator-real` | 1 verde |
>   | `front-asset` | `asset-browse` | 8 verdi |
>   | `front-asset` | `asset-list` | 28 verdi |
>   | `front-fx` | `fx-bulk` | 7 verdi |
>
>   Porta 6189 libera alla fine.
> - **`mkdocs build`** (strict, `nice -n 15`): exit 0, 3 036 URL relativi di asset risolti. L'unico «Warning» del log
>   è l'annuncio del team di Material for MkDocs. **`check-links`**: 95 link validi.
> - **Impalcatura d'oro tolta** dal worktree, dopo aver verificato che la copia nella cartella di sessione è identica.
>   I file d'oro restano in `/tmp/librefolio-r13-y/datatable-golden{,-after}`.
>
> **Fuori pista**: `files-uploader` ha 8 test rossi su 8, desktop e mobile, ma non dipendono da Y2.
> - **Dove cade.** L'unico errore di ogni test è il controllo di chiusura della spec (`files-uploader.spec.ts:233`,
>   «Only the declared synthetic GET contracts may be requested»), su due `GET /api/v1/system/instance`. I corpi dei
>   test, tabella dei file compresa, sono passati.
> - **Da dove viene la richiesta.** Dallo store `features/instance/instanceConfig.svelte.ts` di H (`2069c75cd`, entrato
>   con CP6), che la fa a ogni caricamento di pagina, mentre la spec dichiara un insieme chiuso di contratti GET.
> - **Anche `dev_release2` è rosso.** Lì la spec e la richiesta sono identiche.
> - **Decisione del coordinatore**: lo corregge con H. Y non tocca la spec, e per Y2 non è un cancello.

### Y2 — checkpoint 🧊 FROZEN (2026-10-15, 16:45)

> **Note implementazione**: base `cf8101f29`; `dev_release2` è a `dae4de4fa`. Albero: 10 file modificati e 2 nuovi.
> - Codice: `DataTable.svelte` (2 431 → 1 751 righe); `DataTableColumnHeader.svelte` (329, dopo Prettier) e
>   `DataTableCellContent.svelte` (454), nuovi.
> - Test: `htmlSink.gate.test.ts` e `DataTable.test.ts`.
> - Baseline: `themeRoles.baseline.tsv`.
> - Documentazione: `core-ui/data-table.md`.
> - devWiki: 3 pagine.
> - Journal: piano e backlog (Y-4, Y-5).
>
> Fuori dal commit: l'impalcatura d'oro e i file d'oro, `.testLog/`, `frontend/build/`, `frontend/test-results/` e il
> catalogo i18n generato. `git diff --check` è pulito, e i due file nuovi non hanno spazi in coda.
>
> **Ancora da fare**: la galleria filtrata, cancello d'ingresso dopo il commit (slot del programma colori, chiesto dal
> coordinatore).

### Y2 — commit e aggiornamento di base ✅ (2026-10-15, 16:42–16:48)

> **Note implementazione**:
> - **Commit del coordinatore**: `fbee8506d` (`refactor(table): split DataTable header and cells`) e `491cf3a4c`
>   (journal).
> - **Aggiornamento di base**: con `dev_release2` a `dae4de4fa`, che porta FE8a di W. L'unico conflitto è stato
>   `frontend/src/themeRoles.baseline.tsv`.
>   - `--resolve` ha fatto vincere il lato più stretto, e `--check` è pulito, senza il caso R-8.
>   - Restano tutte e 6 le righe `~split`, le 3 di Y e le 3 di FE8a, più l'`~accept` D3 di `themeStore.ts`.
>   - `git add` del solo baseline. Merge committato dal coordinatore: `2ffedf004`.
> - **File uniti da Git, controllati**:
>   - `htmlSink.gate.test.ts`: le due voci di Y più quella di W (`TxBulkBanners`), nessuna persa;
>   - backlog: la sezione Y è identica;
>   - nessun marcatore di conflitto;
>   - nessun file nuovo di FE8a stila da fuori le classi passate ai figli, né li importa.
> - **Sulla revisione unita**, una prova alla volta con `nice -n 10`:
>   - `api sync`, nessun file tracciato cambiato;
>   - `npm run check`, **0/0**;
>   - Vitest: `htmlSink` 7, `DataTable` 55, `rowOrder` 12, `HeaderTooltip` 12, `ColumnFilter` 59, `Pagination` 20,
>     `dataTableLogic` 83, `ReportSetCard` 45. Tutti verdi.

### Y2 — galleria filtrata, cancello d'ingresso ✅ (2026-10-15, 16:54–18:10)

> **Note implementazione**:
> - **Scatto**: slot del programma colori, concesso mentre T-8 era in scrittura.
>   `gallery_snapshot.sh y2-dt-2ffedf004 … -- -f "Transactions|Assets|FX|Files|Risk Analysis" --desktop-only --workers 6`,
>   cioè i 57 test dei cinque gruppi più un test di Onboarding e uno di Import report sets, i cui titoli contengono
>   quelle parole.
>   - Esito: 59 verdi e 10 rossi, 600 PNG, in 16 minuti.
>   - Carico medio da 21 (16:48) a 85 (17:11). Porta libera alla fine.
> - **Confronto** con `g-final3-r1` (`--common-only`, maschere e stabilità di `g-final3__r1__vs__r2`): 454 identiche,
>   146 cambiate in 46 scatti.
>   - 43 scatti su 46 cambiano anche nel rumore `r1` contro `r2` (stesso codice), con ampiezze simili o maggiori; lo
>     script è `/tmp/libreFolio_y2_noise_cmp.py`.
>   - I 3 restanti hanno Δ1: la linea del grafico FX dietro il modale dei provider, un bordo di 1 px di
>     `add-pair-routes` e un'icona 7×7 di RSI.
>   - `transactions/list`: 8 su 8 identiche.
>   - `assets/list-table`: punti cambiati solo nella barra sopra la tabella. `fx/list-table`: bordi della barra e
>     pillola della paginazione, un file che Y2 non tocca. Entrambe cambiano allo stesso modo anche nel rumore.
>   - **Nessuna differenza viene da Y2.**
> - **Triage dei 10 rossi** (skill `test-triage`). Verdetto: **ambiente**, da confermare con la ripresa.
>   - §1 forma della risposta: nessuna asserzione sul contenuto, solo timeout.
>   - §2 clock: le attese sono sulle condizioni giuste.
>   - §3 stato condiviso: corsia esclusiva e nessun errore del backend.
>   - §4 cascata: nessuna causa unica. I 2 rossi di Files cadono nella prima ondata di login, gli 8 di Assets negli
>     ultimi 15 test, al picco di carico.
>   - Tutti e 10 erano verdi in `r1`, `r2`, `candR`, `candL` e `candT6`.
>   - Nessuno cade su una `DataTable`. Il #10 passa `tx-table` e cade sull'`AssetSelect` del wizard, che non è mai in una
>     cella.
> - **Ripresa chiesta** al coordinatore: `-- --no-populate --desktop-only --workers 2 -f "<i 10 titoli>"`; il filtro
>   prende esattamente quei 10. Chiude anche il buco di copertura, che comprende la lista dei report dei broker in
>   Files (`FilesTable`, una `DataTable`).

### Y2 — E2E sulla revisione unita ✅ (2026-10-15, 17:39–17:45)

> **Note implementazione**: slot pesante 2, dopo E1b di W. Sulla revisione `2ffedf004`, che porta FE8a, con
> `/tmp/libreFolio_y2_e2e_merged.sh`: `--workers 2`, `nice -n 10`, una spec alla volta.
> - `front-transaction transactions-table`: 25 verdi.
> - `front-transaction transactions-modals`: 25 verdi.
> - `front-transaction tx-import-upload`: 10 verdi.
>
> Porta 6189 libera alla fine.

### Y2 — ripresa della galleria e ingresso ✅ (2026-10-15, 18:00–18:10)

> **Note implementazione**:
> - **Ripresa**: slot del programma colori, a carico basso, dopo la validazione di T-8.
>   `gallery_snapshot.sh y2-dt-2ffedf004-retry … -- --desktop-only --workers 2 -f "<i 10 titoli>"`: **10 verdi su 10**,
>   96 PNG, in 4,7 minuti, con il carico medio fra 31 e 38. Il verdetto «ambiente» del triage è confermato.
> - **Confronto** con `g-final3-r1`, stesse opzioni: 75 identiche, 21 cambiate in 7 scatti, e tutti e 7 cambiano anche
>   nel rumore `r1` contro `r2`.
>   - `files/static-grid` supera il rumore (fino a 28 113 px), ma è G-10: l'ultima scheda mostra un altro avatar
>     (`men_04` → `men_01`), e cambiano gli orari di caricamento (09:15 → 18:00). È la griglia, senza tabelle.
>   - Pagine con `DataTable`: `files/brim-tab` (la lista dei report dei broker, `FilesTable`) è identica 8 su 8, e lo
>     sono anche `assets/distribution-editor-*`, `detail-classification` e `chart-settings`.
>   - **Nessuna differenza viene da Y2.**
>
> **Fuori pista**: per la ripresa ho fatto ripopolare il DB alla galleria invece di usare `--no-populate`. Le 3 E2E
> fatte nel frattempo l'avevano ripopolato senza risorse statiche (il runner E2E non usa `--with-static`), e i test di
> Files avrebbero falsato il confronto. Regola: `--no-populate` vale solo se fra la galleria e la ripresa non gira nulla
> nella corsia.
>
> Il coordinatore ha aggiunto Y-6 per Y10 (`AllocationPanel.svelte:65` passa `emoji` alla torta, che dopo DV non lo
> legge più): è nel backlog e in §2.

### Y3 e Y4 — analisi ✅ (2026-10-15, 18:10–18:20, sola lettura)

> **Note implementazione**: analisi breve mandata al coordinatore. Base `c747a74c3`, letta dal worktree portato a
> `695e6ad12`, stesso codice. Script e dati nella cartella di sessione: `libreFolio_y34_graph.py` (grafo degli import)
> e `libreFolio_y34_literals.py` (percorsi fuori dagli import).
>
> | Lotto | Da → a | File | Import esterni |
> |---|---|---:|---:|
> | Y3 · FE6b | `components/dashboard/**`, `dashboardViewStore(.test).ts`, `dateRangeController.svelte.ts` → `features/dashboard/` | 35 | 5 |
> | Y4a · FE2a | `lib/charts/**`, `signalCatalogStore(+test)`, la UI dei segnali più `ChartSettingsModal` e `MeasurePanel` → `features/signals/` | ~55 | 30, 8 dei quali di X |
> | Y4b · FE2b | `components/risk/**`, `lib/risk`, `stores/risk` → `features/risk/` | 101 | 5 |
>
> Nessuna collisione di nomi.
> - **Accoppiamenti per percorso**:
>   - stringhe `vi.mock`: 2 in `AboutTab.test` e 10 nei test di rischio;
>   - gate: `themeModeReads:500-502,1118`, `moneyRenderSites`, `htmlSink` (`SignalOptionContent`), `catalogIcuLocale`,
>     il registro di `warningTranslatorSites`; poi `allocationTypeEmoji.test` (`readFileSync`);
>   - backend: `test_risk_schemas.py:1475-1477`;
>   - runner, righe esatte:
>
>     | File | Proprietario | Y3 | Y4a | Y4b |
>     |---|---|---|---|---|
>     | `_frontend_utility.py` | programma colori | 302–309 | 41–42, 81, 164–172, 270–272 | 84–92, 275–281 |
>     | `_frontend_asset.py` | X | 34–36, 66 | 23–25, 29 | — |
>     | `_frontend_ai_export.py` | J | — | 24–31 | — |
>     | `_frontend_portfolio.py` | Y | — | — | 163–295 |
>     | `coverage_js.py` | — | — | 187, 238 | 184 |
>
>   - istruzioni: l'`applyTo` di `frontend-signals`;
>   - documentazione: MkDocs 1, 3 e 5 pagine; devWiki circa 20, 21 e 27 tabelle.
> - **Colori**:
>   - R4 accoppia senza ambiguità i 53 record dei file spostati, quindi `--check` passa senza toccare il baseline;
>   - lo scanner del Lab, `CHART_PATH_RE` a `frontend/scripts/designer-lab/scan-colors.mjs:193`, deve imparare
>     `features/(dashboard|risk|signals)` nello stesso commit;
>   - `theme-roles.mjs:72` cambia per D-Y14.
> - **Decisioni**: D-Y13…D-Y16 approvate dal coordinatore (§0.3). L'ordine e i lotti Y7 e Y8 aspettano il via del
>   developer, che il coordinatore gli ha chiesto insieme alle decisioni 48–50 (C-85, 54-1, difetto 5 del PAC).
>
> **Fuori pista**: i file di DV stanno in due cartelle che si spostano: `AllocationHistoryChart` e `AllocationPanel` in
> `dashboard` (Y3), `CorrelationHeatmap` in `risk` (Y4b). Per questo il coordinatore propone Y3 e Y4b dopo
> l'ingresso di DV: nessuno deve unire a mano un file spostato.

### Y8 — avvio e rossi ✅ (2026-10-15, 18:36–19:00 circa)

> **Note implementazione**:
> - **Base**: `e424e8740`, il merge senza conflitti di `dev_release2` (`bcd680868`: W E1b, J CP-4, E2 e decisioni) sul
>   mio commit di journal `33620fb7e`.
> - **Verifica**: le cinque voci sono state verificate sul codice di oggi; righe e correzioni sono in §4 Y8.
> - **48-1**: ho chiesto l'ok direttamente a J, che ha risposto: «ok for 48-1, make it yourself in Y8: line 299 …
>   nothing else», senza modifiche aperte né previste sul file.
> - **Rossi**: affidati a `test-author`, un agente sui cinque file già registrati, solo Vitest su file singolo:
>   `timeSeriesAggregation.test.ts`, `GrowthChart.test.ts`, `chartCoreHelpers.test.ts`, `LineChart.test.ts`
>   (facoltativo), `lotGanttChartHelpers.test.ts`.
>
> **Fuori pista**: la skill `devpy-i18n` cambia il disegno di O-16.
> - Regola 6: il `count` di un plurale ICU viene dalle cifre mostrate, mai da `Number(…)`, e un valore mascherato è
>   plurale.
> - Quindi c'è un gemello di `formatQuantity`, `quantityPluralCount` (`formatToParts` con le stesse opzioni: parte
>   intera mostrata, più 0,5 se c'è una frazione), e `count` vale `NaN` quando è mascherato.
> - Regola 5: i testi ICU devono differire fra le lingue, e i miei differiscono. Lo controlla il gate
>   `catalogIcuLocale.test.ts`.
>
> **Esito dei rossi**: `test-author` li ha confermati tutti rossi sul codice di `e424e8740`, uno per voce, e ha
> corretto due miei numeri: 365 punti a 800 px danno `interval` 33, e la finestra di prova è di 34 punti. Per
> la regola 6 il caso che discrimina è 1.0004, non 1.0000001: `Intl.PluralRules` arrotonda a 3 decimali.

### Y8 — passo 2, correzioni ✅ (2026-10-15, 19:00–19:35 circa)

> **Note implementazione**:
> - **I-01** (`charts/timeSeriesAggregation.ts`): `aggregateSumSeries` somma solo i punti presenti. Il secchio è
>   `missing`, con valore 0, solo se lo sono tutti i suoi punti; altrimenti la chiave `missing` dell'ultimo punto non
>   passa. `sourcePointCount` conta i punti presenti. `timeSeriesAggregation.test.ts` 47/47.
> - **I-03** (`dashboard/GrowthChart.svelte`): `restoredPctUnchecked` diventa `pctFallback`. Un `$effect`, a ogni
>   caricamento finito, ripiega da `%` ad Abs quando la storia non ha dati in `%`, e torna al `%` quando li ritrova,
>   salvo una scelta esplicita nel frattempo (`selectMode` azzera il ripiego). Lo storage non cambia.
>   `GrowthChart.test.ts` 165/165, tooltip 6/6.
> - **O-16** (`brokers/lots/lotGanttChartHelpers.ts`, `LotGanttChart.svelte`): `quantityPluralCount` e
>   `lotQuantityLine`. Le chiavi `brokers.lots.tooltip.quantityClosed` e `quantityOpen`, ICU nelle quattro lingue,
>   sono state aggiunte con `dev.py i18n add`; `shares` e `sharesOpenOutOf` sono state tolte con `i18n remove -f`, e
>   nessun lettore resta, nemmeno dinamico. `lotGanttChartHelpers.test.ts` 117/117, `catalogIcuLocale.test.ts` 17/17,
>   `dev.py i18n check` verde (4482 chiavi, strict).
> - **47-1** (`charts/responsiveXAxis.ts`, `LineChart`, `CandlestickChart`, `PriceChartFull`):
>   - `visibleCount` entra nella politica; `visiblePointCountFromZoom` legge l'evento o la finestra `{start, end}`;
>     `categoryAxisLabelPatch` porta sempre `interval: 'auto'`; `ZOOM_LABEL_SETTLE_MS` vale 120.
>   - `LineChart` e `CandlestickChart` salvano l'ultimo evento di `dataZoom` e, a gesto fermo da 120 ms, uniscono la
>     patch. Il ridimensionamento usa il conteggio visibile, e `cleanup()` ferma il timer.
>   - `PriceChartFull` riusa il suo timer di 200 ms: se la risoluzione non cambia, ridistribuisce le etichette; il
>     render passa il conteggio ricavato da `computeZoomWindow`.
>   - `LineChart.test.ts` 5/5, con i 2 rossi diventati verdi; `PriceChartFull.test.ts` 36/36;
>     `priceChartHelpers.test.ts` 148/148.
> - **48-1**: `gap-2 px-3` → `gap-1.5 px-2.5` in `AiExportMenu.svelte:299` (con l'ok di J) e nel `sync-button` della
>   Dashboard (`+page.svelte:965`). Nessun test fissa quelle classi.
> - **Prettier** pulito sui file toccati; `theme-roles --check` pulito.
>
> **Fuori pista**:
> - **Il lampo dopo un ridisegno**: con lo zoom attivo, un render completo di `LineChart` e `CandlestickChart` usava
>   il passo di tutto l'asse finché, 120 ms dopo, l'evento dello zoom ripristinato lo correggeva. Sul dettaglio asset in
>   candele, con il ciclo di 30 s, sarebbe stato un lampo ogni 30 s. Ora il render legge lo zoom salvato *prima* della
>   politica e le passa `visibleCount`. La lettura con `getOption()` è salita di qualche riga: è sempre una per render.
>   `PriceChartFull` lo faceva già, da `logicalRange`.
> - **Il patto di adozione in `chartCoreHelpers.test.ts`**: 3 rossi, perché il ramo del ridimensionamento doveva
>   contenere `axisLabel: policy.axisLabel` e ora unisce `categoryAxisLabelPatch(policy)`. Il cambio è voluto: senza
>   `interval: 'auto'`, un passo vecchio sopravvive all'unione. Lo ripinna `test-author`, solo per i tre grafici zoomabili
>   (gli altri cinque restano stretti), con nuovi pin sul cablaggio.
> - **48-1 esteso al `sync-button`**: sulla Dashboard il vicino del pulsante dell'AI Export è il `sync-button`, con le
>   stesse `gap-2 px-3`. Allineare solo il primo avrebbe creato uno scarto proprio lì. La pagina è nel mio perimetro;
>   lo segnalo al checkpoint.
> - **Prettier** ha riformattato la firma di `lotQuantityLine`, codice mio: in HEAD il file era pulito.

### Y8 — passo 3, test e prove leggere ✅ (2026-10-15, 19:35–20:10 circa)

> **Note implementazione**:
> - **`test-author`, secondo e terzo giro** (solo `chartCoreHelpers.test.ts`, 277 → 287, tutti verdi):
>   - il patto di adozione è ripinnato per i tre grafici zoomabili (`ZOOM_RELABEL_CHARTS`): il ramo del
>     ridimensionamento unisce `categoryAxisLabelPatch(policy)`, e in quei file non resta un `axisLabel:
>     policy.axisLabel`. Gli altri cinque grafici tengono il pin stretto;
>   - un `describe` nuovo fissa il cablaggio: evento → `scheduleZoomedAxisLabels` → timer →
>     `applyZoomedAxisLabels`; il conteggio visibile nel ridimensionamento e nel render; l'ordine «zoom salvato →
>     politica → `setOption(option, true)` → ripristino», con la stessa condizione per il conteggio e il ripristino;
>     nessun `getOption()` nelle funzioni dello zoom;
>   - unità di `categoryAxisLabelPatch`: compatto con passo (34 di 365, `interval` 2), compatto senza passo (4 di
>     365 a 300 px, `'auto'`), largo (20 di 365, uguaglianza stretta con i valori ripristinati);
>   - ECharts vero in SSR: dopo un'unione l'`interval` vale 33, poi 2, poi `'auto'`. I `null` restano `null`, che
>     per ECharts significa il suo valore predefinito. Il controllo negativo: un'unione senza `interval` tiene 33. È la
>     regola che giustifica la patch;
>   - stretta anche la fetta `capture` del test di `CandlestickChart`, che dopo lo spostamento abbracciava tutta la
>     costruzione dell'opzione;
>   - morso provato su copie in memoria dei file veri: 30 espressioni regolari, ognuna rossa sulla sua mutazione;
>     i controlli dei file intatti e del pin vecchio si comportano come previsto.
> - **Vitest, un file alla volta** (`/tmp/libreFolio_y2_vitest.sh`, `nice -n 10`), 17 file:
>   - `chartCoreHelpers` 287, `LineChart` 5, `PriceChartFull` 36, `priceChartHelpers` 148, `timeSeriesAggregation`
>     47, `GrowthChart` 165, `GrowthChart.tooltip` 6, `lotGanttChartHelpers` 117, `aiExportUi` 6;
>   - i gate: `catalogIcuLocale` 17, `moneyRenderSites` 6, `htmlSink` 7, `themeRoles` 36, `themeModeReads` 24,
>     `themeComponentTokens` 18, `flagFont` 13;
>   - `htmlInterpolation` 25/26: il rosso non è di Y8 (sotto).
> - **Statiche**:
>   - `npm run check` (svelte-check, `nice -n 15`): 0 errori, 0 avvisi;
>   - `npm run lint:dead` (knip): gli stessi reperti di Y2, con un'esportazione inutilizzata in meno (`ApiError`,
>     corretta da altri nella base). Le mie esportazioni nuove sono tutte usate;
>   - Prettier `--check` pulito, `theme-roles --check` pulito, `git diff --check` pulito;
>   - `dev.py api sync` senza cambi tracciati; `dev.py i18n check` verde (4482 chiavi, strict); `dev.py i18n
>     audit`: le chiavi dei lotti sono usate, e i 2 «likely unused» sono di W (`events.deleteBlocked`,
>     `events.deleteNotFound`).
>
> **Fuori pista**: `htmlInterpolation.gate.test.ts` › «finds no markup in any translation outside the reviewed
> sanitized keys» è rosso sulla base, non per Y8.
> - Il reperto: `email.problems.SMTP_FROM_INVALID` contiene «<» nelle quattro lingue («…such as LibreFolio
>   <noreply@example.com>»).
> - La chiave viene da `b33654f22` (E, «feat(email): add admin status and test email», 15/10 15:25), antenato di
>   `e424e8740` e già in `dev_release2`. Il mio diff i18n tocca solo `brokers/`.
> - Il gate legge il catalogo, quindi il rosso è deterministico, non instabile. Lo segnalo al coordinatore e non tocco
>   la chiave: il file è di E.

### Y8 — passo 5, documentazione ✅ (2026-10-15, 19:40–20:05 circa)

> **Note implementazione**:
> - **`docs-writer`**:
>   - `user/dashboard/charts.en.md`, riga 11: la frase sul ripiego da `%` ad Abs dice che la scelta resta, e che `%`
>     torna appena ci sono dati, salvo un'altra scelta nel frattempo (I-03);
>   - `developer/frontend/components/charts.md`: il punto «Zoom» in «Responsive Date Axis» (47-1), la frase finale
>     sul passaggio da compatto a largo, e il paragrafo dei sottomodi P&L, che descriveva ancora l'I-03 di prima.
>     Quest'ultima è una correzione in più: la tengo, perché è esatta e il paragrafo era falso.
> - **Mie correzioni al testo**:
>   - «`pctFallback` remembers it» → «marks the fallback»: il ricordo è dello storage;
>   - «a zoom handler never needs `getOption()`» → «never from `getOption()`»: `updateArrowRotations()` lo legge
>     ancora a ogni passo (Y-8).
> - **Traduzioni**: la sola frase cambiata, scritta a mano in it, fr ed es, con il lessico delle pagine sorelle
>   («período» e «bróker» in spagnolo). Debito prima: nessuno (`translate --dry-run` «up-to-date»).
>   `translate-stamp`, poi `--dry-run` di nuovo «up-to-date». `translate-validate --hide-localized`: nessuna riga
>   per `dashboard/charts`; i 282 errori sono di altre pagine.
> - **devWiki**: `problems/line-chart-axes-lost-the-day` (47-1 chiusa), `problems/toolbar-measurements-differed-by-
>   the-scrollbar-gutter` (48-1 chiusa), `concepts/echarts-chart-gotchas` (la regola dell'unione), tre righe
>   dell'indice e una voce del log. `check_source_paths.py`: 5 mancanti (8 occorrenze), come prima, tutti
>   preesistenti. Grafo non aggiornato: graphify non c'è nel worktree.
> - **Backlog, sezione Y**: Y-1 chiusa (al checkpoint), Y-8 nuova (`updateArrowRotations()` e `getOption()` a ogni
>   passo dello zoom).
> - **`mkdocs build` (strict) e `check-links`** (via del coordinatore, 20:10, con `nice -n 15` e carico sotto 70): build
>   rc 0, 0 righe WARNING/ERROR, 3044 URL relativi risolti; `check-links` 96 link validi. Nessun file tracciato
>   cambiato. Tra le due prove il carico è salito a 89, e lo script ha aspettato 3,5 minuti che tornasse sotto 70.

### Y8 — checkpoint 🧊 FROZEN (2026-10-15, 20:18)

> **Note implementazione**:
> - **CHANGELOG**: tre righe in `[Unreleased]` › «🐛 Fixed», approvate dal coordinatore (20:10): I-03, 47-1, O-16.
>   La seconda è corretta rispetto alla proposta: il difetto non era «on phones» soltanto. La politica compatta vale
>   anche sotto i 24 px per punto, quindi un periodo lungo su desktop perdeva le etichette nello stesso modo.
> - **48-1**: la riga di `AiExportMenu.svelte` è di J, e il suo ok è scritto: «ok for 48-1, make it yourself in Y8:
>   line 299 … nothing else». Il coordinatore ha approvato anche il `sync-button`.
> - **Stato**: HEAD `e424e8740`, nessun server, porta 6189 libera, `git diff --check` pulito. Il coordinatore fa il
>   checkpoint e poi il merge di `dev_release2`, che porta anche la correzione di E per `htmlInterpolation`
>   (`be7de95b6`).
> - **Dopo**: le 8 E2E sulla revisione unita, con lo slot 2 dopo X; poi la galleria d'ingresso, chiesta dal
>   coordinatore al coordinatore dei colori.

### Y8 — commit, merge di `dev_release2` e prove sulla revisione unita ✅ (2026-10-15, 20:19–20:31)

> **Note implementazione**:
> - **Commit del coordinatore**: `a25d09a69` fix(charts) e `df817a3a8` docs(journal).
> - **Merge**: il coordinatore ha aperto il merge di `dev_release2` (`b4597efad`). Due conflitti, entrambi aggiunte
>   allo stesso punto:
>   - `CHANGELOG.md`: le 2 righe della base, poi le 3 di Y8 in fondo a «🐛 Fixed»;
>   - `devWiki/log.md`: la voce di B, poi quella di Y8.
> - **Stage**: solo i due file, tramite uno script che rifiutava più di un blocco di conflitto per file.
> - **File uniti da Git, rivisti uno per uno**: `devWiki/index.md` e il backlog, ognuno con le modifiche dell'altro
>   lato in sezioni diverse.
> - **Sovrapposizioni di senso**: nessuna. Nessun file della base tocca le superfici di Y8, e nessuno legge le chiavi
>   tolte.
> - **Commit del merge**: `e587be8ce`, genitori `df817a3a8` e `b4597efad`, worktree pulito.
> - **Prove sulla revisione unita**, una alla volta, `api sync` e svelte-check solo con il carico sotto 70:
>   - `api sync`: nessun cambio tracciato;
>   - svelte-check: 0 errori, 0 avvisi;
>   - `htmlInterpolation` 26/26, verde grazie a `be7de95b6` di E;
>   - gli altri 16 file Vitest di Y8 tutti verdi, con gli stessi conteggi di prima;
>   - `theme-roles --check` pulito; `i18n check` verde (4517 chiavi, strict).
>
> **Regola nuova del coordinatore** (20:19): il CHANGELOG è una sua superficie. Dal prossimo lotto le righe vanno nel
> messaggio del checkpoint, non nel file.
>
> **Da fare**:
> - le 8 E2E nello slot 2, quando il coordinatore lo libera;
> - la galleria d'ingresso dentro G-13 (decisione del coordinatore dei colori), con la revisione degli scatti di
>   Dashboard, Brokers, Assets e FX che G manderà;
> - nel prossimo checkpoint, una correzione della devWiki: la riga di 47-1 in `echarts-chart-gotchas` dice «on a
>   phone» accanto al 33, che è l'esempio da desktop a 800 px, e il difetto colpisce anche un periodo lungo su
>   desktop.

### Y8 — E2E nello slot 2 ✅ (2026-10-15, 20:33–21:20, con due pause del coordinatore)

> **Note implementazione**:
> - **Slot pesante 2** dal coordinatore (20:32), sulla revisione `e587be8ce`. Script `/tmp/libreFolio_y8_e2e.sh`: una
>   spec alla volta, `--workers 2`, `nice -n 10`, ci si ferma se la porta 6189 è occupata. Log in
>   `files/y8_e2e_NN_*.log` della sessione.
> - **01 `front-portfolio dashboard`: 27/27 verdi** (4,2 min). Prima, il build del test server: 449 s, perché il carico
>   all'avvio era 191.
>
> **Fuori pista**: alle ~20:45 il coordinatore ha fermato le prove per circa 15 minuti, perché DV doveva rilanciare
> una galleria e la macchina era satura.
> - Ho fermato solo il ciclo, con `kill` del suo bash (pid 21017), e ho lasciato finire la spec in corso: il runner
>   21099 è uscito da solo e la porta è tornata libera.
> - Ho risposto «fermo» con l'elenco delle spec verdi.
> - Per la ripresa, `/tmp/libreFolio_y8_e2e_resume.sh` riparte da `front-broker detail` (02) e arriva a
>   `front-portfolio risk-lab` (08).
>
> **Durante la pausa**, la correzione della devWiki: la riga di 47-1 in `concepts/echarts-chart-gotchas` dice ora
> «33 per un anno di giorni a 800 px, 90 o più su un telefono», e anche su desktop. Nel log una voce di correzione in
> coda; la voce di Y8 resta com'era.

> **Esito**, revisione `e587be8ce`, `--workers 2`, `nice -n 10`, una spec alla volta:
>
> | # | Spec | Esito |
> |---|---|---|
> | 01 | `front-portfolio dashboard` | 27/27 |
> | 02 | `front-broker detail` | 37/37 |
> | 03 | `front-asset asset-detail` | 30/33: i 3 test del blocco «Live price direction flash» (sotto) |
> | 04 | `front-fx fx-detail` | 17/17 |
> | 05 | `front-ai-export panel` | 6/6 |
> | 06 | `front-portfolio dashboard-cache` | 6/6 |
> | 07 | `front-portfolio risk` | 38/38 |
> | 08 | `front-portfolio risk-lab` | 44/44 |
> | 09 | `front-asset asset-detail "Live price direction flash"`, da soli con `--workers 1` | 4/4 |
>
> **Triage dei 3 rossi** (skill `test-triage`): `an up-tick flashes green then decays back to neutral`, `a down-tick
> flashes red then decays back to neutral`, `consecutive same-direction ticks each restart the flash`
> (`e2e/assets/asset-detail.spec.ts:8105`, `:8131`, `:8155`).
> - **Cosa ha ricevuto il test**: dopo il tick di 30 s il prezzo è 105.00, quindi il poll è arrivato. Ma
>   `data-live-price-direction` resta `neutral`, senza la classe del lampo.
> - **Dove si decide la direzione**: solo in `applyLiveSummary` (`routes/(app)/assets/[id]/+page.svelte`). Torna
>   `neutral` solo con il timer di 1,3 s o nel `$effect` del poller. Y8 non tocca la pagina, `AssetPriceSummary` né
>   il poller. Senza zoom, il suo codice su quella pagina dà opzioni dell'asse identiche a prima.
> - **Da soli passano**: con `--workers 1` sono 4/4 (09). Nella spec intera a `--workers 2` falliscono.
> - **Verdetto: «assunzione»** (tabella §8 della skill), riprodotto da Z (coordinatore, 21:22). Il test cambia il mock
>   a 105 senza aspettare che il primo poll abbia letto 100. Dopo `74d028ec6` di Z, che ha riscritto il ciclo vivo
>   alle 15:46, ogni poll parte da un timer. Sotto carico il primo poll scatta dopo il cambio del mock: legge 105 senza
>   un valore precedente, e la prima lettura dal vivo è `neutral` per costruzione. Il prodotto è corretto.
> - **Correzione**: Z, in un lotto piccolo di soli test. La spec aspetterà `100.00` prima di cambiare il prezzo.
> - **Per Y8**: i 3 rossi sono preesistenti, con la causa qui sopra. Y8 entra lo stesso (decisione del coordinatore).
>   La mia ipotesi del triage («il primo poll non registra 100 prima del tick») era questa.
> - Porta 6189 libera dopo ogni spec. Nessun file tracciato toccato dalle prove.

### Y7 — preanalisi e annuncio ⏳ (2026-10-15, 20:50–21:00 circa, sola lettura)

> **Note implementazione**: durante la pausa delle prove un agente `explore` di sola lettura ha verificato C-38, i
> difetti 2 e 5 del PAC e C-62 sul codice di oggi, cioè dopo il taglio di Y2. Ho ricontrollato io i punti dubbi.
> - **C-38 e difetto 2**: `@media (max-width: 768px) { .th-actions, .td-actions { position: static } }`
>   (`table/DataTable.svelte:1693-1699`) sblocca solo il corpo. `thead.sticky-header th` (0,1,2, `:1280-1285`) batte
>   `.th-actions` (0,1,0): su un telefono «Azioni» resta fissata a destra (`:1324-1326`) mentre i ⋮ scorrono via.
> - **Difetto 5**: in `TargetsStep.svelte:111-134` le larghezze minime, con la selezione (48 px) e le azioni (64 px),
>   passano i 500 px. La colonna di selezione è fissata a sinistra a ogni larghezza (`:1314`, `:1548`) e copre
>   l'inizio dei nomi.
> - **C-62**:
>   - la larghezza trascinata va solo nello `width` inline del `th` (`:983`; maniglia in
>     `DataTableColumnHeader.svelte:175`, gestori in `DataTable.svelte:688-719`, solo eventi del mouse);
>   - con `tableLayout="auto"`, 11 tabelle, è un suggerimento. È provata solo la L1° del Lab, che è `fixed`;
>   - la causa «`onColumnResize` non letto» della wiki è sbagliata.
> - **La spec `designer-lab-picker`** confronta le occorrenze dello scanner con i candidati dell'ancora, entrambi
>   calcolati a runtime: un cambio dei numeri di riga di `DataTable.svelte` non la rompe.
> - **Colori**: 0 classi di palette in `DataTable.svelte`; gli sfondi fissi vengono da `--lf-cmp-datatable-*`.
> - **Annuncio al coordinatore** (`needs_input`), con le decisioni proposte:
>   - D-Y17 (UX): sotto i 768 px la selezione e le azioni scorrono con la tabella, intestazione e corpo insieme;
>     l'intestazione resta fissa in alto. L'alternativa: le azioni fissate a destra anche sul telefono;
>   - D-Y18 (C-62): prima un rosso E2E su una tabella auto; poi il `min-width` dalla larghezza trascinata, e le
>     maniglie ai Pointer Events.
>   - Il layout del PAC da telefono resta fuori da Y7, come vuole la decisione 50.
> - **Codice**: solo dopo le E2E di Y8, che costruiscono il frontend da questo worktree, e dopo il via del
>   coordinatore.

### Y8 — ingresso ✅ (2026-10-15, ~21:25)

> **Note implementazione**: Y8 è entrato in `dev_release2` = `160562b56`, con i registri in `f98c20f1b`. Le righe del
> CHANGELOG c'erano già dal commit di Y8. Il coordinatore ha portato il worktree a `f98c20f1b` con un avanzamento
> veloce; restava fuori solo la mia modifica al piano, con il verdetto di Z sui 3 rossi. La galleria d'ingresso di Y8
> resta dentro G-13: G manderà gli scatti di Dashboard, Brokers, Assets e FX da rivedere.

### Y7 — avvio e rossi ⏳ (2026-10-15, 21:25–)

> **Note implementazione**:
> - **Via**: coordinatore 20:52 (D-Y17, D-Y18) e 21:25 («prima i rossi, con test-author»); colori 20:53.
>   - Le condizioni dei colori: `theme-roles --check` pulito nell'handoff, e la riga `~split` di `DataTable` invariata.
>   - La galleria d'ingresso è solo mobile, nel loro slot dopo G-13, e confrontata con il riferimento di G-13.
>   - G-13 aspetta l'ingresso di T: se slitta a domani, slitta anche questa galleria.
> - **Base**: `f98c20f1b`. Lo slot pesante si richiede per le E2E di Y7.
> - **Rossi**: `test-author` in background. Scrive due spec nuove in `frontend/e2e/layout/`, senza lanciarle:
>   - telefono, D-Y17: la tabella delle transazioni a 390 px;
>   - ridimensionamento su una tabella `layout-auto`, D-Y18.
>   Le righe del runner (`_frontend_utility.py`, del programma colori) le propone a me: vanno al coordinatore per il
>   via (D-Y6).
> - **Filtro della galleria mobile** (`-f`, arriva a Playwright come `-g`, sui titoli di `gallery.spec.ts`), preparato
>   per il checkpoint:
>   `PAC allocator steps|transaction list|dashboard transactions tab|(dashboard|broker) (positions tab|fifo lots panel)|Asset list table|FX list table|static resources tab|broker reports tab`
>   - copre PAC targets e review, le transazioni (pagina e scheda della Dashboard), le posizioni e i lotti (Dashboard e
>     broker), gli asset e i cambi in tabella, i file;
>   - altre tabelle con la colonna delle azioni, da aggiungere se il coordinatore dei colori vuole coprirle tutte:
>     `PAC allocator result|report set|import wizard step|import bulk staging|data editor|dashboard risk diversification`.
> - **Spec scritte** da `test-author`, nessuna lanciata. `prettier` è pulito, e `playwright test --list` dà 8 test in 2
>   file sul progetto desktop.
>   - `frontend/e2e/layout/datatable-mobile.spec.ts` (D-Y17), a 390×844, sola lettura su dati di popolamento. Due
>     ospiti: Transazioni e la lista dei file statici. Su ognuno tre test: le azioni scorrono con la tabella; la
>     selezione esce con la tabella; la guardia sull'intestazione fissa in alto, in un'area di scorrimento limitata.
>   - `frontend/e2e/layout/datatable-resize.spec.ts` (D-Y18), a 1280×720. Due trascinamenti, +80 e −40 px (±4), sulla
>     colonna «File name» dei file statici (`tableLayout="auto"`). Il controllo: gli stessi trascinamenti sulla
>     colonna Date delle transazioni (layout fisso).
> - **Tre scoperte di `test-author`**, verificate sul codice:
>   - `TransactionsTable` passa `stickyActions={false}` (`:1010`): lì l'intestazione «Azioni» è già giusta, e il test
>     delle azioni è verde. Il rosso di C-38 sta sui file: `FilesTable` ha le azioni fisse di default e la selezione
>     multipla, ed è lo stesso caso del difetto 2 del PAC;
>   - un'intestazione fissa a livello di pagina oggi non esiste. `overflow-x: auto` del contenitore rende anche
>     `overflow-y` `auto`, quindi l'intestazione resta ferma solo dentro il contenitore. D-Y17 vuol dire tenere questo
>     comportamento, ed è ciò che la guardia controlla;
>   - `startResize` parte dalla larghezza configurata (250), non da quella disegnata. Sulla tabella auto la stima è
>     che la colonna si muova di circa due terzi del trascinamento.
> - **Preparazione** (nessun cambio di comportamento): 5 `data-testid` in `table/DataTable.svelte`:
>   - `dt-scroll` sul contenitore;
>   - `dt-select-header` e `dt-actions-header` sulle intestazioni;
>   - `dt-select-cell-{rowId}` e `dt-actions-cell-{rowId}` sulle celle.
>   Nessuno usa i prefissi che altre spec enumerano. Dopo l'aggiunta: i 6 file Vitest della tabella verdi (241 test),
>   `htmlSink` 7, `themeRoles` 36, `themeComponentTokens` 18; `theme-roles --check` pulito; Prettier pulito.
> - **In corso**: `test-author` aggiunge il rosso del trascinamento col dito (CDP `Input.dispatchTouchEvent`), perché
>   D-Y18 porta le maniglie ai Pointer Events.
> - **Poi**: le righe del runner in `_frontend_utility.py` al coordinatore, che dà il via (D-Y6); lo slot; i rossi
>   lanciati sul codice di oggi.
> - **Rosso del dito** (secondo giro di `test-author`): `datatable-resize.spec.ts:297`, «with a finger, on a phone».
>   - A 390×844, con `isMobile` e `hasTouch`, un trascinamento di +60 px dalla maniglia della colonna Date delle
>     transazioni (CDP `Input.dispatchTouchEvent`), con tolleranza ±4.
>   - È su una tabella fissa perché a 390 px la tabella auto dei file disegna ogni colonna al minimo, e nessun
>     trascinamento la sposta: il test è sul percorso dell'input, non sul layout.
>   - Rosso oggi: la maniglia ascolta solo `mousedown`, e un dito che scorre non lo manda.
>   - Per la correzione serve `touch-action: none` sulla maniglia.
> - **Totale**: 9 test sul progetto desktop, 6 della spec del telefono e 3 di quella del ridimensionamento.
> - **Righe del runner proposte al coordinatore** (`scripts/test_runner/_frontend_utility.py`, D-Y6):
>   - le funzioni vanno dopo `front_docs_offline_math`, sul modello dei vicini: `front_datatable_mobile` e
>     `front_datatable_resize`, con `_ensure_frontend_build`, `_ensure_db_populated` e `_ensure_test_users`, poi
>     `_run_playwright("layout/<spec>")`;
>   - gli `add_test` vanno dopo quello di `docs-offline-math`:
>     - `"datatable-mobile"`, «DataTable Mobile Pinned Columns». Desc: «At 390 px, read-only on seeded data, on
>       Transactions (stickyActions false) and the Files static list (sticky actions): scrolled half an actions cell
>       short of the far right, the actions header sits over its row's actions cell and both end with the table; the
>       selection header and cell have scrolled out past the scroll area's left edge; and, the scroll area bounded to
>       the header and two rows and scrolled down, every header cell stays on its top while the body passes under
>       (Y7, D-Y17; needs the dt-scroll / dt-select-* / dt-actions-* test ids)»;
>     - `"datatable-resize"`, «DataTable Column Resize». Desc: «Read-only on seeded data. At 1280 px, on the Files
>       static list (tableLayout auto): a mouse drag of the File name column's resize handle (found by cursor:
>       col-resize under the title cell's right edge, pressed at its centre) by +80 px then -40 px changes the title
>       cell's drawn width by as much, ±4 px; control: the same drags on the Transactions Date column (fixed layout,
>       table wider than its dt-scroll area). At 390 x 844 with isMobile and hasTouch: a finger drag of +60 px from
>       the Date handle's centre (Chromium CDP Input.dispatchTouchEvent: touchStart, touchMove in 6 steps, touchEnd)
>       changes its drawn width by 60 ±4 px; on the fixed table, because at 390 px the auto-layout Files table is wider
>       than its box and draws every column at its minimum, which no drag moves (Y7, C-62, D-Y18)»;
>     - entrambi con `prereq="Populated DB + test users"` e `tests=` sulla propria spec.
> - **Richiesti al coordinatore** (21:5x): il via sulle righe e uno slot per i rossi.
> - **Via del coordinatore** (22:10):
>   - le righe del runner, come descritte e solo in aggiunta; le dichiara lui ai colori;
>   - le tre scoperte nel piano;
>   - `touch-action: none` e la larghezza disegnata come punto di partenza entrano nella cura;
>   - lo slot: dopo i due `core-unit` di A ed E, `datatable-mobile` poi `datatable-resize`, una alla volta, con
>     `nice -n 10` e il carico sotto 70.
> - **Registrazione fatta** in `scripts/test_runner/_frontend_utility.py`: le funzioni `front_datatable_mobile` e
>   `front_datatable_resize` dopo `front_docs_offline_math`, e i due `add_test` dopo `docs-offline-math`.
>   - `git diff --numstat` dà 42 righe aggiunte e 0 tolte; `py_compile`, `ruff check` e `ruff format --check` sono
>     puliti;
>   - il registro `front-utility` contiene `datatable-mobile` e `datatable-resize`, con la propria spec e
>     `in_all` vero.
> - **Rossi visti** sul codice di oggi (`f98c20f1b` più i `data-testid`), nello slot 2 dalle 22:20, `--workers 2`,
>   `nice -n 10`. Il log è nella cartella di sessione, `files/y7_red_01_datatable-mobile.log`.
>   - `front-utility datatable-mobile`: 3 rossi e 3 verdi, come atteso:
>     - ✘ Transazioni, la selezione esce con la tabella (`:323`);
>     - ✘ file statici, le azioni scorrono con la tabella (`:311`);
>     - ✘ file statici, la selezione esce con la tabella (`:323`);
>     - ✔ Transazioni, le azioni (`stickyActions={false}`), e le due guardie sull'intestazione fissa.
>
> **Fuori pista**: alle 22:28 il coordinatore ha fermato le prove pesanti per 10 minuti, per una galleria di T.
> - Il mio script aspettava che il carico scendesse sotto 70, e ha lanciato `datatable-resize` alle 22:28:32, 4 secondi
>   dopo il messaggio.
> - L'ho fermata dopo 2 secondi, ancora nella preparazione, con un SIGINT al solo runner, e ho fermato il ciclo. Nessun
>   processo rimasto, porta libera.
> - La cura resta ferma finché non vedo i rossi di `datatable-resize` sul codice di oggi.
> - **Cambio di piano dei colori** (coordinatore, 22:29): T (la palette) e DV (i colori dei grafici) entrano insieme,
>   dopo un'unica revisione del developer. Y3, Y4b, Y9 e Y10 aspettano quell'ingresso, e lo segnala il coordinatore;
>   il quando dipende dal developer. Y7 non ne dipende e va avanti.
> - **Regola dei test**, valida dall'ingresso di T e DV (coordinatore, 22:29): con T-7 l'header dell'app si blocca solo
>   con il focus da tastiera (`:focus-visible`).
>   - Un test che vuole l'header fermo usa l'aiuto `focusHeaderControlByKeyboard` (`e2e/fixtures/`, arriva con T), non
>     `toggle.focus()`.
>   - Le due spec di Y7 non ne dipendono: nessun `.focus()` e nessun header dell'app. Riguarda l'intestazione della
>     pagina, non quella delle tabelle.
> - **Rossi di `datatable-resize`** (22:32, ripresa): 2 rossi e 1 verde.
>   - ✘ mouse sulla tabella auto dei file: +80 px → +57,0 (279,6 → 336,5); −40 → −27,2;
>   - ✘ dito, +60 px sulla Date delle transazioni a 390 px → +0,0 (110,0 → 110,0);
>   - ✔ il controllo a layout fisso.

### Y7 — passo 2, la cura ✅ (2026-10-15, 22:35–22:44)

> **Note implementazione** (`table/DataTable.svelte`, `table/DataTableColumnHeader.svelte`):
> - **D-Y17**, la regola mobile (`@media (max-width: 768px)`):
>   - `.datatable .td-select`, `.datatable .td-actions` → `position: static`;
>   - `.datatable .th-select`, `.datatable .th-actions.th-fixed` → `left: auto; right: auto`. L'intestazione tiene
>     `position: sticky; top: 0`.
>   Ogni selettore è di una classe più specifico del vincolo che toglie. Le celle del piede sono coperte dalle stesse
>   classi.
> - **D-Y18**, il ridimensionamento:
>   - la maniglia risponde a `onpointerdown`, con la cattura del puntatore, e il documento ascolta `pointermove`,
>     `pointerup` e `pointercancel`. Solo il tasto principale del mouse avvia il trascinamento;
>   - `touch-action: none` sulla maniglia;
>   - si parte dalla larghezza **disegnata** del `th`;
>   - `fitDrawnWidth()` scrive la larghezza sul `th`, la misura e la corregge finché quella disegnata non coincide con
>     il dito: prima scala di disegnata/data, poi fino a quattro passi secanti. Su una tabella fissa più larga del suo
>     box la prima stima è esatta;
>   - `columnMinWidth()` dà il `min-width` = la larghezza della colonna solo se l'utente l'ha ridimensionata, cioè se
>     differisce da quella predefinita; le altre tengono `minWidth || 60`;
>   - `onDestroy(endResize)` toglie gli ascoltatori se la tabella sparisce durante un trascinamento.
> - **Prove leggere**: Prettier pulito; i 6 file Vitest della tabella verdi (241); `htmlSink`, `themeRoles`,
>   `themeComponentTokens` verdi; `theme-roles --check` pulito, con la riga `~split` invariata; svelte-check 0/0.
>
> **Fuori pista**, due scostamenti dal disegno approvato (D-Y18):
> - **Il solo `min-width` non bastava.** Una tabella con spazio in avanzo, cioè auto o fissa più stretta del suo box,
>   divide l'avanzo in proporzione alle larghezze date. Allora un restringimento di 40 px avrebbe disegnato circa −30,
>   perché l'avanzo torna anche alla colonna trascinata. La larghezza scritta si corregge quindi sulla misura. Lo
>   scopo approvato resta: la colonna segue il trascinamento.
> - **Il `min-width` vale solo per le colonne ridimensionate.** `columnWidths` contiene sempre le larghezze
>   predefinite di tutte le colonne (`defaultColumnWidths`, caricate e reimpostate con quelle). Un «`min-width` = width»
>   per tutte avrebbe cambiato ogni tabella. Così le tabelle mai ridimensionate, e la galleria, restano identiche.
> - **Prettier** voleva spezzare l'attributo `style` dentro un'espressione: la logica è passata nell'aiuto
>   `columnMinWidth()`, e la riga è lunga come prima.

### Y7 — passo 4, E2E dopo la cura ✅ (2026-10-15, 22:44–23:28)

> **Note implementazione**: nello slot 2, `--workers 2`, `nice -n 10`, una spec alla volta, carico sotto 70:
> - 01 `front-utility datatable-mobile` 6/6; 02 `front-utility datatable-resize` 3/3; 03 `front-portfolio risk-lab`
>   44/44, che trascina la maniglia sulla tabella L1°;
> - 04 `front-portfolio risk` 38/38, anche questa con la maniglia; 05 `front-transaction transactions-table` 25/25.
>
> **Fuori pista**: alle ~22:53 il coordinatore ha annunciato una finestra tranquilla. Ho fermato il ciclo dopo
> `risk-lab`, uccidendo solo il bash del ciclo e lasciando finire la spec. Poi la finestra si è spostata a 00:00–01:15,
> per le schermate datate 16/10, e ho ripreso con 04–09.
> - **Seconda parte**, 22:57–23:12: 06 `front-designer-lab picker` 4/4; 07 `front-utility files` 28/28; 08
>   `front-asset asset-list` 28/28; 09 `front-fx fx-bulk` 7/7. Porta libera dopo ogni spec.
> - **Un test in più** (terzo giro di `test-author`). Su richiesta di `docs-writer`, che aveva notato i testi superati:
>   - i commenti delle due spec ora descrivono il contratto, con un paragrafo «Was (C-38 / C-62)» per il difetto, e
>     nessuna frase al presente sul codice che non c'è più;
>   - il test del dito ora guarda il solo percorso dell'input, sulla tabella fissa;
>   - nuovo test `datatable-resize.spec.ts:330`, «on a narrow screen»: a 390 px, sulla tabella auto dei file più
>     larga del suo box, +60 px allargano la colonna di 60 ± 4. Lo `scrollWidth` della tabella cresce allo stesso
>     modo, cioè le altre colonne non vengono schiacciate. Prima della cura era impossibile: lì la colonna restava
>     larga quanto il titolo.
> - **10 `front-utility datatable-resize` (23:26)**: 4/4.

### Y7 — passo 5, documentazione ✅ (2026-10-15, 23:00–23:30)

> **Note implementazione**:
> - **`docs-writer`**, `mkdocs_src/docs/developer/frontend/components/core-ui/data-table.md` (il percorso giusto ha
>   `components/`), +92/−17 righe:
>   - Features, Props (`tableLayout`, `stickyActions`, `enableColumnResize`, `onColumnResize`, `stickyHeader`) e
>     ColumnDef (`width`, `minWidth`, `maxWidth`, `pinned`);
>   - «Sticky columns» riscritta: l'intestazione resta fissa dentro `dt-scroll`, mai sulla pagina; la regola del
>     telefono; i test id; la nota sulla specificità;
>   - una sezione nuova, «Column resize» `{: #column-resize }`;
>   - corrette due frasi vecchie: «sticks to the top of the vertical scroll viewport» e «at 768 px and below the
>     actions column never sticks».
>   Nessuna pagina utente lo contraddice; `user/assets/index.en.md:54` resta vera.
> - **Mia aggiunta**: il paragrafo finale di «Column resize» nomina il test sullo schermo stretto.
> - **Runner**: la `desc` di `datatable-resize` dice ora il contratto e il nuovo test, al posto di «which no drag
>   moves». È la stessa riga aggiunta da me: 42 righe aggiunte e 0 tolte, `ruff` pulito.
> - **`mkdocs build`** strict: rc 0, 0 righe WARNING/ERROR, 3060 URL. **`check-links`**: 96 validi.
> - **devWiki**:
>   - `problems/datatable-actions-column-on-mobile`: risolta, con la causa confermata e la cura;
>   - `problems/datatable-column-resize-noop`: risolta; la causa sbagliata sostituita da quella misurata, con la cura
>     e la prevenzione;
>   - due righe dell'indice e una voce del log;
>   - `check_source_paths.py` dà 5 mancanti, preesistenti.
> - **Backlog, sezione Y**: Y-9 (il layout del PAC da telefono, da rivedere sugli scatti mobile, per la decisione 50) e
>   Y-10 (la maniglia invisibile su un telefono).

### Y7 — checkpoint 🧊 FROZEN (2026-10-15, 23:35)

> **Note implementazione**:
> - **Stato**: HEAD `f98c20f1b`, nessun server, porta 6189 libera; slot 2 da liberare con l'handoff.
> - **Controlli puliti**: `theme-roles --check` (la riga `~split` di `DataTable` non cambia), Prettier,
>   `git diff --check`.
> - **Nel messaggio al coordinatore**: le righe del CHANGELOG (non scritte nel file, per la sua regola) e il filtro
>   della galleria mobile.

### Y7 — commit e revisione combinata con T+DV ✅ (2026-10-15, 23:34–23:48)

> **Note implementazione**:
> - **Commit del coordinatore**: `ca681b4f9` (codice) e `8d4719c21` (journal). Merge di `dev_release2` (`4ef2fc199`,
>   che contiene T+DV) in `94a8b4a7e`, senza conflitti: backlog e `_frontend_utility.py` si sono uniti da soli.
> - **Prove sulla revisione combinata**, una alla volta, `nice`, carico sotto 70, tutte finite prima della finestra
>   di G-13 (00:00–01:15):
>   - `api sync`: nessun cambio tracciato;
>   - svelte-check: 0 errori, 0 avvisi;
>   - `theme-roles --check`: pulito;
>   - E2E: `datatable-mobile` 6/6, `datatable-resize` 4/4, `transactions-table` 25/25, `files` 28/28.
> - **Ingresso di Y7**: dopo la fine di G-13, così il riferimento della galleria resta quello di prima. Dopo le 01:15
>   tocca alla galleria mobile filtrata (il filtro è nel checkpoint), confrontata con il riferimento di G-13.
> - **Regola del CHANGELOG** confermata: le righe vanno nel messaggio. La `desc` cambiata del runner l'ha dichiarata
>   il coordinatore ai colori.
> - **Nota per Y10** (coordinatore, 23:34): T farà TD-3, cioè sfondi e pulsanti della card «Allocazione
>   Patrimoniale» sui ruoli, in `AllocationPanel.svelte`, dopo l'ingresso di T+DV e il suo lotto W3-a. Fino a TD-3
>   quel file non si tocca; Y10 partirà da una base che lo contiene.

### Prossimo lotto — proposta Y4b ⏳ (2026-10-15, 23:50)

> **Note implementazione**: il coordinatore mi ha lasciato scegliere fra Y3, Y4b e Y9, chiedendo prima l'elenco dei
> file per i colori.
> - **Ordine proposto**:
>   - Y4b subito;
>   - Y3 dopo TD-1 e TD-1b, che toccano `GrowthChart.svelte`, `growthChartSeries.ts`, `GrowthChart.test.ts` e
>     `KpiSection.svelte` (verso le 01:30);
>   - Y9 dopo gli spostamenti, perché modifica circa 35 file di grafici e va fatto sui percorsi definitivi.
> - **Y4b su `94a8b4a7e`**: 103 file vanno in `frontend/src/lib/features/risk/`, che oggi non esiste. Forma piatta
>   (D-Y13), nessuna collisione di nomi:
>   - 47 da `components/risk/`, 4 da `lib/risk/` e 6 da `stores/risk/` alla radice;
>   - 46 in `levels/`, `levels/l1/` e `levels/l4/`.
>   - 5 importatori esterni: la Dashboard, il dettaglio broker, le due pagine degli asset (area di X) e
>     `AssetPickerPanel.test.ts`.
>   - **Stringhe di percorso**: `RiskCardGrid` e il suo test, `assetPicker.ts`, `catalogIcuLocale.test.ts`,
>     `moneyRenderSites.test.ts`.
>   - **Programma colori**: `scan-colors.mjs:193`, `scanColors.test.ts` e il baseline.
>   - **Runner**: `_frontend_portfolio.py`, `_frontend_utility.py` e `coverage_js.py`.
>   - **Backend**: `test_risk_schemas.py` e `test_i18n_usage_gate.py`.
>   - **Testi**: `backend-risk.instructions.md:19`, `TODO_FUTURI.md`, 5 pagine MkDocs e circa 27 della devWiki.
> - **Tempi proposti**: gli script di spostamento e di riscrittura degli import si preparano durante la finestra di
>   G-13, senza applicarli. Si applicano dopo la galleria mobile di Y7, che si costruisce da questo worktree.
> - **In attesa**: il via del coordinatore e dei colori sulla lista.
> - **Via di Y4b** (coordinatore, 23:5x), con l'ordine Y4b, poi Y3 dopo TD-1b, poi Y9. Le asset pages di X: una riga
>   di import si fonde senza problemi; lo avvisa il coordinatore.
> - **Risposte dei colori**:
>   1. stanotte nessun loro lotto tocca `components/risk/**`, `lib/risk/` o `stores/risk/`;
>   2. `scan-colors.mjs` e `scanColors.test.ts` li scrive L, che aggiunge `features/risk` accanto a `components/risk`,
>      e così funziona in qualunque ordine;
>   3. il baseline lo scrivo io, ma solo con `theme-roles.mjs` (R4 accoppia le righe rinominate), mai a mano.
>      Nell'handoff: `--check` pulito e le righe `~` verificate;
>   4. i percorsi del runner li scrivo io.

### Y4b — preparazione degli script ✅ (2026-10-15, 23:50–00:00, niente applicato)

> **Note implementazione**: gli script sono nella cartella di sessione, con prove a secco, sola lettura, worktree
> intatto.
> - **`files/y4b_move.py`**: 103 spostamenti con `mv` semplice, non `git mv`: il Git policy vieta lo stage, e lo stage
>   lo fa il coordinatore.
>   - riscrive 148 specificatori in 68 file: gli spostati più le 4 pagine `routes/(app)/{dashboard,brokers/[id],assets,
>     assets/[id]}`;
>   - ogni specificatore si risolve dalla posizione vecchia, passa per la mappa degli spostamenti e si riscrive dalla
>     posizione nuova, con lo stile `$lib/` o relativo, il suffisso implicito e `?raw` conservati;
>   - legge anche `vi.mock` e `new URL(…, import.meta.url)`.
> - **`files/y4b_paths.py`**: 323 sostituzioni di percorsi in 110 file di testo: runner, `coverage_js.py`,
>   `test_risk_schemas.py`, istruzioni, `TODO_FUTURI.md`, 5 pagine MkDocs, 24 pagine della devWiki, commenti e test
>   con chiavi di percorso. Si lancia dopo lo spostamento.
> - **Lasciati fuori di proposito**:
>   - il journal, la devWiki `sources/` e `log.md`: sono cronache;
>   - `scan-colors.mjs`, `scanColors.test.ts` e `designer-lab.md:448`, che descrive lo scanner: tutti di L;
>   - il baseline, che si scrive solo con lo strumento;
>   - `test_i18n_usage_gate.py`: alberi sintetici, quindi dati di test;
>   - `AssetPickerPanel.test.ts`: le sue stringhe a forma di import alla riga 1517 sono dati del test di confine
>     «ui/select imports nothing from components/risk/». Va a `test-author`, con l'import vero alla riga 47.
>
> **Fuori pista**:
> - la prima regex dei letterali prendeva anche gli URL `/api/v1/risk/…` (89 righe), e l'ho ristretta ai percorsi di
>   cartella (15 righe);
> - la prima riscrittura avrebbe toccato le stringhe di test di `AssetPickerPanel.test.ts`, e ho aggiunto un elenco a
>   mano.
>
> **Ordine di applicazione**, dopo la galleria mobile di Y7:
> 1. `y4b_move.py --apply`;
> 2. `y4b_paths.py --apply`;
> 3. `theme-roles.mjs --check`, poi `--update` per i nomi nuovi, solo se non ci sono cali in file d'altri;
> 4. `test-author` per `AssetPickerPanel.test.ts`;
> 5. le prove: svelte-check, Vitest del rischio e i gate, `test_risk_schemas.py`, knip, `theme-roles --check`,
>    `mkdocs build` e `check-links`, `check_source_paths.py`; con lo slot, le E2E del rischio.

### Y3 — preparazione degli script ✅ (2026-10-16, 00:00–00:10, niente applicato; entra dopo TD-1b)

> **Note implementazione**: gli script sono derivati da quelli di Y4b, con la sola mappa degli spostamenti diversa.
> - **`files/y3_move.py`**: 35 spostamenti in `lib/features/dashboard/`, a radice piatta:
>   - i 32 file di `components/dashboard/`, senza sottocartelle;
>   - `stores/portfolio/dashboardViewStore.ts` con il suo test;
>   - `stores/dateRangeController.svelte.ts`.
>   I due store li importa solo la pagina della Dashboard. Le riscritture sono 42 specificatori in 8 file: gli
>   spostati, `chartCoreHelpers.test.ts` (D-Y16: solo i percorsi), `AssetRiskScenariosView` e `RiskAnalysisPanel`, e
>   le pagine della Dashboard e del dettaglio broker.
> - **`files/y3_paths.py`**: 87 sostituzioni in 34 file. Comprende il runner (`_frontend_asset.py` di X,
>   `_frontend_portfolio.py`, `_frontend_utility.py`), `themeModeReads.gate.test.ts` e `moneyRenderSites.test.ts`, che
>   hanno chiavi di percorso, `charts.md` e 16 pagine della devWiki.
> - **Lasciati fuori**:
>   - `pickView.test.ts` e `scanColors.test.ts` del Lab, di L;
>   - la pagina `designer-lab/picker.md`;
>   - `KpiDivergingFlowBar.test.ts` e `KpiMetricBar.test.ts`: «promoted out of `components/dashboard/`» è storia;
>   - la cronaca e il baseline, come in Y4b.
> - Gli script leggono lo stato dell'albero, quindi l'ordine con Y4b è indifferente.

### Y11 — analisi (C-85, decisione 48) ✅ (2026-10-16, 00:00–00:10, sola lettura, agente `explore`)

> **Note implementazione**:
> - **Nessun pulsante «Aggiorna» globale**: l'header dell'app (`layout/Header.svelte`) non ne ha. Ogni pagina ha il
>   suo, nella propria barra:
>   - la Dashboard `sync-button` (`:968`), i broker `brokers-refresh` (`:371`), il dettaglio broker
>     `broker-refresh` (`:604`);
>   - la lista FX `fx-refresh-all-button` (`:1102`), il dettaglio FX `fx-detail-refresh-btn` (`:1319`);
>   - la lista asset (`:1611`), il dettaglio asset `asset-detail-refresh-btn` (`:2878`);
>   - le transazioni `tx-refresh-button` (`:740`), i file `files-refresh-button` (`:724`).
>   Ognuno gira solo con il proprio flag locale. La Dashboard gira solo mentre è premuto: un cambio di periodo o una
>   rivalidazione della cache non lo fanno girare. FX e asset in lista non hanno `disabled`, quindi non diventano
>   grigi.
> - **Nessun meccanismo comune**: nessun contatore di richieste nel client API, nessuno store «busy».
> - **I pollers** (`startActivePolling`: lista asset `:461`, dettaglio asset `:1512`) non mostrano niente.
>   «Aggiornamento in pausa» (`live-updates/LiveUpdatesStatus.svelte`) sta nell'intestazione della pagina, non accanto
>   al pulsante.
> - **Pulsanti nei pannelli**:
>   - `RiskPanelHeader.svelte:100` e `RiskAnalysisPanel.svelte:601` (`risk-refresh-button`): un aggiornamento
>     semplice, da togliere;
>   - i loro `risk-sync-button` aprono la sincronizzazione prezzi e FX: è un'altra azione, e resta;
>   - restano anche le azioni per riga o per selezione, `ChartSignalsSection`, i modali e i pannelli di Impostazioni e
>     Tools, che non hanno un pulsante di pagina.
> - **Test che fissano l'oggi**: `dashboard-cache.spec.ts` (clic su `sync-button`, attesa di `data-busy`), le spec del
>   rischio (`risk-refresh-button`), `asset-live-pause.spec.ts`, i Vitest di `LiveUpdatesStatus` e `activePolling`.
> - **Decisione notturna, da rivedere** (tecnica, nel mio perimetro): uno store `pageBusy` con `begin()` che dà un
>   gettone e `end(gettone)`, azzerato alla navigazione.
>   - Ogni pagina avvolge i suoi ricaricamenti: periodo, filtri, rivalidazione della cache, `loadBase`; i pollers
>     passano da un aggancio facoltativo di `startActivePolling`.
>   - Il pulsante della pagina gira e diventa grigio con `busy` o con la pressione.
>   - Il pulsante resta nella pagina che lo disegna, cambia solo l'espressione: niente componente nuovo, che dovrebbe
>     usare solo i ruoli `*-lf-*` e sposterebbe le classi di palette.
> - **Domanda al developer**, mandata al coordinatore secondo la regola della notte:
>   - «la barra in cima» va letta come la barra di ogni pagina;
>   - le due rimozioni nei pannelli del rischio;
>   - se i pollers dal vivo, ogni 30 s, debbano far girare il pulsante.

### Y9 — analisi (K-15, C-34, K-13) ✅ (2026-10-16, 00:10–00:20, sola lettura, agente `explore`)

> **Note implementazione**, sul codice dopo T+DV:
> - **K-15**: quasi tutti i formatter a funzione escapano già, nei costruttori locali e in `growthChartTooltip`,
>   `exposureTooltip`, `signalLabelToHtml`, `buildTooltipTopN` e `buildTooltipByThreshold`. Restano tre buchi:
>   - `charts/AllocationPieChart.svelte:455/472-477`: `translated`, cioè caption o nome dai dati, e `parentLabel`, che
>     ricade sulla chiave grezza;
>   - `charts/CandlestickChart.svelte:522/524`: il codice valuta e la bandiera nell'intestazione;
>   - `charts/PriceChartFull.svelte:1013`: la bandiera.
> - **Correzione alla wiki**: `htmlInterpolation.gate` vede anche i formatter, ma solo per i nomi con un suffisso di
>   `TEXT_SUFFIXES` (`:171`); `HTML_FIRST_ARGUMENT` (`:221`) tratta come HTML il primo argomento dei costruttori di
>   riga. Per questo i tre buchi passano. `htmlSink.gate` invece non vede i formatter.
> - **C-34**: `risk/CorrelationHeatmap.svelte:351-353` escapa `& < >` ma non `"` e `'`; `utils/core/escapeHtml.ts`
>   escapa tutti e cinque. `utils/inlineMath.ts:14` resta: lascia `'` per KaTeX, ed è voluto. Altre copie locali non ce
>   ne sono.
> - **K-13**: nessun file di grafico e nessun `lib/theme/*` imposta `fontFamily`, quindi il testo su canvas usa
>   `sans-serif`, senza 'LF Flags'.
>   - Testo su canvas con bandiere: la legenda e le serie di `FxPairSignal.ts:98-100`, le etichette della mappa
>     (`geographyMapHelpers.ts:140-146`), l'emoji in area di `AllocationHistoryChart.svelte:698`, la legenda e le
>     etichette di `AllocationPieChart` (`:353`, `:546`).
>   - Gli `echarts.init` sono 16 componenti più 2 del PAC (`LotGanttChart` ne ha due).
>   - `flagFont.gate` legge solo le pile CSS, non le opzioni di ECharts.
> - **Proposte**, da approvare con l'elenco dei file:
>   - K-15: escapare i tre punti, e aggiungere al gate i suffissi o una lista di nomi ammessi per i template restituiti
>     da un `formatter`;
>   - C-34: importare `escapeHtml`, e un gate che rifiuti un `escapeHtml` locale fuori da `escapeHtml.ts` e
>     `inlineMath.ts`;
>   - K-13: una costante `CHART_FONT_FAMILY` con 'LF Flags' in testa, come `textStyle.fontFamily` globale, e un gate
>     sugli `echarts.init`.
> - **Rischio da verificare in K-13**: il canvas disegna una volta sola. 'LF Flags', caricato con `@font-face` e
>   `unicode-range`, deve essere già caricato al disegno, altrimenti la bandiera esce con il ripiego fino al disegno
>   dopo. Forse serve `document.fonts.load()` prima del primo `setOption`, o un ridisegno a `document.fonts.ready`.
> - **Ordine**: Y9 dopo Y4b e Y3, così i percorsi sono quelli definitivi. `lib/theme/chartTheme.ts` è nell'area del
>   programma colori: va nell'elenco dei file per loro.

### Ingresso di T+DV (2026-10-16, ~00:00, informazione del coordinatore)

> **Note implementazione**: T+DV è entrato in `dev_release2` (`a0915bef9`).
> - Nei file di Y ha toccato `components/risk/stressBucketLabel.ts` (DV-6), che è nel lotto di Y4b.
> - Ha cambiato `e2e/portfolio/dashboard.spec.ts` e `privacy-masking.spec.ts`, e ha aggiunto
>   `e2e/fixtures/headerKeyboardFocus.ts`: per il focus da tastiera nell'intestazione si usa quello, non `focus()`.
> - Al prossimo checkpoint il coordinatore aggiorna la base; dopo serve `api sync` (`SectorListResponse`).
> - Y3, Y4b, Y9 e Y10 sono sbloccati, nel mio ordine dopo Y7. Per Y10 vale la nota su TD-3.
>
> **Decisione notturna, da rivedere**: Y4b si applica solo su una base che contiene `a0915bef9`, cioè dopo
> l'ingresso di Y7 e l'aggiornamento della base. Così lo spostamento parte dal `stressBucketLabel.ts` di DV-6, invece
> di unire un file modificato su un file spostato.

### Y5 — preparazione degli script ✅ (2026-10-16, 00:05–00:25, niente applicato)

> **Note implementazione**: richiesta del coordinatore per la finestra di G-13. Y5 entra dopo CP-16 di J, verso
> l'01:00, e dopo il ritocco di T su `LotCustodyModal.svelte`.
> - **`files/y5_move.py`**: 40 spostamenti; 52 specificatori riscritti in 28 file.
>   - 11 file in `features/brokers/`;
>   - 27 in `features/brokers/lots/`: i 25 di `lots/` e `lotsAnalysisStore` con il suo test, che importa solo
>     `LotsAnalysisPanel`;
>   - 2 in `components/ui/display/` (`BrokerIcon` e il suo test).
>   Fuori dal lotto: le transazioni (W), il PAC, `ui/`, `AssetSetRiskPanel`, 4 pagine, `chartCoreHelpers.test.ts`,
>   un harness e `e2e/brokers/brokers-detail.spec.ts`.
> - **`files/y5_paths.py`**: circa 100 percorsi in 58 file: il runner (`_frontend_broker.py`,
>   `_frontend_portfolio.py`, `_frontend_utility.py`), `moneyRenderSites.test.ts`, 3 pagine MkDocs e 23 della devWiki.
> - **Lasciati fuori**: come Y3; in più `frontend/scripts/theme/theme-roles.mjs:70`, un'eccezione con chiave sul
>   percorso di `lotComparisonChartHelpers.ts` che aggiornano i colori, e `frontend/design/REPORT.md:78`, che è
>   storia.
> - **Decisione notturna, da rivedere**: `BrokerIcon` va in `components/ui/display/`, accanto a `BrokerBadge`, e non
>   nella feature. Ha 17 importatori fra transazioni, PAC e `ui/`, che altrimenti dipenderebbero da
>   `features/brokers`.
> - `stores/reference/brokerStore.ts` resta dov'è: è un dato di riferimento letto da 30 file (D-Y5).
> - **Per i colori**, girato al coordinatore: `theme-roles.mjs:70`; e lo scanner di L, `CHART_PATH_RE`, che deve
>   imparare anche `features/dashboard` e `features/brokers/lots`.
> - **Y9, risposte dei colori** (coordinatore, 00:06):
>   - `chartTheme.ts` lo scrivo io, ma dopo l'ingresso di TD-1 di DV, verso le 01:45–02:00, che tocca `chartTheme.ts`,
>     `ExposureBars.svelte` e `GrowthChart.svelte`;
>   - i componenti di grafico non sono in nessuna loro ondata stanotte;
>   - i gate nuovi non toccano i loro.
>   L'ordine Y4b, Y3, Y9 rispetta già questi tempi.

### Y6 — preparazione degli script ✅ (2026-10-16, 00:10–00:20, niente applicato; dopo CP-U2 di H)

> **Note implementazione**: richiesta del coordinatore. H sta rifacendo `components/files/` per CP-U2, quindi gli
> script calcolano spostamenti e riscritture dall'albero al momento dell'applicazione.
> - **`files/y6_move.py`**: 6 spostamenti, tutto `components/files/*` in `features/files/`. 8 specificatori in 5 file:
>   gli spostati, `BrokerImportFilesModal` (che con Y5 sarà in `features/brokers/`), `ImportWizardModal` (W),
>   `ui/media/AssetPickerModal` e la pagina `files`.
> - **`files/y6_paths.py`**: 21 percorsi in 14 file. Sono `htmlSink.gate.test.ts:70` (una chiave di percorso fra le
>   eccezioni), `_frontend_utility.py` (2 righe) e 7 pagine della devWiki.
> - **Restano dove sono**: `utils/files/*` e `stores/files/imagePreviewCache.ts`, utilità condivise lette da `ui/`,
>   broker e transazioni (D-Y5).
> - Nessuna riga dei colori. L'elenco è al coordinatore, per H e per i colori.

### Y10 — analisi (54-1, Y-6, decisione 49) ✅ (2026-10-16, 00:20–00:30, sola lettura, agente `explore`)

> **Note implementazione**, sul codice dopo T+DV:
> - **Il contratto dei dati va già bene**:
>   - `AllocationItem{name, value: percentuale 0-100, amount, emoji}` (`schemas/portfolio.py:75-81`);
>   - la liquidità è una riga «Liquidity» con il segno (`financial_math/portfolio/daily_state.py:720-721`), presente
>     nei tipi e nei settori, non nella geografia;
>   - le quote le calcola il backend sul totale netto (`derived_views.py:213-217`, `:239-243`).
>   Con liquidità negativa il backend manda già `value` e `amount` < 0, e le quote positive sommano più di 100. La
>   decisione 49 vuole esattamente questo, quindi niente backend e niente matematica nel frontend.
> - **Cosa taglia il negativo, solo nel frontend**:
>   - `dashboard/AllocationHistoryChart.svelte:777` ha `max: 100` fisso;
>   - i filtri del tooltip `> 0.01` a `:607`, `:610` (famiglie dei tipi) e `:750` (le altre dimensioni);
>   - `buildTooltipByThreshold` metterebbe una riga negativa nel «Remaining».
>   Lo stack (`:678`, `areaStyle` `:691`) usa il predefinito di ECharts 6, `stackStrategy: 'samesign'`: i negativi
>   scendono già sotto zero.
> - **La torta**: `AllocationPanel.svelte:64` toglie `v <= 0` e `AllocationPieChart.svelte:201` filtra `> 0`. Restano
>   tutti e due, perché la decisione tiene solo le quote positive. Uno spazio per la nota oggi non c'è.
> - **Y-6**: `emoji` è morto. Lo scrive `AllocationPanel.svelte:65`, lo dichiara il tipo a `:23`, e la torta prende le
>   emoji dei settori dallo store. Il campo `AllocationItem.emoji` del backend resta.
> - **Privacy**: la torta maschera gli importi con `formatCurrencyAmountPlain`; la storia mostra solo percentuali. La
>   nota «−X» deve passare dallo stesso formattatore e va registrata in `moneyRenderSites.test.ts`, che oggi non
>   registra questi file.
> - **Dati di test**: `populate_mock_data.py:312-336` dà a ogni broker `allow_cash_overdraft: False`, quindi nessun
>   portafoglio popolato ha liquidità negativa.
> - **Decisioni notturne, da rivedere** (tecniche, nel mio perimetro):
>   1. l'asse della storia ha `max` dai dati: 100, o la somma positiva più alta arrotondata in su. `min` va sotto zero
>      solo se c'è un negativo. È presentazione dell'asse, non matematica finanziaria;
>   2. `stackStrategy: 'samesign'` esplicito su ogni serie, per non dipendere dal predefinito;
>   3. i filtri del tooltip guardano il valore assoluto, e la riga negativa resta sempre in vista, fuori dal
>      «Remaining»;
>   4. la nota della torta è una didascalia sotto la torta in `AllocationPanel`, letta dalla riga «Liquidity» del
>      backend (`amount`). Chiave `dashboard.allocationNegativeCash`, «Negative cash: {amount}», nelle 4 lingue;
>      l'importo formattato e mascherato, con il «−» fuori dalla maschera (D8);
>   5. per i test: niente modifica al popolamento condiviso. I casi negativi vanno nei Vitest, con un riassunto finto,
>      e in un E2E con la risposta del riassunto intercettata. Nessun nuovo broker in scoperto nei dati comuni;
>   6. Y-6: tolgo `emoji` da `AllocEntry` e da `toAllocEntries`.
> - **Ordine**: Y10 parte dopo TD-3 dei colori su `AllocationPanel.svelte`, per la nota del coordinatore.

### Y10 — passo 1, rossi ✅ (2026-10-16, 00:15–00:40; il codice di prodotto dopo l'ingresso di Y7 e TD-3)

> **Note implementazione**: `test-author`, solo Vitest e in file nuovi e separati, così la galleria non cambia.
> Lanciati uno alla volta, con `nice`.
> - **`dashboard/AllocationHistoryChart.negativeCash.test.ts`**: 9 test, 7 rossi e 2 verdi (le guardie).
>   - I due tipi d'asse, `type` e `sector`: l'asse deve arrivare a 120 e scendere a −20. Rossi su `max: 100` (`:777`).
>     Il `min` è già assente, quindi segue i dati.
>   - `stackStrategy: 'samesign'` esplicito: rossi per tipo, settore e geografia.
>   - Il tooltip per tipo deve avere la voce `LIQUIDITY` negativa, e «Remaining» solo le famiglie positive lasciate
>     fuori: rosso, filtri a `:607` e `:610`.
>   - Il tooltip per settore: rosso, filtro a `:750`.
>   - Guardie: senza negativi l'asse va da 0 a 100, in tutti e due i tipi.
>   - Controlli positivi nei test del tooltip: la serie della liquidità è disegnata a −20, e il lettore riconosce una
>     riga negativa costruita da `buildTooltipRow`. Così il rosso viene dal grafico, non dal test.
> - **`dashboard/AllocationPanel.negativeCash.test.ts`**: 10 test, 5 rossi e 5 verdi (le guardie).
>   - Y-6, per tipo e per settore: rossi, perché le voci portano ancora `emoji` (`:65`).
>   - La nota `allocation-negative-cash-note` con −2000 scritto da `formatCurrencyAmountPlain`; mascherata in privacy
>     (`-••• € 🇪🇺 EUR`, il segno fuori dalla maschera, D8); che segue il cambio di privacy sul posto: rossi, la nota non
>     c'è.
>   - Guardie: solo quote positive alla torta, per tipo e per settore; nessuna nota con liquidità positiva, zero o
>     assente.
> - **Registrazione**: tutti e due i file sono in `allocation-unit` di `scripts/test_runner/_frontend_portfolio.py`, il
>   mio file del runner, e la `desc` è estesa. `check-orphans`: «All test files are registered». `ruff` dà 28 avvisi
>   (`E701`, `PLC0415`) e una riformattazione, uguali a quelli di HEAD: debito preesistente, non mio.
>
> **Decisioni notturne, da rivedere**:
> - `AllocationPanel.negativeCash.test.ts` è registrato in `allocation-unit`, il mio file, invece che accanto ad
>   `AllocationPanel.test.ts` in `front_component_unit` di `_frontend_utility.py`, che è del programma colori;
> - la nota va anche sotto la torta per settore, che ha la riga «Liquidity», e non sotto quella per geografia, che
>   non ce l'ha. Oggi i test la chiedono solo per tipo; il secondo caso si aggiunge con il prodotto;
> - le due descrizioni «0-100» non valgono più con liquidità negativa. Quella del commento di
>   `AllocationPieChart.svelte:53` la correggo io in Y10. Quella di `AllocationItem.value`
>   (`backend/app/schemas/portfolio.py:79`) è nell'area di J: la segnalo e non la tocco.

### Y5 — risposte dei colori (2026-10-16, 00:39)

> **Note implementazione**:
> - `frontend/scripts/theme/theme-roles.mjs:70` lo cambio io nello stesso commit dello spostamento, solo il percorso:
>   l'eccezione si confronta con `===`. Prova: `--check` pulito e i totali m1/m2 identici prima e dopo. Il file è
>   tornato fra quelli di `files/y5_paths.py`; è l'unica riga del file che cita `components/brokers`.
> - `designer-lab.md` e `CHART_PATH_RE` li aggiorna L. Il baseline si scrive con lo strumento.
> - Y5 entra dopo le 03:20, dopo il lotto di T che porta `LotCustodyModal`.
> - **Strumento della prova**: `files/theme_totals.mjs` stampa i totali m1/m2 dell'albero e del baseline, con
>   `scanTree`, `readBaseline` e `totalsOf` esportati da `theme-roles.mjs`. Su `94a8b4a7e`:
>   `{"tree":{"m1":11026,"m2":83},"baseline":{"m1":11026,"m2":83},"treeFiles":284,"baselineFiles":284}`. Si lancia
>   prima e dopo ogni spostamento: Y4b, Y3, Y5 e Y6.
> - **Y6**: il coordinatore aspetta la risposta dei colori su `htmlSink.gate.test.ts:70`.

### Y6 — risposte dei colori (2026-10-16, 00:40)

> **Note implementazione**: via libero dai colori. Y6 si applica sempre dopo l'ingresso di CP-U2 di H.
> - `htmlSink.gate.test.ts:70` è il gate di K, non loro. Lo cambio io nello stesso commit dello spostamento, perché la
>   chiave si confronta con il percorso.
> - `_frontend_utility.py` lo scrivo io.
> - Il baseline ha una riga sola, `lib/components/files/FileGrid.svelte`, e si scrive con lo strumento.
> - `files/y6_paths.py` copre già tutti e due i file; la prova dei totali con `files/theme_totals.mjs`, come per gli
>   altri spostamenti.

### Y7 — galleria mobile d'ingresso, preparazione ✅ (2026-10-16, 00:41–00:55; si lancia nello slot dopo G-13)

> **Note implementazione**: il riferimento di G-13 è `a2c1c39f4` (coordinatore, 00:41), cioè lo snapshot
> `g-ref13-r1`: alle 00:43 era ancora in corsa (partito alle 00:02), e il suo `meta.json` arriva alla fine.
> - **Confronto scelto**: leggere il diff con l'attribuzione, senza un ramo temporaneo. `a2c1c39f4` è antenato della
>   base `4ef2fc199`. Fra i due, nel frontend cambiano solo `providerProbe.ts`, `resolveProviderError.ts` e l'i18n
>   degli asset (X-RL: errori dei fornitori) e una riga di `FilesTable.test.ts` (H CP-U1); `gallery.spec.ts` è
>   identica. Nel backend, H CP-U1 cambia `services/files/static_uploads.py` (le righe dei file statici) e X-RL i
>   fornitori FX e asset. Quindi una differenza nelle schermate filtrate è di Y7, salvo le righe delle liste dei file,
>   che possono venire da H CP-U1. E5a, W-B20, W3-a e J CP-16 non sono in nessuna delle due revisioni.
> - **Desktop invariato per costruzione**: senza trascinamento `columnMinWidth()` rende `column.minWidth || 60`, come
>   prima, e la galleria parte senza larghezze salvate. Il cancello resta solo mobile.
> - **Filtro**, verificato su `HEAD` e su `a2c1c39f4`, con 11 test su 139 in entrambe le revisioni:
>   `PAC allocator steps|transaction list|dashboard transactions tab|(dashboard|broker) (positions tab|fifo lots panel)|Asset list table|FX list table|static resources tab|broker reports tab`.
>   `dev.py` lo passa a Playwright così com'è (`-g`, lista di argomenti, niente shell).
> - **Script**: `/tmp/libreFolio_y7_gallery.sh`.
>   - Si ferma se il riferimento non ha `meta.json` o se la porta 6189 è occupata.
>   - `gallery_snapshot.sh y7-tables-<sha>-mobile --port 6189 --data-dir /tmp/librefolio-r13-y -- --mobile-only -f
>     "<filtro>" --workers 2`, con `nice -n 10` e senza `--no-populate`: dopo le E2E di Y7, il DB della corsia non ha i
>     file statici.
>   - Poi `gallery_tool.py diff … --common-only --stability diffs/g-final3__r1__vs__r2/stability.json` (177 shot,
>     16 varianti ciascuno, mobile compreso) e `/tmp/libreFolio_y7_attr.py`, che raggruppa le immagini cambiate per
>     pagina e shot, con il riquadro unito e la larghezza del PNG (1290 px, iPhone 14 Pro Max a 3×).
> - **Attesa per Y7**: sui telefoni la colonna delle azioni non è più fissata al bordo destro. In una tabella più
>   larga dello schermo, a scorrimento zero, le azioni spariscono dal bordo destro: il riquadro della differenza sta
>   sulla destra della tabella, intestazione compresa. Le composizioni A | B | pixel si guardano a campione.

### Y7 — galleria avviata e fermata (2026-10-16, 00:52–00:57)

> **⚠️ Fuori pista**: alle 00:48 il coordinatore ha dato il via: «lancia la galleria appena G-13 ha il `meta.json` e la
> porta è libera». Ho messo in attesa `/tmp/libreFolio_y7_gallery_wait.sh`, un ciclo che aspetta il `meta.json`, il
> carico sotto 70 e la 6189 libera.
> - Il `meta.json` di `g-ref13-r1` è comparso alle 00:52:44, e il ciclo ha avviato la galleria subito, mentre partiva la
>   r2 dei colori (`g-ref13-r2`, `--workers 6`).
> - Alle ~00:57 il coordinatore ha fermato tutte le prove e le build fino all'01:40 circa: la galleria dei colori aveva
>   rossi per il carico. Ho fermato la mia alle 00:57:38.
> - Fino a lì aveva fatto solo la build debug del frontend (svelte-check e vite build), finita. Niente populate,
>   backend o Playwright, e nessun processo rimasto. La 6189 è libera.
> - Lo snapshot vuoto `y7-tables-94a8b4a7e-mobile` l'ho tolto, perché lo script non riusa un'etichetta esistente.
>   La build log è in `files/gallery_y7_aborted_build.log`.
> - Il coordinatore ne è informato, con la sovrapposizione all'inizio della r2.
> - **Da qui**: niente cicli d'avvio automatici. La galleria parte solo al via esplicito del coordinatore, verso
>   l'01:40, dopo la r2. La build debug è pronta e ha la versione bloccata, quindi la run parte dal populate.

### Y9 — passo 1, rossi ⏳ (2026-10-16, dalle 00:58; via del coordinatore alle 00:48)

> **Note implementazione**: `test-author`, solo file Vitest nuovi, senza codice di prodotto e senza toccare i gate di K.
> Per lo stop del coordinatore, l'agente scrive e non lancia niente. Li lancio io, uno alla volta con `nice`, quando il
> coordinatore lo permette.
> - **K-15** (escape nei tooltip, verdetto: il payload `<b data-pwned>` resta testo e non diventa un elemento):
>   - `charts/AllocationPieChart.tooltipEscape.test.ts`: `caption` e `parentLabel` (`:455`, `:472-477`, `:480`);
>   - `charts/CandlestickChart.tooltipEscape.test.ts`: valuta e bandiera nell'intestazione (`:522`, `:524`);
>   - `charts/PriceChartFull.tooltipEscape.test.ts`: la bandiera del segnale sovrapposto (`:1013`), valuta e bandiera
>     della serie principale (`:1020`, `:1023`).
> - **C-34**:
>   - `risk/CorrelationHeatmap.tooltipEscape.test.ts`: il nome dell'asset esce come `escapeHtml(nome)` condiviso, con
>     `&quot;` e `&#39;`;
>   - `utils/core/escapeHtml.single.test.ts`: una guardia statica, un solo escaper HTML nel sorgente (`inlineMath` a
>     parte).
> - **K-13**, `charts/chartFlagFont.test.ts`:
>   - parte A: ECharts vero in SSR (SVG), con un controllo positivo (un tema inline) e il rosso con `CHART_INIT_THEME`;
>   - parte B: la scansione statica, ogni `echarts.init` passa `CHART_INIT_THEME`. Oggi sono 18 chiamate in 17 file: l'analisi ne contava 16 nei componenti, ma sono 16 in 15 file, perché `LotGanttChart` ne ha due, più le 2 del PAC. I commenti che citano `echarts.init()` non contano: la scansione li toglie, e nei `.svelte` legge solo i blocchi `<script>`.
> - **Registrazione**: una unità nuova, `chart-safety-unit`, nel mio `scripts/test_runner/_frontend_portfolio.py`, con la
>   funzione `front_portfolio_chart_safety_unit` e un `add_test` su più righe.
>
> **Decisioni notturne, da rivedere**:
> - **Il disegno di K-13**. `chartTheme.ts` esporta `CHART_FONT_FAMILY`, cioè 'LF Flags' seguito dal default di
>   ECharts, così il testo senza bandiere non cambia: `'sans-serif'`, o 'Microsoft YaHei' su Windows
>   (`echarts/lib/model/globalDefault.js:104`). Esporta anche `CHART_INIT_THEME = {textStyle: {fontFamily}}`, un tema
>   passato come secondo argomento di ogni `echarts.init`.
>   - ECharts 6 accetta un oggetto come tema. Il suo `textStyle` è il font globale del canvas e del `font` in linea del
>     tooltip HTML, e si riapplica a ogni `setOption(…, true)`.
>   - Sul Mac della galleria non mi aspetto differenze: le bandiere sono Apple in tutti e due i casi.
>   - Usare Inter nel canvas, come l'HTML, sarebbe un cambiamento visibile su tutti i grafici: non lo faccio senza
>     una decisione del developer.
> - **La registrazione** va in un'unità mia, `chart-safety-unit`, e non accanto a `PriceChartFull.test.ts` e
>   `CorrelationHeatmap.test.ts` in `front_component_unit` di `_frontend_utility.py`, che è del programma colori.
>   Come per Y10.
> - **Correzione all'analisi di Y9**: una copia locale dell'escaper c'è. `transactions/modals/TransactionBulkModal.svelte:1879`
>   escapa tre caratteri in linea per una cella `html`; è nell'area di W (FE8). La guardia la ammette per nome del
>   file, con il motivo scritto, e fallisce se la copia sparisce, così la lista non invecchia. Lo segnalo al
>   coordinatore. Le altre corrispondenze non sono escaper HTML:
>   - `toastStore.svelte.ts:63` decodifica;
>   - `PerformanceChart.svelte:162` toglie le graffe del rich text di ECharts;
>   - `markdown.ts` scrive Markdown.

### Y7 — galleria mobile d'ingresso ✅ (2026-10-16, 01:33–01:48; via del coordinatore alle 01:33)

> **Note implementazione**: `bash /tmp/libreFolio_y7_gallery.sh` sulla corsia 6189: snapshot
> `y7-tables-94a8b4a7e-mobile`, `--mobile-only`, `--workers 2` e `nice`. 11 test su 11 verdi in 5,8 minuti, 272 PNG.
> Il carico era fra 41 e 57, con altre due corsie e una build di un altro worktree in corsa.
> - **Diff** contro `g-ref13-r1` (`a2c1c39f4`), `--common-only` e `--stability` di `g-final3`, report in
>   `diffs/g-ref13-r1__vs__y7-tables-94a8b4a7e-mobile/`. 174 immagini cambiate e 98 identiche; nessuna cambia di
>   dimensione o manca; il massimo è lo 0,6%.
> - **Attribuzione, tutto a Y7 (D-Y17)**, guardando a occhio sei composizioni:
>   1. l'intestazione «Actions» non è più fissata al bordo destro. Al suo posto c'è l'intestazione della colonna sotto:
>      «Δ 1D» in FX, «Total P&L» nei lotti, «Size» nei file, «Ac…» tagliato nella revisione del PAC;
>   2. anti-aliasing nel testo dell'intestazione e negli angoli della cornice, con Δ massimo fra 10 e 148;
>   3. sulle righe colorate dei lotti FIFO la cella di selezione prende il colore della riga, al posto del blocco scuro
>      opaco del fissaggio. Il caso massimo è fr/dark, allo 0,6%;
>   4. grafici e mappe identici, o rumore entro lo 0,005%.
>   H CP-U1 e X-RL non si vedono: le righe dei file sono identiche.
> - **⚠️ Fuori pista**: `mkdocs gallery` ricostruisce comunque il frontend, con svelte-check (0/0) e vite. La build
>   della run fermata alle 00:57 quindi non ha fatto risparmiare tempo: avevo detto il contrario al coordinatore e l'ho
>   corretto nell'handoff.
> - **Ingresso**: `theme-roles --check` alle 01:48 dice «0 files dropped». Handoff al coordinatore alle 01:48. Entra
>   solo il committato (`ca681b4f9` e `8d4719c21`): il piano, i rossi di Y9 e Y10 e `_frontend_portfolio.py` restano
>   fuori.
> - **Da riferire al developer**, con il riepilogo di D-Y17: la tinta delle righe sulla cella di selezione, sui
>   telefoni.

### Y7 — ingresso ✅ (2026-10-16, 01:49)

> **Note implementazione**: il treno 76 l'ha portato in `dev_release2` con il merge `a613a217c`, con le mie due righe 🐛
> nel CHANGELOG. La tinta delle righe sulla cella di selezione va nella lista di domattina del developer.
> Il coordinatore ha aggiornato la mia base: merge `c7dea8be6`, HEAD `f068a2f5f`. C'era un conflitto di sola aggiunta
> in `LibreFolio_devWiki/log.md`, e i miei file aperti non sono stati toccati.

### Y4b — FE2b, il rischio in `lib/features/risk/` ⏳ (2026-10-16, dalle 01:50; via del coordinatore alle 01:49)

> **Note implementazione**:
> 1. **Base**: HEAD `f068a2f5f`, che contiene T+DV (`a0915bef9`, DV-6 su `stressBucketLabel.ts`). `api sync` senza
>    cambi tracciati.
> 2. **Il runner messo da parte** (passo nuovo). `_frontend_portfolio.py` aveva anche le registrazioni dei rossi di Y9
>    e Y10, che non entrano con Y4b. Ho salvato la copia (`files/_frontend_portfolio.y9y10.py`) e la patch
>    (`files/y9y10_runner.patch`), e ho riportato il file a HEAD. Dopo il commit di Y4b rimetto le registrazioni, con
>    il percorso nuovo del rosso di `CorrelationHeatmap`.
> 3. **`test-author` dei rossi di Y9** chiuso prima dello spostamento: sei file, 19 rossi e 30 verdi attesi, niente
>    lanciato. Fra i suoi reperti, per il passo 2 di Y9: le bandiere dei marcatori d'evento (`PriceChartFull.svelte`,
>    `:812` e `:815`), e l'asse di `CorrelationHeatmap`, che fissa `fontFamily: 'sans-serif'` (`:131`).
> 4. **Spostamento**: `files/y4b_move.py --apply`, 104 file (i 103 previsti più il rosso nuovo di Y9) e 149
>    specificatori riscritti in 69 file. `components/risk/`, `lib/risk/` e `stores/risk/` non esistono più.
> 5. **Percorsi**: `files/y4b_paths.py --apply`, 177 sostituzioni in 46 file. La prova a secco ne contava 328 perché
>    comprendeva anche i 149 specificatori già riscritti. Restano solo le eccezioni previste:
>    - `AssetPickerPanel.test.ts`, che va a `test-author`;
>    - `scanColors.test.ts`, di L;
>    - gli alberi sintetici di `test_i18n_usage_gate.py`;
>    - il baseline, che si scrive con lo strumento;
>    - le cronache (il journal, `sources/` e `log.md`);
>    - `mkdocs_src/site/`, ignorato.
> 6. **Colori**, con lo strumento come chiesto da loro:
>    - `--check` pulito già dopo lo spostamento, perché R4 accoppia i file per nome;
>    - `--update` scrive i nomi nuovi: 30 righe rinominate, conteggi identici a coppie, nessun'altra riga toccata,
>      «m1 10980 → 10980, m2 83 → 83»;
>    - `files/theme_totals.mjs` dà gli stessi totali prima e dopo: albero e baseline a 10980/83, 284 file;
>    - `--check` di nuovo pulito.
> 7. **`AssetPickerPanel.test.ts`** a `test-author`. L'import di tipo di `:47` e il gate di confine «ui/select non
>    importa dal rischio»: il gate risolveva `RISK = resolve(HERE, '../../risk')`, una cartella che non esiste più.
>    Così sarebbe passato in silenzio anche con un import da `features/risk`. Ora punta alla cartella nuova, con una
>    guardia sulla sua esistenza.
>
> **Prove leggere**, una alla volta con `nice`, carico fra 21 e 35:
> - `schemas risk` (pytest): 69 verdi;
> - `check_source_paths.py`: 5 percorsi inesistenti, gli stessi di prima e non miei. I 3 nuovi erano tabelle «Source
>   files» di pagine `sources/` e li ho aggiornati (vedi le decisioni);
> - `mkdocs build` stretto: 3060 URL relativi risolti. `mkdocs check-links`: 96 link validi. Le 5 pagine MkDocs
>   cambiate non hanno traduzioni;
> - knip (`npm run lint:dead`): gli stessi reperti di Y8 a percorsi normalizzati, più l'import di
>   `AssetPickerPanel.test.ts:47`, in correzione;
> - `front-portfolio`: `risk-unit` 40, `risk-request-unit` 26, `risk-benchmark-unit` 13, `risk-controller-unit` 102,
>   `risk-levels-unit` 498, `risk-levels-component` 273 e `risk-frame-component` 20, tutti verdi;
> - `front-utility core-unit`: 170 file e 5870 test verdi, compresi i gate (`htmlSink`, `themeRoles`, `themeTokens`),
>   `moneyRenderSites` e `catalogIcuLocale`, che hanno chiavi di percorso;
> - `check-orphans`: orfani solo gli 8 rossi non tracciati di Y9 e Y10.
>
> **Decisioni notturne, da rivedere**:
> - **Le tre pagine `sources/` della devWiki** («Source files»: `RiskLevelsPanel.svelte`, `riskAnalysisHelpers.ts`,
>   `riskStore.svelte.ts`) le ho aggiornate al percorso nuovo, anche se gli script lasciavano fuori `sources/`. Il
>   motivo: `check_source_paths.py` chiede che ogni percorso di quelle tabelle esista, e c'è un precedente (il
>   refactor `27a29af09`). Le cronache in prosa restano com'erano.
> - **Il runner riportato a HEAD per il checkpoint**, con le registrazioni dei rossi rimesse dopo, invece di uno stage
>   parziale da parte del coordinatore.
>
> **Seguito delle prove** (02:08–02:25):
> - `AssetPickerPanel.test.ts`, dopo `test-author`: 97 verdi da solo. Il gate di confine ora guarda `features/risk/`,
>   con una guardia che la cartella esista e contenga `eligibility.ts`, e con il nome `$lib/` ricavato dalla cartella.
>   I due nomi vecchi sono fra i negativi;
> - `front-utility component-unit`: 144 file e 3795 test verdi;
> - `front check` (svelte-check): 0 errori, 0 avvisi;
> - Prettier `--check` sui 113 file frontend toccati: puliti;
> - ruff sui 4 file Python: identico a HEAD. In `_frontend_portfolio.py` restano i 28 avvisi e la deriva di formato, che
>   c'erano già;
> - `utils gate-i18n-catalog` 176 verdi e `utils gate-i18n-usage` 195 verdi. Il secondo l'avevo escluso dagli script
>   come «alberi sintetici» senza lanciarlo, e lo conferma;
> - `check-orphans` sullo stato del checkpoint, con gli 8 rossi messi da parte e poi rimessi (8 somme OK): «All test
>   files are registered», e 448 test frontend raggiungibili da `all`;
> - `git diff --check` pulito, `theme-roles --check` pulito, 6189 libera.
>
> **⚠️ Fuori pista**: il primo tentativo di `check-orphans` «pulito» ha messo da parte 51 file invece di 8, perché il
> glob degli untracked prendeva anche i 43 test del rischio appena spostati. Li ho rimessi tutti (51 somme OK) e ho
> rifatto la prova con l'elenco esatto degli 8.
>
> **Checkpoint**: 255 percorsi da mettere in stage, in `files/y4b_stage_code.txt`: 103 cancellazioni, 103 file nuovi
> in `features/risk/` e 49 modifiche. Restano fuori gli 8 rossi di Y9 e Y10 e il piano, che va nel commit del journal.
> Non ci sono righe di CHANGELOG: è uno spostamento interno. Le E2E `risk` e `risk-lab` aspettano lo slot del
> coordinatore, dopo H e A.

### Y4b — commit e revisione combinata ⏳ (2026-10-16, 02:26–)

> **Note implementazione**: il coordinatore ha salvato Y4b in `51aff4a12`, 152 file (103 rinomine e 49 modifiche), e il
> journal in `26cdfb3ec`. Poi ha aggiornato la base: merge pulito di `dev_release2` (`57802d827`, con DV TD-1),
> HEAD `9295febe9`, con `_frontend_utility.py` fuso da solo e `theme-roles --check` pulito.
> - **Prove leggere sulla revisione combinata** (`/tmp/libreFolio_y4b_entry_light.sh`, una alla volta con `nice`, ognuna
>   dopo il carico sotto 70), tutte verdi:
>   - `api sync`, senza cambi tracciati;
>   - `front check`: 0 errori, 0 avvisi;
>   - i 7 test unitari del rischio: 26 file, 972 test;
>   - `core-unit`: 171 file e 5900 test. Un file in più per l'ingresso di DV.
> - **E2E nello slot pesante 2** (via del coordinatore, 02:27): `risk` e poi `risk-lab`, `--workers 2` e `nice`
>   (`/tmp/libreFolio_y4b_e2e.sh`).
> - **Le registrazioni dei rossi** di Y9 e Y10 si rimettono solo dopo le E2E (coordinatore), così la revisione che entra
>   resta pulita.
>   - La patch salvata non si applica più, perché Y4b ha cambiato le righe del rischio che fanno da contesto.
>   - Le rimette `files/y9y10_runner_reapply.py`: prende i pezzi dalla copia salvata e li inserisce per ancora, con il
>     percorso nuovo `features/risk/` del rosso di `CorrelationHeatmap`. A secco passa, e le ancore coincidono con il
>     file di oggi.
> - **Per il passo 2 di Y9**:
>   - DV TD-1 toglie `PAC_EXPOSURE_BAR_COLORS` da `chartTheme.ts`, quindi `ExposureBars.svelte` non importa più
>     `chartTheme`. `files/y9_k13_apply.py` aggiunge la riga d'import dopo quella di `echarts`, ed è già previsto;
>   - a secco sulla base nuova: 18 chiamate in 17 file.
>   - L'aggiunta a `chartTheme.ts` va in fondo al file, una zona che DV non tocca.
> - **E2E** (slot 2, `9295febe9`): `front-portfolio risk` 38 su 38 (02:33–02:43, build compresa), `front-portfolio
>   risk-lab` 44 su 44 (02:43–02:48). La 6189 è libera. Handoff d'ingresso al coordinatore alle 02:48.
> - **Registrazioni dei rossi** rimesse dopo le E2E, come da ok del coordinatore: `files/y9y10_runner_reapply.py
>   --apply`, +40 −2. `check-orphans` è pulito con gli 8 rossi registrati; ruff dà 28 avvisi come HEAD. Non sono
>   committate.

### Y9 — passo 1, rossi ✅ (2026-10-16, 00:58–02:50)

> **Note implementazione**: `test-author` ha scritto sei file nuovi. Li ho lanciati uno alla volta con `nice` e il
> reporter verboso, alle 02:48. Il risultato è identico alla previsione: **19 rossi e 30 verdi**.
>
> | File | Rossi | Verdi | Motivo dei rossi (asserzione) |
> |---|---:|---:|---|
> | `charts/AllocationPieChart.tooltipEscape` | 3 | 4 | il carico diventa un elemento: titolo da `data.caption`, riga del padre con uno e con due anelli |
> | `charts/CandlestickChart.tooltipEscape` | 4 | 3 | intestazione: codice e bandiera, con e senza conversione |
> | `charts/PriceChartFull.tooltipEscape` | 5 | 5 | bandiera della riga sovrapposta; codice e bandiera della riga principale, con e senza conversione |
> | `features/risk/CorrelationHeatmap.tooltipEscape` | 1 | 2 | la copia locale lascia `'` e `"` |
> | `utils/core/escapeHtml.single` | 1 | 5 | un solo escaper fuori elenco: `features/risk/CorrelationHeatmap.svelte:352` |
> | `charts/chartFlagFont` | 5 | 11 | `CHART_FONT_FAMILY` e `CHART_INIT_THEME` assenti; 18 su 18 `echarts.init` senza il tema |
>
> Nessun rosso viene dall'import o dall'impianto di prova: i verdi comprendono i controlli positivi, cioè un tema in
> linea che funziona anche dopo un `setOption(…, true)`, e gli scanner provati su sorgenti inventati.
> - **Per il passo 2** (reperti di `test-author`, non ancora coperti da test):
>   - le bandiere dei marcatori d'evento (`PriceChartFull.svelte:812`, `:815`) sono lo stesso vettore di K-15, e le
>     metto nel passo 2;
>   - `marker.type` grezzo (`:808`), le date di `formatDay` e i colori negli attributi `style` vengono da valori
>     interni o dal backend, quindi il rischio è basso: li valuto nel passo 2;
>   - le graffe nel rich text di ECharts della torta (`:361`, `:546`) sono testo su canvas, non HTML;
>   - l'asse di `CorrelationHeatmap` fissa `fontFamily: 'sans-serif'` (`:131`, `:276`, `:478`), e lì il tema non
>     arriva. È una decisione del passo 2.

### Y4b — ingresso ✅ (2026-10-16, 02:52)

> **Note implementazione**: il treno 81 l'ha portato in `dev_release2` con il merge `08efa5ac3`. FE2b è chiuso: il
> rischio è in `lib/features/risk/`. Resta Y4a (FE2a, i segnali), dopo FE4 e FE5a di X. Y3 parte dopo l'ingresso del
> lotto di T, verso le 03:20, al messaggio del coordinatore. Il passo 2 di Y9 l'ho proposto per subito, perché Y3 è
> fermo, e aspetto il via.

### Y9 — passo 2, prima parte ✅ (2026-10-16, 02:52–03:05; via del coordinatore alle 02:52, checkpoint prima di Y3)

> **Condizioni del coordinatore**:
> - un checkpoint di Y9 prima di applicare Y3, anche se il lotto non è finito;
> - `document.fonts.load` prima del primo disegno, coperto da un test.
>
> **Note implementazione**:
> - **K-13**: un modulo nuovo, `lib/components/charts/chartFont.ts`, con `CHART_FONT_FAMILY` («'LF Flags'» più il
>   default di ECharts, che su Windows è 'Microsoft YaHei', letto come lo legge ECharts) e `CHART_INIT_THEME`.
>   `files/y9_k13_apply.py --apply` ha portato il tema in 18 chiamate `echarts.init` di 17 file, ognuno con la sua riga
>   d'import.
> - **K-15**, con l'`escapeHtml` condiviso:
>   - `AllocationPieChart`: il titolo e la riga del padre;
>   - `CandlestickChart`: valuta e bandiera nell'intestazione, con e senza conversione;
>   - `PriceChartFull`: la bandiera della riga sovrapposta, valuta e bandiera della riga principale, e nei marcatori
>     d'evento le due bandiere e `marker.type`.
> - **C-34**: `CorrelationHeatmap` usa l'`escapeHtml` condiviso al posto della copia a tre caratteri. Il font del suo asse
>   (`AXIS_FONT_FAMILY`) diventa `CHART_FONT_FAMILY`, così il tema non viene scavalcato e la misura resta uguale al
>   disegno.
> - **Il test rosso di K-13** l'ho puntato a `chartFont` a mano (l'import, l'esempio sintetico, i messaggi) e poi
>   formattato con Prettier. È una sostituzione meccanica di percorso, come quelle degli script di spostamento.
>
> **Prove**, una alla volta con `nice`:
> - i 6 file di Y9, da soli: 49 verdi su 49 (prima 19 rossi e 30 verdi). `front-portfolio chart-safety-unit` dal
>   runner: 6 file, 49 test;
> - i test esistenti dei grafici toccati: 13 file, 359 test. I grafici dei lotti hanno solo test degli helper, e
>   `GeographyMap` ed `ExposureMaps` non hanno test;
> - `theme-roles --check` pulito; `front check` 0 errori e 0 avvisi;
> - `core-unit`: 171 file e 5900 test, compresi i gate `htmlSink`, `htmlInterpolation` e `themeRoles`;
> - `front-fx fx-unit`: 4 file e 138 test, compreso `flagFont.gate`;
> - Prettier pulito; `git diff --check` pulito;
> - `check-orphans` sullo stato del checkpoint, con i 2 rossi di Y10 messi da parte e rimessi: pulito.
>
> **Decisioni notturne, da rivedere**:
> - **`chartFont.ts` e non `chartTheme.ts`**. `chartTheme.test.ts`, dei colori, visita ogni export di `chartTheme.ts`
>   e vuole che ogni stringa sia un colore: una famiglia di font lì lo romperebbe. Un modulo a parte, accanto agli altri
>   helper di ECharts, lascia intatti i file dei colori.
> - **Escape anche dove i rossi non arrivavano**: le bandiere dei marcatori d'evento e `marker.type`. I test per
>   questi arrivano nella seconda parte.
> - **Il runner per il checkpoint** ha solo la registrazione di Y9 (`chart-safety-unit`). Le righe di Y10 sono in
>   `files/_frontend_portfolio.y9y10.after-y4b.py` e tornano con il codice di Y10.
>
> **Resta per la seconda parte**:
> 1. `document.fonts.load` prima del primo disegno, con il suo test (condizione 2), scritto da `test-author`;
> 2. i test sull'escape dei marcatori, e il nome dell'alias `chartTheme` nel test di K-13;
> 3. la documentazione con `docs-writer` (`developer/frontend/components/charts.md`, `styling.md`);
> 4. con lo slot, le E2E dei grafici e una galleria filtrata sui grafici con bandiere;
> 5. le righe CHANGELOG nell'handoff d'ingresso.

### Y9 — passo 2, seconda parte ⏳ (2026-10-16, dalle 03:08; prima parte salvata in `dae8b4442` e `7e3c88e5e`)

> **Note implementazione**:
> - **Il carico del font** (condizione 2 del coordinatore).
>   - Il problema: un canvas disegna il testo una volta sola, con le facce già caricate, e il browser scarica una faccia
>     `unicode-range` solo per il testo della pagina che ne ha bisogno. Il testo del canvas non conta, e
>     `document.fonts.ready` aspetta solo le facce già richieste.
>   - In `chartFont.ts`, `chartFontReady()` fa una sola richiesta, in cache:
>     `document.fonts.load("16px 'LF Flags'", '🇺🇸')`. Non rifiuta mai, e senza `document.fonts` (nei test e su un
>     server) si risolve subito. C'è anche `chartFontLoaded()` (`document.fonts.check`).
>   - La richiesta parte quando il modulo viene caricato. Ogni grafico lo importa prima di poter disegnare, quindi la
>     richiesta precede sempre il primo disegno.
>   - La rete di sicurezza è in `scheduleFirstRenderStabilityFix` (`echartsTooltipHelpers.ts`), che 16 grafici su 17
>     chiamano dopo il primo `setOption`: se la faccia non c'è ancora, un solo `resize()` quando arriva. Il diciassettesimo
>     è `LotGanttChart`, che non disegna bandiere.
> - **Test**, affidati a `test-author`:
>   - `chartFont.load.test.ts`, nuovo: la richiesta all'import, la cache, che non rifiuti mai, `check`, l'ordine «load
>     prima del primo `setOption`» su un grafico vero montato, e il ridisegno una volta sola;
>   - i marcatori d'evento in `PriceChartFull.tooltipEscape.test.ts`;
>   - il nome dell'alias in `chartFlagFont.test.ts`.
>   Il file nuovo è registrato in `chart-safety-unit`.
> - **Documentazione**, affidata a `docs-writer`: `developer/frontend/components/charts.md` (font, carico ed escape, con
>   le guardie) e la sezione 'LF Flags' di `styling.md`.
>
> **Decisione notturna, da rivedere**: «prima del primo disegno» qui vuol dire che la richiesta del font parte prima, ed
> è garantito. Che il caricamento sia finito prima del disegno non è garantito: in quel caso raro il grafico si
> ridisegna una volta, appena la faccia arriva. Aspettare il font prima del primo `setOption` voleva dire cambiare il
> flusso d'avvio di 17 componenti diversi, e rendere asincroni i test dei grafici. Sul Mac della galleria non si vede
> differenza.
>
> **Checkpoint Y9-2** (03:32, chiesto dal coordinatore per aggiornare la base prima di Y3; il lotto di T è entrato in
> `503dce683`):
> - **Entrano**:
>   - `chartFont.ts`, con il carico del font, ed `echartsTooltipHelpers.ts`, con il ridisegno;
>   - la documentazione di `docs-writer`: `charts.md` («Chart Text and Tooltips», con le sezioni sul font, sull'HTML dei
>     tooltip e sulle guardie), `styling.md` (il testo dei grafici nella sezione 'LF Flags') e `security.md` (la terza
>     guardia di «Output Escaping»). `docs-writer` ha anche corretto: «two letters» vale dove manca il glifo, Windows
>     compreso, non su ogni Linux; e `TransactionBulkModal` importa già `escapeHtml`, ha solo una copia in linea;
>   - il piano.
> - **Restano fuori**, perché `test-author` li sta scrivendo:
>   - `chartFont.load.test.ts`, nuovo;
>   - i test dei marcatori in `PriceChartFull.tooltipEscape.test.ts`;
>   - l'alias in `chartFlagFont.test.ts`;
>   - la loro registrazione in `_frontend_portfolio.py`;
>   - i 2 rossi di Y10.
>   Nessuno di questi file è cambiato in `dev_release2`: lo è solo `security.md`, che entra.
> - **Prove**:
>   - i test dei grafici toccati, compreso `echartsTooltipHelpers.test.ts`: 14 file e 406 test;
>   - svelte-check: 0 errori e 0 avvisi;
>   - Prettier sui due file di codice;
>   - `mkdocs build` stretto: 3068 URL relativi risolti. `check-links`: 96 link validi;
>   - `git diff --check` pulito.
> - **Salvato**: il coordinatore ha committato `26978e101` (codice e documentazione) e `8c762a10f` (journal). Poi ha
>   aggiornato la base: merge pulito di `dev_release2` (`503dce683`, con il lotto di T e TD-3), HEAD `a1e4e5448`, con
>   `security.md` fuso da solo.

### Y9 — passo 2, i test di `test-author` ✅ (2026-10-16, 03:09–03:35; non ancora committati, sono il checkpoint Y9-3)

> **Note implementazione**: tutti e tre i file sono verdi da soli, e lo restano dopo il merge della base.
> - **`chartFont.load.test.ts`**, nuovo, 13 test:
>   - all'import, `load` è chiamato una sola volta, con un `font` che il parser CSS accetta e che nomina 'LF Flags', e
>     un campione fatto solo di indicatori regionali;
>   - la cache: una sola promessa, un solo `load`;
>   - non rifiuta mai: né dopo un `load` rimandato, né dopo un `load` rifiutato, né senza `document.fonts`;
>   - `chartFontLoaded()` segue `check`;
>   - **prima del primo disegno**: monta `SemiDonutChart` con un ECharts finto, e nel registro `fonts.load` viene prima
>     del primo `setOption`. Il controllo inverso usa con `vi.doMock` una versione che chiede la faccia solo quando un
>     grafico la chiede, e lì la richiesta arriva dopo: così il test può fallire davvero;
>   - il ridisegno: un solo `resize` in più quando la faccia arriva dopo; nessuno se c'era già; nessuno su un grafico
>     già chiuso.
> - **`PriceChartFull.tooltipEscape.test.ts`**: 17 test (10 di prima e 7 nuovi), sul tipo del marcatore, sulla sua
>   bandiera e su quella d'origine di un marcatore convertito, più i controlli sul percorso e le guardie sui codici.
> - **`chartFlagFont.test.ts`**: 16 test. L'alias è ora `chartFont`, e la sezione «Why it is red today» è al passato.
> - **Reperti di `test-author`**:
>   - `ScatterChart` chiama la passata di stabilità prima del primo `setOption`. Per K-13 non cambia niente;
>   - un `load` fallito non viene ritentato, come dice la documentazione;
>   - un'eccezione sincrona di `document.fonts.load` romperebbe l'import di tutti i grafici. Le specifiche la
>     escludono, ma una guardia `try` costa poco: la metto nel checkpoint Y9-3.

### Y3 — FE6b, la dashboard in `lib/features/dashboard/` ⏳ (2026-10-16, dalle 03:33; via del coordinatore)

> **Note implementazione**:
> 1. **Base**: HEAD `a1e4e5448`, con il lotto di T e `AllocationPanel.svelte` nella forma finale. `api sync` non cambia
>    file tracciati.
> 2. **Il runner messo da parte**, come per Y4b: la registrazione non committata di `chartFont.load.test.ts` (Y9-3) è
>    salvata in `files/_frontend_portfolio.y9-3.py` e `files/y9-3_runner.patch`, e `_frontend_portfolio.py` è tornato a
>    HEAD.
> 3. **Spostamento**: `files/y3_move.py --apply`, 37 file (i 35 previsti più i 2 rossi di Y10, che seguono la cartella) e
>    42 specificatori riscritti in 8 file. `components/dashboard/` non esiste più; `dashboardViewStore` e
>    `dateRangeController` sono ora in `features/dashboard/`.
> 4. **Percorsi**: `files/y3_paths.py --apply`, 74 sostituzioni in 29 file. Restano fuori di proposito:
>    - `pickView.test.ts` e `scanColors.test.ts`, di L;
>    - i commenti di storia in `KpiDivergingFlowBar.test.ts` e `KpiMetricBar.test.ts`;
>    - le cronache.
> 5. **Colori**, con lo strumento:
>    - `--check` pulito;
>    - `--update`: 11 righe rinominate, conteggi identici a coppie, nessun'altra riga, «m1 10166 → 10166, m2 71 → 71»;
>    - i totali sono identici prima e dopo: 10166/71, 263 file.
>    - **Da sapere**: la dichiarazione `~split` di Y1 (`GrowthChart`, riga 272) cita ancora
>      `lib/components/dashboard/`. `--update` lascia le dichiarazioni come sono, perché sono un registro, e a mano il
>      baseline non si tocca. `--check` è pulito; lo segnalo ai colori.
> 6. **devWiki**: tre tabelle «Source files» di `sources/` (`GrowthChart.svelte` due volte, `YieldOnCostCell.svelte`)
>    portate al percorso nuovo, come in Y4b. `check_source_paths` torna ai 5 percorsi mancanti di prima.
> 7. **Documentazione**: l'albero di `developer/frontend/index.md` era vecchio, già da Y4b: `stores/risk/`, e
>    `features/` con solo `auth` e `settings`. Ora è anche stantio per Y3. Lo corregge `docs-writer`.
>
> **Prove leggere** (03:37–03:53, una alla volta con `nice`):
> - `front check`: 0 errori, 0 avvisi;
> - `component-unit`: 149 file e 3939 test;
> - `growth-chart-memo` 166, `allocation-unit` 173 (6 file), `utils gate-i18n-usage` 195;
> - `check-orphans` sullo stato del checkpoint, con messi da parte i 3 file di test non registrati di proposito: pulito;
> - knip: gli stessi reperti di Y8, a percorsi normalizzati;
> - `mkdocs build` stretto, 3068 URL; `check-links`, 96;
> - `git diff --check` pulito, `theme-roles --check` pulito.
>
> **⚠️ Fuori pista**:
> - **`asset-unit`, 5 rossi.**
>   - 3 rossi in `chartCoreHelpers.test.ts`, colpa di Y3: un `ENOENT` su `components/dashboard/growthChartData.ts`, perché
>     il test costruisce il percorso con un template, `` new URL(`../dashboard/${file}`, import.meta.url) ``, che lo
>     script non riconosce. L'ho corretto a mano in `../../features/dashboard/${file}`. Era l'unico template di quella
>     forma nel frontend: ho controllato anche quelli del rischio.
>   - 2 rossi in `timeSeriesAggregationGolden.test.ts`, che non vengono da Y3 ma da **Y8** (`a25d09a69`, I-01). Il
>     verdetto è **difetto**: Y8 ha cambiato di proposito la somma con i punti mancanti e non ha ricatturato il corpus
>     golden, e nelle prove di Y8 mancava `asset-unit`. Il test è rosso sul target dal treno di Y8. È nel backlog come
>     Y-11, e lo segnalo al coordinatore con il rimedio.
>   - Dopo la correzione, `asset-unit` ha solo i 2 rossi di Y8 (874 verdi su 876).
> - **`core-unit`, 1 rosso**: `themeModeReads.gate.test.ts` (R, W8) confronta un elenco in ordine, e quello ricevuto è
>   ordinato per percorso. Con `features/dashboard/` le due voci della dashboard (`AllocationHistoryChart` e
>   `OtherPeriodEffectsTable`) cadono dopo `RiskCardGrid`. Ho spostato quelle due righe dell'elenco atteso, senza altri
>   cambi: il gate dà 24 verdi su 24.
> - **Prettier**: l'import di `chartCoreHelpers.test.ts`, riscritto dallo script, era diventato troppo lungo. Prettier
>   l'ha rimandato a capo (41 righe in più, 28 in meno). Gli altri 41 file erano già puliti.
>
> **Checkpoint Y3**: 102 percorsi in `files/y3_stage_code.txt`: 35 cancellazioni, 35 file nuovi in
> `features/dashboard/` e 32 modifiche. Restano fuori:
> - i 3 file di Y9-3: `chartFont.load.test.ts`, più i cambi di `test-author` in `PriceChartFull.tooltipEscape.test.ts` e
>   in `chartFlagFont.test.ts`;
> - i 2 rossi di Y10, ora in `features/dashboard/`;
> - il piano e il backlog, che vanno nel commit del journal.
> - **Salvato**: `ce828e9c1` (67 file: 35 rinomine e 32 modifiche) e `0eefb51df` (journal). Poi il merge di
>   `dev_release2` (`d0efca910`, con CP7b-1 e CP-6), pulito: HEAD `ee8b4edad`, `theme-roles --check` pulito. La riga
>   `~split` l'ha girata il coordinatore ai colori. Le E2E di Y3 vanno nello slot 2, dopo quelle di A, verso le 04:30.

### Y-11 — il corpus golden dopo I-01 ⏳ (2026-10-16, dalle 03:56; via del coordinatore)

> **Note implementazione**: `api sync` sulla base nuova non cambia file tracciati.
> - Il corpus si accetta con la procedura scritta nel file: lo script di rigenerazione mostra la deriva, `--accept`
>   riscrive il JSON, e `GOLDEN_DIGEST` si aggiorna a mano.
> - `test-author` deve prima controllare che cambino solo voci di `aggregateSumSeries` con punti mancanti, e solo come
>   vuole I-01. Una deriva diversa sarebbe un altro difetto: in quel caso si ferma.

### Y9-3 — i test di `test-author` e la guardia ⏳ (2026-10-16, dalle 03:57)

> **Note implementazione**:
> - la registrazione di `chartFont.load.test.ts` è rimessa con `git apply` della patch salvata, che si applica pulita;
> - in `chartFont.ts` una guardia `try` su `document.fonts.load` (un'eccezione sincrona all'import romperebbe tutti i
>   grafici) e su `check`, che nella passata di stabilità restituisce true. I test di queste guardie li aggiunge
>   `test-author` in `chartFont.load.test.ts`.
>
> **Fatto** (`test-author`, 03:57–04:02):
> - lo script senza flag mostra 4 voci cambiate su 276, nessuna aggiunta o tolta. Le voci sono
>   `aggregateSumSeries|{all-missing-values,partial-missing-bucket}|{weekly,monthly}`, cioè 6 secchi;
> - cambiano solo `sourcePointCount` (contano i punti presenti) e `missing`, che non viene più copiato dall'ultimo punto
>   del secchio. Nessuna somma cambia, perché nel corpus i punti mancanti valgono 0;
> - i 6 secchi sono stati confrontati con un calcolo I-01 indipendente, fatto sugli input dei casi, e coincidono;
> - poi `--accept`, il nuovo `GOLDEN_DIGEST` (`sha256:007e69d21f…`) e il commento che registra I-01 e le chiavi
>   cambiate.
>
> **Prove**: il golden 10 su 10 e `timeSeriesAggregation.test.ts` 47 su 47, ciascuno da solo; `front-asset asset-unit`
> dal runner, 20 file e 876 test verdi (prima 2 rossi); `git diff --check` pulito. Il golden non vede la regressione
> «la somma salta i mancanti», perché i suoi mancanti valgono 0. La coprono i test di I-01 in
> `timeSeriesAggregation.test.ts`, con segnaposto come 999.
>
> **Checkpoint Y-11**: il JSON del corpus e `timeSeriesAggregationGolden.test.ts`; il backlog (Y-11 ✅) e il piano
> vanno nel journal.
> - **Salvato**: `4c1f2fee6` (test) e `c27c34619` (journal). Y-11 entra con Y3 e Y9, dopo le E2E.

### Y9-3 — test e guardie ✅ (2026-10-16, 03:57–04:08; checkpoint mandato alle 04:08)

> **Note implementazione**:
> - In `chartFont.ts`, due guardie `try`. Se `document.fonts.load` lancia un'eccezione sincrona, la richiesta si
>   considera chiusa: senza la guardia, la richiesta che parte all'import romperebbe l'import di tutti i grafici. Se la
>   lancia `check`, `chartFontLoaded()` restituisce true e il ridisegno viene saltato.
> - `test-author`:
>   - `chartFont.load.test.ts`, 16 test: i 13 di prima e 3 nuovi sulle guardie. Ha anche provato che, su una copia
>     senza guardie, i 3 nuovi test falliscono;
>   - `PriceChartFull.tooltipEscape.test.ts`, 17 test;
>   - `chartFlagFont.test.ts`, 16 test.
> - La registrazione di `chartFont.load.test.ts` in `chart-safety-unit` è rimessa con la patch salvata.
>
> **Prove**: `chart-safety-unit` dal runner, 7 file e 72 test; `echartsTooltipHelpers.test.ts` 47; svelte-check 0 errori
> e 0 avvisi; `check-orphans` pulito, con i 2 rossi di Y10 messi da parte; Prettier e `git diff --check` puliti.

### Y3 + Y9 — E2E d'ingresso ⏳ (slot 2, 04:30–05:00)

> **Note implementazione**: l'elenco l'ha approvato il coordinatore alle 04:10. Prima le spec principali, poi le altre se
> c'è tempo. Lo slot deve essere libero entro le 05:00, per la galleria di X. Le 3 «Live price direction flash» devono
> essere verdi: la correzione di Z è entrata con il treno 60. Niente galleria per Y3 e Y9: la copre la candidata dei
> colori delle 05:30.
> - **Script**: `/tmp/libreFolio_y3y9_e2e.sh`, una spec alla volta, `--workers 2` e `nice`. Ogni spec ha un orario
>   oltre il quale non parte.
> - **Ordine**: `front-portfolio dashboard`, `front-asset asset-detail`, `asset-name-xss`, `front-fx fx-detail`,
>   `front-broker detail`, `front-portfolio dashboard-cache`, `front-fx fx-flag-font`; poi, se c'è tempo,
>   `privacy-masking`, `yield-on-cost-real`, `broker-filter-label` e `broker-icons`.
> - **04:44, nessun via allo slot.** Le 7 spec principali chiedono circa 34 minuti e non stanno più prima delle 05:00.
>   Ho chiesto al coordinatore di spostarle dopo la galleria di X (mia preferenza), oppure di lanciare subito solo
>   `dashboard`. HEAD `fd77a13ee`: Y9-3 è committato in `fd77a13ee`.

### Y10 — E2E rossa scritta ✅ (2026-10-16, 04:12–04:44; `test-author`, niente lanciato)

> **Note implementazione**: `frontend/e2e/portfolio/allocation-negative-cash.spec.ts`, 4 test, non registrato.
> - **Endpoint intercettato**: la Dashboard legge il blocco `summary` di `POST /api/v1/portfolio/report`
>   (`portfolioStore.fetchReport`). Il commento in testa al rosso Vitest, che dice «GET /portfolio/summary», è sbagliato:
>   lo correggo con il codice di Y10.
> - **La riscrittura**, solo per i tipi e i settori:
>   - via la riga di liquidità vera, e una riga «Liquidity» con −P/6, dove P è il totale delle posizioni;
>   - le quote ricalcolate con la formula del backend, quindi i positivi arrivano a circa 120;
>   - lo schema verificato con il `PortfolioSummary` del client generato.
> - **I test**:
>   - rossi: la nota, firmata e nella valuta, sulle schede tipo e settore; la privacy attivata e disattivata sul posto
>     (le cifre mascherate, il segno e la valuta restano). Tutti e due falliscono alla prima asserzione sulla nota;
>   - guardie verdi: nessun arco per la liquidità, letto con l'hook `__lfChart`; senza intercettazione, nessuna nota.
> - **Assunzioni da verificare alla prima corsa**: un solo report per caricamento, `route.fulfill` con il corpo
>   modificato, e l'importo della nota in un solo pezzo (`-8,333.33 € 🇪🇺 EUR`). L'ultima la seguo nel codice.
> - **04:45–04:49, coordinatore**: le E2E di Y3 e Y9 si spostano dopo le 06:45, dopo lo slot dei colori di DV, all'ora
>   che darà. Y10 ha il via, codice compreso, con le prove leggere fino alle 05:25. Alle 06:45:
>   - se Y10 è completo, verde e committato, una sola corsa per Y3, Y9 e Y10;
>   - altrimenti Y10 va salvato come patch fuori dal repo, e la corsa gira sulla HEAD committata.
>   Dalle 05:30 alle 06:45 la macchina è ferma: nessuna prova, si scrive soltanto.
> - **C-34**: la correzione di W a `TransactionBulkModal` è in `dev_release2` (`60917185c`), non ancora nella mia base.
>   La voce dell'elenco ammesso in `escapeHtml.single.test.ts` si toglie insieme all'aggiornamento della base che porta
>   quel commit: tolta adesso, il test diventerebbe rosso, perché nel mio albero la copia c'è ancora.

### Y10 — 54-1, Y-6, decisione 49: il codice ✅ (2026-10-16, 04:45–05:00)

> **Note implementazione**:
> - **`features/dashboard/AllocationHistoryChart.svelte`**:
>   - l'asse ha `min` e `max` in forma di funzione: 0–100 entro un punto di tolleranza, perché le quote arrotondate a
>     due decimali possono sommare 100,01; fuori da quella fascia segue la pila, alla decina successiva;
>   - `stackStrategy: 'samesign'` è dichiarato su ogni serie;
>   - nel tooltip per tipo, le famiglie con valore assoluto > 0,01. La regola dei primi cinque oltre sei, e il
>     «Remaining», contano solo le famiglie positive; quelle negative vengono dopo, ognuna con la sua riga
>     `data-allocation-family`. Per farlo il corpo del ciclo è diventato `familyHtml`;
>   - nel tooltip per settore, le voci negative hanno righe proprie dopo `buildTooltipByThreshold`, che riceve solo i
>     positivi. L'helper condiviso resta com'è.
> - **`features/dashboard/AllocationPanel.svelte`**:
>   - Y-6: `emoji` tolto da `AllocEntry` e da `toAllocEntries`;
>   - `negativeCash()` legge l'`amount` della riga `Liquidity` quando è sotto zero;
>   - la nota `allocation-negative-cash-note` (`dashboard.allocationNegativeCash`, con l'importo scritto da
>     `formatCurrencyAmountPlain` nella valuta mostrata, quindi mascherato con il segno fuori, D8) compare solo nella
>     vista «ora», per tipo e per settore;
>   - la nota è un fratello sotto l'area del grafico, non dentro il contenitore assoluto della torta: per i
>     portafogli senza scoperto il DOM non cambia, e con lui gli scatti. Usa solo utility `*-lf-*`.
> - **`components/charts/AllocationPieChart.svelte`**: il commento «0-100» ora dice che è una quota del totale netto.
> - **i18n**: `./dev.py i18n add` ha messo `dashboard.allocationNegativeCash` nella sorgente `dashboard`, in 4 lingue
>   (EN «Negative cash: {amount}», IT «Liquidità negativa: {amount}», FR «Liquidités négatives : {amount}», con lo
>   spazio prima dei due punti come le altre voci FR, ES «Liquidez negativa: {amount}»). Una riga per lingua.
> - **`moneyRenderSites`**: non serve registrare niente. La nota passa da `formatCurrencyAmountPlain`, uno dei
>   formattatori sicuri; lo conferma `core-unit`.
> - **Runner**: i 2 Vitest sono in `allocation-unit`, con la `desc` estesa. L'E2E è una nuova azione,
>   `front-portfolio allocation-negative-cash`. Le righe `if … return False` le ho scritte su due righe, così ruff
>   resta a 28 come HEAD.
> - **Commento corretto** nel rosso Vitest del pannello: l'endpoint è `POST /portfolio/report`, non
>   `GET /portfolio/summary`.
> - **Rossi → verdi**: `AllocationHistoryChart.negativeCash` 9 su 9, `AllocationPanel.negativeCash` 10 su 10.
>
> **Decisioni notturne, da rivedere**:
> - la tolleranza di un punto sull'asse: uno scoperto sotto l'1 % viene tagliato di meno di un punto, cioè non si
>   vede;
> - i negativi in coda ai tooltip, sotto il «Remaining», come nel grafico, dove stanno sotto lo zero;
> - la nota solo nella vista «ora», perché nella storia lo scoperto è già disegnato;
> - la documentazione per l'utente non è toccata. Se la si vuole, è una frase nella pagina della Dashboard, con le
>   traduzioni.
>
> **Prove leggere** (04:54–05:01, una alla volta con `nice`, prima della fermata delle 05:20): `front check` 0 errori e 0
> avvisi; `allocation-unit` 8 file e 192 test, compresi i 2 ex rossi; `core-unit` 173 file e 6146 test, con
> `moneyRenderSites` e i gate; `component-unit` 149 file e 3939 test; `./dev.py i18n check` pulito;
> `theme-roles --check` pulito; `check-orphans` pulito, con l'E2E nuova registrata; `git diff --check` pulito; ruff
> 28 come HEAD; Prettier pulito. La 6189 è libera.
>
> **Checkpoint Y10** (mandato alle 05:03): 12 percorsi, cioè i 3 componenti, le 4 sorgenti i18n, i 2 Vitest, l'E2E e il
> runner, più il piano per il journal. L'E2E `allocation-negative-cash` non è mai stata lanciata: è nella corsa unica
> di Y3, Y9 e Y10, all'ora che darà il coordinatore.
> - **Salvato**: `1bb8dc990` (`fix(dashboard)`) e `036d957c0` (journal). Poi il merge di `dev_release2` (`2f637d7cb`)
>   senza conflitti: HEAD `4cffd9586`, worktree pulito, verificato. La base contiene `60917185c` (C-34 di W).

### C-34 — la guardia senza l'eccezione temporanea ⏳ (2026-10-16, 05:03; non committata)

> **Note implementazione**: in `TransactionBulkModal.svelte` la copia dell'escaper non c'è più (0 occorrenze dopo
> `60917185c`). Ho tolto la voce dall'elenco ammesso di `escapeHtml.single.test.ts`, che ora ha una sola eccezione,
> `inlineMath.ts`. La sezione «Why it is red today» è diventata «Why it was red before C-34» e racconta le due copie,
> tolte da Y9 e da W. Prettier ha anche rimandato a capo una catena, che sfuggiva perché il file era non tracciato al
> controllo di Y9-1. La guardia dà 6 verdi su 6 (05:04, prima della fermata delle 05:25).
> - La documentazione la aggiorna `docs-writer`, scrivendo e basta: `charts.md`, che ha «Tooltip HTML» e la tabella
>   delle guardie, e `security.md`, «Output Escaping». La build stretta e il controllo dei link si fanno dopo le 06:45.
> - **Dopo le 06:45**, sulla revisione fusa: `api sync`, svelte-check, `allocation-unit`, `core-unit`,
>   `component-unit`, `mkdocs build` e `check-links`; poi la corsa unica delle E2E di Y3, Y9 e Y10.
> - **Documentazione aggiornata** (`docs-writer`, scrivendo e basta, 05:05–05:09): in `charts.md`, «Tooltip HTML» e la
>   riga della guardia nella tabella, e in `security.md`, il terzo punto di «Output Escaping». Ora c'è una sola
>   eccezione, `inlineMath.ts`, e resta la regola per cui un'eccezione che non ha più una copia fa fallire la guardia.
> - **05:07, aggiornamento della base** con il secondo lotto di T (`72e66d1a6`). Delle 27 modifiche di `dev_release2`
>   (`git diff HEAD...72e66d1a6`), l'unico file in comune è il baseline dei colori, il conflitto previsto, da risolvere
>   solo con `theme-roles.mjs --resolve`. Ho chiesto al coordinatore di aprire il merge prima delle 05:25.
> - **05:09, merge risolto** (MERGE_HEAD `72e66d1a6` su `4cffd9586`, aperto dal coordinatore): `theme-roles.mjs --resolve`,
>   poi `--check` pulito. Il baseline fuso ha le 11 righe di Y3 in `features/dashboard/` e non ha le righe che T ha
>   tolto. In stage solo il baseline; il commit di merge lo fa il coordinatore.
> - **La regola dei colori sulle classi miste** (`-lf-` mai su un elemento che ha già classi di tavolozza). La scansione
>   delle righe aggiunte nei `.svelte` dai lotti di stanotte (Y8, Y7, Y4b, Y3, Y9, Y10) e del worktree trova 0 elementi
>   misti, e 0 anche nei file dove ho toccato classi, guardati come sono oggi. Lo script è
>   `/tmp/libreFolio_mixed_scan.py`; non vede le direttive `class:` né gli attributi su più righe.
> - **Merge committato** dal coordinatore: `47c03681a` (genitori `4cffd9586` e `72e66d1a6`), verificato. La riga
>   `~split` di `GrowthChart`, l'unica con `lib/components/dashboard/`, resta perché è un registro storico.
> - **Guardia C-34 sulla revisione fusa**: 6 verdi su 6 (05:10). Anche con il secondo lotto di T dentro, nessun escaper
>   nuovo fuori dall'elenco.
> - **Dopo le 06:45**: svelte-check, `allocation-unit`, `core-unit`, `component-unit`, `api sync`, e per i documenti
>   `mkdocs build` stretto e `check-links`; poi la corsa unica delle E2E di Y3, Y9 e Y10 all'ora del coordinatore
>   (`DEADLINE=HHMM bash /tmp/libreFolio_y3y9y10_e2e.sh`). La guardia e i due documenti vanno nel prossimo lotto.

### Y5 — FE7, broker e lotti in `lib/features/brokers/` ✅ applicato (2026-10-16, 05:12–05:17; via del coordinatore)

> **Note implementazione**: via alle 05:12 per Y5 e poi Y6, solo scrittura. Commit separati, in sequenza: Y5 committato
> subito, poi Y6 sopra, perché i due lotti hanno file in comune (il baseline, `ImportWizardModal.svelte`,
> `files/+page.svelte`, alcune pagine della devWiki). Scelta del coordinatore, prima opzione.
> 1. **Base**: `47c03681a`. Totali prima: 9701/64, 244 file.
> 2. **Spostamento** (`files/y5_move.py --apply`): 42 file. `components/brokers/**` va in `features/brokers/`, con
>    `lots/`; `lotsAnalysisStore` (con il test) in `features/brokers/lots/`; `BrokerIcon` (con il test) in
>    `components/ui/display/`. 52 specificatori riscritti in 28 file.
> 3. **Percorsi** (`files/y5_paths.py --apply`): 65 sostituzioni in 33 file, compreso `theme-roles.mjs:70`, l'eccezione
>    del colore generato dei lotti, solo il percorso.
> 4. **Colori**: `--check` pulito, poi `--update`. 16 righe rinominate a coppie, con conteggi identici, nessun'altra
>    riga. I totali sono identici, 9701/64, e `--check` è di nuovo pulito.
> 5. **devWiki**: 4 righe di «Source files» in `sources/` portate al percorso nuovo, come in Y4b e Y3.
>    `check_source_paths` torna ai 5 di prima.
> 6. **Prettier**: i 67 file del frontend erano già puliti. `git diff --check` pulito.
> - **Restano di proposito**: `designer-lab.md`, di L; gli alberi sintetici di `test_i18n_usage_gate.py`; l'albero di
>   `developer/frontend/index.md`, che si corregge in Y6 per tutti e due gli spostamenti.
> - **Checkpoint**: 143 percorsi (`files/y5_stage_code.txt`), mandato alle 05:17. Le prove leggere vengono dopo le
>   06:45.
> - **Committato**: `6f7ac70ce` (42 rinomine e 59 modifiche), HEAD `6f7ac70ce`.

### Y6 — FE3, i file in `lib/features/files/` ✅ applicato (2026-10-16, 05:17–05:20; sopra Y5 committato)

> **Note implementazione**:
> 1. **Spostamento** (`files/y6_move.py --apply`): 7 file, da `components/files/` a `features/files/`, e 8 specificatori
>    riscritti. `utils/files` e `stores/files` restano dove sono.
> 2. **Percorsi** (`files/y6_paths.py --apply`): 14 sostituzioni in 9 file, compresa la chiave di
>    `htmlSink.gate.test.ts:70`, il gate di K, che si confronta con il percorso (via libera dei colori), e
>    `_frontend_utility.py`.
> 3. **Colori**: `--check` pulito, poi `--update`. Cambia una riga sola, `lib/features/files/FileGrid.svelte 1`, come
>    avevano previsto i colori. I totali sono identici, 9701/64, e `--check` è di nuovo pulito.
> 4. **devWiki**: una riga di «Source files» (`phase-final-bugs-2026-06-25.md:41`, `FilesTable.svelte`) portata al
>    percorso nuovo. `check_source_paths` torna ai 5 di prima.
> 5. **Prettier**: 12 file già puliti; `git diff --check` pulito.
> 6. **Documentazione**: l'albero di `developer/frontend/index.md` lo corregge `docs-writer`, scrivendo e basta, per
>    tutti e due gli spostamenti (`components/brokers/`, `components/files/`, `lotsAnalysisStore`).
> - **L'albero è corretto** (`docs-writer`, 05:18–05:21): via `components/brokers/` e `components/files/`, via
>   `lotsAnalysisStore` dal commento di `stores/portfolio/`; `brokers/` e `files/` aggiunti fra le `features/`, in
>   ordine alfabetico. Nessun'altra riga era vecchia. `designer-lab.md` (`:550` e `:1220`) cita ancora i percorsi
>   vecchi dei broker: è di L, e lo segnalo al coordinatore.
> - **Checkpoint Y6**: 30 percorsi (`files/y6_stage_code.txt`), mandato alle 05:22. Fuori: il lotto C-34 e il piano.
> - **Committato**: `aec49a9cb` (7 rinomine e 16 modifiche), HEAD `aec49a9cb`. La nota su `designer-lab.md` l'ha girata il
>   coordinatore ai colori. Fuori restano solo il lotto C-34 e il piano.

### Dopo le 06:45 — prove leggere su tutto, poi la corsa E2E unica ⏳ (preparato alle 05:25, niente lanciato)

> **Note implementazione**:
> - **Prove leggere**, con `/tmp/libreFolio_after0645_light.sh`, una alla volta con `nice` e il carico sotto 70:
>   - `api sync`, `front check` e `theme-roles --check`;
>   - la guardia C-34;
>   - `chart-safety-unit`, `allocation-unit` e `store-unit` (`lotsAnalysisStore`);
>   - `front-broker broker-unit` e `front-utility onboarding-component-unit`, che hanno test spostati da Y5;
>   - `core-unit`, `component-unit` e `asset-unit`;
>   - `check-orphans`, `mkdocs build` stretto e `check-links`, per i documenti di C-34 e per l'albero di Y6;
>   - `git diff --check`.
> - Poi il coordinatore committa il lotto C-34 e dà l'ora della corsa E2E.
> - **Corsa E2E unica** per Y3, Y9, Y10, Y5 e Y6: `DEADLINE=HHMM bash /tmp/libreFolio_y3y9y10_e2e.sh`, 18 spec in ordine di
>   priorità (circa 88 minuti se partono tutte; lo script salta quelle che non stanno prima della scadenza):
>   - `dashboard`, `allocation-negative-cash`, `asset-detail`, `asset-name-xss`, `fx-detail`, `front-broker detail` e
>     `list`, `front-utility files`, `dashboard-cache`, `fx-flag-font`, `front-user broker-sharing`, `broker-icons`,
>     `files-pdf-offline`, `tx-import-flow`;
>   - poi le extra: `privacy-masking`, `yield-on-cost-real`, `broker-filter-label`, `tx-broker-icon-hydration`.
>   - Se Y5 o Y6 non passano le prove leggere, li correggo con un commit sopra, oppure li toglie il coordinatore prima
>     dell'ingresso.

### Y12a — U8, analisi in sola lettura ✅ (2026-10-16, 05:25–05:30; agente `explore`, durante la fermata; HEAD `aec49a9cb`)

> **Note implementazione**. Le fonti: l'inventario del 43 (righe R17, V11, W7, W8, P4 e P5, e la riga U8 a `:538`), il
> backlog (T-U8 a `:672-675`, J-1 a `:3457-3465`) e il piano di J (`05_numbersAnalysis`; CP-13 «U8 lato backend per Y»
> a `:232`, che dipende da CP-3 e CP-4). I percorsi sono quelli dopo Y3 e Y5. «(a)» vuol dire che basta il frontend,
> «(b)» che serve un campo nuovo del backend.
>
> | Voce | Codice di oggi | Campo del backend | Verdetto | Rosso da scrivere prima |
> |---|---|---|---|---|
> | **W7** | `features/dashboard/ExposureTable.svelte:181`: `nav_weight_percent ?? (valore/NAV)·100` | `nav_weight_percent` c'è già (`schemas/portfolio.py:395`) | **(a)**: togliere il ripiego, così con null si legge «—» | `ExposureTable.test.ts`: con `nav_weight_percent: null`, valore 100 e NAV 1000, la cella dice «—» e non 10 % |
> | **`LotCustodyModal`, valore d'apertura** | `features/brokers/lots/LotCustodyModal.svelte:235-238`: `original_quantity × opening_unit_price`, mostrato a `:313-314`. È anche sbagliato per i lotti trasferiti o rettificati, e sulla valuta | `LotSummarySchema.original_cost` c'è già (`portfolio.py:796`, `:808`), nella valuta di destinazione o null; altri componenti dei lotti lo usano già | **(a)** | `LotCustodyModal.test.ts`: con `original_cost '150'`, quantità 10 e prezzo 10, mostra 150 e non 100; con null, «—» |
> | **Dichiarazioni delle misure interattive** | `charts/signals/MeasureSignal.ts` (R18: Δ, Δ% e annualizzazione), `CompoundSignal.ts` (R19, il «cosa succede se»), `LinearSignal.ts`, `SineSignal.ts` | non serve | **(a)**: una dichiarazione nel codice dell'eccezione e della sua regola (43 `:334`; T-U8) | una guardia che legge il sorgente: i 4 file portano il marcatore, e nessun altro file ha uno schema di annualizzazione senza marcatore |
> | **J-1, `CompoundSignal.ts:69`** | la curva del «cosa succede se» | non serve | **(a)**, insieme alle dichiarazioni | la stessa guardia |
> | **J-1, `features/risk/levels/levelHelpers.ts:359`** | `1/(1−perdita) − 1`, il rendimento che recupera una perdita | nessuno trovato, e nessun checkpoint nominato | **decisione aperta**: un campo del backend (Y12b) o una dichiarazione | dipende dalla decisione |
> | **R17** | `features/dashboard/KpiSection.svelte:80-134` (Δ del giorno e Δ% dalla `history`), `:243` (`mwrr − twrr`) | nessuno a livello di portafoglio; lo porta CP-13 | **(b)** | i valori del backend mostrati così come sono, diversi da quelli che darebbe la `history` |
> | **W8** | `features/dashboard/ExposureTreemap.svelte:442-445`: costo = valore − gl, poi gl/costo | nessun G/L % per gruppo; CP-13 | **(b)** | il tooltip di un nodo mostra il G/L % del gruppo che manda il backend |
> | **P4** | `features/dashboard/PerformanceChart.svelte:200-210`: contributo % = valore/apertura | nessuno; CP-13 | **(b)** | il suffisso del tooltip è il campo del backend |
> | **P5** | `lotComparisonChartHelpers.ts:150-172`, `LotComparisonChart.svelte:524-531`, `unifiedLotsTableHelpers.ts:109-183` | per lotto c'è; per l'aggregato e il piè di tabella no. CP-13 e CP-7 (le regole del realizzato) | **(b)** | l'aggregato e il piè di tabella leggono il backend |
> | **V11** | `LotWacPriceChart.svelte:1413`: il valore di un BUY è `|qty| × prezzo` | per evento no; CP-13. Il riscalamento di `lotWacPriceChartHelpers.ts:109` è solo una scala di visualizzazione | **(b)** per evento; la bolla per lotto potrebbe già usare `original_cost` | il valore della bolla è quello del backend |
>
> - **Conflitti**: nessuno di questi file è di X, W o H.
>   - Sui lotti lavora J (CP-16; e il suo piano a `:2453`, `:2481` e `:2536` tocca `LotCustodyModal` e i suoi helper):
>     prima di toccare `LotCustodyModal` serve un accordo con J.
>   - Il piano R dei colori nomina KpiSection, ExposureTreemap, PerformanceChart, i grafici dei lotti e `MeasureSignal`.
>     Le loro ondate sono finite o non cambiano i componenti; da riconfermare con i colori al momento.
>   - Il T-D9 di J è segnato ✔ su `MeasureSignal.ts:103,133`: prima di dichiarare, controllare se la soglia è già
>     allineata alla casa della matematica.
> - **Ordine proposto per Y12a**, dopo l'ingresso della corsa unica (il codice cambierebbe la build delle E2E):
>   1. W7: il rosso, poi via il ripiego;
>   2. `LotCustodyModal`: il rosso, poi `original_cost`, dopo l'accordo con J;
>   3. le dichiarazioni (4 file e la guardia), dopo aver ricontrollato T-D9;
>   4. `levelHelpers:359`: secondo la decisione.
> - **Decisione notturna, da rivedere**: le dichiarazioni sono un commento-marcatore in testa e una guardia che legge il
>   sorgente, perché un commento da solo invecchia. **Va invece al developer** (lista di domattina, tramite il
>   coordinatore): `levelHelpers:359`. La mia proposta è un campo del backend (Y12b, J), perché non è una misura
>   interattiva e la regola 10 vuole la matematica in un posto solo; l'alternativa è dichiararla come aritmetica di
>   visualizzazione.

### Nota: gallerie e giorno UTC ✅ (2026-10-16, 06:15; avviso di G inoltrato dal coordinatore)

> **Note implementazione**. Il backend ragiona in UTC, quindi due scatti sono confrontabili solo se cadono nello stesso
> giorno UTC: la mezzanotte che conta è alle **02:00 ora locale**. Ho controllato le mie gallerie, leggendo gli orari
> di partenza nei `report.md` dei diff in `LibreFolio_visual_review/diffs/` (`/tmp/libreFolio_y_gallery_days.log`):
>
> | Lotto | A (riferimento) | B (candidato) | Giorno UTC |
> |---|---|---|---|
> | Y1 | `g-final3-r1`, 15/10 09:14 | 15/10 14:46, 15:05, 15:07 | 15/10 per tutti |
> | Y2 | `g-final3-r1`, 15/10 09:14 | 15/10 16:54, 18:00 | 15/10 per tutti |
> | Y7 (mobile) | `g-ref13-r1`, 16/10 00:02 | 16/10 01:33, chiusa alle 01:44:46; diff alle 01:45:32 con 0 immagini mancanti in A | 15/10 per tutti |
>
> - Nessun confronto passa le 02:00: le attribuzioni di Y1, Y2 e Y7 restano valide.
> - **Y-11** non è una galleria: è il JSON di una funzione pura, `timeSeriesAggregation.ts`, che usa solo getter UTC su
>   date fisse e non legge l'orologio. Non dipende né dal giorno né dal fuso.
> - **D'ora in poi**: una galleria fatta dopo le 02:00 di oggi vuole un riferimento preso anch'esso dopo le 02:00 locali
>   del 16/10, per esempio una run del blocco dei colori. `g-ref13-r1` e `g-final3` sono del 15/10 UTC: per questo
>   giorno non valgono più come riferimento.
>
> **Ingresso senza galleria** (decisione del coordinatore, 06:14). Basta la corsa E2E unica: Y3, Y5 e Y6 sono
> spostamenti, Y9 non tocca il markup, e Y10 cambia il DOM solo quando la liquidità va sotto zero. Ho verificato i tre
> punti in cui poteva cambiare qualcosa:
> - **asse di `CorrelationHeatmap`**: `'sans-serif'` è diventato `CHART_FONT_FAMILY`, cioè `'LF Flags', sans-serif`
>   (`chartFont.ts:26`). `'LF Flags'` copre solo `U+1F1E6-1F1FF` e sul Mac usa `local('Apple Color Emoji')`
>   (`static/lf-flags.css:18-24`). Le misure del testo latino e le bandiere restano le stesse;
> - **il campo `emoji` tolto da `AllocationPanel`**: nessuno lo leggeva, perché `AllocationPieChart` prende le emoji
>   dallo store dei settori (`getSectorEmoji`, `:211`) e mai da `entry.emoji`;
> - **asse e impilamento di `AllocationHistoryChart`**: con dati tutti positivi il massimo resta 100 e il minimo 0.
>
> Se servirà una galleria più avanti, il riferimento sarà il candidato dei colori di oggi (06:10–06:50).

### Prove leggere dopo il blocco dei colori ✅ (2026-10-16, 06:48–07:08; HEAD `aec49a9cb`, con il lotto C-34 nel worktree)

> **Note implementazione**. Lo script è `/tmp/libreFolio_after0645_light.sh`: una prova alla volta, con `nice`, e solo se
> il carico è sotto 70; il log di ogni prova è in `/tmp/libreFolio_0645_<prova>.log`. Copre Y3, Y9, Y-11, Y10, Y5 e Y6,
> già committati, più il lotto C-34.
>
> | Prova | Esito |
> |---|---|
> | `api sync` | nessun cambiamento tracciato |
> | `front check` | svelte-check 0 errori, 0 avvisi |
> | `theme-roles.mjs --check` | gate dei colori puliti |
> | guardia C-34 (`escapeHtml.single.test.ts`) | 6/6 |
> | `front-portfolio chart-safety-unit` | 7 file, 72 test |
> | `front-portfolio allocation-unit` | 8 file, 192 test |
> | `front-portfolio store-unit` | 4 file, 52 test |
> | `front-broker broker-unit` | 5 file, 57 test |
> | `front-utility onboarding-component-unit` | 15 file, 449 test |
> | `front-utility core-unit` | 174 file, 6 220 test (gate per percorso e lotti di Y5 compresi) |
> | `front-utility component-unit` | 150 file, 3 980 test (file e broker di Y5 e Y6 compresi) |
> | `front-asset asset-unit` | 20 file, 876 test (il golden di Y-11 compreso) |
> | `check-orphans` | ogni file registrato, ogni test raggiungibile |
> | `check_source_paths.py` | 5 percorsi mancanti su 4 026, già noti e non miei (cartelle generate: `htmlcov-*`, `coverage-js`, una sonda) |
> | `mkdocs build` | nessun avviso; 3 076 URL relativi risolti |
> | `mkdocs check-links` | 97 link validi |
> | `git diff --check` | pulito; porta 6189 libera |
>
> Poi viene l'handoff del lotto C-34, e dopo il suo commit la corsa E2E unica: `DEADLINE=0850`, slot 1, dopo W.

### Corsa E2E unica per Y3, Y9, Y10, Y5 e Y6 (2026-10-16, dalle 07:20; HEAD `be90b30e0`, che è la fusione con dev `1d37087f8`, DV compreso)

> **Note implementazione**.
> - **Prima della corsa**:
>   - la fusione con DV ha portato modifiche alle API (`api/v1/settings.py`, `schemas/settings.py`,
>     `schemas/transactions/transactions.py`), così ho rifatto `api sync`: nessun file tracciato cambiato;
>   - il conflitto nel baseline l'ho risolto solo con `theme-roles.mjs --resolve`, poi `--check` pulito; il commit
>     della fusione l'ha fatto il coordinatore.
> - **Lo script**: `SKIP_API_SYNC=1 DEADLINE=0850 bash /tmp/libreFolio_y3y9y10_e2e.sh`. Una spec alla volta, `--workers 2`.
>   Una spec parte solo se, secondo la sua stima, finisce entro DEADLINE − 2 minuti. I log sono
>   `files/y3y9y10_e2e_<azione>.log` nella cartella della sessione.
> - **La prima spec ha girato da sola**: «Running 27 tests using 2 workers», cioè `dashboard.spec` (26 test più il
>   setup). Il coordinatore temeva che `--workers 2` con un'azione allargasse la corsa a tutta la categoria: non succede.
> - **I 3 test «Live price direction flash» di `asset-detail` sono verdi**, anzi 4 su 4: la correzione di Z tiene.
> - **`allocation-negative-cash`**, alla prima corsa in assoluto: 4/4.
>
> **⚠️ Fuori pista: un rosso in `front-broker detail`, 36 su 37.**
> - Il test è `brokers-detail.spec.ts:553`, «Value presentation toggle…». Cade nell'helper `goToBrokerWithHoldings`, a
>   `:104`: dopo il clic sulla card, `toHaveURL(/\/brokers\/\d+/, {timeout: 5000})` legge `/brokers` per 5 s.
> - **Triage** (skill `test-triage`, ipotesi in ordine):
>   - §1, la forma: no. La card si cerca per nome ed era visibile, e gli altri 16 test che passano dallo stesso helper
>     sono verdi;
>   - §2, l'orologio: sì. Il `load` di `brokers/[id]/+page.ts` non aspetta niente, quindi l'URL cambia quando il codice
>     della pagina di dettaglio è caricato, e ogni test parte da un contesto nuovo, senza cache. Lo stesso test dura
>     4,2 s a macchina scarica (15/10, 14:20), 15,8 s sotto carico (Y8) e 29,2 s qui: è arrivato al clic dopo circa
>     24 s, nel picco di carico della corsa (media su 5 minuti 73,9). I 5 s sono l'attesa più stretta della catena
>     (card 8 s, nome 10 s; il default di `expect` è 3 s);
>   - §3, lo stato condiviso: nel frattempo altri test hanno creato e cancellato 6 broker, ma l'helper filtra per nome,
>     e non c'è nessun segno che la lista si sia mossa sotto il clic.
> - L'istantanea della pagina è andata persa: Playwright pulisce `test-results` alla spec dopo, e in locale non ci sono
>   tracce (`trace: 'on-first-retry'`, 0 ripetizioni).
> - **Verdetto: un'assunzione sul tempo.** Non dipende da Y5, che è solo uno spostamento: la stessa spec era verde nel
>   giro di Y8, sotto carico.
> - **Correzione** (scelta (b) del coordinatore, 07:58): `test-author` cambia i tre punti della spec, `:72`, `:104` e
>   `:140`. Prima si aspetta la pagina di destinazione, `broker-detail-page`, con il tempo della navigazione; poi si
>   controlla l'URL. Dopo la corsa, `front-broker detail` gira da solo nello slot, entro le 08:50. Commit a parte,
>   `test(e2e): …`.
> - **Correzione della nota sul limite di 30 s**: non vale per il test rosso. Il blocco FIFO ha già
>   `test.describe.configure({timeout: 60_000})`, a `:281`. I 30 s di default valgono per gli altri 12 test di
>   `Broker Detail Page`: è un rischio nei picchi di carico, mai visto.
> - **Esteso dal coordinatore** (08:08), nello stesso commit:
>   - `:329`, «View Asset»: la stessa correzione, su `asset-detail-page`;
>   - `test.describe.configure({timeout: 60_000})` come prima istruzione di `Broker Detail Page`.
>
>   Restano solo elencati `:205-206` (ora `:213-214`) e `:33/:35`. La coda del test a `:582` (era `:573`) non gira da
>   luglio: è **Y-12** nel backlog, e il coordinatore porta al developer la decisione sulla funzione.
>
> **Esito della corsa unica** (07:20:02–08:09:58, HEAD `be90b30e0`). Ogni spec da sola, `--workers 2`; in ogni riga i
> test verdi su quelli girati.
>
> | Lotto | Spec |
> |---|---|
> | Y3 | `front-portfolio dashboard` 27/27; `dashboard-cache` 6/6 |
> | Y10 | `front-portfolio allocation-negative-cash` 4/4 |
> | Y9 | `front-asset asset-detail` 33/33; `asset-name-xss` 2/2; `front-fx fx-detail` 17/17; `fx-flag-font` 7/7 |
> | Y5 | `front-broker detail` **36/37**; `front-broker list` 9/9; `front-user broker-sharing` 17/17; `front-portfolio broker-icons` 1/1; `front-transaction tx-import-flow` 10/10 |
> | Y6 | `front-utility files` 29/29; `files-pdf-offline` 1/1 |
> | altre | `privacy-masking` 18/18; `yield-on-cost-real` 2/2; `broker-filter-label` 2/2; `tx-broker-icon-hydration` 2/2 |
>
> In tutto 223 verdi su 224, 18 spec su 18, nessuna saltata per la scadenza. Alla fine la porta 6189 era libera.
>
> **La correzione del rosso.** L'ha scritta `test-author`, senza lanciare niente: +22/−6 in
> `e2e/brokers/brokers-detail.spec.ts`, solo quel file.
> - **I quattro clic che navigano** (`goToFirstBrokerDetail`, `goToBrokerWithHoldings`, il test del clic sulla card e
>   «View Asset»): prima la pagina di destinazione, `broker-detail-page` o `asset-detail-page`, che è la radice
>   incondizionata della route, con 10 s di tempo; poi l'URL, ormai immediato. In SvelteKit 2 l'ordine è: carica il
>   codice della route, poi `pushState`, poi `root.$set`.
> - **`Broker Detail Page`**: `test.describe.configure({timeout: 60_000})` come prima istruzione. Il commento non
>   ricopia «a 30 s finiva il tempo» del blocco FIFO, perché per questo blocco C-58 aveva misurato il contrario
>   (13 s); cita invece i circa 24 s prima del primo clic, misurati oggi a carico 70.
> - **La riprova**, Prettier pulito, poi `front-broker detail` da solo (08:15:39–08:21:11): **37/37** in 3,5 minuti, a
>   carico 45–53. I quattro test toccati durano 7,5–11,4 s, il più lento della spec 16,0 s. Porta 6189 libera.

### Ultima base prima dell'ingresso e prove leggere ✅ (2026-10-16, 08:22–08:32)

> **Note implementazione**.
> - **I commit**: il coordinatore ha salvato la correzione dello spec (`43eea2b9b`) e il journal (`c38fd7f78`).
> - **La fusione**: dev `c94254695`, con dentro il terzo lotto di T, CP-10a di J, W-B32, B39, B44 e il CHANGELOG.
>   - L'unico conflitto, nel baseline, l'ho risolto con `--resolve`; `--check` pulito (baseline +3/−14). Ho messo in
>     stage solo il baseline, e il commit della fusione l'ha fatto il coordinatore: `b84903df8`, con genitori
>     `c38fd7f78` e `c94254695`.
>   - **Ho controllato i file fusi**: nessun riferimento nuovo alle cartelle vecchie, niente che finisca dentro di esse,
>     nessun file mio toccato. I due runner fusi da soli compilano e tengono i miei percorsi.
>   - `api/v1/brokers.py` cambiava l'API.
> - **Le prove leggere sulla revisione fusa**, una alla volta con carico sotto 50 (`/tmp/libreFolio_entry_light.sh`):
>   `api sync` senza cambiamenti tracciati; svelte-check 0/0; `theme-roles --check` pulito; `allocation-unit` 192/192;
>   `core-unit` 6 247/6 247 in 176 file; `component-unit` 4 006/4 006 in 150 file; `git diff --check` pulito; 6189
>   libera.
> - **Nessuna E2E nuova**, per decisione del coordinatore: da dev arrivano classi validate dai colori, più CP-10a, già
>   provato dalle E2E sugli asset. **Y entra così com'è.**

## Y12a — U8, la parte che si fa senza campi nuovi (via del coordinatore, 2026-10-16 08:33)

Base: HEAD `d5c3c3ae3`, cioè la punta di `dev_release2` dopo il treno 104, quello dell'ingresso di Y. Ordine dato dal
coordinatore: W7, poi le dichiarazioni, poi `LotCustodyModal`, ma solo dopo un accordo con J (diff mandato prima di
scrivere). Prove leggere con carico sotto 50; ogni passo si chiude con un checkpoint FROZEN.

### Passo 1 · W7, il peso sul NAV in `ExposureTable` ✅ (2026-10-16)

- **Oggi**: `features/dashboard/ExposureTable.svelte:181` fa
  `nav_weight_percent ?? (currentValue/navAmount)·100`.
  - Il backend riempie il campo solo `if h.current_value:` (`backend/app/services/portfolio_service.py:856`).
  - Il ripiego scatta quindi solo per una posizione che vale 0, oppure con un payload senza il campo; oggi mostra
    «0,0 %».
  - `ExposureTreemap.svelte:408` legge già il campo senza ripiego.
  - `navAmount` serve solo al ripiego: lo passa `PositionsPanel.svelte:203`, che lo ricava a `:123` con
    `parseFloat(summary.net_worth.amount)`.
- **Prima `test-author`** (`ExposureTable.test.ts`):
  - il rosso W7: `nav_weight_percent` nullo, valore 100, `navAmount` 1000. Ci si aspetta «—»; oggi si legge «10,0 %»;
  - il controllo: il peso del backend si mostra così com'è, anche quando valore/NAV darebbe un altro numero;
  - la fixture dei test M-18 riceve il peso dal backend: la loro barriera sul peso finora reggeva sul ripiego;
  - via gli argomenti `navAmount` diventati morti, tranne nel rosso W7, che resta come guardia contro un ripiego
    reintrodotto.
- **Poi il codice**:
  - via il ripiego e la prop `navAmount` da `ExposureTable`;
  - via il passaggio e il valore derivato in `PositionsPanel`.
- **Prove**: il file da solo, poi svelte-check, `component-unit`, `allocation-unit` e `core-unit`.
- **Due difetti del backend, da segnalare a J tramite il coordinatore** (non sono di Y):
  - `portfolio_service.py:856`: con `if h.current_value:` una posizione che vale 0 riceve un peso nullo invece di 0;
    dopo W7 si leggerà «—»;
  - `:852`: con NAV ≤ 0 il denominatore diventa 1, e i pesi non hanno senso.

> **Note implementazione** (2026-10-16).
> - **Il rosso**, scritto da `test-author` (`ExposureTable.test.ts`, +72/−36):
>   - un `describe` nuovo, «the NAV weight is the backend's (W7 / U8)», con un rosso e un controllo. Tutti e due
>     tengono `navAmount: 1000` apposta: dopo W7 è una prop vecchia che il componente ignora, e il test fa da guardia
>     se un ripiego tornasse;
>   - nella fixture, l'opzione `navWeightPercent`;
>   - `cellText` portato a livello di modulo: c'erano due copie locali;
>   - `navAmount` tolto dagli altri 12 montaggi;
>   - M-18 legge ora il peso del backend, `'30.94'`, invece di ricavarlo.
>
>   Prima corsa del file: 15 verdi e 1 rosso, quello giusto (`expected '10.0%' to be '—'`).
> - **Il codice** (10:34, prima della regola dei colori delle 10:45; avvisato il coordinatore per DV):
>   - `ExposureTable.svelte`: via `navAmount` da `Props` e dalla destrutturazione; `:181` diventa
>     `navWeight: safeDecimal(holding.nav_weight_percent)`, con un commento;
>   - `PositionsPanel.svelte`: via il derivato `navAmount` e il suo passaggio.
>
>   Nessuna classe toccata. Il file da solo: 16/16. Prettier pulito.
> - **⚠️ Fuori pista**:
>   - Lo STOP del developer (08:5x–10:32): `test-author` aveva già finito. Ripreso al via, con HEAD e worktree uguali.
>   - Prima corsa delle prove leggere: svelte-check ha trovato 1 errore, in `features/auth/RegisterCard.svelte:100`
>     (`verification_required`, di E). Il client generato del mio worktree era di prima del treno 103 (E5b), che ha
>     aggiunto quel campo (`backend/app/schemas/auth.py:111`). È ambiente, non codice di Y: corsa fermata,
>     `api sync`, poi da capo.
>   - `/tmp` è stato svuotato dal riavvio delle 10:03, e con lui gli script di stanotte. Da ora gli script stanno nella
>     cartella della sessione (`files/scripts/`).
> - **Prove leggere su HEAD `d5c3c3ae3` più il lotto** (10:41–10:55, carico sotto 50; script
>   `files/scripts/w7_light.sh`, log in `files/logs/`): `api sync` senza cambiamenti tracciati fuori dal lotto;
>   svelte-check 0/0; `allocation-unit` 192/192; `core-unit` 6 266/6 266 in 178 file; `component-unit` 4 029/4 029 in
>   154 file, con `ExposureTable.test.ts`; `git diff --check` pulito; 6189 libera.
> - **Checkpoint**: tre file (`files/w7_stage_code.txt`), più il piano.

### Passo 2 · le dichiarazioni delle misure interattive ✅ (2026-10-16)

- **La regola**: `financial-math.instructions.md`, regola 6, e `developer/backend/financial_math.md:303-308`. Le misure
  interattive sono le sole eccezioni, e ognuna va «dichiarata dove vive».
  - La documentazione nomina già i quattro file.
  - Nel codice invece la dichiarazione manca. Il piano 43, a `:1494`, lo annota così: «oggi nel codice non lo sono».
- **La forma**, decisione di Y: un marcatore `@financial-math-exception` nel JSDoc in testa a ciascun file, con la
  regola che vale per quel file:
  - `MeasureSignal.ts` (R18): Δ, Δ% e annualizzato fra i due punti che l'utente sceglie col righello, calcolati nel
    browser;
  - `CompoundSignal.ts`, `LinearSignal.ts` e `SineSignal.ts` (R19): curve «cosa succede se», tracciate dai parametri
    dell'utente.
  - Si tocca solo la testa del file, non le righe di T-D9 (`MeasureSignal.ts:103,134`), che sono di J in CP-14.
- **La guardia, scritta da `test-author`**: `lib/charts/signals/financialMathExceptions.gate.test.ts`.
  - I quattro file portano il marcatore, e solo loro.
  - Nessun `Math.pow(…365…)`, né `** …365…`, in `src/**/*.{ts,svelte}` fuori dai file dichiarati. Sono esclusi i test e
    i file generati.
  - Un controllo positivo su un sorgente finto.
  - Oggi lo schema stretto trova solo `MeasureSignal` e `CompoundSignal`: niente falsi positivi, cioè non
    `CellDateRange` e non le etichette di `ScheduledInvestmentEditor`.
- **La registrazione**: in `chart-safety-unit`, nel mio `_frontend_portfolio.py`, con la descrizione allargata.
  `_frontend_utility.py` (`core-unit`) è un file del programma colori: lo tocco solo se il coordinatore lo chiede.
- **La documentazione, con `docs-writer`**: una frase nella regola 6 di `financial_math.md`, che nomina il marcatore e
  la guardia.
- **Fuori perimetro**: i tre ribasamenti in % di R19 (`chartUtils.ts:12-17`, `backendRenderer.ts:36-39`,
  `AssetComparisonSignal.ts:66-72`). Hanno la loro voce, P2, «un helper frontend».
- **J**: gli scrivo che tocco solo la testa di `MeasureSignal.ts`, prima del suo CP-14.

> **Note implementazione** (2026-10-16).
> - **J è avvisato** (10:40): marcatore e guardia; le sue righe `:103` e `:134` non le tocco.
> - **La guardia**, scritta da `test-author`: `frontend/src/financialMathExceptions.gate.test.ts`, nuova, 14 test.
>   - (A) Ogni file della lista porta il tag in una riga del JSDoc di testa, con almeno 20 caratteri di descrizione.
>   - (B) Nessun altro sorgente porta il tag.
>   - (C) Una potenza con 365 nell'esponente (`Math.pow`, `**`, `**=`) sta solo nei file della lista. La legge con i
>     parser di TypeScript e di Svelte, come `clipboardSink.gate`, quindi commenti e stringhe non contano.
>   - (D) Sette controlli positivi.
>     - Il controllo sul vero albero si ancora solo a `CompoundSignal`: così il CP-14 di J su `MeasureSignal`
>       (T-D9) non può farlo diventare rosso.
>     - Lo stesso controllo verifica che `CellDateRange`, `ScheduledInvestmentEditor` e `LinearSignal` non danno
>       risultati.
>   - Registrata in `chart-safety-unit` (`_frontend_portfolio.py`: lista, docstring, `desc`, `tests`).
>   - I componenti non hanno una forma per dichiararsi: un `.svelte` nella lista fa fallire (A), con un messaggio che
>     lo spiega. Oggi nessun componente è un'eccezione.
>   - Quello che (C) non vede (365 dentro una costante, una formula con `exp` e `log`, un file `.js`) è scritto nella
>     testa della guardia.
> - **Rosso prima dei tag** (11:36, carico 47): 4 rossi, tutti in (A), e 10 verdi.
> - **I tag**, miei: in testa a `MeasureSignal.ts` (prima di `@module`), `CompoundSignal.ts`, `LinearSignal.ts` e
>   `SineSignal.ts`. Dicono cosa calcola la misura e perché resta nel browser, e rimandano alla regola 6 di
>   `financial_math.md`. Le righe di T-D9 non le ho toccate.
> - **Verde dopo i tag** (11:43): la guardia più i test dei segnali (`measureSignal`, `syntheticSignals`,
>   `localSignalRegression`), 98/98 in 4 file. Prettier pulito.
> - **La documentazione**, da `docs-writer`: in `financial_math.md`, due frasi alla fine della regola 6 (come si
>   dichiara un'eccezione e cosa la sorveglia), più una sottosezione nuova in «Guards and Tests».
> - **⚠️ Fuori pista**: i due `test-author` sono stati lenti. Uno ha aspettato che il carico scendesse sotto 50 (era
>   arrivato a 149, con le altre corsie); l'altro si è fermato per l'errore di rete già segnato nel passo 3.

### Passo 3 · `LotCustodyModal`, il valore d'apertura da `original_cost` ✅ (2026-10-16)

- **Il diff proposto**:
  - `lotOpeningValue = lot ? parseNumber(lot.original_cost) : null`, al posto di
    `multiplyOrNull(original_quantity, opening_unit_price)` (`LotCustodyModal.svelte:235-238`);
  - un `data-testid="lot-modal-opening-value"` sul `<dd>` di `:314`;
  - via `multiplyOrNull` (`lotCustodyModalHelpers.ts:133`), che non ha altri chiamanti, e il suo `describe`;
  - il rosso, da `test-author`: un test jsdom che monta il modale con `original_cost` '150' e quantità × prezzo = 100.
    I dati sono incoerenti apposta, per provare quale campo si legge; con `original_cost` nullo ci si aspetta «—».
- **⚠️ Correzione dell'analisi di Y12a**: avevo scritto che il prodotto era «sbagliato per i lotti trasferiti o
  rettificati e sulla valuta». Non è così.
  - Il motore tiene l'invariante `original_quantity × opening_unit_price = original_cost` (`fifo/engine.py:513-516`).
  - `lots_analysis_service.py:730-731` converte i due valori allo stesso cambio, alla data d'apertura.
  - Senza bug visibili, il passo serve all'unica fonte della matematica (regola 10): cambiano solo gli arrotondamenti.
  - La tabella (`UnifiedLotsTable:294`), il grafico WAC (`:1027`) e il Gantt (`:704`) leggono già `original_cost`.
- **CP-16 di J è già dentro** (treno 70): ha toccato `eventDetailItems` (`:172-187`) e `closureValueLabelKey`. Le mie
  righe sono altre.

> **Note implementazione** (2026-10-16).
> - **Il sì di J (10:40)**: nessuno scontro. CP-16 è dentro, CP-13 non tocca il modale né `original_cost`. È lo stesso
>   numero: `|amount|` della riga d'apertura, senza le commissioni registrate come righe FEE, al cambio della data
>   d'apertura.
>   - I casi limite: una rettifica senza costo vale 0, non «—»; un lotto corto vale il nozionale venduto.
>   - **Il vincolo**: il CP-7a di J (solo backend, entra presto) cambia i valori delle righe di chiusura nella
>     cronologia del modale, quindi il test non le fissa.
> - **Il via dei colori (10:55)**: il modale è nell'area di BK, che non lo tocca fino all'ingresso di Y12a; poi migra le
>   classi.
> - **Il rosso**, scritto da `test-author`: `features/brokers/lots/LotCustodyModal.test.ts`, nuovo, in jsdom, con tre
>   test.
>   - Il lotto passa per `schemas.LotSummarySchema.parse`; cronologia vuota.
>   - Il valore atteso si costruisce col formattatore del modale (`formatCurrencyAmountPlain`).
>   - Gli esiti: `original_cost` 150 con prodotto 100, mostra 150; nullo, «—»; il controllo è il caso di J, costo 0,
>     che mostra zero e non «—».
>   - Lo stesso `test-author` ha tolto il `describe('multiplyOrNull')` da `lotCustodyModalHelpers.test.ts` e ha
>     registrato il file nuovo in `broker-unit` (`_frontend_broker.py`: lista, docstring e `desc`).
> - **Il codice, mio**:
>   - `LotCustodyModal.svelte`: `data-testid="lot-custody-modal-opening-value"` sul `<dd>`, chiamato come gli altri
>     test id del modale, con il prefisso `lot-custody-modal-`; `lotOpeningValue = lot ? parseNumber(lot.original_cost) : null`;
>     `multiplyOrNull` tolto dall'import;
>   - `lotCustodyModalHelpers.ts`: via `multiplyOrNull`, che non aveva altri chiamanti.
>
>   Nessuna classe toccata. Nessuna pagina della documentazione o della devWiki nominava il calcolo tolto.
> - **Prove**: prima del codice, il file nuovo fa 2 rossi e 1 verde, i rossi per la ragione giusta
>   (`expected '100.00 EUR' to be '150.00 EUR'` e `… to be '—'`). Dopo il codice, il file nuovo e il test degli
>   aiutanti fanno 42/42. Prettier pulito; `_frontend_broker.py` compila. I log sono in `files/logs/y12a3_*.log`.
> - **⚠️ Fuori pista**: `test-author` si è fermato a metà della fase B per un errore di rete (DNS verso il servizio del
>   modello). Le modifiche ai test e al runner erano già fatte e le ho controllate io; la corsa del rosso l'ho fatta io.

### Decisioni del developer (2026-10-16, 11:19, tramite il coordinatore)

- **P3 / Y11 (decisione 48)**: approvate le mie proposte.
  - Un solo «Aggiorna» per pagina; `risk-refresh-button` sparisce; nessuna rotazione durante l'aggiornamento dei
    prezzi dal vivo.
  - **Il meccanismo, con le parole del developer**: il pulsante gira solo mentre sono in volo le richieste «grandi»,
    quelle che la UI decide a monte. Quando partono, un segnale raggiunge il componente; quando finiscono, bene o male,
    ne arriva un altro. Il componente tiene una lista delle richieste in volo e si ferma quando sono tornate tutte, o
    dopo un timeout lungo, oltre il quale la richiesta si considera persa, almeno per il pulsante.
  - Diventa `pageBusy` con gettoni `begin(label) → token` / `end(token)`, più un timeout per gettone.
  - **Prima il contratto, poi il codice**: l'API, il valore del timeout, e cosa conta come richiesta «grande», pagina
    per pagina.
  - Y11 tocca file `.svelte` delle pagine, nelle aree dei colori: la lista va al coordinatore prima di scrivere.
- **P25 / Y-12**: si **riscrive** il controllo dei bottoni di presentazione sui controlli di oggi.
- **P19**: sì. J aggiunge nel backend il campo del guadagno che recupera una perdita, e Y12b lo usa in
  `levelHelpers.ts`; il nome lo concordo con J.
  - Proposta mandata a J (11:25): per il drawdown attuale il campo **esiste già**, `RiskDrawdownOutput.remaining_to_peak_ratio`
    (`risk/metrics.py:392`, `−cd/(1+cd)`, che è proprio `1/(1−L) − 1`), e il laboratorio lo legge già
    (`assetSetLevels.ts:194`).
  - Per il drawdown peggiore serve un campo nuovo, per esempio `maximum_drawdown_trough_to_peak_ratio`, più una scelta
    sul ripiego da `historical_kpi`.
  - Caso limite segnalato a J: con una perdita totale `:392` divide per zero, e lo schema non ammette il nullo.
  - **La decisione di J (11:30)**:
    - nome `maximum_drawdown_trough_to_peak_ratio`, in `RiskDrawdownOutput` e in `RiskAssetSetDrawdownItem`;
    - forma `Optional[FiniteFloat] = Field(None, ge=0)`, con valore `−MDD/(1+MDD)`; la formula ha una casa sola in
      `financial_math/`, che dà `None` per L ≤ −1;
    - anche `remaining_to_peak_ratio` diventa nullabile, in tutti e due i modelli: dopo `api sync` è
      `number | null`, ma in pratica non è mai nullo, perché la preparazione delle serie rifiuta i prezzi ≤ 0
      (`schemas/risk.py:350`);
    - **niente ripiego dal KPI**: senza `drawdown_summary` si legge «—»;
    - entra con **CP-13**, in un lotto piccolo dopo il J-17 che J ha in corso. J mi manda lo SHA.
  - **In Y12b**: `requiredRecovery` di `levelHelpers.ts:356-360` sparisce; le due righe leggono i due campi.
- **Ordine**: Y12a così com'è, poi Y-12, poi Y11. Y12b dopo, quando ci sono il campo di J e CP-13.

### Prove leggere dei passi 2 e 3 ✅ (2026-10-16, 11:49–11:57; HEAD `93c39a11c` con i due passi nel worktree)

> **Note implementazione**. Script `files/scripts/y12a_light.sh`, una prova alla volta, carico sotto 50; log in
> `files/logs/y12a_*.log`.
>
> | Prova | Esito |
> |---|---|
> | `front check` | svelte-check 0/0 |
> | `theme-roles.mjs --check` | pulito |
> | `front-portfolio chart-safety-unit` | 8 file, 86 test (+1 file e +14 test: la guardia) |
> | `front-broker broker-unit` | 6 file, 60 test (+1 file e +3 test: `LotCustodyModal.test.ts`) |
> | `front-utility core-unit` | 6 261/6 261 in 178 file (−5: il `describe('multiplyOrNull')` tolto) |
> | `check-orphans` | tutto registrato e raggiungibile |
> | `mkdocs build` | nessun avviso; 3 076 URL relativi risolti |
> | `mkdocs check-links` | 97 link validi |
> | `git diff --check` | pulito; 6189 libera |
>
> I checkpoint sono due commit separati, con i file in `files/y12a2_stage_code.txt` (passo 2) e
> `files/y12a3_stage_code.txt` (passo 3), più il journal (`files/y12a_stage_journal.txt`).

## Y11 — il contratto di `pageBusy` (P3, decisione 48) ✅ approvato (2026-10-16, 12:20 e 12:35; nessun codice)

Fonti: le decisioni del developer delle 11:19, e un'indagine `explore` sul codice di oggi (HEAD `9c42584e7`). Il codice
viene dopo Y-12. Il coordinatore chiede ai colori i file delle loro aree (T, DV, BK, AF, TR) e mi gira la risposta
prima che io cominci.

### L'API

Un modulo nuovo, `frontend/src/lib/stores/app/pageBusy.svelte.ts`: solo script, nessun markup.

```ts
export interface BusyToken { readonly id: number; readonly label: string }
/** Past it the request counts as lost, for the button only: the request itself is not cancelled. */
export const PAGE_BUSY_TIMEOUT_MS = 120_000;
export const pageBusy: {
    begin(label: string, options?: {timeoutMs?: number}): BusyToken; // a «big» request starts
    end(token: BusyToken): void;                                     // it came back, well or badly; idempotent
    track<T>(label: string, work: () => Promise<T>, options?: {timeoutMs?: number}): Promise<T>; // begin + finally end
    readonly busy: boolean;              // reactive: at least one token pending on this page
    readonly labels: readonly string[];  // the pending labels, for diagnostics and tests
    reset(): void;                       // drops every token (route change)
};
```

- **La lista**: un `$state` con i gettoni pendenti; `busy` vale «almeno uno». `end` di un gettone sconosciuto, già
  chiuso, scaduto o di prima di un `reset` non fa niente.
- **Il timeout**: ogni gettone ha il suo; quando scade si toglie dalla lista e scrive un `console.warn` con l'etichetta.
  - Il valore è **120 s**. Un gettone avvolge una funzione di caricamento, che può fare fino a tre o quattro richieste
    in fila; ognuna ha il timeout di axios a 30 s (`zodios-client.ts:33`).
  - Le richieste da 120 s (le sincronizzazioni di cambi e prezzi della Dashboard) sono escluse: hanno i loro modali.
  - Si può alzare per chiamata, con `timeoutMs`.
- **La pagina**: `reset()` lo chiama un `onNavigate` nel layout `routes/(app)/+layout.svelte` quando cambia la route
  (`from.route.id !== to.route.id`). Il layout oggi importa solo `afterNavigate`; `onNavigate` scatta prima che la
  pagina nuova si monti, quindi i gettoni del suo primo caricamento non si perdono.
  - Un cambio di parametro nella stessa route (da asset 1 ad asset 2) non azzera: la pagina ricarica comunque, con
    gettoni nuovi.
  - Niente `$app/state` nello store: in Vitest non ha un mock, mentre `$app/navigation` sì.
- **Il pulsante**: in ogni pagina, l'icona gira (`animate-spin`, che non è un colore) e il pulsante è `disabled` (cioè
  grigio) quando vale `pageBusy.busy`. La pressione stessa apre un gettone.
  - Il pulsante pubblica `data-busy="true|false"` per i test (regola 10 della skill design-system).
  - Le radici delle pagine tengono i loro `data-busy` di oggi, su cui contano le spec.
  - Nessuna classe di colore cambia.
- **Le prove**: `test-author` scrive i Vitest dello store (`begin`/`end`, idempotenza, timeout con orologio finto,
  `reset`, `track` con un errore) e adatta le E2E.
  - In E2E si prova il cuore della decisione: sulla Dashboard, un cambio di periodo fa girare `sync-button` senza
    clic, e il pulsante si ferma quando il report torna.

### Dove va `track()`: sui punti che fanno partire, mai dentro le funzioni di caricamento (vincolo di Z-13, 12:35)

- **Il caso**: Z-13 (lotto di Z) a fine aggiornamento dei prezzi ricarica Dashboard e broker **in sfondo**, con
  `loadAll()` e `loadOverview()`. P3 dice che un aggiornamento dei prezzi non fa girare il pulsante.
- **Quindi `track()` sta sui punti che fanno partire il caricamento**, e mai nel corpo di `loadAll`, `loadOverview`,
  `loadBase` o `loadMain`, né negli ascoltatori del bus:
  - la chiamata del primo caricamento in `onMount`;
  - il gestore di «Aggiorna»;
  - gli `$effect` di periodo, ambito, filtro e scheda;
  - l'apertura di un pannello e il cambio dei suoi parametri;
  - nei pannelli del rischio e dei lotti, l'`$effect` di `refreshVersion`, che solo l'«Aggiorna» della pagina fa
    salire (`dashboard :701`, `broker :429`).
- **Il bus** (`stores/portfolio/portfolioMutation.ts`) ha due segnali:
  - `kind: 'mutation'`: una scrittura vista dall'intercettore. Le cache si segnano vecchie e si aggiornano in sfondo,
    senza rotazione;
  - `kind: 'refresh'`, cioè `requestPortfolioRefresh()`, che è l'«Aggiorna» dell'utente.

  **Per Z**: un ricaricamento in sfondo non usa né `requestPortfolioRefresh()` né `refreshVersion`, altrimenti i
  pannelli girerebbero.

### Le richieste «grandi», pagina per pagina

**La regola**: è grande una richiesta che la pagina fa per (ri)costruire quello che mostra perché l'utente o la
pagina l'hanno deciso. Quindi il primo caricamento, «Aggiorna», un cambio di periodo, di ambito, di filtro o di
scheda, e il caricamento di un pannello: quando si apre, quando cambiano i suoi parametri, e quando lo ricarica
l'«Aggiorna» della pagina. La rivalidazione della cache conta solo dentro uno di questi.

**Non lo sono**:
- il poller dei prezzi dal vivo, per decisione del developer;
- le azioni con un modale o un indicatore proprio: sincronizzazione di prezzi e cambi, «Calcola» del PAC, il wizard
  d'import, i salvataggi nei modali;
- le richieste di sfondo piccole: la compatibilità dell'AI Export, i cataloghi dei segnali, le liste per i selettori
  non attese.

| Pagina | Pulsante | Gettoni | Escluse |
|---|---|---|---|
| Dashboard | `sync-button` (`R/dashboard/+page.svelte:964-971`) | `loadAll` (`:559`: primo caricamento, Aggiorna, gli `$effect` di periodo e ambito, la rivalidazione), `loadContribution` (`:627`), `loadPnlCandles` (`:668`), `loadTransactions` (`:315`); il pannello del rischio, `loadBase` (`RiskAnalysisPanel.svelte:456`) | sincronizzazione cambi (`:368`) e prezzi (`:449`); `loadAiExportCompatibility` |
| Broker, lista | `brokers-refresh` (`R/brokers/+page.svelte:371`) | `loadBrokers` (`:152`: primo, Aggiorna, cambio di valuta) | — |
| Broker, dettaglio | `broker-refresh` (`R/brokers/[id]/+page.svelte:599-606`) | `loadBroker` (`:277`), `loadOverview` (`:302`), `loadPnlCandles` (`:353`), `loadContribution` (`:365`), `loadTransactions` (`:382`); il pannello dei lotti, `loadMain` e `loadSelectionHistories` (`LotsAnalysisPanel.svelte:220`, `:264`); il rischio, `loadBase` | AI Export |
| FX, lista | `fx-refresh-all-button` (`R/fx/+page.svelte:1100-1105`; oggi non è mai `disabled`) | `fetchAllPairData` (`:401`: primo e Aggiorna), `loadPairSources` (`:304`) | Sync All (modale); `loadAssetList` (non atteso); l'aggiornamento di una coppia dalla sua card (da verificare: indicatore proprio) |
| FX, dettaglio | `fx-detail-refresh-btn` (`R/fx/[pair]/+page.svelte:1317-1323`) | `loadChartData` (`:743`: primo, Aggiorna, orientamento), `ensureFxRangeLoaded` dei sovrapposti, `maybeLoadComparison` | sincronizzazione (`:1022`); AI Export |
| Asset, lista | **senza test id** (`R/assets/+page.svelte:~1610-1619`; mai `disabled`): gli do `assets-refresh-button` | `loadAssets` (`:536`), `fetchAllPriceData` (primo e Aggiorna) | **il poller dal vivo** (`startActivePolling` `:461`, `refreshLivePricesNow`); Sync All |
| Asset, dettaglio | `asset-detail-refresh-btn` (`R/assets/[id]/+page.svelte:2875-2881`) | `reloadPage` (primo, cambio di asset), `loadChartData` (`:1697`: Aggiorna, intervallo); il rischio, `loadBase` | **il poller dal vivo** (`:1511`); sincronizzazione (`:2198`); AI Export |
| Transazioni | `tx-refresh-button` (`R/transactions/+page.svelte:756-770`) | `reload` (`:128`: primo, Aggiorna, filtri, il ricaricamento leggero dopo una modifica) | i modali di modifica |
| File | `files-refresh-button` (`R/files/+page.svelte:775-776`) | `loadFiles` (`:325`: primo, Aggiorna, scheda) | l'upload e l'import BRIM (UI propria) |
| Tools, hub e host | `tools-hub-refresh` (`features/tools/ToolsHub.svelte:153-160`), `tool-host-refresh` (`ToolHost.svelte:259-266`) | `loadCatalog`, `requestReload` | «Calcola» del PAC |
| Pannelli del rischio | `risk-refresh-button` **tolto** (`RiskPanelHeader.svelte:95-104`, `RiskAnalysisPanel.svelte:596-605`) | — (il rischio si ricarica dall'«Aggiorna» della pagina, tramite `refreshVersion`, che c'è già) | `risk-sync-button` resta |

Impostazioni: `RefreshCw` in `GlobalSettingsTab` e in `CachePanel` è un'azione dei pannelli, non un «Aggiorna» di
pagina; resta fuori, da verificare all'inizio del lotto.

### I file, per area dei colori (vanno al coordinatore prima di scrivere)

- **T**: lo store nuovo (`.ts`); `routes/(app)/+layout.svelte` (solo lo script); `routes/(app)/files/+page.svelte`.
- **DV**: `routes/(app)/dashboard/+page.svelte`, `features/risk/RiskAnalysisPanel.svelte`,
  `features/risk/levels/RiskPanelHeader.svelte`, `features/tools/ToolsHub.svelte`, `features/tools/ToolHost.svelte`.
- **BK**: `routes/(app)/brokers/+page.svelte`, `routes/(app)/brokers/[id]/+page.svelte`,
  `features/brokers/lots/LotsAnalysisPanel.svelte`.
- **AF**: `routes/(app)/fx/+page.svelte`, `routes/(app)/fx/[pair]/+page.svelte`, `routes/(app)/assets/+page.svelte`.
- **X**, fino all'ingresso di FE5c: `routes/(app)/assets/[id]/+page.svelte`.
- **TR**: `routes/(app)/transactions/+page.svelte`.

In ogni pagina cambiano lo script (i gettoni) e, sul pulsante, l'espressione di `animate-spin` e di `disabled`, più
`data-busy`; nessuna classe di colore. Nei pannelli del rischio si toglie un pulsante.

### La risposta dei colori, file per file (coordinatore, 12:25)

- **Lo `<script>` di ogni file è libero subito.**
- **Pulsanti liberi subito**: `routes/(app)/+layout.svelte`, `files/+page.svelte`, `LotsAnalysisPanel.svelte`,
  `dashboard/+page.svelte`. Fa eccezione la radice `<div data-testid="dashboard-page" … aria-busy>` della Dashboard
  (`:825` nella base), che aspetta l'ingresso di DV: non la tocco, il suo `data-busy` resta com'è.
- **Pulsanti dopo l'ingresso dei colori su quel file** (il coordinatore manda lo SHA di ciascuno):
  - AF, verso le 13:00: `fx/+page.svelte`, `fx/[pair]/+page.svelte`, `assets/+page.svelte`;
  - DV, verso le 14:00: `RiskAnalysisPanel`, `RiskPanelHeader` (vince la mia cancellazione), `ToolsHub`, `ToolHost`;
  - BK, verso le 14:45: `brokers/+page.svelte`, `brokers/[id]/+page.svelte`;
  - TR, più tardi: `transactions/+page.svelte`;
  - X: `assets/[id]` dopo FE5c e il suo 9b, come ultimo passo.
- **Ordine di lavoro che ne viene**:
  1. lo store, con il rosso di `test-author` (`store-unit`, nel mio `_frontend_portfolio.py`);
  2. dopo la corsa E2E di Y-12, il layout (`onNavigate`), File e Dashboard, script e pulsanti, e lo script del pannello
     dei lotti;
  3. gli altri pulsanti, a ogni ingresso dei colori.
- **Una regola nuova della skill** (`a317392d4`): `text-lf-primary` più `placeholder:text-lf-placeholder` su un input
  `-lf-`. Y11 non tocca campi.

### Le spec toccate (le adatta `test-author`)

- `risk-real`, `risk-analysis`, `risk-lab`, `data-quality-real`, `yield-on-cost-real` e `privacy-masking` usano
  `risk-refresh-button` o i pulsanti di pagina.
- `dashboard-cache` (`data-busy`).
- `toolbar-width-sweep` e `onboarding-tour` (i pulsanti nella barra).
- `brokers.spec`, `fx-detail`, `fx-destructive`, `transactions-table`, `tx-broker-icon-hydration`, `asset-detail`,
  `asset-mobile-layout`, `ai-export-panel` e `ai-export-memory`.
- La galleria aspetta i `data-busy` di pagina, che restano.
- Nessun Vitest di oggi usa questi test id.

### Domande per il via (risposte del coordinatore, 12:35)

1. `assets/[id]` è di X fino a FE5c: aspetto l'ingresso di FE5c, oppure si concorda con X una modifica piccola allo
   script e al pulsante?
   → **Si aspetta**: X sta dividendo la pagina, e dopo viene il suo 9b. `assets/[id]` è l'ultimo passo di Y11,
   dopo l'ingresso di 9b.
2. Le pagine con `disabled` mancante (lista FX, lista asset) diventano grigie anche loro mentre lavorano: è quello che
   dice la decisione 48 («diventa grigio»).
   → **Sì**, alla lettera della decisione 48.

## Y-12 — riscritto il controllo dei bottoni del confronto dei lotti (P25) ✅ (2026-10-16)

> **Note implementazione**.
> - **Il test morto**, `brokers-detail.spec.ts:569`, l'ha sostituito `test-author` con **due test** e tre aiutanti, nello
>   stesso `describe` FIFO (60 s); +167/−29, Prettier pulito, non ancora lanciato.
>   - **Test A**: un lotto scelto per id; i valori di partenza (modalità Valore, asse Auto, nessun controllo di Rendimento);
>     l'asse di Valore su «Da 0»; poi Rendimento, con i suoi controlli, Abs e il suo asse su Auto: lo «Da 0» di Valore
>     non passa a Rendimento; si torna a Valore, dove l'asse è ancora su «Da 0».
>   - **Test B**: senza lotti scelti, cioè tutti i lotti visibili; in Rendimento, Abs e % e poi l'asse, nei due sensi.
>   - Ogni coppia ha un solo bottone premuto (`aria-pressed`), e dopo ogni clic il grafico si ridisegna: lo prova il
>     contatore di rendering, `chartRenders`.
> - **Correzione al mio brief**: in Rendimento il valore di partenza è **Abs**, non % (`LotComparisonChart.svelte:168`;
>   `returnUnit` è nato in `01b4132bb` già su `'abs'`). Niente finisce in localStorage.
> - **Il lotto si sceglie per stato**: `dt-row-checkbox-{rowId}` e `data-selected` di `DataTable.svelte:1098-1149`, non per
>   classe CSS.
> - **Non si è potuto**: leggere l'opzione di ECharts e provare che l'asse parte da 0. Questo grafico non espone
>   `__lfChart`, quindi il test si ferma allo stato dei bottoni e ai ridisegni.
> - **Trovato fuori perimetro**:
>   - due test vicini (il clic su un segmento del Gantt e quello sulla cella della custodia) controllano la selezione
>     con la classe `selected` e non con `data-selected`. È la regola 10 della skill design-system: **Y-13** nel backlog;
>   - `LotsAnalysisPanel.svelte:125` cita ancora un interruttore «Aggregato/Per-lotto»: è un commento vecchio. Lo
>     correggo in Y11, che tocca quel file;
>   - il pannello non pubblica quando ha finito di caricare i lotti scelti (`selectionLoading`): lo fa Y11, col
>     `data-busy` dei pannelli.
> - **La corsa E2E** (slot 2 del coordinatore, 12:33–12:43, scadenza 13:00): `front-broker detail` da solo,
>   `--workers 2`, **38/38 in 3,9 minuti**, con il carico tra 80 e 168. I due test nuovi durano 15,1 s e 12,2 s. La porta
>   6189 libera alla fine; log in `files/logs/y12_e2e_broker_detail.log`.
> - **Checkpoint**: lo spec (`files/y12_stage_code.txt`) più il journal (`files/y12_stage_journal.txt`).

## Y11 — implementazione (2026-10-16, dalle 12:45)

### Passo 1 · lo store `pageBusy` ✅

> **Note implementazione**.
> - **Il rosso**, scritto da `test-author`: `frontend/src/lib/stores/app/pageBusy.test.ts`, in jsdom, con gli aiutanti
>   `$test/runes.svelte`; 20 test sui gettoni, il timeout, `track` e la reattività. Registrato in `store-unit`, nel mio
>   `_frontend_portfolio.py`: lista, docstring, `desc` e `tests` con tutti e cinque i file. Il rosso (12:52) si ferma
>   all'import: `Failed to resolve import "./pageBusy.svelte"`.
> - **Lo store**, mio: `frontend/src/lib/stores/app/pageBusy.svelte.ts`.
>   - Una lista `$state.raw`, sostituita a ogni cambiamento; un timer per gettone, con un solo `console.warn` quando
>     scade.
>   - Gli id crescono e basta; `track` chiude il gettone in `finally`.
>   - Un `timeoutMs` non valido (zero, negativo, infinito) vale il default.
>   - `reset` è registrato anche su `registerClientSessionReset`, come gli altri store. La domanda era di
>     `test-author`; la scelta è mia.
>   - Verde: 20/20, Prettier pulito.
> - **⚠️ Fuori pista, e una scelta**: le pagine chiamano `track` dentro gli `$effect` (periodo, valuta, filtro).
>   Senza `untrack` lo store, leggendo la sua lista in `begin`, `release` e `reset`, legava l'effetto a sé, che sarebbe
>   ripartito a ogni gettone. Così lo store la legge con `untrack`.
>   - `test-author` ha aggiunto 4 test, fra cui una prova di presenza: l'effetto riparte quando cambia il suo periodo.
>   - **Il rosso l'ho provato io**: rimessa per un momento la versione senza `untrack`, con una copia nella cartella
>     della sessione, i 4 test nuovi sono rossi e gli altri 20 verdi. Poi ho rimesso la versione con `untrack`, identica
>     (stessa checksum). In tutto 24/24.

### Passo 2 · il primo cablaggio, sui file già liberi (risposta dei colori delle 12:25) — prove leggere in corso

> **Note implementazione**.
> - **`routes/(app)/+layout.svelte`**, solo lo script: un `onNavigate` chiama `pageBusy.reset()` quando cambia la route.
>   Il layout è in sintassi vecchia (`$:`): l'aggancio sta accanto ad `afterNavigate`, e la modalità non cambia. Il mock
>   di `$app/navigation` esporta già `onNavigate`.
> - **`files/+page.svelte`**:
>   - una funzione `reloadFiles(label)` avvolge `loadFiles` per chi fa partire il caricamento: Aggiorna, scheda, e i
>     cinque ricaricamenti dopo un upload o una cancellazione. `loadFiles` resta senza gettone;
>   - il primo caricamento è una catena sola: impostazioni, icone, broker e file;
>   - sul pulsante, `disabled` e la rotazione leggono `pageBusy.busy`, e c'è `data-busy`.
> - **`dashboard/+page.svelte`**:
>   - **gettoni** su primo caricamento (dai broker e dagli asset fino al report), Aggiorna, periodo, valuta (l'`$effect`
>     e il selettore), filtro dei broker (dopo i suoi 2 s), scheda transazioni, contributo, candele P&L, e il
>     ricaricamento dopo la creazione di una coppia FX;
>   - **niente gettone** sui ricaricamenti dopo una sincronizzazione (le CTA della qualità dei dati, `onsynced` del
>     rischio, la coppia appena sincronizzata): P3;
>   - `handleSync` tiene `syncLoading`, che alimenta il `data-busy` della radice; la radice resta di DV, non la tocco;
>   - il pulsante legge `pageBusy.busy`.
> - **`LotsAnalysisPanel.svelte`**, solo lo script: gettoni sui tre `$effect` che caricano (apertura e parametri,
>   selezione, `refreshVersion`). Corretto anche il commento vecchio di `:125`, quello trovato in Y-12.
> - **`riskPanelController.svelte.ts`**: gettoni su `applyBaseSignature` (apertura e parametri) e sull'`$effect` di
>   `refreshVersion`.
>   - Non su `handleSynced`, che è una sincronizzazione.
>   - Nemmeno sulle analisi a richiesta, che hanno i loro indicatori.
> - **Nessuna classe toccata.**
>
> **Prove leggere del passo 2** (13:07–13:2x, carico sotto 50; script `files/scripts/y11_light.sh`, log
> `files/logs/y11_*.log`): svelte-check 0/0; `theme-roles` pulito; `store-unit` 76/76 in 5 file; `risk-controller-unit`
> 102/102; `risk-levels-unit` 498/498; `allocation-unit` 192/192; `core-unit` 6 261/6 261; `component-unit`
> 4 029/4 029; `git diff --check` pulito; 6189 libera. **`check-orphans` non è partito**: l'ho fermato mentre lo script
> aspettava il carico, per la pausa del developer. Si rifà dopo il via, perché `page-busy.spec.ts` è registrata ma non
> ancora verificata.
>
> **La E2E del passo 2**, scritta da `test-author` e non ancora lanciata: `frontend/e2e/portfolio/page-busy.spec.ts`,
> registrata come `front-portfolio page-busy` (+20 righe in `_frontend_portfolio.py`). Cinque test:
> 1. un cambio di periodo (`date-preset-6m`) fa girare `sync-button` senza clic;
> 2. «Aggiorna» della Dashboard;
> 3. «Aggiorna» dei File;
> 4. il cambio di scheda dei File;
> 5. l'ambito della pagina: un report della Dashboard trattenuto, poi il link `nav-files`; il pulsante dei File torna
>    fermo mentre il report è ancora in volo.
>
> Le richieste si trattengono con `page.route` e si rilasciano in `finally`; si legge solo `data-busy` e `disabled`.
> Il percorso giusto dei rapporti dei broker è `GET /api/v1/brokers/import/files`.
> - **Le spec che possono cambiare**, segnalate da `test-author` senza toccarle:
>   - `dashboard-cache.spec.ts` (`:474`, `:497`, `:554`): il clic su `sync-button` aspetta il pulsante abilitato;
>   - `ai-export-memory.spec.ts:157`: `toBeEnabled()` entro 3 s;
>   - la galleria (`galleryShot.ts`, `noLoaderOnScreen`, limite 30 s), che ora aspetta anche i caricamenti tracciati
>     prima di ogni scatto della Dashboard e dei File. È il cambiamento più visibile: va detto ai colori.

### ⏸️ Pausa del developer (2026-10-16, 13:2x) — FROZEN

- **HEAD**: `3bf871f4f` (il journal di Y-12). Nessuna fusione aperta.
- **File sporchi, tutti di Y11 e da committare insieme**:
  - modificati: `frontend/src/lib/features/brokers/lots/LotsAnalysisPanel.svelte`,
    `frontend/src/lib/features/risk/riskPanelController.svelte.ts`, `frontend/src/routes/(app)/+layout.svelte`,
    `frontend/src/routes/(app)/dashboard/+page.svelte`, `frontend/src/routes/(app)/files/+page.svelte`,
    `scripts/test_runner/_frontend_portfolio.py`;
  - nuovi: `frontend/src/lib/stores/app/pageBusy.svelte.ts`, `frontend/src/lib/stores/app/pageBusy.test.ts`,
    `frontend/e2e/portfolio/page-busy.spec.ts`;
  - il piano.
- **Il passo dopo, al via**:
  1. uno slot E2E per il passo 2: `page-busy`, `dashboard`, `dashboard-cache`, `files` e `front-broker detail` (il
     pannello dei lotti), circa 30 minuti;
  2. poi il checkpoint del passo 2;
  3. poi gli script e i pulsanti delle altre pagine, all'ingresso di ciascuna area dei colori (AF, DV, BK, TR), e
     `assets/[id]` per ultimo.
- **14:14, ripresa dopo la pausa** (via del coordinatore):
  - `check-orphans` verde: tutti i file registrati e raggiungibili, `page-busy.spec.ts` compreso;
  - lo slot E2E 2 è verso le 15:10, per 30 minuti; lo script è `files/scripts/y11_e2e.sh`;
  - AF è entrato (`bfd33a0f5`): i pulsanti di `fx/+page.svelte`, `fx/[pair]/+page.svelte` e `assets/+page.svelte` sono
    liberi dopo l'allineamento della base, che il coordinatore fa al prossimo checkpoint;
  - Z-13b non tocca più `refreshVersion`; Z-15 (il ricaricamento dei pannelli dopo un aggiornamento dei prezzi) si
    decide dopo Y11.

### Passo 2 · E2E ✅ (2026-10-16, slot 2, 15:10–15:43; HEAD `94e5e146e`, la fusione con dev `b51bb3663`)

> **Note implementazione**.
> - **I commit**: il passo 2 l'ha salvato il coordinatore (`ec018afdf` feat, `77ae9bcd7` journal). Poi la fusione con dev
>   `b51bb3663` (AF, IM, DV, H, W), con commit `94e5e146e`.
>   - L'unico conflitto, nel backlog (Y-13 contro la nuova sezione MF), l'ho risolto tenendo i due lati.
>   - `dashboard/+page.svelte` si è fuso da solo con DV: il pulsante ha i ruoli di DV e i miei attributi.
> - **Le prove leggere sulla revisione fusa**: verdi, tranne **C4 `bg-white/90`**. Quel rosso viene da dev: le ultime
>   occorrenze le hanno tolte IM e DV, senza togliere la regola da `app.css`. L'ho segnalato; i colori l'hanno corretto
>   su dev in `1c7b9def2`.
> - **La E2E**, una spec alla volta, `--workers 2`, script `files/scripts/y11_e2e.sh`, `DEADLINE=1545`:
>   `front-portfolio page-busy` **5/5** (prima corsa); `dashboard` 27/27; `dashboard-cache` 6/6; `front-utility files`
>   29/29; `front-broker detail` 38/38. In tutto **105/105**.
> - **Saltata per la scadenza**: `front-ai-export memory`, da mettere nel prossimo slot.
> - **⚠️ Fuori pista**: la build del primo passo, con il sito della documentazione, ha preso 15 minuti con il carico a
>   80–120; il resto è stato nella norma. Porta 6189 libera alle 15:43.

### Passo 3 · le pagine di AF e DV (2026-10-16, dalle 15:45) — prove leggere verdi, E2E da fare

> **Note implementazione** (base `94e5e146e`, che contiene già gli ingressi di AF e DV).
> - **AF**, con le patch preparate in `files/patches/` e provate a secco sulla stessa revisione:
>   - **lista FX**: gettoni sul primo caricamento (catalogo, coppie e cambi), Aggiorna, periodo, impostazioni che vanno
>     al backend, nuovo tentativo dei segnali, e il ricaricamento dopo la creazione di una coppia.
>     **Senza gettone**: i ricaricamenti dopo una sincronizzazione (P3), l'aggiornamento della singola card (che ha il suo
>     indicatore) e la lista degli asset, che non si aspetta;
>   - **dettaglio FX**: gettoni su primo caricamento, cambio d'utente, orientamento, Aggiorna, periodo, segnali e
>     confronto, nuovo tentativo dei segnali. Senza gettone: il completamento della sincronizzazione di una coppia
>     appena creata, e le sincronizzazioni di coppie e asset (P3);
>   - **lista asset**: gettoni su primo caricamento (catalogo, asset e prezzi), periodo, Aggiorna tutto, aggiornamento di
>     una selezione, impostazioni, nuovo tentativo, e i ricaricamenti dopo la creazione o la modifica di un asset.
>     Senza gettone: il poller dal vivo (`refreshLivePricesNow`), i ricaricamenti dopo una sincronizzazione,
>     l'aggiornamento della singola riga e gli slug FX;
>   - **i pulsanti**: `disabled`, `data-busy` e rotazione su `pageBusy.busy`, più `disabled:opacity-50`, che è
>     un'opacità e non un colore. Il pulsante della lista asset riceve il suo primo test id: `assets-refresh-button`.
>     Prettier ha solo rimesso a capo i miei due pulsanti delle pagine FX.
> - **DV**:
>   - `risk-refresh-button` tolto da `RiskPanelHeader.svelte` e `RiskAnalysisPanel.svelte`, con l'icona e, nel
>     pannello, la funzione `loadBase` che restava senza chiamanti. Restano `risk-sync-button` e il derivato
>     `refreshing`, che serve alle cornici dei risultati;
>   - `ToolsHub` e `ToolHost`: gettoni su catalogo, caricamento dello strumento, Aggiorna, nuovo tentativo e
>     ricaricamento confermato. Il pulsante gira e pubblica `data-busy` su `pageBusy.busy`; `disabled` tiene anche il
>     `busy` locale, così i Vitest di oggi restano validi.
> - **Le spec che cliccano `risk-refresh-button`** (`dashboard-cache`, `risk-real`, `risk-analysis`, `asset-detail`): le
>   adatta `test-author`.
> - **Le quattro spec**, adattate da `test-author`. Nessuna faceva clic su `risk-refresh-button`: tre lo usavano come
>   barriera («l'ondata è arrivata», con `toBeEnabled`) e `asset-detail` controllava solo che mancasse.
>   - `dashboard-cache`: l'aiutante `pressRefresh` aspetta che `sync-button` sia abilitato, poi prende il segno, poi
>     clicca; la barriera diventa `sync-button` `data-busy="false"`, poi `riskSettled`.
>   - `risk-real` (`openRiskTab`): `sync-button` `data-busy="false"`, 90 s.
>   - `risk-analysis`: la stessa barriera, 20 s invece di 15, perché ora aspetta anche il report di 1 anno.
>   - `asset-detail`: via il controllo di assenza di un test id che non esiste più. Prima di armare l'attesa della
>     richiesta c'è ora una barriera: `risk-analysis-panel` `data-busy="false"`.
>   - L'«Aggiorna» del dettaglio asset ricarica davvero il pannello del rischio (`riskRefreshVersion`).
>   - Prettier pulito.
> - **Prove leggere** (15:46–16:01, carico sotto 50; script `files/scripts/y11_light.sh`, log `files/logs/y11_*.log`):
>   svelte-check 0/0; `theme-roles` pulito; store 76; risk-controller 102; risk-levels 498; allocation 192; component
>   4 044 (i Vitest degli strumenti compresi); `check-orphans` pulito; `git diff --check` pulito; 6189 libera.
>   - `core-unit` fa 6 412/6 413: l'unico rosso è il C4 `bg-white/90` ereditato da dev. La correzione dei colori
>     (`1c7b9def2`) non è ancora nella mia base.
> - **Checkpoint**: 11 file (+143/−87), elencati in `files/y11s3_stage_code.txt`, più il piano. La E2E del passo 3 è
>   `files/scripts/y11s3_e2e.sh`, circa 45 minuti:
>   - prima le spec adattate: dashboard-cache, risk, risk-real, asset-detail;
>   - poi le pagine: fx-list, fx-detail, asset-list;
>   - poi `pac-allocator-real` (gli strumenti), `live-pause` e `ai-export memory`.

### Passo 3 · checkpoint e seconda fusione (2026-10-16, 16:04–16:31)

> **Note implementazione**.
> - **I commit**: il passo 3 l'ha salvato il coordinatore, `e843be00c` (11 file) ed `ec2235b00` (journal). Poi la
>   fusione con dev `e9b4ac6b0`, che porta C4 dei colori, Z5, Z-13 e Z-13b di Z, P17 di H, B36b di W e IW.
> - **I due conflitti**, risolti tenendo i due lati:
>   - `dashboard/+page.svelte`: ha litigato solo l'import (`registerPortfolioMutationListener` di Z, `pageBusy` mio).
>     `reloadAfterPriceCatchUp()` di Z chiama `loadAll()` senza gettone, come vuole P3;
>   - `_frontend_portfolio.py`: due funzioni intere e due `add_test` interi, `page-busy` e `price-refresh`.
> - **Gli altri file toccati dalla fusione**: `LotsAnalysisPanel` è stato ricolorato da BK, ma il mio script è
>   intatto; `portfolioMutation` ha ora `kind: 'prices'`, e il mio codice non lo distingue.
> - **⚠️ Fuori pista**:
>   - **una mia svista**: al passo 2 non avevo passato Prettier sulla Dashboard, e la riga di `PositionsPanel` era
>     diventata troppo lunga. Corretta nel worktree, fuori dalla fusione: va col prossimo checkpoint;
>   - `svelte-check` (`front check`) non controlla Prettier. Da ora Prettier gira su ogni file toccato.
> - **Il test che Z ci aveva lasciato**: `page-busy.spec.ts`, scritto da `test-author`. Un aggiornamento dei prezzi
>   simulato con il meccanismo di `price-refresh-reload.spec.ts`; mentre il report di sfondo è trattenuto, `sync-button`
>   resta `data-busy="false"` e abilitato, e un registratore non vede mai `true`. Il controllo è il cambio di periodo a
>   6 mesi, che invece lo fa girare.
>   - `hold().release()` ora usa `route.fallback()`.
> - **Prove leggere sulla revisione fusa** (16:14–16:31): `api sync`; svelte-check 0/0; `theme-roles` pulito; store 82;
>   risk-controller 102; risk-levels 498; core **6 472/6 472** (il C4 se n'è andato con la fusione); component 4 044.
> - **Da dire a Z**: durante il ricaricamento di sfondo la radice della Dashboard è `aria-busy="true"`. P3 riguarda solo
>   il pulsante, e la radice è di DV: è solo una segnalazione.
- **16:31**: commit della fusione `8268f65ec` (genitori `ec2235b00` ed `e9b4ac6b0`). La riga di Prettier e il test P3
  restano per il prossimo checkpoint. Lo slot E2E del passo 3 è verso le 17:10–17:15.
- **Patch pronte per le aree che entrano dopo**, provate a secco su `8268f65ec` e salvate in `files/patches/`:
  - `y11_brokers_list.py` e `y11_broker_detail.py` (BK). Il ricaricamento di sfondo di Z-13 (`reloadAfterPriceCatchUp`)
    e `onsynced` del rischio restano senza gettone;
  - `y11_transactions.py` (TR). I filtri sono lato client (W28), quindi senza gettone;
  - si applicano **solo** quando il coordinatore conferma l'ingresso dell'area. `assets/[id]` arriva dopo FE5c e il 9b
    di X: la sua patch si scrive solo allora, perché X sta dividendo quella pagina.
- **16:56, nota di Z per il passo 4 (BK)**: oggi l'icona di «Aggiorna» nella pagina del broker segue `reportLoading`,
  quindi gira durante il ricaricamento di sfondo di Z-13, contro P3.
  - La patch `y11_broker_detail.py` toglie già `loading || reportLoading` sia da `disabled` sia dalla rotazione: tutti e
    due leggono `pageBusy.busy`.
  - **Al passo 4**: `test-author` estende il test P3 di `page-busy.spec.ts` alla pagina del broker, con lo stesso
    aggiornamento simulato. Durante il ricaricamento di sfondo `broker-refresh` resta `data-busy="false"`.

### Passo 3 · E2E (slot 1, dalle 17:01, scadenza 17:50; HEAD `8268f65ec` più il test P3 e la riga di Prettier) — ✅ 17:44 (155/156, un rosso da sovraccarico da riconfermare)

> **Note implementazione** (`files/scripts/y11s3_e2e.sh`, riepilogo in `files/logs/y11s3_e2e_summary.log`).
> - `front-portfolio page-busy` **6/6**: il test P3 è verde alla prima corsa, cioè l'aggiornamento dei prezzi non fa
>   girare il pulsante.
>   - La build del primo passo, con il sito della documentazione, ha preso 15 minuti, con il carico a 100–140.
> - **⚠️ Fuori pista: `dashboard-cache`, 5/6.** Il rosso è `:420`, «back on the Positions tab…», alla riga 431: il
>   primo `analyzeLots` dell'aiutante (`:271`), con `lots-analysis-panel-loading` ancora presente dopo 30 s e il limite
>   di 120 s del test superato.
>   - **Triage** (skill `test-triage`):
>     - §1, la forma: no. È la stessa riga, con lo stesso lotto;
>     - §2, l'orologio o la lentezza: sì. Il test aveva già speso circa 90 s per login, assestamento della Dashboard e
>       tabella Performance; il carico era 166–172, perché in parallelo girava la galleria completa dei colori (il
>       coordinatore indica 130–170);
>     - l'istantanea finale (`error-context.md`, copiata in `files/logs/`) mostra la tabella dei lotti, che sta nel ramo
>       `{:else}` di `loading` (`LotsAnalysisPanel.svelte:482-550`): il caricamento è finito, solo dopo il tempo del
>       test. Non si è piantato;
>     - lo stesso test era verde al passo 2 (15:31, carico circa 124), con lo stesso pannello tracciato;
>     - il mio cambiamento nel pannello (`track` attorno a `loadMain`) non cambia `loading` e fa partire `loadMain` in
>       modo sincrono, come prima;
>     - il log del backend non registra le richieste dei lotti, e non c'è traccia (nessuna ripetizione in locale).
>   - **Verdetto**: lentezza da sovraccarico della macchina, non un difetto di Y11. **Da confermare** con una corsa di
>     `dashboard-cache` da sola a carico normale.
> - **Il resto è verde** (carico in discesa da 172 a 44):
>
>   | Spec | Esito | Note |
>   |---|---|---|
>   | `front-portfolio risk` | 38/38 | con `risk-analysis` adattata (senza `risk-refresh-button`) |
>   | `front-portfolio risk-real` | 2/2 | adattata |
>   | `front-asset asset-detail` | 34/34 | adattata |
>   | `front-fx fx-list` | 12/12 | |
>   | `front-fx fx-detail` | 17/17 | |
>   | `front-asset asset-list` | 28/28 | |
>   | `front-utility pac-allocator-real` | 1/1 | |
>   | `front-asset live-pause` | 8/8 | |
>   | `front-ai-export memory` | 4/4 | saltata al passo 2 dal limite d'orario, qui è entrata |
>
> - **Totale**: 155/156. La porta 6189 è libera alle 17:44:54 (`lsof` senza ascoltatori).
> - **Resta**: la corsa di conferma di `dashboard-cache` da sola, in uno slot a carico normale.

### Passo 4 · preparazione (17:46–17:52, sola lettura; nessun file del repo toccato)

- **17:46, coordinatore**: BK è in dev (`939e4998a`), quindi il passo 4 è sbloccato da quel lato.
  - **Ordine**: al suo via, prima `prettier --check` e CHECKPOINT READY, poi la corsa di conferma di `dashboard-cache` da
    sola, che apre lo slot E2E del passo 4.
- **Base**:
  - `939e4998a` è già un antenato di `8268f65ec`, e anche TR (`e402d3b87`, 14:57, arrivato con `e9b4ac6b0`). Le patch
    BK e TR provate a secco su `8268f65ec` valgono ancora;
  - si applicano **dopo** il commit del checkpoint e l'eventuale aggiornamento della base, perché file del broker
    sporchi bloccherebbero la fusione;
  - per TR serve il via del coordinatore per `transactions/+page.svelte`, che è un'area colori.
- **Le barriere su `broker-refresh`**: cinque spec aspettano il pulsante abilitato come segno che il report è caricato.
  Restano valide, perché il primo caricamento è tracciato (`broker-first-load`) e si chiude dopo `loadOverview`:
  - `yield-on-cost-real:447` e `data-quality-real:712` aprono `?tab=posizioni`. Lì il pannello dei lotti è un cassetto
    (`open={activeAssetId != null}`), quindi non carica finché non si apre un titolo;
  - `privacy-masking:200` e `:627`, `toolbar-width-sweep:360` e `risk-analysis:1714` aprono la scheda predefinita;
  - `brokers.spec.ts:91` controlla solo che `brokers-refresh` sia visibile.
- **Commenti che diventano falsi**, da far correggere a `test-author`:
  - `risk-analysis.spec.ts:1700-1712` nomina `loading || reportLoading`;
  - `toolbar-width-sweep.spec.ts:358-359` dice «Refresh is disabled exactly while the broker or its report loads».
- **TR, `tx-refresh-button`**: le due spec che lo usano non dipendono dal vecchio `disabled={loading}`:
  - `tx-broker-icon-hydration:320` aspetta il pulsante abilitato, che ora arriva dopo anche le liste di riferimento: è
    più stretto, quindi sicuro;
  - `transactions-table` TT20 aspetta il `data-busy` della radice, che segue ancora `loading`.
- **Coerenza con la Dashboard**: le candele e il contributo sono tracciati allo stesso modo (`dashboard-pnl-candles`,
  `dashboard-contribution` contro `broker-pnl-candles`, `broker-contribution`).
- **`test-author` al passo 4**:
  - estende `page-busy.spec.ts` alla pagina del broker: durante il ricaricamento di sfondo dopo un aggiornamento dei
    prezzi, `broker-refresh` resta `data-busy="false"`, mentre un cambio di periodo lo fa diventare `true`;
  - aggiunge il caso della lista dei broker (`brokers-refresh`) e, con TR, quello delle transazioni;
  - corregge i due commenti.
- **Script E2E**: `files/scripts/y11s4_e2e.sh`, con `DEADLINE=HHMM` e TR opzionale (`WITH_TR=1`):
  1. `dashboard-cache` come conferma, prima: ha 6 test, quindi la guardia contro l'allargamento la legge ancora;
  2. `page-busy`, `front-broker detail`, `front-broker list`;
  3. con TR: `transactions-table` e `tx-broker-icon-hydration`;
  4. `risk`, `privacy-masking`, `yield-on-cost-real`, `data-quality-real`, `toolbar-width-sweep`, `default-currency` e
     `price-refresh`.
  - Circa 60 minuti in tutto, 68 con TR: la guardia della scadenza salta la coda, da recuperare in uno slot successivo.
- **18:00, conferma di `dashboard-cache`**: da sola, con `--workers 2`, su `8268f65ec` più i tre file del checkpoint.
  - **6/6 in 36 s**, con il carico da 70 a 41; `:420` è verde.
  - Il verdetto sul rosso delle 17:21 è confermato: lentezza da sovraccarico.
- **Checkpoint**: il coordinatore ha committato `3324a9f59` (test P3 e riflusso della Dashboard) e `d99f7987d` (journal).
  HEAD è `d99f7987d`, con l'albero pulito.

### Passo 4 · BK e TR (dalle 18:02, su `d99f7987d`) — ✅ codice e prove leggere 18:29; E2E da fare

> **Note implementazione**.
> - **Via del coordinatore**:
>   - applicare le patch;
>   - `transactions/+page.svelte` è libero, e lui avvisa il programma colori;
>   - nessuna classe di palette, e `theme-roles --check` fra le prove leggere.
> - **Patch applicate** (`files/patches/y11_brokers_list.py`, `y11_broker_detail.py`, `y11_transactions.py`): ogni
>   ancora è stata trovata una sola volta, quindi nessuna scrittura parziale.
>   - **Lista dei broker**:
>     - gettoni sul primo caricamento, sul cambio di valuta, sui ricaricamenti dopo creazione, modifica e cancellazione,
>       e sul clic di `brokers-refresh`;
>     - il pulsante pubblica `data-busy` e legge `pageBusy.busy`;
>     - la radice `brokers-page` tiene il suo `data-busy`, che segue `loading`.
>   - **Pagina del broker**:
>     - gettoni sul primo caricamento, sul periodo, su «Aggiorna», sulla valuta, sulla prima apertura della scheda
>       Transazioni e su `handleUpdated`;
>     - anche sullo storico dell'allocazione, chiesto quando l'utente sceglie la vista Storico o quando questa viene
>       ripristinata al montaggio, e su candele e contributo, come nella Dashboard;
>     - `reloadAfterPriceCatchUp` resta senza gettone (P3). Il pulsante non segue più `reportLoading`, quindi non gira
>       più durante il ricaricamento di sfondo: è la correzione chiesta dalla nota di Z.
>   - **Transazioni**:
>     - gettoni sul primo caricamento (prima le liste di riferimento, poi `reload()`), sui ricaricamenti morbidi dopo le
>       modifiche dell'utente e sul clic di `tx-refresh-button`;
>     - la radice `transactions-page` tiene il suo `data-busy`, che segue `loading`;
>     - la pagina non ha ascoltatori dei prezzi.
> - **Prettier**: le tre pagine erano pulite a HEAD. `--write` ha riformattato solo le mie due righe lunghe, cioè il
>   pulsante della lista e la riga di `GrowthChart` della pagina del broker. `--check` è pulito su tutte e tre.
> - **`theme-roles --check`**: pulito («0 files dropped below their record»). Nessuna stringa di classe è cambiata:
>   solo `disabled`, `data-busy`, il gestore del clic e la condizione della rotazione.
> - **`test-author`** (dalle 18:06 alle 18:26; non ha eseguito nulla tranne Prettier):
>   - `page-busy.spec.ts` (+269/−16): quattro test nuovi, mentre i sei vecchi restano com'erano.
>     - **Pagina del broker, P3**: tiene fermo il ricaricamento di sfondo dopo un aggiornamento simulato dei prezzi.
>       Intanto `broker-refresh` resta `data-busy="false"` e abilitato, e il registratore non vede mai `true`; vale
>       anche dopo l'arrivo del ricaricamento. Il controllo è il preset 6M: il pulsante diventa occupato e il
>       registratore vede `true`.
>     - **Pagina del broker, «Aggiorna»**: tiene fermo l'overview richiesto di nuovo.
>     - **Lista dei broker**: tiene fermo `GET /brokers?include_inaccessible=true`.
>     - **Transazioni**: tiene fermo `GET /transactions` senza query.
>     - Il broker è «Interactive Brokers» del mock, cercato per nome con `page.request`. Non si scrive nulla.
>   - Correzioni di soli commenti in `risk-analysis.spec.ts` (`openBrokerRiskWithHoldings`) e in
>     `toolbar-width-sweep.spec.ts` (`brokerDetailReady`); il `desc=` di `page-busy` in `_frontend_portfolio.py`.
> - **Revisione**:
>   - nessun `waitForTimeout`, nessun `.first()`, nessun testo tradotto; ogni richiesta trattenuta viene rilasciata
>     nel `finally`;
>   - **⚠️ Fuori pista, contatore nella pagina**. La radice della pagina del broker non pubblica `data-busy`. Per
>     sapere quando il ricaricamento di sfondo è arrivato, la spec avvolge `XMLHttpRequest.open/send` con
>     `page.evaluate` e conta i report inviati e arrivati: un report conta come arrivato un task dopo il suo
>     `loadend`. Prima di fidarsi di un arrivo, la spec controlla di vedere il report in volo.
>   - L'ho accettato. Aggiungere un `data-busy` alla radice scavalcherebbe la voce di Z sull'`aria-busy` della
>     radice durante i ricaricamenti di sfondo, e P3 vuole quel ricaricamento silenzioso.
> - **Prove leggere** (`files/scripts/y11s4_light.sh`, dalle 18:27 alle 18:29, carico 21–24):
>   - svelte-check: 0 errori e 0 avvisi, `e2e/**` compreso;
>   - `theme-roles`: pulito;
>   - `core-unit`: 6 472/6 472;
>   - Prettier: pulito sui sei file;
>   - `py_compile` di `_frontend_portfolio.py`: superato;
>   - `git diff --check`: pulito.
> - **⚠️ Fuori pista, un caso di P3 rimasto** (trovato da `test-author`, verificato nel codice, segnalato alle 18:26):
>   - il ricaricamento di sfondo azzera le candele: nella Dashboard `applyReport` alla riga 524, nel broker
>     `applyOverview` alla 335; nel broker azzera anche il contributo, alla 331;
>   - nella vista Candele `GrowthChart` (976–980) le richiede di nuovo, e nella vista Performance del broker
>     `PositionsPanel` (112–116) richiede il contributo;
>   - entrambe le callback sono tracciate, quindi il pulsante gira per tutta quella richiesta. Nella Dashboard succede
>     dal passo 2.
>   - **Decisione N55 del coordinatore** (da rivedere con il developer): l'opzione 1, `pageBusy.join`. Candele e
>     contributo tengono fermo il pulsante solo se si aggiungono a un caricamento già in corso.
>   - Va fatta come **passo 4b**, dopo il checkpoint del passo 4, con i test Vitest del metodo e il test P3 con la
>     vista Candele salvata.
> - **BACKLOG**:
>   - Y-14: «Aggiorna» della lista dei broker rilegge solo l'elenco;
>   - Y-15: il `title="Refresh"` di `brokers-refresh` è scritto in inglese nel codice. Il coordinatore chiede di
>     proporre la parola, «Refresh» o «Reload», nelle quattro lingue, insieme agli altri pulsanti «Aggiorna»; sceglie
>     il developer.
> - **Conflitti previsti**: nessuno. Dev è a `5609b16d7`, 97 commit avanti, e non tocca i miei percorsi. Nel BACKLOG le
>   sue modifiche finiscono intorno alla riga 4 297, mentre la sezione Y comincia alla 4 439.
> - **Script E2E** `files/scripts/y11s4_e2e.sh`, rivisto: la conferma di `dashboard-cache` è già fatta e TR è applicato.
>   L'ordine è `page-busy`, `front-broker detail` e `list`, `transactions-table`, `tx-broker-icon-hydration`,
>   `price-refresh`, `default-currency`, `risk`, `privacy-masking`, `toolbar-width-sweep`, `yield-on-cost-real` e
>   `data-quality-real`.
> - **Documentazione, da fare alla chiusura di Y11** con `docs-writer`, insieme alla riga del CHANGELOG. Ricerca fatta
>   sulle pagine inglesi di `mkdocs_src/docs`: né `risk-refresh-button` né `pageBusy` vi compaiono.
>   - `user/dashboard/index.en.md`, sezione «Coming back and refreshing» (riga 81): oggi non dice che «Refresh» gira ed
>     è grigio mentre la pagina carica ciò che l'utente ha chiesto, né che non lo fa durante un ricalcolo di sfondo
>     (P3);
>   - `user/brokers/index.en.md:86`: lo stesso, per la pagina del broker;
>   - `user/dashboard/risk.en.md:139` («press **Refresh**») resta vero, perché dal passo 3 il «Refresh» della pagina
>     ricarica la scheda Rischio. Basta, al più, un collegamento alla sezione della Dashboard;
>   - lato sviluppatori manca una pagina sullo schema `pageBusy`: dove va `track`, mai dentro le funzioni di
>     caricamento, e niente gettoni sui ricaricamenti di sfondo.
- **Checkpoint del passo 4**: il coordinatore ha committato `fba7b036d` (feat) ed `e24ef7a2f` (journal); HEAD
  `e24ef7a2f`, con l'albero pulito. Un'unica E2E per il passo 4 e il 4b nello slot 1, verso le 20:00, per 60 minuti. Se
  le prove leggere del 4b non sono verdi per quell'ora, la corsa copre solo il passo 4.

### Passo 4b · `pageBusy.join` (N55, dalle 18:32, su `e24ef7a2f`) — ✅ codice, test e prove leggere 18:54; E2E verso le 20:00

> **Note implementazione**.
> - **Decisione N55 del coordinatore**, da rivedere con il developer: l'opzione 1. Le richieste che un pannello fa da
>   sé quando gli mancano i dati (candele e contributo) tengono fermo il pulsante solo se si aggiungono a un
>   caricamento già in corso.
> - **Store**: `join(label, work, options?)`, asincrona.
>   - Se nella lista letta con `untrack` non c'è nessun gettone, esegue `work()` senza gettone; altrimenti fa `track`.
>   - Decide nel momento della chiamata.
>   - È esportata in `pageBusy`, e l'intestazione del file ha una voce che spiega dove va.
> - **Le quattro callback** passano da `track` a `join`, con le stesse etichette: `dashboard-pnl-candles`,
>   `dashboard-contribution`, `broker-pnl-candles` e `broker-contribution`.
> - **Perché regge nel tempo**:
>   - quando l'utente cambia periodo, `applyReport` o `applyOverview` scrivono lo stato prima che finisca il caricamento
>     tracciato. Svelte svuota gli effetti in un microtask, messo in coda prima della continuazione di `track`, quindi
>     il `$effect` di `GrowthChart` o di `PositionsPanel` trova ancora il gettone del periodo;
>   - lo verifica in un browser vero il controllo dei nuovi test E2E.
> - **Sfumatura da riportare**: il contributo ha un indicatore proprio (`contributionLoading`, presente in entrambe le
>   pagine), le candele no.
>   - `GrowthChart` ha solo lo scheletro della storia (`loading`).
>   - Quindi, se l'utente passa direttamente alle Candele a pagina ferma, nessun indicatore lo segnala finché le
>     candele non arrivano. Era così anche prima di Y11.
>   - Ho tolto dall'intestazione dello store la frase «il pannello mostra il suo caricamento».
> - **Prettier**: pulito sui tre file.
> - **`test-author`** (in corso, dalle 18:33):
>   - Vitest di `join` in `pageBusy.test.ts`, con tre test pensati per distinguere le varianti: sempre tracciata, mai
>     tracciata, senza `untrack`;
>   - due test E2E in `page-busy.spec.ts`: la Dashboard con la vista Candele salvata, e la pagina del broker con la
>     vista Performance. Ciascuno ha un controllo: il cambio di periodo tiene il pulsante occupato finché la richiesta
>     a cascata è trattenuta.
> - **Consegna di `test-author`** (alle 18:47; non ha eseguito nulla tranne Prettier):
>   - `pageBusy.test.ts` (+222/−5): da 24 a 35 casi; i 24 vecchi restano intatti.
>     - Nove casi per `join`: pagina ferma, pagina occupata, decisione presa alla chiamata, rifiuto con e senza
>       gettone, eccezione sincrona che diventa una promessa rifiutata, `timeoutMs`;
>     - due casi di `join` chiamata dentro un effetto, con gli stessi aiutanti dei test di `track`.
>   - `page-busy.spec.ts` (+291/−6): due test nuovi.
>     - Il primo è la Dashboard con la vista Candele salvata. Il secondo è la pagina del broker con la vista Performance
>       salvata in `?tab=posizioni`.
>     - Ogni test tiene fermi il ricaricamento di sfondo e la richiesta a cascata (candele o contributo). Intanto il
>       pulsante resta fermo e il registratore non vede mai `true`.
>     - Il controllo è il cambio di periodo a 6M: la richiesta a cascata, trattenuta, tiene occupato il pulsante. Nel
>       broker si controlla anche che il pannello mostri il proprio caricamento (`positions-panel` con
>       `data-busy="true"`).
>     - Le viste salvate si impostano con una prima visita, prima di installare la finta notifica di aggiornamento dei
>       prezzi; poi la pagina viene ricaricata da zero.
>     - Timeout di 180 s per test (`CASCADE_TEST_MS`). `openBrokerDetail` accetta ora una scheda, `panoramica` se non
>       indicata.
>   - Il `desc=` di `page-busy` in `_frontend_portfolio.py`.
> - **Prova per mutazione** (`files/scripts/y11s4b_mutations.sh`, dalle 18:48 alle 18:51):
>   - punto di partenza: `store-unit` **93/93**;
>   - M1, `join` sempre tracciata: **3 rossi**;
>   - M2, `join` mai tracciata: **5 rossi**;
>   - M3, la lista letta senza `untrack`: **2 rossi**, i due test degli effetti;
>   - file ripristinato con lo stesso SHA-256 (`f883cb88…`).
> - **Prove leggere** (`files/scripts/y11s4b_light.sh`, dalle 18:49 alle 18:54, carico 33–39):
>   - Prettier pulito sui cinque file; `py_compile` superato;
>   - svelte-check 0 errori e 0 avvisi; `theme-roles` pulito;
>   - `store-unit` 93/93; `core-unit` 6 472/6 472;
>   - `git diff --check` pulito; la porta 6189 è libera.
> - **Osservazioni di `test-author`**, verificate:
>   - nel broker, `loadOverview` applica subito l'overview in cache, che non contiene il contributo, quindi la
>     richiesta a cascata parte prima ancora dell'overview. È innocuo, ed è il motivo per cui i due blocchi delle
>     richieste vengono installati prima che la finta notifica cambi stato;
>   - il lato positivo del controllo dipende dalla tempistica di Svelte, verificata su 5.48. Se un giorno cambiasse,
>     il controllo diventerebbe rosso: è il segnale che N55 si è rotta;
>   - **Y-16**: una vista Candele salvata si carica su una pagina nuova solo per una dipendenza involontaria
>     dell'effetto. Era così anche prima;
>   - **Y-17**: i pulsanti di `PositionsPanel` non pubblicano `aria-pressed`.
>   - Più la mia **Y-18**: le candele non hanno un indicatore di caricamento.
>   - Tutte e tre sono nel BACKLOG.

### Y-15 · proposta della parola per i pulsanti «Aggiorna» (per il developer; 16/10 18:38)

Il coordinatore chiede di proporre la parola, «Refresh» o «Reload», nelle quattro lingue, per tutti i pulsanti
«Aggiorna» delle pagine; la scelta spetta al developer. Inventario fatto in sola lettura su `e24ef7a2f`; i valori
vengono dal catalogo generato alle 18:27.

| Pagina | Pulsante (`data-testid`) | Chiave di oggi | EN | IT | FR | ES |
|---|---|---|---|---|---|---|
| Dashboard | `sync-button` | `dashboard.syncData` | Refresh | Aggiorna | Actualiser | Actualizar |
| Pagina del broker | `broker-refresh` | `dashboard.syncData` | Refresh | Aggiorna | Actualiser | Actualizar |
| Lista dei broker | `brokers-refresh` | nessuna: `title="Refresh"` scritto nel codice | Refresh | Refresh | Refresh | Refresh |
| Transazioni | `tx-refresh-button` | `transactions.refresh` | Refresh from server | Ricarica dal server | Actualiser depuis le serveur | Recargar desde el servidor |
| File | `files-refresh-button` | `common.refresh` | Reload | Ricarica | Recharger | Recargar |
| Dettaglio cambio | `fx-detail-refresh-btn` | `common.refresh` | Reload | Ricarica | Recharger | Recargar |
| Dettaglio asset | `asset-detail-refresh-btn` | `common.refresh` | Reload | Ricarica | Recharger | Recargar |
| Strumenti (hub e strumento) | `tools-hub-refresh`, `tool-host-refresh` | `common.refresh` | Reload | Ricarica | Recharger | Recargar |
| Lista dei cambi, lista degli asset | `fx-refresh-all-button`, `assets-refresh-button` | `sharedResource.refreshAll` | Reload All | Ricarica Tutto | Recharger Tout | Recargar Todo |

- **Oggi ci sono tre parole per la stessa azione.** La documentazione utente dice «**Refresh**» (`dashboard/index.en.md`,
  `brokers/index.en.md`).
- `common.refresh` non serve solo a questi pulsanti: lo usano anche il ricaricamento di una singola scheda o riga
  (`AssetCard`, `AssetTable`, `FxCard`, `FxTable`), il modale dei file del broker, i pannelli degli strumenti, il
  prefisso di due avvisi di errore e un'etichetta delle azioni di gruppo. Se ne cambio il valore, cambiano anche tutti
  questi.
- **Proposta A (consigliata): «Refresh»**, con una chiave dedicata al pulsante della barra della pagina, per esempio
  `common.refreshPage` in `i18n/base/`.
  - Valori: EN «Refresh», IT «Aggiorna», FR «Actualiser», ES «Actualizar», cioè i valori di oggi di
    `dashboard.syncData`.
  - Varianti «tutto» per le liste dei cambi e degli asset: «Refresh all», «Aggiorna tutto», «Tout actualiser»,
    «Actualizar todo».
  - `common.refresh` («Reload») resta ai ricaricamenti di una singola scheda o riga e dei pannelli, oppure si allinea
    anche quello: lo decide il developer.
  - Perché:
    - è la parola della documentazione e delle due pagine più viste;
    - l'icona è quella di «refresh»;
    - «Reload» fa pensare al ricaricamento della pagina nel browser, che il pulsante non fa: richiede i dati senza
      ricaricare la pagina.
- **Proposta B: «Reload» ovunque**, cioè EN «Reload», IT «Ricarica», FR «Recharger», ES «Recargar». Cambiano le
  etichette della Dashboard e della pagina del broker, e la documentazione passa da «Refresh» a «Reload».
- Dopo la scelta: un `$_()` sulla chiave scelta per gli undici pulsanti, Y-15 compreso, con le chiavi nelle quattro
  lingue (skill `devpy-i18n`). Le spec E2E usano i `data-testid`, quindi i testi non le toccano.

### Y12b · sbloccato: CP-13a di J è in dev (`0452e592c`; messaggio di J delle 18:39)

- **Campo nuovo** `maximum_drawdown_trough_to_peak_ratio` (`number | null`, ≥ 0) in `RiskDrawdownOutput`
  (`drawdown_summary`) e in `RiskAssetSetDrawdownItem` (`asset_set_drawdown`).
  - È il guadagno che serve per tornare dal punto più basso al massimo precedente, `−MDD/(1+MDD)`.
  - Vale 0 senza drawdown e null in caso di perdita totale.
  - Lo calcola `financial_math/returns.py::required_recovery_return`.
- **`remaining_to_peak_ratio`** ora è `number | null`; è null solo in caso di perdita totale e viene dalla stessa
  funzione.
- **Perdita totale**: il risultato porta l'avviso `total_loss_no_recovery`, con `degrades_result=false`, quindi lo stato
  resta `ok`.
  - Chiavi: `risk.warnings.total_loss_no_recovery`, e `risk.warnings.total_loss_no_recovery_assets` con
    `{count}`/`{names}`, già in `i18n/risk/*`.
  - Con i prezzi salvati in pratica non succede: serve un valore che arrotondi esattamente a −100 %.
- **Versioni**: `drawdown_summary` 1.2.0, `asset_set_drawdown` 1.1.0.
- **Da fare in Y12b, dopo l'aggiornamento della base**:
  - `levelHelpers.ts` legge i due campi (la riga peggiore intorno alla 411, quella corrente intorno alla 444), senza
    ripiego sui KPI;
  - `requiredRecovery` (360 circa) sparisce;
  - `api sync` per i tipi nuovi.
- **Riferimenti scaduti, da sistemare in Y12b**:
  - `developer/frontend/components/features/risk-lab.md:285-287` descrive `requiredRecovery()`, con righe di
    `L1HowMuchItHurts.svelte` già sbagliate: ora sono 152-155 e 182-183;
  - il commento in `levelHelpers.ts:137-141` dice che il ripiego per settore è «l'unico avviso» con
    `degrades_result=false`, e non è più vero.
- **Conflitti previsti all'aggiornamento della base**: la fusione `0452e592c` tocca solo il BACKLOG fra i miei file,
  nella sezione di J.

### Passo 4 + 4b · E2E (slot 1, dalle 18:55, scadenza 20:00; HEAD `1c3f6a432`) — ✅ 19:30, 180/180

- Il coordinatore ha committato il 4b: `7f0a07b9d` (feat) e `1c3f6a432` (journal).
  - N55 e Y-18 vanno nella revisione con il developer, e anche Y-15 con la proposta «Refresh / Aggiorna…».
- Script: `files/scripts/y11s4_e2e.sh` con `DEADLINE=2000`. Riepilogo in `files/logs/y11s4_e2e_summary.log`.

> **Note implementazione**: tutte e 12 le spec verdi alla prima corsa, **180/180**, dalle 18:55:31 alle 19:29:54,
> con il carico fra 25 e 88. Alle 19:29:54 la porta 6189 è libera (`lsof` non trova processi in ascolto).
>
> | Spec | Esito | Cosa copre |
> |---|---|---|
> | `front-portfolio page-busy` | 12/12 | 6 vecchi, 4 del passo 4 (P3 e «Aggiorna» del broker, lista dei broker, transazioni), 2 di N55 (viste Candele e Performance salvate) |
> | `front-broker detail` | 38/38 | la pagina del broker |
> | `front-broker list` | 9/9 | la lista dei broker |
> | `front-transaction transactions-table` | 25/25 | TT20, cioè «Aggiorna» con il `data-busy` della radice |
> | `front-transaction tx-broker-icon-hydration` | 2/2 | barriera su `tx-refresh-button` |
> | `front-portfolio price-refresh` | 3/3 | ricaricamento di sfondo di Z-13, nella Dashboard e nel broker |
> | `front-portfolio default-currency` | 6/6 | gettoni sulla valuta, nella lista e nel broker |
> | `front-portfolio risk` | 38/38 | barriera su `broker-refresh` in `risk-analysis` |
> | `front-portfolio privacy-masking` | 18/18 | barriere su `broker-refresh` |
> | `front-utility toolbar-width-sweep` | 24/24 | barriera su `broker-refresh` |
> | `front-portfolio yield-on-cost-real` | 2/2 | barriera su `broker-refresh` |
> | `front-portfolio data-quality-real` | 3/3 | barriera su `broker-refresh` |
>
> - **Cosa resta di Y11**:
>   - `assets/[id]`, dopo FE5c e il 9b di X;
>   - alla chiusura: la riga del CHANGELOG e la documentazione con `docs-writer`, cioè la sezione «Coming back and
>     refreshing», la pagina dei broker e una pagina per sviluppatori su `pageBusy`.
> - **Revisione con il developer**: N55, Y-18 e Y-15.

### Aggiornamento della base: fusione con dev `967ddbda4` (aperta dal coordinatore alle 19:30; HEAD `aec08170f`)

- Il journal con l'E2E dei passi 4 e 4b è committato: `aec08170f`.
- La fusione porta CP-13a (J), C-97a, X-R28, O-20 di X, H-12/21, il lotto 9 di AF e DV.
- **Un conflitto, `routes/(app)/assets/+page.svelte`**: il mio Y11 contro O-20 di X. Con O-20 la pagina non
  sincronizza più da sola dopo una creazione: `AssetModal` sincronizza, e la pagina mostra lo spinner sulla scheda.
  - Import: tenuti entrambi, `pageBusy` e `type AssetCreateSyncResult`.
  - `AssetModal`: `oncreated={handleAssetCreated}` e `onsynced={handleCreatedAssetSynced}` di X, più il mio
    `onupdated` tracciato (`assets-reload`).
  - In `handleAssetCreated` di X il `loadAssets()` è tracciato (`assets-reload`), come nel mio `oncreated` inline.
  - `handleCreatedAssetSynced` resta senza gettone e senza `join`. È il ricaricamento dopo una sincronizzazione che ha
    il proprio indicatore, lo spinner della scheda; per il contratto e per P3 non tiene fermo il pulsante, come
    `handleSyncAsset`.
  - Il coordinatore suggeriva `join` se lo spinner della scheda dovesse tenere fermo il pulsante; per il contratto non
    deve.
  - Ho fatto `git add` solo di quel file; nessun conflitto rimasto.
- **File automerged da entrambi i lati**, rivisti:
  - `brokers-detail.spec.ts`: il `data-selected` di T (righe 392–419) accanto ai miei test Y-12;
  - `financial_math.md`: la sezione del gate accanto alla riga di J su `required_recovery_return`;
  - BACKLOG: le voci da Y-12 a Y-18 intatte.
- **Prove leggere sulla revisione fusa** (`files/scripts/y11m3_light.sh`, dalle 19:33 alle 19:42, carico 35–45):
  - `api sync` non ha cambiato file tracciati;
  - svelte-check 0 errori e 0 avvisi; `theme-roles` pulito;
  - store 93; risk-controller 102; risk-levels 499; asset-unit 880;
  - core 6 830/6 830; component 4 099/4 099;
  - `diff --cached --check` pulito.
- **⚠️ Fuori pista, un gettone mancante del passo 3**: in `AssetMergeModal`, `onmerged` chiama `loadAssets()` senza
  gettone, anche se è un ricaricamento dopo una scrittura dell'utente. La patch del passo 3 non l'aveva considerato.
  Va nel prossimo lotto di Y11, insieme ad `assets/[id]`, e non nella fusione, che deve solo unire i due lati.
- **E2E combinata** (`files/scripts/y11m3_e2e.sh`, slot 1, dalle 19:44, scadenza 20:25): `page-busy`, `asset-list`,
  `asset-modal`, `front-broker detail`, `transactions-table`.
  - **✅ 121/121 alla prima corsa**, dalle 19:43 alle 19:56. La prima spec comprende la ricostruzione del frontend,
    circa 4,5 minuti con il carico a 116.
    - `page-busy` 12/12; `asset-list` 28/28; `asset-modal` 18/18, che copre anche O-20 di X sulla revisione combinata;
    - `front-broker detail` 38/38; `transactions-table` 25/25.
  - Alle 19:56:28 la porta 6189 è libera.
  - Queste note restano fuori dalla fusione, non in stage: vanno nel prossimo checkpoint.
- **Per `assets/[id]`**: la fusione porta lo split della pagina di dettaglio fatto da X, con i componenti in
  `components/assets/detail/` (per esempio `AssetDetailToolbarActions.svelte` e `AssetDetailHeader.svelte`). Prima di
  scrivere la patch chiedo al coordinatore se FE5c e il 9b sono entrambi entrati.
- **19:57**: il coordinatore ha committato la fusione (`ceb182ad4`), e **Y è entrato in dev** con `0c79932a7` (corsa
  130: Y12a, Y-12 e Y11 dal passo 1 al 4b).
  - `assets/[id]`: FE5c e il 9b sono entrati, ma X sta lavorando a C-66 sullo stesso file. Quindi prima Y12b; poi
    `assets/[id]`, con `onmerged`, appena C-66 entra (me lo dice il coordinatore).

### Y12b · P19, i guadagni di recupero dal backend (dalle 19:58, su `ceb182ad4`) — ✅ codice, test e prove leggere 20:12; E2E da fare

> **Note implementazione**.
> - **Ambito di oggi: solo P19**, con CP-13a di J (`0452e592c`) già nella base.
>   - R17, W8, P4, P5 e V11 aspettano il resto di CP-13 di J, e P5 anche CP-7: nessuno di questi campi è nel client
>     generato.
> - **Cosa cambia** (`features/risk/levels/levelHelpers.ts`; patch `files/patches/y12b_levelHelpers.py`, provata a
>   secco su una copia):
>   - `requiredRecovery()` sparisce: la formula `1/(1−L) − 1` ora sta solo nel backend
>     (`financial_math/returns.py::required_recovery_return`);
>   - la riga «worst» di `buildHurtRows` legge `maximum_drawdown_trough_to_peak_ratio` così com'è arriva, solo da
>     `drawdown_summary`. Senza riepilogo, quando la profondità viene dal KPI, il recupero è null: niente ripiego;
>   - una profondità zero non ha niente da recuperare e resta null, come oggi;
>   - `buildCurrentDrawdown` legge `remaining_to_peak_ratio` così com'è;
>   - si corregge il commento su `degrades_result` (righe 137–141): oltre al ripiego per settore ora c'è anche
>     `total_loss_no_recovery`.
> - **L1** (`L1HowMuchItHurts.svelte`) non cambia: con il valore null la riga del recupero non compare, come succede in
>   L1 per ogni sottomisura che manca, e come oggi per una perdita totale. La decisione parla di «—»: se il developer
>   vuole un trattino, basta una riga del template.
> - **Il laboratorio** (`assetSetLevels.ts:190-194`) legge già `remaining_to_peak_ratio` e non mostra un recupero dal
>   punto peggiore: resta com'è.
> - **E2E**: `risk-analysis.spec.ts:1922` controlla solo che `risk-l1-recovery-worst` sia visibile, e nessuna spec ne
>   legge il valore. L'export per l'AI non usa il campo nuovo.
> - **Documentazione**: `developer/frontend/components/features/risk-lab.md:285-287` descrive `requiredRecovery()` con
>   righe sbagliate. La aggiorna `docs-writer` dopo il codice, con le righe definitive.
> - **`test-author`** (dalle 19:59 alle 20:05):
>   - in `levelHelpers.test.ts`, via il blocco `requiredRecovery` (3 test); i due test che usavano il valore calcolato
>     ora hanno i campi nella fixture;
>   - 17 casi nuovi:
>     - il valore del backend letto così com'è, per la riga «worst» e per il drawdown corrente;
>     - la perdita totale con valore null;
>     - il ripiego dal KPI, che non porta recupero;
>     - una profondità del riepilogo col segno sbagliato, quando subentra il KPI;
>     - la profondità zero;
>     - NaN, infinito, una stringa e un valore mancante, che si leggono come null.
>   - **⚠️ Fuori pista**, trovato da `test-author`: la stub di `drawdown_summary` in `risk-analysis.spec.ts` (riga 755)
>     non aveva il campo nuovo. Con il cambio, `risk-l1-recovery-worst` (riga 1922) sarebbe sparito. Ho aggiunto
>     `maximum_drawdown_trough_to_peak_ratio: 0.087 / 0.913` (3 righe).
>   - Una seconda scoperta, sulla durata che mescola le fonti, è fuori da P19 ed era già presente: è nel BACKLOG come
>     Y-19.
> - **Rifinitura della patch**: il recupero si legge solo quando la profondità viene dal riepilogo (`summaryDepth`). Così
>   non può mai finire accanto alla profondità del KPI.
> - **Rosso** (20:05, `risk-levels-unit`): **12 falliti** su 511, cioè esattamente i 12 attesi.
> - **Verde** dopo la patch (20:06): **511/511**. Nel codice non resta nessuna chiamata a `requiredRecovery(`.
> - **Prove leggere** (`files/scripts/y12b_light.sh`, dalle 20:07 alle 20:12, carico 40–46):
>   - Prettier pulito; svelte-check 0 errori e 0 avvisi; `theme-roles` pulito;
>   - risk-levels-unit 511/511; risk-levels-component 273/273;
>   - core 6 830/6 830, compreso il gate delle eccezioni della matematica finanziaria;
>   - `git diff --check` pulito.
> - **`docs-writer`** (dalle 20:07 alle 20:14): `risk-lab.md`, righe 279–301, +19/−11.
>   - **Worst fall**: il recupero lo calcola il backend (`required_recovery_return()`, `returns.py:239`). Si legge così
>     com'è arriva, e solo sulla profondità del riepilogo; non c'è ripiego dal KPI. Con una perdita totale c'è l'avviso,
>     con un collegamento a «The Drawdown Episode» nella pagina dell'architettura del rischio. Con il valore null la
>     riga non compare.
>   - **Current drawdown**: `remaining_to_peak_ratio`.
>   - Aggiornati tutti i numeri di riga del paragrafo, controllati uno per uno.
>   - `check-links` verde (97 validi). Il collegamento nuovo l'ha controllato a mano: il file esiste e l'ancora è
>     esplicita. Nessuna traduzione, perché le pagine per sviluppatori sono solo in inglese.
>   - **Riferimenti scaduti fuori dal paragrafo**, lasciati com'erano e messi nel BACKLOG come **Y-20**:
>
>     | Riga della pagina | La pagina dice | Oggi |
>     |---|---|---|
>     | 302–303 | `l1Helpers.ts:136`, `holdsCut` l.92, `belowCut` l.101 | 138, 94, 103 |
>     | 304–305 | `ReturnHistogram.svelte:51`, `title` l.79 | la regola sta nel commento alla riga 18 e in `barClass()` (40–43); `title` alla 68 |
>     | 306 | `lossMoney()` `L1HowMuchItHurts.svelte:86` | 72 |
>     | 309 | `RiskMetricCard.svelte:107` | 108 |
>     | 310 | `DOC_PATHS` l.117, `TAIL_DOCS` l.127 | 103, 113 |
>     | 119 | `riskAnalysisHelpers.ts:280`, «used at l.340» | 282; usato alle righe 321 e 342 |
> - **E2E da chiedere**: `front-portfolio risk`, circa 5 minuti. Copre la stub aggiornata e la riga del recupero.
- **20:16, checkpoint di Y12b**: il coordinatore ha committato `c3d0a7fa7` (feat) e `f1f2b9390` (journal).
  - E2E `front-portfolio risk`, circa 5 minuti, nel primo slot libero dopo le 20:45, su sua conferma.
  - Vanno nella revisione con il developer: «null: la riga non compare, non "—"».
  - La domanda sul resto di CP-13 (R17, W8, P4, P5 e V11) è passata a J.
  - **Tre file ai colori finché non entrano** (avviso delle 20:15): `features/dashboard/PositionsPanel.svelte`,
    `features/dashboard/ExposureTable.svelte` e `features/brokers/lots/LotCustodyModal.svelte`. Se ne servisse uno,
    prima lo dico al coordinatore. Y12b P19 non li tocca, e il resto di Y12b neppure: R17 è in `KpiSection`, W8 in
    `ExposureTreemap`, P4 in `PerformanceChart`, P5 e V11 nei grafici dei lotti. Y-17, cioè `aria-pressed` su
    `PositionsPanel`, invece li tocca, e aspetta l'ingresso dei colori.

### Y4a · analisi aggiornata (16/10 20:17–20:22, sola lettura, nessun file toccato; HEAD `f1f2b9390`)

> **Note implementazione**. L'ha chiesta il coordinatore (opzione 1). FE4 e FE5a di X **non** sono entrati: oggi non
> esistono né `features/fx` né `features/assets`; sono entrati solo FE5b e FE5c.
> - **Script e dati**: `files/y4a_graph.py` (grafo degli import) e `files/y4a_literals.py` (percorsi fuori dagli
>   import). I risultati sono in `files/logs/y4a_*.log` e `files/y4a_*.json`.
> - **Il lotto, 57 file** (erano circa 55), verso `features/signals/`. La cartella oggi non esiste e non ci sono
>   collisioni di nomi.
>   - 35 da `lib/charts/signals`, appiattiti, con i test in `__tests__`;
>   - 6 dalla radice di `lib/charts`: `signalLabel`, `loadComparisonData`, `chartPageSignals` (nuovo, di X, FE5c, 06:49)
>     e i loro tre test;
>   - 14 da `components/charts` verso `features/signals/components/`: la UI dei segnali, più `ChartSettingsModal` e
>     `MeasurePanel` (D-Y14);
>   - 2 dello store, `signalCatalogStore` e il suo test.
> - **Importatori esterni: 36** (erano 30):
>   - 16 primitive di `components/charts`, cioè l'inversione D-Y15, accettata fino a FE9;
>   - 3 in `features/risk`, 2 in `features/settings` (`AboutTab` e il suo test, con 2 `vi.mock`), 3
>     `chartSettingsStore*`;
>   - **12 di X** (erano 8):
>     - `components/assets/AssetCard` e `AssetDataEditorSection`;
>     - i 4 nuovi di FE5c: `components/assets/detail/assetDetailFxRequirements` e `assetDetailPriceQuery`, con i loro
>       test;
>     - `components/fx/FxCard` e `FxDataEditorSection`;
>     - le pagine `assets`, `assets/[id]` (10 righe di import nel lotto), `fx` e `fx/[pair]`.
> - **Prima di FE4 e FE5a: sì, a tre condizioni.**
>   1. FE4 e FE5a sposteranno gli 8 file di `components/assets` e `components/fx`; le 4 pagine restano dove sono. Se
>      Y4a entra prima, X parte da una base in cui quei file importano già `$lib/features/signals`, e i percorsi nuovi
>      viaggiano con lo spostamento: nessun conflitto. Il rischio c'è solo se esiste già un ramo FE4 o FE5a aperto: in
>      quel caso gli 8 blocchi di import confliggerebbero da entrambi i lati. Il coordinatore deve confermarlo.
>   2. C-66 di X lavora oggi su `assets/[id]/+page.svelte`, che ha 10 righe di import nel lotto. Lo stesso file mi serve
>      per Y11. L'ordine è: C-66, poi Y11 su `assets/[id]`, poi Y4a.
>   3. `chartPageSignals.ts` è di X. Importa solo moduli dei segnali e lo usa solo `assets/[id]`. La mia proposta è che
>      si sposti con il lotto, ma la decisione va presa con X: l'alternativa è `features/assets` con FE5a.
> - **File condivisi**:
>   - **Colori**:
>     - `scripts/test_runner/_frontend_utility.py`, 16 righe (41–43, 84, 202–209 e seguenti);
>     - `frontend/scripts/theme/theme-roles.mjs:81`, l'eccezione di `ChartSettingsModal`, che era alla riga 72 (D-Y14);
>     - `frontend/scripts/designer-lab/scan-colors.mjs:193`: `CHART_PATH_RE` deve imparare `features/signals`,
>       altrimenti la UI il cui nome non comincia con «chart» smette di contare come grafico;
>     - il baseline non ha record per i file spostati, quindi `--check` non cambia.
>   - **X**: `scripts/test_runner/_frontend_asset.py` (righe 23–25 e 29), più i 12 importatori.
>   - **Export per l'AI**: `scripts/test_runner/_frontend_ai_export.py` (righe 24–31).
>   - **Miei o comuni**:
>     - il gate `financialMathExceptions` (6 percorsi) e `htmlSink.gate.test.ts:71`;
>     - `scripts/coverage_js.py:187` e `:238`;
>     - l'`applyTo` di `.github/instructions/frontend-signals.instructions.md:2`, e
>       `frontend.instructions.md:197`;
>     - la skill `devpy-i18n/SKILL.md:136`;
>     - i `vi.mock` di `AboutTab.test` (righe 86 e 91) e l'import dinamico di `PriceChartFull.tooltipEscape.test`
>       (righe 166 e 173);
>     - 4 pagine MkDocs: `signal_plugin_guide.md:392`, `financial_math.md:308`, `charts.md:541` e
>       `coverage-model.md:342`;
>     - **21 pagine della devWiki** (64 righe, nelle tabelle dei file sorgente), da verificare con
>       `check_source_paths.py`;
>     - il journal storico non si tocca.
> - **Costo stimato: 3–3,5 ore**, di cui circa un'ora sui file condivisi con tre proprietari.
>   - Spostamento e riscrittura degli import con uno script: quattro famiglie di percorsi, più gli import relativi
>     interni al lotto. Circa 45 minuti.
>   - I percorsi fuori dagli import: circa 30 minuti.
>   - Documentazione MkDocs (`docs-writer`) e devWiki (script, più `check_source_paths.py`): circa 45 minuti.
>   - Prove leggere: svelte-check, `theme-roles`, asset-unit, core con i gate, component e i test dell'export per
>     l'AI. Circa 20 minuti.
>   - Uno slot E2E di circa 45 minuti: dettaglio e lista degli asset, dettaglio e lista dei cambi, segnali, export per
>     l'AI, la scheda About.
>   - **Rischio medio-basso**: il lavoro è meccanico. Il rischio vero sono i rami in volo sui 12 file di X e sui 3 file
>     del runner. Si gestisce con un congelamento di circa 2 ore su quei file.
> - **Proposta**: non nella 1.3, a meno che il developer non lo voglia. Se lo vuole, una finestra notturna dopo C-66 e
>   dopo il mio `assets/[id]`, con quel congelamento.
- **20:21, coordinatore**: Y4a resta **fermo**. Porta al developer la mia proposta: «non nella 1.3, oppure in una
  finestra notturna dopo C-66 e `assets/[id]`».
  - X non ha rami FE4 o FE5a aperti, quindi la prima condizione è soddisfatta.
  - Alle 20:45 `front-portfolio risk` per Y12b, poi l'ingresso in dev.

### Y12b · E2E `front-portfolio risk` (dalle 20:45 alle 20:51; HEAD `f1f2b9390`) — 37/38, un rosso non dovuto a Y12b

> **Note implementazione** (script `files/scripts/y12b_e2e.sh`, avviato da solo alle 20:45 con il controllo del
> carico; log in `files/logs/y12b_e2e_risk.log`).
> - **37/38** in 2,5 minuti, compresa la ricostruzione del frontend. La porta 6189 è libera.
> - **⚠️ Fuori pista, il rosso alla riga 3638** di `risk-analysis.spec.ts`: «L3's table … the return's title is the short
>   name, and resting on it opens the full name first».
>   - Dopo `title.hover()` (riga 3648), `getByTestId('tooltip-content')` non viene trovato entro i 3 s di attesa
>     predefiniti (riga 3650).
>   - **Prove** (copiate in `files/logs/`: `y12b_l3title_error-context.md` e `y12b_l3title_failed.png`):
>     - nell'istantanea ARIA presa al fallimento la tabella di L3 è completa, con le righe e i dati, e il tooltip non
>       c'è;
>     - nello screenshot preso dopo il timeout il tooltip invece è **aperto**, con il testo giusto («Average annual
>       return …»);
>     - `Tooltip.svelte` non è cambiato dall'ultima corsa verde (`1c3f6a432`), e il suo `data-testid` è sempre alla
>       riga 433.
>   - **Di nuovo da solo, 3 volte su 3 verde** (dalle 20:53 alle 20:59, da 9 a 11 s ciascuna, con il filtro
>     «title is the short name»).
>   - **Triage** (skill `test-triage`):
>     - §1, la forma: no;
>     - §2, l'orologio: sì. Il test passa il mouse una volta sola appena il titolo mostra il testo giusto, e concede 3 s.
>       Con due worker la tabella sistema ancora le larghezze dei titoli dopo il passaggio, oppure il thread principale
>       ritarda il timer di apertura del tooltip: il passaggio va perso, o arriva tardi;
>     - §3, lo stato condiviso: no, perché gli stub sono della pagina;
>     - Y12b tocca solo L1, quindi non c'entra.
>   - **Verdetto: un'assunzione del test.** Lo stesso schema c'è anche alla riga 3694.
>   - **Correzione** (`test-author`, dalle 21:00): un aiuto che ripassa il mouse finché l'aiuto si apre, con `toPass` e
>     un limite di circa 10–15 s, senza attese fisse. Si usa nei due punti.
>   - Ho chiesto al coordinatore: una nuova corsa completa di `risk` dopo la correzione, oppure l'ingresso di Y12b
>     subito, con la correzione come Y-21.
- **21:01**: il coordinatore sceglie di correggere e rifare la corsa, così Y12b entra con la spec corretta e dev resta
  verde.
- **Correzione di `test-author`** (dalle 21:00 alle 21:10, `risk-analysis.spec.ts`, +42/−7):
  - un aiuto nuovo, `hoverUntilHelpOpens(page, trigger, why)`: `expect(async () => {…}).toPass({timeout: 10_000})`;
  - a ogni tentativo il puntatore va in `(0, 0)`, poi passa sul trigger, e si aspetta `tooltip-content` per 2 s, cioè
    quattro volte il ritardo di 500 ms del Tooltip. Il tooltip si arma con `mouseenter`, quindi senza spostarsi prima
    il passaggio non lo riarmerebbe;
  - l'aiuto si usa ai due punti, righe 3678 e 3725;
  - Prettier pulito; svelte-check 0 errori e 0 avvisi alle 21:15, sotto un picco di carico a 86.
- **Nuova corsa completa** (slot 3, dalle 21:15 alle 21:18, carico 72–83; log `files/logs/y12b_e2e_risk_rerun.log`):
  **37/38**.
  - Il test di L3 corretto è verde.
  - **⚠️ Fuori pista, un rosso diverso alla riga 2812**: L4, D377, «opens no tool on a first visit…», alla riga 2828.
    - È un `expect.poll(offered).toEqual([shock, simulation])`, con il limite predefinito di 3 s.
    - Il messaggio è «Timeout 3000ms exceeded while waiting **on the predicate**», senza nessun valore ricevuto:
      `evaluateAll` non è tornata entro 3 s.
    - Prove in `files/logs/y12b_l4_error-context.md` e `y12b_l4_failed.png`: alla fine il DOM è giusto (solo shock e
      simulazione da aggiungere, il replay aperto, una sola istanza di L4).
    - In `L4WhatIf.svelte` `addable` e `shown` derivano in modo sincrono da `openTools`, senza transizioni.
    - Lo stesso test era verde alle 20:45, a carico 35.
    - **Verdetto: lentezza sotto carico.** Subito dopo l'apertura del replay storico il thread principale resta
      occupato per più di 3 s; non è un difetto di Y12b. Al coordinatore ho proposto una terza corsa sotto carico 50,
      oppure l'ingresso subito, con Y-21.
- **21:19, coordinatore**: il W6-d di DV è entrato (`3805bf2ca`), e `PositionsPanel.svelte` ed `ExposureTable.svelte`
  sono di nuovo liberi.
  - DV ha chiuso la mia **Y-17**: `aria-pressed` sui 4 pulsanti Holdings/Performance e Table/Map di `PositionsPanel`.
    È segnata ✅ nel BACKLOG con `3805bf2ca`, e va nel prossimo checkpoint.
  - `3805bf2ca` non è ancora nella mia base: lo porterà il prossimo aggiornamento.
  - Il test N55 sulla vista Performance del broker legge ancora `contribution-table`. Potrà leggere `aria-pressed`
    dopo l'aggiornamento della base, ma non serve.
- **21:20, coordinatore**: opzione 2. Y12b è entrato con la correzione: `8acf41fdf` (test) e `684560cd3` (journal, che
  contiene solo il piano). Y-21 va nel BACKLOG, scritta alle 21:21 e da portare nel prossimo checkpoint.
  - Prossimo: `assets/[id]` dopo il lotto A di Z; nel frattempo Y-14, oppure un'altra voce lontana dalle pagine degli
    asset.

### Y-14 · «Aggiorna» della lista dei broker ricalcola anche le schede (dalle 21:22, su `684560cd3`) — ✅ rosso e verde 21:43, prove leggere 22:05

> **Note implementazione**.
> - **Decisione** (coordinatore, 21:2x): il rimedio è «forzare», come nella Dashboard e nella pagina del broker.
> - **Vincolo**: il lotto B di Z ha aperto `page-busy.spec.ts` fino alle 22:10 circa, quindi il rosso va in
>   `e2e/brokers/brokers.spec.ts` (azione `front-broker list`).
>   - `test-author` era partito su `page-busy.spec.ts`: l'ho reindirizzato, con l'ordine di riportare quel file a
>     HEAD.
> - **Patch** (`files/patches/y14_brokers_refresh.py`, provata a secco su una copia):
>   - `loadBrokers(force = false)` passa `force` a `fetchReport` (riga 177);
>   - il clic su `brokers-refresh` va a un nuovo `handleRefresh()`, che fa `requestPortfolioRefresh()` e poi
>     `pageBusy.track('brokers-refresh', () => loadBrokers(true))`;
>   - il primo caricamento, la valuta e i ricaricamenti dopo una modifica restano senza `force`;
>   - **⚠️ Fuori pista, il pulsante «riprova» dello stato d'errore** (riga 404). Passava `loadBrokers` direttamente
>     a `on:click`, quindi con il parametro nuovo l'evento del clic sarebbe finito in `force`. Ora è una chiamata
>     esplicita, tracciata (`brokers-retry`) come ogni ricaricamento chiesto dall'utente: nel passo 4 mi era sfuggito.
> - La pagina non ascolta il bus del portafoglio, quindi `requestPortfolioRefresh()` qui non provoca un secondo
>   caricamento: segna come scadute le cache delle altre viste.
> - **Il rosso di `test-author`** (dalle 21:22 alle 21:37, `e2e/brokers/brokers.spec.ts`, +160/−2). `page-busy.spec.ts`
>   e `_frontend_portfolio.py` non li ha mai toccati.
>   - Titolo: «Refresh asks the report of the cards again even when its cache is fresh, and holds its button until it
>     is back (Y-14)», in un `describe` suo, con un limite di 90 s.
>   - **Cosa fa**:
>     1. la lista si carica da zero e si assesta;
>     2. come precondizione, il primo caricamento ha chiesto il report delle schede (`include_breakdown: true`) e ha
>        avuto risposta;
>     3. trattiene ogni report successivo e fa clic su `brokers-refresh`;
>     4. attende fino a 30 s un report trattenuto. Il suo corpo, tolti i `broker_ids`, deve essere uguale a quello in
>        cache, e i `broker_ids` devono essere quelli con un ruolo nella risposta stessa di «Aggiorna»;
>     5. intanto il pulsante deve essere occupato; dopo il rilascio torna libero, e il report ha risposto.
>   - **Perché oggi è rosso**: con `force=false` la cache ancora fresca risponde, e nessun report parte.
>   - **Limite**: con tutto `front-broker all` altre spec cambiano i broker di TEST_USER. Allora la cache può mancare per
>     conto suo, e il test passerebbe senza dimostrare il `force`, anche se non può fallire per questo. Quindi il rosso
>     va provato con la sola azione `front-broker list`.
> - Al coordinatore ho chiesto uno slot di circa 12 minuti: il rosso, la patch con le prove leggere, poi il verde.
> - **Rosso, patch e verde** (slot 1, dalle 21:38 alle 21:43, carico 87–98; script `files/scripts/y14_red_green.sh`):
>   - **rosso**, `front-broker list` sul codice di oggi: 1 fallito su 10, cioè solo il test Y-14, alla riga 244, perché
>     entro 30 s non è partito nessun report;
>   - la patch applicata;
>   - **verde**, `front-broker list` dopo la ricostruzione: **10/10**.
> - **⚠️ Fuori pista, ordini incrociati**: il messaggio del coordinatore «solo il rosso, il verde dopo», scritto con il
>   carico a 142, mi è arrivato quando lo script aveva già fatto anche il verde, secondo il via dello slot «rosso,
>   patch, verde». Gliel'ho detto subito: lo slot si è liberato alle 21:43:37 e il verde non va ripetuto.
> - **Prettier**: dopo la patch la pagina non era formattata. `--write` ha rimesso su una riga il pulsante «Aggiorna»,
>   che con `on:click={handleRefresh}` è più corto. È solo formattazione: il verde vale lo stesso.
> - **Prove leggere** (`files/scripts/y14_light.sh`, dalle 21:52 alle 22:05; ognuna è partita solo con il carico sotto 50):
>   - Prettier pulito;
>   - svelte-check 0 errori e 0 avvisi; `theme-roles` pulito;
>   - core 6 830/6 830;
>   - `git diff --check` pulito; la porta 6189 è libera.
> - **BACKLOG**: Y-14 ✅ nel checkpoint di Y-14. Nello stesso checkpoint vanno anche Y-17 ✅ (`3805bf2ca`), Y-21 e la nota
>   sul W6-d.
- **22:06, Y-14 entrato** (corsa 144, con una riga 🐛 nel CHANGELOG): `daa2001ea` (fix) e `7c36f2129` (journal).
  `assets/[id]` aspetta il lotto A di Z.

### MF-P · contratti dei campi per il resto di Y12b (22:06–22:12, sola lettura)

> **Note implementazione**.
> - Il coordinatore (22:06): R17, W8 e V11 arrivano con MF-P (ondata 3 di MF); P4 dopo MF-A (ondata 2, che parte
>   ora); P5 dopo MF-E, che aspetta CP-7b di J. I contratti e le date li concordo con MF direttamente.
> - Fonti:
>   - il piano MF in dev, letto con `git show dev_release2:…` e copiato in `files/mf_plan_dev.md`: MF-P è alla riga
>     328, D-MF6 alla 381;
>   - le righe di oggi del frontend.
> - **Mandato a MF** (session `dfb94070…`), voce per voce: cosa calcola oggi il frontend e la mia proposta.
>   - **R17**: `pnl_change_1d`, `…_vs_total_pnl_percent`, `…_vs_nav_percent` e `timing_effect_percent` in
>     `PortfolioSummary`. Il giorno prima è il punto precedente della serie, con il segno della variazione e null su
>     base 0.
>   - **W8**: un valore di G/L % per ogni nodo broker e (broker, tipo) della treemap.
>   - **P4**: `net_percent_of_start` negli item di `positions_contribution`, dopo MF-A.
>   - **V11**: `opening_value` negli eventi BUY.
>   - **P5**: con D-MF6(b) il piè della tabella somma le righe visibili, quindi è un aggregato interattivo da
>     dichiarare. Un campo serve solo per un totale fisso di tutti i lotti. Anche il ribasamento in % di
>     `lotWacPriceChartHelpers.ts:142` è una scala da dichiarare.
>   - Ho chiesto le date.

### Y-18 · indicatore proprio per le candele (analisi per le domande del developer, 22:12)

> **Note implementazione** (sola lettura).
> - **Oggi**:
>   - `GrowthChart` ha uno scheletro solo per la storia: `{#if loading}` disegna
>     `absolute inset-0 z-10 bg-lf-panel rounded animate-pulse` e nasconde il contenitore del grafico (righe
>     1467–1474);
>   - nella vista Candele, finché `pnlCandles` è null, il grafico mostra gli assi senza candele, e nessun indicatore
>     lo segnala;
>   - entrambe le pagine hanno già `pnlCandlesLoading` (Dashboard alla riga 100, broker alla 92), ma non lo passano al
>     grafico;
>   - dopo N55, con un passaggio diretto alle Candele a pagina ferma, il pulsante della pagina non gira più.
> - **Proposta A (consigliata)**:
>   - una prop `candlesLoading?: boolean`, passata dalle due pagine (`{pnlCandlesLoading}`);
>   - con vista P&L → Candele, `candlesLoading` vero e `pnlCandles == null`, lo stesso scheletro della storia
>     (`bg-lf-panel animate-pulse`): nessun colore nuovo;
>   - `aria-busy` sul contenitore (riga 1377) e un `data-testid="growth-candles-loading"`;
>   - il testo per i lettori di schermo è `common.loading`, una chiave che esiste già.
>   - Costo: circa 1–1,5 ore. Un test Vitest in `GrowthChart.test.ts` e un controllo E2E nel test N55 della Dashboard,
>     mentre la richiesta delle candele è trattenuta: `page-busy.spec.ts` si può toccare dopo l'ingresso di Z.
>   - `GrowthChart` è nell'area DV: prima lo annuncio al coordinatore.
> - **Proposta B**: un piccolo `LoadingSpinner` accanto al pulsante «Candele». È meno visibile, e il grafico vuoto
>   resta.
> - **Domanda collegata (P3)**: durante un ricaricamento di sfondo, `applyReport` e `applyOverview` azzerano
>   `pnlCandles`, quindi oggi le candele spariscono fino alla nuova richiesta. Con A al loro posto comparirebbe lo
>   scheletro. Invece la documentazione utente dice che durante un ricalcolo di sfondo «le cifre restano». In
>   alternativa si possono tenere le candele vecchie finché arrivano le nuove, ma questo tocca il ricaricamento di Z-13
>   e le due pagine: è una decisione a parte.
- **22:12, la risposta di MF sui contratti di MF-P**:
  - **Unità**: frazione ovunque (0.05 = 5 %), come oggi `twrr_percent`, `gain_loss_percent` e `period_pnl_percent`;
    SafeDecimal come stringa; null si legge «—».
  - **R17**, in `PortfolioSummary`: `pnl_change_1d: Currency|null`, `pnl_change_1d_vs_total_pnl_percent`,
    `pnl_change_1d_vs_nav_percent` e `timing_effect_percent`.
    - «Il giorno prima» è **D−1 di calendario** (`state_as_of(D−1)`), non il punto precedente della serie: se il
      report campiona, oggi il frontend confronta due punti lontani.
    - Le percentuali sono Δ/|base|; null con base 0 o senza un D−1.
    - Il timing è null se manca l'MWRR, che dopo D-MF5/N54 può mancare.
  - **W8**: `summary.holding_groups: list[{broker_id, asset_type: str|null, gain_loss: Currency|null,
    gain_loss_percent: str|null}]`, dove `asset_type` null è il livello del broker.
    - Si contano solo i titoli con valore e G/L entrambi noti.
    - Oggi un titolo con G/L nullo mette il suo valore nella base come se fosse costo: è un 🐛 per il CHANGELOG.
  - **P4**: nessun campo nuovo. Si usa `period_pnl_percent` (= `period_pnl/|start_value|`) così com'è; con MF-A i
    valori migliorano.
  - **V11**: `opening_value: Currency|null` sui BUY, nella valuta di `unit_price`. Arriva con MF-E, dopo CP-7b di J.
  - **P5**:
    - il piè della tabella sulle righe visibili e il ribasamento di `lotWacPriceChartHelpers.ts:142` si dichiarano nel
      codice;
    - il totale fisso c'è già (`LotSummarySchema`).
  - **Date**: R17 e W8 il 17/10 mattina; P4 subito; V11 ed eventuali totali di P5 verso il 18/10. MF mi manda lo schema
    dopo `api sync`, per i rossi.
  - **La sua domanda sui periodi fissi dell'asset (1G, 1S…)**: non sono in Y12b. Stanno in
    `lib/utils/assetPriceDerived.ts:193-196` (`computePeriodDelta`, lista degli asset) e in
    `routes/(app)/fx/+page.svelte:236-240`, area di X. Gliel'ho risposto.

### Y-19 · la durata della caduta peggiore segue la fonte della profondità (via del coordinatore 22:11, su `7c36f2129`) — ✅ 22:31

> **Note implementazione**.
> - **Analisi**: nello schema le due durate sono `int` obbligatori e ≥ 0, e il riepilogo controlla la coerenza fra
>   durata e stato del recupero.
>   - Con dati validi la profondità e la durata vengono dalla stessa fonte.
>   - Si mescolano solo quando c'è il riepilogo ma la sua profondità ha il segno contrario, che `lossMagnitude` legge
>     come assente.
> - **Correzione**, una riga (`files/patches/y19_levelHelpers.py`):
>   `durationDays: summaryDepth !== null ? finite(summary…) : finite(kpi…)`. Lo stesso schema vale per il recupero da
>   Y12b. Non sposta i numeri di riga citati da `risk-lab.md`.
> - **Rosso**: `test-author` scrive un caso con la profondità del riepilogo di segno contrario e un caso di guardia in
>   cui vince un riepilogo valido.
> - **Ciclo**: `files/scripts/y19_cycle.sh`, cioè rosso, patch, verde, Prettier, svelte-check e core, ogni passo solo
>   con il carico sotto 50. Niente E2E.
> - **`test-author`** (dalle 22:13 alle 22:15, `levelHelpers.test.ts`), due casi subito dopo quello Y12b del segno
>   contrario:
>   - il rosso: la profondità del riepilogo ha il segno sbagliato (`0.3`, durata 99), e il KPI ha `−0.4` con durata 30.
>     Ci si aspettano una perdita di 0.4 e una durata di 30;
>   - la guardia: un riepilogo valido (`−0.25`, durata 12) accanto a un KPI più profondo. Profondità e durata del
>     riepilogo vincono insieme, cioè 0.25 e 12. Copre il verso opposto del test che già c'era, dove il KPI era meno
>     profondo.
> - **Ciclo** (`files/scripts/y19_cycle.sh`, dalle 22:19 alle 22:31, ogni passo solo con il carico sotto 50):
>   - **rosso**: risk-levels-unit 1 fallito su 513, cioè proprio il caso atteso («expected 99 to be 30»);
>   - la patch di una riga;
>   - **verde**: 513/513;
>   - Prettier pulito; svelte-check 0 errori e 0 avvisi; core 6 830/6 830; `git diff --check` pulito; la porta 6189 è
>     libera.
> - Nel BACKLOG Y-19 è ✅. Nessuna E2E, perché le stub sono valide e il comportamento resta quello.
- **22:2x, revisione del lotto B di Z** (sola lettura, con `git show 1b46178bd`), sui due casi «reload in background»
  di `page-busy.spec.ts`:
  - durante la richiesta trattenuta la radice della Dashboard deve essere `data-busy="false"` (Z-18);
  - l'arrivo del ricaricamento si legge con `countReports` e `landedAllBut`, gli strumenti della spec;
  - `holds` esiste nel test.
  - Ho risposto **OK**, senza modifiche. Il lotto B di Z è entrato. `assets/[id]` diventa mio quando entra il lotto A.
- **22:32**: Y-19 committato (`9fd2dcdc0` fix e `54cce7263` journal) ed entrato in dev. Il via per Y-20 è arrivato
  mentre Z lavora al lotto A.

### Y-20 · `risk-lab.md`: numeri di riga scaduti (dalle 22:33, su `54cce7263`) — ✅ 22:47

> **Note implementazione**.
> - **`docs-writer`** (dalle 22:33) aggiorna i sei riferimenti della tabella in «Y12b» (righe 119 e 302–310 della
>   pagina), ognuno ricontrollato sul codice di oggi.
>   - Controlla anche gli altri riferimenti `file:riga` della sezione «How Much Can It Hurt?» e del punto «Bad month».
>   - Il resto della pagina non lo tocca: segnala soltanto.
>   - Verifica con `dev.py mkdocs check-links`.
> - **Primo giro di `docs-writer`** (dalle 22:33 alle 22:40): 9 riferimenti aggiornati, ognuno controllato sul codice,
>   e `check-links` verde (97 validi).
>   - **Requests**: `riskAnalysisHelpers.ts:334` → 336 e l.368-371 → 370-373; `:280` → 282, con l'uso alle righe
>     321 e 342 invece della 340.
>   - **Istogramma**: `l1Helpers.ts:136` → 138, e `holdsCut`/`belowCut` alle righe 94 e 103 invece di 92 e 101. Per
>     la regola del bin a cavallo, al posto di `ReturnHistogram.svelte:51` ora ci sono il commento alla riga 18 e
>     `barClass()` alle righe 40–43; `title` passa da 79 a 68.
>   - **Cifre in denaro**: `lossMoney()` da 86 a 72.
>   - **Etichette**: `RiskMetricCard.svelte` da 107 a 108; `DOC_PATHS`/`TAIL_DOCS` da 117/127 a 103/113.
> - **Secondo giro**, le quattro osservazioni del primo giro, applicate:
>   - **Worst fall**: ora la pagina dice che la durata segue la fonte della profondità (Y-19, riga 405).
>   - **Money**: si aggiunge Broker Detail, che usa il patrimonio netto di quel broker (riga 718). La tabella degli host
>     lo diceva già.
>   - **Istogramma**: «neither», che era ambiguo, diventa: il bin a cavallo è quello ambra `holdsCut` e non conta mai
>     come coda (`belowCut` falso, `l1Helpers.ts:175-176`).
>   - **UnderwaterChart**: il riferimento va alla didascalia, righe 65–70 con il valore alla 67, invece che al suo
>     link alla riga 69.
> - **⚠️ Fuori pista**: con il primo giro la pagina citava due righe diverse per lo stesso fatto (718 nel punto, 686
>   nella tabella degli host). Ho chiesto a `docs-writer` di aggiornare anche gli 11 numeri della tabella degli host e
>   del punto «No owned broker», già verificati. Non si va oltre.
> - **Terzo giro** (fino alle 22:47): gli 11 numeri della tabella degli host e del punto «No owned broker».
>   - Ciascuno è stato confrontato con la stessa riga di `eee56b42a`, quando la pagina fu scritta: punta allo stesso
>     codice, solo spostato (di 1, 31 o 32 righe).
>   - Ora la pagina dà una riga sola per ogni fatto (`:718` sia nel punto sia nella tabella).
>   - `check-links` verde, 97 link validi; `brokerStore.ts:262` era già giusto.
> - **In tutto**: 20 riferimenti aggiornati e 4 precisazioni di testo, solo in `risk-lab.md`. Pagina solo in inglese,
>   quindi niente traduzioni né marcatura. Y-20 ✅ nel BACKLOG.
- **22:45, Y-20 committato** ed entrato in dev.

### Notte del 16→17/10 · regole e coda

- **Regola del coordinatore** (22:45): il developer dorme fino al mattino. Una domanda che solo lui può sciogliere la
  scrivo qui, la mando al coordinatore e passo alla voce successiva; se il lavoro finisce, chiedo al coordinatore.
  - Già nella sua lista del mattino: Y4a, Y-15, Y-18 e il null di L1 («la riga non compare» contro «—»).
- **Domande per il developer**, aggiunte alle 22:50:
  - **Y-10**: mostrare sul telefono la maniglia di ridimensionamento (`@media (hover: none)`) cambia gli scatti mobile;
  - **Y-3**: aggiungere `\bt\(` alla forma del gate della privacy, dopo averne misurato il rumore.
- **Situazione del piano**: tutto il mandato è entrato (Y1–Y10, Y-11, Y12a, Y-12, Y-14, Y-17, Y-19, Y-20), tranne:
  - `assets/[id]`, la chiusura di Y11, dopo il lotto A di Z;
  - il resto di Y12b, che aspetta MF-P (R17 e W8 il 17 mattina);
  - Y4a, fermo per il developer;
  - Y13 (FE9–FE11), che è l'ultimo.
  - Y-16 non si può fare stanotte: tocca `GrowthChart` e la Dashboard.
- **Proposta al coordinatore** (22:49), in quest'ordine:
  1. Y-21, cioè la scadenza dei `poll` del test L4, con il commento di Y-5;
  2. la pagina per sviluppatori su `pageBusy`;
  3. l'analisi di Y13.

### Y-21 e Y-5 · scadenze del test L4 e commento di `headerTooltip` (via del coordinatore 22:50, su `bf1b802d7`)

> **Note implementazione** (in corso).
> - **Y-21** (`test-author`, dalle 22:50 alle 22:55, `risk-analysis.spec.ts`, +9/−4):
>   - una costante `L4_OFFER_DEADLINE_MS = 10_000`, una scadenza e non un'attesa, nei quattro
>     `expect.poll(offered, …)` del test D377 (righe 2827, 2833, 2846 e 2864);
>   - `test.setTimeout(90_000)` come prima istruzione del test, cioè un budget che lascia arrivare prima le sue scadenze.
>     Prima nulla gli dava più dei 30 s della configurazione.
>   - `test-author` fa notare che la somma di tutte le scadenze del test arriva a circa 277 s. I 90 s coprono una corsa
>     lenta sotto carico, non quella in cui ogni passo arriva al limite.
> - **Y-5** (io): il commento di `headerTooltip` in `table/types.ts:291` ora dice che il tooltip sta sull'etichetta e
>   che l'icona compare solo con `headerTooltipUrl`.
> - **Prove leggere**: Prettier e `git diff --check` puliti; svelte-check 0 errori e 0 avvisi (22:55–22:59).
> - **Slot**: il coordinatore ha dato lo slot 1 verso le 23:25, dopo W (FE8b) e X, con sua conferma.
> - **Voce 2 avviata intanto** (22:58): `docs-writer` scrive la sezione su `pageBusy` in
>   `developer/frontend/state/app-state.md`.
>   - È una pagina che esiste già, quindi la navigazione condivisa non si tocca.
>   - Al più aggiunge una riga di collegamento in `domain-state.md`.
> - **E2E**: `files/scripts/y21_e2e.sh` (`front-portfolio risk`, con la ricostruzione del frontend), nello slot che ho
>   chiesto al coordinatore.
> - **Voce 2 ✅** (`docs-writer`, dalle 22:58 alle 23:08):
>   - in `developer/frontend/state/app-state.md` (+145) una riga nella tabella degli store e la sezione
>     `## ⏳ Page busy: the Refresh button {: #page-busy }`. Contiene:
>     - l'API, con le righe di `pageBusy.svelte.ts`;
>     - dove vanno `track` e `join`, e dove mai, con i siti della Dashboard, del broker, di `LotsAnalysisPanel` e
>       di `riskPanelController`;
>     - l'ambito della pagina, il reset e il timeout;
>     - il contratto del pulsante, con i 10 test id e la differenza dal `data-busy` della radice;
>     - le prove: il Vitest, e nell'E2E la richiesta trattenuta, il registratore, il controllo e i casi di N55;
>   - in `domain-state.md` (+1) una riga che rimanda a `#page-busy` dalla sezione sul bus;
>   - `check-links` verde (97); la build strict verde, 106 s, senza WARNING.
> - **⚠️ Fuori pista**: in `domain-state.md` («How a page uses the cache», passo 5) una frase è falsa da Y11. Dice che il
>   ricaricamento dopo l'aggiornamento dei prezzi «lascia stare `syncLoading`, lo spinner del pulsante Refresh»; da Y11
>   il pulsante gira su `pageBusy.busy`. Il file l'ha toccato per ultimo Z: ho chiesto al coordinatore se la correggo io
>   nello stesso checkpoint.
> - **La frase di `domain-state.md`**: il coordinatore ha detto «correggila tu». Ma il lotto B di Z (`1b46178bd`, già in
>   dev) aveva riscritto proprio quel passo 5 (riga 121 in dev): «Nor is it tracked by `pageBusy` … so the button
>   neither waits nor spins for it», più Z-18.
>   - La mia copia è quella precedente, quindi non la tocco: avrei solo un conflitto. Il testo giusto arriva con il
>     prossimo aggiornamento della base.
>   - La riga aggiunta da `docs-writer` è nella sezione del bus, lontana dal passo 5, e dice la stessa cosa.
>   - L'ho detto al coordinatore.

### Y13 · FE9–FE11, analisi (16/10 23:10–23:20, sola lettura; HEAD `bf1b802d7`)

> **Note implementazione**. Script `files/y13_inventory.py`: per ogni file di `lib/utils` e `lib/stores`, chi lo importa
> e da quali domini; le inversioni di livello; il censimento dei suffissi. Log in `files/logs/y13_inventory.log`,
> dati in `files/y13_inventory.json`.
> - **FE9 · `utils/` generici e inversioni**:
>   - `lib/utils` ha 18 file in radice e 11 sottocartelle (brim 4, broker 5, core 20, currency 3, files 5, layout 4,
>     privacy 1, security 1, sync 3, transactions 27, url 3). Quasi tutto è condiviso fra più domini.
>   - **Usati da un solo dominio**, da portare nella loro feature:
>     - `utils/urlFilters.ts`, usato solo dalla pagina dei file. Il §3 lo dava a FE3, ma Y6 l'ha lasciato;
>     - `utils/files/pdfPreviewState.ts` e `pdfViewerAssets.ts`, usati solo da `features/files`. Y6 aveva tenuto
>       fermo tutto `utils/files/` come condiviso (D-Y5), ma condivisi davvero sono solo `upload` e `imageCrop`;
>     - `utils/core/positionKey.ts`, usato solo dalla dashboard;
>     - `utils/transactions/commitRefusal.ts` e `utils/url/queryParams.ts`, usati solo dalla pagina delle transazioni:
>       sono di W.
>   - **Inversioni utils/stores → componenti** (7):
>     - `chartSettingsStore` → `components/charts/calendarReturnWindow.ts`;
>     - `txStore`, `importCompare` e `txFormFields` → `components/transactions/types.ts`;
>     - `assetTypes` → `components/ui/select/treeSelect.ts`;
>     - `urlFilters` → `components/table/types.ts`;
>     - `chartUtils` → `components/charts/LineChart.svelte`, che è un `.svelte` importato da un modulo `utils`.
>     - Rimedio: i tipi comuni vanno in moduli neutri, e la dipendenza di `chartUtils` va sciolta.
>   - **Componenti generici → feature** (42 archi):
>     - per feature: onboarding (`guideAnchors`) 20, ai-export 5, live-updates 4, plugin-settings 3, update-check 3,
>       brokers 2, files 2, changelog 1, auth 1, instance 1;
>     - quasi tutti partono da `components/assets`, `fx` o `transactions`: diventano import fra feature quando FE4, FE5
>       e FE8 li spostano. Quindi li risolvono quei lotti, non FE9;
>     - restano tre casi veri. `components/layout` (`Header`, `Sidebar`, `ChangelogModal`) importa onboarding,
>       changelog e update-check; è il guscio dell'app, accettabile. `components/ui/input/PasswordStrength` importa
>       auth e instance: è UI generica, da sistemare passando le regole come props oppure spostandola in
>       `features/auth`. Poi c'è `guideAnchors`, che è infrastruttura usata ovunque.
>   - **Import fra feature**: 23 coppie (settings→molte, auth↔email, onboarding→settings/support/update-check,
>     price-refresh→instance/live-updates, risk→dashboard, tools→onboarding, brokers→files/onboarding,
>     instance→backup). D-P4 era rinviato a FE9: si importa dal file che definisce, senza barili, come dice D-Y5.
>   - In FE9 si chiude anche **Y-7**: le primitive dei grafici importano dai segnali (D-Y15).
> - **FE10 · `stores/` solo globali**: oggi nessuno store è usato da un dominio solo (radice 6, app 15, core 3,
>   files 1, fx 1, portfolio 2, reference 6, transactions 2).
>   - `stores/core` (`EditBuffer`, `entityStore`) è infrastruttura usata dentro `lib/stores`.
>   - `stores/transactions` e `stores/fx` possono seguire FE8 e FE4, se dopo quegli spostamenti diventano di un solo
>     dominio.
>   - Quindi FE10 si fa rifacendo l'inventario dopo FE4, FE5 e FE8: circa un'ora.
> - **FE11 · suffissi**: Modal 44, Dialog 10, Panel 23, Section 19, Popover 1. Serve prima una convenzione, che decide
>   il developer. I rinomi toccano tutte le aree, i test, la documentazione e la devWiki; i test id non cambiano.
> - **Dipendenze e tempi**:
>   - FE9 dopo FE2–FE8. Oggi mancano Y4a, fermo, FE4 e FE5a di X, e FE8 di W, congelato.
>   - FE10 insieme o dopo le feature; FE11 per ultimo, ed è facoltativo.
>   - Realisticamente dopo il tag della 1.3.
> - **Conflitti**: larghi, perché toccano gli importatori di tutte le aree (X, W, J, colori). Serve una finestra
>   notturna con congelamento, come per Y4a.
> - **Costo**:
>   - FE9 3–4 ore: 7 inversioni, 6 file da spostare, `PasswordStrength`, la verifica di D-P4, documentazione e
>     devWiki;
>   - FE10 circa un'ora, dopo FE4, FE5 e FE8;
>   - FE11 2–3 ore, dopo la convenzione.
> - **Domande per il developer** (alla lista del mattino del coordinatore):
>   - **Y13-1**: FE9–FE11 dopo il tag della 1.3?
>   - **Y13-2**: per FE11, quale convenzione fra Modal e Dialog e fra Panel e Section? Oppure si lascia perdere FE11?
>   - **Y13-3**: `guideAnchors` di onboarding, usato da 20 componenti generici, va in un modulo neutro come
>     infrastruttura, o resta il file pubblico della feature, come vuole D-P4?

### Notte 16→17/10 · FE8b, allineamento a Z-18, kit di chiusura di Y11, contratto MF (23:11–23:30)

> **Note implementazione**.
> - **Congelamento FE8b** (W, 23:11). Nessun file congelato è aperto da me.
>   - `app-state.md:326` è una riga di prima, non mia, che cita `lib/components/transactions/shared/txDisplayHelpers.ts`.
>     Se W riscrive i percorsi nelle pagine, la cambia in dev; le mie aggiunte nello stesso file sono alla riga 20 e
>     dalla 454, quindi la fusione va da sola.
>   - Detto al coordinatore.
> - **⚠️ Fuori pista: la mia sezione `#page-busy` contraddiceva Z-18** (lotto B di Z, `1b46178bd`, già in dev). Il
>   ricaricamento dopo un recupero dei prezzi ora gira con `loadAll(false, false, {background: true})`, e la radice
>   `dashboard-page` resta `false`. Corrette due frasi della mia sezione, che non è committata:
>   - la radice segue i flag di caricamento della pagina, non i gettoni. Dopo un recupero dei prezzi restano entrambi
>     `false` (Z-18, passo 5 di `domain-state.md#how-a-page-uses-the-cache`);
>   - `reloadAfterPriceCatchUp()` chiama `loadAll()` o `loadOverview()` «senza gettone», non più «bare»: con gli
>     argomenti di Z-18 la parola non era più esatta.
>   - Il codice di Z-18 entra nel mio ramo con il prossimo aggiornamento della base.
> - **Kit di chiusura di Y11**, fuori dal repo (richiesta del coordinatore, 23:11), in `files/y11_closing/`:
>   - `CHANGELOG-lines.md`: due righe 🔄, cioè «una ⟦REFRESH⟧ per pagina» e «il Rischio senza un suo pulsante».
>     Il segnaposto di Y-15 ha la tabella A/B. Ci sono anche i controlli da fare alla chiusura: le righe Z-13 e Y-14
>     già nel CHANGELOG dicono «Refresh»; l'elenco delle 11 pagine; il Rischio sulla pagina dell'asset dopo il lotto
>     `assets/[id]`; una riga in più per Y-15;
>   - `user-docs-draft.md`: la scrive `docs-writer` (in sfondo). Contiene il paragrafo «una ⟦REFRESH⟧ per pagina» in
>     `user/dashboard/index.en.md#coming-back-and-refreshing`, i ritocchi di `brokers/index.en.md:86` e la tabella
>     delle occorrenze per Y-15;
>   - `files/scripts/y11_docrefs.py` (`capture`/`check`) e `docrefs_anchor.json`. Sono i 48 riferimenti a righe della
>     mia sezione, tutti giusti su `bf1b802d7`. Dopo l'aggiornamento della base, `check` dice quali si sono spostati e
>     dove; servirà perché Z-B e FE8b toccano Dashboard, broker e transazioni.
> - **Contratto MF per R17 e W8** (23:18): controllato sul codice.
>   - W8 coincide con le chiavi della treemap (`ExposureTreemap.svelte:371-374`): prima il broker, poi
>     `h.asset_type || 'Unknown'`. Nel riassunto `broker_id` non è mai null (`portfolio_service.py:779+`).
>   - Accettata una differenza: la treemap disegna solo i valori > 0 (`:368`), mentre il gruppo di MF conta anche un
>     asset a valore zero, che porta la sua perdita.
>   - Il frontend prenderà da MF sia `gain_loss` sia `gain_loss_percent` del gruppo, e smetterà di sommare.
>   - I rossi si scrivono dopo lo SHA di MF e lo slot del coordinatore, perché stanotte la Dashboard è ferma. Risposta
>     mandata a MF.

### Y-21 · E2E `front-portfolio risk` (slot 2, 23:25–23:37; HEAD `bf1b802d7` più Y-21, Y-5 e la documentazione) — 36/38

> **Note implementazione**. Comando: `bash files/scripts/y21_e2e.sh`, cioè
> `nice -n 10 … dev.py test --test-port 6189 --data-dir /tmp/librefolio-r13-y --workers 2 front-portfolio risk`. Il
> carico era 57 alla partenza. Log in `files/logs/y21_e2e_risk.log`; gli artefatti dei rossi sono stati copiati subito
> in `files/logs/y21_reds/`.
> - **Il bersaglio di Y-21 è verde**: L4 D377 (`:2815`) in 11,7 s, dentro il budget nuovo di 90 s.
> - **⚠️ Fuori pista: due rossi in test che non ho toccato**, del benchmark di L3 (commit `2f54c9c0b` dell'01/10 e
>   `28f201737` del 07/10). Tutti e due «Test timeout of 30000ms exceeded»:
>   - D378, `:3993`, «a move of the period asks the engine again…» (37,6 s). Si ferma in `moveToOneYear`: il
>     `data-active` di `date-preset-1y` non arriva a `true` prima della fine del budget. La fotografia della pagina
>     mostra però il clic avvenuto: l'intervallo è 2025-10-16 → 2026-10-16, e Refresh è disabilitato mentre arriva il
>     report di 1Y;
>   - benchmark condiviso, `:4456`, il caso della Dashboard «the picker offers an asset the scope holds» (40,1 s):
>     `openBenchmarkPicker` non vede opzioni entro 10 s. Manca la fotografia, perché la pagina si è chiusa al timeout.
> - **Triage** (skill `test-triage`):
>   - §1, la forma della risposta: non c'entra (nessuna posizione, nessun conteggio);
>   - §2, l'orologio: in questa corsa tutta la parte centrale del blocco è andata 2–3× più lenta delle due corse di
>     Y12b. Per esempio `:3073` 10,3 s contro 3,6, `:3309` 12,6 contro 4,5, `:3948` 14,1 contro 4,4. I primi test
>     (`:1921`–`:2766`) invece sono andati come allora, e i due rossi allora facevano 6–10 s;
>   - i test concatenano attese che insieme superano i 30 s del budget predefinito: la barriera di 20 s a `:1696`, il
>     selettore 10 + 10 s, i `poll` 10 + 15 s. Solo D377 ha 90 s (`:2817`);
>   - §3, stato condiviso: il DB della corsia pesa 1,3 MB e non è cresciuto; nessuna scrittura dei vicini c'entra. Il
>     log del backend non registra la durata delle richieste, quindi non si può misurare il backend da lì;
>   - nessuna regressione di Y: dalle corse verdi Y ha toccato solo la pagina dei broker (Y-14), una riga di
>     `levelHelpers` (Y-19) e la documentazione.
> - **Verdetto: un'assunzione sull'orologio**, cioè il budget del test, sotto contesa della macchina. È lo stesso schema
>   di Y-21.
> - **Al coordinatore** (23:40, `needs_input`):
>   - A (consigliata): un budget di 90 s per tutto il blocco, scritto da `test-author`, e una nuova corsa nello slot;
>   - B: Y-22 nel backlog.
>   - Ho segnalato anche il pulsante «Reload All» della scheda Correlation per il lotto `assets`.

### Kit di chiusura di Y11 · la bozza di `docs-writer` (23:40)

> **Note implementazione**. `files/y11_closing/user-docs-draft.md`, 285 righe. Nessun file del repo è stato toccato; le
> 8 stringhe OLD sono verificate esatte.
> - §1: alla riga 81 di `user/dashboard/index.en.md` c'è un H3 nuovo, `### 🔘 The ⟦REFRESH⟧ button {: #refresh-button }`.
>   Contiene le pagine con il pulsante e quattro punti: quando gira, quando no, i due minuti, il Rischio. L'ancora della
>   sezione resta.
> - §2–§4: `brokers/index.en.md:86` e `dashboard/index.en.md:62` puntano a `#refresh-button`. Ci sono cinque
>   collegamenti facoltativi.
> - §5: le tabelle di Y-15, cioè 16 occorrenze dell'etichetta del pulsante di pagina e 8 «Reload» che non cambiano.
>   Nota: le chiavi di traduzione sono condivise, quindi B ha bisogno di una chiave propria per il pulsante di pagina.
> - §7, i punti trovati nel codice:
>   - **la scheda Correlation**: `risk-reload-button` (`assets/+page.svelte:1581-1593`) sostituisce il pulsante della
>     lista ed è l'unico pulsante di ricarica della scheda, ma non legge `pageBusy`. **Decisione notturna, da
>     rivedere**: lo metto nel lotto `assets`, con `onmerged`;
>   - **la pagina dell'asset**: il pulsante è ancora `disabled={loading}` (`AssetDetailToolbarActions.svelte:90`), ed è
>     nel lotto `assets/[id]`;
>   - il caricamento di massa non è un'incoerenza. Sulla lista degli asset ricarica i prezzi di tutti gli asset
>     (`fetchAllPriceData`, `assets/+page.svelte:1015`), quindi conta come ricarica di pagina; nei cambi va riga per
>     riga (`fx/+page.svelte:822-828`);
>   - **le transazioni**: il pulsante azzera anche filtri e selezione, e nessuna pagina utente lo dice. Non è di Y;
>   - tornare su una pagina scaduta fa girare il pulsante (`*-first-load`). Il testo è scritto di conseguenza.

### Y-21 · opzione A: un budget di 90 s per tutto il blocco (decisione del coordinatore, 23:45)

> **Note implementazione**.
> - Il coordinatore sceglie A: `test-author` dà 90 s a tutto il blocco «Risk analysis functional integration» di
>   `risk-analysis.spec.ts`, in un solo punto.
> - Il `test.setTimeout(90_000)` di D377 diventa ridondante e si toglie; restano i `L4_OFFER_DEADLINE_MS`.
> - Poi si rifà la corsa di `front-portfolio risk` nello slot 2, dopo X (verso le 00:05, al suo via). Tutto entra nel
>   checkpoint di Y-21, con Y-5 e la pagina di `pageBusy`.
> - **Approvata dal coordinatore**, come decisione notturna: il «Reload All» della scheda Correlation va nel lotto
>   `assets`, con `onmerged`.
> - **23:47, il budget del blocco è fatto** (`test-author`). In `risk-analysis.spec.ts`:
>   - `test.describe.configure({timeout: 90_000})` in cima al blocco, con un commento: è un budget, non un'attesa;
>   - tolto il `test.setTimeout(90_000)` di D377, che era ridondante;
>   - `L4_OFFER_DEADLINE_MS` e i suoi quattro `poll` sono rimasti come erano;
>   - verificato su Playwright 1.61: il `timeout` del describe arriva a tutti i 38 test, e non va in conflitto con il
>     `mode: 'parallel'` del file.
>   - Contropartita accettata: senza `actionTimeout` un `click()` su un controllo che non diventa mai cliccabile cade a
>     90 s invece che a 30.
> - **Prove leggere**: svelte-check 0/0 (`files/logs/y21_front-check2.log`); Prettier pulito sulla spec e su
>   `types.ts`; `git diff --check` pulito.
>   - La documentazione: la build del sito fatta dentro la corsa E2E delle 23:31 comprende le due frasi corrette. Ha 0
>     WARNING ed è finita in 92,8 s, quindi la build stretta passa. L'ancora `domain-state.md#how-a-page-uses-the-cache`
>     esiste.
> - **Ordine nuovo del coordinatore** (23:50; T è entrato in dev con `9016f47c3`, che tocca la stessa spec):
>   1. checkpoint FROZEN;
>   2. il coordinatore committa e fonde dev nel mio ramo;
>   3. la nuova corsa nello slot 2, sulla revisione combinata, che prova anche i colori di T.
> - **Previsione della fusione**: nessun conflitto testuale.
>   - Nella spec, i pezzi di T sono a 3509–3648 (l'aiuto `roleBackground()` e le righe di L3), i miei a 1917 e
>     2801–2867.
>   - `app-state.md`: dev cambia solo la riga 326 (il percorso di FE8b); le mie aggiunte sono alla 20 e dalla 454.
>   - `domain-state.md`: dev cambia la 121 (Z-B), io la 84.
>   - Nella sostanza, i test di T nel blocco ricevono anche loro i 90 s.

### Y-21 · seconda corsa, sulla revisione combinata (slot 2, 23:50–00:03; HEAD `a49a86a7b`) — 36/38, ✅ per Y-21

> **Note implementazione**.
> - **Il checkpoint di Y-21** l'ha committato il coordinatore: `92e04271d` (spec), `0025383b4` (documentazione),
>   `dc68fc64b` (journal).
> - **La fusione** con dev `c91bd41b2` è `a49a86a7b`, pulita. L'ho verificata con `files/scripts/y21_after_merge.sh`:
>   i genitori, `api sync` a rc 0, il budget a `:1920`, `L4_OFFER_DEADLINE_MS` a `:2802`, `roleBackground()` di T a
>   `:3527`.
> - **Corsa**: `files/scripts/y21_e2e_rerun.sh`. Il carico era 94 alla partenza e 115 durante la build. Risultato
>   36/38 in 4,5 min; log in `files/logs/y21_e2e_risk_rerun.log`.
>   - **D377 è verde** (`:2820`, 22,2 s).
>   - **D378 (`:4025`) e il benchmark condiviso (`:4488`) sono verdi**: quello che il budget del blocco doveva fare.
>   - Tutta la corsa è andata 2–3× più lenta delle corse di Y12b: i primi test 11–19 s contro 5–8.
> - **⚠️ Fuori pista: due rossi nuovi, d'altro tipo.** Non sono nelle righe di T né nelle mie. Artefatti copiati in
>   `files/logs/y21_reds_rerun/`.
>   - `:3736`, la tabella di L3: `hoverUntilHelpOpens` non apre l'aiuto del «—» entro 10 s (`HELP_OPEN_DEADLINE_MS`).
>     La fotografia mostra L3 completa e l'aiuto chiuso. **Verdetto: un'assunzione sull'orologio** (una scadenza scelta
>     a carico normale).
>   - `:2871`, il benchmark scelto sulla Dashboard: `option.click()` (`:1476`) resta in «waiting for element to be
>     visible, enabled and stable» fino alla fine dei 90 s. L'opzione si era risolta un attimo prima: è eleggibile ed
>     evidenziata, e `toBeVisible` era passato. **Nessun verdetto**: manca fotografia e manca traccia, e un'attesa così
>     lunga non si spiega con l'orologio.
>     - Prossimo passo: quel test da solo con `--trace on`.
>     - Ipotesi da guardare, §1.4: il `.first()` su tutta la pagina.
>   - Va nel backlog: **Y-22**.
> - **I riferimenti della mia sezione `#page-busy`** dopo la fusione: 26 su 48 si sono spostati (Dashboard, broker, FX,
>   asset, transazioni, `page-busy.spec.ts`). Erano previsti, perché vengono da Z-B e da FE8b.
>   - Corretti con `files/scripts/y11_docrefs_fix.py`: 18 sostituzioni su 17 righe, ognuna legata al suo file e unica.
>   - Il caso ambiguo del controllo, a 666–678, l'ho risolto a mano: è quello della Dashboard.
>   - `y11_docrefs.py`, i riferimenti aggiornati e ricatturati: ogni riga contiene il codice che il testo dice. Lo
>     verifica `files/logs/y11_docrefs_capture2.log`.
>   - Sono solo numeri dentro codice in linea, quindi nessun link cambia.
> - **Y-21 ✅** nel backlog, **Y-22** aperto.

### Y-22 · traccia di `:2871` da solo (slot 2, dalle 00:08 del 17/10; HEAD `a49a86a7b`, Y-21 entrato in dev `149157025`)

> **Note implementazione**.
> - Il runner non ha `--grep`, quindi lancio Playwright direttamente, con `files/scripts/y22_trace.sh`:
>   - prima `dev.py server --test --build-only`;
>   - poi `pipenv run npm run test:e2e -- … -g "<titolo>" --trace on --repeat-each 4 --workers 2`. Il `webServer` della
>     configurazione avvia `dev.py server --test` su `TEST_PORT`/`LIBREFOLIO_TEST_DATA_DIR`, cioè la corsia;
>   - `--repeat-each 4`: un solo verde non spiega il rosso.
>   - **`LF_SETUP_DONE=1` è obbligatorio**: senza, `global-setup.ts` lancia `populate_mock_data --force` sul DB della
>     corsia, che non è autorizzato.
> - **⚠️ Fuori pista: ho lanciato lo script mentre lo modificavo** (00:08). Bash l'ha letto a metà modifica: la riga
>   del controllo della porta è uscita storpiata, e l'`export` della corsia non è stato eseguito. Il passo di Playwright
>   sarebbe partito sulla porta 6041 e sul DB predefinito.
>   - L'ho fermato durante il `--build-only`, prima di Playwright.
>   - Verificato: 6041 e 6189 libere; `backend/data/test` del worktree intatto, con solo `.gitkeep` e `logs` del 15/10;
>     nessun mio processo rimasto. Il server senza corsia visibile in `ps` è di `e-alfy-congenial-spoon`.
>   - Rimedio: ora lo script, prima di Playwright, si ferma se porta e cartella non sono quelle della corsia. In più,
>     da qui in poi non modifico mai uno script nello stesso blocco in cui lo lancio.
> - **Traccia di `:2871`** (00:08:58–00:10:44; carico 52–57): **4/4 verdi**, ciascuno 36–38 s. Senza traccia erano
>   8–16 s, quindi la traccia circa raddoppia il tempo; col vecchio budget di 30 s sarebbero tutti rossi.
>   - Lettura con `/tmp/libreFolio_y22_trace_parse.py`, log in `files/logs/y22_trace_parse.log`. In tutti e quattro
>     `option.click()` è subito eseguibile: da «waiting for element to be visible, enabled and stable» a «click action
>     done» passano 0,04–0,29 s.
>   - Il tempo si distribuisce su login, navigazione e i18n (fino a 12 s per l'aggancio del login), non su un singolo
>     passo.
>   - **Verdetto per `:2871`: ambiente, non riprodotto.** Nella corsa rossa (carico 94–115) il clic è rimasto in attesa
>     di eseguibilità per decine di secondi; a carico 55, quattro su quattro passano subito.
>     - Il sintomo è quello di un renderer affamato (ricordo che le mie corse girano con `nice 10`). Nella stessa corsa
>       anche `:3736` ha un predicato che non torna in 10 s.
>     - Il test resta com'è. Se ricompare, la prossima volta serve una traccia del caso rosso. La configurazione traccia
>       solo `on-first-retry`, e in locale non ci sono tentativi ripetuti.
> - **`:3736`**: `test-author` (`5833dce5`) allarga `HELP_OPEN_DEADLINE_MS` da 10 a 20 s, e valuta `HELP_REST_MS`.
>   Poi si verifica quel test da solo, ×4, con `files/scripts/y22_verify3736.sh`, più svelte-check e Prettier.
> - **`:3736`, la scadenza** (`test-author`, 00:1x):
>   - `HELP_OPEN_DEADLINE_MS` da 10 a 20 s, e `HELP_REST_MS` da 2 a 3 s. Il motivo, nel codice: `handlePointerLeave`
>     del Tooltip disarma il ritardo pendente a ogni tentativo, quindi un ritardo arrivato tardi deve stare in un solo
>     riposo, e la scadenza compra solo più tentativi.
>   - I due chiamanti (`:3733`, `:3783`) restano sensati. Commenti aggiornati con la misura del 17/10.
>   - Il test rosso era finito a 24,2 s; con 10 s in più resta dentro i 90 s, quindi un rosso dice ancora il suo nome.
>   - **Verifica**: `files/scripts/y22_verify3736.sh`, il test da solo (ora `:3748`), ×4, 2 lavoratori, carico 55:
>     **4/4** in 11–20 s. Log in `files/logs/y22_verify3736.log`.
> - **Y-23**, un rosso mio trovato da A in dev (coordinatore, 00:15). `ec018afdf` (Y11 passo 2) importa `onNavigate`
>   in `(app)/+layout.svelte`, ma i mock locali di `$app/navigation` in `layout.gate.test.ts` e
>   `layout.authGate.test.ts`, che sono di H, non lo esportano.
>   - **Rosso riprodotto**: `front-utility onboarding-component-unit` 20 rossi (9 + 11), tutti «No "onNavigate" export
>     is defined on the "$app/navigation" mock», nient'altro rosso.
>   - **Rimedio** (`test-author`): `onNavigate: vi.fn()` nei due mock.
>   - **Verde**: 454/454, 15 file.
>   - Il mock globale (`src/__mocks__/$app/navigation.ts`) lo esportava già. Nessun altro file importa `onNavigate`:
>     `pageBusy` lo nomina solo in un commento.
>   - **⚠️ Fuori pista**: nelle prove leggere del passo 2 di Y11 mancava `onboarding-component-unit`, che copre i test
>     del layout. Da qui in poi, quando tocco `routes/(app)/+layout.svelte`, la includo.
> - **Prove leggere finali** (00:29): svelte-check 0/0 (`files/logs/y22_front-check.log`); Prettier pulito sulla spec
>   e sui due test; `git diff --check` pulito.
> - **Y-22 ✅, Y-23 ✅** nel backlog. Checkpoint di seguito mandato al coordinatore.

## Y11 — il lotto `assets`: `assets/[id]`, `onmerged`, «Reload All» di Correlation (analisi 17/10, 00:35–00:50; HEAD `d7f3a49c3`)

> **Base**: HEAD `d7f3a49c3` = dev, pulito, con dentro il lotto A di Z, A7b e FE8b. `api sync` a rc 0.
> `y11_docrefs.py check`: 46/48. Si spostano `files/+page.svelte` 784→783 e `assets/+page.svelte` 1642→1644; li
> correggo alla fine del lotto, perché `assets/+page.svelte` cambia ancora.

### Stato reale

- **`assets/[id]/+page.svelte`** (2 770 righe) non ha nessun gettone.
  - Le chiamate che partono dall'utente, o dalla pagina per sé:
    - `onMount` → `reloadPage()` (`:1106`);
    - `$effect` sul cambio di `data.assetId` → `reloadPage()` (`:1114`);
    - `$effect` sul cambio di valuta → `loadChartData().then(maybeLoadComparison)` (`:1166`);
    - `handleDateRangeChange` (`:1750`);
    - `handleSignalsChange` (`:1822`);
    - `retryBackendSignals` (`:1043`);
    - Refresh → `onrefresh={() => handleRefresh()}` (`:2269`).
  - **`handleRefresh` ha 6 chiamanti**:
    - il pulsante (`:2269`);
    - dopo un sync: `handlePageSyncComplete` (`:1708`) e `handleFxPairCreationSynced` (`:1735`);
    - dopo un salvataggio in un modale: `handleAssetUpdated` (`:2117`), `handleFxPairCreated` (`:1728`) e `onsave` del
      modale dell'intervallo (`:2632`).
    - Dentro c'è `riskRefreshVersion += 1` (`:1639`).
  - Il poller dal vivo (`AssetDetailLive`) chiama `loadChartData` direttamente: resta senza gettone.
- **`AssetDetailToolbarActions.svelte`** (`components/assets/detail/`, area AF; la usa solo la pagina): il pulsante
  `asset-detail-refresh-btn` ha `disabled={loading}`, la rotazione su `loading` e nessun `data-busy`. La prop
  `loading` serve solo a quel pulsante.
- **`assets/+page.svelte`**:
  - `onmerged` (`:1911`) fa `invalidateAfterMutation` più `loadAssets()` senza gettone, mentre `onupdated`, accanto
    (`:1897`), ha già `assets-reload`;
  - `risk-reload-button` (`:1581-1593`, solo nella scheda Correlation, al posto del pulsante della lista) ha
    `disabled={!labPanel}`, nessun `data-busy` e nessuna rotazione.
- **`AssetSetRiskPanel.reload()`** (`features/risk`, `:224`) fa `invalidateRisk()` e `syncGeneration += 1`. Ogni
  sezione riceve quel numero come `refreshVersion` e ha il suo `createRiskPanelController`, quindi **i gettoni
  `risk-refresh` e `risk-load` ci sono già**. Manca solo il contratto del pulsante.
- **Il precedente della Dashboard** per il Rischio dopo un sync: i sync del banner della qualità dei dati (`:389`,
  `:465`) portano `refreshVersion`, «as after Aggiorna». Il report della pagina si ricarica senza gettone, i pannelli
  con il loro. Quindi sulla pagina dell'asset `riskRefreshVersion` resta in `handleRefresh`.
  - Dopo un sync, con la scheda Rischio aperta, il pulsante gira mentre il Rischio si ricarica, come sulla Dashboard.
  - È una sfumatura di P3, già in dev dalla 1.3 per la Dashboard: va nella revisione con il developer, con N55.

### Cosa cambia

1. `assets/[id]/+page.svelte`, gettoni sui punti che fanno partire, come nel dettaglio del cambio (passo 3):
   - `asset-first-load` (`onMount`), `asset-change` (cambio di asset), `asset-currency` (cambio di valuta);
   - `asset-period` (`handleDateRangeChange`), `asset-signals` e `asset-comparison` (`handleSignalsChange`),
     `asset-signals-retry`;
   - `asset-refresh` sul pulsante: `onrefresh={() => void pageBusy.track('asset-refresh', () => handleRefresh())}`;
   - `asset-reload` dopo un salvataggio in un modale: `handleAssetUpdated`, `handleFxPairCreated`, `onsave`, come
     `assets-reload` della lista;
   - senza gettone dopo un sync (P3): `handlePageSyncComplete`, `handleFxPairCreationSynced`.
2. `AssetDetailToolbarActions.svelte`: la prop `loading` diventa `busy`, con `disabled={busy}`,
   `data-busy={busy ? 'true' : 'false'}` e la rotazione su `busy`. La pagina passa `busy={pageBusy.busy}`; il
   componente resta di sola presentazione.
3. `assets/+page.svelte`:
   - `onmerged` → `await pageBusy.track('assets-reload', () => loadAssets())`, dopo `invalidateAfterMutation`;
   - `risk-reload-button` → `disabled={!labPanel || pageBusy.busy}`, `data-busy` e la rotazione.
4. Test (`test-author`):
   - in `page-busy.spec.ts` i casi nuovi:
     - dettaglio asset: Refresh e periodo aspettano; dopo un sync della pagina, con la scheda grafico aperta, il
       pulsante non aspetta, con il suo controllo;
     - Correlation: «Reload All» è disabilitato mentre le sezioni rileggono;
   - da rivedere: `risk-lab.spec.ts:7049` (`toBeEnabled()` subito dopo che le richieste sono partite),
     `fx-detail.spec.ts:1461` (`activateByKeyboard` sul pulsante), `asset-detail.spec.ts:232/532/2362`,
     `asset-mobile-layout.spec.ts:386/416`.
5. Documentazione: la tabella dei pulsanti e dei punti che fanno partire in `app-state.md#page-busy` (dettaglio asset,
   Correlation), più i 2 riferimenti spostati.
6. **E2E** nello slot: `page-busy`, `front-asset` (`asset-detail`, `asset-mobile-layout`, la lista), `fx-detail`,
   `risk-lab`, `risk`. È una corsa lunga, da chiedere.
7. Poi la **chiusura di Y11**: le righe del CHANGELOG del kit, la documentazione utente con la parola di Y-15, il
   backlog.

### Lotto `assets` · via e preparazione (17/10, 00:50–01:05)

> **Note implementazione**.
> - **Coordinatore**: FE5a (`components/assets/*` → `features/assets/`) non è nella coda di X stanotte e verrà dopo
>   questo lotto. Prima i test e la documentazione; lo slot E2E (~40 min) dopo la risposta dei colori e il codice.
> - **Il via dei colori su tutti e 3 i `.svelte`**:
>   - nessuna classe di palette: la rotazione è solo `animate-spin` e l'icona prende il colore del testo del pulsante;
>   - `theme-roles --check` entra nelle prove leggere;
>   - le 42 classi storiche della pagina dell'asset (gli interruttori delle barre del grafico, AF-1) aspettano il
>     designer, quindi non si toccano.
> - **`test-author` (`09f0c986`)** scrive in `page-busy.spec.ts` i casi rossi:
>   - dettaglio asset: Refresh, periodo, e P3 dopo il sync della pagina, con il suo controllo;
>   - Correlation: «Reload All»;
>   - facoltativo, `onmerged`.
>   - Rivede anche le attese di `risk-lab:7049`, `fx-detail:1461`, `asset-detail` e `asset-mobile-layout`.
> - **Il codice è pronto da applicare**: `files/scripts/y11_assets_apply.py`, 19 sostituzioni esatte, ciascuna unica
>   (prova a secco verde).
>   - In più rispetto all'analisi: il pulsante di `AssetDetailToolbarActions` prende
>     `disabled:opacity-50 disabled:cursor-not-allowed`, come il pulsante Modifica dello stesso componente. Senza, il
>     pulsante sarebbe «disabilitato ma non grigio», contro il contratto. Non sono classi di palette.
>   - Un commento d'una riga ai due chiamanti dopo un sync, «no pageBusy token … (P3)», così nessuno ne aggiunge uno.
> - **Ordine**:
>   1. i rossi su oggi, con `page-busy` in uno slot breve;
>   2. `--apply`;
>   3. prove leggere: svelte-check, `theme-roles --check`, Prettier, `check-orphans`, e
>      `onboarding-component-unit` se tocco il layout (non lo tocco);
>   4. lo slot E2E lungo;
>   5. la documentazione `#page-busy`: le righe del dettaglio asset e di Correlation, più i 2 riferimenti, con le righe
>      vere dopo il codice.
> - **I test sono scritti** (`test-author`, 01:05). È girato solo Prettier, che è pulito.
>   - `page-busy.spec.ts` +373 righe, con un blocco nuovo «Page busy on the asset pages…» e i casi:
>     - (a) Refresh;
>     - (b) il preset 6M;
>     - (c) P3 dopo il Sync della pagina, con il controllo;
>     - (d) «Reload All» di Correlation.
>   - Ogni caso controlla per primo che il pulsante pubblichi `data-busy`, quindi oggi va rosso in circa 3 s.
>   - Nessuna scrittura e nessun fornitore: il Sync è stubbato nel browser e il poll dal vivo è rifiutato.
>   - (d) gira sul motore del rischio vero, che legge e basta.
>   - (e), `onmerged`, è saltato: l'aiuto per creare la coppia è privato di `asset-merge.spec.ts`, e un merge è
>     irreversibile.
>   - Altre attese:
>     - `risk-lab.spec.ts:~7045`: `toBeEnabled({timeout: 15_000})` prima dei conteggi;
>     - `fx-detail.spec.ts:~1459`: `toBeEnabled({timeout: 10_000})` prima di `activateByKeyboard`;
>     - `asset-detail.spec.ts:7256`: tolto un `toBeDisabled()` che, con il cambio di finestra senza gettone, misurava
>       solo la coda;
>     - gli altri circa 40 usi sono invariati, con i verdetti nella risposta.
> - **Trovati da `test-author`, decisi dal coordinatore** (01:15):
>   - **tre scenari del test lungo di `asset-detail.spec.ts`** (`:3405/3412`, `:3907/3908`, `:7494`) premono Refresh
>     mentre una richiesta grande è trattenuta. Col contratto il pulsante è disabilitato, quindi **si riscrivono**: la
>     prima richiesta parte dal Sync della pagina, senza gettone, oppure prima si rilascia. Riscrittura affidata a
>     `test-author` (01:16);
>   - **N64** (decisione notturna, da rivedere con N55): `setPrimaryMode` → `asset-mode`, e
>     `setCalendarPreset`/`setCalendarCustom` → `asset-calendar-window`. Sono già nelle 23 sostituzioni.
> - **Slot breve per i rossi**: slot 2, dopo H (al suo via). Script `files/scripts/y11a_reds.sh`.
> - **I rossi** (slot 1, 01:27–01:37; HEAD `d7f3a49c3` senza codice; carico 40–49): `files/scripts/y11a_reds.sh`, cioè
>   `front-portfolio page-busy`, 16 test. Risultato: **4 rossi, i casi nuovi a–d, e 12 verdi**, quelli di prima.
>   - Tutti e quattro per la ragione giusta: «…publishes no data-busy: it does not follow the big requests of its page
>     (Y11)», con `Received string: ""`.
>   - Il pulsante è `asset-detail-refresh-btn` per a–c e il `risk-reload-button` di Correlation per d.
>   - Durata 14–18 s; log in `files/logs/y11a_reds_page-busy.log`.
>   - La build di quella corsa lancia svelte-check solo come diagnostica, senza guardarne l'esito (`dev.py:677-678`), e
>     Playwright carica solo `page-busy.spec.ts`. Quindi le modifiche in corso di `test-author` su
>     `asset-detail.spec.ts` non toccavano la corsa.
> - **Codice applicato** (01:38): `y11_assets_apply.py --apply`, 23 sostituzioni in 3 file (+36/−27).
>   - `theme-roles --check` pulito: «0 files dropped below their record».
>   - **⚠️ Fuori pista**: Prettier segnalava 2 file, che a HEAD erano puliti, per le mie righe. Con `--write`: la catena
>     `.then` di `asset-change` va a capo, e gli attributi del pulsante di `AssetDetailToolbarActions` vanno uno per
>     riga. Il diff di Prettier tocca solo quelle righe.
> - **Poi**: la riscrittura dei 3 scenari (`test-author`, in corso), svelte-check, Prettier su tutti i file,
>   `theme-roles --check` di nuovo, lo slot lungo, la documentazione.
> - **I 3 scenari riscritti** (`test-author`, 01:5x), in `asset-detail.spec.ts`:
>   - un aiuto nuovo, `refreshThroughPageSync()` (2622–2685): il Sync della pagina con ogni voce `skipped`, quindi
>     niente accettato e niente scritto;
>   - **scenario 1** (3449–3523): la prima generazione parte dal ricaricamento del Sync, senza gettone, e poi Refresh la
>     sostituisce. È la mossa concordata;
>   - **scenari 2 (3960–4031) e 3 (7544–7640)**: la richiesta più vecchia in volo viene da azioni sempre tracciate (il
>     cambio del termine di confronto; MAX più due ritorni a Price). Quindi è il Sync che fa partire il refresh sotto
>     prova, e le asserzioni restano tutte.
>     - Rilasciare prima avrebbe perso l'intento: i dati che arrivano a metà refresh, e le risposte tardive, cioè il
>       successore e il 503 provvisorio.
>     - Il pulsante resta coperto dagli altri 29 clic del test e da `page-busy`. **Accettato**: rientra nel via del
>       coordinatore («la prima richiesta parte dal Sync della pagina»);
>   - 3405–3418: riordino precauzionale (attesa di Refresh abilitato, poi il cancello);
>   - 7335–7337: torna il `toBeDisabled()` che con N64 ha di nuovo senso;
>   - una rotta nuova nella fixture: `GET /api/v1/fx/providers` → lista vuota, che toglie anche una chiamata vera verso
>     ECB e SNB.
> - **Prove leggere sul tutto** (02:0x; carico 40–45): svelte-check 0/0 (`files/logs/y11a_front-check.log`); Prettier
>   pulito sui 7 file di codice e di test; `theme-roles --check` pulito; `git diff --check` pulito.
>   - `check-orphans` non serve: nessun file di test nuovo.
> - **Slot lungo** da chiedere, con `files/scripts/y11a_e2e.sh`: `page-busy`, `asset-detail`, `asset-mobile-layout`,
>   `asset-list`, `fx-detail`, `risk-lab`, `risk`.
> - **Documentazione e runner** (02:1x, prima dello slot lungo, così la build del sito della corsa le comprende):
>   `files/scripts/y11a_docs_apply.py`, 15 sostituzioni uniche.
>   - `app-state.md#page-busy`, la tabella dei punti che fanno partire:
>     - `asset-first-load`;
>     - `asset-refresh` su `onrefresh`, con il perché: `handleRefresh()` gira anche dopo un sync;
>     - `asset-period`, `asset-currency`, `asset-mode`, `asset-calendar-window`;
>     - una riga nuova, «A reload after a save in a window» (`assets-reload` ×3, `asset-reload` ×3);
>     - Correlation (`AssetSetRiskPanel.reload()` → `refreshVersion` delle sezioni).
>   - «Never for»: il ricaricamento dopo un sync della pagina dell'asset, più la sfumatura scritta come comportamento.
>     Un sync fa ancora aspettare un pannello aperto, attraverso `refreshVersion` e `riskRefreshVersion`.
>   - Tabella dei pulsanti: le righe nuove «Asset detail» e «Assets list, Correlation tab»; File 784 → 783 e lista
>     degli asset 1642 → 1645.
>   - Test: i riferimenti di `page-busy.spec.ts` spostati dall'intestazione nuova (178, 214, 220/226, 338, 368,
>     679–691), più il punto 6 sui casi delle pagine degli asset (l.1184).
>   - `_frontend_portfolio.py`: la descrizione di `page-busy` nomina le pagine degli asset.
>   - `y11_docrefs.py` ora tiene 69 riferimenti, ricatturati e controllati a occhio
>     (`files/logs/y11_docrefs_capture3.log`).
>   - Solo codice in linea, nessun link nuovo. Il WARNING della build va controllato nel log dello slot lungo.
> - **Ordine nuovo del coordinatore** (01:54). DV è entrato in dev `323c61b73` con i neutri di tutti i grafici: 25 file in
>   `components/charts/`, `features/dashboard/`, `CorrelationHeatmap`, `features/brokers/lots/`, più `chartTheme.ts` e
>   `roleColors.ts`. Quindi la corsa lunga deve provare la revisione **combinata**:
>   1. checkpoint FROZEN subito, con il lotto com'è;
>   2. commit e fusione con dev;
>   3. la corsa lunga, nello slot 2 dopo X.
>   - **Checkpoint mandato alle 01:5x**: 10 percorsi, nessuno toccato da dev dopo `d7f3a49c3`. Le liste per lo stage
>     sono `files/y11a_stage_{feat,tests,docs,journal}.txt`.
>   - La documentazione era già fatta e verificata: va nel checkpoint come commit a parte. Lasciarla non committata
>     avrebbe rischiato di fermare la fusione, perché `app-state.md` cambia spesso in dev.
>   - **⚠️ Fuori pista**: nel controllo prima dell'handoff c'era un `git fetch -q` inutile (`dev_release2` è un ramo
>     locale condiviso). Restava appeso, credo per la rete o l'autenticazione, e l'ho fermato dopo 30 s: nessun
>     processo rimasto, nessun ref cambiato che importi. Non lo rifaccio.

### Lotto `assets` · committato e base aggiornata (17/10, 01:56–01:59)

> **Note implementazione**.
> - **Commit del coordinatore**: `37bfeebb9` (feat), `fcd435668` (tests), `e42d1d75d` (docs), `1cfbd913e` (journal).
> - **Fusione** con dev `323c61b73`, che contiene DV con i neutri di tutti i grafici: **`2cd430a5e`**, pulita.
> - Verifiche con `files/scripts/y21_after_merge.sh`:
>   - i genitori `1cfbd913e` e `323c61b73`;
>   - `api sync` a rc 0;
>   - `y11_docrefs.py check` **69/69 invariati**: DV non sposta nessuna riga citata.
> - **Prove leggere sulla revisione combinata** (carico 31): svelte-check 0/0
>   (`files/logs/y11a_front-check_merged.log`); `theme-roles --check` pulito.
> - **Poi**: la corsa lunga `files/scripts/y11a_e2e.sh`, nello slot 2 dopo X, al via del coordinatore.
> - **Corsa lunga avviata e poi fermata** (slot 2, 02:04–02:2x, su `2cd430a5e`): `files/scripts/y11a_e2e.sh`.
>   - Il coordinatore l'ha fermata alle 02:2x: la galleria dei colori gira fino alle 03:30 circa e il carico era a 159–170,
>     quindi i timeout da carico andrebbero solo rifatti.
>   - Arrivata fin qui: **`page-busy` 16/16 verdi** (2,4 min), compresi i 4 casi nuovi a–d; `asset-detail` partito, 3
>     verdi, poi fermato; il resto non partito.
>   - Fermata con `stop_bash`: porta 6189 libera, nessun mio processo rimasto.
>   - **Ripresa dopo le 03:30**, prima in coda, con `files/scripts/y11a_e2e2.sh`: da `asset-detail` in poi, senza
>     `page-busy`, già verde su questa revisione.

## R17 · W8 · P4 — analisi lato frontend (17/10, 02:00–02:30; sola lettura; HEAD `2cd430a5e`, MF-P in dev `536501541`)

Approvato dal coordinatore alle 02:02, con P4 nello stesso lotto. Il testo completo, in inglese, è in
`files/r17_w8_analysis.md` della sessione.

- **Backend** (MF-P, `f191dfbf9`, solo backend; nessun file frontend cambiato in dev). In `PortfolioSummary`, tutte
  frazioni:
  - `timing_effect_percent` = MWRR cumulativo − TWRR, null se manca uno dei due;
  - `pnl_change_1d` (Currency): il P&L totale da **D−1 di calendario** a D, null per un portafoglio nato in D;
  - `pnl_change_1d_vs_total_pnl_percent` e `…_vs_nav_percent`: Δ/|base di D−1|, col segno di Δ, null con base 0;
  - `holding_groups: [{broker_id, asset_type|null, gain_loss, gain_loss_percent}]`, dove contano solo i titoli con
    valore e G/L noti.
- **R17**, `features/dashboard/KpiSection.svelte`, usato dalla Dashboard (`:1012`) e dalla pagina del broker (`:647`):
  - via `prevHistoryPoint` (`:78`), il Δ dagli ultimi due punti della `history` (`:80-85`), `dayChangePct`
    (`:93-96`), le due percentuali (`:99-102` sul NAV, `:131-134` sul P&L totale) e `mwrr − twrr` (`:243`);
  - al loro posto, letture dei 4 campi. Resta solo il ×100 di presentazione, come `returnPct()`. Le scale del colore
    del timing (`:244-249`) restano;
  - per l'utente: con una serie campionata, il «giorno» di oggi confronta due punti lontani; il backend usa D−1 di
    calendario, che è già quello che dice la documentazione utente («from yesterday to today»).
- **W8**, `ExposureTreemap.svelte` + `PositionsPanel.svelte`:
  - via le somme del G/L di gruppo (`:423-424`) e `aggregateGlPct` (`:449`, usato a `:471` e `:487`). È lì il 🐛: un
    titolo con G/L ignoto metteva il suo valore nel costo;
  - una prop nuova, `holdingGroups`, con la ricerca per `(broker_id, asset_type|null)` sulle stesse chiavi della treemap
    (`:373-376`); un gruppo assente si legge «—»;
  - `PositionsPanel` (`:205`) ha già `summary`, quindi passa `summary.holding_groups`. Le pagine non cambiano;
  - le somme di valore e peso restano: non sono W8;
  - differenza accettata con MF: la treemap disegna solo valore > 0 (`:371`).
- **P4**, `PerformanceChart.svelte`:
  - il netto (l'etichetta della barra `:252` e la riga del tooltip `:545`) passa a `period_pnl_percent` (`:47`, che
    arriva già e non viene letto);
  - le componenti del tooltip (`:548`): **MF sceglie (a)** (02:03). Arrivano 4 campi in `AssetPeriodContribution`:
    `period_unrealized_delta_percent`, `period_realized_gain_loss_percent`, `period_income_percent`,
    `period_fees_taxes_percent`.
    - Sono arrotondati a 4 decimali: non si somma per rifare il totale. Null con un inizio 0 o null.
    - `fees_taxes` è positivo e si mostra come costo.
    - In dev entro la mattina del 17/10; MF manda lo SHA.
    - Le componenti si cablano solo quando la fusione di MF è nella mia base, così non spariscono nel frattempo.
- **Colori**: i 4 file sono già sui ruoli (KpiSection `a694d8fb2`, ExposureTreemap `38e17c2a5` DV B4, PositionsPanel
  `45f582eeb`, PerformanceChart `38e17c2a5`). Cambiano solo gli script, più una prop nel template di PositionsPanel.
  **Prima di scrivere lo dico al coordinatore**, che avvisa i colori, anche per la cifra delle KPI nella galleria.
- **Test** (`test-author`, rossi prima):
  - `KpiSection.test.ts`: una `history` i cui ultimi due punti darebbero cifre diverse dai campi; i null;
  - `ExposureTreemap.test.ts`: un gruppo con un titolo dal G/L nullo;
  - `PerformanceChart.test.ts`: `period_pnl_percent '0.07'` contro 50/1000 → «+7.0%»;
  - i tre file sono già registrati.
  - E2E: nessuna spec legge questi valori. Slot breve: `dashboard`, `front-broker detail`, `privacy-masking`.
- **Documentazione e CHANGELOG**:
  - una frase in `kpi-cards.en.md` (il giorno di calendario prima, anche con punti settimanali), che è debito di
    traduzione;
  - due righe 🐛 al coordinatore: il Δ del giorno su D−1 di calendario; il G/L % dei gruppi della treemap.
- **Ordine**:
  1. dopo l'ingresso del lotto `assets`, l'aggiornamento della base con MF-P e `api sync`;
  2. i rossi Vitest;
  3. l'avviso al coordinatore, poi il codice;
  4. le prove leggere;
  5. lo slot breve.
  - Costo: 2,5–3 ore con P4.
> - **Correzione** (coordinatore, 02:18): MF-P **è già** nella mia base. Verificato: `536501541` è antenato di
>   `2cd430a5e`, e il client generato ha `pnl_change_1d*`, `timing_effect_percent`, `holding_groups` e
>   `HoldingGroupGainLoss`. Prima l'avevo creduto più tardo. Quindi niente aggiornamento della base per R17/W8: i rossi
>   Vitest si scrivono subito, **solo file di test**; il codice dopo la corsa lunga, perché la build deve restare quella
>   del lotto `assets`.
>   - `test-author` (`59152098`): `KpiSection.test.ts` (R17), `ExposureTreemap.test.ts` (W8), `PerformanceChart.test.ts`
>     (P4, solo il netto).
>   - **Le componenti di P4 no**: un caso scritto ora resterebbe rosso anche dopo il codice di questo lotto, finché
>     non arrivano i campi di MF, e un rosso non deve entrare in dev. Vengono dopo, con lo SHA di MF.
>   - Rossi da lanciare con il carico sotto 50, file per file, con `frontend/node_modules/.bin/vitest run <file>`.
> - **I rossi sono scritti** (`test-author`, 02:4x): 15 casi nuovi.
>   - KpiSection: il Δ del giorno con le sue due quote e il timing dal riassunto; i null e gli assenti, perché un
>     report in cache da prima di MF-P non ha i campi.
>   - ExposureTreemap: il gruppo del backend, «—» per un gruppo assente, nessuna cifra per un gruppo con i valori a
>     null.
>   - PerformanceChart: `period_pnl_percent` sul netto, nell'etichetta e nel tooltip; null e assente.
>   - Circa 27 casi esistenti leggevano gli ingressi di prima. Ora le loro fixture portano anche i campi nuovi
>     coerenti, così restano verdi prima e dopo; nessuna asserzione cambiata. V2 verifica solo che la scheda scriva le
>     quote che riceve: la regola del segno ora la prova il backend.
>   - Prettier pulito. Nessun file di prodotto o del runner toccato.
> - **⚠️ Fuori pista: la fixture della galleria** (`frontend/e2e/dashboard-report.json`, un'istantanea vera) non ha i
>   campi di MF-P.
>   - Dopo il codice di R17/W8, nella galleria sparirebbe la riga del giorno, e timing e G/L dei gruppi leggerebbero
>     «—».
>   - Per la regola 12 (`test-author.agent.md:242`) un'istantanea non si tocca a mano. Mandate al coordinatore, per il
>     developer: (a) una cattura nuova, poi `normalize-dashboard-fixture`; (b) derivare i campi con le funzioni del
>     backend, come `a26051686`; (c) «—» fino ad (a).
>   - Propongo (a), e (c) nel frattempo. Il codice va avanti comunque, perché cambia solo la galleria.
> - **I rossi** restano da lanciare con il carico sotto 50 (alle 02:45 era 88).
> - **Decisione sulla fixture** (coordinatore, 02:46): **(c) fino ad (a)**. È fra le domande del developer, e i colori
>   sono avvisati.
> - **I rossi, lanciati** (02:47–02:50, carico 44; `files/scripts/r17w8_reds.sh`, `node_modules/.bin/vitest run`, file
>   per file): **15 rossi, come previsto**, tutti su asserzioni:
>   - `KpiSection` 9 rossi su 51: `-100.00 EUR` della history contro `+12.34 EUR` del riassunto;
>   - `ExposureTreemap` 3 su 7: `-2.78%` della somma contro `-3.23%` del gruppo; `7.14%` contro `11.11%`; il bond
>     `-200.00 EUR -9.09%` contro nessuna cifra;
>   - `PerformanceChart` 3 su 20: `+5.0%` contro `+7.0%`; null e assente.
>   - Nessun errore d'import o di setup; gli altri 63 sono verdi. Log in `files/logs/r17w8_red_*.log`.
> - **Preferenza dei colori** (02:50): R17/W8 entra **dopo le 04:45**, la fine della cattura «after» della galleria,
>   così il foglio del developer mostra solo i colori. Non è un blocco; il mio ordine ci arriva comunque.
> - **Il codice R17/W8/P4 (netto) è pronto, non applicato** (02:5x–03:0x): `files/scripts/r17w8_apply.py`, 23
>   sostituzioni esatte e uniche, prova a secco verde. Si applica dopo la corsa lunga di `assets`.
>   - **KpiSection**:
>     - via `prevHistoryPoint` e `dayChangePct`;
>     - `pnlDeltaDay` ← `safeCurrency(summary.pnl_change_1d)`;
>     - le due quote ← `returnPct(…_vs_nav_percent / …_vs_total_pnl_percent)`;
>     - `timingEffectVal` ← `returnPct(summary.timing_effect_percent)`.
>   - **ExposureTreemap**:
>     - una prop `holdingGroups` (tipo locale `HoldingGroupFigures`);
>     - via le somme `gl` e `aggregateGlPct`;
>     - `groupGainLoss(brokerId, assetType)` con la chiave `JSON.stringify([broker_id, asset_type])`;
>     - un gruppo assente o null non mostra cifre: il tooltip salta già le righe con `gl`/`glPct` null.
>   - **PositionsPanel**: `holdingGroups={summary?.holding_groups ?? []}`.
>   - **PerformanceChart**:
>     - `AssetRow.netPct` ← `safeDecimal(position.period_pnl_percent)`;
>     - `netReturnSuffix` e `netReturnPlainSuffix` (frazione ×100), per l'etichetta della barra e la riga «Period
>       P&L» del tooltip;
>     - le componenti restano su `openingPctSuffix` finché non arrivano i campi di MF;
>     - via `openingPctPlainSuffix`, che dopo il cambio non ha più chiamanti.
> - **Il blocco della galleria dalle 03:50 alle 04:45** (coordinatore, 03:06): la corsa lunga di `assets` parte
>   **subito dopo le 04:45**, prima in coda. Gli ho corretto un equivoco: l'`all-backend` sulla porta 6182 non è mio,
>   perché la 6189 è libera.
> - **devWiki** (03:1x, skill `wiki-file`), tre pagine:
>   - `wiki/concepts/page-busy-refresh-button.md`: il contratto di P3, le regole, il pulsante e lo schema E2E. Nella
>     wiki non c'era niente su `pageBusy`;
>   - `wiki/problems/e2e-chained-waits-outlast-the-test-budget.md`: Y-21 e Y-22;
>   - `wiki/problems/direct-playwright-run-in-a-test-lane.md`: `LF_SETUP_DONE`, la guardia della corsia, lo script
>     modificato mentre bash lo eseguiva.
>   - Più le righe in `index.md` e la voce in `log.md`.
>   - `check_source_paths.py`: 7 mancanti, tutti di prima, nessuno su queste pagine (4128 citati).
>   - Il grafo non è aggiornato: graphify non c'è in questo worktree.
> - **Nel worktree, non committato**: i 3 file di test di R17/W8 (i rossi), da non committare prima del loro codice
>   per non portare 15 rossi in dev; il journal; la devWiki.
> - **MF-P4b entrato in dev** (`d93de2899`, commit `5e30d875e`, solo backend; coordinatore, 03:40). I 4 campi sono in
>   `AssetPeriodContribution`: frazioni arrotondate a 4 decimali, null con un inizio 0 o null, `fees_taxes` positivo.
>   Arrivano nella mia base con l'aggiornamento dopo il lotto `assets`. Quindi **le componenti di P4 entrano nello
>   stesso lotto di R17/W8**.
>   - `r17w8_apply.py`: la parte di PerformanceChart è riscritta, **27 sostituzioni**, prova a secco verde; la copia
>     di prima è in `r17w8_apply.py.bak_netonly`.
>     - Un solo `returnSuffix(fraction)`, con la variante semplice, e `signedMoneyWithReturnHtml` per il netto e le
>       componenti.
>     - `AssetRow.netPct` e `componentPcts`, e i 4 campi nell'interfaccia locale.
>     - I costi negati per la presentazione, come il denaro.
>     - Via `openingPctSuffix`, `openingPctPlainSuffix` e `signedMoneyWithOpeningPct(Html)`, che restano senza
>       chiamanti.
>   - `test-author`, un agente nuovo: il precedente, `59152098`, non era più disponibile. Scrive i casi rossi delle componenti, più i 4 campi nelle fixture
>     `EUR_ASSET`/`CHF_ASSET`, così i casi esistenti stampano lo stesso a un decimale.
> - **Previsione della fusione per l'aggiornamento della base**, verificata dal merge-base `323c61b73`:
>   - fra i miei percorsi non committati, dev ha cambiato solo `LibreFolio_devWiki/log.md`: un'aggiunta di 5 righe
>     dopo la 3702, mentre la mia è in coda, dopo la 3715. Non sono adiacenti, quindi la fusione è pulita;
>   - il mio piano, `index.md`, i 3 file di test e i 4 file di prodotto non sono cambiati in dev. Il «differs» del
>     piano era solo il mio commit di journal non ancora entrato;
>   - nessun blocco previsto, con o senza i miei file non committati.
> - **I rossi delle componenti di P4 sono scritti** (`test-author` `77e23d11`, 03:46–04:00; solo `PerformanceChart.test.ts`,
>   Prettier pulito).
>   - Fixture `EUR_ASSET`/`CHF_ASSET`: i 4 campi con `componentReturn()`, cioè `periodReturn`, `toFixed(4)`, costi
>     positivi. Controllato a mano che a un decimale stampino lo stesso di oggi: EUR +28,6 / +18,3 / +7,4 / −1,1 %, CHF
>     −19,0 % e 0,0 %; nessun confine d'arrotondamento.
>   - In un describe annidato «component returns from their own fractions (MF-P4b)», tre casi rossi e un controllo:
>     - le frazioni proprie, con i costi negati, contro la divisione: `(+3.0%) (-1.1%) (+0.9%) (-0.4%)` contro
>       `(+2.0%) (-0.7%) (+0.5%) (-0.2%)`;
>     - una frazione null o assente → nessun ritorno su quella riga (×2);
>     - il controllo: inizio 0 e frazioni null, nessun ritorno, verde prima e dopo.
>   - Ogni riga si legge «tutto quello che segue l'importo», quindi un `(—)` o un `(0.0%)` fa rosso.
>   - **Rinforzato** anche il caso di prima, quello del netto null o assente: ora nel tooltip, dopo l'importo, non deve
>     esserci niente. Prima un `(—)` sarebbe passato.
> - **Rossi non lanciati**: il carico era a 143 alle 03:58, per il blocco della galleria. Si lanciano dopo
>   l'aggiornamento della base, prima del codice. Resta una corsa rossa valida, perché dev non ha toccato i 4 file di
>   prodotto.
> - **Da tenere fuori dal checkpoint di `assets`**: i 3 file di test di R17/W8/P4 (18 rossi su oggi), che entrano solo
>   insieme al loro codice.
> - **Rossi lanciati di nuovo, con le componenti** (04:01–04:04; il carico è sceso a 44 durante il blocco della
>   galleria; `files/scripts/r17w8_reds.sh`, invariato): **18 rossi, tutti su asserzioni**.
>   - `KpiSection` 9/51;
>   - `ExposureTreemap` 3/7;
>   - `PerformanceChart` 6/24: i 3 del netto, più i 3 delle componenti, cioè `(+2.0%)` della divisione contro
>     `(+3.0%)` della frazione e il null/assente. Il controllo, con inizio 0, è verde.
>   - Gli altri 64 sono verdi; nessun errore d'import o di setup. Log in `files/logs/r17w8_red_*.log`.
> - **Resta, dopo la corsa lunga e l'ingresso di `assets`**: l'aggiornamento della base (con MF-P4b) e `api sync`, poi
>   l'avviso al coordinatore per i file DV e il suo via; `r17w8_apply.py --apply`; i verdi Vitest dei 3 file;
>   svelte-check, `theme-roles --check` e Prettier; lo slot breve.

### Lotto `assets` · corsa lunga sulla revisione combinata ✅ (slot 2, 04:31–04:47; HEAD `2cd430a5e`; carico 24–35)

> **Note implementazione**.
> - **Comando**: `files/scripts/y11a_e2e2.sh`, la ripresa dopo il blocco della galleria. Sequenziale, `--workers 2`,
>   porta 6189, `/tmp/librefolio-r13-y`.
> - **Risultato: tutto verde.**
>   - `front-asset asset-detail` 35/35 (2,8 min), con i 3 scenari riscritti e il `toBeDisabled` ripristinato;
>   - `asset-mobile-layout` 21/21;
>   - `asset-list` 30/30;
>   - `front-fx fx-detail` 17/17;
>   - `front-portfolio risk-lab` 44/44;
>   - `risk` 38/38.
>   - Con `page-busy` 16/16 della prima corsa (02:04, stessa revisione), fanno **201/201**.
>   - Log in `files/logs/y11a_e2e2_*.log` e `y11a_e2e_front-portfolio_page-busy.log`.
> - **Documentazione**: il sito della prima corsa comprende `e42d1d75d`: 0 WARNING, costruito in 155,9 s.
> - Porta 6189 libera, nessun processo rimasto.
> - **Il lotto `assets` è pronto per l'ingresso**: `37bfeebb9`, `fcd435668`, `e42d1d75d`, `1cfbd913e`, più la fusione
>   `2cd430a5e`. Con questo **Y11 è completo nel codice**: tutte le pagine e la scheda Correlation. Restano per la
>   chiusura le righe del CHANGELOG e la documentazione utente del kit (`files/y11_closing/`), che aspettano la parola di
>   Y-15 dal developer.

## R17 · W8 · P4 — implementazione (17/10, dalle 04:48; HEAD `d32d0f3d9`, il lotto `assets` entrato, MF-P4b dentro)

> **Note implementazione**.
> - **Base**: `d32d0f3d9` = dev, con dentro il lotto `assets` (`aa95cc86d` journal, `1e93d8046` wiki) e MF-P4b.
>   - `api sync` a rc 0: il client ha i 4 campi `period_*_percent`;
>   - i 4 file di prodotto non sono cambiati da `2cd430a5e`;
>   - la prova a secco dà ancora 27 sostituzioni; `y11_docrefs.py` 69/69;
>   - svelte-check prima del codice 0/0, con i 3 test trattenuti.
> - **Via dei colori** sui 4 file DV (coordinatore, 04:5x).
>   - Le regole: non toccare le 4 classi di palette delle barre di `KpiSection`, che sono nella baseline e aspettano
>     il designer; i colori di segno solo dagli aiuti esistenti; un aiuto nuovo nei file del tema solo con il loro via;
>     `theme-roles --check` fra le prove leggere.
>   - Rispettate tutte: nessun attributo `class` cambiato (controllato sul diff), nessun colore e nessun aiuto nuovo.
> - **Applicato** `r17w8_apply.py --apply`: 27 sostituzioni in 4 file (+71/−74). Prettier pulito.
> - **⚠️ Fuori pista, due correzioni a mano in `ExposureTreemap.svelte`**, trovate dalle prove:
>   1. **Il rosso del gruppo assente.** Il caso chiede «—», come diceva il mio brief, ma il tooltip saltava le righe
>      con `gl` null.
>      - Ora le tessere di tipo e di broker scrivono «Unrealized P&L: —» quando il backend non dà una cifra (gruppo
>        assente o null); le tessere degli asset restano come prima.
>      - È la regola «null → «—»» concordata con MF.
>   2. **svelte-check, 3 errori.** Un `gl: 0` rimasto nell'inizializzazione della tessera di tipo, e il mio tipo locale
>      `HoldingGroupFigures` che non combaciava con il tipo generato, dove ogni campo ammette anche array.
>      - Ora il tipo è `NonNullable<PortfolioSummary['holding_groups']>[number]`, dallo store, come usano già
>        `PositionsPanel` e il test.
>      - Le letture passano per `safeString`, `safeCurrency` e `safeDecimal` di `$lib/types`. A runtime è equivalente.
> - **Prove** (carico 31–56):
>   - Vitest: `KpiSection` 51/51, `ExposureTreemap` 7/7 (dopo la correzione 1), `PerformanceChart` 24/24,
>     `AllocationPanel` 3/3;
>   - **`front-utility core-unit` 7941/7941** (200 file, con i gate di HTML e denaro) e **`component-unit`
>     4468/4468** (166 file). Sono girati prima della correzione 2, che cambia solo tipi e letture equivalenti; dopo
>     ho rilanciato il file della treemap;
>   - svelte-check 0/0 dopo la correzione 2; `theme-roles --check` pulito; `git diff --check` pulito.
>   - Log in `files/logs/r17w8_green*_*.log`, `r17w8_core-unit.log`, `r17w8_component-unit.log` e
>     `r17w8_front-check_post2.log`.
> - **Documentazione per sviluppatori**: `pages/index.md:120-123` descriveva ancora il calcolo nel browser (gli ultimi
>   due punti della history, `mwrr − twrr`). Affidata a `docs-writer`. Nessuna pagina utente cambia:
>   `kpi-cards.en.md` dice già «from yesterday to today».
> - **Slot breve** pronto: `files/scripts/r17w8_e2e.sh` (`front-portfolio dashboard`, `privacy-masking`,
>   `front-broker detail`).
> - **E2E breve** (slot 1, 05:11–05:25; `files/scripts/r17w8_e2e.sh`): `front-portfolio dashboard` 27/27,
>   `privacy-masking` 18/18, `front-broker detail` 38/38: **83/83**. Porta 6189 libera, nessun processo rimasto.
> - **Documentazione** (`docs-writer`):
>   - `developer/frontend/pages/index.md` (+23/−5): i punti del Δ del giorno e del timing dicono ora che si leggono i
>     campi del backend; due punti nuovi per i gruppi della treemap e per i ritorni di `PerformanceChart`;
>   - `user/dashboard/kpi-cards.en.md`, due frasi: «It needs two days of history» era fuorviante. Ora la riga manca
>     solo quando il periodo finisce nel primo giorno del portafoglio, e di lunedì copre il fine settimana.
>     **Debito di traduzione**: it/fr/es hanno ancora la frase vecchia, senza stamp.
>   - Durante la corsa E2E `docs-writer` non ha lanciato build: due build scriverebbero sullo stesso `mkdocs_src/site`.
>     Le ho lanciate io dopo, con `files/scripts/r17w8_docs_check.sh`: build stretta rc 0 e 0 WARNING (53,7 s);
>     `check-links` con 97 collegamenti validi.
> - **Backlog**: T-U8 («il frontend solo di presentazione») sta nella sezione T, che non è mia. Lo segnalo al
>   coordinatore: con Y12a e questo lotto restano solo V11 e P5, che aspettano MF-E e il CP-7b di J.
> - **E2E breve verde** (05:11–05:25): `dashboard` 27/27, `privacy-masking` 18/18, `front-broker detail` 38/38. **Entrato**:
>   `9d40a1df0`, `879cfc9d7`, `f24096f01` → dev `1565b6bbb`; CHANGELOG `a3662b3ef` con le mie due righe 🐛. T-U8 lo
>   riconcilia il coordinatore.

## Coda del mattino del 17/10: Y-16, Y-2, Y-13, Y-8 (dalle 05:30; HEAD `a3662b3ef`)

### Y-16 · la vista Candele salvata si carica per una dipendenza involontaria — opzione A approvata (05:4x)

> **Note implementazione**.
> - **Meccanismo**, verificato sul codice:
>   - l'`$effect` di `GrowthChart` (`:975-979`) legge solo `viewMode`, `pnlSubmode` e `pnlCandles`, e chiama
>     `onRequestPnlCandles()` in modo sincrono;
>   - nella Dashboard la callback è `pageBusy.join('dashboard-pnl-candles', loadPnlCandles)`, e `loadPnlCandles` legge
>     prima del primo `await` `canAsk`, `pnlCandles`, `pnlCandlesLoading`, `activeBrokerIds`, `dateRangeCtl` e
>     `targetCurrency`. Diventano tutte dipendenze dell'effetto del figlio;
>   - è il passaggio di `canAsk` a true, quando i broker diventano noti, a far ripartire la richiesta di una vista
>     Candele salvata;
>   - la pagina del broker non ha una guardia di prontezza.
> - **Trovato analizzando: Y-24**, nel backlog, per il developer insieme a Y-18. La stessa dipendenza nascosta da
>   `pnlCandlesLoading` riarma la richiesta dopo ogni errore, perché `requestReport` restituisce `null` invece di
>   lanciare: richieste senza limite finché il backend fallisce. `PositionsPanel` fa lo stesso per il contributo,
>   attraverso la sua prop dichiarata.
> - **Opzione A** (coordinatore, 05:4x): nessun cambio di comportamento.
>   - Un E2E diretto in `page-busy.spec.ts` (`test-author` `13eb06ea`): la richiesta dei broker è trattenuta, quindi
>     niente candele; al rilascio parte la richiesta delle candele.
>   - La prova di mutazione: un `untrack` attorno alla chiamata deve far diventare rosso il test.
>   - Due commenti. In `GrowthChart.svelte`, sopra l'effetto: la callback gira tracciata apposta (Y-16), il test che lo
>     fissa, Y-24. Nella Dashboard, sul JSDoc di `loadPnlCandles`: le letture della guardia sono dipendenze
>     dell'effetto, e vanno tenute prima del primo `await`.
> - **Opzione B, per il developer**: una prop esplicita `canRequestPnlCandles` più `untrack`. Toglie il ciclo, ma dopo
>   un errore, o in un passaggio di periodo da null a null, non si richiederebbe più niente. Serve una «chiave di
>   scope» e uno stato d'errore: è la decisione di Y-18.

### Y-13 · ✅ già chiuso da T

> `4a7ba1d7e` (16/10): `brokers-detail.spec.ts:392-419` usa `data-selected`. Aggiunta la ✅ nella mia sezione del backlog
> (via del coordinatore, 05:4x).

### Y-2 · il buco nella cascata settimanale — analisi e rosso (dalle 05:45)

> **Note implementazione**.
> - **Il difetto**, verificato:
>   - `buildBucketInfos` (`growthChartData.ts:225`) dà a ogni secchio settimanale o mensile, come `date`, l'ultimo
>     giorno di quel secchio presente in storia;
>   - `aggregateMetric` (`:380`) cerca il valore aggregato **per `bucket.date`**, mentre `aggregateLineSeries`
>     (`components/charts/timeSeriesAggregation.ts`) lo data sull'ultimo punto con un valore;
>   - quindi una linea che si ferma a metà settimana (valori da lunedì a mercoledì, poi null) non trova niente il
>     venerdì e fa un buco. La scala a gradini delle candele (`ladderLast`) tiene invece l'ultimo valore. Lo stesso
>     vale per il mese.
> - **La correzione prevista**: cercare per `bucketEnd`, il bordo di calendario che i due lati calcolano con la stessa
>   `mapDateToBucket`, cioè l'ultimo valore esistente nel secchio. Il punto resta su `bucket.date`; un secchio senza
>   valori resta un buco. Non è matematica finanziaria: è la scelta del punto che rappresenta il secchio, come già
>   fanno `aggregateLineSeries` e `ladderLast`.
> - Il rosso lo scrive `test-author` (`e6cd112c`) in `components/charts/chartCoreHelpers.test.ts`, nella sezione di
>   growthChartData (FE6a), che ha già le fixture `week` e `weekBucket`.
> - **I rossi di Y-2** (`test-author` `e6cd112c`, `chartCoreHelpers.test.ts` dopo `:4577`), tre casi:
>   - settimanale, la linea si ferma a metà settimana: `[null]` contro `[30]`;
>   - due settimane: `[null, null]` contro `[30, null]`. La seconda settimana resta un buco vero, quindi un valore non
>     viene portato nella settimana dopo;
>   - mensile, il secchio da `buildResolutionData`: `[null]` contro `[119]`, più un controllo che passa anche oggi;
>   - il controllo «valore l'ultimo giorno» c'era già (`:4577` e la cascata a `:3874`).
>   - **Lanciati** alle 05:45 (carico 47): **3 rossi su asserzioni**, 287 verdi (`files/logs/y2_red.log`).
> - **Correzione di Y-2 applicata** (`files/scripts/y2_apply.py`): `aggregateMetric` cerca per `bucketEnd`, con un
>   commento sul perché. Verdi: `chartCoreHelpers` 290/290, `GrowthChart` 166/166, `GrowthChart.tooltip` 6/6,
>   `growthLadderAxis` 138/138.
> - **Nota, fuori da Y-2**: `aggregateCandleMetric` (`:481-497`) cerca anch'esso per `bucket.date`. Ma la vista Candele
>   prende la scala a gradini (`getActiveAggregation`: `ladderActive` → `buildLadderData` → `ladderCandleMetric`), quindi
>   quella candela della cascata non si disegna mai. Nessun effetto visibile, niente voce nel backlog.
> - **L'E2E di Y-16** (`test-author` `13eb06ea`): `page-busy.spec.ts` ~l.867, «Dashboard loaded from scratch on a saved
>   P&L candles view: the candles are asked, and drawn, once the brokers are known…».
>   - Usa `saveCandlesView`, `hold(BROKERS_PATH, isBrokerList)`, `expectBusy` e le prove di montaggio (`aria-pressed`
>     di `growth-toggle-pnl` e `growth-pnl-submode-candles`).
>   - Con i broker trattenuti, nessun corpo con `include_pnl_candles`. Al rilascio parte la richiesta, con `broker_ids`
>     non vuoti, e le candele vengono disegnate (`candleBodies` attraverso `[data-chart-ready]`).
>   - Con la mutazione `untrack` si aspetta un timeout con un messaggio proprio.
> - **Prove leggere su Y-16 e Y-2** (05:5x, carico 36): svelte-check 0/0, Prettier pulito sui 5 file,
>   `theme-roles --check` pulito, `git diff --check` pulito.
> - **Slot chiesto**: `files/scripts/y16_e2e.sh`.
>   - Prima la mutazione su `GrowthChart.svelte` (provata su una copia: diventa `untrack(() => onRequestPnlCandles?.())`
>     più l'import), e `page-busy` che si aspetta rossa.
>   - Poi il ripristino controllato con l'hash, con una trap anche in caso d'errore.
>   - Infine `page-busy` e `dashboard` sul codice vero.
> - **E2E di Y-16 e Y-2** (slot 1, 05:50–06:07; `files/scripts/y16_e2e.sh`). La guardia sul carico a 5 minuti sotto 50
>   l'ho aggiunta allo script prima di lanciarlo: il coordinatore la dava per già presente, ma non c'era. Partenza dopo
>   150 s, con il carico a 47.
>   - **Mutazione** (`untrack(() => onRequestPnlCandles?.())` più l'import): `page-busy` 15 verdi e **2 rossi, per la
>     ragione giusta**:
>     - `:867`, il test di Y-16, con il suo messaggio: «Y-16: the brokers are known, and the candles the chart asked
>       before them are never asked — the refused ask was not re-armed when the brokers landed»;
>     - `:774`, N55, sulla sua precondizione: «the saved candles view never drew its candles».
>   - **Ripristino**: l'hash è uguale (`54d25178…`) e nel codice non resta nessun `untrack` (`grep` dà 0).
>   - **Codice vero**: `front-portfolio page-busy` **17/17** e `front-portfolio dashboard` **27/27**.
>   - Porta 6189 libera. Log in `files/logs/y16_e2e_*.log`.
> - **Backlog**: Y-16 ✅ (opzione A; la correzione vera è Y-24) e Y-2 ✅.

### Y13 · lista degli spostamenti FE9–FE11 (06:10–06:20, sola lettura; HEAD `abf8391fb`)

> **Note implementazione**. Script `files/y13_movelist.py` → `files/y13_movelist.md` (cartella di sessione), mandata al
> coordinatore. Rispetto all'analisi del 16/10, FE8b di W ha già chiuso 3 inversioni e 12 archi.
> - **FE9, 7 file da spostare**: `utils/core/positionKey.ts` → `features/dashboard/` (Y); `utils/files/pdfPreviewState.ts`,
>   `pdfViewerAssets.ts` e `utils/urlFilters.ts` → `features/files/`; `utils/assetGrouping.ts`, `assetIdentifiers.ts`,
>   `utils/core/requestConcurrency.ts` e `utils/currency/fxConversionHelper.ts` → `features/transactions/` (W). Nessuno è
>   in `themeRoles.baseline.tsv`. Tre righe di `_frontend_utility.py` (121–123) e la SKILL `design-system` (`:220`) sono
>   del programma colori.
> - **Restano**: `utils/url/queryParams.ts` e `utils/brim/pluginKind.ts`, condivisi con `utils/broker` e `utils/url`.
> - **`PasswordStrength`**: (a) spostamento puro in `features/auth/`, oppure (b) regole come prop nei 5 chiamanti di A e B.
>   Proposta (a): è la domanda **Y13-4**.
> - **Inversioni**: 4 (`chartUtils` → `LineChart.svelte`, `chartSettingsStore` → `calendarReturnWindow.ts`, `urlFilters` →
>   `table/types.ts`, `assetTypes` → `treeSelect.ts`), più Y-7. **Archi componenti → feature**: 30 (`components/assets` 19
>   e `fx` 1, che chiudono FE4 e FE5; `layout` 6, il guscio; `ui` 4, con `AssetPickerModal` → `FileGrid`, composizione
>   accettabile). **FE10**: nessuno store di un dominio solo. **FE11**: Modal 45, Panel 23, Section 19, Dialog 10, Popover 1.
> - **Coordinatore (06:2x)**: piano parcheggiato fino alla risposta del developer a Y13-1 (dopo il tag); Y13-4 è nella sua
>   lista con la proposta (a).
>
> **Fuori pista**: la prima scansione degli store cercava `$lib/lib/stores/…` e non trovava niente; rifatta corretta
> (`connectionSecurityStore` lo usa solo il guscio, `TimeSeriesStore` solo `utils`).

### Y-8 · `updateArrowRotations()` e `getOption()` a ogni passo dello zoom — analisi e scelta (06:20)

> **Via del coordinatore** (06:1x), con la condizione vincolante del programma colori:
> - `updateArrowRotations()` riscrive tutto `option.series` letto da `getOption()`, colori compresi. Una cache fra due
>   passi dello zoom va invalidata a ogni `setOption` che ricostruisce l'opzione, anche su `onThemeClassChange` e
>   `onChartColorsChange`; in alternativa, dalla cache non si riscrive niente che porti colore;
> - test unitario obbligatorio: costruzione in chiaro, ricostruzione in scuro, un passo di zoom → il payload porta i
>   colori scuri, o nessun colore. Nessuna classe di colore cambiata; `theme-roles --check` pulito; prima il rosso.
>
> **Stato reale** (verificato su `abf8391fb`):
> - `lineChartHelpers.ts:590` `updateArrowRotations(chart)`: `getOption()` (copia profonda di tutta l'opzione), poi per ogni
>   marcatore `arrow` di un `markPoint` due `convertToPixel`, poi `setOption({series: option.series}, false)`: riscrive
>   tutte le serie, dati e colori compresi. Senza frecce non riscrive niente, ma la copia la fa comunque.
> - Lo chiamano a ogni passo i tre gestori di `dataZoom`: `LineChart.svelte:401`, `CandlestickChart.svelte:292`,
>   `PriceChartFull.svelte:613` (quest'ultimo sotto la nota «do NOT read `getOption()` here», che contraddice).
> - Le frecce vengono solo dai segnali sovrapposti (`markerStart`/`markerEnd`: lo stile scelto dall'utente in
>   `SignalStyleEditor`, e la freccia finale di `MeasureSignal`), costruite in `LineChart.svelte:557` e in
>   `chartCoreHelpers.ts:359` (`buildOverlaySignalSeries`, per `CandlestickChart` e `PriceChartFull`). Ogni marcatore porta
>   `itemStyle.color`. Gli eventi di split (`EVENT_SYMBOLS.SPLIT = 'arrow'`) sono serie scatter: non c'entrano.
> - I tre grafici hanno già un rinvio a gesto fermo: `scheduleZoomedAxisLabels` (`ZOOM_LABEL_SETTLE_MS`, 120 ms) in
>   `LineChart` e `CandlestickChart`, `scheduleResolutionRecompute` (200 ms) in `PriceChartFull`. Gli hook del tema
>   (`onThemeClassChange`, `onChartColorsChange`) chiamano `renderChart()`: ricostruzione completa, poi
>   `updateArrowRotations` alla fine.
>
> **Scelta: rinviare la rotazione al gesto fermo**, come le etichette (la seconda strada del backlog).
> - Il gestore di `dataZoom` non chiama più `updateArrowRotations`; la chiama il timer che già esiste: dopo
>   `applyZoomedAxisLabels()` in `LineChart` e `CandlestickChart`; nel ramo «risoluzione tenuta» di
>   `scheduleResolutionRecompute` in `PriceChartFull` (una risoluzione nuova ridisegna, e `renderChart` già le ruota).
> - **Nessuna cache**: `getOption()` si legge al momento, una volta per gesto. Quindi il payload porta sempre i colori
>   dell'opzione corrente, scuri dopo una ricostruzione in scuro: la condizione del colore vale per costruzione.
> - **Perché non la rotazione dal vivo con una cache**: toglierebbe la copia, ma non la riscrittura. In ECharts ogni
>   `setOption` con `series` rifonde tutte le serie (`mergeOption`, poi `getInitialData`) e ridisegna, e i marcatori
>   (array) si possono riscrivere solo interi, colore compreso. Il costo per passo resterebbe circa la metà, e in più ci
>   sarebbe una cache da invalidare.
> - **Il prezzo**: durante il gesto la freccia tiene l'angolo di prima, e si riallinea 120–200 ms dopo l'ultimo passo,
>   come le etichette. Le frecce sono piccole (8 px circa) e solo sui segnali che le hanno.
> - **Fuori da Y-8**: il ridimensionamento chiama ancora `updateArrowRotations` subito (`ResizeObserver`): non è per passo
>   di zoom, resta com'è.
>
> **Passi**:
> 1. `test-author`: i rossi (nessun `getOption()` e nessuna riscrittura delle serie per passo; le frecce riallineate una
>    volta a gesto fermo) per i tre grafici, in `LineChart.test.ts` e `PriceChartFull.test.ts` (già registrati in
>    `component-unit`); il test del colore chiaro → scuro → un passo, che oggi è verde per costruzione.
> 2. La correzione nei tre componenti e nel JSDoc di `updateArrowRotations`.
> 3. La prova del morso sul test del colore: una variante che tiene in cache il primo `getOption()` deve farlo diventare
>    rosso; ripristino controllato con l'hash.
> 4. Prove leggere: i file Vitest dei grafici, svelte-check, Prettier, `theme-roles --check`, `git diff --check`.
> 5. Documentazione (`developer/frontend/components/charts.md`, punto «Zoom», con `docs-writer`), devWiki
>    (`concepts/echarts-chart-gotchas`), backlog; poi lo slot E2E e il checkpoint.
>
> **Passo 1 ✅, i rossi** (`test-author` `dd7aff62`, 06:25–06:52; solo `LineChart.test.ts` e `PriceChartFull.test.ts`,
> già registrati in `component-unit`):
> - **Il registratore di ECharts**, nei due file, ora tiene l'opzione come ECharts: un `setOption` fonde oggetto per
>   oggetto e componente per indice (`notMerge` sostituisce tutto); `getOption()` risponde una copia profonda, ogni
>   componente come lista, e conta le chiamate (`getOptionCount`); `convertToPixel` mappa `[categoria, valore]` su una
>   griglia fissa (10 px a categoria, y = 400 − valore), così una freccia viene ruotata e riscritta come su uno schermo;
>   `resize` conta (`resizeCount`). In `PriceChartFull.test.ts` anche `on`/`emit` come nel file di `LineChart`.
> - **Una barriera nuova**: il primo disegno riallinea le frecce altre due volte da solo (`scheduleFirstRenderStabilityFix`:
>   subito, e dopo due frame fermi); i casi aspettano `resizeCount ≥ 2` prima dei timer finti.
> - **Tre rossi**, uno per grafico (`LineChart`, `PriceChartFull`, `CandlestickChart`): cinque passi di zoom di fila →
>   `{getOptionReads: 5, seriesWriteBacks: 5}` invece di `{0, 0}`; al gesto fermo nessun riallineamento (`[]` invece di
>   una riscrittura con le due frecce ruotate); letture totali 5 (6 per `PriceChartFull`) invece di ≤ 1 (≤ 2: l'intervallo
>   assestato, letto apposta, più le frecce). Il caso di `PriceChartFull` prova anche che il gesto si ferma nel ramo
>   «risoluzione tenuta»: nessun ridisegno, etichette ridistanziate, asse ancora giornaliero.
> - **Quattro guardie del colore, verdi oggi per costruzione**: `LineChart` in chiaro → scuro (`lineColor`/`darkLineColor`)
>   e su `notifyChartColorsChange()` con un ruolo cambiato (`setRoleReader`, la linea di base); `PriceChartFull` (linea del
>   prezzo, `colorByBaseline: false`) e `CandlestickChart` (guadagno e perdita di `CHART_GAIN_LOSS.price`) in chiaro →
>   scuro. Dopo un passo di zoom, ogni riscrittura delle serie porta i colori nuovi, mai i vecchi.
> - **Le prove di `test-author`**, su copie e poi ripristinate con l'hash: la correzione emulata porta i tre rossi al
>   verde; il mutante con la cache del primo `getOption()` porta le quattro guardie al rosso.
> - Esiti: `LineChart` 1 rosso, 7 verdi; `PriceChartFull` 2 rossi, 38 verdi (`files/logs/y8_red_*.log`). Prettier pulito.
> - **Osservazioni di `test-author`, fuori da Y-8**: il primo disegno fa 3 copie di `getOption()` e 3 riscritture in circa
>   50 ms; `updateArrowRotations` riscrive anche quando nessun angolo cambia; il ridimensionamento riallinea a ogni
>   callback; `CandlestickChart` riallinea dopo il ripristino dello zoom, `LineChart` prima. Il verde scuro del prezzo
>   coincide con il verde del guadagno (`#4ade80`). I costi del ridimensionamento e della riscrittura senza angoli
>   cambiati vanno in **Y-25** (backlog, minimo); il resto sono costi di una volta, non per passo.
>
> **Passo 2 ✅, la correzione** (06:52, `files/scripts/y8_apply.py`, 9 sostituzioni esatte, ognuna trovata una volta; 4 file,
> +23 −11):
> - `LineChart.svelte` e `CandlestickChart.svelte`: il gestore di `dataZoom` chiama solo `scheduleZoomedAxisLabels(event)`;
>   il timer da 120 ms, dopo `applyZoomedAxisLabels()`, chiama `updateArrowRotations` (nel callback del timer, non dentro
>   `applyZoomedAxisLabels`, i cui ritorni anticipati in modo compatto o senza finestra salterebbero le frecce: avviso di
>   `test-author`). Il JSDoc delle due variabili del timer dice che ora riallinea anche le frecce.
> - `PriceChartFull.svelte`: il gestore chiama solo `scheduleResolutionRecompute()`, e la nota «do NOT read getOption()
>   here» ora nomina anche `updateArrowRotations()`; nel ramo «risoluzione tenuta» del rinvio, dopo
>   `applyZoomedAxisLabels()`, `updateArrowRotations(chartInstance)`. Una risoluzione nuova ridisegna, e `renderChart()`
>   riallinea da sé.
> - `lineChartHelpers.ts`: il JSDoc di `updateArrowRotations` dice quando va chiamata (a gesto fermo, mai per passo) e che
>   legge l'opzione al momento e non tiene niente fra due chiamate.
> - Nessuna classe di colore toccata. Il ridimensionamento e il primo disegno restano come prima.
>
> **Passo 3 ✅, la prova del morso** (06:57, `files/scripts/y8_bite.sh`, sul codice corretto): il mutante che tiene in cache
> il primo `getOption()` di ogni grafico porta **le 4 guardie del colore al rosso**, con i loro messaggi («Y-8 guard: a
> series write-back after the zoom brought the light price line back over the dark rebuild…», e così per la linea di
> base, `PriceChartFull` e le candele). Ripristino dalla copia: hash uguale (`08156eba9ac4`), nessun `__y8Cache` nel file.
>
> **Passo 4 ✅, prove leggere** (06:53–06:55, carico 24, `files/scripts/y8_light.sh`): `LineChart` 8/8, `PriceChartFull`
> 40/40, `lineChartHelpers` 42, `lineChartHelpers.sessionGaps` 9, `chartCoreHelpers` 290 (i pin di 47-1 reggono: il
> timer chiama ancora `applyZoomedAxisLabels()` senza graffe di mezzo, e il codice delle funzioni dello zoom, tolti i
> commenti, non nomina `getOption(`), `CandlestickChart.tooltipEscape` 7, `PriceChartFull.tooltipEscape` 17,
> `echartsZoomPan` 24, `chartFlagFont` 16; svelte-check 0/0; Prettier pulito sui 6 file; `theme-roles --check` pulito;
> `git diff --check` pulito.
>
> **Passo 5, in corso**: devWiki (`concepts/echarts-chart-gotchas`: una riga nella tabella, quattro nei file sorgente; la
> riga dell'indice; una voce del log; `check_source_paths.py`: 7 mancanti, 12 occorrenze, nessuna della mia pagina, tutte
> di altre pagine), backlog Y-8 ✅, `docs-writer` su `charts.md`. Slot 2 per l'E2E (coordinatore, 06:58), dopo
> l'avanzamento rapido del mio HEAD a dev `952c68cd5` (38 commit, nessuna sovrapposizione con i miei file).
>
> **Passo 5 ✅, documentazione, devWiki, backlog ed E2E** (06:58–07:10):
> - **E2E** (slot 2, `files/scripts/y8_e2e.sh`, HEAD `952c68cd5` più i miei file; carico a 5 minuti 22): `front-asset
>   asset-detail` **35/35** (2,7 minuti), `front-fx fx-detail` **17/17** (1,0 minuto). Porta 6189 libera alle 07:08.
> - **`docs-writer`** (`028c525a`): `developer/frontend/components/charts.md`, un punto nuovo **«Arrow markers»** dopo
>   «Zoom», nella sezione «Responsive Date Axis»: le frecce si riallineano nell'assestamento che ridistanzia le etichette,
>   mai a ogni passo; durante il gesto tengono l'angolo; l'opzione si legge al momento, quindi la riscrittura non riporta i
>   colori di prima di un cambio di tema o di colore. La pagina è solo in inglese e non ha marca di data: niente
>   `translate-stamp`.
> - **`mkdocs build` (strict) e `check-links`** (`files/scripts/y8_docs_check.sh`, carico 32): build rc 0, 0 righe WARNING,
>   50,8 s; `check-links` 97 link validi. Nessun file tracciato cambiato dal build.
>
> **⚠️ Fuori pista: un buco aperto dalla correzione, trovato da `docs-writer`** (Y-8b, nello stesso lotto):
> - `LineChart.renderChart()` riallineava le frecce **prima** di ripristinare lo zoom salvato (`dispatchAction` `dataZoom`),
>   subito dopo il `setOption(option, true)` che azzera lo zoom: frecce orientate sull'asse intero. Prima di Y-8 l'evento del
>   ripristino le correggeva subito nel gestore. Ora il gestore pianifica solo l'assestamento, quindi dopo ogni ridisegno
>   completo di un `LineChart` zoomato con frecce restavano storte per circa 120 ms. ECharts 6 emette l'evento anche per un
>   `dispatchAction` da codice (`echarts.js:1479`, salvo `silent`), quindi si correggevano dopo l'assestamento.
> - `CandlestickChart` ripristina già prima e riallinea dopo (`:624-636`); `PriceChartFull` scrive la finestra nell'opzione.
> - **Correzione**: lo stesso ordine in `LineChart` (`files/scripts/y8b_apply.py`, a secco pulito). Tocca solo il `LineChart` a
>   piena misura: i grafici del rischio (`UnderwaterChart`, `L4Simulation`, `RiskAnalysisPanel`) e l'anteprima di
>   `ChartSettingsModal`; le card compatte non ripristinano lo zoom.
> - **Coordinatore** (07:1x): via allo scambio, prima il rosso; slot 2 per `front-portfolio risk` quando rosso e correzione
>   sono pronti, con la guardia sul carico a 5 minuti; poi CHECKPOINT READY.
> - Il rosso lo scrive `test-author` (`dd7aff62`) in `LineChart.test.ts`: un ridisegno completo di un grafico zoomato → la
>   prima riscrittura porta le frecce orientate sulla finestra ripristinata, non sull'asse intero.
>
> **Y-8b ✅, rosso, scambio e prove** (07:10–07:30):
> - **Il rosso** (`test-author` `dd7aff62`, solo `LineChart.test.ts`, 07:10–07:22):
>   - il registratore ora ha uno zoom vero: `dispatchAction` registra ogni azione (`dispatchedActions`, con `atCall`); un
>     `dataZoom` con `start`/`end` numerici aggiorna `dataZoom[0]` dell'opzione tenuta (e toglie `startValue`/`endValue`,
>     come `setRawRange`) ed emette `dataZoom` subito, con la forma di ECharts 6 per un'azione non a lotti, salvo
>     `silent`; `userZoom({start, end})` simula il gesto dell'utente (modello aggiornato, poi evento); `convertToPixel` mappa
>     x sulla finestra a schermo (`gridPixel`, 800 px sulle categorie visibili, contate come `visiblePointCountFromZoom`);
>   - il caso: montaggio con le frecce di TREND, zoom dell'utente a `{70, 100}`, assestamento; poi un ridisegno completo
>     (`rerender({showGridLines: false})`) con i timer finti, e un `advanceTimersByTimeAsync(0)` che lascia girare le
>     microtask senza far scattare l'assestamento. Barriere: un disegno completo nuovo, un ripristino `{70, 100}` dopo di
>     esso, una riscrittura delle serie, l'assestamento ancora pendente;
>   - **rosso** (`files/logs/y8b_red_LineChart.log`, 1 rosso e 8 verdi): «Y-8: a full redraw of a zoomed chart aimed its
>     arrows on the whole axis, before restoring the zoom — they point wrong until the settle»; freccia iniziale 102,85°
>     invece di 93,97°, finale −77,15° invece di −86,03°; una precondizione vuole i due angoli diversi di oltre 1°.
> - **Lo scambio** (`files/scripts/y8b_apply.py --apply`, 07:23): in `LineChart.renderChart()` prima il ripristino dello zoom
>   salvato, poi `updateArrowRotations` e il blocco della stabilità, con un commento sul perché. È l'ordine di
>   `CandlestickChart`.
> - **Prove leggere** (`files/scripts/y8b_light.sh`, 07:23–07:28, carico 35): `LineChart` **9/9**, `PriceChartFull` 40/40,
>   `lineChartHelpers` 42, `sessionGaps` 9, `chartCoreHelpers` 290 (il pin dell'ordine del ridisegno di 47-1 regge: il
>   ripristino viene ancora dopo `setOption(option, true)`), i due `tooltipEscape` 7 e 17, `echartsZoomPan` 24,
>   `chartFlagFont` 16; svelte-check 0/0; Prettier pulito; `theme-roles --check` pulito; `git diff --check` pulito.
> - **Prova del morso rifatta sul codice finale** (`files/scripts/y8b_bite.sh`): il mutante con la cache porta di nuovo le 4
>   guardie del colore al rosso; ripristino con hash uguale (`08156eba9ac4`).
> - **Osservazione di `test-author`, nessuna voce**: il ripristino non è `silent`, quindi 120 ms dopo ogni ridisegno di un
>   grafico zoomato l'assestamento riallinea di nuovo (una copia e una riscrittura in più, ridondanti dopo lo scambio). Lo
>   stesso in `CandlestickChart`. Costo una volta per ridisegno, non per passo: annotato in **Y-25**, con il
>   ridimensionamento.
> - **E2E** (slot 2, `files/scripts/y8b_e2e.sh`, 07:30–07:37, carico a 5 minuti 47 alla partenza, poi fino a 60 per il
>   build del frontend e le altre sessioni): `front-portfolio risk` **38/38** (2,3 minuti), i grafici del rischio che usano il
>   `LineChart` a piena misura. Porta 6189 libera alle 07:37.
> - **Backlog**: Y-8 ✅ con Y-8b; **Y-25** nuova (minimo): il ridimensionamento riallinea a ogni callback, la riscrittura
>   parte anche senza angoli cambiati, il riallineamento in più dopo ogni ridisegno zoomato.
> - **devWiki**: la riga di `concepts/echarts-chart-gotchas` dice anche l'ordine «ripristino, poi riallineamento»; voce del
>   log aggiornata.
>
> ### Y-8 — checkpoint 🧊 FROZEN (07:4x)
>
> Handoff al coordinatore con le liste da committare. Nessun server, porta 6189 libera, `git diff --check` pulito.

## Dopo Y-8: J-44 (annullata, poi revisione) e Y-25 (dalle 07:40; HEAD `039af67bb`)

### J-44 · revisione a posteriori del commit di J ✅ (07:45–07:55)

> **Note implementazione**. Il coordinatore mi aveva passato J-44 (07:40), poi l'ha annullata: J l'aveva già fatta, nel
> suo checkpoint F5 (messaggi incrociati). Nessun file toccato da me. Revisione in sola lettura di `824b27437` («fix(charts):
> no tooltip Δ% from a zero start», in dev `b6b615c3d`), via `git show`:
> - ✅ `changePct` esportato da `MeasureSignal.ts` (file dichiarato dal gate della matematica finanziaria): la regola ha una
>   copia sola. `buildDeltaHtml` la usa; `—` (U+2014, lo stesso glyph del righello) solo nella vista assoluta; colore dal
>   segno di Δabs e vista percentuale invariati, come dichiarato. Nessun ciclo: `MeasureSignal.ts` nomina
>   `priceChartHelpers` solo in un commento. Test: rossi con ragioni, il vecchio pin ripinnato, `changePct` provato con un
>   import dinamico. `financial_math.md` regola 6 aggiornata; nessuna pagina utente descrive il Δ del tooltip.
> - Note, non correzioni: il `—` del tooltip prende il colore di Δabs (nel righello è grigio: cambiarlo è dei colori);
>   `priceChartHelpers` → `MeasureSignal` è un arco in più dell'inversione D-Y15/Y-7, da sciogliere in FE9.
> - **Fuori dal perimetro di J-44, lo stesso numero sbagliato** (regola 10): la vista percentuale. `toDisplaySeries`
>   (`priceChartHelpers.ts:369`) rende la serie intatta quando il primo valore è 0, quindi linea e Δ del tooltip mostrano
>   valori assoluti come percentuali. Altre copie del ribasamento, tre comportamenti su una base nulla:
>   `computeGhostSeries` (`:469`, tutto 0 %), `candlestickChartHelpers.toPercent` (`:35`) e `backendRenderer.transformValue`
>   (`:37`, valore grezzo), `lotWacPriceChartHelpers.toPercentSeries` (`:130`, ribasa sul primo valore non nullo).
>   Mandato al coordinatore; diventa **Y-26** (aperta, per il developer) al prossimo checkpoint.

### Y-25 · i costi di `updateArrowRotations` fuori dallo zoom — analisi e scelta (07:55)

> **Via del coordinatore** (07:4x): «Y-25 if it's cheap».
>
> **Stato reale** (HEAD `039af67bb`; i 9 commit nuovi di dev non toccano questi file):
> - ogni chiamata copia tutta l'opzione con `getOption()`, anche su un grafico **senza frecce** (quasi tutti: le frecce
>   vengono solo dai segnali con `markerStart`/`markerEnd: 'arrow'` e dalla freccia finale del righello);
> - riscrive tutte le serie appena trova una freccia, anche se nessun angolo è cambiato;
> - i tre `ResizeObserver` (`LineChart.resizeChartOnly`, `CandlestickChart`, `PriceChartFull`) la chiamano a ogni
>   callback, cioè a ogni frame di un trascinamento della finestra o di una transizione di larghezza;
> - il primo disegno la chiama tre volte (`renderChart` e i due passi di `scheduleFirstRenderStabilityFix`), e ogni
>   ridisegno di un grafico zoomato una volta in più, 120 ms dopo (il ripristino non è `silent`).
> - Ogni componente ha un solo disegno completo (`setOption(option, true)`); gli altri `setOption` toccano solo le
>   etichette dell'asse. Nessun altro chiamante di `updateArrowRotations`.
>
> **Scelta, tre parti piccole**:
> - **(a)** la riscrittura parte solo se una freccia gira di più di 0,01° (sotto, la freccia è identica a vista);
> - **(b)** i tre `ResizeObserver` non riallineano più a ogni callback: `LineChart` e `CandlestickChart` riarmano
>   l'assestamento che già c'è (`scheduleZoomedAxisLabels(lastZoomEvent)`: etichette e frecce 120 ms dopo l'ultima
>   callback); `PriceChartFull` lascia fare al suo rinvio da 200 ms, che già riallinea nel ramo «risoluzione tenuta» (una
>   risoluzione nuova ridisegna);
> - **(d)** un grafico il cui ultimo disegno completo non ha frecce non legge niente: `noteArrowMarkers(chart, option)`,
>   chiamata subito dopo ogni `setOption(option, true)`, annota in un `WeakSet` i grafici senza frecce, e
>   `updateArrowRotations` esce prima di `getOption()`. Un grafico mai annotato si comporta come oggi.
> - Non faccio il ripristino `silent` dello zoom: altri ascoltatori potrebbero contare sull'evento; con (a) e (d) costa
>   una copia sola, e nessuna sui grafici senza frecce.
>
> **Passi**: rossi (`test-author`); correzione; prove leggere; prova del morso su (d) (un disegno che non annota → la
> guardia «un grafico che ottiene frecce le riallinea» resta verde, quello senza frecce torna a leggere); E2E dei grafici;
> backlog (Y-25 ✅, Y-26 nuova), devWiki, checkpoint.
>
> **Passo 1 ✅, i rossi** (`test-author` `dd7aff62`, 07:57–08:07; solo i quattro file di test permessi, già registrati):
> - **16 rossi**, ognuno per la ragione voluta; tutti i casi di prima verdi (42, 9, 40, 290):
>   - unità (`__tests__/lineChartHelpers.test.ts`, 4 rossi e 45 verdi): (a) una seconda chiamata senza niente di mosso
>     riscrive (`expected 2 to be 1`); una freccia a 0,005° dal suo angolo viene riscritta; (d) `noteArrowMarkers` manca
>     (barriera dell'import dinamico, due casi). Guardie: una freccia a 0,02° si riallinea; una che gira fra altre ferme
>     dà una riscrittura con tutte le serie; un grafico mai annotato legge come prima;
>   - `LineChart.test.ts` (2 rossi e 9 verdi): (d) un grafico senza frecce legge `getOption()` all'assestamento (`1` invece
>     di `0`); (b) cinque callback del ridimensionamento → `{5 letture, 5 riscritture}` invece di `{0, 0}`, nessun
>     riallineamento all'assestamento, letture totali 5 invece di ≤ 1;
>   - `PriceChartFull.test.ts` (4 rossi e 40 verdi): (d) per `PriceChartFull` (2 letture invece di ≤ 1) e per le candele;
>     (b) per i due grafici;
>   - `chartCoreHelpers.test.ts` (6 rossi e 293 verdi): i pin di (b) per i tre grafici e di (d) per i tre (`noteArrowMarkers`
>     subito dopo `setOption(option, true)`, importato da `./lineChartHelpers`); una premessa verde: il disegno completo è
>     l'unico `setOption` con le serie.
> - **Il registratore**: `PriceChartFull.test.ts` ha ora lo zoom vero di `LineChart.test.ts` (`gridPixel`, `userZoom`,
>   `dispatchAction` registrato ed emesso, `takeWindow`); la larghezza del grafico è una manopola (`plot.width`), così un
>   ridimensionamento cambia gli angoli. I casi di Y-8 e le guardie del colore usano zoom veri: con (a), uno zoom che non
>   muove niente non porterebbe nessuna riscrittura. I casi di ridimensionamento usano un `ResizeObserver` locale che tiene
>   la sua callback, tolto in `afterEach`; lo stub globale resta inerte.
> - **La tolleranza**: il bordo esatto non è provabile in virgola mobile (90,01 − 90 = 0,010000000000005), quindi i test
>   guardano a metà (0,005°) e al doppio (0,02°). La freccia dentro la tolleranza non viene toccata, nemmeno nella copia.
>
> **Passo 2 ✅, la correzione** (08:08, `files/scripts/y25_apply.py --apply`, 12 sostituzioni esatte; 4 file, +46 −8):
> - `lineChartHelpers.ts`: `ARROW_ROTATE_EPSILON_DEG = 0.01`; `noteArrowMarkers(chart, option)` con un `WeakSet` dei grafici
>   senza frecce; `updateArrowRotations` esce prima di `getOption()` per quei grafici e salta una freccia che non gira; JSDoc.
> - I tre componenti: `noteArrowMarkers(chartInstance, option)` subito dopo il disegno completo; nei `ResizeObserver`,
>   `LineChart` (`resizeChartOnly`) e `CandlestickChart` riarmano l'assestamento (`scheduleZoomedAxisLabels(lastZoomEvent)`),
>   `PriceChartFull` lascia fare a `scheduleResolutionRecompute()`.
>
> **Passo 3 ✅, prove leggere** (`files/scripts/y25_light.sh`, 08:08–08:19; il carico è salito fino a 59 e lo script ha
> aspettato): `LineChart` 11, `PriceChartFull` 44, `lineChartHelpers` 49, `sessionGaps` 9, `chartCoreHelpers` 299, i due
> `tooltipEscape` 7 e 17, `echartsZoomPan` 24, `chartFlagFont` 16, `moneyRenderSites` 6, `themeModeReads` 24, `MeasurePanel`
> 23 (529, tutti verdi); svelte-check 0/0; Prettier pulito sugli 8 file; `theme-roles --check` pulito; `git diff --check`
> pulito.
>
> **Passo 4 ✅, la prova del morso sul verso pericoloso di (d)** (`files/scripts/y25_bite.sh`): un `noteArrowMarkers` che
> archivia ogni grafico come senza frecce lascerebbe le frecce vere dritte. Con quel mutante vanno rossi tutti i casi che
> disegnano frecce: `LineChart` 5 (passo e assestamento, ridisegno zoomato, le due guardie del colore, ridimensionamento),
> `PriceChartFull` 6 (passo e assestamento, guardie del colore e ridimensionamento, per i due grafici), la guardia
> d'unità «un grafico che ottiene frecce viene riallineato». Ripristino con hash uguale (`6a53971c3280`).
>
> **Slot E2E chiesto** (08:2x, `files/scripts/y25_e2e.sh`: `asset-detail`, `asset-mobile-layout`, `asset-list`, `fx-detail`,
> `risk`); il coordinatore lo mette in coda dopo F, A, MF e B-31. **`docs-writer`** (`adeb1b4e`) riscrive il punto «Arrow
> markers» di `charts.md`. **Backlog**: Y-25 ✅, Y-26 nuova, e la ✅ di Y-12 che mancava (`6ac6ead12`, 16/10).

### Y-3 e Y-4 · via del coordinatore, mentre Y-25 aspetta lo slot (08:3x)

> **Y-3, la misura** (sola lettura, `files/scripts/y3_measure.py`, log `files/logs/y3_measure.log`): una copia in Python di
> `scanLine`/`scan` del gate `moneyRenderSites.test.ts`, con le sue espressioni di oggi, girata due volte.
> - 819 file; **8 colpi oggi** (forma A 4, B 4) e **gli stessi 8** con `\bt\(` in `I18N_CALL`: nessuno sparisce, nessuno
>   compare, quindi nessuna voce del registro marcisce.
> - Un solo letterale ha un `t(` accanto a un segno di valuta: `growthChartTooltip.ts:166`
>   (`${t('dashboard.totalPnl')}`), che resta un colpo grazie a `pnlColor`. Nessun `t(` porta valori con importi.
> - **Rumore zero**: la modifica è solo di test (la forma, il commento e un controllo sintetico attraverso `scanLine`).
>
> **Y-4**: da G-9 (`c635da129`, entrato con `1470bd693`) `selectIndicatorFromTree` della galleria apre il menu con ↓ sul
> pulsante, aspetta il fuoco della casella di ricerca e un `aria-activedescendant`, apre una famiglia chiusa con → dopo
> averla raggiunta (`walkIndicatorTreeTo`), arriva all'opzione e conferma con Invio. I commenti di
> `SignalTreeSelect.test.ts` (`:16-17`, `:306-310`) descrivono ancora i clic. Solo il testo dei commenti; lo spostamento di
> FE2 resta congelato.
>
> Le due modifiche le fa `test-author` (file di test), in due file diversi.
>
> **Y-25, documentazione ✅** (`docs-writer` `adeb1b4e`, 08:2x–08:30): il punto «Arrow markers» di `charts.md` riscritto (13
> righe): le frecce si riallineano quando un gesto o un ridimensionamento si ferma, nell'assestamento delle etichette che
> un evento `dataZoom` o una callback del `ResizeObserver` riarmano; un disegno completo le riallinea subito, dopo il
> ripristino dello zoom; la riscrittura solo oltre 0,01°; `noteArrowMarkers` e i grafici senza frecce; i colori; i test.
> - **Due correzioni al mio brief, giuste**: anche un pan può girare una freccia (lo zoom filtra i punti,
>   `filterMode: 'filter'`, e l'asse Auto segue i dati visibili), quindi non l'ho più dato come esempio di «niente
>   riscrittura»; il passo della stabilità del primo disegno riallinea anch'esso subito, quindi niente «solo».
> - `mkdocs build` (strict) rc 0, 0 righe WARNING, 47,6 s; `check-links` 97 validi (`files/scripts/y25_docs_check.sh`,
>   carico 39 dopo 90 s di attesa).
>
> **Y-3 ✅ e Y-4 ✅** (`test-author` `331dfce4`, 08:3x–08:50):
> - **Y-3** (`moneyRenderSites.test.ts`): `I18N_CALL = /\$_\(|\bt\(|label\(/`. `\bt\(` prende il posto di `\$t\(` invece di
>   affiancarlo: copre anche `$t(` (`$` non è un carattere di parola), e un'alternativa morta sarebbe proprio quella contro cui
>   mette in guardia la nota di `SAFE_CALL`. Commento sulla forma: le chiavi sono parole e non numeri, il `\b` tiene fuori
>   `format(`, `fmt(`, `parseInt(`, `split(`, e il punto cieco condiviso con `$_(` (un importo nei `values` di una traduzione).
>   Caso nuovo con tre righe sintetiche attraverso `scanLine`: una chiave `t('…totalPnl')` accanto alla valuta non è un colpo;
>   la stessa con `formatFixed(amount, 2)` sì; `fmt(`/`format(` accanto alla valuta sì. **Il rosso**, valutato con node sul
>   `scanLine` di prima (il brief diceva una corsa sola, alla fine): la prima asserzione rossa con la forma di oggi; il mutante
>   senza `\b` rende rossa la terza. Su `src`: gli stessi 8 colpi con ogni forma. Corsa: **7/7**.
> - **Y-4** (`SignalTreeSelect.test.ts`, solo commenti): il docblock (`:16-25`) dice come sceglie oggi la galleria (↓ apre
>   sulla casella di ricerca col fuoco e una riga evidenziata, ↓/↑ camminano, → apre la famiglia chiusa raggiunta, Invio
>   sceglie e chiude) e nomina i quattro casi da tastiera che lo fissano; il commento del caso a clic (`:318-320`) dice che è
>   la strada dell'utente e di `asset-detail.spec.ts`. Corsa: **28/28**. **Il titolo** del caso («…the way the gallery helper
>   drives it…») ora è falso: `test-author` propone di cambiarlo; è una stringa, non un commento, e
>   `BACKLOG_POST_1.2.md:2370` (sezione G) la cita. Lo porto al coordinatore.

### X-R53 · revisione a posteriori (dev `78708660f`, commit `d38077ed4`), sola lettura (08:40–08:45)

> **Note implementazione**. Le colonne Δ 1D…5Y di Asset e FX dal backend (`/period-changes`), in uno stato loro con un
> contatore di versione; `fetchAllPriceData` (asset) e `fetchAllPairData` (FX) = `Promise.all` di prezzi e periodi.
> - ✅ **Flusso e pageBusy**: i gettoni restano sui grilli (primo caricamento, periodo, Aggiorna, aggiornamento in blocco,
>   impostazioni, riprova dei segnali, ricarica), quindi il pulsante gira finché ci sono anche le colonne Δ;
>   `periodChangesLoading` è nel `busy`/`data-busy` della pagina e non in `pageBusy`, come vuole il contratto di Y11; il
>   sondaggio dal vivo tocca solo `livePriceMap`, come prima. Versione: vale solo l'ultima risposta, e il `finally` spegne
>   solo per l'ultima; un errore svuota i Δ, sempre sotto la guardia.
> - **Regressione, medio-bassa: le preferenze delle colonne Δ 1W…5Y si azzerano a ogni caricamento** (Asset e FX).
>   `periodSpecs` parte vuoto e `visiblePeriodColumns([], …)` dà `[]`, quindi il primo disegno della tabella non ha quelle
>   colonne. `DataTable` all'`onMount` filtra le scelte di visibilità sulle colonne presenti; il suo `$effect` di
>   sincronizzazione toglie gli id assenti da `columnOrder` e **salva subito**, e toglie le larghezze. All'arrivo della
>   risposta le colonne tornano al posto predefinito, visibili, larghe come da definizione. Una colonna nascosta ricompare a
>   ogni caricamento, e la scelta si perde per sempre al primo cambio di visibilità salvato; lo stesso per l'ordine (subito) e
>   le larghezze (al primo ridimensionamento). Prima di X-R53 le colonne c'erano dal primo disegno (lista statica filtrata
>   sull'intervallo). In più un salto della tabella quando arrivano. Rimedi: (a) in `DataTable` (mio): non potare le
>   preferenze delle colonne assenti, filtrare solo al disegno — chiude anche la perdita che c'era già quando un intervallo
>   più corto nasconde i periodi lunghi; (b) in X: seminare `periodSpecs` con l'ultima risposta conservata.
> - Minori: la riprova dei segnali e il cambio di impostazioni richiedono anche i periodi (non ne dipendono); un errore
>   svuota anche Δ ancora validi per lo stesso `dateEnd`; senza una prima risposta non compare nessuna colonna di periodo.
>   FX, percorso per coppia (`loadPairPeriodChanges`): nessun indicatore, quindi `data-busy` può dire «finale» mentre il Δ
>   della coppia è ancora in volo; e non incrementa la versione, quindi una risposta completa partita prima e arrivata dopo
>   riscrive la coppia con dati più vecchi (finestra stretta).
>
> **Coordinatore (08:4x)**: il rimedio (a) è mio, in `DataTable` (tenere le preferenze delle colonne assenti, filtrarle solo
> al disegno), rosso prima, come **lotto a parte dopo Y-25**, con il suo checkpoint; se un test fissa la potatura come voluta,
> va detto prima di cambiarlo. Analisi in sola lettura: nessun test la fissa. `DataTable.test.ts` dichiara la persistenza
> non coperta (il suo jsdom non ha `localStorage`) e il filtro degli id assenti in `orderedColumns`; `ExposureTable.test.ts`
> fissa il verso opposto (una scelta di visibilità esistente sopravvive). Le note minori le passa a X il coordinatore.
> **Y-4**: titolo rinominato come proposto da `test-author` («selects an item on click, its collapsed family clicked open
> first: …»), 28/28; `BACKLOG_POST_1.2.md:2370` (sezione G) lo allinea il coordinatore.
>
> **Y-25, E2E ✅** (slot 2, `files/scripts/y25_e2e.sh`, 08:35–08:54, HEAD `039af67bb` più i miei file; carico a 5 minuti 42,5
> alla partenza, poi fino a 95 a un minuto per le altre sessioni): `front-asset asset-detail` **35/35** (2,7 minuti),
> `asset-mobile-layout` **21/21** (1,9), `asset-list` **30/30** (2,6), `front-fx fx-detail` **17/17** (1,0), `front-portfolio
> risk` **38/38** (2,7). 141/141. Porta 6189 libera alle 08:54.
>
> ### Y-25 + Y-3 + Y-4 — checkpoint 🧊 FROZEN (08:5x)
>
> 15 file tracciati, nessuno nuovo; `git diff --check` pulito; nessun server. Dev `547545b8e` (55 commit avanti) tocca solo
> `log.md` della devWiki (aggiunte in fondo: unione) e il backlog in altre sezioni (H, X, J, Z, B, E, MF).
>
> **Entrato**: 5 commit (punta `164a08220`), dev `73443c6db` (`log.md` della devWiki unito), niente CHANGELOG. HEAD avanzato a
> `73443c6db`.

## Y-27 · `DataTable` pota le preferenze delle colonne assenti — il rimedio (a) di X-R53 (dalle 08:55; HEAD `73443c6db`)

> **Via del coordinatore** (08:55): lotto a parte, rosso prima, con il suo checkpoint; se un test fissa la potatura come
> voluta, va detto prima di cambiarlo (nessuno la fissa: sopra).
>
> **Stato reale** (`components/table/DataTable.svelte`):
> - `onMount` (`:780-795`) carica le scelte di visibilità **filtrate sulle colonne presenti** (`:788-791`), le larghezze e
>   l'ordine;
> - l'`$effect` di sincronizzazione (`:831-892`) toglie da `columnOrder` gli id assenti e **salva subito**, toglie le scelte
>   di visibilità degli id assenti e salva, toglie le loro larghezze; gli id nuovi entrano al posto naturale;
> - `reorderColumns` (`:668`), chiamato da `setColumnOrder` di `ColumnVisibilityToggle.handleReorder` con le sole colonne
>   disegnate ed etichettate: salva quell'ordine, quindi un riordino perderebbe anche lui le colonne assenti;
> - `orderedColumns` (`:336`) e `columnVisibility` (`:204`) leggono già solo le colonne presenti: tenere gli id assenti nello
>   stato non cambia niente a schermo;
> - gli id di colonna costruiti dai dati sono limitati (`delta_*` di `AssetTable` e `FxTable`): tenerli non fa crescere lo
>   storage senza limite.
>
> **Scelta**:
> - in `dataTableLogic.ts` (la logica pura della tabella) due funzioni: `withNewColumns(order, columnIds)` aggiunge solo
>   gli id mai visti, al posto naturale (dopo l'ultima colonna che li precede in `columnIds`), e lascia dove sono gli id
>   assenti; `reorderKeepingAbsent(previousOrder, newOrder, columnIds)` rimette ogni id assente dopo la colonna che seguiva
>   (all'inizio se nessuna lo precede);
> - in `DataTable.svelte`: `onMount` tiene tutte le scelte di visibilità salvate; l'`$effect` usa `withNewColumns`, salva solo
>   quando l'ordine guadagna id, dà la larghezza predefinita solo a chi non ne ha una, e non pota niente; `reorderColumns`
>   usa `reorderKeepingAbsent`. Il ripristino (`resetColumns`) resta com'è: torna ai predefiniti delle colonne presenti.
> - Effetto: le colonne Δ di Asset e FX tengono posto, visibilità e larghezza fra un caricamento e l'altro; e anche quando un
>   intervallo più corto le nasconde e uno più lungo le rimette (la perdita che c'era già prima di X-R53).
>
> **Passi**: rossi (`test-author`: unità in `dataTableLogic.test.ts`, componente in `DataTable.test.ts` con un `localStorage`
> finto); correzione; prove leggere; E2E (`asset-list`, `fx-list` e qualche tabella col selettore delle colonne);
> documentazione; checkpoint.
>
> **Passo 1 ✅, i rossi** (`test-author` `95dd2300`, 08:58–09:14; solo i due file di test, già registrati):
> - **14 rossi**, ognuno per la ragione voluta, e 3 guardie verdi; tutti i casi di prima verdi (83 e 55):
>   - unità (`dataTableLogic.test.ts:721-839`, 8 rossi alla barriera dell'import dinamico: le due funzioni mancano): un id
>     assente resta al suo posto mentre uno nuovo va al posto naturale, anche all'inizio e in fila; niente di nuovo → stesso
>     contenuto; il riordino rimette un id assente dopo quello che seguiva o all'inizio, più id assenti tengono il loro
>     ordine, un id presente mancante dal nuovo ordine non si aggiunge. Gli array d'ingresso sono congelati. Le attese sono
>     state provate in memoria contro un'implementazione d'appoggio della specifica;
>   - componente (`DataTable.test.ts:1054-1289`, con un `localStorage` finto per caso, tolto dopo il `cleanup()`): l'ordine
>     salvato riscritto senza `delta_1Y` al montaggio; `delta_1Y` che torna ultima invece che dopo `a`; nascosta che arriva
>     visibile; la scelta persa salvando un'altra colonna; 80 px invece dei 222 salvati; il riordino mentre manca. Guardie:
>     una colonna mai vista va al posto naturale; `resetColumnLayout()` rende i predefiniti; senza niente salvato, l'ordine
>     dichiarato.
> - **Osservazioni di `test-author`**: oggi l'`onMount` perde la scelta di visibilità di una colonna assente solo in memoria
>   (lo storage la tiene, ignorata a ogni caricamento, e il primo salvataggio la cancella); il filtro di `orderedColumns`
>   sugli id assenti non lavorava mai e lavora da adesso; `withNewColumns` mette un id nuovo fra il suo predecessore e un
>   id assente che lo segue (`[a, delta_1Y, b]` + `x` dopo `a` → `[a, x, delta_1Y, b]`): scelta accettabile, non fissata.
>
> **Passo 2 ✅, la correzione** (09:15, `files/scripts/y27_apply.py --apply`, 5 sostituzioni esatte; 2 file, +72 −51):
> `dataTableLogic.ts` con `withNewColumns` e `reorderKeepingAbsent`; `DataTable.svelte`: `onMount` tiene tutte le scelte di
> visibilità, l'`$effect` usa `withNewColumns` e non pota niente (larghezza predefinita solo a chi non ne ha una),
> `reorderColumns` passa da `reorderKeepingAbsent`.
>
> **Passo 3, prove leggere** (`files/scripts/y27_light.sh`, dalle 09:15): `dataTableLogic` **91**, `DataTable` **64**,
> `DataTable.rowOrder` 12, `DataTableHeaderTooltip` 12, `DataTableColumnFilter` 59, `DataTablePagination` 20, `AssetTable` 12,
> `AssetTable.privacy` 2, `assetBrowse` 22, `FxMissingRate` 2, `ExposureTable` 17, `AssetSetComparisonLevels` 57,
> `htmlInterpolation.gate` 26 (tutti verdi, i 14 rossi compresi); svelte-check 0/0.
> **Documentazione**: `docs-writer` (`0082f94b`) su `core-ui/data-table.md` («Persistence» e «State Management»).
>
> **Passo 3 ✅** (fine, 09:28): Prettier segnalava `DataTable.svelte`: le due chiamate con `columns.map((c) => c.id)` come
> argomento andavano spezzate. Al loro posto `defaultColumnOrder`, che è già `$derived(columns.map((c) => c.id))`: gli id nel
> loro ordine dichiarato. Riprova (`files/scripts/y27_light2.sh`, 09:29–09:37): `dataTableLogic` 91, `DataTable` 64,
> `DataTable.rowOrder` 12, `AssetTable` 12, `ExposureTable` 17; svelte-check 0/0; Prettier pulito sui 4 file;
> `theme-roles --check` pulito; `git diff --check` pulito.
>
> **Passo 4 ✅, documentazione e devWiki**:
> - `docs-writer` (`0082f94b`): `core-ui/data-table.md`, il punto «Persistence» (una colonna assente per un po' tiene posto,
>   visibilità e larghezza; si aggiungono solo le colonne mai viste; il riordino dal selettore rimette un'assente dopo quella
>   che seguiva; il ripristino torna ai predefiniti delle presenti e dimentica le assenti), la lista «State Management» (le
>   regole dell'ordine in `dataTableLogic.ts`) e, in più, la riga di `dataTableLogic.ts` nella tabella dei file, che elencava
>   gli import vecchi. Pagina solo in inglese. Nota lasciata: «written back when they change» non vale per
>   `setColumnWidth`, che non salva; è di prima.
> - `mkdocs build` (strict) rc 0, 0 WARNING, 147,7 s; `check-links` 97 (`files/scripts/y27_docs_check.sh`).
> - devWiki: `problems/datatable-pruned-preferences-of-absent-columns` (nuova, legata a
>   `problems/datatable-net-columns-hidden-override-model`), la riga dell'indice, una voce del log. `check_source_paths.py`:
>   i 7 mancanti di sempre, nessuno della pagina nuova.
> - Backlog: Y-27 ✅ (commit al checkpoint).
> - **Slot E2E** chiesto (`files/scripts/y27_e2e.sh`); in coda dopo E e J (coordinatore, 09:3x).
>
> **Passo 5, E2E** (slot, `files/scripts/y27_e2e.sh`, 10:01–10:19, HEAD `73443c6db` più i miei file; carico a 5 minuti 24,6 alla
> partenza, poi fino a 100 a un minuto per le altre sessioni): `front-fx fx-list` **13/13**, `front-portfolio privacy-masking`
> **18/18**, `risk-lab` **44/44**, `front-asset asset-detail` **35/35**, `front-asset asset-list` **30/31**. Porta 6189 libera
> alle 10:19.
>
> **⚠️ Fuori pista: il rosso di `asset-list.spec.ts:1084`, non di Y-27** («sync all over a period whose prices are all filled
> backward does not warn», C-66, `32c64bbd9`, 16/10). Triage:
> - È una **precondizione** del test, non un'asserzione: nel periodo da oggi+7 a oggi+14 giorni nessun asset con un fornitore
>   mostra un prezzo («0 stored of 0 shown» per tutti). Il test chiede `POST /assets/prices/query` su un periodo **futuro** e
>   si aspetta prezzi portati avanti.
> - Lo stesso test era **verde alle 08:43** (corsa di Y-25, stesso giorno, quindi stesso periodo) su `039af67bb`.
> - In mezzo è entrato **X-R55** (`a71d23e7e`, «fix(prices): ceiling on query date ranges», fuso in dev alle 08:30 con
>   `ab7711f04`): `price_query.py` taglia ogni intervallo a `latest_range_end()`, cioè domani, e un elemento che **comincia**
>   dopo riceve un risultato vuoto. `a71d23e7e` non è antenato di `039af67bb`, lo è di `73443c6db`.
> - Quindi un conflitto di contratto fra X-R55 e il test di C-66: rosso deterministico su dev per chiunque. Y-27 tocca solo la
>   tabella del frontend e non può cambiare ciò che restituisce l'API. Nessuna ripetizione: non è un timeout, la causa si
>   legge nel codice. Diventa **Y-28** nel backlog, da instradare dal coordinatore (X-R55 o il proprietario di C-66).
>
> **Entrato**: `8e3c58ccc`, `51ba3bc2e`, `2aa8a0753` → dev `542c0e8b5`; l'unione di `log.md` sistemata dal coordinatore in
> `e9cd5d6ef`; niente CHANGELOG (la potatura nasceva con X-R53, non rilasciato); Y-28 passato a X. HEAD avanzato a
> `bab5a8fb9`.

## Y12b, il resto · V11 e P5 — analisi (10:25–10:40, sola lettura; HEAD `bab5a8fb9`)

> **Perché adesso**: MF-E1 è in dev (`e43dfae68`, dopo CP-7b di J): `LotTimelineEventSchema.opening_value` c'è (piano MF,
> `:1423`; nel client generato: «For the event that opens a lot (BUY, ADJUSTMENT_IN): the lot's original cost …, in the
> currency of unit_price. None on every other kind and when the conversion is missing»).
>
> **Stato reale**:
> - **V11**: `LotWacPriceChart.svelte:1418-1422`, il tooltip di un BUY calcola `|quantità| × prezzo unitario`; la bolla per
>   lotto (`:1034`) legge già `original_cost`. Atteso a numeri uguali (il costo d'origine è quantità × prezzo del lotto,
>   nella stessa valuta): è la regola della casa unica, non un numero sbagliato; senza conversione il campo è null → «—».
> - **T-U8, il modale della custodia**: `LotCustodyModal.svelte:236` legge già `original_cost`. Fatto (da J).
> - **P5**, decisione D-MF6(b) (gli aggregati dei lotti scelti sono misure interattive dichiarate nel codice, con il
>   marcatore e il gate di Y):
>   - `unifiedLotsTableHelpers.ts:107-185`: il piè della tabella sulle righe visibili (somme, medie pesate sul valore,
>     rendimento totale e netto sul valore d'apertura sommato, `ratioOrNull`);
>   - `lotComparisonChartHelpers.ts:130-174`: l'aggregato dei lotti scelti nel grafico di confronto (valore, e rendimento
>     = Σ P&L con proventi ÷ Σ costo d'origine);
>   - `lotWacPriceChartHelpers.ts:124-145` (`toPercentSeries`): la vista % del grafico WAC, ribasata sul primo valore non
>     nullo (è anche una delle copie di Y-26: dichiararla non cambia il suo comportamento su una base nulla);
>   - il totale fisso dei lotti c'è già nel backend (`LotSummarySchema`).
> - `lotGanttChartHelpers.isSplitTransition` (`:288-298`) moltiplica quantità × prezzo solo per riconoscere uno split senza
>   eventi: un'euristica non mostrata, nessuna dichiarazione.
> - Nessun test di componente per `LotWacPriceChart` (solo gli aiuti); un file di test nuovo vorrebbe una riga in
>   `_frontend_utility.py`, del programma colori.
>
> **Proposta**:
> 1. **V11**: un aiuto in `lotWacPriceChartHelpers.ts` (il valore d'apertura di un evento, cioè il campo del backend) usato
>    dal ramo BUY del tooltip; rosso d'unità in `lotWacPriceChartHelpers.test.ts` (il campo anche quando differisce da
>    quantità × prezzo; null senza campo) e un pin sul sorgente: il ramo BUY non moltiplica più.
> 2. **P5**: i tre moduli dichiarano la loro misura nel JSDoc d'apertura (`@financial-math-exception`, D-MF6(b)); il gate
>    `financialMathExceptions.gate.test.ts` (mio, Y12a) li aggiunge a `DECLARED_EXCEPTIONS` — il rosso: (A) finché i tag
>    mancano; `financial_math.md` regola 6 li nomina (`docs-writer`).
> 3. Nessun numero cambia; nessuna classe di colore. CHANGELOG: niente (parità e dichiarazioni).
> 4. Prove leggere: i test dei lotti, il gate, svelte-check, Prettier, `theme-roles`; E2E `front-broker detail` (i grafici
>    dei lotti e la tabella).
>
> **Conflitti da verificare dal coordinatore**: i tre aiuti e `LotWacPriceChart.svelte` (`features/brokers/lots`, FE7, miei;
> i colori ci sono passati con DV); `financial_math.md` (J l'ha toccato stamattina per J-44, MF lo usa); il gate è mio.
>
> **Via del coordinatore** (10:25): V11 + P5 come proposti, rossi prima; il valore di ADJUSTMENT_IN resta fuori; nessun ramo
> dei colori o di J tocca i miei file; in `financial_math.md` (aperto da MF per X-R59) il `docs-writer` tocca solo l'elenco
> della regola 6; lo slot E2E `front-broker detail` lo chiedo quando sono pronto.
>
> **Passo 1 ✅, i rossi** (`test-author` `1170c251`, 10:27–10:39; i due file di test, già registrati):
> - **V11** (`lotWacPriceChartHelpers.test.ts:511-651`, 7 rossi, 69 di prima verdi): quattro casi d'unità per
>   `eventOpeningValue`, fermi alla barriera dell'import dinamico (stringa decimale, zero compreso; 29,97 e mai 3 × 10 = 30;
>   `null`/assente; non numerico: `'n/a'` e `'Infinity'`, perché `safeDecimal` legge un numero iniziale, `'12abc'` → 12);
>   tre pin sul sorgente del ramo BUY di `buildMarkerTooltip` (chiama `eventOpeningValue(event)`, non moltiplica quantità ×
>   prezzo, importa l'aiuto), con un controllo positivo.
> - **P5** (`financialMathExceptions.gate.test.ts`, 3 rossi, 14 di prima verdi): tre voci nuove in `DECLARED_EXCEPTIONS`;
>   la regola (A) fallisce per ciascun file («its leading JSDoc block … carries no @financial-math-exception block tag»). Il
>   docblock del gate dice ora che le eccezioni sono misure interattive che l'utente plasma su un grafico o una tabella, e
>   nomina gli aggregati di D-MF6(b).
> - **Osservazioni**: senza selezione il piè somma tutte le righe filtrate, su ogni pagina, non solo quelle a schermo (la
>   frase del tag è corretta di conseguenza); una dichiarazione esenta tutto il file anche dalla regola (C), quindi
>   un'annualizzazione aggiunta un giorno a uno dei tre moduli passerebbe in silenzio → **Y-29** nel backlog (minimo).
>
> **Passo 2 ✅, la correzione** (10:40, `files/scripts/v11p5_apply.py --apply`, 6 sostituzioni esatte; 4 file, +28 −1):
> `eventOpeningValue` in `lotWacPriceChartHelpers.ts` e il ramo BUY di `LotWacPriceChart.svelte` che lo usa; il tag
> `@financial-math-exception` nel JSDoc d'apertura dei tre moduli (D-MF6(b)).
>
> **Passo 3 ✅, prove leggere** (`files/scripts/v11p5_light.sh`, 10:40–10:44): `lotWacPriceChartHelpers` **77**, il gate **17**,
> `unifiedLotsTableHelpers` 64, `lotComparisonChartHelpers` 162, `lotChartShared` 25, `lotGanttChartHelpers` 117,
> `LotCustodyModal` 3, `moneyRenderSites` 7; svelte-check 0/0; Prettier pulito sui 6 file; `theme-roles --check` pulito;
> `git diff --check` pulito.
>
> **Documentazione ✅**: `docs-writer` (`f7b35c59`) ha riscritto solo l'elenco della regola 6 di `financial_math.md` (un solo
> blocco, +5 −1): le misure dei lotti plasmate dalle scelte dell'utente (D-MF6(b)) e i tre file. `mkdocs build` (strict) rc 0,
> 0 WARNING; `check-links` 97. Lo stesso elenco sta in due righe di istruzioni condivise
> (`.github/instructions/financial-math.instructions.md:48`, `frontend.instructions.md:49`): chiesto al coordinatore.
>
> **Istruzioni condivise ✅** (via del coordinatore, 10:47): `.github/instructions/financial-math.instructions.md` regola 6 e
> `.github/instructions/frontend.instructions.md` «Financial numbers» nominano ora, oltre al righello e alle curve
> «what-if», gli aggregati dei lotti scelti dall'utente (D-MF6(b)); poche parole per riga, `git diff --check` pulito.
> **Slot E2E** `front-broker detail`: in coda (coordinatore, 10:47).
>
> **Passo 4 ✅, E2E** (slot, `files/scripts/v11p5_e2e.sh`, 10:52–10:58, HEAD `bab5a8fb9` più i miei file; carico a 5 minuti 40):
> `front-broker detail` **38/38** (2,1 minuti). Porta 6189 libera alle 10:58.
>
> ### V11 + P5 — checkpoint 🧊 FROZEN (10:5x)
>
> 11 file tracciati, nessuno nuovo; `git diff --check` pulito; nessun server. T-U8 (sezione T) lo riconcilia il coordinatore:
> con V11 e P5 il suo inventario è chiuso.
>
> **Entrato**: `10345abac` + `c97b0c5ee` → dev `d4ecfb692`; HEAD avanzato. T-U8 lo riconcilia il coordinatore nella sezione T.

## Y-29 · il gate delle eccezioni: un segnalino «annualizza» per voce (dalle 11:00; HEAD `d4ecfb692`)

> **Via del coordinatore** (10:59): rossi prima, prove leggere; dopo, mi passa lavoro da un'altra sezione mentre le voci del
> developer aspettano.
>
> **Stato reale**: la regola (C) del gate (`financialMathExceptions.gate.test.ts`, «annualization by exponent only where
> declared») filtra i colpi con `!DECLARED_FILES.has(hit.file)`: ogni file dichiarato è esente. Oggi alzano a un esponente
> con 365 solo `MeasureSignal.ts` (`Math.pow(growth, 365 / days)`, il Δ%/anno del righello) e `CompoundSignal.ts`
> (`Math.pow(1 + rate, 1 / 365)`, il fattore giornaliero della curva composta); `LinearSignal.ts` ha `days / 365` (nessun
> esponente), `SineSignal.ts` niente, e i tre moduli dei lotti di D-MF6(b) sommano, mediano e ribasano.
>
> **Scelta** (tutta nel file del gate, quindi `test-author` `c23643d5` fa rosso e cura): (1) il filtro di (C) in una funzione
> pura, senza cambi; (2) il rosso, un colpo sintetico in un modulo dei lotti che deve contare come trasgressore; (3) un
> segnalino obbligatorio `annualizes: boolean` per voce, vero solo per `MeasureSignal.ts` e `CompoundSignal.ts`; (C) ammette
> esponenti solo lì; docblock e messaggi aggiornati; un controllo che anche il colpo vero di `MeasureSignal` venga trovato.
>
> **Documentazione**: `financial_math.md` descrive (C) in due punti («outside the listed files»: la frase del gate nella
> regola 6, `:478-479`, e il terzo punto della sezione del gate, `:629`); chiesto al coordinatore se toccarli ora (MF ha la
> pagina aperta).
>
> **Fatto ✅** (`test-author` `c23643d5`, 11:00–11:14; solo il gate, +90 −30):
> - base 17/17; **passo 1**, il filtro in `annualizationOffenders(hits, allowedFiles)` e l'insieme `ANNUALIZING_FILES` (per
>   ora uguale a `DECLARED_FILES`): 17/17; **passo 2**, il rosso: un controllo (D) che fa produrre allo scanner del gate un
>   esponente con 365 in un file non dichiarato, nei tre moduli dei lotti, in `MeasureSignal` e in `CompoundSignal`, e vuole
>   trasgressori i primi quattro → 1 rosso («Y-29: being declared does not exempt a file from (C)…»: venivano segnalati solo
>   il file non dichiarato, non i tre moduli); **passo 3**, la cura: `annualizes: boolean` obbligatorio in ogni voce, vero
>   solo per `MeasureSignal.ts` e `CompoundSignal.ts`; `ANNUALIZING_FILES` costruito dal segnalino; titolo e messaggio di (C)
>   aggiornati; docblock ((C), (D), «Adding an exception», «Completeness»); una guardia nuova (i due file sono nell'insieme,
>   e ogni file dell'insieme ha un esponente vero) → **19/19**.
> - Prove che la guardia morde, poi ripristinate col checksum: `LinearSignal` a `true` → rossa la sola guardia; `MeasureSignal`
>   a `false` → tre rossi, e la regola (C) nomina l'esponente vero di `MeasureSignal.ts:56`.
> - Osservazioni: prima di Y-29 il verdetto di (C) non aveva un controllo positivo (un filtro che non segnalava niente
>   sarebbe passato): il controllo del passo 2 lo copre; la concessione resta per file (una seconda annualizzazione dentro
>   `MeasureSignal` passerebbe), ora scritto in «Completeness».
> - **Documentazione** (`docs-writer` `bc90fe07`, via del coordinatore per le sole due righe): `financial_math.md:479-480`
>   («outside the listed files that annualize») e `:630-631` (il segnalino `annualizes: true`, il righello e la curva
>   composta); `git diff` di due blocchi, +4 −2.
> - **Prove leggere** (`files/scripts/y29_light.sh` e `y29_docs_check.sh`, 11:14–11:18): il gate **19/19**; svelte-check 0/0
>   (il campo obbligatorio è controllato); Prettier pulito; `theme-roles --check` pulito; `git diff --check` pulito;
>   `mkdocs build` (strict) rc 0, 0 WARNING; `check-links` 97.
> - **Backlog**: Y-29 ✅. Nessun E2E: cambia solo un test e una pagina per sviluppatori.
>
> ### Y-29 — checkpoint 🧊 FROZEN (11:1x)

## J-12, la metà del pannello (N81, opzione A) — analisi (dalle 11:20; HEAD `ce2452615`, sola lettura)

Dal coordinatore (dalla sezione di J). **Metà di J**: con `FAILED` la risposta dei lotti tiene stato, issue, metadati,
prezzi e righe WAC; tornano vuote le sezioni derivate dai lotti (lotti, Gantt, eventi, custodia, valore, rendimento,
performance, eventi di reddito). **Metà mia**: con `FAILED` nessun disegno dei lotti; una spiegazione semplice e, per ogni
issue, il **nome** del broker, la data e un link alla transazione da correggere (oggi il messaggio dice «(broker 7)»).
J parte dopo J-50. Il piano di J (05) non ha ancora un'analisi di J-12: solo le menzioni `:1615` e `:5406`.

**Stato reale (verificato)**
- `LotsAnalysisPanel.svelte`: avviso rosso `lots-analysis-panel-failed` (`:476-480`, chiave `brokers.lots.analysisFailed`,
  «… figures may be incomplete»), poi disegna **sempre** grafico WAC/prezzo, Gantt, tabella e confronto (`:486-547`);
  modale della custodia a `:551`. Lo stato e le issue arrivano da `applyMain` (`:194-195`).
- Con `lots` vuoto `effectiveSelectionIds` è vuoto, quindi la seconda richiesta (valore e rendimento) già non parte
  (`loadSelectionHistories`, `ids.length === 0`).
- `LotDataQualityBanner.svelte`: raggruppa **per codice** e mostra i parametri della **prima** issue del gruppo; le chip
  solo per i lotti visibili (con `FAILED` e lotti vuoti: nessuna chip).
- «(broker 7)» viene dai testi `dataQuality.shortTransferNotSupported`, `shortAdjustmentNotSupported` e
  `fifoSourceQuantityMissing` (`{broker_id}`); `transferPairMissing` non ha il broker.
- **Cosa porta oggi ogni issue** (`lots_analysis_service.py::_build_data_quality_report`): `message_params` con
  `transaction_id`, `lot_id`, `broker_id`, `related_transaction_id`, più i parametri del motore (`missing_quantity`).
  **Nessuna data.** I codici che danno `FAILED` sono `_QUANTITATIVE_FAILURE_CODES` (`fifo/models.py:28`); severità ERROR.
  Il frontend non ha copia di quella lista.
- Le altre issue della stessa risposta (`_report_gaps`: `MISSING_FX_RATES`, `MISSING_COST_BASIS`) riguardano le righe WAC,
  che restano: sono fissate da `data-quality-real.spec.ts` e `data-quality-legacy.spec.ts`.
- Il nome del broker si risolve già nel client: `resolveBrokerName` (`lotChartShared.ts:95`) sulla prop `brokers`
  (Dashboard: `allBrokers`, ⊇ il perimetro; pagina broker: il broker stesso).
- Il link esiste: `handleGotoTransaction(id)` → `/transactions?highlight=<id>`; la pagina carica la riga per id se non è
  nella finestra e apre la sua modale (`consumeHighlightParam`).
- Nessun test fissa l'avviso `FAILED` (né Vitest né E2E). Documentazione: `developer/frontend/components/features/
  lots-analysis.md:121` dice «warn but show»; la pagina utente `user/dashboard/positions.en.md` (pannello dei lotti, `:207`).

**Contratto chiesto a J** (proposta, da concordare in breve)
1. Con `FAILED`: vuote (`[]` o `null`) le sezioni dei lotti; restano `price_history`, `broker_wac_history`,
   `cumulative_wac_history`, `quote_base_quantity`, `calculation_metadata`, `data_quality` (tutte le issue).
2. Ogni issue di un codice che fa `FAILED` porta in `message_params`, oltre ai campi di oggi: `transaction_date` (ISO,
   nuovo) e un segnalino `fails_analysis: true` (nuovo, così il frontend non copia la lista dei codici).
3. Nessun nome di broker dal backend; `message_i18n_key` invariata.

**Proposta per il pannello**
- Con `FAILED`: un avviso nuovo (`LotAnalysisFailedNotice.svelte`, file nuovo, solo ruoli `-lf-`) con la spiegazione e una
  riga per issue: broker per nome, data, messaggio, «Apri la transazione». Il banner tiene le sole issue che non fanno
  `FAILED`. Nascosti Gantt, tabella e confronto; il grafico prezzo/WAC resta con le sole linee (decisione D1).
- Helper puro per dividere e ordinare le issue (data, poi id; dedup per codice e transazione) in
  `lotDataQualityHelpers.ts`.
- Testi: `brokers.lots.analysisFailed` riscritto (le cifre non si vedono più); i tre `dataQuality.*` senza
  «(broker {broker_id})»; chiavi nuove per il link; 4 lingue.

**Decisioni**: D1 il grafico prezzo/WAC resta con `FAILED` (proposta: sì, è a livello di posizione e giusto); D2 le issue
non bloccanti restano nel banner (proposta: sì, senza doppioni); D3 i testi nelle 4 lingue li scrivo io.

**Lotto unico**, dopo il sì di J sul contratto: rossi (`test-author`: Vitest dell'helper e dell'avviso), cura, testi;
E2E in `brokers-detail.spec.ts` (`front-broker detail`, nessun cambio del runner) quando la metà di J è in dev; scenario
proposto: broker con `allow_asset_shorting`, una SELL che apre uno short, un ADJUSTMENT− → `SHORT_ADJUSTMENT_NOT_SUPPORTED`.
Documentazione (`docs-writer`): `lots-analysis.md:121` e la pagina utente. Checkpoint FROZEN.

> **Inviata** al coordinatore e a J (proposta del contratto, domande (a) id sempre apribile, anche con le copie di J-10/J-47?
> (b) più issue per riga e codice?) alle 11:27.
>
> **Coordinatore (11:28)**: **D1 sì** (grafico prezzo/WAC con le sole linee; Gantt, tabella e confronto nascosti), **D2 sì**,
> **D3 sì** (4 lingue con `dev.py i18n add`/edit). Nessun ramo BK tocca `features/brokers/lots/` o `positions.en.md`;
> pagine divise con J come proposto. **I rossi partono quando J accetta il contratto** (`transaction_date` +
> `fails_analysis`); l'E2E aspetta la metà di J in dev.
>
> **J (11:3x): contratto sì**, con correzioni:
> - con `FAILED` le sezioni tornano **`null`** (default dello schema, come `_empty_response`): `lots`, `gantt_segments`,
>   `custody_history`, `lot_events`, `value_history`, `return_history`, `performance_history`, `income_events`,
>   `economic_allocation_groups`, **`price_history`** (è per lotto: `LotPriceHistoryPoint.lot_id`) e
>   `asset_orphan_income/fees/taxes`. Restano `broker_wac_history`, `cumulative_wac_history`, `quote_base_quantity`,
>   `calculation_metadata`, `data_quality` con tutte le issue;
> - `transaction_date` e `fails_analysis: true` solo sulle issue dei codici di `_QUANTITATIVE_FAILURE_CODES`;
> - (a) `transaction_id` è sempre una riga vera del perimetro (anche con le copie di J-10/J-47). J corregge nel backend,
>   con un rosso, l'id di un trasferimento in eccesso e di `SHORT_TRANSFER_NOT_SUPPORTED`: la gamba che dà, non l'id più
>   basso della coppia. **Mai collegare `related_transaction_id`** (può nominare una compagna che l'utente non vede);
> - (b) di regola una issue per riga e codice; deduplicare copre i dati corrotti.
> - J parte dopo il checkpoint di J-50.
>
> **⚠️ Fuori pista (D1)**: la linea del prezzo di mercato del grafico WAC nasce dall'unione per data dei punti per lotto di
> `price_history` (`LotWacPriceChart.svelte:747-764`), quindi con `FAILED` il grafico tiene **solo le linee del costo
> medio**. Proposta al coordinatore (11:4x): va bene così; una serie del prezzo senza lotti sarebbe un campo nuovo di J,
> da indice. Chiesto anche l'OK per la riga del runner: il test del componente va in `_frontend_broker.py`
> (`front_broker_unit`, accanto a `LotCustodyModal.test.ts`); i test dell'helper in `lotDataQualityHelpers.test.ts`, già
> in `core-unit`.
>
> **Rossi** (`test-author`, dalle 11:4x): `partitionLotIssues` e `buildFailureRows` in `lotDataQualityHelpers.ts`;
> componente nuovo `LotAnalysisFailedNotice.svelte` (test id `lots-analysis-panel-failed` tenuto, righe
> `lots-analysis-failed-row-{code}-{tx}`, link `lots-analysis-failed-goto-{tx}`); quantità formattata e mascherata come
> nella modale della custodia (D5′).
>
> **Coordinatore (11:4x)**: (1) OK, con `FAILED` solo le linee del costo medio, niente linea del prezzo; la serie del
> prezzo senza lotti è una voce a parte nella sezione Y, per J → **Y-30** nell'indice. (2) OK alla riga additiva in
> `_frontend_broker.py` (`front_broker_unit`, accanto a `LotCustodyModal.test.ts`) e alla frase della docstring: fatta
> (lista, docstring e `desc` di `broker-unit`).
>
> **J (12:0x), issue con `FAILED`: la mia proposta, nel backend.** Restano le bloccanti (`fails_analysis: true`) e le lacune
> delle righe WAC di `_report_gaps` (cambi mancanti delle righe WAC, `MISSING_COST_BASIS`); vanno via
> `REFERENCE_PRICE_FALLBACK/_UNAVAILABLE`, `ASSET_INCOME/COST_NO_ELIGIBLE_LOTS`, `CURRENT_PRICE_ASSUMED_AT_COST` e le
> lacune di cambio delle cifre dei lotti (quelle sezioni non si calcolano più). L'AI Export porta solo i `failure_codes`
> bloccanti: già coerente. J lo fissa in un test del servizio.
>
> **Rossi ✅** (`test-author` `b73cf952`, 11:4x–12:0x; logs `files/logs/j12_*_run1.json`):
> - `lotDataQualityHelpers.test.ts`: 75 test, **58 rossi** (`partitionLotIssues is not a function` ×9,
>   `buildFailureRows is not a function` ×49), i 17 preesistenti verdi.
> - `LotAnalysisFailedNotice.test.ts` (nuovo, jsdom, 10 test): non si raccoglie (`Failed to resolve import
>   "./LotAnalysisFailedNotice.svelte"`). Dopo il componente resta rosso «never shows a bare broker id» finché i testi
>   del catalogo stampano `{broker_id}`. Privacy fissata anche col commutatore in posto (`setPrivacyEnabled`).
> - Osservazioni del test-author, accolte: l'ordine d'ingresso (se la mia metà entra prima di quella di J, una risposta
>   `FAILED` non ha issue segnalate: l'avviso mostra solo la spiegazione e le bloccanti tornano al banner senza broker) →
>   **il lotto entra in dev con o dopo la metà di J**; due issue dello stesso codice senza id di transazione collassano
>   (`CODE:none`, solo dati corrotti); `#<id>` resta il ripiego di `resolveBrokerName` (le due chiamate passano una
>   lista che copre il perimetro).
>
> **Cura ✅** (12:0x–12:15):
> - `lotDataQualityHelpers.ts`: `partitionLotIssues` (solo con `FAILED`, il segnalino `fails_analysis === true` decide;
>   ordine d'ingresso) e `buildFailureRows` (id solo da `transaction_id`, intero sicuro positivo; giorno ISO nudo o null;
>   nome del broker con `resolveBrokerName`; `missing_quantity`, e solo lui, dal formattatore iniettato; una riga per
>   (codice, transazione), la prima vince; ordine giorno → id → codice, i null in fondo). Import di `resolveBrokerName` da
>   `lotChartShared.ts` (nessun ciclo).
> - `LotAnalysisFailedNotice.svelte` (nuovo, solo ruoli: il contenitore dell'avviso di prima, `AlertCircle`, il bottone
>   sottolineato nel colore del testo dell'avviso con `focus-visible:outline-lf-focus`; la quantità come nella modale,
>   `maskableQuantity(formatExactDecimal(…))`; righe `$derived`, quindi seguono la privacy). Etichetta del bottone:
>   `brokers.lots.modal.goToTransaction`, già esistente.
> - `LotsAnalysisPanel.svelte`: `applyMain` con `FAILED` non prende sezioni dei lotti (`lotSection`), anche da una
>   risposta in cache; `analysisFailed` + `issueParts`; l'avviso prima del banner (che riceve solo `issueParts.banner`);
>   Gantt, tabella e confronto sotto `{#if !analysisFailed}`; commento d'intestazione.
> - Testi (`dev.py i18n update/add`, 4 lingue): `brokers.lots.analysisFailed` riscritto; `brokers.lots.analysisFailedFix`
>   nuovo; i tre `dataQuality.*` senza «(broker {broker_id})» (`fifoSourceQuantityMissing` = «Removes {missing_quantity}
>   more than the broker held that day»). `i18n check` strict ok, diff di 24+/20−.
> - **Prove leggere** (`files/scripts/j12_light.sh`, `j12_gates.sh`; 12:03–12:15): `lotDataQualityHelpers` **75/75**,
>   `LotAnalysisFailedNotice` **10/10**, `themeRoles.gate` 80, `moneyRenderSites` 7, `htmlInterpolation.gate` 26,
>   `financialMathExceptions.gate` 19; Prettier pulito; `theme-roles --check` pulito; `git diff --check` pulito;
>   `front-broker broker-unit` **7 file / 70** (il file nuovo registrato); `gate-i18n-catalog` **176**; `gate-i18n-usage`
>   **195**; svelte-check **0/0**.
> - **⚠️ Fuori pista**: il primo svelte-check dava 2 errori in `features/legal/` (A9: `InstanceConfigResponse.legal`): il
>   client generato del worktree (ignorato, 10:52) era più vecchio del fast-forward a `ce2452615`. `dev.py api sync`
>   (scrive solo file ignorati) → 0/0. Non è del lotto.
> - In corso: `docs-writer` (`lots-analysis.md:121`, `positions.en.md` «When the panel warns you», senza timbro) e il
>   `test-author` per l'E2E in `brokers-detail.spec.ts` (scritto ora, lanciato dopo la metà di J in dev).
>
> **Documentazione ✅** (`docs-writer` `187113c2`, 12:12–12:19; +18 −10):
> - `user/dashboard/positions.en.md:208`: il punto «A red message» riscritto (le transazioni da correggere col giorno, il
>   broker e **Go to transaction**; lotti, cronologia e confronto nascosti; il primo grafico con le sole linee del costo
>   medio). Debito di traduzione IT/FR/ES reale: **nessun timbro**.
> - `developer/frontend/components/features/lots-analysis.md`: riga di `LotAnalysisFailedNotice` nella tabella dei
>   componenti; ordine di disegno (l'avviso prima di `LotDataQualityBanner`, nome corretto); flusso §1 (con `FAILED`
>   nessuna richiesta della selezione); «warn but show» → «explains and hides» (J-12) in cinque punti; tabella dei test id;
>   link alla pagina del servizio.
> - Osservazione accolta: il commento «never shown as an id» di `buildFailureRows` esagerava (`#<id>` per un broker che la
>   lista non ha, `—` senza broker): corretto, anche nella devWiki.
> - **devWiki**: revisione datata 17/10 in `decisions/fifo-v4-gross-net-status-model.md` (la scelta «warn but show» del
>   22/07 superata da N81, le due metà del contratto, Y-30), riga dell'indice, voce in `log.md`; detto a J (12:1x), che
>   non tocca quella pagina. `check_source_paths.py`: i soliti 7.
> - **Prove** (`files/scripts/j12_docs_check.sh`, 12:20–12:22): `mkdocs build` (strict) rc 0, 0 WARNING; `check-links`
>   **97**.
>
> **E2E scritta, non lanciata** (`test-author` `b73cf952`, 12:1x–12:3x; +365 righe in coda a `brokers-detail.spec.ts`,
> più due import; Prettier pulito; il tipo controllato, nessun errore nel file):
> - describe «Broker detail — a FAILED lots analysis names the transaction to fix (J-12)»: **J12-1** (lo scenario, il
>   controllo prima della riga che rompe, la riga col nome del broker e il giorno, nessun id nudo, solo le linee del costo
>   medio, niente Gantt/tabella/confronto, nessun gruppo bloccante nel banner) e **J12-2** (il bottone apre la transazione
>   in sola lettura nella pagina delle transazioni: navigazione `?highlight=<id>`, il bottone di modifica, `#<id>` nel piede,
>   Save nascosto, come T11 di `transactions-modals.spec.ts`).
> - Scenario: broker del test con `allow_cash_overdraft` e `allow_asset_shorting` (il controllo dei saldi salta solo con
>   tutti e due); asset manuale in EUR, chiusure a −40/−30/−20/−5 giorni; BUY 10 a 100 (−40), SELL 15 a 110 (−30: chiude il
>   lungo, apre uno short di 5; il controllo: non `FAILED`, Gantt, tabella e confronto si disegnano), ADJUSTMENT −2 (−20) →
>   `SHORT_ADJUSTMENT_NOT_SUPPORTED` (manca 2) → `FAILED`. Ogni test crea e cancella i suoi dati.
> - Premessa via API prima della pagina: stato `FAILED` e una sola issue con `fails_analysis`, con id, broker e giorno.
>   **Finché la metà di J non è in dev, cade lì con un messaggio che nomina il segnalino mancante**, non per un'attesa.
> - Da confermare solo con una corsa: la storia WAC del broker resta con `FAILED`; il banner assente (tollerato se c'è);
>   la lingua `en-US` del browser; la navigazione colta da `waitForURL` (`commit`); 90 s per test sotto carico.
> - Punti deboli segnalati → **Y-31** (basso): la regola M-18 ricopiata nella spec; nessuno stato pubblicato per il «nessun
>   dato» del grafico WAC e per la riga evidenziata.
>
> ### J-12 metà del pannello — checkpoint 🧊 FROZEN (12:4x), senza l'E2E lanciata
>
> - Delta: 20 file tracciati modificati + 2 nuovi (`LotAnalysisFailedNotice.svelte` e il suo test). Esclusi: il client
>   generato (`openapi.json`, `generated.ts`, ignorati, rigenerati da `api sync`), il catalogo i18n generato, i log.
> - Prove finali: Prettier pulito sui file toccati, `git diff --check` pulito, porta 6189 libera.
> - **Ordine d'ingresso**: il commit sul mio ramo ora; l'ingresso in dev **con o dopo la metà di J** (senza, l'avviso non ha
>   righe e le bloccanti tornano al banner senza broker); poi lo slot `front-broker detail` per l'E2E, prima della consegna
>   finale.
>
> **Coordinatore (12:39)**: J-12 metà del pannello committata (`23aa2110f`, `0bb91c384`, `0c7afb49f`); entra con la metà di
> J o dopo, poi lo slot `front-broker detail`; il testo 🔄 del CHANGELOG salvato.

## X-R59, il passaggio del frontend — analisi (12:39–12:5x; HEAD `0c7afb49f`, sola lettura)

Dal coordinatore (12:39), tolta dalla coda di X (X tiene X-R60, X-R58 e la divisione in lotti delle period-changes). Il
passaggio sostituisce `computeDerivedPriceState()` (le card degli asset), `displayFxDelta()` (`FxTable`, `FxCard`,
`FxPriceSummary` di `fx/[pair]`) e il calcolo della pagina dell'asset (`assets/[id]/+page.svelte:502-514`) con la quotazione
live (`POST /prices/current?range_start=`). Note di X da includere: `range_start` tagliato a 1900-01-01; −100 % resta con un
prezzo finale 0 (MF corregge la regola della casa). Da non toccare senza dirlo: le regioni di Z (`assets/+page.svelte`
~742-760, `fxStoreRegistry.ts` ~429-453) e `periodChanges.ts` (X-R60).

**Il contratto** (MF, `a8de6b584` «feat(prices): whole-range change from the server», sopra `46bbbb1e3`, già nel mio HEAD;
non in dev; decisione N80). Il piano di MF non è nel commit: valgono codice, schemi e documenti.
- `POST /assets/prices/period-changes` e `POST /fx/currencies/period-changes`: ogni voce accetta `range_start` (≥
  1900-01-01, ≤ `as_of`, al più 5 giorni distinti per richiesta come `as_of`, 422 `period_changes_too_many_days`); ogni
  risultato porta `range_change`: asset `{reference_date, change_abs, change_ratio}` (con `target_currency` convertito al
  cambio di ogni giorno), cambi anche `inverse_change_abs`, `inverse_change_ratio`. Riferimento: il valore su `range_start`
  (all'indietro), altrimenti il primo dentro l'intervallo, cioè il primo punto della serie della pagina; ancora: il valore
  su `as_of`. Tutto null senza valore o con uno dei due ≤ 0 (MF correggerà lo 0 finale → −100 %).
- `POST /assets/prices/current?range_start=`: ogni risultato porta `range_change` verso il prezzo corrente (live o
  `db:last_known`), **nella valuta del prezzo, senza conversione**; un fallimento lascia i campi null; `range_start` <
  1900-01-01 → 422.
- `range_change()` in `financial_math/returns.py`. I documenti di MF (`assets/architecture.md`, `fx/architecture.md`,
  `financial_math.md`) dicono «the web app is to send `range_start`… it does not yet»: da aggiornare col passaggio.

**Stato reale del frontend**
- Lista asset: le card prendono `deltaAbs`/`deltaPercent` da `computeDerivedPriceState()` (thread principale `:820` e Web
  Worker `priceProcessing.worker.ts:80`), primo e ultimo punto della serie, in float. La card mostra il prezzo live
  (`livePriceMap`) ma la Δ della serie: incoerenza già oggi. `AssetTable` ha `deltaAbs`/`deltaPercent` nelle righe ma non li
  disegna. `loadPeriodChanges()` (X-R53, `:638-656`) chiede già `period-changes` per tutti gli asset con `as_of = dateEnd`,
  in parallelo alla serie, con il suo contatore di versione e `periodChangesLoading` nel busy.
- Lista cambi: `FxTable.getDelta()` → `displayFxDelta()` per le colonne Δ Abs e Δ %; `FxCard` la sua Δ %; il caricamento delle
  period-changes (`loadPeriodChanges`, `loadPairPeriodChanges`) sceglie diretto/inverso per coppia come per le colonne dei
  periodi.
- Pagina della coppia: `displayFxDelta()` sui punti del grafico; oggi nessuna chiamata a `period-changes`.
- Pagina dell'asset: `lastPrice` = live se l'intervallo arriva a oggi, altrimenti l'ultima chiusura; Δ dal primo punto del
  grafico, nella **valuta di visualizzazione** (la serie è chiesta con `target_currency`; il live è convertito dal client con
  `convert` al cambio di oggi, `AssetDetailLive`). Con una lacuna di cambio parziale il primo punto è nativo e l'ultimo
  convertito: Δ in valute miste (difetto di oggi).
- `'min'` diventa `2000-01-01`; una data a mano o nell'URL può essere prima del 1900: serve il taglio.
- Nessun elemento della Δ ha un test id (card, riassunti); l'E2E di X-R53 cerca le voci con `objectContaining`, quindi un
  `range_start` in più non lo rompe. Test che fissano le copie: `assetPriceDerived.test.ts` (`:21`, `:54`),
  `fxStoreRegistry.test.ts` (`:502-525`); `assetDetailLive.svelte.test.ts` per il poller.

**Decisioni proposte**
- **D1, pagina dell'asset con valuta convertita e quotazione live** (il caso di default per chi guarda un asset nella sua
  valuta): `/prices/current` dà `range_change` solo nativo. (a) MF aggiunge `target_currency` a quel `range_change`
  (riferimento al cambio del suo giorno, ancora al cambio di oggi, come il client converte il live) — **proposta**; (b)
  ripiego: `period-changes` con `target_currency` e `as_of` oggi, sul prezzo salvato (il poll lo aggiorna: Δ in ritardo di
  al più un poll); (c) la Δ nativa: sbagliata.
- **D2, card della lista**: parità (Δ della serie, dalle period-changes) — **proposta**; ancorarla al live come la pagina
  dell'asset (il poll della lista chiama già `/prices/current` per tutti) va nell'indice, se il developer lo vuole.
- **D3, dove vive la richiesta**: il `range_start` deve viaggiare nella stessa richiesta delle period-changes (un'altra
  costerebbe i dieci giorni dei periodi di nuovo), quindi due aggiunte opzionali in `fetchAssetPeriodChanges` e
  `fetchFxPeriodChanges` di `periodChanges.ts` (il file di X-R60 e della divisione in lotti); il resto (taglio a 1900,
  lettura di `range_change` in `{abs, pct}` diretta/inversa) in un modulo nuovo, `utils/rangeChange.ts`.
- **D4**: tolte le copie (`displayFxDelta`, la Δ di `computeDerivedPriceState`, il calcolo inline della pagina dell'asset),
  non lasciate accanto; i campi morti di `AssetTable`.

**Conflitti previsti**: X (X-R60 e la divisione in lotti su `periodChanges.ts` e sui caricatori delle due liste; X-R58 sul
`catch` di `fetchAllPriceData`); AF (i colori di asset e cambi: `AssetCard`, `FxCard`, `FxTable`, i riassunti, le pagine —
le mie modifiche sono prop, derivati e test id, nessuna classe); MF (i tre documenti, dopo l'ingresso). Regioni di Z
evitate.

**Lotti**: A — liste e pagina della coppia (`periodChanges.ts` + `rangeChange.ts`, le due liste, la coppia; via
`displayFxDelta` e la Δ di `computeDerivedPriceState`); B — pagina dell'asset (period-changes per il caso storico,
`/current?range_start=` nel poller per il live, D1). Ognuno: rossi (`test-author`), cura, documenti (`docs-writer`), E2E
in slot, checkpoint FROZEN; la riga 🔄 del CHANGELOG con l'ultimo. Prerequisito di entrambi: X-R59 di MF (con SEC9-1 e lo 0
finale) nel mio HEAD.
>
> **Coordinatore (12:48)**: **D1 = (a)**: MF aggiunge `target_currency` al `range_change` di `/prices/current` nel suo lotto
> SEC9-1 aperto (riferimento al cambio del suo giorno, prezzo live al cambio di oggi, come il client). **D2**: parità; la Δ
> ancorata al live sulla lista → **Y-32** nell'indice. **D3, D4**: sì, le copie vanno via. **Ordine su `periodChanges.ts`**:
> X-R60 (X, ora) → il mio lotto A sopra → la divisione in lotti di X dopo Z-27 → X-R58; le mie aggiunte scritte in modo che
> la divisione di X le possa avvolgere. **AF**: nessuna modifica aperta su quei componenti; solo prop, derivati e test id,
> nessuna classe. **X-R59 di MF**: dopo SEC9-1, lo 0 finale e D1(a), poi l'ingresso (primo pomeriggio). Intanto i rossi
> Vitest; righe dei runner (`_frontend_asset.py`, `_frontend_fx.py`) OK, solo aggiunte.
>
> **Lotto A, rossi Vitest** (`test-author`, dalle 12:5x): il modulo nuovo `utils/rangeChange.ts` (`EARLIEST_RANGE_START`,
> `RangeDelta`, `rangeStartFor`, `assetRangeDelta`, `fxRangeDeltas`); i due fetcher di `periodChanges.ts` con un terzo
> argomento facoltativo `rangeStart` (il fetcher applica `rangeStartFor`; senza, le voci restano identiche) e le mappe
> `rangeDeltaByAssetId` / `rangeDeltasByPair`, provati in un file nuovo (`periodChanges.rangeChange.test.ts`) per non
> toccare `periodChanges.test.ts`, aperto da X-R60; `computeDerivedPriceState` senza Δ; `displayFxDelta` non più esportata.
>
> **J-12, l'E2E sulla revisione combinata ✅** (12:53–13:04). Il coordinatore: J-12 completa in dev (metà di J `4195fa857`
> + `fc8ab50ca`, la mia `0c7afb49f` → dev `46b5fbc0e`; il `log.md` riunito e la riga 🔄 del CHANGELOG combinata in
> `4e11fabec`). Parcheggiati i miei 3 file sporchi (`files/patches/xr59_park_1254.patch`, 144 righe; il test-author di X-R59
> in pausa, nessun file scritto), fast-forward a `4e11fabec`, patch riapplicata pulita. Slot `front-broker detail`
> (`files/scripts/j12_e2e.sh`, guardia del carico a 5 minuti: 36.76): **40/40** (2,3 min), J12-1 e J12-2 compresi, nessun
> ritentativo; porta 6189 libera.
>
> **Lotto A, rossi ✅** (`test-author` `b4d8d984`, 12:50–13:20, in pausa durante il fast-forward e l'E2E di J-12; log
> `files/logs/xr59_*.json`):
> - `rangeChange.test.ts` (nuovo): non si raccoglie (modulo mancante);
> - `periodChanges.rangeChange.test.ts` (nuovo): **26 rossi**, 2 verdi (i rifiuti della chiamata); nessun `range_start`
>   inviato, nessuna mappa nuova, l'elenco vuoto senza la mappa;
> - `assetPriceDerived.test.ts`: **3 rossi** (le chiavi `deltaAbs`/`deltaPercent` ci sono ancora), 10 verdi;
> - `fxStoreRegistry.test.ts`: **1 rosso** (`displayFxDelta` esportata), 90 verdi; i 12 test di `displayFxDelta` (`:498-545`,
>   col commento B1) tolti.
> - `rangeStartFor` controlla il calendario (`2026-02-30`, `2026-02-29`, `1900-02-29`, mese 13, mese o giorno 00 → null; una
>   data sbagliata prima del 1900 è rifiutata, non alzata).
> - Osservazioni del test-author, accolte: `ratioToPercent` deve lasciare `periodChanges.ts` (importa `$lib/api`: un modulo
>   puro non può importarlo, e sarebbe un ciclo) → casa nuova in `rangeChange.ts`, `periodChanges.ts` la riesporterà nel
>   lotto A (sopra X-R60); i due `toEqual` di `periodChanges.test.ts` sull'elenco vuoto («asks nothing for no asset/pair»)
>   vanno adattati nel lotto A (chiavi nuove); il client generato toglie `range_change` finché non è rigenerato dal backend
>   di MF (prerequisito già noto); i due file nuovi non passano il controllo dei tipi fino alla cura.
>
> **Cura, il modulo puro ✅** (13:2x): `frontend/src/lib/utils/rangeChange.ts` (`EARLIEST_RANGE_START`, `RangeDelta`,
> `ratioToPercent` spostata qui, `rangeStartFor` col calendario, `assetRangeDelta`, `fxRangeDeltas`): `rangeChange.test.ts`
> **83/83**, Prettier pulito. Due copie di `ratioToPercent` finché `periodChanges.ts` non la riesporta (lotto A, dopo
> X-R60). Il resto del lotto A aspetta X-R60 e l'ingresso di X-R59 di MF.

## X-R59, lotto B — la pagina dell'asset (dalle 13:21; HEAD `c4fe7cfb1`)

> **Coordinatore (13:20)**: checkpoint del lotto A sul mio ramo, non per dev (`c18deef09` test e modulo, `c4fe7cfb1` diario);
> dev entrerà nel ramo con X-R60 e X-R59 di MF. Dice a X di non spostare `ratioToPercent`.
>
> **Coordinatore (13:21)**: mentre il lotto A aspetta, **i rossi del lotto B**. Contratto (MF): `/prices/current?range_start=
> &target_currency=` con `range_change`; un cambio mancante dà una variazione nulla; un riferimento prima del 1900 è
> tagliato. Rossi Vitest per `assetDetailLive` e la Δ derivata della pagina, con risposte finte (nessuna dipendenza dal
> client generato); commit a un confine di passo. Se avanza tempo prima degli ingressi: **Y-31** (minima).
> - Il ramo di MF (`f252acb4a`) non ha ancora `target_currency` su `/current`: vale il contratto del coordinatore; i test
>   usano risposte finte. Le istantanee «copilot checkpoint» di altre sessioni non le leggo.
>
> **Contratto del lotto B** (proposto, da fissare nei rossi): `AssetDetailLiveInput.rangeStart?` (facoltativo: le fixture
> esistenti restano valide); stato `rangeDelta: RangeDelta | null`, azzerato a ogni giro dell'effetto, scritto nello stesso
> passo di `currentPrice` (`assetRangeDelta(range_change)`; nessuna variazione senza `range_start` o con la conversione
> fallita); la chiamata `([id], {queries: {range_start, target_currency?}})`, esattamente `([id])` senza inizio;
> `resetPrice()` la azzera. Modulo nuovo `assetDetailRangeChange.ts`: `summaryRangeDelta(liveShown, live, series)` (mai la
> Δ della serie accanto a un prezzo live) e `fetchSeriesRangeDelta({assetId, asOf, dateStart, targetCurrency?})` (una voce
> di `period-changes`). Il test nuovo va in `_frontend_asset.py` (non in `_frontend_utility.py`, file del programma colori).
>
> **Lotto B, rossi ✅** (`test-author` `b4d8d984`, 13:2x–13:4x; log `files/logs/xr59b_*.json`):
> - `assetDetailRangeChange.test.ts` (nuovo, 25 test: 7 `summaryRangeDelta`, 18 `fetchSeriesRangeDelta`): non si raccoglie
>   (modulo mancante).
> - `assetDetailLive.svelte.test.ts`: 127 test, **50 rossi** nuovi (l'effetto 13, la richiesta del poll 14, cosa scrive un
>   poll 22, `resetPrice()` 1), tutti su asserzioni; i **77 esistenti verdi**. Il getter `rangeStart` è definito solo
>   quando un caso passa la chiave: il test esistente che fissa le cinque letture dell'effetto resta verde anche dopo la
>   cura; il nuovo fissa le sei letture per una pagina che passa `rangeStart`.
> - Registrazione: `assetDetailRangeChange.test.ts` in `_frontend_asset.py` (`asset-unit`, aggiunta approvata), non in
>   `_frontend_utility.py`.
> - Dubbi del test-author, per la cura: riformulare «nothing else» di `resetPrice()` (docblock e titolo esistenti); serve la
>   versione di MF con `target_currency` su `/current` e un `api sync`; le query confrontate in modo stretto (mai una chiave
>   `undefined`); `rangeStart` catturato dall'effetto, non riletto dal poll; **`fetchSeriesRangeDelta` riceve la valuta di
>   visualizzazione solo quando il grafico è davvero convertito** (con `fxConversionMissing` niente `target_currency`, o la
>   Δ sparirebbe per ogni asset senza la coppia); la Δ si spegne per una richiesta al cambio di valuta o di intervallo; la
>   conversione del prezzo live resta del client (data UTC) mentre la Δ è del backend.
>
> ### Lotto B rossi — checkpoint 🧊 FROZEN (13:4x)
>
> **Coordinatore (13:36)**: rossi del lotto B committati (`d4a31ef29`, solo il ramo). Y-31: sì allo spostamento di
> `resolveUiLocale` in `uiLocaleRule.ts` (riesportato) e a `data-state` su `LotWacPriceChart`.

## Y-31 · la regola M-18 ricopiata in una spec, e due stati non pubblicati — versione minima (13:21–13:56; HEAD `d4a31ef29`)

> - **Rossi** (`test-author` `b73cf952`, quello di J-12): `uiLocale.test.ts` +2 (il modulo della regola non importa nulla,
>   letto col compilatore TypeScript, con un controllo che lo scanner trovi l'import di `./language` in `uiLocale.ts`;
>   `uiLocale` riesporta la stessa funzione) → 2 rossi (modulo mancante), 31 verdi; `brokers-detail.spec.ts`:
>   `dayAsThePanelWritesIt` importa `resolveUiLocale` per percorso, legge `<html lang>` e `navigator.language`, calcola la
>   lingua in Node e scrive il giorno nella pagina (un'annotazione registra lingua → tag → locale); J12-1 legge
>   `data-state="drawn"` invece della tela.
> - **Cura**: `frontend/src/lib/stores/app/uiLocaleRule.ts` (nuovo, senza import: `LANGUAGE_DEFAULTS`, `canonicalTag`,
>   `resolveUiLocale`); `uiLocale.ts` lo importa e lo riesporta; `LotWacPriceChart.svelte` `data-state={showChart ? 'drawn'
>   : 'empty'}` sulla radice (`showChart` è esattamente il contrario del messaggio «nessun dato»).
> - **Documentazione** (`docs-writer` `dd486281`): `developer/frontend/i18n.md:232-235` (dove vive la regola e perché senza
>   import); `components/features/lots-analysis.md:195` (`data-state` nella riga di `LotWacPriceChart`).
> - **Prove**: `uiLocale.test.ts` **33/33**; `tsc -p tsconfig.e2e.json` 0 errori; Prettier, `theme-roles --check`, `git diff
>   --check` puliti; svelte-check: i soli 36 errori dei tre file rossi di X-R59 (attesi fino alla loro cura). Slot
>   `front-broker detail` (`files/scripts/y31_e2e.sh`, carico a 5 minuti 30.41): **40/40** in 1,8 min, J12-1 e J12-2
>   compresi; porta 6189 libera. `mkdocs build` (strict) rc 0, 0 WARNING; `check-links` **97**.
> - **Resta, da girare a W**: il segno durevole della riga di `?highlight=` (pagina delle transazioni).
>
> **Coordinatore (13:5x)**: X-R59 di MF (con SEC9-1, lo 0 finale, D1 `target_currency` su `/prices/current`) e X-R60 sono in
> dev (`482343eb3`): dopo il commit di Y-31, dev entra nel mio ramo per i lotti A e B.
>
> ### Y-31 — checkpoint 🧊 FROZEN (13:5x)

## X-R59, la cura dei lotti A e B (dalle 13:57; HEAD `44873e1d1`)

> **Coordinatore (13:56–13:57)**: X-R64 di X entra per primo oggi e avvolge gli invii dei due fetcher (e di
> `livePriceService.fetchCurrentPrices`) in `sendBulkBatches`: nei fetcher tocco solo il costruttore delle voci
> (`range_start`) e il lettore del risultato (`range_change`). Y-31 committata (`bb9ed5800`) ed entrata in dev come pick
> (`8aa8a821e`); dev entrata nel mio ramo (`44873e1d1`): X-R59 di MF (con SEC9-1, lo 0 finale, D1) e X-R60. Il segno della
> riga di `?highlight=` va a W.
>
> - `dev.py api sync` (file ignorati): il client ha `range_change`, `range_start` e `target_currency`.
> - **⚠️ Fuori pista (X-R60)**: `periodChanges.ts` ha ora `PeriodChangesLedger` (quale risposta tenere; con un errore
>   tiene i valori calcolati fino allo stesso `as_of`). Per la Δ sull'intervallo non basta: dipende anche da `range_start`.
>   Quindi **un secondo ledger per pagina**, con la chiave dell'intervallo intero (`start…end`), riempito dalla stessa
>   risposta: con un errore restano solo i valori dello stesso intervallo; `periodChangesLoading` = l'uno o l'altro occupato.
>
> **Lotto A, cura ✅**:
> - `periodChanges.ts`: `ratioToPercent` riesportata da `rangeChange.ts` (la copia tolta); i due fetcher col terzo
>   argomento `rangeStart` (solo il costruttore delle voci e il lettore del risultato: `rangeDeltaByAssetId`,
>   `rangeDeltasByPair`). I due `toEqual` dell'elenco vuoto di `periodChanges.test.ts` adattati alla forma nuova (una chiave
>   in più, vuota: adattamento meccanico, nessuna asserzione nuova).
> - `assetPriceDerived.ts`: `computeDerivedPriceState` senza Δ (`DerivedPriceState` = `lastPrice`, `chartData`);
>   `fxStoreRegistry.ts`: `displayFxDelta` tolta.
> - Lista asset: `rangeDeltas` + `rangeDeltaLedger`; `loadPeriodChanges` manda `dateStart`; le card leggono la mappa
>   (`asset-range-delta`, `data-mode`); via i campi morti `deltaAbs`/`deltaPercent` di `AssetState` e `AssetRow`.
> - Lista cambi: lo stesso, chiave `BASE/QUOTE`, anche nella richiesta di una coppia (`loadPairPeriodChanges`);
>   `FxTable.getDelta()` sceglie diretto/inverso con `isCardInverted` (come oggi); `FxCard` prende `rangeDeltas` e sceglie
>   col suo `inverted` (`fx-range-delta`).
> - Pagina della coppia: `$effect` sulla coppia canonica e l'intervallo, più `rangeDeltaRefresh` (dopo `handleRefresh`,
>   la sincronizzazione alla creazione, il cambio di sessione), `pageBusy` `fx-detail-range-delta`; una Δ di un altro
>   intervallo è tolta subito; `fx-price-summary-range-delta`.
> - Prove (`files/scripts/xr59a_light.sh`): `rangeChange` 83, `periodChanges.rangeChange` **28** (i 26 rossi verdi),
>   `periodChanges` 63, `assetPriceDerived` 13, `fxStoreRegistry` 97, worker 2 + 5, `AssetTable` 12 + 2, `themeRoles.gate`
>   80, `financialMathExceptions.gate` 19; `theme-roles --check`, `git diff --check` puliti.
>
> **Lotto B, cura ✅**:
> - `assetDetailRangeChange.ts` (nuovo): `summaryRangeDelta`, `fetchSeriesRangeDelta`.
> - `AssetDetailLive`: `rangeStart?`, `rangeDelta` (azzerato a ogni giro dell'effetto), le query
>   `{range_start, target_currency?}`, la Δ scritta col prezzo (nessuna con la conversione fallita), `resetPrice()`.
> - Pagina dell'asset: `liveShown`; `seriesRangeDelta` con `$effect` (asset, intervallo, valuta convertita solo senza
>   `fxConversionMissing`) e `seriesRangeDeltaRefresh` (ricarica intera, `handleRefresh`), `pageBusy`
>   `asset-detail-range-delta`; `deltaPercent`/`deltaAbs` = `summaryRangeDelta(...)`; `rangeStart` passato al controllo
>   live; via il calcolo nel browser. `AssetPriceSummary`: `asset-price-summary-range-delta` e `…-abs`.
> - Prove: `assetDetailRangeChange` **25/25**, `assetDetailLive.svelte` **127/127** (i 50 rossi verdi); svelte-check
>   **0/0** per i due lotti (dopo un `$derived.by`: TypeScript rifiuta `live`, dichiarato più in basso, in un `$derived`
>   semplice); Prettier pulito.
>
> In corso: E2E del lotto A (`asset-list`, `fx-list`, `fx-detail`) e del lotto B (`asset-detail`, test `X-R59…`), scritte
> dai `test-author`; documentazione del lotto A (le frasi di MF «the web app is to send…»).
>
> **Documentazione ✅** (`docs-writer` `e7c6c482`, due giri): `backend/assets/architecture.md` `:379-391` e `:496-503`,
> `backend/fx/architecture.md` `:240-248`, `backend/financial_math.md` `:145-146` (solo quella frase, pagina condivisa):
> il web app ora manda `range_start` e legge `range_change` (liste, coppia, pagina dell'asset coi due endpoint), via le frasi
> «is to send… does not yet». `mkdocs build` (strict) rc 0, 0 WARNING; `check-links` **97** (`files/scripts/xr59_docs_check.sh`).
>
> **E2E del lotto A, scritta** (`test-author` `4b22e62a`, non lanciata; `tsc -p tsconfig.e2e.json` e Prettier puliti): 12
> test in tre describe «… (X-R59)» — `asset-list.spec.ts` 3, `fx-list.spec.ts` 4, `fx-detail.spec.ts` 5: la richiesta porta
> `range_start` (anche 1899-12-01 → 1900-01-01), la risposta modificata (`route.fetch()`) con valori inconfondibili si vede
> sulla card, nelle colonne Δ Abs / Δ %, nel riassunto della coppia, l'inverso dopo lo scambio; tutti i campi null → nessuna
> Δ, dopo una barriera.
> - **⚠️ Fuori pista**: i test id `fx-card-range-delta` e `asset-card-range-delta` cominciavano col prefisso delle radici
>   delle card (`fx-card-{slug}`, `asset-card-{id}`), che `fx-list.spec.ts` (`:37`, `:65`, `:86`, `:97`, «reset filters
>   restores all cards» con `toHaveCount(totalBefore)` esatto) e `fx-bulk.spec.ts:153` contano: la Δ arriva dopo, quindi il
>   conto dipenderebbe dai tempi. Rinominati **`fx-range-delta`** e **`asset-range-delta`** nei componenti e nelle due spec.
>
> **E2E del lotto B, scritta** (`test-author` `19628900`, non lanciata; `tsc -p tsconfig.e2e.json` e Prettier puliti): 4 test
> in fondo a `asset-detail.spec.ts`, describe «… (X-R59, lot B)», sull'asset sintetico `mockCacheHitEventsAsset` (niente
> scritture): intervallo che finisce prima di oggi → Δ di `period-changes` con `range_start` e nessun poll; senza provider →
> Δ della serie, poi un Refresh con `range_change` tutto null → nessuna Δ; intervallo fino a oggi con quotazione → il poll
> porta `range_start` e il riassunto mostra la Δ della quotazione, non quella della serie; GBP con la coppia configurata →
> `target_currency` nelle due richieste, JPY senza coppia → in nessuna. Barriera: le risposte di `period-changes` e
> `asset-detail-refresh-btn` a `data-busy="false"` (la Δ della serie è sotto `pageBusy.track('asset-detail-range-delta')`).
> - **⚠️ Fuori pista**: la query che il poll della pagina ora porta (`?range_start=`) fa saltare le mock con la glob esatta
>   `'**/api/v1/assets/prices/current'`: in Playwright 1.61 la glob è ancorata alla fine (`coreBundle.js:4560-4617`,
>   `globToRegexPattern` chiude con `$`; `urlMatches` prova l'URL intero). Il poll arriverebbe al provider vero e
>   scriverebbe la candela di oggi nel DB condiviso. Solo il poll della pagina cambia: quello della lista
>   (`fetchCurrentPrices`) non ha query. Il `test-author` allarga con un `*` finale le glob delle spec che possono aprire
>   `/assets/<id>` di un asset con provider su un intervallo fino a oggi; le corrispondenze per percorso (`page-busy`,
>   `risk-asset-detail`, `galleryReportSets`) vanno già bene. Per Y-32 (poll della lista con `range_start`) annotato nel
>   backlog che allora toccherà alle spec della lista.
>
> **Le glob allargate** (`test-author` `19628900`, secondo giro; un carattere per riga, nessuna riga spostata): 13 delle 32
> righe che nominano `prices/current` nelle E2E prendono il `*` finale (`'**/api/v1/assets/prices/current*'`, verificato col
> compilatore di glob di Playwright: con e senza query, rifiuta `…/current/x`). Sono quelle dove un test può aprire
> `/assets/<id>` di un asset con provider su un intervallo fino a oggi: `asset-detail` `:2338`, `:8234` (i 4 «Live price
> direction flash», che sarebbero diventati rossi), `:8448`, `:8700`, `:8765`; `toolbar-width-sweep:380`,
> `onboarding-guides:293`, `dashboard-cache:100`, `price-refresh-reload:158`, `asset-modal:656`,
> `asset-mobile-layout:629`, `asset-live-pause:115`, `asset-data-editor:605`. Le altre 13 restano (lista, o asset senza
> provider, o intervallo passato), 6 erano già per percorso. Tabella completa nel rapporto del `test-author`.
> - **⚠️ Fuori pista, P3**: le due `$effect` della Δ sull'intervallo (`asset-detail-range-delta`, `fx-detail-range-delta`)
>   chiamavano `pageBusy.track`. Ma `handleRefresh()`, che le rilancia, gira **senza** gettone dopo una sincronizzazione
>   (`handlePageSyncComplete()`, `handleFxPairCreationSynced()`, il completamento della creazione di una coppia FX): il
>   bottone avrebbe girato in un ricaricamento non chiesto, contro P3 e la regola «Never for» di `app-state.md#page-busy`.
>   Ora chiamano **`pageBusy.join`** (N55): gettone se la pagina lavora già (Refresh, periodo, cambio di asset, primo
>   caricamento dell'asset), nessuno su pagina ferma. Limite noto: nello stesso flush la mia `$effect` gira prima di quella
>   che apre `asset-currency` e, sulla coppia FX, prima di `onMount` con `fx-detail-first-load`; quei due caricamenti della
>   Δ trovano la pagina ferma e vanno senza gettone (il bottone può fermarsi un attimo prima della cifra). Le barriere delle
>   E2E aspettano comunque le risposte di `period-changes` prima di `data-busy="false"`.
> - **Riferimenti di `#page-busy`**: le mie modifiche spostavano 19 righe citate; il controllo per contenuto
>   (`files/scripts/y11_docrefs.py check`) ne trovava altre 15 già spostate da dev e dal pannello di J-12 (Dashboard +3,
>   `LotsAnalysisPanel` +19, `page-busy.spec.ts` +11/+59, le liste di asset e FX). Aggiornati tutti e 34 con
>   `files/scripts/xr59_pagebusy_refs.py` (sottostringhe esatte, una per riga, altrimenti si ferma), verificati riga per riga
>   sul codice (`files/logs/xr59_pagebusy_refs_verify.log`). La frase sul `join` della Δ la scrive `docs-writer` `e7c6c482`.
>
> **Checkpoint e merge (17/10, 15:10–15:20)**. Committati dal coordinatore `53fea97f7` (codice e doc), `ef005d68e`
> (test), `8c8025677` (giornale); `app-state.md` escluso, parcheggiato in `files/patches/xr59_app-state.patch` (dev
> l'aveva cambiato: sporco avrebbe fermato la merge). Merge di dev `79d4ca239` (X-R64) aperta dal coordinatore: un solo
> conflitto, `periodChanges.ts`. Risolto tenendo le righe di X (l'import di `sendBulkBatches`, l'invio a lotti con
> `inBatches`, l'unione delle risposte) e le mie nel builder (`range_start`) e nel mapper (`range_change`), col terzo
> parametro `rangeStart` e i due paragrafi dell'intestazione; nessun `ratioToPercent` doppio. Uniti da soli e riletti:
> `periodChanges.test.ts` (rispetto a dev solo le mie due righe della lista vuota; i test dei lotti di X leggono le
> chiavi una per una), le due `architecture.md` (solo i miei paragrafi; nessun «not yet» rimasto), il backlog (tutto dev
> più Y-32, una sola `## MF ·`).
> - Prove sulla revisione fusa: `api sync` rc 0; svelte-check 0/0; Prettier; `theme-roles --check`; Vitest **522/522** in
>   8 file (`periodChanges` coi test dei lotti, `periodChanges.rangeChange`, `rangeChange`, `assetPriceDerived`,
>   `fxStoreRegistry`, `assetDetailRangeChange`, `assetDetailLive`, `bulkBatches`); MkDocs strict rc 0, 0 WARNING;
>   `check-links` 97. MERGE READY mandato alle 15:19.
> - `app-state.md`: patch rimessa con `git apply` semplice (non `-3`, che mette nello stage), fuori dallo stage per il
>   commit dopo. La merge non tocca nessuno dei file citati in `#page-busy`, quindi i riferimenti restano validi.
> - **⚠️ Fuori pista**: `docs-writer` ha visto un terzo caso del limite del `join`. Sulla coppia FX, un cambio di coppia
>   rilancia la Δ (`fx/[pair]/+page.svelte:324`) prima dell'`$effect` che apre `fx-detail-orientation` (`:735-753`);
>   uno scambio della stessa coppia non la richiede (l'inverso si legge sul posto). Aggiunto alla frase del limite.
>
> **E2E sulla revisione fusa `3fda937e0` ✅ (17/10, 15:19–16:05; slot del coordinatore fino alle 16:15, corsia 6189,
> `--workers 2`; `files/scripts/xr59_e2e.sh`, log `files/logs/xr59_e2e_*.log`)**: **244/245**.
>
> | Spec | Esito | Cosa copre |
> |:--|:--|:--|
> | `front-portfolio dashboard-cache` | 6/6 | glob allargata (`:100`); guardia d'allargamento |
> | `front-asset asset-detail` | 38/39 | lotto B (4 nuovi), i 4 «Live price direction flash», chip del provider, C-66 |
> | `front-fx fx-detail` | 22/22 | lotto A sulla coppia (5 nuovi) |
> | `front-fx fx-list` | 22/22 | lotto A sulla lista FX (4 nuovi) |
> | `front-asset asset-list` | 37/37 | lotto A sulle card (3 nuovi) |
> | `front-portfolio page-busy` | 17/17 | il contratto del bottone, col `join` |
> | `front-asset live-pause` | 12/12 | glob allargata (costante) |
> | `front-portfolio price-refresh` | 8/8 | glob allargata (costante), Z-14 |
> | `front-asset asset-data-editor` | 27/27 | glob allargata (`:605`) |
> | `front-asset asset-modal` | 21/21 | glob allargata (`:656`) |
> | `front-asset asset-mobile-layout` | 21/21 | glob allargata (`:629`) |
> | `front-utility onboarding-guides [asset_detail_guide]` | 2/2 | glob allargata (`:293`) |
> | `front-utility toolbar-width-sweep [assetDetail]` | 4/4 | glob allargata (`:380`) |
> | `front-fx fx-bulk` | 7/7 | lista FX dopo il cambio di nome dei test id |
>
> - **Il rosso, `asset-detail:240` «edit button opens asset modal»**: `goToSeededAssetDetail()` aspetta 10 s la radice della
>   pagina dopo il clic sulla card di Apple, ed è caduto ancora sulla lista (istantanea salvata in
>   `files/logs/xr59_ad240_evidence/`: nessuna finestra aperta, card visibile con la sua Δ). Era tra i primi test, al picco di
>   carico dopo la build. **Rilanciato da solo a carico normale: verde in 4,1 s**
>   (`files/logs/xr59_e2e_rerun_ad240.log`); gli altri test con lo stesso aiuto sono passati. Verdetto (test-triage):
>   un'assunzione di tempo sotto carico, non X-R59. Backlog **Y-33**.
> - Dopo l'ultima frase di `docs-writer` (il terzo caso del limite): MkDocs strict rc 0, 0 WARNING; `check-links` 97.
> - Porta 6189 libera alla fine.
>
> **Ingresso di X-R59 (17/10, 16:08–16:22)**. All'ingresso dei lotti A e B si è messo in mezzo X-R58 di X: i toast per una
> richiesta troppo grande sulle liste, con E2E nuove (`asset-list` +1, `fx-list` +3). Il coordinatore ha aperto la merge
> di dev `15ae6f61e` nel mio worktree.
> - **⚠️ Fuori pista**: nelle due spec le due sezioni nuove (la mia X-R59 e la X-R58 di X), entrambe aggiunte in fondo,
>   git le aveva intrecciate sulle righe comuni (`configure`, `beforeEach`, le chiusure). Ricostruite con
>   `files/scripts/xr58_rebuild.py`: la parte unita (uguale a quella di dev: la mia più gli import di X), poi la sezione
>   X-R59 intera da HEAD, poi la X-R58 intera da dev. Nessun nome di primo livello doppio, nessun marcatore rimasto;
>   `asset-list` 38 test, `fx-list` 25. Le due pagine, unite da sole, sono l'unione pulita (rispetto a HEAD solo X-R58,
>   rispetto a dev solo il lotto A).
> - Prove: `api sync` (serviva: svelte-check dava 1 errore in `UsersTab.svelte:174`, il campo `cancel_setup` di A-51 col
>   client vecchio), svelte-check 0/0, Prettier e `tsc` delle E2E puliti, Vitest 581/581 in 9 file (con `bulkRefusal`);
>   E2E `asset-list` 38/38 e `fx-list` 25/25 (16:13–16:21). Entrato: dev `f317e3a9f` (merge `0e995b428`), CHANGELOG 🔄
>   `763d94b87`.

## J-53 · Il banner dei lotti: ogni fondo orfano con il suo importo e la sua data (17/10)

Voce di J (analisi di J-36), titolare Y per decisione del coordinatore; cura decisa: una riga per issue per i codici senza
lotto, nessun totale dal backend (valute diverse, date perse). Base `763d94b87`.

**Stato reale.** `buildIssueGroups` (`lotDataQualityHelpers.ts:83`) raggruppa per codice e tiene i parametri della prima
issue; i chip vengono dai `lot_id` visibili. Il backend mette `lot_id: null` su ogni issue senza lotto
(`lots_analysis_service.py:1150-1162`). Nel banner (fuori da `FAILED`) arrivano senza lotto: i due codici orfani, uno
per fondo (`engine.py:899-913`, `:1015-1029`); `CURRENT_PRICE_ASSUMED_AT_COST`, uno; le issue FX di `_report_gaps`, fino a
due `MISSING_FX_RATES` (`missingFxRates`, le coppie con provider e il loro intervallo, e `missingFxRatesManual`) col
numero di coppie, senza la chiave `lot_id` (stesso difetto: la seconda si nascondeva dietro la prima); `MISSING_COST_BASIS`,
una. I quattro codici del rigioco vanno nella notice di J-12.

**Forma (decisione mia, nel perimetro; mandata al coordinatore).** Un blocco per codice, come oggi (chiave
`group.code`, test id `lot-data-quality-issue-{code}`, conteggi dell'intestazione per categoria), con dentro **una riga
per issue senza lotto**, coi suoi parametri, nell'ordine dell'input; due issue identiche fanno una riga sola. Le issue con
lotto restano una riga (i parametri della prima) più i chip. Perché non righe di primo livello: il localizzatore stretto di
`data-quality-real.spec.ts:479` e la chiave dell'`{#each}` (`each_key_duplicate`) vogliono un elemento per codice.

**Passi.**
1. Rossi (`test-author`): `lotDataQualityHelpers.test.ts` (in `core-unit`; adattati i test che leggevano
   `messageParams`), più il test di componente nuovo `LotDataQualityBanner.test.ts` (riga aggiunta in
   `_frontend_broker.py`, `front_broker_unit`, OK chiesto).
2. Cura: `IssueGroup.messages` in `lotDataQualityHelpers.ts`; il banner disegna le righe (`lot-data-quality-message`),
   nessuna classe nuova.
3. Documentazione (`docs-writer`): `backend/transactions/lots_analysis_service.md:600`,
   `frontend/components/features/lots-analysis.md`.
4. Prove leggere; slot E2E corto: `front-portfolio data-quality-real`, `data-quality-legacy`, `front-broker detail`.
5. CHANGELOG 🐛 nel messaggio; la riga J-53 del backlog (sezione di J) la chiude il coordinatore.

**Avanzamento.**
1. ✅ 17/10 — **Rossi** (`test-author` `5749c9f8`). `lotDataQualityHelpers.test.ts`: 3 test adattati a `messages` e il blocco
   «J-53» (20 test: due fondi di entrata, i fondi di costo accanto, le due `MISSING_FX_RATES`, `lot_id` null/assente/non
   numerico, il doppione, sei parametri che differiscono uno alla volta, un'altra chiave, i lotti visibili e nascosti, il
   codice misto in due ordini, le chiavi uniche, un gruppo per codice, l'ordine per gravità). `LotDataQualityBanner.test.ts`
   nuovo (jsdom, i18n vera): 4 test, due rossi sul difetto stesso («… 12.50 EUR on 2024-03-15 …» senza «30.75»). Riga
   aggiunta in `_frontend_broker.py` (`front_broker_unit`, OK del coordinatore). Rossi: 22 e 2; verdi gli altri 73 e 2.
   > **Note implementazione**: `check-orphans` pulito (548 file registrati). Log in `files/logs/j53-red-*.log`.
   > **⚠️ Fuori pista**: il `test-author` ha corretto la mia lettura delle issue FX (non una per coppia: fino a due
   > `MISSING_FX_RATES` con il numero di coppie, senza `lot_id`); corretta sopra, nello stato reale.
2. ✅ 17/10 — **Cura**. `lotDataQualityHelpers.ts`: `IssueMessage {key, messageKey, params}`, `IssueGroup.messages` al
   posto di `messageKey`/`messageParams`; in `buildIssueGroups` le issue su un lotto (`lot_id` finito, visibile o no)
   aprono una sola riga, la prima, e danno i chip come prima; ogni issue senza lotto aggiunge la sua riga, una sola per
   stessa chiave e stessi parametri (`messageIdentity`, chiavi ordinate); chiavi `code:lots` e `code:<indice>`.
   `LotDataQualityBanner.svelte`: un `{#each group.messages}` con `data-testid="lot-data-quality-message"`, le stesse
   classi di prima.
   > **Note implementazione**: Vitest dei due file 99/99; svelte-check 0/0; Prettier; `theme-roles --check` pulito;
   > `git diff --check` pulito. Nessun altro lettore di `messageKey`/`messageParams` del gruppo.
3. ✅ 17/10 — **Documentazione** (`docs-writer` `f90771f4`): `backend/transactions/lots_analysis_service.md` (`:600`, più
   `:400` che diceva «un messaggio per codice»), `frontend/components/features/lots-analysis.md` (voce dell'ordine di
   disegno, riga della composizione, sezione «LotDataQualityBanner», riga dei test id), `user/dashboard/positions.en.md:207`
   (entrate e costi che nessun lotto ha preso, ognuno col suo importo e la sua data). MkDocs strict rc 0, 0 WARNING;
   `check-links` 97.
   > **⚠️ Fuori pista**: `positions.en.md` non timbrata: IT/FR/ES erano già indietro (righe 50, 57, 58 dell'inglese) e la
   > frase è nuova. Debito di traduzione, sezione «🧾 5. Lot Detail» → «⚠️ When the panel warns you»; si timbra quando le
   > quattro lingue tornano allineate.
4. ✅ 17/10 — **E2E** (`files/scripts/j53_e2e.sh`, corsia 6189, 16:53–17:08, prima spec dopo il carico a 5 minuti sotto
   50): `front-portfolio data-quality-real` 3/3, `data-quality-legacy` 1/1, `front-broker detail` 40/40. Porta libera.
5. ⏳ CHECKPOINT READY al coordinatore, con la riga 🐛 del CHANGELOG; la riga J-53 del backlog la chiude lui.
> **J-53 entrato** (17/10, 17:11): dev `fb6d58d17` (`c37c2bb1e`); CHANGELOG 🐛 e la riga J-53 chiusa in `38be2102b`. J
> rilegge `lots_analysis_service.md` dopo, su richiesta del coordinatore.

## Y-33 · `asset-detail.spec.ts`: la navigazione a freddo sotto carico (17/10)

Voce mia (slot E2E di X-R59); review di X. Base `38be2102b`.
- **Il difetto**: `goToSeededAssetDetail()` (`frontend/e2e/assets/asset-detail.spec.ts:107-114`, 28 chiamate) clicca la card
  di Apple e dà 10 s alla radice `asset-detail-page`. Al picco di carico dopo la build un contesto nuovo importa a freddo il
  bundle della pagina: «edit button opens asset modal» (`:240`) è caduto ancora sulla lista; da solo, verde in 4,1 s.
- **La cura (forma decisa)**: dopo il clic, prima l'URL (`toHaveURL(/\/assets\/\d+(?:\?|$)/)`, tetto 30 s, messaggio che
  dice «il clic sulla card porta alla pagina dell'asset»), poi la radice a 10 s come oggi. Nessun nuovo clic: un clic
  perso deve fallire, e sul messaggio dell'URL.
- **Passi**: 1. `test-author` scrive la riparazione (nessuna run); 2. prove leggere (`tsc` delle E2E, Prettier); 3. slot:
   `front-asset asset-detail`; 4. CHECKPOINT READY, review di X.

**Avanzamento.**
1. ✅ 17/10 — **Riparazione** (`test-author` `b9253145`, due giri): `goToSeededAssetDetail()` divide l'attesa (URL 30 s, poi
   la radice 10 s, ognuna col suo messaggio; paragrafo Y-33 nel docblock: in SvelteKit l'URL cambia dopo l'import del chunk
   della rotta, `client.js:1568`, `:1685-1686`, `:1739`); lo stesso passaggio in riga del test della cache degli eventi
   (`:8570-8577`, l'URL del suo asset); il commento di `:332` («~40 s») riscritto senza totali. +14/−3.
   > **Note implementazione**: `tsc -p tsconfig.e2e.json` e Prettier puliti; `git diff --check` pulito.
   > **⚠️ Fuori pista**: il timeout di default dei test (30 s, `playwright.config.ts:113`) fa da tetto anche all'attesa
   > dell'URL nei test che non lo alzano; lasciato così (il guasto visto era l'attesa di 10 s), detto a X per la review.
2. ✅ 17/10 — **E2E** (`files/scripts/y33_e2e.sh`, slot del coordinatore dalle 17:32, dopo B; partita alle 17:33 col carico
   a 5 minuti sotto 50): `front-asset asset-detail` **39/39** in 3,5 min, fine alle 17:42. Porta 6189 libera.
3. ⏳ CHECKPOINT READY al coordinatore (la spec e il giornale); review di X. Y-33 ✅ nel backlog.
> **Y-33 entrato** (17/10, 17:43): dev `c5b347a46` (`dc6e8aba7`); review di X dopo.

## Y-24 · Candele e contributo: dopo un errore, al più tre nuove richieste (17/10)

Proposta di Y (la voce più utile senza decisioni della sezione), via del coordinatore alle 17:47: «at most 3 automatic
retries at 2/4/8 s, reset on a scope change or a Refresh; no UI change». La parte UX (l'indicatore e lo stato d'errore
delle candele) resta con Y-18, al developer. Nessun'altra worktree ha le due pagine, `GrowthChart`, `PositionsPanel` o
`stores/portfolio/` (coordinatore). Base `c5b347a46`.

**Stato reale (verificato).** Quattro caricatori pigri fanno lo stesso giro: Dashboard (runes) `loadPnlCandles`
(`dashboard/+page.svelte:676-687`) e `loadContribution` (`:637-665`); pagina del broker (legacy: `export let data`, `$:`)
`loadPnlCandles` (`:354-364`) e `loadContribution` (`:366-375`). Se il report fallisce `requestReport` dà `null`
(`portfolioStore.svelte.ts:345-347`), il `finally` rimette `loading` a false e l'`$effect` che chiede (`GrowthChart.svelte:980-984`,
`PositionsPanel.svelte:112-116`) lo legge e riparte: una richiesta dopo l'altra, senza pausa, ognuna un report intero (per
le candele il calcolo OHLC). Un successo non fa il giro: `get_pnl_candles` dà una serie vuota, mai `None`
(`portfolio_service.py:1254+`). Sulla pagina del broker, legacy, i `let` riassegnati sono segnali: il giro c'è anche lì.

**Contratto.** `lib/stores/portfolio/lazyReportRetry.svelte.ts`: `createLazyReportRetry(delaysMs = [2000, 4000, 8000])` →
`canAsk(scope)` (lettura reattiva: un tick `$state` sveglia l'effetto quando scade un nuovo tentativo, e dopo `reset()`),
`failed(scope)`, `succeeded(scope)`, `reset()`, `dispose()`. Al più 4 richieste per ambito (la prima e 3 tentativi, a 2, 4 e
8 s da ogni errore), poi più nessuna finché cambia l'ambito (broker|inizio|fine|valuta) o arriva un Refresh. Nessun
orologio letto: lo stato «scaduto» viene dal timer.

**Passi.**
1. Rossi (`test-author` `73198f94`): unità `lazyReportRetry.svelte.test.ts` (in `store-unit`); E2E nuova
   `e2e/portfolio/lazy-report-retry.spec.ts` (azione `front-portfolio lazy-report-retry`), con l'orologio di Playwright:
   candele della Dashboard (niente tempesta, 4 al più, un cambio di periodo richiede), recupero, contributo con Refresh,
   candele della pagina del broker.
2. Slot corto: l'E2E rossa sul codice di oggi (la prova che morde).
3. Cura: il modulo; i quattro caricatori (guardia `canAsk`, dopo l'attesa `succeeded`/`failed` sullo stesso ambito); i due
   Refresh chiamano `reset()`; `dispose()` alla distruzione; il commento di `GrowthChart.svelte:979`.
4. Documentazione (`docs-writer`); prove leggere; slot: l'E2E nuova più `page-busy`, `dashboard`, `dashboard-cache`,
   `front-broker detail`.
5. CHECKPOINT READY con la riga 🐛 del CHANGELOG e la pulizia del giornale (Y-5…Y-22 ✅, già fatta).

**Avanzamento.**
1. ✅ 17/10 — **Rossi** (`test-author` `73198f94`): `lazyReportRetry.svelte.test.ts`, 20 test (il calendario 2/4/8 s, lo
   sfinimento, un altro ambito, `succeeded`, `reset`, `dispose`, l'effetto svegliato anche se ha letto `canAsk` una volta
   sola prima di ogni errore, nessun orologio letto); rossi: il modulo non esiste. E2E `lazy-report-retry.spec.ts`, 5 casi con
   l'orologio di Playwright (candele della Dashboard, recupero, contributo con Refresh, candele e contributo della pagina
   del broker); conteggi dalla rotta e dalla pagina. Runner: il file in `store-unit`, l'azione `lazy-report-retry`.
   `tsc` delle E2E, Prettier, `check-orphans` puliti.
   > **⚠️ Fuori pista**: sulla pagina del broker le **candele** oggi non fanno il giro: `pnlCandlesLoading` è un `let`
   > che il template e i `$:` non leggono, quindi Svelte 5 legacy non lo rende reattivo (verificato dal `test-author`
   > compilando la pagina). Dopo un errore nessun nuovo tentativo: una richiesta, poi niente. Il **contributo** invece fa il
   > giro. La cura copre i due: `canAsk` registra il lettore in ogni stato, così il timer sveglia anche un effetto che l'ha
   > letto una volta sola. Il caso (d) dell'E2E sarà rosso sul tentativo che non arriva.
2. ✅ 17/10 — **E2E rossa sul codice di oggi** (slot 18:30–18:36, `files/scripts/y24red_e2e.sh`): 5/5 rossi, ognuno per il
   motivo giusto — candele della Dashboard 6 richieste a orologio fermo (attesa 1), recupero un nuovo tentativo immediato,
   contributo della Dashboard 5, candele della pagina del broker il tentativo a 2 s mai arrivato, contributo della pagina del
   broker 4. Log `files/logs/y24red_e2e_*`.
3. ✅ 17/10 — **Cura**. `lib/stores/portfolio/lazyReportRetry.svelte.ts` (unità 20/20 al primo colpo). Dashboard e pagina
   del broker: due retry (candele, contributo), `reportScope()` (broker|inizio|fine|valuta), la guardia `canAsk` letta
   prima del primo `await`, l'esito registrato prima del `finally`, la risposta di un altro ambito scartata; il Refresh
   (`handleSync`, `handleRefresh`) chiama `reset()`; `dispose()` in `onDestroy`. Commento di `GrowthChart.svelte:979`.
   > **Note implementazione**: Vitest 239/239 (il modulo, `portfolioStore`, `portfolioMutation`, i due `GrowthChart`);
   > svelte-check 0/0; `theme-roles --check`, Prettier (formattato il modulo), `git diff --check` puliti.
   > **⚠️ Fuori pista**: la risposta delle candele di un ambito già cambiato prima si applicava comunque (Dashboard e
   > pagina del broker); ora si scarta, col controllo che serve anche per contare l'errore. Le modifiche spostano i
   > riferimenti di riga di `app-state.md#page-busy` nelle due pagine: da riallineare dopo la documentazione.
4. ✅ 17/10 — **Documentazione** (`docs-writer` `e3986f2f`): `domain-state.md` (riga della tabella degli store, sezione
   «Lazy sections after a failure», `#lazy-report-retry`), `app-state.md` (la frase del `join`: di norma a pagina ferma),
   `components/charts.md` (le Candele), `pages/index.md`, `backend/transactions/price_resolver.md`; riallineati i
   riferimenti di riga spostati dalla cura in `app-state.md`, `risk-lab.md` (anche quelli già vecchi prima) e
   `backend/risk/architecture.md:24` (controllato a occhio: `1101-1110`); corretti i quattro percorsi vecchi della
   tabella degli store di `domain-state.md` (lotti, dashboard, rischio, transazioni: le mie mosse di cartella).
5. ✅ 17/10 — **Verdi e regressioni** (slot 18:42–19:11, `files/scripts/y24green_e2e.sh`): `lazy-report-retry` 5/5,
   `page-busy` 17/17, `dashboard` 27/27, `dashboard-cache` 6/6, `front-broker detail` 40/40. Porta libera.
   > **⚠️ Fuori pista — un buco della cura, trovato da `docs-writer` leggendo il codice**: sulla pagina del broker
   > `pnlCandlesLoading` è un `let` che il compilatore legacy non rende segnale, e la guardia esce su di lui prima di
   > `canAsk`. (f) Un cambio di periodo con la richiesta delle candele in volo: la risposta vecchia scartata, nessuno
   > sveglia l'effetto, le candele del periodo nuovo mai chieste (regressione della correzione sulle risposte scadute);
   > (g) uscire dalle Candele e rientrare con la richiesta in volo che poi fallisce: il tentativo a 2 s non arriva. La
   > Dashboard no (il suo flag è `$state`). Prova col compilatore (`files/y24_probe*.svelte`, `files/y24_probe.mjs`):
   > con `$: void pnlCandlesLoading;` il flag diventa `$.mutable_source` e la guardia lo legge con `$.get`.
6. ✅ 17/10 — **Il buco, chiuso** (slot 19:17–19:34). Rossi (f) e (g) (`test-author` `73198f94`, secondo giro) visti sul
   codice di prima: «le candele del periodo nuovo mai chieste» e «il tentativo a 2 s mai mandato»; gli altri 5 verdi.
   Correzione, solo nella pagina del broker: `$: void pnlCandlesLoading;` (il flag diventa un segnale, come sulla
   Dashboard) e `canAsk` letto prima delle altre guardie nei due caricatori. Poi `lazy-report-retry` 7/7, `front-broker
   detail` 40/40; svelte-check 0/0; Prettier pulito. Riferimenti di riga della pagina del broker riallineati
   (`files/scripts/y24_brokerrefs.py`, istantanea → oggi): 9 nei backtick in `app-state.md` e `risk-lab.md`, più
   `(l.751)`/`(l.753)` → `(l.759)`/`(l.761)` a mano in `risk-lab.md:265`; tutti verificati sul codice.
7. ⏳ CHECKPOINT READY con la riga 🐛 del CHANGELOG; Y-24 ✅ nel backlog (la parte del giro), il resto con Y-18.
> **Y-24 entrato** (17/10, 19:48): dev `ad5104c4f` (prove combinate verdi sull'albero fuso), CHANGELOG `c1bdc380b`.
> Review a posteriori fatte nel frattempo: C-97c-3 parte DV (OK, una nota su una copia di formato in 5 componenti) e J-21
> lato renderer (OK, una nota: le sequenze di un output con molti `null` non hanno tetto; J la verifica con un rosso).

## Y-34 · `brokers-detail.spec.ts`: il pannello dei lotti sotto carico, più la nota di X su Y-33 (17/10)

Voce di gate I, via del coordinatore; review di X. Base `ab74aafbf`.
- **Il difetto**: 12 test di `brokers-detail.spec.ts` aspettano 5 s `lots-analysis-panel` dopo «analizza i lotti» (`:314`,
  `:327`, `:355`, `:364`, `:380`, `:407`, `:431`, `:458`, `:497`, `:532`, `:555`, `:610`); `:355` è caduto una volta col
  carico vicino a 90. L'azione scrive `?asset=<id>` nell'URL, la pagina lo legge in un `$:` e monta il pannello sotto
  `{#if open && assetId != null}`: navigazione nella stessa rotta più montaggio.
- **La nota di X su Y-33**: i quattro test «Live price direction flash» di `asset-detail.spec.ts` (`:8265`, `:8279`,
  `:8316`, `:8351`) abbassano il timeout a 20 s, sotto il tetto di 30 s dell'URL di `goToSeededAssetDetail`.
- **La cura (forma decisa)**: in `brokers-detail.spec.ts` un aiuto, prima l'URL con `?asset=` (tetto 30 s), poi il
  pannello (10 s), per i 12 punti (e `:947`/`:2027` se sono la stessa sequenza); in `asset-detail.spec.ts` un
  `test.describe.configure({timeout: 60_000})` sul describe dei flash al posto dei quattro `setTimeout(20_000)`.
- **Passi**: 1. `test-author` (brief `files/y34_testauthor_prompt.md`); 2. `tsc` delle E2E e Prettier; 3. slot:
   `front-broker detail` e `front-asset asset-detail` (i flash); 4. CHECKPOINT READY, review di X.

**Avanzamento.**
1. ✅ 17/10 — **Riparazione** (`test-author` `f5f41fd9`, due giri). `brokers-detail.spec.ts`: `expectLotsPanelOpen(page,
   assetId?)` (URL con `?asset=` 30 s, poi il pannello 10 s, senza ripetere il clic) al posto delle 12 attese di 5 s;
   `expectLotsPanelClosed(page)` per la chiusura (`:352-353`: URL senza `?asset=`, poi il pannello nascosto); `:947`/`:2027`
   lasciate (deep link). `asset-detail.spec.ts`: `test.describe.configure({timeout: 60_000})` sul describe dei flash (al posto
   dei quattro `setTimeout(20_000)`) e sul describe `Asset Detail Page` (19 test col default di 30 s, che non arrivavano al
   tetto dell'URL; fra loro quello caduto in Y-33). Tutti i 27 chiamanti di `goToSeededAssetDetail` hanno almeno 60 s; i 13
   test del pannello stanno in describe da 60 s.
   > **Note implementazione**: `tsc -p tsconfig.e2e.json` e Prettier puliti; `git diff --check` pulito. Verdetto (test-triage):
   > un'assunzione di tempo.
   > **⚠️ Fuori pista**: allargato oltre la nota di X ai 19 test col default di 30 s e alla chiusura del pannello (stessa classe,
   > stessi due file). Residuo da instradare: `dashboard-cache.spec.ts:295` (`analyzeLots`), stessa classe con un'attesa sola.
2. ✅ 17/10 — **E2E** (slot 20:02–20:08, `files/scripts/y34_e2e.sh`): `front-broker detail` **40/40**, `front-asset
   asset-detail` filtrato su «direction» **5/5** (i 4 flash e un test veloce). Porta 6189 libera. Il coordinatore approva i 60 s
   sul describe `Asset Detail Page` e il residuo di `dashboard-cache.spec.ts:295` nella riga di Y-34.
3. ✅ 17/10 — CHECKPOINT READY (solo test e giornale, nessuna riga del CHANGELOG). Entrata in dev `7dbd46aa6` (`69b2fe74e` +
   `2abcb35d9`); X rivede a posteriori il parametro `assetId` di `expectLotsPanelOpen`.

## Y-30 · Con `FAILED` il grafico prezzo/WAC ritrova la linea del prezzo (17/10)

Voce del mio settore, nata «per J»: il coordinatore (20:11) la passa a Y, backend compreso, perché J è occupato e
`lots_analysis_service.py` e gli schemi dei lotti non sono aperti altrove; J rivede la parte backend. Base `7dbd46aa6`.
Analisi inviata alle 20:2x; via del coordinatore alle 20:3x.

**Decisioni** (coordinatore, 20:3x).
- **(a) sempre** (la mia raccomandazione): il pannello prende la linea del prezzo, le date dell'asse e le bolle dalla serie
  nuova, e non chiede più `PRICE_HISTORY`. Una fonte sola; la linea continua anche dove non c'è un lotto aperto, come le
  linee del costo medio. Il coordinatore la registra come decisione notturna **N89**, per il developer.
- **(b) nomi**: `MARKET_PRICE_HISTORY` / `market_price_history`; `_AVERAGE_COST_ANALYSES` → `_REPLAY_FREE_ANALYSES`.
- **Il test dei codici di J** (S7 di `test_lots_failed_analysis_withholding.py`) si estende al buco di cambio della serie
  con `FAILED`; J rivede la parte backend.
- **`data-price-line="drawn|absent"`** sul grafico: sì, letto nel passo 2 di J12-1.
- **CHANGELOG**: la riga 🔄 di J-12 («keeps only the average-cost lines») la corregge il coordinatore all'ingresso; la mia
  riga 🐛 va nel checkpoint. `api sync` va bene (additivo); `schemas/portfolio.py` cambia solo per aggiunta.

**Il contratto backend.**
- `LotAnalysisType.MARKET_PRICE_HISTORY`; `MarketPriceHistoryPoint` (`date`, `market_price`, `currency`, `estimated`), come
  `LotPriceHistoryPoint` senza `lot_id`; `LotsAnalysisResponse.market_price_history`, `None` se non chiesta.
- Un punto per ogni giorno dell'intervallo calcolato che ha un prezzo convertibile (`estimated_market_prices`: la
  quotazione o l'ultimo scambio, portati avanti, convertiti al cambio del giorno), qualunque lotto sia aperto e qualunque
  sia `selected_lot_ids`; tagliato a `[display_from, actual_to]` come le altre storie. Un giorno senza osservazione o
  senza cambio non ha punto; il cambio mancante va in `missing_fx_pairs` e nel suo avviso (DEGRADED se il replay è
  COMPLETE).
- Con `FAILED` resta (sta in `_REPLAY_FREE_ANALYSES`), con i suoi buchi di cambio nel data quality.
  `CURRENT_PRICE_ASSUMED_AT_COST` invece no: la serie non valuta nulla al costo, e l'avviso resta legato alle analisi che
  valutano i lotti (`needs_market_series`, invariata). Le esigenze di cambio della serie si registrano in
  `collect_fx_needs` anche quando la chiede da sola.
- `PRICE_HISTORY` per lotto resta nell'API: dopo Y-30 nessun lettore nell'app.
- AI Export: chiede solo `LOT_SUMMARY` (`asset_resources.py`, `payloads/portfolio_broker.py`): nessun cambio di
  contratto, nessuna versione.

**Il frontend.** `LotsAnalysisPanel` chiede `MARKET_PRICE_HISTORY` al posto di `PRICE_HISTORY` e la tiene anche con
`FAILED` (fuori da `lotSection`); `LotWacPriceChart` legge `marketPriceHistory` per la linea, le date dell'asse, il
riavvio della risoluzione, il conteggio dei punti e le bolle (prezzo all'apertura); l'unione per data dei punti per lotto
diventa un aiuto puro di `lotWacPriceChartHelpers.ts`, una data un punto; il grafico pubblica
`data-price-line="drawn|absent"`.

**Passi.**
1. ✅ 17/10 — **Reds backend** (`test-author` `y30-backend-reds`): 19 rossi, ciascuno per la ragione attesa (ValueError
   «'MARKET_PRICE_HISTORY' is not a valid LotAnalysisType», AttributeError, 422), più 4 guardie verdi.
   - File nuovo `test_financial/test_lots_market_price_history.py` (A1–A7 e una guardia sul per-lotto), il file di J
     (B1 `test_s1_s2_failed_analysis_keeps_the_market_price_line`, B2 `test_s7_failed_analysis_keeps_the_fx_gap_of_the_market_price_line`,
     una guardia senza la serie, THE RULE con un punto Y-30), `test_lots_analysis_pure.py` (C1 costruttore e schema, C2 il
     pavimento del 1900; `_sec8_analysis` con due argomenti opzionali), `test_portfolio_api.py` (D1 dopo l'ultima vendita).
   - Run (`files/scripts/y30_backend.sh`, TAG `y30_reds`): `roi-fifo-utils` 12 rossi + 27 verdi (i 18 di J verdi),
     `lots-analysis-pure` 6 rossi (198 col file intero, i 4 SEC8 verdi), `api portfolio` 1 rosso.
   > **Note implementazione**: niente riferimenti a livello di modulo ai nomi nuovi (la stringa nelle richieste); C1 legge
   > `histories_module.build_market_price_history` invece di un import locale (ruff PLC0415).
2. ✅ 17/10 — **Cura backend**: `LotAnalysisType.MARKET_PRICE_HISTORY`, `MarketPriceHistoryPoint`,
   `LotsAnalysisResponse.market_price_history`; `build_market_price_history` in `financial_math/lots/histories.py`;
   `_REPLAY_FREE_ANALYSES`; `daily_series` con la serie; `collect_fx_needs` registra i cambi anche per la serie da sola.
   - Verdi (TAG `y30_green`): `roi-fifo-utils` filtrato sui lotti (`market_price test_lots_ test_date_range_bounds
     test_orphan_transfer_after_broker_delete test_portfolio_cost_currency test_adjustment_out_with_cost_numbers`)
     **213/213**; `lots-analysis-pure` **198/198**; `financial-math` **1474/1474** (confini del livello compresi); `api
     portfolio TestLotsAnalysisEndpoint` **8/8**. Porta 6189 libera.
   - `ruff check` pulito sugli 8 file; `black --check` pulito tranne `test_portfolio_api.py`, già fuori formato a HEAD
     (dalla riga 1406, codice non nostro). `api sync` rc 0: il client generato (ignorato) ha il tipo nuovo; nessun file
     tracciato cambiato.
   > **Note implementazione**: `needs_market_series` resta com'è: decide anche `CURRENT_PRICE_ASSUMED_AT_COST`, che la
   > serie non deve sollevare (A6, S7 di J con `ALL_ANALYSES` che ora la contiene).
   > **Fuori pista**: da aggiornare in chiusura la devWiki (`entities/lots-analysis-service.md:93` cita
   > `_AVERAGE_COST_ANALYSES`; `decisions/fifo-v4-gross-net-status-model.md:89` dà Y-30 «per J»).
3. ✅ 17/10 — **Vitest rossi e cura del frontend.**
   - Rossi (`test-author` `y30-frontend-reds`): `lotWacPriceChartHelpers.test.ts`, V1 `marketPriceLine` (5 casi) e V2 la
     colla sul sorgente (l'import del helper, niente prop `priceHistory`), 7 rossi per la ragione attesa («is not a
     function», la colla), 77 verdi; `lotsAnalysisStore.test.ts` `MAIN` con `MARKET_PRICE_HISTORY` (9/9); E1 in J12-1:
     `data-price-line="drawn"` nel controllo e nel passo 2, titolo e commento del passo, un punto nelle «Expectations».
   - Cura: `marketPriceLine` e `MarketPriceLinePoint` in `lotWacPriceChartHelpers.ts`; `LotWacPriceChart.svelte` con la
     prop `marketPriceHistory` (linea, date dell'asse, riavvio della risoluzione, conteggio, bolle) e
     `data-price-line={priceLineDrawn ? 'drawn' : 'absent'}` (la stessa condizione del `series.push` della linea);
     `LotsAnalysisPanel.svelte` chiede `MARKET_PRICE_HISTORY` e la legge con `asArray`, fuori da `lotSection`.
   - Controlli (`files/scripts/y30_light.sh`): helper **85/85**, store **9/9**, `financialMathExceptions.gate` 19/19,
     `themeRoles.gate` 80/80, `svelte-check` 0/0, `tsc -p tsconfig.e2e.json` pulito, Prettier pulito, `theme-roles --check`
     pulito, `git diff --check` pulito.
   > **Note implementazione**: una data ripetuta tiene il suo primo punto (il backend ne manda uno al giorno); il «declassamento»
   > dell'unione (una quotazione vera sulla stessa data toglie la stima) non serve più.
   > **Fuori pista**: corretto anche il paragrafo del contratto J-12 in testa alle spec di J12 (`brokers-detail.spec.ts`
   > ~:1883: «keeps its average-cost lines» → più la linea del prezzo), segnalato da `test-author`.
4. ✅ 17/10 — **E2E** (slot del coordinatore, 21:11–21:22, `files/scripts/y30_e2e.sh`, `--workers 2`, corsia 6189).
   - Prima dello slot, fusa la nota di X su Y-34: tolto da `expectLotsPanelOpen` il parametro `assetId`, mai passato dai 12
     chiamanti (il ramo dell'espressione e la frase del commento con lui); `tsc` delle E2E e Prettier puliti.
   - `front-broker detail` **39/40**: J12-1 verde col controllo e il passo 2 (`data-price-line="drawn"`); rosso
     `:265 import files modal can open file preview` (nessuna riga `row-actions-` nello storico degli import in 8 s).
     `stale-price-banner` **2/2**, `dashboard-cache` **6/6**.
   - Triage (`test-triage`), verdetto **ambiente**: i miei run `api portfolio` (20:4x–20:51) popolano con
     `populate_mock_data --force` senza `--with-reports`, che svuota `broker_reports/` (`reset_broker_reports`); lo script
     E2E mette `LF_SETUP_DONE=1`, quindi `global-setup.ts` non ripopola, e `front-broker detail` non lo fa da sé: ogni
     broker del mock aveva lo storico vuoto. Il run di `dashboard-cache` (`_ensure_db_populated`, con i report) li ha
     rimessi alle 21:16:14. Prove: le date di `broker_reports/` e di `uploaded/broker_*`, i log dei run (`Populating`).
   - Rerun di `front-broker detail` sul dato ricostruito (`files/scripts/y30_e2e_rerun.sh`): **40/40** (21:20–21:22).
     Porta 6189 libera.
   > **⚠️ Fuori pista**: la trappola va nella devWiki (`problems/direct-playwright-run-in-a-test-lane.md`, terza trappola) e
   > nei miei script: `y30_e2e.sh` lascia cadere `LF_SETUP_DONE` quando `broker_reports/uploaded/` è vuota.
5. ✅ 17/10 — **Documentazione** (`docs-writer` `y30-docs`, solo inglese, nessuno stamp):
   `lots_analysis_service.md` (contratto, FAILED con `_REPLAY_FREE_ANALYSES`, cambi, costruttori),
   `lots-analysis.md` (POST #1, FAILED, la prop e `marketPriceLine`, `data-price-line`), `positions.en.md` (un punto
   «la linea del prezzo copre tutto il periodo», il messaggio rosso con la linea del prezzo), più `financial_math.md`,
   `data-quality-banner.md`, `fifo_lot_engine.md` e il riferimento di `app-state.md` (`LotsAnalysisPanel.svelte:365-392`,
   ricontrollato per contenuto dopo il mio ultimo commento). Build strict **0 warning**, check-links **97/97** (rilanciati
   da me dopo l'ultima modifica). Debito di traduzione vero: due punti di `positions.en.md`.
   > **Note implementazione**: corretto il commento di testa di `LotsAnalysisPanel.svelte` (con FAILED disegnava «solo
   > le linee del costo medio»).
   > **⚠️ Fuori pista**: il `docs-writer` trova un'eccezione alla regola S7 di J-12, verificata da me nel codice: con
   > FAILED le conversioni di dividendi, commissioni e tasse girano prima del motore (`needs_income_alloc` legge le analisi
   > chieste; `unconvertible_ids` chiama `fx_resolver.convert`), quindi un loro cambio mancante resta nel data quality.
   > Nessun test lo copre. È di J: va al coordinatore; la pagina la documenta come comportamento attuale.
   - DevWiki (`wiki-file`): `decisions/fifo-v4-gross-net-status-model.md` (il «Left out» diventa «aggiunta la sera
     stessa»), `entities/lots-analysis-service.md` (`_REPLAY_FREE_ANALYSES`, l'eccezione), la terza trappola; `index.md`,
     `log.md`; `check_source_paths.py` nessun path rotto nelle tre pagine. Grafo non aggiornato (graphify assente nel
     worktree).
6. ✅ 17/10 — **CHECKPOINT READY** al coordinatore (~21:5x): riga 🐛, nota per la 🔄 di J-12, J revisore del backend;
   l'eccezione di S7 per J, la trappola della corsia, Y-35 (il `PRICE_HISTORY` senza lettori) nella mia sezione. FROZEN.
7. ✅ 19/10 — **Ingresso**: dopo il sì del developer a N89 («la linea del prezzo deve continuare anche dopo l'ultima
   vendita»), il coordinatore fa entrare Y-30 in `dev_release2` con il merge `ede7adf75` (conflitto solo sul log della
   devWiki, risolto da lui tenendo le righe di tutte e due le parti).

## 19/10 · Ripartenza: contabilità e analisi (Y-30 dopo l'ultima vendita, N65)

Base `ede7adf75`, worktree pulito. Fonte: le risposte del developer al resoconto, file del coordinatore
`risposte-resoconto-20261019.md`, §4 e §6. **Regole nuove del coordinatore, da ora**: nessuna decisione di prodotto da
Y (ogni scelta che cambia ciò che l'utente vede, i numeri o i dati diventa una domanda, con le opzioni e un consiglio);
si implementa solo col suo via esplicito; niente carichi pesanti senza uno slot. Questa sezione è in sola lettura: nessun
codice, nessun test lanciato, nessun server.

### Contabilità ✅ (19/10, 11:10–11:45)

- **Piano**: la testata «Stato al 19/10»; i titoli di Y1, Y2 e Y7 nel §4 con il commit d'ingresso (Y7 diceva ancora «in
  corso»); nel §4 la tabella «Stato dei lotti» al posto di «Y3–Y13 — da avviare»; nel §2 un rimando a quella tabella.
- **Backlog, sezione Y** (26 sostituzioni in 24 voci, ognuna limitata alla sua voce, `files/scripts/y19_backlog_proofs.py`):
  - Y-3 e Y-4 ✅: fatte il 17/10 da `test-author` (`034f0f13a`, `1130d2eff`), entrate con `73443c6db` (treno 237), ma
    non marcate. Verificate nel codice di oggi: `I18N_CALL` con `\bt\(`; il titolo del caso a clic di
    `SignalTreeSelect.test.ts` non nomina più l'aiuto della galleria;
  - il commit d'ingresso su 22 voci ✅ che non lo citavano: 14 senza alcun commit (Y-1, Y-5, Y-8, Y-14, Y-16, Y-19,
    Y-20, Y-24, Y-25, Y-27, Y-29, Y-30, Y-31, Y-33), 8 con solo quello di contenuto (Y-2, Y-6, Y-11, Y-12, Y-13, Y-21,
    Y-22, Y-23);
  - aperte, tutte in attesa del developer: Y-7 (dopo Y4a), Y-9, Y-10, Y-15, Y-18, Y-26, Y-32, Y-35.
- **Prove**: i 48 commit citati nella sezione e quelli della tabella sono antenati della base
  (`git merge-base --is-ancestor`). Gli ingressi vengono dal registro dei treni del [README della fase](../README.md)
  (fino al treno 370) e da `git log` per Y-34 (`7dbd46aa6`) e Y-30 (`ede7adf75`), che il registro non ha ancora. Per un
  commit di contenuto, il primo commit della linea di `dev_release2` che lo contiene (`files/scripts/y19_entry_merge.sh`).
- `git diff --check` pulito; un solo `## MF ·` nel backlog.

### Analisi 1 · Y-30: la linea del prezzo continua dopo l'ultima vendita ✅ confermato

- **Il percorso.** `get_lots_analysis` costruisce i giorni da `computed_from` (la prima transazione dell'ambito, mai
  prima del 1900) ad `actual_to`, cioè `date_to` o oggi, con il tetto `latest_range_end()` (domani del server).
  `MARKET_PRICE_HISTORY` è un'analisi giornaliera (`daily_series`), quindi ogni giorno ha il suo segno in
  `estimated_market_prices`. `build_market_price_history` (`financial_math/lots/histories.py`) mette un punto per ogni
  giorno con un segno, qualunque lotto sia aperto, e `trim_dates` taglia a `[display_from, actual_to]`.
- **Dopo l'ultima vendita** il risolutore dei prezzi porta avanti l'ultima osservazione: la quotazione (linea piena) o,
  senza quotazioni, l'ultimo scambio (linea tratteggiata, `estimated`). Il sync pianificato (`run_history_sync`,
  `platform/scheduler/jobs.py`) prende ogni asset attivo con un provider, posseduto o no. Quindi dopo una vendita
  totale la linea segue le quotazioni vere; resta piatta sull'ultimo valore solo per un asset senza provider o
  disattivato.
- **La fine della finestra.** Il pannello non manda `date_range` (`LotsAnalysisPanel.loadMain`): la finestra va dalla
  prima transazione a oggi (data del server), e l'asse del grafico segue `computed_date_to` (`xAxisRange`).
- **Le prove**, verdi il 17/10:
  - D1 (`test_portfolio_api.py::test_market_price_history_continues_after_the_last_sale`) è il caso esatto del developer:
    BUY 10 il 10/1/2026, vendita di tutto il 15/1, nessun riacquisto, letto fino al 20/1. Ha un punto per ogni giorno
    fino al 20/1: 100 fino al 14, 110 dal 15, stimati. 8/8;
  - A1 (`test_lots_market_price_history.py`): ultima vendita il 13/3, punti fino al 16/3. 213/213.
- **Codice invariato** da `6db475ac9`: dopo, nei file della linea, solo `81a927681` (il banner dei lotti) e `279764d88`
  (una riga di enum in `schemas/portfolio.py`).
- **Non coperto**: nessun test nel browser fissa il tratto dopo l'ultima vendita (J12-1 legge `data-price-line` con
  `FAILED`). Un caso E2E piccolo è possibile, se il developer lo vuole.

### Analisi 2 · N65: il righello con lo stesso giorno in «Da» e «A»

**La causa vera** non è nel `DateRangePicker`: è il righello, che rifiuta in silenzio.
1. Il selettore della scheda della misura riceve le date a senso unico (`MeasurePanel.svelte:560`: `start={…} end={…}`,
   nessun `bind:`) e avvisa con `onchange`.
2. Il selettore scrive le sue date **prima** di avvisare. `start` ed `end` sono `$bindable` (`DateRangePicker.svelte:108-109`);
   il clic del calendario (`handleDayClick`, `:463-480`) e i campi scritti (`flushTypedRange`, `:965-976`) le assegnano e
   poi chiamano `onchange`. Se il genitore non le lega, quel valore resta locale finché il genitore non ne passa uno
   diverso.
3. Il righello rifiuta lo stesso giorno: `updateMeasureDates` (`MeasurePanel.svelte:228-233`) esce con
   `if (s === e) return; // measure needs 2 different days`, prima di toccare la misura e senza riassegnare `measures`.
4. Quindi la misura resta sulle date vecchie (i numeri della scheda, la riga riassuntiva, la sovrapposizione sul
   grafico), e al selettore non arriva nessuna data nuova: resta sul giorno scelto. Due componenti in disaccordo, e niente
   dice all'utente che la scelta è stata rifiutata. È «il componente mostra il dato giusto, il resto resta sul vecchio».

**Due fatti che pesano sulla scelta:**
- La misura **sa già** misurare un giorno solo. `MeasureSignal.getMeasurement` dà Δ 0, Δ% 0 % (o «—» se il valore è 0,
  N65), 0 giorni, Δ%/anno «—» (sotto i 30 giorni, N65); `computePoints` dà un punto solo. È fissato da test:
  `measureSignal.test.ts:105` e `:173`, il rosso T-D9 che vuole «—» per l'annualizzato di un giorno.
- Il grafico **crea già** misure di un giorno. `addPoint` (`MeasurePanel.svelte:154-184`) non controlla lo stesso giorno:
  un secondo clic sullo stesso punto, dopo 300 ms, ne crea una. Invece l'anteprima le rifiuta (`updatePendingEnd`, `:140`,
  test `MeasurePanel.test.ts:246`), e così «misura tutto il grafico» (`:195`). Le due entrate oggi non sono d'accordo
  (dalla lettura del codice; non provato nel browser).

**Opzioni** (nessuna decisa):
- **(a) Il righello accetta lo stesso giorno.** Tocca solo `MeasurePanel.svelte`: si toglie il rifiuto di
  `updateMeasureDates` (l'anteprima può restare com'è).
  - L'utente vede una misura di un giorno: Δ 0, Δ% 0 % (o «—»), 0 giorni, Δ%/anno «—»; sul grafico il segnaposto e la
    freccia sullo stesso punto. È ciò che oggi esce da due clic sullo stesso punto.
  - Nessun file condiviso, nessun testo nuovo, nessun colore.
  - Test: un rosso in `MeasurePanel.test.ts` che sceglie lo stesso giorno nel calendario della scheda (oggi la scheda
    resta sulle date vecchie). Documentazione: una riga in `user/assets/detail/measures.en.md` e
    `user/fx/detail/measures.en.md`. Circa mezza giornata.
- **(b) Il selettore non lascia scegliere lo stesso giorno, solo per il righello** (la proposta del developer, nella forma
  del coordinatore).
  - Una prop nuova di `DateRangePicker`, spenta di default. Gli altri 9 usi non cambiano (Dashboard, pagina del broker,
    lista e dettaglio di asset e cambi, filtro delle colonne, `CellDateRange`, replay L4), e lì un giorno solo resta
    valido.
  - Il calendario disabilita il giorno già scelto finché si sceglie il secondo. `CalendarMonth` ha già i giorni
    disabilitati (`disabledDates`), con l'aspetto già sui ruoli: nessun colore nuovo.
  - Servono due scelte in più del developer:
    - **(b1)** lo stesso giorno scritto a mano nei due campi: rifiutato con un messaggio sotto il campo (una stringa nuova
      nelle 4 lingue; il mio consiglio) oppure spostato di un giorno da solo;
    - **(b2)** le frecce che portano un capo sull'altro: saltano quel giorno (il mio consiglio) oppure si fermano.
  - Per coerenza il secondo clic sul grafico sullo stesso giorno va ignorato, come fa già l'anteprima: così il righello
    non ha mai misure di un giorno.
  - Test in `DateRangePicker.test.ts` e `MeasurePanel.test.ts`; le stesse due pagine utente. Circa una giornata.
- **(c) La minima**, solo se né (a) né (b): il righello continua a rifiutare, ma rimette il selettore sulle date della
  misura. La scelta sparisce senza spiegazione e sembra un difetto: sconsigliata.

**Il mio consiglio: (a).** La causa è un rifiuto silenzioso del righello, non il selettore. La misura di un giorno era
già specificata (T-D9, N65) e già raggiungibile dal grafico; (a) mette d'accordo le due entrate con la modifica più
piccola, senza toccare un componente condiviso né aprire sotto-decisioni. Se invece il developer vuole che una misura
abbia sempre due giorni diversi (la sua proposta), allora (b), con (b1) il messaggio e (b2) il salto.

**Il programma colori.** `DateRangePicker.svelte`, con `CalendarMonth.svelte`, era nell'ondata **W1-c di T** (`ui/date`):
da 73 classi legacy a 0, `a5c7714ca` (16/10, 03:31), chiusa. Da allora nessun commit di colore sul file, e non è nel
registro del cricchetto: oggi non è in un lotto aperto. (a) non lo tocca; (b) sì, solo nel comportamento, con l'aspetto
disabilitato che c'è già: un avviso a T, tramite il coordinatore.

**Domande per il developer**, tramite il coordinatore:
- **N65-1**: (a), (b) o (c)? Il mio consiglio è (a).
- Solo con (b): **N65-2**, cioè (b1), e **N65-3**, cioè (b2).

**Definizione di fatto, dopo il via**: prima i rossi (Vitest; nessuna E2E nuova necessaria), poi la cura; `front check`,
Prettier, `theme-roles --check`; le due pagine utente in inglese (il debito di traduzione resta visibile); checkpoint
FROZEN.

## 19/10 · Revisione a posteriori di J-21 bis (`def1d5259`, in dev `539371064`), sola lettura

Via del coordinatore alle 11:28, sulla base `41fbfe3ea` (il giornale del 19/10 committato). Nessun test lanciato: lettura
del commit, del codice di oggi, dei chiamanti, dei plugin e della documentazione.

**Cosa fa.** `MAX_LINE_RUNS = 30` in `charts/signals/backendRenderer.ts`. In `renderScalarSeries` una linea senza regioni
di stile, o un'area, con **più di 30 tratti** (31 o più) torna una serie sola che unisce i vuoti, com'era prima di J-21.
Il nome prende « (gaps joined)» e `outcome.warnings` riceve un avviso. Le linee con regioni di stile e le barre non
cambiano. Chiavi `signals.gapsJoined.{label,warning}` nelle 4 lingue. Nessun file di test o di catalogo nuovo: 230 righe
in `backendRendererSegments.test.ts`.

**Verdetto: OK, con tre note e un rischio latente.**

Verificato e giusto:
- **La logica.** Il tetto vale solo per linea e area. «Con stile» è `series.kind === 'line'` e una regione con `lineStyle`,
  quindi un'area si unisce anche con regioni di stile. La serie unita tiene `id` (`${config.id}:${key}`), i due
  indicatori agli estremi, i livelli e le regioni. `renderedSignalPointCount` non cambia, perché conta le date.
- **I test**, completi sul renderer: 30 tratti restano divisi e 31 si uniscono; l'area si unisce anche con regioni di
  stile; livelli e regioni restano; una linea con stile resta un tratto per pezzo; si unisce solo l'uscita oltre il
  tetto, con un avviso dopo quelli del backend; `translate` con il ripiego in inglese; la barra resta intera. Il test di
  J-21 «120 tratti restano 120 linee» è riscritto per il tetto.
- **I18n**: le due chiavi sono a `signals.gapsJoined.*` in `charts/{en,it,fr,es}.json`, dove il codice le cerca.
- **Il costo**: 30 tratti × circa 2 500 giorni di borsa ≈ 75 000 punti, come dice il commento. Nessun colore, nessun
  calcolo finanziario nel frontend.

Le note:
1. **L'avviso non arriva all'utente** (basso, chiarezza). I sei chiamanti di `renderBackendSignalResult` (`fx/+page`
   ×2, `fx/[pair]`, `assets/+page` ×2, `assets/[id]`) leggono solo `outcome.signals`; `outcome.warnings` non è letto da
   nessuno, nemmeno prima di J-21 bis. Il pannello dei segnali costruisce i suoi avvisi da `item.result.warnings` del
   backend (`signalProblem.ts:162`); `warningMessages` di `assets/[id]:1015` va solo nel log di debug. Si vede quindi
   solo il nome «(gaps joined)», nel tooltip del grafico (`PriceChartFull.svelte:981-987`; i grafici non hanno una
   legenda delle serie). Il messaggio del commit («plus
   warning»), il commento di `MAX_LINE_RUNS` («its name and the outcome's warnings say so») e J-59 («con un avviso»)
   descrivono un avviso che non si vede. Due strade, la scelta non è mia:
   - (i) togliere l'avviso e lasciare il nome, che già lo dice (commento e J-59 da correggere): il mio consiglio, perché
     non cambia nulla di visibile;
   - (ii) mostrare gli avvisi del renderer nel pannello dei segnali: un cambio d'interfaccia, quindi una domanda per il
     developer.
2. **La guida per sviluppatori è rimasta indietro** (minimo, documentazione). `signal_plugin_guide.md:255-259` dice che
   il renderer spezza sempre una linea o un'area ai punti senza valore, «so no segment crosses a day on which nothing was
   measured». Da J-21 bis, oltre 30 tratti, una linea senza stile o un'area unisce i vuoti. Basta una frase, con
   `docs-writer`.
3. **Il CHANGELOG sbaglia di uno** (minimo; il file è del coordinatore). Dice «more than 30 gaps». Il tetto conta i
   tratti: si unisce da 31 tratti, cioè da 30 vuoti, come fissano i test (30 tratti divisi, 31 uniti). Meglio «30 gaps or
   more».

Il rischio latente, nessuna azione per la 1.3:
- Le linee con stile sono esenti dal tetto, per scelta e fissate da un test, e `limitStyledSegments` non unisce mai oltre
  un vuoto. Quindi una linea con stile e N tratti resta almeno N serie lunghe quanto l'asse.
- Oggi le linee con stile sono RSI, CCI, MFI e Stochastic RSI (le sole con `line_style` nelle regioni), e tutte chiamano
  pandas-ta-classic con `talib=True`. TA-Lib dà 0, non NaN, su una finestra piatta, quindi i punti senza valore restano
  quelli del riscaldamento, all'inizio, che non aprono un tratto. Letto nel codice, non misurato.
- Morderebbe solo con un'uscita con stile che manda vuoti a metà serie. Anche uno stile di partizione scelto
  dall'utente (`config.partitionStyles`) rende «con stile» una regione senza `line_style`, e la fa uscire dal tetto.
- J-59, una serie sola per uscita, toglie sia il tetto sia questa esenzione. Da annotare in J-59 quando si fa.

**Per dopo la 1.3**: J-56 (il gradino nel secchio del taglio) e J-59 stanno nella sezione di J del backlog, ma sono per Y
(FE2): li prendo io quando il coordinatore li assegna. Non tocco la sezione di J.

## 19/10 · Revisione di J-48 (`ab4be3daa`, ramo di J), sola lettura

Richiesta del coordinatore alle 12:35, sulla base `88fdf4517`. Letti gli oggetti git dal mio worktree, non il worktree di
J. Nessun test lanciato. J-48 è su `5da188c15`, che contiene Y-30 (`ede7adf75`). Dalla base comune, nei file dei lotti
c'è solo J-48, e il mio ramo differisce solo nel giornale: nessun conflitto atteso.

**Cosa fa.** Una gamba di trasferimento il cui partner sta presso un broker fuori dall'ambito si legge come una rettifica
(J-10), e le viste dei lotti dicevano «rettifica». J-48 aggiunge `LotTimelineEventSchema.scope_boundary`: `IN` sulla
riga d'apertura della gamba in arrivo, `OUT` su ogni riga di chiusura della gamba in partenza, `None` altrove.
Il frontend lo legge con `scopeBoundaryOf` ed `eventLabelKind` (`lotChartShared.ts`) per l'etichetta e la categoria del
marcatore, nelle tre viste: storia della modale, Gantt, grafico prezzo/costo medio. Chiavi `TRANSFER_IN`/`TRANSFER_OUT`
in `brokers.lots.modal.event` e `brokers.lots.chartMarkers.eventType`, nelle 4 lingue. Una riga del CHANGELOG, la pagina
utente, due pagine per sviluppatori e i test (backend 8, Vitest in 5 file).

**Verdetto: OK.** Le tre cose chieste tengono; quattro note, nessuna bloccante.

1. **Nessun numero cambia** ✅
   - Backend: solo il campo nuovo. `kind`, prezzi, P&L e proventi non cambiano. Un `BoundaryLeg` tiene solo l'id e la
     direzione.
   - Frontend: `scope_boundary` lo leggono solo l'etichetta e la categoria del marcatore. `applyLotEvent` (la
     ricostruzione di quantità e prezzo), le voci di dettaglio della modale e le righe di quantità ed effetto del tooltip
     leggono ancora `kind`. Per una gamba in uscita `closureValueLabelKey` resta «consegnato», non «proventi».
   - I test lo fissano: `applyLotEvent` uguale con e senza il campo, in entrata e in uscita; `closureValueLabelKey`.
   - La tabella dei lotti ricava lo stato dalle quantità (aperto, parziale, chiuso), quindi lì nessuna etichetta di
     rettifica rimane indietro.
2. **Il broker dell'altro lato non viene mai nominato** ✅
   - La gamba entra nel motore come un ADJUSTMENT a sé, sul proprio broker, con `related_transaction_id=None` (`_read` in
     `scope_boundary.py`): nessuna riga riceve l'id o il broker del partner. Il test c3 lo fissa per tutti e due i lati.
   - Le etichette («TRANSFER+/-», «Transfer In/Out») non nominano broker. Il tooltip del grafico per queste righe non ha
     «Da/A» né il broker. La riga della modale nomina un broker dell'ambito (nota 2).
3. **Etichette e colori coerenti, anche con Y-30** ✅
   - Stessa famiglia nelle tre viste e nelle 4 lingue. Storia: «ADJUSTMENT+/-» diventa «TRANSFER+/-», mentre un
     trasferimento dentro l'ambito resta «TRANSFER». Marcatori: «Adjustment In/Out» diventa «Transfer In/Out».
   - Colori e glifi: la riga prende l'aspetto dei trasferimenti di ogni vista, senza nuovi colori:
     - modale: il ⇄ blu, prima il + verde o il − ambra;
     - Gantt: ◆, prima + o ×;
     - grafico: la serie dei trasferimenti.
     Nel diff nessuna classe cambia, quindi il cricchetto dei colori non si muove; i colori del distintivo della modale
     sono categorici e preesistenti.
   - Y-30: nel grafico l'unico pezzo vicino al codice di Y-30 è la chiamata di `eventCategory`. I marcatori restano sulla
     linea del prezzo senza lotti (`resolveMarketPriceAtOrBefore` su `marketPriceLookupPoints`), quindi un marcatore
     d'uscita sta sulla linea anche quando non resta nessun lotto. Con `FAILED` non ci sono eventi dei lotti, quindi
     nessun marcatore.
4. **Documentazione e testi** ✅: la pagina utente (una frase; le traduzioni restano in debito, vero, nessuno stamp), le
   due pagine per sviluppatori (le àncore `#scope-edge-transfers` esistono in entrambe), la riga del CHANGELOG, le chiavi
   in 4 lingue × 2 spazi.

Le note:
1. **La nota di J sul Gantt è confermata.** La serie `__event-markers` ha `tooltip: {show: false}` e nient'altro legge il
   `label` del marcatore. Sul Gantt quindi cambia solo il glifo; `eventMarkerLabel` ed `eventMarkerLabelKey` producono un
   testo che nessuno vede, già prima di J-48.
   - Da aggiungere alla domanda per il developer: senza etichetta, sul Gantt entrata, uscita e trasferimento interno sono
     tutti ◆. La direzione si legge solo dalla posizione: ◆ all'inizio di una corsia è un arrivo, alla fine un'uscita.
   - Di conseguenza la chiave di deduplica `${kind}:${lotId}:${laneIndex}:${dateMs}` unisce in un solo ◆ un'uscita al bordo
     e un trasferimento interno nello stesso giorno sulla stessa corsia (prima ◆ e ×). Nessun numero, ed è un caso raro.
   - Se il developer sceglie di mostrare l'etichetta, `lots-analysis.md` ha bisogno di una frase.
2. **Preesistente, non di J-48: la riga di chiusura nomina il broker d'apertura del lotto.** `_build_closure_rows` mette
   `broker_id = lot.opening_broker_id`: `LotClosure` non ha un broker, solo `fragment_id`. La modale scrive
   «<etichetta> <broker>».
   - Con «TRANSFER-» la riga si legge «uscito da <broker>». È sbagliata quando il lotto si è spostato dentro l'ambito
     prima di uscirne: aperto in A, spostato in B, mandato fuori da B, la riga dice «TRANSFER- A». Lo stesso vale oggi per
     «SELL A» su una vendita in B, e prima di J-48 era «ADJUSTMENT- A».
   - Resta un broker dell'ambito: il partner non è mai nominato.
   - Dalla lettura del codice, non provato. Il test c3 filtra un broker solo, quindi non copre il caso.
   - Rimedio possibile, nel backend di J: il broker di chiusura dal frammento chiuso (`closure.fragment_id`). Cambia un
     testo visibile, quindi è una domanda; peso minimo, chiarezza.
3. **`scripts/test_runner/_frontend_utility.py`, una riga**: il file di test nuovo in `front_utility_unit`, nel blocco dei
   lotti. Nelle regole del mio avvio è un file del programma colori, che si tocca solo passando dal coordinatore. È
   un'aggiunta e non porta conflitti: va solo confermato che J aveva il via.
4. **Le prove di J non le ho viste girare**: la revisione è di lettura.

## 19/10 · Y-N65 — lo stesso giorno in «Da» e «A», in tutti i selettori: analisi (sola lettura)

**La decisione del developer** (inoltrata dal coordinatore alle 14:31), testuale: «va impedita sia nel grafico che
selezionando le date, e come dicevo, nel datapicker range, non permettiamo proprio da ui di scegliere 2 volte la stessa
data, se si fa 2 volte click sulla stessa data il click viene ignorato, anche meglio compare come per i giorni futuri
l'icona che fa capire che non ci puoi andare sopra». Alla domanda del coordinatore («solo nel righello o in tutti i
selettori?») ha risposto: in tutti i selettori di intervallo dell'app, sapendo che il filtro per data delle tabelle non
potrà più avere un giorno solo.

Base `918c2ce39`; `dev_release2` è a `84c1bcba1`, 36 commit avanti. Nei file del lotto, in quei commit, c'è solo X-R16
sulle pagine di dettaglio di asset e cambi. Nessun codice, nessun test lanciato.

### Dove nasce oggi un intervallo di un giorno

1. **Calendario**: il secondo clic sul giorno in attesa dà inizio = fine (`handleDayClick`, `DateRangePicker.svelte:463-480`).
2. **Data scritta uguale all'altro capo**: `applyRangeDate` (`:950-962`) la accetta.
3. **Data scritta con l'altro capo vuoto o una sentinella**: `fieldIso(altro) || iso` copia la data sull'altro capo.
   - Il filtro per data delle tabelle parte vuoto: una sola data in «Da» oggi filtra quel giorno solo.
   - Con MAX attivo (`min`/`max`), una data d'inizio scritta dà [X, X].
4. **Frecce**: un capo portato sull'altro dà inizio = fine (`handleFieldKeydown`, `:1042-1050`).
5. **Grafico**: `MeasurePanel.addPoint` (`:154-184`) crea una misura se il secondo clic è sullo stesso giorno. Già oggi
   rifiutano l'anteprima (`:140`) e «misura tutto il grafico» (`:195`).

Non ne creano:
- le scorciatoie: YTD, MTD e QTD hanno un minimo di 14 giorni, WTD di 6 (`withMinWindow`, `:301`);
- la finestra personalizzata: `min={1}`, applicato da `isDraftValid` di `CompactDurationBadge`;
- MAX, che dà `min`/`max`.

**«L'icona» dei giorni futuri** è il cursore `not-allowed`, sul bottone del giorno `disabled`
(`CalendarMonth.svelte:192-196`, `:270-273`).

**Il backend accetta ovunque un giorno solo**: `DateRangeModel` (`end >= start`, un giorno solo documentato), il periodo
dell'investimento programmato («end on or after start»), il replay del rischio («on or before»). Quindi il lotto è solo
d'interfaccia: l'API non cambia (segnalibri, client dell'API).

### La proposta, punto per punto

1. **Il calendario del selettore.**
   - Il giorno in attesa non si può cliccare: `disabled` e cursore `not-allowed`, come un giorno futuro. Tiene il suo
     colore d'attesa, senza la barratura dei `disabledDates`.
   - Passandoci sopra non si vede l'anteprima di un giorno solo (`hoveredDate` a `null` su quel giorno).
   - `handleDayClick` lo ignora anche lui.
   - Dove: `CalendarMonth`, perché solo il selettore d'intervallo imposta `pending` (`SingleDatePicker` mai), e
     `DateRangePicker`. Nessun colore nuovo: `cursor-not-allowed` è già la classe dei giorni futuri.
2. **Il grafico.**
   - `addPoint` ignora il secondo clic sul giorno d'inizio: nessuna misura, la modalità misura resta accesa, l'inizio
     resta in attesa.
   - Sul giorno d'inizio `updatePendingEnd` toglie l'anteprima, invece di lasciare l'ultima.
   - Facoltativo: il cursore di divieto anche sul grafico (N65-5).
3. **`MeasurePanel`: niente più rifiuto silenzioso.** Si toglie `if (s === e) return` da `updateMeasureDates` (`:233`).
   - Il selettore non può più mandare due date uguali.
   - Se qualcos'altro lo facesse, una misura di un giorno si calcola giusta (T-D9): nessun disallineamento.
4. **Lo stesso giorno scritto a mano** (N65-2): rifiutato come una data futura scritta, cioè testo rosso
   (`text-lf-danger`, `data-invalid`), non applicato, nessun messaggio.
   - In più, appena l'altro capo cambia e i due giorni sono diversi, il testo in attesa si applica.
   - Senza questo, chi scrive un «Da» nuovo uguale al vecchio «A», e poi il nuovo «A», resterebbe con «Da» rifiutato.
     È l'ordine delle E2E di `fx-detail` e il più naturale per un utente.
5. **Le frecce su un capo** (N65-3): saltano il giorno uguale, cioè un giorno in più nella stessa direzione; lo scambio
   dei capi continua a valere. Se il salto passerebbe oltre oggi (futuro non ammesso), il passo non fa nulla.
6. **Una data scritta con l'altro capo vuoto o con MAX** (N65-4): l'altro capo non si copia più.
   - Vuoto resta vuoto, cioè un intervallo aperto: «dal giorno X» o «fino al giorno X». Il filtro di colonna, l'URL
     delle transazioni (`?date_start=&date_end=`, `transactions/filterState.ts`) e quello dei file (`?date=da,a`) lo
     accettano già.
   - Con MAX la sentinella resta: `max` vale «da X a oggi», risolto dalle pagine con `resolveDateSentinel`; `min` vale
     «dai primi dati fino a X».
   - Cambio visibile: nel filtro di una tabella, una sola data in «Da» significa «da X in poi», non più «solo X».
   - Nota: con `min` il bottone MAX resta acceso anche con una fine diversa da oggi (`effectivePreset`, `:272-288`). È
     una regola che c'è già; la lascerei.
7. **Gli intervalli di un giorno già salvati** (N65-6): non li riscrive nulla, si caricano e funzionano.
   - Dove stanno:
     - il periodo delle pagine: `sessionStorage` `librefolio_dateRange`, per scheda, e l'URL `?start=&end=`;
     - i filtri: transazioni, file, e il link della Dashboard verso le transazioni, che porta il periodo della pagina;
     - i periodi degli investimenti programmati, nel DB.
   - Il selettore li mostra; solo non se ne possono fare di nuovi.
   - Le misure e il periodo del replay L4 non si salvano: non ce ne sono.
   - L'alternativa, normalizzarli al caricamento, riscriverebbe un segnalibro o un periodo salvato dall'utente:
     sconsigliata.

### I 10 usi del selettore

In nessuno serve codice: il comportamento viene dal componente condiviso.

| Uso | Oggi un giorno solo nasce da | Dopo |
|---|---|---|
| Pagine ×6: Dashboard, broker, lista e dettaglio di asset e cambi | due clic sullo stesso giorno; data scritta uguale; data d'inizio scritta con MAX: [X, X] | impedito; con MAX, da X a oggi |
| `DataTableColumnFilter`, il filtro per data | due clic; una data scritta sola, copiata | impedito; una data sola è un intervallo aperto |
| `CellDateRange`, il periodo dell'investimento programmato (`allowFuture`) | due clic; data scritta | impedito; i periodi di un giorno già salvati restano |
| `L4Replay`, senza MAX | due clic; data scritta | impedito |
| `MeasurePanel` | nella scheda, due clic o la data scritta, rifiutati in silenzio (il difetto N65); sul grafico, il secondo clic ne crea uno | impedito nella scheda; secondo clic sul grafico ignorato |

### I file, e chi li ha aperti

- **Il nucleo del lotto**: `ui/date/DateRangePicker.svelte`, `ui/date/CalendarMonth.svelte`, `charts/MeasurePanel.svelte`
  e i loro test.
  - Invariati in `dev_release2` dalla mia base.
  - Programma colori: `ui/date` era la W1-c di T, chiusa (`a5c7714ca`). `charts/` è l'area di DV, integrata fino a B4. Il
    lotto non porta colori nuovi; basta un avviso a T e a DV, tramite il coordinatore.
  - Lavoro committato su questi file negli altri rami: nessuno. Quello non committato non lo vedo: lo conferma il
    coordinatore.
- **Solo con N65-5 (b)**, il cursore sul grafico: `charts/PriceChartFull.svelte` (oggi `cursor-crosshair` in modalità
  misura, `:1152`), `routes/(app)/assets/[id]/+page.svelte` e `routes/(app)/fx/[pair]/+page.svelte`. Le due pagine le ha
  toccate X-R16 (`299393b19`, già in dev) e sono vicine al lavoro di X e di Z-29.
- I 10 usi: nessuna modifica.
- **Documentazione** (`docs-writer`, solo inglese):
  - per sviluppatori: `developer/frontend/components/core-ui/datePickers.md`, `developer/frontend/components/charts.md`
    (MeasurePanel), `core-ui/data-table.md` (il filtro per data);
  - per gli utenti: `user/assets/detail/measures.en.md`, `user/fx/detail/measures.en.md`, e una frase sul filtro aperto
    in `user/transactions/index.en.md`. Le traduzioni restano un debito vero.
- **CHANGELOG**: una riga 🔄, del coordinatore.
- **Prima del codice**: aggiornare la mia base a `dev_release2`.

### Rossi, test, costo

**Rossi** (Vitest, `test-author`):
- `DateRangePicker.test.ts`:
  - il secondo clic sul giorno in attesa non pubblica nulla, il giorno è `disabled`, il calendario resta aperto; un
    altro giorno chiude l'intervallo;
  - sul giorno in attesa nessuna anteprima;
  - «A» scritto uguale a «Da» resta rosso, nessun `onchange` con due date uguali; con un nuovo «Da» il testo in attesa
    si applica;
  - un «Da» uguale al vecchio «A», poi un nuovo «A», pubblica i due nuovi;
  - le frecce saltano il giorno uguale, e al tetto di oggi non fanno nulla;
  - con «A» vuoto si pubblica `(X, '')`, con MAX `(X, 'max')` e `('min', X)`: oggi `(X, X)`.
- `CalendarMonth.test.ts`: il giorno in attesa è `disabled` e il clic non arriva; controllo: senza `pending` nessun
  giorno è disabilitato.
- `MeasurePanel.test.ts`:
  - due clic sullo stesso giorno non creano una misura e la modalità resta accesa;
  - sul giorno d'inizio l'anteprima sparisce;
  - nella scheda espansa, due clic sullo stesso giorno lasciano la misura e il selettore sulle stesse date. È il difetto
    N65 di oggi: i campi mostrano X–X, la misura le date vecchie.

**I test esistenti**: nessuno fissa un giorno solo dal selettore.
- `MeasurePanel.test.ts:246` (anteprima sullo stesso giorno, nessun effetto) diventa «l'anteprima sparisce».
- `measureSignal.test.ts:105` e `:173`, sul modello, restano.
- `DataTableColumnFilter.test.ts:545` resta verde: controlla solo `from`.
- Le E2E (`asset-browse`, `asset-detail`, `fx-detail`, `risk-analysis`, galleria) scrivono sempre due date diverse.

**Prove**:
- leggere, col carico sotto 50: i Vitest toccati più `DataTableColumnFilter`, `L4Replay` e `CellDateRange`;
  `front check`, Prettier, `theme-roles --check`;
- slot E2E di circa 30 minuti, solo regressione: `front-asset asset-detail` (le misure), `front-fx detail`,
  `front-portfolio` sul replay L4, `front-asset asset-browse`. Una E2E nuova non serve.

**Costo**: circa una giornata (selettore 3 h, calendario e righello 1 h, rossi 2 h, documentazione 1 h, slot); con
N65-5 (b) da 1 a 2 ore in più.

### Domande per il developer (tramite il coordinatore)

- **N65-2, lo stesso giorno scritto a mano**: (a) rosso come una data futura, nessun testo nuovo (**consiglio**: è il
  «come per i giorni futuri» del developer); (b) rosso, con un tooltip proprio in 4 lingue.
- **N65-3, le frecce**: (a) saltano il giorno (**consiglio**); (b) si fermano prima.
- **N65-4, una data scritta con l'altro capo vuoto o con MAX**: (a) l'altro capo resta com'è: intervallo aperto, con MAX
  fino a oggi (**consiglio**); (b) «A» vuoto diventa oggi.
- **N65-5, il cursore sul grafico**: (a) clic ignorato e anteprima tolta, senza cursore; (b) anche il cursore di divieto
  sul punto d'inizio (**consiglio**, è il suo «anche meglio»), se X e Z-29 lasciano libere le due pagine di dettaglio.
- **N65-6, gli intervalli di un giorno già salvati**: (a) restano come sono (**consiglio**); (b) normalizzati al
  caricamento.

### Il lotto Y-N65 (via del coordinatore, 19/10 15:01)

**Decisioni del developer**: tutti i consigli, cioè N65-2 (a), N65-3 (a), N65-4 (a), N65-5 (b), N65-6 (a). Giornale
committato in `156c1411d`. Prima i rossi (`test-author`), **scritti senza lanciare nulla** finché il coordinatore non
aggiorna la base (dopo il cancello della fusione delle migrazioni; al suo «fermati» mi fermo). Dopo l'aggiornamento la
corsia 6189 si ripopola con `--force --clean`: la migrazione 011 non esiste più. Le note per T e DV («nessun colore
nuovo») le manda il coordinatore. Le pagine `assets/[id]` e `fx/[pair]` oggi non le ha aperte nessuno; se Z-29 parte
prima, l'ordine lo decide il coordinatore.

**Il contratto che i rossi fissano.**
1. **`CalendarMonth`**: il giorno uguale a `highlights.pending` è un bottone `disabled`, col cursore `not-allowed`. Il
   colore e `data-state` non cambiano, e il clic non arriva a `onDayClick`. Nessun altro giorno cambia;
   `SingleDatePicker` non imposta mai `pending`.
2. **`DateRangePicker`**:
   - il secondo clic sul giorno in attesa è ignorato: nulla pubblicato, calendario aperto, attesa tenuta; il passaggio
     del mouse su quel giorno non mostra l'anteprima di un giorno solo;
   - una data scritta uguale all'altro capo non si applica: resta sul campo e, armata, è `data-invalid="true"`, come una
     data futura scritta. Appena l'altro capo cambia e i due giorni sono diversi, il testo in attesa si applica;
   - le frecce: se il passo cade sull'altro capo, si va di un giorno in più nella stessa direzione, e lo scambio vale. Se
     quel giorno è nel futuro non ammesso, il passo non fa nulla;
   - una data scritta con l'altro capo vuoto o con una sentinella (`min`/`max`) lascia l'altro capo com'è: si pubblica
     `(X, '')`, `(X, 'max')`, `('min', X)`. Lo scambio solo fra due date vere.
3. **`MeasurePanel`**:
   - `addPoint` ignora il secondo clic sul giorno d'inizio: nessuna misura, la modalità resta accesa, l'inizio resta;
   - `updatePendingEnd` restituisce `true` sul giorno d'inizio (bloccato) e `false` altrove. Sul giorno d'inizio toglie
     l'anteprima se c'era (un'emissione senza `__pending__`), altrimenti non emette nulla;
   - `updateMeasureDates` perde `if (s === e) return`.
4. **Il cursore sul grafico** (`PriceChartFull`, vista a linea, e `CandlestickChart`), con N65-7 (b):
   - in modalità misura il grafico gestisce il suo cursore con zr. A ogni `mousemove` di zr, subito, prima della
     limitazione al frame, chiama `zr.setCursorStyle('crosshair')`, oppure `'not-allowed'` se l'ultimo passaggio era sul
     giorno bloccato. zrender rimette il cursore a `default` a ogni movimento, prima degli ascoltatori
     (`zrender/lib/Handler.js:95`, `:99`, versione 6.0.0);
   - `onMeasureHover` può restituire `true`. Dopo il frame il grafico applica il cursore del nuovo esito e pubblica
     `data-measure-hover="blocked" | "free"` sul contenitore;
   - fuori dalla modalità misura il grafico non chiama `setCursorStyle`;
   - le pagine non cambiano: le loro funzioni freccia restituiscono già il valore di `updatePendingEnd`
     (`assets/[id]/+page.svelte:2525`, `fx/[pair]/+page.svelte:1544`, numeri alla base `bb676c44c`).
5. **Gli intervalli di un giorno già salvati** restano come sono: nessun codice.

**N65-7, il mirino** (deciso dal developer alle 15:11, (b): «si se puoi, io non sapevo manco fosse stato fatto, non l'ho
mai visto!»). In modalità misura il contenitore dei due grafici ha `cursor-crosshair` (`PriceChartFull.svelte:1152`,
`CandlestickChart.svelte:643`), ma zrender mette `cursor: default` in linea sul suo elemento al primo movimento: il
mirino non si vedeva quasi mai. Lo rende vero la stessa chiamata del punto 4, con il suo rosso.

**Passi.**
1. ✅ 19/10 — **Rossi scritti, non lanciati** (`test-author` `85d6ba6a`, in sottofondo; nessun processo avviato, come
   chiesto dal coordinatore). Quattro file, +673 righe:
   - `CalendarMonth.test.ts`: 1 rosso (il giorno in attesa `disabled`, il clic non arriva) e 2 guardie (senza `pending`
     nessun giorno passato è disabilitato; `data-state` invariato);
   - `DateRangePicker.test.ts`, describe «no range of a single day (Y-N65)»: 2a, 2b, 2c (2 righe), 2d (2), 2e (4 righe)
     rossi. Guardie: il flusso «Da = vecchio A, poi un A nuovo», verde oggi per un'altra strada (la bozza di un giorno),
     e due giorni vicini;
   - `MeasurePanel.test.ts`: `PanelApi.updatePendingEnd` restituisce `boolean`; 3a, 3b (2), 3c rossi;
   - `PriceChartFull.test.ts`: l'imitazione di ECharts ha uno zr per grafico, che tiene i gestori e registra
     `setCursorStyle`, e `pointerIndex` (predefinito `null`, quindi i casi esistenti non cambiano). Un `describe.each`
     sulla vista a linea e a candele: 4 rossi e 1 guardia per vista.
   > **Note implementazione**: revisione mia in sola lettura. `git diff --check` pulito; nessuna asserzione su classi
   > (l'unica `cursor-crosshair` è in un commento) né su testo tradotto, nessuna attesa a tempo.
   > **⚠️ Fuori pista**: in jsdom, con la delega degli eventi di Svelte 5, un clic inviato a un bottone `disabled`
   > raggiunge comunque `onclick`. La cura deve quindi tenere anche il controllo nel gestore, come già per
   > `disabledDates`. E il tipo `onMeasureHover` dei due grafici va allargato da `=> void`.
2. ✅ 19/10 — Dopo l'aggiornamento della base: ripopolare la corsia; i rossi lanciati e visti rossi, col carico sotto 50.
   > **Note implementazione** (19/10, 15:43–15:50):
   > - base `bb676c44c` (fusione di `156c1411d` e dev `cc3c3af15`), i 5 file non committati intatti;
   > - la fusione tocca solo `assets/[id]` e `fx/[pair]` (X-R16, l'isolamento dei segnali); le funzioni freccia di
   >   `onMeasureHover` sono invariate, solo spostate a `:2525` e `:1544`;
   > - `dev.py test --test-port 6189 --data-dir /tmp/librefolio-r13-y db populate --force --clean`: riuscito in 12 s.
   >
   > **⚠️ Fuori pista** (15:44): **disco pieno**. Il volume Data è al 100%, con meno di 500 MiB liberi, in calo per le
   > scritture delle altre sessioni.
   > - `TAG=red bash files/scripts/yn65_vitest.sh` (un file alla volta, con `nice`, a carico 28–41): tutti e 4 i file
   >   sono caduti con `ENOSPC` alla trasformazione dei moduli, «Tests no tests».
   > - È un rosso d'infrastruttura, prima della raccolta: nessun test è girato, i rossi non sono ancora visti.
   > - Nessun server avviato, porta libera. Il populate di prima resta valido.
   > - Segnalato al coordinatore (`purpose: error`), con la mia parte liberabile (`mkdocs_src/site`, 578 MB). Fermo
   >   finché non tornano almeno 5 GB e il suo via. Intanto la cura si prepara a secco, nella cartella della sessione.
   >
   > ✅ 19/10, 16:0x — **Rossi visti rossi.** Il coordinatore ha liberato il disco (~21 GiB; ha cancellato lui la mia
   > `mkdocs_src/site`). Stesso script, carico 20–23:
   > - `CalendarMonth` 1 rosso su 15, `DateRangePicker` 10 su 86, `MeasurePanel` 4 su 32, `PriceChartFull` 8 su 58:
   >   23 rossi, esattamente quelli di Y-N65. Tutte le guardie e tutti i test esistenti sono verdi.
   > - Ogni rosso cade sulla sua asserzione, con il messaggio atteso; nessun `TypeError` e nessun montaggio fallito. Per
   >   esempio: `toBeDisabled()` sul giorno in attesa; `[['2024-02-10','2024-02-10']]` contro `[['min','2024-02-10']]`;
   >   `{cursor: undefined, hover: null}` contro `'not-allowed'`.
   > - Prettier `--check` sui 4 file di test: pulito. Log in `files/logs/yn65_red_*.log`.
3. ✅ 19/10 — La cura: `CalendarMonth`, `DateRangePicker`, `MeasurePanel`, `PriceChartFull`, `CandlestickChart`.
   > **Note implementazione** (16:0x–16:3x):
   > - `CalendarMonth`: `pendingDay` entra in `disabled` e nel controllo del clic. Nel blocco dello stato di base,
   >   `cursor-not-allowed` dopo i casi futuri. Colore e `data-state` invariati.
   > - `DateRangePicker`:
   >   - `handleDayClick` ignora il giorno in attesa;
   >   - `handleDayHover` sostituisce le 4 funzioni in linea identiche e mette `hoveredDate` a `null` su quel giorno;
   >   - `isAcceptableDate(which, iso)` = tetto più «non il giorno dell'altro capo», usato da `*Unparseable` e da
   >     `commitTypedField`;
   >   - `applyRangeDate`:
   >     - legge l'altro capo grezzo (`fieldValue`), così vuoto, `min` e `max` restano;
   >     - scambia solo due date vere (`concreteIso`);
   >     - prende in coppia la data in attesa dell'altro campo (`waitingTypedDate`: armata, sotto il tetto, diversa).
   >       Così lo scambio ordina le due date scritte dall'utente; applicarle una alla volta poteva perderne una;
   >   - le frecce: se il passo cade sull'altro capo, `addDays(±1)` nella stessa direzione; se quel giorno è oltre il
   >     tetto, nulla.
   > - `MeasurePanel`:
   >   - `updatePendingEnd(): boolean`; sul giorno d'inizio toglie l'anteprima se c'è e risponde `true`;
   >   - `addPoint` ignora il secondo clic sul giorno d'inizio;
   >   - via `if (s === e) return` da `updateMeasureDates`.
   > - `PriceChartFull` (vista a linea) e `CandlestickChart`:
   >   - `onMeasureHover` restituisce `boolean | void`;
   >   - `measureHover` (`$state`) è `blocked`, `free` o `null`, e un `$effect` lo azzera fuori dalla modalità misura;
   >   - a ogni `mousemove` di zr in modalità misura, prima della limitazione rAF, `setCursorStyle` sincrono;
   >   - nel rAF, il cursore e `data-measure-hover` dall'esito (`free` anche quando il puntatore non cade su un punto);
   >   - il rAF ricontrolla `measureMode`, così un passaggio rimasto in coda alla fine della misura non pubblica nulla;
   >   - le pagine non cambiano.
   > - Vitest (stesso script, carico 14–25): `CalendarMonth` 15/15, `DateRangePicker` 86/86, `MeasurePanel` 32/32,
   >   `PriceChartFull` 58/58, `CandlestickChart.tooltipEscape` 7/7.
4. ✅ 19/10 — Prove leggere: i Vitest toccati più `DataTableColumnFilter`, `L4Replay`, `CellDateRange`; `front check`,
   Prettier, `theme-roles --check`.
   > **Note implementazione** (16:3x–17:0x, carico 16–36):
   > - Vitest dei vicini: `files/scripts/yn65_vitest_batch.sh`, un solo processo con i 37 file di test che nominano
   >   `DateRangePicker`, `CalendarMonth`, `SingleDatePicker`, `MeasurePanel`, `CandlestickChart`, `PriceChartFull`,
   >   `DataTableColumnFilter`, `CellDateRange` o `L4Replay`, gate per percorso compresi. Risultato: 36 file su 37 verdi,
   >   1810 test verdi e 17 saltati.
   > - Prettier `--check` sui 5 sorgenti: pulito. `theme-roles.mjs --check`: «Colour gates: clean». `git diff --check`:
   >   pulito.
   > - `npm run check`: 0 errori, 0 avvisi (dopo `api sync`, vedi sotto).
   >
   > **⚠️ Fuori pista**:
   > - Nel lotto dei 37 file, il `beforeAll` di `PriceChartFull.tooltipEscape.test.ts` è scaduto a 60 s: i suoi import
   >   dinamici (`generated.ts`) erano in coda dietro gli altri 36 file. Rilanciato da solo: 17/17 verdi, 46 s. Verdetto:
   >   ambiente (contesa degli import), non prodotto.
   > - Il primo `npm run check` ha dato 4 errori nei file di J-48 (`LotCustodyModal.test.ts`, `LotGanttChart.svelte`,
   >   `LotWacPriceChart.svelte`): `scope_boundary` assente da `LotTimelineEventSchema`. Il client generato (ignorato,
   >   non committato) era di prima dell'aggiornamento della base. `dev.py api sync` lo ha rigenerato, senza toccare
   >   nessun file tracciato; poi 0/0.
   >
   > **Copertura E2E, letta in sola lettura**:
   > - `fx-detail` (`:1773`, `:2029`, `:2526`) e `asset-detail` (`:2609`) scrivono «Da», poi «A», poi Invio: il caso
   >   della coppia, coperto anche quando «Da» è il vecchio «A».
   > - `risk-analysis` mette solo il fuoco sui campi e li legge; `asset-browse` usa solo i preset.
   > - Nessuna E2E clicca due volte sullo stesso punto del grafico in modalità misura, e nessuna scrive una data nel
   >   filtro di colonna (le E2E dei filtri usano gli enum): quei casi li coprono solo i Vitest.
5. ✅ 19/10 — Slot E2E (circa 30 minuti): `front-asset asset-detail`, `front-fx detail`, `front-portfolio` sul replay L4,
   `front-asset asset-browse`.
   > **Note implementazione**: slot del coordinatore dalle 16:11, `DEADLINE` 16:55, corsia 6189, `--workers 2`.
   >
   > | Spec | Esito | Durata | Ora di fine |
   > |---|---|---|---|
   > | `front-fx fx-detail` | 28/28 | 2,7 min | 16:24 |
   > | `front-asset asset-detail` | 43/43 | 4,1 min | 16:36 |
   > | `front-portfolio risk` | 38/38 | 5,0 min | 16:42 |
   > | `front-asset asset-browse` | 8/8 | 1,6 min | 16:46 |
   >
   > In tutto 117/117 verdi; alle 16:46:13 la porta era libera. Gli script sono `files/scripts/yn65_e2e.sh` e
   > `yn65_e2e_rest.sh`, i log `files/logs/yn65_e2e_*.log`.
   > - La prima spec ha rifatto la build di debug e anche quella del sito MkDocs, perché il coordinatore aveva
   >   cancellato `mkdocs_src/site` per lo spazio: 16:12–16:19.
   > - Global-setup ha ripopolato con i report, perché dopo `--clean` la corsia non ne aveva più.
   >
   > **⚠️ Fuori pista**:
   > - **Il carico.** Alle 16:23 il carico a 1 minuto è salito a 201, per le altre sessioni. `yn65_e2e.sh` lasciava
   >   partire le spec dopo la prima con il carico a 5 minuti sotto 60. Il coordinatore aveva chiesto sotto 50: alla
   >   fine di `fx-detail` ho fermato lo script mentre aspettava, con la porta libera e nessun processo in corsia. Ho
   >   ripreso le altre tre spec con `yn65_e2e_rest.sh`: sotto 50 per tutte, fino a 6 minuti d'attesa.
   > - **Il sito MkDocs si rifà da solo.** `auto_build_mkdocs` (`dev.py`) rifà l'intero sito prima di ogni spec, se un
   >   `.md` di `mkdocs_src/docs` è più nuovo di `site/index.html`. Per questo ho messo in pausa `docs-writer` durante lo
   >   slot. Non aveva ancora salvato nulla.
   >
   > **Nota di `docs-writer`, verificata**: per il backend, `end: null` vale un giorno solo (`DateRangeModel`,
   > `GET /api/v1/transactions`); per il frontend, dopo Y-N65, «da X in poi». Oggi le due letture non si incontrano: la
   > pagina delle transazioni filtra nel browser. Registrata nel backlog come **Y-36**.
6. ✅ 19/10 — Documentazione (`docs-writer`, solo inglese); riga 🔄 del CHANGELOG nel checkpoint; CHECKPOINT READY.
   > **Note implementazione** (`docs-writer` `283bfe61`, 16:0x–16:5x, in pausa durante lo slot E2E). 8 pagine, nessuno
   > stamp: il debito di traduzione è vero.
   > - Sviluppatori, solo inglese:
   >   - `core-ui/datePickers.md`: il punto di `CalendarMonth` sul giorno in attesa, la sezione nuova
   >     `#no-single-day-range` (calendario, date scritte, frecce, capi aperti in tabella, intervalli già salvati) e i
   >     rimandi di «Used by»;
   >   - `charts.md`: la sezione nuova `#measure-mode` (il cablaggio del pannello, `addPoint`, `updatePendingEnd` con il
   >     suo booleano, N65, il cursore con zrender, `data-measure-hover`);
   >   - `core-ui/data-table.md`: la sezione nuova `#date-filter` (ogni capo può restare vuoto; il formato `from,to`
   >     dell'URL; un filtro di un giorno nell'URL vale com'è).
   > - Utente, `.en.md`:
   >   - `assets/detail/measures` e `fx/detail/measures`: il mirino, il secondo clic sull'inizio, il divieto, due giorni
   >     diversi;
   >   - `transactions/index`: «Da» solo vale da quel giorno in poi, «A» solo fino a quel giorno;
   >   - `fx/detail/chart` e `assets/detail/chart`: due giorni diversi. In `assets/detail/chart` anche «Custom with a
   >     calendar» corretto, nella stessa frase, e la data della pagina.
   >
   > **Verifica mia, in sola lettura, sul codice**:
   > - esistono `startMeasureMode`, `stopMeasureMode`, `addMeasureFromChartData` e `onmeasuremodechange`, e il 📏 delle
   >   due pagine li chiama;
   > - il filtro per data va bene con un capo solo lungo tutta la catena: `DataTableColumnFilter` passa
   >   `from: dateFrom || undefined`; `matchesColumnFilter` e il pre-filtro di `TransactionsTable` saltano un capo
   >   vuoto; `urlFilters.ts` scrive «from,to (either can be empty)»;
   > - esistono `resolveDateSentinel` e `lib/stores/dateRangeStore.svelte.ts`.
   >
   > **Prove** (`files/scripts/yn65_docs_check.sh`, carico 41):
   > - `dev.py mkdocs build` strict: 0 avvisi in 105 s. L'ancora `#calendarmonth`, senza id esplicito, si risolve;
   > - `check-links`: 97 link validi su 97;
   > - `translate-validate --file` sulle 5 pagine utente, con `-L`: 15 file su 15 a posto, nessun errore. Il debito è
   >   solo di contenuto;
   > - `git diff --check`: pulito.
   >
   > **Lasciato com'è, scritto nel backlog come Y-37**: tre inesattezze di prima in `datePickers.md`, fuori da Y-N65.
   > - In `CalendarMonth` non esiste «Keyboard navigation within the grid»: c'è solo `numericArrows` sull'anno.
   > - Non è vero «week starts on Monday for most locales»: la griglia parte sempre da lunedì.
   > - Il riferimento `DateRangePicker.svelte:36,216-251` (8/10) è approssimato. Quelle righe non le sposta Y-N65.
   >
   > **CHECKPOINT READY** al coordinatore (19/10, verso le 17:10), poi FROZEN. 25 percorsi, 22 modificati e 3 nuovi:
   > - le liste sono `files/yn65_stage_{code,tests,docs,journal}.txt`;
   > - due commit proposti: `fix(web): refuse one-day date ranges (Y-N65)` (codice, test, MkDocs) e
   >   `docs(journal): Y-N65 plan, Y-36, Y-37, devWiki`;
   > - due righe del CHANGELOG nel messaggio, una 🔄 e una 🐛.
   >
   > Conflitti previsti con dev `ccc2a4141`, solo nei file condivisi del giornale:
   > - `LibreFolio_devWiki/index.md`: A-CL1 ha aggiunto righe in cima alla tabella dei problemi e al registro, dove
   >   vanno le mie. Si tengono tutte;
   > - `LibreFolio_devWiki/log.md`: tutti e due aggiungono in fondo. Si tengono tutti e due;
   > - il backlog: nessun pezzo dentro la mia sezione.
7. ✅ 19/10 — **Ingresso**. Il coordinatore ha committato `298be1611` (`fix(web)`, 17 percorsi) e `15603fe69` (il
   giornale, 8 percorsi), che ho verificato contro le liste. Revisione automatica pulita; merge `5cb47395f` in
   `dev_release2`, CHANGELOG `b1e7a2dd5` con le mie due righe (🔄 e 🐛); gate leggero del coordinatore: Vitest
   236/236 su 6 file, `front check` 0/0.
   > **Note implementazione**: i conflitti della devWiki (`index.md`, `log.md`) li ha risolti il coordinatore
   > sommando le due parti, con A-CL1. Verificato in sola lettura alle 17:15: i miei commit sono antenati di dev, le mie
   > righe (le due tabelle e il registro) e quelle di A-CL1 ci sono, nessun marcatore di conflitto. DV, che aspettava
   > questo ingresso per la sua riga in `PriceChartFull` e `CandlestickChart`, lo avvisa il coordinatore.

## 19/10 sera · Pausa generale (richiesta del developer, 18:12)

Il developer spegne la macchina, e `/tmp` verrà ripulito. Stato scritto alle 18:1x, senza comandi git.

- **Nulla in corsa**: nessun test, sonda o server; la porta 6189 è libera (18:14).
- **Il worktree**: HEAD `15603fe69`, non ancora portato al merge di dev (`5cb47395f`, poi `b1e7a2dd5`). L'unico file
  sporco è questo piano (la contabilità di Y-N65 e questa sezione): va nel prossimo checkpoint.
- **La corsia non sopravvive**: `/tmp/librefolio-r13-y` sparisce con `/tmp`. Alla ripresa, prima di qualunque run e col
  carico sotto 50: `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test --test-port 6189
  --data-dir /tmp/librefolio-r13-y db populate --force --clean`. Per le E2E resta la guardia dei report: senza un
  `.csv` in `<data dir>/broker_reports/uploaded`, `LF_SETUP_DONE` va tolto. Script e log stanno nella cartella della
  sessione, non in `/tmp`.
- **Il prossimo lavoro**: **Z-29d**, il dialogo che chiede la serie del bersaglio. Parte quando Z-29b è avanti, al
  messaggio del coordinatore: prima l'analisi, niente codice.

**Note in coda, per il prossimo checkpoint:**
1. **Le maschere della galleria** (nota del programma colori, 19/10 17:02). Il punto 4 delle verifiche del taglio di
   `GrowthChart` (§4; oggi righe 95–99), l'unica procedura che le usa, cita `g-final3-r1`, con maschere e stabilità di
   `g-final3__r1__vs__r2`: sono state cancellate per liberare il disco. Il riferimento di oggi è il trio del 18/10,
   `g-r3-prima-ba8e06763-full`, `g-r3-dopo-cd686f445-full` e `g-r3-dopo2-cd686f445-full`, con maschere e stabilità da
   `diffs/g-r3-dopo-cd686f445__vs__g-r3-dopo2-cd686f445`. Lo descrive `scripts/visual_review/README.md`, sezione
   «Known gallery behaviour»: è in dev, non ancora nella mia base, da rileggere dopo l'aggiornamento. Tutte le altre
   citazioni di `g-final3` (gli esiti di Y1 e Y2, la galleria mobile di Y7, la nota sul giorno UTC) sono la storia
   delle corse fatte: restano. Il coordinatore, 20/10: le maschere chiedono una pausa di tutta la macchina, quindi
   più avanti. La nota resta in coda.
   - ✅ 20/10, al checkpoint di Y-39a: il testo del punto 4 è aggiornato (§4, ora righe 96–109), con la sezione del
     README letta da `ccc2a4141`. Resta per la pausa della macchina solo la corsa della galleria, quando servirà.
2. **Il numero del treno di Y-N65** nella tabella «Stato dei lotti»: da leggere nel README della fase, dopo
   l'aggiornamento della base.
   - ✅ 20/10: il README della fase non numera più i treni dopo il 112 (16/10). Il riferimento resta il merge
     `5cb47395f`.
3. **Aperti, invariati**: nel backlog Y-7, Y-9, Y-10, Y-15, Y-18, Y-26, Y-32, Y-35, Y-36, Y-37 (in attesa del
   developer, o minimi); fermi Y4a e Y13 (Y13-1); dopo la 1.3, se assegnati, J-56 e J-59.

## 20/10 · Z-29d — il dialogo che chiede la serie del bersaglio: analisi (sola lettura)

> **Richiesta del coordinatore** (20/10 08:46): «Z-29d aspetta che Z-29b sia avanti, e Z è ancora su Z-32 (d). […]
> Nel frattempo prepara l'analisi di Z-29d (file, rischi, ordine dei passi), senza scrivere codice. Niente corse
> pesanti.»
>
> - **Base del worktree**: `15603fe69`; sporco solo questo piano.
> - **Codice letto**: quello di `dev_release2` `ecc7ac667`. Per il contratto di Z-29a, il ramo di Z `6510fe169`: commit,
>   letti in sola lettura con `git show`.
> - **Nessuna corsa** e nessun comando che cambia qualcosa. I numeri di riga sono di `ecc7ac667`.

**Cos'è Z-29d.** Viene dal piano di Z, sezioni «piano breve del lotto intero» e «il contratto rivisto» (19/10
15:25–15:35):
- «in modalità scheda, scegliendo il bersaglio di un confronto, la pagina dà la serie allineata con un risolutore
  asincrono; Vitest e un caso E2E. **0,5 giorni**»;
- «Il dialogo, scegliendo un bersaglio, manda la voce della scheda (`include_price: false`) e quella del bersaglio in
  una richiesta sola»;
- a Y tocca anche `AssetComparisonSignal`, «una riga»: in percentuale, la base del confronto dal `first` del bersaglio
  (`_baseValue`). Serve anche a Z-29b, per le schede.

### Lo stato reale (20/10)

**Le dipendenze.**
- **Z-29a e Z-29r, committati sul ramo di Z** (`37c3ec3ee`; checkpoint del 19/10 17:15, revisori MF e X), non ancora
  in `dev_release2`:
  - Z-29a è il backend dei prezzi: `key`, `max_points`, `resolution` e `sample_like` nella richiesta; `resolution` e
    `sample_bounds` nella risposta;
  - Z-29r è la sede neutra della regola per secchio.
- **Z-29s e Z-29b, non cominciati**: Z-29s riduce i segnali nel backend, Z-29b è la lista. Z è su Z-32 (d).

**Il dialogo oggi** (`lib/components/charts/ChartSettingsModal.svelte`, 444 righe). La modalità scheda è
`mode="pair"`.
- **La linea principale dell'anteprima** è `pairData` (`:227`), cioè la `chartData` della scheda (pagina, `:1913`).
  In % la normalizza `normalizeToPercentage`, che prende la base dal primo punto disegnato (`:231`).
- **I segnali locali** passano da `renderLocalPreview` (`:287`) a `renderMulti(previewDataAbs, …)`. La loro base in %
  è il primo punto dei dati di base (`ChartSignal.ts:421`).
- **Il confronto con un asset**: `_resolvedData = assetsDataMap[targetId]` (`:296-301`). È la `chartData` della scheda
  del bersaglio, sincrona.
  - L'anteprima non mette il nome del bersaglio e non controlla l'asset stesso.
  - La scheda invece salta il confronto con sé stessa (`assets/+page.svelte:1304`).
- **I segnali del backend in modalità scheda** sono i risultati salvati, dati dalla pagina:
  `resolveSettingsBackendPreview` → `getRenderedSignals(asset.id, asset.chartData, …)` (pagina, `:1265-1269`).
- **Il modello per l'asincrono c'è già, in modalità globale**: i segnali del backend sulla curva sintetica, con un
  ritardo di 250 ms (`:271`), un gettone (`livePreviewToken`) e uno stato d'errore.
- **I test.** Nessun test del dialogo. Lo legge solo il controllo sul sorgente di `chartCoreHelpers.test.ts:256`:
  verifica alcune proprietà di `<ChartSettingsModal>` nella pagina degli asset, e una proprietà in più non lo rompe.

**La pagina degli asset** (`routes/(app)/assets/+page.svelte`).
- `assetsDataMap` raccoglie le `chartData` delle schede (`:1916`).
- `fetchPriceSeries` manda `{asset_id, date_range: {start: dateStart, end: dateEnd}, include_price, signals}`, senza
  `target_currency` (`:739-742`), con `sendBulkBatches` e il pool dei worker (`:780`).

**`AssetComparisonSignal`** (`lib/charts/signals/AssetComparisonSignal.ts`, 176 righe).
- Allinea `_resolvedData` alle date del grafico per data esatta.
- In % la base è il suo primo valore allineato, per la linea (`:67`) e per il fantasma della conversione (`:137`).
  `comparisonSignals.test.ts:123` lo fissa.
- Sulla lista non c'è conversione, quindi niente fantasma.

**Il backend di Z-29a v3 per la richiesta del dialogo** (ramo di Z, `price_query.py`).
- `_plan_samples` pianifica la voce indicata anche con `include_price: false`: ne legge il seme e la prima riga, cioè
  il giorno F e il passo.
- Una voce con `include_price: false` torna con `prices` vuoti e senza `sample_bounds` (`:1054-1056`).
- Il `first` del bersaglio cade nel più tardo fra il giorno F della scheda e il primo giorno del bersaglio. Con una
  scheda giornaliera, il bersaglio è giornaliero da quel giorno.
- Due voci con intervalli diversi danno un 422 `range_mismatch`.

### Rispetto al piano di Z: cosa manca, cosa devia
- **Di Z-29d non c'è ancora nulla**, né del suo `AssetComparisonSignal`.
- **Il confronto rado, cioè il difetto che Z-29d ripara.** Dopo Z-29b ogni scheda ha la sua serie ridotta, con il suo
  giorno F e il suo passo. In modalità scheda l'anteprima allinea per data la serie ridotta del bersaglio
  (`assetsDataMap`) sulle date ridotte della scheda: con passi o F diversi le date coincidono poco o niente, e la
  linea è rada o vuota.
- **«Una riga» non basta.** Il fantasma della conversione ha la sua base, il primo valore originale allineato. Con la
  sola `_baseValue` linea e fantasma partirebbero da giorni diversi. Sulla lista oggi non succede (nessuna
  conversione), ma la classe serve anche al dettaglio e ai cambi.
- **La base dell'anteprima: un punto nuovo, che il piano di Z non tocca.**
  - Dopo Z-29b la scheda disegna `prices` e prende la base dal `first`: per la percentuale e per i segnali locali e
    del backend.
  - Il dialogo invece normalizza `pairData` sul suo primo punto e calcola i segnali locali su `pairData`.
  - Così, in %, la linea principale e i segnali locali dell'anteprima partono da 0 % alla fine del primo secchio, la
    scheda dal giorno F: anteprima e scheda non coincidono più.
  - Va riparato nello stesso lotto (D-Z29d-4).
- **I segnali del backend nell'anteprima** vengono da `getRenderedSignals` con la `chartData` della scheda. Se Z-29b
  cambia i dati di base di quella funzione per la scheda, deve cambiare anche questa chiamata (stesso file, di
  Z-29b). Lo verifico all'inizio di Z-29d.
- **La stima.** Il piano di Z dà 0,5 giorni per il dialogo, più la riga della classe. Con la base dell'anteprima, lo
  stato pubblicato e i suoi test, la mia stima è di circa 1,25 giorni (sotto).

### La proposta (tecnica, da concordare con Z)

1. **`AssetComparisonSignal`: `_basePoint`**, un punto invece del numero `_baseValue`.
   - In % la base della linea è `_basePoint.value`, quella del fantasma `_basePoint.originalValue` quando c'è.
   - Senza `_basePoint`, o con una base inutilizzabile (zero, non finita, `missing`), resta tutto come oggi.
   - Lo iniettano un solo aiuto comune, usato dalla scheda (Z-29b) e dall'anteprima (Z-29d), così i due calcoli del
     confronto non divergono.
2. **Il dialogo**, solo in modalità scheda. Le proprietà sono facoltative: senza, resta tutto com'è (lista dei cambi,
   modalità globale).
   - `comparisonTargetResolver(targetId)` restituisce `{data, basePoint, displayName}`, cioè la serie allineata del
     bersaglio, `[first, …prices]`. La dà subito se la pagina la ha, altrimenti con una promessa.
   - `pairFirst`, il `first` della scheda: dà la base della linea principale, e i segnali locali si calcolano su
     `[first, …prices]`, come sulla scheda.
   - Un piccolo modulo a rune accanto al dialogo tiene lo stato per bersaglio: `loading`, `ready` o `failed`.
     - Una sola richiesta per bersaglio a ogni apertura.
     - Un gettone per apertura: una risposta arrivata dopo la chiusura si scarta.
     - Nessun ritardo: una scelta nel menù è un evento solo.
   - L'anteprima pubblica lo stato, per i test: `data-testid="chart-settings-preview"`, con
     `data-comparison-state="none|loading|ready|failed"`. Il `LineChart` dell'anteprima non espone le sue serie: niente
     `__lfChart`, solo `data-chart-ready` e `data-chart-renders`.
3. **La pagina** (`assets/+page.svelte`), il risolutore.
   - **La serie c'è già**: se le strutture di Z-29b hanno la serie allineata per la coppia (scheda, bersaglio), il
     risolutore la restituisce subito, senza richiesta. Succede con un confronto salvato della scheda, caricato nella
     sua richiesta.
   - **Altrimenti**, una richiesta sola con due voci, costruite dal costruttore di gruppo di Z-29b:
     - la voce della scheda: la sua `key`, lo stesso `date_range` della sua voce in cache, `include_price: false`, e
       il suo campo di campionamento (T-Z29d-1);
     - quella del bersaglio: `sample_like` = la chiave della scheda, e lo stesso `date_range`.
   - **La risposta** passa dalla stessa via dei worker e va nella cache di Z-29b, che il bus `{kind: 'prices'}` svuota.
   - **Il bersaglio uguale alla scheda**: nessuna richiesta e nessuna linea, come sulla scheda (D-Z29d-3).

### Domande

**Di prodotto**: cambiano ciò che si vede. Il consiglio è in neretto.
- **D-Z29d-1 · Mentre la serie allineata arriva** (qualche centinaio di ms):
  - (a) **nessuna linea di confronto finché non arriva**. Niente lampo di una linea sbagliata, e oggi un bersaglio
    senza dati non dà linea;
  - (b) intanto la serie della scheda del bersaglio, rada, poi sostituita.
- **D-Z29d-2 · Se la richiesta fallisce** (rete, 422, budget):
  - (a) **nessuna linea, senza messaggio**. È un'anteprima: dopo il salvataggio la scheda chiede il suo confronto
    nella sua richiesta, con la gestione degli errori della pagina;
  - (b) un breve messaggio sotto l'anteprima, come quelli dei segnali del backend, con chiavi nuove nelle 4 lingue.
- **D-Z29d-3 · Il confronto con l'asset stesso.** Oggi l'anteprima lo disegna, la scheda mai.
  - (a) **lo salta anche l'anteprima**, come la scheda;
  - (b) resta com'è.
- **D-Z29d-4 · La base dell'anteprima dopo Z-29b:**
  - (a) **l'anteprima segue la scheda**, dentro Z-29d: linea principale e segnali locali con la base dal `first`;
  - (b) resta com'è, e in % anteprima e scheda sono diverse.

**Tecniche**, per il coordinatore e Z:
- **T-Z29d-1 · Il campo di campionamento della voce della scheda:**
  - **la `resolution` della risposta della scheda**, cioè il passo disegnato. L'allineamento è garantito anche se la
    larghezza è cambiata e la scheda non ha ancora richiesto;
  - oppure il suo `max_points`: il backend rifà la stessa scelta, se la larghezza non è cambiata.
- **T-Z29d-2 · Il nome e la forma della base:** **`_basePoint`** o `_baseValue`. Il punto copre anche il fantasma; il
  nome lo usa anche Z-29b.
- **T-Z29d-3 · Chi fa `AssetComparisonSignal`, e quando:**
  - **io, subito, come lotto minimo Z-29d-0**: è indipendente, perché senza iniezione non cambia nulla, e Z-29b lo
    trova pronto;
  - oppure Z, dentro Z-29b, con la mia revisione.
- **T-Z29d-4 · Dove va il caso E2E:**
  - **in coda a `assets/asset-list.spec.ts`, dopo che le E2E di Z-29b sono entrate**: stessa azione,
    `front-asset asset-list`, e nessuna riga nuova nel runner;
  - oppure una spec nuova, con la sua riga nel runner, che è un file condiviso.
- **Nota per Z, non bloccante.** Una voce pianificata con `include_price: false` legge e conta lo stesso le sue righe
  di secchio, perché `_read_samples` scorre tutte le voci pianificate, e poi le scarta. Sono poche centinaia di righe.

### Superfici
- **Codice:**
  - `lib/charts/signals/AssetComparisonSignal.ts` (Z-29d-0);
  - `lib/components/charts/ChartSettingsModal.svelte`, più il modulo nuovo dello stato (nome da fissare, per esempio
    `comparisonPreviewTargets.svelte.ts`);
  - `routes/(app)/assets/+page.svelte`: il risolutore, e due proprietà su `<ChartSettingsModal>`;
  - forse `lib/utils/chartUtils.ts`: `normalizeToPercentage` con una base, se Z-29b non lo ha già fatto.
- **Test:**
  - `comparisonSignals.test.ts` (Z-29d-0);
  - il test del modulo dello stato, o un `ChartSettingsModal.test.ts` nuovo;
  - il test del costruttore della richiesta;
  - un caso in `asset-list.spec.ts`.
- **Doc:**
  - `developer/frontend/components/charts.md`: l'anteprima in modalità scheda, il risolutore, la base;
  - la base del confronto nella pagina per sviluppatori dei segnali.
  - Nessuna pagina utente descrive l'anteprima in modalità scheda: nessun cambio previsto.
- **Fuori:** nessun backend; nessuna chiave i18n e nessun colore nuovo, salvo D-Z29d-2 (b), che userebbe un
  `InfoBanner` esistente.

### Conflitti previsti
- **`assets/+page.svelte`** è il file principale di Z-29b: la cache, i bersagli, la ricarica per scheda. Z-29d parte
  solo con il codice di Z-29b sulla mia base. Il risolutore è un pezzo a parte.
- **`asset-list.spec.ts`**: Z-29b ci scrive le sue E2E. Io dopo di lui (T-Z29d-4).
- **`ChartSettingsModal.svelte`**: oggi nessuno lo ha aperto.
  - DV lo ha portato a 0 classi di palette, quindi non ha un record nel cricchetto: nel codice nuovo solo ruoli.
  - Y4a lo sposterebbe in `lib/features/signals/` (tabella di DV, «D-Y14»), ma è fermo. Se riparte, l'ordine lo
    decide il coordinatore.
- **`AssetComparisonSignal.ts`**: solo Y. Z-29b inietta la base dal lato della pagina.
- **Il controllo sul sorgente** in `chartCoreHelpers.test.ts`: le proprietà nuove non lo toccano.
- **La galleria**: lo scatto `assets/chart-settings` è in modalità globale, e il confronto del dettaglio è
  giornaliero. Nessuno scatto cambia.
- **Gli altri**: J (il renderer dei segnali), X (i cambi; X rivede la lista), W, A e H non hanno file in comune.

### Complessità e rischi
- **Lo stato asincrono del dialogo**: risposte tardive, chiusura e riapertura, cambi rapidi di bersaglio, più confronti
  insieme. È una complessità media, che il modello globale risolve già.
- **Le forme di Z-29b**: la chiave, la voce in cache, il `first` della scheda, il mapping dei worker. Parto dal suo
  codice committato, non da questa analisi: al primo passo ricontrollo e aggiorno.
- **Due calcoli del confronto**, la scheda e l'anteprima, possono divergere. Il rimedio è un solo aiuto d'iniezione,
  usato da tutti e due.
- **`range_mismatch`**: l'intervallo della richiesta va preso dalla voce della scheda, non ricalcolato.
- **Il costo**: una richiesta piccola per ogni bersaglio nuovo, nessuna per quelli salvati.

### Lotti e passi

Ogni lotto si chiude con un checkpoint FROZEN.

0. ✅ 20/10 — Questa analisi, con le domande al coordinatore.
1. **Z-29d-0 · `AssetComparisonSignal._basePoint`**, se T-Z29d-3 è (a). Indipendente da Z-29a e Z-29b. **0,25
   giorni.**
   - Rossi (`test-author`): la base iniettata, per la linea e per il fantasma; senza iniezione, come oggi; la base
     zero.
   - Poi la cura, i Vitest leggeri e il checkpoint.
2. **L'attesa**: Z-29a in `dev_release2` e il codice di Z-29b sulla mia base, aggiornata dal coordinatore. Poi la
   corsia 6189 si ripopola con `--force --clean`.
3. **Z-29d · il dialogo.** **Circa 1 giorno.**
   1. Ricontrollo sul codice di Z-29b (la chiave, la voce in cache, il `first`, i worker, `getRenderedSignals`, il bus)
      e aggiornamento di questa analisi.
   2. Rossi (`test-author`), poi visti rossi con il carico sotto 50:
      - il modulo dello stato: una richiesta per bersaglio, la risposta subito dalla pagina, la risposta tardiva
        scartata, il fallimento, il bersaglio uguale alla scheda;
      - il costruttore della richiesta: due voci, con i campi detti;
      - la base dell'anteprima dal `first`;
      - GUARDIE: senza risolutore come oggi; la lista dei cambi e la modalità globale invariate.
   3. La cura, poi le prove leggere:
      - i Vitest toccati e i vicini: `comparisonSignals`, `chartCoreHelpers`, `ChartSignalsSection`,
        `chartPageSignals`, `loadComparisonData`, `previewPolicy`;
      - `front check`, Prettier, `theme-roles --check`, `git diff --check`.
   4. Uno slot E2E:
      - il caso nuovo: su «All», le impostazioni di una scheda, un confronto con un asset di storia diversa. Una
        richiesta con le due voci giuste, e `data-comparison-state="ready"`;
      - come regressione, `front-asset asset-list` e `asset-detail`.
   5. La doc (`docs-writer`), poi CHECKPOINT READY.

**Totale: circa 1,25 giorni.**

**Fatto quando:**
- in modalità scheda, il confronto dell'anteprima sta sulle date della scheda e, in %, parte dove parte sulla scheda,
  con una scheda ridotta come con una giornaliera;
- c'è una richiesta per ogni bersaglio nuovo, nessuna per uno salvato;
- modalità globale, lista dei cambi e dettaglio non cambiano;
- i rossi sono stati visti rossi, poi verdi; prove leggere ed E2E verdi; doc scritta; piano aggiornato.

**Il piano dei passi** lo scrivo qui sotto, sezione «Il lotto Z-29d», al via del coordinatore.

### Risposte del coordinatore (20/10 09:01) e il lotto Z-29d-0

**Le risposte.**
- **D-Z29d-1…4**: le porta il coordinatore al developer.
- **T-Z29d-1**: la `resolution` della risposta della scheda.
- **T-Z29d-2**: `_basePoint`.
- **T-Z29d-3**: Z-29d-0 è mio, **via adesso**: prima i rossi, poi il codice, poi il checkpoint. Corse leggere solo con
  il carico a 1 minuto sotto 50; la corsia 6189 si ripopola quando serve.
- **T-Z29d-4**: il caso E2E in coda ad `asset-list.spec.ts`.
- **`data-comparison-state`** sull'anteprima: sì.
- **Il dialogo** parte quando Z-29a è in dev e Z-29b sulla mia base: avvisa il coordinatore.

**Il contratto di chi consuma la serie ridotta** (le tre note della revisione di MF su Z-29a v3, per Y e Z-29b):
- **(n1)** Il Vitest legge la tabella dei casi (`compactDensityCases.json`) con la regola del browser e i
  `max_points` che la pagina manda. Per Z-29d: il dialogo non calcola `max_points`; manda la `resolution` della risposta
  della scheda (T-Z29d-1), e il suo Vitest lo fissa.
- **(n2)** Se un ridimensionamento cambia il passo, si rilegge dal server: un campione settimanale non si riaggrega in
  mesi, e da un campione non si torna al giornaliero. Per Z-29d: la chiave dell'anteprima comprende la `resolution` e
  l'intervallo della scheda; se la scheda rilegge con un altro passo, l'anteprima chiede di nuovo e non riaggrega mai
  la serie che ha.
- **(n3)** La base della percentuale e il colore della linea leggono `sample_bounds.first` (F), non `prices[0]`.
  - Z-29d-0: `_basePoint` è il `sample_bounds.first` del bersaglio.
  - Z-29d (D-Z29d-4, in attesa del developer): la linea principale dell'anteprima prende base e colore dal `first`
    della scheda.
  - Z-29b: lo stesso sulla scheda.

**Il contratto di Z-29d-0** (`AssetComparisonSignal`).
1. `params._basePoint`, facoltativo, è un `LineDataPoint`, iniettato dalla pagina come `_resolvedData`. Vale il punto
   del bersaglio nel giorno in cui parte il confronto: dopo Z-29a, il `sample_bounds.first` della voce del bersaglio,
   convertito come i suoi prezzi (`value` e, con la conversione, `originalValue`).
2. In %:
   - la linea si normalizza su `_basePoint.value`, non più sul suo primo valore allineato;
   - il fantasma della conversione si normalizza su `_basePoint.originalValue` quando c'è, altrimenti come oggi.
3. Un `_basePoint` inutilizzabile si ignora, e tutto resta come oggi: assente, non un oggetto, `missing: true`, oppure
   un `value` non finito o zero. Lo stesso per `originalValue` nel fantasma.
4. Nessun punto in più: il punto della base non si disegna. Le date restano quelle allineate, come per la scheda, che
   non disegna F (Q-Z29-1). La vista assoluta non cambia.
5. `toConfig()` lascia fuori `_basePoint`, come `_resolvedData`: è un dato del momento. Tiene gli altri parametri con
   `_`, che sono preferenze di stile salvate (il commento di `toConfig`, per esempio `_signalColor` di MACD).
   - Oggi `toConfig()` si chiama solo su un segnale appena creato (`createSignalConfig`), quindi niente perdite; la
     regola resta esplicita.
   - L'intestazione della classe dice che anche `_assetDisplayName` è escluso: non è vero (il codice esclude solo
     `_resolvedData`). Si corregge.
6. Senza `_basePoint` è tutto identico a oggi, per tutti i chiamanti di adesso: dettaglio, lista, cambi, anteprima.

**Fuori da Z-29d-0.**
- `FxPairSignal`: secondo l'analisi di Z, il negozio dei cambi ha ogni giorno di calendario. Con i dati di base
  `[first, …prices]` di Z-29b il cambio ha quindi il giorno F, e la sua base è già quella di F. Fa eccezione solo una
  coppia che comincia dopo F, un caso raro: nota per Z-29b.
- Nessuna pagina MkDocs descrive la base del confronto. Le pagine utente («in % le due linee partono da 0 %») parlano
  del dettaglio, che resta giornaliero. `_basePoint` si documenta con il suo primo uso, in Z-29b e Z-29d.
- Niente CHANGELOG (nessun cambio visibile), niente E2E (nessun chiamante), niente corsia (nessun backend).

**Passi.**
1. ✅ 20/10 — Rossi (`test-author`), in coda a `lib/charts/signals/__tests__/comparisonSignals.test.ts`, describe
   «AssetComparisonSignal — an injected base point (Z-29d-0)». Sono rossi oggi: la base iniettata per la linea e per il
   fantasma, e `toConfig()` senza `_basePoint`. Le guardie:
   - la vista assoluta non cambia;
   - un `_basePoint` inutilizzabile lascia tutto come oggi;
   - un `_basePoint` senza `originalValue` lascia il fantasma come oggi;
   - il punto della base non si disegna;
   - `toConfig()` tiene un parametro con `_` di stile e lascia fuori `_resolvedData`.
   > **Note implementazione**: 4 rossi e 25 guardie nuove (tabelle comprese), più i 29 test di prima: 58 in tutto. Un
   > secondo `test-author` ha aggiunto le righe di una decisione presa da me, che il primo aveva lasciato aperta.
   > **⚠️ Fuori pista**: il caso di un `value` inutilizzabile con un `originalValue` buono, per esempio
   > `{value: 0, originalValue: 200}`. Si leggeva in due modi. Ho deciso: il punto vale solo se vale il suo `value`, e
   > il fantasma vuole in più un `originalValue` buono. Con un `value` inutilizzabile si ignora tutto il punto, fantasma
   > compreso. Così vale alla lettera il punto 3 del contratto, «si ignora, e tutto resta come oggi».
   >
   > La base zero: l'analisi diceva «nessuna normalizzazione», il contratto «si ignora»; vale il contratto, cioè la
   > linea di oggi, misurata dal suo primo valore. La frase dell'analisi è corretta qui sotto.
2. ✅ 20/10 09:2x — I rossi visti rossi: `TAG=red bash files/scripts/z29d0_vitest.sh <file>`, carico 18. 4 falliti e 54
   passati su 58: falliscono esattamente i 4 rossi, ognuno sulla sua asserzione. Per esempio «the comparison restarts at
   0 % on its first drawn point (110 on 03-02) instead of measuring from … (100 on 03-01)», e «toConfig() saves the
   moment's base point with the chart settings». Nessun `TypeError`.
3. ✅ 20/10 — La cura.
   - `ChartSignal.ts`:
     - `TRANSIENT_PARAMS = {_resolvedData, _basePoint}`, che `toConfig()` lascia fuori (prima l'esclusione era una
       chiave sola, scritta nel codice);
     - corretti i due commenti, quello di `toConfig` e quello di `SignalConfig`.
   - `AssetComparisonSignal.ts`:
     - `isUsableBase`: un numero finito diverso da 0;
     - `basePoint()`, privato: il punto iniettato, oppure null se manca o è inutilizzabile;
     - `render()`: `p0 = basePoint()?.value ?? absData[0].value`;
     - `renderMulti()`, il fantasma: `originalValue` del punto se è utilizzabile, altrimenti come oggi;
     - l'intestazione, corretta: non dice più che `_assetDisplayName` è escluso.
   - Diff: +44 −10 righe in 2 file.
4. ✅ 20/10 — Prove leggere, con il carico fra 15 e 18:
   - `comparisonSignals`: 58/58;
   - i vicini, `files/scripts/z29d0_vitest_batch.sh`: 39 file in un solo processo, cioè tutti i test di `lib/charts/`,
     i gate di `src/*.gate.test.ts` (compreso quello della matematica finanziaria), `chartSettingsStore` e
     `chartSettingsStore.migration`, `ChartSignalsSection`, `SignalTreeSelect`, `chartCoreHelpers`,
     `assetDetailPriceQuery` e `assetDetailFxRequirements`: 1216/1216;
   - `npm run check`: 0 errori e 0 avvisi;
   - Prettier `--check` sui 3 file, `theme-roles --check` e `git diff --check`: puliti.
   - Log: `files/logs/z29d0_*`.
5. ✅ 20/10 — CHECKPOINT READY, poi FROZEN. Committato dal coordinatore: `bccf05cbb` (codice) e `c19d808fe` (giornale);
   entra in `dev_release2` col treno 2.

**Le risposte del developer su Z-29d** (20/10, mattina, dal coordinatore). Valgono per il lotto del dialogo.
- **D-Z29d-1: (a)**, nessuna linea di confronto finché la serie non arriva.
- **D-Z29d-2**, testuale: «se la connessione manca io mostrerei in toast di errore rosse che dice che la connessione è
  persa, se invece l'errore è nel segnale, in asset globa non mostriamo nulla, mentre in asset detail lo mostriamo
  dentro la card del segnale, come già avviene per i segnali tecnici. Al più si potrebbe fare in asset global la stessa
  cosa in impostazioni, anche se ha poco senso, vedi tu se è facile.» Secondo il coordinatore:
  - **connessione persa**: il toast rosso che esiste già, se c'è;
  - **errore nella pagina Assets**: nessuna linea;
  - **errore nel dettaglio dell'asset**: come i segnali tecnici, dentro la card del segnale;
  - **il messaggio nell'anteprima delle impostazioni**: facoltativo, solo se costa poco e riusa chiavi esistenti.
  - Da verificare all'inizio del lotto del dialogo:
    - se un toast rosso di connessione persa esiste già, e dove;
    - se il dettaglio mostra già nella card un confronto fallito. `ChartSignalsSection` ha già una diagnostica del
      confronto (`_conversionFailed`, `comparisonStatus`, i problemi tipizzati); manca forse il caso «richiesta
      fallita». Se manca, è lavoro nuovo da proporre.
- **D-Z29d-3: (a)**, l'anteprima salta il confronto con l'asset stesso, come la card.
- **D-Z29d-4: sì, riallineare** (developer, 20/10), testuale: «si dobbiamo riallinearle, giusto per sicurezza mi
  ripeto, lo 0 deve essere rispetto allo stesso giorno, se presente, se il segnale inizia con il suo primo punto
  assoluto dopo, allora lo 0 di quel segnale di confronto è calcolato rispetto al suo primo punto, anche se nella vista
  aggregata settimanalmente il punto richiesto è un martedì ma noi mostriamo nei punti il venerdì, significa che lo 0 è
  rispetto al valore di martedì, e il primo punto è il venerdì scalato rispetto a martedì, tutto chiaro? questo vale per
  entrambe, anzi in realtà è strano che siano 2 componenti, in origine erano lo stesso! c'è stata duplicazione di
  codice? riesci a fonderle e riportarle ad essere un unico componente mergiando il meglio dei 2?»
  - **La regola dello 0**, contratto di Z-29b e Z-29d:
    - la linea si misura dal valore del giorno F, il primo giorno vero del periodo;
    - un confronto si misura dal suo valore in F, oppure dal suo primo punto se comincia dopo F;
    - i punti disegnati (per esempio i venerdì di una vista settimanale) si scalano da quel valore;
    - vale per la scheda e per l'anteprima. Per i confronti è `_basePoint` (Z-29d-0); per la linea, il `first`.
  - **La fusione**: analisi nella sezione «20/10 · La scheda e l'anteprima», prima di Z-29d.

## 20/10 · Y-38 — il selettore dell'asset di confronto fa scorrere il nome lungo: analisi breve (sola lettura)

> **Richiesta del developer** (dal coordinatore, 20/10), testuale: «in segnali il selettore dell'asset di confronto non
> è praticamente mai largo abbastanza per far vedere il nome per intero dell'asset, possiamo aggiungere a quel
> componente la capacità di "scorrere" come avviene in quasi tutto il resto del progetto, quando il nome è troppo
> lungo?»
> Il coordinatore: «Usa il componente di scorrimento che il progetto ha già, e fai prima un'analisi breve […]. Se è
> piccolo e non tocca i file di Z-29b, puoi farlo dopo Z-29d-0.»
>
> - **Base:** `15603fe69`, uguale a `dev_release2` su questi file.
> - **ID:** Y-38, libero.

**Dove sta.** `lib/components/charts/ChartSignalsSection.svelte`, ramo `configuredAssets` (`:675-722`).
- È un `SearchSelect` in un riquadro largo `w-48`, cioè 192 px, con due snippet, che disegnano tutti e due icona e
  nome dentro `<span class="flex items-center gap-1.5 truncate">`. Da qui il nome tagliato con «…»:
  - `selectedItem`, il campo chiuso;
  - `item`, le righe della tendina.
- La tendina è larga quanto il campo: `dropdownMinWidth` vale 0, e la larghezza è il massimo fra il campo e quel valore
  (`SearchSelect.svelte:173`). Così anche le righe sono tagliate.
- Lo stesso componente sta in tre posti, quindi una modifica li copre tutti:
  - la finestra delle impostazioni (`ChartSettingsModal`), cioè la lista Asset e la lista dei cambi;
  - il pannello dei segnali del dettaglio asset (`assets/[id]/+page.svelte:2341`);
  - il pannello dei segnali del dettaglio cambio (`fx/[pair]/+page.svelte:1420`).
- Il selettore della coppia di valute (`w-44`) ha etichette corte, bandiere e codici: resta com'è.

**Cosa si riusa.** Lo scorrimento automatico del progetto, usato in 27 file (nomi di asset e broker nelle schede,
tabelle, titoli, la pagina Informazioni):
- l'azione `use:scrollOnOverflow` (`lib/actions/scrollOnOverflow.ts`): dopo 2 s di pausa il testo scorre fino alla
  fine, si ferma e riparte. Non fa nulla se il testo ci sta, né con il movimento ridotto;
- la classe comune `overflowScrollTextClass` (`lib/utils/overflowScroll.ts`).

`MarqueeName.svelte` del PAC è lo stesso, ma con peso e colore fissi; si usano direttamente azione e classe, come negli
altri 25 posti. La catena delle larghezze c'è già: `SearchSelect` mette gli snippet dentro
`<div class="flex-1 min-w-0">` (`:450`, `:533`).

**La modifica**, nei due snippet:
- il contenitore passa da `truncate` a `min-w-0`;
- il nome diventa `<span use:scrollOnOverflow class="{overflowScrollTextClass} text-xs" title={option.label}>`;
- in più, due import. Nessun colore nuovo; il file non ha un record nel cricchetto (0 classi di palette).

**Domanda** (di prodotto, consiglio in neretto). Scorrono anche le righe della tendina?
- (a) **sì, come il campo**: due nomi lunghi con lo stesso inizio si distinguono. Le tabelle del progetto fanno già
  scorrere più righe insieme;
- (b) solo il campo chiuso: nella tendina il nome resta tagliato, con il nome intero nel tooltip.

**Test.**
- **Vitest**, in `ChartSignalsSection.test.ts`, describe del confronto. Un nome lungo nel campo chiuso (e nelle righe,
  se (a)): il nome intero sta in un elemento dello scorrimento, trovato con `OVERFLOW_MARQUEE_SELECTOR` (il marcatore
  che lo scorrimento esporta, come nei test di `GrowthChart` e del rischio), con `title` uguale al nome.
- **Niente E2E nuova**: lo scorrimento è visivo, e le E2E del pannello usano i `data-testid`, che non cambiano.
- **La galleria**: gira con il movimento ridotto (`gallery.spec.ts:489`), quindi lo scorrimento non parte mai. Lo scatto
  del dettaglio con un confronto (`:5389`) può cambiare solo alla fine di un nome lungo: tagliato netto invece dei «…».

**Conflitti.**
- `ChartSignalsSection.svelte` non è fra i file di Z-29b, e oggi non l'ha aperto nessuno.
- È di Y: il lotto del dialogo (D-Z29d-2, la card del dettaglio) potrebbe toccarlo dopo. Lo stesso proprietario, in
  sequenza.
- T ha scritto che non lo tocca più. Y4a lo sposterebbe, ma è fermo.

**Costo**: circa 0,25 giorni, rossi e doc compresi. Doc: nessuna pagina descrive il selettore, quindi niente MkDocs;
CHANGELOG, una riga 🔄.

**Ordine**: dopo il commit di Z-29d-0. Prima i rossi (`test-author`), poi la cura, le prove leggere e il checkpoint.

> **Decisione** (coordinatore, 20/10 09:35): **(a)**, scorrono anche le righe della tendina, «come nel resto del
> progetto». Z-29d-0 committato (`bccf05cbb`, giornale `c19d808fe`). **Via a Y-38**: prima i rossi.

**Il lotto Y-38.**
1. ✅ 20/10 — Rossi (`test-author` `87d78b6d`, in sottofondo), describe «ChartSignalsSection — the asset-comparison
   selector scrolls a long asset name with the project marquee (Y-38)».
   - 2 rossi: il campo chiuso e le righe della tendina tengono ognuno un solo elemento dello scorrimento
     (`OVERFLOW_MARQUEE_SELECTOR`), con testo e `title` uguali all'etichetta intera, cioè nome e suffisso (`✓`, `📌`).
   - 1 guardia: il nome intero compare una volta sola nel campo.
   - Visti rossi da me (carico 18): 2 falliti su 24, ognuno sulla sua asserzione («the closed field holds no marquee
     with the whole label…»).
   > **Note implementazione**: non è fissato l'ordine dell'icona, che non ha un `data-testid`: per selezionarla
   > servirebbe il suo `src`. Non è fissato `👑`, perché in produzione non arriva in questa lista: la pagina toglie il
   > suo asset da `availableAssets`.
2. ✅ 20/10 — La cura, in `ChartSignalsSection.svelte`, nei due snippet:
   - il contenitore passa da `truncate` a `min-w-0`;
   - il nome diventa `<span use:scrollOnOverflow class="{overflowScrollTextClass} text-xs" title={option.label}>`;
   - in più, due import.
3. ✅ 20/10 — Prove leggere, con il carico a 21:
   - il file: 24/24;
   - i vicini, `files/scripts/y38_vitest_batch.sh`: 30 file in un solo processo, cioè i gate `src/*.gate.test.ts`, i
     test di `ui/select`, `SignalTreeSelect`, `chartCoreHelpers`, `comparisonSignals`, `loadComparisonData` e tutti i
     test che usano lo scorrimento: 1364/1364;
   - `npm run check` 0/0; Prettier, `theme-roles --check` e `git diff --check` puliti.
   - **Le E2E**, lette e non lanciate: `asset-detail.spec.ts:2816-2830` e `fx-detail.spec.ts:1952-1962` guidano il
     selettore con i `data-testid` (`…-trigger`, `ArrowDown`, `search-select-option-<id>`), che non cambiano.
   - **La galleria**: col movimento ridotto lo scorrimento non parte. Nello scatto del dettaglio con un confronto
     (`gallery.spec.ts:5389`) un nome lungo finisce tagliato netto, senza i «…».
   - **Doc**: nessuna pagina descrive il selettore.
4. ✅ 20/10 — CHECKPOINT READY, con una riga 🔄 nel CHANGELOG. Committato dal coordinatore: `252ddefbd` (codice) e
   `a91ff36cd` (giornale); entra in `dev_release2` col treno 2, insieme a Z-29d-0.

## 20/10 · La scheda e l'anteprima: due componenti? Analisi della fusione (sola lettura)

> **Richiesta del coordinatore** (20/10 09:35), dopo la risposta del developer a D-Z29d-4: «card e anteprima usano due
> componenti diversi? Trova dove si sono separati, cosa ha in più ognuno e quanto costa fonderli in un componente
> solo, "il meglio dei due". Senza codice: mandami l'analisi.»
>
> - **Base:** `c19d808fe`.
> - **Metodo:** il codice di oggi e la storia di git, in sola lettura.

**Sì, si sono separati, su due livelli.**

1. **Il grafico.**
   - Le schede (`AssetCard`, `FxCard`) disegnano con `PriceChartCompact.svelte`: 42 righe sopra un `LineChart`
     compatto.
   - L'anteprima è nata sullo stesso componente: `4f3ee08b5`, 9/3 11:20, «preview chart». L'intestazione di
     `PriceChartCompact` lo dice ancora: «Used by FxCard, AssetCard, ChartSettingsModal preview».
   - Sette ore dopo, `5487096df` (9/3 18:15: MACD su due assi, le bande, il selettore delle coppie) la porta su un
     `LineChart` diretto e non compatto, con il suo interruttore Abs/%. Sposta anche la conversione in % nel dialogo
     (`previewDataAbs`, il «Problema 1» del suo piano).
   - Il 10/3 `e57408376` toglie l'import. Da allora sono due grafici.
2. **I segnali: tre copie della stessa logica.** Per ogni segnale locale: crea l'istanza, inietta i dati del
   confronto o del cambio, poi `renderMulti`; e i risultati del backend.
   - `getRenderedSignals` della pagina dei cambi (`fx/+page.svelte:692`, dal 9/3, `099d252de`);
   - `getRenderedSignals` della pagina Asset (`assets/+page.svelte:1276`, dal 4/4, `2c1ab6e24`, la «parità della
     lista Asset»);
   - `renderLocalPreview` del dialogo (`ChartSettingsModal.svelte:287`, dal 23/7, `5b9dddb45`, insieme ai segnali del
     backend).
   - Anche `resolveGlobalBackendPreview`, cioè i segnali del backend dal vivo sulla curva sintetica, è scritta due
     volte. Le due copie sono uguali, salvo il dominio.

**Cosa ha in più ognuno, oggi.**
- **La scheda:**
  - il nome del bersaglio nel confronto (`_assetDisplayName`), mentre l'anteprima mostra «Asset #id»;
  - salta il confronto con sé stessa; D-Z29d-3 lo porta anche nell'anteprima;
  - i cambi presi dal negozio dei cambi, sempre nel verso salvato. Nella lista dei cambi, invece, l'anteprima legge
    `pairsDataMap`, che inverte la coppia bersaglio se è invertita sulla SUA scheda
    (`isCardInverted(p.config.slug)`). Una coppia mostrata invertita arriva quindi invertita nell'anteprima e diritta
    sulla scheda. Lo dice il codice; non l'ho ancora provato con un caso;
  - il grafico compatto: l'asse mini, la riduzione per densità (`chooseStaticResolution`), 80 px.
- **L'anteprima:**
  - le configurazioni che si stanno modificando, non ancora salvate;
  - in modalità globale, la curva sintetica con i segnali del backend dal vivo;
  - gli stati dei segnali del backend: da applicare, serve un asset vero, non disponibile;
  - il suo interruttore Abs/%, 140 px, le righe degli assi secondari;
  - **il colore per la linea di base.** Il grafico non compatto lo applica, quello compatto mai: `LineChart.svelte:450`,
    `colorByBaseline && !compact`, dal 3/3 (`0a551f1cb`, prima che l'anteprima esistesse). Così l'opzione «colora per
    la linea di base» si vede nell'anteprima e non sulle schede. È la differenza più visibile.
- **Uguale nelle due**: `normalizeToPercentage` sul primo punto disegnato. Dopo Z-29b deve passare a F (n3, D-Z29d-4).

**La proposta: il meglio dei due.**
1. **Una sola funzione per i segnali di una scheda**, pura, in `lib/charts/` (per esempio `renderCardSignals`).
   - Riceve le configurazioni, i dati assoluti, la base F, la vista e un contesto: i risolutori del cambio e del
     confronto (dati, nome, `_basePoint`), i risultati del backend, l'asset della scheda (per saltare sé stesso).
   - La usano la scheda Asset, la scheda del cambio e l'anteprima: stesse configurazioni, stessi segnali.
   - Le due `resolveGlobalBackendPreview` diventano una, con il dominio come parametro.
2. **Un solo componente del grafico.** `PriceChartCompact` riceve i dati assoluti e la base F, e fa lui la
   percentuale: la regola dello 0 sta in un posto solo. L'anteprima torna a montarlo, con l'altezza, l'interruttore e
   le righe degli assi che ha oggi.
3. **La regola dello 0 (D-Z29d-4) dentro quei due pezzi**: `first` per la linea, `_basePoint` per i confronti
   (Z-29d-0, già fatto).

**Domande** (di prodotto, consiglio in neretto).
- **F-1 · L'aspetto dell'anteprima:**
  - (a) **come la scheda, più grande**: grafico compatto con asse mini e riduzione per densità. È «un componente
    solo», e l'anteprima mostra davvero la scheda;
  - (b) grande con gli assi completi, come oggi, ma con gli stessi dati, la stessa base e gli stessi segnali della
    scheda.
- **F-2 · Il colore per la linea di base:**
  - (a) **anche sulle schede, come dice l'opzione**: in % rosso sotto lo 0 e verde sopra; in valore assoluto, rispetto
    al giorno F (n3);
  - (b) solo nell'anteprima, come oggi, e l'opzione lo dice;
  - (c) toglierlo anche dall'anteprima.
- **F-3 · Il verso delle coppie nell'anteprima della lista dei cambi**: con la funzione comune, (a) **lo stesso della
  scheda** (il verso salvato, più il `_inverted` del segnale). Si risolve da sé.

**Costo: circa 2 giorni.**
- La funzione comune e i suoi tre usi, con i Vitest di parità (scheda e anteprima danno gli stessi segnali): 1 giorno.
- Il componente con la base F e l'anteprima che lo monta: 0,5 giorni.
- E2E, cioè `asset-list`, `fx-chart-settings` e `fx-list`, e la doc: 0,5 giorni.
- La galleria, in più: se cambia l'aspetto dell'anteprima (F-1 a) o il colore delle schede (F-2 a), cambiano gli
  scatti `assets/chart-settings`, `fx/chart-settings` e quelli delle schede. Serve un cancello della galleria, cioè
  una pausa della macchina.

**Ordine e conflitti.**
- **Prima di Z-29b (consiglio).** Così Z-29b mette `first` e `_basePoint` in un posto solo, e l'anteprima resta
  allineata da sé. Z-29d si riduce al risolutore asincrono per un bersaglio nuovo: da circa 1,25 a circa 0,75 giorni.
  Dopo Z-29b, invece, Z-29b scrive la sua logica in `getRenderedSignals` e la fusione deve spostarla.
- **File toccati:**
  - un modulo nuovo in `lib/charts/`;
  - `PriceChartCompact.svelte`, `ChartSettingsModal.svelte`;
  - `AssetCard.svelte` e `FxCard.svelte`: la percentuale passa al componente;
  - `assets/+page.svelte`, il file principale di Z-29b;
  - `fx/+page.svelte`, la lista dei cambi: va chiesto a X e al coordinatore;
  - `LineChart.svelte`, solo con F-2 (a): ci lavora Z-29b, e c'entra il programma colori.
- **Colori**: nessun ruolo nuovo. F-2 (a) usa il verde e il rosso che il grafico ha già.
- **Lotto proposto**: Y-39, «una scheda e la sua anteprima: un grafico solo, una funzione dei segnali», di Y.

> **F-1 risposto dal developer** (20/10 ~10:00): l'anteprima usa il grafico del dettaglio, con il rendimento mobile; la
> proposta qui sopra è superata per il grafico (vale ancora la funzione comune dei segnali). Analisi rivista nella
> sezione «20/10 · Y-39 rivisto e Y-40». F-2 lo chiede il coordinatore; F-3 si risolve da sé.

## 20/10 · Y-39 rivisto e Y-40 (le tre viste): analisi (sola lettura)

> **F-1, risposta del developer** (dal coordinatore, 20/10 ~10:00), testuale: «in impostazioni farei il componente come
> in asset detail e ci aggiungerei anche il rendimento mobile come opzione, e nelle impostazioni globali questo fa si
> che tutte le card si spostano al rendimento e a livello di car il bottone percentuale abs lo farei diventare che ad
> ogni tocco cambia a rotazione, prima % per andare in percentuale, poi l'icona della rendita mobile per andare alla
> rendita mobile, e per finire in abs per tornare all'abs, e il bottone nella top bar abs/% ci aggiungerei anche la
> renditaà quindi è un triplo selettore, e ovviamente entrando poi in asset detail l'impostazione resta, ti torna?»
>
> La lettura del coordinatore:
> - l'anteprima delle impostazioni usa il grafico del dettaglio;
> - tre viste: assoluto, percentuale, rendimento mobile; nelle impostazioni globali la scelta vale per tutte le schede;
> - il pulsante della scheda gira % → rendimento → assoluto;
> - il selettore della barra in alto diventa triplo;
> - il dettaglio si apre nella vista scelta.
>
> Chiede: il costo lato server, la lista dei cambi, dove si salva la vista, l'ordine con Z-29b e la stima, le domande.
> F-2 lo chiede lui al developer; F-3 si risolve da sé; `fx/+page.svelte` lo chiede lui a X.
>
> - **Base:** `c19d808fe`, scritta come bozza mentre Y-38 era in consegna; copiata qui dopo il suo commit (`a91ff36cd`).
> - **Metodo:** il codice di oggi, in sola lettura; nessuna corsa.

### Lo stato di oggi

**Il rendimento mobile** è il segnale del backend `ASSET_CALENDAR_ROLLING_RETURN`
(`backend/app/services/signal_plugins/calendar_rolling_return/plugin.py`).
- Vale solo per gli asset: `compatible_domains = (SignalDomain.ASSET,)`.
- Il suo profilo di riduzione è `LAST_WITH_RANGE`.
- La finestra è `window_days`: preset 1S, 1M, 3M, 1A, oppure personalizzata in settimane, mesi o anni. La predefinita
  è 1M (`calendarReturnWindow.ts`).
- Per il primo giorno mostrato servono `window_days` giorni di storia prima.

**Lo chiede solo il dettaglio** (`charts.md`, tabella «price | calendar-return»):
- una voce per l'asset, con il segnale;
- una voce per ogni confronto, con `include_price: false`, lo stesso segnale e la stessa valuta;
- in questa modalità il dettaglio mostra solo i confronti: gli altri segnali restano salvati e nascosti.

**La vista oggi non si salva da nessuna parte.**
- Nel dettaglio, `primaryMode` parte da `'price'` (`assets/[id]/+page.svelte:206`) e `viewMode` da `'percentage'`
  (`:203`), a ogni visita.
- Nella lista, `globalViewMode` parte da `'percentage'` (`assets/+page.svelte:249`). La scelta della scheda
  (`AssetCard.svelte:103`) è in memoria e si azzera quando cambia il globale.
- Si salva solo la finestra, `calendarReturnWindow`, nelle impostazioni dei grafici: globali e per scheda, nel
  `localStorage` dell'utente, non nel backend.

**Il resto.**
- `PriceChartFull` ha già le proprietà per una forma ridotta: `hideToolbar`, `hideViewModeToggle`,
  `disableCandlestick`, `valueUnit`; niente `editMode`, `measureMode` o eventi.
- Il dettaglio dei cambi non ha il rendimento mobile.

### 1. Il costo lato server del rendimento su ogni scheda

**Cosa fa il server.** Ogni scheda in vista rendimento diventa una voce con un segnale del backend. Il server legge il
riempimento giornaliero dall'inizio meno la finestra fino alla fine, e calcola il rendimento giorno per giorno. In più
c'è una voce per ogni bersaglio di un confronto, come nel dettaglio; la si può tenere una sola per asset bersaglio, con
la stessa finestra e la stessa valuta.

**Ordine di grandezza**, su «Tutto» di 20 anni:
- circa 7 300 giorni per scheda, più il margine dei segnali (`BULK_SIGNAL_MARGIN_DAYS` = 400);
- con 100 asset, circa 770 000 giorni-voce: sta in un lotto da 800 000 (`BULK_ITEM_DAYS_BUDGET`), al più due;
- è il costo per il server della lista di prima di Z-29, cioè quello che Z-29 toglie alle schede senza segnali.

**La risposta dipende da Z-29s.**
- Senza Z-29s il rendimento torna giornaliero: circa 7 300 punti per scheda, la lista pesante di prima.
- Con Z-29s, che riduce i segnali nel backend con il loro profilo (qui `LAST_WITH_RANGE`), sono qualche centinaio di
  punti.
- Nel contratto di Z-29a, una voce con `max_points` e segnali dà 422 finché Z-29s non arriva.
- **Y-40 dipende quindi da Z-29s.**

**Con le serie campionate.** La regola dello 0 non serve: il rendimento è già una percentuale. F e `sample_bounds`
servono solo al prezzo in testa alla scheda.

**Un'alternativa più leggera, per dopo.** Calcolare il rendimento solo nelle date campionate: due prezzi per punto,
quello del giorno e quello di una finestra prima, invece di tutti i giorni. Si perde però l'intervallo del secchio che
`LAST_WITH_RANGE` porta. Ora non la propongo.

### 2. La lista dei cambi

**Proposta: per ora no.**
- Il segnale vale solo per gli asset, e il dettaglio dei cambi non ha il rendimento mobile.
- La regola «una lista offre le viste del suo dettaglio» tiene la lista dei cambi su Abs/%.
- Se il developer la vuole, è un lotto a parte: il segnale per i cambi, la modalità nel dettaglio dei cambi, poi la
  lista. Circa 2–3 giorni.

### 3. Dove si salva la vista

- **Un campo nuovo nelle impostazioni dei grafici**: `primaryView: 'absolute' | 'percentage' | 'calendar-return'`.
  - È globale e per scheda, nello stesso `localStorage` dell'utente.
  - Il valore predefinito è `'percentage'`, come oggi la lista e il dettaglio.
  - Il formato salvato si migra; il negozio ha già le sue migrazioni (`chartSettingsStore.migration.test.ts`).
- **Il valore globale** lo scrivono il selettore triplo della barra in alto e la finestra delle impostazioni globali.
  Come oggi l'interruttore della barra, cambiarlo azzera le scelte delle schede.
- **Il pulsante della scheda** gira % → rendimento → Abs e scrive la scelta di quell'asset.
- **Il dettaglio** si apre con la vista di quell'asset: la sua scelta, altrimenti la globale.
  - `'calendar-return'` diventa `primaryMode` rendimento.
  - `'absolute'` e `'percentage'` diventano `primaryMode` prezzo, con quella `viewMode`.
- **Niente URL**: è una preferenza, non un pezzo del link.
- **La finestra** resta `calendarReturnWindow`, la stessa nella lista e nel dettaglio.

### 4. Ordine e stima

**Y-39 rivisto: circa 2,5 giorni, prima di Z-29b** (la funzione comune dei segnali e l'anteprima sul grafico del
dettaglio).
- La funzione comune nei tre posti (scheda Asset, scheda del cambio, anteprima), con i Vitest di parità: 1 giorno.
- L'anteprima su `PriceChartFull` ridotto, con le tre viste: 1 giorno.
  - Nel globale la curva sintetica deve essere più lunga della finestra: oggi è di un anno, quindi con una finestra di
    1A il rendimento sarebbe vuoto.
  - Il rendimento sintetico passa da `/signals/preview`, come gli altri segnali del backend.
- E2E (`fx-chart-settings`, `asset-list`, `fx-list`) e doc: 0,5 giorni.
- In più un cancello della galleria, perché gli scatti `chart-settings` cambiano.

**Y-40, le tre viste: circa 4 giorni, dopo Z-29s.**
- Il campo, la migrazione e i test del negozio: 0,5 giorni.
- Il selettore triplo e il pulsante a rotazione, con le due E2E della lista che oggi provano Abs/%: in
  `asset-list.spec.ts`, «global Abs/% controls update every rendered AssetCard…» e «one AssetCard can override
  Abs/% until a later global change». 1 giorno.
- La richiesta della lista e il disegno della scheda: 1,5 giorni. Cioè la voce del rendimento per ogni scheda e i
  bersagli dei confronti, nei lotti.
- Il dettaglio che eredita la vista: 0,5 giorni.
- La doc per l'utente e per gli sviluppatori: 0,5 giorni.
- In più la galleria: la barra della lista e le schede in vista rendimento.

**Ordine proposto**: Y-39 → Z-29b → Z-29s → Y-40. Z-29d resta dopo Z-29b, ridotto al risolutore dell'anteprima, circa
0,75 giorni. **Totale nuovo per Y: circa 7 giorni** (2,5 + 4 + 0,75).

### 5. Le domande

**Di prodotto** (il consiglio in neretto):
- **V-1 · La scelta del pulsante della scheda:**
  - (a) **resta salvata per quell'asset, e il dettaglio la eredita** («l'impostazione resta»);
  - (b) è temporanea come oggi, e il dettaglio si apre con la vista globale.
- **V-2 · Un cambio di vista nel dettaglio:**
  - (a) **diventa la scelta di quell'asset, e la scheda la segue**;
  - (b) vale solo per quella visita.
- **V-3 · Il selettore della barra e le impostazioni globali:**
  - (a) **sono lo stesso valore, e cambiarlo azzera le scelte delle schede**, come oggi;
  - (b) le scelte delle schede restano.
- **V-4 · La finestra del rendimento nelle schede:**
  - (a) **la stessa del dettaglio** (`calendarReturnWindow`, globale o della scheda), che si cambia nelle impostazioni;
  - (b) una finestra fissa per la lista.
- **V-5 · I segnali in vista rendimento:**
  - (a) **solo i confronti, come nel dettaglio**; gli altri segnali restano salvati e nascosti;
  - (b) anche gli altri segnali.
- **V-6 · Il prezzo e il Δ in testa alla scheda:**
  - (a) **restano come oggi**, cambia solo il grafico;
  - (b) mostrano l'ultimo rendimento.
- **V-7 · Un asset con meno storia della finestra:**
  - (a) **la scheda mostra in piccolo lo stato del dettaglio** («storia insufficiente»), con le chiavi che esistono;
  - (b) la scheda torna alla vista prezzo.
- **V-8 · L'icona del rendimento sul pulsante:** (a) **quella del dettaglio** (`AssetChartModeToggle`).
- **V-9 · La lista dei cambi:** (a) **per ora no** (punto 2).

**Tecniche**, per il coordinatore e Z:
- Z-29s deve coprire anche il rendimento mobile; il profilo `LAST_WITH_RANGE` è già previsto.
- Nei lotti della lista, i bersagli dei confronti vanno tenuti una volta sola per asset.

### Rischi
- **Il selettore triplo nella barra della lista**: lo spazio sul telefono e le soglie del layout
  (`responsiveLayout`); le schermate cambiano.
- **Il costo del server**: con tutte le schede in vista rendimento torna quello di prima di Z-29. Le risposte restano
  piccole solo con Z-29s.
- **La migrazione delle impostazioni salvate**: un campo nuovo con il suo valore predefinito, nessun dato perso.

## 20/10 · Il lotto Y-39: decisioni, contratto, passi

> **Le decisioni del developer** (dal coordinatore, 20/10 13:16; scelte alle 12:1x):
> - Y-39 e Y-40 tutti e due nella 1.3.
> - V-1…V-8: tutte (a).
> - V-9: il rendimento mobile anche sui cambi, nella 1.3 (+2–3 giorni: il segnale per le coppie, la vista nel dettaglio
>   della coppia, le tre viste nella lista dei cambi).
> - Testuale: «mi pare che il grafico sia lo stesso componente anche in forex, se è così il componente va fattorizzato
>   si». Quindi Y-39 riunisce la scheda degli asset, la scheda dei cambi e l'anteprima.
> - F-2 (a): il colore della linea di base anche sulle schede.
> - Il rendimento mobile (Y-40): la finestra si sceglie nelle impostazioni; al primo avvio, la più grande del selettore
>   per il periodo mostrato.
> - L'ordine: Y-39 → Z-29b → Z-29s → Y-40 (con i cambi); Z-29d, ridotto, dopo Z-29b.
> - **Via per Y-39**: prima i rossi, la parità fra scheda e anteprima.
> - I file d'altri:
>   - `fx/+page.svelte`: X è d'accordo, purché il lavoro resti dentro Y-39;
>   - `LineChart.svelte` per F-2: il coordinatore chiede al coordinatore dei colori;
>   - `assets/+page.svelte`: Z aspetta la fine di Y-39 per cominciare Z-29b.
> - La galleria (gli scatti `chart-settings` e quelli delle schede) si rigenera in una pausa della macchina, a fine
>   lotto.
>
> **X** (20/10 ~13:20, direttamente): le copie del ciclo dei segnali locali sono cinque, non tre. Le altre due sono
> nelle pagine di dettaglio, file di X (FE4/FE5): `assets/[id]/+page.svelte` (`overlaySignals`, `:711-750`) e
> `fx/[pair]/+page.svelte` (`:~390-430`). Le differenze vere: i punti del cambio (`staleDays` nelle due pagine dei
> cambi; il dettaglio dell'asset li scrive in linea, con `missing` e senza `staleDays`) e il confronto (il dettaglio del
> cambio passa anche icona e tipo). Non chiede di allargare il lotto: chiede un contratto della funzione comune non
> legato alla scheda, con i risolutori come parametri, il punto del cambio con `missing` e `staleDays`, il confronto con
> nome, icona e tipo. Così le pagine di dettaglio potranno adottarla più avanti. N64, il suo prossimo lotto, tocca solo
> le richieste dei segnali del backend nei dettagli: nessun conflitto.
>
> - **Base:** `a91ff36cd`. dev `6e1761121` è 173 commit avanti, con Z-29a dentro. Sulle superfici di Y-39 cambia solo
>   l'avvio di ECharts (`chartInitOptions` di `chartPixelRatio.ts`) in `LineChart`, `PriceChartFull` e
>   `CandlestickChart`; pagine, schede, modale e `lib/charts/` sono uguali.

### Le copie, oggi (verificate sul codice)
- **Il ciclo dei segnali locali**, cinque copie:
  - in Y-39: `assets/+page.svelte` e `fx/+page.svelte` (`getRenderedSignals`), `ChartSettingsModal.svelte`
    (`renderLocalPreview`);
  - fuori, di X: le due pagine di dettaglio.
- **Il convertitore** «punto del cambio → punto del grafico»: `fx/+page.svelte:197` e `fx/[pair]/+page.svelte:332`
  (con `inverted`, `staleDays` da `extractDaysBack`), `assets/+page.svelte:1209` (senza `inverted`), più in linea in
  `FxCard.svelte` (due volte) e nel dettaglio dell'asset (senza `staleDays`).
- **`resolveGlobalBackendPreview`**: due copie uguali, salvo il dominio (le due liste).

### Il contratto di Y-39a: un modulo puro, non legato alla scheda
Il modulo è `lib/charts/chartSignalRendering.ts`, nuovo. Sta accanto a `chartPageSignals.ts` (dei dettagli, che X
toccherà con FE4), ma separato: niente conflitti con X.
- **Le fonti**, `SignalDataSources`:
  - `fxPairData(slug)`: i cambi diritti, che il `_inverted` del segnale gira;
  - `comparisonTarget(id)`: `{data, displayName?, iconUrl?, assetType?, basePoint?}`, oppure null;
  - `selfAssetId?`: l'asset del grafico.
- **`fxPointToLineDataPoint(point, inverted)`**: `value`, `missing` e `staleDays`.
- **`renderLocalSignal(config, baseData, viewMode, sources)`** e `renderLocalSignals(configs, definitionsByType, …)`,
  con il meglio delle copie:
  - il confronto ha il nome del bersaglio (dalla scheda), icona e tipo quando ci sono (dal dettaglio del cambio) e
    `_basePoint` (Z-29d-0);
  - niente confronto con sé stesso (D-Z29d-3 a); un bersaglio senza dati si salta;
  - la coppia arriva dai dati diritti, girata dal `_inverted` del segnale (F-3 a);
  - nessuna mutazione della configurazione.
- **`renderBackendResults(configs, results, …)`**: i risultati salvati, con la configurazione corrente, come oggi nelle
  due liste.
- **Chi lo usa in Y-39a:**
  - la lista Asset, per le schede e la modale, con le fonti della pagina: i cambi dal negozio, i confronti dalle schede
    della lista, `selfAssetId` della scheda;
  - la lista dei cambi, per le schede e la modale: `comparisonTarget` resta null come oggi, perché la lista non carica
    asset (vedi Y-41);
  - la modale: una prop nuova, `signalSources`; escono `pairsDataMap` e `assetsDataMap`.
- **La parità** fra scheda e anteprima viene per costruzione: le due chiamano `renderLocalSignal` con le stesse fonti e
  gli stessi dati assoluti. `pairData` è la `chartData` della scheda; per i cambi, la stessa conversione con
  l'inversione della scheda.
- **Gli effetti visibili**, tutti già decisi:
  - nell'anteprima il confronto ha il nome del bersaglio, non più «Asset #id»;
  - l'anteprima non disegna più il confronto con sé stesso;
  - nella lista dei cambi, la coppia è nel verso della scheda.
  - Icona e tipo del confronto: il grafico compatto delle schede non li mostra; l'anteprima sul grafico del dettaglio
    (Y-39b) sì, come nel dettaglio.

### Il contratto di Y-39b
- **L'anteprima sul grafico del dettaglio** (F-1): `PriceChartFull` al posto di `LineChart`. Riceve i dati assoluti, la
  vista dell'anteprima (`externalViewMode`), i segnali, l'aspetto e le scale degli assi delle impostazioni in modifica.
  - La proposta di aspetto (domanda P-Y39 al coordinatore): la barra degli strumenti nascosta, perché resta il
    selettore della modale, che in Y-40 diventa triplo; solo linea, perché la lista non ha OHLC; niente eventi, misure
    o modifica; circa 220 px di altezza (oggi 140); lo zoom con la rotella come nel dettaglio, senza barra visibile.
- **F-2 (a)**: `LineChart` applica `colorByBaseline` anche in modalità compatta (oggi `colorByBaseline && !compact`,
  `:450`).
  - In valore assoluto la base è il primo punto dei dati in ingresso, prima della riduzione per densità. Oggi è il primo
    punto ridotto, cioè la fine del primo secchio; così il colore segue la regola dello 0, il giorno F.
  - Una prop facoltativa, `baselineValue`, la sostituisce: Z-29b ci passa F (n3). `PriceChartCompact` la inoltra.
  - Serve l'OK del coordinatore dei colori su `LineChart.svelte`, che chiede il coordinatore.
- **Doc, CHANGELOG, E2E e galleria**: `charts.md` (la funzione comune, l'anteprima, il colore sulle schede) e le pagine
  utente delle impostazioni dei grafici; due righe 🔄; le E2E `asset-list`, `fx-list` e `fx-settings`; la galleria
  nella pausa della macchina.

### Proposte al coordinatore
- **T-Y39-1 · Due checkpoint.**
  - Y-39a (il modulo, le due liste, la modale; circa 1 giorno) libera `assets/+page.svelte` per Z-29b.
  - Y-39b (l'anteprima sul grafico del dettaglio, F-2, la doc; circa 1 giorno) non tocca `assets/+page.svelte` e va in
    parallelo con Z-29b.
  - Su `LineChart.svelte` Z-29b sposta la soglia della densità (`:193`, `:296-301`), mentre F-2 tocca `:450` e aggiunge
    una prop: pezzi diversi.
  - **Consiglio: sì.**
- **T-Y39-2 · La terza vista dell'anteprima, il rendimento mobile, va in Y-40.**
  - Nelle impostazioni quella vista è la vista salvata (V-3 a: barra e impostazioni globali sono lo stesso valore), e
    nessuno la legge prima di Y-40.
  - I dati del rendimento di una scheda vera arrivano con la richiesta della lista di Y-40, dopo Z-29s.
  - In Y-39 l'anteprima ha Abs e % come oggi, sul grafico del dettaglio.
  - Tenerla in Y-39 costa circa +1 giorno: un risolutore asincrono per la scheda e una curva sintetica più lunga della
    finestra.
  - **Consiglio: in Y-40.**
- **P-Y39 · L'aspetto dell'anteprima** sul grafico del dettaglio: la proposta qui sopra.
- **La base**: aggiornarla quando è comodo, prima della cura di F-2.

### Fuori dal lotto, da registrare nel backlog al checkpoint
- **Y-41**: nella lista dei cambi la finestra delle impostazioni offre il confronto con un asset, ma né la scheda né
  l'anteprima lo disegnano, perché la lista non carica asset. È così già oggi, e resta uguale.
- **Y-42**: le due pagine di dettaglio, file di X, adottano `chartSignalRendering.ts` e il convertitore comune. Il
  cancello `signalRendering.gate` le tiene in una lista che può solo accorciarsi. Da proporre a X tramite il
  coordinatore.
- `FxCard.svelte` converte i punti in linea, due volte: può passare a `fxPointToLineDataPoint` chi tocca quel file
  (FE5, X).

### Le risposte del coordinatore (20/10 13:34)
- **T-Y39-1: sì, due checkpoint.** Y-39a libera `assets/+page.svelte` per Z-29b; Y-39b va in parallelo.
- **T-Y39-2: sì**, la terza vista dell'anteprima va in Y-40.
- **P-Y39: va bene**, «è proprio quello che ha chiesto il developer».
- **Il contratto staccato dalla scheda, per X: ok.** Y-41 e Y-42 si registrano al checkpoint.
- **La base** la aggiorna il coordinatore al checkpoint di Y-39a, con l'albero pulito, prima della cura di F-2.
- **Le condizioni di DV per F-2 su `LineChart.svelte`** (dal coordinatore dei colori):
  1. Non toccare `echarts.init(…, chartInitOptions(chartContainer))`: è il DPR, sorvegliato dal gate K-13. È in dev,
     non ancora sulla mia base.
  2. I colori sono gli stessi di oggi, `greenColor` e `redColor`: in `LineChart` nessun letterale e nessun nuovo
     `isDark ? … : …`. `chartTheme.ts` non si tocca, perché DV-10 lo porterà sui ruoli.
     - Oggi `LineChart` li prende da `COLORS.greenLight`, `greenDark`, `redLight` e `redDark` (`:140-143`,
       `:417-418`), e restano così.
  3. Il perimetro: l'unico chiamante compatto è `PriceChartCompact`, cioè `AssetCard` e `FxCard`.
     - Verificato: i quattro `LineChart` del rischio (`RiskAnalysisPanel:725` e `:1061`, `UnderwaterChart:63`,
       `L4Simulation:246`) non sono compatti e passano `colorByBaseline={false}`.
  4. Prima del checkpoint:
     - `front-portfolio chart-safety-unit`, `LineChart.test.ts` e `chartCoreHelpers.test.ts`;
     - poi una scheda nei due temi, cambiando tema senza ricaricare: il verde e il rosso seguono il tema, e la cache
       delle frecce non tiene colori vecchi (la regola di Y-8).

### I passi di Y-39a
1. ✅ 20/10 · I rossi (`test-author` `47f7b156`):
   - `lib/charts/__tests__/chartSignalRendering.test.ts`: il contratto del modulo, rosso perché il modulo non c'è;
   - `lib/components/charts/ChartSettingsModal.test.ts`: l'anteprima con `signalSources` (il nome del confronto, la
     coppia diritta e il suo `_inverted`), con i due grafici possibili sostituiti da un registratore; una guardia, un
     segnale locale senza dati esterni, nei due modi;
   - `chartCoreHelpers.test.ts`: le due liste passano `signalSources`, non passano più `pairsDataMap` né
     `assetsDataMap`, e importano il modulo;
   - `src/signalRendering.gate.test.ts`: `signalFromConfig(` solo nel modulo, più le due pagine di dettaglio, copie
     note che possono solo diminuire.
2. ✅ 20/10 · I rossi visti rossi, con il carico a 11: 57 rossi e 318 verdi su 375, in 4 file, ognuno rosso per la
   ragione dichiarata (il modulo assente, le props della modale, le due liste, il cancello).
3. ✅ 20/10 · La cura.
   > **Note implementazione**:
   > - `lib/charts/chartSignalRendering.ts`, nuovo: il contratto qui sopra, più `NO_SIGNAL_SOURCES`, le fonti vuote che
   >   la modale prende quando la pagina non ne passa (coppie e confronti non disegnati, gli altri segnali sì).
   > - `ChartSettingsModal.svelte`: la prop `signalSources` al posto di `pairsDataMap` e `assetsDataMap`;
   >   `renderLocalPreview` chiama `renderLocalSignal` con quelle fonti. Nessun `signalFromConfig(` nel file.
   > - `assets/+page.svelte`: `signalSourcesFor(selfAssetId)` (i cambi dal negozio, diritti; i confronti dalle schede,
   >   con nome, icona e tipo; la scheda stessa esclusa) per le schede, e `settingsSignalSources`, un `$derived` sulla
   >   scheda della modale, per l'anteprima. `getRenderedSignals` diventa `renderLocalSignals` più
   >   `renderBackendResults`; `resolveGlobalBackendPreview` usa `renderBackendResults`. Tolti il convertitore locale,
   >   `buildPairsDataMap` e le due mappe passate alla modale.
   > - `fx/+page.svelte`: `fxListSignalSources`, i cambi dal negozio, diritti, e nessun confronto (Y-41). Stesso
   >   cambio per `getRenderedSignals` e `resolveGlobalBackendPreview`; il convertitore viene dal modulo, e la mappa
   >   `pairsDataMap` girata scheda per scheda (F-3) esce.

   > **⚠️ Fuori pista**:
   > - I risolutori dei cambi sono di una riga, senza `try`: `getFxStore` crea il negozio quando manca, quindi non
   >   lancia, e il modulo tratta una serie vuota come una assente.
   > - `TimeSeriesStore` non è reattivo (una `Map`). La prop di prima era un'istantanea memorizzata, rifatta solo
   >   quando cambiava `fxPairSlugs`; ora l'anteprima legge il negozio a ogni ricalcolo, quindi è aggiornata almeno
   >   quanto prima. Le schede leggono il negozio come prima.
   > - `renderBackendResults` scrive `console.error` per una definizione mancante, mentre l'anteprima globale prima
   >   saltava in silenzio. Lì non può succedere: il piano delle richieste nasce dalle definizioni.
   > - Icona e tipo arrivano ora anche ai confronti delle schede, ma `LineChart` non li disegna (non usa
   >   `signalLabel`): nessun effetto visibile in Y-39a. Si vedranno nel tooltip dell'anteprima con `PriceChartFull`
   >   (Y-39b).
4. ✅ 20/10 · Le prove leggere, con il carico sotto 35:
   - i 4 file dei rossi: **375/375** (`files/logs/y39a_cure.log`);
   - i vicini, 31 file in un processo solo (i `src/*.gate`, i segnali, i confronti, lo store delle impostazioni,
     `fxStoreRegistry`, `LineChart`, `FxCard`, `ChartSignalsSection`, `SignalTreeSelect`): **1044/1044**
     (`files/logs/y39a_neighbours.log`);
   - `npm run check`: 0 errori e 0 avvisi;
   - Prettier: tre file riscritti (il modulo e le due liste), solo nelle mie righe; le due liste erano pulite a HEAD;
   - `theme-roles --check` e `git diff --check`: puliti.
   - Da fare dopo l'OK del coordinatore: le tre righe del runner in `_frontend_utility.py`, un file del programma
     colori, poi `check-orphans`:
     - `front_utility_unit`: `chartSignalRendering.test.ts` dopo `chartPageSignals.test.ts` (`:47`), e
       `src/signalRendering.gate.test.ts` dopo `src/instanceProfile.gate.test.ts` (`:144`);
     - `front_component_unit`: `ChartSettingsModal.test.ts` dopo `ChartSignalsSection.test.ts` (`:355`).
4b. ✅ 21/10 · La rifinitura dei rossi e le prove leggere sulla base fusa (HEAD `e64e9df0f`, merge di `dev_release2`
   `208199bf6`; Linux, carico 3-10):
   > **Note implementazione**:
   > - Le parole della fase rossa sono sparite dai quattro file di test. Cambiate solo parole, titoli e import:
   >   asserzioni e numero dei test uguali (375).
   >   - `chartSignalRendering.test.ts`: import statico del modulo al posto di `exported()` con l'import dinamico
   >     `@vite-ignore`; i tipi copiati a mano (`ViewMode`, `FxStorePoint`, `ComparisonTarget`, `SignalDataSources`,
   >     `ChartSignalRendering`) sono i tipi del modulo (`ViewMode` ne è derivato con `Parameters<…>`); tolte le
   >     righe `const x = await exported(…)` e gli `async` che non servivano più; la sezione «Red until the cure» è
   >     diventata «How the cases are built».
   >   - `ChartSettingsModal.test.ts`: tolta la copia locale di `SignalDataSources` (import del tipo del modulo) e il
   >     `as unknown as`: `props` è ora `ComponentProps<typeof ChartSettingsModal>`; tolti «Red today», «(to be)» e
   >     i «RED:» dai titoli; la sezione «Red and green» è diventata «Cases and guards».
   >   - `signalRendering.gate.test.ts`: tolto il paragrafo «Red until Y-39a», «(to be)» e i «RED until Y-39a — » dai
   >     due titoli; due verbi al passato nell'introduzione.
   >   - `chartCoreHelpers.test.ts`: tolta la frase «Red until Y-39a» dal commento.
   > - `chartSignalRendering.ts`: una sola riga di tipo, `FxRatePoint.backwardFillInfo` accetta anche
   >   `actualRateDate?: string` (c'è in `FxDataPoint`): serviva perché i test passino al modulo i punti dello
   >   store senza un tipo copiato. Nessun cambio di comportamento.
   > - Prove: Vitest 4 file **375/375**; 31 vicini in un processo **1044/1044** (stessa lista del 20/10, `files/logs/
   >   y39a_neighbours.txt`); Prettier `--check` sugli 8 file toccati o vicini: pulito; `theme-roles --check`: pulito;
   >   `git diff --check`: pulito; `dev.py test check-orphans`: tutti raggiungibili (frontend `src` 588, e2e 147).
   >
   > **⚠️ Fuori pista**:
   > - `dev.py front check`: **1 errore, 0 avvisi**, in un file che non è mio:
   >   `src/lib/features/instance/instanceConfig.svelte.ts:68` («Property 'client_log_level' does not exist on type
   >   'InstanceConfigResponse'»). Viene da `dev_release2` (H-60): il backend ha `client_log_level`
   >   (`backend/app/schemas/system.py`), ma `frontend/src/lib/api/generated.ts` (ignorato da git) è ancora quello di
   >   prima della fusione. Si cura con `api sync`, che è del coordinatore: non l'ho lanciato. Nessun errore nei file
   >   di Y-39a.
5. ✅ 21/10 · Lo slot E2E (coordinatore, 12:44-14:00), Chromium 1228 sulla macchina (`~/.cache/ms-playwright/chromium-1228`).
   > **Note implementazione**: corsia 6189 + `/tmp/librefolio-r13-y`, popolata da zero (`db populate --force --clean`, rc 0,
   > 10 s); ogni spec dentro `flock /tmp/librefolio-heavy.lock`, `--workers 2`, `nice`, uno alla volta, HEAD `e64e9df0f`,
   > carico 3,9-5,1. Comando: `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test --test-port 6189
   > --data-dir /tmp/librefolio-r13-y --workers 2 <categoria> <spec>`.
   > - `front-fx fx-settings`: **3/3** (8,4 s di test; 4 min 19 s con la build di debug e l'avvio), guardia d'allargamento
   >   superata (3 test, non la categoria);
   > - `front-fx fx-list`: **25/25** (54,9 s);
   > - `front-asset asset-list`: **43/43** (2,0 min).
   > Nessun rosso, nessun ripetuto. Porta 6189 libera a fine corsa (`lsof`: nessun ascoltatore). Log in
   > `…/scratchpad/y39a_e2e_{fx-settings,fx-list,asset-list}.log` (cartella di sessione, non nel repo).
6. ✅ 21/10 · CHECKPOINT READY (dopo l'E2E). Da lì Z-29b può partire su `assets/+page.svelte`.

### I passi di Y-39b
1. ✅ 21/10 · I rossi (HEAD `89e8b2e61`, `api sync` fatto):
   - `LineChart.test.ts`: nuovo `describe` «a compact chart colours its line by its baseline…» (9 casi): la base tratteggiata sul
     compatto, la base = primo punto dei dati in ingresso (8 anni di giorni, disegnati a settimane), `baselineValue`, la base 0 in
     percentuale, verde/rosso chiari, scuri e ridisegno al cambio tema, due guardie (colorByBaseline spento; la base del grafico
     pieno), `PriceChartCompact` che inoltra `baselineValue`. **7 rossi, 2 verdi** (le guardie), ognuno per la causa dichiarata.
   - `ChartSettingsModal.test.ts`: nuovo `describe` «the detail page's chart» (5 casi): il modulo montato è `PriceChartFull`, dati
     assoluti e `externalViewMode` dal selettore della modale, solo linea / niente barra, eventi, misure, modifica / 220 px,
     estetica e scale in modifica (la scala % nella vista %). **5 rossi, 8 verdi** (i casi di Y-39a, che non cambiano).
2. ✅ 21/10 · La cura.
   > **Note implementazione**:
   > - `LineChart.svelte`: la prop `baselineValue` (nel codice `baselineOverride`); `useBaselineColoring = colorByBaseline` (via
   >   `&& !compact`); la base assoluta è il primo punto non mancante di `data` (prima della riduzione per densità), sostituita da
   >   `baselineValue` se finito; in percentuale 0. `echarts.init(…chartInitOptions…)`, i colori `COLORS.*` e `chartTheme.ts`
   >   non toccati; nessun nuovo `isDark ? … : …`. Solo `:450` e la prop: la soglia di densità resta a Z-29b.
   > - `PriceChartCompact.svelte`: inoltra `baselineValue`.
   > - `ChartSettingsModal.svelte`: `PriceChartFull` al posto di `LineChart` (dati assoluti, `externalViewMode`, `hideToolbar`,
   >   `disableCandlestick`, `hideViewModeToggle`, `externalChartType="line"`, 220 px, estetica e scale in modifica,
   >   `overlaySignalInfoMap` e le etichette di stale); via `previewData` e `normalizeToPercentage` (la percentuale la prende il
   >   grafico); due `data-testid` sui bottoni Abs / %.
   > - Doc (agente `docs-writer`, solo inglese): `user/fx/chart-settings.en.md` e `developer/frontend/components/charts.md`
   >   (tre sezioni: `#signal-rendering`, `#settings-preview-chart`, `#cards-baseline-colour`). `mkdocs build` e `check-links` exit 0.
   >
   > **⚠️ Fuori pista**:
   > - `hideToolbar` nasconde solo la `ChartToolbar`: `PriceChartFull` disegna sul grafico anche un selettore flottante (tipo di
   >   grafico, Abs/%). Visto nella prova a mano (il test dei props non lo vedeva): aggiunti `disableCandlestick` e
   >   `hideViewModeToggle`, con il test rosso prima.
   > - Sulle schede compare ora la linea tratteggiata della base (la disegna `LineChart` ogni volta che colora per base): è la
   >   regola del contratto, da confermare a occhio dal developer.
   > - **O2 (`backendRenderer.ts:356`)**: lasciato a Z-29b. La base `baseData[0]` serve i segnali del backend in % e deve valere
   >   `sample_bounds.first`, che è dei dati della pagina `assets/+page.svelte` (file di Z-29b): serve un `baseValue` nelle opzioni
   >   del renderer e in `renderBackendResults`, passato dalla pagina insieme al `baselineValue` della scheda (stessa F).
3. ✅ 21/10 · Le prove leggere (carico 3-8):
   - 5 file Vitest (`LineChart`, `ChartSettingsModal`, `chartCoreHelpers`, `signalRendering.gate`, `chartSignalRendering`): **403/403**;
     `FxCard.test.ts` + `chartCoreHelpers`: 307/307;
   - `dev.py test front-portfolio chart-safety-unit` (in `flock`): **9 file, 144/144**;
   - `dev.py front check` (dopo `api sync`, in `flock`): **0 errori, 0 avvisi** (due volte, anche dopo l'ultima modifica);
   - Prettier `--check` sui 5 file: pulito (tre riscritti nelle mie righe, erano puliti a HEAD); `theme-roles --check` pulito;
     `git diff --check` pulito.
4. ✅ 21/10 · La prova a mano, nei due temi (build di debug, corsia 6189, `e2e_test_user`, server fermato, porta libera):
   - la modale di una scheda: anteprima di 220 px, senza selettori sul grafico, nei due temi;
   - schede della lista, cambiando tema senza ricaricare: pixel del canvas nei colori scuri (`#4ade80`/`#f87171`) e zero nei chiari
     dopo il passaggio al buio; di nuovo chiari e zero scuri tornando al chiaro (la cache non tiene colori vecchi).
5. ✅ 21/10 · Slot E2E (coordinatore), corsia 6189 + `/tmp/librefolio-r13-y`, HEAD `89e8b2e61` + il lotto; ogni spec in `flock`,
   `nice`, `--workers 2`, `LC_ALL=en_US.UTF-8`, una alla volta.
   > **Note implementazione**: comando `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test --test-port 6189
   > --data-dir /tmp/librefolio-r13-y --workers 2 <categoria> <spec>`.
   > - `front-fx fx-settings`: **3/3** (8,9 s);
   > - `front-fx fx-list`: **25/25** (56,0 s);
   > - `front-asset asset-list`: **43/43** (2,0 min).
   > Nessun rosso, nessun ripetuto. Porta 6189 libera a fine corsa (`lsof`: nessun ascoltatore). Log in
   > `salvataggi-worktrees-20261021/ondata2/y-e2e-{fx-settings,fx-list,asset-list}.log`.
6. ✅ 21/10 · Seguito da C2 (colori): `pendingColor` di `LineChart` non ha più il getter come valore di default della prop (Svelte lo
   tiene: dopo un cambio tema senza ricarica restava il colore vecchio).
   > **Note implementazione**: rosso prima (`LineChart.test.ts`, nuovo `describe` «the pending-edit colour follows the theme after a
   > rebuild»: `PRICE_SERIES.pendingEditPoint` sostituito da un getter, colore cambiato, grafico ridisegnato con
   > `notifyChartColorsChange()`: restava quello del montaggio). Cura di una riga: prop senza default, `pendingColor ?? PRICE_SERIES.pendingEditPoint`
   > dove si costruisce la serie. Una guardia: la prop `pendingColor` vince ancora. `LineChart.test.ts` **25/25**; `front check`
   > 0 errori e 0 avvisi (in `flock`); Prettier, `theme-roles --check`, `git diff --check` puliti. Non toccati `echarts.init` né `chartTheme.ts`.

## 21/10 notte · Il lotto Y-40 (asset) e il test di `OtherPeriodEffectsTable` (ondata 3)

> **Base:** `2879ae3e4` (= `dev_release2`, treno 7), `api sync` fatto. Brief: `ondata3/kickoff-Y.md`. Le pagine di dettaglio
> sono di X (Y-42): qui solo il contratto della vista d'apertura, che X legge dopo il commit.

### Il contratto (V-1…V-8 tutti (a))
- **Lo store** (`chartSettingsStore.svelte.ts`), versione di archivio sempre 3: due campi nuovi, riempiti dalla pulizia
  (`sanitizeSettings`) e riscritti all'idratazione:
  - `primaryView: 'absolute' | 'percentage' | 'calendar-return'`, predefinito `'percentage'`;
  - `calendarReturnWindowAuto: boolean`: vero finché l'utente non sceglie una finestra; un archivio di prima vale vero solo
    se la sua finestra è quella predefinita (1M). Un salvataggio con una finestra diversa da quella salvata la segna scelta,
    chiunque salvi (anche il dettaglio di oggi, che salva `...settings` con la finestra nuova).
- **Le funzioni:**
  - `setScopePrimaryView(view, scope)`: la barra in alto e le impostazioni globali; azzera la vista di ogni scheda dello
    scope (V-3 a), il resto dei loro salvataggi resta; l'altro scope non cambia;
  - `setItemPrimaryView(slug, view, scope)`: il pulsante della scheda e il dettaglio (V-1 a, V-2 a);
  - `nextCardPrimaryView`: % → rendimento → Abs → %;
  - `detailModesForPrimaryView(view)` → `{primaryMode, viewMode}` e `primaryViewForDetailModes(primaryMode, viewMode)`:
    **il contratto per X** (il dettaglio si apre con `getSettingsForPair('asset-<id>', 'assets').primaryView`, e salva il
    suo cambio con `setItemPrimaryView`);
  - `effectiveCalendarReturnWindow(settings, rangeDays)`: la scelta, o in automatico il preset più grande che sta nel
    periodo (`largestCalendarReturnPresetFor` in `calendarReturnWindow.ts`; sotto i 7 giorni, 1S). Anche questa è per X.

### I passi
0. ✅ 21/10 · `OtherPeriodEffectsTable.test.ts`: `plainAmount` scriveva l'importo atteso con `toLocaleString(undefined, …)`, la
   lingua del sistema; il componente con `uiLocale()`. Rosso: con `LC_ALL=it_IT.UTF-8` **3 rossi su 4**, con `en_US` 4/4.
   Cura nel test: `toLocaleString(uiLocale(), …)`. Verde **4/4 con `it_IT.UTF-8` e 4/4 con `en_US.UTF-8`**.
1. ✅ 21/10 · Lo store: i rossi e la cura.
   > **Note implementazione**: rossi in `chartSettingsStore.test.ts` (nuovo `describe` «the primary view and the rolling-return
   > window (Y-40)»): **15 rossi** su 55, gli altri 40 verdi; la causa: funzioni e campi assenti. Cura nello store e in
   > `calendarReturnWindow.ts`. Il caso dell'archivio di prima spostato in `chartSettingsStore.migration.test.ts` (nuovo
   > `describe` «a payload from before Y-40»), con le stesse asserzioni. Tutti i test degli store: **29 file, 720/720**.
   >
   > **⚠️ Fuori pista**: niente salto di versione (3 → 4): i due campi nuovi hanno un predefinito, e la pulizia li riempie
   > già; un salto avrebbe cambiato solo il numero nei test della migrazione di CP-10a.
2. ✅ 21/10 · La richiesta della lista: `reducedPriceQuery.ts`.
   > **Note implementazione**: rosso in `reducedPriceQuery.test.ts` (nuovo `describe` «a card in the rolling-return view
   > (Y-40)»): **2 rossi**, la guardia verde. Cura: `CardQueryInput.calendar = {signals, targetCurrency}`; con questo ogni
   > bersaglio di un confronto parte sempre (un segnale non è in cache), `sample_like` della scheda, `include_price: false`,
   > con il segnale e `target_currency` = la valuta della scheda (come il dettaglio chiede i confronti). **29/29**.
3. ✅ 21/10 · La scheda: `AssetCard.svelte`, nuovo `AssetCard.test.ts` (una riga additiva nel runner, `front_component_unit`,
   dopo `AssetTable.test.ts`).
   > **Note implementazione**: **9 rossi, 2 verdi** su 11 (le due prove in %, che non cambiano). Cura: via
   > `globalViewMode` e la scelta in memoria della scheda; props `primaryView`, `onprimaryviewchange`, `calendarReturn`,
   > `calendarOverlaySignals`; il pulsante dice dove va (`data-next-view`) e gira % → rendimento → Abs; in vista rendimento il
   > grafico disegna il rendimento (già in %, base 0) con i confronti, scala %; mentre carica un segnaposto
   > (`asset-card-calendar-loading`), senza dati il messaggio del dettaglio (`asset-card-calendar-problem`, `data-state`,
   > `data-problem-code`); la scheda pubblica `data-calendar-state`. `AssetTable.test.ts`: la prop rinominata
   > (`globalViewMode` → `primaryView`). **28/28** con `AssetTable.test.ts`.
   >
   > **⚠️ Fuori pista**: l'icona del rendimento. Nel dettaglio (`AssetChartModeToggle`) il rendimento usa `Percent`, la
   > stessa icona della percentuale: sul pulsante a rotazione «vai in %» e «vai al rendimento» sarebbero uguali. Messo
   > `CalendarSync` per il rendimento (e `ChartLine` per «torna in Abs»), da confermare: DOMANDA V-8b nel checkpoint.
4. ✅ 21/10 · `chartSignalRendering.ts`: `renderCalendarComparisons` (i confronti in vista rendimento, come
   `calendarComparisonSignals` del dettaglio, per la scheda, l'anteprima e, quando lo adotta, X). **3 rossi** → **51/51**.
5. ✅ 21/10 · La modale: tre viste, la finestra, l'anteprima del rendimento.
   > **Note implementazione**: rossi in `ChartSettingsModal.test.ts` (nuovo `describe` «the three views, and the rolling-return
   > preview»): **4 rossi**, la guardia FX verde. Cura: il selettore è la vista salvata (`previewView`, Apply la salva);
   > il terzo pulsante solo per gli asset e solo con `calendarPreviewResolver`; in vista rendimento i controlli della
   > finestra del dettaglio (`AssetCalendarWindowControls`), la finestra in vigore con `effectiveCalendarReturnWindow` e
   > `calendarRangeDays`, una scelta la segna `calendarReturnWindowAuto: false`; il grafico come il dettaglio
   > (`valueUnit: 'percentage'`, `externalViewMode: 'absolute'`, `showMainDelta: false`), i confronti come sovrapposizioni;
   > nel globale la curva sintetica allungata della finestra, mostrato solo l'anno. **18/18**.
   >
   > **⚠️ Fuori pista**: lo stand-in del test non toglie il suo elemento quando Svelte smonta il grafico; con la vista
   > iniziale scritta da un `$effect` il grafico si montava due volte (prezzo, poi rendimento). La vista iniziale ora nasce
   > dalle impostazioni (`openingView`): niente primo disegno nella vista sbagliata, anche nell'app.
6. ✅ 21/10 · La pagina della lista (`assets/+page.svelte`).
   > **Note implementazione**: la vista globale dallo store (`globalPrimaryView`), la barra tripla
   > (`assets-global-view-calendar-return`, `aria-pressed`, `data-view` sul gruppo); `handleListPrimaryView`
   > (`setScopePrimaryView`) e `handleCardPrimaryView` (`setItemPrimaryView`) ricaricano solo le schede che entrano o escono
   > dal rendimento; in `fetchPriceSeries` una scheda in vista rendimento chiede il suo segnale (finestra in vigore per il
   > periodo della lista), nessun altro segnale del backend (V-5 a), e i bersagli con il segnale; le risposte dei bersagli non
   > toccano la cache dei campioni; `calendarByCard` tiene i rendimenti (mentre carica restano i vecchi punti); in errore
   > lo stato `error`. Il risolutore dell'anteprima (`resolveCalendarPreview`): per una scheda una richiesta come quella delle
   > schede (600 px di piano), per il globale `/signals/preview` sulla curva sintetica. Il salvataggio delle impostazioni
   > ricarica se il rendimento è coinvolto prima o dopo.
7. ✅ 22/10 · E2E riscritte in `asset-list.spec.ts` (verdi nello slot, passo 12): «the top bar’s three views…» (tre viste, il
   segnale chiesto, ogni scheda che si assesta), «one AssetCard turns its own view, keeps it across a reload…» (V-1 a, V-3 a);
   le due prove del Δ della scheda passano per il rendimento prima dell'assoluto. `onboarding-tour.spec.ts` resta valida
   (usa Abs e %).
   >
   > **⚠️ Fuori pista**: per provare il backend ho avviato `dev.py server --test` sulla 6189: con la build vecchia ha lanciato
   > da solo `build:debug` (un comando pesante, fuori dal lucchetto). Fermato subito (solo i miei processi; la build di
   > un'altra sessione non l'ho toccata). La prova a mano si fa nello slot, dopo `server --build-only` dentro `flock`.
8. ✅ 21/10 · Le prove leggere (carico 2-4).
   > **Note implementazione**:
   > - Vitest, a gruppi di 3 file (il lucchetto era tenuto da un `all-frontend` di un'altra sessione, coda di 7): **16 file,
   >   802/802** (store ×3, `reducedPriceQuery`, `AssetCard`, `AssetTable`, `ChartSettingsModal`, `chartSignalRendering`,
   >   `chartCoreHelpers`, `signalRendering.gate`, `LineChart`, `priceChartHelpers`, `AssetCalendarWindowControls`, `FxCard`,
   >   `OtherPeriodEffectsTable`, `themeRoles.gate`); `OtherPeriodEffectsTable` anche con `LC_ALL=it_IT.UTF-8`: 4/4.
   > - `dev.py front check` in `flock`: **0 errori, 0 avvisi** (un secondo giro sullo stato finale è in coda nel lucchetto).
   > - Prettier `--check` sui file toccati, `theme-roles --check`, `git diff --check`: puliti.
   > - `dev.py test check-orphans`: rc 1 per **5 orfani preesistenti di Z-29b** (`bulkBatchesGroups.test.ts`,
   >   `compactDensity.test.ts`, `reducedPriceCache.test.ts`, `chartUtils.test.ts`, `reducedPriceQuery.test.ts`), non miei;
   >   `AssetCard.test.ts` è registrato.
9. ✅ 22/10 · Doc (agente `docs-writer`, solo inglese): `user/assets/index.en.md` (la nota delle tre viste),
   `user/fx/chart-settings.en.md` (il selettore è la vista salvata; «🔁 Rolling Return view»),
   `developer/frontend/components/charts.md` («Three views», `#primary-views`: il contratto dello store, la richiesta della
   lista, `renderCalendarComparisons`, il contratto per il dettaglio). `mkdocs build` (strict) exit 0, `check-links` exit 0
   (97 link). Tolta da me la frase «the asset detail page uses the same window» (vera solo quando X adotta
   `effectiveCalendarReturnWindow`). Debito di traduzione: `user/assets/index` e `user/fx/chart-settings` (IT/FR/ES).
   V-8b decisa dal developer: (a) `CalendarSync` (come già nel codice).
10. ✅ 22/10 · Slot: build di debug (`server --build-only` in `flock`), prova a mano del backend (la richiesta delle schede con il
    segnale, i bersagli `sample_like` senza prezzi con `target_currency`), poi E2E `front-asset asset-list` e
    `front-fx fx-settings`.
   > **Note implementazione (22/10)**: build di debug in `flock` (`server --test --debug --build-only`, rc 0, log
   > `ondata3/y40-build.log`); server sulla 6189 avviato dopo, senza ricompilare. Prova a mano (`ondata3/y40-probe.log`),
   > `POST /assets/prices/query` come lo fanno le schede: 200; la scheda (Apple, USD, `max_points` 377, finestra 1A) ha i
   > punti con la provenienza (30, stato `partial`: la storia dei dati di prova è corta); un bersaglio `sample_like`,
   > `include_price: false`, nella stessa valuta, con finestra 3M: 305 punti come la scheda; un bersaglio in EUR con
   > `target_currency: USD`: `unavailable`, senza problema dichiarato (nei dati di prova manca il cambio, credo; il dettaglio
   > lo chiede allo stesso modo). Server fermato, porta libera.
11. ✅ 22/10 · Primo giro E2E nello slot (`--workers 2`, `nice`, in `flock`): `front-fx fx-settings` **3/3**;
    `front-asset asset-list` **41/43**, due rossi veri, nelle due prove nuove, tutti e due del prodotto:
    - «the top bar’s three views…»: dopo il clic sul rendimento `waitForSettled` è tornato con 16 schede ancora `loading`:
      `data-busy` della pagina non contava il caricamento del rendimento. Cura: `busy` include le schede con
      `calendarByCard` in `loading` (la regola «publish state»: lo stato c'era, il segnale della pagina no);
    - «one AssetCard turns its own view, keeps it across a reload…»: dopo il clic e un ricaricamento subito la scheda era
      tornata in %: lo store scrive `localStorage` 250 ms dopo l'ultima modifica e un ricaricamento in quella finestra
      perdeva la scelta. Rosso di unità in `chartSettingsStore.test.ts` («a pending write is done when the page goes away»,
      1 rosso), cura: al `pagehide` la scrittura in attesa si fa subito. Store **72/72**.
    Log: `ondata3/y40-e2e-asset-list.log`, `ondata3/y40-e2e-fx-settings.log`.
12. ✅ 22/10 · Secondo giro nello slot, dopo le due cure (in `flock`): build di debug rc 0 (`ondata3/y40-build2.log`);
    `front-asset asset-list` **43/43** (2,0 min, `ondata3/y40-e2e-asset-list-2.log`); `dev.py front check` **0 errori,
    0 avvisi** (`ondata3/y40-front-check.log`). Prettier, `theme-roles --check`, `git diff --check` puliti;
    `OtherPeriodEffectsTable` con `it_IT.UTF-8` 4/4. Porta 6189 libera.
13. ✅ 22/10 · CHECKPOINT READY (asset). La parte cambi (V-9, passo 2 del brief) aspetta il via del coordinatore dopo Z-29fx.

### Y-40, parte cambi (22/10, ondata 3, passo 2)

> **Base:** `71e615cf8` (merge di Z-29fx in Y, genitori `816a4b6c1` = Y-40 asset e `46455857a` = Z-29fx), `api sync` fatto.
> Regole di file: `assets/+page.svelte` e `reducedPriceQuery.ts` sono di Z (Z-29d): non toccati; la richiesta dei cambi
> in un file mio, `lib/utils/reducedFxQuery.ts`. Le pagine di dettaglio restano di X.

1. ✅ 22/10 · Lo store: per i cambi la vista predefinita resta **Abs**, come la barra della lista prima (la lista asset e il
   dettaglio restano in %). Rossi in `chartSettingsStore.test.ts` («the FX list opens on absolute rates»): **2 rossi**, il
   terzo caso verde. Cura: `scopeDefaultView('fx') = 'absolute'`, applicata al ripiego sulle impostazioni di base
   (`forScope`) e alla pulizia di un archivio di prima (le chiavi `__global_fx__` e quelle delle coppie). Il caso di Y-40
   asset che leggeva «fx in %» ora legge «fx in Abs». Store **58/58**.
2. ✅ 22/10 · `reducedFxQuery.ts` (nuovo) e `reducedFxQuery.test.ts` (nuovo, una riga nel runner dopo
   `reducedPriceQuery.test.ts`): una conversione di 1 per scheda, nel verso in cui la scheda mostra la coppia, con il
   rendimento, `key` `fx:<slug>` e `max_points`; ogni coppia confrontata (`fx-pair`) `sample_like` la scheda, nel verso del
   suo segnale; la propria coppia non si chiede. Rosso: il modulo assente. **7/7**.
3. ✅ 22/10 · `chartSignalRendering.ts`: `renderCalendarPairComparisons` (le coppie confrontate in vista rendimento, con il
   nome del loro segnale). **2 rossi** → **53/53**.
4. ✅ 22/10 · `FxCard.svelte` e `FxCard.primaryView.test.ts` (nuovo, una riga nel runner dopo `FxCard.test.ts`).
   > **Note implementazione**: **9 rossi, 2 verdi** (le due prove della conversione: lo stesso risultato di oggi, come
   > diceva X). Cura come `AssetCard`: `primaryView`, `onprimaryviewchange`, `calendarReturn`, `calendarOverlaySignals`,
   > `data-view-mode`, `data-calendar-state`, il pulsante `fx-card-view-toggle` con `data-next-view`, segnaposto e messaggio.
   > La richiesta di X: i punti si convertono una volta sola con `fxPointToLineDataPoint(d, inverted)`, per il grafico e per
   > i segnali. `FxCard.test.ts` e il nuovo: **15/15**.
5. ✅ 22/10 · La modale: il terzo pulsante dove la pagina calcola il rendimento (`calendarPreviewResolver`), non più solo per
   gli asset. Rosso: «offers the rolling return to the FX settings too…»; guardia: senza risolutore niente rendimento, e una
   vista salvata in rendimento si apre in %. **19/19**.
6. ✅ 22/10 · La pagina dei cambi (`fx/+page.svelte`): la vista globale dallo store, la barra tripla (`fx-global-view-*`,
   prima senza `data-testid`), `fetchCalendarReturns` (in `fetchAllPairData` con prezzi e Δ, al cambio di vista, di verso
   della scheda o della tabella, al salvataggio delle impostazioni; un numero di richiesta per scheda scarta le risposte
   vecchie; le conversioni non entrano negli store dei tassi), `data-busy` che conta il rendimento, il risolutore
   dell'anteprima (una coppia: la richiesta delle schede su 600 px; il globale: `/signals/preview` con `domain: 'fx'`).
   > **⚠️ Fuori pista**: le schede dei cambi disegnano ancora i tassi giornalieri degli store (non `max_points`): solo il
   > rendimento usa le conversioni ridotte di Z-29fx. Ridurre anche i tassi delle schede è un lotto a sé (come Z-29b per gli
   > asset), proposto nel checkpoint.
7. ✅ 22/10 · E2E in `fx-list.spec.ts` (verdi nello slot, passo 9): «the top bar’s three views update every FX card, opening on Abs…» e
   «one FX card turns its own view, keeps it across a reload…». La prova «loads all FX cards through exactly one bulk
   conversion request» resta valida (in Abs nessuna richiesta del rendimento).
8. ✅ 22/10 · Prove leggere e doc.
   > **Note implementazione**: Vitest a gruppi di 3 file: **14 file, 705/705** (store ×3, `reducedFxQuery`,
   > `FxCard.primaryView`, `FxCard`, `ChartSettingsModal`, `chartSignalRendering`, `chartCoreHelpers`,
   > `signalRendering.gate`, `AssetCard`, `reducedPriceQuery`, `themeRoles.gate`, `fxStoreRegistry`); `dev.py front check`
   > in `flock` **0 errori, 0 avvisi**; Prettier, `theme-roles --check`, `git diff --check` puliti; `check-orphans` rc 0.
   > Doc (`docs-writer`, solo inglese): `user/fx/index.en.md`, `user/fx/chart-settings.en.md`, il lato FX in
   > `developer/frontend/components/charts.md` (`#primary-views`); `mkdocs build` e `check-links` exit 0. Debito di
   > traduzione: `user/fx/index` e `user/fx/chart-settings`.
9. ✅ 22/10 · Slot (in `flock`): build di debug rc 0 (`ondata3/y40fx-build.log`); `front-fx fx-list` **27/27** (1,0 min);
   `front-fx fx-settings` **3/3** (la modale è cambiata). Log `ondata3/y40fx-e2e-{fx-list,fx-settings}.log`. Porta libera.
10. ✅ 22/10 · CHECKPOINT READY (cambi).
11. ✅ 22/10 · Due richieste di X (il dettaglio dell'asset legge ora la vista della lista, `b64c3f4c6` sul ramo di X):
    `charts.md` (`#primary-views`): il paragrafo del dettaglio dice ora quello che fa (si apre nella vista della scheda e
    la salva, con la stessa finestra della lista: rimessa la frase tolta il 21/10); nello store il commento di
    `setItemPrimaryView`: ricostruisce l'override dalla copia dello store e perde ciò che una pagina scrive nelle sue
    configurazioni (`_resolvedData`), quindi una pagina con le sue impostazioni salva con
    `setPairSettings(slug, {...settings, primaryView, signals})`, come fa il dettaglio. Nessun cambio di comportamento.

## 22/10 · Y-41 e #49 — analisi delle quattro superfici (ondata 4, sola lettura e prova a mano)

> **Base:** `6f816aad8` (il checkpoint 0, `data-testid="asset-card-settings"`, sopra `c042f2481`). `api sync` fatto. Prova a mano
> sulla corsia 6189: build di debug in `flock` (`ondata4/y-y41-build.log`), server avviato dopo, fermato, porta libera.
> **Metodo della prova:** nel browser ho scritto le impostazioni di due schede nel `localStorage`
> (`lf_2_chartSettingsStore`): la scheda EUR-USD con un confronto con Apple (asset 1) e con la coppia EUR-GBP, la scheda di
> Apple con la coppia EUR-USD e con Bitcoin (asset 6); colori puri (magenta per la coppia, ciano per l'asset), poi ho contato
> i pixel del canvas.

### La tabella

| Superficie | Funziona (provato) | Manca | Chi |
|---|---|---|---|
| **Lista asset** | un asset sopra un asset: sì (ciano 368 px sulla scheda di Apple al primo caricamento) | **una coppia sopra un asset non compare al primo caricamento** (magenta 0 dopo 12 s); compare dopo un ridisegno (il pulsante della scheda ×3: 36 px). Causa: `fxPairData` legge `getFxStore(...)`, che non è reattivo, e `loadFxRateData` finisce dopo che le schede hanno disegnato; nessun segnale le fa ridisegnare | **Y** |
| **Lista cambi** | una coppia sopra una coppia: sì (smeraldo 418 px su EUR-USD al primo caricamento) | **un asset sopra un cambio non si disegna** (arancio 0): `fxListSignalSources.comparisonTarget: () => null` (`fx/+page.svelte:865`), la lista non carica serie di asset; vale anche per l'anteprima della scheda | **Y** |
| **Dettaglio cambio** | un asset sopra il cambio: sì (ciano 2696 px, ricaricamento pulito) | **una coppia sopra il cambio non compare in un caricamento pulito** (magenta 0 dopo 15 s): le coppie dei segnali `fx-pair` si caricano nello store solo nel percorso «aggiorna» (`fx/[pair]/+page.svelte:1041-1048`), mai all'apertura, al cambio di periodo o alla scelta della coppia | **X** |
| **Dettaglio asset** | un asset sopra l'asset: sì (ciano 1270 px) | **una coppia sopra l'asset non compare in un caricamento pulito** (magenta 0, e la scheda del segnale è rossa con ⚠: «nessun dato»); **compare se arrivi dalla lista** (store già caldo: magenta 438 px). Stessa causa: `ensureFxRangeLoaded` solo nei gestori di sync/aggiorna (`assets/[id]/+page.svelte:1707`, `:2077`, `:2157`), non all'apertura né alla scelta | **X** |

**Osservazione a margine per X**, vista una volta, non analizzata: nel dettaglio di Apple (3M, % ) con il confronto con Bitcoin la linea ciana
sale in verticale al bordo destro fino a circa 400 % (mentre nella lista la stessa linea è una curva intera). Da guardare: la
base della percentuale o le date del confronto.

### Il contratto dello store (punto 2 del brief)
- **`chartSettingsStore` basta così com'è.** Salva solo le **configurazioni** (`signalType`, `params.assetId`, `params.pairSlug`,
  stile): i dati (`_resolvedData`…) sono del momento e si tolgono prima di scrivere (`sanitizeStoredSettings`). Nessun campo
  nuovo, nessuna migrazione.
- **La forma che i disegnatori leggono c'è già:** `SignalDataSources.comparisonTarget(assetId) → ComparisonTarget | null` e
  `fxPairData(pairSlug)` in `chartSignalRendering.ts`. Chi disegna costruisce le fonti dalla sua pagina: la lista asset da
  `targetSamples`, i dettagli da `_resolvedData` (`detailPageSignalSources`).
- **Quello che manca è dove la lista dei cambi trova la serie di un asset.** Proposta: un piccolo modulo mio, `lib/charts/comparisonSeries.ts`,
  con (1) `comparisonTargetFromStore(assetId, currency, names)`, che legge la cache esistente delle serie giornaliere
  (`assetPriceStoreRegistry`, `getAssetPriceStore`, con il suo rilevamento dei buchi, già usata dal dettaglio) e dà la forma
  `ComparisonTarget`; (2) `ensureComparisonSeries(items, range)`, **una sola richiesta** `POST /assets/prices/query` (giornaliera, senza
  eventi, in lotti con `sendBulkBatches`) per gli asset che mancano; (3) `fxPairSlugsOf(configs, ownSlug)` e
  `ensureSignalFxPairs(configs, ownSlug, range)` per le coppie dei segnali `fx-pair`, **che X chiama dai due dettagli** all'apertura,
  al cambio di periodo e alla scelta della coppia (poi `overlayDataVersion++`). Così X ha due righe da aggiungere per pagina, non un
  caricamento da scrivere.

### Il piano per Y (dopo il via)
1. **Rossi** (nessuna cura prima):
   - Vitest del modulo `comparisonSeries.ts`: `comparisonTargetFromStore` dà una serie giornaliera con nome, icona e tipo; `ensureComparisonSeries`
     manda **una** richiesta per gli asset che mancano e **nessuna** se la cache copre il periodo; le coppie dei segnali senza la propria.
   - Vitest `FxCard.primaryView.test.ts`: la scheda con un `asset-comparison` pubblica la linea (`data-overlay-count`, nuovo, sulla scheda,
     e lo stesso su `AssetCard` e sull'anteprima della modale): oggi 1 (la coppia), dopo 2.
   - E2E `front-fx fx-list`: con le impostazioni scritte nel browser (lo schema di `fx-list.spec.ts:574`) la scheda EUR-USD ha 2 linee e la
     lista fa **una** richiesta di prezzi, solo per gli asset confrontati; `front-asset asset-list`: la scheda di un asset con una
     coppia ha la linea al primo caricamento; `front-fx fx-settings`: l'anteprima di una scheda con un asset confrontato la disegna.
2. **La cura:**
   - `fx/+page.svelte`: le fonti reali (`comparisonTarget`) dalla cache; il caricamento solo per le schede con un confronto configurato
     (`comparisonTargetIds`), nel percorso che già carica tassi e rendimento; un contatore `$state` che i getter leggono, perché lo store
     non è reattivo; l'anteprima della scheda legge le stesse fonti (e chiede la serie mancante come l'anteprima della lista asset).
     `loadAssetList` porta anche la valuta (serve alla chiave della cache).
   - `assets/+page.svelte`: lo stesso contatore, alzato quando `loadFxRateData` finisce, letto da `getRenderedSignals` e `signalSourcesFor`.
   - `FxCard.svelte`, `AssetCard.svelte`, `ChartSettingsModal.svelte`: l'attributo `data-overlay-count`.
   - Doc: `charts.md` (il contratto sopra, per X) e la pagina utente delle impostazioni dei grafici (un confronto con un asset ora si vede anche
     sulle schede dei cambi).
3. **Costi** (decisione 11: va bene qualche richiesta in più): una sola `POST /assets/prices/query` per tutte le schede dei cambi, solo per gli asset
   confrontati (distinti), solo se la cache non copre il periodo; zero richieste per una lista senza confronti. Serie **giornaliere**, non
   ridotte: le schede dei cambi disegnano ancora i tassi giornalieri (Y-43, dopo la 1.3).
4. **File toccati (stima 11-13):** `fx/+page.svelte`, `assets/+page.svelte`, `FxCard.svelte`, `AssetCard.svelte`, `ChartSettingsModal.svelte`,
   `comparisonSeries.ts` (+ test), `FxCard.primaryView.test.ts`, i tre E2E, `charts.md`, la pagina utente, piano e backlog. Non tocco
   `chartSettingsStore.svelte.ts`, né i file di X.

### #49 — l'analisi
- **Il meccanismo c'è:** `ContributionTable.svelte` ha già `headerTooltip` per le altre colonne (`:268`, `:281`, `:294`, `:307`, `:417`, con la
  chiave nel catalogo e il testo di ripiego). Le due colonne `start-value` (`:388`) ed `end-value` (`:401`) ne sono senza. Aggiungo
  `headerTooltip: () => label('dashboard.startValueTooltip', …)` e `endValueTooltip`, con le chiavi accanto a `oldestOpenLotDateTooltip`
  (`i18n/dashboard/{en,it,fr,es}.json:106`) con `./dev.py i18n add`; le intestazioni delle colonne nelle quattro lingue sono già
  «Start/End Value», «Valore Iniziale/Finale», «Valeur Initiale/Finale», «Valor Inicial/Final».
- **Il test:** `DataTableHeaderTooltip.test.ts` mostra come si legge un tooltip d'intestazione; in `ContributionTable.test.ts` non c'è un
  caso sui tooltip: ne aggiungo uno che fissa il testo delle due colonne (in inglese, dal catalogo) e che la colonna resta nascosta di
  default.
- **La frase:** sta in `user/dashboard/positions.en.md:96` (verificato il 22/10: «**Start Value** and **End Value** are worked out as the **Value** in
  **Portfolio** …»; il grep del brief non la trovava, ma c'è). In `positions.{it,fr,es}.md` **manca** (la riga 86 elenca
  solo i nomi delle colonne): la scrivo nelle tre lingue con i nomi dell'interfaccia (**Valore Iniziale**, **Valeur Initiale**, **Valor Inicial**; nella
  pagina spagnola oggi c'è «Valor inicial» minuscolo: uso quello del catalogo). Non modifico `positions.en.md`: il timbro Aphra si guarda con
  `translate-validate` al momento, e si mette solo se serve.
- **Stima:** mezza giornata. Checkpoint a parte.

### Le domande per il developer
- **Q-Y41-1 · Vista assoluta di una scheda dei cambi con un asset in un'altra valuta.** Il confronto si disegna sullo stesso asse del tasso: un asset da 340 USD
  sopra un cambio da 1,08 appiattisce il tasso. Il dettaglio dei cambi fa già così (nessuna conversione); in % non c'è problema.
  (a) **Come il dettaglio, senza conversione** (consiglio: coerente, e la vista sensata è la %); (b) convertire nella valuta di quotazione della coppia
  (più richieste e un cambio in più da caricare).
- **Nota, non domanda:** nella finestra delle impostazioni **globali** (curva sintetica) un confronto con un asset non si disegna, come nella lista asset:
  non c'è un asset vero da mettere.

### Y-41 — i passi (22/10, dopo il via del coordinatore; Q-Y41-1: (a), senza conversione)
1. ✅ 22/10 · `lib/charts/comparisonSeries.ts` (nuovo) e il suo test `lib/charts/__tests__/comparisonSeries.test.ts` (nuovo, una riga nel
   runner dopo `chartSignalRendering.test.ts`).
   > **Note implementazione**: rosso: il modulo assente. Il contratto: `comparisonTargetFromStore(asset)` (la serie giornaliera della cache,
   > con nome, icona e tipo, nella valuta dell'asset; null senza punti), `ensureComparisonSeries(assets, range)` (**una** richiesta per gli
   > asset con un buco, giornaliera, senza eventi né conversione, in lotti; niente se la cache copre; una richiesta fallita non segna nulla,
   > un 404 è definitivo; non lancia mai), `fxPairSlugsOf(configs, ownSlug)`, `ensureSignalFxPairs(configs, ownSlug, range)` (le coppie dei
   > segnali `fx-pair` negli store dei tassi, una che fallisce non ferma le altre). **13/13**.
2. ✅ 22/10 · `data-overlay-count` e `data-testid="fx-card-settings"`.
   > **Note implementazione**: rossi (7 + 1) in `FxCard.primaryView.test.ts`, `AssetCard.test.ts`, `ChartSettingsModal.test.ts`; cura: l'attributo
   > sulle due schede (`overlaySignals.length`) e sull'anteprima della modale (`chart-settings-preview`, `previewOverlays.length`), il test id sul
   > pulsante delle impostazioni della scheda dei cambi (parallelo a `asset-card-settings` del checkpoint 0).
3. ✅ 22/10 · La lista dei cambi (`fx/+page.svelte`).
   > **Note implementazione**: `signalSourcesFor(readMissing)` al posto della costante: `comparisonTarget` legge `comparisonTargetFromStore` (la
   > cache delle serie giornaliere condivisa con il dettaglio asset) e legge `comparisonSeriesVersion`, un contatore `$state` alzato quando le
   > serie arrivano (gli store non sono reattivi); `fetchComparisonSeries()` (in `fetchAllPairData`, dopo `loadAssetList`, al salvataggio delle
   > impostazioni; una alla volta, così la seconda chiamata trova la cache piena) chiede gli asset confrontati **solo dalle schede che hanno un
   > confronto** (`comparisonTargetIds`); l'anteprima legge `settingsSignalSources` (con `readMissing`: un asset non ancora in cache si chiede,
   > fuori dal derived, con `queueMicrotask`); `data-busy` conta il caricamento; `loadAssetList` porta anche la valuta (la chiave della cache).
4. ✅ 22/10 · La lista asset (`assets/+page.svelte`): `fxRatesVersion` alzato quando `loadFxRateData` finisce e letto da `fxPairData`: una coppia
   confrontata si disegna al primo caricamento; `loadFxRateData` riparte anche al cambio di periodo (prima solo all'apertura).
5. ✅ 22/10 · E2E scritte (da lanciare nello slot): `front-fx fx-list` (nuovo describe «a card draws its saved comparisons (Y-41)»: una scheda con
   un asset e una coppia ha 2 linee e la lista chiede i prezzi **una** volta, per il solo asset confrontato; guardia: senza confronto con un
   asset nessuna richiesta di prezzi, la coppia 1 linea); `front-fx fx-settings` (l'anteprima di una scheda disegna il confronto con un asset);
   `front-asset asset-list` (la scheda con una coppia ha la linea al primo caricamento). Il fixture nuovo `e2e/fixtures/chartComparisons.ts` scrive
   le impostazioni nel browser (nessun dato condiviso).
   > **⚠️ Fuori pista**: i rossi delle E2E non sono stati lanciati prima della cura (una build e tre spec in coda nel lucchetto per un rosso
   > già misurato): lo stato rosso è la prova a mano del 22/10 (arancio 0, magenta 0 sul sorgente di `6f816aad8`, `ondata4/y-y41-build.log`) e i
   > 7+1 rossi di unità.
6. ✅ 22/10 · Prove leggere: Vitest a gruppi di 3 file, **12 file, 420/420** (`comparisonSeries`, `FxCard` ×2, `AssetCard`, `AssetTable`,
   `ChartSettingsModal`, `chartSignalRendering`, `chartPageSignals`, `reducedPriceQuery`, `signalRendering.gate`, `themeRoles.gate`,
   `chartSettingsStore`); `dev.py front check` in `flock` **0 errori, 0 avvisi** (`ondata4/y-y41-check.log`).
7. ✅ 22/10 · Doc (agente `docs-writer`, solo inglese): `charts.md` (nuova sezione «Series for comparisons», `#comparison-series`, il contratto per i
   dettagli; tolta la frase «i confronti con un asset non si disegnano sulle schede dei cambi»), `user/fx/chart-settings.en.md`, `user/fx/index.en.md`;
   `mkdocs build` e `check-links` exit 0. Debito di traduzione: `user/fx/chart-settings` e `user/fx/index` (it/fr/es).
8. ✅ 22/10 · Slot (in `flock`): build di debug rc 0 (`ondata4/y-y41-build2.log`); `front-fx fx-list` **29/29**, `front-fx fx-settings` **4/4**,
   `front-asset asset-list` **44/44** (log `ondata4/y-y41-e2e-*.log`); Prettier, `theme-roles --check`, `git diff --check` puliti. Porta 6189 libera.
9. ✅ 22/10 · CHECKPOINT READY (Y-41). #49: la frase in `positions.{it,fr,es}.md` è già scritta (fuori dal commit di Y-41); il tooltip e le chiavi
   sono il passo seguente, checkpoint a parte.

## 22/10 · #49 — il tooltip su «Valore Iniziale» e «Valore Finale», e la frase in it/fr/es (ondata 4)

> **Base:** `5333837b7` (Y-41 committato dal coordinatore). Discussione #49, promessa a un utente il 17/10.
1. ✅ 22/10 · Il rosso: `ContributionTable.test.ts`, nuovo `describe` «the tooltips of Start Value and End Value (#49)» (3 casi: le due colonne restano
   nascoste di default; il tooltip della colonna è quello del catalogo, `dashboard.startValueTooltip` / `endValueTooltip`, letto in lingua d'interfaccia, mai
   scritto nel test). Le colonne si mostrano con gli override salvati della tabella (uno `localStorage` in memoria: il jsdom di qui non lo ha).
   Rosso per il motivo giusto: la colonna c'è (precondizione verde) e `Unable to find role="tooltip"`; dopo la cura 5/5; tolta e rimessa la cura per rivederlo.
   > **⚠️ Fuori pista**: una colonna con un tooltip e senza link alla documentazione porta il tooltip **sul suo pulsante di ordinamento**
   > (`DataTableColumnHeader`), non su un'icona «i» (che c'è solo con il link): il primo rosso cercava l'icona sbagliata.
2. ✅ 22/10 · La cura: `ContributionTable.svelte` `headerTooltip` sulle due colonne (stesso meccanismo di `annualized-return`); le chiavi nelle quattro lingue
   con `./dev.py i18n add` (`i18n/dashboard/{en,it,fr,es}.json`): «Valore della posizione a inizio/fine periodo, calcolato come la colonna Valore del
   Portafoglio; 0 se la posizione non c'era ancora / era già chiusa. È la base delle percentuali del periodo (solo l'inizio)». `i18n check` rc 0 (5132 chiavi).
3. ✅ 22/10 · La frase in `positions.{it,fr,es}.md`: il punto «**Valore Iniziale** e **Valore Finale** si calcolano come il **Valore** nel **Portafoglio** …» (la riga ~96
   di `positions.en.md`), con i nomi dell'interfaccia; nella pagina spagnola anche la riga 86 («Valor inicial» → «Valor Inicial», come il catalogo).
   > **⚠️ Fuori pista**: `positions.en.md` non l'ho toccata, e **non ho messo il timbro Aphra**: l'hash della pagina EN è cambiato da altri commit
   > (`bd22b078 → 34c40c89`) e `translate-diff` segnala 2 anomalie per lingua (struttura: mancano, per esempio, la sezione YOC e il punto «Titoli spostati tra
   > due broker»). Timbrare nasconderebbe un debito vero, non il mio. Il debito della pagina resta per la traduzione di Aphra.
4. ✅ 22/10 · Prove: `ContributionTable` + `PerformanceChart` + `DataTableHeaderTooltip` **41/41**; Prettier, `theme-roles --check`, `git diff --check`
   puliti; in `flock` (dopo oltre un'ora di coda): `front check` **0 errori, 0 avvisi**, `mkdocs build` exit 0, `check-links` exit 0 (97 link validi); log
   `ondata4/y-y49-{check,mkdocs-build,mkdocs-links}.log`.

## 23/10 · Ondata 5 (Y5-1 · Y5-F1…F4 · Y5-2 · riga B5)

> **Base:** `1fd80c481` (= `dev_release2`, treni 9 e 10), `api sync` fatto. Brief: `ondata5/kickoff-Y.md`. Corsia 6189, `/tmp/librefolio-r13-y`.
> **I treni:** Y5-1, F1-F4 e la riga di B5 sono nell'11a (tranne B5: 11b); Y5-2 nell'11b.

### Y5-1 · Z-14b + Z-15 — la ricarica silenziosa dopo un recupero dei prezzi (PARTI SUBITO, treno 11a)

**Analisi.** Il piano 06 («Z-14b + Z-15 — piano per il mattino», ~3555) è rimasto valido nei fatti; le righe sono cambiate. Il sì del 22/10 vale per le tre
scelte di UX: D1 (il rischio ricarica **in silenzio**, senza `refreshing`), D2 (le analisi su richiesta **restano**), D3 (i punti vecchi **subito**, la richiesta
in background, senza `aria-busy`). Nessun dubbio vero nel piano. Un'unica cosa non prevista: `price-refresh-reload.spec.ts` **esiste già** (casi (a)…(h) di Z5,
Z-13, Z-18, Z-14): si **estende**, non si crea.
- **L'helper** (nuovo, mio): `features/price-refresh/onPricesCaughtUp.ts`: `onPricesCaughtUp(reload)` ascolta il bus per `{kind: 'prices'}` e chiama `reload` in un
  microtask, dopo che ogni cache si è segnata stale; una chiave per chiamata; non lancia mai; restituisce la funzione che smette. Mai `refreshVersion` né
  `requestPortfolioRefresh` (sono l'«Aggiorna»).
- **`TimeSeriesStore.isStale`** (un getter in sola lettura nel file dello store: la regola D3 delle quattro pagine ne ha bisogno; lo dichiaro nel checkpoint).
- **Le sei superfici**, ciascuna con un parametro `silent` che non accende nessuno stato di caricamento e con la regola D3 (store stale con punti per
  l'intervallo: i punti subito, la richiesta in background): `riskPanelController.svelte.ts` (`loadBase(force, silent)`, l'ascolto in un `$effect`),
  `LotsAnalysisPanel.svelte` (`loadMain` e `loadSelectionHistories` senza `pageBusy`, la cache stale li fa chiedere senza indicatori), il dettaglio asset
  (`loadChartData(force, signals, propagateError, silent)` + i confronti), il dettaglio cambio (`loadChartData(signals, propagateError, silent)` + i confronti e le
  coppie), la lista asset (`fetchAllPriceData(silent)`, `fetchPriceSeries(only, silent)`, `loadPeriodChanges(silent)`, i tassi delle coppie) e la lista cambi
  (`fetchAllPairData(propagateError, silent)` con le sue quattro letture).
- **I rossi:** Vitest dell'helper (7), di `isStale` (4), del controller del rischio (5, di cui 1 rosso e 4 guardie); gli E2E (i)…(m), (g'), (h') li scrive
  l'agente `test-author` nello spec esistente; i comuni, nello slot.
- **File che toccherò:** l'helper (+ test), `TimeSeriesStore.ts` (+ test), `riskPanelController.svelte.ts` (+ test), `LotsAnalysisPanel.svelte`, le quattro pagine,
  `price-refresh-reload.spec.ts`, la `desc` di `price-refresh` nel runner e la riga dell'helper nel runner (additive, proposte al coordinatore), la doc di sviluppo
  (`state/domain-state.md`, `live-ticker.md#price-refresh`, `state/registries.md`).
- **Domande:** nessuna.

1. ✅ 23/10 · L'helper, `isStale`, il controller del rischio e il pannello dei lotti: i rossi e la cura.
   > **Note implementazione**: `onPricesCaughtUp.test.ts` (nuovo, **7/7**, il rosso era il modulo assente); `TimeSeriesStore.test.ts` (**4 rossi** su `isStale` assente, poi
   > 38/38); `riskPanelController.test.ts` (nuovo `describe`: **1 rosso** + 4 guardie, poi **107/107**): `loadBase(force, silent)` non accende `refreshing`, l'ascolto non
   > ricarica se non c'è niente a schermo né dopo lo smontaggio né per un altro segnale; `LotsAnalysisPanel.svelte` solo `<script>`, nessun `pageBusy`.
2. ✅ 23/10 · Le quattro pagine (solo `<script>`).
   > **Note implementazione**: dettaglio asset e dettaglio cambio: `silent` in `loadChartData`, `staleShown` (i punti stale subito, senza `loading`), l'ascolto in un
   > secondo `onMount`; il dettaglio asset ricarica anche i confronti con `force`, quello dei cambi anche i confronti e le coppie dei segnali (la `loadSignalFxPairs` di X,
   > che usa il mio `ensureSignalFxPairs`); lista asset: `silent` in `fetchAllPriceData`/`fetchPriceSeries`/`loadPeriodChanges`, la scheda con la serie stale la mostra subito
   > (D3) e i tassi delle coppie si rileggono; lista cambi: `silent` in `fetchAllPairData` e nelle sue quattro letture, la coppia con tassi stale li mostra subito.
   > **⚠️ Fuori pista**: `loadChartData` del dettaglio asset ha ora un quarto parametro e il blocco della cache stale ripete il mapping dei punti in una funzione locale
   > (`chartPointsOf`), usata anche dal ramo «cache fresca»: stesso risultato, una copia in meno.
3. ✅ 23/10 · La documentazione per sviluppatori (docs-writer; solo inglese, nessun file `.it/.fr/.es`, nessun debito di traduzione).
   > **Note implementazione**: `live-ticker.md` (`#price-refresh-reload`, Mermaid e tabella delle viste), `registries.md` (`isStale`, regola D3, `#stale-reload`), `domain-state.md`
   > (`#prices-reload`), `core-infrastructure.md`, `app-state.md`, `risk/architecture.md`, `risk-lab.md`. `mkdocs build` strict **0 avvisi**, `check-links` **97 validi**.
   > **⚠️ Fuori pista**: `app-state.md` non era nella lista ma diceva il contrario («restano stale»): allineata.
4. ✅ 23/10 · Gli E2E, in corsia 6189 dentro il lock. `price-refresh` **14/15 al primo giro**, poi **15/15**; `asset-list` **44/44**, `fx-list` **29/29**, `asset-detail` **56/56**,
   `fx-detail` **33/33**, `risk-asset-detail` **5/5**.
   > **Note implementazione**: l'unico rosso era il caso (j), il pannello dei lotti del Dashboard: `sync-button` diceva «occupato» durante la ricarica silenziosa.
   > **⚠️ Fuori pista**: causa vera, trovata leggendo il codice e confermata dal verde: `effectiveSelectionIds` è un array nuovo a ogni risposta (anche con gli stessi lotti),
   > quindi l'effetto «lots-selection-load» ripartiva dentro `pageBusy.track` e accendeva il bottone. Cura in `LotsAnalysisPanel.svelte`: l'effetto riparte solo se la
   > selezione cambia **per valore** (`askedSelectionKey`, azzerata alla chiusura del pannello). Nessun test di unità del pannello esiste (monta mezza Dashboard): la prova è il caso (j) dell'E2E.

### Y5-F1 · F2 · F3 — ritocchi dal feedback della checklist (treno 11a, consegnati insieme)

- **F1:** nelle barre strumenti delle liste Asset e FX, in vista a schede, il primo pulsante della vista non dice più «Abs»: è l'icona `ChartLine` delle schede (stesso `data-testid`, `aria-label`/`title` «Mostra assoluto»). Nel dettaglio asset in modalità prezzi il selettore Abs/% resta com'è (non toccato). I tre pulsanti (Impostazioni, Sincronizza tutto, Ricarica tutto) sono avvolti nel `Tooltip` condiviso (ritardo di 500 ms già nel componente) con una riga di spiegazione ciascuno; il clic si ferma prima del clic del tooltip (come nella scheda «correlazione»), che altrimenti fisserebbe il suggerimento sopra la finestra aperta. Chiavi nuove `sharedResource.settingsHint|syncAllHint|refreshAllHint` in 4 lingue (`./dev.py i18n add`).
- **F2:** con la vista «Rolling Return» nell'anteprima, `ChartSettingsModal` passa `allowedSignalTypes` alla sezione dei segnali: solo `asset-comparison` nelle impostazioni degli asset, solo `fx-pair` in quelle dei cambi (è ciò che la vista disegna; nel dettaglio asset è `['asset-comparison']`). Gli altri segnali restano salvati (le operazioni della sezione toccano solo i visibili) e riappaiono tornando ad Abs o %.
- **F3:** `LineChart` (compatto) dice la risoluzione statica scelta con `onresolution`; `PriceChartCompact` mostra il `ResolutionBadge` del dettaglio (angolo in alto a sinistra) col più grosso tra il passo già applicato dal backend (`sampledResolution`, passato da `AssetCard` dalla riga della pagina, `daily` nella vista a rendimento) e quello del grafico stesso. `ResolutionBadge` pubblica `data-resolution`. Le schede dei cambi mostrano il badge quando è il grafico ad aggregare (i tassi dei cambi non vengono campionati dal backend).
- **Domande:** nessuna. **Ipotesi da far confermare:** i «tre pulsanti» sono Impostazioni, Sincronizza tutto e Ricarica tutto; il gruppo Abs/%/Rolling Return ha già il suo titolo.

### Y5-F5 · riga «Transfers at market value» (B5 di MF) — consegnata a parte

- `OtherPeriodEffectsTable.svelte` e `PerformanceChart.svelte` traducono la descrizione inglese `'Transfers at market value'` con la chiave nuova `dashboard.transfersAtMarketValue` (4 lingue). Vitest in `OtherPeriodEffectsTable.test.ts` (3 casi, 2 rossi con la riga tolta, poi 7/7; con `PerformanceChart.test.ts` 31/31). `PerformanceChart.test.ts` non ha un caso per le descrizioni (usate solo dentro le closure di ECharts): nessun test aggiunto lì.
- Doc: `user/dashboard/positions.en.md`, la riga fra «FX on cash» e il residuo, con il link a `period-pnl.md#transfers-at-market-value`.
  > **⚠️ Fuori pista**: l'àncora non esiste ancora nell'albero (è di MF): `mkdocs build` strict fallisce **solo** per quel link finché la sua intestazione non arriva col treno. `check-links` verde (97). Traduzioni it/fr/es: debito dichiarato (il link e la frase).

### Y5-F4 — il selettore dell'asset di confronto (in corso)

- `ChartSignalsSection.svelte` usa `AssetPickerPanel` (modo singolo, come il confronto del rischio) al posto del `SearchSelect` con i suffissi 👑 ✓ 📌: filtri tipo/valuta, i benchmark in testa, l'asset del grafico in sola lettura (verdetto `ineligible`), un asset già confrontato scegliibile ma con avviso. Chiavi nuove `signals.comparisonAsset.blocked|isMainAsset|alreadyCompared`; `is_benchmark` e `currency` passati da asset list, dettaglio asset e lista cambi (`fx/[pair]` è di X: non toccato, il pannello regge l'assenza).
  > **⚠️ Fuori pista**: due test Y-38 (campo chiuso e righe: il nome lungo scorre in un solo marquee col titolo) falliscono perché il pannello condiviso tronca il campo chiuso (`truncate`, fissato dai suoi test) e non mette `title` sulle righe. Cambiare `ui/select/AssetPickerPanel.svelte` non spetta a me: domanda al coordinatore.
- **F4 deciso (24/10, coordinatore):** (A) cambio additivo ad `ui/select/AssetPickerPanel.svelte` — il campo chiuso è un marquee con `title`, le righe (scelte e in sola lettura) hanno il `title`; il test del pannello non fissa più «un solo `truncate`» ma «un solo marquee»; i due casi Y-38 di `ChartSignalsSection.test.ts` restano, con le etichette senza suffissi. Prove: Vitest 201 file / 7288 test (components, risk, dashboard, gate dei colori); `front check` 0/0; `check-orphans` rc 0; E2E `asset-card-comparison-preview` 1/1, `asset-detail` 56/56, `asset-list` 49/49, `fx-detail` 33/33, `fx-list` 34/34, `risk-benchmark-shared` 4/4, `risk-asset-detail` 5/5. Docs: tre frasi in inglese (`fx/chart-settings`, `assets/detail/signals`, `fx/detail/signals`); debito di traduzione dichiarato.

### Y5-2 · #48 — il grafico delle singole posizioni e la torta per asset (treno 11b) — 24/10

**Analisi (dal contratto di J, `POST /api/v1/portfolio/positions-series`, e da MF, `allocation_by_asset` / `allocation_history.asset`).**
- **Dove**: scheda «Le tue posizioni» → vista Portafoglio (Holdings / tabella): `ExposureTable` ha i selettori di riga (come `UnifiedLotsTable`), sotto la tabella un grafico a linee. Senza selezione: la sola linea del portafoglio. Le righe scelte aggiungono le loro linee; la legenda le accende e le spegne.
- **«Dettaglio lotto» sostituisce la vista** nella pagina (`routes/(app)/dashboard/+page.svelte`, scheda `posizioni`): con `?asset=` il `PositionsPanel` non c'è e al suo posto c'è `LotsAnalysisPanel`, con un «← Portafoglio» ben visibile. Aprire il dettaglio fa un passo nella cronologia del browser (oggi `replaceState`), così anche «indietro» torna al portafoglio. ⚠️ Il file della pagina non è nell'elenco dei miei: lo tocco solo per questo, e lo dico al coordinatore.
- **Le due viste**: Abs = `pnl` (cumulato dall'inizio della finestra), % = «base 100» = `100 × (1 + pnl_percent)` (la % arriva fatta dal backend; l'unico passo del frontend è questo spostamento di presentazione).
- **La linea del portafoglio** viene dalla storia della Dashboard (`history`): % = `100 × (1 + twrr)`; Abs = `total_pnl` meno il suo primo punto (la finestra). **Non è il P&L sul capitale impiegato delle posizioni**: la legenda lo dice («Portafoglio (rendimento della Dashboard)»). Eccezione di presentazione dichiarata come quella di `lotComparisonChartHelpers.ts` (`@financial-math-exception`).
- **Colori**: i ruoli esistenti, `sequenceColor(CATEGORY_SEQUENCE, rango)`; il rango = il peso di oggi, dal più grande; poi gli asset chiusi, andando indietro nel tempo (chiusi più di recente per primi). Stesso rango per la torta, per la storia e per le linee.
- **La torta e la storia per asset**: una quarta scheda «Asset» nel pannello delle allocazioni (`AllocationPanel`): ora = torta di `allocation_by_asset`; storia = `allocation_history.asset` con le posizioni chiuse. Si riusano `AllocationPieChart` e `AllocationHistoryChart`.
- **Dati finti finché J e MF non entrano**: i tipi del contratto stanno in `features/dashboard/positionsSeries.ts` (specchio dello schema di J); dopo il merge dei loro rami si sostituiscono con quelli generati e si collega il client vero (`api sync`).

**Passi** (aggiornati dopo ciascuno): 1 helper puri + rossi · 2 grafico a linee `PositionsReturnChart` · 3 selettori di riga in `ExposureTable` + cablaggio in `PositionsPanel` · 4 la pagina: «Dettaglio lotto» sostituisce la vista, «← Portafoglio», cronologia · 5 la scheda «Asset» di `AllocationPanel` (torta + storia) con i colori per rango · 6 i18n (4 lingue) e doc `user/dashboard/positions.en.md` · 7 collegamento ai dati veri dopo il merge, E2E · 8 consegna.

**Avanzamento Y5-2 (24/10, sera).** Passi 1-8 ✅; consegnato al coordinatore (HEAD 49d018565).
1. ✅ `positionsSeries.ts` (tipi del contratto di J, linee Abs / base 100, linea del portafoglio, chiavi della selezione, rango dei colori per peso): `positionsSeries.test.ts` **51/51** (rosso = modulo assente).
2. ✅ `PositionsReturnChart.svelte` (linee su asse temporale, legenda con accendi/spegni, Abs / %, linea di riferimento 0 / 100, posizione chiusa che finisce al suo giorno): **34/34**.
3. ✅ `ExposureTable.svelte` con i selettori di riga (prop `selectable`, `selectedKeys`, `onSelectionChange` nell'ordine della tabella) **35/35**; `PositionsPanel.svelte` col grafico sotto la tabella Portafoglio, vista Abs/% ricordata, chiamata `onRequestPositionsSeries` una volta per cambio di selezione: **24/24**.
4. ✅ La pagina `dashboard/+page.svelte`: con `?asset=` al posto del `PositionsPanel` c'è il `LotsAnalysisPanel` con «← Portafoglio» (`positions-back-to-portfolio`); aprire il dettaglio è un passo nella cronologia, «indietro» o il pulsante tornano alla vista. Cinque E2E (dashboard-cache ×2, data-quality-legacy, data-quality-real ×2) aggiornati al nuovo disegno senza cambiare ciò che dimostrano; un E2E nuovo in `dashboard.spec.ts`. `front-portfolio all` **210/210**.
   > **⚠️ Fuori pista**: il file della pagina non era nell'elenco dei miei (lo dico al coordinatore). Un mio errore di tipo: `history.back()` coincideva con la variabile locale `history` della pagina → `window.history.back()`.
5. ✅ Scheda «Per Asset» in `AllocationPanel` (pie + storia, colori per rango): `AllocationPieChart` modo `asset` (4 casi), `AllocationHistoryChart` dimensione `asset` (3), pannello (8). Il contratto-sorgente di `allocationRings.test.ts` ha preso il rango dentro `sameTypeSet`.
6. ✅ i18n in 4 lingue (`dashboard.positionsChart.*`, `assetAllocation`, `backToPortfolio`); doc `positions.en.md` e `charts.en.md` (sezione «By Asset»). Mini-lotto a parte: il filtro valuta di `AssetPickerPanel` non ha più la voce vuota (3 casi, 2 rossi).
7. ✅ (24/10, dopo il merge di J `49d018565` e di MF `1b1b28c2a`) **Dati veri.** `positionsSeries.ts` ora deriva i tipi dal client generato (`z.infer<typeof schemas.PositionsSeriesResponse>` ecc.; i campi opzionali e le unioni con array passano da `safeString`/`safeDecimal`); l'eccezione `@financial-math-exception` dice che è lo spostamento di un numero del backend, non un calcolo nuovo. Nuovo `positionsSeriesController.ts` (una sola copia per Dashboard e pagina del broker): costruisce la richiesta con lo stesso ambito del report (broker, periodo, valuta), tiene solo la risposta più recente, non richiede due volte lo stesso ambito, richiede di nuovo quando cambiano ambito o `refreshVersion`, dopo un errore richiede al tick o al cambio di ambito successivo. `positionsSeriesController.test.ts` **11/11**. La pagina del broker (`brokers/[id]`, scheda Posizioni) passa ora `portfolioHistory` e il controllore (prima mostrava le caselle senza caricare nulla). `AllocationPanel`: tolti i `as any` su `allocation_by_asset` e `allocationHistory.asset`, ora tipizzati dal client. `front check` 0/0; Vitest `features/dashboard` + `components/charts` + `components/ui/select` **2379/2379**.
   > **Nota implementazione**: l'ambito del controllore è un oggetto `{brokerIds, start, end, currency, ready, version}`; la pagina del broker (non-runes) lo calcola con `$:` e chiama `sync`, la Dashboard con `$effect` + `untrack`.
8. ✅ (24/10) E2E sul dato vero (test-author): `dashboard.spec.ts` +2 test (linee delle posizioni su dati veri con cambio periodo/valuta e errore 500; «Per Asset» con pie, storia e persistenza dopo reload), `brokers-detail.spec.ts` +1 (scheda Posizioni: `broker_ids:[id]`, linea disegnata). `front-portfolio dashboard` 32/32 due volte; `front-broker detail` verde; `front-portfolio all` rosso solo per `chart-safety-unit` (vedi sotto), il resto verde.
   > **⚠️ Fuori pista (1)**: il primo giro del test sulla pagina del broker è uscito rosso: la pagina è in modalità legacy e non seguiva i campi `$state` letti da un getter del controllore → il controllore è diventato uno store Svelte (`subscribe`), le pagine leggono `$positionsSeriesCtl`.
   > **⚠️ Fuori pista (2)**: `financialMathExceptions.gate.test.ts` (nel gruppo `chart-safety-unit`) era rosso: `positionsSeries.ts` porta il tag `@financial-math-exception` ma non era nella lista. Aggiunta la voce `POSITIONS_SERIES` (e nell'intestazione del gate) e la regola 6 di `financial_math.md`: file fuori dal mio elenco, il coordinatore ha accettato l'eccezione. `chart-safety-unit` verde; utility core/component-unit verdi; `check-orphans`: 4 orfani di altri lotti, nessuno mio.

### Y5-3 · le serie a gradini (D-P4, cura B) — 25/10

**Analisi (piano `ondata5/Y-Y53-piano.md`, contratto `ondata5/CONTRATTO-P4b.md`, revisioni `ondata5/REVISIONI-P4b.md`).** La cura A (`max_points`) non vale più: il developer ha scelto la cura B. Ogni serie del report, dei lotti e del #48 è «un punto per tratto senza novità» (`date`, `through`), il MWRR della storia sta in `mwrr_line`. Un solo helper del frontend, `lib/utils/stepSeries.ts`, legge il formato; mai un array di tutti i giorni.
- Decisioni mie, accettate dal coordinatore: (4) il tooltip legge il giorno puntato, non il punto più vicino; (5) tratti veri se stanno nella densità (1,3 punti/px), altrimenti bucket settimana/mese con `bucketValue`, e il badge Weekly/Monthly solo dove c'è un bucket; (6) aree impilate: tutte le serie di una dimensione sugli stessi tratti; (7) una serie parziale finisce al suo ultimo `through`; (8) test con un tratto di 2 000 anni + gate sui cicli giorno per giorno; (9) helper di test che comprime le fixture giornaliere; (10) #48 passa ai tratti.
- Correzioni al contratto: la linea MWRR è in `GrowthChart` (vista %), non in `PerformanceChart`; serve `pointsBetween`.

**Passi:** 1 `stepSeries.ts` + test + prova del tooltip · (dopo il checkpoint di MF: `StepSpan`, `range`, `mwrr_line`) 2 `portfolioStore` e tipi · 3 `GrowthChart` (dati, scala a candele, tooltip, MWRR) · 4 allocazioni nel tempo e P&L per broker · 5 #48 · 6 lotti · 7 fixture/E2E · 8 documentazione.

**Avanzamento Y5-3.**
1. ✅ (25/10) `lib/utils/stepSeries.ts`: `valueAt`, `bucketValue(points, bucketStart, bucketEnd)`, `pointsBetween`, `coveredRange`, `toStepSeries` (un elemento per tratto più la chiusura; il valore ignoto o un buco spezzano la linea), `toLineSeries`, `nearestPoint` (a metà vince il punto prima), `expandDays` (conta i giorni prima di farli; null sopra il tetto, `EXPAND_DAYS_CAP` = 1 000), `dayOfAxisValue`. Rossi prima (modulo assente), poi **35/35** anche con `TZ` UTC, Europe/Rome, America/Los_Angeles, Pacific/Auckland. `__tests__/stepSeriesTestKit.ts` (`stepsFromDaily`, `dailyFromSteps`) per le fixture. Registrato in `front-utility core-unit`.
   > **Nota implementazione**: la ricerca è binaria sul testo delle date (`YYYY-MM-DD` con quattro cifre per l'anno, come le scrive il backend): `0024-03-01` viene prima di `2024-03-01`.
   > **Prova del tooltip (ECharts 6.0.0, pagina a parte, fuori dal repo):** su un asse del tempo il tooltip a `trigger: 'axis'` dà il punto dati **più vicino** al puntatore: a metà della destra di un tratto mostra il valore del tratto dopo (puntatore al 9 gennaio → 200, la linea dice 100). Con `xAxis.axisPointer.snap: false` l'evento `updateAxisPointer` porta il giorno puntato esatto, prima del formatter, mentre `params[0].axisValue` resta quello del punto più vicino. Regola per i grafici: `snap: false`, tenere `dayOfAxisValue(event.axesInfo[0].value)`, il formatter legge `valueAt` su quel giorno. Il valore dell'asse è in ora locale: `dayOfAxisValue` usa il calendario locale, non `toISOString()`.
