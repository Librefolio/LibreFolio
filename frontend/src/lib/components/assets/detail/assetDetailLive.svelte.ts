/**
 * The live updates of the asset detail page (F26, decision 31): one poll of the current price every 30 s while the
 * chart reaches today and the asset has a provider, paused while the tab is hidden or nobody uses the page, resumed
 * by itself (`activePolling`). A poll feeds the price summary (converted when the page shows another currency, with
 * the flash of a tick) and the chart's last point.
 *
 * Moved out of the page with FE5c (piece 9b): the effect and the functions are the page's, with the page's state read
 * through `AssetDetailLiveInput`, an object of getters. The reads were the page's own; Z-8 added the provider code,
 * read through a `$derived` boolean so that the page reloading the assignment does not restart the poller. Create
 * the instance while the page initialises: its constructor registers the polling effect, which the page's
 * destruction tears down.
 *
 * @module components/assets/detail/assetDetailLive
 */

import {zodiosApi} from '$lib/api';
import {startActivePolling, type ActivePollingState} from '$lib/features/live-updates/activePolling';
import {ASSET_DETAIL_LIVE_INTERVAL_MS} from '$lib/features/live-updates/cadence';
import {computeDirection, livePollFailure, livePollOutcome, toLivePriceResult, type LivePriceDirection} from '$lib/services/livePriceService';
import {invalidateAssetPriceStore} from '$lib/stores/assetPriceStoreRegistry';
import {todayIso} from '$lib/utils/dateOnly';
import {assetRangeDelta, rangeStartFor, type RangeDelta} from '$lib/utils/rangeChange';
import {mergeChartPointsIncremental} from './assetDetailChartPoints';

/** How long the flash stays lit before decaying to the resting colour — kept in sync with the CSS animation duration in app.css (.lf-price-flash-*). */
export const LIVE_PRICE_FLASH_DECAY_MS = 1300;

/** What the live updates read from the page: getters over its state; `chartData` also has a setter. */
export interface AssetDetailLiveInput {
    readonly assetInfo: {id: number; currency: string} | null;
    /** The asset of the page's route: an answer for another asset is dropped. */
    readonly pageAssetId: number;
    readonly displayCurrency: string;
    /** The display currency differs from the asset's and its FX pair is not configured. */
    readonly fxConversionMissing: boolean;
    /** The chart's end date is today or later: only then the price is live. */
    readonly isHeadToday: boolean;
    /** `null` while it loads and for a manual asset: without a provider code there is no live poll (Z-8). */
    readonly providerAssignment: {provider_code?: string | null} | null;
    /** The chart is reloading. */
    readonly loading: boolean;
    readonly primaryMode: 'price' | 'calendar-return';
    readonly calendarReturnView: {state: string};
    /** The first day of the range on screen (the page's `dateStart`): the live price's Δ over the range is asked from it (X-R59). Absent: none is asked. */
    readonly rangeStart?: string;
    chartData: any[];
    /** The page's chart load, forced. */
    loadChartData(force: boolean): Promise<void>;
}

export class AssetDetailLive {
    /** Live current price (from provider, only when dateEnd = today). */
    currentPrice = $state<number | null>(null);
    /** True when live price conversion to displayCurrency failed (pair exists but rate unavailable). */
    conversionFailed = $state(false);
    /** The Δ over the range on screen to the live price, as the summary shows it, from the backend (X-R59); null while unknown for the current context. */
    rangeDelta = $state<RangeDelta | null>(null);
    /** State of the live poll, for the page root (`data-live-updates`) and the «Updates paused» pill (F26). */
    updatesState = $state<ActivePollingState>('stopped');
    /** Direction of the latest live-price tick — drives the transient flash animation. Resets to 'neutral' once the flash decays. */
    direction = $state<LivePriceDirection>('neutral');
    /** Increments on every non-neutral tick so the flash element can be re-keyed (forces the CSS animation to restart even for two consecutive same-direction ticks). */
    flashToken = $state(0);
    /** Previous poll's native-currency value — plain (non-reactive) bookkeeping, not rendered. */
    #previousNative: number | null = null;
    /** Pending "decay back to neutral" timer for the current flash. */
    #flashTimeoutId: ReturnType<typeof setTimeout> | null = null;
    #input: AssetDetailLiveInput;

    constructor(input: AssetDetailLiveInput) {
        this.#input = input;
        // Whether there is a provider code, not the assignment itself: the page reloads the assignment after a sync or
        // an edit (a new object, usually the same code), which by itself must not restart the poller. Lazy: read by
        // the effect, never while the instance is built.
        const hasProvider = $derived(!!input.providerAssignment?.provider_code);
        $effect(() => {
            const id = input.assetInfo?.id;
            const nativeCurrency = input.assetInfo?.currency;
            const targetCurrency = input.displayCurrency;
            const fxMissing = input.fxConversionMissing;
            const rangeStart = input.rangeStart;
            // The change belonged to the context that just changed (asset, currency, range): unknown until the next poll.
            this.rangeDelta = null;
            // Without a provider `POST /assets/prices/current` only echoes the stored price, and every answer counts as
            // a portfolio mutation: no poller for a manual asset, nor before the assignment has loaded (Z-8).
            if (!input.isHeadToday || !id || !hasProvider) {
                this.currentPrice = null;
                this.conversionFailed = false;
                // Polling context changed (asset switched, range no longer heads
                // "today", or provider gone) — drop the direction/flash state so it
                // can't carry over and compare against a stale/unrelated previous value.
                this.#previousNative = null;
                this.direction = 'neutral';
                if (this.#flashTimeoutId) {
                    clearTimeout(this.#flashTimeoutId);
                    this.#flashTimeoutId = null;
                }
                this.updatesState = 'stopped';
                return;
            }
            // An answer that lands after this effect re-ran (another currency, another asset) writes nothing.
            let current = true;
            const poller = startActivePolling({
                run: () => this.#pollLivePriceOnce(id, nativeCurrency ?? '', targetCurrency, fxMissing, () => current, rangeStart),
                intervalMs: ASSET_DETAIL_LIVE_INTERVAL_MS,
                onstatechange: (state) => (this.updatesState = state),
            });
            return () => {
                current = false;
                poller.stop();
                if (this.#flashTimeoutId) {
                    clearTimeout(this.#flashTimeoutId);
                    this.#flashTimeoutId = null;
                }
                // The decay timer is gone: put the flash out with it, or it stays lit (coloured, with reduced motion).
                this.direction = 'neutral';
            };
        });
    }

    /** The page reloads everything: no live price, and no Δ to it, until the next poll. */
    resetPrice(): void {
        this.currentPrice = null;
        this.conversionFailed = false;
        this.rangeDelta = null;
    }

    /**
     * One live poll: a single `/assets/prices/current` request feeds the price summary and
     * the chart's last point. It replaced two loops on the same endpoint (every 30 s for the
     * summary, every 60 s with a 5 s warm-up for the chart), which made three writes of
     * today's candle a minute: the endpoint is not read-only, it stores the day's OHLC.
     *
     * With a range start the same request asks the Δ over the range to the quote (X-R59), in the display currency when
     * the summary converts the price.
     */
    async #pollLivePriceOnce(assetId: number, nativeCurrency: string, targetCurrency: string, fxMissing: boolean, isCurrent: () => boolean, rangeStart?: string) {
        const start = rangeStartFor(rangeStart ?? '', todayIso());
        const converting = !!targetCurrency && !!nativeCurrency && targetCurrency !== nativeCurrency && !fxMissing;
        let item: any;
        try {
            const response =
                start === null ? await zodiosApi.get_current_prices_bulk_api_v1_assets_prices_current_post([assetId]) : await zodiosApi.get_current_prices_bulk_api_v1_assets_prices_current_post([assetId], {queries: {range_start: start, ...(converting ? {target_currency: targetCurrency} : {})}});
            item = (response as any)?.results?.[0];
        } catch (error) {
            // Non-blocking: keep the last known value; the poller waits longer before the next try (Z7).
            return livePollFailure(error);
        }
        // A paused provider still answers with the last saved price, shown as usual; the next poll waits for the pause.
        const outcome = livePollOutcome(item ? [toLivePriceResult(item)] : []);
        // Route or currency changed mid-request: drop the result.
        if (!isCurrent() || assetId !== this.#input.pageAssetId) return outcome;
        if (!item || item.value == null) return outcome;
        const nativeValue = Number(item.value);
        if (!Number.isFinite(nativeValue)) return outcome;
        const liveDelta: RangeDelta = start === null ? {abs: null, pct: null} : assetRangeDelta(item.range_change);
        await this.#applyLiveSummary(nativeValue, nativeCurrency, targetCurrency, fxMissing, isCurrent, liveDelta);
        if (isCurrent()) await this.#applyLiveChartHead(item, nativeValue);
        return outcome;
    }

    /** The Δ written with the price: none beside a price left native because its conversion failed (the change is in the display currency). */
    #writeRangeDelta(liveDelta: RangeDelta): void {
        this.rangeDelta = this.conversionFailed ? {abs: null, pct: null} : liveDelta;
    }

    /** The price summary's share of a live poll: the price, converted when the page shows another currency, its Δ over the range, and the flash of a tick. */
    async #applyLiveSummary(nativeValue: number, nativeCurrency: string, targetCurrency: string, fxMissing: boolean, isCurrent: () => boolean, liveDelta: RangeDelta) {
        // Direction compares this tick's NATIVE value to the previous poll's
        // NATIVE value (never the day's open, never the display-converted
        // value) — reuses computeDirection from livePriceService.ts (same
        // helper the assets list page uses) so a displayCurrency switch can
        // never fabricate a false up/down tick. First poll after (re)mount
        // has no previous value → computeDirection returns 'neutral'.
        const direction = computeDirection(nativeValue, this.#previousNative);
        this.#previousNative = nativeValue;
        if (direction !== 'neutral') {
            this.direction = direction;
            this.flashToken++;
            if (this.#flashTimeoutId) clearTimeout(this.#flashTimeoutId);
            this.#flashTimeoutId = setTimeout(() => {
                this.direction = 'neutral';
                this.#flashTimeoutId = null;
            }, LIVE_PRICE_FLASH_DECAY_MS);
        }

        // No conversion needed
        if (!targetCurrency || !nativeCurrency || targetCurrency === nativeCurrency || fxMissing) {
            this.currentPrice = nativeValue;
            this.conversionFailed = false;
            this.#writeRangeDelta(liveDelta);
            return;
        }

        // Convert via FX API
        try {
            // The day of a lookup that fills backward (the latest stored rate on or before it): the UTC date and the
            // user's give the same rate, so it stays UTC (Z-3 changed only what «today» means for the chart's end).
            const today = new Date().toISOString().slice(0, 10);
            const convResponse = await zodiosApi.convert_currency_bulk_api_v1_fx_currencies_convert_post([
                {
                    from_amount: {code: nativeCurrency, amount: String(nativeValue)},
                    to: targetCurrency,
                    date_range: {start: today, end: today},
                },
            ]);
            if (!isCurrent()) return;
            const convResults = (convResponse as any)?.results ?? [];
            if (convResults.length > 0 && convResults[0].to_amount?.amount != null) {
                this.currentPrice = parseFloat(convResults[0].to_amount.amount);
                this.conversionFailed = false;
            } else {
                // Conversion returned no results — fallback to native
                this.currentPrice = nativeValue;
                this.conversionFailed = true;
            }
            this.#writeRangeDelta(liveDelta);
        } catch {
            if (!isCurrent()) return;
            // FX conversion failed — fallback to native price
            this.currentPrice = nativeValue;
            this.conversionFailed = true;
            this.#writeRangeDelta(liveDelta);
        }
    }

    // I-bis #24 — Live chart head (contextual auto-refresh)
    // =========================================================================
    //
    // Why: clicking Sync already does a targeted merge (decision matrix in
    // handleSyncAsset), but the user wants updates to appear *without* any
    // manual click. The live poll above (one request every 30 s) hands its
    // answer here; when the polled close differs from the in-memory chart, today's
    // point is merged in place — zero flicker, signals auto-recompute.
    //
    // IMPORTANT (why we do NOT fall back to a silent ``/sync`` call):
    // the ``/current`` endpoint is NOT read-only — its F.2/F.3 side-effect
    // already persists today's OHLC to the DB. If we chained a silent
    // ``/sync`` after ``/current``, the sync's ``_count_actual_price_changes``
    // would see the DB already up-to-date and return ``changed_points=None``,
    // forcing the FE into the full-reload fallback (flicker) — exactly the
    // UX regression reported during retest. The polled item carries all we
    // need (close + currency + as_of_date) to update today's point.
    //
    // Constraints:
    // • Only with a provider assigned (otherwise the endpoint just echoes back
    //   the DB's last known value — nothing to merge): the effect starts no
    //   poll without a provider code (Z-8), so no answer reaches here then.
    // • Not during a full chart reload (``loading === true``), to avoid
    //   interleaving writers of the same chartData array.
    // • Point merge is idempotent: if the polled close equals the point's
    //   native close (``original_close ?? close``) for the same as_of_date,
    //   we skip the state update (no render, no network).
    // • Converted-currency chart (displayCurrency ≠ asset currency): the
    //   polled close is in the asset's native currency and would flash
    //   wrong values inside the FX-converted series — in that case, when the
    //   native close changed, we do a silent full reload (single
    //   loadChartData) as the fallback.
    // =========================================================================

    async #applyLiveChartHead(item: any, newClose: number) {
        if (this.#input.loading || (this.#input.primaryMode === 'calendar-return' && this.#input.calendarReturnView.state === 'loading')) return;
        if (item.error || !item.as_of_date) return;

        // Idempotent guard: compare with the point for the same date, in the asset's own currency. The poll answers in
        // that currency, while a converted chart's `close` is in the display one: its native close is `original_close`.
        const existingIdx = this.#input.chartData.findIndex((p: any) => p.date === item.as_of_date);
        if (existingIdx >= 0) {
            const existing = this.#input.chartData[existingIdx] as any;
            const existingClose = Number(existing.original_close ?? existing.close);
            if (Number.isFinite(existingClose) && Math.abs(existingClose - newClose) < 1e-9) return;
        }

        // Converted-currency chart: the polled close is in the asset's
        // native currency and would flash wrong numbers mid-series. A
        // single silent full reload is the pragmatic fallback here.
        const isConvertedChart = !!(this.#input.displayCurrency && this.#input.assetInfo?.currency && this.#input.displayCurrency !== this.#input.assetInfo.currency);
        if (isConvertedChart || this.#input.primaryMode === 'calendar-return') {
            invalidateAssetPriceStore(this.#input.pageAssetId);
            await this.#input.loadChartData(true);
            return;
        }

        // Point-level merge: update today's close + currency + as_of_date
        // via mergeChartPointsIncremental. Enriched fields on the existing
        // point (original_close, backward_fill_info, …) are preserved by
        // the shallow-merge rule (the polled item does not carry them,
        // so they are not overwritten). Signal derivatives ($derived
        // from chartData) recompute automatically.
        const polledPoint: any = {
            date: item.as_of_date,
            close: newClose,
            currency: item.currency,
        };
        this.#input.chartData = mergeChartPointsIncremental(this.#input.chartData, [polledPoint]);
    }
}
