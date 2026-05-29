# Plan: WAC Inline in Validate/Commit + Analytics Migration

> **✅ STATUS**: COMPLETED — All phases (A+B+C+D+E) done. Analytics endpoint live.

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

#### Step A1: Estendere `cost_basis_mode` Literal ✅ 2026-05-28

> **Note implementazione**: Campo aggiunto a `TXCreateItem`, `TXUpdateItem` e `WACPendingTXItem`.
> Aggiunta **Rule 12** nel model_validator: valida che `cost_basis_mode` != None è compatibile solo con TRANSFER receiver (qty>0) o ADJUSTMENT (qty>0). Se incompatibile → `PydanticCustomError("costBasisModeIncompatible", ...)`.

#### Step A2: Creare `TXBatchWacResult` schema ✅ 2026-05-28

> **⚠️ Fuori pista**: In fase di review utente, eliminato `TXBatchWacResult` — i campi posizionali (operation, index, source_broker_id) aggiunti come Optional direttamente a `WACPreviewResultItem`. Riuso diretto senza wrapper dedicato.

#### Step A3: Estendere `TXBatchResponse` con `wac_results` ✅ 2026-05-28

> **⚠️ Fuori pista**: In fase di review utente, `TXBatchResponse` ora eredita da `BaseBulkResponse[TXBatchResultItem]` (non più BaseModel vanilla). Aggiunto `committed`, `issues`, `wac_results`. `results` è ora sempre una List (non Optional), `success_count` computed.

#### Step A4: Implementare WAC computation in `execute_batch` ✅ 2026-05-28

> **Note implementazione**: Aggiunto `_compute_wac_for_auto_items()`, `_find_created_tx_for_wac()`, e `_resolve_source_broker_from_link()` al TransactionService. Il metodo viene invocato al step 6b (post link resolution, pre balance walk). Condizione: skip se ci sono errori pydantic/access. Usa direttamente `WACPreviewResultItem` con campi posizionali.

#### Step A5: `./dev.py api sync` ✅ 2026-05-28

> **Note implementazione**: Client TypeScript rigenerato 2x (dopo primo design e dopo redesign). Verificato: 28/28 test WAC esistenti passano (P1-P15, WAC1-13). Nessuna regressione.

### Phase B: Backend — Test

#### Step B1: Adattare test WAC esistenti (P12-P15) ✅ 2026-05-28

> **Note implementazione**: I test P1-P15 esistenti passano invariati (28/28). Non serve duplicarli — il vecchio endpoint `/wac-preview` è funzionante e coperto.

#### Step B2: Nuovi test validate+commit con WAC ✅ 2026-05-28

> **Note implementazione**: Creato file separato `test_transactions_wac_inline.py` (non modificato il file originale).
> **13/13 test passano** al primo run: P16-P28 tutti green in 8.71s.

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

#### Step B3: Test regression — endpoint `/wac-preview` ancora funzionante ✅ 2026-05-28

> **Note implementazione**: 28/28 test passano (confermato sia prima che dopo l'aggiunta dei test inline). Endpoint legacy non toccato.

### Phase C: Frontend — BulkModal migration

#### Step C1: Eliminare `fetchBatchWac` e infrastruttura WAC dedicata ✅ 2026-05-29

> **Note implementazione**: Rimossi: `wacFingerprint`, `autoWacItems`, `wacFetchInFlight`, `wacAbortController`, `wacDebounceTimer`, `wacFetchPromise`, `wacFetchResolve`, `fetchBatchWac()`, l'`$effect` WAC. Mantenuto solo `wacResults` state e `WacResultEntry` type.

#### Step C2: Leggere `wac_results` dalla validate response ✅ 2026-05-29

> **Note implementazione**: Aggiunto `buildOpsIndexMap(resolved)` che replica l'ordinamento di `resolveOps+buildBatchPayload` per mappare `"operation:index"` → `tempId`. La validateFn estrae `wac_results` da `rawResponse` e popola la mappa.

#### Step C3: Writeback WAC in ops per il display nelle celle ✅ 2026-05-29

> **Note implementazione**: Dopo il mapping, il valore WAC viene scritto in `ops[x].fields.cost_basis_override` con equality guard (non scrive se code+amount identici) per evitare re-trigger del draftKey.

#### Step C4: Commit senza WAC value — solo mode ✅ 2026-05-29

> **Note implementazione**: Modificato `buildCreatePayload` e `buildUpdateDiff` in `txPayloadHelpers.ts`: per `cost_basis_mode === 'auto'`, il payload manda `cost_basis_mode: "auto"` + `cost_basis_override: null`. Aggiunto `cost_basis_mode` a `TxFields` interface.

#### Step C5: Eliminare pre-commit WAC await ✅ 2026-05-29

> **Note implementazione**: Rimosso il blocco pre-commit (14 righe) che aspettava `wacFetchPromise` e forzava `fetchBatchWac`. Il commit ora manda solo il mode e il backend calcola.

### Phase D: Frontend — FormModal migration

#### Step D1: FormModal manda `cost_basis_mode: "auto-detail"` ✅ 2026-05-29

> **Note implementazione**: `draftToTxFields()` ora include `cost_basis_mode: 'auto'` quando `costBasisMode === 'auto'`. Per il layout `transfer_asset`, `buildDualCreatePayloads` mette `cost_basis_mode: "auto"` + `cost_basis_override: null` sul `toItem` (receiver). Il backend vede mode=auto → calcola WAC inline.

#### Step D2: WacPreviewSection legge da validate response ✅ 2026-05-29

> **Note implementazione**: Aggiunto `formWacResult` state nel FormModal. La `validateFn` estrae `wac_results` dalla response e popola `formWacResult`. Il derived `externalWacResult` usa `formWacResult` come fallback quando `getWacResult` (BulkModal) non è disponibile. WacPreviewSection riceve sempre `externalResult` e skippa il proprio fetch.

#### Step D3: Eliminare chiamata diretta a `/wac-preview` dal FormModal ✅ 2026-05-29

> **Note implementazione**: Completato con D4 (vedi sotto).

#### Step D4: Unificare UX WacPreviewSection (Auto/Manual toggle always) ✅ 2026-05-29

> **Note implementazione**: Il WacPreviewSection è stato riscritto per avere UX identica tra create e edit:
> - Il toggle **Auto | Manual** è ora **sempre visibile** (nascosto solo se `disabled=true`)
> - Il bottone ↺ Recalculate e il pannello Accept/Keep sono stati **rimossi**
> - `variant` controlla solo il mode iniziale (`auto-new` → Auto, `saved` → Manual) ma il toggle funziona in entrambi
> - Rimossi completamente: `fetchWacPreview()`, `handleRecalculate()`, `acceptRecalculated()`, `dismissRecalc()`, `recalcResult` state, import `zodiosApi`, import `RefreshCw`
> - Il componente non chiama più `/wac-preview` in nessun caso — **zero dipendenze dirette da endpoint WAC**
> - Il WAC arriva SOLO via `externalResult` prop (validate response o BulkModal)
> - Quando l'utente switcha da Manual→Auto su TX salvata, il WAC viene applicato dalla validate response (che il FormModal ha già)
>
> **Impatto su Phase E**: Step E4 può ora rimuovere `/wac-preview` senza preoccupazioni frontend — nessun caller rimasto.

### Phase E: Cleanup + Analytics Migration

> **Nota post-D4**: Il frontend non chiama più `/wac-preview` in nessun caso. La Phase E può procedere direttamente alla rimozione dell'endpoint senza rischi frontend. Lo step E1 (deprecare) è opzionale — si può saltare direttamente a E4.

#### Step E1: ~~Deprecare `/transactions/wac-preview`~~ → SKIP

Non più necessario: il frontend ha zero caller. Si procede direttamente con E3+E4.

#### Step E2: Creare router `/api/v1/analytics/` ✅ 2026-05-29

> **Note implementazione**: Creati `schemas/analytics.py` (WACAnalyticsQuery con OpenDateRangeModel, WACAnalyticsRequest, WACSeriesPoint, WACAnalyticsResultItem, WACAnalyticsResponse) e `api/v1/analytics.py` (POST /analytics/wac). L'endpoint riusa `compute_wac_iterative` e costruisce la serie da `qualifying_txs` con `running_wac`. Registrato `analytics_router` in `router.py`. 8/8 test passed (A1-A8 in `test_analytics_wac.py`). `./dev.py api sync` + `front check` → 0 errors.

#### Step E3: Aggiornare E2E tests ✅ 2026-05-29

> **Note implementazione**: Rimossi intercept `/wac-preview` da WB5 e contatore request da WB6. WB5 ora verifica solo che `[data-testid="tx-bulk-cost-basis-auto"]` diventa visibile dopo clone. WB6 mantiene solo la verifica valore stabile (value2 === value1) dopo 2.5s, senza contare network request.

**File**: `frontend/e2e/transactions/tx-wac-bulk.spec.ts`

Test da aggiornare (gli altri sono OK — usano solo data-testid invariati):

| Test | Problema | Fix |
|------|----------|-----|
| **WB5** (riga 366) | `waitForResponse('/wac-preview')` → timeout perché il frontend non chiama più quell'endpoint | Rimuovere l'intercept; verificare solo che `tx-bulk-cost-basis-auto` appare dopo che la validate ha risposto (aspettare la cella auto visibile, non la network request) |
| **WB6** (riga 440) | Conta request a `/wac-preview` per verificare no feedback loop | Rimuovere il contatore; il feedback loop non è più possibile by design (il valore non torna mai al frontend per essere ri-mandato). Verificare solo che il valore nella cella è stabile dopo 2.5s (la parte `value2 === value1` resta valida). Anche `waitForWacResolved` va verificato — se usa intercept a `/wac-preview` internamente, va cambiato per aspettare la cella auto. |

**Test invariati** (nessuna modifica necessaria):
- `tx-wac.spec.ts` (W8, W9, W10, W-manual, W-sell, W-excluded) — usano solo testid del toggle/input
- `tx-wac-bulk.spec.ts` WB1, WB2, WB3, WB4 — non intercettano `/wac-preview`
- `tx-commit-all-types.spec.ts` — usa solo il campo input
- La gallery è esclusa dai test (non testa WAC)

#### Step E4: Rimuovere `/transactions/wac-preview` + cleanup `pending_txs` ✅ 2026-05-29

> **Note implementazione**: Rimosso endpoint `wac_preview` da `transactions.py`, parametro `pending_txs` da `compute_wac_iterative`, schemi `WACPendingTXItem`/`WACPreviewItem`/`WACPreviewRequest`/`WACPreviewResponse` da `schemas/transactions.py`, e test file `test_transactions_wac.py` (P1-P15). `./dev.py api sync` rigenerato client senza il metodo. 13/13 test inline passed. `./dev.py front check` → 0 errors.

**File da modificare**:
- `backend/app/api/v1/transactions.py` — eliminare endpoint e route
- `backend/app/services/transaction_service.py` — rimuovere parametro `pending_txs` da `compute_wac_iterative`
- `backend/app/schemas/transactions.py` — rimuovere `WACPendingTXItem`, `WACPreviewItem`, `WACPreviewRequest`, `WACPreviewResponse`
- `backend/test_scripts/test_api/test_transactions_wac.py` — rimuovere test P1-P15 (coprono l'endpoint eliminato)
- `frontend/src/lib/api/generated.ts` — `./dev.py api sync` rimuoverà il client method automaticamente

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

#### Step E5: Split WAC in file dedicati ✅ 2026-05-29

> **Note implementazione**: Creati `schemas/wac.py` (94 righe: WACConversionInfo, WACResult, WACQualifyingTX, WACPreviewResultItem) e `services/wac_service.py` (347 righe: compute_weighted_avg_cost, compute_wac_iterative). `schemas/transactions.py` re-esporta i simboli WAC per backward compat. `financial_utils.py` importa da `schemas/wac.py`. Rinominato test → `test_wac_inline.py`. 13/13 test passed. `./dev.py api sync` + `front check` → 0 errors. Riduzione: transactions.py -133 righe, transaction_service.py -321 righe.

Dopo la cleanup di E4, riorganizzare il codice WAC in moduli separati:

| Sorgente | Destinazione | Contenuto |
|----------|-------------|-----------|
| `schemas/transactions.py` | `schemas/wac.py` | `WACResult`, `WACConversionInfo`, `WACQualifyingTX`, `WACPreviewResultItem` (con campi batch-context) |
| `services/transaction_service.py` | `services/wac_service.py` | `compute_weighted_avg_cost()`, `compute_wac_iterative()`, logica auto-items (estratta come funzione standalone) |
| `api/v1/transactions.py` | `api/v1/analytics.py` | Endpoint `/analytics/wac` (già creato in E2) |
| `test_api/test_transactions_wac.py` | `test_api/test_wac_inline.py` | Rinominare `test_transactions_wac_inline.py` → `test_wac_inline.py` (WAC ha ora il suo dominio) |

**Motivazione**: `transactions.py` (schemas) è 1500+ righe; `transaction_service.py` è 1760+ righe. Lo split riduce la complessità per file e rende il dominio WAC autonomo.
**Nota**: richiede `./dev.py api sync` dopo lo spostamento + verifica 13/13 test `test_wac_inline.py`.

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

- [x] Backend P16-P28: validate/commit con WAC inline (13 nuovi test) — **13/13 passed 2026-05-28**
- [x] Backend P1-P15: regression (wac-preview ancora funzionante) — **28/28 passed 2026-05-28**
- [x] Frontend: BulkModal mostra WAC nelle celle senza chiamata a /wac-preview — **Phase C completata 2026-05-29**
- [x] Frontend: FormModal mostra qualifying table dai dati validate — **Phase D completata 2026-05-29**
- [x] Frontend: Commit funziona con cbo=null + mode=auto (backend applica) — **Phase C4 2026-05-29**
- [x] E2E: WB5 e WB6 adattati al nuovo flusso (WB1-WB4, WB7 invariati) — **2026-05-29**
- [x] `./dev.py front check` — 0 errors — **2026-05-29**
- [x] `./dev.py api sync` eseguito — **2026-05-28**

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

## Deviazioni dal piano originale (applicate in fase di review 2026-05-28)

| Tema | Piano originale | Decisione implementata | Motivazione |
|------|----------------|----------------------|-------------|
| `TXBatchWacResult` | Classe wrapper dedicata con campi flat | **ELIMINATA** — campi posizionali (operation, index, source_broker_id) come Optional in `WACPreviewResultItem` | Evita duplicazione; riuso diretto della classe esistente |
| `TXBatchResponse` base class | `BaseModel` vanilla | **`BaseBulkResponse[TXBatchResultItem]`** | Coerenza con pattern progetto; `results` sempre lista (non Optional), `success_count` computed |
| `cost_basis_mode` validazione | Frontend-driven (None se tipo non compatibile) | **Rule 12 in model_validator** di TXCreateItem: errore pydantic se tipo incompatibile | La validazione bulk già cattura errori; il backend enforca le regole, non si fida del frontend |

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

