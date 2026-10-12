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

export function buildResponsiveXAxisPolicy({width, values, locale, axisType, horizontalPadding = 64}: ResponsiveXAxisInput): ResponsiveXAxisPolicy {
    const usableWidth = Math.max(0, width - horizontalPadding);
    const pointCount = values.length;
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
        },
    };
}
