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

// =============================================================================
// MKDOCS DOCUMENTATION DEEP-LINKS
// =============================================================================

/**
 * Map a transaction type to the relative slug under
 * `mkdocs/financial-theory/instruments/transaction-types/`. Several enum
 * values share a doc page (BUY+SELL → `buy-sell`,
 * DEPOSIT+WITHDRAWAL → `deposit-withdrawal`). Types without a dedicated
 * page fall back to the section index.
 */
const TX_TYPE_DOC_SLUG: Record<string, string> = {
    BUY: 'buy-sell',
    SELL: 'buy-sell',
    DEPOSIT: 'deposit-withdrawal',
    WITHDRAWAL: 'deposit-withdrawal',
    DIVIDEND: 'dividend',
    INTEREST: 'interest',
    FEE: 'fee',
    TAX: 'fee',
    TRANSFER: 'transfer',
};

/** Languages with a built mkdocs site (besides default `en`). */
const DOC_LANGS = new Set(['it', 'fr', 'es']);

/**
 * Build the absolute mkdocs URL for a transaction type, language-aware.
 *
 * The mkdocs i18n plugin emits `/mkdocs/<lang>/...` for non-default
 * languages and `/mkdocs/...` for the default `en`. The backend serves
 * the bundled site under `/mkdocs/`.
 *
 * In dev mode (Vite at :5173) there is no proxy for `/mkdocs/`, so we
 * construct an absolute URL pointing to the backend at :8000.
 */
export function getTxTypeDocUrl(type: string | null | undefined, lang: string = 'en'): string {
    const slug = TX_TYPE_DOC_SLUG[(type ?? '').toUpperCase()];
    const langPrefix = DOC_LANGS.has(lang) ? `/${lang}` : '';
    const path = slug ? `/mkdocs${langPrefix}/financial-theory/instruments/transaction-types/${slug}/` : `/mkdocs${langPrefix}/financial-theory/instruments/transaction-types/`;

    // In the browser, detect if we're running on the Vite dev server (:5173)
    // and redirect to the backend origin (:8000) which actually serves mkdocs.
    if (typeof window !== 'undefined') {
        const loc = window.location;
        if (loc.port === '5173') {
            return `${loc.protocol}//${loc.hostname}:8000${path}`;
        }
    }
    return path;
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
