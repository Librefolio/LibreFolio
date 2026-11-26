/**
 * The Allocazione controller: filters remembered per page, one answer at a time, the previous answer kept.
 */
import {describe, expect, it, vi} from 'vitest';
import type {PortfolioScope} from '$lib/features/portfolio-view/portfolioDataScope';
import {createAllocationController, type AllocationControllerDeps} from './allocationController.svelte';
import {emptyFilters} from './allocationFilters';
import {makeView} from './allocation.fixture';
import type {AllocationQuery} from './allocationQuery';

const scope: PortfolioScope = {brokerIds: [1], start: '2025-11-23', end: '2026-11-23', currency: 'EUR', fullShare: false};
const ask = (overrides = {}) => ({scope, dimension: 'sector' as const, filters: emptyFilters(), ...overrides});
const answer = (base: string) => makeView({base});

function deferred<T>() {
    let resolve!: (value: T) => void;
    let reject!: (error: unknown) => void;
    const promise = new Promise<T>((res, rej) => ((resolve = res), (reject = rej)));
    return {promise, resolve, reject};
}

function make(overrides: Partial<AllocationControllerDeps> = {}, stored = '') {
    const storage = new Map<string, string>(stored ? [['allocation-filters:dashboard', stored]] : []);
    const deps: AllocationControllerDeps = {
        fetch: vi.fn(async () => answer('100')),
        read: vi.fn((key: string) => storage.get(key) ?? ''),
        write: vi.fn((key: string, value: string) => void storage.set(key, value)),
        ...overrides,
    };
    return {controller: createAllocationController('allocation-filters:dashboard', deps), deps, storage};
}

describe('filters per page', () => {
    it('open on the whole portfolio when nothing is stored', () => {
        expect(make().controller.filters).toEqual(emptyFilters());
    });

    it('open on what the page stored', () => {
        const {controller, deps} = make({}, JSON.stringify({classes: ['STOCK'], types: [], excludeBuckets: ['Unknown'], excludeAssetIds: [4]}));
        expect(controller.filters).toEqual({classes: ['STOCK'], types: [], excludeBuckets: ['Unknown'], excludeAssetIds: [4]});
        expect(deps.read).toHaveBeenCalledWith('allocation-filters:dashboard');
    });

    it('open on the whole portfolio when the stored value is corrupt', () => {
        expect(make({}, '{broken').controller.filters).toEqual(emptyFilters());
    });

    it('are written under the page key at each change, and «Rimuovi filtri» writes the first opening', () => {
        const {controller, storage} = make();
        controller.setFilters({classes: ['BOND'], types: [], excludeBuckets: [], excludeAssetIds: []});
        expect(JSON.parse(storage.get('allocation-filters:dashboard')!)).toEqual({classes: ['BOND'], types: [], excludeBuckets: [], excludeAssetIds: []});
        controller.resetFilters();
        expect(controller.filters).toEqual(emptyFilters());
        expect(JSON.parse(storage.get('allocation-filters:dashboard')!)).toEqual({classes: null, types: [], excludeBuckets: [], excludeAssetIds: []});
    });
});

describe('load', () => {
    it('sends the body built from the ask and keeps the answer', async () => {
        const {controller, deps} = make();
        expect(controller.loading).toBe(false);
        const done = controller.load(ask());
        expect(controller.loading, 'busy while the request is on its way').toBe(true);
        await done;
        expect(controller.loading).toBe(false);
        expect(controller.failed).toBe(false);
        expect(controller.response?.base).toBe('100');
        expect(vi.mocked(deps.fetch).mock.calls[0][0]).toMatchObject({dimension: 'sector', broker_ids: [1], target_currency: 'EUR'} satisfies Partial<AllocationQuery>);
    });

    it('drops an answer that comes back after a newer ask', async () => {
        const first = deferred<ReturnType<typeof makeView>>();
        const second = deferred<ReturnType<typeof makeView>>();
        const fetch = vi.fn().mockReturnValueOnce(first.promise).mockReturnValueOnce(second.promise);
        const {controller} = make({fetch});

        const a = controller.load(ask());
        const b = controller.load(ask({dimension: 'asset'}));
        second.resolve(answer('NEW'));
        await b;
        first.resolve(answer('OLD'));
        await a;

        expect(controller.response?.base).toBe('NEW');
        expect(controller.loading, 'the late old answer does not touch the busy flag either').toBe(false);
    });

    it('stays busy until the newest ask is answered', async () => {
        const first = deferred<ReturnType<typeof makeView>>();
        const second = deferred<ReturnType<typeof makeView>>();
        const {controller} = make({fetch: vi.fn().mockReturnValueOnce(first.promise).mockReturnValueOnce(second.promise)});

        const a = controller.load(ask());
        const b = controller.load(ask());
        first.resolve(answer('OLD'));
        await a;
        expect(controller.loading).toBe(true);
        second.resolve(answer('NEW'));
        await b;
        expect(controller.loading).toBe(false);
    });

    it('keeps the previous answer on a failure, and says it failed; the next ask clears the flag', async () => {
        const fetch = vi.fn().mockResolvedValueOnce(answer('100')).mockRejectedValueOnce(new Error('boom')).mockResolvedValueOnce(answer('200'));
        const {controller} = make({fetch});
        await controller.load(ask());
        await controller.load(ask({dimension: 'type'}));
        expect(controller.failed).toBe(true);
        expect(controller.loading).toBe(false);
        expect(controller.response?.base, 'the screen does not blank').toBe('100');
        const retry = controller.load(ask());
        expect(controller.failed).toBe(false);
        await retry;
        expect(controller.response?.base).toBe('200');
    });

    it('drops everything after dispose', async () => {
        const pending = deferred<ReturnType<typeof makeView>>();
        const {controller} = make({fetch: vi.fn().mockReturnValue(pending.promise)});
        const done = controller.load(ask());
        controller.dispose();
        pending.resolve(answer('LATE'));
        await done;
        expect(controller.response).toBeNull();
        await controller.load(ask());
        expect(controller.response).toBeNull();
    });
});
