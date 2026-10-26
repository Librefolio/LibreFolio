/**
 * The tooltip of step lines, on the day the pointer is on (Y5-3, D-P4).
 *
 * On a time axis ECharts hands every series the data point nearest to the pointer, so in the right half of a step a line would show the next
 * step's value while the line says another (measured with ECharts 6.0.0). A chart sets `axisPointer.snap: false` on its time axis, keeps
 * `dayOfAxisValue(event.axesInfo[0].value)` from the `updateAxisPointer` event, and gives its tooltip builder `paramsAtDay(params, day, series)`
 * instead of `params`: the builders read what each line says that day, and none of them changes.
 *
 * @module components/charts/stepTooltip
 */

import {indexHoldingDay} from '$lib/utils/stepSeries';

/** The part of an ECharts tooltip param this module reads and rewrites; every other field is kept. */
export interface StepParam {
    seriesId?: string;
    seriesIndex?: number;
    dataIndex?: number;
    data?: unknown;
    value?: unknown;
    axisValue?: unknown;
    [field: string]: unknown;
}

/** The part of a series of the option this module reads: its id and its data. */
export interface StepSeriesLike {
    id?: unknown;
    data?: unknown;
}

/** The day a datum is drawn on, when it is a `{value: [isoDay, y]}`, `[isoDay, y]` or `{name: isoDay}` datum; null for anything else (a millisecond x, a bare number). */
function dayOf(datum: unknown): string | null {
    const pair = Array.isArray(datum) ? datum : datum !== null && typeof datum === 'object' ? (datum as {value?: unknown}).value : undefined;
    const x = Array.isArray(pair) ? pair[0] : undefined;
    return typeof x === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(x) ? x : null;
}

function seriesOf(param: StepParam, series: ReadonlyArray<StepSeriesLike>): StepSeriesLike | undefined {
    if (typeof param.seriesId === 'string') {
        const byId = series.find((entry) => entry.id === param.seriesId);
        if (byId) return byId;
    }
    return typeof param.seriesIndex === 'number' ? series[param.seriesIndex] : undefined;
}

/**
 * The params of a step chart's tooltip, restated on `day`: each one becomes the point of its own series that holds the day (the last
 * on or before it) with `day` as its axis value; a series that does not exist that day (before its first point, after its last) loses its
 * param; a param whose series is not made of dated points (an internal series) is kept as it is. With no day, the params come back as given.
 */
export function paramsAtDay<P extends StepParam>(params: readonly P[], day: string | null, series: ReadonlyArray<StepSeriesLike>): P[] {
    if (day === null) return params as P[];
    const restated: P[] = [];
    for (const param of params) {
        const data = seriesOf(param, series)?.data;
        const days = Array.isArray(data) ? data.map(dayOf) : [];
        if (days.length === 0 || days.some((entry) => entry === null)) {
            restated.push(param);
            continue;
        }
        const first = days[0] as string;
        const last = days[days.length - 1] as string;
        if (day < first || day > last) continue;
        const index = indexHoldingDay(
            (days as string[]).map((date) => ({date})),
            day,
        );
        const datum = (data as unknown[])[index];
        restated.push({...param, dataIndex: index, data: datum, value: Array.isArray(datum) ? datum : (datum as {value?: unknown}).value, axisValue: day});
    }
    return restated;
}
