/**
 * Chart Signals Library — Barrel export.
 *
 * Provides chart overlay signals: real data (FxPairSignal) and
 * synthetic benchmarks (LinearSignal, CompoundSignal).
 *
 * Usage:
 *   import { createSignal, signalFromConfig, getRegisteredSignalTypes } from '$lib/charts/signals';
 *   import type { SignalConfig, RenderedSignal } from '$lib/charts/signals';
 */

// Base class & types
export {
    ChartSignal,
    DEFAULT_SIGNAL_COLORS,
    type MarkerType,
    type SignalColorRole,
    type SignalParamDescriptor,
    type SignalStyle,
    type SignalConfig,
    type SignalDefinition,
    type SignalDefinitionSource,
    type SignalDomain,
    type SignalIndicatorGroup,
    type SignalInputField,
    type SignalVisualComponent,
    type SignalVisualPartition,
    type SignalVisualStyle,
    type RenderedSignal,
} from './ChartSignal';
export {backendSignalSchemas} from './backendTypes';
export type {
    BackendSignalAnnotation,
    BackendSignalBandSeries,
    BackendSignalBarSeries,
    BackendSignalCatalogDefinition,
    BackendSignalCatalogResponse,
    BackendSignalLineSeries,
    BackendSignalOutputSpec,
    BackendSignalOutputStyle,
    BackendSignalReferenceLevel,
    BackendSignalRequest,
    BackendSignalResult,
    BackendSignalSeries,
    BackendSignalStatus,
    BackendSignalValueRegion,
} from './backendTypes';
export {defaultSignalVisualStyle, resolveSignalColor, resolveVisualSignalStyle} from './signalVisualStyle';

// Concrete signal classes
export {FxPairSignal} from './FxPairSignal';
export {AssetComparisonSignal} from './AssetComparisonSignal';
export {LinearSignal} from './LinearSignal';
export {CompoundSignal} from './CompoundSignal';
export {SineSignal} from './SineSignal';
export {EmaSignal} from './EmaSignal';
export {MacdSignal} from './MacdSignal';
export {RsiSignal} from './RsiSignal';
export {BollingerSignal} from './BollingerSignal';

// Measure signal (not registered in dropdown — managed by MeasurePanel)
export {MeasureSignal, type MeasurementResult} from './MeasureSignal';

// Registry & factory
export {getLocalSignalDefinitions, getRegisteredSignalTypes, createSignal, createSignalConfig, signalFromConfig, type SignalTypeInfo} from './registry';
export {mapBackendSignalDefinition, mergeSignalDefinitions, signalCodeToType} from './catalogMapper';
export {mapSignalParamsSchema, UnsupportedSignalSchemaError} from './schemaMapper';
export {renderBackendSignalResult, type BackendSignalRendererOptions, type BackendSignalRenderOutcome} from './backendRenderer';
export {buildBackendSignalRequestPlan, type BackendSignalRequestPlan} from './requestBuilder';
export {mapSignalInstanceResults, SignalResultState, type SignalInstanceResult, type SignalInstanceStatus} from './resultMapper';
export {getSignalProblem, getSignalProblemSeverity, type SignalProblem, type SignalProblemCode, type SignalProblemSeverity} from './signalProblem';
export {resolveSignalPreview, type BackendPreviewState, type SignalPreviewResolution} from './previewPolicy';
