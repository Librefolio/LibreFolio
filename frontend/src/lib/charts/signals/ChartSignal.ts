/**
 * ChartSignal — Abstract base class for chart overlay signals.
 *
 * All overlay signals (real data from backend, synthetic benchmarks) share this
 * interface. The UI reads `paramDescriptors` from each subclass to dynamically
 * render controls in the ChartSettingsModal.
 *
 * @module charts/signals/ChartSignal
 */

import type {LineDataPoint} from '$lib/components/charts/LineChart.svelte';

// ═══════════════════════════════════════════════════════════════════════════════
// PARAM DESCRIPTORS — Read by ChartSettingsModal to render controls
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * Descriptor for a user-editable parameter of a signal.
 * The ChartSettingsModal reads these from each signal class to dynamically
 * render the appropriate input controls in the OrderableList rows.
 */
export interface SignalParamDescriptor {
    /** Unique key (maps to signal.params[key]) */
    key: string;
    /** Label shown in the UI (i18n key or fallback string) */
    label: string;
    /**
     * Input type for rendering:
     *  - 'number': <input type="number"> with min/max/step/suffix
     *  - 'select': <select> with static options or dynamicOptionsKey
     *  - 'string': <input type="text">
     */
    type: 'number' | 'string' | 'select';
    /** Default value for new instances */
    default: unknown;
    // ── For type === 'number' ──
    min?: number;
    max?: number;
    step?: number;
    /** Suffix shown inline after the input (e.g. "%/yr") */
    suffix?: string;
    // ── For type === 'select' ──
    /** Static options list */
    options?: Array<{value: string; label: string}>;
    /**
     * If set, the modal resolves options at runtime using this key.
     * e.g. 'configuredFxPairs' → modal passes configured pairs as options
     */
    dynamicOptionsKey?: string;
}

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
 * Stored in `ChartSettings.signals[]` and used to recreate class instances
 * via the registry's `signalFromConfig()`.
 *
 * Fields prefixed with '_' in params are transient and excluded by `toConfig()`.
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
}

/** Default color palette — cycled when adding new signals */
export const DEFAULT_SIGNAL_COLORS = [
    '#3b82f6', '#f59e0b', '#8b5cf6', '#ec4899', '#06b6d4', '#84cc16',
];

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
    /**
     * Series rendering type:
     * - 'line' (default): standard line series
     * - 'bar': vertical bars (used for MACD histogram)
     * - 'band': confidence band — requires bandData with upper/lower arrays
     *           (used for Bollinger Bands)
     */
    seriesType?: 'line' | 'bar' | 'band';
    /**
     * Band data for confidence-band rendering (seriesType === 'band').
     * Contains parallel arrays for upper, middle, lower values aligned to `data[].date`.
     */
    bandData?: {
        upper: number[];
        middle: number[];
        lower: number[];
    };
}

// ═══════════════════════════════════════════════════════════════════════════════
// ABSTRACT BASE CLASS
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * Abstract base class for all chart overlay signals.
 *
 * Subclasses MUST define static properties:
 *   - `signalType: string`              — unique registry key
 *   - `displayName: string`             — shown in "Add signal" dropdown
 *   - `icon: string`                    — emoji for the dropdown
 *   - `paramDescriptors: SignalParamDescriptor[]`  — editable params
 *
 * Subclasses MUST implement:
 *   - `computePoints(baseData)` — generate overlay data points (absolute values only)
 *   - `getLabel()` — human-readable label for legend/tooltip
 */
export abstract class ChartSignal {
    readonly id: string;
    style: SignalStyle;
    params: Record<string, unknown>;

    // ── Static metadata (read by UI and registry) ────────────────────────────
    static signalType: string;
    static displayName: string;
    static icon: string;
    static paramDescriptors: SignalParamDescriptor[];
    /** Category for UI grouping in ChartSettingsModal dropdown selectors */
    static category: 'indicator' | 'comparison' | 'benchmark' = 'benchmark';
    /** Y-axis index: 0 = primary (same scale as data), 1 = secondary (independent scale). */
    static yAxisIndex: number = 0;

    constructor(id: string, style: SignalStyle, params: Record<string, unknown>) {
        this.id = id;
        this.style = {...style};
        this.params = {...params};
    }

    /**
     * Day difference between two YYYY-MM-DD date strings.
     * JS Date has no built-in day-diff, so we parse to UTC and divide once.
     * Shared by all subclasses for date arithmetic.
     *
     * Note: JavaScript doesn't have a native "days between" function.
     * We use UTC dates to avoid timezone/DST issues, then integer division.
     */
    protected static daysBetween(dateA: string, dateB: string): number {
        const a = new Date(dateA + 'T00:00:00Z');
        const b = new Date(dateB + 'T00:00:00Z');
        // 1 day = 24 * 60 * 60 * 1000 ms. Math.round handles any floating-point drift.
        return Math.round((b.getTime() - a.getTime()) / 86_400_000);
    }

    /**
     * Compute overlay data points in ABSOLUTE values, aligned to the primary
     * chart's date axis.
     *
     * Subclasses MUST return absolute (raw) values only.
     * The base class `render()` handles the abs→% conversion centrally so that
     * all signals share the same formula: pct = ((value − p0) / p0) × 100.
     *
     * @param baseData  Primary chart data (provides date axis + baseValue reference)
     * @returns         Points aligned to baseData dates (absolute values)
     */
    abstract computePoints(
        baseData: LineDataPoint[],
    ): LineDataPoint[];

    /** Human-readable label for ECharts legend and tooltip */
    abstract getLabel(): string;

    /**
     * Serialize to storable config.
     * Excludes `_resolvedData` (transient runtime data injected by the modal for FxPairSignal).
     * Other `_` prefixed params (e.g. MACD's `_signalColor`, `_signalLineType`)
     * are persistent style overrides and must be included.
     */
    toConfig(): SignalConfig {
        const serializableParams = Object.fromEntries(
            Object.entries(this.params).filter(([k]) => k !== '_resolvedData'),
        );
        return {
            id: this.id,
            signalType: (this.constructor as typeof ChartSignal).signalType,
            params: serializableParams,
            style: {...this.style},
        };
    }

    /**
     * Convenience: compute points and wrap into RenderedSignal format.
     *
     * The % conversion is centralized here: every signal computes absolute
     * values in computePoints(), and render() converts to percentage using
     * the standard formula: pct = ((value − p0) / p0) × 100
     * where p0 is the BASE DATA's first value (not the signal's own first value).
     * This preserves the offset: if a LinearSignal starts at +5% above base,
     * in % mode it shows +5% while the base data shows 0%.
     *
     * Signals on the secondary axis (yAxisIndex=1, e.g. RSI, MACD) are
     * inherently dimensionless — they skip the % conversion entirely.
     * @param baseData  Primary chart data (provides date axis + baseValue reference)
     * @param viewMode
     * @returns RenderedSignal
     */
    render(baseData: LineDataPoint[], viewMode: 'absolute' | 'percentage'): RenderedSignal {
        const absData = this.computePoints(baseData);
        const yAxis = (this.constructor as typeof ChartSignal).yAxisIndex;

        // Signals on secondary axis are already in their own scale — no % conversion
        // For primary-axis signals, use p0 from BASE DATA (not from signal data)
        // so that the offset is preserved in % mode:
        //   signal starts at offset% while base data starts at 0%
        let data = absData;
        if (viewMode === 'percentage' && yAxis === 0 && absData.length > 0 && baseData.length > 0) {
            const p0 = baseData[0].value;
            if (p0 !== 0) {
                data = absData.map(d => ({
                    ...d,
                    value: ((d.value - p0) / p0) * 100,
                }));
            }
        }

        return {
            id: this.id,
            label: this.getLabel(),
            data,
            color: this.style.color,
            lineWidth: this.style.lineWidth,
            lineType: this.style.lineType,
            markerStart: this.style.markerStart,
            markerEnd: this.style.markerEnd,
            yAxisIndex: yAxis,
        };
    }

    /**
     * Render this signal as one or more RenderedSignal items.
     *
     * By default returns a single-element array from `render()`.
     * Composite signals (e.g. MACD: Line + Signal + Histogram) override this
     * to return multiple RenderedSignal items from a single config/card.
     *
     * Callers should always use `renderMulti()` instead of `render()` to
     * support both simple and composite signals uniformly.
     */
    renderMulti(baseData: LineDataPoint[], viewMode: 'absolute' | 'percentage'): RenderedSignal[] {
        const result = this.render(baseData, viewMode);
        return result.data.length > 0 ? [result] : [];
    }
}

