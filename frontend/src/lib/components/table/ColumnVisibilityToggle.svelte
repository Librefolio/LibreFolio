<!--
  ColumnVisibilityToggle — Standalone eye icon button with dropdown
  for toggling DataTable column visibility and reordering via OrderableList.

  Uses Svelte 5 runes.
-->
<script lang="ts">
    import {tick} from 'svelte';
    import {Eye, EyeOff, RotateCcw} from 'lucide-svelte';
    import {_ as t} from '$lib/i18n';
    import type DataTable from './DataTable.svelte';
    import OrderableList from '$lib/components/ui/OrderableList.svelte';

    // =========================================================================
    // Props
    // =========================================================================

    interface Props {
        tableRef?: DataTable<any>;
        /** Additional tables whose visibility/order should be synced */
        additionalTableRefs?: (DataTable<any> | undefined)[];
        showLabel?: boolean;
        class?: string;
    }

    let {tableRef, additionalTableRefs = [], showLabel = false, class: extraClass = ''}: Props = $props();

    /** All refs including primary */
    let allRefs = $derived([tableRef, ...additionalTableRefs].filter((r): r is DataTable<any> => !!r));

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
    let dropdownStyle = $state('position: fixed; top: 8px; left: 8px; width: max-content; max-width: calc(100vw - 1rem); z-index: 9999;');
    let columnItems: ColumnItem[] = $state([]);

    function refreshColumns() {
        if (!tableRef) return;
        const cols = tableRef.getColumnsForVisibility();
        columnItems = cols.map((c) => {
            const headerLabel = typeof c.header === 'function' ? c.header() : c.header;
            const displayLabel = c.displayName ? (typeof c.displayName === 'function' ? c.displayName() : c.displayName) : undefined;
            return {
                id: c.id,
                label: displayLabel || headerLabel,
                visible: c.visible,
            };
        });
    }

    async function toggle() {
        if (open) {
            close();
            return;
        }
        refreshColumns();
        open = true;
        await tick();
        updatePosition();
    }

    function close() {
        open = false;
    }

    function updatePosition() {
        if (!triggerEl) return;
        const rect = triggerEl.getBoundingClientRect();
        const margin = 8;
        const maxWidth = Math.max(0, window.innerWidth - margin * 2);
        const dropW = Math.min(dropdownRef?.offsetWidth ?? 320, maxWidth);
        const dropH = Math.min(dropdownRef?.offsetHeight ?? 400, 400);
        const spaceBelow = window.innerHeight - rect.bottom - margin;
        const spaceAbove = rect.top - margin;
        const openAbove = spaceBelow < dropH && spaceAbove > spaceBelow;
        const preferredTop = openAbove ? rect.top - dropH - 4 : rect.bottom + 4;
        const maxTop = Math.max(margin, window.innerHeight - dropH - margin);
        const top = Math.min(Math.max(preferredTop, margin), maxTop);
        const preferredLeft = rect.right - dropW;
        const maxLeft = Math.max(margin, window.innerWidth - dropW - margin);
        const left = Math.min(Math.max(preferredLeft, margin), maxLeft);
        dropdownStyle = `position: fixed; top: ${top}px; left: ${left}px; width: max-content; max-width: calc(100vw - 1rem); z-index: 9999;`;
    }

    // Keep the dropdown anchored to the trigger while the page scrolls (ignore internal
    // dropdown scrolling). Bugfix: this used to *close* the dropdown on any scroll, which
    // raced with scroll-into-view side effects that can happen right as/after the trigger
    // is clicked (e.g. bringing an off-screen button into view), instantly re-closing a
    // dropdown that had just opened — looking like the click "did nothing".
    $effect(() => {
        if (!open) return;
        const handleViewportChange = (e?: Event) => {
            if (dropdownRef && e?.target instanceof Node && dropdownRef.contains(e.target)) return;
            updatePosition();
        };
        window.addEventListener('scroll', handleViewportChange, true);
        window.addEventListener('resize', handleViewportChange);
        return () => {
            window.removeEventListener('scroll', handleViewportChange, true);
            window.removeEventListener('resize', handleViewportChange);
        };
    });

    function handleToggleColumn(columnId: string) {
        for (const ref of allRefs) ref.toggleColumnVisibilityById(columnId);
        const col = columnItems.find((c) => c.id === columnId);
        if (col) col.visible = !col.visible;
        columnItems = [...columnItems];
    }

    function handleReorder(newItems: ColumnItem[]) {
        columnItems = newItems;
        const order = newItems.map((c) => c.id);
        for (const ref of allRefs) ref.setColumnOrder(order);
    }

    function handleReset() {
        for (const ref of allRefs) ref.resetColumnLayout();
        refreshColumns();
    }
</script>

<button
    bind:this={triggerEl}
    class="flex items-center justify-center gap-1 px-2.5 py-1.5 text-xs bg-white dark:bg-slate-700 border border-gray-200 dark:border-slate-600 rounded-lg hover:bg-gray-50 dark:hover:bg-slate-600 text-gray-600 dark:text-gray-300 transition-colors {extraClass}"
    onclick={toggle}
    type="button"
    data-testid="column-visibility-toggle"
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
    <div bind:this={dropdownRef} class="overflow-y-auto rounded-lg border border-gray-200 bg-white p-2 shadow-lg dark:border-slate-600 dark:bg-slate-700 max-h-[400px]" style={dropdownStyle} onclick={(e) => e.stopPropagation()} data-testid="column-visibility-dropdown">
        <OrderableList items={columnItems} keyFn={(c) => c.id} onReorder={handleReorder} compact={true}>
            {#snippet children({item})}
                <!-- svelte-ignore a11y_no_static_element_interactions -->
                <!-- svelte-ignore a11y_click_events_have_key_events -->
                <div class="flex min-w-0 cursor-pointer select-none items-center gap-2 text-xs text-gray-700 whitespace-normal md:whitespace-nowrap dark:text-gray-300" onclick={() => handleToggleColumn(item.id)} data-testid={`column-visibility-item-${item.id}`}>
                    {#if item.visible}
                        <Eye size={13} class="text-libre-green shrink-0" />
                    {:else}
                        <EyeOff size={13} class="text-gray-400 dark:text-gray-500 shrink-0" />
                    {/if}
                    <span class="min-w-0 {item.visible ? '' : 'text-gray-400 dark:text-gray-500 line-through'}">{item.label}</span>
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
