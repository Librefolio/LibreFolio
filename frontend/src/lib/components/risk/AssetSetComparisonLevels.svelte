<script lang="ts">
    /**
     * The two comparison levels of Asset Global, each on a request of its own.
     *
     * **Why two controllers, one per level** (the developer's decision of 02/10):
     * L1° is measured without the benchmark, L3° with it. A benchmark is prepared
     * inside the request that asks for its comparison, and joins that request's
     * joint window. When the two levels shared one request, choosing a benchmark
     * moved L1°'s figures — and turned them Partial on prices the benchmark's own
     * dates left stale — for an instrument L1° does not even show. So L1° asks for
     * its share of the per-asset wave (`includeAssetSetLossLevels`: the two VaR
     * horizons and the drawdown) and never the comparison; L3° asks for its share
     * (`includeAssetSetPaidLevels`: the KPI, the risk/return pair and, with a
     * benchmark, the comparison).
     *
     * ⚠️ **They are not the only requests on the page.** The correlation section
     * and the replay section build their own controllers too, so the laboratory
     * issues several calls: each carries `correlation` beside its own analytics.
     *
     * 🔑 **Commensurability survives that, and here is why it is not luck.**
     * Clause ⓪ of the asset-set contract asks for *one preparation per request*,
     * and `RiskService.execute` prepares the joint series (`_prepare_asset_series`)
     * **once per request, before the analytic loop** — from the scope, the window
     * and the currency, never from which analytics were asked for, except that a
     * comparison's reference joins it. Two requests that agree on those three
     * therefore get the *same* joint calendar: without a benchmark, a dot from L3°,
     * a row of L1° and a cell from the matrix above are measured over the same
     * dates. With one, only L3° moves, and its period line says which window it
     * used. What the extra request costs is the preparation, paid again; what it
     * does not cost is correctness.
     *
     * **Why their own controllers rather than the panel's**, and it is the same
     * reason the correlation section gives: `loadBase` has no emptiness check, so
     * a controller declared at the panel's top level fires the instant the
     * selection empties and comes back 422, which the panel would then show as a
     * load failure. Mounting under the caller's `{#if}` makes the component
     * boundary the guard.
     *
     * ⚠️ **The five do not fail together, and the page has to say so.**
     * `asset_set_drawdown` needs 2 observations; the other four need 20. On a
     * short window the honest answer is one `ok` beside four `unavailable`, and
     * without disclosure the reader sees four blanks and one table and cannot
     * tell whether the page is broken or the window is short. Each level
     * therefore declares **its own** slice — what did not come back at all, error
     * codes and provenance — through `RiskLevelSection`, and the slices are built
     * by explicit code, never as "everything minus what I know about": a blanket
     * filter reports an analytic no level renders as a fault of whichever level
     * happened to catch it. What is *partial*, and every warning, the lab says
     * once, in the notice above the sections (`qualitySource()`; the developer,
     * 05/10): one stale price read under every frame was four problems.
     *
     * **The benchmark picker sits in L3°'s frame, above its table** (the developer's
     * review, 06/10: «sopra la tabella, esattamente come in dashboard»), drawn from the
     * panel's `benchmarkPicker`, which owns the choice. Only L3° waits for it: the
     * picker confirms a stored benchmark against the asset list before it says `set`,
     * and while it says `pending` L3°'s controller does not exist yet — it is created by
     * a `RiskControllerHost` mounted under `{#if !benchmarkPending}` — so L3° asks once,
     * with the benchmark, instead of once without it and again with it. L1° never uses
     * the benchmark, so it asks at once. The picker itself is drawn whatever the wait:
     * it is what ends it, and a picker mounted again would start a new one.
     */
    import type {Snippet} from 'svelte';
    import {_ as t} from '$lib/i18n';
    import ColumnVisibilityToggle from '$lib/components/table/ColumnVisibilityToggle.svelte';
    import type DataTable from '$lib/components/table/DataTable.svelte';
    import {ANSWER_DISCARDED_CODE, createRiskPanelController, type RiskControllerInputs, type RiskPanelController} from '$lib/stores/risk/riskPanelController.svelte';

    import AssetSetLossComparisonSection from './AssetSetLossComparisonSection.svelte';
    import type {AssetSetHurtRow, AssetSetPaidRow, AssetSetQualitySource} from './assetSetLevels';
    import AssetSetRiskReturnSection from './AssetSetRiskReturnSection.svelte';
    import {ASSET_SET_DAILY_VAR_INSTANCE, ASSET_SET_MONTHLY_VAR_INSTANCE, resultByCode, resultByInstance} from './riskAnalysisHelpers';
    import {degradedResults, levelMetadata, resultErrorCodes} from './levels/levelHelpers';
    import {levelErrorHealth} from './levels/partialNotice';
    import RiskLevelSection from './levels/RiskLevelSection.svelte';
    import RiskControllerHost from './RiskControllerHost.svelte';

    interface Props {
        /** Already non-empty: the caller's `{#if}` is the guard, see above. */
        assetIds: number[];
        assetLabels: ReadonlyMap<number, string>;
        /** Each asset's icon URL, resolved by the panel, for the loss table's asset cells. */
        assetIcons: ReadonlyMap<number, string>;
        dateStart: string;
        dateEnd: string;
        targetCurrency: string;
        /**
         * The shared L3 benchmark, or null.
         *
         * Resolved by the panel rather than read here, because the decision
         * "does this benchmark apply to this selection" needs the selection, and
         * a component that answered it twice could answer it differently.
         */
        benchmarkId: number | null;
        /** Bumped by the panel after an accepted sync (R2-128). Default: never. */
        refreshVersion?: number;
        /**
         * The picker has not yet confirmed a stored benchmark: L3° waits, and asks once
         * it has (see above). Default: nothing to wait for.
         */
        benchmarkPending?: boolean;
        /** The benchmark picker, drawn at the top of L3°'s frame, above its table. */
        benchmarkPicker?: Snippet;
    }

    let {assetIds, assetLabels, assetIcons, dateStart, dateEnd, targetCurrency, benchmarkId, refreshVersion = 0, benchmarkPending = false, benchmarkPicker}: Props = $props();

    // Sharpe and Sortino are charged against a zero risk-free rate here, as the
    // correlation section already does, because this page has no control to set
    // one — and inventing a rate the reader never chose would put a number in the
    // denominator of every ratio on screen.

    /** L1°: its share of the wave, and never the benchmark — not even read here. */
    const lossController = createRiskPanelController(
        () => ({
            scope: {kind: 'asset_set', asset_ids: assetIds},
            dateStart,
            dateEnd,
            targetCurrency,
            appliedRiskFreePercent: 0,
            refreshVersion,
        }),
        {includeAssetSetLossLevels: true},
    );

    /**
     * L3°: its share of the wave, with the benchmark when one applies. Its controller is
     * created by the `RiskControllerHost` below, once the benchmark is no longer pending,
     * and read here; until then L3° has asked nothing and shows its loading state.
     */
    const paidInputs = (): RiskControllerInputs => ({
        scope: {kind: 'asset_set', asset_ids: assetIds},
        dateStart,
        dateEnd,
        targetCurrency,
        appliedRiskFreePercent: 0,
        refreshVersion,
        assetSetBenchmarkId: benchmarkId,
    });
    let paidController = $state<RiskPanelController>();

    let lossHistorical = $derived(lossController.historicalResults);
    let paidHistorical = $derived(paidController?.historicalResults ?? []);

    // The two VaR horizons share an analytic code, so they are resolved by
    // instance: a lookup by code would return whichever arrived first and the
    // bad day and the bad month would become the same column.
    let dailyVar = $derived(resultByInstance(lossHistorical, ASSET_SET_DAILY_VAR_INSTANCE));
    let monthlyVar = $derived(resultByInstance(lossHistorical, ASSET_SET_MONTHLY_VAR_INSTANCE));
    let drawdown = $derived(resultByCode(lossHistorical, 'asset_set_drawdown'));
    let riskReturn = $derived(resultByCode(paidHistorical, 'asset_set_risk_return'));
    let kpi = $derived(resultByCode(paidHistorical, 'asset_set_kpi'));
    let comparison = $derived(resultByCode(paidHistorical, 'asset_set_comparison'));

    // Each level's own slice. The VaR pair is labelled by instance so a
    // disclosure names the row the reader is missing instead of repeating the
    // analytic's name twice.
    const VAR_LABELS = {
        [ASSET_SET_DAILY_VAR_INSTANCE]: 'risk.assetSet.levels.l1.columns.badDay',
        [ASSET_SET_MONTHLY_VAR_INSTANCE]: 'risk.assetSet.levels.l1.columns.badMonth',
    };

    let l1Results = $derived([dailyVar, monthlyVar, drawdown]);
    let l3Results = $derived([riskReturn, kpi, comparison]);

    // Each frame keeps only what did not come back at all; what is partial, and why, the lab's
    // one notice says above the sections, from `qualitySource()` (the developer, 05/10).
    let l1Health = $derived(levelErrorHealth(degradedResults(l1Results, VAR_LABELS)));
    /**
     * A base answer discarded on every attempt is said once, by the frame, with the same
     * code the replay and the Dashboard's L4 use (`answer_discarded`); the body only
     * offers the retry. Without it both levels showed their rows of dashes in silence.
     * Each level reads its own controller: one level's discarded answer is not the other's.
     */
    let lossDiscardedCodes = $derived(lossController.loadDiscarded ? [ANSWER_DISCARDED_CODE] : []);
    let paidDiscardedCodes = $derived(paidController?.loadDiscarded ? [ANSWER_DISCARDED_CODE] : []);
    let l1Errors = $derived([...resultErrorCodes(l1Results), ...lossDiscardedCodes]);
    let l1Metadata = $derived(levelMetadata(l1Results));

    let l3Health = $derived(levelErrorHealth(degradedResults(l3Results)));
    let l3Errors = $derived([...resultErrorCodes(l3Results), ...paidDiscardedCodes]);
    let l3Metadata = $derived(levelMetadata(l3Results));

    /**
     * What the panel reads through `bind:this` for the lab's one notice: the six results the two
     * frames render, the controllers' own objects in page order (`null` where an answer had
     * none), the two VaR horizons' labels, and both controllers' data-quality issues, L1°'s
     * first. A function, so a `$derived` in the panel tracks what it reads here.
     */
    export function qualitySource(): AssetSetQualitySource {
        return {
            results: [dailyVar, monthlyVar, drawdown, riskReturn, kpi, comparison],
            labels: VAR_LABELS,
            issues: [...lossController.dataQualityIssues, ...(paidController?.dataQualityIssues ?? [])],
        };
    }

    /**
     * Whether the beta and correlation columns have a reference at all.
     *
     * Read from the *answer* rather than from the stored choice, so the columns
     * appear when a measurement exists and not when a preference does. A
     * benchmark that was requested and came back unavailable would otherwise
     * leave two columns of em-dashes that look like missing data rather than an
     * inapplicable comparison.
     */
    let benchmarkApplies = $derived(benchmarkId !== null && comparison?.status === 'ok');

    /**
     * The loss table's instance, bound while the table is on screen. The column toggle
     * it feeds sits in the frame's header beside the manual (the developer's review,
     * 30/09), and only while there is a table to act on.
     */
    let lossTable = $state<DataTable<AssetSetHurtRow>>();
    /** L3°'s table, the same way: its toggle beside L3°'s manual, only while the table is shown. */
    let riskTable = $state<DataTable<AssetSetPaidRow>>();
</script>

<RiskLevelSection title={$t('risk.assetSet.levels.l1.title')} level={1} testId="risk-asset-set-loss" health={l1Health} errorCodes={l1Errors} metadata={l1Metadata} docsPath="financial-theory/technical-analysis/risk-metrics/" actions={lossTable ? lossActions : undefined}>
    <AssetSetLossComparisonSection
        bind:tableRef={lossTable}
        {assetIds}
        {assetLabels}
        {assetIcons}
        {dailyVar}
        {monthlyVar}
        {drawdown}
        loading={lossController.initialLoading}
        failed={lossController.loadError}
        discarded={lossController.loadDiscarded}
        onretry={() => void lossController.loadBase(true)}
    />
</RiskLevelSection>

{#snippet lossActions()}
    <ColumnVisibilityToggle tableRef={lossTable} />
{/snippet}

{#snippet riskActions()}
    <ColumnVisibilityToggle tableRef={riskTable} />
{/snippet}

{#if !benchmarkPending}
    <RiskControllerHost inputs={paidInputs} options={{includeAssetSetPaidLevels: true}} bind:controller={paidController} />
{/if}

<RiskLevelSection title={$t('risk.assetSet.levels.l3.title')} level={3} testId="risk-asset-set-paid" health={l3Health} errorCodes={l3Errors} metadata={l3Metadata} docsPath="financial-theory/technical-analysis/risk-metrics/" actions={riskTable ? riskActions : undefined}>
    {@render benchmarkPicker?.()}
    <AssetSetRiskReturnSection
        bind:tableRef={riskTable}
        {assetIds}
        {assetLabels}
        {assetIcons}
        {riskReturn}
        {kpi}
        {comparison}
        {benchmarkApplies}
        {dateStart}
        {dateEnd}
        loading={paidController?.initialLoading ?? true}
        failed={paidController?.loadError ?? false}
        discarded={paidController?.loadDiscarded ?? false}
        onretry={() => void paidController?.loadBase(true)}
    />
</RiskLevelSection>
