<!--
  BulkDeleteLinkedPairModal.svelte — confirm-and-extend modal for bulk delete.

  Step 8 of plan-phase07-transaction-Part4.prompt.md.

  Pattern:
  - Caller pre-scans the selected rows and identifies "problematic" ones
    (TX with `related_transaction_id != null` whose partner is NOT in the
    selection). Caller resolves the partner data (from in-memory rows or via
    `GET /transactions?ids=…`) and passes it as `problemRows` to this modal.
  - The user can choose, per problematic row, whether to:
      `extend`  → also delete the partner
      `remove`  → drop the row from the deletion batch
    A global toggle at the top syncs all per-row choices.
  - Other selected rows (without partner conflicts) are deleted unchanged.
  - On commit: `POST /transactions/commit` with `{deletes: [...]}` (atomic, multi-broker).

  When there are no problematic rows the caller should bypass this modal and
  use a plain ConfirmModal instead.
-->
<script lang="ts">
    import {_ as t} from '$lib/i18n';
    import {AlertTriangle, X} from 'lucide-svelte';
    import ModalBase from '$lib/components/ui/modals/ModalBase.svelte';
    import {commitTransactions} from '$lib/utils/transactions/txCommitApi';

    // =========================================================================
    // Types
    // =========================================================================

    import type {TXReadItem} from '../types';

    export interface ProblemPair {
        /** Row currently in the user selection. */
        selected: TXReadItem;
        /** Partner row (resolved from current dataset or fetched on the fly). */
        partner: TXReadItem;
    }

    interface Props {
        open: boolean;
        /** Selected rows that are NOT part of any problematic pair (deleted as-is). */
        cleanRows?: TXReadItem[];
        /** Rows whose partner is missing from the selection. */
        problemRows: ProblemPair[];
        onClose: () => void;
        onCommitted?: (resp: unknown) => void;
    }

    let {open, cleanRows = [], problemRows, onClose, onCommitted}: Props = $props();

    // =========================================================================
    // State
    // =========================================================================

    type RowChoice = 'extend' | 'remove';

    let globalChoice = $state<RowChoice>('extend');
    /** Per-row choice keyed by selected.id (which is unique within a batch). */
    let perRow = $state<Map<number, RowChoice>>(new Map());
    let committing = $state(false);
    let rolledBack = $state<{errors: string[]} | null>(null);

    // Re-init choices whenever the modal opens or problemRows changes.
    $effect(() => {
        if (!open) return;
        const m = new Map<number, RowChoice>();
        for (const p of problemRows) m.set(p.selected.id, globalChoice);
        perRow = m;
        rolledBack = null;
    });

    function setGlobal(choice: RowChoice) {
        globalChoice = choice;
        const m = new Map<number, RowChoice>();
        for (const p of problemRows) m.set(p.selected.id, choice);
        perRow = m;
    }

    function setRow(selectedId: number, choice: RowChoice) {
        const m = new Map(perRow);
        m.set(selectedId, choice);
        perRow = m;
    }

    // =========================================================================
    // Derived
    // =========================================================================

    let finalIds = $derived.by(() => {
        const ids = new Set<number>(cleanRows.map((r) => r.id));
        for (const p of problemRows) {
            const choice = perRow.get(p.selected.id) ?? globalChoice;
            if (choice === 'extend') {
                ids.add(p.selected.id);
                ids.add(p.partner.id);
            }
            // `remove` → drop the selected row entirely (do not delete it).
        }
        return [...ids];
    });

    let extendedCount = $derived(problemRows.reduce((acc, p) => acc + ((perRow.get(p.selected.id) ?? globalChoice) === 'extend' ? 1 : 0), 0));
    let removedCount = $derived(problemRows.length - extendedCount);
    let partnersCount = $derived(extendedCount); // 1 partner per extended row

    // =========================================================================
    // Commit
    // =========================================================================

    async function commit() {
        if (finalIds.length === 0) {
            onClose();
            return;
        }
        committing = true;
        rolledBack = null;
        try {
            const result = await commitTransactions({deletes: finalIds}, {fallback: $t('transactions.bulkDelete.rolledBack')});
            if (result.networkError) {
                rolledBack = {errors: [result.networkError]};
            } else if (!result.committed) {
                rolledBack = {errors: result.issues.map((i) => i.error)};
            } else {
                onCommitted?.(result.rawResponse);
                onClose();
            }
        } finally {
            committing = false;
        }
    }
</script>

<ModalBase {open} maxWidth="3xl" onRequestClose={onClose} testId="tx-bulk-delete-modal">
    <div class="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
        <h2 class="text-base font-semibold text-gray-800 dark:text-gray-100" data-testid="tx-bulk-delete-title">
            🗑 {$t('transactions.bulkDelete.title')} — {cleanRows.length + problemRows.length}
            {$t('common.selected') || 'selected'}
        </h2>
        <button class="p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-700" onclick={onClose} data-testid="tx-bulk-delete-close" aria-label="Close">
            <X size={18} />
        </button>
    </div>

    <div class="p-4 space-y-4 overflow-y-auto">
        {#if problemRows.length === 0}
            <!-- Simple confirm: no linked-pair conflicts -->
            <p class="text-sm text-gray-700 dark:text-gray-200" data-testid="tx-bulk-delete-simple">
                {$t('transactions.bulkDelete.confirmSimple', {values: {n: cleanRows.length}})}
            </p>
            <p class="text-xs text-gray-500 dark:text-gray-400">
                {$t('transactions.bulkDelete.confirmSimpleDesc')}
            </p>
        {:else}
            <!-- Full conflict-resolution UI -->
            <p class="text-xs text-gray-600 dark:text-gray-300">
                {$t('transactions.bulkDelete.intro')}
            </p>

            <div class="flex items-center gap-3 text-xs">
                <span class="text-gray-700 dark:text-gray-200">{$t('transactions.bulkDelete.applyToAll')}:</span>
                <label class="inline-flex items-center gap-1 cursor-pointer">
                    <input type="radio" name="tx-bulk-global" checked={globalChoice === 'remove'} onchange={() => setGlobal('remove')} data-testid="tx-bulk-global-remove" />
                    <span>{$t('transactions.bulkDelete.removeAll')}</span>
                </label>
                <label class="inline-flex items-center gap-1 cursor-pointer">
                    <input type="radio" name="tx-bulk-global" checked={globalChoice === 'extend'} onchange={() => setGlobal('extend')} data-testid="tx-bulk-global-extend" />
                    <span>{$t('transactions.bulkDelete.extendAll')}</span>
                </label>
            </div>

            <div class="border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden">
                <table class="w-full text-xs">
                    <thead class="bg-gray-50 dark:bg-gray-800 text-[10px] uppercase text-gray-500 dark:text-gray-400">
                        <tr>
                            <th class="text-left px-2 py-1.5">{$t('transactions.bulkDelete.colSelected')}</th>
                            <th class="text-left px-2 py-1.5">{$t('transactions.bulkDelete.colType')}</th>
                            <th class="text-left px-2 py-1.5">{$t('transactions.bulkDelete.colPartner')}</th>
                            <th class="text-left px-2 py-1.5">{$t('transactions.bulkDelete.colAction')}</th>
                        </tr>
                    </thead>
                    <tbody>
                        {#each problemRows as p}
                            {@const choice = perRow.get(p.selected.id) ?? globalChoice}
                            <tr data-testid={`tx-bulk-row-${p.selected.id}`}>
                                <td class="px-2 py-1.5 font-mono">#{p.selected.id}</td>
                                <td class="px-2 py-1.5">{$t(`transactions.types.${p.selected.type}`) || p.selected.type}</td>
                                <td class="px-2 py-1.5">#{p.partner.id} <span class="text-gray-400">↩</span></td>
                                <td class="px-2 py-1.5">
                                    <label class="inline-flex items-center gap-1 cursor-pointer mr-3">
                                        <input type="radio" name={`tx-bulk-row-${p.selected.id}`} checked={choice === 'remove'} onchange={() => setRow(p.selected.id, 'remove')} data-testid={`tx-bulk-row-${p.selected.id}-remove`} />
                                        <span>{$t('transactions.bulkDelete.removeAll')}</span>
                                    </label>
                                    <label class="inline-flex items-center gap-1 cursor-pointer">
                                        <input type="radio" name={`tx-bulk-row-${p.selected.id}`} checked={choice === 'extend'} onchange={() => setRow(p.selected.id, 'extend')} data-testid={`tx-bulk-row-${p.selected.id}-extend`} />
                                        <span>{$t('transactions.bulkDelete.extendRow', {values: {id: p.partner.id}})}</span>
                                    </label>
                                </td>
                            </tr>
                        {/each}
                    </tbody>
                </table>
            </div>

            {#if cleanRows.length > 0}
                <p class="text-xs text-gray-500 dark:text-gray-400">
                    {$t('transactions.bulkDelete.noConflict', {values: {n: cleanRows.length}})}
                </p>
            {/if}

            <div class="text-xs text-gray-700 dark:text-gray-200 font-medium" data-testid="tx-bulk-summary">
                {$t('transactions.bulkDelete.summary', {values: {total: finalIds.length, clean: cleanRows.length, extended: extendedCount, partners: partnersCount, removed: removedCount}})}
            </div>
        {/if}

        {#if rolledBack}
            <div class="p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded text-xs text-red-800 dark:text-red-200" data-testid="tx-bulk-rollback">
                <div class="flex items-start gap-2 mb-1">
                    <AlertTriangle size={14} class="shrink-0 mt-0.5" />
                    <strong>{$t('transactions.bulkDelete.rolledBack')}</strong>
                </div>
                <ul class="ml-5 list-disc">
                    {#each rolledBack.errors as err}
                        <li>{err}</li>
                    {/each}
                </ul>
            </div>
        {/if}
    </div>

    <div class="flex items-center justify-end gap-2 p-3 border-t border-gray-200 dark:border-gray-700">
        <button class="px-4 py-1.5 text-xs rounded text-gray-700 dark:text-gray-200 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600" onclick={onClose} data-testid="tx-bulk-cancel">
            {$t('transactions.bulkDelete.cancel')}
        </button>
        <button class="px-4 py-1.5 text-xs rounded text-white bg-red-600 hover:bg-red-700 disabled:opacity-50" disabled={committing || finalIds.length === 0} onclick={commit} data-testid="tx-bulk-confirm">
            {committing ? $t('transactions.bulkDelete.deleting') : $t('transactions.bulkDelete.confirm', {values: {n: finalIds.length}})}
        </button>
    </div>
</ModalBase>
