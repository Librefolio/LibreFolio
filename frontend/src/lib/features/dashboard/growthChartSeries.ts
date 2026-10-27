/**
 * GrowthChart's series — what each view draws, and how (FE6a, release 1.3).
 *
 * Pure functions of their arguments: the component passes the view on screen (mode, submode, labels, the % series)
 * as a context object built at call time, so a series reads exactly what the component read when it built it.
 */
import type * as echarts from 'echarts';
import {buildOhlcQuad} from '$lib/components/charts/candlestickChartHelpers';
import {withHexAlpha} from '$lib/theme/colorAlpha';
import {themed} from '$lib/theme/themePair';
import {CHART_GAIN_LOSS, chartNeutrals, GROWTH_SERIES} from '$lib/theme/chartTheme';
import {growthBrokerColor} from '$lib/theme/chartPalettes';
import type {AggregatedResolutionData, AggregationInputs, CandleSeriesPoint, PctSeriesKey, SeriesPoint} from './growthChartData';

// coreMode = value|return|pnl (plan §5.1); kept as the existing 'eur'/'pct'/'pnl'
// literal union for minimal churn on the 14 existing branches, not a rename.
export type GrowthMode = 'eur' | 'pct' | 'pnl';
export type PnlSubmode = 'line' | 'candles' | 'income';

/** The translated names of the Abs view's series and tooltip rows. */
export interface EurLabels {
    bookAssetLike: string;
    bookAssetLikeTooltip: string;
    cashContributed: string;
    cashGenerated: string;
    nav: string;
    capitalBaseline: string;
    capitalBaselineTooltip: string;
}

/** The translated names of the P&L view's series and tooltip rows. */
export interface PnlLabels {
    total: string;
    dividend: string;
    interest: string;
    costs: string;
    deposit: string;
    acqNewCapital: string;
    acqReinvested: string;
    bookValue: string;
}

/** One series of the % view: its values, its translated name and how it is drawn. */
export interface PctSeriesSpec {
    key: PctSeriesKey;
    name: string;
    values: Array<number | null>;
    lineStyle: 'solid' | 'dashed' | 'dotted';
    colorKey: 'nav' | 'invested' | 'pctCash';
}

/** The view a series is built for, read by the component when it builds it. */
export interface GrowthSeriesContext {
    viewMode: GrowthMode;
    pnlSubmode: PnlSubmode;
    eurLabels: EurLabels;
    pnlLabels: PnlLabels;
    /** The % series with data; see `pctSeries` in `GrowthChart.svelte`. */
    pctSeries: PctSeriesSpec[];
    aggregationInputs: AggregationInputs;
    /**
     * The entry is the steps themselves (the daily resolution of a report that gives one point per stretch without news):
     * its lines hold their value to the next date (`step: 'end'`) instead of joining two points with a slope, and the
     * P&L halves change sign at the next date instead of at an interpolated crossing. The MWRR line is the exception: it
     * is a line of true values and stays joined.
     */
    stepped?: boolean;
}

/** The data of one series, as the partial update sends it. */
export interface GrowthSeriesData {
    name: string;
    data: SeriesPoint[];
}

/** ECharts' empty-value sentinel. MUST be used instead of `null` for a gap in a
 *  candlestick series on a category axis — a `null` item crashes
 *  `whiskerBoxCommon.getInitialData` during SeriesModel.init (see
 *  `toCandlestickPoint`). */
export const ECHARTS_EMPTY_VALUE = '-';
/** Name of the non-data decoration series behind the P&L Line submode's dashed
 *  reference line. Declared once and referenced everywhere (series construction
 *  AND the legend exclusion in applyFullOption) so the sentinel never becomes a
 *  magic string that a second site has to remember independently. */
export const PNL_REFERENCE_SERIES_NAME = '__pnlReference__';
/**
 * Opacity of a ladder bucket that is not comparable with the others (candle or Income bars).
 *
 * The buckets are calendar periods, and the series cuts the ones at its ends. A period that
 * is over and that the series covers only in part — the month the range starts in, or the
 * one it ends in when the range ends in the past — would read as a weak period, or its
 * candle as a narrow range, when it is simply a shorter one. Fading it says "not
 * comparable"; the tooltip says by how much. The period that has not ended yet is not
 * faded: its missing days are the future (developer, 06/10/2026: «essendo il futuro non
 * ancora scritto, lo consideriamo comunque pieno»).
 */
export const PARTIAL_BUCKET_OPACITY = 0.5;
/**
 * Income draws three columns in every bucket — the income stack (dividends and
 * interest above zero, costs below it), the deposit, the acquisition stack — so its
 * rule is checked per COLUMN, not per bucket: a slot that holds one readable candle
 * holds three bars a third as wide.
 *
 * The gaps are the ones the Income series declare, so the offer and the drawing cannot
 * disagree: bar = slot × (1 − category gap) / (columns + (columns − 1) × bar gap).
 *
 * Two gaps, deliberately unequal (developer's review of 06/10/2026: «ok fare le barre
 * larghe, ma se sono tutte attaccate non si capisce nulla»): 30 % of the slot between two
 * buckets, a visible margin, and 10 % of a bar between the three columns of one bucket, so
 * a bucket still reads as one group.
 */
export const INCOME_COLUMNS = 3;
export const INCOME_BAR_GAP = 0.1;
export const INCOME_CATEGORY_GAP = 0.3;
export const INCOME_BAR_SHARE = (1 - INCOME_CATEGORY_GAP) / (INCOME_COLUMNS + (INCOME_COLUMNS - 1) * INCOME_BAR_GAP);

// Color palettes
const COLORS = GROWTH_SERIES;

// The P&L broker overlay (G1a): one line per broker, coloured by its index and read at each draw (TD-1b).
export function brokerColor(index: number, isDark: boolean): string {
    return growthBrokerColor(index, isDark);
}

/** ECharts candlestick data point for a `category` xAxis: a flat `[open, close,
 *  low, high]` quad (note the element order — NOT open/high/low/close),
 *  reusing the exact same shared convention as CandlestickChart.svelte via
 *  `buildOhlcQuad` (see PR discussion: candlestick series silently fails to
 *  paint any body/wick on a `time` xAxis — a known upstream ECharts limitation
 *  — so this submode uses a `category` axis instead, matching the codebase's
 *  own already-proven Asset Detail price-chart pattern).
 *
 *  A gap day/bucket (no candle) MUST be ECharts' empty-value sentinel `'-'`,
 *  never `null`. On a category base axis the candlestick series clones its data
 *  through `whiskerBoxCommon.getInitialData`, which branches
 *  `isArray(item) -> … else if (isArray(item.value))` — so a `null` item
 *  dereferences `null.value` and throws *inside SeriesModel.init*, before the
 *  GlobalModel finishes building. The chart then has no `_seriesIndices`, so
 *  every later `setOption` silently no-ops and the canvas freezes on the
 *  previous submode's paint. `'-'` falls through that same branch chain
 *  harmlessly (verified empirically against this exact echarts build, not
 *  inferred: `null` throws "Cannot read properties of null (reading 'value')",
 *  `'-'` renders). Position in the array (not the date itself) is what aligns
 *  a point to the shared `xAxis.data` category list, so the gap must still
 *  occupy its slot — which is exactly why it can't just be omitted. */
export function toCandlestickPoint(point: CandleSeriesPoint): number[] | string {
    if (point.open == null || point.close == null || point.low == null || point.high == null) return ECHARTS_EMPTY_VALUE;
    return buildOhlcQuad(point.open, point.close, point.low, point.high, false, 1);
}

/** Clip a point's value to null when it doesn't match `keepPositive` — used to
 *  split the Total P&L line into two fixed, same-length series (positive-part /
 *  negative-part), each with its own solid green/red color. A FIXED two-series
 *  split (rather than a variable number of contiguous same-sign segments) keeps
 *  `updateChartData`'s partial by-index series merge valid across zoom/pan,
 *  where the count of sign-crossings in the visible window can change on every
 *  frame. ECharts' visualMap does not reliably recolor a line series'
 *  lineStyle/areaStyle per value — a documented upstream limitation (see
 *  apache/echarts#8034) — so per-point coloring needs this series-split
 *  approach instead, same spirit as LineChart.svelte's segment-based coloring. */
export function clipToSign(point: SeriesPoint, keepPositive: boolean): SeriesPoint {
    const v = point.value[1];
    if (v == null || v >= 0 === keepPositive) return point;
    return {...point, value: [point.value[0], null]};
}

/**
 * Split a signed series into its positive and negative halves WITHOUT leaving a hole
 * at the sign change.
 *
 * `clipToSign` alone cannot do it: it is a point-to-point map, so it can null a value
 * but never add one. Between +430 on Monday and −50 on Tuesday the positive half held
 * [+430, null] and the negative [null, −50], and with `connectNulls: false` neither
 * covered the interval — the area vanished and reappeared, which is exactly what the
 * developer reported.
 *
 * The missing point is the zero crossing. It is interpolated on the segment and
 * inserted into BOTH halves, so each one reaches the axis instead of stopping short.
 *
 * The series COUNT is untouched — still one positive, one negative — which is what
 * `updateChartData`'s by-index partial merge depends on. Only the number of points
 * inside them changes, and that is per-series data, not series identity.
 */
export function splitBySign(points: SeriesPoint[], stepped = false): {positive: SeriesPoint[]; negative: SeriesPoint[]} {
    const positive: SeriesPoint[] = [];
    const negative: SeriesPoint[] = [];

    for (let i = 0; i < points.length; i++) {
        const point = points[i];
        positive.push(clipToSign(point, true));
        negative.push(clipToSign(point, false));

        const current = point.value[1];
        const next = points[i + 1]?.value[1];
        if (current == null || next == null || current === 0 || next === 0) continue;
        if (current > 0 === next > 0) continue;

        // A stepped line holds `current` until the next date and then jumps: the sign changes AT the next date, so
        // both halves meet the axis there and no day of the hold is filled or emptied.
        if (stepped) {
            const crossing: SeriesPoint = {...points[i + 1], value: [points[i + 1].value[0], 0]};
            positive.push(crossing);
            negative.push(crossing);
            continue;
        }

        // Linear crossing between the two x positions. `value[0]` is a DATE STRING,
        // not a number — so it is parsed to millis, interpolated, and formatted back.
        // The crossing falls inside a day, which a `time` axis accepts as an ISO
        // instant; this path is only ever reached from the Line submode, whose axis
        // is `time` (the candles path uses `category`, where a fractional position
        // would be meaningless).
        const x0 = new Date(points[i].value[0]).getTime();
        const x1 = new Date(points[i + 1].value[0]).getTime();
        if (!Number.isFinite(x0) || !Number.isFinite(x1)) continue;
        const t = Math.abs(current) / (Math.abs(current) + Math.abs(next));
        const crossingX = new Date(x0 + (x1 - x0) * t).toISOString();
        const crossing: SeriesPoint = {...point, value: [crossingX, 0]};
        positive.push(crossing);
        negative.push(crossing);
    }

    return {positive, negative};
}

/**
 * Total P&L **on** `referenceDate` — the anchor for the dashed baseline that answers
 * "was P&L up or down across the period on screen".
 *
 * Read from the DAILY series, not from the aggregated buckets. The previous version
 * took the first bucket whose end reached the date, and its own docstring said so:
 * "at (or just after)". Under a monthly bucket that "just after" is up to a month of
 * drift, which is how a line that should have sat at 0 in June sat at ~600 instead.
 * A baseline that marks the first visible day cannot be allowed to land after it.
 *
 * Reading the daily value also makes the anchor independent of the bucket width, so
 * it stays correct when the candle-width ladder changes how many days a body spans.
 */
export function findReferenceTotalPnl(entry: AggregatedResolutionData, referenceDate: string | null, aggregationInputs: AggregationInputs): number | null {
    const daily = aggregationInputs.eurStackedData.totalPnl;
    const allDates = aggregationInputs.dates;
    if (allDates.length === 0) return entry.pnl.total.points[0]?.value[1] ?? null;

    if (referenceDate == null) return daily[0] ?? null;

    // Exact day if present; otherwise the last day BEFORE it — never a later one,
    // because the value on a day that has not happened yet is not a baseline.
    let idx = allDates.indexOf(referenceDate);
    if (idx < 0) {
        idx = 0;
        for (let i = 0; i < allDates.length; i++) {
            if (allDates[i] <= referenceDate) idx = i;
            else break;
        }
    }
    return daily[idx] ?? null;
}

/** The data of every series the view on screen draws, in the order the full build declares them. */
export function buildGrowthUpdateSeries(context: GrowthSeriesContext, entry: AggregatedResolutionData, referenceDate: string | null = null): GrowthSeriesData[] {
    const {viewMode, pnlSubmode, eurLabels, pnlLabels, pctSeries, aggregationInputs} = context;
    if (viewMode === 'eur') {
        return [
            {name: eurLabels.bookAssetLike, data: entry.eur.bookAssetLike.points},
            {name: eurLabels.cashContributed, data: entry.eur.cashContributed.points},
            {name: eurLabels.cashGenerated, data: entry.eur.cashGenerated.points},
            {name: eurLabels.nav, data: entry.eur.nav.points},
            {name: eurLabels.capitalBaseline, data: entry.eur.capitalBaseline.points},
        ];
    }

    if (viewMode === 'pnl' && pnlSubmode === 'line') {
        // A fixed positive/negative pair plus a third fixed slot for the dashed
        // reference line (flat at the first-visible-day P&L). The three slots are
        // what updateChartData's partial by-index series merge depends on across
        // zoom/pan; splitBySign adds POINTS inside two of them (the interpolated zero
        // crossings) and leaves the slot count alone, so the merge stays valid.
        const signSplit = splitBySign(entry.pnl.total.points, context.stepped === true);
        const referenceValue = findReferenceTotalPnl(entry, referenceDate, aggregationInputs);
        const referencePoints: SeriesPoint[] = entry.pnl.total.points.map((p) => ({...p, value: [p.value[0], referenceValue]}));
        return [{name: pnlLabels.total, data: signSplit.positive}, {name: pnlLabels.total, data: signSplit.negative}, {name: PNL_REFERENCE_SERIES_NAME, data: referencePoints}, ...entry.pnl.brokers.map((broker) => ({name: broker.brokerName, data: broker.metric.points}))];
    }

    if (viewMode === 'pnl' && pnlSubmode === 'candles') {
        // TOTAL CANDLE ONLY (developer review 2026-09-21). The per-broker dashed
        // overlay was removed everywhere, not just on Broker detail: a candle already
        // carries four numbers per position, and laying broker lines over it made the
        // one series that has to be read precisely the hardest one to see.
        // Candlestick data is structurally a flat quad, not a SeriesPoint — cast
        // through unknown; ECharts itself doesn't care, only the shared return-type
        // annotation does (see buildGrowthFullSeries's matching cast). The partial first
        // bucket wraps its quad as `{value, itemStyle}`, the item form ECharts reads
        // through `isArray(item.value)`; a gap stays the bare sentinel.
        const candles = entry.pnl.candle.points.map((point, index) => {
            const quad = toCandlestickPoint(point);
            return quad !== ECHARTS_EMPTY_VALUE && entry.buckets[index]?.partial ? {value: quad, itemStyle: {opacity: PARTIAL_BUCKET_OPACITY}} : quad;
        });
        return [{name: pnlLabels.total, data: candles as unknown as SeriesPoint[]}];
    }

    if (viewMode === 'pnl' && pnlSubmode === 'income') {
        // DIVIDEND/INTEREST stacked bars (plan §3.4) + batch 2's costs/deposit/
        // acquisition dimensions — no broker overlay for this submode (the plan's
        // hybrid-overlay rule is specific to Line/Candles). Fixed 6-slot order
        // matches buildGrowthFullSeries's matching index reads exactly. The partial first
        // bucket is faded on every column alike.
        const faded = (points: SeriesPoint[]): SeriesPoint[] => points.map((point, index) => (entry.buckets[index]?.partial ? {...point, itemStyle: {opacity: PARTIAL_BUCKET_OPACITY}} : point));
        return [
            {name: pnlLabels.dividend, data: faded(entry.pnl.income.dividend.points)},
            {name: pnlLabels.interest, data: faded(entry.pnl.income.interest.points)},
            {name: pnlLabels.costs, data: faded(entry.pnl.costs.points)},
            {name: pnlLabels.deposit, data: faded(entry.pnl.deposits.points)},
            {name: pnlLabels.bookValue, data: faded(entry.pnl.acquisition.fromNewCapital.points)},
            {name: pnlLabels.bookValue, data: faded(entry.pnl.acquisition.fromReinvested.points)},
        ];
    }

    // See buildGrowthFullSeries's matching guard.
    if (viewMode === 'pnl') return [];

    return pctSeries.map((series) => ({
        name: series.name,
        data: entry.pct[series.key].points,
    }));
}

/** Every series of the view on screen, with its style, around the data `buildGrowthUpdateSeries` built. */
export function buildGrowthFullSeries(context: GrowthSeriesContext, isDark: boolean, seriesData: GrowthSeriesData[]): echarts.SeriesOption[] {
    const series = buildSeries(context, isDark, seriesData);
    if (!context.stepped) return series;
    // A line that does not say otherwise holds its value to the next date. The MWRR says `step: false`.
    return series.map((entry) => (entry.type === 'line' && (entry as {step?: unknown}).step === undefined ? ({...entry, step: 'end'} as echarts.SeriesOption) : entry));
}

function buildSeries(context: GrowthSeriesContext, isDark: boolean, seriesData: GrowthSeriesData[]): echarts.SeriesOption[] {
    const {viewMode, pnlSubmode, eurLabels, pnlLabels, pctSeries} = context;
    if (viewMode === 'eur') {
        const cc = (key: keyof typeof COLORS) => COLORS[key][isDark ? 'dark' : 'light'];
        return [
            {
                name: eurLabels.bookAssetLike,
                type: 'line',
                stack: 'bookValue',
                data: seriesData[0].data,
                smooth: false,
                symbol: 'none',
                lineStyle: {color: cc('bookAssetLike'), width: 1, opacity: 0.7},
                areaStyle: {color: withHexAlpha(cc('bookAssetLike'), '44')},
                itemStyle: {color: cc('bookAssetLike')},
                emphasis: {focus: 'series'},
            },
            {
                name: eurLabels.cashContributed,
                type: 'line',
                stack: 'bookValue',
                data: seriesData[1].data,
                smooth: false,
                symbol: 'none',
                lineStyle: {color: cc('cashContributed'), width: 1, opacity: 0.7},
                areaStyle: {color: withHexAlpha(cc('cashContributed'), '44')},
                itemStyle: {color: cc('cashContributed')},
                emphasis: {focus: 'series'},
            },
            {
                name: eurLabels.cashGenerated,
                type: 'line',
                stack: 'bookValue',
                data: seriesData[2].data,
                smooth: false,
                symbol: 'none',
                lineStyle: {color: cc('cashGenerated'), width: 1, opacity: 0.7},
                areaStyle: {color: withHexAlpha(cc('cashGenerated'), '44')},
                itemStyle: {color: cc('cashGenerated')},
                emphasis: {focus: 'series'},
            },
            {name: eurLabels.nav, type: 'line', data: seriesData[3].data, smooth: false, symbol: 'none', lineStyle: {color: cc('nav'), width: 2, type: 'solid'}, itemStyle: {color: cc('nav')}, emphasis: {focus: 'series'}},
            {name: eurLabels.capitalBaseline, type: 'line', data: seriesData[4].data, smooth: false, symbol: 'none', lineStyle: {color: cc('capitalBaseline'), width: 1.5, type: 'dashed'}, itemStyle: {color: cc('capitalBaseline')}, emphasis: {focus: 'series'}},
        ];
    }

    if (viewMode === 'pnl' && pnlSubmode === 'line') {
        const greenColor = themed(CHART_GAIN_LOSS.portfolio.gain, isDark);
        const redColor = themed(CHART_GAIN_LOSS.portfolio.loss, isDark);
        // Positive/negative split (see clipToSign) instead of a single fixed-color
        // line — ECharts visualMap doesn't reliably recolor a line's
        // lineStyle/areaStyle per value (apache/echarts#8034), so this uses the
        // same "split into multiple series" idiom as LineChart.svelte's own
        // segment coloring, just as a fixed 2-slot pair (not a variable segment
        // count) so it stays compatible with updateChartData's partial merge.
        const positiveSeries: echarts.SeriesOption = {
            name: pnlLabels.total,
            type: 'line',
            data: seriesData[0].data,
            smooth: false,
            connectNulls: false,
            symbol: 'none',
            lineStyle: {color: greenColor, width: 2, type: 'solid'},
            itemStyle: {color: greenColor},
            areaStyle: {color: greenColor, opacity: 0.15},
            emphasis: {focus: 'series'},
        };
        const negativeSeries: echarts.SeriesOption = {
            name: pnlLabels.total,
            type: 'line',
            data: seriesData[1].data,
            smooth: false,
            connectNulls: false,
            symbol: 'none',
            lineStyle: {color: redColor, width: 2, type: 'solid'},
            itemStyle: {color: redColor},
            areaStyle: {color: redColor, opacity: 0.15},
            emphasis: {focus: 'series'},
        };
        // Dashed reference line at the first-visible-day P&L (plan follow-up #3) —
        // drawn as a dedicated flat-line series, not markLine, to avoid an ECharts
        // bug where markLine + visualMap (piecewise, dimension:1, tuple data)
        // crashes with "Cannot read properties of undefined (reading 'coord')"
        // (same precedent as LineChart.svelte's own baseline reference line).
        const referenceSeries: echarts.SeriesOption = {
            type: 'line',
            name: PNL_REFERENCE_SERIES_NAME,
            data: seriesData[2].data,
            symbol: 'none',
            showSymbol: false,
            lineStyle: {color: chartNeutrals(isDark).growth.pnlReference, type: 'dashed', width: 1},
            itemStyle: {color: 'transparent'},
            emphasis: {disabled: true},
            tooltip: {show: false},
            silent: true,
            z: 0,
        };
        const brokerSeries: echarts.SeriesOption[] = seriesData.slice(3).map((s, index) => ({
            name: s.name,
            type: 'line' as const,
            data: s.data,
            smooth: false,
            connectNulls: false,
            symbol: 'none',
            lineStyle: {color: brokerColor(index, isDark), width: 1.5, type: 'dashed'},
            itemStyle: {color: brokerColor(index, isDark)},
            emphasis: {focus: 'series'},
        }));
        return [positiveSeries, negativeSeries, referenceSeries, ...brokerSeries];
    }

    if (viewMode === 'pnl' && pnlSubmode === 'candles') {
        // Same up/down colors as the P&L tooltip's sign coloring, for consistency.
        const greenColor = themed(CHART_GAIN_LOSS.portfolio.gain, isDark);
        const redColor = themed(CHART_GAIN_LOSS.portfolio.loss, isDark);
        // seriesData[0].data is really (number[]|null)[] here (see the matching cast
        // in buildGrowthUpdateSeries) — a flat [open,close,low,high] quad per category
        // position, matching CandlestickChart.svelte's own category-axis convention
        // (a `time` xAxis silently fails to paint any candlestick body/wick — a known
        // upstream ECharts limitation). `any` here matches the existing
        // CandlestickChart.svelte convention (`const series: any[] = []`) rather than
        // fighting the generated types file-wide.
        const candleSeries: any = {
            name: pnlLabels.total,
            type: 'candlestick',
            data: seriesData[0].data,
            barWidth: '80%',
            itemStyle: {color: greenColor, color0: redColor, borderColor: greenColor, borderColor0: redColor},
        };
        // Total candle only — see the matching note in buildGrowthUpdateSeries.
        return [candleSeries];
    }

    if (viewMode === 'pnl' && pnlSubmode === 'income') {
        const cc = (key: keyof typeof COLORS) => COLORS[key][isDark ? 'dark' : 'light'];
        // Three columns per bucket: the income stack (dividends and interest above zero,
        // costs hanging below it — a same-sign stack splits by sign), the deposit, the
        // acquisition stack. The gaps are the ones the rung offer assumes
        // (INCOME_BAR_SHARE). ECharts keeps the last value it meets on the axis, so
        // every series declares them rather than trusting one to be read.
        const gaps = {barGap: `${Math.round(INCOME_BAR_GAP * 100)}%`, barCategoryGap: `${Math.round(INCOME_CATEGORY_GAP * 100)}%`};
        return [
            {name: pnlLabels.dividend, type: 'bar' as const, stack: 'income', data: seriesData[0].data, itemStyle: {color: cc('dividend')}, ...gaps},
            {name: pnlLabels.interest, type: 'bar' as const, stack: 'income', data: seriesData[1].data, itemStyle: {color: cc('interest')}, ...gaps},
            {name: pnlLabels.costs, type: 'bar' as const, stack: 'income', data: seriesData[2].data, itemStyle: {color: cc('costs')}, ...gaps},
            {name: pnlLabels.deposit, type: 'bar' as const, data: seriesData[3].data, itemStyle: {color: cc('deposit')}, ...gaps},
            // Acquisition 2-zone stacked bar (batch 2, plan §5.2): the purchase value,
            // split by the money that paid for it (R11). Both zones carry its name, so
            // the legend lists it once and one click hides both. Each zone keeps the
            // colour its money has in the Abs view (D26): new capital the KPI blue of
            // the assets at cost, reinvested the green of the generated returns.
            // The Abs area shows the same text and ECharts keeps legend state by name,
            // so hiding it in one view hides it in the other too (accepted, D27).
            {name: pnlLabels.bookValue, type: 'bar' as const, stack: 'acquisition', data: seriesData[4].data, itemStyle: {color: cc('bookAssetLike')}, ...gaps},
            {name: pnlLabels.bookValue, type: 'bar' as const, stack: 'acquisition', data: seriesData[5].data, itemStyle: {color: cc('cashGenerated')}, ...gaps},
        ];
    }

    // See buildGrowthUpdateSeries's matching guard.
    if (viewMode === 'pnl') return [];

    return pctSeries.map((series, index) => ({
        name: series.name,
        type: 'line' as const,
        data: seriesData[index].data,
        smooth: false,
        // The history's MWRR has a true value only on a few days (`mwrr_line`): the line joins them, and does not stop at the days between.
        connectNulls: series.key === 'mwrrCum',
        ...(series.key === 'mwrrCum' ? {step: false as const} : {}),
        symbol: 'none',
        lineStyle: {color: COLORS[series.colorKey][isDark ? 'dark' : 'light'], width: 2, type: series.lineStyle},
        itemStyle: {color: COLORS[series.colorKey][isDark ? 'dark' : 'light']},
    }));
}
