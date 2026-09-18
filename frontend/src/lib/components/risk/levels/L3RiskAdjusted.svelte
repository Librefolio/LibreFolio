<script lang="ts">
    import {_ as t} from '$lib/i18n';
    import DocsLink from '$lib/components/ui/DocsLink.svelte';
    import type {RiskAnalyticResult} from '$lib/stores/risk/riskStore.svelte';

    import {formatRatio} from '../riskAnalysisHelpers';
    import {buildRiskAdjusted} from './levelHelpers';

    /**
     * L3 — "am I being paid for this risk?"
     *
     * The only one of the four that looks outward. Sharpe, Sortino and beta used
     * to appear as orphan cards; they were never bad metrics, they were metrics
     * without a home, and the question is the home.
     *
     * Sortino leads and Sharpe follows. Sharpe divides by *total* volatility, so
     * it punishes violent rises exactly as it punishes falls — it would rate a
     * flat portfolio above a lumpy but rewarding one. Sharpe is still shown,
     * quietly, because it is the number most readers have met elsewhere and
     * hiding it would read as evasion. Neither is presented as a grade.
     */
    interface Props {
        historicalResults: RiskAnalyticResult[];
        comparisonResult: RiskAnalyticResult | null;
        /** Name of the benchmark beta is measured against, when one is chosen. */
        benchmarkName?: string | null;
        loading?: boolean;
    }

    let {historicalResults, comparisonResult, benchmarkName = null, loading = false}: Props = $props();

    let figures = $derived(buildRiskAdjusted(historicalResults, comparisonResult));
    let hasAny = $derived(figures.sortino !== null || figures.sharpe !== null || figures.volatility !== null || figures.beta !== null);
</script>

<div data-testid="risk-l3">
    {#if loading && !hasAny}
        <div class="grid grid-cols-2 gap-3 sm:grid-cols-4" data-testid="risk-l3-loading">
            {#each [0, 1, 2, 3] as placeholder (placeholder)}
                <div class="h-16 animate-pulse rounded bg-gray-100 dark:bg-slate-700"></div>
            {/each}
        </div>
    {:else if !hasAny}
        <p class="text-sm text-gray-500 dark:text-gray-400" data-testid="risk-l3-empty">{$t('risk.states.unavailable')}</p>
    {:else}
        <div class="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <!-- Sortino first, and visually heavier: the order is the argument. -->
            <div class="rounded-lg bg-gray-50 p-3 dark:bg-slate-900/40" data-testid="risk-l3-sortino">
                <div class="flex items-center gap-1">
                    <span class="text-xs text-gray-500 dark:text-gray-400">{$t('risk.levels.l3.sortino')}</span>
                    <DocsLink path="user/analysis/risk.md#sortino" label={$t('risk.levels.l3.sortinoHelp')} testId="risk-l3-doc-sortino" />
                </div>
                <div class="mt-1 text-xl font-semibold tabular-nums text-gray-800 dark:text-gray-100" data-testid="risk-l3-sortino-value">{formatRatio(figures.sortino)}</div>
            </div>

            <div class="rounded-lg bg-gray-50 p-3 dark:bg-slate-900/40" data-testid="risk-l3-sharpe">
                <div class="flex items-center gap-1">
                    <span class="text-xs text-gray-500 dark:text-gray-400">{$t('risk.levels.l3.sharpe')}</span>
                    <DocsLink path="user/analysis/risk.md#sharpe" label={$t('risk.levels.l3.sharpeHelp')} testId="risk-l3-doc-sharpe" />
                </div>
                <div class="mt-1 text-base tabular-nums text-gray-600 dark:text-gray-300" data-testid="risk-l3-sharpe-value">{formatRatio(figures.sharpe)}</div>
            </div>

            <div class="rounded-lg bg-gray-50 p-3 dark:bg-slate-900/40" data-testid="risk-l3-volatility">
                <span class="text-xs text-gray-500 dark:text-gray-400">{$t('risk.levels.l3.volatility')}</span>
                <div class="mt-1 text-base tabular-nums text-gray-600 dark:text-gray-300" data-testid="risk-l3-volatility-value">
                    {figures.volatility == null ? '—' : `${(figures.volatility * 100).toFixed(1)}%`}
                </div>
            </div>

            <div class="rounded-lg bg-gray-50 p-3 dark:bg-slate-900/40" data-testid="risk-l3-beta">
                <div class="flex items-center gap-1">
                    <span class="text-xs text-gray-500 dark:text-gray-400">{$t('risk.levels.l3.beta')}</span>
                    <DocsLink path="user/analysis/risk.md#beta" label={$t('risk.levels.l3.betaHelp')} testId="risk-l3-doc-beta" />
                </div>
                <div class="mt-1 text-base tabular-nums text-gray-600 dark:text-gray-300" data-testid="risk-l3-beta-value">{formatRatio(figures.beta)}</div>
                {#if figures.beta !== null && benchmarkName}
                    <!-- A beta without its benchmark is not a number, it is a rumour. -->
                    <div class="mt-0.5 truncate text-[10px] text-gray-400 dark:text-gray-500" data-testid="risk-l3-beta-benchmark">{benchmarkName}</div>
                {/if}
            </div>
        </div>
    {/if}
</div>
