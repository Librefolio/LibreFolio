<script lang="ts">
    import {SvelteSet} from 'svelte/reactivity';
    import {t} from '$lib/i18n';
    import {DIMENSION_FALLBACKS} from '../labels';
    import type {PacExposureRow} from '../types';
    import {BUTTON_LINK, HINT} from '../ui';
    import {exposureGroups, UNCATEGORISED_CATEGORY_ID, type WeightRow} from './model';
    import WeightBars from './WeightBars.svelte';
    const PLANNER_KEY = 'tools.pacAllocator.planner';

    interface Props {
        rows: readonly PacExposureRow[];
    }

    let {rows}: Props = $props();

    const groups = $derived(exposureGroups(rows));
    /** Folded "nothing declared" dimensions the user chose to expand. */
    const expanded = new SvelteSet<string>();

    function label(row: PacExposureRow): string {
        // The backend sends a fixed English label for the undeclared share: the interface translates it.
        return row.category_id === UNCATEGORISED_CATEGORY_ID ? $t(`${PLANNER_KEY}.result.exposures.uncategorised`, {default: 'Uncategorised'}) : row.label;
    }

    function weightRows(group: PacExposureRow[]): WeightRow[] {
        return group.map((row) => ({id: row.category_id, label: label(row), target: row.target_weight, final: row.final_weight}));
    }
</script>

<div class="space-y-5" data-testid="pac-planner-exposures">
    <p class={HINT}>{$t(`${PLANNER_KEY}.result.exposures.public`, {default: 'Public weights: identical with privacy on.'})}</p>
    {#each groups as group (group.dimension)}
        <div data-testid="pac-planner-exposures-dimension" data-dimension={group.dimension} data-folded={group.onlyUncategorised && !expanded.has(group.dimension) ? 'true' : 'false'}>
            <h4 class="text-sm font-semibold text-gray-900 dark:text-gray-100">{$t(`${PLANNER_KEY}.dimensions.${group.dimension}`, {default: DIMENSION_FALLBACKS[group.dimension]})}</h4>
            {#if group.rows.length === 0}
                <p class="mt-1 {HINT}">—</p>
            {:else if group.onlyUncategorised && !expanded.has(group.dimension)}
                <p class="mt-1 flex flex-wrap items-center gap-2 text-sm text-gray-700 dark:text-gray-300">
                    {$t(`${PLANNER_KEY}.result.exposures.nothingDeclared`, {default: 'No classification declared · 100% uncategorised'})}
                    <button type="button" class={BUTTON_LINK} data-testid="pac-planner-exposures-show" onclick={() => expanded.add(group.dimension)}>
                        {$t(`${PLANNER_KEY}.actions.show`, {default: 'Show'})}
                    </button>
                </p>
            {:else}
                <div class="mt-2">
                    <WeightBars rows={weightRows(group.rows)} testid="pac-planner-exposures-bars" />
                </div>
            {/if}
        </div>
    {/each}
    <p class={HINT}>{$t(`${PLANNER_KEY}.result.exposures.uncategorisedHint`, {default: '“Uncategorised” is the share with no declared classification.'})}</p>
</div>
