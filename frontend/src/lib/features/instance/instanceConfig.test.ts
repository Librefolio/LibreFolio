// @vitest-environment jsdom
/**
 * instanceConfig — the public configuration of the instance (`GET /api/v1/system/instance`), read once per page load.
 *
 * The contract under test:
 *   - until the server answers, and whenever it cannot, the configuration is `DEFAULT_INSTANCE_CONFIG`, a self-hosted
 *     instance; importing the store asks nothing;
 *   - `load()` shares one request per page load among concurrent and later callers; `force` asks again;
 *   - only the latest request writes: an older one that answers (or fails) last changes nothing;
 *   - a failure keeps the configuration in force, sets `failed`, logs through `debug.warn`, never rejects, and lets the
 *     next `load()` ask again, a fetcher that throws before returning a promise included (its request still starts
 *     within `load()`);
 *   - `fetchInstanceConfigFromApi()` is the generated client's `get_instance_config_api_v1_system_instance_get`;
 *   - the getters are reactive: a consumer reading them re-runs when the answer lands.
 *
 * The store keeps its state in module-level `$state` and a module-level request, so every test takes a freshly
 * imported graph (`vi.resetModules()` + `import()`): the store, and `svelte` and the rune helpers of the same graph, so
 * that an effect of the test tracks the store's own signals. No test inherits its neighbour's request, in any order.
 *
 * Requests are deferreds the test answers by hand: no clock, and the order of the answers is the test's. `$lib/api`
 * and `$lib/debug` are mocks: the generated client is the subject of one test only, and the warning of a failure is
 * read from the `debug.warn` mock (the real one is compiled out of production builds). jsdom, because effects run
 * only there and the reactivity case needs them.
 */
import {beforeEach, describe, expect, it, vi} from 'vitest';
import type {InstanceConfig} from './instanceConfig.svelte';

const mocks = vi.hoisted(() => ({
    getInstanceConfig: vi.fn().mockName('zodiosApi.get_instance_config_api_v1_system_instance_get'),
    warn: vi.fn().mockName('debug.warn'),
}));

vi.mock('$lib/api', () => ({zodiosApi: {get_instance_config_api_v1_system_instance_get: mocks.getInstanceConfig}}));
vi.mock('$lib/debug', () => ({debug: {log: vi.fn(), warn: mocks.warn, error: vi.fn(), info: vi.fn()}, isDebugEnabled: () => false}));

// The accounts part (A5a/A5b): the default is an open registration nobody pinned; the managed answer differs in it too.
const SELFHOSTED: InstanceConfig = {profile: 'selfhosted', accounts: {registration_mode: 'open', registration_locked: false}};
const MANAGED: InstanceConfig = {profile: 'managed', accounts: {registration_mode: 'invite', registration_locked: true}};

/** The store of a page load that has just begun, with the rune helpers and `flushSync` of the same module graph. */
async function freshPageLoad() {
    vi.resetModules();
    const store = await import('./instanceConfig.svelte');
    const runes = await import('$test/runes.svelte');
    const {flushSync} = await import('svelte');
    return {...store, ...runes, flushSync};
}

/** A `fetchConfig` whose requests the test answers by hand, the n-th request answered by `answers[n]`. */
function scriptedFetch() {
    const answers: Array<{resolve: (config: InstanceConfig) => void; reject: (error: unknown) => void}> = [];
    const fetchConfig = vi.fn(
        () =>
            new Promise<InstanceConfig>((resolve, reject) => {
                answers.push({resolve, reject});
            }),
    );
    return {fetchConfig, answers};
}

beforeEach(() => {
    mocks.getInstanceConfig.mockReset();
    mocks.warn.mockClear();
});

describe('instanceConfig — before the server answers', () => {
    it('is the self-hosted default, neither loaded nor failed, and importing the store asks nothing', async () => {
        const {instanceConfig, DEFAULT_INSTANCE_CONFIG} = await freshPageLoad();

        expect(DEFAULT_INSTANCE_CONFIG).toEqual(SELFHOSTED);
        expect(instanceConfig.config).toEqual(DEFAULT_INSTANCE_CONFIG);
        expect([instanceConfig.loaded, instanceConfig.failed]).toEqual([false, false]);
        expect(mocks.getInstanceConfig, 'the store asks only when load() is called').not.toHaveBeenCalled();
    });
});

describe('instanceConfig.load — one request per page load', () => {
    it('asks the server once, and its answer becomes the configuration in force', async () => {
        const {instanceConfig} = await freshPageLoad();
        const {fetchConfig, answers} = scriptedFetch();

        const loading = instanceConfig.load({fetchConfig});
        expect(fetchConfig).toHaveBeenCalledTimes(1);
        expect(instanceConfig.config, 'the default stays until the answer lands').toEqual(SELFHOSTED);
        expect(instanceConfig.loaded).toBe(false);

        answers[0].resolve(MANAGED);
        await loading;

        expect(instanceConfig.config).toEqual(MANAGED);
        expect([instanceConfig.loaded, instanceConfig.failed]).toEqual([true, false]);
    });

    it('shares the request among concurrent callers and later ones: one fetch for the whole page load', async () => {
        const {instanceConfig} = await freshPageLoad();
        const {fetchConfig, answers} = scriptedFetch();

        const first = instanceConfig.load({fetchConfig});
        const concurrent = instanceConfig.load({fetchConfig});
        expect(concurrent, 'a caller arriving while the request is in flight joins it').toBe(first);

        answers[0].resolve(MANAGED);
        await first;
        const later = instanceConfig.load({fetchConfig});

        expect(later, 'a caller arriving after the answer gets the settled request, not a new one').toBe(first);
        expect(fetchConfig).toHaveBeenCalledTimes(1);
        expect(instanceConfig.config).toEqual(MANAGED);
    });

    it('force asks again, and the newer answer is the one in force', async () => {
        const {instanceConfig} = await freshPageLoad();
        const {fetchConfig, answers} = scriptedFetch();
        const first = instanceConfig.load({fetchConfig});
        answers[0].resolve(SELFHOSTED);
        await first;

        const forced = instanceConfig.load({force: true, fetchConfig});
        expect(forced, 'force starts a request of its own').not.toBe(first);
        expect(fetchConfig).toHaveBeenCalledTimes(2);
        answers[1].resolve(MANAGED);
        await forced;

        expect(instanceConfig.config).toEqual(MANAGED);
        expect(instanceConfig.load({fetchConfig}), 'and later callers share the forced request').toBe(forced);
        expect(fetchConfig).toHaveBeenCalledTimes(2);
    });

    it('without fetchConfig, asks GET /system/instance through the generated client', async () => {
        const {instanceConfig, fetchInstanceConfigFromApi} = await freshPageLoad();
        mocks.getInstanceConfig.mockResolvedValue(MANAGED);

        expect(await fetchInstanceConfigFromApi()).toEqual(MANAGED);
        expect(mocks.getInstanceConfig).toHaveBeenCalledTimes(1);
        expect(mocks.getInstanceConfig).toHaveBeenCalledWith();

        await instanceConfig.load();

        expect(mocks.getInstanceConfig, 'load() without fetchConfig uses the same call').toHaveBeenCalledTimes(2);
        expect(instanceConfig.config).toEqual(MANAGED);
    });
});

describe('instanceConfig.load — only the latest request writes', () => {
    it('an older request answering after a forced one changes nothing', async () => {
        const {instanceConfig} = await freshPageLoad();
        const {fetchConfig, answers} = scriptedFetch();
        const older = instanceConfig.load({fetchConfig});
        const forced = instanceConfig.load({force: true, fetchConfig});

        answers[1].resolve(MANAGED);
        await forced;
        answers[0].resolve(SELFHOSTED);
        await older;

        expect(instanceConfig.config, 'the late answer of the older request was written over the newer one').toEqual(MANAGED);
        expect([instanceConfig.loaded, instanceConfig.failed]).toEqual([true, false]);
    });

    it('an older request failing after a forced one neither sets failed nor logs', async () => {
        const {instanceConfig} = await freshPageLoad();
        const {fetchConfig, answers} = scriptedFetch();
        const older = instanceConfig.load({fetchConfig});
        const forced = instanceConfig.load({force: true, fetchConfig});

        answers[1].resolve(MANAGED);
        await forced;
        answers[0].reject(new Error('the older request failed late'));
        await older;

        expect(instanceConfig.failed, 'a failure of a request nobody waits for any more was reported').toBe(false);
        expect(mocks.warn).not.toHaveBeenCalled();
        expect(instanceConfig.load({fetchConfig}), 'the forced request stays the one of the page load').toBe(forced);
    });
});

describe('instanceConfig.load — a failure never blocks the interface', () => {
    it('keeps the default, sets failed, logs the error, resolves, and the next load() asks again', async () => {
        const {instanceConfig} = await freshPageLoad();
        const {fetchConfig, answers} = scriptedFetch();
        const error = new Error('503 Service Unavailable');

        const failing = instanceConfig.load({fetchConfig});
        answers[0].reject(error);

        await expect(failing, 'a failed request must not reject at whoever awaits load()').resolves.toBeUndefined();
        expect(instanceConfig.config).toEqual(SELFHOSTED);
        expect([instanceConfig.loaded, instanceConfig.failed]).toEqual([false, true]);
        expect(mocks.warn).toHaveBeenCalledTimes(1);
        expect(mocks.warn).toHaveBeenCalledWith('InstanceConfig', expect.any(String), error);

        const retry = instanceConfig.load({fetchConfig});
        expect(retry, 'after a failure the next load() is a new request').not.toBe(failing);
        expect(fetchConfig).toHaveBeenCalledTimes(2);
        answers[1].resolve(MANAGED);
        await retry;

        expect(instanceConfig.config).toEqual(MANAGED);
        expect([instanceConfig.loaded, instanceConfig.failed]).toEqual([true, false]);
    });

    it('keeps the last configuration known when a forced reload fails', async () => {
        const {instanceConfig} = await freshPageLoad();
        const {fetchConfig, answers} = scriptedFetch();
        const first = instanceConfig.load({fetchConfig});
        answers[0].resolve(MANAGED);
        await first;

        const forced = instanceConfig.load({force: true, fetchConfig});
        answers[1].reject(new Error('timeout'));
        await forced;

        expect(instanceConfig.config, 'a failed reload must not fall back to the default').toEqual(MANAGED);
        expect([instanceConfig.loaded, instanceConfig.failed], 'it answered once on this page load, and the last request failed').toEqual([true, true]);
    });

    it('a fetcher that throws at once is a failure like any other: load() resolves, and the next load() asks it again', async () => {
        const {instanceConfig} = await freshPageLoad();
        const error = new Error('thrown before returning a promise');
        const fetchConfig = vi
            .fn<() => Promise<InstanceConfig>>()
            .mockImplementationOnce(() => {
                throw error;
            })
            .mockResolvedValueOnce(MANAGED);

        const failing = instanceConfig.load({fetchConfig});
        expect(fetchConfig, 'the request starts within load(), not a tick later').toHaveBeenCalledTimes(1);

        await expect(failing, 'a synchronous throw must not escape load()').resolves.toBeUndefined();
        expect(instanceConfig.config).toEqual(SELFHOSTED);
        expect([instanceConfig.loaded, instanceConfig.failed]).toEqual([false, true]);
        expect(mocks.warn).toHaveBeenCalledWith('InstanceConfig', expect.any(String), error);

        const retry = instanceConfig.load({fetchConfig});
        expect(retry, 'the failed attempt must not stay the request of the page load').not.toBe(failing);
        expect(fetchConfig, 'the next load(), not forced, asks the fetcher again').toHaveBeenCalledTimes(2);
        await retry;

        expect(instanceConfig.config).toEqual(MANAGED);
        expect([instanceConfig.loaded, instanceConfig.failed]).toEqual([true, false]);
    });
});

describe('instanceConfig — the getters are reactive', () => {
    it('a consumer reading the configuration re-runs when the answer lands, and when a later request fails', async () => {
        const {instanceConfig, assertEffectsRun, recordReads, flushSync} = await freshPageLoad();
        assertEffectsRun();
        const {fetchConfig, answers} = scriptedFetch();
        const reads = recordReads(() => [instanceConfig.config.profile, instanceConfig.loaded, instanceConfig.failed]);

        const first = instanceConfig.load({fetchConfig});
        answers[0].resolve(MANAGED);
        await first;
        flushSync();
        const forced = instanceConfig.load({force: true, fetchConfig});
        answers[1].reject(new Error('timeout'));
        await forced;
        flushSync();
        reads.stop();

        expect(reads.values).toEqual([
            ['selfhosted', false, false],
            ['managed', true, false],
            ['managed', true, true],
        ]);
    });
});
