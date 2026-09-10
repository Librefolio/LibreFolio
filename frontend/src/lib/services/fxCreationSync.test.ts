/**
 * Browser-background creation completion, without a browser/backend.
 * API promises and host refresh promises are independently released by the test.
 * The real formatter runs with an injected translator, not catalogue strings.
 */
import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';
import type {Writable} from 'svelte/store';
import type {NotifyOptions} from '$lib/stores/app/notify.svelte';

vi.mock('$lib/api', () => ({zodiosApi: {sync_rates_api_v1_fx_currencies_sync_post: vi.fn()}}));
vi.mock('$lib/i18n', async () => {
    const {writable} = await import('svelte/store');
    return {_: writable((key: string) => `injected:${key}`)};
});
vi.mock('$lib/stores/app/notify.svelte', () => ({notify: vi.fn()}));
vi.mock('$lib/stores/app/toastStore.svelte', () => ({toasts: {show: vi.fn(), error: vi.fn()}}));
vi.mock('$lib/stores/fxStoreRegistry', () => ({getFxStore: vi.fn()}));
vi.mock('$lib/stores/reference/fxRoutesStore', () => ({invalidateFxRoutes: vi.fn()}));
vi.mock('$lib/stores/currencyGraphStore', () => ({getCachedFxProviders: () => []}));
vi.mock('$lib/stores/reference/currencyStore', () => ({
    getCurrencyInfo: (code: string) => ({code, flag_emoji: `fixture-flag-${code}`}),
}));
vi.mock('$lib/utils/sync/syncToastHelpers', async (importOriginal) => {
    const original = await importOriginal<typeof import('$lib/utils/sync/syncToastHelpers')>();
    return {...original, buildFxSyncToast: vi.fn(original.buildFxSyncToast)};
});

import {finishFxPairCreation, subscribeFxCreationSyncCompleted, type FxPairCreationContext, type FxPairSyncCompleteDetail} from './fxCreationSync';
import {zodiosApi} from '$lib/api';
import {_} from '$lib/i18n';
import {notify} from '$lib/stores/app/notify.svelte';
import {getClientSessionGeneration, transitionClientSession} from '$lib/stores/app/clientSession';
import {getFxStore} from '$lib/stores/fxStoreRegistry';
import {invalidateFxRoutes} from '$lib/stores/reference/fxRoutesStore';
import {buildFxSyncToast} from '$lib/utils/sync/syncToastHelpers';

const syncRates = vi.mocked(zodiosApi.sync_rates_api_v1_fx_currencies_sync_post);
type Response = Awaited<ReturnType<typeof zodiosApi.sync_rates_api_v1_fx_currencies_sync_post>>;
type Result = Response['results'][number];
const RANGE = {start: '2024-03-01', end: '2024-03-31'};
const MAIN = 'EUR-GBP';
const INTERMEDIATE = 'EUR-USD';
const invalidations = new Map<string, ReturnType<typeof vi.fn>>();
const listenerCleanups = new Set<() => void>();

function listen(listener: (detail: FxPairSyncCompleteDetail) => void | Promise<void>) {
    const unsubscribe = subscribeFxCreationSyncCompleted(listener);
    listenerCleanups.add(unsubscribe);
    return unsubscribe;
}

function deferred<T>() {
    let resolve!: (value: T) => void;
    let reject!: (reason: unknown) => void;
    const promise = new Promise<T>((yes, no) => {
        resolve = yes;
        reject = no;
    });
    return {promise, resolve, reject};
}

function result(pair: string, status: Result['status'] = 'ok'): Result {
    return {pair, status, points_fetched: 11, points_changed: 4, provider_used: 'MOCKFX'};
}

function response(results: Result[], errors: string[] = []): Response {
    return {
        results,
        success_count: results.filter((item) => item.status === 'ok').length,
        date_range: RANGE,
        total_points_changed: results.reduce((sum, item) => sum + (item.points_changed ?? 0), 0),
        errors,
    };
}

function context(overrides: Partial<FxPairCreationContext> = {}) {
    return {
        detail: {base: 'EUR', quote: 'GBP', slug: MAIN, hasRealProvider: true, autoSyncStarted: true},
        pairs: [MAIN],
        ...RANGE,
        sessionGeneration: getClientSessionGeneration(),
        oncreated: vi.fn(),
        onclose: vi.fn(),
        onsynced: vi.fn(),
        ...overrides,
    };
}

function events(): NotifyOptions[] {
    return vi.mocked(notify).mock.calls.map(([event]) => event);
}

function completionEvent() {
    const completed = events().filter((event) => event.name === 'fx.pair.creation-sync-completed');
    expect(completed).toHaveLength(1);
    const [event] = completed;
    return event!;
}

function toastEvents() {
    return events().filter((event) => event.toast !== undefined);
}

beforeEach(() => {
    vi.clearAllMocks();
    invalidations.clear();
    vi.stubGlobal('window', {});
    transitionClientSession('owned-fx-sync-context');
    syncRates.mockReset().mockResolvedValue(response([result(MAIN)]));
    vi.mocked(getFxStore).mockImplementation((slug) => {
        if (!invalidations.has(slug)) invalidations.set(slug, vi.fn());
        return {invalidateAll: invalidations.get(slug)!} as unknown as ReturnType<typeof getFxStore>;
    });
});

afterEach(() => {
    for (const unsubscribe of listenerCleanups) unsubscribe();
    listenerCleanups.clear();
    vi.unstubAllGlobals();
});

describe('finishFxPairCreation — response identity and honest feedback', () => {
    it('matches primary and created intermediates by slug, ignoring an unrelated failed row', async () => {
        const primary = result(MAIN);
        const intermediate = result(INTERMEDIATE);
        syncRates.mockResolvedValue(response([result('JPY-USD', 'failed'), intermediate, primary]));
        const ctx = context({pairs: [MAIN, INTERMEDIATE]});
        await finishFxPairCreation(ctx);

        expect(syncRates.mock.calls.map(([body]) => body)).toEqual([{pairs: [MAIN, INTERMEDIATE], ...RANGE}]);
        expect(ctx.oncreated).toHaveBeenCalledExactlyOnceWith(ctx.detail);
        expect(ctx.onclose).toHaveBeenCalledTimes(1);
        expect(ctx.onsynced).toHaveBeenCalledExactlyOnceWith(expect.objectContaining({slug: MAIN, pairs: [MAIN, INTERMEDIATE], outcome: 'ok', missingPairs: []}));
        expect(vi.mocked(buildFxSyncToast).mock.calls.map(([item, slug]) => ({pair: item.pair, slug}))).toEqual([
            {pair: MAIN, slug: MAIN},
            {pair: INTERMEDIATE, slug: INTERMEDIATE},
        ]);
        expect(toastEvents()).toHaveLength(1);
        expect(completionEvent().toast?.variant).toBe('success');
        for (const slug of [MAIN, INTERMEDIATE]) expect(completionEvent().toast?.message).toContain(`href="/fx/${slug}"`);
        expect(completionEvent().toast?.message).not.toContain('JPY-USD');
        expect([...invalidations.keys()].sort()).toEqual([MAIN, INTERMEDIATE].sort());
    });

    it.each([
        {status: 'partial' as const, variant: 'warning', outcome: 'partial'},
        {status: 'failed' as const, variant: 'error', outcome: 'failed'},
        {status: 'skipped' as const, variant: 'info', outcome: 'skipped'},
    ])('uses $variant for a $status source and still calls the completion refresh', async ({status, variant, outcome}) => {
        syncRates.mockResolvedValue(response([result(MAIN, status)]));
        const ctx = context();
        await finishFxPairCreation(ctx);
        expect(syncRates.mock.calls.map(([body]) => body)).toEqual([{pairs: [MAIN], ...RANGE}]);
        expect(ctx.onsynced).toHaveBeenCalledExactlyOnceWith(expect.objectContaining({outcome}));
        expect(toastEvents()).toHaveLength(1);
        expect(completionEvent().toast?.variant).toBe(variant);
        expect(completionEvent().toast?.message).toContain(`href="/fx/${MAIN}"`);
        expect(buildFxSyncToast).toHaveBeenCalledWith(expect.objectContaining({pair: MAIN, status}), MAIN, expect.any(Function), undefined, expect.any(Function), {outerFlags: true, linkToDetail: true});
    });

    it.each([
        {status: 'partial' as const, variant: 'warning', outcome: 'partial'},
        {status: 'failed' as const, variant: 'error', outcome: 'failed'},
        {status: 'skipped' as const, variant: 'warning', outcome: 'partial'},
    ])('never reports green when a created intermediate is $status', async ({status, variant, outcome}) => {
        syncRates.mockResolvedValue(response([result(INTERMEDIATE, status), result(MAIN)]));
        const ctx = context({pairs: [MAIN, INTERMEDIATE]});
        await finishFxPairCreation(ctx);
        expect(syncRates.mock.calls.map(([body]) => body)).toEqual([{pairs: [MAIN, INTERMEDIATE], ...RANGE}]);
        expect(completionEvent().detail).toMatchObject({outcome, pairs: [MAIN, INTERMEDIATE], missingPairs: []});
        expect(completionEvent().toast?.variant).toBe(variant);
        expect(toastEvents()).toHaveLength(1);
        expect(ctx.oncreated).toHaveBeenCalledTimes(1);
    });

    it.each([
        {name: 'missing primary', rows: [result(INTERMEDIATE)], missing: [MAIN]},
        {name: 'missing intermediate', rows: [result(MAIN)], missing: [INTERMEDIATE]},
        {name: 'empty response', rows: [], missing: [MAIN, INTERMEDIATE]},
    ])('treats $name as failure, with the missing pair explicitly identified', async ({rows, missing}) => {
        syncRates.mockResolvedValue(response(rows));
        const ctx = context({pairs: [MAIN, INTERMEDIATE]});
        await finishFxPairCreation(ctx);
        expect(syncRates.mock.calls.map(([body]) => body)).toEqual([{pairs: [MAIN, INTERMEDIATE], ...RANGE}]);
        expect(completionEvent().detail).toMatchObject({outcome: 'failed', missingPairs: missing, configurationSaved: true});
        expect(completionEvent().toast?.variant).toBe('error');
        expect(toastEvents()).toHaveLength(1);
        for (const slug of missing) expect(completionEvent().toast?.message).toContain(`href="/fx/${slug}"`);
    });

    it('does not turn no response into an unhandled rejection or a creation-success toast', async () => {
        syncRates.mockResolvedValue(undefined as never);
        const ctx = context();
        await finishFxPairCreation(ctx);
        expect(syncRates.mock.calls.map(([body]) => body)).toEqual([{pairs: [MAIN], ...RANGE}]);
        expect(completionEvent().detail).toMatchObject({outcome: 'failed', missingPairs: [MAIN]});
        expect(completionEvent().toast?.variant).toBe('error');
        expect(ctx.onsynced).toHaveBeenCalledTimes(1);
        expect(toastEvents()).toHaveLength(1);
    });

    it('reports operation-level errors even when the pair row says ok', async () => {
        syncRates.mockResolvedValue(response([result(MAIN)], ['owned-operation-error']));
        await finishFxPairCreation(context());
        expect(syncRates.mock.calls.map(([body]) => body)).toEqual([{pairs: [MAIN], ...RANGE}]);
        expect(completionEvent().detail).toMatchObject({outcome: 'failed', operationErrors: ['owned-operation-error']});
        expect(completionEvent().toast?.variant).toBe('error');
        expect(toastEvents()).toHaveLength(1);
    });

    it('turns a transport failure into one linked error, keeping configuration success separate', async () => {
        syncRates.mockRejectedValue(new Error('owned-transport-failure'));
        const ctx = context();
        await finishFxPairCreation(ctx);
        expect(syncRates.mock.calls.map(([body]) => body)).toEqual([{pairs: [MAIN], ...RANGE}]);
        expect(ctx.oncreated).toHaveBeenCalledTimes(1);
        expect(ctx.onclose).toHaveBeenCalledTimes(1);
        expect(ctx.onsynced).toHaveBeenCalledExactlyOnceWith(expect.objectContaining({outcome: 'transport-error'}));
        expect(toastEvents()).toHaveLength(1);
        expect(completionEvent().detail).toMatchObject({configurationSaved: true, transportError: 'owned-transport-failure'});
        expect(completionEvent().toast?.variant).toBe('error');
        expect(completionEvent().toast?.message).toContain(`href="/fx/${MAIN}"`);
    });
});

describe('finishFxPairCreation — lifecycle and host refresh ordering', () => {
    it('closes and starts sync without waiting for creation refresh, then refreshes after that refresh settles', async () => {
        const initialRefresh = deferred<void>();
        const pending = deferred<Response>();
        const ctx = context({oncreated: vi.fn(() => initialRefresh.promise)});
        syncRates.mockReturnValue(pending.promise);
        const done = finishFxPairCreation(ctx);
        try {
            expect(ctx.oncreated).toHaveBeenCalledTimes(1);
            expect(ctx.onclose).toHaveBeenCalledTimes(1);
            expect(syncRates.mock.calls.map(([body]) => body)).toEqual([{pairs: [MAIN], ...RANGE}]);
            expect(ctx.onsynced).not.toHaveBeenCalled();
            expect(toastEvents()).toEqual([]);

            pending.resolve(response([result(MAIN)]));
            // First invalidation proves the response handler ran; the old
            // refresh is still held, so it cannot overwrite the final refresh.
            await vi.waitFor(() => expect(invalidations.get(MAIN)).toHaveBeenCalledTimes(1));
            expect(ctx.onsynced).not.toHaveBeenCalled();
            expect(toastEvents()).toEqual([]);

            initialRefresh.resolve();
            await done;
            expect(invalidations.get(MAIN)).toHaveBeenCalledTimes(2);
            expect(ctx.onsynced).toHaveBeenCalledTimes(1);
            expect(ctx.oncreated).toHaveBeenCalledTimes(1);
            expect(toastEvents()).toHaveLength(1);
        } finally {
            initialRefresh.resolve();
            pending.resolve(response([result(MAIN)]));
            await done;
        }
    });

    describe('FX creation completion subscriptions', () => {
        it('notifies a page mounted during sync once, after final invalidation and before the final toast', async () => {
            const pending = deferred<Response>();
            const refresh = deferred<void>();
            const listenerRefresh = deferred<void>();
            const ctx = context({pairs: [MAIN, INTERMEDIATE], oncreated: vi.fn(() => refresh.promise)});
            syncRates.mockReturnValue(pending.promise);
            const done = finishFxPairCreation(ctx);
            const observed: FxPairSyncCompleteDetail[] = [];
            const listener = vi.fn((completion: FxPairSyncCompleteDetail) => {
                observed.push(completion);
                for (const pair of completion.pairs) expect(invalidations.get(pair)).toHaveBeenCalledTimes(2);
                expect(toastEvents()).toEqual([]);
                return listenerRefresh.promise;
            });
            // A detail route need not exist at configuration commit time.
            listen(listener);
            try {
                expect(syncRates.mock.calls.map(([body]) => body)).toEqual([{pairs: [MAIN, INTERMEDIATE], ...RANGE}]);
                expect(listener).not.toHaveBeenCalled();
                pending.resolve(response([result(INTERMEDIATE), result(MAIN)]));
                await vi.waitFor(() => expect(invalidations.get(MAIN)).toHaveBeenCalledTimes(1));
                expect(listener).not.toHaveBeenCalled();
                refresh.resolve();
                await vi.waitFor(() => expect(listener).toHaveBeenCalledTimes(1));
                expect(observed).toEqual([
                    {
                        ...ctx.detail,
                        pairs: [MAIN, INTERMEDIATE],
                        ...RANGE,
                        sessionGeneration: ctx.sessionGeneration,
                        outcome: 'ok',
                        results: [result(INTERMEDIATE), result(MAIN)],
                        missingPairs: [],
                    },
                ]);
                expect(toastEvents()).toEqual([]);
                listenerRefresh.resolve();
                await done;
                expect(listener).toHaveBeenCalledTimes(1);
                expect(ctx.onsynced).toHaveBeenCalledTimes(1);
                expect(toastEvents()).toHaveLength(1);
                expect(completionEvent().toast?.variant).toBe('success');
            } finally {
                pending.resolve(response([result(MAIN), result(INTERMEDIATE)]));
                refresh.resolve();
                listenerRefresh.resolve();
                await done;
            }
        });

        it('an unsubscribed page is not called, while another live page still receives completion', async () => {
            const pending = deferred<Response>();
            syncRates.mockReturnValue(pending.promise);
            const departed = vi.fn();
            const live = vi.fn();
            const unsubscribe = listen(departed);
            listen(live);
            const done = finishFxPairCreation(context());
            try {
                unsubscribe();
                unsubscribe(); // Component teardown may defensively repeat cleanup.
                pending.resolve(response([result(MAIN)]));
                await done;
                expect(syncRates.mock.calls.map(([body]) => body)).toEqual([{pairs: [MAIN], ...RANGE}]);
                expect(live).toHaveBeenCalledExactlyOnceWith(expect.objectContaining({slug: MAIN, outcome: 'ok'}));
                expect(departed).not.toHaveBeenCalled();
                expect(completionEvent().toast?.variant).toBe('success');
            } finally {
                pending.resolve(response([result(MAIN)]));
                await done;
            }
        });

        it('does not replay completed work to a later subscriber or deliver it twice after a new creation', async () => {
            await finishFxPairCreation(context());
            const listener = vi.fn();
            const unsubscribe = listen(listener);
            const next = context({
                detail: {base: 'EUR', quote: 'USD', slug: INTERMEDIATE, hasRealProvider: true, autoSyncStarted: true},
                pairs: [INTERMEDIATE],
            });
            syncRates.mockResolvedValue(response([result(INTERMEDIATE)]));
            await finishFxPairCreation(next);
            expect(listener).toHaveBeenCalledExactlyOnceWith(expect.objectContaining({slug: INTERMEDIATE, pairs: [INTERMEDIATE]}));
            unsubscribe();
            syncRates.mockResolvedValue(response([result(MAIN)]));
            await finishFxPairCreation(context());
            expect(listener).toHaveBeenCalledTimes(1);
            expect(syncRates.mock.calls.map(([body]) => body)).toEqual([
                {pairs: [MAIN], ...RANGE},
                {pairs: [INTERMEDIATE], ...RANGE},
                {pairs: [MAIN], ...RANGE},
            ]);
        });

        it.each([
            {name: 'partial intermediate', rows: [result(INTERMEDIATE, 'partial'), result(MAIN)], outcome: 'partial', missingPairs: []},
            {name: 'failed intermediate', rows: [result(INTERMEDIATE, 'failed'), result(MAIN)], outcome: 'failed', missingPairs: []},
            {name: 'all skipped', rows: [result(INTERMEDIATE, 'skipped'), result(MAIN, 'skipped')], outcome: 'skipped', missingPairs: []},
            {name: 'missing intermediate', rows: [result(MAIN)], outcome: 'failed', missingPairs: [INTERMEDIATE]},
        ])('delivers honest results for $name rather than broadcasting success unconditionally', async ({rows, outcome, missingPairs}) => {
            const listener = vi.fn();
            listen(listener);
            syncRates.mockResolvedValue(response(rows));
            await finishFxPairCreation(context({pairs: [MAIN, INTERMEDIATE]}));
            expect(listener).toHaveBeenCalledExactlyOnceWith(expect.objectContaining({slug: MAIN, pairs: [MAIN, INTERMEDIATE], results: rows, outcome, missingPairs}));
            expect(syncRates.mock.calls.map(([body]) => body)).toEqual([{pairs: [MAIN, INTERMEDIATE], ...RANGE}]);
            expect(toastEvents()).toHaveLength(1);
        });

        it('delivers transport failure to subscribers without presenting rates as available', async () => {
            const listener = vi.fn();
            listen(listener);
            syncRates.mockRejectedValue(new Error('owned-subscriber-transport-failure'));
            await finishFxPairCreation(context());
            expect(listener).toHaveBeenCalledExactlyOnceWith(expect.objectContaining({slug: MAIN, pairs: [MAIN], outcome: 'transport-error', results: [], missingPairs: [MAIN]}));
            expect(syncRates.mock.calls.map(([body]) => body)).toEqual([{pairs: [MAIN], ...RANGE}]);
            expect(completionEvent().toast?.variant).toBe('error');
        });

        it('isolates thrown and rejected listeners, lets all other listeners finish, and reports one aggregate warning', async () => {
            const pendingListener = deferred<void>();
            const thrown = vi.fn(() => {
                throw new Error('owned-listener-threw');
            });
            const rejected = vi.fn().mockRejectedValue(new Error('owned-listener-rejected'));
            const delayed = vi.fn(() => pendingListener.promise);
            const healthy = vi.fn();
            listen(thrown);
            listen(rejected);
            listen(delayed);
            listen(healthy);
            const ctx = context();
            const done = finishFxPairCreation(ctx);
            try {
                await vi.waitFor(() => expect(healthy).toHaveBeenCalledTimes(1));
                expect(thrown).toHaveBeenCalledTimes(1);
                expect(rejected).toHaveBeenCalledTimes(1);
                expect(delayed).toHaveBeenCalledTimes(1);
                expect(toastEvents()).toEqual([]);
                pendingListener.resolve();
                await done;
                expect(syncRates.mock.calls.map(([body]) => body)).toEqual([{pairs: [MAIN], ...RANGE}]);
                expect(ctx.onsynced).toHaveBeenCalledTimes(1);
                expect(toastEvents()).toHaveLength(1);
                expect(completionEvent().detail).toMatchObject({
                    outcome: 'ok',
                    callbackErrors: [
                        {phase: 'completion', message: 'owned-listener-threw'},
                        {phase: 'completion', message: 'owned-listener-rejected'},
                    ],
                });
                expect(completionEvent().toast?.variant).toBe('warning');
                expect(healthy).toHaveBeenCalledTimes(1);
            } finally {
                pendingListener.resolve();
                await done;
            }
        });

        it('does not deliver an obsolete account result to a currently subscribed page', async () => {
            const pending = deferred<Response>();
            syncRates.mockReturnValue(pending.promise);
            const listener = vi.fn();
            listen(listener);
            const done = finishFxPairCreation(context());
            try {
                transitionClientSession('new-subscriber-account');
                pending.resolve(response([result(MAIN)]));
                await done;
                expect(listener).not.toHaveBeenCalled();
                expect(invalidations.size).toBe(0);
                expect(toastEvents()).toEqual([]);
                // Positive barrier: the same subscription receives current work.
                syncRates.mockResolvedValue(response([result(MAIN)]));
                const current = context();
                await finishFxPairCreation(current);
                expect(listener).toHaveBeenCalledExactlyOnceWith(expect.objectContaining({sessionGeneration: current.sessionGeneration}));
                expect(syncRates.mock.calls.map(([body]) => body)).toEqual([
                    {pairs: [MAIN], ...RANGE},
                    {pairs: [MAIN], ...RANGE},
                ]);
            } finally {
                pending.resolve(response([result(MAIN)]));
                await done;
            }
        });

        it('an account change during listener refresh suppresses the old host callback and final notification', async () => {
            const pendingListener = deferred<void>();
            const listener = vi.fn(() => pendingListener.promise);
            listen(listener);
            const ctx = context();
            const done = finishFxPairCreation(ctx);
            try {
                await vi.waitFor(() => expect(listener).toHaveBeenCalledTimes(1));
                transitionClientSession('changed-during-subscriber-refresh');
                pendingListener.resolve();
                await done;
                expect(ctx.onsynced).not.toHaveBeenCalled();
                expect(toastEvents()).toEqual([]);
                expect(events().filter((event) => event.name === 'fx.pair.creation-sync-completed')).toEqual([]);
                expect(syncRates.mock.calls.map(([body]) => body)).toEqual([{pairs: [MAIN], ...RANGE}]);
            } finally {
                pendingListener.resolve();
                await done;
            }
        });

        it.each([
            {name: 'manual creation', overrides: {detail: {base: 'EUR', quote: 'GBP', slug: MAIN, hasRealProvider: false, autoSyncStarted: false}}},
            {name: 'missing date', overrides: {start: ''}},
            {name: 'configuration edit', overrides: {editMode: true}},
        ])('does not broadcast rate completion for $name', async ({overrides}) => {
            const listener = vi.fn();
            listen(listener);
            const ctx = context(overrides);
            await finishFxPairCreation(ctx);
            expect(ctx.oncreated).toHaveBeenCalledTimes(1);
            expect(ctx.onclose).toHaveBeenCalledTimes(1);
            expect(listener).not.toHaveBeenCalled();
            expect(syncRates).not.toHaveBeenCalled();
        });
    });

    it('captures pair/range/callback identity and deduplicates pairs before the draft can change', async () => {
        const pending = deferred<Response>();
        syncRates.mockReturnValue(pending.promise);
        const ctx = context({pairs: [INTERMEDIATE, MAIN, INTERMEDIATE]});
        const mutableDraftDetail = {...ctx.detail};
        ctx.detail = mutableDraftDetail;
        const capturedCreated = ctx.oncreated;
        const capturedSynced = ctx.onsynced;
        const done = finishFxPairCreation(ctx);
        try {
            ctx.pairs = ['JPY-USD'];
            mutableDraftDetail.slug = 'JPY-USD';
            ctx.start = '2022-01-01';
            ctx.end = '2022-01-31';
            ctx.oncreated = vi.fn();
            ctx.onsynced = vi.fn();
            pending.resolve(response([result(INTERMEDIATE), result(MAIN)]));
            await done;
            expect(syncRates.mock.calls.map(([body]) => body)).toEqual([{pairs: [MAIN, INTERMEDIATE], ...RANGE}]);
            expect(capturedCreated).toHaveBeenCalledExactlyOnceWith(expect.objectContaining({slug: MAIN}));
            expect(capturedSynced).toHaveBeenCalledExactlyOnceWith(expect.objectContaining({slug: MAIN, pairs: [MAIN, INTERMEDIATE], ...RANGE}));
            expect(ctx.oncreated).not.toHaveBeenCalled();
            expect(ctx.onsynced).not.toHaveBeenCalled();
            expect(completionEvent().toast?.message).not.toContain('JPY-USD');
        } finally {
            pending.resolve(response([result(MAIN), result(INTERMEDIATE)]));
            await done;
        }
    });

    it.each(['response', 'creation refresh', 'completion refresh'] as const)('suppresses obsolete account completion while awaiting %s', async (phase) => {
        const pending = deferred<Response>();
        const creationRefresh = deferred<void>();
        const completionRefresh = deferred<void>();
        const ctx = context({
            oncreated: vi.fn(() => (phase === 'creation refresh' ? creationRefresh.promise : undefined)),
            onsynced: vi.fn(() => (phase === 'completion refresh' ? completionRefresh.promise : undefined)),
        });
        syncRates.mockReturnValue(pending.promise);
        const done = finishFxPairCreation(ctx);
        try {
            expect(syncRates.mock.calls.map(([body]) => body)).toEqual([{pairs: [MAIN], ...RANGE}]);
            if (phase !== 'response') {
                pending.resolve(response([result(MAIN)]));
                if (phase === 'creation refresh') await vi.waitFor(() => expect(invalidations.get(MAIN)).toHaveBeenCalledTimes(1));
                else await vi.waitFor(() => expect(ctx.onsynced).toHaveBeenCalledTimes(1));
            }
            const invalidationsBefore = invalidations.get(MAIN)?.mock.calls.length ?? 0;
            transitionClientSession('different-fx-account');
            // Even switching back is a new generation, not the old account run.
            transitionClientSession('owned-fx-sync-context');
            pending.resolve(response([result(MAIN)]));
            creationRefresh.resolve();
            completionRefresh.resolve();
            await done;
            expect(toastEvents()).toEqual([]);
            expect(events().filter((event) => event.name === 'fx.pair.creation-sync-completed')).toEqual([]);
            expect(invalidations.get(MAIN)?.mock.calls.length ?? 0).toBe(invalidationsBefore);
            if (phase !== 'completion refresh') expect(ctx.onsynced).not.toHaveBeenCalled();
        } finally {
            pending.resolve(response([result(MAIN)]));
            creationRefresh.resolve();
            completionRefresh.resolve();
            await done;
        }
    });

    it('does nothing if the committed context already belongs to an obsolete account', async () => {
        const ctx = context();
        transitionClientSession('new-owner-before-completion');
        await finishFxPairCreation(ctx);
        expect(syncRates).not.toHaveBeenCalled();
        expect(ctx.oncreated).not.toHaveBeenCalled();
        expect(ctx.onclose).not.toHaveBeenCalled();
        expect(ctx.onsynced).not.toHaveBeenCalled();
        expect(invalidateFxRoutes).not.toHaveBeenCalled();
        expect(events()).toEqual([]);
    });

    it.each(['creation', 'completion'] as const)('keeps one final notification and downgrades success when the %s callback rejects', async (phase) => {
        const failed = vi.fn().mockRejectedValue(new Error('owned-refresh-rejected'));
        const ctx = context(phase === 'creation' ? {oncreated: failed} : {onsynced: failed});
        await finishFxPairCreation(ctx);
        expect(syncRates.mock.calls.map(([body]) => body)).toEqual([{pairs: [MAIN], ...RANGE}]);
        expect(ctx.oncreated).toHaveBeenCalledTimes(1);
        expect(ctx.onclose).toHaveBeenCalledTimes(1);
        expect(ctx.onsynced).toHaveBeenCalledTimes(1);
        expect(toastEvents()).toHaveLength(1);
        expect(completionEvent().toast?.variant).toBe('warning');
        expect(completionEvent().detail).toMatchObject({outcome: 'ok', configurationSaved: true, callbackErrors: [{phase, message: 'owned-refresh-rejected'}]});
    });

    it('reads the translator at completion rather than retaining the launch locale', async () => {
        const pending = deferred<Response>();
        syncRates.mockReturnValue(pending.promise);
        const currentTr = vi.fn((key: string) => `current-locale:${key}`);
        const launchTr = vi.fn((key: string) => `launch-locale:${key}`);
        const translator = _ as unknown as Writable<(key: string) => string>;
        translator.set(launchTr);
        const done = finishFxPairCreation(context());
        try {
            translator.set(currentTr);
            pending.resolve(response([result(MAIN)]));
            await done;
            expect(syncRates.mock.calls.map(([body]) => body)).toEqual([{pairs: [MAIN], ...RANGE}]);
            expect(buildFxSyncToast).toHaveBeenCalledWith(expect.objectContaining({pair: MAIN}), MAIN, currentTr, undefined, expect.any(Function), {outerFlags: true, linkToDetail: true});
            expect(currentTr).toHaveBeenCalledWith('fx.sync.synced');
            expect(launchTr).not.toHaveBeenCalled();
        } finally {
            pending.resolve(response([result(MAIN)]));
            await done;
            translator.set((key) => `injected:${key}`);
        }
    });
});
