// @vitest-environment jsdom
/**
 * LotWacPriceChart on steps (D-P4, Y5-3): the average-cost lines and the market price are one point per stretch without news, each
 * holding from its `date` to its `through`.
 *
 * The chart takes them as the points of their witness days (`lotStepRows.ts`), so its resolution cascade and its zoom run as they always did on
 * a few dates instead of one per day. What these cases pin:
 *   - the daily resolution is the steps themselves: a point on each witness day, every cost and price line drawn with `step: 'end'`;
 *   - a coarser resolution joins its buckets as it always did (no step);
 *   - the tooltip lists what each line says on the day the pointer is on, not at the drawn point nearest to it.
 *
 * ECharts is a recorder (jsdom has no canvas): it keeps every `setOption` payload and the handlers `on` was given.
 */
import {afterAll, beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';

const {chartInstances, echartsModule} = vi.hoisted(() => {
    interface FakeChart {
        setOptionCalls: Array<{option: Record<string, unknown>}>;
        handlers: Map<string, Array<(event: unknown) => void>>;
        setOption: (option: Record<string, unknown>) => void;
        getOption: () => Record<string, unknown>;
        getDom: () => unknown;
        getWidth: () => number;
        getHeight: () => number;
        on: (event: string, handler: (event: unknown) => void) => void;
        off: (event: string) => void;
        getZr: () => {on: () => void; off: () => void};
        dispatchAction: (action: unknown) => void;
        convertToPixel: (finder: unknown, value: number) => number;
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
            handlers: new Map(),
            setOption(option) {
                chart.setOptionCalls.push({option});
            },
            getOption: () => ({}),
            getDom: () => dom,
            getWidth: () => 1200,
            getHeight: () => 400,
            on: (event, handler) => {
                chart.handlers.set(event, [...(chart.handlers.get(event) ?? []), handler]);
            },
            off: (event) => {
                chart.handlers.delete(event);
            },
            getZr: () => ({on: () => {}, off: () => {}}),
            // The pointer snap moves the pointer with a second `updateAxisPointer`: ECharts hands it back to the listeners
            dispatchAction: (action) => {
                const payload = action as {type?: string; axesInfo?: unknown};
                if (payload.type === 'updateAxisPointer') for (const handler of chart.handlers.get('updateAxisPointer') ?? []) handler({axesInfo: payload.axesInfo});
            },
            convertToPixel: (_finder, value) => value / 1_000_000_000,
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
            get() {
                return vi.fn(async () => ({items: []}));
            },
        },
    ),
}));

import {render, setupI18n, waitFor} from '$test/component';
import {formatCurrencyAmountPlain} from '$lib/utils/currency/currencyFormat';
import {addDays} from '$lib/utils/dateOnly';
import LotWacPriceChart from './LotWacPriceChart.svelte';
import {valueOnDrawnLine} from './lotWacPriceChartHelpers';
import {setGlobalLineShape} from '$lib/stores/chartSettingsStore.svelte';
import {MOMENTS_ON_THE_NEWEST_DAY, MOMENTS_ON_THE_OLDEST_DAY, firePointerAt, tooltipHoldsDay} from '$test/timeAxisPointer';

const wac = (broker_id: number, date: string, through: string, value: number) => ({broker_id, date, through, wac: String(value), pool_qty: '10'});
const total = (date: string, through: string, value: number) => ({date, through, wac: String(value), pool_qty: '10'});
const price = (date: string, through: string, value: number) => ({date, through, market_price: String(value), currency: 'EUR', estimated: false});

/** Average cost 10 to 10 January, 12 from the 11th; the market price 20 to 14 January, 25 from the 15th. */
const BROKER_WAC = [wac(1, '2026-01-02', '2026-01-10', 10), wac(1, '2026-01-11', '2026-01-31', 12)];
const CUMULATIVE = [total('2026-01-02', '2026-01-10', 10), total('2026-01-11', '2026-01-31', 12)];
const MARKET = [price('2026-01-02', '2026-01-14', 20), price('2026-01-15', '2026-01-31', 25)];
const RANGE = {start: '2026-01-02', end: '2026-01-31'};

interface Drawn {
    id?: string;
    name?: string;
    type?: string;
    step?: unknown;
    data?: Array<{value?: [string | number, number | null]} | [string | number, number | null]>;
}
interface DrawnOption {
    series: Drawn[];
    tooltip: {formatter: (params: unknown) => string; axisPointer?: {snap: boolean}};
    xAxis: {axisPointer?: {snap: boolean}};
}

function lastOption(): DrawnOption | undefined {
    const call = [...(chartInstances[0]?.setOptionCalls ?? [])].reverse().find(({option}) => Array.isArray(option.series) && option.tooltip != null);
    return call?.option as unknown as DrawnOption | undefined;
}

const xOf = (datum: NonNullable<Drawn['data']>[number]): string | number => (Array.isArray(datum) ? datum[0] : (datum.value as [string | number, number | null])[0]);
const yOf = (datum: NonNullable<Drawn['data']>[number]): number | null => (Array.isArray(datum) ? datum[1] : (datum.value as [string | number, number | null])[1]);

let restoreRects: (() => void) | undefined;
beforeAll(async () => {
    await setupI18n();
    const spy = vi.spyOn(Element.prototype, 'getClientRects').mockImplementation(() => [{x: 0, y: 0, top: 0, left: 0, width: 1200, height: 400, right: 1200, bottom: 400}] as unknown as DOMRectList);
    restoreRects = () => spy.mockRestore();
});
afterAll(() => restoreRects?.());
beforeEach(() => {
    chartInstances.length = 0;
    setGlobalLineShape('steps');
});

async function mountChart(props: Record<string, unknown> = {}): Promise<DrawnOption> {
    render(LotWacPriceChart, {
        props: {brokerWacHistory: BROKER_WAC, cumulativeWacHistory: CUMULATIVE, marketPriceHistory: MARKET, range: RANGE, lotEvents: [], lots: [], brokers: [{id: 1, name: 'Broker One'}], currency: 'EUR', xAxisRange: null, ...props} as never,
    });
    await waitFor(() => expect(lastOption()?.series.some((series) => series.type === 'line')).toBe(true), {timeout: 5_000});
    return lastOption()!;
}

const lines = (option: DrawnOption): Drawn[] => option.series.filter((series) => series.type === 'line' && !(series.name ?? '').startsWith('__'));
const market = (option: DrawnOption): Drawn => lines(option).find((series) => (series.data ?? []).some((datum) => yOf(datum) === 25))!;

describe('the daily resolution is the steps', () => {
    it('draws every cost and price line with step end', async () => {
        const option = await mountChart();
        expect(lines(option).length).toBeGreaterThanOrEqual(2);
        expect(lines(option).every((series) => series.step === 'end')).toBe(true);
    });

    it('has a point on the witness days only, not a point per day', async () => {
        const option = await mountChart();
        const days = market(option).data!.map(xOf);
        expect(days.length).toBeLessThan(15);
        expect(days).toContain('2026-01-02');
        expect(days).toContain('2026-01-15');
        expect(days).toContain('2026-01-31');
        expect(days).not.toContain('2026-01-06');
    });

    it('reads the axis pointer with `snap: false`', async () => {
        const option = await mountChart();
        expect(option.xAxis.axisPointer?.snap).toBe(false);
        expect(option.tooltip.axisPointer?.snap).toBe(false);
    });
});

describe('dense steps are the weekly line they always were', () => {
    it('joins the buckets (no step) when the steps are more than the plot takes', async () => {
        // One-day steps: a plot of about 1 100 px takes 1 430 points at 1.3 a pixel, so 2 400 of them are too many.
        const first = '2020-01-01';
        const days = Array.from({length: 2_400}, (_, index) => addDays(first, index));
        const dense = {
            brokerWacHistory: days.map((day, index) => wac(1, day, day, 10 + (index % 5))),
            cumulativeWacHistory: days.map((day, index) => total(day, day, 10 + (index % 5))),
            marketPriceHistory: days.map((day, index) => price(day, day, 20 + (index % 7))),
            range: {start: first, end: days[days.length - 1]},
        };
        render(LotWacPriceChart, {props: {...dense, lotEvents: [], lots: [], brokers: [{id: 1, name: 'Broker One'}], currency: 'EUR', xAxisRange: null} as never});
        await waitFor(
            () => {
                const option = lastOption();
                expect(option?.series.some((series) => series.type === 'line' && (series.data?.length ?? 0) > 0 && (series.data?.length ?? 0) < 1_000)).toBe(true);
            },
            {timeout: 8_000},
        );
        expect(lines(lastOption()!).some((series) => series.step === 'end')).toBe(false);
    });
});

describe('an event marker beyond the daily resolution rests on the drawn line (G7, B9)', () => {
    // The dense steps of the case above: a plot takes a weekly line, one point per bucket on its last day.
    const first = '2020-01-01';
    const days = Array.from({length: 2_400}, (_, index) => addDays(first, index));
    const dense = {
        brokerWacHistory: days.map((day, index) => wac(1, day, day, 10 + (index % 5))),
        cumulativeWacHistory: days.map((day, index) => total(day, day, 10 + (index % 5))),
        // A price that swings from day to day, so the true price of a day is far from the line drawn through the week's last day.
        marketPriceHistory: days.map((day, index) => price(day, day, index % 2 === 0 ? 50 : 20)),
        range: {start: first, end: days[days.length - 1]},
    };
    // A Wednesday: inside its week, never on the day the weekly line has a point.
    const BUY_INDEX = Array.from({length: 7}, (_, offset) => 1_000 + offset).find((index) => new Date(`${days[index]}T00:00:00Z`).getUTCDay() === 3)!;
    const BUY_DAY = days[BUY_INDEX];
    const TRUE_PRICE = BUY_INDEX % 2 === 0 ? 50 : 20;
    const buy = {lot_id: 1, date: BUY_DAY, kind: 'BUY', transaction_id: 7, broker_id: 1, quantity: '10', unit_price: '20', opening_value: '200'};

    async function mountDense(lotEvents: unknown[]) {
        render(LotWacPriceChart, {props: {...dense, lotEvents, lots: [], brokers: [{id: 1, name: 'Broker One'}], currency: 'EUR', xAxisRange: null} as never});
        await waitFor(
            () => {
                const option = lastOption();
                expect(option?.series.some((series) => series.type === 'line' && (series.data?.length ?? 0) > 0 && (series.data?.length ?? 0) < 1_000)).toBe(true);
            },
            {timeout: 8_000},
        );
        return lastOption()!;
    }
    const markerOf = (option: DrawnOption) => option.series.find((series) => series.type === 'scatter' && (series.data ?? []).some((datum) => xOf(datum) === BUY_DAY))!;
    const drawnMarket = (option: DrawnOption) => lines(option).find((series) => (series.data ?? []).some((datum) => yOf(datum) === 50 || yOf(datum) === 20) && (series.data?.length ?? 0) < 1_000)!;

    it('the triangle sits on the line drawn at its date, not on the true price of the day', async () => {
        const option = await mountDense([buy]);
        const line = drawnMarket(option).data!.map((datum) => ({date: String(xOf(datum)), value: yOf(datum)}));
        const triangle = markerOf(option).data![0] as {value: [string, number]};
        expect(triangle.value[0], 'the marker keeps its true date').toBe(BUY_DAY);
        expect(
            line.some((point) => point.date === BUY_DAY),
            'precondition: the weekly line has no point on the buy day',
        ).toBe(false);
        expect(triangle.value[1]).toBeCloseTo(valueOnDrawnLine(line, BUY_DAY) as number, 9);
        expect(Math.abs(triangle.value[1] - TRUE_PRICE), 'the true price of the day is off the drawn line').toBeGreaterThan(1);
    });

    it('its tooltip keeps the true date and price of the event', async () => {
        const option = await mountDense([buy]);
        const triangle = markerOf(option).data![0] as {meta: {date: string; event: {unit_price: string}}};
        expect(triangle.meta.date).toBe(BUY_DAY);
        expect(triangle.meta.event.unit_price).toBe('20');
    });
});

describe('the tooltip of a step line', () => {
    function pointAt(day: string): void {
        const [year, month, date] = day.split('-').map(Number);
        const handlers = chartInstances[0].handlers.get('updateAxisPointer') ?? [];
        expect(handlers.length, 'the chart listens to the axis pointer').toBeGreaterThan(0);
        for (const handler of handlers) handler({axesInfo: [{value: new Date(year, month - 1, date).getTime()}]});
    }
    const money = (amount: number) => formatCurrencyAmountPlain(amount, 'EUR', {sensitivity: 'public'});

    function nearestParam(option: DrawnOption, series: Drawn, day: string): Record<string, unknown> {
        const index = series.data!.findIndex((datum) => xOf(datum) === day);
        const datum = series.data![index];
        return {seriesType: 'line', seriesId: series.id, seriesIndex: option.series.indexOf(series), seriesName: series.name, dataIndex: index, data: datum, value: Array.isArray(datum) ? datum : datum.value, axisValue: Date.parse(day), color: '#123456'};
    }

    it('lists what the line says on the pointed day, not at the drawn point nearest to it', async () => {
        const option = await mountChart();
        const line = market(option);
        // 14 January, the last day of the 20 step: the nearest drawn point is the 15th (25), the line says 20.
        pointAt('2026-01-14');
        const html = option.tooltip.formatter([nearestParam(option, line, '2026-01-15')]);
        expect(html).toContain(money(20));
        expect(html).not.toContain(money(25));
    });

    it('lists the nearest drawn point when nothing was pointed', async () => {
        const option = await mountChart();
        const html = option.tooltip.formatter([nearestParam(option, market(option), '2026-01-15')]);
        expect(html).toContain(money(25));
    });

    it.each(MOMENTS_ON_THE_NEWEST_DAY)('opens on the newest day with the pointer at its $label', async (moment) => {
        const option = await mountChart();
        // 31 January is the last day of the range; the point ECharts hands over is the first one, the 2nd.
        firePointerAt(chartInstances[0].handlers.get('updateAxisPointer') ?? [], '2026-01-31', moment);
        const html = option.tooltip.formatter([nearestParam(option, market(option), '2026-01-02')]);
        expect(tooltipHoldsDay(html, '2026-01-31')).toBe(true);
        expect(html).toContain(money(25));
    });

    it.each(MOMENTS_ON_THE_OLDEST_DAY)('opens on the oldest day shown with the pointer at its $label', async (moment) => {
        const option = await mountChart();
        firePointerAt(chartInstances[0].handlers.get('updateAxisPointer') ?? [], '2026-01-02', moment);
        const html = option.tooltip.formatter([nearestParam(option, market(option), '2026-01-31')]);
        expect(tooltipHoldsDay(html, '2026-01-02')).toBe(true);
        expect(html).toContain(money(20));
    });
});

describe('the line shape the user chose (Y2 FB-3)', () => {
    it('joins the points by segments when the choice is segments', async () => {
        setGlobalLineShape('segments');
        const option = await mountChart();
        expect(lines(option).length).toBeGreaterThanOrEqual(2);
        expect(lines(option).every((series) => series.step === false)).toBe(true);
    });

    it('draws smooth lines when the choice is spline', async () => {
        setGlobalLineShape('spline');
        const option = await mountChart();
        expect(lines(option).every((series) => series.step === false && (series as {smooth?: boolean}).smooth === true)).toBe(true);
    });
});
