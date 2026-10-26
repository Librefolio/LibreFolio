/**
 * rangeChange.ts — The Δ over the range a page shows, read from the backend (X-R59, decision N80).
 *
 * The backend computes the change from the first to the last point of the range on screen: the `range_change` of
 * `POST /assets/prices/period-changes` and `POST /fx/currencies/period-changes` for an item that sends a `range_start`
 * (and of `POST /assets/prices/current?range_start=…` for a live quote). This module says which `range_start` a request
 * may send and reads the answer as the pages show it; it keeps no copy of the maths. Also the home of `ratioToPercent`,
 * the reading of a backend change as a percent, shared with the fixed-period Δ columns (`periodChanges.ts`).
 *
 * Pure: no Svelte, no API client.
 *
 * @module utils/rangeChange
 */

import {utcMs} from './dateOnly';

/** A change over the range as a page shows it: absolute (in the price's or the rate's unit) and percent; null where the backend has none. */
export interface RangeDelta {
    abs: number | null;
    pct: number | null;
}

const ISO_DAY = /^(\d{4})-(\d{2})-(\d{2})$/;
const PLAIN_DECIMAL = /^([+-]?)(\d+)(?:\.(\d+))?$/;
const DECIMAL = /^[+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?$/;

/**
 * A backend change (a fraction, as a decimal string) as the percent the pages show; `null` when there is none.
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

/** True for a bare `YYYY-MM-DD` the calendar has, from the year 1 (the backend's first): a UTC round trip, so a daylight-saving change never matters. */
function isCalendarDay(iso: string): boolean {
    const match = ISO_DAY.exec(iso);
    if (!match) return false;
    const [year, month, day] = [Number(match[1]), Number(match[2]), Number(match[3])];
    if (year < 1) return false;
    const back = new Date(utcMs(year, month - 1, day));
    return back.getUTCFullYear() === year && back.getUTCMonth() === month - 1 && back.getUTCDate() === day;
}

/**
 * The `range_start` a request sends for the range `dateStart … asOf`: its first day, as it is (the backend takes any day
 * from the year 1; D-P4). Null — send none — when either is not a day the calendar has, or when the start falls after
 * `asOf`: the backend would refuse the whole request, every Δ column with it.
 */
export function rangeStartFor(dateStart: string, asOf: string): string | null {
    if (!isCalendarDay(dateStart) || !isCalendarDay(asOf)) return null;
    return dateStart > asOf ? null : dateStart;
}

/** A decimal string as a number (plain or with an exponent); anything else, a non-string included, is none. Never −0. */
function decimalToNumber(value: unknown): number | null {
    if (typeof value !== 'string') return null;
    const text = value.trim();
    if (!DECIMAL.test(text)) return null;
    const number = Number(text);
    if (!Number.isFinite(number)) return null;
    return number === 0 ? 0 : number;
}

/** One orientation of a change: only strings are read, since the generated type of a decimal is wider than what the server sends. */
function deltaOf(abs: unknown, ratio: unknown): RangeDelta {
    return {abs: decimalToNumber(abs), pct: typeof ratio === 'string' ? ratioToPercent(ratio) : null};
}

/** The fields of a `range_change`, or null for anything that is not a plain object. */
function fieldsOf(raw: unknown): Record<string, unknown> | null {
    return raw !== null && typeof raw === 'object' && !Array.isArray(raw) ? (raw as Record<string, unknown>) : null;
}

/** An asset's `range_change` (`{reference_date, change_abs, change_ratio}`) as the page shows it; no change for a missing one. */
export function assetRangeDelta(raw: unknown): RangeDelta {
    const fields = fieldsOf(raw);
    return fields ? deltaOf(fields.change_abs, fields.change_ratio) : {abs: null, pct: null};
}

/**
 * A pair's `range_change` both ways, each from its own fields: `direct` (quote per base) from `change_abs` and
 * `change_ratio`, `inverse` (the pair shown inverted) from `inverse_change_abs` and `inverse_change_ratio`.
 */
export function fxRangeDeltas(raw: unknown): {direct: RangeDelta; inverse: RangeDelta} {
    const fields = fieldsOf(raw);
    if (!fields) return {direct: {abs: null, pct: null}, inverse: {abs: null, pct: null}};
    return {direct: deltaOf(fields.change_abs, fields.change_ratio), inverse: deltaOf(fields.inverse_change_abs, fields.inverse_change_ratio)};
}
