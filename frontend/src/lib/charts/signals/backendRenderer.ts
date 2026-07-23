import type {LineDataPoint} from '$lib/components/charts/LineChart.svelte';

import type {BackendSignalResult, BackendSignalSeries} from './backendTypes';
import type {RenderedSignal, SignalConfig} from './ChartSignal';

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

function axisLabel(series: BackendSignalSeries): string {
    return series.axis.key.replaceAll('_', ' ').toUpperCase();
}

function resultErrorMessage(error: BackendSignalResult['error']): string | null {
    if (Array.isArray(error)) {
        return error.find((item) => item !== null)?.message ?? null;
    }
    return error?.message ?? null;
}

function renderScalarSeries(series: Extract<BackendSignalSeries, {kind: 'line' | 'bar'}>, config: SignalConfig, seriesIndex: number, baseValue: number | null, shouldTransform: boolean, translate?: (key: string) => string): RenderedSignal {
    const data = (series.points ?? [])
        .filter((point): point is typeof point & {value: number} => typeof point.value === 'number')
        .map((point) => ({
            date: point.date,
            value: transformValue(point.value, baseValue, shouldTransform),
        }));

    return {
        id: `${config.id}:${series.key}`,
        label: translatedLabel(series.label_key, `${series.key.toUpperCase()}`, translate),
        data,
        color: config.style.color,
        lineWidth: config.style.lineWidth,
        lineType: seriesIndex === 0 ? config.style.lineType : 'dashed',
        markerStart: seriesIndex === 0 ? config.style.markerStart : null,
        markerEnd: seriesIndex === 0 ? config.style.markerEnd : null,
        seriesType: series.kind,
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
        valueRegions: (series.value_regions ?? []).map((region) => ({
            key: region.key,
            label: translatedLabel(region.label_key, region.key, translate),
            semantic: region.semantic,
            lower: typeof region.lower === 'number' ? transformValue(region.lower, baseValue, shouldTransform) : undefined,
            upper: typeof region.upper === 'number' ? transformValue(region.upper, baseValue, shouldTransform) : undefined,
        })),
    };
}

function renderBandSeries(series: Extract<BackendSignalSeries, {kind: 'band'}>, config: SignalConfig, baseValue: number | null, shouldTransform: boolean, translate?: (key: string) => string): RenderedSignal {
    const completePoints = (series.points ?? []).filter((point): point is typeof point & {lower: number; middle: number; upper: number} => typeof point.lower === 'number' && typeof point.middle === 'number' && typeof point.upper === 'number');
    const data = completePoints.map((point) => ({
        date: point.date,
        value: transformValue(point.middle, baseValue, shouldTransform),
    }));

    return {
        id: `${config.id}:${series.key}`,
        label: translatedLabel(series.label_key, series.key.toUpperCase(), translate),
        data,
        color: config.style.color,
        lineWidth: config.style.lineWidth,
        lineType: config.style.lineType,
        markerStart: config.style.markerStart,
        markerEnd: config.style.markerEnd,
        seriesType: 'band',
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
        valueRegions: (series.value_regions ?? []).map((region) => ({
            key: region.key,
            label: translatedLabel(region.label_key, region.key, translate),
            semantic: region.semantic,
            lower: typeof region.lower === 'number' ? transformValue(region.lower, baseValue, shouldTransform) : undefined,
            upper: typeof region.upper === 'number' ? transformValue(region.upper, baseValue, shouldTransform) : undefined,
        })),
    };
}

export function renderBackendSignalResult(result: BackendSignalResult, config: SignalConfig, options: BackendSignalRendererOptions): BackendSignalRenderOutcome {
    const baseValue = options.baseData[0]?.value ?? null;
    const signals = (result.series ?? [])
        .map((series, seriesIndex) => {
            const shouldTransform = options.viewMode === 'percentage' && series.view_transform === 'base_percentage';
            return series.kind === 'band' ? renderBandSeries(series, config, baseValue, shouldTransform, options.translate) : renderScalarSeries(series, config, seriesIndex, baseValue, shouldTransform, options.translate);
        })
        .filter((signal) => signal.data.length > 0);

    return {
        signals,
        status: result.status,
        warnings: (result.warnings ?? []).map((warning) => warning.message),
        error: resultErrorMessage(result.error),
    };
}
