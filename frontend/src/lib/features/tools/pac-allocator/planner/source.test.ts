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
import {effectiveTaxRegime} from '$lib/features/brokers/profile/brokerOperatingProfile';
import {fetchPlannerSource, fromPlannerId, toPlannerId, type SourceQuery} from './source';

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

describe('fetchPlannerSource — the broker operating profile (P3 of project 67, source 1.1.0)', () => {
    /** A served broker row with its operating profile, every field as the backend writes it (sale side and regime included). */
    const PROFILE = {
        profile_version: 1,
        order_modes: [
            {
                currency: 'EUR',
                capability: {kind: 'whole_quantity', capability_id: 'mode:EUR', quantity_unit: 'asset_unit', quantity_step: '1'},
                fees: [
                    {fee_schedule_id: 'fee:EUR:buy', capability_id: 'mode:EUR', side: 'buy', fixed_fee: null, rate: '0.0019', variable_floor: {amount: '1.5', currency: 'EUR'}, variable_cap: {kind: 'none'}},
                    {fee_schedule_id: 'fee:EUR:sell', capability_id: 'mode:EUR', side: 'sell', fixed_fee: {amount: '5', currency: 'EUR'}, rate: '0', variable_floor: null, variable_cap: {kind: 'none'}},
                ],
            },
        ],
        conversion_mode: 'automatic',
        tax_regime: 'administered',
    };

    function brokerRow(changes: Record<string, unknown> = {}) {
        return {
            broker_id: 'broker:7',
            source_broker_id: 7,
            name: 'Profile probe',
            icon_url: null,
            portal_url: null,
            default_import_plugin: null,
            access_role: 'OWNER',
            ownership_share: '1',
            observed_currencies: ['EUR'],
            active: true,
            allow_cash_overdraft: false,
            allow_asset_shorting: false,
            operating_profile_status: 'available',
            operating_profile: PROFILE,
            provenance_id: 'source:broker-domain',
            ...changes,
        };
    }

    it('maps the profile of a source Broker, sell side and tax regime included', async () => {
        allocationSource.mockResolvedValue({...sourceResponse([]), current_distribution: null, brokers: [brokerRow()]});

        const source = await fetchPlannerSource({...QUERY, sections: ['brokers']}, getClientSessionGeneration());

        expect(source.brokers).toHaveLength(1);
        expect(source.brokers[0]).toMatchObject({broker_id: 'broker:7', operating_profile_status: 'available'});
        expect(source.brokers[0].operating_profile).toEqual(PROFILE);
    });

    it('a Broker without a profile maps to a null profile', async () => {
        allocationSource.mockResolvedValue({...sourceResponse([]), current_distribution: null, brokers: [brokerRow({operating_profile_status: 'not_available', operating_profile: null})]});

        const source = await fetchPlannerSource({...QUERY, sections: ['brokers']}, getClientSessionGeneration());

        expect(source.brokers[0]).toMatchObject({operating_profile_status: 'not_available', operating_profile: null});
    });

    it('an absent tax regime reads «declarative», as the backend reads it', async () => {
        const {tax_regime: _regime, ...withoutRegime} = PROFILE;
        allocationSource.mockResolvedValue({...sourceResponse([]), current_distribution: null, brokers: [brokerRow({operating_profile: withoutRegime})]});

        const source = await fetchPlannerSource({...QUERY, sections: ['brokers']}, getClientSessionGeneration());

        expect(source.brokers[0].operating_profile).not.toHaveProperty('tax_regime');
        expect(effectiveTaxRegime(source.brokers[0].operating_profile)).toBe('declarative');
        expect(effectiveTaxRegime({profile_version: 1, tax_regime: 'administered'})).toBe('administered');
        expect(effectiveTaxRegime(null)).toBe('declarative');
    });
});

describe('fetchPlannerSource — positions (F3a of project 67, step 4)', () => {
    /** One served holding row: 10 units in custody, half of them the user's. */
    function holdingRow() {
        return {holding_id: 'holding:asset:11:broker:7', asset_id: 'asset:11', broker_id: 'broker:7', custody_quantity: '10', ownership_share: '0.5', economic_quantity: '5', quantity_unit: 'asset_unit', provenance_id: 'source:portfolio-ledger'};
    }

    it('holdings map quantity and share for the rebalancer', async () => {
        allocationSource.mockResolvedValue({...sourceResponse([]), current_distribution: null, holdings: [holdingRow()]});

        const source = await fetchPlannerSource({...QUERY, sections: ['holdings']}, getClientSessionGeneration(), undefined, {positions: true});

        expect(source.holdings).toEqual([{holding_id: 'holding:asset:11:broker:7', asset_id: 'asset:11', broker_id: 'broker:7', provenance_id: 'source:portfolio-ledger', quantity: {custody: '10', ownershipShare: '0.5', economic: '5'}}]);
    });

    it('quantities served with trailing zeros reach the planner in canonical form (G5-3)', async () => {
        // The ledger serves its scale (`7.0000000000`); the quantity field showed it whole, cut at 390 px.
        allocationSource.mockResolvedValue({...sourceResponse([]), current_distribution: null, holdings: [{...holdingRow(), custody_quantity: '17.5000000000', ownership_share: '0.4000000000', economic_quantity: '7.0000000000'}]});

        const source = await fetchPlannerSource({...QUERY, sections: ['holdings']}, getClientSessionGeneration(), undefined, {positions: true});

        expect(source.holdings[0].quantity).toEqual({custody: '17.5', ownershipShare: '0.4', economic: '7'});
    });

    it('the PAC source mapping still drops quantities', async () => {
        allocationSource.mockResolvedValue({...sourceResponse([]), current_distribution: null, holdings: [holdingRow()]});

        const source = await fetchPlannerSource({...QUERY, sections: ['holdings']}, getClientSessionGeneration());

        expect(source.holdings).toEqual([{holding_id: 'holding:asset:11:broker:7', asset_id: 'asset:11', broker_id: 'broker:7', provenance_id: 'source:portfolio-ledger', quantity: null}]);
    });
});

/**
 * The planner's identifiers (`toPlannerId`): a sector such as «Health Care» travels encoded, `enc:` plus its bytes. The
 * result's exposure rows carry that id; `fromPlannerId` reads the name back, exactly, so a chart can find the sector's
 * colour by its name.
 */
describe('fromPlannerId — the name a planner id was made from', () => {
    it.each(['Health Care', 'Real Estate', 'Consumer Discretionary', 'snake_case', 'a+b', 'Énergie à 100%', 'enc:already'])('reads back %s', (name) => {
        const id = toPlannerId(name) as string;
        expect(fromPlannerId(id)).toBe(name);
    });

    it('leaves a plain identifier as it is', () => {
        for (const id of ['STOCK', 'Energy', 'USA', 'allocation.uncategorised']) expect(fromPlannerId(id)).toBe(id);
    });
});
