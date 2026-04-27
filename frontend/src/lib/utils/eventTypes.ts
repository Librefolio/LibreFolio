/**
 * Asset Event Types — Centralized utility for event type emoji mapping.
 *
 * Factored from AssetDataEditorSection to be reusable across components
 * (event tooltips in TransactionsTable, future event badges, etc.).
 *
 * @module utils/eventTypes
 */

/**
 * Map event type code → emoji for visual rendering.
 *
 * Mirrors the mapping in AssetDataEditorSection's `eventTypeOptions`.
 */
const EVENT_TYPE_EMOJI: Record<string, string> = {
    DIVIDEND: '💰',
    INTEREST: '📈',
    SPLIT: '✂️',
    PRICE_ADJUSTMENT: '📊',
    MATURITY_SETTLEMENT: '🏁',
};

/**
 * Get the emoji for an asset event type.
 *
 * Returns the mapped emoji or a generic 📌 for unknown types.
 */
export function getEventTypeEmoji(type: string | null | undefined): string {
    return EVENT_TYPE_EMOJI[(type ?? '').toUpperCase()] ?? '📌';
}
