/**
 * Chart utility functions shared across AssetCard, FxCard, and ChartSettingsModal.
 */
import type {LineDataPoint} from '$lib/components/charts/LineChart.svelte';

/**
 * Normalize data points to percentage change from first value (p0).
 * Formula: ((value - p0) / p0) * 100
 * Missing values stay marked so LineChart renders them as gaps. The baseline
 * is `base` when it is a finite number other than 0 — the point on the day a
 * sampled series starts, which its first point does not show (Z-29b) — else
 * the first present non-zero value.
 */
export function normalizeToPercentage(data: LineDataPoint[], base?: number | null): LineDataPoint[] {
    if (data.length === 0) return data;
    const usableBase = typeof base === 'number' && Number.isFinite(base) && base !== 0 ? base : undefined;
    const p0 = usableBase ?? data.find((d) => !d.missing && d.value !== 0)?.value;
    if (p0 === undefined) return data;
    return data.map((d) => (d.missing ? d : {...d, value: ((d.value - p0) / p0) * 100}));
}
