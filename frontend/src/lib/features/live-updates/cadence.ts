/**
 * How often the live prices refresh, and when they pause — decision 31 of the developer (15/10/2026).
 *
 * The list of assets refreshes every minute, the page of one asset every 30 seconds: that is the page where a fresh
 * price matters. Both pause while the tab is hidden and after two minutes without mouse, keyboard or touch, and resume
 * by themselves as soon as the page is used again (`activePolling.ts`).
 *
 * @module lib/features/live-updates/cadence
 */

/** No input for this long, and the live prices stop refreshing until the next one. */
export const LIVE_UPDATES_IDLE_MS = 2 * 60_000;

/** Cadence of the live prices on the list of assets. */
export const ASSET_LIST_LIVE_INTERVAL_MS = 60_000;

/** Cadence of the live price on the page of one asset. */
export const ASSET_DETAIL_LIVE_INTERVAL_MS = 30_000;
