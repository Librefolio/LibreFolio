/**
 * riskReturnLevel — unit tests for the decisions behind the one risk/return table, chart and notes
 * that the portfolio's L3 (Dashboard, a broker's page) and Asset Global's L3° share.
 *
 * What is pinned here is what the developer approved in his visual reviews 3 and 4 (06/10/2026,
 * «tutto perfetto»), at the level where it is decided rather than drawn:
 *
 *  - **a column is as wide as its title** (`headerWidth`): DataTable writes its titles upper-case, on
 *    one line, 12 px semibold with 0.025em between letters, inside 8 + 8 px of padding, a 4 px gap and
 *    a 14 px sort icon. So the width is the title measured upper-case, plus 0.3 px per letter, rounded
 *    up, plus 36 px of chrome — and a longer title opens a wider column («peso è troppo larga»);
 *  - **every row and every dot has one id, and they map onto each other** (`rowIdOf`, `pointIdOf`,
 *    `rowIdForPoint`): an asset is `<assetId>` in the table and `asset-<assetId>` on the chart — a
 *    benchmark the reader holds included; the portfolio, added for the reference, is `ref-portfolio`
 *    and `portfolio`; a benchmark nobody holds, added too, is `ref-<assetId>` and `benchmark`;
 *  - **the references open the table** (`referenceRowsFirst`): the portfolio, then the benchmark, then
 *    every other row in the order the page gave it, untouched;
 *  - **the notes under the chart, in reading order, each only where it applies** (`riskReturnNotes`):
 *    what is not plotted, what being above the line means, which return the dots use, that it comes
 *    from prices alone, where the line comes from, what a dot's size means. The two about the line need
 *    a line, so a chart without an anchor — the lab before a benchmark is placed — never describes one,
 *    and the lab with a benchmark describes the line through it;
 *  - **a share is said only when it is a real, strictly positive number** (`outsideParts`).
 *
 * Every figure, name and id below is invented here. `measure` is a stand-in for the page's canvas:
 * jsdom has none, and what is under test is the arithmetic around the measurement, not the font.
 */
import {describe, expect, it} from 'vitest';

import {headerWidth, outsideParts, pointIdOf, referenceRowsFirst, riskReturnNotes, rowIdForPoint, rowIdOf, type RiskReturnCapabilities, type RiskReturnNote, type RiskReturnOutside, type RiskReturnRow} from './riskReturnLevel';

/** An ordinary asset row: no role, not added. */
function assetRow(assetId: number, extra: Partial<RiskReturnRow> = {}): RiskReturnRow {
    return {assetId, name: `Invented asset ${assetId}`, volatility: 0.1, expectedReturn: 0.05, ...extra};
}

/** The portfolio's own row, as `buildRiskReturnRows` adds it: asset id 0, which is no asset's. */
const PORTFOLIO: RiskReturnRow = {assetId: 0, name: 'Invented portfolio', role: 'portfolio', added: true, weight: 1, volatility: 0.118, expectedReturn: 0.071};
/** A benchmark nobody holds: a row added for the comparison, under the benchmark's asset id. */
const ADDED_BENCHMARK: RiskReturnRow = {assetId: 90, name: 'Invented index', role: 'benchmark', added: true, isReference: true, weight: null, volatility: 0.15, expectedReturn: 0.058};
/** A benchmark the reader holds: the holding's own row, marked, not added. */
const HELD_BENCHMARK: RiskReturnRow = assetRow(2, {role: 'benchmark', isReference: true, weight: 0.35});

describe('headerWidth — a figure column as wide as its title, and no wider', () => {
    it('measures the title as DataTable draws it: upper-case, in the reader’s own letters', () => {
        const measured: string[] = [];
        const measure = (text: string): number => {
            measured.push(text);
            return 0;
        };

        headerWidth('Ann. return', measure);
        headerWidth('Volatilità', measure);

        expect(measured, 'the measure must be handed the title upper-case — DataTable writes every title in capitals, and capitals are wider').toEqual(['ANN. RETURN', 'VOLATILITÀ']);
    });

    it('adds the letter spacing, 0.3 px per letter of the title', () => {
        // The measure says 0 for every title, so what is left is the spacing (and the chrome, the same for both).
        const ten = headerWidth('ABCDEFGHIJ', () => 0);
        const twenty = headerWidth('ABCDEFGHIJKLMNOPQRST', () => 0);

        expect(twenty - ten, 'ten more letters must add 3 px: DataTable spaces its titles 0.025em apart, 0.3 px at 12 px').toBe(3);
    });

    it('adds the 36 px DataTable draws around a title: padding, gap, sort icon, and 2 px so rounding never clips a letter', () => {
        expect(
            headerWidth('', () => 0),
            'an empty title still needs the chrome around it',
        ).toBe(36);
    });

    it('rounds the measured title up, so a fraction of a pixel never clips the last letter', () => {
        const atRest = headerWidth('', () => 0);

        expect(headerWidth('', () => 10.01) - atRest, '10.01 px of title must take 11 px of column, not 10').toBe(11);
        expect(headerWidth('', () => 10) - atRest, 'a whole number of pixels is not rounded past itself').toBe(10);
    });

    it('opens a longer title wider, and the same title at the same width', () => {
        // A stand-in for the canvas: every letter is as wide as the others, so only the length differs.
        const measure = (text: string): number => text.length * 7;

        expect(headerWidth('Correlation', measure)).toBeGreaterThan(headerWidth('Beta', measure));
        expect(headerWidth('Volatility', measure)).toBeGreaterThan(headerWidth('Weight', measure));
        expect(headerWidth('Sharpe', measure)).toBe(headerWidth('Sharpe', measure));
    });
});

describe('rowIdOf and pointIdOf — one id per row and per dot', () => {
    it('an asset is its own id in the table and asset-<id> on the chart', () => {
        expect(rowIdOf(assetRow(7))).toBe('7');
        expect(pointIdOf(assetRow(7))).toBe('asset-7');
    });

    it('the portfolio, added for the reference, is ref-portfolio in the table and portfolio on the chart', () => {
        expect(rowIdOf(PORTFOLIO), 'the portfolio is no asset: its row id names its role, not asset id 0').toBe('ref-portfolio');
        expect(pointIdOf(PORTFOLIO)).toBe('portfolio');
    });

    it('a benchmark nobody holds, added for the comparison, is ref-<id> in the table and benchmark on the chart', () => {
        expect(rowIdOf(ADDED_BENCHMARK), 'an added row takes a ref- id, so it can never collide with the asset’s own row').toBe('ref-90');
        expect(pointIdOf(ADDED_BENCHMARK)).toBe('benchmark');
    });

    it('a benchmark the reader holds keeps its holding’s ids: its own in the table, asset-<id> on the chart', () => {
        expect(rowIdOf(HELD_BENCHMARK), 'a held benchmark is one of the assets: it keeps its row').toBe('2');
        expect(pointIdOf(HELD_BENCHMARK), 'and its dot is its holding’s, only drawn as the benchmark').toBe('asset-2');
    });
});

describe('rowIdForPoint — a dot selects its row, and a dot without one selects nothing', () => {
    it('maps every dot back to the row it stands for', () => {
        const rows = [assetRow(1), PORTFOLIO, assetRow(3), ADDED_BENCHMARK];

        expect(rowIdForPoint('portfolio', rows)).toBe('ref-portfolio');
        expect(rowIdForPoint('benchmark', rows)).toBe('ref-90');
        expect(rowIdForPoint('asset-1', rows)).toBe('1');
        expect(rowIdForPoint('asset-3', rows)).toBe('3');
        // Every row, both ways: the table and the chart name one thing by two ids that agree.
        for (const row of rows) expect(rowIdForPoint(pointIdOf(row), rows), `the round trip through the chart lost row ${rowIdOf(row)}`).toBe(rowIdOf(row));
    });

    it('a held benchmark answers to its holding’s dot, and no dot called benchmark is left to answer', () => {
        const rows = [PORTFOLIO, HELD_BENCHMARK, assetRow(1)];

        expect(rowIdForPoint('asset-2', rows)).toBe('2');
        expect(rowIdForPoint('benchmark', rows), 'a held benchmark has no separate dot: benchmark names no row here').toBeNull();
    });

    it('a dot whose row is not in the table selects nothing', () => {
        const rows = [assetRow(1), assetRow(3)];

        // Presence first: the same rows answer for a dot they hold.
        expect(rowIdForPoint('asset-1', rows)).toBe('1');
        expect(rowIdForPoint('asset-99', rows)).toBeNull();
        expect(rowIdForPoint('portfolio', rows), 'the lab has no portfolio row: its dot, were there one, would select nothing').toBeNull();
        expect(rowIdForPoint('benchmark', rows)).toBeNull();
    });
});

describe('referenceRowsFirst — the portfolio, then the benchmark, then the rest as given', () => {
    it('opens with the portfolio and the benchmark wherever the page put them', () => {
        const ordered = referenceRowsFirst([assetRow(5), ADDED_BENCHMARK, assetRow(3), PORTFOLIO, assetRow(9)]);

        expect(ordered.map(rowIdOf)).toEqual(['ref-portfolio', 'ref-90', '5', '3', '9']);
    });

    it('moves a held benchmark up to second, past heavier holdings', () => {
        const ordered = referenceRowsFirst([PORTFOLIO, assetRow(1, {weight: 0.6}), assetRow(4, {weight: 0.4}), HELD_BENCHMARK]);

        expect(ordered.map(rowIdOf)).toEqual(['ref-portfolio', '2', '1', '4']);
    });

    it('leaves every other row in the order the page gave it — the reader sorts, the system never ranks', () => {
        // Neither by id nor by name: any order the function invented would show here.
        const given = [assetRow(8), assetRow(2), assetRow(11), assetRow(5)];

        expect(referenceRowsFirst(given).map(rowIdOf)).toEqual(['8', '2', '11', '5']);
        expect(referenceRowsFirst([assetRow(8), PORTFOLIO, assetRow(2), assetRow(11), assetRow(5)]).map(rowIdOf)).toEqual(['ref-portfolio', '8', '2', '11', '5']);
    });

    it('hands back a new list and leaves the page’s own alone', () => {
        const given = [assetRow(5), PORTFOLIO];
        const ordered = referenceRowsFirst(given);

        expect(ordered).not.toBe(given);
        expect(given.map(rowIdOf), 'the caller’s list was reordered in place').toEqual(['5', 'ref-portfolio']);
    });
});

describe('riskReturnNotes — one idea per line, in reading order, each only where it applies', () => {
    const PORTFOLIO_PAGE: RiskReturnCapabilities = {weight: true, ratios: true, benchmark: true};
    const LAB: RiskReturnCapabilities = {ratios: true, benchmark: true};
    const CASH_AND_UNPRICED: RiskReturnOutside = {cash: 0.046, unpriced: 0.004};

    it('on a portfolio page with a line and something not plotted, all six, in the reviewed order', () => {
        expect(riskReturnNotes({lineAnchor: 'benchmark', capabilities: PORTFOLIO_PAGE, outside: CASH_AND_UNPRICED})).toEqual(['outside', 'above', 'return', 'priceOnly', 'line', 'size']);
        expect(riskReturnNotes({lineAnchor: 'portfolio', capabilities: PORTFOLIO_PAGE, outside: CASH_AND_UNPRICED}), 'the line through the portfolio is described like the one through the benchmark').toEqual(['outside', 'above', 'return', 'priceOnly', 'line', 'size']);
    });

    it('says what is not plotted only when something is: cash, unpriced holdings, or both', () => {
        expect(riskReturnNotes({lineAnchor: 'portfolio', capabilities: PORTFOLIO_PAGE, outside: {cash: 0.05, unpriced: null}})[0]).toBe('outside');
        expect(riskReturnNotes({lineAnchor: 'portfolio', capabilities: PORTFOLIO_PAGE, outside: {cash: null, unpriced: 0.004}})[0]).toBe('outside');
        expect(riskReturnNotes({lineAnchor: 'portfolio', capabilities: PORTFOLIO_PAGE, outside: {cash: null, unpriced: null}})).toEqual(['above', 'return', 'priceOnly', 'line', 'size']);
        expect(riskReturnNotes({lineAnchor: 'portfolio', capabilities: PORTFOLIO_PAGE, outside: null})).toEqual(['above', 'return', 'priceOnly', 'line', 'size']);
    });

    it('a chart with no line, no weight, nothing outside — the lab before a benchmark is placed — says only the return and that it comes from prices', () => {
        expect(riskReturnNotes({lineAnchor: null, capabilities: LAB})).toEqual(['return', 'priceOnly']);
        expect(riskReturnNotes({lineAnchor: null, capabilities: {ratios: true}})).toEqual(['return', 'priceOnly']);
    });

    /**
     * The lab draws the line once a benchmark is placed (developer's review of 06/10/2026: «non compare la
     * retta tra 0 e benchmark»): the benchmark anchors it on a plot with no portfolio (`capitalMarketLineAnchor`),
     * so the lab says what being above it means and where it comes from — and still nothing of a dot's size,
     * because its dots carry no weight.
     */
    it('in the lab with a benchmark — a line through it, no weight, nothing outside — what being above the line means, the return, prices only, where the line comes from, and no size', () => {
        const notes = riskReturnNotes({lineAnchor: 'benchmark', capabilities: LAB});

        expect(notes).toEqual(['above', 'return', 'priceOnly', 'line']);
        expect(notes, 'the lab’s dots carry no weight: nothing to say about a dot’s size').not.toContain('size');
    });

    it('never describes a line it does not draw, whatever else the page declares', () => {
        const capabilities: RiskReturnCapabilities[] = [{}, LAB, PORTFOLIO_PAGE, {weight: true}];
        const outsides: (RiskReturnOutside | null)[] = [null, CASH_AND_UNPRICED];
        for (const declared of capabilities) {
            for (const outside of outsides) {
                const notes = riskReturnNotes({lineAnchor: null, capabilities: declared, outside});
                // Presence first: the notes were drawn, so the absence is about the line and nothing else.
                expect(notes, `${JSON.stringify(declared)} / ${JSON.stringify(outside)}`).toContain('return');
                expect(
                    notes.filter((note: RiskReturnNote) => note === 'above' || note === 'line'),
                    `a chart with no line described one: ${JSON.stringify(declared)} / ${JSON.stringify(outside)}`,
                ).toEqual([]);
            }
        }
    });

    it('says what a dot’s size means only where the dots are sized by a weight', () => {
        expect(riskReturnNotes({lineAnchor: null, capabilities: {weight: true}})).toEqual(['return', 'priceOnly', 'size']);
        expect(riskReturnNotes({lineAnchor: 'portfolio', capabilities: {ratios: true, benchmark: true}})).toEqual(['above', 'return', 'priceOnly', 'line']);
    });
});

describe('outsideParts — a share is said only when it is a real, strictly positive number', () => {
    it('says each part that is there, and only that part', () => {
        expect(outsideParts({cash: 0.05, unpriced: 0.004})).toEqual({cash: true, unpriced: true});
        expect(outsideParts({cash: 0.05, unpriced: null})).toEqual({cash: true, unpriced: false});
        expect(outsideParts({cash: null, unpriced: 0.004})).toEqual({cash: false, unpriced: true});
    });

    it('says nothing of a share that is zero, negative, not a number, or unknown', () => {
        for (const share of [0, -0, -0.01, Number.NaN, Number.POSITIVE_INFINITY, null]) {
            expect(outsideParts({cash: share, unpriced: share}), `a share of ${String(share)} was said`).toEqual({cash: false, unpriced: false});
        }
        expect(outsideParts(null)).toEqual({cash: false, unpriced: false});
        expect(outsideParts(undefined)).toEqual({cash: false, unpriced: false});
    });
});
