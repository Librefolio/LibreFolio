import {describe, expect, it, vi, type Mock} from 'vitest';

import {createOnboardingController} from './onboarding.svelte';
import type {OnboardingApi, OnboardingProgressItem, OnboardingProgressResponse} from '$lib/types/onboarding';

/**
 * Onboarding controller — load lifecycle, generation guarding and replay.
 *
 * The controller is created through its factory (`createOnboardingController`),
 * never through the module singleton: the singleton wires itself into the real
 * `clientSession` reset registry at import time, which is a side effect this
 * spec has no business triggering. Every dependency (identity, generation,
 * storage, clock) is injected, so a "stale" or "account switch" scenario is
 * produced by moving the fake dependency, never by faking time.
 */

/** Minimal in-memory Storage — enough surface for the controller's own usage. */
function createMemoryStorage(overrides: Partial<Storage> = {}): Storage {
    const data = new Map<string, string>();
    const storage = {
        get length() {
            return data.size;
        },
        clear() {
            data.clear();
        },
        getItem(key: string) {
            return data.has(key) ? (data.get(key) as string) : null;
        },
        key(index: number) {
            return Array.from(data.keys())[index] ?? null;
        },
        removeItem(key: string) {
            data.delete(key);
        },
        setItem(key: string, value: string) {
            data.set(key, value);
        },
        ...overrides,
    };
    return storage as unknown as Storage;
}

function progressItem(overrides: Partial<OnboardingProgressItem> = {}): OnboardingProgressItem {
    return {
        flow: 'welcome',
        status: 'pending',
        version: 1,
        current_version: 1,
        update_available: false,
        created_at: '2026-01-01T00:00:00Z',
        updated_at: '2026-01-01T00:00:00Z',
        completed_at: null,
        skipped_at: null,
        ...overrides,
    };
}

function progressResponse(items: OnboardingProgressItem[]): OnboardingProgressResponse {
    return {flows: items};
}

function deferred<T>() {
    let resolve!: (value: T) => void;
    let reject!: (error: unknown) => void;
    const promise = new Promise<T>((res, rej) => {
        resolve = res;
        reject = rej;
    });
    return {promise, resolve, reject};
}

/** A fake API surface whose two proxied endpoints are independently controllable. */
function fakeApi(): OnboardingApi & {
    getProgress: Mock<OnboardingApi['getProgress']>;
    completeFlow: Mock<OnboardingApi['completeFlow']>;
    skipFlow: Mock<OnboardingApi['skipFlow']>;
} {
    return {
        getProgress: vi.fn<OnboardingApi['getProgress']>(),
        completeFlow: vi.fn<OnboardingApi['completeFlow']>(),
        skipFlow: vi.fn<OnboardingApi['skipFlow']>(),
    };
}

/** Builds a controller whose identity/generation are driven by mutable test-owned refs. */
function buildController(initial: {userId?: string | null; generation?: number} = {}) {
    let userId: string | null = initial.userId ?? 'user-1';
    let generation = initial.generation ?? 1;
    const storage = createMemoryStorage();
    const controller = createOnboardingController({
        getUserId: () => userId,
        getGeneration: () => generation,
        isCurrent: (g: number) => g === generation,
        getSessionStorage: () => storage,
        now: () => 1000,
    });
    return {
        controller,
        storage,
        setUserId: (next: string | null) => {
            userId = next;
        },
        setGeneration: (next: number) => {
            generation = next;
        },
    };
}

describe('onboarding controller — load', () => {
    it('goes loading -> ready and stores the response on success', async () => {
        const {controller} = buildController();
        const api = fakeApi();
        const response = progressResponse([progressItem()]);
        const {promise, resolve} = deferred<OnboardingProgressResponse>();
        api.getProgress.mockReturnValue(promise);

        const loadPromise = controller.load(api);
        expect(controller.state).toBe('loading');
        expect(controller.error).toBeNull();

        resolve(response);
        await loadPromise;

        expect(controller.state).toBe('ready');
        expect(controller.progress).toEqual(response);
    });

    it('goes loading -> error and surfaces the message on failure', async () => {
        const {controller} = buildController();
        const api = fakeApi();
        api.getProgress.mockRejectedValue(new Error('progress unavailable'));

        await expect(controller.load(api)).rejects.toThrow('progress unavailable');

        expect(controller.state).toBe('error');
        expect(controller.error).toBe('progress unavailable');
        expect(controller.progress).toBeNull();
    });

    it('wraps a non-Error rejection into a generic message', async () => {
        const {controller} = buildController();
        const api = fakeApi();
        api.getProgress.mockRejectedValue('boom');

        await expect(controller.load(api)).rejects.toBe('boom');
        expect(controller.error).toBe('Onboarding request failed');
    });

    it('discards a response that resolves after the account generation moved on', async () => {
        const {controller, setGeneration} = buildController({generation: 1});
        const api = fakeApi();
        const {promise, resolve} = deferred<OnboardingProgressResponse>();
        api.getProgress.mockReturnValue(promise);

        const loadPromise = controller.load(api);
        // Simulate an account/session-generation switch while the request is in flight.
        setGeneration(2);
        resolve(progressResponse([progressItem()]));

        const result = await loadPromise;

        expect(result).toBeNull();
        expect(controller.progress).toBeNull();
        expect(controller.state).toBe('loading'); // never advanced to 'ready' for the stale ticket
    });

    it('discards a response that resolves after the user id changed', async () => {
        const {controller, setUserId} = buildController({userId: 'user-1'});
        const api = fakeApi();
        const {promise, resolve} = deferred<OnboardingProgressResponse>();
        api.getProgress.mockReturnValue(promise);

        const loadPromise = controller.load(api);
        setUserId('user-2');
        resolve(progressResponse([progressItem()]));

        expect(await loadPromise).toBeNull();
        expect(controller.progress).toBeNull();
    });

    it('discards a stale error the same way it discards a stale success', async () => {
        const {controller, setGeneration} = buildController({generation: 1});
        const api = fakeApi();
        const {promise, reject} = deferred<OnboardingProgressResponse>();
        api.getProgress.mockReturnValue(promise);

        const loadPromise = controller.load(api);
        setGeneration(2);
        reject(new Error('late failure'));

        expect(await loadPromise).toBeNull();
        expect(controller.error).toBeNull();
        expect(controller.state).toBe('loading');
    });

    it('lets the latest request win when an earlier one resolves last', async () => {
        const {controller} = buildController();
        const apiFirst = fakeApi();
        const apiSecond = fakeApi();
        const first = deferred<OnboardingProgressResponse>();
        const second = deferred<OnboardingProgressResponse>();
        apiFirst.getProgress.mockReturnValue(first.promise);
        apiSecond.getProgress.mockReturnValue(second.promise);

        const firstResponse = progressResponse([progressItem({version: 1})]);
        const secondResponse = progressResponse([progressItem({version: 2})]);

        const p1 = controller.load(apiFirst);
        const p2 = controller.load(apiSecond);

        // Resolve the *second* (latest) request first, then the stale first request —
        // the sequence ticket, not arrival order, must decide the winner.
        second.resolve(secondResponse);
        first.resolve(firstResponse);

        await Promise.all([p1, p2]);

        expect(controller.progress).toEqual(secondResponse);
    });
});

describe('onboarding controller — requiresAutomaticFlow (terminal status predicate)', () => {
    it('is true only for a pending flow, regardless of update_available', async () => {
        const {controller} = buildController();
        const api = fakeApi();
        api.getProgress.mockResolvedValue(
            progressResponse([progressItem({flow: 'welcome', status: 'pending', update_available: false}), progressItem({flow: 'intro_tour', status: 'completed', update_available: true}), progressItem({flow: 'import_guide', status: 'skipped', update_available: true})]),
        );
        await controller.load(api);

        expect(controller.requiresAutomaticFlow('welcome')).toBe(true);
        expect(controller.requiresAutomaticFlow('intro_tour')).toBe(false);
        expect(controller.requiresAutomaticFlow('import_guide')).toBe(false);
    });

    it('is false for a flow that has not been loaded at all', () => {
        const {controller} = buildController();
        expect(controller.requiresAutomaticFlow('welcome')).toBe(false);
    });
});

describe('onboarding controller — transition (complete/skip)', () => {
    it('marks transitioningFlow during the call and replaces the flow row on success', async () => {
        const {controller} = buildController();
        const api = fakeApi();
        api.getProgress.mockResolvedValue(progressResponse([progressItem({flow: 'welcome', status: 'pending', version: 1})]));
        await controller.load(api);

        const {promise, resolve} = deferred<OnboardingProgressItem>();
        api.completeFlow.mockReturnValue(promise);

        const transitionPromise = controller.complete(api, 'welcome', 1);
        expect(controller.transitioningFlow).toBe('welcome');

        const updated = progressItem({flow: 'welcome', status: 'completed', version: 1});
        resolve(updated);
        const result = await transitionPromise;

        expect(result).toEqual(updated);
        expect(controller.transitioningFlow).toBeNull();
        expect(controller.findFlow('welcome')).toEqual(updated);
        expect(api.completeFlow).toHaveBeenCalledWith('welcome', {expected_version: 1});
    });

    it('surfaces the error message and rethrows on a failed skip', async () => {
        const {controller} = buildController();
        const api = fakeApi();
        api.skipFlow.mockRejectedValue(new Error('version conflict'));

        await expect(controller.skip(api, 'welcome', 3)).rejects.toThrow('version conflict');

        expect(controller.error).toBe('version conflict');
        expect(controller.transitioningFlow).toBeNull();
        expect(api.skipFlow).toHaveBeenCalledWith('welcome', {expected_version: 3});
    });

    it('discards a transition outcome that arrives after the account changed', async () => {
        const {controller, setGeneration} = buildController({generation: 1});
        const api = fakeApi();
        const {promise, resolve} = deferred<OnboardingProgressItem>();
        api.completeFlow.mockReturnValue(promise);

        const transitionPromise = controller.complete(api, 'welcome', 1);
        setGeneration(2);
        resolve(progressItem({flow: 'welcome', status: 'completed', version: 1}));

        expect(await transitionPromise).toBeNull();
        expect(controller.progress).toBeNull(); // replaceFlow never ran
        expect(controller.error).toBeNull();
    });

    it('lets a newer load() supersede an in-flight transition: transitioningFlow clears immediately, and the stale transition resolution neither gets stuck nor overwrites the newer progress', async () => {
        const {controller} = buildController();
        const api = fakeApi();

        // Establish a ready state first, so there is a real flow row to be "in flight" against.
        api.getProgress.mockResolvedValueOnce(progressResponse([progressItem({flow: 'welcome', status: 'pending', version: 1})]));
        await controller.load(api);

        const transitionDeferred = deferred<OnboardingProgressItem>();
        api.completeFlow.mockReturnValue(transitionDeferred.promise);
        const transitionPromise = controller.complete(api, 'welcome', 1);
        expect(controller.transitioningFlow).toBe('welcome');

        // A newer load() starts while the transition is still in flight. Its ticket has a
        // later sequence number, which is what makes the earlier transition's ticket stale.
        const loadDeferred = deferred<OnboardingProgressResponse>();
        api.getProgress.mockReturnValue(loadDeferred.promise);
        const loadPromise = controller.load(api);

        // Superseding must be synchronous and immediate: no need to await anything for
        // transitioningFlow to clear and the loading state to take over.
        expect(controller.transitioningFlow).toBeNull();
        expect(controller.state).toBe('loading');

        // Now the *stale* transition resolves. It must not resurrect transitioningFlow,
        // must not report itself as having applied, and must not clobber load()'s outcome.
        transitionDeferred.resolve(progressItem({flow: 'welcome', status: 'completed', version: 1}));
        const transitionResult = await transitionPromise;
        expect(transitionResult).toBeNull();
        expect(controller.transitioningFlow).toBeNull();

        // The newer load's own response must win, untouched by the stale transition's payload.
        const freshResponse = progressResponse([progressItem({flow: 'welcome', status: 'pending', version: 2})]);
        loadDeferred.resolve(freshResponse);
        const loadResult = await loadPromise;

        expect(loadResult).toEqual(freshResponse);
        expect(controller.progress).toEqual(freshResponse);
        expect(controller.state).toBe('ready');
    });
});

describe('onboarding controller — replay (session + account scoped)', () => {
    it('starting a replay never calls the API', () => {
        const {controller} = buildController();
        // `startReplay`/`resumeReplay`/`updateReplayStep`/`clearReplay` take no `OnboardingApi`
        // parameter at all — there is structurally nothing here that could invoke a request.
        // What we can and do assert is the actual observable effect: a synchronous write to
        // storage, with no `state`/`error` change that a network round trip would produce.
        expect(controller.startReplay('welcome', 1, 'step-1')).toBe(true);
        expect(controller.state).toBe('idle');
        expect(controller.error).toBeNull();
        expect(controller.replay).toEqual({
            flow: 'welcome',
            version: 1,
            stepId: 'step-1',
            startedAt: 1000,
        });
    });

    it('keys replay storage by account + flow + version and cannot read another account', () => {
        const {controller, setUserId} = buildController({userId: 'user-1'});
        controller.startReplay('welcome', 2, 'step-a');

        // Switch to a different account entirely — a fresh controller sharing nothing
        // but the same in-memory storage backend represents "another account's session".
        setUserId('user-2');
        const resumedForOtherAccount = controller.resumeReplay('welcome', 2, ['step-a'], 'step-a');

        expect(resumedForOtherAccount).toBeNull();
        expect(controller.replay).toBeNull();

        // Switching back, the original account's saved step is still there.
        setUserId('user-1');
        const resumedForOwner = controller.resumeReplay('welcome', 2, ['step-a'], 'step-a');
        expect(resumedForOwner).toEqual({
            flow: 'welcome',
            version: 2,
            stepId: 'step-a',
            startedAt: 1000,
        });
    });

    it('removes a stale/invalid version and never applies it', () => {
        const {controller, storage} = buildController();
        controller.startReplay('welcome', 1, 'old-step');
        const oldKey = 'lf_user-1_onboarding_replay_welcome_v1';
        expect(storage.getItem(oldKey)).not.toBeNull();

        // The content version moved on to v2 — resuming at v2 must drop the v1 residue,
        // never resurrect it under a different key.
        const resumed = controller.resumeReplay('welcome', 2, ['new-step'], 'new-step');

        expect(resumed).toBeNull();
        expect(storage.getItem(oldKey)).toBeNull();
    });

    it('recovers to the fallback step when the saved step id is no longer valid', () => {
        const {controller} = buildController();
        controller.startReplay('welcome', 1, 'removed-step');

        const resumed = controller.resumeReplay('welcome', 1, ['first-step', 'second-step'], 'first-step');

        expect(resumed).toEqual({
            flow: 'welcome',
            version: 1,
            stepId: 'first-step',
            startedAt: 1000,
        });
        expect(controller.replay?.stepId).toBe('first-step');
    });

    it('discards a corrupted stored payload and removes it instead of applying it', () => {
        const {controller, storage} = buildController({userId: 'user-1'});
        const key = 'lf_user-1_onboarding_replay_welcome_v1';
        storage.setItem(key, JSON.stringify({flow: 'welcome', version: 1})); // missing stepId/startedAt

        const resumed = controller.resumeReplay('welcome', 1, ['step-a'], 'step-a');

        expect(resumed).toBeNull();
        expect(controller.replayStorageError).toBeTruthy();
        expect(storage.getItem(key)).toBeNull();
    });

    it('discards unparsable JSON in storage without throwing', () => {
        const {controller, storage} = buildController({userId: 'user-1'});
        const key = 'lf_user-1_onboarding_replay_welcome_v1';
        storage.setItem(key, '{not json');

        const resumed = controller.resumeReplay('welcome', 1, ['step-a'], 'step-a');

        expect(resumed).toBeNull();
        expect(controller.replay).toBeNull();
        expect(controller.replayStorageError).toBeTruthy();
        // The corrupted entry must be removed, not left behind: a retry on the same key
        // must not keep hitting the same unparsable payload forever.
        expect(storage.getItem(key)).toBeNull();
    });

    it('updates only the step id of an in-progress replay, keeping flow/version/startedAt', () => {
        const {controller} = buildController();
        controller.startReplay('welcome', 1, 'step-1');

        expect(controller.updateReplayStep('step-2')).toBe(true);

        expect(controller.replay).toEqual({
            flow: 'welcome',
            version: 1,
            stepId: 'step-2',
            startedAt: 1000,
        });
    });

    it('returns false updating a step when there is no active replay', () => {
        const {controller} = buildController();
        expect(controller.updateReplayStep('step-2')).toBe(false);
    });

    it('clears the stored replay for the given flow/version', () => {
        const {controller, storage} = buildController({userId: 'user-1'});
        controller.startReplay('welcome', 1, 'step-1');
        const key = 'lf_user-1_onboarding_replay_welcome_v1';
        expect(storage.getItem(key)).not.toBeNull();

        controller.clearReplay('welcome', 1);

        expect(storage.getItem(key)).toBeNull();
        expect(controller.replay).toBeNull();
    });

    it('surfaces a storage write failure instead of silently losing the replay', () => {
        const throwingStorage = createMemoryStorage({
            setItem: () => {
                throw new Error('quota exceeded');
            },
        });
        const throwing = createOnboardingController({
            getUserId: () => 'user-1',
            getGeneration: () => 1,
            isCurrent: () => true,
            getSessionStorage: () => throwingStorage,
            now: () => 1000,
        });

        expect(throwing.startReplay('welcome', 1, 'step-1')).toBe(false);
        expect(throwing.replayStorageError).toBe('quota exceeded');
    });

    it('surfaces "storage unavailable" when there is no session storage at all', () => {
        const controller = createOnboardingController({
            getUserId: () => 'user-1',
            getGeneration: () => 1,
            isCurrent: () => true,
            getSessionStorage: () => null,
            now: () => 1000,
        });

        expect(controller.startReplay('welcome', 1, 'step-1')).toBe(false);
        expect(controller.replayStorageError).toBe('Session storage is unavailable');

        expect(controller.resumeReplay('welcome', 1, ['step-1'], 'step-1')).toBeNull();
        expect(controller.replayStorageError).toBe('Session storage is unavailable');
    });
});

describe('onboarding controller — reset', () => {
    it('clears load, transition and replay state back to idle', async () => {
        const {controller} = buildController();
        const api = fakeApi();
        api.getProgress.mockResolvedValue(progressResponse([progressItem()]));
        await controller.load(api);
        controller.startReplay('welcome', 1, 'step-1');

        controller.reset();

        expect(controller.state).toBe('idle');
        expect(controller.progress).toBeNull();
        expect(controller.error).toBeNull();
        expect(controller.transitioningFlow).toBeNull();
        expect(controller.replay).toBeNull();
        expect(controller.replayStorageError).toBeNull();
    });

    it('makes any in-flight request from before the reset stale', async () => {
        const {controller} = buildController();
        const api = fakeApi();
        const {promise, resolve} = deferred<OnboardingProgressResponse>();
        api.getProgress.mockReturnValue(promise);

        const loadPromise = controller.load(api);
        controller.reset();
        resolve(progressResponse([progressItem()]));

        expect(await loadPromise).toBeNull();
        expect(controller.progress).toBeNull();
    });
});
