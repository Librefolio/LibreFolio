# Plan D2 — Frontend: Split/Promote UI + Suggest Banner

**Date**: 2026-05-12
**Status**: ✅ COMPLETED (C7✅ C5✅ C1✅ C3✅ C2✅ C4✅ C6✅)
**Priority**: P1 (feature completion)
**Estimated effort**: ~10h (~2.5 days)

**Parent**: [`plan-phase07-transaction-Part4_Round6_PlanD_SplitPromoteFullStack.prompt.md`](./plan-phase07-transaction-Part4_Round6_PlanD_SplitPromoteFullStack.prompt.md)
**Predecessor**: D1 ✅ (Backend Batch Pipeline + Suggest)
**Steps covered**: C5, C3, C4, C1, C2, C6, C7

---

## 🎯 Obiettivo

Aggiungere Split row action (Main Table + BulkModal) e Promote (Main Table migrate → batch, BulkModal toolbar new/saved/mixed), creare PromoteMergeModal per campi divergenti, implementare promote-suggest green banner nel BulkModal, aggiungere le chiavi i18n in 4 lingue.

---

## ⚠️ Deviazioni dal piano D padre (post-D1)

1. **Endpoint `/split` e `/promote` ELIMINATI** → Main Table promote (`confirmPromote()` riga 542-557) chiama `zodiosApi.promote_pairs_api_v1_transactions_promote_post(...)` che **non esiste più**. Va migrata a `zodiosApi.commit_transactions_api_v1_transactions_commit_post({promotes: [{id_a, id_b, resolved_fields}]})`.

2. **`consumed_link_uuids`** in pipeline → il frontend non ha bisogno di saperlo. Quando manda `promotes: [{link_uuid_a, link_uuid_b}]` nella stessa batch con creates, il backend gestisce l'esclusione da Step 6 internamente. Nessun impatto FE.

3. **`resolved_fields` applicato a ENTRAMBI i lati** dal backend → il PromoteMergeModal emette UN set di campi risolti, il backend li copia su tx_a E tx_b. Il FE non serve mandare campi separati per i due lati.

4. **Promote suggest endpoint** disponibile come `zodiosApi.promote_suggest_api_v1_transactions_promote_suggest_post(body, {queries: {tolerance_days}})`.

---

## Stato attuale frontend (da contesto code)

```
+page.svelte (938 LOC)
├── promoteMatch: $derived — findPromoteMatch(a.type, b.type, $_) su 2 righe selezionate
├── onPromotePair() → setta promoteTarget + apre promoteConfirmOpen
├── confirmPromote() → 🔴 USA VECCHIO zodiosApi.promote_pairs (ROTTO)
├── <ConfirmModal> per promote → mostra solo tipo → nessun MergeModal
├── NO split action in rowActions/toolbar

TransactionBulkModal.svelte (1749 LOC)
├── PendingOp tagged union (op: 'create' | 'edit')
├── commit() → crea {creates, updates, deletes} — NO splits/promotes
├── NO split row action
├── NO promote toolbar/selection
├── NO promote-suggest banner

TransactionsTable.svelte (1173 LOC)
├── rowActions: view, edit, clone, delete — NO split
├── Props: onEditRow, onCloneRow, onDeleteRow, onViewRow — NO onSplitRow
```

---

## Design Decisions (D2-specifiche)

### DD-D2.1 — Split locale new pairs (BulkModal)
Per new paired ops (op='create' con link_uuid condiviso), lo split è una trasformazione puramente locale: rimuovere link_uuid da entrambe, mutare i types secondo client-side `SPLIT_TYPE_MAP`, separare in 2 ops indipendenti. Non serve nessuna API call. Il `SPLIT_TYPE_MAP` client-side deve essere definito come mirror di quello backend:
```ts
const SPLIT_TYPE_MAP: Record<string, [string, string]> = {
    TRANSFER: ['ADJUSTMENT', 'ADJUSTMENT'],
    CASH_TRANSFER: ['WITHDRAWAL', 'DEPOSIT'],
    FX_CONVERSION: ['WITHDRAWAL', 'DEPOSIT'],
};
```

### DD-D2.2 — Promote 2 new nel BulkModal = trasformazione locale
Se le 2 righe sono entrambe `op='create'`, il promote è locale: assegna un `link_uuid` condiviso, muta i types al target type. Al commit vanno come 2 creates paired (Step 6 link resolution nel backend). Nessun `promotes[]` nel batch.

### DD-D2.3 — Promote 2 saved nel BulkModal = batch promotes
Se le 2 righe sono `op='edit'`, il promote va nel batch: `{promotes: [{id_a, id_b, resolved_fields}]}`. Se i campi divergono → PromoteMergeModal.

### DD-D2.4 — Promote saved+new nel BulkModal = batch promotes con link_uuid
Un saved + un new: `{promotes: [{id_a: saved_id, link_uuid_b: new_uuid, resolved_fields}]}`, dove `new_uuid` è il `link_uuid` dell'op create. Il new viene creato prima (Step 5 creates), poi promosso (Step 5c promotes via link_uuid_b).

### DD-D2.5 — `promoteMatch` senza constraint check client-side
`findPromoteMatch()` attuale verifica solo i TIPI (type_a ↔ type_b). Il piano D padre menziona verifiche constraint (broker diverso/uguale, currency, ecc.) nel client-side suggest. Per il promote MANUALE (toolbar selection), basta il type match — il backend farà il constraint check completo e ritornerà un'issue se fallisce. Per il suggest AUTOMATICO (banner verde), le constraint sono verificate dal backend endpoint `/promote-suggest`.

---

## Steps

### Step C5 — PromoteMergeModal (componente greenfield) — ~2h

**Nuovo file**: `frontend/src/lib/components/transactions/PromoteMergeModal.svelte`

**Props**:
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

**Comportamento**:
- Itera sui 4 campi (description, tags, date, cost_basis_override). Per ogni campo dove `txA[field] !== txB[field]` → mostra una riga con 3 colonne:
  - Sinistra (readonly): valore txA
  - Centro (editabile): campo risultato (pre-populated con merge di default)
  - Destra (readonly): valore txB
- 3 pulsanti per auto-populate il centro: `◀` (copia sinistra), `⟷` (merge), `▸` (copia destra)
- Pre-populate default: `merge` (concatena desc con `" | "`, union tags, date più recente, cost_basis di A)
- Se TUTTI i campi sono identici → la modale non serve (`onConfirm` chiamato direttamente senza aprire dal parent)
- Tags: merge = union set deduplicated; `◀`/`▸` = solo quelli di un lato
- Date: se diversa → date picker nel campo centro
- Modale usa `ModalBase` come tutte le altre
- `data-testid="promote-merge-modal"`, `data-testid="promote-merge-confirm"`, `data-testid="promote-merge-field-{name}"`

**Layout**:
```
┌───────────────────────────────────────────────────────────────────────────┐
│  🔗 Promuovi a {targetTypeLabel}                                      [X] │
│                                                                           │
│  Campi divergenti da risolvere:                                           │
│                                                                           │
│  ┌─────────── Descrizione ────────────────────────────────────────────┐  │
│  │  Riga A (readonly)   │  [◀] [⟷] [▸]  │  Riga B (readonly)        │  │
│  │  "Transfer AAPL"     │  Risultato:     │  "Move shares"            │  │
│  │                       │  [___________]  │                           │  │
│  └──────────────────────────────────────────────────────────────────────┘│
│                                                                           │
│  ┌─────────── Tags ──────────────────────────────────────────────────┐   │
│  │  [rebalance]          │  [◀] [⟷] [▸]  │  [core] [monthly]         │  │
│  │                       │  Risultato:     │                           │  │
│  │                       │  [___________]  │                           │  │
│  └──────────────────────────────────────────────────────────────────────┘│
│                                                                           │
│                        [Annulla]  [🔗 Conferma]                           │
└───────────────────────────────────────────────────────────────────────────┘
```

**Stile**: `ModalBase` small/medium, stesso design delle altre modali TX.

---

### Step C1 — Main Table: Split row action — ~1h

**File**: `frontend/src/lib/components/transactions/TransactionsTable.svelte`

**1a.** Aggiungere `import {Unlink} from 'lucide-svelte'` (o icona equivalente).

**1b.** Aggiungere nuova prop: `onSplitRow?: (row: TXReadItem) => void`

**1c.** Aggiungere in `rowActions` (dopo `clone`, prima di `delete`):
```ts
{
    id: 'split',
    icon: Unlink,
    label: () => $t('transactions.actions.split') || 'Split pair',
    variant: 'warning',
    onClick: (d) => onSplitRow?.(d.tx),
    visible: (d) => d.tx.related_transaction_id != null && rowAccessLevel(d) === 'full',
},
```

**File**: `frontend/src/routes/(app)/transactions/+page.svelte`

**1d.** Aggiungere state per split confirm:
```ts
let splitConfirmOpen = $state(false);
let splitConfirmTx = $state<TXReadItem | null>(null);
let splitting = $state(false);
```

**1e.** Handler `handleSplitRow(row: TXReadItem)`:
```ts
function handleSplitRow(row: TXReadItem) {
    splitConfirmTx = row;
    splitConfirmOpen = true;
}
```

**1f.** Handler `confirmSplit()`:
- Chiama `zodiosApi.commit_transactions_api_v1_transactions_commit_post({splits: [{id: splitConfirmTx.id}]} as never)`
- Se `committed === true` → close modal, `txStoreInvalidate()`, `reload()`
- Se fallisce → mostra errore nell'ConfirmModal o toast

**1g.** `<ConfirmModal>` per split nel template (accanto a quello di promote):
- Riepilogo: tipo coppia, broker Da→A, importo
- Messaggio i18n `transactions.split.confirmMessage`

**1h.** Passare `onSplitRow={handleSplitRow}` al `<TransactionsTable>`.

---

### Step C2 — Main Table: Promote → migrazione a batch + MergeModal — ~1.5h

**File**: `frontend/src/routes/(app)/transactions/+page.svelte`

**2a.** Riscrivere `confirmPromote()` (riga 542-557):
- Se campi identici (description, tags, date, cost_basis_override) → commit diretto: `zodiosApi.commit_transactions_api_v1_transactions_commit_post({promotes: [{id_a, id_b}]} as never)`
- Se campi divergono → apre `PromoteMergeModal` anziché `ConfirmModal`
- Nuovo state: `promoteMergeOpen`, `promoteMergeData`

**2b.** Handler `onPromoteMergeConfirm(resolved)`:
```ts
async function onPromoteMergeConfirm(resolved: Record<string, unknown>) {
    promoting = true;
    try {
        const resp = await zodiosApi.commit_transactions_api_v1_transactions_commit_post({
            promotes: [{id_a: promoteTarget!.idA, id_b: promoteTarget!.idB, resolved_fields: resolved}]
        } as never);
        const data = resp as {committed?: boolean; issues?: unknown[]};
        if (data.committed) {
            promoteMergeOpen = false;
            promoteConfirmOpen = false;
            promoteTarget = null;
            selectedRows = [];
            await reload();
        } else {
            console.error('[promote] commit failed:', data.issues);
        }
    } catch (e) {
        console.error('[promote]', e);
    } finally {
        promoting = false;
    }
}
```

**2c.** Logica di decisione MergeModal vs ConfirmModal:1
- `onPromotePair()` (riga 531) ora controlla: se i campi dei 2 selectedRows divergono → setta `promoteMergeData` e apre `promoteMergeOpen = true`
- Altrimenti → apre `promoteConfirmOpen = true` (UX attuale preservata, flusso diretto)

**2d.** Sostituire il corpo di `confirmPromote()`:
```ts
async function confirmPromote() {
    // Shortcut: if fields are identical, no merge needed → direct commit
    await onPromoteMergeConfirm({});
}
```

**2e.** Aggiungere `<PromoteMergeModal>` nel template:
```svelte
<PromoteMergeModal
    open={promoteMergeOpen}
    txA={promoteMergeData?.txA}
    txB={promoteMergeData?.txB}
    targetTypeLabel={promoteMergeData?.targetTypeLabel ?? ''}
    onConfirm={onPromoteMergeConfirm}
    onCancel={() => { promoteMergeOpen = false; promoteMergeData = null; }}
/>
```

**2f.** Rimuovere import e call a `zodiosApi.promote_pairs_api_v1_transactions_promote_post` (il metodo non esiste più nel client rigenerato).

---

### Step C3 — BulkModal: Split row action — ~2h

**File**: `frontend/src/lib/components/transactions/TransactionBulkModal.svelte`

**3a.** Aggiungere `SPLIT_TYPE_MAP` come costante client-side (mirror del backend):
```ts
const SPLIT_TYPE_MAP: Record<string, [string, string]> = {
    TRANSFER: ['ADJUSTMENT', 'ADJUSTMENT'],
    CASH_TRANSFER: ['WITHDRAWAL', 'DEPOSIT'],
    FX_CONVERSION: ['WITHDRAWAL', 'DEPOSIT'],
};
```

**3b.** Aggiungere import `Unlink` da lucide-svelte.

**3c.** Aggiungere nuovo state:
```ts
let pendingSplits = $state<{id: number}[]>([]);
```

**3d.** Aggiungere row action `split` in `rowActions` array (dopo `clone`, prima di `mark-delete`):
```ts
{
    id: 'split',
    icon: Unlink,
    label: () => $t('transactions.actions.split') || 'Split pair',
    variant: 'warning',
    onClick: (row: PendingOp) => handleSplitRow(row),
    visible: (row: PendingOp) => {
        // Saved paired → backend split
        if (row.op === 'edit' && row.partnerId != null) return true;
        // New paired (link_uuid shared) → local split
        if (row.op === 'create' && row.link_uuid != null) {
            return ops.some(o => o !== row && o.op === 'create' && o.link_uuid === row.link_uuid);
        }
        return false;
    },
},
```

**3e.** Handler `handleSplitRow(row: PendingOp)`:

**Caso A — Saved paired** (`op === 'edit'`, `partnerId != null`):
1. Lookup the current paired type from `row.fields.type`
2. Lookup `SPLIT_TYPE_MAP[row.fields.type]` → `[fromType, toType]`
3. If not found → skip (type cannot be split)
4. Accumula `{id: row.txId}` in `pendingSplits`
5. Determine from/to based on sign: if quantity < 0 or cash.amount < 0 → this is "from"
6. Mutare `row.fields.type` al tipo corrispondente (from or to)
7. Re-add the partner as a new edit op: `editOpFromTx(row.partnerId!)` with type overridden to the other split type
8. Clear partner display: set `row.partnerId = undefined`, `row.partnerBrokerId = undefined`, `row.partnerCash = undefined`, `row.partnerPayload = undefined`, `row.partnerDate = undefined`
9. Trigger reactivity: `ops = [...ops]`

**Caso B — New paired** (`op === 'create'`, `link_uuid` condiviso):
1. Find the partner op: `ops.find(o => o !== row && o.op === 'create' && o.link_uuid === row.link_uuid)`
2. Lookup `SPLIT_TYPE_MAP[row.fields.type]` → `[fromType, toType]`
3. Determine from/to by sign (same logic as above)
4. Mutare types per entrambe le ops
5. Set `link_uuid = null` su entrambe
6. Clear partner display su entrambe
7. Nessun `pendingSplits` entry (non serve backend)
8. Trigger reactivity: `ops = [...ops]`

**3f.** Modificare `commit()` per includere `splits` nel payload (riga ~821):
```ts
// After: if (deletes.length > 0) payload.deletes = deletes;
if (pendingSplits.length > 0) payload.splits = pendingSplits;
```

**3g.** Reset `pendingSplits` all'apertura modal (`$effect` init, riga ~260 untrack block):
```ts
pendingSplits = [];
```

**3h.** Reset `pendingSplits` dopo commit success (riga ~850):
```ts
pendingSplits = [];
```

---

### Step C4 — BulkModal: Promote selection toolbar + commit — ~2h

**File**: `frontend/src/lib/components/transactions/TransactionBulkModal.svelte`

**4a.** Import `findPromoteMatch` da `$lib/stores/transactionTypeStore`, import `Link2` da lucide-svelte, import `PromoteMergeModal`.

**4b.** Aggiungere state:
```ts
let pendingPromotes = $state<{id_a?: number; id_b?: number; link_uuid_a?: string; link_uuid_b?: string; resolved_fields?: Record<string, unknown>}[]>([]);
let promoteMergeOpen = $state(false);
let promoteMergeData = $state<{txA: any; txB: any; targetTypeLabel: string; opA: PendingOp; opB: PendingOp} | null>(null);
```

**4c.** Selection-based promote detection — `$derived`:
```ts
let selectedForPromote = $derived.by(() => {
    // Get selected rows from DataTable
    const sel = tableRef?.getSelectedRows?.() ?? [];
    if (sel.length !== 2) return null;
    const [a, b] = sel;
    // Both must be standalone (no partnerId, no partnerPayload)
    if (a.partnerId != null || b.partnerId != null) return null;
    if (a.partnerPayload != null || b.partnerPayload != null) return null;
    // Check markedDelete
    if ((a.op === 'edit' && a.markedDelete) || (b.op === 'edit' && b.markedDelete)) return null;
    const match = findPromoteMatch(a.fields.type, b.fields.type, $t);
    if (!match) return null;
    return {...match, opA: a, opB: b};
});
```

**4d.** Toolbar promote — visibile come inline banner sotto la stats toolbar, sopra la DataTable grid:
```svelte
{#if selectedForPromote}
    <div class="flex items-center gap-2 px-3 py-1.5 bg-indigo-50 dark:bg-indigo-900/20 border border-indigo-200 dark:border-indigo-800 rounded-lg text-xs" data-testid="promote-toolbar">
        <Link2 size={14} class="text-indigo-600 dark:text-indigo-400" />
        <span>{$t('transactions.actions.promotePair')}: <strong>{selectedForPromote.targetLabel}</strong></span>
        <button onclick={handlePromoteSelected} class="px-2 py-0.5 bg-indigo-600 text-white rounded text-xs hover:bg-indigo-700" data-testid="promote-toolbar-confirm">🔗 {$t('promote.mergeConfirm')}</button>
    </div>
{/if}
```

**4e.** Handler `handlePromoteSelected()`:
```ts
function handlePromoteSelected() {
    if (!selectedForPromote) return;
    const {opA, opB, targetLabel} = selectedForPromote;

    // Check if fields diverge
    const descA = opA.fields.description, descB = opB.fields.description;
    const tagsA = opA.fields.tags, tagsB = opB.fields.tags;
    const dateA = opA.fields.date, dateB = opB.fields.date;
    const cbA = opA.fields.cost_basis_override, cbB = opB.fields.cost_basis_override;
    const diverges = descA !== descB || JSON.stringify(tagsA) !== JSON.stringify(tagsB) || dateA !== dateB || cbA !== cbB;

    if (diverges) {
        promoteMergeData = {
            txA: {label: `#${opA.op === 'edit' ? opA.txId : opA.tempId.slice(0,6)}`, description: descA, tags: tagsA, date: dateA, cost_basis_override: cbA},
            txB: {label: `#${opB.op === 'edit' ? opB.txId : opB.tempId.slice(0,6)}`, description: descB, tags: tagsB, date: dateB, cost_basis_override: cbB},
            targetTypeLabel: targetLabel,
            opA, opB,
        };
        promoteMergeOpen = true;
        return;
    }
    // No divergence → direct promote
    executePromote(opA, opB, {});
}
```

**4f.** `executePromote(opA, opB, resolved)`:

| Caso | Azione |
|------|--------|
| **2 saved** (both `op='edit'`) | `pendingPromotes.push({id_a: opA.txId, id_b: opB.txId, resolved_fields: resolved})` |
| **2 new** (both `op='create'`) | Trasformazione locale: assegna `link_uuid` condiviso (`generateUUID()`), muta types al target type su entrambe. No `pendingPromotes` entry. |
| **1 saved + 1 new** | Il new deve avere un `link_uuid` (generare se null). `pendingPromotes.push({id_a: savedOp.txId, link_uuid_b: newOp.link_uuid, resolved_fields: resolved})`. |

In all cases: update ops in place (muta types, set partner display, trigger reactivity `ops = [...ops]`).

**4g.** Modificare `commit()` per includere `promotes` nel payload (riga ~822):
```ts
if (pendingPromotes.length > 0) payload.promotes = pendingPromotes;
```

**4h.** Reset `pendingPromotes` all'apertura modal e dopo commit (same locations as `pendingSplits`).

**4i.** MergeModal confirm handler:
```ts
function onBulkPromoteMergeConfirm(resolved: Record<string, unknown>) {
    if (!promoteMergeData) return;
    executePromote(promoteMergeData.opA, promoteMergeData.opB, resolved);
    promoteMergeOpen = false;
    promoteMergeData = null;
}
```

**4j.** `<PromoteMergeModal>` nel template:
```svelte
<PromoteMergeModal
    open={promoteMergeOpen}
    txA={promoteMergeData?.txA}
    txB={promoteMergeData?.txB}
    targetTypeLabel={promoteMergeData?.targetTypeLabel ?? ''}
    onConfirm={onBulkPromoteMergeConfirm}
    onCancel={() => { promoteMergeOpen = false; promoteMergeData = null; }}
/>
```

---

### Step C6 — Promote Suggest green banner — ~3h

**File**: `frontend/src/lib/components/transactions/TransactionBulkModal.svelte`

**6a.** State per suggest:
```ts
let suggestFromDB = $state<Map<number, Array<{id: number; broker_id: number; date: string; type: string}>>>(new Map());
let suggestTimer: ReturnType<typeof setTimeout> | null = null;
```

**6b.** DB candidates (per ops `edit` standalone) — `$effect` reattivo con debounce:
```ts
$effect(() => {
    const editStandalone = ops.filter(o =>
        o.op === 'edit' && !o.partnerId && !(o as any).markedDelete && !o.partnerPayload
    );
    if (editStandalone.length === 0) {
        untrack(() => { suggestFromDB = new Map(); });
        return;
    }
    // Build inputs
    const inputs = editStandalone.map(o => ({
        id: (o as any).txId as number,
        type: o.fields.type,
        broker_id: o.fields.broker_id,
        date: o.fields.date,
        currency: o.fields.cash?.code ?? null,
        asset_id: o.fields.asset_id,
    }));
    const key = JSON.stringify(inputs);

    untrack(() => {
        if (suggestTimer) clearTimeout(suggestTimer);
        suggestTimer = setTimeout(async () => {
            try {
                const resp = await zodiosApi.promote_suggest_api_v1_transactions_promote_suggest_post(
                    inputs as never,
                    {queries: {tolerance_days: 7}}
                );
                suggestFromDB = new Map(Object.entries((resp as any).results ?? {}).map(
                    ([k, v]) => [Number(k), v as any[]]
                ));
            } catch (e) {
                console.warn('[promote-suggest]', e);
            }
        }, 500);
    });
});
onDestroy(() => { if (suggestTimer) clearTimeout(suggestTimer); });
```

**6c.** Local candidates (per ops new standalone, match tra loro) — `$derived` puro:
```ts
let localSuggestions = $derived.by(() => {
    const newStandalone = ops.filter(o =>
        o.op === 'create' && !o.link_uuid && !o.partnerId && !o.partnerPayload
    );
    const results: Array<{tempIdA: string; tempIdB: string; labelA: string; labelB: string; targetLabel: string}> = [];
    for (let i = 0; i < newStandalone.length; i++) {
        for (let j = i + 1; j < newStandalone.length; j++) {
            const match = findPromoteMatch(newStandalone[i].fields.type, newStandalone[j].fields.type, $t);
            if (match) {
                results.push({
                    tempIdA: newStandalone[i].tempId,
                    tempIdB: newStandalone[j].tempId,
                    labelA: `${newStandalone[i].fields.type}`,
                    labelB: `${newStandalone[j].fields.type}`,
                    targetLabel: match.targetLabel,
                });
            }
        }
    }
    return results;
});
```

**6d.** Combine suggestions:
```ts
let allSuggestions = $derived.by(() => {
    const combined: Array<{tempIdA: string; tempIdB: string; labelA: string; labelB: string; targetLabel: string; isDB?: boolean; dbCandidateId?: number}> = [];
    // Local suggestions (new+new)
    for (const s of localSuggestions) combined.push(s);
    // DB suggestions (edit → DB candidate)
    for (const [txId, candidates] of suggestFromDB) {
        const op = ops.find(o => o.op === 'edit' && (o as any).txId === txId);
        if (!op || !candidates.length) continue;
        const best = candidates[0]; // closest by date
        combined.push({
            tempIdA: op.tempId,
            tempIdB: `db-${best.id}`,
            labelA: `#${txId} ${op.fields.type}`,
            labelB: `DB #${best.id} ${best.type}`,
            targetLabel: findPromoteMatch(op.fields.type, best.type, $t)?.targetLabel ?? '?',
            isDB: true,
            dbCandidateId: best.id,
        });
    }
    return combined;
});
```

**6e.** Banner verde — posizione: sopra la DataTable grid, sotto la toolbar stats/split-hint:
```svelte
{#if allSuggestions.length > 0}
    <div class="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg p-2 text-xs space-y-0.5" data-testid="promote-suggest-banner">
        {#each allSuggestions.slice(0, 5) as sug, idx}
            <div class="flex items-center gap-1 flex-wrap" data-testid="promote-suggest-item-{idx}">
                <span>💡</span>
                <button class="underline text-green-700 dark:text-green-300" onclick={() => scrollToRow(sug.tempIdA)}>{sug.labelA}</button>
                <span>&amp;</span>
                <button class="underline text-green-700 dark:text-green-300" onclick={() => scrollToRow(sug.tempIdB)}>{sug.labelB}</button>
                <span>→ {sug.targetLabel}</span>
                <button class="text-green-600 font-bold hover:text-green-800" onclick={() => triggerPromoteFromSuggestion(sug)} data-testid="promote-suggest-link-{idx}">🔗</button>
            </div>
        {/each}
        {#if allSuggestions.length > 5}
            <span class="text-gray-500 text-[11px]">{$t('transactions.promoteSuggest.bannerMore', {values: {n: allSuggestions.length - 5}})}</span>
        {/if}
    </div>
{/if}
```

**6f.** `scrollToRow(tempIdOrDbRef: string)`:
- If starts with `db-` → scroll is N/A (row not in batch). Skip or show tooltip.
- Otherwise → `tableRef?.navigateToRowId(tempIdOrDbRef)` + pulse CSS `tx-row-highlight`

**6g.** `triggerPromoteFromSuggestion(sug)`:
- For **local suggestions** (new+new): find both ops by tempId, auto-select them in DataTable, then invoke `handlePromoteSelected()`.
- For **DB suggestions** (edit → DB candidate): two sub-cases:
  - If DB candidate is already in ops (was picker-added) → select both + `handlePromoteSelected()`
  - If DB candidate NOT in ops → add it via `editOpFromTx(sug.dbCandidateId!, {addedViaPicker: true})`, push to ops, then select both + `handlePromoteSelected()`

**6h.** Debounce cleanup in `$effect` init (when modal opens): clear `suggestFromDB` + cancel timer.

---

### Step C7 — i18n (4 lingue) — ~30min

**File**: `frontend/src/lib/i18n/{en,it,fr,es}.json`

Chiavi da aggiungere (namespace `transactions`):

| Key | EN | IT | FR | ES |
|-----|----|----|----|----|
| `actions.split` | `Split pair` | `Scollega coppia` | `Séparer la paire` | `Separar par` |
| `split.confirmTitle` | `Unlink this pair?` | `Scollegare questa coppia?` | `Dissocier cette paire ?` | `¿Desvincular este par?` |
| `split.confirmMessage` | `The 2 transactions will become independent rows.` | `Le 2 transazioni diventeranno righe indipendenti.` | `Les 2 transactions deviendront des lignes indépendantes.` | `Las 2 transacciones se convertirán en filas independientes.` |
| `split.success` | `Pair unlinked successfully` | `Coppia scollegata` | `Paire dissociée` | `Par desvinculado` |
| `promote.mergeTitle` | `Promote to {type}` | `Promuovi a {type}` | `Promouvoir en {type}` | `Promover a {type}` |
| `promote.mergeConfirm` | `Confirm promotion` | `Conferma promozione` | `Confirmer la promotion` | `Confirmar promoción` |
| `promote.fieldDescription` | `Description` | `Descrizione` | `Description` | `Descripción` |
| `promote.fieldTags` | `Tags` | `Tag` | `Tags` | `Etiquetas` |
| `promote.fieldDate` | `Date` | `Data` | `Date` | `Fecha` |
| `promote.fieldCostBasis` | `Cost basis` | `Costo base` | `Coût de base` | `Costo base` |
| `promote.useLeft` | `Use left` | `Usa sinistra` | `Utiliser gauche` | `Usar izquierda` |
| `promote.useMerge` | `Merge` | `Unisci` | `Fusionner` | `Combinar` |
| `promote.useRight` | `Use right` | `Usa destra` | `Utiliser droite` | `Usar derecha` |
| `promoteSuggest.banner` | `Row {a} and Row {b} are compatible — promote to {type}` | `Riga {a} e Riga {b} sono compatibili — promuovi a {type}` | `Ligne {a} et Ligne {b} sont compatibles — promouvoir en {type}` | `Fila {a} y Fila {b} son compatibles — promover a {type}` |
| `promoteSuggest.bannerMore` | `and {n} more...` | `e altri {n}...` | `et {n} de plus...` | `y {n} más...` |
| `promoteSuggest.dbMatch` | `Match found in DB: {type} on {broker} ({date})` | `Match nel DB: {type} su {broker} ({date})` | `Correspondance en BDD : {type} sur {broker} ({date})` | `Coincidencia en BD: {type} en {broker} ({date})` |

Usare `./dev.py i18n add` o modifica diretta dei JSON.

---

## 📊 Step Classification

| Step | Tipo | Stima | Dipendenze |
|------|------|-------|------------|
| C5 | 🗺️ Component | ~2h | — |
| C1 | 🎯 Main Table | ~1h | — |
| C2 | 🎯 Main Table | ~1.5h | C5 |
| C3 | 🗺️ BulkModal | ~2h | C5 |
| C4 | 🗺️ BulkModal | ~2h | C5, C3 (needs `pendingSplits` cleanup pattern) |
| C6 | 🗺️ Suggest | ~3h | C4 (needs promote handler) |
| C7 | 🎯 i18n | ~30min | — |

**Totale stimato**: ~12h (~2.5 days)

---

## 🔀 Ordine di esecuzione

```
C7 (i18n — prerequisito per tutti i componenti che usano chiavi)
  ↓
C5 (PromoteMergeModal — greenfield, nessuna dipendenza)
  ↓
C1 (Main Table split) ─── C3 (BulkModal split) ←── paralleli
  ↓                           ↓
C2 (Main Table promote)    C4 (BulkModal promote)
                              ↓
                           C6 (Promote suggest banner)
```

---

## Riepilogo file modificati

| File | Tipo modifica | Step |
|------|--------------|------|
| `frontend/src/lib/components/transactions/PromoteMergeModal.svelte` | **NUOVO** — 3-column diff UI | C5 |
| `frontend/src/lib/components/transactions/TransactionsTable.svelte` | +1 row action `split`, +1 prop `onSplitRow` | C1 |
| `frontend/src/routes/(app)/transactions/+page.svelte` | Split handler, promote migration (batch), PromoteMergeModal integration | C1, C2 |
| `frontend/src/lib/components/transactions/TransactionBulkModal.svelte` | Split row action, promote toolbar, suggest banner, `pendingSplits/pendingPromotes` nel commit, SPLIT_TYPE_MAP | C3, C4, C6 |
| `frontend/src/lib/i18n/{en,it,fr,es}.json` | ~17 nuove chiavi × 4 lingue | C7 |

---

## Rischi e mitigazioni

| Rischio | Prob. | Mitigazione |
|---------|-------|-------------|
| `zodiosApi.promote_pairs_*` call residue in codice | Bassa | Grep + rimuovere; la type generation non ha più quel metodo |
| Split locale new pairs perde il partner display | Media | Testare: split deve rimuovere `partnerId` E separare visivamente le 2 ops nella grid |
| Promote suggest $effect loop se ops cambia troppo spesso | Bassa | Debounce 500ms + `untrack()` per scrittura `suggestFromDB` |
| PromoteMergeModal → campi date divergenti | Bassa | Usare `<input type="date">` standard, il backend accetta ISO string |
| Regressione test E2E esistenti (84+ test) | Media | `./dev.py test front-transaction all` dopo ogni step |
| `pendingSplits`/`pendingPromotes` non resettati dopo commit | Bassa | Reset esplicito nel finally del commit() + nel $effect init |

---

## 🔗 Cross-links

- **Parent plan**: [`plan-phase07-transaction-Part4_Round6_PlanD_SplitPromoteFullStack.prompt.md`](./plan-phase07-transaction-Part4_Round6_PlanD_SplitPromoteFullStack.prompt.md)
- **Predecessor (D1)**: [`plan-phase07-transaction-Part4_Round6_PlanD1_BackendBatchSuggest.prompt.md`](./plan-phase07-transaction-Part4_Round6_PlanD1_BackendBatchSuggest.prompt.md)
- **Bugfix 1**: [`plan-phase07-transaction-Part4_Round6_PlanD2_bugfix_1_SplitPromotePolish.prompt.md`](./plan-phase07-transaction-Part4_Round6_PlanD2_bugfix_1_SplitPromotePolish.prompt.md) — 21 bug, UX polish, E2E tests
- **Next (D3)**: Embedded in Bugfix 1 as Step F14

