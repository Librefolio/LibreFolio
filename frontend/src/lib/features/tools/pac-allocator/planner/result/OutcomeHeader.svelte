<script lang="ts">
    import {ArrowDown} from 'lucide-svelte';
    import {t, locale} from '$lib/i18n';
    import Tooltip from '$lib/components/ui/feedback/Tooltip.svelte';
    import {formatObjectiveValue, formatPlannerDate, type CurrencyDigits} from '../format';
    import {L2_FORMULA_FALLBACK} from '../policies';
    import {tipHtml} from '../shared/tipHtml';
    import type {PacReadyResult} from '../types';
    import {BADGE, BUTTON_LINK, BUTTON_PRIMARY, BUTTON_SECONDARY, CARD, HINT} from '../ui';
    import {objectiveStage, resultBadges, type BadgeTone} from './model';
    import ResultBadgeTip from './ResultBadgeTip.svelte';
    const PLANNER_KEY = 'tools.pacAllocator.planner';

    interface Props {
        result: PacReadyResult;
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
    const badges = $derived(resultBadges(result));
    const stages = $derived('primary_solution' in result ? result.primary_solution.objectives.stages : []);
    const l2 = $derived(objectiveStage(stages, 'fixed_l2'));
    const shortfall = $derived(objectiveStage(stages, 'shortfall'));
    /** A ready result never carries an error: a warning colours the badge, an information only marks it. */
    const notesTone = $derived<BadgeTone>(result.issues.some((issue) => issue.severity === 'warning') ? 'warning' : result.issues.length > 0 ? 'info' : 'neutral');
    const TIP_WIDTH = '320px';
</script>

<section class="{CARD} space-y-3" aria-labelledby="pac-planner-result-title" data-testid="pac-planner-outcome" data-state={result.result_state}>
    <div class="flex flex-wrap items-start justify-between gap-2">
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
        <button type="button" class={BUTTON_LINK} data-testid="pac-planner-goto-proof" onclick={ongotoproof}>
            <span>{$t('tools.pacAllocator.planner.result.gotoProof', {default: 'Proof and timings'})}</span>
            <ArrowDown size={16} aria-hidden="true" />
        </button>
    </div>
    <!-- R11.4: every badge opens its explanation on hover, tap or focus. -->
    <ul class="flex flex-wrap gap-2" data-testid="pac-planner-outcome-badges">
        {#each badges as badge (badge.id)}
            <li data-testid="pac-planner-outcome-badge" data-badge={badge.id} data-tone={badge.tone}>
                <ResultBadgeTip {badge} />
            </li>
        {/each}
    </ul>
    {#if l2 || shortfall}
        <ul class="flex flex-wrap gap-2 tabular-nums" data-testid="pac-planner-outcome-objectives">
            {#if l2}
                <li data-testid="pac-planner-outcome-objective" data-objective="fixed_l2">
                    <Tooltip html={tipHtml($t(`${PLANNER_KEY}.strategy.l2Formula`, {default: L2_FORMULA_FALLBACK}))} math maxWidth={TIP_WIDTH}>
                        <span class={BADGE.neutral}>{$t(`${KEY}.l2`, {default: 'L2 distance {value}', values: {value: formatObjectiveValue(l2.value, l2.unit, digits)}})}</span>
                    </Tooltip>
                </li>
            {/if}
            {#if shortfall}
                <li data-testid="pac-planner-outcome-objective" data-objective="shortfall">
                    <Tooltip
                        text={$t(`${PLANNER_KEY}.result.kpi.help.shortfall`, {default: 'The part of the base that does not end up in the Assets: cash left free, costs and rounding.'})}
                        maxWidth={TIP_WIDTH}
                    >
                        <span class={BADGE.neutral}>{$t(`${KEY}.shortfall`, {default: 'Not invested {value}', values: {value: formatObjectiveValue(shortfall.value, shortfall.unit, digits)}})}</span>
                    </Tooltip>
                </li>
            {/if}
            <li data-testid="pac-planner-outcome-notes" data-tone={notesTone}>
                <Tooltip
                    text={$t(`${KEY}.notesHelp`, {default: 'The messages the calculation left about this plan, warnings or information. When there are any, they are listed just below.'})}
                    maxWidth={TIP_WIDTH}
                >
                    <span class={BADGE[notesTone]}>{$t(`${KEY}.notes`, {default: '{count, plural, =0 {no notes} one {# note} other {# notes}}', values: {count: result.issues.length}})}</span>
                </Tooltip>
            </li>
        </ul>
    {/if}
    <div class="flex flex-wrap items-center justify-between gap-2">
        <button type="button" class={BUTTON_SECONDARY} data-testid="pac-planner-edit" {disabled} onclick={onedit}>{$t(`${PLANNER_KEY}.actions.editConfiguration`, {default: 'Edit configuration'})}</button>
        <button type="button" class={BUTTON_PRIMARY} data-testid="pac-planner-recalculate" {disabled} onclick={oncalculate}>{$t(`${KEY}.calculateNew`, {default: 'Calculate new plan'})}</button>
    </div>
</section>
