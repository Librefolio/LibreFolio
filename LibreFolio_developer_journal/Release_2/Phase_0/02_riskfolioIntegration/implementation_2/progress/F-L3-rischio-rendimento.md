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
| L3-6 | checkpoint a Risk dei giri 1–3 (G1–G6; rifatto senza la voce di `TODO_FUTURI.md`, 13:0x) | ✅ 2026-10-01: `c66757dcc`…`b69df5c96`, fusione `2130bc42e` validata |
| L3-7 | giro 4: tooltip sui trattini (L1° e L3°), nota del periodo, guida; poi il selettore del benchmark (variante B) dalla primitiva `BenchmarkSelect` di Risk, quando arriva nel mio ramo | ⏳ in corso: vedi «Giro 4» (L4-0…L4-7) |

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
> - copia di prod fresca; build di debug aggiornata, nessun sorgente più recente;
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

> **Terzo giro di review** (2026-10-01): copia di prod fresca, build di debug più recente di ogni
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

> ✅ **Committato** dal developer: `c66757dcc` G1 · `f6f11cb9c` G2 · `eeb22b7dc` G3 · `78b9ba04f` G4 · `41728d8d9` G5 ·
> `b69df5c96` G6. Verificato in sola lettura (`/tmp/libreFolio_f4/verify_l3_merged.sh`, prima linea dei genitori
> `3eff35036..b69df5c96`): messaggi e file uguali per ogni commit, blob identici al registro (`dd0579fb…`) → **PASS**.
>
> **Fusione della punta di Risk** (del coordinatore, 15:3x): `2130bc42e`, genitori `b69df5c96` + `cf09df7f6`, albero
> uguale alla simulazione, pulito. Validata nella 6154, uno per volta (`/tmp/libreFolio_f4/merge2130_gates.sh`, log in
> `/tmp/libreFolio_f4/merge2130/`):
> - `front build --debug` 0; `front check` al pavimento (3 errori e 41 avvisi negli stessi 4 file, nessuno mio);
> - `core-unit` **107 file, 2896 test**, con i due cancelli XSS di K (`htmlInterpolation.gate`, `htmlSink.gate`);
>   `component-unit` **98 file, 2356 test**;
> - `check-orphans` pulito; `i18n audit` 3500 chiavi, tutte tradotte;
> - E2E `risk-lab` **31/31**, `risk` **13/13**, `asset-list` **28/28**;
> - backend `risk-all` non eseguito, per la regola del coordinatore: nessun file del motore di rischio è cambiato, e
>   `series_preparation.py` rende solo pubblica `mark_market_closed_carries`, con corpo identico.
> - Evidenza a Risk e al coordinatore (15:50).

## Giro 4 · 2026-10-01, dalle 15:55

**Via libera**: le bozze del developer («ok per le bozze», 12:4x); Risk (15:51): «Non serve che tu stia fermo […] Puoi
iniziare adesso le voci del giro 4 che non riguardano il selettore». Le chiavi nuove vanno sotto `risk.assetSet.*`.
Il selettore (variante B) arriva dopo, con la primitiva `BenchmarkSelect` di Risk e una fusione vera della sua punta.

**Fatti verificati sul codice (base `2130bc42e`)**:
- **Trattini**: `HtmlCell.tooltip: {text}` (`table/types.ts:147`) avvolge la cella nel `<Tooltip>` del progetto
  (`DataTable.svelte:1372`). Il wrapper è un `role="button"` focalizzabile, e il suo `toggle` chiama
  `event.stopPropagation()` (`Tooltip.svelte:144-145`). **Conseguenza in L3°**: un clic proprio sul trattino apre la
  spiegazione e non seleziona la riga; il resto della riga la seleziona come prima. `DataTable` non espone
  `interactiveChild`, e non è mio: comportamento accettato, da dire al developer in review.
- **Periodo** per un insieme di asset (`series_preparation.py:398-429`):
  - `effective_range` va dal primo all'ultimo giorno di **rendimento** e diventa `metadata.analyzed_range`;
  - `calendar_days` = ultimo rendimento − prezzo di partenza;
  - quindi il primo giorno di prezzo è `analyzed_range.end − calendar_days`, e i giorni inclusi sono
    `calendar_days + 1`. Col periodo 1 ott – 30 set la nota dice «dal 1 ott al 30 set (365 giorni)», come la barra.
  - **Più corto del periodo scelto** quando l'inizio cade più di 7 giorni dopo `dateStart`, o la fine più di 7 giorni
    prima di `dateEnd`. È la soglia di freschezza del progetto, quindi weekend e festivi non lo fanno scattare.
- **Fonte**: i metadati di `riskReturn`, da cui vengono volatilità e rendimento; in mancanza `kpi`, poi `comparison`.
  Senza metadati, o con 0 osservazioni, la nota non compare.
- **Date**: `dayFormatter($currentLanguage)` (`eligibility.ts:123`), come il banner del periodo.
- **Annualizzati**: volatilità e rendimento medio; Sharpe e Sortino ne derivano; beta e correlazione no.

**Passi**:

| # | passo | stato |
|---|---|---|
| L4-0 | piano | ✅ 2026-10-01 |
| L4-1 | test rossi (test-author): helper della finestra, trattini con tooltip in L1° e L3°, via le due note fisse, nota del periodo; E2E | ✅ 2026-10-01 (rilanciati in due dopo la caduta di rete) |
| L4-2 | i18n via `dev.py i18n`: `risk.assetSet.levels.l3.period.{window,narrowed,annualized}` × 4 | ✅ 2026-10-01 |
| L4-3 | codice: `assetSetCalculationWindow` (`assetSetLevels.ts`), tooltip del trattino condiviso (`assetSetTable.ts`), sezioni L1° e L3°, `dateStart`/`dateEnd` passati a L3° | ✅ 2026-10-01 |
| L4-4 | guida (docs-writer, solo EN): `:110-118`, `:128`, ordinamento, selezione collegata, trattino, nota del periodo; `:124` e `:122` aspettano | ✅ 2026-10-01 (da riverificare dopo il codice: due frasi descrivono comportamenti nuovi) |
| L4-5 | cancelli, uno per volta | ⏳ |
| L4-6 | review del developer sulla 6164, poi checkpoint a Risk | ⏳ |
| L4-7 | fusione vera della punta di Risk con `BenchmarkSelect`, poi il selettore sopra L1° e L3° (e `:124` della guida) | ⏳ |

### L4-2 · i18n ✅ 2026-10-01 (script `/tmp/libreFolio_f4/l4_i18n_add.sh`, 3 `dev.py i18n add`)

> **Note implementazione**:
> - Tre frasi composte nella nota, sotto `risk.assetSet.levels.l3.period`:
>   - `window`, con `{start}`, `{end}` e il plurale ICU `{days}`;
>   - `narrowed`, con `{selectedStart}` e `{selectedEnd}`;
>   - `annualized`.
> - Date nello stile del bottone del periodo (`fitPeriod.button`): IT «dal … al», EN «… – …», FR «du … au», ES «del … al»
>   (con «período», come lì).
> - Il trattino non ha una chiave nuova: il tooltip riusa `risk.assetSet.levels.blankNote`, già nelle 4 lingue
>   (approvato nella bozza).

> **⚠️ Fuori pista (16:2x)**: i due agenti del giro (test-author `l4-red-tests`, docs-writer `l4-guide`) sono caduti
> dopo ~25 minuti per errori di rete del modello: una connessione scaduta, poi «408 Timed out reading request body…
> use a smaller request size». Nessuna modifica lasciata nel worktree (`git status`: solo il piano e le 4 chiavi i18n).
> Rilanciati con contesti più piccoli: test-author diviso in due (unitari / E2E, file disgiunti), e letture mirate
> (`grep`, `view_range`) invece dei file interi.

### L4-4 · la guida ✅ 2026-10-01, 16:4x (docs-writer `l4-guide-retry`)

> **Note implementazione** (`mkdocs_src/docs/user/assets/correlation.en.md`, solo EN, la pagina non ha traduzioni):
> - L1° (`:94`, `:106`): icona e nome su una riga; il falso «ⓘ next to each column heading opens its theory page»
>   diventa: la pagina non ordina da sé, ordina solo il clic sul titolo; il titolo spiega in un tooltip e non porta a
>   nessuna pagina; il libro della testata apre Risk Metrics (`docsPath` = `…/risk-metrics/`, verificato), l'occhio
>   mostra o nasconde le colonne.
> - L3° (`:110-121`):
>   - prima la tabella, poi il grafico; «Average annual return» al posto di «Expected return», anche nel titolo
>     dell'avviso, che ora dice anche che descrive il passato;
>   - l'ordinamento del lettore, la riga del periodo, la selezione condivisa (il punto del benchmark non seleziona);
>   - `:131`: tolta la frase sulla nota sotto la tabella, link intatti.
> - `:174`: le date stanno nella riga sotto la tabella di L3°, le cifre in «Calculation details». `:184`: la
>   spiegazione sta sul trattino.
> - `:125` (rombo) e `:127` (*Compared with*, nessun selettore): **verbatim**, aspettano A e Risk.
> - `mkdocs build` (strict) pulito; `check-links` **88 validi, 8 non verificabili, 3 ancore note** (come la base);
>   `sw.js` riscritto con lo stesso timbro → nessuna differenza in git.
> - Da riverificare dopo il codice: la riga del periodo (`:114`) e il trattino (`:184`) descrivono il comportamento
>   del giro 4.

### L4-1 · test rossi prima ✅ 2026-10-01, 16:3x–17:1x (test-author `l4-unit-tests` e `l4-e2e-tests`, file disgiunti)

> **Unitari** (4 file, 235 casi): **45 rossi, 190 verdi**, tutti i rossi nuovi e per la ragione giusta, verificato da
> me (`/tmp/libreFolio_f4/l4_red.log`):
> - `assetSetLevels.test.ts`: 17 rossi, `assetSetCalculationWindow is not a function`. Coprono l'esempio dell'anno,
>   7 casi sul restringimento (con 7 giorni contro 8 su ciascun lato), 4 sul conteggio all'indietro (fine mese più
>   weekend, 29 febbraio 2028, un anno che lo contiene, la notte del cambio d'ora), il giorno singolo con `end` nullo,
>   l'ordine dei risultati, i metadati rotti (letti via `riskMetadata()`, cioè Zod) e i casi `null`;
> - L1°: 8 rossi (la nota fissa c'è ancora; 5 colonne più 2 casi cella per cella senza Tooltip sul trattino);
> - L3°: 17 rossi (la nota fissa in 2 casi; 8 trattini senza Tooltip; 7 casi della nota del periodo);
> - livelli: 3 rossi (nessuna nota del periodo dopo l'arrivo delle cifre).
> - Guardie già verdi: nessuna nota negli stati di errore, caricamento, scarto e vuoto; le chiavi nelle 4 lingue;
>   nessuna nota del periodo senza metadati; una riga di soli trattini si seleziona dal nome.
> - Prova di test-author: implementazione di riferimento in `/private/tmp` → 235/235; 6 difetti voluti, ciascuno preso
>   (conti in ora locale, `>= 7`, partenza il giorno prima del primo rendimento, livelli senza date, Tooltip su ogni
>   cella, date in `'en'` fisso). Copia cancellata.
> - Fissato anche l'ordine delle frasi: periodo, «più corto», «annualizzati».
>
> **E2E** (`risk-lab.spec.ts`): un caso cambiato (nessuna delle due note, ~:4237-4243) e tre nuovi:
> - i trattini di L1° (`:4334`) e di L3° (`:4396`) spiegano sé stessi al passaggio del mouse, e una cifra misurata non ha
>   Tooltip;
> - la nota del periodo (`:4444`): attributi ricavati dai metadati dello stub (`metadata()` dello spec, 87 giorni
>   fissi); la posizione fra tabella e grafico; poi il preset `1y` → `data-narrowed="true"`.
> - Nessuno stub esteso; `risk-mocks.ts` (di E) non toccato; `tsc -p tsconfig.e2e.json` pulito su risk-lab.

### L4-3 · il codice ✅ 2026-10-01, 17:1x

> **Note implementazione**:
> - `assetSetLevels.ts`: `AssetSetCalculationWindow` e `assetSetCalculationWindow(results, dateStart, dateEnd)`.
>   - Legge i metadati con `riskMetadata()`, cioè validati da Zod, e salta quelli rotti e quelli che non hanno
>     misurato nulla.
>   - `start` = `end − calendar_days` in giorni UTC; `days` = `calendar_days + 1`; «più corto» oltre 7 giorni da
>     ciascun lato (`NARROWED_AFTER_DAYS`).
> - `assetSetTable.ts`: `figureCell(html, measured, blankExplanation)`, un solo punto per L1° e L3°. Il trattino ha
>   `tooltip: {text}`, la cifra misurata nessun tooltip.
> - L1°: le tre costruzioni di cella passano da `figureCell`; via la nota fissa e il suo commento (ormai falso).
> - L3°:
>   - `valueColumn` passa da `figureCell`;
>   - due prop nuove obbligatorie, `dateStart`/`dateEnd`;
>   - `calculationWindow`, `formatDay` (`dayFormatter($currentLanguage)`) e `periodText`, composto di tre frasi, la
>     seconda solo se «più corto»;
>   - la nota `risk-asset-set-l3-period` con `data-start/end/days/narrowed` prende il posto della nota fissa, fra la
>     tabella e il grafico.
> - Livelli: `{dateStart} {dateEnd}` passati a L3°.
> - vitest sui 4 file: **235/235** (erano 45 rossi).

### L4-5 · cancelli · 2026-10-01, dalle 17:19 (uno per volta, corsia 6154)

> **Prima tornata** (`/tmp/libreFolio_f4/l4_gates1.sh`, log in `/tmp/libreFolio_f4/l4gates/`):
> - prettier pulito sui 14 file del frontend (dopo `--write` sul solo `AssetSetComparisonLevels.svelte`: la riga del
>   montaggio di L3°, allungata dalle due prop, va a capo una prop per riga);
> - vitest sui 27 percorsi del giro: **27 file, 1044 test**;
> - `front build --debug` 0; E2E `risk-lab` **34/34** (31 + i 3 casi nuovi);
> - `tsc -p tsconfig.e2e.json`: i soliti 4 errori in altri file, 0 negli spec del rischio.
> - **⚠️ Fuori pista**: `front check` dava **5** errori, 2 miei in `assetSetLevels.ts`: il tipo generato allarga ogni
>   giorno di `analyzed_range` a `string | (string | null)[]`, e io lo passavo come `string`. Vitest non controlla i
>   tipi, quindi i 235 test erano verdi. Cura: `singleValue()`, come per ogni campo allargato, e un salto se il giorno
>   resta `null`. Poi vitest sui due file toccati 153/153 e `front check` di nuovo **al pavimento** (3 errori e 41
>   avvisi negli stessi 4 file, nessuno mio). Comportamento invariato su una stringa; la build e l'E2E si rifanno
>   comunque sul codice finale.
> - Interruzione di servizio a metà tornata (17:2x–18:4x): nessun comando lasciato a metà; albero ricontrollato, nessun
>   mutante applicato, 6154 e 6164 libere.

> **Mutanti sui casi E2E nuovi** (`/tmp/libreFolio_f4/l4_mutants.sh`): tre difetti insieme → build → i 4 casi mirati
> (`risk-lab "explains itself" | "shows beta and correlation…" | "publishes the period…"`) → **4/4 rossi**, ciascuno per
> la ragione giusta:
> - nota fissa di L1° rimessa → il caso del benchmark (`:4241`, attesa 0, trovata 1);
> - nessun Tooltip sui trattini → i due casi dei trattini (`badDay` `:4376`, `volatility` `:4428`);
> - `data-narrowed` sempre falso → il caso del periodo, sul preset `1y` (`:2018`).
> - Ripristino byte per byte, sha256 verificato per i tre file.
>
> **⚠️ Fuori pista, e un presupposto falso del MIO brief** (trovato dal docs-writer `l4-guide-period`, verificato da me):
> - avevo scritto che il prezzo di partenza cade sul primo giorno del periodo. **Falso**:
>   - `risk/service.py:635-637` carica i prezzi dal giorno **prima** del periodo;
>   - `series_preparation.py:292-294` prende come base l'ultimo giorno prima del periodo, quando tutti gli asset
>     hanno storia prima;
> - quindi nel caso comune `end − calendar_days` è il giorno prima della barra. La nota avrebbe detto «dal 30 set 2025
>   al 30 set 2026 (366 giorni)», contro la bozza approvata «dal 1 ott 2025 al 30 set 2026 (365 giorni)»;
> - i test erano verdi perché i fixture seguivano il mio brief, non il motore;
> - **cura**, allineata alla bozza approvata: il periodo va dal giorno **dopo** il prezzo di partenza, cioè il primo
>   giorno di cui le cifre colgono il movimento, all'ultimo rendimento: `start = end − calendar_days + 1`,
>   `days = calendar_days`, regola dei 7 giorni invariata. Con storia precedente `start` = il primo giorno della barra.
>   Test prima (test-author), poi una riga di codice.
> - La frase della guida (`:114`) l'ha già riscritta il docs-writer: «sempre le date usate davvero», qualche giorno di
>   differenza a un capo non fa dire «più corto», solo oltre una settimana. Resta vera anche con la cura.
>   - **Test riallineati** (test-author `l4-period-realign`): fixture realistici (l'anno pieno: primo rendimento
>     2025-10-01, `calendar_days` 365); due casi guardia, uno contro la formula vecchia (`end − calendar_days`) e uno
>     contro chi leggesse `analyzed_range.start` (inizio di sabato 2025-10-04, primo rendimento lunedì 10-06); fine di
>     domenica; confini 7/8 e conti all'indietro ricalcolati; E2E `l3PeriodFor` e premesse aggiornati. Contro il codice
>     di prima: **26 rossi**, tutti lo sfasamento di un giorno (`start` un giorno prima, `days` uno in più).
>   - **Codice**: `start = end − (calendar_days − 1)`, `days = calendar_days`; docblock con i fatti del motore. →
>     vitest sui 3 file **184/184**; prettier pulito.

> **Cancelli finali sul codice definitivo** (19:20–19:26, `/tmp/libreFolio_f4/l4_gates2.sh`, log in
> `/tmp/libreFolio_f4/l4final/`, uno per volta nella 6154):
> - prettier pulito; vitest sui 27 percorsi **27 file, 1045 test**;
> - `front check` **al pavimento** (3 errori e 41 avvisi negli stessi 4 file, nessuno mio); `tsc -p tsconfig.e2e.json`
>   4 errori, 0 negli spec del rischio;
> - `front build --debug` 0; E2E `risk-lab` **34/34** (= i test dello spec), `risk` **13/13**;
> - `core-unit` **107 file, 2915 test**; `component-unit` **98 file, 2406 test**, nessun errore non gestito;
> - `check-orphans` pulito; `i18n audit` **3503 chiavi**, tutte tradotte; `check-links` **88 validi**, 8 non
>   verificabili, 3 ancore note (invariato);
> - `git diff --check` pulito; `sw.js` invariato; 6154 libera.

### L4-6 · review del developer sulla 6164 · 2026-10-01, dalle 19:3x

> **Preparazione**: copia di prod fresca, build del codice definitivo, server `l4server` sulla 6164.
>
> **Risposta del developer (ask_user), alla lettera**: «quando scrivi: Periodo: dal 1 lug 2026 al 1 ott 2026 (93
> giorni). Volatilità e rendimento medio sono annualizzati; Sharpe e Sortino derivano da questi. non mettere 93 giorni,
> meglio 3 mesi e 3 giorni e poi andrei a capo a Volatilità e rendimento .... Riguardo al grafico, credi potremmo
> sfruttare il raggio dei puntini per mettere un altra informazione? se si quale? per il resto ok,, mi piace quello che
> hai fatto, fai questo intanto che aspetti risk»
>
> **Il raggio dei puntini** (parere dato, nessun lavoro): si può, ma non lo farei.
> - In Dashboard il raggio vuol dire già «quanto ne possiedi» (05 §7.5, «bolla ∝ peso»), e una selezione non ha pesi.
> - L'area è il canale che si legge peggio, e una bolla grande diventa una classifica implicita.
> - L'unico candidato sensato è la peggior discesa, con legenda, valore nel tooltip e il permesso di A; meglio
>   lasciarla in L1°.
>
> **La durata**: 1 lug – 1 ott, contando i due capi, a mesi di calendario fa «3 mesi e 1 giorno», non «3 e 3» (mesi da
> 30 giorni). Chiesto (ask_user): il developer sceglie **«Mesi di calendario: 3 mesi e 1 giorno, e 1 anno per l'anno
> pieno»**.
>
> **Note implementazione**:
> - i18n (`/tmp/libreFolio_f4/l4_i18n_length.sh`): `period.window` aggiornato a `({length})` nelle 4 lingue; nuove
>   `period.years`, `period.months`, `period.days`, ciascuna con plurale ICU.
> - Test rossi prima (test-author `l4-length-tests`): `calendarLength` (19 casi: l'esempio del developer con la guardia
>   contro i mesi da 30 giorni, mesi tagliati a fine mese, mai a catena, 29 febbraio, cambio d'ora in Europe/Rome);
>   la nota su due righe (`-period-window`, `-period-annualized`), senza il numero dei giorni, con la durata composta
>   dalle chiavi e da `Intl.ListFormat` (caso a tre parti, 1 anno, 2 mesi e 3 giorni). → 23 rossi per le ragioni
>   giuste.
> - Codice:
>   - `calendarLength(start, end)` in `assetSetLevels.ts`: mesi interi da `start`, tagliati a fine mese e mai a
>     catena, poi i giorni rimasti fino al giorno dopo `end`;
>   - nella sezione `periodLength` (parti a zero omesse, `Intl.ListFormat` nella lingua corrente) e `periodWindowText`;
>     la nota ha due `span.block`.
>   - `data-days` invariato.
> - vitest sui 3 file: **204/204**, poi la sezione da sola 104/104 dopo prettier.
> - Guida (docs-writer `l4-guide-length`): `:114` e `:174` dicono la durata «in calendar years, months and days» (con
>   l'esempio 1 luglio – 1 ottobre = 3 mesi e 1 giorno); build strict pulito, `check-links` 88/8/3, `sw.js` invariato.
>
> **Cancelli sul codice definitivo, di nuovo** (22:18–22:24, stesso script, log in `/tmp/libreFolio_f4/l4final/`; la
> tornata precedente è in `l4final_pre_length/`):
> - prettier pulito; vitest **27 file, 1065 test**; `front check` al pavimento (3 errori e 41 avvisi negli stessi 4 file);
>   `tsc -p tsconfig.e2e.json` 4 errori, 0 negli spec del rischio;
> - build 0; E2E `risk-lab` **34/34**, `risk` **13/13**; `core-unit` **107 file, 2934 test**; `component-unit` **98
>   file, 2407 test**;
> - `check-orphans` pulito; `i18n audit` **3506 chiavi**, tutte tradotte; `check-links` 88 validi;
> - `git diff --check` pulito; `sw.js` invariato; 6154 libera.
>
> **Ultimo sguardo del developer** (ask_user, 22:2x): «Periodo: dal 1 lug 2026 al 1 ott 2026 (3 mesi e 1 giorno).» su
> una riga e «Volatilità e rendimento medio…» sotto. Risposta: **«Va bene, procedi col checkpoint»**. Server 6164
> fermato (`lsof`: libera).

## Checkpoint di L3° · giro 4 (tutto tranne il selettore) · 2026-10-01 (verso Risk)

> Il delta, i gruppi (G1–G6) e i digest stanno nel messaggio a Risk e in `/tmp/libreFolio_commits/f-l4-*`.
> Dopo il commit: fusione vera della punta di Risk `68b46721b` (script del coordinatore), poi il selettore
> `BenchmarkSelect` sopra L1° e L3° (L4-7) e la guida `:124`.
> Stato: **FROZEN** fino al commit: niente modifiche, test, server o comandi Git.

> ✅ **Committato** dal developer: `4a52584cd` G1 · `e1911ef8f` G2 · `1fe9a8883` G3 · `446e6f75b` G4 · `37bc78965` G5 ·
> `04cbc4997` G6. Verificato in sola lettura (`/tmp/libreFolio_f4/verify_l4_merged.sh`, prima linea dei genitori
> `2130bc42e..04cbc4997`): messaggi e file uguali per ogni commit, blob identici (`2e7563f5…`) → **PASS**.
>
> **Fusione della punta di Risk** (del coordinatore): `c221ed22d`, genitori `04cbc4997` + `68b46721b`
> (`BenchmarkSelect`, regola B della torta), pulito. Validata nella 6154 (`/tmp/libreFolio_f4/merge_c221_gates.sh`, log
> in `/tmp/libreFolio_f4/merge_c221/`):
> - build 0; `front check` al pavimento;
> - `core-unit` 107/2934; `component-unit` 98/2407; `allocation-unit` 5/211;
> - `check-orphans` pulito; i18n 3507;
> - E2E `risk-lab` 34/34, `risk` 13/13, `risk-benchmark-shared` 4/4.
> - Evidenza a Risk (23:1x).

## Giro 5 · il selettore del benchmark (L4-7) · 2026-10-01, dalle 23:1x

**Decisioni già prese**:
- il developer: variante **B**, sopra L1° e L3°; il selettore mostra sempre la scelta corrente, ed è vuoto solo se
  non è impostata;
- Risk:
  - la primitiva `BenchmarkSelect` (sua), con `measuredAssetIds` uguali agli asset analizzati;
  - la mia frase in `measuredHint`, con una chiave sotto `risk.assetSet.*`;
  - le colonne di beta e correlazione e il punto del benchmark solo con `state === 'set'` e un valore fuori dalla
    selezione.

**Fatti verificati sul codice (`c221ed22d`)**:
- `BenchmarkSelect`:
  - lo stato iniziale è sincrono (`none` o `pending`); poi `resolveRiskBenchmark()` lo conferma contro l'elenco
    degli asset e dà `set` o `unknown`;
  - `value` resta `null` finché lo stato non è `set`;
  - la radice `{testid}-control` pubblica `data-benchmark-id`, `data-benchmark-state` e `data-measured`; il ⚠ è
    `{testid}-measured`.
- Il controller dei livelli (`createRiskPanelController`, di Risk) lancia l'onda base appena montato
  (`$effect` → `applyBaseSignature`) e non ha un cancello.
- Oggi il pannello specchia `riskBenchmark.assetId` in un `$effect` prima che i livelli si montino (dopo la semina
  della selezione), quindi l'onda parte una volta sola, già col benchmark.

**Decisione di implementazione (mia, nessun cambio visibile)**: il selettore si monta **nel pannello**, subito sopra
`AssetSetComparisonLevels`, cioè sopra L1° e L3°; non dentro i livelli.
- Montato dentro, si risolverebbe dopo che il controller ha già sparato: a ogni caricamento con un benchmark salvato
  partirebbero **due onde**, la prima senza benchmark e con un'altra finestra.
- Nel pannello: `bind:value` e `bind:state`; `benchmarkId` diventa un helper puro e testabile (`set`, valore non
  nullo, fuori dagli analizzati); i livelli si montano solo quando lo stato non è più `pending`.
- Con un helper puro la guardia sullo stato si prova direttamente. Il mutante che la toglie, equivalente se si
  guarda il componente intero, qui non lo è.

**Passi**:

| # | passo | stato |
|---|---|---|
| L5-1 | i18n: `risk.assetSet.benchmark.measuredHint` (la frase del ⚠) e `risk.assetSet.benchmark.help` (l'ⓘ) × 4 | ✅ 2026-10-01 (`/tmp/libreFolio_f4/l5_i18n_add.sh`; spazio normale prima dei due punti in FR, come 248 stringhe su 255) |
| L5-2 | test rossi (test-author): helper `labBenchmarkId`, E2E del selettore | ✅ 2026-10-01 |
| L5-3 | codice: helper, selettore nel pannello con l'ⓘ, livelli dopo la risoluzione, docblock del pannello | ✅ 2026-10-01 |
| L5-4 | guida `:124` (docs-writer) | ⏳ |
| L5-5 | cancelli e mutanti, review sulla 6164, checkpoint | ⏳ |

### L5-2 · test rossi prima ✅ 2026-10-01 (test-author `l5-unit` e `l5-e2e`, file disgiunti)

> - **Unitario** (`assetSetSelection.test.ts`): `labBenchmarkId`, 9 casi nuovi, tutti rossi su `labBenchmarkId is not
>   a function` (98 test, 89 già verdi).
>   - La guardia sullo stato è provata da sola: righe `pending`, `unknown` e `none` con un valore non nullo, ciascuna
>     con la controprova che `set` darebbe l'id.
>   - Gli altri casi: l'id fra gli analizzati (anche non in prima posizione), `null`, e l'elenco non toccato.
> - **E2E** (`risk-lab.spec.ts`, aiutanti `:2104-2362`):
>   - casi nuovi, rossi al primo controllo sul selettore: (a) posizione sopra L1° e L3° e apertura su `set`;
>     (b) la scelta nel laboratorio scrive la chiave condivisa; (c) il benchmark fra i selezionati, col ⚠ e la sua
>     frase; (d) un id che non corrisponde a nessun asset, `unknown`;
>   - (e) è una guardia: nessuna onda per-asset senza il benchmark salvato;
>   - due commenti di un caso esistente riallineati al selettore (nessuna asserzione toccata).
>   - Le frasi dell'ⓘ e del ⚠ si confrontano con il catalogo (`fixtures/i18n-data`), il solo modo di distinguere la
>     frase del laboratorio da quella generica.

### L5-3 · il codice ✅ 2026-10-01

> - `assetSetSelection.ts`: `labBenchmarkId(state, value, analysedIds)`.
> - `AssetSetRiskPanel.svelte`:
>   - via lo specchio `$effect` di `riskBenchmark.assetId`;
>   - `benchmarkValue` e `benchmarkState` (iniziale `pending`) legati a `BenchmarkSelect`, e
>     `benchmarkId = labBenchmarkId(…)`;
>   - la riga `risk-asset-set-benchmark-row`: «Confrontato con», l'ⓘ `risk-asset-set-benchmark-help` e il selettore
>     (`measuredAssetIds` = analizzati, `measuredHint` = la mia frase), fra la matrice e L1°;
>   - `AssetSetComparisonLevels` dentro `{#if benchmarkState !== 'pending'}`;
>   - docblock riscritto.
> - vitest `assetSetSelection.test.ts` **98/98**; `front check` al pavimento; `front build --debug` 0.

### L5-4 · la guida ✅ 2026-10-01 (docs-writer `l5-guide`)

> - `:127`: il benchmark si sceglie **su questa scheda**, sotto *Compared with*, in una riga fra la matrice e le due
>   sezioni che cambia; è la stessa scelta di tutte le pagine di rischio, e l'ⓘ lo dice.
> - `:128`: l'elenco esclude i selezionati tranne la scelta corrente; un benchmark che è anche selezionato resta
>   visibile col ⚠ ambra, che spiega perché mancano beta e correlazione.
> - `:171` (*One Shared Window*): il benchmark che entra nella finestra si sceglie nella riga sopra le due sezioni.
> - `:125` (rombo): non toccato. Build strict pulito; `check-links` 88/8/3; `sw.js` invariato.
> - Segnalato dal docs-writer: l'intestazione di `BenchmarkSelect.svelte` (di Risk) dice che Dashboard e broker lo
>   montano, ma nella mia base usano ancora `L3Benchmark`; scrivono lo stesso store, quindi la guida è vera comunque.
>   Lo riporto a Risk.

### L5-5 · cancelli e mutanti · 2026-10-01, dalle 23:5x

> - E2E `risk-lab` **39/39** (34 + i 5 nuovi), dopo `front build --debug`.
> - **Mutanti**, uno per volta (`/tmp/libreFolio_f4/l5_mutants.sh`, log in `/tmp/libreFolio_f4/l5mut/`), ciascuno
>   preso dal caso giusto:
>   - senza il cancello `pending` → (e): le onde portano `[null, 10]`, cioè la prima partiva senza il benchmark. È la
>     prova che il cancello serve: test-author pensava che (e) fosse verde già sul codice vecchio, e lo era solo
>     perché lì il pannello leggeva lo store prima di montare i livelli;
>   - `measuredAssetIds={[]}` → (c): `data-measured` `"false"`;
>   - senza `measuredHint` → (c): la frase generica invece di quella del laboratorio;
>   - selezione non controllata (`labBenchmarkId(…, [])`) → (c): L3° applica il benchmark (`data-benchmark="true"`).
>   - La guardia sullo **stato** è un mutante **equivalente** a livello di componente: con la primitiva di oggi
>     `value` resta `null` finché lo stato non è `set`, come Risk aveva detto. La prendono le righe `pending`,
>     `unknown` e `none` del test unitario dell'helper.
>   - Ripristino con sha256 verificato dopo ogni mutante; build finale sul codice ripristinato.
> - **Cancelli finali** (00:17–00:24, `/tmp/libreFolio_f4/l5_gates.sh`, log in `/tmp/libreFolio_f4/l5final/`):
>   - **⚠️ Fuori pista**: il primo lancio non è partito (lo strumento ha reso un'uscita vuota senza eseguire: la
>     cartella dei log non esisteva). Rilanciato; nessun effetto.
>   - prettier: **un file**, `risk-lab.spec.ts`, formattato a mano da test-author → `--write`. La differenza è solo
>     di spazi più una virgola finale negli argomenti di due `expect(…)`, verificato confrontando il testo
>     normalizzato. Poi tsc risk-lab pulito e `risk-lab` di nuovo **39/39**;
>   - vitest **27 file, 1074 test**; `front check` al pavimento; `tsc -p tsconfig.e2e.json` 4 errori, 0 negli spec del
>     rischio;
>   - build 0; E2E `risk-lab` **39/39**, `risk` **13/13**, `risk-benchmark-shared` **4/4**;
>   - `core-unit` **107/2943**; `component-unit` **98/2407**;
>   - `check-orphans` pulito; i18n **3509** chiavi, tutte tradotte; `check-links` 88;
>   - `git diff --check` pulito; `sw.js` invariato; 6154 libera.

> **Review del selettore sulla 6164** (2026-10-02):
> - **⚠️ Fuori pista**: il developer ha riavviato il programma per aggiornarlo, e il riavvio ha fermato il server (era
>   legato alla sessione); la domanda di review era rimasta a metà. La copia era stata scritta (`e689ab09…`) →
>   sostituita con una copia fresca; la build era ancora più recente di ogni sorgente; server
>   riavviato (shell `l5server2`, PID 93092), `/assets` 200. HEAD invariata (`c221ed22d`), albero invariato (10 file).
>
> **Review del developer (ask_user, 2026-10-02 09:5x), alla lettera**: «l componente che fa il cerca, vorrei sfruttasse
> il pannel che abbiamo sviluppato per la sezione iniziale, che si apre con il "+", ha i filtri e i nomi scorrono, è
> molto meglio, ti dirò di più, sarebbe fantastico averlo anche nel segnale del "Confronto Asset", mi pare che quello che
> c'è ora lo hai preso da lì, dove altro è usato? potremmo migrarlo al nuovo ovunque. Riguardo il tooltip hai scritto:
> Lo stesso benchmark di tutte le pagine di rischio: cambiarlo qui lo cambia ovunque. Si misura insieme agli asset
> scelti, aggiunge beta e correlazione e, se ha una storia più corta, restringe il periodo delle due sezioni qui sotto.
> ma toglierei il faatto che sia lo stesso in tutte le pagine di rischio, userei una frase corta che spiega che serve
> per scegliere un asset di riferimento, considerato il "rischio base" e fa capire, asset per asset, se il rischio è
> superiore o meno, o insomma una frase così, informativa. Nella lista degli asset che compaiono non ci sono quelli
> selezionati, mi pareva avessimo deciso che potessero essere scelti anche loro, o è in risk ancora? Per altro mettere
> [un suo asset] o gli altri asset con 0 prezzi, similmente a quanto avviene con "+" divrebbero essere esclusi perchè non
> ammissibili. Poi mettendone 1 ottengo: Giornata storta: Parziale · Mese storto: Parziale · Discese per asset: Parziale
> Prezzi fermi da più di 7 giorni per N asset: […] ma non in un banner come abbiamo sviluppato, ma sia dentro "quanto
> fa male?" che "quanto ha pagato ciascuno" A livello di posizionamento, io lo ripeterei dentro ogni pannel in cui è
> utile poterlo editare, senza fare continuamente sopra sotto, altrimenti lo mettevamo direttamente in cima.»
>
> **Analisi (verificata sul codice, `c221ed22d`)**:
> 1. **Il «Parziale» in L1°**: L1° e L3° fanno una richiesta sola (`buildBaseAnalytics`, `includeAssetSetLevels`, in
>    `riskAnalysisHelpers.ts:313-345`, di Risk), e `asset_set_comparison` vi entra col benchmark. Il motore prepara la
>    finestra comune per richiesta, benchmark compreso (guida `:171`), quindi il benchmark cambia anche la finestra di
>    L1°, che non lo mostra. I due ETF «fermi da più di 7 giorni» sono probabilmente l'effetto dei giorni del
>    benchmark alla fine della finestra (ipotesi, non misurata). Cura possibile: due richieste, L1° senza benchmark
>    (sulla finestra della matrice) e L3° col benchmark. Serve separare `includeAssetSetLevels` in due gruppi: file di
>    Risk.
> 2. **Avvisi**: tutte le sezioni del laboratorio (Correlazione, L1°, L3°, Replay) li mostrano come righe ambra nella
>    propria cornice (`RiskLevelSection`, di Risk; guida «Each Section Speaks for Itself»). L'unica striscia del
>    laboratorio è quella del periodo (`risk-fit-period-banner`); in Dashboard c'è `DataQualityBanner`.
> 3. **Asset selezionati nell'elenco**: la decisione del developer, riportata da Risk, riguardava gli asset
>    **posseduti**, che si possono scegliere. Quelli **selezionati** restano fuori perché il motore rifiuta un asset
>    misurato contro sé stesso (`schemas/risk.py:1578`); se la scelta corrente è fra i selezionati, si vede col ⚠.
>    Non è un lavoro rimasto in Risk.
> 4. **Asset non ammissibili** (0 prezzi): il «+» li tiene fuori con i verdetti di idoneità
>    (`LabAssetPicker`, `eligibility`); `BenchmarkSelect` (di Risk) non ha un modo di escluderli: serve una prop, o il
>    pannello del punto 5.
> 5. **Il componente di ricerca**: `AssetSelect` (ui, condiviso), su `SearchSelect`, si usa in 6 posti:
>    - `SignalAssetParamControl` (il segnale «Confronto Asset»);
>    - `ImportWizardModal` e `TransactionFormModal`;
>    - `AssetMergeModal`;
>    - `BenchmarkSelect` e `L3Benchmark`.
>    `LabAssetPicker` (mio) è a scelta multipla, con filtri, idoneità e nomi che scorrono. Migrarlo ovunque vuol dire
>    estrarne un pannello riusabile anche a scelta singola; i file sono di più proprietari → coordinatore.
>
> **Decisioni del developer (ask_user, 2026-10-02, 10:0x–10:2x), alla lettera**:
> 1. Posizione e misura: prima «Solo in L3°, e L1° misurato senza benchmark (consigliato)»; poi: «vai da risk, era in
>    dashboard ma lì abbiamo fatto un bel lavoro di fattorizzazione e spiegazione, vorrei che riusassi quel banner, e sto
>    iniziando a pensare, essendo un parametro "comune" forse ha senso che sia all'inizio la sua scelta, vicino alla
>    scelta degli asset da analizzare, poi che per ora lo usa solo L3 è un caso». → Il selettore va **in cima**, vicino
>    alla scelta degli asset; L1° resta **misurato senza benchmark** (decisione non revocata).
> 2. Avvisi di qualità dei dati: **il banner della Dashboard**, tramite Risk. Verificato: lì le cornici L1-L3 mostrano
>    solo gli errori (`levelErrorHealth`, `partialNotice.ts:49`), e la qualità dei dati sta in `DataQualityBanner`
>    (`RiskPanelHeader.svelte:116`, alimentato da `controller.dataQualityIssues`).
> 3. Asset selezionati come benchmark: «Permettere di sceglierli: diventa il riferimento degli altri (lavoro di Risk)».
> 4. Asset non ammissibili (0 prezzi) fuori dall'elenco, come nel «+».
> 5. Tooltip dell'ⓘ: una frase corta e informativa (asset di riferimento, «rischio di base», asset per asset più o meno
>    rischioso); via «lo stesso in tutte le pagine».
> 6. Pannello del «+» al posto del cerca: «sono daccordo con il piano, ma nell'import guidato terrei l'attuale»; e
>    «Tenere l'attuale anche in «Unisci asset»». Tappe:
>    1. il pannello riusabile con la scelta singola (mio);
>    2. `BenchmarkSelect` lo adotta (Risk), con l'esclusione degli asset non ammissibili;
>    3. il segnale «Confronto Asset»;
>    4. il modulo della transazione.
>    L'import guidato e «Unisci asset» tengono `AssetSelect`.
>
> Server 6164 fermato (`lsof`: libera).
>
> **Risposte (10:3x)**:
> - **Coordinatore**:
>   - il pannello riusabile sta in `frontend/src/lib/components/ui/select/`, accanto ad `AssetSelect.svelte`;
>   - **concessione a F**: solo file nuovi (il pannello e il suo test jsdom) più una riga in `component-unit`
>     (`_frontend_utility.py`), con `check-orphans`; `index.ts` e `AssetSelect.svelte` non si toccano;
>   - tappe: 1 di F; 2 e 3 della famiglia Risk; la 4 (`TransactionFormModal`) **non ora**: dopo che il pannello è in
>     `dev_release2` e dopo la fase F di L; il proprietario lo decide lui. Ogni tappa ha test rossi prima e il suo
>     checkpoint.
> - **Risk**:
>   1. la divisione delle richieste è **concessa una tantum**: due flag additivi in `buildBaseAnalytics`
>      (`includeAssetSetLossLevels`, `includeAssetSetPaidLevels`, con `includeAssetSetLevels` come loro unione) e il solo
>      passaggio delle opzioni in `riskPanelController.svelte.ts` (`:122`, `:271`), più i loro test. Rossi prima, e
>      un pin che le richieste dei chiamanti di oggi restino identiche byte per byte. Niente altro in quei file. La
>      guida `:168/171` cambia con la decisione: mia;
>   2. banner **confermato**: cornici con `levelErrorHealth`; il replay con la sua salute; le azioni su `openSync`;
>      la mappatura delle azioni scritta nei miei file (quella di `RiskPanelHeader` è di A); le questioni dei tre
>      controller deduplicate con la chiave con cui il banner le raggruppa;
>   3. il benchmark fra i selezionati è **suo** (decisione D370); fino ad allora `measuredAssetIds` resta la
>      selezione;
>   4. asset non ammissibili: **niente prop provvisoria**, arrivano con la tappa 2;
>   5. tappe: 1 mia; 2 `BenchmarkSelect` sua e `AssetSetRiskPanel` mio; 3 sua;
>   6. il testo dell'ⓘ: mio.
>   - L'ordine va bene: ora il selettore in cima e l'ⓘ, poi il checkpoint del giro 5; poi la divisione e il banner;
>     poi la tappa 1.
>
> **Giro 5b · il selettore nella scheda della selezione** (test-author `l5b-placement`): il caso (a) ora vuole la riga
> dentro `risk-asset-set-controls`, dopo le chip (`risk-selected-assets`), prima della matrice e dei due livelli. Sul
> codice di oggi è rosso: la riga sta dopo la matrice, fuori dalla scheda.
>
> **Note implementazione (5b)**:
> - `AssetSetRiskPanel.svelte`: la riga «Confrontato con ⓘ [selettore]» diventa l'ultima della scheda della selezione
>   (`risk-asset-set-controls`), con un filetto sopra. È montata con la scheda, quindi la scelta salvata si conferma
>   prima che i livelli chiedano i dati; il cancello `pending` resta.
> - ⓘ (`/tmp/libreFolio_f4/l5b_i18n_help.sh`, `dev.py i18n update`): «L'asset di riferimento, il «rischio di base»:
>   beta dice, asset per asset, se ciascuno si è mosso più (sopra 1) o meno (sotto 1) di lui; la correlazione, quanto
>   insieme.» nelle 4 lingue.
> - Guida (docs-writer `l5b-guide`): `:127` e `:171` mettono la riga nel pannello in cima alla scheda, e l'ⓘ spiega a
>   cosa serve; il fatto che la scelta sia comune a tutte le pagine resta nella guida. Build strict pulito, 88 link.
> - **Cancelli** (11:14–11:21, `/tmp/libreFolio_f4/l5b_gates.sh`, log in `/tmp/libreFolio_f4/l5bfinal/`):
>   - prettier pulito; vitest 27/1074; `front check` al pavimento; tsc e2e 0 negli spec del rischio;
>   - build 0; E2E `risk-lab` **39/39** (il caso della posizione, rosso prima, ora verde), `risk` 13/13,
>     `risk-benchmark-shared` 4/4;
>   - `core-unit` 107/2943; `component-unit` 98/2407; orfani pulito; i18n 3509; link 88;
>   - `git diff --check` pulito; `sw.js` invariato; 6154 libera.
>
> **Review (ask_user, 11:3x), alla lettera**: «va bene ,procedi con il checkpoint, ma mi chiedevo, avendo il beta, sul
> grafico rendimento-volatilità il beta non si disegna con una retta o sbaglio?» — risposta di teoria nella chat (la
> retta del beta sta sul grafico beta-rendimento, la Security Market Line; su quello volatilità-rendimento la retta è
> la Capital Market Line, un verdetto che il laboratorio non disegna). Nessun lavoro richiesto. Server 6164 fermato.

## Checkpoint di L3° · giro 5 (il selettore del benchmark) · 2026-10-02 (verso Risk)

> Il delta, i gruppi (G1–G5) e i digest stanno nel messaggio a Risk e in `/tmp/libreFolio_commits/f-l5-*`.
> Dopo il commit: la divisione L1°/L3° (concessa), il banner della qualità dei dati, poi la tappa 1 del pannello.
> Stato: **FROZEN** fino al commit.
>
> **Ritocco chiesto dal developer prima del commit (11:3x), alla lettera**: «poi, nella label Per ogni asset
> selezionato, quanto ha oscillato e quanto ha reso in media all'anno, nel grafico e nella tabella; con un benchmark
> scelto nella Dashboard, anche quanto si è mosso insieme a lui. aggiorna la parte della scelta del benckmark poi».
> - `risk.assetSet.levels.l3.description` × 4 (`/tmp/libreFolio_f4/l5_i18n_l3desc.sh`): «… nella tabella e nel grafico;
>   con un benchmark scelto in cima alla scheda, anche quanto si è mosso insieme a lui.» Era l'ultima frase del
>   laboratorio a nominare la Dashboard (cercato in `risk.assetSet.*` nelle 4 lingue); in più, l'ordine segue la pagina,
>   con la tabella prima del grafico.
> - vitest `assetSetI18n`, sezione e livelli: 145/145; E2E non rifatti, perché nessun selettore legge testo tradotto.
> - Registro rifatto (G1 e G5 cambiano) e mandato a Risk.

> ✅ **Committato**: `34bf2d804` G1 · `8f94b5d16` G2 · `8a7124782` G3 · `ec2c4dad7` G4 · `23c63080a` G5. Verificato in sola
> lettura (`/tmp/libreFolio_f4/verify_l5.sh`, base `c221ed22d`): messaggi e file uguali, blob identici (`b185999a…`)
> → **PASS**.

## Giro 6 · L1° senza benchmark, poi il banner della qualità dei dati · 2026-10-02, dalle 11:4x

**Decisione del developer** (10:0x): «Solo in L3°, e L1° misurato senza benchmark». **Concessione di Risk**, una
tantum, solo per questa divisione:
- `riskAnalysisHelpers.ts`: in `buildBaseAnalytics`, due flag additivi, `includeAssetSetLossLevels` (VaR ×2 e drawdown)
  e `includeAssetSetPaidLevels` (KPI, risk_return e comparison col benchmark); `includeAssetSetLevels` resta la loro
  unione;
- `riskPanelController.svelte.ts` (`:122`, `:271`): il solo passaggio delle due opzioni;
- i loro test, rossi prima, con un pin che i chiamanti di oggi mandino richieste identiche byte per byte.
- Niente altro in quei due file.

**Fatti verificati (`23c63080a`)**:
- Oggi l'ordine delle analisi per-asset è: kpi, var 1g, var 30g, drawdown, risk_return, comparison
  (`riskAnalysisHelpers.ts:313-345`). L'unione deve restare **identica**, quindi nel codice: kpi (paid), poi var, var e
  drawdown (loss), poi risk_return e comparison (paid).
- `correlation` entra in ogni onda storica che la capacità permette (`add('correlation')`), quindi in tutte e due le
  richieste nuove.
- Senza benchmark le due richieste hanno stessa scala, finestra e valuta → la stessa finestra comune (il motore la
  prepara per richiesta, «never from the analytics list», `riskAnalysisHelpers.ts:250-254`).

**Passi**:

| # | passo | stato |
|---|---|---|
| L6-1 | test rossi (test-author): flag del helper e pin byte per byte, passaggio delle opzioni nel controller, due controller nei livelli; E2E riletti per le richieste divise | ⏳ |
| L6-2 | codice: helper e controller (concessi), due controller in `AssetSetComparisonLevels` | ⏳ |
| L6-3 | guida `:168/171` (docs-writer) | ⏳ |
| L6-4 | cancelli; poi il banner (L6-5…) | ⏳ |

> **In arrivo da Risk (11:4x): D371, l'asset selezionato come benchmark.** La scelta del developer, riportata da Risk,
> testuale: «per le metriche che si calcolano con il benchmark e l'asset stesso è il benckmar, mettici un trattino e un
> tooltip che spiega che non è applicabile perchè se stesso è già il banckmark».
> - Backend (`asset_set_comparison` 1.1.0, di Risk):
>   - il riferimento fra i selezionati è accettato;
>   - `items` sono gli **altri** selezionati, senza il riferimento (nessun beta 1,00 inventato);
>   - i campi `comparison_*` restano quelli del riferimento, sulla stessa finestra;
>   - con il solo riferimento selezionato, `items == []`.
> - Il mio lato, quando la punta di Risk arriva nel mio ramo (passo L7, dopo il giro 6):
>   - `labBenchmarkId` accetta un valore fra i selezionati, e `measuredAssetIds={[]}` toglie il ⚠;
>   - nella riga del riferimento, un trattino in beta e correlazione col tooltip del developer, con `figureCell` e una
>     chiave nuova;
>   - **il grafico**: il punto dell'asset e quello del benchmark coinciderebbero. Risk propone un solo punto, disegnato
>     come benchmark: da portare alla review del developer;
>   - la guida (la frase «cannot be one of the selected assets») cambia;
>   - i test che fissano «mai uno dei confrontati» si riallineano: `AssetSetRiskReturnSection.test.ts:178` e i mock di
>     `risk-lab.spec.ts` (`:870`, `:1988`, `:4146`).

### L6-1 · test rossi prima, E2E (test-author `l6-e2e`)

> - Le richieste si distinguono per le analisi che portano: L1° = `asset_set_var`/`asset_set_drawdown`; L3° =
>   `asset_set_kpi`/`asset_set_risk_return`/`asset_set_comparison`. Aiutanti nuovi: `lossRequestsFor`,
>   `paidRequestsFor` ed `expectLossWithoutComparison`.
> - Adattati senza cambiarne il senso: le letture delle richieste nei casi sull'asset non misurato, sugli ordinamenti
>   di L1° e L3°, sui trattini, sulla nota del periodo, sulla sincronizzazione e sul ricarico. Due erano già fragili:
>   un `[0]` e un `.at(-1)` che potevano cadere sulla richiesta dell'altro livello.
> - Verificato da me (build, poi `risk-lab`): **5 rossi, 34 verdi**, i 5 annunciati, ciascuno sulla richiesta unica
>   che porta il confronto:
>   - una richiesta con una fetta di entrambi i livelli (`:3867`);
>   - `asset_set_var` insieme al confronto (`:4697`);
>   - il confronto arriva a L1° (`:2385`, due casi);
>   - la scelta del benchmark richiede di nuovo L1° (`:4832`).
> - Non fatto, e detto: un controllo a schermo che «L1° non cambia», perché lo stub non riproduce il restringimento
>   della finestra da parte del benchmark e passerebbe per la ragione sbagliata.
>
> **D371 (12:0x)**: il backend è nella punta di Risk `a9f6bcf9f` (`asset_set_comparison` 1.1.0). Arriva nel mio ramo con
> la fusione vera del prossimo checkpoint; poi il passo L7, come sopra.

### L6-1 · test rossi prima, unitari (test-author `l6-unit`) · L6-2 · il codice ✅ 2026-10-02

> - **Unitari**: 190 casi nei 3 file, **20 rossi** prima del codice, tutti sulla divisione mancante (flag che non
>   fanno nulla, opzioni che non arrivano alla richiesta, una sola domanda per due livelli). **6 pin** byte per byte,
>   verdi prima e dopo: l'unione con e senza benchmark, la Dashboard e i broker, Asset Detail, il laboratorio di oggi.
>   L'imbracatura dei livelli ora conta tutti i controller del componente, e i mock rispondono solo alle analisi
>   chieste.
> - **Codice**:
>   - `riskAnalysisHelpers.ts` (concesso): `includeAssetSetLossLevels` e `includeAssetSetPaidLevels`. Le stesse
>     aggiunte nello stesso ordine sotto due guardie, quindi l'unione resta identica; il confronto solo con la parte
>     di L3°.
>   - `riskPanelController.svelte.ts` (concesso): le due opzioni e il loro passaggio, nient'altro.
>   - `AssetSetComparisonLevels.svelte` (mio):
>     - `lossController` (senza benchmark, che lì non si legge nemmeno) e `paidController` (con il benchmark);
>     - stati, `answer_discarded` e «Riprova» per livello;
>     - docblock riscritto.
> - vitest sui 3 file **190/190**; prettier pulito (lo spec E2E formattato con `--write`: solo spazi e virgole finali,
>   verificato col testo normalizzato); tsc e2e pulito su risk-lab.

### L6-3 · guida ✅ (docs-writer `l6-guide`) · L6-4 · cancelli ✅ 2026-10-02, 12:15–12:3x

> - Guida `:171`: il benchmark entra nella finestra di «What did each of these pay for its risk?» **soltanto**; «How much
>   did each of these hurt?» e la matrice restano sulla finestra della selezione. Verificato anche nel backend
>   (`service.py:183`, `:191-196`: il benchmark entra nella finestra solo della richiesta che chiede il confronto). Build
>   strict pulito; 88 link.
> - Cancelli (`/tmp/libreFolio_f4/l6_gates.sh`, log in `/tmp/libreFolio_f4/l6final/`):
>   - prettier pulito; vitest 27 file, **1100** test; E2E `risk-lab` **39/39** (i 5 rossi di prima ora verdi), `risk`
>     13/13, `risk-benchmark-shared` 4/4;
>   - `risk-controller-unit` 59/59, `risk-levels-component` 75, `core-unit` 107/2955, `component-unit` 98/2416;
>   - orfani pulito; i18n 3509; link 88; `git diff --check` pulito; `sw.js` invariato.
>   - **⚠️ Fuori pista**: `front check` dava 4 errori, uno nuovo in `AssetSetComparisonLevels.test.ts:807` (un
>     `parameters?.comparison_asset_id` senza cast). Corretto da test-author come in `riskPanelController.test.ts:114`
>     (190/190), poi `front check` di nuovo **al pavimento** e `component-unit` 98/2416.
>
> **Review (ask_user, 12:4x), alla lettera**: «non posso fare la prova perchè il confronta con mostra ancora solo gli
> asset non selezionati, e il pannel non è quello del + che avevamo deciso». Spiegato che D371 entra con la fusione dopo
> questo checkpoint e il pannello con le tappe 1 e 2; scelta del developer: **«Checkpoint ora della divisione, e review a
> selettore completo»**. La divisione è coperta dai test (5 E2E rossi e poi verdi, 6 pin byte per byte). Server 6164
> fermato (si era ricostruito da sé all'avvio, perché un file di test in `src` era più recente della build: stesso
> codice provato).

## Checkpoint · giro 6a, la divisione L1°/L3° · 2026-10-02 (verso Risk)

> Il delta, i gruppi (G1–G5) e i digest stanno nel messaggio a Risk e in `/tmp/libreFolio_commits/f-l6-*`.
> Dopo il commit: la fusione vera della punta di Risk (con D371), poi D371 lato mio, il banner e la tappa 1, e una
> review unica a selettore completo.
> Stato: **FROZEN** fino al commit.

> ✅ **Committato** (13:0x): `f778901b7` G1 · `5053c3f65` G2 · `054f95d0e` G3 · `9a8dbdf55` G4 · `ac6145784` G5. Verificato
> in sola lettura (`/tmp/libreFolio_f4/verify_l6.sh`): **PASS**, blob identici (`d570c9d2…`).
>
> **Note scritte durante il congelamento** (tenute fuori dal worktree finché il diario era nel checkpoint):
> - **Dati reali** (coordinatore e Risk, 12:5x):
>   - `chmod -R go-rwx /tmp/librefolio-r2-f-prodcopy`: `drwx------`, 0 file leggibili da altri;
>   - cancellati, senza handle aperti (`lsof`) e con `ls` come prova, i log dei server di review che puntavano alla
>     copia: i due che Risk aveva nominato (`/tmp/libreFolio_FL3b_server_6164.log`, `…_r2.log`) e altri 7 miei
>     (`/tmp/libreFolio_f4/l{1,3,4,5,5b,6}_server_6164*.log`);
>   - `/tmp/libreFolio_f4` ora è `go-rwx`, e lì vanno i log di review nuovi.
>   - Non miei, segnalati e non toccati: `/tmp/libreFolio_i_integ_check.log` e `/tmp/librefolio-r2-prod-snapshot`
>     (`dr-xr-xr-x`).
>   - La copia si cancella dopo la review finale (`lsof +D`, poi `ls`, poi una nota qui).
> - **Concessioni a Risk** (13:0x e 13:1x), una tantum, sul suo ramo, per F3, il blocco del replay:
>   - `AssetSetReplaySection.svelte:108/111` (ragioni ed errori via `replaySectionView`) e il punto 📌 del suo
>     docblock (`:43-47`, solo commenti);
>   - `AssetSetReplaySection.test.ts:309` e il cablaggio;
>   - in `risk-lab.spec.ts`, il cancello `risk-replay-audit` (~`:600`) e lo stub del replay (~`:917-1011`).
>   - Mi arrivano con la sua punta.
> - **Concessione di Risk a me**, solo commenti, per D371: in `riskAnalysisHelpers.ts`, il JSDoc di
>   `assetSetBenchmarkId` (`:266-268`) e il paragrafo «The reference may not also be one of the measured…»
>   (`:357-360`).
> - **Da correggere** (Risk): il docblock di `AssetSetComparisonLevels.svelte` cita `service.py:170`; va citato il
>   simbolo, la chiamata `_prepare_asset_series` in `RiskService.execute`.
>
> **Fusione della punta di Risk** (13:2x): `a8c1d8d77`, genitori `ac6145784` + `a9f6bcf9f` (D371: `asset_set_comparison`
> 1.1.0), albero `5aaa75f43`, pulito.
> - Validata nella 6154 (`/tmp/libreFolio_f4/merge_a8c1_gates.sh`, log in `/tmp/libreFolio_f4/merge_a8c1/`):
>   - build 0; `front check` al pavimento;
>   - `core-unit` 107/2955; `component-unit` 98/2416; orfani pulito; i18n 3509;
>   - E2E `risk` 13/13, `risk-benchmark-shared` 4/4; backend `services risk-asset-set` **30/30** (il backend di D371
>     tocca la mia L3°).
> - **⚠️ Fuori pista: `risk-lab` exit 1, con 38 verdi, 1 non eseguito e 1 errore fuori dai test.**
>   - Il caso del preset broker (`:5193`) lascia una `route.fetch` in volo alla sua fine, nel gestore di
>     `captureReports` (`risk-lab.spec.ts:2542`): «route.fetch: Test ended».
>   - Playwright la conta come errore fuori dai test e salta il caso seguente (`:5360`, «a report discarded by a
>     portfolio mutation in flight…»).
>   - La fusione non tocca lo spec, quindi è una fragilità del test e non un difetto di prodotto; probabilmente
>     intermittente, da verificare.
>
> ⏸️ **PAUSA** (13:3x, coordinatore, su richiesta del developer). Nessun comando in corso; nessun server; 6154 e 6164
> libere; nessuna operazione Git; il lavoro resta nel worktree com'è.
> - **Fatto**: giri 1–6a committati; la fusione `a8c1d8d77` validata, tranne il rosso qui sopra.
> - **In corso**: niente; il diario è l'unico file modificato.
> - **Prossimo passo esatto**, alla ripresa:
>   1. triage del rosso di `risk-lab` (skill test-triage: rilanciare `risk-lab` una volta e leggere se torna);
>      se torna, test-author rende il gestore di `captureReports` tollerante alla fine del test, per esempio con
>      `page.unrouteAll({behavior: 'ignoreErrors'})` in fondo al caso del preset broker, o con un gestore che
>      ignora l'errore «Test ended»;
>   2. poi il mio lato di D371:
>      - `labBenchmarkId` accetta un valore fra i selezionati, e `measuredAssetIds={[]}`;
>      - trattino e tooltip del developer nella riga del riferimento;
>      - il punto unico nel grafico, da portare in review;
>      - i due commenti concessi e il docblock di `service.py:170`;
>      - la guida;
>      - i test che fissavano «mai uno dei confrontati»;
>   3. poi il banner della qualità dei dati, poi la tappa 1 del pannello, poi la review unica a selettore completo.

## Ripresa · 2026-10-05, dalle 09:4x

> ▶️ **Riprendi** (coordinatore, 09:48). La mia corsia è sopravvissuta alla pulizia di macOS su `/tmp` delle 00:01:
> `app.db` del 02/10. Lo snapshot condiviso `/tmp/librefolio-r2-prod-snapshot` invece è stato cancellato dalla pulizia.
> - **Copia di prod**: il developer ha deciso di toglierla subito. L'ha cancellata il coordinatore alle 09:49:37: niente
>   in ascolto sulla 6164, `lsof +D` vuoto, `ls` «No such file or directory», e verificato anche da me. In `/tmp` non
>   resta nessuna copia di prod. La review finale userà una copia nuova, fatta dopo l'aggiornamento dei prezzi e con
>   l'OK del developer.

### Triage del rosso di `risk-lab` (skill test-triage) · 2026-10-05

> **Evidenza** (log del 02/10, `/tmp/libreFolio_f4/merge_a8c1/07_risklab.log`):
> - «route.fetch: Test ended», dentro `captureReports` (`risk-lab.spec.ts:2542`), alla fine del caso del preset broker
>   (`:5193`); Playwright lo conta come «1 error was not a part of any test» e salta il caso seguente (`:5360`).
> - La richiesta ha `referer: /dashboard`: è il report che la Dashboard manda dopo il login del `beforeEach`. Il caso
>   installa `captureReports` mentre la pagina è ancora sulla Dashboard, quindi il gestore inoltra anche quel report
>   con `route.fetch()`. Poi la pagina va su `/assets`, ma la `route.fetch` lato Node resta in attesa del backend; se il
>   backend è lento, è ancora in volo quando il test finisce.
> - La fusione `a8c1d8d77` non tocca lo spec né il codice coinvolto.
>
> **Rilancio** una volta, come chiesto dal coordinatore (build ancora più recente dei sorgenti): `risk-lab` **39/39**
> (`/tmp/libreFolio_f4/triage_risklab_rerun.log`).
>
> **Verdetto: assumption** (§8 della skill). Il test presume che i suoi gestori siano fermi quando finisce, e inoltra una
> richiesta che non gli serve. Un rilancio verde non toglie una corsa che il log mostra; «flaky» non è un verdetto.
> **Cura nello stesso giro**, solo nel test (file mio), con test-author:
> - `page.unrouteAll({behavior: 'ignoreErrors'})` alla fine di ogni caso, come suggerisce Playwright stesso e come fanno
>   già `stale-price-banner.spec.ts:100`, `toolbar-width-sweep.spec.ts:275` e `asset-mobile-layout.spec.ts:105`;
> - e, se si può fare senza fragilità, `captureReports` che non inoltra i report di altre pagine.
>
> **Prima cura** (test-author `triage-route-teardown`):
> - `afterEach` con `unrouteAll({behavior: 'ignoreErrors'})`;
> - `captureReports` che inoltra solo i report con `Referer` `/assets` (`sentByLab`);
> - una route di contesto che annulla il poll dei prezzi, messa davanti al blocco di `holdLivePricePoll`. test-author
>   aveva letto, e io ho verificato nel sorgente di playwright-core 1.61 (`Route.removeHandler` →
>   `continue({isFallback: true})`), che togliere una route rilascia le richieste che tiene ferme.
> - Risultato: `risk-lab` **39/39**, i tre casi del preset broker eseguiti.
>
> **⚠️ Fuori pista: una regressione trovata nel log del backend della corsia.**
> - Durante quel giro (`/tmp/libreFolio_f4/triage_backend_window.log`, 08:17:47–50Z) il poll dei prezzi ha raggiunto il
>   backend: «Started live quote feed» ×2 (justETF), Yahoo (AAPL, BTC-USD), Borsa Italiana, «[F.2 bootstrap]» ×6 e
>   «Current-price persist: … commit OK (8 row(s) written/updated)», cioè i prezzi di oggi scritti nel DB della corsia.
> - Nel rilancio senza cura (07:5xZ, backend appena avviato) non c'era niente di tutto questo: nessun avvio di feed e
>   nessun bootstrap. Il file è scritto apposta per non scrivere nel DB.
> - Conclusione: con questo teardown l'`unrouteAll` rilascia il poll trattenuto, e la route di contesto non lo ferma.
>   Il percorso nel sorgente dice che dovrebbe; il log dice di no, e vale il log.
> - **Cura rivista**:
>   - niente `unrouteAll` alla fine dei casi, e `holdLivePricePoll` com'era: il poll trattenuto muore con il contesto;
>   - resta la parte 2, `sentByLab`, che toglie la causa;
>   - i gestori che inoltrano al backend (`captureReports`, quello del broker senza posizioni, `release` di
>     `gateReports`) assorbono da sé il proprio errore, così niente può lanciare fuori da un test. È lo stesso principio
>     della guardia del poll.
> - Effetto sul DB della corsia: 8 righe di prezzi del 05/10 (e alcune estensioni intra-giornaliere). Gli altri spec
>   scrivono prezzi a ogni visita, e questi test leggono le proprie risposte, quindi non c'è bisogno di rigenerare il DB.
>
> **Cura rivista** (test-author `triage-route-teardown-2`):
> - via l'`afterEach` e la route di contesto; `holdLivePricePoll` di nuovo com'era nel commit, più una frase sul perché
>   qui niente toglie le route alla fine;
> - resta `sentByLab`;
> - nuovo `routeQuietly(page, url, handler)` per `captureReports`, per il gestore del broker senza posizioni e per la
>   callback di `gateReports`: un errore della callback lascia la richiesta senza risposta e scrive una riga
>   `[risk-lab]` su stderr, invece di lanciare fuori da un test.
> - A metà test un inoltro fallito fa comunque fallire il caso sulle sue barriere (15–20 s), sotto il timeout di 30 s
>   di axios. `release` non assorbe nulla, perché i casi lo attendono.
>
> **Prova** (`/tmp/libreFolio_f4/triage_risklab_fixed2.log`): `risk-lab` **39/39**, nessun errore fuori dai test,
> nessuna riga `[risk-lab]`. Nel log del backend, appena avviato, per tutta la finestra del giro: **0** avvii di feed,
> **0** «Current-price persist», **0** bootstrap, **0** prezzi da Yahoo o Borsa Italiana.
> - Verdetto chiuso: **assumption**, curata nel test. Va nel prossimo checkpoint come gruppo a sé.

## Giro 7 · D371 lato mio: un asset selezionato come benchmark · 2026-10-05

**Decisione** (il developer, riportato da Risk), testuale: «per le metriche che si calcolano con il benchmark e l'asset
stesso è il benckmar, mettici un trattino e un tooltip che spiega che non è applicabile perchè se stesso è già il
banckmark». **Backend** (`asset_set_comparison` 1.1.0, già nel mio ramo con `a8c1d8d77`):
- il riferimento selezionato resta nella selezione e viene **saltato** negli `items` (beta e correlazione con sé stesso
  sarebbero 1 per costruzione: una tautologia);
- la finestra non cambia.

**Contratto (mio)**:
- `labBenchmarkId(state, value)`: il valore se lo stato è `set`, altrimenti `null`. Il parametro della selezione sparisce.
  Nel pannello `BenchmarkSelect` è senza `measuredAssetIds` (cioè `[]`) e senza `measuredHint`, quindi niente ⚠, e la
  chiave `risk.assetSet.benchmark.measuredHint` si toglie.
- `AssetSetPaidRow.isReference`: vero per la riga il cui `assetId` è il `comparison_asset_id` della risposta.
- Celle di beta e correlazione della riga di riferimento: trattino, `data-reference="true"` e un tooltip con la chiave
  nuova `risk.assetSet.levels.l3.referenceItself`, al posto della spiegazione generica del trattino.
- `buildAssetSetChartPoints(rows, benchmark)`: un punto per riga piazzabile; quello del riferimento, se c'è, ha ruolo
  `benchmark` e tiene l'id `asset-<id>`, così la selezione collegata funziona; il punto `benchmark` a parte solo se il
  riferimento non è fra i punti. È la proposta di Risk: un punto solo, **da portare alla review del developer**.
- I commenti diventati falsi:
  - `riskAnalysisHelpers.ts`: il JSDoc di `assetSetBenchmarkId` e il paragrafo «The reference may not also be one of
    the measured» (concessione di Risk, solo commenti);
  - il docblock del pannello, `buildAssetSetBenchmarkPoint`, il commento dello stub E2E;
  - il docblock dei livelli: `service.py:170` diventa la chiamata `_prepare_asset_series` in `RiskService.execute`.
- Guida: le frasi sull'asset selezionato come benchmark (`:127-128`).

**Passi**:

| # | passo | stato |
|---|---|---|
| L7-1 | chiave `risk.assetSet.levels.l3.referenceItself` × 4 | ✅ 2026-10-05 (`/tmp/libreFolio_f4/l7_i18n_add.sh`) |
| L7-2 | test rossi: unitari (helper, righe, punti, sezione) ed E2E (caso (c) riscritto, elenco del selettore con i selezionati) | ✅ 2026-10-05 |
| L7-3 | codice; via `measuredHint` e la sua chiave; commenti | ✅ 2026-10-05 |
| L7-4 | guida; cancelli; poi il banner e la tappa 1, prima della review unica | ✅ 2026-10-05 guida e cancelli; banner → giro 8 |

### L7-2 · test rossi prima, E2E (test-author `l7-e2e`)

> - **(c) riscritto**: il benchmark salvato è uno dei selezionati.
>   - Il selettore è `set` con `data-measured="false"` e senza ⚠.
>   - Una richiesta di L3° porta il confronto con quell'id, nessuna di L1°.
>   - Beta e correlazione ci sono, e nella riga del riferimento sono trattini con `data-reference="true"` e il
>     tooltip `referenceItself`; nelle altre righe sono misurate.
>   - Punti del grafico = numero dei selezionati.
> - **(f) nuovo**: il selettore offre ogni asset selezionato, e uno scelto fra loro si applica.
> - Aiutanti: `L3_BENCHMARK_CELLS`; `paidCell` con beta e correlazione; `castBenchmark` restituisce anche `selected`;
>   `expectComparisonWith` attende un punto in più solo se il riferimento è fuori dalla selezione.
> - Commenti riallineati (lo stub del confronto, `pickUnselectedAssetId`, il caso delle colonne del benchmark e (a)).
> - Verificato da me (build, poi `risk-lab`): **2 rossi, 38 verdi**, ciascuno sul comportamento che manca:
>   - (c) a `:4979`: `data-measured` è ancora `"true"`;
>   - (f) a `:5138`: un asset selezionato non è fra le opzioni.

### L7-2 · test rossi prima, unitari (test-author `l7-unit`) · L7-3 · il codice ✅ 2026-10-05

> - **Unitari**: 322 casi nei 3 file, **48 rossi** prima del codice, tutti sul comportamento che manca:
>   - `labBenchmarkId` che filtra ancora (6);
>   - `isReference` assente (10);
>   - `buildAssetSetChartPoints` che non esiste (21);
>   - le celle del riferimento senza `data-reference` e con il tooltip generico (9);
>   - il grafico con un punto `benchmark` in più (2).
> - Prova di test-author: un'implementazione di riferimento in `/tmp` passa 322/322; 4 errori voluti, ciascuno preso.
> - Due punti di test-author:
>   - **il riferimento da solo non disegna il grafico**: un punto solo, e il minimo resta due. Coerente;
>   - **un clic sul punto del riferimento selezionato seleziona la sua riga**: punto e riga sono lo stesso asset. La
>     vecchia regola («il punto del benchmark non seleziona nulla») valeva perché il benchmark non aveva una riga. Da
>     mostrare al developer in review.
> - **Codice**:
>   - `assetSetSelection.ts`: `labBenchmarkId(state, value)`;
>   - `assetSetLevels.ts`: `isReference` letto dal `comparison_asset_id` validato; `AssetSetChartPoint` e
>     `buildAssetSetChartPoints`; il commento di `buildAssetSetBenchmarkPoint`;
>   - L3°: i punti da `buildAssetSetChartPoints`; nelle colonne di beta e correlazione la riga del riferimento ha il
>     trattino, `data-reference="true"` e il tooltip `referenceItself`;
>   - pannello: `BenchmarkSelect` senza `measuredAssetIds` e senza `measuredHint`; docblock riscritto;
>   - `riskAnalysisHelpers.ts`: i due commenti concessi;
>   - livelli: il docblock cita `RiskService.execute` / `_prepare_asset_series` invece di `service.py:170`;
>   - `dev.py i18n remove risk.assetSet.benchmark.measuredHint -f` (non resta nessun uso; i test della primitiva usano
>     una stringa loro).
> - vitest su 6 file (i 3 di prima più livelli, `assetSetI18n` e `BenchmarkSelect`): **411/411**; prettier pulito.
> - Dopo il codice, una cosa per volta nella 6154:
>   - `front check`: **3 errori e 41 avvisi in 4 file**, la soglia, nessuno mio;
>   - `front build --debug`: completo;
>   - E2E `risk-lab`: **40 passati** (1,7 min), i due rossi di L7-2 compresi.
>   - Log in `/tmp/libreFolio_f4/l7_{check,build,risklab}.log`.

### L7-4 · la guida (docs-writer `l7-guide`) ✅ 2026-10-05

> - `correlation.en.md`, solo EN (la pagina non ha traduzioni):
>   - `:128`: il benchmark **può essere uno dei selezionati**. Il selettore li elenca tutti; quella riga tiene le sue
>     cifre, con il trattino e il tooltip in beta e correlazione; nel grafico compare una volta, come benchmark;
>   - `:117`: solo un benchmark *fuori* dalla selezione non ha riga, quindi il clic sul suo punto non seleziona nulla;
>   - `:171`: un benchmark già selezionato non sposta nessuna finestra;
>   - `:182`: il trattino che vuol dire «non si applica».
>   - La frase del rombo (`:125`) è intatta: aspetta `SYMBOL_BY_ROLE` di A.
> - Ho controllato tutte e quattro le frasi sul codice: sono vere.
> - `mkdocs build` (strict) pulito; `check-links` **88 / 8 / 3**, uguale a prima; `sw.js` invariato.
> - **⚠️ Fuori pista**: docs-writer ha trovato un commento falso in un mio file. In `AssetSetRiskReturnSection.svelte`,
>   il JSDoc di `benchmarkApplies` diceva «…it is not itself in the selection». Corretto: «…the comparison against it
>   was measured», che è quanto `AssetSetComparisonLevels.svelte:168` deriva davvero.
> - Una ricerca nei miei file degli altri «outside the selection» e «not in the selection» non trova altro di falso.
>   Il fuori-selezione resta un caso valido.

> **Da Risk (2026-10-05), per la guida, da fare nel mio giro dopo che F3 (D372) arriva nel mio ramo** (me lo segnala):
> - `correlation.en.md` §What If…? (`:130-146`):
>   - il blocco del replay elenca gli asset lasciati fuori, raggruppati per motivo, sotto le barre; i motivi della
>     sezione non riportano più quelle frasi (i montaggi passano `replaySectionView`). Se la frase d'esempio cita il
>     vecchio avviso d'esclusione, va tolta;
>   - aggiungere il periodo comune: quando i bordi della finestra lasciano fuori degli asset, un pulsante «Replay from
>     {start} to {end}: N assets come back» imposta le date e rilancia con un clic.
> - Ancore nuove linkabili in `historical-replay.en.md`: `#what-the-result-shows`, `#the-common-period`,
>   `#what-takes-its-place`.
> - Nei miei file, sotto le concessioni:
>   - `AssetSetReplaySection.svelte`: `replaySectionView` a `:108` e `:111`, più i codici d'errore del risultato; il
>     punto 📌 del docblock;
>   - il suo test: `:309` fissa il principio sull'avviso dei prezzi fermi; 3 casi di cablaggio;
>   - `risk-lab.spec.ts`: solo il cancello e lo stub del replay. Lo stub lascia fuori l'ultima posizione, e un aiutante
>     nuovo, `expectReplayLeftOutWithoutWeight`, sostituisce la barriera dell'audit.

### L7-4 · i cancelli ✅ 2026-10-05, 11:28-11:35

> `/tmp/libreFolio_f4/l7_gates.sh` (derivato da `l6_gates.sh`, più `BenchmarkSelect.test.ts` e
> `services risk-asset-set`), nella 6154, un comando per volta, su `a8c1d8d77` più l'albero (16 file):
> - prettier sui file toccati: pulito;
> - vitest su 28 file: **1189/1189**;
> - `front check`: **3 errori e 41 avvisi in 4 file**, la soglia (BrokerSharingPanel, GlobalSettingsTab,
>   TransactionFormModal.test, ToolExecutionMetrics);
> - `tsc -p tsconfig.e2e.json`: 4 errori, la soglia, 0 negli spec di rischio;
> - `front build --debug`: completo;
> - E2E: `risk-lab` **40/40**, `risk` **13/13**, `risk-benchmark-shared` **4/4**;
> - `risk-controller-unit` **59/59**, `risk-levels-component` **75/75**, `core-unit` **2984/2984** (107 file),
>   `component-unit` **2437/2437** (98 file);
> - backend `services risk-asset-set` **30/30**;
> - `check-orphans` pulito; i18n 3509 chiavi, 382 inutilizzate (uguale al giro 6); `check-links` **88 / 8 / 3**;
> - `git diff --check` pulito; `sw.js` invariato; 6154 libera.
> - Log in `/tmp/libreFolio_f4/l7final/`.

## Giro 8 · gli avvisi sulla qualità dei dati: analisi · 2026-10-05

**🔴 Presupposto falso** (il disegno confermato da Risk era: «`DataQualityBanner` alimentato dalle `dataQualityIssues`
dei tre controller, azioni su `openSync`»):
- nel laboratorio le `dataQualityIssues` sono **sempre vuote**. Il backend riempie `data_quality.issues` solo per il
  perimetro portafoglio (`portfolio_engine`, tramite `portfolio_data_quality`). Per `asset_set` il rapporto viene da
  `series_preparation`, che lo costruisce in tre punti senza mai `issues`, e il servizio di rischio non le aggiunge
  mai (`_merge_data_quality` unisce solo le liste dei due rapporti). Un `DataQualityBanner` così non comparirebbe mai;
- verificato leggendo, non misurato. Ho provato una sonda in sola lettura sulla 6154
  (`/tmp/libreFolio_f4/l7_dq_probe.py`), ma dopo ogni corsa il DB della lane è vuoto (niente asset né utenti), e
  ripopolarlo non è in un piano approvato. **⚠️ Fuori pista**: per la sonda ho creato `e2e_test_user` con
  `dev.py user --test-db create`. Senza conseguenze: ogni corsa E2E cancella il DB (`populate --force`) prima di
  creare gli utenti. Server fermato; 6154 libera; log `600` nella cartella privata.

**Che cosa ha visto il developer** («Giornata storta: Parziale · Mese storto: Parziale · Discese per asset:
Parziale · Prezzi fermi da più di 7 giorni per N asset», ripetuto in L1° e L3°):
- sono la salute e i motivi di ogni cornice (`RiskLevelSection`). La frase sui prezzi fermi è un **avviso del
  risultato** (`data_quality_stale_prices`, `service.py:961-963`), che arriva su ogni risultato con dati non integri
  insieme allo stato `partial`; nel laboratorio è l'unico canale;
- in Dashboard la stessa cosa la dice **`RiskPartialNotice`**, una volta sopra i livelli (la sua decisione del
  24/09): le cornici L1-L3 tengono solo `levelErrorHealth` (non disponibili e falliti) e nessun motivo; L4 tiene i
  suoi. Il `DataQualityBanner` della Dashboard è un'altra cosa: le questioni del portafoglio, con i pulsanti.

**Opzioni**:
- **A** (consigliata): `RiskPartialNotice` una volta in cima al laboratorio, sotto la scheda della selezione,
  alimentato dai risultati che correlazione, L1° e L3° mostrano. Cornici con `levelErrorHealth`, senza motivi; il
  replay invariato. Solo frontend, file miei, nessuna chiave nuova;
- **B**: A più il `DataQualityBanner` con «Sincronizza» → `openSync`. Serve che il backend (Risk) produca le
  `issues` anche per `asset_set`; la frase dei prezzi fermi comparirebbe due volte, come in Dashboard;
- **C**: un banner costruito nel frontend dagli avvisi: sconsigliata (seconda fonte delle questioni, logica nel
  frontend).

**Decisione del developer (ask_user, 2026-10-05), testuale**: «B — A più il banner con «Sincronizza» (lavoro backend di
Risk)». Ha visto il mock-up delle tre varianti (oggi, A, B) e la nota sulle due frasi con un benchmark dai prezzi fermi.

**Mandato a Risk** (inviato): `data_quality.issues` anche per `asset_set`, aggregate una per categoria come nel
portafoglio (`code + group_key` unico in una risposta), con una delle cinque `cta_action` che il banner conosce.
Proposta mia, in attesa di conferma: deduplicare le quattro fonti (correlazione, L1°, L3°, replay) per
`code + group_key`, la chiave dell'`{#each}` del banner. A parità di chiave con asset diversi, unione degli `affected_*`,
`count` e `message_params.count` alla dimensione dell'unione, `cta_target` il primo.

**Disegno, lato mio**:
- ogni sezione esporta `qualitySource()` → `{results, labels, issues}`:
  - correlazione: `[correlation]`;
  - livelli: i tre di L1° e i tre di L3°, nell'ordine della pagina, con le etichette dei due VaR;
  - replay (in B): `results` vuoti, perché la sua cornice tiene la sua salute, e le sue `issues`;
- il pannello le legge con `bind:this` (il precedente è `labPanel` in `+page.svelte:215`). Ne deriva
  `partialNotice(...)` per `RiskPartialNotice` e, in B, le questioni unite per `DataQualityBanner`. Ordine come in
  Dashboard: banner, poi nota, sotto la scheda della selezione e prima della correlazione;
- cornici di correlazione, L1° e L3°: `levelErrorHealth`, senza `reasons`; il replay invariato;
- il tipo, e poi in B l'aiutante dell'unione, in `assetSetLevels.ts`, così il test è già registrato e il runner
  non si tocca.

| # | passo | stato |
|---|---|---|
| L8-1 | A: test rossi (test-author): unitari delle due sezioni, E2E (b), (c), (d) e la posizione della nota | ✅ 2026-10-05, rimessi dopo la fusione `19b99e8ae` |
| L8-2 | A: codice | ✅ 2026-10-05 (più la guardia e il perché della correlazione) |
| L8-3 | B: rossi e codice sui mock, dopo la conferma di Risk sulla regola dell'unione | ⏳ |
| L8-1b | la guida: la nota di Risk su §What If…? (F3, D372), via docs-writer | ✅ 2026-10-05, più l'allineamento ad A |
| L8-4 | cancelli; poi la tappa 1 del pannello; poi la review unica (con la punta di Risk) | ✅ cancelli del giro 8a; la tappa 1 e la review dopo B |

### L8-1 · i rossi di A (test-author `l8-notice`) ✍️ 2026-10-05

> - Unitari, nei due file delle sezioni: **16 rossi e 46 verdi**. I verdi sono i 44 di prima più 2 guardie nuove: un
>   `unavailable` o `failed` della correlazione resta nella cornice, oggi e dopo. I rossi:
>   - un `partial` ancora nella salute della cornice;
>   - i motivi ancora nella cornice;
>   - `qualitySource` che non esiste.
> - Note di test-author:
>   - l'identità dei risultati si confronta con le voci di `historicalResults` del controller, perché `$state` li
>     avvolge in un proxy;
>   - le questioni piantate sul risultato `correlation` di ogni risposta, l'unico che `allResults` legge;
>   - la reattività provata anche dentro un effetto.
> - E2E: (c) rosso sulla visibilità della nota; (b) e (d) verdi oggi e dopo, perché provano solo l'assenza della nota.
>   I numeri derivati dallo stub (`labNoticeFor`, che ricostruisce le risposte con `resultFor`): in (c) **6** misure
>   parziali (1 correlazione, 3 di L1°, 2 di L3°), una frase sola con 6 occorrenze; in (d) zero.

**Risposta di Risk (2026-10-05)**:
- **sì a B**. La regola dell'unione è mia, ma sta in **un posto solo, il suo**: `mergeQualityIssues(issues)`,
  esportata pura da `riskPanelController.svelte.ts`. La usa anche il controller, perché la collisione avviene anche
  dentro un controller solo (il replay prepara finestre diverse). **Non ne scrivo una mia.** La regola:
  - chiave `code|group_key ?? ''`, nell'ordine della prima comparsa;
  - unione di `affected_asset_ids` (nomi allineati per id, vince il primo) e di `affected_fx_pairs`;
  - `count` e `message_params.count` alla dimensione dell'unione;
  - `cta_target` e gli altri parametri dal primo;
  - `severity` la più grave;
  - per `MISSING_FX_RATES`: `date_from` il minimo, `date_to` il massimo, `dates_count` il maggiore;
- mappatura backend:
  - prezzi portati oltre i 7 giorni → `STALE_PRICE` (`sync_asset_prices`);
  - prezzi inutilizzabili → `MISSING_PRICE` (`navigate_asset`);
  - cambi divisi come nel portafoglio: `add_fx_pair`, `sync_fx_pair`, `navigate_fx`;
  - cambi portati avanti → `MISSING_FX_RATES`;
- ordine:
  1. **io ora**: checkpoint del lavoro sporco (correzione di `risk-lab` e D371), prima della sua punta; poi A;
  2. Risk: fusione `dev_release2` → Risk, poi D15 con `mergeQualityIssues`, rossi prima, in un checkpoint: B lo
     cablo su quella;
  3. Risk: le `issues` per `asset_set` nel backend, in un checkpoint suo;
- F3 è committato (`c42bbad9e`): la mia nota della guida su §What If…? può entrare nel prossimo giro.

**⚠️ Fuori pista: i rossi di A erano già nell'albero** quando è arrivata la richiesta di checkpoint. In
`risk-lab.spec.ts` stavano accanto al giro 7. Li ho tolti dal checkpoint senza perderli:
- copia privata in `/tmp/libreFolio_f4/l8_A_backup/` (`700`/`600`), sha256:
  - `risk-lab.spec.ts` `42a7311d…`;
  - `AssetSetComparisonLevels.test.ts` `4223f6d5…`;
  - `AssetSetCorrelationSection.test.ts` `105e590c…`;
- i due unitari riportati a HEAD con `git show HEAD:<file> > <file>` (nessun comando Git che modifichi lo stato);
  `git diff --quiet` lo conferma;
- dallo spec, tolti gli 11 blocchi di A con `l8_strip_A.py` (il diff `-U0` applicato al contrario, dal basso);
- prova con `l8_verify_strip.py`: i blocchi rimasti, contati sui numeri di riga di HEAD, sono **identici, 38 su 38**, ai
  blocchi non-A della copia; nessun identificatore di A rimasto;
- l'albero torna ai 16 file del giro 7, e i cancelli girano di nuovo su quell'albero.

Dopo il commit e la fusione della punta di Risk, A torna con `git merge-file`:
- base: lo spec del giro 7 committato;
- nostro: lo spec fuso;
- loro: la copia.

### Checkpoint del giro 7 · i cancelli sull'albero consegnato ✅ 2026-10-05, 12:17-12:22

> `/tmp/libreFolio_f4/l7ckpt_gates.sh`, nella 6154, un comando per volta, sui 16 file del giro 7 (senza A):
> - prettier pulito; vitest **1189/1189** (28 file);
> - `front check` e `tsc e2e` alla soglia, 0 negli spec di rischio;
> - build completo; `risk-lab` **40/40**; `check-orphans` pulito; `git diff --check` pulito; `sw.js` invariato;
>   6154 libera.
> - Log in `/tmp/libreFolio_f4/l7ckpt/`.
> - **Nessuna attività dei provider** durante le corse di `risk-lab` di oggi (09:30Z e 10:20Z) nel log della lane.
>   Il log è cumulativo dal 29/09, e il conteggio grezzo (496) va letto per finestra di corsa.
> - **Reperto, non mio**: durante la corsa `front-portfolio risk` dei cancelli (backend avviato alle 09:31:54Z, spec
>   di E) il poll dei prezzi live della Dashboard ha raggiunto i provider veri (justETF, Borsa Italiana, Kitco) e ha
>   scritto **8 righe di prezzo**, due volte, nel DB della mia lane, alle 09:32:20Z. Raffiche uguali di 14 righe
>   ricorrono nei giorni precedenti, quindi è preesistente. È lo stesso meccanismo che in `risk-lab` tiene
>   `holdLivePricePoll`. Segnalato a Risk.

### Giro 7 committato e fuso ✅ 2026-10-05, 12:27

> - Commit del developer: `4a2a37401` (G1), `7c15e1f86` (G2), `6f1a30b2e` (G3), `04af0af05` (G4), albero
>   `1bc6427c6`. Fusione `19b99e8ae`, genitori `04af0af05` + `bb513bf8a` (la punta di Risk, con F3 `c42bbad9e` e
>   `dev_release2`), albero `aaa7a9cc0`.
> - `/tmp/libreFolio_f4/verify_l7.sh` (in sola lettura) dà **PASS**:
>   - 4 commit senza fusioni; messaggi, file e blob uguali al registro (digest `d3fb3c23…`);
>   - nella fusione, i 5 file toccati da entrambi (i18n ×4, `risk-lab.spec.ts`) sono senza marcatori;
>   - gli altri 11 sono i miei blob; nessuna voce non fusa.
> - Cancelli sulla revisione combinata (`/tmp/libreFolio_f4/merge_19b9_gates.sh`, 6154, un comando per volta,
>   12:28-12:37):
>   - `front build --debug` e `mkdocs build` completi;
>   - `front check` **0 errori e 0 avvisi**: la soglia di prima è sparita con `dev_release2`;
>   - `tsc -p tsconfig.e2e.json`: **2 errori**, in `onboarding-tour.spec.ts` e `src/lib/types/files.ts`, nuova
>     soglia; 0 negli spec di rischio;
>   - prettier dei file del laboratorio pulito; vitest **1236/1236** (28 file);
>   - `core-unit` **2984/2984**, `component-unit` **2461/2461** (100 file), `risk-controller-unit` **59/59**,
>     `risk-levels-component` **92/92**;
>   - E2E: `risk-lab` **40/40**, `risk` **14/14**, `risk-benchmark-shared` **4/4**;
>   - `services risk-asset-set` **30/30**; `check-orphans` pulito; i18n 3516 chiavi, 382 inutilizzate;
>   - provider: 0 righe durante `risk-lab` e `risk-benchmark-shared`, **14 durante `risk`** (il reperto già
>     segnalato, non mio);
>   - albero pulito prima e dopo; `sw.js` invariato; 6154 libera.
> - 🔴 **`mkdocs check-links`: exit 1, ereditato, non mio.**
>   - L'ancora `user/assets/detail/chart/#rolling-return` esiste in inglese ma non in it/fr/es. È linkata da
>     `assets/[id]/+page.svelte:3006`.
>   - Arriva da `dev_release2` (`c8daff33f`, commit `e3af27ff3` «add rolling-return guide link»), quindi è rossa
>     anche sulla punta di Risk.
>   - I conteggi: 88 validi, 8 non verificabili, 3 ancore note, **1 rotta**. Segnalato al coordinatore.
> - Risposta del coordinatore: il rosso di `check-links` è **D28**, accettato. Si chiude con le traduzioni a fine
>   giro, e su `dev` dà solo un banner giallo. Il poll durante `risk` è di A (`holdLivePricePoll` nel suo spec).
>   Nessuna azione mia.

### L8-1 · i rossi di A rimessi nell'albero ✅ 2026-10-05, 12:4x

> - Copia privata verificata prima di usarla (sha256 `42a7311d…`, `4223f6d5…`, `105e590c…`).
> - I due unitari: HEAD ha gli stessi blob di `a8c1d8d77` (`c6c51c289`, `3dad861a4`), perché né il giro 7 né la
>   fusione li hanno toccati. Copiati così come sono; `cmp` con la copia dà uguale.
> - Lo spec: `git merge-file`, con base = lo spec del giro 7 committato (`04af0af05`), nostro = lo spec fuso
>   (`19b99e8ae`, con F3), loro = la copia. **0 conflitti**, e il delta è la somma esatta dei due: nostro +92 −28,
>   loro +183 −19, fuso +275 −47. Dentro ci sono sia `expectReplayLeftOutWithoutWeight` (F3) sia `labNoticeFor` (A).
> - Sul codice fuso i rossi sono gli stessi di prima: **16 falliti e 46 passati**, ciascuno sul comportamento che
>   manca (`qualitySource` assente ×8; un parziale o un motivo ancora nella cornice ×8).
> - `tsc e2e` alla soglia nuova (2), 0 in `risk-lab`; prettier pulito. Log in
>   `/tmp/libreFolio_f4/l8_A_red_restored.log`.

### L8-2 · il codice di A · 2026-10-05, 12:5x

> - `assetSetLevels.ts`: il tipo `AssetSetQualitySource` (`results`, `labels`, `issues`).
> - `AssetSetComparisonLevels.svelte`:
>   - cornici con `levelErrorHealth(degradedResults(...))`, senza `reasons`;
>   - `export function qualitySource()`: i sei risultati nell'ordine della pagina, le etichette dei due VaR, le
>     questioni di L1° poi di L3°;
>   - docblock aggiornato.
> - `AssetSetCorrelationSection.svelte`: la stessa cosa per la correlazione; docblock aggiornato.
> - `AssetSetRiskPanel.svelte`:
>   - `bind:this` sulle due sezioni;
>   - `notice = partialNotice(risultati, $t, etichette)`;
>   - `RiskPartialNotice` all'inizio del blocco `{#if analysedIds.length > 0}`, dopo la scheda della selezione e
>     prima della correlazione;
>   - il replay non partecipa: tiene la sua salute.
> - Esiti:
>   - i due unitari **62/62** (erano 16 rossi);
>   - prettier pulito;
>   - `front check` **0 errori, 0 avvisi**.
> - Dopo il codice, build e poi E2E `risk-lab` nella 6154: **40/40**, 0 righe dei provider. Log in
>   `/tmp/libreFolio_f4/l8A/`.
> - **Mutante E2E** (il rosso di (c) non era mai stato osservato: test-author non esegue Playwright):
>   - tolta la riga `<RiskPartialNotice …/>` dal pannello (copia privata, `diff` di una riga);
>   - build, poi solo (c) (`"with the reason in the lab"`, che il runner passa a `--grep`): **rosso** a `:4280`,
>     «its one notice is missing»;
>   - pannello rimesso, `cmp` uguale.
> - **⚠️ Fuori pista 1: la guardia `warningTranslatorSites.test.ts` è diventata rossa.** È mia (K8, `2e2894742`).
>   Fissa l'inventario delle chiamate a `resultReasons` e `partialNotice`, e A le ha spostate apposta: via dalle
>   due sezioni, una `partialNotice` nuova nel pannello.
>   - Riallineata da test-author (`l8-guard`): via le due voci `resultReasons`, più
>     `AssetSetRiskPanel.svelte · partialNotice`. 5/5.
>   - Mutante: nel pannello `$t` → `undefined` nella chiamata a `partialNotice`. La guardia diventa rossa e nomina
>     `AssetSetRiskPanel.svelte:589`; pannello rimesso, `cmp` uguale.
>   - Il secondo test della guardia (ogni chiamata passa `$t`) era verde anche prima.
> - **⚠️ Fuori pista 2: la cornice della correlazione non diceva mai perché mancava** (lo ha trovato docs-writer).
>   L1°, L3° e il replay passano `resultErrorCodes(...)`; la correlazione solo `answer_discarded`. Preesistente, ma
>   la regola di A («ogni cornice dice che cosa manca del tutto, e perché») lo rende un buco:
>   - rossi da test-author (`l8-corr-why`): 3 rossi (`insufficient_history`, `execution_timeout`, e il caso
>     combinato con `answer_discarded` dopo) e 2 guardie verdi;
>   - codice: `errorCodes = [...resultErrorCodes([result]), ...scartata]`;
>   - correlazione, livelli e guardia: **71/71**.
>
> ### L8-1b · la guida ✅ 2026-10-05 (docs-writer `l8-whatif`)
>
> - §What If…? (`:141-153`):
>   - il blocco del replay elenca gli asset lasciati fuori, raggruppati per motivo, sotto le barre;
>   - la sezione tiene solo lo stato;
>   - «Nothing to replay» quando non resta nulla;
>   - i cinque motivi con le etichette del blocco;
>   - il periodo comune con il pulsante e «Only part of the crisis»;
>   - i link alle tre ancore nuove di `historical-replay`.
> - Allineamento ad A:
>   - §Each Section Speaks for Itself diventa «What Is Missing, What Is Partial», con l'ancora invariata;
>   - `:169` e `:178` (§One Shared Window) rimandano alla nota.
> - `mkdocs build` pulito; `check-links` 88/8/3 + D28; `sw.js` invariato.

### L8-4a · i cancelli del giro 8a ✅ 2026-10-05, 13:09-13:16

> `/tmp/libreFolio_f4/l8A_gates.sh`, nella 6154, un comando per volta, su `19b99e8ae` più l'albero (10 file):
> - `front build --debug` e `mkdocs build` completi; `front check` **0/0**; `tsc e2e` 2 (soglia), 0 negli spec di
>   rischio;
> - prettier pulito; vitest **1281/1281** (30 file, più `partialNotice` e `RiskPartialNotice`);
> - `core-unit` **2984/2984**, `component-unit` **2483/2483** (i +22 sono i test nuovi), `risk-controller-unit`
>   **59/59**, `risk-levels-component` **92/92**;
> - E2E: `risk-lab` **40/40**, `risk` **14/14**, `risk-benchmark-shared` **4/4**;
> - `services risk-asset-set` **30/30**; `check-orphans` pulito; i18n 3516/382 (nessuna chiave nuova);
> - `check-links` 88/8/3 più la sola D28;
> - provider: 0 durante `risk-lab` e `risk-benchmark-shared`, 14 durante `risk` (di A);
> - `git diff --check` pulito; `sw.js` invariato; 6154 libera.
> - Log in `/tmp/libreFolio_f4/l8Afinal/`.
>
> **Checkpoint del giro 8a** a Risk, poi FROZEN fino al commit e alla fusione della sua punta (D15 e
> `mergeQualityIssues`). Poi B su `mergeQualityIssues`, e la tappa 1 del pannello.

### Giro 8a committato, e la fusione della punta di Risk (k1 + k2) ✅ 2026-10-05, 14:4x-15:01

> - Commit del developer: `64394ad1f` (G1), `132be8e58` (G2), `cd2e87801` (G3), `47069cff1` (G4), albero
>   `ac09380a9`. Verifica mia in sola lettura: messaggi, file e blob uguali al registro (digest `6fabb88a…`).
> - La fusione `--no-commit` di `2e2d21e76`: k1 `1ac534552` (D15 di I, `mergeQualityIssues`) più k2 (D373, le
>   `issues` del backend per gli insiemi di asset). Base `bb513bf8a`.
> - **⚠️ Fuori pista: un conflitto vero** in `riskPanelController.test.ts`, mentre la previsione di Risk diceva
>   «0 conflitti» (la sua shell leggeva `$?` dopo una sostituzione `$(basename …)`, che lo azzerava). Ci hanno
>   aggiunto righe sia il mio giro 6a sia k1, in due punti:
>   1. la lista degli import;
>   2. un blocco `describe` in coda.
> - **Risoluzione** (mia, con la sola `git add` di quel file, come autorizzato dal coordinatore):
>   - preparata prima che la fusione si aprisse, su una copia privata;
>   - i tre stadi della fusione vera erano identici byte per byte alla simulazione;
>   - un solo import con gli 11 nomi, più le due righe in più di Risk;
>   - i due blocchi interi, prima quello di Risk e poi il mio (l'ordine che Risk ha proposto), nessuna asserzione
>     cambiata;
>   - verifica a tre vie sulla base: base più le modifiche dei due lati, niente in meno e niente in più.
> - **⚠️ Fuori pista: la larghezza.** L'import unito è lungo 315 caratteri, oltre il `printWidth` 300, che nessuno dei
>   due lati da solo superava. La prima corsa dei cancelli lo ha preso (prettier exit 1). Prettier lo scrive un nome
>   per riga: stessa istruzione, stessi nomi, stesso ordine. Ripreparato, rimesso in stage e ricontrollato.
> - Fusioni automatiche riviste:
>   - `riskPanelController.svelte.ts`: ha sia le mie opzioni per livello sia `mergeQualityIssues` di Risk, ed è
>     uguale al `merge-file` pulito dei due lati;
>   - i18n: k2 aggiunge 4 chiavi; JSON validi; le mie chiavi intatte.
> - Cancelli sulla fusione aperta (`/tmp/libreFolio_f4/merge_2e2d_gates.sh`, 6154, un comando per volta,
>   14:49-14:57):
>   - build OK; `front check` 0/0; `tsc e2e` 2 (soglia);
>   - vitest 1304/1304; `risk-controller-unit` **82/82** (54 di base, 23 di Risk, 5 miei);
>   - `core-unit` 2984/2984; `component-unit` 2483/2483; `risk-levels-component` 92/92; `allocation-unit` 214/214;
>   - `risk-lab` 40/40, `risk` 14/14, `risk-benchmark-shared` 4/4;
>   - `services risk-asset-set` 44/44 (+14 di k2); orfani puliti; i18n 3520/382; link 88/8/3 + D28.
> - «RESOLVED» al coordinatore con l'albero in stage `e2a600295`. Il developer ha committato la fusione
>   `89fb5c9b9` (genitori `47069cff1` + `2e2d21e76`, albero `e2a600295`); verificato, albero pulito.

## Giro 8b · B: il banner della qualità dei dati sopra la nota · 2026-10-05

**Decisione** (il developer, 05/10): «B — A più il banner con «Sincronizza»». Il backend ora c'è (k2, D373): per un
insieme di asset `data_quality.issues` arriva una per categoria, `code + group_key` unico in una risposta:

| codice | gruppo | azione | chiave |
|---|---|---|---|
| `STALE_PRICE` (warning) | `stale_price` | `sync_asset_prices` | `dataQuality.stalePrice` |
| `MISSING_PRICE` (error) | `missing_price` | `navigate_asset` (un link per asset) | `risk.quality.missingPrice` |
| `MISSING_FX_MARKET` | `missing_fx` | `add_fx_pair` | `risk.quality.missingFx` |
| `MISSING_FX_RATES` | `missing_fx_rates` | `sync_fx_pair` | `risk.quality.missingFxRates` |
| `MISSING_FX_RATES` | `missing_fx_rates_manual` | `navigate_fx` | `risk.quality.missingFxRatesManual` |

**Disegno**:
- `AssetSetReplaySection` esporta anche lui `qualitySource()`: `results` vuoti, perché la sua cornice tiene la sua
  salute e la nota non lo legge, e le `issues` del suo controller. Il doc del tipo dice che `results` è ciò che la
  nota legge.
- Il pannello legge le tre sezioni con `bind:this`. Ne deriva:
  - la nota, come in A;
  - `mergeQualityIssues(issues di correlazione, L1°, L3°, replay)`: la funzione di Risk, l'unica regola. Non ne
    scrivo una mia.
- `DataQualityBanner` (`grouped`) sopra la nota, come in Dashboard: prima il banner, poi la nota, dopo la scheda
  della selezione e prima della correlazione. Senza questioni non si vede.
- Azioni, mappate da un aiutante puro mio in `syncTargets.ts`, `labQualityAction(action, target)`:
  - `sync_*` → `openSync()`, il modale del laboratorio, limitato alla selezione (prezzi e cambi);
  - `navigate_asset` → `/assets/<id>`;
  - `navigate_fx` → `/fx/<slug>`;
  - `add_fx_pair` → `/fx`;
  - un'azione sconosciuta non fa nulla.
- Niente euro: le questioni portano conteggi, nomi e coppie, mai importi.
- Guida: il banner sopra la nota, con «Sincronizza» e i link.

| # | passo | stato |
|---|---|---|
| L8b-1 | rossi (test-author): `labQualityAction`; `qualitySource()` del replay; E2E del banner (unione fra sezioni, posizione, «Sincronizza» → il modale del laboratorio, link all'asset; nessun banner sull'onda completa) | ✅ 2026-10-05 |
| L8b-2 | codice | ✅ 2026-10-05 |
| L8b-3 | mutanti, guida, cancelli, checkpoint | ✅ 2026-10-05 |

### L8b-1 · i rossi (test-author `l8b-banner`) · L8b-2 · il codice ✅ 2026-10-05

> - **Rossi, osservati**:
>   - unitari 8 (6 per `labQualityAction` che non esiste, 2 per il `qualitySource()` del replay che manca);
>   - E2E: il caso nuovo (e) rosso a `:4660`, «the sections hold data-quality issues and the lab draws no banner».
> - Lo stub di test-author:
>   - pianta le questioni per sezione (`labQualityIssues`): `STALE_PRICE` [A, B] sulla correlazione e [B, C] su
>     L3°, `MISSING_PRICE` [A] su L1° e [C] su L3°, `MISSING_FX_MARKET` solo sulla risposta del replay;
>   - il replay si esegue nel test;
>   - la richiesta `[correlation]` è condivisa fra la sezione della correlazione e l'onda di base del replay.
> - **Codice**:
>   - `syncTargets.ts`: `labQualityAction(action, target)`;
>   - `AssetSetReplaySection.svelte`: `qualitySource()` → `{results: [], labels: {}, issues}`;
>   - `assetSetLevels.ts`: il doc di `results` (che cosa legge la nota);
>   - `AssetSetRiskPanel.svelte`: `bind:this` anche sul replay;
>     `qualityIssues = mergeQualityIssues(issues delle quattro fonti)`, la funzione di Risk;
>     `DataQualityBanner` (`grouped`) prima della nota;
>     `handleQualityAction` → `openSync()` o `goto(href)`.
> - Esiti:
>   - unitari dei 5 file **99/99**; `front check` **0/0**; prettier pulito;
>   - build, poi `risk-lab` **41/41** (i 40 di prima più (e)), 0 righe dei provider.
> - **Mutanti**, uno per volta, ciascuno con build e il solo (e), pannello rimesso e `cmp` uguale dopo ognuno:
>   1. il replay fuori dalle fonti → rosso a `:4678`, «…the panel does not read the replay section»;
>   2. le questioni concatenate senza `mergeQualityIssues` → rosso a `:4667`, «…must be one item».
>   - **⚠️ Fuori pista**: il primo tentativo del mutante 2 era sintatticamente invalido (`$derived` con due argomenti).
>     Il build è fallito e il runner non ha avviato il backend: nessun test è girato, quindi non prova nulla.
>     Rifatto valido (2b).
>   - Il banner tolto non serve come mutante: è lo stato di prima del codice, già osservato rosso.
> - **Decisione del developer (via coordinatore)**: Risk si allinea alla mia punta `89fb5c9b9` e il suo test-author
>   riallinea 8 miei test al nuovo limite (3 tentativi): 6 dei livelli, 1 della correlazione, 1 del replay.
>   - Fino alla fusione del suo checkpoint non tocco `AssetSetComparisonLevels.test.ts` né
>     `AssetSetCorrelationSection.test.ts`.
>   - In `AssetSetReplaySection.test.ts` tengo le mie modifiche; un'eventuale sovrapposizione la risolvo io alla
>     fusione.
>   - Il commento di `risk-lab.spec.ts:6354` («re-asked once») lo correggo **dopo** quella fusione: prima sarebbe
>     falso il contrario.

### L8b-3 · la guida, i cancelli, un reperto ✅ 2026-10-05, 15:5x-16:02

> - Guida (docs-writer, `correlation.en.md`):
>   - un paragrafo nuovo, `:205`, in §What Is Missing, What Is Partial: il banner sopra la nota, piegato, che copre
>     le quattro sezioni compresa What if…?. «Sync prices» e «Sync rates» aprono la stessa sincronizzazione di
>     «Sync selection» nella barra; gli altri sono link alle pagine degli asset o dei cambi. Il banner offre il
>     rimedio, la nota dice che cosa è successo alle cifre;
>   - `:169` corretta: non è più detto «una volta» nella scheda, perché ora lo dicono sia il banner sia la nota.
> - Lasciati, da segnalare:
>   - una sincronizzazione cancella anche il replay finito (`:155` nomina solo selezione e date; non è falso);
>   - `user/assets/index.en.md:37` descrive la sincronizzazione della barra solo per la scheda Assets. Non è mia.
> - Cancelli (`/tmp/libreFolio_f4/l8B_gates.sh`, 6154, un comando per volta, 15:54-16:02):
>   - build e `mkdocs build` completi; `front check` **0/0**; `tsc e2e` 2 (soglia), 0 negli spec di rischio;
>   - prettier pulito; vitest **1312/1312**;
>   - `core-unit` **2990/2990** (+6) e `component-unit` **2485/2485** (+2);
>   - `risk-controller-unit` **82/82**; `risk-levels-component` **92/92**;
>   - E2E: `risk-lab` **41/41**, `risk` **14/14**, `risk-benchmark-shared` **4/4**;
>   - `services risk-asset-set` **44/44**; orfani puliti; i18n 3520/382; link 88/8/3 + D28;
>   - `git diff --check` pulito; `sw.js` invariato; 6154 libera.
> - **Reperto, non mio: `risk-benchmark-shared` arriva a Yahoo.**
>   - Durante la sua corsa, alle 14:01:25Z, `yahoo_finance | current_value for MSFT` e 4 volte «Intra-day price
>     extend» sull'asset 2, nel DB della mia lane.
>   - Le corse dello stesso spec di stamattina (10:36Z, 11:15Z, 12:56Z) non hanno scritto nulla: erano prima
>     dell'apertura del mercato USA (13:30Z). Dipende dall'orario.
>   - Lo spec è di Risk (`07f6bb01d`) e non trattiene il poll dei prezzi live.
>   - Il mio `risk-lab`, che ha girato dopo le 13:30Z: **0** righe, `current_value` compreso.
>   - Il mio filtro dei provider non conteneva `current_value for` (le chiamate a Yahoo); da qui in poi lo
>     comprende.

### Giro 8b committato ✅ 2026-10-05, 16:15

> - `c20ae9382` (G1), `457a7a4ab` (G2), `84d12b814` (G3), `8cb564ace` (G4), albero `44637ca2c`.
> - Verifica in sola lettura: messaggi, file e blob uguali al registro (digest `f9295233…`).
> - Risk ha fatto il fast-forward allo stesso commit. Il suo test-author riallinea al limite di 3 tentativi tre miei
>   file di test. **Non li tocco fino alla fusione del suo checkpoint**:
>   - `AssetSetComparisonLevels.test.ts`;
>   - `AssetSetCorrelationSection.test.ts`;
>   - `AssetSetReplaySection.test.ts`.
> - Dopo quella fusione: il commento di `risk-lab.spec.ts:6354` («re-asked once»).

## Giro 9 · la guida della barra e la tappa 1 del pannello · 2026-10-05

| # | passo | stato |
|---|---|---|
| L9-1 | guida: `user/assets/index.en.md:37` (compito dal coordinatore via Risk). Nella scheda Correlation la sincronizzazione della barra è «Sync selection», per prezzi e cambi. Solo EN, via docs-writer | ✅ 2026-10-05, più `:33-35` e `correlation.en.md:50` |
| L9-2 | tappa 1: analisi del pannello riusabile in `ui/select/` (scelta singola e multipla, estratto da `LabAssetPicker`); contratto con Risk, che lo adotta nella tappa 2 | ✅ 2026-10-05 (D-a, D-b, D-c) |
| L9-3 | tappa 1: rossi, codice (file nuovi più una riga in `component-unit`, poi `check-orphans`), laboratorio identico | ✅ 2026-10-05 codice, mutanti e guida; cancelli sotto |
| L9-4 | cancelli prima e dopo il fast-forward a k3 (`bb8d68ad2`), poi il checkpoint | ✅ 2026-10-05, 18:05 |

### L9-2 · tappa 1: analisi del pannello riusabile (verificata su `8cb564ace`)

**Stato reale**:
- `LabAssetPicker.svelte` (317 righe, mio) è il «+» del laboratorio, a scelta multipla:
  - ricerca, e i filtri di tipo e valuta (`LabCheckMenu`) con i conteggi di ciò che si può ancora aggiungere;
  - righe con icona, nome che scorre, tipo e valuta, e ⚠ per gli avvisi;
  - una sezione in sola lettura per i non ammissibili, con i motivi;
  - «seleziona visibili», il limite `room`, Annulla e «Aggiungi N», Invio che conferma.
- Le sue primitive sono mie e del solo laboratorio:
  - `LabPopover` (90 righe; lo usa anche il menu del preset broker del pannello);
  - `LabCheckMenu` (95);
  - gli aiutanti di `assetSetSelection.ts` (`applyFilters`, `pickerRows`, `toggleVisibleRows`,
    `visibleRowsAllChecked`) e `nameOrder` di `correlationHelpers.ts`;
  - `EligibilityView` (`{level, codes, texts}`), già generico.
  - Nessun test unitario per i tre componenti: li copre `risk-lab`, con 21 usi dei loro testid, tutti nel mio spec.
- I consumatori delle tappe 2 e 3 usano `AssetSelect` allo stesso modo (`BenchmarkSelect` e
  `SignalAssetParamControl`): `value`, `filter`, una sezione «Benchmark» in testa, `compact`,
  `dropdownPosition="auto"`, `dropdownMinWidth=280`, `placeholder`, `testid`, `onchange`. Cerca per ISIN, ticker e
  altri codici, non per valuta o tipo (P3/A6). Oggi nessun comando riporta la scelta a «nessuno»: `SearchSelect`
  azzera solo la ricerca.
- In `ui/` non c'è un popover generico: un pannello in `ui/select/` non può importare da `risk/`.

**Proposta** (file nuovi in `ui/select/`):
1. `AssetPickerPanel.svelte`, con `mode: 'single' | 'multi'`:
   - in comune:
     - `assets` passati dal chiamante; `searchText`, per difetto gli identificativi come `AssetSelect` (il
       laboratorio passa il suo: nome, valuta, tipo);
     - `verdicts` e `blockedLabel` (la sezione in sola lettura); `sections` e `restLabel`; i filtri;
     - lo snippet `trigger` (il «+» del laboratorio). Per difetto, in `single`, una casella con l'asset scelto e
       la freccia;
     - `testId` come prefisso unico di tutti i testid;
     - nessun importo;
   - `multi`: `selected`, `room`, `onadd`;
   - `single`: `value`, `onchange`; un clic sceglie e chiude; la scelta corrente è marcata.
2. `SelectPopover.svelte` e `CheckMenu.svelte`: `LabPopover` e `LabCheckMenu` spostati così come sono e resi
   generici. `LabPopover` porta il comportamento delicato del clic (F-6).
3. `assetPicker.ts`: i quattro aiutanti, `SelectionFilters` e `nameOrder`, spostati. I miei moduli li importano da lì.
4. `AssetPickerPanel.test.ts` (jsdom): i due modi e gli aiutanti, con i test spostati da
   `assetSetSelection.test.ts`. Una riga in `component-unit`.

**I miei file**:
- `LabAssetPicker` diventa un involucro sottile: `multi`, `testId="risk-asset-add"`, il suo «+», le etichette del
  laboratorio;
- il pannello usa `SelectPopover`;
- `LabPopover` e `LabCheckMenu` si tolgono;
- in `risk-lab.spec.ts` cambiano solo i 7 usi dei testid dei filtri, al prefisso (`risk-filter-type` →
  `risk-asset-add-filter-type`, …);
- i18n: chiavi generiche `assetPicker.*` × 4 con il testo di oggi; quelle del laboratorio che sostituiscono si
  tolgono.

**Decisioni**:
- **D-a** (developer): il comportamento della scelta singola, con un mock-up;
- **D-b** (coordinatore): la concessione parlava del pannello e del suo test. Qui i file nuovi in `ui/select/` sono
  quattro, più il test, e la riga del runner resta una;
- **D-c** (Risk): il contratto delle tappe 2 e 3.

**Conflitti**:
- `ui/select/` ha solo file nuovi; `AssetSelect` e `index.ts` non si toccano;
- i18n: aggiunte, più la rimozione di chiavi mie;
- i tre test che Risk riallinea non sono fra i miei file di questa tappa.

**Decisioni (2026-10-05)**:
- **D-a, il developer** (ask_user, col mock-up della scelta singola nel selettore «Confrontato con»), testuale: «Così:
  un clic sceglie e chiude, stessi filtri e sezioni del «+» (Consigliata)». Quindi: ✓ sulla scelta corrente,
  «Benchmark» in testa, i non analizzabili in sola lettura, nessuna riga «nessuno».
- **D-b, il coordinatore**: sì, dentro la concessione, con questi limiti:
  - in `ui/select/` solo i 5 file nuovi (`AssetPickerPanel.svelte`, `SelectPopover.svelte`, `CheckMenu.svelte`,
    `assetPicker.ts`, `AssetPickerPanel.test.ts`). I file esistenti non si toccano: `index.ts`, e
    `AssetSelect.svelte`, che ora Risk modifica con una sua concessione;
  - nessun doppione: in `ui/` non c'è un popover né un menu a spunte. **Omonimia**: `ui/media/AssetPickerModal.svelte`
    sceglie un file d'immagine, quindi l'intestazione di `AssetPickerPanel` dice che sceglie asset del portafoglio;
  - una sola riga nel runner;
  - i18n solo via `dev.py i18n`. Prima di togliere le chiavi del laboratorio, cercarle nel sorgente; nella
    consegna, l'elenco delle chiavi aggiunte e tolte (L, D e Risk toccano i cataloghi in altri namespace);
  - dopo la tappa 1 i file nuovi diventano condivisi: quando la tappa 2 di Risk li usa, ogni modifica passa dal
    coordinatore;
  - guida: `:33-36` nello stesso giro, solo EN, senza timbro.
- **D-c, Risk**: in attesa (il contratto: `assets` passati dal chiamante o un involucro sul negozio; il periodo per
  i verdetti; i testid col prefisso).

### L9-1 · la guida della barra (docs-writer) · 2026-10-05

> - `user/assets/index.en.md:37`: la sincronizzazione e il ricaricamento valgono così sulla scheda **Assets**. Sulla
>   scheda **Correlation** gli stessi due pulsanti agiscono sulla selezione: **Sync selection** (prezzi e cambi che
>   li convertono) e **Reload All** (ogni analisi della selezione). Link alla pagina del laboratorio.
> - **Nessun timbro**: la pagina aveva già un debito di traduzione (IT/FR/ES non sincronizzate dal 04/09; manca loro
>   tutto il punto Abs/%). Timbrare l'avrebbe nascosto, quindi il debito resta in coda. Il coordinatore è d'accordo.
> - **⚠️ Fuori pista**: `:33-35` era falso (Abs/% «you can switch it from the **Correlation** tab too»). L'hanno
>   scritto il commit della pagina (`e2327e9a3`) e il mio F-3b (`abcf21860`), lo stesso giorno su rami paralleli, e
>   la fusione l'ha reso falso. Riscritto:
>   - il comando c'è solo sulla scheda Assets, in griglia;
>   - l'impostazione è della pagina e sopravvive al passaggio dalla scheda Correlation;
>   - la scelta di una singola carta no;
>   - non si salva.
>   Solo EN, senza timbro.
> - **⚠️ Fuori pista**: lo stesso conflitto fra rami nella mia pagina, la nota `correlation.en.md:48-50` (la ricerca e
>   i filtri della barra «stay visible on this tab»). Da F-3b sono nascosti; la correzione è in corso.
> - Controlli: `mkdocs build` strict pulito; `check-links` 88/8/3 + D28; `sw.js` invariato.
- **D-c, Risk** (2026-10-05, 16:24): sì, con queste modifiche.
  - `assets` passati dal chiamante; i wrapper con il negozio sono `BenchmarkSelect` e
    `SignalAssetParamControl`. In più `loading?` e `disabled?`.
  - **`single` è un sostituto diretto dei testid di `SearchSelect`**: la radice `{testId}`, `{testId}-trigger`,
    `{testId}-search`, le opzioni `search-select-option-{id}` dentro la radice (niente portal). Li usano 4 spec
    con 3 proprietari, uno fuori dalla famiglia (`asset-detail`).
  - I miei suffissi in più e `data-level` / `data-reasons` / `aria-selected` vanno bene; `multi` tiene il mio schema.
  - Il trigger di difetto in `single` è uguale alla voce compatta che Risk porta in k3 (`AssetSelect`): una riga,
    icona `w-4 h-4`, `ticker · name` come nella riga dell'elenco, il badge «inactive». **Stessa altezza con e senza
    valore**, fissata da un test strutturale: è il difetto che il developer ha visto.
  - Tastiera come `SearchSelect`: le frecce saltano le righe bloccate (gli aiutanti di passo di
    `optionFilter.ts`), Invio sceglie, Esc chiude e rende il focus al trigger. Posizione `auto`, larghezza minima
    280, che stia anche sul mobile.
  - **Il valore corrente non sparisce mai**: nel trigger qualunque sia il suo verdetto; nell'elenco segnato come
    corrente, e nella sezione dei bloccati se non è ammissibile.
  - Il tipo del verdetto sta in `assetPicker.ts`: `ui/select` non importa `risk/eligibility.ts`, ed
    `EligibilityView` resta compatibile per struttura.
  - La regola di ricerca: `assetSearchText(asset)` esportata da `assetPicker.ts` e usata per difetto. Nella tappa 2
    Risk la usa in `AssetSelect.svelte:109`, con una concessione, così la regola P3/A6 ha una copia sola.
  - i18n in uno spazio neutro, non `risk.*`, spostato con `dev.py i18n` nelle 4 lingue.
  - Guida per sviluppatori: il pannello in `developer/frontend/components/core-ui/select.md` (EN, docs-writer).
  - I verdetti della tappa 2 si decidono nella sua analisi.
> - `correlation.en.md:50` (la nota «The toolbar filters belong to the Assets tab»): riscritta, non tolta. Dice dove
>   sono finiti la ricerca e i filtri della barra in questa scheda (nascosti: il laboratorio lavora sull'elenco
>   intero, con la ricerca e i filtri del suo «+») e che cosa la barra tiene (le date, Sync selection, Reload All).
>   È l'unico punto della pagina che nomina Reload All.
> - Tutto solo EN; `mkdocs build` pulito; `check-links` 88/8/3 + D28; `sw.js` invariato.

### L9-2 · il contratto finale della tappa 1 (D-a, D-b, D-c) e i rossi

> - L'ordine resta quello del chiamante: il laboratorio ordina con il suo `nameOrder`, che resta dov'è.
>   `assetSelectOrder` (prima gli attivi, poi il nome) si esporta da `assetPicker.ts` per la tappa 2 (proposto a
>   Risk). Gli aiutanti che si spostano sono i quattro del «+» più `SelectionFilters`, usati oggi solo da
>   `LabAssetPicker`.
> - Il trigger di `single` copierà la voce compatta di k3 quando Risk ne manda il markup. Intanto i rossi fissano
>   solo l'invariante: la stessa classe d'altezza con e senza valore, e una riga.
> - Risk (16:4x) ha mandato il markup della voce compatta di k3, che confermerà col blob:
>   - la scatola è quella compatta di `SearchSelect` (`w-full flex items-center justify-between gap-2 px-3 py-2
>     text-sm border rounded-lg`); il segnaposto è `<span class="text-gray-400">`;
>   - la riga: un'icona `w-4 h-4 rounded-sm object-contain shrink-0`, poi un solo span `truncate text-sm` con
>     `ticker · nome`, poi il badge `asset-select-selected-inactive-badge`;
>   - niente valuta e niente seconda riga: 38 px con e senza valore.
>   Ha confermato anche `assetSelectOrder`: una copia esatta di `AssetSelect.svelte:98-101`, `localeCompare` senza
>   locale compreso. Passato a test-author (`l9-picker`) mentre scrive i rossi.

### ⚠️ Fuori pista: i dati del developer nei miei journal (regola di privacy, 2026-10-05)

> **Regola** (dal coordinatore, via Risk; il repo è pubblico): in un journal non resta nessun nome, importo,
> percentuale o conteggio che venga dai dati del developer. Risk ne ha segnalate due righe; la scansione dei miei tre
> journal non ancora in `dev_release2` ne ha trovate altre.
> - Tolti, per categoria (senza ripeterli qui):
>   - il nome di un'obbligazione e gli emittenti dei suoi asset;
>   - l'impronta del DB della copia (7 punti), e lunghezza e impronta del testo del pannello;
>   - i conteggi: asset, nomi con emoji, asset senza prezzi, «N selezionati su N», asset dentro due citazioni;
>   - le osservazioni e le coperture misurate sulla copia, e le percentuali di C3 sui suoi dati;
>   - un suo asset nominato in una citazione, e un tipo di asset che ne rivelava la composizione.
> - Restano il metodo, i casi limite, gli id degli asset della copia, le impronte delle build e i conteggi dei test.
>   Le citazioni corrette lo segnano fra parentesi quadre.
> - **Terza passata** (18:1x, rilanciando la scansione prima del checkpoint; `l9_privacy_fix3.py`, 3 sostituzioni
>   esatte): un id da solo resta, ma tre righe di `F-laboratorio-postmerge.md` legavano degli id a un fatto dei suoi
>   dati (quali asset non hanno prezzi, e quali hanno avuto la riga dello scheduler). L'intervallo di id diceva anche
>   quanti erano. Gli id sono tolti e segnati «[id tolti]»; il metodo e il caso limite restano.
> - Strumenti: `/tmp/libreFolio_f4/l9_privacy_scan.py` e due passate di sostituzioni esatte, ciascuna verificata
>   (`l9_privacy_fix.py`, 30; `l9_privacy_fix2.py`, 7). La scansione finale non trova nulla.
> - `implementation/progress/F-esecuzione.md` (già in `dev_release2`): scansionato, pulito.
> - Se riscrivere la storia lo decide il developer, tramite il coordinatore.
> - **Decisione del developer sulla storia** (via Risk): «Sì, basta toglierli dai file». Nessuna riscrittura.
> - **Da fare dopo la fusione di k3 di Risk** (D374, 3 tentativi in tutto, `RISK_DISCARD_ATTEMPTS`), solo commenti:
>   - nei `.svelte` (`AssetSetRiskReturnSection`, `AssetSetLossComparisonSection`, `AssetSetCorrelationSection`,
>     `AssetSetReplaySection`, `AssetSetComparisonLevels`): «discarded twice running» → «discarded on every attempt»;
>   - in `AssetSetRiskPanel`: togliere «the policy `loadBase` adopted». Il singolo nuovo tentativo del preset broker
>     resta com'è (il developer: «ho il dubbio che stai overtinkando»);
>   - nei test lasciati a me (`AssetSetComparisonLevels.test.ts` intestazione e titolo,
>     `AssetSetCorrelationSection.test.ts`) e in `risk-lab.spec.ts:6354`. Dopo la fusione cercare `twice running` e
>     `re-asked once`.

### L9-3 · i rossi, il codice, i mutanti e la guida della tappa 1 ✅ 2026-10-05

> **Note implementazione**
> - **Rossi** (test-author `l9-picker`), tutti rossi prima del codice:
>   - `ui/select/AssetPickerPanel.test.ts`, 93 test: i due modi, `dropdownPlacement`, gli aiutanti spostati
>     (21 test tolti da `assetSetSelection.test.ts`, invariati nella sostanza) e il confine (`ui/select` non importa
>     da `components/risk/`, letto dai sorgenti della cartella);
>   - `risk-lab.spec.ts`, 11 righe: i testid dei filtri passano al prefisso del pannello
>     (`risk-asset-add-filter-{type,currency}-*`, `risk-asset-add-filters-clear`);
>   - una riga nel runner: `component-unit` (`_frontend_utility.py:179`).
> - **Codice**: cinque file nuovi in `ui/select/`.
>   - `assetPicker.ts` (160 righe). I tipi `PickerAsset`, `PickerVerdict`, `PickerSection` e `SelectionFilters`.
>     Spostati: `applyFilters`, `foldForSearch`, `pickerRows`, `toggleVisibleRows`, `visibleRowsAllChecked`. Nuovi:
>     - `assetSearchText` (gli identificativi, mai valuta o tipo: P3/A6);
>     - `assetSelectOrder` (copia esatta di `AssetSelect.svelte:98-101`);
>     - `dropdownPlacement`.
>   - `SelectPopover.svelte` (122): `LabPopover` spostato com'è, più `placement` (posizione fissa che segue
>     scroll e resize) e `rootClass`.
>   - `CheckMenu.svelte` (97): `LabCheckMenu` su `SelectPopover`; testid `{testId}-button|-panel|-clear|-{value}`.
>   - `AssetPickerPanel.svelte` (665): i due modi. `single` è il sostituto diretto di `SearchSelect` (testid,
>     ricerca `filterOptions`, tastiera `stepSelectable`); trigger di una riga a `h-[38px]`, con e senza valore.
>   - `AssetPickerPanel.test.ts`: **93/93**.
> - **Laboratorio identico**:
>   - `LabAssetPicker.svelte` da 317 a 84 righe: un involucro (`multi`, `testId="risk-asset-add"`, `nameOrder`,
>     la sua ricerca per nome, valuta e tipo, le sue etichette, il suo «+»);
>   - il menu del preset broker di `AssetSetRiskPanel` usa `SelectPopover`;
>   - `LabPopover.svelte` e `LabCheckMenu.svelte` tolti; gli aiutanti tolti da `assetSetSelection.ts` (−77 righe).
> - **i18n**, 4 lingue, stessi valori di prima (`/tmp/libreFolio_f4/l9_i18n_move.py`, con `dev.py i18n`):
>   - aggiunte 7: `assetPicker.filters.{type,currency,clear}`,
>     `assetPicker.{selectVisible,deselectVisible,confirm,allSelected}`;
>   - tolte 7, dopo la ricerca nel sorgente: `risk.assetSet.filters.{type,currency,clear}`,
>     `risk.assetSet.picker.{selectVisible,deselectVisible,confirm,allSelected}`. Resta
>     `risk.assetSet.picker.notAnalysable`.
>
> **⚠️ Fuori pista**
> - `foldForSearch` è uscito con `pickerRows`, ma il suo blocco di test era rimasto in
>   `assetSetSelection.test.ts`, che falliva all'import. Test-author l'ha spostato (3 test) e ha corretto
>   l'intestazione del test («five helpers»). Ora 96 + 72.
> - Svelte 5: uno `{#snippet trigger}` dentro il componente oscura la prop omonima. La prop si chiama `trigger`
>   fuori e `customTrigger` dentro.
> - prettier ha riformattato `AssetPickerPanel.svelte` in tre punti, solo forma.
> - Un mio commento in `risk-lab.spec.ts:3878` attribuiva a `SelectPopover` un fatto di `LabPopover`; ora li nomina
>   entrambi.
> - L'intestazione di `AssetPickerPanel.svelte` dava `search-select-header-{key}`; il testid vero è
>   `search-select-header-__section:{key}`. Segnalato dal docs-writer, corretto.
>
> **Mutanti** (`/tmp/libreFolio_f4/l9_mutants.py`, ciascuno ripristinato e verificato con sha256):
> - M1, il valore corrente nascosto se bloccato: rosso, 1 (`shows a ruled-out current value…`);
> - M2, `disabled: false` sulle opzioni bloccate: **sopravvive, ed è equivalente**. Le righe bloccate sono `disabled`
>   nel markup, senza `onclick`, e non entrano mai in `listed`: il flag è un metadato vero che nessuno legge. Resta;
> - M2b, righe bloccate senza `disabled` e cliccabili: rosso, 2;
> - M3, l'altezza del trigger che dipende dal valore (`h-9` da vuoto): rosso, 1 (il test strutturale);
> - M4, un import `../../risk/eligibility` in `assetPicker.ts`: rosso, 1 (il confine).
>
> **Guida per sviluppatori** (docs-writer `l9-devdoc`): `developer/frontend/components/core-ui/select.md`, la
> sezione `🧺 AssetPickerPanel`, più quattro punti in testa alla pagina che altrimenti la contraddirebbero (l'intro,
> il nodo del diagramma, il suo stile, la legenda). Nessun timbro: il manuale dello sviluppatore è solo EN
> (`EN_ONLY_SECTIONS`). `mkdocs build` strict pulito; `check-links` 88/8/3 + D28; `sw.js` invariato.
>
> **Reperto per Risk (tappa 3)**: il segnale «Confronto Asset» del grafico sceglie l'asset con un `SearchSelect` in
> `charts/ChartSignalsSection.svelte:~680` (`configuredAssets`). `SignalAssetParamControl` è un'altra cosa: il
> parametro «Comparison asset» dei segnali backend, oggi Rolling Beta. La tappa 3 deve dire quale dei due adotta il
> pannello.
>
> **Prima dei cancelli** (fuori corsia): `front check` 0/0; `tsc e2e` 2 errori (gli altri file, il pavimento);
> prettier pulito; la lista vitest **1384** (1312 − 24 + 96).

### L9-4 · i cancelli, prima e dopo il fast-forward a k3 ✅ 2026-10-05, 17:42-18:05

> **Note implementazione**
> - **Prima** (`/tmp/libreFolio_f4/l9_gates.sh`, su `8cb564ace` più i 23 percorsi): tutto verde. È la stessa lista del
>   giro 8b, con tre differenze:
>   - prettier esclude i file cancellati e vede quelli nuovi;
>   - la lista vitest comprende `AssetPickerPanel.test.ts`;
>   - il conteggio dei provider cerca anche «current_value for».
> - **Fast-forward** (script del coordinatore `/tmp/libreFolio_ff_f_to_rk3.sh`, eseguito dal developer al mio punto di
>   pausa): `8cb564ace` → `bb8d68ad2`, cioè k3 di Risk (D374: tre tentativi per una risposta scartata; la voce
>   compatta di `AssetSelect` su una riga; lo spec del benchmark che trattiene i prezzi live). I 23 percorsi sono
>   intatti: il manifesto sha256 di prima e quello di dopo coincidono. Nulla in stage.
> - **La voce compatta di k3 confrontata col mio trigger**: stesse classi (prettier ne cambia solo l'ordine),
>   icona `w-4 h-4`, `ticker · nome` oppure il solo nome, badge `asset-select-selected-inactive-badge`, regola
>   dell'icona identica. 38 px in entrambi.
> - **Dopo** (`/tmp/libreFolio_f4/l9ff_gates.sh`, su `bb8d68ad2` più i 23 percorsi), uno per volta nella corsia 6154:
>
> | cancello | prima | dopo |
> |---|---|---|
> | `front build --debug`, `mkdocs build` (0 WARNING) | ✅ | ✅ |
> | `front check` | 0/0 | 0/0 |
> | `tsc -p tsconfig.e2e.json` | 2 (gli altri file) | 2 |
> | prettier sui file toccati | pulito | pulito |
> | lista vitest | 1384 | 1401 |
> | `core-unit` | 2966 | 2966 |
> | `component-unit` | 2581 | 2583 |
> | `risk-controller-unit` | 82 | 96 (k3) |
> | `risk-levels-component` | 92 | 92 |
> | `risk-lab` | **41/41** | **41/41** |
> | `risk` · `risk-benchmark-shared` · `services risk-asset-set` | 14 · 4 · 44 | 14 · 4 · 44 |
> | `check-orphans` · `i18n audit` | ok · 3520 chiavi, 382 inutilizzate | uguale |
> | `mkdocs check-links` | 88/8/3 + D28 | uguale |
> | righe di provider: `risk-lab` · `risk` · `bench` | 0 · 27 · 9 | 0 · 27 · **0** |
>
> - `git diff --check` pulito; `sw.js` invariato; porta 6154 libera alla fine.
>
> **⚠️ Fuori pista: le righe di provider negli spec di Risk.**
> - `risk-benchmark-shared`: il mio reperto dell'8b (una chiamata `current_value` a Yahoo, dopo l'apertura di Wall
>   Street) è curato da k3: 9 righe prima, 0 dopo.
> - `risk` (`risk-analysis.spec.ts`): in ogni giro feed live, «Current-price persist» e uno scraping di Borsa Italiana
>   nel DB della corsia: 14 righe nell'8a, 20 nell'8b, 27 ora. Non è il mio spec e questo giro non lo tocca, ma non
>   l'avevo segnalato. Va a Risk nel checkpoint.
>
> **Da A** (rischio dashboard), annuncio sul grafico a dispersione condiviso (`charts/ScatterChart.svelte`, suo):
> - il benchmark diventa un rombo, e nel laboratorio cambiano solo il rombo e il margine. I punti del laboratorio non
>   portano mai `weight` né `detail` (`assetSetLevels.ts:231-238`, `:289-294`), e nessun mio test fissa simbolo,
>   `grid` o i 64 px. OK dato ad A;
> - **concessione ad A**, solo il blocco `assetSetI18n.test.ts:194-233` (il commento e il controllo positivo): lo punta
>   a `risk.levels.l3.scatter.notes.line`, sua, e toglie `risk.levels.l3.scatter.note` nello stesso cambiamento, così
>   nel catalogo non resta una chiave morta. Il coordinatore è informato;
> - **da fare quando il rombo arriva nel mio ramo**: `correlation.en.md:117` dice «its dot» per un benchmark non
>   selezionato.
>
> **Giro 10, prima voce**: l'allineamento dei commenti a k3 (D374), elencato sopra nel fuori pista della privacy. Non
> sta nel giro 9 perché toccherebbe `AssetSetRiskPanel.svelte` e `risk-lab.spec.ts`, che sono già nel gruppo del
> codice, e un percorso non può stare in due gruppi.

### Checkpoint del giro 9 · 2026-10-05, 18:2x (verso Risk)

> - Base: `bb8d68ad2` (k3, dopo il fast-forward). 23 percorsi: 16 modificati, 5 nuovi (tutti in `ui/select/`, compreso
>   il test), 2 cancellati. Quattro gruppi, e ogni commit resta verde da solo:
>   - **G1** il codice della tappa 1, 17 percorsi. Ci stanno anche i rinomini dei testid in `risk-lab.spec.ts`:
>     senza di loro il commit del codice romperebbe `risk-lab`;
>   - **G2** la guida della barra (`index.en.md`, `correlation.en.md`);
>   - **G3** la guida per sviluppatori (`core-ui/select.md`);
>   - **G4** i tre journal, con la correzione di privacy.
> - Strumenti: `/tmp/libreFolio_f4/l9_msgs.py` e `l9_record.sh`. Il record segna i cancellati come `deleted <path>`.
> - **CHANGELOG**: nessuna riga. Il laboratorio è identico e la tappa 1 non cambia niente che si veda; la voce verrà con
>   la tappa 2, quando il selettore del benchmark cambierà.
> - Reperti per Risk: la tappa 3 deve dire quale selettore adotta il pannello; e le righe di provider dello spec `risk`.
> - Stato dopo l'invio: **FROZEN** fino al commit.

### Giro 9 committato ✅ 2026-10-05, 18:3x

> - Commit del developer: `ddbb51512`, `6fc57b3bb`, `f1de4ee63`, `0da41fb11`; `HEAD~4` = `bb8d68ad2`, albero `3f085d28b`,
>   worktree pulito.
> - `/tmp/libreFolio_f4/verify_l9.sh`: **PASS**. 4 commit lineari, messaggi e percorsi per gruppo identici al record, e
>   impronta dei blob `5660cd68…` identica. L'intervallo dà 22 file e non 23 perché git abbina `LabCheckMenu.svelte` →
>   `ui/select/CheckMenu.svelte` come rinomina (81%); con `--no-renames` sono 23.
> - Da qui i 5 file nuovi di `ui/select/` sono condivisi: ogni modifica passa dal coordinatore. La tappa 2
>   (`BenchmarkSelect` sul pannello) è di Risk, che manderà il contratto dopo il suo k4, compreso il punto aperto
>   `verdicts` o `period`.
> - **Correzione al reperto di L9-4** (le righe di provider dello spec `risk`): lo spec è di **A**, non di Risk. A l'ha
>   già curato nel suo checkpoint 4 (`528f6154d`: il poll live e il catalogo dei provider di cambio trattenuti), che
>   arriva nei nostri rami con l'integrazione della famiglia. Niente da fare per me.

## Giro 10 · i commenti allineati a k3 (D374) · 2026-10-05

| # | passo | stato |
|---|---|---|
| L10-1 | solo commenti e un titolo di test: «discarded twice running», «re-asked once» e «the policy `loadBase` adopted» non sono più veri con D374 (tre tentativi in tutto, `RISK_DISCARD_ATTEMPTS`) | ✅ 2026-10-05 |
| L10-2 | cancelli, poi il checkpoint | ✅ 2026-10-05, 18:5x |
| poi | `correlation.en.md:117` («its dot») quando il rombo di A arriva nel ramo; l'adozione della tappa 2 in `AssetSetRiskPanel` dopo il contratto di Risk; la review unica sulla 6164 con una copia nuova (OK del developer) | in attesa |

### L10-1 · analisi (su `0da41fb11`)

> - **Il fatto di k3** (`riskPanelController.svelte.ts:446-455` e `:510-515`): un'onda di base e un'analisi a richiesta
>   si richiedono fino a `RISK_DISCARD_ATTEMPTS` (3) tentativi in tutto. `loadDiscarded` e `discarded[analysis]`
>   scattano solo al terzo scarto.
> - **Cosa ha già riallineato k3** nei miei tre test: i conteggi, i titoli dei `describe` («discarded three times
>   running») e i commenti sul copione. Resta il mio testo che k3 non ha toccato:
>   - produzione, solo commenti: `AssetSetRiskReturnSection.svelte:74` e `AssetSetLossComparisonSection.svelte:71`
>     (la prop `discarded`), `AssetSetCorrelationSection.svelte:99`, `AssetSetReplaySection.svelte:115`,
>     `AssetSetComparisonLevels.svelte:148`, `AssetSetRiskPanel.svelte:193` («`loadBase` asks again only once») e
>     `:490` («the policy `loadBase` adopted»);
>   - test: l'intestazione di `AssetSetCorrelationSection.test.ts:10`, l'intestazione di
>     `AssetSetComparisonLevels.test.ts:13` e `:20`, il titolo del test a `:956`;
>   - E2E: il commento di `risk-lab.spec.ts:6354` («a discarded answer is re-asked once»).
> - **Restano com'è**:
>   - `risk-lab.spec.ts:6176-6191`, il preset broker: il suo singolo nuovo tentativo è suo, e il developer l'ha voluto
>     così;
>   - i «`loadBase` has no emptiness check» in tre file: non c'entrano con D374.
> - **Le parole**: in produzione «discarded on every attempt», col nome della costante dove serve, così un cambio del
>   limite non li rende di nuovo falsi. Nei test «three times running», la parola di k3 negli stessi file: lì il
>   copione scarta proprio tre volte.
> - **Il titolo a `:956`** cambia solo nella parola: nessuna asserzione, conteggio invariato. Il runner lancia i file e
>   non i titoli (verificato sotto).
> - **Fuori dai miei file**: `levels/RiskLevelsPanel.svelte:148` dice ancora «An on-demand answer discarded twice
>   running». Lo segnalo a Risk, senza toccarlo.

### L10-1 · i commenti ✅ 2026-10-05 (`/tmp/libreFolio_f4/l10_comments.py`, 12 sostituzioni esatte, ciascuna trovata una volta)

> **Note implementazione**
> - Produzione, solo commenti, in 6 file: «discarded twice running» diventa «discarded on every attempt» in
>   `AssetSetRiskReturnSection`, `AssetSetLossComparisonSection`, `AssetSetCorrelationSection`, `AssetSetReplaySection` e
>   `AssetSetComparisonLevels`. In `AssetSetRiskPanel`:
>   - `:193`: «`loadBase` re-asks only up to `RISK_DISCARD_ATTEMPTS` in all»;
>   - `:490`: tolto «the policy `loadBase` adopted for the same guard». Il singolo nuovo tentativo del preset broker
>     resta com'è.
> - Test: «three times running», come scrive k3 negli stessi file, nelle due intestazioni e nel titolo di
>   `AssetSetComparisonLevels.test.ts:956`.
> - E2E: `risk-lab.spec.ts:6354`, «re-asked, up to three attempts in all».
> - **Prova che è solo testo**: nel diff (32 righe) l'unica riga che non è un commento è il titolo del test. In nessuno
>   dei miei file resta «twice running», «re-asked once», «asks again only once» o «the policy `loadBase` adopted».
>
> **⚠️ Fuori pista**: lo stesso testo vecchio sta in due file che non sono miei, e li segnalo senza toccarli.
> - `levels/RiskLevelsPanel.svelte:148`: «An on-demand answer discarded twice running».
> - La descrizione di `component-unit` in `scripts/test_runner/_frontend_utility.py:532` (del coordinatore): «a replay
>   answer discarded twice running is disclosed as risk.errors.answer_discarded».

### L10-2 · i cancelli ✅ 2026-10-05, 18:4x-18:5x (fuori corsia: nessun comando tocca la 6154)

> - prettier sui 9 file pulito; `front check` 0/0; `tsc -p tsconfig.e2e.json` 2 errori (il pavimento, altri file);
>   lista vitest **1401** (invariata); `git diff --check` pulito.
> - Il titolo cambiato gira: `vitest --reporter=verbose` su `AssetSetComparisonLevels.test.ts` lo mostra due volte
>   (L1° e L3°), e i test del file restano 50.
> - **Non eseguiti, e perché**: `front build` e gli E2E. Nessun comportamento cambia: le modifiche ai `.svelte` sono
>   commenti nello script, compilati da svelte-check e montati da vitest; lo spec cambia solo un commento, e `tsc e2e` lo
>   compila.

### Checkpoint del giro 10 · 2026-10-05 (verso Risk)

> - Base `0da41fb11`, 10 percorsi, tutti modificati. Due gruppi: **G1** il testo nel codice (6 `.svelte`, 2 test,
>   1 spec), **G2** questo journal.
> - Strumenti: `/tmp/libreFolio_f4/l10_msgs.py`, `l10_record.sh` e `verify_l10.sh`.
> - CHANGELOG: niente, perché nulla cambia per l'utente.
> - Stato dopo l'invio: **FROZEN** fino al commit.

### Giro 10 committato, e la chiusura della sessione · 2026-10-05, sera

> - Commit del developer: `875e06589` (G1) e `174c467df` (G2), albero `d1e0afe3e`. `/tmp/libreFolio_f4/verify_l10.sh`:
>   **PASS** (2 commit lineari su `0da41fb11`, messaggi, percorsi e blob identici al record). Worktree pulito prima di
>   questa nota.
> - **Il developer chiude la sessione** (coordinatore): niente di nuovo. Nessun server avviato in questo giro; 6154 e 6164
>   libere.
> - **`/tmp`**: macOS toglie i file non toccati da 3-4 giorni. Ho copiato `/tmp/libreFolio_f4/` e i miei record
>   `/tmp/libreFolio_commits/f-*` nei file della mia sessione, fuori dal repo.
>   - Esclusi apposta: i tre script della correzione di privacy, la prima scansione e un vecchio estratto del journal.
>     Contengono proprio i dati tolti dai journal. In `/tmp` sono leggibili solo dall'utente (file 600, cartella 700), e
>     la pulizia di macOS li toglierà.
>   - Il DB della corsia (`/tmp/librefolio-r2-f`) non serve copiarlo: ogni E2E lo ricrea.
> - **Concessione per il prossimo giro** (dal coordinatore, via Risk): in `scripts/test_runner/_frontend_utility.py:532`
>   solo la frase della descrizione di `component-unit` «a replay answer discarded twice running» passa ai tre
>   tentativi. Nient'altro nel file.
>
> **Da A (18:40), la richiesta del developer dalla sua review visiva di oggi**, alla lettera: «le label che sono
> applicabili scrivile anche là, e fallo a livello di componente, non di wrapper se possibile, e sì fai la stessa cosa
> anche con la tabella, rendi il tutto un componente così che nel tempo se aggiorniamo uno aggiorniamo entrambi. […]
> nella tabella metti la paginazione se ci sono più di 5 righe […]. Sul come farlo mettetevi d'accordo tra di voi».
> - **La proposta di A**:
>   - un componente condiviso `components/risk/RiskReturnLevel.svelte`, con aiutanti e test; il mio
>     `AssetSetRiskReturnSection` e il suo `L3RiskAdjusted` diventano involucri che costruiscono le righe dal proprio
>     payload;
>   - dentro: prima la tabella (la mia DataTable, `assetNameColumn`, le colonne con i tooltip, la selezione singola
>     legata ai punti), poi il grafico;
>   - una colonna compare solo se le righe la portano; paginazione sopra 5 righe (`[5, 10, 25, 0]`, come
>     `DistributionEditor`);
>   - le note per capacità e non per pagina: quelle sulla retta solo dove c'è la retta, mai nel laboratorio;
>   - un `testIdPrefix`, così i miei testid restano;
>   - A scrive il componente; la migrazione della mia sezione la faccio io, oppure A con una mia concessione.
> - **Le sue tre domande**:
>   1. il nome del rendimento: il mio «rendimento medio annuo» (developer, 30/09) su entrambe le pagine;
>   2. le colonne per asset che la Dashboard non ha (Sortino, Sharpe, beta, correlazione): dipendono dal controller di
>      Risk, quindi la prima versione mostra solo ciò che c'è;
>   3. come si incastra col mio lavoro, e quali file evitare.
> - **Fatti già verificati** (in sola lettura, su `0da41fb11`):
>   - la sezione ha 356 righe, e tutti i suoi testid hanno il prefisso `risk-asset-set-l3` (14, più il `testId` del
>     grafico); il suo test ha 1859 righe;
>   - `assetNameColumn` sta in `assetSetTable.ts:54`, mio;
>   - `assetSetI18n.test.ts` legge il sorgente della sezione per trovare la nota che rende, quindi deve seguire lo
>     spostamento.
> - **Da verificare prima di rispondere**:
>   - come si decidono oggi le colonne Beta e Correlazione. Devono restare legate alla capacità (c'è un benchmark),
>     non a «qualche riga ha un valore»: con un benchmark e beta tutti indefiniti la colonna c'è, con i trattini;
>   - quante righe usano i test di L3, unitari ed E2E: a 5 per pagina le righe oltre la prima pagina spariscono;
>   - se `DataTable` sa portarsi alla pagina della riga scelta da un punto del grafico;
>   - se `warningTranslatorSites.test.ts` legge il sorgente della sezione.
> - **Bozza della risposta (non ancora inviata)**:
>   - due passi: prima lo spostamento puro, col laboratorio identico e i miei test invariati come guardia; poi la
>     paginazione, con i rossi prima;
>   - sì al nome «rendimento medio annuo» su entrambe;
>   - colonne per capacità esplicita;
>   - nessun importo nel laboratorio, e la rete E2E lo guarda;
>   - chi migra la mia sezione e chi è il writer del file nuovo condiviso si decide col coordinatore.
>
> **Prossimo passo, in ordine**:
> 1. le verifiche sopra, poi la risposta ad A, con il coordinatore informato per la proprietà del file nuovo e per le
>    concessioni;
> 2. la concessione di `_frontend_utility.py:532`;
> 3. in attesa:
>    - il rombo di A, poi `correlation.en.md:117` («its dot»);
>    - il contratto della tappa 2 di Risk dopo il suo k4, poi l'adozione in `AssetSetRiskPanel`;
>    - la review unica sulla 6164, con una copia di prod nuova e l'OK del developer.

## Ripresa · 2026-10-06, dalle 09:2x

> - Stato: `174c467df`, un file sporco (la nota di chiusura qui sopra); 6154 e 6164 libere; `/tmp/libreFolio_f4/` intatto.
>   Carico della macchina alto (19-21), da ricordare per gli E2E sensibili ai tempi.
> - **Arrivato da A dopo la chiusura (05/10, 18:46)**, annotato solo nelle note private perché ero FROZEN:
>   - il developer ha chiesto che la retta passi dal benchmark quando c'è. `capitalMarketLine` si ancora al benchmark e
>     ripiega sul portafoglio; `capitalMarketLineAnchor()` dà `'benchmark' | 'portfolio' | null`, e `null` senza un
>     punto del portafoglio. Nel laboratorio quindi niente retta, e i miei due test del grafico passano invariati;
>   - la mia guida: `correlation.en.md:116` («On a portfolio, a line through the portfolio's own point separates…»)
>     diventa inesatta sulle pagine col portafoglio quando c'è un benchmark. La correggo insieme a `:117` (il rombo)
>     quando il cambiamento di A arriva nel mio ramo, spiegando anche perché il laboratorio, che un benchmark ce l'ha,
>     non disegna la retta.
>
> **Le quattro verifiche per la proposta di A** (`RiskReturnLevel`), su `174c467df`:
> 1. **Colonne Beta e Correlazione**: le decide una prop esplicita, `benchmarkApplies`, non i valori. Con un benchmark e
>    beta tutti indefiniti la colonna c'è, coi trattini. Sulla riga del riferimento (D371) le due celle hanno un
>    trattino col suo tooltip (`referenceItself`). Quindi «una colonna compare se le righe la portano» deve essere una
>    capacità esplicita.
> 2. **Paginazione a 5**: non è neutra per i miei test.
>    - Unitari: `SELECTION` ha 5 righe e non pagina; `SELECTION_WITH_REFERENCE` (D371) ne ha 6, `WIDE_SELECTION` 12.
>    - E2E: una decina di asserzioni contano le celle di L3° contro `selected.length` o `covered.length`, con selezioni
>      «almeno N» prese dal seed.
> 3. **`DataTable.navigateToRowId()`** porta già alla pagina della riga, ma la evidenzia e la scorre in vista
>    (`scrollIntoView` smooth, al centro). Il grafico sta sotto la tabella, quindi un clic su un punto tirerebbe la
>    pagina in su. Serve una via «solo pagina», e `table/` è condiviso.
> 4. **Chi legge il sorgente della sezione**: solo `assetSetI18n.test.ts:208-212` (la chiave della nota sotto il
>    grafico), dentro il blocco già concesso ad A. `warningTranslatorSites.test.ts` scandisce ogni `.svelte` in modo
>    generico. Il resto di `assetSetI18n.test.ts` controlla l'intero sottoalbero `risk.assetSet`: se le chiavi di L3°
>    ne escono, il mio test non si rompe ma ne copre meno, e il controllo deve passare ai test del componente.
> - Altri pezzi del laboratorio che il componente deve permettere senza conoscerli: la descrizione, i quattro stati col
>   riprova, il blocco del periodo sotto la tabella, `tableRef` (il menu delle colonne di `AssetSetComparisonLevels`),
>   `storageKey`, `data-row-count` e `data-benchmark`, lo scorrimento dei nomi lunghi.
>
> **La risposta ad A (09:4x)**:
> - **sì al componente unico**. A ne è il writer e, nella stessa modifica, fa della mia sezione il suo involucro con una
>   mia concessione, così i miei test fanno da guardia subito;
> - **passo 1, solo lo spostamento, senza paginazione**:
>   - Props, testid e attributi invariati, e quindi `AssetSetComparisonLevels` non si tocca;
>   - i miei test passano invariati, compreso `risk-lab`;
>   - nel mio involucro restano righe e punti (D371), la descrizione, gli stati e il periodo;
>   - nessun importo;
>   - rivedo il diff dei miei file prima del suo checkpoint;
> - le colonne per capacità esplicita;
> - la paginazione è il passo 2, da pianificare insieme dopo il passo 1;
> - sì a «rendimento medio annuo» su entrambe le pagine; colonne della Dashboard solo da ciò che il payload ha.
> - Al coordinatore: il writer del file nuovo condiviso e la concessione sulla mia sezione. In attesa.

## Giro 11 · la frase del runner, e la guida dopo i cambi di A · 2026-10-06

| # | passo | stato |
|---|---|---|
| L11-1 | `scripts/test_runner/_frontend_utility.py:532`, concessione del coordinatore via Risk: nella descrizione di `component-unit` solo «a replay answer discarded twice running» passa a «three times running», le parole del `describe` di `AssetSetReplaySection.test.ts:367` (k3). Nient'altro nel file | ✅ 2026-10-06 |
| L11-2 | la guida `correlation.en.md:116-117` (la retta dal benchmark, il rombo), quando i cambi di A arrivano nel mio ramo | in attesa |
| L11-3 | il passo 1 di A (`RiskReturnLevel`): rivedere il diff dei miei file prima del suo checkpoint | in attesa |

> **Il coordinatore (09:5x) approva entrambe le decisioni**:
> - A scrive `components/risk/RiskReturnLevel.svelte`, con aiutanti e test: file nuovi condivisi della famiglia, di A
>   finché il passo 1 non arriva;
> - la mia concessione ad A per il passo 1 resta com'è scritta. Il mio `risk-lab` è nei cancelli di A, e io rivedo il
>   diff di A sui miei file prima del suo checkpoint;
> - **paginazione (passo 2)**: la via «solo pagina» nel `DataTable` condiviso è fuori dalla famiglia. Prima di toccarlo
>   serve un'analisi breve (chi lo chiama, come si comporta `navigateToRowId`, i test) e una sua concessione.

### L11-1 · la frase del runner ✅ 2026-10-06, 09:5x

> **Note implementazione**
> - Una sola sostituzione esatta, trovata una volta: nella descrizione di `component-unit` (`:532`) «a replay answer
>   discarded twice running» diventa «a replay answer discarded three times running». Il word-diff mostra solo
>   `[-twice-]{+three times+}`; `--numstat` dà 1/1.
> - Prove: `python3 -m py_compile` passa; `dev.py test check-orphans` esce 0 (registrati 94 E2E, 297 unitari e 229
>   backend, tutti raggiungibili da `all`).

### Checkpoint del giro 11 · 2026-10-06 (verso Risk)

> - Base `174c467df`, 2 percorsi modificati: **G1** la frase del runner, **G2** questo journal (la chiusura del 05/10,
>   la ripresa, le verifiche e l'accordo con A, il giro 11).
> - L11-2 (la guida) e L11-3 (la revisione del passo 1 di A) restano aperti: aspettano i cambiamenti di A.
> - Strumenti: `/tmp/libreFolio_f4/l11_msgs.py`, `l11_record.sh` e `verify_l11.sh`.
> - CHANGELOG: niente, perché nulla cambia per l'utente.
> - Stato dopo l'invio: **FROZEN** fino al commit.

### Giro 11 committato ✅ 2026-10-06, 09:4x

> - Commit del developer: `6d8476f91` (G1) e `cda8cba1c` (G2); `HEAD~2` = `174c467df`, albero `231a635c9`.
>   `/tmp/libreFolio_f4/verify_l11.sh`: **PASS**. Worktree pulito.
> - **A (09:33) accetta tutte le condizioni del passo 1.** Una dipendenza: il mio `174c467df` non è nel suo ramo, e la
>   mia sezione ha 91 righe in più dalla nostra base comune. Il suo ordine, chiesto al coordinatore: il suo checkpoint 6,
>   poi la fusione della mia punta nel suo ramo, poi il passo 1.
> - **Mio impegno con A**: finché il passo 1 non arriva, gli dico prima di committare qualunque cosa sui miei file di
>   L3°. Non ne ho in programma.

## Giro 12 · in attesa di A, e l'analisi del `DataTable` per il passo 2 · 2026-10-06

| # | passo | stato |
|---|---|---|
| L12-1 | analisi breve della via «solo pagina» nel `DataTable` condiviso, chiesta dal coordinatore prima di ogni concessione: chi lo chiama, come si comporta `navigateToRowId`, i test | ✅ 2026-10-06, in sola lettura |
| L12-2 | la guida `correlation.en.md:116-117` (la retta dal benchmark, il rombo), quando i cambi di A arrivano nel mio ramo | in attesa |
| L12-3 | il passo 1 di A: rivedere il diff dei miei file prima del suo checkpoint | in attesa |
| L12-4 | `DataTable`: l'opzione «solo pagina» di `navigateToRowId`, rossi prima; commit a parte `feat(ui): …`, prima della paginazione di A | approvata in linea di principio; parte col passo 2, dopo la conferma della UX dal developer |
| L12-5 | `risk-lab` raggiunge i provider di cambio veri (segnalato da A): la modale di sincronizzazione chiede `GET /fx/providers`. Correzione nello spec (test-author), prova nel log della corsia | ✅ 2026-10-06, 10:1x |

### L12-1 · `DataTable.navigateToRowId`: la via «solo pagina» (su `cda8cba1c`, solo lettura)

> - **Cosa fa oggi** (`table/DataTable.svelte:856-881`), in quest'ordine:
>   1. trova la riga in `sortedData`, quindi tiene conto dell'ordinamento attivo;
>   2. se c'è la paginazione, passa alla sua pagina;
>   3. la evidenzia (`highlightedRowId`: `data-highlighted="true"` e la classe `highlighted`). L'evidenza si spegne al
>      clic su una riga o a un tasto nella tabella;
>   4. dopo un `tick()`, la porta in vista con `scrollIntoView({behavior: 'smooth', block: 'center'})`, cercandola solo
>      nel proprio contenitore (Bugfix-4 §C15).
> - **Chi la chiama**: 13 chiamate in 6 posti, tutti fuori dalla famiglia, e tutti la usano per «vai a quella riga e
>   mostramela», quindi lo scorrimento lo vogliono:
>   - `ui/data-editor/DataEditor.svelte` (3);
>   - `brokers/lots/LotsAnalysisPanel.svelte`, tramite `UnifiedLotsTable.svelte`, che la riesporta;
>   - `transactions/modals/TransactionBulkModal.svelte` (5);
>   - `transactions/TransactionsTable.svelte`, in modalità piatta;
>   - `routes/(app)/transactions/+page.svelte`.
> - **Test** (`table/DataTable.test.ts:517-556`):
>   - salta alla pagina della riga e la segna;
>   - tiene conto dell'ordinamento;
>   - ignora un id che non ha.
>   Nessuno fissa lo scorrimento: jsdom non ha layout.
> - **Non c'è un controllo esterno della pagina**: nessuna prop `$bindable` per l'indice di pagina, nessun callback.
>   Esistono `getPageRowIds()` e `getSortedRowIds()`. L'ultima modifica al file è dell'11/09.
> - **Il problema per L3°**: con la paginazione, un clic su un punto la cui riga sta su un'altra pagina deve portare la
>   tabella su quella pagina. `navigateToRowId` lo fa, ma scorre anche la vista per centrare la riga. Il grafico sta
>   sotto la tabella, quindi la vista salterebbe in su, via dal punto appena cliccato. In più l'evidenza ripeterebbe la
>   selezione, che la riga mostra già.
> - **La modifica più piccola** (additiva):
>   - `navigateToRowId(rowId, {scroll = true, highlight = true} = {})`, con valori di difetto che lasciano identiche
>     tutte e 13 le chiamate;
>   - il componente condiviso chiamerebbe `navigateToRowId(id, {scroll: false, highlight: false})` e poi
>     `toggleRowSelectionById(id)`;
>   - l'alternativa è un metodo nuovo, `showRowPage(id)`.
> - **Rossi prima**, in `DataTable.test.ts` (fuori famiglia, serve la concessione):
>   - con `{scroll: false, highlight: false}` cambia pagina, non segna nulla e non chiama `scrollIntoView`;
>   - il difetto evidenzia e chiama `scrollIntoView` con `smooth` e `center`. Oggi nessun test lo fissa.
> - **Da confermare col developer quando pianifichiamo il passo 2 con A**: un clic su un punto cambia la pagina della
>   tabella senza spostare la vista.
>
> **Il coordinatore (09:45) approva in linea di principio, per quando parte il passo 2**:
> - l'opzione additiva `navigateToRowId(rowId, {scroll = true, highlight = true} = {})`, con difetti che lasciano
>   identiche le 13 chiamate;
> - i rossi prima in `DataTable.test.ts`, come li ho elencati. Il test del difetto, che fissa lo scorrimento `smooth` al
>   centro, è obbligatorio;
> - **il writer sono io**, con un commit piccolo e a parte (`feat(ui): …`) prima del passo di paginazione di A, che lo
>   usa;
> - oggi nessun ramo tocca `DataTable.svelte`, committato o no;
> - la UX (un punto cambia la pagina senza spostare la vista) va al developer quando si pianifica il passo 2. Fino ad
>   allora non scrivo nulla: un'opzione che il developer potrebbe non volere sarebbe codice morto.

### L12-5 · `risk-lab` chiama i provider di cambio veri · analisi (skill test-triage), 2026-10-06

> - **Il reperto di A** (09:48): sul suo albero, a fine giro, il backend ha scritto «SNB dimensions loaded»
>   (`fx_providers.snb`), cioè una GET vera all'API della SNB.
> - **Confermato nella mia corsia** (`/tmp/librefolio-r2-f/logs/librefolio.log`): una riga per giro dentro le finestre
>   di `risk-lab` di ieri (15:47:52Z in `l9final`, 16:03:11Z in `l9ff`). Le altre due righe cadono nelle finestre di
>   `risk`, lo spec di A, che A ha già curato.
> - **La causa, nel codice**:
>   1. la modale di sincronizzazione del laboratorio (`PageSyncModal.svelte:55-64`), quando si apre, chiama
>      `getCurrencyGraph()` per avere le icone dei provider;
>   2. `getCurrencyGraph()` chiede `GET /api/v1/fx/providers`;
>   3. lato backend, `list_providers` (`api/v1/fx.py`) chiama `get_supported_currencies()` su ogni provider;
>   4. la SNB (`_ensure_currency_map`, `snb.py:138`) scarica le sue dimensioni dalla rete.
>   Lo fa anche la BCE: lo stesso log ha i suoi «Failed to fetch available currencies from ECB» (senza rete, di notte).
>   La perdita quindi riguarda tutti i provider, e solo la SNB scrive i successi.
> - **Non è la causa**: la lettura di `/fx/providers/routes` a `:3186`, l'altra ipotesi di A. Quell'endpoint legge solo
>   il DB (`list_routes`, una `select`).
> - **Chi apre la modale**: `:3090` (un aiutante), `:4706` (il Sync del banner), `:6245` e `:6325` (la sincronizzazione
>   della barra).
> - **Verdetto (test-triage §8)**: assumption. I test presumevano che aprire la modale non chiamasse nulla fuori, e la
>   correzione va nello spec.
> - **Come correggere**:
>   - in `installRiskMocks` dello spec, accanto a `holdLivePricePoll`, si ferma `GET /api/v1/fx/providers` (solo il
>     percorso nudo, mai `/routes`);
>   - trattenerla è ciò che ha fatto A (`holdFxProviderCatalog`), ma `getCurrencyGraph()` ha `try/finally` senza
>     `catch` e la modale non la attende. Dopo i 30 s di axios ne verrebbe un rifiuto non gestito nella pagina.
>     Nessun test lo guarda oggi, ma resta rumore;
>   - rispondere con un catalogo vuoto è inerte: una GET su `/fx/providers` non è una mutazione
>     (`portfolioMutation.ts:58` riconosce solo POST e DELETE su `/routes`), e la modale usa il grafo solo per le icone;
>   - la scelta tocca a test-author, che deve dimostrare che nessuna asserzione cambia;
>   - in più, un test che apre la modale controlla che la richiesta sia stata intercettata, così un URL cambiato non
>     riapre la perdita in silenzio.
> - **Prova richiesta**: `risk-lab` 41/41 nella corsia 6154, e zero righe `fx_providers` nel log della corsia nella
>   finestra del giro.
> - **Il mio cancello**: anche lo schema delle perdite nei miei script (`/tmp/libreFolio_f4/l*_gates.sh`) non conta le
>   righe `fx_providers`; lo aggiungo.

### L12-5 · la correzione (test-author `fx-provider-leak`) ✅ 2026-10-06, 10:0x-10:1x

> **Note implementazione** (`risk-lab.spec.ts`, +70 −1, nessun altro file):
> - `answerFxProviderCatalog(page)`, subito dopo `holdLivePricePoll`:
>   - instrada solo il percorso nudo `/\/api\/v1\/fx\/providers(?:\?|$)/`, con o senza query. Test-author ha verificato
>     che non prende `/routes`, `/routes?…`, `/providers/` né `/providersX`;
>   - risponde `200 []` a una GET e la registra; ogni altro metodo passa con `route.fallback()`;
>   - nulla toglie la route alla fine, come per `holdLivePricePoll`.
> - La chiama `installRiskMocks`, che usano tutti e cinque i test che aprono la modale; l'unico test senza mock (la
>   guardia del catalogo) non carica pagine. L'intestazione del file dice che la modale non raggiunge più i provider.
> - **Risposta e non trattenuta**: una GET su quel percorso non è una mutazione (`isPortfolioAffectingMutation`), e una
>   richiesta trattenuta diventerebbe, dopo i 30 s di axios, un rifiuto non gestito dentro i test più lunghi. `[]` è
>   valido per lo schema, e la modale lo usa solo per le icone.
> - **La guardia si controlla da sé**: il test della sincronizzazione della barra verifica che almeno una richiesta del
>   catalogo sia stata intercettata. Lo verifica come «almeno una» e mai come conteggio, perché il grafo resta in cache.
> - **Ho verificato due affermazioni del docblock**:
>   - la BCE interroga la rete a ogni chiamata (`ecb.py:92-135`, nessuna cache);
>   - `isPortfolioAffectingMutation` esiste (`portfolioMutation.ts:19`).
>
> **Prove** (corsia 6154, un comando per volta):
> - prettier pulito; `tsc -p tsconfig.e2e.json` 2 errori, il pavimento, in altri file; `front build --debug` passa, con
>   svelte-check 0/0;
> - **giro 1**: 40/41; **giro 2**: **41/41**;
> - righe `fx_providers` nel log della corsia: **0** in entrambe le finestre (08:06:44-08:09:41Z e 08:11:57-08:14:01Z).
>   Il log DEBUG è acceso e la SNB scrive alla prima richiesta del catalogo, riuscita o fallita, quindi zero vuol dire
>   che nessuna richiesta è arrivata;
> - 6154 libera alla fine.
>
> **⚠️ Fuori pista: il rosso del giro 1 (skill test-triage).**
> - **Il fatto**: il test del selettore del benchmark, ora a `:5455`, si ferma a `:5490`: il tooltip della ⓘ non è
>   visibile entro i 3 s di `expect` del progetto. Lo screenshot preso subito dopo lo mostra aperto e con la frase
>   giusta.
> - Il test attende la condizione giusta (il tooltip visibile, con asserzioni che riprovano) e nessun orologio. Non apre
>   la modale, quindi la correzione non passa da lì.
> - Carico durante il giro: 54,7 (1 minuto) e 37,1 (5 minuti) su 10 core. I test duravano 3-5 s contro ~2,5 s del
>   05/10, questo 9,7 s. Al giro 2, con carico da 29,8 a 21,8, è verde.
> - **Verdetto (§8): slowness**, cioè lentezza causata dall'ambiente: la macchina è sovraccarica di servizi di sistema,
>   come ha detto il coordinatore. Niente da cambiare; se torna rosso a carico normale, si fa il triage vero.
>
> **⚠️ Fuori pista: il log della corsia è ruotato** all'avvio del backend del giro 1. Il file da 116 MB, con le righe
> SNB del 05/10, è ora `logs/librefolio.log.2026-09-29.gz`. Test-author l'ha controllato: niente delle sue finestre è lì.
> I miei script delle perdite contano anche `fx_providers` (`/tmp/libreFolio_f4/l12_gates.sh`).

### Il passo 1 di A è partito, e la nota sotto il grafico · 2026-10-06, 10:2x

> - A parte dalla base fusa `f6b7273f8` (la mia punta nel suo ramo), su cui ha validato `risk-lab`, 41 passati.
> - **La domanda di A**: nel componente le note vengono dalle capacità. Nel laboratorio sono due righe condivise:
>   «I punti usano il rendimento medio annuo: su un asset molto volatile, quello vissuto davvero è più basso.» e «Il
>   rendimento viene dai soli prezzi: cedole e dividendi non sono ancora inclusi» (chiesta da Risk). La seconda frase del
>   mio `risk.assetSet.levels.l3.scatterNote` ripete la prima riga. A propone due strade:
>   - (a) ritirare la mia nota;
>   - (b) una `leadNote` passata dal mio involucro, con la nota accorciata alla frase sugli assi.
> - **La mia scelta, (a)**:
>   - (b) direbbe due volte di seguito che l'asse verticale è il rendimento medio annuo, e terrebbe del testo
>     nell'involucro, contro la richiesta del developer («a livello di componente, non di wrapper se possibile»);
>   - quello che (a) perde, la lettura in parole dell'asse orizzontale, lo dicono già il nome dell'asse («Volatilità
>     annualizzata») e il tooltip della colonna Volatilità.
> - **Condizioni date ad A**:
>   - il testid `risk-asset-set-l3-scatter-note` resta sull'elemento che contiene le note del laboratorio, così
>     `AssetSetRiskReturnSection.test.ts:1159`, che chiede solo un testo non vuoto, passa invariato;
>   - la chiave si toglie dai 4 cataloghi nella stessa modifica, con `dev.py i18n`, sotto la mia concessione, e va
>     elencata nella consegna;
>   - la guardia (`assetSetI18n.test.ts:208-212`, nel blocco concesso) controlla che nessuna nota resa dal laboratorio
>     nomini una retta, nelle 4 lingue.
> - **Verificato prima di rispondere**: il mio E2E non legge la nota, e la mia guida non la cita.
> - **Per la mia guida, quando il passo 1 arriva**: dire che il rendimento viene dai soli prezzi, senza cedole né
>   dividendi. Per chi legge il laboratorio è una notizia. Va con L12-2.
> - Ad A ho detto anche che lo spec cambia nel giro 12 senza toccare i test di L3°. Gli ho segnalato il rifiuto non
>   gestito che darebbe una richiesta trattenuta: riguarda il suo `holdFxProviderCatalog`.

### Checkpoint del giro 12 · 2026-10-06 (verso Risk)

> - Base `cda8cba1c`, 2 percorsi modificati: **G1** lo spec (la perdita verso i provider), **G2** questo journal (il
>   giro 11 committato, l'accordo e la dipendenza con A, l'analisi del `DataTable`, la revisione della tappa 2, la
>   perdita).
> - Strumenti: `/tmp/libreFolio_f4/l12_msgs.py`, `l12_record.sh` e `verify_l12.sh`.
> - CHANGELOG: niente, perché nulla cambia per l'utente.
> - Ad A, prima del commit (il mio impegno): fatto, lo spec cambia senza toccare i test di L3°.
> - Stato dopo l'invio: **FROZEN** fino al commit.
