# Plan: WAC Backend Cleanup — Schema Consolidation + Tests

**Parent plan**: [`plan-R2-SP-C-BugfixRound2-WacPreview`](plan-phase07-transaction-Part4_Round6_PlanD2_round2_plan-R2-SP-C-BugfixRound2-WacPreview.prompt.md)
**Scope**: Backend-only refactoring + test coverage (Steps 6 del parent plan + TODO pending)
**Triggered by**: Architecture feedback round 2

---

## 🎯 Obiettivo

Consolidare gli schema WAC eliminando duplicazioni, usare `DateRangeModel` come unica interfaccia temporale, riusare `TXCreateItem` per le pending TX (validazione semantica inclusa), eliminare `asset_price_at_date` in favore del service layer esistente, poi scrivere test completi.

---

## Decisioni

| Decisione | Scelta |
|-----------|--------|
| `as_of_date` su WACPreviewItem | ❌ Rimosso — solo `date_range: DateRangeModel` |
| Semantica `DateRangeModel` nel WAC | `start` = inizio range, `end` = opzionale (se None → oggi) |
| `WACPendingTX` | ❌ Rimosso — sostituito da `WACPendingTXItem(TXCreateItem)` + campo `id` |
| Validazione semantica TXCreateItem | ✅ Ereditata (pacchetto deve essere corretto) |
| `asset_price_at_date` | ❌ Eliminata — usa `AssetSourceManager.get_prices_bulk` (service layer diretto) |
| Inline imports | ❌ Spostati al top |
| Backward-fill asset prices | 🐛 Bug fix — allineato al comportamento FX (illimitato all'indietro) |

---

## Steps

### Step 0: Bugfix — `get_prices_bulk` backward-fill illimitato (come FX)

**Bug identificato**: `AssetSourceManager.get_prices_bulk()` fa backward-fill **solo dentro il range richiesto**. Se il primo giorno del range non ha un prezzo, il campo resta vuoto. Il sistema FX (`convert_bulk`) invece fa `date <= max_date` **senza lower bound**, tornando indietro indefinitamente e fornendo `backward_fill_info.days_back` per informare il chiamante della staleness.

**Comportamento atteso** (uguale a FX): se non c'è prezzo alla data richiesta, il sistema torna il prezzo più recente disponibile **prima** del range, con `BackwardFillInfo(actual_rate_date=X, days_back=N)`. Nessun limite artificiale.

**File**: `backend/app/services/asset_source.py`

**Fix** in `get_prices_bulk()` (~linea 1911):
1. Dopo la query principale (`date >= global_start AND date <= global_end`), per ogni asset che **non ha un prezzo a `start_date`** nel `price_map`, eseguire una query supplementare:
   ```python
   SELECT * FROM price_history
   WHERE asset_id = :aid AND date < :start
   ORDER BY date DESC LIMIT 1
   ```
2. Il risultato (`seed_price`) viene passato a `_build_backward_filled_series` come parametro `seed_price`.
3. Se `seed_price` è `None` → nessun prezzo esiste nel DB prima del range richiesto → è corretto non ritornare nulla per quei giorni (il backward-fill non ha dati da cui partire).

**Fix** in `_build_backward_filled_series()` (~linea 1829):
1. Aggiungere parametro opzionale: `seed_price: Optional[PriceHistory] = None`
2. Inizializzare `last_known = seed_price` instead of `None`
3. Il resto della logica rimane identico — il seed funge da fonte per il backward-fill dei giorni iniziali senza prezzo

**Impatto**: tutti i chiamanti di `get_prices_bulk` beneficiano automaticamente. Nessuna breaking change nell'interfaccia — la response ha gli stessi campi (`backward_fill_info` era già previsto). Se `seed_price=None` (nessun prezzo storico precedente al range), i giorni iniziali senza prezzo restano vuoti — comportamento corretto e intenzionale.

**Ottimizzazione**: la query supplementare per-asset è O(N) queries dove N = numero di asset senza prezzo a start. Per il caso WAC (1 asset) è trascurabile. Per bulk con molti asset, si potrebbe fare una singola query con `UNION ALL` o window functions — ma per ora la versione semplice è sufficiente.

**Post**: nessun `api sync` necessario (la response non cambia schema)

---

### Step 1: Schema — `WACPreviewItem` solo `DateRangeModel`

**File**: `backend/app/schemas/transactions.py`

- Rimuovere `as_of_date: Optional[date_type]`
- Rimuovere il `@model_validator` "exactly one"
- Cambiare `date_range` da `Optional[DateRangeModel]` a `DateRangeModel` (required)
- Property `effective_date` → `self.date_range.end or date.today()`
- Aggiornare docstring: `start` = inizio periodo, `end` = fine (se None → oggi)

**File**: `backend/app/api/v1/transactions.py`
- L'endpoint già usa `item.effective_date` → nessun cambio

**Post**: `./dev.py api sync`

### Step 2: Schema — `WACPendingTXItem` estende `TXCreateItem`

**File**: `backend/app/schemas/transactions.py`

- Eliminare classe `WACPendingTX`
- Creare `WACPendingTXItem(TXCreateItem)` con:
  - `id: Optional[int] = Field(None, description="DB id to override, or None for new")`
  - `asset_id: int` (override da Optional a required — WAC ha sempre un asset)
  - `link_uuid` ereditato da TXCreateItem (default None, ok per WAC)
- In `WACPreviewRequest`: `pending_txs: List[WACPendingTXItem]`

**File**: `backend/app/services/transaction_service.py`
- Nella prep-layer di `compute_wac_iterative()`:
  - `ptx.cash.amount` al posto del vecchio `ptx.amount`
  - `ptx.cash.code` al posto del vecchio `ptx.currency`
  - `ptx.cost_basis_override` resta uguale (è Currency in entrambi)
  - `ptx.type.value` (TransactionType enum, non più str grezzo)

**Post**: `./dev.py api sync`

### Step 3: Import — spostare inline al top

**File**: `backend/app/services/transaction_service.py`

- Spostare `WACPreviewResultItem`, `WACQualifyingTX` al block import (linee 34-59)
- Spostare `WACInputTX`, `compute_wac_from_txlist`, `determine_target_currency` al block import
- Verificare no circular: `python -c "from backend.app.services.transaction_service import compute_wac_iterative"`

### Step 4: Sostituire `asset_price_at_date` con service layer

**File**: `backend/app/services/transaction_service.py`

- Eliminare la funzione `asset_price_at_date()`

**File**: `backend/app/api/v1/transactions.py`
- Rimuovere import `asset_price_at_date`
- Importare `AssetSourceManager` e `FAPriceQueryItem` da `schemas/prices.py`
- Nell'endpoint `wac_preview`:
  - Creare request: `FAPriceQueryItem(asset_id=..., date_range=DateRangeModel(start=effective_date, end=effective_date))`
    - Nessun range artificiale di 30gg — dopo Step 0, `get_prices_bulk` fa backward-fill illimitato automaticamente
  - Chiamare `await AssetSourceManager.get_prices_bulk([req], session)`
  - Estrarre l'ultimo punto prezzo (close + backward_fill_info)
  - Convertire in `Currency` per la response
- Se nessun punto prezzo → `asset_price_missing=True`

**Post**: `./dev.py api sync` (se cambi alla response)

### Step 5: Test — Adattare `TestRecalcWAC` → `TestWACPreview`

**File**: `backend/test_scripts/test_api/test_transactions_wac.py`

- Rinominare `TestRecalcWAC` → `TestWACPreview`
- WAC-6: multi-broker → `POST /transactions/wac-preview` con `date_range`
- WAC-7: convertire a wac-preview (invalid request → 422)
- WAC-8: convertire a wac-preview (empty asset → WAC 0)
- Aggiungere nuovi test:
  - **WAC-P1**: BUY 10@100 + SELL 3 → WAC = 100 (invariato dalla riduzione)
  - **WAC-P2**: BUY 10@100 + BUY 5@200 → WAC = (1000+1000)/15 = 133.33
  - **WAC-P3**: pending_txs override (new) → WAC cambia rispetto a solo-DB
  - **WAC-P4**: excluded_tx_ids → TX esclusa non contribuisce
  - **WAC-P5**: FX missing pair → `wac=null, wac_missing_pairs=["CHF/EUR"]`
  - **WAC-P6**: same-date BUY+SELL → nessun negative (additions first)
  - **WAC-P7**: date_range con end=None → usa oggi come end
  - **WAC-P8**: pending_txs override by id → sovrascrive DB row nel calcolo WAC
  - **WAC-P9**: pool reset (BUY + full SELL + new BUY) → WAC = nuovo prezzo
- Verificare `TestWACCostBasis` (WAC-1 to WAC-5):
  - ✅ TRANSFER commit senza override → cost_basis resta NULL (no auto-calc)
  - ✅ Asserzioni adattate per rimuovere aspettative su `wac_info` nel commit

### Step 6: Test — Unit test `financial_utils`

**File**: `backend/test_scripts/test_services/test_financial_utils.py` (nuovo)

Test puri senza server:
- **FU-1**: Lista vuota → WAC=0, qty=0
- **FU-2**: Solo BUY → WAC = unit price
- **FU-3**: BUY + SELL → WAC invariato, qty ridotta
- **FU-4**: BUY + BUY diversi prezzi → media ponderata
- **FU-5**: Same-date BUY+SELL → reductions after additions (no negative)
- **FU-6**: Clamp: qty negativa → (0, 0) instead of error
- **FU-7**: TRANSFER_IN con override → contribuisce a WAC
- **FU-8**: TRANSFER_IN senza override → add_zero_cost
- **FU-9**: `determine_target_currency`: most frequent wins
- **FU-10**: `determine_target_currency`: tie → asset_currency
- **FU-11**: Pool reset (BUY, full SELL, new BUY) → WAC = nuovo prezzo
- **FU-12**: Multiple reductions consecutive → WAC stabile

**Test runner**: registrato in `scripts/test_runner/_backend_services.py` → `./dev.py test services financial-utils`

---

## Execution Checklist

- [x] Step 0: Bugfix backward-fill `get_prices_bulk`
- [x] Step 1: WACPreviewItem → solo DateRangeModel
- [x] Step 2: WACPendingTXItem estende TXCreateItem
- [x] Step 3: Import inline → top
- [x] Step 4: Eliminare asset_price_at_date → service layer
- [x] Step 5: Test API — TestWACPreview (22 test: WAC-1…P9 + validation + promote)
- [x] Step 6: Test unit — financial_utils (12 test: FU-1…FU-12)

---

## Completion Notes (2026-05-19)

**Additional cleanups applied post-plan**:
- `effective_date` property renamed to `end_date` (cleaner semantics)
- All inline imports in `wac_preview` endpoint moved to file top (`BackwardFillInfo`, `FAPriceQueryItem`, `AssetSourceManager`)
- `./dev.py api sync` run after property rename
- Test runner registration: `services financial-utils` added to `_backend_services.py`

**Final test counts**:
- `test_financial_utils.py`: 12 tests (FU-1…FU-12) — pure math, no server
- `test_transactions_wac.py`: 22 tests (WAC-1…WAC-P9 + WAC-9…WAC-13) — API, with server

**Parent plan Step 6 coverage**: ✅ Fully covered. All API + unit tests described in parent plan Step 6 are implemented and passing. The cleanup plan supersedes the parent's Step 6 requirements.
