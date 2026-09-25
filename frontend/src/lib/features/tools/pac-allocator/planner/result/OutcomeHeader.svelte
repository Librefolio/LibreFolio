<script lang="ts">
    import {t, locale} from '$lib/i18n';
    import {formatObjectiveValue, formatPlannerDate, type CurrencyDigits} from '../format';
    import type {PacReadyResult} from '../types';
    import {BADGE, BUTTON_PRIMARY, BUTTON_SECONDARY, CARD, HINT} from '../ui';
    import {objectiveStage, resultBadges} from './model';
    const PLANNER_KEY = 'tools.pacAllocator.planner';

    interface Props {
        result: PacReadyResult;
        revision: number;
        apiVersion: string;
        digits: CurrencyDigits;
        disabled: boolean;
        onedit: () => void;
        oncalculate: () => void;
    }

    let {result, revision, apiVersion, digits, disabled, onedit, oncalculate}: Props = $props();

    const KEY = 'tools.pacAllocator.planner.result.header';
    const basis = $derived(result.scenario_basis);
    const badges = $derived(resultBadges(result));
    const stages = $derived('primary_solution' in result ? result.primary_solution.objectives.stages : []);
    const l2 = $derived(objectiveStage(stages, 'fixed_l2'));
    const shortfall = $derived(objectiveStage(stages, 'shortfall'));
</script>

<section class="{CARD} space-y-3" aria-labelledby="pac-planner-result-title" data-testid="pac-planner-outcome" data-state={result.result_state}>
    <div>
        <h2 id="pac-planner-result-title" tabindex="-1" class="text-lg font-semibold text-gray-900 focus:outline-none dark:text-gray-100">
            {$t(`${KEY}.title`, {default: 'Calculated plan'})}
        </h2>
        <p class={HINT} data-testid="pac-planner-outcome-basis">
            {$t(`${KEY}.basis`, {
                default: 'Scenario {date} · Currency {currency} · draft rev. {revision} · Backend/API {version}',
                values: {date: formatPlannerDate(basis.as_of, $locale), currency: basis.valuation_currency, revision, version: apiVersion},
            })}
        </p>
    </div>
    <ul class="flex flex-wrap gap-2" data-testid="pac-planner-outcome-badges">
        {#each badges as badge (badge.id)}
            <li class={BADGE[badge.tone]} data-testid="pac-planner-outcome-badge" data-badge={badge.id} data-tone={badge.tone}>{$t(badge.key, {default: badge.fallback})}</li>
        {/each}
    </ul>
    {#if l2 || shortfall}
        <p class="text-sm tabular-nums" data-testid="pac-planner-outcome-objectives">
            {[
                ...(l2 ? [$t(`${KEY}.l2`, {default: 'L2 distance {value}', values: {value: formatObjectiveValue(l2.value, l2.unit, digits)}})] : []),
                ...(shortfall ? [$t(`${KEY}.shortfall`, {default: 'Not invested {value}', values: {value: formatObjectiveValue(shortfall.value, shortfall.unit, digits)}})] : []),
                $t(`${KEY}.notes`, {default: '{count, plural, =0 {no notes} one {# note} other {# notes}}', values: {count: result.issues.length}}),
            ].join(' · ')}
        </p>
    {/if}
    <div class="flex flex-wrap items-center justify-between gap-2">
        <button type="button" class={BUTTON_SECONDARY} data-testid="pac-planner-edit" {disabled} onclick={onedit}>{$t(`${PLANNER_KEY}.actions.editConfiguration`, {default: 'Edit configuration'})}</button>
        <button type="button" class={BUTTON_PRIMARY} data-testid="pac-planner-recalculate" {disabled} onclick={oncalculate}>{$t(`${KEY}.calculateNew`, {default: 'Calculate new plan'})}</button>
    </div>
</section>
