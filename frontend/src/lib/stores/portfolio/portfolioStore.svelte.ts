/**
 * portfolioStore — Session-level cache for unified portfolio report.
 *
 * Uses POST /api/v1/portfolio/report to run the engine once and get
 * summary + history + allocation_history + data_quality in a single call.
 *
 * Cache key = `user | broker_ids (sorted) | dateFrom | dateTo | targetCurrency`.
 * Calling `invalidate()` clears the cache (used by auth transitions, [↻ Sync],
 * and portfolio-affecting API mutations). There is no time-based frontend TTL:
 * entries live for the current authenticated session unless invalidated.
 *
 * Architecture: Svelte 5 module-level $state() runes.
 *
 * @module stores/portfolio/portfolioStore
 */

import {zodiosApi} from '$lib/api';
import {getClientSessionGeneration, getClientSessionUserId, isClientSessionCurrent, registerClientSessionReset} from '$lib/stores/app/clientSession';
import {registerPortfolioMutationListener} from './portfolioMutation';

// ============================================================================
// TYPES — derived from unified /report endpoint response
// ============================================================================

type ApiReturnType<T extends (...args: never[]) => Promise<unknown>> = Awaited<ReturnType<T>>;

export type PortfolioReport = ApiReturnType<typeof zodiosApi.get_portfolio_report_api_v1_portfolio_report_post>;

// Extract summary type from report response
type RawSummary = PortfolioReport['summary'];
export type PortfolioSummary = NonNullable<RawSummary> extends infer S ? (S extends {net_worth: unknown} ? S : never) : never;

// History point type — define inline (generated type is not exported)
export type PortfolioHistoryPoint = {
    date: string;
    cash_value: {code: string; amount: string};
    market_value: {code: string; amount: string};
    broker_nav_value?: {code: string; amount: string} | null;
    in_transit_cash_value?: {code: string; amount: string} | null;
    in_transit_asset_market_value?: {code: string; amount: string} | null;
    in_transit_market_value?: {code: string; amount: string} | null;
    nav_value: {code: string; amount: string};
    open_cost_basis?: {code: string; amount: string} | null;
    in_transit_asset_cost_basis?: {code: string; amount: string} | null;
    in_transit_book_value?: {code: string; amount: string} | null;
    book_value?: {code: string; amount: string} | null;
    capital_baseline: {code: string; amount: string};
    book_asset_like: {code: string; amount: string};
    cash_from_contributed_capital: {code: string; amount: string};
    cash_from_generated_returns: {code: string; amount: string};
    total_pnl: {code: string; amount: string};
    unrealized_gain_loss?: {code: string; amount: string} | null;
    twrr?: string | null;
    mwrr_annualized?: string | null;
    mwrr_cumulative?: string | null;
    roi?: string | null;
};

// Broker P&L history point/series types — define inline (generated type is not exported),
// mirroring PortfolioHistoryPoint above. G1a: additive per-broker P&L overlay for GrowthChart.
export type PortfolioBrokerPnlHistoryPoint = {
    date: string;
    total_pnl: {code: string; amount: string};
};

export type PortfolioBrokerPnlHistory = {
    broker_id: number;
    broker_name: string;
    points: PortfolioBrokerPnlHistoryPoint[];
};

// Synthetic P&L candle types — define inline (generated type is not exported), mirroring
// the pattern above. G1b: total-only candle series for GrowthChart's P&L candles submode.
export type PortfolioPnlCandlePoint = {
    date: string;
    open: {code: string; amount: string};
    high: {code: string; amount: string};
    low: {code: string; amount: string};
    close: {code: string; amount: string};
};

export type PortfolioPnlCandleSeries = {
    hypothetical: boolean;
    points: PortfolioPnlCandlePoint[];
};

// Signed personal income history types — define inline (generated type is not exported),
// mirroring the pattern above. G1c: DIVIDEND/INTEREST stacked bars for GrowthChart's P&L
// income submode.
export type PortfolioIncomeHistoryPoint = {
    date: string;
    dividend: {code: string; amount: string};
    interest: {code: string; amount: string};
};

export type PortfolioIncomeHistorySeries = {
    points: PortfolioIncomeHistoryPoint[];
    missing_fx_pairs: string[];
};

// Signed FEE+TAX cost history types — define inline, mirroring the pattern above.
// Batch 2: costs dimension for GrowthChart's P&L income submode.
export type PortfolioCostHistoryPoint = {
    date: string;
    cost: {code: string; amount: string};
};

export type PortfolioCostHistorySeries = {
    points: PortfolioCostHistoryPoint[];
    missing_fx_pairs: string[];
};

// DEPOSIT history types — define inline, mirroring the pattern above. Batch 2:
// deposit-size dimension for GrowthChart's P&L income submode.
export type PortfolioDepositHistoryPoint = {
    date: string;
    deposit: {code: string; amount: string};
};

export type PortfolioDepositHistorySeries = {
    points: PortfolioDepositHistoryPoint[];
    missing_fx_pairs: string[];
};

// New-vs-reinvested BUY funding split types — define inline, mirroring the pattern
// above. Batch 2: acquisition-size dimension (2-zone stacked bar) for GrowthChart's
// P&L income submode.
export type PortfolioAcquisitionFundingPoint = {
    date: string;
    from_new_capital: {code: string; amount: string};
    from_reinvested: {code: string; amount: string};
};

export type PortfolioAcquisitionFundingSeries = {
    points: PortfolioAcquisitionFundingPoint[];
};

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

// ============================================================================
// MODULE-LEVEL REACTIVE STATE (Svelte 5 runes)
// ============================================================================

let reportCache = $state(new Map<CacheKey, PortfolioReport>());

const reportInflight = new Map<CacheKey, Promise<PortfolioReport | null>>();
let cacheGeneration = 0;

let _isLoading = $state(false);
let _error = $state<string | null>(null);

// ============================================================================
// HELPERS
// ============================================================================

function makeCacheKey(brokerIds?: number[], dateFrom?: string, dateTo?: string, targetCurrency?: string): CacheKey {
    return [getClientSessionUserId() ?? 'anonymous', brokerIds ? [...brokerIds].sort().join(',') : 'all', dateFrom ?? '', dateTo ?? '', targetCurrency ?? ''].join('|');
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
 * @param includeContribution — Also request positions_contribution (per-asset period P&L).
 * @param includeBreakdown     — Also request summary.by_broker (per-broker NAV/gain/cash breakdown).
 * @param includeHistory           — Request the daily history series. Defaults to true for
 *   backward compatibility — pass false for callers that only need `summary` (e.g. a broker list's
 *   breakdown-only fetch), since the daily series can be several MB for a long-lived portfolio and
 *   synchronously JSON-parsing it blocks the main thread for no benefit if it's never read.
 * @param includeAllocationHistory — Request allocation_history (type/sector/geography series).
 *   Same rationale as includeHistory — defaults to true, pass false when not consumed.
 * @param options.includeBrokerPnlHistory — Request broker_pnl_history (G1a additive per-broker
 *   P&L overlay for GrowthChart). Trailing options object per plan §4.1: feature selection
 *   must not add more order-sensitive positional booleans. Caller sets true only when the
 *   effective broker scope has ≥2 brokers.
 * @param options.includePnlCandles — Request pnl_candles (G1b synthetic total-P&L candle
 *   series). Lazy — caller sets true only on first candle-submode activation, per plan §4.1
 *   ("expensive OHLC work stays off ordinary reports").
 * @param options.includeIncomeHistory — Request income_history (G1c signed DIVIDEND/
 *   INTEREST history). Eager — a sparse, cheap payload; Dashboard/Broker overview set
 *   this true on every ordinary load, unlike includePnlCandles.
 * @param options.includeCostHistory — Request cost_history (batch 2 signed FEE+TAX
 *   history). Same eager/sparse caller policy as includeIncomeHistory.
 * @param options.includeDepositHistory — Request deposit_history (batch 2 DEPOSIT
 *   history). Same eager/sparse caller policy as includeIncomeHistory.
 * @param options.includeAcquisitionFunding — Request acquisition_funding (batch 2
 *   new-vs-reinvested BUY funding split). Same eager/sparse caller policy as
 *   includeIncomeHistory.
 */
export async function fetchReport(
    brokerIds?: number[],
    dateFrom?: string,
    dateTo?: string,
    targetCurrency?: string,
    force = false,
    includeContribution = false,
    includeBreakdown = false,
    includeHistory = true,
    includeAllocationHistory = true,
    options?: {includeBrokerPnlHistory?: boolean; includePnlCandles?: boolean; includeIncomeHistory?: boolean; includeCostHistory?: boolean; includeDepositHistory?: boolean; includeAcquisitionFunding?: boolean},
): Promise<PortfolioReport | null> {
    const includeBrokerPnlHistory = options?.includeBrokerPnlHistory ?? false;
    const includePnlCandles = options?.includePnlCandles ?? false;
    const includeIncomeHistory = options?.includeIncomeHistory ?? false;
    const includeCostHistory = options?.includeCostHistory ?? false;
    const includeDepositHistory = options?.includeDepositHistory ?? false;
    const includeAcquisitionFunding = options?.includeAcquisitionFunding ?? false;
    const key =
        makeCacheKey(brokerIds, dateFrom, dateTo, targetCurrency) +
        (includeContribution ? '|contrib' : '') +
        (includeBreakdown ? '|breakdown' : '') +
        (includeHistory ? '' : '|nohist') +
        (includeAllocationHistory ? '' : '|noalloc') +
        (includeBrokerPnlHistory ? '|brokerpnl' : '') +
        (includePnlCandles ? '|pnlcandles' : '') +
        (includeIncomeHistory ? '|incomehist' : '') +
        (includeCostHistory ? '|costhist' : '') +
        (includeDepositHistory ? '|deposithist' : '') +
        (includeAcquisitionFunding ? '|acqfunding' : '');
    const requestSessionGeneration = getClientSessionGeneration();
    const requestCacheGeneration = cacheGeneration;

    if (!force) {
        const cached = reportCache.get(key);
        if (cached) return cached;
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
                include_history: includeHistory,
                include_allocation_history: includeAllocationHistory,
                include_positions_contribution: includeContribution,
                include_breakdown: includeBreakdown,
                include_broker_pnl_history: includeBrokerPnlHistory,
                include_pnl_candles: includePnlCandles,
                include_income_history: includeIncomeHistory,
                include_cost_history: includeCostHistory,
                include_deposit_history: includeDepositHistory,
                include_acquisition_funding: includeAcquisitionFunding,
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
            if (!isClientSessionCurrent(requestSessionGeneration) || requestCacheGeneration !== cacheGeneration) {
                return null;
            }
            reportCache = new Map(reportCache).set(key, data);
            return data;
        } catch (err) {
            if (isClientSessionCurrent(requestSessionGeneration) && requestCacheGeneration === cacheGeneration) {
                _error = err instanceof Error ? err.message : 'Failed to fetch portfolio report';
            }
            throw err;
        } finally {
            if (isClientSessionCurrent(requestSessionGeneration) && requestCacheGeneration === cacheGeneration) {
                reportInflight.delete(key);
            }
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
    cacheGeneration += 1;
    reportCache = new Map();
    reportInflight.clear();
    _isLoading = false;
    _error = null;
}

registerClientSessionReset('portfolioStore', invalidate);
registerPortfolioMutationListener('portfolioStore', invalidate);
