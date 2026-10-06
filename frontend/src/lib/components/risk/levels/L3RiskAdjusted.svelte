<script lang="ts">
    import {_ as t} from '$lib/i18n';
    import type DataTable from '$lib/components/table/DataTable.svelte';
    import type {RiskAnalyticResult} from '$lib/stores/risk/riskStore.svelte';

    import {resultByCode} from '../riskAnalysisHelpers';
    import RiskReturnLevel from '../RiskReturnLevel.svelte';
    import type {RiskReturnRow} from '../riskReturnLevel';
    import {buildRiskAdjusted, uncoveredWeight} from './levelHelpers';
    import {buildRiskReturnPoints, buildRiskReturnRows, selectKpiWave} from './l3Helpers';

    /**
     * L3 — "am I being paid for this risk?"
     *
     * The only one of the four that looks outward. Sharpe, Sortino and beta used to appear as
     * orphan cards; they were never bad metrics, they were metrics without a home, and the
     * question is the home.
     *
     * **One table, the portfolio first** (developer's review of 06/10/2026: «leviamo le 4 card
     * perchè si assorbono nella tabella»). The four cards became the portfolio's row: the
     * portfolio opens the table, the benchmark follows, each tinted like its dot, then every
     * holding — the same table, chart and notes as Asset Global's L3° (`RiskReturnLevel`).
     * Sortino comes before Sharpe in it, as it did on the cards: Sharpe divides by *total*
     * volatility, so it punishes violent rises exactly as it punishes falls. Sharpe stays,
     * because it is the number most readers have met elsewhere. Neither is a grade.
     *
     * ⚠️ EVERY FIGURE HERE SHARES ONE PERIMETER, AND THE TITLE SAYS WHICH.
     * This level reads the *current composition* wave: today's weights replayed over past asset
     * returns. That is a backtest and is labelled as one. The alternative — the portfolio's real
     * history — answers a different question, in the past tense, and for a portfolio that was
     * mostly cash for most of the window it answers it uselessly: its correlation against a stock
     * benchmark collapses towards zero, so the beta computed on it has nothing to estimate. The
     * two perimeters can disagree on Sharpe and Sortino by more than half, which is why they may
     * not be mixed silently, and why the perimeter is read from the payload's `metadata` rather
     * than assumed here.
     */
    interface Props {
        historicalResults: RiskAnalyticResult[];
        /** The whole `current_composition` wave: the KPI and the scatter both live in it. */
        currentResults?: RiskAnalyticResult[];
        comparisonResult: RiskAnalyticResult | null;
        /** Name of the benchmark beta is measured against, when one is chosen. */
        benchmarkName?: string | null;
        /** Display names for the table's rows and the chart's dots, resolved by the panel. */
        assetNames?: Record<number, string>;
        /** Each asset's icon, for the table, resolved by the panel. */
        assetIcons?: ReadonlyMap<number, string>;
        /** Anchors the Capital Market Line at x = 0. Percent, as the panel holds it. */
        appliedRiskFreePercent?: number;
        loading?: boolean;
        /** The table's instance, for the column menu the panel draws beside the level's manual icon. */
        tableRef?: DataTable<RiskReturnRow>;
    }

    let {historicalResults, currentResults = [], comparisonResult, benchmarkName = null, assetNames = {}, assetIcons = new Map(), appliedRiskFreePercent = 0, loading = false, tableRef = $bindable()}: Props = $props();

    let wave = $derived(selectKpiWave(currentResults, historicalResults));
    let figures = $derived(buildRiskAdjusted(wave.results, comparisonResult));
    let perimeterLabel = $derived(wave.perimeter === null ? '' : $t(`risk.levels.l3.perimeter.${wave.perimeter}`));
    // The perimeter the cards used to state, now said once, beside the table's title.
    let title = $derived(perimeterLabel ? `${$t('risk.levels.l3.scatter.title')} · ${perimeterLabel}` : $t('risk.levels.l3.scatter.title'));

    let riskReturnResult = $derived(resultByCode(currentResults, 'asset_risk_return'));
    let points = $derived(
        buildRiskReturnPoints({
            riskReturnResult,
            comparisonResult,
            assetNames,
            benchmarkName,
            portfolioLabel: $t('risk.levels.l3.scatter.portfolio'),
            details: {
                weight: (share) => $t('risk.levels.l3.scatter.tooltip.weight', {values: {share}}),
                benchmark: $t('risk.levels.l3.scatter.tooltip.benchmark'),
                heldBenchmark: (share) => $t('risk.levels.l3.scatter.tooltip.heldBenchmark', {values: {share}}),
            },
        }),
    );
    // What the scatter leaves out, named by what it is. `cash_weight` alone used to
    // be printed as "cash", and on a portfolio whose unpriced holdings were a third
    // of it — with no cash at all — the sentence announced a third in cash. The split
    // is L2's own (`uncoveredWeight`), so the two levels cannot tell it differently;
    // when it is unknown, neither sentence is said rather than call it all cash.
    let uncovered = $derived(uncoveredWeight(riskReturnResult));
    let outside = $derived(uncovered === null ? null : {cash: uncovered.cash, unpriced: uncovered.unpriced});

    let rows = $derived(
        buildRiskReturnRows({
            riskReturnResult,
            comparisonResult,
            assetNames,
            benchmarkName,
            portfolioLabel: $t('risk.levels.l3.scatter.portfolio'),
            portfolioKpi: {sortino: figures.sortino, sharpe: figures.sharpe, volatility: figures.volatility},
        }),
    );
    // Beta and correlation need a benchmark the comparison actually measured.
    let benchmarkApplies = $derived(figures.beta !== null || rows.some((row) => row.role === 'benchmark'));
</script>

<div class="space-y-4" data-testid="risk-l3" data-perimeter={wave.perimeter ?? ''}>
    {#if loading && rows.length === 0}
        <div class="h-40 animate-pulse rounded-lg bg-gray-100 dark:bg-slate-700" data-testid="risk-l3-loading"></div>
    {:else if rows.length === 0}
        <p class="text-sm text-gray-500 dark:text-gray-400" data-testid="risk-l3-empty">{$t('risk.states.unavailable')}</p>
    {:else}
        <!-- The table, the chart and their notes are the shared level's (`RiskReturnLevel`, with
             the lab's L3°). This page declares the weight, the ratios and — with a benchmark —
             beta and correlation; its blocks keep the `risk-l3-*` names, and its cells take
             `risk-l3-row-*`, so they never collide with another `risk-l3-*` name. -->
        <RiskReturnLevel
            {rows}
            {points}
            capabilities={{weight: true, ratios: true, benchmark: benchmarkApplies}}
            {assetIcons}
            testIdPrefix="risk-l3"
            cellTestIdPrefix="risk-l3-row"
            storageKey="risk-l3"
            {title}
            labels={{
                volatility: $t('risk.levels.l3.scatter.axisVolatility'),
                return: $t('risk.levels.l3.scatter.axisReturn'),
                capitalMarketLine: $t('risk.levels.l3.scatter.line'),
            }}
            riskFreeRate={appliedRiskFreePercent / 100}
            {outside}
            bind:tableRef
        />
    {/if}
</div>
