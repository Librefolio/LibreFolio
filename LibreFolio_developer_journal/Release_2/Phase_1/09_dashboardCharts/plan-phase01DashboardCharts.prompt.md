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
   /tmp/librefolio-r13-y -- -f "Dashboard|Brokers" --workers 6`; confronto con il riferimento `g-final3-r1` di oggi,
   `--common-only --ignore-masks $W/diffs/g-final3__r1__vs__r2/masks --stability
   $W/diffs/g-final3__r1__vs__r2/stability.json`. Rumore noto: `static-grid`, `import-modal` e gli scatti instabili.

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

### Y2 — `DataTable` tagliata sul posto [autorizzato; forma approvata e taglio annunciato il 15/10; fatto, checkpoint FROZEN alle 16:45, galleria d'ingresso dopo il commit]

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

### Y7 — tabelle sul telefono e ridimensionamento [via del coordinatore e dei colori, 15/10 20:52–21:22; in corso]

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

### Y3–Y13 — da avviare nell'ordine del §0.2

Y3 FE6b; Y4 FE2a e FE2b; Y5 FE7 (dopo FE8a); Y6 FE3 (dopo FE8a); Y7 C-38 e C-62; Y9 K-15, C-34, C-15, K-13; Y10 54-1;
Y11 C-85; Y12 U8 a/b; Y13 FE9–FE11. I dettagli sono nell'analisi del 15/10 (cartella di sessione) e nel §2; si
scrivono qui quando partono.

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
