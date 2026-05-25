# Task: SP-A — Cost Basis Override con Currency + WAC Service + recalc-wac endpoint

> **✅ STATUS (2026-05-24)**: COMPLETATO. Commit `92f4b1ba`.

**Parent plan**: [`plan-R2-WalktestFeedbackRound`](plan-phase07-transaction-Part4_Round6_PlanD2_round2_WalktestFeedbackRound.prompt.md)
**Next**: [`plan-R2-SP-B-BackendTests`](plan-phase07-transaction-Part4_Round6_PlanD2_round2_plan-R2-SP-B-BackendTests.prompt.md)

## Context
Leggi il piano master `plan-phase07-transaction-Part4_Round6_PlanD2_round2_WalktestFeedbackRound.prompt.md`
per il contesto completo. Leggi anche `bugfix_4_SplitSuggestPmcOverrideUx` per lo stato attuale
del cost_basis_override (oggi SafeDecimal, domani Currency).

## Scope — Steps 1-5 del piano master
Tutto il backend: DB model, Alembic, Pydantic schemas (TXCreateItem/TXUpdateItem/TXReadItem + WACResult +
WACConversionInfo + TXBatchResultItem), service compute_weighted_avg_cost con FX cross-currency,
auto-calc adattato ai 2 call-site, nuovo endpoint recalc-wac.

## What to implement

### Step 1: DB model + Alembic — `cost_basis_currency` column

- In `backend/app/db/models.py` (riga ~653, dopo `cost_basis_override`), aggiungere:
  ```python
  cost_basis_currency: Optional[str] = Field(
      default=None,
      sa_column=Column(String(3), nullable=True),
      description="Currency code for cost_basis_override (ISO 4217).",
  )
  ```
  con validator `_validate_currency_field` (riusare il pattern già presente per `currency` a riga 678).

- In `backend/alembic/versions/001_initial.py` (riga 274), aggiungere colonna dopo `cost_basis_override`:
  ```sql
  cost_basis_currency    VARCHAR(3),
  ```

- Eseguire `./dev.py db create-clean`.

### Step 2: Schema — `cost_basis_override` da `SafeDecimal` → `Currency`

In `backend/app/schemas/transactions.py`:

- **TXCreateItem** (riga 136): cambiare
  ```python
  cost_basis_override: Optional[SafeDecimal] = Field(...)
  ```
  in:
  ```python
  cost_basis_override: Optional[Currency] = Field(
      default=None,
      description="Frozen cost basis for TRANSFER_IN. Object {code, amount}.",
  )
  ```

- **TXUpdateItem** (riga 489): stesso cambio `SafeDecimal` → `Currency`.

- **TXReadItem** (riga 372): stesso cambio `SafeDecimal` → `Currency`.

- **TXReadItem.from_db_model()** (riga 404): aggiornare la costruzione:
  ```python
  # Build Currency from DB fields
  cost_basis = None
  if tx.cost_basis_override is not None and tx.cost_basis_currency is not None:
      cost_basis = Currency(code=tx.cost_basis_currency, amount=tx.cost_basis_override)

  return cls(
      ...
      cost_basis_override=cost_basis,
      ...
  )
  ```

- **TXTransferPromoteRequest** (riga 786): cambiare `cost_basis_override: Optional[SafeDecimal]` → `Optional[Currency]`.

- **TXPromoteBatchItem.resolved_fields** (riga 829): documentare che `cost_basis_override` in `resolved_fields` sarà un dict `{code, amount}` (non più una stringa decimale).

### Step 3: Nuovi schema — `WACConversionInfo` + `WACResult`

In `backend/app/schemas/transactions.py`, aggiungere (prima di `TXBatchResultItem`):

```python
class WACConversionInfo(BaseModel):
    """Single FX conversion applied during WAC calculation."""
    model_config = ConfigDict(extra="forbid")

    tx_id: int = Field(..., description="Transaction ID that needed conversion")
    from_currency: str = Field(..., description="Original currency of the transaction")
    to_currency: str = Field(..., description="Target currency for WAC")
    rate: SafeDecimal = Field(..., description="FX rate applied")
    rate_date: date_type = Field(..., description="Actual date of the FX rate used")
    stale_days: int = Field(0, ge=0, description="Days between TX date and rate date (0 = fresh)")


class WACResult(BaseModel):
    """Result of weighted average cost calculation with FX details."""
    model_config = ConfigDict(extra="forbid")

    wac: Optional[Currency] = Field(None, description="Calculated WAC. None if FX conversion failed.")
    conversions: list[WACConversionInfo] = Field(default_factory=list, description="FX conversions applied")
    missing_pairs: list[str] = Field(default_factory=list, description="FX pairs that could not be resolved (e.g. 'CHF/EUR')")
```

In `TXBatchResultItem` (riga 633), aggiungere:
```python
wac_info: Optional[WACResult] = None
```

### Step 4: Service — `compute_weighted_avg_cost` rewrite con FX

In `backend/app/services/transaction_service.py` (riga 59), riscrivere completamente:

```python
async def compute_weighted_avg_cost(
    session: AsyncSession,
    broker_id: int,
    asset_id: int,
    as_of_date: date_type,
    asset_currency: str,
) -> WACResult:
```

**Logica**:

1. Query BUY + incoming TRANSFER (qty > 0, con o senza cost_basis_override) per (broker_id, asset_id, date <= as_of_date).

2. **Determine target_currency**:
   - Contare le valute tra le TX qualificanti (BUY.currency, TRANSFER.cost_basis_currency).
   - Maggioritaria → target. Pareggio → `asset_currency` se presente tra le valute, altrimenti prima alfabeticamente.

3. **Per ogni TX con valuta ≠ target_currency**:
   - Costruire lista `conversions` per `convert_bulk()` da `fx.py`.
   - `convert_bulk(session, [(Currency(code=from_ccy, amount=cost), target_currency, tx.date), ...], raise_on_error=False)`

4. **Se anche una sola conversione FX fallisce** (None in results):
   - Return `WACResult(wac=None, conversions=[successe...], missing_pairs=["CHF/EUR", ...])`.

5. **Se total_qty == 0** (nessun errore FX):
   - Return `WACResult(wac=Currency(code=target_currency, amount="0"), conversions=[...], missing_pairs=[])`.

6. **Normal case**:
   - Calcolare `total_cost / total_qty` nella target_currency.
   - Return `WACResult(wac=Currency(code=target_currency, amount=wac), conversions=[...], missing_pairs=[])`.

**Import necessari**: `from backend.app.services.fx import convert_bulk`

### Step 5a: Adattare call-site #1 — promote (righe 1353-1365)

In `transaction_service.py`, sezione promote auto-calc:

```python
# Auto-calc cost_basis_override for TRANSFER receiver if not set
if target_type == TransactionType.TRANSFER:
    receiver = tx_a if (tx_a.quantity and tx_a.quantity > 0) else tx_b if (tx_b.quantity and tx_b.quantity > 0) else None
    sender = tx_b if receiver is tx_a else tx_a
    if receiver and receiver.cost_basis_override is None and sender.broker_id:
        # Fetch asset currency for target_currency determination
        asset_row = await self.session.execute(
            select(Asset.currency).where(Asset.id == receiver.asset_id)
        )
        asset_ccy = asset_row.scalar_one_or_none() or ""
        wac_result = await compute_weighted_avg_cost(
            self.session, sender.broker_id, receiver.asset_id, receiver.date, asset_ccy
        )
        if wac_result.wac is not None:
            receiver.cost_basis_override = wac_result.wac.amount
            receiver.cost_basis_currency = wac_result.wac.code
        else:
            receiver.cost_basis_override = None
            receiver.cost_basis_currency = None
    # Force sender override to null
    if sender:
        sender.cost_basis_override = None
        sender.cost_basis_currency = None
```

Propagare `wac_result` come `wac_info` nel `TXBatchResultItem` del promote result (riga 1377).

### Step 5b: Adattare call-site #2 — create link resolution (righe 1409-1424)

Stesso pattern: fetch `asset_currency` → call `compute_weighted_avg_cost()` → unpack `WACResult` → set `cost_basis_override` + `cost_basis_currency`. Propagare `wac_info` nel `TXBatchResultItem`.

### Step 5c: Adattare create path (riga 1225-1235)

Nella creazione TX da `TXCreateItem`, spacchettare il `Currency` object:

```python
tx = Transaction(
    ...
    cost_basis_override=item.cost_basis_override.amount if item.cost_basis_override else None,
    cost_basis_currency=item.cost_basis_override.code if item.cost_basis_override else None,
    ...
)
```

### Step 5d: Adattare update path (righe 1172-1173)

```python
if item.cost_basis_override is not None:
    tx.cost_basis_override = item.cost_basis_override.amount
    tx.cost_basis_currency = item.cost_basis_override.code
```

### Step 5e: Adattare promote endpoint legacy (riga 720-737)

In `promote_transfer_pair()`, la serializzazione del `cost_basis_override` (riga 737) deve cambiare:

```python
"cost_basis_override": {
    "code": req.cost_basis_override.code,
    "amount": format(req.cost_basis_override.amount, "f"),
} if req.cost_basis_override is not None else None,
```

### Step 5f: Adattare resolved_fields handling (righe 1326-1338)

Nel promote batch, `resolved_fields["cost_basis_override"]` sarà un dict `{code, amount}`. Parser:

```python
if "cost_basis_override" in item.resolved_fields:
    cbo_raw = item.resolved_fields["cost_basis_override"]
    if cbo_raw is not None:
        # Parse as Currency dict
        cbo_currency = Currency.model_validate(cbo_raw)
        cbo_amount = cbo_currency.amount
        cbo_code = cbo_currency.code
    else:
        cbo_amount = None
        cbo_code = None

    if tx_a.quantity and tx_a.quantity > 0:
        tx_a.cost_basis_override = cbo_amount
        tx_a.cost_basis_currency = cbo_code
        tx_b.cost_basis_override = None
        tx_b.cost_basis_currency = None
    elif tx_b.quantity and tx_b.quantity > 0:
        tx_b.cost_basis_override = cbo_amount
        tx_b.cost_basis_currency = cbo_code
        tx_a.cost_basis_override = None
        tx_a.cost_basis_currency = None
    else:
        tx_a.cost_basis_override = cbo_amount
        tx_a.cost_basis_currency = cbo_code
        tx_b.cost_basis_override = cbo_amount
        tx_b.cost_basis_currency = cbo_code
```

### Step 6: Nuovo endpoint — POST `/api/v1/transactions/recalc-wac`

In `backend/app/api/v1/transactions.py`:

```python
class RecalcWACRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    tx_ids: list[int] = Field(..., min_length=1, max_length=100)

class RecalcWACResponseItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    tx_id: int
    wac_result: WACResult
    updated: bool = Field(..., description="Whether the TX was actually updated")

class RecalcWACResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    results: list[RecalcWACResponseItem]
```

**Endpoint**:
```python
@tx_router.post("/recalc-wac", response_model=RecalcWACResponse)
async def recalc_wac(
    body: RecalcWACRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session_generator),
):
```

**Validazioni**:
1. Tutte le TX devono esistere.
2. Tutte devono avere lo **stesso asset_id** (non necessariamente stesso broker).
3. L'utente deve avere almeno EDITOR su ogni broker coinvolto.

**Logica**:
- Per ogni TX che è TRANSFER ricevente (qty > 0):
  - Trova il partner sender (via `related_transaction_id`).
  - Ricalcola WAC via `compute_weighted_avg_cost(session, sender.broker_id, tx.asset_id, tx.date, asset_ccy)`.
  - Salva `cost_basis_override` + `cost_basis_currency` dal `WACResult.wac`.
  - Return result.
- TX non-TRANSFER o sender → skip (updated=False, wac_result con wac=None).
- TODO per futura categoria `analytics/`.

## Key files to read first
- `backend/app/db/models.py` — Transaction model, cost_basis fields
- `backend/app/schemas/transactions.py` — TXCreateItem, TXUpdateItem, TXReadItem, TXBatchResultItem
- `backend/app/schemas/common.py` — Currency class
- `backend/app/services/transaction_service.py` — compute_weighted_avg_cost, auto-calc call-sites
- `backend/app/services/fx.py` — convert_bulk() for FX rate lookup per data
- `backend/alembic/versions/001_initial.py` — transactions table

## Constraints
- Conversione FX impossibile → WACResult(wac=None), TX riceve null
- total_qty == 0 senza errori FX → Currency(amount="0"), NON None
- Vecchio formato (SafeDecimal puro) → 422, no backward compatibility
- Alla fine: `./dev.py db create-clean` + `./dev.py api sync` devono passare
- Aggiornare i test backend esistenti che rompono (breaking changes)

## Further Considerations

1. **`convert_bulk` vs singole query**: Usare `convert_bulk(session, conversions, raise_on_error=False)` da `fx.py` per batch-convertire tutte le TX in un colpo → evita N query separate. Raccogliere errori per `missing_pairs`.

2. **Impatto sulla promote endpoint legacy** (`/transfers/promote`): `TXTransferPromoteRequest.cost_basis_override` cambia tipo. L'endpoint a riga 311 usa `promote_transfer_pair()` (riga 720) che serializza il `cost_basis_override` come dict `format()` — deve diventare `{"code": ..., "amount": ...}`. Verificare la coerenza.

3. **`resolved_fields["cost_basis_override"]`** nel promote batch (riga 1326-1338): oggi è un `Decimal`, domani sarà un `dict {code, amount}` — il parsing dev'essere aggiornato per deserializzare come `Currency` e spacchettare in `tx.cost_basis_override` + `tx.cost_basis_currency`.

4. **`TXCreateItem.cost_basis_override` → DB mapping**: Nella creazione TX (riga 1225-1235), oggi viene passato direttamente `item.cost_basis_override` (un `Decimal`). Domani è un `Currency` → spacchettare in `cost_basis_override=cbo.amount` + `cost_basis_currency=cbo.code`.

5. **`TXUpdateItem.cost_basis_override` clearing**: Lo schema `TXUpdateItem` usa `None` come "non cambiare". Per _azzerare_ il cost_basis serve un sentinel (oggi non esiste — il valore `None` nel campo Optional significa "non toccare"). Considerare se serve un `0`-sentinel come per `asset_event_id`. Per ora: non cambiamo — il clear si fa solo lato server (auto-calc → null).

## Execution checklist

- [x] Step 1: DB model + Alembic
- [x] Step 2: Schema cost_basis_override → Currency
- [x] Step 3: WACConversionInfo + WACResult schemas
- [x] Step 4: compute_weighted_avg_cost rewrite
- [x] Step 5a: Promote call-site
- [x] Step 5b: Create link call-site
- [x] Step 5c: Create path unpacking
- [x] Step 5d: Update path unpacking
- [x] Step 5e: Promote endpoint legacy
- [x] Step 5f: resolved_fields handling
- [x] Step 6: recalc-wac endpoint
- [x] `./dev.py db create-clean`
- [x] `./dev.py api sync`
- [x] Fix broken tests (cost_basis "42.50" → {code, amount}) — **nessun test backend toccato direttamente**

## Deviations from plan

- **No `String` import needed in models.py**: Used `max_length=3` on Field (SQLModel auto-maps), consistent with existing `currency` field.
- **No backend tests broken**: Zero test files referenced `cost_basis_override` or `compute_weighted_avg_cost`. Frontend E2E tests (`tx-commit-all-types.spec.ts`) use old format but will be updated in SP-E after frontend changes.
- **`check_user_broker_access` doesn't exist**: Used existing `_check_broker_access_or_raise()` method instead in recalc-wac endpoint.
- **`row_data` uses mutable list[tuple]**: Had to use list indexing `row_data[row_idx] = (...)` for replacing converted costs. Tuples inside list replaced by re-assignment.

