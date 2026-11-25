<!--
  The «Check the limits» box under the targets table (F2 of project 67, M1): the limits' own problems, live, the same check
  that stops «Continue» and «Calculate». A minimum above the maximum names both limits, as the mockup does (coordinator's
  answer F2-Q2). The amounts are formatted here, where the line is drawn, through the planner's personal formatter, so privacy
  masks them; a share is a percentage, public. The message is cut at two private-use markers, so each language keeps its
  own word order and each limit gets a `data-side` of its own.
  Below them, the cross checks only the backend can make, as the last preview names them (R1-E of project 67: «Ho messo un
  minimo che era più di tutto il capitale disponibile, mi aspettavo già in 6 un banner»): with «Calculate»'s own sentence.
  These warn and stop nothing; they stay while the preview is being updated, as its figures do, and go with a failed one.
  TL-4 of project 67 («appena il numero inserito fosse troppo alto il banner compariva», «farei comparire anche un toast»):
  an Asset's minimum alone above the Tool's base is said at once, on the last preview's total, until the preview names the
  sum (`minimumsAboveTotal`); the sum of the minimums says its two figures, each Tool with its own name for the base; and a
  problem that appears raises a toast once — not the ones already there when the step opens, not a figure that changes.
-->
<script lang="ts">
    import {untrack} from 'svelte';
    import {t} from '$lib/i18n';
    import {notify} from '$lib/stores/app/notify.svelte';
    import {escapeHtml} from '$lib/utils/core/escapeHtml';
    import type {PlannerDraft} from '../draft.svelte';
    import {formatPlannerMoneyPlain, formatPlannerPercentUnits} from '../format';
    import {parseLimit} from '../limits';
    import {limitProblems, minimumsAboveTotal, previewLimitProblems, type LimitProblem, type PreviewLimitProblem} from '../request';
    import type {PlannerExactMoney} from '../types';
    import {NOTICE} from '../ui';
    import {getPlannerProfile, testId} from '../profile';

    /** Read once, while the component is created: the Tool's profile (F1 of project 67), the PAC's when none is set. */
    const profile = getPlannerProfile();
    const KEY = 'tools.pacAllocator.planner.targets';
    const R = 'tools.portfolioRebalancer.planner';
    const MINIMUM_MARKER = '';
    const MAXIMUM_MARKER = '';

    interface Props {
        draft: PlannerDraft;
        /** The limits' cross checks of the last preview (none without one). */
        previewProblems?: readonly PreviewLimitProblem[];
        /** The Tool's base of the last preview, while a newer one is on its way too; null without one. */
        total?: PlannerExactMoney | null;
    }

    let {draft, previewProblems = [], total = null}: Props = $props();

    const problems = $derived([...limitProblems(draft), ...minimumsAboveTotal(draft, total, previewProblems), ...previewLimitProblems(draft, previewProblems)]);

    /**
     * What a toast is raised for: a problem the user's figure creates. One identity per check and entry, never its figures,
     * so a digit more is not a new problem; the minimum alone above the base and the sum of the minimums are one identity,
     * the same problem said first by the page and then by the preview. A field still being typed («1.») is not one.
     */
    function identity(problem: LimitProblem): string | null {
        if (problem.key === 'limitInvalid') return null;
        if (problem.key === 'limitMinimumAboveTotal' || problem.key === 'bounds_min_sum_exceeds_reference') return 'minimums-above-base';
        return `${problem.key}|${problem.assetKey ?? ''}`;
    }

    /** The identities on screen at the last look: seeded when the step opens, so the problems already there raise nothing. */
    let seen: Set<string> | null = null;
    $effect(() => {
        const current = new Map<string, LimitProblem>();
        for (const problem of problems) {
            const id = identity(problem);
            if (id !== null && !current.has(id)) current.set(id, problem);
        }
        untrack(() => {
            if (seen !== null) {
                for (const [id, problem] of current) {
                    if (seen.has(id)) continue;
                    notify({name: 'planner.limit-problem.appeared', detail: {tool: profile.text, key: problem.key}, toast: {variant: 'warning', message: escapeHtml(toastText(problem))}});
                }
            }
            seen = new Set(current.keys());
        });
    });

    /** The toast says the line of the box, as plain text. */
    function toastText(problem: LimitProblem): string {
        const text =
            problem.key === 'limitMinAboveMax'
                ? conflictParts(problem)
                      .map((part) => part.text)
                      .join('')
                : problemText(problem);
        return problem.entity ? `${problem.entity}: ${text}` : text;
    }

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
            case 'bound_min_above_max':
                return $t('tools.pacAllocator.planner.issues.allocation.bound_min_above_max', options);
            case 'bounds_min_sum_exceeds_reference':
                return profile.text === 'rebalancer' ? $t(`${R}.issues.allocation.bounds_min_sum_exceeds_reference`, options) : $t('tools.pacAllocator.planner.issues.allocation.bounds_min_sum_exceeds_reference', options);
            case 'limitMinimumAboveTotal':
                return profile.text === 'rebalancer' ? $t(`${R}.problems.limitMinimumAboveTotal`, options) : $t('tools.pacAllocator.planner.problems.limitMinimumAboveTotal', options);
            case 'bound_max_below_current':
                return $t('tools.pacAllocator.planner.issues.allocation.bound_max_below_current', options);
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
