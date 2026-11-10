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
 * The tooltip's days and its history header are the T-ISO describe's: the
 * structural cases above it compare a day with its notation set aside (`sansDay`,
 * ISO or the house notation), so they hold before and after that cure. The T-ISO
 * describe boots svelte-i18n to word the caller's labels from the catalogue, and
 * switches the interface language as the selector does (`currentLanguage`).
 *
 * The tooltip is rendered as HTML, and a failure's detail is the provider's text (an
 * external site's error, a reason phrase): `buildProbeTooltipHtml` escapes the detail,
 * on a failure and on the success fall-through, while the tables keep their markup
 * (security review of CP10–CP11). The escaped oracles are written by hand, never
 * computed with `escapeHtml`.
 *
 * C-97c-3 (the last describe): the table's prices keep their significant digits. Its
 * digits are typed, under an English UI on an en-US browser: Node's `navigator.language`
 * follows the host's ICU locale, so the browser is pinned to en-US before any import, as
 * the chart helpers' tests pin it (the interface locale takes its region from it, M-18).
 */
import {afterAll, afterEach, beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';

// The browser, pinned before any import: the interface locale takes its region from it.
vi.hoisted(() => {
    vi.stubGlobal('navigator', {language: 'en-US', languages: ['en-US']});
});

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
import {SOFT_FAIL_CODES, isSoftProbeFailure, isRealProbeError, summarizeProbeError, formatCurrencyForTooltip, buildProbeTooltipHtml, type ProbeTooltipLabels, type ProbeTooltipResult} from './providerProbe';

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

afterAll(() => {
    vi.unstubAllGlobals();
});

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

    it('returns the detail escaped (or Error) for a failed result', () => {
        expect(buildProbeTooltipHtml({success: false, detail: 'boom'}, labels)).toBe('boom');
        expect(buildProbeTooltipHtml({success: false, detail: `401 <b>"key"</b> isn't valid & expired`}, labels)).toBe('401 &lt;b&gt;&quot;key&quot;&lt;/b&gt; isn&#39;t valid &amp; expired');
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

    describe('the detail is escaped (security review of CP10–CP11)', () => {
        /*
         * The tooltip renders HTML, and DOMPurify stops a script, not an image that calls home or a form asking for the
         * key: markup in the provider's detail must read as text. The tables keep their markup: their labels are the
         * caller's, their cells a validated currency, days and numbers.
         */
        const IMAGE = '<img src=//x.example/a onerror=alert(1)>';
        const FORM = '<form action=//x.example>';
        /** Both again, quoted, beside an ampersand: every character `escapeHtml` replaces. */
        const QUOTED = `401 for "MSFT": <img src="//x.example/a" onerror='alert(1)'> & <form action='//x.example'><input name="key"></form>`;

        /** Each detail, and the text the tooltip shows instead: written by hand, the `&` escaped first (no `&amp;lt;`). */
        const ESCAPED: Array<[label: string, detail: string, shown: string]> = [
            ['an image that calls home', IMAGE, '&lt;img src=//x.example/a onerror=alert(1)&gt;'],
            ['a form asking for the key', FORM, '&lt;form action=//x.example&gt;'],
            ['both, quoted, beside an ampersand', QUOTED, '401 for &quot;MSFT&quot;: &lt;img src=&quot;//x.example/a&quot; onerror=&#39;alert(1)&#39;&gt; &amp; &lt;form action=&#39;//x.example&#39;&gt;&lt;input name=&quot;key&quot;&gt;&lt;/form&gt;'],
        ];

        const SAMPLES = [
            {date: '2024-01-01', close: 10},
            {date: '2024-01-02', close: 11},
        ];

        /** How many cells each row of a tooltip table has. */
        const widthsOf = (html: string): number[] => rowsOf(html).map((cells) => cells.length);

        it.each(ESCAPED)('a failure shows %s as text', (_label, detail, shown) => {
            const html = buildProbeTooltipHtml({success: false, detail}, labels);

            expect(html).toBe(shown);
            expect(html, 'no tag can open or close, no quoted attribute can end').not.toMatch(/[<>"']/);
        });

        it.each(ESCAPED)('the success fall-through, with no price and no sample, shows %s as text', (_label, detail, shown) => {
            const results: ProbeTooltipResult[] = [
                {success: true, detail},
                {success: true, detail, samplePrices: []},
            ];

            for (const result of results) {
                const html = buildProbeTooltipHtml(result, labels);

                expect(html, `samples: ${JSON.stringify(result.samplePrices)}`).toBe(shown);
                expect(html).not.toMatch(/[<>"']/);
            }
        });

        it('a detail without markup is shown as it is, on a failure and on the fall-through', () => {
            const plain = 'HTTP 404: /v1/quote?symbol=MSFT — fonds introuvable, réessayez dans 60 s';

            expect(buildProbeTooltipHtml({success: false, detail: plain}, labels)).toBe(plain);
            expect(buildProbeTooltipHtml({success: true, detail: plain}, labels)).toBe(plain);
        });

        it('the tables keep their markup, and a detail beside a price or a sample never reaches them raw', () => {
            const tables = {
                price: buildProbeTooltipHtml({success: true, detail: QUOTED, priceValue: 12.5, priceCurrency: 'USD', priceDate: '2024-01-02'}, labels),
                history: buildProbeTooltipHtml({success: true, detail: QUOTED, priceCurrency: 'EUR', samplePrices: SAMPLES}, labels),
            };

            expect(widthsOf(tables.price), 'price: a header row and a price row, two cells each').toEqual([2, 2]);
            expect(widthsOf(tables.history), 'history: a header row and a row per sample, two cells each').toEqual([2, 2, 2]);
            for (const [name, html] of Object.entries(tables)) {
                expect(html.startsWith('<table') && html.endsWith('</table>'), `${name}: one table`).toBe(true);
                expect(html, `${name}: nothing in it escaped`).not.toContain('&lt;');
                expect(html, `${name}: none of the detail's tags`).not.toMatch(/<(img|form|input)\b/);
            }
        });
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

/**
 * C-97c-3 (decision D-C97c-1 of the coordinator, 17/10): a price on screen keeps its significant digits.
 *
 * The probe's hover table writes the current price and each history sample's close with two fixed decimals,
 * `formatFixed(Number(…), 2)`: a provider quoting an asset at 0.0000034573 USD shows `0.00`, one at 1.234 shows
 * `1.23`. The contract: `formatPrice(Number(…))` — two decimals at least, as many as the first four significant
 * digits need (`priceFractionDigits`, formatFixed.ts).
 *
 * Reds: a current price of 0.0000034573 (today `0.00`) and of 1.234 (today `1.23`); a history whose closes are
 * 0.0000034573 and 0.0000035 (today `0.00` both). Guards, green today and after: 12.5 → `12.50`, 123.45, a close of 11
 * → `11.00`. Each figure is read in its cell (`rowsOf`) and matched as a whole number token, never as the cell — which
 * also holds the currency. English UI on the en-US browser this file pins, checked before each case: the digits are
 * typed.
 */
describe('providerProbe — buildProbeTooltipHtml: a price keeps its significant digits (C-97c-3, D-C97c-1)', () => {
    /** The labels a caller passes: what they say is not under test here. */
    const labels: CallerLabels = {date: 'Date', currentPrice: 'Current Price', close: 'Close'};

    /** `digits` as a whole number in a text: no digit, decimal mark, group separator or sign glued to either side. */
    function numberToken(digits: string): RegExp {
        return new RegExp(`(?<![\\d.,+\\-\\u2212])${digits.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}(?![.,]?\\d)`);
    }

    /** The current price's cell: the second cell of the table's second row. */
    function currentPriceCell(priceValue: number): string {
        const rows = rowsOf(buildProbeTooltipHtml({success: true, priceValue, priceCurrency: 'USD', priceDate: '2024-01-02'}, labels));
        expect(
            rows.map((cells) => cells.length),
            'barrier: a header row and one price row, two cells each',
        ).toEqual([2, 2]);
        return rows[1][1];
    }

    /** The close cell of each sample, in the order given. */
    function closeCells(closes: number[]): string[] {
        const rows = rowsOf(buildProbeTooltipHtml({success: true, priceCurrency: 'EUR', samplePrices: closes.map((close, index) => ({date: `2024-01-0${index + 1}`, close}))}, labels));
        expect(
            rows.map((cells) => cells.length),
            'barrier: a header row and a row per sample, two cells each',
        ).toEqual([2, ...closes.map(() => 2)]);
        return rows.slice(1).map(([, close]) => close);
    }

    beforeEach(() => {
        // The expected digits are typed: the premise that the table is written en-US, checked.
        expect(uiLocale(), 'control: an English UI on the en-US browser this file pins is written en-US').toBe('en-US');
    });

    it('a current price of 0.0000034573 USD reads 0.000003457, not 0.00', () => {
        expect(currentPriceCell(0.0000034573), 'the current price (today 0.00)').toMatch(numberToken('0.000003457'));
    });

    it('a current price of 1.234 USD reads 1.234 — four significant digits — not 1.23', () => {
        expect(currentPriceCell(1.234), 'the current price (today 1.23)').toMatch(numberToken('1.234'));
    });

    it('a history sample’s close of 0.0000034573 reads 0.000003457, and one of 0.0000035 reads 0.0000035, not 0.00', () => {
        const [first, second] = closeCells([0.0000034573, 0.0000035]);

        expect.soft(first, 'the first close (today 0.00)').toMatch(numberToken('0.000003457'));
        expect.soft(second, 'the second close (today 0.00)').toMatch(numberToken('0.0000035'));
    });

    it('guard: 12.5 still reads 12.50 and 123.45 123.45 in the current price, a close of 11 still 11.00', () => {
        expect.soft(currentPriceCell(12.5), 'the current price 12.5').toMatch(numberToken('12.50'));
        expect.soft(currentPriceCell(123.45), 'the current price 123.45').toMatch(numberToken('123.45'));
        expect.soft(closeCells([11])[0], 'the close 11').toMatch(numberToken('11.00'));
    });
});
