<!--
  TxBulkToolbar — the toolbar of the bulk workspace: search and add on the left, selection and actions on the right.

  Cut from TransactionBulkModal.svelte (FE8a): the modal owns the state and the handlers; this
  section reads them as props, writes the bound ones back, and calls the handlers.
-->
<script lang="ts">
    import {_ as t} from '$lib/i18n';
    import {Plus, Trash2, Undo2, Link2, Lightbulb, Upload} from 'lucide-svelte';
    import ColumnVisibilityToggle from '$lib/components/table/ColumnVisibilityToggle.svelte';
    import Tooltip from '$lib/components/ui/feedback/Tooltip.svelte';
    import type {BulkLinkSelection} from './bulkCharges';
    import {txStoreCount} from '$lib/features/transactions/txStore.svelte';
    import {guideAnchor} from '$lib/features/onboarding/guideAnchors.svelte';
    import type {PendingOp, PromoteSelection} from './txBulkTypes';
    import type DataTable from '$lib/components/table/DataTable.svelte';
    import type {importableSuggestions as importableFromResults} from '$lib/features/transactions/bulk/promoteSuggest';

    interface Props {
        bulkTableSelectedRows: PendingOp[];
        importWizardOpen: boolean;
        maxDeltaDays: number;
        pendingSplits: {id_a: number; id_b: number; originalType: string}[];
        tableRef: DataTable<PendingOp> | undefined;
        importableSuggestions: ReturnType<typeof importableFromResults>;
        /** 66 C22: the merge button — absent, off with a reason (`promoteHint`), or on. */
        selectedForPromote: PromoteSelection;
        promoteHint: string;
        tableRefForToggle: never;
        visibleOps: PendingOp[];
        deriveStatus: (d: PendingOp) => 'new' | 'edited' | 'original' | 'delete';
        executeBulkDeleteOnSelected: () => void;
        /** 66 F7-d: «Link» on the selection (U3) — hidden, off with a reason (`linkHint`), or on. */
        linkState: BulkLinkSelection;
        linkHint: string;
        onLinkCharges: () => void;
        handlePromoteSelected: () => void;
        openAddRowForm: () => void;
        openPicker: () => void;
        openSuggestPicker: () => void;
        resetAll: () => void;
        /** 66 C22 (§5.1): one reset of the whole selection, so its order never changes the outcome. */
        resetRows: (tempIds: string[]) => void;
    }

    let {
        bulkTableSelectedRows = $bindable(),
        importWizardOpen = $bindable(),
        maxDeltaDays = $bindable(),
        pendingSplits,
        tableRef,
        importableSuggestions,
        selectedForPromote,
        promoteHint,
        tableRefForToggle,
        visibleOps,
        deriveStatus,
        executeBulkDeleteOnSelected,
        linkState,
        linkHint,
        onLinkCharges,
        handlePromoteSelected,
        openAddRowForm,
        openPicker,
        openSuggestPicker,
        resetAll,
        resetRows,
    }: Props = $props();
</script>

{#snippet promoteButton()}
    {@const off = selectedForPromote.kind === 'disabled'}
    <button
        type="button"
        class="inline-flex items-center gap-1 px-2 py-1 rounded text-indigo-600 dark:text-indigo-400 hover:bg-indigo-50 dark:hover:bg-indigo-900/20 text-[11px] aria-disabled:opacity-50 aria-disabled:cursor-not-allowed"
        onclick={() => {
            if (selectedForPromote.kind === 'ok') handlePromoteSelected();
        }}
        aria-disabled={off ? 'true' : undefined}
        aria-label={selectedForPromote.kind === 'disabled' ? `${$t('transactions.actions.promotePair')} — ${selectedForPromote.targetLabel}` : undefined}
        data-reason={selectedForPromote.kind === 'disabled' ? selectedForPromote.reason : undefined}
        data-testid="promote-toolbar-confirm"
        title={off ? undefined : $t('transactions.actions.promotePair')}
    >
        <Link2 size={12} /> <span class="hidden sm:inline">🔗 {selectedForPromote.kind === 'hidden' ? '' : selectedForPromote.targetLabel}</span>
    </button>
{/snippet}

{#snippet linkButton()}
    {@const off = linkState.kind === 'disabled'}
    <button
        type="button"
        class="inline-flex items-center gap-1 px-2 py-1 rounded text-lf-secondary hover:bg-lf-hover text-[11px] aria-disabled:opacity-50 aria-disabled:cursor-not-allowed"
        onclick={() => {
            if (linkState.kind === 'ok') onLinkCharges();
        }}
        aria-disabled={off ? 'true' : undefined}
        aria-label={$t('transactions.chargesLink.action') || 'Link the charges'}
        title={off ? undefined : $t('transactions.chargesLink.action') || 'Link the charges'}
        data-reason={linkState.kind === 'disabled' ? linkState.reason : undefined}
        data-testid="tx-bulk-link-charges"
    >
        <Link2 size={12} /> <span class="hidden sm:inline">{$t('transactions.chargesLink.actionShort') || 'Link'}</span>
    </button>
{/snippet}

<div class="flex items-center gap-2 px-5 py-3 border-b border-lf-subtle text-xs shrink-0" use:guideAnchor={'transaction.bulk.add_import'}>
    <!-- Left: search & add -->
    {#if txStoreCount() > 0}
        <button type="button" class="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg text-lf-secondary bg-lf-panel hover:bg-lf-neutral" onclick={openPicker} data-testid="tx-bulk-picker" title={$t('transactions.picker.searchAdd') || 'Search & add'}>
            🔍 <span class="hidden sm:inline">{$t('transactions.picker.searchAdd') || 'Search & add'}</span>
        </button>
    {/if}

    <!-- R3-B5: Delta-days filter for promote suggestions -->
    <div class="inline-flex items-center gap-1.5 text-[11px] text-lf-muted">
        <span class="hidden sm:inline">{$t('transactions.promoteSuggest.deltaLabel') || 'Max Δ days'}</span>
        <span class="sm:hidden" title="Max delta days">Δ</span>
        <input type="range" min="0" max="14" step="1" class="w-20 accent-lf-checked" bind:value={maxDeltaDays} data-testid="promote-suggest-delta-input" />
        <span class="text-[11px] font-mono w-5 text-center">{maxDeltaDays}</span>
    </div>

    <!-- Inline selection toolbar moved to Right group below -->

    <!-- Right: actions -->
    <div class="ml-auto flex flex-row-reverse items-center gap-2 flex-wrap">
        <button type="button" class="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg bg-lf-action text-lf-on-action hover:bg-lf-action-hover" onclick={openAddRowForm} data-testid="tx-bulk-add-row" title={$t('common.addRow') || 'Add row'}>
            <Plus size={12} /> <span class="hidden sm:inline">{$t('common.addRow') || 'Add row'}</span>
        </button>
        <button type="button" class="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg text-lf-secondary hover:bg-lf-hover border border-lf-subtle" onclick={() => (importWizardOpen = true)} data-testid="tx-bulk-import" title={$t('common.import') || 'Import'}>
            <Upload size={12} /> <span class="hidden sm:inline">{$t('common.import') || 'Import'}</span>
        </button>
        {#if importableSuggestions.length > 0}
            <button
                type="button"
                class="inline-flex items-center gap-1 px-2 py-1.5 rounded-lg text-lf-warning hover:bg-lf-warning-soft border border-lf-warning-line"
                onclick={openSuggestPicker}
                data-testid="tx-bulk-suggest-import"
                title={$t('transactions.bulk.suggestLightbulb') || 'Import suggested pairs'}
            >
                <Lightbulb size={14} />
                <span class="text-[10px] font-medium">{importableSuggestions.reduce((n, s) => n + s.candidates.length, 0)}</span>
            </button>
        {/if}
        {#if visibleOps.some((d) => d.op === 'edit' && (deriveStatus(d) === 'edited' || deriveStatus(d) === 'delete')) || pendingSplits.length > 0}
            <button type="button" class="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg text-lf-secondary hover:bg-lf-hover" onclick={resetAll} data-testid="tx-bulk-reset-all" title={$t('common.resetAllChanges')}>
                <Undo2 size={12} /> <span class="hidden sm:inline">{$t('common.resetAllChanges')}</span>
            </button>
        {/if}
        <ColumnVisibilityToggle tableRef={tableRefForToggle} />
        {#if bulkTableSelectedRows.length > 0}
            <div class="flex items-center gap-2" use:guideAnchor={'transaction.bulk.selection'}>
                <button
                    type="button"
                    class="inline-flex items-center gap-1 px-2 py-1 rounded text-lf-secondary bg-lf-panel hover:bg-lf-neutral text-[11px]"
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
                        class="inline-flex items-center gap-1 px-2 py-1 rounded text-lf-secondary hover:bg-lf-hover text-[11px]"
                        onclick={() => resetRows(bulkTableSelectedRows.map((r) => r.tempId))}
                        title={$t('transactions.bulk.resetSelected') || 'Reset selected'}
                        data-testid="tx-bulk-reset-selected"
                    >
                        <Undo2 size={12} /> <span class="hidden sm:inline">{$t('transactions.bulk.resetSelected') || 'Reset'}</span>
                    </button>
                {/if}
                {#if linkState.kind !== 'hidden'}
                    {#if linkState.kind === 'disabled'}
                        <!-- Off with a reason (the F7-a pattern): `aria-disabled`, so the click and the tap open the reason. -->
                        <Tooltip text={linkHint} interactiveChild>
                            {@render linkButton()}
                        </Tooltip>
                    {:else}
                        {@render linkButton()}
                    {/if}
                {/if}
                <button type="button" class="inline-flex items-center gap-1 px-2 py-1 rounded text-lf-danger hover:bg-lf-danger-soft text-[11px]" onclick={executeBulkDeleteOnSelected} title={$t('transactions.bulk.deleteSelected') || 'Delete selected'} data-testid="tx-bulk-delete-selected">
                    <Trash2 size={12} /> <span class="hidden sm:inline">{$t('common.delete') || 'Delete'}</span>
                </button>
                {#if selectedForPromote.kind === 'disabled'}
                    <!-- 66 C22: off with a reason (the F7-a pattern, as «Link»): `aria-disabled`, so the click and the tap open it. -->
                    <Tooltip text={promoteHint} interactiveChild>
                        {@render promoteButton()}
                    </Tooltip>
                {:else if selectedForPromote.kind === 'ok'}
                    {@render promoteButton()}
                {/if}
            </div>
        {/if}
    </div>
</div>
