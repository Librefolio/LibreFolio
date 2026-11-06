/**
 * horizonExpression — the simulation horizon written as `2y3m5d`, read as days.
 *
 * The backend takes `horizon_days`, calendar days (`simulation` plugin, `1 … 3650`), and stays as it is. The field accepts a plain
 * number of days or an expression of years, months and days, in this order, each part at most once, each unit written in the
 * interface language (IT `a/m/g`, EN `y/m/d`, FR `a/m/j`, ES `a/m/d`: the letters come in as `HorizonUnits`, from the catalogue, so
 * this file knows no language).
 *
 * ⚠️ A FIXED SUM, NOT A CALENDAR (developer's decision, 05/11/2026). A year is 365 days, a month is 30, a day is 1; the parts add up
 * and the total goes to the engine: `2a3m5g` is 730 + 90 + 5 = 825. No date is involved, so the answer never depends on the day it is
 * asked, and a value past its natural range is as good as any: `24m66g` is 720 + 66 = 786. A plain number is days, as the field always
 * was.
 *
 * Not a financial quantity: a count of days written another way, for a control. The one place that does it, shared by the two panels
 * that show the field.
 */

/** Smallest horizon the engine accepts, in calendar days. */
export const HORIZON_MIN_DAYS = 1;
/** Largest horizon the engine accepts (`le=3650` of the simulation parameters), in calendar days. */
export const HORIZON_MAX_DAYS = 3650;

/** The letters of the three units, in the interface language, from the catalogue. */
export interface HorizonUnits {
    year: string;
    month: string;
    day: string;
}

/** What is wrong with the text. `format` is anything that is not days, or years, months, days in order. */
export type HorizonError = 'empty' | 'format' | 'tooShort' | 'tooLong';

export interface HorizonParts {
    years: number;
    months: number;
    days: number;
}

export type HorizonParse = {ok: true; days: number; /** `null` for a plain number of days. */ parts: HorizonParts | null} | {ok: false; error: HorizonError};

/** Anything past this many of a unit is past the maximum whatever the others say; it also keeps the sum an exact integer. */
const OVERFLOW_GUARD = 100_000;

/** What each unit counts for, in days (developer's decision, 05/11/2026). */
export const DAYS_PER_YEAR = 365;
export const DAYS_PER_MONTH = 30;

const UNIT_ORDER = ['year', 'month', 'day'] as const;

function boundsError(days: number): HorizonError | null {
    if (days < HORIZON_MIN_DAYS) return 'tooShort';
    if (days > HORIZON_MAX_DAYS) return 'tooLong';
    return null;
}

/**
 * Read the field's text.
 *
 * - `365` (digits only) is days, as the field always was.
 * - `2y3m5d`, `1y`, `18m`, `24m66d`, `2y 6m`: parts in the interface language's letters, any case, spaces allowed between the
 *   parts; years before months before days; a part at most once.
 * - Anything else is `format`; a result under one day is `tooShort`, over the engine's maximum `tooLong`.
 */
export function parseHorizon(text: string, units: HorizonUnits): HorizonParse {
    const source = text.trim();
    if (source === '') return {ok: false, error: 'empty'};

    if (/^\d+$/.test(source)) {
        const days = Number(source);
        const error = boundsError(days);
        return error ? {ok: false, error} : {ok: true, days, parts: null};
    }

    const letters = new Map<string, (typeof UNIT_ORDER)[number]>();
    for (const unit of UNIT_ORDER) letters.set(units[unit].toLowerCase(), unit);

    const parts: HorizonParts = {years: 0, months: 0, days: 0};
    const token = /(\d+)\s*([^\d\s]+)\s*/y;
    let lastRank = -1;
    let consumed = 0;
    for (let match = token.exec(source); match; match = token.exec(source)) {
        consumed = token.lastIndex;
        const unit = letters.get(match[2].toLowerCase());
        const rank = unit ? UNIT_ORDER.indexOf(unit) : -1;
        // Unknown letter, a repeated unit, or a unit out of order.
        if (!unit || rank <= lastRank) return {ok: false, error: 'format'};
        lastRank = rank;
        const amount = Number(match[1]);
        if (amount > OVERFLOW_GUARD) return {ok: false, error: 'tooLong'};
        if (unit === 'year') parts.years = amount;
        else if (unit === 'month') parts.months = amount;
        else parts.days = amount;
    }
    if (consumed !== source.length || lastRank < 0) return {ok: false, error: 'format'};

    const days = parts.years * DAYS_PER_YEAR + parts.months * DAYS_PER_MONTH + parts.days;
    const error = boundsError(days);
    return error ? {ok: false, error} : {ok: true, days, parts};
}
