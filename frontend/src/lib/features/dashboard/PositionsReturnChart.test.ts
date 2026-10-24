// @vitest-environment jsdom
/**
 * PositionsReturnChart — component test (Vitest + jsdom), Y5-2 (#48).
 *
 * The chart under the Dashboard's holdings table: one line per selected position plus the portfolio
 * line, in the «absolute» (P&L) or «percentage» (base 100) view, with a legend that switches each line
 * on and off and a toggle for the view. The component is controlled: it never decides the view or the
 * hidden set, it calls `onviewchange(view)` / `ontoggle(id)` and draws the props it is given.
 *
 * ## What is replaced, and why
 *
 * - `echarts`: a recorder, not a renderer (jsdom has no canvas). It answers every call a chart makes on
 *   an instance and keeps each `setOption` payload; the assertions read the OPTION the component handed
 *   over, never pixels. As in `AllocationHistoryChart.test.ts` / `GrowthChart.test.ts`.
 * - `getClientRects`: jsdom lays nothing out, and the dashboard charts draw only into a container that has
 *   a client rect. Every element answers with one rect for the duration of the file.
 *
 * ## What is NOT asserted
 *
 * Translated words (the only text compared is the `note` string this file passes in as a prop), pixel
 * geometry, class names. Everything is found by `data-testid` / `data-*` / `aria-pressed`.
 *
 * ## How the option is read
 *
 * Series are identified by `id` (= the line id). A datum may be a bare number, a `[date, value]` pair or
 * `{value}` — `datumValue` reads the value out of any of them. The colour of a series is read from
 * `lineStyle.color`, then `itemStyle.color`, then `color`. The reference line (100 in the percentage view,
 * 0 in the absolute one) is a `markLine` somewhere in the series, found by its value alone.
 */
import {afterAll, afterEach, beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';

const {chartInstances, echartsModule} = vi.hoisted(() => {
    interface SetOptionCall {
        option: Record<string, unknown>;
        opts: unknown;
    }

    interface FakeChart {
        setOptionCalls: SetOptionCall[];
        setOption: (option: Record<string, unknown>, opts?: unknown) => void;
        getOption: () => Record<string, unknown>;
        getDom: () => unknown;
        getWidth: () => number;
        getHeight: () => number;
        on: (event: string, handler: () => void) => void;
        off: (event: string, handler?: () => void) => void;
        dispatchAction: (action: unknown) => void;
        resize: () => void;
        clear: () => void;
        isDisposed: () => boolean;
        dispose: () => void;
    }

    const chartInstances: FakeChart[] = [];

    function createFakeChart(dom: unknown): FakeChart {
        let disposed = false;
        const chart: FakeChart = {
            setOptionCalls: [],
            setOption(option, opts) {
                chart.setOptionCalls.push({option, opts});
            },
            getOption: () => ({}),
            getDom: () => dom,
            getWidth: () => 800,
            getHeight: () => 400,
            on: () => {},
            off: () => {},
            dispatchAction: () => {},
            resize: () => {},
            clear: () => {},
            isDisposed: () => disposed,
            dispose: () => {
                disposed = true;
            },
        };
        chartInstances.push(chart);
        return chart;
    }

    return {
        chartInstances,
        echartsModule: {
            init: (dom: unknown) => createFakeChart(dom),
            format: {
                getTextRect(text: string) {
                    return {x: 0, y: 0, width: text.length * 7, height: 14};
                },
            },
        },
    };
});

vi.mock('echarts', () => echartsModule);

vi.mock('$lib/api', () => ({
    zodiosApi: new Proxy(
        {},
        {
            get() {
                return vi.fn(async () => ({items: []}));
            },
        },
    ),
}));

import {fireEvent, render, screen, setupI18n, waitFor} from '$test/component';
import PositionsReturnChart from './PositionsReturnChart.svelte';
import type {PositionLine, PositionsChartView} from './positionsSeries';

// =============================================================================
// Fixtures
// =============================================================================

const NOTE = 'NOTE-SENTINEL-not-a-translation';

/** Colours the chart must take from `colorOf`: distinct, and unlike anything a theme would pick. */
const COLORS: Record<string, string> = {
    '12-3': 'rgb(11, 22, 33)',
    '7-0': 'rgb(44, 55, 66)',
    '5-1': 'rgb(77, 88, 99)',
    portfolio: 'rgb(101, 102, 103)',
};
const colorOf = (id: string): string => COLORS[id] ?? 'rgb(1, 1, 1)';

function line(id: string, values: Array<number | null>, overrides: Partial<PositionLine> = {}): PositionLine {
    return {
        id,
        label: `Label ${id}`,
        points: values.map((value, i) => ({date: `2026-01-0${i + 1}`, value})),
        closedOn: null,
        complete: true,
        kind: 'position',
        ...overrides,
    };
}

const A = () => line('12-3', [1, 2, 3]);
const B = () => line('7-0', [10, null, 30]);
const PORTFOLIO = () => line('portfolio', [0, 5, 4], {kind: 'portfolio', label: 'Portfolio'});

type Props = {
    lines: PositionLine[];
    view: PositionsChartView;
    onviewchange?: (view: PositionsChartView) => void;
    hiddenIds?: ReadonlySet<string>;
    ontoggle?: (id: string) => void;
    colorOf: (id: string) => string;
    currency: string;
    loading?: boolean;
    failed?: boolean;
    portfolioLabel?: string;
    note?: string;
};

function props(overrides: Partial<Props> = {}): Props {
    return {lines: [PORTFOLIO(), A(), B()], view: 'absolute', colorOf, currency: 'EUR', note: NOTE, ...overrides};
}

// =============================================================================
// Reading what the chart handed ECharts
// =============================================================================

type Json = Record<string, unknown>;

function lastSeries(): Json[] | undefined {
    for (const chart of chartInstances) {
        for (let i = chart.setOptionCalls.length - 1; i >= 0; i--) {
            const series = chart.setOptionCalls[i].option.series;
            if (Array.isArray(series)) return series as Json[];
        }
    }
    return undefined;
}

/** Every drawn line series (the ones whose id is a line id), whatever else the option carries. */
function lineSeries(knownIds: string[]): Json[] {
    return (lastSeries() ?? []).filter((s) => typeof s.id === 'string' && knownIds.includes(s.id as string));
}

function seriesIds(knownIds: string[]): string[] {
    return lineSeries(knownIds)
        .map((s) => s.id as string)
        .sort();
}

function datumValue(datum: unknown): unknown {
    if (Array.isArray(datum)) return datum[datum.length - 1];
    if (datum && typeof datum === 'object' && 'value' in (datum as Json)) return datumValue((datum as Json).value);
    return datum;
}

function dataValues(series: Json): unknown[] {
    return ((series.data as unknown[]) ?? []).map(datumValue);
}

function seriesColor(series: Json): unknown {
    const ls = series.lineStyle as Json | undefined;
    const is = series.itemStyle as Json | undefined;
    return ls?.color ?? is?.color ?? series.color;
}

/** Every number a markLine of any series draws a horizontal line at. */
function markLineLevels(): number[] {
    const levels: number[] = [];
    for (const s of lastSeries() ?? []) {
        const markLine = s.markLine as Json | undefined;
        if (!markLine) continue;
        for (const item of (markLine.data as Json[]) ?? []) {
            if (typeof item.yAxis === 'number') levels.push(item.yAxis);
            else if (typeof item.value === 'number') levels.push(item.value);
        }
    }
    return levels;
}

const root = () => screen.getByTestId('positions-return-chart');

beforeAll(async () => {
    await setupI18n();
});

let restoreLayout: (() => void) | undefined;
beforeAll(() => {
    // jsdom lays nothing out: every element gets the one client rect it would have on screen.
    const spy = vi.spyOn(Element.prototype, 'getClientRects').mockImplementation(() => [{x: 0, y: 0, top: 0, left: 0, width: 800, height: 400, right: 800, bottom: 400}] as unknown as DOMRectList);
    restoreLayout = () => spy.mockRestore();
});

afterAll(() => {
    restoreLayout?.();
});

beforeEach(() => {
    chartInstances.length = 0;
});

afterEach(() => {
    document.documentElement.classList.remove('dark');
});

/** Mounts the chart and waits until it has handed ECharts a series list. */
async function mountReady(overrides: Partial<Props> = {}) {
    const p = props(overrides);
    const view = render(PositionsReturnChart, {props: p});
    await waitFor(() => expect(lastSeries(), 'the chart never handed ECharts a series list').toBeDefined(), {timeout: 5_000});
    return {view, props: p};
}

const ALL_IDS = ['12-3', '7-0', '5-1', 'portfolio'];

// =============================================================================
// Root attributes and states
// =============================================================================

describe('PositionsReturnChart — root attributes and states', () => {
    it('ready: data-state ready, the view and the number of lines drawn', async () => {
        await mountReady();
        expect(root()).toHaveAttribute('data-state', 'ready');
        expect(root()).toHaveAttribute('data-view', 'absolute');
        expect(root()).toHaveAttribute('data-line-count', '3');
    });

    it('data-view follows the view prop', async () => {
        const {view} = await mountReady({view: 'percentage'});
        expect(root()).toHaveAttribute('data-view', 'percentage');
        await view.rerender({...props({view: 'absolute'})});
        await waitFor(() => expect(root()).toHaveAttribute('data-view', 'absolute'));
    });

    it('loading: data-state loading', () => {
        render(PositionsReturnChart, {props: props({loading: true})});
        expect(root()).toHaveAttribute('data-state', 'loading');
    });

    it('failed: data-state failed', () => {
        render(PositionsReturnChart, {props: props({failed: true})});
        expect(root()).toHaveAttribute('data-state', 'failed');
    });

    it('empty: no lines at all', () => {
        render(PositionsReturnChart, {props: props({lines: []})});
        expect(root()).toHaveAttribute('data-state', 'empty');
        expect(root()).toHaveAttribute('data-line-count', '0');
    });

    it('empty: lines that have no point', () => {
        render(PositionsReturnChart, {props: props({lines: [line('12-3', []), line('portfolio', [], {kind: 'portfolio'})]})});
        expect(root()).toHaveAttribute('data-state', 'empty');
        expect(root()).toHaveAttribute('data-line-count', '0');
    });

    it('empty: lines whose points are all null', () => {
        render(PositionsReturnChart, {props: props({lines: [line('12-3', [null, null])]})});
        expect(root()).toHaveAttribute('data-state', 'empty');
        expect(root()).toHaveAttribute('data-line-count', '0');
    });

    it('a line with at least one non-null point counts as drawn; an all-null one does not', async () => {
        await mountReady({lines: [A(), line('7-0', [null, null, null]), line('5-1', [null, 4, null])]});
        expect(root()).toHaveAttribute('data-line-count', '2');
        expect(root()).toHaveAttribute('data-state', 'ready');
    });

    it('a hidden line is not counted', async () => {
        await mountReady({hiddenIds: new Set(['7-0'])});
        expect(root()).toHaveAttribute('data-line-count', '2');
    });

    it('every line hidden: nothing drawn, so empty', async () => {
        render(PositionsReturnChart, {props: props({hiddenIds: new Set(['portfolio', '12-3', '7-0'])})});
        expect(root()).toHaveAttribute('data-line-count', '0');
        expect(root()).toHaveAttribute('data-state', 'empty');
    });
});

// =============================================================================
// View toggle
// =============================================================================

describe('PositionsReturnChart — view toggle', () => {
    it('aria-pressed marks the current view only', () => {
        render(PositionsReturnChart, {props: props({view: 'percentage'})});
        expect(screen.getByTestId('positions-chart-view-percentage')).toHaveAttribute('aria-pressed', 'true');
        expect(screen.getByTestId('positions-chart-view-absolute')).toHaveAttribute('aria-pressed', 'false');
    });

    it('a click calls onviewchange with the clicked view', async () => {
        const onviewchange = vi.fn();
        render(PositionsReturnChart, {props: props({view: 'absolute', onviewchange})});
        await fireEvent.click(screen.getByTestId('positions-chart-view-percentage'));
        expect(onviewchange).toHaveBeenCalledTimes(1);
        expect(onviewchange).toHaveBeenCalledWith('percentage');
    });

    it('the component is controlled: a click alone does not change the pressed view', async () => {
        const onviewchange = vi.fn();
        render(PositionsReturnChart, {props: props({view: 'absolute', onviewchange})});
        await fireEvent.click(screen.getByTestId('positions-chart-view-percentage'));
        expect(screen.getByTestId('positions-chart-view-absolute')).toHaveAttribute('aria-pressed', 'true');
        expect(root()).toHaveAttribute('data-view', 'absolute');
    });

    it('works without a callback', async () => {
        render(PositionsReturnChart, {props: props()});
        await fireEvent.click(screen.getByTestId('positions-chart-view-percentage'));
        expect(root()).toHaveAttribute('data-state', 'ready');
    });
});

// =============================================================================
// Legend
// =============================================================================

describe('PositionsReturnChart — legend', () => {
    it('one legend button per line, hidden or not', async () => {
        render(PositionsReturnChart, {props: props({hiddenIds: new Set(['7-0'])})});
        for (const id of ['portfolio', '12-3', '7-0']) expect(screen.getByTestId(`positions-chart-legend-${id}`)).toBeInTheDocument();
    });

    it('aria-pressed is whether the line is visible', () => {
        render(PositionsReturnChart, {props: props({hiddenIds: new Set(['7-0'])})});
        expect(screen.getByTestId('positions-chart-legend-12-3')).toHaveAttribute('aria-pressed', 'true');
        expect(screen.getByTestId('positions-chart-legend-portfolio')).toHaveAttribute('aria-pressed', 'true');
        expect(screen.getByTestId('positions-chart-legend-7-0')).toHaveAttribute('aria-pressed', 'false');
    });

    it('a click calls ontoggle with the line id', async () => {
        const ontoggle = vi.fn();
        render(PositionsReturnChart, {props: props({ontoggle})});
        await fireEvent.click(screen.getByTestId('positions-chart-legend-12-3'));
        expect(ontoggle).toHaveBeenCalledTimes(1);
        expect(ontoggle).toHaveBeenCalledWith('12-3');
        await fireEvent.click(screen.getByTestId('positions-chart-legend-portfolio'));
        expect(ontoggle).toHaveBeenLastCalledWith('portfolio');
    });

    it('the component is controlled: a click alone does not hide the line', async () => {
        const ontoggle = vi.fn();
        render(PositionsReturnChart, {props: props({ontoggle})});
        await fireEvent.click(screen.getByTestId('positions-chart-legend-12-3'));
        expect(screen.getByTestId('positions-chart-legend-12-3')).toHaveAttribute('aria-pressed', 'true');
    });

    it('the swatch of each line wears colorOf(id)', () => {
        render(PositionsReturnChart, {props: props()});
        for (const id of ['portfolio', '12-3', '7-0']) {
            const swatch = screen.getByTestId(`positions-chart-swatch-${id}`);
            expect(swatch.getAttribute('style') ?? '', `swatch of ${id}`).toContain(colorOf(id));
        }
    });

    it('the swatch is a child of its legend button', () => {
        render(PositionsReturnChart, {props: props()});
        expect(screen.getByTestId('positions-chart-legend-12-3')).toContainElement(screen.getByTestId('positions-chart-swatch-12-3'));
    });

    it('the portfolio line’s entry is marked data-kind=portfolio; a position’s is not', () => {
        render(PositionsReturnChart, {props: props()});
        expect(screen.getByTestId('positions-chart-legend-portfolio')).toHaveAttribute('data-kind', 'portfolio');
        expect(screen.getByTestId('positions-chart-legend-12-3').getAttribute('data-kind')).not.toBe('portfolio');
    });

    it('the note is shown with the portfolio line (the text it was given)', () => {
        render(PositionsReturnChart, {props: props()});
        expect(screen.getByTestId('positions-chart-note')).toHaveTextContent(NOTE);
    });

    it('a line with closedOn is marked data-closed=true; an open one is not', () => {
        render(PositionsReturnChart, {props: props({lines: [PORTFOLIO(), A(), line('7-0', [10, 20], {closedOn: '2026-01-02'})]})});
        expect(screen.getByTestId('positions-chart-legend-7-0')).toHaveAttribute('data-closed', 'true');
        expect(screen.getByTestId('positions-chart-legend-12-3').getAttribute('data-closed')).not.toBe('true');
        expect(screen.getByTestId('positions-chart-legend-portfolio').getAttribute('data-closed')).not.toBe('true');
    });
});

// =============================================================================
// The option handed to ECharts
// =============================================================================

describe('PositionsReturnChart — the option', () => {
    it('one series per drawn line, with the line id as series id', async () => {
        await mountReady();
        expect(seriesIds(ALL_IDS)).toEqual(['12-3', '7-0', 'portfolio']);
    });

    it('every series carries the values of its line, in order', async () => {
        await mountReady();
        const byId = new Map(lineSeries(ALL_IDS).map((s) => [s.id as string, s]));
        expect(dataValues(byId.get('12-3')!)).toEqual([1, 2, 3]);
        expect(dataValues(byId.get('portfolio')!)).toEqual([0, 5, 4]);
    });

    it('a null point stays null in the data, so the line breaks (never 0)', async () => {
        await mountReady();
        const values = dataValues(lineSeries(ALL_IDS).find((s) => s.id === '7-0')!);
        expect(values.filter((v) => v !== null && v !== undefined)).toEqual([10, 30]);
        expect(values.some((v) => v === null)).toBe(true);
        expect(values).not.toContain(0);
    });

    it('a hidden line is not in the option', async () => {
        await mountReady({hiddenIds: new Set(['7-0'])});
        expect(seriesIds(ALL_IDS)).toEqual(['12-3', 'portfolio']);
    });

    it('a line with no point at all is not a series', async () => {
        await mountReady({lines: [A(), line('7-0', [])]});
        expect(seriesIds(ALL_IDS)).toEqual(['12-3']);
    });

    it('the colours come from colorOf', async () => {
        await mountReady();
        for (const s of lineSeries(ALL_IDS)) expect(seriesColor(s), `colour of ${s.id}`).toBe(colorOf(s.id as string));
    });

    it('the absolute view draws its reference at 0', async () => {
        await mountReady({view: 'absolute'});
        expect(markLineLevels()).toContain(0);
        expect(markLineLevels()).not.toContain(100);
    });

    it('the percentage view draws its reference at 100', async () => {
        await mountReady({view: 'percentage', lines: [line('12-3', [100, 105, 112]), line('portfolio', [100, 101, 99], {kind: 'portfolio'})]});
        expect(markLineLevels()).toContain(100);
        expect(markLineLevels()).not.toContain(0);
    });

    it('hiding a line redraws without it; showing it brings it back', async () => {
        const {view} = await mountReady();
        expect(seriesIds(ALL_IDS)).toContain('7-0');

        await view.rerender({...props({hiddenIds: new Set(['7-0'])})});
        await waitFor(() => expect(seriesIds(ALL_IDS)).toEqual(['12-3', 'portfolio']));

        await view.rerender({...props({hiddenIds: new Set<string>()})});
        await waitFor(() => expect(seriesIds(ALL_IDS)).toEqual(['12-3', '7-0', 'portfolio']));
    });

    it('a new set of lines redraws: a line that joins is drawn, one that leaves is gone', async () => {
        const {view} = await mountReady({lines: [PORTFOLIO(), A()]});
        expect(seriesIds(ALL_IDS)).toEqual(['12-3', 'portfolio']);

        await view.rerender({...props({lines: [PORTFOLIO(), line('5-1', [3, 2, 1])]})});
        await waitFor(() => expect(seriesIds(ALL_IDS)).toEqual(['5-1', 'portfolio']));
        expect(root()).toHaveAttribute('data-line-count', '2');
    });

    it('a view change redraws with the new lines’ values', async () => {
        const {view} = await mountReady({view: 'absolute', lines: [line('12-3', [1, 2, 3])]});
        expect(dataValues(lineSeries(ALL_IDS)[0])).toEqual([1, 2, 3]);

        await view.rerender({...props({view: 'percentage', lines: [line('12-3', [101, 102, 103])]})});
        await waitFor(() => expect(dataValues(lineSeries(ALL_IDS)[0])).toEqual([101, 102, 103]));
        expect(markLineLevels()).toContain(100);
    });
});
