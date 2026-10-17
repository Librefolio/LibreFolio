// @vitest-environment jsdom
/**
 * ScatterChart — the selection seam, read off the real component.
 *
 * The Asset Global lab sets a table beside this scatter, and one selection has to show in
 * both: a row picked in the table lights its dot (`selectedId`), a dot clicked on the
 * chart reports which point it is (`onpointclick`). The Dashboard mounts the same
 * component with neither, and must get today's chart.
 *
 * ## Why a chart component has a spec after all
 *
 * `scatterChartHelpers.ts` explains why no chart `.svelte` here had one: mounting ECharts
 * in jsdom tests the mock rather than the drawing. For the drawing that still holds, and
 * what a selected dot looks like is pinned where it is decided, in
 * `scatterChartHelpers.test.ts`. What the builder cannot see is the wiring this component
 * owns: that `selectedId` reaches the builder and is re-applied when it moves; that the
 * container publishes it as `data-selected-id`, because an E2E cannot read a canvas; and
 * that an ECharts `click` comes back as the point's id. Props in, calls out — component-test
 * territory. The tooltip box is wiring of the same kind (B4): the builder never sees it; the
 * component reads it for the page's theme when it draws, and draws again when the Designer
 * Lab's colours change (C4).
 *
 * ## What is mocked
 *
 * Only `echarts`, replaced by a recorder, as in `GrowthChart.test.ts` and
 * `AllocationPieChart.test.ts`. It keeps every `setOption` payload and every listener
 * handed to `on()`, so a test reads what the component decided to draw and delivers a
 * click the way ECharts does: to the listener the component registered. The component,
 * its runes, the option builder and the chart helpers are the real ones. So are the roles
 * of tokens.css, read as jsdom has them — no stylesheet, so each reads its stand-in —
 * except where one test injects a reader (`setRoleReader`, the seam `roleColors.ts` keeps
 * for tests) to change the card under a drawn chart.
 *
 * ## What is not asserted
 *
 * No translated text: the chart takes its labels as props and these are fixture strings.
 * No pixels. And not HOW the listener is registered — `on('click', fn)` and
 * `on('click', query, fn)` are both recorded — only what a click does.
 */
import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';

type Listener = (params: unknown) => void;

/** One ECharts instance, as the recorder stands it in. */
interface FakeChart {
    /** Every `setOption`, in order: what the component decided to draw. */
    setOptionCalls: {option: Record<string, unknown>; opts: unknown}[];
    /** Live listeners by event name, in registration order. `dispose()` drops them, as ECharts does. */
    listeners: Map<string, Listener[]>;
    setOption(option: Record<string, unknown>, opts?: unknown): void;
    getOption(): Record<string, unknown>;
    on(event: string, queryOrListener: unknown, listener?: unknown): FakeChart;
    off(event: string, listener?: Listener): FakeChart;
    dispatchAction(): void;
    resize(): void;
    getDom(): HTMLElement;
    getWidth(): number;
    getHeight(): number;
    isDisposed(): boolean;
    dispose(): void;
}

/**
 * The ECharts stand-in: a recorder, not a renderer.
 *
 * It answers every call the component and its helpers make on an instance —
 * `attachChartReady` → `on('finished')`, `scheduleFirstRenderStabilityFix` →
 * `isDisposed`/`resize`, the resize watcher → `resize`, teardown → `dispose` — and the rest
 * of the surface a click wiring may reasonably touch (`off`, `dispatchAction`,
 * `getOption`), so a legitimate implementation never goes red here on a missing method.
 */
const {charts, echartsModule} = vi.hoisted(() => {
    const charts: FakeChart[] = [];

    function createFakeChart(dom: HTMLElement): FakeChart {
        let disposed = false;
        let merged: Record<string, unknown> = {};
        const chart: FakeChart = {
            setOptionCalls: [],
            listeners: new Map(),
            setOption(option, opts) {
                chart.setOptionCalls.push({option, opts});
                merged = {...merged, ...option};
            },
            getOption: () => merged,
            // ECharts takes `on(event, handler[, context])` and `on(event, query, handler[, context])`.
            on(event, queryOrListener, listener) {
                const handler = typeof queryOrListener === 'function' ? queryOrListener : listener;
                if (typeof handler !== 'function') throw new Error(`on('${event}') was called without a handler`);
                chart.listeners.set(event, [...(chart.listeners.get(event) ?? []), handler as Listener]);
                return chart;
            },
            off(event, listener) {
                chart.listeners.set(event, listener ? (chart.listeners.get(event) ?? []).filter((entry) => entry !== listener) : []);
                return chart;
            },
            dispatchAction: () => {},
            resize: () => {},
            getDom: () => dom,
            getWidth: () => 800,
            getHeight: () => 420,
            isDisposed: () => disposed,
            dispose: () => {
                disposed = true;
                chart.listeners.clear();
            },
        };
        charts.push(chart);
        return chart;
    }

    return {charts, echartsModule: {init: (dom: HTMLElement) => createFakeChart(dom)}};
});

vi.mock('echarts', () => echartsModule);

import {flushSync, tick, type ComponentProps} from 'svelte';
import {get} from 'svelte/store';
import {locale, waitLocale} from 'svelte-i18n';

import {cleanup, render, screen, waitFor} from '$test/component';
import {reactiveBox} from '$test/runes.svelte';
import {currentLanguage} from '$lib/stores/app/language';
import {setRoleReader} from '$lib/theme/roleColors';
import {notifyChartColorsChange} from '$lib/theme/themeMode';
import {formatPercent} from '$lib/utils/core/formatPercent';
import {CHART_ANIMATION_CONFIG, CHART_SET_OPTION_OPTS} from './echartsAnimationConfig';
import {buildTooltipTheme} from './echartsTooltipHelpers';
import {buildScatterOption, type RiskReturnPoint} from './scatterChartHelpers';
import ScatterChart from './ScatterChart.svelte';

// =============================================================================
// Fixtures
// =============================================================================

const TEST_ID = 'scatter-under-test';
const LABELS = {volatility: 'Volatility (fixture)', return: 'Return (fixture)', capitalMarketLine: 'Line (fixture)'};
const RISK_FREE = 0.02;
/** The light theme's selection colour. jsdom's root carries no `dark` class, and `beforeEach` makes sure of it. */
const SELECTED_LIGHT = '#22c55e';
/** A render here is one `tick()` away: generous for a loaded machine, short enough that a red is quick. */
const WAIT = {timeout: 2_000};

/**
 * Both surfaces in one set: a portfolio, so the Capital Market Line is drawn as on the
 * Dashboard; weighted and weightless assets and the benchmark, as in the lab; and one
 * asset with no volatility, which the builder drops. Display names differ from ids on
 * purpose: a click must report the id.
 */
const POINTS: RiskReturnPoint[] = [
    {id: 'portfolio', name: 'My portfolio', volatility: 0.15, annualReturn: 0.08, weight: 1, role: 'portfolio'},
    {id: 'asset-1', name: 'Asset One', volatility: 0.12, annualReturn: 0.05, weight: 0.25, role: 'asset'},
    {id: 'asset-2', name: 'Asset Two', volatility: 0.3, annualReturn: 0.12, role: 'asset'},
    {id: 'asset-3', name: 'Asset Three', volatility: 0.22, annualReturn: -0.02, role: 'asset'},
    {id: 'benchmark', name: 'World Index', volatility: 0.18, annualReturn: 0.07, role: 'benchmark'},
    {id: 'asset-9', name: 'Asset Nine', volatility: Number.NaN, annualReturn: 0.1, role: 'asset'},
];
const PLACED = 5;
const DROPPED = 1;

/** What the builder draws for POINTS with nothing selected: the Dashboard's chart, and the reference every selection is measured against. */
function unselected() {
    return buildScatterOption({points: POINTS, riskFreeRate: RISK_FREE, dark: false, labels: LABELS});
}

// =============================================================================
// Reading what the component handed to ECharts
// =============================================================================

interface Datum {
    value: [number, number];
    name: string;
    symbolSize: number;
    itemStyle: {color: string; opacity: number};
    role: string;
    id: string;
}

interface DrawnSeries {
    id: string;
    type: string;
    data: unknown[];
}

interface DrawnOption {
    series: DrawnSeries[];
    grid?: unknown;
}

/** Mounts the chart over the fixture. Descriptors, not a spread: a spread would read a getter once and hand the component a frozen value. */
function mount(props: Partial<ComponentProps<typeof ScatterChart>> = {}) {
    const all = Object.defineProperties({points: POINTS, labels: LABELS, riskFreeRate: RISK_FREE, testId: TEST_ID}, Object.getOwnPropertyDescriptors(props)) as ComponentProps<typeof ScatterChart>;
    const utils = render(ScatterChart, all);
    return {...utils, host: screen.getByTestId(TEST_ID)};
}

/** The one ECharts instance of this mount. One mount is one chart: a rebuild would reset `data-chart-renders`, the counter E2E specs wait on. */
function theChart(): FakeChart {
    expect(charts, 'one mount should be one ECharts instance').toHaveLength(1);
    return charts[0];
}

/** Waits for the first `setOption`: the component draws one `tick()` after mounting. */
async function firstDraw(): Promise<FakeChart> {
    await waitFor(() => expect(charts[0]?.setOptionCalls.length ?? 0, 'ScatterChart never called setOption').toBeGreaterThan(0), WAIT);
    return theChart();
}

function lastOption(chart: FakeChart): DrawnOption {
    const call = chart.setOptionCalls.at(-1);
    if (!call) throw new Error('ScatterChart never called setOption');
    return call.option as unknown as DrawnOption;
}

/**
 * The shared tooltip box of a theme, in the keys an ECharts tooltip takes it. Derived from `buildTooltipTheme`, never
 * written out: it is whatever the roles read here — their stand-ins, since jsdom loads no tokens.css, unless a test
 * injects a reader.
 */
function sharedBox(dark: boolean): {backgroundColor: string; borderColor: string; textStyle: {color: string}} {
    const box = buildTooltipTheme(dark);
    expect([box.bg, box.border, box.textColor], `barrier: buildTooltipTheme(${dark}) names three colours — toEqual takes an undefined key for an absent one, so a box of nothing would match a tooltip that names none`).toEqual([
        expect.stringMatching(/\S/),
        expect.stringMatching(/\S/),
        expect.stringMatching(/\S/),
    ]);
    return {backgroundColor: box.bg, borderColor: box.border, textStyle: {color: box.textColor}};
}

/** The colours of the tooltip box in the last `setOption`: what ECharts paints it with. */
function drawnBox(chart: FakeChart): Record<string, unknown> {
    const tooltip = (chart.setOptionCalls.at(-1)?.option.tooltip ?? {}) as Record<string, unknown>;
    return {backgroundColor: tooltip.backgroundColor, borderColor: tooltip.borderColor, textStyle: tooltip.textStyle};
}

/** Where the datum carrying `id` is drawn, and how. Fails unless it is drawn exactly once. */
function locate(series: readonly DrawnSeries[], id: string): {seriesId: string; seriesIndex: number; dataIndex: number; datum: Datum} {
    const hits = series.flatMap((entry, seriesIndex) => (entry.type === 'scatter' ? (entry.data as Datum[]).map((datum, dataIndex) => ({seriesId: entry.id, seriesIndex, dataIndex, datum})) : [])).filter((hit) => hit.datum.id === id);
    expect(hits, `point "${id}" should be drawn exactly once`).toHaveLength(1);
    return hits[0];
}

/** `series` with the datum carrying `id` swapped for `original`: whatever still differs from the unselected series, the selection changed and should not have. */
function withDatum(series: readonly DrawnSeries[], id: string, original: Datum): DrawnSeries[] {
    return series.map((entry) => (entry.type === 'scatter' ? {...entry, data: (entry.data as Datum[]).map((datum) => (datum.id === id ? original : datum))} : entry));
}

function clickListeners(chart: FakeChart): Listener[] {
    return chart.listeners.get('click') ?? [];
}

/** Delivers an event as ECharts does: to every listener registered for it, in order. */
function emit(chart: FakeChart, event: string, params: unknown): void {
    for (const listener of [...(chart.listeners.get(event) ?? [])]) listener.call(chart, params);
}

/** The params ECharts sends for a click on the dot carrying `id`, built from the datum the component actually handed over. */
function clickOn(option: DrawnOption, id: string): Record<string, unknown> {
    const {seriesId, seriesIndex, dataIndex, datum} = locate(option.series, id);
    return {type: 'click', componentType: 'series', componentSubType: 'scatter', seriesType: 'scatter', seriesId, seriesIndex, dataIndex, name: datum.name, value: datum.value, data: datum, color: datum.itemStyle.color};
}

async function clickListenerRegistered(chart: FakeChart): Promise<void> {
    await waitFor(() => expect(clickListeners(chart), 'ScatterChart registered no ECharts click listener').not.toHaveLength(0), WAIT);
}

// =============================================================================

beforeEach(() => {
    charts.length = 0;
    document.documentElement.classList.remove('dark');
});

afterEach(() => {
    cleanup();
});

describe('ScatterChart', () => {
    describe('with neither selectedId nor onpointclick, as the Dashboard mounts it', () => {
        it("hands ECharts exactly today's option, publishes an empty selection, and a click goes nowhere", async () => {
            const {host} = mount();
            const chart = await firstDraw();
            const built = unselected();
            const box = sharedBox(false);
            const call = chart.setOptionCalls.at(-1)!;

            // Today's option, key for key: the builder's grid and series untouched, the
            // percent formatters on both axes, the tooltip in the light theme's shared box
            // (B4: ECharts drew its own, white in both themes), the house animation.
            expect(call.option).toEqual({
                ...CHART_ANIMATION_CONFIG,
                grid: built.option.grid,
                series: built.option.series,
                xAxis: {...built.option.xAxis, axisLabel: {...built.option.xAxis.axisLabel, formatter: expect.any(Function)}},
                yAxis: {...built.option.yAxis, axisLabel: {...built.option.yAxis.axisLabel, formatter: expect.any(Function)}},
                tooltip: {position: expect.any(Function), confine: true, backgroundColor: box.backgroundColor, borderColor: box.borderColor, textStyle: {color: box.textStyle.color}, formatter: expect.any(Function)},
            });
            expect(call.opts).toEqual(CHART_SET_OPTION_OPTS);

            // Today's attributes, plus the new one: present and empty, so a spec can tell
            // "nothing selected" from "attribute missing".
            expect(host).toHaveAttribute('data-point-count', String(PLACED));
            expect(host).toHaveAttribute('data-dropped-count', String(DROPPED));
            expect(host).toHaveAttribute('data-selected-id', '');

            // Every Dashboard dot can be clicked, and nobody listens: whatever listens must
            // shrug. The chart-ready listener is the recorder's own presence barrier — it
            // proves registrations are seen at all.
            expect(chart.listeners.get('finished'), 'the recorder saw no chart-ready listener, so it would see no click listener either').toHaveLength(1);
            expect(() => emit(chart, 'click', clickOn(lastOption(chart), 'asset-3'))).not.toThrow();
        });
    });

    describe('selectedId', () => {
        it.each([
            {what: 'absent', props: {}, published: ''},
            {what: 'null', props: {selectedId: null}, published: ''},
            {what: 'a point id', props: {selectedId: 'asset-2'}, published: 'asset-2'},
        ])('is published on the container when it is $what', async ({props, published}) => {
            const {host} = mount(props);
            await firstDraw();

            expect(host).toHaveAttribute('data-selected-id', published);
        });

        it('reaches the builder: that one point is drawn larger, green and opaque, every other as before', async () => {
            const {host} = mount({selectedId: 'asset-3'});
            const chart = await firstDraw();
            const drawn = lastOption(chart);
            const built = unselected();

            const before = locate(built.option.series, 'asset-3');
            const after = locate(drawn.series, 'asset-3');
            expect(after.datum.itemStyle.color).toBe(SELECTED_LIGHT);
            expect(after.datum.itemStyle.color).not.toBe(before.datum.itemStyle.color);
            expect(after.datum.itemStyle.opacity).toBe(1);
            expect(after.datum.symbolSize).toBeGreaterThan(before.datum.symbolSize);

            // Put the unselected datum back and the series are the Dashboard's again; the
            // grid is the builder's own.
            expect(withDatum(drawn.series, 'asset-3', before.datum)).toEqual(built.option.series);
            expect(drawn.grid).toEqual(built.option.grid);
            expect(host).toHaveAttribute('data-selected-id', 'asset-3');
        });

        /**
         * The selection lives in the caller's `$state` and reaches the chart through a getter,
         * which is what `selectedId={…}` compiles to in a parent: moving it invalidates
         * `selectedId` and nothing else. Not `rerender`: that replaces the whole props object,
         * so every prop read goes stale and the chart redraws whatever the component tracks —
         * this test would stay green for a component that never reacts to the selection.
         */
        it('is re-applied on the same chart as it moves, and leaves no highlight once cleared', async () => {
            const caller = reactiveBox<{selectedId: string | null}>({selectedId: null});
            const {host} = mount({
                get selectedId() {
                    return caller.selectedId;
                },
            });
            const chart = await firstDraw();
            const built = unselected();

            for (const next of ['asset-3', 'asset-1']) {
                const draws = chart.setOptionCalls.length;
                caller.selectedId = next;
                flushSync();
                await waitFor(() => expect(chart.setOptionCalls.length, `no setOption followed selectedId = '${next}'`).toBeGreaterThan(draws), WAIT);

                const drawn = lastOption(chart);
                expect(locate(drawn.series, next).datum.itemStyle.color).toBe(SELECTED_LIGHT);
                // Restoring the new one leaves the unselected drawing: the previous
                // highlight went with the move.
                expect(withDatum(drawn.series, next, locate(built.option.series, next).datum)).toEqual(built.option.series);
                expect(host).toHaveAttribute('data-selected-id', next);
            }

            const draws = chart.setOptionCalls.length;
            caller.selectedId = null;
            flushSync();
            await waitFor(() => expect(chart.setOptionCalls.length, 'no setOption followed clearing the selection').toBeGreaterThan(draws), WAIT);
            expect(lastOption(chart).series).toEqual(built.option.series);
            expect(host).toHaveAttribute('data-selected-id', '');

            expect(theChart()).toBe(chart);
        });
    });

    describe('onpointclick', () => {
        it('receives the id of the point clicked, from params.data.id and not its name, once per click', async () => {
            const onpointclick = vi.fn<(id: string) => void>();
            mount({selectedId: 'asset-1', onpointclick});
            const chart = await firstDraw();
            await clickListenerRegistered(chart);

            // Drawing and highlighting call nobody back.
            expect(onpointclick).not.toHaveBeenCalled();

            emit(chart, 'click', {data: {id: 'asset-3'}});
            expect(onpointclick.mock.calls).toEqual([['asset-3']]);

            // As ECharts really sends it: the datum the component handed over, named "Asset Two".
            emit(chart, 'click', clickOn(lastOption(chart), 'asset-2'));
            expect(onpointclick.mock.calls).toEqual([['asset-3'], ['asset-2']]);
        });

        it.each([
            {what: 'no datum at all', params: {}},
            {what: 'an empty datum', params: {data: {}}},
            {what: 'the capital market line', params: {type: 'click', componentType: 'series', componentSubType: 'line', seriesType: 'line', seriesId: 'capital-market-line', dataIndex: 0, value: [0, RISK_FREE], data: [0, RISK_FREE]}},
        ])('is not called for a click without a string id: $what', async ({params}) => {
            const onpointclick = vi.fn<(id: string) => void>();
            mount({onpointclick});
            const chart = await firstDraw();
            await clickListenerRegistered(chart);

            expect(() => emit(chart, 'click', params)).not.toThrow();
            expect(onpointclick).not.toHaveBeenCalled();

            // Presence barrier: the same listener answers a real point, so the silence
            // above was its decision and not a dead listener.
            emit(chart, 'click', {data: {id: 'asset-2'}});
            expect(onpointclick.mock.calls).toEqual([['asset-2']]);
        });

        it('is called once per click, however many times the option has been re-applied', async () => {
            const onpointclick = vi.fn<(id: string) => void>();
            const {rerender} = mount({onpointclick});
            const chart = await firstDraw();

            // Two fresh payloads, as a re-fetch delivers them: two more renders on the same chart.
            for (const shift of [0.01, 0.02]) {
                const draws = chart.setOptionCalls.length;
                await rerender({points: POINTS.map((point) => ({...point, annualReturn: point.annualReturn + shift}))});
                await waitFor(() => expect(chart.setOptionCalls.length).toBeGreaterThan(draws), WAIT);
            }
            expect(theChart()).toBe(chart);

            await clickListenerRegistered(chart);
            emit(chart, 'click', {data: {id: 'asset-1'}});
            expect(onpointclick.mock.calls).toEqual([['asset-1']]);
        });
    });

    /**
     * The point's tooltip (T11, developer's review of 05/10/2026): the caller's extra line — what the
     * dot weighs, or that it is the benchmark, already translated — sits under the name, because it
     * says what the dot is before where it is. The line is the caller's text, and an asset's name or a
     * benchmark's can carry anything a provider or a user typed, so it is escaped like the name.
     *
     * Read through the formatter the component hands ECharts, called with the very datum it drew, and
     * parsed back into a DOM: what is asserted is what a reader would see, line by line.
     */
    describe('the tooltip', () => {
        /** The tooltip's lines for the dot carrying `id`, as the drawn formatter renders them. */
        async function tooltipLines(points: RiskReturnPoint[], id: string): Promise<{lines: (string | null)[]; box: HTMLElement}> {
            mount({points});
            const chart = await firstDraw();
            const tooltip = chart.setOptionCalls.at(-1)?.option.tooltip as {formatter?: (params: unknown) => string} | undefined;
            expect(typeof tooltip?.formatter, 'ScatterChart handed ECharts no tooltip formatter').toBe('function');
            const box = document.createElement('div');
            box.innerHTML = tooltip!.formatter!({data: locate(lastOption(chart).series, id).datum});
            return {lines: [...box.children].map((line) => line.textContent), box};
        }

        it("puts the caller's line under the name, as text: markup in it is shown, never run", async () => {
            const detail = 'Weighs <b>35%</b> & more <img src=x onerror="window.__lfTooltipHit=1">';
            const {lines, box} = await tooltipLines(
                POINTS.map((point) => (point.id === 'asset-1' ? {...point, detail} : point)),
                'asset-1',
            );

            expect(lines, 'four lines: the name, the caller’s line, then where the dot sits').toHaveLength(4);
            expect(lines[0]).toBe('Asset One');
            expect(lines[1], 'the caller’s line comes right under the name, whole').toBe(detail);
            expect(lines[2]).toContain('Volatility (fixture)');
            expect(lines[3]).toContain('Return (fixture)');
            expect(box.querySelector('b, img'), 'markup in the caller’s line reached the tooltip as markup').toBeNull();
        });

        it('adds no line to a dot whose caller gave none', async () => {
            const {lines} = await tooltipLines(POINTS, 'asset-2');

            // Presence first: the name and both coordinates are there, so the count is about the extra line.
            expect(lines[0]).toBe('Asset Two');
            expect(lines, 'the name and where the dot sits, and nothing else').toHaveLength(3);
        });
    });

    /**
     * The tooltip box, on the roles (B4, DV). ECharts drew its own box, white in both themes, so a dark page showed a
     * white tooltip: the chart now hands it the shared box, `buildTooltipTheme(dark, container)` — the card, the raised
     * border and the primary text, read on its own element when it draws — and draws again when the Designer Lab's
     * colours change without a theme switch (C4), the roles read anew.
     *
     * The expectations come from `buildTooltipTheme` (`sharedBox`), never from hex literals: jsdom loads no tokens.css,
     * so a role reads its stand-in, which `roleColors.test.ts` keeps equal to tokens.css. Where a role must change under
     * a drawn chart, a reader injected with `setRoleReader` answers it, and `afterEach` takes it away.
     */
    describe('the tooltip box, on the roles (B4)', () => {
        afterEach(() => {
            setRoleReader(null);
        });

        it("draws the dark theme's box on a dark page, not the light one", async () => {
            const lightBox = sharedBox(false);
            const darkBox = sharedBox(true);
            // Barrier: the two themes' boxes differ in every colour, so matching the dark one is about the theme.
            expect(darkBox.backgroundColor, 'barrier: both themes have one background, so the check below could not tell them apart').not.toBe(lightBox.backgroundColor);
            expect(darkBox.borderColor, 'barrier: both themes have one border, so the check below could not tell them apart').not.toBe(lightBox.borderColor);
            expect(darkBox.textStyle.color, 'barrier: both themes have one text colour, so the check below could not tell them apart').not.toBe(lightBox.textStyle.color);

            // Before mounting, as the theme store leaves <html>; the file's beforeEach takes the class off again.
            document.documentElement.classList.add('dark');
            mount();
            const chart = await firstDraw();

            await waitFor(() => expect(drawnBox(chart), "the tooltip box of a dark page is not the dark theme's: the theme does not reach it, and a dark page shows a light tooltip").toEqual(darkBox), WAIT);
        });

        it("draws the box again, with the roles read anew, when the Designer Lab's colours change (C4)", async () => {
            const standIn = sharedBox(false).backgroundColor;
            const before = '#0a1b2c';
            const after = '#c2b1a0';
            expect(new Set([standIn, before, after]).size, "barrier: the card's two injected colours differ from each other and from its stand-in, so a background names the read it came from").toBe(3);

            // `#rrggbb`, which chartRoles takes as it is: jsdom has no canvas to resolve another notation. Every other
            // role answers nothing, and reads its stand-in.
            let card = before;
            setRoleReader((role) => (role === '--lf-surface-card' ? card : ''));
            mount();
            const chart = await firstDraw();
            await waitFor(() => expect(drawnBox(chart).backgroundColor, 'barrier: the first draw did not read the card through the roles, so a change of the role could not show').toBe(before), WAIT);

            const draws = chart.setOptionCalls.length;
            card = after;
            notifyChartColorsChange();
            flushSync();
            await waitFor(() => expect(chart.setOptionCalls.length, "no setOption followed the Designer Lab's colour signal: the chart keeps the colours of its last draw until the theme switches").toBeGreaterThan(draws), WAIT);
            await waitFor(() => expect(drawnBox(chart).backgroundColor, 'the chart drew again with the card it read before the signal: the box was not read anew').toBe(after), WAIT);
            expect(theChart(), 'the signal redrew the same chart').toBe(chart);
        });
    });

    /**
     * M-18 CP2: a switch of the UI language redraws the chart.
     *
     * Both axes write their ticks through `axisPercent`, a `formatPercent` whose locale defaults to the
     * interface locale, read when ECharts calls it. But ECharts calls a formatter only while painting,
     * and paints only when it is handed an option: the render effect tracks the built option alone —
     * points, labels, theme, selection — so a language switch hands ECharts nothing, and the axes keep
     * the language they were drawn in. Every figure is written in the interface language (the
     * developer's decision M-18, 2026-10-12), and every effect that calls `setOption` reads `uiLocale()`,
     * so a switch redraws, on the same instance, an option whose axes write French.
     *
     * Read: a new `setOption` after the switch, and the two axis formatters of that option, called as
     * ECharts calls them. Expectations from `formatPercent` with an explicit locale; English is the control.
     *
     * Language. Switched as LanguageSelector does — `currentLanguage.set`, which also drives svelte-i18n —
     * after the mount; the `afterEach` puts English back. The chart takes its labels as props, so no
     * translated text is read.
     */
    describe('redrawn in the interface language (M-18)', () => {
        type AxisFormatter = (value: number) => string;

        /** The tick formatter of one axis of a drawn option. */
        function axisFormatter(option: Record<string, unknown>, axis: 'xAxis' | 'yAxis'): AxisFormatter {
            const formatter = (option[axis] as {axisLabel?: {formatter?: unknown}} | undefined)?.axisLabel?.formatter;
            if (typeof formatter !== 'function') throw new Error(`the option carries no ${axis} label formatter`);
            return formatter as AxisFormatter;
        }

        /** A volatility tick on x and a return tick on y, as each axis writes them. */
        function ticksOf(option: Record<string, unknown>): {volatility: string; annualReturn: string} {
            return {volatility: axisFormatter(option, 'xAxis')(0.1234), annualReturn: axisFormatter(option, 'yAxis')(-0.05)};
        }

        /** Both ticks as an axis must write them in `localeTag`: fractions, as percentages with one decimal and no `+`. */
        function expectedTicks(localeTag: string): {volatility: string; annualReturn: string} {
            const percent = (fraction: number) => formatPercent(fraction, {scale: 100, signed: false, digits: 1, locale: localeTag});
            return {volatility: percent(0.1234), annualReturn: percent(-0.05)};
        }

        /** Change the UI language as LanguageSelector does, then flush. The controls name the layer if the language did not move. */
        async function switchLanguage(lang: 'en' | 'fr'): Promise<void> {
            currentLanguage.set(lang);
            await waitLocale(lang);
            flushSync();
            await tick();
            expect(get(currentLanguage), `control: the app language is ${lang}`).toBe(lang);
            expect(get(locale), `control: the svelte-i18n locale is ${lang}`).toBe(lang);
        }

        afterEach(async () => {
            // The language is module-level state shared by every test of the file.
            await switchLanguage('en');
        });

        it('a switch to French redraws the chart on the same instance, and the option it hands ECharts writes French percentages on both axes', async () => {
            mount();
            const chart = await firstDraw();
            // Control: drawn under the English UI, today's text; and French writes it otherwise.
            expect(ticksOf(chart.setOptionCalls.at(-1)!.option)).toEqual({volatility: '12.3%', annualReturn: '-5.0%'});
            const french = expectedTicks('fr');
            expect(french.volatility, 'French differs from English').not.toBe('12.3%');

            const draws = chart.setOptionCalls.length;
            await switchLanguage('fr');
            await waitFor(() => expect(chart.setOptionCalls.length, 'no setOption followed the switch to French').toBeGreaterThan(draws), WAIT);

            expect(ticksOf(chart.setOptionCalls.at(-1)!.option)).toEqual(french);
            expect(theChart(), 'the switch redrew the same chart').toBe(chart);
        });
    });
});
