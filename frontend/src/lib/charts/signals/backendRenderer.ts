import type {LineDataPoint} from '$lib/components/charts/LineChart.svelte';

import type {BackendSignalBandSeries, BackendSignalBarSeries, BackendSignalLineSeries, BackendSignalOutputStyle, BackendSignalResult, BackendSignalValueRegion} from './backendTypes';
import type {RenderedSignal, SignalConfig, SignalStyle, SignalVisualStyle} from './ChartSignal';
import {defaultSignalVisualStyle, resolveVisualSignalStyle} from './signalVisualStyle';

export interface BackendSignalRenderOutcome {
    signals: RenderedSignal[];
    status: BackendSignalResult['status'];
    warnings: string[];
    error: string | null;
}

export interface BackendSignalRendererOptions {
    baseData: LineDataPoint[];
    viewMode: 'absolute' | 'percentage';
    translate?: (key: string) => string;
}

function translatedLabel(key: string, fallback: string, translate?: (key: string) => string): string {
    if (!translate) return fallback;
    const translated = translate(key);
    return translated !== key ? translated : fallback;
}

function transformValue(value: number, baseValue: number | null, shouldTransform: boolean): number {
    if (!shouldTransform || baseValue === null || baseValue === 0) return value;
    return ((value - baseValue) / baseValue) * 100;
}

type FlexibleDescription<T> = Omit<T, 'description_key'> & {description_key?: unknown};
type RenderLineSeries = FlexibleDescription<BackendSignalLineSeries>;
type RenderBarSeries = FlexibleDescription<BackendSignalBarSeries>;
type RenderBandSeries = FlexibleDescription<BackendSignalBandSeries>;
type RenderSeries = RenderLineSeries | RenderBarSeries | RenderBandSeries;

function axisLabel(series: RenderSeries): string {
    return series.axis.key.replaceAll('_', ' ').toUpperCase();
}

function resultErrorMessage(error: BackendSignalResult['error']): string | null {
    if (Array.isArray(error)) {
        return error.find((item) => item !== null)?.message ?? null;
    }
    return error?.message ?? null;
}

type RenderedValueRegion = NonNullable<RenderedSignal['valueRegions']>[number];

function normalizedRegionLineStyle(value: BackendSignalValueRegion['line_style']) {
    if (Array.isArray(value)) return value.find((item) => item !== null) ?? null;
    return value ?? null;
}

function normalizedLinePattern(value: BackendSignalOutputStyle['line_pattern']): SignalVisualStyle['lineType'] {
    const pattern = Array.isArray(value) ? value.find((item) => item !== null) : value;
    return pattern ?? undefined;
}

function normalizedOutputStyle(value: BackendSignalOutputStyle | undefined): SignalVisualStyle {
    if (!value) return defaultSignalVisualStyle();
    return {
        colorRole: value.color_role ?? 'primary',
        lineType: normalizedLinePattern(value.line_pattern),
        lineWidthDelta: value.width_delta ?? 0,
        opacity: value.opacity ?? 1,
    };
}

function mapValueRegions(series: RenderSeries, baseValue: number | null, componentStyle: SignalStyle, config: SignalConfig, shouldTransform: boolean, translate?: (key: string) => string): RenderedValueRegion[] {
    return (series.value_regions ?? []).map((region) => {
        const lineStyle = normalizedRegionLineStyle(region.line_style);
        const partitionKey = `${series.key}:${region.key}`;
        const defaultStyle = lineStyle
            ? resolveVisualSignalStyle(componentStyle, {
                  colorRole: lineStyle.color_role ?? 'primary',
                  lineType: lineStyle.pattern,
                  lineWidthDelta: lineStyle.width_delta ?? 0,
                  opacity: lineStyle.opacity ?? 1,
              })
            : null;
        const effectiveStyle = config.partitionStyles?.[partitionKey] ?? defaultStyle;
        return {
            key: region.key,
            label: translatedLabel(region.label_key, region.key, translate),
            semantic: region.semantic,
            lower: typeof region.lower === 'number' ? transformValue(region.lower, baseValue, shouldTransform) : undefined,
            upper: typeof region.upper === 'number' ? transformValue(region.upper, baseValue, shouldTransform) : undefined,
            includeLower: region.include_lower ?? true,
            includeUpper: region.include_upper ?? false,
            lineStyle: effectiveStyle
                ? {
                      lineType: effectiveStyle.lineType,
                      lineWidth: effectiveStyle.lineWidth,
                      color: effectiveStyle.color,
                      opacity: lineStyle?.opacity ?? 1,
                  }
                : undefined,
        };
    });
}

function regionContains(region: RenderedValueRegion, value: number): boolean {
    const aboveLower = region.lower === undefined || (region.includeLower ? value >= region.lower : value > region.lower);
    const belowUpper = region.upper === undefined || (region.includeUpper ? value <= region.upper : value < region.upper);
    return aboveLower && belowUpper;
}

interface StyledLineSegment {
    key: string;
    lineType: RenderedSignal['lineType'];
    lineWidth: number;
    color: string;
    opacity: number;
    startIndex: number;
    endIndex: number;
}

function segmentLength(segment: StyledLineSegment): number {
    return segment.endIndex - segment.startIndex + 1;
}

function limitStyledSegments(segments: StyledLineSegment[], maximum = 100): StyledLineSegment[] {
    const limited = segments.map((segment) => ({...segment}));
    while (limited.length > maximum) {
        let shortestIndex = 0;
        for (let index = 1; index < limited.length; index++) {
            if (segmentLength(limited[index]) < segmentLength(limited[shortestIndex])) shortestIndex = index;
        }

        if (shortestIndex === 0) {
            limited[1].startIndex = limited[0].startIndex;
        } else if (shortestIndex === limited.length - 1) {
            limited[shortestIndex - 1].endIndex = limited[shortestIndex].endIndex;
        } else if (segmentLength(limited[shortestIndex - 1]) >= segmentLength(limited[shortestIndex + 1])) {
            limited[shortestIndex - 1].endIndex = limited[shortestIndex].endIndex;
        } else {
            limited[shortestIndex + 1].startIndex = limited[shortestIndex].startIndex;
        }
        limited.splice(shortestIndex, 1);
    }
    return limited;
}

function applyValueRegionLineStyles(signal: RenderedSignal): RenderedSignal[] {
    const styledRegions = (signal.valueRegions ?? []).filter((region) => region.lineStyle);
    if (signal.seriesType !== 'line' || styledRegions.length === 0 || signal.data.length === 0) return [signal];

    const styleForValue = (value: number) => {
        const region = styledRegions.find((candidate) => regionContains(candidate, value));
        return {
            key: region?.key ?? 'default',
            lineType: region?.lineStyle?.lineType ?? signal.lineType,
            lineWidth: region?.lineStyle?.lineWidth ?? signal.lineWidth,
            color: region?.lineStyle?.color ?? signal.color,
            opacity: region?.lineStyle?.opacity ?? signal.opacity ?? 1,
        };
    };
    const sameStyle = (left: ReturnType<typeof styleForValue>, right: ReturnType<typeof styleForValue>) => left.key === right.key && left.lineType === right.lineType && left.lineWidth === right.lineWidth && left.color === right.color && left.opacity === right.opacity;

    const segments: StyledLineSegment[] = [];
    let currentStyle = styleForValue(signal.data[0].value);
    let startIndex = 0;
    for (let index = 1; index <= signal.data.length; index++) {
        const nextStyle = index < signal.data.length ? styleForValue(signal.data[index].value) : null;
        if (nextStyle && sameStyle(currentStyle, nextStyle)) continue;
        segments.push({
            ...currentStyle,
            startIndex,
            endIndex: index - 1,
        });
        if (nextStyle) {
            currentStyle = nextStyle;
            startIndex = index - 1;
        }
    }

    return limitStyledSegments(segments).map((segment, index, allSegments) => ({
        ...signal,
        id: `${signal.id}:${segment.key}:${segment.startIndex}`,
        data: signal.data.slice(segment.startIndex, segment.endIndex + 1),
        lineType: segment.lineType,
        lineWidth: segment.lineWidth,
        color: segment.color,
        opacity: segment.opacity,
        markerStart: index === 0 ? signal.markerStart : null,
        markerEnd: index === allSegments.length - 1 ? signal.markerEnd : null,
        referenceLevels: undefined,
        valueRegions: undefined,
    }));
}

function renderScalarSeries(series: RenderLineSeries | RenderBarSeries, config: SignalConfig, seriesIndex: number, baseValue: number | null, shouldTransform: boolean, translate?: (key: string) => string): RenderedSignal[] {
    const data = (series.points ?? [])
        .filter((point): point is typeof point & {value: number} => typeof point.value === 'number')
        .map((point) => ({
            date: point.date,
            value: transformValue(point.value, baseValue, shouldTransform),
        }));

    const visualStyle = normalizedOutputStyle(series.style);
        const fallbackStyle: SignalStyle =
            seriesIndex === 0
                ? config.style
                : {
                      ...config.style,
                      lineType: 'dashed',
                      markerStart: null,
                      markerEnd: null,
                  };
        const defaultStyle = resolveVisualSignalStyle(fallbackStyle, visualStyle, seriesIndex === 0 && series.kind === 'line');
    const componentStyle = config.componentStyles?.[series.key] ?? defaultStyle;
    const rendered: RenderedSignal = {
        id: `${config.id}:${series.key}`,
        label: translatedLabel(series.label_key, `${series.key.toUpperCase()}`, translate),
        data,
        color: componentStyle.color,
        lineWidth: componentStyle.lineWidth,
        lineType: componentStyle.lineType,
        markerStart: componentStyle.markerStart,
        markerEnd: componentStyle.markerEnd,
        seriesType: series.kind,
        barColorMode: series.kind === 'bar' && config.componentStyles?.[series.key] ? 'single' : 'signed',
        opacity: visualStyle.opacity,
        axisKey: series.axis.key,
        axisRole: series.axis.role,
        axisMinimum: typeof series.axis.minimum === 'number' ? series.axis.minimum : undefined,
        axisMaximum: typeof series.axis.maximum === 'number' ? series.axis.maximum : undefined,
        axisLabel: axisLabel(series),
        unit: series.unit,
        referenceLevels: (series.reference_levels ?? []).map((level) => ({
            key: level.key,
            label: translatedLabel(level.label_key, level.key, translate),
            semantic: level.semantic,
            value: transformValue(level.value, baseValue, shouldTransform),
        })),
        valueRegions: mapValueRegions(series, baseValue, componentStyle, config, shouldTransform, translate),
    };
    return series.kind === 'line' ? applyValueRegionLineStyles(rendered) : [rendered];
}

function renderBandSeries(series: RenderBandSeries, config: SignalConfig, baseValue: number | null, shouldTransform: boolean, translate?: (key: string) => string): RenderedSignal {
    const completePoints = (series.points ?? []).filter((point): point is typeof point & {lower: number; middle: number; upper: number} => typeof point.lower === 'number' && typeof point.middle === 'number' && typeof point.upper === 'number');
    const data = completePoints.map((point) => ({
        date: point.date,
        value: transformValue(point.middle, baseValue, shouldTransform),
    }));

    const visualStyle = normalizedOutputStyle(series.style);
    const defaultStyle = resolveVisualSignalStyle(config.style, visualStyle, true);
    const componentStyle = config.componentStyles?.[series.key] ?? defaultStyle;
    return {
        id: `${config.id}:${series.key}`,
        label: translatedLabel(series.label_key, series.key.toUpperCase(), translate),
        data,
        color: componentStyle.color,
        lineWidth: componentStyle.lineWidth,
        lineType: componentStyle.lineType,
        markerStart: componentStyle.markerStart,
        markerEnd: componentStyle.markerEnd,
        seriesType: 'band',
        opacity: visualStyle.opacity,
        bandData: {
            lower: completePoints.map((point) => transformValue(point.lower, baseValue, shouldTransform)),
            middle: data.map((point) => point.value),
            upper: completePoints.map((point) => transformValue(point.upper, baseValue, shouldTransform)),
        },
        axisKey: series.axis.key,
        axisRole: series.axis.role,
        axisMinimum: typeof series.axis.minimum === 'number' ? series.axis.minimum : undefined,
        axisMaximum: typeof series.axis.maximum === 'number' ? series.axis.maximum : undefined,
        axisLabel: axisLabel(series),
        unit: series.unit,
        referenceLevels: (series.reference_levels ?? []).map((level) => ({
            key: level.key,
            label: translatedLabel(level.label_key, level.key, translate),
            semantic: level.semantic,
            value: transformValue(level.value, baseValue, shouldTransform),
        })),
        valueRegions: mapValueRegions(series, baseValue, componentStyle, config, shouldTransform, translate),
    };
}

export function renderBackendSignalResult(result: BackendSignalResult, config: SignalConfig, options: BackendSignalRendererOptions): BackendSignalRenderOutcome {
    const baseValue = options.baseData[0]?.value ?? null;
    const signals = (result.series ?? [])
        .flatMap((series, seriesIndex) => {
            const shouldTransform = options.viewMode === 'percentage' && series.view_transform === 'base_percentage';
            return series.kind === 'band' ? [renderBandSeries(series, config, baseValue, shouldTransform, options.translate)] : renderScalarSeries(series, config, seriesIndex, baseValue, shouldTransform, options.translate);
        })
        .filter((signal) => signal.data.length > 0);

    return {
        signals,
        status: result.status,
        warnings: (result.warnings ?? []).map((warning) => warning.message),
        error: resultErrorMessage(result.error),
    };
}
