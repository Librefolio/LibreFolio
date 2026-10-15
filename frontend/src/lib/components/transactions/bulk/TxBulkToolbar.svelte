<!--
  TxBulkToolbar — the toolbar of the bulk workspace: search and add on the left, selection and actions on the right.

  Cut from TransactionBulkModal.svelte (FE8a): the modal owns the state and the handlers; this
  section reads them as props, writes the bound ones back, and calls the handlers.
-->
<script lang="ts">
    import {_ as t} from '$lib/i18n';
    import {Plus, Trash2, Undo2, Link2, Lightbulb, Upload} from 'lucide-svelte';
    import ColumnVisibilityToggle from '$lib/components/table/ColumnVisibilityToggle.svelte';
    import {txStoreCount} from '$lib/stores/transactions/txStore.svelte';
    import {guideAnchor} from '$lib/features/onboarding/guideAnchors.svelte';
    import type {PendingOp} from './txBulkTypes';
    import type DataTable from '$lib/components/table/DataTable.svelte';
    import type {importableSuggestions as importableFromResults} from '$lib/utils/transactions/promoteSuggest';
    import type {findPromoteMatch} from '$lib/stores/transactions/transactionTypeStore';

    interface Props {
        bulkTableSelectedRows: PendingOp[];
        importWizardOpen: boolean;
        maxDeltaDays: number;
        pendingSplits: {id_a: number; id_b: number; originalType: string}[];
        tableRef: DataTable<PendingOp> | undefined;
        importableSuggestions: ReturnType<typeof importableFromResults>;
        selectedForPromote: (NonNullable<ReturnType<typeof findPromoteMatch>> & {opA: PendingOp; opB: PendingOp}) | null;
        tableRefForToggle: never;
        visibleOps: PendingOp[];
        deriveStatus: (d: PendingOp) => 'new' | 'edited' | 'original' | 'delete';
        executeBulkDeleteOnSelected: () => void;
        handlePromoteSelected: () => void;
        openAddRowForm: () => void;
        openPicker: () => void;
        openSuggestPicker: () => void;
        resetAll: () => void;
        resetRow: (tempId: string) => void;
    }

    let {
        bulkTableSelectedRows = $bindable(),
        importWizardOpen = $bindable(),
        maxDeltaDays = $bindable(),
        pendingSplits,
        tableRef,
        importableSuggestions,
        selectedForPromote,
        tableRefForToggle,
        visibleOps,
        deriveStatus,
        executeBulkDeleteOnSelected,
        handlePromoteSelected,
        openAddRowForm,
        openPicker,
        openSuggestPicker,
        resetAll,
        resetRow,
    }: Props = $props();
</script>

<div class="flex items-center gap-2 px-5 py-3 border-b border-gray-100 dark:border-slate-800 text-xs shrink-0" use:guideAnchor={'transaction.bulk.add_import'}>
    <!-- Left: search & add -->
    {#if txStoreCount() > 0}
        <button
            type="button"
            class="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg text-gray-700 dark:text-gray-200 bg-gray-100 dark:bg-slate-700 hover:bg-gray-200 dark:hover:bg-slate-600"
            onclick={openPicker}
            data-testid="tx-bulk-picker"
            title={$t('transactions.picker.searchAdd') || 'Search & add'}
        >
            🔍 <span class="hidden sm:inline">{$t('transactions.picker.searchAdd') || 'Search & add'}</span>
        </button>
    {/if}

    <!-- R3-B5: Delta-days filter for promote suggestions -->
    <div class="inline-flex items-center gap-1.5 text-[11px] text-gray-500 dark:text-gray-400">
        <span class="hidden sm:inline">{$t('transactions.promoteSuggest.deltaLabel') || 'Max Δ days'}</span>
        <span class="sm:hidden" title="Max delta days">Δ</span>
        <input type="range" min="0" max="14" step="1" class="w-20 accent-libre-green" bind:value={maxDeltaDays} data-testid="promote-suggest-delta-input" />
        <span class="text-[11px] font-mono w-5 text-center">{maxDeltaDays}</span>
    </div>

    <!-- Inline selection toolbar moved to Right group below -->

    <!-- Right: actions -->
    <div class="ml-auto flex flex-row-reverse items-center gap-2 flex-wrap">
        <button type="button" class="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg bg-libre-green text-white hover:bg-libre-green/90" onclick={openAddRowForm} data-testid="tx-bulk-add-row" title={$t('common.addRow') || 'Add row'}>
            <Plus size={12} /> <span class="hidden sm:inline">{$t('common.addRow') || 'Add row'}</span>
        </button>
        <button
            type="button"
            class="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-slate-700 border border-gray-200 dark:border-gray-600"
            onclick={() => (importWizardOpen = true)}
            data-testid="tx-bulk-import"
            title={$t('common.import') || 'Import'}
        >
            <Upload size={12} /> <span class="hidden sm:inline">{$t('common.import') || 'Import'}</span>
        </button>
        {#if importableSuggestions.length > 0}
            <button
                type="button"
                class="inline-flex items-center gap-1 px-2 py-1.5 rounded-lg text-amber-600 dark:text-amber-400 hover:bg-amber-50 dark:hover:bg-amber-900/20 border border-amber-200 dark:border-amber-700"
                onclick={openSuggestPicker}
                data-testid="tx-bulk-suggest-import"
                title={$t('transactions.bulk.suggestLightbulb') || 'Import suggested pairs'}
            >
                <Lightbulb size={14} />
                <span class="text-[10px] font-medium">{importableSuggestions.reduce((n, s) => n + s.candidates.length, 0)}</span>
            </button>
        {/if}
        {#if visibleOps.some((d) => d.op === 'edit' && (deriveStatus(d) === 'edited' || deriveStatus(d) === 'delete')) || pendingSplits.length > 0}
            <button type="button" class="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-slate-700" onclick={resetAll} data-testid="tx-bulk-reset-all" title={$t('common.resetAllChanges')}>
                <Undo2 size={12} /> <span class="hidden sm:inline">{$t('common.resetAllChanges')}</span>
            </button>
        {/if}
        <ColumnVisibilityToggle tableRef={tableRefForToggle} />
        {#if bulkTableSelectedRows.length > 0}
            <div class="flex items-center gap-2" use:guideAnchor={'transaction.bulk.selection'}>
                <button
                    type="button"
                    class="inline-flex items-center gap-1 px-2 py-1 rounded text-gray-600 dark:text-gray-300 bg-gray-100 dark:bg-slate-700 hover:bg-gray-200 dark:hover:bg-slate-600 text-[11px]"
                    onclick={() => {
                        tableRef?.clearSelection();
                        bulkTableSelectedRows = [];
                    }}
                >
                    <span class="font-medium">{bulkTableSelectedRows.length}</span> <span class="hidden sm:inline">{$t('common.selected') || 'selected'}</span> <span class="opacity-60 ml-0.5">×</span>
                </button>
                {#if bulkTableSelectedRows.some((d) => d.op === 'edit' && (deriveStatus(d) === 'edited' || deriveStatus(d) === 'delete'))}
                    <button
                        type="button"
                        class="inline-flex items-center gap-1 px-2 py-1 rounded text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-slate-700 text-[11px]"
                        onclick={() => {
                            for (const r of bulkTableSelectedRows) resetRow(r.tempId);
                        }}
                        title={$t('transactions.bulk.resetSelected') || 'Reset selected'}
                        data-testid="tx-bulk-reset-selected"
                    >
                        <Undo2 size={12} /> <span class="hidden sm:inline">{$t('transactions.bulk.resetSelected') || 'Reset'}</span>
                    </button>
                {/if}
                <button
                    type="button"
                    class="inline-flex items-center gap-1 px-2 py-1 rounded text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 text-[11px]"
                    onclick={executeBulkDeleteOnSelected}
                    title={$t('transactions.bulk.deleteSelected') || 'Delete selected'}
                    data-testid="tx-bulk-delete-selected"
                >
                    <Trash2 size={12} /> <span class="hidden sm:inline">{$t('common.delete') || 'Delete'}</span>
                </button>
                {#if selectedForPromote}
                    <button
                        type="button"
                        class="inline-flex items-center gap-1 px-2 py-1 rounded text-indigo-600 dark:text-indigo-400 hover:bg-indigo-50 dark:hover:bg-indigo-900/20 text-[11px]"
                        onclick={handlePromoteSelected}
                        data-testid="promote-toolbar-confirm"
                        title={$t('transactions.actions.promotePair')}
                    >
                        <Link2 size={12} /> <span class="hidden sm:inline">🔗 {selectedForPromote.targetLabel}</span>
                    </button>
                {/if}
            </div>
        {/if}
    </div>
</div>
