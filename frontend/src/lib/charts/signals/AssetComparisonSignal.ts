/**
 * AssetComparisonSignal — Overlay signal sourced from another asset's price data.
 *
 * The parent component pre-fetches data and injects it via `params._resolvedData`
 * before calling `computePoints()`, with the names it shows (`_assetDisplayName`, …).
 * Where the chart does not draw the day the comparison starts (a sampled series,
 * Z-29), it also injects `params._basePoint`: the target's point on that day, which
 * the percentage view measures from (Z-29d-0). `toConfig()` leaves out
 * `_resolvedData` and `_basePoint`, data of the moment.
 *
 * Complementary to FxPairSignal: allows overlaying asset prices on any chart
 * (FX or Asset), enabling cross-asset comparison.
 *
 * No maxInstances limit — user can overlay multiple assets on the same chart.
 */

import {ChartSignal, type RenderedSignal, type SignalParamDescriptor} from './ChartSignal';
import type {LineDataPoint} from '$lib/components/charts/LineChart.svelte';
import {getCurrencyInfo} from '$lib/stores/reference/currencyStore';

/** A percentage base: a finite number other than 0. */
function isUsableBase(value: unknown): value is number {
    return typeof value === 'number' && Number.isFinite(value) && value !== 0;
}

export class AssetComparisonSignal extends ChartSignal {
    static override signalType = 'asset-comparison';
    static override displayName = 'Asset';
    static override icon = '📊';
    static category: 'indicator' | 'comparison' | 'benchmark' = 'comparison';

    static override paramDescriptors: SignalParamDescriptor[] = [
        {
            key: 'assetId',
            label: 'Asset',
            type: 'select',
            default: '',
            dynamicOptionsKey: 'configuredAssets',
            tooltip: 'chartSettings.tooltips.assetComparison',
        },
    ];

    computePoints(baseData: LineDataPoint[]): LineDataPoint[] {
        // _resolvedData is injected by the parent before calling computePoints
        const resolvedData = this.params._resolvedData as LineDataPoint[] | undefined;
        if (!resolvedData?.length || !baseData.length) return [];

        // Build date→value lookup, then align to base chart's date axis
        const lookup = new Map(resolvedData.map((d) => [d.date, d.value]));
        const points: LineDataPoint[] = [];
        for (const bd of baseData) {
            const val = lookup.get(bd.date);
            if (val !== undefined && val !== 0) {
                points.push({date: bd.date, value: val});
            }
        }

        return points;
    }

    /**
     * The injected base point (Z-29d-0), or null when there is none or it is unusable:
     * not an object, `missing`, or a `value` that is not a finite number or is 0.
     * Null leaves the percentage view as it was, measured from the own first value.
     */
    private basePoint(): LineDataPoint | null {
        const point = this.params._basePoint;
        if (point === null || typeof point !== 'object') return null;
        const candidate = point as Partial<LineDataPoint>;
        if (candidate.missing === true || !isUsableBase(candidate.value)) return null;
        return point as LineDataPoint;
    }

    /**
     * Override render() for AssetComparisonSignal: in percentage mode, normalize to the
     * signal's OWN first value (not the base chart's p0), or to the injected base point.
     *
     * Rationale: Asset comparison data has a completely different scale
     * (e.g. AAPL ~180 vs GOOGL ~140). Normalizing both curves to their
     * own starting point makes them start at 0% and shows relative movement,
     * which is the only meaningful comparison in percentage mode.
     *
     * On a sampled chart the first drawn day is not the day the comparison starts:
     * there the page injects `_basePoint`, the target's point on that day, and the
     * line is measured from it, as a daily chart measures from its first point (Z-29d-0).
     */
    override render(baseData: LineDataPoint[], viewMode: 'absolute' | 'percentage'): RenderedSignal {
        const absData = this.computePoints(baseData);

        let data = absData;
        if (viewMode === 'percentage' && absData.length > 0) {
            const p0 = this.basePoint()?.value ?? absData[0].value; // the base point, else the OWN first value
            if (p0 !== 0) {
                data = absData.map((d) => ({
                    ...d,
                    value: ((d.value - p0) / p0) * 100,
                }));
            }
        }

        // Determine effective currency: if conversion happened → target currency,
        // otherwise → asset's native currency
        const resolvedData = this.params._resolvedData as LineDataPoint[] | undefined;
        const hasOriginals = resolvedData?.some((d) => d.originalValue !== undefined) ?? false;
        const nativeCurrency = (this.params._assetCurrency as string | undefined) ?? '';
        const targetCurrency = this.params._targetCurrency as string | undefined;
        const currency = hasOriginals && targetCurrency ? targetCurrency : nativeCurrency;
        const currencyFlag = currency ? getCurrencyInfo(currency).flag_emoji : '';

        return {
            id: this.id,
            label: this.getLabel(),
            data,
            color: this.style.color,
            lineWidth: this.style.lineWidth,
            lineType: this.style.lineType,
            markerStart: this.style.markerStart,
            markerEnd: this.style.markerEnd,
            yAxisIndex: 0,
            iconUrl: (this.params._assetIconUrl as string | undefined) ?? null,
            assetType: (this.params._assetType as string | undefined) ?? null,
            currency,
            currencyFlag,
            aggregationProfile: 'last_with_range',
        };
    }

    /**
     * Override renderMulti: produce a ghost signal showing original (unconverted)
     * values when FX conversion is active.
     *
     * - Abs mode: ghost = raw original values on yAxisIndex 0
     * - % mode: ghost = normalized to own p0 on yAxisIndex 0, or to the base point's
     *   `originalValue` when the injected base point has a usable one (Z-29d-0)
     *
     * The ghost uses opacity 0.4 and dashed lines with 💱 label.
     */
    override renderMulti(baseData: LineDataPoint[], viewMode: 'absolute' | 'percentage'): RenderedSignal[] {
        const main = this.render(baseData, viewMode);
        if (main.data.length === 0) return [];

        const results: RenderedSignal[] = [main];

        // Ghost: when original values are present (FX conversion active)
        const resolvedData = this.params._resolvedData as LineDataPoint[] | undefined;
        if (resolvedData?.length) {
            const hasOriginals = resolvedData.some((d) => d.originalValue !== undefined);
            if (hasOriginals) {
                // Build aligned original points using the same date alignment as computePoints
                const lookup = new Map(resolvedData.map((d) => [d.date, d]));
                const origPoints: LineDataPoint[] = [];
                for (const bd of baseData) {
                    const rd = lookup.get(bd.date);
                    if (rd?.originalValue !== undefined && rd.originalValue !== 0) {
                        origPoints.push({date: bd.date, value: rd.originalValue});
                    }
                }

                if (origPoints.length > 0) {
                    let ghostData: LineDataPoint[];
                    if (viewMode === 'percentage') {
                        // Normalize to the base point's original when it has a usable one, else to own p0
                        const baseOriginal = this.basePoint()?.originalValue;
                        const origP0 = isUsableBase(baseOriginal) ? baseOriginal : origPoints[0].value;
                        ghostData = origP0 !== 0 ? origPoints.map((d) => ({...d, value: ((d.value - origP0) / origP0) * 100})) : origPoints;
                    } else {
                        // Abs mode: raw original values
                        ghostData = origPoints;
                    }

                    const origCurrency = resolvedData.find((d) => d.originalCurrency)?.originalCurrency ?? '';
                    const origFlag = resolvedData.find((d) => (d as any).originalCurrencyFlag)?.originalCurrencyFlag ?? '';
                    const ghostLabelText = origFlag ? `💱 ${this.getLabel()} (${origFlag} ${origCurrency})` : `💱 ${this.getLabel()} (${origCurrency})`;
                    results.push({
                        id: `${this.id}__ghost`,
                        label: ghostLabelText,
                        data: ghostData,
                        color: this.style.color,
                        lineWidth: 1,
                        lineType: 'dashed',
                        markerStart: null,
                        markerEnd: null,
                        yAxisIndex: 0,
                        opacity: 0.8,
                        currency: origCurrency,
                        currencyFlag: origFlag,
                        aggregationProfile: 'last_with_range',
                    });
                }
            }
        }

        return results;
    }

    getLabel(): string {
        const displayName = this.params._assetDisplayName as string | undefined;
        if (displayName) return displayName;
        const assetId = this.params.assetId;
        if (assetId) return ChartSignal.text('chartSettings.signals.assetFallback', {id: String(assetId)});
        return ChartSignal.text('common.asset', {});
    }
}
