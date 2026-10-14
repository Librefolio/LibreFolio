<!--
  DataTableToolbar - Compact toolbar showing selection counter and bulk actions.
  Shown when rows are selected and bulkActions are defined.
-->
<script lang="ts">
    import {t} from '$lib/i18n';
    import Tooltip from '$lib/components/ui/feedback/Tooltip.svelte';
    import '$lib/theme/components/table.css';

    interface BulkActionInfo {
        id: string;
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        icon: any;
        label: string | (() => string);
        variant?: 'default' | 'danger';
        onClick: () => void;
        /** CSS class applied to the icon (e.g. 'animate-spin' for loading) */
        iconClass?: string;
        /** Disable the button */
        disabled?: boolean;
    }

    interface Props {
        selectedCount: number;
        bulkActions: BulkActionInfo[];
        onClearSelection?: () => void;
    }

    let {selectedCount, bulkActions, onClearSelection}: Props = $props();

    function getActionLabel(action: BulkActionInfo): string {
        return typeof action.label === 'function' ? action.label() : action.label;
    }
</script>

<div class="toolbar" data-testid="selection-toolbar" data-selected-count={selectedCount}>
    <div class="toolbar-right">
        {#if selectedCount > 0}
            <button type="button" class="selected-count-btn" onclick={() => onClearSelection?.()} title={$t('common.clearSelection') || 'Clear selection'}>
                <span class="count-text">{selectedCount} {$t('common.selected')}</span>
                <span class="clear-icon">×</span>
            </button>
            <div class="bulk-actions">
                {#each bulkActions as action}
                    <Tooltip text={getActionLabel(action)}>
                        <button type="button" class="bulk-btn" class:danger={action.variant === 'danger'} onclick={action.onClick} disabled={action.disabled} data-testid="toolbar-action-{action.id}">
                            <action.icon size={16} class={action.iconClass || ''} />
                        </button>
                    </Tooltip>
                {/each}
            </div>
        {/if}
    </div>
</div>

<style>
    .toolbar {
        display: flex;
        justify-content: flex-end;
        align-items: center;
        padding: 0.375rem 0;
        gap: 0.75rem;
    }

    .toolbar-right {
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }

    .selected-count-btn {
        display: flex;
        align-items: center;
        gap: 0.375rem;
        padding: 0.25rem 0.5rem;
        border: 1px solid transparent;
        border-radius: 6px;
        background: var(--lf-cmp-datatable-toolbar-selected-count-btn-bg);
        font-size: 0.8125rem;
        color: var(--lf-cmp-datatable-toolbar-selected-count-btn-text);
        font-weight: 500;
        cursor: pointer;
        transition: all 0.15s;
    }

    .selected-count-btn:hover {
        background: var(--lf-cmp-datatable-toolbar-selected-count-btn-hover-bg);
        border-color: var(--lf-cmp-datatable-toolbar-selected-count-btn-hover-border);
    }

    .selected-count-btn .clear-icon {
        font-size: 1rem;
        line-height: 1;
        opacity: 0.6;
    }

    .selected-count-btn:hover .clear-icon {
        opacity: 1;
    }

    :global(.dark) .selected-count-btn {
        background: var(--lf-cmp-datatable-toolbar-selected-count-btn-bg-dark);
        color: var(--lf-cmp-datatable-toolbar-selected-count-btn-text-dark);
    }

    :global(.dark) .selected-count-btn:hover {
        background: var(--lf-cmp-datatable-toolbar-selected-count-btn-hover-bg-dark);
        border-color: var(--lf-cmp-datatable-toolbar-selected-count-btn-hover-border-dark);
    }

    .bulk-actions {
        display: flex;
        gap: 0.25rem;
    }

    .bulk-btn {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 28px;
        height: 28px;
        border: none;
        border-radius: 6px;
        background: var(--lf-cmp-datatable-toolbar-bulk-btn-bg);
        color: var(--lf-cmp-datatable-toolbar-bulk-btn-text);
        cursor: pointer;
        transition: all 0.15s;
    }

    .bulk-btn:hover {
        background: var(--lf-cmp-datatable-toolbar-bulk-btn-hover-bg);
        color: var(--lf-cmp-datatable-toolbar-bulk-btn-hover-text);
    }

    .bulk-btn.danger {
        color: var(--lf-cmp-datatable-toolbar-bulk-btn-danger-text);
    }

    .bulk-btn.danger:hover {
        background: var(--lf-cmp-datatable-toolbar-bulk-btn-danger-hover-bg);
        color: var(--lf-cmp-datatable-toolbar-bulk-btn-danger-hover-text);
    }

    :global(.dark) .bulk-btn {
        background: var(--lf-cmp-datatable-toolbar-bulk-btn-bg-dark);
        color: var(--lf-cmp-datatable-toolbar-bulk-btn-text-dark);
    }

    :global(.dark) .bulk-btn:hover {
        background: var(--lf-cmp-datatable-toolbar-bulk-btn-hover-bg-dark);
        color: var(--lf-cmp-datatable-toolbar-bulk-btn-hover-text-dark);
    }

    :global(.dark) .bulk-btn.danger {
        color: var(--lf-cmp-datatable-toolbar-bulk-btn-danger-text-dark);
    }

    :global(.dark) .bulk-btn.danger:hover {
        background: var(--lf-cmp-datatable-toolbar-bulk-btn-danger-hover-bg-dark);
        color: var(--lf-cmp-datatable-toolbar-bulk-btn-danger-hover-text-dark);
    }
</style>
