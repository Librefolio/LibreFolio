/**
 * A hand-made answer of `POST /portfolio/allocation` for the component tests of the tab. The numbers are the mockup's
 * (a portfolio of 80 000 €, a base of 36 880 €): base + outside + excluded = the net worth. They are the backend's in the
 * real world; a test only shows them.
 */
import type {AllocationResponse} from './allocationQuery';

export function makeView(overrides: Partial<AllocationResponse> = {}): AllocationResponse {
    return {
        currency: 'EUR',
        date_from: '2025-11-23',
        as_of: '2026-11-23',
        dimension: 'geography',
        applicable_buckets: ['Unknown'],
        portfolio_total: '80000.00',
        base: '36880.00',
        base_share_of_portfolio: '46.10',
        slices: [
            {key: 'USA', asset_id: null, amount: '23600.00', share_of_selection: '64.00', share_of_portfolio: '29.50', assets: []},
            {key: 'Unknown', asset_id: null, amount: '4120.00', share_of_selection: null, share_of_portfolio: '5.15', assets: []},
        ],
        outside: {
            amount: '39000.00',
            by_class: [
                {asset_class: 'BOND', amount: '22000.00'},
                {asset_class: 'FUND', amount: '5000.00'},
                {asset_class: 'Liquidity', amount: '5000.00'},
                {asset_class: 'CRYPTO', amount: '4000.00'},
                {asset_class: 'COMMODITY', amount: '3000.00'},
            ],
        },
        excluded: {
            amount: '4120.00',
            by_bucket: [{key: 'Unknown', amount: '4120.00'}],
            by_asset: [],
            unattributable: [{reason: 'in_transit', amount: '0.00'}],
        },
        classes: [
            {asset_class: 'STOCK', amount: '41000.00'},
            {asset_class: 'BOND', amount: '22000.00'},
            {asset_class: 'Liquidity', amount: '5000.00'},
        ],
        assets: [
            {asset_id: 1, asset_class: 'STOCK', amount: '19600.00', name: 'World ETF', ticker: 'WRLD', asset_type: 'ETF_STOCK', icon_url: null},
            {asset_id: 2, asset_class: 'STOCK', amount: '4000.00', name: 'Apple Inc.', ticker: 'AAPL', asset_type: 'STOCK', icon_url: null},
            {asset_id: 3, asset_class: 'BOND', amount: '22000.00', name: 'Gov Bond', ticker: null, asset_type: 'BOND', icon_url: null},
        ],
        history: null,
        matrix: null,
        ...overrides,
    };
}
