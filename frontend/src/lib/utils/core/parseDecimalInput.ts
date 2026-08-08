/**
 * Locale-safe decimal input normalization for text inputs.
 *
 * Canonical app/backend decimal format uses "." as the decimal separator.
 * Browsers can reinterpret <input type="number"> values by locale, so decimal
 * entry fields use type="text" and normalize here instead.
 *
 * Two separators can appear in one string and they do not mean the same thing:
 * in "1.234,56" the dot groups thousands, in "1,234.56" the comma does. Guessing
 * wrong turns a thousand into a unit, so the rule is deliberately narrow — a
 * separator counts as a thousands mark ONLY when the whole string is grouped the
 * way a formatter would group it (three digits per group). Anything else, such
 * as "1.4,1", is a typo: the FIRST separator is the decimal point and the extra
 * ones are dropped while their digits stay, so "1.4,1" reads as 1.41 — the user
 * hit the key twice, they did not mean to throw a digit away.
 */

import {ArrowHold} from './arrowHold';

/** Canonical form: optional sign, digits, at most one dot. */
const CANONICAL = /^-?(?:\d+\.?\d*|\.\d+)$/;

/** e.g. `1.234.567,89` — `group` marks thousands, `decimal` marks the fraction. */
function groupedPattern(group: '.' | ',', decimal: '.' | ','): RegExp {
    return new RegExp(`^-?\\d{1,3}(?:\\${group}\\d{3})+(?:\\${decimal}\\d+)?$`);
}

/**
 * Promotes the first separator to the decimal point and deletes the others,
 * keeping every digit: "1.4,1" is 1.41, not 1.4. A stray separator is a slip of
 * the finger, and dropping the digits behind it would silently change the number.
 */
function firstSeparatorWins(body: string): string {
    const first = body.search(/[.,]/);
    if (first < 0) return body;
    const head = body.slice(0, first);
    const tail = body.slice(first + 1).replace(/[.,]/g, '');
    return `${head}.${tail}`;
}

/**
 * Normalizes a partially- or fully-typed number into the canonical form.
 *
 * Returns the input untouched when it cannot be read as a number at all, so a
 * value still being typed is never destroyed by the field it is typed into.
 */
export function normalizeDecimalInput(value: string): string {
    const trimmed = value.trim();
    if (trimmed === '') return '';

    const sign = trimmed.startsWith('-') ? '-' : '';
    const body = trimmed.slice(sign.length).replace(/[^\d.,]/g, '');
    if (body === '') return trimmed;

    const dots = (body.match(/\./g) ?? []).length;
    const commas = (body.match(/,/g) ?? []).length;

    let candidate: string;
    if (dots > 0 && commas > 0) {
        if (groupedPattern('.', ',').test(sign + body)) candidate = sign + body.replace(/\./g, '').replace(',', '.');
        else if (groupedPattern(',', '.').test(sign + body)) candidate = sign + body.replace(/,/g, '');
        else candidate = sign + firstSeparatorWins(body);
    } else if (dots > 1 || commas > 1) {
        const group = dots > 1 ? '.' : ',';
        const decimal = group === '.' ? ',' : '.';
        if (groupedPattern(group, decimal).test(sign + body)) candidate = sign + body.split(group).join('');
        else candidate = sign + firstSeparatorWins(body);
    } else {
        candidate = sign + body.replace(',', '.');
    }

    return CANONICAL.test(candidate) ? candidate : trimmed;
}

/** Number of digits after the decimal point in a canonical string. */
function decimalPlaces(value: string): number {
    const dot = value.indexOf('.');
    return dot < 0 ? 0 : value.length - dot - 1;
}

/**
 * Adds `delta * step` to a typed decimal, in integer arithmetic.
 *
 * Text inputs lost the arrow keys that `<input type="number">` gave for free, and
 * float addition would hand back 5.800000000000001 for 5.9 - 0.1, so the value is
 * scaled to an integer, stepped, and scaled back at the precision the user is
 * already working at.
 */
export function stepDecimalValue(value: string, delta: number, step = 1): string {
    const normalized = normalizeDecimalInput(value);
    const current = Number(normalized);
    const base = Number.isFinite(current) ? normalized : '0';
    const places = Math.max(decimalPlaces(base), decimalPlaces(String(step)));
    const scale = 10 ** places;
    const scaled = Math.round(Number(base) * scale) + Math.round(delta * step * scale);
    const next = scaled / scale;
    return places === 0 ? String(next) : next.toFixed(places);
}

/**
 * Hold-to-accelerate state. Only one input can hold a key at a time, so a single
 * module-level tracker is enough and every call site keeps its plain signature.
 */
const hold = new ArrowHold();

/** Forgets the current hold, so the next press starts again at the base step. */
export function resetDecimalArrowHold(): void {
    hold.reset();
}

/**
 * Step to apply for this repeat of a held arrow key.
 *
 * The step grows — but only once it can do so without skipping past what the user was
 * aiming at. After a fixed number of repeats the step waits for
 * the value to reach the next round multiple of ten times itself, and escalates
 * exactly there: 1 → 10 at a ten, 10 → 100 at a hundred, and so on in both
 * directions. A value that would jump over the boundary lands on it instead
 * (`snapTo`), so the run stays on a round grid all the way up.
 */
function heldStep(event: KeyboardEvent, current: number, direction: number, step: number): {magnitude: number; snapTo: number | null} {
    if (hold.begin(event, direction)) {
        hold.level = step;
        return {magnitude: step, snapTo: null};
    }
    // The caller's own step is the floor: a field that moves by 0.5 must never be
    // dragged down to a magnitude left over from a field that moved by 1.
    if (hold.level < step) hold.level = step;
    if (!hold.ready) return {magnitude: hold.level, snapTo: null};

    const decade = hold.level * 10;
    const ratio = current / decade;
    if (Math.abs(ratio - Math.round(ratio)) < 1e-9) {
        hold.escalated();
        hold.level = decade;
        return {magnitude: decade, snapTo: null};
    }

    const next = current + direction * hold.level;
    if (Math.floor(next / decade) !== Math.floor(ratio)) {
        hold.escalated();
        hold.level = decade;
        return {magnitude: decade, snapTo: (direction > 0 ? Math.ceil(ratio) : Math.floor(ratio)) * decade};
    }
    return {magnitude: hold.level, snapTo: null};
}

/**
 * Arrow-key stepping for a decimal text input. Returns the new value, or `null`
 * when the key is not an arrow and the event should be left alone.
 *
 * Held down, the step accelerates — see {@link heldStep}. Decimals are
 * left to the keyboard: the acceleration only ever grows the step, never shrinks
 * it below the caller's own.
 */
export function decimalArrowStep(event: KeyboardEvent, value: string, step = 1): string | null {
    if (event.key !== 'ArrowUp' && event.key !== 'ArrowDown') return null;
    if (event.ctrlKey || event.metaKey || event.altKey) return null;
    event.preventDefault();
    const direction = event.key === 'ArrowUp' ? 1 : -1;
    const parsed = Number(normalizeDecimalInput(value));
    const {magnitude, snapTo} = heldStep(event, Number.isFinite(parsed) ? parsed : 0, direction, step);
    return snapTo === null ? stepDecimalValue(value, direction, magnitude) : String(snapTo);
}
