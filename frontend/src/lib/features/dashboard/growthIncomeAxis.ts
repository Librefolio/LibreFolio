/**
 * The lower edge of the Income chart's y axis (G4, B9).
 *
 * Income draws bars that stand on zero, with the costs hanging below it. ECharts picks the lower edge itself, always a whole tick below the
 * lowest bar: with costs of 80 € the axis jumped to −2k, and the bars were crushed against the top. The edge is set here instead: just below
 * the largest cost, at a small round number; zero when there are no costs. The grid, `containLabel` and the zero line stay ECharts'.
 *
 * It computes no financial quantity: it only chooses where an axis stops, from the extent ECharts hands its `min` callback.
 *
 * @module features/dashboard/growthIncomeAxis
 */

/** How far below the largest cost the edge goes at least: a tenth, so the bar does not touch it. */
export const INCOME_AXIS_MARGIN = 0.1;

/**
 * A share of the axis' span the edge keeps below zero at least: the edge is labelled, and a cost of 20 € under bars of 20 000 € would put its
 * label on top of the zero's. A twentieth of the span is about the height of a label.
 */
export const INCOME_AXIS_MIN_SHARE = 0.05;

/** The mantissas a round edge may have, times a power of ten: 90, 1.5k, 25k. Fine enough that the edge stays near the cost. */
const ROUND_MANTISSAS = [1, 1.2, 1.5, 2, 2.5, 3, 3.5, 4, 4.5, 5, 6, 7, 8, 9, 10] as const;

/**
 * The lower edge for data from `dataMin` to `dataMax`: 0 when nothing hangs below zero (or the value is not a finite number), else a small
 * round negative number a little below the lowest value (and never closer to zero than `INCOME_AXIS_MIN_SHARE` of the span).
 */
export function incomeAxisMin(dataMin: number, dataMax: number = 0): number {
    if (!Number.isFinite(dataMin) || dataMin >= 0) return 0;
    const span = Number.isFinite(dataMax) && dataMax > dataMin ? dataMax - dataMin : 0;
    const padded = Math.max(Math.abs(dataMin) * (1 + INCOME_AXIS_MARGIN), span * INCOME_AXIS_MIN_SHARE);
    const magnitude = 10 ** Math.floor(Math.log10(padded));
    const mantissa = ROUND_MANTISSAS.find((candidate) => candidate >= padded / magnitude - 1e-9) ?? 10;
    // Rounded to a few digits: 1.2 × 1000 must not print 1200.0000000000001.
    return -Number((mantissa * magnitude).toPrecision(12));
}
