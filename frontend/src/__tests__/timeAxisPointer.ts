/**
 * Which day does a chart open on? The Vitest half (Y2-I63, GitHub issue #63); the browser half is `e2e/fixtures/timeAxisTooltip.ts`.
 *
 * A chart with a time axis listens to ECharts' `updateAxisPointer` event, which carries the pointed instant as epoch milliseconds, and its tooltip
 * formatter writes the day it stands for into the header (`data-tooltip-from` / `data-tooltip-to`, ISO). A component test mounts the chart over a
 * recorder of ECharts, fires that event at the instants that matter, and reads the days back with `tooltipSpan`: no translated word, no pixel.
 * What it cannot see is the geometry (where a pixel lands); the E2E does.
 */

/** The instant ECharts reports for `hour:minute` local time on `day` (an ISO date). */
export function axisMs(day: string, hour = 0, minute = 0): number {
    const [year, month, date] = day.split('-').map(Number);
    return new Date(year, month - 1, date, hour, minute).getTime();
}

/** The `updateAxisPointer` handlers a recorder of ECharts kept for a chart. */
export type PointerHandlers = ReadonlyArray<(event: unknown) => void>;

/** Fire the event of the pointer resting at `hour:minute` of `day`. */
export function firePointer(handlers: PointerHandlers, day: string, hour = 0, minute = 0): void {
    if (handlers.length === 0) throw new Error('the chart does not listen to the axis pointer (updateAxisPointer)');
    for (const handler of handlers) handler({axesInfo: [{axisDim: 'x', value: axisMs(day, hour, minute)}]});
}

/** A moment the pointer can rest at: `days` days after the day it is given, at `hour:minute`. */
export interface PointerMoment {
    label: string;
    days: number;
    hour: number;
    minute: number;
}

/**
 * The moments at which the pointer of a chart that snaps to days (`attachDaySnap`: the nearest day, noon going to the next) rests on the OLDEST
 * day shown: from its midnight to the last minute before noon. Before its midnight there is no plot.
 */
export const MOMENTS_ON_THE_OLDEST_DAY: readonly PointerMoment[] = [
    {label: 'its midnight', days: 0, hour: 0, minute: 0},
    {label: 'a minute before its noon', days: 0, hour: 11, minute: 59},
];

/**
 * The same for the NEWEST day shown: from the noon of the day before to its midnight. After its midnight there is no plot (the time axis ends
 * there), so a later moment is not a pointer a user can reach.
 */
export const MOMENTS_ON_THE_NEWEST_DAY: readonly PointerMoment[] = [
    {label: 'the noon before it', days: -1, hour: 12, minute: 0},
    {label: 'the last minute before it', days: -1, hour: 23, minute: 59},
    {label: 'its midnight', days: 0, hour: 0, minute: 0},
];

/** The moments of a chart whose tooltip reads the day the pointer is IN (no snap): every moment of the day. */
export const MOMENTS_IN_A_DAY: readonly PointerMoment[] = [
    {label: 'midnight', days: 0, hour: 0, minute: 0},
    {label: 'noon', days: 0, hour: 12, minute: 0},
    {label: 'the last minute', days: 0, hour: 23, minute: 59},
];

/** Fire the event of the pointer resting at `moment` of `day`. */
export function firePointerAt(handlers: PointerHandlers, day: string, moment: PointerMoment): void {
    const [year, month, date] = day.split('-').map(Number);
    const at = new Date(year, month - 1, date + moment.days);
    const iso = `${at.getFullYear()}-${String(at.getMonth() + 1).padStart(2, '0')}-${String(at.getDate()).padStart(2, '0')}`;
    firePointer(handlers, iso, moment.hour, moment.minute);
}

/** `html` with the days its headers publish taken out, to read what a tooltip says to a person (those attributes hold ISO dates by design). */
export function withoutTooltipDays(html: string): string {
    return html.replace(/ data-tooltip-(?:from|to)="\d{4}-\d{2}-\d{2}"/g, '');
}

/** The days the header of a tooltip stands for, or null when the tooltip has no dated header (or is empty). */
export function tooltipSpan(html: string): {from: string; to: string} | null {
    const from = /data-tooltip-from="(\d{4}-\d{2}-\d{2})"/.exec(html)?.[1];
    const to = /data-tooltip-to="(\d{4}-\d{2}-\d{2})"/.exec(html)?.[1];
    return from && to ? {from, to} : null;
}

/** True when `html` is the tooltip of a header that stands for `day` (alone, or inside a bucket). */
export function tooltipHoldsDay(html: string, day: string): boolean {
    const span = tooltipSpan(html);
    return span !== null && span.from <= day && day <= span.to;
}
