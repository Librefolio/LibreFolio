# F — L3° di Asset Global, «Quanto ha pagato ciascuno per il suo rischio?» · piano vivo

> Segue [F-L1-confronto-perdite.md](F-L1-confronto-perdite.md). Il componente è stato proposto da F, ha avuto l'OK di Risk
> ed è stato approvato dal developer il 2026-09-30.

## Coordinate

| | |
|---|---|
| Worktree | `e-alfy-super-dollop`, ramo `e-alfy-risk-asset-global-lab` |
| Base | `3eff35036`: guida `31cff1e5e` più journal, sopra la fusione F → Risk `3c46c8e60` (L1° più il calendario di Risk) |
| Corsie | 6154 per le suite (`/tmp/librefolio-r2-f`), 6164 per la copia di prod (`/tmp/librefolio-r2-f-prodcopy`) |
| Sessione | rinominata «F - Rischio/rendimento Asset Global» |

## Decisioni del developer (ask_user, 2026-09-30), alla lettera

> Proposta: la stessa cura di L1°. Risposta: **«Sì, partiamo da L3° come L1° (consigliato)»**.

> Etichetta di «Rendimento atteso»: **«metti rendimento medio annuo e un info con tooltip che contenga questa spiegazione
> sul come viene calcolato»**.

**Note di Risk** (OK del 16:06):
- il grafico `ScatterChart` è di A: non si tocca, e le osservazioni del developer su di esso vanno a Risk;
- l'ordinamento è del lettore, come in L1°;
- «Rendimento atteso» si propone al developer come scelta;
- C4 (tasso privo di rischio a 0) e C5 (soglia del Sortino a 0) sono del motore: vanno nella scheda, senza cure
  nell'interfaccia;
- l'helper condiviso della cella dell'asset è di F; un test jsdom nuovo richiede la sua riga nel runner, data dal
  coordinatore.

## Fatti verificati (base `3eff35036`)

- `AssetSetRiskReturnSection.svelte`:
  - `ScatterChart` (di A), con le etichette degli assi passate dalla sezione: `labels.return` =
    `risk.levels.l3.scatter.axisReturn`, «Rendimento annualizzato atteso», chiave di Risk usata anche dalla L3 della
    Dashboard;
  - la tabella è scritta a mano (`<table>`, `risk-asset-set-l3-row`), con il nome nudo `{row.name}`, titoli senza
    tooltip e nessun ordinamento; il commento alle celle dice «no ordering by value»;
  - le colonne beta e correlazione ci sono solo se `benchmarkApplies`.
- Riga `AssetSetPaidRow` (`assetSetLevels.ts:50`): `assetId`, `name`, `volatility`, `expectedReturn`, `sharpe`,
  `sortino`, `beta`, `correlation`, tutti annullabili.
- I testi (`risk.assetSet.levels.l3.*`) sono miei:
  - la descrizione è da sviluppatore: «Non ci passa nessuna retta: una selezione non ha un tutto…»;
  - `scatterNote` è tecnica: «media-varianza», «erode il composto»;
  - `expectedReturn` = «Rendimento atteso».
- Test che toccano L3°: `risk-lab.spec.ts`, `assetSetI18n.test.ts` (la nota del grafico non deve nominare una linea),
  `AssetSetComparisonLevels.test.ts`. Nessun test jsdom proprio.

## Contratto (per i test e per il codice)

- `AssetSetRiskReturnSection` riceve due prop nuove: `assetIcons: ReadonlyMap<number, string>` e
  `tableRef = $bindable()`. `AssetSetComparisonLevels` le collega, e la cornice di L3° riceve `actions` con
  `ColumnVisibilityToggle` quando la tabella c'è.
- Il contenitore `[data-testid="risk-asset-set-l3-table"]` porta `data-row-count` e contiene il `DataTable`:
  - senza selezione, azioni, filtri, paginazione né menu contestuale; con l'ordinamento;
  - `storageKey` `risk-asset-set-l3`; `tableLayout="auto"`.
- Colonne: `name`, `volatility`, `expectedReturn`, `sortino`, `sharpe`; con `benchmarkApplies`, anche `beta` e
  `correlation`.
  - All'apertura l'ordine di `assetIds`.
  - `name` ordina come «Per nome» (`nameComparator`), a parità per id.
  - Le colonne dei valori ordinano per il numero mostrato, col segno; i valori mancanti vanno in fondo.
  - `headerTooltip` = `risk.assetSet.levels.l3.columnHelp.<col>` su ogni colonna dei valori, niente su `name`; niente
    link, niente ⓘ.
- Cella dell'asset: lo **stesso helper di L1°**, con i testid di L3°.
  - `[data-testid="risk-asset-set-l3-name"][data-asset-id]` contiene `img[data-testid="risk-asset-set-l3-icon"]`, se c'è
    l'URL, e lo span `overflow-scroll-marquee` col nome escapato.
- Celle dei valori `[data-testid="risk-asset-set-l3-<col>"][data-measured]`:
  - volatilità in `x,x%`;
  - rendimento medio annuo col segno (`+` o U+2212);
  - i rapporti con `formatRatio`;
  - `—` quando manca.
- Il rendimento cambia nome: **«Rendimento medio annuo»** nella colonna e sull'asse del grafico, con una chiave mia,
  `risk.assetSet.levels.l3.axisReturn`. Il suo tooltip spiega il calcolo: la media dei rendimenti del periodo,
  annualizzata; un dato del passato, non una previsione; per un asset molto volatile, più alta di quanto ha reso davvero.
- Restano come oggi: gli stati, il blocco del grafico (`-risk-return`, `-scatter`, `-scatter-note`), `-no-benchmark` e
  `-blank-note`.
- Via: `risk-asset-set-l3-row`, sostituita da `tr[data-row-id]`.

## Passi

| # | passo | stato |
|---|---|---|
| L3-0 | piano, rinomina della sessione, riga del runner chiesta al coordinatore | ✅ 2026-09-30 |
| L3-1 | test rossi prima (test-author): jsdom `AssetSetRiskReturnSection.test.ts` (nuovo), `AssetSetComparisonLevels.test.ts`, E2E `risk-lab` | ✅ 2026-09-30 |
| L3-2 | codice: helper condiviso della cella (L1° lo usa senza cambiare comportamento), sezione → `DataTable`, livelli (icone, occhio) | ✅ 2026-09-30 |
| L3-3 | i18n via `dev.py i18n`: `columnHelp.*` ×6, `axisReturn`, etichetta, descrizione e nota del grafico nelle 4 lingue | ✅ 2026-09-30 |
| L3-4 | cancelli, mutanti sugli E2E nuovi | ✅ 2026-09-30 (E2E rossi veri sul codice vecchio, niente mutanti) |
| L3-5 | review del developer sulla 6164: giro 1 (tabella prima del grafico), giro 2 (selezione collegata, via la nota del benchmark), giro 3 (approvato; richieste del giro 4) | ✅ 2026-10-01 |
| L3-6 | checkpoint a Risk dei giri 1–3 (G1–G6; rifatto senza la voce di `TODO_FUTURI.md`, 13:0x) | ⏳ FROZEN fino al commit |
| L3-7 | giro 4: tooltip sui trattini (L1° e L3°), nota del periodo, guida; poi il selettore del benchmark (variante B) dalla primitiva `BenchmarkSelect` di Risk, quando arriva nel mio ramo | ⏳ dopo il commit e la fusione |

## Esecuzione

### L3-0 ✅ 2026-09-30, 16:20

> - Base verificata: HEAD `3eff35036`, albero pulito, `sw.js` al timbro committato, 6154 e 6164 libere.
> - Sessione rinominata.
> - Chiesta al coordinatore la riga del runner per `AssetSetRiskReturnSection.test.ts`: solo il percorso, accanto a
>   `AssetSetLossComparisonSection.test.ts` (`_frontend_utility.py:215`), nessuna `desc` cambiata.

### L3-1 · test rossi prima ✅ 2026-09-30, 16:25–16:50 (test-author `l3-datatable-tests`, corsia 6154 in esclusiva)

> - **Nuovo `AssetSetRiskReturnSection.test.ts`** (51 casi), modellato su quello di L1°:
>   - struttura, con e senza benchmark, 12 righe senza paginazione, `storageKey`, `tableRef`;
>   - intestazioni senza link, i 6 tooltip, nessun tooltip sul nome;
>   - le 7 chiavi nei 4 cataloghi;
>   - cella dell'asset, escaping, celle dei valori;
>   - ordinamento delle 6 colonne, compreso il rendimento col segno, e del nome;
>   - grafico: `ScatterChart` sostituito da un sostituto che registra le props, così si verifica
>     `labels.return` = `risk.assetSet.levels.l3.axisReturn`;
>   - i rami rimasti uguali.
> - **`AssetSetComparisonLevels.test.ts`** (27 casi): i casi dell'occhio sui due livelli, uno per tabella, e le icone a
>   entrambe le tabelle.
> - **E2E `risk-lab.spec.ts`**: opzione di stub `zigzagExpectedReturn`, definita nello spec, con rendimenti che passano per
>   lo zero. Casi nuovi di L3°:
>   - titoli con tooltip, senza link, layout `auto`;
>   - ordinamento del rendimento col segno;
>   - cella dell'asset;
>   - l'occhio prima del manuale, con Sortino spento e riacceso.
> - **Rossi sul codice di prima**:
>   - unitari: 35 su 51 nel file nuovo e 9 su 27 nei livelli;
>   - **E2E: 4 rossi, esattamente i casi nuovi**, con 26 verdi (build di debug prima della corsa). Rosso vero sul codice
>     vecchio, quindi niente mutanti.
>   - Contratto provato soddisfacibile su una versione usa e getta in `/tmp/l3proof`: 74 verdi, rossi solo i cataloghi;
>     16 mutanti presi.
> - Nota: lo schema vero si chiama `RiskAssetSetReturnOutput`.

### L3-2 · il codice ✅ 2026-09-30, 16:50–17:00

> - **Nuovo `assetSetTable.ts`** (mio): `assetNameCellHtml` e `assetNameColumn`.
>   - Icona e nome su una riga, tetto `max-w-56`, `escapeHtml`, colonna fissata a sinistra.
>   - L'ordine è `nameComparator` più l'id; le icone si leggono al disegno.
> - **L1° passa all'helper** (`assetNameColumn(…, 'risk-asset-set-l1')`), senza cambiare comportamento: i suoi 36 test
>   restano verdi. Via da L1° `nameHtml`, il comparatore locale e l'import di `overflowScrollTextClass`.
> - **`AssetSetRiskReturnSection.svelte`**: la `<table>` diventa `DataTable`.
>   - Colonne con `valueColumn()`, che ordina per il valore col segno; beta e correlazione solo con `benchmarkApplies`
>     (`columns` è `$derived`).
>   - `storageKey` `risk-asset-set-l3`, layout `auto`, `tableRef` bindable, scorrimento dei nomi sul contenitore.
>   - L'asse del grafico usa la mia chiave `risk.assetSet.levels.l3.axisReturn`.
>   - Nel docblock, il paragrafo sulla tabella del progetto ordinata solo dal lettore.
> - **`AssetSetComparisonLevels.svelte`**: `assetIcons` e `bind:tableRef={riskTable}` per L3°; la cornice di L3° riceve
>   `actions={riskTable ? riskActions : undefined}`.
> - **Runner**: la riga approvata dal coordinatore, `AssetSetRiskReturnSection.test.ts` dopo quello di L1° in
>   `component-unit`, solo il percorso.

### L3-3 · i18n ✅ 2026-09-30, 17:00 (script `/tmp/libreFolio_f4/l3_i18n.sh`, 10 operazioni)

> - Nuove: `risk.assetSet.levels.l3.columnHelp.{volatility,expectedReturn,sortino,sharpe,beta,correlation}` e
>   `…l3.axisReturn`.
> - Aggiornate:
>   - `…l3.expectedReturn` → «Rendimento medio annuo»;
>   - `…l3.description`, ora sul contenuto;
>   - `…l3.scatterNote`, più semplice. Parla di assi e non di direzioni, perché il test vieta `droite` in francese.
> - Il tooltip del rendimento spiega il calcolo, come ha chiesto il developer: la media del periodo, riportata a un anno;
>   un dato del passato, non una previsione; per un asset molto volatile più alta di quanto ha reso davvero.
> - Nessun testo nomina il tasso a 0 o la soglia del Sortino, che sono punti del motore di Risk.
> - Termini dei cataloghi: FR «référence», «tableau de bord»; ES «índice de referencia», «Panel», «Rentabilidad».

### L3-4 · cancelli ✅ 2026-09-30, 17:00–17:25

> - vitest sui 25 percorsi del giro (i 24 più il file nuovo): **25 file, 912 test**. Prettier pulito dopo `--write` su
>   due file.
> - `front check`: il pavimento (3 errori e 41 avvisi in 4 file non miei). `front build --debug`.
> - E2E: `risk-lab` **30 ⇒ 30**, `risk` **13 ⇒ 13**.
> - `risk-levels-component` 36. `core-unit` 103 file, 2845 test. `component-unit` **90 file, 2255 test**.
> - `check-orphans` pulito; `i18n audit` 3498 chiavi, tutte tradotte; `check-links` 83+5 = **88 validi**, 8 non
>   verificabili; `git diff --check` pulito; 6154 libera.
>
> ⚠️ **Fuori pista — `component-unit` è uscito 1 una volta, con tutti i test verdi** (skill `test-triage`):
> - **Il sintomo**: «Unhandled Errors: ReferenceError: document is not defined», attribuito da Vitest a
>   `src/lib/components/charts/ChartSignalsSection.test.ts`, che non è mio e non cambia dal 17/09. Nessuno stack.
> - **Le prove**: nelle 4 esecuzioni successive, una per volta, l'errore non torna:
>   - vitest diretto sulla stessa lista di 90 file;
>   - la stessa lista senza il mio file nuovo;
>   - `ChartSignalsSection.test.ts` da solo;
>   - il runner rilanciato: 90 file, 2255 test, exit 0.
> - **Il meccanismo probabile** (§2, un timer dopo lo smontaggio):
>   - `Tooltip.svelte` non cancella `pendingShowTimer` né `pendingHideTimer` quando viene distrutto; il periodo di
>     tolleranza di un tooltip fissato è di 30 s;
>   - `ChartSignalsSection.test.ts` (549 righe) non chiama mai `cleanup` e non ha `afterEach`, e con `globals` spento nella
>     configurazione di Vitest niente smonta i componenti al posto suo; fa 11 interazioni, e almeno un caso apre un
>     tooltip (`:262`);
>   - un timer rimasto vivo a fine file fa scattare la pulizia dell'effetto di `Tooltip` (`document.removeEventListener`,
>     `:350-357`) a jsdom già smontato.
>   - I miei due file di test smontano dopo ogni caso.
> - **Verdetto**: difetto probabile, fuori dalla mia corsia. Il timer sopravvive al componente (`Tooltip`, UI condivisa) e
>   il test non smonta (`ChartSignalsSection.test.ts`). **Non è «instabile».** Segnalato al coordinatore.

### L3-5 · review del developer sulla 6164 · 2026-09-30, dalle 17:30

> **Preparazione**:
> - copia di prod fresca (`app.db` sha `5c0a681bc4e4b59c`); build di debug aggiornata, nessun sorgente più recente;
> - server `dev.py server --test --port 6164 --data-dir /tmp/librefolio-r2-f-prodcopy`, shell `l3server`, PID 1509.
>
> **Primo giro (ask_user), alla lettera**: «guarda, mi pare tutto ottimo, ma sai cosa, invertirei tabella e grafico, così
> prima si mostrano i dati e poi la loro graficazione».
>
> **Note implementazione**:
> - In `AssetSetRiskReturnSection.svelte` il blocco del grafico (`risk-asset-set-l3-risk-return`, con la sua nota) passa
>   **dopo** la tabella e le sue due note (benchmark e trattini).
> - Aggiornati:
>   - il docblock: «The table comes first…»;
>   - il commento della nota, che parlava ancora di «expected».
> - La riga della nota resta identica, perché `assetSetI18n.test.ts` la legge dal sorgente.
> - Nessun test fissava l'ordine fra grafico e tabella.
> - prettier pulito; vitest su 3 file (sezione, livelli, `assetSetI18n`), 89 test; `front build --debug`; la 6164 serve
>   la build nuova.

> **Secondo giro (ask_user), alla lettera**: «sarebbe carino che se clicco in tabella o sul grafico, mi si seleziona la riga
> o il puntino, con un colore. poi la label "Scegli un benchmark nella Dashboard per aggiungere beta e correlazione. Un
> benchmark che è già nella selezione non può fare da metro a sé stesso." credo sia fuori luogo qui».
>
> **Analisi**:
> - **Tabella**: il `DataTable` ha la selezione singola senza la colonna delle caselle (`enableSelection` e
>   `selectionMode="single"`, `:170`, `:954`). Un clic sulla riga fa `toggleRowSelection` e chiama `onSelectionChange`, e
>   la riga selezionata e cliccabile diventa verde (`tr.clickable.selected`, `#dcfce7`).
>   - Un `selectedRowId` esterno si recepisce solo se non è `null` (`:535-542`), ma l'istanza esporta `clearSelection()`
>     e `toggleRowSelectionById()`.
>   - → **Fonte unica**: la selezione della tabella. Il grafico la legge da `onSelectionChange` e la comanda tramite
>     l'istanza; il `DataTable` non si tocca.
> - **Grafico**: `ScatterChart` (di A) non ha né un clic sui punti né un'evidenza. I punti hanno `id` `asset-<id>` e
>   `benchmark`, e lo monta anche la L3 della Dashboard.
>   - → Chiesto a Risk (18:0x): `selectedId?` e `onpointclick?`, additivi, con il verde `#22c55e` della matrice.
>     Decide Risk se lo fa A o se me lo concede.
> - **La nota del benchmark**: da togliere, con la sua chiave `risk.assetSet.levels.l3.noBenchmark` (mia).
> - La 6164 è spenta durante il lavoro e si riaccende per il giro successivo.

> **Risposte di Risk e del coordinatore (18:0x–18:3x)**:
> - Risk approva il contratto: id `asset-<id>` e `benchmark`, un'unica fonte nell'istanza della tabella.
> - **Permesso una tantum, con l'OK di A**, su `charts/ScatterChart.svelte` e `charts/scatterChartHelpers.ts`. Condizioni:
>   1. solo additive (`selectedId?`, `onpointclick?`); senza di esse il grafico resta identico, e i test lo fissano;
>   2. test rossi prima;
>   3. E2E `risk`, cioè la L3 di A con `data-point-count` 3, e `risk-lab` verdi prima del checkpoint;
>   4. `grid` (`:208`) non si tocca: è il V6 di A.
> - **Coordinatore**:
>   - approvata la riga del runner di `charts/ScatterChart.test.ts`, subito dopo quella di L3°;
>   - avvertimento: K ha già modificato `ScatterChart.svelte` in `dev_release2` (`53219bc00`), cioè l'import di
>     `escapeHtml` in testa e il formatter del tooltip. Tenersi lontani da quelle righe. Il gate XSS di K
>     (`htmlInterpolation.gate.test.ts`, in arrivo con la base) vuole il testo dell'utente solo attraverso
>     `escapeHtml(` e le variabili che contengono HTML chiamate `…Html`.
>
> **Test rossi prima, lato tabella e nota** (test-author `l3-select-tests`):
> - rossi sul codice di prima: 9 unitari (4 dei cataloghi, la nota, 4 della selezione) e 2 E2E (la nota, la selezione);
> - i 3 casi del grafico sono scritti ma `it.skip`, in attesa delle prop di `ScatterChart`;
> - nel test di L1° c'è un caso in più: la riga di L1° non si seleziona.
>
> **Note implementazione (lato tabella e nota)**:
> - `AssetSetRiskReturnSection.svelte`:
>   - via la nota `risk-asset-set-l3-no-benchmark`;
>   - `enableSelection` e `selectionMode="single"`, con `onSelectionChange` che tiene `selectedAssetId`;
>   - `clearSelection()` e `toggleRowSelectionById()` notificano anch'essi `onSelectionChange` (`clearAllSelection` con
>     `[]`), quindi la tabella resta l'unica fonte.
> - `dev.py i18n remove risk.assetSet.levels.l3.noBenchmark -f`: tolta dalle 4 lingue; non la usava nessun sorgente.
> - vitest: 103 verdi e 3 saltati.
> - Runner: la riga di `ScatterChart.test.ts`.
> - Per il gate di K: nell'helper `icon` diventa `iconHtml`, e in L1° `lasted` diventa `lastedHtml`.

> **Test rossi prima, lato grafico** (test-author `scatter-select-tests`, solo vitest):
> - `scatterChartHelpers.test.ts`: 9 casi nuovi (evidenza ×4 ruoli, tema scuro, invarianza ×4 con barriera di presenza);
> - `ScatterChart.test.ts` (nuovo, jsdom, echarts finto): 11 casi (Dashboard senza prop identica al byte, attributo ×3,
>   passaggio al builder, riapplicazione quando la selezione si sposta, clic → id ×5).
> - Verificato da me: `vitest run` sui due file → **20 rossi, 23 verdi**, per le ragioni giuste (colore del ruolo invece
>   del verde, `data-selected-id` assente, nessun `setOption` dopo il cambio, nessun listener di clic).
>
> **Note implementazione (lato grafico)**, lontano dalle righe di K (`53219bc00` tocca solo l'import in testa e le due
> righe del tooltip, verificato con `git show` in sola lettura) e senza toccare `grid`:
> - `scatterChartHelpers.ts`: `selectedId?: string | null` nell'input; il punto scelto resta nella sua serie e al suo
>   posto, con `symbolSize` ×1.5 (anche oltre `MAX_SYMBOL_PX`), verde `#22c55e` (`#4ade80` nel tema scuro) e opacità 1.
>   Un id che non nomina un punto piazzato non cambia nulla.
> - `ScatterChart.svelte`: le due prop; `selectedId` entra nel `$derived` di `built`; il listener di clic si registra una
>   volta per istanza, dentro `if (!chart)`, e chiama `onpointclick` solo con un `data.id` stringa; il contenitore
>   pubblica `data-selected-id={selectedId ?? ''}`.
> - Docblock di entrambi: «nessun componente grafico ha uno spec» non è più vero, riscritto; l'elenco degli attributi
>   pubblicati ora ne ha tre.
> - Sezione: `selectedId` = `asset-<id>` o `null`; `onpointclick` → `selectFromPoint`, che ignora il benchmark e gli id
>   senza riga, e passa per `tableRef.toggleRowSelectionById`: un secondo clic sul punto scelto lo toglie, come sulla
>   riga.
> - vitest sui due file del grafico: **43/43**.

> **Metà grafico attivata nei test** (test-author `l3-chart-link-tests`, solo vitest):
> - `AssetSetRiskReturnSection.test.ts`: tolti i 3 `it.skip`, aggiornata la prosa rimasta al «si aspetta»; due casi
>   nuovi: il secondo clic sullo stesso punto toglie la selezione (con il controllo in mezzo), e un `asset-<id>` senza
>   riga non cambia nulla (con la barriera: la tabella non ha quella riga; senza la guardia della sezione il `DataTable`
>   selezionerebbe un id inesistente). → **72/72, 0 saltati** (prima 67 + 3 saltati).
> - `risk-lab.spec.ts`: il caso della selezione di L3° legge anche `data-selected-id` sul grafico (`""` all'apertura,
>   `asset-<first>`, `""`, `asset-<second>`), con la premessa che il grafico sia disegnato e abbia un punto per riga. Il
>   verso punto → riga non si guida in E2E (servirebbero coordinate nel canvas): lo fissano i test di componente.
> - Suo giro extra: tutto il catalogo `component-unit` via vitest diretto, 91 file, 2287 verdi.

> **Cancelli del secondo giro** (2026-09-30, uno per volta, corsia 6154 `/tmp/librefolio-r2-f`):
> - prettier `--check` sui 16 file del frontend: pulito.
> - vitest sui 27 percorsi (`FL3b_vitest_paths.txt`: i 25 del giro più i due del grafico): **27 file, 976 test**, 0 saltati.
> - `front check`: 3 errori e 41 avvisi in 4 file, **il pavimento**, nessuno mio.
> - `tsc -p tsconfig.e2e.json --noEmit` (il gate che `front check` non fa sugli spec): 4 errori, tutti in altri file
>   (`asset-detail.spec.ts` ×2, `onboarding-tour.spec.ts`, `src/lib/types/files.ts`); **0** in `risk-lab`/`risk-*`.
> - `front build --debug`; E2E `front-portfolio risk-lab`: **31/31** (31 test nello spec, compreso quello esteso).
> - **Mutante** sul caso E2E esteso, che non era rosso prima: `selectedId={null}` nella sezione → build → solo quel caso
>   (`risk-lab "and the scatter follows"`) **rosso a `:4287`** (atteso `asset-1`, ricevuto `""`); ripristino con sha256
>   verificato (`7de1960a…`), build, di nuovo **verde**.
> - E2E `front-portfolio risk`: **13/13** (la L3 della Dashboard disegna il suo grafico: le prop nuove non la toccano).
> - `risk-levels-component` 3 file, 36 test; `core-unit` **103 file, 2854 test**; `component-unit` **91 file, 2287
>   test**, nessun errore non gestito.
> - `check-orphans`: tutto raggiungibile (e2e 88, `src/**/*.test.ts` 279); `i18n audit`: **3497 chiavi** (una in meno:
>   `noBenchmark`), tutte tradotte, nessuna chiave di L1°/L3° fra le inutilizzate; `check-links`: **88 validi**, 8 non
>   verificabili, 3 ancore note (invariato).
> - `git diff --check` pulito; 6154 e 6164 libere; `sw.js` non toccato.
>
> **Reperto per A (via Risk), non corretto**: in `scatterChartHelpers.ts` `SYMBOL_BY_ROLE` (`:96`) è dichiarato e mai
> letto, e nessuna serie porta `symbol:` → il benchmark si disegna **cerchio**, non il rombo che i commenti descrivono
> (anche il mio, in `AssetSetRiskReturnSection.svelte`, «labelled the diamond»). Cambierebbe anche la Dashboard: decide A.

> **Terzo giro di review** (2026-10-01): copia di prod fresca (`5c0a681bc4e4b59c`), build di debug più recente di ogni
> sorgente, server sulla 6164.
> - **⚠️ Fuori pista**: il developer ha riavviato il programma per aggiornarlo, e il riavvio ha fermato il server (era
>   legato alla sessione). Nel frattempo la copia era stata scritta (`3ae5f49f…`) → sostituita con una copia fresca,
>   server riavviato (shell `l3server4`, PID 57942), `/assets` 200. Nessun file del worktree toccato, HEAD invariata.
>
> **Terzo giro (ask_user, poi rimandato in chat dopo la caduta della linea), alla lettera**:
> «la label "Un trattino significa che la misura non è stata possibile per quell'asset su questa finestra — non significa
> zero." la togliere fissa e la metterei come tooltip sui trattini quando compaiono
>
> Riguardo il benchmark, ok che in dashvoard esiste, ma noi stiamo in asset, se serve un benchamrk, lo devo poter
> scegliere qui, mi sta anche bene che a livello di memoria del client siano lo stesso, così se lo cambio qui o lì è
> indipendente, ma non è accettabile che debba andare in dashboard, modificare il selettore e poi tornare qui.
>
> Poi stavo pensando che siccome la topbar è lontana, mettere una nota tra tabella e grafico, in cui si ricorda quale
> sia il periodo selezionato, e quanto è lungo e che i calcoli sono annualizzati, potrebbe aiutare.
>
> Poi mi è venuta un idea pazzerella... […] avrebbe senso creare un tracciato […] se il periodo scelto è 1Y, allora
> calcoliamo e mostriamo, sul grafico, il 1/4, poi il 2° e così via ogniuno di 3 mesi, per far vedere l'evoluzione, è
> un idea stupida? questa cosa non la fale, ma riflettici e dammi la tua opinione»
>
> Sulla selezione collegata nessuna osservazione. Server 6164 fermato a fine giro (`lsof`: libera).
>
> **Analisi (verificata sul codice)**:
> 1. **Trattini**: la nota `risk.assetSet.levels.blankNote` sta sotto **tutte e due** le tabelle (L1°
>    `AssetSetLossComparisonSection.svelte:260`, L3° `AssetSetRiskReturnSection.svelte:270`). `HtmlCell.tooltip: {text}`
>    (`table/types.ts:147`) avvolge già la cella nel `<Tooltip>` del progetto (`DataTable.svelte:1372`): nessun
>    meccanismo nuovo. Proposta: tooltip solo sulle celle nulle, stesso testo (già nelle 4 lingue), via la nota fissa,
>    in L3° **e in L1°** (da confermare).
> 2. **Benchmark**: lo store `riskBenchmark` (`stores/risk/riskBenchmarkStore.svelte.ts`, di Risk) ha già `set()` «per
>    ogni scope»; il pannello lo specchia (`AssetSetRiskPanel.svelte:562-578`) e lo passa ai livelli come `benchmarkId`,
>    ritirato quando fa parte della selezione. `L3Benchmark` (Dashboard) è legato al `RiskPanelController` della
>    Dashboard (`registerLauncher`, `runGuarded`): non riusabile → nel laboratorio `AssetSelect` (ui condiviso) più
>    `riskBenchmark.set`, nei miei file. 03 §3.1 («il benchmark deve essere **lo stesso** nelle due pagine») resta
>    vero: un solo store.
>    - Per Risk: il laboratorio escluderebbe gli asset **selezionati**, non quelli **posseduti** → un asset posseduto
>      può diventare il benchmark della Dashboard, il cui elenco li esclude (`excludeAssetIds={assetIds}`) ma che usa
>      comunque il valore salvato; `comparison.py` non lo rifiuta (lo rifiuta solo `RiskAssetSetComparisonOutput`,
>      `schemas/risk.py:1578`, per i membri della selezione).
>    - Il benchmark entra anche nella finestra di L1° (guida `:168`): sceglierlo in L3° cambia anche i numeri di L1°.
> 3. **Periodo**: ogni risultato porta `metadata.analyzed_range` (dal primo all'ultimo giorno di **rendimento**,
>    `service.py:1155`), `calendar_days` (dal prezzo di partenza all'ultimo rendimento, `service.py:1120`) e
>    `annualization_factor`; il pannello passa `dateStart`/`dateEnd` ai livelli; `dayFormatter`
>    (`eligibility.ts:123`) è il formato del banner del periodo. Annualizzati: volatilità e rendimento medio; Sharpe e
>    Sortino ne derivano; beta e correlazione no.
> 4. **Traccia per trimestri**: da non fare; parere al developer (asse x informativo, asse y dominato dal caso: σ/√T).
>
> **Derive della guida `user/assets/correlation.en.md`** (da correggere in questo giro):
> - `:124` «This tab has no picker of its own» → falso col selettore;
> - `:128` «a note under the table recalls how to add them» → **già falso** dal secondo giro (nota tolta): deriva mia;
> - `:122` «a larger diamond» → si disegna un cerchio (`SYMBOL_BY_ROLE` mai letto): reperto per A, decide lui.
> - CHANGELOG `:76` «beside the benchmark chosen on the Dashboard»: proposta nel checkpoint (file condiviso).
>
> **Bozze e parere (ask_user), risposta del developer alla lettera**: «si chat ok per le bozze e grazie per la
> spiegazione sulla traccia, magari possiamo aggiunere in todo_futuri una nota sullo snail trail in cui si specifica che
> è un idea e che va approfondita. Poi un altra domanda teorica, per coerenza va bene che i calcoli siano sul periodo
> attualmente impostato, ma ha senso fare una simile analisi per appena 3 mesi? quanto dovrebbe essere lungo il priodo
> di analisi per essere significativo? Potremmo mettere un suggerimento che dica di aumentare l'orizonte temporale di
> almeno x tempo e che modifica la data in topbar a quel periodo minimo (o magari dare una lista di slice) cosa ne
> pensi? anche di questo voglio solo un analisi per ora»
> - ✅ La nota sullo snail trail è passata in `TODO_FUTURI.md` su `dev_release2`, attraverso il coordinatore: il file è
>   suo, e lui ha copiato la mia voce così com'era. Il developer la committa lì.
>   - **⚠️ Fuori pista**: l'avevo scritta io in questo ramo (41 righe prima della voce «Idea interessante presa da un
>     utente»), come gruppo a sé del checkpoint, senza chiedere a chi possiede il file. Su richiesta di Risk (13:00)
>     l'ho tolta **modificando il file**, senza `git restore`/`checkout`: uno script che scrive solo se il risultato è
>     identico a `HEAD:TODO_FUTURI.md` (`/tmp/libreFolio_f4/l3_todo_remove.py`). Poi `git diff -- TODO_FUTURI.md`:
>     vuoto.
> - La domanda sul periodo minimo: **solo analisi**, data al developer (ask_user, 12:5x). In sintesi:
>   - per puro caso, su un ETF al 20% con Sharpe 0,5, il rendimento medio annuo si sposta di ±40 punti su 3 mesi, ±20
>     su 1 anno, ±12 su 3 anni; lo Sharpe di ±2,1, ±1,1, ±0,6; la volatilità solo del 9–14%, 5–7%, 3–4% del suo valore;
>   - proposta: soglia a 1 anno con un avviso, non un blocco; un solo bottone «Estendi a 3 anni» col meccanismo del
>     banner del periodo; niente lista di periodi; soglie per singola misura → motore, cioè Risk.
>   - Nessun lavoro approvato.
>
> **Risk (due messaggi, 01/10)**:
> - **Il developer ha deciso** (riportato da Risk, testuale): «credo che matematicamente può avere senso usare come
>   benckmark un asset posseduto […] Vorrei che ovunque serve scegliere un benchmark ci sia un selettore che permette
>   di farlo e che al momento del caricamento della pagina, esso mostri il benchmark attuale, vuoto non deve mai essere,
>   eccetto quando non c'è nessun asset impostato». La pagina dell'asset userà il benchmark condiviso (lo fa Risk).
> - Per il giro 4 di L3°:
>   - selettore nel laboratorio **approvato**; si escludono **solo gli asset selezionati**, i posseduti si possono
>     scegliere;
>   - la **scelta corrente resta sempre visibile**, anche quando è fra i selezionati: `AssetSelect` filtra le opzioni e
>     `SearchSelect` cerca il valore fra quelle filtrate → filtro `!selezionati.has(a.id) || a.id === corrente`, test
>     rosso prima;
>   - un id che non corrisponde più a nessun asset vale «non impostato»: segnaposto, nessuna colonna, fissato da un test;
>   - la guida `:124` cambia insieme al selettore;
>   - **dove metterlo lo decide il developer**, fra due varianti in ASCII: dentro L3° (come in Dashboard) o in cima
>     ad `AssetSetComparisonLevels`, sopra L1° e L3°, perché cambia la finestra di tutti e due. Risk preferisce la
>     seconda.
> - Il difetto gemello della Dashboard (un benchmark posseduto nascosto dalla lista ma usato) è di A: lo porta Risk.
> - `SYMBOL_BY_ROLE`: confermato; lo passa Risk ad A, che lo fa quando il mio lavoro arriva nel suo ramo. Se A non lo
>   applica, la guida `:122` la correggo io.
> - **Tempi, decisione di Risk**: checkpoint del giro 3 **adesso**, poi il giro 4. `ScatterChart` e il suo helper
>   tornano così ad A; la fusione con la nuova punta arriva dopo il commit di Risk, quando il coordinatore la dà.
>
> **Variante del selettore, decisione del developer** (ask_user, 12:5x): «B · sopra L1° e L3°». Il selettore va in cima
> ad `AssetSetComparisonLevels`, sopra le due sezioni di cui cambia la finestra.
>
> **Risk, 12:2x e 12:3x** (andati persi con l'errore della mia sessione, rimandati alle 13:00):
> 1. **Checkpoint senza la voce di `TODO_FUTURI.md`** (vedi sopra): 6 gruppi, 19 file, il diario come ultimo gruppo,
>    blob e digest nuovi. Il resto l'ha verificato: prop di `ScatterChart` additive, `grid` non toccata, Dashboard
>    identica con `selectedId=null`, runner +2, i18n solo `risk.assetSet.*`.
> 2. **Il selettore viene dalla primitiva di Risk**, non ne scrivo uno mio: `components/risk/BenchmarkSelect.svelte`,
>    con `resolveRiskBenchmark()` nello store, perché la regola del developer vale su tre superfici e deve stare in un
>    posto solo.
>    - Interfaccia: `measuredAssetIds` (per me gli asset selezionati: la scelta corrente resta visibile, con il ⚠);
>      `bind:value` (la scelta corrente risolta, un id morto vale `null`); `onchange(id)` dopo la scrittura dello
>      store; `testid`, `placeholder`; sezioni «benchmark / altri asset».
>    - Il disegno del ⚠ lo do io a Risk, che lo mette nella primitiva così com'è.
>    - Nel giro 4 faccio prima le altre voci. Il selettore lo monto quando la primitiva arriva nel mio ramo con la
>      punta di Risk.
>
> **Derive note che restano nel checkpoint**, corrette nel giro 4 con un solo passaggio sulla guida:
> - `correlation.en.md:128`: la nota sotto la tabella non c'è più dal secondo giro (nel messaggio a Risk avevo scritto
>   `:127`: era `:128`);
> - `correlation.en.md:114`, `:116`, `:118`: **Expected return** è ora «Average annual return»;
> - `:110-114` elencano prima il grafico e poi la tabella, che ora viene prima; «no ranking» resta vero (il sistema non
>   ordina), ma l'ordinamento del lettore non è detto;
> - la guida non dice ancora né l'ordinamento né la selezione collegata.

## Checkpoint di L3° · giri 1–3 · 2026-10-01 (verso Risk)

> Il delta, i gruppi (G1–G6) e i digest stanno nel messaggio a Risk e in `/tmp/libreFolio_commits/f-l3-*`. Prima
> versione (12:4x) con 7 gruppi; rifatta alle 13:0x senza la voce di `TODO_FUTURI.md`.
> Stato: **FROZEN** fino al commit: niente modifiche, test, server o comandi Git.
