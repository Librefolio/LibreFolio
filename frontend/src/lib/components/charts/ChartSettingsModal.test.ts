// @vitest-environment jsdom
/**
 * ChartSettingsModal — the preview draws a chart's saved local signals through the sources its page hands it
 * (lot Y-39a, «parity between the card and the preview»).
 *
 * ## The contract
 *
 * A card and its settings preview drew the same saved signals through two copies of one loop, and the copies drifted
 * (`lib/charts/__tests__/chartSignalRendering.test.ts` tells how). Since Y-39a the modal takes an optional prop,
 * `signalSources` — the `SignalDataSources` of `lib/charts/chartSignalRendering.ts`, the very sources the page's cards
 * draw with — and draws each local signal of its preview with
 * `renderLocalSignal(config, <the preview's base data>, <the preview's view mode>, signalSources)`: in pair mode (a
 * card's settings) on `pairData`, in global mode on its synthetic curve. The props `pairsDataMap` and `assetsDataMap`
 * are gone. Without `signalSources`, an FX pair or a comparison draws nothing; every other local signal draws as before.
 * The backend signals keep their paths (saved results in pair mode, the live resolver in global mode): not asserted here.
 *
 * ## The harness
 *
 * The modal runs as in the app — real i18n, real `ModalBase`, real signals section — with its preview chart stood in
 * for. Both chart modules the preview mounted over time are replaced by the same recorder (`LineChart.svelte` before Y-39b, `PriceChartFull.svelte`
 * since), so the Y-39a cases read the same props whichever chart the preview is. The
 * stand-in keeps the props object the modal hands the chart — its getters read the modal's state at the time of the read
 * — and marks its place with `data-testid="chart-settings-preview-chart"`, so the preview is found by test id inside the
 * open modal. The cases read the `overlaySignals` and the `data` it receives: never a pixel, never a translated text —
 * «Synthetic peer» is a name the case injects.
 *
 * The cases do not choose the preview's view: its toggle is the modal's own, and the modal hands it to the chart (`externalViewMode`).
 * A comparison's or a pair's values are accepted in either view — the levels in the absolute one, their change from the
 * first in the percentage one — and the straight rates are told from their reciprocals in both.
 *
 * The asset picker of a comparison row loads the asset list on mount: here it is answered at once, empty, so no case
 * makes a request.
 *
 * ## Cases and guards
 *
 * The cases pin where the preview gets a comparison and an FX pair: from `signalSources`, each on its own assertion. The
 * GUARDs pin what holds with and without them: a benchmark needing no outside data is drawn in both modes, with
 * `signalSources` and without; without it, an FX pair and a comparison draw nothing.
 *
 * Registered in `front_component_unit` (`scripts/test_runner/_frontend_utility.py`, action `component-unit`),
 * beside `ChartSignalsSection.test.ts`.
 */
import {beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';

/**
 * Every chart the modal mounts, with the props it was handed. Hoisted because `vi.mock` factories run before the
 * imports; the stand-in has the calling convention of a compiled Svelte 5 component — `(anchor, props)`, content
 * inserted before the anchor — which is all the modal's compiled output asks of it. Its element goes away with the
 * preview, when Svelte unmounts it.
 */
const charts = vi.hoisted(() => {
    type ChartModule = 'LineChart' | 'PriceChartFull';
    interface Mount {
        module: ChartModule;
        element: HTMLElement;
        live: Record<string, unknown>;
    }
    const mounts: Mount[] = [];
    const standIn = (module: ChartModule) =>
        function ChartStandIn(anchor: ChildNode, props: Record<string, unknown>): void {
            const element = document.createElement('div');
            element.setAttribute('data-testid', 'chart-settings-preview-chart');
            element.setAttribute('data-chart-module', module);
            anchor.before(element);
            mounts.push({module, element, live: props});
        };
    return {mounts, LineChartStandIn: standIn('LineChart'), PriceChartFullStandIn: standIn('PriceChartFull')};
});

vi.mock('$lib/components/charts/LineChart.svelte', () => ({default: charts.LineChartStandIn}));
vi.mock('$lib/components/charts/PriceChartFull.svelte', () => ({default: charts.PriceChartFullStandIn}));

// The comparison row's asset picker loads the asset list on mount: answered at once, from the empty cache.
vi.mock('$lib/stores/reference/assetStore', async (importOriginal) => ({
    ...(await importOriginal<typeof import('$lib/stores/reference/assetStore')>()),
    ensureAssetsLoaded: vi.fn(async () => undefined),
}));

import {tick, type ComponentProps} from 'svelte';
import {fireEvent, render, screen, setupI18n, within} from '$test/component';
import type {SignalDataSources} from '$lib/charts/chartSignalRendering';
import type {RenderedSignal, SignalConfig, SignalStyle} from '$lib/charts/signals';
import type {LineDataPoint} from '$lib/components/charts/LineChart.svelte';
import {DEFAULT_CHART_SETTINGS, type ChartSettings} from '$lib/stores/chartSettingsStore.svelte';
import ChartSettingsModal from './ChartSettingsModal.svelte';

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

const STYLE: SignalStyle = {color: '#3b82f6', lineWidth: 2, lineType: 'solid', markerStart: null, markerEnd: null};

/** The card's own chart data, as a page hands it in pair mode: four days, absolute. */
const PAIR_DATA: LineDataPoint[] = [
    {date: '2026-03-02', value: 100},
    {date: '2026-03-03', value: 104},
    {date: '2026-03-04', value: 102},
    {date: '2026-03-05', value: 106},
];
const PAIR_DATES = PAIR_DATA.map((point) => point.date);

/** EUR-GBP as the FX store holds it, straight: a day before the card's, and no rate on 03-05. */
const EUR_GBP: LineDataPoint[] = [
    {date: '2026-02-27', value: 0.4},
    {date: '2026-03-02', value: 0.5},
    {date: '2026-03-03', value: 0.8},
    {date: '2026-03-04', value: 0.625},
];

/** Asset 42, the comparison's target: a day before the card's and one after them, and no price on 03-04. */
const PEER_NAME = 'Synthetic peer';
const PEER: LineDataPoint[] = [
    {date: '2026-02-27', value: 190},
    {date: '2026-03-02', value: 200},
    {date: '2026-03-03', value: 220},
    {date: '2026-03-05', value: 180},
    {date: '2026-03-06', value: 240},
];

/** A benchmark needing no outside data. */
const LINEAR: SignalConfig = {id: 'lin-1', signalType: 'linear', params: {annualRate: 2, offset: 0}, style: STYLE};
/** A comparison with asset 42, its id saved as the asset picker saves it: a number. */
const COMPARISON_42: SignalConfig = {id: 'cmp-42', signalType: 'asset-comparison', params: {assetId: 42}, style: {...STYLE, color: '#f59e0b'}};
const FX_PAIR_ID = 'fx-eur-gbp';

/** The FX pair EUR-GBP, as saved: with the signal's own `_inverted` when the user turned it. */
function fxPair(inverted: boolean): SignalConfig {
    return {id: FX_PAIR_ID, signalType: 'fx-pair', params: inverted ? {pairSlug: 'EUR-GBP', _inverted: true} : {pairSlug: 'EUR-GBP'}, style: {...STYLE, color: '#10b981'}};
}

/** Sources that know the pair EUR-GBP and the asset 42, and nothing else — each a spy. */
function signalSources() {
    return {
        fxPairData: vi.fn((pairSlug: string): LineDataPoint[] | null => (pairSlug === 'EUR-GBP' ? EUR_GBP : null)),
        comparisonTarget: vi.fn((assetId: number) => (assetId === 42 ? {data: PEER, displayName: PEER_NAME} : null)),
    } satisfies SignalDataSources;
}

/** To 9 decimals, -0 read as 0: what the cases compare, so that a float's last bit never decides. */
const round = (value: number): number => Number(value.toFixed(9)) + 0;
const datesOf = (signal: RenderedSignal | undefined): string[] => (signal?.data ?? []).map((point) => point.date);
const valuesOf = (signal: RenderedSignal | undefined): number[] => (signal?.data ?? []).map((point) => round(point.value));

/** A line's values in either view the preview may be in: its levels, or their change from the first, in %. */
function inEitherView(levels: readonly number[]): number[][] {
    const first = levels[0];
    return [levels.map(round), levels.map((level) => round(((level - first) / first) * 100))];
}

// ---------------------------------------------------------------------------
// Harness
// ---------------------------------------------------------------------------

interface OpenOptions {
    mode: 'pair' | 'global';
    signals: SignalConfig[];
    pairData?: LineDataPoint[];
    signalSources?: SignalDataSources;
    /** Saved settings other than the defaults: what the preview's aesthetics and scales start from. */
    saved?: Partial<ChartSettings>;
}

/** The modal, open, on settings holding `signals` — as a list page opens it for a card (pair) or for the filter bar (global). */
async function openModal({mode, signals, pairData, signalSources, saved}: OpenOptions): Promise<void> {
    const settings: ChartSettings = {...(JSON.parse(JSON.stringify(DEFAULT_CHART_SETTINGS)) as ChartSettings), ...saved, signals: JSON.parse(JSON.stringify(signals)) as SignalConfig[]};
    const props: ComponentProps<typeof ChartSettingsModal> = {open: true, settings, mode};
    if (pairData) props.pairData = pairData;
    if (signalSources) props.signalSources = signalSources;
    render(ChartSettingsModal, props);
    await tick();
}

/** What the one chart of the open modal's preview receives: the overlay signals, and the data it draws them over. */
function previewMount(): {module: string; live: Record<string, unknown>} {
    const stands = within(screen.getByTestId('chart-settings-modal')).getAllByTestId('chart-settings-preview-chart');
    expect(stands, 'the open modal mounts one preview chart').toHaveLength(1);
    const mount = charts.mounts.find((entry) => entry.element === stands[0]);
    if (!mount) throw new Error('the preview chart was not placed by a chart stand-in');
    return mount;
}

function previewChart(): {overlaySignals: RenderedSignal[]; data: LineDataPoint[]} {
    const stands = within(screen.getByTestId('chart-settings-modal')).getAllByTestId('chart-settings-preview-chart');
    expect(stands, 'the open modal mounts one preview chart').toHaveLength(1);
    const mount = charts.mounts.find((entry) => entry.element === stands[0]);
    if (!mount) throw new Error('the preview chart was not placed by a chart stand-in');
    return {
        overlaySignals: (mount.live.overlaySignals as RenderedSignal[] | undefined) ?? [],
        data: (mount.live.data as LineDataPoint[] | undefined) ?? [],
    };
}

beforeAll(async () => {
    await setupI18n();
});

beforeEach(() => {
    charts.mounts.length = 0;
});

// ---------------------------------------------------------------------------
// Cases
// ---------------------------------------------------------------------------

describe('ChartSettingsModal preview — saved local signals drawn through signalSources (Y-39a)', () => {
    it('a saved comparison with asset 42 is drawn from signalSources.comparisonTarget(42) — named after its target, on the days of pairData', async () => {
        const sources = signalSources();
        await openModal({mode: 'pair', signals: [LINEAR, COMPARISON_42], pairData: PAIR_DATA, signalSources: sources});

        const {overlaySignals} = previewChart();
        expect(
            overlaySignals.map((signal) => signal.id),
            'control: the preview draws the benchmark beside the comparison',
        ).toContain(LINEAR.id);

        const comparison = overlaySignals.find((signal) => signal.id === COMPARISON_42.id);
        expect(comparison, 'the preview draws no comparison with asset 42: it does not draw through signalSources.comparisonTarget').toBeDefined();
        expect(sources.comparisonTarget).toHaveBeenCalledWith(42);
        expect(comparison?.label, 'the comparison is not named after its target').toBe(PEER_NAME);
        expect(datesOf(comparison), 'the comparison is not drawn on the days of pairData').toEqual(['2026-03-02', '2026-03-03', '2026-03-05']);
        expect(inEitherView([200, 220, 180]), 'the comparison does not carry the prices of its target').toContainEqual(valuesOf(comparison));
    });

    it.each([
        {label: 'its straight rates', inverted: false, levels: [0.5, 0.8, 0.625]},
        {label: 'with the signal’s _inverted: true, their reciprocals', inverted: true, levels: [2, 1.25, 1.6]},
    ])('a saved FX pair EUR-GBP is drawn from signalSources.fxPairData — $label', async ({inverted, levels}) => {
        const sources = signalSources();
        await openModal({mode: 'pair', signals: [LINEAR, fxPair(inverted)], pairData: PAIR_DATA, signalSources: sources});

        const {overlaySignals} = previewChart();
        expect(
            overlaySignals.map((signal) => signal.id),
            'control: the preview draws the benchmark beside the pair',
        ).toContain(LINEAR.id);

        const pair = overlaySignals.find((signal) => signal.id === FX_PAIR_ID);
        expect(pair, 'the preview draws no EUR-GBP: it does not draw through signalSources.fxPairData').toBeDefined();
        expect(sources.fxPairData).toHaveBeenCalledWith('EUR-GBP');
        expect(datesOf(pair), 'the pair is not drawn on the days of pairData').toEqual(['2026-03-02', '2026-03-03', '2026-03-04']);
        expect(inEitherView(levels), inverted ? 'the inverted pair does not carry the reciprocals of the straight rates' : 'the pair does not carry the straight rates its source gives').toContainEqual(valuesOf(pair));
    });

    it.each([
        {mode: 'pair', withSources: false},
        {mode: 'pair', withSources: true},
        {mode: 'global', withSources: false},
        {mode: 'global', withSources: true},
    ] as const)('GUARD: in $mode mode (signalSources given: $withSources), a benchmark needing no outside data is drawn on the days the preview chart draws', async ({mode, withSources}) => {
        await openModal({mode, signals: [LINEAR], pairData: mode === 'pair' ? PAIR_DATA : undefined, signalSources: withSources ? signalSources() : undefined});

        const {overlaySignals, data} = previewChart();
        const benchmark = overlaySignals.find((signal) => signal.id === LINEAR.id);
        expect(benchmark, 'the preview does not draw the linear benchmark').toBeDefined();
        expect(datesOf(benchmark), 'the benchmark is not drawn on the days of the preview chart').toEqual(data.map((point) => point.date));
        if (mode === 'pair') {
            expect(
                data.map((point) => point.date),
                'a card’s settings preview the card’s own days',
            ).toEqual(PAIR_DATES);
        } else {
            expect(data.length, 'control: the global preview draws its synthetic curve').toBeGreaterThan(PAIR_DATA.length);
        }
    });

    it('GUARD: without signalSources, a saved FX pair and a comparison draw nothing — the benchmark beside them still does', async () => {
        await openModal({mode: 'pair', signals: [COMPARISON_42, LINEAR, fxPair(false)], pairData: PAIR_DATA});

        expect(previewChart().overlaySignals.map((signal) => signal.id)).toEqual([LINEAR.id]);
    });
});

// ---------------------------------------------------------------------------
// Y-39b (F-1) — the preview is the detail page's chart
// ---------------------------------------------------------------------------

/**
 * Y-39b (F-1) — the preview draws on `PriceChartFull`, the chart of the detail pages, as they draw it.
 *
 * What it protects: the preview of the settings used to be a `LineChart` of its own, 140 px tall, which drew the signals,
 * the aesthetics and the axis scales its own way; a signal looked one way in the preview and another on the page it was
 * for. The contract, after the cure: the preview mounts `PriceChartFull` with
 *
 * - the ABSOLUTE data (`pairData`, or the synthetic curve) and `externalViewMode` = the preview's own Abs/% toggle —
 *   `PriceChartFull` takes the percentage itself, as on the detail pages; the modal's toggle stays, and the chart's
 *   toolbar and the floating controls it carries over the plot are hidden (`hideToolbar`, `hideViewModeToggle`);
 * - only the line (`externalChartType: 'line'`, `disableCandlestick`: no OHLC in a list), no events, no measure and no edit, and about 220 px of
 *   height (`chartHeight`); the wheel zoom is the chart's own;
 * - the aesthetics and the scales of the settings in editing: `colorByBaseline`, `areaFill`, `showGridLines`,
 *   `showGradient`, the primary axis of the previewed view (`yAxisMode`/`yAxisMin`/`yAxisMax`) and
 *   `secondaryAxisScales`.
 *
 * How it is tested: as the cases above, over the recorder that stands in for the chart modules: which module was
 * mounted, with which props — never a pixel. The toggle is found by its test id.
 */
describe('ChartSettingsModal preview — the detail page’s chart (Y-39b, F-1)', () => {
    const viewToggle = (view: 'absolute' | 'percentage') => screen.getByTestId(`chart-settings-preview-view-${view}`);

    it('mounts PriceChartFull, in place of LineChart', async () => {
        await openModal({mode: 'pair', signals: [], pairData: PAIR_DATA});

        expect(previewMount().module).toBe('PriceChartFull');
    });

    it.each(['absolute', 'percentage'] as const)('hands the chart the absolute data and the %s view, which the modal’s toggle chooses', async (view) => {
        await openModal({mode: 'pair', signals: [], pairData: PAIR_DATA});

        await fireEvent.click(viewToggle(view));
        await tick();

        const {live} = previewMount();
        expect(live.externalViewMode, 'the chart is not told the preview’s view').toBe(view);
        expect(live.data, 'the chart is not handed the absolute data: the percentage is the chart’s to take').toEqual(PAIR_DATA);
    });

    it('draws the line only, with no toolbar, no events, no measure and no edit, in about 220 px', async () => {
        await openModal({mode: 'pair', signals: [], pairData: PAIR_DATA});

        const {live} = previewMount();
        expect({
            hideToolbar: live.hideToolbar,
            disableCandlestick: live.disableCandlestick,
            hideViewModeToggle: live.hideViewModeToggle,
            externalChartType: live.externalChartType,
            editMode: live.editMode ?? false,
            measureMode: live.measureMode ?? false,
            eventMarkers: live.eventMarkers ?? [],
            chartHeight: live.chartHeight,
        }).toEqual({hideToolbar: true, disableCandlestick: true, hideViewModeToggle: true, externalChartType: 'line', editMode: false, measureMode: false, eventMarkers: [], chartHeight: '220px'});
    });

    it('hands the chart the aesthetics and the scales of the settings in editing — the percentage view’s scale in the percentage view', async () => {
        const saved: Partial<ChartSettings> = {
            colorByBaseline: false,
            areaFill: false,
            gridLines: false,
            staleGradient: false,
            axisScales: {absolute: {mode: 'custom', min: 90, max: 110}, percentage: {mode: 'include0'}, secondary: {rsi: {mode: 'custom', min: 0, max: 100}}},
        };
        await openModal({mode: 'pair', signals: [], pairData: PAIR_DATA, saved});

        await fireEvent.click(viewToggle('absolute'));
        await tick();
        const absolute = previewMount().live;
        expect(
            {
                colorByBaseline: absolute.colorByBaseline,
                areaFill: absolute.areaFill,
                showGridLines: absolute.showGridLines,
                showGradient: absolute.showGradient,
                yAxisMode: absolute.yAxisMode,
                yAxisMin: absolute.yAxisMin,
                yAxisMax: absolute.yAxisMax,
                secondaryAxisScales: absolute.secondaryAxisScales,
            },
            'the absolute view',
        ).toEqual({colorByBaseline: false, areaFill: false, showGridLines: false, showGradient: false, yAxisMode: 'custom', yAxisMin: 90, yAxisMax: 110, secondaryAxisScales: saved.axisScales?.secondary});

        await fireEvent.click(viewToggle('percentage'));
        await tick();
        expect(previewMount().live.yAxisMode, 'the percentage view').toBe('include0');
    });
});

// ---------------------------------------------------------------------------
// Y-40 — the three views in the settings, and the rolling-return preview
// ---------------------------------------------------------------------------

/**
 * Y-40 — the preview's view is the saved view of the chart (V-3 a: the list's top bar and its global settings are one value;
 * a card's settings hold the card's), with a third one, the rolling return.
 *
 * The contract, after the cure:
 * - The selector has three views — `chart-settings-preview-view-{absolute,percentage,calendar-return}` — and opens on the
 *   settings' `primaryView`. Apply saves the view it shows (`onsave(…{primaryView})`).
 * - In the rolling-return view the modal asks its page for the return (`calendarPreviewResolver(windowDays, signals,
 *   points)`) and draws what it answers on `PriceChartFull` as the detail draws it: the return as the data, already in
 *   percent (`valueUnit: 'percentage'`, `externalViewMode: 'absolute'`), the comparisons' returns as the overlays, the
 *   percentage axis' scale. In global mode the points are the synthetic curve lengthened by the window, so the year shown
 *   has a return from its first day.
 * - The window is chosen there (`asset-calendar-window-<preset>`, the detail's controls): while the settings' window is
 *   automatic, the one in force is the largest preset that fits the period on screen (`calendarRangeDays`); a preset chosen
 *   is asked at once and saved as chosen (`calendarReturnWindowAuto: false`).
 * - The third view is offered where the page computes the rolling return (`calendarPreviewResolver`): the asset settings,
 *   and the FX ones since the FX half of Y-40; without it, a saved rolling return opens in percent.
 *
 * Red today: two views, no resolver, no window.
 */
describe('ChartSettingsModal — the three views, and the rolling-return preview (Y-40)', () => {
    const RETURNS: LineDataPoint[] = [
        {date: '2026-03-03', value: 4},
        {date: '2026-03-04', value: -2},
    ];
    const PEER_RETURN = {id: 'cmp-42:calendar-return', label: PEER_NAME, data: [{date: '2026-03-04', value: 1}], color: '#f59e0b', lineWidth: 2, lineType: 'solid', markerStart: null, markerEnd: null, yAxisIndex: 0} as RenderedSignal;
    const viewButton = (view: string) => screen.getByTestId(`chart-settings-preview-view-${view}`);
    const flush = async () => {
        for (let turn = 0; turn < 5; turn++) await tick();
        await new Promise((resolve) => setTimeout(resolve, 0));
        await tick();
    };

    async function open(extra: Record<string, unknown>, saved: Partial<ChartSettings> = {}) {
        const settings: ChartSettings = {...(JSON.parse(JSON.stringify(DEFAULT_CHART_SETTINGS)) as ChartSettings), ...saved};
        const onsave = vi.fn();
        const calendarPreviewResolver = vi.fn(async () => ({points: RETURNS, overlays: [PEER_RETURN]}));
        render(ChartSettingsModal, {open: true, settings, mode: 'pair', pairData: PAIR_DATA, onsave, calendarPreviewResolver, ...extra} as unknown as ComponentProps<typeof ChartSettingsModal>);
        await tick();
        return {onsave, calendarPreviewResolver};
    }

    it('opens the selector on the saved view, and Apply saves the view it shows', async () => {
        const {onsave} = await open({}, {primaryView: 'absolute'} as Partial<ChartSettings>);
        expect(viewButton('absolute')).toHaveAttribute('aria-pressed', 'true');
        expect(previewMount().live.externalViewMode).toBe('absolute');

        await fireEvent.click(viewButton('calendar-return'));
        await fireEvent.click(screen.getByTestId('chart-settings-apply'));

        expect(onsave).toHaveBeenCalledWith(expect.objectContaining({primaryView: 'calendar-return'}));
    });

    it('in the rolling-return view, asks the page for the return over the window in force and draws it as the detail does', async () => {
        const {calendarPreviewResolver} = await open({calendarRangeDays: 120}, {primaryView: 'calendar-return'} as Partial<ChartSettings>);
        await flush();

        expect(calendarPreviewResolver, 'automatic window: 120 days on screen take the 3-month preset').toHaveBeenCalledWith(90, expect.any(Array), PAIR_DATA);
        const live = previewMount().live;
        expect({data: live.data, valueUnit: live.valueUnit, externalViewMode: live.externalViewMode, overlaySignals: live.overlaySignals, yAxisMode: live.yAxisMode}).toEqual({
            data: RETURNS,
            valueUnit: 'percentage',
            externalViewMode: 'absolute',
            overlaySignals: [PEER_RETURN],
            yAxisMode: DEFAULT_CHART_SETTINGS.axisScales.percentage.mode,
        });
    });

    it('in global mode, hands the resolver the synthetic curve lengthened by the window', async () => {
        const {calendarPreviewResolver} = await open({mode: 'global', pairData: undefined, calendarRangeDays: 400}, {primaryView: 'calendar-return'} as Partial<ChartSettings>);
        await flush();

        const [windowDays, , points] = calendarPreviewResolver.mock.calls[0] as unknown as [number, unknown, LineDataPoint[]];
        expect(windowDays).toBe(365);
        expect(points.length, 'the synthetic year plus the window before it').toBeGreaterThanOrEqual(365 + 365);
    });

    it('chooses the window there: a preset is asked at once, and saved as chosen', async () => {
        const {calendarPreviewResolver, onsave} = await open({calendarRangeDays: 120}, {primaryView: 'calendar-return'} as Partial<ChartSettings>);
        await flush();

        await fireEvent.click(screen.getByTestId('asset-calendar-window-1y'));
        await flush();
        expect(calendarPreviewResolver).toHaveBeenLastCalledWith(365, expect.any(Array), PAIR_DATA);

        await fireEvent.click(screen.getByTestId('chart-settings-apply'));
        expect(onsave).toHaveBeenCalledWith(expect.objectContaining({calendarReturnWindow: expect.objectContaining({kind: 'preset', preset: '1y'}), calendarReturnWindowAuto: false}));
    });

    it('offers the rolling return to the FX settings too, once their page computes it (Y-40, FX)', async () => {
        await open({axisDomain: 'fx'}, {primaryView: 'calendar-return'} as Partial<ChartSettings>);

        expect(viewButton('calendar-return'), 'the FX settings open on their saved rolling return').toHaveAttribute('aria-pressed', 'true');
    });

    it('guard: settings whose page computes no rolling return offer none, and open a saved one in percent', async () => {
        await open({axisDomain: 'fx', calendarPreviewResolver: undefined}, {primaryView: 'calendar-return'} as Partial<ChartSettings>);

        expect(screen.queryByTestId('chart-settings-preview-view-calendar-return')).toBeNull();
        expect(viewButton('percentage')).toHaveAttribute('aria-pressed', 'true');
    });
});

/**
 * Y-41 — the preview publishes how many overlay lines it draws (`chart-settings-preview`, `data-overlay-count`): a saved
 * comparison drawn in a card's settings, from the page's sources, counts; one the page cannot draw does not.
 *
 * Red today: the preview publishes no count.
 */
describe('ChartSettingsModal preview — the overlay lines it draws (Y-41)', () => {
    it('counts the benchmark and the comparison the page’s sources can draw, and not one they cannot', async () => {
        await openModal({mode: 'pair', signals: [LINEAR, COMPARISON_42], pairData: PAIR_DATA, signalSources: signalSources()});
        expect(screen.getByTestId('chart-settings-preview')).toHaveAttribute('data-overlay-count', '2');
    });

    it('counts only the benchmark when the page has no series for the comparison', async () => {
        await openModal({mode: 'pair', signals: [LINEAR, COMPARISON_42], pairData: PAIR_DATA});
        expect(screen.getByTestId('chart-settings-preview')).toHaveAttribute('data-overlay-count', '1');
    });
});

// ---------------------------------------------------------------------------
// Y5-F2 — the signals list follows the rolling-return view
// ---------------------------------------------------------------------------

/**
 * Y5-F2 — while the preview is the rolling return, the signals section lists only the comparison signals that view draws
 * (as the detail page does with `allowedSignalTypes`): for `axisDomain='asset'` the asset comparison, for
 * `axisDomain='fx'` the FX pair. The other saved signals (a technical indicator, a benchmark, and in FX the asset
 * comparison) are hidden from the list but stay saved: Apply keeps every one of them. Back in the percentage or the
 * absolute view, the list shows them all again.
 *
 * Cards are found by `signal-card-<id>` (the section's own test id). `sma` needs the backend: it has no registered local
 * definition here, and its card is drawn all the same, from the saved config.
 *
 * Red today: the list shows every saved signal in every view.
 */
describe('ChartSettingsModal — the signals list in the rolling-return view (Y5-F2)', () => {
    const SMA: SignalConfig = {id: 'y5f2-sma', signalType: 'sma', params: {window: 20}, style: {...STYLE, color: '#ec4899'}};
    const BENCHMARK: SignalConfig = {id: 'y5f2-linear', signalType: 'linear', params: {annualRate: 2, offset: 0}, style: STYLE};
    const COMPARISON: SignalConfig = {id: 'y5f2-asset', signalType: 'asset-comparison', params: {assetId: 42}, style: {...STYLE, color: '#f59e0b'}};
    const PAIR: SignalConfig = {id: 'y5f2-pair', signalType: 'fx-pair', params: {pairSlug: 'EUR-GBP'}, style: {...STYLE, color: '#10b981'}};

    const card = (id: string) => screen.queryByTestId(`signal-card-${id}`);
    const flush = async () => {
        for (let turn = 0; turn < 5; turn++) await tick();
        await new Promise((resolve) => setTimeout(resolve, 0));
        await tick();
    };

    async function open(axisDomain: 'asset' | 'fx', signals: SignalConfig[], primaryView: 'percentage' | 'calendar-return') {
        const settings: ChartSettings = {...(JSON.parse(JSON.stringify(DEFAULT_CHART_SETTINGS)) as ChartSettings), primaryView, signals: JSON.parse(JSON.stringify(signals)) as SignalConfig[]};
        const onsave = vi.fn();
        const calendarPreviewResolver = vi.fn(async () => ({points: [], overlays: []}));
        render(ChartSettingsModal, {open: true, settings, mode: 'pair', pairData: PAIR_DATA, axisDomain, onsave, calendarPreviewResolver, signalSources: signalSources()} as unknown as ComponentProps<typeof ChartSettingsModal>);
        await tick();
        await flush();
        return {onsave};
    }

    it('asset domain: the rolling return hides a technical indicator and a benchmark, and lists the comparison', async () => {
        await open('asset', [SMA, BENCHMARK, COMPARISON], 'calendar-return');

        expect(card(COMPARISON.id), 'the comparison is what the rolling return draws: it is listed').not.toBeNull();
        expect(card(SMA.id), 'the technical indicator is not drawn by the rolling return: it is not listed').toBeNull();
        expect(card(BENCHMARK.id), 'the benchmark is not drawn by the rolling return: it is not listed').toBeNull();
    });

    it('fx domain: the rolling return hides a technical indicator and an asset comparison, and lists the FX pair', async () => {
        await open('fx', [SMA, COMPARISON, PAIR], 'calendar-return');

        expect(card(PAIR.id), 'the FX pair is what the FX rolling return draws: it is listed').not.toBeNull();
        expect(card(SMA.id), 'the technical indicator is not listed').toBeNull();
        expect(card(COMPARISON.id), 'the asset comparison is not listed in FX').toBeNull();
    });

    it.each([
        {axisDomain: 'asset', signals: [SMA, BENCHMARK, COMPARISON], hidden: [SMA.id, BENCHMARK.id], shown: [COMPARISON.id], back: 'percentage'},
        {axisDomain: 'fx', signals: [SMA, COMPARISON, PAIR], hidden: [SMA.id, COMPARISON.id], shown: [PAIR.id], back: 'absolute'},
    ] as const)('$axisDomain domain: switching the preview to $back lists every saved signal again, and back to the rolling return hides them again', async ({axisDomain, signals, hidden, shown, back}) => {
        await open(axisDomain, [...signals], 'calendar-return');
        for (const id of hidden) expect(card(id), `premise: ${id} is hidden in the rolling return`).toBeNull();

        await fireEvent.click(screen.getByTestId(`chart-settings-preview-view-${back}`));
        await flush();
        for (const id of [...shown, ...hidden]) expect(card(id), `${id} is listed again in the ${back} view`).not.toBeNull();

        await fireEvent.click(screen.getByTestId('chart-settings-preview-view-calendar-return'));
        await flush();
        for (const id of hidden) expect(card(id), `${id} is hidden again in the rolling return`).toBeNull();
        for (const id of shown) expect(card(id)).not.toBeNull();
    });

    it('guard: in the percentage view every saved signal is listed from the start', async () => {
        await open('asset', [SMA, BENCHMARK, COMPARISON], 'percentage');

        for (const signal of [SMA, BENCHMARK, COMPARISON]) expect(card(signal.id), `${signal.id} is listed`).not.toBeNull();
    });

    it.each([
        {axisDomain: 'asset', signals: [SMA, BENCHMARK, COMPARISON]},
        {axisDomain: 'fx', signals: [SMA, COMPARISON, PAIR]},
    ] as const)('$axisDomain domain: Apply from the rolling-return view still saves every signal, the hidden ones untouched', async ({axisDomain, signals}) => {
        const {onsave} = await open(axisDomain, [...signals], 'calendar-return');

        await fireEvent.click(screen.getByTestId('chart-settings-apply'));

        expect(onsave).toHaveBeenCalledTimes(1);
        const saved = (onsave.mock.calls[0][0] as ChartSettings).signals;
        expect(
            saved.map((signal) => signal.id),
            'the hidden signals stay saved, in their order',
        ).toEqual(signals.map((signal) => signal.id));
        for (const signal of signals)
            expect(
                saved.find((entry) => entry.id === signal.id),
                `${signal.id} is saved as it was`,
            ).toEqual(signal);
        expect((onsave.mock.calls[0][0] as ChartSettings).primaryView).toBe('calendar-return');
    });
});
