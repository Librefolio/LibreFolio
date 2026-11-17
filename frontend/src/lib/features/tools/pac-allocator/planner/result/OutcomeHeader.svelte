<script lang="ts">
    import {ArrowDown} from 'lucide-svelte';
    import {t} from '$lib/i18n';
    import Tooltip from '$lib/components/ui/feedback/Tooltip.svelte';
    import {exactDisplay, formatExactMoneyPlain, formatObjectiveValue, formatPlannerDate, formatPlannerPlainDecimal, type CurrencyDigits} from '../format';
    import {L2_FORMULA_FALLBACK} from '../policies';
    import {tipHtml} from '../shared/tipHtml';
    import type {PlannerReadyResult, RebalancerSolution} from '../types';
    import {BADGE, BUTTON_LINK, BUTTON_PRIMARY, BUTTON_SECONDARY, CARD, HINT} from '../ui';
    import {objectiveStage, resultBadges, type BadgeTone} from './model';
    import ResultBadgeTip from './ResultBadgeTip.svelte';
    import {getPlannerProfile, domId, testId} from '../profile';

    /** Read once, while the component is created: the Tool's profile (F1 of project 67), the PAC's when none is set. */
    const profile = getPlannerProfile();
    const PLANNER_KEY = 'tools.pacAllocator.planner';

    interface Props {
        result: PlannerReadyResult;
        revision: number;
        apiVersion: string;
        digits: CurrencyDigits;
        disabled: boolean;
        onedit: () => void;
        oncalculate: () => void;
        /** R10.7: opens «Proof and solver», with the backend timings, and scrolls to it. */
        ongotoproof: () => void;
    }

    let {result, revision, apiVersion, digits, disabled, onedit, oncalculate, ongotoproof}: Props = $props();

    const KEY = 'tools.pacAllocator.planner.result.header';
    const basis = $derived(result.scenario_basis);
    const badges = $derived(resultBadges(result, profile.text, digits));
    const stages = $derived('primary_solution' in result ? result.primary_solution.objectives.stages : []);
    const l2 = $derived(objectiveStage(stages, 'fixed_l2'));
    const shortfall = $derived(objectiveStage(stages, 'shortfall'));
    /** A ready result never carries an error: a warning colours the badge, an information only marks it. */
    const notesTone = $derived<BadgeTone>(result.issues.some((issue) => issue.severity === 'warning') ? 'warning' : result.issues.length > 0 ? 'info' : 'neutral');
    const TIP_WIDTH = '320px';
    /** The Rebalancer's score (F4a of project 67, step 4; contract §6.6): `J` and its parts, or under «Target first» the
     * distance and the money lost, all published in `score`. Absent for the PAC. */
    const R = 'tools.portfolioRebalancer.planner.result.header';
    const score = $derived(profile.text === 'rebalancer' && 'primary_solution' in result ? (result.primary_solution as unknown as RebalancerSolution).score : null);
    const scoreMoney = (value: Parameters<typeof formatExactMoneyPlain>[0]) => formatExactMoneyPlain(value, {digits});
</script>

<section class="{CARD} space-y-3" aria-labelledby={domId('result-title', profile)} data-testid={testId('outcome', profile)} data-state={result.result_state}>
    <div class="flex flex-wrap items-start justify-between gap-2">
        <div>
            <h2 id={domId('result-title', profile)} tabindex="-1" class="text-lg font-semibold text-lf-primary focus:outline-none">
                {$t(`${KEY}.title`, {default: 'Calculated plan'})}
            </h2>
            <p class={HINT} data-testid={testId('outcome-basis', profile)}>
                {$t(`${KEY}.basis`, {
                    default: 'Scenario {date} · Currency {currency} · draft rev. {revision} · Backend/API {version}',
                    values: {date: formatPlannerDate(basis.as_of), currency: basis.valuation_currency, revision, version: apiVersion},
                })}
            </p>
        </div>
        <button type="button" class={BUTTON_LINK} data-testid={testId('goto-proof', profile)} onclick={ongotoproof}>
            <span>{$t('tools.pacAllocator.planner.result.gotoProof', {default: 'Proof and timings'})}</span>
            <ArrowDown size={16} aria-hidden="true" />
        </button>
    </div>
    <!-- R11.4: every badge opens its explanation on hover, tap or focus. -->
    <ul class="flex flex-wrap gap-2" data-testid={testId('outcome-badges', profile)}>
        {#each badges as badge (badge.id)}
            <li data-testid={testId('outcome-badge', profile)} data-badge={badge.id} data-tone={badge.tone}>
                <ResultBadgeTip {badge} />
            </li>
        {/each}
    </ul>
    {#if score}
        <ul class="flex flex-wrap gap-2 tabular-nums" data-testid={testId('outcome-objectives', profile)}>
            {#if score.plan_score && score.distance_weight}
                <li data-testid={testId('outcome-objective', profile)} data-objective="plan_score">
                    <Tooltip text={$t(`${R}.scoreHelp`, {values: {lambda: formatPlannerPlainDecimal(exactDisplay(score.distance_weight).text), distance: scoreMoney(score.distance_per_wealth), lost: scoreMoney(score.wealth_loss)}})} maxWidth={TIP_WIDTH}>
                        <span class={BADGE.neutral}>{$t(`${R}.score`, {values: {value: scoreMoney(score.plan_score)}})}</span>
                    </Tooltip>
                </li>
            {:else}
                <li data-testid={testId('outcome-objective', profile)} data-objective="target_distance">
                    <Tooltip text={$t(`${R}.distanceHelp`)} maxWidth={TIP_WIDTH}>
                        <span class={BADGE.neutral}>{$t(`${R}.distance`, {values: {value: scoreMoney(score.distance_per_wealth)}})}</span>
                    </Tooltip>
                </li>
                <li data-testid={testId('outcome-objective', profile)} data-objective="wealth_loss">
                    <Tooltip text={$t('tools.portfolioRebalancer.planner.result.kpi.moneyLostHelp')} maxWidth={TIP_WIDTH}>
                        <span class={BADGE.neutral}>{$t(`${R}.moneyLost`, {values: {value: scoreMoney(score.wealth_loss)}})}</span>
                    </Tooltip>
                </li>
            {/if}
            <li data-testid={testId('outcome-notes', profile)} data-tone={notesTone}>
                <Tooltip text={$t(`${KEY}.notesHelp`, {default: 'The messages the calculation left about this plan, warnings or information. When there are any, they are listed just below.'})} maxWidth={TIP_WIDTH}>
                    <span class={BADGE[notesTone]}>{$t(`${KEY}.notes`, {default: '{count, plural, =0 {no notes} one {# note} other {# notes}}', values: {count: result.issues.length}})}</span>
                </Tooltip>
            </li>
        </ul>
    {:else if l2 || shortfall}
        <ul class="flex flex-wrap gap-2 tabular-nums" data-testid={testId('outcome-objectives', profile)}>
            {#if l2}
                <li data-testid={testId('outcome-objective', profile)} data-objective="fixed_l2">
                    <Tooltip html={tipHtml($t(`${PLANNER_KEY}.strategy.l2Formula`, {default: L2_FORMULA_FALLBACK}))} math maxWidth={TIP_WIDTH}>
                        <span class={BADGE.neutral}>{$t(`${KEY}.l2`, {default: 'L2 distance {value}', values: {value: formatObjectiveValue(l2.value, l2.unit, digits)}})}</span>
                    </Tooltip>
                </li>
            {/if}
            {#if shortfall}
                <li data-testid={testId('outcome-objective', profile)} data-objective="shortfall">
                    <Tooltip text={$t(`${PLANNER_KEY}.result.kpi.help.shortfall`, {default: 'The part of the base that does not end up in the Assets: cash left free, costs and rounding.'})} maxWidth={TIP_WIDTH}>
                        <span class={BADGE.neutral}>{$t(`${KEY}.shortfall`, {default: 'Not invested {value}', values: {value: formatObjectiveValue(shortfall.value, shortfall.unit, digits)}})}</span>
                    </Tooltip>
                </li>
            {/if}
            <li data-testid={testId('outcome-notes', profile)} data-tone={notesTone}>
                <Tooltip text={$t(`${KEY}.notesHelp`, {default: 'The messages the calculation left about this plan, warnings or information. When there are any, they are listed just below.'})} maxWidth={TIP_WIDTH}>
                    <span class={BADGE[notesTone]}>{$t(`${KEY}.notes`, {default: '{count, plural, =0 {no notes} one {# note} other {# notes}}', values: {count: result.issues.length}})}</span>
                </Tooltip>
            </li>
        </ul>
    {/if}
    <div class="flex flex-wrap items-center justify-between gap-2">
        <button type="button" class={BUTTON_SECONDARY} data-testid={testId('edit', profile)} {disabled} onclick={onedit}>{$t(`${PLANNER_KEY}.actions.editConfiguration`, {default: 'Edit configuration'})}</button>
        <button type="button" class={BUTTON_PRIMARY} data-testid={testId('recalculate', profile)} {disabled} onclick={oncalculate}>{$t(`${KEY}.calculateNew`, {default: 'Calculate new plan'})}</button>
    </div>
</section>
