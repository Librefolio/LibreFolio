# Piano — K / step 12: seguiti della review (selezione, bandiere, titolo)

> Tre seguiti della review del developer del 28–29/09, assegnati a K. Analisi (29/09) approvata dal developer con tutte
> le raccomandazioni (coordinator, 29/09 10:52). Viene dopo lo step 11
> ([`plan-phase00TaxonomySelectStep11BulkCreationOrder.prompt.md`](plan-phase00TaxonomySelectStep11BulkCreationOrder.prompt.md)).
> Ordine **c → a → b**, un commit per punto, un solo checkpoint alla fine. Test rossi prima (test-author).
> Seguito: step 13, [`plan-phase00TaxonomySelectStep13DevNotesFixes.prompt.md`](plan-phase00TaxonomySelectStep13DevNotesFixes.prompt.md).

| | |
|---|---|
| **Baseline** | `4ce1dc35f` (= `dev_release2`, dopo il fast-forward su `fb7701968` e il CHANGELOG del coordinator) |
| **Lane suite** | `--test-port 6155 --data-dir /tmp/librefolio-r2-k`; `front build --debug` prima della prima suite che avvia il backend |
| **File di K** | c: `files/+page.svelte`, `tools/+page.svelte`, `tools/[tool_code]/+page.svelte`, `(app)/+layout.svelte`, `e2e/layout/document-title.spec.ts`, `(app)/layout.gate.test.ts`; a: `transactions/+page.svelte`; b: `app.css`, `app.html`, `static/offline.html`, `static/fonts/**`, `scripts/update_js_cache.py`, `TransactionsTable.svelte` (solo `:1100`), devWiki `problems/flag-emoji-windows.md` |
| **Condivisi, solo in aggiunta** | `scripts/test_runner/_frontend_utility.py`, `scripts/test_runner/_frontend_transaction.py` |

## Decisioni del developer

- **D-a1, D-a2**: la selezione si azzera dopo **ogni** commit eseguito dal workspace (modifica, clona, elimina, Aggiungi,
  Importa) e dopo collega e scollega; resta all'annullo.
- **D-b1**: le bandiere sul canvas di ECharts vanno nel backlog dei proprietari dei grafici (lista nell'handoff).
- **D-b2**: via il `<link>` di Noto e i 10 sottoinsiemi morti; K scrive `app.html`, `offline.html` e `update_js_cache.py`.
- **D-b3**: adesso un test di controllo sul file delle bandiere; nel backlog il nome stabile generato dallo script.
- **Addendum**: la faccia `'LF Flags'` sta in `static/fonts/lf-flags.css`, linkata da `app.html` e `offline.html`; anche in
  `offline.html` `.emoji-flag` segue la regola nuova.
- **D-c1**: il `<title>` di `offline.html` resta «LibreFolio — Offline».
- **c** comprende le pagine Tools, il reset del layout e il contratto finale.

## c. Nessuna pagina cambia il titolo della scheda

- Via i `<svelte:head><title>` di `files/+page.svelte:691-693`, `tools/+page.svelte:6-8`, `tools/[tool_code]/+page.svelte:9-11`
  (con l'import `t` se resta senza uso; le chiavi `uploads.title` e `tools.title` restano).
- Via il reset di `(app)/+layout.svelte:57-63` e l'import di `onNavigate`, che serviva solo a quello; via la sua sezione in
  `layout.gate.test.ts`.
- `document-title.spec.ts` al contratto finale: nessuna pagina cambia il titolo (arrivo diretto e navigazione nell'app).
- Guardia nuova: unit che vieta `<svelte:head>` con `<title>` e `document.title =` in `src`, allow-list vuota.

## a. Selezione dopo un'operazione bulk

- Helper `clearSelection()` (tabella via `getTableRef().clearSelection()`, che emette `onSelectionChange([])`, più
  `selectedRows`) in `handleBulkCommitted`, nel successo di promote e split, nel «clear» della toolbar e nel refresh.
  Mai in `onClose`/`onCancel`.

## b. Bandiere: regola globale solo per le bandiere

- `static/fonts/lf-flags.css`: `@font-face 'LF Flags'`, `src: local('Apple Color Emoji'), local('AppleColorEmoji'),
  local('Noto Color Emoji'), url(noto-color-emoji.0.woff2)`, `unicode-range: U+1F1E6-1F1FF`.
- `'LF Flags'` in testa a `html`, `@theme --font-sans` e `--font-mono`; `.emoji-flag` = `'LF Flags', Inter, system-ui,
  sans-serif`; via lo stile di `TransactionsTable.svelte:1100`; `offline.html` uguale.
- Via il `<link>` di Noto da `app.html` e `offline.html`, i 10 sottoinsiemi morti; `update_js_cache.py` scarica solo il
  sottoinsieme delle bandiere.
- devWiki `problems/flag-emoji-windows.md` riscritta.

## Passi

- [x] **12.0 Piano nel journal** — ✅ 2026-09-29: questo file, con il rimando dallo step 11.
- [x] **12.1 c** — ✅ 2026-09-29: test rossi (guardia, `document-title.spec.ts`), codice, gate, commit c.
  > **Note implementazione**:
  > - **Rossi prima** (test-author, HEAD `4ce1dc35f`):
  >   - guardia nuova `src/routes/documentTitle.guard.test.ts`, 5 test, allow-list vuota: 1 rosso, che elenca esattamente
  >     `(app)/+layout.svelte:63` (`document.title =`), `files/+page.svelte:692`, `tools/+page.svelte:7` e
  >     `tools/[tool_code]/+page.svelte:10`;
  >   - `document-title.spec.ts` al contratto finale: 11 test × desktop e mobile = 22. **10 rossi, 12 verdi**: solo File,
  >     Tools e la pagina del tool (`/tools/pac_allocator`, codice letto da `GET /api/v1/tools/catalog`); Dashboard,
  >     Transazioni, Asset, Broker, FX e Impostazioni verdi;
  >   - `layout.gate.test.ts`: via la sezione del titolo e i suoi helper, da 4 a 2 test, verdi.
  > - **Codice**:
  >   - via i `<svelte:head>` di File, Tools e della pagina del tool;
  >   - via l'import `t` delle due pagine Tools, rimasto senza uso; le chiavi `uploads.title` e `tools.title` restano,
  >     per i titoli `<h1>` e la barra laterale;
  >   - via il reset `(app)/+layout.svelte:57-64` e `onNavigate` dall'import.
  >   - Lo stub `onNavigate: vi.fn()` rimasto nel mock di `layout.gate.test.ts` l'ho tolto io: una riga, conseguenza
  >     della rimozione.
  > - **Gate** nella lane 6155, dopo `front build --debug` (`/tmp/libreFolio_k_12c_gates.sh`):
  >   - `document-title` **22/22**; `core-unit` 99 file, **2651 ✓**, guardia compresa; `component-unit` 85 file,
  >     **2113 ✓**, `layout.gate` compreso; `files` **20/20**;
  >   - `check-orphans` ok; knip, niente sui file toccati; svelte-check, i 3 errori della baseline.
  > - **Runner**: una riga aggiunta in `_frontend_utility.py` (la guardia in `core-unit`), più la `desc` di
  >   `document-title` aggiornata al contratto nuovo.
  >
  > **Fuori pista**:
  > - Nessuna pagina di un tool si apre cliccando la sua card: `lib/features/tools/registry.ts` non compila l'interfaccia
  >   di nessun tool, uno stato documentato dal 21/09. La camminata E2E parte quindi dall'arrivo diretto sulla pagina del
  >   tool e torna all'hub dal suo link di ritorno.
  > - `CHANGELOG.md:52`, la voce di J («Leaving the Files page no longer leaves "Files" as the window title…»), va
  >   riconciliata con la voce di c. La scrive il coordinator.
  > - Per tenere ogni commit separabile per percorso, i test di b vanno in `_frontend_fx.py`: c tocca
  >   `_frontend_utility.py`, a tocca `_frontend_transaction.py`.
- [x] **12.2 a** — ✅ 2026-09-29: test rossi (`tx-selection-after-bulk.spec.ts`), codice, gate, commit a.
  > **Note implementazione**:
  > - **Rossi prima** (test-author, codice di prodotto intatto): spec nuova, registrata in `_frontend_transaction.py`,
  >   **6 rossi e 4 verdi**.
  >   - Rossi, i casi eseguiti:
  >     - E1 modifica: toolbar 2, poi 3 dopo un clic;
  >     - E2 clona: toolbar 2, poi 3;
  >     - E3 elimina: toolbar 2;
  >     - E4 aggiungi: toolbar 1, poi 2;
  >     - E5 collega: toolbar assente ma checkbox spuntate, poi 3;
  >     - E6 scollega: come E5.
  >   - Verdi, i casi annullati: C1 chiuso senza modifiche, C2 scartato, C3 collega annullato, C4 scollega annullato.
  >     Verificano anche che non parta nessun commit.
  >   - Importa non ha un test suo: passa dallo stesso `handleBulkCommitted` di Aggiungi, quindi lo copre E4.
  > - **Codice** (`transactions/+page.svelte`): l'helper `clearSelection()` azzera la tabella, che riporta
  >   `onSelectionChange([])`, e `selectedRows`. Lo chiamano `handleBulkCommitted`, il successo di collega e di
  >   scollega, il «clear» della toolbar e il refresh. Mai `onClose`/`onCancel`.
  > - **Gate** nella lane 6155, dopo `front build --debug` (`/tmp/libreFolio_k_12a_gates.sh`):
  >   - `tx-selection-after-bulk` **10/10**;
  >   - regressione: `transactions-table` 25, `tx-bulk-operations` 10, `transactions-modals` 19, `tx-split-promote` 6,
  >     `tx-commit-all-types` 19, `tx-wac-bulk` 10, `tx-wac-formmodal` 10, `tx-clone` 6, `tx-bulk-row-order` 3,
  >     `onboarding-tour` 10, tutti ✓;
  >   - `check-orphans` ok.
  > - La corsa rossa sul codice originale fa da mutante «senza cura».
  >
  > **Fuori pista (preesistente, per il backlog)**: clonando insieme **due righe singole dello stesso tipo**, il workspace
  > dà loro un `link_uuid` condiviso (`TransactionBulkModal.svelte:412`, da `8268a44bb`, 05/06), e l'editor le mostra come
  > una coppia (1a e 1b). La condizione controlla solo «2 righe, stesso tipo», non che siano davvero legate tra loro.
  > Rimedio probabile: condividere l'uuid solo se una delle due righe ha l'altra come `related_transaction_id`. E2 clona un
  > DEPOSIT e un WITHDRAWAL proprio per evitarlo.
- [x] **12.3 b** — ✅ 2026-09-29: test rossi (gate CSS, E2E con CDP), codice, gate, devWiki, commit b.
  > **Note implementazione**:
  > - **Rossi prima** (test-author, codice intatto):
  >   - gate statico nuovo `src/flagFont.gate.test.ts` (in `fx-unit`): **10 rossi, 3 verdi**; i verdi sono il controllo
  >     del parser e D-b3 (`.0` = U+1f1e6-1f1ff);
  >   - `test_update_js_cache.py`, classe nuova `TestKeepOnlyTheFlagsSubset`: **12 rossi, 19 verdi**, i 16 esistenti
  >     compresi;
  >   - E2E nuova `e2e/fx/fx-flag-font.spec.ts` (azione `fx-flag-font`), che legge con CDP
  >     `CSS.getPlatformFontsForNode` il font che disegna davvero ogni nodo: **4 rossi, 3 verdi**.
  >     - R1: le bandiere nella cella di cassa oggi le disegna `Noto Color Emoji`, non Apple;
  >     - R2: su macOS viene richiesto `noto-color-emoji.0.woff2`;
  >     - R3: `#lang-flag` di `offline.html` lo disegna Noto;
  >     - R4, aggiunto da test-author: dentro `.emoji-flag` cifre, `#` e `*` li disegna Apple Color Emoji;
  >     - controlli verdi: la sonda del ramo Windows (la faccia con un `local()` che non si risolve disegna la bandiera
  >       con Noto, le cifre col font di testo), le cifre accanto alle bandiere nel DOM, e una premessa.
  > - **Codice**:
  >   - `static/lf-flags.css` nuovo, con la faccia `'LF Flags'`: `local()` Apple e Noto, poi l'`url` del sottoinsieme 0,
  >     `unicode-range: U+1F1E6-1F1FF`;
  >   - `app.html` e `offline.html` linkano `/lf-flags.css` al posto della CSS di Noto;
  >   - `app.css`: `'LF Flags'` in testa a `html`, `@theme --font-sans` e `--font-mono`, e `.emoji-flag` =
  >     `'LF Flags', Inter, system-ui, sans-serif`;
  >   - `offline.html`: le sue 3 pile e il suo `.emoji-flag`;
  >   - `TransactionsTable.svelte:1100`: via il `font-family` locale, resta `line-height: 1`;
  >   - `scripts/update_js_cache.py`: `keep_unicode_ranges: ['U+1f1e6-1f1ff']`. Tiene solo i sottoinsiemi con il range
  >     normalizzato (lo 0 è sempre le bandiere), mette l'impronta nel manifest e nella decisione «aggiornato», scrive
  >     solo quando tutto è scaricato e poi toglie i `<prefix>.N.woff2` rimasti.
  > - **Gate** nella lane 6155, dopo `front build --debug` (`/tmp/libreFolio_k_12b_gates.sh`); la build contiene
  >   `/lf-flags.css`:
  >   - `fx-flag-font` **7/7**; `fx-unit` **126** (gate 13/13); `js-cache-fail-loud` **31**;
  >   - regressione: `fx-list` 12, `fx-detail` 17, `select` 17, `transactions-table` 25, `asset-list` 28, `core-unit`
  >     2651, `component-unit` 2113, `document-title` 22, tutti ✓;
  >   - `check-orphans` ok; knip e svelte-check come la baseline;
  >   - ruff e black: sulle righe nuove niente; l'errore ruff a `:564` c'è identico su HEAD.
  > - **Cache reale**: ora contiene solo `noto-color-emoji.0.woff2` (709 KB), più la CSS con una sola faccia e il manifest
  >   con l'impronta; la build successiva la dà «già aggiornata».
  > - **devWiki**: `problems/flag-emoji-windows.md` riscritta con la soluzione nuova, il perché e come provarla senza
  >   Windows; riga di `index.md` aggiornata; voce in `log.md`. `check_source_paths.py`: nessun percorso rotto nella
  >   pagina (i rossi che dà sono preesistenti, in pagine di Risk). graphify non c'è in questo worktree: niente update
  >   del grafo.
  > - Documentazione MkDocs: `admin/docker_advanced.*.md:54` («Noto… per le bandiere su Windows») resta vera: nessuna
  >   modifica.
  >
  > **Fuori pista**:
  > - **`lf-flags.css` in `static/`, non in `static/fonts/`**: `static/fonts/` è ignorata da git (`.gitignore:87`, è la
  >   cache dello script), quindi il file lì non si sarebbe mai committato. Il comportamento non cambia.
  > - **Test preesistente che scrive nella cache vera**:
  >   `TestConsumerScopedFailure::test_an_unattributed_resource_stays_fatal_for_every_consumer[required_for0]` esegue
  >   l'aggiornamento reale, con la rete, sulle cartelle vere: è lui che ha tolto i 10 sottoinsiemi appena scritto il
  >   codice. È un difetto d'isolamento, per il backlog.
  > - **Pile scritte a mano senza `'LF Flags'`** (`CompactCashCell.svelte:166`, `DataTable.svelte:2289`,
  >   `FilePreviewModal.svelte:1098,1216`, `ImageEditModal`, `FileEditModal`): una bandiera dentro è coperta solo se
  >   avvolta in `.emoji-flag`. Chi usa `formatCurrencyHtml` lo è già.
  > - **Mutanti**: la corsa rossa sul codice originale fa da mutante «senza cura». In più test-author ha provato il gate
  >   contro 9 varianti sbagliate in una copia in `/tmp`: tutte prese.
- [x] **12.4 Handoff** — ✅ 2026-09-29: messaggi di commit, lista per la verifica manuale sui dispositivi (developer),
  lista dei canvas ECharts per il backlog, voci di CHANGELOG, CHECKPOINT READY.
  > **Note implementazione**:
  > - **Quattro commit, separabili per percorso**, nessun file in due commit, in quest'ordine:
  >   - c `/tmp/libreFolio_commits/k-17-12c-tab-title.txt`, 8 file;
  >   - a `k-18-12a-selection.txt`, 3 file;
  >   - b `k-19-12b-flags.txt`, 18 file: le 3 pagine della devWiki e, dopo il via libera del coordinator, i 5
  >     documenti allineati (vedi sotto);
  >   - journal `k-20-journal-12.txt`, 2 file: questo piano e il rimando dallo step 11.
  > - Oggetti da 45, 47, 47 e 49 caratteri, solo ASCII.
  > - `git diff --check` pulito; porte 6155 e 6165 libere; nessun server acceso.
  > - Liste per il developer e per il backlog: nelle sezioni sotto.
  > - devWiki `problems/flag-emoji-windows.md`: il «Known limit» ora nomina anche i tooltip HTML di ECharts (`font`
  >   inline, verificato in `TooltipHTMLContent.assembleFont`), non solo il canvas. `check_source_paths.py`: nessun
  >   percorso rotto nella pagina; l'uscita 1 viene da 56 pagine preesistenti, nessuna di K.
  >
  > **Fuori pista**:
  > - **`--font-sans` è ora la pila di `html`.** Lo usano solo le 3 schede di accesso (`LoginCard`, `RegisterCard`,
  >   `ForgotPasswordCard`, classe `font-sans`), che adesso seguono il font dell'app.
  >   - Prima avevano il default di Tailwind: `ui-sans-serif, system-ui, …` più le quattro emoji.
  >   - Cambia qualcosa solo su una macchina con Inter installato in locale: l'app non serve Inter come web font.
  > - **Documenti collegati con la regola vecchia, fuori dai file approvati.** Li ho segnalati al coordinator, che alle
  >   13:28 mi ha chiesto di allinearli **dentro il commit b**, solo testo, perché le istruzioni guidano tutti gli agenti:
  >   - `.github/copilot-instructions.md:86`: la faccia `'LF Flags'` al posto di «Noto Color Emoji»;
  >   - `.github/instructions/frontend.instructions.md:52`: la pila vera, più una riga «Flags» con la regola e il gate;
  >   - `knowledge_base/05_project_conventions.md:89-101`: sezione riscritta; prescriveva Noto in testa e «`.emoji-flag`
  >     SOLO ai container bandiera»;
  >   - `knowledge_base/02_frontend.md:45,116`;
  >   - devWiki `domains/layout-settings.md:56`, e in `log.md` la voce di oggi lo nomina.
  >   - Lasciati com'erano, perché storici o datati: `frontend/design/REPORT.md` (report del 24/07), le pagine `sources/`
  >     della devWiki, `features/F-008.md` e `F-098.md`, i piani archiviati. `admin/docker_advanced.*.md:54` resta vero.

## Verifica manuale sui dispositivi (developer)

Serve un server su questa revisione, raggiungibile dal telefono: `dev.py server` ascolta su `0.0.0.0`, quindi
`http://<IP del Mac>:<porta>`. Windows non si emula: la E2E `fx-flag-font` prova il ramo Noto solo con una faccia sonda.

**Bandiere** — su iPhone e Mac (Safari, poi Chrome), e su Windows (Chrome o Edge) se disponibile:

1. Dashboard, le valute (era qui l'«EU» su Windows).
2. Transazioni, colonna della cassa: la bandiera accanto all'importo, e le cifre nel font del testo, non in quello emoji.
3. Un select di valuta, per esempio nel modulo di una transazione o nell'aggiunta di una coppia FX.
4. FX: la lista e un dettaglio.
5. Il selettore della lingua, nell'app e nella schermata di accesso.
6. `/offline.html`, aperto direttamente: la bandiera della lingua.
7. Rete:
   - su Apple, nessun download di `noto-color-emoji.0.woff2`;
   - su Windows, un solo download (~700 KB), e solo sulle pagine con una bandiera.

Atteso: su Apple le bandiere di Apple ovunque, cella della cassa compresa (prima lì c'era Noto); su Windows le bandiere
di Noto, colorate, mai lettere; le altre emoji restano quelle del sistema.

**Titolo della scheda** — in qualunque browser: «LibreFolio» su File, su Strumenti e su `/tools/pac_allocator`, e
tornando da lì alla Dashboard dalla barra laterale.

**Selezione dopo un'operazione** — `/transactions` filtrata su un asset, come nel caso della review:

1. Selezioni tutte le righe → Bulk → Salva: la barra «N selezionati» sparisce e nessuna casella resta spuntata.
2. Lo stesso dopo una modifica, una clonazione, un'eliminazione, un'aggiunta, un'importazione, «Promuovi coppia» e
   «Scollega coppia».
3. Annullando la selezione resta: chiudi il Bulk senza modifiche, scarta le modifiche, annulla la conferma di «Promuovi
   coppia» o di «Scollega coppia».

## Backlog

- **D-b1, bandiere in ECharts** (proprietari dei grafici): ECharts non passa dalle pile globali, quindi su Windows lì le
  bandiere restano lettere. Il canvas disegna con la sua `fontFamily` (default `sans-serif`), e i tooltip HTML hanno un
  `font: … sans-serif` inline (`TooltipHTMLContent.assembleFont`); nel tooltip una bandiera avvolta in `.emoji-flag` è
  coperta.
  - 15 componenti con `echarts.init`:
    - `brokers/lots`: `LotComparisonChart`, `LotGanttChart`, `LotWacPriceChart`;
    - `charts`: `AllocationPieChart`, `CandlestickChart`, `GeographyMap`, `LineChart`, `PriceChartFull`,
      `ScatterChart`, `SemiDonutChart`;
    - `dashboard`: `AllocationHistoryChart`, `ExposureTreemap`, `GrowthChart`, `PerformanceChart`;
    - `risk`: `CorrelationHeatmap`.
  - Dove le bandiere arrivano a ECharts: le legende dei segnali (`FxPairSignal`, `AssetComparisonSignal`,
    `loadComparisonData`), la mappa geografica (`geographyMapHelpers`) e lo storico dell'allocazione.
  - Pista: `textStyle.fontFamily` globale con `'LF Flags'` in testa, che vale per canvas e tooltip, più un
    `document.fonts.load` prima del disegno, perché il canvas non fa scaricare un font.
- **D-b3, nome stabile del file delle bandiere** generato dallo script, al posto dell'indice `.0`.
- **Pile scritte a mano senza `'LF Flags'`**: `CompactCashCell.svelte:166`, `DataTable.svelte:2289`,
  `FilePreviewModal.svelte:1098,1216`, `ImageEditModal`, `FileEditModal`. Una bandiera lì dentro è coperta solo se
  avvolta in `.emoji-flag`.
- **Isolamento di `test_update_js_cache.py`**:
  `TestConsumerScopedFailure::test_an_unattributed_resource_stays_fatal_for_every_consumer[required_for0]` esegue
  l'aggiornamento reale, con la rete, sulle cartelle vere di `frontend/static`.
- **Clonazione di due righe singole dello stesso tipo**: ricevono un `link_uuid` condiviso
  (`TransactionBulkModal.svelte:412`, da `8268a44bb`) e l'editor le mostra come una coppia.
- **«Riprova» della scheda Correlazione**: già girato a Risk dal coordinator.

## Voci di CHANGELOG proposte

- a (🐛 Fixed, «📥 Imports and transaction editing»): «After a saved bulk edit, clone, deletion, addition or import, and
  after linking or unlinking a pair, the Transactions page clears its selection; cancelling keeps it.»
- b (🐛 Fixed): «Country flags render as flags on Windows everywhere, dashboard currencies included, instead of letter
  pairs such as "EU". Apple devices show their own flags everywhere, the transactions cash column included, without
  downloading a flag font.»
- c (🔄 Changed): «The browser tab title stays "LibreFolio" on every page; Files and Tools no longer set their own.» Va
  riconciliata con `CHANGELOG.md:52` di J («Leaving the Files page no longer leaves "Files" as the window title…»), che
  c assorbe: proposta, togliere `:52`.
