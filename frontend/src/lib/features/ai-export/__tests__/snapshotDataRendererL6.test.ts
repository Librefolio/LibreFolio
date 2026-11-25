/**
 * @vitest-environment node
 *
 * 78 L6 · S1 + S7 — the renderer knows the three versions the lot moves, and prints their new data compactly.
 *
 * `portfolio.asset_market_context` and `broker.asset_market_context` (v2) carry the daily
 * return volatility; `portfolio.allocations_cash` (v3) carries the cash of each broker, the basis it counts on (the
 * user's share) and the cash in transit as a figure of its own. A version missing from
 * `COMPACT_COMPONENT_VERSIONS` falls back to YAML: each one renders compactly, and its new data is in the text.
 * Pins structure only: never a wording.
 */
import {describe, expect, it} from 'vitest';

import {renderSnapshotDataText} from '../templates/snapshotDataRenderer';

const FALLBACK = 'PAYLOAD YAML FALLBACK';
const directory = {
    assets: [{asset_id: 1, display_name: 'Close Only ETF', ticker: 'CLO', currency: 'EUR', asset_type: 'ETF', quote_base_quantity: 1}],
    brokers: [
        {broker_id: 5, display_name: 'First Broker'},
        {broker_id: 7, display_name: 'Second Broker'},
    ],
    fx_pairs: [],
};

function render(componentId: string, componentVersion: number, payload: Record<string, unknown>, target: Record<string, unknown> = {kind: 'portfolio'}) {
    const section = {component_id: componentId, component_version: componentVersion, schema_id: componentId, schema_version: 1, payload};
    return renderSnapshotDataText([section], target, directory).content;
}

const marketRow = {entity_id: 'asset:1', value_unit: 'EUR', observation_count: 63, current_value: 100.5, daily_return_volatility_ratio: 0.0123};

describe('78 L6: the versions of S1 and S7 render compactly', () => {
    it.each([
        ['portfolio.asset_market_context', {kind: 'portfolio'}],
        ['broker.asset_market_context', {kind: 'broker', broker_id: 5}],
    ] as const)('%s v2 prints the daily return volatility, not as YAML', (componentId, target) => {
        const content = render(componentId, 2, {policy_code: 'portfolio_asset_snapshot_v2', entities: [marketRow]}, target);
        expect(content).not.toContain(FALLBACK);
        expect(content).toContain('daily_return_volatility_percent');
        expect(content).toContain('1.23%');
    });

    it('portfolio.allocations_cash v3 prints the cash of each broker by its public reference, not as YAML', () => {
        const content = render('portfolio.allocations_cash', 3, {
            by_type: [],
            by_sector: [],
            by_geography: [],
            cash_total: {code: 'EUR', amount: '1500'},
            cash_by_broker: [
                {broker_id: 5, cash_total: {code: 'EUR', amount: '1000'}, cash_balances: [{code: 'EUR', amount: '1000'}]},
                {broker_id: 7, cash_total: {code: 'EUR', amount: '500'}, cash_balances: [{code: 'USD', amount: '540'}]},
            ],
            cash_by_broker_basis: 'user_ownership_share',
            cash_in_transit: {code: 'EUR', amount: '250'},
        });
        expect(content).not.toContain(FALLBACK);
        // One row per broker, by its public reference (the names stay in the BROKERS directory)
        expect(content).toContain('TABLE cash_by_broker');
        expect(content).toMatch(/\|1\|B1\|EUR\|1000\|/);
        expect(content).toMatch(/\|2\|B2\|EUR\|500\|/);
        // The basis beside the list, and the cash in transit as a figure of its own
        expect(content).toContain('cash_by_broker_basis');
        expect(content).toContain('user_ownership_share');
        expect(content).toMatch(/cash_in_transit[^\n]*250/);
    });
});
