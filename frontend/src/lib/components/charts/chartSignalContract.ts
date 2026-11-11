/**
 * What a chart draws for a signal: the one contract between the chart primitives and the signals.
 *
 * A signal (`features/signals`) turns its `SignalConfig` (the saved state, with its `SignalStyle`) and its data into a `RenderedSignal`; `LineChart`, `PriceChartCompact`,
 * `PriceChartFull` and `CandlestickChart` draw it. The contract lives with the charts, so a generic chart never imports
 * from a feature: the signals import it, and `features/signals/ChartSignal.ts` re-exports it for the users of the feature.
 *
 * @module components/charts/chartSignalContract
 */

import type {LineDataPoint} from '$lib/components/charts/LineChart.svelte';

// ═══════════════════════════════════════════════════════════════════════════════
// MARKER TYPES — Endpoint markers for signal lines
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * Marker type for signal line endpoints.
 * - 'arrow': directional arrow (ECharts 'arrow' symbol)
 * - 'circle': round dot
 * - 'diamond': diamond shape
 * - 'pin': pin/flag marker
 * - null: no marker
 */
export type MarkerType = 'arrow' | 'circle' | 'diamond' | 'rect' | 'pin' | null;

export type SignalAggregationProfile = 'last_with_range' | 'first_with_range' | 'min_with_range' | 'max_with_range' | 'band_envelope' | 'events_verbatim';

// ═══════════════════════════════════════════════════════════════════════════════
// SIGNAL STYLE — Common rendering parameters for every signal
// ═══════════════════════════════════════════════════════════════════════════════

export interface SignalStyle {
    /** Line color as hex string, e.g. '#3b82f6' */
    color: string;
    /** Line width: 1, 2, 3, or 4 */
    lineWidth: number;
    /** Line dash style */
    lineType: 'solid' | 'dashed' | 'dotted';
    /** Marker at the first data point, null = no marker */
    markerStart: MarkerType;
    /** Marker at the last data point, null = no marker */
    markerEnd: MarkerType;
}

// ═══════════════════════════════════════════════════════════════════════════════
// SIGNAL CONFIG — Serializable state (stored in ChartSettings)
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * Serializable config for a signal instance.
 * Stored in `ChartSettings.signals[]`. Local comparison and benchmark configs
 * may be recreated as class instances via the registry's `signalFromConfig()`.
 * Backend technical configs remain plain transported state and are rendered
 * generically from backend results.
 *
 * Local runtime data such as `params._resolvedData` and `params._basePoint` is excluded by `toConfig()`.
 */
export interface SignalConfig {
    /** Unique instance ID (UUID) */
    id: string;
    /** Registry key: 'fx-pair', 'linear', 'compound', etc. */
    signalType: string;
    /** Signal-specific editable parameters */
    params: Record<string, unknown>;
    /** Rendering style */
    style: SignalStyle;
    /** Per-output style overrides for backend signal components. */
    componentStyles?: Record<string, SignalStyle>;
    /** Per-region style overrides for backend threshold/value partitions. */
    partitionStyles?: Record<string, SignalStyle>;
}

// ═══════════════════════════════════════════════════════════════════════════════
// RENDERED SIGNAL — Output format for chart components
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * Output format after computing signal points — ready for chart rendering.
 * Passed as `overlayData` prop to LineChart / PriceChartCompact / PriceChartFull.
 */
export interface RenderedSignal {
    id: string;
    label: string;
    data: LineDataPoint[];
    color: string;
    lineWidth: number;
    lineType: 'solid' | 'dashed' | 'dotted';
    /** Marker at the first data point, null = no marker */
    markerStart: MarkerType;
    /** Marker at the last data point, null = no marker */
    markerEnd: MarkerType;
    /** Y-axis index: 0 = primary (right), 1 = secondary (left). Default 0. */
    yAxisIndex?: number;
    /** Canonical backend axis identity used to allocate independent axes. */
    axisKey?: string;
    /** Canonical semantic axis role. */
    axisRole?: 'price' | 'independent' | 'volume';
    /** Optional canonical axis bounds. */
    axisMinimum?: number;
    axisMaximum?: number;
    /** Short axis label shown next to independent values. */
    axisLabel?: string;
    /** Canonical output unit. */
    unit?: 'price' | 'percentage' | 'index' | 'volume' | 'none';
    /**
     * Series rendering type:
     * - 'line' (default): standard line series
     * - 'area': line plus fill from zero (used for Drawdown)
     * - 'bar': vertical bars (used for MACD histogram)
     * - 'band': confidence band — requires bandData with upper/lower arrays
     *           (used for Bollinger Bands)
     */
    seriesType?: 'line' | 'area' | 'bar' | 'band';
    /** Plugin-declared temporal representative policy. */
    aggregationProfile: SignalAggregationProfile;
    /** Signed histograms keep semantic green/red bars until explicitly overridden. */
    barColorMode?: 'signed' | 'single';
    /** Whether ECharts may connect gaps in sparse overlay series. Default preserves legacy true. */
    connectNulls?: boolean;
    /**
     * A comparison's line asks the chart to reach its days even where the main series has none: a chart with a category axis (the detail pages
     * of an asset and of an FX pair, which render their comparisons with `_unionAxis`) lays its axis on the union of the main days and the days of
     * the signals that say so, so a comparison older than the main series is drawn from its first day and the main line is empty before its own.
     * Indicators, benchmarks and the comparisons of a card do not say so: they follow the main series' days.
     */
    extendsAxis?: boolean;
    /**
     * Band data for confidence-band rendering (seriesType === 'band').
     * Contains parallel arrays for upper, middle, lower values aligned to `data[].date`.
     */
    bandData?: {
        upper: number[];
        middle: number[];
        lower: number[];
        observedDates?: Array<{
            upper: string;
            middle: string;
            lower: string;
        }>;
    };
    /** Custom icon URL for the signal source (e.g. asset icon_url) — used by MeasurePanel and tooltip */
    iconUrl?: string | null;
    /** Asset type code for PNG icon fallback (e.g. "CRYPTO", "ETF") — used by MeasurePanel and tooltip */
    assetType?: string | null;
    /** Line/fill opacity override (0-1). Used for ghost/watermark series. Default 1. */
    opacity?: number;
    /** Area fill opacity for seriesType === 'area'. */
    fillOpacity?: number;
    /** Currency code the signal values are denominated in (e.g. "EUR", "RON") */
    currency?: string;
    /** Flag emoji for the currency (e.g. "🇪🇺") */
    currencyFlag?: string;
    /** Horizontal semantic levels supplied by the backend. */
    referenceLevels?: Array<{
        key: string;
        label: string;
        semantic: string;
        value: number;
    }>;
    /** Semantic background regions supplied by the backend. */
    valueRegions?: Array<{
        key: string;
        label: string;
        semantic: string;
        lower?: number;
        upper?: number;
        includeLower: boolean;
        includeUpper: boolean;
        lineStyle?: {
            lineType: 'solid' | 'dashed' | 'dotted';
            lineWidth: number;
            color: string;
            opacity: number;
        };
    }>;
}

// ═══════════════════════════════════════════════════════════════════════════════
// CALENDAR-RETURN POINT — What the chart's tooltip reads about one calendar point
// ═══════════════════════════════════════════════════════════════════════════════

export type CalendarReturnPointStatus = 'available' | 'missing_reference' | 'invalid_current_price' | 'invalid_reference_price';

export interface CalendarReturnPointContext {
    status: CalendarReturnPointStatus;
    referenceTargetDate: string;
    currentPriceDate: string;
    referencePriceDate: string | null;
    currentFxDate: string | null;
    referenceFxDate: string | null;
}
