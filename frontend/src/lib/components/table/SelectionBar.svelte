<!--
  SelectionBar — Standalone selection counter + bulk action buttons.

  Designed to be placed externally (like ColumnVisibilityToggle),
  outside of DataTable, for full layout control by the parent.

  Uses Tailwind classes (no scoped CSS) for consistency with the design system.
  Uses Svelte 5 runes.
-->
<script lang="ts">
    import {_ as t} from '$lib/i18n';

    // =========================================================================
    // Types
    // =========================================================================

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    export interface SelectionBarAction {
        id: string;
        /** Icon component (lucide-svelte or similar) */
        icon: any;
        label: string | (() => string);
        variant?: 'default' | 'danger';
        onClick: () => void;
    }

    // =========================================================================
    // Props
    // =========================================================================

    interface Props {
        /** Number of selected rows */
        selectedCount: number;
        /** Bulk actions to show */
        actions?: SelectionBarAction[];
        /** Called when the user clicks the "clear" button */
        onClearSelection?: () => void;
        /** Extra CSS classes */
        class?: string;
    }

    let {
        selectedCount,
        actions = [],
        onClearSelection,
        class: extraClass = '',
    }: Props = $props();

    function getActionLabel(action: SelectionBarAction): string {
        return typeof action.label === 'function' ? action.label() : action.label;
    }
</script>

{#if selectedCount > 0}
    <div class="flex items-center gap-1.5 {extraClass}">
        <!-- Selection counter with clear button -->
        <button
            type="button"
            class="flex items-center gap-1.5 px-2 py-1 rounded-md text-[13px] font-medium
                   bg-libre-green/10 text-libre-green hover:bg-libre-green/15
                   dark:bg-green-400/10 dark:text-green-400 dark:hover:bg-green-400/15
                   transition-colors cursor-pointer border border-transparent hover:border-libre-green/20 dark:hover:border-green-400/20"
            onclick={() => onClearSelection?.()}
            title={$t('table.clearSelection')}
        >
            <span>{selectedCount} {$t('table.selected')}</span>
            <span class="text-base leading-none opacity-60 hover:opacity-100">×</span>
        </button>

        <!-- Bulk action buttons -->
        {#each actions as action}
            <button
                type="button"
                class="flex items-center justify-center w-7 h-7 rounded-md transition-colors
                       {action.variant === 'danger'
                           ? 'text-red-500 bg-gray-100 hover:bg-red-50 hover:text-red-600 dark:bg-slate-700 dark:text-red-400 dark:hover:bg-red-900/30'
                           : 'text-gray-500 bg-gray-100 hover:bg-gray-200 hover:text-gray-700 dark:bg-slate-700 dark:text-gray-400 dark:hover:bg-slate-600 dark:hover:text-gray-200'}"
                onclick={action.onClick}
                title={getActionLabel(action)}
            >
                <action.icon size={16} />
            </button>
        {/each}
    </div>
{/if}


