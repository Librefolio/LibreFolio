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
    import {riskMetadata, riskOutput, singleValue} from '$lib/risk/riskTypes';
    import {createRiskPanelController} from '$lib/stores/risk/riskPanelController.svelte';
    import CorrelationHeatmap from './CorrelationHeatmap.svelte';
    import {degradedResults, resultReasons} from './levels/levelHelpers';
    import RiskLevelSection from './levels/RiskLevelSection.svelte';
    import {resultByCode} from './riskAnalysisHelpers';

    interface Props {
        /** Already non-empty: the caller's `{#if}` is the guard, see above. */
        assetIds: number[];
        /** Axis names the page already holds. Missing ids degrade to `#id`. */
        assetLabels: ReadonlyMap<number, string>;
        dateStart: string;
        dateEnd: string;
        targetCurrency: string;
    }

    let {assetIds, assetLabels, dateStart, dateEnd, targetCurrency}: Props = $props();

    const controller = createRiskPanelController(() => ({
        scope: {kind: 'asset_set', asset_ids: assetIds},
        dateStart,
        dateEnd,
        targetCurrency,
        // No risk-free rate reaches a correlation: it is a rate the Sharpe family
        // needs, and passing a live one here would re-ask the question on every
        // keystroke in a control this section does not read.
        appliedRiskFreePercent: 0,
        refreshVersion: 0,
    }));

    let result = $derived(resultByCode(controller.historicalResults, 'correlation'));
    let output = $derived(riskOutput(result, schemas.RiskCorrelationOutput));

    let health = $derived(degradedResults([result]));
    let reasons = $derived(resultReasons([result]));
    let metadata = $derived(riskMetadata(result));

    /**
     * The window the number was measured in, which is half of what the number means.
     *
     * The same pair of assets reads one correlation here and another on the
     * dashboard, because the two pages ask over different spans. Neither is
     * wrong and nothing on screen says so, so the observation count is not
     * decoration: it is the date of the figure above it.
     *
     * ⚠️ Rendered here rather than in `RiskLevelSection` only because that frame
     * has no metadata slot yet. It is written as one liftable block so it can be
     * moved up verbatim the day it gains one — at which point this must be
     * deleted, or the reader will see it twice.
     */
    function percent(value: number | null | undefined): string {
        return value == null ? '—' : `${(value * 100).toFixed(1)}%`;
    }

    function fixed(value: number | readonly (number | null)[] | null | undefined): string {
        const scalar = singleValue(value);
        return scalar == null ? '—' : scalar.toFixed(2);
    }

    /**
     * A key built at runtime is a key that can reach the screen.
     *
     * `return_basis` is a backend enum: a value this frontend has not seen yet
     * produces a missing key, and an unguarded lookup prints `risk.returnBasis.…`
     * to the user. That has already happened once in this codebase, which is why
     * `levelHelpers` refuses runtime keys outright. Here the raw value is a
     * better answer than the key, so it is the fallback.
     */
    function returnBasisLabel(basis: string | null | undefined): string {
        if (!basis) return '—';
        const key = `risk.returnBasis.${basis}`;
        const translated = $t(key);
        return translated === key ? basis : translated;
    }
</script>

<RiskLevelSection title={$t('risk.analytics.correlation.name')} level={2} testId="risk-correlation-section" {health} {reasons}>
    <div data-testid="risk-correlation-content" data-busy={controller.initialLoading ? 'true' : 'false'}>
        <p class="mb-3 text-xs text-gray-500 dark:text-gray-400">{$t('risk.analytics.correlation.description')}</p>

        {#if controller.loadError}
            <p class="py-6 text-center text-sm text-red-600 dark:text-red-400" data-testid="risk-correlation-error">{$t('risk.states.loadFailed')}</p>
        {:else if output}
            <CorrelationHeatmap {output} {assetLabels} />
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

        {#if metadata}
            <details class="mt-3 border-t border-gray-100 pt-2 text-xs text-gray-500 dark:border-slate-700 dark:text-gray-400" data-testid="risk-correlation-section-metadata">
                <summary class="cursor-pointer list-none font-medium">{$t('risk.metadata.title')}</summary>
                <dl class="mt-2 grid grid-cols-2 gap-x-4 gap-y-1 sm:grid-cols-4">
                    <div>
                        <dt>{$t('risk.metadata.observations')}</dt>
                        <dd class="font-mono text-gray-700 dark:text-gray-200" data-testid="risk-correlation-observations">{metadata.n_observations}</dd>
                    </div>
                    <div>
                        <dt>{$t('risk.metadata.coverage')}</dt>
                        <dd class="font-mono text-gray-700 dark:text-gray-200">{percent(metadata.coverage)}</dd>
                    </div>
                    <div>
                        <dt>{$t('risk.metadata.annualization')}</dt>
                        <dd class="font-mono text-gray-700 dark:text-gray-200">{fixed(metadata.annualization_factor)}</dd>
                    </div>
                    <div>
                        <dt>{$t('risk.metadata.returnBasis')}</dt>
                        <dd class="font-mono text-gray-700 dark:text-gray-200">{returnBasisLabel(metadata.return_basis)}</dd>
                    </div>
                    {#if singleValue(metadata.method)}
                        <div class="col-span-2 sm:col-span-4">
                            <dt>{$t('risk.metadata.method')}</dt>
                            <dd class="break-all font-mono text-gray-700 dark:text-gray-200">{singleValue(metadata.method)}</dd>
                        </div>
                    {/if}
                </dl>
            </details>
        {/if}
    </div>
</RiskLevelSection>
