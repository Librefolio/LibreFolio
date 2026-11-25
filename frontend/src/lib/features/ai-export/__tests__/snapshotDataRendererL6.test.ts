/**
 * @vitest-environment node
 *
 * 78 L6 · S1 + S7 — the renderer knows the three versions the lot moves, and prints their new data compactly.
 *
 * `portfolio.asset_market_context` and `broker.asset_market_context` (v2) and `fx.market_summary` (v2) carry the daily
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

    it('fx.market_summary v2 prints the daily return volatility, not as YAML', () => {
        const row = {...marketRow, entity_id: 'fx:EUR/USD', value_unit: 'USD_per_EUR'};
        const content = render('fx.market_summary', 2, {policy_code: 'fx_market_context_v2', entities: [row]}, {kind: 'fx', base_currency: 'EUR', quote_currency: 'USD'});
        expect(content).not.toContain(FALLBACK);
        expect(content).toContain('daily_return_volatility_percent');
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

/** The columns a market row of the portfolio does not report: before 78 L6 S2 they were null in every row. */
const NOT_REPORTED_BY_PORTFOLIO = ['ema_20', 'atr_14', 'bollinger_lower', 'bollinger_middle', 'bollinger_upper', 'ppo_12_26_9_percent', 'roc_20_percent'];

function omittedColumns(content: string): string[] {
    return content
        .split('\n')
        .filter((line) => line.startsWith('omitted_null_columns=') && !line.includes(' '))
        .flatMap((line) => line.slice('omitted_null_columns='.length).split(','));
}

describe('78 L6 S2: a column the component does not report is not «unavailable»', () => {
    it('the portfolio row names only a declared column that could not be computed', () => {
        // The payload as the backend writes it now: no key for a column the row does not declare; ema_200 declared, null
        const row = {entity_id: 'asset:1', portfolio_weight_ratio: 0.5, value_unit: 'EUR', observation_count: 3, current_value: 100.5, ema_200: null, daily_return_volatility_ratio: 0.0123};
        const content = render('portfolio.asset_market_context', 2, {policy_code: 'portfolio_asset_snapshot_v2', entities: [row]});
        const omitted = omittedColumns(content);
        expect(omitted).toContain('ema_200');
        for (const column of NOT_REPORTED_BY_PORTFOLIO) expect(omitted).not.toContain(column);
    });

    it('asset.position_market_context v2 renders compactly, with the volatility and without PPO, ROC or a weight', () => {
        const row = {entity_id: 'asset:1', value_unit: 'EUR', observation_count: 63, current_value: 100.5, ema_20: 99.1, atr_14: 1.2, daily_return_volatility_ratio: 0.0123};
        const content = render('asset.position_market_context', 2, {policy_code: 'asset_position_context_v2', entities: [row]}, {kind: 'asset', asset_id: 1});
        expect(content).not.toContain(FALLBACK);
        expect(content).toContain('1.23%');
        const omitted = omittedColumns(content);
        for (const column of ['ppo_12_26_9_percent', 'roc_20_percent', 'portfolio_weight_percent']) expect(omitted).not.toContain(column);
    });
});
