/**
 * Unit tests for timeSeriesAggregation.ts — shared chart bucketing and aggregation helpers.
 */
import {readFileSync} from 'node:fs';

import {describe, expect, it} from 'vitest';

import type {RenderedSignal} from '$lib/charts/signals';

import type {LineDataPoint} from '../LineChart.svelte';
import {
    CANDLE_MIN_SLOT_PX,
    aggregateEnvelope,
    aggregateLineSeries,
    aggregateOHLCV,
    aggregateSumSeries,
    bucketEventMarkers,
    cascadeResolution,
    chooseInitialResolution,
    chooseResolution,
    computeDensity,
    downsampleRenderedSignal,
    mapDateToBucket,
    selectSignalRepresentative,
    type BucketMeta,
    type ChartResolution,
} from '../timeSeriesAggregation';

type BucketedPoint = LineDataPoint & BucketMeta;
const sharedAggregationFixture = JSON.parse(readFileSync(new URL('../../../../../../backend/test_scripts/fixtures/signals/aggregation_profiles.v1.json', import.meta.url), 'utf8')) as {
    scalar_cases: Array<{
        points: Array<{date: string; value: string}>;
        expected: {
            representatives: Record<string, {date: string; value: string} | null>;
        };
    }>;
};

function pt(date: string, value: number, extra: Partial<LineDataPoint> = {}): LineDataPoint {
    return {
        date,
        value,
        ...extra,
    };
}

function signal(data: LineDataPoint[], extra: Partial<RenderedSignal> = {}): RenderedSignal {
    return {
        id: extra.id ?? 'sig-1',
        label: extra.label ?? 'Signal',
        data,
        color: extra.color ?? '#22c55e',
        lineWidth: extra.lineWidth ?? 2,
        lineType: extra.lineType ?? 'solid',
        markerStart: extra.markerStart ?? null,
        markerEnd: extra.markerEnd ?? null,
        aggregationProfile: extra.aggregationProfile ?? (extra.seriesType === 'band' ? 'band_envelope' : 'last_with_range'),
        yAxisIndex: extra.yAxisIndex ?? 0,
        seriesType: extra.seriesType,
        bandData: extra.bandData,
        iconUrl: extra.iconUrl ?? null,
        assetType: extra.assetType ?? null,
        opacity: extra.opacity ?? 1,
        currency: extra.currency ?? 'EUR',
        currencyFlag: extra.currencyFlag ?? '🇪🇺',
    };
}

function renderedBucket(date: string, bucketStart: string, bucketEnd: string): LineDataPoint {
    return pt(date, 0, {bucketStart, bucketEnd});
}

describe('timeSeriesAggregation', () => {
    // =========================================================================
    // mapDateToBucket
    // =========================================================================
    it('mapDateToBucket handles daily, ISO-week cross-year, and leap-year month buckets', () => {
        expect(mapDateToBucket('2026-01-05', 'daily')).toEqual({
            bucketStart: '2026-01-05',
            bucketEnd: '2026-01-05',
        });

        expect(mapDateToBucket('2025-12-31', 'weekly')).toEqual({
            bucketStart: '2025-12-29',
            bucketEnd: '2026-01-04',
        });

        expect(mapDateToBucket('2024-02-10', 'monthly')).toEqual({
            bucketStart: '2024-02-01',
            bucketEnd: '2024-02-29',
        });
    });

    // =========================================================================
    // aggregateLineSeries
    // =========================================================================
    it('aggregateLineSeries keeps end-of-period point and preserves staleDays semantics', () => {
        const points = [pt('2026-01-05', 100, {staleDays: 0}), pt('2026-01-06', 101, {staleDays: 1}), pt('2026-01-09', 105, {staleDays: 2}), pt('2026-01-12', 106, {staleDays: 0})];

        const result = aggregateLineSeries(points, 'weekly');

        expect(result).toHaveLength(2);

        const firstBucket = result[0] as BucketedPoint;
        expect(firstBucket).toMatchObject({
            date: '2026-01-09',
            value: 105,
            staleDays: 2,
            bucketStart: '2026-01-05',
            bucketEnd: '2026-01-11',
            resolution: 'weekly',
            sourcePointCount: 3,
            representativeDate: '2026-01-09',
        });

        const secondBucket = result[1] as BucketedPoint;
        expect(secondBucket).toMatchObject({
            date: '2026-01-12',
            value: 106,
            bucketStart: '2026-01-12',
            bucketEnd: '2026-01-18',
            resolution: 'weekly',
            sourcePointCount: 1,
            representativeDate: '2026-01-12',
        });
    });

    it('aggregateLineSeries returns empty array for empty input', () => {
        expect(aggregateLineSeries([], 'monthly')).toEqual([]);
    });

    // =========================================================================
    // aggregateSumSeries
    // =========================================================================
    //
    // The flow-series counterpart of aggregateLineSeries. It exists because a sparse
    // economic flow (a dividend, a fee, a deposit, a day's BUY funding) has no "current
    // balance" to read at the end of a bucket — only a sum of what occurred inside it.
    // Aggregating a flow with end-of-period semantics silently reports the LAST day's
    // value as the whole week's, which is both wrong and invisible: the chart still
    // renders, the bars are just too small. These tests pin the difference explicitly.

    it('aggregateSumSeries returns the ORIGINAL array by reference at daily resolution', () => {
        const points = [pt('2026-01-05', 10), pt('2026-01-06', 20)];

        expect(aggregateSumSeries(points, 'daily')).toBe(points);
    });

    it('aggregateSumSeries returns empty array for empty input', () => {
        expect(aggregateSumSeries([], 'weekly')).toEqual([]);
        expect(aggregateSumSeries([], 'monthly')).toEqual([]);
    });

    it('aggregateSumSeries sums every point in a weekly bucket and carries canonical bucket metadata', () => {
        // ISO weeks: 01-05..01-11 (Mon–Sun) then 01-12..01-18.
        const points = [pt('2026-01-05', 10), pt('2026-01-06', 20), pt('2026-01-09', 5), pt('2026-01-12', 7)];

        const result = aggregateSumSeries(points, 'weekly');

        expect(result).toHaveLength(2);
        expect(result[0] as BucketedPoint).toMatchObject({
            date: '2026-01-09',
            value: 35, // 10 + 20 + 5 — NOT 5, which end-of-period semantics would give
            bucketStart: '2026-01-05',
            bucketEnd: '2026-01-11',
            resolution: 'weekly',
            sourcePointCount: 3,
            representativeDate: '2026-01-09',
        });
        expect(result[1] as BucketedPoint).toMatchObject({date: '2026-01-12', value: 7, sourcePointCount: 1});
    });

    it('aggregateSumSeries differs from aggregateLineSeries on the same input — the whole reason it exists', () => {
        const points = [pt('2026-01-05', 10), pt('2026-01-06', 20), pt('2026-01-09', 5)];

        expect(aggregateSumSeries(points, 'weekly')[0].value).toBe(35);
        expect(aggregateLineSeries(points, 'weekly')[0].value).toBe(5);
    });

    it('aggregateSumSeries sums across a monthly bucket and starts each bucket from zero', () => {
        const points = [pt('2026-01-05', 100), pt('2026-01-20', 50), pt('2026-02-02', 8), pt('2026-02-27', 2)];

        const result = aggregateSumSeries(points, 'monthly');

        expect(result).toHaveLength(2);
        expect(result[0] as BucketedPoint).toMatchObject({value: 150, bucketStart: '2026-01-01', bucketEnd: '2026-01-31', sourcePointCount: 2});
        // February must be 10, not 160 — the accumulator resets per bucket, it does not run cumulatively.
        expect(result[1] as BucketedPoint).toMatchObject({value: 10, bucketStart: '2026-02-01', bucketEnd: '2026-02-28', sourcePointCount: 2});
    });

    it('aggregateSumSeries keeps signed values signed and can net a bucket to zero', () => {
        // Costs are negative, a legacy correction can be positive: the sum is signed
        // arithmetic, never a magnitude. A bucket that genuinely nets to 0 must report 0
        // (an event happened and cancelled out), not be dropped.
        const points = [pt('2026-01-05', -30), pt('2026-01-06', -12), pt('2026-01-07', 42)];

        const result = aggregateSumSeries(points, 'weekly');

        expect(result).toHaveLength(1);
        expect(result[0].value).toBe(0);
    });

    it('aggregateSumSeries sums a purely negative bucket without flipping its sign', () => {
        const points = [pt('2026-03-02', -3), pt('2026-03-03', -9)];

        expect(aggregateSumSeries(points, 'weekly')[0].value).toBe(-12);
    });

    it('aggregateSumSeries inherits every non-value field from the LAST point of the bucket', () => {
        // Only `value` is recomputed; the rest of the shape comes from the bucket's last
        // point (spread first, then overwritten) — the same convention aggregateLineSeries
        // uses, which is what keeps the two interchangeable at the call site.
        const points = [pt('2026-01-05', 10, {staleDays: 7, close: 111}), pt('2026-01-06', 20, {staleDays: 1, close: 222})];

        const result = aggregateSumSeries(points, 'weekly');

        expect(result[0]).toMatchObject({value: 30, staleDays: 1, close: 222});
    });

    it('aggregateSumSeries puts a cross-year ISO week in a single bucket', () => {
        // 2025-12-29 (Mon) .. 2026-01-04 (Sun) is one ISO week spanning two years.
        const points = [pt('2025-12-31', 4), pt('2026-01-02', 6), pt('2026-01-05', 1)];

        const result = aggregateSumSeries(points, 'weekly');

        expect(result).toHaveLength(2);
        expect(result[0] as BucketedPoint).toMatchObject({value: 10, bucketStart: '2025-12-29', bucketEnd: '2026-01-04'});
        expect(result[1].value).toBe(1);
    });

    it('aggregateSumSeries preserves total mass: the sum of the buckets equals the sum of the inputs', () => {
        const values = [3, -7, 11, 0, 25, -1, 4, 9, -12, 6];
        const points = values.map((v, i) => pt(`2026-01-${String(i + 1).padStart(2, '0')}`, v));
        const total = values.reduce((a, b) => a + b, 0);

        for (const resolution of ['weekly', 'monthly'] as const) {
            const bucketed = aggregateSumSeries(points, resolution);
            expect(bucketed.reduce((a, p) => a + p.value, 0)).toBe(total);
        }
    });

    // =========================================================================
    // aggregateOHLCV
    // =========================================================================
    it('aggregateOHLCV applies standard OHLCV bucket semantics with partial null volumes', () => {
        const points = [pt('2026-01-05', 11, {open: 10, high: 12, low: 9, close: 11, volume: 100}), pt('2026-01-06', 12, {open: 11, high: 13, low: 10, close: 12, volume: null}), pt('2026-01-09', 13, {open: 12, high: 14, low: 8, close: 13, volume: 150})];

        const result = aggregateOHLCV(points, 'weekly');

        expect(result).toHaveLength(1);
        expect(result[0]).toMatchObject({
            date: '2026-01-09',
            value: 13,
            open: 10,
            high: 14,
            low: 8,
            close: 13,
            volume: 250,
        });
        expect((result[0] as BucketedPoint).sourcePointCount).toBe(3);
    });

    it('aggregateOHLCV returns null volume when all volumes in bucket are nullish', () => {
        const points = [pt('2026-01-05', 11, {open: 10, high: 12, low: 9, close: 11, volume: null}), pt('2026-01-06', 12, {open: 11, high: 13, low: 10, close: 12})];

        const result = aggregateOHLCV(points, 'weekly');

        expect(result[0].volume).toBeNull();
        expect(result[0].value).toBe(12);
    });

    // =========================================================================
    // aggregateEnvelope
    // =========================================================================
    it('aggregateEnvelope uses upper=max, lower=min, middle=end-of-period', () => {
        const middle = [pt('2026-01-05', 100), pt('2026-01-06', 101), pt('2026-01-09', 105), pt('2026-01-12', 106)];

        const result = aggregateEnvelope([110, 112, 111, 120], middle, [90, 89, 92, 95], 'weekly');

        expect(result.middle).toHaveLength(2);
        expect(result.upper).toEqual([112, 120]);
        expect(result.lower).toEqual([89, 95]);
        expect(result.middle[0]).toMatchObject({date: '2026-01-09', value: 105});
        expect((result.middle[0] as BucketedPoint).sourcePointCount).toBe(3);
    });

    // =========================================================================
    // downsampleRenderedSignal
    // =========================================================================
    it('downsampleRenderedSignal downsamples line signals and preserves metadata', () => {
        const lineSignal = signal([pt('2026-01-05', 1), pt('2026-01-06', 2), pt('2026-01-09', 3), pt('2026-01-12', 4)], {id: 'line-1', label: 'EMA(14)', color: '#3b82f6', opacity: 0.7, yAxisIndex: 1});

        const result = downsampleRenderedSignal(lineSignal, 'weekly', [renderedBucket('2026-01-09', '2026-01-05', '2026-01-11')]);

        expect(result).not.toBe(lineSignal);
        expect(result.data).toEqual([
            expect.objectContaining({
                date: '2026-01-09',
                value: 3,
                representativeDate: '2026-01-09',
            }),
        ]);
        expect(result.id).toBe('line-1');
        expect(result.label).toBe('EMA(14)');
        expect(result.color).toBe('#3b82f6');
        expect(result.opacity).toBe(0.7);
        expect(result.yAxisIndex).toBe(1);
    });

    it('downsampleRenderedSignal downsamples band signals with envelope semantics', () => {
        const bandSignal = signal([pt('2026-01-05', 100), pt('2026-01-06', 101), pt('2026-01-09', 105), pt('2026-01-12', 106)], {
            id: 'bb-1',
            label: 'BB(20,2σ)',
            seriesType: 'band',
            bandData: {
                upper: [110, 112, 111, 120],
                middle: [100, 101, 105, 106],
                lower: [90, 89, 92, 95],
            },
        });

        const result = downsampleRenderedSignal(bandSignal, 'weekly', [renderedBucket('2026-01-09', '2026-01-05', '2026-01-11')]);

        expect(result.data).toEqual([
            expect.objectContaining({
                date: '2026-01-09',
                value: 105,
            }),
        ]);
        expect(result.bandData).toEqual({
            middle: [105],
            upper: [112],
            lower: [89],
            observedDates: [
                {
                    lower: '2026-01-06',
                    middle: '2026-01-09',
                    upper: '2026-01-06',
                },
            ],
        });
    });

    it('downsampleRenderedSignal keeps bar signals as end-of-period snapshots, not bucket sums', () => {
        const barSignal = signal([pt('2026-01-05', 1), pt('2026-01-06', 2), pt('2026-01-09', 3)], {seriesType: 'bar'});

        const result = downsampleRenderedSignal(barSignal, 'weekly', [renderedBucket('2026-01-09', '2026-01-05', '2026-01-11')]);

        expect(result.data).toEqual([
            expect.objectContaining({
                date: '2026-01-09',
                value: 3,
            }),
        ]);
    });

    it('downsampleRenderedSignal rejects malformed band data', () => {
        const malformedBandSignal = signal([pt('2026-01-05', 1), pt('2026-01-06', 2), pt('2026-01-09', 3)], {seriesType: 'band'});

        expect(() => downsampleRenderedSignal(malformedBandSignal, 'weekly', [renderedBucket('2026-01-09', '2026-01-05', '2026-01-11')])).toThrow('missing aligned bandData');
    });

    it('downsampleRenderedSignal returns same reference for daily fast-path', () => {
        const dailySignal = signal([pt('2026-01-05', 1)]);
        expect(downsampleRenderedSignal(dailySignal, 'daily', [pt('2026-01-05', 1)])).toBe(dailySignal);
    });

    it('preserves a Drawdown trough and its real date in a weekly bucket', () => {
        const drawdown = signal([pt('2026-01-05', 0), pt('2026-01-06', -20), pt('2026-01-09', -5)], {
            id: 'drawdown',
            seriesType: 'area',
            aggregationProfile: 'min_with_range',
        });

        const result = downsampleRenderedSignal(drawdown, 'weekly', [renderedBucket('2026-01-09', '2026-01-05', '2026-01-11')]);

        expect(result.data).toEqual([
            expect.objectContaining({
                date: '2026-01-09',
                value: -20,
                representativeDate: '2026-01-06',
                bucketStart: '2026-01-05',
                bucketEnd: '2026-01-11',
                sourcePointCount: 3,
            }),
        ]);
    });

    it('joins Signal and price by logical bucket when observed end dates differ', () => {
        const lastObservedThursday = signal([pt('2026-01-05', 1), pt('2026-01-08', 4)]);
        const result = downsampleRenderedSignal(lastObservedThursday, 'weekly', [renderedBucket('2026-01-09', '2026-01-05', '2026-01-11')]);

        expect(result.data).toEqual([
            expect.objectContaining({
                date: '2026-01-09',
                value: 4,
                representativeDate: '2026-01-08',
            }),
        ]);
    });

    it('matches the shared Python/TypeScript scalar representative fixture', () => {
        for (const fixtureCase of sharedAggregationFixture.scalar_cases) {
            const points = fixtureCase.points.map((point) => pt(point.date, Number(point.value)));
            for (const [profile, expected] of Object.entries(fixtureCase.expected.representatives)) {
                const representative = selectSignalRepresentative(points, profile as RenderedSignal['aggregationProfile']);
                expect(representative ? {date: representative.date, value: String(representative.value)} : null).toEqual(expected);
            }
        }
    });

    // =========================================================================
    // computeDensity
    // =========================================================================
    it('computeDensity returns bucket-per-pixel ratio and guards non-positive widths', () => {
        expect(computeDensity(130, 100)).toBe(1.3);
        expect(computeDensity(10, 0)).toBe(0);
        expect(computeDensity(10, -25)).toBe(0);
    });

    // =========================================================================
    // chooseResolution
    // =========================================================================
    it('chooseResolution covers all hysteresis transitions', () => {
        expect(chooseResolution('daily', {dailyCount: 131, weeklyCount: 20, monthlyCount: 5}, 100)).toBe('weekly');
        expect(chooseResolution('daily', {dailyCount: 80, weeklyCount: 12, monthlyCount: 3}, 100)).toBe('daily');

        expect(chooseResolution('weekly', {dailyCount: 79, weeklyCount: 12, monthlyCount: 3}, 100)).toBe('daily');
        expect(chooseResolution('weekly', {dailyCount: 100, weeklyCount: 131, monthlyCount: 20}, 100)).toBe('monthly');
        expect(chooseResolution('weekly', {dailyCount: 100, weeklyCount: 100, monthlyCount: 20}, 100)).toBe('weekly');

        expect(chooseResolution('monthly', {dailyCount: 100, weeklyCount: 79, monthlyCount: 20}, 100)).toBe('weekly');
        expect(chooseResolution('monthly', {dailyCount: 100, weeklyCount: 80, monthlyCount: 20}, 100)).toBe('monthly');
    });

    // =========================================================================
    // chooseInitialResolution
    // =========================================================================
    it('chooseInitialResolution cascades straight to monthly for a very dense cold-start dataset', () => {
        // ~26 years of daily prices (e.g. AAPL since ~2000: ~6500 trading days) at a normal
        // desktop plot width — dense enough to need 'monthly' immediately on first paint,
        // not just 'weekly'. chooseResolution('daily', ...) alone would get stuck at
        // 'weekly' (only one hysteresis hop), which is the exact bug this guards against.
        const counts = {dailyCount: 6500, weeklyCount: 1300, monthlyCount: 300};
        expect(chooseInitialResolution(counts, 800)).toBe('monthly');
    });

    it('chooseInitialResolution matches chooseResolution for a single-hop (weekly) density', () => {
        const counts = {dailyCount: 131, weeklyCount: 20, monthlyCount: 5};
        expect(chooseInitialResolution(counts, 100)).toBe('weekly');
    });

    it('chooseInitialResolution stays daily when density is low', () => {
        const counts = {dailyCount: 80, weeklyCount: 12, monthlyCount: 3};
        expect(chooseInitialResolution(counts, 100)).toBe('daily');
    });

    // =========================================================================
    // cascadeResolution
    // =========================================================================
    it('cascadeResolution jumps 2 tiers in one settled evaluation (weekly -> daily-density -> monthly)', () => {
        // Simulates a single decisive zoom-out that only fires ONE debounced recompute
        // (e.g. a fast gesture, or a programmatic dataZoom dispatch) but whose FINAL
        // settled density needs 2 hops from the current 'weekly' state. A single
        // chooseResolution('weekly', ...) call would only reach 'monthly' too here
        // (weekly's own high-density check), so also verify starting from 'daily'.
        const counts = {dailyCount: 6500, weeklyCount: 1300, monthlyCount: 300};
        expect(cascadeResolution('daily', counts, 800)).toBe('monthly');
        expect(cascadeResolution('weekly', counts, 800)).toBe('monthly');
        expect(cascadeResolution('monthly', counts, 800)).toBe('monthly');
    });

    it('cascadeResolution preserves hysteresis "stay put" memory in a dead zone (unlike restarting from daily)', () => {
        // densityDaily = 100/100 = 1.0 -> inside the [0.8, 1.3] dead zone: NOT low enough to
        // drop to 'daily' (needs < 0.8), NOT high enough to escalate further either.
        // Starting the cascade from the TRUE current resolution ('weekly') must stay
        // 'weekly' here — this is the whole point of hysteresis (avoid flapping around a
        // borderline density). Starting from 'daily' instead would wrongly stay 'daily'
        // (1.0 is not > 1.3), silently discarding the fact that the chart was already
        // zoomed to 'weekly' — which is why cascadeResolution takes `current` as a
        // parameter instead of always restarting from 'daily' like chooseInitialResolution.
        const counts = {dailyCount: 100, weeklyCount: 30, monthlyCount: 5};
        expect(cascadeResolution('weekly', counts, 100)).toBe('weekly');
        expect(cascadeResolution('daily', counts, 100)).toBe('daily'); // demonstrates the divergence described above
        expect(chooseResolution('weekly', counts, 100)).toBe('weekly'); // sanity: single hop agrees here too
    });

    it('cascadeResolution matches a single chooseResolution hop when only one tier change is needed', () => {
        const counts = {dailyCount: 131, weeklyCount: 20, monthlyCount: 5};
        expect(cascadeResolution('daily', counts, 100)).toBe('weekly');
    });

    // =========================================================================
    // ChartGrammar — per-grammar density thresholds
    // =========================================================================

    // `CANDLE_MIN_SLOT_PX` is imported, never copied. A local copy would not fail if the
    // module's PROVISIONAL floor were raised — `slot >= 8` is still satisfied by a 12px
    // floor — so the test would keep passing while silently guarding a floor that no
    // longer exists. Importing makes the assertion track the value it is about.
    /** `DENSITY_THRESHOLDS.candle.high` — a slot may not shrink below CANDLE_MIN_SLOT_PX. */
    const CANDLE_HIGH_DENSITY = 1 / CANDLE_MIN_SLOT_PX; // 0.125 buckets/px
    /** `DENSITY_THRESHOLDS.candle.low` — the high one scaled by the line pair's own ratio. */
    const CANDLE_LOW_DENSITY = CANDLE_HIGH_DENSITY * (0.8 / 1.3); // ~0.0769 buckets/px

    /**
     * Bucket counts for an N-day window, counted the way the two real consumers count them:
     * distinct `mapDateToBucket` buckets, not `ceil(days / 7)`. Mirrors
     * `computeBucketCounts()` in GrowthChart.svelte and `countBuckets()` in
     * priceChartHelpers.ts, so the densities under test are the ones a chart actually
     * produces — partial ISO weeks and short months included.
     */
    function countsForWindow(days: number): {dailyCount: number; weeklyCount: number; monthlyCount: number} {
        const weekly = new Set<string>();
        const monthly = new Set<string>();
        const startMs = Date.UTC(2023, 0, 2); // a Monday, so the first ISO week starts whole

        for (let i = 0; i < days; i++) {
            const iso = new Date(startMs + i * 86_400_000).toISOString().slice(0, 10);
            weekly.add(mapDateToBucket(iso, 'weekly').bucketEnd);
            monthly.add(mapDateToBucket(iso, 'monthly').bucketEnd);
        }

        return {dailyCount: days, weeklyCount: weekly.size, monthlyCount: monthly.size};
    }

    function bucketCountFor(resolution: ChartResolution, counts: {dailyCount: number; weeklyCount: number; monthlyCount: number}): number {
        if (resolution === 'daily') return counts.dailyCount;
        return resolution === 'weekly' ? counts.weeklyCount : counts.monthlyCount;
    }

    it('omitting the grammar argument is identical to passing "line", over a resolution x counts x width matrix', () => {
        // Guards the module's "every existing caller keeps its previous behavior by
        // construction" claim by non-constructive means. Note the division of labour: this
        // pins `default === 'line'`, while what pins `'line' === the historical 1.3/0.8
        // pair` is the literal-valued 'chooseResolution covers all hysteresis transitions'
        // test above. The two together close the loop; neither does alone.
        const currents: ChartResolution[] = ['daily', 'weekly', 'monthly'];
        const widths = [100, 320, 580, 800, 1280];
        const countsMatrix = [
            {dailyCount: 80, weeklyCount: 12, monthlyCount: 3},
            {dailyCount: 131, weeklyCount: 20, monthlyCount: 5},
            {dailyCount: 100, weeklyCount: 131, monthlyCount: 20},
            {dailyCount: 100, weeklyCount: 79, monthlyCount: 20},
            {dailyCount: 6500, weeklyCount: 1300, monthlyCount: 300},
            countsForWindow(93),
            countsForWindow(365),
            countsForWindow(730),
            countsForWindow(1825),
        ];

        const seen = new Set<ChartResolution>();

        for (const counts of countsMatrix) {
            for (const width of widths) {
                const label = `counts=${JSON.stringify(counts)} width=${width}`;

                const initial = chooseInitialResolution(counts, width);
                expect(initial, `chooseInitialResolution ${label}`).toBe(chooseInitialResolution(counts, width, 'line'));
                seen.add(initial);

                for (const current of currents) {
                    const chosen = chooseResolution(current, counts, width);
                    expect(chosen, `chooseResolution('${current}') ${label}`).toBe(chooseResolution(current, counts, width, 'line'));
                    seen.add(chosen);

                    const cascaded = cascadeResolution(current, counts, width);
                    expect(cascaded, `cascadeResolution('${current}') ${label}`).toBe(cascadeResolution(current, counts, width, 'line'));
                    seen.add(cascaded);
                }
            }
        }

        // Non-vacuity: a matrix that only ever produced one resolution would satisfy every
        // equality above for free.
        expect([...seen].sort(), 'the matrix must exercise all three tiers').toEqual(['daily', 'monthly', 'weekly']);
    });

    it('a candle escalates where a line stays put, at the very same density', () => {
        // ~3 months of daily points in a dashboard-sized plot: 93 buckets / 580px = 0.16
        // buckets/px, i.e. a 6.2px slot.
        //   line   (high 1.3)   — nowhere near escalation; a continuous line at 6.2px is fine
        //   candle (high 0.125) — escalates; 6.2px cannot hold a body with two visible edges
        //                         plus a wick, which is the reported degeneration into a stroke
        const counts = countsForWindow(93);
        const plotWidth = 580;

        expect(chooseResolution('daily', counts, plotWidth, 'line')).toBe('daily');
        expect(chooseResolution('daily', counts, plotWidth, 'candle')).toBe('weekly');

        expect(cascadeResolution('daily', counts, plotWidth, 'line')).toBe('daily');
        expect(cascadeResolution('daily', counts, plotWidth, 'candle')).toBe('weekly');

        expect(chooseInitialResolution(counts, plotWidth, 'line')).toBe('daily');
        expect(chooseInitialResolution(counts, plotWidth, 'candle')).toBe('weekly');
    });

    it('every resolution the candle grammar chooses clears the minimum slot width', () => {
        // The property the thresholds exist to produce, stated as a property rather than as
        // a list of expected tiers: whatever tier is chosen, the slot it implies must be
        // renderable as a candle.
        const plotWidth = 580;
        const windows = [93, 365, 730, 1825]; // ~3 months, then 1 / 2 / 5 years
        let lineViolations = 0;

        for (const days of windows) {
            const counts = countsForWindow(days);

            const candle = chooseInitialResolution(counts, plotWidth, 'candle');
            const candleSlotPx = plotWidth / bucketCountFor(candle, counts);
            expect(candleSlotPx, `${days}-day window resolved to '${candle}' => ${candleSlotPx.toFixed(2)}px slot`).toBeGreaterThanOrEqual(CANDLE_MIN_SLOT_PX);

            const line = chooseInitialResolution(counts, plotWidth, 'line');
            if (plotWidth / bucketCountFor(line, counts) < CANDLE_MIN_SLOT_PX) lineViolations++;
        }

        // Non-vacuity: these windows have to be inside the defect zone, otherwise the
        // assertion above would hold for any thresholds at all. A statement about the
        // corpus, NOT a requirement on the line grammar — a line is continuous and is meant
        // to tolerate sub-pixel slots.
        expect(lineViolations, 'the chosen windows must be ones where the line thresholds do produce sub-8px slots').toBeGreaterThan(0);
    });

    it('the candle hysteresis band keeps the current resolution instead of flapping', () => {
        // 100 buckets / 1000px = 0.1 buckets/px — above the candle low threshold and below
        // the candle high one, i.e. inside the dead zone. Same inputs, two answers: the band
        // is the memory of where the chart came from, and it must survive the new parameter
        // rather than collapse to a single point or invert.
        const counts = {dailyCount: 100, weeklyCount: 15, monthlyCount: 4};
        const plotWidth = 1000;
        const density = counts.dailyCount / plotWidth;

        expect(density, 'fixture must sit above the candle low threshold').toBeGreaterThan(CANDLE_LOW_DENSITY);
        expect(density, 'fixture must sit below the candle high threshold').toBeLessThan(CANDLE_HIGH_DENSITY);

        expect(chooseResolution('daily', counts, plotWidth, 'candle')).toBe('daily');
        expect(chooseResolution('weekly', counts, plotWidth, 'candle')).toBe('weekly');
        expect(cascadeResolution('daily', counts, plotWidth, 'candle')).toBe('daily');
        expect(cascadeResolution('weekly', counts, plotWidth, 'candle')).toBe('weekly');
    });

    it('the candle grammar escalates just above its high threshold, and not at it', () => {
        const plotWidth = 1000;
        const justAbove = {dailyCount: 126, weeklyCount: 18, monthlyCount: 5}; // 0.126 buckets/px
        const atThreshold = {dailyCount: 125, weeklyCount: 18, monthlyCount: 5}; // 0.125 exactly

        expect(justAbove.dailyCount / plotWidth).toBeGreaterThan(CANDLE_HIGH_DENSITY);
        expect(atThreshold.dailyCount / plotWidth).toBe(CANDLE_HIGH_DENSITY);

        expect(chooseResolution('daily', justAbove, plotWidth, 'candle')).toBe('weekly');
        // The comparison is strict (`> high`), so sitting exactly on the threshold stays put.
        expect(chooseResolution('daily', atThreshold, plotWidth, 'candle')).toBe('daily');
        expect(cascadeResolution('daily', justAbove, plotWidth, 'candle')).toBe('weekly');
    });

    it('the candle grammar de-escalates below its low threshold, not merely below the line one', () => {
        const plotWidth = 1000;
        const belowCandleLow = {dailyCount: 76, weeklyCount: 12, monthlyCount: 3}; // 0.076 buckets/px
        const aboveCandleLow = {dailyCount: 78, weeklyCount: 12, monthlyCount: 3}; // 0.078 buckets/px

        expect(belowCandleLow.dailyCount / plotWidth).toBeLessThan(CANDLE_LOW_DENSITY);
        expect(aboveCandleLow.dailyCount / plotWidth).toBeGreaterThan(CANDLE_LOW_DENSITY);

        expect(chooseResolution('weekly', belowCandleLow, plotWidth, 'candle')).toBe('daily');
        expect(cascadeResolution('weekly', belowCandleLow, plotWidth, 'candle')).toBe('daily');
        // Both densities are far below the LINE low threshold (0.8). Under a single shared
        // pair this one de-escalated too — the band sitting in the wrong place, which is the
        // other half of the same defect.
        expect(chooseResolution('weekly', aboveCandleLow, plotWidth, 'candle')).toBe('weekly');
    });

    it('cascadeResolution still multi-hops in one call under the candle grammar', () => {
        // Two years of daily points at 580px: escalating to 'weekly' leaves 105 buckets =
        // 0.18 buckets/px, still above the candle high threshold, so the settled answer is
        // two tiers away from 'daily'.
        const counts = countsForWindow(730);
        const plotWidth = 580;

        // One hop stops at the intermediate tier — chooseResolution's documented single-hop
        // contract, which the grammar parameter must not change either.
        expect(chooseResolution('daily', counts, plotWidth, 'candle')).toBe('weekly');

        // The cascade has to arrive at the final tier in the SAME call, or a chart that gets
        // exactly one settled evaluation per gesture sticks at 'weekly' until something else
        // happens to fire.
        expect(cascadeResolution('daily', counts, plotWidth, 'candle')).toBe('monthly');
        expect(chooseInitialResolution(counts, plotWidth, 'candle')).toBe('monthly');

        // The mirror: monthly -> weekly -> daily. NOTE this half cannot be red against the
        // pre-fix code and is therefore not evidence — the candle low threshold is BELOW the
        // line one, so anything that de-escalates under 'candle' also de-escalated under the
        // old shared pair. It is pinned because the cascade's contract is symmetric.
        const sparse = countsForWindow(30);
        expect(chooseResolution('monthly', sparse, plotWidth, 'candle')).toBe('weekly');
        expect(cascadeResolution('monthly', sparse, plotWidth, 'candle')).toBe('daily');
    });

    // =========================================================================
    // bucketEventMarkers
    // =========================================================================
    it('bucketEventMarkers keeps exact dates for daily buckets', () => {
        const markers = [
            {date: '2026-01-05', type: 'DIVIDEND'},
            {date: '2026-01-05', type: 'SPLIT'},
        ];

        const result = bucketEventMarkers(markers, 'daily');

        expect(result.get('2026-01-05')).toEqual(markers);
    });

    it('bucketEventMarkers groups weekly and monthly markers without dedup and sorts ascending', () => {
        const weeklyMarkers = [
            {date: '2026-01-02', type: 'DIVIDEND'},
            {date: '2025-12-30', type: 'SPLIT'},
            {date: '2025-12-31', type: 'DIVIDEND'},
        ];

        const weekly = bucketEventMarkers(weeklyMarkers, 'weekly');
        expect(weekly.get('2026-01-04')).toEqual([
            {date: '2025-12-30', type: 'SPLIT'},
            {date: '2025-12-31', type: 'DIVIDEND'},
            {date: '2026-01-02', type: 'DIVIDEND'},
        ]);

        const monthly = bucketEventMarkers(
            [
                {date: '2026-01-21', type: 'SPLIT'},
                {date: '2026-01-05', type: 'DIVIDEND'},
                {date: '2026-01-12', type: 'DIVIDEND'},
            ],
            'monthly',
        );

        expect(monthly.get('2026-01-31')).toEqual([
            {date: '2026-01-05', type: 'DIVIDEND'},
            {date: '2026-01-12', type: 'DIVIDEND'},
            {date: '2026-01-21', type: 'SPLIT'},
        ]);
    });

    it('bucketEventMarkers returns empty map for empty input', () => {
        expect(bucketEventMarkers([], 'monthly').size).toBe(0);
    });
});
