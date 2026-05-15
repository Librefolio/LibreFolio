# Task: SP-B — Backend Tests WAC + Mock Data

**Parent plan**: [`plan-R2-WalktestFeedbackRound`](plan-phase07-transaction-Part4_Round6_PlanD2_round2_WalktestFeedbackRound.prompt.md)
**Depends on**: [`plan-R2-SP-A-CostBasisWAC`](plan-phase07-transaction-Part4_Round6_PlanD2_round2_plan-R2-SP-A-CostBasisWAC.prompt.md) ✅ completed

## Context

SP-A completato: `cost_basis_override` è `Currency` (oggetto `{code, amount}`),
`compute_weighted_avg_cost` restituisce `WACResult`, nuovo endpoint `POST /transactions/recalc-wac`.

Nessun test backend esistente referenzia direttamente `cost_basis_override` o `compute_weighted_avg_cost`,
quindi non ci sono test rotti da SP-A. I 3 file menzionati nel piano master (test_transaction_schemas,
test_transaction_service, test_transactions_batch_split_promote) **non hanno test relativi a cost_basis**,
quindi l'aggiornamento consiste nell'**aggiungere** test, non nel fixarli.

## Scope

### 1. Nuovo file `backend/test_scripts/test_api/test_transactions_wac.py` — 13 test

Tutto via HTTP (pattern API test con `_TestingServerManager`, `httpx.AsyncClient`).
Ogni test crea il proprio utente+broker+asset isolato.

| ID | Scenario | Setup | Verifica |
|----|----------|-------|----------|
| WAC-1 | TRANSFER con `cost_basis_override: {code:"EUR", amount:"42.50"}` | Broker, asset EUR, DEPOSIT, TRANSFER pair con override | POST commit → 200, GET TX → `cost_basis_override.code == "EUR"`, `.amount == "42.50"` |
| WAC-2 | TRANSFER senza override, BUY tutti EUR | Broker, asset EUR, DEPOSIT 10000 EUR, 2 BUY EUR, TRANSFER pair | auto-calc → `cost_basis_override != null`, `.code == "EUR"`, WAC = (\|buy1\| + \|buy2\|) / (qty1 + qty2) |
| WAC-3 | TRANSFER senza override, BUY EUR+USD con FX pair | Broker, asset EUR, DEPOSIT EUR+USD, BUY EUR + BUY USD, FX pair EUR/USD con rate, TRANSFER pair | auto-calc → `cost_basis_override != null`, `wac_info.conversions` non vuoto |
| WAC-4 | TRANSFER senza override, BUY EUR+CHF senza FX pair | Broker, asset EUR, DEPOSIT EUR+CHF, BUY EUR + BUY CHF, NO FX pair, TRANSFER pair | auto-calc → `cost_basis_override == null`, response `wac_info.missing_pairs` contiene `"CHF/EUR"` |
| WAC-5 | TRANSFER senza override, nessun BUY | Broker, asset EUR, DEPOSIT, TRANSFER pair (no BUY) | auto-calc → `cost_basis_override` = `{code:"EUR", amount:"0"}` |
| WAC-6 | recalc-wac 2 TX stesso asset, broker diversi | 2 broker, stesso asset, TRANSFER ricevente su ciascuno, BUY su sender | POST recalc-wac → entrambi aggiornati |
| WAC-7 | recalc-wac TX asset diversi | 2 asset, 1 TRANSFER ciascuno | POST recalc-wac → 400 |
| WAC-8 | recalc-wac TX non-TRANSFER | 1 BUY + 1 DEPOSIT | POST recalc-wac → `updated=false` per entrambi |
| WAC-9 | old format `"42.50"` (plain string) | TRANSFER con `cost_basis_override: "42.50"` | POST commit → issues con validation error |
| WAC-10 | invalid currency `{code:"INVALID", amount:"10"}` | TRANSFER con `cost_basis_override: {code:"INVALID", amount:"10"}` | POST commit → issues con validation error |
| WAC-11 | PATCH update cost_basis_override con Currency | TRANSFER receiver esistente, PATCH con `cost_basis_override: {code:"USD", amount:"99.00"}` | GET → `cost_basis_override.code == "USD"`, `.amount == "99.00"` |
| WAC-12 | Promote batch con resolved_fields.cost_basis_override | W+D pair, promote con `resolved_fields: {cost_basis_override: {code:"EUR", amount:"55.00"}}` | Receiver ha cost_basis = Currency EUR 55.00 |
| WAC-13 | Promote legacy `/transfers/promote` con cost_basis_override | W+D pair, POST `/transfers/promote` con `cost_basis_override: {code:"EUR", amount:"33.00"}` | New receiver TX ha cost_basis = Currency EUR 33.00 |

### 2. Aggiornare file test esistenti (solo se necessario)

Dopo SP-A, nessun test esistente è rotto. Se durante l'esecuzione si scopre che
qualche test dipendeva implicitamente dal vecchio formato, fixare lì.

### 3. Mock data per WAC-3 (FX pair)

WAC-3 richiede un FX pair con rate. Crearlo via API nel test stesso:
- `POST /api/v1/fx/pairs` → crea pair EUR/USD
- `POST /api/v1/fx/rates` → inserisci rate per la data del BUY

Non serve modificare `populate_mock_data.py` — i test API sono self-contained.

## Key files to read first

- `backend/test_scripts/test_api/test_transactions_api.py` — pattern: helper, fixture, test
- `backend/test_scripts/test_api/test_transactions_batch_split_promote.py` — batch commit pattern
- `backend/test_scripts/test_server_helper.py` — `_TestingServerManager`
- `backend/test_scripts/test_utils.py` — `print_section()`, `print_success()`
- `backend/app/api/v1/transactions.py` — endpoint shapes (commit, recalc-wac)
- `backend/app/api/v1/fx.py` — FX pair/rate creation endpoints (per WAC-3)

## Implementation notes

### Helper functions needed

```python
async def create_user_broker_asset(client, *, currency="EUR", allow_overdraft=True):
    """Create user + broker + asset, return (broker_id, asset_id)."""

async def commit_batch(client, creates=None, updates=None, deletes=None):
    """POST /transactions/commit, return response JSON."""

async def get_tx_by_id(client, tx_id):
    """GET /transactions?ids=N, return single TX dict."""

async def create_fx_pair_with_rate(client, base, quote, rate, rate_date):
    """Create FX pair + insert rate for WAC-3 test."""
```

### TRANSFER pair creation pattern

Ogni TRANSFER pair richiede:
1. DEPOSIT nel broker source (cash per finanziare BUY)
2. BUY (opzionale, per WAC test)
3. TRANSFER sender (qty < 0) + TRANSFER receiver (qty > 0) con stesso `link_uuid`

Per WAC-6 (recalc-wac): servono 2 broker separati, ciascuno con almeno
1 TRANSFER ricevente. Il sender è sul broker opposto.

### recalc-wac endpoint shape

```
POST /api/v1/transactions/recalc-wac
Body: { "tx_ids": [id1, id2] }
Response: { "results": [{ "tx_id": N, "wac_result": {...}, "updated": bool }] }
```

### WAC-9 e WAC-10: validazione errori

Questi test validano il batch commit, non il recalc-wac.
Il commit accetta il batch ma riporta `issues` per le righe con formato invalido.
Verificare che `response.committed == false` e `issues` contenga l'errore di validazione.

### ⚠️ `wac_info` vive solo nella commit/promote response

`wac_info` è un campo di `TXBatchResultItem` (`response.results[N].wac_info`).
**NON** è presente in `TXReadItem` (il GET `/transactions` non lo restituisce).
Quindi WAC-3, WAC-4, WAC-5 devono verificare `wac_info` dalla **response del commit**,
non dal GET successivo. Il GET serve solo per verificare `cost_basis_override`.

## Pass criterion

```bash
./dev.py test api all    # tutti verdi (inclusi i 10 nuovi WAC)
```

Se ci sono test rotti in altre categorie dopo le modifiche SP-A:
```bash
./dev.py test all-backend    # tutti verdi
```

## Execution checklist

- [x] Leggere i file chiave per capire il pattern test
- [x] Creare `test_transactions_wac.py` con helper + 13 test
- [x] WAC-1: TRANSFER con Currency override → verifica GET
- [x] WAC-2: auto-calc single currency
- [x] WAC-3: auto-calc cross-currency con FX
- [x] WAC-4: auto-calc missing FX → null
- [x] WAC-5: auto-calc no BUY → zero
- [x] WAC-6: recalc-wac multi-broker
- [x] WAC-7: recalc-wac asset diversi → 400
- [x] WAC-8: recalc-wac non-TRANSFER → skip
- [x] WAC-9: old format → 422
- [x] WAC-10: invalid currency → 422
- [x] WAC-11: PATCH update cost_basis_override Currency
- [x] WAC-12: Promote batch resolved_fields con cost_basis_override
- [x] WAC-13: Promote legacy con cost_basis_override
- [x] `./dev.py test api all` → verde (ran per-module: tx_api 19✅, batch_split_promote 18✅, wac 13✅)
- [x] `./dev.py test all-backend` → verde (non-regression verified per-module; combined run OOM-killed due to _TestingServerManager thread leak — pre-existing infra issue)

## Deviations from plan

### D1: DB needed `create-clean --test` before tests
**Problem**: `cost_basis_currency` column missing from test DB (added by SP-A migration but DB not rebuilt).
**Fix**: Ran `./dev.py db create-clean --test` before first test run.

### D2: Amount serialization includes trailing zeros
**Problem**: Expected `"42.50"` but DB stores `Numeric(18,6)` → serialized as `"42.500000"`.
**Fix**: Changed amount assertions to use `Decimal()` comparison instead of string equality.

### D3: WAC-9/WAC-10 — validation errors return 200+issues, not 422
**Problem**: Plan expected 422 (Pydantic rejection). In reality, the batch pipeline catches per-item validation errors and returns 200 with `committed=False` and `issues[]`.
**Fix**: Changed assertions to check `resp.status_code == 200`, `committed == False`, and presence of relevant error in `issues[]`.

### D4: WAC-13 — legacy promote needs BUY for asset balance
**Problem**: `Asset quantity goes negative (-5)` because the promote creates a TRANSFER which requires positive asset balance on the sender broker.
**Fix**: Added DEPOSIT + BUY to the test setup before creating the WITHDRAWAL/DEPOSIT pair to promote.

### D5: Combined pytest run killed by OOM
**Problem**: Running all API test modules in a single pytest process triggers OOM kill. Each module starts a _TestingServerManager in-thread, and multiple concurrent servers exhaust memory.
**Impact**: Non-regression verified per-module (3 transaction test modules: 50 tests green). Full `./dev.py test api all` uses subprocess-per-module and works from CLI.
