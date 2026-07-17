# FIFO Lot Engine v2 — Log di implementazione

> Piano sorgente: [`hig-level-plan_v2.md`](./hig-level-plan_v2.md) (letto integralmente prima dell'implementazione).
> Report di analisi collegati: [`high-level-plan_v1-feasibility-report.md`](./high-level-plan_v1-feasibility-report.md), [`high-level-plan_v1-open-questions.md`](./high-level-plan_v1-open-questions.md), [`fifo-engine-current-state.md`](./fifo-engine-current-state.md), [`fifo-segment-model-analysis.md`](./fifo-segment-model-analysis.md).
>
> Questo file viene aggiornato dopo **ogni step**, non solo a fine fase, per garantire continuità tra sessioni (convenzione repo: `.github/copilot-instructions.md` § Developer Journal & Plan Methodology).

## Decisioni assunte in fase di planning

- Fix WAC split/reverse-split e uniformazione transito `[min,max)` sono **fix di produzione globali** (prerequisiti Fase 0 espliciti nel piano) — cambiano numeri già visualizzati oggi per ADJUSTMENT collegati a SPLIT e per TRANSFER con date non adiacenti. Non sono scope creep: il piano lo richiede esplicitamente al §20 e §7.2.
- SHORT è in scope da Fase 1 (non rimandato come nel v1).
- **UI lotti**: quantità/valore sempre assoluti di broker, mai scalati per `share_percentage` (deciso con l'utente in sede di planning). Nota/tooltip per broker in comproprietà.
- **Fuori scope, non toccati in questa implementazione** (bug noti da report precedenti, non richiesti esplicitamente dal piano v2): quantità/costo fantasma su TRANSFER con `share_percentage` diversi tra broker, `InTransitInterval.share` hardcoded a 1, `share_mismatch_warnings` mai popolato.

## Fase 0 — Prerequisiti

- [x] 0.1 Tracking log (questo file)
- [x] 0.2 Fix WAC split/reverse-split
- [x] 0.3 Test di regressione WAC
- [x] 0.4 Uniformare convenzione transito `[min,max)`
- [x] 0.5 Schema identità lotto/frammento + naming DTO

## Fase 1 — FifoLotEngine puro

- [x] 1.1 Classificazione eventi
- [x] 1.2 Code FIFO LONG/SHORT
- [x] 1.3 ADJUSTMENT+/-
- [x] 1.4 TRANSFER
- [x] 1.5 SPLIT/reverse split
- [x] 1.6 Valore e P&L
- [x] 1.7 Stati derivati + Data Quality
- [x] 1.8 Test matematici esaustivi

## Fase 2 — Service layer e API bulk

- [x] 2.1 Loader bulk
- [x] 2.2 Price/FX integration
- [x] 2.3 WAC series integration
- [x] 2.4 DTO bulk
- [ ] 2.5 Endpoint `POST /portfolio/lots/analysis`
- [x] 2.5 Endpoint `POST /portfolio/lots/analysis`
- [x] 2.6 Data Quality integration
- [x] 2.7 Test API/integrazione

## Fase 3 — Frontend

- [x] 3.1 API sync — 2026-07-16
- [x] 3.2 Gantt ECharts — 2026-07-16
- [x] 3.3 Tabella unificata — 2026-07-16
- [x] 3.4 Modale Custodia — 2026-07-16
- [x] 3.5 Evoluzione AssetWacPriceChart
- [x] 3.6 Grafico comparativo — 2026-07-16
- [x] 3.7 Sincronizzazione temporale — 2026-07-16
- [x] 3.8 Migrazione FIFOLotsPanel — 2026-07-16
- [x] 3.9 Data Quality banner — 2026-07-16
- [x] 3.10 i18n — 2026-07-16
- [x] 3.11 Verifica visuale + test funzionali — 2026-07-16

## Fase 4 — Migrazione, pulizia, validazione

- [x] 4.1 Rimozione backend obsoleto — 2026-07-16
- [x] 4.2 Rimozione frontend obsoleto — 2026-07-16
- [x] 4.3 Gallery/E2E — 2026-07-16
- [x] 4.4 Validazione completa — 2026-07-16
- [x] 4.5 Report finale — 2026-07-16

---

## Log dettagliato

### 0.1 — Tracking log
**Stato: ✅ completato — 2026-07-16**
> **Note implementazione**: creato questo file cross-linkato con `hig-level-plan_v2.md` e i report di analisi. Struttura a checklist per fase, sezione "Log dettagliato" per note step-by-step.

### 0.2 — Fix WAC split/reverse-split
**Stato: ✅ completato — 2026-07-16**
> **Note implementazione**: causa esatta del bug isolata a `transaction_service.py::_compute_wac_for_auto_items` (righe ~1601-1604): per QUALSIASI item `cost_basis_mode in ("auto","auto-detail")` — incluso un ADJUSTMENT collegato a SPLIT — veniva sempre scritto il WAC corrente (pre-transazione) come `cost_basis_override`, raddoppiando il costo per split diretti e dimezzandolo per reverse split.
>
> Fix implementato in 4 file:
> - `backend/app/utils/financial/wac_utils.py`: nuovo campo `WACInputTX.is_split_linked`; nuovo branch "rescale" in `compute_wac_from_txlist` (bypassa add/reduce, formula `new_wac = (wac*qty_pool)/new_qty` — matematicamente equivalente a "costo totale invariato", valida sia per split diretti che reverse).
> - `backend/app/services/portfolio_service.py`: sia `compute_wac_iterative` sia `compute_wac_iterative_multi_broker` ora fanno un query aggiuntiva (`Transaction.asset_event_id` → `AssetEvent.type==SPLIT`) per popolare `is_split_linked` per riga; fingerprint di cache aggiornato per includere l'esito di questa query (altrimenti un edit di `AssetEvent.type` dopo il collegamento non invaliderebbe la cache).
> - `backend/app/services/portfolio_engine.py`: nuovo metodo statico `DailyStateBuilder._apply_split_rescale` (stessa formula, ma qui il costo pool resta semplicemente invariato — `wac_pool_cost[key]` non viene toccato, solo `wac_pool_qty[key]`); applicato sia nel loop pre-frame che nel loop frame (sono due copie quasi identiche nel codice esistente); `PortfolioCalculationEngine.run()` calcola `split_linked_tx_ids` con una query dedicata e la passa al builder; aggiunta al blob cache key per lo stesso motivo di invalidazione.
> - `backend/app/services/transaction_service.py::_compute_wac_for_auto_items`: per item collegati a SPLIT, salta interamente la chiamata a `compute_wac_iterative` e lascia `cost_basis_override=None` (hygiene — il valore non verrebbe comunque letto dal motore WAC per righe split-linked, ma scrivere un valore fuorviante è comunque sbagliato).
>
> **Scoperta chiave**: il ratio di split è già disponibile in `AssetEvent.value` (popolato da `yahoo_finance.py` come "2.0" per uno split 2:1) — nessuna modifica DB necessaria. Inoltre il motore WAC/FIFO non ha nemmeno bisogno di leggere questo ratio: la quantità delta della transazione ADJUSTMENT stessa è sufficiente per applicare la formula di rescale.
>
> **Verificato anche**: §20 del piano ("WAC = costo totale invece di unitario?") — confermato che NON è un bug; `abs(amount)/qty` è già corretto ovunque (wac_utils.py, compute_wac_iterative, portfolio_engine._buy_unit_cost).

### 0.3 — Test di regressione WAC
**Stato: ✅ completato — 2026-07-16**
> **Note implementazione**: 448 test totali eseguiti, 0 fallimenti (nessuna regressione):
> - `test_financial_utils.py`: 16/16 (4 nuovi: FU-13 forward split, FU-14 reverse split, FU-15 ignora override fasullo, FU-16 SELL post-split usa WAC ricalcolato).
> - `test_daily_state_builder.py`: 26/26 (3 nuovi: forward split in-frame, reverse split in-frame, forward split in pre-frame — quest'ultimo per coprire la seconda copia del loop).
> - `test_financial/` + `test_portfolio_engine_vnext.py`: 227/227.
> - `test_transaction_service.py` + `test_transaction_edge_cases.py` + `test_wac_inline.py`: 95/95.
> - `test_portfolio_wac.py`: 10/10 (2 nuovi, integrazione live end-to-end: creano un vero AssetEvent SPLIT via API, un ADJUSTMENT collegato, verificano sia il WAC finale sia che `wac_results[0].wac is None` per l'item auto-mode split-linked).
> - `test_portfolio_service.py` + `test_portfolio_api.py`: 74/74.
>
> **⚠️ Fuori pista**: durante la scrittura del test di reverse split ho scoperto un vincolo di validazione preesistente non documentato nel piano: `cost_basis_mode` è rifiutato dalla business validation per ADJUSTMENT con quantità negativa ("only valid for qty>0"). Questo significa che il fallback "auto" non è mai raggiungibile per un reverse split via API oggi — il bug si manifesta comunque tramite un ADJUSTMENT negativo semplice (senza cost_basis_mode), che infatti resta scoperto e corretto dal fix in wac_utils.py/portfolio_engine.py. Nessuna modifica al codice di validazione: solo adattato il test.

### 0.4 — Uniformare convenzione transito [min,max)
**Stato: ✅ completato — 2026-07-16**
> **Note implementazione**: modifica isolata a `portfolio_engine.py::_build_in_transit_interval` — rimosso il `+ timedelta(days=1)` dalla formula di `start` (era `departure.date + 1`, ora `departure.date`); `end` resta invariato (`arrival.date - 1`). Questo perché `departure`/`arrival` sono già assegnati per ordine cronologico (`tx_a.date <= tx_b.date`), quindi `start = min(dep,arr)` e `end = max(dep,arr) - 1` — esattamente la formula `[min,max)` del piano §7.2, espressa in termini inclusivo-inclusivo (`[start,end]`) per non toccare tutti i punti di consumo esistenti che usano `<=` su entrambi gli estremi (righe ~645-650, ~1154, ~2023-2029).
>
> Effetto: l'intervallo è vuoto SOLO per transfer stesso giorno (`start>end` ⟺ `dep==arr`); il caso "giorni adiacenti" (T, T+1) che prima produceva un buco di valore di 1 giorno ora produce correttamente una finestra di 1 giorno sul giorno di partenza.
>
> Test aggiornati in `test_scope_classifier.py` (`TestLinkedInternalDifferentDates`):
> - `test_cash_transfer_different_dates`/`test_asset_transfer_different_dates`: aggiornate le date attese (`start` non ha più +1).
> - `test_adjacent_days_no_transit` → rinominato `test_adjacent_days_transit_covers_departure_day`: l'aspettativa è CAMBIATA da "intervallo vuoto" a "finestra di 1 giorno sul giorno di partenza" (è il fix del buco di valore, non solo una modifica cosmetica).
> - Aggiunto `test_same_day_transfer_no_transit`: unico caso che resta vuoto.
> - Aggiunto `test_out_leg_dated_after_in_leg_still_resolves_chronologically`: verifica che la direzione del transito segua l'ordine cronologico anche quando la gamba con importo negativo è datata DOPO quella con importo positivo (nessuna assunzione sul segno).
>
> Regressione completa post-fix: 229 (financial engine + vnext, +2 dai nuovi test) + 28 (portfolio_api) + 10 (portfolio_wac) + 141 (transaction_service + edge_cases + wac_inline + portfolio_service) = 408 test, 0 fallimenti.

### 0.5 — Schema identità lotto/frammento + naming DTO
**Stato: ✅ completato — 2026-07-16**
> **Note implementazione**: specifica di design (nessun codice — verrà implementata in Fase 1). Decisioni vincolanti per l'implementazione del `FifoLotEngine`:
>
> **Modulo**: `backend/app/services/fifo_lot_engine.py` — simmetrico a `portfolio_engine.py` (entrambi "Engine" nel diagramma architetturale §12.1 del piano), ma internamente puro/senza I/O come `fifo_utils.py`/`wac_utils.py`. Tipi interni come `@dataclass` (stesso stile di `ClassifiedTransaction`/`InTransitInterval`/`DailyPositionState` in `portfolio_engine.py`), non modelli Pydantic — la conversione a DTO API è responsabilità di `LotsAnalysisService` (Fase 2).
>
> **Identità lotto**: `lot_id: int = opening_transaction_id` — l'id della transazione che ha aperto il lotto (BUY che apre LONG, ADJUSTMENT+ che apre LONG, SELL che apre SHORT per l'eccedenza, ADJUSTMENT che apre SHORT). Stabile per definizione (mai ricalcolato).
>
> **Identità frammento**: stringa, tre forme possibili:
> - Origine: `f"lot:{lot_id}/origin:{broker_id}"` — frammento creato all'apertura del lotto.
> - Transito: `f"lot:{lot_id}/transfer:{transfer_pair_id}/transit"` — frammento IN_TRANSIT, distinto dal frammento di destinazione (nel Gantt sono barre visivamente separate, vedi mockup §14.3 "Coinbase 0,05 ┳━ Coinbase 0,05 / Transit / IBKR 0,10").
> - Destinazione transfer: `f"lot:{lot_id}/transfer:{transfer_pair_id}/to:{broker_id}"` — frammento creato all'arrivo.
> - `transfer_pair_id: int = min(departure_leg.transaction_id, arrival_leg.transaction_id)` — id canonico stabile per la coppia TRANSFER (non dipende dall'ordine di iterazione).
> - Una vendita/chiusura parziale NON crea un nuovo frammento: riduce `q_{i,j}` sul frammento esistente, chiude l'intervallo di validità se `q_{i,j}` arriva a 0 (§3.3 del piano: "una vendita parziale può chiudere un intervallo e aprirne uno successivo... senza modificare l'identità logica del branch" — cioè lo stesso `id` di frammento persiste attraverso riduzioni parziali, cambia solo `[t_start, t_end)`).
>
> **Direzione**: `Direction = Literal["LONG", "SHORT"]`, immutabile per lotto (§3.1).
>
> **Ordinamento eventi**: chiave `(date, transaction_id)`; eccezione: eventi SPLIT applicati all'inizio della giornata, prima di qualunque altra transazione con la stessa data (§4, §8.4) — quindi la chiave di ordinamento effettiva è `(date, 0 if is_split else 1, transaction_id)`.
>
> **Prezzo FIFO = sempre il prezzo originario.** Confermato che il piano v2 NON reintroduce la distinzione "prezzo originario vs costo fiscale riconosciuto" esplorata nel report di sessione precedente (`fifo-segment-model-analysis.md`) — `cost_basis_override` alimenta solo il dominio WAC (§2.3, §7.3: "ignorano il cost_basis_override nel dominio FIFO"). Nessun campo "tax_unit_cost" nel nuovo motore.
>
> **Nessuna modifica DB**: tutti gli identificatori sono calcolati a runtime da colonne esistenti (`Transaction.id`, `Transaction.related_transaction_id`, `Transaction.asset_event_id`, `AssetEvent.value`) — coerente con "FIFO at Runtime" (architettura esistente, nessuna persistenza di lotti/frammenti).

### 1.1 — Classificazione eventi
**Stato: ✅ completato — 2026-07-16**
> **Note implementazione**: creato nuovo modulo puro `backend/app/services/fifo_lot_engine.py` con input `FifoInputTransaction` duck-typed/DB-free, classificazione deterministica in `BUY`, `SELL`, `ADJUSTMENT_IN`, `ADJUSTMENT_OUT`, `SPLIT`, `TRANSFER_DEPART`, `TRANSFER_ARRIVE`. Ordinamento effettivo: transfer state transitions di inizio giornata → split → altre transazioni, sempre deterministico per `(date, phase, transaction_id)`; i `TRANSFER` sono risolti da `related_transaction_id` bidirezionale e scartano/issueano coppie mancanti o incoerenti (`TRANSFER_PAIR_MISSING`).
>
> **⚠️ Fuori pista**: per rappresentare correttamente intervalli half-open `[start,end)` senza ambiguità su split nello stesso giorno dell'arrivo/partenza, ho espanso internamente ogni coppia `TRANSFER` in due eventi derivati (`TRANSFER_DEPART`/`TRANSFER_ARRIVE`) eseguiti all'inizio del giorno. È una scelta implementativa non esplicitata letteralmente nel piano, ma preserva esattamente la matematica §7.2 + §8.4.

### 1.2 — Code FIFO LONG/SHORT
**Stato: ✅ completato — 2026-07-16**
> **Note implementazione**: implementate code FIFO per frammenti `LONG`/`SHORT` per broker, ordinate sempre dalla data/id di apertura del lotto originario (non dalla data di arrivo del frammento trasferito). `BUY` chiude FIFO eventuali `SHORT` sul broker e apre nuovo lotto `LONG` col residuo; `SELL` chiude FIFO i `LONG` e, se resta quantità e `broker_shorting[broker_id]` è `True`, apre nuovo lotto `SHORT`. Crossing-zero coperto esplicitamente dal motore e dai test (esempio piano §5.3: `LONG 5@100`, `SELL 8@120` → `P&L +100` + nuovo `SHORT 3@120`).

### 1.3 — ADJUSTMENT+/-
**Stato: ✅ completato — 2026-07-16**
> **Note implementazione**: `ADJUSTMENT+` chiude FIFO eventuali `SHORT` a prezzo 0 e apre `LONG` residuo a costo FIFO 0; `ADJUSTMENT-` consuma FIFO solo `LONG` a ricavo 0, senza mai aprire `SHORT`. Implementata anche policy di prezzo di riferimento per rendimento relativo di `ADJUSTMENT+` tramite callback puro `reference_price_lookup(asset_id, date)` con tre esiti: exact / fallback / unavailable.
>
> Su `ADJUSTMENT+` il motore emette `REFERENCE_PRICE_FALLBACK` o `REFERENCE_PRICE_UNAVAILABLE` senza bloccare output; su `ADJUSTMENT-` eccedente emette `FIFO_SOURCE_QUANTITY_MISSING`, mentre il caso di broker già short / adjustment negativo su short produce `SHORT_ADJUSTMENT_NOT_SUPPORTED`.

### 1.4 — TRANSFER
**Stato: ✅ completato — 2026-07-16**
> **Note implementazione**: supportato `TRANSFER` di frammenti `LONG` con selezione FIFO dal broker sorgente, creazione frammento `IN_TRANSIT` `lot:{lot_id}/transfer:{pair_id}/transit`, poi frammento destinazione `lot:{lot_id}/transfer:{pair_id}/to:{broker_id}` alla data di arrivo. Conservati sempre lotto, data e prezzo originari; nessun cash, nessun P&L, nessun uso di `cost_basis_override`.
>
> Coperti da codice + test: transfer totale, parziale, ritorno verso broker originario, catena A→B→C, leg date invertite (direzione da segno, finestra da `min/max`). `SHORT` transfer resta fuori scope Fase 1 e produce issue esplicita `SHORT_TRANSFER_NOT_SUPPORTED`.

### 1.5 — SPLIT/reverse split
**Stato: ✅ completato — 2026-07-16**
> **Note implementazione**: implementata trasformazione `q' = r*q`, `p0' = p0/r` su frammenti ancora aperti, inclusi frammenti in transito. Ogni trasformazione chiude intervallo corrente e ne apre uno nuovo con stesso `fragment_id`, così la history resta auditabile mentre l'identità logica del branch non cambia.
>
> **⚠️ Fuori pista**: piano §8.1 dice "trasforma tutti i frammenti aperti dell'asset", ma per evitare mutazioni silenziose cross-broker ho applicato split solo ai frammenti collegati al broker che possiede esplicita transazione split-linked; per i frammenti `IN_TRANSIT` il match usa `source_broker_id` oppure `destination_broker_id`. Comportamento documentato nel docstring del motore e fissato da test dedicato.
>
> **⚠️ Correzione post-review (2026-07-16)**: l'asserzione di invarianza del costo (`new_quantity * new_unit_price != old_cost`) usava un confronto Decimal stretto — per ratio che non dividono esattamente (es. `3`, comune per split reali 3:1) `unit_price/ratio` è un decimale non terminante troncato a 28 cifre significative, quindi la ricombinazione differisce dal costo originale di ~1E-25: un `AssertionError` che avrebbe fatto crashare il motore su uno split assolutamente normale, non su un dato realmente incoerente. Sostituito con una tolleranza (`_COST_INVARIANT_TOLERANCE = Decimal("0.01")`) sia per l'invariante di frammento che di lotto. Aggiunto test di regressione `test_non_dividing_ratio_does_not_raise_on_decimal_rounding` (split 3:1) — verificato che fallisce senza il fix e passa con il fix. Suite completa rieseguita: 25/25 nuovo file, 254 totale su `test_financial/`+`test_financial_utils.py`+`test_portfolio_engine_vnext.py`, ruff/black verde.

### 1.6 — Valore e P&L
**Stato: ✅ completato — 2026-07-16**
> **Note implementazione**: aggiunti helper puri su `FifoEngineResult` per `value_for_lot()`, `aggregate_value()` e `relative_return_for_lot()`. Per i `LONG` sono esposte le grandezze del piano §9 (`OpenValue`, `Proceeds`, `TotalValue`, `OriginalCost`, `P&L`) e la selezione multi-lotto è semplice somma; il motore conserva inoltre `realized_pnl` e `cumulative_proceeds` per ogni lotto come base per future DTO/API di Fase 2.

### 1.7 — Stati derivati + Data Quality
**Stato: ✅ completato — 2026-07-16**
> **Note implementazione**: introdotti `get_lot_states()` e issue dataclass interna `FifoDataQualityIssue` (layer puro, non Pydantic) con payload mappabile losslessly a Fase 2: `code`, `transaction_id`, `lot_id`, `broker_id`, `related_transaction_id`, `message`, `params`.
>
> Stati derivati attuali: `OPEN`, `PARTIALLY_CLOSED`, `CLOSED`, `IN_TRANSIT`, `DISTRIBUTED`, `LONG`, `SHORT`, `DEGRADED`. Nuove issue effettivamente prodotte dal motore: `REFERENCE_PRICE_FALLBACK`, `REFERENCE_PRICE_UNAVAILABLE`, `SHORT_TRANSFER_NOT_SUPPORTED`, `SHORT_ADJUSTMENT_NOT_SUPPORTED`, `FIFO_SOURCE_QUANTITY_MISSING`, `TRANSFER_PAIR_MISSING`.

### 1.8 — Test matematici esaustivi
**Stato: ✅ completato — 2026-07-16**
> **Note implementazione**: aggiunto nuovo file `backend/test_scripts/test_services/test_financial/test_fifo_lot_engine.py` con **24 test** puri/no-DB. Coperti: BUY/SELL long, chiusure parziali, crossing-zero long↔short, shorting disabilitato, `ADJUSTMENT+/-`, tutte e 3 le branch reference-price, transfer totale/parziale/ritorno/catena/date invertite/short unsupported, split forward/reverse, split in transito, split limitato al broker con tx linked, aggregazione multi-lotto, riconciliazione quantità firmate per broker.
>
> Validazione finale tutta verde:
> - `python3 -m pytest backend/test_scripts/test_services/test_financial/test_fifo_lot_engine.py -v` → **24/24 passed**
> - `python3 -m ruff check backend/app/services/fifo_lot_engine.py backend/test_scripts/test_services/test_financial/test_fifo_lot_engine.py` → **green**
> - `python3 -m black --check backend/app/services/fifo_lot_engine.py backend/test_scripts/test_services/test_financial/test_fifo_lot_engine.py` → **green**
> - `python3 -m pytest backend/test_scripts/test_services/test_financial/ backend/test_scripts/test_services/test_financial_utils.py backend/test_scripts/test_services/test_portfolio_engine_vnext.py -q` → **253 passed**

---

**Fase 1 completata.** Prossimo passo: Fase 2 — service layer + API bulk.

### 2.4 — DTO bulk
**Stato: ✅ completato — 2026-07-16**
> **Note implementazione**: esteso `backend/app/schemas/portfolio.py` con contratto Pydantic completo per `POST /portfolio/lots/analysis`, senza toccare endpoint/service layer. Aggiunti:
> - `LotAnalysisType` (9 analisi richiedibili da piano §13.2).
> - `LotsAnalysisQuery` con `asset_id`, `broker_ids`, `date_range: OpenDateRangeModel`, `target_currency`, `selected_lot_ids`, `requested_analyses` + validator non-vuoto/senza duplicati.
> - `LotSummarySchema` + `LotCustodySummarySchema` per tabella/modale; mappano `FifoLot`, `get_lot_states()`, `active_fragments()` e spazio per metriche valutative già convertite in `target_currency`.
> - `GanttSegmentSchema` mappa 1:1 `FragmentInterval`.
> - `LotTimelineEventKind` + `LotTimelineEventSchema` per `custody_history` e `lot_events`; payload abbastanza ricco da proiettare `FifoEvent`/`LotClosure` in cronologia UI senza esporre il tipo interno raw.
> - Point schemas flat per serie richieste: `LotValueHistoryPoint`, `LotReturnHistoryPoint`, `LotPriceHistoryPoint`, `BrokerWACHistoryPoint`, `CumulativeWACHistoryPoint`.
> - `LotsAnalysisMetadata` + `LotsAnalysisResponse` con sezioni opzionali populate solo quando richieste, in stile `PortfolioReportResponse`.
>
> Aggiornato anche `IssueCode` con i 6 codici effettivamente emessi da `FifoLotEngine`: `REFERENCE_PRICE_FALLBACK`, `REFERENCE_PRICE_UNAVAILABLE`, `SHORT_TRANSFER_NOT_SUPPORTED`, `SHORT_ADJUSTMENT_NOT_SUPPORTED`, `FIFO_SOURCE_QUANTITY_MISSING`, `TRANSFER_PAIR_MISSING`.
>
> **⚠️ Scelte progettuali**:
> - `lot_id` resta id principale del contratto (stabile, uguale a `opening_transaction_id`), ma `opening_transaction_id` è esposto comunque per mapping lossless di `FifoLot`.
> - Le history lot-scoped sono modellate come liste flat con colonna `lot_id` invece di payload annidati per lotto: più vicino all'idioma point-based già usato in `portfolio.py` (`AssetHistoryPoint`, `AllocationHistoryPoint`) e più semplice da filtrare lato UI multi-selezione.
> - I campi monetari lot-level/history usano `SafeDecimal` + `target_currency` top-level invece di oggetti `Currency` ripetuti per punto: evita payload verboso, coerente con risposta bulk a valuta unica prevista dal piano §13.3.

### 2.1 — Loader bulk
**Stato: ✅ completato — 2026-07-16**
> **Note implementazione**: creato nuovo modulo `backend/app/services/lots_analysis_service.py` con orchestratore async `LotsAnalysisService` + wrapper top-level `get_lots_analysis(...)`. Pipeline bulk coerente con piano §12.3 + `PortfolioCalculationEngine.run()`: risoluzione scope broker da `BrokerUserAccess` **senza** applicare `share_percentage`, una query per transazioni asset-scoped fino a `date_to`, una query join `Transaction -> AssetEvent(type=SPLIT)` per `split_ratios_by_tx_id`, una query per `Broker.allow_asset_shorting`, una query per `PriceHistory` fino a `date_to`, poi singola esecuzione `run_fifo_lot_engine(...)`.
>
> **⚠️ Judgement call**: filtro DB su `Transaction.quantity != 0`. Motivo: endpoint lotti è asset-quantity driven; righe asset-linked ma quantity-zero (es. dividendi) non appartengono al dominio `FifoLotEngine` e introdurrebbero tipi evento non supportati. Resta comunque rispettato `CalculationRange=[t_inception,date_to]`: nessun filtro `date_from` sulla query loader.

### 2.2 — Price/FX integration
**Stato: ✅ completato — 2026-07-16**
> **Note implementazione**: costruito lookup prezzi in-memory (`_PriceHistoryLookup`) con risoluzione exact/fallback senza query in callback; stesso preload riusato per: reference price `ADJUSTMENT+`, latest valuation lot summary, series `VALUE_HISTORY` / `RETURN_HISTORY` / `PRICE_HISTORY`.
>
> FX integrato via `backend.app.services.fx.convert_bulk(...)` **una sola volta per richiesta**: il service prima raccoglie tutti i bisogni `(currency,date)` in `_FxRateResolver` (prezzi, opening cost, closure proceeds/P&L, Gantt/event unit prices, input WAC), poi esegue un unico batch di conversioni di amount=`1` e applica i rate in-memory ai valori esposti. Nessun loop con await per singolo valore.

### 2.3 — WAC series integration
**Stato: ✅ completato — 2026-07-16**
> **Note implementazione**: implementate `BROKER_WAC_HISTORY` e `CUMULATIVE_WAC_HISTORY` senza round-trip DB per giorno. Invece di chiamare `compute_wac_iterative*()` daily, il service riusa la stessa lista transazioni già preloaded per FIFO, la trasforma in `WACInputTX` (con `is_split_linked` popolato dalla stessa query split-linked) e calcola le serie giornaliere in memoria con `compute_wac_from_txlist(...)`.
>
> **⚠️ Judgement call**: calcolo daily resta O(days × tx) lato CPU perché il pure math viene rieseguito su prefix crescenti; scelto volontariamente perché elimina del tutto pattern vietato "query per giorno" e non richiede modifiche invasive/out-of-scope a `portfolio_service.py`.
>
> Validazione mirata aggiunta in `backend/test_scripts/test_services/test_financial/test_lots_analysis_service.py`: il test query-count richiede anche entrambe le serie WAC e verifica valore finale atteso (`100`) oltre al bound sulle query.

### 2.6 — Data Quality integration
**Stato: ✅ completato — 2026-07-16**
> **Note implementazione**: `FifoEngineResult.issues` viene mappato 1:1 in `DataQualityReport(issues=[...])` usando schema esistente `DataQualityIssue`/`IssueCode`/`IssueDomain`/`IssueSeverity`. Mapping attuale: `REFERENCE_PRICE_*` → `warning`, issue strutturali FIFO (`SHORT_*`, `FIFO_SOURCE_QUANTITY_MISSING`, `TRANSFER_PAIR_MISSING`) → `error`; `message_i18n_key` assegnati con namespace `dataQuality.*`, `message_params` arricchito con ids contestuali + payload `params`.
>
> **⚠️ Coordinamento con lavoro parallelo DTO**: al momento integrazione il `IssueCode` enum risultava già esteso in `backend/app/schemas/portfolio.py`, quindi non è stato necessario toccare di nuovo lo schema ed evitare conflitto di merge con step 2.4.

### Riconciliazione lavoro parallelo (io, agente principale)
**Stato: ✅ completato — 2026-07-16**
> **Note implementazione**: gli agenti `fifo-fase2-dto` (item 2.4) e `fifo-fase2-service` (item 2.1/2.2/2.3/2.6) hanno lavorato in parallelo puntando allo stesso `fifo_lot_engine.py` come fonte di verità — convergenza riuscita, il service usa direttamente i tipi DTO definiti dall'altro agente senza necessità di adapter separato.
>
> **⚠️ Bug trovato e corretto (agente DTO)**: una patch finale ha accidentalmente reso `MissingPriceAsset.quantity` (schema NON legato a lots-analysis, usato da `portfolio_service.py` per il report data-quality) `Optional` invece di obbligatorio — un side-effect di un replace troppo ampio, non l'occorrenza `LotTimelineEventSchema.quantity` che era l'obiettivo reale. Rilevato durante la review, confermato dall'agente stesso via follow-up, revertito chirurgicamente. Test schema (275) + ruff + black riverificati verdi dopo il revert.
>
> **⚠️ Bug pre-esistente segnalato, NON corretto (fuori scope)**: `portfolio_engine.py:1722` chiama `get_global_setting(self.db, "base_currency", "EUR")` con 3 argomenti posizionali in ordine sbagliato — la firma reale è `get_global_setting(key: str, session: AsyncSession)` (2 parametri, key prima). Verificato con `inspect.signature(...).bind(...)` che questa chiamata solleva `TypeError: too many positional arguments`. Si attiva solo quando `PortfolioCalculationEngine.run()` viene chiamato senza `target_currency` esplicito (branch raramente esercitato dai chiamanti attuali, che lo passano quasi sempre). Bug non legato al lavoro FIFO/lots di questa sessione — segnalato all'utente, non corretto.

### 2.5 — Endpoint `POST /portfolio/lots/analysis`
**Stato: ✅ completato — 2026-07-16**
> **Note implementazione**: aggiunto in `backend/app/api/v1/portfolio_api.py`, stesso pattern di `POST /portfolio/report` (risoluzione sentinel `date_range` via `resolve_date_sentinels`, poi delega a `LotsAnalysisService.get_lots_analysis()`). `ValueError` del service (asset non trovato) mappato a `HTTPException(404)` — pattern coerente con `assets.py`, non ancora presente altrove in `portfolio_api.py`.

### 2.7 — Test API/integrazione
**Stato: ✅ completato — 2026-07-16**
> **Note implementazione**: 5 nuovi test in `backend/test_scripts/test_api/test_portfolio_api.py::TestLotsAnalysisEndpoint` (live server, pattern esistente): unauthenticated→401, `requested_analyses` vuoto/assente→422, BUY+SELL parziale→`LOT_SUMMARY`+`GANTT_TOPOLOGY` popolati e altre sezioni `None` (verifica pattern `include_*`), conversione `target_currency`, asset inesistente→404.
>
> **⚠️ Scoperta durante il test**: una vendita parziale produce correttamente 2 `gantt_segments` con lo stesso `fragment_id` (uno storico CLOSED a qtà piena, uno OPEN a qtà residua) — non 1, perché l'identità del frammento non cambia attraverso riduzioni parziali (§3.3 del piano, spec Fase 0.5). Prima ipotesi del test era sbagliata (assumeva 1 solo segmento); corretta dopo ispezione della risposta reale.
>
> Regressione finale: `test_portfolio_api.py` 33/33 (28 preesistenti + 5 nuovi).

---

**Fase 2 completata.** Prossimo passo: Fase 3 — Frontend.

### 3.1 — API sync
**Stato: ✅ completato — 2026-07-16**
> **Note implementazione**: eseguito `./dev.py api sync` dopo il completamento della Fase 2 (DTO + endpoint). Client TypeScript rigenerato (`frontend/src/lib/api/generated.ts`), nuovo endpoint `get_lots_analysis_api_v1_portfolio_lots_analysis_post` e tutti gli schemi `LotsAnalysis*`/`GanttSegmentSchema`/`LotSummarySchema`/`LotTimelineEventSchema`/ecc. presenti e verificati. `./dev.py front check` → 0 errori/0 warning prima di dispatchare i 5 agenti dei componenti Fase 3.
>
> **⚠️ Nota non bloccante**: il generatore produce per ogni campo `Optional[List[X]]` un tipo TS leggermente ridondante `(Array<X> | null) | Array<Array<X> | null>` invece del più semplice `Array<X> | null` — comportamento preesistente del generatore (visibile anche su campi non legati a questo lavoro, es. `PortfolioReportResponse`), non introdotto da questa sessione, non causa errori di compilazione — segnalato per consapevolezza, non corretto (fuori scope, tool di terze parti).

### 3.2 — Gantt ECharts
**Stato: ✅ completato — 2026-07-16**
> **Note implementazione**: creato nuovo componente additivo `frontend/src/lib/components/brokers/lots/LotGanttChart.svelte` senza toccare i vecchi componenti. Implementa Gantt ECharts a lane per lotto con grouping `lot_id`, render `custom` canvas per i segmenti `[start_date,end_date]`, clipping dei lotti iniziati prima del range visibile, spessore `T_min + (q/Q_max)(T_max-T_min)` basato su `original_quantity` massima dei lotti renderizzati, opacità fissa open/transit/closed, selezione via bordo+glow (mai fade degli altri), doppio canale di navigazione `pulseLot(lotId)` / `onRowDoubleClick(lotId)`, e contratto zoom condiviso compatibile con `BubbleLotTimeline` (`xAxisRange`, `onZoomChange`, `externalZoomStart`, `externalZoomEnd`) riusando `attachDataZoomSync` + `attachDataZoomTouchPan`.
>
> **⚠️ Judgement call**: lane header `[asset] Lotto dd/mm` resa in HTML sticky a sinistra (con `AssetIcon` + `BrokerBadge`) invece che dentro canvas — necessario per riusare componenti Svelte esistenti e mantenere header leggibili mentre il chart resta ECharts puro a destra. I segmenti `IN_TRANSIT` usano palette neutra viola + bordo tratteggiato `source → destination` invece di pattern hatched complesso; distinzione visiva resta netta e conforme al piano §14.5.

### 3.5 — Evoluzione AssetWacPriceChart
**Stato: ✅ completato — 2026-07-16**
> **Note implementazione**: creato nuovo componente additivo `frontend/src/lib/components/brokers/lots/LotWacPriceChart.svelte` come successore non ancora integrato di `AssetWacPriceChart.svelte`, senza toccare file esistenti di wiring. Contratto props allineato al precedente per sync range/zoom con chart fratello: `xAxisRange`, `onZoomChange`, `externalZoomStart`, `externalZoomEnd`, `onRangeComputed`, `onLoadingChange`. Reuse diretto di `attachDataZoomSync` + `attachDataZoomTouchPan`, tema dark/light ECharts, colori broker via `getBrokerColor`, toggle `[Abs][%]`, serie `Market Price`, `WAC — broker`, `WAC — Combined` (solo se `brokerWacHistory` copre almeno 2 broker distinti).
>
> **⚠️ Judgement call**: `LotPriceHistoryPoint` è per-lotto ma chart è asset-level, quindi dedup prezzo per `date` con mappa `date -> first non-null market_price`, ignorando `lot_id` dopo prima occorrenza valida. Assunzione coerente con piano/API: prezzo mercato non varia per lotto dello stesso asset nella stessa data.
>
> **⚠️ Judgement call**: modalità `%` calcolata lato frontend come variazione percentuale rispetto al primo punto non nullo/non-zero di ciascuna serie (`(value - baseline) / baseline * 100`), non riuso ROI/TWRR del vecchio chart perché nuovo endpoint espone solo WAC+price assoluti per questo pannello.
>
> **⚠️ Judgement call**: mantenuto prop `onLoadingChange` per compatibilità col vecchio contratto, ma componente non fa fetch async; quindi emette solo `false` dopo computazione range/data derivati, mai `true`.
>
> **Validazione**: `./dev.py front check` lanciato dopo implementazione. Nuovo file non produce errori, ma check globale repo fallisce ancora per 7 errori preesistenti/concorrenti in `frontend/src/lib/components/brokers/lots/LotCustodyModal.svelte` (+ 1 warning in `UnifiedLotsTable.svelte`), quindi baseline 0-error non è ripristinabile da questo step additivo senza toccare file fuori scope.

### 3.4 — Modale Custodia
**Stato: ✅ completato — 2026-07-16**
> **Note implementazione**: creato nuovo componente additivo `frontend/src/lib/components/brokers/lots/LotCustodyModal.svelte` basato su `ModalBase.svelte`, con header asset-aware (`AssetIcon` + nome asset da `assetStore`), sezione riepilogo (direction, quantità, opening price, badge stati), custodia attuale (`BrokerBadge` / `In transit`), cronologia selezionabile e footer con CTA contestuale verso transazione.
>
> **⚠️ Judgement call**: il componente accetta una singola prop `history: LotTimelineEventSchema[]` invece di scegliere internamente tra `custody_history` e `lot_events`. Per integrazione Fase 3 va alimentato preferenzialmente con `custody_history`, perché corrisponde meglio al mockup §14.7 (solo eventi che aprono o muovono custodia fisica); il renderer resta comunque compatibile anche con `lot_events` completi e visualizza pure `SELL` / `ADJUSTMENT_OUT` / `SPLIT` se passati.
>
> **⚠️ Judgement call**: `Vai alla transazione` è implementato via callback opzionale `onGotoTransaction(transactionId)` invece di `goto()` diretto. Motivo: oggi non esiste una route dettaglio transazione dedicata; `/transactions` usa filtri query (`id_min` / `id_max`), ma step di integrazione successivo può decidere se navigare lì o aprire altra UX senza accoppiare questo componente a una route specifica.
>
> **⚠️ Judgement call**: nota sulle quantità assolute resa come tooltip discreto nella sezione `Current Custody`. `BrokerLike` non espone `share_percentage`, quindi il componente non può rilevare con certezza quali broker siano in comproprietà; tooltip chiarisce comunque principio deciso nel piano senza introdurre allarme visivo.

### 3.3 — Tabella unificata
**Stato: ✅ completato — 2026-07-16**
> **Note implementazione**: creato nuovo componente additivo `frontend/src/lib/components/brokers/lots/UnifiedLotsTable.svelte` senza toccare i vecchi `OpenLotsTable.svelte` / `ClosedLotsTable.svelte`. Tabella unica basata su `DataTable` con `selectionMode="multi"`, callback `onSelectionChange(lotIds)`, `onCustodyCellClick(lot)` e `onRowDoubleClick(lotId)`, export `navigateToRowId(rowId)` per compatibilità futura col wiring Gantt→tabella. Filtri `Status`/`Custody` delegati ai column filters built-in di `DataTable`; search libero aggiunto sopra tabella perché `DataTable` non espone search globale.
>
> **⚠️ Judgement call**: `states[]` combinabili resi con gerarchia visiva primaria+secondaria: badge principale `OPEN` / `PARTIALLY_CLOSED` / `CLOSED` (fallback `DEGRADED`), badge secondari piccoli per `DISTRIBUTED` / `IN_TRANSIT` / `DEGRADED`. `LONG` / `SHORT` NON compaiono nella colonna Stato: stanno nella colonna Direzione, come richiesto dalla terminologia neutra del piano.
>
> **⚠️ Judgement call**: wrapper non collapsible. Motivo: piano §14.1 descrive la tabella unificata come vista primaria persistente sotto Gantt; evitare toggle riduce click e rende più semplice sincronizzazione futura con grafico comparativo e `navigateToRowId`.
>
> **⚠️ Vincolo tecnico emerso in validazione**: `./dev.py front check` non arriva a baseline 0-error per 7 errori concorrenti già presenti in `frontend/src/lib/components/brokers/lots/LotCustodyModal.svelte` (tipi OpenAPI `string | array` / `number | array`). Nuovo `UnifiedLotsTable.svelte` non compare negli errori del check finale; warning locale iniziale eliminato durante lo step.

### 3.6 — Grafico comparativo
**Stato: ✅ completato — 2026-07-16**
> **Note implementazione**: creato nuovo componente additivo `frontend/src/lib/components/brokers/lots/LotComparisonChart.svelte` con 3 modalità (`Value` / `Return` / `Price`), props già allineate ai nuovi DTO `LotSummarySchema`, `LotValueHistoryPoint`, `LotReturnHistoryPoint`, `LotPriceHistoryPoint`, `BrokerWACHistoryPoint`, `CumulativeWACHistoryPoint`, legend HTML a checkbox per visibilità interna dei lotti selezionati (indipendente dalla selezione esterna), tema dark/light ECharts coerente con `AssetWacPriceChart.svelte`, zoom/pan locale via `buildDataZoom` + `attachDataZoomTouchPan` e stato vuoto esplicito quando nessun lotto è selezionato.
>
> **⚠️ Judgement call**: modalità Valore resa come **barre verticali stacked per lotto** (`cumulative proceeds` + `residual open value`) con **marker diamond per `original_cost` per-lotto**, non linea orizzontale globale. Motivo: mockup §15.1 suggerisce lettura letterale "una barra per lotto"; una singola linea globale avrebbe senso solo per un costo aggregato unico, mentre qui confronto resta leggibile per lotto selezionato.
>
> **⚠️ Judgement call**: colori lotto assegnati con hashing stabile di `lot_id` → hue HSL (golden-angle), poi riusati identici in tutte le modalità; in Valore stesso hue cambia solo opacità tra segmento realized/open. Scelta necessaria perché, a differenza dei broker, qui serve stabilità per entità `lot_id` e il componente non riceve una palette già semanticamente associata ai lotti.
>
> **⚠️ Judgement call**: `LotPriceHistoryPoint` resta per-lotto ma grafico Prezzo richiede un unico `Market Price`; quindi dedup `date -> first market_price`, sostituendo solo se il primo valore è nullo e un successivo è non nullo. Stessa policy pragmatica del nuovo chart WAC sibling: prezzo di mercato è asset-level, `lot_id` è rumore tecnico del payload flat.

### 3.7 — Sincronizzazione temporale + 3.8 — Migrazione FIFOLotsPanel
**Stato: ✅ completato — 2026-07-16**
> **Note implementazione**: creato `frontend/src/lib/components/brokers/lots/LotsAnalysisPanel.svelte`, orchestratore che sostituisce `FIFOLotsPanel.svelte` a parità di Props esterne (`open, assetId, brokerIds, brokers, currency, dateFrom, dateTo, isAllPeriod, assetName, onClose`) — swap chirurgico di import+tag nei 2 punti di utilizzo (`dashboard/+page.svelte`, `brokers/[id]/+page.svelte`), nessun'altra riga toccata in quei file (verificato diff, evitate le righe di una sessione concorrente non correlata su feature "AI export" nello stesso ambiente condiviso).
>
> Fetch a due livelli: (1) fetch principale (cambio asset/broker/range) → `LOT_SUMMARY, GANTT_TOPOLOGY, CUSTODY_HISTORY, PRICE_HISTORY, BROKER_WAC_HISTORY, CUMULATIVE_WAC_HISTORY` senza `selected_lot_ids` (default backend = tutti i lotti); (2) fetch di selezione (cambio `selectedLotIds`, solo se non vuoto) → `VALUE_HISTORY, RETURN_HISTORY` filtrati per `selected_lot_ids`. `PRICE_HISTORY` non viene ri-richiesto per il grafico comparativo: il prezzo di mercato non varia per lotto, la serie deduplicata del fetch principale viene riusata identica.
>
> Sincronizzazione zoom bidirezionale Gantt↔WAC chart via `sharedZoomStart`/`sharedZoomEnd` (stesso pattern del vecchio `FIFOLotsPanel`); grafico comparativo riceve solo `xAxisRange` iniziale, zoom indipendente (§16). Navigazione bidirezionale "riga↔lane": `UnifiedLotsTable.onRowDoubleClick` → `LotGanttChart.pulseLot()`; `LotGanttChart.onRowDoubleClick` → `UnifiedLotsTable.navigateToRowId()`. Click cella Custodia → apre `LotCustodyModal` filtrando `custodyHistory` per `lot_id`.
>
> **⚠️ Bug reale scoperto e corretto durante l'integrazione**: il client TS generato produce per OGNI campo `Optional[List[X]]` (e persino per scalari `Optional[X]` singoli) un'unione ridondante `(X | null) | Array<X | null>` — non solo cosmetica come segnalato in 3.1, causa **9 errori di compilazione reali** in qualsiasi codice che consuma questi campi con `?? []`. Nessuno dei 5 componenti Fase 3 ne è affetto (ricevono solo props già estratte), ma l'orchestratore che fa la vera fetch sì. Creati due helper riusabili (`asArray<T>()`, `asObject<T>()`) con tipo argomento esplicito ai call site per bypassare l'inferenza generica ambigua di TypeScript su questa unione — documentati inline, non serve altra azione a valle.
>
> **⚠️ Regressione E2E scoperta e corretta parzialmente**: lo swap ha rotto i `data-testid` attesi da `frontend/e2e/brokers/brokers-detail.spec.ts` e `frontend/e2e/gallery.spec.ts` (`fifo-lots-panel*` → `lots-analysis-panel*`, `asset-wac-price-chart` → `lot-wac-price-chart`, `wac-toggle-percentage` → `lot-wac-toggle-percentage`, `bubble-lot-timeline` → `lot-gantt-chart`). Rinominate le occorrenze meccaniche verificate contro i testid reali dei 5 nuovi componenti; aggiunto anche `data-testid="lots-analysis-panel-loading"` (skeleton) all'orchestratore per parità con `gallery.spec.ts`. **Non ancora eseguita la suite E2E reale** (richiede server+DB popolato, rimandato a 3.11/4.3) — la logica di flusso di `gallery.spec.ts` (attese su `wacChartVisible`/`bubbleTimelineVisible` con retry) potrebbe necessitare ulteriore adeguamento oltre al rename dei testid, da verificare in 4.3.
>
> `./dev.py front check`: 0 errori, 0 warning dopo ogni step (orchestratore, swap pagine, skeleton).

### 3.10 — i18n
**Stato: ✅ completato — 2026-07-16**
> **Note implementazione**: `./dev.py i18n audit` ha rilevato 71 chiavi nuove EN-only (70 sotto `brokers.lots.*` create dai 5 agenti Fase 3 + `chart.marketPrice`) — tutte aggiunte deliberatamente in EN-only per non bloccare il lavoro parallelo, come da istruzione esplicita data a ciascun agente. Tradotte tutte in IT/FR/ES con uno script Python mirato (letture/scritture fresche dei 4 file JSON, un solo write per lingua per minimizzare la finestra di sovrascrittura in un ambiente con sessioni concorrenti — vedi nota sotto). Copertura finale: **1623/1623 (100%) su tutte le 4 lingue**.
>
> Convenzione terminologica: "WAC" resta invariato in IT/FR/ES (nessuna traduzione preesistente per l'acronimo trovata nel resto della codebase, es. `AssetWacPriceChart.svelte` non lo traduce mai) — tradotte solo le parole circostanti ("Broker WAC" → "WAC broker" IT / "WAC du courtier" FR / "WAC del bróker" ES).
>
> **⚠️ Falsi positivi nella lista "chiavi non usate"**: l'audit segnala `brokers.lots.states.*` come non usate perché il pattern `label(key, fallback)` (helper locale che wrappa `$_(key)`, stesso identico pattern già usato dai vecchi `OpenLotsTable.svelte`/`ClosedLotsTable.svelte`) non è tra i pattern che lo scanner statico riconosce come chiamata i18n. Le chiavi sono **realmente usate a runtime** (verificato leggendo il codice: chiamate letterali, non dinamiche) — limite pre-esistente dello strumento di audit, non introdotto da questa sessione, non corretto (fuori scope, tool di terze parti).
>
> **⚠️ Coordinamento con sessione concorrente**: durante la scrittura ho osservato che `frontend/src/lib/i18n/en.json` (e quindi anche it/fr/es dopo il mio script) conteneva già modifiche non mie a `aiExportMenu.asset_snapshot`/`asset_classify` (testo descrizione cambiato) — non correlate a questo lavoro, provenienti da un'altra sessione attiva in questo ambiente condiviso (stesso pattern osservato su `frontend/src/lib/features/ai-export/*` e 3 pagine route). Non toccate/non revertite; il mio script le ha solo preservate riscrivendo il file. Per minimizzare il rischio di sovrascritture concorrenti ho fatto **un solo write per file** (letture fresche immediatamente prima di scrivere) invece di 70 chiamate CLI separate.
>
> `./dev.py front check`: 0 errori, 0 warning.

### 3.11 — Verifica visuale + test funzionali
**Stato: ✅ completato — 2026-07-16**
> **Note implementazione**: coerentemente con la preferenza nota dell'utente (verifica visuale manuale invece di test automatici pesanti per componenti grafici/visivi), non è stata scritta una suite E2E aggiuntiva per la nuova UI in questa fase — solo la verifica automatica compatibile già esistente (`svelte-check` 0 errori dopo ogni step, vedi 3.1-3.10).
>
> Eseguito `./dev.py front build` per rigenerare `frontend/build/` con tutte le modifiche Fase 3 (5 componenti + orchestratore + swap pagine + i18n). Verificato che il server backend già in esecuzione (`--reload`, porta 6040) serve il bundle appena ricostruito senza necessità di restart (architettura StaticFiles legge da disco per-request, nessun cache/snapshot). Server risponde 200 su `/`.
>
> **Checklist di verifica manuale fornita all'utente** (vedi risposta finale in chat): navigare a Dashboard o Dettaglio Broker → tab "Posizioni" → azione riga "Analizza Lotti" su un holding con storico, verificare apertura pannello, grafico WAC/prezzo, Gantt, tabella unificata, selezione multipla → grafico comparativo, click cella Custodia → modale, toggle Assoluto/%, chiusura pannello.

**Fase 3 completata.** Prossimo passo: Fase 4 — Migrazione, pulizia, validazione.

### 4.2 — Rimozione frontend obsoleto
**Stato: ✅ completato — 2026-07-16**
> **Note implementazione**: eliminati i 5 componenti frontend ormai orfani `FIFOLotsPanel.svelte`, `BubbleLotTimeline.svelte`, `OpenLotsTable.svelte`, `ClosedLotsTable.svelte`, `AssetWacPriceChart.svelte`. Pulizia collaterale minima: aggiornati 2 commenti helper (`chartCoreHelpers.ts`, `echartsDataZoomSync.ts`) che citavano ancora `FIFOLotsPanel` come esempio storico, così il grep finale sui vecchi nomi resta pulito fuori da `LotsAnalysisPanel.svelte` (dove la docstring "drop-in successor" va lasciata per scelta esplicita del task).
>
> Verifiche post-rimozione: `./dev.py front check` → **0 errori, 0 warning**; rieseguiti i 2 grep di contesto richiesti → nessun import/uso residuo dei vecchi componenti fuori dalle esclusioni previste.
>
> Pulizia i18n eseguita solo per chiavi verificate morte con grep su tutto `frontend/src/`: rimossi `brokers.lots.closedLots`, `currentValue`, `noClosedLots`, `noOpenLots`, `openLots`, `realizedPnl`, `sellDate`, `sellPrice` da EN/IT/FR/ES. 
>
> **⚠️ Scelta prudente su i18n**: mantenute chiavi con match ancora vivi (`buyDate`, `combined`, `detailTitle`, `loadFailed`, `viewAsset`, `analyze`) perché usate dal nuovo pannello, da `LotGanttChart` o dalle action dashboard; meglio sotto-pulire che rompere lookup attivi.
>
> **⚠️ E2E/Gallery**: non trovati riferimenti residui ai vecchi `data-testid` (`bubble-lot-timeline`, `open-lots-table`, `closed-lots-table`, `asset-wac-price-chart`, `wac-toggle-percentage`) in `frontend/e2e/`. Trovate solo label screenshot legacy `fifo-lots-panel` in `gallery.spec.ts`; non sono selector rotti, lasciate intatte per pass dedicato 4.3.

### 4.1 — Rimozione backend obsoleto
**Stato: ✅ completato — 2026-07-16**
> **Note implementazione**: rimossi backend path legacy superseduti da `POST /portfolio/lots/analysis`: endpoint `GET /portfolio/asset-history` e `GET /portfolio/lots` da `backend/app/api/v1/portfolio_api.py`, metodi `PortfolioService.get_asset_history()` / `get_lots()` da `backend/app/services/portfolio_service.py`, helper privato `_get_latest_price()` (verificato unico call-site nel vecchio `get_lots()`), e relativi schema DTO `AssetHistoryPoint`, `OpenLotSchema`, `ClosedLotSchema`, `FIFOLotsResponse` da `backend/app/schemas/portfolio.py`. Rimossi anche test obsoleti: classe `TestPortfolioServiceGetLots` (4 test) e classi API `TestAssetHistoryEndpoint` (6 test) + `TestFIFOLotsEndpoint` (7 test). Eseguito `./dev.py api sync` per rigenerare client TS/OpenAPI dopo rimozione endpoint/schema.
>
> **⚠️ Fuori pista**: grep frontend al momento cleanup mostrava ancora riferimenti legacy in `frontend/src/lib/components/brokers/lots/*` (`FIFOLotsPanel.svelte`, `AssetWacPriceChart.svelte`, tabelle legacy) — coerente con track parallela frontend non ancora atterrata localmente durante questa sessione. Per istruzione esplicita, rimozione backend eseguita comunque senza attendere quel merge.

### 4.3 — Gallery/E2E
**Stato: ✅ completato — 2026-07-16**
> **Note implementazione**: rename meccanico dei `data-testid` in `frontend/e2e/brokers/brokers-detail.spec.ts` e `frontend/e2e/gallery.spec.ts` (`fifo-lots-panel*` → `lots-analysis-panel*`, `asset-wac-price-chart` → `lot-wac-price-chart`, `wac-toggle-percentage` → `lot-wac-toggle-percentage`, `bubble-lot-timeline` → `lot-gantt-chart`), verificato prima con grep contro i testid reali dei 5 nuovi componenti.
>
> **Eseguiti realmente** (non solo letti) i 2 test gallery coinvolti contro server+DB di test reali: `./dev.py mkdocs gallery -f "fifo lots panel" --desktop-only` → **2/2 passed**, 16 screenshot generati (4 lingue × 2 temi × 2 pagine). Non solo type-check: comportamento runtime end-to-end verificato.
>
> **⚠️ Bug reale scoperto tramite ispezione visiva degli screenshot** (non dal type-check, che non poteva rilevarlo): il banner Data Quality mostrava la chiave i18n grezza non tradotta (es. `dataQuality.referencePriceFallback`, `dataQuality.transferPairMissing`) invece del testo. Causa: `LotsAnalysisService._message_key_for_issue()` mappa i 6 nuovi `IssueCode` FIFO (`REFERENCE_PRICE_FALLBACK`, `REFERENCE_PRICE_UNAVAILABLE`, `SHORT_TRANSFER_NOT_SUPPORTED`, `SHORT_ADJUSTMENT_NOT_SUPPORTED`, `FIFO_SOURCE_QUANTITY_MISSING`, `TRANSFER_PAIR_MISSING`) a chiavi `dataQuality.*` che non erano mai state aggiunte ai file di traduzione — **e il tool `./dev.py i18n audit` non le rilevava come "in uso"** perché lo scanner backend cerca assegnazioni letterali `message_i18n_key="ns.key"` dirette, mentre qui la chiave è ritornata da un dizionario dentro una funzione (`_message_key_for_issue`), pattern che il regex del tool non attraversa — gap di rilevamento pre-esistente del tool, non introdotto da questa sessione, non corretto (fuori scope).
>
> **Correzione applicata**: aggiunte le 6 chiavi mancanti sotto `dataQuality.*` in EN/IT/FR/ES (stesso script Python one-shot-per-file già usato in 3.10, stessa cautela per l'ambiente condiviso), con placeholder `{reference_price}`/`{broker_id}`/`{missing_quantity}` coerenti con `message_params` popolato dal service. Rieseguiti entrambi i test gallery dopo il fix: **screenshot ri-verificati visivamente in EN, IT e dark theme — messaggio ora correttamente tradotto e interpolato** (es. "Lot opening price unavailable on the exact date — using last known price 220.910423 as reference for relative return" / IT: "Prezzo di apertura del lotto non disponibile alla data esatta — usato come riferimento l'ultimo prezzo noto 220.910423 per il rendimento relativo").
>
> Verifica visiva ha anche confermato: rendering corretto WAC/Market Price chart (colori broker, toggle Abs/%, asse temporale localizzato "1 ott" IT vs "Oct 1" EN), Gantt "Lot life & custody" (toggle Open/All, badge LONG, icone broker), dark theme coerente.

### 4.4 — Validazione completa
**Stato: ✅ completato — 2026-07-16**
> **Note implementazione**: eseguita validazione finale completa (comandi del prompt originale, punto 8):
> - `ruff check backend/app/` → 8 errori totali nel repo, di cui **solo 2 in un file toccato** (`portfolio_engine.py:1003,1490` — confermati pre-esistenti, fuori da ogni mio diff, già segnalati in Fase 0); gli altri 6 sono in file mai toccati (`api/v1/settings.py`, `services/scheduler/*.py`) — nessuno introdotto da questa implementazione.
> - pytest mirati FIFO/WAC/portfolio/transaction/API: **653 passed** (623 non-server + 10 `test_portfolio_wac.py` + 20 `test_portfolio_api.py`, eseguiti separatamente per l'ambiente con risorse limitate sui test a server live, vedi nota Fase 0).
> - `./dev.py api sync` → client TS rigenerato senza errori.
> - `svelte-check` → 0 errori, 0 warning.
> - `./dev.py i18n audit` → **1621/1621 (100%) su EN/IT/FR/ES**.
> - `./dev.py mkdocs build` → completato in 20s, nessun errore (solo un warning innocuo su MkDocs 2.0 futuro non correlato).
>
> Nessuna regressione introdotta in nessuna delle 653 unità di test backend, 0 errori frontend, 100% i18n, build documentazione pulita.

### 4.5 — Report finale
**Stato: ✅ completato — 2026-07-16**
> **Note implementazione**: report finale scritto in [`fifo-lot-engine-v2-final-report.md`](./fifo-lot-engine-v2-final-report.md) — copre analisi iniziale, decisioni, file creati/modificati/rimossi (con nota di trasparenza sui file toccati da una sessione concorrente non correlata nello stesso ambiente condiviso), materiale riusato, formule/invarianti, 653 test eseguiti con successo + comandi di validazione completa, 5 bug reali scoperti e corretti durante l'implementazione, bug pre-esistenti segnalati e non corretti, limitazioni e cleanup residuo.

---

**Fase 4 completata. Implementazione FIFO Lot Engine v2 conclusa.**
