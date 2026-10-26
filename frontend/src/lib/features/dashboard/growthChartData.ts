/**
 * GrowthChart's derived data — the series it aggregates and the buckets each view draws (FE6a, release 1.3).
 *
 * Pure functions of their arguments. The component keeps the reactive state: the `$derived` inputs, the memo of each
 * aggregation, the entry on screen. Every value these functions used to read from the component's closure is a
 * parameter here, so an input can reach an aggregation only by being passed to it.
 */
import {namedPoint} from '$lib/components/charts/echartsAnimationConfig';
import {aggregateLineSeries, aggregateOHLCV, aggregateSumSeries, mapDateToBucket, type ChartResolution} from '$lib/components/charts/timeSeriesAggregation';
import type {LineDataPoint} from '$lib/components/charts/LineChart.svelte';
import {daysBetween} from '$lib/utils/dateOnly';
import {buildCalendarLadder, type CalendarPeriod, type LadderRung} from './growthLadderBuckets';

// =========================================================================
// Types
// =========================================================================

/** One rung of the candle-width ladder: the calendar period one body, or one group of Income bars, covers. */
export type CandleWidth = LadderRung;

export type SeriesPoint = ReturnType<typeof namedPoint> & {
    bucketStart: string;
    bucketEnd: string;
    resolution: ChartResolution;
    /** Only on a ladder bucket that is not comparable; see PARTIAL_BUCKET_OPACITY. */
    itemStyle?: {opacity: number};
};

export type EurSeriesKey = 'bookAssetLike' | 'cashContributed' | 'cashGenerated' | 'nav' | 'capitalBaseline' | 'totalPnl';
export type PctSeriesKey = 'mwrrCum' | 'twrr' | 'roi';

export interface BucketInfo {
    date: string;
    bucketStart: string;
    bucketEnd: string;
    resolution: ChartResolution;
    /** Only on a ladder bucket: the calendar period it stands for. `bucketStart`/`bucketEnd`
     *  are the days of it the series covers, so the closing date stays a day with data. */
    period?: CalendarPeriod;
    /** Only on a ladder bucket that is over and that the series covers in part: faded,
     *  and its tooltip says how many of the period's days it holds. */
    partial?: {days: number; total: number};
    /** Only on the ladder bucket that has not ended yet, wider than a day: drawn whole, and
     *  its tooltip says how far it has got. */
    current?: {days: number; total: number};
}

/** A ladder bucket also carries the day-index range it spans, which is what the local
 *  reducers walk — no date re-parsing, no calendar lookup. */
export type LadderBucket = BucketInfo & {startIndex: number; endIndex: number};

export interface AggregatedMetric {
    values: Array<number | null>;
    points: SeriesPoint[];
}

interface AggregatedLookupEntry {
    value: number;
    bucketStart: string;
    bucketEnd: string;
}

/** One broker's P&L overlay line, aggregated at a given resolution (G1a). */
export interface AggregatedBrokerPnl {
    brokerId: number;
    brokerName: string;
    metric: AggregatedMetric;
}

/** One synthetic P&L candle point, aggregated at a given resolution (G1b). */
export type CandleSeriesPoint = SeriesPoint & {
    open: number | null;
    high: number | null;
    low: number | null;
    close: number | null;
};

export interface AggregatedCandleMetric {
    points: CandleSeriesPoint[];
}

export interface AggregatedResolutionData {
    resolution: ChartResolution;
    /** True for an entry built by the ladder (P&L candles and Income): its buckets are
     *  categories on the x axis, not points in time. A property of the entry, not of
     *  the mode on screen, so a stale entry can never be read with the wrong geometry. */
    ladder: boolean;
    /** The rung a ladder entry was built on, which names its axis labels; absent on a density entry. */
    rung?: LadderRung;
    dates: string[];
    buckets: BucketInfo[];
    eur: Record<EurSeriesKey, AggregatedMetric>;
    pct: Record<PctSeriesKey, AggregatedMetric>;
    pnl: {
        total: AggregatedMetric;
        brokers: AggregatedBrokerPnl[];
        candle: AggregatedCandleMetric;
        income: {dividend: AggregatedMetric; interest: AggregatedMetric};
        costs: AggregatedMetric;
        deposits: AggregatedMetric;
        acquisition: {fromNewCapital: AggregatedMetric; fromReinvested: AggregatedMetric};
    };
}

/** One day's synthetic P&L candle. */
export interface DailyCandle {
    open: number;
    high: number;
    low: number;
    close: number;
}

/** The six amounts of the Abs view, one value per day of the history. */
export type EurStackedData = Record<EurSeriesKey, Array<number | null>>;

/** The three returns of the % view, in percent, one value per day of the history. */
export type PctValues = Record<PctSeriesKey, Array<number | null>>;

/** One broker's total P&L, aligned to the history's days. */
export interface BrokerPnlSeries {
    brokerId: number;
    brokerName: string;
    values: Array<number | null>;
}

/**
 * Everything an aggregation reads. The component builds it as one `$derived` object, so its identity changes whenever
 * any member does; the memo of each aggregation is keyed on that identity (see `aggregationInputs` in
 * `GrowthChart.svelte`).
 */
export interface AggregationInputs {
    dates: string[];
    eurStackedData: EurStackedData;
    pctValuesRaw: PctValues;
    pnlBrokerSeriesRaw: BrokerPnlSeries[];
    pnlCandleByDate: Map<string, DailyCandle>;
    dividendValues: number[];
    interestValues: number[];
    costValues: number[];
    depositValues: number[];
    acqFromNewCapitalValues: number[];
    acqFromReinvestedValues: number[];
}

// =========================================================================
// Inputs: one value per date (`growthStepInputs.ts` builds them from the report's steps)
// =========================================================================

/** Helper to safely extract amount from an optional Currency field (handles union types). */
export function amountOf(field: any): number | null {
    if (field != null && !Array.isArray(field) && typeof field === 'object' && 'amount' in field) return Number(field.amount);
    return null;
}

/** A sparse flow series (signed DIVIDEND/INTEREST, G1c; costs, deposits and the BUY funding
 *  split, batch 2) aligned to `dates`. A date absent from the points means no flow that
 *  day — rendered as 0 (a sparse-flow series, distinct from candle "gap" semantics). */
export function alignFlowToDates<P extends {date: string}>(dates: string[], points: readonly P[], amount: (point: P) => number): number[] {
    const byDate = new Map(points.map((p) => [p.date, amount(p)]));
    return dates.map((d) => byDate.get(d) ?? 0);
}

// =========================================================================
// Buckets
// =========================================================================

export function buildBucketInfos(resolution: ChartResolution, dates: string[]): BucketInfo[] {
    if (resolution === 'daily') {
        return dates.map((date) => ({
            date,
            bucketStart: date,
            bucketEnd: date,
            resolution,
        }));
    }

    const buckets: BucketInfo[] = [];
    let lastBucketEnd: string | null = null;

    for (const date of dates) {
        const {bucketStart, bucketEnd} = mapDateToBucket(date, resolution);
        // The point stands on the last day of its bucket the history holds, where the
        // aggregators put its value: a whole period's calendar end, the running one's last
        // day with data. The calendar end of a period still running has not happened yet.
        if (bucketEnd === lastBucketEnd) {
            buckets[buckets.length - 1].date = date;
            continue;
        }

        buckets.push({
            date,
            bucketStart,
            bucketEnd,
            resolution,
        });
        lastBucketEnd = bucketEnd;
    }

    return buckets;
}

/**
 * Ladder buckets: one per calendar period of `rung` the series touches
 * (`growthLadderBuckets`; developer's decision of 06/10/2026, which replaces D16-ii's
 * day counts anchored at the last day). The closing date of each bucket — its category
 * value — is the last day of it the series holds, so the axis planner's contract and the
 * candles' "value at" date stay days with data; the calendar edges travel in `period`.
 *
 * A period that is over and that the series covers in part is marked `partial` (faded);
 * the one that has not ended yet is `current` (whole). Both carry the period's covered
 * days and its length for the tooltip.
 *
 * Kept separate from `buildBucketInfos` on purpose. That one delegates to the shared
 * calendar aggregators (`aggregateLineSeries` and friends), which can only express ISO
 * weeks and calendar months — there is no way to ask them for a three-day block, a pair
 * of weeks or a quarter. The OUTPUT is the same `AggregatedResolutionData` the rest of the
 * component already consumes, so this is one pipeline with two bucket builders, not a
 * second pipeline.
 *
 * `resolution` is carried for the tooltip only: a one-day bucket prints a date, any
 * wider bucket prints its range.
 */
export function buildLadderBuckets(sourceDates: string[], rung: CandleWidth, today: string): LadderBucket[] {
    return buildCalendarLadder(sourceDates, rung, today).map((bucket) => {
        const days = {days: bucket.coveredDays, total: bucket.periodDays};
        // A one-day period has nothing to report on how far it has got (developer, 06/10/2026:
        // no «In progress: 1 of 1 days» on today's 1D candle), so it carries no current mark.
        const current = bucket.current && bucket.periodDays > 1;
        return {
            date: sourceDates[bucket.endIndex],
            bucketStart: sourceDates[bucket.startIndex],
            bucketEnd: sourceDates[bucket.endIndex],
            resolution: rung === '1D' ? 'daily' : 'weekly',
            period: bucket.period,
            ...(bucket.partial ? {partial: days} : current ? {current: days} : {}),
            startIndex: bucket.startIndex,
            endIndex: bucket.endIndex,
        };
    });
}

/** How many days, weeks and months of `dates` fall between `startDate` and `endDate`: what the density cascade weighs. */
export function countBuckets(dates: string[], startDate: string, endDate: string): {dailyCount: number; weeklyCount: number; monthlyCount: number} {
    let dailyCount = 0;
    const weekly = new Set<string>();
    const monthly = new Set<string>();

    for (const date of dates) {
        if (date < startDate || date > endDate) continue;
        dailyCount += 1;
        weekly.add(mapDateToBucket(date, 'weekly').bucketEnd);
        monthly.add(mapDateToBucket(date, 'monthly').bucketEnd);
    }

    return {
        dailyCount,
        weeklyCount: weekly.size,
        monthlyCount: monthly.size,
    };
}

// =========================================================================
// Metrics
// =========================================================================

export function toSeriesPoint(bucket: BucketInfo | LadderBucket, value: number | null): SeriesPoint {
    return {
        ...namedPoint(bucket.date, value),
        bucketStart: bucket.bucketStart,
        bucketEnd: bucket.bucketEnd,
        resolution: bucket.resolution,
    };
}

/** End-of-period reduction: the last value that actually exists inside the bucket. */
export function ladderLast(values: Array<number | null>, bucket: LadderBucket): number | null {
    for (let i = bucket.endIndex; i >= bucket.startIndex; i--) {
        const v = values[i];
        if (v != null) return v;
    }
    return null;
}

export function ladderMetric(values: Array<number | null>, buckets: LadderBucket[]): AggregatedMetric {
    const aggregated = buckets.map((bucket) => ladderLast(values, bucket));
    return {values: aggregated, points: buckets.map((bucket, i) => toSeriesPoint(bucket, aggregated[i]))};
}

/** Flow reduction: a bucket's value is the SUM of what happened inside it, never the
 *  last day's balance — a flow has no closing level to read. */
export function ladderFlowMetric(values: number[], buckets: LadderBucket[]): AggregatedMetric {
    const aggregated = buckets.map((bucket) => {
        let sum = 0;
        for (let i = bucket.startIndex; i <= bucket.endIndex; i++) sum += values[i] ?? 0;
        return sum;
    });
    return {values: aggregated, points: buckets.map((bucket, i) => toSeriesPoint(bucket, aggregated[i]))};
}

/** OHLC reduction: first open, max high, min low, last close — the composition order
 *  the plan fixes (daily candles first, aggregation second, never the reverse). */
export function ladderCandleMetric(byDate: Map<string, DailyCandle>, buckets: LadderBucket[], dates: string[]): AggregatedCandleMetric {
    return {
        points: buckets.map((bucket) => {
            let open: number | null = null;
            let high: number | null = null;
            let low: number | null = null;
            let close: number | null = null;
            for (let i = bucket.startIndex; i <= bucket.endIndex; i++) {
                const c = byDate.get(dates[i]);
                if (!c) continue;
                if (open == null) open = c.open;
                high = high == null ? c.high : Math.max(high, c.high);
                low = low == null ? c.low : Math.min(low, c.low);
                close = c.close;
            }
            return {...toSeriesPoint(bucket, close), open, high, low, close};
        }),
    };
}

export function aggregateMetric(values: Array<number | null>, resolution: ChartResolution, buckets: BucketInfo[], dates: string[]): AggregatedMetric {
    if (resolution === 'daily') {
        return {
            values: [...values],
            points: buckets.map((bucket, index) => toSeriesPoint(bucket, values[index] ?? null)),
        };
    }

    const sourcePoints: LineDataPoint[] = dates.flatMap((date, index) => {
        const value = values[index];
        return value == null ? [] : [{date, value}];
    });
    const aggregated = aggregateLineSeries(sourcePoints, resolution);
    // Matched by calendar bucket, not by date (Y-2): the aggregated point stands on the last day WITH a value, the
    // bucket on the last day of the history. A line that stops mid-period (a broker leaving the scope on a Wednesday)
    // keeps its last value there, as `ladderLast` does, instead of turning into a gap; a bucket with no value at all
    // stays a gap. Both sides compute `bucketEnd` with `mapDateToBucket`.
    const lookup = new Map<string, AggregatedLookupEntry>(
        aggregated.map((point) => {
            const bucketEnd = 'bucketEnd' in point && typeof point.bucketEnd === 'string' ? point.bucketEnd : point.date;
            return [
                bucketEnd,
                {
                    value: point.value,
                    bucketStart: 'bucketStart' in point && typeof point.bucketStart === 'string' ? point.bucketStart : point.date,
                    bucketEnd,
                },
            ];
        }),
    );

    const aggregatedValues = buckets.map((bucket) => lookup.get(bucket.bucketEnd)?.value ?? null);
    const points = buckets.map((bucket, index) => {
        const meta = lookup.get(bucket.bucketEnd);
        return toSeriesPoint(
            {
                ...bucket,
                bucketStart: meta?.bucketStart ?? bucket.bucketStart,
                bucketEnd: meta?.bucketEnd ?? bucket.bucketEnd,
            },
            aggregatedValues[index],
        );
    });

    return {values: aggregatedValues, points};
}

/** Aggregate a sparse economic-flow metric (signed DIVIDEND/INTEREST, G1c) using
 *  aggregateSumSeries — mirrors aggregateMetric()'s structure exactly but sums
 *  every day in a bucket instead of taking the last value (plan §3.4/§5.2: "Weekly/
 *  monthly buckets sum them; they never use end-of-period/last-value semantics"). */
export function aggregateFlowMetric(values: number[], resolution: ChartResolution, buckets: BucketInfo[], dates: string[]): AggregatedMetric {
    if (resolution === 'daily') {
        return {
            values: [...values],
            points: buckets.map((bucket, index) => toSeriesPoint(bucket, values[index] ?? 0)),
        };
    }

    const sourcePoints: LineDataPoint[] = dates.map((date, index) => ({date, value: values[index] ?? 0}));
    const aggregated = aggregateSumSeries(sourcePoints, resolution);
    const lookup = new Map<string, AggregatedLookupEntry>(
        aggregated.map((point) => [
            point.date,
            {
                value: point.value,
                bucketStart: 'bucketStart' in point && typeof point.bucketStart === 'string' ? point.bucketStart : point.date,
                bucketEnd: 'bucketEnd' in point && typeof point.bucketEnd === 'string' ? point.bucketEnd : point.date,
            },
        ]),
    );

    const aggregatedValues = buckets.map((bucket) => lookup.get(bucket.date)?.value ?? 0);
    const points = buckets.map((bucket, index) => {
        const meta = lookup.get(bucket.date);
        return toSeriesPoint(
            {
                ...bucket,
                bucketStart: meta?.bucketStart ?? bucket.bucketStart,
                bucketEnd: meta?.bucketEnd ?? bucket.bucketEnd,
            },
            aggregatedValues[index],
        );
    });

    return {values: aggregatedValues, points};
}

/** Aggregate the daily synthetic P&L candle series to a coarser resolution, reusing
 *  the shared aggregateOHLCV reducer (first open / max high / min low / last close) —
 *  the exact "compose daily first, then roll up" contract (plan §4.3), never re-derived
 *  here. Days with no candle (map miss) are excluded before aggregating, matching
 *  aggregateMetric()'s null-filtering convention for the same reason: a bucket with no
 *  contributing day must not synthesize a false zero-range candle. */
export function aggregateCandleMetric(byDate: Map<string, DailyCandle>, resolution: ChartResolution, buckets: BucketInfo[], dates: string[]): AggregatedCandleMetric {
    if (resolution === 'daily') {
        return {
            points: buckets.map((bucket) => {
                const c = byDate.get(bucket.date);
                return {...toSeriesPoint(bucket, c?.close ?? null), open: c?.open ?? null, high: c?.high ?? null, low: c?.low ?? null, close: c?.close ?? null};
            }),
        };
    }

    const sourcePoints: LineDataPoint[] = dates.flatMap((date) => {
        const c = byDate.get(date);
        return c ? [{date, value: c.close, open: c.open, high: c.high, low: c.low, close: c.close}] : [];
    });
    const aggregated = aggregateOHLCV(sourcePoints, resolution);
    const lookup = new Map(
        aggregated.map((point) => [
            point.date,
            {
                open: point.open ?? null,
                high: point.high ?? null,
                low: point.low ?? null,
                close: point.close ?? null,
                bucketStart: 'bucketStart' in point && typeof point.bucketStart === 'string' ? point.bucketStart : point.date,
                bucketEnd: 'bucketEnd' in point && typeof point.bucketEnd === 'string' ? point.bucketEnd : point.date,
            },
        ]),
    );

    const points = buckets.map((bucket) => {
        const meta = lookup.get(bucket.date);
        return {
            ...toSeriesPoint({...bucket, bucketStart: meta?.bucketStart ?? bucket.bucketStart, bucketEnd: meta?.bucketEnd ?? bucket.bucketEnd}, meta?.close ?? null),
            open: meta?.open ?? null,
            high: meta?.high ?? null,
            low: meta?.low ?? null,
            close: meta?.close ?? null,
        };
    });

    return {points};
}

// =========================================================================
// Entries: one per density resolution, one per ladder rung
// =========================================================================

/** The density cascade's entry at `resolution`: every view's series on the same buckets. */
export function buildResolutionData(inputs: AggregationInputs, resolution: ChartResolution): AggregatedResolutionData {
    const buckets = buildBucketInfos(resolution, inputs.dates);
    return {
        resolution,
        ladder: false,
        dates: buckets.map((bucket) => bucket.date),
        buckets,
        eur: {
            bookAssetLike: aggregateMetric(inputs.eurStackedData.bookAssetLike, resolution, buckets, inputs.dates),
            cashContributed: aggregateMetric(inputs.eurStackedData.cashContributed, resolution, buckets, inputs.dates),
            cashGenerated: aggregateMetric(inputs.eurStackedData.cashGenerated, resolution, buckets, inputs.dates),
            nav: aggregateMetric(inputs.eurStackedData.nav, resolution, buckets, inputs.dates),
            capitalBaseline: aggregateMetric(inputs.eurStackedData.capitalBaseline, resolution, buckets, inputs.dates),
            totalPnl: aggregateMetric(inputs.eurStackedData.totalPnl, resolution, buckets, inputs.dates),
        },
        pct: {
            mwrrCum: aggregateMetric(inputs.pctValuesRaw.mwrrCum, resolution, buckets, inputs.dates),
            twrr: aggregateMetric(inputs.pctValuesRaw.twrr, resolution, buckets, inputs.dates),
            roi: aggregateMetric(inputs.pctValuesRaw.roi, resolution, buckets, inputs.dates),
        },
        pnl: {
            // Reuses the exact same Decimal-sourced totalPnl values as EUR mode's
            // tooltip line — one canonical, non-rebased total_pnl series (plan §3.2).
            total: aggregateMetric(inputs.eurStackedData.totalPnl, resolution, buckets, inputs.dates),
            brokers: inputs.pnlBrokerSeriesRaw.map((broker) => ({
                brokerId: broker.brokerId,
                brokerName: broker.brokerName,
                metric: aggregateMetric(broker.values, resolution, buckets, inputs.dates),
            })),
            candle: aggregateCandleMetric(inputs.pnlCandleByDate, resolution, buckets, inputs.dates),
            income: {
                dividend: aggregateFlowMetric(inputs.dividendValues, resolution, buckets, inputs.dates),
                interest: aggregateFlowMetric(inputs.interestValues, resolution, buckets, inputs.dates),
            },
            costs: aggregateFlowMetric(inputs.costValues, resolution, buckets, inputs.dates),
            deposits: aggregateFlowMetric(inputs.depositValues, resolution, buckets, inputs.dates),
            acquisition: {
                fromNewCapital: aggregateFlowMetric(inputs.acqFromNewCapitalValues, resolution, buckets, inputs.dates),
                fromReinvested: aggregateFlowMetric(inputs.acqFromReinvestedValues, resolution, buckets, inputs.dates),
            },
        },
    };
}

/**
 * The ladder's entry at `width`: identical shape, different bucket builder.
 *
 * Only the P&L sections are filled. EUR and % never reach this branch — they keep the
 * density cascade — so computing their series here would be work whose result nothing
 * reads, and a memo that computes what nobody asks for is how a memo becomes a cost.
 */
export function buildLadderData(inputs: AggregationInputs, width: CandleWidth, today: string): AggregatedResolutionData {
    const buckets = buildLadderBuckets(inputs.dates, width, today);
    const empty: AggregatedMetric = {values: [], points: []};
    return {
        resolution: buckets[0]?.resolution ?? 'daily',
        ladder: true,
        rung: width,
        dates: buckets.map((bucket) => bucket.date),
        buckets,
        eur: {bookAssetLike: empty, cashContributed: empty, cashGenerated: empty, nav: empty, capitalBaseline: empty, totalPnl: empty},
        pct: {mwrrCum: empty, twrr: empty, roi: empty},
        pnl: {
            total: ladderMetric(inputs.eurStackedData.totalPnl, buckets),
            brokers: inputs.pnlBrokerSeriesRaw.map((broker) => ({brokerId: broker.brokerId, brokerName: broker.brokerName, metric: ladderMetric(broker.values, buckets)})),
            candle: ladderCandleMetric(inputs.pnlCandleByDate, buckets, inputs.dates),
            income: {dividend: ladderFlowMetric(inputs.dividendValues, buckets), interest: ladderFlowMetric(inputs.interestValues, buckets)},
            costs: ladderFlowMetric(inputs.costValues, buckets),
            deposits: ladderFlowMetric(inputs.depositValues, buckets),
            acquisition: {fromNewCapital: ladderFlowMetric(inputs.acqFromNewCapitalValues, buckets), fromReinvested: ladderFlowMetric(inputs.acqFromReinvestedValues, buckets)},
        },
    };
}

// =========================================================================
// The zoom window, read the way each axis draws it
// =========================================================================

/** How close, in days, a cascade window edge may fall to a drawn point and still stand on it: float and DST error, never a day the user chose. */
const ZOOM_EDGE_SNAP_DAYS = 0.1;
const cascadeDayOffsets = new WeakMap<AggregatedResolutionData, number[]>();

/**
 * Each cascade point, in days from the first one. The cascade draws on a time axis,
 * where ECharts maps a dataZoom percent to time over the drawn extent, not to a bucket
 * index: the two agree only while the points are evenly spaced, which a running
 * period, drawn on its last day, or a gap in the history breaks.
 */
export function cascadeDayOffsetsOf(entry: AggregatedResolutionData): number[] {
    let offsets = cascadeDayOffsets.get(entry);
    if (!offsets) {
        const first = entry.buckets[0]?.date ?? '';
        offsets = entry.buckets.map((bucket) => daysBetween(first, bucket.date));
        cascadeDayOffsets.set(entry, offsets);
    }
    return offsets;
}

/** The ladder buckets a dataZoom window shows. ECharts snaps a category window's edge to the NEAREST bucket, so it is read the way it is drawn. */
export function ladderIndicesAt(entry: AggregatedResolutionData, start: number, end: number): {startIndex: number; endIndex: number} {
    const maxIndex = Math.max(entry.buckets.length - 1, 0);
    const startIndex = Math.max(0, Math.min(maxIndex, Math.round((start / 100) * maxIndex)));
    const endIndex = Math.max(startIndex, Math.min(maxIndex, Math.round((end / 100) * maxIndex)));
    return {startIndex, endIndex};
}

/** The cascade buckets a dataZoom window shows, widened to the points at or outside its edges, so a partly visible period is never lost. */
export function cascadeIndicesAt(entry: AggregatedResolutionData, start: number, end: number): {startIndex: number; endIndex: number} {
    const offsets = cascadeDayOffsetsOf(entry);
    const maxIndex = offsets.length - 1;
    const span = offsets[maxIndex] ?? 0;
    if (maxIndex <= 0 || span <= 0) return {startIndex: 0, endIndex: Math.max(maxIndex, 0)};

    const startDay = (start / 100) * span;
    const endDay = (end / 100) * span;
    const startIndex = Math.max(
        0,
        offsets.findLastIndex((day) => day <= startDay + ZOOM_EDGE_SNAP_DAYS),
    );
    const firstAtEnd = offsets.findIndex((day) => day >= endDay - ZOOM_EDGE_SNAP_DAYS);
    const endIndex = Math.max(startIndex, firstAtEnd < 0 ? maxIndex : firstAtEnd);
    return {startIndex, endIndex};
}

/** The zoom percentages that put `entry`'s buckets holding `startDate` and `endDate` at the window edges. */
export function buildZoomWindow(entry: AggregatedResolutionData, startDate: string, endDate: string): {start: number; end: number} {
    if (entry.buckets.length <= 1) return {start: 0, end: 100};

    const startIndex = Math.max(
        0,
        entry.buckets.findIndex((bucket) => bucket.bucketEnd >= startDate),
    );
    const endIndex = Math.max(
        startIndex,
        entry.buckets.findLastIndex((bucket) => bucket.bucketStart <= endDate),
    );
    // The cascade's percent is time over its drawn extent, the ladder's an index.
    const offsets = entry.ladder ? null : cascadeDayOffsetsOf(entry);
    const span = offsets?.at(-1) ?? 0;
    if (offsets && span > 0) {
        return {
            start: (offsets[startIndex] / span) * 100,
            end: (offsets[endIndex] / span) * 100,
        };
    }
    const denominator = entry.buckets.length - 1;

    return {
        start: (startIndex / denominator) * 100,
        end: (endIndex / denominator) * 100,
    };
}
