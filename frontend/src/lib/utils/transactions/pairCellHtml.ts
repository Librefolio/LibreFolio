/**
 * From/To cells of a linked pair, in the bulk editor's visual language (D3, plan 31_brimDegiro).
 *
 * The markup mirrors `renderDualHtml` of `TransactionBulkModal.svelte`, so a pair reads the same in
 * the import wizard and in the editor; the implied-rate chip mirrors its promote suggestion.
 * Callers pass already-escaped HTML for the values.
 */
import {computeFxConversionInfo} from '$lib/utils/currency/fxConversionHelper';
import {formatCurrencyCodeHtml} from '$lib/utils/currency/currencyFormat';

/** Two lines, "From:" and "To:", with labels padded to the longer one. */
export function renderFromToHtml(fromHtml: string, toHtml: string, labels: {from: string; to: string}): string {
    const maxCh = Math.max(labels.from.length, labels.to.length) + 2;
    const labelCls = 'inline-block text-gray-400 dark:text-gray-500 font-medium';
    const labelStyle = `min-width:${maxCh}ch`;
    return `<div class="flex flex-col gap-0.5 text-xs leading-tight min-h-[2.5rem] justify-center"><span><span class="${labelCls}" style="${labelStyle}">${labels.from}:</span> ${fromHtml}</span><hr class="border-gray-200 dark:border-gray-600 my-0.5"/><span><span class="${labelCls}" style="${labelStyle}">${labels.to}:</span> ${toHtml}</span></div>`;
}

/** `USD → EUR @ 0.8554`: the rate the two amounts imply (|to| / |from|); empty when it cannot be computed. */
export function renderImpliedRateHtml(from: {code: string; amount: number}, to: {code: string; amount: number}): string {
    if (from.code === to.code) return '';
    const info = computeFxConversionInfo(from.amount, from.code, to.amount, to.code);
    if (!info) return '';
    return `<span class="inline-flex items-center gap-0.5 text-xs text-violet-600 dark:text-violet-400" data-testid="import-tx-pair-rate">${formatCurrencyCodeHtml(info.base)}<span>→</span>${formatCurrencyCodeHtml(info.quote)}<span class="font-mono">@ ${info.impliedRate.toFixed(4)}</span></span>`;
}
