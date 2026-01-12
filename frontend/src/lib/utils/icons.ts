/**
 * Icon utilities for transactions and asset types.
 *
 * Maps enum values to their corresponding icon paths.
 */

/**
 * Get the icon path for a transaction type.
 * @param type - Transaction type (e.g., 'BUY', 'SELL', 'FX_CONVERSION')
 * @returns Path to the icon image
 */
export function getTransactionIcon(type: string): string {
    const normalized = type.toLowerCase().replace(/_/g, '-');
    return `/icons/transactions/${normalized}.png`;
}

/**
 * Get the icon path for an asset type.
 * @param type - Asset type (e.g., 'STOCK', 'ETF', 'CRYPTO')
 * @returns Path to the icon image
 */
export function getAssetTypeIcon(type: string): string {
    const normalized = type.toLowerCase().replace(/_/g, '-');
    return `/icons/asset-types/${normalized}.png`;
}

/**
 * Transaction type icons mapping for reference.
 */
export const TRANSACTION_ICONS = {
    ADJUSTMENT: '/icons/transactions/adjustment.png',
    BUY: '/icons/transactions/buy.png',
    DEPOSIT: '/icons/transactions/deposit.png',
    DIVIDEND: '/icons/transactions/dividend.png',
    FEE: '/icons/transactions/fee.png',
    FX_CONVERSION: '/icons/transactions/fx-conversion.png',
    INTEREST: '/icons/transactions/interest.png',
    SELL: '/icons/transactions/sell.png',
    TAX: '/icons/transactions/tax.png',
    TRANSFER_IN: '/icons/transactions/transfer.png',
    TRANSFER_OUT: '/icons/transactions/transfer.png',
    WITHDRAWAL: '/icons/transactions/withdrawal.png',
} as const;

/**
 * Asset type icons mapping for reference.
 */
export const ASSET_TYPE_ICONS = {
    BOND: '/icons/asset-types/bond.png',
    CRYPTO: '/icons/asset-types/crypto.png',
    CROWDFUNDING: '/icons/asset-types/crowdfunding.png',
    ETF: '/icons/asset-types/etf.png',
    FUND: '/icons/asset-types/fund.png',
    HOLD: '/icons/asset-types/hold.png',
    OTHER: '/icons/asset-types/other.png',
    STOCK: '/icons/asset-types/stock.png',
} as const;

