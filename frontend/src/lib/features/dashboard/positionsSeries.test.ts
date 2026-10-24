/**
 * Unit tests for positionsSeries — the pure mapping behind the Dashboard's per-position return chart
 * (Y5-2, #48): the backend's `positions-series` answer and the Dashboard history in, chart lines out.
 *
 * The backend owns every figure (P&L, P&L %, base); the only step made here is a presentation shift:
 * the percentage view is «base 100», `100 * (1 + pnl_percent)` with `pnl_percent` a FRACTION (0.12 is
 * +12 %, drawn at 112). The portfolio line comes from the Dashboard history (`twrr`, `total_pnl`), not
 * from the positions' P&L, and says so by being its own `kind`.
 *
 * Pure tests only: no DOM, no ECharts. Amounts are decimals sent as strings, as the generated client
 * gives them; expectations on shifted fractions use `toBeCloseTo` (binary floats), the rest are exact.
 *
 * @vitest-environment node
 */

import {describe, expect, it} from 'vitest';
import {MAX_CHART_POSITIONS, PORTFOLIO_LINE_ID, lineValue, portfolioLine, positionLine, positionLineId, positionLines, rankAssetsByWeight, selectionKeys, type HistoryPointLike, type PositionSeries, type PositionSeriesPoint, type PositionsSeriesResponse} from './positionsSeries';
import {makePositionKey} from '$lib/utils/core/positionKey';

// =============================================================================
// Fixtures
// =============================================================================

function point(date: string, overrides: Partial<PositionSeriesPoint> = {}): PositionSeriesPoint {
    return {
        date,
        quantity: '10',
        market_value: '1100',
        cost_basis: '1000',
        pnl: '100',
        base: '1000',
        pnl_percent: '0.1',
        valuation_source: 'MARKET_PRICE',
        complete: true,
        ...overrides,
    };
}

function series(overrides: Partial<PositionSeries> = {}): PositionSeries {
    return {
        key: {asset_id: 12, broker_id: 3},
        asset_name: 'Acme Corp',
        asset_ticker: 'ACME',
        broker_name: 'Broker One',
        first_date: '2026-01-02',
        last_date: '2026-01-04',
        held_at_start: true,
        held_at_end: true,
        closed_on: null,
        complete: true,
        points: [point('2026-01-02'), point('2026-01-03', {pnl: '-50', pnl_percent: '-0.05'}), point('2026-01-04', {pnl: '0', pnl_percent: '0'})],
        ...overrides,
    };
}

function response(list: PositionSeries[]): PositionsSeriesResponse {
    return {currency: 'EUR', date_from: '2026-01-02', date_to: '2026-01-04', series: list, missing_fx_pairs: []};
}

function historyPoint(date: string, amount: string, twrr?: string | null): HistoryPointLike {
    return {date, total_pnl: {code: 'EUR', amount}, ...(twrr === undefined ? {} : {twrr})};
}

/** The values of a line, in order — null where the line breaks. */
const valuesOf = (line: {points: Array<{value: number | null}>}): Array<number | null> => line.points.map((p) => p.value);

// =============================================================================
// Constants and ids
// =============================================================================

describe('positionsSeries — constants and line ids', () => {
    it('caps the chart at 50 positions and names the portfolio line «portfolio»', () => {
        expect(MAX_CHART_POSITIONS).toBe(50);
        expect(PORTFOLIO_LINE_ID).toBe('portfolio');
    });

    it('builds the line id with the shared makePositionKey', () => {
        expect(positionLineId({asset_id: 12, broker_id: 3})).toBe('12-3');
        expect(positionLineId({asset_id: 12, broker_id: 3})).toBe(makePositionKey(12, 3));
    });

    it('collapses a null broker to 0, as makePositionKey does', () => {
        expect(positionLineId({asset_id: 12, broker_id: null})).toBe('12-0');
    });
});

// =============================================================================
// lineValue
// =============================================================================

describe('positionsSeries — lineValue', () => {
    it('absolute: the P&L as a number', () => {
        expect(lineValue({pnl: '123.45', pnl_percent: '0.5'}, 'absolute')).toBe(123.45);
        expect(lineValue({pnl: '-7', pnl_percent: null}, 'absolute')).toBe(-7);
        expect(lineValue({pnl: '0', pnl_percent: null}, 'absolute')).toBe(0);
    });

    it('percentage: «base 100», the fraction shifted onto 100', () => {
        expect(lineValue({pnl: '120', pnl_percent: '0.12'}, 'percentage')).toBeCloseTo(112, 9);
        expect(lineValue({pnl: '-50', pnl_percent: '-0.05'}, 'percentage')).toBeCloseTo(95, 9);
        expect(lineValue({pnl: '0', pnl_percent: '0'}, 'percentage')).toBe(100);
        expect(lineValue({pnl: '1', pnl_percent: '1'}, 'percentage')).toBe(200);
    });

    it('percentage: a null pnl_percent (the backend had no base) is a gap, never 100', () => {
        expect(lineValue({pnl: '0', pnl_percent: null}, 'percentage')).toBeNull();
    });

    it('absolute: a null pnl is a gap, never 0', () => {
        expect(lineValue({pnl: null, pnl_percent: '0.1'}, 'absolute')).toBeNull();
    });

    it('each view reads only its own field', () => {
        expect(lineValue({pnl: null, pnl_percent: '0.1'}, 'percentage')).toBeCloseTo(110, 9);
        expect(lineValue({pnl: '5', pnl_percent: null}, 'absolute')).toBe(5);
    });

    it('a field that is not a finite number is a gap', () => {
        expect(lineValue({pnl: 'Infinity', pnl_percent: 'NaN'}, 'absolute')).toBeNull();
        expect(lineValue({pnl: 'Infinity', pnl_percent: 'NaN'}, 'percentage')).toBeNull();
        expect(lineValue({pnl: 'not a number', pnl_percent: '-Infinity'}, 'percentage')).toBeNull();
    });
});

// =============================================================================
// positionLine / positionLines
// =============================================================================

describe('positionsSeries — positionLine', () => {
    it('maps a series to a position line: id, points in order, flags', () => {
        const line = positionLine(series(), 'absolute');
        expect(line.id).toBe('12-3');
        expect(line.kind).toBe('position');
        expect(line.points.map((p) => p.date)).toEqual(['2026-01-02', '2026-01-03', '2026-01-04']);
        expect(valuesOf(line)).toEqual([100, -50, 0]);
        expect(line.closedOn).toBeNull();
        expect(line.complete).toBe(true);
    });

    it('the percentage view shifts the same points onto 100', () => {
        const line = positionLine(series(), 'percentage');
        const values = valuesOf(line);
        expect(values[0]).toBeCloseTo(110, 9);
        expect(values[1]).toBeCloseTo(95, 9);
        expect(values[2]).toBe(100);
    });

    it('keeps a null value as null, in place, so the line breaks there', () => {
        const line = positionLine(series({points: [point('2026-01-02'), point('2026-01-03', {pnl: null, pnl_percent: null}), point('2026-01-04', {pnl: '30', pnl_percent: '0.03'})]}), 'absolute');
        expect(valuesOf(line)).toEqual([100, null, 30]);
        expect(line.points).toHaveLength(3);
    });

    it('label: the ticker when there is one, then « · » and the broker name', () => {
        expect(positionLine(series(), 'absolute').label).toBe('ACME · Broker One');
    });

    it('label: the asset name when the ticker is absent or null', () => {
        expect(positionLine(series({asset_ticker: null}), 'absolute').label).toBe('Acme Corp · Broker One');
        expect(positionLine(series({asset_ticker: undefined}), 'absolute').label).toBe('Acme Corp · Broker One');
    });

    it('label: no « · » suffix when the broker name is null (a broker-less position)', () => {
        const line = positionLine(series({key: {asset_id: 12, broker_id: null}, broker_name: null}), 'absolute');
        expect(line.label).toBe('ACME');
        expect(line.label).not.toContain(' · ');
        expect(line.id).toBe('12-0');
    });

    it('carries closed_on and complete from the series', () => {
        const line = positionLine(series({closed_on: '2026-01-03', held_at_end: false, complete: false}), 'absolute');
        expect(line.closedOn).toBe('2026-01-03');
        expect(line.complete).toBe(false);
    });

    it('an empty series gives a line with no points', () => {
        const line = positionLine(series({points: [], first_date: null, last_date: null}), 'percentage');
        expect(line.points).toEqual([]);
        expect(line.kind).toBe('position');
    });
});

describe('positionsSeries — positionLines', () => {
    it('one line per series, in the order of the response', () => {
        const a = series({key: {asset_id: 5, broker_id: 1}});
        const b = series({key: {asset_id: 2, broker_id: null}, broker_name: null});
        const c = series({key: {asset_id: 9, broker_id: 4}});
        expect(positionLines(response([a, b, c]), 'absolute').map((l) => l.id)).toEqual(['5-1', '2-0', '9-4']);
    });

    it('the view reaches every line', () => {
        const lines = positionLines(response([series(), series({key: {asset_id: 2, broker_id: 1}})]), 'percentage');
        for (const line of lines) expect(valuesOf(line)[2]).toBe(100);
    });

    it('an empty response gives no lines', () => {
        expect(positionLines(response([]), 'absolute')).toEqual([]);
    });

    it('null and undefined give no lines', () => {
        expect(positionLines(null, 'absolute')).toEqual([]);
        expect(positionLines(undefined, 'percentage')).toEqual([]);
    });
});

// =============================================================================
// portfolioLine
// =============================================================================

describe('positionsSeries — portfolioLine', () => {
    const history: HistoryPointLike[] = [historyPoint('2026-01-02', '500', '0'), historyPoint('2026-01-03', '650.5', '0.02'), historyPoint('2026-01-04', '400', '-0.015')];

    it('absolute: total P&L minus the first point’s, so the window starts at 0', () => {
        const line = portfolioLine(history, 'absolute', 'Portfolio');
        expect(line).not.toBeNull();
        const values = valuesOf(line!);
        expect(values[0]).toBe(0);
        expect(values[1]).toBeCloseTo(150.5, 9);
        expect(values[2]).toBeCloseTo(-100, 9);
    });

    it('absolute: the first point is 0 whatever the starting P&L is (even negative)', () => {
        const line = portfolioLine([historyPoint('2026-01-02', '-300'), historyPoint('2026-01-03', '-250')], 'absolute', 'P');
        const values = valuesOf(line!);
        expect(values[0]).toBe(0);
        expect(values[1]).toBeCloseTo(50, 9);
    });

    it('percentage: «base 100» of the TWRR fraction', () => {
        const values = valuesOf(portfolioLine(history, 'percentage', 'Portfolio')!);
        expect(values[0]).toBe(100);
        expect(values[1]).toBeCloseTo(102, 9);
        expect(values[2]).toBeCloseTo(98.5, 9);
    });

    it('percentage: a point without twrr (absent or null) is a gap', () => {
        const line = portfolioLine([historyPoint('2026-01-02', '0', '0'), historyPoint('2026-01-03', '5'), historyPoint('2026-01-04', '9', null), historyPoint('2026-01-05', '9', '0.1')], 'percentage', 'P');
        const values = valuesOf(line!);
        expect(values[0]).toBe(100);
        expect(values[1]).toBeNull();
        expect(values[2]).toBeNull();
        expect(values[3]).toBeCloseTo(110, 9);
    });

    it('percentage does not need total_pnl, absolute does not need twrr', () => {
        const noTwrr = portfolioLine([historyPoint('2026-01-02', '10'), historyPoint('2026-01-03', '30')], 'absolute', 'P');
        expect(valuesOf(noTwrr!)).toEqual([0, 20]);
    });

    it('is the portfolio line: its id, its kind, the label it was given, never closed, complete', () => {
        const line = portfolioLine(history, 'absolute', 'My label');
        expect(line!.id).toBe(PORTFOLIO_LINE_ID);
        expect(line!.kind).toBe('portfolio');
        expect(line!.label).toBe('My label');
        expect(line!.closedOn).toBeNull();
        expect(line!.complete).toBe(true);
    });

    it('keeps the dates of the history, in order', () => {
        expect(portfolioLine(history, 'percentage', 'P')!.points.map((p) => p.date)).toEqual(['2026-01-02', '2026-01-03', '2026-01-04']);
    });

    it('an empty history is no line at all (null), in both views', () => {
        expect(portfolioLine([], 'absolute', 'P')).toBeNull();
        expect(portfolioLine([], 'percentage', 'P')).toBeNull();
    });

    it('does not mutate the history it is given', () => {
        const copy = JSON.parse(JSON.stringify(history));
        portfolioLine(history, 'absolute', 'P');
        portfolioLine(history, 'percentage', 'P');
        expect(history).toEqual(copy);
    });
});

// =============================================================================
// selectionKeys
// =============================================================================

describe('positionsSeries — selectionKeys', () => {
    it('one key per row, in the order given', () => {
        expect(
            selectionKeys([
                {assetId: 7, brokerId: 2},
                {assetId: 3, brokerId: 1},
            ]),
        ).toEqual([
            {asset_id: 7, broker_id: 2},
            {asset_id: 3, broker_id: 1},
        ]);
    });

    it('keeps a null broker as null (not 0)', () => {
        expect(selectionKeys([{assetId: 7, brokerId: null}])).toEqual([{asset_id: 7, broker_id: null}]);
    });

    it('drops a duplicate (assetId, brokerId), keeping the first occurrence in place', () => {
        const keys = selectionKeys([
            {assetId: 1, brokerId: 1},
            {assetId: 2, brokerId: 1},
            {assetId: 1, brokerId: 1},
            {assetId: 1, brokerId: null},
            {assetId: 1, brokerId: null},
        ]);
        expect(keys).toEqual([
            {asset_id: 1, broker_id: 1},
            {asset_id: 2, broker_id: 1},
            {asset_id: 1, broker_id: null},
        ]);
    });

    it('the same asset at two brokers is two keys', () => {
        expect(
            selectionKeys([
                {assetId: 1, brokerId: 1},
                {assetId: 1, brokerId: 2},
            ]),
        ).toHaveLength(2);
    });

    it('is capped at MAX_CHART_POSITIONS by default, keeping the first ones', () => {
        const rows = Array.from({length: MAX_CHART_POSITIONS + 20}, (_, i) => ({assetId: i + 1, brokerId: 1}));
        const keys = selectionKeys(rows);
        expect(keys).toHaveLength(MAX_CHART_POSITIONS);
        expect(keys[0]).toEqual({asset_id: 1, broker_id: 1});
        expect(keys[MAX_CHART_POSITIONS - 1]).toEqual({asset_id: MAX_CHART_POSITIONS, broker_id: 1});
    });

    it('an explicit max wins over the default', () => {
        const rows = Array.from({length: 10}, (_, i) => ({assetId: i + 1, brokerId: null}));
        expect(selectionKeys(rows, 3).map((k) => k.asset_id)).toEqual([1, 2, 3]);
    });

    it('the cap counts distinct keys: duplicates do not use the budget', () => {
        const keys = selectionKeys(
            [
                {assetId: 1, brokerId: 1},
                {assetId: 1, brokerId: 1},
                {assetId: 2, brokerId: 1},
                {assetId: 3, brokerId: 1},
            ],
            2,
        );
        expect(keys.map((k) => k.asset_id)).toEqual([1, 2]);
    });

    it('nothing in, nothing out', () => {
        expect(selectionKeys([])).toEqual([]);
    });
});

// =============================================================================
// rankAssetsByWeight
// =============================================================================

describe('positionsSeries — rankAssetsByWeight', () => {
    const noHistory: Array<{date: string; components: Array<{id: number | null; amount: number}>}> = [];

    it('assets held today: rank 0 is the heaviest, descending by amount', () => {
        const rank = rankAssetsByWeight(
            [
                {id: 10, amount: 100},
                {id: 20, amount: 300},
                {id: 30, amount: 200},
            ],
            noHistory,
        );
        expect(rank.get(20)).toBe(0);
        expect(rank.get(30)).toBe(1);
        expect(rank.get(10)).toBe(2);
        expect(rank.size).toBe(3);
    });

    it('ties on amount: the lower id first', () => {
        const rank = rankAssetsByWeight(
            [
                {id: 9, amount: 50},
                {id: 4, amount: 50},
                {id: 6, amount: 50},
            ],
            noHistory,
        );
        expect(rank.get(4)).toBe(0);
        expect(rank.get(6)).toBe(1);
        expect(rank.get(9)).toBe(2);
    });

    it('the Liquidity slice (id null) has no rank and does not take one', () => {
        const rank = rankAssetsByWeight(
            [
                {id: null, amount: 9999},
                {id: 1, amount: 10},
                {id: 2, amount: 5},
            ],
            noHistory,
        );
        expect(rank.get(1)).toBe(0);
        expect(rank.get(2)).toBe(1);
        expect(rank.size).toBe(2);
    });

    it('a slice with no amount (0 or negative) is not held today', () => {
        const rank = rankAssetsByWeight(
            [
                {id: 1, amount: 10},
                {id: 2, amount: 0},
                {id: 3, amount: -5},
            ],
            noHistory,
        );
        expect(rank.get(1)).toBe(0);
        expect(rank.has(2)).toBe(false);
        expect(rank.has(3)).toBe(false);
    });

    it('assets that are only in the history come after the held ones', () => {
        const rank = rankAssetsByWeight(
            [{id: 1, amount: 1}],
            [
                {
                    date: '2026-01-01',
                    components: [
                        {id: 1, amount: 500},
                        {id: 2, amount: 900},
                    ],
                },
            ],
        );
        expect(rank.get(1)).toBe(0);
        expect(rank.get(2)).toBe(1);
    });

    it('closed assets: the most recently closed first (the last date with an amount decides)', () => {
        const rank = rankAssetsByWeight(
            [{id: 1, amount: 100}],
            [
                {
                    date: '2026-01-01',
                    components: [
                        {id: 2, amount: 10},
                        {id: 3, amount: 10},
                        {id: 4, amount: 10},
                    ],
                },
                {
                    date: '2026-02-01',
                    components: [
                        {id: 3, amount: 10},
                        {id: 4, amount: 10},
                    ],
                },
                {
                    date: '2026-03-01',
                    components: [{id: 4, amount: 10}],
                },
            ],
        );
        // held: 1; then 4 (last seen 03-01), 3 (02-01), 2 (01-01)
        expect(rank.get(1)).toBe(0);
        expect(rank.get(4)).toBe(1);
        expect(rank.get(3)).toBe(2);
        expect(rank.get(2)).toBe(3);
    });

    it('the history order of the input does not matter: dates decide', () => {
        const rank = rankAssetsByWeight(
            [],
            [
                {date: '2026-03-01', components: [{id: 4, amount: 10}]},
                {date: '2026-01-01', components: [{id: 2, amount: 10}]},
                {date: '2026-02-01', components: [{id: 3, amount: 10}]},
            ],
        );
        expect(rank.get(4)).toBe(0);
        expect(rank.get(3)).toBe(1);
        expect(rank.get(2)).toBe(2);
    });

    it('closed assets with the same last date: the lower id first', () => {
        const rank = rankAssetsByWeight(
            [],
            [
                {
                    date: '2026-01-05',
                    components: [
                        {id: 8, amount: 1},
                        {id: 3, amount: 1},
                        {id: 5, amount: 1},
                    ],
                },
            ],
        );
        expect(rank.get(3)).toBe(0);
        expect(rank.get(5)).toBe(1);
        expect(rank.get(8)).toBe(2);
    });

    it('a day with a zero or negative amount is not a day the asset was held', () => {
        const rank = rankAssetsByWeight(
            [],
            [
                {date: '2026-01-01', components: [{id: 2, amount: 10}]},
                {date: '2026-06-01', components: [{id: 2, amount: 0}]},
                {date: '2026-03-01', components: [{id: 3, amount: 10}]},
                {date: '2026-06-02', components: [{id: 3, amount: -4}]},
            ],
        );
        // 3 was last held on 03-01, 2 on 01-01: 3 closed more recently
        expect(rank.get(3)).toBe(0);
        expect(rank.get(2)).toBe(1);
    });

    it('an asset held today is ranked by today’s amount, not by its history', () => {
        const rank = rankAssetsByWeight(
            [
                {id: 1, amount: 10},
                {id: 2, amount: 20},
            ],
            [
                {
                    date: '2026-01-01',
                    components: [
                        {id: 1, amount: 9000},
                        {id: 2, amount: 1},
                    ],
                },
            ],
        );
        expect(rank.get(2)).toBe(0);
        expect(rank.get(1)).toBe(1);
        expect(rank.size).toBe(2);
    });

    it('the Liquidity slice in the history gets no rank either', () => {
        const rank = rankAssetsByWeight(
            [],
            [
                {
                    date: '2026-01-01',
                    components: [
                        {id: null, amount: 1000},
                        {id: 7, amount: 1},
                    ],
                },
            ],
        );
        expect(rank.get(7)).toBe(0);
        expect(rank.size).toBe(1);
    });

    it('ranks are consecutive from 0 across the two groups', () => {
        const rank = rankAssetsByWeight(
            [
                {id: 1, amount: 3},
                {id: 2, amount: 2},
            ],
            [
                {date: '2026-01-01', components: [{id: 5, amount: 1}]},
                {date: '2026-02-01', components: [{id: 6, amount: 1}]},
            ],
        );
        expect([...rank.values()].sort((a, b) => a - b)).toEqual([0, 1, 2, 3]);
        expect(rank.get(6)).toBe(2);
        expect(rank.get(5)).toBe(3);
    });

    it('empty inputs give an empty map', () => {
        expect(rankAssetsByWeight([], []).size).toBe(0);
    });
});
