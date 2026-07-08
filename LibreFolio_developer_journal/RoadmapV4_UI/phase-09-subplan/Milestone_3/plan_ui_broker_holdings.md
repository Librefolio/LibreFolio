# Piano UI v2: Tab Posizioni & Lotti FIFO (Milestone_3 — Fase 2)

> **Supersede**: [`../plan_ui_broker_holdings.md`](../plan_ui_broker_holdings.md) (disegno originale).
> **Riferimento architetturale**: [`../../phases/phase-09-subplan/Milestone_2/portfolio_engine/ARCHITECTURE_CURRENT_STATE.md`](../../phases/phase-09-subplan/Milestone_2/portfolio_engine/ARCHITECTURE_CURRENT_STATE.md).
> **Fasi correlate**: ← [`plan_ui_broker_overview.md`](./plan_ui_broker_overview.md) (Fase 1, shell tab) ·
> → [`plan_ui_broker_transactions.md`](./plan_ui_broker_transactions.md) (Fase 3).

## Perché un v2

Il disegno originale immaginava una tabella posizioni "semplice" (asset, quantità, costo medio, valore,
P&L, allocazione) da costruire ex novo. Nel frattempo la Dashboard Home ha costruito un **pannello posizioni
molto più ricco** (`PositionsPanel`, 4 viste: Esposizione/Contributo × Tabella/Mappa) già alimentato
dall'endpoint unificato. La parte di dettaglio lotti FIFO (modale con bubble timeline + confronto WAC/prezzo)
resta invece sostanzialmente **come immaginata**, perché lo schema dati che serviva (`AssetHistoryPoint`) è
già stato scritto nel backend — solo la route HTTP che lo espone manca.

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
|   |  ( Cliccando una riga si apre l'overlay dei Lotti FIFO sottostante — §2 )                  |   |
|   +-----------------------------------------------------------------------------------------+   |
+-------------------------------------------------------------------------------------------------+
```

Note sul disegno:
- Il blocco "POSIZIONI" **è** `PositionsPanel` (`frontend/src/lib/components/dashboard/PositionsPanel.svelte`)
  montato as-is, passandogli `summary`/`contribution` calcolati con `broker_ids: [id]` invece del filtro
  multi-broker globale. I 4 sotto-componenti (`ExposureTable`, `ExposureTreemap`, `ContributionTable`,
  `ContributionTreemap`) e il toggle Aperte/Chiuse sono tutti già scritti e funzionanti — questo tab li
  eredita gratis, superando l'ambizione originale (che prevedeva solo tabella + filtro).
- Colonna "Peso su NAV" = `PortfolioHolding.nav_weight_percent`, già calcolato dal backend (non serve nulla
  di nuovo).
- Il click riga per aprire l'overlay Lotti FIFO è l'unica interazione **non** già presente in
  `PositionsPanel` (che oggi linka a `/assets`, non apre modali) — va aggiunto un handler `onRowClick` che
  apre la modale di §2 passando `broker_id` (fisso, quello della pagina) + `asset_id` (dalla riga cliccata).
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

**Deciso (2026-07-08): Opzione A** — resta un modale sopra Broker Detail, aperto dal tab Posizioni.
Opzione B (tab in Asset Detail) scartata per Milestone_3 (coerente con quanto già anticipato in
`plan_ui_broker_transactions.md` §"Decisioni prese", punto 1). Tabelle pro/contro sopra lasciate come
riferimento storico.

### 1ter. Sotto-decisione aperta: come si apre il modale dalla riga/tile

Confermata l'Opzione A, resta da scegliere il meccanismo di innesco. Stato di partenza: `ExposureTable`/
`ContributionTable` e `ExposureTreemap` hanno oggi **solo** il doppio click → `goto('/assets/'+assetId)`
(`ExposureTable.svelte:296-298`, `ExposureTreemap.svelte:417-423`), invariato dalla Dashboard; su
`ExposureTable` sia `enableActions` sia `enableContextMenu` sono oggi **disattivati**
(`ExposureTable.svelte:309,315`). In discussione con l'utente, in attesa di conferma finale — vedi thread
di refinement per il confronto completo delle opzioni.

---

## 2. Modale Overlay — Dettaglio Lotti FIFO

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

Note sul disegno (invariato nello spirito rispetto all'originale, con dettagli tecnici aggiornati):
- Il grafico WAC vs valore era già pensato per un endpoint dedicato (per non appesantire lo schema di
  `/portfolio/history`) — quell'endpoint **esiste lato service** ma non è ancora raggiungibile via HTTP
  (vedi "Manca" sotto). Lo switch `[EUR | %]` resta valido: lo schema `AssetHistoryPoint` include sia i
  valori assoluti (`wac`, `market_price`) sia le metriche percentuali (`roi`, `twrr`, `mwrr_*`).
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
  `ExposureTreemap`, `ContributionTable`, `ContributionTreemap` — toggle Esposizione/Contributo,
  Tabella/Mappa, Aperte/Chiuse tutti già funzionanti, alimentati da `summary.holdings` e
  `positions_contribution` del `/portfolio/report` scoped a `broker_ids: [id]`.
* **`GET /portfolio/lots`** (`backend/app/api/v1/portfolio_api.py`, già montato) — `PortfolioService.get_lots()`
  restituisce `open_lots`/`closed_lots`/`total_realized_pnl`/`total_unrealized_quantity` per
  `(broker_id, asset_id)`. Nessuna modifica richiesta.
* **`<DataTable>`** (`frontend/src/lib/components/table/DataTable.svelte`) — per entrambe le tabelle lotti:
  sorting integrato gratis, e soprattutto il metodo pubblico `navigateToRowId()` per il "Goto & Pulse".
* **Overlay/Modale**: il wrapper modale generico usato altrove nell'app è riusabile per il contenitore
  dell'intera vista Lotti FIFO.

### Funzionalità da Sviluppare (Backend & API)

* **`GET /portfolio/asset-history` — da ripristinare, non da progettare** (vedi nota storica sopra). Il
  metodo `PortfolioService.get_asset_history()` esiste già intatto (`backend/app/services/
  portfolio_service.py:1849`) e produce esattamente la serie `AssetHistoryPoint` (date, wac, market_price,
  roi, twrr, mwrr_annualized, mwrr_cumulative) che serve al grafico WAC-vs-prezzo — basta reintrodurre la
  route rimossa nel commit `3184a969` (stesso path/firma di allora: `GET /portfolio/asset-history?asset_id=
  ...&broker_id=...`, `broker_id` opzionale — il metodo usa il primo broker accessibile se omesso, ma per lo
  scope di questa pagina va sempre passato il broker corrente) e i relativi test rimossi nello stesso commit.

### Funzionalità da Sviluppare (Frontend)

* **Componente "Bubble Timeline"** per il rendimento per lotto — nuovo, nessun grafico ECharts esistente ha
  questa forma (bolla = lotto, x = data acquisto, y = gain%, dimensione/tratteggio = quota residua vs
  originale).
* **Componente "Stacked Line WAC vs Prezzo"** con switch `[EUR | %]` — nuovo, consuma i dati dell'endpoint
  `asset-history` una volta ripristinato.
* **Handler di apertura modale** da riga `PositionsPanel` → Lotti FIFO (`onRowClick` con `asset_id` +
  `broker_id` fisso di pagina) — cablaggio nuovo ma banale, nessuna nuova infrastruttura.
* **Collegamento bubble→tabella** tramite `navigateToRowId()` (vedi sopra) — solo cablaggio, non nuova
  infrastruttura.
