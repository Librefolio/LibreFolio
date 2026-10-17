/**
 * fxConversionHelper — pure unit tests (node env, no jsdom): the implied rate, the spread and the info tooltip of an
 * FX_CONVERSION pair.
 *
 * The first block: the tooltip's data when no market rate is usable, and its market-not-available branch. The last block
 * (C-97c-4): the tooltip's rates and spread keep their significant digits. Its figures are typed, under an English UI on
 * an en-US browser: Node's `navigator.language` follows the host's ICU locale, so the browser is pinned to en-US before
 * any import, as the chart helpers' tests pin it (the interface locale takes its region from it, M-18). The labels come
 * from a `t` that echoes its key, so a line is found by its key, never by a word.
 */
import {afterAll, beforeEach, describe, expect, it, vi} from 'vitest';

// The browser, pinned before any import: the interface locale takes its region from it.
vi.hoisted(() => {
    vi.stubGlobal('navigator', {language: 'en-US', languages: ['en-US']});
});

import {uiLocale} from '$lib/stores/app/uiLocale';
import {formatFixed, formatPrice} from '$lib/utils/core/formatFixed';
import {buildFxTooltipData, buildFxTooltipHtml, computeFxConversionInfo} from './fxConversionHelper';

const t = (key: string) => key;

afterAll(() => {
    vi.unstubAllGlobals();
});

describe('fxConversionHelper', () => {
    it('builds no-market tooltip data when the FX point has a zero rate', () => {
        const info = computeFxConversionInfo(-100, 'USD', 90, 'EUR');

        if (!info) throw new Error('Expected non-null FX conversion info');
        const data = buildFxTooltipData(info, {
            date: '2024-01-01',
            rate: 0,
            backwardFillInfo: {actualRateDate: '2023-12-29', daysBack: 3},
        });

        expect(data).toMatchObject({
            impliedRate: 0.9,
            base: 'USD',
            quote: 'EUR',
            marketRate: null,
            marketDate: null,
            staleDays: null,
            spread: null,
        });
    });

    it('builds no-market tooltip data when the FX point has a null rate', () => {
        const info = computeFxConversionInfo(-100, 'USD', 90, 'EUR');

        if (!info) throw new Error('Expected non-null FX conversion info');
        const data = buildFxTooltipData(info, {
            date: '2024-01-01',
            rate: null,
            backwardFillInfo: {actualRateDate: '2023-12-29', daysBack: 3},
        });

        expect(data).toMatchObject({
            impliedRate: 0.9,
            base: 'USD',
            quote: 'EUR',
            marketRate: null,
            marketDate: null,
            staleDays: null,
            spread: null,
        });
    });

    it('renders the market-not-available branch when market rate is null', () => {
        const html = buildFxTooltipHtml(
            {
                impliedRate: 0.9,
                base: 'USD',
                quote: 'EUR',
                marketRate: null,
                marketDate: null,
                staleDays: null,
                spread: null,
            },
            t,
        );

        expect(html).toContain('transactions.fxInfo.marketNotAvailable');
        expect(html).not.toContain('transactions.fxInfo.marketRate');
    });
});

/**
 * C-97c-4 (decision D-C97c-1 of the coordinator, 17/10): a rate on screen keeps its significant digits.
 *
 * The FX info tooltip of an FX_CONVERSION pair (`buildFxTooltipHtml`, shared by the bulk modal's banner and the form
 * modal's info marker) writes the implied rate, the market rate and the spread between them with four fixed decimals —
 * `formatFixed(data.impliedRate, 4)`, `formatFixed(data.marketRate, 4)`, `formatFixed(data.spread.absolute, 4, {signed:
 * true})` — so a conversion between a weak and a strong currency loses its digits: 1,000,000 VND converted into 41.20 USD
 * shows an implied rate of `0.0000`, a market rate of 0.0000391 `0.0000` and a spread of 0.0000021 `+0.0000`. The
 * contract: `formatPrice(rate, {minDecimals: 4})` for the two rates, `formatPrice(spread, {minDecimals: 4, signed: true})`
 * for the spread — four decimals at least, as many as the first four significant digits need (`priceFractionDigits`,
 * formatFixed.ts), at most twelve; a `+` on a positive spread, no sign on a zero one. Markup and classes unchanged.
 *
 * Reds on HEAD, because the sites still write `formatFixed(…, 4)`: the VND→USD conversion above, through the helper's own
 * `computeFxConversionInfo` and `buildFxTooltipData` — implied 41.2 / 1,000,000 (today `0.0000`), market 0.0000391 (today
 * `0.0000`), spread their difference (today `+0.0000`) — and a spread of -0.0000021 (today `-0.0000`). Guards, green today
 * and after: EUR→USD at 1.0823 against 1.0801 with a spread of 0.0022 (`1.0823`, `1.0801`, `+0.0022`), and a zero spread
 * (`0.0000`, no sign).
 *
 * Premises, checked in each case before the tooltip is read: the cure's formatter writes the expected text
 * (`formatPrice(x, {minDecimals: 4[, signed: true]})`, the oracle: the typed strings are its own, not guesses) and the
 * site's formatter today writes what the tooltip shows today (`formatFixed(x, 4[, {signed: true}])`, the barrier). A red
 * after them is the site's.
 *
 * Reading. The tooltip is an HTML string with no handle in it: a line is a `<div>` of it read as text, found by the key
 * its label echoes, and the figure is the first token after the label. No case has a stale warning or a market date, so
 * the market line holds its figure alone.
 */
describe('buildFxTooltipHtml — the rates and the spread keep their significant digits (C-97c-4, D-C97c-1)', () => {
    const IMPLIED = 'transactions.fxInfo.impliedRate';
    const MARKET = 'transactions.fxInfo.marketRate';
    const SPREAD = 'transactions.fxInfo.spread';

    /**
     * The premise of a case: the cure, `formatPrice(value, {minDecimals: 4})`, writes `cure`, and the site's formatter
     * today, `formatFixed(value, 4)`, writes `today` — both `signed` for the spread. Checked before the tooltip is read, so
     * a red after them is the site's.
     */
    function premise(value: number, cure: string, today: string, {signed = false}: {signed?: boolean} = {}): void {
        expect(formatPrice(value, {minDecimals: 4, signed}), `control: the cure, formatPrice(${value}, {minDecimals: 4${signed ? ', signed: true' : ''}}), writes ${cure}`).toBe(cure);
        expect(formatFixed(value, 4, {signed}), `barrier: the site today, formatFixed(${value}, 4${signed ? ', {signed: true}' : ''}), writes ${today}`).toBe(today);
    }

    /** The tooltip's lines as text: each `<div>` of it, its tags dropped and its whitespace runs collapsed. */
    function linesOf(html: string): string[] {
        return html
            .split(/<\/?div\b[^>]*>/)
            .map((chunk) =>
                chunk
                    .replace(/<[^>]*>/g, '')
                    .replace(/\s+/g, ' ')
                    .trim(),
            )
            .filter((line) => line !== '');
    }

    /** The figure the line labelled `key` writes: the first token after its label. */
    function figureOf(html: string, key: string): string {
        const line = linesOf(html).find((text) => text.startsWith(`${key}:`));
        if (line === undefined) throw new Error(`no line labelled ${key} in the tooltip: ${html}`);
        return line
            .slice(key.length + 1)
            .trim()
            .split(' ')[0];
    }

    /** The three figures of a tooltip with a market rate: the implied rate, the market rate and the spread. */
    function figuresOf(html: string): {implied: string; market: string; spread: string} {
        return {implied: figureOf(html, IMPLIED), market: figureOf(html, MARKET), spread: figureOf(html, SPREAD)};
    }

    beforeEach(() => {
        // The expected digits are typed: the premise that the tooltip is written en-US, checked.
        expect(uiLocale(), 'control: an English UI on the en-US browser this file pins is written en-US').toBe('en-US');
    });

    it('1,000,000 VND into 41.20 USD: implied rate 0.0000412, market rate 0.0000391, spread +0.0000021 — not 0.0000, 0.0000, +0.0000', () => {
        const info = computeFxConversionInfo(-1_000_000, 'VND', 41.2, 'USD');
        if (!info) throw new Error('Expected non-null FX conversion info');
        const data = buildFxTooltipData(info, {date: '2026-10-16', rate: 0.0000391, backwardFillInfo: null});
        if (data.marketRate === null || data.spread === null) throw new Error('Expected a market rate and a spread');
        premise(data.impliedRate, '0.0000412', '0.0000');
        premise(data.marketRate, '0.0000391', '0.0000');
        premise(data.spread.absolute, '+0.0000021', '+0.0000', {signed: true});

        const figures = figuresOf(buildFxTooltipHtml(data, t));

        expect.soft(figures.implied, 'the implied rate (today 0.0000)').toBe('0.0000412');
        expect.soft(figures.market, 'the market rate (today 0.0000)').toBe('0.0000391');
        expect.soft(figures.spread, 'the spread (today +0.0000)').toBe('+0.0000021');
    });

    it('a spread below the market, -0.0000021, reads -0.0000021, not -0.0000', () => {
        premise(-0.0000021, '-0.0000021', '-0.0000', {signed: true});

        const html = buildFxTooltipHtml({impliedRate: 0.0000391, base: 'VND', quote: 'USD', marketRate: 0.0000412, marketDate: null, staleDays: null, spread: {absolute: -0.0000021, percent: -5.1}}, t);

        expect(figureOf(html, SPREAD), 'the spread (today -0.0000)').toBe('-0.0000021');
    });

    it('guard: EUR→USD at 1.0823 against 1.0801 reads 1.0823, 1.0801 and +0.0022, and a zero spread 0.0000 with no sign — as today', () => {
        premise(1.0823, '1.0823', '1.0823');
        premise(1.0801, '1.0801', '1.0801');
        premise(0.0022, '+0.0022', '+0.0022', {signed: true});
        premise(0, '0.0000', '0.0000', {signed: true});

        const wide = buildFxTooltipHtml({impliedRate: 1.0823, base: 'EUR', quote: 'USD', marketRate: 1.0801, marketDate: null, staleDays: null, spread: {absolute: 0.0022, percent: 0.2037}}, t);
        const flat = buildFxTooltipHtml({impliedRate: 1.0801, base: 'EUR', quote: 'USD', marketRate: 1.0801, marketDate: null, staleDays: null, spread: {absolute: 0, percent: 0}}, t);

        expect({wide: figuresOf(wide), flat: figuresOf(flat)}).toEqual({
            wide: {implied: '1.0823', market: '1.0801', spread: '+0.0022'},
            flat: {implied: '1.0801', market: '1.0801', spread: '0.0000'},
        });
    });
});
