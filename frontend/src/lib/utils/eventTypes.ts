/**
 * Shared event type utilities — options builder for event type selects/pickers.
 * Used by AssetDataEditorSection (all 5 types) and EventCreateMiniModal (3 TX-compatible types).
 */
import {getEventTypeEmoji} from '$lib/stores/transactionTypeStore';

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
