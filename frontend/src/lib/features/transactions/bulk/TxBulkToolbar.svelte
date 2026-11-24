<!--
  TxBulkToolbar — the toolbar of the bulk workspace: search and add on the left, the workspace's actions on the right.
  The selection's actions are the table's selection panel (77 SEL-E): the bar at the top of the table, the balloon when it
  scrolls away.

  Cut from TransactionBulkModal.svelte (FE8a): the modal owns the state and the handlers; this
  section reads them as props, writes the bound ones back, and calls the handlers.
-->
<script lang="ts">
    import {_ as t} from '$lib/i18n';
    import {Plus, Undo2, Lightbulb, Upload} from 'lucide-svelte';
    import ColumnVisibilityToggle from '$lib/components/table/ColumnVisibilityToggle.svelte';
    import {txStoreCount} from '$lib/features/transactions/txStore.svelte';
    import {guideAnchor} from '$lib/features/onboarding/guideAnchors.svelte';
    import type {PendingOp} from './txBulkTypes';
    import type {importableSuggestions as importableFromResults} from '$lib/features/transactions/bulk/promoteSuggest';

    interface Props {
        importWizardOpen: boolean;
        maxDeltaDays: number;
        pendingSplits: {id_a: number; id_b: number; originalType: string}[];
        importableSuggestions: ReturnType<typeof importableFromResults>;
        tableRefForToggle: never;
        visibleOps: PendingOp[];
        deriveStatus: (d: PendingOp) => 'new' | 'edited' | 'original' | 'delete';
        openAddRowForm: () => void;
        openPicker: () => void;
        openSuggestPicker: () => void;
        resetAll: () => void;
    }

    let {importWizardOpen = $bindable(), maxDeltaDays = $bindable(), pendingSplits, importableSuggestions, tableRefForToggle, visibleOps, deriveStatus, openAddRowForm, openPicker, openSuggestPicker, resetAll}: Props = $props();
</script>

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
    </div>
</div>
