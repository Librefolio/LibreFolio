<script lang="ts">
    /**
     * The two comparison levels of Asset Global, on one request.
     *
     * **Why one controller for both levels, and not one each.** All five
     * per-asset analytics are `ASSET_SET` × `HISTORICAL`, so asking for them
     * together makes a single canonical request — and `queryRisk` caches and
     * de-duplicates on exactly that key (`riskStore:131`). One flight, one
     * response, two readers.
     *
     * ⚠️ **It is one request for these two levels, not for the page.** The
     * correlation section and the replay section build their own controllers
     * without this opt-in, so the laboratory issues more than one call: theirs
     * carries `[correlation]`, this one carries `correlation` plus the five. An
     * earlier draft of this comment claimed every section asked for the identical
     * set — that was the design intent read back as if it were a measurement, and
     * it was wrong about two sections that never opted in.
     *
     * 🔑 **Commensurability survives that, and here is why it is not luck.**
     * Clause ⓪ of the asset-set contract asks for *one preparation per request*,
     * and `service.py:170` prepares the joint series **once per request, before
     * the analytic loop** — from the scope, the window and the currency, never
     * from which analytics were asked for. Two requests that agree on those three
     * therefore get the *same* joint calendar, so a dot from this wave and a cell
     * from the matrix above are measured over the same dates. What the extra
     * request costs is the preparation, paid twice; what it does not cost is
     * correctness.
     *
     * Folding the matrix into this wave would remove that cost, and was left
     * undone deliberately: it would hand the correlation section a benchmark id
     * it has no use for, purely so its request key would match this one.
     *
     * **Why its own controller rather than the panel's**, and it is the same
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
     * therefore declares **its own** slice — health, reasons, error codes and
     * provenance — through `RiskLevelSection`, and the slices are built by
     * explicit code, never as "everything minus what I know about": a blanket
     * filter reports an analytic no level renders as a fault of whichever level
     * happened to catch it.
     */
    import {_ as t} from '$lib/i18n';
    import {createRiskPanelController} from '$lib/stores/risk/riskPanelController.svelte';

    import AssetSetLossComparisonSection from './AssetSetLossComparisonSection.svelte';
    import AssetSetRiskReturnSection from './AssetSetRiskReturnSection.svelte';
    import {ASSET_SET_DAILY_VAR_INSTANCE, ASSET_SET_MONTHLY_VAR_INSTANCE, resultByCode, resultByInstance} from './riskAnalysisHelpers';
    import {degradedResults, levelMetadata, resultErrorCodes, resultReasons} from './levels/levelHelpers';
    import RiskLevelSection from './levels/RiskLevelSection.svelte';

    interface Props {
        /** Already non-empty: the caller's `{#if}` is the guard, see above. */
        assetIds: number[];
        assetLabels: ReadonlyMap<number, string>;
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
    }

    let {assetIds, assetLabels, dateStart, dateEnd, targetCurrency, benchmarkId}: Props = $props();

    const controller = createRiskPanelController(
        () => ({
            scope: {kind: 'asset_set', asset_ids: assetIds},
            dateStart,
            dateEnd,
            targetCurrency,
            // Sharpe and Sortino are charged against a zero risk-free rate here,
            // as the correlation section already does, because this page has no
            // control to set one — and inventing a rate the reader never chose
            // would put a number in the denominator of every ratio on screen.
            appliedRiskFreePercent: 0,
            refreshVersion: 0,
            assetSetBenchmarkId: benchmarkId,
        }),
        {includeAssetSetLevels: true},
    );

    let historical = $derived(controller.historicalResults);

    // The two VaR horizons share an analytic code, so they are resolved by
    // instance: a lookup by code would return whichever arrived first and the
    // bad day and the bad month would become the same column.
    let dailyVar = $derived(resultByInstance(historical, ASSET_SET_DAILY_VAR_INSTANCE));
    let monthlyVar = $derived(resultByInstance(historical, ASSET_SET_MONTHLY_VAR_INSTANCE));
    let drawdown = $derived(resultByCode(historical, 'asset_set_drawdown'));
    let riskReturn = $derived(resultByCode(historical, 'asset_set_risk_return'));
    let kpi = $derived(resultByCode(historical, 'asset_set_kpi'));
    let comparison = $derived(resultByCode(historical, 'asset_set_comparison'));

    // Each level's own slice. The VaR pair is labelled by instance so a
    // disclosure names the row the reader is missing instead of repeating the
    // analytic's name twice.
    const VAR_LABELS = {
        [ASSET_SET_DAILY_VAR_INSTANCE]: 'risk.assetSet.levels.l1.columns.badDay',
        [ASSET_SET_MONTHLY_VAR_INSTANCE]: 'risk.assetSet.levels.l1.columns.badMonth',
    };

    let l1Results = $derived([dailyVar, monthlyVar, drawdown]);
    let l3Results = $derived([riskReturn, kpi, comparison]);

    let l1Health = $derived(degradedResults(l1Results, VAR_LABELS));
    let l1Reasons = $derived(resultReasons(l1Results));
    let l1Errors = $derived(resultErrorCodes(l1Results));
    let l1Metadata = $derived(levelMetadata(l1Results));

    let l3Health = $derived(degradedResults(l3Results));
    let l3Reasons = $derived(resultReasons(l3Results));
    let l3Errors = $derived(resultErrorCodes(l3Results));
    let l3Metadata = $derived(levelMetadata(l3Results));

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
</script>

<RiskLevelSection title={$t('risk.assetSet.levels.l1.title')} level={1} testId="risk-asset-set-loss" health={l1Health} reasons={l1Reasons} errorCodes={l1Errors} metadata={l1Metadata}>
    <AssetSetLossComparisonSection {assetIds} {assetLabels} {dailyVar} {monthlyVar} {drawdown} loading={controller.initialLoading} />
</RiskLevelSection>

<RiskLevelSection title={$t('risk.assetSet.levels.l3.title')} level={3} testId="risk-asset-set-paid" health={l3Health} reasons={l3Reasons} errorCodes={l3Errors} metadata={l3Metadata}>
    <AssetSetRiskReturnSection {assetIds} {assetLabels} {riskReturn} {kpi} {comparison} {benchmarkApplies} loading={controller.initialLoading} />
</RiskLevelSection>
