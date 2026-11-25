<!--
  CheckMenu — one filter of a picker, as a compact multi-choice menu. Moved from the Asset Global
  lab (`risk/LabCheckMenu.svelte`), unchanged but for its test ids, which derive from `testId`.

  Filters drawn as a row of chips per criterion, one chip per value, grow with the catalogue. Here
  each criterion is one button; its values open under it, with their icon and how many assets carry
  them. An empty choice means "every value", as `applyFilters` reads it, and the button says how many
  values are on.

  Test ids: `{testId}-button`, `{testId}-panel`, `{testId}-clear`, and one `{testId}-{value}` per
  value, the only ones carrying `aria-pressed`.

  The value rows stay hand-written (checkbox-like rows: a square, an icon, a count). The clear is the standard `Button`
  (85 BTN-2c), never `pressed`: a test finds the options by `[aria-pressed]` under the same prefix.
-->
<script lang="ts">
    import {Check} from 'lucide-svelte';
    import type {ComponentType} from 'svelte';

    import Button from '$lib/components/ui/button/Button.svelte';
    import FilterButton from './FilterButton.svelte';
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
        /** Open in viewport coordinates, out of any clipping parent: for a menu inside a panel that clips (`overflow-hidden`), where a short list would cut it. */
        floating?: boolean;
    }

    let {label, icon, items, selected, ontoggle, onclear, clearLabel, testId, floating = false}: Props = $props();

    let active = $derived(selected.length > 0);
</script>

<SelectPopover testId="{testId}-panel" panelClass="w-60" placement={floating ? {position: 'auto', minWidth: 240} : undefined}>
    {#snippet trigger({open, toggle})}
        <FilterButton {label} {icon} count={selected.length} expanded={open} onclick={toggle} testId="{testId}-button" />
    {/snippet}

    {#snippet children()}
        <div class="max-h-64 overflow-y-auto p-1">
            {#each items as item (item.value)}
                {@const on = selected.includes(item.value)}
                <button type="button" class="flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left text-[13px] text-lf-secondary hover:bg-lf-hover" aria-pressed={on} onclick={() => ontoggle(item.value)} data-testid="{testId}-{item.value}">
                    <span class="flex h-4 w-4 shrink-0 items-center justify-center rounded-sm border transition-colors {on ? 'border-lf-checked bg-lf-checked text-lf-on-checked' : 'border-lf-input bg-lf-field'}">
                        {#if on}<Check size={12} />{/if}
                    </span>
                    {#if item.iconUrl}
                        <img src={item.iconUrl} alt="" class="h-4 w-4 shrink-0 object-contain" />
                    {:else if item.glyph}
                        <span class="w-4 shrink-0 text-center leading-none" aria-hidden="true">{item.glyph}</span>
                    {/if}
                    <span class="min-w-0 flex-1 truncate">{item.label}</span>
                    {#if item.count !== undefined}
                        <span class="font-mono text-[10px] tabular-nums text-lf-muted">{item.count}</span>
                    {/if}
                </button>
            {/each}
        </div>
        {#if active}
            <!-- At its own width, so it sits left without fighting the recipe's `justify-center`; the wrapper keeps the place. -->
            <div class="border-t border-lf-subtle px-3 py-2">
                <Button label={clearLabel} variant="link" size="sm" dense onclick={onclear} data-testid="{testId}-clear" />
            </div>
        {/if}
    {/snippet}
</SelectPopover>
