<script lang="ts">
    import {_ as t} from '$lib/i18n';
    import RiskCardGrid from '$lib/components/ui/display/RiskCardGrid.svelte';
    import RiskMetricCard from '$lib/components/ui/display/RiskMetricCard.svelte';
    import ScatterChart from '$lib/components/charts/ScatterChart.svelte';
    import {formatPercent} from '$lib/utils/core/formatPercent';
    import type {RiskAnalyticResult} from '$lib/stores/risk/riskStore.svelte';

    import {formatRatio, resultByCode} from '../riskAnalysisHelpers';
    import {buildRiskAdjusted} from './levelHelpers';
    import {buildRiskReturnPoints, cashWeight, selectKpiWave} from './l3Helpers';

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
     *
     * ⚠️ EVERY FIGURE HERE SHARES ONE PERIMETER, AND THE CARD SAYS WHICH.
     * This level reads the *current composition* wave: today's weights replayed
     * over past asset returns. That is a backtest and is labelled as one. The
     * alternative — the portfolio's real history — answers a different question,
     * in the past tense, and for a portfolio that was mostly cash for most of the
     * window it answers it uselessly: its correlation against a stock benchmark
     * collapses towards zero, so the beta computed on it has nothing to estimate.
     * The two perimeters can disagree on Sharpe and Sortino by more than half,
     * which is why they may not be mixed silently, and why the perimeter is read
     * from the payload's `metadata` rather than assumed here.
     */
    interface Props {
        historicalResults: RiskAnalyticResult[];
        /** The whole `current_composition` wave: the KPI and the scatter both live in it. */
        currentResults?: RiskAnalyticResult[];
        comparisonResult: RiskAnalyticResult | null;
        /** Name of the benchmark beta is measured against, when one is chosen. */
        benchmarkName?: string | null;
        /** Display names for the scatter's dots, resolved by the panel. */
        assetNames?: Record<number, string>;
        /** Anchors the Capital Market Line at x = 0. Percent, as the panel holds it. */
        appliedRiskFreePercent?: number;
        loading?: boolean;
    }

    let {historicalResults, currentResults = [], comparisonResult, benchmarkName = null, assetNames = {}, appliedRiskFreePercent = 0, loading = false}: Props = $props();

    let wave = $derived(selectKpiWave(currentResults, historicalResults));
    let figures = $derived(buildRiskAdjusted(wave.results, comparisonResult));
    let perimeterLabel = $derived(wave.perimeter === null ? '' : $t(`risk.levels.l3.perimeter.${wave.perimeter}`));

    let riskReturnResult = $derived(resultByCode(currentResults, 'asset_risk_return'));
    let points = $derived(
        buildRiskReturnPoints({
            riskReturnResult,
            comparisonResult,
            assetNames,
            benchmarkName,
            portfolioLabel: $t('risk.levels.l3.scatter.portfolio'),
        }),
    );
    let cash = $derived(cashWeight(riskReturnResult));

    let hasAny = $derived(figures.sortino !== null || figures.sharpe !== null || figures.volatility !== null || figures.beta !== null);
    // Two dots are the least that can show a relationship; a lone one is a fact
    // without a comparison, and no chart says more than half a chart.
    let hasScatter = $derived(points.length >= 2);

    function ratio(value: number): string {
        return formatRatio(value);
    }

    function percent(value: number): string {
        return formatPercent(value, {scale: 100, signed: false, digits: 1});
    }
</script>

<div class="space-y-4" data-testid="risk-l3" data-perimeter={wave.perimeter ?? ''}>
    {#if loading && !hasAny}
        <div class="grid grid-cols-2 gap-3 sm:grid-cols-4" data-testid="risk-l3-loading">
            {#each [0, 1, 2, 3] as placeholder (placeholder)}
                <div class="h-16 animate-pulse rounded bg-gray-100 dark:bg-slate-700"></div>
            {/each}
        </div>
    {:else if !hasAny}
        <p class="text-sm text-gray-500 dark:text-gray-400" data-testid="risk-l3-empty">{$t('risk.states.unavailable')}</p>
    {:else}
        <RiskCardGrid testId="risk-l3-metrics">
            <!-- Sortino first, and first is the argument. -->
            <RiskMetricCard
                label={$t('risk.levels.l3.sortino')}
                technicalName="Sortino"
                numericValue={figures.sortino ?? undefined}
                formatValue={ratio}
                value={formatRatio(figures.sortino)}
                caption={perimeterLabel}
                docsPath="financial-theory/technical-analysis/risk-metrics/sortino-ratio/"
                {loading}
                testId="risk-l3-sortino"
            />

            <RiskMetricCard
                label={$t('risk.levels.l3.sharpe')}
                technicalName="Sharpe"
                numericValue={figures.sharpe ?? undefined}
                formatValue={ratio}
                value={formatRatio(figures.sharpe)}
                caption={perimeterLabel}
                docsPath="financial-theory/technical-analysis/risk-metrics/sharpe-ratio/"
                {loading}
                testId="risk-l3-sharpe"
            />

            <RiskMetricCard
                label={$t('risk.levels.l3.volatility')}
                technicalName="σ ann."
                numericValue={figures.volatility ?? undefined}
                formatValue={percent}
                value={formatPercent(figures.volatility, {scale: 100, signed: false, digits: 1})}
                caption={perimeterLabel}
                docsPath="financial-theory/technical-analysis/risk-metrics/volatility/"
                {loading}
                testId="risk-l3-volatility"
            />

            <!-- A beta without its benchmark is not a number, it is a rumour — so the
                 caption names the reference as soon as there is one, and falls back to
                 the perimeter when there is not. -->
            <RiskMetricCard
                label={$t('risk.levels.l3.beta')}
                technicalName="β"
                numericValue={figures.beta ?? undefined}
                formatValue={ratio}
                value={formatRatio(figures.beta)}
                caption={figures.beta !== null && benchmarkName ? benchmarkName : perimeterLabel}
                docsPath="financial-theory/technical-analysis/risk-metrics/beta-active-return/"
                {loading}
                testId="risk-l3-beta"
            />
        </RiskCardGrid>

        {#if figures.beta !== null && benchmarkName}
            <!-- The benchmark's name is inside the beta card's caption, which is where a
                 reader looks. This keeps the name addressable on its own for the E2E
                 that asserts it, without printing it twice on screen. -->
            <p class="sr-only" data-testid="risk-l3-beta-benchmark">{benchmarkName}</p>
        {/if}

        {#if hasScatter}
            <div data-testid="risk-l3-risk-return">
                <h4 class="mb-1 text-sm font-medium text-gray-700 dark:text-gray-200">{$t('risk.levels.l3.scatter.title')}</h4>
                <ScatterChart
                    {points}
                    labels={{
                        volatility: $t('risk.levels.l3.scatter.axisVolatility'),
                        return: $t('risk.levels.l3.scatter.axisReturn'),
                        capitalMarketLine: $t('risk.levels.l3.scatter.line'),
                    }}
                    riskFreeRate={appliedRiskFreePercent / 100}
                    testId="risk-l3-scatter"
                    emptyLabel={$t('risk.states.unavailable')}
                />
                <!-- The axis label alone cannot carry this. On a very volatile holding the
                     expected return and the one actually lived through differ by tens of
                     percentage points, and a reader seeing "-11%" beside a coin that
                     halved will not guess that the word "expected" was the warning. -->
                <p class="mt-1 text-xs text-gray-500 dark:text-gray-400" data-testid="risk-l3-scatter-note">
                    {$t('risk.levels.l3.scatter.note')}
                    {#if cash !== null && cash > 0}
                        {$t('risk.levels.l3.scatter.cash', {values: {share: formatPercent(cash, {scale: 100, signed: false, digits: 0})}})}
                    {/if}
                </p>
            </div>
        {/if}
    {/if}
</div>
