/**
 * Categorical palettes and colour scales of the charts — the one home for them.
 *
 * Each list is the one a chart drew with before it moved here, entry for entry and in the same order, so moving changed
 * no pixel. The lists stay distinct where they overlap — the allocation pie and the allocation history order their
 * colours differently, the semi-donut has no dark version — so the designer sees them side by side and decides.
 *
 * Order matters: charts pick colours by position, and a light entry pairs with the dark entry at the same index, so a
 * category keeps its colour when the theme changes. A pair is read with `themed(pair, dark)` (`./themePair`).
 *
 * @module lib/theme/chartPalettes
 */

import type {ThemePair} from './themePair';

/** Allocation pie and donut: one colour per family, its subtypes shaded from it (`shadeForDepth`). 14 slots. */
export const ALLOCATION_PIE_PALETTE: ThemePair<string[]> = {
    light: ['#1a4031', '#2563eb', '#7c3aed', '#dc2626', '#d97706', '#0d9488', '#be185d', '#4f46e5', '#059669', '#ea580c', '#6366f1', '#0891b2', '#ca8a04', '#9333ea'],
    dark: ['#4ade80', '#60a5fa', '#a78bfa', '#f87171', '#fbbf24', '#2dd4bf', '#f472b6', '#818cf8', '#34d399', '#fb923c', '#a5b4fc', '#22d3ee', '#facc15', '#c084fc'],
};

/** The ownership semi-donut: the first eight entries of the pie's light palette. There is no dark version: both themes draw these. */
export const SEMI_DONUT_PALETTE: string[] = ['#1a4031', '#2563eb', '#7c3aed', '#dc2626', '#d97706', '#0d9488', '#be185d', '#4f46e5'];

/** Allocation history: one stacked area per category, 14 slots. Why 14, and what happens past them: `AllocationHistoryChart.svelte`. */
export const ALLOCATION_HISTORY_PALETTE: ThemePair<string[]> = {
    light: ['#1a4031', '#3b82f6', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4', '#84cc16', '#ec4899', '#f97316', '#14b8a6', '#6366f1', '#a3a3a3', '#a21caf', '#7e22ce'],
    dark: ['#4ade80', '#60a5fa', '#fbbf24', '#f87171', '#a78bfa', '#22d3ee', '#a3e635', '#f472b6', '#fb923c', '#2dd4bf', '#818cf8', '#d4d4d4', '#e879f9', '#c084fc'],
};

/** Default line colours of a new chart signal; `registry.ts` picks the one farthest in hue from those in use. The same in both themes. */
export const SIGNAL_DEFAULT_PALETTE: string[] = ['#3b82f6', '#f59e0b', '#8b5cf6', '#ec4899', '#06b6d4', '#84cc16'];

/** World maps, from no weight to the most: one green hue. The dark ramp is not a Tailwind green. */
export const GEO_CHOROPLETH_SCALE: ThemePair<string[]> = {
    light: ['#f0fdf4', '#bbf7d0', '#86efac', '#4ade80', '#22c55e', '#16a34a'],
    dark: ['#1e3a2f', '#22543d', '#276749', '#2f855a', '#38a169', '#48bb78'],
};

/** Correlation from −1 to +1: red, a neutral that follows the card, blue. */
export const CORRELATION_SCALE: ThemePair<string[]> = {
    light: ['#b91c1c', '#f8fafc', '#1d4ed8'],
    dark: ['#b91c1c', '#334155', '#1d4ed8'],
};

/** The Growth chart's P&L broker lines: distinct hues, cycled by the broker's index. */
export const GROWTH_BROKER_PALETTE: ThemePair<string>[] = [
    {light: '#2563eb', dark: '#60a5fa'}, // blue
    {light: '#d97706', dark: '#fbbf24'}, // amber
    {light: '#7c3aed', dark: '#a78bfa'}, // violet
    {light: '#db2777', dark: '#f472b6'}, // pink
    {light: '#0891b2', dark: '#22d3ee'}, // cyan
    {light: '#65a30d', dark: '#a3e635'}, // lime
];
