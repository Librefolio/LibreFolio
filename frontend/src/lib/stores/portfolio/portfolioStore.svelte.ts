/**
 * portfolioStore — Session-level cache for unified portfolio report.
 *
 * Uses POST /api/v1/portfolio/report to run the engine once and get
 * summary + history + allocation_history + data_quality in a single call.
 *
 * Cache key = `user | broker_ids (sorted) | dateFrom | dateTo | targetCurrency | include flags`.
 * Stale-while-revalidate (page cache, phase 1, decision E1): `invalidate()` — a portfolio
 * mutation or «Aggiorna» — marks every cached report stale and keeps it. A page reads what it has
 * with `peekReport()` and shows it at once; `fetchReport()` asks a stale key again, once however
 * many callers, and stores the fresh answer. Only `resetPortfolioCache()` — a session change —
 * forgets everything. There is no time-based frontend TTL.
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

/** Trailing feature selection of `fetchReport` / `peekReport` (plan §4.1: no more positional booleans). */
export type ReportOptions = {includeBrokerPnlHistory?: boolean; includePnlCandles?: boolean; includeIncomeHistory?: boolean; includeCostHistory?: boolean; includeDepositHistory?: boolean; includeAcquisitionFunding?: boolean};

/** A cached report and the mark it was asked under: asked before the last `invalidate()` = stale. */
interface ReportEntry {
    report: PortfolioReport;
    seq: number;
}

interface InflightReport {
    promise: Promise<PortfolioReport | null>;
    seq: number;
}

// ============================================================================
// MODULE-LEVEL REACTIVE STATE (Svelte 5 runes)
// ============================================================================

let reportCache = $state(new Map<CacheKey, ReportEntry>());

const reportInflight = new Map<CacheKey, InflightReport>();
/** Bumped by `resetPortfolioCache()`: an answer to a question asked before it is dropped. */
let cacheGeneration = 0;
/** Bumped by `invalidate()`: entries and requests from before it are stale, and kept. */
let markSeq = 0;

let _isLoading = $state(false);
let _error = $state<string | null>(null);

// ============================================================================
// HELPERS
// ============================================================================

function makeCacheKey(brokerIds?: number[], dateFrom?: string, dateTo?: string, targetCurrency?: string): CacheKey {
    return [getClientSessionUserId() ?? 'anonymous', brokerIds ? [...brokerIds].sort().join(',') : 'all', dateFrom ?? '', dateTo ?? '', targetCurrency ?? ''].join('|');
}

/** The one key `fetchReport` and `peekReport` share: the scope, then every include flag. */
function reportKey(
    brokerIds: number[] | undefined,
    dateFrom: string | undefined,
    dateTo: string | undefined,
    targetCurrency: string | undefined,
    includeContribution: boolean,
    includeBreakdown: boolean,
    includeHistory: boolean,
    includeAllocationHistory: boolean,
    options: ReportOptions | undefined,
): CacheKey {
    return (
        makeCacheKey(brokerIds, dateFrom, dateTo, targetCurrency) +
        (includeContribution ? '|contrib' : '') +
        (includeBreakdown ? '|breakdown' : '') +
        (includeHistory ? '' : '|nohist') +
        (includeAllocationHistory ? '' : '|noalloc') +
        (options?.includeBrokerPnlHistory ? '|brokerpnl' : '') +
        (options?.includePnlCandles ? '|pnlcandles' : '') +
        (options?.includeIncomeHistory ? '|incomehist' : '') +
        (options?.includeCostHistory ? '|costhist' : '') +
        (options?.includeDepositHistory ? '|deposithist' : '') +
        (options?.includeAcquisitionFunding ? '|acqfunding' : '')
    );
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
 * A fresh cached report is returned without asking; a stale or missing one is asked once per key,
 * however many callers, and the promise resolves the fresh answer. It resolves null when the
 * request fails (the stale report stays cached, for `peekReport`) or when a session change
 * discarded it.
 *
 * @param brokerIds      — Filter by broker IDs. Omit or pass [] for all brokers.
 * @param dateFrom       — Start date for history (ISO string, e.g. '2024-01-01').
 * @param dateTo         — End date for history (ISO string).
 * @param targetCurrency — Override base currency (ISO 4217). Defaults to user setting.
 * @param force          — Ask again even when the cached report is fresh.
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
    options?: ReportOptions,
): Promise<PortfolioReport | null> {
    const key = reportKey(brokerIds, dateFrom, dateTo, targetCurrency, includeContribution, includeBreakdown, includeHistory, includeAllocationHistory, options);

    const cached = reportCache.get(key);
    if (!force && cached && cached.seq >= markSeq) return cached.report;

    // One request per key: a caller joins the one in flight unless it left before the last mark.
    const existing = reportInflight.get(key);
    if (existing && existing.seq >= markSeq) return existing.promise;

    const body: Record<string, unknown> = {
        include_summary: true,
        include_history: includeHistory,
        include_allocation_history: includeAllocationHistory,
        include_positions_contribution: includeContribution,
        include_breakdown: includeBreakdown,
        include_broker_pnl_history: options?.includeBrokerPnlHistory ?? false,
        include_pnl_candles: options?.includePnlCandles ?? false,
        include_income_history: options?.includeIncomeHistory ?? false,
        include_cost_history: options?.includeCostHistory ?? false,
        include_deposit_history: options?.includeDepositHistory ?? false,
        include_acquisition_funding: options?.includeAcquisitionFunding ?? false,
    };
    if (brokerIds && brokerIds.length > 0) body.broker_ids = brokerIds;
    if (dateFrom || dateTo) {
        body.date_range = {
            ...(dateFrom ? {start: dateFrom} : {}),
            ...(dateTo ? {end: dateTo} : {}),
        };
    }
    if (targetCurrency) body.target_currency = targetCurrency;

    const slot = {seq: markSeq} as InflightReport;
    reportInflight.set(key, slot);
    slot.promise = requestReport(key, body, slot);
    return slot.promise;
}

/**
 * Ask the engine and store its answer under the mark the question was asked in.
 *
 * Only a session change or `resetPortfolioCache()` discards the answer (null): a mark is not a
 * reason, or on the asset page — the live price ticks every 30-60 s — a slow refresh would never
 * land. An answer asked before the last mark is stored still stale, and never over a newer one.
 * A failure resolves null and leaves the cached report, stale, where it was.
 */
async function requestReport(key: CacheKey, body: Record<string, unknown>, slot: InflightReport): Promise<PortfolioReport | null> {
    const requestSessionGeneration = getClientSessionGeneration();
    const requestCacheGeneration = cacheGeneration;
    const discarded = () => !isClientSessionCurrent(requestSessionGeneration) || requestCacheGeneration !== cacheGeneration;
    _isLoading = true;
    _error = null;
    try {
        const data = await zodiosApi.get_portfolio_report_api_v1_portfolio_report_post(body);
        if (discarded()) return null;
        const stored = reportCache.get(key);
        if (!stored || stored.seq <= slot.seq) reportCache = new Map(reportCache).set(key, {report: data, seq: slot.seq});
        return data;
    } catch (err) {
        if (!discarded()) _error = err instanceof Error ? err.message : 'Failed to fetch portfolio report';
        return null;
    } finally {
        if (reportInflight.get(key) === slot) reportInflight.delete(key);
        if (reportInflight.size === 0) _isLoading = false;
    }
}

/**
 * What the cache holds for exactly the question `fetchReport` would ask with the same arguments
 * (without `force`), read synchronously: `{report, stale}`, or null when nothing was asked yet.
 * A page shows it at once — stale or not — and lets `fetchReport` refresh it.
 */
export function peekReport(brokerIds?: number[], dateFrom?: string, dateTo?: string, targetCurrency?: string, includeContribution = false, includeBreakdown = false, includeHistory = true, includeAllocationHistory = true, options?: ReportOptions): {report: PortfolioReport; stale: boolean} | null {
    const entry = reportCache.get(reportKey(brokerIds, dateFrom, dateTo, targetCurrency, includeContribution, includeBreakdown, includeHistory, includeAllocationHistory, options));
    return entry ? {report: entry.report, stale: entry.seq < markSeq} : null;
}

// Keep legacy exports for backward compatibility with any direct consumers of summary/history
export const fetchSummary = (brokerIds?: number[], _includeBreakdown = false, targetCurrency?: string, force = false) => fetchReport(brokerIds, undefined, undefined, targetCurrency, force).then((r) => r?.summary ?? null);

export const fetchHistory = (brokerIds?: number[], dateFrom?: string, dateTo?: string, targetCurrency?: string, force = false) => fetchReport(brokerIds, dateFrom, dateTo, targetCurrency, force).then((r) => r?.history ?? []);

/**
 * Mark every cached report stale, and keep it: the next `fetchReport` of each key asks again,
 * while `peekReport` still hands the old report to the page that shows it (decision E1).
 *
 * Called by every portfolio-affecting mutation and by «Aggiorna» (`requestPortfolioRefresh`).
 */
export function invalidate(): void {
    markSeq += 1;
    _error = null;
}

/** Forget everything, requests in flight included: a session change never shows another account's data. */
export function resetPortfolioCache(): void {
    cacheGeneration += 1;
    reportCache = new Map();
    reportInflight.clear();
    _isLoading = false;
    _error = null;
}

registerClientSessionReset('portfolioStore', resetPortfolioCache);
registerPortfolioMutationListener('portfolioStore', invalidate);
