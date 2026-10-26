/**
 * What the FX pair detail asks `POST /fx/currencies/convert` for in the rolling-return mode (lot X5-F1), and how it reads the answer.
 *
 * The detail asks the pair's own return, and one for every FX pair its `fx-pair` signals compare, each as a conversion of
 * 1 unit in the direction the page shows it, with the calendar rolling return as its only signal. Unlike the list's cards
 * (`utils/reducedFxQuery.ts`, a sample as wide as a small plot) it asks the daily return: no `key`, no `max_points`, no
 * `sample_like`, as the detail's other signal requests do.
 *
 * Pure: no Svelte, no store, no clock.
 *
 * @module charts/fxDetailCalendar
 */

import {CALENDAR_RETURN_INSTANCE_ID, emptyCalendarReturnView, extractCalendarReturnView, type CalendarReturnView} from '$lib/components/charts/priceChartHelpers';
import {fxCalendarRequest, type FxCalendarRequest} from '$lib/utils/reducedFxQuery';

export interface FxDetailCalendarInput {
    /** The page's pair, canonical (`EUR-USD`): a compared pair equal to it is the page's own and is not asked twice. */
    ownSlug: string;
    /** The pair as the page shows it (the URL's orientation). */
    base: string;
    quote: string;
    start: string;
    end: string;
    windowDays: number;
    /** The FX pairs the page's `fx-pair` signals compare, each the way its signal shows it. */
    pairTargets: ReadonlyArray<{configId: string; pairSlug: string; inverted: boolean}>;
}

export interface FxDetailCalendarEntry {
    request: FxCalendarRequest;
    /** The `fx-pair` signal the entry answers; null for the page's own pair. */
    configId: string | null;
}

/** The conversions of the request, in order: the page's pair, then its compared pairs. */
export function buildFxDetailCalendarQuery(input: FxDetailCalendarInput): FxDetailCalendarEntry[] {
    const dateRange = {start: input.start, end: input.end};
    const signals = () => [fxCalendarRequest(input.windowDays)];
    const entries: FxDetailCalendarEntry[] = [{request: {from_amount: {code: input.base, amount: '1'}, to: input.quote, date_range: dateRange, signals: signals()}, configId: null}];
    for (const target of input.pairTargets) {
        const codes = target.pairSlug.split('-');
        if (codes.length !== 2 || !codes[0] || !codes[1] || target.pairSlug === input.ownSlug) continue;
        const [first, second] = codes;
        entries.push({
            request: {from_amount: {code: target.inverted ? second : first, amount: '1'}, to: target.inverted ? first : second, date_range: dateRange, signals: signals()},
            configId: target.configId,
        });
    }
    return entries;
}

/** The page's rolling return and its compared pairs' (by `fx-pair` signal id), from an answer of `buildFxDetailCalendarQuery`'s request. */
export function fxDetailCalendarViews(answer: unknown, entries: readonly FxDetailCalendarEntry[]): {own: CalendarReturnView; targets: Map<string, CalendarReturnView>} {
    let own: CalendarReturnView | null = null;
    const targets = new Map<string, CalendarReturnView>();
    const groups = answer && typeof answer === 'object' ? (answer as {signal_results?: unknown}).signal_results : null;
    for (const group of Array.isArray(groups) ? groups : []) {
        if (!group || typeof group !== 'object') continue;
        const {request_index: index, signals} = group as {request_index?: unknown; signals?: unknown};
        const entry = typeof index === 'number' ? entries[index] : undefined;
        if (!entry) continue;
        const view = extractCalendarReturnView(signals, CALENDAR_RETURN_INSTANCE_ID);
        if (entry.configId === null) own = view;
        else targets.set(entry.configId, view);
    }
    return {own: own ?? emptyCalendarReturnView('error'), targets};
}
