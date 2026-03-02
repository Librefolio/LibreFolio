/**
 * Charts Component Library — Barrel Export
 *
 * Modular ECharts components for LibreFolio.
 *
 * @module components/charts
 */

// Core chart components
export {default as LineChart} from './LineChart.svelte';
export {default as DataZoomBar} from './DataZoomBar.svelte';
export {default as ChartToolbar} from './ChartToolbar.svelte';

// Composite chart components
export {default as PriceChartCompact} from './PriceChartCompact.svelte';
export {default as PriceChartFull} from './PriceChartFull.svelte';

// Specialized charts
export {default as SemiDonutChart} from './SemiDonutChart.svelte';

// Stubs (to be completed in Step 6)
export {default as CandlestickChart} from './CandlestickChart.svelte';
export {default as VolumeBar} from './VolumeBar.svelte';
export {default as MeasureOverlay} from './MeasureOverlay.svelte';
export {default as EditPopup} from './EditPopup.svelte';

// Re-export types
export type {LineDataPoint} from './LineChart.svelte';
export type {ChartType, ViewMode, RangePreset} from './ChartToolbar.svelte';

