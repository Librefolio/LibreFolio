import {describe, expect, it} from 'vitest';

import {renderBackendSignalResult} from '../backendRenderer';
import {backendSignalSchemas, type BackendSignalResult} from '../backendTypes';
import type {SignalConfig, SignalDefinition} from '../ChartSignal';

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

function render(series: unknown[]) {
    return renderBackendSignalResult(result(series), config, {
        baseData: [{date: dateAt(0), value: 100}],
        viewMode: 'absolute',
        definition,
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
