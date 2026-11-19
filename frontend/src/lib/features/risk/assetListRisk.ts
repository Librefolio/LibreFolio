/**
 * The risk columns of the asset list (RN-23, Q10 a): each row measured on its own asset, over the page's period and in
 * its currency, at the reader's risk-free rate.
 *
 * **Each row is its own asset's request.** An `asset_set` request measures every asset on one shared calendar (each
 * series is carried onto the other assets' quote days), so a row would depend on its neighbours. Each row therefore
 * sends the Risk tab's own requests on that one asset (`asset` scope), cut to the analytics the columns read; the
 * engine prepares a series per request, so the other analytics of the tab do not change these figures:
 *   - historical: `historical_kpi` (worst and best day) and `drawdown_summary` (max drawdown, largest rally), as L1
 *     and «How does it move?» read them;
 *   - current composition: `historical_kpi` (Sharpe, Sortino) and `asset_risk_return` (volatility, annual return), as
 *     L3's own row reads them.
 * Same period, currency and rate → the same numbers as the tab. The requests go through `queryRisk` (its cache, its
 * in-flight sharing, its staleness after a sync), a few at a time.
 *
 * A figure that cannot be measured is null with the engine's error code, so the cell says «—» with its reason (Q20)
 * and the row sorts last, never as a zero.
 */
import {buildRiskAnalyticRequest, buildRiskQueryRequest} from './riskRequest';
import {riskFreeParameters} from './riskFreeRate';
import {hasRiskCapability, queryRisk, type RiskAnalyticResult, type RiskCatalogResponse, type RiskMode, type RiskQueryRequest, type RiskQueryResponse} from './riskStore.svelte';

/** The columns, in the table's order; the first is the one shown by default. */
export const ASSET_LIST_RISK_COLUMNS = ['maxDrawdown', 'volatility', 'annualReturn', 'sharpe', 'sortino', 'worstDay', 'bestDay', 'rally'] as const;
export type AssetListRiskColumn = (typeof ASSET_LIST_RISK_COLUMNS)[number];

export interface AssetListRiskQuery {
    start: string;
    end: string;
    currency: string;
    riskFreePercent: number;
}

export interface AssetListRiskFigures {
    /** Fractions: drawdown and worst day ≤ 0, the rest as the engine publishes them; null when not measured. */
    values: Record<AssetListRiskColumn, number | null>;
    /** For a null value, the engine's error code saying why (`risk.errors.<code>`); `unknown` when it named none. */
    reasons: Partial<Record<AssetListRiskColumn, string>>;
}

/** Instance ids: one per analytic and mode, as the base waves name theirs. */
const INSTANCE = {
    historicalKpi: 'list-historical-historical_kpi',
    drawdown: 'list-historical-drawdown_summary',
    currentKpi: 'list-current_composition-historical_kpi',
    riskReturn: 'list-current_composition-asset_risk_return',
} as const;

/** The identity of a question: an answer for another one is never shown. */
export function assetListRiskKey(query: AssetListRiskQuery): string {
    return `${query.start}…${query.end} ${query.currency} ${query.riskFreePercent}`;
}

/** The two requests of one row, each only with the analytics the catalogue offers for one asset in that mode. */
export function assetListRiskRequests(assetId: number, query: AssetListRiskQuery, catalog: RiskCatalogResponse | null): Record<RiskMode, RiskQueryRequest | null> {
    const rate = riskFreeParameters(query.riskFreePercent);
    const build = (mode: RiskMode, wanted: Array<[string, string, Record<string, number>]>): RiskQueryRequest | null => {
        const analytics = wanted.filter(([, code]) => hasRiskCapability(catalog, code, 'asset', mode)).map(([instance, code, parameters]) => buildRiskAnalyticRequest(instance, code, parameters));
        if (analytics.length === 0) return null;
        // The current composition is today's holding bought and held, as the tab asks it: the engine refuses that mode without it.
        const compositionPolicy = mode === 'current_composition' ? ('current_buy_and_hold' as const) : undefined;
        return buildRiskQueryRequest({scope: {kind: 'asset', asset_id: assetId}, dateStart: query.start, dateEnd: query.end, targetCurrency: query.currency, mode, compositionPolicy, analytics});
    };
    return {
        historical: build('historical', [
            [INSTANCE.historicalKpi, 'historical_kpi', rate],
            [INSTANCE.drawdown, 'drawdown_summary', {}],
        ]),
        current_composition: build('current_composition', [
            [INSTANCE.currentKpi, 'historical_kpi', rate],
            [INSTANCE.riskReturn, 'asset_risk_return', rate],
        ]),
    };
}

function finite(value: unknown): number | null {
    return typeof value === 'number' && Number.isFinite(value) ? value : null;
}

function resultOf(response: RiskQueryResponse | null, instanceId: string): RiskAnalyticResult | null {
    return response?.items?.find((item) => item.instance_id === instanceId) ?? null;
}

/** The output of an `ok` or `partial` result, or null; and the code that explains a missing one. */
function outputOf(result: RiskAnalyticResult | null): {output: Record<string, unknown> | null; code: string} {
    if (result && (result.status === 'ok' || result.status === 'partial') && result.output) return {output: result.output as unknown as Record<string, unknown>, code: 'unknown'};
    const error = (result as {error?: unknown} | null)?.error;
    const first = Array.isArray(error) ? error[0] : error;
    const code = typeof (first as {code?: unknown} | null | undefined)?.code === 'string' ? (first as {code: string}).code : 'unknown';
    return {output: null, code};
}

/** A row's figures from its two answers (either may be missing: a failed or refused request). */
export function readAssetListRiskFigures(historical: RiskQueryResponse | null, current: RiskQueryResponse | null, {historicalFailed = false, currentFailed = false}: {historicalFailed?: boolean; currentFailed?: boolean} = {}): AssetListRiskFigures {
    const failed = (code: string, didFail: boolean) => (didFail ? 'execution_failed' : code);
    const read = (response: RiskQueryResponse | null, instanceId: string, didFail: boolean) => {
        const result = outputOf(resultOf(response, instanceId));
        return {output: result.output, code: failed(result.code, didFail)};
    };
    const historicalKpi = read(historical, INSTANCE.historicalKpi, historicalFailed);
    const drawdown = read(historical, INSTANCE.drawdown, historicalFailed);
    const currentKpi = read(current, INSTANCE.currentKpi, currentFailed);
    const riskReturn = read(current, INSTANCE.riskReturn, currentFailed);
    const values: Record<AssetListRiskColumn, number | null> = {
        // The tab's L1 reads the summary's depth first, the KPI's when the summary has none (`levelHelpers`).
        maxDrawdown: finite(drawdown.output?.maximum_drawdown) ?? finite(historicalKpi.output?.max_drawdown),
        volatility: finite(riskReturn.output?.portfolio_volatility),
        annualReturn: finite(riskReturn.output?.portfolio_expected_annual_return),
        sharpe: finite(currentKpi.output?.sharpe),
        sortino: finite(currentKpi.output?.sortino),
        worstDay: finite(historicalKpi.output?.worst_realization),
        bestDay: finite(historicalKpi.output?.best_realization),
        rally: finite(drawdown.output?.largest_rally),
    };
    const source: Record<AssetListRiskColumn, {code: string}> = {
        maxDrawdown: drawdown.output ? drawdown : historicalKpi,
        volatility: riskReturn,
        annualReturn: riskReturn,
        sharpe: currentKpi,
        sortino: currentKpi,
        worstDay: historicalKpi,
        bestDay: historicalKpi,
        rally: drawdown,
    };
    const reasons: Partial<Record<AssetListRiskColumn, string>> = {};
    for (const column of ASSET_LIST_RISK_COLUMNS) if (values[column] === null) reasons[column] = source[column].code;
    return {values, reasons};
}

/**
 * Every row's figures, `concurrency` assets at a time. `onRow` hands each row over as it lands, so the column fills
 * progressively; `stillWanted` stops the remaining rows once the page has asked another question.
 */
export async function loadAssetListRisk(
    assetIds: readonly number[],
    query: AssetListRiskQuery,
    catalog: RiskCatalogResponse | null,
    {concurrency = 4, onRow, stillWanted = () => true}: {concurrency?: number; onRow?: (assetId: number, figures: AssetListRiskFigures) => void; stillWanted?: () => boolean} = {},
): Promise<Map<number, AssetListRiskFigures>> {
    const figures = new Map<number, AssetListRiskFigures>();
    const queue = [...assetIds];
    const worker = async () => {
        while (queue.length > 0 && stillWanted()) {
            const assetId = queue.shift()!;
            const requests = assetListRiskRequests(assetId, query, catalog);
            // Each wave on its own: a failed one (the API client logs it, H-60) blanks only its columns, saying the measure failed.
            const [historical, current] = await Promise.allSettled([requests.historical ? queryRisk(requests.historical) : null, requests.current_composition ? queryRisk(requests.current_composition) : null]);
            const row = readAssetListRiskFigures(historical.status === 'fulfilled' ? historical.value : null, current.status === 'fulfilled' ? current.value : null, {
                historicalFailed: historical.status === 'rejected',
                currentFailed: current.status === 'rejected',
            });
            if (!stillWanted()) return;
            figures.set(assetId, row);
            onRow?.(assetId, row);
        }
    };
    await Promise.all(Array.from({length: Math.max(1, Math.min(concurrency, assetIds.length))}, worker));
    return figures;
}
