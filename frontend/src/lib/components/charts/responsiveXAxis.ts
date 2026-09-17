import {parseDisplayDate} from '$lib/utils/core/formatAxisDate';

export interface ResponsiveXAxisPolicy {
    compact: boolean;
    maxLabels: number;
    splitNumber?: number;
    axisLabel?: {
        hideOverlap: true;
        showMinLabel: true;
        showMaxLabel: true;
        rotate: 0;
        interval?: number | 'auto';
        formatter: (value: number | string) => string;
    };
}

interface ResponsiveXAxisInput {
    width: number;
    values: readonly (number | string)[];
    locale?: string;
    axisType: 'category' | 'time';
    horizontalPadding?: number;
}

function dateSpanDays(values: readonly (number | string)[]): number {
    if (values.length < 2) return 0;
    const first = parseDisplayDate(values[0]);
    const last = parseDisplayDate(values.at(-1)!);
    if (!first || !last) return 0;
    const firstDay = Date.UTC(first.getFullYear(), first.getMonth(), first.getDate());
    const lastDay = Date.UTC(last.getFullYear(), last.getMonth(), last.getDate());
    return Math.abs(lastDay - firstDay) / 86_400_000;
}

export function formatCompactXAxisDate(locale: string | undefined, value: number | string, spanDays: number): string {
    const date = parseDisplayDate(value);
    if (!date) return String(value);
    const options: Intl.DateTimeFormatOptions = spanDays >= 365 ? {month: 'short', year: '2-digit'} : spanDays > 90 ? {month: 'short'} : {day: 'numeric', month: 'short'};
    return new Intl.DateTimeFormat(locale || undefined, options).format(date);
}

export function buildResponsiveXAxisPolicy({width, values, locale, axisType, horizontalPadding = 64}: ResponsiveXAxisInput): ResponsiveXAxisPolicy {
    const usableWidth = Math.max(0, width - horizontalPadding);
    const pointCount = values.length;
    const compact = usableWidth < 480 || (pointCount > 1 && usableWidth / pointCount < 24);
    const labelBudget = axisType === 'time' ? 48 : 56;
    const maxLabels = compact ? Math.max(2, Math.min(12, Math.floor(usableWidth / labelBudget))) : Math.max(2, pointCount);
    if (!compact) return {compact, maxLabels};

    const spanDays = dateSpanDays(values);
    const formatter = (value: number | string) => formatCompactXAxisDate(locale, value, spanDays);
    const interval = axisType === 'category' && pointCount > maxLabels ? Math.max(0, Math.ceil((pointCount - 1) / (maxLabels - 1)) - 1) : undefined;

    return {
        compact,
        maxLabels,
        ...(axisType === 'time' ? {splitNumber: maxLabels} : {}),
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
