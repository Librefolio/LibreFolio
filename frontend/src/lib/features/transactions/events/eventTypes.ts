/**
 * Shared event type utilities — options builder for event type selects/pickers.
 * Used by AssetDataEditorSection (all 5 types) and EventCreateMiniModal (3 TX-compatible types).
 */
import {getEventTypeEmoji} from '$lib/features/transactions/transactionTypeStore';

/** Event types that can be linked to transactions (event_compatible rule). */
export const EVENT_TYPES_TX_COMPATIBLE = ['DIVIDEND', 'INTEREST', 'PRICE_ADJUSTMENT'] as const;

/** All event types available in the system. */
export const EVENT_TYPES_ALL = ['DIVIDEND', 'INTEREST', 'SPLIT', 'PRICE_ADJUSTMENT', 'MATURITY_SETTLEMENT'] as const;

export interface EventTypeOption {
    value: string;
    label: string;
    emoji: string;
    tooltip?: string;
    docsPath?: string;
}

/**
 * Build event type options for select/dropdown components.
 * @param t - i18n translation function ($t)
 * @param filter - if provided, only include these types (default: all 5)
 */
export function getEventTypeOptions(t: (key: string) => string, filter?: readonly string[]): EventTypeOption[] {
    const types = filter ?? EVENT_TYPES_ALL;
    const docsMap: Record<string, string> = {
        DIVIDEND: 'financial-theory/instruments/asset-events/dividend',
        INTEREST: 'financial-theory/instruments/asset-events/interest',
        SPLIT: 'financial-theory/instruments/asset-events/split',
        PRICE_ADJUSTMENT: 'financial-theory/instruments/asset-events/price-adjustment',
        MATURITY_SETTLEMENT: 'financial-theory/instruments/asset-events/maturity-settlement',
    };
    return types.map((type) => ({
        value: type,
        label: t(`assetDetail.eventType.${type}`) || type.replace(/_/g, ' '),
        emoji: getEventTypeEmoji(type),
        tooltip: t(`assetDetail.eventTypeTooltip.${type}`) || undefined,
        docsPath: docsMap[type],
    }));
}

/** Event types an ADJUSTMENT can link to (`EventTypeMetadata.compatible_tx_types`): a split or a price adjustment. */
export const EVENT_TYPES_FOR_ADJUSTMENT = ['SPLIT', 'PRICE_ADJUSTMENT'] as const;
/** The event types the «new event» modal offers for a transaction of this type. */
export function eventTypesForTx(txType: string): readonly string[] {
    return txType === 'ADJUSTMENT' ? EVENT_TYPES_FOR_ADJUSTMENT : EVENT_TYPES_TX_COMPATIBLE;
}
/** The event type the «new event» modal starts with for a transaction of this type. */
export function defaultEventTypeForTx(txType: string): string {
    if (txType === 'ADJUSTMENT') return 'SPLIT';
    if (txType === 'INTEREST') return 'INTEREST';
    return 'DIVIDEND';
}
