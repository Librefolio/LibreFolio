<!--
  ColumnVisibilityToggle — Standalone eye icon button with dropdown
  for toggling DataTable column visibility and reordering via OrderableList.

  Uses Svelte 5 runes.
-->
<script lang="ts">
    import {Eye, EyeOff, RotateCcw} from 'lucide-svelte';
    import {_ as t} from '$lib/i18n';
    import type DataTable from './DataTable.svelte';
    import OrderableList from '$lib/components/ui/OrderableList.svelte';

    // =========================================================================
    // Props
    // =========================================================================

    interface Props {
        tableRef?: DataTable<any>;
        showLabel?: boolean;
        class?: string;
    }

    let {
        tableRef,
        showLabel = false,
        class: extraClass = '',
    }: Props = $props();

    // =========================================================================
    // Types
    // =========================================================================

    interface ColumnItem {
        id: string;
        label: string;
        visible: boolean;
    }

    // =========================================================================
    // State
    // =========================================================================

    let open = $state(false);
    let triggerEl: HTMLButtonElement | undefined = $state(undefined);
    let dropdownRef: HTMLDivElement | undefined = $state(undefined);
    let dropdownStyle = $state('');
    let columnItems: ColumnItem[] = $state([]);

    function refreshColumns() {
        if (!tableRef) return;
        const cols = tableRef.getColumnsForVisibility();
        columnItems = cols.map(c => ({
            id: c.id,
            label: typeof c.header === 'function' ? c.header() : c.header,
            visible: c.visible,
        }));
    }

    function toggle() {
        if (!open) {
            updatePosition();
            refreshColumns();
        }
        open = !open;
    }

    function close() {
        open = false;
    }

    function updatePosition() {
        if (!triggerEl) return;
        const rect = triggerEl.getBoundingClientRect();
        const dropH = 300; // estimated max dropdown height
        const spaceBelow = window.innerHeight - rect.bottom - 8;
        const spaceAbove = rect.top - 8;
        const openAbove = spaceBelow < dropH && spaceAbove > spaceBelow;
        const top = openAbove ? 'auto' : `${rect.bottom + 4}px`;
        const bottom = openAbove ? `${window.innerHeight - rect.top + 4}px` : 'auto';
        const right = window.innerWidth - rect.right;
        dropdownStyle = `position: fixed; top: ${top}; bottom: ${bottom}; right: ${right}px; z-index: 9999;`;
    }

    // Close dropdown on external scroll (ignore internal dropdown scrolling)
    $effect(() => {
        if (!open) return;
        const handleScroll = (e: Event) => {
            if (dropdownRef && dropdownRef.contains(e.target as Node)) return;
            close();
        };
        window.addEventListener('scroll', handleScroll, true);
        return () => window.removeEventListener('scroll', handleScroll, true);
    });

    function handleToggleColumn(columnId: string) {
        tableRef?.toggleColumnVisibilityById(columnId);
        const col = columnItems.find(c => c.id === columnId);
        if (col) col.visible = !col.visible;
        columnItems = [...columnItems];
    }

    function handleReorder(newItems: ColumnItem[]) {
        columnItems = newItems;
        tableRef?.setColumnOrder(newItems.map(c => c.id));
    }

    function handleReset() {
        tableRef?.resetColumnLayout();
        refreshColumns();
    }
</script>

<button
    bind:this={triggerEl}
    type="button"
    class="flex items-center justify-center gap-1 px-2.5 py-1.5 text-xs bg-white dark:bg-slate-700 border border-gray-200 dark:border-slate-600 rounded-lg hover:bg-gray-50 dark:hover:bg-slate-600 text-gray-600 dark:text-gray-300 transition-colors {extraClass}"
    onclick={toggle}
    title="Column visibility"
>
    <Eye size={13} />
    {#if showLabel}<span>{$t('table.columns')}</span>{/if}
</button>

{#if open}
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <!-- svelte-ignore a11y_click_events_have_key_events -->
    <div class="fixed inset-0 z-[9998]" onclick={close}></div>

    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <!-- svelte-ignore a11y_click_events_have_key_events -->
    <div
        bind:this={dropdownRef}
        class="bg-white dark:bg-slate-700 border border-gray-200 dark:border-slate-600 rounded-lg shadow-lg p-2 max-h-[400px] overflow-y-auto w-max"
        style={dropdownStyle}
        onclick={(e) => e.stopPropagation()}
    >
        <OrderableList
            items={columnItems}
            keyFn={(c) => c.id}
            onReorder={handleReorder}
        >
            {#snippet children({ item })}
                <!-- svelte-ignore a11y_no_static_element_interactions -->
                <!-- svelte-ignore a11y_click_events_have_key_events -->
                <div
                    class="flex items-center gap-2 text-xs text-gray-700 dark:text-gray-300 cursor-pointer select-none whitespace-nowrap"
                    onclick={() => handleToggleColumn(item.id)}
                >
                    {#if item.visible}
                        <Eye size={13} class="text-libre-green shrink-0" />
                    {:else}
                        <EyeOff size={13} class="text-gray-400 dark:text-gray-500 shrink-0" />
                    {/if}
                    <span class="{item.visible ? '' : 'text-gray-400 dark:text-gray-500 line-through'}">{item.label}</span>
                </div>
            {/snippet}
        </OrderableList>

        <button
            type="button"
            class="w-full flex items-center justify-center gap-1.5 mt-2 px-2 py-1.5 text-xs text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 hover:bg-gray-50 dark:hover:bg-slate-600 rounded-md border border-gray-200 dark:border-slate-600 transition-colors"
            onclick={handleReset}
        >
            <RotateCcw size={12} />
            Reset layout
        </button>
    </div>
{/if}
