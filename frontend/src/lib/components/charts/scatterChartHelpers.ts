/**
 * scatterChartHelpers — the arithmetic behind the risk/return scatter.
 *
 * Split from the component for the reason every chart here is split: mounting
 * ECharts in jsdom tests the mock rather than the drawing. The option object is
 * the part that carries the decisions, so it is built by a pure function and
 * asserted directly, the selected point's look included. `ScatterChart.svelte`
 * is the drawing; its own spec pins only the wiring.
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
     * which is the normal case for a benchmark the reader does not hold.
     */
    weight?: number;
    role: RiskReturnRole;
    /**
     * One more line for the tooltip, already translated by the caller — what the
     * dot weighs, or that it is the benchmark. Absent → the tooltip says only the
     * name and the two coordinates, as it always did.
     */
    detail?: string;
}

export interface ScatterOptionInput {
    points: readonly RiskReturnPoint[];
    /**
     * Intercept of the Capital Market Line, as a fraction. The line is drawn
     * from `(0, riskFreeRate)` through the benchmark, or through the portfolio
     * when there is no benchmark (`capitalMarketLineAnchor`), so "above the line"
     * reads as "better paid for the risk taken" than the dot it runs through.
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
    /**
     * Id of the point the caller has selected, or `null`. That point is drawn larger and
     * opaque; an asset also turns the selection green, while the portfolio and the benchmark
     * keep their own colour, which is what names them (developer's review of 06/10/2026: «il
     * simbolo nel grafico non deve cambiare colore»). Nothing else changes. An id that names no
     * placed point highlights nothing, so the result is then the unselected one.
     */
    selectedId?: string | null;
}

/** Smallest a dot may be and still be clickable. */
export const MIN_SYMBOL_PX = 8;
/** Largest a bubble may be before it starts hiding its neighbours. */
export const MAX_SYMBOL_PX = 44;

/**
 * How much larger the selected point is drawn than it would be otherwise. Applied past
 * `MAX_SYMBOL_PX` too: the largest bubble must still grow when it is the one selected.
 */
const SELECTED_SYMBOL_SCALE = 1.5;

/** The selection green, the hue of a selected table row, apart from every role colour. */
function selectedColor(dark: boolean): string {
    return dark ? '#4ade80' : '#22c55e';
}

const SYMBOL_BY_ROLE: Record<RiskReturnRole, 'circle' | 'diamond'> = {
    portfolio: 'circle',
    benchmark: 'diamond',
    asset: 'circle',
};

/**
 * How much wider a symbol is drawn than a circle of the same weight, so that the two
 * cover the same area. ECharts fits every symbol in a square of side `symbolSize`: a
 * circle fills π/4 of it, a diamond — the square turned on its corner — half. At one
 * size the diamond would be a third smaller than the circle beside it, and the weight
 * it stands for would read smaller with it; √(π/2) gives it the circle's area back.
 */
const AREA_SCALE_BY_SYMBOL: Record<'circle' | 'diamond', number> = {
    circle: 1,
    diamond: Math.sqrt(Math.PI / 2),
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
 * The dot the Capital Market Line runs through, or `null` when no line can be drawn.
 *
 * The benchmark when there is one: in theory the line runs from the risk-free rate
 * through the *market* portfolio, and the benchmark is what stands for the market
 * here, so a dot above the line is better paid for its risk than the market
 * (developer's review of 05/10/2026). The reader's own portfolio is the fallback,
 * when no benchmark is placed; the line through it says "better paid than my
 * portfolio as a whole" instead.
 *
 * The benchmark anchors it on any plot, a set of assets included (developer's review
 * of 06/10/2026, on Asset Global's lab: «non compare la retta tra 0 e benchmark»):
 * "better paid than the market" needs no aggregate to be true. The fallback does —
 * a set of assets has no whole to run a line through — so the lab draws a line only
 * when a benchmark is placed.
 *
 * Only a strictly positive volatility can anchor it: at zero the slope is undefined,
 * and inventing a vertical line there would assert something the data does not say.
 */
export function capitalMarketLineAnchor(points: readonly RiskReturnPoint[]): 'benchmark' | 'portfolio' | null {
    const placeable = points.filter(isPlaceable);
    if (placeable.some((point) => point.role === 'benchmark' && point.volatility > 0)) return 'benchmark';
    const portfolio = placeable.find((point) => point.role === 'portfolio');
    return portfolio && portfolio.volatility > 0 ? 'portfolio' : null;
}

/**
 * The two endpoints of the Capital Market Line, or `null` when it cannot be drawn.
 *
 * It runs through the dot `capitalMarketLineAnchor` picks, and is extended to the
 * widest volatility on the plot so it spans the chart rather than stopping there.
 */
export function capitalMarketLine(points: readonly RiskReturnPoint[], riskFreeRate: number): [[number, number], [number, number]] | null {
    const placeable = points.filter(isPlaceable);
    const role = capitalMarketLineAnchor(placeable);
    const anchor = role === null ? undefined : placeable.find((point) => point.role === role && point.volatility > 0);
    if (!anchor) return null;

    const slope = (anchor.annualReturn - riskFreeRate) / anchor.volatility;
    const maxVolatility = Math.max(...placeable.map((point) => point.volatility));
    const end = maxVolatility > anchor.volatility ? maxVolatility : anchor.volatility;

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
    symbol: 'circle' | 'diamond';
    symbolSize: number;
    itemStyle: {color: string; opacity: number};
    /** Carried through so a tooltip can name the role without re-deriving it. */
    role: RiskReturnRole;
    id: string;
    /** The caller's extra tooltip line, when it gave one. */
    detail?: string;
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
    const {points, riskFreeRate = 0, dark = false, labels, selectedId = null} = input;

    const placeable = points.filter(isPlaceable);
    const droppedCount = points.length - placeable.length;

    // The selected point keeps its series and its place in it: the highlight changes how
    // it is drawn, never where it is filed.
    //
    // A benchmark with no weight is a reference, not a holding, and keeps a fixed marker
    // size. One with a weight is a holding too, so it is sized by that weight like every
    // other, with the area its diamond needs to match a circle of the same weight.
    const byRole = (role: RiskReturnRole): ScatterDataItem[] =>
        placeable
            .filter((point) => point.role === role)
            .map((point) => {
                const symbol = SYMBOL_BY_ROLE[role];
                const size = role === 'benchmark' && point.weight === undefined ? MIN_SYMBOL_PX * 1.6 : symbolSizeForWeight(point.weight) * AREA_SCALE_BY_SYMBOL[symbol];
                const selected = point.id === selectedId;
                return {
                    value: [point.volatility, point.annualReturn] as [number, number],
                    name: point.name,
                    symbol,
                    symbolSize: selected ? size * SELECTED_SYMBOL_SCALE : size,
                    itemStyle: selected ? {color: role === 'asset' ? selectedColor(dark) : colorForRole(role, dark), opacity: 1} : {color: colorForRole(role, dark), opacity: role === 'asset' ? 0.75 : 1},
                    role,
                    id: point.id,
                    ...(point.detail === undefined ? {} : {detail: point.detail}),
                };
            });

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
            // `left` is the outer inset, as on the growth chart (`cda9408d4`): with
            // `containLabel` the y labels are added to it, so a pixel constant here was an
            // empty strip before them. It was there for the axis name, which ECharts centres
            // on the axis line and `containLabel` does not measure; the name now starts at
            // the line and runs right, over the plot's top margin, so nothing is left to clip.
            grid: {left: '3%', right: 28, top: 28, bottom: 52, containLabel: true},
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
                nameTextStyle: {color: textColor, align: 'left'},
                axisLine: {lineStyle: {color: axisColor}},
                axisLabel: {color: textColor},
                splitLine: {lineStyle: {color: axisColor, opacity: 0.3}},
            },
            series,
        },
    };
}
