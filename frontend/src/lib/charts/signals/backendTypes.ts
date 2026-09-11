import {z} from 'zod';

import {schemas} from '$lib/api/generated';

export type BackendSignalCatalogDefinition = z.output<typeof schemas.SignalCatalogDefinition>;
export type BackendSignalCatalogResponse = z.output<typeof schemas.SignalCatalogResponse>;
export type BackendSignalRequest = z.input<typeof schemas.SignalRequest>;
export type BackendSignalResult = z.output<typeof schemas.SignalResult>;
export type BackendSignalStatus = z.output<typeof schemas.SignalStatus>;
export type BackendSignalLineSeries = z.output<typeof schemas.SignalLineSeries>;
export type BackendSignalAreaSeries = z.output<typeof schemas.SignalAreaSeries>;
export type BackendSignalBarSeries = z.output<typeof schemas.SignalBarSeries>;
export type BackendSignalBandSeries = z.output<typeof schemas.SignalBandSeries>;
export type BackendSignalSeries = BackendSignalLineSeries | BackendSignalAreaSeries | BackendSignalBarSeries | BackendSignalBandSeries;
export type BackendSignalReferenceLevel = z.output<typeof schemas.SignalReferenceLevel>;
export type BackendSignalValueRegion = z.output<typeof schemas.SignalValueRegion>;
export type BackendSignalOutputSpec = z.output<typeof schemas.SignalOutputSpec>;
export type BackendSignalOutputStyle = z.output<typeof schemas.SignalOutputStyle>;
export type BackendSignalAnnotation = z.output<typeof schemas.SignalAnnotation>;

type GeneratedBackendSignalSeries = NonNullable<BackendSignalResult['series']>[number];
type GeneratedLineSeries = Extract<GeneratedBackendSignalSeries, {kind: 'line'}>;
type GeneratedAreaSeries = Extract<GeneratedBackendSignalSeries, {kind: 'area'}>;
type GeneratedBarSeries = Extract<GeneratedBackendSignalSeries, {kind: 'bar'}>;
type GeneratedBandSeries = Extract<GeneratedBackendSignalSeries, {kind: 'band'}>;

export type NormalizedBackendSignalLineSeries = Omit<GeneratedLineSeries, 'points'> & {points: BackendSignalLineSeries['points']};
export type NormalizedBackendSignalAreaSeries = Omit<GeneratedAreaSeries, 'points'> & {points: BackendSignalAreaSeries['points']};
export type NormalizedBackendSignalBarSeries = Omit<GeneratedBarSeries, 'points'> & {points: BackendSignalBarSeries['points']};
export type NormalizedBackendSignalBandSeries = GeneratedBandSeries;
export type NormalizedBackendSignalSeries = NormalizedBackendSignalLineSeries | NormalizedBackendSignalAreaSeries | NormalizedBackendSignalBarSeries | NormalizedBackendSignalBandSeries;

function flattenGeneratedPoints<T>(points: Array<T | T[]>): T[] {
    return points.flatMap((point) => (Array.isArray(point) ? point : [point]));
}

export function normalizeBackendSignalSeries(series: GeneratedBackendSignalSeries): NormalizedBackendSignalSeries {
    switch (series.kind) {
        case 'line':
        case 'area':
        case 'bar':
            return {...series, points: flattenGeneratedPoints(series.points)};
        case 'band':
            return series;
    }
}

export const backendSignalSchemas = {
    catalog: schemas.SignalCatalogDefinition,
    request: schemas.SignalRequest,
    result: schemas.SignalResult,
    lineSeries: schemas.SignalLineSeries,
    areaSeries: schemas.SignalAreaSeries,
    barSeries: schemas.SignalBarSeries,
    bandSeries: schemas.SignalBandSeries,
} as const;
