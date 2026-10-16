/**
 * resolveProviderError — pure unit tests (Vitest, node env).
 *
 * The resolver maps a failed probe's `error_code` + `error_details` to a
 * `providerErrors.*` i18n key and falls back to the raw English `error` text
 * when the code is unknown — never hiding what the backend sent (I3).
 *
 * The `t` double mimics the one svelte-i18n store contract the resolver relies
 * on: an unknown key returns the key itself. The dictionary below is the
 * test's own — these tests pin *key selection and fallback order*, not the
 * English copy. A separate describe checks the keys the resolver is designed
 * to emit actually exist in the shipped catalogue.
 *
 * X8 (RATE_LIMITED): a stub `t` that answers «key → {time}» shows which of
 * RATE_LIMITED (a pause ending today), RATE_LIMITED_DAY (another day) and
 * RATE_LIMITED_NO_TIME was chosen and what time it was given, never a text.
 * «Now» is a fake clock (Date only); the resume moment is checked against Intl
 * oracles, in a month with no daylight-saving change, with the locale passed.
 */
import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';
import {formatResumeTime, resolveProviderError, resumesToday, type ProviderErrorLike} from './resolveProviderError';
import {formatDateTime} from '$lib/utils/core/formatDateTime';
import en from '$lib/i18n/en.json';
import es from '$lib/i18n/es.json';
import fr from '$lib/i18n/fr.json';
import it_ from '$lib/i18n/it.json';

const DICT: Record<string, string> = {
    'providerErrors.NO_DATA': 'generic no-data',
    'providerErrors.NO_DATA_STALE': 'stale as of {nav_date}',
    'providerErrors.TIMEOUT': 'generic timeout',
};

/** svelte-i18n-shaped `t`: known key → template with {placeholders} filled; unknown → the key. */
function fakeT(key: string, opts?: {values?: Record<string, string | number | boolean | Date | null | undefined>}): string {
    let msg = DICT[key] ?? key;
    for (const [k, v] of Object.entries(opts?.values ?? {})) msg = msg.replaceAll(`{${k}}`, String(v));
    return msg;
}

const op = (over: Partial<ProviderErrorLike>): ProviderErrorLike => ({error: 'raw English message', ...over});

/** The three keys of a «too many requests» refusal (X8). */
const RATE_LIMITED_KEYS = ['RATE_LIMITED', 'RATE_LIMITED_DAY', 'RATE_LIMITED_NO_TIME'];

describe('resolveProviderError — code mapping', () => {
    it('NO_DATA with a nav_date resolves to the stale-NAV variant, with the date interpolated', () => {
        const out = resolveProviderError(op({error_code: 'NO_DATA', error_details: {nav_date: '2026-08-20'}}), fakeT);
        expect(out).toBe('stale as of 2026-08-20');
    });

    it('NO_DATA without a nav_date resolves to the generic NO_DATA message', () => {
        expect(resolveProviderError(op({error_code: 'NO_DATA'}), fakeT)).toBe('generic no-data');
        expect(resolveProviderError(op({error_code: 'NO_DATA', error_details: {}}), fakeT)).toBe('generic no-data');
    });

    it('NO_DATA with a nav_date falls through to generic NO_DATA when the stale key is missing from the catalogue', () => {
        const t = (key: string) => (key === 'providerErrors.NO_DATA' ? DICT[key] : key);
        expect(resolveProviderError(op({error_code: 'NO_DATA', error_details: {nav_date: '2026-08-20'}}), t)).toBe('generic no-data');
    });

    it('matches codes case-insensitively', () => {
        expect(resolveProviderError(op({error_code: 'timeout'}), fakeT)).toBe('generic timeout');
    });

    it('an unmapped code falls back to the raw backend message', () => {
        expect(resolveProviderError(op({error_code: 'SOME_NEW_BACKEND_CODE'}), fakeT)).toBe('raw English message');
    });

    it('no code at all falls back to the raw backend message', () => {
        expect(resolveProviderError(op({}), fakeT)).toBe('raw English message');
    });

    it('with neither code nor message there is still a non-empty answer', () => {
        expect(resolveProviderError({}, fakeT)).toBe('Unknown error');
    });

    it('non-primitive detail values are stringified for interpolation', () => {
        // The wire is JSON, but the backend `details` dict can carry dates —
        // serialized before sending (see _json_safe_details). The resolver must
        // not choke on whatever survives.
        const out = resolveProviderError(op({error_code: 'NO_DATA', error_details: {nav_date: 20260820}}), fakeT);
        expect(out).toBe('stale as of 20260820');
    });
});

describe('resolveProviderError — shipped catalogue', () => {
    it('the keys the resolver is designed to emit exist in en.json', () => {
        const providerErrors = (en as Record<string, unknown>).providerErrors as Record<string, unknown>;
        // The mapped surface (I3 scope): the codes a user meets on "Test
        // Configuration". A missing key silently degrades to raw English, so
        // existence is the contract worth pinning.
        for (const key of ['NO_DATA', 'NO_DATA_STALE', 'NOT_FOUND', 'FETCH_ERROR', 'NOT_IMPLEMENTED', 'TIMEOUT', 'MISSING_PARAMS', 'PARSE_ERROR', 'SCRAPE_ERROR', ...RATE_LIMITED_KEYS]) {
            expect(providerErrors, `providerErrors.${key} missing from en.json`).toHaveProperty(key);
        }
    });

    it('the three RATE_LIMITED keys exist in the four catalogues, the two timed ones with their {time}', () => {
        // A translation without {time} would drop the moment the pause ends: the placeholder is the contract, not the wording.
        for (const [lang, catalogue] of Object.entries({en, it: it_, fr, es})) {
            const providerErrors = (catalogue as Record<string, unknown>).providerErrors as Record<string, string>;
            for (const key of RATE_LIMITED_KEYS) expect(providerErrors, `providerErrors.${key} missing from ${lang}.json`).toHaveProperty(key);
            for (const key of ['RATE_LIMITED', 'RATE_LIMITED_DAY']) expect(providerErrors[key], `${lang}: providerErrors.${key}`).toContain('{time}');
        }
    });
});

// ─────────────────────────────────────────────────────────────────────────────
// X8 — RATE_LIMITED: «paused until …», the resume moment in local time
// ─────────────────────────────────────────────────────────────────────────────

const TODAY_KEY = 'providerErrors.RATE_LIMITED';
const DAY_KEY = 'providerErrors.RATE_LIMITED_DAY';
const NO_TIME_KEY = 'providerErrors.RATE_LIMITED_NO_TIME';

/** A local moment of June 2026 — a month with no daylight-saving change, so «today» is a plain calendar day. */
const at = (day: number, hours: number, minutes: number, seconds = 0) => new Date(2026, 5, day, hours, minutes, seconds);
/** «Now» for the resolver: 10 June 2026, 14:30:20 local time. */
const NOW = at(10, 14, 30, 20);

/** The house oracle for a time alone, as Intl writes it in `locale` — never a typed string. */
const timeIn = (moment: Date, locale: string) => moment.toLocaleTimeString(locale, {hour: '2-digit', minute: '2-digit'});

/**
 * A `t` that knows only `keys`: it answers «key → {time}», so a test reads which key the resolver chose and the
 * time it handed over, never a text. Every key asked is recorded.
 */
function keyT(...keys: string[]) {
    const asked: string[] = [];
    const t = (key: string, opts?: {values?: Record<string, string | number | boolean | Date | null | undefined>}) => {
        asked.push(key);
        return keys.includes(key) ? `${key} → ${String(opts?.values?.time ?? '∅')}` : key;
    };
    return {t, asked};
}

const refused = (over: Partial<ProviderErrorLike>): ProviderErrorLike => ({error: 'raw English message', error_code: 'RATE_LIMITED', ...over});

describe('formatResumeTime — rounding up, today or another day, the locale passed', () => {
    it('rounds the end of the pause up to the next whole minute, never earlier than the end', () => {
        expect(formatResumeTime(25, NOW, 'en-GB')).toBe(timeIn(at(10, 14, 31), 'en-GB')); // 14:30:45 → 14:31
        expect(formatResumeTime(40, NOW, 'en-GB')).toBe(timeIn(at(10, 14, 31), 'en-GB')); // 14:31:00 is already whole
        expect(formatResumeTime(41, NOW, 'en-GB')).toBe(timeIn(at(10, 14, 32), 'en-GB')); // 14:31:01 → 14:32
        expect(formatResumeTime(0, NOW, 'en-GB')).toBe(timeIn(at(10, 14, 31), 'en-GB')); // no wait: the next minute, not 14:30
        expect(formatResumeTime(0, at(10, 14, 30), 'en-GB')).toBe(timeIn(at(10, 14, 30), 'en-GB')); // on a whole minute: that minute
    });

    it('a pause ending today is written as the time alone', () => {
        const out = formatResumeTime(3600, NOW, 'en-GB'); // 15:30:20 → 15:31

        expect(out).toBe(timeIn(at(10, 15, 31), 'en-GB'));
        expect(out).not.toBe(formatDateTime(at(10, 15, 31), 'en-GB'));
    });

    it('a pause ending another day is written with its date and time', () => {
        const out = formatResumeTime(43_200, NOW, 'en-GB'); // 02:30:20 on the 11th → 02:31

        expect(out).toBe(formatDateTime(at(11, 2, 31), 'en-GB'));
        expect(out).not.toBe(timeIn(at(11, 2, 31), 'en-GB'));
    });

    it('a short pause crossing midnight is another day', () => {
        expect(formatResumeTime(45, at(10, 23, 59, 30), 'en-GB')).toBe(formatDateTime(at(11, 0, 1), 'en-GB')); // 00:00:15 → 00:01
    });

    it('writes the moment in the locale it is given', () => {
        const italian = formatResumeTime(3600, NOW, 'it');
        const american = formatResumeTime(3600, NOW, 'en-US');

        expect(italian).toBe(timeIn(at(10, 15, 31), 'it'));
        expect(american).toBe(timeIn(at(10, 15, 31), 'en-US'));
        expect(italian, 'premise: the two locales write 15:31 apart').not.toBe(american);
        expect(formatResumeTime(43_200, NOW, 'it')).toBe(formatDateTime(at(11, 2, 31), 'it'));
    });
});

describe('resumesToday — the same rounding as formatResumeTime', () => {
    it.each([
        {seconds: 29, end: at(10, 23, 59), today: true}, // 23:58:59 → 23:59
        {seconds: 30, end: at(10, 23, 59), today: true}, // 23:59:00, already whole
        {seconds: 31, end: at(11, 0, 0), today: false}, // 23:59:01 → 00:00 of the 11th: rounding up crosses midnight
        {seconds: 90, end: at(11, 0, 0), today: false}, // 00:00:00 of the 11th
    ])('$seconds s after 23:58:30: today is $today, and the moment is written accordingly', ({seconds, end, today}) => {
        const now = at(10, 23, 58, 30);

        expect(resumesToday(seconds, now)).toBe(today);
        expect(formatResumeTime(seconds, now, 'en-GB')).toBe(today ? timeIn(end, 'en-GB') : formatDateTime(end, 'en-GB'));
    });

    it('a pause of a day or more never ends today', () => {
        expect(resumesToday(86_400, at(10, 0, 0))).toBe(false);
        expect(resumesToday(3600, NOW)).toBe(true);
    });

    describe('with the clock at 23:58:30', () => {
        beforeEach(() => {
            vi.useFakeTimers({toFake: ['Date']});
            vi.setSystemTime(at(10, 23, 58, 30));
        });
        afterEach(() => vi.useRealTimers());

        it('reads «now» from the clock when none is given', () => {
            expect(resumesToday(30)).toBe(true);
            expect(resumesToday(31)).toBe(false);
        });
    });
});

describe('resolveProviderError — RATE_LIMITED (X8)', () => {
    beforeEach(() => {
        vi.useFakeTimers({toFake: ['Date']});
        vi.setSystemTime(NOW);
    });
    afterEach(() => vi.useRealTimers());

    it('a pause ending today resolves to RATE_LIMITED, with the time it ends', () => {
        const {t} = keyT(TODAY_KEY, DAY_KEY, NO_TIME_KEY);

        expect(resolveProviderError(refused({retry_after: 90}), t)).toBe(`${TODAY_KEY} → ${formatResumeTime(90, NOW)}`);
    });

    it('a pause ending another day resolves to RATE_LIMITED_DAY, with its date and time', () => {
        const {t, asked} = keyT(TODAY_KEY, DAY_KEY, NO_TIME_KEY);

        expect(resolveProviderError(refused({retry_after: 43_200}), t)).toBe(`${DAY_KEY} → ${formatResumeTime(43_200, NOW)}`);
        expect(asked).toEqual([DAY_KEY]);
    });

    it('chooses the key with the rounding: 45 s before midnight is already another day', () => {
        vi.setSystemTime(at(10, 23, 59, 30));
        const {t} = keyT(TODAY_KEY, DAY_KEY, NO_TIME_KEY);

        expect(resolveProviderError(refused({retry_after: 45}), t)).toBe(`${DAY_KEY} → ${formatResumeTime(45, at(10, 23, 59, 30))}`);
    });

    it('reads the wait from error_details.retry_after when retry_after is absent or null, a numeric string included', () => {
        const {t} = keyT(TODAY_KEY, DAY_KEY, NO_TIME_KEY);

        expect(resolveProviderError(refused({error_details: {retry_after: 600}}), t)).toBe(`${TODAY_KEY} → ${formatResumeTime(600, NOW)}`);
        expect(resolveProviderError(refused({retry_after: null, error_details: {retry_after: '120'}}), t)).toBe(`${TODAY_KEY} → ${formatResumeTime(120, NOW)}`);
    });

    it('retry_after wins over error_details.retry_after', () => {
        const {t} = keyT(TODAY_KEY, DAY_KEY, NO_TIME_KEY);

        expect(resolveProviderError(refused({retry_after: 90, error_details: {retry_after: 43_200}}), t)).toBe(`${TODAY_KEY} → ${formatResumeTime(90, NOW)}`);
    });

    it('a wait of 0 is a wait: the current minute, rounded up', () => {
        const {t} = keyT(TODAY_KEY, DAY_KEY, NO_TIME_KEY);

        expect(resolveProviderError(refused({retry_after: 0}), t)).toBe(`${TODAY_KEY} → ${formatResumeTime(0, NOW)}`);
    });

    it.each([
        {name: 'no wait at all', over: {}},
        {name: 'both null', over: {retry_after: null, error_details: null}},
        {name: 'a negative wait', over: {retry_after: -5}},
        {name: 'an unreadable string', over: {error_details: {retry_after: 'soon'}}},
        {name: 'a boolean', over: {error_details: {retry_after: true}}},
    ])('without a usable wait ($name) it resolves to RATE_LIMITED_NO_TIME, asking no timed key', ({over}) => {
        const {t, asked} = keyT(TODAY_KEY, DAY_KEY, NO_TIME_KEY);

        expect(resolveProviderError(refused(over), t)).toBe(`${NO_TIME_KEY} → ∅`);
        expect(asked).toEqual([NO_TIME_KEY]);
    });

    it('matches the code case-insensitively', () => {
        const {t} = keyT(TODAY_KEY, DAY_KEY, NO_TIME_KEY);

        expect(resolveProviderError(refused({error_code: 'rate_limited', retry_after: 90}), t)).toBe(`${TODAY_KEY} → ${formatResumeTime(90, NOW)}`);
    });

    it('a timed key missing from the catalogue falls back to RATE_LIMITED_NO_TIME', () => {
        const {t} = keyT(NO_TIME_KEY);

        expect(resolveProviderError(refused({retry_after: 90}), t)).toBe(`${NO_TIME_KEY} → ∅`);
        expect(resolveProviderError(refused({retry_after: 43_200}), t)).toBe(`${NO_TIME_KEY} → ∅`);
    });

    it('with none of the three keys, the raw backend message, then a non-empty answer', () => {
        const {t} = keyT();

        expect(resolveProviderError(refused({retry_after: 90}), t)).toBe('raw English message');
        expect(resolveProviderError({error_code: 'RATE_LIMITED'}, t)).toBe('Unknown error');
    });
});
