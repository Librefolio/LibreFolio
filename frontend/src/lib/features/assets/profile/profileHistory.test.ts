/**
 * profileHistory — the big chart of «Storia del dato» (plan 68, E6b; the mock's shot 13): the steps of one voice from
 * its first day, a point where each step starts, coloured by who gave it (a source, or written by hand), and the line
 * closed on the last day. Only the voices whose value is a number get it; a text, a choice, a map do not.
 */
import {describe, expect, it} from 'vitest';
import type {ProfileStep, ProfileVoice} from './profileStore';
import {buildHistoryOption, historyPoints, historyCharted} from './profileHistory';

function voice(shape: string, extra: Partial<ProfileVoice> = {}): ProfileVoice {
    return {key: 'yield_gross', shape, groups: ['bond'], volatile: true, ...extra} as unknown as ProfileVoice;
}

function step(date: string, through: string, value: unknown, source: string): ProfileStep {
    return {date, through, value, source, update_id: 1} as unknown as ProfileStep;
}

const STEPS = [step('2026-10-11', '2026-10-17', '0.0352', 'borsa_italiana'), step('2026-10-18', '2026-10-31', '0.0359', 'borsa_italiana'), step('2026-11-01', '2026-11-07', '0.034', 'user'), step('2026-11-08', '2026-11-19', '0.0361', 'borsa_italiana')];

describe('historyCharted', () => {
    it('charts a number, a percentage and an amount; never a text, a choice or a map', () => {
        expect(['number', 'percentage', 'amount'].map((shape) => historyCharted(voice(shape)))).toEqual([true, true, true]);
        expect(['text', 'choice', 'map', 'date', 'country', 'table'].map((shape) => historyCharted(voice(shape)))).toEqual([false, false, false, false, false, false]);
    });
});

describe('historyPoints', () => {
    it('puts a point where each step starts, with who gave it, and closes the line on the last day', () => {
        const points = historyPoints(voice('percentage'), STEPS);
        expect(points.map((point) => [point.date, point.value, point.byHand, point.marked])).toEqual([
            ['2026-10-11', 3.52, false, true],
            ['2026-10-18', 3.59, false, true],
            ['2026-11-01', 3.4, true, true],
            ['2026-11-08', 3.61, false, true],
            ['2026-11-19', 3.61, false, false],
        ]);
    });

    it('keeps the stored value of each step, for the tooltip to write it as the profile does', () => {
        const points = historyPoints(voice('percentage'), STEPS);
        expect(points.map((point) => point.stored)).toEqual(['0.0352', '0.0359', '0.034', '0.0361', '0.0361']);
    });

    it('draws an amount in the currency of the last reading: a step in another currency breaks the line (§3.7)', () => {
        const amount = voice('amount', {key: 'fund_size'});
        const points = historyPoints(amount, [step('2026-09-01', '2026-09-30', {amount: '50000000', currency: 'USD'}, 'justetf'), step('2026-10-01', '2026-10-31', {amount: '52000000', currency: 'EUR'}, 'justetf'), step('2026-11-01', '2026-11-19', {amount: '55000000', currency: 'EUR'}, 'justetf')]);
        expect(points.map((point) => point.value)).toEqual([null, 52000000, 55000000, 55000000]);
    });

    it('breaks the line over a step left empty', () => {
        const points = historyPoints(voice('number'), [step('2026-10-01', '2026-10-09', '2.1', 'user'), step('2026-10-10', '2026-10-19', null, 'user'), step('2026-10-20', '2026-10-20', '2.3', 'borsa_italiana')]);
        expect(points.map((point) => point.value)).toEqual([2.1, null, 2.3]);
    });
});

describe('buildHistoryOption', () => {
    const colors = {line: 'LINE', hand: 'HAND', axisLine: 'AXIS', axisLabel: 'LABEL', gridLine: 'GRID'};

    it('draws one stepped line in the line colour, a hand-written point in its own colour', () => {
        const option = buildHistoryOption(historyPoints(voice('percentage'), STEPS), colors) as unknown as {series: Array<{type: string; step: string; data: Array<{value: [string, number | null]; itemStyle?: {color: string}; symbolSize?: number}>; lineStyle: {color: string}}>};
        const [series] = option.series;
        expect(series.type).toBe('line');
        expect(series.step).toBe('end');
        expect(series.lineStyle.color).toBe('LINE');
        expect(series.data.map((datum) => datum.itemStyle?.color)).toEqual(['LINE', 'LINE', 'HAND', 'LINE', 'LINE']);
        expect((series.data.at(-1) as {symbol?: string}).symbol, 'the closing point draws no dot').toBe('none');
        expect((series as unknown as {symbolSize: number}).symbolSize, 'a dot on every step').toBeGreaterThan(0);
    });

    it('steps the time axis by days, and writes its labels as days', () => {
        const option = buildHistoryOption(historyPoints(voice('percentage'), STEPS), {...colors, formatDay: (iso: string) => `[${iso}]`}) as unknown as {xAxis: {minInterval: number; axisLabel: {formatter: (value: number) => string}}};
        expect(option.xAxis.minInterval).toBe(24 * 3600 * 1000);
        expect(option.xAxis.axisLabel.formatter(Date.UTC(2026, 10, 8))).toBe('[2026-11-08]');
    });
});
