# Plan: WAC Inline in Validate/Commit + Analytics Migration

> **⏳ STATUS**: PENDING REVIEW — awaiting user approval before execution.

**Parent plan**: [`plan-FixWacFeedbackLoop.prompt.md`](./plan-FixWacFeedbackLoop.prompt.md) (v8+v8b completato — questo piano ristruttura l'architettura WAC)

---

## Obiettivo

Eliminare l'endpoint `/wac-preview` dal flusso workspace editing. Il calcolo WAC viene integrato nella response di `/validate` e applicato server-side in `/commit`. L'endpoint esistente viene migrato verso `/analytics/wac` per serie temporali (dashboard, grafici).

---

## Decisioni architetturali

### 1. `cost_basis_mode` esteso con livello di dettaglio

```python
cost_basis_mode: Literal["auto", "auto-detail", "manual"] | None
```

| Valore | Chi lo manda | Cosa ritorna il backend |
|--------|-------------|------------------------|
| `"auto"` | BulkModal (celle) | `wac: Currency` + `source_broker_id` |
| `"auto-detail"` | FormModal (tabella qualifying) | `wac` + `qualifying_txs[]` + `missing_pairs` + `asset_price` |
| `"manual"` | Ovunque | nulla (usa `cost_basis_override` as-is) |
| `None` | BUY, SELL, etc. | nulla |

### 2. Determinazione source broker (backend-side)

Per ogni item con `cost_basis_mode` in `("auto", "auto-detail")`:

1. **Ha `link_uuid`?** → è un TRANSFER receiver. Cerca il partner (stesso `link_uuid`, diverso `broker_id`) nel **payload originale** (creates + updates) → usa il **partner's broker_id** come source
2. **No `link_uuid`?** → è un ADJUSTMENT standalone. Usa il **proprio broker_id** con `excluded_tx_ids=[self.id]` per ottenere il WAC del pool senza self (pool invariant)

**Note**: il matching `link_uuid` è cross-operation (il giver può essere un update, il receiver un create). La ricerca avviene nel payload originale del batch, non nel DB.

### 3. Riuso schema esistenti

La response WAC inline riusa `WACPreviewResultItem` e `WACQualifyingTX` già esistenti — zero nuovi schemi per i dati WAC. Solo un wrapper per il posizionamento nel batch:

```python
class TXBatchWacResult(BaseModel):
    """WAC result for a single auto item in the batch."""
    operation: Literal["create", "update"]
    index: int  # posizione in creates[] o updates[]
    source_broker_id: int  # broker usato per il calcolo
    # Campi da WACPreviewResultItem (flat, non nested)
    wac: Optional[Currency] = None
    qualifying_txs: Optional[List[WACQualifyingTX]] = None  # solo se auto-detail
    missing_pairs: List[str] = Field(default_factory=list)
    asset_price: Optional[Currency] = None
    asset_price_stale: Optional[BackwardFillInfo] = None
    asset_price_missing: bool = False
```

### 4. Commit: backend applica WAC autonomamente

In `/commit`, per items con `cost_basis_mode = "auto"` o `"auto-detail"`:
- Backend calcola WAC (stessa logica)
- Scrive il risultato in `cost_basis_override` prima del DB flush
- Il frontend NON manda il valore — manda solo `cost_basis_mode: "auto"` + `cost_basis_override: null`
- Zero feedback loop possibile (il valore non torna mai al frontend per essere ri-mandato)

**Nota**: `cost_basis_mode` NON viene persistito in DB. È un'istruzione di sessione. Dopo commit, la TX ha solo `cost_basis_override` (valore esplicito). Se l'utente ri-edita, il frontend la mostra come "manual" (perché ha un valore). Design corretto: una volta committato, il valore È il valore.

### 5. Post-flush computation (architettura semplificata)

**Insight chiave**: il calcolo WAC avviene **post-flush**, direttamente sullo stato della session. Non serve un adapter per convertire batch items in pending_txs.

Flusso in `execute_batch`:
```
1. Parse pydantic (lenient)
2. Applica deletes → splits → updates → creates → promotes → link resolution
3. Flush intermedi (ogni create fa flush per avere ID)
4. ══════ STEP 6b: WAC COMPUTATION ══════
   Per ogni auto item:
   - TRANSFER: compute_wac_iterative(broker_id=SOURCE) ← session vede i rows flushati
   - ADJUSTMENT: compute_wac_iterative(broker_id=OWN, excluded_tx_ids=[self.id])
   Scrive cost_basis_override sugli auto items
5. Flush finale
6. Balance walk (vede i cbo corretti)
7. Decision: rollback (validate) o commit
```

**Perché funziona senza adapter**: dopo il flush, tutti i rows del batch sono nel DB (session-level, non committed). `compute_wac_iterative` fa query normali sulla stessa session → vede tutto. Per l'ADJUSTMENT, si esclude self per ottenere il WAC "prima di lui."

**Perché il WAC è sempre nella response** (anche con issues di business logic): il balance walk avviene DOPO il WAC computation. Se il balance fallisce → rollback, ma `wac_results[]` è già calcolato e ritornato nella response. Il frontend ha il preview WAC indipendentemente dalla validità del balance.

**Condizione**: WAC computation avviene SOLO se zero issues pydantic e zero issues di accesso. Se ci sono errori di formato → `wac_results: null`.

### 6. `/analytics/wac` — endpoint per serie temporali (Phase 9)

L'attuale `/transactions/wac-preview` viene preservato sotto un nuovo router analytics, ridisegnato per query read-only su dati committed:

```python
# POST /api/v1/analytics/wac
{
  "queries": [
    {"broker_id": 1, "asset_id": 1, "date_range": {"start": "2026-01-01", "end": "2026-05-28"}}
  ]
}
# Response: serie WAC point-per-transaction (non daily — solo dove il WAC cambia)
{
  "results": [
    {
      "broker_id": 1, "asset_id": 1,
      "series": [
        {"date": "2026-04-08", "wac": "150.00", "pool_qty": "10", "effect": "add"},
        {"date": "2026-04-22", "wac": "160.00", "pool_qty": "15", "effect": "add"},
        ...
      ]
    }
  ]
}
```

Nessun `pending_txs` — solo dati committed nel DB. Utile per overlay WAC su price chart e P&L storico.

---

## Steps di esecuzione

### Phase A: Backend — Schema + Logica WAC in execute_batch

#### Step A1: Estendere `cost_basis_mode` Literal

**File**: `backend/app/schemas/transactions.py`

- `TXCreateItem.cost_basis_mode`: da `Literal["auto", "manual"] | None` a `Literal["auto", "auto-detail", "manual"] | None`
- `WACPendingTXItem.cost_basis_mode`: idem (backward compat: "auto-detail" è nuovo, "auto" e None invariati)

#### Step A2: Creare `TXBatchWacResult` schema

**File**: `backend/app/schemas/transactions.py`

Aggiungere la classe `TXBatchWacResult` (vedi §3 sopra) dopo `TXBatchResultItem`.

#### Step A3: Estendere `TXBatchResponse` con `wac_results`

**File**: `backend/app/schemas/transactions.py`

```python
class TXBatchResponse(BaseModel):
    committed: bool
    issues: List[TXValidationIssue] = Field(default_factory=list)
    results: Optional[List[TXBatchResultItem]] = None
    wac_results: Optional[List[TXBatchWacResult]] = None  # NEW
```

#### Step A4: Implementare WAC computation in `execute_batch`

**File**: `backend/app/services/transaction_service.py`

Aggiungere un metodo privato `_compute_wac_for_auto_items()` chiamato nel punto 6b di `execute_batch` (tra link resolution e balance walk — riga 1729 attuale).

**Precondizioni**: zero issues pydantic + zero access denied. Se ci sono → skip (wac_results=None).

**Algoritmo** (post-flush, tutte le righe sono nella session):

```python
async def _compute_wac_for_auto_items(
    self,
    parsed_creates: list,   # [(orig_idx, TXCreateItem)]
    parsed_updates: list,   # [(orig_idx, TXUpdateItem)]
    created_tx_map: dict,   # {orig_idx: Transaction} — i DB rows creati
    updated_tx_map: dict,   # {orig_idx: Transaction} — i DB rows aggiornati
) -> list[TXBatchWacResult]:
    results = []
    
    # Collect all auto items
    auto_items = []
    for orig_idx, item in parsed_creates:
        if item.cost_basis_mode in ("auto", "auto-detail"):
            auto_items.append(("create", orig_idx, item, created_tx_map[orig_idx]))
    for orig_idx, item in parsed_updates:
        if item.cost_basis_mode in ("auto", "auto-detail"):
            auto_items.append(("update", orig_idx, item, updated_tx_map[orig_idx]))
    
    if not auto_items:
        return []
    
    for operation, idx, schema_item, db_tx in auto_items:
        # Determine source broker
        if schema_item.link_uuid:
            # TRANSFER: find partner in batch payload
            partner = self._find_link_partner(schema_item.link_uuid, parsed_creates, parsed_updates, schema_item)
            source_broker_id = partner.broker_id if partner else db_tx.broker_id
        else:
            # ADJUSTMENT standalone
            source_broker_id = db_tx.broker_id
        
        # Compute WAC (session sees all flushed rows)
        # For ADJUSTMENT: exclude self so we get "pool WAC before me"
        excluded = [db_tx.id] if not schema_item.link_uuid else []
        
        wac_result = await compute_wac_iterative(
            self.session,
            broker_id=source_broker_id,
            asset_id=db_tx.asset_id,
            as_of_date=db_tx.date,
            asset_currency=...,  # from asset lookup
            excluded_tx_ids=excluded,
        )
        
        # Write cbo on the DB row
        if wac_result.wac:
            db_tx.cost_basis_override = wac_result.wac.amount
            db_tx.cost_basis_currency = wac_result.wac.code
        
        # Build response item
        results.append(TXBatchWacResult(
            operation=operation, index=idx,
            source_broker_id=source_broker_id,
            wac=wac_result.wac,
            qualifying_txs=wac_result.wac_qualifying_txs if schema_item.cost_basis_mode == "auto-detail" else None,
            missing_pairs=wac_result.wac_missing_pairs,
            asset_price=wac_result.asset_price if schema_item.cost_basis_mode == "auto-detail" else None,
            asset_price_stale=wac_result.asset_price_stale if schema_item.cost_basis_mode == "auto-detail" else None,
            asset_price_missing=wac_result.asset_price_missing if schema_item.cost_basis_mode == "auto-detail" else False,
        ))
    
    return results
```

**Nota**: nessun adapter. `compute_wac_iterative` fa query dirette sulla session (dove i rows sono già flushati). L'unico override è `excluded_tx_ids` per gli ADJUSTMENT standalone.

#### Step A5: `./dev.py api sync`

Rigenerare client TypeScript con i nuovi campi su `TXBatchResponse`.

### Phase B: Backend — Test

#### Step B1: Adattare test WAC esistenti (P12-P15)

**File**: `backend/test_scripts/test_api/test_transactions_wac.py`

I test P12-P15 attualmente chiamano `/wac-preview`. Creare una COPIA dei test che chiama `/validate` con gli stessi scenari e asserisce `wac_results[]` nella response. L'endpoint `/wac-preview` resta funzionante (non rotto) — i vecchi test restano come regression.

#### Step B2: Nuovi test validate+commit con WAC

**File**: `backend/test_scripts/test_api/test_transactions_wac.py`

| Test | Scenario |
|------|----------|
| P16 | validate con TRANSFER auto → `wac_results[0].wac` = source broker WAC |
| P17 | validate con ADJUSTMENT auto → `wac_results[0].wac` = own broker WAC (pool invariant) |
| P18 | commit con TRANSFER auto → DB row ha `cost_basis_override` populato dal backend |
| P19 | validate con `auto-detail` → response include `qualifying_txs` |
| P20 | validate senza auto items → `wac_results` è null/empty |
| P21 | commit con TRANSFER auto + source_broker detection via link_uuid |
| P22 | update partial con `cost_basis_mode="auto"` (broker_id da DB) → WAC calcolato corretto |
| P23 | mixed batch: BUY + TRANSFER auto + ADJUSTMENT manual → `wac_results` ha solo 1 entry (TRANSFER) |
| P24 | TRANSFER: giver = update, receiver = create (link_uuid cross-operation) → source corretto |
| P25 | delete nel batch esclude TX dal pool → WAC cambia di conseguenza |
| P26 | batch con BUY + TRANSFER stesso broker (dipendenza intra-batch) → WAC include il BUY |
| P27 | TRANSFER auto da broker con pool vuoto → wac = null o amount "0" |
| P28 | `auto-detail` su ADJUSTMENT → qualifying include riga con effect="add_at_wac" |

#### Step B3: Test regression — endpoint `/wac-preview` ancora funzionante

Verificare che i test P1-P15 esistenti passano invariati (l'endpoint legacy non è rotto).

### Phase C: Frontend — BulkModal migration

#### Step C1: Eliminare `fetchBatchWac` e infrastruttura WAC dedicata

**File**: `frontend/src/lib/components/transactions/TransactionBulkModal.svelte`

Rimuovere:
- `wacFingerprint` derived
- `autoWacItems` derived
- `wacFetchInFlight`, `wacAbortController`, `wacDebounceTimer`, `wacFetchPromise`, `wacFetchResolve`
- `fetchBatchWac()` function
- `$effect` WAC (righe 304-319)
- Pre-commit WAC guard (righe 1214-1226)

#### Step C2: Leggere `wac_results` dalla validate response

**File**: `frontend/src/lib/components/transactions/TransactionBulkModal.svelte`

Nella `validateFn` (riga 1099), dopo la response:
```typescript
const result = await validateTransactions(payload, {...});
// Extract WAC results and populate wacResults map
if (result.wac_results) {
    const nextMap = new Map<string, WacResultEntry>();
    for (const wr of result.wac_results) {
        // Map (operation, index) back to tempId via resolvedOps ordering
        const tempId = resolvedOpsMap.get(`${wr.operation}:${wr.index}`);
        if (tempId) {
            nextMap.set(tempId, {
                wac: wr.wac, qualifying_txs: wr.qualifying_txs ?? [], missing_pairs: wr.missing_pairs,
            });
        }
    }
    wacResults = nextMap;
}
```

#### Step C3: Writeback WAC in ops per il display nelle celle

Dopo aver estratto `wac_results`, scrivere il valore in `ops[x].fields.cost_basis_override` (come oggi) ma con il guard di uguaglianza per evitare re-trigger inutili.

#### Step C4: Commit senza WAC value — solo mode

Nel commit payload, per items auto: mandare `cost_basis_override: null` + `cost_basis_mode: "auto"`. Il backend applica il valore. La response conferma il valore applicato.

#### Step C5: Eliminare pre-commit WAC await

L'attuale guard "aspetta che WAC sia calcolato prima di commit" (righe 1214-1226) diventa inutile — il commit stesso calcola il WAC. Rimuovere.

### Phase D: Frontend — FormModal migration

#### Step D1: FormModal manda `cost_basis_mode: "auto-detail"`

**File**: `frontend/src/lib/components/transactions/TransactionFormModal.svelte` (o equivalente)

Quando il toggle WAC è su "Auto", la riga nel payload validate ha `cost_basis_mode: "auto-detail"`.

#### Step D2: WacPreviewSection legge da validate response

**File**: `frontend/src/lib/components/transactions/WacPreviewSection.svelte`

Invece di chiamare `/wac-preview` autonomamente, riceve i dati WAC come prop (passati dal BulkModal/FormModal dopo la validate). La qualifying table, missing_pairs, asset_price vengono tutti dalla validate response.

#### Step D3: Eliminare chiamata diretta a `/wac-preview` dal FormModal

Rimuovere la fetch WAC standalone che il WacPreviewSection faceva internamente.

### Phase E: Cleanup + Analytics Migration

#### Step E1: Deprecare `/transactions/wac-preview`

**File**: `backend/app/api/v1/transactions.py`

Aggiungere header `Deprecation: true` + log warning. L'endpoint resta funzionante durante la migrazione frontend (Phase C+D).

#### Step E2: Creare router `/api/v1/analytics/`

**File**: `backend/app/api/v1/analytics.py` (nuovo)

Endpoint `POST /analytics/wac` con formato serie temporale per query su dati committed. Nessun `pending_txs`, nessun `excluded_tx_ids`. Riusa `compute_wac_iterative(session, broker_id, asset_id, as_of_date, asset_currency)` senza parametri opzionali.

#### Step E3: Aggiornare E2E tests

**File**: `frontend/e2e/transactions/tx-wac-bulk.spec.ts`

- WB6: non più intercetta `/wac-preview` — verifica che il valore WAC appare nelle celle dopo validate (non serve network count, il meccanismo è diverso)
- WB7: stesso adattamento
- WB1-WB5: aggiornare per il nuovo flusso

#### Step E4: Rimuovere `/transactions/wac-preview` + cleanup `pending_txs`

**File**: `backend/app/api/v1/transactions.py` — eliminare endpoint e route.
**File**: `backend/app/services/transaction_service.py` — rimuovere parametro `pending_txs` da `compute_wac_iterative` (dead code dopo rimozione endpoint).
**File**: `backend/app/schemas/transactions.py` — rimuovere `WACPendingTXItem`, `WACPreviewItem`, `WACPreviewRequest`, `WACPreviewResponse` (non più usati da nessuno).

Dopo E4, `compute_wac_iterative` ha firma semplificata:
```python
async def compute_wac_iterative(
    session: AsyncSession,
    broker_id: int,
    asset_id: int,
    as_of_date: date_type,
    asset_currency: str,
    excluded_tx_ids: list[int] | None = None,  # unico parametro opzionale rimasto
) -> WACPreviewResultItem:
```

**Nota**: `excluded_tx_ids` resta perché è usato da step 6b in `execute_batch` (ADJUSTMENT auto: escludi self). `/analytics/wac` lo chiama senza (default None).

---

## Mapping response → ops (dettaglio tecnico)

Il frontend deve mappare `wac_results[i]` (che ha `operation` + `index`) al `tempId` interno. Questo richiede che durante `resolveOps()` si mantenga una mappa di corrispondenza:

```typescript
// During resolveOps, track: "create:0" → tempId, "update:0" → tempId, etc.
const resolvedOpsMap = new Map<string, string>(); // "operation:index" → tempId
```

Questa mappa viene costruita durante `buildBatchPayload` e usata per mappare la response.

---

## Test Criteria

- [ ] Backend P16-P28: validate/commit con WAC inline (13 nuovi test)
- [ ] Backend P1-P15: regression (wac-preview ancora funzionante)
- [ ] Frontend: BulkModal mostra WAC nelle celle senza chiamata a /wac-preview
- [ ] Frontend: FormModal mostra qualifying table dai dati validate
- [ ] Frontend: Commit funziona con cbo=null + mode=auto (backend applica)
- [ ] E2E: WB1-WB7 adattati al nuovo flusso
- [ ] `./dev.py front check` — 0 errors
- [ ] `./dev.py api sync` eseguito

---

## Rischi e mitigazioni

| Rischio | Mitigazione |
|---------|-------------|
| Validate diventa lento (calcola WAC + validation) | WAC solo per items con mode=auto (pochi). compute_wac_iterative è già <20ms. Skip se pydantic errors. |
| Mapping response→tempId si rompe | Test E2E coprono il mapping; la mappa è deterministica (stessa logica di resolveOps) |
| FormModal ha latenza (aspetta validate per mostrare qualifying) | Il debounce validate è già in place; la FormModal manda "auto-detail" solo per la propria riga |
| Deprecazione wac-preview rompe qualcosa | L'endpoint resta attivo (solo warning). Rimozione solo dopo Phase E stabilizzata |
| ADJUSTMENT auto: WAC "senza self" diverge se pool vuoto | Pool vuoto → WAC=0, cbo=0 (semanticamente corretto: nessun prezzo di riferimento). Test P27 copre. |
| Double-submit (commit x2 stesso batch) | Secondo commit: la TX ha già cbo (dal primo commit) → niente da ricalcolare. `cost_basis_mode` non è in DB, il frontend non lo rimanda su TX già salvate. |

---

## Decisioni architetturali verificate (post-review)

| Tema | Decisione | Motivazione |
|------|-----------|-------------|
| Timing WAC | Post-flush, pre-balance walk | Session vede i rows; no adapter; balance vede cbo corretti |
| Adapter | **ELIMINATO** | Non serve: query dirette sulla session post-flush |
| `pending_txs` param | **RIMOSSO in Step E4** | Dopo rimozione /wac-preview, nessun caller lo usa più → dead code |
| `excluded_tx_ids` param | **RESTA** | Usato da step 6b per ADJUSTMENT auto (escludi self). Analytics lo ignora (default None). |
| `cost_basis_mode` in DB | NO — solo istruzione di sessione | Dopo commit il valore È il valore; re-edit mostra "manual" |
| WAC con pydantic errors | Skip (wac_results=null) | Inutile calcolare su dati malformati |
| WAC con balance errors | SI — calcolato comunque | Il frontend ha bisogno del preview anche se balance invalid |
| link_uuid matching | Cross-operation (creates+updates) | Il giver può essere un update, il receiver un create |
| ADJUSTMENT auto self-exclusion | `excluded_tx_ids=[self.id]` | Dà il "pool WAC prima di me" = valore corretto da scrivere |
| `/wac-preview` | **CANCELLATO** (Step E4) | Non deprecato a tempo indeterminato — rimosso dopo migrazione frontend |

---

## Relazione con Phase 9 (Dashboard)

Il calcolo WAC iterativo (`compute_wac_from_txlist`) è il fondamento per:
- Overlay WAC su price chart (serie temporale)
- P&L computation (realized gains = sell_price - WAC)
- Portfolio analytics (entry price per holding)

L'endpoint `/analytics/wac` (Step E2) sarà consumato dalla dashboard. Vedi nota aggiunta in `phase-09-dashboard.md`.

---

## Dopo il completamento di questo piano — cosa riprendere

1. **Walktest manuale del WAC** — verificare che TRANSFER mostra il WAC del source broker (non più 6.07 ma 160.42)
2. **Fix E2E WB2/WB4/WB5** — hanno problemi infrastrutturali di selezione riga nel main table (non WAC), da risolvere separatamente
3. **Tornare al walktest R2** — riprendere `SP-C-Bugfix` per gli altri bug identificati nel round di walktest
4. **Tradurre docs WAC** — la pagina `.en.md` è stata aggiornata con Auto WAC effect + Example 4; le traduzioni IT/FR/ES vanno fatte con pipeline Aphra (`./dev.py mkdocs translate`)
5. **Phase 9 (Dashboard)** — l'endpoint `/analytics/wac` (Step E2) è il fondamento per l'overlay WAC su price chart

