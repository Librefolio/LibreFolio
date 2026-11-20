/**
 * profileHistory.ts — the big chart of «Storia del dato» (plan 68, E6b; the mock's shot 13): the steps of one voice from
 * its first day, a point where each step starts, coloured by who gave it — the line's colour for a source, its own for
 * a value written by hand —, and the line closed on the last day. Only a voice whose value is a number gets a chart.
 *
 * Plain module: the option builder takes its colours from the caller, who reads them from the roles at each draw.
 */
import type {EChartsOption} from 'echarts';
import type {ProfileStep, ProfileVoice} from './profileStore';
import {chartNumber} from './profileTabState';

/** The shapes whose values the chart draws. */
const CHARTED = new Set(['number', 'percentage', 'amount']);

/** Whether «Storia del dato» draws a chart for this voice. */
export function historyCharted(voice: ProfileVoice): boolean {
    return CHARTED.has(voice.shape);
}

/** One point of the chart: where a step starts (`marked`), or where the line closes. `value` null breaks the line. */
export interface HistoryPoint {
    date: string;
    value: number | null;
    /** The step's value as stored: the tooltip writes it as the profile does (an amount with its currency). */
    stored: unknown;
    source: string;
    byHand: boolean;
    marked: boolean;
}

/** The currency of an amount as stored; null for anything else. */
function currencyOf(value: unknown): string | null {
    const currency = (value as {currency?: unknown} | null | undefined)?.currency;
    return typeof currency === 'string' ? currency : null;
}

/**
 * The points of the chart: one where each step starts, and one closing the line on the last day. An amount is drawn in
 * the currency of the last reading (plan §3.7): a step in another currency breaks the line instead of mixing two scales.
 */
export function historyPoints(voice: ProfileVoice, steps: readonly ProfileStep[]): HistoryPoint[] {
    const lastCurrency = voice.shape === 'amount' ? currencyOf([...steps].reverse().find((step) => step.value !== null && step.value !== undefined)?.value) : null;
    const points: HistoryPoint[] = steps.map((step) => {
        const otherCurrency = lastCurrency !== null && currencyOf(step.value) !== lastCurrency;
        return {date: step.date, value: otherCurrency ? null : chartNumber(voice, step.value), stored: step.value, source: step.source, byHand: step.source === 'user', marked: true};
    });
    const last = steps.at(-1);
    const closing = points.at(-1);
    if (last && closing && last.through !== last.date) points.push({...closing, date: String(last.through), marked: false});
    return points;
}

/** The colours of one draw, read from the roles by the caller, and how a day is written on the axis. */
export interface HistoryColors {
    line: string;
    hand: string;
    axisLine: string;
    axisLabel: string;
    gridLine: string;
    /** A day (`YYYY-MM-DD`) as the profile writes it; without it the axis writes ECharts' own. */
    formatDay?: (iso: string) => string;
}

const DAY_MS = 24 * 3600 * 1000;

/** The day of an axis value: ECharts reads `YYYY-MM-DD` as a local midnight, so the day is the local one. */
function dayOf(value: number): string {
    const day = new Date(value);
    return `${day.getFullYear()}-${String(day.getMonth() + 1).padStart(2, '0')}-${String(day.getDate()).padStart(2, '0')}`;
}

/** The ECharts option of the chart: one stepped line, a point per step in its source's colour, a time axis. */
export function buildHistoryOption(points: readonly HistoryPoint[], colors: HistoryColors): EChartsOption {
    return {
        grid: {left: 8, right: 16, top: 16, bottom: 8, containLabel: true},
        // Days, never hours: a profile value holds a whole day
        xAxis: {type: 'time', minInterval: DAY_MS, axisLine: {lineStyle: {color: colors.axisLine}}, axisLabel: {color: colors.axisLabel, hideOverlap: true, ...(colors.formatDay ? {formatter: (value: number) => colors.formatDay!(dayOf(value))} : {})}, splitLine: {show: false}},
        yAxis: {type: 'value', scale: true, axisLine: {show: false}, axisLabel: {color: colors.axisLabel}, splitLine: {lineStyle: {color: colors.gridLine}}},
        series: [
            {
                type: 'line',
                step: 'end',
                showSymbol: true,
                showAllSymbol: true,
                symbol: 'circle',
                symbolSize: 9,
                connectNulls: false,
                lineStyle: {color: colors.line, width: 2},
                // A dot where each step starts; the point that closes the line on the last day has none
                data: points.map((point) => ({
                    value: [point.date, point.value] as [string, number | null],
                    itemStyle: {color: point.byHand ? colors.hand : colors.line},
                    ...(point.marked ? {} : {symbol: 'none'}),
                })),
            },
        ],
    } as EChartsOption;
}
