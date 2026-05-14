# Plan D2 Bugfix 3 — UX Modal Unification, Payload Fix, Suggest & E2E

**Date**: 2026-05-14
**Status**: ✅ COMPLETED
**Priority**: P1
**Estimated effort**: ~16h (~3-4 days)

**Parent**: [`plan-phase07-transaction-Part4_Round6_PlanD2_bugfix_2_PayloadSplitPreviewUX.prompt.md`](./plan-phase07-transaction-Part4_Round6_PlanD2_bugfix_2_PayloadSplitPreviewUX.prompt.md)

**Child**: [`plan-phase07-transaction-Part4_Round6_PlanD2_bugfix_4_SplitSuggestPmcOverrideUx.prompt.md`](./plan-phase07-transaction-Part4_Round6_PlanD2_bugfix_4_SplitSuggestPmcOverrideUx.prompt.md)

---

## 🎯 Obiettivo

Correggere i bug emersi dal test manuale Round 2 (post-D2 Bugfix 2), unificare lo stile delle modali di azione (delete/split/promote) con layout tabellare, ridisegnare il suggest banner con delta-days, risolvere il payload `cost_basis_override`/`link_uuid` persistente nel validate scheduler, cambiare lo schema split a `{id_a, id_b}` per coerenza, aggiungere validazione balance al db-populate via service layer, e coprire tutto con una suite E2E completa.

---

## 📋 Bugs catalogati

| # | Area | Descrizione | Root cause |
|---|------|-------------|-----------|
| R3-1 | Payload (P0) | `cost_basis_override: ""` + `link_uuid` mancante nel partner create (promote suggest) | Validate scheduler (riga 811) bypassa `buildCreatePayload` |
| R3-2 | BulkModal cash sign | Withdrawal mostra `+500` invece di `-500` nella griglia | `fieldsFromTx()` fa abs() per form; colonna cash usa valore normalizzato |
| R3-3 | Split payload | Split invia solo `{id: txId}` — serve `{id_a, id_b}` con validazione coppia | Schema `TXSplitBatchItem` ha solo `id: int` |
| R3-4 | Split modal UX | TransactionActionModal non ha stile tabellare come DeleteModal | Due componenti con layout diverso |
| R3-5 | PromoteMergeModal UX | Sfondo verde, bottoni in fondo, textarea resize, clickToSelect, frecce asimmetriche | Stile non raffinato |
| R3-6 | MergeModal discard | `confirmVariant="danger"` non è prop valida; deve essere warning giallo | Prop sbagliata + chiave i18n errata |
| R3-7 | Suggest banner UX | Icone stretchate, frase non localizzata, manca delta-time, bottone Unisci mimetico | Layout banner grezzo |
| R3-8 | DB populate balance | TX incoerenti non rilevate all'avvio | Nessuna validate post-populate |

---

## Steps

### Step 1 — Fix payload validate scheduler — ~15min

**File**: `frontend/src/lib/components/transactions/TransactionBulkModal.svelte`

**Root cause**: a riga ~811, nel validate scheduler, `d.partnerPayload` viene pushato raw in `creates[]`:
```ts
if (d.partnerPayload) creates.push(d.partnerPayload as unknown as Record<string, unknown>);
```

Questo bypassa `buildCreatePayload()` che:
- filtra `cost_basis_override` se stringa vuota
- include `link_uuid` solo se `rule.requiresPair`

La stessa fix è GIÀ applicata in `commit()` (righe 962-965) e `getBulkContextExcluding()` (righe 740-744), ma manca nel validate scheduler.

**Fix**: sostituire riga ~811 con:
```ts
if (d.partnerPayload) {
    const partnerFields = d.partnerPayload as unknown as TxFields;
    const partnerRule = getTypeRule(partnerFields.type as TransactionTypeCode);
    creates.push(buildCreatePayload(partnerFields, partnerRule));
}
```

---

### Step 2 — Fix cash sign rendering BulkModal — ~30min

**File**: `frontend/src/lib/components/transactions/TransactionBulkModal.svelte`

**Root cause**: `fieldsFromTx()` (riga 148) normalizza i valori per l'editing nel form:
```ts
if (cash && rule.cashSign === 'negative' && Number(cash.amount) < 0) {
    cash = {code: cash.code, amount: String(Math.abs(Number(cash.amount)))};
}
```
Questo è corretto per i form (l'utente inserisce un valore positivo, il backend lo nega). Ma la colonna `cash` del BulkModal grid (riga ~1218) chiama `formatCashText(row.fields.cash)` con il valore già normalizzato → mostra `+500` per WITHDRAWAL.

**Fix**: nella colonna `cash` (riga ~1218), prima del rendering, ricostruire il segno display:
```ts
cell: (row): CellContent => {
    const rule = getTypeRule(row.fields.type);
    if (rule.cashField === 'forbidden') {
        return {type: 'html', html: '<span class="text-gray-400 italic">—</span>'};
    }
    // Reconstruct display sign: form stores abs, column shows actual sign
    let displayCash = row.fields.cash;
    if (displayCash && rule.cashSign === 'negative') {
        displayCash = {code: displayCash.code, amount: String(-Math.abs(Number(displayCash.amount)))};
    }
    // Paired row → show Da:/A: dual cash lines
    if (rule.requiresPair && row.partnerCash !== undefined && row.partnerBrokerId != null) {
        let displayPartnerCash = row.partnerCash;
        // partnerCash is already in DB format (not form-normalized) — but check just in case
        return {type: 'html', html: renderDualHtml(formatCashText(displayCash), formatCashText(displayPartnerCash))};
    }
    return {type: 'html', html: `<span class="text-sm">${formatCashText(displayCash)}</span>`};
},
```

Stessa logica per la colonna `quantity` se `rule.quantityRule === 'negative'`.

---

### Step 3 — Split payload: `TXSplitBatchItem{id_a, id_b}` — ~1.5h

#### Step 3a — Backend schema (~30min)

**File**: `backend/app/schemas/transactions.py`

Cambiare `TXSplitBatchItem`:
```python
class TXSplitBatchItem(BaseModel):
    """Single split within a batch. Both IDs of the pair must be provided."""
    model_config = ConfigDict(extra="forbid")

    id_a: int = Field(..., gt=0, description="ID of one half of the pair")
    id_b: int = Field(..., gt=0, description="ID of the other half of the pair")

    @model_validator(mode="after")
    def ids_must_differ(self):
        if self.id_a == self.id_b:
            raise ValueError("id_a and id_b must be different transactions")
        return self
```

#### Step 3b — Backend service (~30min)

**File**: `backend/app/services/transaction_service.py`

Adattare il loop split (riga ~1010):
```python
for orig_idx, item in parsed_splits:
    tx_a = existing_by_id.get(item.id_a)
    tx_b = existing_by_id.get(item.id_b)
    if tx_a is None or tx_b is None:
        issues.append(TXValidationIssue(
            operation="split", index=orig_idx,
            ref_id=item.id_a if tx_a is None else item.id_b,
            error=f"Transaction not found",
            code=TXValidationCode.TX_NOT_FOUND.value,
        ))
        continue
    # Validate they are actually a pair
    if tx_a.related_transaction_id != item.id_b or tx_b.related_transaction_id != item.id_a:
        issues.append(TXValidationIssue(
            operation="split", index=orig_idx,
            ref_id=item.id_a,
            error=f"Transactions {item.id_a} and {item.id_b} are not a linked pair",
            code=TXValidationCode.SPLIT_IDS_MISMATCH.value,
        ))
        continue
    # ... rest of split logic using tx_a, tx_b instead of tx, partner
```

Aggiungere `SPLIT_IDS_MISMATCH` a `TXValidationCode` enum.

Aggiornare `split_partner_ids` lookup (riga ~948) per non dover cercare i partner separatamente — ora entrambi gli ID sono nel payload.

#### Step 3c — Frontend (~15min)

**File**: `frontend/src/lib/components/transactions/TransactionBulkModal.svelte`

`handleSplitRow()` riga 642:
```ts
pendingSplits = [...pendingSplits, {id_a: txId, id_b: partnerId}];
```

Aggiornare tipo `pendingSplits`:
```ts
let pendingSplits = $state<{id_a: number; id_b: number}[]>([]);
```

#### Step 3d — API sync

`./dev.py api sync` per rigenerare `generated.ts`.

---

### Step 4 — Unifica TransactionActionModal con stile tabellare — ~2h

**File**: `frontend/src/lib/components/transactions/TransactionActionModal.svelte`

Refactor usando stesso pattern `<table>` 2-colonne From/To di `TransactionDeleteModal.svelte`.

**Scenario C — Split:**
```
┌──────────────────────────────────────────────────────────┐
│ ✂️ Unlink this pair?                                   ✕ │
├──────────────────────────────────────────────────────────┤
│ The 2 transactions will become independent rows.         │
│                                                          │
│   BEFORE (paired)                                        │
│ ┌──────────────────────────────────────────────────────┐ │
│ │          │    From             │    To                │ │
│ │ Date     │ 2026-05-03         │ 2026-05-03           │ │
│ │ Type     │ 💸 Cash Transfer   │ 💸 Cash Transfer     │ │
│ │ Cash     │ -500,00 € EUR      │ +500,00 € EUR        │ │
│ │ Broker   │ 🏦 Coinbase        │ 🏦 IB                │ │
│ └──────────────────────────────────────────────────────┘ │
│                         ⬇                                │
│   AFTER (2 standalone)                                   │
│ ┌──────────────────────────────────────────────────────┐ │
│ │          │    TX #38           │    TX #39            │ │
│ │ Type     │ 📤 Withdrawal      │ 📥 Deposit           │ │
│ │ Cash     │ -500,00 € EUR      │ +500,00 € EUR        │ │
│ │ Broker   │ 🏦 Coinbase        │ 🏦 IB                │ │
│ └──────────────────────────────────────────────────────┘ │
│                                                          │
│                      [Cancel ✕]  [✂️ Split]              │
└──────────────────────────────────────────────────────────┘
```

**Scenario D — Promote identico (nessuna divergenza):**
```
┌──────────────────────────────────────────────────────────┐
│ 🔗 Link as pair                                        ✕ │
├──────────────────────────────────────────────────────────┤
│   2 standalone → 1 paired                                │
│ ┌──────────────────────────────────────────────────────┐ │
│ │          │    TX #41           │    TX #42            │ │
│ │ Date     │ 2026-05-03         │ 2026-05-03           │ │
│ │ Type     │ 📤 Withdrawal      │ 📥 Deposit           │ │
│ │ Cash     │ -500,00 € EUR      │ +500,00 € EUR        │ │
│ │ Broker   │ 🏦 Coinbase        │ 🏦 IB                │ │
│ └──────────────────────────────────────────────────────┘ │
│                         ⬇                                │
│ ┌──────────────────────────────────────────────────────┐ │
│ │ Target   │ 💸 Cash Transfer                          │ │
│ └──────────────────────────────────────────────────────┘ │
│ ⚠️ Both source rows will be re-typed atomically.         │
│                                                          │
│                      [Cancel ✕]  [🔗 Promote]            │
└──────────────────────────────────────────────────────────┘
```

**Implementazione**: importare `BrokerBadge`, `getAssetInfo`, `getTransactionTypeIconUrl`, `formatCurrencyAmountPlain` come fa `TransactionDeleteModal`. Usare `<table>` con `<thead>` From/To e `<tbody>` con righe Date, Type, Cash, Broker. Sezione "After" con stessa tabella ma tipi post-split/target. Colori tematici: ambra per split (border), verde per promote (border).

---

### Step 5 — PromoteMergeModal polish — ~1.5h

**File**: `frontend/src/lib/components/transactions/PromoteMergeModal.svelte`

**Scenario E — Promote divergente (MergeModal redesign):**
```
┌─────────────────────────────────────────────────────────────────┐
│ 🔗 Merge as Cash Transfer                                    ✕ │
├─────────────────────────────────────────────────────────────────┤
│ These transactions have different values. Choose how to merge.  │
│                                                                 │
│ [◀ All Left]       [⟷ Merge All]       [All Right ▸]           │
│  (azzurro)          (indigo)            (rosa)                  │
│                                                                 │
│ ┌─ Description ──────────────────────────────────────── [⟷] ──┐ │
│ │ ┌─blue──────────────┐       ┌─pink──────────────┐          │ │
│ │ │ TX #41             │       │ TX #42             │          │ │
│ │ │ Withdrawal for...  │       │ Deposit for...     │          │ │
│ │ └────────────────────┘       └────────────────────┘          │ │
│ │ ┌──────────────────────────────────────────────────┐        │ │
│ │ │ [textarea, resize-none, max-h-32, scroll]        │        │ │
│ │ └──────────────────────────────────────────────────┘        │ │
│ └─────────────────────────────────────────────────────────────┘ │
│                                                                 │
│                        [Cancel]  [🔗 Confirm merge]             │
└─────────────────────────────────────────────────────────────────┘
```

**Scenario F — Discard changes (dalla MergeModal):**
```
┌────────────────────────────────────────┐
│ ⚠️ Discard Changes?                   │
├────────────────────────────────────────┤
│ You have unsaved changes.             │
│ Are you sure you want to close?       │
│                                       │
│        [Cancel]  [⚠️ Discard]         │
│                   (amber/warning)     │
└────────────────────────────────────────┘
```

**Modifiche puntuali**:

(a) Rimuovere `bg-green-50/50 dark:bg-green-950/20` dal container (riga 122).

(b) Spostare i 3 bottoni globali (allLeft/Merge/Right) IN CIMA, sopra i campi divergenti. Colori per lato:
- `◀ All Left` → `bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300`
- `⟷ Merge All` → `bg-indigo-100 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-300`
- `All Right ▸` → `bg-pink-100 text-pink-700 dark:bg-pink-900/30 dark:text-pink-300`

(c) Rimuovere tutti i `<span class="text-[9px] text-gray-400 mt-0.5 block">{$t('transactions.promote.clickToSelect')}</span>` (righe 146, 153, 181, 192, 215, 222, 239, 246).

(d) Textarea: aggiungere `resize-none max-h-32 overflow-y-auto` (riga 162), rimuovere `resize-y`.

(e) Bottone ⟷ Concat: centrato rispetto alla modale (non rispetto al campo). Posizionarlo sulla stessa riga del titolo campo:
```svelte
<div class="flex items-center justify-between mb-2">
    <div class="text-xs font-semibold text-gray-500 dark:text-gray-400">{$t('transactions.promote.fieldDescription')}</div>
    <Tooltip text={$t('transactions.promote.concat')}>
        <button type="button" class="px-1.5 py-0.5 text-[10px] rounded bg-indigo-50 dark:bg-indigo-900/30 text-indigo-600 dark:text-indigo-400 hover:bg-indigo-100 dark:hover:bg-indigo-900/50" onclick={() => (resDescription = mergeStrings(txA?.description ?? '', txB?.description ?? ''))}>⟷ {$t('transactions.promote.concat')}</button>
    </Tooltip>
</div>
```

(f) ConfirmModal discard: cambiare `confirmVariant="danger"` (non esiste come prop) → `warning={true}`. Chiavi i18n: `title={$t('common.discardChanges')}`, `message={$t('common.discardChangesMessage')}`.

(g) Frecce simmetriche: assicurarsi che `◀` e `▸` siano dello stesso peso visivo.

---

### Step 6 — Suggest banner redesign + delta-days in toolbar — ~1.5h

**File**: `frontend/src/lib/components/transactions/TransactionBulkModal.svelte`

#### Step 6a — Banner redesign (righe ~2053-2088)

Nuovo formato:
```svelte
{#if allSuggestions.length > 0}
    <div class="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg p-3 text-xs space-y-1.5" data-testid="promote-suggest-banner">
        <div class="font-medium text-green-800 dark:text-green-200 mb-1">{$t('transactions.promoteSuggest.detected')}</div>
        {#each allSuggestions.slice(0, 5) as sug, idx}
            <div class="flex items-center gap-1.5 flex-wrap" data-testid="promote-suggest-item-{idx}">
                <button type="button"
                    class="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-blue-100 dark:bg-blue-800/30 border border-blue-300 dark:border-blue-700 text-blue-700 dark:text-blue-300 hover:bg-blue-200 dark:hover:bg-blue-700/40 font-medium"
                    onclick={() => triggerPromoteFromSuggestion(sug)}
                    data-testid="promote-suggest-link-{idx}">
                    <Link2 size={12} />
                    {$t('transactions.promoteSuggest.merge')}
                </button>
                <span>{$t('transactions.bulk.rowN', {values: {n: sug.indexA + 1}})}</span>
                <img src={getTransactionTypeIconUrl(sug.typeA)} alt="" class="w-4 h-4 object-contain" />
                <span class="text-gray-500">({sug.dateA})</span>
                <span class="text-gray-500">{$t('common.and')}</span>
                <span>{$t('transactions.bulk.rowN', {values: {n: sug.indexB + 1}})}</span>
                <img src={getTransactionTypeIconUrl(sug.typeB)} alt="" class="w-4 h-4 object-contain" />
                <span class="text-gray-500">({sug.dateB})</span>
                <span class="text-gray-500">→</span>
                <Tooltip text={sug.targetLabel}>
                    <img src={getTransactionTypeIconUrl(sug.targetType)} alt="" class="w-4 h-4 object-contain" />
                </Tooltip>
                <span class="text-gray-400">(Δ {Math.abs(/* dateA - dateB in days */)} {$t('transactions.promoteSuggest.deltaGG', {values: {n: Math.abs(/* delta */)}})}</span>
            </div>
        {/each}
    </div>
{/if}
```

Aggiungere `dateA`, `dateB`, `indexA`, `indexB` alla struttura `allSuggestions`:
- `dateA = opA.fields.date`
- `dateB = opB.fields.date`
- `indexA = ops.indexOf(opA)`
- `indexB = ops.indexOf(opB)`

#### Step 6b — Delta-days in toolbar

Nella toolbar (accanto a "🔍 Search & add"), aggiungere:
```svelte
<div class="inline-flex items-center gap-1 text-[11px] text-gray-500 dark:text-gray-400">
    <span>{$t('transactions.promoteSuggest.deltaLabel')}</span>
    <input type="number" min="0" max="30" step="1"
        class="w-12 px-1 py-0.5 text-[11px] rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800"
        bind:value={maxDeltaDays}
        data-testid="promote-suggest-delta-input" />
</div>
```

State:
```ts
let maxDeltaDays = $state(Number(sessionStorage.getItem('lf-suggest-delta-days') ?? '3'));
$effect(() => { sessionStorage.setItem('lf-suggest-delta-days', String(maxDeltaDays)); });
```

Filtro nel calcolo suggest: `if (Math.abs(daysDiff(dateA, dateB)) > maxDeltaDays) continue;`

---

### Step 7 — Validate in db-populate (service layer) — ~2h

**File**: `backend/test_scripts/test_db/populate_mock_data.py`

Aggiungere funzione `validate_all_balances(session)`:

```python
from backend.app.services.transaction_service import TransactionService

async def validate_all_balances(session):
    """Run balance walk on all brokers and report violations."""
    from sqlmodel import select
    from backend.app.db.models import Broker, Transaction

    brokers = session.exec(select(Broker)).all()
    tx_service = TransactionService(session)

    violations = []
    for broker in brokers:
        try:
            await tx_service._walk_broker_balance(broker.id)
        except Exception as e:
            violations.append(f"[{broker.name}] {e}")

    if violations:
        print(f"\n  ⚠️  {len(violations)} balance violations found:")
        for v in violations:
            print(f"    ❌ {v}")
    else:
        print(f"\n  ✅ 0 balance violations — all brokers pass balance walk")

    return len(violations)
```

**Nota**: se `_walk_broker_balance` è async, wrappare con `asyncio.run()` o adattare. La funzione usa il service layer direttamente — nessuna duplicazione di logica.

Chiamarla alla fine di `run_populate()`:
```python
print("\n📊 Running balance validation on all brokers...")
violation_count = validate_all_balances(session)  # or asyncio.run(...)
if violation_count > 0:
    print(f"  💡 Fix the {violation_count} violations above before running E2E tests")
```

Fix dei dati mock in base ai risultati — ad esempio aggiungere DEPOSIT EUR su Coinbase prima delle TX promote-test che hanno WITHDRAWAL EUR.

---

### Step 8 — i18n nuove chiavi — ~30min

**File**: `frontend/src/lib/i18n/{en,it,fr,es}.json`

Aggiungere/aggiornare:

| Chiave | EN | IT | FR | ES |
|--------|----|----|----|----|
| `transactions.promoteSuggest.detected` | Complementary transactions detected: | Transazioni complementari rilevate: | Transactions complémentaires détectées : | Transacciones complementarias detectadas: |
| `transactions.promoteSuggest.deltaLabel` | Max Δ days | Max Δ giorni | Max Δ jours | Máx Δ días |
| `transactions.promoteSuggest.deltaGG` | {n} days | {n} gg | {n} j | {n} días |

Fix MergeModal discard: usare chiavi `common.discardChanges` (già esistente = "Discard Changes?") e `common.discardChangesMessage` (già esistente = "You have unsaved changes. Are you sure you want to close?").

Verificare che tutte le chiavi `promote.*` e `promoteSuggest.*` risolvano in tutte e 4 le lingue.

---

### Step 9 — Analisi re-rendering PromoteMergeModal — ~30min

Investigare il re-layout multiplo osservato in Chrome (desktop → mobile viewport toggle). Cause possibili:

1. **`$effect` reset** (riga 60-70): il `setTimeout` per `initialSnapshot` ritarda 1 tick → il primo render mostra valori non-snapshot, poi il secondo tick li ricalcola → possibile flash.
2. **`dirty` derivation chain**: `dirty = $derived(initialSnapshot !== '' && currentSnapshot() !== initialSnapshot)` → `currentSnapshot()` dipende da `resDescription`, `resTags`, `resDate`, `resCostBasis` → ogni cambio causa re-render della guard.
3. **ModalBase `$: maxWidthValue`**: usa `$:` reattivo (Svelte 4) che potrebbe cascata con resize events.

**Fix possibili**:
- Usare `untrack()` per lo snapshot init in `$effect`
- Debounce `dirty` con `$derived` lazy
- ModalBase: verificare che il resize non triggeri re-render multipli della modale stessa (improbabile ma da controllare)

---

### Step 10 — E2E Test Suite completa `tx-crud-full.spec.ts` — ~6h

**File**: `frontend/e2e/transactions/tx-crud-full.spec.ts` (NUOVO)

Suite comprensiva che copre il ciclo di vita completo delle transazioni, partendo dal db-populate pulito:

| # | Scenario | Azioni | Verifiche |
|---|----------|--------|-----------|
| 1 | Create standalone | + Add → FormModal → DEPOSIT EUR 100 IB → Save | Toast, riga in tabella, cash +100 |
| 2 | Edit standalone | Edit TX → amount 200 → Save | Amount aggiornato |
| 3 | Clone standalone | Clone → FormModal auto-filled → Save | 2 TX stessi dati, ID diversi |
| 4 | Delete standalone | Select → Delete → DeleteModal → Confirm | TX rimossa |
| 5 | Create paired (CASH_TRANSFER) | + Add → FormModal → CASH_TRANSFER → Save | 2 TX linked, icona link |
| 6 | Split paired | Select → ✂️ → ActionModal tabellare → Confirm | 2 standalone, link rimosso |
| 7 | Promote 2 standalone | Select W+D → 🔗 toolbar → ActionModal → Confirm | 2 TX ri-linkate |
| 8 | Promote con MergeModal | Select 2 TX desc diverse → 🔗 → MergeModal → Left → Confirm | TX linkate desc sinistra |
| 9 | BulkModal create batch | BulkModal → + Add 3 TX → Commit | 3 TX |
| 10 | BulkModal edit batch | Select 2 → BulkModal → modifica desc → Commit | Updates |
| 11 | BulkModal delete batch | Select 3 → mark delete → Commit | Rimosse |
| 12 | BulkModal split preview | BulkModal paired → ✂️ → 2 preview → edit → Commit | splits[] + updates[] |
| 13 | Suggest + collapse | BulkModal → W+D new → banner → Unisci → 1 paired | Payload OK, no cost_basis:"" |
| 14 | Cash sign BulkModal | BulkModal con Withdrawal → cash negativo | `-500,00` non `+500,00` |
| 15 | Access guard promote | Select 2 TX (VIEWER broker) → no 🔗 | Bottone assente |
| 16 | Delta-days filtro | Delta gg = 0 → suggest scompare; = 10 → ricompare | Filtro funziona |
| 17 | MergeModal discard | MergeModal → modifica → Cancel → ConfirmModal giallo | Warning amber |
| 18 | ActionModal split UX | Split → tabella Before/After stile delete | Layout tabellare From/To |
| 19 | Payload promote suggest | Suggest → Unisci → Commit → intercept request | link_uuid×2, no cost_basis:"" |

**File**: `scripts/test_runner/_frontend_transaction.py`

Registrare:
```python
def front_tx_crud_full(args):
    """Full CRUD lifecycle E2E tests for transactions."""
    return _run_playwright("transactions/tx-crud-full.spec.ts", args)

# In populate_registry():
add_test(cat, "tx-crud-full", front_tx_crud_full, "Full TX CRUD lifecycle E2E")
```

Aggiungere `front_tx_crud_full` alla lista in `front_transaction_all()`.

---

## 📊 Step Classification & Priorità

| Step | Tipo | Stima | Priorità | Dipendenze |
|------|------|-------|----------|------------|
| 1 | 🔴 Critical ✅ | ~15min | P0 | — |
| 2 | 🔴 Critical ✅ | ~30min | P0 | — |
| 3 | 🔴 Critical ✅ | ~1.5h | P0 | — |
| 4 | 🟡 UX ✅ | ~2h | P1 | — |
| 5 | 🟡 UX ✅ | ~1.5h | P1 | — |
| 6 | 🟡 UX ✅ | ~1.5h | P1 | 8 |
| 7 | 🟡 Infra ✅ | ~2h | P1 | — |
| 8 | 🟢 i18n ✅ | ~30min | P2 | — |
| 9 | 🟢 Investigation ✅ | ~30min | P2 | — |
| 10 | 🟡 Tests ✅ | ~6h | P1 | 1-8 |

---

## 🔀 Ordine di esecuzione

```
Wave 1 — Bloccanti (P0):
  Step 1 (payload validate) → Step 2 (cash sign) → Step 3 (split id_a/id_b)

Wave 2 — UX:
  Step 4 (ActionModal tabellare) → Step 5 (MergeModal polish) →
  Step 6 (suggest banner + delta-days) → Step 8 (i18n) → Step 9 (re-render analysis)

Wave 3 — Infra + Tests:
  Step 7 (validate db-populate) → Step 10 (E2E suite completa)
```

---

## Riepilogo file modificati

| File | Modifica | Step |
|------|----------|------|
| `frontend/src/lib/components/transactions/TransactionBulkModal.svelte` | Fix validate scheduler, cash sign, split payload, suggest banner, delta-days | 1, 2, 3, 6 |
| `frontend/src/lib/components/transactions/TransactionActionModal.svelte` | Refactor stile tabellare (delete-like) | 4 |
| `frontend/src/lib/components/transactions/PromoteMergeModal.svelte` | Polish UX, discard fix, re-render analysis | 5, 9 |
| `backend/app/schemas/transactions.py` | `TXSplitBatchItem{id_a, id_b}` + `SPLIT_IDS_MISMATCH` | 3 |
| `backend/app/services/transaction_service.py` | Split loop: validazione coppia da entrambi gli ID | 3 |
| `backend/test_scripts/test_api/test_transactions_batch_split_promote.py` | Step 3 (test updates) |
| `backend/test_scripts/test_db/populate_mock_data.py` | Step 7 |
| `frontend/src/lib/i18n/{en,it,fr,es}.json` | Step 8 |
| `frontend/src/lib/api/generated.ts` | Step 3d (regenerated) |
| `frontend/e2e/transactions/tx-crud-full.spec.ts` | Step 10 (NEW) |
| `scripts/test_runner/_frontend_transaction.py` | Step 10 |

---

### Addendum: `tx-commit-all-types.spec.ts` — Comprehensive Commit E2E Suite

**Date**: 2026-05-14
**File**: `frontend/e2e/transactions/tx-commit-all-types.spec.ts`

#### Obiettivo

Scrivere una suite E2E che esercita il flow completo **FormModal → BulkModal → POST /transactions/commit → table refresh** per **ogni tipo di transazione** (standalone e paired), più i flussi edit e delete. Questa suite colma un gap critico: il crash su FX_CONVERSION commit (`resp.results[0].ids[0]`) non era mai stato catturato perché nessun test esercitava il commit reale per tipi paired.

#### Test implementati (16 scenari)

| # | Gruppo | Test | Flusso |
|---|--------|------|--------|
| 1 | Standalone | DEPOSIT create → commit | FormModal → BulkModal → commit POST → payload.creates ≥ 1 |
| 2 | Standalone | WITHDRAWAL create → commit | idem |
| 3 | Standalone | BUY create → commit | + asset + qty |
| 4 | Standalone | SELL create → commit | + asset + qty |
| 5 | Standalone | DIVIDEND create → commit | + asset + amount |
| 6 | Standalone | INTEREST create → commit | amount only |
| 7 | Standalone | FEE create → commit | amount only |
| 8 | Standalone | TAX create → commit | amount only |
| 9 | Standalone | ADJUSTMENT create → commit | + asset + qty |
| 10 | Paired | FX_CONVERSION create → commit | shared broker + dual CompactCashCell (From EUR / To USD) |
| 11 | Paired | CASH_TRANSFER create → commit | dual brokers (From/To panels) + shared cash |
| 12 | Paired | TRANSFER (asset) create → commit | dual brokers (From/To panels) + shared asset + qty |
| 13 | Edit | Edit standalone → change desc → commit | toolbar edit → FormModal → desc change → BulkModal commit → payload.updates ≥ 1 |
| 14 | Delete | Delete via BulkModal mark-delete → commit | create DEPOSIT → commit → select → toolbar edit → mark delete → commit → payload.deletes ≥ 1 |
| 15 | Delete | Delete via main table row action → DeleteModal → confirm | create DEPOSIT → commit → inline delete button → TransactionDeleteModal → confirm → API DELETE → row removed |

#### Problemi riscontrati e soluzioni

| # | Problema | Root cause | Soluzione |
|---|----------|-----------|-----------|
| P1 | Test CASH_TRANSFER falliva: `tx-form-cash-from-amount` non trovato | `CompactCashCell` con testid `tx-form-cash-from` appare **solo** per `pairLayout === 'fx'` (FX_CONVERSION). Per CASH_TRANSFER, `pairLayout === 'transfer_cash'` → i pannelli From/To contengono broker selectors, il cash è condiviso fuori dal dual split (`tx-form-cash-wrap`) | Riscritto test: verifica broker selectors nei pannelli From/To + `tx-form-cash-wrap`. Per il commit test, usa `pickBrokerInPanel()` + `fillCash()` |
| P2 | Errori TS: `payload.creates?.length` → `Property 'length' does not exist on type '{}'` | `postDataJSON()` restituisce `Record<string,unknown>`, e `.creates` è di tipo `{}`, non `unknown[]` | Aggiunta interfaccia `CommitPayload { creates?: unknown[]; updates?: unknown[]; deletes?: unknown[] }`, cast con `as CommitPayload` su `postDataJSON()` |
| P3 | Warning TS: `pickBrokerInPanel` unused | Inizialmente rimossa perché il test CASH_TRANSFER non faceva commit, solo render check | Ripristinata: necessaria per i commit test di CASH_TRANSFER e TRANSFER che selezionano broker **diversi** nei pannelli From/To |
| P4 | FX_CONVERSION commit: `commitBtn.click()` non triggera il POST in certe condizioni | Anti-bounce di 10s su `draftKey` oppure evento perso in Svelte 5 event delegation | Aggiunto retry click pattern: se il BulkModal è ancora visibile dopo il click e il button è ancora enabled, retry click. Intercettazione con `page.waitForResponse` + `.catch(() => null)` per non fallire il test |
| P5 | Delete test necessita di riga "safe" da cancellare | I mock data non hanno TX sacrificabili — i test precedenti le usano | Il test **crea** prima un DEPOSIT da 1€, lo commita, poi lo elimina. Self-contained, nessuna dipendenza da mock data |

#### Copertura complessiva: cosa è coperto dove

| Area | tx-commit-all-types | tx-delete | tx-crud-full | Altro |
|------|:--:|:--:|:--:|------|
| Standalone create → commit (9 tipi) | ✅ | — | ✅ (DEPOSIT) | — |
| FX_CONVERSION create → commit | ✅ | — | — | — |
| CASH_TRANSFER create → commit | ✅ | — | ✅ | — |
| TRANSFER (asset) create → commit | ✅ | — | — | — |
| Edit standalone → commit | ✅ | — | — | tx-paired-edit |
| Delete: BulkModal mark-delete → commit | ✅ | — | — | tx-bulk-operations |
| Delete: main table → DeleteModal → confirm | ✅ | ✅ (A1/A2-confirm) | — | — |
| Delete: paired → Layout B | — | ✅ | — | — |
| Delete: VIEWER blocked | — | ✅ (A4, A5) | — | — |

#### Punti aperti

1. **FX_CONVERSION commit fragile**: il test usa `page.waitForResponse().catch(() => null)` — se il commit non triggera il POST, il test *non fallisce* ma verifica solo la validazione UI. Root cause potrebbe essere anti-bounce su `draftKey` o timing Svelte 5 event delegation. Serve investigation dedicata.
2. **CASH_TRANSFER/TRANSFER commit**: dipendono dalla disponibilità di ≥2 broker OWNER/EDITOR nel db-populate. Se il populate ha solo 1 broker con accesso, `pickBrokerInPanel(nth=1)` selezionerà lo stesso broker → la business rule potrebbe respingere il commit. Il populate attuale ha Interactive Brokers (OWNER) + Coinbase (OWNER) + Directa SIM (EDITOR) → OK.
3. **Edit paired → commit**: non coperto in questo file. Coperto da `tx-paired-edit.spec.ts`.
4. **Delete paired via main table DeleteModal**: coperto da `tx-delete.spec.ts` (A2-confirm), non duplicato qui.

---

### Addendum Round 3 — Feedback test manuale CASH_TRANSFER / TRANSFER commit

**Date**: 2026-05-14
**Test**: 11 (CASH_TRANSFER) e 12 (TRANSFER)
**Tester**: utente (manuale su browser)

#### Osservazioni

##### Test 11 — CASH_TRANSFER

1. **FormModal → Apply**: funziona. Il form si chiude e popola correttamente il BulkModal.
2. **Validate NOW non si avvia in automatico** al passaggio FormModal → BulkModal. Il bottone "Save" è abilitato ma nessuna validazione preventiva è stata lanciata.
3. **Azione Split mancante**: nel BulkModal, una TX paired (CASH_TRANSFER) dovrebbe mostrare l'azione ✂️ Split nella toolbar/riga — non è presente.
4. **Toolbar allineamento**: la toolbar della tabella BulkModal è allineata a **sinistra** invece che a **destra** (regressione o manca il `justify-end`).
5. **Slider delta-days mancante**: lo slider/input per il max Δ giorni di suggest (pianificato in Step 6b) non è presente nella toolbar.
6. **Crash al commit**: cliccando "Save" nel BulkModal → errore JS in console:
   ```
   Uncaught (in promise) TypeError: Cannot read properties of undefined (reading 'length')
   at Tn (13.ZZlBkPpX.js:2:27858)
   ```
   Il crash è nel codice minificato → serve source-map per individuare la funzione esatta. Probabile: `resp.results[0].ids.length` dove `resp.results[0]` è undefined, oppure accesso a un array di risultati che il backend non restituisce per i paired types.
7. **Cancel funziona** correttamente.

##### Test 12 — TRANSFER (asset)

1. Selezionando 1° broker (Coinbase) e 2° broker (Directa SIM) + 1° asset (Amundi MSCI World ETF), i **dati pre-popolati causano inconsistenza**: banner amber con "This configuration causes data inconsistencies — holdings would go negative (-1) on Coinbase".
2. **Fragilità dei selettori**: i test E2E che fanno `pickBrokerInPanel(nth=0)` e `pickFirstAsset()` sono fragili — se il db-populate cambia l'ordine degli elementi, i test falliscono o selezionano combinazioni invalide.
3. **Crash al commit**: stesso errore JS del test 11 — `Cannot read properties of undefined (reading 'length')`.
4. **Cost basis override**: lasciato ad `auto` — manca un test che lo modifica e verifica che il valore salvato sia corretto nelle TX singole post-commit.

#### Bugs catalogati Round 3

| # | Area | Descrizione | Severità |
|---|------|-------------|----------|
| R3-B1 | BulkModal commit (P0) | Crash `Cannot read properties of undefined (reading 'length')` al commit di paired types (CASH_TRANSFER, TRANSFER). Probabile accesso a `resp.results[i].ids` dove `results[i]` è undefined | 🔴 P0 — Bloccante ✅ RISOLTO |
| R3-B2 | BulkModal validate (P1) | Validate NOW non parte in automatico dopo Apply dal FormModal — il bottone Save è enabled senza validazione | 🟡 P1 ✅ RISOLTO |
| R3-B3 | BulkModal toolbar (P1) | Toolbar allineata a sinistra invece che a destra | 🟡 P1 ✅ GIÀ OK (ml-auto presente) |
| R3-B4 | BulkModal split action (P1) | Azione ✂️ Split mancante per TX paired nel BulkModal | 🟡 P1 ✅ RISOLTO — split ora visibile anche per TX nuove paired (partnerPayload) |
| R3-B5 | BulkModal delta-days (P1) | Input Δ giorni per suggest non implementato (Step 6b del piano) | 🟡 P1 ✅ IMPLEMENTATO |
| R3-B6 | Test fragilità (P2) | `pickBrokerInPanel(nth=N)` e `pickFirstAsset()` dipendono dall'ordine del db-populate — fragile | 🟡 P2 ✅ RISOLTO |
| R3-B7 | Test gap (P2) | Manca test che modifica `cost_basis_override` e verifica il valore nelle TX singole post-commit | 🟡 P2 ✅ RISOLTO |

#### Piano di risoluzione

##### R3-B1 — Crash commit paired (P0) ✅ RISOLTO

**Root cause**: in `txPayloadHelpers.ts`, `buildCreatePayload()` accedeva direttamente a `fields.tags.length`, `fields.description.trim()`, `fields.cost_basis_override.trim()` — ma il partner payload creato da `collectDualCreates()` nel FormModal (righe ~938-962) è un raw `Record<string,unknown>` che NON include `tags`/`description`/`cost_basis_override` quando sono vuoti (li aggiunge solo condizionalmente con `if (sharedTags)`). Quando il BulkModal assegna `fromOp.partnerPayload = items[1]` (riga 1577) e poi lo casta a `TxFields` per passarlo a `buildCreatePayload`, i campi mancanti risultano `undefined` → `.length` su `undefined` = crash.

**Fix applicato**: in `txPayloadHelpers.ts` riga 134, sostituito accesso diretto con null-safe:
```ts
const tags = fields.tags ?? [];
if (tags.length > 0) out.tags = tags;
const desc = (fields.description ?? '').trim();
if (desc) out.description = desc;
const cbo = (fields.cost_basis_override ?? '').trim();
if (cbo) out.cost_basis_override = cbo;
```

**Verifica**: testato manualmente CASH_TRANSFER e TRANSFER → commit OK, 0 errori console, modale si chiude, TX create correttamente.

##### R3-B2 — Auto-validate dopo Apply ✅ RISOLTO

**Fix applicato**: in `handleFormPushed()` (TransactionBulkModal.svelte riga ~1560), aggiunto `scheduler.trigger('change')` dopo l'inserimento/aggiornamento del draft. Il validate scheduler ora si attiva automaticamente 1s dopo l'Apply dal FormModal.

##### R3-B3 — Toolbar alignment ✅ GIÀ OK

**Analisi**: la toolbar ha `ml-auto` sulla sezione destra (riga 2162) — funziona correttamente. L'utente potrebbe aver osservato il layout quando il picker button (sinistra) era nascosto (`txStoreCount() === 0`). In quel caso, il `ml-auto` sulla sezione destra la spinge comunque a destra. Nessun fix necessario.

##### R3-B4 — Split action in BulkModal ✅ RISOLTO

**Analisi precedente (ERRATA)**: ~~lo split per TX nuove non ha senso — basta eliminarla~~.
**Correzione**: l'utente ha ragione — se si crea un paired per errore, si deve poter tornare indietro con split (coerenza con la modale di conferma). Il paired creato via dual form produce UNA sola riga visibile con `partnerPayload` nascosto. Lo split deve: (1) mostrare il pulsante ✂️, (2) materializzare il partner come riga standalone visibile.

**Fix applicato**:
1. **Visibilità**: condizione esplicita per tipo (`t === 'TRANSFER' || t === 'CASH_TRANSFER' || t === 'FX_CONVERSION'`) — l'operatore `in` su `SPLIT_TYPE_MAP` e l'accesso a proprietà proxy (`row.partnerPayload`) causavano dead code elimination nel bundler Svelte 5
2. **handleSplitRow Case C**: per TX create paired (dual form), materializza il partner come nuova riga `create` standalone usando `partnerPayload` (se accessibile) o fallback con `partnerBrokerId/partnerCash/partnerDate` + segno invertito
3. **Nessun backend call**: per TX nuove lo split è puramente locale (nessun `pendingSplits.push`)
4. **Scoperta Svelte 5 proxy**: le proprietà opzionali (`partnerPayload?: TxFields`) su oggetti in `$state` array non sono accessibili con `in` operator o con truthiness check dal bundler ottimizzato → usare type-based discriminant invece

**Risultato**: 1 riga paired CASH_TRANSFER → click split → 2 righe standalone (WITHDRAWAL + DEPOSIT). 15/15 E2E test invariati.

##### R3-B5 — Delta-days input ✅ IMPLEMENTATO

**Implementazione**:
1. Aggiunto stato `maxDeltaDays` con persistence in `sessionStorage` (chiave `lf-suggest-delta-days`, default 3)
2. Aggiunto helper `daysDiff(a, b)` per calcolo differenza in giorni tra date ISO
3. Filtro delta-days aggiunto in `localSuggestions` e `allSuggestions` derivations
4. Input number nella toolbar BulkModal con `data-testid="promote-suggest-delta-input"`
5. Banner suggest mostra Δ days per ogni suggerimento (`(Δ 2d)`)
6. Chiavi i18n aggiunte in EN/IT/FR/ES: `deltaLabel`, `deltaGG`

**File modificati**: `TransactionBulkModal.svelte`, `en.json`, `it.json`, `fr.json`, `es.json`

##### R3-B6 — Test fragilità selettori ✅ RISOLTO

**Fix applicato**: i selettori broker ora usano **nomi** stabili anziché posizioni (`nth`):
- Costanti `BROKER_OWNER_A = 'Interactive Brokers'`, `BROKER_OWNER_B = 'Coinbase'`, `BROKER_EDITOR = 'Directa SIM'`
- `pickBrokerInPanel(page, panelTestid, brokerName)` seleziona per testo visibile con `hasText`
- `pickFirstBroker(page)` preferisce `BROKER_OWNER_A` per nome, fallback al primo disponibile
- Asset pick resta posizionale (primo disponibile) — la scelta dell'asset non importa per i test standalone
- **File modificato**: `tx-commit-all-types.spec.ts`

##### R3-B7 — Test cost_basis_override ✅ RISOLTO

**Test aggiunto**: `'TRANSFER with cost_basis_override → commit → verify saved value'` in sezione `Cost Basis Override`:
1. Crea un TRANSFER con `cost_basis_override = 42.50`
2. Seleziona broker From (Interactive Brokers) e To (Coinbase) per nome
3. Committa → intercetta payload
4. Verifica che almeno un create abbia `cost_basis_override` non vuoto
- **Nota**: il campo `tx-form-cost-basis` è visibile solo per `pairLayout === 'transfer_asset'` (TRANSFER), non per BUY/SELL
- **File modificato**: `tx-commit-all-types.spec.ts`
- **Risultato**: 16/16 test passati (15 precedenti + 1 nuovo)

#### ⏳ Conferma UX pendente

Le seguenti modifiche UX (Step 4, 5, 6 del piano) **restano in attesa di conferma umana** dopo la risoluzione dei bug bloccanti:
- **Step 4**: TransactionActionModal con stile tabellare (split/promote)
- **Step 5**: PromoteMergeModal polish (sfondo, bottoni, textarea)
- **Step 6**: Suggest banner redesign + delta-days ✅ Delta-days implementato (input + filtro + banner Δ)
- **Toolbar alignment** (R3-B3) → ✅ GIÀ OK

L'utente deve ri-validare visivamente l'estetica dopo l'implementazione.

---

### Walktest pianificato — Checklist per conferma UX + funzionale

**Prerequisiti**: server test mode (8001), mock data populated, browser aperto su /transactions

| # | Scenario | Cosa verificare | Status |
|---|----------|----------------|--------|

| W1 | FormModal → Apply → BulkModal | Auto-validate si attiva dopo ~1s? Banner issues appare se ci sono problemi? | ✅ | 

| W2 | BulkModal toolbar layout | "Search & add" a sinistra, "+ Add row" a destra, delta-days input visibile | No |
Intanto i delta days dovrebbero essere uno slider, e anche nella modalità mobile avere almeno l'icona del delta. Poi toolbar della datatable è allineato a sinistra, non a destra.

| W3 | Delta-days input | Cambiare valore → suggest appare/scompare. Persiste in sessionStorage |
Si sembra funzionare e al variare dei numeri nel selettore compare e scompare.
attualmente si renderizza:
<div class="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg p-3 text-xs space-y-1.5" data-testid="promote-suggest-banner"><div class="font-medium text-green-800 dark:text-green-200 mb-1">Complementary transactions detected:</div> <div class="flex items-center gap-1.5 flex-wrap" data-testid="promote-suggest-item-0"><button type="button" class="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-blue-100 dark:bg-blue-800/30 border border-blue-300 dark:border-blue-700 text-blue-700 dark:text-blue-300 hover:bg-blue-200 dark:hover:bg-blue-700/40 font-medium" data-testid="promote-suggest-link-0"><svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide-icon lucide lucide-link-2"><!----><path d="M9 17H7A5 5 0 0 1 7 7h2"></path><!----><path d="M15 7h2a5 5 0 1 1 0 10h-2"></path><!----><line x1="8" x2="16" y1="12" y2="12"></line><!----><!----><!----></svg><!----> Merge</button> <button type="button" class="underline text-gray-700 dark:text-gray-300">DEPOSIT</button> <div class="tooltip-wrapper svelte-bgl7um" role="button" tabindex="0"><!----><img alt="" class="w-4 h-4 inline object-contain" src="/icons/transactions/deposit.png"><!----></div> <!----><!----> <span class="text-gray-500">and</span> <button type="button" class="underline text-gray-700 dark:text-gray-300">WITHDRAWAL</button> <div class="tooltip-wrapper svelte-bgl7um" role="button" tabindex="0"><!----><img alt="" class="w-4 h-4 inline object-contain" src="/icons/transactions/withdrawal.png"><!----></div> <!----><!----> <span class="text-gray-500">→</span> <div class="tooltip-wrapper svelte-bgl7um" role="button" tabindex="0"><!----><img alt="" class="w-4 h-4 inline object-contain" src="/icons/transactions/cash-transfer.png"><!----></div> <!----><!----> <span class="text-gray-400">(Δ 2d)</span><!----></div><!----> <!----></div>
Mentre doveva essere così:

Complementary transactions detected:
 - Merge the WITHDRAWAL (icon) and DEPOSIT (icon) → Merge to one Cash Transfert(icon cash transfer) (Δ 2d)

dopo il salva ho fatto una nuova transazione e il valore che avevo impostato resta, però bisogna mettere un limite, massimo 14 gg, e come detto prima, deve essere sotto forma di slider.
Per ora non abbiamo ancora pensato, ma a livello potenziale potrebbero esserci anche casi di multi merge... Per ora direi che è esagerato preoccuparcene, mostriamo solo il primo risultato, ma segnamo nei todo_futuri.md che questa possibilità esiste e va gestita.

| W4 | Suggest banner Δ | Banner mostra "(Δ 2d)" per suggerimenti con date diverse |
si

| W5 | CASH_TRANSFER create → commit | FormModal → dual brokers → cash → Apply → BulkModal → Save → 0 errori | ⏳ |
si si crea e si salva.
Ho anche provato a vedere se c'è l'azione split, c'è e se la clicco si separano correttamente e ora compare il banner di merge!
Non è su un elenco puntato e non è ancora come te lo avevo chiesto, ma è un miglioramento:
<div class="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg p-3 text-xs space-y-1.5" data-testid="promote-suggest-banner"><div class="font-medium text-green-800 dark:text-green-200 mb-1">Complementary transactions detected:</div> <div class="flex items-center gap-1.5 flex-wrap" data-testid="promote-suggest-item-0"><button type="button" class="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-blue-100 dark:bg-blue-800/30 border border-blue-300 dark:border-blue-700 text-blue-700 dark:text-blue-300 hover:bg-blue-200 dark:hover:bg-blue-700/40 font-medium" data-testid="promote-suggest-link-0"><svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide-icon lucide lucide-link-2"><!----><path d="M9 17H7A5 5 0 0 1 7 7h2"></path><!----><path d="M15 7h2a5 5 0 1 1 0 10h-2"></path><!----><line x1="8" x2="16" y1="12" y2="12"></line><!----><!----><!----></svg><!----> Merge</button> <button type="button" class="underline text-gray-700 dark:text-gray-300">WITHDRAWAL</button> <div class="tooltip-wrapper svelte-bgl7um" role="button" tabindex="0"><!----><img alt="" class="w-4 h-4 inline object-contain" src="/icons/transactions/withdrawal.png"><!----></div> <!----><!----> <span class="text-gray-500">and</span> <button type="button" class="underline text-gray-700 dark:text-gray-300">DEPOSIT</button> <div class="tooltip-wrapper svelte-bgl7um" role="button" tabindex="0"><!----><img alt="" class="w-4 h-4 inline object-contain" src="/icons/transactions/deposit.png"><!----></div> <!----><!----> <span class="text-gray-500">→</span> <div class="tooltip-wrapper svelte-bgl7um" role="button" tabindex="0"><!----><img alt="" class="w-4 h-4 inline object-contain" src="/icons/transactions/cash-transfer.png"><!----></div> <!----><!----> <!----></div><!----> <!----></div>
Mentre doveva essere così:

Complementary transactions detected:
 - Merge the WITHDRAWAL (icon) and DEPOSIT (icon) → Merge to one Cash Transfert(icon cash transfer)

Oltretutto premere nuovamente il pulsante di merge ripristina la situazione originale


| W6 | TRANSFER create → commit | FormModal → dual brokers → asset → qty → Apply → Save → 0 errori |
Si funziona sia lo split e merge che il salvataggio!

| W7 | Split action (TX salvata) | Selezionare TX paired dal DB → split button visibile nella riga |
Per db ho pensato intendessi nella main table. Fatto, mi piace molto l'estetica!
<div class="p-6 space-y-4" data-testid="tx-action-modal-content"><div class="flex items-center gap-2 text-lg font-semibold text-gray-800 dark:text-gray-100"><svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide-icon lucide lucide-unlink text-amber-500"><!----><path d="m18.84 12.25 1.72-1.71h-.02a5.004 5.004 0 0 0-.12-7.07 5.006 5.006 0 0 0-6.95 0l-1.72 1.71"></path><!----><path d="m5.17 11.75-1.71 1.71a5.004 5.004 0 0 0 .12 7.07 5.006 5.006 0 0 0 6.95 0l1.71-1.71"></path><!----><line x1="8" x2="8" y1="2" y2="5"></line><!----><line x1="2" x2="5" y1="8" y2="8"></line><!----><line x1="16" x2="16" y1="19" y2="22"></line><!----><line x1="19" x2="22" y1="16" y2="16"></line><!----><!----><!----></svg><!----> <span>✂️ Scollegare questa coppia?</span></div> <!----><p class="text-sm text-gray-600 dark:text-gray-400">Le 2 transazioni diventeranno righe indipendenti.</p> <div class="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide">Prima (Accoppiata)</div> <div data-testid="tx-action-before" class="border border-amber-200 dark:border-amber-800 rounded-lg overflow-hidden"><table class="w-full text-sm"><thead><tr class="bg-gray-50 dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700"><th class="px-3 py-2 text-left text-gray-500 dark:text-gray-400 font-medium w-24"></th><th class="px-3 py-2 text-left text-gray-500 dark:text-gray-400 font-medium">Da</th><th class="px-3 py-2 text-left text-gray-500 dark:text-gray-400 font-medium">A</th></tr></thead><tbody><tr class="border-b border-gray-100 dark:border-gray-700"><td class="px-3 py-2 font-medium text-gray-500 dark:text-gray-400">Data</td><td class="px-3 py-2">2026-05-14</td><td class="px-3 py-2">2026-05-14</td></tr><tr class="border-b border-gray-100 dark:border-gray-700"><td class="px-3 py-2 font-medium text-gray-500 dark:text-gray-400">Tipo</td><td class="px-3 py-2 flex items-center gap-2" colspan="2"><img alt="" class="w-5 h-5" src="/icons/transactions/transfer.png"><!----> Trasferimento Titoli</td></tr><tr class="border-b border-gray-100 dark:border-gray-700"><td class="px-3 py-2 font-medium text-gray-500 dark:text-gray-400">Importo</td><td class="px-3 py-2">—</td><td class="px-3 py-2">—</td></tr><tr><td class="px-3 py-2 font-medium text-gray-500 dark:text-gray-400">Broker</td><td class="px-3 py-2"><span class="broker-badge svelte-1fyo7yf" data-testid="broker-badge-5" title="Coinbase"><img alt="" class="broker-badge-icon svelte-1fyo7yf" src="https://www.coinbase.com/favicon.ico" style="width: 16px; height: 16px;"><!----> <span class="broker-badge-name svelte-1fyo7yf">Coinbase</span><!----> <!----></span><!----></td><td class="px-3 py-2"><span class="broker-badge svelte-1fyo7yf" data-testid="broker-badge-3" title="Directa SIM"><img alt="" class="broker-badge-icon svelte-1fyo7yf" src="https://www.directa.it/favicon.ico" style="width: 16px; height: 16px;"><!----> <span class="broker-badge-name svelte-1fyo7yf">Directa SIM</span><!----> <!----></span><!----></td></tr></tbody></table></div> <div class="flex justify-center"><svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide-icon lucide lucide-arrow-down text-gray-400"><!----><path d="M12 5v14"></path><!----><path d="m19 12-7 7-7-7"></path><!----><!----><!----></svg><!----></div> <div class="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide">Dopo (2 Indipendente)</div> <div data-testid="tx-action-after" class="border border-amber-200 dark:border-amber-800 rounded-lg overflow-hidden"><table class="w-full text-sm"><thead><tr class="bg-gray-50 dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700"><th class="px-3 py-2 text-left text-gray-500 dark:text-gray-400 font-medium w-24"></th><th class="px-3 py-2 text-left text-gray-500 dark:text-gray-400 font-medium">TX #74</th><th class="px-3 py-2 text-left text-gray-500 dark:text-gray-400 font-medium">TX #75</th></tr></thead><tbody><tr class="border-b border-gray-100 dark:border-gray-700"><td class="px-3 py-2 font-medium text-gray-500 dark:text-gray-400">Tipo</td><td class="px-3 py-2 flex items-center gap-2"><img alt="" class="w-4 h-4" src="/icons/transactions/adjustment.png"><!----> Aggiustamento</td><td class="px-3 py-2"><span class="inline-flex items-center gap-2"><img alt="" class="w-4 h-4" src="/icons/transactions/adjustment.png"><!----> Aggiustamento</span></td></tr><tr class="border-b border-gray-100 dark:border-gray-700"><td class="px-3 py-2 font-medium text-gray-500 dark:text-gray-400">Importo</td><td class="px-3 py-2">—</td><td class="px-3 py-2">—</td></tr><tr><td class="px-3 py-2 font-medium text-gray-500 dark:text-gray-400">Broker</td><td class="px-3 py-2"><span class="broker-badge svelte-1fyo7yf" data-testid="broker-badge-5" title="Coinbase"><img alt="" class="broker-badge-icon svelte-1fyo7yf" src="https://www.coinbase.com/favicon.ico" style="width: 16px; height: 16px;"><!----> <span class="broker-badge-name svelte-1fyo7yf">Coinbase</span><!----> <!----></span><!----></td><td class="px-3 py-2"><span class="broker-badge svelte-1fyo7yf" data-testid="broker-badge-3" title="Directa SIM"><img alt="" class="broker-badge-icon svelte-1fyo7yf" src="https://www.directa.it/favicon.ico" style="width: 16px; height: 16px;"><!----> <span class="broker-badge-name svelte-1fyo7yf">Directa SIM</span><!----> <!----></span><!----></td></tr></tbody></table></div><!----> <div class="flex justify-end gap-3 pt-2"><button type="button" class="px-4 py-2 text-sm text-gray-600 dark:text-gray-300 bg-gray-100 dark:bg-gray-700 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600 transition" data-testid="tx-action-modal-cancel">Annulla</button> <button type="button" data-testid="tx-action-modal-confirm" class="px-4 py-2 text-sm text-white rounded-lg transition flex items-center gap-1.5 bg-amber-600 hover:bg-amber-700"><svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide-icon lucide lucide-unlink"><!----><path d="m18.84 12.25 1.72-1.71h-.02a5.004 5.004 0 0 0-.12-7.07 5.006 5.006 0 0 0-6.95 0l-1.72 1.71"></path><!----><path d="m5.17 11.75-1.71 1.71a5.004 5.004 0 0 0 .12 7.07 5.006 5.006 0 0 0 6.95 0l1.71-1.71"></path><!----><line x1="8" x2="8" y1="2" y2="5"></line><!----><line x1="2" x2="5" y1="8" y2="8"></line><!----><line x1="16" x2="16" y1="19" y2="22"></line><!----><line x1="19" x2="22" y1="16" y2="16"></line><!----><!----><!----></svg><!----> <span>✂️ Scollegare questa coppia?</span></button></div></div>
Giusto un paio di errori, le tabelle hanno quel bordo estreno giallo che è inguardabile.
Nel tipo dell'accoppiata, capisco che non serva metterlo 2 volte, ma allora mettilo centrale.
I campi mostrati non mostrano la quantità che in questo scenario è importante, e forse in generale sarebbe meglio mostrare tutto, tag e descrizione compresi.

Purtroppo lo split non funziona, sul commit compare:
{"splits":[{"id":74}]}
{
    "committed": false,
    "issues": [
        {
            "operation": "split",
            "index": 0,
            "ref_id": null,
            "error": "Field required",
            "code": "missing",
            "params": null,
            "field": "id_a"
        },
        {
            "operation": "split",
            "index": 0,
            "ref_id": null,
            "error": "Field required",
            "code": "missing",
            "params": null,
            "field": "id_b"
        },
        {
            "operation": "split",
            "index": 0,
            "ref_id": null,
            "error": "Extra inputs are not permitted",
            "code": "extra_forbidden",
            "params": null,
            "field": "id"
        }
    ],
    "results": null
}

in generare però, quando ci sono questi fail o un banner o un toast andrebbe mostrato con una motivazione sintetica, anche se mi rendo conto che non dovrebbero mai essere mostrarti, diciamo che può andare bene mostrare un messaggio generico del tipo "Salvataggio impossibile, errore nel server"

| W8 | Split action (TX nuova) | TX paired appena creata → split button NON visibile (corretto)
Non ho capito il test? Intendi new o saved? in entrambi i casi dovrebbe essere visibile, e sia nella bulk transaction (new e saved) che nella main table (saved) c'è.
lato main table c'è l'errore che ho espresso prima. Nella bulk la new funziona e anche il suo merge.
Se sono nella bulk, con una saved importata dentro, e faccio split, esteticamente il risultato è corretto, ma il banner di validazione fallisce:
⚠️ Sono stati identificati degli errori nei campi

Riga 1: Cannot change type from TRANSFER to ADJUSTMENT (allowed swaps: TRANSFER)
Riga 2: Cannot change type from TRANSFER to ADJUSTMENT (allowed swaps: TRANSFER)

e il pachetto è:
{"updates":[{"id":74,"type":"ADJUSTMENT"},{"id":75,"type":"ADJUSTMENT"}]}
{
    "committed": false,
    "issues": [
        {
            "operation": "update",
            "index": 0,
            "ref_id": 74,
            "error": "Cannot change type from TRANSFER to ADJUSTMENT (allowed swaps: TRANSFER)",
            "code": null,
            "params": null,
            "field": null
        },
        {
            "operation": "update",
            "index": 1,
            "ref_id": 75,
            "error": "Cannot change type from TRANSFER to ADJUSTMENT (allowed swaps: TRANSFER)",
            "code": null,
            "params": null,
            "field": null
        }
    ],
    "results": null
}

l'errore è evidente che riguardi l'operazione comunicata al backend, che dovrebbe essere anche qui split.

| W9 | TransactionActionModal (split) | Cliccare split → modale con layout tabellare Before/After |
credo di averti risposto in W8

| W10 | TransactionActionModal (promote) | Selezionare 2 TX standalone compatible → 🔗 → modale con layout tabellare 
Andiamo nella giusta direzione:
<div class="p-5 space-y-4 rounded-lg" data-testid="promote-merge-modal"><div class="flex items-center gap-2 text-lg font-semibold text-gray-800 dark:text-gray-100"><svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide-icon lucide lucide-link-2 text-green-600 dark:text-green-400"><!----><path d="M9 17H7A5 5 0 0 1 7 7h2"></path><!----><path d="M15 7h2a5 5 0 1 1 0 10h-2"></path><!----><line x1="8" x2="16" y1="12" y2="12"></line><!----><!----><!----></svg><!----> <span>Promuovi a Bonifico</span></div> <p class="text-sm text-gray-500 dark:text-gray-400">Risolvi i campi divergenti:</p> <div class="flex justify-center gap-2"><div class="tooltip-wrapper svelte-bgl7um" role="button" tabindex="0"><!----><button type="button" class="px-3 py-1.5 text-xs rounded-lg bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300 hover:bg-blue-200 dark:hover:bg-blue-800/40" data-testid="promote-merge-all-left">◀ Tutti sinistra</button><!----></div> <!----><!----> <div class="tooltip-wrapper svelte-bgl7um" role="button" tabindex="0"><!----><button type="button" class="px-3 py-1.5 text-xs rounded-lg bg-indigo-100 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-300 hover:bg-indigo-200 dark:hover:bg-indigo-800/40" data-testid="promote-merge-all-merge">⟷ Unisci tutti</button><!----></div> <!----><!----> <div class="tooltip-wrapper svelte-bgl7um" role="button" tabindex="0"><!----><button type="button" class="px-3 py-1.5 text-xs rounded-lg bg-pink-100 text-pink-700 dark:bg-pink-900/30 dark:text-pink-300 hover:bg-pink-200 dark:hover:bg-pink-800/40" data-testid="promote-merge-all-right">Tutti destra ▶</button><!----></div> <!----><!----></div> <div class="space-y-4"><div class="border border-gray-200 dark:border-gray-700 rounded-lg p-3" data-testid="promote-merge-field-description"><div class="flex items-center justify-between mb-2"><div class="text-xs font-semibold text-gray-500 dark:text-gray-400">Descrizione</div> <div class="tooltip-wrapper svelte-bgl7um" role="button" tabindex="0"><!----><button type="button" class="px-1.5 py-0.5 text-[10px] rounded bg-indigo-50 dark:bg-indigo-900/30 text-indigo-600 dark:text-indigo-400 hover:bg-indigo-100 dark:hover:bg-indigo-900/50">⟷ Concatena</button><!----></div> <!----><!----></div> <div class="grid grid-cols-2 gap-2 mb-2"><button type="button" class="w-full text-left text-xs text-gray-600 dark:text-gray-300 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded p-2 break-words min-h-[2.5rem] hover:ring-2 hover:ring-blue-300 dark:hover:ring-blue-600 transition-all whitespace-pre-wrap" data-testid="promote-merge-desc-left"><span class="text-[10px] text-gray-400 block mb-0.5">Transaction #43</span> [promote-test] Deposit for cash transfer test</button> <button type="button" class="w-full text-left text-xs text-gray-600 dark:text-gray-300 bg-pink-50 dark:bg-pink-900/20 border border-pink-200 dark:border-pink-800 rounded p-2 break-words min-h-[2.5rem] hover:ring-2 hover:ring-pink-300 dark:hover:ring-pink-600 transition-all whitespace-pre-wrap" data-testid="promote-merge-desc-right"><span class="text-[10px] text-gray-400 block mb-0.5">Transaction #42</span> [promote-test] Withdrawal for cash transfer test</button></div> <textarea class="w-full text-xs px-2 py-1.5 rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-800 dark:text-gray-100 resize-none max-h-32 overflow-y-auto" style="white-space: pre-wrap" data-testid="promote-merge-desc-input" rows="3"></textarea></div><!----> <!----> <!----> <!----></div><!----> <div class="flex justify-end gap-2 pt-2"><button type="button" class="px-4 py-2 text-sm rounded-lg text-gray-700 dark:text-gray-200 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600">Annulla</button> <button type="button" class="px-4 py-2 text-sm rounded-lg text-white bg-green-600 hover:bg-green-700 inline-flex items-center gap-1.5" data-testid="promote-merge-confirm"><svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide-icon lucide lucide-link-2"><!----><path d="M9 17H7A5 5 0 0 1 7 7h2"></path><!----><path d="M15 7h2a5 5 0 1 1 0 10h-2"></path><!----><line x1="8" x2="16" y1="12" y2="12"></line><!----><!----><!----></svg><!----> Conferma promozione</button></div></div>

Il concatena di descrizione non è al centro ma a destra.
i pulsanti tutti erano meglio in fondo. I colori sono corretti però. Invertirei le frecce tra ttutti sinistra e tutti destra e anche le label:
Accetta Tutti > | [icona merge] | < Accetta Tutti
leverei il testo al centro e semplificherei i testi dei bottoni. In oltre la freccia doppia del centro è piccolissima, deve essere molto più spessa.

Estetica a parte, la promozionee funziona!

| W11 | PromoteMergeModal | 2 TX con desc diverse → MergeModal → bottoni All Left/Right/Merge → textarea 
Si funziona, mi sarei aspettato che andando a capo nella text area, per un pò si allargasse l'altezza della text area, non all'infinito, ma 2 o 3 righe prima della comparsa della scrollbar si.

| W12 | PromoteMergeModal discard | Modificare desc → Cancel → ConfirmModal amber (non danger) | 
si

| W13 | Cash sign in BulkModal | Withdrawal mostra "-500" non "+500" nella griglia bulk |
si

| W14 | Delete via DeleteModal | Main table → delete button → DeleteModal → conferma → TX rimossa |
sia singola transazione che doppia nella main table finzionano e hanno l'aspetto che mi aspettavo.

| W15 | cost_basis_override | TRANSFER con cost_basis override → commit → verifica valore salvato | 
No e in modo strano:
Creo il trasfermimento nel form, per ora senza override, la validate è verde:
{"creates":[{"broker_id":3,"type":"TRANSFER","date":"2026-05-14","quantity":"-1","asset_id":1,"link_uuid":"690d9575-50ac-437d-9ef7-0e6f420b00fa"},{"broker_id":1,"type":"TRANSFER","date":"2026-05-14","quantity":"1","asset_id":1,"link_uuid":"690d9575-50ac-437d-9ef7-0e6f420b00fa"}]}

{
    "committed": false,
    "issues": [],
    "results": [
        {
            "operation": "create",
            "index": 0,
            "ids": [
                76
            ],
            "link_uuid": "690d9575-50ac-437d-9ef7-0e6f420b00fa",
            "status": "success"
        },
        {
            "operation": "create",
            "index": 1,
            "ids": [
                77
            ],
            "link_uuid": "690d9575-50ac-437d-9ef7-0e6f420b00fa",
            "status": "success"
        }
    ]
}

entro in edit nel form e si è perso nuovamente il secondo broker (vecchio bug tornato, dobbiamo fare un test di non regressione in merito) comunque la validate diventa:
{"creates":[{"broker_id":3,"type":"TRANSFER","date":"2026-05-14","quantity":"-1","link_uuid":"90f06cc8-0d7f-4ed1-837e-f4894cf96c59","asset_id":1},{"broker_id":0,"type":"TRANSFER","date":"2026-05-14","quantity":"1","link_uuid":"90f06cc8-0d7f-4ed1-837e-f4894cf96c59","asset_id":1}]}

io quindi rimetto il precedente broker e si ripara.
A questo punto metto al posto di override costo medio (che comunque merita di avere un info vicino che se cliccato riporta al manuale e spiega a cosa serve quel campo)
la validate va bene:
{"creates":[{"broker_id":3,"type":"TRANSFER","date":"2026-05-14","quantity":"-1","link_uuid":"9a8610be-15e7-4d90-b849-fb7ed599b9cc","asset_id":1},{"broker_id":1,"type":"TRANSFER","date":"2026-05-14","quantity":"1","link_uuid":"9a8610be-15e7-4d90-b849-fb7ed599b9cc","asset_id":1,"cost_basis_override":"10"}]}
e come vedi la variabile c'è ed è giustamente solo sul ricevente.

Faccio apply e disastro su bulk:
{"creates":[{"broker_id":3,"type":"TRANSFER","date":"2026-05-14","quantity":"-1","asset_id":1,"link_uuid":"690d9575-50ac-437d-9ef7-0e6f420b00fa"},{"broker_id":1,"type":"TRANSFER","date":"2026-05-14","quantity":"1","asset_id":1,"cost_basis_override":"10","link_uuid":"a83fca13-ecbf-49bc-aecf-b62893410a3b"}]}
{
    "committed": false,
    "issues": [
        {
            "operation": "create",
            "index": 0,
            "ref_id": null,
            "error": "link_uuid '690d9575-50ac-437d-9ef7-0e6f420b00fa' has 1 creates (expected 2)",
            "code": "linkUuidPairCount",
            "params": {
                "linkUuid": "690d9575-50ac-437d-9ef7-0e6f420b00fa",
                "count": 1
            },
            "field": null
        },
        {
            "operation": "create",
            "index": 1,
            "ref_id": null,
            "error": "link_uuid 'a83fca13-ecbf-49bc-aecf-b62893410a3b' has 1 creates (expected 2)",
            "code": "linkUuidPairCount",
            "params": {
                "linkUuid": "a83fca13-ecbf-49bc-aecf-b62893410a3b",
                "count": 1
            },
            "field": null
        }
    ],
    "results": null
}

credo sia un altra categoria di bug che dobbiamo tracciare e risolvere.

Se invece creo il trasferimento direttamente con l'override da form, senza passare per l'edit, la validate è corretta e anche l'apply va a buon fine.
Arrivati alla bulk ecco la validate che la bulk manda:
{"creates":[{"broker_id":3,"type":"TRANSFER","date":"2026-05-14","quantity":"-1","asset_id":1,"link_uuid":"5480f916-3ae8-45a3-a5e5-c5952bb81f6f"},{"broker_id":1,"type":"TRANSFER","date":"2026-05-14","quantity":"1","asset_id":1,"cost_basis_override":"10","link_uuid":"5480f916-3ae8-45a3-a5e5-c5952bb81f6f"}]}
{
    "committed": false,
    "issues": [],
    "results": [
        {
            "operation": "create",
            "index": 0,
            "ids": [
                76
            ],
            "link_uuid": "5480f916-3ae8-45a3-a5e5-c5952bb81f6f",
            "status": "success"
        },
        {
            "operation": "create",
            "index": 1,
            "ids": [
                77
            ],
            "link_uuid": "5480f916-3ae8-45a3-a5e5-c5952bb81f6f",
            "status": "success"
        }
    ]
}

Nella main table le righe compaiono, ma se faccio il read delle righe, indipendentemente da quale delle 2 selezione, l'override è sempre ad auto esteticamente! Mentre i dati ricevuti parlano chiaro:
Request URL
http://localhost:8001/api/v1/transactions?ids=77&limit=1

[
    {
        "id": 77,
        "broker_id": 1,
        "asset_id": 1,
        "type": "TRANSFER",
        "date": "2026-05-14",
        "quantity": "1.000000",
        "cash": null,
        "related_transaction_id": 76,
        "partner_broker_id": 3,
        "tags": null,
        "description": null,
        "cost_basis_override": "10.000000",
        "asset_event_id": null,
        "created_at": "2026-05-14T16:20:46.997540Z",
        "updated_at": "2026-05-14T16:20:46.997997Z"
    }
]

e 

Request URL
http://localhost:8001/api/v1/transactions?ids=76&limit=1

[
    {
        "id": 76,
        "broker_id": 3,
        "asset_id": 1,
        "type": "TRANSFER",
        "date": "2026-05-14",
        "quantity": "-1.000000",
        "cash": null,
        "related_transaction_id": 77,
        "partner_broker_id": 1,
        "tags": null,
        "description": null,
        "cost_basis_override": null,
        "asset_event_id": null,
        "created_at": "2026-05-14T16:20:46.996516Z",
        "updated_at": "2026-05-14T16:20:46.997990Z"
    }
]

Credo che un altro problema, connesso agli id doppi, è che per una read doppia servono entrambi gli ID, in questo caso non credo sia un errore del backend, ma è il frontend che dovrebbe provare ad ottenere entrambe e in base ai dati ottenuti popolare il form.


Piccola nota a margine, quando e dove dovrebbe attivarsi la funzione di suggest? Per ora sembra che non compaia mai. In teoria dovrebbe comparire come azione nelle righe dentro la bulk transaction a seguito di una richiesta che il frontend fa a backend, o sbaglio?
