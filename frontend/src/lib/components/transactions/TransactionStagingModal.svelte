<!--
  TransactionStagingModal.svelte — universal create/edit modal for transactions.

  Step 7 of plan-phase07-transaction-Part4.prompt.md.

  This is the **single, universal** modal for any flow that produces a list of
  transaction drafts:
  - `create-many` (manual Add) → POST /transactions/bulk
  - `edit-many`   (single-row edit, bulk edit, clone)  → PATCH /transactions/bulk
  - import-from-broker (BRIM, Round 2) → reuses the same modal pre-populated
    with the parsed BRIM drafts; commit pipeline is identical.

  Each mode opens with a list of draft rows (passed in as `initialRows`); the
  user can edit fields inline, add or remove rows (create-many only) and commit
  the whole batch atomically. A debounced live-validate hits POST
  /transactions/validate with one branch populated and surfaces issues in a
  banner above the rows.

  Pattern: Svelte 5 runes, dark mode, `data-testid` everywhere.
-->
<script lang="ts">
    import {onMount} from 'svelte';
    import {_ as t} from '$lib/i18n';
    import {AlertTriangle, Plus, X} from 'lucide-svelte';
    import ModalBase from '$lib/components/ui/ModalBase.svelte';
    import AssetSelect from '$lib/components/ui/select/AssetSelect.svelte';
    import {zodiosApi} from '$lib/api';
    import {ensureAssetsLoaded} from '$lib/stores/assetStore';
    import {TX_TYPES} from '$lib/utils/transactionTypes';
    import {getBrokerColor, type BrokerLike} from '$lib/utils/brokerColors';

    // =========================================================================
    // Types
    // =========================================================================

    export interface TXReadItem {
        id: number;
        broker_id: number;
        asset_id?: number | null;
        type: string;
        date: string;
        quantity: string;
        cash?: {code: string; amount: string} | null;
        related_transaction_id?: number | null;
        tags?: string[] | null;
        description?: string | null;
        cost_basis_override?: string | null;
        asset_event_id?: number | null;
    }

    interface TXCreateItem {
        broker_id: number;
        asset_id?: number | null;
        type: string;
        date: string;
        quantity: string;
        cash?: {code: string; amount: string} | null;
        related_transaction_id?: number | null;
        tags?: string[] | null;
        description?: string | null;
    }

    interface TXUpdateItem {
        id: number;
        date?: string;
        quantity?: string;
        cash?: {code: string; amount: string} | null;
        tags?: string[] | null;
        description?: string | null;
        asset_event_id?: number | null;
    }

    interface ValidationIssue {
        operation: 'create' | 'update' | 'delete';
        index: number;
        ref_id?: number | null;
        code?: string;
        message: string;
    }

    interface DraftRow {
        /** Tracks lifecycle. `original` rows in edit-many that haven't been touched
         *  are sent as no-op updates? No — only emit edited rows on commit. */
        status: 'new' | 'edited' | 'original';
        /** Original snapshot for reset (edit-many only). */
        original?: TXReadItem;
        /** Live working copy. */
        draft: TXCreateItem & {id?: number};
    }

    interface Props {
        open: boolean;
        mode: 'create-many' | 'edit-many';
        initialRows?: TXReadItem[];
        brokers: BrokerLike[];
        onClose: () => void;
        onCommitted?: (resp: unknown) => void;
    }

    let {open, mode, initialRows = [], brokers, onClose, onCommitted}: Props = $props();

    // =========================================================================
    // State
    // =========================================================================

    let drafts = $state<DraftRow[]>([]);
    let issues = $state<ValidationIssue[]>([]);
    let validating = $state(false);
    let committing = $state(false);
    let rolledBack = $state<{errors: string[]; results?: unknown[]} | null>(null);
    let debounceTimer: ReturnType<typeof setTimeout> | null = null;

    // =========================================================================
    // Lifecycle
    // =========================================================================

    function freshDraftFromTx(tx: TXReadItem): DraftRow {
        return {
            status: 'original',
            original: structuredClone(tx),
            draft: {
                id: tx.id,
                broker_id: tx.broker_id,
                asset_id: tx.asset_id ?? null,
                type: tx.type,
                date: tx.date,
                quantity: tx.quantity,
                cash: tx.cash ?? null,
                related_transaction_id: tx.related_transaction_id ?? null,
                tags: tx.tags ?? null,
                description: tx.description ?? null,
            },
        };
    }

    function freshEmptyDraft(): DraftRow {
        const today = new Date().toISOString().slice(0, 10);
        return {
            status: 'new',
            draft: {
                broker_id: brokers[0]?.id ?? 0,
                asset_id: null,
                type: 'BUY',
                date: today,
                quantity: '0',
                cash: null,
                related_transaction_id: null,
                tags: null,
                description: null,
            },
        };
    }

    /** Reset drafts whenever `open` flips to true. */
    $effect(() => {
        if (!open) return;
        rolledBack = null;
        issues = [];
        // Compute the next drafts list in a local variable BEFORE assigning to
        // the `drafts` rune. This avoids the read-write loop trap of Svelte 5
        // `$effect`: assigning to `drafts` and then iterating it inside the same
        // effect makes `drafts` a tracked dependency, and the prior write
        // immediately invalidates the effect → infinite re-run
        // (`effect_update_depth_exceeded`). Reading from `next` is untracked.
        const next: DraftRow[] = mode === 'create-many' ? (initialRows.length > 0 ? initialRows.map(freshDraftFromTx).map((d) => ({...d, status: 'new', draft: {...d.draft, id: undefined}})) : [freshEmptyDraft()]) : initialRows.map(freshDraftFromTx);
        const ids = new Set<number>();
        for (const d of next) if (d.draft.asset_id != null) ids.add(d.draft.asset_id);
        drafts = next;
        // Refresh asset cache on open (avoid stale display_name cross-client).
        if (ids.size > 0) void ensureAssetsLoaded();
    });

    onMount(() => {
        return () => {
            if (debounceTimer != null) clearTimeout(debounceTimer);
        };
    });

    // =========================================================================
    // Live validate (debounced)
    // =========================================================================

    function scheduleValidate() {
        if (debounceTimer != null) clearTimeout(debounceTimer);
        debounceTimer = setTimeout(() => {
            void runValidate();
        }, 500);
    }

    async function runValidate() {
        if (!open) return;
        validating = true;
        try {
            const payload: {creates?: TXCreateItem[]; updates?: TXUpdateItem[]; deletes?: number[]} = {};
            if (mode === 'create-many') {
                payload.creates = drafts.map((d) => sanitizeCreate(d.draft));
            } else {
                payload.updates = collectUpdates();
            }
            const res = (await zodiosApi.validate_transactions_api_v1_transactions_validate_post(payload as never)) as {issues?: ValidationIssue[]};
            issues = res?.issues ?? [];
        } catch (e) {
            issues = [{operation: mode === 'create-many' ? 'create' : 'update', index: 0, message: e instanceof Error ? e.message : String(e)}];
        } finally {
            validating = false;
        }
    }

    function sanitizeCreate(d: TXCreateItem & {id?: number}): TXCreateItem {
        const clean: TXCreateItem = {
            broker_id: d.broker_id,
            type: d.type,
            date: d.date,
            quantity: d.quantity,
        };
        if (d.asset_id != null) clean.asset_id = d.asset_id;
        if (d.cash) clean.cash = d.cash;
        if (d.related_transaction_id != null) clean.related_transaction_id = d.related_transaction_id;
        if (d.tags?.length) clean.tags = d.tags;
        if (d.description) clean.description = d.description;
        return clean;
    }

    function collectUpdates(): TXUpdateItem[] {
        const out: TXUpdateItem[] = [];
        for (const d of drafts) {
            if (d.status !== 'edited' || !d.original || d.draft.id == null) continue;
            const u: TXUpdateItem = {id: d.draft.id};
            if (d.draft.date !== d.original.date) u.date = d.draft.date;
            if (d.draft.quantity !== d.original.quantity) u.quantity = d.draft.quantity;
            if (JSON.stringify(d.draft.cash ?? null) !== JSON.stringify(d.original.cash ?? null)) u.cash = d.draft.cash ?? null;
            if (JSON.stringify(d.draft.tags ?? null) !== JSON.stringify(d.original.tags ?? null)) u.tags = d.draft.tags ?? null;
            if ((d.draft.description ?? null) !== (d.original.description ?? null)) u.description = d.draft.description ?? null;
            out.push(u);
        }
        return out;
    }

    // =========================================================================
    // Mutators
    // =========================================================================

    function markEdited(idx: number) {
        const d = drafts[idx];
        if (d.status === 'original') drafts[idx] = {...d, status: 'edited'};
        scheduleValidate();
    }

    function addRow() {
        drafts = [...drafts, freshEmptyDraft()];
        scheduleValidate();
    }

    function removeRow(idx: number) {
        drafts = drafts.filter((_, i) => i !== idx);
        scheduleValidate();
    }

    function resetRow(idx: number) {
        const d = drafts[idx];
        if (!d.original) return;
        drafts[idx] = freshDraftFromTx(d.original);
        scheduleValidate();
    }

    function resetAll() {
        if (mode !== 'edit-many') return;
        drafts = drafts.map((d) => (d.original ? freshDraftFromTx(d.original) : d));
        scheduleValidate();
    }

    // =========================================================================
    // Commit
    // =========================================================================

    async function commit() {
        committing = true;
        rolledBack = null;
        try {
            if (mode === 'create-many') {
                const items = drafts.map((d) => sanitizeCreate(d.draft));
                const res = (await zodiosApi.create_transactions_bulk_api_v1_transactions_bulk_post(items as never)) as {rolled_back: boolean; errors?: string[]; results?: unknown[]};
                if (res.rolled_back) {
                    rolledBack = {errors: res.errors ?? [], results: res.results};
                } else {
                    onCommitted?.(res);
                    onClose();
                }
            } else {
                const items = collectUpdates();
                if (items.length === 0) {
                    onClose();
                    return;
                }
                const res = (await zodiosApi.update_transactions_bulk_api_v1_transactions_bulk_patch(items as never)) as {rolled_back: boolean; errors?: string[]; results?: unknown[]};
                if (res.rolled_back) {
                    rolledBack = {errors: res.errors ?? [], results: res.results};
                } else {
                    onCommitted?.(res);
                    onClose();
                }
            }
        } catch (e) {
            rolledBack = {errors: [e instanceof Error ? e.message : String(e)]};
        } finally {
            committing = false;
        }
    }

    // =========================================================================
    // Derived
    // =========================================================================

    let editedCount = $derived(drafts.filter((d) => d.status === 'edited' || d.status === 'new').length);
    let commitDisabled = $derived(committing || drafts.length === 0 || (mode === 'edit-many' && editedCount === 0));

    function brokerStyle(brokerId: number): string {
        const c = getBrokerColor(brokerId, brokers);
        return `--broker-bg:${c.bg};--broker-text:${c.text};`;
    }

    // =========================================================================
    // Inline-input handlers (Svelte 5 doesn't accept `as` casts in markup
    // expressions, so we extract them to typed script-level functions).
    // =========================================================================

    function onDateInput(idx: number, e: Event) {
        const v = (e.currentTarget as HTMLInputElement).value;
        drafts[idx].draft.date = v;
        markEdited(idx);
    }
    function onTypeChange(idx: number, e: Event) {
        const v = (e.currentTarget as HTMLSelectElement).value;
        drafts[idx].draft.type = v;
        markEdited(idx);
    }
    function onQtyInput(idx: number, e: Event) {
        const v = (e.currentTarget as HTMLInputElement).value;
        drafts[idx].draft.quantity = v;
        markEdited(idx);
    }
    function onCashAmountInput(idx: number, e: Event) {
        const v = (e.currentTarget as HTMLInputElement).value;
        const cur = drafts[idx].draft.cash;
        if (!v || v === '0') drafts[idx].draft.cash = null;
        else drafts[idx].draft.cash = {code: cur?.code ?? 'EUR', amount: v};
        markEdited(idx);
    }
    function onCashCodeInput(idx: number, e: Event) {
        const code = (e.currentTarget as HTMLInputElement).value.toUpperCase();
        const cur = drafts[idx].draft.cash;
        if (cur) drafts[idx].draft.cash = {...cur, code};
        markEdited(idx);
    }
    function onBrokerChange(idx: number, e: Event) {
        const v = Number((e.currentTarget as HTMLSelectElement).value);
        drafts[idx].draft.broker_id = v;
        markEdited(idx);
    }
    function onAssetChange(idx: number, _v: number | null) {
        markEdited(idx);
    }
</script>

<ModalBase {open} maxWidth="5xl" onRequestClose={onClose} testId="tx-staging-modal">
    <div class="modal-header flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
        <h2 class="text-base font-semibold text-gray-800 dark:text-gray-100" data-testid="tx-staging-title">
            {#if mode === 'create-many'}
                ➕ {$t('transactions.staging.createTitle')} —
                {drafts.length === 1 ? $t('transactions.staging.draftSingular', {values: {n: drafts.length}}) : $t('transactions.staging.draftPlural', {values: {n: drafts.length}})}
            {:else}
                ✎ {$t('transactions.staging.editTitle')} — {$t('transactions.staging.editedFmt', {values: {n: editedCount, total: drafts.length}})}
            {/if}
            {#if validating}
                <span class="ml-2 text-xs text-gray-400">…validating</span>
            {:else if issues.length > 0}
                <span class="ml-2 text-xs text-amber-600">· {issues.length} issue{issues.length === 1 ? '' : 's'}</span>
            {/if}
        </h2>
        <button class="p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-700" onclick={onClose} data-testid="tx-staging-close" aria-label="Close">
            <X size={18} />
        </button>
    </div>

    {#if issues.length > 0}
        <div class="p-3 bg-amber-50 dark:bg-amber-900/20 border-b border-amber-200 dark:border-amber-800" data-testid="tx-staging-issues">
            <div class="flex items-start gap-2">
                <AlertTriangle class="text-amber-600 dark:text-amber-400 shrink-0 mt-0.5" size={16} />
                <ul class="text-xs text-amber-800 dark:text-amber-200 space-y-0.5">
                    {#each issues as issue}
                        <li data-testid="tx-staging-issue">
                            Row {issue.index + 1}{issue.ref_id != null ? ` (#${issue.ref_id})` : ''}: {issue.message}
                        </li>
                    {/each}
                </ul>
            </div>
        </div>
    {/if}

    {#if rolledBack}
        <div class="p-3 bg-red-50 dark:bg-red-900/20 border-b border-red-200 dark:border-red-800" data-testid="tx-staging-rollback">
            <p class="text-xs text-red-800 dark:text-red-200 font-semibold mb-1">⛔ Commit rolled back — nothing was saved.</p>
            <ul class="text-xs text-red-700 dark:text-red-300 space-y-0.5">
                {#each rolledBack.errors as err}
                    <li>{err}</li>
                {/each}
            </ul>
        </div>
    {/if}

    <div class="modal-body flex-1 overflow-y-auto overflow-x-auto p-3" data-testid="tx-staging-body">
        <table class="w-full text-xs">
            <thead class="text-[10px] uppercase text-gray-500 dark:text-gray-400">
                <tr>
                    <th class="w-3 px-1 py-2"></th>
                    <th class="text-left px-2 py-2">{$t('transactions.table.date')}</th>
                    <th class="text-left px-2 py-2">{$t('transactions.table.type')}</th>
                    <th class="text-left px-2 py-2">{$t('transactions.table.asset')}</th>
                    <th class="text-right px-2 py-2">{$t('transactions.table.quantity')}</th>
                    <th class="text-right px-2 py-2">{$t('transactions.table.cash')}</th>
                    <th class="text-left px-2 py-2">Currency</th>
                    <th class="text-left px-2 py-2">{$t('transactions.table.broker')}</th>
                    <th class="w-10 px-1 py-2"></th>
                </tr>
            </thead>
            <tbody>
                {#each drafts as row, i (i)}
                    <tr style={brokerStyle(row.draft.broker_id)} data-testid={`tx-staging-row-${i}`} class={row.status === 'new' ? 'bg-emerald-50/40 dark:bg-emerald-900/10' : row.status === 'edited' ? 'bg-amber-50/40 dark:bg-amber-900/10' : ''}>
                        <td class="px-1 py-1">
                            <span class="inline-block w-1 h-6 rounded" style="background: var(--broker-bg);"></span>
                        </td>
                        <td class="px-2 py-1">
                            <input type="date" class="w-full bg-transparent border-b border-transparent focus:border-libre-green outline-none text-xs" value={row.draft.date} oninput={(e) => onDateInput(i, e)} data-testid={`tx-staging-date-${i}`} />
                        </td>
                        <td class="px-2 py-1">
                            <select class="w-full bg-transparent text-xs" value={row.draft.type} disabled={mode === 'edit-many'} onchange={(e) => onTypeChange(i, e)} data-testid={`tx-staging-type-${i}`}>
                                {#each TX_TYPES as tt}
                                    <option value={tt}>{tt}</option>
                                {/each}
                            </select>
                        </td>
                        <td class="px-2 py-1 min-w-[200px]">
                            <AssetSelect
                                value={row.draft.asset_id ?? null}
                                testid={`tx-staging-asset-${i}`}
                                placeholder="—"
                                compact={true}
                                onchange={(v) => {
                                    drafts[i].draft.asset_id = v;
                                    onAssetChange(i, v);
                                }}
                            />
                        </td>
                        <td class="px-2 py-1">
                            <input type="text" class="w-24 bg-transparent border-b border-transparent focus:border-libre-green outline-none text-xs text-right" value={row.draft.quantity} oninput={(e) => onQtyInput(i, e)} data-testid={`tx-staging-qty-${i}`} />
                        </td>
                        <td class="px-2 py-1">
                            <input type="text" class="w-28 bg-transparent border-b border-transparent focus:border-libre-green outline-none text-xs text-right" value={row.draft.cash?.amount ?? ''} placeholder="0" oninput={(e) => onCashAmountInput(i, e)} data-testid={`tx-staging-cash-${i}`} />
                        </td>
                        <td class="px-2 py-1">
                            <input
                                type="text"
                                class="w-16 bg-transparent border-b border-transparent focus:border-libre-green outline-none text-xs uppercase"
                                value={row.draft.cash?.code ?? ''}
                                placeholder="EUR"
                                maxlength="3"
                                oninput={(e) => onCashCodeInput(i, e)}
                                data-testid={`tx-staging-currency-${i}`}
                            />
                        </td>
                        <td class="px-2 py-1">
                            <select class="w-full bg-transparent text-xs" value={row.draft.broker_id} disabled={mode === 'edit-many'} onchange={(e) => onBrokerChange(i, e)} data-testid={`tx-staging-broker-${i}`}>
                                {#each brokers as b}
                                    <option value={b.id}>{b.name}</option>
                                {/each}
                            </select>
                        </td>
                        <td class="px-1 py-1 text-right">
                            {#if mode === 'edit-many' && row.original}
                                <button class="p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-400" title="Reset row" onclick={() => resetRow(i)} data-testid={`tx-staging-reset-${i}`}>↺</button>
                            {:else}
                                <button class="p-1 rounded hover:bg-red-100 dark:hover:bg-red-900/30 text-red-500" title="Remove row" onclick={() => removeRow(i)} data-testid={`tx-staging-remove-${i}`}>
                                    <X size={14} />
                                </button>
                            {/if}
                        </td>
                    </tr>
                {/each}
            </tbody>
        </table>

        {#if mode === 'create-many'}
            <button class="mt-2 px-3 py-1.5 text-xs rounded border border-dashed border-gray-300 dark:border-gray-600 text-gray-600 dark:text-gray-300 hover:border-libre-green hover:text-libre-green flex items-center gap-1" onclick={addRow} data-testid="tx-staging-add-row">
                <Plus size={14} /> Add row
            </button>
        {/if}
    </div>

    <div class="modal-footer flex items-center justify-end gap-2 p-3 border-t border-gray-200 dark:border-gray-700">
        {#if mode === 'edit-many'}
            <button class="px-3 py-1.5 text-xs rounded text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700" onclick={resetAll} data-testid="tx-staging-reset-all">Reset all</button>
        {/if}
        <button class="px-4 py-1.5 text-xs rounded text-gray-700 dark:text-gray-200 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600" onclick={onClose} data-testid="tx-staging-cancel">Cancel</button>
        <button class="px-4 py-1.5 text-xs rounded text-white bg-libre-green hover:bg-libre-green/90 disabled:opacity-50" disabled={commitDisabled} onclick={commit} data-testid="tx-staging-commit">
            {committing ? '…committing' : `Commit ${mode === 'create-many' ? drafts.length : editedCount}`}
        </button>
    </div>
</ModalBase>
