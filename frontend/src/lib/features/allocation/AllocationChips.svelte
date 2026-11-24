<!--
  AllocationChips — the choices of the «Allocazione» filters, one chip each, with a cross that takes the choice away
  (lane 80, F2). A class kept reads as its name, a bucket or an asset taken out as «Without …». Nothing is drawn when no
  filter is on. Test ids: `{testId}` (the row), `-chip` (each, with `data-kind` and `data-value`), `-chip-remove`.
-->
<script lang="ts">
    import {X} from 'lucide-svelte';
    import {_} from '$lib/i18n';
    import {filterChips, removeChip, type AllocationChip, type AllocationFilters} from './allocationFilters';
    import type {AllocationResponse} from './allocationQuery';
    import {chipName, chipText, type Translate} from './allocationLabels';

    interface Props {
        filters: AllocationFilters;
        /** The last answer, for the names of assets; absent before the first one (a chip then shows the asset's number). */
        view: AllocationResponse | null;
        onchange: (next: AllocationFilters) => void;
        testId: string;
    }

    let {filters, view, onchange, testId}: Props = $props();

    const t = (key: string, options?: Parameters<Translate>[1]) => $_(key, options as never);
    const chips = $derived(filterChips(filters));
    const assetNames = $derived(new Map((view?.assets ?? []).map((asset) => [asset.asset_id, asset.name])));

    const name = (chip: AllocationChip) => chipName(t, chip, assetNames);
    const text = (chip: AllocationChip) => chipText(t, chip, assetNames);
</script>

{#if chips.length > 0}
    <ul class="flex flex-wrap items-center gap-1.5" data-testid={testId}>
        {#each chips as chip (`${chip.kind}:${chip.value}`)}
            <li class="inline-flex items-center gap-1 rounded-full border border-lf-info-line bg-lf-info-soft py-0.5 pl-2.5 pr-1 text-xs text-lf-info-on-soft" data-testid="{testId}-chip" data-kind={chip.kind} data-value={chip.value}>
                {text(chip)}
                <button
                    type="button"
                    class="inline-flex rounded-full p-0.5 hover:bg-lf-hover focus-visible:outline-2 focus-visible:outline-lf-focus"
                    aria-label={$_('allocation.chip.remove', {values: {name: name(chip)}})}
                    onclick={() => onchange(removeChip(filters, chip))}
                    data-testid="{testId}-chip-remove"
                >
                    <X size={12} aria-hidden="true" />
                </button>
            </li>
        {/each}
    </ul>
{/if}
