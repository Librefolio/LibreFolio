import type {LineDataPoint} from '$lib/components/charts/LineChart.svelte';

import {
    normalizeBackendSignalSeries,
    type BackendSignalOutputStyle,
    type BackendSignalResult,
    type BackendSignalValueRegion,
    type NormalizedBackendSignalAreaSeries,
    type NormalizedBackendSignalBandSeries,
    type NormalizedBackendSignalBarSeries,
    type NormalizedBackendSignalLineSeries,
} from './backendTypes';
import type {RenderedSignal, SignalConfig, SignalDefinition, SignalStyle, SignalVisualComponent, SignalVisualStyle} from './ChartSignal';
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
    definition: SignalDefinition;
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
type RenderLineSeries = FlexibleDescription<NormalizedBackendSignalLineSeries>;
type RenderAreaSeries = FlexibleDescription<NormalizedBackendSignalAreaSeries>;
type RenderBarSeries = FlexibleDescription<NormalizedBackendSignalBarSeries>;
type RenderBandSeries = FlexibleDescription<NormalizedBackendSignalBandSeries>;
type RenderSeries = RenderLineSeries | RenderAreaSeries | RenderBarSeries | RenderBandSeries;

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
        fillOpacity: value.fill_opacity ?? 0.2,
    };
}

function visualComponent(definition: SignalDefinition, seriesKey: string): SignalVisualComponent {
    if (definition.source !== 'backend') throw new Error(`Signal definition '${definition.type}' is not backend-owned`);
    const component = definition.visualComponents?.find((candidate) => candidate.key === seriesKey);
    if (!component) throw new Error(`Signal definition '${definition.type}' has no output component '${seriesKey}'`);
    return component;
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
                  fillOpacity: 0.2,
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
    run: number;
    startIndex: number;
    endIndex: number;
}

/**
 * The most runs an unstyled line or area output is drawn as. Each run is an ECharts series as long as the whole axis, so
 * 30 runs on a ten-year daily axis are about 75 000 points, a few price lines' worth. Measured on the real rolling metrics,
 * an asset quoted monthly gives at most 19 runs over ten years even at the smallest window, and the default window one;
 * only a small window on an illiquid daily asset goes past 30 (46 to 371). Past the cap the output is one line joining
 * its gaps, as before J-21, and both its name and the outcome's warnings say so.
 */
export const MAX_LINE_RUNS = 30;

/** A stretch of one output between two points the backend sent without a value, as indices into its data. */
interface LineRun {
    startIndex: number;
    endIndex: number;
}

function segmentLength(segment: StyledLineSegment): number {
    return segment.endIndex - segment.startIndex + 1;
}

/**
 * Caps the slices of one output, merging the shortest into a neighbour of its own run. A merge never crosses a
 * gap the backend declared, so an output with more runs than `maximum` keeps one slice per run.
 */
function limitStyledSegments(segments: StyledLineSegment[], maximum = 100): StyledLineSegment[] {
    const limited = segments.map((segment) => ({...segment}));
    const sameRun = (index: number, neighbour: number) => limited[neighbour]?.run === limited[index].run;
    while (limited.length > maximum) {
        let shortestIndex = -1;
        for (let index = 0; index < limited.length; index++) {
            if (!sameRun(index, index - 1) && !sameRun(index, index + 1)) continue;
            if (shortestIndex < 0 || segmentLength(limited[index]) < segmentLength(limited[shortestIndex])) shortestIndex = index;
        }
        if (shortestIndex < 0) break;

        const previous = sameRun(shortestIndex, shortestIndex - 1) ? limited[shortestIndex - 1] : undefined;
        const next = sameRun(shortestIndex, shortestIndex + 1) ? limited[shortestIndex + 1] : undefined;
        if (previous && (!next || segmentLength(previous) >= segmentLength(next))) {
            previous.endIndex = limited[shortestIndex].endIndex;
        } else if (next) {
            next.startIndex = limited[shortestIndex].startIndex;
        }
        limited.splice(shortestIndex, 1);
    }
    return limited;
}

/**
 * Splits one line or area output into the series the chart draws: one per run between the points the backend
 * sent without a value, so the gap stays a gap, and for a line with styled value regions one per stretch of
 * constant style inside each run. A date absent from the output is no gap: the chart bridges it, as it bridges
 * the days without a quote on which an indicator has no point.
 */
function splitLineSignal(signal: RenderedSignal, runs: LineRun[]): RenderedSignal[] {
    const styledRegions = signal.seriesType === 'line' ? (signal.valueRegions ?? []).filter((region) => region.lineStyle) : [];
    if (signal.data.length === 0 || (styledRegions.length === 0 && runs.length <= 1)) return [signal];

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
    runs.forEach((run, runIndex) => {
        let currentStyle = styleForValue(signal.data[run.startIndex].value);
        let startIndex = run.startIndex;
        for (let index = run.startIndex + 1; index <= run.endIndex + 1; index++) {
            const nextStyle = index <= run.endIndex ? styleForValue(signal.data[index].value) : null;
            if (nextStyle && sameStyle(currentStyle, nextStyle)) continue;
            segments.push({
                ...currentStyle,
                run: runIndex,
                startIndex,
                endIndex: index - 1,
            });
            if (nextStyle) {
                currentStyle = nextStyle;
                startIndex = index - 1;
            }
        }
    });

    // Styled slices draw no level or region, as before; plain runs keep them on the first run only, since each
    // series would draw its own copy.
    const keepsReferences = styledRegions.length === 0;
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
        referenceLevels: keepsReferences && index === 0 ? signal.referenceLevels : undefined,
        valueRegions: keepsReferences && index === 0 ? signal.valueRegions : undefined,
    }));
}

function renderScalarSeries(series: RenderLineSeries | RenderAreaSeries | RenderBarSeries, component: SignalVisualComponent, config: SignalConfig, seriesIndex: number, baseValue: number | null, shouldTransform: boolean, notes: string[], translate?: (key: string) => string): RenderedSignal[] {
    // A point without a value is never drawn as a 0: it ends a run, and the next value starts another.
    const data: Array<{date: string; value: number}> = [];
    const runs: LineRun[] = [];
    let gapSinceLastValue = false;
    for (const point of series.points ?? []) {
        if (typeof point.value !== 'number') {
            gapSinceLastValue = data.length > 0;
            continue;
        }
        if (runs.length === 0 || gapSinceLastValue) runs.push({startIndex: data.length, endIndex: data.length});
        runs[runs.length - 1].endIndex = data.length;
        gapSinceLastValue = false;
        data.push({date: point.date, value: transformValue(point.value, baseValue, shouldTransform)});
    }

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
    const defaultStyle = resolveVisualSignalStyle(fallbackStyle, visualStyle, seriesIndex === 0 && (series.kind === 'line' || series.kind === 'area'));
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
        aggregationProfile: component.aggregationProfile,
        barColorMode: series.kind === 'bar' && config.componentStyles?.[series.key] ? 'single' : 'signed',
        opacity: visualStyle.opacity,
        fillOpacity: visualStyle.fillOpacity,
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
    if (series.kind === 'bar') return [rendered];
    const styled = series.kind === 'line' && (rendered.valueRegions ?? []).some((region) => region.lineStyle);
    if (!styled && runs.length > MAX_LINE_RUNS) {
        notes.push(translatedLabel('signals.gapsJoined.warning', 'Too many gaps to draw: the line joins them.', translate));
        return [{...rendered, label: `${rendered.label} (${translatedLabel('signals.gapsJoined.label', 'gaps joined', translate)})`}];
    }
    return splitLineSignal(rendered, runs);
}

function renderBandSeries(series: RenderBandSeries, component: SignalVisualComponent, config: SignalConfig, baseValue: number | null, shouldTransform: boolean, translate?: (key: string) => string): RenderedSignal {
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
        aggregationProfile: component.aggregationProfile,
        opacity: visualStyle.opacity,
        fillOpacity: visualStyle.fillOpacity,
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
    const notes: string[] = [];
    const signals = (result.series ?? [])
        .flatMap((generatedSeries, seriesIndex) => {
            const series = normalizeBackendSignalSeries(generatedSeries);
            const shouldTransform = options.viewMode === 'percentage' && series.view_transform === 'base_percentage';
            const component = visualComponent(options.definition, series.key);
            return series.kind === 'band' ? [renderBandSeries(series, component, config, baseValue, shouldTransform, options.translate)] : renderScalarSeries(series, component, config, seriesIndex, baseValue, shouldTransform, notes, options.translate);
        })
        .filter((signal) => signal.data.length > 0);

    return {
        signals,
        status: result.status,
        warnings: [...(result.warnings ?? []).map((warning) => warning.message), ...notes],
        error: resultErrorMessage(result.error),
    };
}

/**
 * How many points one signal instance shows across the series it rendered into: the «📈N» badge of the signals
 * panel. It counts dates, because neither the longest series nor the sum is the count: the slices of a styled
 * line share their join points, the runs of a line with gaps split it, and the components of one output share
 * their dates.
 */
export function renderedSignalPointCount(signals: RenderedSignal[]): number {
    return new Set(signals.flatMap((signal) => signal.data.map((point) => point.date))).size;
}
