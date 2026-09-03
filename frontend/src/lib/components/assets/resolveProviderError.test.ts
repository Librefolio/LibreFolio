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
 */
import {describe, expect, it} from 'vitest';
import {resolveProviderError, type ProviderErrorLike} from './resolveProviderError';
import en from '$lib/i18n/en.json';

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
        for (const key of ['NO_DATA', 'NO_DATA_STALE', 'NOT_FOUND', 'FETCH_ERROR', 'NOT_IMPLEMENTED', 'TIMEOUT', 'MISSING_PARAMS', 'PARSE_ERROR', 'SCRAPE_ERROR']) {
            expect(providerErrors, `providerErrors.${key} missing from en.json`).toHaveProperty(key);
        }
    });
});
