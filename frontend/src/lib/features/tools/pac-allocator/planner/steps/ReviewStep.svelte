<script lang="ts">
    import {CircleAlert, CircleCheck, Info} from 'lucide-svelte';
    import {t, locale} from '$lib/i18n';
    import type {PlannerDraft} from '../draft.svelte';
    import {formatPlannerDate, formatPlannerFxRate, formatPlannerMoneyPlain, formatPlannerPlainDecimal, formatPlannerPricePlain} from '../format';
    import {STEP_FALLBACKS, stepKey, type ListedIssue} from '../labels';
    import {sectionCounts, snapshotFacts, type SnapshotFact} from '../review';
    import type {PlannerStep} from '../types';
    import {BUTTON_LINK, BUTTON_PRIMARY, BUTTON_SECONDARY, HINT, NOTICE, TABLE, TD, TD_NUM, TH} from '../ui';
    import IssueList from '../shared/IssueList.svelte';
    import OriginBadge from '../shared/OriginBadge.svelte';
    import AgeLabel from '../shared/AgeLabel.svelte';
    const PLANNER_KEY = 'tools.pacAllocator.planner';

    interface Props {
        draft: PlannerDraft;
        problems: readonly ListedIssue[];
        busy: boolean;
        hasResult: boolean;
        ongoto: (step: PlannerStep) => void;
        oncalculate: () => void;
        onshowresult: () => void;
    }

    let {draft, problems, busy, hasResult, ongoto, oncalculate, onshowresult}: Props = $props();

    const POLICY_FALLBACKS: Record<string, string> = {proportional: 'Proportional'};
    const SECTIONS: PlannerStep[] = ['scenario', 'liquidity', 'brokers', 'assets', 'routing', 'targets', 'fx', 'strategy'];

    let factsView = $state<'none' | 'all' | 'changed'>('none');

    const counts = $derived(sectionCounts(draft));
    const facts = $derived(snapshotFacts(draft));
    const shownFacts = $derived(factsView === 'all' ? facts : factsView === 'changed' ? facts.filter((fact) => fact.modified || fact.stale) : []);
    const blocked = $derived(new Set(problems.map((problem) => problem.step)));

    function summary(step: PlannerStep): string {
        switch (step) {
            case 'scenario':
                return [formatPlannerDate(counts.scenario.asOf, $locale), counts.scenario.currency].filter((part) => part !== '').join(' · ');
            case 'liquidity':
                return [$t('tools.pacAllocator.planner.review.sources', {default: '{count, plural, one {# source} other {# sources}}', values: {count: counts.liquidity.sources}}), counts.liquidity.currencies.join(', ')].filter((part) => part !== '').join(' · ');
            case 'brokers':
                return $t('tools.pacAllocator.planner.review.brokers', {
                    default: '{operative} operative · {fundingOnly} funding only',
                    values: {operative: counts.brokers.operative, fundingOnly: counts.brokers.fundingOnly},
                });
            case 'assets':
                return $t('tools.pacAllocator.planner.review.assets', {
                    default: '{count} · prices {priced}/{count} · {stale} not of the day',
                    values: {count: counts.assets.count, priced: counts.assets.priced, stale: counts.assets.stale},
                });
            case 'routing':
                return $t('tools.pacAllocator.planner.review.routes', {default: '{count, plural, one {# BUY route} other {# BUY routes}}', values: {count: counts.routing.enabled}});
            case 'targets':
                return $t('tools.pacAllocator.planner.review.targets', {default: '{count, plural, one {# Asset} other {# Assets}}', values: {count: counts.targets.count}});
            case 'fx':
                return counts.fx.pairs === 0
                    ? $t('tools.pacAllocator.planner.review.noFx', {default: 'no conversion rate'})
                    : $t('tools.pacAllocator.planner.review.fx', {default: '{count, plural, one {# pair} other {# pairs}} · {stale} not of the day', values: {count: counts.fx.pairs, stale: counts.fx.stale}});
            case 'strategy':
                return counts.strategy.policy ? $t(`${PLANNER_KEY}.policies.${counts.strategy.policy}`, {default: POLICY_FALLBACKS[counts.strategy.policy] ?? counts.strategy.policy}) : '—';
            default:
                return '';
        }
    }

    function factValue(fact: SnapshotFact): string {
        const value = fact.value;
        switch (value.kind) {
            case 'money': {
                const available = formatPlannerMoneyPlain(value.amount, value.currency);
                if (value.selected === null) return available;
                return $t('tools.pacAllocator.planner.review.selectedOf', {default: '{selected} of {available}', values: {selected: formatPlannerMoneyPlain(value.selected, value.currency), available}});
            }
            case 'price':
                return $t('tools.pacAllocator.planner.review.price', {
                    default: '{price} / {units} {count, plural, one {unit} other {units}}',
                    values: {price: formatPlannerPricePlain(value.amount, value.currency), units: formatPlannerPlainDecimal(value.units), count: Number(value.units) || 0},
                });
            case 'rate':
                return formatPlannerFxRate(value.rate);
            case 'rows':
                return $t('tools.pacAllocator.planner.review.exposureRows', {default: '{count, plural, one {# exposure} other {# exposures}}', values: {count: value.count}});
            default:
                return '';
        }
    }
</script>

<div class="space-y-4" data-testid="pac-planner-review">
    <p class="text-sm text-gray-700 dark:text-gray-300">{$t('tools.pacAllocator.planner.review.intro', {default: 'The backend will receive this complete copy, and only this.'})}</p>

    <ul class="divide-y divide-gray-100 rounded-xl border border-gray-200 dark:divide-gray-800 dark:border-gray-700" data-testid="pac-planner-review-sections">
        {#each SECTIONS as step (step)}
            <li class="flex flex-wrap items-center gap-3 px-4 py-2 text-sm" data-testid="pac-planner-review-section" data-step={step} data-blocked={blocked.has(step) ? 'true' : 'false'}>
                {#if blocked.has(step)}
                    <CircleAlert class="h-4 w-4 text-amber-600 dark:text-amber-400" aria-hidden="true" />
                {:else}
                    <CircleCheck class="h-4 w-4 text-emerald-600 dark:text-emerald-400" aria-hidden="true" />
                {/if}
                <span class="w-28 font-medium">{$t(stepKey(step), {default: STEP_FALLBACKS[step]})}</span>
                <span class="flex-1 text-gray-700 dark:text-gray-300">{summary(step)}</span>
                <button type="button" class={BUTTON_LINK} data-testid="pac-planner-review-goto" onclick={() => ongoto(step)}>{$t('tools.pacAllocator.planner.review.edit', {default: 'Edit'})}</button>
            </li>
        {/each}
    </ul>

    <div class="flex flex-wrap gap-2" role="group" aria-label={$t('tools.pacAllocator.planner.review.factsLabel', {default: 'Facts of the snapshot'})}>
        <button type="button" class={BUTTON_SECONDARY} aria-pressed={factsView === 'all'} data-testid="pac-planner-review-facts-all" onclick={() => (factsView = factsView === 'all' ? 'none' : 'all')}>
            {$t('tools.pacAllocator.planner.review.factsAll', {default: 'Full snapshot'})}
        </button>
        <button type="button" class={BUTTON_SECONDARY} aria-pressed={factsView === 'changed'} data-testid="pac-planner-review-facts-changed" onclick={() => (factsView = factsView === 'changed' ? 'none' : 'changed')}>
            {$t('tools.pacAllocator.planner.review.factsChanged', {default: 'Only modified / not of the day'})}
        </button>
    </div>

    {#if factsView !== 'none'}
        {#if shownFacts.length === 0}
            <p class={HINT} data-testid="pac-planner-review-facts-empty">{$t('tools.pacAllocator.planner.review.factsEmpty', {default: 'No fact in this view.'})}</p>
        {:else}
            <div class="overflow-x-auto">
                <table class={TABLE} data-testid="pac-planner-review-facts" data-view={factsView}>
                    <thead>
                        <tr>
                            <th scope="col" class={TH}>{$t('tools.pacAllocator.planner.review.factStep', {default: 'Step'})}</th>
                            <th scope="col" class={TH}>{$t('tools.pacAllocator.planner.review.factEntity', {default: 'Fact'})}</th>
                            <th scope="col" class="{TH} text-right">{$t('tools.pacAllocator.planner.review.factValue', {default: 'Value'})}</th>
                            <th scope="col" class={TH}>{$t('tools.pacAllocator.planner.review.factOrigin', {default: 'Origin'})}</th>
                        </tr>
                    </thead>
                    <tbody class="divide-y divide-gray-100 dark:divide-gray-800">
                        {#each shownFacts as fact (fact.id)}
                            <tr data-testid="pac-planner-review-fact" data-kind={fact.kind} data-modified={fact.modified ? 'true' : 'false'} data-stale={fact.stale ? 'true' : 'false'}>
                                <td class={TD}>{$t(stepKey(fact.step), {default: STEP_FALLBACKS[fact.step]})}</td>
                                <td class={TD}>{fact.entity}</td>
                                <td class={TD_NUM}>{factValue(fact)}</td>
                                <td class={TD}>
                                    <span class="flex flex-wrap items-center gap-2">
                                        <OriginBadge origin={fact.origin} modified={fact.modified} />
                                        {#if fact.referenceDate}<AgeLabel date={fact.referenceDate} asOf={draft.data.asOf} />{/if}
                                    </span>
                                </td>
                            </tr>
                        {/each}
                    </tbody>
                </table>
            </div>
        {/if}
    {/if}

    {#if problems.length > 0}
        <div class={NOTICE.warning} role="alert" data-testid="pac-planner-review-problems">
            <p class="mb-2 font-medium">{$t('tools.pacAllocator.planner.review.problems', {default: 'Complete these fields before calculating:'})}</p>
            <IssueList items={problems} {ongoto} testid="pac-planner-review-problem" />
        </div>
    {/if}

    <p class="flex items-start gap-2 {NOTICE.info}"><Info class="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />{$t('tools.pacAllocator.planner.review.noOrders', {default: 'No order will be sent to the Broker. The calculation uses only this payload.'})}</p>

    <div class="flex flex-wrap justify-center gap-3">
        {#if hasResult}
            <button type="button" class={BUTTON_SECONDARY} data-testid="pac-planner-show-result" onclick={onshowresult}>{$t('tools.pacAllocator.planner.review.showResult', {default: 'See the last result'})}</button>
        {/if}
        <button type="button" class={BUTTON_PRIMARY} disabled={busy || problems.length > 0} data-testid="pac-planner-calculate" onclick={oncalculate}>
            {$t('tools.pacAllocator.planner.review.calculate', {default: 'Calculate plan'})}
        </button>
    </div>
</div>
