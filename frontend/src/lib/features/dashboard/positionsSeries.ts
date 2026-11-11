/**
 * The per-position return chart's data (Y5-2, #48): the daily series of the positions the user ticked, as lines.
 *
 * The backend computes every number: a position's result since the window's start (`pnl`) and its percent on the capital
 * it employed (`pnl_percent`, a fraction), day by day (`POST /portfolio/positions-series`). This module only shapes
 * those series for a chart: the Abs view draws `pnl`, the % view draws «base 100» (`100 × (1 + pnl_percent)`), and a
 * missing value stays missing so the line breaks instead of dropping to zero.
 *
 * @financial-math-exception Presentation only, declared as `lotComparisonChartHelpers.ts` declares its aggregate. (1)
 * «Base 100» is `100 × (1 + the backend's fraction)`: a change of unit, not a measure. (2) The portfolio line is the
 * Dashboard's own history (`twrr`, `total_pnl`) moved to the window's left edge: its Abs figure is `total_pnl` minus its
 * first point, because the window is the user's and the history carries the lifetime P&L. This is not a new calculation: it
 * only moves a number the backend computed to the window's left edge, as the base 100 changes a unit. It is the Dashboard's return,
 * not the P&L of the positions on the capital they employed, and the legend says so.
 *
 * @module features/dashboard/positionsSeries
 */

import type {z} from 'zod';
import type {schemas} from '$lib/api/generated';
import {safeDecimal, safeString} from '$lib/types';
import {makePositionKey} from '$lib/features/dashboard/positionKey';
import {indexHoldingDay} from '$lib/utils/stepSeries';

/** The two views drawn from the positions' own series: the position's result in money, or its return in «base 100». */
export type PositionsSeriesView = 'absolute' | 'percentage';

/** The three views of the chart: those two, and the rolling return of the asset's price (FB-15, `positionsRolling.ts`). */
export type PositionsChartView = PositionsSeriesView | 'rolling';

/** A position asked for: an asset at one broker, or at all the brokers of the scope (`broker_id` null or absent). */
export type PositionKey = z.infer<typeof schemas.PositionKey>;

/** The answer of `POST /portfolio/positions-series`. */
export type PositionsSeriesResponse = z.infer<typeof schemas.PositionsSeriesResponse>;

/** The request of `POST /portfolio/positions-series`. */
export type PositionsSeriesQuery = z.infer<typeof schemas.PositionsSeriesQuery>;

/** The series of one asked position. */
export type PositionSeries = z.infer<typeof schemas.PositionSeries>;

/** One calendar day of a position's series; the decimals are strings, as the generated client gives them. */
export type PositionSeriesPoint = z.infer<typeof schemas.PositionSeriesPoint>;

/** One point of a line; `null` is «not known that day», never zero. */
export interface ChartPoint {
    date: string;
    value: number | null;
}

/** A line of the chart: a position's, or the portfolio's. */
export interface PositionLine {
    id: string;
    label: string;
    points: ChartPoint[];
    closedOn: string | null;
    complete: boolean;
    kind: 'position' | 'portfolio';
    /** The line is made of steps (the Dashboard's history): each point holds to the next date, drawn with `step: 'end'`. */
    stepped?: boolean;
}

/** The backend's cap on the positions of one request. */
export const MAX_CHART_POSITIONS = 50;

/** The id of the portfolio's line. */
export const PORTFOLIO_LINE_ID = 'portfolio';

/** The structural part of a Dashboard history point the portfolio line reads. */
export interface HistoryPointLike {
    /** The history is steps: the point holds from `date` to `through`, both included. */
    date: string;
    through: string;
    total_pnl: {code: string; amount: string};
    twrr?: string | null;
}

/** The broker of a key as a number, or null for the asset summed over the brokers of the scope. */
function brokerOf(key: PositionKey): number | null {
    const broker = Array.isArray(key.broker_id) ? key.broker_id[0] : key.broker_id;
    return broker ?? null;
}

/** The id of a position's line: the key its table row has. */
export function positionLineId(key: PositionKey): string {
    return makePositionKey(key.asset_id, brokerOf(key));
}

/** What a point draws in a view: its result in money, or its return in «base 100»; null when it is not known. */
export function lineValue(point: Pick<PositionSeriesPoint, 'pnl' | 'pnl_percent'>, view: PositionsSeriesView): number | null {
    if (view === 'absolute') return safeDecimal(point.pnl);
    const fraction = safeDecimal(point.pnl_percent);
    return fraction === null ? null : 100 * (1 + fraction);
}

/**
 * A position's line: the asset's name (the legend scrolls a long one, F-1), then the broker when the series is for one broker. The series is steps (each
 * holds from its `date` to its `through`): one point per step and a closing point on the last `through`, so the line reaches the
 * last day the position is known; drawn as steps.
 */
export function positionLine(series: PositionSeries, view: PositionsSeriesView): PositionLine {
    const name = series.asset_name;
    const broker = safeString(series.broker_name);
    const steps = series.points ?? [];
    const points: ChartPoint[] = steps.map((point) => ({date: point.date, value: lineValue(point, view)}));
    const last = steps[steps.length - 1];
    if (last && last.through > last.date) points.push({date: last.through, value: points[points.length - 1].value});
    return {
        id: positionLineId(series.key),
        label: broker ? `${name} · ${broker}` : name,
        points,
        closedOn: safeString(series.closed_on),
        complete: series.complete !== false,
        kind: 'position',
        stepped: true,
    };
}

/**
 * What a line says on a day, for a tooltip: the point holding the day (the last one on or before it), with its own date; null when
 * the line does not exist that day (before its first point, after its last). A stepped line reads the day the pointer is on, not the
 * drawn point nearest to it.
 */
export function lineOnDay(line: PositionLine, day: string): ChartPoint | null {
    const points = line.points;
    if (points.length === 0 || day < points[0].date || day > points[points.length - 1].date) return null;
    return points[indexHoldingDay(points, day)];
}

/** The lines of an answer, in the order the positions were asked. */
export function positionLines(response: PositionsSeriesResponse | null | undefined, view: PositionsSeriesView): PositionLine[] {
    return (response?.series ?? []).map((series) => positionLine(series, view));
}

/**
 * The portfolio's line, from the Dashboard's history: its return in «base 100» (`twrr` is a fraction), or its P&L
 * since the first day of the window. One point per step of the history and a closing point on the last day of the last step, so the line
 * reaches the end of the window; drawn as steps. Null when the history is empty.
 */
export function portfolioLine(history: ReadonlyArray<HistoryPointLike>, view: PositionsSeriesView, label: string): PositionLine | null {
    if (history.length === 0) return null;
    const origin = view === 'absolute' ? safeDecimal(history[0].total_pnl?.amount) : null;
    const points = history.map((point): ChartPoint => {
        if (view === 'percentage') {
            const fraction = safeDecimal(point.twrr);
            return {date: point.date, value: fraction === null ? null : 100 * (1 + fraction)};
        }
        const pnl = safeDecimal(point.total_pnl?.amount);
        return {date: point.date, value: pnl === null || origin === null ? null : pnl - origin};
    });
    const last = history[history.length - 1];
    const closing = points[points.length - 1];
    if (last.through > last.date) points.push({date: last.through, value: closing.value});
    return {id: PORTFOLIO_LINE_ID, label, points, closedOn: null, complete: true, kind: 'portfolio', stepped: true};
}

/** The keys to ask for the ticked rows: one per distinct position, in the order given, no more than `max`. */
export function selectionKeys(rows: ReadonlyArray<{assetId: number; brokerId: number | null}>, max: number = MAX_CHART_POSITIONS): PositionKey[] {
    const seen = new Set<string>();
    const keys: PositionKey[] = [];
    for (const row of rows) {
        const id = makePositionKey(row.assetId, row.brokerId);
        if (seen.has(id)) continue;
        seen.add(id);
        keys.push({asset_id: row.assetId, broker_id: row.brokerId});
        if (keys.length >= max) break;
    }
    return keys;
}

/**
 * The colour rank of every asset (0 = the first colour): the assets held today, the heaviest first (ties: the lower id),
 * then the ones that left the portfolio, the one closed most recently first (its last day with a positive amount decides, a step's being its `through`;
 * ties: the lower id), then the `extraIds` no list above knows (the lower id first). The Liquidity slice (no id) has no rank.
 *
 * It is the ONE place the ranks are computed: the pie, the history area and the return chart's lines all take them from here (through
 * `assetColorRanks`), so an asset wears one colour in all of them, whatever is ticked and in whatever order. A panel that draws more assets than the pie
 * (the lines of a position sold out in the period) passes them as `extraIds`: they come after every ranked asset, so the ranks the pie reads do not move.
 */
export function rankAssetsByWeight(
    today: ReadonlyArray<{id: number | null; amount: number}>,
    history: ReadonlyArray<{date: string; through?: string; components: ReadonlyArray<{id: number | null; amount: number}>}>,
    extraIds: ReadonlyArray<number> = [],
): Map<number, number> {
    const held = new Map<number, number>();
    for (const slice of today) {
        if (slice.id !== null && slice.id !== undefined && slice.amount > 0) held.set(slice.id, slice.amount);
    }
    const lastHeld = new Map<number, string>();
    for (const point of history) {
        for (const component of point.components) {
            if (component.id === null || component.id === undefined || !(component.amount > 0)) continue;
            // A step holds the asset to its last day, so that is the last day the asset was held.
            const lastDay = point.through ?? point.date;
            const previous = lastHeld.get(component.id);
            if (previous === undefined || lastDay > previous) lastHeld.set(component.id, lastDay);
        }
    }
    const ranks = new Map<number, number>();
    for (const [id] of [...held].sort((left, right) => right[1] - left[1] || left[0] - right[0])) ranks.set(id, ranks.size);
    const closed = [...lastHeld].filter(([id]) => !held.has(id)).sort((left, right) => (left[1] < right[1] ? 1 : left[1] > right[1] ? -1 : left[0] - right[0]));
    for (const [id] of closed) ranks.set(id, ranks.size);
    for (const id of [...new Set(extraIds)].sort((left, right) => left - right)) if (!ranks.has(id)) ranks.set(id, ranks.size);
    return ranks;
}

/** The structural part of a slice of the asset dimension (`allocation_by_asset`, or a component of its history) the ranks read. */
interface AssetSliceLike {
    id?: number | null;
    amount?: string | null;
}

/**
 * The ranks of the assets from what the backend sent: today's allocation by asset and, when the history was asked, its points. The one entry
 * point of the Allocation panel and of the positions panel (see `rankAssetsByWeight`).
 */
export function assetColorRanks(
    today: ReadonlyArray<AssetSliceLike>,
    history: ReadonlyArray<{date: string; through?: string; components?: ReadonlyArray<AssetSliceLike>}>,
    extraIds: ReadonlyArray<number> = [],
): Map<number, number> {
    const amountOf = (slice: AssetSliceLike | null | undefined): number => parseFloat(slice?.amount ?? '0');
    return rankAssetsByWeight(
        today.map((slice) => ({id: slice?.id ?? null, amount: amountOf(slice)})),
        history.map((point) => ({date: point.date, through: point.through, components: (point.components ?? []).map((component) => ({id: component?.id ?? null, amount: amountOf(component)}))})),
        extraIds,
    );
}

/** The asset a line belongs to: its id is `<asset>-<broker>`; the portfolio's line has no asset. */
export function assetIdOfLineId(lineId: string): number | null {
    if (lineId === PORTFOLIO_LINE_ID) return null;
    const asset = Number(lineId.split('-')[0]);
    return Number.isInteger(asset) ? asset : null;
}

/**
 * The look of each line among the lines of the same asset (two brokers holding it): the first is solid, the others dashed, dotted, dash-dot,
 * in the order of their broker. They wear the same colour, so the pattern is what tells them apart. A line alone, and the portfolio's, are solid.
 */
export type LineDash = 'solid' | 'dashed' | 'dotted' | number[];
export const LINE_DASHES: ReadonlyArray<LineDash> = ['solid', 'dashed', 'dotted', [8, 3, 2, 3]];

export function lineDashes(lineIds: ReadonlyArray<string>): Map<string, LineDash> {
    const byAsset = new Map<number, string[]>();
    for (const id of lineIds) {
        const asset = assetIdOfLineId(id);
        if (asset === null) continue;
        byAsset.set(asset, [...(byAsset.get(asset) ?? []), id]);
    }
    const dashes = new Map<string, LineDash>();
    const brokerOf = (id: string) => Number(id.split('-')[1] ?? 0);
    for (const ids of byAsset.values()) {
        [...ids].sort((left, right) => brokerOf(left) - brokerOf(right)).forEach((id, i) => dashes.set(id, LINE_DASHES[i % LINE_DASHES.length]));
    }
    return dashes;
}
