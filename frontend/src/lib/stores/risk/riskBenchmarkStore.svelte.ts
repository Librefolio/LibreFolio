/**
 * The benchmark L3 measures against — one choice, shared by every scope.
 *
 * L3 asks "am I being paid for this risk", and the answer is only meaningful
 * next to something. If the Dashboard compared against MSCI World while a broker
 * page compared against the S&P 500, the two pages would stop being comparable —
 * and comparability across scopes is the whole property the four levels exist to
 * build. So the benchmark is deliberately **not** component state: it lives here,
 * at module scope, and every mount reads the same value.
 *
 * Three disciplines are borrowed from `chartSettingsStore`, each for a reason
 * that has already cost someone an afternoon:
 * - **`browser` guard**: this module is imported during SSR, where `localStorage`
 *   does not exist and touching it throws while rendering;
 * - **user-scoped key**: a benchmark is a personal choice, and a shared key would
 *   hand one user's choice to the next account on the same browser;
 * - **session reset**: logging out and back in as someone else must not inherit
 *   the previous reader's comparison.
 */
import {browser} from '$app/environment';

import {getClientSessionUserId, registerClientSessionReset} from '$lib/stores/app/clientSession';

const STORAGE_BASE_KEY = 'risk_benchmark_asset';

function storageKey(): string {
    return `lf_${getClientSessionUserId() ?? 'anon'}_${STORAGE_BASE_KEY}`;
}

let assetId = $state<number | null>(null);
/** The key the current value was hydrated from, so a user switch re-reads. */
let hydratedKey: string | null = null;

/** A stored id, or null for anything that is not a usable asset id. */
function parse(raw: string | null): number | null {
    if (raw === null) return null;
    const parsed = Number(raw);
    // A benchmark is an asset id: integral and positive. Anything else is a
    // corrupted or hand-edited entry, and silently trusting it would send a
    // nonsense `comparison_asset_id` to the backend on the next run.
    if (!Number.isInteger(parsed) || parsed <= 0) return null;
    return parsed;
}

function hydrate(): void {
    if (!browser) return;
    const key = storageKey();
    if (hydratedKey === key) return;
    hydratedKey = key;
    try {
        assetId = parse(localStorage.getItem(key));
    } catch {
        // A browser with storage disabled is not a broken app: it is an app
        // without persistence, which still has to render.
        assetId = null;
    }
}

export const riskBenchmark = {
    /** The shared benchmark, or null when the reader has never chosen one. */
    get assetId(): number | null {
        hydrate();
        return assetId;
    },

    /** Choose the benchmark for every scope at once. */
    set(next: number | null): void {
        hydrate();
        const value = Number.isInteger(next) && (next as number) > 0 ? next : null;
        assetId = value;
        if (!browser) return;
        try {
            if (value === null) localStorage.removeItem(storageKey());
            else localStorage.setItem(storageKey(), String(value));
        } catch {
            // Persistence is best-effort; the in-memory choice still holds for
            // this session, and both pages still agree, which is the point.
        }
    },
};

registerClientSessionReset('riskBenchmarkStore', () => {
    hydratedKey = null;
    assetId = null;
    hydrate();
});
