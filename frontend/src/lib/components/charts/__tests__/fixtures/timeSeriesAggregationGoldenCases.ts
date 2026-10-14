/**
 * Input catalogue + capture harness for the `timeSeriesAggregation` golden corpus.
 *
 * WHAT THIS FILE IS
 * -----------------
 * The *inputs* and the *capture procedure*. It contains no expectations at all.
 * The expectations live in `timeSeriesAggregation.golden.v1.json`, recorded from
 * the implementation as it stood BEFORE the `groupPointsByBucket` refactor.
 *
 * WHY THE SPLIT MATTERS
 * ---------------------
 * An identity test written after a refactor compares the new code against itself
 * and passes forever while proving nothing. Keeping the recorded outputs in a
 * committed artefact — captured from the pre-refactor code — makes the
 * post-refactor assertion a real comparison against a frozen record.
 *
 * Both the test and the regeneration script call `captureGoldenCorpus()`, so the
 * two can never drift in *how* they observe the code; only the committed JSON
 * decides what the answer is supposed to be.
 *
 * SCOPE
 * -----
 * `groupPointsByBucket` (private, `timeSeriesAggregation.ts:59`) has exactly four
 * consumers, each verified by the enclosing function of the call site:
 *   - aggregateLineSeries  (:134)
 *   - aggregateSumSeries   (:158)
 *   - aggregateOHLCV       (:181)
 *   - aggregateEnvelope    (:239)  <- a full consumer, and additionally an
 *                                     indirect one, since it also delegates to
 *                                     aggregateLineSeries for its middle band.
 * `renderBuckets`, `signalGroups`, `downsampleRenderedSignal` and
 * `bucketEventMarkers` call `mapDateToBucket` directly and never reach
 * `groupPointsByBucket`, so they are deliberately NOT captured here.
 * `timeSeriesAggregationGolden.test.ts` re-derives that consumer set from the
 * source on every run, so this claim cannot rot silently.
 */

import {createHash} from 'node:crypto';

import type {LineDataPoint} from '../../LineChart.svelte';
// Explicit `.ts` specifier (allowed by `rewriteRelativeImportExtensions` in
// tsconfig.json): the regeneration script runs on plain `node`, whose ESM
// resolver does not guess extensions. Vite/Vitest resolve it identically.
import {aggregateEnvelope, aggregateLineSeries, aggregateOHLCV, aggregateSumSeries, type ChartResolution} from '../../timeSeriesAggregation.ts';

export const GOLDEN_FORMAT_VERSION = 1;

export const GOLDEN_RESOLUTIONS = ['daily', 'weekly', 'monthly'] as const satisfies readonly ChartResolution[];

/** The four `groupPointsByBucket` consumers, in declaration order. */
export const GOLDEN_FUNCTIONS = ['aggregateLineSeries', 'aggregateSumSeries', 'aggregateOHLCV', 'aggregateEnvelope'] as const;

export type GoldenFunction = (typeof GOLDEN_FUNCTIONS)[number];

export interface GoldenCase {
    /** Stable identifier; also the middle segment of every entry key. */
    id: string;
    /** Why this shape is in the corpus — i.e. what a grouping bug would do to it. */
    why: string;
    points: LineDataPoint[];
    /** Envelope bands, always `points.length` long, as `aggregateEnvelope` requires. */
    bands: {upper: number[]; lower: number[]};
}

/**
 * Input shapes, chosen because a *grouping* change breaks them — a happy-path
 * series agrees under almost any bucketing bug.
 *
 * Every date below was verified against the real `mapDateToBucket`, not assumed:
 * weekdays, ISO-week spans and month lengths are all as the comments state.
 */
export const GOLDEN_CASES: readonly GoldenCase[] = [
    {
        id: 'empty',
        why: 'No points at all: separates the length-0 guard from the grouping loop.',
        points: [],
        bands: {upper: [], lower: []},
    },
    {
        id: 'single-point-midweek',
        why: '2026-01-07 is a Wednesday inside week 01-05..01-11 and inside January: one point that sits at no boundary in any resolution.',
        points: [{date: '2026-01-07', value: 101.5}],
        bands: {upper: [103.5], lower: [99.5]},
    },
    {
        id: 'single-point-on-double-boundary',
        why: '2026-03-01 is a Sunday: the LAST day of ISO week 02-23..03-01 and the FIRST day of March. One point sitting on two opposite kinds of edge.',
        points: [{date: '2026-03-01', value: 55}],
        bands: {upper: [57], lower: [53]},
    },
    {
        id: 'all-missing-values',
        why: 'Every point unavailable. Real shape from priceChartHelpers.ts:176 — `value: 0` plus `missing: true`, never a null value. Crosses a week boundary so the flag has to survive grouping twice.',
        points: [
            {date: '2026-01-08', value: 0, missing: true},
            {date: '2026-01-09', value: 0, missing: true},
            {date: '2026-01-12', value: 0, missing: true},
            {date: '2026-01-13', value: 0, missing: true},
        ],
        bands: {upper: [0, 0, 0, 0], lower: [0, 0, 0, 0]},
    },
    {
        id: 'partial-missing-bucket',
        why: 'One bucket whose LAST point is available and one whose last point is missing. Pins which point the bucket inherits its flags from.',
        points: [
            {date: '2026-01-06', value: 100},
            {date: '2026-01-07', value: 0, missing: true},
            {date: '2026-01-08', value: 102},
            {date: '2026-01-12', value: 105},
            {date: '2026-01-13', value: 0, missing: true},
        ],
        bands: {upper: [101, 1, 103, 106, 1], lower: [99, -1, 101, 104, -1]},
    },
    {
        id: 'unaligned-start-midweek',
        why: 'Starts Wednesday 2026-01-07, so the first weekly bucket is partial (3 of 7 days) before a full one begins on Monday 01-12.',
        points: [
            {date: '2026-01-07', value: 100},
            {date: '2026-01-08', value: 101},
            {date: '2026-01-09', value: 99},
            {date: '2026-01-12', value: 104},
            {date: '2026-01-13', value: 103},
        ],
        bands: {upper: [102, 103, 101, 106, 105], lower: [98, 99, 97, 102, 101]},
    },
    {
        id: 'unaligned-start-midmonth',
        why: 'Starts 2026-01-29 and crosses into February INSIDE ISO week 01-26..02-01, so weekly and monthly disagree about where the split is.',
        points: [
            {date: '2026-01-29', value: 200},
            {date: '2026-01-30', value: 201},
            {date: '2026-01-31', value: 202},
            {date: '2026-02-01', value: 203},
            {date: '2026-02-02', value: 204},
        ],
        bands: {upper: [202, 203, 204, 205, 206], lower: [198, 199, 200, 201, 202]},
    },
    {
        id: 'month-end-31-january',
        why: '31-day month. 2026-01-31 is a Saturday, so Jan 30/31 and Feb 01 share ISO week 01-26..02-01 while splitting across two monthly buckets.',
        points: [
            {date: '2026-01-30', value: 10},
            {date: '2026-01-31', value: 11},
            {date: '2026-02-01', value: 12},
            {date: '2026-02-02', value: 13},
        ],
        bands: {upper: [11, 12, 13, 14], lower: [9, 10, 11, 12]},
    },
    {
        id: 'month-end-28-non-leap-february',
        why: '28-day February (2026). 02-28 is a Saturday and 03-01 a Sunday, so the month change again falls inside ISO week 02-23..03-01.',
        points: [
            {date: '2026-02-27', value: 20},
            {date: '2026-02-28', value: 21},
            {date: '2026-03-01', value: 22},
            {date: '2026-03-02', value: 23},
        ],
        bands: {upper: [21, 22, 23, 24], lower: [19, 20, 21, 22]},
    },
    {
        id: 'month-end-29-leap-february',
        why: '29-day February (2024). All four dates fall in the single ISO week 2024-02-26..03-03, so weekly yields ONE bucket where monthly yields two — the sharpest disagreement in the corpus.',
        points: [
            {date: '2024-02-27', value: 30},
            {date: '2024-02-28', value: 31},
            {date: '2024-02-29', value: 32},
            {date: '2024-03-01', value: 33},
        ],
        bands: {upper: [31, 32, 33, 34], lower: [29, 30, 31, 32]},
    },
    {
        id: 'month-end-30-april',
        why: '30-day month. 2026-04-29..05-02 all sit in ISO week 04-27..05-03: one weekly bucket, two monthly buckets.',
        points: [
            {date: '2026-04-29', value: 40},
            {date: '2026-04-30', value: 41},
            {date: '2026-05-01', value: 42},
            {date: '2026-05-02', value: 43},
        ],
        bands: {upper: [41, 42, 43, 44], lower: [39, 40, 41, 42]},
    },
    {
        id: 'iso-week-across-year-boundary',
        why: 'ISO week 2025-12-29..2026-01-04 spans the year change, so the weekly bucket key mixes two years while the monthly buckets do not.',
        points: [
            {date: '2025-12-30', value: 50},
            {date: '2025-12-31', value: 51},
            {date: '2026-01-01', value: 52},
            {date: '2026-01-02', value: 53},
            {date: '2026-01-05', value: 54},
        ],
        bands: {upper: [52, 53, 54, 55, 56], lower: [48, 49, 50, 51, 52]},
    },
    {
        id: 'multi-bucket-baseline',
        why: 'The ordinary case: 8 points over three ISO weeks and two months, nothing degenerate. The control against which the edge cases are read.',
        points: [
            {date: '2026-03-30', value: 100},
            {date: '2026-03-31', value: 102},
            {date: '2026-04-01', value: 101},
            {date: '2026-04-02', value: 105},
            {date: '2026-04-06', value: 107},
            {date: '2026-04-07', value: 106},
            {date: '2026-04-13', value: 110},
            {date: '2026-04-14', value: 109},
        ],
        bands: {
            upper: [103, 104, 106, 108, 109, 111, 112, 113],
            lower: [97, 99, 96, 100, 104, 101, 107, 105],
        },
    },
    {
        id: 'bucket-gap-skips-a-whole-week',
        why: 'Jumps from week 01-05..01-11 straight to week 01-19..01-25, skipping 01-12..01-18 entirely: grouping must not invent the empty bucket in between.',
        points: [
            {date: '2026-01-05', value: 60},
            {date: '2026-01-06', value: 61},
            {date: '2026-01-19', value: 62},
        ],
        bands: {upper: [61, 62, 63], lower: [59, 60, 61]},
    },
    {
        id: 'revisited-bucket-non-monotonic',
        why: 'Week A, week B, week A again. `groupPointsByBucket` only compares against the PREVIOUS group, so this yields three weekly groups; a Map-keyed rewrite would silently yield two. The single most load-bearing case for this refactor.',
        points: [
            {date: '2026-01-05', value: 70},
            {date: '2026-01-12', value: 71},
            {date: '2026-01-06', value: 72},
        ],
        bands: {upper: [71, 72, 73], lower: [69, 70, 71]},
    },
    {
        id: 'fully-unsorted-descending',
        why: 'Three Mondays in descending order. Weekly gives three buckets emitted newest-first; monthly gives ONE bucket whose representative is the input-order last point (2026-01-05) — the EARLIEST date. A rewrite that sorts would change both.',
        points: [
            {date: '2026-01-19', value: 80},
            {date: '2026-01-12', value: 81},
            {date: '2026-01-05', value: 82},
        ],
        bands: {upper: [81, 82, 83], lower: [79, 80, 81]},
    },
    {
        id: 'duplicate-dates',
        why: 'Two points share 2026-01-07. Both must stay inside one bucket and count towards sourcePointCount; neither may be deduplicated.',
        points: [
            {date: '2026-01-07', value: 90},
            {date: '2026-01-07', value: 91},
            {date: '2026-01-08', value: 92},
        ],
        bands: {upper: [91, 92, 93], lower: [89, 90, 91]},
    },
    {
        id: 'signed-values-netting-to-zero',
        why: 'A flow bucket whose members cancel out (-5 + 5 + 0 = 0) plus a purely negative one, with bands that straddle zero. Separates "summed to zero" from "no data".',
        points: [
            {date: '2026-01-05', value: -5},
            {date: '2026-01-06', value: 5},
            {date: '2026-01-07', value: 0},
            {date: '2026-01-12', value: -3},
        ],
        bands: {upper: [-3, 7, 2, -1], lower: [-7, 3, -2, -5]},
    },
    {
        id: 'metadata-carry-over',
        why: 'staleDays / fxStaleDays / originalCurrency / originalValue are inherited wholesale from the bucket representative. If grouping picks a different point, the currency badge and staleness shown to the user change with it.',
        points: [
            {date: '2026-01-06', value: 100, originalCurrency: 'USD', originalCurrencyFlag: '🇺🇸', originalValue: 110},
            {date: '2026-01-08', value: 101, staleDays: 2, fxStaleDays: 1, originalCurrency: 'USD', originalCurrencyFlag: '🇺🇸', originalValue: 111},
            {date: '2026-01-12', value: 102, staleDays: 4, originalCurrency: 'GBP', originalCurrencyFlag: '🇬🇧', originalValue: 88},
        ],
        bands: {upper: [101, 102, 103], lower: [99, 100, 101]},
    },
    {
        id: 'ohlcv-full',
        why: 'Complete candles over two ISO weeks inside one month: first open / max high / min low / last close / summed volume, exercised twice at weekly and once at monthly.',
        points: [
            {date: '2026-01-06', value: 104, open: 100, high: 105, low: 99, close: 104, volume: 1000},
            {date: '2026-01-08', value: 106, open: 104, high: 108, low: 103, close: 106, volume: 1200},
            {date: '2026-01-12', value: 102, open: 106, high: 107, low: 101, close: 102, volume: 900},
            {date: '2026-01-13', value: 103, open: 102, high: 104, low: 100, close: 103, volume: 1100},
        ],
        bands: {upper: [105, 108, 107, 104], lower: [99, 103, 101, 100]},
    },
    {
        id: 'ohlcv-all-fields-null',
        why: 'Every OHLCV field null. Drives the fallback ladder `close ?? lastPoint.close ?? lastPoint.value` and the `sawVolume` flag, so the candle has to be rebuilt out of `value` alone.',
        points: [
            {date: '2026-01-06', value: 11, open: null, high: null, low: null, close: null, volume: null},
            {date: '2026-01-07', value: 12, open: null, high: null, low: null, close: null, volume: null},
            {date: '2026-01-12', value: 13, open: null, high: null, low: null, close: null, volume: null},
        ],
        bands: {upper: [12, 13, 14], lower: [10, 11, 12]},
    },
    {
        id: 'ohlcv-sparse-fields',
        why: 'Holes in different fields on different days: the first open is null, some closes and volumes are null. Each of open/high/low/close/volume has to be resolved from a different member of the bucket.',
        points: [
            {date: '2026-01-06', value: 104, open: null, high: 105, low: 99, close: 104, volume: null},
            {date: '2026-01-07', value: 105, open: 104, high: null, low: null, close: null, volume: 1200},
            {date: '2026-01-12', value: 102, open: 106, high: 107, low: null, close: 102, volume: null},
            {date: '2026-01-13', value: 103, open: null, high: null, low: 100, close: null, volume: 300},
        ],
        bands: {upper: [105, 106, 107, 104], lower: [99, 100, 101, 100]},
    },
    {
        id: 'ohlcv-without-any-ohlcv-fields',
        why: 'A plain line series pushed through aggregateOHLCV, which PriceChartFull does whenever the source has no candles. Every OHLCV key is absent rather than null — a different branch from `ohlcv-all-fields-null`.',
        points: [
            {date: '2026-01-06', value: 21},
            {date: '2026-01-07', value: 22},
            {date: '2026-01-12', value: 23},
        ],
        bands: {upper: [22, 23, 24], lower: [20, 21, 22]},
    },
];

// =============================================================================
// Faithful encoding
// =============================================================================

export type EncodedValue = string | number | boolean | null | EncodedValue[] | {[key: string]: EncodedValue};

const UNDEFINED_TAG = '__undefined__';
const NAN_TAG = '__NaN__';
const POSITIVE_INFINITY_TAG = '__Infinity__';
const NEGATIVE_INFINITY_TAG = '__-Infinity__';
const NEGATIVE_ZERO_TAG = '__-0__';

/**
 * Encode a captured value into something JSON can hold WITHOUT losing the
 * distinctions that matter here.
 *
 * Plain `JSON.stringify` would drop `undefined` properties entirely (erasing the
 * difference between "key absent" and "key present but undefined"), and would
 * flatten NaN / ±Infinity / -0 into `null` or `0`. If today's code produces any
 * of those, the golden has to say so — the record is of what the code does,
 * warts included, not of what it ought to do.
 */
export function encodeCaptured(value: unknown): EncodedValue {
    if (value === undefined) return UNDEFINED_TAG;
    if (value === null) return null;

    if (typeof value === 'number') {
        if (Number.isNaN(value)) return NAN_TAG;
        if (value === Number.POSITIVE_INFINITY) return POSITIVE_INFINITY_TAG;
        if (value === Number.NEGATIVE_INFINITY) return NEGATIVE_INFINITY_TAG;
        if (Object.is(value, -0)) return NEGATIVE_ZERO_TAG;
        return value;
    }

    if (typeof value === 'boolean') return value;

    if (typeof value === 'string') {
        // A payload string shaped like a sentinel would make the encoding
        // ambiguous. No fixture contains one; fail loudly rather than let one in.
        if (/^__.*__$/.test(value)) throw new Error(`Golden capture refuses the ambiguous string '${value}': it collides with a sentinel tag`);
        return value;
    }

    if (Array.isArray(value)) return value.map(encodeCaptured);

    if (typeof value === 'object') {
        const source = value as Record<string, unknown>;
        const encoded: Record<string, EncodedValue> = {};
        for (const key of Object.keys(source).sort()) encoded[key] = encodeCaptured(source[key]);
        return encoded;
    }

    throw new Error(`Golden capture cannot encode a ${typeof value}`);
}

/** Stable JSON text: object keys sorted at every depth, so the digest ignores key order and file formatting. */
export function canonicalStringify(value: EncodedValue): string {
    if (value === null || typeof value !== 'object') return JSON.stringify(value);
    if (Array.isArray(value)) return `[${value.map(canonicalStringify).join(',')}]`;
    return `{${Object.keys(value)
        .sort()
        .map((key) => `${JSON.stringify(key)}:${canonicalStringify(value[key])}`)
        .join(',')}}`;
}

// =============================================================================
// Capture
// =============================================================================

export interface GoldenEntry {
    /**
     * Whether the daily fast-path handed back the caller's own array. The module
     * documents this ("Daily path returns original array by reference") and
     * callers such as PriceChartFull rely on it for cache identity, so it is part
     * of the observable behaviour, not an implementation detail.
     */
    returnsInputByReference: boolean | {upper: boolean; middle: boolean; lower: boolean};
    /** Whether the call mutated the arrays/objects it was handed. Today: never. */
    mutatedInput: boolean;
    result: EncodedValue;
}

export type GoldenEntries = Record<string, GoldenEntry>;

export interface GoldenCorpus {
    formatVersion: number;
    entries: GoldenEntries;
}

export function goldenKey(fn: GoldenFunction, caseId: string, resolution: ChartResolution): string {
    return `${fn}|${caseId}|${resolution}`;
}

/** Fresh, independent copies so identity and mutation checks mean something. */
function clonePoints(points: readonly LineDataPoint[]): LineDataPoint[] {
    return points.map((point) => ({...point}));
}

function captureArrayFunction(fn: (points: LineDataPoint[], resolution: ChartResolution) => LineDataPoint[], goldenCase: GoldenCase, resolution: ChartResolution): GoldenEntry {
    const input = clonePoints(goldenCase.points);
    const before = canonicalStringify(encodeCaptured(input));
    const result = fn(input, resolution);
    const after = canonicalStringify(encodeCaptured(input));

    return {
        returnsInputByReference: result === input,
        mutatedInput: before !== after,
        result: encodeCaptured(result),
    };
}

function captureEnvelope(goldenCase: GoldenCase, resolution: ChartResolution): GoldenEntry {
    const upper = [...goldenCase.bands.upper];
    const middle = clonePoints(goldenCase.points);
    const lower = [...goldenCase.bands.lower];
    const before = canonicalStringify(encodeCaptured({upper, middle, lower}));
    const result = aggregateEnvelope(upper, middle, lower, resolution);
    const after = canonicalStringify(encodeCaptured({upper, middle, lower}));

    return {
        returnsInputByReference: {
            upper: result.upper === upper,
            middle: result.middle === middle,
            lower: result.lower === lower,
        },
        mutatedInput: before !== after,
        result: encodeCaptured(result),
    };
}

function captureEntry(fn: GoldenFunction, goldenCase: GoldenCase, resolution: ChartResolution): GoldenEntry {
    if (fn === 'aggregateLineSeries') return captureArrayFunction(aggregateLineSeries, goldenCase, resolution);
    if (fn === 'aggregateSumSeries') return captureArrayFunction(aggregateSumSeries, goldenCase, resolution);
    if (fn === 'aggregateOHLCV') return captureArrayFunction(aggregateOHLCV, goldenCase, resolution);
    return captureEnvelope(goldenCase, resolution);
}

/**
 * Run every function over every case at every resolution, against whatever the
 * module does right now. The test compares this to the committed JSON; the
 * regeneration script writes it there. Nothing here decides what is correct.
 */
export function captureGoldenCorpus(): GoldenCorpus {
    const entries: GoldenEntries = {};

    for (const fn of GOLDEN_FUNCTIONS) {
        for (const goldenCase of GOLDEN_CASES) {
            for (const resolution of GOLDEN_RESOLUTIONS) {
                entries[goldenKey(fn, goldenCase.id, resolution)] = captureEntry(fn, goldenCase, resolution);
            }
        }
    }

    return {formatVersion: GOLDEN_FORMAT_VERSION, entries};
}

/**
 * Tamper-evident digest over the recorded entries only.
 *
 * Computed from the canonical form, so reformatting the JSON (prettier does
 * reformat it) cannot change it, while altering a single recorded number does.
 * The expected value is a literal in `timeSeriesAggregationGolden.test.ts`,
 * which the regeneration script deliberately never writes: regenerating the
 * fixture therefore leaves the suite RED until a human copies the new digest
 * across, having looked at the diff that produced it.
 *
 * `meta` is excluded on purpose — prose about provenance is for humans, and
 * pinning it would make the digest churn for reasons unrelated to behaviour.
 */
export function goldenDigest(entries: GoldenEntries): string {
    return `sha256:${createHash('sha256')
        .update(canonicalStringify(entries as unknown as EncodedValue))
        .digest('hex')}`;
}

/** Every key the corpus must contain, in deterministic order. */
export function expectedGoldenKeys(): string[] {
    const keys: string[] = [];
    for (const fn of GOLDEN_FUNCTIONS) {
        for (const goldenCase of GOLDEN_CASES) {
            for (const resolution of GOLDEN_RESOLUTIONS) keys.push(goldenKey(fn, goldenCase.id, resolution));
        }
    }
    return keys;
}
