/**
 * What a detail page asks for, in the rolling-return view, to draw a comparison of the OTHER type (lot FB-11): the asset
 * detail an FX pair, the FX pair detail an asset. Each is asked the way that other type is asked on its own page, with the
 * calendar rolling return as the only signal.
 *
 * Pure: no Svelte, no store, no clock.
 *
 * @module charts/crossTypeCalendar
 */

import {CALENDAR_RETURN_INSTANCE_ID, extractCalendarReturnView, type CalendarReturnView} from '$lib/features/signals/calendarReturn';
import {fxCalendarRequest, type FxCalendarRequest, type FxCalendarSignalRequest} from '$lib/utils/reducedFxQuery';

/** An `fx-pair` signal the page compares, the way the signal shows the pair. */
export interface FxPairComparisonTarget {
    configId: string;
    pairSlug: string;
    inverted: boolean;
}

export interface FxPairComparisonInput {
    start: string;
    end: string;
    windowDays: number;
    pairTargets: ReadonlyArray<FxPairComparisonTarget>;
}

export interface FxPairComparisonEntry {
    request: FxCalendarRequest;
    /** The `fx-pair` signal the entry answers. */
    configId: string;
}

/** The conversions that give the rolling return of each compared pair, in the targets' order: 1 unit in the direction its signal shows. */
export function buildFxPairComparisonQuery(input: FxPairComparisonInput): FxPairComparisonEntry[] {
    const dateRange = {start: input.start, end: input.end};
    const entries: FxPairComparisonEntry[] = [];
    for (const target of input.pairTargets) {
        const codes = target.pairSlug.split('-');
        if (codes.length !== 2 || !codes[0] || !codes[1]) continue;
        const [first, second] = codes;
        entries.push({
            request: {from_amount: {code: target.inverted ? second : first, amount: '1'}, to: target.inverted ? first : second, date_range: dateRange, signals: [fxCalendarRequest(input.windowDays)]},
            configId: target.configId,
        });
    }
    return entries;
}

/** The rolling-return view of each compared pair (by `fx-pair` signal id) from an answer of `POST /fx/currencies/convert`; a pair with no answer is absent. */
export function fxPairComparisonViews(answer: unknown, entries: readonly FxPairComparisonEntry[]): Map<string, CalendarReturnView> {
    const views = new Map<string, CalendarReturnView>();
    const groups = answer && typeof answer === 'object' ? (answer as {signal_results?: unknown}).signal_results : null;
    for (const group of Array.isArray(groups) ? groups : []) {
        if (!group || typeof group !== 'object') continue;
        const {request_index: index, signals} = group as {request_index?: unknown; signals?: unknown};
        const entry = typeof index === 'number' ? entries[index] : undefined;
        if (entry) views.set(entry.configId, extractCalendarReturnView(signals, CALENDAR_RETURN_INSTANCE_ID));
    }
    return views;
}

export interface AssetComparisonInput {
    start: string;
    end: string;
    windowDays: number;
    assetIds: readonly number[];
}

export interface AssetComparisonItem {
    asset_id: number;
    date_range: {start: string; end: string};
    include_price: false;
    include_events: false;
    signals: FxCalendarSignalRequest[];
}

/** The items of `POST /assets/prices/query` that give the rolling return of each compared asset, once each, in the asset's own currency. */
export function buildAssetComparisonQuery(input: AssetComparisonInput): AssetComparisonItem[] {
    return [...new Set(input.assetIds)].map((assetId) => ({
        asset_id: assetId,
        date_range: {start: input.start, end: input.end},
        include_price: false as const,
        include_events: false as const,
        signals: [fxCalendarRequest(input.windowDays)],
    }));
}
