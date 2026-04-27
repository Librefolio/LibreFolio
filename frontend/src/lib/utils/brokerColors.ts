/**
 * Broker Colors — Deterministic, infinite-palette color assignment for brokers.
 *
 * Uses the shared `getIndexColor()` golden-ratio generator from `colors.ts`.
 * The index is the broker's position in the broker list sorted by id ascending,
 * which gives a stable assignment for the lifetime of the broker list.
 *
 * Used by: TransactionsTable (color band + broker badge), TransactionStagingModal,
 *          future BRIM staging.
 *
 * @module utils/brokerColors
 */

import {getIndexColor, type ColorSet} from './colors';

/** Minimal shape required for broker color resolution and icon display. */
export interface BrokerLike {
    id: number;
    name?: string;
    /** Custom icon URL (highest priority in icon chain) */
    icon_url?: string | null;
    /** Portal URL for favicon fallback */
    portal_url?: string | null;
    /** Default import plugin code for plugin-icon fallback */
    default_import_plugin?: string | null;
}

/**
 * Resolve a deterministic ColorSet for a broker.
 *
 * Index is the broker's position in `brokers` sorted by id ascending.
 * If `brokerId` is not in `brokers`, falls back to `getIndexColor(brokerId)`
 * so the color is still deterministic by id even when the broker list is empty
 * (unlikely but defensive).
 */
export function getBrokerColor(brokerId: number, brokers: ReadonlyArray<BrokerLike>): ColorSet {
    const sorted = [...brokers].sort((a, b) => a.id - b.id);
    const idx = sorted.findIndex((b) => b.id === brokerId);
    // Fallback: hash by id directly so the color is stable even without context.
    return getIndexColor(idx >= 0 ? idx : brokerId, /* startHue */ 200);
}
