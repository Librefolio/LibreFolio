# Plan D1 — Backend: Batch Pipeline + Promote-Suggest

**Date**: 2026-05-12
**Status**: ✅ DONE
**Priority**: P1 (feature completion)
**Estimated effort**: ~10h (~2 days)

**Parent**: [`plan-phase07-PlanD_SplitPromoteFullStack.prompt.md`](../plan-phase07-PlanD_SplitPromoteFullStack.prompt.md)
**Steps covered**: E1, E2, A1, A2, A3, A4, A5, B1, B2, B3

---

## 🎯 Obiettivo

Integrare split e promote nella pipeline unificata `execute_batch` (validate/commit), eliminare gli endpoint standalone `/split` e `/promote` (mai usati in produzione — nessuna backward compat necessaria), aggiungere l'endpoint bulk `POST /transactions/promote-suggest`, e coprire tutto con test backend.

---

## 📐 Design Decisions

### DD1 — Constraint check duck-typing (Opzione B)

Il metodo `_check_promote_constraints` attuale lavora con `Transaction` objects. Per `promote-suggest` serve validare constraints usando dati raw da `TXPromoteSuggestInput`. 

**Decisione**: creare un nuovo helper `_PromoteCandidate` (semplice dataclass/namedtuple con attributi `broker_id`, `currency`, `amount`, `quantity`, `asset_id`) e generalizzare `_check_promote_constraints` per accettare qualsiasi oggetto con quegli attributi (duck-typing). Questo permette di usarlo sia con `Transaction` (batch pipeline) sia con `_PromoteCandidate` (suggest).

### DD2 — Eliminazione endpoint `/split` e `/promote`

Gli endpoint `POST /transactions/split` e `POST /transactions/promote` non sono mai stati usati in produzione (solo predisposti). Verranno **eliminati completamente** dalla codebase — nessun thin wrapper, nessuna backward compat. Split e promote passano esclusivamente per `/validate` e `/commit` tramite i nuovi campi `splits[]` e `promotes[]` di `TXMixedBatch`.

### DD3 — Eliminazione schema orfani

Con la rimozione degli endpoint, anche i relativi schema (`TXSplitItem`, `TXSplitRequest`, `TXSplitResultItem`, `TXSplitResponse`, `TXPromoteItem`, `TXPromoteRequest`, `TXPromoteResultItem`, `TXPromoteResponse`) vanno eliminati. Idem per i metodi service `split_pairs()` e `promote_pairs()` — la logica viene assorbita in `execute_batch`.

### DD4 — `consumed_link_uuids` per evitare ri-processing in Step 6

Quando un promote consuma un `link_uuid_a` o `link_uuid_b` dal `link_uuid_map` (creates nello stesso batch), quegli UUID devono essere tracciati in un `consumed_link_uuids: Set[str]`. Lo Step 6 (link resolution) salta le entries in `consumed_link_uuids`. Questo evita che un link_uuid venga sia usato per un promote che per una normale pair resolution.

---

## Step E1 — ✅ Mock data: 4 TX standalone tagged `promote-test`

**File**: `backend/test_scripts/test_db/populate_mock_data.py`
**Posizione**: dopo riga ~1255 (sezione linked TX, dopo CASH TRANSFER pair)

Aggiungere 4 TX standalone (senza `related_transaction_id`) con tag `promote-test`:

```python
# --- Standalone transactions for promote-suggest E2E tests ---
# Tagged 'promote-test' so tests can locate them.

# CASH_TRANSFER promote candidate pair (same currency, diff broker, opposite amounts)
tx_prom_withdrawal = Transaction(
    broker_id=degiro.id, asset_id=None,
    type=TransactionType.WITHDRAWAL,
    date=today - timedelta(days=10),
    quantity=Decimal("0"), amount=Decimal("-500.00"), currency="EUR",
    description="[promote-test] Withdrawal for cash transfer test",
    tags="promote-test",
)
tx_prom_deposit = Transaction(
    broker_id=ib.id, asset_id=None,
    type=TransactionType.DEPOSIT,
    date=today - timedelta(days=10),
    quantity=Decimal("0"), amount=Decimal("500.00"), currency="EUR",
    description="[promote-test] Deposit for cash transfer test",
    tags="promote-test",
)

# TRANSFER promote candidate pair (same asset, diff broker, opposite qty)
tx_prom_adj_out = Transaction(
    broker_id=ib.id, asset_id=apple.id,
    type=TransactionType.ADJUSTMENT,
    date=today - timedelta(days=8),
    quantity=Decimal("-2"), amount=Decimal("0"), currency="USD",
    description="[promote-test] Adjustment out for transfer test",
    tags="promote-test",
)
tx_prom_adj_in = Transaction(
    broker_id=directa.id, asset_id=apple.id,
    type=TransactionType.ADJUSTMENT,
    date=today - timedelta(days=8),
    quantity=Decimal("2"), amount=Decimal("0"), currency="USD",
    description="[promote-test] Adjustment in for transfer test",
    tags="promote-test",
)

session.add_all([tx_prom_withdrawal, tx_prom_deposit, tx_prom_adj_out, tx_prom_adj_in])
session.commit()
print(f"  💡 promote-test standalone: W#{tx_prom_withdrawal.id}, D#{tx_prom_deposit.id}, Adj-#{tx_prom_adj_out.id}, Adj+#{tx_prom_adj_in.id}")
```

**Note**: standalone = no `related_transaction_id`, no `flush()` + link assignment. Tag `promote-test` per filtraggio nei test E2E.

---

## Step E2 — ✅ Refresh test DB

```bash
./dev.py db create-clean --test
```

---

## Step A1 — ✅ Schema: estendere `TXMixedBatch` + nuovi item

**File**: `backend/app/schemas/transactions.py`

### A1.1 — Nuovi batch item (inserire prima di `TXMixedBatch`, riga ~610)

```python
class TXSplitBatchItem(BaseModel):
    """Single split within a batch. Only for saved paired TXs."""
    model_config = ConfigDict(extra="forbid")

    id: int = Field(..., gt=0, description="ID of one half of the pair to split")


class TXPromoteBatchItem(BaseModel):
    """Single promote within a batch. Supports saved+saved, new+new, saved+new."""
    model_config = ConfigDict(extra="forbid")

    id_a: Optional[int] = Field(None, gt=0, description="Real ID for saved TX A")
    id_b: Optional[int] = Field(None, gt=0, description="Real ID for saved TX B")
    link_uuid_a: Optional[str] = Field(None, max_length=36, description="link_uuid to resolve TX A from creates in same batch")
    link_uuid_b: Optional[str] = Field(None, max_length=36, description="link_uuid to resolve TX B from creates in same batch")
    resolved_fields: Optional[Dict[str, Any]] = Field(None, description="Merged field values from PromoteMergeModal: description, tags, date, cost_basis_override")

    @model_validator(mode="after")
    def _validate_refs(self) -> "TXPromoteBatchItem":
        """At least one of id_a/link_uuid_a and id_b/link_uuid_b must be set."""
        if self.id_a is None and self.link_uuid_a is None:
            raise ValueError("Either id_a or link_uuid_a must be provided for TX A")
        if self.id_b is None and self.link_uuid_b is None:
            raise ValueError("Either id_b or link_uuid_b must be provided for TX B")
        if self.id_a is not None and self.link_uuid_a is not None:
            raise ValueError("Provide either id_a or link_uuid_a for TX A, not both")
        if self.id_b is not None and self.link_uuid_b is not None:
            raise ValueError("Provide either id_b or link_uuid_b for TX B, not both")
        return self
```

### A1.2 — Modificare `TXMixedBatch`

```python
class TXMixedBatch(BaseModel):
    """Unified batch body for /validate and /commit."""
    model_config = ConfigDict(extra="forbid")

    creates: List[dict] = Field(default_factory=list, max_length=500)
    updates: List[dict] = Field(default_factory=list, max_length=500)
    deletes: List[int] = Field(default_factory=list, max_length=500)
    splits: List[dict] = Field(default_factory=list, max_length=100)    # NEW
    promotes: List[dict] = Field(default_factory=list, max_length=100)  # NEW
```

### A1.3 — Aggiornare `TXBatchResultItem.operation`

```python
operation: Literal["create", "update", "delete", "split", "promote"]
```

### A1.4 — Aggiornare `TXValidationIssue.operation`

```python
operation: Literal["create", "update", "delete", "split", "promote"]
```

### A1.5 — Schema promote-suggest (inserire dopo promote/split batch items)

```python
class TXPromoteSuggestInput(BaseModel):
    """Single TX to find promote candidates for. id < 0 = fake (unsaved)."""
    model_config = ConfigDict(extra="forbid")

    id: int = Field(..., description="Real ID (>0) or fake ID (<0) for unsaved TX")
    type: TransactionType
    broker_id: int = Field(..., gt=0)
    date: date_type
    currency: Optional[str] = None
    asset_id: Optional[int] = None
    amount: Optional[SafeDecimal] = None
    quantity: Optional[SafeDecimal] = None


class TXPromoteSuggestCandidate(BaseModel):
    """A DB transaction that could be promoted with the input TX."""
    model_config = ConfigDict(extra="forbid")

    id: int = Field(..., gt=0)
    broker_id: int
    date: date_type
    type: str
    currency: Optional[str] = None
    asset_id: Optional[int] = None


class TXPromoteSuggestResponse(BaseModel):
    """Map of input id/fakeId → list of DB candidates."""
    model_config = ConfigDict(extra="forbid")

    results: Dict[int, List[TXPromoteSuggestCandidate]]
```

### A1.6 — Eliminare schema orfani (DD3)

Rimuovere completamente:
- `TXSplitItem`, `TXSplitRequest`, `TXSplitResultItem`, `TXSplitResponse`
- `TXPromoteItem`, `TXPromoteRequest`, `TXPromoteResultItem`, `TXPromoteResponse`

---

## Step A2 — ✅ Pipeline: Step 5b (splits) + Step 5c (promotes) in `execute_batch`

**File**: `backend/app/services/transaction_service.py`

### A2.1 — Nuovo helper `_PromoteCandidate` (top-level, vicino a `BalanceValidationError`)

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class _PromoteCandidate:
    """Lightweight duck-type-compatible object for _check_promote_constraints.
    Used by promote-suggest to validate constraints without a full Transaction."""
    broker_id: int
    asset_id: Optional[int]
    currency: Optional[str]
    amount: Decimal
    quantity: Decimal
```

### A2.2 — Estendere firma `execute_batch`

```python
async def execute_batch(
    self,
    creates_raw: List[dict],
    updates_raw: List[dict],
    deletes: List[int],
    splits_raw: List[dict] | None = None,     # NEW
    promotes_raw: List[dict] | None = None,    # NEW
    user_id: Optional[int] = None,
    commit: bool = False,
) -> TXBatchResponse:
```

Default `None` (non `[]`) per backward compat con chiamate esistenti (promote_transfer lo chiama senza splits/promotes).

### A2.3 — Step 1 esteso: lenient parse di splits e promotes

Dopo le righe 1001-1003 (parse creates/updates):

```python
parsed_splits, split_issues = _parse_lenient(splits_raw or [], TXSplitBatchItem, "split")
parsed_promotes, promote_issues = _parse_lenient(promotes_raw or [], TXPromoteBatchItem, "promote")
issues.extend(split_issues)
issues.extend(promote_issues)
```

### A2.4 — Step 2 esteso: lookup IDs per splits e promotes

Estendere `ids_to_lookup` (riga ~1011):

```python
# Include split IDs
for _, item in parsed_splits:
    ids_to_lookup.add(item.id)

# Include promote real IDs (>0)
for _, item in parsed_promotes:
    if item.id_a is not None:
        ids_to_lookup.add(item.id_a)
    if item.id_b is not None:
        ids_to_lookup.add(item.id_b)
```

Dopo il fetch di `existing_by_id`, serve anche fetchare i partner dei split (come fa `split_pairs()`):

```python
# Fetch split partners
split_partner_ids: set[int] = set()
for _, item in parsed_splits:
    tx = existing_by_id.get(item.id)
    if tx and tx.related_transaction_id and tx.related_transaction_id not in existing_by_id:
        split_partner_ids.add(tx.related_transaction_id)
if split_partner_ids:
    partners = await self.get_by_ids(list(split_partner_ids))
    for tx in partners:
        existing_by_id[tx.id] = tx
    touched_brokers |= {tx.broker_id for tx in partners}
```

### A2.5 — Step 5b: Splits (dopo Step 5 creates, prima di Step 6 link resolution)

```python
# 5b. Apply splits (only saved paired TXs)
for orig_idx, item in parsed_splits:
    tx = existing_by_id.get(item.id)
    if tx is None:
        issues.append(TXValidationIssue(
            operation="split", index=orig_idx, ref_id=item.id,
            error=f"Transaction {item.id} not found", code="txNotFound",
        ))
        continue
    if tx.related_transaction_id is None:
        issues.append(TXValidationIssue(
            operation="split", index=orig_idx, ref_id=item.id,
            error=f"Transaction {item.id} has no pair", code="noPairToSplit",
        ))
        continue
    partner = existing_by_id.get(tx.related_transaction_id)
    if partner is None:
        partner = await self.session.get(Transaction, tx.related_transaction_id)
    if partner is None:
        issues.append(TXValidationIssue(
            operation="split", index=orig_idx, ref_id=item.id,
            error=f"Partner {tx.related_transaction_id} not found", code="partnerNotFound",
        ))
        continue
    split_types = self.SPLIT_TYPE_MAP.get(tx.type)
    if split_types is None:
        issues.append(TXValidationIssue(
            operation="split", index=orig_idx, ref_id=item.id,
            error=f"Type {tx.type.value} cannot be split", code="typeCannotSplit",
        ))
        continue

    from_type, to_type = split_types

    # Determine from/to by value signs (same logic as old split_pairs)
    if tx.type == TransactionType.TRANSFER:
        if tx.quantity < Decimal("0"):
            tx_from, tx_to = tx, partner
        else:
            tx_from, tx_to = partner, tx
    else:
        if tx.amount < Decimal("0"):
            tx_from, tx_to = tx, partner
        else:
            tx_from, tx_to = partner, tx

    # Mutate types
    tx_from.type = from_type
    tx_to.type = to_type

    # Remove link
    tx_from.related_transaction_id = None
    tx_to.related_transaction_id = None

    # TRANSFER→ADJUSTMENT: keep asset+qty. CASH→WITHDRAWAL/DEPOSIT: clear asset
    if split_types != (TransactionType.ADJUSTMENT, TransactionType.ADJUSTMENT):
        tx_from.asset_id = None
        tx_to.asset_id = None

    tx_from.updated_at = utcnow()
    tx_to.updated_at = utcnow()

    # Track dates for balance validation
    for t in (tx_from, tx_to):
        prev = earliest_date_by_broker.get(t.broker_id)
        earliest_date_by_broker[t.broker_id] = t.date if prev is None else min(prev, t.date)

    results.append(TXBatchResultItem(operation="split", index=orig_idx, id=item.id, status="success"))
```

### A2.6 — Step 5c: Promotes

```python
# 5c. Apply promotes
consumed_link_uuids: Set[str] = set()

for orig_idx, item in parsed_promotes:
    # Resolve TX A
    tx_a = self._resolve_promote_ref(item.id_a, item.link_uuid_a, existing_by_id, link_uuid_map)
    tx_b = self._resolve_promote_ref(item.id_b, item.link_uuid_b, existing_by_id, link_uuid_map)

    if tx_a is None:
        issues.append(TXValidationIssue(
            operation="promote", index=orig_idx,
            error="Cannot resolve TX A reference", code="promoteRefNotFound",
        ))
        continue
    if tx_b is None:
        issues.append(TXValidationIssue(
            operation="promote", index=orig_idx,
            error="Cannot resolve TX B reference", code="promoteRefNotFound",
        ))
        continue
    if tx_a.related_transaction_id is not None:
        issues.append(TXValidationIssue(
            operation="promote", index=orig_idx, ref_id=getattr(tx_a, 'id', None),
            error=f"TX A ({tx_a.id}) already paired", code="alreadyPaired",
        ))
        continue
    if tx_b.related_transaction_id is not None:
        issues.append(TXValidationIssue(
            operation="promote", index=orig_idx, ref_id=getattr(tx_b, 'id', None),
            error=f"TX B ({tx_b.id}) already paired", code="alreadyPaired",
        ))
        continue

    # Find matching promote rule
    target_type = self._find_promote_rule_match(tx_a, tx_b)
    if target_type is None:
        issues.append(TXValidationIssue(
            operation="promote", index=orig_idx,
            error=f"No promote rule for {tx_a.type.value}+{tx_b.type.value}", code="noPromoteRule",
        ))
        continue

    # Mutate types + set bidirectional link
    tx_a.type = target_type
    tx_b.type = target_type
    tx_a.related_transaction_id = tx_b.id
    tx_b.related_transaction_id = tx_a.id

    # Apply resolved_fields
    if item.resolved_fields:
        for field_name in ("description", "cost_basis_override"):
            if field_name in item.resolved_fields:
                val = item.resolved_fields[field_name]
                setattr(tx_a, field_name, val)
                setattr(tx_b, field_name, val)
        if "tags" in item.resolved_fields:
            csv_tags = tags_to_csv(item.resolved_fields["tags"])
            tx_a.tags = csv_tags
            tx_b.tags = csv_tags
        if "date" in item.resolved_fields:
            from backend.app.utils.datetime_utils import parse_ISO_date
            resolved_date = parse_ISO_date(item.resolved_fields["date"])
            tx_a.date = resolved_date
            tx_b.date = resolved_date

    tx_a.updated_at = utcnow()
    tx_b.updated_at = utcnow()

    # Track dates for balance validation
    for t in (tx_a, tx_b):
        prev = earliest_date_by_broker.get(t.broker_id)
        earliest_date_by_broker[t.broker_id] = t.date if prev is None else min(prev, t.date)

    # Track consumed link_uuids so Step 6 doesn't re-process them
    if item.link_uuid_a:
        consumed_link_uuids.add(item.link_uuid_a)
    if item.link_uuid_b:
        consumed_link_uuids.add(item.link_uuid_b)

    results.append(TXBatchResultItem(operation="promote", index=orig_idx, id=tx_a.id, status="success"))
```

### A2.7 — Step 6: Skip consumed link_uuids

Modificare il loop di link resolution (riga ~1172):

```python
# 6. Link resolution
for link_uuid, pairs in link_uuid_map.items():
    if link_uuid in consumed_link_uuids:
        continue  # Already consumed by a promote in Step 5c
    # ...existing link resolution logic...
```

### A2.8 — Helper `_resolve_promote_ref`

Nuovo metodo statico sulla classe `TransactionService`:

```python
@staticmethod
def _resolve_promote_ref(
    id_val: Optional[int],
    link_uuid_val: Optional[str],
    existing_by_id: Dict[int, Transaction],
    link_uuid_map: Dict[str, List[Tuple[int, Transaction]]],
) -> Optional[Transaction]:
    """Resolve a promote reference to a Transaction.

    - id_val > 0 → lookup in existing_by_id
    - link_uuid_val → lookup first TX in link_uuid_map[link_uuid_val]
    """
    if id_val is not None and id_val > 0:
        return existing_by_id.get(id_val)
    if link_uuid_val:
        entries = link_uuid_map.get(link_uuid_val, [])
        if entries:
            return entries[0][1]  # (idx, Transaction) → Transaction
    return None
```

### A2.9 — Helper `_find_promote_rule_match`

Estrarre la logica di ricerca regola da `promote_pairs()` in un metodo riusabile:

```python
@staticmethod
def _find_promote_rule_match(tx_a: "Transaction", tx_b: "Transaction") -> Optional[TransactionType]:
    """Scan TX_TYPE_METADATA promote_from rules for a match between tx_a and tx_b."""
    for pair_type, meta in TX_TYPE_METADATA.items():
        if meta.promote_from is None:
            continue
        for rule in meta.promote_from:
            if (tx_a.type.value == rule.type_a and tx_b.type.value == rule.type_b) or \
               (tx_a.type.value == rule.type_b and tx_b.type.value == rule.type_a):
                if TransactionService._check_promote_constraints(tx_a, tx_b, rule.field_constraints):
                    return pair_type
    return None
```

### A2.10 — Nuovo metodo `promote_suggest_bulk`

```python
async def promote_suggest_bulk(
    self,
    inputs: List["TXPromoteSuggestInput"],
    tolerance_days: int,
    user_id: int,
) -> "TXPromoteSuggestResponse":
    """For each input TX, find DB transactions compatible for promote."""
    from backend.app.schemas.transactions import (
        TXPromoteSuggestCandidate,
        TXPromoteSuggestResponse,
    )

    accessible = await self._get_accessible_broker_ids(user_id)
    if not accessible:
        return TXPromoteSuggestResponse(results={})

    # Collect all positive IDs from inputs to exclude self-match
    input_positive_ids: set[int] = {inp.id for inp in inputs if inp.id > 0}

    results: Dict[int, List[TXPromoteSuggestCandidate]] = {}

    for inp in inputs:
        # Determine complementary types from promote_from rules
        complementary: list[tuple[TransactionType, list]] = []  # (target_type, constraints)
        for pair_type, meta in TX_TYPE_METADATA.items():
            if meta.promote_from is None:
                continue
            for rule in meta.promote_from:
                if inp.type.value == rule.type_a:
                    comp_type = TransactionType(rule.type_b)
                    complementary.append((comp_type, rule.field_constraints))
                elif inp.type.value == rule.type_b:
                    comp_type = TransactionType(rule.type_a)
                    complementary.append((comp_type, rule.field_constraints))

        if not complementary:
            results[inp.id] = []
            continue

        # Query DB: standalone TX with complementary type, date ±tolerance, accessible broker
        comp_types = list({ct for ct, _ in complementary})
        lo = inp.date - timedelta(days=tolerance_days)
        hi = inp.date + timedelta(days=tolerance_days)

        stmt = (
            select(Transaction)
            .where(Transaction.type.in_(comp_types))
            .where(Transaction.related_transaction_id.is_(None))
            .where(Transaction.date >= lo)
            .where(Transaction.date <= hi)
            .where(Transaction.broker_id.in_(accessible))
        )
        if input_positive_ids:
            stmt = stmt.where(Transaction.id.notin_(input_positive_ids))

        rows = (await self.session.execute(stmt)).scalars().all()

        # Build input as _PromoteCandidate for constraint checking
        inp_candidate = _PromoteCandidate(
            broker_id=inp.broker_id,
            asset_id=inp.asset_id,
            currency=inp.currency,
            amount=inp.amount or Decimal("0"),
            quantity=inp.quantity or Decimal("0"),
        )

        candidates: list[TXPromoteSuggestCandidate] = []
        for row in rows:
            # Check if any rule matches
            matched = False
            for comp_type, constraints in complementary:
                if row.type == comp_type:
                    if self._check_promote_constraints(inp_candidate, row, constraints):
                        matched = True
                        break
            if matched:
                candidates.append(TXPromoteSuggestCandidate(
                    id=row.id,
                    broker_id=row.broker_id,
                    date=row.date,
                    type=row.type.value,
                    currency=row.currency,
                    asset_id=row.asset_id,
                ))

        results[inp.id] = candidates

    return TXPromoteSuggestResponse(results=results)
```

### A2.11 — Eliminare metodi orfani (DD3)

Rimuovere completamente da `TransactionService`:
- `split_pairs()` (riga ~737-848)
- `promote_pairs()` (riga ~850-943)

La logica è ora interamente in Step 5b/5c di `execute_batch`.

---

## Step A3 — ✅ API: eliminare `/split` e `/promote`, aggiungere `/promote-suggest`

**File**: `backend/app/api/v1/transactions.py`

### A3.1 — Eliminare endpoint `/split` e `/promote`

Rimuovere completamente:
- `split_pairs()` (riga ~277-297) e relativo route decorator
- `promote_pairs()` (riga ~300-320) e relativo route decorator
- La sezione commento `# BULK SPLIT / PROMOTE (immediate, server-driven)` (riga ~272-275)

### A3.2 — Aggiornare imports

Rimuovere import orfani:
- `TXPromoteRequest`, `TXPromoteResponse`, `TXSplitRequest`, `TXSplitResponse`

Aggiungere nuovi import:
- `TXPromoteSuggestInput`, `TXPromoteSuggestResponse`

### A3.3 — Aggiornare `openapi_extra` su validate/commit

Nei decorator `openapi_extra` di `/validate` e `/commit` (riga ~66-80 e ~120-135), aggiungere `splits` e `promotes` allo schema:

```python
"splits": {"type": "array", "items": TXSplitBatchItem.model_json_schema()},
"promotes": {"type": "array", "items": TXPromoteBatchItem.model_json_schema()},
```

### A3.4 — Aggiornare chiamate a `execute_batch` in validate/commit

Passare `splits_raw` e `promotes_raw`:

```python
# In validate_transactions:
response = await service.execute_batch(
    creates_raw=batch.creates,
    updates_raw=batch.updates,
    deletes=batch.deletes,
    splits_raw=batch.splits,       # NEW
    promotes_raw=batch.promotes,   # NEW
    user_id=user_id,
    commit=False,
)

# In commit_transactions:
response = await service.execute_batch(
    creates_raw=batch.creates,
    updates_raw=batch.updates,
    deletes=batch.deletes,
    splits_raw=batch.splits,       # NEW
    promotes_raw=batch.promotes,   # NEW
    user_id=user_id,
    commit=True,
)
```

Aggiornare il log in commit:

```python
logger.info(
    "Commit batch: %d creates, %d updates, %d deletes, %d splits, %d promotes",
    len(batch.creates), len(batch.updates), len(batch.deletes),
    len(batch.splits), len(batch.promotes),
    user_id=user_id,
)
```

### A3.5 — Nuovo endpoint `POST /transactions/promote-suggest`

```python
@tx_router.post("/promote-suggest", response_model=TXPromoteSuggestResponse)
async def promote_suggest(
    inputs: List[TXPromoteSuggestInput],
    tolerance_days: int = Query(7, ge=1, le=30),
    session: AsyncSession = Depends(get_session_generator),
    current_user: User = Depends(get_current_user),
) -> TXPromoteSuggestResponse:
    """Find DB transactions compatible for promote with each input TX.

    Each input can have a real ID (>0) or a fake ID (<0, unsaved).
    Results are keyed by the input ID.
    """
    if len(inputs) > 500:
        raise HTTPException(status_code=422, detail="Max 500 inputs per call")

    service = TransactionService(session)
    return await service.promote_suggest_bulk(inputs, tolerance_days, user_id=current_user.id)
```

---

## Step A4 — ✅ Cleanup import references

**File**: `backend/app/services/transaction_service.py`

Aggiornare il blocco import schemas (riga ~33):
- Rimuovere: `TXPromoteItem`, `TXPromoteResultItem`, `TXPromoteResponse`, `TXSplitItem`, `TXSplitResultItem`, `TXSplitResponse`
- Aggiungere: `TXSplitBatchItem`, `TXPromoteBatchItem`

---

## Step A5 — ✅ API sync

```bash
./dev.py api sync
```

Rigenerare il client TypeScript dopo tutte le modifiche schemas+endpoints.

---

## Step B1 — ✅ Test: split nel batch

**Nuovo file**: `backend/test_scripts/test_api/test_transactions_batch_split_promote.py`

Struttura comune: fixture `test_server`, helper `create_test_user`, `create_broker`, `create_tx_pair`.

| # | Test | Scenario | Verifica |
|---|------|----------|----------|
| 1 | `test_commit_with_split_transfer` | Crea TRANSFER pair (2 broker, stessa asset, qty opposte) → commit con `splits:[{id: half_id}]` | GET entrambi: type=ADJUSTMENT, related_transaction_id=null |
| 2 | `test_commit_with_split_cash_transfer` | Crea CASH_TRANSFER pair → commit con split | WITHDRAWAL + DEPOSIT standalone, asset_id=null |
| 3 | `test_validate_split_not_found` | ID inesistente in splits | `committed: false`, issue con `code: "txNotFound"` |
| 4 | `test_split_standalone_fails` | TX standalone (no pair) in splits | issue con `code: "noPairToSplit"` |
| 5 | `test_split_in_mixed_batch` | creates[] + updates[] + splits[] nello stesso commit | Tutti committed, split applicato, creates linkati |

### Dettaglio test 1 (pattern da seguire per tutti):

```python
async def test_commit_with_split_transfer(self):
    """Split a TRANSFER pair via batch pipeline."""
    async with httpx.AsyncClient() as client:
        await create_test_user(client)
        broker_a_id = await create_broker(client, "Split Broker A")
        broker_b_id = await create_broker(client, "Split Broker B")
        asset_id = await get_or_create_asset(client)

        # Create TRANSFER pair via commit
        link_uuid = str(uuid4())
        resp = await client.post(f"{API_BASE}/transactions/commit", json={
            "creates": [
                {"broker_id": broker_a_id, "asset_id": asset_id, "type": "TRANSFER",
                 "date": "2026-01-15", "quantity": "-5", "link_uuid": link_uuid},
                {"broker_id": broker_b_id, "asset_id": asset_id, "type": "TRANSFER",
                 "date": "2026-01-15", "quantity": "5", "link_uuid": link_uuid},
            ],
        }, timeout=TIMEOUT)
        assert resp.status_code == 200
        data = resp.json()
        assert data["committed"] is True
        tx_ids = [r["id"] for r in data["results"] if r["operation"] == "create"]
        assert len(tx_ids) == 2

        # Split via commit
        resp2 = await client.post(f"{API_BASE}/transactions/commit", json={
            "splits": [{"id": tx_ids[0]}],
        }, timeout=TIMEOUT)
        assert resp2.status_code == 200
        data2 = resp2.json()
        assert data2["committed"] is True
        split_results = [r for r in data2["results"] if r["operation"] == "split"]
        assert len(split_results) == 1

        # Verify both TXs are now ADJUSTMENT standalone
        resp3 = await client.get(f"{API_BASE}/transactions", params={"ids": tx_ids}, timeout=TIMEOUT)
        txs = resp3.json()
        for tx in txs:
            assert tx["type"] == "ADJUSTMENT"
            assert tx["related_transaction_id"] is None
```

---

## Step B2 — ✅ Test: promote nel batch

Stesso file di B1.

| # | Test | Scenario | Verifica |
|---|------|----------|----------|
| 1 | `test_commit_promote_saved_saved` | 2 saved standalone WITHDRAWAL+DEPOSIT (broker diversi, stessa currency, amount opposti) → commit con `promotes:[{id_a, id_b}]` | GET entrambi: type=CASH_TRANSFER, bidirectional link |
| 2 | `test_commit_promote_new_new` | 2 creates (ADJUSTMENT+ADJUSTMENT stessa asset, broker diversi, qty opposte, con link_uuid) + `promotes:[{link_uuid_a, link_uuid_b}]` | TRANSFER pair atomico. Verifica link_uuid NON ri-processato in Step 6 (no issue `linkUuidPairCount`) |
| 3 | `test_commit_promote_saved_new` | 1 saved WITHDRAWAL + 1 create DEPOSIT (link_uuid_b) + `promotes:[{id_a: saved_id, link_uuid_b: new_uuid}]` | CASH_TRANSFER, bidirectional link |
| 4 | `test_validate_promote_incompatible` | BUY+SELL → no rule | issue `code: "noPromoteRule"` |
| 5 | `test_validate_promote_already_paired` | TX con related_transaction_id → promote | issue `code: "alreadyPaired"` |
| 6 | `test_promote_resolved_fields` | `resolved_fields: {description: "merged", tags: ["a","b"]}` | GET entrambi: stessi description e tags |
| 7 | `test_promote_constraint_fail` | Same broker per CASH_TRANSFER (viola `broker_id: different`) | issue `code: "noPromoteRule"` (no rule matches) |

### Dettaglio test 2 (new+new, il più complesso):

```python
async def test_commit_promote_new_new(self):
    """Promote two new creates via link_uuid in the same batch."""
    async with httpx.AsyncClient() as client:
        await create_test_user(client)
        broker_a_id = await create_broker(client, "Promote A")
        broker_b_id = await create_broker(client, "Promote B")
        asset_id = await get_or_create_asset(client)

        uuid_a = str(uuid4())
        uuid_b = str(uuid4())

        resp = await client.post(f"{API_BASE}/transactions/commit", json={
            "creates": [
                {"broker_id": broker_a_id, "asset_id": asset_id, "type": "ADJUSTMENT",
                 "date": "2026-02-10", "quantity": "-3", "link_uuid": uuid_a},
                {"broker_id": broker_b_id, "asset_id": asset_id, "type": "ADJUSTMENT",
                 "date": "2026-02-10", "quantity": "3", "link_uuid": uuid_b},
            ],
            "promotes": [{"link_uuid_a": uuid_a, "link_uuid_b": uuid_b}],
        }, timeout=TIMEOUT)
        assert resp.status_code == 200
        data = resp.json()
        assert data["committed"] is True

        # No issues (link_uuid not re-processed in Step 6)
        assert data["issues"] == []

        # Verify: both are TRANSFER with bidirectional link
        create_results = [r for r in data["results"] if r["operation"] == "create"]
        tx_ids = [r["id"] for r in create_results]

        resp2 = await client.get(f"{API_BASE}/transactions", params={"ids": tx_ids}, timeout=TIMEOUT)
        txs = resp2.json()
        assert all(tx["type"] == "TRANSFER" for tx in txs)
        assert txs[0]["related_transaction_id"] == txs[1]["id"]
        assert txs[1]["related_transaction_id"] == txs[0]["id"]
```

---

## Step B3 — ✅ Test: promote-suggest

Stesso file.

| # | Test | Scenario | Verifica |
|---|------|----------|----------|
| 1 | `test_suggest_finds_cash_transfer_candidate` | Input DEPOSIT EUR broker X, DB ha WITHDRAWAL EUR broker Y → candidate | `results[inp.id]` ha ≥1 candidate con `type: "WITHDRAWAL"` |
| 2 | `test_suggest_respects_tolerance` | tolerance_days=1, TX a 30gg di distanza | `results[inp.id]` vuoto |
| 3 | `test_suggest_excludes_paired` | TX con related_transaction_id nel DB | non in results |
| 4 | `test_suggest_excludes_self` | input `id=X` (>0), DB ha TX con id=X | X non in candidates |
| 5 | `test_suggest_multiple_inputs` | 3 items bulk | Dict con 3 chiavi, ciascuna con candidati appropriati |
| 6 | `test_suggest_fake_id` | `id=-1` (unsaved) | Results keyed by `-1`, candidates validi |

---

## 📊 Step Classification

| Step | Tipo | Stima | Dipendenze |
|------|------|-------|------------|
| E1 | 📝 Mock data | ~15min | — |
| E2 | 🎯 CLI | ~5min | E1 |
| A1 | 🎯 Schema | ~30min | — |
| A2 | 🗺️ Pipeline | ~3h | A1 |
| A3 | 🎯 API endpoint | ~1h | A1, A2 |
| A4 | 🎯 Cleanup imports | ~10min | A2, A3 |
| A5 | 🎯 CLI | ~5min | A1-A4 |
| B1 | 🧪 Test split | ~1h | A1-A5, E1-E2 |
| B2 | 🧪 Test promote | ~1.5h | A1-A5, E1-E2 |
| B3 | 🧪 Test suggest | ~1h | A1-A5, E1-E2 |

**Totale stimato**: ~9h

---

## 🔀 Ordine di esecuzione

```
E1 (mock data)
  ↓
E2 (create-clean --test)
  ↓
A1 (schema nuovi + cleanup orfani)
  ↓
A2 (pipeline execute_batch estesa + helpers + suggest_bulk + cleanup metodi)
  ↓
A3 (API: eliminare /split /promote, aggiungere /promote-suggest, aggiornare validate/commit)
  ↓
A4 (cleanup import)
  ↓
A5 (api sync)
  ↓
B1 (test split) ─┐
B2 (test promote) ├─ paralleli se file separati, altrimenti sequenziali
B3 (test suggest) ┘
```

---

## 🔗 Cross-links

- **Parent plan**: [`plan-phase07-PlanD_SplitPromoteFullStack.prompt.md`](../plan-phase07-PlanD_SplitPromoteFullStack.prompt.md)
- **Next sub-plan (D2)**: `plan-PlanD2_FrontendSplitPromoteUI.prompt.md` (⏳ planned)
- **devWiki**: `LibreFolio_devWiki/wiki/decisions/pendingop-tagged-union.md`

