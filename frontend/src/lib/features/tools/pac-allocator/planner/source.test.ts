/**
 * fetchPlannerSource: the current distribution keeps the portfolio engine's valuation code (Vitest, node).
 *
 * J-17 (developer's option A, 16/10). A holding with no price observation at all — no quote, BUY or
 * SELL on or before the day — is valued by the portfolio engine at its book cost, as a declared
 * estimate, and `POST /portfolio/allocation-source` publishes `valuation_source: "ESTIMATED_AT_COST"`
 * for its row. The mapper keeps the codes it knows and turns any other value into `null`;
 * ESTIMATED_AT_COST must be one it knows, or the planner loses why the holding has the weight it has.
 *
 * Before J-17: the mapper knew MARKET_PRICE, LAST_TRADE_PRICE and MISSING only, so an at-cost row
 * reached the planner with `valuation_source: null`.
 *
 * The API client is mocked: its response goes to the mapper as the client would return it. The
 * tool session is a real one (`transitionClientSession`), so the call passes the real session guard.
 * No translated text is read.
 */
import {beforeEach, describe, expect, it, vi} from 'vitest';

const allocationSource = vi.hoisted(() => vi.fn());

// source.ts and the tool client import the API client. Nothing here talks to a server.
vi.mock('$lib/api', () => ({
    zodiosApi: {get_portfolio_allocation_source_api_v1_portfolio_allocation_source_post: allocationSource},
    axiosInstance: {get: vi.fn(), post: vi.fn()},
}));

import {getClientSessionGeneration, transitionClientSession} from '$lib/stores/app/clientSession';
import {fetchPlannerSource, type SourceQuery} from './source';

const QUERY: SourceQuery = {
    asOf: '2026-09-15',
    targetCurrency: 'EUR',
    sections: ['current_distribution'],
    brokerIds: [7],
    assetIds: [11, 12, 13, 14, 15, 16],
    fxPairs: [],
};

/** One current-distribution row of the API response, as the backend serialises it. */
function weightRow(assetId: number, valuationSource: string | null) {
    return {
        weight_id: `current:asset:${assetId}`,
        asset_id: `asset:${assetId}`,
        held: valuationSource !== null,
        weight: null,
        valuation_source: valuationSource,
        valuation_reference_date: null,
        valuation_days_before_requested: null,
        valuation_stale: false,
    };
}

/** A response with nothing but a current distribution made of ``rows``. */
function sourceResponse(rows: ReturnType<typeof weightRow>[]) {
    return {
        snapshot: {as_of: '2026-09-15', target_currency: 'EUR', generated_at: '2026-09-15T12:30:00Z'},
        provenance: [],
        assets: [],
        brokers: [],
        holdings: [],
        cash_balances: [],
        prices: [],
        classifications: [],
        fx_quotes: [],
        current_distribution: {status: 'incomplete', weight_quantum: '0.0001', as_of: '2026-09-15', provenance_id: 'source:portfolio-engine', rows},
        issues: [],
    };
}

let nextUser = 40;

beforeEach(() => {
    allocationSource.mockReset();
    transitionClientSession(++nextUser);
});

describe('fetchPlannerSource — current distribution valuation codes', () => {
    it('keeps ESTIMATED_AT_COST, the code of a holding valued at its book cost, beside the codes it already knew', async () => {
        allocationSource.mockResolvedValue(
            sourceResponse([
                weightRow(11, 'MARKET_PRICE'),
                weightRow(12, 'LAST_TRADE_PRICE'),
                weightRow(13, 'MISSING'),
                weightRow(14, 'ESTIMATED_AT_COST'),
                weightRow(15, null),
                // Guard: a code the planner does not know still reaches it as null, never as free text.
                weightRow(16, 'NOT_A_VALUATION_CODE'),
            ]),
        );

        const source = await fetchPlannerSource(QUERY, getClientSessionGeneration());

        expect(allocationSource).toHaveBeenCalledTimes(1);
        const rows = source.currentDistribution?.rows ?? [];
        expect(rows.map((row) => row.asset_id)).toEqual(['asset:11', 'asset:12', 'asset:13', 'asset:14', 'asset:15', 'asset:16']);
        expect(Object.fromEntries(rows.map((row) => [row.asset_id, row.valuation_source]))).toEqual({
            'asset:11': 'MARKET_PRICE',
            'asset:12': 'LAST_TRADE_PRICE',
            'asset:13': 'MISSING',
            'asset:14': 'ESTIMATED_AT_COST',
            'asset:15': null,
            'asset:16': null,
        });
    });
});
