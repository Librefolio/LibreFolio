/**
 * echartsTooltipHelpers.ts — Shared tooltip and lifecycle utilities for ALL ECharts charts.
 *
 * Used by: GrowthChart, AllocationHistoryChart, LineChart, CandlestickChart, AllocationPieChart.
 * Provides consistent tooltip styling, HTML builders, and top-N grouping across the app.
 */

// =============================================================================
// Tooltip Theme
// =============================================================================

export interface TooltipTheme {
    bg: string;
    border: string;
    textColor: string;
    mutedColor: string;
}

/**
 * Get tooltip colors for the current theme.
 */
export function buildTooltipTheme(isDark: boolean): TooltipTheme {
    return {
        bg: isDark ? '#1e293b' : '#ffffff',
        border: isDark ? '#334155' : '#e2e8f0',
        textColor: isDark ? '#e2e8f0' : '#1e293b',
        mutedColor: isDark ? '#94a3b8' : '#64748b',
    };
}

// =============================================================================
// HTML Tooltip Builders
// =============================================================================

/**
 * Build a colored dot span (8×8px circle).
 */
export function buildDot(color: string): string {
    return `<span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${color};margin-right:6px;flex-shrink:0"></span>`;
}

/**
 * Build the tooltip date header line.
 */
export function buildTooltipHeader(date: string, textColor: string): string {
    return `<div style="font-size:11px;color:${textColor};margin-bottom:4px">${date}</div>`;
}

/**
 * Build a single key-value row in the tooltip.
 */
export function buildTooltipRow(label: string, valueHtml: string, dotColor?: string): string {
    const dot = dotColor ? buildDot(dotColor) : '';
    return `<div style="display:flex;justify-content:space-between;gap:16px"><span>${dot}${label}</span><b>${valueHtml}</b></div>`;
}

/**
 * Build a horizontal divider.
 */
export function buildTooltipDivider(borderColor: string): string {
    return `<hr style="border:none;border-top:1px solid ${borderColor};margin:4px 0"/>`;
}

/**
 * Build a top-N + "Other" grouping from items.
 *
 * @param items - Sorted descending by value.
 * @param topN - How many to show individually.
 * @param theme - Tooltip theme for colors.
 * @param otherLabel - Label for the "Other" row (e.g. "Other (5)")
 * @param formatValue - Format a number into display string (default: "X.1%")
 */
export function buildTooltipTopN(
    items: {name: string; value: number; color: string}[],
    topN: number,
    theme: TooltipTheme,
    otherLabel: string,
    formatValue: (v: number) => string = (v) => `${v.toFixed(1)}%`,
): string {
    if (items.length === 0) return '';

    const sorted = [...items].sort((a, b) => b.value - a.value);
    const top = sorted.slice(0, topN);
    const rest = sorted.slice(topN);

    let html = '';
    for (const item of top) {
        html += buildTooltipRow(item.name, formatValue(item.value), item.color);
    }

    if (rest.length > 0) {
        const sumValue = rest.reduce((s, r) => s + r.value, 0);
        const label = `${otherLabel} (${rest.length})`;
        html += buildTooltipRow(label, formatValue(sumValue), theme.mutedColor);
    }

    return html;
}

// =============================================================================
// Chart grid colors (non-tooltip but commonly needed)
// =============================================================================

export interface ChartGridColors {
    textColor: string;
    gridColor: string;
}

/**
 * Standard grid colors for axes and split lines.
 */
export function buildGridColors(isDark: boolean): ChartGridColors {
    return {
        textColor: isDark ? '#94a3b8' : '#64748b',
        gridColor: isDark ? '#1e293b' : '#f1f5f9',
    };
}
