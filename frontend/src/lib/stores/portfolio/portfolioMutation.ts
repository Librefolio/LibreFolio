/**
 * The portfolio signal bus: who must hear that the portfolio changed, or that the user asked to
 * see it fresh.
 *
 * The axios response interceptor (`zodios-client.ts`) notifies every successful response;
 * `isPortfolioAffectingMutation` keeps the writes that change what a portfolio view shows. A sync
 * is a write only when its answer says it wrote something (`points_changed`, `events_changed`), and
 * an asset merge only when it was not a dry run: an answer that cannot be read counts as a write,
 * because a stale view nobody refreshes is worse than one request too many.
 *
 * Listeners (the report, risk and lots caches) mark their answers stale and keep them: a page shows
 * what it has at once and refreshes it in background (page cache, phase 1, decision E1).
 * `requestPortfolioRefresh()` is the same signal for «Aggiorna», with `kind: 'refresh'`.
 */
export type PortfolioMutation = {kind: 'mutation'; method: string; path: string} | {kind: 'refresh'};

export type PortfolioMutationListener = (mutation: PortfolioMutation) => void;

const listeners = new Map<string, PortfolioMutationListener>();

function normalizedPath(url: string): string {
    try {
        const path = new URL(url, 'http://librefolio.local').pathname;
        return path.length > 1 ? path.replace(/\/+$/, '') : path;
    } catch {
        return url.split('?')[0].replace(/\/+$/, '');
    }
}

function asRecord(value: unknown): Record<string, unknown> | null {
    return value !== null && typeof value === 'object' && !Array.isArray(value) ? (value as Record<string, unknown>) : null;
}

function changedCount(value: unknown): number {
    return typeof value === 'number' && Number.isFinite(value) ? value : 0;
}

/** The per-item results of a bulk sync answer, or null when the answer cannot be read. */
function syncResults(data: unknown): Record<string, unknown>[] | null {
    const results = asRecord(data)?.results;
    if (!Array.isArray(results)) return null;
    return results.map((result) => asRecord(result) ?? {});
}

/** `POST /assets/prices/sync` (`FABulkRefreshResponse`): a write when some asset changed a price or an event. */
function assetSyncWrote(data: unknown): boolean {
    const results = syncResults(data);
    if (results === null) return true;
    return results.some((result) => changedCount(result.points_changed) > 0 || changedCount(result.events_changed) > 0);
}

/** `POST /fx/currencies/sync` (`FXSyncBulkResponse`): a write when some rate changed, read from the total or else per pair. */
function fxSyncWrote(data: unknown): boolean {
    const total = asRecord(data)?.total_points_changed;
    if (typeof total === 'number' && Number.isFinite(total)) return total > 0;
    const results = syncResults(data);
    if (results === null) return true;
    return results.some((result) => changedCount(result.points_changed) > 0);
}

/**
 * Whether a successful response changed what a portfolio view shows.
 *
 * @param data — the response body. Read only by the rules that depend on it (the two syncs, the
 *   merge); a missing or unreadable body counts as a write.
 */
export function isPortfolioAffectingMutation(method: string | undefined, url: string | undefined, data?: unknown): boolean {
    if (!method || !url) return false;
    const normalizedMethod = method.toUpperCase();
    if (!['POST', 'PUT', 'PATCH', 'DELETE'].includes(normalizedMethod)) return false;

    const path = normalizedPath(url);

    if (normalizedMethod === 'POST' && (path === '/api/v1/transactions/commit' || path === '/api/v1/transactions/transfers/promote')) {
        return true;
    }

    if ((normalizedMethod === 'POST' || normalizedMethod === 'DELETE') && path === '/api/v1/brokers') {
        return true;
    }
    if ((normalizedMethod === 'PATCH' && /^\/api\/v1\/brokers\/\d+$/.test(path)) || (normalizedMethod === 'PUT' && /^\/api\/v1\/brokers\/\d+\/access$/.test(path))) {
        return true;
    }
    // «Become viewer» and «leave the broker»: the share the Dashboard scales by changes.
    if ((normalizedMethod === 'PATCH' || normalizedMethod === 'DELETE') && /^\/api\/v1\/brokers\/\d+\/access\/me$/.test(path)) {
        return true;
    }

    if (path === '/api/v1/assets' && ['POST', 'PATCH', 'DELETE'].includes(normalizedMethod)) {
        return true;
    }
    if (normalizedMethod === 'POST' && path === '/api/v1/assets/merge') {
        return asRecord(data)?.dry_run !== true;
    }
    if (normalizedMethod === 'POST' && /^\/api\/v1\/assets\/\d+\/market-data\/wipe$/.test(path)) {
        return true;
    }
    if (path.startsWith('/api/v1/assets/prices')) {
        if (path === '/api/v1/assets/prices/query') return false;
        if (path === '/api/v1/assets/prices/sync') return normalizedMethod === 'POST' && assetSyncWrote(data);
        // `/prices/current` stays a write: it persists today's candle (decision E1). What changed is
        // the effect — the views are marked stale and refreshed in background, not thrown away.
        return ['POST', 'DELETE'].includes(normalizedMethod);
    }
    if (path.startsWith('/api/v1/assets/events')) {
        if (path === '/api/v1/assets/events/query') return false;
        return ['POST', 'DELETE'].includes(normalizedMethod);
    }
    if (path.startsWith('/api/v1/assets/provider')) {
        if (path === '/api/v1/assets/provider/probe') return false;
        return ['POST', 'DELETE'].includes(normalizedMethod);
    }

    if (path === '/api/v1/fx/currencies/sync' && normalizedMethod === 'POST') return fxSyncWrote(data);
    if (path === '/api/v1/fx/currencies/rate' && ['POST', 'DELETE'].includes(normalizedMethod)) return true;
    if (path === '/api/v1/fx/providers/routes' && ['POST', 'DELETE'].includes(normalizedMethod)) return true;

    return false;
}

export function registerPortfolioMutationListener(key: string, listener: PortfolioMutationListener): () => void {
    listeners.set(key, listener);
    return () => {
        if (listeners.get(key) === listener) listeners.delete(key);
    };
}

function dispatch(signal: PortfolioMutation): void {
    for (const [key, listener] of listeners) {
        try {
            listener(signal);
        } catch (error) {
            console.error(`[portfolioMutation] Listener "${key}" failed`, error);
        }
    }
}

/** Called by the axios response interceptor with every successful response. */
export function notifyPortfolioMutation(method: string | undefined, url: string | undefined, data?: unknown): void {
    if (!isPortfolioAffectingMutation(method, url, data)) return;
    dispatch({kind: 'mutation', method: method!.toUpperCase(), path: normalizedPath(url!)});
}

/** «Aggiorna»: every portfolio view marks what it holds stale; the page that asked reloads it. */
export function requestPortfolioRefresh(): void {
    dispatch({kind: 'refresh'});
}
