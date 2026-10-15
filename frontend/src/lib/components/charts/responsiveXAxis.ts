import * as echarts from 'echarts';
import {parseDisplayDate} from '$lib/utils/core/formatAxisDate';
import {uiLocale} from '$lib/stores/app/uiLocale';

/**
 * The third argument ECharts passes to an axis-label formatter: a time axis sends
 * the tick level (`time.level`, plus the deprecated `level` alias), a category
 * axis sends nothing.
 */
interface AxisLabelFormatterExtra {
    level?: number;
    time?: {level?: number};
}

export type ResponsiveXAxisFormatter = (value: number | string, index?: number, extra?: AxisLabelFormatterExtra | null) => string;

export interface ResponsiveXAxisPolicy {
    compact: boolean;
    maxLabels: number;
    splitNumber?: number;
    /** The label formatter in both modes: ECharts' own labels are English on a time axis and raw ISO dates on a category one. */
    formatter: ResponsiveXAxisFormatter;
    axisLabel?: {
        hideOverlap: true;
        showMinLabel: true;
        showMaxLabel: true;
        rotate: 0;
        interval?: number | 'auto';
        /** Category axes only: the forced last label ends at its tick instead of spilling past the chart's right edge. */
        alignMaxLabel?: 'right';
        formatter: ResponsiveXAxisFormatter;
    };
}

interface ResponsiveXAxisInput {
    width: number;
    values: readonly (number | string)[];
    /** Default: the interface locale (`uiLocale()`, M-18). */
    locale?: string;
    axisType: 'category' | 'time';
    horizontalPadding?: number;
    /**
     * How many of `values` a zoom leaves visible (`visiblePointCountFromZoom`). The density and the label spacing of a
     * category axis follow the visible window, not the whole series: computed on all the points, a zoomed window of 34
     * days out of 365 keeps a step of 34 and shows only its edges (47-1). The formatter still names every value.
     */
    visibleCount?: number;
}

interface AxisDateFormats {
    dayMonth: Intl.DateTimeFormat;
    dayMonthYear: Intl.DateTimeFormat;
    month: Intl.DateTimeFormat;
    monthYear: Intl.DateTimeFormat;
    year: Intl.DateTimeFormat;
}

function axisDateFormats(locale: string | undefined): AxisDateFormats {
    const format = (options: Intl.DateTimeFormatOptions) => new Intl.DateTimeFormat(locale || uiLocale(), options);
    return {
        dayMonth: format({day: 'numeric', month: 'short'}),
        dayMonthYear: format({day: 'numeric', month: 'short', year: '2-digit'}),
        month: format({month: 'short'}),
        monthYear: format({month: 'short', year: '2-digit'}),
        year: format({year: 'numeric'}),
    };
}

function isLocalMidnight(date: Date): boolean {
    return date.getHours() === 0 && date.getMinutes() === 0 && date.getSeconds() === 0 && date.getMilliseconds() === 0;
}

function crossesCalendarYear(first: Date | null | undefined, last: Date | null | undefined): boolean {
    return !!first && !!last && first.getFullYear() !== last.getFullYear();
}

/**
 * Names the ticks ECharts places on a time axis. The label follows the tick, not the
 * length of the period: ticks a week apart read "8 Aug", "15 Aug", never "Aug Aug".
 *
 * - With `labelEndpoints` (compact mode, where the edge labels are forced on), the
 *   first and last data points keep their day, with the year when the range crosses
 *   one, and the midnight of a last day that ends mid-day gets no label.
 * - A tick off local midnight gets no label: it would repeat a day already on the axis.
 * - January 1st is the year. The 1st of another month is the month when the ticks
 *   are months (level 0), and "1 Aug" when it is a month boundary among day ticks.
 */
function buildTimeAxisFormatter(locale: string | undefined, values: readonly (number | string)[], labelEndpoints: boolean): ResponsiveXAxisFormatter {
    const formats = axisDateFormats(locale);
    const first = values.length > 0 ? parseDisplayDate(values[0]) : null;
    const last = values.length > 0 ? parseDisplayDate(values[values.length - 1]) : null;
    const endpointFormat = crossesCalendarYear(first, last) ? formats.dayMonthYear : formats.dayMonth;
    const lastDayMidnight = labelEndpoints && last && !isLocalMidnight(last) ? new Date(last.getFullYear(), last.getMonth(), last.getDate()).getTime() : null;

    return (value, _index, extra) => {
        const date = parseDisplayDate(value);
        if (!date) return String(value);
        const time = date.getTime();
        if (labelEndpoints && (time === first?.getTime() || time === last?.getTime())) return endpointFormat.format(date);
        if (!isLocalMidnight(date) || time === lastDayMidnight) return '';
        if (date.getDate() !== 1) return formats.dayMonth.format(date);
        if (date.getMonth() === 0) return formats.year.format(date);
        const level = extra?.time?.level ?? extra?.level ?? 0;
        return level > 0 ? formats.dayMonth.format(date) : formats.month.format(date);
    };
}

/**
 * Names the labels of a category axis, one every `interval + 1` points.
 *
 * Month names alone are used only when every two neighbouring labels fall in
 * different months; otherwise the labels keep their day. The year is added where it
 * changes from the previous label, and on the first and last point when the data
 * crosses a year. A label off the regular grid (the last point, or one moved by
 * zoom) keeps its day.
 *
 * Without an `interval` (desktop), ECharts picks the labels itself, so every label
 * carries what it needs: the month for monthly data, the day otherwise, and the year
 * whenever the data crosses one.
 */
function buildCategoryAxisFormatter(locale: string | undefined, values: readonly (number | string)[], interval: number | null): ResponsiveXAxisFormatter {
    const formats = axisDateFormats(locale);
    const dates = values.map((value) => parseDisplayDate(value));
    const indexByValue = new Map(values.map((value, index) => [String(value), index]));
    const step = interval === null ? 1 : interval + 1;
    const lastIndex = dates.length - 1;
    const crossesYear = crossesCalendarYear(dates[0], dates[lastIndex]);
    const monthOf = (date: Date) => date.getFullYear() * 12 + date.getMonth();
    let monthLabels = dates.length > 1 && dates.every((date) => date !== null);
    for (let index = step; monthLabels && index <= lastIndex; index += step) {
        monthLabels = monthOf(dates[index]!) !== monthOf(dates[index - step]!);
    }

    return (value) => {
        const index = indexByValue.get(String(value));
        const date = index === undefined ? parseDisplayDate(value) : dates[index];
        if (!date) return String(value);
        if (interval === null) return (monthLabels ? (crossesYear ? formats.monthYear : formats.month) : crossesYear ? formats.dayMonthYear : formats.dayMonth).format(date);
        if (index === undefined) return (crossesYear ? formats.dayMonthYear : formats.dayMonth).format(date);
        const regular = index % step === 0;
        const previousIndex = regular ? index - step : Math.floor(index / step) * step;
        const previous = previousIndex >= 0 && previousIndex !== index ? dates[previousIndex] : null;
        const withYear = (!!previous && previous.getFullYear() !== date.getFullYear()) || ((index === 0 || index === lastIndex) && crossesYear);
        if (monthLabels && regular) return (withYear ? formats.monthYear : formats.month).format(date);
        return (withYear ? formats.dayMonthYear : formats.dayMonth).format(date);
    };
}

/** Painted width, in px, of one axis label text. */
export type AxisLabelMeasure = (text: string) => number;

interface TimeAxisGridRightInput {
    /** The chart's width in px. */
    width: number;
    /** The data dates of the axis: the first and the last bound the labels it can draw. */
    values: readonly (number | string)[];
    /** Default: the interface locale (`uiLocale()`, M-18). */
    locale?: string;
    /** The grid's right edge without the fix: px, or a percentage of `width` as ECharts reads it. */
    base: number | string;
    measure: AxisLabelMeasure;
}

/** The part of an ECharts instance the label font is read from: its model, once a first option has built it. */
interface ChartModelSource {
    getModel?: () => {get?: (path: string[]) => unknown} | undefined;
}

const DAY_MS = 86_400_000;
const CANDIDATE_CACHE_SIZE = 16;
const candidateCache = new Map<string, readonly string[]>();

const calendarDay = (date: Date) => `${date.getFullYear()}-${date.getMonth() + 1}-${date.getDate()}`;

/**
 * Every text `buildTimeAxisFormatter` can write, compact or wide, on an axis whose data runs from
 * `first` to `last`. Zoom can put the axis edge on any day of the data, and ECharts widens a
 * one-day extent by a day on each side, so each local midnight from the day before `first` to the
 * day after `last` can be a labelled tick. Past 366 days every day of the calendar can: a leap
 * year names them all, plus the year of each real January 1.
 */
function timeAxisLabelCandidates(locale: string, first: Date, last: Date): readonly string[] {
    const key = `${locale}|${calendarDay(first)}|${calendarDay(last)}`;
    const cached = candidateCache.get(key);
    if (cached) return cached;

    const formats = axisDateFormats(locale);
    const endpointFormat = crossesCalendarYear(first, last) ? formats.dayMonthYear : formats.dayMonth;
    const texts = new Set([endpointFormat.format(first), endpointFormat.format(last)]);
    const addTick = (day: Date) => {
        if (day.getDate() !== 1) {
            texts.add(formats.dayMonth.format(day));
        } else if (day.getMonth() === 0) {
            texts.add(formats.year.format(day));
        } else {
            texts.add(formats.month.format(day));
            texts.add(formats.dayMonth.format(day));
        }
    };
    const nextDay = (day: Date) => new Date(day.getFullYear(), day.getMonth(), day.getDate() + 1);
    const start = new Date(first.getFullYear(), first.getMonth(), first.getDate() - 1);
    const stop = new Date(last.getFullYear(), last.getMonth(), last.getDate() + 1).getTime();
    if (Math.round((stop - start.getTime()) / DAY_MS) + 1 > 366) {
        for (let day = new Date(2024, 0, 2); day.getFullYear() === 2024; day = nextDay(day)) addTick(day);
        for (let year = start.getFullYear(); year <= new Date(stop).getFullYear(); year++) {
            const newYear = new Date(year, 0, 1);
            if (newYear.getTime() >= start.getTime() && newYear.getTime() <= stop) addTick(newYear);
        }
    } else {
        for (let day = start; day.getTime() <= stop; day = nextDay(day)) addTick(day);
    }

    const candidates = [...texts];
    if (candidateCache.size >= CANDIDATE_CACHE_SIZE) candidateCache.delete(candidateCache.keys().next().value!);
    candidateCache.set(key, candidates);
    return candidates;
}

function insetPx(base: number | string, width: number): number {
    if (typeof base === 'number') return base;
    const value = parseFloat(base);
    if (Number.isNaN(value)) return 0;
    return base.trim().endsWith('%') ? (value / 100) * width : value;
}

/**
 * The right edge of a time-axis grid that keeps the last label whole (plan 52).
 *
 * WHY: `grid.containLabel` reserves the height of the x labels, never the half-width a centred
 * label overhangs past the plot's right edge. A time axis ends exactly on the last day of the data,
 * or of the zoom, and ECharts labels that edge, so on a phone the last label was cut. The inset is
 * half the widest label the axis can draw plus 2 px; it replaces `base` only when it is wider, so a
 * desktop keeps its percentage and follows its own width.
 */
export function timeAxisGridRight({width, values, locale, base, measure}: TimeAxisGridRightInput): number | string {
    const first = values.length > 0 ? parseDisplayDate(values[0]) : null;
    const last = values.length > 0 ? parseDisplayDate(values[values.length - 1]) : null;
    if (!first || !last) return base;
    const [low, high] = first.getTime() <= last.getTime() ? [first, last] : [last, first];
    let widest = 0;
    for (const text of timeAxisLabelCandidates(locale || uiLocale(), low, high)) widest = Math.max(widest, measure(text));
    const inset = widest > 0 ? Math.ceil(widest / 2) + 2 : 0;
    return inset > insetPx(base, width) ? inset : base;
}

/** The CSS font ECharts draws a `fontSize` axis label with: the chart's family, or ECharts 6's own default before a first option. */
export function axisLabelFont(chart: unknown, fontSize: number): string {
    const family = (chart as ChartModelSource | null | undefined)?.getModel?.()?.get?.(['textStyle', 'fontFamily']);
    if (typeof family === 'string' && family !== '') return `${fontSize}px ${family}`;
    const windows = typeof navigator !== 'undefined' && /^Win/.test(navigator.platform ?? '');
    return `${fontSize}px ${windows ? 'Microsoft YaHei' : 'sans-serif'}`;
}

/**
 * Painted width of a `fontSize` axis label on `chart`, as ECharts lays it out.
 *
 * WHY lazy: the font is resolved at the first measure, and `echarts.format` read only inside the
 * call, so a test that mocks ECharts without it still mounts a chart that measures nothing.
 */
export function axisLabelMeasure(chart: unknown, fontSize: number): AxisLabelMeasure {
    let font: string | undefined;
    return (text) => {
        font ??= axisLabelFont(chart, fontSize);
        return echarts.format.getTextRect(text, font).width;
    };
}

export function buildResponsiveXAxisPolicy({width, values, locale, axisType, horizontalPadding = 64, visibleCount}: ResponsiveXAxisInput): ResponsiveXAxisPolicy {
    const usableWidth = Math.max(0, width - horizontalPadding);
    const pointCount = visibleCount === undefined || !Number.isFinite(visibleCount) ? values.length : Math.min(values.length, Math.max(1, Math.round(visibleCount)));
    const compact = usableWidth < 480 || (pointCount > 1 && usableWidth / pointCount < 24);
    const labelBudget = axisType === 'time' ? 48 : 56;
    const maxLabels = compact ? Math.max(2, Math.min(12, Math.floor(usableWidth / labelBudget))) : Math.max(2, pointCount);
    if (!compact) {
        const formatter = axisType === 'time' ? buildTimeAxisFormatter(locale, values, false) : buildCategoryAxisFormatter(locale, values, null);
        return {compact, maxLabels, formatter};
    }

    const interval = axisType === 'category' && pointCount > maxLabels ? Math.max(0, Math.ceil((pointCount - 1) / (maxLabels - 1)) - 1) : undefined;
    const formatter = axisType === 'time' ? buildTimeAxisFormatter(locale, values, true) : buildCategoryAxisFormatter(locale, values, interval ?? 0);

    return {
        compact,
        maxLabels,
        ...(axisType === 'time' ? {splitNumber: maxLabels} : {}),
        formatter,
        axisLabel: {
            hideOverlap: true,
            showMinLabel: true,
            showMaxLabel: true,
            rotate: 0,
            formatter,
            ...(interval !== undefined ? {interval} : {}),
            // A centred last label spills half its width past the plot on a phone. Category labels share one priority,
            // so the forced last one survives `hideOverlap` once it ends at its tick; on a time axis a month or year tick
            // outranks it and the inward label would be the one hidden. The first label spills at most into the price axis's
            // label column on the left, which the grid keeps inside the chart.
            ...(axisType === 'category' ? {alignMaxLabel: 'right' as const} : {}),
        },
    };
}

/** How long a zoom gesture must pause before a chart re-spaces its category labels on the new window. */
export const ZOOM_LABEL_SETTLE_MS = 120;

/**
 * How many categories a zoom leaves visible, read from a `dataZoom` event (its first `batch` entry, or the event
 * itself) or from a `{start, end}` window: by value (`startValue`/`endValue`, indices on a category axis) when it
 * carries them, else by percent (`start`/`end`). Clamped to `[1, pointCount]`; `null` when there is nothing to read.
 * Read from the event, not from `getOption()`, which deep-clones the whole option on every zoom tick (47-1).
 */
export function visiblePointCountFromZoom(event: unknown, pointCount: number): number | null {
    if (!(pointCount > 0) || event === null || typeof event !== 'object') return null;
    const batch = (event as {batch?: unknown}).batch;
    const source = (Array.isArray(batch) && batch[0] !== null && typeof batch[0] === 'object' ? batch[0] : event) as {startValue?: unknown; endValue?: unknown; start?: unknown; end?: unknown};
    const clamp = (count: number) => Math.min(pointCount, Math.max(1, count));
    const finite = (value: unknown): value is number => typeof value === 'number' && Number.isFinite(value);
    if (finite(source.startValue) && finite(source.endValue)) return clamp(Math.round(source.endValue) - Math.round(source.startValue) + 1);
    if (finite(source.start) && finite(source.end)) {
        const last = pointCount - 1;
        return clamp(Math.ceil((source.end / 100) * last) - Math.floor((source.start / 100) * last) + 1);
    }
    return null;
}

/**
 * The `xAxis.axisLabel` patch that re-spaces a category axis on a new window (a zoom, a resize). A compact window
 * gets its own step, or ECharts' (`'auto'`) when it needs none, so a `setOption` merge never keeps the previous
 * window's step. A window that is no longer compact also gets back the defaults the compact policy overrides (47-1).
 */
export function categoryAxisLabelPatch(policy: ResponsiveXAxisPolicy): Record<string, unknown> {
    if (policy.axisLabel) return {interval: 'auto', ...policy.axisLabel};
    return {interval: 'auto', formatter: policy.formatter, hideOverlap: false, showMinLabel: null, showMaxLabel: null, alignMaxLabel: null};
}
