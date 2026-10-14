<!--
  R9.8: the exposures of the plan, ideal vs actual (R11.7). Countries on two maps (one colour scale),
  Asset types and sectors as bars (the two distributions side by side). The weights are the backend's, exact;
  the charts only draw them, and an accessible list under each chart carries the same numbers.
-->
<script lang="ts">
    import {untrack} from 'svelte';
    import {SvelteSet} from 'svelte/reactivity';
    import {t} from '$lib/i18n';
    import {currentLanguage} from '$lib/stores/app/language';
    import {CategoryLabels} from '../categoryLabels.svelte';
    import {EXPOSURE_DIMENSIONS, type ExposureDimension} from '../draft.svelte';
    import {formatExactPercent} from '../format';
    import {DIMENSION_FALLBACKS} from '../labels';
    import type {PacExposureRow} from '../types';
    import {BUTTON_LINK, HINT} from '../ui';
    import ExposureBars from './ExposureBars.svelte';
    import ExposureMaps from './ExposureMaps.svelte';
    import {exposureTooltipText} from './exposureTooltip';
    import {exposureGroups, UNCATEGORISED_CATEGORY_ID, type MapWeightRow} from './model';
    const PLANNER_KEY = 'tools.pacAllocator.planner';

    interface Props {
        rows: readonly PacExposureRow[];
    }

    let {rows}: Props = $props();

    /** Folded "nothing declared" dimensions the user chose to expand. */
    const expanded = new SvelteSet<string>();
    const labels = new CategoryLabels();

    $effect(() => {
        const language = $currentLanguage;
        untrack(() => labels.load(language));
    });

    function label(row: PacExposureRow): string {
        // The backend sends a fixed English label for the undeclared share: the interface translates it.
        if (row.category_id === UNCATEGORISED_CATEGORY_ID) return $t(`${PLANNER_KEY}.result.exposures.uncategorised`, {default: 'Uncategorised'});
        // A type, sector or country code reads in the user's language, as on the Asset pages.
        return (EXPOSURE_DIMENSIONS as readonly string[]).includes(row.dimension) ? labels.text($t, row.dimension as ExposureDimension, row.label) : row.label;
    }

    /** The countries first, on the whole width; types and sectors side by side under them. */
    const views = $derived(
        exposureGroups(rows)
            .sort((a, b) => Number(b.dimension === 'geography') - Number(a.dimension === 'geography'))
            .map((group) => ({
                ...group,
                folded: group.onlyUncategorised && !expanded.has(group.dimension),
                weights: group.rows.map((row): MapWeightRow => ({id: row.category_id, code: row.category_id, label: label(row), target: row.target_weight, final: row.final_weight})),
            })),
    );
    const words = $derived(exposureTooltipText($t));

    function finalText(row: MapWeightRow): string {
        return row.final.kind === 'available' ? formatExactPercent(row.final.value) : `— (${words.unavailable[row.final.reason]})`;
    }
</script>

<div class="space-y-4" data-testid="pac-planner-exposures">
    <div class="grid grid-cols-1 gap-x-6 gap-y-5 lg:grid-cols-2">
        {#each views as view (view.dimension)}
            <div class="min-w-0 {view.dimension === 'geography' ? 'lg:col-span-2' : ''}" data-testid="pac-planner-exposures-dimension" data-dimension={view.dimension} data-folded={view.folded ? 'true' : 'false'}>
                <h4 class="text-sm font-semibold text-gray-900 dark:text-gray-100">{$t(`${PLANNER_KEY}.dimensions.${view.dimension}`, {default: DIMENSION_FALLBACKS[view.dimension]})}</h4>
                {#if view.weights.length === 0}
                    <p class="mt-1 {HINT}">—</p>
                {:else if view.folded}
                    <p class="mt-1 flex flex-wrap items-center gap-2 text-sm text-gray-700 dark:text-gray-300">
                        {$t(`${PLANNER_KEY}.result.exposures.nothingDeclared`, {default: 'No classification declared · 100% uncategorised'})}
                        <button type="button" class={BUTTON_LINK} data-testid="pac-planner-exposures-show" onclick={() => expanded.add(view.dimension)}>
                            {$t(`${PLANNER_KEY}.actions.show`, {default: 'Show'})}
                        </button>
                    </p>
                {:else}
                    <div class="mt-2">
                        {#if view.dimension === 'geography'}
                            <ExposureMaps rows={view.weights} />
                        {:else}
                            <ExposureBars rows={view.weights} dimension={view.dimension} />
                        {/if}
                    </div>
                    <ul class="sr-only" data-testid="pac-planner-exposures-values">
                        {#each view.weights as row (row.id)}
                            <li data-testid="pac-planner-exposures-row" data-id={row.id}>{row.label}: {words.target} {formatExactPercent(row.target)}, {words.final} {finalText(row)}</li>
                        {/each}
                    </ul>
                {/if}
            </div>
        {/each}
    </div>
    <p class={HINT}>{$t(`${PLANNER_KEY}.result.exposures.uncategorisedHint`, {default: '“Uncategorised” is the share with no declared classification.'})}</p>
</div>
