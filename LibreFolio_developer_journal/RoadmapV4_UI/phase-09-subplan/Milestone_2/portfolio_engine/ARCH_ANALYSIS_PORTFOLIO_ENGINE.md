# LibreFolio — Portfolio Calculation Engine: Architectural Analysis

> **Type:** Technical deep-dive report  
> **Purpose:** Design input for new Portfolio Calculation Engine  
> **Constraint:** No code modification. No refactor. No new features beyond scope.  
> **Date:** 2026-06-19  
> **DB Sample:** Prod DB (1 user, 1 broker "directa", 10 assets all EUR, 104 transactions)

---

## Files Analyzed

| File | Role |
|------|------|
| `backend/app/db/models.py` | All ORM models — Transaction, Asset, PriceHistory, FxRate, BrokerUserAccess |
| `backend/app/services/portfolio_service.py` | get_summary(), get_history(), compute_wac_iterative() |
| `backend/app/services/fx.py` | convert_bulk() — single FX entry point |
| `backend/app/utils/financial/roi_utils.py` | TWRR, MWRR, Simple ROI series |
| `backend/app/utils/financial/wac_utils.py` | compute_wac_from_txlist() — pure WAC math |
| `backend/app/utils/financial/fifo_utils.py` | calculate_fifo_lots() — FIFO math |
| `backend/app/utils/financial/valuation_utils.py` | compute_holding_value() |
| `backend/app/schemas/portfolio.py` | PortfolioSummary, PortfolioHistoryPoint, AllocationItem |
| `backend/app/schemas/wac.py` | WACPreviewResultItem, WACQualifyingTX, WACMissingPairInfo |
| `backend/app/api/v1/portfolio_api.py` | POST /portfolio/summary, POST /portfolio/history, GET /portfolio/lots |

---

## 1. Transaction Subsystem

### 1.1 DB Model: Transaction

Table: `transactions`. Key fields:

| Field | Type | Nullable | Description |
|-------|------|----------|-------------|
| `id` | int PK | no | |
| `broker_id` | int FK→brokers | no | |
| `asset_id` | int FK→assets | yes | NULL for cash-only transactions |
| `type` | TransactionType enum | no | |
| `date` | date | no | Settlement date |
| `quantity` | Numeric(18,6) | no, default=0 | Asset delta: +buy/in, −sell/out |
| `amount` | Numeric(18,6) | no, default=0 | Cash delta: +receive, −spend |
| `currency` | varchar(3) | yes | Required when amount ≠ 0 |
| `related_transaction_id` | int FK→transactions | yes | DEFERRABLE DEFERRED, bidirectional |
| `cost_basis_override` | Numeric(18,6) | yes | Frozen cost basis for TRANSFER_IN |
| `cost_basis_currency` | varchar(3) | yes | Currency of cost_basis_override |
| `asset_event_id` | int FK→asset_events | yes | Link to corporate action event |
| `tags` | text | yes | Comma-separated |
| `description` | text | yes | |

### 1.2 TransactionType enum — sign rules

| Type | qty | amount | currency | related_id | Cash effect |
|------|-----|--------|----------|-----------|-------------|
| BUY | >0 | <0 | required | — | −(money spent) |
| SELL | <0 | >0 | required | — | +(money received) |
| DIVIDEND | 0 | >0 | required | — | +(internal return) |
| INTEREST | 0 | >0 | required | — | +(internal return) |
| DEPOSIT | 0 | >0 | required | — | +(external CF in) |
| WITHDRAWAL | 0 | <0 | required | — | −(external CF out) |
| FEE | 0 | <0 | required | — | −(cost) |
| TAX | 0 | <0 | required | — | −(cost) |
| ADJUSTMENT | ±≠0 | 0 | — | optional | none |
| TRANSFER | ±≠0 | 0 | — | **required** | none |
| FX_CONVERSION | 0 | ≠0 | required | **required** | ± (pair nets to 0) |
| CASH_TRANSFER | 0 | ≠0 | required | **required** | ± (pair nets to 0) |

**Prod DB verification (2026-06-19):**  
Only BUY/SELL/DEPOSIT/FEE/INTEREST/TAX present. No TRANSFER, FX_CONVERSION, CASH_TRANSFER, WITHDRAWAL in this portfolio. All amounts EUR.

### 1.3 Risposta alle domande specifiche

**Il portfolio engine può calcolare cash semplicemente sommando tutti i cash delta accessibili?**

> **SÌ, con una precisazione.** `amount` è già algebricamente signato per ogni tipo.  
> `cash(date) = SUM(amount * share_percentage)` su tutte le transazioni con `date ≤ target_date`  
> convertite in base_currency. Zero filtri per tipo necessari.  
> L'unica eccezione è `ADJUSTMENT` (amount=0 by design) e `TRANSFER` (amount=0 by design) — ma non impattano la formula perché amount=0.

**Ci sono transaction type con amount valorizzato ma che NON devono impattare cash?**

> **NO.** Tutti i tipi con `amount ≠ 0` hanno impact diretto sulla liquidità del broker.  
> Non esiste alcun tipo con amount valorizzato che sia "neutro" per il cash.

**Ci sono transaction type che impattano cash ma non hanno amount direttamente usabile?**

> **NO nei tipi presenti.** Per FX_CONVERSION e CASH_TRANSFER (non presenti in prod ma modellati):  
> ogni leg ha il proprio `amount` signato. La somma delle due leg netta a zero sull'aggregato  
> (il broker A perde, il broker B guadagna) — ma **all'interno di un singolo broker** l'amount  
> della leg pertinente è corretto e usabile direttamente. Non serve logica speciale.

**BUY/SELL hanno già amount signato dal punto di vista del portfolio?**

> **SÌ.** Verificato da DB prod:  
> BUY: amount < 0 (min=-10000, max=-27.52) → cash drain  
> SELL: amount > 0 (384.84) → cash inflow  
> Nessuna inversione di segno necessaria.

**DEPOSIT/WITHDRAWAL hanno già amount signato?**

> **SÌ.**  
> DEPOSIT: amount > 0 (20 → 10000) → cash in  
> WITHDRAWAL: amount < 0 (non in prod, ma per costruzione model amount <0)  
> Nessuna inversione di segno necessaria.

**FX_CONVERSION e CASH_TRANSFER: singola transazione o coppia?**

> **COPPIA BIDIREZIONALE** linkata tramite `related_transaction_id`.  
> Entrambe le transazioni si puntano vicendevolmente.  
> La FK usa `DEFERRABLE INITIALLY DEFERRED` per permettere insert in una sola transazione DB.  
> Ciascuna leg ha il proprio `amount` signato relativo al suo broker.  
> Per il portfolio engine multi-broker: sommare solo le leg dei broker accessibili.  
> Per un broker singolo: prendere solo la leg pertinente (quella con `broker_id` del broker).

---

## 2. Cash Ledger

### 2.1 Dove viene calcolata la cash oggi

**`get_summary()` — `portfolio_service.py` ~L596-622**

```python
# Somma algebrica di TUTTI i transaction amount (ogni tipo)
for tx in broker_txns:
    broker_cash[tx.currency] += tx.amount * share     # dict per currency
    amount_base_signed = convert_to_base(tx.amount, tx.currency, tx.date)
    if tx.type in _CASH_FLOW_TYPES:  # solo DEPOSIT + WITHDRAWAL
        total_invested += amount_base_signed * share
        cash_flows.append(...)   # per MWRR/TWRR
```

**Incoerenza critica in `get_summary()`:**  
`broker_cash` è calcolata correttamente da TUTTI i tipi (somma algebrica).  
`total_invested` è calcolata SOLO da DEPOSIT/WITHDRAWAL — corretto per definizione di capitale investito.  
**Ma `total_invested` non è la cash!** Sono due cose diverse.

**`get_history()` — `portfolio_service.py` ~L400, `_build_history_series()`**

```python
# Somma algebrica completa — zero filtri per tipo
for row in sorted(transactions):
    cash_delta_by_date[row.date] += row.amount * row.share
```

`_build_history_series()` include TUTTI i transaction type con amount ≠ 0.  
**Questo è corretto** per la cash ledger.

**Differenza tra summary e history:**

| | get_summary() | get_history() |
|--|--------------|--------------|
| Cash ledger | somma algebrica completa ✅ | somma algebrica completa ✅ |
| `total_invested` | solo DEPOSIT−WITHDRAWAL | calcolato da cash flows series |
| Transaction scope | tutte le tx del broker | tutte le tx del broker |
| FX conversion | per ogni tx a data tx | per ogni tx a data tx |

**Formula proposta:**
> `cash(date) = cumsum(amount * share_percentage)` su tutte le transazioni accessibili `date ≤ target_date` convertite in base_currency.  
> **Corretta. Nessuna eccezione.** Tutti i tipi contribuiscono con il loro amount già signato.  
> Le uniche transazioni con `amount = 0` (ADJUSTMENT, TRANSFER) contribuiscono zero per costruzione — non richiedono esclusione esplicita.

---

## 3. Asset Price Subsystem

### 3.1 Modello PriceHistory

Table: `price_history`. Unico constraint: `(asset_id, date)`.  
Campi: `open, high, low, close, adjusted_close` (tutti Numeric(18,6), nullable).  
Campi chiave: `close` (usato per mark-to-market), `currency` (non-nullable), `source_plugin_key`.  
**Nessun campo per distinguere prezzi manuali vs provider vs importati** — solo `source_plugin_key` (string).

**Prod DB:** tutti e 10 gli asset hanno prezzi dal 2024-06-15 a oggi (735 punti = ~2 anni giornalieri).

### 3.2 Funzioni per recupero prezzi

**Funzione interna `_price_on_date(sorted_prices, query_date)`** — `portfolio_service.py` ~L336:

```python
def _price_on_date(sorted_prices, query_date):
    """Backward fill: ritorna l'ultimo (close, currency) con date <= query_date.
    sorted_prices = [(date, close, currency), ...] ordinato ASC.
    Usa bisect_right per O(log N). Ritorna None se nessun prezzo."""
    dates = [p[0] for p in sorted_prices]
    idx = bisect.bisect_right(dates, query_date) - 1
    if idx < 0:
        return None
    return close, ccy
```

**Comportamento stale:** nessun limite di staleness. Backward fill illimitato.  
Se il prezzo più recente è di 6 mesi fa, viene comunque usato senza warning.

**`_bulk_load_asset_prices(asset_ids, date_from, date_to)`** — `portfolio_service.py` ~L484:  
Carica tutti i `(date, close, currency)` per un set di asset in un range. Usato in `get_history()`.

**`_get_latest_price(asset_id)`** — ritorna `(close, currency, date)` del record più recente per quell'asset. Usato in `get_summary()`.

### 3.3 Risposta alle domande specifiche

**Per ogni asset detenuto, il portfolio engine può chiedere ultimo prezzo disponibile ≤ date?**

> **SÌ.** La funzione `_price_on_date()` implementa esattamente questo.  
> Per il nuovo engine: `_bulk_load_asset_prices()` + `_price_on_date()` sono già pronti.  
> Possono essere estratti come utility senza duplicazione.

**Come identificare asset senza neanche un prezzo storico?**

> Query: `SELECT asset_id FROM holdings WHERE asset_id NOT IN (SELECT DISTINCT asset_id FROM price_history)`.  
> Nel codice: `get_summary()` lo gestisce a ~L690: se `price_data is None`, aggiunge `asset.display_name` a `missing_prices_assets`.

**Dati per `missing_price_assets` da mandare al frontend:**

> Attualmente `missing_prices_assets` è solo `set[str]` (display_name).  
> Per il DTO target servono: `asset_id`, `symbol`, `name`, `broker_id`, `broker_name`, `first_position_date`, `quantity`, `currency`.  
> I dati ci sono tutti nelle tabelle — servono solo nella serializzazione.

**Esiste distinzione prezzi manuali / provider / importati?**

> **NO** distinzione nel modello PriceHistory. Solo `source_plugin_key` (string).  
> Prezzi inseriti manualmente avranno `source_plugin_key = "manual"` o simile — non standardizzato.  
> **Non esiste un boolean `is_manual`** o enum separato.

---

## 4. Forex Subsystem

### 4.1 Modelli

**`FxRate`** — table `fx_rates`:
- `(date, base, quote)` unico — una riga per pair per giorno
- `base < quote` per constraint — sempre ordine alfabetico
- `rate` = `1 base = rate * quote` (es. EUR/USD: 1 EUR = 1.09 USD)
- Reverso calcolato come `1/rate` nel service layer

**`FxConversionRoute`** — table `fx_conversion_routes`:
- Configura quale provider usa quale pair
- Supporta multi-step chain (RON→EUR→USD)
- Priority per fallback

### 4.2 Funzione principale: `convert_bulk()`

**Firma:**
```python
async def convert_bulk(
    session,
    conversions: list[tuple[Currency, str, date]],  # (from_Currency, to_code, as_of_date)
    raise_on_error: bool = True
) -> tuple[list[tuple[Currency, date, bool] | None], list[str]]
    # returns: [(converted_Currency, rate_date, backward_fill_applied), ...], [errors]
```

**Comportamento:**
- Batch query unica per tutti i pair necessari
- Backward fill illimitato (nessun limite temporale)
- Identity conversion (EUR→EUR) gestita inline — no query
- `raise_on_error=False` → ritorna None per conversioni fallite, raccoglie errori
- Gestisce solo coppie dirette (stored alphabetically). Triangolazione non supportata direttamente da `convert_bulk` — passa attraverso `FxConversionRoute` in altri servizi.

### 4.3 Risposta alle domande specifiche

**Il portfolio engine può delegare tutte le conversioni FX al forex subsystem?**

> **SÌ, completamente.** `convert_bulk()` è l'unico entry point necessario.  
> Il nuovo engine non deve fare arithmetic su FX rates — solo chiamare `convert_bulk()` con `raise_on_error=False`.

**Ci sono punti nel portfolio_service che duplicano logica FX?**

> **SÌ, due punti:**
> 1. `_convert_to_base()` — helper privato in `portfolio_service.py` che wrappa `convert_bulk()`. Ridondante ma non duplica logica, solo wrapping.  
> 2. In `get_history()` e `get_summary()` il pattern di conversione è ripetuto con codice quasi identico. Il nuovo engine dovrebbe unificare.

**Come convertire cash delta / market value / open cost basis:**

> Tutti tramite `convert_bulk()`:
> - **cash delta:** `convert_bulk([(Currency(tx.currency, tx.amount), base_ccy, tx.date)])`
> - **market value:** `convert_bulk([(Currency(price_ccy, market_val), base_ccy, price_date)])`
> - **open cost basis:** WAC è già in una valuta target — `convert_bulk([(Currency(wac_ccy, wac * qty), base_ccy, today)])`

**Cosa succede se manca FX per una data?**

> Con `raise_on_error=False`: la conversione ritorna `None`, l'errore va in `errors` list.  
> Il portfolio engine deve:
> 1. Accumulare `missing_fx_pairs` da ogni `None` result
> 2. Escludere quel valore dalla somma (non imputare 0)
> 3. Segnalare al frontend via `data_quality`

---

## 5. WAC / Cost Basis Subsystem

### 5.1 Funzioni principali

**`compute_wac_iterative(session, broker_id, asset_id, as_of_date, asset_currency)`**  
→ Async, con I/O DB. Restituisce `WACPreviewResultItem` con:
- `wac: Currency` — WAC per unità nella valuta target
- `wac_qualifying_txs: list[WACQualifyingTX]` — ogni tx con running_wac
- `wac_missing_pairs: list[WACMissingPairInfo]`

**`compute_wac_from_txlist(txs, target_currency)`** — Pure math, O(N).

### 5.2 Caratteristiche del WAC

| Aspetto | Comportamento |
|---------|--------------|
| Scope | Per (broker_id, asset_id, as_of_date) |
| Currency | Valuta del target: default = valuta dell'ultimo BUY. Non è base_currency. |
| Include fee | NO — solo amount del BUY entra nel costo unitario |
| Tiene conto di SELL | SÌ — SELL riduce il pool ma non cambia WAC per unità |
| TRANSFER/ADJUSTMENT | SÌ — modificano qty. TRANSFER_IN usa `cost_basis_override` se presente |
| SPLIT | Gestito come ADJUSTMENT (qty delta, amount=0) — WAC per unità si aggiusta |
| Pool qty | Ritornata in `WACCalcResult.pool_qty` |
| Storico giornaliero | **NON esiste.** WAC è computato as-of date. Non esiste serie storica WAC. |
| cost_basis_mode=auto | La qty arriva al pool WAC senza cambiarlo (TRANSFER_IN "al costo corrente") |

### 5.3 Formula proposta: validazione

```
open_cost_basis(asset, broker, date) = WAC(asset, broker, date) × quantity_held(asset, broker, date)
```

**Validità:** PARZIALMENTE VALIDA con importante caveat.

- `WAC(asset, broker, date)` = `compute_wac_iterative(..., as_of_date=date).wac.amount`  ✅
- `quantity_held(asset, broker, date)` = sum(quantity) per BUY/SELL fino a date ✅
- **MA:** `WAC.wac.code` è la valuta del target (valuta dell'ultimo BUY), NON base_currency.
  - Se l'utente ha comprato in USD ma la base currency è EUR, WAC è in USD.
  - Serve conversione: `open_cost_basis_EUR = WAC_USD × qty × FX(USD→EUR, date)`
  - **Rischio doppia conversione:** `compute_wac_iterative` già converte i costi unitari in target_currency. Se poi il chiamante converte di nuovo senza sapere in che valuta è già il WAC, si ottiene una doppia conversione.

**Formula corretta per `open_cost_basis_total`:**

```
for each (asset, broker):
    wac_result = compute_wac_iterative(broker_id, asset_id, as_of_date=date)
    wac_currency = wac_result.wac.code          # NON assumere sia base_currency
    qty = compute_quantity_held(broker_id, asset_id, date)
    ocb_in_wac_ccy = wac_result.wac.amount * qty
    ocb_in_base = convert_bulk([(Currency(wac_currency, ocb_in_wac_ccy), base_ccy, date)])
open_cost_basis_total = sum(ocb_in_base)
```

### 5.4 WAC storico — gap per book_value series

**Problema chiave:** `compute_wac_iterative` NON ha una firma `get_wac_series(date_from, date_to)`.  
Per costruire la serie giornaliera di `book_value = open_cost_basis + cash` serve WAC per ogni giorno del calendario.

**Opzioni:**
1. Chiamare `compute_wac_iterative` per ogni giorno → O(N_days × N_assets × N_txs) — troppo lento
2. Usare `wac_qualifying_txs` per ricostruire la serie WAC inline:  
   - `compute_wac_iterative(..., as_of_date=date_to)` ritorna tutte le qualifying TXs con `running_wac`  
   - Si può ricostruire WAC per ogni giorno forward-filling tra un TX e il successivo  
   - **Questa è la via praticabile senza nuovo codice.**  
   - Complessità: O(N_assets × N_brokers) chiamate, poi O(N_days) interpolazione per asset.

**Risposta alle domande:**

> **Questa formula è valida?** Sì, con la caveat sulla doppia conversione FX sopra descritta.  
> **Il WAC disponibile è quello che serve per book_value?** Sì se si gestisce la valuta correttamente.  
> **Serve funzione nuova `get_open_cost_basis(asset_id, broker_id, date)`?** Non è necessaria se si usa il pattern `wac_qualifying_txs` + forward-fill. Sarebbe comunque utile come wrapper per chiarezza.  
> **Rischio doppia conversione FX?** SÌ — `compute_wac_iterative` converte i costi in target_currency. Il chiamante deve usare `wac_result.wac.code` come source currency, non assumere sia già in base_currency.  
> **WAC e quantity calcolate con logiche diverse?** SÌ — `compute_wac_iterative` usa solo `qty ≠ 0` transactions. `get_summary()` calcola `net_qty` come sum(qty) per BUY+SELL. Bisogna assicurarsi di usare la stessa logica.  
> **Se WAC non è storico, cosa manca per serie giornaliera?** Manca solo il forward-fill giornaliero dei `wac_qualifying_txs`. Non serve nuovo storage.

---

## 6. FIFO / Lotti

### 6.1 Stato attuale

`fifo_utils.py` implementa `calculate_fifo_lots(transactions: list[FIFOTransactionInput])`:
- Input: solo BUY e SELL, già FX-convertiti, già in una valuta comune
- Output: `OpenLot[]`, `ClosedLot[]`, `total_realized_pnl`, `total_unrealized_quantity`
- Algoritmo: deque, BUY→push, SELL→consume FIFO

**`get_lots()` in `portfolio_service.py`** espone già FIFO via `GET /portfolio/lots`.

### 6.2 Dati disponibili per FIFO futuro

| Dato | Disponibile | Note |
|------|-------------|------|
| Transaction ID | ✅ | per tracciabilità lot→tx |
| Data settlement | ✅ | `date` |
| Quantity delta | ✅ | signed |
| Cost (amount) | ✅ | signed, in transaction currency |
| related_transaction_id | ✅ | per TRANSFER tra broker |
| cost_basis_override | ✅ | per TRANSFER_IN — costo "frozen" dalla source |
| cost_basis_currency | ✅ | valuta del cost_basis_override |

### 6.3 Casi complessi FIFO

| Caso | Complessità | Note |
|------|------------|------|
| Vendita parziale lotto | Media | Deque gestisce già parzialmente (`remaining_quantity`) |
| Vendita multi-lotto | Media | Deque gestisce già consume successivo |
| SPLIT (ADJUSTMENT qty) | Alta | Cambia il prezzo unitario di ogni lotto. L'algoritmo attuale non lo gestisce |
| TRANSFER tra broker | Alta | `cost_basis_override` preserva il costo. Ma i lotti sono "tronchi" — non si sa quale lotto originale è stato trasferito |
| ADJUSTMENT generico | Alta | Potrebbe essere dividend reinvestment, bonus shares — semantica varia |
| FX_CONVERSION | Bassa | Non impatta qty |
| Cambio valuta (re-denomination) | Molto alta | Rarissimo, non modellato |

### 6.4 Risposta alle domande

> **Possiamo rimandare FIFO senza bloccare il nuovo portfolio engine?** **SÌ.** WAC/open_cost_basis è già calcolabile. FIFO serve per realized P&L ma non per NAV/book_value.  
> **Usare WAC ora rende difficile aggiungere FIFO dopo?** **NO.** `fifo_utils.py` è già separato da `wac_utils.py`. Sono moduli indipendenti. Il cambio sarebbe solo nel layer che sceglie quale "cost method" usare.  
> **Conviene introdurre già interfaccia astratta `CostBasisProvider`?** **SÌ, consigliato.** Con un'interfaccia `CostBasisProvider.get_open_cost_basis(asset_id, broker_id, date) → Decimal` si può switchare WAC→FIFO senza toccare il resto dell'engine.

---

## 7. Portfolio Service Attuale — Mappa

### 7.1 `get_summary()` — dove si calcola cosa

| Calcolo | Riga approx | Note |
|---------|-------------|------|
| Cash per currency (broker) | ~L598-603 | somma algebrica TUTTI i tipi ✅ |
| total_invested | ~L620-622 | solo DEPOSIT+WITHDRAWAL |
| WAC per asset | ~L640-646 | `compute_wac_iterative(today)` |
| net_qty per asset | ~L657 | sum(qty) BUY+SELL |
| Market value corrente | ~L662-691 | `_get_latest_price()` + FX |
| missing_prices_assets | ~L691 | se `price_data is None` |
| open_cost_basis (per holding) | ~L700-701 | WAC × qty × share |
| gain_loss per holding | ~L703-705 | market_value − cost_basis |
| allocation_by_type/sector/geo | ~L715-727 | pesi su market_value |
| ROI metrics (TWRR/MWRR) | ~L797-822 | da cash_flows list |
| total_gl / total_gl_pct | ~L825-826 | nav − invested |

### 7.2 `get_history()` — dove si calcola cosa

| Calcolo | Riga approx | Note |
|---------|-------------|------|
| cash_delta per giorno | `_build_history_series()` ~L381 | somma algebrica, no filtri tipo ✅ |
| cumulative quantities per asset | ~L936-946 | solo BUY+SELL (`_HOLDING_TYPES`) |
| Prices bulk load | ~L927 | `_bulk_load_asset_prices()` |
| market_value giornaliero | ~L979-997 | qty × price × FX (bulk) |
| NAV giornaliero | ~L1000 | `cash + market_value` |
| Period re-basing | ~L1021-1035 | CF sintetico per metriche % |
| TWRR series | ~L1039 | `calculate_twrr_series()` |
| ROI series | ~L1040 | `calculate_simple_roi_series()` |
| MWRR series | ~L1042 | `calculate_mwrr_series()` in thread |

### 7.3 Incoerenze e problemi identificati

**Naming confusion:**
- `invested_value` in `PortfolioHistoryPoint` = market value degli asset (NON capitale investito!). Il nome è fuorviante.
- `invested_value` in `_HistoryCalcPoint` viene settato a `market_value` in ~L999.
- `total_invested` in `get_summary()` = somma DEPOSIT−WITHDRAWAL (capitale versato). Diverso concetto, stesso nome base.

**Gradini falsi BUY/SELL:**
- `get_history()` usa `_build_history_series()` che include amount di BUY/SELL nella cash.  
- Un BUY da −1000 EUR farà scendere la cash di 1000 ma dovrebbe far salire market_value di ~1000.  
- Se il prezzo dell'asset non è disponibile esattamente quel giorno, il NAV cala falsamente.  
- **Questo è il bug principale che causa "gradini" nel grafico.** Si manifesta quando il prezzo ha delay rispetto alla data transazione.

**missing_prices_assets:**
- In `get_summary()`: rilevato e tracciato correttamente come `set[str]` (display_name).
- In `get_history()`: asset senza prezzo su un giorno specifico viene silenziosamente escluso dalla market_value — NON tracciato come dato mancante. Il NAV viene sottoestimato senza warning.

**Duplicazione cash/invested logic:**
- `get_summary()` e `get_history()` costruiscono entrambi i cash_flows per TWRR/MWRR in modi diversi.
- `get_summary()` usa liste esplicite per ogni broker_tx.
- `get_history()` usa `_build_history_series()` poi ri-filtra `rows` per DEPOSIT/WITHDRAWAL.

---

## 8. Access Control

### 8.1 Modello BrokerUserAccess

Table: `broker_user_access`. Campi chiave:

| Campo | Tipo | Note |
|-------|------|------|
| user_id | int FK→users | |
| broker_id | int FK→brokers | |
| role | UserRole enum | OWNER / EDITOR / VIEWER |
| share_percentage | Numeric(7,6) | 0.0–1.0. Default 1. Per broker condivisi. |

**Prod DB:** 1 user, 1 broker "directa", role=OWNER, share=1.

### 8.2 Dove viene applicato access control

**`_get_user_broker_access(user_id, broker_ids)`** — `portfolio_service.py` ~L443:
```python
stmt = select(BrokerUserAccess).where(BrokerUserAccess.user_id == user_id)
if broker_ids:
    stmt = stmt.where(BrokerUserAccess.broker_id.in_(broker_ids))
```

**Il portfolio engine riceve una lista di `BrokerUserAccess` rows** — non raw broker_ids.  
`share_percentage` è applicato: `amount * share` per ogni aggregazione.

**PriceHistory e FX rates:** globali — nessun access control. Tutti gli utenti vedono gli stessi prezzi e tassi FX.

### 8.3 Risposta alle domande

**Viewer/Editor/Owner con accesso allo stesso broker vedono gli stessi report?**

> **SÌ.** Il ruolo non filtra i dati visti — filtra solo le operazioni di scrittura (CRUD).  
> Il portfolio engine usa solo `broker_id` e `share_percentage` dalla `BrokerUserAccess`.  
> Due utenti con ruoli diversi sullo stesso broker vedono identici NAV/ROI.

**Rischi di leak dati tra broker condivisi?**

> **Nessun rischio.** Il filtro è a livello di `BrokerUserAccess.user_id = current_user.id`.  
> Un utente non vede mai transazioni di broker ai quali non ha accesso.

**Quali filtri devono essere applicati prima del calculation engine?**

> Il nuovo engine deve ricevere:  
> 1. `user_id` → risolve `BrokerUserAccess` rows (una query)  
> 2. `broker_ids` opzionale → filtro aggiuntivo sull'accesso  
> Il resto è delegato: `accesses: list[BrokerUserAccess]` con `broker_id` e `share_percentage`.  
> **Nessun altro filtro necessario prima dell'engine.**

---

## 9. Output DTO — Verifica Estendibilità

### 9.1 PortfolioHistoryPoint (attuale → target)

| Campo | Attuale | Target | Azione |
|-------|---------|--------|--------|
| `date` | ✅ | ✅ | nessuna |
| `cash_value` | ✅ `Currency` | ✅ | nessuna |
| `invested_value` | ✅ `Currency` | → `market_value` | **rinomina** (naming errato) |
| `nav_value` | ✅ `Currency` | ✅ | nessuna |
| `open_cost_basis` | ❌ | `Currency` | **aggiungere** |
| `book_value` | ❌ | `Currency` | **aggiungere** |
| `unrealized_gain_loss` | ❌ | `Currency` | **aggiungere** |
| `twrr` | ✅ `Optional[SafeDecimal]` | ✅ | nessuna |
| `mwrr` | ✅ `Optional[SafeDecimal]` | ✅ | nessuna |
| `roi` | ✅ `Optional[SafeDecimal]` | ✅ | nessuna |

**Estendibile senza breaking change?** SÌ — aggiungere campi opzionali con `Optional[Currency] = None`.  
La rinomina `invested_value → market_value` **è un breaking change** sul client TypeScript.

### 9.2 PortfolioSummary (attuale → target)

| Campo | Attuale | Target | Azione |
|-------|---------|--------|--------|
| `net_worth` | ✅ `Currency` | ✅ | nessuna |
| `market_value` | ❌ | `Currency` | **aggiungere** (attualmente folded in net_worth) |
| `cash_total` | ✅ `Currency` | ✅ | nessuna |
| `open_cost_basis` | ❌ | `Currency` | **aggiungere** |
| `book_value` | ❌ | `Currency` | **aggiungere** |
| `unrealized_gain_loss` | ❌ | `Currency` | **aggiungere** |
| `total_invested` | ✅ `Currency` | ✅ | nessuna (= capitale versato) |
| `total_gain_loss` | ✅ `Currency` | ✅ | nessuna |
| `simple_roi_percent` | ✅ | ✅ | nessuna |
| `twrr_percent` | ✅ | ✅ | nessuna |
| `mwrr_percent` | ✅ | ✅ | nessuna |
| `allocation_by_type` | ✅ | ✅ | nessuna |
| `allocation_by_sector` | ✅ | ✅ | nessuna |
| `allocation_by_geography` | ✅ | ✅ | nessuna |
| `missing_prices_assets` | ✅ `List[str]` | `List[MissingPriceAsset]` | **sostituire** con DTO ricco |
| `missing_fx_pairs` | ✅ `List[WACMissingPairInfo]` | ✅ | nessuna |
| `data_quality` | ❌ | `DataQualityReport` | **aggiungere** |

### 9.3 MissingPriceAsset DTO (nuovo)

```python
class MissingPriceAsset(BaseModel):
    asset_id: int
    symbol: Optional[str]     # identifier_ticker o identifier_isin
    name: str                 # display_name
    broker_id: int
    broker_name: str
    first_position_date: date # prima transazione BUY per questo asset in questo broker
    quantity: Decimal         # qty attuale detenuta
    open_cost_basis: Optional[Currency]  # WAC × qty se WAC disponibile
    currency: str             # valuta asset
```

Tutti i campi necessari sono disponibili nei modelli esistenti.

---

## 10. Validazione Algoritmo Target

### 10.1 Valutazione step-by-step

**Step 1 — Risolvi broker accessibili**
> ✅ Già funziona. `_get_user_broker_access(user_id, broker_ids)` → `list[BrokerUserAccess]`.

**Step 2 — Carica tutte le transazioni accessibili fino a date_to**
> ✅ Già funziona. `_get_transactions(broker_id, date_to=date_to)` per ogni broker access.

**Step 3 — Normalizza ogni transazione in (date, broker_id, asset_id, quantity_delta, cash_delta, currency, is_external_cash_flow)**
> ✅ Fattibile direttamente dai campi Transaction.  
> `cash_delta = tx.amount` (già signato)  
> `quantity_delta = tx.quantity` (già signato)  
> `is_external_cash_flow = tx.type in {DEPOSIT, WITHDRAWAL}` (booleano semplice)  
> Nessuna funzione di normalizzazione esistente — va scritta (triviale, ~10 righe).

**Step 4 — Converti cash_delta in base_currency tramite forex subsystem**
> ✅ `convert_bulk()` batch per tutte le transazioni in un passaggio.  
> **Attenzione:** le transazioni con `currency = NULL` (ADJUSTMENT, TRANSFER con amount=0) devono essere skipparse silenziosamente (amount=0 comunque).

**Step 5 — Costruisci calendario giornaliero**
> ✅ `_build_history_series()` fa esattamente questo. Può essere riusata o riscritta in modo più pulito.

**Step 6 — Per ogni giorno: cash, quantity, market_value, open_cost_basis, book_value, NAV, unrealized_gain_loss, external_cash_flow**
> ✅ Tutte le parti esistono:
> - cash: somma cumulativa cash_delta ✅
> - quantity: cumulative BUY+SELL ✅
> - market_value: `_price_on_date()` + `compute_holding_value()` + `convert_bulk()` ✅
> - open_cost_basis: **GAP** — serve forward-fill WAC da `wac_qualifying_txs`. Non esiste funzione, va costruita.
> - book_value: `open_cost_basis + cash` — triviale ✅
> - NAV: `market_value + cash` ✅
> - unrealized_gain_loss: `nav - book_value` ✅
> - external_cash_flow: filtra `is_external_cash_flow` ✅

**Step 7 — ROI/TWRR/MWRR dalla serie**
> ✅ `roi_utils.py` è già pronto con tutte e tre le funzioni.

**Step 8 — Allocation current dall'ultimo giorno**
> ✅ Logica già in `get_summary()`. Può essere estratta come funzione pura.

**Step 9 — Allocation history come 100% stacked su NAV**
> ⚠️ Non esiste. Richiede:
> - Tracciare la composizione per tipo/settore/geo su ogni giorno del calendario
> - Per ogni asset: quantity × price per giorno → % del NAV
> - Cash come "Liquidity" category
> - **Non esiste codice per questo.** Va costruito sul loop giornaliero dell'Step 6.

**Step 10 — data_quality report**
> ⚠️ Parzialmente. `missing_prices_assets` e `missing_fx_pairs` già raccolti.  
> `incomplete_nav_dates` (giorni in cui almeno un asset era senza prezzo) — **non esiste**.  
> `stale_prices` — **non esiste** (nessun threshold di staleness definito).

### 10.2 Fattibilità complessiva

**Fattibile senza implementare nulla di nuovo?** Quasi. I gap sono:

| Gap | Impatto | Soluzione |
|-----|---------|-----------|
| WAC serie giornaliera | Alto — blocca book_value history | Forward-fill da `wac_qualifying_txs` (~50 righe) |
| `missing_price_assets` DTO ricco | Medio — oggi è solo `List[str]` | Arricchire schema (~15 righe) |
| Allocation history stacked | Medio — non esiste | Aggiungere loop su ogni giorno (+asset composition) |
| `incomplete_nav_dates` | Basso — qualità dato | Flag per giorni con NAV parziale |
| Normalizzazione transazione | Basso — triviale | ~10 righe |

---

## 11. Lacune Tecniche da Colmare

1. **WAC storico per asset/broker/date:** Non esiste funzione che restituisca WAC a una data passata in forma di serie. `compute_wac_iterative` ricomputa dall'inizio ogni volta. Per la serie book_value bisogna usare `wac_qualifying_txs` con forward-fill giornaliero. **Da implementare: funzione `wac_to_daily_series(qualifying_txs, dates) → dict[date, Decimal]`.**

2. **`MissingPriceAsset` DTO strutturato:** L'attuale `missing_prices_assets: List[str]` non permette al frontend di linkare all'asset o dare contesto. **Da implementare: schema `MissingPriceAsset` con i campi identificati in §9.3.**

3. **Allocation history (stacked per giorno):** Non esiste. Richiede di tracciare la composizione asset+cash per ogni giorno nel loop del calendario. **Da implementare: accumulo `allocation_by_type/sector/geo` per giorno nel loop.**

4. **`DataQualityReport` DTO:** Aggregare `missing_fx_pairs`, `missing_price_assets`, `incomplete_nav_dates`, `stale_prices` in un oggetto strutturato. **Da implementare: nuovo schema.**

5. **Rinomina `invested_value` → `market_value` in `PortfolioHistoryPoint`:** Breaking change sul client TS — richiede `./dev.py api sync` e aggiornamento frontend.

6. **Normalizzazione trasparente dei tipi transazione:** Non esiste un metodo `normalize_for_portfolio(tx) → NormalizedTx`. Oggi la logica è embedded in `get_history()`. Estrarre come funzione pura migliora testabilità.

---

## 12. Raccomandazione Implementativa

### Ordine di implementazione consigliato

1. **Creare `NormalizedTx` dataclass + funzione di normalizzazione** — base di tutto l'engine. Dipendenze: zero.

2. **Creare `wac_to_daily_series()`** — forward-fill WAC da `qualifying_txs`. Pura matematica, no I/O. Sblocca book_value.

3. **Aggiungere campi `open_cost_basis`, `book_value`, `unrealized_gain_loss` a `PortfolioHistoryPoint` e `PortfolioSummary`** — opzionali, no breaking change.

4. **Sostituire `missing_prices_assets: List[str]` con `List[MissingPriceAsset]`** — breaking change minore, richiede api sync.

5. **Implementare il nuovo engine come service separato** — non modificare `portfolio_service.py` esistente. Nuovo file `portfolio_engine.py`. Riusa: `convert_bulk`, `calculate_twrr/mwrr_series`, `compute_wac_iterative`, `_price_on_date`, `compute_holding_value`.

6. **Aggiungere allocation history** — solo dopo che il calendario loop è stabile.

7. **Aggiungere `DataQualityReport`** — last step, aggrega tutto.

### Struttura del nuovo engine

```
portfolio_engine.py
├── _normalize_transactions()     # NormalizedTx da Transaction[]
├── _build_daily_calendar()       # date range → date[]
├── _accumulate_cash_series()     # date → cash cumulativa
├── _accumulate_qty_series()      # date → {asset_id: qty}
├── _compute_market_value()       # date → market_value (riusa _price_on_date + convert_bulk)
├── _compute_open_cost_basis()    # date → open_cost_basis (riusa wac_to_daily_series)
├── _compute_roi_metrics()        # TWRR/MWRR/ROI (riusa roi_utils.py)
├── _compute_allocation_snapshot()# 1 data → allocation (riusa logica get_summary)
├── _build_data_quality()         # raccoglie tutti i missing
└── run_portfolio_engine()        # orchestrator pubblico
```

---

## 13. Rischi Principali

| Rischio | Livello | Mitigation |
|---------|---------|-----------|
| **Performance WAC serie:** `compute_wac_iterative` per ogni asset×broker è O(N_txs) per chiamata. Con 50 asset e 5 anni di dati può essere lento. | Alto | Chiamare 1 volta per asset, forward-fill giornaliero nel loop. Non chiamare per ogni giorno. |
| **Backward fill prezzi illimitato:** un prezzo di 6 mesi fa valorizza l'asset come se fosse oggi. | Medio | Aggiungere `stale_threshold_days` e segnalare in data_quality. Non bloccare il calcolo. |
| **WAC currency ≠ base_currency:** rischio doppia conversione se il chiamante assume WAC già in base_currency. | Alto | Sempre usare `wac_result.wac.code` come source currency prima di convertire. |
| **FX_CONVERSION coppia parziale:** se solo una leg è accessibile all'utente, il saldo cash risulta errato. | Basso (non presente in prod) | Documentare il caso. Gestire con flag `incomplete_conversion_pair`. |
| **Allocation history memoria:** tracciare composizione per ogni giorno per ogni asset può essere O(N_days × N_assets) in memoria. | Medio | Generare on-demand, non caricare tutto in RAM per range multi-anno. Paginare o calcolare per finestre. |
| **Naming breaking change:** rinomina `invested_value → market_value` rompe il client TS generato. | Basso-Medio | Coordinare con `./dev.py api sync` + frontend update in un'unica PR. |

---

*Fine report — analisi statica del codice, nessuna modifica eseguita.*

