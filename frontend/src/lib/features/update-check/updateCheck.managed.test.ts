/**
 * checkForNewerRelease() on a managed instance (F05, lot A9 of workstream A): the automatic update check — the one the
 * (app) layout runs after an admin signs in (`routes/(app)/+layout.svelte`, `checkForNewerRelease(info.app_version)`) —
 * never runs there. A managed instance is updated by its hoster: telling its admin to `docker pull` is noise at best.
 *
 * The contract under test (approved by the coordinator, 17/10): `checkForNewerRelease()` awaits
 * `instanceConfig.load()` and, when the profile is `managed`, returns null **without any probe** — no release request
 * (`fetchFn`, or the global `fetch` it defaults to), no image probe (`imageProbe`, or the backend alias it defaults to),
 * no cache write. Self-hosted: unchanged.
 *   - UCM-01: managed, called exactly as the layout calls it (no seams): null; no `fetch`, no API alias, nothing
 *     written; `load()` asked;
 *   - UCM-02: the answer lands while the call waits on `load()`, and says managed: nothing probed before, nothing
 *     after — the profile is read once the server has answered, not from the defaults (which say self-hosted);
 *   - UCM-03: managed with a fresh cached release that would prompt: no image probe, the cache left as it was;
 *   - UCM-04 / UCM-05 (positive controls, green today): self-hosted, the network path and the cached path run as
 *     before — they also prove the seams below are wired, so the absences of UCM-01..03 are not vacuous;
 *   - UCM-06: self-hosted with the answer pending: nothing probed until `load()` settles, then the probe runs.
 *
 * Mocks, all owned here: `$lib/features/instance/instanceConfig.svelte` is a fake with the real store's shape —
 * getters over a `$state` box (`reactiveBox`) — whose `load` each test programs: answering at once, or when the test
 * says so; `$lib/api` is a proxy recording every alias called and refusing it (no network); the global `fetch` and
 * `localStorage` are stubs; `Date.now` is pinned so the cache's freshness does not depend on the clock.
 *
 * Node env: no DOM needed.
 */
import {afterEach, beforeEach, describe, expect, it, vi, type Mock} from 'vitest';
import type {InstanceConfig} from '$lib/features/instance/instanceConfig.svelte';

const mocks = await vi.hoisted(async () => {
    const {reactiveBox} = await import('$test/runes.svelte');
    /** What the real store holds until the server answers: `DEFAULT_INSTANCE_CONFIG`, a self-hosted instance. */
    const BEFORE_ANSWER = {profile: 'selfhosted', accounts: {registration_mode: 'open', registration_locked: false}} as InstanceConfig;
    return {
        BEFORE_ANSWER,
        instance: reactiveBox<{config: InstanceConfig; loaded: boolean; failed: boolean}>({config: BEFORE_ANSWER, loaded: false, failed: false}),
        instanceLoad: vi.fn<(options?: {force?: boolean}) => Promise<void>>().mockName('instanceConfig.load'),
        /** Every `zodiosApi` alias called, by name, in order. */
        apiCalls: [] as string[],
    };
});

vi.mock('$lib/features/instance/instanceConfig.svelte', () => ({
    DEFAULT_INSTANCE_CONFIG: mocks.BEFORE_ANSWER,
    fetchInstanceConfigFromApi: () => Promise.reject(new Error('no network in this test')),
    instanceConfig: {
        get config() {
            return mocks.instance.config;
        },
        get loaded() {
            return mocks.instance.loaded;
        },
        get failed() {
            return mocks.instance.failed;
        },
        load: mocks.instanceLoad,
    },
}));

// Every alias is recorded and refused: the default image probe goes through the backend
// (`get_container_image_status_api_v1_system_container_image_status_get`), and no case may reach a network.
vi.mock('$lib/api', () => ({
    zodiosApi: new Proxy(
        {},
        {
            get(_target, property) {
                if (typeof property !== 'string' || property === 'then') return undefined;
                return () => {
                    mocks.apiCalls.push(property);
                    return Promise.reject(new Error(`no network in this test: ${property}`));
                };
            },
        },
    ),
}));

import {checkForNewerRelease, readCache, writeCache, type ImageProbeResult, type NewerRelease} from './updateCheck';

const SELFHOSTED: InstanceConfig = {profile: 'selfhosted', accounts: {registration_mode: 'open', registration_locked: false}};
const MANAGED: InstanceConfig = {...SELFHOSTED, profile: 'managed'};

/** The running version, and a stable release newer than it. */
const RUNNING = '1.0.0';
const RELEASE: NewerRelease = {version: '9.9.9', tag: 'v9.9.9', url: 'https://example.com/release-9.9.9', name: 'Release 9.9.9'};
const NOW = 1_800_000_000_000;

/** An in-memory Storage whose writes are recorded. */
function fakeStorage() {
    const map = new Map<string, string>();
    return {
        map,
        getItem: vi.fn((key: string) => map.get(key) ?? null),
        setItem: vi.fn((key: string, value: string) => void map.set(key, value)),
        removeItem: vi.fn((key: string) => void map.delete(key)),
    };
}

/** GitHub's `/releases/latest`, answering `RELEASE`. */
function githubAnswersRelease(): Mock<typeof fetch> {
    return vi.fn<typeof fetch>(
        async () =>
            new Response(JSON.stringify({tag_name: RELEASE.tag, html_url: RELEASE.url, name: RELEASE.name, draft: false, prerelease: false}), {
                status: 200,
                headers: {'content-type': 'application/json'},
            }),
    );
}

/** The image gate, saying the release's image is published. */
function imagePublished(): Mock<(version: string) => Promise<ImageProbeResult>> {
    return vi.fn(async (_version: string): Promise<ImageProbeResult> => ({status: 'published'}));
}

function deferred(): {promise: Promise<void>; resolve: () => void} {
    let resolve!: () => void;
    const promise = new Promise<void>((res) => {
        resolve = res;
    });
    return {promise, resolve};
}

/** The server's answer is in, as `instanceConfig.load()` leaves it. */
function serverAnswered(config: InstanceConfig): void {
    mocks.instance.config = config;
    mocks.instance.loaded = true;
    mocks.instance.failed = false;
}

/** `load()` waits for the test, then lands `config`: the request is in flight until `answer.resolve()`. */
function answerLandsLater(config: InstanceConfig): {resolve: () => void} {
    const answer = deferred();
    mocks.instanceLoad.mockImplementation(async () => {
        await answer.promise;
        serverAnswered(config);
    });
    return answer;
}

let storage: ReturnType<typeof fakeStorage>;
let globalFetch: Mock<typeof fetch>;

beforeEach(() => {
    mocks.instance.config = mocks.BEFORE_ANSWER;
    mocks.instance.loaded = false;
    mocks.instance.failed = false;
    mocks.instanceLoad.mockReset();
    mocks.instanceLoad.mockImplementation(() => Promise.resolve());
    mocks.apiCalls.length = 0;
    storage = fakeStorage();
    vi.stubGlobal('localStorage', storage);
    // What the layout's call reaches when it passes no `fetchFn`: GitHub, answering a newer release.
    globalFetch = githubAnswersRelease();
    vi.stubGlobal('fetch', globalFetch);
    vi.spyOn(Date, 'now').mockReturnValue(NOW);
});

afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
});

describe('checkForNewerRelease() — managed: null, without any probe', () => {
    // red until A9
    it('UCM-01: called as the layout calls it (no seams) — no release request, no image probe, no cache write; null', async () => {
        serverAnswered(MANAGED);

        const result = await checkForNewerRelease(RUNNING);

        expect(globalFetch, 'no request to GitHub’s releases').not.toHaveBeenCalled();
        expect(mocks.apiCalls, 'no image probe through the backend, no other alias').toEqual([]);
        expect(storage.setItem, 'nothing written to the update-check cache').not.toHaveBeenCalled();
        expect(mocks.instanceLoad, 'it asks the instance configuration first').toHaveBeenCalled();
        expect(result).toBeNull();
    });

    // red until A9
    it('UCM-02: the answer lands while the call waits on load() and says managed — nothing probed before it, nothing after; null', async () => {
        const answer = answerLandsLater(MANAGED);
        const fetchFn = githubAnswersRelease();
        const imageProbe = imagePublished();

        const pending = checkForNewerRelease(RUNNING, fetchFn, imageProbe);
        await vi.waitFor(() => expect(mocks.instanceLoad, 'it asks the instance configuration').toHaveBeenCalled(), {timeout: 2_000});
        expect(fetchFn, 'nothing probed while the instance has not answered: the defaults say self-hosted').not.toHaveBeenCalled();

        answer.resolve();
        const result = await pending;

        expect(fetchFn, 'no request to GitHub’s releases').not.toHaveBeenCalled();
        expect(imageProbe, 'no image probe').not.toHaveBeenCalled();
        expect(storage.setItem, 'nothing written to the update-check cache').not.toHaveBeenCalled();
        expect(result).toBeNull();
    });

    // red until A9
    it('UCM-03: a fresh cached release that would prompt — no image probe, the cache left as it was; null', async () => {
        writeCache({checkedAt: NOW, latest: RELEASE, probeStatus: 'success'}, storage);
        storage.setItem.mockClear();
        const cached = [...storage.map.entries()];
        serverAnswered(MANAGED);
        const fetchFn = githubAnswersRelease();
        const imageProbe = imagePublished();

        const result = await checkForNewerRelease(RUNNING, fetchFn, imageProbe);

        expect(imageProbe, 'no image probe, though the cache holds a newer release').not.toHaveBeenCalled();
        expect(fetchFn, 'no request to GitHub’s releases').not.toHaveBeenCalled();
        expect(storage.setItem, 'nothing written to the update-check cache').not.toHaveBeenCalled();
        expect([...storage.map.entries()], 'the cache is left as it was').toEqual(cached);
        expect(result).toBeNull();
    });
});

describe('checkForNewerRelease() — self-hosted: unchanged', () => {
    it('UCM-04: an empty cache — the release probe and the image gate run as before, the cache is written, the release comes back (positive control)', async () => {
        serverAnswered(SELFHOSTED);
        const fetchFn = githubAnswersRelease();
        const imageProbe = imagePublished();

        const result = await checkForNewerRelease(RUNNING, fetchFn, imageProbe);

        expect(fetchFn).toHaveBeenCalledTimes(1);
        expect(String(fetchFn.mock.calls[0][0])).toContain('/releases/latest');
        expect(imageProbe).toHaveBeenCalledTimes(1);
        expect(imageProbe).toHaveBeenCalledWith(RELEASE.version);
        expect(readCache(storage)?.latest, 'the probe is cached').toEqual(RELEASE);
        expect(result).toEqual(RELEASE);
    });

    it('UCM-05: a fresh cached release — no network, the image gate asked once, the release comes back (positive control)', async () => {
        writeCache({checkedAt: NOW, latest: RELEASE, probeStatus: 'success'}, storage);
        serverAnswered(SELFHOSTED);
        const fetchFn = githubAnswersRelease();
        const imageProbe = imagePublished();

        const result = await checkForNewerRelease(RUNNING, fetchFn, imageProbe);

        expect(fetchFn, 'the cache is fresh').not.toHaveBeenCalled();
        expect(imageProbe).toHaveBeenCalledTimes(1);
        expect(imageProbe).toHaveBeenCalledWith(RELEASE.version);
        expect(result).toEqual(RELEASE);
    });

    // red until A9
    it('UCM-06: the answer pending — nothing probed until load() settles; once it says self-hosted, the probe runs and the release comes back', async () => {
        const answer = answerLandsLater(SELFHOSTED);
        const fetchFn = githubAnswersRelease();
        const imageProbe = imagePublished();

        const pending = checkForNewerRelease(RUNNING, fetchFn, imageProbe);
        await vi.waitFor(() => expect(mocks.instanceLoad, 'it asks the instance configuration').toHaveBeenCalled(), {timeout: 2_000});
        expect(fetchFn, 'nothing probed before the instance answered').not.toHaveBeenCalled();
        expect(imageProbe, 'nothing probed before the instance answered').not.toHaveBeenCalled();

        answer.resolve();

        await expect(pending).resolves.toEqual(RELEASE);
        expect(fetchFn).toHaveBeenCalledTimes(1);
        expect(imageProbe).toHaveBeenCalledTimes(1);
    });
});
