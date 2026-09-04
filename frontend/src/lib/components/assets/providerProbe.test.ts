/**
 * providerProbe — pure unit tests (Vitest, node env).
 *
 * These are the classifier + formatter helpers shared by ProviderAssignmentSection
 * and AssetModal's auto-probe. Every branch is a decision the user perceives
 * (a green tick vs an amber warning vs a red error; a rich tooltip vs a bare
 * message), so each one is worth pinning.
 *
 * The currency store is mocked so `formatCurrencyForTooltip` is deterministic and
 * every flag/symbol branch is reachable without loading real currency metadata.
 */
import {beforeEach, describe, expect, it, vi} from 'vitest';

vi.mock('$lib/stores/reference/currencyStore', () => ({
    getCurrencyInfo: vi.fn((code: string) => {
        const table: Record<string, {symbol: string; flag_emoji: string}> = {
            USD: {symbol: '$', flag_emoji: '🇺🇸'},
            EUR: {symbol: '€', flag_emoji: '🇪🇺'},
            // A currency whose symbol IS its code (symbol branch must drop it):
            XAU: {symbol: 'XAU', flag_emoji: '🏳️'},
            // A currency with a symbol but the placeholder flag (flag branch drops it):
            GBP: {symbol: '£', flag_emoji: '🏳️'},
        };
        return table[code] ?? {code, name: code, symbol: code, flag_emoji: '🏳️', country_codes: [], country_names: []};
    }),
}));

import {SOFT_FAIL_CODES, isSoftProbeFailure, isRealProbeError, summarizeProbeError, formatCurrencyForTooltip, buildProbeTooltipHtml} from './providerProbe';

beforeEach(() => vi.clearAllMocks());

describe('providerProbe — isSoftProbeFailure', () => {
    it('treats each SOFT_FAIL_CODE (case-insensitive) as a soft failure', () => {
        expect(SOFT_FAIL_CODES.has('NO_DATA')).toBe(true);
        expect(isSoftProbeFailure(undefined, 'NO_DATA')).toBe(true);
        expect(isSoftProbeFailure(undefined, 'not_implemented')).toBe(true); // lowercased → uppercased
    });

    it('ignores an unknown error code and falls through to the message heuristic', () => {
        expect(isSoftProbeFailure(undefined, 'HTTP_ERROR')).toBe(false); // no detail → false
        expect(isSoftProbeFailure('Provider NOT supported here', 'HTTP_ERROR')).toBe(true);
    });

    it('returns false when there is neither a soft code nor a matching message', () => {
        expect(isSoftProbeFailure(undefined, null)).toBe(false);
        expect(isSoftProbeFailure('connection timeout')).toBe(false);
    });

    it('matches each message variant of "not supported"', () => {
        expect(isSoftProbeFailure('op NOT_IMPLEMENTED')).toBe(true);
        expect(isSoftProbeFailure('this is not supported')).toBe(true);
        expect(isSoftProbeFailure('feature not implemented')).toBe(true);
    });
});

describe('providerProbe — isRealProbeError', () => {
    it('is false for a missing op or a successful op', () => {
        expect(isRealProbeError(undefined)).toBe(false);
        expect(isRealProbeError(null)).toBe(false);
        expect(isRealProbeError({success: true})).toBe(false);
    });

    it('is false when the failure is soft (code or message)', () => {
        expect(isRealProbeError({success: false, error_code: 'NO_DATA'})).toBe(false);
        expect(isRealProbeError({success: false, error: 'not implemented'})).toBe(false);
    });

    it('is true when the failure is a genuine error', () => {
        expect(isRealProbeError({success: false, error: 'HTTP 500', error_code: 'HTTP_ERROR'})).toBe(true);
        expect(isRealProbeError({success: false})).toBe(true); // no code, no message → real
    });
});

describe('providerProbe — summarizeProbeError', () => {
    it('returns a generic label when there is no detail', () => {
        expect(summarizeProbeError(undefined)).toBe('Error');
        expect(summarizeProbeError('')).toBe('Error');
    });

    it('maps each known error shape to its short label', () => {
        expect(summarizeProbeError('op NOT_IMPLEMENTED')).toBe('Not supported');
        expect(summarizeProbeError('Connection timeout after 30s')).toBe('Connection timeout');
        expect(summarizeProbeError('selector NOT_FOUND on page')).toBe('Selector not found');
        expect(summarizeProbeError('symbol NOT_FOUND')).toBe('Element not found');
        expect(summarizeProbeError('HTTP_ERROR 502')).toBe('HTTP error');
        expect(summarizeProbeError('request failed: refused')).toBe('Connection failed');
        expect(summarizeProbeError('PARSE_ERROR at line 3')).toBe('Parse error');
        expect(summarizeProbeError('MISSING_PARAMS: currency')).toBe('Missing parameters');
    });

    it('passes a short unknown detail through unchanged', () => {
        expect(summarizeProbeError('weird thing')).toBe('weird thing');
    });

    it('truncates a long unknown detail to 60 chars + ellipsis', () => {
        const long = 'x'.repeat(80);
        const out = summarizeProbeError(long);
        expect(out).toBe('x'.repeat(60) + '…');
        expect(out.length).toBe(61);
    });
});

describe('providerProbe — formatCurrencyForTooltip', () => {
    it('returns empty string for a missing code', () => {
        expect(formatCurrencyForTooltip(undefined)).toBe('');
        expect(formatCurrencyForTooltip('')).toBe('');
    });

    it('joins flag + code + symbol when both are meaningful', () => {
        expect(formatCurrencyForTooltip('USD')).toBe('🇺🇸 USD $');
    });

    it('drops the placeholder flag but keeps a real symbol', () => {
        expect(formatCurrencyForTooltip('GBP')).toBe('GBP £');
    });

    it('drops a symbol equal to the code', () => {
        expect(formatCurrencyForTooltip('XAU')).toBe('XAU'); // flag placeholder + symbol==code → just code
    });
});

describe('providerProbe — buildProbeTooltipHtml', () => {
    const labels = {date: 'Date', currentPrice: 'Current Price'};

    it('returns the raw detail (or Error) for a failed result', () => {
        expect(buildProbeTooltipHtml({success: false, detail: 'boom'}, labels)).toBe('boom');
        expect(buildProbeTooltipHtml({success: false}, labels)).toBe('Error');
    });

    it('builds a single-row price table when priceValue is set', () => {
        const html = buildProbeTooltipHtml({success: true, priceValue: 12.5, priceCurrency: 'USD', priceDate: '2024-01-02'}, labels);
        expect(html).toContain('<table');
        expect(html).toContain('Current Price');
        expect(html).toContain('2024-01-02');
        expect(html).toContain('12.50 🇺🇸 USD $');
    });

    it('renders an em dash for a missing price date', () => {
        const html = buildProbeTooltipHtml({success: true, priceValue: 1, priceCurrency: 'USD'}, labels);
        expect(html).toContain('>—<');
    });

    it('builds a multi-row history table with a currency label when sample prices exist', () => {
        const html = buildProbeTooltipHtml(
            {
                success: true,
                priceCurrency: 'EUR',
                samplePrices: [
                    {date: '2024-01-01', close: 10},
                    {date: '2024-01-02', close: 11},
                ],
            },
            labels,
        );
        expect(html).toContain('Close (🇪🇺 EUR €)');
        expect(html).toContain('2024-01-01');
        expect(html).toContain('11.00');
    });

    it('omits the currency label in the history header when no currency is known', () => {
        const html = buildProbeTooltipHtml({success: true, samplePrices: [{date: '2024-01-01', close: 10}]}, labels);
        expect(html).toContain('💰 Close</th>');
    });

    it('falls back to detail (or em dash) for a successful result with no price data', () => {
        expect(buildProbeTooltipHtml({success: true, detail: 'metadata ok'}, labels)).toBe('metadata ok');
        expect(buildProbeTooltipHtml({success: true}, labels)).toBe('—');
        expect(buildProbeTooltipHtml({success: true, samplePrices: []}, labels)).toBe('—'); // empty array → fallthrough
    });
});
