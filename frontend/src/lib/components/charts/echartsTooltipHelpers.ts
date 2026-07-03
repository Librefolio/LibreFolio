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

/**
 * Build tooltip rows by threshold: show items > threshold%, group rest as "Remaining".
 * The actual "Other" category (if present in data) is always shown individually.
 * The grouped "Remaining" row is always last.
 *
 * @param items - All items (unsorted).
 * @param threshold - Minimum % to show individually (e.g. 5).
 * @param theme - Tooltip theme.
 * @param remainingLabel - Label for the grouped row (e.g. "Remaining", "Resto").
 * @param formatValue - Value formatter.
 */
export function buildTooltipByThreshold(
    items: {name: string; value: number; color: string}[],
    threshold: number,
    theme: TooltipTheme,
    remainingLabel: string,
    formatValue: (v: number) => string = (v) => `${v.toFixed(1)}%`,
): string {
    if (items.length === 0) return '';

    const sorted = [...items].sort((a, b) => b.value - a.value);
    const visible = sorted.filter((i) => i.value >= threshold);
    const grouped = sorted.filter((i) => i.value < threshold);

    let html = '';
    for (const item of visible) {
        html += buildTooltipRow(item.name, formatValue(item.value), item.color);
    }

    // Grouped small items — always at the very bottom
    if (grouped.length > 0) {
        const sumValue = grouped.reduce((s, r) => s + r.value, 0);
        const label = `${remainingLabel} (${grouped.length})`;
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

// =============================================================================
// Mobile Tooltip Positioning & Auto-Hide
// =============================================================================

/**
 * ECharts tooltip `position` function that centers horizontally on the cursor
 * and places the tooltip ABOVE the finger on touch devices (with a larger gap).
 *
 * Use as: `tooltip: { position: tooltipPositionAboveFinger, ... }`
 */
export function tooltipPositionAboveFinger(
    point: [number, number],
    _params: unknown,
    _dom: unknown,
    _rect: unknown,
    size: {contentSize: [number, number]; viewSize: [number, number]},
): [number, number] {
    const tooltipW = size.contentSize[0];
    const tooltipH = size.contentSize[1];
    const viewW = size.viewSize[0];

    // Center horizontally on cursor
    let x = point[0] - tooltipW / 2;

    // On touch: larger gap above finger; on desktop: smaller gap
    const isTouch = 'ontouchstart' in window || navigator.maxTouchPoints > 0;
    const gap = isTouch ? 80 : 30;
    let y = point[1] - tooltipH - gap;
    if (y < 0) y = 0;

    // Clamp horizontal to viewport
    if (x < 8) x = 8;
    if (x + tooltipW > viewW - 8) x = viewW - tooltipW - 8;

    return [x, y];
}

/**
 * ECharts tooltip `position` function that places the tooltip to the LEFT or RIGHT
 * of the cursor (whichever side has more space), pinned near the top.
 * This avoids covering area chart labels/emoji directly under the cursor.
 *
 * Use as: `tooltip: { position: tooltipPositionSide, ... }`
 */
export function tooltipPositionSide(
    point: [number, number],
    _params: unknown,
    _dom: unknown,
    _rect: unknown,
    size: {contentSize: [number, number]; viewSize: [number, number]},
): [number, number] {
    const tooltipW = size.contentSize[0];
    const tooltipH = size.contentSize[1];
    const viewW = size.viewSize[0];
    const viewH = size.viewSize[1];

    const gapX = 24;

    // Place on the side with more space
    let x: number;
    if (point[0] > viewW / 2) {
        // Cursor on right half → tooltip on left
        x = point[0] - tooltipW - gapX;
    } else {
        // Cursor on left half → tooltip on right
        x = point[0] + gapX;
    }

    // Clamp horizontal
    if (x < 8) x = 8;
    if (x + tooltipW > viewW - 8) x = viewW - tooltipW - 8;

    // Vertically: pin near top of chart, but not above it
    let y = 8;
    if (y + tooltipH > viewH - 8) y = viewH - tooltipH - 8;
    if (y < 0) y = 0;

    return [x, y];
}

/**
 * Set up touch event handlers on a chart container for mobile tooltip behavior:
 * - Auto-hide tooltip 3s after finger lift
 *
 * Returns a cleanup function to remove listeners.
 *
 * @param container - The chart container element
 * @param getInstance - Function to get the current ECharts instance
 */
export function setupTooltipAutoHide(
    container: HTMLElement,
    getInstance: () => any | undefined,
): () => void {
    let hideTimer: ReturnType<typeof setTimeout> | null = null;

    function clearHideTimer() {
        if (hideTimer) {
            clearTimeout(hideTimer);
            hideTimer = null;
        }
    }

    function onTouchStart() {
        clearHideTimer();
    }

    function onTouchEnd() {
        clearHideTimer();
        const instance = getInstance();
        if (instance) {
            hideTimer = setTimeout(() => {
                instance.dispatchAction({type: 'hideTip'});
            }, 3000);
        }
    }

    container.addEventListener('touchstart', onTouchStart, {passive: true});
    container.addEventListener('touchend', onTouchEnd);
    container.addEventListener('touchcancel', onTouchEnd);

    return () => {
        clearHideTimer();
        container.removeEventListener('touchstart', onTouchStart);
        container.removeEventListener('touchend', onTouchEnd);
        container.removeEventListener('touchcancel', onTouchEnd);
    };
}
