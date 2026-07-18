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
    let dropdownStyle = $state('');
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
        const margin = 8;
        // Must match the dropdown's CSS `max-h-[400px]` cap (bugfix: this was previously
        // 300, which under-estimated the real height for tables with many columns — e.g.
        // the lots table's 13 columns push the rendered list past 300px — causing the
        // "open above" branch to compute a negative `bottom`/off-screen `top` and render
        // the dropdown fully or partially outside the viewport, i.e. invisible.
        const dropH = 400;
        const spaceBelow = window.innerHeight - rect.bottom - margin;
        const spaceAbove = rect.top - margin;
        const openAbove = spaceBelow < dropH && spaceAbove > spaceBelow;
        const preferredTop = openAbove ? rect.top - dropH - 4 : rect.bottom + 4;
        // Clamp so the dropdown always stays fully within the viewport vertically,
        // regardless of where the trigger button sits (even near the top/bottom edge).
        const maxTop = Math.max(margin, window.innerHeight - dropH - margin);
        const top = Math.min(Math.max(preferredTop, margin), maxTop);
        const right = window.innerWidth - rect.right;
        dropdownStyle = `position: fixed; top: ${top}px; right: ${right}px; z-index: 9999;`;
    }

    // Keep the dropdown anchored to the trigger while the page scrolls (ignore internal
    // dropdown scrolling). Bugfix: this used to *close* the dropdown on any scroll, which
    // raced with scroll-into-view side effects that can happen right as/after the trigger
    // is clicked (e.g. bringing an off-screen button into view), instantly re-closing a
    // dropdown that had just opened — looking like the click "did nothing".
    $effect(() => {
        if (!open) return;
        const handleScroll = (e: Event) => {
            if (dropdownRef && dropdownRef.contains(e.target as Node)) return;
            updatePosition();
        };
        window.addEventListener('scroll', handleScroll, true);
        return () => window.removeEventListener('scroll', handleScroll, true);
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
    <div bind:this={dropdownRef} class="bg-white dark:bg-slate-700 border border-gray-200 dark:border-slate-600 rounded-lg shadow-lg p-2 max-h-[400px] overflow-y-auto w-max" style={dropdownStyle} onclick={(e) => e.stopPropagation()}>
        <OrderableList items={columnItems} keyFn={(c) => c.id} onReorder={handleReorder} compact={true}>
            {#snippet children({item})}
                <!-- svelte-ignore a11y_no_static_element_interactions -->
                <!-- svelte-ignore a11y_click_events_have_key_events -->
                <div class="flex items-center gap-2 text-xs text-gray-700 dark:text-gray-300 cursor-pointer select-none whitespace-nowrap" onclick={() => handleToggleColumn(item.id)}>
                    {#if item.visible}
                        <Eye size={13} class="text-libre-green shrink-0" />
                    {:else}
                        <EyeOff size={13} class="text-gray-400 dark:text-gray-500 shrink-0" />
                    {/if}
                    <span class={item.visible ? '' : 'text-gray-400 dark:text-gray-500 line-through'}>{item.label}</span>
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
