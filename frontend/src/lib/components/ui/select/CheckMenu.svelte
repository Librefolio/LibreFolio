<!--
  CheckMenu — one filter of a picker, as a compact multi-choice menu. Moved from the Asset Global
  lab (`risk/LabCheckMenu.svelte`), unchanged but for its test ids, which derive from `testId`.

  Filters drawn as a row of chips per criterion, one chip per value, grow with the catalogue. Here
  each criterion is one button; its values open under it, with their icon and how many assets carry
  them. An empty choice means "every value", as `applyFilters` reads it, and the button says how many
  values are on.

  Test ids: `{testId}-button`, `{testId}-panel`, `{testId}-clear`, and one `{testId}-{value}` per
  value, the only ones carrying `aria-pressed`.
-->
<script lang="ts">
    import {Check, ChevronDown} from 'lucide-svelte';
    import type {ComponentType} from 'svelte';

    import SelectPopover from './SelectPopover.svelte';

    export interface CheckMenuItem {
        value: string;
        label: string;
        /** An image (the asset-type icons) or a glyph (the currency flags). */
        iconUrl?: string;
        glyph?: string;
        count?: number;
    }

    interface Props {
        label: string;
        /** A lucide icon, typed as `TabBar` types its own: lucide-svelte still ships class components. */
        icon: ComponentType;
        items: CheckMenuItem[];
        selected: readonly string[];
        ontoggle: (value: string) => void;
        onclear: () => void;
        clearLabel: string;
        testId: string;
    }

    let {label, icon: Icon, items, selected, ontoggle, onclear, clearLabel, testId}: Props = $props();

    let active = $derived(selected.length > 0);
</script>

<SelectPopover testId="{testId}-panel" panelClass="w-60">
    {#snippet trigger({open, toggle})}
        <button
            type="button"
            class="inline-flex items-center gap-1.5 rounded-lg border px-2.5 py-1 text-xs font-medium transition-colors {active
                ? 'border-blue-200 bg-blue-50 text-blue-700 dark:border-blue-700 dark:bg-blue-900/20 dark:text-blue-300'
                : 'border-gray-200 text-gray-600 hover:bg-gray-50 dark:border-slate-600 dark:text-gray-300 dark:hover:bg-slate-700'}"
            aria-expanded={open}
            onclick={toggle}
            data-testid="{testId}-button"
        >
            <Icon size={13} />
            {label}
            {#if active}
                <span class="rounded-full bg-blue-600 px-1.5 text-[10px] font-semibold leading-4 text-white dark:bg-blue-500">{selected.length}</span>
            {/if}
            <ChevronDown size={12} class="transition-transform {open ? 'rotate-180' : ''}" />
        </button>
    {/snippet}

    {#snippet children()}
        <div class="max-h-64 overflow-y-auto p-1">
            {#each items as item (item.value)}
                {@const on = selected.includes(item.value)}
                <button type="button" class="flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left text-[13px] text-gray-700 hover:bg-gray-50 dark:text-gray-200 dark:hover:bg-slate-700" aria-pressed={on} onclick={() => ontoggle(item.value)} data-testid="{testId}-{item.value}">
                    <span
                        class="flex h-4 w-4 shrink-0 items-center justify-center rounded-sm border transition-colors {on
                            ? 'border-libre-green bg-libre-green text-white dark:border-emerald-400 dark:bg-emerald-400 dark:text-slate-900'
                            : 'border-gray-300 bg-white dark:border-slate-500 dark:bg-slate-900'}"
                    >
                        {#if on}<Check size={12} />{/if}
                    </span>
                    {#if item.iconUrl}
                        <img src={item.iconUrl} alt="" class="h-4 w-4 shrink-0 object-contain" />
                    {:else if item.glyph}
                        <span class="w-4 shrink-0 text-center leading-none" aria-hidden="true">{item.glyph}</span>
                    {/if}
                    <span class="min-w-0 flex-1 truncate">{item.label}</span>
                    {#if item.count !== undefined}
                        <span class="font-mono text-[10px] tabular-nums text-gray-400 dark:text-gray-500">{item.count}</span>
                    {/if}
                </button>
            {/each}
        </div>
        {#if active}
            <div class="border-t border-gray-100 p-1 dark:border-slate-700">
                <button type="button" class="w-full rounded-md px-2 py-1 text-left text-xs text-libre-green hover:bg-gray-50 dark:hover:bg-slate-700" onclick={onclear} data-testid="{testId}-clear">
                    {clearLabel}
                </button>
            </div>
        {/if}
    {/snippet}
</SelectPopover>
