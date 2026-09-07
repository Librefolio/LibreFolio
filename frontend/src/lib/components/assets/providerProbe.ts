/**
 * providerProbe — pure helpers for the provider "Test Configuration" (probe) flow.
 *
 * These functions were inlined in two components that both drive the same probe
 * endpoint: `ProviderAssignmentSection` (which renders the per-operation results)
 * and `AssetModal.autoTriggerProbe` (which only needs the pass/fail verdict).
 * They duplicated the soft-failure classifier verbatim. Extracting them here:
 *
 *   - removes the duplication (one classifier, two callers);
 *   - makes every branch unit-testable without mounting a component or a jsdom
 *     Tooltip, which only renders on a real `mouseenter` + layout.
 *
 * Nothing here reads a Svelte store or `$_(...)`: the two functions that need
 * human labels take them as arguments, so the module stays i18n-free and the
 * caller keeps ownership of the translated strings.
 */
import {getCurrencyInfo} from '$lib/stores/reference/currencyStore';

/**
 * Provider error codes that mean "config is fine, just no data here" — a warning,
 * not a hard failure. `NO_DATA` (e.g. a fund whose NAV isn't dated today) and
 * `NOT_IMPLEMENTED` (the provider doesn't offer this operation) must never gate
 * the "Save Without Testing?" warning.
 */
export const SOFT_FAIL_CODES = new Set(['NO_DATA', 'NOT_IMPLEMENTED']);

/**
 * Classify whether a failed operation is a *soft* failure (a warning) rather than
 * a real error. A structured `errorCode` is authoritative; the message-text
 * heuristic is a fallback for providers that don't set one.
 */
export function isSoftProbeFailure(detail: string | undefined, errorCode?: string | null): boolean {
    if (errorCode && SOFT_FAIL_CODES.has(errorCode.toUpperCase())) return true;
    if (!detail) return false;
    const lower = detail.toLowerCase();
    return lower.includes('not_implemented') || lower.includes('not supported') || lower.includes('not implemented');
}

/** Shape of one operation result inside a probe response (current_price / history). */
export interface ProbeOperation {
    success?: boolean;
    error?: string | null;
    error_code?: string | null;
}

/**
 * True when a probe operation failed with a *real* error (not a soft failure and
 * not a success). Used by the auto-probe verdict: a probe is "passed" unless some
 * operation is a real error.
 */
export function isRealProbeError(op: ProbeOperation | null | undefined): boolean {
    if (!op || op.success) return false;
    return !isSoftProbeFailure(op.error ?? undefined, op.error_code);
}

/** Generate a short, human-readable one-liner from a raw provider error detail. */
export function summarizeProbeError(detail: string | undefined): string {
    if (!detail) return 'Error';
    const lower = detail.toLowerCase();
    if (lower.includes('not_implemented') || lower.includes('not supported') || lower.includes('not implemented')) return 'Not supported';
    if (lower.includes('timeout')) return 'Connection timeout';
    if (lower.includes('not_found') && lower.includes('selector')) return 'Selector not found';
    if (lower.includes('not_found')) return 'Element not found';
    if (lower.includes('http_error') || lower.includes('http error')) return 'HTTP error';
    if (lower.includes('request_error') || lower.includes('request failed')) return 'Connection failed';
    if (lower.includes('parse_error')) return 'Parse error';
    if (lower.includes('missing_params')) return 'Missing parameters';
    return detail.length > 60 ? detail.slice(0, 60) + '…' : detail;
}

/** Format a currency code with flag + symbol for tooltip/label display. */
export function formatCurrencyForTooltip(code: string | undefined): string {
    if (!code) return '';
    const info = getCurrencyInfo(code);
    const flag = info.flag_emoji && info.flag_emoji !== '🏳️' ? info.flag_emoji : '';
    const symbol = info.symbol && info.symbol !== code ? info.symbol : '';
    return [flag, code, symbol].filter(Boolean).join(' ');
}

/** Minimal view of a test result needed to render its rich HTML tooltip. */
export interface ProbeTooltipResult {
    success: boolean;
    detail?: string;
    priceValue?: number;
    priceCurrency?: string;
    priceDate?: string;
    samplePrices?: Array<{date: string; close: number}>;
}

/** Translated labels the tooltip HTML needs (kept out of this pure module). */
export interface ProbeTooltipLabels {
    date: string;
    currentPrice: string;
}

/**
 * Build the rich HTML tooltip for a probe result — a single-row table for a
 * current price, a multi-row table for a history sample, the raw detail
 * otherwise. Kept as a pure string builder so both the branch shape and the
 * escaping can be asserted directly.
 */
export function buildProbeTooltipHtml(result: ProbeTooltipResult, labels: ProbeTooltipLabels): string {
    if (!result.success) return result.detail ?? 'Error';

    const thStyle = 'text-align:left;padding:2px 8px;font-weight:600;border-bottom:1px solid rgba(255,255,255,0.2);';
    const tdStyle = 'padding:2px 8px;';
    const tdRight = 'padding:2px 8px;text-align:right;font-variant-numeric:tabular-nums;';

    // Current Price tooltip — single-row table
    if (result.priceValue !== undefined) {
        const ccyLabel = formatCurrencyForTooltip(result.priceCurrency);
        let html = '<table style="font-size:12px;border-collapse:collapse;">';
        html += `<tr><th style="${thStyle}">📅 ${labels.date}</th><th style="${thStyle}">💰 ${labels.currentPrice}</th></tr>`;
        html += `<tr><td style="${tdStyle}">${result.priceDate ?? '—'}</td>`;
        html += `<td style="${tdRight}">${Number(result.priceValue).toFixed(2)} ${ccyLabel}</td></tr>`;
        html += '</table>';
        return html;
    }

    // History tooltip — multi-row table with sample prices
    if (result.samplePrices && result.samplePrices.length > 0) {
        const ccyLabel = formatCurrencyForTooltip(result.priceCurrency);
        let html = '<table style="font-size:12px;border-collapse:collapse;">';
        html += `<tr><th style="${thStyle}">📅 ${labels.date}</th><th style="${thStyle}">💰 Close${ccyLabel ? ` (${ccyLabel})` : ''}</th></tr>`;
        for (const p of result.samplePrices) {
            html += `<tr><td style="${tdStyle}">${p.date}</td><td style="${tdRight}">${Number(p.close).toFixed(2)}</td></tr>`;
        }
        html += '</table>';
        return html;
    }

    return result.detail ?? '—';
}
