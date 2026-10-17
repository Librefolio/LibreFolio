import {describe, expect, it} from 'vitest';

import {buildOverlaySignalSeries} from '$lib/components/charts/chartCoreHelpers';

import {renderBackendSignalResult, renderedSignalPointCount} from '../backendRenderer';
import {backendSignalSchemas, type BackendSignalResult} from '../backendTypes';
import type {RenderedSignal, SignalConfig, SignalDefinition} from '../ChartSignal';

/**
 * A line coloured by value region is not one ECharts series but one per stretch
 * of constant colour. An oscillator that crosses its threshold on most days
 * therefore asks for hundreds of series, and ECharts slows to a crawl long
 * before it refuses. The renderer caps them, merging the shortest stretches into
 * a neighbour — the cap is a performance decision, but "the line stays whole" is
 * the part the user sees.
 */

const config: SignalConfig = {
    id: 'rsi-instance',
    signalType: 'backend-signal',
    params: {},
    style: {color: '#3b82f6', lineWidth: 2, lineType: 'solid', markerStart: 'pin', markerEnd: 'arrow'},
};

const definition: SignalDefinition = {
    type: 'backend-signal',
    displayName: 'Backend signal',
    icon: 'activity',
    category: 'indicator',
    paramDescriptors: [],
    source: 'backend',
    visualComponents: [
        {
            key: 'rsi',
            labelKey: 'signals.rsi',
            kind: 'line',
            aggregationProfile: 'last_with_range',
            style: {colorRole: 'primary', lineWidthDelta: 0, opacity: 1, fillOpacity: 0.2},
            fullyPartitioned: true,
        },
    ],
};

const valueRegions = [
    {
        key: 'low',
        label_key: 'signals.rsi.low',
        semantic: 'oversold',
        upper: 50,
        include_lower: true,
        include_upper: false,
        line_style: {pattern: 'dashed', width_delta: 0},
    },
    {
        key: 'high',
        label_key: 'signals.rsi.high',
        semantic: 'overbought',
        lower: 50,
        include_lower: true,
        include_upper: false,
        line_style: {pattern: 'solid', width_delta: 1},
    },
];

function dateAt(index: number): string {
    return new Date(Date.UTC(2026, 0, 1 + index)).toISOString().slice(0, 10);
}

/**
 * A series whose value crosses the 50 threshold after each run, with runs of
 * cycling length so the merge has genuinely unequal neighbours to choose
 * between rather than a tie every time.
 */
function crossingSeries(runLengths: number[]) {
    const points: Array<{date: string; value: number}> = [];
    runLengths.forEach((length, runIndex) => {
        for (let step = 0; step < length; step++) {
            points.push({date: dateAt(points.length), value: runIndex % 2 === 0 ? 20 : 80});
        }
    });
    return {
        key: 'rsi',
        label_key: 'signals.rsi',
        semantic_id: 'test.rsi',
        semantic_description: 'Canonical test output for RSI.',
        unit: 'index',
        axis: {key: 'rsi', role: 'independent'},
        kind: 'line',
        points,
        value_regions: valueRegions,
    };
}

function result(series: unknown[]): BackendSignalResult {
    return backendSignalSchemas.result.parse({instance_id: config.id, signal_code: 'RSI', status: 'ok', series});
}

function render(series: unknown[], signalDefinition: SignalDefinition = definition) {
    return renderBackendSignalResult(result(series), config, {
        baseData: [{date: dateAt(0), value: 100}],
        viewMode: 'absolute',
        definition: signalDefinition,
    });
}

/** Run lengths 1..4, repeating — 250 points, so ~100 crossings. */
const manyRuns = Array.from({length: 100}, (_, index) => 1 + (index % 4));

describe('backend renderer — capping the number of styled slices', () => {
    it('leaves a modestly crossing line as one slice per stretch', () => {
        // Ten runs, ten slices: nothing is merged while ECharts can cope.
        const outcome = render([crossingSeries(Array.from({length: 10}, () => 3))]);

        expect(outcome.signals).toHaveLength(10);
        expect(outcome.signals.map((signal) => signal.lineType)).toEqual(['dashed', 'solid', 'dashed', 'solid', 'dashed', 'solid', 'dashed', 'solid', 'dashed', 'solid']);
    });

    it('caps a wildly crossing line at a hundred slices', () => {
        const outcome = render([crossingSeries(manyRuns)]);

        expect(outcome.signals.length).toBe(100);
    });

    it('keeps the whole line drawn after merging, from first date to last', () => {
        const points = manyRuns.reduce((total, length) => total + length, 0);
        const outcome = render([crossingSeries(manyRuns)]);

        expect(outcome.signals[0].data[0].date).toBe(dateAt(0));
        expect(outcome.signals.at(-1)!.data.at(-1)!.date).toBe(dateAt(points - 1));
    });

    it('leaves no gap between one slice and the next', () => {
        // Adjacent slices share their joining point, so the line reads as one
        // stroke rather than a dashed row of fragments.
        const outcome = render([crossingSeries(manyRuns)]);

        const joins = outcome.signals.slice(1).map((signal, index) => [outcome.signals[index].data.at(-1)!.date, signal.data[0].date]);
        expect(joins.filter(([previousEnd, nextStart]) => previousEnd !== nextStart)).toEqual([]);
    });

    it('visits every point exactly once, counting each join once', () => {
        const points = manyRuns.reduce((total, length) => total + length, 0);
        const outcome = render([crossingSeries(manyRuns)]);

        // Each of the 99 joins repeats one point, so the slices hold
        // points + joins dates in total and none is skipped.
        const dates = outcome.signals.flatMap((signal) => signal.data.map((point) => point.date));
        expect(dates).toHaveLength(points + outcome.signals.length - 1);
        expect(new Set(dates).size).toBe(points);
    });

    it('keeps the end markers at the two ends of the line, not on every slice', () => {
        const outcome = render([crossingSeries(manyRuns)]);

        expect(outcome.signals[0].markerStart).toBe('pin');
        expect(outcome.signals.at(-1)!.markerEnd).toBe('arrow');
        expect(outcome.signals.slice(1).every((signal) => signal.markerStart === null)).toBe(true);
        expect(outcome.signals.slice(0, -1).every((signal) => signal.markerEnd === null)).toBe(true);
    });

    it('caps a line that crosses on every single point', () => {
        // The worst case: 200 runs of one point each, all the same length, so
        // the merge has nothing but ties to break.
        const outcome = render([crossingSeries(Array.from({length: 200}, () => 1))]);

        expect(outcome.signals.length).toBe(100);
        expect(outcome.signals.at(-1)!.data.at(-1)!.date).toBe(dateAt(199));
    });

    it('absorbs a one-day stretch at the very end rather than dropping it', () => {
        // The last day crosses the threshold on its own — the shortest stretch
        // of all, and the one with only a neighbour behind it.
        const runs = [...Array.from({length: 120}, () => 3), 1];
        const points = runs.reduce((total, length) => total + length, 0);
        const outcome = render([crossingSeries(runs)]);

        expect(outcome.signals.length).toBe(100);
        expect(outcome.signals.at(-1)!.data.at(-1)!.date).toBe(dateAt(points - 1));
    });
});

describe('backend renderer — definitions it refuses to render', () => {
    it('refuses to render a locally-computed signal as a backend one', () => {
        const local: SignalDefinition = {...definition, source: 'local', visualComponents: undefined};

        expect(() => renderBackendSignalResult(result([crossingSeries([3])]), config, {baseData: [], viewMode: 'absolute', definition: local})).toThrow(/backend-owned/);
    });

    it('refuses a series the definition never declared', () => {
        // Backend and frontend disagree about the shape of this signal; drawing
        // an unstyled guess would hide the mismatch.
        const series = {...crossingSeries([3]), key: 'macd'};

        expect(() => render([series])).toThrow(/macd/);
    });
});

/**
 * J-21. A point the backend sends WITHOUT a value (`value: null`) is a hole in
 * the line: the calendar Rolling Return when the reference price is missing
 * mid-series, a Sharpe or Beta window with zero variance. The chart joins the
 * gaps of a series (`connectNulls` defaults to true), so a line that merely
 * dropped those points drew a segment across a day nothing was measured on.
 *
 * A day ABSENT from `points` is something else: an indicator computed on quote
 * days sends no point at all for a carried day of the axis (a weekend), and the
 * line must keep joining it. So a line or area output is cut into runs at the
 * points sent without a value, and the chart keeps joining absent days inside
 * each run.
 */

type SentPoint = {date: string; value: number | null};

/** One point per value on consecutive days from `dateAt(0)`; a `null` is a day sent without a value. */
function daily(values: Array<number | null>): SentPoint[] {
    return values.map((value, index) => ({date: dateAt(index), value}));
}

/** The chart's date axis: every day from `dateAt(0)`, whether or not a point was sent for it. */
function axisDays(count: number): string[] {
    return Array.from({length: count}, (_, index) => dateAt(index));
}

/** An output as the backend sends it, unstyled unless `extra` adds value regions or reference levels. */
function sentSeries(key: string, kind: 'line' | 'area' | 'bar', points: SentPoint[], extra: Record<string, unknown> = {}) {
    return {
        key,
        label_key: `signals.${key}`,
        semantic_id: `test.${key}`,
        semantic_description: `Canonical test output for ${key}.`,
        unit: 'index',
        axis: {key, role: 'independent'},
        kind,
        points,
        ...extra,
    };
}

function rsiLine(points: SentPoint[], extra: Record<string, unknown> = {}) {
    return sentSeries('rsi', 'line', points, extra);
}

/** `series` with the points at `indexes` sent without a value. */
function withoutValueAt(series: ReturnType<typeof crossingSeries>, indexes: number[]) {
    return {...series, points: series.points.map((point, index) => (indexes.includes(index) ? {date: point.date, value: null} : point))};
}

/** `definition` plus an AREA output, which the rule reaches, and a BAR output, which it does not. */
const kindsDefinition: SignalDefinition = {
    ...definition,
    visualComponents: [
        ...(definition.visualComponents ?? []),
        {key: 'drawdown', labelKey: 'signals.drawdown', kind: 'area', aggregationProfile: 'min_with_range', style: {colorRole: 'negative', lineWidthDelta: 0, opacity: 1, fillOpacity: 0.2}, fullyPartitioned: false},
        {key: 'histogram', labelKey: 'signals.histogram', kind: 'bar', aggregationProfile: 'last_with_range', style: {colorRole: 'primary', lineWidthDelta: 0, opacity: 1, fillOpacity: 0.2}, fullyPartitioned: false},
    ],
};

function datesOf(signals: RenderedSignal[]): string[][] {
    return signals.map((signal) => signal.data.map((point) => point.date));
}

/** The dates of every signal holding days on both sides of `gapDate`: a stroke across a day sent without a value. */
function signalsAcross(signals: RenderedSignal[], gapDate: string): string[][] {
    return datesOf(signals).filter((dates) => dates.some((date) => date < gapDate) && dates.some((date) => date > gapDate));
}

/** The data of every chart series holding a value on both sides of the axis index `gapIndex`: ECharts joins them across it. */
function seriesAcross(chartSeries: Array<{data: unknown[]}>, gapIndex: number): unknown[][] {
    return chartSeries.map((series) => series.data).filter((data) => data.slice(0, gapIndex).some((value) => value !== null) && data.slice(gapIndex + 1).some((value) => value !== null));
}

/** What a run keeps of the line it was cut from. */
function lineIdentity(signal: RenderedSignal) {
    return {label: signal.label, axisKey: signal.axisKey, axisRole: signal.axisRole, unit: signal.unit, seriesType: signal.seriesType, aggregationProfile: signal.aggregationProfile, color: signal.color, lineWidth: signal.lineWidth, lineType: signal.lineType};
}

/** The ids outside `${config.id}:${seriesKey}:`, and the ids given twice. */
function idProblems(signals: RenderedSignal[], seriesKey: string) {
    const ids = signals.map((signal) => signal.id);
    return {outsidePrefix: ids.filter((id) => !id.startsWith(`${config.id}:${seriesKey}:`)), repeated: ids.filter((id, index) => ids.indexOf(id) !== index)};
}

describe('backend renderer — a point the backend sent without a value breaks the line', () => {
    it('cuts the line in two at that point, each run the same line under an id of its own', () => {
        // Premise: without the null the same output is one line, the one whose attributes each run keeps.
        const whole = render([rsiLine(daily([40, 45, 50, 60, 65]))]).signals;
        expect(whole).toHaveLength(1);

        const outcome = render([rsiLine(daily([40, 45, null, 60, 65]))]);

        expect(outcome.signals.map((signal) => signal.data)).toEqual([
            [
                {date: dateAt(0), value: 40},
                {date: dateAt(1), value: 45},
            ],
            [
                {date: dateAt(3), value: 60},
                {date: dateAt(4), value: 65},
            ],
        ]);
        expect(outcome.signals.map(lineIdentity)).toEqual(outcome.signals.map(() => lineIdentity(whole[0])));
        expect(idProblems(outcome.signals, 'rsi')).toEqual({outsidePrefix: [], repeated: []});
    });

    it('gives the chart no series joining the two sides of that point, while every series still joins absent days', () => {
        const axis = axisDays(5);
        const gapIndex = axis.indexOf(dateAt(2));
        const {signals} = render([rsiLine(daily([40, 45, null, 60, 65]))]);

        const chartSeries = buildOverlaySignalSeries(signals, axis, false);

        // Premise: every series is a line, the type `connectNulls` governs.
        expect(chartSeries.map((series) => series.type)).toEqual(chartSeries.map(() => 'line'));
        expect(seriesAcross(chartSeries, gapIndex)).toEqual([]);
        expect(chartSeries.map((series) => series.connectNulls)).toEqual(chartSeries.map(() => true));
        // Nothing sent with a value is lost: each of those days is drawn by exactly one series.
        expect(axis.map((_, index) => chartSeries.map((series) => series.data[index]).filter((value) => value !== null))).toEqual([[40], [45], [], [60], [65]]);
    });

    it('keeps one line across the axis days the backend sent no point for', () => {
        // Premise: a quote-day indicator has no point at all on the weekend of 3-4
        // January 2026, which the daily axis still carries; nothing was sent
        // without a value.
        const axis = axisDays(6);
        const weekend = [dateAt(2), dateAt(3)];
        const outcome = render([
            rsiLine([
                {date: dateAt(0), value: 40},
                {date: dateAt(1), value: 45},
                {date: dateAt(4), value: 50},
                {date: dateAt(5), value: 55},
            ]),
        ]);

        expect(outcome.signals.map((signal) => signal.id)).toEqual([`${config.id}:rsi`]);
        const chartSeries = buildOverlaySignalSeries(outcome.signals, axis, false);
        expect(chartSeries).toHaveLength(1);
        expect(chartSeries[0]).toMatchObject({type: 'line', connectNulls: true, data: [40, 45, null, null, 50, 55]});
        expect(axis.filter((_, index) => chartSeries[0].data[index] === null)).toEqual(weekend);
    });

    it('cuts at the point sent without a value, not at the absent weekend inside a run', () => {
        // Thursday 1 to Thursday 8 January 2026: no point on the weekend of 3-4,
        // a point without a value on Tuesday 6.
        const axis = axisDays(8);
        const outcome = render([
            rsiLine([
                {date: dateAt(0), value: 40},
                {date: dateAt(1), value: 45},
                {date: dateAt(4), value: 50},
                {date: dateAt(5), value: null},
                {date: dateAt(6), value: 60},
                {date: dateAt(7), value: 65},
            ]),
        ]);

        expect(datesOf(outcome.signals)).toEqual([
            [dateAt(0), dateAt(1), dateAt(4)],
            [dateAt(6), dateAt(7)],
        ]);
        const chartSeries = buildOverlaySignalSeries(outcome.signals, axis, false);
        expect(seriesAcross(chartSeries, axis.indexOf(dateAt(5)))).toEqual([]);
        // Friday and Monday are one series, joined across the weekend.
        expect(chartSeries.filter((series) => series.data[1] !== null && series.data[4] !== null).map((series) => series.connectNulls)).toEqual([true]);
    });

    it('leaves one line when the points without a value all come before the first value or after the last', () => {
        // Premise: a warm-up is sent as points without a value before the first
        // value, and a series may end the same way.
        const outcome = render([rsiLine(daily([null, null, 40, 45, 50, null, null]))]);

        expect(outcome.signals.map((signal) => signal.id)).toEqual([`${config.id}:rsi`]);
        expect(outcome.signals[0].data).toEqual([
            {date: dateAt(2), value: 40},
            {date: dateAt(3), value: 45},
            {date: dateAt(4), value: 50},
        ]);
        expect([outcome.signals[0].markerStart, outcome.signals[0].markerEnd]).toEqual(['pin', 'arrow']);
    });

    it('makes one gap of consecutive points sent without a value', () => {
        // Premise: days 2 and 3 are both sent without a value.
        const outcome = render([rsiLine(daily([40, 45, null, null, 60, 65]))]);

        expect(datesOf(outcome.signals)).toEqual([
            [dateAt(0), dateAt(1)],
            [dateAt(4), dateAt(5)],
        ]);
    });

    it('keeps the start marker on the first run and the end marker on the last: the two ends of the whole line', () => {
        // Premise: the config asks for a pin where the line starts and an arrow where it ends.
        expect([config.style.markerStart, config.style.markerEnd]).toEqual(['pin', 'arrow']);

        const outcome = render([rsiLine(daily([40, 45, null, 50, 55, null, 60, 65]))]);

        expect(outcome.signals.map((signal) => [signal.markerStart, signal.markerEnd])).toEqual([
            ['pin', null],
            [null, null],
            [null, 'arrow'],
        ]);
    });

    it('draws the reference level and the background region of an unstyled line once, with its first run', () => {
        const levelAndRegion = {
            reference_levels: [{key: 'zero', label_key: 'signals.reference.zero', semantic: 'No change.', value: 0}],
            value_regions: [{key: 'high', label_key: 'signals.rsi.high', semantic: 'overbought', lower: 70}],
        };
        // Premise: the region has no line style, so without the gap the line is one signal carrying both.
        const whole = render([rsiLine(daily([40, 45, 50, 60, 75]), levelAndRegion)]).signals;
        expect(whole.map((signal) => [signal.referenceLevels?.map((level) => level.key), signal.valueRegions?.map((region) => region.key)])).toEqual([[['zero'], ['high']]]);

        const outcome = render([rsiLine(daily([40, 45, null, 60, 75]), levelAndRegion)]);

        expect(outcome.signals.map((signal) => signal.referenceLevels?.map((level) => level.key))).toEqual([['zero'], undefined]);
        expect(outcome.signals.map((signal) => signal.valueRegions?.map((region) => region.key))).toEqual([['high'], undefined]);
        // In the chart: one markLine and one markArea, not one per run stacked on each other.
        const chartSeries = buildOverlaySignalSeries(outcome.signals, axisDays(5), false);
        expect(chartSeries.filter((series) => series.markLine).length).toBe(1);
        expect(chartSeries.filter((series) => series.markArea).length).toBe(1);
    });

    it('cuts a styled line into its slices within each run, never across the gap', () => {
        // Premise: below 50 the line is dashed, from 50 solid; day 4 is sent without a value.
        const gapDate = dateAt(4);
        const outcome = render([rsiLine(daily([20, 20, 80, 80, null, 20, 20, 80, 80]), {value_regions: valueRegions})]);

        expect(signalsAcross(outcome.signals, gapDate)).toEqual([]);
        // Within each run, the slicing of an unbroken line: 20, 20, 80, 80 is a
        // dashed and a solid slice sharing their join.
        expect(datesOf(outcome.signals)).toEqual([
            [dateAt(0), dateAt(1)],
            [dateAt(1), dateAt(2), dateAt(3)],
            [dateAt(5), dateAt(6)],
            [dateAt(6), dateAt(7), dateAt(8)],
        ]);
        expect(outcome.signals.map((signal) => signal.lineType)).toEqual(['dashed', 'solid', 'dashed', 'solid']);
        expect(outcome.signals.map((signal) => [signal.markerStart, signal.markerEnd])).toEqual([
            ['pin', null],
            [null, null],
            [null, null],
            [null, 'arrow'],
        ]);
        // As on an unbroken styled line, no slice carries the levels or the regions.
        expect(outcome.signals.filter((signal) => signal.referenceLevels !== undefined || signal.valueRegions !== undefined)).toEqual([]);
        expect(idProblems(outcome.signals, 'rsi')).toEqual({outsidePrefix: [], repeated: []});
    });

    it('caps a wildly crossing line cut by two gaps without merging any slice across them', () => {
        // 160 stretches of cycling length 1..4, 400 points; two points sent
        // without a value cut the line into three runs.
        const stretches = Array.from({length: 160}, (_, index) => 1 + (index % 4));
        const gapIndexes = [133, 266];
        const gapDates = gapIndexes.map((index) => dateAt(index));
        // Premise: unbroken, the same line asks for more slices than the cap and is capped.
        expect(render([crossingSeries(stretches)]).signals.length).toBe(100);

        const outcome = render([withoutValueAt(crossingSeries(stretches), gapIndexes)]);

        expect(outcome.signals.length).toBeLessThanOrEqual(100);
        expect(gapDates.flatMap((gapDate) => signalsAcross(outcome.signals, gapDate))).toEqual([]);
        // In date order: within a run consecutive slices share their join, and
        // only the two gaps separate a slice from the next.
        const joins = outcome.signals.slice(1).map((signal, index) => [outcome.signals[index].data.at(-1)!.date, signal.data[0].date]);
        expect(joins.filter(([end, start]) => end !== start && !gapDates.some((gapDate) => end < gapDate && gapDate < start))).toEqual([]);
        expect(joins.filter(([end, start]) => end !== start)).toHaveLength(gapDates.length);
        // Every value is still drawn; the two days without one are not.
        const drawn = new Set(datesOf(outcome.signals).flat());
        expect(drawn.size).toBe(400 - gapDates.length);
        expect(gapDates.filter((gapDate) => drawn.has(gapDate))).toEqual([]);
        expect(outcome.signals[0].markerStart).toBe('pin');
        expect(outcome.signals.at(-1)!.markerEnd).toBe('arrow');
        expect(outcome.signals.slice(1).every((signal) => signal.markerStart === null)).toBe(true);
        expect(outcome.signals.slice(0, -1).every((signal) => signal.markerEnd === null)).toBe(true);
    });

    it('leaves one slice per run when a styled line has more runs than the cap allows slices', () => {
        // Premise: one run of 20, 80 crosses the threshold and alone asks for two
        // slices; 120 such runs, each followed by a point without a value, ask for 240.
        expect(render([rsiLine(daily([20, 80]), {value_regions: valueRegions})]).signals).toHaveLength(2);
        const values = Array.from({length: 120}, () => [20, 80, null])
            .flat()
            .slice(0, -1);

        const outcome = render([rsiLine(daily(values), {value_regions: valueRegions})]);

        expect(outcome.signals.length).toBe(120);
        expect(datesOf(outcome.signals)).toEqual(Array.from({length: 120}, (_, run) => [dateAt(3 * run), dateAt(3 * run + 1)]));
    });

    it('never bridges a gap to stay under the cap: an unstyled line of 120 runs stays 120 lines', () => {
        // Premise: 120 runs of two points, one point without a value between each
        // pair: more runs than the cap's 100 slices.
        const values = Array.from({length: 120}, () => [40, 60, null])
            .flat()
            .slice(0, -1);

        const outcome = render([rsiLine(daily(values))]);

        expect(outcome.signals.length).toBe(120);
        expect(datesOf(outcome.signals)).toEqual(Array.from({length: 120}, (_, run) => [dateAt(3 * run), dateAt(3 * run + 1)]));
        expect(idProblems(outcome.signals, 'rsi')).toEqual({outsidePrefix: [], repeated: []});
    });

    it('cuts an AREA output the same way, each run still an area', () => {
        // Premise: the definition declares drawdown as an area output.
        const outcome = render([sentSeries('drawdown', 'area', daily([-2, -5, null, -3, -1]))], kindsDefinition);

        expect(outcome.signals.map((signal) => [signal.seriesType, signal.data.map((point) => point.date)])).toEqual([
            ['area', [dateAt(0), dateAt(1)]],
            ['area', [dateAt(3), dateAt(4)]],
        ]);
        expect(idProblems(outcome.signals, 'drawdown')).toEqual({outsidePrefix: [], repeated: []});
    });

    it('leaves a BAR output whole: bars are never joined, the point without a value is just not drawn', () => {
        // Premise: the definition declares histogram as a bar output.
        const outcome = render([sentSeries('histogram', 'bar', daily([1, -2, null, 3]))], kindsDefinition);

        expect(outcome.signals.map((signal) => [signal.id, signal.seriesType])).toEqual([[`${config.id}:histogram`, 'bar']]);
        expect(outcome.signals[0].data).toEqual([
            {date: dateAt(0), value: 1},
            {date: dateAt(1), value: -2},
            {date: dateAt(3), value: 3},
        ]);
    });
});

/**
 * The «📈N» badge of the signals panel (`SignalDataSummary.pointCount`) for a
 * backend instance: the number of distinct dates drawn across every signal the
 * instance rendered into. One instance renders into several signals — one per
 * output, one per slice of a line coloured by value region, one per run of a
 * line the backend broke (J-21) — so the longest of them undercounts, and their
 * sum counts twice the join two slices share and a date two outputs share.
 */
describe('signals panel badge — points of one backend instance', () => {
    it('counts each point of a styled line once, not only its longest slice', () => {
        // Premise: crossing the threshold twice, the line reaches the badge as
        // three slices of 2, 3 and 3 points that share their two joins.
        const {signals} = render([rsiLine(daily([20, 20, 80, 80, 20, 20]), {value_regions: valueRegions})]);
        expect(signals.map((signal) => signal.data.length)).toEqual([2, 3, 3]);

        expect(renderedSignalPointCount(signals)).toBe(6);
    });

    it('counts the points of every run of a line broken by a point sent without a value', () => {
        // Premise: the line reaches the badge as two runs of 2 and 3 points
        // (J-21); the day sent without a value is drawn by neither.
        const {signals} = render([rsiLine(daily([40, 45, null, 60, 65, 70]))]);
        expect(signals.map((signal) => signal.data.length)).toEqual([2, 3]);

        expect(renderedSignalPointCount(signals)).toBe(5);
    });

    it('counts once a date that two outputs of the instance both draw', () => {
        // Premise: a line output and a bar output, both drawn on the same four days.
        const {signals} = render([rsiLine(daily([40, 45, 50, 55])), sentSeries('histogram', 'bar', daily([1, -2, 3, -4]))], kindsDefinition);
        expect(datesOf(signals)).toEqual([axisDays(4), axisDays(4)]);

        expect(renderedSignalPointCount(signals)).toBe(4);
    });

    it('counts the points of a plain line', () => {
        // Premise: an unstyled line with a value on every point is one signal.
        const {signals} = render([rsiLine(daily([40, 45, 50, 55, 60]))]);
        expect(signals).toHaveLength(1);

        expect(renderedSignalPointCount(signals)).toBe(5);
    });

    it('is 0 for an instance that drew nothing', () => {
        // Premise: a warm-up longer than the history sends every point without
        // a value, and the instance renders no signal at all.
        const {signals} = render([rsiLine(daily([null, null, null]))]);
        expect(signals).toEqual([]);

        expect(renderedSignalPointCount(signals)).toBe(0);
    });

    it('counts the days of every output when the outputs do not cover the same days', () => {
        // Premise: the line is drawn on days 0-3 and the bar on days 2-5: six
        // days in all, two of them drawn by both outputs.
        const barDays = [1, -2, 3, -4].map((value, index) => ({date: dateAt(2 + index), value}));
        const {signals} = render([rsiLine(daily([40, 45, 50, 55])), sentSeries('histogram', 'bar', barDays)], kindsDefinition);
        expect(datesOf(signals)).toEqual([axisDays(4), axisDays(6).slice(2)]);

        expect(renderedSignalPointCount(signals)).toBe(6);
    });
});
