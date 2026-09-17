// @vitest-environment jsdom
/**
 * MeasurePanel — component test (Vitest + jsdom).
 *
 * MeasurePanel is the measurement-overlay manager on the FX/asset detail chart:
 * two clicks drop a measure between two dates, the panel keeps the set of
 * measures, and it hands the parent the rendered overlay signals through
 * `onmeasureschange`. The interesting behaviour is *arithmetic and state*, not
 * pixels — which is exactly what a component test can reach without a canvas:
 *   - the 2-click placement flow (`addPoint`), including its 300 ms debounce and
 *     the start/end swap when the second click lands earlier than the first;
 *   - the live preview (`updatePendingEnd`) and mode toggling;
 *   - the whole-range shortcut (`addMeasureFromChartData`);
 *   - the summary table `buildSummaryRows` builds — main row, the ghost
 *     original-currency row under FX conversion, and one row per overlay signal
 *     (ghost vs. currency-suffixed) — reached by expanding a card so the real
 *     DataTable renders the HtmlCells.
 *
 * What it deliberately does NOT assert:
 *   - translated text. The pending banner, the column headers and the empty-state
 *     line all come from the catalogue in four languages; every assertion here is
 *     on a `data-row-id`, on a structural marker, or on a *numeric value the test
 *     itself put into the fixture* (e.g. `+21.00%`), never on a label.
 *   - CSS classes. Sign colouring (`text-emerald-*` / `text-red-*`) is a styling
 *     concern; the contract asserted is the *value* that drives it.
 *   - geometry. jsdom reports zeroes for every rect, and MeasurePanel's only
 *     layout branch (`isNarrow`) is driven by `matchMedia`, which is stubbed to a
 *     fixed answer below — the responsive pixel behaviour is E2E territory.
 *   - what ECharts draws. MeasurePanel never touches a canvas; it emits plain
 *     data objects, and those are what the assertions read.
 */
import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';
import type {ComponentProps} from 'svelte';
import {cleanup, fireEvent, render, setupI18n, waitFor, within} from '$test/component';
import MeasurePanel from './MeasurePanel.svelte';
import type {LineDataPoint} from './LineChart.svelte';
import type {RenderedSignal} from '$lib/charts/signals';

/**
 * `isNarrow` reads `window.matchMedia('(max-width: 639px)')` inside an $effect.
 * jsdom ships no matchMedia, so without this the panel throws on mount. A fixed
 * answer is correct here: the responsive layout is not what this spec tests.
 */
function stubMatchMedia(matches = false): void {
    Object.defineProperty(window, 'matchMedia', {
        writable: true,
        configurable: true,
        value: (query: string) => ({
            matches,
            media: query,
            onchange: null,
            addEventListener: () => {},
            removeEventListener: () => {},
            addListener: () => {},
            removeListener: () => {},
            dispatchEvent: () => false,
        }),
    });
}

/** Clean, round values so every delta the summary table prints is exact. */
const baseData: LineDataPoint[] = [
    {date: '2024-01-01', value: 100},
    {date: '2024-01-11', value: 108},
    {date: '2024-01-21', value: 115},
    {date: '2024-01-31', value: 121},
];

/** Valid chart data whose range cannot satisfy a measure anchored to baseData. */
const incompatibleData: LineDataPoint[] = [
    {date: '2099-01-01', value: 1},
    {date: '2099-12-31', value: 2},
];

/** The exported instance methods MeasurePanel exposes to its parent chart. */
interface PanelApi {
    startMeasureMode(): void;
    stopMeasureMode(): void;
    clearMeasures(): void;
    updatePendingEnd(date: string, value: number): void;
    addPoint(date: string, value: number): void;
    addMeasureFromChartData(): void;
}

type PanelProps = ComponentProps<typeof MeasurePanel>;

function mount(props: Partial<PanelProps> = {}) {
    const onmeasureschange = vi.fn();
    const onmeasuremodechange = vi.fn();
    const utils = render(MeasurePanel, {
        chartData: baseData,
        onmeasureschange,
        onmeasuremodechange,
        ...props,
    } as PanelProps);
    const api = utils.component as unknown as PanelApi;
    return {onmeasureschange, onmeasuremodechange, api, ...utils};
}

/** Last array of rendered signals the parent was handed. */
function lastEmit(fn: ReturnType<typeof vi.fn>): RenderedSignal[] | undefined {
    const calls = fn.mock.calls;
    return calls.length ? (calls[calls.length - 1][0] as RenderedSignal[]) : undefined;
}

/** Find one DataTable row by its stable row identity without relying on DOM position. */
function rowById(container: HTMLElement, id: string): HTMLElement | null {
    return rowsById(container, id).at(0) ?? null;
}

/** Find all DataTable rows with a stable identity (one per completed measure). */
function rowsById(container: HTMLElement, id: string): HTMLElement[] {
    return within(container)
        .queryAllByRole('row')
        .filter((row) => row.getAttribute('data-row-id') === id);
}

/** An overlay signal covering the base date axis, cast past the profile boilerplate. */
function overlaySignal(over: Partial<RenderedSignal> & {label: string}): RenderedSignal {
    return {
        id: over.label,
        data: baseData.map((d) => ({date: d.date, value: d.value * 2})),
        color: '#3366cc',
        lineWidth: 1,
        lineType: 'solid',
        markerStart: null,
        markerEnd: null,
        yAxisIndex: 0,
        aggregationProfile: 'last_with_range',
        ...over,
    } as RenderedSignal;
}

beforeEach(async () => {
    stubMatchMedia(false);
    await setupI18n('en');
});

afterEach(() => {
    vi.restoreAllMocks();
    cleanup();
});

describe('MeasurePanel — measure mode', () => {
    it('startMeasureMode / stopMeasureMode notify the parent', () => {
        const {api, onmeasuremodechange} = mount();
        api.startMeasureMode();
        expect(onmeasuremodechange).toHaveBeenLastCalledWith(true);
        api.stopMeasureMode();
        expect(onmeasuremodechange).toHaveBeenLastCalledWith(false);
    });

    it('stopMeasureMode clears any pending preview by re-emitting', () => {
        const {api, onmeasureschange} = mount();
        api.startMeasureMode();
        vi.spyOn(Date, 'now').mockReturnValue(1000);
        api.addPoint('2024-01-01', 100); // arm a pending start
        api.updatePendingEnd('2024-01-31', 121); // build a live preview → emit
        onmeasureschange.mockClear();
        api.stopMeasureMode();
        // Emitted once more with an empty set (no measures, preview cleared).
        expect(lastEmit(onmeasureschange)).toEqual([]);
    });
});

describe('MeasurePanel — addPoint 2-click placement', () => {
    it('ignores clicks entirely when measure mode is off', () => {
        const {api, onmeasureschange} = mount();
        api.addPoint('2024-01-01', 100);
        api.addPoint('2024-01-31', 121);
        expect(onmeasureschange).not.toHaveBeenCalled();
    });

    it('places a measure on the second click and emits one rendered signal', () => {
        const {api, onmeasureschange, onmeasuremodechange} = mount();
        api.startMeasureMode();
        const now = vi.spyOn(Date, 'now');
        now.mockReturnValue(1000);
        api.addPoint('2024-01-01', 100); // first click → pending, no emit yet
        expect(onmeasureschange).not.toHaveBeenCalled();
        now.mockReturnValue(1400); // >300 ms later → not debounced
        api.addPoint('2024-01-31', 121); // second click → measure created
        const emitted = lastEmit(onmeasureschange);
        expect(emitted).toHaveLength(1);
        expect(emitted![0].id).toBe('measure-0');
        // The rendered line spans the whole fixture range, interpolated per point.
        expect(emitted![0].data.map((d) => d.date)).toEqual(['2024-01-01', '2024-01-11', '2024-01-21', '2024-01-31']);
        expect(emitted![0].data[0].value).toBe(100);
        expect(emitted![0].data[3].value).toBe(121);
        // Placing a measure leaves measure mode.
        expect(onmeasuremodechange).toHaveBeenLastCalledWith(false);
    });

    it('debounces a second click within 300 ms (double-fire guard)', () => {
        const {api, onmeasureschange} = mount();
        api.startMeasureMode();
        vi.spyOn(Date, 'now').mockReturnValue(5000); // both clicks share the clock
        api.addPoint('2024-01-01', 100); // pending start
        api.addPoint('2024-01-31', 121); // 0 ms later → ignored, no measure
        expect(onmeasureschange).not.toHaveBeenCalled();
    });

    it('normalises order when the second click is earlier than the first', () => {
        const {api, onmeasureschange} = mount();
        api.startMeasureMode();
        const now = vi.spyOn(Date, 'now');
        now.mockReturnValue(1000);
        api.addPoint('2024-01-31', 121); // pending start = later date
        now.mockReturnValue(2000);
        api.addPoint('2024-01-01', 100); // earlier date → start/end swapped
        const emitted = lastEmit(onmeasureschange);
        expect(emitted![0].data[0].date).toBe('2024-01-01');
        expect(emitted![0].data[emitted![0].data.length - 1].date).toBe('2024-01-31');
    });
});

describe('MeasurePanel — updatePendingEnd live preview', () => {
    it('does nothing before a start point exists', () => {
        const {api, onmeasureschange} = mount();
        api.startMeasureMode();
        api.updatePendingEnd('2024-01-31', 121);
        expect(onmeasureschange).not.toHaveBeenCalled();
    });

    it('emits a preview signal tagged __pending__ once a start exists', () => {
        const {api, onmeasureschange} = mount();
        api.startMeasureMode();
        vi.spyOn(Date, 'now').mockReturnValue(1000);
        api.addPoint('2024-01-01', 100);
        onmeasureschange.mockClear();
        api.updatePendingEnd('2024-01-31', 121);
        const emitted = lastEmit(onmeasureschange);
        expect(emitted).toHaveLength(1);
        expect(emitted![0].id).toBe('__pending__');
    });

    it('ignores a zero-length preview (end === start)', () => {
        const {api, onmeasureschange} = mount();
        api.startMeasureMode();
        vi.spyOn(Date, 'now').mockReturnValue(1000);
        api.addPoint('2024-01-01', 100);
        onmeasureschange.mockClear();
        api.updatePendingEnd('2024-01-01', 100); // same day → no-op
        expect(onmeasureschange).not.toHaveBeenCalled();
    });
});

describe('MeasurePanel — addMeasureFromChartData', () => {
    it('creates a measure spanning the full data range', () => {
        const {api, onmeasureschange} = mount();
        api.addMeasureFromChartData();
        const emitted = lastEmit(onmeasureschange);
        expect(emitted).toHaveLength(1);
        expect(emitted![0].data[0].date).toBe('2024-01-01');
        expect(emitted![0].data[emitted![0].data.length - 1].date).toBe('2024-01-31');
    });

    it('is a no-op with fewer than two points', () => {
        const {api, onmeasureschange} = mount({chartData: [{date: '2024-01-01', value: 100}]});
        api.addMeasureFromChartData();
        expect(onmeasureschange).not.toHaveBeenCalled();
    });

    it('is a no-op when first and last dates coincide', () => {
        const {api, onmeasureschange} = mount({
            chartData: [
                {date: '2024-01-01', value: 100},
                {date: '2024-01-01', value: 100},
            ],
        });
        api.addMeasureFromChartData();
        expect(onmeasureschange).not.toHaveBeenCalled();
    });
});

describe('MeasurePanel — clearMeasures', () => {
    it('clears completed and pending state before accepting a fresh measure', async () => {
        const {api, container, onmeasureschange, onmeasuremodechange} = mount();

        api.addMeasureFromChartData();
        api.addMeasureFromChartData();
        await waitFor(() => expect(rowsById(container, 'main')).toHaveLength(2));
        expect(lastEmit(onmeasureschange)?.map((signal) => signal.id)).toEqual(['measure-0', 'measure-1']);

        const now = vi.spyOn(Date, 'now').mockReturnValue(1000);
        api.startMeasureMode();
        api.addPoint('2024-01-01', 100);
        api.updatePendingEnd('2024-01-21', 115);
        expect(lastEmit(onmeasureschange)?.map((signal) => signal.id)).toEqual(['measure-0', 'measure-1', '__pending__']);
        expect(onmeasuremodechange).toHaveBeenLastCalledWith(true);

        api.clearMeasures();
        expect(lastEmit(onmeasureschange)).toEqual([]);
        expect(onmeasuremodechange).toHaveBeenLastCalledWith(false);
        await waitFor(() => expect(rowsById(container, 'main')).toHaveLength(0));

        onmeasureschange.mockClear();
        api.addPoint('2024-01-11', 108);
        expect(onmeasureschange).not.toHaveBeenCalled();

        api.startMeasureMode();
        now.mockReturnValue(1000);
        api.addPoint('2024-01-11', 108);
        now.mockReturnValue(1400);
        api.addPoint('2024-01-31', 121);

        const rebuilt = lastEmit(onmeasureschange);
        expect(rebuilt).toHaveLength(1);
        const freshMeasure = rebuilt?.find((signal) => signal.id === 'measure-0');
        expect(freshMeasure?.data.map((point) => point.date)).toEqual(['2024-01-11', '2024-01-21', '2024-01-31']);
        expect(rebuilt?.some((signal) => signal.id === '__pending__')).toBe(false);
        expect(onmeasuremodechange.mock.calls.map(([active]) => active)).toEqual([true, false, true, false]);
        await waitFor(() => expect(rowsById(container, 'main')).toHaveLength(1));
    });
});

describe('MeasurePanel — summary table (expanded card)', () => {
    it('renders a main row with the exact start/end/delta values', async () => {
        const {api, container} = mount();
        api.addMeasureFromChartData(); // auto-expands the new card → DataTable mounts
        await waitFor(() => expect(container.querySelector('[data-row-id="main"]')).not.toBeNull());
        const main = container.querySelector('[data-row-id="main"]')!;
        const text = main.textContent ?? '';
        expect(text).toContain('100.0000'); // valueStart (fmtValue)
        expect(text).toContain('121.0000'); // valueEnd
        expect(text).toContain('+21.0000'); // deltaAbs (fmtDelta)
        expect(text).toContain('+21.00%'); // deltaPct (fmtPct)
    });

    it('adds a ghost original-currency row under FX conversion', async () => {
        const fxData: LineDataPoint[] = baseData.map((d) => ({
            ...d,
            originalValue: d.value * 10, // USD leg an order of magnitude apart
            originalCurrency: 'USD',
        }));
        const {api, container} = mount({
            chartData: fxData,
            displayCurrency: 'EUR',
            displayCurrencyFlag: '🇪🇺',
        });
        api.addMeasureFromChartData();
        await waitFor(() => expect(container.querySelector('[data-row-id="main"]')).not.toBeNull());
        // The FX branch pushes a second, ghost row for the native currency leg.
        const original = container.querySelector('[data-row-id="main-original"]');
        expect(original).not.toBeNull();
        expect(original!.textContent ?? '').toContain('1000.0000'); // 100 * 10
    });

    it('adds one row per primary-axis overlay signal (ghost and currency variants)', async () => {
        const {api, container} = mount({
            overlaySignals: [
                overlaySignal({label: 'Bench', currency: 'GBP', currencyFlag: '🇬🇧'}),
                overlaySignal({label: 'Ghosted', opacity: 0.5}),
                overlaySignal({label: 'OtherAxis', yAxisIndex: 1}), // filtered out
            ],
        });
        api.addMeasureFromChartData();
        await waitFor(() => expect(container.querySelector('[data-row-id="main"]')).not.toBeNull());
        expect(container.querySelector('[data-row-id="sig-Bench"]')).not.toBeNull();
        expect(container.querySelector('[data-row-id="sig-Ghosted"]')).not.toBeNull();
        // yAxisIndex 1 is excluded from the primary-axis summary.
        expect(container.querySelector('[data-row-id="sig-OtherAxis"]')).toBeNull();
    });

    it('repopulates updated peer rows for the existing completed measure after overlays clear', async () => {
        const peer = (label: string, values: [number, number, number, number]) =>
            overlaySignal({
                label,
                data: baseData.map(({date}, index) => ({date, value: values[index]})),
            });
        const initialPeers = [peer('Peer-A', [200, 220, 240, 260]), peer('Peer-B', [80, 88, 96, 104])];
        const correctedPeers = [peer('Peer-A', [300, 330, 360, 390]), peer('Peer-B', [40, 50, 60, 70])];
        const {api, container, onmeasureschange, rerender} = mount({
            overlaySignals: initialPeers,
            preserveUnavailableMeasures: true,
            storageKeyPrefix: 'test-overlay-repopulation',
        });

        api.addMeasureFromChartData();
        await waitFor(() => {
            expect(rowsById(container, 'main')).toHaveLength(1);
            expect(rowsById(container, 'sig-Peer-A')).toHaveLength(1);
            expect(rowsById(container, 'sig-Peer-B')).toHaveLength(1);
        });
        expect(rowById(container, 'main')).toHaveTextContent('100.0000');
        expect(rowById(container, 'main')).toHaveTextContent('121.0000');
        expect(rowById(container, 'sig-Peer-A')).toHaveTextContent('200.0000');
        expect(rowById(container, 'sig-Peer-A')).toHaveTextContent('260.0000');
        expect(rowById(container, 'sig-Peer-B')).toHaveTextContent('80.0000');
        expect(rowById(container, 'sig-Peer-B')).toHaveTextContent('104.0000');
        expect(within(container).getByTestId('date-range-input-start')).toHaveValue('2024-01-01');
        expect(within(container).getByTestId('date-range-input-end')).toHaveValue('2024-01-31');
        expect(lastEmit(onmeasureschange)?.map((signal) => signal.id)).toEqual(['measure-0']);

        await rerender({
            chartData: baseData,
            overlaySignals: [],
            preserveUnavailableMeasures: true,
            storageKeyPrefix: 'test-overlay-repopulation',
        } as PanelProps);
        await waitFor(() => {
            expect(rowsById(container, 'sig-Peer-A')).toHaveLength(0);
            expect(rowsById(container, 'sig-Peer-B')).toHaveLength(0);
        });
        expect(rowsById(container, 'main')).toHaveLength(1);
        expect(rowById(container, 'main')).toHaveTextContent('100.0000');
        expect(rowById(container, 'main')).toHaveTextContent('121.0000');
        expect(within(container).getByTestId('date-range-input-start')).toHaveValue('2024-01-01');
        expect(within(container).getByTestId('date-range-input-end')).toHaveValue('2024-01-31');
        expect(lastEmit(onmeasureschange)?.map((signal) => signal.id)).toEqual(['measure-0']);

        await rerender({
            chartData: baseData,
            overlaySignals: correctedPeers,
            preserveUnavailableMeasures: true,
            storageKeyPrefix: 'test-overlay-repopulation',
        } as PanelProps);
        await waitFor(() => {
            expect(rowsById(container, 'sig-Peer-A')).toHaveLength(1);
            expect(rowsById(container, 'sig-Peer-B')).toHaveLength(1);
        });
        expect(rowsById(container, 'main')).toHaveLength(1);
        expect(rowById(container, 'main')).toHaveTextContent('100.0000');
        expect(rowById(container, 'main')).toHaveTextContent('121.0000');
        expect(rowById(container, 'sig-Peer-A')).toHaveTextContent('300.0000');
        expect(rowById(container, 'sig-Peer-A')).toHaveTextContent('390.0000');
        expect(rowById(container, 'sig-Peer-A')).toHaveTextContent('+90.0000');
        expect(rowById(container, 'sig-Peer-A')).not.toHaveTextContent('200.0000');
        expect(rowById(container, 'sig-Peer-B')).toHaveTextContent('40.0000');
        expect(rowById(container, 'sig-Peer-B')).toHaveTextContent('70.0000');
        expect(rowById(container, 'sig-Peer-B')).toHaveTextContent('+30.0000');
        expect(rowById(container, 'sig-Peer-B')).not.toHaveTextContent('80.0000');
        expect(within(container).getByTestId('date-range-input-start')).toHaveValue('2024-01-01');
        expect(within(container).getByTestId('date-range-input-end')).toHaveValue('2024-01-31');
        expect(lastEmit(onmeasureschange)?.map((signal) => signal.id)).toEqual(['measure-0']);
    });

    it('presents return values as percentage points without price-only fields', async () => {
        const {api, container} = mount({
            measurementUnit: 'percentage-points',
            mainCurrency: 'USD',
            mainCurrencyFlag: '🇺🇸',
            displayCurrency: 'EUR',
            displayCurrencyFlag: '🇪🇺',
            storageKeyPrefix: 'test-return-summary',
        });
        api.addMeasureFromChartData();

        const table = within(container);
        await waitFor(() => expect(table.queryByTestId('dt-header-days')).not.toBeNull());

        expect(table.getByTestId('dt-header-valueStart')).toBeInTheDocument();
        expect(table.getByTestId('dt-header-valueEnd')).toBeInTheDocument();
        expect(table.getByTestId('dt-header-deltaAbs')).toBeInTheDocument();
        expect(table.getByTestId('dt-header-days')).toBeInTheDocument();
        expect(table.queryByTestId('dt-header-deltaPct')).toBeNull();
        expect(table.queryByTestId('dt-header-annualizedPct')).toBeNull();

        const main = rowById(container, 'main');
        expect(main).not.toBeNull();
        expect(main).toHaveTextContent('100.00%');
        expect(main).toHaveTextContent('121.00%');
        expect(main).toHaveTextContent('+21.00 pp');
        expect(main).toHaveTextContent('30d');
        expect(main).not.toHaveTextContent('USD');
        expect(main).not.toHaveTextContent('EUR');
        expect(main).not.toHaveTextContent('🇺🇸');
        expect(main).not.toHaveTextContent('🇪🇺');
        expect(rowById(container, 'main-original')).toBeNull();
    });
});

describe('MeasurePanel — independent instances', () => {
    it('keeps simultaneously mounted Price and Return panels isolated', async () => {
        const price = mount({
            mainCurrency: 'USD',
            storageKeyPrefix: 'test-price-instance',
        });
        const returnData: LineDataPoint[] = [
            {date: '2024-02-01', value: -5},
            {date: '2024-02-11', value: 7},
        ];
        const returns = mount({
            chartData: returnData,
            measurementUnit: 'percentage-points',
            preserveUnavailableMeasures: true,
            mainCurrency: 'USD',
            mainCurrencyFlag: '🇺🇸',
            storageKeyPrefix: 'test-return-instance',
        });

        price.api.addMeasureFromChartData();
        const priceTable = within(price.container);
        await waitFor(() => expect(priceTable.queryByTestId('dt-header-deltaPct')).not.toBeNull());
        expect(returns.onmeasureschange).not.toHaveBeenCalled();

        const priceRendered = lastEmit(price.onmeasureschange);
        expect(priceRendered).toHaveLength(1);
        const priceMeasure = priceRendered?.find((signal) => signal.id === 'measure-0');
        expect(priceMeasure?.data.map((point) => point.date)).toEqual(baseData.map((point) => point.date));

        price.onmeasureschange.mockClear();
        returns.api.addMeasureFromChartData();
        const returnTable = within(returns.container);
        await waitFor(() => expect(returnTable.queryByTestId('dt-header-days')).not.toBeNull());

        expect(price.onmeasureschange).not.toHaveBeenCalled();
        expect(priceTable.getByTestId('dt-header-deltaPct')).toBeInTheDocument();
        expect(priceTable.getByTestId('dt-header-annualizedPct')).toBeInTheDocument();
        expect(priceTable.queryByTestId('dt-header-days')).toBeNull();
        expect(returnTable.getByTestId('dt-header-days')).toBeInTheDocument();
        expect(returnTable.queryByTestId('dt-header-deltaPct')).toBeNull();
        expect(returnTable.queryByTestId('dt-header-annualizedPct')).toBeNull();

        const priceMain = rowById(price.container, 'main');
        const returnMain = rowById(returns.container, 'main');
        expect(priceMain).toHaveTextContent('USD');
        expect(returnMain).not.toHaveTextContent('USD');

        const returnRendered = lastEmit(returns.onmeasureschange);
        expect(returnRendered).toHaveLength(1);
        const returnMeasure = returnRendered?.find((signal) => signal.id === 'measure-0');
        expect(returnMeasure?.data.map((point) => point.date)).toEqual(returnData.map((point) => point.date));
    });
});

describe('MeasurePanel — card interactions', () => {
    it('collapses to a compact summary when the chevron is toggled', async () => {
        const {api, container} = mount();
        api.addMeasureFromChartData();
        await waitFor(() => expect(container.querySelector('[data-row-id="main"]')).not.toBeNull());
        // The chevron is the first button in the card header; clicking it collapses.
        const chevron = container.querySelector('button');
        expect(chevron).not.toBeNull();
        await fireEvent.click(chevron!);
        // Collapsed view drops the summary table and shows the 📏 range line.
        await waitFor(() => expect(container.querySelector('[data-row-id="main"]')).toBeNull());
        expect(container.textContent ?? '').toContain('📏 2024-01-01 → 2024-01-31');
    });

    it('auto-deletes a completed price measure by default when its dates leave non-empty data', async () => {
        const storageKeyPrefix = 'test-price-default-pruning';
        const {api, container, onmeasureschange, rerender} = mount({
            measurementUnit: 'price',
            storageKeyPrefix,
        });
        const panel = within(container);

        api.addMeasureFromChartData();
        await waitFor(() => {
            expect(lastEmit(onmeasureschange)?.map((signal) => signal.id)).toEqual(['measure-0']);
            expect(rowsById(container, 'main')).toHaveLength(1);
            expect(panel.getByTestId('date-range-input-start')).toHaveValue('2024-01-01');
            expect(panel.getByTestId('date-range-input-end')).toHaveValue('2024-01-31');
        });

        onmeasureschange.mockClear();
        await rerender({
            chartData: incompatibleData,
            measurementUnit: 'price',
            storageKeyPrefix,
        } as PanelProps);
        await waitFor(() => {
            expect(lastEmit(onmeasureschange)).toEqual([]);
            expect(rowsById(container, 'main')).toHaveLength(0);
            expect(panel.queryByTestId('date-range-input-start')).toBeNull();
            expect(panel.queryByTestId('date-range-input-end')).toBeNull();
            expect(panel.queryByTestId('dt-header-deltaPct')).toBeNull();
        });
    });

    it('preserves a completed price measure across incompatible data and restores its summary', async () => {
        const storageKeyPrefix = 'test-price-unavailable-retention';
        const {api, container, onmeasureschange, rerender} = mount({
            measurementUnit: 'price',
            preserveUnavailableMeasures: true,
            storageKeyPrefix,
        });
        const panel = within(container);

        api.addMeasureFromChartData();
        await waitFor(() => {
            expect(lastEmit(onmeasureschange)?.map((signal) => signal.id)).toEqual(['measure-0']);
            expect(rowsById(container, 'main')).toHaveLength(1);
            expect(panel.getByTestId('dt-header-deltaPct')).toBeInTheDocument();
        });
        expect(panel.getByTestId('date-range-input-start')).toHaveValue('2024-01-01');
        expect(panel.getByTestId('date-range-input-end')).toHaveValue('2024-01-31');

        onmeasureschange.mockClear();
        await rerender({
            chartData: incompatibleData,
            measurementUnit: 'price',
            preserveUnavailableMeasures: true,
            storageKeyPrefix,
        } as PanelProps);
        await waitFor(() => {
            expect(lastEmit(onmeasureschange)).toEqual([]);
            expect(rowsById(container, 'main')).toHaveLength(0);
            expect(panel.getByTestId('date-range-input-start')).toHaveValue('2024-01-01');
            expect(panel.getByTestId('date-range-input-end')).toHaveValue('2024-01-31');
            expect(panel.queryByTestId('dt-header-deltaPct')).toBeNull();
        });

        onmeasureschange.mockClear();
        await rerender({
            chartData: baseData,
            measurementUnit: 'price',
            preserveUnavailableMeasures: true,
            storageKeyPrefix,
        } as PanelProps);
        await waitFor(() => {
            expect(lastEmit(onmeasureschange)?.map((signal) => signal.id)).toEqual(['measure-0']);
            expect(rowsById(container, 'main')).toHaveLength(1);
            expect(panel.getByTestId('dt-header-deltaPct')).toBeInTheDocument();
        });
        expect(panel.getByTestId('date-range-input-start')).toHaveValue('2024-01-01');
        expect(panel.getByTestId('date-range-input-end')).toHaveValue('2024-01-31');
    });

    it('retains its date anchors while preserved endpoints are unavailable', async () => {
        const {api, container, onmeasureschange, rerender} = mount({
            preserveUnavailableMeasures: true,
            storageKeyPrefix: 'test-preserved-return',
        });
        api.addMeasureFromChartData();
        await waitFor(() => expect(lastEmit(onmeasureschange)).toHaveLength(1));

        onmeasureschange.mockClear();
        const unavailable = baseData.map((point) => (point.date === '2024-01-01' || point.date === '2024-01-31' ? {...point, missing: true} : point));
        await rerender({
            chartData: unavailable,
            preserveUnavailableMeasures: true,
        } as PanelProps);
        await waitFor(() => expect(lastEmit(onmeasureschange)).toEqual([]));

        const panel = within(container);
        expect(panel.getByTestId('date-range-input-start')).toHaveValue('2024-01-01');
        expect(panel.getByTestId('date-range-input-end')).toHaveValue('2024-01-31');

        onmeasureschange.mockClear();
        await rerender({
            chartData: baseData,
            preserveUnavailableMeasures: true,
        } as PanelProps);
        await waitFor(() => expect(lastEmit(onmeasureschange)).toHaveLength(1));

        const restored = lastEmit(onmeasureschange);
        const restoredMeasure = restored?.find((signal) => signal.id === 'measure-0');
        expect(restoredMeasure?.data.map((point) => point.date)).toEqual(baseData.map((point) => point.date));
    });
});
