/**
 * `paramsAtDay` — the tooltip of step lines restated on the day the pointer is on (D-P4, Y5-3).
 *
 * On a time axis ECharts gives every series the data point NEAREST to the pointer, so in the right half of a step a line would show the
 * next step's value. The lot charts build their tooltips from those params; `paramsAtDay` rewrites each param to the point of its own
 * series that holds the pointed day (the last one on or before it), with the day as its axis value, so the builders read what the line says.
 * A series that does not exist that day (before its first point, after its last) loses its param.
 */
import {describe, expect, it} from 'vitest';
import {paramsAtDay, type StepParam} from '../stepTooltip';

const point = (date: string, value: number | null) => ({name: date, value: [date, value] as [string, number | null]});

/** A: 100 from 2 January, -50 from 11 January, closing point on 31 January. B: 10 from 11 January to 25 January. */
const SERIES = [
    {id: 'a', data: [point('2026-01-02', 100), point('2026-01-11', -50), point('2026-01-31', -50)]},
    {id: 'b', data: [point('2026-01-11', 10), point('2026-01-25', 10)]},
    {id: 'dots', data: [{value: [Date.UTC(2026, 0, 5), 3]}]},
];

/** What ECharts hands over: for each series, its point nearest to the pointer. */
const nearest = (seriesId: string, index: number): StepParam => {
    const series = SERIES.find((entry) => entry.id === seriesId)!;
    const datum = series.data[index] as {value: unknown};
    return {seriesId, seriesIndex: SERIES.indexOf(series), dataIndex: index, data: datum, value: datum.value, axisValue: 0, seriesName: seriesId};
};

describe('paramsAtDay', () => {
    it('rewrites each param to the point of its series holding the day, with the day as its axis value', () => {
        // 9 January: ECharts says A's second point (11 January) and B's first.
        const out = paramsAtDay([nearest('a', 1), nearest('b', 0)], '2026-01-09', SERIES);
        expect(out.map((param) => [param.seriesId, param.dataIndex, (param.value as [string, number])[1], param.axisValue])).toEqual([['a', 0, 100, '2026-01-09']]);
    });

    it('drops a series that does not exist that day, before its first point and after its last', () => {
        expect(paramsAtDay([nearest('a', 0), nearest('b', 0)], '2026-01-05', SERIES).map((param) => param.seriesId)).toEqual(['a']);
        expect(paramsAtDay([nearest('a', 2), nearest('b', 1)], '2026-01-28', SERIES).map((param) => param.seriesId)).toEqual(['a']);
    });

    it('reads the last point on or before the day', () => {
        const out = paramsAtDay([nearest('a', 0), nearest('b', 0)], '2026-01-11', SERIES);
        expect(out.map((param) => [param.seriesId, (param.value as [string, number])[1]])).toEqual([
            ['a', -50],
            ['b', 10],
        ]);
    });

    it('keeps a param whose series it cannot read as it is (an internal series with another shape)', () => {
        const dots: StepParam = {seriesId: 'dots', seriesIndex: 2, dataIndex: 0, data: SERIES[2].data[0], value: SERIES[2].data[0].value, axisValue: 5};
        expect(paramsAtDay([dots], '2026-01-09', SERIES)).toEqual([dots]);
    });

    it('keeps an unknown value as the null it is, and leaves every other field of the param', () => {
        const withNull = [{id: 'n', data: [point('2026-01-02', null), point('2026-01-11', 4)]}];
        const out = paramsAtDay([{seriesId: 'n', seriesIndex: 0, dataIndex: 1, data: withNull[0].data[1], value: withNull[0].data[1].value, axisValue: 0, color: '#123', seriesName: 'N'}], '2026-01-05', withNull);
        expect(out).toHaveLength(1);
        expect((out[0].value as [string, number | null])[1]).toBeNull();
        expect(out[0].color).toBe('#123');
        expect(out[0].seriesName).toBe('N');
    });

    it('does not mutate the params it is given', () => {
        const given = [nearest('a', 1)];
        const copy = JSON.parse(JSON.stringify(given));
        paramsAtDay(given, '2026-01-09', SERIES);
        expect(given).toEqual(copy);
    });

    it('is a no-op for no day', () => {
        const given = [nearest('a', 1)];
        expect(paramsAtDay(given, null, SERIES)).toBe(given);
    });
});
