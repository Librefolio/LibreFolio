import {z} from 'zod';

import {schemas} from '$lib/api/generated';

export type BackendSignalCatalogDefinition = z.output<typeof schemas.SignalCatalogDefinition>;
export type BackendSignalCatalogResponse = z.output<typeof schemas.SignalCatalogResponse>;
export type BackendSignalRequest = z.input<typeof schemas.SignalRequest>;
export type BackendSignalResult = z.output<typeof schemas.SignalResult>;
export type BackendSignalStatus = z.output<typeof schemas.SignalStatus>;
export type BackendSignalLineSeries = z.output<typeof schemas.SignalLineSeries>;
export type BackendSignalBarSeries = z.output<typeof schemas.SignalBarSeries>;
export type BackendSignalBandSeries = z.output<typeof schemas.SignalBandSeries>;
export type BackendSignalSeries = BackendSignalLineSeries | BackendSignalBarSeries | BackendSignalBandSeries;
export type BackendSignalReferenceLevel = z.output<typeof schemas.SignalReferenceLevel>;
export type BackendSignalValueRegion = z.output<typeof schemas.SignalValueRegion>;
export type BackendSignalOutputSpec = z.output<typeof schemas.SignalOutputSpec>;
export type BackendSignalOutputStyle = z.output<typeof schemas.SignalOutputStyle>;
export type BackendSignalAnnotation = z.output<typeof schemas.SignalAnnotation>;

export const backendSignalSchemas = {
    catalog: schemas.SignalCatalogDefinition,
    request: schemas.SignalRequest,
    result: schemas.SignalResult,
    lineSeries: schemas.SignalLineSeries,
    barSeries: schemas.SignalBarSeries,
    bandSeries: schemas.SignalBandSeries,
} as const;
