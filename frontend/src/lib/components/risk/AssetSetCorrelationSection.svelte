<script lang="ts">
    /**
     * L2 for Asset Global — the correlation matrix, on its own data path.
     *
     * **A component and not a block in the panel, because the boundary is the
     * guard.** An `asset_set` scope needs at least one id; a controller declared
     * at the panel's top level would fire the instant the selection emptied, and
     * `loadBase` has no emptiness check — the request would reach the API and
     * come back 422, which the panel would then show as a load failure. Mounting
     * this under the same `{#if}` that already gates the analysis is exactly how
     * the legacy panel solved the identical problem; the only difference is
     * which component the `{#if}` protects.
     *
     * **Its own controller rather than the legacy's**, because on an `asset_set`
     * scope six of `RiskAnalysisPanel`'s eight sections are switched off by the
     * catalogue, and of the two that survive one is a hypothetical shock this
     * page is not allowed to show. Asking for the matrix directly costs no extra
     * request — `queryRisk` is cached by canonical request and de-duplicates in
     * flight — and it buys the one thing the matrix could not have while it
     * lived inside the legacy: a section whose title is the whole of its
     * content.
     *
     * **No money crosses this component.** A set of assets carries no weights,
     * so there is no amount it could honestly put a currency on.
     *
     * **It discloses through the redesign's own frame, not its own.** A matrix
     * computed over a selection the server had to trim is still a matrix: it
     * renders, it looks whole, and nothing in its shape says an asset is
     * missing. `RiskLevelSection` already carries that disclosure for the four
     * levels, and `degradedResults`/`resultReasons` already compute it, so this
     * section borrows all three rather than growing a fifth copy — and inherits
     * every future repair to them for free.
     */
    import {schemas} from '$lib/api';
    import {_ as t} from '$lib/i18n';
    import {riskOutput} from '$lib/risk/riskTypes';
    import {currentLanguage} from '$lib/stores/app/language';
    import {ANSWER_DISCARDED_CODE, createRiskPanelController} from '$lib/stores/risk/riskPanelController.svelte';
    import CorrelationHeatmap from './CorrelationHeatmap.svelte';
    import {createMatrixMetadata} from './matrixMetadata.svelte';
    import {degradedResults, levelMetadata, resultReasons} from './levels/levelHelpers';
    import RiskLevelSection from './levels/RiskLevelSection.svelte';
    import {resultByCode} from './riskAnalysisHelpers';

    interface Props {
        /** Already non-empty: the caller's `{#if}` is the guard, see above. */
        assetIds: number[];
        /** Axis names the page already holds. Missing ids degrade to `#id`. */
        assetLabels: ReadonlyMap<number, string>;
        /** Asset types by id, for the matrix's "by type" ordering. */
        assetTypes?: ReadonlyMap<number, string | null | undefined>;
        dateStart: string;
        dateEnd: string;
        targetCurrency: string;
        /** Bumped by the panel after an accepted sync: forces a fresh base read. */
        refreshVersion?: number;
    }

    let {assetIds, assetLabels, assetTypes, dateStart, dateEnd, targetCurrency, refreshVersion = 0}: Props = $props();
    const controller = createRiskPanelController(() => ({
        scope: {kind: 'asset_set', asset_ids: assetIds},
        dateStart,
        dateEnd,
        targetCurrency,
        // No risk-free rate reaches a correlation: it is a rate the Sharpe family
        // needs, and passing a live one here would re-ask the question on every
        // keystroke in a control this section does not read.
        appliedRiskFreePercent: 0,
        refreshVersion,
    }));

    let result = $derived(resultByCode(controller.historicalResults, 'correlation'));
    let output = $derived(riskOutput(result, schemas.RiskCorrelationOutput));

    let health = $derived(degradedResults([result]));
    let reasons = $derived(resultReasons([result], $t));
    /**
     * The window the figures were measured over — now rendered by the frame.
     *
     * This lived here as a local block only while `RiskLevelSection` had no
     * metadata slot, and its own docstring said to delete it the day the slot
     * arrived, "or the reader will see it twice". The slot arrived, so it is
     * gone, and the local copy of the runtime-key guard went with it:
     * `translateOrRaw` is the same comparison, lifted where every level gets it.
     *
     * ⚠️ One field does not survive the lift: `levelMetadata` drops `method` on
     * purpose. That costs this section nothing, and for a sharper reason than
     * the one it gives — the correlation plugin (`risk_plugins/correlation.py`)
     * assigns `method` exactly once, `"pearson_post_fx"`. The field can print exactly
     * one string forever, and a value that cannot vary is not provenance.
     */
    let metadata = $derived(levelMetadata([result]));
    /** A base answer discarded twice running is said by the frame, as on L1°/L3°, the replay and the Dashboard's L4. */
    let errorCodes = $derived(controller.loadDiscarded ? [ANSWER_DISCARDED_CODE] : []);

    /**
     * Sector and country distributions of the selection, for the matrix's two
     * exposure orderings (F-3b), loaded by the shared `matrixMetadata` module
     * (K11: the Dashboard's L2 matrix reads the same inputs). One bulk GET of the
     * asset metadata: it cannot trigger `notifyPortfolioMutation`, so it cannot
     * discard the correlation answer in flight. A failed read leaves the maps
     * empty, and the two buttons simply do not appear.
     *
     * The module also reads each asset's type, but this section keeps taking the
     * types from the page's list (`assetTypes`): they are known before any read,
     * and the "by type" ordering must survive a failed metadata read.
     */
    const matrixMetadata = createMatrixMetadata(() => ({assetIds, language: $currentLanguage}));
</script>

<RiskLevelSection title={$t('risk.analytics.correlation.name')} level={2} testId="risk-correlation-section" docsPath="financial-theory/technical-analysis/risk-metrics/correlation/" docsLabel={$t('risk.analytics.correlation.help')} {health} {reasons} {errorCodes} {metadata}>
    <!-- `data-catalog` is published here because every section on this page is
         gated on the capability catalogue, so an absent section means
         "unsupported" *or* "not loaded yet" and a test cannot tell which. The
         legacy panel used to publish it for the whole page; it no longer mounts
         here, and a gate on a component that left is a gate that waits forever. -->
    <div data-testid="risk-correlation-content" data-busy={controller.initialLoading ? 'true' : 'false'} data-catalog={controller.catalogState}>
        <p class="mb-3 text-xs text-gray-500 dark:text-gray-400">{$t('risk.analytics.correlation.description')}</p>

        {#if controller.loadError}
            <div class="py-6 text-center" data-testid="risk-correlation-error">
                <p class="text-sm text-red-600 dark:text-red-400">{$t('risk.states.loadFailed')}</p>
                <button type="button" class="mt-2 rounded-md border border-gray-300 px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-50 dark:border-slate-600 dark:text-gray-200 dark:hover:bg-slate-700" onclick={() => void controller.loadBase(true)} data-testid="risk-correlation-retry"
                    >{$t('common.retry')}</button
                >
            </div>
        {:else if output}
            <CorrelationHeatmap {output} {assetLabels} {assetTypes} assetSectors={matrixMetadata.sectors} assetRegions={matrixMetadata.regions} />
        {:else if controller.initialLoading}
            <div class="h-48 animate-pulse rounded-lg bg-gray-100 dark:bg-slate-700" data-testid="risk-correlation-loading"></div>
        {:else if controller.loadDiscarded}
            <!-- The answer arrived and a session transition made it unreadable, twice
                 running. "No result" here would describe the world, when the fact is
                 about this client — and the cure is to ask again, not to explain, so
                 this branch carries the action and nothing else. -->
            <div class="py-6 text-center" data-testid="risk-correlation-discarded">
                <button type="button" class="rounded-md border border-gray-300 px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-50 dark:border-slate-600 dark:text-gray-200 dark:hover:bg-slate-700" onclick={() => void controller.loadBase(true)} data-testid="risk-correlation-retry"
                    >{$t('common.retry')}</button
                >
            </div>
        {:else}
            <p class="py-6 text-center text-sm text-gray-400 dark:text-gray-500" data-testid="risk-correlation-empty">{$t('risk.states.empty')}</p>
        {/if}
    </div>
</RiskLevelSection>
