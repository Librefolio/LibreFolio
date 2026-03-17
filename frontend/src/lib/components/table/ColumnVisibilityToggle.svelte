<!--
  ColumnVisibilityToggle — Standalone eye icon button with dropdown
  for toggling DataTable column visibility.

  Usage:
    <DataTable bind:this={tableRef} showToolbar={false} ... />
    <ColumnVisibilityToggle {tableRef} />

  Connects to a DataTable instance via its exported public API
  (getColumnsForVisibility, toggleColumnVisibilityById).

  Uses Svelte 5 runes.
-->
<script lang="ts">
    import {Eye} from 'lucide-svelte';
    import type DataTable from './DataTable.svelte';

    // =========================================================================
    // Props
    // =========================================================================

    interface Props {
        /** Reference to the DataTable instance to control */
        tableRef?: DataTable<any>;
        /** Optional extra CSS classes for the trigger button */
        class?: string;
    }

    let {
        tableRef,
        class: extraClass = '',
    }: Props = $props();

    // =========================================================================
    // State
    // =========================================================================

    let open = $state(false);
    let triggerEl: HTMLButtonElement | undefined = $state(undefined);
    let dropdownStyle = $state('');

    function toggle() {
        if (!open) {
            updatePosition();
        }
        open = !open;
    }

    function close() {
        open = false;
    }

    function updatePosition() {
        if (!triggerEl) return;
        const rect = triggerEl.getBoundingClientRect();
        const dropW = 200;
        const left = Math.max(8, Math.min(rect.left, window.innerWidth - dropW - 8));
        const top = rect.bottom + 4;
        dropdownStyle = `position: fixed; top: ${top}px; left: ${left}px; z-index: 9999; min-width: ${dropW}px;`;
    }

    function handleToggleColumn(columnId: string) {
        tableRef?.toggleColumnVisibilityById(columnId);
        // Force reactivity: re-read after toggle
        open = open; // no-op but keeps dropdown alive
    }
</script>

<button
    bind:this={triggerEl}
    type="button"
    class="flex items-center gap-1 px-2.5 py-1.5 text-xs bg-white dark:bg-slate-700 border border-gray-200 dark:border-slate-600 rounded-lg hover:bg-gray-50 dark:hover:bg-slate-600 text-gray-600 dark:text-gray-300 transition-colors {extraClass}"
    onclick={toggle}
    title="Column visibility"
>
    <Eye size={13} />
</button>

{#if open}
    <!-- Backdrop -->
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <!-- svelte-ignore a11y_click_events_have_key_events -->
    <div class="fixed inset-0 z-[9998]" onclick={close}></div>

    <!-- Dropdown -->
    <div
        class="bg-white dark:bg-slate-700 border border-gray-200 dark:border-slate-600 rounded-lg shadow-lg p-2"
        style={dropdownStyle}
    >
        {#each tableRef?.getColumnsForVisibility() ?? [] as col}
            <label class="flex items-center gap-2 px-2 py-1 text-xs text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-slate-600 rounded cursor-pointer">
                <input
                    type="checkbox"
                    checked={col.visible}
                    onchange={() => handleToggleColumn(col.id)}
                    class="rounded border-gray-300 dark:border-slate-500"
                />
                {typeof col.header === 'function' ? col.header() : col.header}
            </label>
        {/each}
    </div>
{/if}


