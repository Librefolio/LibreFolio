// @vitest-environment jsdom
/**
 * PositionsPanel — component test (Vitest + jsdom), Y5-2 (#48): the per-position return chart wired under
 * the Holdings table.
 *
 * ## Subject
 *
 * In the Holdings + Table view, and only there, the panel mounts `PositionsReturnChart` under the table:
 *
 * - with NO row selected it draws the portfolio line alone, built from `portfolioHistory`;
 * - selecting rows asks the parent for the series of exactly those positions —
 *   `onRequestPositionsSeries(selectionKeys(rows))`, once per change, never on mount and never for an empty
 *   selection — and the answer (`positionsSeries`) is drawn beside the portfolio line;
 * - the chart's view (absolute / percentage) is panel state kept per user under
 *   `getUserStorageKey('dashboard-positions-chart-view')`, `percentage` by default;
 * - the legend hides and shows lines without asking for anything new.
 *
 * ## What is real, what is replaced
 *
 * The real panel, the real `ExposureTable` (so selection goes through its real checkboxes) and the real
 * `PositionsReturnChart`. Replaced: `echarts` (a recorder: the option is what is read), `$lib/api` (the
 * table's reference-data loads), `localStorage` (a Map, emptied before each case; the product's own
 * `getUserStorageKey` builds the keys) and `getClientRects` (jsdom lays nothing out).
 *
 * Rows are found by their real keys (`dt-row-checkbox-<asset>-<broker>`), lines by `data-line-count` and
 * the legend ids. Nothing translated is asserted.
 */
import {afterAll, beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';

const {chartInstances, echartsModule} = vi.hoisted(() => {
    interface FakeChart {
        setOptionCalls: Array<{option: Record<string, unknown>; opts: unknown}>;
        [method: string]: unknown;
    }
    const chartInstances: FakeChart[] = [];

    function createFakeChart(dom: unknown): FakeChart {
        let disposed = false;
        const chart: FakeChart = {
            setOptionCalls: [],
            setOption(option: Record<string, unknown>, opts?: unknown) {
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
            format: {getTextRect: (text: string) => ({x: 0, y: 0, width: text.length * 7, height: 14})},
        },
    };
});

vi.mock('echarts', () => echartsModule);

vi.mock('$lib/api', () => ({
    zodiosApi: new Proxy(
        {},
        {
            get(_target, property) {
                if (property === 'list_currencies_api_v1_utilities_currencies_get') return vi.fn(async () => ({items: []}));
                if (property === 'list_assets_api_v1_assets_query_get') return vi.fn(async () => []);
                return vi.fn(async () => undefined);
            },
        },
    ),
}));

const storage = new Map<string, string>();
vi.stubGlobal('localStorage', {
    getItem: (key: string) => storage.get(key) ?? null,
    setItem: (key: string, value: string) => void storage.set(key, value),
    removeItem: (key: string) => void storage.delete(key),
});

import {fireEvent, render, screen, setupI18n, waitFor} from '$test/component';
import {getUserStorageKey} from '$lib/utils/storage';
import type {ComponentProps} from 'svelte';
import PositionsPanel from './PositionsPanel.svelte';
import type {HistoryPointLike, PositionKey, PositionsSeriesResponse, PositionSeries} from './positionsSeries';

// =============================================================================
// Fixtures
// =============================================================================

function holding(assetId: number, brokerId: number | null) {
    return {
        asset_id: assetId,
        asset_name: `Asset ${assetId}`,
        asset_type: 'STOCK',
        broker_id: brokerId,
        broker_name: brokerId == null ? null : `Broker ${brokerId}`,
        quantity: '10',
        current_value: String(assetId * 1000), // distinct, so the table order is deterministic: 33, 22, 11
        yield_on_cost: {
            status: 'no_income',
            value: '0',
            reason: null,
            provenance: {source: 'transactions', window_start: '2025-09-12', window_end: '2026-09-11', first_pair_transaction_date: null, gross_income_transaction_count: 0, gross_income_per_unit: null, net_zero: false, fx: [], issue_date: null, issue_pair: null},
        },
    };
}

/** A summary as the panel reads it; the store's type is the generated one, so the fixture is cast. */
function summaryOf(...holdings: Array<ReturnType<typeof holding>>) {
    return {net_worth: {code: 'EUR', amount: '60000'}, holdings, holding_groups: []} as never;
}

const SUMMARY = () => summaryOf(holding(11, 1), holding(22, 1), holding(33, 2));

const HISTORY: HistoryPointLike[] = [
    {date: '2026-01-02', through: '2026-01-02', total_pnl: {code: 'EUR', amount: '500'}, twrr: '0'},
    {date: '2026-01-03', through: '2026-01-03', total_pnl: {code: 'EUR', amount: '650'}, twrr: '0.02'},
    {date: '2026-01-04', through: '2026-01-04', total_pnl: {code: 'EUR', amount: '400'}, twrr: '-0.015'},
];

function seriesFor(assetId: number, brokerId: number | null, pnls: Array<[string, string]>): PositionSeries {
    return {
        key: {asset_id: assetId, broker_id: brokerId},
        asset_name: `Asset ${assetId}`,
        asset_ticker: null,
        broker_name: brokerId == null ? null : `Broker ${brokerId}`,
        first_date: '2026-01-02',
        last_date: '2026-01-04',
        held_at_start: true,
        held_at_end: true,
        closed_on: null,
        complete: true,
        points: pnls.map(([pnl, pct], i) => ({
            date: `2026-01-0${i + 2}`,
            quantity: '10',
            market_value: '1000',
            cost_basis: '900',
            pnl,
            base: '900',
            pnl_percent: pct,
            valuation_source: 'MARKET_PRICE' as const,
            complete: true,
        })),
    };
}

const response = (...list: PositionSeries[]): PositionsSeriesResponse => ({currency: 'EUR', date_from: '2026-01-02', date_to: '2026-01-04', series: list, missing_fx_pairs: []});

type PanelProps = Record<string, unknown>;

function panelProps(overrides: PanelProps = {}): ComponentProps<typeof PositionsPanel> {
    return {summary: SUMMARY(), contribution: null, portfolioHistory: HISTORY, ...overrides} as unknown as ComponentProps<typeof PositionsPanel>;
}

/** Mounts the panel and waits for the holdings rows. */
async function mountPanel(overrides: PanelProps = {}) {
    const view = render(PositionsPanel, {props: panelProps(overrides)});
    await waitFor(() => expect(document.querySelectorAll('tbody tr[data-row-id]').length).toBeGreaterThan(0));
    return view;
}

const chartRoot = () => screen.getByTestId('positions-return-chart');
const checkbox = (key: string) => screen.getByTestId(`dt-row-checkbox-${key}`);
const keyOf = (assetId: number, brokerId: number | null): PositionKey => ({asset_id: assetId, broker_id: brokerId});

// Reading the option the chart handed ECharts ------------------------------------------------------------------

type Json = Record<string, unknown>;

function lastSeries(): Json[] | undefined {
    for (const chart of [...chartInstances].reverse()) {
        for (let i = chart.setOptionCalls.length - 1; i >= 0; i--) {
            const series = chart.setOptionCalls[i].option.series;
            if (Array.isArray(series)) return series as Json[];
        }
    }
    return undefined;
}

const LINE_IDS = ['portfolio', '11-1', '22-1', '33-2'];
const drawnIds = (): string[] =>
    (lastSeries() ?? [])
        .map((s) => s.id)
        .filter((id): id is string => typeof id === 'string' && LINE_IDS.includes(id))
        .sort();

function datumValue(datum: unknown): unknown {
    if (Array.isArray(datum)) return datum[datum.length - 1];
    if (datum && typeof datum === 'object' && 'value' in (datum as Json)) return datumValue((datum as Json).value);
    return datum;
}

const valuesOfSeries = (id: string): unknown[] => (((lastSeries() ?? []).find((s) => s.id === id)?.data as unknown[]) ?? []).map(datumValue);

const CHART_VIEW_KEY = () => getUserStorageKey('dashboard-positions-chart-view');

let restoreLayout: (() => void) | undefined;

beforeAll(async () => {
    await setupI18n();
    const spy = vi.spyOn(Element.prototype, 'getClientRects').mockImplementation(() => [{x: 0, y: 0, top: 0, left: 0, width: 800, height: 400, right: 800, bottom: 400}] as unknown as DOMRectList);
    restoreLayout = () => spy.mockRestore();
});

afterAll(() => {
    restoreLayout?.();
});

beforeEach(() => {
    storage.clear();
    chartInstances.length = 0;
});

// =============================================================================
// Where the chart is mounted
// =============================================================================

describe('PositionsPanel — the return chart is Holdings + Table only', () => {
    it('Holdings + Table (the default): the chart is under the table', async () => {
        await mountPanel();
        expect(chartRoot()).toBeInTheDocument();
        expect(screen.getByTestId('exposure-table')).toBeInTheDocument();
    });

    it('Holdings + Map: no chart', async () => {
        storage.set(getUserStorageKey('dashboard-positions-semantic'), 'holdings');
        storage.set(getUserStorageKey('dashboard-positions-visual'), 'map');
        render(PositionsPanel, {props: panelProps()});
        await waitFor(() => expect(screen.getByTestId('positions-toggle-map')).toHaveAttribute('aria-pressed', 'true'));
        expect(screen.queryByTestId('positions-return-chart')).toBeNull();
    });

    it('switching from the table to the map takes the chart away', async () => {
        await mountPanel();
        expect(chartRoot()).toBeInTheDocument();
        await fireEvent.click(screen.getByTestId('positions-toggle-map'));
        await waitFor(() => expect(screen.queryByTestId('positions-return-chart')).toBeNull());
    });

    it('Performance: no chart, in either visual mode', async () => {
        storage.set(getUserStorageKey('dashboard-positions-semantic'), 'performance');
        render(PositionsPanel, {props: panelProps()});
        await waitFor(() => expect(screen.getByTestId('positions-toggle-performance')).toHaveAttribute('aria-pressed', 'true'));
        expect(screen.queryByTestId('positions-return-chart')).toBeNull();
        await fireEvent.click(screen.getByTestId('positions-toggle-map'));
        await waitFor(() => expect(screen.getByTestId('positions-toggle-map')).toHaveAttribute('aria-pressed', 'true'));
        expect(screen.queryByTestId('positions-return-chart')).toBeNull();
    });
});

// =============================================================================
// No selection: the portfolio line alone
// =============================================================================

describe('PositionsPanel — with no row selected', () => {
    it('draws the portfolio line alone, from portfolioHistory', async () => {
        await mountPanel();
        await waitFor(() => expect(chartRoot()).toHaveAttribute('data-line-count', '1'));
        expect(chartRoot()).toHaveAttribute('data-state', 'ready');
        expect(screen.getByTestId('positions-chart-legend-portfolio')).toHaveAttribute('data-kind', 'portfolio');
        await waitFor(() => expect(drawnIds()).toEqual(['portfolio']));
    });

    it('asks for nothing on mount', async () => {
        const onRequestPositionsSeries = vi.fn();
        await mountPanel({onRequestPositionsSeries});
        await waitFor(() => expect(chartRoot()).toHaveAttribute('data-state', 'ready'));
        expect(onRequestPositionsSeries).not.toHaveBeenCalled();
    });

    it('without a history there is no line to draw: the chart is empty', async () => {
        await mountPanel({portfolioHistory: []});
        expect(chartRoot()).toHaveAttribute('data-line-count', '0');
        expect(chartRoot()).toHaveAttribute('data-state', 'empty');
    });

    it('the portfolio line is the Dashboard’s: base 100 of the TWRR in the percentage view', async () => {
        await mountPanel();
        await waitFor(() => expect(valuesOfSeries('portfolio')).toHaveLength(3));
        const values = valuesOfSeries('portfolio') as number[];
        expect(values[0]).toBe(100);
        expect(values[1]).toBeCloseTo(102, 9);
        expect(values[2]).toBeCloseTo(98.5, 9);
    });
});

// =============================================================================
// Selecting rows
// =============================================================================

describe('PositionsPanel — selecting rows asks for their series', () => {
    it('one row: onRequestPositionsSeries once, with that row’s key', async () => {
        const onRequestPositionsSeries = vi.fn();
        await mountPanel({onRequestPositionsSeries});
        await fireEvent.click(checkbox('22-1'));

        await waitFor(() => expect(onRequestPositionsSeries).toHaveBeenCalledTimes(1));
        expect(onRequestPositionsSeries).toHaveBeenCalledWith([keyOf(22, 1)]);
    });

    it('a second row: asked again, once, with both keys in table order', async () => {
        const onRequestPositionsSeries = vi.fn();
        await mountPanel({onRequestPositionsSeries});
        await fireEvent.click(checkbox('22-1'));
        await waitFor(() => expect(onRequestPositionsSeries).toHaveBeenCalledTimes(1));

        await fireEvent.click(checkbox('33-2'));
        await waitFor(() => expect(onRequestPositionsSeries).toHaveBeenCalledTimes(2));
        expect(onRequestPositionsSeries).toHaveBeenLastCalledWith([keyOf(33, 2), keyOf(22, 1)]);
    });

    it('a holding without a broker is asked with broker_id null', async () => {
        const onRequestPositionsSeries = vi.fn();
        await mountPanel({onRequestPositionsSeries, summary: summaryOf(holding(11, 1), holding(44, null))});
        await fireEvent.click(checkbox('44-0'));

        await waitFor(() => expect(onRequestPositionsSeries).toHaveBeenCalledTimes(1));
        expect(onRequestPositionsSeries).toHaveBeenCalledWith([keyOf(44, null)]);
    });

    it('emptying the selection does not ask: the chart falls back to the portfolio line', async () => {
        const onRequestPositionsSeries = vi.fn();
        await mountPanel({onRequestPositionsSeries});
        await fireEvent.click(checkbox('22-1'));
        await waitFor(() => expect(onRequestPositionsSeries).toHaveBeenCalledTimes(1));

        await fireEvent.click(checkbox('22-1'));
        await waitFor(() => expect(checkbox('22-1')).toHaveAttribute('data-state', 'unchecked'));
        expect(onRequestPositionsSeries).toHaveBeenCalledTimes(1);
    });

    it('works without the callback: the selection is still made, the chart still shows the portfolio', async () => {
        await mountPanel();
        await fireEvent.click(checkbox('22-1'));

        await waitFor(() => expect(checkbox('22-1')).toHaveAttribute('data-state', 'checked'));
        expect(chartRoot()).toHaveAttribute('data-line-count', '1');
        expect(chartRoot()).toHaveAttribute('data-state', 'ready');
    });
});

// =============================================================================
// The answer is drawn
// =============================================================================

describe('PositionsPanel — the series answer is drawn with the portfolio line', () => {
    const answer = () =>
        response(
            seriesFor(22, 1, [
                ['0', '0'],
                ['90', '0.1'],
                ['-45', '-0.05'],
            ]),
            seriesFor(33, 2, [
                ['0', '0'],
                ['10', '0.01'],
                ['20', '0.02'],
            ]),
        );

    it('each series of the response is a line beside the portfolio line', async () => {
        const view = await mountPanel({onRequestPositionsSeries: vi.fn()});
        await fireEvent.click(checkbox('22-1'));
        await fireEvent.click(checkbox('33-2'));

        await view.rerender(panelProps({onRequestPositionsSeries: vi.fn(), positionsSeries: answer()}));

        await waitFor(() => expect(chartRoot()).toHaveAttribute('data-line-count', '3'));
        expect(screen.getByTestId('positions-chart-legend-22-1')).toBeInTheDocument();
        expect(screen.getByTestId('positions-chart-legend-33-2')).toBeInTheDocument();
        await waitFor(() => expect(drawnIds()).toEqual(['22-1', '33-2', 'portfolio']));
    });

    it('the percentage view draws base 100 of each position’s pnl_percent', async () => {
        const view = await mountPanel({onRequestPositionsSeries: vi.fn()});
        await fireEvent.click(checkbox('22-1'));
        await view.rerender(panelProps({onRequestPositionsSeries: vi.fn(), positionsSeries: answer()}));

        await waitFor(() => expect(valuesOfSeries('22-1')).toHaveLength(3));
        const values = valuesOfSeries('22-1') as number[];
        expect(values[0]).toBe(100);
        expect(values[1]).toBeCloseTo(110, 9);
        expect(values[2]).toBeCloseTo(95, 9);
    });

    it('the absolute view draws each position’s pnl and the portfolio’s from 0', async () => {
        storage.set(CHART_VIEW_KEY(), 'absolute');
        const view = await mountPanel({onRequestPositionsSeries: vi.fn()});
        await fireEvent.click(checkbox('22-1'));
        await view.rerender(panelProps({onRequestPositionsSeries: vi.fn(), positionsSeries: answer()}));

        await waitFor(() => expect(valuesOfSeries('22-1')).toHaveLength(3));
        expect(valuesOfSeries('22-1')).toEqual([0, 90, -45]);
        const portfolio = valuesOfSeries('portfolio') as number[];
        expect(portfolio[0]).toBe(0);
        expect(portfolio[1]).toBeCloseTo(150, 9);
        expect(portfolio[2]).toBeCloseTo(-100, 9);
    });

    it('loading: the chart says so', async () => {
        const view = await mountPanel({onRequestPositionsSeries: vi.fn()});
        await fireEvent.click(checkbox('22-1'));
        await view.rerender(panelProps({onRequestPositionsSeries: vi.fn(), positionsSeriesLoading: true}));

        await waitFor(() => expect(chartRoot()).toHaveAttribute('data-state', 'loading'));
    });

    it('failed: the chart says so', async () => {
        const view = await mountPanel({onRequestPositionsSeries: vi.fn()});
        await fireEvent.click(checkbox('22-1'));
        await view.rerender(panelProps({onRequestPositionsSeries: vi.fn(), positionsSeriesFailed: true}));

        await waitFor(() => expect(chartRoot()).toHaveAttribute('data-state', 'failed'));
    });
});

// =============================================================================
// The legend
// =============================================================================

describe('PositionsPanel — the legend hides and shows lines without a new request', () => {
    async function mountWithAnswer() {
        const onRequestPositionsSeries = vi.fn();
        const view = await mountPanel({onRequestPositionsSeries});
        await fireEvent.click(checkbox('22-1'));
        await waitFor(() => expect(onRequestPositionsSeries).toHaveBeenCalledTimes(1));
        const props = panelProps({
            onRequestPositionsSeries,
            positionsSeries: response(
                seriesFor(22, 1, [
                    ['0', '0'],
                    ['9', '0.01'],
                    ['18', '0.02'],
                ]),
            ),
        });
        await view.rerender(props);
        await waitFor(() => expect(chartRoot()).toHaveAttribute('data-line-count', '2'));
        return {onRequestPositionsSeries};
    }

    it('hiding a position removes its line; showing it brings it back; nothing is requested', async () => {
        const {onRequestPositionsSeries} = await mountWithAnswer();

        await fireEvent.click(screen.getByTestId('positions-chart-legend-22-1'));
        await waitFor(() => expect(chartRoot()).toHaveAttribute('data-line-count', '1'));
        expect(screen.getByTestId('positions-chart-legend-22-1')).toHaveAttribute('aria-pressed', 'false');
        await waitFor(() => expect(drawnIds()).toEqual(['portfolio']));

        await fireEvent.click(screen.getByTestId('positions-chart-legend-22-1'));
        await waitFor(() => expect(chartRoot()).toHaveAttribute('data-line-count', '2'));
        expect(screen.getByTestId('positions-chart-legend-22-1')).toHaveAttribute('aria-pressed', 'true');
        await waitFor(() => expect(drawnIds()).toEqual(['22-1', 'portfolio']));

        expect(onRequestPositionsSeries).toHaveBeenCalledTimes(1);
    });

    it('the portfolio line can be hidden too', async () => {
        await mountWithAnswer();
        await fireEvent.click(screen.getByTestId('positions-chart-legend-portfolio'));

        await waitFor(() => expect(chartRoot()).toHaveAttribute('data-line-count', '1'));
        await waitFor(() => expect(drawnIds()).toEqual(['22-1']));
    });
});

// =============================================================================
// The view
// =============================================================================

describe('PositionsPanel — the chart view is kept per user', () => {
    it('the default is percentage', async () => {
        await mountPanel();
        expect(chartRoot()).toHaveAttribute('data-view', 'percentage');
        expect(screen.getByTestId('positions-chart-view-percentage')).toHaveAttribute('aria-pressed', 'true');
    });

    it('a stored absolute view is restored at mount', async () => {
        storage.set(CHART_VIEW_KEY(), 'absolute');
        await mountPanel();
        expect(chartRoot()).toHaveAttribute('data-view', 'absolute');
        expect(screen.getByTestId('positions-chart-view-absolute')).toHaveAttribute('aria-pressed', 'true');
    });

    it('choosing a view switches the chart and stores the choice under the per-user key', async () => {
        await mountPanel();
        await fireEvent.click(screen.getByTestId('positions-chart-view-absolute'));

        await waitFor(() => expect(chartRoot()).toHaveAttribute('data-view', 'absolute'));
        await waitFor(() => expect(storage.get(CHART_VIEW_KEY())).toBe('absolute'));

        await fireEvent.click(screen.getByTestId('positions-chart-view-percentage'));
        await waitFor(() => expect(chartRoot()).toHaveAttribute('data-view', 'percentage'));
        await waitFor(() => expect(storage.get(CHART_VIEW_KEY())).toBe('percentage'));
    });

    it('changing the view asks for nothing new', async () => {
        const onRequestPositionsSeries = vi.fn();
        await mountPanel({onRequestPositionsSeries});
        await fireEvent.click(checkbox('22-1'));
        await waitFor(() => expect(onRequestPositionsSeries).toHaveBeenCalledTimes(1));

        await fireEvent.click(screen.getByTestId('positions-chart-view-absolute'));
        await waitFor(() => expect(chartRoot()).toHaveAttribute('data-view', 'absolute'));
        expect(onRequestPositionsSeries).toHaveBeenCalledTimes(1);
    });
});
