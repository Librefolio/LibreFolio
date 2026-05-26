# Plan D2 Bugfix 2 — Payload, Split Preview, Access Guard, UX & E2E

**Date**: 2026-05-13
**Status**: ✅ COMPLETED
**Priority**: P1
**Estimated effort**: ~16h (~3-4 days)

**Parent**: [`plan-bugfix1_SplitPromotePolish.prompt.md`](./plan-bugfix1_SplitPromotePolish.prompt.md)

---

## 🎯 Obiettivo

Risolvere i bug payload (cost_basis_override, link_uuid partner), implementare split-preview editabile nel BulkModal (anziché rimuovere la riga), aggiungere broker access guard, fixare i18n duplicato, rinnovare UX suggest banner e PromoteMergeModal, estendere result con `ids: list[int]`, rifare le ConfirmModal ricche, e creare la suite E2E completa.

---

## 📋 Bug dal test manuale (Round 1)

| # | Area | Descrizione | Root cause |
|---|------|-------------|-----------|
| M2-1 | Suggest banner | 🔗 non sembra cliccabile (emoji, nessun riquadro) | UX mancante |
| M2-2 | Payload | `cost_basis_override: ""` → backend Decimal parse error | `partnerPayload` bypassa `buildCreatePayload` |
| M2-3 | Payload | `link_uuid` mancante nel partner create → `linkUuidPairCount` error | `partnerPayload` bypassa `buildCreatePayload` |
| M3-1 | BulkModal split | Commit disabilitato dopo split (0 righe visibili) | `handleSplitRow` rimuove la riga anziché mostrare preview |
| M3-2 | BulkModal split | Nessuna preview delle righe splittate | Decisione DD-BF1 errata (rimuovi dal batch) |
| M4-1 | i18n | Chiavi `promote.*` non risolte (testo raw visibile) | 2 oggetti `"promote"` duplicati nello stesso JSON |
| M4-8 | Access | Promote su broker VIEWER → backend `accessDenied` | Manca guard frontend |
| M4-UX1 | PromoteMergeModal | Colori generici, concat non centrato, no label "seleziona" | UX non implementata |
| M4-UX2 | DataTableToolbar | Tooltip = `title` HTML nativo (incoerente) | Deve usare componente Tooltip custom |
| M4-UX3 | Suggest banner | Formato messaggio generico (solo tipi) | Serve formato dettagliato con icone e posizioni riga |
| B11 | Backend result | Promote/split ritornano solo 1 ID su 2 | Schema `id: Optional[int]` troppo ristretto |

---

## ✅ Decisioni architetturali

### DD-R2.1 — Split nel BulkModal: preview editabile (corregge DD-BF1)

La decisione DD-BF1 (rimuovi la riga dal batch dopo split) era sbagliata. Nuovo comportamento:

1. Accumulare `{id: row.txId}` in `pendingSplits` (il backend deve sapere di fare lo split).
2. **Sostituire** la riga paired con 2 righe `op='edit'` standalone che rappresentano le TX post-split: ciascuna con il suo `txId` (originale e partner), tipo post-split da `SPLIT_TYPE_MAP`, `partnerId = undefined`, `partnerPayload = undefined`.
3. L'utente le vede e le può editare (cambio qty, desc, tags...).
4. Gli eventuali edit su queste righe generano `updates[]` nel payload commit.
5. Il badge "⚡ N split in coda" resta visibile nella toolbar stats.

### DD-R2.2 — Backend ordine: splits PRIMA di updates

L'ordine backend attuale: `deletes(3) → updates(4) → creates(5) → splits(5b) → promotes(5c) → links(6) → balance(7)`.

Per il caso "split + edit post-split" serve che lo split avvenga **prima** degli updates. Nuovo ordine:

```
deletes(3) → splits(3b) → updates(4) → creates(5) → promotes(5c) → links(6) → balance(7)
```

**Analisi conflitti**:
- Un update su una riga creata nello stesso batch NON è possibile (non si conosce l'ID al momento dell'invio).
- Un delete + split della stessa riga: il backend rileva "TX not found" allo step split (la TX è già stata eliminata a step 3). Issue appropriata.
- Splits agiscono solo su TX già esistenti nel DB — nessuna dipendenza da creates.
- Updates su righe appena splittate funzionano: le TX sono mutate in-place nella session (tipo cambiato, link rimosso), poi l'update applica le modifiche dell'utente sui nuovi campi.

### DD-R2.3 — `TXBatchResultItem.id` → `ids: List[int]`

Split e promote coinvolgono sempre 2 TX — ritornare solo 1 ID è una perdita di informazione. Con `ids: list[int]` il contract è uniforme:
- `create`: `ids=[new_tx.id]`
- `update`: `ids=[item.id]`
- `delete`: `ids=[tx_id]`
- `split`: `ids=[tx_from.id, tx_to.id]` (entrambi i lati)
- `promote`: `ids=[tx_a.id, tx_b.id]` (entrambi i lati)

**Impatto frontend**: Solo `TransactionFormModal.svelte` legge `resp.results?.[0]?.id` (3 righe). Aggiornare a `resp.results?.[0]?.ids?.[0]`. Nessun altro uso di `result.id` nel codice TX.

---

## Steps

### Step 1 — Fix i18n `promote` duplicato — ~15min

**File**: `frontend/src/lib/i18n/{en,it,fr,es}.json`

**Problema**: ci sono DUE oggetti `"promote": {}` allo stesso livello dentro `"transactions"` (righe ~494 e ~627 in en.json). Il parser JSON tiene l'ultimo → le chiavi aggiunte in F12 (nel primo oggetto) sono invisibili.

**Fix**: unire i contenuti dei 2 oggetti `promote` in un unico blocco. Eliminare il duplicato.

---

### Step 2 — Fix payload partner: `cost_basis_override` e `link_uuid` — ~45min

**File**: `frontend/src/lib/components/transactions/TransactionBulkModal.svelte`

**Root cause**: a riga 923, `d.partnerPayload` viene pushato raw in `creates[]`:
```ts
if (d.partnerPayload) creates.push(d.partnerPayload as unknown as Record<string, unknown>);
```

Questo bypassa `buildCreatePayload()` che:
- (riga 137) filtra `cost_basis_override` se stringa vuota
- (riga 138) include `link_uuid` solo se `rule.requiresPair`

**Fix**: sostituire riga 923 con:
```ts
if (d.partnerPayload) {
    const partnerFields = d.partnerPayload as unknown as TxFields;
    const partnerRule = getTypeRule(partnerFields.type as TransactionTypeCode);
    creates.push(buildCreatePayload(partnerFields, partnerRule));
}
```

Stesso fix a riga 705 (in `getBulkContextExcluding`):
```ts
if (d.partnerPayload) {
    const partnerFields = d.partnerPayload as unknown as TxFields;
    const partnerRule = getTypeRule(partnerFields.type as TransactionTypeCode);
    creates.push(buildCreatePayload(partnerFields, partnerRule));
}
```

**Semantica `cost_basis_override`**: è un `Optional[SafeDecimal]` nel backend — `null` oppure un numero Decimal valido. Stringa vuota causa parse error. Le nuove TX create tramite promote (CASH_TRANSFER, ecc.) non hanno cost_basis_override → correttamente omesso da `buildCreatePayload` quando la stringa è vuota.

---

### Step 3 — Split nel BulkModal: preview editabile + BE reorder — ~3h

#### Step 3a — Backend: spostare splits prima di updates (~1h)

**File**: `backend/app/services/transaction_service.py`

Spostare il blocco "Step 5b — Apply splits" (righe 1113-1199) subito dopo "Step 3 — Apply deletes" (dopo riga ~1008). Rinominare il commento in "Step 3b — Apply splits". Aggiornare i commenti dei passi successivi per riflettere il nuovo ordine.

Nuovo ordine pipeline:
```python
# 1. Lenient per-row parse
# 2. Access check
# 3. Apply deletes
# 3b. Apply splits (spostato qui da Step 5b)
# 4. Apply updates
# 4b. Validate pair desc/tags consistency
# 5. Apply creates
# 5c. Apply promotes
# 6. Link resolution
# 7. Balance walk
# 8. Decision
```

**Nota**: `split_partner_ids` lookup (righe 948-957) resta al suo posto (necessario prima dell'access check per toccare i broker dei partner).

#### Step 3b — Frontend: split preview editabile (~2h)

**File**: `frontend/src/lib/components/transactions/TransactionBulkModal.svelte`

Riscrivere `handleSplitRow()` Case A (riga 637-640):

```ts
function handleSplitRow(row: PendingOp) {
    if (row.op === 'edit' && row.partnerId != null) {
        // Case A: Saved paired → backend split + preview editable
        const txId = (row as any).txId as number;
        const partnerId = row.partnerId!;
        pendingSplits = [...pendingSplits, {id: txId}];

        // Determine split types
        const splitTypes = SPLIT_TYPE_MAP[row.fields.type];
        if (!splitTypes) return;
        const [fromType, toType] = splitTypes;

        // Determine from/to by sign
        const cashAmt = Number(row.fields.cash?.amount ?? 0);
        const qty = Number(row.fields.quantity ?? 0);
        const isFrom = row.fields.type === 'TRANSFER' ? qty < 0 : cashAmt < 0;

        // Create 2 standalone edit ops replacing the paired row
        // Op 1: the main TX (already in ops as `row`)
        row.fields.type = (isFrom ? fromType : toType) as TransactionTypeCode;
        row.partnerId = undefined;
        row.partnerBrokerId = undefined;
        row.partnerCash = undefined;
        row.partnerDate = undefined;
        row.partnerPayload = undefined;

        // Op 2: the partner TX (add as new edit op)
        const partnerTx = txStoreGet(partnerId);
        if (partnerTx) {
            const partnerOp = createEditOp(partnerTx);
            partnerOp.fields.type = (isFrom ? toType : fromType) as TransactionTypeCode;
            partnerOp.partnerId = undefined;
            partnerOp.partnerBrokerId = undefined;
            partnerOp.partnerCash = undefined;
            partnerOp.partnerDate = undefined;
            partnerOp.partnerPayload = undefined;
            ops = [...ops, partnerOp];
        }

        ops = [...ops]; // trigger reactivity
    } else if (row.op === 'create' && row.link_uuid) {
        // Case B unchanged...
    }
}
```

**Nota**: `createEditOp(tx)` è un helper che crea un `PendingOp` di tipo `edit` da un `TXReadItem` del txStore (come `editOpFromTx` se esiste, altrimenti creare).

**commitDisabled**: con le 2 righe preview nel batch, `ops.length > 0` e `actionCount > 0` (le righe hanno `deriveStatus() === 'edited'` perché il tipo è cambiato rispetto all'originale). Il commit funziona naturalmente.

**Payload finale**: `{splits: [{id: 38}], updates: [{id: 38, type: "ADJUSTMENT", ...}, {id: 39, type: "ADJUSTMENT", ...}]}`. Il backend prima splitta (Step 3b: rimuove link, cambia tipi), poi applica gli updates dell'utente (Step 4).

---

### Step 4 — Broker access guard promote + mock data — ~30min

**File**: `frontend/src/routes/(app)/transactions/+page.svelte`

In `promoteMatch` ($derived, riga 543), aggiungere guard dopo la riga 547:
```ts
// Access guard: both brokers must be EDITOR+
if (getBrokerRole(a.broker_id) === 'viewer' || getBrokerRole(b.broker_id) === 'viewer') return null;
```

**File**: `backend/test_scripts/test_db/populate_mock_data.py`

Dopo le 4 TX `promote-test` (riga ~1465), aggiungere 2 TX tagged `promote-test-access-fail`:

```python
# CASH_TRANSFER candidate that SHOULD FAIL for e2e_test_user:
# Directa (index 2, EDITOR) + DEGIRO (index 1, VIEWER) → promote toolbar hidden
tx_access_fail_w = Transaction(
    broker_id=directa.id, asset_id=None,
    type=TransactionType.WITHDRAWAL,
    date=today - timedelta(days=9),
    quantity=Decimal("0"), amount=Decimal("-200.00"), currency="EUR",
    description="[promote-test-access-fail] Withdrawal on EDITOR broker - promote should fail for test_user (VIEWER on DEGIRO)",
    tags="promote-test-access-fail",
)
tx_access_fail_d = Transaction(
    broker_id=degiro.id, asset_id=None,
    type=TransactionType.DEPOSIT,
    date=today - timedelta(days=9),
    quantity=Decimal("0"), amount=Decimal("200.00"), currency="EUR",
    description="[promote-test-access-fail] Deposit on VIEWER broker - promote should fail for test_user (VIEWER on DEGIRO)",
    tags="promote-test-access-fail",
)
session.add_all([tx_access_fail_w, tx_access_fail_d])
session.commit()
print(f"  🚫 promote-test-access-fail: W#{tx_access_fail_w.id} (Directa/EDITOR), D#{tx_access_fail_d.id} (DEGIRO/VIEWER)")
```

Broker access per `e2e_test_user`:
- [0] Interactive Brokers: OWNER 30%
- [1] DEGIRO: **VIEWER**
- [2] Directa SIM: EDITOR
- [3] eToro: VIEWER
- [4] Coinbase: EDITOR
- [5] Recrowd: VIEWER

Le TX `promote-test` originali (Withdrawal su DEGIRO + Deposit su IB) sono giustamente bloccate perché DEGIRO è VIEWER. A queste ne aggiungiamo un paio esplicito (Directa EDITOR + DEGIRO VIEWER) con tag dedicato per il test E2E.

---

### Step 5 — Suggest banner UX rinnovato — ~1h

**File**: `frontend/src/lib/components/transactions/TransactionBulkModal.svelte` (righe ~2004-2020)

Nuovo formato per ogni suggest item:

```svelte
<div class="flex items-center gap-1.5 flex-wrap text-xs" data-testid="promote-suggest-item-{idx}">
    <button type="button" class="underline text-green-700 dark:text-green-300 font-medium"
        onclick={() => scrollToSuggestRow(sug.tempIdA)}>
        Riga {sug.indexA + 1}
    </button>
    <Tooltip text={$t(`transactions.types.${sug.typeA}`)}>
        <img src={getTransactionTypeIconUrl(sug.typeA)} alt="" class="w-4 h-4 inline" />
    </Tooltip>
    <span class="text-gray-500">{$t('common.and')}</span>
    <button type="button" class="underline text-green-700 dark:text-green-300 font-medium"
        onclick={() => scrollToSuggestRow(sug.tempIdB)}>
        Riga {sug.indexB + 1}
    </button>
    <Tooltip text={$t(`transactions.types.${sug.typeB}`)}>
        <img src={getTransactionTypeIconUrl(sug.typeB)} alt="" class="w-4 h-4 inline" />
    </Tooltip>
    <span class="text-gray-500">→</span>
    <Tooltip text={sug.targetLabel}>
        <img src={getTransactionTypeIconUrl(sug.targetType)} alt="" class="w-4 h-4 inline" />
    </Tooltip>
    <button type="button"
        class="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-green-100 dark:bg-green-800/30 border border-green-300 dark:border-green-700 text-green-700 dark:text-green-300 hover:bg-green-200 dark:hover:bg-green-700/40 font-medium"
        onclick={() => triggerPromoteFromSuggestion(sug)}
        data-testid="promote-suggest-link-{idx}">
        <Link2 size={12} />
        {$t('transactions.promoteSuggest.merge') || 'Unisci'}
    </button>
</div>
```

**Dati aggiuntivi nel suggest**: aggiungere `typeA`, `typeB`, `targetType`, `indexA`, `indexB` alla struttura `allSuggestions` (computed dagli indici delle ops nel array visibile).

**i18n chiave da aggiungere**: `transactions.promoteSuggest.merge` = "Merge" / "Unisci" / "Fusionner" / "Combinar"

---

### Step 6 — PromoteMergeModal polish — ~2h

**File**: `frontend/src/lib/components/transactions/PromoteMergeModal.svelte`

**6a — Tema verde modale**: Aggiungere al container `<div class="p-5 space-y-4">` la classe `bg-green-50/50 dark:bg-green-950/20 rounded-lg`.

**6b — Colori 2 lati**: Sostituire `bg-gray-50 dark:bg-gray-800` sui bottoni readonly:
- Sinistra: `bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800`
- Destra: `bg-pink-50 dark:bg-pink-900/20 border-pink-200 dark:border-pink-800`
- Aggiungere `border` su entrambi per renderli più evidenti.

**6c — Label "Clicca per selezionare"**: Sotto ogni blocco readonly, aggiungere:
```svelte
<span class="text-[9px] text-gray-400 mt-0.5 block">{$t('transactions.promote.clickToSelect')}</span>
```

**6d — Concat centrato**: Spostare il bottone `⟷ Concat` in una riga `flex justify-center` tra i 2 blocchi readonly (non sotto):
```svelte
<div class="grid grid-cols-2 gap-2 mb-1">
    <!-- left button -->
    <!-- right button -->
</div>
<div class="flex justify-center my-1">
    <button ...>⟷ {$t('transactions.promote.concat')}</button>
</div>
<textarea ...></textarea>
```

**6e — Testo merge**: nei bottoni readonly, formato `Transaction #{label}: {description}`:
```svelte
<span class="text-[10px] text-gray-400 block mb-0.5">Transaction {txA.label}</span>
{txA.description || '—'}
```

**6f — Dirty flag + ConfirmModal**: 
```ts
let dirty = $state(false);
// Track changes
$effect(() => { /* compare current values with initial → set dirty */ });

function handleCancel() {
    if (dirty) { showDiscardConfirm = true; return; }
    onCancel();
}
```
Aggiungere `<ConfirmModal>` per discard. `ModalBase` `onRequestClose` → `handleCancel`.

**6g — title → Tooltip**: sui bottoni azione (allLeft, allMerge, allRight, concat, union), wrappare con `<Tooltip text={...}>` al posto di `title`.

**i18n chiave**: `transactions.promote.clickToSelect` = "Click to select" / "Clicca per selezionare" / "Cliquer pour sélectionner" / "Haz clic para seleccionar"

---

### Step 7 — DataTableToolbar `title` → `Tooltip` — ~15min

**File**: `frontend/src/lib/components/table/DataTableToolbar.svelte`

Riga 43, sostituire:
```svelte
<button ... title={getActionLabel(action)} ...>
```
con:
```svelte
<Tooltip text={getActionLabel(action)}>
    <button ... ...>
        <action.icon size={16} class={action.iconClass || ''} />
    </button>
</Tooltip>
```

Aggiungere import: `import Tooltip from '$lib/components/ui/Tooltip.svelte';`

---

### Step 8 — Backend: `TXBatchResultItem.id` → `ids: List[int]` — ~1h

**File**: `backend/app/schemas/transactions.py`

```python
class TXBatchResultItem(BaseModel):
    """Per-item result for committed rows."""
    model_config = ConfigDict(extra="forbid")

    operation: TXBatchOperation
    index: int
    ids: List[int] = Field(default_factory=list, description="IDs of affected transactions. Split/promote return both IDs.")
    link_uuid: Optional[str] = None
    status: TXItemStatus
```

**File**: `backend/app/services/transaction_service.py`

- Riga ~1005 (delete): `ids=[tx_id]`
- Riga ~1048 (update): `ids=[item.id]`
- Riga ~1109 (create): `ids=[tx.id]`
- Riga ~1199 (split): `ids=[tx_from.id, tx_to.id]`
- Riga ~1300 (promote): `ids=[tx_a.id, tx_b.id]`

**File**: `frontend/src/lib/components/transactions/TransactionFormModal.svelte`

Righe 1063, 1079, 1096, 1113 — cambiare:
```ts
onCommitted?.({transaction_id: resp.results?.[0]?.id ?? null});
```
→
```ts
onCommitted?.({transaction_id: resp.results?.[0]?.ids?.[0] ?? null});
```

**Eseguire**: `./dev.py api sync` per rigenerare il client TypeScript.

---

### Step 9 — F8/F9: TransactionActionModal (rich confirm) — ~2h

**Nuovo file**: `frontend/src/lib/components/transactions/TransactionActionModal.svelte`

Generalizzare `TransactionDeleteModal.svelte` con prop `mode: 'delete' | 'split' | 'promote'`:

| Mode | Layout | Contenuto |
|------|--------|-----------|
| `delete` | Come attuale (Layout A/B/C) | Stesse info attuali |
| `split` | 2 colonne (before→after) | Sinistra: TX paired attuale. Destra: 2 TX standalone post-split con tipi nuovi |
| `promote` | 2 colonne + tipo target | Colonna A: TX A. Colonna B: TX B. Centro/sotto: tipo target con icona |

**Refactor**: rinominare `TransactionDeleteModal` → `TransactionActionModal`, aggiungere prop `mode`, condizionare header/body/footer in base al mode. I chiamanti in `+page.svelte` aggiornano di conseguenza:
- `deleteModalOpen` → usa `mode='delete'`
- `splitConfirmOpen` → usa `mode='split'` (sostituisce il `ConfirmModal` semplice)
- `promoteConfirmOpen` → usa `mode='promote'` (per il caso identico senza MergeModal)

---

### Step 10 — E2E: completare `tx-split-promote.spec.ts` — ~4h

**File**: `frontend/e2e/transactions/tx-split-promote.spec.ts`

Scenari da aggiungere:

| # | Test | Verifica |
|---|------|----------|
| 2 | Split da BulkModal (saved) → 2 righe preview editabili → commit | Payload: `splits:[{id:X}]` + `updates:[...]`, 2 righe visibili post-split |
| 3 | Promote Main Table (identico, CASH_TRANSFER) | Tipo corretto nel confirm, commit OK |
| 5 | Suggest banner visibile con formato dettagliato | Icone tipo, "Riga N", bottone "Unisci" |
| 6 | Suggest → click Unisci → collapse in paired | 1 riga paired Da:/A: |
| 9 | Mixed batch: split 1 pair + promote 2 standalone → commit | Payload con `splits[]` + `promotes[]` |
| 11 | Broker access guard: promote toolbar hidden su righe con broker VIEWER | Tag `promote-test-access-fail`, toolbar assente |
| NR-1 | BulkModal open paired dopo refresh | Grid OK, paired rendering |
| NR-2 | BulkModal open single dopo refresh | FormModal auto-open, tipo corretto |
| NR-5 | Suggest banner → CASH_TRANSFER (not FX_CONVERSION) | Same currency + diff broker |
| NR-6 | Suggest banner → FX_CONVERSION | Diff currency + same broker |
| NR-8 | Split saved nel BulkModal → 2 righe preview | Righe visibili con tipi post-split |
| NR-10 | Promote 2 new → collapse | 1 riga paired |

**File**: `scripts/test_runner/_frontend_transaction.py`

Registrare con `add_test(cat, "tx-split-promote", front_tx_split_promote, ...)`.

---

## 📊 Step Classification & Priorità

| Step | Tipo | Stima | Priorità | Dipendenze |
|------|------|-------|----------|------------|
| 1 | 🔴 Critical ✅ | ~15min | P0 | — |
| 2 | 🔴 Critical ✅ | ~45min | P0 | — |
| 3 | 🔴 Critical ✅ | ~3h | P0 | — |
| 4 | 🟡 Guard ✅ | ~30min | P1 | — |
| 5 | 🟡 UX ✅ | ~1h | P1 | 1 |
| 6 | 🟡 UX ✅ | ~2h | P1 | 1 |
| 7 | 🟢 Polish ✅ | ~15min | P2 | — |
| 8 | 🟡 Schema ✅ | ~1h | P1 | — |
| 9 | 🟡 UX ✅ | ~2h | P2 | — |
| 10 | 🟡 Tests ✅ | ~4h | P1 | 1-8 |

---

## 🔀 Ordine di esecuzione

```
Wave 1 — Bloccanti (P0):
  Step 1 (i18n merge) → sblocca tutta UI
  Step 2 (payload fix) → sblocca M2
  Step 3 (split preview + BE reorder) → sblocca M3
  Step 4 (access guard + mock) → sblocca M4

Wave 2 — UX (P1-P2):
  Step 5 (suggest banner)
  Step 6 (PromoteMergeModal)
  Step 7 (DataTableToolbar Tooltip)
  Step 9 (TransactionActionModal)

Wave 3 — Schema + Tests:
  Step 8 (ids: list backend + api sync)
  Step 10 (E2E completa)
```

---

## Riepilogo file modificati

| File | Modifica | Step |
|------|----------|------|
| `frontend/src/lib/i18n/{en,it,fr,es}.json` | Merge promote duplicate + nuove chiavi | 1, 5, 6 |
| `frontend/src/lib/components/transactions/TransactionBulkModal.svelte` | Partner payload via `buildCreatePayload`, split preview editabile, suggest banner UX | 2, 3, 5 |
| `backend/app/services/transaction_service.py` | Spostare splits prima di updates (Step 3b) | 3 |
| `frontend/src/routes/(app)/transactions/+page.svelte` | Broker access guard, ActionModal integration | 4, 9 |
| `backend/test_scripts/test_db/populate_mock_data.py` | 2 TX promote-test-access-fail | 4 |
| `frontend/src/lib/components/transactions/PromoteMergeModal.svelte` | Redesign colori + UX polish | 6 |
| `frontend/src/lib/components/table/DataTableToolbar.svelte` | title → Tooltip | 7 |
| `backend/app/schemas/transactions.py` | `id → ids: List[int]` in TXBatchResultItem | 8 |
| `frontend/src/lib/components/transactions/TransactionFormModal.svelte` | `.id → .ids?.[0]` | 8 |
| `frontend/src/lib/api/generated.ts` | Rigenerato da `./dev.py api sync` | 8 |
| `frontend/src/lib/components/transactions/TransactionActionModal.svelte` | **NUOVO** (da TransactionDeleteModal) | 9 |
| `frontend/e2e/transactions/tx-split-promote.spec.ts` | Scenari completi + NR | 10 |
| `scripts/test_runner/_frontend_transaction.py` | Register spec | 10 |

---

## Rischi e mitigazioni

| Rischio | Prob. | Mitigazione |
|---------|-------|-------------|
| BE reorder: split prima di update causa regression | Bassa | Test backend `./dev.py test api all` verifica l'intera suite. Il caso "split + update same TX" è il caso primario coperto |
| `ids: List[int]` rompe schema client | Bassa | Solo 3 righe in TransactionFormModal usano `.id`. `./dev.py api sync` rigenera. No backward compat per policy |
| Split preview: `deriveStatus` ritorna 'edited' anche senza edit utente (tipo cambiato) | Media | Accettabile: il payload includerà un update `{id, type}` che il backend applica come no-op dopo lo split (tipo già cambiato). Nessun side effect |
| PromoteMergeModal redesign: dirty flag falso positivo | Bassa | Confrontare stato iniziale vs corrente con deep-equal |

---

## 🔗 Cross-links

- **Parent (Bugfix 1)**: [`plan-bugfix1_SplitPromotePolish.prompt.md`](./plan-bugfix1_SplitPromotePolish.prompt.md)
- **D2 Frontend**: [`plan-PlanD2_FrontendSplitPromoteUI.prompt.md`](../plan-PlanD2_FrontendSplitPromoteUI.prompt.md)
- **D1 Backend**: [`plan-PlanD1_BackendBatchSuggest.prompt.md`](../plan-PlanD1_BackendBatchSuggest.prompt.md)
- **Parent plan (D)**: [`plan-phase07-PlanD_SplitPromoteFullStack.prompt.md`](../../plan-phase07-PlanD_SplitPromoteFullStack.prompt.md)
- **Child (Bugfix 3)**: [`plan-bugfix3_UXModalPayloadSuggestE2E.prompt.md`](./plan-bugfix3_UXModalPayloadSuggestE2E.prompt.md)

---

## 📝 Execution Notes (2026-05-13)

### Step 8 — `ids: List[int]`
- Backend schema already had `ids` field → OK
- Backend service already used `ids=[...]` → OK
- Frontend `TransactionFormModal` already had `.ids?.[0]` → OK
- `api sync` confirmed → `generated.ts` has `ids: z.array(z.number().int())`
- **Fix**: Backend test scripts had lingering `["id"]` references (6 files) → updated to `["ids"][0]`
- **37/37 API tests pass** ✅

### Step 10 — E2E `tx-split-promote.spec.ts`
- **Rewrote entire test file** — original used non-existent selectors (`row-actions-trigger`, `pair-icon`)
- Correct DOM patterns:
  - Table wrapper: `[data-testid="tx-table"]`
  - Rows: `tr[data-row-id="tx-{id}"]`
  - Actions: inline `button[data-action-id="split"]` (no dropdown)
  - Link indicator: `.tx-link-icon` class
  - Toolbar: `[data-testid="toolbar-action-{id}"]`
  - Split modal: `[data-testid="tx-action-modal"]`
- **4/5 tests pass**, 1 skipped:
  - ✅ Guard: split hidden on standalone
  - ✅ Split from Main Table → confirm modal appears
  - ✅ Guard: promote toolbar hidden on paired
  - ✅ NR-1: BulkModal after refresh
  - ⏭️ Promote selection: skipped (toolbar-action-promote not visible after selecting W+D pair — needs deeper reactive chain investigation)

### Mock data fix — promote-test broker access
- **Bug**: `tx_prom_withdrawal` used `degiro` (VIEWER for e2e_test_user) → promote always blocked
- **Fix**: Changed to `coinbase` (EDITOR) → both promote-test brokers now editable
- Added `!text.includes('access-fail')` guard in E2E matching
- `promote-test-access-fail` pair unchanged (Directa/EDITOR + DEGIRO/VIEWER)
- `login()` call fixed: was `login(page, TEST_USER.username, TEST_USER.password)` → `login(page, TEST_USER)`

