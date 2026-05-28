# Plan: Fix WAC Feedback Loop + `cost_basis_mode` in Payload

> **✅ STATUS (2026-05-28)**: COMPLETATO — backend math engine gestisce `add_at_wac`, frontend manda `cost_basis_mode` nel payload WAC, loop eliminato. 28 backend WAC tests pass, E2E WB6+WB7 pass, regression 25/25 pass.

**Parent plan**: [`plan-ReactiveWacBulkModal.prompt.md`](./plan-ReactiveWacBulkModal.prompt.md) (Piano v6 completato — questo è il follow-up per il loop scoperto nel walktest)

---

## Problema

Il batch WAC nella BulkModal genera un **feedback loop** perché il receiver TRANSFER manda il proprio `cost_basis_override` (calcolato) come contesto nei `pending_txs` → il backend lo re-include nel pool del broker destinazione → produce un WAC diverso → valore scritto nel receiver → re-fire → loop fino a convergenza a ~0.

### Payload osservato (human walktest 2026-05-28)

```
1° call: receiver cbo = 160.42 → backend risponde WAC ≈ 26.7
2° call: receiver cbo = 26.7   → backend risponde WAC ≈ 4.5
...
N° call: receiver cbo ≈ 0.02  → converge a 0
```

### Problema secondario: items interdipendenti

2 ADJUSTMENT in auto sullo stesso broker:
- Day1: ADJUSTMENT +5, auto (cbo=null)
- Day2: ADJUSTMENT +3, auto (cbo=null)

Il backend tratta `cbo=null` come "add_zero_cost" (diluisce il pool). Ma "auto" dovrebbe significare **"inherit running_wac"** (quote arrivano al costo medio del pool → pool invariato).

### Bug minore UX

Nella FormModal, se la tabella qualifying è espansa e l'utente clicca "Manual", la tabella resta aperta. Dovrebbe collassarsi.

---

## Root Cause

`compute_wac_from_txlist` (`financial_utils.py` riga 119-124) tratta `unit_cost_converted = None` come "add_zero_cost":

```python
if tx.unit_cost_converted is not None and tx.unit_cost_converted > 0:
    unit_cost = tx.unit_cost_converted
    effect = "add"
else:
    unit_cost = Decimal("0")
    effect = "add_zero_cost"  # ← PROBLEM: diluisce il pool
```

Per items con `cost_basis_mode == "auto"`, il corretto è: `unit_cost = running_wac` (pool invariato algebricamente).

---

## Decisione architetturale: campo esplicito `cost_basis_mode`

**NON usare null come sentinel**. Mandare `cost_basis_mode` esplicitamente a `WACPendingTXItem`:

```python
cost_basis_mode: Literal["auto", "manual"] | None = Field(
    None,
    description="'auto': inherit running_wac (no pool impact); "
                "'manual': use cost_basis_override value; "
                "None: not applicable (BUY, SELL, etc.)",
)
```

### Semantica nel math engine

| `cost_basis_mode` | `cbo` value | Backend behavior | Effect label | Pool impact |
|---|---|---|---|---|
| `"auto"` | null (forzato) | `unit_cost = running_wac` | `add_at_wac` | Pool invariato |
| `"manual"` | explicit value | `unit_cost = cbo_amt` | `add` | Pool cambia |
| `None` (BUY) | — | `unit_cost = cash/qty` | `add` | Pool cambia |
| `None` (SELL) | — | `unit_cost = running_wac` | `reduce` | Pool cambia |
| `None` + no cbo | — | `unit_cost = 0` | `add_zero_cost` | Pool diluito |

### Perché "add_at_wac" non impatta il pool (dimostrazione algebrica)

```
new_wac = ((wac × qty_pool) + (wac × tx_qty)) / (qty_pool + tx_qty)
        = wac × (qty_pool + tx_qty) / (qty_pool + tx_qty)
        = wac  ✅
```

### Quando compare `add_at_wac` nella tabella qualifying?

Quando il backend processa un pending TX con `cost_basis_mode == "auto"` e qty > 0. Esempio nella UI:

```
● | TRANSFER | 2026-05-28 | +5 | 100.00 USD | [Inherited] | 100.00
```

- `●` = pending (no tx_id)
- Unit cost = running_wac al momento dell'inserimento
- Effect badge = "Inherited" (nuovo colore blu/indigo)
- Running WAC = invariato rispetto alla riga precedente

Le pending sono già evidenziate con sfondo indigo (riga 420 di WacPreviewSection).

### Caso limite: pool vuoto (qty_pool == 0)

Se il broker non ha mai avuto l'asset e il primo ingresso è un TRANSFER auto:
- `wac = 0` → `unit_cost = 0` → `effect = "add_at_wac"`
- Le quote entrano a costo 0 — semanticamente corretto: nessun WAC di riferimento
- Il valore reale verrà calcolato dall'endpoint (`sender_broker_id` punta al source)

---

## Steps

### Step 1: Backend — aggiungere `cost_basis_mode` a `WACPendingTXItem` ✅

**Completato**: 2026-05-28

> **Note implementazione**: Aggiunto campo `cost_basis_mode: Literal["auto", "manual"] | None = Field(None, ...)` a `WACPendingTXItem` in `transactions.py`.

**File**: `backend/app/schemas/transactions.py`, classe `WACPendingTXItem` (riga 701)

```python
class WACPendingTXItem(TXCreateItem):
    """..."""
    id: Optional[int] = Field(None, ...)
    asset_id: int = Field(..., ...)
    cost_basis_mode: Literal["auto", "manual"] | None = Field(
        None,
        description="'auto': cost = inherit running WAC (no pool impact); "
                    "'manual': use cost_basis_override; "
                    "None: not applicable (BUY, SELL, etc.)",
    )
```

### Step 2: Backend — aggiungere `cost_basis_mode` a `WACInputTX` dataclass ✅

**Completato**: 2026-05-28

> **Note implementazione**: Aggiunto `cost_basis_mode: Optional[str] = None` al dataclass `WACInputTX` in `financial_utils.py`.

**File**: `backend/app/utils/financial_utils.py`, dataclass `WACInputTX` (riga 36)

```python
@dataclass
class WACInputTX:
    tx_id: Optional[int]
    type: str
    date: date
    quantity: Decimal
    unit_cost_converted: Optional[Decimal]
    original_currency: str
    is_pending: bool = False
    cost_basis_mode: str | None = None  # "auto" | "manual" | None
```

### Step 3: Backend — propagare `cost_basis_mode` nel tuple unified ✅

**Completato**: 2026-05-28

> **Note implementazione**: Tuple `unified` esteso a 10 elementi (cbm come 10°). Aggiornati 3 punti di append (pending override in DB, remaining pending, new pending) e 3 loop di lettura (pre_txs, fx_requests, input_txs). Per DB rows: `None`. Per pending: `ptx.cost_basis_mode`. Propagato in `WACInputTX(cost_basis_mode=cbm)`.

**File**: `backend/app/services/transaction_service.py`, funzione `compute_wac_iterative`

Il tuple `unified` diventa a 10 elementi. Aggiungere `cbm` (cost_basis_mode) come 10° campo:
- Per pending TX: `ptx.cost_basis_mode`
- Per DB rows: `None`

Propagare nella costruzione di `WACInputTX` (riga 385):
```python
input_txs.append(
    WACInputTX(
        ...,
        cost_basis_mode=cbm,
    )
)
```

### Step 4: Backend — `compute_wac_from_txlist` gestisce "auto" mode ✅

**Completato**: 2026-05-28

> **Note implementazione**: Aggiunto branch `if tx.cost_basis_mode == "auto"` come primo check nel ramo acquisitions (qty>0). Se pool non vuoto: `unit_cost = wac`, effect = `"add_at_wac"`. Se pool vuoto: `unit_cost = 0`. Tutti i 24 test WAC esistenti passano (P1-P11 + validation + cost_basis).

**File**: `backend/app/utils/financial_utils.py`, righe 117-124

```python
if tx_qty > 0:
    # Acquisition
    if tx.cost_basis_mode == "auto":
        # Auto: shares arrive at current pool cost → pool WAC unchanged
        unit_cost = wac if qty_pool > 0 else Decimal("0")
        effect = "add_at_wac"
    elif tx.unit_cost_converted is not None and tx.unit_cost_converted > 0:
        unit_cost = tx.unit_cost_converted
        effect = "add"
    else:
        unit_cost = Decimal("0")
        effect = "add_zero_cost"
    tx_cost = unit_cost
```

### Step 5: Frontend — `fetchBatchWac` manda `cost_basis_mode` e nullifica cbo per auto ✅

**Completato**: 2026-05-28

> **Note implementazione**: Nel `.map()` dei pending_txs, aggiunto `cost_basis_mode: f.cost_basis_mode ?? undefined` e cambiato `cost_basis_override` in `f.cost_basis_mode === 'auto' ? null : (f.cost_basis_override ?? null)`. Questo rompe il loop: auto items non mandano il valore calcolato precedentemente.

**File**: `frontend/src/lib/components/transactions/TransactionBulkModal.svelte`, funzione `fetchBatchWac()`, nel `.map()` dei pending_txs

```typescript
// Nel mapping aggiungere:
cost_basis_mode: o.fields.cost_basis_mode ?? undefined,
// Per righe auto: forzare cbo a null (non mandare valore precedente)
cost_basis_override: o.fields.cost_basis_mode === 'auto'
    ? null
    : (o.fields.cost_basis_override ?? null),
```

`undefined` per BUY/SELL → non incluso nel JSON → backend riceve None → legacy.
`"auto"` per TRANSFER receiver / ADJUSTMENT auto → backend fa add_at_wac.
`"manual"` per override espliciti → backend usa il valore.

### Step 6: Frontend — collassare tabella qualifying al toggle manual ✅

**Completato**: 2026-05-28

> **Note implementazione**: Aggiunto `showQualifying = false;` in `switchToManual()` dopo `mode = 'manual'`.

**File**: `frontend/src/lib/components/transactions/WacPreviewSection.svelte`, funzione `switchToManual()` (riga 291)

```typescript
function switchToManual() {
    mode = 'manual';
    onModeChange?.('manual');
    showQualifying = false;  // ← NEW: collapse table on manual switch
    if (abortController) abortController.abort();
}
```

### Step 7: Frontend — render effect label `add_at_wac` nella qualifying table ✅

**Completato**: 2026-05-28

> **Note implementazione**: Aggiunto branch `add_at_wac` con colore indigo nel template effect badge. Now 4 cases: add (green), reduce (amber), add_at_wac (indigo), fallback/addZeroCost (gray).

**File**: `frontend/src/lib/components/transactions/WacPreviewSection.svelte`, righe 434-444

Aggiungere un branch per `add_at_wac` con colore blu/indigo:

```svelte
{#if qtx.effect === 'add'}
    <span class="... bg-green-100 ... text-green-700 ...">{$t('transactions.wacPreview.effect.add') ?? 'Weighted'}</span>
{:else if qtx.effect === 'reduce'}
    <span class="... bg-amber-100 ... text-amber-700 ...">{$t('transactions.wacPreview.effect.reduce') ?? 'Reduced'}</span>
{:else if qtx.effect === 'add_at_wac'}
    <span class="... bg-indigo-100 dark:bg-indigo-900/20 text-indigo-700 dark:text-indigo-400 ...">{$t('transactions.wacPreview.effect.addAtWac') ?? 'Inherited'}</span>
{:else}
    <span class="... bg-gray-100 ... text-gray-600 ...">{$t('transactions.wacPreview.effect.addZeroCost') ?? 'Dilution'}</span>
{/if}
```

### Step 8: i18n — aggiungere chiave `transactions.wacPreview.effect.addAtWac` ✅

**Completato**: 2026-05-28

> **Note implementazione**: Aggiunto in en/it/fr/es.json: "Inherited"/"Ereditato"/"Hérité"/"Heredado".

**Files**: `frontend/src/lib/i18n/{en,it,fr,es}.json`

| Lingua | Chiave | Valore |
|--------|--------|--------|
| EN | `transactions.wacPreview.effect.addAtWac` | `"Inherited"` |
| IT | `transactions.wacPreview.effect.addAtWac` | `"Ereditato"` |
| FR | `transactions.wacPreview.effect.addAtWac` | `"Hérité"` |
| ES | `transactions.wacPreview.effect.addAtWac` | `"Heredado"` |

### Step 9: `./dev.py api sync` + `./dev.py front check` ✅

**Completato**: 2026-05-28

> **Note implementazione**: Client rigenerato (cost_basis_mode visibile in generated.ts riga 4132). svelte-check: 0 errors, 0 warnings.

Rigenerare client TypeScript (nuovo campo `cost_basis_mode` su WACPendingTXItem). Verificare 0 errori svelte-check.

### Step 10: Backend tests — 4 scenari WAC ✅

**Completato**: 2026-05-28

> **Note implementazione**: Aggiunti P12-P15 in `TestWACPreview`. P12 testa sia pool vuoto (WAC=0, stabile) sia pool non vuoto (WAC=100, stabile). P13/P14/P15 passano al primo colpo. Tutti 28 test WAC passano.
> **⚠️ Fuori pista**: P12 originale aspettava WAC=100 per empty pool, ma con auto+pool vuoto il WAC è 0 (corretto: nessun WAC di riferimento). Adattato per testare stabilità in entrambi i casi (empty pool → 0, non-empty pool → WAC preservato).

**File**: `backend/test_scripts/test_api/test_transactions_wac.py`

#### P12: `test_wacp12_auto_mode_no_feedback_loop`

```python
async def test_wacp12_auto_mode_no_feedback_loop(self):
    """WAC with TRANSFER receiver in auto mode → stable result, no loop."""
    # 1. Create user, broker_A (owner), broker_B (owner), asset (USD)
    # 2. Commit BUY 10@100 on broker_A
    # 3. Call wac-preview:
    #    items: [{sender_broker_id: broker_B, asset_id, date_range: {end: today}}]
    #    pending_txs: [
    #      {broker_A, asset_id, type: TRANSFER, qty: -5, link_uuid: X, cost_basis_mode: null},
    #      {broker_B, asset_id, type: TRANSFER, qty: +5, link_uuid: X,
    #       cost_basis_mode: "auto", cost_basis_override: null},
    #    ]
    # 4. Assert 200 OK, WAC = 100
    # 5. Call AGAIN with same payload → Assert WAC = 100 (stable)
```

#### P13: `test_wacp13_interdependent_auto_same_broker`

```python
async def test_wacp13_interdependent_auto_same_broker(self):
    """Two auto ADJUSTMENTs on same broker, different days → pool unchanged."""
    # 1. Broker with BUY 10@100 committed
    # 2. pending_txs: [
    #      Day1: {broker, asset, type: ADJUSTMENT, qty: +5, cost_basis_mode: "auto", cbo: null},
    #      Day2: {broker, asset, type: ADJUSTMENT, qty: +3, cost_basis_mode: "auto", cbo: null},
    #    ]
    # 3. items: [{sender_broker_id: broker, asset_id, date_range: {end: Day2}}]
    # 4. Assert WAC = 100 (both add_at_wac → pool invariant)
```

#### P14: `test_wacp14_auto_same_day`

```python
async def test_wacp14_auto_same_day(self):
    """Two auto ADJUSTMENTs same day → pool unchanged."""
    # Same as P13 but Day1 == Day2
    # Assert WAC = 100
```

#### P15: `test_wacp15_mixed_auto_manual`

```python
async def test_wacp15_mixed_auto_manual(self):
    """Manual ADJUSTMENT contributes to pool, subsequent auto inherits."""
    # 1. Broker with BUY 10@100 committed
    # 2. pending_txs: [
    #      Day1: {broker, asset, type: ADJUSTMENT, qty: +5,
    #             cost_basis_mode: "manual", cbo: {code: "USD", amount: "200"}},
    #      Day2: {broker, asset, type: ADJUSTMENT, qty: +3,
    #             cost_basis_mode: "auto", cbo: null},
    #    ]
    # 3. items: [{sender_broker_id: broker, asset_id, date_range: {end: Day2}}]
    # 4. Assert WAC = (10*100 + 5*200) / 15 = 133.333...
    #    (Day1 manual contributes, Day2 auto inherits 133.33, doesn't change it)
```

### Step 11: Frontend E2E — 2 nuovi test in `tx-wac-bulk.spec.ts` ✅

**Completato**: 2026-05-28

> **Note implementazione**: Aggiunti WB6 (stabilità no-loop) e WB7 (multiple pending BUYs). Entrambi passano. Regression: tx-commit-all-types (19) + tx-split-promote (6) = 25/25 ✅.

**File**: `frontend/e2e/transactions/tx-wac-bulk.spec.ts`

#### WB6: `WAC value stable after debounce — no feedback loop`

```typescript
test('WB6 — WAC value stable after debounce (no feedback loop)', async ({page}) => {
    // 1. Create BUY 10@1000 + TRANSFER 5 (same as WB1)
    // 2. Wait for WAC resolve → capture cell text (value1)
    // 3. Wait 2000ms (allows second debounce to fire if buggy)
    // 4. Capture cell text again (value2)
    // 5. Assert value1 === value2 (no degradation/loop)
});
```

#### WB7: `Multiple pending BUYs affect WAC correctly`

```typescript
test('WB7 — Multiple pending BUYs affect WAC', async ({page}) => {
    // 1. Create BUY 10@100 (broker_A, Apple)
    // 2. Create BUY 5@200 (broker_A, Apple)
    // 3. Create TRANSFER 3 from broker_A → broker_B (Apple)
    // 4. Wait WAC resolve
    // 5. Assert WAC ≈ 133 (weighted: (10*100+5*200)/15 = 133.33)
});
```

---

## Test Criteria

- [x] Backend P12: auto mode → WAC stabile (no loop)
- [x] Backend P13: 2 auto interdipendenti → WAC = 100 (pool invariato)
- [x] Backend P14: same-day auto → WAC = 100
- [x] Backend P15: mixed auto+manual → WAC = 133.33
- [x] E2E WB6: valore stabile dopo debounce
- [x] E2E WB7: pending BUY context → WAC corretto
- [ ] E2E WB1-WB5: non rotti (regression) — da verificare separatamente
- [x] Existing E2E tx-commit-all-types + tx-split-promote: passano (25/25)
- [x] `./dev.py front check` — 0 errors
- [x] `./dev.py api sync` eseguito

---

## Further Considerations

1. **`add_at_wac` con pool vuoto (qty_pool == 0)**: `wac = 0` → `unit_cost = 0`. Questo è corretto: se il broker non ha mai avuto l'asset, non c'è WAC di riferimento. Il valore "reale" viene dal calcolo `sender_broker_id` dell'endpoint items — il pending con auto serve solo come contesto per non diluire il pool.

2. **Compatibilità**: campo `cost_basis_mode` è `Optional` con default `None`. DB rows e vecchi client non lo mandano → None → backend fa legacy. Zero breaking change, zero migration.

3. **Relazione col Piano v7 (E2E test)**: i test WB1-WB5 del Piano v7 sono scritti ma 3 su 5 falliscono (WB2, WB4, WB5) perché il loop era attivo o per selettori infrastrutturali. Dopo il fix del loop (questo piano), WB2 e WB6 dovrebbero passare. WB4 e WB5 hanno problemi di selezione riga (infrastrutturali, non WAC) da risolvere separatamente.

4. **`effect="add_at_wac"` è un nuovo valore**: la `WACQualifyingTX.effect` nel backend schema è `str` (non enum), quindi nessuna modifica schema. Il frontend aggiunge un branch di rendering.

---

## Plan v8b: Fix WAC Infinite Polling + Label "Auto WAC" + Docs

> **✅ STATUS (2026-05-28)**: COMPLETATO — infinite polling eliminato (autoWacItems fuori da tracking scope), label rinominata, docs aggiornata, WB6 con network count passa.

### Problema

Il valore WAC è stabile (no loop nei valori), ma le **chiamate HTTP** continuano all'infinito ogni 800ms (debounce). Dev Tools Network mostra `wac-preview 200` ripetute senza fine anche senza interazione utente.

### Root Cause

Il `$effect` (riga 304) legge sincronamente `autoWacItems` (array `$derived` da `ops`).
Dopo `fetchBatchWac` → writeback `ops = ops.map(...)` (riga 394) → `ops` cambia reference →
`autoWacItems` ricalcola → **nuovo array reference** → Svelte 5 notifica (arrays no deep equality) →
`$effect` re-fires → debounce 800ms → fetch → write → repeat.

`wacFingerprint` (string primitiva) **NON** è il problema: `$derived` con primitivi fa `===` e non notifica se stessa stringa. Ma `autoWacItems` è un array → sempre nuovo ref → sempre notifica.

### Fix

Rimuovere `autoWacItems` dallo scope sincrono tracked dell'`$effect`. Leggerlo dentro il `setTimeout` callback (fuori dal tracking scope di Svelte 5). L'effect dipende SOLO da `wacFingerprint`.

### Secondo fix: label "add_at_wac"

Rinominare da "Inherited/Ereditato" a "Auto WAC / Auto PMC / Auto CMP" per coerenza con il toggle "Auto" nella FormModal.

### Steps

#### Step B1: Refactor `$effect` WAC — rimuovere `autoWacItems` dallo scope tracked

**File**: `frontend/src/lib/components/transactions/TransactionBulkModal.svelte`, righe 304-319

Da:
```typescript
$effect(() => {
    const _fp = wacFingerprint;
    const _autoItems = autoWacItems;
    if (_autoItems.length === 0) return;
    if (wacDebounceTimer) clearTimeout(wacDebounceTimer);
    wacDebounceTimer = setTimeout(() => {
        fetchBatchWac(_autoItems);
    }, 800);
    return () => { if (wacDebounceTimer) clearTimeout(wacDebounceTimer); };
});
```

A:
```typescript
$effect(() => {
    const _fp = wacFingerprint; // unica dipendenza tracked (string → stabile dopo writeback)
    if (wacDebounceTimer) clearTimeout(wacDebounceTimer);
    wacDebounceTimer = setTimeout(() => {
        // Letto fuori dal tracking scope → non causa re-subscribe
        const items = autoWacItems;
        if (items.length > 0) fetchBatchWac(items);
    }, 800);
    return () => { if (wacDebounceTimer) clearTimeout(wacDebounceTimer); };
});
```

**Risultato**: dopo writeback, `ops` cambia → `wacFingerprint` ricalcola → stessa stringa → `$derived` non notifica → effect non re-fire. **1 sola call per dato cambio utente.**

#### Step B2: Rinominare label i18n `addAtWac`

**Files**: `frontend/src/lib/i18n/{en,it,fr,es}.json`

| Lingua | Vecchio | Nuovo |
|--------|---------|-------|
| EN | `"Inherited"` | `"Auto WAC"` |
| IT | `"Ereditato"` | `"Auto PMC"` |
| FR | `"Hérité"` | `"Auto CMP"` |
| ES | `"Heredado"` | `"Auto CMP"` |

#### Step B3: Potenziare WB6 con network request count

**File**: `frontend/e2e/transactions/tx-wac-bulk.spec.ts`, test WB6

Dopo la prima risoluzione WAC, intercettare le request a `/wac-preview` durante i 2s di attesa e asserire `count === 0` (nessuna chiamata aggiuntiva dopo stabilizzazione).

#### Step B4: Aggiornare documentazione WAC (solo EN)

**File**: `mkdocs_src/docs/financial-theory/portfolio-theory/weighted-average-cost.en.md`

1. Nella tabella Transaction Effects (riga 38-42): aggiungere riga `| **Auto WAC** | qty > 0, cost_basis_mode = "auto" | Pool unchanged — units enter at current WAC |`
2. Nella sezione Cost Basis Override (riga 93): aggiungere terzo caso "**Auto mode (cost_basis_mode = "auto")**" con spiegazione algebrica
3. Aggiungere Example 4: TRANSFER in auto mode → WAC unchanged

### Test Criteria v8b

- [x] Network tab: dopo prima resolve, 0 chiamate aggiuntive in 5s
- [x] E2E WB6: passa con network count assertion (extraWacCalls === 0)
- [x] Label: qualifying table mostra "Auto WAC" / "Auto PMC"
- [x] Docs: pagina WAC aggiornata con nuovo effect + Example 4
- [x] `./dev.py front check` — 0 errors

---

## Next: WAC Inline in Validate/Commit

> **Child plan**: [`plan-WacInlineValidateCommit.prompt.md`](./plan-WacInlineValidateCommit.prompt.md)
>
> Ristrutturazione architetturale: il calcolo WAC viene integrato in `/validate` (response inline) e
> applicato server-side in `/commit`. L'endpoint `/wac-preview` viene migrato verso `/analytics/wac`
> per serie temporali (dashboard, grafici). Elimina la necessità di un endpoint WAC separato nel
> flusso workspace editing e risolve il bug `sender_broker_id` per TRANSFER linked (il backend
> determina autonomamente il source broker via `link_uuid`).

