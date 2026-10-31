/**
 * The first date of an asset's or an FX pair's series, remembered for the session (FB-7b).
 *
 * «All» on a detail or list page asks a series from the sentinel `min` (the server resolves it to the series' first stored day)
 * and adopts the first date the answer holds. Remembered here, the next visit with «All» starts from that real day, and so from
 * the series store, instead of asking the whole history again. A series seen from an earlier date replaces the date held; a later
 * one does not (a range that began after the first day tells nothing about it).
 *
 * It is a fact about the server's data, so whatever changes the data forgets it: a prices catch-up, a sync, a save and a refresh
 * (the pages call `forgetFirstDate` where they re-arm «All»), and a change of user.
 *
 * @module stores/firstSeriesDates
 */

import {registerClientSessionReset} from './app/clientSession';
import {registerPortfolioMutationListener} from './portfolio/portfolioMutation';

export type SeriesKind = 'asset' | 'fx';

/** The first day of a series, or `null` for a series that answered with no point at all (an asset with no price, a pair with no rate). */
const firstDates = new Map<string, string | null>();

function keyOf(kind: SeriesKind, id: number | string): string {
    return `${kind}:${id}`;
}

/** Remember `date` (YYYY-MM-DD) as a day the series has a point on; the earliest one seen is kept. */
export function rememberFirstDate(kind: SeriesKind, id: number | string, date: string): void {
    const key = keyOf(kind, id);
    const held = firstDates.get(key);
    if (held === undefined || held === null || date < held) firstDates.set(key, date);
}

/**
 * Remember that the series answered with no point: a list that asks all its series at once knows then that nothing is left to find
 * out about it, and starts the next «All» from the others' first days. A date remembered for the series is kept.
 */
export function rememberNoSeries(kind: SeriesKind, id: number | string): void {
    const key = keyOf(kind, id);
    if (!firstDates.has(key)) firstDates.set(key, null);
}

/** The earliest date remembered for the series, or `undefined` (nothing remembered, or the series has no point). */
export function firstDateOf(kind: SeriesKind, id: number | string): string | undefined {
    return firstDates.get(keyOf(kind, id)) ?? undefined;
}

/** Whether the series was seen this session: it has a first day, or it is known to have no point. */
export function isFirstDateKnown(kind: SeriesKind, id: number | string): boolean {
    return firstDates.has(keyOf(kind, id));
}

export function forgetFirstDate(kind: SeriesKind, id: number | string): void {
    firstDates.delete(keyOf(kind, id));
}

export function forgetAllFirstDates(): void {
    firstDates.clear();
}

// A catch-up may have filled or corrected any series; a change of user drops everything a session held
registerPortfolioMutationListener('firstSeriesDates', (signal) => {
    if (signal.kind === 'prices') forgetAllFirstDates();
});
registerClientSessionReset('firstSeriesDates', forgetAllFirstDates);
