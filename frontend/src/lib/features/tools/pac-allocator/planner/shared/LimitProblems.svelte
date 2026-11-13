<!--
  The «Check the limits» box under the targets table (F2 of project 67, M1): the limits' own problems, live, the same check
  that stops «Continue» and «Calculate». A minimum above the maximum names both limits, as the mockup does (coordinator's
  answer F2-Q2). The amounts are formatted here, where the line is drawn, through the planner's personal formatter, so privacy
  masks them; a share is a percentage, public. The message is cut at two private-use markers, so each language keeps its
  own word order and each limit gets a `data-side` of its own.
-->
<script lang="ts">
    import {t} from '$lib/i18n';
    import type {PlannerDraft} from '../draft.svelte';
    import {formatPlannerMoneyPlain, formatPlannerPercentUnits} from '../format';
    import {parseLimit} from '../limits';
    import {limitProblems, type LimitProblem} from '../request';
    import {NOTICE} from '../ui';
    import {getPlannerProfile, testId} from '../profile';

    /** Read once, while the component is created: the Tool's profile (F1 of project 67), the PAC's when none is set. */
    const profile = getPlannerProfile();
    const KEY = 'tools.pacAllocator.planner.targets';
    const MINIMUM_MARKER = '';
    const MAXIMUM_MARKER = '';

    interface Props {
        draft: PlannerDraft;
    }

    let {draft}: Props = $props();

    const problems = $derived(limitProblems(draft));

    /** One literal key per limit problem, so the i18n audit can prove each one is used. */
    function problemText(problem: LimitProblem): string {
        const options = {default: problem.fallback, values: problem.values};
        switch (problem.key) {
            case 'limitInvalid':
                return $t('tools.pacAllocator.planner.problems.limitInvalid', options);
            case 'limitShareAboveHundred':
                return $t('tools.pacAllocator.planner.problems.limitShareAboveHundred', options);
            case 'limitShareMinimumsAboveHundred':
                return $t('tools.pacAllocator.planner.problems.limitShareMinimumsAboveHundred', options);
            default:
                return $t('tools.pacAllocator.planner.problems.limitMinAboveMax', options);
        }
    }

    /** A typed limit as the user reads it: an amount in the valuation currency (personal), or a percentage (public). */
    function limitText(text: string | undefined): string {
        const limit = parseLimit(text);
        if (limit === null || limit === 'invalid') return '';
        return limit.kind === 'amount' ? formatPlannerMoneyPlain(limit.value, draft.data.valuationCurrency) : formatPlannerPercentUnits(limit.percent);
    }

    /** «The minimum ({minimum}) is above the maximum ({maximum}).», cut around the two limits, in the language's own order. */
    function conflictParts(problem: LimitProblem): {text: string; side: 'minimum' | 'maximum' | null}[] {
        const message = $t(`${KEY}.limitMinAboveMax`, {default: 'The minimum ({minimum}) is above the maximum ({maximum}).', values: {minimum: MINIMUM_MARKER, maximum: MAXIMUM_MARKER}});
        const limits = problem.assetKey === null ? undefined : draft.data.limits[problem.assetKey];
        return message
            .split(new RegExp(`(${MINIMUM_MARKER}|${MAXIMUM_MARKER})`))
            .filter((part) => part !== '')
            .map((part) => (part === MINIMUM_MARKER ? {text: limitText(limits?.minimum), side: 'minimum'} : part === MAXIMUM_MARKER ? {text: limitText(limits?.maximum), side: 'maximum'} : {text: part, side: null}));
    }
</script>

{#if problems.length > 0}
    <div class="{NOTICE.danger} space-y-1" role="alert" data-testid={testId('targets-limits-problems', profile)}>
        <p class="font-semibold">{$t(`${KEY}.limitsCheck`, {default: 'Check the limits'})}</p>
        {#each problems as problem (`${problem.key}|${problem.assetKey ?? ''}`)}
            <p data-testid={testId('targets-limits-problem', profile)} data-key={problem.key} data-asset-key={problem.assetKey}>
                {problem.entity ? `${problem.entity}: ` : ''}{#if problem.key === 'limitMinAboveMax'}{#each conflictParts(problem) as part, index (index)}{#if part.side}<span class="font-medium tabular-nums" data-side={part.side}>{part.text}</span>{:else}{part.text}{/if}{/each}{:else}{problemText(
                        problem,
                    )}{/if}
            </p>
        {/each}
    </div>
{/if}
