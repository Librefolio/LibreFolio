# Piano UI v2: Tab Posizioni & Lotti FIFO (Milestone_3 — Fase 2)

> **Supersede**: [`../plan_ui_broker_holdings.md`](../plan_ui_broker_holdings.md) (disegno originale).
> **Riferimento architetturale**: [`../../phases/phase-09-subplan/Milestone_2/portfolio_engine/ARCHITECTURE_CURRENT_STATE.md`](../../phases/phase-09-subplan/Milestone_2/portfolio_engine/ARCHITECTURE_CURRENT_STATE.md).
> **Fasi correlate**: ← [`plan_ui_broker_overview.md`](./plan_ui_broker_overview.md) (Fase 1, shell tab) ·
> → [`plan_ui_broker_transactions.md`](./plan_ui_broker_transactions.md) (Fase 3).

## Perché un v2

Il disegno originale immaginava una tabella posizioni "semplice" (asset, quantità, costo medio, valore,
P&L, allocazione) da costruire ex novo. Nel frattempo la Dashboard Home ha costruito un **pannello posizioni
molto più ricco** (`PositionsPanel`, 4 viste: Esposizione/Contributo × Tabella/Mappa — la vista Mappa di
Contributo è realizzata da `PerformanceChart.svelte`, un diverging bar chart, **non** un secondo treemap:
la dicitura "ContributionTreemap" usata in una versione precedente di questo piano era imprecisa, corretta
qui) già alimentato dall'endpoint unificato. La parte di dettaglio lotti FIFO (bubble timeline + confronto
WAC/prezzo) resta invece sostanzialmente **come immaginata nel contenuto**, con 2 correzioni emerse nel
raffinamento (2026-07-08/10, vedi §1bis/§1ter/§2): (a) diventa un **pannello inline**, non una modale; (b)
solo la vista `[EUR]` del confronto WAC/prezzo ha davvero solo un gap di routing — la vista `[%]` (TWRR/ROI)
è un gap di **calcolo backend reale, mai implementato** (vedi nota storica sotto, corretta).

> **Nota — non è un gap da "costruire", è una regressione da ripristinare.** Verificato con `git log`:
> la route `GET /portfolio/asset-history` **esisteva** ed era funzionante (aggiunta nel commit `06613074`),
> insieme ai suoi test (`test_unauthenticated`, `test_missing_asset_id`, `test_nonexistent_asset` in
> `test_portfolio_api.py`). È stata rimossa nel commit `3184a9691afbc6f99f0163ef29006fd4090e68d6` ("docs:
> add portfolio engine mathematical model page") insieme ai test — ma quel commit rimuoveva
> **deliberatamente** solo `/summary`, `/history`, `/allocation-history` in quanto superseduti da `/report`
> (lo dice esplicitamente il proprio commento: *"Legacy standalone endpoints (/summary, /history,
> /allocation-history) removed — all data is available via /report"*). `/asset-history` **non** è
> superseduto da `/report` (che non include serie WAC-vs-prezzo per singolo asset) e non è citato in quella
> frase — sembra collateral damage di un unico blocco di diff cancellato tutto insieme. Prova più forte:
> il docstring in cima al file **elenca ancora oggi** `GET /portfolio/asset-history` come endpoint
> disponibile (non è stato aggiornato per rimuoverlo, a differenza degli altri tre), e il metodo di servizio
> `PortfolioService.get_asset_history()` è rimasto intatto e funzionante, orfano. Consigliato: ripristinare
> route + test così com'erano, non riprogettarli.
>
> **Aggiornamento (2026-07-10) — precisazione sul gap `[%]` (TWRR/ROI):** verificato via
> `git log --all -S "class AssetHistoryPoint"` che lo schema è stato introdotto in un solo commit
> (`06613074`) e non più toccato da allora; confrontando il corpo di `get_asset_history()` in quel commit
> (`git show 06613074:backend/app/services/portfolio_service.py`) con quello orfano di oggi, sono
> **identici carattere per carattere**. Conclusione: anche alla nascita dell'endpoint i campi `roi`/`twrr`/
> `mwrr_annualized`/`mwrr_cumulative` erano dichiarati nello schema ma **mai popolati** (sempre `None` per
> assenza di codice, non per rimozione). "Ripristinare route + test così com'erano" resta corretto ma vale
> **solo** per il confronto `[EUR]` (wac/market_price) — il confronto `[%]` richiede lavoro di calcolo
> nuovo, non un ripristino (vedi "Funzionalità da Sviluppare (Backend & API)" sotto).

---

## 1. Wireframe Tab Posizioni

```text
+-------------------------------------------------------------------------------------------------+
|  <- Torna ai Broker                                                                             |
|  [Icon] DIRECTA  (♛ Owner · Quota: 100%)                                    [Share] [↻ Refresh] |
+-------------------------------------------------------------------------------------------------+
|                                                                                                 |
|   [ PANORAMICA ]   [* POSIZIONI *]   [ TRANSAZIONI ]                                            |
|                                                                                                 |
|   +-----------------------------------------------------------------------------------------+   |
|   |  POSIZIONI                        [Esposizione|Contributo]  [Tabella|Mappa] [Aperte|Chiuse]| |
|   |-------------------------------------------------------------------------------------------|  |
|   |  Vista Tabella (Esposizione):                                                             |   |
|   |  +------------+----------+-----------+---------------+-----------------+--------------+   |   |
|   |  | Asset      | Quantità | Costo Med.| Valore Att.   | P&L Non Realiz. | Peso su NAV  |   |   |
|   |  +------------+----------+-----------+---------------+-----------------+--------------+   |   |
|   |  | (Icon) AAPL| 50       | USD 165,00| USD 5.463,00  | +USD 513 (+10%) | 15%          |   |   |
|   |  | (Icon) VWCE| 120      | EUR 98,00 | EUR 14.500,00 | +EUR 450 (+4%)  | 45%          |   |   |
|   |  +------------+----------+-----------+---------------+-----------------+--------------+   |   |
|   |                                                                                             |   |
|   |  ( Vista Mappa: treemap Tipo→Asset. Vista Contributo: P&L di periodo per asset,             |   |
|   |    invece di quantità/costo/valore attuale. )                                              |   |
|   |                                                                                             |   |
|   |  ( Cliccando una riga/tile/barra si apre il pannello dei Lotti FIFO sottostante — §2 )    |   ||   +-----------------------------------------------------------------------------------------+   |
+-------------------------------------------------------------------------------------------------+
```

Note sul disegno:
- Il blocco "POSIZIONI" **è** `PositionsPanel` (`frontend/src/lib/components/dashboard/PositionsPanel.svelte`)
  montato as-is, passandogli `summary`/`contribution` calcolati con `broker_ids: [id]` invece del filtro
  multi-broker globale. I 4 sotto-componenti (`ExposureTable`, `ExposureTreemap`, `ContributionTable`,
  `PerformanceChart` — **corretto qui**: la vista Mappa di Contributo è un diverging bar chart, non un
  secondo treemap, nessun file `ContributionTreemap.svelte` esiste nel codebase) e il toggle Aperte/Chiuse
  sono tutti già scritti e funzionanti — questo tab li eredita gratis, superando l'ambizione originale (che
  prevedeva solo tabella + filtro).
- Colonna "Peso su NAV" = `PortfolioHolding.nav_weight_percent`, già calcolato dal backend (non serve nulla
  di nuovo).
- Il click riga per aprire il pannello Lotti FIFO è l'unica interazione **non** già presente in
  `PositionsPanel` (che oggi linka a `/assets`, non apre pannelli/modali) — meccanismo finale deciso in
  §1ter (click singolo su riga/tile/barra → pannello, dblclick invariato → asset detail).
- **Aggiornamento post-Fase 1** (dopo l'implementazione di Overview): `ExposureTable.svelte`
  (`frontend/src/lib/components/dashboard/ExposureTable.svelte:15,297,318`) è già costruito sopra
  `<DataTable>` e oggi fa `onRowDoubleClick={() => goto('/assets/' + row.assetId)}`. `DataTable.svelte`
  espone già `rowActions` (colonna azioni) ed `enableContextMenu` (default `true`, tasto destro) come
  feature generiche — **zero infrastruttura nuova** per aggiungere una colonna azioni o un context-menu a
  `ExposureTable`/`ContributionTable`, va solo passata la prop.

---

## 1bis. Dove va l'interazione riga → analisi di dettaglio — ✅ deciso (2026-07-08): Opzione A

Con Overview (Fase 1) implementata, il pannello Posizioni del broker detail riusa `PositionsPanel`
1:1 dalla Dashboard — inclusi tutti i toggle e il doppio click che porta ad Asset Detail. Prima di
costruire l'overlay Lotti FIFO di §2, va deciso **dove** questa interazione deve vivere: resta un
modale sopra Broker Detail (disegno originale, invariato), o si sposta come nuovo tab dentro Asset
Detail? Non sono mutuamente esclusive nel lungo periodo, ma per Milestone_3 va scelta una direzione.

### Opzione A — Menu/azione riga in Broker Detail (disegno originale di §2, invariato)

Click riga (o context-menu tasto destro, o icona azione dedicata) apre la modale Lotti FIFO
(bubble timeline + tabelle lotti aperti/chiusi) **restando sulla pagina broker**.

| Pro | Contro |
|-----|--------|
| Contesto broker **gratis** — `broker_id` è già fisso dalla pagina, nessun selettore da costruire | Un altro modale nell'inventario (già numerosi: BrokerModal, DeleteBrokerDialog, BrokerImportFilesModal, TransactionFormModal, FxPairAddModal, ConfirmModal...) |
| `DataTable.navigateToRowId()` ("Goto & Pulse" bolla→riga) naturale in un contenitore autosufficiente (bolle + tabelle nella stessa vista) | Nessuna URL propria — non bookmarkabile, non condivisibile, niente back/forward del browser |
| Riusa `rowActions`/`enableContextMenu` di `DataTable`, già pronti — quasi zero codice nuovo | Se in futuro serve la stessa vista anche da Asset Detail o Dashboard, va ri-arrangiata/duplicata |
| Coerente col disegno Fase 2 già scritto e concordato | — |

### Opzione B — Tab dedicato in Asset Detail, popolato in base all'utente connesso (idea nuova)

Asset Detail (oggi pagina piatta, 2078 righe, nessun tab) acquisisce una struttura a tab — stesso
pattern `TabBar` già costruito per Broker Detail/Dashboard — con un nuovo tab "Lotti FIFO"/analisi,
che si popola solo se/come rilevante per l'utente collegato (es. solo se detiene l'asset).

| Pro | Contro |
|-----|--------|
| URL vera, back/forward funzionante, un solo posto canonico per "tutto sull'asset" indipendentemente da dove si arriva (Broker Detail, Dashboard, ricerca diretta) | **Problema di scoping broker**: `PortfolioService.get_lots(user_id, broker_id, asset_id)` richiede `broker_id` obbligatorio (verificato: `backend/app/services/portfolio_service.py:2003-2008`, non è una lista, non è opzionale) — se lo stesso asset è su più broker, serve un selettore broker che oggi non esiste. Anche `asset-history` è per-broker (broker_id opzionale ma "primo broker accessibile" se omesso — ambiguo con più broker) |
| Coerente col pattern `TabBar` già in uso in Broker Detail/Dashboard — consistenza strutturale in tutta l'app | Refactor più grande e rischioso: Asset Detail è già una pagina densa (2078 righe), molto più corposa di quanto Broker Detail fosse prima di Fase 1 |
| Estendibile in futuro (altre analisi: tecnica, dividendi, confronto) senza un nuovo modale per ciascuna | "Popolato in base all'utente connesso" introduce un pattern di **tab condizionali** mai usato finora — tutti i tab esistenti (Broker/Dashboard) sono sempre visibili a prescindere dai dati |
| — | L'ingresso da una riga di Broker Detail diventerebbe una navigazione a pagina intera (perdita del contesto "leggero" del modale) invece di un overlay istantaneo |

**Deciso (2026-07-08): Opzione A** — resta sopra Broker Detail, aperto dal tab Posizioni (forma esatta del
contenitore raffinata in §1ter/§2, il 2026-07-10: pannello inline, non più modale — la sostanza della
decisione "resta su Broker Detail" è invariata). Opzione B (tab in Asset Detail) scartata per Milestone_3
(coerente con quanto già anticipato in `plan_ui_broker_transactions.md` §"Decisioni prese", punto 1).
Tabelle pro/contro sopra lasciate come riferimento storico.

### 1ter. Meccanismo di apertura da riga/tile/barra — ✅ deciso (2026-07-10)

**Deciso: click singolo → apre il pannello inline di §2 (Opzione 4) · doppio click → resta
`goto('/assets/'+assetId)`, invariato — su tutti e 4 i sotto-componenti di `PositionsPanel`, non solo le
tabelle.** Stato di partenza verificato per ciascuno:

- **`ExposureTable`/`ContributionTable`** (via `<DataTable>`): oggi **solo** `onRowDoubleClick`
  (`ExposureTable.svelte:296-298,318`); `onRowClick` è già una prop esposta da `DataTable` ma **non
  cablata** da nessuno dei due — nessuna regressione da disinnescare. `enableActions`/`enableContextMenu`
  restano disattivati (`ExposureTable.svelte:309,315`, invariato — non serve una colonna azioni per questo).
- **`ExposureTreemap`**: oggi **solo** `dblclick` su leaf-node asset (`ExposureTreemap.svelte:417-423,459`)
  — va aggiunto in parallelo il listener `click` nativo ECharts (stesso `chartInstance.on(...)`, stessa
  guardia `meta?.level === 'asset'`).
- **`PerformanceChart`**: oggi **zero interazione** (verificato via grep: nessun `click`/`dblclick`
  cablato) — va aggiunta da zero, stessa tecnica di `ExposureTreemap` (listener nativo ECharts sulla
  barra), esclusa la sezione "Other period effects" (righe non-asset, nessun lotto da mostrare per loro).
  Richiede una piccola aggiunta al modello dati: `AssetRow` (righe 56-67) non porta oggi un campo `assetId`
  isolato (solo incastonato nella stringa `key`, riga 258) — va aggiunto per un lookup pulito dal
  click-handler.

**Nuova infra condivisa, genuinamente nuova (nessun precedente nel codebase, verificato via grep su
`dblclick`/`clickTimeout`):** un guard click-vs-dblclick (pattern standard: `setTimeout` ~250ms, annullato
se arriva il secondo click entro la finestra) condiviso dai 4 componenti — senza, un doppio click farebbe
comunque lampeggiare il pannello un istante prima di navigare, perché il browser spara sempre l'evento
`click` anche durante la sequenza che porta a un `dblclick`. Da scrivere una volta come utility condivisa
(es. `frontend/src/lib/utils/interaction/clickVsDblClick.ts`), non duplicata 4 volte.

**Opzione 5 (bookmarkabilità) confermata anch'essa**: lo stato "pannello aperto per asset X" va riflesso in
query-param (`?asset=<id>`), stesso pattern già usato da `files/+page.svelte` per `?tab=`
(`history.replaceState`/`goto(newUrl, {replaceState:true, noScroll:true})`, righe 222/236-240) — riuso di
un pattern esistente, non infra nuova.

---

## 2. Pannello Inline — Dettaglio Lotti FIFO

```text
+-----------------------------------------------------------------------------+
|  DETTAGLIO TRANCHE / LOTTI (FIFO) — Apple (AAPL)                       [X]  |
+-----------------------------------------------------------------------------+
|                                                                             |
|   ANDAMENTO WAC E VALORE ASSET  [EUR | %]                                   |
|                                                                             |
|    EUR (o % se attivato: TWRR/ROI)                                          |
|    200 |                                            ****  <- Prezzo Mercato |
|        |                                        ****                        |
|    150 |       ---------------------------------          <- WAC            |
|        |      /                                                             |
|    100 +-----+---------------------------------------------------------->   |
|         Gen   Feb   Mar   Apr   Mag   Giu   Lug   Ago                       |
|                                                                             |
|   +---------------------------------------------------------------------+   |
|                                                                             |
|   RENDIMENTO PER LOTTO DI ACQUISTO (Bubble Timeline)                        |
|                                                                             |
|    Gain (%)                                                                 |
|     +20% |             ( ) Lotto 1 (2026-01-10) — 30 / 100 quote residue    |
|          |            :   : (Il cerchio tratteggiato indica l'orig. 100)    |
|     +10% |                           ( ) Lotto 2 (2026-03-15) — 20 / 20     |
|       0% +------------------------------------------------------------->    |
|     -10% |                                                                  |
|                                                                             |
|   (Click su una bolla -> DataTable.navigateToRowId() sulla tabella lotti    |
|    sottostante: scroll automatico + riga evidenziata per ~2s — "Goto&Pulse")|
|                                                                             |
|   +---------------------------------------------------------------------+   |
|   | LOTTI APERTI RESIDUI (FIFO)                                         |   |
|   +------------+----------+-----------+---------------+-----------------+   |
|   | Data Acq.  | Quantità | Prezzo    | Valore Att.   | P&L Non Realiz. |   |
|   +------------+----------+-----------+---------------+-----------------+   |
|   | 2026-01-10 | 30 / 100 | USD 165,00| USD 5.463,00  | +USD 513 (+10%) |   |
|   | 2026-03-15 | 20 / 20  | USD 180,00| USD 3.642,00  | +USD 42  (+1,1%)|   |
|   +------------+----------+-----------+---------------+-----------------+   |
|                                                                             |
|   +---------------------------------------------------------------------+   |
|   | LOTTI CHIUSI / VENDITE REALIZZATE (FIFO)                            |   |
|   +------------+------------+----------+--------------+-----------------+   |
|   | Data Acq.  | Data Vend. | Quantità | Prezzo Vend. | P&L Realizzato  |   |
|   +------------+------------+----------+--------------+-----------------+   |
|   | 2026-01-10 | 2026-05-20 | 70       | USD 175,00   | +USD 700,00     |   |
|   +------------+------------+----------+--------------+-----------------+   |
|                                                                             |
+-----------------------------------------------------------------------------+
```

Note sul disegno (contenuto invariato nello spirito rispetto all'originale; contenitore e dettagli tecnici
aggiornati nel raffinamento 2026-07-08/10):
- **Contenitore**: non più una modale — il `[X]` in alto a destra nell'ASCII sopra è ora un bottone
  "collassa/chiudi il pannello", non la chiusura di un overlay. Un pannello inline che si apre/chiude
  **sotto** il blocco `PositionsPanel` esistente, nella stessa pagina (Opzione 4, §1ter). Stato
  aperto/chiuso pilotato da query-param `?asset=<id>` (Opzione 5, §1ter), non da un flag locale di modale.
  Transizione apri/chiudi: nessun precedente diretto di `transition:slide` nel codebase (verificato via
  grep) — il precedente più vicino è `transition:fade` per aree collassabili
  (`BrokerImportFilesModal.svelte`, area upload). `slide` di `svelte/transition` (già una dipendenza core
  di Svelte, solo prima adozione di questo specifico transition) è la scelta naturale per un pannello che
  spinge il contenuto sotto, non `fade`.
- Il grafico WAC vs valore era già pensato per un endpoint dedicato (per non appesantire lo schema di
  `/portfolio/history`) — quell'endpoint **esiste lato service** ma non è ancora raggiungibile via HTTP per
  la vista `[EUR]` (vedi "Funzionalità da Sviluppare" sotto). La vista `[%]` è un gap di calcolo diverso, non
  solo di routing. **Raccomandazione** (da confermare con l'utente, non ancora implementata in nessun
  verso): nello switch mostrare solo `[EUR | %]` dove `%` = ROI+TWRR (entrambi da calcolare, vedi sotto) e
  **droppare `mwrr_annualized`/`mwrr_cumulative`** da questo grafico — un solver Newton per-asset per un
  solo "investitore" aggiunge complessità senza portare informazione che ROI+TWRR non diano già per un
  singolo asset (rispondono già a "quanto ha reso l'asset"/"quanto ho guadagnato io").
- Le due tabelle Lotti Aperti/Chiusi mappano **esattamente** i campi già restituiti da
  `GET /portfolio/lots` (nessun gap): `OpenLotSchema` (buy_date, buy_price, original/remaining_quantity,
  unrealized_pnl) e `ClosedLotSchema` (buy_date, sell_date, quantity, buy/sell_price, realized_pnl).
- L'interazione "Goto & Pulse" bolla→riga **non va costruita da zero**: `DataTable.svelte` espone già un
  metodo pubblico `navigateToRowId(rowId)` ("Reusable: called from DataEditor's Add Row, chart point
  click, etc.") che pagina, scrolla (`scrollIntoView`) ed evidenzia (classe CSS `.highlighted`) la riga.
  Basta montare le due tabelle lotti come `<DataTable>` e richiamare questo metodo dal click-handler della
  bubble chart.

---

## Requisiti Dati Frontend

### Funzionalità Esistenti (da riutilizzare così come sono)

* **`PositionsPanel` e sotto-componenti** (`frontend/src/lib/components/dashboard/`): `ExposureTable`,
  `ExposureTreemap`, `ContributionTable`, `PerformanceChart` — toggle Esposizione/Contributo,
  Tabella/Mappa, Aperte/Chiuse tutti già funzionanti, alimentati da `summary.holdings` e
  `positions_contribution` del `/portfolio/report` scoped a `broker_ids: [id]`.
* **`GET /portfolio/lots`** (`backend/app/api/v1/portfolio_api.py`, già montato) — `PortfolioService.get_lots()`
  restituisce `open_lots`/`closed_lots`/`total_realized_pnl`/`total_unrealized_quantity` per
  `(broker_id, asset_id)`. Nessuna modifica richiesta.
* **`<DataTable>`** (`frontend/src/lib/components/table/DataTable.svelte`) — per entrambe le tabelle lotti:
  sorting integrato gratis, e soprattutto il metodo pubblico `navigateToRowId()` per il "Goto & Pulse".
* **`svelte/transition` (`slide`)**: già una dipendenza core di Svelte, solo prima adozione nel codebase per
  questo pattern specifico (pannello che apre/chiude spingendo il contenuto sotto) — nessun nuovo package.

### Funzionalità da Sviluppare (Backend & API)

* **(a) `GET /portfolio/asset-history` — vista `[EUR]`, da ripristinare, non da progettare** (vedi nota
  storica sopra). Il metodo `PortfolioService.get_asset_history()` esiste già intatto
  (`backend/app/services/portfolio_service.py:1953`) e produce già `date`/`wac`/`market_price` — basta
  reintrodurre la route rimossa nel commit `3184a969` (stesso path/firma di allora: `GET
  /portfolio/asset-history?asset_id=...&broker_id=...`, `broker_id` opzionale — il metodo usa il primo
  broker accessibile se omesso, ma per lo scope di questa pagina va sempre passato il broker corrente) e i
  relativi test rimossi nello stesso commit. **Nessuna dipendenza da (b)** — la vista `[EUR]` funziona da
  sola una volta ripristinata la route.
* **(b) Vista `[%]` (ROI/TWRR) — gap di calcolo reale, non di routing.** Verificato: `roi`/`twrr`/
  `mwrr_annualized`/`mwrr_cumulative` sono dichiarati in `AssetHistoryPoint`
  (`backend/app/schemas/portfolio.py:437-446`) ma **mai stati popolati**, nemmeno alla nascita
  dell'endpoint (commit `06613074`, confrontato via `git show` — il corpo del metodo è identico carattere
  per carattere a quello orfano di oggi). Non serve costruire la matematica da zero:
  `calculate_twrr_series`/`calculate_mwrr_series` (`backend/app/utils/financial/roi_utils.py:207,299`) sono
  già generici (`list[NAVSnapshot]` + `list[CashFlowInput]`, nessuna assunzione "portfolio" nel tipo) —
  vanno solo alimentati con serie per-asset dentro `get_asset_history()`: `NAVSnapshot.nav` = quantità
  posseduta alla data × `market_price` (non NAV di portafoglio), `CashFlowInput` = transazioni BUY (importo
  negativo)/SELL (importo positivo) di quell'asset. **Raccomandazione** (da confermare con l'utente):
  calcolare solo `roi` (già esiste `calculate_simple_roi`, stesso file) + `twrr`, **droppare
  `mwrr_annualized`/`mwrr_cumulative`** per questo grafico specifico (solver Newton per-asset a basso
  valore informativo aggiunto, vedi §2) — se confermato, rimuovere anche i 2 campi da `AssetHistoryPoint`
  invece di lasciarli sempre `None`.

### Funzionalità da Sviluppare (Frontend)

* **Componente "Bubble Timeline"** per il rendimento per lotto — nuovo, nessun grafico ECharts esistente ha
  questa forma (bolla = lotto, x = data acquisto, y = gain%, dimensione/tratteggio = quota residua vs
  originale). **Pronto lato dati**: `unrealized_pnl`/`realized_pnl` di `GET /portfolio/lots` sono già in
  valuta nativa asset (nessuna conversione target-currency mescolata, verificato in
  `portfolio_service.py:2061-2089`) — gain% derivabile lato frontend senza altro dato backend.
* **Componente "Stacked Line WAC vs Prezzo"** con switch `[EUR | %]` — nuovo, consuma i dati dell'endpoint
  `asset-history` (vista `[EUR]` pronta dopo backend (a); vista `[%]` pronta dopo backend (b)).
* **Guard click-vs-dblclick condiviso** (nuova utility, vedi §1ter) — usato da `ExposureTable`,
  `ContributionTable`, `ExposureTreemap`, `PerformanceChart`.
* **Click singolo su riga/tile/barra → apre il pannello** (query-param `?asset=<id>`, §1ter/§2); doppio
  click resta/diventa `goto('/assets/'+assetId)` (invariato su Tabella+Mappa Esposizione, nuovo su
  `PerformanceChart`). `PerformanceChart` richiede in più un campo `assetId` isolato su `AssetRow` (oggi
  solo incastonato nella stringa `key`) e il primo listener `click`/`dblclick` nativo ECharts di questo
  componente (oggi zero interazione).
* **Pannello inline apri/chiudi** con `transition:slide` (prima adozione nel codebase, vedi §2) — sostituisce
  il concetto di "modale" del disegno originale.
* **Collegamento bubble→tabella** tramite `navigateToRowId()` (vedi sopra) — solo cablaggio, non nuova
  infrastruttura.

---

## 3. Ordine di implementazione e dipendenze (aggiunto 2026-07-10)

```text
STEP 1 (Backend, indipendenti tra loro)
 ├─ 1a. Ripristino GET /portfolio/asset-history — vista [EUR] (wac/market_price)
 └─ 1b. Calcolo roi/twrr in get_asset_history() — vista [%] (bloccata su conferma utente: calcolare
        solo roi+twrr, droppare mwrr_annualized/mwrr_cumulative — vedi §2)
         │
STEP 2 (Frontend, infra condivisa — nessuna dipendenza da Step 1)
 ├─ 2a. Guard click-vs-dblclick condiviso (nuova utility)
 ├─ 2b. Query-param ?asset=<id> per stato pannello (pattern files/+page.svelte, riuso)
 └─ 2c. Campo assetId isolato su PerformanceChart::AssetRow
         │
         ▼
STEP 3 (Frontend, cablaggio click — dipende da 2a, 2c)
 ├─ 3a. ExposureTable/ContributionTable: onRowClick → apri pannello (dblclick invariato)
 └─ 3b. ExposureTreemap/PerformanceChart: click nativo ECharts → apri pannello (dblclick
        invariato su Treemap, nuovo su PerformanceChart)
         │
         ▼
STEP 4 (Frontend, componenti grafico — Bubble indipendente da Step 1; WAC/Prezzo dipende da Step 1)
 ├─ 4a. Bubble Timeline (rendimento per lotto) — dipende solo da GET /portfolio/lots, già pronto
 │      oggi, può partire il giorno 1 insieme a Step 1/2
 └─ 4b. Stacked Line WAC vs Prezzo [EUR|%] — vista [EUR] dipende da 1a, vista [%] dipende da 1b
         │
         ▼
STEP 5 (Frontend, contenitore — punto di convergenza, dipende da 2b + almeno un ramo di Step 3 e Step 4)
 └─ Pannello inline (apri/chiudi via query-param, transition:slide) + le 2 tabelle Lotti
    Aperti/Chiusi (<DataTable>, dati già pronti da GET /portfolio/lots) + collegamento
    bubble→tabella (navigateToRowId(), "Goto & Pulse")
         │
         ▼
STEP 6 — i18n (./dev.py i18n audit)
```

Note di dipendenza:
- **Step 1 e Step 2 sono completamente paralleli** (nessuna dipendenza incrociata) — possono partire
  insieme, anche da sessioni/persone diverse.
- **Step 4a (Bubble Timeline) non dipende da alcun lavoro backend nuovo** — `GET /portfolio/lots` è già
  montato e invariato, può partire il giorno 1 insieme a Step 1/2, senza attendere nulla.
- **Step 4b (WAC/Prezzo) è l'unico blocco realmente sequenziale sul backend**: la vista `[EUR]` si sblocca
  dopo 1a (banale, ripristino puro), la vista `[%]` dopo 1b (lavoro nuovo, da confermare) — se 1b viene
  rimandato o scartato, 4b esce comunque con solo `[EUR]` e `[%]` si aggiunge dopo senza rework del
  componente (lo switch va solo esteso, non ridisegnato).
- **Step 5 è l'unico vero punto di convergenza**: non si chiude prima che 2b (query-param) e almeno un ramo
  di Step 3 (click da almeno un componente) e Step 4 (almeno Bubble Timeline) siano pronti — ma i 3 rami
  (2/3/4) restano sviluppabili in parallelo fino a quel punto.
- Dopo ogni modifica di schema/endpoint backend (Step 1): `./dev.py api sync` prima di toccare il frontend
  che li consuma (Step 4b).
- **Decisione bloccante prima di partire con Step 1b**: confermare con l'utente il drop di
  `mwrr_annualized`/`mwrr_cumulative` (vedi §2) — cambia lo scope di 1b da "4 metriche" a "2 metriche".
