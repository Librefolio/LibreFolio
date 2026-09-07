/**
 * currencyBlocker — parse the structured "currency change blocked" marker the
 * backend returns when an asset still carries market data.
 *
 * When a bulk PATCH changes an asset's currency but prices / events / linked
 * transactions still reference the old one, the per-item result fails with a
 * pipe-delimited token instead of a free-text error, so the modal can render a
 * precise destructive-confirm dialog. Token shape:
 *
 *   CURRENCY_CHANGE_BLOCKED_BY_MARKET_DATA|prices=N|events_manual=M|
 *     events_provider=K|linked_tx=L|oldest=...|newest=...|from=X|to=Y
 *
 * Extracted from `AssetModal.svelte` so the parse (missing keys default to 0/'',
 * malformed chunks are ignored) is unit-testable without a mocked PATCH round-trip.
 *
 * @module components/assets/currencyBlocker
 */

export const CURRENCY_CHANGE_BLOCKED_PREFIX = 'CURRENCY_CHANGE_BLOCKED_BY_MARKET_DATA|';

/** The counts + range carried by the blocker token (everything but the asset id). */
export interface CurrencyChangeBlockerCounts {
    prices: number;
    eventsManual: number;
    eventsProvider: number;
    linkedTx: number;
    oldest: string;
    newest: string;
    from: string;
    to: string;
}

/** True when `message` is the structured blocker marker (and thus parseable below). */
export function isCurrencyChangeBlockedMessage(message: unknown): message is string {
    return typeof message === 'string' && message.startsWith(CURRENCY_CHANGE_BLOCKED_PREFIX);
}

/**
 * Parse the blocker token into structured counts. Robust by construction: chunks
 * without a `key=value` shape are skipped, and any missing key defaults (numbers
 * to 0, strings to ''). The caller supplies the `assetId`, which is not in the token.
 */
export function parseCurrencyChangeBlocker(message: string): CurrencyChangeBlockerCounts {
    const parsed: Record<string, string> = {};
    for (const chunk of message.split('|').slice(1)) {
        const [k, v] = chunk.split('=');
        if (k && v !== undefined) parsed[k] = v;
    }
    return {
        prices: parseInt(parsed.prices || '0', 10),
        eventsManual: parseInt(parsed.events_manual || '0', 10),
        eventsProvider: parseInt(parsed.events_provider || '0', 10),
        linkedTx: parseInt(parsed.linked_tx || '0', 10),
        oldest: parsed.oldest || '',
        newest: parsed.newest || '',
        from: parsed.from || '',
        to: parsed.to || '',
    };
}
