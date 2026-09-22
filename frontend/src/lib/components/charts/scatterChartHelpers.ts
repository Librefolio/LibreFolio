/**
 * scatterChartHelpers — the arithmetic behind the risk/return scatter.
 *
 * Split from the component for the reason every chart here is split: no chart
 * `.svelte` in this repository has a unit test, because mounting ECharts in
 * jsdom tests the mock rather than the drawing. The option object is the part
 * that carries the decisions, so it is built by a pure function and asserted
 * directly. `ScatterChart.svelte` is the drawing.
 *
 * WHY THIS EXISTS AT ALL, given `LineChart` already draws points. `LineChart`
 * is a TIME SERIES: its `xAxis` is `{type: 'category', data: dates}`, and the
 * scatter it uses internally maps a date to a category index
 * (`dates.indexOf(d.date)`). Every one of its series is aligned to a date. The
 * chart specified in `05-grammatica-visiva §7.5` has no dates at all — X is
 * volatility, Y is return, both continuous. Reaching for `LineChart` here would
 * produce markers pinned to a date axis, which is a different chart wearing the
 * same name. Hence `type: 'value'` on both axes, asserted in the spec.
 *
 * ⚠️ RADIUS SCALES WITH THE SQUARE ROOT OF THE WEIGHT, AND THAT IS NOT A DETAIL.
 * A bubble is read by its AREA, and area grows with the square of the radius.
 * Setting the radius proportional to the weight makes a holding of 4× the size
 * look 16× the size — the chart would overstate every large position and
 * understate every small one, silently and consistently. `√weight` makes the
 * ink proportional to the quantity, which is the only encoding that does not
 * lie.
 *
 * ⚠️ NON-FINITE POINTS ARE DROPPED, NOT CLAMPED. A `NaN` volatility reaching
 * ECharts is not an error anybody sees: the point is skipped, the axis extent
 * quietly changes, and the plot still looks like a plot. Since the caller here
 * is a risk payload that can carry `null` for an unavailable metric, filtering
 * is done once, explicitly, and the count is reported so the component can say
 * how many assets it could not place.
 */

/** What a point stands for. Drives symbol and colour, never position. */
export type RiskReturnRole = 'portfolio' | 'benchmark' | 'asset';

export interface RiskReturnPoint {
    /** Stable identity, for tooltips and for the caller's own lookups. */
    id: string;
    /** Display name. Already resolved by the caller — this file does no i18n. */
    name: string;
    /** X axis. Annualised volatility as a fraction: `0.18` is 18%. */
    volatility: number;
    /** Y axis. Annualised return as a fraction. */
    annualReturn: number;
    /**
     * Share of the set, `0..1`. Drives the bubble area where present.
     * Absent means "no weight to show" and yields the base symbol size —
     * which is the normal case for a benchmark.
     */
    weight?: number;
    role: RiskReturnRole;
}

export interface ScatterOptionInput {
    points: readonly RiskReturnPoint[];
    /**
     * Intercept of the Capital Market Line, as a fraction. The line is drawn
     * from `(0, riskFreeRate)` through the portfolio point, so "above the line"
     * reads as "better paid for the risk taken".
     */
    riskFreeRate?: number;
    /** `document.documentElement.classList.contains('dark')`, resolved by the caller. */
    dark?: boolean;
    /** Axis titles and the CML name. Supplied already translated. */
    labels: {
        volatility: string;
        return: string;
        capitalMarketLine: string;
    };
}

/** Smallest a dot may be and still be clickable. */
export const MIN_SYMBOL_PX = 8;
/** Largest a bubble may be before it starts hiding its neighbours. */
export const MAX_SYMBOL_PX = 44;

const SYMBOL_BY_ROLE: Record<RiskReturnRole, string> = {
    portfolio: 'circle',
    benchmark: 'diamond',
    asset: 'circle',
};

/** A point is placeable only if both coordinates are real numbers. */
export function isPlaceable(point: RiskReturnPoint): boolean {
    return Number.isFinite(point.volatility) && Number.isFinite(point.annualReturn);
}

/**
 * Bubble diameter for a weight, with area — not radius — proportional to it.
 *
 * A missing, non-finite or non-positive weight yields the base size rather than
 * a zero-area dot: "no weight supplied" and "a position of size zero" are
 * different statements, and only the second would justify an invisible point.
 */
export function symbolSizeForWeight(weight: number | undefined): number {
    if (weight === undefined || !Number.isFinite(weight) || weight <= 0) return MIN_SYMBOL_PX;
    const normalized = Math.min(1, weight);
    return MIN_SYMBOL_PX + (MAX_SYMBOL_PX - MIN_SYMBOL_PX) * Math.sqrt(normalized);
}

/**
 * The two endpoints of the Capital Market Line, or `null` when it cannot be drawn.
 *
 * It needs a portfolio with a strictly positive volatility: at zero the slope is
 * undefined, and inventing a vertical line there would assert something the data
 * does not say. The line is extended to the widest volatility on the plot so it
 * spans the chart rather than stopping at the portfolio.
 */
export function capitalMarketLine(points: readonly RiskReturnPoint[], riskFreeRate: number): [[number, number], [number, number]] | null {
    const placeable = points.filter(isPlaceable);
    const portfolio = placeable.find((point) => point.role === 'portfolio');
    if (!portfolio || portfolio.volatility <= 0) return null;

    const slope = (portfolio.annualReturn - riskFreeRate) / portfolio.volatility;
    const maxVolatility = Math.max(...placeable.map((point) => point.volatility));
    const end = maxVolatility > portfolio.volatility ? maxVolatility : portfolio.volatility;

    return [
        [0, riskFreeRate],
        [end, riskFreeRate + slope * end],
    ];
}

/** Colours per role, resolved for the active theme. */
export function colorForRole(role: RiskReturnRole, dark: boolean): string {
    if (role === 'portfolio') return dark ? '#38bdf8' : '#0284c7';
    if (role === 'benchmark') return dark ? '#fbbf24' : '#d97706';
    return dark ? '#94a3b8' : '#64748b';
}

interface ScatterDataItem {
    value: [number, number];
    name: string;
    symbolSize: number;
    itemStyle: {color: string; opacity: number};
    /** Carried through so a tooltip can name the role without re-deriving it. */
    role: RiskReturnRole;
    id: string;
}

/** Everything the component needs, so the drawing stays declarative. */
export interface ScatterOptionResult {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    option: Record<string, any>;
    /** Points the caller supplied that could not be placed. */
    droppedCount: number;
    /** True when nothing at all can be drawn, so the component can show its empty state. */
    isEmpty: boolean;
}

export function buildScatterOption(input: ScatterOptionInput): ScatterOptionResult {
    const {points, riskFreeRate = 0, dark = false, labels} = input;

    const placeable = points.filter(isPlaceable);
    const droppedCount = points.length - placeable.length;

    const byRole = (role: RiskReturnRole): ScatterDataItem[] =>
        placeable
            .filter((point) => point.role === role)
            .map((point) => ({
                value: [point.volatility, point.annualReturn] as [number, number],
                name: point.name,
                symbolSize: role === 'benchmark' ? MIN_SYMBOL_PX * 1.6 : symbolSizeForWeight(point.weight),
                itemStyle: {color: colorForRole(role, dark), opacity: role === 'asset' ? 0.75 : 1},
                role,
                id: point.id,
            }));

    const axisColor = dark ? '#475569' : '#cbd5e1';
    const textColor = dark ? '#cbd5e1' : '#475569';

    const line = capitalMarketLine(placeable, riskFreeRate);

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const series: Record<string, any>[] = [];

    if (line) {
        series.push({
            id: 'capital-market-line',
            name: labels.capitalMarketLine,
            type: 'line',
            data: line,
            showSymbol: false,
            silent: true,
            lineStyle: {type: 'dashed', width: 1, color: dark ? '#64748b' : '#94a3b8'},
            z: 1,
        });
    }

    for (const role of ['asset', 'benchmark', 'portfolio'] as const) {
        const data = byRole(role);
        if (data.length === 0) continue;
        series.push({
            id: `scatter-${role}`,
            name: role,
            type: 'scatter',
            data,
            z: role === 'asset' ? 2 : 3,
        });
    }

    return {
        droppedCount,
        isEmpty: placeable.length === 0,
        option: {
            grid: {left: 64, right: 28, top: 28, bottom: 52, containLabel: true},
            xAxis: {
                type: 'value',
                name: labels.volatility,
                nameLocation: 'middle',
                nameGap: 30,
                nameTextStyle: {color: textColor},
                axisLine: {lineStyle: {color: axisColor}},
                axisLabel: {color: textColor},
                splitLine: {lineStyle: {color: axisColor, opacity: 0.3}},
            },
            yAxis: {
                type: 'value',
                name: labels.return,
                nameTextStyle: {color: textColor},
                axisLine: {lineStyle: {color: axisColor}},
                axisLabel: {color: textColor},
                splitLine: {lineStyle: {color: axisColor, opacity: 0.3}},
            },
            series,
        },
    };
}
