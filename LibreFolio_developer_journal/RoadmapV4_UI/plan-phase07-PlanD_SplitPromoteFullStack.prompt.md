# Plan — Phase 07 · Part 4 · Round 6 · Plan D — Split/Promote Full Stack

**Date**: 2026-05-12
**Status**: 🔄 IN PROGRESS (D1 ✅, D2 ✅ + bugfix1-4 ✅, D2-round2 SP-A/B/C ✅, D2-round3 ⏳ SP-D, D3 merged in D2-bugfix3)
**Priority**: P1 (feature completion)
**Estimated effort**: ~5-6 days

**Parent**: [`plan-phase07-transaction-Part4_Round6_ContextMenuDeletePolish.prompt.md`](./phases/phase-07-subplan/Parte4/Round6/plan-phase07-transaction-Part4_Round6_ContextMenuDeletePolish.prompt.md)
**Predecessor**: Piano C3 ✅ (PendingOp refactor)

---

## 🎯 Obiettivo

Integrare split/promote nella pipeline batch unificata (validate/commit), aggiungere un endpoint bulk promote-suggest che accetta TX con ID reali o fake e ritorna candidati dal DB, implementare split come row action e promote come auto-suggest banner verde nella BulkModal + toolbar manuale se 2 righe selezionate, con PromoteMergeModal per risolvere campi divergenti.

---

## Stato attuale

### Backend (post-D1 ✅)
- `POST /transactions/split` — **ELIMINATO** (DD2 di D1: mai usato in produzione)
- `POST /transactions/promote` — **ELIMINATO** (DD2 di D1: mai usato in produzione)
- `POST /transactions/validate` — dry-run batch (creates + updates + deletes + **splits** + **promotes**)
- `POST /transactions/commit` — commit batch (creates + updates + deletes + **splits** + **promotes**)
- `POST /transactions/promote-suggest` — **NUOVO**: bulk candidate search con tolerance_days
- `TXMixedBatch`: esteso con `splits: List[dict]` e `promotes: List[dict]`
- `TXBatchOperation`: tipo centralizzato `Literal["create","update","delete","split","promote"]`
- `TXSplitBatchItem`: `{id}` — one half of a pair to split
- `TXPromoteBatchItem`: `{id_a?, id_b?, link_uuid_a?, link_uuid_b?, resolved_fields?}` — supports saved+saved, new+new, saved+new
- `TXPromoteSuggestInput/Candidate/Response`: promote-suggest I/O
- `_PromoteCandidate` dataclass: duck-typed constraint validation
- `_find_promote_rule_match()`, `_resolve_promote_ref()`: pipeline helpers
- `consumed_link_uuids`: prevents Step 6 from re-processing promotes' link_uuids
- `SPLIT_TYPE_MAP`: TRANSFER→(ADJUSTMENT,ADJUSTMENT), CASH_TRANSFER→(WITHDRAWAL,DEPOSIT), FX_CONVERSION→(WITHDRAWAL,DEPOSIT)
- `promote_from` rules in `TX_TYPE_METADATA`: ADJUSTMENT+ADJUSTMENT→TRANSFER, WITHDRAWAL+DEPOSIT(same currency, diff broker)→CASH_TRANSFER, WITHDRAWAL+DEPOSIT(diff currency, same broker)→FX_CONVERSION
- 18 backend tests: all passing (`./dev.py test api batch-split-promote`)

### Frontend (già implementato, pre-D2)
- Main Table promote: selection-based (2 rows) → `ConfirmModal` → **vecchio `POST /promote` — ORA ROTTO** → serve migrare a batch `{promotes: [...]}`
- `findPromoteMatch(typeA, typeB, t)` — client-side promote rule matching
- BulkModal: `WorkspaceIntent` API, `PendingOp` tagged union, txStore SSoT
- Split hint banner in BulkModal (passive, info-only)

### Cosa manca (D2-round2)
- ~~Split/promote NON sono nella pipeline batch~~ ✅ D1
- ~~Nessun promote-suggest endpoint~~ ✅ D1
- ~~Migrare Main Table promote da vecchio `/promote` a batch `{promotes: [...]}`~~ ✅ D2
- ~~Split come row action non esiste (né Main Table né BulkModal)~~ ✅ D2
- ~~Promote tra new rows (locale) non supportato~~ ✅ D2
- ~~Promote tra saved+new (mixed) non supportato~~ ✅ D2
- ~~Nessun PromoteMergeModal per campi divergenti~~ ✅ D2
- ~~Nessun auto-detect banner per coppie compatibili~~ ✅ D2+bugfix3
- ~~E2E tests split/promote~~ ✅ D2-bugfix3 (absorbed D3 scope)
- cost_basis con valuta+FX ⏳ D2-round2
- AssetEvent picker riusando DataEditor ⏳ D2-round2
- Paired TX store-first pattern ⏳ D2-round2

---

## Sezione A — Backend

### A1. Estendere `TXMixedBatch` con promotes e splits

**File**: `backend/app/schemas/transactions.py` (riga ~611)

Aggiungere a `TXMixedBatch`:
```python
class TXMixedBatch(BaseModel):
    """Unified batch body for /validate and /commit."""
    model_config = ConfigDict(extra="forbid")

    creates: List[dict] = Field(default_factory=list, max_length=500)
    updates: List[dict] = Field(default_factory=list, max_length=500)
    deletes: List[int] = Field(default_factory=list, max_length=500)
    promotes: List[dict] = Field(default_factory=list, max_length=100)  # NEW
    splits: List[dict] = Field(default_factory=list, max_length=100)    # NEW
```

Nuovi schema per promote batch item:
```python
class TXPromoteBatchItem(BaseModel):
    """Single promote within a batch. Supports saved+saved, new+new, saved+new."""
    model_config = ConfigDict(extra="forbid")

    id_a: Optional[int] = Field(None, gt=0, description="Real ID for saved TX A")
    id_b: Optional[int] = Field(None, gt=0, description="Real ID for saved TX B")
    link_uuid_a: Optional[str] = Field(None, description="link_uuid to resolve TX A from creates in same batch")
    link_uuid_b: Optional[str] = Field(None, description="link_uuid to resolve TX B from creates in same batch")
    resolved_fields: Optional[Dict[str, Any]] = Field(None, description="Merged field values: description, tags, date, cost_basis_override")
```

Logica risoluzione:
- `id_a > 0` → lookup in `existing_by_id`
- `id_a is None` + `link_uuid_a` → lookup in `link_uuid_map` (creates dello stesso batch)
- Almeno uno tra `id_a` e `link_uuid_a` deve essere non-null (validazione)

Split batch item (semplice):
```python
class TXSplitBatchItem(BaseModel):
    """Single split within a batch. Only for saved paired TXs."""
    model_config = ConfigDict(extra="forbid")

    id: int = Field(..., gt=0, description="ID of one half of the pair to split")
```

Aggiornare `TXBatchResultItem.operation` literal:
```python
operation: Literal["create", "update", "delete", "split", "promote"]
```

---

### A2. Estendere `execute_batch` pipeline

**File**: `backend/app/services/transaction_service.py` (riga ~981)

Inserire nella pipeline dopo Step 5 (creates) e prima di Step 6 (link resolution):

**Step 5b — Splits**:
```python
# 5b. Apply splits (only saved paired TXs)
parsed_splits, split_issues = _parse_lenient(splits_raw, TXSplitBatchItem, "split")
issues.extend(split_issues)

for orig_idx, item in parsed_splits:
    tx = existing_by_id.get(item.id)
    if tx is None:
        issues.append(TXValidationIssue(operation="split", index=orig_idx, ref_id=item.id, error=f"Transaction {item.id} not found", code="txNotFound"))
        continue
    if tx.related_transaction_id is None:
        issues.append(TXValidationIssue(operation="split", index=origIdx, ref_id=item.id, error=f"Transaction {item.id} has no pair", code="noPairToSplit"))
        continue
    partner = existing_by_id.get(tx.related_transaction_id) or await self.session.get(Transaction, tx.related_transaction_id)
    if partner is None:
        issues.append(TXValidationIssue(operation="split", index=origIdx, ref_id=item.id, error="Partner not found", code="partnerNotFound"))
        continue
    split_types = self.SPLIT_TYPE_MAP.get(tx.type)
    if split_types is None:
        issues.append(TXValidationIssue(operation="split", index=origIdx, ref_id=item.id, error=f"Type {tx.type.value} cannot be split", code="typeCannotSplit"))
        continue
    # Determine from/to and mutate (same logic as split_pairs)
    # ... apply mutation, remove links, update timestamps
    results.append(TXBatchResultItem(operation="split", index=origIdx, id=item.id, status="success"))
```

**Step 5c — Promotes**:
```python
# 5c. Apply promotes (saved+saved, new+new via link_uuid, saved+new mixed)
parsed_promotes, promote_issues = _parse_lenient(promotes_raw, TXPromoteBatchItem, "promote")
issues.extend(promote_issues)

for orig_idx, item in parsed_promotes:
    # Resolve TX A
    tx_a = _resolve_promote_ref(item.id_a, item.link_uuid_a, existing_by_id, link_uuid_map)
    tx_b = _resolve_promote_ref(item.id_b, item.link_uuid_b, existing_by_id, link_uuid_map)
    if tx_a is None or tx_b is None:
        issues.append(TXValidationIssue(operation="promote", index=orig_idx, error="Cannot resolve TX references", code="promoteRefNotFound"))
        continue
    if tx_a.related_transaction_id is not None or tx_b.related_transaction_id is not None:
        issues.append(TXValidationIssue(operation="promote", index=orig_idx, error="TX already paired", code="alreadyPaired"))
        continue
    # Find matching promote rule (same logic as promote_pairs)
    target_type = _find_promote_rule_match(tx_a, tx_b)
    if target_type is None:
        issues.append(TXValidationIssue(operation="promote", index=orig_idx, error=f"No rule for {tx_a.type.value}+{tx_b.type.value}", code="noPromoteRule"))
        continue
    # Mutate types, set bidirectional link
    tx_a.type = target_type
    tx_b.type = target_type
    tx_a.related_transaction_id = tx_b.id
    tx_b.related_transaction_id = tx_a.id
    # Apply resolved_fields to both
    if item.resolved_fields:
        for field in ("description", "tags", "date", "cost_basis_override"):
            if field in item.resolved_fields:
                val = item.resolved_fields[field]
                setattr(tx_a, field if field != "tags" else "_tags_raw", val)
                setattr(tx_b, field if field != "tags" else "_tags_raw", val)
    tx_a.updated_at = utcnow()
    tx_b.updated_at = utcnow()
    results.append(TXBatchResultItem(operation="promote", index=orig_idx, id=tx_a.id, status="success"))
```

---

### A3. ~~Refactor endpoint `/split` e `/promote` → thin wrappers~~ → ELIMINATI (D1 DD2)

> **Deviazione D1**: gli endpoint `/split` e `/promote` non sono mai stati usati in produzione. Invece di mantenerli come thin wrapper, sono stati **completamente eliminati**. Split e promote passano esclusivamente per `/validate` e `/commit` tramite `splits[]` e `promotes[]` di `TXMixedBatch`. Anche i relativi schema orfani sono stati rimossi (`TXSplitItem`, `TXSplitRequest`, `TXSplitResponse`, `TXPromoteItem`, `TXPromoteRequest`, `TXPromoteResponse`).
>
> **Impatto D2**: la Main Table promote attualmente usa il vecchio `POST /promote` che non esiste più. D2 deve migrare a `POST /transactions/commit` con `{promotes: [{id_a, id_b, resolved_fields}]}`.

**Files eliminati/modificati** (in D1):
- `backend/app/api/v1/transactions.py` — rimossi endpoint + relativi imports
- `backend/app/schemas/transactions.py` — rimossi 8 schema orfani
- `backend/app/services/transaction_service.py` — rimossi `split_pairs()` e `promote_pairs()`

---

### A4. Endpoint `POST /transactions/promote-suggest`

**File**: `backend/app/api/v1/transactions.py` (nuovo endpoint)
**File**: `backend/app/services/transaction_service.py` (nuovo metodo)
**File**: `backend/app/schemas/transactions.py` (nuovi schema)

**Schema request** — lista di TX raw (no nuovo tipo, riusa shape esistente):
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

class TXPromoteSuggestResponse(BaseModel):
    """Map of input id/fakeId → list of DB candidates."""
    model_config = ConfigDict(extra="forbid")

    results: Dict[int, List[TXPromoteSuggestCandidate]]
```

**Endpoint**:
```python
@tx_router.post("/promote-suggest", response_model=TXPromoteSuggestResponse)
async def promote_suggest(
    inputs: List[TXPromoteSuggestInput],
    tolerance_days: int = Query(7, ge=1, le=30),
    session: AsyncSession = Depends(get_session_generator),
    current_user: User = Depends(get_current_user),
) -> TXPromoteSuggestResponse:
    """Find DB transactions compatible for promote with each input TX."""
    service = TransactionService(session)
    return await service.promote_suggest_bulk(inputs, tolerance_days, user_id=current_user.id)
```

**Service logic** (`promote_suggest_bulk`):
- Per ogni input TX, determina i tipi complementari dalle `promote_from` rules
- Query DB: standalone transactions (no `related_transaction_id`) con tipo complementare, data ±tolerance, su broker accessibili dall'utente
- Escludi ID già nella lista input (evita self-match)
- Per ogni candidato: valida `field_constraints` (broker equal/different, currency, amount opposite, etc.)
- Ritorna solo candidati che soddisfano TUTTI i constraint

---

### A5. `./dev.py api sync`

Rigenerare il client TypeScript dopo tutte le modifiche schemas+endpoints.

---

### A6. ASCII art dei flussi

```
┌─────────────────────────────────────────────────────────────────────────┐
│              EXECUTE_BATCH PIPELINE (validate / commit)                  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  INPUT: TXMixedBatch { creates[], updates[], deletes[], splits[],       │
│                         promotes[] }                                     │                                                                         │
│  ┌─── Step 1: Lenient Parse ────────────────────────────────────────┐   │
│  │  creates_raw → TXCreateItem[]  (errors → issues[])               │   │
│  │  updates_raw → TXUpdateItem[]  (errors → issues[])               │   │
│  │  splits_raw  → TXSplitBatchItem[]   (errors → issues[])          │   │
│  │  promotes_raw → TXPromoteBatchItem[] (errors → issues[])         │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                           ↓                                             │
│  ┌─── Step 2: Access Check (EDITOR on all touched brokers) ─────────┐   │
│  │  Lookup existing IDs → touched_brokers set                        │   │
│  │  Any denied → issues[] + early return                             │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                           ↓                                             │
│  ┌─── Step 3: Deletes ─────────────────────────────────────────────┐    │
│  │  For each id: find TX, check pair integrity, session.delete()    │    │
│  └──────────────────────────────────────────────────────────────────┘   │
│                           ↓                                             │
│  ┌─── Step 4: Updates ─────────────────────────────────────────────┐    │
│  │  For each item: find TX, apply PATCHABLE_FIELDS, type swap,     │    │
│  │  pair desc/tags consistency check                                │    │
│  └──────────────────────────────────────────────────────────────────┘   │
│                           ↓                                             │
│  ┌─── Step 5: Creates ─────────────────────────────────────────────┐    │
│  │  For each item: build Transaction, flush → get ID               │    │
│  │  Collect link_uuid_map: {uuid → [(idx, Transaction)]}           │    │
│  └──────────────────────────────────────────────────────────────────┘   │
│                           ↓                                             │
│  ┌─── Step 5b: Splits ─────────────────────────────────────────────┐   │
│  │  For each {id}: find TX + partner via related_transaction_id     │   │
│  │  Apply SPLIT_TYPE_MAP → mutate types, remove link                │   │
│  │  Clear asset_id for CASH types                                   │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                           ↓                                             │
│  ┌─── Step 5c: Promotes ───────────────────────────────────────────┐   │
│  │  For each {id_a, id_b, link_uuid_a, link_uuid_b, resolved}:     │   │
│  │    Resolve IDs: real → existing_by_id, uuid → link_uuid_map      │   │
│  │    Match promote_from rules in TX_TYPE_METADATA                  │   │
│  │    Validate field_constraints (broker, currency, qty, asset)     │   │
│  │    Mutate types → target paired type                             │   │
│  │    Set related_transaction_id bidirectional                       │   │
│  │    Apply resolved_fields (desc, tags, date, cost_basis)          │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                           ↓                                             │
│  ┌─── Step 6: Link Resolution (existing creates with link_uuid) ───┐   │
│  │  Pairs from link_uuid_map not consumed by promotes               │   │
│  │  Validate pair constraints, set related_transaction_id           │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                           ↓                                             │
│  ┌─── Step 7: Balance Walk ────────────────────────────────────────┐   │
│  │  flush() → per-broker balance validation from earliest_date     │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                           ↓                                             │
│  ┌─── Step 8: Decision ───────────────────────────────────────────┐    │
│  │  issues? → {committed: false, issues}                           │    │
│  │  !commit? → {committed: false, results} (dry-run)               │    │
│  │  commit → {committed: true, results} (caller does session.commit)│   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘


┌─────────────────────────────────────────────────────────────────────────┐
│              PROMOTE-SUGGEST FLOW                                        │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  INPUT: List[{id: int (real or fake), type, broker_id, date,            │
│               currency?, asset_id?, amount?, quantity?}]                 │
│                                                                         │
│  ┌─── Per-item processing ─────────────────────────────────────────┐   │
│  │                                                                  │   │
│  │  1. Determine promote_from rules where this type is type_a/type_b│   │
│  │     → complementary_types = [DEPOSIT, ADJUSTMENT, ...]           │   │
│  │                                                                  │   │
│  │  2. Query DB: SELECT * FROM transaction WHERE                    │   │
│  │       type IN complementary_types                                │   │
│  │       AND related_transaction_id IS NULL                         │   │
│  │       AND date BETWEEN (input.date - tolerance, + tolerance)     │   │
│  │       AND broker_id IN (user accessible brokers)                 │   │
│  │       AND id NOT IN (input list IDs > 0)  ← avoid self-match    │   │
│  │                                                                  │   │
│  │  3. For each candidate: validate field_constraints vs input TX   │   │
│  │       broker_id different/equal? ✓                               │   │
│  │       currency equal/different? ✓                                │   │
│  │       amount opposite? ✓                                         │   │
│  │       asset_id equal? ✓                                          │   │
│  │                                                                  │   │
│  │  4. Filter → keep only fully-matching candidates                 │   │
│  │                                                                  │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                           ↓                                             │
│  OUTPUT: { results: {[id_or_fakeId]: [{id, broker_id, date, type}]} }   │
│                                                                         │
│  Frontend uses broker_id → broker name from store                       │
│  Frontend sorts by abs(date - input.date) for proximity                 │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Sezione B — Test Backend

### B1. Test split nel batch

**File**: `backend/test_scripts/test_api/test_transactions_api.py`

| Test | Scenario | Expected |
|------|----------|----------|
| `test_commit_with_split_transfer` | Create TRANSFER pair, commit con `splits:[{id}]` | 2 ADJUSTMENT standalone, link removed |
| `test_commit_with_split_cash_transfer` | Paired WITHDRAWAL/DEPOSIT → split | 2 standalone, types preserved |
| `test_validate_split_unsaved` | ID inesistente nel splits | issue `txNotFound` |
| `test_split_standalone_fails` | TX senza partner | issue `noPairToSplit` |
| `test_split_in_mixed_batch` | Creates + updates + split nello stesso commit | Tutto atomico |

### B2. Test promote nel batch

| Test | Scenario | Expected |
|------|----------|----------|
| `test_commit_promote_saved_saved` | 2 saved WITHDRAWAL+DEPOSIT → promote | CASH_TRANSFER pair |
| `test_commit_promote_new_new` | 2 creates (ADJUSTMENT+ADJUSTMENT con link_uuid_a/b) + promote | TRANSFER pair atomico |
| `test_commit_promote_saved_new` | 1 saved WITHDRAWAL + 1 create DEPOSIT(link_uuid_b) + promote | CASH_TRANSFER |
| `test_validate_promote_incompatible` | BUY+SELL → no rule | issue `noPromoteRule` |
| `test_validate_promote_constraint_fail` | Same broker per CASH_TRANSFER | issue `constraintFailed` |
| `test_promote_resolved_fields` | resolved_fields.description/tags | Applied to both sides |
| `test_promote_already_paired` | TX con related_transaction_id | issue `alreadyPaired` |

### B3. Test promote-suggest

| Test | Scenario | Expected |
|------|----------|----------|
| `test_suggest_finds_cash_transfer` | WITHDRAWAL nel DB, query con DEPOSIT | candidate {id, broker_id, date, type} |
| `test_suggest_respects_tolerance` | ±30 days | empty results |
| `test_suggest_excludes_paired` | TX già paired | not in results |
| `test_suggest_excludes_self` | Same ID in input list | not in results |
| `test_suggest_multiple_inputs` | Bulk 3 items | per-id results map |
| `test_suggest_fake_id_negative` | id=-1 (unsaved) | Results keyed by -1 |

### B4. Mock data

Vedi Sezione E.

---

## Sezione C — Frontend: sviluppi

### C1. Main Table — Split row action

**Files**: `frontend/src/lib/components/transactions/TransactionsTable.svelte`, `frontend/src/routes/(app)/transactions/+page.svelte`

**TransactionsTable.svelte** — aggiungere in `rowActions` (riga ~828):
```ts
{
    id: 'split',
    icon: Unlink,  // from lucide-svelte
    label: () => $t('transactions.actions.split') || 'Split pair',
    variant: 'warning',
    onClick: (d) => onSplitRow?.(d.tx),
    visible: (d) => d.tx.related_transaction_id != null && rowAccessLevel(d) === 'full',
},
```

Nuova prop in Props: `onSplitRow?: (row: TXReadItem) => void;`

**+page.svelte** — handler:
```ts
async function handleSplitRow(row: TXReadItem) {
    splitConfirmTx = row;
    splitConfirmOpen = true;
}
async function confirmSplit() {
    const resp = await zodiosApi.commit({splits: [{id: splitConfirmTx.id}]});
    if (resp.committed) {
        // Update txStore in-place with response data (Option B)
        txStoreInvalidate();
        await reload({soft: true});
        splitConfirmOpen = false;
    }
}
```

`ConfirmModal` con riepilogo: tipo coppia, broker Da→A, importo.

---

### C2. Main Table — Promote con MergeModal

**File**: `frontend/src/routes/(app)/transactions/+page.svelte`

Evolvere `confirmPromote()` (riga ~542):
- Se campi divergono (description, tags, date, cost_basis) → apre `PromoteMergeModal` (C5)
- Se campi identici → `ConfirmModal` diretto (UX attuale preservata)
- Commit usa batch: `{promotes: [{id_a, id_b, resolved_fields}]}`

---

### C3. BulkModal — Split row action

**File**: `frontend/src/lib/components/transactions/TransactionBulkModal.svelte`

Azione riga `✂ Split`:
- **Saved paired** (`op === 'edit'`, `partnerId != null`): accumula in `pendingSplits: TXSplitBatchItem[]`. Al commit → inserisce in `batch.splits`. UI: la paired op viene visual-splittata in 2 ops standalone (types mutati localmente per preview, status CSS `row-split-preview`).
- **New paired** (`op === 'create'`, `link_uuid` condiviso): trasformazione locale — rimuovi `link_uuid` da entrambe, muta types secondo client-side SPLIT_TYPE_MAP, separa in 2 ops indipendenti. Nessuna API call, nessun `pendingSplits` entry.

---

### C4. BulkModal — Promote selection toolbar + commit

**File**: `frontend/src/lib/components/transactions/TransactionBulkModal.svelte`

Toolbar visibile quando 2 righe selezionate, senza `partnerId`, e `findPromoteMatch()` valido:

| Caso | Azione | Nel commit batch |
|------|--------|-----------------|
| **2 saved** | PromoteMergeModal → ok | `promotes: [{id_a, id_b, resolved_fields}]` |
| **2 new** | Trasformazione locale | Nessun promote nel batch. Assegna `link_uuid` condiviso, muta types. Al commit vanno come 2 creates paired. |
| **1 saved + 1 new** | PromoteMergeModal → ok | `promotes: [{id_a: saved_id, link_uuid_b: new_uuid, resolved_fields}]` |

---

### C5. PromoteMergeModal

**New file**: `frontend/src/lib/components/transactions/PromoteMergeModal.svelte`

Props:
```ts
interface Props {
    open: boolean;
    txA: {label: string; description: string; tags: string[]; date: string; cost_basis_override: string};
    txB: {label: string; description: string; tags: string[]; date: string; cost_basis_override: string};
    targetTypeLabel: string;
    onConfirm: (resolved: {description?: string; tags?: string[]; date?: string; cost_basis_override?: string}) => void;
    onCancel: () => void;
}
```

Layout — per ogni campo divergente (nascondere se identici):
```
┌───────────────────────────────────────────────────────────────────────────┐
│  🔗 Promuovi a {targetTypeLabel}                                      [X] │
│                                                                           │
│  Campi divergenti da risolvere:                                           │
│                                                                           │
│  ┌─────────── Descrizione ────────────────────────────────────────────┐  │
│  │  Riga 2 (readonly)  │  [◀] [⟷] [▸]  │  Riga 5 (readonly)        │  │
│  │  "Transfer AAPL"    │  Risultato:     │  "Move shares"            │  │
│  │                      │  [___________]  │                           │  │
│  └──────────────────────────────────────────────────────────────────────┘│
│                                                                           │
│  ┌─────────── Tags ──────────────────────────────────────────────────┐   │
│  │  [rebalance]         │  [◀] [⟷] [▸]  │  [core] [monthly]         │  │
│  │                      │  Risultato:     │                           │  │
│  │                      │  [___________]  │                           │  │
│  └──────────────────────────────────────────────────────────────────────┘│
│                                                                           │
│                        [Annulla]  [🔗 Conferma]                           │
└───────────────────────────────────────────────────────────────────────────┘
```

Pulsanti auto-populate:
- `◀` → copia valore sinistra nel centro
- `⟷ merge` → concatenazione (`"valA | valB"` per desc, union per tags)
- `▸` → copia valore destra nel centro

Pre-populate centro: `merge` di default.
Tags: merge = union set deduplicated, `◀`/`▸` = solo quelli di un lato.
Date: se diverse mostra date picker per il centro.

---

### C6. Promote Suggest — green banner auto-detect

**File**: `frontend/src/lib/components/transactions/TransactionBulkModal.svelte`

Due fonti di suggerimenti:

**a) DB candidates** (per ops `edit` standalone):
- `$effect` reattivo: quando `ops` cambia e contiene ≥1 edit standalone, debounce 500ms, chiama `POST /transactions/promote-suggest` con le ops standalone.
- Response → `suggestFromDB: Map<number, TXPromoteSuggestCandidate[]>`

**b) Local candidates** (per ops `new` standalone, match tra loro):
- `$derived` puro: per ogni new op standalone, itera le altre new ops standalone, chiama `findPromoteMatch()` localmente e controlla constraint (broker diverso/uguale, currency, ecc.) usando i campi del draft.
- Risultato → lista di `{opTempIdA, opTempIdB, targetTypeLabel}`

**UI — Banner verde** (simile al validate success banner):
- Posizione: sopra la grid, sotto la toolbar.
- Stile: `bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800`
- Contenuto: lista di suggerimenti (max 5):
  ```
  💡 Riga 2 e Riga 5 sono compatibili → promuovi a CASH_TRANSFER [🔗]
  💡 Riga 1 e Riga 3 sono compatibili → promuovi a TRANSFER [🔗]
  ... e altri 2 suggerimenti
  ```
- Click su "Riga N" → `scrollIntoView({block:'nearest'}) + pulse` (classe `tx-row-highlight`)
- Click su `[🔗]` → auto-seleziona le 2 righe + apre PromoteMergeModal
- Banner scompare quando non ci sono più suggerimenti (reattivo).
- `data-testid="promote-suggest-banner"`, `data-testid="promote-suggest-item-{idx}"`

---

### C7. i18n keys (EN/IT/FR/ES)

```json
{
  "transactions.actions.split": "Split pair" / "Scollega coppia" / "Séparer la paire" / "Separar par",
  "transactions.split.confirmTitle": "Unlink this pair?" / "Scollegare questa coppia?" / ...,
  "transactions.split.confirmMessage": "The 2 transactions will become independent rows with type {fromType} and {toType}." / ...,
  "transactions.split.success": "Pair unlinked successfully" / "Coppia scollegata" / ...,

  "transactions.promote.mergeTitle": "Promote to {type}" / "Promuovi a {type}" / ...,
  "transactions.promote.mergeConfirm": "Confirm promotion" / "Conferma promozione" / ...,
  "transactions.promote.fieldDescription": "Description" / "Descrizione" / ...,
  "transactions.promote.fieldTags": "Tags" / "Tag" / ...,
  "transactions.promote.fieldDate": "Date" / "Data" / ...,
  "transactions.promote.fieldCostBasis": "Cost basis" / "Costo base" / ...,
  "transactions.promote.useLeft": "Use left" / "Usa sinistra" / ...,
  "transactions.promote.useMerge": "Merge" / "Unisci" / ...,
  "transactions.promote.useRight": "Use right" / "Usa destra" / ...,

  "transactions.promoteSuggest.banner": "Row {a} and Row {b} are compatible — promote to {type}" / "Riga {a} e Riga {b} sono compatibili — promuovi a {type}" / ...,
  "transactions.promoteSuggest.bannerMore": "and {n} more..." / "e altri {n}..." / ...,
  "transactions.promoteSuggest.dbMatch": "Match found in DB: {type} on {broker} ({date})" / "Match nel DB: {type} su {broker} ({date})" / ...
}
```

---

## Sezione D — Test Frontend (E2E)

### D1. `tx-split-promote.spec.ts`

**New file**: `frontend/e2e/transactions/tx-split-promote.spec.ts`

| # | Scenario | Verifica |
|---|----------|----------|
| 1 | Split TRANSFER dalla Main Table | row action `[data-action-id="split"]` → ConfirmModal → 2 ADJUSTMENT in tabella |
| 2 | Split da BulkModal (saved paired) | row action → preview split → commit → 2 standalone |
| 3 | Split locale (new paired nel batch) | no network call, 2 ops separate |
| 4 | Promote 2 saved dalla Main Table | selection toolbar → MergeModal (se diverge) → CASH_TRANSFER |
| 5 | Promote 2 new nel batch (locale) | link_uuid assegnato, types mutati, no network |
| 6 | Promote suggest banner appare | mock data `promote-test` → banner verde visibile |
| 7 | Promote suggest → click 🔗 → MergeModal | Full flow da banner a conferma |
| 8 | Guard: split nascosto su standalone | button non presente |
| 9 | Guard: promote nascosto su rows paired | toolbar button non visibile |
| 10 | Guard: split new locale non chiama API | intercept network → 0 calls to /split |

### D2. Registrazione test runner

**File**: `scripts/test_runner/_frontend_transaction.py`

```python
def front_tx_split_promote(headed=False, ui=False, debug=False):
    """Run tx-split-promote E2E tests."""
    _run_playwright("transactions/tx-split-promote.spec.ts", headed=headed, ui=ui, debug=debug)
```

Aggiungere a `front_transaction_all()` e `populate_registry()`.

---

## Sezione E — DB (mock data)

### E1. Mock data per test promote-suggest

**File**: `backend/test_scripts/test_db/populate_mock_data.py` (dopo riga ~1129)

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

### E2. Refresh test DB

```bash
./dev.py db create-clean --test
```

---

## Sezione F — Ordine di esecuzione

```
Phase 1: Fondamenta
  E1 → E2 (mock data → recreate test DB)
  A1 (schema TXMixedBatch esteso)
  A2 (execute_batch pipeline + step 5b/5c)
  A3 (refactor /split e /promote → wrappers)
  A4 (promote-suggest endpoint)
  A5 (api sync)

Phase 2: Verifica backend
  B1 (test split nel batch)
  B2 (test promote nel batch)
  B3 (test promote-suggest)

Phase 3: Frontend core
  C5 (PromoteMergeModal — componente base)
  C3 (BulkModal split row action)
  C4 (BulkModal promote toolbar)
  C1 (Main Table split row action)
  C2 (Main Table promote → MergeModal)
  C6 (Promote suggest banner)
  C7 (i18n)

Phase 4: E2E
  D1 (tx-split-promote.spec.ts)
  D2 (registrazione runner)
```

---

## 🔗 Cross-links

- **Parent plan**: [`plan-phase07-transaction-Part4_Round6_ContextMenuDeletePolish.prompt.md`](./phases/phase-07-subplan/Parte4/Round6/plan-phase07-transaction-Part4_Round6_ContextMenuDeletePolish.prompt.md)
- **Piano C3 (predecessor)**: [`plan-phase07-transaction-Part4_Round6_PlanC3_PendingOpRefactor.prompt.md`](./phases/phase-07-subplan/Parte4/Round6/plan-phase07-transaction-Part4_Round6_PlanC3_PendingOpRefactor.prompt.md)
- **devWiki decision**: `LibreFolio_devWiki/wiki/decisions/pendingop-tagged-union.md`
- **Feature page**: `LibreFolio_devWiki/wiki/features/F-048.md`

---

## 📊 Step Classification

| Step | Tipo | Stima | Dipendenze |
|------|------|-------|------------|
| A1 | 🎯 Schema | ~30min | — |
| A2 | 🗺️ Pipeline | ~3h | A1 |
| A3 | 🎯 Refactor | ~45min | A2 |
| A4 | 🗺️ Endpoint | ~2h | A1 |
| A5 | 🎯 CLI | ~5min | A1-A4 |
| B1-B3 | 🧪 Test | ~2h | A1-A4 |
| C5 | 🗺️ Component | ~2h | — |
| C3 | 🗺️ BulkModal | ~2h | C5, A5 |
| C4 | 🗺️ BulkModal | ~2h | C5, A5 |
| C1 | 🎯 Main Table | ~1h | A5 |
| C2 | 🎯 Main Table | ~1h | C5, A5 |
| C6 | 🗺️ Suggest | ~3h | A4, A5, C5 |
| C7 | 🎯 i18n | ~30min | — |
| D1-D2 | 🧪 E2E | ~3h | C1-C6 |
| E1-E2 | 📝 Data | ~15min | — |

**Totale stimato**: ~23h (~5-6 giorni)

---

## 📦 Sotto-piani di dettaglio

| Sotto-piano | Steps inclusi | Focus | Stima | File | Status |
|------------|---------------|-------|-------|------|--------|
| **D1** — Backend: Batch Pipeline + Suggest | E1, E2, A1, A2, A3, A4, A5, B1, B2, B3 | Schema estesi, pipeline execute_batch con split/promote, eliminazione endpoint /split e /promote (mai usati), endpoint promote-suggest, mock data, tutti i test backend | ~9h | [`PlanD1_BackendBatchSuggest`](./phases/phase-07-subplan/Parte4/Round6/PlanD-D1D2/plan-PlanD1_BackendBatchSuggest.prompt.md) | ✅ |
| **D2** — Frontend: Split/Promote UI + Suggest Banner | C5, C3, C4, C1, C2, C6, C7 | PromoteMergeModal, BulkModal split/promote, Main Table split/promote, suggest banner verde, i18n | ~12h | [`PlanD2_FrontendSplitPromoteUI`](./phases/phase-07-subplan/Parte4/Round6/PlanD-D1D2/plan-PlanD2_FrontendSplitPromoteUI.prompt.md) | ✅ |
| **D2-bugfix1** — Split/Promote Polish | Post-D2 | UX polish, edge cases, test fixes | — | [`PlanD2_bugfix_1`](./phases/phase-07-subplan/Parte4/Round6/PlanD-D1D2/Bugfix/plan-bugfix1_SplitPromotePolish.prompt.md) | ✅ |
| **D2-bugfix2** — Payload + Split Preview UX | Post-bugfix1 | Commit payload alignments, split preview rendering | — | [`PlanD2_bugfix_2`](./phases/phase-07-subplan/Parte4/Round6/PlanD-D1D2/Bugfix/plan-bugfix2_PayloadSplitPreviewUX.prompt.md) | ✅ |
| **D2-bugfix3** — UX Modal + Payload + Suggest + E2E | Post-bugfix2 | PromoteMergeModal polish, payload fixes, suggest banner UX, E2E tests (absorbed D3 scope) | — | [`PlanD2_bugfix_3`](./phases/phase-07-subplan/Parte4/Round6/PlanD-D1D2/Bugfix/plan-bugfix3_UXModalPayloadSuggestE2E.prompt.md) | ✅ |
| **D2-bugfix4** — Split Suggest + PMC Override UX | Post-bugfix3 | Split suggest logic, PromoteMergeCandidate override, UX edge cases | — | [`PlanD2_bugfix_4`](./phases/phase-07-subplan/Parte4/Round6/PlanD-D1D2/Bugfix/plan-bugfix4_SplitSuggestPmcOverrideUx.prompt.md) | ✅ |
| **D2-round2** — Walktest Feedback Round | Post-bugfix4 | cost_basis con valuta+FX, AssetEvent picker, paired TX store-first, 18 step in 5 sotto-piani | — | [`PlanD2_round2`](./phases/phase-07-subplan/Parte4/Round6/PlanD-R2/plan-R2-WalktestFeedbackRound.prompt.md) | 🔄 SP-A/B/C ✅, SP-D → R3 |
| **D2-round3** — SP-D: FormModal + Picker + FX | Post-round2 | Store-first refactor, AssetEventPickerModal, WAC FX staleness feedback | ~12h | [`plan-R3-SP-D`](./plan-R3-SP-D-FormModalEventPickerWacFx.prompt.md) | ⏳ NEXT |
| ~~**D3** — E2E Tests~~ | ~~D1, D2~~ | ~~tx-split-promote.spec.ts~~ | ~~3h~~ | — | ⛔ merged in D2-bugfix3 |

### Ordine di esecuzione

```
D1 (backend + test backend + mock data) ✅
  ↓
D2 (frontend — dipende da api sync di D1) ✅
  ↓
D2-bugfix1 (polish) ✅
  ↓
D2-bugfix2 (payload + split preview) ✅
  ↓
D2-bugfix3 (UX modal + suggest + E2E — absorbed D3 scope) ✅
  ↓
D2-bugfix4 (split suggest + PMC override) ✅
  ↓
D2-round2 (walktest feedback — SP-A/B/C ✅, SP-D/E pending) ✅ (core done)
  ↓
D2-round3 (SP-D: FormModal store-first + EventPicker + FX feedback) ⏳ NEXT
  ↓
SP-E (E2E tests for round2+round3) — after R3
```

---

## 🤖 Prompt per l'agente — creazione sotto-piani

### Prompt D1 — Backend: Batch Pipeline + Suggest

```
Leggiti il piano #file:plan-phase07-transaction-Part4_Round6_PlanD_SplitPromoteFullStack.prompt.md e crea il sotto-piano di dettaglio D1 (Backend: Batch Pipeline + Suggest).

Il piano D1 copre gli step: E1, E2, A1, A2, A3, A4, A5, B1, B2, B3.

In sintesi devi pianificare:
1. Mock data in populate_mock_data.py (E1, E2) — 4 TX standalone tagged 'promote-test'
2. Estendere TXMixedBatch con promotes[] e splits[] (A1) — nuovi schema TXPromoteBatchItem, TXSplitBatchItem
3. Estendere execute_batch pipeline (A2) — aggiungere step 5b (splits) e 5c (promotes) dopo creates e prima di link resolution. Attenzione ai casi: saved+saved, new+new (via link_uuid), saved+new (mixed). Attenzione all'interazione con step 6 (link resolution): i link_uuid consumati da promotes NON devono essere ri-processati in step 6.
4. Refactor /split e /promote come thin wrappers su execute_batch (A3) — backward compat
5. Nuovo endpoint POST /transactions/promote-suggest (A4) — bulk, accetta TX con ID reali o fake (<0), ritorna candidati DB
6. api sync (A5)
7. Tutti i test backend (B1, B2, B3) — split nel batch, promote nel batch (3 varianti: saved+saved, new+new, saved+new), promote-suggest

Il file va salvato come: plan-phase07-transaction-Part4_Round6_PlanD1_BackendBatchSuggest.prompt.md
```

### Prompt D2 — Frontend: Split/Promote UI + Suggest Banner

```
Leggiti il piano padre #file:plan-phase07-transaction-Part4_Round6_PlanD_SplitPromoteFullStack.prompt.md e il sotto-piano D1 già completato #file:plan-phase07-transaction-Part4_Round6_PlanD1_BackendBatchSuggest.prompt.md.

Poi leggiti il contesto dell'architettura frontend consultando i piani precedenti nella cartella #file:RoadmapV4_UI — in particolare i sotto-piani e bugfix di Round 6 (PlanA, PlanB, PlanB1, PlanB23, PlanC, PlanC2, PlanC2Round2, PlanC3) per avere pieno contesto di:
- Come funziona il PendingOp tagged union nel BulkModal
- Come funziona il commit() / collapsePairedOps() / deriveStatus()
- Come funzionano le row actions nella DataTable e TransactionsTable
- Come funziona il promote esistente nella Main Table (selection-based)
- Come funziona il txStore SSoT (txStoreGet, txStoreSetAll, txStoreInvalidate)

⚠️ BREAKING CHANGE DA D1:
- Gli endpoint `POST /transactions/split` e `POST /transactions/promote` sono stati ELIMINATI.
- Split e promote passano esclusivamente per `POST /transactions/commit` con `{splits: [...], promotes: [...]}`.
- Schema eliminati: TXSplitItem, TXSplitRequest, TXSplitResponse, TXPromoteItem, TXPromoteRequest, TXPromoteResponse.
- Nuovo endpoint: `POST /transactions/promote-suggest` (body: List[TXPromoteSuggestInput], query: tolerance_days).
- Il client TS è già rigenerato (`./dev.py api sync` fatto in D1).
- La Main Table promote (`confirmPromote()`) attualmente chiamerebbe il vecchio /promote che non esiste più → va migrata a batch `{promotes: [{id_a, id_b, resolved_fields}]}`.
- La tipizzazione `TXBatchOperation = Literal["create","update","delete","split","promote"]` è centralizzata in transactions.py.

Se a seguito delle scelte implementative fatte in D1 (eliminazione endpoint standalone, `consumed_link_uuids`, `resolved_fields` applicato a entrambi i lati), qualcosa nel piano D padre va raffinato per il frontend, segnalalo esplicitamente.

Crea il sotto-piano D2 che copre gli step: C5, C3, C4, C1, C2, C6, C7.

In sintesi devi pianificare:
1. PromoteMergeModal (C5) — nuovo componente greenfield, 3-column diff UI (sinistra readonly, centro editabile, destra readonly), pulsanti ◀ ⟷ ▸, per description/tags/date/cost_basis
2. BulkModal split row action (C3) — saved paired → pendingSplits nel commit, new paired → trasformazione locale
3. BulkModal promote toolbar (C4) — 2 saved, 2 new (locale), 1 saved + 1 new (mixed)
4. Main Table split row action (C1) — nuova row action + ConfirmModal + handler. Usa batch: `{splits: [{id}]}`
5. Main Table promote evoluzione (C2) — MIGRARE da vecchio /promote a batch `{promotes: [{id_a, id_b, resolved_fields}]}`. Usare MergeModal se campi divergono.
6. Promote suggest green banner (C6) — DB candidates via $effect + local candidates via $derived, banner verde con pulse + click 🔗. Endpoint: `POST /transactions/promote-suggest`.
7. i18n (C7)

Il file va salvato come: plan-phase07-transaction-Part4_Round6_PlanD2_FrontendSplitPromoteUI.prompt.md
```

### Prompt D3 — E2E Tests

```
Leggiti il piano padre #file:plan-phase07-transaction-Part4_Round6_PlanD_SplitPromoteFullStack.prompt.md, il sotto-piano D1 #file:plan-phase07-transaction-Part4_Round6_PlanD1_BackendBatchSuggest.prompt.md e il sotto-piano D2 #file:plan-phase07-transaction-Part4_Round6_PlanD2_FrontendSplitPromoteUI.prompt.md (+ eventuali bugfix di D1 e D2).

Poi leggiti il contesto dei test E2E esistenti nella cartella #file:RoadmapV4_UI — in particolare i piani che hanno aggiunto test (PlanA, PlanB, PlanB23, PlanC) e i file spec esistenti in frontend/e2e/transactions/ per capire:
- Pattern di test (data-testid, data-action-id, login, resetDatabase, navigateTo)
- Come sono strutturati i test per BulkModal (tx-bulk-operations.spec.ts)
- Come sono strutturati i test per delete (tx-delete.spec.ts)
- Come funziona la registrazione nel test runner (_frontend_transaction.py)
- Quali mock data sono disponibili (promote-test tag aggiunto in D1)

Se a seguito delle scelte implementative fatte in D1 e D2, qualcosa nel piano D padre va raffinato per i test, segnalalo esplicitamente.

Crea il sotto-piano D3 che copre: tx-split-promote.spec.ts (10 scenari) + registrazione nel test runner.

Il file va salvato come: plan-phase07-transaction-Part4_Round6_PlanD3_E2ETests.prompt.md
```
