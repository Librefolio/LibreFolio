/**
 * brokerStore — `ensureBrokerIconFieldsLoaded`: at most one request per broker per cache
 * generation (C3).
 *
 * The defect this pins: with the Transactions page open, a broker that has none of `icon_url`,
 * `portal_url`, `default_import_plugin` was asked for ~60 times a second. The detail answer
 * carries no icon field either, so the store kept reading the broker as "not hydrated yet" and
 * asked again at the next re-render; only *concurrent* calls were de-duplicated.
 *
 * The contract:
 *   - the FIRST ANSWER — success or error — settles the id: a broker without icon fields is a
 *     valid state, not a pending one;
 *   - a broker whose cached entry already has an icon field makes no request;
 *   - concurrent calls share one request;
 *   - the settled set belongs to the cache generation: `resetBrokerStore()` (also run by a
 *     client-session change) and `refreshAllBrokers()` clear it, `invalidateBroker(idOrIds)`
 *     removes exactly those ids;
 *   - an answer that lands after a client-session change neither merges nor settles the id.
 *
 * A file of its own on purpose: `brokerStore.test.ts` promises "network is not expected" and
 * mocks the API with a Proxy that throws. Here the network *is* the subject, so the two endpoints
 * the store may reach are counted `vi.fn()`s, and any other endpoint is recorded as a stray and
 * fails the test. `refreshAllBrokers()` also fires `ensurePluginIconsLoaded()`: that one is
 * mocked so the plugin catalogue never becomes a stray request, while the real
 * `normalizeBrokerIconField` is kept — it decides what counts as an icon field.
 *
 * No DOM: node env. The store's state (cache, in-flight map, client session) lives at module level
 * and is shared by the whole file, so every test claims a fresh account and a broker id of its own.
 */

import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';

const api = vi.hoisted(() => ({
    getBroker: vi.fn(),
    listBrokers: vi.fn(),
    ensurePluginIcons: vi.fn(),
    /** Endpoints the store reached that this file does not own. Must stay empty. */
    stray: [] as string[],
}));

// vi.mock is hoisted — the factories run before the imports below.
vi.mock('$lib/api', () => {
    const endpoints: Record<string, unknown> = {
        get_broker_api_v1_brokers__broker_id__get: api.getBroker,
        list_brokers_api_v1_brokers_get: api.listBrokers,
    };
    return {
        zodiosApi: new Proxy(endpoints, {
            get(target, key) {
                if (typeof key !== 'string') return undefined;
                if (key in target) return target[key];
                api.stray.push(key);
                return () => Promise.reject(new Error(`unexpected request in brokerStore icon-hydration tests: ${key}`));
            },
        }),
    };
});

vi.mock('$lib/utils/broker/brokerHelpers', async (importOriginal) => {
    const actual = await importOriginal<typeof import('$lib/utils/broker/brokerHelpers')>();
    return {...actual, ensurePluginIconsLoaded: api.ensurePluginIcons};
});

import {transitionClientSession} from '$lib/stores/app/clientSession';
import {ensureBrokerIconFieldsLoaded, getBrokerInfo, invalidateBroker, mergeBrokers, refreshAllBrokers, resetBrokerStore} from './brokerStore';

let nextId = 7_000;
let accountSequence = 0;

/** A broker as a list or a transaction row carries it: id and name, none of the three icon fields. */
function bare(id: number) {
    return {id, name: `No icons ${id}`};
}

/** What `GET /brokers/{id}` answers for a broker that genuinely has no icon: the three fields, all null. */
function detailWithoutIcons(id: number, overrides: Record<string, unknown> = {}) {
    return {id, name: `No icons ${id}`, icon_url: null, portal_url: null, default_import_plugin: null, ...overrides};
}

/** The detail answer for whichever broker the store asked about. */
function answerWithoutIcons({params}: {params: {broker_id: number}}) {
    return Promise.resolve(detailWithoutIcons(params.broker_id));
}

/** Requests the store made for one broker id. */
function requestsFor(id: number): number {
    return api.getBroker.mock.calls.filter(([arg]) => (arg as {params?: {broker_id?: number}} | undefined)?.params?.broker_id === id).length;
}

function deferred<T>() {
    let resolve!: (value: T) => void;
    let reject!: (reason: unknown) => void;
    const promise = new Promise<T>((onResolve, onReject) => {
        resolve = onResolve;
        reject = onReject;
    });
    return {promise, resolve, reject};
}

/**
 * Claim a fresh account. The very first transition only resolves the identity; every later one is
 * a real session change and runs the registered resetters, `resetBrokerStore` among them. Claiming
 * one before each test is what makes the session change in U3f a real one.
 */
function freshAccount(): void {
    transitionClientSession(`broker-icon-hydration-${++accountSequence}`);
}

beforeEach(() => {
    freshAccount();
    resetBrokerStore();
    api.getBroker.mockReset();
    api.listBrokers.mockReset();
    api.ensurePluginIcons.mockReset().mockResolvedValue(undefined);
    api.stray.length = 0;
});

afterEach(() => {
    vi.restoreAllMocks();
    expect(api.stray, 'the store reached an endpoint these tests do not own').toEqual([]);
});

describe('ensureBrokerIconFieldsLoaded — at most one request per broker per cache generation (C3)', () => {
    it('U1 · asks once for a broker without icon fields: a successful answer without them settles the id', async () => {
        const id = nextId++;
        mergeBrokers([bare(id)]);
        api.getBroker.mockImplementation(answerWithoutIcons);

        await ensureBrokerIconFieldsLoaded(id);
        await ensureBrokerIconFieldsLoaded(id);

        expect(api.getBroker).toHaveBeenCalledWith(expect.objectContaining({params: {broker_id: id}}));
        expect(api.getBroker).toHaveBeenCalledTimes(1);
    });

    it('U1 · invalidating another broker does not re-open a settled one', async () => {
        const invalidated = nextId++;
        const untouched = nextId++;
        mergeBrokers([bare(invalidated), bare(untouched)]);
        api.getBroker.mockImplementation(answerWithoutIcons);
        await ensureBrokerIconFieldsLoaded(invalidated);
        await ensureBrokerIconFieldsLoaded(untouched);

        invalidateBroker(invalidated);
        mergeBrokers([bare(invalidated)]);
        await ensureBrokerIconFieldsLoaded(invalidated);
        await ensureBrokerIconFieldsLoaded(untouched);

        expect(requestsFor(invalidated), 'the invalidated broker is asked for again').toBe(2);
        expect(requestsFor(untouched), 'a broker nobody invalidated stays settled').toBe(1);
    });

    it('U2 · a failed answer settles the id too: no retry within the same cache generation', async () => {
        const id = nextId++;
        mergeBrokers([bare(id)]);
        api.getBroker.mockRejectedValue(new Error('synthetic failure of GET /brokers/{id}'));
        // The store logs the failure; the log is not the subject.
        vi.spyOn(console, 'error').mockImplementation(() => undefined);

        await expect(ensureBrokerIconFieldsLoaded(id)).resolves.toBeUndefined();
        await expect(ensureBrokerIconFieldsLoaded(id)).resolves.toBeUndefined();

        expect(api.getBroker).toHaveBeenCalledTimes(1);
    });

    it.each([
        ['icon_url', {icon_url: '/api/v1/files/static/broker-icon.png'}],
        ['portal_url', {portal_url: 'https://example.invalid'}],
        ['default_import_plugin', {default_import_plugin: 'broker_generic_csv'}],
    ])('U3a · makes no request when the cached entry already has %s', async (_field, iconField) => {
        const id = nextId++;
        mergeBrokers([{...bare(id), ...iconField}]);
        expect(getBrokerInfo(id), 'precondition: the icon field is in the cache').toMatchObject(iconField);

        await ensureBrokerIconFieldsLoaded(id);

        expect(api.getBroker).not.toHaveBeenCalled();
    });

    it('U3b · concurrent calls for one broker share a single request', async () => {
        const id = nextId++;
        mergeBrokers([bare(id)]);
        const answer = deferred<Record<string, unknown>>();
        api.getBroker.mockReturnValue(answer.promise);

        const first = ensureBrokerIconFieldsLoaded(id);
        const second = ensureBrokerIconFieldsLoaded(id);
        answer.resolve(detailWithoutIcons(id));
        await Promise.all([first, second]);

        expect(api.getBroker).toHaveBeenCalledTimes(1);
    });

    it('U3c · invalidateBroker(id) re-opens a settled broker: the next call asks again', async () => {
        const id = nextId++;
        mergeBrokers([bare(id)]);
        api.getBroker.mockImplementation(answerWithoutIcons);
        await ensureBrokerIconFieldsLoaded(id);
        expect(api.getBroker).toHaveBeenCalledTimes(1);

        invalidateBroker(id);
        mergeBrokers([bare(id)]);
        await ensureBrokerIconFieldsLoaded(id);

        expect(api.getBroker).toHaveBeenCalledTimes(2);
    });

    it('U3c · invalidateBroker([ids]) re-opens every listed broker', async () => {
        const first = nextId++;
        const second = nextId++;
        mergeBrokers([bare(first), bare(second)]);
        api.getBroker.mockImplementation(answerWithoutIcons);
        await ensureBrokerIconFieldsLoaded(first);
        await ensureBrokerIconFieldsLoaded(second);

        invalidateBroker([first, second]);
        mergeBrokers([bare(first), bare(second)]);
        await ensureBrokerIconFieldsLoaded(first);
        await ensureBrokerIconFieldsLoaded(second);

        expect(requestsFor(first)).toBe(2);
        expect(requestsFor(second)).toBe(2);
    });

    it('U3d · refreshAllBrokers() starts a new cache generation: the next call asks again', async () => {
        const id = nextId++;
        api.listBrokers.mockResolvedValue({items: [detailWithoutIcons(id)], inaccessible: []});
        api.getBroker.mockImplementation(answerWithoutIcons);
        await refreshAllBrokers();
        expect(getBrokerInfo(id), 'precondition: the list loader seeded the broker').toMatchObject({id, name: bare(id).name});
        await ensureBrokerIconFieldsLoaded(id);

        await refreshAllBrokers();
        await ensureBrokerIconFieldsLoaded(id);

        expect(api.listBrokers).toHaveBeenCalledTimes(2);
        expect(api.getBroker).toHaveBeenCalledTimes(2);
    });

    it('U3e · resetBrokerStore() starts a new cache generation: the next call asks again', async () => {
        const id = nextId++;
        mergeBrokers([bare(id)]);
        api.getBroker.mockImplementation(answerWithoutIcons);
        await ensureBrokerIconFieldsLoaded(id);

        resetBrokerStore();
        expect(getBrokerInfo(id), 'precondition: the reset emptied the cache').toBeNull();
        mergeBrokers([bare(id)]);
        await ensureBrokerIconFieldsLoaded(id);

        expect(api.getBroker).toHaveBeenCalledTimes(2);
    });

    it.each(['resolves', 'rejects'] as const)('U3f · an answer that %s after a client-session change neither merges nor settles the id', async (outcome) => {
        const id = nextId++;
        mergeBrokers([bare(id)]);
        const stale = deferred<Record<string, unknown>>();
        api.getBroker.mockReturnValueOnce(stale.promise);
        vi.spyOn(console, 'error').mockImplementation(() => undefined);
        const staleCall = ensureBrokerIconFieldsLoaded(id);

        // Another account signs in while the request is in flight.
        freshAccount();
        expect(getBrokerInfo(id), 'precondition: the session change reset the broker cache').toBeNull();

        if (outcome === 'resolves') stale.resolve(detailWithoutIcons(id, {name: 'Previous account view'}));
        else stale.reject(new Error('synthetic failure of the previous account request'));
        await staleCall;
        expect(getBrokerInfo(id), 'the stale answer must not be merged').toBeNull();

        mergeBrokers([bare(id)]);
        api.getBroker.mockResolvedValueOnce(detailWithoutIcons(id, {description: 'current account answer'}));
        await ensureBrokerIconFieldsLoaded(id);

        expect(api.getBroker, 'the stale answer must not settle the id').toHaveBeenCalledTimes(2);
        expect(getBrokerInfo(id), 'the current answer is merged').toMatchObject({name: bare(id).name, description: 'current account answer'});
    });
});
