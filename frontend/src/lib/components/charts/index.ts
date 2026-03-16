/**
 * Charts Component Library — Barrel Export
 *
 * Modular ECharts components for LibreFolio.
 *
 * @module components/charts
 */

// Core chart components
export {default as LineChart} from './LineChart.svelte';
export {default as ChartToolbar} from './ChartToolbar.svelte';
export {default as ChartAestheticsSection} from './ChartAestheticsSection.svelte';
export {default as ChartSignalsSection} from './ChartSignalsSection.svelte';
export {default as MeasurePanel} from './MeasurePanel.svelte';

// Composite chart components
export {default as PriceChartCompact} from './PriceChartCompact.svelte';
export {default as PriceChartFull} from './PriceChartFull.svelte';

// Specialized charts
export {default as SemiDonutChart} from './SemiDonutChart.svelte';

// Stubs — TODO Phase 6 (Assets): Implement for OHLC data. Not applicable to daily FX close rates.
export {default as CandlestickChart} from './CandlestickChart.svelte';
export {default as VolumeBar} from './VolumeBar.svelte';

// Re-export types
export type {LineDataPoint} from './LineChart.svelte';
export type {ChartType, ViewMode} from './ChartToolbar.svelte';
