/**
 * portfolioStore — Session-level cache for portfolio summary and history.
 *
 * Provides reactive, parameterised caching for the two main portfolio API calls:
 * - POST /api/v1/portfolio/summary  → PortfolioSummary (KPIs + allocations)
 * - POST /api/v1/portfolio/history  → PortfolioHistoryPoint[] (daily time series)
 *
 * Cache key = `broker_ids (sorted) | dateFrom | dateTo | targetCurrency` so each
 * unique filter combination is cached independently. Calling `invalidate()` clears
 * the entire cache (used by the [↻ Sync] button and after any transaction CRUD mutation).
 *
 * Architecture: Svelte 5 module-level $state() runes — same pattern as txStore.svelte.ts.
 *
 * @module stores/portfolio/portfolioStore
 */

import {zodiosApi} from '$lib/api';
import type {z} from 'zod';

// ============================================================================
// TYPES (inferred from the generated Zodios client)
// ============================================================================

type ApiReturnType<T extends (...args: never[]) => Promise<unknown>> = Awaited<ReturnType<T>>;

export type PortfolioSummary = ApiReturnType<typeof zodiosApi.get_portfolio_summary_api_v1_portfolio_summary_post>;
export type PortfolioHistoryPoint = ApiReturnType<typeof zodiosApi.get_portfolio_history_api_v1_portfolio_history_post> extends (infer U)[] ? U : never;

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

let summaryCache = $state(new Map<CacheKey, CacheEntry<PortfolioSummary>>());
let historyCache = $state(new Map<CacheKey, CacheEntry<PortfolioHistoryPoint[]>>());

/** Tracks which cache keys are currently being fetched to prevent duplicate in-flight requests. */
const summaryInflight = new Map<CacheKey, Promise<PortfolioSummary>>();
const historyInflight = new Map<CacheKey, Promise<PortfolioHistoryPoint[]>>();

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

/**
 * Reactive loading indicator — true while at least one fetch is in-flight.
 * Use as: `$derived(portfolioIsLoading())`
 */
export function portfolioIsLoading(): boolean {
    return _isLoading;
}

/** Last error message, or null if no error. */
export function portfolioError(): string | null {
    return _error;
}

/**
 * Fetch (or return cached) portfolio summary.
 *
 * @param brokerIds      — Filter by broker IDs. Omit or pass [] for all brokers.
 * @param includeBreakdown — Include per-broker breakdown (default false).
 * @param targetCurrency — Override base currency (ISO 4217, e.g. 'USD'). Defaults to user setting.
 * @param force          — Bypass cache and re-fetch.
 */
export async function fetchSummary(brokerIds?: number[], includeBreakdown = false, targetCurrency?: string, force = false): Promise<PortfolioSummary | null> {
    const key = makeCacheKey(brokerIds, undefined, undefined, targetCurrency);

    if (!force) {
        const cached = summaryCache.get(key);
        if (cached) return cached.data;
    }

    // Deduplicate concurrent callers for the same key
    const existing = summaryInflight.get(key);
    if (existing) return existing;

    _isLoading = true;
    _error = null;

    const promise = (async () => {
        try {
            const body: Record<string, unknown> = {};
            if (brokerIds && brokerIds.length > 0) body.broker_ids = brokerIds;
            if (includeBreakdown) body.include_breakdown = true;
            if (targetCurrency) body.target_currency = targetCurrency;

            const data = await zodiosApi.get_portfolio_summary_api_v1_portfolio_summary_post(body);
            summaryCache = new Map(summaryCache).set(key, {data, timestamp: Date.now()});
            return data;
        } catch (err) {
            _error = err instanceof Error ? err.message : 'Failed to fetch portfolio summary';
            throw err;
        } finally {
            summaryInflight.delete(key);
            if (summaryInflight.size === 0 && historyInflight.size === 0) _isLoading = false;
        }
    })();

    summaryInflight.set(key, promise);
    return promise.catch(() => null);
}

/**
 * Fetch (or return cached) portfolio history time series.
 *
 * @param brokerIds      — Filter by broker IDs. Omit or pass [] for all brokers.
 * @param dateFrom       — Start date (ISO string, e.g. '2024-01-01').
 * @param dateTo         — End date (ISO string).
 * @param targetCurrency — Override base currency (ISO 4217, e.g. 'USD'). Defaults to user setting.
 * @param force          — Bypass cache and re-fetch.
 */
export async function fetchHistory(brokerIds?: number[], dateFrom?: string, dateTo?: string, targetCurrency?: string, force = false): Promise<PortfolioHistoryPoint[]> {
    const key = makeCacheKey(brokerIds, dateFrom, dateTo, targetCurrency);

    if (!force) {
        const cached = historyCache.get(key);
        if (cached) return cached.data;
    }

    const existing = historyInflight.get(key);
    if (existing) return existing;

    _isLoading = true;
    _error = null;

    const promise = (async () => {
        try {
            const body: Record<string, unknown> = {};
            if (brokerIds && brokerIds.length > 0) body.broker_ids = brokerIds;
            if (dateFrom || dateTo) {
                body.date_range = {
                    ...(dateFrom ? {start: dateFrom} : {}),
                    ...(dateTo ? {end: dateTo} : {}),
                };
            }
            if (targetCurrency) body.target_currency = targetCurrency;

            const data = await zodiosApi.get_portfolio_history_api_v1_portfolio_history_post(body);
            historyCache = new Map(historyCache).set(key, {data, timestamp: Date.now()});
            return data;
        } catch (err) {
            _error = err instanceof Error ? err.message : 'Failed to fetch portfolio history';
            throw err;
        } finally {
            historyInflight.delete(key);
            if (summaryInflight.size === 0 && historyInflight.size === 0) _isLoading = false;
        }
    })();

    historyInflight.set(key, promise);
    return promise.catch(() => []);
}

/**
 * Clear the entire portfolio cache.
 *
 * Call this after any transaction CRUD mutation or when the user clicks [↻ Sync].
 */
export function invalidate(): void {
    summaryCache = new Map();
    historyCache = new Map();
}
