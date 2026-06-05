<!--
  DataTableToolbar - Compact toolbar showing selection counter and bulk actions.
  Shown when rows are selected and bulkActions are defined.
-->
<script lang="ts">
    import {t} from '$lib/i18n';
    import Tooltip from '$lib/components/ui/feedback/Tooltip.svelte';

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

<div class="toolbar">
    <div class="toolbar-right">
        {#if selectedCount > 0}
            <button type="button" class="selected-count-btn" onclick={() => onClearSelection?.()} title={$t('table.clearSelection') || 'Clear selection'}>
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
        background: rgba(26, 64, 49, 0.1);
        font-size: 0.8125rem;
        color: #1a4031;
        font-weight: 500;
        cursor: pointer;
        transition: all 0.15s;
    }

    .selected-count-btn:hover {
        background: rgba(26, 64, 49, 0.15);
        border-color: rgba(26, 64, 49, 0.2);
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
        background: rgba(74, 222, 128, 0.1);
        color: #4ade80;
    }

    :global(.dark) .selected-count-btn:hover {
        background: rgba(74, 222, 128, 0.15);
        border-color: rgba(74, 222, 128, 0.2);
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
        background: #f1f5f9;
        color: #64748b;
        cursor: pointer;
        transition: all 0.15s;
    }

    .bulk-btn:hover {
        background: #e2e8f0;
        color: #0f172a;
    }

    .bulk-btn.danger {
        color: #dc2626;
    }

    .bulk-btn.danger:hover {
        background: #fef2f2;
        color: #b91c1c;
    }

    :global(.dark) .bulk-btn {
        background: #334155;
        color: #94a3b8;
    }

    :global(.dark) .bulk-btn:hover {
        background: #475569;
        color: #f1f5f9;
    }

    :global(.dark) .bulk-btn.danger {
        color: #f87171;
    }

    :global(.dark) .bulk-btn.danger:hover {
        background: #7f1d1d;
        color: #fecaca;
    }
</style>
