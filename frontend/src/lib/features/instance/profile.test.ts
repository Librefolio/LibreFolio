// @vitest-environment jsdom
/**
 * profile.ts — «the server has confirmed the profile», in one place (workstream A, H-nit: one helper for the rule that
 * `donationsVisible()`, `ChangelogModal`, `AssetSearchAutocomplete`, `checkForNewerRelease()` and `ForgotPasswordCard`
 * each wrote by hand).
 *
 * `instanceConfig` holds `DEFAULT_INSTANCE_CONFIG` until `GET /api/v1/system/instance` answers, and the defaults say
 * `profile: 'selfhosted'`: the profile alone reads self-hosted before the answer, while the request is in flight, and
 * after a request that failed before any answer. What the app may act on is the answer: `loaded && profile === …`.
 *
 * The contract under test (approved by the coordinator, 17/10):
 *   - PRF-01: the module sits next to this test and exports `selfHostedConfirmed` and `managedConfirmed` as functions;
 *   - PRF-02: before any request both are false, although the defaults say self-hosted;
 *   - PRF-03: while the first request is in flight both are false;
 *   - PRF-04: answered self-hosted → `selfHostedConfirmed()` true, `managedConfirmed()` false; answered managed → the
 *     reverse;
 *   - PRF-05: the first request failed and nothing ever answered → both false;
 *   - PRF-06: a forced reload that fails after an answer leaves that answer confirmed, whichever profile it said;
 *   - PRF-07: a forced reload that answers the other profile → the helpers follow it;
 *   - PRF-08: reactive — read inside an effect (a template, a `$derived`), they follow the store.
 * A case that expects both false then lands an answer and sees it confirmed: a helper that always says false passes none.
 *
 * The REAL store, never a fake: answers land through `instanceConfig.load({force: true, fetchConfig})`, with fetchers the
 * test settles by hand — no clock, no network. The store keeps its state in module-level `$state`, so every case takes a
 * freshly imported graph (`vi.resetModules()` + `import()`, as `instanceConfig.test.ts` does): the store, the helpers —
 * which import that very store — and `svelte` with the rune helpers of the same graph. No case inherits its neighbour's
 * answer, in any order. `$lib/api` and `$lib/debug` are mocks: the generated client must never be asked (every request
 * here has a fetcher of the test, checked after each case), and the warning of a failed request goes to a spy.
 *
 * Written red-first, before `profile.ts` exists: the module is loaded lazily through a glob (the pattern of
 * `donations.test.ts`), so every case fails on its own, naming the missing module.
 */
import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';
import type {InstanceConfig} from './instanceConfig.svelte';

const mocks = vi.hoisted(() => ({
    getInstanceConfig: vi.fn().mockName('zodiosApi.get_instance_config_api_v1_system_instance_get'),
}));

vi.mock('$lib/api', () => ({zodiosApi: {get_instance_config_api_v1_system_instance_get: mocks.getInstanceConfig}}));
vi.mock('$lib/debug', () => ({debug: {log: vi.fn(), warn: vi.fn(), error: vi.fn(), info: vi.fn()}, isDebugEnabled: () => false}));

type Profile = InstanceConfig['profile'];

/** `[selfHostedConfirmed(), managedConfirmed()]`: what the two helpers say, read together. */
type Confirmed = [selfHosted: boolean, managed: boolean];

const PROFILES: readonly Profile[] = ['selfhosted', 'managed'];

/** The server's answer for each profile; the accounts part differs too, as it does between the two kinds of instance. */
const ANSWER: Record<Profile, InstanceConfig> = {
    selfhosted: {profile: 'selfhosted', accounts: {registration_mode: 'open', registration_locked: false}},
    managed: {profile: 'managed', accounts: {registration_mode: 'invite', registration_locked: true}},
};

/** What the helpers must say once the server's answer has landed: the helper of that profile alone is true. */
const CONFIRMED: Record<Profile, Confirmed> = {selfhosted: [true, false], managed: [false, true]};

// ---------------------------------------------------------------------------
// Loading the module under test, with the store it reads
// ---------------------------------------------------------------------------

interface ProfileModule {
    selfHostedConfirmed(): boolean;
    managedConfirmed(): boolean;
}

// A lazy glob rather than a literal import: the module does not exist yet, and a missing file must fail each case on its
// own, naming it, instead of failing the whole file at collection.
const PROFILE_MODULES = import.meta.glob<Partial<ProfileModule>>('./profile.ts');

/** The helpers of the current module graph, or the reason they cannot be loaded. */
async function importProfile(): Promise<ProfileModule> {
    const load = PROFILE_MODULES['./profile.ts'];
    if (!load) throw new Error('profile.ts cannot be found next to this test (src/lib/features/instance/): it should export selfHostedConfirmed() and managedConfirmed()');
    const mod = await load();
    const missing = (['selfHostedConfirmed', 'managedConfirmed'] as const).filter((name) => typeof mod[name] !== 'function');
    if (missing.length > 0) throw new Error(`profile.ts does not export ${missing.join(' and ')} as a function`);
    return mod as ProfileModule;
}

/**
 * A page load that has just begun: the store, the helpers — imported after it, so they read this very store — and the
 * rune helpers and `flushSync` of the same module graph.
 */
async function freshPageLoad() {
    vi.resetModules();
    const store = await import('./instanceConfig.svelte');
    const {selfHostedConfirmed, managedConfirmed} = await importProfile();
    const runes = await import('$test/runes.svelte');
    const {flushSync} = await import('svelte');
    const confirmed = (): Confirmed => [selfHostedConfirmed(), managedConfirmed()];
    return {...store, ...runes, flushSync, selfHostedConfirmed, managedConfirmed, confirmed};
}

type Store = (typeof import('./instanceConfig.svelte'))['instanceConfig'];

/** One forced request, and the server answers it with `config`. */
async function serverAnswers(instanceConfig: Store, config: InstanceConfig): Promise<void> {
    await instanceConfig.load({force: true, fetchConfig: () => Promise.resolve(config)});
}

/** One forced request, and it fails. */
async function requestFails(instanceConfig: Store): Promise<void> {
    await instanceConfig.load({force: true, fetchConfig: () => Promise.reject(new Error('503 Service Unavailable'))});
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
    mocks.getInstanceConfig.mockClear();
});

afterEach(() => {
    expect(mocks.getInstanceConfig, 'every request of these cases has a fetcher of the test: none may fall back to GET /system/instance').not.toHaveBeenCalled();
});

// ---------------------------------------------------------------------------
// The cases
// ---------------------------------------------------------------------------

describe('profile.ts — the module', () => {
    it('PRF-01: exports selfHostedConfirmed() and managedConfirmed() as functions', async () => {
        const {selfHostedConfirmed, managedConfirmed} = await freshPageLoad();

        expect([typeof selfHostedConfirmed, typeof managedConfirmed]).toEqual(['function', 'function']);
    });
});

describe('before the server answers — the defaults say self-hosted, and confirm nothing', () => {
    it('PRF-02: before any request, both are false', async () => {
        const {instanceConfig, confirmed} = await freshPageLoad();

        expect([instanceConfig.config.profile, instanceConfig.loaded], 'the premise: the defaults say self-hosted, and nobody asked the server yet').toEqual(['selfhosted', false]);
        expect(confirmed(), 'nothing is confirmed before the server answers').toEqual([false, false]);

        await serverAnswers(instanceConfig, ANSWER.selfhosted);
        expect(confirmed(), 'the same helpers read this store: its answer is confirmed at once').toEqual(CONFIRMED.selfhosted);
    });

    it('PRF-03: while the first request is in flight, both are false', async () => {
        const {instanceConfig, confirmed} = await freshPageLoad();
        const {fetchConfig, answers} = scriptedFetch();

        const loading = instanceConfig.load({force: true, fetchConfig});
        expect(fetchConfig, 'the request is in flight').toHaveBeenCalledTimes(1);
        expect([instanceConfig.config.profile, instanceConfig.loaded], 'the premise: the defaults are still in force').toEqual(['selfhosted', false]);
        expect(confirmed(), 'a managed instance must not read as self-hosted while its answer is on the way').toEqual([false, false]);

        answers[0].resolve(ANSWER.managed);
        await loading;
        expect(confirmed(), 'the answer landed: managed').toEqual(CONFIRMED.managed);
    });
});

describe('the server answered — the helpers say what it said', () => {
    it.each(PROFILES)('PRF-04: answered %s → the helper of that profile alone is true', async (profile) => {
        const {instanceConfig, confirmed} = await freshPageLoad();

        await serverAnswers(instanceConfig, ANSWER[profile]);

        expect([instanceConfig.loaded, instanceConfig.config.profile], 'the premise: the answer is in force').toEqual([true, profile]);
        expect(confirmed()).toEqual(CONFIRMED[profile]);
    });
});

describe('a failed request — it confirms nothing, and takes back nothing', () => {
    it('PRF-05: the first request failed and nothing ever answered: both are false', async () => {
        const {instanceConfig, confirmed} = await freshPageLoad();

        await requestFails(instanceConfig);

        expect([instanceConfig.config.profile, instanceConfig.loaded, instanceConfig.failed], 'the premise: the defaults are in force, and the request failed').toEqual(['selfhosted', false, true]);
        expect(confirmed(), 'the defaults confirm nothing, failed request or not').toEqual([false, false]);

        await serverAnswers(instanceConfig, ANSWER.selfhosted);
        expect(confirmed(), 'the next request asks again, and its answer is confirmed').toEqual(CONFIRMED.selfhosted);
    });

    it.each(PROFILES)('PRF-06: answered %s, then a forced reload failed → the answer stays confirmed', async (profile) => {
        const {instanceConfig, confirmed} = await freshPageLoad();
        await serverAnswers(instanceConfig, ANSWER[profile]);
        expect(confirmed(), 'the answer, before the reload').toEqual(CONFIRMED[profile]);

        await requestFails(instanceConfig);

        expect([instanceConfig.loaded, instanceConfig.failed, instanceConfig.config.profile], 'the premise: the last request failed, and the answer is still in force').toEqual([true, true, profile]);
        expect(confirmed(), 'a failed reload takes back nothing the server said').toEqual(CONFIRMED[profile]);
    });
});

describe('a forced reload — the helpers follow the latest answer', () => {
    it.each([
        ['selfhosted', 'managed'],
        ['managed', 'selfhosted'],
    ] as const)('PRF-07: answered %s, then a forced reload answered %s → the helpers follow', async (from, to) => {
        const {instanceConfig, confirmed} = await freshPageLoad();
        await serverAnswers(instanceConfig, ANSWER[from]);
        expect(confirmed(), `the first answer: ${from}`).toEqual(CONFIRMED[from]);

        await serverAnswers(instanceConfig, ANSWER[to]);

        expect([instanceConfig.loaded, instanceConfig.failed, instanceConfig.config.profile], 'the premise: the reload answered').toEqual([true, false, to]);
        expect(confirmed(), `the reload answered ${to}`).toEqual(CONFIRMED[to]);
    });
});

describe('reactive — read inside an effect, the helpers follow the store', () => {
    it('PRF-08: nothing before the answer, self-hosted once it says so, managed after a forced reload, unchanged by a failed one', async () => {
        const {instanceConfig, confirmed, assertEffectsRun, recordReads, flushSync} = await freshPageLoad();
        assertEffectsRun();
        const reads = recordReads(confirmed);
        try {
            expect(reads.values.at(-1), 'before the answer: nothing confirmed').toEqual([false, false]);

            await serverAnswers(instanceConfig, ANSWER.selfhosted);
            flushSync();
            expect(reads.values.at(-1), 'the answer said self-hosted: the effect read it again').toEqual(CONFIRMED.selfhosted);

            await serverAnswers(instanceConfig, ANSWER.managed);
            flushSync();
            expect(reads.values.at(-1), 'a forced reload said managed: the effect read it again').toEqual(CONFIRMED.managed);

            await requestFails(instanceConfig);
            flushSync();
            expect(reads.values.at(-1), 'a failed reload changes nothing the helpers say').toEqual(CONFIRMED.managed);

            expect(
                reads.values.filter((value) => value instanceof Error),
                'every read answered',
            ).toEqual([]);
        } finally {
            reads.stop();
        }
    });
});
