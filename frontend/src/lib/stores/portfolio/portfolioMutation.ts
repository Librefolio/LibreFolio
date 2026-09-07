export interface PortfolioMutation {
    method: string;
    path: string;
}

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

export function isPortfolioAffectingMutation(method: string | undefined, url: string | undefined): boolean {
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

    if (path === '/api/v1/assets' && ['POST', 'PATCH', 'DELETE'].includes(normalizedMethod)) {
        return true;
    }
    if (normalizedMethod === 'POST' && /^\/api\/v1\/assets\/\d+\/market-data\/wipe$/.test(path)) {
        return true;
    }
    if (path.startsWith('/api/v1/assets/prices')) {
        if (path === '/api/v1/assets/prices/query') return false;
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

    if (path === '/api/v1/fx/currencies/sync' && normalizedMethod === 'POST') return true;
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

export function notifyPortfolioMutation(method: string | undefined, url: string | undefined): void {
    if (!isPortfolioAffectingMutation(method, url)) return;
    const mutation = {
        method: method!.toUpperCase(),
        path: normalizedPath(url!),
    };
    for (const [key, listener] of listeners) {
        try {
            listener(mutation);
        } catch (error) {
            console.error(`[portfolioMutation] Listener "${key}" failed`, error);
        }
    }
}
