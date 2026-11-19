/**
 * The risk columns of the asset list (RN-23, Q10 a): each row is its own asset's request — never one shared calendar —
 * with the Risk tab's parameters, read as the tab reads it; a figure the engine cannot give is null with its reason.
 */
import {beforeEach, describe, expect, it, vi} from 'vitest';

const queryRisk = vi.fn();
vi.mock('./riskStore.svelte', async (importOriginal) => ({
    ...(await importOriginal<typeof import('./riskStore.svelte')>()),
    queryRisk: (...args: unknown[]) => queryRisk(...args),
}));

import {ASSET_LIST_RISK_COLUMNS, assetListRiskKey, assetListRiskRequests, loadAssetListRisk, readAssetListRiskFigures} from './assetListRisk';
import {buildBaseAnalytics} from './riskAnalysisHelpers';
import type {RiskCatalogResponse, RiskQueryRequest, RiskQueryResponse} from './riskStore.svelte';

const QUERY = {start: '2026-08-18', end: '2026-11-18', currency: 'EUR', riskFreePercent: 2.5};

function catalog(entries: Array<[string, string[]]>): RiskCatalogResponse {
    return {items: entries.map(([code, modes]) => ({analytic_code: code, supported_scopes: ['asset'], supported_modes: modes}))} as unknown as RiskCatalogResponse;
}
const FULL = catalog([
    ['historical_kpi', ['historical', 'current_composition']],
    ['drawdown_summary', ['historical']],
    ['asset_risk_return', ['current_composition']],
]);

const analytic = (request: RiskQueryRequest | null, code: string) => request?.analytics.find((item) => item.analytic_code === code);

function ok(instanceId: string, code: string, output: Record<string, unknown>) {
    return {instance_id: instanceId, analytic_code: code, status: 'ok', output, metadata: {}};
}
function refused(instanceId: string, code: string, errorCode: string) {
    return {instance_id: instanceId, analytic_code: code, status: 'unavailable', output: null, error: {code: errorCode, message: 'x'}, metadata: {}};
}
const response = (...items: unknown[]) => ({items}) as unknown as RiskQueryResponse;

describe('assetListRiskRequests — one asset, the tab’s parameters', () => {
    it('asks about the one asset, over the page’s period, in its currency: never an asset set', () => {
        const requests = assetListRiskRequests(7, QUERY, FULL);
        for (const request of [requests.historical, requests.current_composition]) {
            expect(request?.scope).toEqual({kind: 'asset', asset_id: 7});
            expect(request?.date_range).toEqual({start: QUERY.start, end: QUERY.end});
            expect(request?.target_currency).toBe('EUR');
        }
        expect(requests.historical?.mode).toBe('historical');
        expect(requests.current_composition?.mode).toBe('current_composition');
        expect(requests.historical?.analytics.map((item) => item.analytic_code)).toEqual(['historical_kpi', 'drawdown_summary']);
        // The engine refuses a current-composition request without its policy (a 422): the tab sends it, and so does a row.
        expect(requests.current_composition?.composition_policy).toBe('current_buy_and_hold');
        expect(requests.historical?.composition_policy).toBeUndefined();
        expect(requests.current_composition?.analytics.map((item) => item.analytic_code)).toEqual(['historical_kpi', 'asset_risk_return']);
    });

    it('charges the rate exactly as the Risk tab’s base waves do', () => {
        const ctx = {appliedRiskFreePercent: QUERY.riskFreePercent, hasCapability: () => true, includeDrawdownSummary: true, includeCurrentCompositionRiskReturn: true};
        const tabHistoricalKpi = buildBaseAnalytics('historical', ctx).find((item) => item.analytic_code === 'historical_kpi');
        const tabCurrent = buildBaseAnalytics('current_composition', ctx);
        const requests = assetListRiskRequests(7, QUERY, FULL);
        expect(analytic(requests.historical, 'historical_kpi')?.parameters).toEqual(tabHistoricalKpi?.parameters);
        expect(analytic(requests.current_composition, 'historical_kpi')?.parameters).toEqual(tabCurrent.find((item) => item.analytic_code === 'historical_kpi')?.parameters);
        expect(analytic(requests.current_composition, 'asset_risk_return')?.parameters).toEqual(tabCurrent.find((item) => item.analytic_code === 'asset_risk_return')?.parameters);
        expect(analytic(requests.historical, 'drawdown_summary')?.parameters ?? {}).toEqual({});
    });

    it('asks only what the catalogue offers on one asset, and nothing when it offers nothing', () => {
        const partial = assetListRiskRequests(7, QUERY, catalog([['historical_kpi', ['historical']]]));
        expect(partial.historical?.analytics.map((item) => item.analytic_code)).toEqual(['historical_kpi']);
        expect(partial.current_composition).toBeNull();
        const none = assetListRiskRequests(7, QUERY, catalog([]));
        expect(none).toEqual({historical: null, current_composition: null});
    });

    it('a question is its period, currency and rate', () => {
        expect(assetListRiskKey(QUERY)).not.toBe(assetListRiskKey({...QUERY, end: '2026-11-17'}));
        expect(assetListRiskKey(QUERY)).not.toBe(assetListRiskKey({...QUERY, currency: 'USD'}));
        expect(assetListRiskKey(QUERY)).not.toBe(assetListRiskKey({...QUERY, riskFreePercent: 3}));
    });
});

describe('readAssetListRiskFigures — the tab’s fields, and «—» with its reason', () => {
    const historical = response(ok('list-historical-historical_kpi', 'historical_kpi', {kind: 'kpi', max_drawdown: -0.3, worst_realization: -0.05, best_realization: 0.04}), ok('list-historical-drawdown_summary', 'drawdown_summary', {kind: 'drawdown', maximum_drawdown: -0.25, largest_rally: 0.6}));
    const current = response(ok('list-current_composition-historical_kpi', 'historical_kpi', {kind: 'kpi', sharpe: 0.8, sortino: 1.1}), ok('list-current_composition-asset_risk_return', 'asset_risk_return', {kind: 'risk_return', portfolio_volatility: 0.18, portfolio_expected_annual_return: 0.07}));

    it('reads every column from the field the tab reads', () => {
        const figures = readAssetListRiskFigures(historical, current);
        expect(figures.values).toEqual({maxDrawdown: -0.25, volatility: 0.18, annualReturn: 0.07, sharpe: 0.8, sortino: 1.1, worstDay: -0.05, bestDay: 0.04, rally: 0.6});
        expect(figures.reasons).toEqual({});
    });

    it('takes the KPI’s drawdown when the summary has none, as L1 does', () => {
        const noSummary = response(ok('list-historical-historical_kpi', 'historical_kpi', {kind: 'kpi', max_drawdown: -0.3}), refused('list-historical-drawdown_summary', 'drawdown_summary', 'insufficient_history'));
        const figures = readAssetListRiskFigures(noSummary, current);
        expect(figures.values.maxDrawdown).toBe(-0.3);
        expect(figures.reasons.maxDrawdown).toBeUndefined();
        expect(figures.values.rally).toBeNull();
        expect(figures.reasons.rally).toBe('insufficient_history');
    });

    it('a refused analytic leaves its columns null with the engine’s code; a missing answer says unknown', () => {
        const refusedCurrent = response(refused('list-current_composition-historical_kpi', 'historical_kpi', 'insufficient_history'), refused('list-current_composition-asset_risk_return', 'asset_risk_return', 'data_unavailable'));
        const figures = readAssetListRiskFigures(null, refusedCurrent);
        expect(figures.values.sharpe).toBeNull();
        expect(figures.reasons.sharpe).toBe('insufficient_history');
        expect(figures.reasons.volatility).toBe('data_unavailable');
        for (const column of ['maxDrawdown', 'worstDay', 'bestDay', 'rally'] as const) {
            expect(figures.values[column]).toBeNull();
            expect(figures.reasons[column]).toBe('unknown');
        }
    });
});

describe('loadAssetListRisk — a few at a time, and only for the question still asked', () => {
    beforeEach(() => {
        queryRisk.mockReset();
    });

    it('measures every asset, never more than `concurrency` at once, and hands each row over as it lands', async () => {
        let inFlight = 0;
        let peak = 0;
        queryRisk.mockImplementation(async () => {
            inFlight += 1;
            peak = Math.max(peak, inFlight);
            await new Promise((resolve) => setTimeout(resolve, 1));
            inFlight -= 1;
            return response();
        });
        const landed: number[] = [];
        const figures = await loadAssetListRisk([1, 2, 3, 4, 5, 6, 7], QUERY, FULL, {concurrency: 2, onRow: (assetId) => landed.push(assetId)});
        expect([...figures.keys()].sort()).toEqual([1, 2, 3, 4, 5, 6, 7]);
        expect([...landed].sort()).toEqual([1, 2, 3, 4, 5, 6, 7]);
        // Two requests per asset (the two modes), two assets at a time.
        expect(peak).toBeLessThanOrEqual(4);
        expect(queryRisk).toHaveBeenCalledTimes(14);
    });

    it('stops when the page asks another question, and hands nothing over', async () => {
        let wanted = true;
        queryRisk.mockImplementation(async () => {
            wanted = false;
            return response();
        });
        const landed: number[] = [];
        const figures = await loadAssetListRisk([1, 2, 3], QUERY, FULL, {concurrency: 1, onRow: (assetId) => landed.push(assetId), stillWanted: () => wanted});
        expect(landed).toEqual([]);
        expect(figures.size).toBe(0);
        expect(queryRisk).toHaveBeenCalledTimes(2);
    });

    it('one failed wave blanks only its own columns: the other wave’s figures still land', async () => {
        queryRisk.mockImplementation(async (request: RiskQueryRequest) => {
            if (request.mode === 'current_composition') throw new Error('422');
            return response(ok('list-historical-drawdown_summary', 'drawdown_summary', {kind: 'drawdown', maximum_drawdown: -0.2, largest_rally: 0.3}));
        });
        const figures = await loadAssetListRisk([1], QUERY, FULL, {concurrency: 1});
        expect(figures.get(1)?.values.maxDrawdown).toBe(-0.2);
        expect(figures.get(1)?.reasons.sharpe).toBe('execution_failed');
        expect(figures.get(1)?.reasons.volatility).toBe('execution_failed');
    });

    it('a row whose requests fail says so in every column, and the others still land', async () => {
        queryRisk.mockImplementation(async (request: RiskQueryRequest) => {
            if (request.scope.kind === 'asset' && request.scope.asset_id === 2) throw new Error('boom');
            return response();
        });
        const figures = await loadAssetListRisk([1, 2], QUERY, FULL, {concurrency: 1});
        expect(figures.get(2)?.reasons).toEqual(Object.fromEntries(ASSET_LIST_RISK_COLUMNS.map((column) => [column, 'execution_failed'])));
        expect(figures.get(1)?.reasons.maxDrawdown).toBe('unknown');
    });
});
