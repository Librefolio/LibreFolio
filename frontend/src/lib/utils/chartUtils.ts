/**
 * Chart utility functions shared across AssetCard, FxCard, and ChartSettingsModal.
 */
import type {LineDataPoint} from '$lib/components/charts/LineChart.svelte';

/**
 * Normalize data points to percentage change from first value (p0).
 * Formula: ((value - p0) / p0) * 100
 * Returns the original array unchanged if empty or p0 === 0.
 */
export function normalizeToPercentage(data: LineDataPoint[]): LineDataPoint[] {
    if (data.length === 0) return data;
    const p0 = data[0].value;
    if (p0 === 0) return data;
    return data.map((d) => ({...d, value: ((d.value - p0) / p0) * 100}));
}
