/**
 * currencyRoutesPool — `findRoutePathsOffThread` and `destroyCurrencyRoutesPool` (lane 75, wave 2, lot L20b; plan
 * `plan-phase02FxCentralBanksOndata2.prompt.md`, decision Q6 of 19/11/2026). Written before the module exists.
 *
 * One lazily created `WorkerPool(factory, 1)` runs the search in a Web Worker; where `globalThis.Worker` is undefined (SSR,
 * node tests) the same `computeRoutePaths` runs in the current thread. A fake `Worker` class stands in for the browser's.
 * The pool keeps module state, so each test loads a fresh copy of the module and destroys its pool.
 */
import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';

import type {ProviderInfo} from '$lib/utils/currency/currencyGraph';
import {computeRoutePaths, type CurrencyRoutesRequest} from '../currencyRoutes.worker';

function prov(code: string, base: string, targets: string[]): ProviderInfo {
    return {code, name: `Test ${code}`, base_currency: base, base_currencies: [base], target_currencies: targets};
}

const REQUEST: CurrencyRoutesRequest = {
    providers: [prov('P0', 'A', ['Z']), prov('P1', 'A', ['B']), prov('P2', 'B', ['Z'])],
    currencyCodes: ['A', 'B', 'Z'],
    source: 'A',
    target: 'Z',
};

/** The route the fake worker invents when it does not compute: it can only come from the worker, never from the thread. */
const FAKE_ANSWER = [[{from: 'A', to: 'Z', provider: 'FAKE'}]];

type Reply = (payload: CurrencyRoutesRequest, id: string) => Record<string, unknown>;

/** A stand-in for the browser's Worker: records its construction, answers each message asynchronously. */
class FakeWorker {
    static instances: FakeWorker[] = [];
    static reply: Reply = (payload, id) => ({id, result: computeRoutePaths(payload)});

    onmessage: ((event: {data: unknown}) => void) | null = null;
    onerror: ((event: unknown) => void) | null = null;
    terminated = false;
    readonly url: string;

    constructor(url: string | URL) {
        this.url = String(url);
        FakeWorker.instances.push(this);
    }

    postMessage(message: {id: string; payload: CurrencyRoutesRequest}): void {
        // A microtask, never a timer: the answer is asynchronous but needs no clock.
        void Promise.resolve().then(() => {
            if (!this.terminated) this.onmessage?.({data: FakeWorker.reply(message.payload, message.id)});
        });
    }

    terminate(): void {
        this.terminated = true;
    }
}

/** The copy of the pool module the current test loaded, so `afterEach` destroys the pool that test created. */
let loaded: typeof import('../currencyRoutesPool') | null = null;

async function freshPool() {
    vi.resetModules();
    loaded = await import('../currencyRoutesPool');
    return loaded;
}

beforeEach(() => {
    FakeWorker.instances = [];
    FakeWorker.reply = (payload, id) => ({id, result: computeRoutePaths(payload)});
});

afterEach(() => {
    loaded?.destroyCurrencyRoutesPool();
    loaded = null;
    vi.unstubAllGlobals();
});

describe('findRoutePathsOffThread without a Worker (SSR, node)', () => {
    it('computes in the current thread: the answer is computeRoutePaths', async () => {
        expect(globalThis.Worker).toBeUndefined();
        const {findRoutePathsOffThread} = await freshPool();

        const paths = await findRoutePathsOffThread(REQUEST);

        expect(paths).toEqual(computeRoutePaths(REQUEST));
        expect(paths.map((p) => p.length)).toEqual([1, 2]);
    });

    it('answers [] for a pair with no chain', async () => {
        const {findRoutePathsOffThread} = await freshPool();
        expect(await findRoutePathsOffThread({...REQUEST, target: 'NOPE'})).toEqual([]);
    });
});

describe('findRoutePathsOffThread with a Worker', () => {
    it('takes the answer from the worker, which here computes it from the payload', async () => {
        vi.stubGlobal('Worker', FakeWorker);
        const {findRoutePathsOffThread} = await freshPool();

        expect(await findRoutePathsOffThread(REQUEST)).toEqual(computeRoutePaths(REQUEST));
        expect(FakeWorker.instances).toHaveLength(1);
    });

    it('does not compute in the thread: a worker that answers something else gets its answer through', async () => {
        vi.stubGlobal('Worker', FakeWorker);
        FakeWorker.reply = (_payload, id) => ({id, result: FAKE_ANSWER});
        const {findRoutePathsOffThread} = await freshPool();

        expect(await findRoutePathsOffThread(REQUEST)).toEqual(FAKE_ANSWER);
    });

    it('builds exactly one worker, even for several concurrent requests, each answered in turn', async () => {
        vi.stubGlobal('Worker', FakeWorker);
        const {findRoutePathsOffThread} = await freshPool();
        const requests = [REQUEST, {...REQUEST, target: 'B'}, {...REQUEST, source: 'B'}];

        const answers = await Promise.all(requests.map((request) => findRoutePathsOffThread(request)));

        expect(FakeWorker.instances).toHaveLength(1);
        answers.forEach((answer, i) => expect(answer).toEqual(computeRoutePaths(requests[i])));
        // A later request reuses the same worker.
        await findRoutePathsOffThread(REQUEST);
        expect(FakeWorker.instances).toHaveLength(1);
    });

    it('creates the worker lazily, from the currencyRoutes.worker.ts module, not at import', async () => {
        vi.stubGlobal('Worker', FakeWorker);
        const {findRoutePathsOffThread} = await freshPool();
        expect(FakeWorker.instances, 'importing the pool builds nothing').toHaveLength(0);

        await findRoutePathsOffThread(REQUEST);

        expect(FakeWorker.instances[0].url.endsWith('currencyRoutes.worker.ts')).toBe(true);
    });

    it('rejects when the worker answers with an error', async () => {
        vi.stubGlobal('Worker', FakeWorker);
        FakeWorker.reply = (_payload, id) => ({id, error: 'boom'});
        const {findRoutePathsOffThread} = await freshPool();

        await expect(findRoutePathsOffThread(REQUEST)).rejects.toThrow('boom');
    });

    it('still answers the next request after one that failed', async () => {
        vi.stubGlobal('Worker', FakeWorker);
        FakeWorker.reply = (_payload, id) => ({id, error: 'boom'});
        const {findRoutePathsOffThread} = await freshPool();
        await expect(findRoutePathsOffThread(REQUEST)).rejects.toThrow('boom');

        FakeWorker.reply = (payload, id) => ({id, result: computeRoutePaths(payload)});
        expect(await findRoutePathsOffThread(REQUEST)).toEqual(computeRoutePaths(REQUEST));
        expect(FakeWorker.instances).toHaveLength(1);
    });
});

describe('destroyCurrencyRoutesPool', () => {
    it('terminates the worker, and a later request builds a new one', async () => {
        vi.stubGlobal('Worker', FakeWorker);
        const {findRoutePathsOffThread, destroyCurrencyRoutesPool} = await freshPool();
        await findRoutePathsOffThread(REQUEST);
        expect(FakeWorker.instances[0].terminated).toBe(false);

        destroyCurrencyRoutesPool();
        expect(FakeWorker.instances[0].terminated).toBe(true);

        expect(await findRoutePathsOffThread(REQUEST)).toEqual(computeRoutePaths(REQUEST));
        expect(FakeWorker.instances).toHaveLength(2);
        expect(FakeWorker.instances[1].terminated).toBe(false);
    });

    it('is safe when no pool was ever created, and when called twice', async () => {
        const {destroyCurrencyRoutesPool} = await freshPool();
        expect(() => {
            destroyCurrencyRoutesPool();
            destroyCurrencyRoutesPool();
        }).not.toThrow();
    });
});
