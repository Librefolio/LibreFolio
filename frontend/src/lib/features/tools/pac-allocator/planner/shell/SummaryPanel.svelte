<script lang="ts">
    import {t} from '$lib/i18n';
    import type {PlannerDraft} from '../draft.svelte';
    import {formatPlannerPercentUnits} from '../format';
    import {sectionCounts} from '../review';
    import type {PlannerStep} from '../types';
    import {SECTION_TITLE} from '../ui';
    const PLANNER_KEY = 'tools.pacAllocator.planner';

    interface Props {
        draft: PlannerDraft;
        step: PlannerStep;
        apiVersion: string;
        uiVersion: string;
        testid?: string;
    }

    let {draft, step, apiVersion, uiVersion, testid = 'pac-planner-summary'}: Props = $props();

    const POLICY_FALLBACKS: Record<string, string> = {proportional: 'Proportional'};

    interface Row {
        id: string;
        label: string;
        value: string;
        warn?: boolean;
    }

    const counts = $derived(sectionCounts(draft));

    /** Counts and states only (Q-C0-2): never a sum, a conversion or a future value. */
    const rows = $derived.by((): Row[] => {
        const c = counts;
        switch (step) {
            case 'scenario':
                return [
                    {id: 'currency', label: $t('tools.pacAllocator.planner.summary.currency', {default: 'Currency'}), value: c.scenario.currency || '—'},
                ];
            case 'liquidity':
                return [
                    {id: 'sources', label: $t('tools.pacAllocator.planner.summary.sources', {default: 'Sources'}), value: String(c.liquidity.sources)},
                    {id: 'cash', label: $t('tools.pacAllocator.planner.summary.cash', {default: 'Cash rows'}), value: String(c.liquidity.cash)},
                    {id: 'contributions', label: $t('tools.pacAllocator.planner.summary.contributions', {default: 'Contributions'}), value: String(c.liquidity.contributions)},
                    {id: 'currencies', label: $t('tools.pacAllocator.planner.summary.currencies', {default: 'Currencies'}), value: c.liquidity.currencies.join(', ') || '—'},
                ];
            case 'brokers':
                return [
                    {id: 'operative', label: $t('tools.pacAllocator.planner.summary.brokers', {default: 'Brokers'}), value: String(c.brokers.operative)},
                    {id: 'funding-only', label: $t('tools.pacAllocator.planner.summary.fundingOnly', {default: 'Funding only'}), value: String(c.brokers.fundingOnly)},
                    {id: 'modes', label: $t('tools.pacAllocator.planner.summary.modes', {default: 'Order modes'}), value: String(c.brokers.modes)},
                    {id: 'funding-routes', label: $t('tools.pacAllocator.planner.summary.fundingRoutes', {default: 'Funding routes'}), value: String(c.brokers.fundingRoutes)},
                ];
            case 'assets':
                return [
                    {id: 'assets', label: $t('tools.pacAllocator.planner.summary.assets', {default: 'Assets'}), value: String(c.assets.count)},
                    {id: 'prices', label: $t('tools.pacAllocator.planner.summary.prices', {default: 'Prices'}), value: [c.assets.priced, c.assets.count].join('/'), warn: c.assets.priced < c.assets.count},
                    {id: 'stale', label: $t('tools.pacAllocator.planner.summary.stale', {default: 'Not of the day'}), value: String(c.assets.stale)},
                    {id: 'exposures', label: $t('tools.pacAllocator.planner.summary.exposures', {default: 'Exposures'}), value: [c.assets.withExposures, c.assets.count].join('/')},
                ];
            case 'routing':
                return [
                    {
                        id: 'assets-with-route',
                        label: $t('tools.pacAllocator.planner.summary.assetsWithRoute', {default: 'Assets with a route'}),
                        value: [c.routing.assetsWithRoute, c.assets.count].join('/'),
                        warn: c.routing.assetsWithRoute < c.assets.count,
                    },
                    {id: 'routes', label: $t('tools.pacAllocator.planner.summary.routes', {default: 'BUY routes'}), value: String(c.routing.enabled)},
                ];
            case 'targets':
                return [
                    {id: 'assets', label: $t('tools.pacAllocator.planner.summary.assets', {default: 'Assets'}), value: String(c.assets.count)},
                    {id: 'total', label: $t('tools.pacAllocator.planner.summary.total', {default: 'Total (control)'}), value: draft.targetTotal === null ? '—' : formatPlannerPercentUnits(draft.targetTotal)},
                ];
            case 'fx':
                return [
                    {id: 'pairs', label: $t('tools.pacAllocator.planner.summary.rates', {default: 'Rates'}), value: [c.fx.pairs, c.fx.needed].join('/'), warn: c.fx.pairs < c.fx.needed},
                    {id: 'stale', label: $t('tools.pacAllocator.planner.summary.stale', {default: 'Not of the day'}), value: String(c.fx.stale)},
                    ...(c.fx.conversions > 0
                        ? [{id: 'spread', label: $t('tools.pacAllocator.planner.summary.spread', {default: 'Spread'}), value: c.fx.spreadPercent ? formatPlannerPercentUnits(c.fx.spreadPercent) : '—'}]
                        : []),
                ];
            case 'strategy':
                return [
                    {
                        id: 'policy',
                        label: $t('tools.pacAllocator.planner.summary.strategy', {default: 'Strategy'}),
                        value: c.strategy.policy ? $t(`${PLANNER_KEY}.policies.${c.strategy.policy}`, {default: POLICY_FALLBACKS[c.strategy.policy] ?? c.strategy.policy}) : '—',
                    },
                ];
            case 'review': {
                const facts = draft.factCounts;
                return [
                    {id: 'revision', label: $t('tools.pacAllocator.planner.summary.revision', {default: 'Draft rev.'}), value: String(draft.revision)},
                    {id: 'copied', label: $t('tools.pacAllocator.planner.summary.copied', {default: 'Copied facts'}), value: String(facts.copied)},
                    {id: 'manual', label: $t('tools.pacAllocator.planner.summary.manual', {default: 'Manual'}), value: String(facts.manual)},
                    {id: 'stale', label: $t('tools.pacAllocator.planner.summary.stale', {default: 'Not of the day'}), value: String(facts.stale)},
                    {id: 'modified', label: $t('tools.pacAllocator.planner.summary.modified', {default: 'Modified'}), value: String(facts.modified)},
                ];
            }
            default:
                return [];
        }
    });
</script>

<aside class="space-y-3" aria-labelledby="{testid}-title" data-testid={testid} data-step={step}>
    <h3 id="{testid}-title" class={SECTION_TITLE}>
        {step === 'review' ? $t('tools.pacAllocator.planner.summary.snapshot', {default: 'Snapshot'}) : $t('tools.pacAllocator.planner.summary.title', {default: 'Summary'})}
    </h3>
    <dl class="space-y-1 text-sm">
        {#each rows as row (row.id)}
            <div class="flex justify-between gap-3" data-testid="{testid}-row" data-row={row.id} data-warn={row.warn ? 'true' : 'false'}>
                <dt class="text-gray-600 dark:text-gray-400">{row.label}</dt>
                <dd class="text-right font-medium tabular-nums {row.warn ? 'text-amber-700 dark:text-amber-300' : ''}">{row.value}{row.warn ? ' !' : ''}</dd>
            </div>
        {/each}
    </dl>
    {#if step === 'targets'}
        <p class="text-xs text-gray-500 dark:text-gray-400">{$t('tools.pacAllocator.planner.summary.noFuture', {default: 'No future value calculated.'})}</p>
    {/if}
    {#if step === 'scenario' || step === 'review'}
        <p class="text-xs text-gray-500 dark:text-gray-400" data-testid="{testid}-versions">
            {$t('tools.pacAllocator.planner.summary.versions', {default: 'Backend/API {api} · UI {ui}', values: {api: apiVersion, ui: uiVersion}})}
        </p>
    {/if}
</aside>
