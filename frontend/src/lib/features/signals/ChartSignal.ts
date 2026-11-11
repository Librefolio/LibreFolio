/**
 * ChartSignal — Abstract base class for chart overlay signals.
 *
 * All overlay signals (real data from backend, synthetic benchmarks) share this
 * interface. The UI reads `paramDescriptors` from each subclass to dynamically
 * render controls in the ChartSettingsModal.
 *
 * @module features/signals/ChartSignal
 */

import {fromStore} from 'svelte/store';
import {_} from '$lib/i18n';
import type {LineDataPoint} from '$lib/components/charts/LineChart.svelte';
import type {MarkerType, RenderedSignal, SignalAggregationProfile, SignalConfig, SignalStyle} from '$lib/components/charts/chartSignalContract';
import {SIGNAL_DEFAULT_PALETTE} from '$lib/theme/chartPalettes';

const trackCatalogue = () => fromStore(_);
/** The catalogue's formatter, tracked like `uiLocale()`; created on the first label, so a module that never labels a signal never reads svelte-i18n. */
let catalogue: ReturnType<typeof trackCatalogue> | undefined;

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
     *  - 'boolean': checkbox/toggle
     *  - 'select': <select> with static options or dynamicOptionsKey
     *  - 'string': <input type="text">
     */
    type: 'number' | 'boolean' | 'string' | 'select';
    /** Optional backend-declared semantic control overriding the primitive type. */
    control?: 'comparison_asset';
    /** Default value for new instances */
    default: unknown;
    /** Whether the backend schema requires this parameter. */
    required?: boolean;
    /** Whether numeric input must be an integer. */
    integer?: boolean;
    // ── For type === 'number' ──
    min?: number;
    max?: number;
    step?: number;
    /**
     * Unit shown inline after the input: a token written through `signals.units.<token>` in the
     * interface language (`percentPerYear`, `days`), as the backend's `x-suffix` is; a token with
     * no key is shown as written (`%`).
     */
    suffix?: string;
    // ── For type === 'select' ──
    /** Static options list */
    options?: Array<{value: string; label: string}>;
    /**
     * If set, the modal resolves options at runtime using this key.
     * e.g. 'configuredFxPairs' → modal passes configured pairs as options
     */
    dynamicOptionsKey?: string;
    /**
     * i18n key for tooltip text shown on hover of the ⓘ icon next to the param.
     * May contain $...$ inline LaTeX (rendered by KaTeX in the Tooltip component).
     * e.g. 'chartSettings.tooltips.period'
     */
    tooltip?: string;
    /** Backend output keys affected by this parameter. */
    affectsOutputs?: string[];
}

export type SignalDomain = 'asset' | 'fx';
export type SignalDefinitionSource = 'local' | 'backend';
export type SignalIndicatorGroup = 'trend' | 'momentum' | 'volatility' | 'volume' | 'risk';
export type SignalInputField = 'open' | 'high' | 'low' | 'close' | 'volume';
export type SignalColorRole = 'primary' | 'secondary' | 'positive' | 'negative' | 'neutral' | 'accent';

export interface SignalVisualStyle {
    colorRole: SignalColorRole;
    lineType?: 'solid' | 'dashed' | 'dotted';
    lineWidthDelta: number;
    opacity: number;
    fillOpacity: number;
}

export interface SignalVisualComponent {
    key: string;
    labelKey: string;
    descriptionKey?: string;
    kind: 'line' | 'area' | 'bar' | 'band';
    aggregationProfile: SignalAggregationProfile;
    style: SignalVisualStyle;
    fullyPartitioned: boolean;
}

export interface SignalVisualPartition {
    key: string;
    labelKey: string;
    descriptionKey?: string;
    semantic: string;
    style: SignalVisualStyle;
}

/**
 * Selector/configuration metadata. Unlike SignalConfig, this describes a signal
 * type rather than one saved instance.
 */
export interface SignalDefinition {
    type: string;
    displayName: string;
    displayNameKey?: string;
    descriptionKey?: string;
    icon: string;
    category: 'indicator' | 'comparison' | 'benchmark' | 'measure';
    paramDescriptors: SignalParamDescriptor[];
    docsPath?: string;
    source: SignalDefinitionSource;
    backendSignalCode?: string;
    indicatorGroup?: SignalIndicatorGroup;
    inputPriceFields?: SignalInputField[];
    compatibleDomains?: SignalDomain[];
    visualComponents?: SignalVisualComponent[];
    visualPartitions?: SignalVisualPartition[];
    paramsSchema?: Record<string, unknown>;
    defaultParams?: Record<string, unknown>;
}

/** The chart contract, re-exported: the signals and their users read it from here. */
export type {MarkerType, RenderedSignal, SignalAggregationProfile, SignalConfig, SignalStyle};

/** Default color palette — cycled when adding new signals */
export const DEFAULT_SIGNAL_COLORS = SIGNAL_DEFAULT_PALETTE;

// ═══════════════════════════════════════════════════════════════════════════════
// ABSTRACT BASE CLASS
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * Params the page injects for one render and `toConfig()` never stores: the comparison data
 * (`_resolvedData`) and the comparison's base point (`_basePoint`, AssetComparisonSignal, Z-29d-0).
 */
const TRANSIENT_PARAMS: ReadonlySet<string> = new Set(['_resolvedData', '_basePoint', '_unionAxis']);

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
    // ── Static metadata (read by UI and registry) ────────────────────────────
    static signalType: string;
    static displayName: string;
    static icon: string;
    static paramDescriptors: SignalParamDescriptor[];
    /** Category for UI grouping in ChartSettingsModal dropdown selectors.
     *  'measure' is not shown in dropdowns — managed exclusively by MeasurePanel. */
    static category: 'indicator' | 'comparison' | 'benchmark' | 'measure' = 'benchmark';
    /** Y-axis index: 0 = primary (same scale as data), 1 = secondary (independent scale). */
    static yAxisIndex: number = 0;
    /** Path to MkDocs documentation section, e.g. 'financial-theory/technical-analysis/indicators/ema/' */
    static docsPath?: string;
    readonly id: string;
    style: SignalStyle;
    params: Record<string, unknown>;

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
     * A catalogue text for a label, in the interface language.
     *
     * Read through `fromStore`, the catalogue is tracked the way `uiLocale()` is: a label built
     * inside the `$derived` that renders the overlays is rebuilt when the language changes, its
     * words and its figures together. The figures arrive already written (`formatPercent`,
     * `formatFixed`), so the message only places them.
     */
    protected static text(key: string, values: Record<string, string>): string {
        catalogue ??= trackCatalogue();
        return catalogue.current(key, {values});
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
    abstract computePoints(baseData: LineDataPoint[]): LineDataPoint[];

    /** Human-readable label for ECharts legend and tooltip */
    abstract getLabel(): string;

    /**
     * Serialize to storable config.
     * Excludes the transient runtime data the page injects (`TRANSIENT_PARAMS`: `_resolvedData`,
     * and AssetComparisonSignal's `_basePoint`).
     * Other `_` prefixed params (e.g. MACD's `_signalColor`, `_signalLineType`)
     * are persistent style overrides and must be included.
     */
    toConfig(): SignalConfig {
        const serializableParams = Object.fromEntries(Object.entries(this.params).filter(([k]) => !TRANSIENT_PARAMS.has(k)));
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
                data = absData.map((d) => ({
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
            aggregationProfile: 'last_with_range',
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
