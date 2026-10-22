// @vitest-environment jsdom
/**
 * FxCard — the three views of a card's chart (lot Y-40, the FX half; decisions V-1…V-9, all (a)), as `AssetCard.test.ts`
 * pins them for the asset cards.
 *
 * The contract, after the cure:
 * - The card shows the view its page resolves for it (`primaryView`: the pair's saved choice, else the FX list's) and
 *   publishes it as `data-view-mode`. It keeps no choice of its own (V-1 a).
 * - Its button (`fx-card-view-toggle`) turns percent → rolling return → absolute → percent: a click asks the page for the
 *   next view (`onprimaryviewchange(slug, next)`), says where it goes (`data-next-view`) and never opens the detail page.
 * - In the rolling-return view the chart draws the pair's rolling return (`calendarReturn.points`, in percent) over the
 *   compared pairs' (`calendarOverlaySignals`), on the percentage axis; the other signals stay hidden (V-5 a). A placeholder
 *   while it loads; the detail's message, and no chart, when the backend has none.
 * - In the price views the rates are drawn the way the card shows the pair, each point converted once, through the shared
 *   `fxPointToLineDataPoint` (X's request: the card converted every point twice, for the chart and for its signals).
 *
 * How it is tested: the real card, real i18n; the mini chart stood in by a recorder of the props it is handed, `goto` a
 * spy, the currency store a fixed flag (as `FxCard.test.ts`).
 *
 * Red today: a two-way toggle of its own (`globalViewMode`), no `primaryView`, no rolling-return view.
 *
 * Registered in `front_component_unit` (`scripts/test_runner/_frontend_utility.py`, action `component-unit`), next to
 * `FxCard.test.ts`.
 */
import {afterEach, beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';

const charts = vi.hoisted(() => {
    const mounts: Array<{element: HTMLElement; live: Record<string, unknown>}> = [];
    function PriceChartCompactStandIn(anchor: ChildNode, props: Record<string, unknown>): void {
        const element = document.createElement('div');
        element.setAttribute('data-testid', 'fx-card-chart');
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
import {fxPointToLineDataPoint} from '$lib/charts/chartSignalRendering';
import type {RenderedSignal} from '$lib/charts/signals';
import type {LineDataPoint} from '$lib/components/charts/LineChart.svelte';
import {DEFAULT_CHART_SETTINGS, type ChartSettings} from '$lib/stores/chartSettingsStore.svelte';
import {clearCardInversions, setCardInverted} from '$lib/stores/fx/fxCardInversionStore';
import type {FxDataPoint} from '$lib/stores/fxStoreRegistry';
import FxCard from './FxCard.svelte';

type View = 'absolute' | 'percentage' | 'calendar-return';

const SLUG = 'EUR-USD';
const RATES: FxDataPoint[] = [
    {date: '2026-03-02', rate: 1.25, backwardFillInfo: null},
    {date: '2026-03-03', rate: 1.5, backwardFillInfo: {actualRateDate: '2026-03-02', daysBack: 1}},
    {date: '2026-03-04', rate: null, backwardFillInfo: null},
] as FxDataPoint[];
const RETURNS: LineDataPoint[] = [
    {date: '2026-03-02', value: 0.75},
    {date: '2026-03-03', value: -1.5},
];
const PEER_RETURN: RenderedSignal = {id: 'fx-gbp:calendar-return', label: 'EUR → GBP', data: [{date: '2026-03-03', value: 0.25}], color: '#10b981', lineWidth: 2, lineType: 'solid', markerStart: null, markerEnd: null, yAxisIndex: 0, aggregationProfile: 'last_with_range'};
const SETTINGS: ChartSettings = {
    ...(JSON.parse(JSON.stringify(DEFAULT_CHART_SETTINGS)) as ChartSettings),
    axisScales: {absolute: {mode: 'custom', min: 1, max: 2}, percentage: {mode: 'custom', min: -10, max: 10}, secondary: {}},
};

function mount(props: Record<string, unknown>) {
    const renderSignals = vi.fn((): RenderedSignal[] => []);
    const onprimaryviewchange = vi.fn();
    render(FxCard, {base: 'EUR', quote: 'USD', slug: SLUG, data: RATES, chartSettings: SETTINGS, renderSignals, onprimaryviewchange, ...props} as unknown as ComponentProps<typeof FxCard>);
    return {card: screen.getByTestId(`fx-card-${SLUG}`), renderSignals, onprimaryviewchange};
}

function chart(card: HTMLElement): Record<string, unknown> {
    const stands = within(card).getAllByTestId('fx-card-chart');
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

afterEach(() => {
    clearCardInversions();
});

describe('FxCard — the three views of its chart (Y-40, FX)', () => {
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
        const button = within(card).getByTestId('fx-card-view-toggle');
        expect(button).toHaveAttribute('data-next-view', next);

        await fireEvent.click(button);

        expect(onprimaryviewchange).toHaveBeenCalledWith(SLUG, next);
        expect(navigation.goto).not.toHaveBeenCalled();
    });

    it('in the rolling-return view, draws the pair’s rolling return over the compared pairs’, on the percentage axis, and asks no other signal', () => {
        const {card, renderSignals} = mount({primaryView: 'calendar-return', calendarReturn: {state: 'ready', points: RETURNS}, calendarOverlaySignals: [PEER_RETURN]});
        const live = chart(card);

        expect({data: live.data, viewMode: live.viewMode, overlaySignals: live.overlaySignals, axisScale: live.axisScale}).toEqual({data: RETURNS, viewMode: 'percentage', overlaySignals: [PEER_RETURN], axisScale: SETTINGS.axisScales.percentage});
        expect(renderSignals).not.toHaveBeenCalled();
    });

    it('in the rolling-return view, a placeholder while it loads, and the detail’s message without a return; no chart', () => {
        const {card} = mount({primaryView: 'calendar-return', calendarReturn: {state: 'loading', points: []}});
        expect(within(card).getByTestId('fx-card-calendar-loading')).toBeInTheDocument();
        expect(within(card).queryByTestId('fx-card-chart')).toBeNull();
    });

    it('in the rolling-return view without a return, says why in a short line, and draws no chart', () => {
        const {card} = mount({primaryView: 'calendar-return', calendarReturn: {state: 'unavailable', points: [], problemCode: 'insufficient_history', problemMessage: 'Not enough history'}});
        const problem = within(card).getByTestId('fx-card-calendar-problem');

        expect({state: problem.getAttribute('data-state'), code: problem.getAttribute('data-problem-code'), text: problem.textContent?.trim()}).toEqual({state: 'unavailable', code: 'insufficient_history', text: 'Not enough history'});
        expect(within(card).queryByTestId('fx-card-chart')).toBeNull();
    });

    it('in absolute, draws each rate converted once by the shared fxPointToLineDataPoint, and hands the same points to its signals', () => {
        const {card, renderSignals} = mount({primaryView: 'absolute'});
        const live = chart(card);
        void live.overlaySignals;

        const expected = RATES.map((point) => fxPointToLineDataPoint(point, false));
        expect({data: live.data, axisScale: live.axisScale}).toEqual({data: expected, axisScale: SETTINGS.axisScales.absolute});
        expect(renderSignals).toHaveBeenCalledWith(expected, 'absolute');
    });

    it('swapped, draws the reciprocals the same way', () => {
        setCardInverted(SLUG, true);
        const {card} = mount({primaryView: 'absolute'});

        expect(chart(card).data).toEqual(RATES.map((point) => fxPointToLineDataPoint(point, true)));
    });
});
