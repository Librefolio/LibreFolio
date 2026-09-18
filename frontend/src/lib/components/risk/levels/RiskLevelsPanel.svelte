<script lang="ts">
    import {_ as t} from '$lib/i18n';
    import type {RiskScope} from '$lib/stores/risk/riskStore.svelte';
    import {createRiskPanelController} from '$lib/stores/risk/riskPanelController.svelte';
    import {assetStoreVersion, getAssetInfo} from '$lib/stores/reference/assetStore';

    import L1HowMuchItHurts from './L1HowMuchItHurts.svelte';
    import L2Diversification from './L2Diversification.svelte';
    import L3Benchmark from './L3Benchmark.svelte';
    import L3RiskAdjusted from './L3RiskAdjusted.svelte';
    import L4WhatIf from './L4WhatIf.svelte';
    import L4Replay from './l4/L4Replay.svelte';
    import L4Shock from './l4/L4Shock.svelte';
    import L4Simulation from './l4/L4Simulation.svelte';
    import RiskLevelSection from './RiskLevelSection.svelte';
    import RiskPanelHeader from './RiskPanelHeader.svelte';
    import {leadDivergence, buildDivergenceRows, degradedResults, resultReasons, backtestDeclared, comparedAssetId} from './levelHelpers';
    import {resultByCode, DAILY_VAR_INSTANCE, MONTHLY_VAR_INSTANCE} from '../riskAnalysisHelpers';

    /**
     * The four levels of risk, as one component.
     *
     * Dashboard and Broker Detail mount *this*, and differ only in `scope` —
     * plus the title and the date source, which are strings, not structure. They
     * are not two similar pages: they are one page seen through two scopes, and
     * the moment they become two components the reader loses the ability to
     * compare them, which is the property this whole redesign exists to build.
     *
     * Each level is a question, asked in order of how much it costs to answer:
     *
     *   L1 how much can it hurt   — open, observed facts only
     *   L2 am I diversified       — open, already in the payload
     *   L3 am I paid for the risk — open, looks outward
     *   L4 what if                — closed, and the only one that asks the server
     */
    interface Props {
        scope: RiskScope;
        dateStart: string;
        dateEnd: string;
        targetCurrency: string;
        title?: string;
        /** Shown under the title; used by Dashboard to flag an active filter. */
        subtitle?: string;
        /** Marks a scope that is a subset of the whole portfolio, as Broker Detail is. */
        internalSubset?: boolean;
        /**
         * What the scope is worth, so L1 can put money beside every percentage.
         *
         * Must be the value of **this scope**, not of whatever the page happens to
         * be showing elsewhere. Dashboard's own summary follows its broker filter
         * while this panel is deliberately unfiltered, so the two disagree exactly
         * when a filter is on — pass `null` rather than a number from a different
         * question. A missing amount is a blank; a mismatched one is a wrong
         * answer that reads as a right one.
         */
        scopeValue?: number | null;
        /** Asset ids in scope, seeding the names and the scenario editors. */
        assetIds?: number[];
        refreshVersion?: number;
        onsynced?: () => void | Promise<void>;
    }

    let {scope, dateStart, dateEnd, targetCurrency, title = '', subtitle = '', internalSubset = false, scopeValue = null, assetIds = [], refreshVersion = 0, onsynced}: Props = $props();

    // The risk-free rate the KPI wave is seeded with. Held here rather than in
    // the controller because it is a user-facing setting, not a fetch concern.
    let appliedRiskFreePercent = $state(0);

    const controller = createRiskPanelController(() => ({scope, dateStart, dateEnd, targetCurrency, appliedRiskFreePercent, refreshVersion}), {
        onsynced: () => onsynced?.(),
        // L1 is the only consumer of these two, and both are opt-in so that
        // turning them on here cannot change what any other surface requests.
        includeDrawdownSummary: true,
        includeMonthlyVar: true,
    });

    let historicalResults = $derived(controller.historicalResults);
    let currentResults = $derived(controller.currentResults);
    let contributionResult = $derived(resultByCode(currentResults, 'risk_contribution'));
    let initialLoading = $derived(controller.initialLoading);
    let loadError = $derived(controller.loadError);

    // Each level discloses only the measurements it actually renders. The filter
    // is by explicit code, not "everything in the wave minus what I know about":
    // `correlation` travels in the same historical wave and is rendered by no
    // level at all, so a blanket filter would report it as an L1 fault — a
    // failure the reader cannot see, cannot check, and cannot act on.
    const L1_CODES = ['historical_var', 'drawdown_summary', 'historical_kpi'];
    const L3_CODES = ['historical_kpi'];
    // The two VaR horizons share an analytic code, so the disclosure names the
    // row the reader is missing rather than repeating "Historical VaR" twice.
    const L1_LABELS = {[DAILY_VAR_INSTANCE]: 'risk.levels.l1.rows.day', [MONTHLY_VAR_INSTANCE]: 'risk.levels.l1.rows.month'};

    let l1Health = $derived(
        degradedResults(
            historicalResults.filter((result) => L1_CODES.includes(result.analytic_code)),
            L1_LABELS,
        ),
    );
    // Already resolved by code, so it needs no filter.
    let l2Health = $derived(degradedResults([contributionResult]));
    let l3Health = $derived(degradedResults([controller.comparisonResult, ...historicalResults.filter((result) => L3_CODES.includes(result.analytic_code))]));

    // The *reasons*, from the same results each level renders. Derived from the
    // identical slices as the health above: a cause disclosed under a question
    // that never consulted the measurement is not transparency, it is an
    // accusation the reader has no way to check.
    let l1Reasons = $derived(resultReasons(historicalResults.filter((result) => L1_CODES.includes(result.analytic_code))));
    let l2Reasons = $derived(resultReasons([contributionResult]));
    let l3Reasons = $derived(resultReasons([controller.comparisonResult, ...historicalResults.filter((result) => L3_CODES.includes(result.analytic_code))]));

    /**
     * L4's three steps, for the same reason as the three levels above — and it
     * was the only section without them.
     *
     * `schemas/risk.py:1056` forbids an `unavailable` or `failed` result from
     * carrying an output, so the `{#if output}` each step renders on is not
     * *probably* empty on that branch: it is empty **by contract**. Without this
     * the reader asks for a simulation, the spinner stops, and nothing appears —
     * no figure and no cause. Reachable today with no exotic input at all: a busy
     * worker, a timeout, a series too short.
     *
     * Naming the step and its state is all that is offered. A timeout is not a
     * question the reader can answer, so no remedy is promised — but it is still
     * something they have to be told.
     */
    let l4Results = $derived([controller.stressResult, controller.replayResult, controller.simulationResult]);
    let l4Health = $derived(degradedResults(l4Results));
    let l4Reasons = $derived(resultReasons(l4Results));

    /**
     * K4. Declared once, above every level, because the basis is a property of
     * the *series* all the historical analytics consumed — not of any one of
     * them. Announcing it inside L1 would leave L3's Sharpe reading as if it
     * came from what actually happened.
     */
    let backtest = $derived(backtestDeclared(historicalResults));

    /**
     * The benchmark's name, resolved where every other name already is.
     *
     * Read from the comparison *answer* rather than from the picker, so the label
     * under beta names the reference the number was actually computed against —
     * not the one the reader has just selected but not yet run.
     */
    let benchmarkName = $derived.by(() => {
        void $assetStoreVersion;
        const id = comparedAssetId(controller.comparisonResult);
        if (id === null) return null;
        return getAssetInfo(id)?.display_name ?? `#${id}`;
    });

    let divergenceRows = $derived(buildDivergenceRows(contributionResult));
    let lead = $derived(leadDivergence(divergenceRows));

    /**
     * Names for every asset the answer mentions.
     *
     * Derived here rather than passed in: both pages would compute the same map
     * from the same store, and two copies of one rule is how the two pages start
     * drifting apart.
     */
    let assetNames = $derived.by(() => {
        void $assetStoreVersion;
        const ids = new Set<number>(assetIds);
        divergenceRows.forEach((row) => ids.add(row.assetId));
        const names: Record<number, string> = {};
        for (const assetId of ids) names[assetId] = getAssetInfo(assetId)?.display_name ?? `#${assetId}`;
        return names;
    });

    /** L2's headline, generated from the data — or empty when nothing stands out. */
    let l2Lead = $derived.by(() => {
        if (!lead) return '';
        return $t('risk.levels.l2.lead', {
            values: {
                name: assetNames[lead.assetId] ?? `#${lead.assetId}`,
                weight: `${(lead.weight * 100).toFixed(0)}%`,
                contribution: `${(lead.contribution * 100).toFixed(0)}%`,
            },
        });
    });
</script>

<div class="space-y-4" data-testid="risk-levels-panel" data-scope={scope.kind} data-catalog={controller.catalogState} data-busy={initialLoading ? 'true' : 'false'}>
    <RiskPanelHeader {controller} {title} {subtitle} {internalSubset} {assetIds} {dateStart} {dateEnd} {targetCurrency} />

    {#if backtest}
        <p class="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800 dark:border-amber-900/50 dark:bg-amber-950/30 dark:text-amber-300" data-testid="risk-backtest-notice">
            {$t('risk.levels.backtestNotice')}
        </p>
    {/if}

    {#if !loadError}
        <RiskLevelSection level={1} title={$t('risk.levels.l1.title')} testId="risk-level-1" health={l1Health} reasons={l1Reasons}>
            <L1HowMuchItHurts {historicalResults} {scopeValue} currency={targetCurrency} loading={initialLoading} />
        </RiskLevelSection>

        <RiskLevelSection level={2} title={$t('risk.levels.l2.title')} lead={l2Lead} testId="risk-level-2" health={l2Health} reasons={l2Reasons}>
            <L2Diversification {contributionResult} {assetNames} loading={initialLoading} />
        </RiskLevelSection>

        <RiskLevelSection level={3} title={$t('risk.levels.l3.title')} testId="risk-level-3" health={l3Health} reasons={l3Reasons}>
            <L3Benchmark {controller} excludeAssetIds={assetIds} />
            <L3RiskAdjusted {historicalResults} comparisonResult={controller.comparisonResult} {benchmarkName} loading={initialLoading} />
        </RiskLevelSection>

        <!-- Closed until asked for, and the scenario catalogue is fetched on that
             first open only: reopening a drawer is not a change of question, so
             it must not start the work over. -->
        <RiskLevelSection level={4} title={$t('risk.levels.l4.title')} collapsible testId="risk-level-4" health={l4Health} reasons={l4Reasons} onfirstopen={() => controller.loadScenarioCatalog()}>
            <L4WhatIf>
                {#snippet replay()}
                    <L4Replay {controller} {assetNames} currency={targetCurrency} {dateStart} {dateEnd} />
                {/snippet}
                {#snippet shock()}
                    <L4Shock {controller} {assetNames} currency={targetCurrency} />
                {/snippet}
                {#snippet simulation()}
                    <L4Simulation {controller} {dateEnd} />
                {/snippet}
            </L4WhatIf>
        </RiskLevelSection>
    {/if}
</div>
