/**
 * Free-text date parsing for the date picker's editable trigger.
 *
 * The calendar is precise but slow for a date the user already knows, and slower
 * still for one far from today. Typing must therefore be accepted, and the formats
 * people actually type are not one format: an Italian writes 7/8/2026, an ISO
 * habit writes 2026-08-07, and both use "-", "/" or "." without thinking about it.
 *
 * The year is always required in full. That is the one concession asked of the
 * user, and it is what makes the reading unambiguous: whichever end carries four
 * digits is the year, so 2026-8-7 and 7.8.2026 are read correctly without a
 * locale setting deciding it silently. Day-first is assumed for the ambiguous
 * middle case (7/8/2026), matching how the app displays dates to European users.
 */

/** Splits on the three separators people mix freely, tolerating spaces. */
const PARTS_RE = /^\s*(\d{1,4})\s*[-/.]\s*(\d{1,2})\s*[-/.]\s*(\d{1,4})\s*$/;

/** Already-canonical input, accepted verbatim. */
const ISO_RE = /^\s*(\d{4})-(\d{2})-(\d{2})\s*$/;

function pad(n: number): string {
    return String(n).padStart(2, '0');
}

/** True when the triple is a real calendar date (rejects 2026-02-30). */
function isRealDate(year: number, month: number, day: number): boolean {
    if (month < 1 || month > 12 || day < 1 || day > 31) return false;
    const d = new Date(Date.UTC(year, month - 1, day));
    return d.getUTCFullYear() === year && d.getUTCMonth() === month - 1 && d.getUTCDate() === day;
}

/**
 * Parses a typed date into `YYYY-MM-DD`, or returns `null` when it cannot be read
 * as one date with certainty. Ambiguity is refused, never guessed.
 */
export function parseTypedDate(input: string): string | null {
    if (!input || input.trim() === '') return null;

    const iso = input.match(ISO_RE);
    if (iso) {
        const [, y, m, d] = iso;
        return isRealDate(Number(y), Number(m), Number(d)) ? `${y}-${m}-${d}` : null;
    }

    const parts = input.match(PARTS_RE);
    if (!parts) return null;
    const [, first, middle, last] = parts;

    // Four digits at one end name the year; the other two fields follow from it.
    let year: number;
    let month: number;
    let day: number;
    if (first.length === 4) {
        year = Number(first);
        month = Number(middle);
        day = Number(last);
    } else if (last.length === 4) {
        year = Number(last);
        day = Number(first);
        month = Number(middle);
    } else {
        // No four-digit year: refused rather than assumed (is 07 the year 2007?).
        return null;
    }

    if (!isRealDate(year, month, day)) return null;
    return `${year}-${pad(month)}-${pad(day)}`;
}
