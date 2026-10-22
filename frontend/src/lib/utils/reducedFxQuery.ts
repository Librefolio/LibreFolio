/**
 * What the FX list asks `POST /fx/currencies/convert` for the cards in the rolling-return view (lot Y-40, the FX half), on
 * the backend's sampled conversions (Z-29fx).
 *
 * A card asks one conversion of 1 unit in the direction it shows the pair, with the calendar rolling return as its signal,
 * named `fx:<slug>` and with the `max_points` its plot takes: the backend computes the return every day and reduces it to
 * the card's buckets. Each FX pair compared on the card asks its own return `sample_like` the card, in the direction its
 * signal shows the pair. The members of a card share a group: `bulkBatches.ts` never cuts between them.
 *
 * The rates of these conversions are not the cards' daily rates: the page reads only their signals, and never puts them in
 * the FX stores.
 *
 * Pure: no Svelte, no store, no clock (`today` is an argument).
 *
 * @module utils/reducedFxQuery
 */

import {BULK_SIGNAL_MARGIN_DAYS, bulkRangeDays} from '$lib/api/bulkBatches';
import {CALENDAR_RETURN_INSTANCE_ID, CALENDAR_RETURN_SIGNAL_CODE} from '$lib/components/charts/priceChartHelpers';
import {compactMaxPoints} from '$lib/components/charts/timeSeriesAggregation';

/** The rolling return a card asks, under the detail's instance id. */
export interface FxCalendarSignalRequest {
    instance_id: string;
    signal_code: string;
    params: {window_days: number};
}

/** A conversion of the request, as the backend takes it (`FXConversionRequest`). */
export interface FxCalendarRequest {
    from_amount: {code: string; amount: string};
    to: string;
    date_range: {start: string; end: string};
    signals: FxCalendarSignalRequest[];
    /** On a card's conversion: its name, which its compared pairs give in `sample_like`. */
    key?: string;
    /** On a card's conversion: the most points its plot takes. */
    max_points?: number;
    /** On a compared pair's conversion: the key of the card it is sampled like. */
    sample_like?: string;
}

/** A conversion with what the page needs to put its answer back: whose it is. */
export interface FxCalendarEntry {
    request: FxCalendarRequest;
    /** The card's key: the members of one card share it. */
    group: string;
    role: 'card' | 'target';
    /** The pair of the card the entry belongs to. */
    cardSlug: string;
    /** On a compared pair's entry: the id of its `fx-pair` signal; null on a card's own entry. */
    configId: string | null;
}

/** What one card in the rolling-return view needs of the request. */
export interface FxCalendarCardInput {
    slug: string;
    base: string;
    quote: string;
    /** The card shows the pair swapped: its return is the swapped rate's. */
    inverted: boolean;
    /** The card's measured plot width, in pixels. */
    plotWidthPx: number;
    start: string;
    end: string;
    windowDays: number;
    /** The FX pairs its `fx-pair` signals compare, each the way its signal shows it. */
    pairTargets: ReadonlyArray<{configId: string; pairSlug: string; inverted: boolean}>;
}

/** The calendar rolling return over `windowDays`. */
export function fxCalendarRequest(windowDays: number): FxCalendarSignalRequest {
    return {instance_id: CALENDAR_RETURN_INSTANCE_ID, signal_code: CALENDAR_RETURN_SIGNAL_CODE, params: {window_days: windowDays}};
}

/** The key a card's conversion is named by. */
export function fxCardKey(slug: string): string {
    return `fx:${slug}`;
}

/** The conversions of the request for `cards`: a card's, then its compared pairs', in the cards' order. */
export function buildFxCalendarQuery(cards: readonly FxCalendarCardInput[]): FxCalendarEntry[] {
    const entries: FxCalendarEntry[] = [];
    for (const card of cards) {
        const key = fxCardKey(card.slug);
        const dateRange = {start: card.start, end: card.end};
        const signals = [fxCalendarRequest(card.windowDays)];
        entries.push({
            request: {from_amount: {code: card.inverted ? card.quote : card.base, amount: '1'}, to: card.inverted ? card.base : card.quote, date_range: dateRange, signals, key, max_points: compactMaxPoints(card.plotWidthPx)},
            group: key,
            role: 'card',
            cardSlug: card.slug,
            configId: null,
        });
        for (const target of card.pairTargets) {
            const [first, second] = target.pairSlug.split('-');
            if (!first || !second || target.pairSlug === card.slug) continue;
            entries.push({
                request: {from_amount: {code: target.inverted ? second : first, amount: '1'}, to: target.inverted ? first : second, date_range: dateRange, signals, sample_like: key},
                group: key,
                role: 'target',
                cardSlug: card.slug,
                configId: target.configId,
            });
        }
    }
    return entries;
}

/** The days a conversion is guessed to cost the backend's day budget: its range, plus the signals' margin. */
export function estimateFxCalendarDays(entry: FxCalendarEntry, today: string): number {
    return bulkRangeDays(entry.request.date_range.start, entry.request.date_range.end, today) + BULK_SIGNAL_MARGIN_DAYS;
}
