<script lang="ts">
    /**
     * L3° for Asset Global — "what did each of these risk, and what did it pay?"
     *
     * **The scatter is the whole level, and the cards are what is missing.** The
     * portfolio's L3 leads with Sortino, Sharpe and beta as cards, and on that
     * page they are answers about one thing. Repeat them per asset and each cell
     * reads as a grade: "0.4" beside "1.9" is a verdict about two instruments,
     * which is exactly what `03-mappa-livelli-pagine` forbids here — *"a
     * comparison between assets, never a judgement"*. A scatter states two
     * coordinates and lets the reader see the trade-off without ranking anyone.
     *
     * 🔴 **AND THE JUDGEMENT IS NOT SUPPRESSED, IT IS IMPOSSIBLE.** On a
     * risk/return plot the verdict is the Capital Market Line: above it means
     * "paid well for the risk". `capitalMarketLine()` draws only when a point
     * whose role is `portfolio` exists, and that point exists only when the
     * payload carries both a portfolio volatility and a portfolio expected
     * return. `RiskAssetSetReturnOutput` **has no field for either** — not
     * `None`, absent — and the model is `extra="forbid"`, so a fabricated
     * aggregate is not merely rejected, it is unexpressible. Nothing on this
     * surface can turn the line back on, because there is no switch to turn: the
     * defence lives in a shape, in a file that would have to be edited.
     *
     * **No money.** `assetSetLevels` has no currency parameter and returns no
     * amount; a set of assets has no weights and therefore no sum.
     *
     * **The benchmark is the shared one, and there is no picker here.** It comes
     * from `riskBenchmark`, the same module-scope choice Dashboard and Broker
     * Detail read. `03` §3.1 says the benchmark must be identical across pages or
     * the pages stop being comparable, which is the property the whole redesign
     * builds; a second picker on this page would be a second way to disagree.
     */
    import {_ as t} from '$lib/i18n';
    import ScatterChart from '$lib/components/charts/ScatterChart.svelte';
    import {formatPercent} from '$lib/utils/core/formatPercent';
    import type {RiskAnalyticResult} from '$lib/stores/risk/riskStore.svelte';

    import {formatRatio} from './riskAnalysisHelpers';
    import {buildAssetSetBenchmarkPoint, buildAssetSetPaidRows, buildAssetSetScatterPoints} from './assetSetLevels';

    interface Props {
        assetIds: number[];
        assetLabels: ReadonlyMap<number, string>;
        riskReturn: RiskAnalyticResult | null;
        kpi: RiskAnalyticResult | null;
        comparison: RiskAnalyticResult | null;
        /** Set when a benchmark is chosen and it is not itself in the selection. */
        benchmarkApplies: boolean;
        loading?: boolean;
    }

    let {assetIds, assetLabels, riskReturn, kpi, comparison, benchmarkApplies, loading = false}: Props = $props();

    let rows = $derived(buildAssetSetPaidRows(assetIds, assetLabels, riskReturn, kpi, comparison));
    let assetPoints = $derived(buildAssetSetScatterPoints(rows));
    let benchmarkPoint = $derived(buildAssetSetBenchmarkPoint(comparison, assetLabels));

    /**
     * The dots, with the benchmark last so it draws over the cloud.
     *
     * Its role is `benchmark`, never `portfolio`. That is not cosmetic: `role`
     * is what `capitalMarketLine()` searches for, so labelling the reference as
     * a portfolio would anchor a verdict line on an asset that is not the
     * reader's holdings — a judgement drawn from a mislabelled dot.
     */
    let points = $derived(benchmarkPoint === null ? assetPoints : [...assetPoints, {id: 'benchmark', name: benchmarkPoint.name, volatility: benchmarkPoint.volatility, annualReturn: benchmarkPoint.expectedReturn, role: 'benchmark' as const}]);

    // Two dots are the least that can show a relationship; one is a fact without
    // a comparison, and this level exists to compare.
    let hasScatter = $derived(points.length >= 2);
    let hasAnyFigure = $derived(rows.some((row) => row.volatility !== null || row.expectedReturn !== null));

    function percent(value: number): string {
        return formatPercent(value, {scale: 100, signed: false, digits: 1});
    }

    /** A return that may be a loss, so it carries its own sign. */
    function signedPercent(value: number): string {
        return `${value < 0 ? '\u2212' : '+'}${formatPercent(Math.abs(value), {scale: 100, signed: false, digits: 1})}`;
    }
</script>

<div class="space-y-4" data-testid="risk-asset-set-l3" data-benchmark={benchmarkApplies ? 'true' : 'false'}>
    <p class="text-xs text-gray-500 dark:text-gray-400">{$t('risk.assetSet.levels.l3.description')}</p>

    {#if loading && !hasAnyFigure}
        <div class="h-64 animate-pulse rounded-lg bg-gray-100 dark:bg-slate-700" data-testid="risk-asset-set-l3-loading"></div>
    {:else if rows.length === 0}
        <p class="py-4 text-center text-sm text-gray-400 dark:text-gray-500" data-testid="risk-asset-set-l3-empty">{$t('risk.states.empty')}</p>
    {:else}
        {#if hasScatter}
            <div data-testid="risk-asset-set-l3-risk-return">
                <!-- `riskFreeRate` is left at its default and anchors nothing here:
                     with no portfolio point there is no line for it to anchor. The
                     label is still supplied because the component asks for it; it
                     names a line that this payload cannot produce. -->
                <ScatterChart
                    {points}
                    labels={{
                        volatility: $t('risk.levels.l3.scatter.axisVolatility'),
                        return: $t('risk.levels.l3.scatter.axisReturn'),
                        capitalMarketLine: $t('risk.levels.l3.scatter.line'),
                    }}
                    height="360px"
                    testId="risk-asset-set-l3-scatter"
                    emptyLabel={$t('risk.states.unavailable')}
                />
                <!-- The axis label alone cannot carry this. On a very volatile
                     holding the expected return and the one actually lived through
                     differ by tens of percentage points, and a reader seeing "−11%"
                     beside a coin that halved will not guess that "expected" was the
                     warning. -->
                <p class="mt-1 text-xs text-gray-500 dark:text-gray-400" data-testid="risk-asset-set-l3-scatter-note">{$t('risk.levels.l3.scatter.note')}</p>
            </div>
        {/if}

        <div class="w-full overflow-x-auto">
            <table class="w-full text-sm" data-testid="risk-asset-set-l3-table" data-row-count={rows.length}>
                <thead>
                    <tr class="border-b border-gray-100 text-xs text-gray-500 dark:border-slate-700 dark:text-gray-400">
                        <th class="py-2 pr-3 text-left font-medium">{$t('risk.assetSet.levels.asset')}</th>
                        <th class="py-2 pl-3 text-right font-medium whitespace-nowrap">{$t('risk.levels.l3.volatility')}</th>
                        <th class="py-2 pl-3 text-right font-medium whitespace-nowrap">{$t('risk.assetSet.levels.l3.expectedReturn')}</th>
                        <th class="py-2 pl-3 text-right font-medium whitespace-nowrap">{$t('risk.levels.l3.sortino')}</th>
                        <th class="py-2 pl-3 text-right font-medium whitespace-nowrap">{$t('risk.levels.l3.sharpe')}</th>
                        {#if benchmarkApplies}
                            <th class="py-2 pl-3 text-right font-medium whitespace-nowrap">{$t('risk.levels.l3.beta')}</th>
                            <th class="py-2 pl-3 text-right font-medium whitespace-nowrap">{$t('risk.assetSet.levels.l3.correlation')}</th>
                        {/if}
                    </tr>
                </thead>
                <tbody>
                    {#each rows as row (row.assetId)}
                        <tr class="border-b border-gray-50 last:border-0 dark:border-slate-800" data-testid="risk-asset-set-l3-row" data-asset-id={row.assetId}>
                            <td class="py-2 pr-3 text-gray-700 dark:text-gray-200" data-testid="risk-asset-set-l3-name">{row.name}</td>
                            <td class="py-2 pl-3 text-right tabular-nums text-gray-600 dark:text-gray-300" data-testid="risk-asset-set-l3-volatility">{row.volatility === null ? '\u2014' : percent(row.volatility)}</td>
                            <td class="py-2 pl-3 text-right tabular-nums text-gray-600 dark:text-gray-300" data-testid="risk-asset-set-l3-expectedReturn">{row.expectedReturn === null ? '\u2014' : signedPercent(row.expectedReturn)}</td>
                            <!-- Ratios, printed plainly. No colour, no arrow, no
                                 ordering by value: a grade is what this level may not
                                 give, and a green cell is a grade. -->
                            <td class="py-2 pl-3 text-right tabular-nums text-gray-600 dark:text-gray-300" data-testid="risk-asset-set-l3-sortino">{formatRatio(row.sortino)}</td>
                            <td class="py-2 pl-3 text-right tabular-nums text-gray-600 dark:text-gray-300" data-testid="risk-asset-set-l3-sharpe">{formatRatio(row.sharpe)}</td>
                            {#if benchmarkApplies}
                                <td class="py-2 pl-3 text-right tabular-nums text-gray-600 dark:text-gray-300" data-testid="risk-asset-set-l3-beta">{formatRatio(row.beta)}</td>
                                <td class="py-2 pl-3 text-right tabular-nums text-gray-600 dark:text-gray-300" data-testid="risk-asset-set-l3-correlation">{formatRatio(row.correlation)}</td>
                            {/if}
                        </tr>
                    {/each}
                </tbody>
            </table>
        </div>

        {#if !benchmarkApplies}
            <!-- Stated rather than left to be noticed. Two columns are missing and
                 the reason is a choice the reader can make elsewhere; without this
                 the absence reads as a limitation of the page. -->
            <p class="text-[11px] text-gray-400 dark:text-gray-500" data-testid="risk-asset-set-l3-no-benchmark">{$t('risk.assetSet.levels.l3.noBenchmark')}</p>
        {/if}
        <p class="text-[11px] text-gray-400 dark:text-gray-500" data-testid="risk-asset-set-l3-blank-note">{$t('risk.assetSet.levels.blankNote')}</p>
    {/if}
</div>
