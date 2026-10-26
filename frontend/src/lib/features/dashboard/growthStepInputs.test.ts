/**
 * The step adapter of GrowthChart (Y5-3, D-P4 cure B): from a report whose series are steps (`date`, `through`), the same
 * `AggregationInputs` the chart's pipeline has always consumed, with a few dates instead of one per day.
 *
 * The contract these cases pin, in order of importance:
 *   1. PARITY. The old pipeline on the day-by-day series and the new one on its steps draw the same buckets with the same
 *      values, at every resolution above the daily one and on every rung of the candle ladder. The expected side of each
 *      case is the OLD code on the expanded days, never a literal derived from the new one.
 *   2. The daily resolution is the steps themselves: one date per stretch without news, whatever the length of the range.
 *   3. A date typed in the year 1 costs the steps, not the 740 000 days.
 */
import {describe, expect, it} from 'vitest';
import {alignFlowToDates, amountOf, buildLadderData, buildResolutionData, type AggregatedMetric, type AggregatedResolutionData, type AggregationInputs, type BrokerPnlSeries, type DailyCandle, type EurStackedData, type PctValues} from './growthChartData';
import {bucketEndDays, buildAggregationInputs, MAX_EXTRA_WITNESS_DAYS, rungWitnessDays, witnessDays, type StepSources} from './growthStepInputs';
import type {LadderRung} from './growthLadderBuckets';
import type {LinePoint} from '$lib/utils/stepSeries';
import {dailyFromSteps} from '$lib/utils/__tests__/stepSeriesTestKit';

// ---------------------------------------------------------------------------------------------------------------------------
// THE OLD MAPPERS, frozen. They read a history with one point per calendar day, as `GrowthChart` did before the report gave
// steps (`growthChartData.ts` held them until Y5-3). They are the expected side of the parity cases: the old pipeline on the
// expanded days. Do not change them to agree with the adapter.
// ---------------------------------------------------------------------------------------------------------------------------
type DayHistoryPoint = Record<string, any>;

function oldEurStackedData(history: DayHistoryPoint[]): EurStackedData {
    return {
        bookAssetLike: history.map((pt) => amountOf(pt.book_asset_like)),
        cashContributed: history.map((pt) => amountOf(pt.cash_from_contributed_capital)),
        cashGenerated: history.map((pt) => amountOf(pt.cash_from_generated_returns)),
        nav: history.map((pt) => (pt.nav_value != null ? Number(pt.nav_value.amount) : null)),
        capitalBaseline: history.map((pt) => amountOf(pt.capital_baseline)),
        totalPnl: history.map((pt) => amountOf(pt.total_pnl)),
    };
}

function oldPctValues(history: DayHistoryPoint[]): PctValues {
    return {
        mwrrCum: history.map((pt) => (pt.mwrr_cumulative != null ? Number(pt.mwrr_cumulative) * 100 : null)),
        twrr: history.map((pt) => (pt.twrr != null ? Number(pt.twrr) * 100 : null)),
        roi: history.map((pt) => (pt.roi != null ? Number(pt.roi) * 100 : null)),
    };
}

function oldBrokerPnlSeries(brokers: Array<{broker_id: number; broker_name: string; points: DayHistoryPoint[]}>, dates: string[]): BrokerPnlSeries[] {
    return brokers.length >= 2
        ? brokers.map((broker) => {
              const byDate = new Map(broker.points.map((p) => [p.date, amountOf(p.total_pnl)]));
              return {brokerId: broker.broker_id, brokerName: broker.broker_name, values: dates.map((d) => byDate.get(d) ?? null)};
          })
        : [];
}

function oldCandlesByDate(points: DayHistoryPoint[]): Map<string, DailyCandle> {
    return new Map(points.map((p) => [p.date, {open: Number(p.open.amount), high: Number(p.high.amount), low: Number(p.low.amount), close: Number(p.close.amount)}]));
}

const money = (amount: number) => ({code: 'EUR', amount: amount.toFixed(2)});
const RANGE = {start: '2026-01-01', end: '2026-04-30'};

/** One history step: every amount a function of `k`, so two steps with the same `k` are the same step. */
function historyStep(date: string, through: string, k: number) {
    return {
        date,
        through,
        cash_value: money(k * 3),
        market_value: money(k * 7),
        nav_value: money(1000 + k * 10),
        capital_baseline: money(1000),
        book_asset_like: money(k * 5),
        cash_from_contributed_capital: money(k * 2),
        cash_from_generated_returns: money(k),
        total_pnl: money(k * 5),
        twrr: (k / 100).toFixed(6),
        roi: (k / 200).toFixed(6),
    };
}

const HISTORY = [historyStep('2026-01-01', '2026-01-09', 1), historyStep('2026-01-10', '2026-01-10', 2), historyStep('2026-01-11', '2026-02-19', 3), historyStep('2026-02-20', '2026-02-20', 4), historyStep('2026-02-21', '2026-03-31', 5), historyStep('2026-04-01', '2026-04-30', 6)];

/** Broker A lives the whole range; broker B joins on 1 February and leaves on 10 March. */
const BROKERS = [
    {
        broker_id: 1,
        broker_name: 'A',
        points: [
            {date: '2026-01-01', through: '2026-02-20', total_pnl: money(3)},
            {date: '2026-02-21', through: '2026-04-30', total_pnl: money(6)},
        ],
    },
    {broker_id: 2, broker_name: 'B', points: [{date: '2026-02-01', through: '2026-03-10', total_pnl: money(4)}]},
];

const candle = (base: number) => ({open: money(base), high: money(base + 5), low: money(base - 5), close: money(base + 2)});

/** Candle steps with a hole from 2 to 10 March: a valuation was missing, a genuine gap. */
const CANDLES = {
    hypothetical: false,
    points: [
        {date: '2026-01-01', through: '2026-01-14', ...candle(10)},
        {date: '2026-01-15', through: '2026-01-15', ...candle(20)},
        {date: '2026-01-16', through: '2026-03-01', ...candle(30)},
        {date: '2026-03-11', through: '2026-04-30', ...candle(40)},
    ],
};

const INCOME = {
    points: [
        {date: '2026-01-20', dividend: money(12), interest: money(0)},
        {date: '2026-03-05', dividend: money(0), interest: money(3)},
    ],
    missing_fx_pairs: [],
};
const COSTS = {points: [{date: '2026-02-10', cost: money(-4)}], missing_fx_pairs: []};
const DEPOSITS = {points: [{date: '2026-01-01', deposit: money(1000)}], missing_fx_pairs: []};
const FUNDING = {points: [{date: '2026-02-21', from_new_capital: money(50), from_reinvested: money(25)}]};

/** The history's MWRR: true values on a few days only, as the report gives them (the ends of the steps, a point a month inside the long ones). */
const MWRR_LINE: LinePoint[] = [
    {date: '2026-01-01', annualized: null, cumulative: null},
    {date: '2026-02-15', annualized: '0.05', cumulative: '0.004500'},
    {date: '2026-02-20', annualized: '0.06', cumulative: '0.005100'},
    {date: '2026-03-20', annualized: '0.07', cumulative: '0.007700'},
    {date: '2026-04-30', annualized: '0.08', cumulative: '0.011100'},
];

function sources(over: Partial<StepSources> = {}): StepSources {
    return {
        range: RANGE,
        history: HISTORY,
        brokerPnlHistory: BROKERS,
        pnlCandles: CANDLES,
        mwrrLine: MWRR_LINE,
        incomeHistory: INCOME,
        costHistory: COSTS,
        depositHistory: DEPOSITS,
        acquisitionFunding: FUNDING,
        ...over,
    } as StepSources;
}

/** The inputs of the old pipeline: every day of the range, as the report used to give it. */
function dailyInputs(): AggregationInputs {
    const mwrr = new Map(MWRR_LINE.map((point) => [point.date, point.cumulative]));
    const history = dailyFromSteps(HISTORY).map((point) => ({...point, mwrr_cumulative: mwrr.get(point.date) ?? null}));
    const dates = history.map((point) => point.date);
    const brokerHistory = BROKERS.map((broker) => ({...broker, points: dailyFromSteps(broker.points)}));
    return {
        dates,
        eurStackedData: oldEurStackedData(history),
        pctValuesRaw: oldPctValues(history),
        pnlBrokerSeriesRaw: oldBrokerPnlSeries(brokerHistory, dates),
        pnlCandleByDate: oldCandlesByDate(dailyFromSteps(CANDLES.points)),
        dividendValues: alignFlowToDates(dates, INCOME.points, (p) => Number(p.dividend.amount)),
        interestValues: alignFlowToDates(dates, INCOME.points, (p) => Number(p.interest.amount)),
        costValues: alignFlowToDates(dates, COSTS.points, (p) => Number(p.cost.amount)),
        depositValues: alignFlowToDates(dates, DEPOSITS.points, (p) => Number(p.deposit.amount)),
        acqFromNewCapitalValues: alignFlowToDates(dates, FUNDING.points, (p) => Number(p.from_new_capital.amount)),
        acqFromReinvestedValues: alignFlowToDates(dates, FUNDING.points, (p) => Number(p.from_reinvested.amount)),
    };
}

const valuesOf = (metric: AggregatedMetric) => metric.values;

/** What a chart reads of an entry, minus the indices into the dates (which differ: the new dates are few). */
function drawn(entry: AggregatedResolutionData, withCandles: boolean) {
    return {
        resolution: entry.resolution,
        dates: entry.dates,
        buckets: entry.buckets.map(({date, bucketStart, bucketEnd, resolution, period, partial, current}) => ({date, bucketStart, bucketEnd, resolution, period, partial, current})),
        eur: Object.fromEntries(Object.entries(entry.eur).map(([key, metric]) => [key, valuesOf(metric)])),
        pct: Object.fromEntries(Object.entries(entry.pct).map(([key, metric]) => [key, valuesOf(metric)])),
        pnl: {
            total: valuesOf(entry.pnl.total),
            brokers: entry.pnl.brokers.map((broker) => ({id: broker.brokerId, values: valuesOf(broker.metric)})),
            income: [valuesOf(entry.pnl.income.dividend), valuesOf(entry.pnl.income.interest)],
            costs: valuesOf(entry.pnl.costs),
            deposits: valuesOf(entry.pnl.deposits),
            acquisition: [valuesOf(entry.pnl.acquisition.fromNewCapital), valuesOf(entry.pnl.acquisition.fromReinvested)],
            ...(withCandles ? {candles: entry.pnl.candle.points.map(({open, high, low, close}) => ({open, high, low, close}))} : {}),
        },
    };
}

describe('witnessDays', () => {
    it('is the first day of every step, the day after a hole, the ends of the range and the dates of the events', () => {
        const days = witnessDays(sources());
        expect(days).toEqual([...days].sort());
        expect(new Set(days).size).toBe(days.length);
        for (const day of ['2026-01-01', '2026-01-10', '2026-01-11', '2026-02-20', '2026-02-21', '2026-04-01', '2026-04-30']) expect(days).toContain(day);
        // broker B leaves after 10 March: its last day is a witness (a bucket keeps its last value) and its line breaks on the 11th
        expect(days).toContain('2026-03-10');
        expect(days).toContain('2026-03-11');
        // the candle hole starts on 2 March, the day after the step that ended on 1 March
        expect(days).toContain('2026-03-01');
        expect(days).toContain('2026-03-02');
        // the events
        for (const day of ['2026-01-20', '2026-03-05', '2026-02-10']) expect(days).toContain(day);
        // the days of the history's MWRR line, which fall inside a long step
        expect(days).toContain('2026-02-15');
        expect(days).not.toContain('2026-02-14');
    });

    it('adds the extra days it is given, once, in order', () => {
        const days = witnessDays(sources({mwrrLine: []}), ['2026-01-04', '2026-01-10']);
        expect(days).toContain('2026-01-04');
        expect(days.filter((day) => day === '2026-01-10')).toHaveLength(1);
        expect(days).toEqual([...days].sort());
    });

    it('keeps the days of the range only: a series or an event dated outside it adds no date', () => {
        const days = witnessDays(sources({range: {start: '2026-02-01', end: '2026-03-01'}}));
        expect(days[0]).toBe('2026-02-01');
        expect(days[days.length - 1]).toBe('2026-03-01');
        expect(days.every((day) => day >= '2026-02-01' && day <= '2026-03-01')).toBe(true);
    });

    it('takes the range from the history when the report gives none', () => {
        const days = witnessDays(sources({range: null, mwrrLine: []}));
        expect(days[0]).toBe('2026-01-01');
        expect(days[days.length - 1]).toBe('2026-04-30');
    });

    it('is empty for no history and no range', () => {
        expect(witnessDays({range: null, history: [], brokerPnlHistory: [], pnlCandles: null, mwrrLine: [], incomeHistory: null, costHistory: null, depositHistory: null, acquisitionFunding: null})).toEqual([]);
    });
});

describe('buildAggregationInputs: the daily resolution is the steps', () => {
    it('has one value per witness date, equal to the value the step holds that day', () => {
        const inputs = buildAggregationInputs(sources({mwrrLine: []}));
        expect(inputs.dates.length).toBeLessThan(40);
        const at = (day: string) => inputs.dates.indexOf(day);
        expect(inputs.eurStackedData.nav[at('2026-01-01')]).toBe(1010);
        expect(inputs.eurStackedData.nav[at('2026-01-11')]).toBe(1030);
        expect(inputs.eurStackedData.nav[at('2026-04-30')]).toBe(1060);
        expect(inputs.pctValuesRaw.twrr[at('2026-02-20')]).toBeCloseTo(4, 9);
        expect(inputs.pctValuesRaw.roi[at('2026-02-20')]).toBeCloseTo(2, 9);
    });

    it('breaks a broker line where the broker is not there, and starts it where it joins', () => {
        const inputs = buildAggregationInputs(sources({mwrrLine: []}));
        const brokerB = inputs.pnlBrokerSeriesRaw.find((broker) => broker.brokerId === 2)!;
        const at = (day: string) => inputs.dates.indexOf(day);
        expect(brokerB.values[at('2026-01-01')]).toBeNull();
        expect(brokerB.values[at('2026-02-01')]).toBe(4);
        expect(brokerB.values[at('2026-03-11')]).toBeNull();
    });

    it("leaves a candle gap a gap, and gives every witness day inside a candle step that step's candle", () => {
        const inputs = buildAggregationInputs(sources({mwrrLine: []}));
        expect(inputs.pnlCandleByDate.has('2026-03-02')).toBe(false);
        expect(inputs.pnlCandleByDate.get('2026-01-11')).toEqual({open: 10, high: 15, low: 5, close: 12});
    });

    it('puts the MWRR only on the days of its line, as a percent, and nowhere else', () => {
        const line: LinePoint[] = [
            {date: '2026-01-01', annualized: null, cumulative: null},
            {date: '2026-02-20', annualized: '0.1', cumulative: '0.0123'},
        ];
        const inputs = buildAggregationInputs(sources({mwrrLine: line}));
        const at = (day: string) => inputs.dates.indexOf(day);
        expect(inputs.pctValuesRaw.mwrrCum[at('2026-01-01')]).toBeNull();
        expect(inputs.pctValuesRaw.mwrrCum[at('2026-02-20')]).toBeCloseTo(1.23, 9);
        expect(inputs.pctValuesRaw.mwrrCum[at('2026-02-21')]).toBeNull();
    });

    it('gives the broker overlay only with two brokers or more, as the old pipeline did', () => {
        expect(buildAggregationInputs(sources({brokerPnlHistory: [BROKERS[0]]})).pnlBrokerSeriesRaw).toEqual([]);
    });
});

describe('PARITY with the old pipeline on the expanded days', () => {
    const OLD = dailyInputs();

    it.each(['weekly', 'monthly'] as const)('%s resolution: the same buckets and the same values', (resolution) => {
        const extra = bucketEndDays(RANGE, resolution);
        expect(extra).not.toBeNull();
        const fresh = buildResolutionData(buildAggregationInputs(sources(), extra ?? []), resolution);
        expect(drawn(fresh, false)).toEqual(drawn(buildResolutionData(OLD, resolution), false));
    });

    it.each(['1D', '3D', '1W', '2W', '1M', '3M', '6M', '1Y'] as LadderRung[])('rung %s of the candle ladder: the same buckets, sums and candles', (rung) => {
        const extra = rungWitnessDays(RANGE, rung);
        expect(extra).not.toBeNull();
        const fresh = buildLadderData(buildAggregationInputs(sources(), extra ?? []), rung, '2026-04-30');
        const old = buildLadderData(OLD, rung, '2026-04-30');
        expect(drawn(fresh, true)).toEqual(drawn(old, true));
    });
});

describe('the extra days of a resolution and of a rung', () => {
    it('bucketEndDays: the Sunday of every ISO week, or the last day of every month, that the range touches', () => {
        expect(bucketEndDays({start: '2026-01-01', end: '2026-01-25'}, 'weekly')).toEqual(['2026-01-04', '2026-01-11', '2026-01-18', '2026-01-25']);
        expect(bucketEndDays({start: '2026-01-15', end: '2026-03-10'}, 'monthly')).toEqual(['2026-01-31', '2026-02-28']);
    });

    it('rungWitnessDays: the first and the last day of every period of the rung inside the range', () => {
        expect(rungWitnessDays({start: '2026-01-15', end: '2026-03-10'}, '1M')).toEqual(['2026-01-15', '2026-01-31', '2026-02-01', '2026-02-28', '2026-03-01', '2026-03-10']);
        expect(rungWitnessDays({start: '2026-05-06', end: '2026-05-08'}, '1D')).toEqual(['2026-05-06', '2026-05-07', '2026-05-08']);
    });

    it('refuse (null) above the cap, so a range of 2 000 years never makes 100 000 buckets', () => {
        const typo = {start: '0001-01-01', end: '2026-10-25'};
        expect(bucketEndDays(typo, 'weekly')).toBeNull();
        expect(rungWitnessDays(typo, '1D')).toBeNull();
        expect(rungWitnessDays(typo, '1W')).toBeNull();
        expect(bucketEndDays(typo, 'monthly')).toBeNull();
        expect(rungWitnessDays(typo, '1Y')).not.toBeNull();
        expect((rungWitnessDays(typo, '1Y') ?? []).length).toBeLessThanOrEqual(MAX_EXTRA_WITNESS_DAYS);
    });

    it('reads a year before 1000 as it is written', () => {
        expect(bucketEndDays({start: '0024-03-01', end: '0024-03-20'}, 'weekly')).toEqual(['0024-03-03', '0024-03-10', '0024-03-17']);
    });
});

describe('a date typed in the year 1', () => {
    const typo = {
        range: {start: '0001-01-01', end: '2026-04-30'},
        history: [{...historyStep('0001-01-01', '0001-01-01', 0)}, {...historyStep('0001-01-02', '2025-12-31', 1)}, ...HISTORY],
        brokerPnlHistory: [],
        pnlCandles: null,
        mwrrLine: [],
        incomeHistory: null,
        costHistory: null,
        depositHistory: null,
        acquisitionFunding: null,
    } as unknown as StepSources;

    it('builds the inputs from the steps: a handful of dates, in a few milliseconds', () => {
        const started = performance.now();
        const inputs = buildAggregationInputs(typo);
        expect(inputs.dates.length).toBeLessThan(40);
        expect(inputs.dates[0]).toBe('0001-01-01');
        expect(inputs.dates[inputs.dates.length - 1]).toBe('2026-04-30');
        expect(inputs.eurStackedData.nav[1]).toBe(1010);
        expect(performance.now() - started).toBeLessThan(200);
    });

    it('draws the daily resolution of that history without a bucket per day', () => {
        const entry = buildResolutionData(buildAggregationInputs(typo), 'daily');
        expect(entry.dates.length).toBeLessThan(40);
    });
});
