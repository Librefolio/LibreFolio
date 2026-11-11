/**
 * What the asset detail page asks of the bulk price query, and when two asks are the same one.
 *
 * `loadChartData` of the page builds one `POST /assets/prices/query` body (the asset, the calendar-return
 * signal, the comparison peers) and decides from fingerprints when a change needs new data. These are the
 * parts of that work which read no page state; the page passes in what it read:
 * - the currencies of the request (the one the series is asked in, the one the server converts to);
 * - the calendar-return request and the peers it asks for;
 * - the bulk body;
 * - the price points a held range shows;
 * - the `fx-pair` signals the calendar view compares;
 * - the fingerprints of the calendar data and of the comparison loads.
 *
 * @module features/assets/detail/assetDetailChartRequest
 */

import {comparisonAssetIds} from '$lib/features/signals/chartPageSignals';
import type {SignalConfig} from '$lib/features/signals/ChartSignal';
import {CALENDAR_RETURN_INSTANCE_ID, CALENDAR_RETURN_SIGNAL_CODE} from '$lib/features/signals/calendarReturn';

/** The currency of the series and the one the server must convert to, from the display and the native currency. */
export function chartCurrencies(displayCurrency: string, nativeCurrency: string): {effectiveCurrency: string; targetCurrency: string | undefined} {
    const converts = Boolean(displayCurrency && nativeCurrency && displayCurrency !== nativeCurrency);
    return {
        effectiveCurrency: converts ? displayCurrency : nativeCurrency,
        targetCurrency: converts ? displayCurrency : undefined,
    };
}

/** The signal request that asks the calendar-return rolling window. */
export function calendarReturnRequests(windowDays: number): Array<{instance_id: string; signal_code: string; params: {window_days: number}}> {
    return [{instance_id: CALENDAR_RETURN_INSTANCE_ID, signal_code: CALENDAR_RETURN_SIGNAL_CODE, params: {window_days: windowDays}}];
}

/**
 * The distinct peers of the comparison signals the calendar view asks with the asset.
 *
 * - Only positive ids count, and the page's own asset is left out.
 * - They keep the order of the configs (the response is read back by id).
 */
export function calendarPeerAssetIds(configs: readonly SignalConfig[], assetId: number): number[] {
    return [
        ...new Set(
            configs
                .filter((config) => config.signalType === 'asset-comparison')
                .map((config) => Number(config.params.assetId))
                .filter((peerId) => peerId > 0 && peerId !== assetId),
        ),
    ];
}

/** One item of the bulk body. */
export interface ChartRequestItem {
    asset_id: number;
    date_range: {start: string; end: string};
    include_price: boolean;
    include_events: boolean;
    target_currency?: string;
    signals: Array<{instance_id?: string; signal_code: string; params?: Record<string, unknown>}>;
}

/** What the bulk body is built from. */
export interface ChartRequestInput {
    assetId: number;
    /** «All» is pending and its first day unknown: the range is asked from the sentinel `min`. */
    askedFromMin: boolean;
    dateStart: string;
    dateEnd: string;
    /** False when the held prices answer the range: only the events (and signals) are asked. */
    includePrice: boolean;
    /** The currency the server converts the asset to, if any. */
    targetCurrency: string | undefined;
    /** The currency of the series: the peers are asked in it. */
    effectiveCurrency: string;
    /** The signal requests of the asset item (backend signals, then the calendar-return one). */
    signals: ChartRequestItem['signals'];
    /** The calendar-return request each peer item asks. */
    calendarRequests: ChartRequestItem['signals'];
    peerAssetIds: readonly number[];
}

/**
 * The bulk body: the asset first, then one item per peer.
 *
 * Every item shares the main one's range, so the peer's own first day is the one the server answers when the
 * main item asks from `min`.
 */
export function buildChartRequestBody(input: ChartRequestInput): ChartRequestItem[] {
    const range = {start: input.askedFromMin ? 'min' : input.dateStart, end: input.dateEnd};
    return [
        {
            asset_id: input.assetId,
            date_range: {...range},
            include_price: input.includePrice,
            include_events: true,
            target_currency: input.targetCurrency,
            signals: input.signals,
        },
        ...input.peerAssetIds.map((peerId) => ({
            asset_id: peerId,
            date_range: {...range},
            include_price: false,
            include_events: true,
            target_currency: input.effectiveCurrency || undefined,
            signals: input.calendarRequests,
        })),
    ];
}

/** A price point of a held range, as the price store keeps it. */
export interface HeldPricePoint {
    date: string;
    close: number;
    open?: number | null;
    high?: number | null;
    low?: number | null;
    volume?: number | null;
    currency?: string | null;
    originalClose?: number | null;
    backwardFillInfo?: {daysBack: number} | null;
}

/** The held points as the chart's points (the shape the server answers with). */
export function heldPointsToChartPoints<T extends HeldPricePoint>(held: readonly T[]) {
    return held.map((p) => ({
        date: p.date,
        close: p.close,
        open: p.open,
        high: p.high,
        low: p.low,
        volume: p.volume,
        currency: p.currency,
        original_close: p.originalClose,
        backward_fill_info: p.backwardFillInfo ? {days_back: p.backwardFillInfo.daysBack} : null,
    }));
}

/** The `fx-pair` signals of `configs` as the FX page reads them: the pair, and whether the signal shows it inverted. */
export function fxPairTargetsOf(configs: readonly SignalConfig[]): Array<{configId: string; pairSlug: string; inverted: boolean}> {
    return configs.filter((config) => config.signalType === 'fx-pair' && config.params.pairSlug).map((config) => ({configId: config.id, pairSlug: String(config.params.pairSlug), inverted: Boolean(config.params._inverted)}));
}

/** The peers of the comparison signals, as the calendar view loads them: it changes when a peer is added or removed. */
export function calendarComparisonFingerprint(configs: SignalConfig[], assetId: number): string {
    return JSON.stringify(comparisonAssetIds(configs, assetId));
}

/** What the calendar data depends on: the asset, the period of the URL, the currency, the window and the peers. */
export function calendarDataFingerprint(
    configs: SignalConfig[],
    context: {assetId: number; urlDateStart: string; urlDateEnd: string; displayCurrency: string; nativeCurrency: string; windowDays: number},
): string {
    return JSON.stringify({
        assetId: context.assetId,
        start: context.urlDateStart,
        end: context.urlDateEnd,
        targetCurrency: context.displayCurrency || context.nativeCurrency || '',
        windowDays: context.windowDays,
        peers: comparisonAssetIds(configs, context.assetId),
    });
}

/** What a price-mode comparison load depends on: each peer (and the config that names it), the period and the currency. */
export function priceComparisonLoadFingerprint(configs: SignalConfig[], context: {assetId: number; comparisonStart: string; dateEnd: string; displayCurrency: string}): string {
    return JSON.stringify({
        peers: configs
            .filter((config) => config.signalType === 'asset-comparison')
            .map((config) => ({configId: config.id, assetId: Number(config.params.assetId)}))
            .filter((peer) => Number.isSafeInteger(peer.assetId) && peer.assetId > 0 && peer.assetId !== context.assetId)
            .sort((left, right) => left.configId.localeCompare(right.configId)),
        start: context.comparisonStart,
        end: context.dateEnd,
        targetCurrency: context.displayCurrency || '',
    });
}

/**
 * Whether every peer comparison has been answered by the runtime: its config carries `_conversionFailed` and its
 * events are known (`hasEvents(peerId)`).
 */
export function priceComparisonRuntimeIsAuthoritative(configs: SignalConfig[], assetId: number, hasEvents: (peerId: number) => boolean): boolean {
    return configs
        .filter((config) => config.signalType === 'asset-comparison')
        .filter((config) => {
            const peerId = Number(config.params.assetId);
            return Number.isSafeInteger(peerId) && peerId > 0 && peerId !== assetId;
        })
        .every((config) => Object.hasOwn(config.params, '_conversionFailed') && hasEvents(Number(config.params.assetId)));
}
