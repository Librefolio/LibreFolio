/**
 * The body of POST /portfolio/allocation is the report's scope plus the tab's choices, and nothing else.
 */
import {describe, expect, it} from 'vitest';
import {scopeKey, type PortfolioScope} from '$lib/features/portfolio-view/portfolioDataScope';
import {allocationAskKey, buildAllocationQuery, DEFAULT_ALLOCATION_DIMENSION, normalizeAllocation, type RawAllocationResponse} from './allocationQuery';
import {emptyFilters} from './allocationFilters';

const dashboard: PortfolioScope = {brokerIds: [1, 2], start: '2025-11-23', end: '2026-11-23', currency: 'EUR', fullShare: false};
const broker: PortfolioScope = {brokerIds: [9], start: 'min', end: '2026-11-23', currency: undefined, fullShare: true};

describe('buildAllocationQuery', () => {
    it('a Dashboard first opening: the scope, the default dimension, no filter fields', () => {
        expect(buildAllocationQuery({scope: dashboard, dimension: DEFAULT_ALLOCATION_DIMENSION, filters: emptyFilters()})).toEqual({
            dimension: 'sector',
            broker_ids: [1, 2],
            date_range: {start: '2025-11-23', end: '2026-11-23'},
            target_currency: 'EUR',
        });
    });

    it('a broker page counts the broker whole and passes the «min» sentinel as the report does', () => {
        const body = buildAllocationQuery({scope: broker, dimension: 'asset', filters: emptyFilters()});
        expect(body.apply_ownership_share).toBe(false);
        expect(body.date_range).toEqual({start: 'min', end: '2026-11-23'});
        expect(body).not.toHaveProperty('target_currency');
    });

    it('never widens the scope: no brokers, no broker_ids field (the caller waits for them)', () => {
        const body = buildAllocationQuery({scope: {...dashboard, brokerIds: undefined}, dimension: 'type', filters: emptyFilters()});
        expect(body).not.toHaveProperty('broker_ids');
    });

    it('carries the filters: classes (also the empty list), buckets, assets, history', () => {
        const body = buildAllocationQuery({scope: dashboard, dimension: 'geography', filters: {classes: [], types: [], excludeBuckets: ['Unknown'], excludeAssetIds: [3]}, includeHistory: true});
        expect(body).toMatchObject({dimension: 'geography', classes: [], exclude_buckets: ['Unknown'], exclude_asset_ids: [3], include_history: true});
        expect(buildAllocationQuery({scope: dashboard, dimension: 'geography', filters: {classes: ['STOCK'], types: [], excludeBuckets: [], excludeAssetIds: []}}).classes).toEqual(['STOCK']);
    });

    it('carries the types kept on their own, only beside a list of classes', () => {
        const ask = (filters: Parameters<typeof buildAllocationQuery>[0]['filters']) => buildAllocationQuery({scope: dashboard, dimension: 'sector', filters});
        expect(ask({classes: ['BOND'], types: ['ETF_STOCK'], excludeBuckets: [], excludeAssetIds: []})).toMatchObject({classes: ['BOND'], types: ['ETF_STOCK']});
        expect(ask({classes: ['BOND'], types: [], excludeBuckets: [], excludeAssetIds: []})).not.toHaveProperty('types');
        expect(ask({classes: null, types: ['ETF_STOCK'], excludeBuckets: [], excludeAssetIds: []})).not.toHaveProperty('types');
    });

    it('does not share arrays with the filters it was given', () => {
        const filters = {classes: ['STOCK'], types: [], excludeBuckets: [], excludeAssetIds: [1]};
        const body = buildAllocationQuery({scope: dashboard, dimension: 'sector', filters});
        (body.classes as string[]).push('BOND');
        (body.exclude_asset_ids as number[]).push(2);
        expect(filters).toEqual({classes: ['STOCK'], types: [], excludeBuckets: [], excludeAssetIds: [1]});
    });
});

describe('allocationAskKey', () => {
    it('begins with the report’s scope key, and moves with the dimension, the filters and the history flag', () => {
        const ask = {scope: dashboard, dimension: 'sector' as const, filters: emptyFilters()};
        const key = allocationAskKey(ask);
        expect(key.startsWith(scopeKey(dashboard))).toBe(true);
        expect(allocationAskKey({...ask, dimension: 'asset'})).not.toBe(key);
        expect(allocationAskKey({...ask, filters: {...emptyFilters(), classes: ['STOCK']}})).not.toBe(key);
        expect(allocationAskKey({...ask, includeHistory: true})).not.toBe(key);
        expect(allocationAskKey({...ask})).toBe(key);
    });
});

describe('normalizeAllocation', () => {
    it('fills the lists the generated client leaves optional, and reads the optional scalars as text or null', () => {
        const raw = {
            currency: 'EUR',
            dimension: 'sector',
            portfolio_total: '100.00',
            base: '40.00',
            outside: {amount: '60.00'},
            excluded: {amount: '0.00'},
        } as unknown as RawAllocationResponse;
        expect(normalizeAllocation(raw)).toEqual({
            currency: 'EUR',
            date_from: null,
            as_of: null,
            dimension: 'sector',
            applicable_buckets: [],
            portfolio_total: '100.00',
            base: '40.00',
            base_share_of_portfolio: null,
            slices: [],
            outside: {amount: '60.00', by_class: []},
            excluded: {amount: '0.00', by_bucket: [], by_asset: [], unattributable: []},
            classes: [],
            assets: [],
            history: null,
            matrix: null,
        });
    });

    it('keeps what the backend sent: shares as written, a slice and an asset with their nulls', () => {
        const raw = {
            currency: 'EUR',
            as_of: '2026-11-23',
            dimension: 'asset',
            portfolio_total: '100.00',
            base: '40.00',
            base_share_of_portfolio: '40.00',
            slices: [{key: '1', asset_id: 1, amount: '40.00', share_of_selection: '100.00', share_of_portfolio: '40.00'}],
            outside: {amount: '60.00', by_class: [{asset_class: 'BOND', amount: '60.00'}]},
            excluded: {amount: '0.00'},
            assets: [{asset_id: 1, asset_class: 'STOCK', amount: '40.00', name: 'A', ticker: 'AA'}],
        } as unknown as RawAllocationResponse;
        const view = normalizeAllocation(raw);
        expect(view.as_of).toBe('2026-11-23');
        expect(view.base_share_of_portfolio).toBe('40.00');
        expect(view.slices[0]).toEqual({key: '1', asset_id: 1, amount: '40.00', share_of_selection: '100.00', share_of_portfolio: '40.00', assets: []});
        expect(view.outside.by_class).toEqual([{asset_class: 'BOND', amount: '60.00'}]);
        expect(view.assets[0]).toEqual({asset_id: 1, asset_class: 'STOCK', amount: '40.00', name: 'A', ticker: 'AA', asset_type: null, icon_url: null});
    });
});
