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
