import {ArrowHold} from './arrowHold';

/**
 * Arrow-key stepping for a date field, with hold-to-accelerate.
 *
 * A date has no single "step": one press should move a day, but reaching a date two
 * decades back a day at a time is not something anyone will do. So the held key climbs
 * the units the calendar is actually made of — day → month → year — and, once whole
 * years are still too slow, keeps going by tens and hundreds of years.
 */

/** Rungs of the ladder, in order. `years` counts how many years one press moves. */
const LADDER: Array<{unit: 'day' | 'month' | 'year'; amount: number}> = [
    {unit: 'day', amount: 1},
    {unit: 'month', amount: 1},
    {unit: 'year', amount: 1},
    {unit: 'year', amount: 10},
    {unit: 'year', amount: 100},
];

const hold = new ArrowHold();

/**
 * Day of the month the run left the "day" rung on.
 *
 * Clamping is lossy: a run that walks month by month over February would come out the
 * other side stuck on the 28th, having silently thrown away the 30th it started from.
 * Remembering the day the run was on restores it as soon as the month is long enough.
 */
let anchorDay = 0;

/** Forgets the current hold, so the next press starts again at one day. */
export function resetDateArrowHold(): void {
    hold.reset();
    anchorDay = 0;
}

function toParts(iso: string): {year: number; month: number; day: number} | null {
    const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso);
    if (!match) return null;
    return {year: Number(match[1]), month: Number(match[2]), day: Number(match[3])};
}

function toIso(year: number, month: number, day: number): string {
    return `${String(year).padStart(4, '0')}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
}

function daysInMonth(year: number, month: number): number {
    return new Date(Date.UTC(year, month, 0)).getUTCDate();
}

/**
 * Moves an ISO date by whole days, months or years.
 *
 * Months and years are moved on the calendar, not on a timestamp: 31 January plus a
 * month is the end of February, not the 2nd or 3rd of March, because the user pressing
 * "up" on a month is thinking in months. The day is therefore clamped to the target
 * month's length.
 */
export function shiftIsoDate(iso: string, unit: 'day' | 'month' | 'year', amount: number): string {
    const parts = toParts(iso);
    if (!parts) return iso;
    if (unit === 'day') {
        const shifted = new Date(Date.UTC(parts.year, parts.month - 1, parts.day + amount));
        return toIso(shifted.getUTCFullYear(), shifted.getUTCMonth() + 1, shifted.getUTCDate());
    }
    const monthIndex = parts.month - 1 + (unit === 'month' ? amount : 0);
    const year = parts.year + (unit === 'year' ? amount : 0) + Math.floor(monthIndex / 12);
    const month = (((monthIndex % 12) + 12) % 12) + 1;
    return toIso(year, month, Math.min(parts.day, daysInMonth(year, month)));
}

/**
 * Next value for this repeat of a held arrow key on a date field, or `null` when the
 * key is not an arrow and the event should be left alone.
 *
 * `fallbackIso` is what an empty or unreadable field steps from — usually today, so
 * the arrows are also a way to fill a blank field without opening the calendar.
 */
export function dateArrowStep(event: KeyboardEvent, iso: string | null, fallbackIso: string): string | null {
    if (event.key !== 'ArrowUp' && event.key !== 'ArrowDown') return null;
    if (event.ctrlKey || event.metaKey || event.altKey) return null;
    event.preventDefault();

    const direction = event.key === 'ArrowUp' ? 1 : -1;
    const base = iso && toParts(iso) ? iso : fallbackIso;

    if (hold.begin(event, direction)) {
        hold.level = 0;
        anchorDay = 0;
    } else if (hold.ready && hold.level < LADDER.length - 1) {
        if (hold.level === 0) anchorDay = toParts(base)?.day ?? 0;
        hold.level += 1;
        hold.escalated();
    }

    const rung = LADDER[hold.level];
    const shifted = shiftIsoDate(base, rung.unit, direction * rung.amount);
    if (rung.unit === 'day' || anchorDay === 0) return shifted;

    const parts = toParts(shifted);
    if (!parts) return shifted;
    return toIso(parts.year, parts.month, Math.min(anchorDay, daysInMonth(parts.year, parts.month)));
}
