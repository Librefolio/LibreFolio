/**
 * Global Date Range Store — shared source of truth for date range across all pages.
 *
 * Pages (assets list/detail, fx list/detail) read from this store on mount.
 * Changing the date range on ANY page updates the store, so navigating back
 * always shows the latest user-chosen range.
 *
 * Persistence: sessionStorage (survives refresh, not new tabs).
 * URL priority: on full page load, URL params override sessionStorage.
 *               On SPA navigation, the store (in-memory $state) is the source of truth.
 *
 * @module stores/dateRangeStore
 */

const STORAGE_KEY = 'librefolio_dateRange';

function defaultRange(): {start: string; end: string} {
    const end = new Date().toISOString().slice(0, 10);
    const d = new Date();
    d.setMonth(d.getMonth() - 3);
    const start = d.toISOString().slice(0, 10);
    return {start, end};
}

function loadFromStorage(): {start: string; end: string} {
    if (typeof sessionStorage === 'undefined') return defaultRange();
    try {
        const raw = sessionStorage.getItem(STORAGE_KEY);
        if (raw) {
            const parsed = JSON.parse(raw);
            if (parsed.start && parsed.end) return parsed;
        }
    } catch {
        // Corrupted — fall back
    }
    return defaultRange();
}

function saveToStorage(start: string, end: string) {
    if (typeof sessionStorage === 'undefined') return;
    try {
        sessionStorage.setItem(STORAGE_KEY, JSON.stringify({start, end}));
    } catch {
        // Quota exceeded or private mode — ignore
    }
}

/**
 * Determine initial range. Priority:
 * 1. URL params (full page load = user pasted/bookmarked a URL)
 * 2. sessionStorage (returning from refresh within same tab session)
 * 3. Default 3M range
 *
 * This runs once at module load (before any page component mounts).
 * On SPA navigation the module is already loaded → this doesn't re-run.
 */
function resolveInitialRange(): {start: string; end: string} {
    // Check URL params first (only meaningful on full page load)
    if (typeof window !== 'undefined') {
        const params = new URL(window.location.href).searchParams;
        const urlStart = params.get('start');
        const urlEnd = params.get('end');
        if (urlStart && urlEnd) {
            // Persist to sessionStorage so subsequent navigations keep this range
            saveToStorage(urlStart, urlEnd);
            return {start: urlStart, end: urlEnd};
        }
    }
    return loadFromStorage();
}

const _init = resolveInitialRange();

let _start = $state(_init.start);
let _end = $state(_init.end);

/**
 * Current global start date (reactive).
 */
export function getStart(): string {
    return _start;
}

/**
 * Current global end date (reactive).
 */
export function getEnd(): string {
    return _end;
}

/**
 * Update the global date range. Persists to sessionStorage.
 */
export function setDateRange(start: string, end: string) {
    _start = start;
    _end = end;
    saveToStorage(start, end);
}

/**
 * Seed the store from URL params (call on `enter` navigation only).
 * If URL has start/end, use them; otherwise keep current store values.
 */
export function seedFromUrl(searchParams: URLSearchParams): void {
    const urlStart = searchParams.get('start');
    const urlEnd = searchParams.get('end');
    if (urlStart && urlEnd) {
        setDateRange(urlStart, urlEnd);
    } else if (urlStart) {
        setDateRange(urlStart, _end);
    } else if (urlEnd) {
        setDateRange(_start, urlEnd);
    }
}

/**
 * Resolve sentinel values ("min"/"max") to concrete ISO dates for endpoints
 * that don't support the sentinel protocol (DateRangeModel-based APIs).
 *
 * - "min" → "2000-01-01" (earliest reasonable date)
 * - "max" → today's date
 * - Any other value → pass through unchanged
 */
export function resolveDateSentinel(value: string): string {
    if (value === 'min') return '2000-01-01';
    if (value === 'max') return new Date().toISOString().slice(0, 10);
    return value;
}

/**
 * Get start/end with sentinels resolved for non-sentinel APIs.
 */
export function getResolvedStart(): string {
    return resolveDateSentinel(_start);
}

export function getResolvedEnd(): string {
    return resolveDateSentinel(_end);
}
