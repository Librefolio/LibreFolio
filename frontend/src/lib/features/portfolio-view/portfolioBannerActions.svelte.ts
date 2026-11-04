/**
 * The data-quality banner's actions of the portfolio view (Y6-7, delivery 2, checkpoint 9e) — moved whole out of
 * `PortfolioView.svelte`, behaviour kept: «sync rates» on MISSING_FX_RATES and on the old exchange rates, «sync prices» on
 * STALE_PRICE, the chips that lead to an asset or a pair, and the dialog that adds a pair.
 *
 * The dialog has two openers, the banner's «add pair» chip and the currency selector of the toolbar («create forex»), so its
 * state lives here and both call `openFxPairModal`. `syncLoading` is what the view's `aria-busy` reads.
 *
 * Everything the actions need from the view comes in as a getter or a callback (`PortfolioBannerInputs`): the view stays the
 * owner of the report and of the counter that makes the open panels ask again.
 */
import {goto} from '$app/navigation';
import {zodiosApi} from '$lib/api';
import {toasts} from '$lib/stores/app/toastStore.svelte';
import {notify} from '$lib/stores/app/notify.svelte';
import {pageBusy} from '$lib/stores/app/pageBusy.svelte';
import {invalidate} from '$lib/stores/portfolio/portfolioStore.svelte';
import {invalidateFxRoutes} from '$lib/stores/reference/fxRoutesStore';
import {getClientSessionGeneration, isClientSessionCurrent} from '$lib/stores/app/clientSession';
import {buildAssetSyncToast, buildFxSyncToast} from '$lib/utils/sync/syncToastHelpers';
import {buildMissingFxRatesSyncRequest} from '$lib/utils/sync/syncRange';
import {fxPairHtml} from '$lib/utils/providerHelpers';
import {extractErrorMessage} from '$lib/utils/trySave';
import {escapeHtml} from '$lib/utils/core/escapeHtml';
import {classifyFxSyncOutcome, formatFxSyncResult, FX_SYNC_TIMEOUT_MS, type FxPairSyncCompleteDetail, type FxSyncResponse} from '$lib/services/fxCreationSync';
import {pairsStillStale, STALE_FX_ACTION, STALE_FX_CODE, type StaleFxPairLike} from '$lib/features/dashboard/staleFxIssue';
import type {DataQualityIssue} from '$lib/components/ui/feedback/DataQualityBanner.svelte';

export interface PortfolioBannerInputs {
    /** The report's issues now (read again after a sync, once the report is reloaded). */
    issues: () => DataQualityIssue[];
    /** The pairs the report valued from an old stored rate (`data_quality.stale_fx_pairs`). */
    staleFxPairs: () => StaleFxPairLike[] | undefined;
    /** The end of the period on screen: where a price sync stops. */
    periodEnd: () => string;
    alive: () => boolean;
    /** The view's own report load. */
    reload: (force?: boolean, propagateError?: boolean) => Promise<unknown>;
    /** New rates or prices: the open lots and risk panels ask again too, as after «Aggiorna». */
    onDataChanged: () => void;
    translate: (key: string, options?: Record<string, unknown>) => string;
}

export class PortfolioBannerActions {
    /** A sync of the banner is running. */
    syncLoading = $state(false);
    /** The banner row whose button was pressed, for its spinner. */
    syncingCode = $state<string | null>(null);
    fxPairModalOpen = $state(false);
    fxPairSlug = $state('');

    constructor(private readonly inputs: PortfolioBannerInputs) {}

    /** Opens the pair dialog on `slug` (`EUR-USD`, or `EUR-` for a base only). */
    openFxPairModal(slug: string): void {
        this.fxPairSlug = slug;
        this.fxPairModalOpen = true;
    }

    /**
     * «Sync rates» on MISSING_FX_RATES. A date is missing only when no rate exists on or
     * before it, so the missing dates precede the pair's first stored rate and a sync of the
     * period on screen never reaches them: the request targets the dates the issue carries,
     * a week either side, never past today (`buildMissingFxRatesSyncRequest`).
     *
     * The outcome is told once the report is reloaded, because only then is it known whether
     * the dates are covered: when the provider returned nothing for them, the toast says so
     * instead of reporting a success the banner would contradict.
     */
    async syncMissingFxRates(issue: DataQualityIssue): Promise<void> {
        const request = buildMissingFxRatesSyncRequest(issue);
        if (!request) return;
        const {inputs} = this;
        const t = inputs.translate;
        const sessionGeneration = getClientSessionGeneration();
        const current = () => inputs.alive() && isClientSessionCurrent(sessionGeneration);
        const coversRequestedPair = (candidate: DataQualityIssue) => (buildMissingFxRatesSyncRequest(candidate)?.pairs ?? []).some((slug) => request.pairs.includes(slug));
        this.syncLoading = true;
        this.syncingCode = issue.code;
        toasts.info(t('fx.sync.inProgress'));
        try {
            let response: FxSyncResponse | undefined;
            let transportError: string | undefined;
            try {
                response = await zodiosApi.sync_rates_api_v1_fx_currencies_sync_post(request, {timeout: FX_SYNC_TIMEOUT_MS});
            } catch (error) {
                transportError = extractErrorMessage(error, t('prices.sync.failedDefault'));
            }
            if (!current()) return;
            const {requestedResults, operationErrors, outcome, variant: outcomeVariant} = classifyFxSyncOutcome(request.pairs, response, transportError);

            // No reload after a transport error: the backend may still be writing those rates.
            let remaining: DataQualityIssue | undefined;
            let stillMissing: boolean | null = null;
            // «Old exchange rate» (Y6-6): the sync worked and, once the report is read again, the pair is still stale: the provider has no newer rate.
            let stillStale: string[] = [];
            if (!transportError) {
                invalidateFxRoutes();
                invalidate();
                // The open lots and risk panels ask again too, as after «Aggiorna»: new rates change their figures.
                inputs.onDataChanged();
                try {
                    await inputs.reload(true, true);
                    remaining = inputs.issues().find((candidate) => candidate.cta_action === 'sync_fx_pair' && coversRequestedPair(candidate));
                    stillMissing = remaining !== undefined;
                    if (issue.code === STALE_FX_CODE) stillStale = pairsStillStale(request.pairs, inputs.staleFxPairs());
                } catch {
                    stillMissing = null;
                }
                if (!current()) return;
            }

            const pairOptions = {outerFlags: true, linkToDetail: true};
            let variant = outcomeVariant;
            let message = transportError
                ? request.pairs.map((slug) => buildFxSyncToast({status: 'failed', message: escapeHtml(transportError)}, slug, t, undefined, undefined, pairOptions).message).join('\n\n')
                : requestedResults.map((result, index) => formatFxSyncResult(result, request.pairs[index]).message).join('\n\n');
            if (operationErrors.length > 0) message += `\n${operationErrors.map(escapeHtml).join('; ')}`;
            if (remaining && (outcome === 'ok' || outcome === 'partial')) {
                const params = remaining.message_params ?? {};
                const stillMissingPairs = (buildMissingFxRatesSyncRequest(remaining)?.pairs ?? []).filter((slug) => request.pairs.includes(slug));
                message += `\n\n${t('dataQuality.missingFxRatesAfterSync', {
                    values: {
                        pairs: stillMissingPairs.map((slug) => fxPairHtml(slug, pairOptions)).join(', '),
                        date_from: escapeHtml(String(params.date_from ?? '')),
                        date_to: escapeHtml(String(params.date_to ?? '')),
                        dates_count: params.dates_count ?? '',
                    },
                })}`;
                if (variant === 'success') variant = 'warning';
            }
            if (stillStale.length > 0 && (outcome === 'ok' || outcome === 'partial')) {
                message += `\n\n${t('dataQuality.staleFxAfterSync', {values: {pairs: stillStale.map((slug) => fxPairHtml(slug, pairOptions)).join(', ')}})}`;
                if (variant === 'success') variant = 'warning';
            }
            notify({
                name: 'fx.rates.synced',
                detail: {origin: 'dashboard-banner', pairs: request.pairs, start: request.start, end: request.end, outcome, stillMissing, stillStale: stillStale.length > 0},
                toast: {variant, message},
            });
        } finally {
            this.syncLoading = false;
            this.syncingCode = null;
        }
    }

    async handleAction(action: string, target: string | null, issue: DataQualityIssue): Promise<void> {
        if (action === 'navigate_asset' && target) {
            goto(`/assets/${target}`);
        } else if (action === 'navigate_fx' && target) {
            goto(`/fx/${target}`);
        } else if (action === 'add_fx_pair') {
            // The banner has one chip per missing pair: the dialog opens on the pair of the chip pressed.
            this.openFxPairModal(target ?? '');
        } else if (action === 'sync_fx_pair' || action === STALE_FX_ACTION) {
            await this.syncMissingFxRates(issue);
        } else if (action === 'sync_asset_prices') {
            await this.syncStalePrices(issue);
        }
    }

    /**
     * STALE_PRICE: re-sync the flagged provider assets from the day after their last
     * stored price ('resume', the rule every auto-sync uses) up to the period's end
     * date, then reload the report (the banner clears once the prices are fresh).
     */
    private async syncStalePrices(issue: DataQualityIssue): Promise<void> {
        const {inputs} = this;
        const assetIds = issue.affected_asset_ids ?? [];
        if (assetIds.length === 0) return;
        const assetNames = issue.affected_asset_names ?? [];
        this.syncLoading = true;
        this.syncingCode = issue.code;
        try {
            const response = await zodiosApi.sync_prices_bulk_api_v1_assets_prices_sync_post(
                assetIds.map((asset_id) => ({asset_id, date_range: {start: 'resume', end: inputs.periodEnd()}})),
                {timeout: 120 * 1000},
            );
            for (const result of ((response as any)?.results ?? []) as any[]) {
                const name = assetNames[assetIds.indexOf(result?.asset_id)] ?? `#${result?.asset_id}`;
                const toast = buildAssetSyncToast(result, escapeHtml(name), inputs.translate);
                toasts[toast.variant](toast.message);
            }
            invalidate();
            // The open lots and risk panels ask again too, as after «Aggiorna»: new prices change their figures.
            inputs.onDataChanged();
            await inputs.reload(true);
        } catch (e: any) {
            toasts.error(`${inputs.translate('common.sync')} — ${e?.message || inputs.translate('prices.sync.failedDefault')}`);
        } finally {
            this.syncLoading = false;
            this.syncingCode = null;
        }
    }

    /** The pair dialog created a pair: the routes and the report are asked again. */
    async handleFxPairCreated(): Promise<void> {
        if (!this.inputs.alive()) return;
        invalidateFxRoutes();
        invalidate();
        await pageBusy.track('dashboard-reload', () => this.inputs.reload(true));
    }

    async handleFxPairCreationSynced(detail: FxPairSyncCompleteDetail): Promise<void> {
        if (!this.inputs.alive() || !isClientSessionCurrent(detail.sessionGeneration)) return;
        // The sync interceptor marks portfolio/risk caches stale at commit time, when it wrote something.
        await this.inputs.reload(true, true);
    }
}
