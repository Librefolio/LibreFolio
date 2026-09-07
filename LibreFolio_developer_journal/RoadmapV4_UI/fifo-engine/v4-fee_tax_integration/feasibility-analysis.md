# Feasibility Analysis — Integrazione FEE/TAX nel FIFO Engine

> Verifica tecnica e matematica preventiva del documento `high-level-analysis.md`.
> Confronto con il codice reale di LibreFolio (backend Python).
> **Nessun codice/schema/test è stato modificato.** Solo lettura + simulazione mentale/algebrica.
> Documento di partenza: [`high-level-analysis.md`](./high-level-analysis.md)

---

## 0. Executive summary

**Raccomandazione finale: GO CON MODIFICHE.**

Il modello economico *lordo* proposto dal piano (accumulatori indipendenti, formula feed-forward
`GrossPnL = OpenValue + SaleProceeds + GrossIncome − OriginalCost`) **è già implementato e verificato**
nel `LotsAnalysisService`. L'esempio numerico del piano (§4: total P&L 190, return 19%) produce
**esattamente** i valori attuali del codice — vedi §4 di questo report. Non c'è doppio conteggio
dell'income. Questo è il risultato più importante: la parte "lorda" del piano non è una nuova
architettura, è una **estensione additiva** (FEE/TAX = due nuovi accumulatori + formula netta).

Tuttavia il piano contiene **cinque criticità reali** che ne condizionano la fattibilità:

1. **[BLOCCANTE per EXPLICIT_LINK]** Nessun plugin BRIM popola `related_transaction_id` per FEE/TAX,
   e il DTO di import **non ha un campo** per esprimere il link fee→trade. La "Regola 1 — EXPLICIT_LINK"
   è **inerte sui dati importati**: 0% di link espliciti. Tutta l'allocazione ricadrà su euristiche
   same-day / adjacent-day / fallback. (§9)
2. **[ARCHITETTURALE]** L'income (DIVIDEND/INTEREST) **oggi NON passa dal `FifoLotEngine`**: è allocato
   dal `LotsAnalysisService._allocate_asset_income`. Il motore ignora completamente le transazioni con
   `quantity == 0` (sono filtrate al load). Portare income+FEE+TAX dentro il motore è una riscrittura
   non banale del confine motore/servizio, non un semplice "aggiungere event kind". (§1, §6)
3. **[CONFLITTO ORDINAMENTO]** Le fasi proposte (§7 del piano) mettono TRANSFER in FASE 3 insieme a
   BUY/SELL. Il motore attuale esegue TRANSFER_DEPART/ARRIVE **prima** dello SPLIT (fasi 0/1 vs 2), per
   scelta deliberata legata agli intervalli half-open. Adottare le fasi del piano **cambierebbe** un
   ordinamento oggi corretto. (§2)
4. **[SEMANTICA — cambio di comportamento]** La regola D-1 sui proventi **contraddice** il comportamento
   attuale, che usa la quantità *a fine giornata D* (post BUY, post SELL). È un cambio voluto ma va
   trattato come breaking change semantico, con test dedicati. (§2, §3.1)
5. **[SCOPE — bug latente confermato]** L'allocazione income attuale è **asset-wide, non broker-scoped**:
   ignora il broker della transazione di provento. La correzione broker-aware è corretta e desiderabile,
   ma va coordinata con la gestione dei transfer in corso (che oggi non è modellata affatto lato income). (§3.2, §3.3)

Inoltre confermo il rischio latente `quote_base_quantity` (§5): i metodi `value_for_lot` /
`aggregate_value` / `relative_return_for_lot` del motore **non sono qbq-aware** e **non hanno consumer
di produzione** — sono usati solo dai test. Vanno rimossi o resi qbq-aware prima di estendere il motore.

---

## 1. Comportamento attuale verificato

Tutti i claim seguenti sono verificati leggendo il codice.

### 1.1 `FifoLotEngine` — tipi di evento supportati

Il motore classifica e replica **solo** eventi con quantità:

| EventKind | Origine transazione |
|---|---|
| `BUY` | `type == "BUY"` |
| `SELL` | `type == "SELL"` |
| `ADJUSTMENT_IN` / `ADJUSTMENT_OUT` | `type == "ADJUSTMENT"`, segno di `quantity` |
| `SPLIT` | tx presente in `split_ratios_by_tx_id` (ADJUSTMENT split-linked) |
| `TRANSFER_DEPART` / `TRANSFER_ARRIVE` | `type == "TRANSFER"` (coppia) |

- `EventKind` literal: `fifo_lot_engine.py:28-36`.
- Classificazione: `fifo_lot_engine.py:369-433`.
- **DIVIDEND, INTEREST, FEE, TAX NON esistono nel motore.** Nessun ramo li gestisce.

**Prova che il motore non vede mai income/fee/tax**: le transazioni passate al motore sono caricate da
`_load_transactions`, che filtra `quantity != 0` (`lots_analysis_service.py:504-506`). DIVIDEND, INTEREST,
FEE, TAX hanno `quantity == 0` per validazione (`schemas/transactions.py:276-289`). Quindi sono
**esclusi a monte**. L'income è caricato separatamente da `_load_income_transactions`
(`lots_analysis_service.py:508-525`) e allocato **fuori** dal motore.

### 1.2 Ordinamento eventi & semantica same-day

- Sort key: `(date, phase, transaction_id, pair_id or transaction_id)` con
  `phase = 0(TRANSFER_DEPART) / 1(TRANSFER_ARRIVE) / 2(SPLIT) / 3(altri)` — `fifo_lot_engine.py:468-471`.
- Quindi **nello stesso giorno**: transfer depart → transfer arrive → split → BUY/SELL/ADJUSTMENT,
  a parità di fase ordinati per `transaction_id`. **L'ordine same-day dipende dal `transaction_id`**.
- Commento di design che giustifica transfer-prima-di-split: `fifo_lot_engine.py:308-311`.

### 1.3 Lotti, frammenti, closure

- `FifoLot` (`fifo_lot_engine.py:151-168`): `lot_id == opening_transaction_id`, `original_cost`,
  `open_quantity`, `realized_quantity`, `realized_pnl`, `cumulative_proceeds`, `reference_unit_price`.
- `FragmentInterval` (`fifo_lot_engine.py:122-134`): custodia `BROKER`/`IN_TRANSIT`, `quantity`,
  `unit_price`, `start_date`, `end_date` (half-open), `broker_id`, `source_broker_id`,
  `destination_broker_id`. **Contiene già** le informazioni per lo scope broker/transito (vedi §3.3).
- `LotClosure` (`fifo_lot_engine.py:137-148`): `realized_pnl`, `proceeds`, `open/close_unit_price`.

### 1.4 Mapping operazioni

- **BUY** → consuma frammenti SHORT del broker (chiusura short), il residuo apre un lotto LONG
  (`_apply_buy`, `fifo_lot_engine.py:473-494`).
- **SELL** → consuma frammenti LONG del broker (FIFO), residuo apre SHORT se il broker consente shorting,
  altrimenti issue `FIFO_SOURCE_QUANTITY_MISSING` (`_apply_sell`, `496-528`).
- Proceeds e realized P&L calcolati in `_close_position_piece` (`779-816`): per LONG
  `realized_pnl = qty·(close−open)`, `proceeds = qty·close` solo se `close_reason == "SELL"`.
- **TRANSFER**: depart estrae pezzi FIFO dal broker sorgente, apre frammento `IN_TRANSIT` se
  `depart_date < arrival_date`, arrive lo chiude e apre frammento `BROKER` sul destinatario
  (`_apply_transfer_depart` 604-637, `_apply_transfer_arrive` 639-664, `_extract_transfer_pieces` 697-743).
- **SPLIT**: riscala quantità×ratio e prezzo/ratio dei frammenti in scope, con invariante di costo
  `q·p0 = const` a tolleranza `0.01` (`_apply_split` 666-690).

### 1.5 Allocazione DIVIDEND/INTEREST (attuale)

`_allocate_asset_income` (`lots_analysis_service.py:914-982`):
- Peso per lotto = `open_qty_i(tx.date) / Σ open_qty_j(tx.date)` sui lotti **LONG** aperti a `tx.date`.
- **`open_qty` valutata a `tx.date`** tramite `_open_quantity_on_date` →
  `_fragment_active_on_date: start_date <= query_date < end_date` (half-open, `lots_analysis_service.py:1691-1692`).
- **NON filtra per broker**: itera `for lot_id, lot in lots_by_id.items()` su **tutti** i lotti
  dell'asset (`:943-948`). → **allocazione asset-wide, non broker-scoped** (conferma il conflitto del piano).
- Conservazione: residuo di divisione assorbito dall'ultimo lotto in ordine di `lot_id` (`:955-961`).
- Income senza lotti LONG aperti a quella data → **saltato** (`if total_qty <= 0: continue`, `:950-951`),
  rimane un effetto broker-level gestito dal Portfolio Engine.

### 1.6 Formule economiche & FX

- Summary lotto (`_build_lot_summaries`, `:984-1083`):
  - `open_value = compute_holding_value(open_qty, market_price, qbq)` (`:1023`) — **qbq-aware**.
  - `total_value = open_value + proceeds` (LONG); `pnl = total_value − original_cost` (`:1025-1030`).
  - `market_pnl = pnl − realized_pnl` (`:1031`).
  - `total_pnl = market_pnl + realized_pnl + asset_income` (`:1044`).
  - `total_return = total_pnl / opening_value`, con `opening_value = converted_original_cost` (`:1047-1050`).
- Return history (`:1470-1472`): `total_return = (total_value + income)/original_cost − 1` — **algebricamente
  identica** al summary all'ultima data (dimostrazione in §4).
- FX: convertito per data via `_FxRateResolver.convert`; income convertito a `tx.date`
  (`_converted_external_amount`, `:1641-1648`).

### 1.7 `quote_base_quantity`

- `compute_holding_value(qty, price, qbq) = (qty/qbq)·price` (`valuation_utils.py:19-26`).
- Modello `Asset.quote_base_quantity` default 1, "100 per bond" (`models.py:504`).
- **Il motore NON è qbq-aware**: `value_for_lot` usa `open_quantity · market_price` (`fifo_lot_engine.py:244-260`),
  `aggregate_value` (`262-281`), `relative_return_for_lot` (`283-287`). Il servizio bypassa questi metodi
  usando `compute_holding_value` direttamente. **Grep conferma: questi metodi sono usati SOLO nei test**
  (`test_fifo_lot_engine.py`), **zero consumer di produzione**.

### 1.8 `related_transaction_id` — uso reale

- Popolato **solo** per coppie TRANSFER / FX_CONVERSION / CASH_TRANSFER (`_LINKED_TYPES`,
  `portfolio_engine.py:81-86`; auto-pairing in `transaction_service.py:1298-1302, 1381-1382`).
- **Mai popolato per FEE/TAX**. Il DTO di import `TXCreateItem` **non ha** `related_transaction_id`
  (solo `link_uuid`, usato per TRANSFER/FX). Dettaglio completo in §9.
- FEE/TAX **non possono** essere legate a un `asset_event` (`EVENT_COMPATIBLE_TYPES` = DIVIDEND/INTEREST/ADJUSTMENT,
  `schemas/transactions.py:256-268`).

### 1.9 Portfolio Engine — FEE/TAX/income (sottosistema separato)

Il Portfolio Engine **già** contabilizza income e fee/tax, ma a **livello broker/periodo** (pool cassa
K/R/W, non a livello lotto):
- DIVIDEND/INTEREST → `R[bid] += amount`; accumulatore `per_income[(asset,broker)]` o `unalloc_income[broker]`
  (`portfolio_engine.py:834-840`).
- FEE/TAX → `R[bid] -= amount`; `per_fees_taxes[(asset,broker)]` o `unalloc_fees[broker]`
  (`:842-851`).
- Esposti nel DTO come `period_fees_taxes`, `period_fees`, `period_taxes`, `unallocated_fees_taxes`
  (`schemas/portfolio.py:310, 326, 396-398`).

→ **Implicazione**: income e fee/tax hanno **due contabilizzazioni indipendenti** (portfolio-level nel
Portfolio Engine, lot-level nel nuovo motore). Non è doppio conteggio *dentro la stessa vista*, ma la
**coerenza numerica tra le due viste** (stessa somma income, stessa somma fee) diventa un invariante da
testare esplicitamente.

---

## 2. Validazione della nuova semantica giornaliera (fasi)

### Matrice evento → fase

| Evento | Fase proposta (piano) | Comportamento attuale | Compatibilità | Modifica necessaria | Rischio |
|---|---|---|---|---|---|
| DIVIDEND / INTEREST | 1 (inizio giornata, qty D-1) | Allocato fuori dal motore, qty a `tx.date` (fine giornata) | ❌ semantica diversa | Portare nel motore + regola D-1 | **Medio** — cambia numeri same-day |
| SPLIT | 2 | Fase 2 (già) | ✅ | Nessuna | Basso |
| BUY / SELL / ADJUSTMENT | 3 | Fase 3 (già) | ✅ | Nessuna | Basso |
| TRANSFER_DEPART/ARRIVE | 3 (con BUY/SELL) | **Fasi 0/1 (prima di split)** | ❌ ordinamento | Non spostare in fase 3 | **Alto** se recepito alla lettera |
| FEE / TAX | 4 (dopo qty) | Non nel motore | ➕ nuovo | Nuova passata post-fase 3 | Medio |
| Snapshot fine giornata | 5 | Implicito (stato dopo replay) | ✅ | Nessuna | Basso |

**Conclusioni:**
- Le fasi 2 e 3 del piano **coincidono già** con il motore. Buono.
- **Conflitto reale su TRANSFER**: il piano lo colloca in fase 3 con BUY/SELL; il motore lo esegue in
  fase 0/1 **prima** dello split, deliberatamente (`fifo_lot_engine.py:308-311, 468-471`). Se si recepisce
  la fase 3 alla lettera, transfer e split same-day cambierebbero comportamento. **Raccomandazione: NON
  spostare TRANSFER.** Il piano dovrebbe essere corretto lasciando l'ordine attuale
  `TRANSFER → SPLIT → BUY/SELL`, e inserendo income **prima** (nuova fase pre-transfer o pre-split) e
  FEE/TAX **dopo** (nuova fase 4). L'ordinamento vero da adottare:
  `income(D-1) → TRANSFER → SPLIT → BUY/SELL/ADJ → FEE/TAX`.
- **FEE/TAX in fase 4 possono riferirsi in sicurezza alle operazioni di fase 3** solo se la passata FEE/TAX
  ha accesso al risultato completo delle closure/aperture del giorno. Ciò suggerisce **due passate**: una
  passata quantitativa (motore attuale) e una **seconda passata deterministica** per l'attribuzione dei
  costi, che legge closures/lotti già prodotti. Vedi §6.
- **Split same-day di BUY/SELL**: resta coerente perché split (fase 2) precede BUY/SELL (fase 3) già oggi;
  nessun cambiamento.
- **Audit dell'ordine originale**: sì, va conservato l'`allocation_rule` + `transaction_id` per ogni
  allocazione (il piano lo prevede al §14 con `CostAllocation`) così l'euristica è tracciabile senza
  dipendere dall'ordine degli ID.

---

## 3. Validazione dell'allocazione dei proventi

### 3.1 Regola D-1 — simulazione

Regola proposta: `EligibleQty_i(D) = OpenQty_i(D−1)`.

Comportamento **attuale** (dimostrato dal codice `_fragment_active_on_date`,
`start ≤ D < end`) = **quantità a FINE giornata D**:

| Scenario | Attuale (fine-D) | Piano (D-1 / inizio-D) | Cambia? |
|---|---|---|---|
| BUY in D + DIVIDEND in D | frammento BUY ha `start=D` → **incluso** → riceve | `OpenQty(D-1)` non include il BUY → **non riceve** | ✅ sì |
| SELL in D + DIVIDEND in D | frammento venduto ha `end=D`, `D<D` falso → **escluso** → non riceve sul venduto | held a inizio-D → **riceve** | ✅ sì |
| BUY in D-1 + DIVIDEND in D | incluso in entrambi | incluso | no |
| SELL in D-1 + DIVIDEND in D | escluso in entrambi | escluso | no |
| BUY e SELL stesso lotto in D | né BUY né SELL contano (BUY start=D incluso, SELL end=D escluso → **si annullano** solo se stessa qty; netto 0 sul lotto same-day) | inizio-D = 0 per quel lotto | equivalente ~0 |

**Conferma esplicita**: l'implementazione attuale usa la quantità **nel punto `tx.date` con intervallo
half-open** = *fine giornata D*, NON inizio giornata, NON un punto determinato dal `transaction_id`
(l'ordine transaction-id non entra: si usa lo stato dei frammenti alla data). La regola D-1 è quindi un
**cambio semantico reale** ma limitato ai casi *same-day BUY/SELL + income*. I test esistenti
(`test_dividend_allocated_pro_rata_to_open_long_lots`, `test_lots_analysis_service.py:823-878`) usano date
**non** same-day, quindi **non si romperebbero**; ma vanno aggiunti test same-day dedicati.

**Nota di rischio matematico**: con la regola D-1, un lotto **interamente venduto in D** resta eleggibile
al provento di D. Il costo income va quindi allocato a un lotto che a fine D ha `open_quantity == 0`. Il
motore deve mantenere l'accumulatore `gross_income` anche sui lotti chiusi (già fa così per `realized_pnl`
e `cumulative_proceeds`). Coerente, ma da testare (§10, scenario "chiusura completa").

### 3.2 Scope broker

- **Oggi**: asset-wide. Simulazione del piano (Directa 30, IBKR 70, DIVIDEND +100 su Directa):
  - Attuale: 100 ripartito su **tutti** i 100 quote → Directa ~30, IBKR ~70. **SBAGLIATO** rispetto al desiderata.
  - Desiderata piano: Directa 100, IBKR 0. **Corretto.**
- La correzione (`filtrare i lotti per broker dell'accredito`) è **desiderabile e indipendente da FEE/TAX**.
- **Attenzione**: il `LotsAnalysisService` supporta lo scope multi-broker (`scope_broker_ids`) e i lotti
  hanno `opening_broker_id`, ma per lo scope broker "corrente" bisogna usare la **custodia attuale del
  frammento** alla data del provento (`fragment.broker_id`), non `lot.opening_broker_id`, perché un
  transfer può aver spostato quote su un altro broker. Questo è esattamente il nodo del §3.3.

### 3.3 Transfer in corso — i dati esistono già

Domanda del piano: `FragmentInterval` contiene abbastanza informazione? **Sì.**
- `custody_type ∈ {BROKER, IN_TRANSIT}`, `broker_id`, `source_broker_id`, `destination_broker_id`,
  `start_date`, `end_date` (`fifo_lot_engine.py:122-134`).
- Un frammento `IN_TRANSIT` porta **sia** `source_broker_id` **sia** `destination_broker_id`
  (`_extract_transfer_pieces`, `:720-730`). Le date di partenza/arrivo = `start_date`/`end_date`.

Quindi la regola del piano è **implementabile con i dati esistenti**:
- Provento su broker **From**: frammenti `BROKER` con `broker_id == From` **+** frammenti `IN_TRANSIT`
  con `source_broker_id == From` e `start_date ≤ D < end_date`.
- Provento su broker **To**: frammenti `BROKER` con `broker_id == To` già creati (arrivati, `start_date ≤ D`).

**Simulazione (esempio del piano: lotto 100, From 40, transito 60):**
- Dividendo su From durante transito → 40 (BROKER From) + 60 (IN_TRANSIT source=From) = **100** ✅
- Dividendo su To durante transito → 0 (nessun frammento BROKER To ancora) ✅
- Dividendo su To dopo arrivo → 60 ✅

**Rischi da presidiare (non-doppio-conteggio):**
- Il frammento `IN_TRANSIT` deve essere contato **una sola volta**, e **solo** dal lato From durante il
  transito. Se per errore lo si contasse anche su To (perché ha `destination_broker_id==To`), si avrebbe
  **doppia allocazione**. → Regola precisa: durante il transito conta su `source_broker_id`; dopo l'arrivo
  il frammento IN_TRANSIT è chiuso (`end_date` settato) e sostituito dal BROKER To. `_fragment_active_on_date`
  con half-open garantisce che nel giorno di arrivo `D==end` l'IN_TRANSIT non è più attivo e il BROKER To
  (start=arrival) lo è → nessuna sovrapposizione. **Coerente.**
- **Allocazione retroattiva a frammenti non esistenti**: impossibile, perché la valutazione è per-data via
  `_fragment_active_on_date`.
- **Transfer parziale / totale / multi-lotto**: `_extract_transfer_pieces` fraziona per lotto FIFO
  (`:708-742`); ogni pezzo mantiene il proprio lot_id e unit_price → l'eleggibilità per-lotto resta corretta.

### 3.4 Nessun lotto eleggibile → `ASSET_INCOME_NO_ELIGIBLE_LOTS`

- **Oggi**: l'income senza lotti LONG viene **silenziosamente saltato** (`:950-951`), senza issue: rischio
  di **perdita di visibilità**. La proposta di emettere un issue è un **miglioramento**.
- **Severity/status raccomandati**: coerenti con le issue esistenti. `FifoDataQualityIssue`
  (`fifo_lot_engine.py:111-119`) e mapping `_message_key_for_issue` (`lots_analysis_service.py:1695+`).
  `calculation_status` diventa `DEGRADED` non appena esiste un'issue (`FifoEngineResult.calculation_status`,
  `fifo_lot_engine.py:198-200`). → Nuovo codice `ASSET_INCOME_NO_ELIGIBLE_LOTS` con severity **WARNING**
  (non blocca il calcolo), status **DEGRADED**.
- **Dati da includere**: `transaction_id`, `broker_id`, `date`, `amount`, `currency`.
- **Non-doppio-conteggio col Portfolio Engine**: attenzione — oggi l'income "orfano" (asset-linked ma senza
  lotti) NON è allocato ai lotti ma **è comunque** contato dal Portfolio Engine come `per_income[(asset,broker)]`
  (`portfolio_engine.py:837-838`). Se la vista lotti iniziasse a "recuperarlo" altrove si creerebbe
  incoerenza tra le due viste. → **Lasciarlo non allocato + issue**, coerente con il comportamento attuale.

---

## 4. Revisione delle formule economiche (no doppio conteggio)

**Scenario del piano** verificato passo-passo contro il codice (`_build_lot_summaries`):

```
BUY  10 × 100 = 1000   → original_cost=1000, open_qty=10
SELL  4 × 120 =  480   → realized_pnl = 4·(120−100)=80, cumulative_proceeds=480, open_qty=6
price attuale = 110
DIVIDEND = 50          → asset_income=50
```

| Grandezza | Formula codice | Valore | Atteso piano |
|---|---|---|---|
| `open_value` | `compute_holding_value(6,110,1)` | 660 | 660 ✅ |
| `proceeds` | `cumulative_proceeds` (conv.) | 480 | 480 ✅ |
| `total_value` | `open_value + proceeds` | 1140 | — |
| `pnl` | `total_value − original_cost` | 140 | — |
| `realized_pnl` | closures | 80 | 80 ✅ |
| `market_pnl` | `pnl − realized_pnl` | 60 | 60 (P&L aperto) ✅ |
| `total_pnl` | `market_pnl + realized_pnl + asset_income` | **190** | **190** ✅ |
| `total_return` | `total_pnl / opening_value` = 190/1000 | **19%** | **19%** ✅ |

**Verifiche di assenza doppio conteggio:**
- `income` **NON** è dentro `total_value` (che è `open_value + proceeds`); è aggiunto **una sola volta** in
  `total_pnl` (`:1044`). ✅ Nessun doppio conteggio.
- `pnl − realized_pnl == open_value − open_cost_basis`? `pnl − realized_pnl = 140−80 = 60 = market_pnl`.
  `market_pnl` è per definizione la componente prezzo. ✅
- **History vs summary** all'ultima data: history usa `(total_value + income)/original_cost − 1`
  = `(1140+50)/1000 − 1 = 0.19`; summary usa `total_pnl/opening_value = 190/1000 = 0.19`. **Identici.** ✅
  (Dimostrazione algebrica: `total_pnl = open_value+proceeds−cost+income = total_value−cost+income`, quindi
  `total_pnl/cost = (total_value+income)/cost − 1`.)
- **Lotto chiuso**: `cumulative_proceeds`, `realized_pnl` e (con il piano) `gross_income` restano
  cristallizzati; `open_value=0`. `total_pnl` resta = `realized_pnl + income`. ✅
- **estimated-at-cost** (`value_source=ESTIMATED_AT_COST`, `:1034-1041`): `open_value` = quota del costo,
  `market_pnl=0`; `total_pnl = 0 + realized_pnl + income`. L'income **non** è introdotto due volte
  (non entra in `open_value`). ✅

**Conclusione §4:** il modello lordo del piano è **già presente e corretto**. FEE/TAX si innestano
**additivamente**: `NetPnL = total_pnl − allocated_fees − allocated_taxes`,
`NetReturn = NetPnL / opening_value`. Nessuna modifica alle formule esistenti richiesta — solo estensione.

**Naming (raccomandazione, non implementare):** l'attuale `total_pnl` è di fatto il **gross** total P&L.
Introducendo il netto conviene rinominare a livello DTO/documentazione:
- `total_pnl` → mantenere come `gross_total_pnl` (o aggiungere alias), `total_return` → `gross_total_return`,
  e aggiungere `net_total_pnl` / `net_total_return`, `allocated_fees`, `allocated_taxes`. Attenzione: il DTO
  `LotSummarySchema` ha `extra="forbid"` (`schemas/portfolio.py:516`) e il client TS è generato via
  `./dev.py api sync` — ogni campo nuovo è breaking per il frontend e va sincronizzato.

---

## 5. Hardening `quote_base_quantity`

**Confine analizzato:**
- Percorso corretto (produzione): `compute_holding_value(qty, price, qbq)` in summary/history
  (`lots_analysis_service.py:1023, 1376, 1451, 1631`). **qbq-aware.**
- Percorso pericoloso (motore): `value_for_lot`/`aggregate_value`/`relative_return_for_lot`
  (`fifo_lot_engine.py:244-287`) usano `qty·price` **senza qbq**.

**Verifica consumer:** grep su tutto `backend/` → questi tre metodi sono referenziati **solo** in
`test_fifo_lot_engine.py`. **Zero consumer di produzione.** Il rischio è quindi **latente**: nessun bug
attivo oggi, ma un futuro consumer (incluso un'estensione FEE/TAX che chiami `aggregate_value`) otterrebbe
valori ×100 su un bond (qbq=100).

**Scenario bond minimo (dal piano):** nominale 1000, quote 98.50 base 100, opening unit 0.985.
- Corretto: `OpenValue = (1000/100)·98.50 = 985`.
- `value_for_lot`: `1000·98.50 = 98 500` → **×100 errato**.

**Raccomandazione (in ordine di preferenza, non implementare ora):**
1. **Rimuovere** `value_for_lot`/`aggregate_value`/`relative_return_for_lot` dal motore e spostarne la logica
   nei test come helper locali — dato che non hanno consumer di produzione, è l'opzione a rischio minore e
   riduce la superficie del motore prima di estenderlo con FEE/TAX.
2. In alternativa, **renderli qbq-aware** accettando `quote_base_quantity` obbligatorio (firma esplicita),
   così l'estensione FEE/TAX non può accidentalmente usarli in modo errato.
3. Rinominarli `*_qbq_unaware()` e marcarli interni (meno robusto: non impedisce l'uso).
- **In ogni caso**: aggiungere un **test permanente con qbq=100** che valga sia il summary sia (se si
  mantengono) i metodi del motore, per prevenire regressioni ×100.

---

## 6. Fattibilità dell'estensione del motore

Il motore oggi è **puro e quantitativo**: nessun FX, nessuna target currency, nessun income. Il servizio
fa I/O + FX + presentazione. Aggiungere DIVIDEND/INTEREST/FEE/TAX pone la domanda **A vs B**:

| Criterio | **Opzione A** — eventi già convertiti in valuta target nel motore | **Opzione B** — motore in valuta originaria, FX nel servizio |
|---|---|---|
| Purezza motore | ⬇ il motore diventa currency-aware; perde neutralità | ⬆ resta valuta-agnostico (come oggi) |
| Dipendenza da target currency | Il replay va **rifatto** per ogni valuta target richiesta | Replay unico, FX applicato dopo → **N valute senza rieseguire** |
| Conservazione importi | Arrotondamenti FX **dentro** il replay, difficili da riconciliare | Allocazione in unità nominali (esatta), FX una volta sola alla fine |
| Ripetibilità / determinismo | Dipende dai tassi FX passati al motore | Determinismo puro (nessun tasso nel motore) |
| Impatto sui test | I test motore diventano FX-dipendenti | I test motore restano puri (come i ~446 righe attuali) |
| Compatibilità architettura | Rompe la separazione motore/servizio attuale | **Conforme** alla separazione attuale |

**Raccomandazione: Opzione B.** Il motore alloca **pesi/quote nominali** (per lotto), il servizio applica
FX a `tx.date` (come già fa `_converted_external_amount`). Questo preserva l'invariante di conservazione
(`Σ AllocatedCost_i = CostTotal`) **prima** dell'FX e permette di chiedere la stessa analisi in valute
diverse senza rieseguire il replay.

**Come modellare gli eventi economici:**
- **NON** estendere `FifoEvent` (che è quantitativo e frozen, `fifo_lot_engine.py:94-108`) con campi
  economici opzionali: inquinerebbe l'evento base. Preferire un **secondo tipo di evento economico**
  (`EconomicEvent`: `transaction_id, date, type ∈ {DIVIDEND,INTEREST,FEE,TAX}, broker_id, asset_id, amount,
  currency, related_transaction_id, description`) mantenendo **separati** eventi quantitativi ed economici.
- **Due passate deterministiche:**
  1. Passata quantitativa = motore attuale invariato → produce lotti, frammenti, closures.
  2. **Seconda passata "economic allocator"** che consuma il risultato della prima (per-data, per-broker,
     con `_fragment_active_on_date`) e produce `gross_income`, `allocated_fees`, `allocated_taxes` e la
     lista `CostAllocation` auditabile. Questa passata può stare **dentro** `FifoLotEngine` (nuovo metodo)
     o in un modulo dedicato `fifo_economic_allocator.py` che riusa i dataclass del motore.

Questa struttura minimizza il rischio di regressione sul core quantitativo (che è già rilasciato e testato)
e isola la nuova complessità.

---

## 7. Validazione delle regole FEE/TAX

**Nota di segno trasversale:** FEE/TAX hanno `amount < 0` per validazione
(`schemas/transactions.py:296`). Le formule del piano usano `CostTotal` come positivo. L'allocatore deve
usare `abs(amount)` (o gestire il segno esplicitamente) e i test devono fissare la convenzione.

### 7.1 Costi senza asset (`asset_id = null`)

- **Confermato**: `_load_transactions` filtra per `asset_id == asset_id` (`:505`), quindi FEE/TAX
  cash-only non entrerebbero mai nel motore per-asset. → correttamente **ignorati** dal FifoLotEngine.
- Restano contabilizzati dal Portfolio Engine come `unalloc_fees[broker]` (`portfolio_engine.py:850-851`)
  → esposti come `unallocated_fees_taxes` (`schemas/portfolio.py:326`). ✅ Nessuna perdita.

### 7.2 Target BUY

- Peso `w_i = OpeningValue_i / Σ OpeningValue_j`. Con una sola BUY → 100% al lotto (`lot_id == tx_id` della BUY,
  `fifo_lot_engine.py:830`). Coerente.
- **Caso BUY che chiude SHORT e apre LONG** (`_apply_buy`, `:473-494`): la BUY può generare **closures** (di
  lotti SHORT) **e** un lotto LONG. `OpeningValue` è definito solo per il lotto **aperto** (LONG). Il piano
  deve specificare: la fee su tale BUY va al lotto LONG aperto o ripartita anche sulle closure SHORT?
  → **Ambiguità da chiarire (domanda di prodotto).** Raccomando: fee della BUY → lotto aperto (opening),
  coerente con "SAME_DAY_BUY → lotti aperti da quelle BUY".

### 7.3 Target SELL

- Peso `w_i = ClosedQuantity_i / Σ ClosedQuantity_j` sui lotti consumati dalla SELL.
- Le `LotClosure` contengono `lot_id`, `quantity`, `transaction_id` (`fifo_lot_engine.py:137-148`), quindi
  `ClosedQuantity_i` per una SELL è ricavabile filtrando `closures` per `transaction_id == sell_tx`. ✅
- **SELL single/multi-lotto/parziale**: coperti dai `LotClosure` per-frammento.
- **SELL che chiude LONG e apre SHORT** (`_apply_sell`, `:496-528`): come §7.2, la SELL genera closures LONG
  **+** un lotto SHORT. Il peso `ClosedQuantity` copre solo la parte chiusa; la parte che apre SHORT non ha
  closure. → Stessa ambiguità: la fee sul "residuo short" non ha target di closure. **Chiarire.**
- **Più SELL nello stesso giorno**: ogni SELL ha closures con `transaction_id` distinto → attribuzione
  per-SELL corretta, purché la fee identifichi la SELL giusta (che dipende dall'euristica same-day, vedi §9).

### 7.4 Target DIVIDEND/INTEREST

- Riusa i pesi dell'income (`income_events`/`income_by_lot`). Fattibile: `_allocate_asset_income` già
  produce, per ogni income tx, la lista dei lotti e i pesi.
- **Casi**: stesso giorno → banale; **TAX in D-1 e provento in D** oppure **provento in D e TAX in D+1** →
  richiede la finestra ±1 giorno (Regola 3). Fattibile ma introduce **non-determinismo di matching** se ci
  sono più proventi candidati nella finestra → serve priorità deterministica documentata.
- **Provento durante transfer**: i pesi income già gestiscono il transito (§3.3), quindi la fee eredita la
  stessa ripartizione. ✅

### 7.5 Fallback sui lotti aperti

- `w_i = OpenQty_i / Σ OpenQty_j` sui lotti LONG aperti stesso asset+broker.
- **Quantità a quale istante?** Il piano dice "inizio giornata" per il fallback FEE/TAX, ma la regola income
  è "D-1". **Incoerenza potenziale**: se income usa `OpenQty(D-1)` e il fallback fee usa `OpenQty(inizio D)`
  (= D-1) sono equivalenti; ma se il fallback usasse fine-D divergerebbe. → **Raccomando: uniformare il
  fallback FEE/TAX alla stessa convenzione D-1** dei proventi, per evitare che una fee sulla stessa data di
  una BUY venga ripartita in modo diverso dall'income. Va esplicitato nel piano.

### 7.6 Nessun target → `ASSET_COST_NO_ELIGIBLE_LOTS`

- Severity **WARNING**, `calculation_status = DEGRADED`.
- Dati diagnostici: `transaction_id`, `broker_id`, `date`, `amount`, `currency`, `type` (FEE|TAX).
- **Trattamento importo / non-doppio-conteggio**: come per income orfano (§3.4), la fee **resta non allocata
  a livello lotto** ma **è già** contata dal Portfolio Engine (`unalloc_fees` o `per_fees_taxes`). Non va
  "recuperata" nella vista lotti, altrimenti incoerenza tra viste.

---

## 8. Modello feed-forward raccomandato

Confermo la scelta del piano (§4, §12): **accumulatori indipendenti**, `original_cost` **invariato**.

**Perché batte l'alternativa "adjusted cost basis / net proceeds":**

| Criterio | Accumulatori indipendenti (piano) | Modifica di `original_cost`/proceeds |
|---|---|---|
| Doppio conteggio | Nessuno: ogni costo entra una volta in `NetPnL` | Rischio: fee aggiunta al costo **e** sottratta nel P&L |
| N. operazioni | 1 delta per evento | ≥2 (aggiungi al costo, poi ricalcola return) |
| Auditabilità | `CostAllocation` per riga | Costo "fuso" nel cost basis, non tracciabile |
| Compatibilità WAC/PMC | Nessun impatto: WAC ignora `quantity==0` (fee/tax) — verificato: `compute_wac_from_txlist` processa solo `qty>0`/`qty<0`, le fee `qty==0` non entrano né in additions né in reductions (`wac_utils.py:99-102`) | Cambierebbe il cost basis → impatta WAC, transfer snapshot, exit tax |
| Metriche esistenti | `total_pnl`/`total_return` restano il "lordo"; netto additivo | Rompe la semantica attuale di `original_cost` (usato anche da transfer `cost_basis_override`, `models.py:661`) |
| History | Prefix-sum per data (come income oggi, `:974-981`) | Ricalcolo per data del cost basis aggiustato |
| Chiusura / estimated-at-cost | Accumulatori cristallizzati; income/fee non entrano in `open_value` | Fragile |

**Formule raccomandate (feed-forward, come il piano):**
```
GrossPnL_i(t) = OpenValue_i(t) + SaleProceeds_i(t) + GrossIncome_i(t) − OriginalCost_i    (già = total_pnl attuale)
NetPnL_i(t)   = GrossPnL_i(t) − AllocatedFees_i(t) − AllocatedTaxes_i(t)
GrossReturn_i = GrossPnL_i / OriginalCost_i     (= total_return attuale)
NetReturn_i   = NetPnL_i   / OriginalCost_i
```
`original_cost` resta il costo della transazione di apertura; FEE/TAX sono accumulatori separati e
auditabili. **Nessuna compensazione inversa.**

---

## 9. Audit empirico dei dati BRIM

Fonte: audit dei plugin `brim_providers/*`, dello schema `schemas/brim.py`/`transactions.py`, e del path
di import in `transaction_service.py`. **Nessun file CSV/XLSX di fixture** è presente sotto
`backend/test_scripts` (solo test Python) → statistiche quantitative reali non disponibili; **dichiaro il
limite** e riporto solo classificazione strutturale.

### Finding bloccante per EXPLICIT_LINK

- Il DTO di import `TXCreateItem` **non ha** `related_transaction_id`. Ha solo `link_uuid`, usato
  esclusivamente per creare coppie **TRANSFER/FX_CONVERSION** (`schemas/transactions.py:127-132, 184-185`).
- Il path di import popola `related_transaction_id` **solo** per coppie con lo stesso `link_uuid`
  (`transaction_service.py:1210-1233, 1298-1302`).
- **Nessun plugin** collega una FEE/TAX alla sua BUY/SELL/DIVIDEND. Nessun order-id/external-ref viene
  preservato come link fee→trade.

→ **La "Regola 1 — EXPLICIT_LINK" produce 0 match sui dati importati.** Tutta l'allocazione dipenderà da
SAME_DAY_* / ADJACENT_DAY / OPEN_LOTS_FALLBACK. Il piano deve declassare EXPLICIT_LINK a "supportato solo
per transazioni inserite/modificate manualmente con link esplicito" (feature futura), **non** come regola
primaria.

### Emissione FEE/TAX per plugin

| Plugin | FEE/TAX emessa? | Asset-linked? | `related_transaction_id`? | Note |
|---|---|---|---|---|
| trading212 | TAX sì / FEE no | a volte | ❌ | `broker_trading212.py:312-335` |
| directa | FEE+TAX sì | sì se ISIN/ticker | ❌ | `broker_directa.py:313-361` |
| degiro | FEE+TAX sì | sì se presente | ❌ | `broker_degiro.py:313-361` |
| schwab | FEE+TAX sì | sì | ❌ | `broker_schwab.py:355-371` |
| coinbase | FEE sì / TAX no | sì | ❌ | `broker_coinbase.py:292-307` |
| revolut | FEE sì / TAX no | sì se ticker | ❌ | `broker_revolut.py:277-313` |
| ibkr | FEE sì / TAX no | sì | ❌ | `broker_ibkr.py:231-251` |
| finpension | FEE sì (TAX nc) | sì se ISIN/nome | ❌ | `broker_finpension.py:196-246` |
| freetrade | no | n/a | n/a | fee foldate nel trade |
| etoro | no | n/a | n/a | fee foldate nel trade |
| generic_csv | FEE+TAX sì | dipende da col `asset` | ❌ | `broker_generic_csv.py:534-620` |

### Classificazione attesa (qualitativa) delle regole

- `EXPLICIT_LINK`: **~0%** (nessun link nei dati importati).
- `SAME_DAY_BUY` / `SAME_DAY_SELL`: quota **maggioritaria** dove la fee condivide data+asset+broker con la
  trade (tipico di directa/degiro/ibkr/schwab che emettono la fee sulla stessa riga/data del trade).
- `SAME_DAY_INCOME`: per ritenute fiscali (TAX) su dividendi stesso giorno (directa/degiro/trading212).
- `ADJACENT_DAY`: settlement sfasato (T+1/T+2) — non stimabile senza dati reali.
- `OPEN_LOTS_FALLBACK`: fee di custodia/gestione (revolut "custody fee", finpension) → nessuna trade
  candidata → fallback sui lotti aperti.
- `NO_ELIGIBLE_LOTS`: fee/tax asset-linked su asset senza posizione aperta (es. dopo chiusura totale).
- `AMBIGUOUS`: **rischio concreto** quando nello stesso giorno/asset/broker coesistono BUY **e** SELL **e**
  income → la priorità deterministica (§9 del piano) decide, ma sui dati reali va calibrata.

**Plugin che perdono informazione utile:** etoro, freetrade (fee foldate → non separabili). **Plugin con
dati sufficienti per same-day matching:** directa, degiro, schwab, ibkr, coinbase, trading212, generic_csv.

**Raccomandazione:** prima di congelare la priorità, generare un **dataset di prova** (fixture CSV per i
plugin principali) e misurare empiricamente le percentuali. Oggi **non esiste** tale dataset nel repo.

---

## 10. Matrice di test proposta

Convenzioni: test async pytest, fixture `session/test_user/asset/broker`, `Transaction`/`PriceHistory`
inline; per motore puro usare `test_fifo_lot_engine.py`.

| # | Scenario | Input minimo | Output atteso | Invariante | File |
|---|---|---|---|---|---|
| 1 | Provento D vs D-1 (BUY same-day) | BUY D, DIVIDEND D | BUY **non** eleggibile (regola D-1) | Σincome = amount | `test_lots_analysis_service.py` |
| 2 | Provento D (SELL same-day) | SELL D, DIVIDEND D | venduto **eleggibile** (held inizio-D) | conservazione | idem |
| 3 | Scope broker | Directa 30 + IBKR 70, DIV su Directa | Directa 100, IBKR 0 | Σ = amount | idem |
| 4 | Provento su From durante transit | transfer parziale in corso, DIV su From | From+transit = 100 | no doppia alloc | idem |
| 5 | Provento su To durante transit | idem, DIV su To | 0 fino ad arrivo | no alloc retroattiva | idem |
| 6 | Provento su To dopo arrivo | DIV su To dopo end | = qty arrivata | conservazione | idem |
| 7 | Income senza lotti | DIV senza LONG aperti | issue `ASSET_INCOME_NO_ELIGIBLE_LOTS`, non allocato | status DEGRADED | idem |
| 8 | BUY + FEE same-day | BUY D, FEE D | fee → lotto aperto (100%) | Σfee = |amount| | idem |
| 9 | SELL + FEE same-day | SELL D, FEE D | fee → closures pesate ClosedQty | Σfee = |amount| | idem |
| 10 | SELL multi-lotto + FEE | 2 BUY + 1 SELL che consuma entrambi + FEE | ripartizione ClosedQty | Σw=1 | idem |
| 11 | Crossing LONG/SHORT + costo | BUY chiude SHORT & apre LONG (+ fee) | target chiarito (opening) | no perdita importo | idem |
| 12 | Income + FEE stessa data | DIV D + TAX D | TAX riusa pesi income | Σ = |amount| | idem |
| 13 | Finestra D-1/D/D+1 | TAX D+1 dopo DIV D | match adiacente deterministico | 1 solo match | idem |
| 14 | Fallback open lots | FEE custodia senza trade | ripartizione OpenQty(D-1) | Σw=1 | idem |
| 15 | Costo senza asset | FEE `asset_id=null` | ignorato dal motore, in `unalloc_fees` | no impatto lotti | `test_portfolio_engine/*` |
| 16 | Nessun target | FEE asset-linked, asset chiuso | issue `ASSET_COST_NO_ELIGIBLE_LOTS` | non allocato | `test_lots_analysis_service.py` |
| 17 | Conservazione importi | mix income+fee su N lotti | Σalloc == totale (residuo ultimo) | esatta | idem |
| 18 | Lordo vs netto | BUY+SELL+DIV+FEE+TAX | gross/net P&L & return coerenti | net = gross − costi | idem |
| 19 | qbq=1 | azione, valori | valori 1× | — | `test_fifo_lot_engine.py` + service |
| 20 | qbq=100 (bond) | nominale 1000, quote 98.5 | OpenValue 985 (no ×100) | **anti-regressione ×100** | idem |
| 21 | FX multi-valuta | tx in USD, target EUR | net/gross convertiti a tx.date | Opzione B: replay unico | `test_lots_analysis_service.py` |
| 22 | estimated-at-cost | nessun prezzo, DIV+FEE | market_pnl=0, income/fee non doppi | no doppio income | idem |
| 23 | Chiusura completa + income/fee | lotto venduto tutto in D, DIV D | income/fee cristallizzati su lotto chiuso | open_value=0 | idem |

---

## 11. Criticità ordinate per severità

**BLOCCANTI (S1)**
- **S1-a** EXPLICIT_LINK inerte: nessun `related_transaction_id` FEE/TAX nei dati importati, DTO senza campo
  di link. → Ridisegnare la Regola 1 come opzionale/manuale; basare l'allocazione su same-day+fallback. (§9)
- **S1-b** Conflitto ordinamento TRANSFER: il piano lo mette in fase 3; il motore lo esegue prima dello
  split. → Non recepire alla lettera; correggere il piano. (§2)

**ALTE (S2)**
- **S2-a** Income oggi fuori dal motore + transazioni `quantity==0` filtrate al load: l'estensione richiede
  una seconda passata economica, non un semplice event kind. (§1.1, §6)
- **S2-b** Cambio semantico D-1: rompe i casi same-day (oggi fine-D). Breaking change controllato. (§3.1)
- **S2-c** Scope broker income asset-wide → broker-scoped: correzione necessaria, da coordinare col transito. (§3.2/§3.3)
- **S2-d** Coerenza tra viste: income/fee sono contati anche dal Portfolio Engine (`per_income`,
  `per_fees_taxes`, `unalloc_*`); la vista lotti deve **quadrare** con quei totali. (§1.9)

**MEDIE (S3)**
- **S3-a** qbq: metodi non-qbq-aware nel motore (test-only) → rimuovere/rendere qbq-aware prima di estendere. (§5)
- **S3-b** Segno FEE/TAX negativo: le formule del piano assumono positivo → `abs()`/convenzione esplicita. (§7)
- **S3-c** Crossing LONG/SHORT: target della fee su BUY/SELL che apre posizione opposta non definito. (§7.2/§7.3)
- **S3-d** Fallback fee: "inizio giornata" vs income "D-1" → uniformare. (§7.5)
- **S3-e** DTO `extra="forbid"` + client TS generato: campi netti nuovi = breaking frontend, richiede
  `./dev.py api sync`. (§4)

**BASSE (S4)**
- **S4-a** Priorità deterministica FEE/TAX non calibrata su dati reali (nessuna fixture). (§9)
- **S4-b** `ASSET_INCOME_NO_ELIGIBLE_LOTS` / `ASSET_COST_NO_ELIGIBLE_LOTS`: aggiungere codici issue + i18n key. (§3.4/§7.6)

---

## 12. Componenti: mantenere / modificare / creare / deprecare

**Mantenere (invariati):**
- Core quantitativo `FifoLotEngine` (BUY/SELL/ADJUSTMENT/TRANSFER/SPLIT) — rilasciato e testato.
- Formule lorde `total_pnl`/`total_return`/`market_pnl` in `_build_lot_summaries` — già corrette (§4).
- `_allocate_asset_income` come base algoritmica (pesi + conservazione) da riusare.
- `compute_holding_value` (qbq-aware) come unico punto di valutazione.
- Contabilità broker-level del Portfolio Engine (`per_income`/`per_fees_taxes`/`unalloc_*`).

**Modificare:**
- Semantica income → D-1 + broker-scoped + transito (`_allocate_asset_income`, `_open_quantity_on_date`
  o nuovo helper "inizio giornata").
- Load: includere FEE/TAX/income nella preparazione (senza romperlo per il motore quantitativo).
- DTO `LotSummarySchema` (+ `LotValueHistoryPoint`/`LotReturnHistoryPoint`): aggiungere `allocated_fees`,
  `allocated_taxes`, `net_total_pnl`, `net_total_return` (e chiarire naming gross).

**Creare:**
- Secondo tipo di evento economico + **economic allocator** (seconda passata deterministica).
- `CostAllocation` audit trail (transaction_id, lot_id, cost_type, allocation_context, allocation_rule, amount).
- Issue `ASSET_INCOME_NO_ELIGIBLE_LOTS`, `ASSET_COST_NO_ELIGIBLE_LOTS` + i18n.
- Test matrix §10 (in particolare qbq=100 e coerenza tra viste).
- Fixture BRIM per calibrare la priorità (§9).

**Deprecare/rimuovere:**
- `value_for_lot`, `aggregate_value`, `relative_return_for_lot` dal motore (o renderli qbq-aware) —
  zero consumer di produzione.

---

## 13. Migrazione incrementale proposta

1. **Hardening qbq** (indipendente, a rischio nullo): rimuovere/rendere qbq-aware i 3 metodi + test qbq=100.
2. **Correzione income** (indipendente da FEE/TAX): D-1 + broker-scope + transito, con test dedicati e
   verifica di non-regressione sui test income esistenti (che sono non-same-day).
3. **Refactor confine load**: consentire il caricamento di income/fee/tax senza inquinare l'input del motore
   quantitativo (Opzione B: nominali, FX nel servizio).
4. **Economic allocator (income)**: spostare l'allocazione income nella seconda passata deterministica,
   mantenendo identici i numeri lordi (regression test byte-per-byte sui DTO esistenti).
5. **FEE/TAX gross→net**: aggiungere accumulatori `allocated_fees`/`allocated_taxes`, regole SAME_DAY/
   ADJACENT/FALLBACK, issue, `CostAllocation`, DTO netti, `./dev.py api sync`.
6. **Coerenza tra viste**: test che quadrino `Σ income lotti == per_income` e `Σ fee lotti == per_fees_taxes`.

Nessuna migrazione **DB** richiesta: il piano preserva il modello transazionale (confermato — FEE/TAX/income
sono già tipi esistenti con `amount`/`asset_id`/`broker_id`). Le uniche migrazioni sono di **schema DTO/API**
+ client TS.

---

## 14. Raccomandazione finale

### GO CON MODIFICHE

Il piano è **fattibile** e la sua parte lorda è **già realtà** nel codice (grande vantaggio: bassa incognita
sul cuore economico). Procedere **a condizione** di recepire queste correzioni al piano:

1. **Rimuovere EXPLICIT_LINK come regola primaria** (dati importati non la supportano); renderla feature
   manuale/futura. Basare l'allocazione su same-day + adjacent + fallback.
2. **Non spostare TRANSFER in fase 3**: mantenere `income(D-1) → TRANSFER → SPLIT → BUY/SELL → FEE/TAX`.
3. **Adottare l'Opzione B** (motore valuta-agnostico, FX nel servizio) e **due passate** (quantitativa +
   economic allocator), senza inquinare `FifoEvent`.
4. **Uniformare le convenzioni temporali** income/fallback-fee (entrambe D-1).
5. **Gestire segno negativo** FEE/TAX e **chiarire il target** su BUY/SELL che aprono posizione opposta.
6. **Hardening qbq** e **coerenza tra viste** come prerequisiti/test permanenti.

### Domande residue (decisione di prodotto)

- **D1 — Coerenza viste**: la vista lotti (netta) e la vista Portfolio (period_fees_taxes/period_income)
  devono mostrare **gli stessi totali**? (Determina se l'allocazione lotti è puramente informativa o è la
  fonte di verità unica.)
- **D2 — Crossing LONG/SHORT**: la fee di una BUY che chiude short + apre long va al lotto aperto (long),
  alle closure short, o ripartita?
- **D3 — Income orfano / fee orfana**: restare non allocati (solo issue) è accettabile per l'utente, o si
  vuole un "lotto sintetico"/riga aggregata dedicata?
- **D4 — Priorità FEE/TAX**: congelare la priorità richiede un dataset BRIM reale (oggi assente). Si accetta
  di calibrarla su fixture sintetiche prima del rilascio?
- **D5 — Naming DTO**: rinominare `total_pnl`→`gross_total_pnl` (breaking frontend) o aggiungere solo i campi
  netti mantenendo i nomi attuali?

---

### Appendice — citazioni chiave

- Motore, event kinds: `backend/app/services/fifo_lot_engine.py:28-36, 369-433`
- Fasi/sort: `fifo_lot_engine.py:468-471, 308-311`
- Metodi non-qbq: `fifo_lot_engine.py:244-287` (consumer: solo test)
- Load motore (filtra qty≠0): `lots_analysis_service.py:504-506`
- Load income: `lots_analysis_service.py:508-525`
- Allocazione income (asset-wide, qty a tx.date): `lots_analysis_service.py:914-982`
- Frammento attivo (half-open): `lots_analysis_service.py:1691-1692`
- Summary/formule lorde: `lots_analysis_service.py:984-1083` (total_pnl `:1044`, total_return `:1047-1050`)
- Return history: `lots_analysis_service.py:1470-1472`
- `compute_holding_value`: `utils/financial/valuation_utils.py:19-26`
- WAC ignora qty==0: `utils/financial/wac_utils.py:99-102`
- Portfolio Engine income/fee: `portfolio_engine.py:834-851`, DTO `schemas/portfolio.py:310, 326, 396-398`
- DTO lotto: `schemas/portfolio.py:513-545` (`extra="forbid"` `:516`)
- Transaction model / related_transaction_id: `db/models.py:564-685`
- Validazione FEE/TAX (qty=0, amount<0, asset opzionale): `schemas/transactions.py:232-300`
- Import DTO senza related_transaction_id (solo link_uuid): `schemas/transactions.py:127-132`
- Pairing solo TRANSFER/FX: `transaction_service.py:1298-1302, 1381-1382`; `portfolio_engine.py:81-86`
- Audit BRIM per plugin: vedi tabella §9 (citazioni per file).
