/**
 * periodChanges.ts — The Δ columns of the Assets and FX lists (1D, 1W … 5Y), read from the backend.
 *
 * The backend computes them (`POST /assets/prices/period-changes`, `POST /fx/currencies/period-changes`): each
 * reference day lies a whole number of calendar days before `as_of`, the periods and their order come with the answer,
 * and each change is a fraction written as a decimal string, `null` when a price or a rate is missing. The tables show
 * percentages: this module turns each change into one and keeps no copy of the periods nor of the maths (X-R53).
 *
 * Several requests can be in flight at once (a range change, a refresh, one pair after its sync):
 * `PeriodChangesLedger` says which answer the list keeps, and whether one still to be kept is on its way (X-R60).
 *
 * The same answer carries the Δ over the whole range on screen when the request sends its first day (`range_start`,
 * X-R59): `rangeChange.ts` says which day may be sent and reads the change; it is also the home of `ratioToPercent`.
 *
 * The backend answers at most 1,000 items per request (`MAX_BULK_ITEMS`): a longer list goes in batches, one after the
 * other, and its answers are merged into one (X-R64).
 *
 * @module utils/periodChanges
 */
import {zodiosApi} from '$lib/api';
import {sendBulkBatches} from '$lib/api/bulkBatches';
import {utcMs} from './dateOnly';
import {assetRangeDelta, fxRangeDeltas, rangeStartFor, ratioToPercent, type RangeDelta} from './rangeChange';

export {ratioToPercent};

/** A fixed period as the backend lists it: its key (`1W`) and its length in calendar days. */
export interface PeriodSpec {
    key: string;
    days: number;
}

/** The percent change per period key, `null` where the backend has none. */
export type PeriodDeltas = Record<string, number | null>;

/** The tables' fixed Δ column, which stands outside the period columns. */
const FIXED_PERIOD_KEY = '1D';
const DAY_MS = 86_400_000;

interface PeriodChangeRow {
    key: string;
    days: number;
    // The generated type of a decimal is wider than what the server sends (text or null): it is narrowed below.
    change_ratio?: unknown;
    inverse_change_ratio?: unknown;
}

/** The day number of an ISO date (`YYYY-MM-DD`), counted in UTC so a daylight-saving change never shortens a day; `null` for a day the calendar does not have. */
function isoDayNumber(iso: string): number | null {
    const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso);
    if (!match) return null;
    const [year, month, day] = [Number(match[1]), Number(match[2]), Number(match[3])];
    const time = utcMs(year, month - 1, day);
    const back = new Date(time);
    if (!Number.isFinite(time) || back.getUTCFullYear() !== year || back.getUTCMonth() !== month - 1 || back.getUTCDate() !== day) return null;
    return time / DAY_MS;
}

/**
 * The period columns a range shows: every period but 1D (the tables' fixed column) that fits in the range — its days
 * at most the whole calendar days from `dateStart` to `dateEnd` — in the backend's order; none when the end is before
 * the start or a date cannot be read.
 */
export function visiblePeriodColumns(periods: readonly PeriodSpec[], dateStart: string, dateEnd: string): PeriodSpec[] {
    const start = isoDayNumber(dateStart);
    const end = isoDayNumber(dateEnd);
    if (start === null || end === null || end < start) return [];
    const rangeDays = end - start;
    return periods.filter((period) => period.key !== FIXED_PERIOD_KEY && period.days <= rangeDays);
}

/** The periods of an answer: those of its first item that has any (every item lists the same), as `{key, days}`. */
function periodsOf(items: ReadonlyArray<{periods?: ReadonlyArray<PeriodChangeRow>}>): PeriodSpec[] {
    const first = items.find((item) => (item.periods?.length ?? 0) > 0);
    return (first?.periods ?? []).map(({key, days}) => ({key, days}));
}

function deltasOf(periods: ReadonlyArray<PeriodChangeRow> | undefined, pick: (period: PeriodChangeRow) => unknown): PeriodDeltas {
    return Object.fromEntries(
        (periods ?? []).map((period) => {
            const ratio = pick(period);
            return [period.key, ratioToPercent(typeof ratio === 'string' ? ratio : null)];
        }),
    );
}

/**
 * The answers of `items` sent in batches of at most `BULK_MAX_ITEMS` (`sendBulkBatches`, lot Z-27), in order. A period
 * change asks no per-day work, so only the item cap splits a request. All or nothing (X-R64): a failed batch rejects
 * with its own error and nothing is sent after it, so a list never shows the changes of some items only.
 */
async function inBatches<T, R>(items: readonly T[], send: (batch: T[]) => Promise<R>): Promise<R[]> {
    const outcome = await sendBulkBatches(items, () => 0, send);
    if (outcome.failed) throw outcome.error;
    return outcome.answers.map(({answer}) => answer);
}

/**
 * The Δ of each asset up to `asOf` (the end of the range the list shows), in the asset's own currency: one call for
 * every 1,000 assets, none for an empty list. A failed call rejects. With `rangeStart`, the first day of that range,
 * each asset also gets its Δ over the whole range (`rangeDeltaByAssetId`); a start the backend would refuse is not sent
 * (`rangeStartFor`), and then that map is empty.
 */
export async function fetchAssetPeriodChanges(assetIds: readonly number[], asOf: string, rangeStart: string | null = null): Promise<{periods: PeriodSpec[]; deltasByAssetId: Map<number, PeriodDeltas>; rangeDeltaByAssetId: Map<number, RangeDelta>}> {
    if (assetIds.length === 0) return {periods: [], deltasByAssetId: new Map(), rangeDeltaByAssetId: new Map()};
    const start = rangeStart === null ? null : rangeStartFor(rangeStart, asOf);
    const answers = await inBatches(assetIds, (batch) =>
        zodiosApi.post(
            '/api/v1/assets/prices/period-changes',
            batch.map((assetId) => ({asset_id: assetId, as_of: asOf, ...(start === null ? {} : {range_start: start})})),
        ),
    );
    const items = answers.flatMap((response) => response.items ?? []);
    return {
        periods: periodsOf(items),
        deltasByAssetId: new Map(items.map((item) => [item.asset_id, deltasOf(item.periods, (period) => period.change_ratio)])),
        rangeDeltaByAssetId: start === null ? new Map() : new Map(items.map((item) => [item.asset_id, assetRangeDelta(item.range_change)])),
    };
}

/**
 * The Δ of each pair up to `asOf`, both ways: `direct` for the pair as configured (quote per base), `inverse` for the
 * pair shown inverted. Keyed `BASE/QUOTE`; one call for every 1,000 pairs, none for an empty list. A failed call
 * rejects. With `rangeStart`, each pair also gets its Δ over the whole range, both ways (`rangeDeltasByPair`), as for
 * the assets.
 */
export async function fetchFxPeriodChanges(
    pairs: ReadonlyArray<{base: string; quote: string}>,
    asOf: string,
    rangeStart: string | null = null,
): Promise<{periods: PeriodSpec[]; deltasByPair: Map<string, {direct: PeriodDeltas; inverse: PeriodDeltas}>; rangeDeltasByPair: Map<string, {direct: RangeDelta; inverse: RangeDelta}>}> {
    if (pairs.length === 0) return {periods: [], deltasByPair: new Map(), rangeDeltasByPair: new Map()};
    const start = rangeStart === null ? null : rangeStartFor(rangeStart, asOf);
    const answers = await inBatches(pairs, (batch) =>
        zodiosApi.post(
            '/api/v1/fx/currencies/period-changes',
            batch.map(({base, quote}) => ({base, quote, as_of: asOf, ...(start === null ? {} : {range_start: start})})),
        ),
    );
    const items = answers.flatMap((response) => response.items ?? []);
    return {
        periods: periodsOf(items),
        deltasByPair: new Map(items.map((item) => [`${item.base}/${item.quote}`, {direct: deltasOf(item.periods, (period) => period.change_ratio), inverse: deltasOf(item.periods, (period) => period.inverse_change_ratio)}])),
        rangeDeltasByPair: start === null ? new Map() : new Map(items.map((item) => [`${item.base}/${item.quote}`, fxRangeDeltas(item.range_change)])),
    };
}

/**
 * One request for the Δ columns, as the ledger tracks it: `full` asks every key of the list (a range change, a
 * refresh), otherwise some keys only (a pair after its own sync); `asOf` is the day it asked up to.
 */
export interface PeriodChangesTicket {
    readonly id: number;
    readonly asOf: string;
    readonly full: boolean;
}

/**
 * Which answer of the Δ columns a list keeps while several are in flight (X-R60).
 *
 * - A full request replaces every one before it: an older full answer that lands late is not kept.
 * - A request for some keys, made after a full one, is fresher for its keys than that full answer, whichever lands
 *   first; a full request made after it makes it moot.
 * - `busy` is true while a request whose answer would still be kept is in flight, one-key requests included, so the
 *   list's `data-busy` never reads final before its Δ.
 * - A failed full request keeps the values computed up to the same day and drops the others: they belong to another
 *   range.
 *
 * Plain state, no reactivity: the page copies `busy` into its own `$state` after `begin` and after `end`.
 */
export class PeriodChangesLedger<K> {
    #lastId = 0;
    #latestFull = 0;
    readonly #inFlight = new Set<PeriodChangesTicket>();
    /** The request whose answer each shown key holds: its id and the day it asked up to. */
    readonly #writers = new Map<K, {id: number; asOf: string}>();

    /** A new request up to `asOf`: for every key when `full`, else for some. */
    begin(asOf: string, full: boolean): PeriodChangesTicket {
        const ticket: PeriodChangesTicket = {id: ++this.#lastId, asOf, full};
        if (full) this.#latestFull = ticket.id;
        this.#inFlight.add(ticket);
        return ticket;
    }

    /** The request is over, answered or not: call it in a `finally`. */
    end(ticket: PeriodChangesTicket): void {
        this.#inFlight.delete(ticket);
    }

    /** Whether a request whose answer would still be kept is in flight. */
    get busy(): boolean {
        for (const ticket of this.#inFlight) if (this.#kept(ticket)) return true;
        return false;
    }

    /**
     * The values to show once `ticket` answered `answer`, from those shown now; `null` when the answer is not kept.
     * A full answer replaces every key but those a later one-key answer wrote (a key it lacks goes); a one-key answer
     * sets its keys, unless a later one already did. `shown` is not changed.
     */
    settle<V>(ticket: PeriodChangesTicket, shown: ReadonlyMap<K, V>, answer: ReadonlyMap<K, V>): Map<K, V> | null {
        if (!this.#kept(ticket)) return null;
        const next = ticket.full ? this.#writtenAfter(ticket, shown) : new Map(shown);
        for (const [key, value] of answer) {
            if ((this.#writers.get(key)?.id ?? 0) > ticket.id) continue;
            next.set(key, value);
            this.#writers.set(key, {id: ticket.id, asOf: ticket.asOf});
        }
        this.#forgetAllBut(next);
        return next;
    }

    /**
     * The values to show once the full request `ticket` failed: those computed up to the same day stay, the others
     * go; `null` when nothing is to change — a one-key request, or a full one another has replaced.
     */
    fail<V>(ticket: PeriodChangesTicket, shown: ReadonlyMap<K, V>): Map<K, V> | null {
        if (!ticket.full || !this.#kept(ticket)) return null;
        const next = new Map<K, V>();
        for (const [key, value] of shown) if (this.#writers.get(key)?.asOf === ticket.asOf) next.set(key, value);
        this.#forgetAllBut(next);
        return next;
    }

    #kept(ticket: PeriodChangesTicket): boolean {
        return ticket.full ? ticket.id === this.#latestFull : ticket.id > this.#latestFull;
    }

    /** The shown keys a request made after `ticket` wrote. */
    #writtenAfter<V>(ticket: PeriodChangesTicket, shown: ReadonlyMap<K, V>): Map<K, V> {
        const kept = new Map<K, V>();
        for (const [key, value] of shown) if ((this.#writers.get(key)?.id ?? 0) > ticket.id) kept.set(key, value);
        return kept;
    }

    #forgetAllBut(kept: ReadonlyMap<K, unknown>): void {
        for (const key of [...this.#writers.keys()]) if (!kept.has(key)) this.#writers.delete(key);
    }
}
