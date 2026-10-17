/**
 * periodChanges.ts — The Δ columns of the Assets and FX lists (1D, 1W … 5Y), read from the backend.
 *
 * The backend computes them (`POST /assets/prices/period-changes`, `POST /fx/currencies/period-changes`): each
 * reference day lies a whole number of calendar days before `as_of`, the periods and their order come with the answer,
 * and each change is a fraction written as a decimal string, `null` when a price or a rate is missing. The tables show
 * percentages: this module turns each change into one and keeps no copy of the periods nor of the maths (X-R53).
 *
 * @module utils/periodChanges
 */
import {zodiosApi} from '$lib/api';

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
const PLAIN_DECIMAL = /^([+-]?)(\d+)(?:\.(\d+))?$/;

interface PeriodChangeRow {
    key: string;
    days: number;
    // The generated type of a decimal is wider than what the server sends (text or null): it is narrowed below.
    change_ratio?: unknown;
    inverse_change_ratio?: unknown;
}

/**
 * A backend change (a fraction, as a decimal string) as the percent the tables show; `null` when there is none.
 * The decimal point moves two places in the text itself, so `0.07` reads 7 and not 7.000000000000001.
 */
export function ratioToPercent(ratio: string | null | undefined): number | null {
    if (ratio == null) return null;
    const text = ratio.trim();
    if (text === '') return null;
    const match = PLAIN_DECIMAL.exec(text);
    let value: number;
    if (match) {
        const [, sign, whole, fraction = ''] = match;
        value = Number(`${sign}${whole}${fraction.padEnd(2, '0').slice(0, 2)}.${fraction.slice(2) || '0'}`);
    } else {
        value = Number(text) * 100;
    }
    if (!Number.isFinite(value)) return null;
    return value === 0 ? 0 : value;
}

/** The day number of an ISO date (`YYYY-MM-DD`), counted in UTC so a daylight-saving change never shortens a day; `null` for a day the calendar does not have. */
function isoDayNumber(iso: string): number | null {
    const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso);
    if (!match) return null;
    const [year, month, day] = [Number(match[1]), Number(match[2]), Number(match[3])];
    const time = Date.UTC(year, month - 1, day);
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
 * The Δ of each asset up to `asOf` (the end of the range the list shows), in the asset's own currency: one call for
 * every asset, none for an empty list. A failed call rejects.
 */
export async function fetchAssetPeriodChanges(assetIds: readonly number[], asOf: string): Promise<{periods: PeriodSpec[]; deltasByAssetId: Map<number, PeriodDeltas>}> {
    if (assetIds.length === 0) return {periods: [], deltasByAssetId: new Map()};
    const response = await zodiosApi.post(
        '/api/v1/assets/prices/period-changes',
        assetIds.map((assetId) => ({asset_id: assetId, as_of: asOf})),
    );
    const items = response.items ?? [];
    return {
        periods: periodsOf(items),
        deltasByAssetId: new Map(items.map((item) => [item.asset_id, deltasOf(item.periods, (period) => period.change_ratio)])),
    };
}

/**
 * The Δ of each pair up to `asOf`, both ways: `direct` for the pair as configured (quote per base), `inverse` for the
 * pair shown inverted. Keyed `BASE/QUOTE`; one call for every pair, none for an empty list. A failed call rejects.
 */
export async function fetchFxPeriodChanges(pairs: ReadonlyArray<{base: string; quote: string}>, asOf: string): Promise<{periods: PeriodSpec[]; deltasByPair: Map<string, {direct: PeriodDeltas; inverse: PeriodDeltas}>}> {
    if (pairs.length === 0) return {periods: [], deltasByPair: new Map()};
    const response = await zodiosApi.post(
        '/api/v1/fx/currencies/period-changes',
        pairs.map(({base, quote}) => ({base, quote, as_of: asOf})),
    );
    const items = response.items ?? [];
    return {
        periods: periodsOf(items),
        deltasByPair: new Map(items.map((item) => [`${item.base}/${item.quote}`, {direct: deltasOf(item.periods, (period) => period.change_ratio), inverse: deltasOf(item.periods, (period) => period.inverse_change_ratio)}])),
    };
}
