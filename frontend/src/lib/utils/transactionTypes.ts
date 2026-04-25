/**
 * Transaction Types — Centralized utility for transaction type constants, icon mapping, and option builders.
 *
 * Mirrors the `assetTypes.ts` pattern (single source of truth for enum + icons).
 * Enum values are derived from the Zod schema in `generated.ts` (auto-generated from backend).
 *
 * Used by: TransactionTypeBadge, TransactionStagingModal, TransactionsTable, future BRIM staging.
 *
 * @module utils/transactionTypes
 */

import {schemas} from '$lib/api/generated';

// =============================================================================
// TRANSACTION TYPES — derived from backend enum via Zod schema
// =============================================================================

export const TX_TYPES = schemas.TransactionType.options;
export type TransactionTypeCode = (typeof TX_TYPES)[number];

/**
 * Map transaction type code → PNG filename in /icons/transactions/.
 * Filenames are kebab-case while enum codes are SCREAMING_SNAKE.
 */
const PNG_MAP: Record<string, string> = {
    BUY: 'buy',
    SELL: 'sell',
    DIVIDEND: 'dividend',
    INTEREST: 'interest',
    DEPOSIT: 'deposit',
    WITHDRAWAL: 'withdrawal',
    FEE: 'fee',
    TAX: 'tax',
    TRANSFER: 'transfer',
    FX_CONVERSION: 'fx-conversion',
    ADJUSTMENT: 'adjustment',
};

/**
 * Get the icon URL for a transaction type.
 *
 * Falls back to 'adjustment.png' for unknown types (visually neutral).
 */
export function getTransactionTypeIconUrl(type: string | null | undefined): string {
    const filename = PNG_MAP[(type ?? '').toUpperCase()] ?? 'adjustment';
    return `/icons/transactions/${filename}.png`;
}

/**
 * Build SelectOption[] for transaction type dropdowns.
 * Each option includes an icon from the PNG map.
 */
export function buildTransactionTypeOptions(t: (key: string) => string): Array<{
    value: string;
    label: string;
    icon: string;
}> {
    return TX_TYPES.map((tt) => ({
        value: tt,
        label: t(`transactions.types.${tt}`) || tt,
        icon: getTransactionTypeIconUrl(tt),
    }));
}
