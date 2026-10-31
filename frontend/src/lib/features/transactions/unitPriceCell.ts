/**
 * unitPriceCell.ts — the read-only «unit price» cell of the transactions table and of the bulk editor (W2-6).
 *
 * One function draws both, so the two grids always say the same thing. The price comes from `rowUnitPrice`, the helper the
 * transaction form uses for its «Total / Unit price» toggle; nothing here calculates. It is shown for a row whose type has a
 * quantity, a cash amount and an asset, and that is not a leg of a pair; for any other row, or when it cannot be calculated,
 * the cell reads «—». The price is public (a quote, not a holding), so the privacy mask leaves it alone.
 *
 * Removable on its own: the two grids each have one column that calls `unitPriceCellHtml`, and the i18n key
 * `transactions.table.unitPrice`.
 */
import {getAssetInfo} from '$lib/stores/reference/assetStore';
import {formatCurrencyAmountHtml} from '$lib/utils/currency/currencyFormat';
import {priceFractionDigits} from '$lib/utils/core/formatFixed';
import {rowUnitPrice, tradeHasUnitPrice} from './form/txTradeAmount';
import {getTypeRule} from './transactionTypeStore';

/** What the cell reads of a row: the saved row's fields, or the bulk editor's draft fields. */
export interface UnitPriceRow {
    type: string;
    quantity?: string | null;
    cash?: {code: string; amount: string} | null;
    asset_id?: number | null;
}

const NO_PRICE = '<span class="text-lf-muted">—</span>';

/** The cell's HTML: the price in the cash currency inside `<span data-testid="{testId}">`, or «—». `isPairLeg`: a leg of a linked pair has no unit price. */
export function unitPriceCellHtml(row: UnitPriceRow, options: {testId: string; isPairLeg: boolean}): string {
    if (options.isPairLeg || !row.cash || row.asset_id == null) return NO_PRICE;
    const rule = getTypeRule(row.type);
    if (rule.requiresPair || !tradeHasUnitPrice(rule)) return NO_PRICE;
    const info = getAssetInfo(row.asset_id);
    if (!info) return NO_PRICE;
    const price = rowUnitPrice({quantity: row.quantity, amount: row.cash.amount, quoteBaseQuantity: info.quote_base_quantity ?? 1});
    if (price === null) return NO_PRICE;
    const {min, max} = priceFractionDigits(price, {minDecimals: 2});
    const html = formatCurrencyAmountHtml(Number(price), row.cash.code, {minFraction: min, maxFraction: max, sensitivity: 'public'});
    return `<span data-testid="${options.testId}">${html}</span>`;
}
