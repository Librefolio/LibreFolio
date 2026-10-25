/**
 * GrowthChart's step adapter (Y5-3, D-P4 cure B): the `AggregationInputs` its pipeline has always consumed, built from a
 * report whose series are steps (`date`, `through`) instead of one point per calendar day.
 *
 * The pipeline (`growthChartData.ts`) reads `dates` and one array of values per series, aligned to them, and never assumes the
 * dates are consecutive days. So the adapter changes only what `dates` is: not every day of the range, but the **witness
 * days**, the few days on which something starts. Each array is then read from the steps by one walk (`alignAt`). The
 * aggregation, the candle ladder, the zoom and the axes are the code they have always been.
 *
 * - **The daily resolution is the steps themselves**: one date per stretch without news. Drawn with `step: 'end'`, a line
 *   holds its value to the next date, which is what the report says.
 * - **A coarser resolution or a rung of the ladder** needs a date in every bucket, or an empty week would draw as a straight
 *   line instead of a flat one. `bucketEndDays` and `rungWitnessDays` give the days to add (`extra`), and the inputs are
 *   built again with them. Above `MAX_EXTRA_WITNESS_DAYS` they give null: the chart draws the steps.
 * - **The cost is the steps, never the days of the range.** A history that starts in the year 1 has a few hundred witnesses.
 *
 * No financial quantity is computed here: a value is found in a step and handed over, as `stepSeries.ts` does.
 *
 * @module features/dashboard/growthStepInputs
 */

import {fillCounts, mapDateToBucket} from '$lib/components/charts/timeSeriesAggregation';
import type {PortfolioBrokerPnlHistoryPoint, PortfolioCostHistoryPoint, PortfolioDepositHistoryPoint, PortfolioHistoryPoint, PortfolioIncomeHistoryPoint, PortfolioAcquisitionFundingPoint, PortfolioPnlCandlePoint} from '$lib/stores/portfolio/portfolioStore.svelte';
import {addDays} from '$lib/utils/dateOnly';
import {alignAt, coveredRange, type LinePoint, type StepSpan} from '$lib/utils/stepSeries';
import {alignFlowToDates, amountOf, type AggregationInputs, type BrokerPnlSeries, type DailyCandle, type EurStackedData, type PctValues} from './growthChartData';
import {calendarPeriodOf, countSpannedPeriods, type LadderRung} from './growthLadderBuckets';

/** The most days `bucketEndDays` and `rungWitnessDays` add; above it the chart draws the steps. */
export const MAX_EXTRA_WITNESS_DAYS = 5000;

type Spanned<T> = T & StepSpan;

/** What GrowthChart is given: the report's step series, the history's MWRR line and the event series. */
export interface StepSources {
    /** The report's `range`; null falls back to what the history spans. */
    range: {start: string; end: string} | null | undefined;
    history: ReadonlyArray<Spanned<PortfolioHistoryPoint>>;
    brokerPnlHistory: ReadonlyArray<{broker_id: number; broker_name: string; points: ReadonlyArray<Spanned<PortfolioBrokerPnlHistoryPoint>>}>;
    pnlCandles: {points: ReadonlyArray<Spanned<PortfolioPnlCandlePoint>>} | null | undefined;
    mwrrLine: ReadonlyArray<LinePoint>;
    incomeHistory: {points: ReadonlyArray<PortfolioIncomeHistoryPoint>} | null | undefined;
    costHistory: {points: ReadonlyArray<PortfolioCostHistoryPoint>} | null | undefined;
    depositHistory: {points: ReadonlyArray<PortfolioDepositHistoryPoint>} | null | undefined;
    acquisitionFunding: {points: ReadonlyArray<PortfolioAcquisitionFundingPoint>} | null | undefined;
}

/** The days the report covers: its `range`, else what the history spans. */
function rangeOf(sources: StepSources): {start: string; end: string} | null {
    return sources.range ?? coveredRange(sources.history);
}

/**
 * The first day of every point; and, for a point that is not followed by the next one (a series that ends before the range
 * does, or has a hole), its last day and the day after. The line must break there and not hold the value on to the next date
 * of something else, and a bucket where the series stops keeps its last value, as it always did.
 */
function addStarts(days: Set<string>, points: ReadonlyArray<StepSpan>, rangeEnd: string | undefined): void {
    for (let index = 0; index < points.length; index += 1) {
        const point = points[index];
        days.add(point.date);
        const next = points[index + 1];
        const dayAfter = addDays(point.through, 1);
        if (next === undefined ? rangeEnd !== undefined && dayAfter <= rangeEnd : next.date > dayAfter) {
            days.add(point.through);
            days.add(dayAfter);
        }
    }
}

/**
 * The dates of the inputs, ascending and without repeats: the ends of the range, the first day of every step of every series,
 * the day after a series ends or has a hole, the days of the MWRR line, the dates of the events, and `extra`.
 */
export function witnessDays(sources: StepSources, extra: readonly string[] = []): string[] {
    const range = rangeOf(sources);
    const days = new Set<string>(extra);
    if (range) {
        days.add(range.start);
        days.add(range.end);
    }
    addStarts(days, sources.history, range?.end);
    for (const broker of sources.brokerPnlHistory) addStarts(days, broker.points, range?.end);
    addStarts(days, sources.pnlCandles?.points ?? [], range?.end);
    for (const point of sources.mwrrLine) days.add(point.date);
    for (const events of [sources.incomeHistory, sources.costHistory, sources.depositHistory, sources.acquisitionFunding]) {
        for (const point of events?.points ?? []) days.add(point.date);
    }
    return [...days].sort();
}

/** The history's three returns in percent (a fraction × 100), the MWRR read from its line on the days the line has. */
function pctValuesOf(history: StepSources['history'], mwrrLine: StepSources['mwrrLine'], dates: readonly string[]): PctValues {
    const cumulative = new Map(mwrrLine.map((point) => [point.date, point.cumulative]));
    return {
        mwrrCum: dates.map((date) => {
            const value = cumulative.get(date);
            return value != null ? Number(value) * 100 : null;
        }),
        twrr: alignAt(history, dates, (point) => (point.twrr != null ? Number(point.twrr) * 100 : null)).map((value) => value ?? null),
        roi: alignAt(history, dates, (point) => (point.roi != null ? Number(point.roi) * 100 : null)).map((value) => value ?? null),
    };
}

/** The six amounts of the Abs view, each from the step that holds the day. */
function eurValuesOf(history: StepSources['history'], dates: readonly string[]): EurStackedData {
    const read = (pick: (point: Spanned<PortfolioHistoryPoint>) => number | null): Array<number | null> => alignAt(history, dates, pick).map((value) => value ?? null);
    return {
        bookAssetLike: read((point) => amountOf(point.book_asset_like)),
        cashContributed: read((point) => amountOf(point.cash_from_contributed_capital)),
        cashGenerated: read((point) => amountOf(point.cash_from_generated_returns)),
        nav: read((point) => (point.nav_value != null ? Number(point.nav_value.amount) : null)),
        capitalBaseline: read((point) => amountOf(point.capital_baseline)),
        totalPnl: read((point) => amountOf(point.total_pnl)),
    };
}

/** The broker overlay: one line per broker, only with two brokers or more, null where the broker is not in the scope. */
function brokerSeriesOf(brokers: StepSources['brokerPnlHistory'], dates: readonly string[]): BrokerPnlSeries[] {
    if (brokers.length < 2) return [];
    return brokers.map((broker) => ({
        brokerId: broker.broker_id,
        brokerName: broker.broker_name,
        values: alignAt(broker.points, dates, (point) => amountOf(point.total_pnl)).map((value) => value ?? null),
    }));
}

/** The candle of each witness day inside a candle step; a day with none stays out of the map, a genuine gap. */
function candlesOf(pnlCandles: StepSources['pnlCandles'], dates: readonly string[]): Map<string, DailyCandle> {
    const candles = alignAt(pnlCandles?.points ?? [], dates, (point): DailyCandle => ({open: Number(point.open.amount), high: Number(point.high.amount), low: Number(point.low.amount), close: Number(point.close.amount)}));
    const byDate = new Map<string, DailyCandle>();
    candles.forEach((candle, index) => {
        if (candle) byDate.set(dates[index], candle);
    });
    return byDate;
}

/**
 * The inputs the GrowthChart pipeline consumes, built from the steps on the witness days (plus `extra`). Pass the days of
 * `bucketEndDays` or `rungWitnessDays` to build the inputs of a coarser resolution or of a rung of the ladder.
 */
export function buildAggregationInputs(sources: StepSources, extra: readonly string[] = []): AggregationInputs {
    const dates = witnessDays(sources, extra);
    return {
        dates,
        eurStackedData: eurValuesOf(sources.history, dates),
        pctValuesRaw: pctValuesOf(sources.history, sources.mwrrLine, dates),
        pnlBrokerSeriesRaw: brokerSeriesOf(sources.brokerPnlHistory, dates),
        pnlCandleByDate: candlesOf(sources.pnlCandles, dates),
        dividendValues: alignFlowToDates(dates, sources.incomeHistory?.points ?? [], (point) => Number(point.dividend.amount)),
        interestValues: alignFlowToDates(dates, sources.incomeHistory?.points ?? [], (point) => Number(point.interest.amount)),
        costValues: alignFlowToDates(dates, sources.costHistory?.points ?? [], (point) => Number(point.cost.amount)),
        depositValues: alignFlowToDates(dates, sources.depositHistory?.points ?? [], (point) => Number(point.deposit.amount)),
        acqFromNewCapitalValues: alignFlowToDates(dates, sources.acquisitionFunding?.points ?? [], (point) => Number(point.from_new_capital.amount)),
        acqFromReinvestedValues: alignFlowToDates(dates, sources.acquisitionFunding?.points ?? [], (point) => Number(point.from_reinvested.amount)),
    };
}

/**
 * The days to add for a weekly or monthly resolution: the Sunday of every ISO week, or the last day of every month, from the
 * one that holds the start of the range up to the end of the range. The chart then has a date in every bucket. Null when the
 * range has more buckets than `MAX_EXTRA_WITNESS_DAYS`.
 */
export function bucketEndDays(range: {start: string; end: string}, resolution: 'weekly' | 'monthly'): string[] | null {
    const counts = fillCounts(range.start, range.end);
    if ((resolution === 'weekly' ? counts.weeks : counts.months) > MAX_EXTRA_WITNESS_DAYS) return null;
    const ends: string[] = [];
    let end = mapDateToBucket(range.start, resolution).bucketEnd;
    while (end <= range.end) {
        ends.push(end);
        end = resolution === 'weekly' ? addDays(end, 7) : mapDateToBucket(addDays(end, 1), 'monthly').bucketEnd;
    }
    return ends;
}

/**
 * The days to add for a rung of the candle ladder: the first and the last day of every period of the rung inside the range,
 * so each period has a date at both edges (its candle opens on the first and closes on the last). Null when that would be more
 * than `MAX_EXTRA_WITNESS_DAYS` days.
 */
export function rungWitnessDays(range: {start: string; end: string}, rung: LadderRung): string[] | null {
    const periods = countSpannedPeriods(range.start, range.end, rung);
    if ((rung === '1D' ? periods : periods * 2) > MAX_EXTRA_WITNESS_DAYS) return null;
    const days: string[] = [];
    const push = (day: string) => {
        if (days[days.length - 1] !== day) days.push(day);
    };
    let period = calendarPeriodOf(range.start, rung);
    while (period.start <= range.end) {
        push(period.start < range.start ? range.start : period.start);
        push(period.end > range.end ? range.end : period.end);
        period = calendarPeriodOf(addDays(period.end, 1), rung);
    }
    return days;
}
