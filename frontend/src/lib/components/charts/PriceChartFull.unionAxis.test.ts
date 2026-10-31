// @vitest-environment jsdom
/**
 * PriceChartFull — the axis of a chart whose comparison is older than its main series (Y2-CMP).
 *
 * The detail pages of an asset and of an FX pair put a comparison on the main chart. With «All», the chart starts on the older of the two: a main
 * series from 2010 with a comparison from 1985 draws from 1985, the main line empty until 2010 (no invented line, no zero). In the percentage view
 * each line is measured from its own first price: the main one is 0 % on its first day, the comparison on its own. The other way (a comparison
 * that starts after the main series) the axis is the main series' one, as it always was, and the comparison line starts on its own first day.
 * A signal asks for this with `extendsAxis` (the comparisons do; an indicator or a benchmark follows the main series' days).
 *
 * The real component, with ECharts replaced by a recorder (the `PriceChartFull.tooltipEscape.test.ts` pattern: jsdom has no canvas, pixels are not
 * the subject): the axis is `xAxis.data` of the last draw, a line is the `data` of its series, one value per day of the axis. The chart imports
 * `assetTypes.ts`, which reads the generated client at module load, so the modules are imported after asserting the generated file exists.
 *
 * Registered in `front_component_unit` (`scripts/test_runner/_frontend_utility.py`).
 */
import {existsSync} from 'node:fs';
import {join} from 'node:path';
import {afterEach, beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';

const {chartInstances, echartsModule} = vi.hoisted(() => {
    interface FakeChart {
        setOptionCalls: Array<{option: Record<string, unknown>}>;
        setOption: (option: Record<string, unknown>) => void;
        getOption: () => Record<string, unknown>;
        getWidth: () => number;
        getHeight: () => number;
        getDom: () => unknown;
        getZr: () => {on: () => void; off: () => void};
        on: () => void;
        off: () => void;
        dispatchAction: () => void;
        resize: () => void;
        containPixel: () => boolean;
        convertFromPixel: () => null;
        isDisposed: () => boolean;
        dispose: () => void;
    }
    const chartInstances: FakeChart[] = [];

    function createFakeChart(dom: unknown): FakeChart {
        let merged: Record<string, unknown> = {};
        let disposed = false;
        const chart: FakeChart = {
            setOptionCalls: [],
            setOption(option) {
                chart.setOptionCalls.push({option});
                merged = {...merged, ...option};
            },
            getOption: () => merged,
            // About two weeks of daily points over 1200 px stay at the daily resolution.
            getWidth: () => 1200,
            getHeight: () => 400,
            getDom: () => dom,
            getZr: () => ({on: () => {}, off: () => {}}),
            on: () => {},
            off: () => {},
            dispatchAction: () => {},
            resize: () => {},
            containPixel: () => false,
            convertFromPixel: () => null,
            isDisposed: () => disposed,
            dispose: () => {
                disposed = true;
            },
        };
        chartInstances.push(chart);
        return chart;
    }

    class LinearGradient {
        readonly stops: unknown[];
        constructor(...stops: unknown[]) {
            this.stops = stops;
        }
    }

    return {chartInstances, echartsModule: {init: (dom: unknown) => createFakeChart(dom), graphic: {LinearGradient}}};
});

vi.mock('echarts', () => echartsModule);

import type {ComponentProps} from 'svelte';
import {cleanup, render, setupI18n, waitFor} from '$test/component';
import type {RenderedSignal} from '$lib/charts/signals';
import type {LineDataPoint} from './LineChart.svelte';

const GENERATED_TS = join(process.cwd(), 'src', 'lib', 'api', 'generated.ts');

type PriceChartComponent = typeof import('./PriceChartFull.svelte').default;
type PriceChartProps = ComponentProps<PriceChartComponent>;
let PriceChartFull: PriceChartComponent;

beforeAll(async () => {
    expect(existsSync(GENERATED_TS), 'src/lib/api/generated.ts is absent: run `./dev.py api sync`.').toBe(true);
    await setupI18n('en');
    PriceChartFull = (await import('./PriceChartFull.svelte')).default;
}, 60_000);

beforeEach(() => {
    chartInstances.length = 0;
    vi.spyOn(Element.prototype, 'getBoundingClientRect').mockReturnValue({x: 0, y: 0, top: 0, left: 0, right: 800, bottom: 400, width: 800, height: 400, toJSON: () => ({})} as DOMRect);
});

afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
});

const MAIN_LABEL = 'Main asset';
const PEER_LABEL = 'Older peer';

/** The main series: five trading days from the 8th. */
const MAIN_DAYS = ['2024-01-08', '2024-01-09', '2024-01-10', '2024-01-11', '2024-01-12'];
const main: LineDataPoint[] = MAIN_DAYS.map((date, index) => ({date, value: 100 + index * 10}));

/** A comparison with a price on each of `days`. */
function peer(days: string[], extendsAxis = true): RenderedSignal {
    return {
        id: 'peer',
        label: PEER_LABEL,
        data: days.map((date, index) => ({date, value: 50 + index})),
        color: '#ff7f0e',
        lineWidth: 1,
        lineType: 'solid',
        markerStart: null,
        markerEnd: null,
        yAxisIndex: 0,
        aggregationProfile: 'last_with_range',
        ...(extendsAxis ? {extendsAxis: true} : {}),
    };
}

/** The comparison's days: three trading days before the main series, then two of its own. */
const OLDER_DAYS = ['2024-01-03', '2024-01-04', '2024-01-05', '2024-01-08', '2024-01-09'];
const LATER_DAYS = ['2024-01-10', '2024-01-11', '2024-01-12'];

function lastDraw(): Record<string, unknown> {
    const calls = chartInstances.at(-1)?.setOptionCalls ?? [];
    return [...calls].reverse().find((call) => Array.isArray(call.option.series))?.option ?? {};
}

function axisDays(): string[] {
    const xAxis = lastDraw().xAxis;
    return ((Array.isArray(xAxis) ? xAxis[0] : xAxis) as {data?: string[]} | undefined)?.data ?? [];
}

/** The values of the series named `name` on the last draw, one per day of the axis. */
function lineOf(name: string): Array<number | null> {
    const series = ((lastDraw().series ?? []) as Array<{name?: string; type?: string; data?: unknown[]}>).find((entry) => entry.name === name && entry.type === 'line');
    if (!series) throw new Error(`no line named ${name} on the last draw`);
    return (series.data ?? []).map((datum) => (typeof datum === 'number' ? datum : null));
}

async function mount(props: Partial<PriceChartProps>) {
    const view = render(PriceChartFull, {props: {data: main, currency: 'EUR', mainSeriesLabel: MAIN_LABEL, colorByBaseline: false, ...props} as PriceChartProps});
    await waitFor(() => expect(axisDays().length).toBeGreaterThan(0), {timeout: 15_000});
    return view;
}

describe('a comparison older than the main series', () => {
    it('starts the axis on the comparison\'s first day, and keeps the main series\' days after it', async () => {
        await mount({overlaySignals: [peer(OLDER_DAYS)]});
        expect(axisDays()).toEqual(['2024-01-03', '2024-01-04', '2024-01-05', ...MAIN_DAYS]);
    });

    it('leaves the main line empty before its own first day: no zero, no invented price', async () => {
        await mount({overlaySignals: [peer(OLDER_DAYS)]});
        expect(lineOf(MAIN_LABEL)).toEqual([null, null, null, 100, 110, 120, 130, 140]);
    });

    it('draws the comparison from its own first day, on the days it has a price for', async () => {
        await mount({overlaySignals: [peer(OLDER_DAYS)]});
        expect(lineOf(PEER_LABEL)).toEqual([50, 51, 52, 53, 54, null, null, null]);
    });

    it('measures the main line from its own first price in the percentage view, 0 % on its first day, still empty before it', async () => {
        await mount({overlaySignals: [peer(OLDER_DAYS)], initialViewMode: 'percentage'});
        expect(lineOf(MAIN_LABEL)).toEqual([null, null, null, 0, 10, 20, 30, 40]);
    });

    it('draws the same axis again when the comparison is taken off: the axis goes back to the main series\' days', async () => {
        const view = await mount({overlaySignals: [peer(OLDER_DAYS)]});
        expect(axisDays().length).toBe(8);
        await view.rerender({overlaySignals: []} as Partial<PriceChartProps>);
        await waitFor(() => expect(axisDays()).toEqual(MAIN_DAYS), {timeout: 15_000});
        expect(lineOf(MAIN_LABEL)).toEqual([100, 110, 120, 130, 140]);
    });
});

describe('a comparison younger than the main series (the other way)', () => {
    it('keeps the main series\' axis and starts the comparison on its own first day', async () => {
        await mount({overlaySignals: [peer(LATER_DAYS)]});
        expect(axisDays()).toEqual(MAIN_DAYS);
        expect(lineOf(PEER_LABEL)).toEqual([null, null, 50, 51, 52]);
        expect(lineOf(MAIN_LABEL)).toEqual([100, 110, 120, 130, 140]);
    });
});

describe('a signal that does not ask for the days', () => {
    it('does not lengthen the axis: an indicator follows the main series\' days', async () => {
        await mount({overlaySignals: [peer(OLDER_DAYS, false)]});
        expect(axisDays()).toEqual(MAIN_DAYS);
    });
});
