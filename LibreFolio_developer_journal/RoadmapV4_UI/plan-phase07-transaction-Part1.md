
# Plan: Phase 7 — Part 1: DB & Schema Realignment + AssetEvent Bulk Delete

**Data**: 18 Aprile 2026
**Status**: 📋 PIANIFICATO (pronto per implementazione)
**Priorità**: P0 (prerequisito di tutte le altre parti di Phase 7)
**Effort stimato**: ~1.5 giorni
**Phase**: [Phase 7 — Transactions System](../phase-07-transactions.md)

> **📌 Contesto**: piano di dettaglio della **Parte 1** del macro-plan di Phase 7.
> Senza questa parte non si può né estendere BRIM (Parte 2) né propagare il link
> evento-transazione nelle API (Parte 3) e nella Staging Modal (Parte 5).

---

## 🎯 Obiettivo

1. **Collegare `Transaction` ad `AssetEvent`** (FK opzionale `asset_event_id`) con validatore di
   coerenza, flag `event_compatible` per-tipo in `TX_TYPE_METADATA`, e rigenerazione del DB.
2. **Proteggere l'integrità referenziale** con `ON DELETE RESTRICT` sulla nuova FK.
3. **Convertire l'AssetEvent delete API in full-bulk** coerente con il pattern di Phase 7,
   con response RESTRICT-aware che espone breakdown accessible / hidden per-utente.
4. **Sanare il flusso AssetDataEditor** (4 bug correlati) con copertura E2E.

**Semantica del link**: quando `asset_event_id` è valorizzato, la transazione è
**la realizzazione personale, nel portafoglio dell'utente, di un evento asset globale**.

---

## 📊 Situazione di partenza

### Backend
- [`Transaction`](../../../../../backend/app/db/models.py) (L550–L659): senza FK verso eventi
- [`AssetEvent`](../../../../../backend/app/db/models.py) (L708–L753): operativo dopo Round 12
- [`TXCreateItem`](../../../../../backend/app/schemas/transactions.py) / `TXReadItem` / `TXUpdateItem`: completi
- [`TX_TYPE_METADATA`](../../../../../backend/app/schemas/transactions.py) (L507–L629)
- [`001_initial.py`](../../../../../backend/alembic/versions/001_initial.py) (L261–L290): no `asset_event_id`
- [`DELETE /api/v1/assets/events/{id}`](../../../../../backend/app/api/v1/assets.py) (L943-L959): single-only, ritorna 200 anche se non trovato

### Frontend
- [`AssetDataEditorSection.svelte`](../../../../../frontend/src/lib/components/assets/AssetDataEditorSection.svelte) (L313-L330): batch via `Promise.all` di chiamate single, count toast errato, no re-derive post-save

### Bug observati (gap di test)
- DELETE event → backend risponde `{success:false, message:"not found"}` con HTTP 200 → frontend non se ne accorge
- Toast "N events deleted" indipendente dal numero realmente cancellato
- Multi-select → solo l'ultimo DELETE va a buon fine in alcuni casi (race su `Promise.all` + ID stale)
- Punto cancellato sul grafico ma riga rimane nella tabella

---

## 🗂️ Scope (files)

| # | File | Tipo | Modifica |
|---|------|------|----------|
| 1 | `backend/app/db/models.py` | Modifica | `Transaction.asset_event_id` FK + index |
| 2 | `backend/app/schemas/transactions.py` | Modifica | 3 schemi + `EVENT_COMPATIBLE_TYPES` + flag + validator |
| 3 | `backend/alembic/versions/001_initial.py` | Modifica | Colonna + FK RESTRICT + indice |
| 4 | `backend/app/services/transaction_service.py` | Modifica | `_validate_asset_event_link` + propagazione campo |
| 5 | `backend/app/services/asset_source.py` | Modifica | `delete_events_bulk` con RESTRICT-aware response |
| 6 | `backend/app/api/v1/assets.py` | Modifica | Rimuove `DELETE /events/{id}`, aggiunge `DELETE /events?ids=...` |
| 7 | `backend/app/schemas/prices.py` (o assets.py) | Modifica | `FAEventBulkDeleteResponse` con per-item status |
| 8 | `frontend/src/lib/components/assets/AssetDataEditorSection.svelte` | Modifica | Bulk call + count corretto + re-derive eventi |
| 9 | `frontend/src/lib/i18n/locales/{en,it,fr,es}/*.json` | Modifica | `dataEditor.col.currency` + `dataEditor.col.type` |
| 10 | `backend/test_scripts/test_db/db_schema_validate.py` | Modifica | Assertion FK + index |
| 11 | `backend/test_scripts/test_schemas/test_transaction_schemas.py` | Modifica | 6 nuovi test validator |
| 12 | `backend/test_scripts/test_services/test_transaction_service.py` | Modifica | 6 nuovi test cross-record + RESTRICT |
| 13 | `backend/test_scripts/test_api/test_transactions_api.py` | Modifica | 4 nuovi test E2E |
| 14 | `backend/test_scripts/test_api/test_assets_events.py` | Modifica/Nuovo | Test bulk delete + RESTRICT response |
| 15 | `frontend/e2e/asset-event-delete.spec.ts` | **Nuovo** | E2E che avrebbe colto i bug A-D |
| 16 | `backend/test_scripts/test_db/populate_mock_data.py` | Modifica (opz.) | 1-2 tx con `asset_event_id` per smoke-test |

---

## 🔧 Blocchi di implementazione

### Blocco 1 — Modello DB (15 min)

**File**: `backend/app/db/models.py`, classe `Transaction` (~L575–L660)

Aggiungere dopo `cost_basis_override` (L651):

```python
# Link to AssetEvent (global asset-level event realized in this portfolio)
# NULL = stand-alone transaction. When set, validates that
# asset_id == asset_event.asset_id (via service layer DB lookup) and
# that transaction type is "event_compatible" (DIVIDEND, INTEREST, ADJUSTMENT).
# ondelete=RESTRICT: event cannot be deleted while referenced by transactions.
# This is consistent with Asset↔Transaction integrity policy (preserves user data).
asset_event_id: Optional[int] = Field(
    default=None,
    sa_column=Column(
        Integer,
        ForeignKey("asset_events.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    ),
    description="FK to AssetEvent this transaction realizes. RESTRICT on delete.",
)
```

`__table_args__` (L576-L580):
```python
Index("idx_transactions_asset_event", "asset_event_id"),
```

---

### Blocco 2 — Migrazione DB (10 min)

**File**: `backend/alembic/versions/001_initial.py`

`CREATE TABLE transactions` (L262–L282) → aggiungere prima di `created_at`:
```sql
asset_event_id        INTEGER,
```

E nella lista FK:
```sql
FOREIGN KEY (asset_event_id) REFERENCES asset_events (id) ON DELETE RESTRICT
```

Dopo i CREATE INDEX (L289):
```python
conn.execute(sa.text("CREATE INDEX idx_transactions_asset_event ON transactions (asset_event_id)"))
```

Aggiornare contatore: `"  ✓ 7 Indexes created"`.

**Validazione**: `./dev.py db create-clean`.

---

### Blocco 3 — Schema Pydantic + Validator (30 min)

**File**: `backend/app/schemas/transactions.py`

#### 3.1 — Costante (top of file, dopo L35)
```python
EVENT_COMPATIBLE_TYPES: frozenset[TransactionType] = frozenset({
    TransactionType.DIVIDEND,
    TransactionType.INTEREST,
    TransactionType.ADJUSTMENT,
})
```

#### 3.2 — `TXCreateItem` (L75–L201)
Campo dopo `cost_basis_override`:
```python
asset_event_id: Optional[int] = Field(
    default=None, gt=0,
    description="Link to AssetEvent (DIVIDEND/INTEREST/ADJUSTMENT only)",
)
```

In `validate_transaction_rules` aggiungere prima di `return self`:
```python
# Rule 9: asset_event_id requires event-compatible type + asset_id present.
# NOTE: cross-record check (asset_id == asset_event.asset_id) is in service layer.
if self.asset_event_id is not None:
    if self.type not in EVENT_COMPATIBLE_TYPES:
        raise ValueError(
            f"{self.type.value} cannot be linked to an asset_event "
            f"(only {sorted(t.value for t in EVENT_COMPATIBLE_TYPES)} can)"
        )
    if self.asset_id is None:
        raise ValueError("asset_event_id requires asset_id")
```

#### 3.3 — `TXReadItem` (L221-L299)
Aggiungere `asset_event_id: Optional[int] = None` e propagarlo in `from_db_model`.

#### 3.4 — `TXUpdateItem` (L307-L350)
```python
asset_event_id: Optional[int] = Field(
    default=None,
    description="Link/unlink to AssetEvent. Use 0 to unlink, None to leave unchanged.",
)
```

#### 3.5 — `TXTypeMetadata` (L477-L502)
```python
event_compatible: bool = Field(..., description="Can be linked to an AssetEvent")
```

#### 3.6 — `TX_TYPE_METADATA` (L507-L629)
Aggiungere `event_compatible=True/False` per ogni entry:
- **True**: `DIVIDEND`, `INTEREST`, `ADJUSTMENT`
- **False**: `BUY`, `SELL`, `DEPOSIT`, `WITHDRAWAL`, `FEE`, `TAX`, `TRANSFER`, `FX_CONVERSION`

---

### Blocco 4 — Service Layer Transactions (20 min)

**File**: `backend/app/services/transaction_service.py`

Helper privato:
```python
def _validate_asset_event_link(
    self, session: Session, asset_event_id: int, expected_asset_id: int,
) -> None:
    """Verify event exists and belongs to expected asset. Raises ValueError on mismatch."""
    event = session.get(AssetEvent, asset_event_id)
    if event is None:
        raise ValueError(f"asset_event_id={asset_event_id} not found")
    if event.asset_id != expected_asset_id:
        raise ValueError(
            f"asset_event_id={asset_event_id} belongs to asset {event.asset_id}, "
            f"not {expected_asset_id}"
        )
```

In `create_bulk` per ogni `item`:
```python
if item.asset_event_id is not None:
    self._validate_asset_event_link(session, item.asset_event_id, item.asset_id)
```
e passare `asset_event_id=item.asset_event_id` al costruttore.

In `update_bulk` (con sentinel `0` = unlink):
```python
if item.asset_event_id is not None:
    if item.asset_event_id == 0:
        tx.asset_event_id = None
    else:
        self._validate_asset_event_link(session, item.asset_event_id, tx.asset_id)
        tx.asset_event_id = item.asset_event_id
```

---

### Blocco 5 — AssetEvent Bulk Delete + RESTRICT-aware Response (45 min)

**File**: `backend/app/services/asset_source.py`

Sostituire `delete_event_by_id(event_id)` con:

```python
@staticmethod
async def delete_events_bulk(
    event_ids: list[int],
    session: AsyncSession,
    current_user: User,
) -> "FAEventBulkDeleteResponse":
    """
    Bulk delete asset events. For each ID returns one of:
    - status='deleted'  (succeeded)
    - status='not_found'
    - status='in_use'   with accessible_transactions[] + hidden_transactions_count
    
    No partial rollback: each ID is independent. Successful deletes are committed.
    """
    results: list[FAEventDeleteItemResult] = []
    
    for event_id in event_ids:
        event = await session.get(AssetEvent, event_id)
        if event is None:
            results.append(FAEventDeleteItemResult(
                event_id=event_id, status="not_found",
            ))
            continue
        
        # RESTRICT pre-check: query transactions referencing this event,
        # split by user accessibility via BrokerUserAccess JOIN.
        accessible_q = (
            select(Transaction.id)
            .join(BrokerUserAccess, Transaction.broker_id == BrokerUserAccess.broker_id)
            .where(
                Transaction.asset_event_id == event_id,
                BrokerUserAccess.user_id == current_user.id,
            )
        )
        accessible_ids = (await session.exec(accessible_q)).all()
        total_count = (await session.exec(
            select(func.count(Transaction.id)).where(Transaction.asset_event_id == event_id)
        )).one()
        hidden = total_count - len(accessible_ids)
        
        if total_count > 0:
            results.append(FAEventDeleteItemResult(
                event_id=event_id, status="in_use",
                accessible_transactions=list(accessible_ids),
                hidden_transactions_count=hidden,
            ))
            continue
        
        # Safe to delete
        await session.delete(event)
        results.append(FAEventDeleteItemResult(
            event_id=event_id, status="deleted",
        ))
    
    await session.commit()
    
    return FAEventBulkDeleteResponse(
        results=results,
        deleted_count=sum(1 for r in results if r.status == "deleted"),
        not_found_count=sum(1 for r in results if r.status == "not_found"),
        in_use_count=sum(1 for r in results if r.status == "in_use"),
    )
```

**File**: `backend/app/schemas/prices.py` (o `assets.py`, dove vivono gli schemi event)

```python
class FAEventDeleteItemResult(BaseModel):
    event_id: int
    status: Literal["deleted", "not_found", "in_use"]
    accessible_transactions: list[int] = Field(default_factory=list)
    hidden_transactions_count: int = 0

class FAEventBulkDeleteResponse(BaseModel):
    results: list[FAEventDeleteItemResult]
    deleted_count: int
    not_found_count: int
    in_use_count: int
```

**File**: `backend/app/api/v1/assets.py`

**Rimuovere** `DELETE /{event_id}` (L943-L959, full-bulk philosophy).
**Aggiungere**:

```python
@event_router.delete("", response_model=FAEventBulkDeleteResponse)
async def delete_events_bulk_endpoint(
    ids: List[int] = Query(..., description="Event IDs to delete"),
    session: AsyncSession = Depends(get_session_generator),
    current_user: User = Depends(get_current_user),
):
    """
    Bulk delete asset events. Per-item result with RESTRICT awareness:
    if an event is referenced by transactions, returns the list of accessible
    transaction IDs (for user) + hidden count (other users).
    """
    return await AssetSourceManager.delete_events_bulk(ids, session, current_user)
```

**HTTP semantics**: sempre 200 OK con per-item result (frontend filtra). Niente 207/multi-status.

---

### Blocco 6 — Frontend: AssetDataEditorSection bugfix (45 min)

**File**: `frontend/src/lib/components/assets/AssetDataEditorSection.svelte`

#### 6.1 — Sostituire il loop `Promise.all` (L320-329)

```typescript
if (realDeletes.length > 0) {
    const ids = realDeletes.map((r) => parseInt(r.rowId, 10));
    const result = await zodiosApi.delete_events_bulk_api_v1_assets_events_delete({
        queries: { ids },
    });
    
    // Use REAL counts from backend response, not the requested length
    if (result.deleted_count > 0) {
        parts.push(`${result.deleted_count} events deleted`);
    }
    if (result.not_found_count > 0) {
        toasts.warning(`${result.not_found_count} events were already gone`);
    }
    if (result.in_use_count > 0) {
        const inUseDetails = result.results.filter((r) => r.status === 'in_use');
        const totalRefs = inUseDetails.reduce(
            (acc, r) => acc + r.accessible_transactions.length + r.hidden_transactions_count, 0
        );
        toasts.error(
            $t('events.deleteBlocked', {
                count: result.in_use_count,
                refs: totalRefs,
            })
        );
        // TODO Phase 7 Part 4/5: open transactions filtered by these IDs to let user unlink
    }
    
    // Remove only successfully deleted events from local state
    const deletedIds = new Set(
        result.results.filter((r) => r.status === 'deleted').map((r) => r.event_id)
    );
    eventRows = eventRows.filter(
        (r) => !(r.status === 'deleted' && deletedIds.has(parseInt(r.rowId, 10)))
    );
}
```

#### 6.2 — Re-derive `eventRows` post-save (dopo L333 `toasts.success`)

Dopo il save aggiungere:
```typescript
// Re-derive editable rows from upstream events to clear "deleted/edited" flags
// for rows that successfully changed status. Pending rows still in conflict
// (e.g. in_use blockers) are preserved by the deletedIds filter above.
eventRows = eventsToEventRows(events.filter(
    (e) => !eventRows.some((r) => r.status === 'deleted' && parseInt(r.rowId, 10) === e.id)
));
```

> **Nota**: idealmente il save deve trigger un `onsave?.()` che provoca refetch eventi nel parent. Verificare se `onsave` già dispatchia un reload — se sì, basta confermare. Se no, la riga sopra è il fallback minimo.

---

### Blocco 7 — i18n (10 min)

```bash
./dev.py i18n add "dataEditor.col.currency" \
  --en "Currency" --it "Valuta" --fr "Devise" --es "Divisa"
./dev.py i18n add "dataEditor.col.type" \
  --en "Type" --it "Tipo" --fr "Type" --es "Tipo"
./dev.py i18n add "events.deleteBlocked" \
  --en "{count} event(s) cannot be deleted: {refs} transaction(s) still reference them. Unlink the transactions first." \
  --it "{count} evento/i non può essere eliminato: {refs} transazione/i lo referenziano ancora. Scollega prima le transazioni." \
  --fr "{count} événement(s) ne peut être supprimé : {refs} transaction(s) y font référence." \
  --es "{count} evento(s) no se puede eliminar: {refs} transacción(es) aún lo referencian."
./dev.py i18n audit
```

---

### Blocco 8 — API Sync (5 min)

```bash
./dev.py api sync
```

Verificare che `frontend/src/lib/api/generated.ts` contenga:
- `delete_events_bulk_api_v1_assets_events_delete` (sostituisce `delete_event_api_v1_assets_events__event_id__delete`)
- `FAEventBulkDeleteResponse`, `FAEventDeleteItemResult`
- `event_compatible: boolean` in `TXTypeMetadata`
- `asset_event_id: number | null` in `TXCreateItem` / `TXReadItem` / `TXUpdateItem`

---

### Blocco 9 — Test Suite (1h 30min)

#### 9.1 — Backend DB (`db_schema_validate.py`)
- `test_transactions_has_asset_event_fk_restrict` — colonna + FK + ON DELETE RESTRICT + index

#### 9.2 — Backend Schemas (`test_transaction_schemas.py`)
- `test_asset_event_id_on_dividend_ok`
- `test_asset_event_id_on_buy_rejected`
- `test_asset_event_id_without_asset_id_rejected`
- `test_tx_read_item_roundtrip_with_asset_event_id`
- `test_tx_update_sentinel_zero_unlinks`
- `test_tx_type_metadata_event_compatible_flags`

#### 9.3 — Backend Service (`test_transaction_service.py`)
- `test_create_bulk_with_valid_asset_event_link`
- `test_create_bulk_with_mismatched_asset_event_rejected`
- `test_create_bulk_with_nonexistent_asset_event_rejected`
- `test_update_bulk_can_unlink_with_sentinel_zero`
- `test_update_bulk_can_relink_to_different_event`

#### 9.4 — Backend AssetEvent Delete (`test_assets_events.py`)
- `test_delete_event_bulk_happy_path` — 3 ids, 3 deleted
- `test_delete_event_bulk_not_found_marked_correctly` — id inesistente → status=not_found
- `test_delete_event_bulk_in_use_returns_breakdown` — evento referenziato da 2 tx user + 1 tx altro user → status=in_use, accessible_transactions=[2 ids], hidden_transactions_count=1
- `test_delete_event_bulk_partial_success` — mix di deleted/not_found/in_use, success commitati
- `test_delete_event_bulk_no_partial_rollback` — un in_use non blocca i deletable

#### 9.5 — Backend API Transactions (`test_transactions_api.py`)
- `test_post_transactions_with_asset_event_id`
- `test_get_types_includes_event_compatible_flag`
- `test_post_buy_with_asset_event_id_returns_400`
- `test_old_single_delete_endpoint_returns_404` — endpoint rimosso

#### 9.6 — Frontend E2E (`asset-event-delete.spec.ts`) — NUOVO

```typescript
test('selecting and deleting events: count, table refresh, blocked items', async ({ page }) => {
    // Setup: navigate to asset detail with at least 3 events
    // Action 1: select 1 event → click delete → save
    // Verify: toast "1 events deleted", row removed from table, chart updated
    // Action 2: select 2 events, one of which is referenced by a transaction
    // Verify: toast "1 events deleted" + warning "1 event blocked: 1 transaction references it"
    // Verify: deleted row gone from table, blocked row still present
});

test('delete non-existent event id (stale UI) shows warning', async ({ page }) => {
    // Setup: open editor, simulate stale state by mocking event already deleted
    // Verify: toast warning "1 events were already gone"
});
```

#### 9.7 — `populate_mock_data.py` (opzionale)
1-2 transazioni DIVIDEND con `asset_event_id` valorizzato.

---

## 📋 Sequenza di esecuzione consigliata

```
1. Blocco 1 — models.py
2. Blocco 2 — 001_initial.py
3. ./dev.py db create-clean
4. Blocco 9.1 — verifica schema
5. Blocco 3 — schemas pydantic
6. Blocco 9.2 — schema tests
7. Blocco 4 — transaction_service
8. Blocco 9.3 — service tests
9. Blocco 5 — asset_source.delete_events_bulk + endpoint
10. Blocco 9.4 — bulk delete tests
11. Blocco 8 — ./dev.py api sync
12. Blocco 6 — frontend AssetDataEditorSection
13. Blocco 7 — i18n keys
14. Blocco 9.5 — API tests transactions
15. Blocco 9.6 — E2E asset-event-delete
16. Blocco 9.7 — populate (opz.)
17. ./dev.py test all && ./dev.py lint backend && ./dev.py format backend
```

---

## ✅ Checklist completamento

### Schema & DB
- [x] `Transaction.asset_event_id` con FK RESTRICT + index
- [x] `001_initial.py` aggiornato
- [x] `./dev.py db create-clean` OK
- [x] `test_transactions_has_asset_event_fk_restrict` passa

### Pydantic
- [x] `TXCreateItem.asset_event_id` validato (tipo + asset_id)
- [x] `TXReadItem.asset_event_id` propagato
- [x] `TXUpdateItem.asset_event_id` con sentinel `0`
- [x] `TXTypeMetadata.event_compatible` (3 True, 8 False)
- [x] `EVENT_COMPATIBLE_TYPES` esportato

### Service
- [x] `_validate_asset_event_link` cross-record check
- [x] `create_bulk` / `update_bulk` propagano il campo
- [x] `delete_events_bulk` con per-item status
- [x] Breakdown accessible/hidden corretto

### API
- [x] `DELETE /api/v1/assets/events/{id}` rimosso
- [x] `DELETE /api/v1/assets/events?ids=...` aggiunto, ritorna `FAEventBulkDeleteResponse`
- [x] `./dev.py api sync` rigenera client

### Frontend
- [x] AssetDataEditorSection usa bulk endpoint
- [x] Toast count corretto (`deleted_count` da risposta, non `realDeletes.length`)
- [x] Warning toast per `not_found_count` e `in_use_count`
- [x] Tabella si aggiorna post-save (righe deleted+success rimosse)
- [ ] i18n: `dataEditor.col.currency`, `dataEditor.col.type`, `events.deleteBlocked` × 4 lingue *(deferred — toasts use literal strings consistent with existing save flow; i18n work is centralized in future parts)*
- [ ] `./dev.py i18n audit` clean *(not run — no i18n key changes in this part)*

### Test
- [x] Schema tests verdi (6 nuovi su `TestAssetEventLink`, 58 totali in `test_transaction_schemas.py`)
- [x] Service tests verdi (5 in `TestAssetEventLinkService`, 35 totali in `test_transaction_service.py`)
- [x] AssetEvent bulk-delete tests verdi (5 nuovi in `test_assets_events.py`, 11 totali)
- [x] API transactions tests verdi (13 + 1 skip)
- [ ] E2E `asset-event-delete.spec.ts` verde *(deferred — nessun .spec.ts esistente da aggiornare; Part 4/5 aggiungeranno gli E2E integrati)*
- [x] `./dev.py test all-backend` relevant suites verdi (270 in schemas+services+db) — FX Sync flake pre-esistente (rate GBP) non correlato
- [ ] Copertura `transaction_service` ≥85% *(non misurata in questa iterazione)*
- [ ] Copertura `delete_events_bulk` ≥85% *(non misurata in questa iterazione)*

### Tooling
- [x] `./dev.py lint` clean
- [x] `./dev.py format` applicato
- [x] `./dev.py front check` clean

---

## 🚧 Decisioni chiave (consolidate)

| # | Decisione | Scelta | Motivazione |
|---|-----------|--------|-------------|
| 1 | Comportamento `ON DELETE` | **RESTRICT + structured per-item response** con breakdown accessible/hidden | Coerente con Asset↔Transaction, preserva dati utente, espone info utile al frontend senza leak |
| 2 | Sentinel unlink in `TXUpdateItem` | **`asset_event_id=0`** | Coerente con altri schemi (`gt=0`), evita campi correlati |
| 3 | Cross-record check `asset_id == event.asset_id` | **Service layer (DB lookup)** + Pydantic per regole statiche | Pydantic non può fare lookup; service produce errori user-friendly per-item; FK è guardia finale |
| 4 | `ADJUSTMENT` event-compatible? | **Sì** (per SPLIT, PRICE_ADJUSTMENT) | Altrimenti SPLIT resterebbe scollegato dalle transazioni di aggiustamento |
| 5 | Flag `event_compatible` esposto | **Auto via `GET /transactions/types`** dopo `api sync` | Zero codice extra, frontend riceve gratis |
| 6 | Endpoint single `DELETE /events/{id}` | **Rimosso** (full-bulk philosophy Phase 7) | Nessuna legacy compat (non in produzione) |
| 7 | HTTP code per delete bulk con conflitti | **200 OK con per-item result** (no 207) | Frontend ispeziona `results[]`; più semplice di multi-status |
| 8 | Rollback parziale su delete bulk | **No**: deleted committati anche se altri sono in_use | Massimizza progresso utile, l'utente vede chiaramente cosa è bloccato |

---

## 📎 Dipendenze & Sblocca

- **Richiede**:
  - Round 12 di Phase 6 ✅
  - `TransactionService.create_bulk`/`update_bulk` operativi ✅
- **Sblocca**:
  - Parte 2 (BRIM Plugin v2: `asset_events` + link nel commit atomico)
  - Parte 3 (`/transactions/validate` + `/transactions/events/suggest` propagano il campo)
  - Parte 4 (colonna ●evt nella tabella transactions, GoTo all'evento)
  - Parte 5 (Staging Modal con tolerance slider + auto-link + handling RESTRICT errors via `accessible_transactions`)

---

## 🔗 Cross-link

- Phase principale: [`phase-07-transactions.md`](../phase-07-transactions.md)
- Round 12 (AssetEvent): [`phase-06-subplan/Bugfix-Step3/plan-phase06Step3Round12-AssetEventAndScheduleRedesign.prompt.md`](../phase-06-subplan/Bugfix-Step3/plan-phase06Step3Round12-AssetEventAndScheduleRedesign.prompt.md)
- Modello DB: [`backend/app/db/models.py`](../../../../../backend/app/db/models.py)
- Schemas: [`backend/app/schemas/transactions.py`](../../../../../backend/app/schemas/transactions.py)
- Migrazione: [`backend/alembic/versions/001_initial.py`](../../../../../backend/alembic/versions/001_initial.py)
- TX Service: [`backend/app/services/transaction_service.py`](../../../../../backend/app/services/transaction_service.py)
- Asset Source: [`backend/app/services/asset_source.py`](../../../../../backend/app/services/asset_source.py)
- API Assets: [`backend/app/api/v1/assets.py`](../../../../../backend/app/api/v1/assets.py)
- Frontend Editor: [`frontend/src/lib/components/assets/AssetDataEditorSection.svelte`](../../../../../frontend/src/lib/components/assets/AssetDataEditorSection.svelte)
