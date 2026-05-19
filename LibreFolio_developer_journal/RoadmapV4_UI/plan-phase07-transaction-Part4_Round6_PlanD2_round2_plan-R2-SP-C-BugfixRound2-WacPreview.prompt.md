# Plan: SP-C BugfixRound2 — WAC Preview Architecture (v5 FINAL)

**Parent plan**: [`plan-R2-SP-C-BugfixRound1`](plan-phase07-transaction-Part4_Round6_PlanD2_round2_plan-R2-SP-C-BugfixRound1.prompt.md)
**Depends on**: BugfixRound1 completato (12/12)
**Triggered by**: Walktest C9 — scoperte feature mancanti → ripensamento architetturale WAC

---

## 📋 Background: osservazioni dal walktest

Durante il walktest finale di BugfixRound1, è emerso che alcune feature pianificate in piani precedenti (SP-A, bugfix_4) non erano mai state implementate lato frontend o coperte da E2E test. Le osservazioni originali:

1. **L'endpoint `POST /recalc-wac` esiste ma nessun bottone UI lo triggera** (source: `plan-R2-SP-A-CostBasisWAC.prompt.md` Step 6)
2. **E2E W8**: nessun test verifica che TRANSFER con override manuale salva SOLO sul ricevente (source: `bugfix_4_SplitSuggestPmcOverrideUx.prompt.md`)
3. **E2E W9**: nessun test verifica che TRANSFER senza override → auto-calc WAC sul ricevente (source: ibid.)
4. **E2E W10**: il Tooltip `<Tooltip>` con testo i18n è stato aggiunto ma manca link alla docs (source: ibid.)
5. **`asset_event_id`**: è un `<input type="number">` grezzo → dovrebbe essere un dropdown/autocomplete filtrato (low priority, spostato in PlanD D2-round2)

**Evoluzione**: durante la pianificazione di questi item, è emerso che il flusso WAC andava ripensato completamente — da "auto-calc nascosto al commit" a "preview esplicito nel form con toggle Auto/Manual". Questo piano è il risultato di quel ripensamento architetturale.

---

## 🎯 Obiettivo

Sostituire l'auto-calc nascosto al commit con un sistema di **preview esplicito**. Nuovo endpoint bulk `wac-preview` con calcolo inventory-aware (SELL/TRANSFER_OUT/ADJUSTMENT- riducono il residuo). Il FormModal mostra il valore suggerito (ricalcolato live usando un toggle Auto/Manual). Il commit è "dumb" — salva esattamente ciò che il form manda. Il vecchio `recalc-wac` viene eliminato.

---

## Decisioni architetturali

| Decisione | Scelta |
|-----------|--------|
| Auto-calc al commit | ❌ Rimosso (opzione A) |
| Preview nel FormModal | ✅ Live, con toggle Auto/Manual |
| Input pendenti dal bulk | ✅ Frontend manda pending TXs + excluded_tx_ids |
| Conflitto ID pending vs DB | Pending vince (override) |
| TX cancellate nel workspace | `excluded_tx_ids` nel request |
| Utente digita con Auto ON | Toggle si spegne → Manual |
| Toggle Auto riattivato | Re-trigger calcolo |
| PromoteMergeModal per TRANSFER | ✅ Sempre aperta, con preview cost_basis |
| Vecchio `POST /recalc-wac` | Eliminato — il nuovo endpoint copre tutto |
| SELL/TRANSFER_OUT/ADJUSTMENT- | ✅ Riducono il pool (WAC invariato, qty ridotta) |

---

## Formula WAC Inventory-Aware (PMC)

### Principio

Le quantità sono **già signed** nel DB (+BUY, -SELL, +TRANSFER_IN, -TRANSFER_OUT, ±ADJUSTMENT). La formula è iterativa e unificata.

### Transazioni che modificano il pool

| Operazione | Effetto | Condizione |
|-----------|---------|------------|
| BUY | ➕ Aggiunge qty al costo `abs(amount)/qty` | `type=BUY, qty>0` |
| TRANSFER_IN (con override) | ➕ Aggiunge qty al costo `cost_basis_override` | `type=TRANSFER, qty>0, override≠null` |
| TRANSFER_IN (senza override) | ➕ Aggiunge qty a costo **0** (segnalato) | `type=TRANSFER, qty>0, override=null` |
| ADJUSTMENT+ (con override) | ➕ Aggiunge qty al costo `cost_basis_override` | `type=ADJUSTMENT, qty>0, override≠null` |
| ADJUSTMENT+ (senza override) | ➕ Aggiunge qty a costo **0** (segnalato) | `type=ADJUSTMENT, qty>0, override=null` |
| SELL | ➖ Rimuove qty al WAC corrente | `type=SELL` |
| TRANSFER_OUT | ➖ Rimuove qty al WAC corrente | `type=TRANSFER, qty<0` |
| ADJUSTMENT- | ➖ Rimuove qty al WAC corrente | `type=ADJUSTMENT, qty<0` |

### Algoritmo (pseudo-codice)

```
Input:
  TXs = tutte le TX di (broker_id, asset_id) con date ≤ as_of_date
         dove quantity ≠ 0 e quantity ≠ null
         Ordinate per (date ASC, id ASC)
  
  Merge: pending_txs sovrascrivono (se id match) o si aggiungono (se id=null)
  Exclude: excluded_tx_ids vengono rimosse dal set

State:
  wac = Decimal(0)    # WAC per unità corrente
  qty = Decimal(0)    # quantità in portafoglio corrente

Per ogni TX in ordine cronologico:

  tx_qty = TX.quantity                     # già signed
  tx_cost = costo_unitario(TX, wac)        # vedi tabella sotto

  new_qty = qty + tx_qty
  
  if new_qty > 0:
    wac = ((wac * qty) + (tx_cost * tx_qty)) / new_qty
  elif new_qty == 0:
    wac = Decimal(0)                       # portafoglio svuotato
  # new_qty < 0: impossibile (balance validation lo impedisce)
  
  qty = new_qty

Risultato:
  WAC = wac (per unità, in target_currency)
```

### Funzione `costo_unitario(TX, wac_corrente)`

| Caso | `tx_cost` (per unità) |
|------|----------------------|
| BUY (qty > 0) | `abs(TX.amount) / TX.quantity` convertito in target_currency |
| TRANSFER_IN con override | `TX.cost_basis_override` convertito in target_currency |
| ADJUSTMENT+ con override | `TX.cost_basis_override` convertito in target_currency |
| TRANSFER_IN senza override | `Decimal(0)` |
| ADJUSTMENT+ senza override | `Decimal(0)` |
| Qualsiasi riduzione (qty < 0) | `wac_corrente` (formula immutata automaticamente) |

### Dimostrazione: riduzioni non cambiano WAC

```
Per una riduzione: tx_cost = wac, tx_qty < 0
new_wac = ((wac × qty) + (wac × tx_qty)) / (qty + tx_qty)
        = wac × (qty + tx_qty) / (qty + tx_qty)
        = wac  ← immutato
```

Solo `qty` si riduce. Questo è il comportamento PMC italiano corretto.

### Determinazione `target_currency`

1. Contare le valute tra tutte le TX di tipo ACQUISTO nel set
2. La più frequente vince
3. A parità: se `asset.currency` è tra le pari → usa quella
4. Altrimenti: prima in ordine alfabetico

---

## Schema (riuso da `common.py`)

```python
# In backend/app/schemas/transactions.py

class WACPreviewItem(BaseModel):
    """Single WAC preview request."""
    model_config = ConfigDict(extra="forbid")
    sender_broker_id: int
    asset_id: int
    as_of_date: date

class WACPendingTX(BaseModel):
    """A pending TX from workspace (overrides DB row if id matches)."""
    model_config = ConfigDict(extra="forbid")
    id: Optional[int] = None
    broker_id: int
    asset_id: int
    type: str
    date: date
    quantity: SafeDecimal
    amount: Optional[SafeDecimal] = None
    currency: Optional[str] = None
    cost_basis_override: Optional[Currency] = None

class WACPreviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    items: List[WACPreviewItem] = Field(..., min_length=1, max_length=50)
    pending_txs: List[WACPendingTX] = Field(default_factory=list, max_length=500)
    excluded_tx_ids: List[int] = Field(default_factory=list, max_length=500)

class WACQualifyingTX(BaseModel):
    """A TX that participated in WAC calculation."""
    model_config = ConfigDict(extra="forbid")
    tx_id: Optional[int] = None          # None if pending without id
    type: str
    date: date
    quantity: SafeDecimal
    unit_cost: Optional[SafeDecimal] = None
    currency: Optional[str] = None
    effect: str                          # "add" | "reduce" | "add_zero_cost" | "skip_no_override"
    fx_info: Optional[FxBackwardFillInfo] = None  # riuso da common.py

class WACPreviewResultItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    # WAC inventory-aware
    wac: Optional[Currency] = None                 # riuso Currency
    wac_qualifying_txs: List[WACQualifyingTX] = Field(default_factory=list)
    wac_missing_pairs: List[str] = Field(default_factory=list)
    # Asset price at date (per ADJUSTMENT scenario)
    asset_price: Optional[Currency] = None         # riuso Currency
    asset_price_stale: Optional[BackwardFillInfo] = None  # riuso da common.py
    asset_price_missing: bool = False

class WACPreviewResponse(BaseListResponse[WACPreviewResultItem]):
    """Response for POST /transactions/wac-preview."""
    pass  # Inherits: items: List[WACPreviewResultItem]
```

---

## Scenari d'uso — Completi con input e regole

### Scenario A: FormModal — Nuova TRANSFER (dual form)

**Condizione**: `isNew === true` AND `type === TRANSFER` AND toggle Auto

**Trigger ricalcolo** (debounce trailing 500ms, leading=true):
- Cambio sender_broker (pannello "From")
- Cambio asset_id
- Cambio date
- Modifica di un'altra riga nel workspace che impatta (same sender_broker + same asset + date ≤)
- Toggle Auto ri-attivato

**Input**:
```json
{
  "items": [{"sender_broker_id": 3, "asset_id": 7, "as_of_date": "2026-05-10"}],
  "pending_txs": [/* righe workspace same broker/asset con date ≤, esclusa se stessa */],
  "excluded_tx_ids": [/* IDs di TX DB cancellate nel workspace */]
}
```

**UI**:
```
│  Cost basis (per unit):              [Auto ◉ / Manual ○]    │
│  ┌───────────────────────────────┐                          │
│  │  175.57            │ USD ▾│   │  ← GRAY ITALIC          │
│  └───────────────────────────────┘                          │
│  💡 Suggested WAC from IB (3 purchases, 1 sale)             │
│     [▶ Show transactions used]                               │
```

Se l'utente digita → toggle → Manual (nero, stop ricalcolo).
Se l'utente riclicca Auto → gray italic, re-trigger.

---

### Scenario A' (FX mancante):

```
│  Cost basis (per unit):              [Auto ◉ / Manual ○]    │
│  ┌───────────────────────────────┐                          │
│  │                    │     ▾│   │  ← EMPTY, red border    │
│  └───────────────────────────────┘                          │
│  ⚠️ Cannot calculate WAC: missing FX rate                   │
│     CHF/EUR on 2026-05-10                                   │
│  • [Add FX pair CHF/EUR →]                                  │
│  • [Sync FX rates]                                          │
│  • [Sync asset prices]                                      │
│  • Enter value manually (switch to Manual)                  │
```

---

### Scenario A'' (Manual mode):

```
│  Cost basis (per unit):              [Auto ○ / Manual ◉]    │
│  ┌───────────────────────────────┐                          │
│  │  42.50             │ EUR ▾│   │  ← BLACK                │
│  └───────────────────────────────┘                          │
```

---

### Scenario A''' (Expanded qualifying TXs):

```
│  💡 Suggested WAC from IB (3 purchases, 1 sale)             │
│     [▼ Hide transactions used]                               │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  #  │ Type     │ Date       │ Qty  │ Unit  │ Effect │   │
│  │─────┼──────────┼────────────┼──────┼───────┼────────│   │
│  │ 12  │ BUY      │ 2026-04-12 │ +15  │$175.57│  add   │   │
│  │ 18  │ BUY      │ 2026-04-20 │ +5   │$180.00│  add   │   │
│  │ 23  │ SELL     │ 2026-04-28 │ -3   │$176.68│ reduce │   │
│  │ ●   │ BUY (*)  │ 2026-05-08 │ +10  │$150.00│  add   │   │
│  │     │          │            │      │       │        │   │
│  │  (*) = pending in workspace                          │   │
│  └──────────────────────────────────────────────────────┘   │
```

---

### Scenario B: FormModal — Edit TRANSFER esistente (receiver)

**Condizione**: `isNew === false` AND `type === TRANSFER` AND `qty > 0`

**Comportamento**: valore salvato mostrato normalmente (nero). Toggle non presente. Ricalcolo solo on-demand.

**UI**:
```
│  Cost basis (per unit):                                     │
│  ┌───────────────────────────────┐                          │
│  │  175.57            │ USD ▾│   │  ← BLACK (saved)        │
│  └───────────────────────────────┘  [↺ Recalculate]        │
```

Dopo click [↺ Recalculate]:
```
│  ┌───────────────────────────────┐                          │
│  │  175.57            │ USD ▾│   │  ← BLACK (current)      │
│  └───────────────────────────────┘                          │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  📊 Recalculated: 182.30 USD  (was: 175.57 USD)     │   │
│  │     [Accept 182.30]    [Keep current]                 │   │
│  │     [▶ Show transactions used (4)]                    │   │
│  └──────────────────────────────────────────────────────┘   │
```

**Input** (on-demand): `sender_broker_id` = partner TX broker (da `related_transaction_id`).

---

### Scenario C: BulkModal — Celle cost_basis

**Righe nuove in Auto** (toggle Auto attivo):
```
│ new  │ TRANSFER │ DEG←IB │ AAPL │ +5 📈 │ 175.57 💡 │  ← gray italic + 💡
│      │(receiver)│        │      │       │   auto    │
```

**Righe da DB** (valore salvato):
```
│ #42  │ TRANSFER │ DEG←CB │ BTC  │+0.1📈 │ 45200.00  │  ← nero, niente altro
│      │(receiver)│        │      │       │           │
```

**Righe nuove in Manual** (utente ha digitato):
```
│ new  │ TRANSFER │ DEG←IB │ AAPL │ +5 📈 │ 42.50     │  ← nero, niente altro
│      │(receiver)│        │      │       │           │
```

- Bottone [↺] visibile per righe DB (on-hover o menu azioni)
- Bulk call: una sola `POST /wac-preview` per tutti gli items in auto
- Re-trigger quando una qualsiasi riga BUY/SELL/TRANSFER dello stesso (broker, asset) cambia

---

### Scenario D: PromoteMergeModal — Receiver NUOVA

**Condizione**: promote crea TRANSFER e il receiver non esiste in DB (è new)

**UI**:
```
┌─────────────────────────────────────────────────────────────────────┐
│  🔗 Promote to TRANSFER                                       [X]  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─── FROM (sender) ──────────┐  ┌─── TO (receiver) ─────────┐    │
│  │ Broker: Interactive Brokers │  │ Broker: DEGIRO             │    │
│  │ Asset:  AAPL                │  │ Asset:  AAPL               │    │
│  │ Qty:    -5                  │  │ Qty:    +5                 │    │
│  │ Date:   2026-05-10         │  │ Date:   2026-05-10         │    │
│  └────────────────────────────┘  └────────────────────────────┘    │
│                                                                     │
│  ── Merged Fields ───────────────────────────────────────────────   │
│  Description: [Transfer AAPL IB → DEGIRO                       ]    │
│  Tags:        [rebalance] [x]  [+]                                  │
│                                                                     │
│  ── Cost Basis (receiver) ────────── [Auto ◉ / Manual ○] ───────   │
│  ┌───────────────────────────────┐                                  │
│  │  175.57            │ USD ▾│   │  ← GRAY ITALIC (auto)           │
│  └───────────────────────────────┘                                  │
│  💡 Suggested WAC from Interactive Brokers                           │
│     (3 purchases, 1 sale — 27 units pool)                           │
│     [▶ Show transactions used]                                      │
│                                                                     │
├─────────────────────────────────────────────────────────────────────┤
│                           [Cancel]    [Confirm Promote]              │
└─────────────────────────────────────────────────────────────────────┘
```

---

### Scenario D'/F: PromoteMergeModal — Receiver DA DB

**Condizione**: promote dove il receiver è una TX DB con `cost_basis_override` già salvato.

**UI**: mostra valore salvato nero + bottone [↺ Recalculate]:
```
│  ── Cost Basis (receiver) ───────────────────────────────────────   │
│  ┌───────────────────────────────┐                                  │
│  │  170.00            │ USD ▾│   │  ← BLACK (saved)                │
│  └───────────────────────────────┘  [↺ Recalculate]                │
│                                                                     │

--- Dopo click [↺ Recalculate]: ---

│  ┌───────────────────────────────┐                                  │
│  │  170.00            │ USD ▾│   │  ← BLACK (current)              │
│  └───────────────────────────────┘                                  │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  📊 Recalculated: 175.57 USD  (was: 170.00 USD)             │   │
│  │     [Accept 175.57]    [Keep 170.00]                         │   │
│  │     [▶ Show transactions used (4)]                           │   │
│  └──────────────────────────────────────────────────────────────┘   │
```

---

### Scenario E: FormModal — Nuova ADJUSTMENT (qty > 0)

**Condizione**: `isNew === true` AND `type === ADJUSTMENT` AND `qty > 0`

**Logica diversa**: non c'è sender broker noto. Il suggerimento "auto" è il **prezzo dell'asset alla data** (non il WAC del broker). Il WAC del broker viene comunque mostrato come opzione secondaria.

**UI**:
```
┌─────────────────────────────────────────────────────────────────────┐
│  ✏️ New Transaction                                            [X]  │
├─────────────────────────────────────────────────────────────────────┤
│  Type:    [ADJUSTMENT ▾]                                            │
│  Broker:  [Interactive Brokers ▾]                                   │
│  Asset:   [Apple Inc. (AAPL) ▾]                                     │
│  Date:    [2026-05-10]                                              │
│  Qty:     [5]  (+)                                                  │
│                                                                     │
│  ▶ Advanced                                                         │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                                                             │    │
│  │  Cost basis (per unit):              [Auto ◉ / Manual ○]    │    │
│  │  ┌───────────────────────────────┐                          │    │
│  │  │  192.30            │ USD ▾│   │  ← GRAY ITALIC (auto)   │    │
│  │  └───────────────────────────────┘                          │    │
│  │                                                             │    │
│  │  💡 Suggestions:                                            │    │
│  │  ┌──────────────────────────────────────────────────────┐   │    │
│  │  │  📈 Asset price on 2026-05-10: 192.30 USD  ← USED   │   │    │
│  │  │     (1 day stale — data from 2026-05-09)             │   │    │
│  │  │                                                       │   │    │
│  │  │  📊 Current WAC on this broker: 175.57 USD            │   │    │
│  │  │     [Use 175.57 instead]                              │   │    │
│  │  │                                                       │   │    │
│  │  │  ℹ️ For gifts/inheritance: use the value at which     │   │    │
│  │  │     the giver originally acquired the asset.          │   │    │
│  │  │     Consult local fiscal rules.                       │   │    │
│  │  └──────────────────────────────────────────────────────┘   │    │
│  │                                                             │    │
│  │  ⚠️ No cost basis set — lot will be created with           │    │
│  │     zero cost if left empty.                                │    │
│  │                                                             │    │
│  └─────────────────────────────────────────────────────────────┘    │
├─────────────────────────────────────────────────────────────────────┤
│                                [Cancel]    [Add to workspace]        │
└─────────────────────────────────────────────────────────────────────┘
```

Se asset price mancante:
```
│  │  📈 Asset price on 2026-05-10: ⚠️ NOT AVAILABLE            │
│  │     No price data for this asset on this date               │
│  │     [Sync asset prices]                                     │
```

Se FX mancante per entrambi:
```
│  │  📈 Asset price: ⚠️ Missing FX CHF/USD                     │
│  │     [Add FX pair →]  [Sync FX rates]                        │
│  │  📊 WAC: ⚠️ Missing FX CHF/EUR                              │
│  │     [Add FX pair →]  [Sync FX rates]                        │
│  │  [Sync asset prices]                                        │
```

---

## Riepilogo: regole Auto/Manual per scenario

| # | Scenario | Toggle visibile? | Default | Auto = ? |
|---|---------|-----------------|---------|----------|
| A | Form: new TRANSFER | ✅ Sì | Auto ON | WAC dal sender broker |
| B | Form: edit TRANSFER | ❌ No (solo [↺]) | — (saved) | [↺] ricalcola on-demand |
| C | Bulk: new TRANSFER row | ✅ Sì (nella cella) | Auto ON | WAC dal sender broker |
| C' | Bulk: DB TRANSFER row | ❌ No (solo [↺]) | — (saved) | [↺] ricalcola on-demand |
| D | Promote: receiver new | ✅ Sì | Auto ON | WAC dal sender broker |
| D'/F | Promote: receiver DB | ❌ No (solo [↺]) | — (saved) | [↺] ricalcola on-demand |
| E | Form: new ADJUSTMENT+ | ✅ Sì | Auto ON | Asset price alla data |

---

## Steps implementativi (lineari)

### Step 1: Backend — `compute_wac_iterative()` (nuova funzione)

**File**: `backend/app/services/transaction_service.py`

- Formula iterativa con pending merge + excluded_tx_ids
- FX-aware (convert_bulk per valute diverse)
- Ritorna `WACPreviewResultItem` (wac + qualifying_txs + missing_pairs)

### Step 2: Backend — `asset_price_at_date()` (nuova funzione)

**File**: `backend/app/services/asset_source.py` (o nuovo helper)

- Query `PriceHistory` per (asset_id, date) con backward-fill
- Convert in target currency se necessario (FX)
- Ritorna `Currency` + `BackwardFillInfo`

### Step 3: Backend — Endpoint `POST /transactions/wac-preview`

**File**: `backend/app/api/v1/transactions.py`
**File**: `backend/app/schemas/transactions.py`

- Bulk: processa `items[]`, per ognuno chiama `compute_wac_iterative()` + `asset_price_at_date()`
- Response: `WACPreviewResponse` (extends `BaseListResponse`)
- Dopo: `./dev.py api sync`

### Step 4: Backend — Rimuovere auto-calc al commit

**File**: `backend/app/services/transaction_service.py`
- Rimuovere auto-calc in promote Step 5c (linee ~1459-1478)
- Rimuovere auto-calc in link resolution Step 6b (linee ~1529-1544)
- Rimuovere `wac_info` da `TXBatchResultItem`

### Step 5: Backend — Eliminare `POST /recalc-wac`

**File**: `backend/app/api/v1/transactions.py`
- Rimuovere endpoint + schema `RecalcWACRequest/Response/ResponseItem`
- Dopo: `./dev.py api sync`

### Step 6: Backend — Adattare test `test_transactions_wac.py`

- WAC-6/7/8 (testano vecchio recalc-wac) → convertire a test del nuovo `wac-preview`
- WAC-1-5 (testano auto-calc al commit) → verificare che commit NON auto-calcola
- Aggiungere test per: formula iterativa, pending merge, excluded_tx_ids, FX errors

### Step 7: Frontend — State machine WAC nel FormModal

**File**: `frontend/src/lib/components/transactions/TransactionFormModal.svelte`

- Toggle Auto/Manual (visibile solo per new TX)
- `$effect` con debounce 500ms trailing, leading=true, AbortController
- Per TRANSFER: chiama wac-preview con sender_broker
- Per ADJUSTMENT+: chiama wac-preview per asset_price + WAC broker
- Rendering: gray italic (auto), black (manual/saved), red border (error)
- [↺ Recalculate] per edit mode (on-demand)
- Sezione espandibile "Show transactions used" con qualifying_txs

### Step 8: Frontend — WAC preview nella BulkModal

**File**: `frontend/src/lib/components/transactions/TransactionBulkModal.svelte`

- Celle: gray italic + 💡 per righe new in auto; nero per DB/manual
- Bulk call: una sola POST per tutti gli items auto
- Re-trigger quando righe rilevanti cambiano
- [↺] per righe DB (on-hover)

### Step 9: Frontend — PromoteMergeModal con cost_basis

**File**: `frontend/src/lib/components/transactions/TransactionActionModal.svelte`

- Quando target = TRANSFER → modale SEMPRE aperta
- Sezione "Cost Basis (receiver)" con toggle Auto/Manual (se new) o [↺] (se DB)
- Qualifying TXs espandibile
- Error state per FX mancanti con opzioni

### Step 10: Frontend — Error handling (FX/Asset mancanti)

- Warning inline con azioni:
  - [Add FX pair →] → naviga a pagina FX
  - [Sync FX rates] → trigger sync FX
  - [Sync asset prices] → trigger asset refresh
- Shared tra FormModal, BulkModal, PromoteMergeModal (componente riusabile?)

### Step 11: i18n + test runner

- i18n (4 lingue): `transactions.wacPreview.*` (toggle, suggested, calculating, failed, missingPairs, qualifyingTxs, assetPrice, stale, recalculated, accept, keep, noPurchases, fromBroker, adjustmentHint)
- Aggiornare `costBasisOverride.tooltip` con HTML link docs
- Registrare `tx-wac` in `scripts/test_runner/_frontend_transaction.py`

### Step 12: E2E tests

**File**: `frontend/e2e/transactions/tx-wac.spec.ts` (nuovo)

| Test | Cosa verifica |
|------|--------------|
| W8 | TRANSFER con override manuale (toggle Manual) → valore esplicito salvato sul ricevente, sender = null |
| W9 | TRANSFER senza override (toggle Auto) → preview mostrato in corsivo → commit → valore ≈ 175.57 (±0.01) |
| W10 | Tooltip info visibile + contiene link docs |
| W-live | Aggiungi BUY nella bulk → il preview WAC nella riga TRANSFER si aggiorna |
| W-manual | Digita → toggle diventa Manual → [Auto] riporta l'auto |
| W-sell | SELL intermedia → WAC inventory diverso da cumulativo (valore corretto con riduzioni) |
| W-excluded | Cancella una TX nel workspace → WAC ricalcolato senza di essa |

---

## Execution Checklist

- [ ] Step 1: `compute_wac_iterative()`
- [ ] Step 2: `asset_price_at_date()`
- [ ] Step 3: Endpoint `wac-preview`
- [ ] Step 4: Rimuovere auto-calc al commit
- [ ] Step 5: Eliminare `recalc-wac`
- [ ] Step 6: Adattare backend tests
- [ ] Step 7: FormModal WAC state machine
- [ ] Step 8: BulkModal celle WAC
- [ ] Step 9: PromoteMergeModal cost_basis
- [ ] Step 10: Error handling componente
- [ ] Step 11: i18n + test runner
- [ ] Step 12: E2E tests

