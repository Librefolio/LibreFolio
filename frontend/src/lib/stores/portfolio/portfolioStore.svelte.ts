/**
 * portfolioStore — Session-level cache for unified portfolio report.
 *
 * Uses POST /api/v1/portfolio/report to run the engine once and get
 * summary + history + allocation_history + data_quality in a single call.
 *
 * Cache key = `broker_ids (sorted) | dateFrom | dateTo | targetCurrency`
 * Calling `invalidate()` clears the cache (used by [↻ Sync] and CRUD mutations).
 *
 * Architecture: Svelte 5 module-level $state() runes.
 *
 * @module stores/portfolio/portfolioStore
 */

import {zodiosApi} from '$lib/api';

// ============================================================================
// TYPES — inferred from direct-return endpoints for cleaner types
// (PortfolioReport wraps fields in Optional unions that are harder to narrow)
// ============================================================================

type ApiReturnType<T extends (...args: never[]) => Promise<unknown>> = Awaited<ReturnType<T>>;

// Use the direct endpoint return types — clean, no optional union wrappers
export type PortfolioSummary = ApiReturnType<typeof zodiosApi.get_portfolio_summary_api_v1_portfolio_summary_post>;
export type PortfolioHistoryPoint = ApiReturnType<typeof zodiosApi.get_portfolio_history_api_v1_portfolio_history_post> extends (infer U)[] ? U : never;
export type PortfolioReport = ApiReturnType<typeof zodiosApi.get_portfolio_report_api_v1_portfolio_report_post>;

// For allocation history dimensions we use the report type (no separate direct endpoint)
type RawAlloc = PortfolioReport['allocation_history'];
export type AllocationHistoryDimensions = Extract<NonNullable<RawAlloc>, {type?: unknown}>;

// Data quality also from report
type RawDQ = PortfolioReport['data_quality'];
export type DataQualityReport = Extract<NonNullable<RawDQ>, {issues?: unknown}>;

// Positions contribution also from report
type RawContrib = PortfolioReport['positions_contribution'];
export type PositionsContribution = Extract<NonNullable<RawContrib>, {positions?: unknown}>;

// ============================================================================
// CACHE INFRASTRUCTURE
// ============================================================================

type CacheKey = string;

interface CacheEntry<T> {
    data: T;
    timestamp: number;
}

// ============================================================================
// MODULE-LEVEL REACTIVE STATE (Svelte 5 runes)
// ============================================================================

let reportCache = $state(new Map<CacheKey, CacheEntry<PortfolioReport>>());

const reportInflight = new Map<CacheKey, Promise<PortfolioReport>>();

let _isLoading = $state(false);
let _error = $state<string | null>(null);

// ============================================================================
// HELPERS
// ============================================================================

function makeCacheKey(brokerIds?: number[], dateFrom?: string, dateTo?: string, targetCurrency?: string): CacheKey {
    return [brokerIds ? [...brokerIds].sort().join(',') : 'all', dateFrom ?? '', dateTo ?? '', targetCurrency ?? ''].join('|');
}

// ============================================================================
// PUBLIC API
// ============================================================================

/** Reactive loading indicator — true while a fetch is in-flight. */
export function portfolioIsLoading(): boolean {
    return _isLoading;
}

/** Last error message, or null if no error. */
export function portfolioError(): string | null {
    return _error;
}

/**
 * Fetch (or return cached) unified portfolio report.
 *
 * Returns summary + history + allocation_history + data_quality from a single engine run.
 *
 * @param brokerIds      — Filter by broker IDs. Omit or pass [] for all brokers.
 * @param dateFrom       — Start date for history (ISO string, e.g. '2024-01-01').
 * @param dateTo         — End date for history (ISO string).
 * @param targetCurrency — Override base currency (ISO 4217). Defaults to user setting.
 * @param force          — Bypass cache and re-fetch.
 */
export async function fetchReport(brokerIds?: number[], dateFrom?: string, dateTo?: string, targetCurrency?: string, force = false, includeContribution = false): Promise<PortfolioReport | null> {
    const key = makeCacheKey(brokerIds, dateFrom, dateTo, targetCurrency) + (includeContribution ? '|contrib' : '');

    if (!force) {
        const cached = reportCache.get(key);
        if (cached) return cached.data;
    }

    // Deduplicate concurrent callers for the same key
    const existing = reportInflight.get(key);
    if (existing) return existing.catch(() => null);

    _isLoading = true;
    _error = null;

    const promise = (async () => {
        try {
            const body: Record<string, unknown> = {
                include_summary: true,
                include_history: true,
                include_allocation_history: true,
                include_positions_contribution: includeContribution,
            };
            if (brokerIds && brokerIds.length > 0) body.broker_ids = brokerIds;
            if (dateFrom || dateTo) {
                body.date_range = {
                    ...(dateFrom ? {start: dateFrom} : {}),
                    ...(dateTo ? {end: dateTo} : {}),
                };
            }
            if (targetCurrency) body.target_currency = targetCurrency;

            const data = await zodiosApi.get_portfolio_report_api_v1_portfolio_report_post(body);
            reportCache = new Map(reportCache).set(key, {data, timestamp: Date.now()});
            return data;
        } catch (err) {
            _error = err instanceof Error ? err.message : 'Failed to fetch portfolio report';
            throw err;
        } finally {
            reportInflight.delete(key);
            if (reportInflight.size === 0) _isLoading = false;
        }
    })();

    reportInflight.set(key, promise);
    return promise.catch(() => null);
}

// Keep legacy exports for backward compatibility with any direct consumers of summary/history
export const fetchSummary = (brokerIds?: number[], _includeBreakdown = false, targetCurrency?: string, force = false) => fetchReport(brokerIds, undefined, undefined, targetCurrency, force).then((r) => r?.summary ?? null);

export const fetchHistory = (brokerIds?: number[], dateFrom?: string, dateTo?: string, targetCurrency?: string, force = false) => fetchReport(brokerIds, dateFrom, dateTo, targetCurrency, force).then((r) => r?.history ?? []);

/**
 * Clear the entire portfolio cache.
 *
 * Call this after any transaction CRUD mutation or when the user clicks [↻ Sync].
 */
export function invalidate(): void {
    reportCache = new Map();
}
