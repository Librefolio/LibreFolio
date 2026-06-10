# Phase 09 — Milestone 1: Piano Implementativo di Dettaglio

> **Data esecuzione**: 2026-06-10  
> **Sorgente**: [`implementation_plan.md`](../../../../../LibreFolio_developer_journal/RoadmapV4_UI/phase-09-subplan/Milestone_1/implementation_plan.md)  
> **Stato**: ✅ Completato  
> **Scope**: Backend-only (nessuna modifica frontend)  
> **Goal**: Servizi finanziari puri (WAC/TWRR/MWRR/FIFO), orchestratore portfolio, 4 nuovi endpoint REST

---

## Stato Codebase Pre-Implementazione

| File | Stato Pre |
|------|-----------|
| `backend/app/utils/financial_utils.py` | `compute_wac_from_txlist()` + `WACInputTX` — matematica pura |
| `backend/app/services/wac_service.py` | `compute_wac_iterative()` — orchestrazione async WAC |
| `backend/app/api/v1/analytics.py` | `analytics_router` (prefix `/analytics`) — solo `POST /wac` |
| `backend/app/schemas/analytics.py` | Solo schemi WAC |
| `backend/test_scripts/test_services/test_financial_utils.py` | Test per financial_utils.py |
| `Pipfile` | Nessuna dipendenza `scipy` |

### Dipendenze Import da Migrare

- `transaction_service.py` → importa `compute_wac_iterative` da `wac_service`
- `analytics.py` (endpoint) → importa `compute_wac_iterative` da `wac_service`
- `wac_service.py` → importa da `financial_utils`
- `test_financial_utils.py` → importa da `financial_utils`

---

## Grafo delle Dipendenze tra Step

```
P1 (scipy) → S1 (folder restructure)
                 ├── S2 (roi_utils) ──────────┐
                 │      └── S2-tests          │
                 ├── S3 (fifo_utils) ──────────┤
                 │      └── S3-tests          │
                 └── S4-schemas               │
                                              ↓
                              S4-portfolio-svc (git mv wac_service + add PortfolioService)
                                 └── S4-portfolio-tests
                                        ↓
                              S5-endpoints (add portfolio_router)
                                 └── S5-api-tests
                                        ↓
                              S6-verify (api sync + front check)
                                        ↓
                              S7-nonregression
```

---

## Pre-Requisiti

### P1 — Aggiungere `scipy` a Pipfile ✅

```ini
# Pipfile [packages]
scipy = "*"
```

Poi: `pipenv install` → installato `scipy 1.17.1`

---

## Step 1 — Ristrutturazione Utils → `financial/` ✅

### 1.1 Creare la cartella

```bash
mkdir -p backend/app/utils/financial
touch backend/app/utils/financial/__init__.py
```

### 1.2 Spostare `financial_utils.py` → `financial/wac_utils.py`

```bash
git mv backend/app/utils/financial_utils.py backend/app/utils/financial/wac_utils.py
```

### 1.3 Aggiornare `__init__.py` con export

```python
# backend/app/utils/financial/__init__.py
from backend.app.utils.financial.wac_utils import (
    WACInputTX, WACCalcResult,
    compute_wac_from_txlist, determine_target_currency,
)
```

### 1.4 Import rotti da correggere (3 file)

| File | Import Vecchio | Import Nuovo |
|------|---------------|-------------|
| `backend/app/services/wac_service.py` | `...financial_utils import ...` | `...financial.wac_utils import ...` |
| `backend/test_scripts/test_services/test_financial_utils.py` | `...financial_utils import ...` | `...financial.wac_utils import ...` |

> `wac_service.py` stesso viene rinominato nello Step 4.

---

## Step 2 — Creare `roi_utils.py` ✅

> **File creato**: `backend/app/utils/financial/roi_utils.py`

### Tipi e Interfacce

```python
class CashFlowInput(NamedTuple):
    date: date
    amount: Decimal  # Segno: negativo=deposito (soldi IN), positivo=prelievo (soldi OUT)

class NAVSnapshot(NamedTuple):
    date: date
    nav: Decimal

@dataclass(frozen=True)
class TWRRPoint:
    date: date
    twrr: Decimal

@dataclass(frozen=True)
class MWRRPoint:
    date: date
    mwrr: Decimal | None  # None se scipy non converge
```

### Funzioni Implementate

| Funzione | Algoritmo | Regole Chiave |
|----------|-----------|---------------|
| `calculate_simple_roi(current_nav, total_invested)` | `(NAV - Invested) / Invested` | Ritorna `0` se `invested == 0` |
| `calculate_twrr(nav_snapshots, cash_flows)` | Prodotto HPR per sotto-periodi: `Π(1+HPR_i) - 1` | Snapshot POST-CF; salta sotto-periodo se `V_start == 0` |
| `calculate_twrr_series(...)` | Accumulazione iterativa O(N) | Un punto per snapshot |
| `calculate_mwrr(...)` | XIRR: `scipy.optimize.newton` su NPV=0 | Ritorna `None` se non converge (no raise) |
| `calculate_mwrr_series(...)` | XIRR per ogni snapshot, **warm-start** | x0 = risultato step precedente → 1-2 iterazioni Newton |

### ⚠️ Bug Trovato e Corretto Durante Implementazione

**Problema**: Formula del TWRR scritta come `v_end - cf_amount` invece di `v_end + cf_amount`.

**Causa**: Le snapshot sono POST-CF. Con la convenzione `deposito = cf_amount < 0`:
```
pre_CF_NAV = post_CF_NAV + cf_amount   ← CORRETTO  (es: 2100 + (-1000) = 1100)
pre_CF_NAV = post_CF_NAV - cf_amount   ← SBAGLIATO  (es: 2100 - (-1000) = 3100)
```

**Scoperto**: durante la scrittura del test `test_with_deposit_midway` che verifica il valore atteso `TWRR = 0.21`.

### Test (19 test, 19/19 ✅)

File: `backend/test_scripts/test_services/test_financial/test_roi_utils.py`

- `TestSimpleROI` (5 test): positivo, negativo, zero_invested, no_change, large_gain
- `TestTWRR` (5 test): no_cash_flows, deposit_midway, raises_on_1_snapshot, no_change, withdrawal
- `TestMWRR` (4 test): simple_1yr, same_date→None, no_convergence→None, result_is_Decimal
- `TestTWRRSeries` (2 test): matches_individual, empty_series
- `TestMWRRSeries` (3 test): one_point_per_snapshot, empty_series, warm_start_no_raise

---

## Step 3 — Creare `fifo_utils.py` ✅

> **File creato**: `backend/app/utils/financial/fifo_utils.py`

### Algoritmo

1. Ordina per `(date, id)` ascending
2. Usa `deque` come coda FIFO
3. BUY → `append` in coda
4. SELL → consuma dalla testa con `popleft`
   - Se lot ha qty sufficiente → match parziale, lot rimane in coda con qty ridotta
   - Se lot esaurito → rimuovi e avanza al successivo
5. Quanto rimasto in coda = `open_lots`

**Gestione errori**: oversell → `ValueError` con messaggio su possibile stock split.

### Test (11 test, 11/11 ✅)

File: `backend/test_scripts/test_services/test_financial/test_fifo_utils.py`

- single_buy_no_sell, buy_then_full_sell, buy_then_partial_sell
- two_buys_one_sell_fifo_order, sell_spans_multiple_lots
- realized_pnl_calculation, negative_pnl_on_loss
- oversell_raises_error, no_transactions, non_buy_sell_ignored
- complex_scenario (5 BUY + 3 SELL)

---

## Step 4 — Creare `portfolio_service.py` ✅

### 4.1 Rename

```bash
git mv backend/app/services/wac_service.py backend/app/services/portfolio_service.py
```

Import da aggiornare in 2 file:
- `transaction_service.py`: `from ...portfolio_service import compute_wac_iterative`
- `analytics.py` (endpoint): `from ...portfolio_service import compute_wac_iterative`

### 4.2 Classe `PortfolioService`

Metodi pubblici implementati:

```python
class PortfolioService:
    async def get_summary(user_id, broker_ids, include_breakdown) -> PortfolioSummary
    async def get_history(user_id, broker_ids, date_from, date_to) -> list[PortfolioHistoryPoint]
    async def get_asset_history(user_id, asset_id, broker_id) -> list[AssetHistoryPoint]
    async def get_lots(user_id, broker_id, asset_id) -> FIFOLotsResponse
```

### 4.3 Note Critiche di Implementazione

- **Event loop**: `calculate_mwrr_series` wrappato in `asyncio.to_thread()` — scipy è CPU-bound
- **share_percentage**: applicata sui valori raw del singolo broker PRIMA dell'aggregazione cross-broker
- **FX bulk**: usare `convert_bulk()` — no chiamate FX in loop

### 4.4 Schemi Pydantic Aggiunti

In `backend/app/schemas/analytics.py`:
`AllocationItem`, `PortfolioHolding`, `BrokerBreakdown`, `PortfolioSummary`,
`PortfolioHistoryPoint`, `AssetHistoryPoint`, `OpenLotSchema`, `ClosedLotSchema`, `FIFOLotsResponse`

> Tutti usano `SafeDecimal` (non `Decimal` raw) per evitare notazione scientifica nel JSON.

### ⚠️ Bug Trovato e Corretto Durante Test

**Problema**: Nel metodo `get_history`, il list comprehension finale usava la variabile `vals` non definita:
```python
# SBAGLIATO (NameError se daily non è vuoto)
cash_value=vals["cash"]

# CORRETTO
cash_value=daily[dt]["cash"]
```

**Scoperto**: dal test di integrazione `test_history_with_deposit` che chiamava il metodo con dati reali.
**Perché i test precedenti non lo catturavano**: `test_empty_history` passava perché `daily` era vuoto → il list comprehension non veniva mai eseguito.

### Test (11 test, 11/11 ✅)

File: `backend/test_scripts/test_services/test_financial/test_portfolio_service.py`

- `TestPortfolioServiceGetLots` (4): no_access, no_transactions, buy_only, buy_and_partial_sell
- `TestPortfolioServiceGetHistory` (3): empty, with_deposit, date_range_filter
- `TestPortfolioServiceGetSummary` (4): empty, with_breakdown, filter_by_broker, nonexistent_broker

---

## Step 5 — Endpoint API ✅

In `backend/app/api/v1/analytics.py`:
```python
portfolio_router = APIRouter(prefix="/portfolio", tags=["Portfolio"])
```

| Endpoint | Response Model |
|----------|---------------|
| `GET /portfolio/summary` | `PortfolioSummary` |
| `GET /portfolio/history` | `list[PortfolioHistoryPoint]` |
| `GET /portfolio/asset-history?asset_id=...` | `list[AssetHistoryPoint]` |
| `GET /portfolio/lots?broker_id=...&asset_id=...` | `FIFOLotsResponse` |

Registrazione in `backend/app/api/v1/router.py`:
```python
router.include_router(analytics.portfolio_router)
```

### Test API (15 test)

File: `backend/test_scripts/test_api/test_portfolio_analytics.py`

- Summary: unauthenticated→401, empty, with_data, filter_by_broker, include_breakdown, nonexistent_broker
- History: unauthenticated→401, empty, with_transactions, date_range_filter
- AssetHistory: unauthenticated→401, missing_asset_id→422, nonexistent_asset→[]
- FIFOLots: unauthenticated→401, missing_params→422, response_structure, no_access→empty

---

## Step 6 — Verifica API Sync & Frontend ✅

```bash
./dev.py api sync     # → generati tipi TS (PortfolioSummary, FIFOLotsResponse, ...)
./dev.py front check  # → 0 errori svelte-check
```

---

## Step 7 — Non-Regressione ✅

```bash
./dev.py test services financial-utils   # ✅
./dev.py test services transaction        # ✅
./dev.py test utils all                   # 9/9 ✅
./dev.py test schemas all                 # 5/5 ✅
```

---

## Riepilogo File Modificati

### Nuovi

| Path | Tipo |
|------|------|
| `backend/app/utils/financial/__init__.py` | modulo |
| `backend/app/utils/financial/wac_utils.py` | utils (git mv) |
| `backend/app/utils/financial/roi_utils.py` | utils (nuovo) |
| `backend/app/utils/financial/fifo_utils.py` | utils (nuovo) |
| `backend/app/services/portfolio_service.py` | service (git mv + esteso) |
| `backend/test_scripts/test_services/test_financial/__init__.py` | test module |
| `backend/test_scripts/test_services/test_financial/test_roi_utils.py` | test |
| `backend/test_scripts/test_services/test_financial/test_fifo_utils.py` | test |
| `backend/test_scripts/test_services/test_financial/test_portfolio_service.py` | test |
| `backend/test_scripts/test_api/test_portfolio_analytics.py` | test |

### Modificati

| Path | Modifica |
|------|----------|
| `Pipfile` | Aggiunto `scipy = "*"` |
| `backend/app/services/transaction_service.py` | Import: `wac_service` → `portfolio_service` |
| `backend/app/api/v1/analytics.py` | Import + `portfolio_router` + 4 endpoint |
| `backend/app/api/v1/router.py` | Registrazione `portfolio_router` |
| `backend/app/schemas/analytics.py` | Aggiunta schemi Portfolio |
| `backend/test_scripts/test_services/test_financial_utils.py` | Import path aggiornato |

---

## Bug Trovati e Corretti

| # | Metodo | Bug | Come Scoperto |
|---|--------|-----|---------------|
| 1 | `roi_utils.calculate_twrr` | `v_end - cf_amount` → `v_end + cf_amount` (segno convenzione snapshot POST-CF) | Test `test_with_deposit_midway` (verifica valore atteso 0.21) |
| 2 | `portfolio_service.get_history` | `vals["cash"]` → `daily[dt]["cash"]` (`NameError` nel list comprehension) | Test integrazione `test_history_with_deposit` (chiamata con dati reali) |

---

## Test Mancanti da Aggiungere (Gap Analysis)

> Vedi sezione dedicata: [missing_tests_gap_analysis.md](./missing_tests_gap_analysis.md)

**Sintesi**: mancano test unitari *puri* (senza DB) per la logica computazionale di
`get_history`, `get_summary` e `get_lots`. I test di integrazione attuali verificano
solo la struttura dell'output, non i valori. Un test che assertisce
`result[0].cash_value == Decimal("10000")` avrebbe trovato Bug 2 prima.
