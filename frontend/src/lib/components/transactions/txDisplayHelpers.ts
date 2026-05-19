/**
 * Shared display formatting helpers for transaction modals and tables.
 *
 * Centralizes quantity, cash, and tag rendering logic so it stays
 * consistent across ActionModal, DeleteModal, BulkModal, and Table.
 */

import {formatCurrencyAmountPlain} from '$lib/utils/currencyFormat';

/**
 * Format a quantity string for display:
 * - null / empty / 0 → "—"
 * - positive → "+1,234.5 📈"
 * - negative → "-1,234.5 📉"
 */
export function formatTxQuantity(qty: string | null | undefined): string {
    if (qty == null || qty === '') return '—';
    const n = parseFloat(qty);
    if (isNaN(n) || n === 0) return '—';
    const formatted = n.toLocaleString(undefined, {minimumFractionDigits: 0, maximumFractionDigits: 6});
    const emoji = n > 0 ? ' 📈' : ' 📉';
    return `${n > 0 ? '+' : ''}${formatted}${emoji}`;
}

/**
 * Format a Cash object ({code, amount}) for display:
 * - null/undefined → "—"
 * - otherwise → formatted with sign (e.g. "+$500.00 🇺🇸 USD")
 */
export function formatTxCash(cash: {code: string; amount: string} | null | undefined): string {
    if (!cash) return '—';
    return formatCurrencyAmountPlain(Number(cash.amount), cash.code, {showSign: true});
}


