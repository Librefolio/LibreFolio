/**
 * Signal Label — Unified visual representation for chart signal labels.
 *
 * Single source of truth for rendering signal labels with proper icons
 * across MeasurePanel summary table, PriceChartFull tooltip, and
 * ChartSignalsSection cards. Replaces ad-hoc emoji/colorDot logic.
 *
 * @module charts/signalLabel
 */

import {getAssetTypeIconUrl} from '$lib/utils/assetTypes';

// =============================================================================
// Types
// =============================================================================

/**
 * Universal descriptor for "who is this signal" — usable as HTML string
 * or as structured data for Svelte component rendering.
 */
export interface SignalLabelInfo {
    /** Human-readable name (e.g. "Bitcoin", "EUR/USD") */
    label: string;
    /** Custom icon URL (highest priority — e.g. asset icon_url) */
    iconUrl?: string | null;
    /** Asset type code for PNG fallback (e.g. "CRYPTO", "ETF") */
    assetType?: string | null;
    /** Signal overlay color (● dot for comparison signals) */
    color?: string | null;
    /** Show crown emoji for the main/primary series */
    isCrown?: boolean;
}

// =============================================================================
// HTML renderer (for ECharts tooltip, DataTable cells)
// =============================================================================

/**
 * Render a SignalLabelInfo as inline HTML string.
 *
 * Rendering order:
 * 1. Crown `👑` if `isCrown` is true
 * 2. Color dot `●` if `color` is set (always shown — additive with icon)
 * 3. Icon: `iconUrl` → `<img>` (custom) or `assetType` → PNG fallback
 * 4. Label text
 */
export function signalLabelToHtml(info: SignalLabelInfo): string {
    const parts: string[] = [];

    // Crown prefix (fixed-width slot — matches dot slot width for table alignment)
    if (info.isCrown) {
        parts.push('<span style="display:inline-block;width:16px;text-align:center;margin-right:2px;vertical-align:middle">👑</span>');
    }

    // Color dot (fixed-width slot — same width as crown for table alignment)
    if (info.color) {
        parts.push(
            `<span style="display:inline-block;width:16px;text-align:center;margin-right:2px;vertical-align:middle;line-height:0"><span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${info.color}"></span></span>`
        );
    }

    // Icon (priority chain: custom icon_url → asset type PNG)
    if (info.iconUrl) {
        parts.push(
            `<img src="${info.iconUrl}" alt="" style="width:14px;height:14px;border-radius:50%;object-fit:cover;vertical-align:middle;margin-right:3px;display:inline-block;" />`
        );
    } else if (info.assetType) {
        const url = getAssetTypeIconUrl(info.assetType);
        parts.push(
            `<img src="${url}" alt="" style="width:14px;height:14px;object-fit:contain;vertical-align:middle;margin-right:3px;display:inline-block;" />`
        );
    }

    // Label text
    parts.push(`<span style="vertical-align:middle">${info.label}</span>`);

    return parts.join('');
}

/**
 * Plain-text version of signal label (for non-HTML contexts like aria labels).
 */
export function signalLabelToText(info: SignalLabelInfo): string {
    const prefix = info.isCrown ? '👑 ' : '';
    return `${prefix}${info.label}`;
}

// =============================================================================
// Overlay signal info map builder
// =============================================================================

/**
 * Build a Map<label, SignalLabelInfo> from rendered overlay signals.
 * Used by PriceChartFull tooltip and MeasurePanel summary table.
 *
 * Extracts color, iconUrl, and assetType from each RenderedSignal
 * to build a consistent lookup map keyed by signal label.
 */
export function buildOverlaySignalInfoMap(
    overlaySignals: ReadonlyArray<{ label: string; color: string; iconUrl?: string | null; assetType?: string | null }>,
): Map<string, SignalLabelInfo> {
    const map = new Map<string, SignalLabelInfo>();
    for (const sig of overlaySignals) {
        map.set(sig.label, {
            label: sig.label,
            color: sig.color,
            iconUrl: sig.iconUrl,
            assetType: sig.assetType,
        });
    }
    return map;
}

