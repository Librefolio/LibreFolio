<!--
  R9.8: the exposures of the plan, ideal vs actual (R11.7). Countries on two maps (one colour scale),
  Asset types and sectors as bars (the two distributions side by side). The weights are the backend's, exact;
  the charts only draw them, and an accessible list under each chart carries the same numbers.
  The Rebalancer (F4a of project 67, step 8): today, after the plan and the target of every category, the cash the last
  row, as a bullet chart in all three dimensions, on the whole portfolio, its legend once above them. The countries are also
  on the two maps, target and after the plan, under their bullets (R1-D of project 67: F4a said «no maps»; the developer,
  20/11: «per l'area geografica mi aspettavo comunque la mappa doppia … magari sotto a questo a proiettile»). «Today» stays
  in the bullets; the cash, which is no place, too.
  TL-5 of project 67 (the developer, 23/11: «la mappa geografica e le sue barre falle come ti ho detto in pac e
  ribilanciatore»): one layout in both Tools — types and sectors side by side, then the countries on the whole width, the
  two maps first and their bars under them: the Rebalancer's bullets, the PAC's two bars (no bullet in the PAC). The
  Rebalancer's maps say «target», never the PAC's «ideal».
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
    import type {PlannerExposureRow} from '../types';
    import {BUTTON_LINK, HINT} from '../ui';
    import ExposureBars from './ExposureBars.svelte';
    import ExposureMaps from './ExposureMaps.svelte';
    import {exposureTooltipText} from './exposureTooltip';
    import {exposureGroups, UNCATEGORISED_CATEGORY_ID, type MapWeightRow} from './model';
    import RebalancerExposureBullets from './RebalancerExposureBullets.svelte';
    import {bulletTooltipText, type BulletRow} from './rebalancerExposureTooltip';
    import {getPlannerProfile, testId} from '../profile';
    import {fromPlannerId} from '../source';

    /** Read once, while the component is created: the Tool's profile (F1 of project 67), the PAC's when none is set. */
    const profile = getPlannerProfile();
    const PLANNER_KEY = 'tools.pacAllocator.planner';
    const R = 'tools.portfolioRebalancer.planner.result.exposure';
    const rebalancer = profile.text === 'rebalancer';

    interface Props {
        rows: readonly PlannerExposureRow[];
    }

    let {rows}: Props = $props();

    /** Folded "nothing declared" dimensions the user chose to expand. */
    const expanded = new SvelteSet<string>();
    const labels = new CategoryLabels();

    $effect(() => {
        const language = $currentLanguage;
        untrack(() => labels.load(language));
    });

    /** The Rebalancer's cash row (contract §6.2): `kind: 'cash'`, with no category id and no label. */
    function isCash(row: PlannerExposureRow): boolean {
        return (row as {kind?: string}).kind === 'cash';
    }

    function label(row: PlannerExposureRow): string {
        if (isCash(row)) return $t(`${R}.cash`, {default: 'Cash'});
        // The backend sends a fixed English label for the undeclared share: the interface translates it.
        if (row.category_id === UNCATEGORISED_CATEGORY_ID) return $t(`${PLANNER_KEY}.result.exposures.uncategorised`, {default: 'Uncategorised'});
        // A type, sector or country code reads in the user's language, as on the Asset pages.
        return (EXPOSURE_DIMENSIONS as readonly string[]).includes(row.dimension) ? labels.text($t, row.dimension as ExposureDimension, row.label) : row.label;
    }

    /** Both Tools: types and sectors side by side, then the countries on the whole width (TL-5). */
    const views = $derived(
        exposureGroups(rows)
            .sort((a, b) => Number(a.dimension === 'geography') - Number(b.dimension === 'geography'))
            .map((group) => ({
                ...group,
                folded: group.onlyUncategorised && !expanded.has(group.dimension),
                weights: group.rows.map((row): MapWeightRow => ({id: isCash(row) ? 'cash' : row.category_id, code: isCash(row) ? 'cash' : row.category_id, label: label(row), target: row.target_weight, final: row.final_weight})),
                bullets: rebalancer ? group.rows.map(bulletRow) : [],
            })),
    );
    const words = $derived(exposureTooltipText($t));
    const bulletWords = $derived(bulletTooltipText($t));
    /** The Rebalancer's maps: «Target» and «After the plan», and the direction against the target, never the PAC's «ideal». */
    const mapWords = $derived({
        target: bulletWords.target,
        final: bulletWords.after,
        above: $t(`${R}.mapAbove`, {default: 'Above the target'}),
        below: $t(`${R}.mapBelow`, {default: 'Below the target'}),
        equal: $t(`${R}.mapEqual`, {default: 'In line with the target'}),
    });

    /** A Rebalancer row for its bullet chart: the colour key is the category's own name (a type code, a sector, a country),
     * read back from its planner id (`enc:Real_20Estate` is «Real Estate»), never the label, which the user may have
     * typed; the cash has none. */
    function bulletRow(row: PlannerExposureRow): BulletRow {
        const before: BulletRow['before'] = (row as {before_weight?: BulletRow['before']}).before_weight ?? {kind: 'unavailable', reason: 'not_applicable'};
        if (isCash(row)) return {id: 'cash', key: 'cash', label: label(row), kind: 'cash', before, target: row.target_weight, final: row.final_weight};
        const key = row.category_id === UNCATEGORISED_CATEGORY_ID ? UNCATEGORISED_CATEGORY_ID : fromPlannerId(row.category_id);
        return {id: row.category_id, key, label: label(row), kind: 'category', before, target: row.target_weight, final: row.final_weight};
    }

    function weightText(value: BulletRow['final']): string {
        return value.kind === 'available' ? formatExactPercent(value.value) : `— (${bulletWords.unavailable[value.reason]})`;
    }

    function finalText(row: MapWeightRow): string {
        return row.final.kind === 'available' ? formatExactPercent(row.final.value) : `— (${words.unavailable[row.final.reason]})`;
    }
</script>

<div class="space-y-4" data-testid={testId('exposures', profile)}>
    {#if rebalancer}
        <!-- The legend, once for the three charts: the base of the weights, and the three marks of every row. -->
        <p class="{HINT} flex flex-wrap items-center gap-x-3 gap-y-1" data-testid={testId('exposures-legend', profile)}>
            <span class="font-medium text-lf-secondary">{$t(`${R}.scope`, {default: 'On the whole portfolio, cash included'})}</span>
            <span aria-hidden="true">·</span>
            <span><span aria-hidden="true">▬ </span>{$t(`${R}.legendNow`, {default: 'grey: today'})}</span>
            <span><span aria-hidden="true">▬ </span>{$t(`${R}.legendAfter`, {default: 'coloured: after the plan'})}</span>
            <span><span aria-hidden="true">│ </span>{$t(`${R}.legendTarget`, {default: 'your target'})}</span>
        </p>
    {/if}
    <div class="grid grid-cols-1 gap-x-6 gap-y-5 lg:grid-cols-2">
        {#each views as view (view.dimension)}
            <div class="min-w-0 {view.dimension === 'geography' ? 'lg:col-span-2' : ''}" data-testid={testId('exposures-dimension', profile)} data-dimension={view.dimension} data-folded={view.folded ? 'true' : 'false'}>
                <h4 class="text-sm font-semibold text-lf-primary">{$t(`${PLANNER_KEY}.dimensions.${view.dimension}`, {default: DIMENSION_FALLBACKS[view.dimension]})}</h4>
                {#if view.weights.length === 0}
                    <p class="mt-1 {HINT}">—</p>
                {:else if view.folded}
                    <p class="mt-1 flex flex-wrap items-center gap-2 text-sm text-lf-secondary">
                        {$t(`${PLANNER_KEY}.result.exposures.nothingDeclared`, {default: 'No classification declared · 100% uncategorised'})}
                        <button type="button" class={BUTTON_LINK} data-testid={testId('exposures-show', profile)} onclick={() => expanded.add(view.dimension)}>
                            {$t(`${PLANNER_KEY}.actions.show`, {default: 'Show'})}
                        </button>
                    </p>
                {:else}
                    <div class="mt-2">
                        {#if view.dimension === 'geography'}
                            <ExposureMaps rows={rebalancer ? view.weights.filter((row) => row.id !== 'cash') : view.weights} titles={rebalancer ? mapWords : undefined} />
                        {/if}
                        <div class={view.dimension === 'geography' ? 'mt-4' : ''}>
                            {#if rebalancer}
                                <RebalancerExposureBullets rows={view.bullets} dimension={view.dimension} />
                            {:else}
                                <ExposureBars rows={view.weights} dimension={view.dimension} />
                            {/if}
                        </div>
                    </div>
                    <ul class="sr-only" data-testid={testId('exposures-values', profile)}>
                        {#each view.weights as row, index (row.id)}
                            <li data-testid={testId('exposures-row', profile)} data-id={row.id}>
                                {#if rebalancer}
                                    {row.label}: {bulletWords.now} {weightText(view.bullets[index].before)}, {bulletWords.after} {weightText(row.final)}, {bulletWords.target} {formatExactPercent(row.target)}
                                {:else}
                                    {row.label}: {words.target} {formatExactPercent(row.target)}, {words.final} {finalText(row)}
                                {/if}
                            </li>
                        {/each}
                    </ul>
                {/if}
            </div>
        {/each}
    </div>
    <p class={HINT}>{$t(`${PLANNER_KEY}.result.exposures.uncategorisedHint`, {default: '“Uncategorised” is the share with no declared classification.'})}</p>
</div>
