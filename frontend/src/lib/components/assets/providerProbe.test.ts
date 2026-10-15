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
 *
 * The tooltip's days and its history header are the last describe's (T-ISO): the
 * structural cases above it compare a day with its notation set aside (`sansDay`,
 * ISO or the house notation), so they hold before and after that cure. The last
 * describe boots svelte-i18n to word the caller's labels from the catalogue, and
 * switches the interface language as the selector does (`currentLanguage`).
 */
import {afterEach, beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';
import {get} from 'svelte/store';
import {waitLocale} from 'svelte-i18n';

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

import {setupI18n} from '$test/component';
import {_} from '$lib/i18n';
import {currentLanguage} from '$lib/stores/app/language';
import {uiLocale} from '$lib/stores/app/uiLocale';
import {formatAxisDate} from '$lib/utils/core/formatAxisDate';
import {SOFT_FAIL_CODES, isSoftProbeFailure, isRealProbeError, summarizeProbeError, formatCurrencyForTooltip, buildProbeTooltipHtml, type ProbeTooltipLabels} from './providerProbe';

/** The labels a caller passes the tooltip — `close` among them, as `ProbeTooltipLabels` reads after T-ISO. */
type CallerLabels = ProbeTooltipLabels & {close: string};

/**
 * The calendar day `iso` (`YYYY-MM-DD`) in the house notation of a tooltip day, as Intl writes it in `locale`:
 * numeric year, short month, numeric day — `2 gen 2024`, `2 janv. 2024`, `Jan 2, 2024`. The oracle, never a typed date.
 */
function houseDay(iso: string, locale: string): string {
    const [year, month, day] = iso.split('-').map(Number);
    return new Intl.DateTimeFormat(locale, {year: 'numeric', month: 'short', day: 'numeric'}).format(new Date(year, month - 1, day));
}

/** Where a day stands once its notation is set aside. */
const DAY = '⟨day⟩';

/** `text` with the day `iso` replaced by `DAY`, written as ISO or in the house notation of the interface locale. */
function sansDay(text: string, iso: string): string {
    return text.split(houseDay(iso, uiLocale())).join(DAY).split(iso).join(DAY);
}

/** A tooltip table's rows as text: each `<tr>`'s `<th>`/`<td>` cells, in order. */
function rowsOf(html: string): string[][] {
    return [...html.matchAll(/<tr\b[^>]*>([\s\S]*?)<\/tr>/g)].map(([, row]) => [...row.matchAll(/<(th|td)\b[^>]*>([\s\S]*?)<\/\1>/g)].map((cell) => cell[2]));
}

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

describe('providerProbe — RATE_LIMITED is a soft failure (X8)', () => {
    // A provider paused after «too many requests»: the configuration may well be right, and the message says until
    // when — a warning, never the red that gates «Save Without Testing?».
    const paused = 'Provider mockprov is paused after too many requests: 60 s left';

    it('is one of the soft codes, whatever its case', () => {
        expect(SOFT_FAIL_CODES.has('RATE_LIMITED')).toBe(true);
        expect(isSoftProbeFailure(undefined, 'RATE_LIMITED')).toBe(true);
        expect(isSoftProbeFailure(paused, 'rate_limited')).toBe(true);
    });

    it('never counts as a real probe error, with or without its message', () => {
        expect(isRealProbeError({success: false, error_code: 'RATE_LIMITED', error: paused})).toBe(false);
        expect(isRealProbeError({success: false, error_code: 'RATE_LIMITED'})).toBe(false);
    });

    it('it is the code that makes it soft: the same message without it is a real error', () => {
        expect(isSoftProbeFailure(paused)).toBe(false);
        expect(isRealProbeError({success: false, error: paused})).toBe(true);
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
    // The English labels; `close` heads the history's price column after T-ISO — the word the module writes today.
    const labels: CallerLabels = {date: 'Date', currentPrice: 'Current Price', close: 'Close'};

    it('returns the raw detail (or Error) for a failed result', () => {
        expect(buildProbeTooltipHtml({success: false, detail: 'boom'}, labels)).toBe('boom');
        expect(buildProbeTooltipHtml({success: false}, labels)).toBe('Error');
    });

    it('builds a single-row price table when priceValue is set', () => {
        const html = buildProbeTooltipHtml({success: true, priceValue: 12.5, priceCurrency: 'USD', priceDate: '2024-01-02'}, labels);
        expect(html).toContain('<table');
        expect(html).toContain('Current Price');
        // The day in either notation: how it is written is the T-ISO describe's.
        expect(sansDay(html, '2024-01-02')).toContain(`>${DAY}<`);
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
        // The day in either notation: how it is written is the T-ISO describe's.
        expect(sansDay(html, '2024-01-01')).toContain(`>${DAY}<`);
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

describe('providerProbe — buildProbeTooltipHtml: its days and its price column’s header in the interface language (T-ISO)', () => {
    /*
     * The hover table of a probe result writes days: the current price's (`priceDate`) and each history sample's
     * (`p.date`). Today both are ISO (`2024-01-02`) whatever the interface language, and the history's price column
     * is headed `💰 Close`, an English word written in the module.
     *
     * The contract, after the cure: both days go through `formatDay` — a `YYYY-MM-DD` day in the house notation of a
     * tooltip day, `formatAxisDate(uiLocale(), day, true)` (`2 gen 2024`, `2 janv. 2024`), anything else unchanged —
     * and a missing `priceDate` still reads `—`. `ProbeTooltipLabels` gains `close`: the history header is
     * `💰 ${labels.close}` before the currency in brackets, and the caller passes `$t('dataEditor.col.close')`.
     *
     * Expected days come from Intl in the interface locale (`houseDay`, tied to `formatAxisDate` by a control); the
     * labels are the caller's own, worded by the catalogue in the interface language — a close label distinct from
     * the English word. The table is read cell by cell (`rowsOf`). Red today in Italian and French; green today and
     * after: the missing day's `—`.
     */
    const LANGUAGES = ['it', 'fr'] as const;
    type UiLanguage = 'en' | (typeof LANGUAGES)[number];

    /** Switch the interface language in place, as the language selector does; answer the locale it now writes days in. */
    async function speak(lang: UiLanguage): Promise<string> {
        currentLanguage.set(lang);
        await waitLocale(lang);
        const locale = uiLocale();
        expect(new Intl.Locale(locale).language, `control: the interface locale follows the ${lang} interface`).toBe(lang);
        return locale;
    }

    /** A catalogue message as the interface language words it. */
    function catalogue(key: string): string {
        return get(_)(key);
    }

    /** The labels the caller passes, as the catalogue words them in the interface language. */
    function callerLabels(): CallerLabels {
        return {date: catalogue('common.date'), currentPrice: catalogue('common.currentPrice'), close: catalogue('dataEditor.col.close')};
    }

    beforeAll(async () => {
        await setupI18n('en');
    });

    afterEach(async () => {
        // The language is module-level state shared by every case of the file.
        await speak('en');
    });

    it.each(LANGUAGES)('%s interface: the current price’s day is written in the house notation', async (lang) => {
        const locale = await speak(lang);
        expect(houseDay('2024-01-02', locale), 'control: the oracle is the lot charts’ tooltip day').toBe(formatAxisDate(locale, '2024-01-02', true));

        const rows = rowsOf(buildProbeTooltipHtml({success: true, priceValue: 12.5, priceCurrency: 'USD', priceDate: '2024-01-02'}, callerLabels()));
        expect(rows, 'barrier: a header row and one price row, two cells each').toEqual([expect.any(Array), [expect.any(String), expect.any(String)]]);

        expect(rows[1][0], `the current price’s day is not in the ${lang} interface’s notation: the table writes the ISO day`).toBe(houseDay('2024-01-02', locale));
    });

    it.each(LANGUAGES)('%s interface: the history’s price column is headed by the caller’s close label, and each sample’s day is written in the house notation', async (lang) => {
        const locale = await speak(lang);
        const labels = callerLabels();
        expect(labels.close, `premise: the ${lang} close label is not the English word`).not.toBe(get(_)('dataEditor.col.close', {locale: 'en'}));

        const rows = rowsOf(
            buildProbeTooltipHtml(
                {
                    success: true,
                    priceCurrency: 'EUR',
                    samplePrices: [
                        {date: '2024-01-01', close: 10},
                        {date: '2024-01-02', close: 11},
                    ],
                },
                labels,
            ),
        );

        expect({header: rows[0], days: rows.slice(1).map(([day]) => day)}, `the history table is not in the ${lang} interface’s words and notation: «Close» is written in English, the days as ISO`).toEqual({
            header: [`📅 ${labels.date}`, `💰 ${labels.close} (${formatCurrencyForTooltip('EUR')})`],
            days: [houseDay('2024-01-01', locale), houseDay('2024-01-02', locale)],
        });
    });

    it.each(LANGUAGES)('%s interface: a missing price day still reads — (guard)', async (lang) => {
        await speak(lang);

        const rows = rowsOf(buildProbeTooltipHtml({success: true, priceValue: 1, priceCurrency: 'USD'}, callerLabels()));

        expect(rows[1]?.[0], 'the missing day is no longer the em dash').toBe('—');
    });
});
