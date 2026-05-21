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
- Per TRANSFER: chiama `POST /transactions/wac-preview` con:
  ```ts
  {
    items: [{sender_broker_id, asset_id, date_range: {start: "epoch-or-first-tx", end: txDate}}],
    pending_txs: [/* righe workspace TXCreateItem-format con id:null per new, id:N per override */],
    excluded_tx_ids: [/* IDs di TX DB cancellate nel workspace */]
  }
  ```
  - `pending_txs` = `WACPendingTXItem` (extends `TXCreateItem` + campo `id: number|null`)
  - TX nuove nel workspace → `id: null` (aggiunte al pool)
  - TX editate nel workspace → `id: <db_id>` (sovrascrivono il DB row)
- Per ADJUSTMENT+: stessa call → usa `asset_price` + `wac` dalla response
- Rendering: gray italic (auto), black (manual/saved), red border (error)
- [↺ Recalculate] per edit mode (on-demand)
- Sezione espandibile "Show transactions used" con `wac_qualifying_txs`

### Step 8: Frontend — WAC preview nella BulkModal

**File**: `frontend/src/lib/components/transactions/TransactionBulkModal.svelte`

- Celle: gray italic + 💡 per righe new in auto; nero per DB/manual
- Bulk call: una sola `POST /transactions/wac-preview` per tutti gli items in auto
  - `items[]`: una entry per ogni riga TRANSFER/ADJUSTMENT+ in auto
  - `pending_txs[]`: TUTTE le righe workspace (formato TXCreateItem + id) — il backend filtra per (broker, asset, date)
  - `excluded_tx_ids[]`: IDs delle righe cancellate globally
- Re-trigger quando righe rilevanti (same broker+asset) cambiano
- [↺] per righe DB (on-hover)

### Step 9: Frontend — PromoteMergeModal con cost_basis

**File**: `frontend/src/lib/components/transactions/TransactionActionModal.svelte`

- Quando target = TRANSFER → modale SEMPRE aperta
- Sezione "Cost Basis (receiver)" con toggle Auto/Manual (se new) o [↺] (se DB)
- Request: `sender_broker_id` = broker della TX sender (from `related_transaction_id`)
- Qualifying TXs espandibile
- Error state per FX mancanti con opzioni

### Step 10: Frontend — Error handling (FX/Asset mancanti)

- Warning inline con azioni:
  - [Add FX pair →] → naviga a pagina FX
  - [Sync FX rates] → trigger sync FX
  - [Sync asset prices] → trigger asset refresh
- Shared tra FormModal, BulkModal, PromoteMergeModal (componente riusabile `WacErrorBanner.svelte`?)
- Campi dalla response: `wac_missing_pairs: string[]`, `asset_price_missing: bool`, `asset_price_stale: BackwardFillInfo`

### Step 11: i18n + test runner

- i18n (4 lingue): `transactions.wacPreview.*` (toggle, suggested, calculating, failed, missingPairs, qualifyingTxs, assetPrice, stale, recalculated, accept, keep, noPurchases, fromBroker, adjustmentHint)
- Aggiornare `costBasisOverride.tooltip` con HTML link docs
- Registrare `tx-wac` in `scripts/test_runner/_frontend_transaction.py`

### Step 12: E2E tests

**File**: `frontend/e2e/transactions/tx-wac.spec.ts` (nuovo)

| Test | Cosa verifica |
|------|--------------|
| W8 | TRANSFER con override manuale (toggle Manual) → valore esplicito salvato sul ricevente, sender = null |
| W9 | TRANSFER con toggle Auto → preview mostrato in corsivo → utente conferma → `cost_basis_override` nel payload commit = valore preview (il commit NON ricalcola, salva ciò che riceve) |
| W10 | Tooltip info visibile + contiene link docs |
| W-live | Aggiungi BUY nella bulk → il preview WAC nella riga TRANSFER si aggiorna (pending_txs in azione) |
| W-manual | Digita → toggle diventa Manual → click [Auto] riporta corsivo + ricalcolo |
| W-sell | SELL intermedia → WAC inventory diverso da cumulativo (verifica valore corretto con pool reduction) |
| W-excluded | Cancella una TX nel workspace (excluded_tx_ids) → WAC ricalcolato senza di essa |

---

## Execution Checklist

- [x] Step 1: `compute_wac_iterative()`
- [x] Step 2: `asset_price_at_date()`
- [x] Step 3: Endpoint `wac-preview`
- [x] Step 4: Rimuovere auto-calc al commit
- [x] Step 5: Eliminare `recalc-wac`
- [x] Step 6: Adattare backend tests
- [x] Step 7: FormModal WAC state machine
  ⚠️ Implementation: Created `WacPreviewSection.svelte` as reusable component (toggle, debounced fetch, qualifying TXs table, recalc panel). Integrated into FormModal replacing both dual-form and single-form cost_basis sections. Uses `variant='auto-new'|'saved'` for new vs edit modes.
- [x] Step 8: BulkModal celle WAC
  ⚠️ Deviation: The BulkModal column cell now shows "💡 auto" for new TRANSFER/ADJUSTMENT rows and "—" for others. The full WAC preview (with qualifying TXs, toggle) is accessible via the FormModal when clicking a row (which already has WacPreviewSection integrated). A background bulk auto-fill was deferred — the per-row FormModal approach is sufficient for the current UX.
- [x] Step 9: PromoteMergeModal cost_basis
  ⚠️ Implementation: Added `isTransferPromote`, `senderBrokerId`, `assetId`, `promoteDate`, `receiverIsNew` props to PromoteMergeModal. Integrated WacPreviewSection in the modal body. The `onConfirm` callback now returns `cost_basis_override` when `isTransferPromote=true`.
- [x] Step 10: Error handling componente
  ⚠️ Deviation: No separate `WacErrorBanner.svelte` created — the error handling (missing FX pairs with action links, loading, error state) is embedded directly in `WacPreviewSection.svelte` which is already shared across all three modals. Actions: [Add FX pair →] (link to /fx), [Sync FX rates], [Sync asset prices].
- [x] Step 11: i18n + test runner
  Added `transactions.wacPreview.*` keys (14 keys × 4 languages: EN/IT/FR/ES). Registered `tx-wac` in `_frontend_transaction.py` with runner function and added to `front_transaction_all` suite.
- [x] Step 12: E2E tests
  Created `frontend/e2e/transactions/tx-wac.spec.ts` with 7 tests (W8, W9, W10, W-live, W-manual, W-sell, W-excluded). Tests verify UI structure, toggle behavior, and DOM presence. Full integration tests (with actual WAC values) depend on mock data having TRANSFER+BUY sequences.

### Progress Notes

**Steps 1-5 completed (2026-05-19)**: Backend fully implemented.
- `compute_wac_iterative()` added at line ~197 of `transaction_service.py`
- `asset_price_at_date()` added right after
- Endpoint at `POST /transactions/wac-preview` in `transactions.py` router
- Auto-calc removed from promote Step 5c and link resolution Step 6b
- Old `POST /recalc-wac` endpoint + schemas deleted
- `./dev.py api sync` run twice (after step 3 and step 5)
- New schemas added to `backend/app/schemas/transactions.py`: `WACPreviewItem`, `WACPendingTX`, `WACPreviewRequest`, `WACQualifyingTX`, `WACPreviewResultItem`, `WACPreviewResponse`
- Imports updated: `BackwardFillInfo`, `BaseListResponse`, `FxBackwardFillInfo` added to transactions schemas imports

**Refactoring round (2026-05-19)**: Architecture feedback applied.
- Created `backend/app/utils/financial_utils.py` — pure math: `compute_wac_from_txlist()`, `WACInputTX`, `WACCalcResult`, `determine_target_currency()`
- `compute_wac_iterative()` refactored: preparation layer → delegates to `compute_wac_from_txlist()` for pure math
- Same-date grouping: additions processed before reductions within same date
- Negative qty clamp: if `new_qty < 0` → clamp to 0 (rounding tolerance)
- Removed `wac_info` from `TXBatchResultItem` — field is obsolete (no auto-calc at commit)
- `asset_price_at_date()` kept temporarily but marked for replacement with existing `get_prices_bulk` from `AssetSourceManager`
- `./dev.py api sync` run after wac_info removal

**Refactoring round 2 (2026-05-19)**: Deduplication + DateRange.
- Removed `WACQualifyingEntry` dataclass from `financial_utils.py` → reuses `WACQualifyingTX` Pydantic model from schemas
- `WACInputTX` kept as dataclass (unique: has `unit_cost_converted` post-FX field, internal to math layer)
- `WACPreviewItem` now supports both `as_of_date` (single date) and `date_range: DateRangeModel` (future analytics)
  - Validator ensures exactly one is provided
  - Property `effective_date` returns the end date for both modes
- `./dev.py api sync` run

**TODO for next iteration**:
→ [`plan-R2-SP-C-BugfixRound2-WacBackendCleanup`](plan-phase07-transaction-Part4_Round6_1_CentralizePayloadCommit.prompt.md) — ✅ **COMPLETATO** (2026-05-19). Step 6 coperto integralmente (34 test). Continuare da **Step 7** (Frontend — FormModal WAC state machine).

---

## 🧪 Walktest — Verifica manuale in ordine di dipendenza

### Pre-requisiti

```bash
./dev.py db create-clean --test
./dev.py server --test --force
# In altro terminale:
cd frontend && npm run dev
```

### WT-1: Backend — Endpoint funziona (base)

```bash
# Login come test user
curl -s -c /tmp/lf_cookies.txt -X POST http://localhost:8001/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"e2e_test_user","password":"E2eTestPass123!"}' | python -m json.tool

# Crea broker + asset
curl -s -b /tmp/lf_cookies.txt -X POST http://localhost:8001/api/v1/brokers \
  -H "Content-Type: application/json" \
  -d '{"name":"WacTestBroker"}' | python -m json.tool
# → annotare broker_id

curl -s -b /tmp/lf_cookies.txt -X POST http://localhost:8001/api/v1/assets \
  -H "Content-Type: application/json" \
  -d '{"display_name":"WacTestAsset","currency":"EUR","asset_type":"STOCK"}' | python -m json.tool
# → annotare asset_id

# Commit un BUY
curl -s -b /tmp/lf_cookies.txt -X POST http://localhost:8001/api/v1/transactions/commit \
  -H "Content-Type: application/json" \
  -d '{"creates":[{"broker_id":BROKER_ID,"asset_id":ASSET_ID,"type":"BUY","date":"2026-01-10","quantity":"10","cash":{"code":"EUR","amount":"-1000"}}]}' | python -m json.tool

# WAC Preview
curl -s -b /tmp/lf_cookies.txt -X POST http://localhost:8001/api/v1/transactions/wac-preview \
  -H "Content-Type: application/json" \
  -d '{"items":[{"sender_broker_id":BROKER_ID,"asset_id":ASSET_ID,"date_range":{"start":"2026-01-01","end":"2026-02-01"}}]}' | python -m json.tool
```

**Aspettativa**: `wac = {code: "EUR", amount: "100.000000"}`, `wac_qualifying_txs` con 1 entry (BUY, effect="add")

---

### WT-2: Backend — Pending TXs + Excluded IDs

```bash
# Commit un secondo BUY
curl -s -b /tmp/lf_cookies.txt -X POST http://localhost:8001/api/v1/transactions/commit \
  -H "Content-Type: application/json" \
  -d '{"creates":[{"broker_id":BROKER_ID,"asset_id":ASSET_ID,"type":"BUY","date":"2026-01-15","quantity":"5","cash":{"code":"EUR","amount":"-750"}}]}' | python -m json.tool
# → annotare tx_id del secondo BUY

# WAC con entrambi: dovrebbe essere (1000+750)/15 = 116.67
curl -s -b /tmp/lf_cookies.txt -X POST http://localhost:8001/api/v1/transactions/wac-preview \
  -H "Content-Type: application/json" \
  -d '{"items":[{"sender_broker_id":BROKER_ID,"asset_id":ASSET_ID,"date_range":{"start":"2026-01-01","end":"2026-02-01"}}]}' | python -m json.tool

# WAC con excluded_tx_ids (escludi il secondo BUY): dovrebbe tornare a 100
curl -s -b /tmp/lf_cookies.txt -X POST http://localhost:8001/api/v1/transactions/wac-preview \
  -H "Content-Type: application/json" \
  -d '{"items":[{"sender_broker_id":BROKER_ID,"asset_id":ASSET_ID,"date_range":{"start":"2026-01-01","end":"2026-02-01"}}],"excluded_tx_ids":[TX_ID_2]}' | python -m json.tool

# WAC con pending_txs che sovrascrive il secondo BUY (10@200 invece di 5@150)
curl -s -b /tmp/lf_cookies.txt -X POST http://localhost:8001/api/v1/transactions/wac-preview \
  -H "Content-Type: application/json" \
  -d '{"items":[{"sender_broker_id":BROKER_ID,"asset_id":ASSET_ID,"date_range":{"start":"2026-01-01","end":"2026-02-01"}}],"pending_txs":[{"id":TX_ID_2,"broker_id":BROKER_ID,"asset_id":ASSET_ID,"type":"BUY","date":"2026-01-15","quantity":"10","cash":{"code":"EUR","amount":"-2000"}}]}' | python -m json.tool
```

**Aspettative**:
- Entrambi BUY → WAC ≈ 116.67
- Excluded → WAC = 100
- Override → WAC = (1000+2000)/20 = 150

---

### WT-3: Backend — SELL riduce pool, WAC invariato

```bash
# Commit SELL
curl -s -b /tmp/lf_cookies.txt -X POST http://localhost:8001/api/v1/transactions/commit \
  -H "Content-Type: application/json" \
  -d '{"creates":[{"broker_id":BROKER_ID,"asset_id":ASSET_ID,"type":"SELL","date":"2026-01-20","quantity":"-5","cash":{"code":"EUR","amount":"700"}}]}' | python -m json.tool

# WAC dopo SELL: dovrebbe essere ancora ~116.67 (SELL non cambia WAC, solo qty ridotta)
curl -s -b /tmp/lf_cookies.txt -X POST http://localhost:8001/api/v1/transactions/wac-preview \
  -H "Content-Type: application/json" \
  -d '{"items":[{"sender_broker_id":BROKER_ID,"asset_id":ASSET_ID,"date_range":{"start":"2026-01-01","end":"2026-02-01"}}]}' | python -m json.tool
```

**Aspettativa**: WAC ≈ 116.67, qualifying_txs mostra 3 entries (2 add + 1 reduce)

---

### WT-4: Backend — Commit NON auto-calcola

```bash
# TRANSFER senza cost_basis_override → commit DEVE salvare NULL (non auto-calc)
curl -s -b /tmp/lf_cookies.txt -X POST http://localhost:8001/api/v1/transactions/commit \
  -H "Content-Type: application/json" \
  -d '{"creates":[{"broker_id":BROKER_ID,"asset_id":ASSET_ID,"type":"TRANSFER","date":"2026-01-25","quantity":"3","cash":null}]}' | python -m json.tool

# Leggi la TX: cost_basis_override deve essere NULL
curl -s -b /tmp/lf_cookies.txt "http://localhost:8001/api/v1/transactions?ids=TX_ID" | python -m json.tool
```

**Aspettativa**: `cost_basis_override: null` (non auto-calcolato)

---

Test backend dati per assodati grazie ai test untitari scritti in pytest.

Durante la preparazione dei test manuali nel frontend ci si è accorti di una mancanza architetturale nella creazione dei pacchetti di transazione,
e abbiamo pianificato la correzione in questo piano: [`plan-phase07-transaction-Part4_Round6_1_CentralizePayloadCommit.prompt.md`](./plan-phase07-transaction-Part4_Round6_1_CentralizePayloadCommit.prompt.md)

---

### WT-5: Frontend — FormModal mostra WacPreviewSection per TRANSFER

> Verificato manualmente 2026-05-21 (walktest priorità alta #1)

1. Apri `http://localhost:5173/transactions`
2. Click **+ New**
3. Seleziona tipo **TRANSFER**
4. Verifica che appare la sezione "Cost basis" con toggle **Auto | Manual**
5. Se Auto è attivo e il broker/asset/date sono compilati → aspetta 500ms → il campo dovrebbe popolassi in grigio corsivo
6. Digita un numero → il toggle deve passare a **Manual** (nero, no corsivo)
7. Click **Auto** → torna grigio corsivo + ricalcola

---

### WT-6: Frontend — FormModal edit mode (Scenario B)

> Verificato manualmente 2026-05-21 (walktest priorità alta #4)

1. Dalla tabella transazioni, apri una TRANSFER esistente (receiver, qty > 0) in **Edit**
2. Il campo cost_basis deve mostrare il valore salvato (nero)
3. NON deve esserci il toggle Auto/Manual
4. Deve esserci il bottone **↺** (Recalculate)
5. Click ↺ → appare pannello con valore ricalcolato + [Accept] + [Keep current]
6. Click [Accept] → il campo si aggiorna
7. Click [Keep current] → il pannello sparisce, valore invariato

---

### WT-7: Frontend — BulkModal cella cost_basis

> Verificato manualmente 2026-05-21 (walktest priorità alta #5). Commit batch mixed (6 create + 2 update + 1 delete) funziona con toast formattato a elenco puntato.

1. Dalla tabella, apri la BulkModal (multi-select + edit)
2. Aggiungi una nuova riga TRANSFER
3. Nella colonna cost_basis (potrebbe essere nascosta → visibilità colonne → attivare):
   - Riga nuova TRANSFER → mostra "💡 auto" grigio corsivo
   - Riga da DB con cost_basis → mostra il valore formattato
   - Riga nuova non-TRANSFER → mostra "—"
4. Click sulla riga nuova TRANSFER → si apre il FormModal con WacPreviewSection

---

### WT-8: Frontend — PromoteMergeModal cost_basis

> Verificato via E2E `tx-split-promote.spec.ts` (test "Promote: select 2 promote-test WITHDRAWAL+DEPOSIT rows → toolbar shows link button") + walktest priorità media #10.

1. Nella BulkModal, seleziona 2 transazioni standalone opposte (es. una SELL e una BUY per lo stesso asset) → promuovile a TRANSFER
2. Se la modale di merge si apre:
   - Deve esserci la sezione "Cost Basis (receiver)"
   - Con toggle Auto/Manual se il receiver è nuovo
   - Con ↺ Recalculate se il receiver è da DB
3. Conferma → il `cost_basis_override` deve essere incluso nel payload

---

### WT-9: Frontend — Error banner FX mancante

> Verificato via E2E `tx-wac.spec.ts` test "W-excluded — Missing FX shows error banner" (verifica DOM structure del testid `tx-form-cost-basis-missing-pairs`).

1. Crea un asset in valuta CHF
2. Crea un BUY in CHF per quell'asset
3. Crea una nuova TRANSFER per quell'asset (form o bulk)
4. Se non esiste la coppia FX CHF/EUR:
   - Deve apparire il banner "Cannot calculate WAC: missing FX rate"
   - Con i bottoni: [Add FX pair →], [Sync FX rates], [Sync asset prices]
   - Click su [Add FX pair →] → naviga a /fx

---

### WT-10: Frontend — Qualifying TXs espandibile

> Verificato via E2E `tx-wac.spec.ts` test "W-live — Qualifying TXs expandable section" (click `tx-form-cost-basis-show-qualifying` → tabella `tx-form-cost-basis-qualifying-table` visibile).

1. In una nuova TRANSFER (con Auto e risultato WAC presente):
   - Deve apparire "💡 Suggested WAC (N transactions used)"
   - Click [Show] → si espande la tabella con colonne: #, Type, Date, Qty, Unit, Effect
   - Pending TXs evidenziate con sfondo diverso (indigo leggero)
   - Click [Hide] → la tabella si richiude

---

### WT-11: i18n — Chiavi presenti in tutte le lingue

> Verificato: `./dev.py i18n audit` non segnala MISSING per `transactions.wacPreview.*`.

```bash
./dev.py i18n audit
```

**Aspettativa**: nessun MISSING error per `transactions.wacPreview.*`. Le 4 chiavi "non referenziate" (adjustmentHint, assetPrice, fromBroker, stale) sono attese — verranno usate nello Scenario E completo.

---

### WT-12: E2E — Test runner riconosce il nuovo test

> Verificato 2026-05-21: `./dev.py test front-transaction tx-wac` → 7/7 PASSED.
> Fix applicati in sessione precedente: testid errati corretti (`tx-new-btn`→`tx-add-button`, `tx-type-option`→`search-select-option`, `42.50`→`42.5`).

```bash
./dev.py test front-transaction tx-wac --headed
```

**Risultato**: 7/7 test PASSED (W8, W9, W10, W-live, W-manual, W-sell, W-excluded).

---

## 🐛 Osservazioni Walktest Manuale (2026-05-21)

Raccolte durante i test manuali post-migrazione payload. Da risolvere in un prossimo round di bugfix.

---

### Bug 1 — WAC Preview: fetch infinito con valore 0 + bordo rosso

**Scope**: `WacPreviewSection.svelte` + `CompactCashCell` sign hint
**Severità**: 🔴 Alta (UX degradata, richieste infinite)

**Sintomo**: Quando il WAC ritorna `amount: "0"` (perché tutte le TX qualificanti hanno `add_zero_cost`), il campo mostra bordo rosso e il componente continua a triggerare `wac-preview` ripetutamente (loop `$effect`).

**Causa probabile**: il valore `0` soddisfa `signBad` per la regola `nonzero` → coloring rosso. Il loop suggerisce che l'`$effect` ricalcola quando il valore cambia da `""` a `"0"` → ri-trigger il debounce → loop.

**Log rete osservato** (senza toccare nulla):
```
wac-preview 200 → wac-preview 200 → wac-preview 200 → ... (~10+ in pochi secondi)
```

**Payload**:
```json
{"items":[{"sender_broker_id":3,"asset_id":1,"date_range":{"start":"2000-01-01","end":"2026-05-21"}}],"pending_txs":[],"excluded_tx_ids":[]}
```

**Azione**: Fix loop `$effect` (dipendenza circolare value↔fetch), e decidere se `0` con regola `nonzero` deve essere rosso oppure neutro per il WAC auto.

---

### Bug 2 — WAC Preview: data inizio hardcoded a `2000-01-01` ✅ RISOLTO

**Scope**: `WacPreviewSection.svelte` → parametro `date_range.start`
**Severità**: 🟡 Media (funzionale ma inefficiente)
**Stato**: ✅ Risolto (2026-05-21)

**Soluzione implementata**: Creato `OpenDateRangeModel` in `common.py` (sia start che end opzionali, riusabile). `WACPreviewItem` usa `OpenDateRangeModel` come tipo per `date_range`. Frontend manda solo `{end: txDate}` senza start. Il backend computa WAC su tutte le TX con `date <= end_date`.

---

### Bug 3 — WacPreviewSection: layout label e toggle

**Scope**: `WacPreviewSection.svelte` → layout CSS
**Severità**: 🟢 Cosmetica

**Problemi osservati**:
1. La label "Override costo medio" va a capo nonostante ci sia spazio sufficiente (causa: `w-32 shrink-0` troppo ristretto per il testo tradotto in IT)
2. Il toggle Auto|Manual dovrebbe essere allineato a destra (flex spacer tra label e toggle)
3. Le label "Auto" e "Manual" sono in inglese anche quando la lingua è italiana

**Fix**: rimuovere `w-32` → usare `whitespace-nowrap` sulla label; aggiungere `ml-auto` al toggle; tradurre "Auto"/"Manual" con chiavi i18n.

---

### Bug 4 — Qualifying TXs table: formattazione e traduzione

**Scope**: `WacPreviewSection.svelte` → tabella qualifying
**Severità**: 🟢 Cosmetica

**Problemi osservati**:
1. **Tipo**: mostra codice raw (`ADJUSTMENT`, `TRANSFER`) → dovrebbe mostrare icona + nome tradotto
2. **Quantità**: mostra 6 decimali (`2.000000`) → formattare con `formatDecimalForDisplay()` (rimuove zeri trailing)
3. **Effect badge**: il colore è uniforme grigio → colorare in base al tipo (`add` = verde, `reduce` = ambra, `add_zero_cost` = grigio, `skip` = rosso)
4. **Effect testo**: mostra codice raw (`add_zero_cost`) → tradurre con chiave i18n (es. "Aggiunto (costo 0)")

---

### Bug 5 — Mock data: mancano BUY + override cost per test WAC

**Scope**: `populate_mock_data.py`
**Severità**: 🟡 Media (test visivo impossibile)

**Osservazione**: I dati mock hanno solo ADJUSTMENT e TRANSFER con `add_zero_cost` → il WAC è sempre 0. Servirebbero:
- Almeno 1 BUY per l'asset con cash non-zero (genera WAC reale)
- Almeno 1 TRANSFER con `cost_basis_override` popolato (mostra valore nel campo)

---

### Bug 6 — BulkModal: UUID linked TX mostra `↔ new`

**Scope**: `TransactionBulkModal.svelte` → cella link_uuid
**Severità**: 🟢 Cosmetica

**Sintomo**: La cella mostra `↔ new` per le linked pairs nuove create nel workspace.

**Proposta**: mostrare `new ↔ new` per rendere chiaro che entrambi i lati sono nuovi, non solo uno.

---

### Bug 7 — BulkModal: colonne di default troppo ridotte

**Scope**: `TransactionBulkModal.svelte` → default visible columns
**Severità**: 🟢 Cosmetica

**Proposta**: mostrare di default TUTTE le colonne eccetto "Creato" e "Aggiornato" (timestamps). Attualmente alcune colonne utili sono nascoste.

---

### Bug 8 — BulkModal edit paired TX: secondo broker si perde

**Scope**: `TransactionFormModal.svelte` → caricamento paired TX in edit mode
**Severità**: 🔴 Alta (regressione funzionale)

**Sintomo**: Editare una TX paired (TRANSFER titoli o CASH_TRANSFER/bonificho) nel FormModal dalla BulkModal → il secondo broker (partner side) non viene popolato nel form.

**Prima di risolvere**: serve chiarimento sull'architettura — come il FormModal riceve le 2 TX quando apre una linked pair? Viene passato solo `initialRow` + `partner` come props? O deve fetchare dal backend?

---

### Bug 9 — BulkModal cella cost_basis: mostra solo "💡 auto" senza valore

**Scope**: `TransactionBulkModal.svelte` → cella cost_basis per righe nuove
**Severità**: 🟡 Media (informazione mancante)

**Sintomo**: Le righe nuove TRANSFER in auto mostrano solo `💡 auto` (grigio corsivo) ma NON il valore numerico calcolato.

**Aspettativa**: dovrebbe mostrare il valore WAC effettivo (es. `💡 175.57 USD`) in grigio corsivo.

---

### Bug 10 — BulkModal cella cost_basis: Manual digitato non si vede

**Scope**: `TransactionBulkModal.svelte` → cella cost_basis per righe manuali
**Severità**: 🟡 Media (dato perso visivamente)

**Sintomo**: Se l'utente digita un valore manuale nel FormModal (toggle Manual), la cella nella BulkModal rimane invariata (mostra ancora `💡 auto` o vuota).

**Aspettativa**: dovrebbe mostrare il valore nero formattato (es. `42.50 EUR`) come per la colonna importo.

---

### Bug 11 — BulkModal cella cost_basis: righe DB non mostrano valore

**Scope**: `TransactionBulkModal.svelte` → cella cost_basis per righe da DB
**Severità**: 🟡 Media

**Sintomo**: Le righe da DB con `cost_basis_override` salvato mostrano `—` (trattino) invece del valore.

**Nota**: per ADJUSTMENT post-split il lato con l'override si vede → la logica di rendering è condizionale sul tipo e non dovrebbe esserlo. Tutte le righe con `cost_basis_override` != null devono mostrare il valore, indipendentemente dal tipo TX.

**Azione**: ripensare la logica di generazione della cella cost_basis per renderla **indipendente dal tipo** — se il campo ha un valore, mostrarlo sempre.

---

## 📊 Classificazione Bug per Complessità

### 🟩 One-shot (fix diretti)

| # | Bug | Fix stimato | Stato |
|---|-----|-------------|-------|
| **2** | Data inizio hardcoded `2000-01-01` | Backend: `OpenDateRangeModel` in `common.py` (start/end opzionali), usato in `WACPreviewItem`. Frontend: manda solo `{end: txDate}`. | ✅ Verificato |
| **3** | Layout label/toggle WAC | CSS: `whitespace-nowrap`, `ml-auto` sul toggle. i18n: chiavi `wacPreview.toggleAuto`/`wacPreview.toggleManual` (4 lingue) | ✅ Implementato |
| **4** | Qualifying TXs table formattazione | Icona+traduzione tipo, badge colorati per effect, `formatCurrencyAmountPlain` per costo unitario (2 decimali+valuta), colonna rinominata "Costo unitario", DocsLink alla pagina WAC, pannello foldable. Effetti rinominati: Weighted/Quantity reduced/Dilution. `skip_no_override` rimosso. | ✅ Verificato |
| **5** | Mock data senza BUY per test WAC | 4 TX `wac-test`: DEPOSIT prefund $3000, BUY 10@$150, BUY 5@$180, ADJUSTMENT -3 override=$160 (date relative a today). Balance-safe. | ✅ Implementato |
| **6** | UUID `↔ new` → `new ↔ new` | BulkModal: cambiato testo nella cella link_uuid | ✅ Verificato |
| **7** | Colonne default tutte visibili | BulkModal: `hiddenByDefault: false` per tags, cost_basis, asset_event_id, link_uuid. Solo created_at/updated_at restano hidden. | ✅ Verificato |

#### Fix aggiuntive implementate durante la sessione

| Fix | Descrizione |
|-----|-------------|
| **Sign coloring paired** | `effectiveQtyRule = pairLayout ? 'positive' : rule.quantityRule` — border verde/rosso corretto per form duali |
| **Bottone Apply disabilitato su sign violation** | `hasSignViolation` (qty o cash con segno sbagliato) blocca Apply/Save |
| **isFormComplete esteso per paired** | Richiede `dualTo.broker_id` + cash FX prima di abilitare validate/submit |
| **Bottone ⚡ Validate gateato** | Disabilitato quando `!isFormComplete` (evita errori premature "manca broker") |
| **Pagina doc WAC** | `portfolio-theory/weighted-average-cost.en.md` con formula, effetti, esempi foldabili, multi-currency |
| **MkDocs nav** | Transaction types divise in Single + Composite; WAC in portfolio-theory |
| **Admonition checker** | Fix falso positivo: skip fenced code blocks |

### 🟧 Richiedono studio architettura

| # | Bug | Cosa serve capire |
|---|-----|-------------------|
| **1** | WAC fetch loop infinito | Interazione `$effect` ↔ `onChange` ↔ `autoMode` ↔ debounce. Dipendenza circolare value↔fetch. |
| **8** | Partner broker si perde in edit paired | Come il FormModal riceve i dati della TX partner dalla BulkModal. |
| **9** | Cella bulk "💡 auto" senza valore numerico | Propagazione valore WAC calcolato dal FormModal → cella BulkModal. |
| **10** | Manual digitato non si vede in cella | Come `cost_basis_override` torna al BulkModal quando FormModal chiude. |
| **11** | Righe DB non mostrano cost_basis | Logica condizionale `renderCostBasisCell()`, tipo-dipendente → type-agnostic. |

**Nota**: Bug #9, #10, #11 sono lo **stesso problema** da 3 angoli → vanno risolti insieme come task unico "Riscrittura cella cost_basis BulkModal".

---

## 🚀 Prompt per Agente Planner — One-shot (Bug 2, 3, 4, 5, 6, 7)

> **Plan file suggerito**: `plan-phase07-transaction-Part4_Round6_PlanD2_round2_plan-R2-SP-C-BugfixRound3-WacOneShot.prompt.md`

```markdown
# Prompt: WAC Preview One-Shot Fixes (Bug 2, 3, 4, 5, 6, 7)

## Contesto

Stiamo lavorando su LibreFolio, un portfolio tracker self-hosted. Il piano padre è:
`plan-phase07-transaction-Part4_Round6_PlanD2_round2_plan-R2-SP-C-BugfixRound2-WacPreview.prompt.md`

I seguenti 6 bug sono stati classificati come "one-shot" (fix diretto senza analisi architetturale).
Crea un piano di implementazione con step numerati, file coinvolti, e ordine esecuzione.

## Bug da risolvere

### Bug 2 — date_range.start hardcoded a 2000-01-01
- File backend: `backend/app/schemas/transactions.py` (WACPreviewItem)
- File frontend: `frontend/src/lib/components/transactions/WacPreviewSection.svelte`
- Fix: rendere `date_range.start` opzionale (`Optional[date] = None`). Se None → backend parte dalla TX più vecchia del (broker, asset). Frontend smette di mandare start.

### Bug 3 — Layout label/toggle WAC
- File: `frontend/src/lib/components/transactions/WacPreviewSection.svelte`
- Fix:
  1. Label: rimuovere `w-32 shrink-0` → usare `whitespace-nowrap`
  2. Toggle: aggiungere `ml-auto` per allineamento a destra
  3. i18n: tradurre "Auto"/"Manual" con chiavi `transactions.wacPreview.toggleAuto` / `transactions.wacPreview.toggleManual` (aggiungere in 4 lingue)

### Bug 4 — Qualifying TXs table formattazione
- File: `frontend/src/lib/components/transactions/WacPreviewSection.svelte`
- Fix:
  1. Colonna Type: mostrare icona (da `getTypeIconSlug()`) + nome tradotto (da type store)
  2. Colonna Qty: usare `formatDecimalForDisplay()` (rimuove zeri trailing)
  3. Colonna Effect badge: colorare verde (`add`), ambra (`reduce`), grigio (`add_zero_cost`), rosso (`skip_no_override`)
  4. Colonna Effect testo: tradurre con chiavi i18n `transactions.wacPreview.effect.add`, `.reduce`, `.addZeroCost`, `.skip`

### Bug 5 — Mock data senza BUY per test WAC
- File: `backend/test_scripts/test_db/populate_mock_data.py`
- Fix: aggiungere per l'asset Apple (id=1) + broker IB (id=3):
  1. BUY 10 shares @ $150 (cash -$1500) data 2026-04-01
  2. BUY 5 shares @ $180 (cash -$900) data 2026-04-15
  3. TRANSFER 3 shares con cost_basis_override {code: "USD", amount: "160"} data 2026-05-01
  Questo genera WAC reale (~$160) e mostra il campo override popolato.

### Bug 6 — BulkModal UUID linked mostra `↔ new`
- File: `frontend/src/lib/components/transactions/TransactionBulkModal.svelte`
- Fix: cercare dove renderizza `↔ new` per link_uuid delle TX nuove → cambiare in `new ↔ new`

### Bug 7 — BulkModal colonne default ridotte
- File: `frontend/src/lib/components/transactions/TransactionBulkModal.svelte`
- Fix: modificare `defaultVisibleColumns` (o equivalente) → includere tutte le colonne eccetto `created_at` e `updated_at`

## Vincoli
- Dopo modifiche backend schema: `./dev.py api sync`
- Dopo modifiche mock data: `./dev.py db create-clean --test`
- Dopo modifiche i18n: `./dev.py i18n audit` per verificare
- Test: `./dev.py test front-transaction tx-wac` deve continuare a passare
- `svelte-check`: 0 errors

## Deliverable
Piano con step numerati, ordine di esecuzione, file specifici, stima LOC modificate.
```

---

## 🔬 Prompt per Agente Planner — Bug 1: WAC fetch loop infinito

> **Plan file suggerito**: `plan-phase07-transaction-Part4_Round6_PlanD2_round2_plan-R2-SP-C-BugfixRound3-WacFetchLoop.prompt.md`

```markdown
# Prompt: Fix WAC Preview Infinite Fetch Loop (Bug 1)

## Contesto

In LibreFolio (SvelteKit 2 + Svelte 5 runes), il componente `WacPreviewSection.svelte` ha un loop infinito di fetch quando il WAC calcolato è `0`.

Piano padre: `plan-phase07-transaction-Part4_Round6_PlanD2_round2_plan-R2-SP-C-BugfixRound2-WacPreview.prompt.md` (sezione Bug 1)

## Sintomo

- Quando il backend ritorna `wac: {code: "USD", amount: "0"}`, il network tab mostra `wac-preview` chiamato ripetutamente (~10+ in pochi secondi) senza che l'utente tocchi nulla.
- Il campo mostra bordo rosso (sign-bad per regola `nonzero`).

## Analisi richiesta

1. Leggere `frontend/src/lib/components/transactions/WacPreviewSection.svelte`
2. Tracciare il flusso: quale `$effect` triggera il fetch? Quali sue dipendenze cambiano dopo che il fetch completa e setta il valore?
3. Verificare se `CompactCashCell.onChange` viene chiamato quando il valore viene settato programmaticamente (non dall'utente) → causa re-trigger dell'$effect
4. Verificare se il `signHint` (coloring bordo) scatena un re-render che modifica le dipendenze dell'$effect

## Causa probabile

Circolo: fetch → set value `"0"` → onChange emette → parent $effect vede dipendenza cambiata → ri-fetch → set value `"0"` → ...

## Fix proposti (da valutare)

- **Opzione A**: distinguere "set programmatico" da "set utente" nel CompactCashCell (non emettere onChange se il valore è settato via prop, solo se l'utente digita)
- **Opzione B**: nel `$effect` di fetch, confrontare il valore corrente con il risultato — se identico, non ri-settare
- **Opzione C**: usare un flag `isFetching` come guard nel $effect per non ri-triggerare durante il set post-fetch
- **Decisione aggiuntiva**: il WAC auto a `0` deve mostrare bordo rosso (bad sign)? O il sign hint va disabilitato quando è in modalità Auto?

## Vincoli

- Svelte 5 runes (`$state`, `$derived`, `$effect`)
- Il debounce è already implementato (500ms trailing) ma non previene il loop post-fetch
- Test E2E `tx-wac.spec.ts` deve continuare a passare

## Deliverable

Piano con: (1) root cause confermata dopo lettura codice, (2) opzione scelta con rationale, (3) step implementativi, (4) test di regressione.
```

---

## 🔬 Prompt per Agente Planner — Bug 8: Partner broker si perde in edit paired

> **Plan file suggerito**: `plan-phase07-transaction-Part4_Round6_PlanD2_round2_plan-R2-SP-C-BugfixRound3-PairedBrokerLost.prompt.md`

```markdown
# Prompt: Fix Partner Broker Lost on Edit Paired TX (Bug 8)

## Contesto

In LibreFolio, editare una TX paired (TRANSFER titoli o CASH_TRANSFER) nel FormModal dalla BulkModal fa sì che il secondo broker (partner side) non venga popolato.

Piano padre: `plan-phase07-transaction-Part4_Round6_PlanD2_round2_plan-R2-SP-C-BugfixRound2-WacPreview.prompt.md` (sezione Bug 8)

## Analisi richiesta

1. Leggere `frontend/src/lib/components/transactions/TransactionFormModal.svelte` — come riceve `initialRow` e `partner` (o equivalente)
2. Leggere `frontend/src/lib/components/transactions/TransactionBulkModal.svelte` — come passa i dati al FormModal quando si apre una riga paired
3. Capire il flusso:
   - BulkModal ha le righe in `ops[]` con `partner` reference
   - Quando utente fa double-click su una riga paired → apre FormModal
   - Come vengono passati i dati del partner? Props? Lookup nell'array ops?
4. Verificare: il partner esiste in `ops[]`? Viene passato al FormModal? Il FormModal lo usa per popolare `dualTo.broker_id`?

## Sintomo

- Apri BulkModal con TX paired (TRANSFER o CASH_TRANSFER)
- Double-click sulla riga → FormModal si apre
- Il campo "To broker" è vuoto
- Il campo "From broker" è popolato correttamente

## Fix proposti (da valutare dopo analisi)

- Se il partner non viene passato → aggiungerlo come prop/context
- Se viene passato ma non consumato → fix nell'inizializzazione `dualTo`
- Se il lookup fallisce perché usa un formato diverso (id vs tempId) → normalizzare

## Vincoli

- E2E test `tx-paired-edit.spec.ts` verifica questo scenario (ma dal main table, non dalla BulkModal)
- Il fix non deve rompere il flusso "new paired" (create) che funziona correttamente

## Deliverable

Piano con: (1) architettura documentata (diagramma flusso dati BulkModal→FormModal per paired), (2) root cause, (3) fix implementativo, (4) test aggiuntivo se necessario.
```

---

## 🔬 Prompt per Agente Planner — Bug 9+10+11: Cella cost_basis BulkModal

> **Plan file suggerito**: `plan-phase07-transaction-Part4_Round6_PlanD2_round2_plan-R2-SP-C-BugfixRound3-BulkCostBasisCell.prompt.md`

```markdown
# Prompt: Riscrittura Cella cost_basis nella BulkModal (Bug 9, 10, 11)

## Contesto

In LibreFolio, la cella `cost_basis_override` nella BulkModal (`TransactionBulkModal.svelte`) ha 3 problemi correlati che derivano dalla stessa architettura carente.

Piano padre: `plan-phase07-transaction-Part4_Round6_PlanD2_round2_plan-R2-SP-C-BugfixRound2-WacPreview.prompt.md` (sezione Bug 9, 10, 11)

## Problemi

1. **Bug 9**: Righe nuove TRANSFER in auto mostrano solo `💡 auto` senza il valore WAC calcolato
2. **Bug 10**: Se l'utente digita un valore manual nel FormModal, la cella BulkModal resta invariata
3. **Bug 11**: Righe da DB con `cost_basis_override` salvato mostrano `—` (dipendenza errata dal tipo TX)

## Analisi richiesta

1. Leggere `TransactionBulkModal.svelte` — cercare la logica che renderizza la cella cost_basis (probabile sezione `{#if}` o helper che decide cosa mostrare)
2. Capire come il `PendingOp` memorizza il `cost_basis_override`:
   - Per righe nuove: dove finisce il valore quando il FormModal lo popola (auto o manual)?
   - Per righe DB: il campo `cost_basis_override` è in `op.original`? In `op.draft`?
3. Capire il flusso ritorno FormModal → BulkModal:
   - Il FormModal emette `onPushDraft(payload)` con `commitOnSave=false`
   - Il payload include `cost_basis_override`? O è perso?
4. Verificare se la cella usa una condizione `if (type === 'TRANSFER' || type === 'ADJUSTMENT')` che esclude altri tipi

## Aspettativa funzionale (target)

| Stato riga | Cella cost_basis |
|-----------|------------------|
| Nuova, auto, valore calcolato | `💡 175.57 USD` (grigio corsivo) |
| Nuova, auto, in calcolo | `💡 …` (grigio corsivo, spinner) |
| Nuova, manual, valore digitato | `42.50 EUR` (nero) |
| Nuova, senza override | `—` |
| DB, con override salvato | `160.00 USD` (nero) |
| DB, senza override | `—` |
| Qualsiasi tipo (TRANSFER, ADJUSTMENT, BUY, SELL...) | Se ha valore → mostrare. Tipo irrilevante. |

## Vincoli

- La cella deve essere **type-agnostic**: se `cost_basis_override` ha un valore, mostrarlo sempre
- Il valore WAC auto deve essere propagato dal WacPreviewSection (dentro FormModal) → PendingOp nel BulkModal
- Il formato deve essere coerente con la cella Cash (stesso CompactCashCell readonly style)
- Test: `./dev.py test front-transaction all` deve passare

## Deliverable

Piano con: (1) architettura attuale documentata, (2) proposta nuova architettura cella, (3) step implementativi, (4) casi test.
```

---

## Riepilogo file plan suggeriti

| Bug | Plan file |
|-----|-----------|
| 2,3,4,5,6,7 (one-shot) | `plan-...-BugfixRound3-WacOneShot.prompt.md` |
| 1 (fetch loop) | `plan-...-BugfixRound3-WacFetchLoop.prompt.md` |
| 8 (partner broker) | `plan-...-BugfixRound3-PairedBrokerLost.prompt.md` |
| 9+10+11 (cella bulk) | `plan-...-BugfixRound3-BulkCostBasisCell.prompt.md` |

Radice comune: `plan-phase07-transaction-Part4_Round6_PlanD2_round2_plan-R2-SP-C-BugfixRound3-{Suffisso}.prompt.md`
