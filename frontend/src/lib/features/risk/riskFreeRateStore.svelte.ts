/**
 * The reader's risk-free rate — one value, shared by every risk page (RN-21; the developer, Q9 b and Q9 bis a).
 *
 * A fixed annual rate, in percent as the reader types it, 0 % until they set one. It is the Sharpe's rate and the
 * threshold of Sortino, Omega and the semi-deviation alike (Q9 bis: one threshold for every «excess» measure), so a
 * card and its neighbour never charge two different rates. Like the shared benchmark (`riskBenchmarkStore`) it lives
 * at module scope, in a user-scoped key of the browser, re-read when the account changes and reset with the session:
 * the backend saves nothing, the value travels with each request.
 */
import {browser} from '$app/environment';

import {getClientSessionUserId, registerClientSessionReset} from '$lib/stores/app/clientSession';

import {parseRiskFreePercent} from './riskFreeRate';

const STORAGE_BASE_KEY = 'risk_free_rate_percent';

function storageKey(): string {
    return `lf_${getClientSessionUserId() ?? 'anon'}_${STORAGE_BASE_KEY}`;
}

/**
 * The value, cached per storage key in a plain variable, never in a `$state`: pages read the rate inside `$derived`
 * (the panel, the lab, a page deriving its signal plan), and the first read — the one that loads the stored value — may
 * not write reactive state there (Svelte forbids it, and the reader then stays on the old value). What tells a reader to
 * read again is `revision`, written only by `set` and by the session reset, outside any derivation.
 */
let cache: {key: string; percent: number} | null = null;
let revision = $state(0);

function readStored(key: string): number {
    if (!browser) return 0;
    try {
        return parseRiskFreePercent(localStorage.getItem(key)) ?? 0;
    } catch {
        // Storage disabled: the app still works, at 0 %.
        return 0;
    }
}

function current(): {key: string; percent: number} {
    const key = storageKey();
    if (cache?.key !== key) cache = {key, percent: readStored(key)};
    return cache;
}

export const riskFreeRate = {
    /** The reader's rate in percent; 0 when never set. */
    get percent(): number {
        void revision;
        return current().percent;
    },

    /** Set the rate for every page at once. A value the engine would refuse is not taken: false, and nothing changes. */
    set(next: number): boolean {
        const value = parseRiskFreePercent(next);
        if (value === null) return false;
        const key = current().key;
        cache = {key, percent: value};
        revision += 1;
        if (!browser) return true;
        try {
            if (value === 0) localStorage.removeItem(key);
            else localStorage.setItem(key, String(value));
        } catch {
            // Best effort: the value holds for this session, and every page still agrees.
        }
        return true;
    },
};

registerClientSessionReset('riskFreeRateStore', () => {
    cache = null;
    revision += 1;
});
