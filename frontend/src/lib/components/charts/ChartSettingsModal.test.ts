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
 * for. Both chart modules the preview may mount are replaced by the same recorder: `LineChart.svelte` today,
 * `PriceChartFull.svelte` once Y-39b moves the preview onto the detail page's chart, so the cases survive the swap. The
 * stand-in keeps the props object the modal hands the chart — its getters read the modal's state at the time of the read
 * — and marks its place with `data-testid="chart-settings-preview-chart"`, so the preview is found by test id inside the
 * open modal. The cases read the `overlaySignals` and the `data` it receives: never a pixel, never a translated text —
 * «Synthetic peer» is a name the case injects.
 *
 * The cases do not choose the preview's view: its toggle is the modal's own today, and Y-39b hands it to the new chart.
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
import {render, screen, setupI18n, within} from '$test/component';
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
}

/** The modal, open, on settings holding `signals` — as a list page opens it for a card (pair) or for the filter bar (global). */
async function openModal({mode, signals, pairData, signalSources}: OpenOptions): Promise<void> {
    const settings: ChartSettings = {...(JSON.parse(JSON.stringify(DEFAULT_CHART_SETTINGS)) as ChartSettings), signals: JSON.parse(JSON.stringify(signals)) as SignalConfig[]};
    const props: ComponentProps<typeof ChartSettingsModal> = {open: true, settings, mode};
    if (pairData) props.pairData = pairData;
    if (signalSources) props.signalSources = signalSources;
    render(ChartSettingsModal, props);
    await tick();
}

/** What the one chart of the open modal's preview receives: the overlay signals, and the data it draws them over. */
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
