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
 *
 * X-R66 (PROBE_RATE_LIMITED) — red until X-R66. The probe endpoint refuses past
 * `LIBREFOLIO_PROBE_RATE_LIMIT` probes a minute per user: 429, a `detail` with
 * `error_code` PROBE_RATE_LIMITED, `retry_after` (whole seconds ≥ 1) and the
 * server's English `message`, and the same seconds in `Retry-After`.
 * `probeRateLimitMessage(error, t, now)` words that refusal the X8 way:
 * PROBE_RATE_LIMITED (the pause ends today), PROBE_RATE_LIMITED_DAY (another
 * day), PROBE_RATE_LIMITED_NO_TIME (no usable wait), then the server's
 * `message` when a key is missing; any other error is not its own: null. The
 * error is what the generated client rejects with, an axios error built by
 * axios's own classes; the same «key → {time}» stub reads the key chosen and
 * the time handed over. The export is read off the module when a case runs, so
 * each case is red on its own, naming what is missing. The three texts are read
 * in the four `assets` sources and written as `$t` writes them, with a
 * realistic moment: each fits the 60 characters of the probe's one-line
 * summary, the date included, whatever the month.
 */
import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';
import {formatResumeTime, resolveProviderError, resumesToday, type ProviderErrorLike} from './resolveProviderError';
// X-R66: the module itself, so that a case can reach an export it does not have yet (`probeRateLimitMessage` below).
import * as resolver from './resolveProviderError';
import {AxiosError, AxiosHeaders, type AxiosResponse} from 'axios';
import {getMessageFormatter} from 'svelte-i18n';
import {formatDateTime} from '$lib/utils/core/formatDateTime';
import en from '$lib/i18n/en.json';
import es from '$lib/i18n/es.json';
import fr from '$lib/i18n/fr.json';
import it_ from '$lib/i18n/it.json';
import assetsEn from '$lib/i18n/assets/en.json';
import assetsEs from '$lib/i18n/assets/es.json';
import assetsFr from '$lib/i18n/assets/fr.json';
import assetsIt from '$lib/i18n/assets/it.json';

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

// ─────────────────────────────────────────────────────────────────────────────
// X-R66 — PROBE_RATE_LIMITED: the probe endpoint's own «too many probes»
// (red until X-R66: neither the export nor the three keys exist yet)
// ─────────────────────────────────────────────────────────────────────────────

const PROBE_TODAY_KEY = 'providerErrors.PROBE_RATE_LIMITED';
const PROBE_DAY_KEY = 'providerErrors.PROBE_RATE_LIMITED_DAY';
const PROBE_NO_TIME_KEY = 'providerErrors.PROBE_RATE_LIMITED_NO_TIME';
/** The server's own English for the refusal (`backend/app/api/v1/assets/providers.py`): the last fallback. */
const PROBE_REFUSAL_MESSAGE = 'Too many provider probes: try again later';
/** A realistic wait: the limiter counts the probes of the last minute, so a refusal waits a minute at most. From NOW: 14:31:02 → 14:32. */
const PROBE_WAIT = 42;
/** A few seconds before midnight: PROBE_WAIT later is 00:00:12 on the 11th → 00:01, another day. */
const BEFORE_MIDNIGHT = at(10, 23, 59, 30);

type Translate = ReturnType<typeof keyT>['t'];

/**
 * `probeRateLimitMessage`, called through the module. Until X-R66 exports it, every case below fails here, on the
 * assertion that names what is missing, rather than on a `TypeError` thrown before any assertion ran — and the cases
 * above keep running.
 */
function probeRateLimitMessage(error: unknown, t: Translate, now?: Date): string | null {
    const helper = (resolver as unknown as Record<string, unknown>).probeRateLimitMessage;
    expect(typeof helper, 'red until X-R66: resolveProviderError exports no probeRateLimitMessage(error, t, now) — the probe’s 429 has no wording').toBe('function');
    return (helper as (error: unknown, t: Translate, now?: Date) => string | null)(error, t, now);
}

/** The `detail` of the probe's 429 as the server sends it — its code, the wait in whole seconds, its English — `over` replacing or adding fields. */
function refusalDetail(over: Record<string, unknown> = {}): Record<string, unknown> {
    return {error_code: 'PROBE_RATE_LIMITED', retry_after: PROBE_WAIT, message: PROBE_REFUSAL_MESSAGE, ...over};
}

/** The same detail naming no wait: no `retry_after` at all. */
function refusalDetailWithoutWait(): Record<string, unknown> {
    return {error_code: 'PROBE_RATE_LIMITED', message: PROBE_REFUSAL_MESSAGE};
}

interface ProbeAnswer {
    status?: number;
    statusText?: string;
    /** The answer's body: by default the server's, `{detail}`. */
    data?: unknown;
    /** Its headers as axios hands them over: lower-case names, string values. By default `Retry-After`, the detail's seconds. */
    headers?: Record<string, string>;
}

/**
 * A failed probe as the generated client rejects with it: the axios error of the answer, built by axios's own classes.
 * By default the probe's 429 as the server sends it: the refusal's detail, and `Retry-After` with the same seconds.
 */
function rejected({status = 429, statusText = 'Too Many Requests', data = {detail: refusalDetail()}, headers = {'retry-after': String(PROBE_WAIT)}}: ProbeAnswer = {}): AxiosError {
    const response: AxiosResponse = {status, statusText, data, headers: new AxiosHeaders(headers), config: {headers: new AxiosHeaders()}};
    return new AxiosError(`Request failed with status code ${status}`, status >= 500 ? AxiosError.ERR_BAD_RESPONSE : AxiosError.ERR_BAD_REQUEST, response.config, undefined, response);
}

describe('probeRateLimitMessage — the probe refused for too many probes (X-R66)', () => {
    it('a pause ending today resolves to PROBE_RATE_LIMITED, with the time it ends', () => {
        const {t, asked} = keyT(PROBE_TODAY_KEY, PROBE_DAY_KEY, PROBE_NO_TIME_KEY);
        expect(resumesToday(PROBE_WAIT, NOW), 'premise: from NOW the pause ends today').toBe(true);

        expect(probeRateLimitMessage(rejected(), t, NOW)).toBe(`${PROBE_TODAY_KEY} → ${formatResumeTime(PROBE_WAIT, NOW)}`);
        expect(asked).toEqual([PROBE_TODAY_KEY]);
    });

    it('a few seconds before midnight the pause ends another day: PROBE_RATE_LIMITED_DAY, with its date and time', () => {
        const {t, asked} = keyT(PROBE_TODAY_KEY, PROBE_DAY_KEY, PROBE_NO_TIME_KEY);
        expect(resumesToday(PROBE_WAIT, BEFORE_MIDNIGHT), 'premise: from 23:59:30 the pause ends on the 11th').toBe(false);

        expect(probeRateLimitMessage(rejected(), t, BEFORE_MIDNIGHT)).toBe(`${PROBE_DAY_KEY} → ${formatResumeTime(PROBE_WAIT, BEFORE_MIDNIGHT)}`);
        expect(asked).toEqual([PROBE_DAY_KEY]);
    });

    it.each([
        {seconds: 30, key: PROBE_TODAY_KEY}, // 23:59:00, already whole: today
        {seconds: 31, key: PROBE_DAY_KEY}, // 23:59:01 → 00:00 of the 11th: rounding up crosses midnight
    ])('chooses the key with the rounding of the time it writes: $seconds s after 23:58:30 is $key', ({seconds, key}) => {
        const now = at(10, 23, 58, 30);
        const {t} = keyT(PROBE_TODAY_KEY, PROBE_DAY_KEY, PROBE_NO_TIME_KEY);

        expect(probeRateLimitMessage(rejected({data: {detail: refusalDetail({retry_after: seconds})}, headers: {'retry-after': String(seconds)}}), t, now)).toBe(`${key} → ${formatResumeTime(seconds, now)}`);
    });

    it.each([
        {name: 'no retry_after at all', detail: refusalDetailWithoutWait()},
        {name: 'a null retry_after', detail: refusalDetail({retry_after: null})},
    ])('reads the wait from the Retry-After header when the detail names none ($name)', ({detail}) => {
        const {t} = keyT(PROBE_TODAY_KEY, PROBE_DAY_KEY, PROBE_NO_TIME_KEY);

        expect(probeRateLimitMessage(rejected({data: {detail}, headers: {'retry-after': '120'}}), t, NOW)).toBe(`${PROBE_TODAY_KEY} → ${formatResumeTime(120, NOW)}`);
        expect(probeRateLimitMessage(rejected({data: {detail}, headers: {'retry-after': '43200'}}), t, NOW), 'the header’s wait chooses the key too').toBe(`${PROBE_DAY_KEY} → ${formatResumeTime(43_200, NOW)}`);
    });

    it('the detail’s retry_after wins over the header', () => {
        // The server sends the same seconds in both; were they ever to differ, the structured answer is the detail.
        const {t} = keyT(PROBE_TODAY_KEY, PROBE_DAY_KEY, PROBE_NO_TIME_KEY);

        expect(probeRateLimitMessage(rejected({headers: {'retry-after': '43200'}}), t, NOW)).toBe(`${PROBE_TODAY_KEY} → ${formatResumeTime(PROBE_WAIT, NOW)}`);
    });

    it.each<{name: string; detail: Record<string, unknown>; headers: Record<string, string>}>([
        {name: 'neither a retry_after nor a header', detail: refusalDetailWithoutWait(), headers: {}},
        {name: 'a null retry_after and no header', detail: refusalDetail({retry_after: null}), headers: {}},
        {name: 'a wait neither of them can read', detail: refusalDetail({retry_after: 'soon'}), headers: {'retry-after': 'soon'}},
    ])('without a usable wait ($name) it resolves to PROBE_RATE_LIMITED_NO_TIME, asking no timed key', ({detail, headers}) => {
        const {t, asked} = keyT(PROBE_TODAY_KEY, PROBE_DAY_KEY, PROBE_NO_TIME_KEY);

        expect(probeRateLimitMessage(rejected({data: {detail}, headers}), t, NOW)).toBe(`${PROBE_NO_TIME_KEY} → ∅`);
        expect(asked).toEqual([PROBE_NO_TIME_KEY]);
    });

    it('a timed key missing from the catalogue falls back to PROBE_RATE_LIMITED_NO_TIME', () => {
        const {t} = keyT(PROBE_NO_TIME_KEY);

        expect(probeRateLimitMessage(rejected(), t, NOW)).toBe(`${PROBE_NO_TIME_KEY} → ∅`);
        expect(probeRateLimitMessage(rejected(), t, BEFORE_MIDNIGHT)).toBe(`${PROBE_NO_TIME_KEY} → ∅`);
    });

    it('with none of the three keys in the catalogue, the server’s own message', () => {
        const {t} = keyT();

        expect(probeRateLimitMessage(rejected(), t, NOW)).toBe(PROBE_REFUSAL_MESSAGE);
        expect(probeRateLimitMessage(rejected({data: {detail: refusalDetailWithoutWait()}, headers: {}}), t, NOW)).toBe(PROBE_REFUSAL_MESSAGE);
    });

    it.each<{name: string; error: () => unknown}>([
        {name: 'another status with the same detail, a 503', error: () => rejected({status: 503, statusText: 'Service Unavailable'})},
        {name: 'a 429 with another code, the providers’ RATE_LIMITED', error: () => rejected({data: {detail: refusalDetail({error_code: 'RATE_LIMITED'})}})},
        {name: 'a 429 whose detail is a sentence', error: () => rejected({data: {detail: 'Too Many Requests'}})},
        {name: 'a 429 with a null detail', error: () => rejected({data: {detail: null}})},
        {name: 'a 429 with no detail, a proxy’s page', error: () => rejected({data: '<html><body><h1>429 Too Many Requests</h1></body></html>', headers: {'content-type': 'text/html', 'retry-after': String(PROBE_WAIT)}})},
        {name: 'a request that got no answer', error: () => new AxiosError('Network Error', AxiosError.ERR_NETWORK)},
        {name: 'a plain Error', error: () => new Error('network down')},
        {name: 'the refusal’s detail alone, not an error', error: () => refusalDetail()},
        {name: 'a string', error: () => 'PROBE_RATE_LIMITED'},
        {name: 'undefined', error: () => undefined},
        {name: 'null', error: () => null},
    ])('any other error is not its own — $name: null, the catalogue not asked', ({error}) => {
        const {t, asked} = keyT(PROBE_TODAY_KEY, PROBE_DAY_KEY, PROBE_NO_TIME_KEY);

        expect(probeRateLimitMessage(error(), t, NOW)).toBeNull();
        expect(asked).toEqual([]);
    });

    describe('with no «now» given', () => {
        beforeEach(() => {
            vi.useFakeTimers({toFake: ['Date']});
            vi.setSystemTime(NOW);
        });
        afterEach(() => vi.useRealTimers());

        it('reads «now» from the clock — how the panel and the modal call it', () => {
            const {t} = keyT(PROBE_TODAY_KEY, PROBE_DAY_KEY, PROBE_NO_TIME_KEY);

            expect(probeRateLimitMessage(rejected(), t)).toBe(`${PROBE_TODAY_KEY} → ${formatResumeTime(PROBE_WAIT, NOW)}`);
            vi.setSystemTime(BEFORE_MIDNIGHT);
            expect(probeRateLimitMessage(rejected(), t)).toBe(`${PROBE_DAY_KEY} → ${formatResumeTime(PROBE_WAIT, BEFORE_MIDNIGHT)}`);
        });
    });
});

describe('probeRateLimitMessage — the shipped texts fit the one-line summary (X-R66)', () => {
    /** The four sources of the `assets` subsystem, which owns `providerErrors` (`src/lib/i18n/assets/prefixes.txt`). */
    const SOURCES: Record<string, unknown> = {en: assetsEn, it: assetsIt, fr: assetsFr, es: assetsEs};
    /**
     * The locales the interface writes each language in (`resolveUiLocale`): the language's own default — and, for
     * English, the American writing too, an English interface on an en-US browser: the longest English time and date.
     */
    const LOCALES: Record<string, string[]> = {en: ['en-GB', 'en-US'], it: ['it'], fr: ['fr'], es: ['es']};
    const LANGUAGES = Object.keys(LOCALES);
    /** The width of the probe's one-line summary (`summarizeProbeError`), the date included. */
    const SUMMARY_WIDTH = 60;

    interface Written {
        where: string;
        sentence: string;
    }

    /** The text of `key` in `lang`'s source — or a red naming what is missing. */
    function text(lang: string, key: string): string {
        const providerErrors = (SOURCES[lang] as {providerErrors?: Record<string, unknown>}).providerErrors ?? {};
        expect(providerErrors[key], `red until X-R66: providerErrors.${key} missing from src/lib/i18n/assets/${lang}.json`).toBeTypeOf('string');
        return providerErrors[key] as string;
    }

    /** `message` written as `$t` writes it: svelte-i18n's own compiler, with `values`. */
    function written(message: string, locale: string, values?: Record<string, string>): string {
        return String(getMessageFormatter(message, locale).format(values));
    }

    /** One line per sentence that does not fit: where it was written, what it says, and its length. */
    function overlong(sentences: Written[]): string[] {
        return sentences.filter(({sentence}) => sentence.length > SUMMARY_WIDTH).map(({where, sentence}) => `${where}: «${sentence}» is ${sentence.length} characters`);
    }

    it.each(LANGUAGES)('%s: PROBE_RATE_LIMITED, with a time of today, fits the one-line summary and writes the time', (lang) => {
        const message = text(lang, 'PROBE_RATE_LIMITED');
        expect(resumesToday(PROBE_WAIT, NOW), 'premise: from NOW the pause ends today').toBe(true);
        const sentences: Written[] = [];
        for (const locale of LOCALES[lang]) {
            const time = formatResumeTime(PROBE_WAIT, NOW, locale);
            const sentence = written(message, locale, {time});
            expect(sentence, `${lang} (${locale}): the time the pause ends is in the sentence`).toContain(time);
            sentences.push({where: locale, sentence});
        }

        expect(overlong(sentences), `longer than the ${SUMMARY_WIDTH} characters of the one-line summary`).toEqual([]);
    });

    it.each(LANGUAGES)('%s: PROBE_RATE_LIMITED_DAY, with a date and time just past midnight, fits the one-line summary whatever the month, and writes them', (lang) => {
        const message = text(lang, 'PROBE_RATE_LIMITED_DAY');
        const sentences: Written[] = [];
        for (const locale of LOCALES[lang]) {
            for (let month = 0; month < 12; month++) {
                // The 10th of each month, 30 s before midnight: the pause ends at 00:01 on the 11th — a two-digit day, every month's name.
                const now = new Date(2026, month, 10, 23, 59, 30);
                expect(resumesToday(PROBE_WAIT, now), `premise: the pause ends another day (${now.toDateString()})`).toBe(false);
                const time = formatResumeTime(PROBE_WAIT, now, locale);
                const sentence = written(message, locale, {time});
                expect(sentence, `${lang} (${locale}): the date and time the pause ends are in the sentence`).toContain(time);
                sentences.push({where: `${locale}, ${time}`, sentence});
            }
        }

        expect(overlong(sentences), `longer than the ${SUMMARY_WIDTH} characters of the one-line summary`).toEqual([]);
    });

    it.each(LANGUAGES)('%s: PROBE_RATE_LIMITED_NO_TIME fits the one-line summary', (lang) => {
        const message = text(lang, 'PROBE_RATE_LIMITED_NO_TIME');
        const sentences: Written[] = LOCALES[lang].map((locale) => ({where: locale, sentence: written(message, locale)}));

        expect(overlong(sentences), `longer than the ${SUMMARY_WIDTH} characters of the one-line summary`).toEqual([]);
    });
});
