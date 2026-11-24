<script lang="ts">
    import {untrack} from 'svelte';
    import {_ as t} from '$lib/i18n';
    import type {RiskAnalyticResult, RiskScope} from '$lib/features/risk/riskStore.svelte';
    import {createRiskPanelController, discardedErrorCodes, LEVEL_ON_DEMAND_ANALYSES, type RiskSyncCompletion} from '$lib/features/risk/riskPanelController.svelte';
    import {setTweenHydration} from '$lib/components/ui/TweenedValue.svelte';
    import {toasts} from '$lib/stores/app/toastStore.svelte';
    import {assetStoreVersion, getAssetInfo} from '$lib/stores/reference/assetStore';
    import {getAssetTypeIconUrl} from '$lib/utils/assetTypes';
    import ColumnVisibilityToggle from '$lib/components/table/ColumnVisibilityToggle.svelte';
    import type DataTable from '$lib/components/table/DataTable.svelte';
    import type {RiskReturnRow} from '../riskReturnLevel';
    import {withWholeBroker} from '../riskRequest';

    import L1HowMuchItHurts from './L1HowMuchItHurts.svelte';
    import HowItMoves from './HowItMoves.svelte';
    import L2Diversification from './L2Diversification.svelte';
    import L3Benchmark from './L3Benchmark.svelte';
    import L3RiskAdjusted from './L3RiskAdjusted.svelte';
    import L4WhatIf from './L4WhatIf.svelte';
    import L4Replay from './l4/L4Replay.svelte';
    import {replaySectionView} from './l4/scenarioHelpers';
    import L4Shock from './l4/L4Shock.svelte';
    import L4Simulation from './l4/L4Simulation.svelte';
    import RiskLevelSection from './RiskLevelSection.svelte';
    import RiskPanelHeader from './RiskPanelHeader.svelte';
    import {leadDivergence, buildDivergenceRows, degradedResults, resultReasons, resultErrorCodes, levelMetadata, backtestDeclared, comparedAssetId} from './levelHelpers';
    import {levelErrorHealth, partialNotice} from './partialNotice';
    import RiskPartialNotice from './RiskPartialNotice.svelte';
    import {selectKpiWave} from './l3Helpers';
    import {resultByCode, resultByInstance, DAILY_VAR_INSTANCE, MONTHLY_VAR_INSTANCE} from '../riskAnalysisHelpers';
    import {buildMoveFigures, moveLead, semiDeviationPerimeterDiffers} from '../moveFigures';
    import {formatPercent} from '$lib/utils/core/formatPercent';
    import {riskFreeRate} from '../riskFreeRateStore.svelte';
    import {goto} from '$app/navigation';
    import {buildTabUrlFromLocation} from '$lib/utils/url/tabUrl';
    import L4Rates from './l4/L4Rates.svelte';
    import {rateShockAvailability} from './l4/scenarioHelpers';

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
        /**
         * The page shows its amounts whole, not at the owner's share (Broker Detail, MF6-3, developer's decision D4): a portfolio
         * scope is then queried with `apply_ownership_share: false`, so the stress impacts and the scope value match the page's.
         */
        wholeBroker?: boolean;
        /** Marks a scope that is a subset of the whole portfolio, as Broker Detail is. */
        internalSubset?: boolean;
        /**
         * What the scope is worth, so L1 can put money beside every percentage.
         *
         * Must be the value of **this scope**, not of whatever the page happens to
         * be showing elsewhere. The Dashboard asks over the brokers of the summary
         * on screen (RSK-F), so the summary's net worth is this scope's; a host
         * whose figures answer another scope passes `null` instead. A missing
         * amount is a blank; a mismatched one is a wrong answer that reads as a
         * right one.
         */
        scopeValue?: number | null;
        /** Asset ids in scope, seeding the names and the scenario editors. */
        assetIds?: number[];
        refreshVersion?: number;
        onsynced?: (detail: RiskSyncCompletion) => void | Promise<void>;
        /** One asset's type (the Asset Detail): a bond without a duration says so in its «What if…?» (RN-25). */
        assetType?: string | null;
    }

    let {scope, dateStart, dateEnd, targetCurrency, title = '', subtitle = '', wholeBroker = false, internalSubset = false, scopeValue = null, assetIds = [], refreshVersion = 0, onsynced, assetType = null}: Props = $props();

    // The reader's risk-free rate (RN-21): one value for every risk page, read from its store. A change is a new
    // question: the controller's signature carries it, so the answers that read it are asked again.
    let appliedRiskFreePercent = $derived(riskFreeRate.percent);

    const controller = createRiskPanelController(() => ({scope: withWholeBroker(scope, wholeBroker), dateStart, dateEnd, targetCurrency, appliedRiskFreePercent, refreshVersion}), {
        onsynced: (detail) => onsynced?.(detail),
        // Page cache: a failed refresh of the figures on screen keeps them, and says so.
        onrefreshfailed: () => toasts.error($t('risk.states.loadFailed')),
        // L1 is the only consumer of these two, and both are opt-in so that
        // turning them on here cannot change what any other surface requests.
        includeDrawdownSummary: true,
        includeMonthlyVar: true,
        // L3's own perimeter, and the scatter it draws.
        //
        // This was the outage. `L3RiskAdjusted` is built to read the *current
        // composition* wave — its docstring argues the case at length — but
        // nothing ever asked for that wave, so `selectKpiWave` fell through to
        // the historical one on every visit and `asset_risk_return` was never
        // requested at all. Two failures in series, both silent: the request did
        // not ask, and the answer was not passed on.
        //
        // ⚠️ Turning this on is not cosmetic. It adds `historical_kpi` on the
        // current-composition wave, which `selectKpiWave` then *prefers*, so
        // Sortino, Sharpe, volatility and beta are computed over today's weights
        // replayed on past returns rather than over the portfolio's own history.
        // The two perimeters can disagree by more than half their own value —
        // which is exactly why the card reads the perimeter from the payload and
        // prints it, instead of anyone assuming which one is on screen.
        // One asset draws no L3 (81 U29), so it does not ask for what only L3 reads. The kind of scope never changes while
        // the panel is mounted (the page remounts it), so reading it once is the intent.
        includeCurrentCompositionRiskReturn: untrack(() => scope.kind !== 'asset'),
        // RN-25: the asset's rates scenario rides in the same wave; the catalogue offers it on one asset only.
        includeRateShock: true,
    });
    // Cards served from the risk cache appear at their value instead of counting up from 0.
    setTweenHydration(() => controller.hydratedFromCache);

    let historicalResults = $derived(controller.historicalResults);
    let currentResults = $derived(controller.currentResults);
    let contributionResult = $derived(resultByCode(currentResults, 'risk_contribution'));
    /** The asset's rates scenario (RN-25): the tool, a bond's missing duration, or nothing. */
    let rateShockResult = $derived(resultByCode(currentResults, 'rate_shock'));
    let rates = $derived(rateShockAvailability(rateShockResult, assetType));
    // `correlation` is requested in the historical wave (`buildBaseAnalytics` in `riskAnalysisHelpers.ts`)
    // and was resolved and handed to nobody. It is not a datum to ask for: it is
    // one already paid for and thrown away.
    let correlationResult = $derived(resultByCode(historicalResults, 'correlation'));
    let initialLoading = $derived(controller.initialLoading);
    /** The Asset Detail's x-ray (RN-17): only the levels and tools that have meaning on one asset. */
    let oneAsset = $derived(scope.kind === 'asset');
    let loadError = $derived(controller.loadError);

    // Each level discloses only the measurements it actually renders. The filter
    // is by explicit code, not "everything in the wave minus what I know about":
    // a blanket filter would report an analytic no level renders as a fault of
    // whichever level happened to catch it — a failure the reader cannot see,
    // cannot check, and cannot act on. `correlation` was that analytic until L2
    // started rendering it, which is why it now travels in L2's disclosures
    // below: **a section that renders two results must declare two.**
    const L1_CODES = ['historical_var', 'drawdown_summary', 'historical_kpi'];
    // The two VaR horizons share an analytic code, so the disclosure names the
    // row the reader is missing rather than repeating "Historical VaR" twice.
    const L1_LABELS = {[DAILY_VAR_INSTANCE]: 'risk.levels.l1.rows.day', [MONTHLY_VAR_INSTANCE]: 'risk.levels.l1.rows.month'};

    let l1Results = $derived(historicalResults.filter((result) => L1_CODES.includes(result.analytic_code)));
    // «How does it move?» (RN-18) reads L1's own answers — the KPI, the 30-day VaR's best window, the drawdown summary —
    // and asks nothing of its own; so it declares nothing either: what failed is said once, in L1's frame.
    let moveFigures = $derived(buildMoveFigures(resultByCode(historicalResults, 'historical_kpi'), resultByInstance(historicalResults, MONTHLY_VAR_INSTANCE), resultByCode(historicalResults, 'drawdown_summary')));
    let moveHeadline = $derived(moveLead(moveFigures, $t));
    // L3 declares what it draws (F2b): the benchmark comparison, the KPI of the wave
    // `L3RiskAdjusted` picks — the current composition's when it came back, through
    // the same `selectKpiWave` — and the current composition's risk/return scatter.
    // It used to declare the *historical* KPI while drawing the other one, so the
    // notice missed two measurements that had lost the same holdings.
    let l3Kpi = $derived(resultByCode(selectKpiWave(currentResults, historicalResults).results, 'historical_kpi'));
    // One asset draws no L3 (81 U29): nothing of it is declared there.
    let l3Results = $derived(oneAsset ? [] : [controller.comparisonResult, l3Kpi, resultByCode(currentResults, 'asset_risk_return')]);
    // L3's own KPI is named for what L3 shows from it: in L3, "historical risk
    // metrics" — its catalogue name — would be false. Not when it is L1's
    // historical one, drawn by L3 only as a fallback: that keeps L1's name.
    let labels = $derived<Record<string, string>>(l3Kpi && !l1Results.includes(l3Kpi) ? {...L1_LABELS, [l3Kpi.instance_id]: 'risk.levels.l3.rows.kpi'} : L1_LABELS);

    let l1Health = $derived(degradedResults(l1Results, L1_LABELS));
    // Already resolved by code, so it needs no filter.
    let l2Health = $derived(degradedResults([contributionResult, correlationResult]));
    let l3Health = $derived(degradedResults(l3Results, labels));

    // What is partial, and why, said once above the levels (developer's decision of
    // 24/09/2026): the same carried-over price or excluded asset used to be repeated
    // under each level that consulted it, and read as four problems. The notice reads
    // the same slices the levels render — never the whole wave, so an analytic no level
    // shows is not reported — and each level keeps only what did not come back at all,
    // named where it is missing. L4, asked on demand, keeps its own disclosure.
    let notice = $derived(partialNotice([...l1Results, contributionResult, correlationResult, ...l3Results], $t, labels));
    /**
     * The level that renders each measurement, claimed in page order, so the notice
     * groups what a cause cost under the questions the reader sees below it
     * (developer's decision of 30/09/2026). The first claim wins: a measurement two
     * levels read — L1's historical KPI, when L3 falls back to it — is named once,
     * where the page shows it first, as `uniqueByInstance` counts it once.
     */
    let levelOf = $derived.by(() => {
        const claimed: Record<string, 1 | 2 | 3> = {};
        const claim = (results: ReadonlyArray<RiskAnalyticResult | null | undefined>, level: 1 | 2 | 3) => {
            for (const result of results) if (result && !(result.instance_id in claimed)) claimed[result.instance_id] = level;
        };
        claim(l1Results, 1);
        claim([contributionResult, correlationResult], 2);
        claim(l3Results, 3);
        return claimed;
    });

    // The *codes* of what did not come back at all, from those same slices.
    //
    // Deliberately not folded into the reasons: those carry finished sentences
    // (translated from the backend's key, or its own words), these carry
    // identifiers the section words itself. A level with
    // no rows looks identical whether the analytic is out of scope, short of
    // history, or still in flight — and says "unavailable for the selected
    // data", blaming the reader's portfolio for a limit of the analytic.
    let l1Errors = $derived(resultErrorCodes(l1Results));
    let l2Errors = $derived(resultErrorCodes([contributionResult, correlationResult]));
    // An on-demand answer discarded on every attempt is disclosed where its figures would be: the
    // benchmark comparison under L3, the three what-if steps under L4.
    let l3Errors = $derived([...resultErrorCodes(l3Results), ...discardedErrorCodes(controller.discarded, LEVEL_ON_DEMAND_ANALYSES.l3)]);

    // What each level's figures were computed over. Same slices again: a window
    // reported under a question that did not consult the measurement describes
    // the wrong number, and describing the wrong number is worse than describing
    // none, because it reads as an answer.
    let l1Metadata = $derived(levelMetadata(l1Results));
    let l2Metadata = $derived(levelMetadata([contributionResult, correlationResult]));
    let l3Metadata = $derived(levelMetadata(l3Results));

    /**
     * L4's three steps, for the same reason as the three levels above — and it
     * was the only section without them.
     *
     * `RiskAnalyticResult.validate_status_payload` (`schemas/risk/results.py`)
     * forbids an `unavailable` or `failed` result from carrying an output, so
     * the `{#if output}` each step renders on is not *probably* empty on that
     * branch: it is empty **by contract**. Without this the reader asks for a
     * simulation, the spinner stops, and nothing appears — no figure and no
     * cause. Reachable today with no exotic input at all: a busy worker, a
     * timeout, a series too short.
     *
     * Naming the step and its state is all that is offered. A timeout is not a
     * question the reader can answer, so no remedy is promised — but it is still
     * something they have to be told.
     *
     * The replay enters as `replaySectionView` (D372): its exclusion and coverage
     * warnings, and the error of a replay with nothing left, are read in the
     * replay block beside the number, so the section keeps only its status line.
     */
    let replayView = $derived(replaySectionView(controller.replayResult));
    let l4Results = $derived([controller.stressResult, replayView, controller.simulationResult]);

    /**
     * The status line names each step by the title its block wears below, in the
     * blocks' order.
     *
     * Not by instance, the way L1 tells its two VaR apart. The shock and the replay
     * are both the `stress` analytic, asked one at a time, so both come back as
     * `single-stress`: a label keyed on the instance fits both at once, and without
     * one both read "Stress test" — the replay announced as a shock nobody ran. The
     * section's list is keyed on the same id, and two degraded steps would hand it
     * the same key twice. So the step names the entry and gives it its key; the
     * payload only says how it went.
     */
    const L4_STEP_LABELS = {replay: 'risk.levels.l4.replay', shock: 'risk.levels.l4.shock', simulation: 'risk.levels.l4.simulation'} as const;
    let l4Health = $derived(
        (
            [
                ['replay', replayView],
                ['shock', controller.stressResult],
                ['simulation', controller.simulationResult],
            ] as const
        ).flatMap(([step, result]) => degradedResults([result], result ? {[result.instance_id]: L4_STEP_LABELS[step]} : {}).map((entry) => ({...entry, instanceId: `l4-${step}`}))),
    );
    let l4Reasons = $derived(resultReasons(l4Results, $t));
    let l4Errors = $derived([...resultErrorCodes(l4Results), ...discardedErrorCodes(controller.discarded, LEVEL_ON_DEMAND_ANALYSES.l4)]);
    let l4Metadata = $derived(levelMetadata(l4Results));

    /**
     * K4. Declared once, above every level, because the basis is a property of
     * the *series* all the historical analytics consumed — not of any one of
     * them. Announcing it inside L1 would leave L3's Sharpe reading as if it
     * came from what actually happened.
     */
    let backtest = $derived(backtestDeclared(historicalResults));
    // RN-18b: the semi-deviation's swing and L3's volatility differ only when they read two series.
    let moveSwingDiffers = $derived(semiDeviationPerimeterDiffers({oneAsset, backtest, l3Perimeter: selectKpiWave(currentResults, historicalResults).perimeter}));

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

    /**
     * L3's table, for its column menu beside the level's manual icon — the lab's place for it
     * (developer's review of 06/10/2026: «nello stesso punto»). Set only while the table is on screen.
     */
    let l3Table = $state<DataTable<RiskReturnRow>>();

    /**
     * Each asset's icon, for L3's table: its own, or its type's, by the lab's rule — the benchmark's
     * too, whose row the table adds when nobody holds it.
     */
    let assetIcons = $derived.by(() => {
        void $assetStoreVersion;
        const icons = new Map<number, string>();
        const benchmarkId = comparedAssetId(controller.comparisonResult);
        const ids = [...Object.keys(assetNames).map(Number), ...(benchmarkId === null ? [] : [benchmarkId])];
        for (const assetId of ids) {
            const info = getAssetInfo(assetId);
            if (info) icons.set(assetId, info.icon_url || getAssetTypeIconUrl(info.asset_type));
        }
        return icons;
    });

    /** L2's headline, generated from the data — or empty when nothing stands out. */
    let l2Lead = $derived.by(() => {
        if (!lead) return '';
        return $t('risk.levels.l2.lead', {
            values: {
                name: assetNames[lead.assetId] ?? `#${lead.assetId}`,
                weight: formatPercent(lead.weight, {scale: 100, signed: false, digits: 0}),
                contribution: formatPercent(lead.contribution, {scale: 100, signed: false, digits: 0}),
            },
        });
    });
</script>

<div class="space-y-4 text-lf-primary" data-testid="risk-levels-panel" data-scope={scope.kind} data-catalog={controller.catalogState} data-busy={initialLoading ? 'true' : 'false'}>
    <!-- One asset: the Asset Detail toolbar holds the page's one Refresh (Y11, decision 48), so the header draws no sync of its own;
         its docs icon opens the Asset Detail's own page, in the asset's words (RN-17 c). -->
    <RiskPanelHeader {controller} {title} {subtitle} {internalSubset} {assetIds} {dateStart} {dateEnd} {targetCurrency} showActions={!oneAsset} {oneAsset} riskFreeRate={oneAsset} />

    {#if backtest}
        <p class="rounded-lg border border-lf-warning-line bg-lf-warning-soft px-3 py-2 text-xs text-lf-warning-on-soft" data-testid="risk-backtest-notice">
            {$t('risk.levels.backtestNotice')}
        </p>
    {/if}

    {#if !loadError}
        <RiskPartialNotice partial={notice.partial} reasons={notice.reasons} {levelOf} />

        <!-- Every level links the risk-metrics index, without an anchor: an anchor would break on the
             translated sites until the index is translated (coordinator's mapping, 29/09/2026). The
             frame places the icon — beside the toggle on L4, which is collapsible. -->
        <RiskLevelSection level={1} title={$t('risk.levels.l1.title')} testId="risk-level-1" docsPath="financial-theory/technical-analysis/risk-metrics/" health={levelErrorHealth(l1Health)} errorCodes={l1Errors} metadata={l1Metadata}>
            <L1HowMuchItHurts {historicalResults} {scopeValue} currency={targetCurrency} loading={initialLoading} />
        </RiskLevelSection>

        <!-- RN-18 (Q21 c, Q22 a): the positive twin of L1, the same block on every surface. No health of its own: its answers
             are L1's, and a second amber frame would repeat L1's word for word. -->
        <RiskLevelSection level="move" title={$t('risk.levels.move.title')} lead={moveHeadline} testId="risk-level-move" docsPath="financial-theory/technical-analysis/risk-metrics/">
            <HowItMoves figures={moveFigures} {scopeValue} currency={targetCurrency} loading={initialLoading} perimeterDiffers={moveSwingDiffers} />
        </RiskLevelSection>

        <!-- One asset (RN-17): nothing to diversify — correlation and risk contribution do not declare the asset scope. -->
        {#if !oneAsset}
            <RiskLevelSection level={2} title={$t('risk.levels.l2.title')} lead={l2Lead} testId="risk-level-2" docsPath="financial-theory/technical-analysis/risk-metrics/" health={levelErrorHealth(l2Health)} errorCodes={l2Errors} metadata={l2Metadata}>
                <L2Diversification {contributionResult} {correlationResult} {assetNames} loading={initialLoading} />
            </RiskLevelSection>
        {/if}

        <!-- One asset: no benchmark level (81 U29, developer): one asset beside one reference is not a table worth drawing. The rate field then sits under the period line, where L1's semi-deviation still reads it. -->
        {#if !oneAsset}
            {#snippet l3Actions()}
                <ColumnVisibilityToggle tableRef={l3Table} />
            {/snippet}

            <RiskLevelSection level={3} title={$t('risk.levels.l3.title')} testId="risk-level-3" docsPath="financial-theory/technical-analysis/risk-metrics/" health={levelErrorHealth(l3Health)} errorCodes={l3Errors} metadata={l3Metadata} actions={l3Table ? l3Actions : undefined}>
                <L3Benchmark {controller} riskFreePercent={appliedRiskFreePercent} period={{start: dateStart, end: dateEnd}} currency={targetCurrency} />
                <L3RiskAdjusted bind:tableRef={l3Table} {historicalResults} {currentResults} {assetNames} {assetIcons} comparisonResult={controller.comparisonResult} {benchmarkName} loading={initialLoading} />
            </RiskLevelSection>
        {/if}

        <!-- Closed until asked for, and the scenario catalogue is fetched on that
             first open only: reopening a drawer is not a change of question, so
             it must not start the work over. -->
        <RiskLevelSection
            level={4}
            title={$t('risk.levels.l4.title')}
            collapsible
            testId="risk-level-4"
            docsPath="financial-theory/technical-analysis/risk-metrics/"
            health={l4Health}
            reasons={l4Reasons}
            errorCodes={l4Errors}
            metadata={l4Metadata}
            onfirstopen={() => controller.loadScenarioCatalog()}
        >
            <L4WhatIf {controller} rates={rates === 'tool' ? ratesTool : undefined} notes={rates === 'missing' ? ratesMissing : undefined}>
                {#snippet replay()}
                    <L4Replay {controller} {assetNames} currency={targetCurrency} {dateStart} {dateEnd} {scopeValue} />
                {/snippet}
                {#snippet shock()}
                    <L4Shock {controller} {assetNames} currency={targetCurrency} withoutTypeShock={oneAsset} {scopeValue} />
                {/snippet}
                {#snippet simulation()}
                    <L4Simulation {controller} {dateEnd} />
                {/snippet}
            </L4WhatIf>
        </RiskLevelSection>
    {/if}
</div>

{#snippet ratesTool()}
    <L4Rates result={rateShockResult} currency={targetCurrency} {scopeValue} />
{/snippet}
{#snippet ratesMissing()}
    <!-- RN-25: on a bond the reader expects the tool; an empty box would read as «it does not exist». -->
    <p class="text-xs text-lf-muted" data-testid="risk-l4-rates-missing">
        {$t('risk.levels.l4.ratesMissing')}
        <button type="button" class="text-lf-link hover:underline" onclick={() => goto(buildTabUrlFromLocation(window.location.href, 'profile'), {noScroll: true})} data-testid="risk-l4-rates-missing-profile">{$t('risk.levels.l4.ratesMissingLink')}</button>
    </p>
{/snippet}
