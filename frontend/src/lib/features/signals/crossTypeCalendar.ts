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
import {bulkRangeDays, BULK_SIGNAL_MARGIN_DAYS} from '$lib/api/bulkBatches';
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

/** A card of a list that compares FX pairs in the rolling-return view (the asset list, FB-11 follow-up). */
export interface ListFxPairCard extends FxPairComparisonInput {
    cardKey: string;
}

/** A card's `fx-pair` signal that an entry answers. */
export interface ListFxPairOwner {
    cardKey: string;
    configId: string;
}

export interface ListFxPairEntry {
    request: FxCalendarRequest;
    /** Every card and signal the request answers: cards that compare the same pair the same way over the same window share it. */
    owners: ListFxPairOwner[];
}

/** One list of conversions for the compared pairs of all the cards of a list, identical requests asked once. */
export function buildListFxPairComparisonQuery(cards: readonly ListFxPairCard[]): ListFxPairEntry[] {
    const entries: ListFxPairEntry[] = [];
    const byRequest = new Map<string, ListFxPairEntry>();
    for (const card of cards) {
        for (const {request, configId} of buildFxPairComparisonQuery(card)) {
            const key = JSON.stringify(request);
            const owner = {cardKey: card.cardKey, configId};
            const shared = byRequest.get(key);
            if (shared) {
                shared.owners.push(owner);
                continue;
            }
            const entry = {request, owners: [owner]};
            byRequest.set(key, entry);
            entries.push(entry);
        }
    }
    return entries;
}

/** The days a request weighs for the batch caps, as the other conversions of the FX calendar. */
export function estimateListFxPairDays(entry: ListFxPairEntry, today: string): number {
    return bulkRangeDays(entry.request.date_range.start, entry.request.date_range.end, today) + BULK_SIGNAL_MARGIN_DAYS;
}

/**
 * The rolling-return view of each compared pair, by card and then by signal id, from the answers of the batches
 * (a `request_index` is local to the batch that carried it, so each answer comes with its own entries). A pair with no answer is absent.
 */
export function listFxPairComparisonViews(answers: ReadonlyArray<{entries: readonly ListFxPairEntry[]; answer: unknown}>): Map<string, Map<string, CalendarReturnView>> {
    const byCard = new Map<string, Map<string, CalendarReturnView>>();
    for (const {entries, answer} of answers) {
        const groups = answer && typeof answer === 'object' ? (answer as {signal_results?: unknown}).signal_results : null;
        for (const group of Array.isArray(groups) ? groups : []) {
            if (!group || typeof group !== 'object') continue;
            const {request_index: index, signals} = group as {request_index?: unknown; signals?: unknown};
            const entry = typeof index === 'number' ? entries[index] : undefined;
            if (!entry) continue;
            const view = extractCalendarReturnView(signals, CALENDAR_RETURN_INSTANCE_ID);
            for (const {cardKey, configId} of entry.owners) {
                if (!byCard.has(cardKey)) byCard.set(cardKey, new Map());
                byCard.get(cardKey)!.set(configId, view);
            }
        }
    }
    return byCard;
}
