/**
 * FX Conversion Helper — compute implied rate, spread, and tooltip data
 * for FX_CONVERSION transaction pairs.
 *
 * @module utils/fxConversionHelper
 */

import type {FxDataPoint} from '$lib/stores/fxStoreRegistry';

export interface FxConversionInfo {
    impliedRate: number;
    /** Currency being converted FROM */
    base: string;
    /** Currency being converted TO */
    quote: string;
}

export interface FxSpreadInfo {
    /** implied - market */
    absolute: number;
    /** (implied - market) / market * 100 */
    percent: number;
}

export interface FxTooltipData {
    impliedRate: number;
    base: string;
    quote: string;
    marketRate: number | null;
    marketDate: string | null;
    staleDays: number | null;
    spread: FxSpreadInfo | null;
}

/**
 * Compute implied FX rate from two transaction amounts.
 *
 * @param amountFrom - Amount leaving (pass absolute value or signed — abs is taken)
 * @param currencyFrom - Currency of the "from" side
 * @param amountTo - Amount arriving (pass absolute value or signed — abs is taken)
 * @param currencyTo - Currency of the "to" side
 * @returns FxConversionInfo or null if amounts are invalid (zero/missing)
 */
export function computeFxConversionInfo(amountFrom: number, currencyFrom: string, amountTo: number, currencyTo: string): FxConversionInfo | null {
    const absFrom = Math.abs(amountFrom);
    const absTo = Math.abs(amountTo);
    if (absFrom === 0 || absTo === 0) return null;
    if (currencyFrom === currencyTo) return null;
    return {
        impliedRate: absTo / absFrom,
        base: currencyFrom,
        quote: currencyTo,
    };
}

/**
 * Compute spread between implied and market rate.
 */
export function computeSpread(impliedRate: number, marketRate: number): FxSpreadInfo {
    const absolute = impliedRate - marketRate;
    const percent = marketRate !== 0 ? (absolute / marketRate) * 100 : 0;
    return {absolute, percent};
}

/**
 * Build structured tooltip data from FxDataPoint (or lack thereof).
 * Handles 3 cases: fresh rate, stale rate, no rate available.
 *
 * @param info - Implied rate info from computeFxConversionInfo
 * @param fxPoint - Result from lookupFxRate: FxDataPoint (has rate), null (pair not configured), undefined (pending/not fetched)
 */
export function buildFxTooltipData(info: FxConversionInfo, fxPoint: FxDataPoint | null | undefined): FxTooltipData {
    if (fxPoint === null || fxPoint === undefined) {
        return {
            impliedRate: info.impliedRate,
            base: info.base,
            quote: info.quote,
            marketRate: null,
            marketDate: null,
            staleDays: null,
            spread: null,
        };
    }
    const marketRate = fxPoint.rate;
    const staleDays = fxPoint.backwardFillInfo?.daysBack ?? null;
    const marketDate = fxPoint.backwardFillInfo?.actualRateDate ?? null;
    const spread = marketRate !== 0 ? computeSpread(info.impliedRate, marketRate) : null;
    return {
        impliedRate: info.impliedRate,
        base: info.base,
        quote: info.quote,
        marketRate,
        marketDate,
        staleDays,
        spread,
    };
}

/**
 * Build tooltip HTML for FX conversion info display.
 * Shared between BulkModal banner and FormModal info marker.
 */
export function buildFxTooltipHtml(data: FxTooltipData, t: (key: string, opts?: any) => string): string {
    let html = `<div class="space-y-1">`;
    html += `<div><span class="text-gray-400">${t('transactions.fxInfo.impliedRate')}:</span> <strong>${data.impliedRate.toFixed(4)}</strong></div>`;
    if (data.marketRate != null) {
        html += `<div><span class="text-gray-400">${t('transactions.fxInfo.marketRate')}:</span> ${data.marketRate.toFixed(4)}`;
        if (data.staleDays != null && data.staleDays > 0) {
            html += ` <span class="text-amber-400">⚠️ ${t('transactions.fxInfo.stale', {values: {days: data.staleDays}})}</span>`;
        }
        if (data.marketDate) html += ` <span class="text-gray-500">(${data.marketDate})</span>`;
        html += `</div>`;
        if (data.spread) {
            const sign = data.spread.absolute >= 0 ? '+' : '';
            html += `<div><span class="text-gray-400">${t('transactions.fxInfo.spread')}:</span> ${sign}${data.spread.absolute.toFixed(4)} (${sign}${data.spread.percent.toFixed(2)}%)</div>`;
        }
    } else {
        html += `<div class="text-gray-500 italic">${t('transactions.fxInfo.marketNotAvailable')}</div>`;
    }
    html += `</div>`;
    return html;
}
