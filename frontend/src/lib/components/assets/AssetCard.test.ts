// @vitest-environment jsdom
/**
 * AssetCard — the three views of a card's chart (lot Y-40, developer's decisions V-1…V-8, all (a)).
 *
 * The contract, after the cure:
 * - The card shows the view its page resolves for it (`primaryView`: the card's own saved choice, else the list's), and
 *   publishes it as `data-view-mode`: `absolute`, `percentage` or `calendar-return`. It keeps no choice of its own: the
 *   choice is saved (V-1 a), so the page owns it.
 * - Its button (`asset-card-view-toggle`) turns percent → rolling return → absolute → percent: a click asks the page for the
 *   next view (`onprimaryviewchange(assetId, next)`) and never opens the detail page. The button says where it goes
 *   (`data-next-view`).
 * - In the rolling-return view the chart draws the card's rolling return (`calendarReturn.points`, already in percent),
 *   over the comparisons' (`calendarOverlaySignals`), on the percentage axis; the other signals stay hidden (V-5 a:
 *   `renderSignals` is not asked). While it loads, a placeholder; when the backend has none (a history shorter than the
 *   window), a short line with the detail's message and its code (V-7 a), and no chart.
 * - The price and the Δ at the top stay as they are (V-6 a).
 *
 * How it is tested: the real card, real i18n; the mini chart stood in by a recorder of the props it is handed (the
 * `ChartSettingsModal.test.ts` pattern), `goto` a spy, the currency store a fixed flag (as `FxCard.test.ts`).
 *
 * Red today: the card has a two-way toggle of its own (`globalViewMode`, `localViewModeOverride`), no `primaryView`, no
 * rolling-return view. Green today, and after: a card in percent (the default of both) draws its prices from the first.
 *
 * Registered in `front_component_unit` (`scripts/test_runner/_frontend_utility.py`, action `component-unit`), next to
 * `AssetTable.test.ts`.
 */
import {beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';

const charts = vi.hoisted(() => {
    const mounts: Array<{element: HTMLElement; live: Record<string, unknown>}> = [];
    function PriceChartCompactStandIn(anchor: ChildNode, props: Record<string, unknown>): void {
        const element = document.createElement('div');
        element.setAttribute('data-testid', 'asset-card-chart');
        anchor.before(element);
        mounts.push({element, live: props});
    }
    return {mounts, PriceChartCompactStandIn};
});

vi.mock('$lib/components/charts/PriceChartCompact.svelte', () => ({default: charts.PriceChartCompactStandIn}));
const navigation = vi.hoisted(() => ({goto: vi.fn()}));
vi.mock('$app/navigation', () => navigation);
vi.mock('$lib/stores/reference/currencyStore', () => ({
    ensureCurrenciesLoaded: vi.fn(),
    getCurrencyInfo: (code: string) => ({code, flag_emoji: '🏳️'}),
}));

import type {ComponentProps} from 'svelte';
import {fireEvent, render, screen, setupI18n, within} from '$test/component';
import type {RenderedSignal} from '$lib/charts/signals';
import type {LineDataPoint} from '$lib/components/charts/LineChart.svelte';
import {DEFAULT_CHART_SETTINGS, type ChartSettings} from '$lib/stores/chartSettingsStore.svelte';
import AssetCard from './AssetCard.svelte';

type View = 'absolute' | 'percentage' | 'calendar-return';

const ASSET = {id: 42, display_name: 'Synthetic asset', currency: 'EUR', asset_type: 'STOCK', provider_code: 'mock', active: true};
const PRICES: LineDataPoint[] = [
    {date: '2026-03-02', value: 100},
    {date: '2026-03-03', value: 110},
    {date: '2026-03-04', value: 105},
];
const RETURNS: LineDataPoint[] = [
    {date: '2026-03-02', value: 4.5},
    {date: '2026-03-03', value: -1.25},
    {date: '2026-03-04', value: 2},
];
const PEER_RETURN: RenderedSignal = {id: 'cmp-9:calendar-return', label: 'Peer', data: [{date: '2026-03-03', value: 1}], color: '#f59e0b', lineWidth: 2, lineType: 'solid', markerStart: null, markerEnd: null, yAxisIndex: 0, aggregationProfile: 'last_with_range'};
const SETTINGS: ChartSettings = {
    ...(JSON.parse(JSON.stringify(DEFAULT_CHART_SETTINGS)) as ChartSettings),
    axisScales: {absolute: {mode: 'custom', min: 90, max: 120}, percentage: {mode: 'custom', min: -10, max: 10}, secondary: {}},
};

function mount(props: Record<string, unknown>) {
    const renderSignals = vi.fn((): RenderedSignal[] => []);
    const onprimaryviewchange = vi.fn();
    render(AssetCard, {asset: ASSET, chartData: PRICES, chartSettings: SETTINGS, renderSignals, onprimaryviewchange, ...props} as unknown as ComponentProps<typeof AssetCard>);
    return {card: screen.getByTestId(`asset-card-${ASSET.id}`), renderSignals, onprimaryviewchange};
}

/** What the card's one chart was handed. */
function chart(card: HTMLElement): Record<string, unknown> {
    const stands = within(card).getAllByTestId('asset-card-chart');
    expect(stands, 'the card mounts one chart').toHaveLength(1);
    const mount = charts.mounts.find((entry) => entry.element === stands[0]);
    if (!mount) throw new Error('the chart was not placed by the stand-in');
    return mount.live;
}

beforeAll(async () => {
    await setupI18n();
});

beforeEach(() => {
    charts.mounts.length = 0;
    navigation.goto.mockClear();
});

describe('AssetCard — the three views of its chart (Y-40)', () => {
    it.each(['absolute', 'percentage', 'calendar-return'] as View[])('shows the view %s its page resolves, and publishes it', (view) => {
        const {card} = mount({primaryView: view, calendarReturn: {state: 'ready', points: RETURNS}});

        expect(card).toHaveAttribute('data-view-mode', view);
    });

    it.each([
        {view: 'percentage', next: 'calendar-return'},
        {view: 'calendar-return', next: 'absolute'},
        {view: 'absolute', next: 'percentage'},
    ] as Array<{view: View; next: View}>)('its button turns $view to $next, says so, and does not open the detail', async ({view, next}) => {
        const {card, onprimaryviewchange} = mount({primaryView: view, calendarReturn: {state: 'ready', points: RETURNS}});
        const button = within(card).getByTestId('asset-card-view-toggle');
        expect(button).toHaveAttribute('data-next-view', next);

        await fireEvent.click(button);

        expect(onprimaryviewchange).toHaveBeenCalledWith(ASSET.id, next);
        expect(navigation.goto, 'the click opened the detail page').not.toHaveBeenCalled();
    });

    it('in the rolling-return view, draws the card’s rolling return over the comparisons’, on the percentage axis, and asks no other signal', () => {
        const {card, renderSignals} = mount({primaryView: 'calendar-return', calendarReturn: {state: 'ready', points: RETURNS}, calendarOverlaySignals: [PEER_RETURN]});
        const live = chart(card);

        expect({data: live.data, viewMode: live.viewMode, overlaySignals: live.overlaySignals, axisScale: live.axisScale}).toEqual({data: RETURNS, viewMode: 'percentage', overlaySignals: [PEER_RETURN], axisScale: SETTINGS.axisScales.percentage});
        expect(renderSignals, 'V-5 a: the other signals stay hidden in the rolling-return view').not.toHaveBeenCalled();
    });

    it('in the rolling-return view, shows a placeholder while it loads, and no chart', () => {
        const {card} = mount({primaryView: 'calendar-return', calendarReturn: {state: 'loading', points: []}});

        expect(within(card).getByTestId('asset-card-calendar-loading')).toBeInTheDocument();
        expect(within(card).queryByTestId('asset-card-chart')).toBeNull();
    });

    it('in the rolling-return view without a return (a history shorter than the window), says why in a short line, and draws no chart', () => {
        const {card} = mount({primaryView: 'calendar-return', calendarReturn: {state: 'unavailable', points: [], problemCode: 'insufficient_history', problemMessage: 'Not enough history'}});
        const problem = within(card).getByTestId('asset-card-calendar-problem');

        expect({state: problem.getAttribute('data-state'), code: problem.getAttribute('data-problem-code'), text: problem.textContent?.trim()}).toEqual({state: 'unavailable', code: 'insufficient_history', text: 'Not enough history'});
        expect(within(card).queryByTestId('asset-card-chart')).toBeNull();
    });

    it('guard: in percent, draws the prices measured from the first and the signals asked in percent', () => {
        const {card, renderSignals} = mount({primaryView: 'percentage'});
        const live = chart(card);

        expect((live.data as LineDataPoint[]).map((point) => Number(point.value.toFixed(6)))).toEqual([0, 10, 5]);
        expect(live.viewMode).toBe('percentage');
        // The chart reads its overlays when it draws: read them as it does.
        void live.overlaySignals;
        expect(renderSignals).toHaveBeenCalledWith(PRICES, 'percentage');
    });

    it('in absolute, draws the prices as they are, on the absolute axis', () => {
        const {card} = mount({primaryView: 'absolute'});
        const live = chart(card);

        expect({data: live.data, viewMode: live.viewMode, axisScale: live.axisScale}).toEqual({data: PRICES, viewMode: 'absolute', axisScale: SETTINGS.axisScales.absolute});
    });
});

/**
 * The settings button of a card has a test id (`asset-card-settings`), as the merge and the delete buttons have theirs: the
 * E2E of the comparison (Z-29d) opens a card's settings through it. A click asks the page for that card's settings
 * (`onsettings(asset)`) and never opens the detail page.
 *
 * Red today: the button has no test id.
 */
describe('AssetCard — its settings button (Y-41, lot 0)', () => {
    it('is found by its test id, and a click asks the page for this card’s settings without opening the detail', async () => {
        const onsettings = vi.fn();
        const {card} = mount({primaryView: 'percentage', onsettings});

        await fireEvent.click(within(card).getByTestId('asset-card-settings'));

        expect(onsettings).toHaveBeenCalledWith(expect.objectContaining({id: ASSET.id}));
        expect(navigation.goto).not.toHaveBeenCalled();
    });
});
