import {describe, expect, it, vi, type Mock} from 'vitest';

import {createAppBootstrap} from '$lib/features/onboarding/appBootstrap.svelte';
import {createOnboardingController} from './onboarding.svelte';
import {createOnboardingGuide, IMPORT_GUIDE_STEP_IDS, INTRO_TOUR_STEP_IDS} from '$lib/features/onboarding/onboardingGuide.svelte';
import {TRANSACTION_BULK_STEP_IDS, guideSteps, isCheckpointFlow, isStepManagedFlow, type ContextualOnboardingFlow} from '$lib/features/onboarding/onboardingGuideCatalog';
import {onboardingApi} from '$lib/features/onboarding/onboardingApi';
import {axiosInstance} from '$lib/api';
import {ONBOARDING_FLOWS, isOnboardingProgressDue, isOnboardingStepProgressDue, type OnboardingApi, type OnboardingFlow, type OnboardingProgressItem, type OnboardingProgressResponse, type OnboardingStepProgressItem, type OnboardingWelcomeCompleteRequest} from '$lib/types/onboarding';
import type {goto} from '$app/navigation';

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

function stepProgressItem(stepId: string, overrides: Partial<OnboardingStepProgressItem> = {}): OnboardingStepProgressItem {
    return {
        step_id: stepId,
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

function progressItem(overrides: Partial<OnboardingProgressItem> = {}): OnboardingProgressItem {
    const flow = overrides.flow ?? 'welcome';
    const status = overrides.status ?? 'pending';
    const managedStepIds = flow === 'import_guide' ? IMPORT_GUIDE_STEP_IDS : flow === 'transaction_bulk_guide' ? TRANSACTION_BULK_STEP_IDS : null;
    return {
        flow,
        status,
        version: 1,
        current_version: 1,
        update_available: false,
        created_at: '2026-01-01T00:00:00Z',
        updated_at: '2026-01-01T00:00:00Z',
        completed_at: null,
        skipped_at: null,
        ...(managedStepIds
            ? {
                  steps: managedStepIds.map((stepId) =>
                      stepProgressItem(stepId, {
                          status,
                          completed_at: status === 'completed' ? '2026-01-01T00:00:00Z' : null,
                          skipped_at: status === 'skipped' ? '2026-01-01T00:00:00Z' : null,
                      }),
                  ),
              }
            : {}),
        ...overrides,
    };
}

function progressResponse(items: OnboardingProgressItem[]): OnboardingProgressResponse {
    return {flows: items};
}

function wireProgressItem(item: OnboardingProgressItem): Record<string, unknown> {
    const {completed_at: _completedAt, skipped_at: _skippedAt, steps, ...flowFields} = item;
    return {
        ...flowFields,
        ...(steps
            ? {
                  steps: steps.map((step) => {
                      const {completed_at: _stepCompletedAt, skipped_at: _stepSkippedAt, ...stepFields} = step;
                      return stepFields;
                  }),
              }
            : {}),
    };
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

/** A fake API surface whose flow/step endpoints are independently controllable. */
function fakeApi(): OnboardingApi & {
    getProgress: Mock<OnboardingApi['getProgress']>;
    completeFlow: Mock<OnboardingApi['completeFlow']>;
    completeWelcome: Mock<OnboardingApi['completeWelcome']>;
    skipFlow: Mock<OnboardingApi['skipFlow']>;
    completeStep: Mock<OnboardingApi['completeStep']>;
    skipStep: Mock<OnboardingApi['skipStep']>;
} {
    return {
        getProgress: vi.fn<OnboardingApi['getProgress']>(),
        completeFlow: vi.fn<OnboardingApi['completeFlow']>(),
        completeWelcome: vi.fn<OnboardingApi['completeWelcome']>(),
        skipFlow: vi.fn<OnboardingApi['skipFlow']>(),
        completeStep: vi.fn<OnboardingApi['completeStep']>(),
        skipStep: vi.fn<OnboardingApi['skipStep']>(),
    };
}

function welcomeCompleteRequest(overrides: Partial<OnboardingWelcomeCompleteRequest> = {}): OnboardingWelcomeCompleteRequest {
    return {
        expected_version: 1,
        welcome_settings: {language: 'en', base_currency: 'EUR', avatar_url: null},
        ...overrides,
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

/**
 * Builds an `appBootstrap` instance whose identity/generation/welcome-flow/replay
 * inputs are all test-owned mutable refs, and whose three loaders are independently
 * controllable mocks (default: all resolved, so a test that doesn't care reaches
 * 'ready' without restating every mock).
 */
function buildBootstrap(initial: {userId?: string | null; generation?: number} = {}) {
    let userId: string | null = initial.userId ?? 'user-1';
    let generation = initial.generation ?? 1;
    let welcome: OnboardingProgressItem | null = null;
    const replayVersions = new Set<number>();

    const loadUserSettings = vi.fn<() => Promise<boolean>>().mockResolvedValue(true);
    const loadOnboarding = vi.fn<() => Promise<unknown>>().mockResolvedValue(undefined);
    const loadGlobalSettings = vi.fn<() => Promise<unknown>>().mockResolvedValue(undefined);

    const bootstrap = createAppBootstrap({
        getUserId: () => userId,
        getGeneration: () => generation,
        isCurrent: (g: number) => g === generation,
        loadUserSettings,
        loadOnboarding,
        loadGlobalSettings,
        findWelcome: () => welcome,
        checkWelcomeReplay: (version: number) => replayVersions.has(version),
    });

    return {
        bootstrap,
        loadUserSettings,
        loadOnboarding,
        loadGlobalSettings,
        setUserId: (next: string | null) => {
            userId = next;
        },
        setGeneration: (next: number) => {
            generation = next;
        },
        setWelcome: (next: OnboardingProgressItem | null) => {
            welcome = next;
        },
        setReplayVersion: (version: number, active: boolean) => {
            if (active) replayVersions.add(version);
            else replayVersions.delete(version);
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

describe('onboarding API — final contract', () => {
    it('requests and parses the 15-flow wire shape with Import/Bulk steps', async () => {
        const response = {
            flows: ONBOARDING_FLOWS.map((flow) => wireProgressItem(progressItem({flow}))),
        };
        const get = vi.spyOn(axiosInstance, 'get').mockResolvedValue({data: response} as never);
        try {
            const parsed = await onboardingApi.getProgress();

            expect(get).toHaveBeenCalledExactlyOnceWith('/api/v1/settings/onboarding');
            expect(parsed.flows.map((item) => item.flow)).toEqual(ONBOARDING_FLOWS);
            expect(parsed.flows.find((item) => item.flow === 'import_guide')?.steps?.map((step) => step.step_id)).toEqual(IMPORT_GUIDE_STEP_IDS);
            expect(parsed.flows.find((item) => item.flow === 'transaction_bulk_guide')?.steps?.map((step) => step.step_id)).toEqual(TRANSACTION_BULK_STEP_IDS);
            expect(parsed.flows.filter((item) => item.flow !== 'import_guide' && item.flow !== 'transaction_bulk_guide').every((item) => item.steps === undefined)).toBe(true);
        } finally {
            get.mockRestore();
        }
    });

    it('posts complete and skip to the step-specific endpoints', async () => {
        const updated = progressItem({flow: 'import_guide'});
        const post = vi.spyOn(axiosInstance, 'post').mockResolvedValue({data: updated} as never);
        try {
            await onboardingApi.completeStep('import_guide', 'import.assets', {expected_version: 3});
            await onboardingApi.skipStep('import_guide', 'import.fix', {expected_version: 3});

            expect(post).toHaveBeenNthCalledWith(1, '/api/v1/settings/onboarding/import_guide/steps/import.assets/complete', {
                expected_version: 3,
            });
            expect(post).toHaveBeenNthCalledWith(2, '/api/v1/settings/onboarding/import_guide/steps/import.fix/skip', {
                expected_version: 3,
            });
        } finally {
            post.mockRestore();
        }
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

describe('onboarding due predicates — final flow and step state', () => {
    it('treats pending records as due and terminal records as final', () => {
        expect(isOnboardingProgressDue(progressItem({status: 'pending'}))).toBe(true);
        expect(isOnboardingProgressDue(progressItem({status: 'completed'}))).toBe(false);
        expect(isOnboardingProgressDue(progressItem({status: 'skipped'}))).toBe(false);

        expect(isOnboardingStepProgressDue(stepProgressItem('import.assets', {status: 'pending'}))).toBe(true);
        expect(isOnboardingStepProgressDue(stepProgressItem('import.assets', {status: 'completed'}))).toBe(false);
        expect(isOnboardingStepProgressDue(stepProgressItem('import.assets', {status: 'skipped'}))).toBe(false);
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

describe('onboarding controller — step transition', () => {
    it('keys the request by flow and step, exposes the in-flight flow, and replaces only that flow', async () => {
        const {controller} = buildController();
        const api = fakeApi();
        const imported = progressItem({flow: 'import_guide'});
        const bulk = progressItem({flow: 'transaction_bulk_guide'});
        api.getProgress.mockResolvedValue(progressResponse([imported, bulk]));
        await controller.load(api);

        const request = deferred<OnboardingProgressItem>();
        api.completeStep.mockReturnValue(request.promise);
        const completedUpload = progressItem({
            flow: 'import_guide',
            steps: imported.steps?.map((step) => (step.step_id === 'import.upload' ? stepProgressItem(step.step_id, {status: 'completed', completed_at: '2026-01-02T00:00:00Z'}) : step)),
        });

        const pending = controller.completeStep(api, 'import_guide', 'import.upload', 1);
        expect(controller.transitioningFlow).toBe('import_guide');
        expect(api.completeStep).toHaveBeenCalledExactlyOnceWith('import_guide', 'import.upload', {
            expected_version: 1,
        });

        request.resolve(completedUpload);
        expect(await pending).toEqual(completedUpload);
        expect(controller.transitioningFlow).toBeNull();
        expect(controller.findStep('import_guide', 'import.upload')?.status).toBe('completed');
        expect(controller.findStep('import_guide', 'import.select')?.status).toBe('pending');
        expect(controller.findFlow('transaction_bulk_guide')).toEqual(bulk);
    });

    it('sends skip for only the addressed step and keeps the server aggregate payload', async () => {
        const {controller} = buildController();
        const api = fakeApi();
        const initial = progressItem({flow: 'transaction_bulk_guide'});
        api.getProgress.mockResolvedValue(progressResponse([initial]));
        await controller.load(api);
        const updated = progressItem({
            flow: 'transaction_bulk_guide',
            status: 'pending',
            steps: initial.steps?.map((step) => (step.step_id === 'transaction.bulk.validation' ? stepProgressItem(step.step_id, {status: 'skipped', skipped_at: '2026-01-02T00:00:00Z'}) : step)),
        });
        api.skipStep.mockResolvedValue(updated);

        const result = await controller.skipStep(api, 'transaction_bulk_guide', 'transaction.bulk.validation', 1);

        expect(result).toEqual(updated);
        expect(api.skipStep).toHaveBeenCalledExactlyOnceWith('transaction_bulk_guide', 'transaction.bulk.validation', {
            expected_version: 1,
        });
        expect(api.skipFlow).not.toHaveBeenCalled();
        expect(controller.findFlow('transaction_bulk_guide')?.status).toBe('pending');
        expect(controller.findStep('transaction_bulk_guide', 'transaction.bulk.validation')?.status).toBe('skipped');
    });
});

describe('onboarding controller — completeWelcome (atomic preferences + progress)', () => {
    it('marks transitioningFlow=welcome during the call and replaces the welcome row with the server response on success', async () => {
        const {controller} = buildController();
        const api = fakeApi();
        api.getProgress.mockResolvedValue(progressResponse([progressItem({flow: 'welcome', status: 'pending', version: 1}), progressItem({flow: 'intro_tour', status: 'pending', version: 1})]));
        await controller.load(api);

        const {promise, resolve} = deferred<OnboardingProgressItem>();
        api.completeWelcome.mockReturnValue(promise);
        const request = welcomeCompleteRequest({expected_version: 1, welcome_settings: {language: 'fr', base_currency: 'CHF', avatar_url: 'https://example.com/a.png'}});

        const completePromise = controller.completeWelcome(api, request);
        expect(controller.transitioningFlow).toBe('welcome');

        const updated = progressItem({flow: 'welcome', status: 'completed', version: 1});
        resolve(updated);
        const result = await completePromise;

        expect(result).toEqual(updated);
        expect(controller.transitioningFlow).toBeNull();
        expect(controller.findFlow('welcome')).toEqual(updated);
        expect(controller.findFlow('intro_tour')?.status).toBe('pending'); // other flows must be left untouched
        expect(controller.error).toBeNull();
        expect(api.completeWelcome).toHaveBeenCalledWith(request);
    });

    it('discards a stale-account completeWelcome outcome: transitioningFlow clears, the flow row is never replaced, and no error is recorded', async () => {
        const {controller, setGeneration} = buildController({generation: 1});
        const api = fakeApi();
        const {promise, resolve} = deferred<OnboardingProgressItem>();
        api.completeWelcome.mockReturnValue(promise);

        const completePromise = controller.completeWelcome(api, welcomeCompleteRequest());
        expect(controller.transitioningFlow).toBe('welcome');

        setGeneration(2);
        resolve(progressItem({flow: 'welcome', status: 'completed', version: 1}));

        expect(await completePromise).toBeNull();
        expect(controller.transitioningFlow).toBeNull();
        expect(controller.progress).toBeNull(); // replaceFlow never ran — there was nothing to replace into
        expect(controller.error).toBeNull();
    });

    it('discards a stale-generation completeWelcome outcome even when progress was already loaded, leaving the loaded snapshot untouched', async () => {
        const {controller, setGeneration} = buildController({generation: 1});
        const api = fakeApi();
        api.getProgress.mockResolvedValueOnce(progressResponse([progressItem({flow: 'welcome', status: 'pending', version: 1})]));
        await controller.load(api);

        const {promise, resolve} = deferred<OnboardingProgressItem>();
        api.completeWelcome.mockReturnValue(promise);
        const completePromise = controller.completeWelcome(api, welcomeCompleteRequest());

        setGeneration(2);
        resolve(progressItem({flow: 'welcome', status: 'completed', version: 1}));

        expect(await completePromise).toBeNull();
        expect(controller.findFlow('welcome')?.status).toBe('pending'); // the stale completion must never overwrite the loaded snapshot
    });

    it('surfaces the error message and rethrows on a failed completeWelcome, and clears transitioningFlow', async () => {
        const {controller} = buildController();
        const api = fakeApi();
        api.completeWelcome.mockRejectedValue(new Error('welcome commit failed'));

        await expect(controller.completeWelcome(api, welcomeCompleteRequest())).rejects.toThrow('welcome commit failed');

        expect(controller.error).toBe('welcome commit failed');
        expect(controller.transitioningFlow).toBeNull();
    });

    it('wraps a non-Error rejection into the controller-wide generic message', async () => {
        const {controller} = buildController();
        const api = fakeApi();
        api.completeWelcome.mockRejectedValue('nope');

        await expect(controller.completeWelcome(api, welcomeCompleteRequest())).rejects.toBe('nope');

        expect(controller.error).toBe('Onboarding request failed');
        expect(controller.transitioningFlow).toBeNull();
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

    it('persists and restores the remainingStepIds set for a step-managed replay', () => {
        const {controller} = buildController();
        controller.startReplay('import_guide', 1, 'import.upload', undefined, ['import.upload', 'import.assets', 'import.bulk']);

        expect(controller.updateReplayStep('import.assets')).toBe(true);
        expect(controller.replay).toEqual({
            flow: 'import_guide',
            version: 1,
            stepId: 'import.assets',
            remainingStepIds: ['import.upload', 'import.assets', 'import.bulk'],
            startedAt: 1000,
        });

        expect(controller.resumeReplay('import_guide', 1, IMPORT_GUIDE_STEP_IDS, 'import.upload')).toEqual(controller.replay);
    });

    it('persists replay mode across step updates and a fresh resume', () => {
        const {controller, storage} = buildController();
        const key = replayKey('user-1', 'import_guide', 1);
        const remainingStepIds = ['import.upload', 'import.assets', 'import.bulk'];

        expect(controller.startReplay('import_guide', 1, 'import.upload', undefined, remainingStepIds, 'replay')).toBe(true);
        expect(JSON.parse(storage.getItem(key) ?? '{}')).toEqual({
            flow: 'import_guide',
            version: 1,
            stepId: 'import.upload',
            mode: 'replay',
            remainingStepIds,
            startedAt: 1000,
        });

        expect(controller.updateReplayStep('import.assets')).toBe(true);
        expect(controller.replay).toEqual({
            flow: 'import_guide',
            version: 1,
            stepId: 'import.assets',
            mode: 'replay',
            remainingStepIds,
            startedAt: 1000,
        });

        expect(controller.resumeReplay('import_guide', 1, IMPORT_GUIDE_STEP_IDS, 'import.upload')).toEqual(controller.replay);
        expect(controller.replay?.mode).toBe('replay');
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

/**
 * appBootstrap — sequencing of the three parallel loaders, generation/account
 * guarding, and the welcome-flow redirect logic. Built through its factory
 * (`createAppBootstrap`), never the module singleton, for the same reason the
 * onboarding controller above is: the singleton wires into the real client-session
 * reset registry at import time, a side effect this spec has no business triggering.
 */
describe('appBootstrap — load (no authenticated user)', () => {
    it('idles without calling any loader when there is no authenticated user', async () => {
        const {bootstrap, loadUserSettings, loadOnboarding, loadGlobalSettings, setUserId} = buildBootstrap();
        setUserId(null);

        const result = await bootstrap.load();

        expect(result).toBe('idle');
        expect(bootstrap.state).toBe('idle');
        expect(bootstrap.error).toBeNull();
        expect(bootstrap.loadedUserId).toBeNull();
        expect(loadUserSettings).not.toHaveBeenCalled();
        expect(loadOnboarding).not.toHaveBeenCalled();
        expect(loadGlobalSettings).not.toHaveBeenCalled();
    });
});

describe('appBootstrap — load (success path)', () => {
    it('stays loading until user settings, onboarding and global settings have all settled, then becomes ready', async () => {
        const {bootstrap, loadUserSettings, loadOnboarding, loadGlobalSettings} = buildBootstrap();
        const settings = deferred<boolean>();
        const onboardingLoad = deferred<unknown>();
        const globalSettingsLoad = deferred<unknown>();
        loadUserSettings.mockReturnValue(settings.promise);
        loadOnboarding.mockReturnValue(onboardingLoad.promise);
        loadGlobalSettings.mockReturnValue(globalSettingsLoad.promise);

        const loadPromise = bootstrap.load();
        expect(bootstrap.state).toBe('loading');

        // Resolving two of the three can never be enough: `Promise.allSettled` is
        // blocked on the third, not merely delayed, so this is a deterministic fact
        // about the promise graph rather than a timing race.
        settings.resolve(true);
        globalSettingsLoad.resolve(undefined);
        await Promise.resolve();
        expect(bootstrap.state).toBe('loading');

        onboardingLoad.resolve(undefined);
        const result = await loadPromise;

        expect(result).toBe('ready');
        expect(bootstrap.state).toBe('ready');
        expect(bootstrap.loadedUserId).toBe('user-1');
        expect(loadUserSettings).toHaveBeenCalledTimes(1);
        expect(loadOnboarding).toHaveBeenCalledTimes(1);
        expect(loadGlobalSettings).toHaveBeenCalledTimes(1);
    });
});

describe('appBootstrap — load (cache reuse)', () => {
    it('reuses a ready state for the same user without re-invoking loaders, but force=true reloads', async () => {
        const {bootstrap, loadUserSettings, loadOnboarding, loadGlobalSettings} = buildBootstrap();

        expect(await bootstrap.load()).toBe('ready');
        expect(loadUserSettings).toHaveBeenCalledTimes(1);
        expect(loadOnboarding).toHaveBeenCalledTimes(1);
        expect(loadGlobalSettings).toHaveBeenCalledTimes(1);

        expect(await bootstrap.load()).toBe('ready');
        expect(loadUserSettings).toHaveBeenCalledTimes(1); // still one — the cached ready state was reused
        expect(loadOnboarding).toHaveBeenCalledTimes(1);
        expect(loadGlobalSettings).toHaveBeenCalledTimes(1);

        expect(await bootstrap.load(true)).toBe('ready');
        expect(loadUserSettings).toHaveBeenCalledTimes(2); // force=true bypasses the cache
        expect(loadOnboarding).toHaveBeenCalledTimes(2);
        expect(loadGlobalSettings).toHaveBeenCalledTimes(2);
    });
});

describe('appBootstrap — load (user settings failure)', () => {
    it('blocks with a fixed message when user settings resolve false', async () => {
        const {bootstrap, loadUserSettings} = buildBootstrap();
        loadUserSettings.mockResolvedValue(false);

        expect(await bootstrap.load()).toBe('blocked');
        expect(bootstrap.state).toBe('blocked');
        expect(bootstrap.error).toBe('User settings could not be loaded');
    });

    it('blocks and surfaces the rejection message when user settings load rejects', async () => {
        const {bootstrap, loadUserSettings} = buildBootstrap();
        loadUserSettings.mockRejectedValue(new Error('settings endpoint down'));

        expect(await bootstrap.load()).toBe('blocked');
        expect(bootstrap.error).toBe('settings endpoint down');
    });
});

describe('appBootstrap — load (onboarding failure)', () => {
    it('blocks when onboarding fails and there is no independently valid cached Welcome', async () => {
        const {bootstrap, loadOnboarding, setWelcome} = buildBootstrap();
        setWelcome(null);
        loadOnboarding.mockRejectedValue(new Error('onboarding endpoint down'));

        expect(await bootstrap.load()).toBe('blocked');
        expect(bootstrap.ready).toBe(false);
        expect(bootstrap.error).toBe('onboarding endpoint down');
    });

    it('blocks when onboarding fails and the cached Welcome is still pending', async () => {
        const {bootstrap, loadOnboarding, setWelcome} = buildBootstrap();
        setWelcome(progressItem({flow: 'welcome', status: 'pending'}));
        loadOnboarding.mockRejectedValue(new Error('onboarding endpoint down'));

        expect(await bootstrap.load()).toBe('blocked');
        expect(bootstrap.ready).toBe(false);
        expect(bootstrap.error).toBe('onboarding endpoint down');
    });

    it.each(['completed', 'skipped'] as const)('degrades only when the independently cached Welcome is already %s', async (status) => {
        const {bootstrap, loadOnboarding, setWelcome} = buildBootstrap();
        setWelcome(progressItem({flow: 'welcome', status}));
        loadOnboarding.mockRejectedValue(new Error('onboarding endpoint down'));

        expect(await bootstrap.load()).toBe('degraded');
        expect(bootstrap.state).toBe('degraded');
        expect(bootstrap.error).toBe('onboarding endpoint down');
        expect(bootstrap.ready).toBe(true); // 'degraded' still counts as usable per the `ready` getter contract
    });
});

describe('appBootstrap — load (stale generation/account guarding)', () => {
    it('ignores an outcome that resolves after the account generation moved on, leaving state at loading', async () => {
        const {bootstrap, loadUserSettings, setGeneration} = buildBootstrap({generation: 1});
        const settings = deferred<boolean>();
        loadUserSettings.mockReturnValue(settings.promise);

        const loadPromise = bootstrap.load();
        setGeneration(2);
        settings.resolve(true);

        expect(await loadPromise).toBe('loading'); // never advanced for the stale ticket
        expect(bootstrap.state).toBe('loading');
    });

    it('ignores an outcome that resolves after the user id changed, leaving state at loading', async () => {
        const {bootstrap, loadUserSettings, setUserId} = buildBootstrap({userId: 'user-1'});
        const settings = deferred<boolean>();
        loadUserSettings.mockReturnValue(settings.promise);

        const loadPromise = bootstrap.load();
        setUserId('user-2');
        settings.resolve(true);

        expect(await loadPromise).toBe('loading');
        expect(bootstrap.state).toBe('loading');
    });
});

describe('appBootstrap — resolveDestination (pending welcome flow)', () => {
    it('redirects an internal deep link to /welcome?returnTo=... when the welcome flow is pending', () => {
        const {bootstrap, setWelcome} = buildBootstrap();
        setWelcome(progressItem({flow: 'welcome', status: 'pending', current_version: 1}));

        expect(bootstrap.resolveDestination('/dashboard')).toBe('/welcome?returnTo=%2Fdashboard');
    });

    it('leaves an already-/welcome destination untouched while pending', () => {
        const {bootstrap, setWelcome} = buildBootstrap();
        setWelcome(progressItem({flow: 'welcome', status: 'pending', current_version: 1}));

        expect(bootstrap.resolveDestination('/welcome?step=intro')).toBe('/welcome?step=intro');
    });

    it('does not treat /welcome-extra as the welcome route while pending: it is wrapped into a returnTo, not left untouched', () => {
        const {bootstrap, setWelcome} = buildBootstrap();
        setWelcome(progressItem({flow: 'welcome', status: 'pending', current_version: 1}));

        expect(bootstrap.resolveDestination('/welcome-extra')).toBe('/welcome?returnTo=%2Fwelcome-extra');
    });
});

describe('appBootstrap — resolveDestination (terminal welcome flow + replay)', () => {
    it.each(['completed', 'skipped'] as const)('never forces welcome for a %s flow when no replay is armed', (status) => {
        const {bootstrap, setWelcome} = buildBootstrap();
        setWelcome(progressItem({flow: 'welcome', status}));

        expect(bootstrap.resolveDestination('/dashboard')).toBe('/dashboard');
    });

    it('forces welcome even from a terminal (completed) state when a valid replay exists for the current version', () => {
        const {bootstrap, setWelcome, setReplayVersion} = buildBootstrap();
        setWelcome(progressItem({flow: 'welcome', status: 'completed', current_version: 4}));
        setReplayVersion(4, true);

        expect(bootstrap.resolveDestination('/dashboard')).toBe('/welcome?returnTo=%2Fdashboard');
    });

    it('restores a safe internal returnTo path once the welcome flow is terminal and not being replayed', () => {
        const {bootstrap, setWelcome} = buildBootstrap();
        setWelcome(progressItem({flow: 'welcome', status: 'completed', current_version: 1}));

        expect(bootstrap.resolveDestination('/welcome?returnTo=%2Fportfolio')).toBe('/portfolio');
    });

    it('falls back to /dashboard when returnTo is an off-site (protocol-relative) //evil path', () => {
        const {bootstrap, setWelcome} = buildBootstrap();
        setWelcome(progressItem({flow: 'welcome', status: 'completed', current_version: 1}));

        expect(bootstrap.resolveDestination('/welcome?returnTo=%2F%2Fevil.example.com')).toBe('/dashboard');
    });

    it('falls back to /dashboard when returnTo contains a backslash (browser-normalized off-site path)', () => {
        const {bootstrap, setWelcome} = buildBootstrap();
        setWelcome(progressItem({flow: 'welcome', status: 'completed', current_version: 1}));

        expect(bootstrap.resolveDestination('/welcome?returnTo=%2F%5Cevil.example.com')).toBe('/dashboard');
    });

    it('falls back to /dashboard when returnTo is missing entirely', () => {
        const {bootstrap, setWelcome} = buildBootstrap();
        setWelcome(progressItem({flow: 'welcome', status: 'skipped', current_version: 1}));

        expect(bootstrap.resolveDestination('/welcome')).toBe('/dashboard');
    });

    it('does not unwrap /welcome-extra as the welcome route from a terminal state: it is returned as-is, not treated as a returnTo wrapper', () => {
        const {bootstrap, setWelcome} = buildBootstrap();
        setWelcome(progressItem({flow: 'welcome', status: 'completed', current_version: 1}));

        expect(bootstrap.resolveDestination('/welcome-extra')).toBe('/welcome-extra');
    });
});

describe('onboarding controller — hasReplay (non-destructive replay probe)', () => {
    it('reports false and leaves the in-memory replay untouched when nothing is stored for that flow/version', () => {
        const {controller} = buildController();

        expect(controller.hasReplay('welcome', 1)).toBe(false);
        expect(controller.replay).toBeNull();
    });

    it('reports true for a matching, valid stored replay without mutating the in-memory replay state', () => {
        const {controller, storage} = buildController({userId: 'user-1'});
        // Written directly to storage, bypassing startReplay, to prove hasReplay reads
        // storage rather than the in-memory `replay` field.
        storage.setItem('lf_user-1_onboarding_replay_welcome_v2', JSON.stringify({flow: 'welcome', version: 2, stepId: 'step-a', startedAt: 1000}));

        expect(controller.hasReplay('welcome', 2)).toBe(true);
        expect(controller.replay).toBeNull(); // a probe must never promote what it read into the active replay
    });

    it('does not overwrite or clear an active replay belonging to a different flow', () => {
        const {controller, storage} = buildController({userId: 'user-1'});
        controller.startReplay('intro_tour', 1, 'step-1');
        const introKey = 'lf_user-1_onboarding_replay_intro_tour_v1';
        expect(storage.getItem(introKey)).not.toBeNull();

        const result = controller.hasReplay('welcome', 5);

        expect(result).toBe(false); // nothing stored for welcome v5
        expect(controller.replay).toEqual({flow: 'intro_tour', version: 1, stepId: 'step-1', startedAt: 1000}); // untouched
        expect(storage.getItem(introKey)).not.toBeNull(); // untouched
    });

    it('removes an invalid stored welcome replay payload instead of reporting it as present', () => {
        const {controller, storage} = buildController({userId: 'user-1'});
        const key = 'lf_user-1_onboarding_replay_welcome_v3';
        storage.setItem(key, JSON.stringify({flow: 'welcome', version: 3})); // missing stepId/startedAt

        expect(controller.hasReplay('welcome', 3)).toBe(false);
        expect(storage.getItem(key)).toBeNull();
    });

    it('reports false without throwing when the stored payload is unparsable JSON', () => {
        const {controller, storage} = buildController({userId: 'user-1'});
        const key = 'lf_user-1_onboarding_replay_welcome_v3';
        storage.setItem(key, '{not json');

        expect(controller.hasReplay('welcome', 3)).toBe(false);
        expect(controller.replayStorageError).toBeTruthy();
    });
});

/**
 * onboardingGuide — the UI-facing semantic-step layer built on top of the
 * controller above.
 *
 * Same discipline as `buildController`: a *real* `createOnboardingController`
 * (factory, memory storage, test-owned identity/clock), a fully fake
 * `OnboardingApi`, and an injected `navigate` spy standing in for `$app/navigation`'s
 * `goto`. The guide's own module-level singleton (`onboardingGuide`, exported at
 * the bottom of `onboardingGuide.svelte.ts`) is never touched — only its factory.
 */
async function buildGuide(options: {flows?: OnboardingProgressItem[]; controllerInit?: Parameters<typeof buildController>[0]} = {}) {
    const {controller, storage, setUserId, setGeneration} = buildController(options.controllerInit);
    const api = fakeApi();
    api.getProgress.mockResolvedValue(progressResponse(options.flows ?? [progressItem({flow: 'intro_tour'}), progressItem({flow: 'import_guide'})]));
    await controller.load(api);
    const navigate = vi.fn<typeof goto>().mockResolvedValue(undefined);
    const guide = createOnboardingGuide({controller, api, navigate});
    return {guide, controller, storage, api, navigate, setUserId, setGeneration};
}

/** Mirrors the controller's private `replayKey` so a test can read/evict storage directly. */
function replayKey(userId: string, flow: string, version: number): string {
    return `lf_${userId}_onboarding_replay_${flow}_v${version}`;
}

const EXPECTED_INTRO_TOUR_STEP_IDS = ['intro.scene', 'intro.navigation', 'intro.dashboard', 'intro.transactions_nav', 'intro.brokers_nav', 'intro.fx_nav', 'intro.assets_nav', 'intro.tools_nav', 'intro.settings_nav'] as const;

function progressForFlows(flows: readonly OnboardingFlow[], status: OnboardingProgressItem['status'] = 'pending'): OnboardingProgressItem[] {
    return flows.map((flow) => progressItem({flow, status}));
}

describe('onboardingGuide — stored token terminal guards', () => {
    it.each(['completed', 'skipped'] as const)('ignores and clears a stored automatic Intro token once the non-step flow is %s', async (status) => {
        const {guide, controller, storage, api} = await buildGuide({
            flows: [progressItem({flow: 'intro_tour', status})],
        });
        const key = replayKey('user-1', 'intro_tour', 1);
        storage.setItem(
            key,
            JSON.stringify({
                flow: 'intro_tour',
                version: 1,
                stepId: 'intro.navigation',
                startedAt: 900,
                mode: 'automatic',
            }),
        );

        expect(guide.maybeStartIntro()).toBe(false);

        expect(guide.active).toBeNull();
        expect(controller.replay).toBeNull();
        expect(storage.getItem(key)).toBeNull();
        expect(api.completeFlow).not.toHaveBeenCalled();
        expect(api.skipFlow).not.toHaveBeenCalled();
    });

    it('clears a stored automatic Import token instead of reactivating its now-terminal step', async () => {
        const terminalStepId = 'import.assets';
        const importFlow = progressItem({
            flow: 'import_guide',
            status: 'pending',
            steps: IMPORT_GUIDE_STEP_IDS.map((stepId) =>
                stepProgressItem(stepId, {
                    status: stepId === terminalStepId ? 'completed' : 'pending',
                    completed_at: stepId === terminalStepId ? '2026-01-02T00:00:00Z' : null,
                }),
            ),
        });
        const {guide, controller, storage, api} = await buildGuide({flows: [importFlow]});
        const key = replayKey('user-1', 'import_guide', 1);
        storage.setItem(
            key,
            JSON.stringify({
                flow: 'import_guide',
                version: 1,
                stepId: terminalStepId,
                startedAt: 900,
                mode: 'automatic',
                remainingStepIds: [terminalStepId],
            }),
        );

        expect(guide.startImportAt(terminalStepId)).toBe(false);

        expect(guide.active).toBeNull();
        expect(controller.replay).toBeNull();
        expect(storage.getItem(key)).toBeNull();
        expect(controller.findStep('import_guide', terminalStepId)?.status).toBe('completed');
        expect(api.completeStep).not.toHaveBeenCalled();
        expect(api.skipStep).not.toHaveBeenCalled();
    });

    it('lets explicit replay reactivate only terminal Import IDs that remain in remainingStepIds', async () => {
        const {guide, controller, storage, api} = await buildGuide({
            flows: [progressItem({flow: 'import_guide', status: 'completed'})],
        });
        const key = replayKey('user-1', 'import_guide', 1);
        const replayToken = {
            flow: 'import_guide',
            version: 1,
            stepId: 'import.assets',
            startedAt: 900,
            mode: 'replay' as const,
            remainingStepIds: ['import.assets'],
        };
        storage.setItem(key, JSON.stringify(replayToken));

        expect(guide.startImportAt('import.review')).toBe(false);
        expect(guide.active).toBeNull();
        expect(storage.getItem(key)).toBe(JSON.stringify(replayToken));

        expect(guide.startImportAt('import.assets')).toBe(true);
        expect(guide.active).toEqual({
            flow: 'import_guide',
            version: 1,
            stepId: 'import.assets',
            mode: 'replay',
        });
        expect(controller.replay).toMatchObject({
            flow: 'import_guide',
            stepId: 'import.assets',
            mode: 'replay',
            remainingStepIds: ['import.assets'],
        });
        expect(api.completeStep).not.toHaveBeenCalled();
        expect(api.skipStep).not.toHaveBeenCalled();
    });
});

describe('onboardingGuide — intro tour auto-start', () => {
    it('auto-starts a pending intro at the scene exactly once, persists the replay, and preserves a safe returnTo', async () => {
        const {guide, storage} = await buildGuide();
        const key = replayKey('user-1', 'intro_tour', 1);

        const started = guide.maybeStartIntro('/transactions/42');

        expect(started).toBe(true);
        expect(guide.active).toEqual({flow: 'intro_tour', version: 1, stepId: 'intro.scene', mode: 'automatic', returnTo: '/transactions/42'});
        expect(storage.getItem(key)).toEqual(JSON.stringify({flow: 'intro_tour', version: 1, stepId: 'intro.scene', startedAt: 1000, mode: 'automatic', returnTo: '/transactions/42'}));

        // Idempotent while still active: a second mount/re-render calling
        // maybeStartIntro must not re-activate, must not rewrite the replay, and
        // must ignore the (different) returnTo it was called with this time.
        const setItemSpy = vi.spyOn(storage, 'setItem');
        expect(guide.maybeStartIntro('/somewhere-else')).toBe(true);
        expect(guide.active?.returnTo).toBe('/transactions/42');
        expect(setItemSpy).not.toHaveBeenCalled();

        // Suspending clears `active` and leaves the persisted replay in storage, but
        // the suspension lasts for the current runtime: this same guide instance must
        // not resume it. (A fresh instance resuming the stored token across a
        // refresh is covered by the dedicated regression test below.)
        guide.suspend();
        expect(guide.active).toBeNull();
        expect(guide.maybeStartIntro()).toBe(false);
        expect(guide.active).toBeNull();
        expect(storage.getItem(key)).not.toBeNull();

        // Once the stored replay itself is gone (e.g. storage eviction) while the
        // flow is still pending, the once-per-instance guard - not the stored
        // replay - is what stops a fresh automatic start.
        guide.suspend();
        storage.removeItem(key);
        expect(guide.maybeStartIntro()).toBe(false);
        expect(guide.active).toBeNull();
    });

    it('does not resume a suspended replay within the same runtime, but a fresh guide instance resumes its preserved step', async () => {
        const {guide: guide1, controller, api, storage} = await buildGuide();
        const key = replayKey('user-1', 'intro_tour', 1);

        expect(guide1.maybeStartIntro('/transactions/42')).toBe(true);
        guide1.nextIntro();
        expect(guide1.active?.stepId).toBe('intro.navigation');

        // Suspending clears `active`, but the replay token is still in storage.
        guide1.suspend();
        expect(guide1.active).toBeNull();
        expect(storage.getItem(key)).not.toBeNull();

        // Regression: the layout's next reactive call used to resume the
        // just-suspended replay immediately because `maybeStartIntro` read the
        // stored replay before checking this instance's `introAttempted`
        // guard. It must now refuse, leaving `active` null, in the very same
        // guide instance that just suspended.
        expect(guide1.maybeStartIntro()).toBe(false);
        expect(guide1.active).toBeNull();
        expect(storage.getItem(key)).not.toBeNull();

        // A fresh guide instance — standing in for a page refresh/new runtime
        // over the same controller and storage — has its own `introAttempted`
        // guard and legitimately resumes the still-pending, still-stored replay.
        const guide2 = createOnboardingGuide({controller, api, navigate: vi.fn<typeof goto>().mockResolvedValue(undefined)});
        expect(guide2.maybeStartIntro()).toBe(true);
        expect(guide2.active).toMatchObject({stepId: 'intro.navigation', mode: 'automatic', returnTo: '/transactions/42'});

        expect(api.completeFlow).not.toHaveBeenCalled();
        expect(api.skipFlow).not.toHaveBeenCalled();
    });

    it('prepareIntroReplay() after a suspended intro resets the per-runtime guard and arms the scene without activating it', async () => {
        const {guide, controller, api} = await buildGuide();

        // Same-runtime suspension guard, as in the test above: once suspended, this
        // guide instance refuses to resume on its own.
        expect(guide.maybeStartIntro('/transactions/42')).toBe(true);
        guide.suspend();
        expect(guide.active).toBeNull();
        expect(guide.maybeStartIntro()).toBe(false);

        // prepareIntroReplay only arms a fresh replay token and clears the
        // guard — it must not itself activate the tour.
        expect(guide.prepareIntroReplay()).toBe(true);
        expect(guide.active).toBeNull();
        expect(controller.replay?.stepId).toBe('intro.scene');

        // The guard being clear lets the next maybeStartIntro() pick the
        // just-armed token back up, starting over at the first intro step.
        expect(guide.maybeStartIntro()).toBe(true);
        expect(guide.active).toMatchObject({flow: 'intro_tour', stepId: INTRO_TOUR_STEP_IDS[0], mode: 'replay'});

        expect(api.completeFlow).not.toHaveBeenCalled();
        expect(api.skipFlow).not.toHaveBeenCalled();
    });

    it('discards an unsafe returnTo at activation time instead of storing it', async () => {
        const {guide} = await buildGuide();

        guide.maybeStartIntro('//evil.example.com');

        expect(guide.active?.returnTo).toBeUndefined();
    });

    it.each(['completed', 'skipped'] as const)('does not auto-start a %s intro tour when nothing is stored for it', async (status) => {
        const {guide} = await buildGuide({flows: [progressItem({flow: 'intro_tour', status})]});

        expect(guide.maybeStartIntro()).toBe(false);
        expect(guide.active).toBeNull();
    });

    it.each(['completed', 'skipped'] as const)('an explicit replay starts the intro tour even from a terminal (%s) status', async (status) => {
        const {guide} = await buildGuide({flows: [progressItem({flow: 'intro_tour', status})]});

        const started = guide.startIntroReplay('/dashboard');

        expect(started).toBe(true);
        expect(guide.active).toMatchObject({flow: 'intro_tour', stepId: 'intro.scene', mode: 'replay', returnTo: '/dashboard'});
    });
});

describe('onboardingGuide — intro tour navigation (next/back)', () => {
    it('publishes the approved Core sequence', () => {
        expect(INTRO_TOUR_STEP_IDS).toEqual(EXPECTED_INTRO_TOUR_STEP_IDS);
    });

    it('starts in the scene and advances to navigation only when the scene starts', async () => {
        const {guide, controller, api} = await buildGuide();

        expect(guide.maybeStartIntro()).toBe(true);
        expect(guide.active?.stepId).toBe('intro.scene');
        expect(controller.replay?.stepId).toBe('intro.scene');

        guide.nextIntro();

        expect(guide.active?.stepId).toBe('intro.navigation');
        expect(controller.replay?.stepId).toBe('intro.navigation');
        expect(api.completeFlow).not.toHaveBeenCalled();
        expect(api.skipFlow).not.toHaveBeenCalled();
    });

    it('walks the exact semantic step order forward and back, persisting each step', async () => {
        const {guide, controller} = await buildGuide();
        guide.maybeStartIntro();

        const visitedForward: string[] = [guide.active!.stepId];
        for (let i = 1; i < INTRO_TOUR_STEP_IDS.length; i += 1) {
            guide.nextIntro();
            visitedForward.push(guide.active!.stepId);
            expect(controller.replay?.stepId).toBe(guide.active!.stepId);
        }
        expect(visitedForward).toEqual([...INTRO_TOUR_STEP_IDS]);
        expect(visitedForward).toContain('intro.tools_nav');

        // Clamped at the last step: one call past the end is a no-op.
        guide.nextIntro();
        expect(guide.active?.stepId).toBe(INTRO_TOUR_STEP_IDS.at(-1));

        const visitedBack: string[] = [guide.active!.stepId];
        for (let i = INTRO_TOUR_STEP_IDS.length - 2; i >= 0; i -= 1) {
            guide.previousIntro();
            visitedBack.push(guide.active!.stepId);
            expect(controller.replay?.stepId).toBe(guide.active!.stepId);
        }
        expect(visitedBack).toEqual([...INTRO_TOUR_STEP_IDS].reverse());

        // Clamped at the first step: one call past the start is a no-op.
        guide.previousIntro();
        expect(guide.active?.stepId).toBe(INTRO_TOUR_STEP_IDS[0]);
    });
});

describe('onboardingGuide — flow precedence', () => {
    it('an active intro tour is never preempted by an import-guide start request', async () => {
        const {guide} = await buildGuide();
        guide.maybeStartIntro();
        expect(guide.active?.flow).toBe('intro_tour');

        const started = guide.startImportAt('import.analyze');

        expect(started).toBe(false);
        expect(guide.active).toMatchObject({flow: 'intro_tour', stepId: 'intro.scene'});
    });
});

describe('onboardingGuide — contextual FIFO and account reset', () => {
    it('keeps FIFO entries distinct by (flow, step) and deduplicates only an exact pair', async () => {
        const otherFlow: ContextualOnboardingFlow = 'transactions_page_guide';
        const {guide} = await buildGuide({flows: progressForFlows([otherFlow, 'transaction_bulk_guide'])});

        expect(guide.maybeStartContextual(otherFlow)).toBe(true);
        guide.queueContextual('transaction_bulk_guide', 'transaction.bulk.workspace');
        guide.queueContextual('transaction_bulk_guide', 'transaction.bulk.validation');
        guide.queueContextual('transaction_bulk_guide', 'transaction.bulk.workspace');

        expect(guide.queuedGuides).toEqual([
            {flow: 'transaction_bulk_guide', stepId: 'transaction.bulk.workspace'},
            {flow: 'transaction_bulk_guide', stepId: 'transaction.bulk.validation'},
        ]);
        expect(guide.queuedFlows).toEqual(['transaction_bulk_guide', 'transaction_bulk_guide']);

        guide.dismissHost();
        expect(guide.maybeStartQueued('transaction_bulk_guide', 'transaction.bulk.validation')).toBe(true);
        expect(guide.active).toMatchObject({
            flow: 'transaction_bulk_guide',
            stepId: 'transaction.bulk.validation',
        });
        expect(guide.queuedGuides).toEqual([{flow: 'transaction_bulk_guide', stepId: 'transaction.bulk.workspace'}]);
    });

    it('clears one stale Bulk step without disturbing its sibling step or another flow', async () => {
        const otherFlow: ContextualOnboardingFlow = 'transactions_page_guide';
        const {guide} = await buildGuide({flows: progressForFlows(['transaction_bulk_guide', otherFlow])});

        guide.queueContextual('transaction_bulk_guide', 'transaction.bulk.workspace');
        guide.queueContextual('transaction_bulk_guide', 'transaction.bulk.validation');
        guide.queueContextual(otherFlow);
        guide.clearQueued('transaction_bulk_guide', 'transaction.bulk.workspace');

        expect(guide.queuedGuides).toEqual([{flow: 'transaction_bulk_guide', stepId: 'transaction.bulk.validation'}, {flow: otherFlow}]);

        guide.clearQueued('transaction_bulk_guide');
        expect(guide.queuedGuides).toEqual([{flow: otherFlow}]);
    });

    it('drops active and queued contextual state at an account reset boundary', async () => {
        const {guide, controller, setUserId} = await buildGuide({flows: progressForFlows(['transaction_bulk_guide'])});
        expect(guide.maybeStartContextual('transaction_bulk_guide', 'transaction.bulk.workspace')).toBe(true);
        guide.queueContextual('transaction_bulk_guide', 'transaction.bulk.validation');
        expect(guide.queuedGuides).toEqual([{flow: 'transaction_bulk_guide', stepId: 'transaction.bulk.validation'}]);

        setUserId('user-2');
        guide.reset();
        controller.reset();

        expect(guide.active).toBeNull();
        expect(guide.queuedFlow).toBeNull();
        expect(guide.queuedFlows).toEqual([]);
        expect(guide.maybeStartQueued()).toBe(false);
        expect(controller.replay).toBeNull();
    });
});

describe('onboardingGuide — final flow and step-managed Bulk contract', () => {
    it('exports exactly the approved 15-flow runtime contract without draft Bulk ids', () => {
        expect(ONBOARDING_FLOWS).toEqual([
            'welcome',
            'intro_tour',
            'transactions_page_guide',
            'transaction_create_guide',
            'transaction_bulk_guide',
            'import_guide',
            'broker_page_guide',
            'broker_guide',
            'broker_detail_guide',
            'fx_page_guide',
            'fx_guide',
            'fx_detail_guide',
            'asset_page_guide',
            'asset_guide',
            'asset_detail_guide',
        ]);
        expect(ONBOARDING_FLOWS).not.toContain('transaction_bulk_validation_guide');
        expect(ONBOARDING_FLOWS).not.toContain('transaction_bulk_selection_guide');
        expect(ONBOARDING_FLOWS).not.toContain('transaction_bulk_save_guide');
    });

    it('registers one checkpoint-mode Bulk flow with four ordered persisted steps while Import stays sequential', () => {
        expect(guideSteps('transaction_bulk_guide')).toEqual(TRANSACTION_BULK_STEP_IDS);
        expect(TRANSACTION_BULK_STEP_IDS).toEqual(['transaction.bulk.workspace', 'transaction.bulk.validation', 'transaction.bulk.selection', 'transaction.bulk.save']);
        expect(isStepManagedFlow('transaction_bulk_guide')).toBe(true);
        expect(isStepManagedFlow('import_guide')).toBe(true);
        expect(isStepManagedFlow('transactions_page_guide')).toBe(false);
        expect(isCheckpointFlow('transaction_bulk_guide')).toBe(true);
        expect(isCheckpointFlow('import_guide')).toBe(false);
    });

    it('Finish completes only the current Bulk step and preserves pending siblings', async () => {
        const initial = progressItem({flow: 'transaction_bulk_guide'});
        const {guide, controller, api} = await buildGuide({flows: [initial]});
        const updated = progressItem({
            flow: 'transaction_bulk_guide',
            status: 'pending',
            steps: initial.steps?.map((step) => (step.step_id === 'transaction.bulk.workspace' ? stepProgressItem(step.step_id, {status: 'completed', completed_at: '2026-01-02T00:00:00Z'}) : step)),
        });
        api.completeStep.mockResolvedValue(updated);

        expect(guide.maybeStartContextual('transaction_bulk_guide', 'transaction.bulk.workspace')).toBe(true);
        await guide.finish();

        expect(api.completeStep).toHaveBeenCalledExactlyOnceWith('transaction_bulk_guide', 'transaction.bulk.workspace', {
            expected_version: 1,
        });
        expect(api.completeFlow).not.toHaveBeenCalled();
        expect(api.skipFlow).not.toHaveBeenCalled();
        expect(controller.findFlow('transaction_bulk_guide')?.status).toBe('pending');
        expect(controller.findStep('transaction_bulk_guide', 'transaction.bulk.workspace')?.status).toBe('completed');
        expect(controller.findStep('transaction_bulk_guide', 'transaction.bulk.validation')?.status).toBe('pending');
    });

    it('X skips only the current Bulk step and leaves the aggregate pending', async () => {
        const initial = progressItem({flow: 'transaction_bulk_guide'});
        const {guide, controller, api} = await buildGuide({flows: [initial]});
        const updated = progressItem({
            flow: 'transaction_bulk_guide',
            status: 'pending',
            steps: initial.steps?.map((step) => (step.step_id === 'transaction.bulk.validation' ? stepProgressItem(step.step_id, {status: 'skipped', skipped_at: '2026-01-02T00:00:00Z'}) : step)),
        });
        api.skipStep.mockResolvedValue(updated);

        expect(guide.maybeStartContextual('transaction_bulk_guide', 'transaction.bulk.validation')).toBe(true);
        expect(await guide.exit()).toBe(true);

        expect(api.skipStep).toHaveBeenCalledExactlyOnceWith('transaction_bulk_guide', 'transaction.bulk.validation', {
            expected_version: 1,
        });
        expect(api.skipFlow).not.toHaveBeenCalled();
        expect(api.completeFlow).not.toHaveBeenCalled();
        expect(controller.findFlow('transaction_bulk_guide')?.status).toBe('pending');
        expect(controller.findStep('transaction_bulk_guide', 'transaction.bulk.validation')?.status).toBe('skipped');
        expect(controller.findStep('transaction_bulk_guide', 'transaction.bulk.selection')?.status).toBe('pending');
    });

    it('replay tracks remainingStepIds and consumes only the current step locally', async () => {
        const {guide, controller, api} = await buildGuide({flows: [progressItem({flow: 'transaction_bulk_guide', status: 'completed'})]});

        expect(guide.armReplay('transaction_bulk_guide')).toBe(true);
        expect(controller.replay?.remainingStepIds).toEqual(TRANSACTION_BULK_STEP_IDS);
        expect(guide.maybeStartContextual('transaction_bulk_guide', 'transaction.bulk.workspace')).toBe(true);
        expect(guide.active).toMatchObject({
            flow: 'transaction_bulk_guide',
            stepId: 'transaction.bulk.workspace',
            mode: 'replay',
        });
        await guide.finish();
        expect(controller.replay).toMatchObject({
            flow: 'transaction_bulk_guide',
            stepId: 'transaction.bulk.validation',
            remainingStepIds: ['transaction.bulk.validation', 'transaction.bulk.selection', 'transaction.bulk.save'],
        });
        expect(guide.maybeStartContextual('transaction_bulk_guide', 'transaction.bulk.validation')).toBe(true);
        expect(guide.active).toMatchObject({stepId: 'transaction.bulk.validation', mode: 'replay'});
        expect(api.completeFlow).not.toHaveBeenCalled();
        expect(api.skipFlow).not.toHaveBeenCalled();
        expect(api.completeStep).not.toHaveBeenCalled();
        expect(api.skipStep).not.toHaveBeenCalled();
    });

    it('keeps an armed pending Bulk flow in replay mode, consumes only the current replay step, and later replays completed steps without backend writes', async () => {
        const bulk = progressItem({
            flow: 'transaction_bulk_guide',
            status: 'pending',
            steps: TRANSACTION_BULK_STEP_IDS.map((stepId) =>
                stepProgressItem(stepId, {
                    status: stepId === 'transaction.bulk.workspace' || stepId === 'transaction.bulk.selection' ? 'completed' : 'pending',
                    completed_at: stepId === 'transaction.bulk.workspace' || stepId === 'transaction.bulk.selection' ? '2026-01-02T00:00:00Z' : null,
                }),
            ),
        });
        const {guide, controller, api, storage} = await buildGuide({flows: [bulk]});

        expect(guide.armReplay('transaction_bulk_guide')).toBe(true);
        expect(controller.replay).toMatchObject({
            flow: 'transaction_bulk_guide',
            stepId: 'transaction.bulk.workspace',
            mode: 'replay',
            remainingStepIds: TRANSACTION_BULK_STEP_IDS,
        });
        expect(JSON.parse(storage.getItem(replayKey('user-1', 'transaction_bulk_guide', 1)) ?? '{}').mode).toBe('replay');

        expect(guide.maybeStartContextual('transaction_bulk_guide', 'transaction.bulk.workspace')).toBe(true);
        expect(guide.active).toMatchObject({
            flow: 'transaction_bulk_guide',
            stepId: 'transaction.bulk.workspace',
            mode: 'replay',
        });
        await guide.finish();
        expect(controller.replay).toMatchObject({
            stepId: 'transaction.bulk.validation',
            mode: 'replay',
            remainingStepIds: ['transaction.bulk.validation', 'transaction.bulk.selection', 'transaction.bulk.save'],
        });

        // Selection was already completed in persisted progress, but an explicit
        // replay must still be able to visit it. Consuming it out of order must
        // leave the other two replay steps armed.
        expect(guide.maybeStartContextual('transaction_bulk_guide', 'transaction.bulk.selection')).toBe(true);
        expect(guide.active).toMatchObject({
            stepId: 'transaction.bulk.selection',
            mode: 'replay',
        });
        await guide.finish();
        expect(controller.replay).toMatchObject({
            stepId: 'transaction.bulk.validation',
            mode: 'replay',
            remainingStepIds: ['transaction.bulk.validation', 'transaction.bulk.save'],
        });

        expect(controller.findStep('transaction_bulk_guide', 'transaction.bulk.workspace')?.status).toBe('completed');
        expect(controller.findStep('transaction_bulk_guide', 'transaction.bulk.selection')?.status).toBe('completed');
        expect(api.completeFlow).not.toHaveBeenCalled();
        expect(api.skipFlow).not.toHaveBeenCalled();
        expect(api.completeStep).not.toHaveBeenCalled();
        expect(api.skipStep).not.toHaveBeenCalled();
    });

    it('does not re-arm a consumed pending Bulk replay step when its workspace is dismissed and reopened', async () => {
        const {guide, controller, api} = await buildGuide({
            flows: [progressItem({flow: 'transaction_bulk_guide', status: 'pending'})],
        });
        const remainingAfterWorkspace = ['transaction.bulk.validation', 'transaction.bulk.selection', 'transaction.bulk.save'] as const;

        expect(guide.armReplay('transaction_bulk_guide')).toBe(true);
        expect(guide.maybeStartContextual('transaction_bulk_guide', 'transaction.bulk.workspace')).toBe(true);
        expect(guide.active).toEqual({
            flow: 'transaction_bulk_guide',
            version: 1,
            stepId: 'transaction.bulk.workspace',
            mode: 'replay',
        });

        await guide.finish();

        expect(guide.active).toBeNull();
        expect(controller.replay).toEqual({
            flow: 'transaction_bulk_guide',
            version: 1,
            stepId: 'transaction.bulk.validation',
            startedAt: 1000,
            mode: 'replay',
            remainingStepIds: remainingAfterWorkspace,
        });

        // The modal host can dismiss after the local acknowledgement and then
        // publish its workspace checkpoint again when reopened. Membership in
        // the explicit replay queue, not the still-pending backend row, decides
        // whether that checkpoint may restart.
        guide.dismissHost();
        expect(guide.maybeStartContextual('transaction_bulk_guide', 'transaction.bulk.workspace')).toBe(false);
        expect(guide.active).toBeNull();
        expect(controller.replay).toEqual({
            flow: 'transaction_bulk_guide',
            version: 1,
            stepId: 'transaction.bulk.validation',
            startedAt: 1000,
            mode: 'replay',
            remainingStepIds: remainingAfterWorkspace,
        });

        expect(guide.maybeStartContextual('transaction_bulk_guide', 'transaction.bulk.validation')).toBe(true);
        await guide.finish();
        expect(guide.maybeStartContextual('transaction_bulk_guide', 'transaction.bulk.selection')).toBe(true);
        await guide.finish();
        expect(guide.maybeStartContextual('transaction_bulk_guide', 'transaction.bulk.save')).toBe(true);
        await guide.finish();

        expect(controller.replay).toBeNull();
        expect(controller.findStep('transaction_bulk_guide', 'transaction.bulk.workspace')?.status).toBe('pending');

        // Once the explicit replay is exhausted, the untouched pending row is
        // again eligible under normal automatic semantics on a later trigger.
        expect(guide.maybeStartContextual('transaction_bulk_guide', 'transaction.bulk.workspace')).toBe(true);
        expect(guide.active).toEqual({
            flow: 'transaction_bulk_guide',
            version: 1,
            stepId: 'transaction.bulk.workspace',
            mode: 'automatic',
        });
        expect(controller.replay).toEqual({
            flow: 'transaction_bulk_guide',
            version: 1,
            stepId: 'transaction.bulk.workspace',
            startedAt: 1000,
            mode: 'automatic',
            remainingStepIds: ['transaction.bulk.workspace'],
        });

        expect(api.completeFlow).not.toHaveBeenCalled();
        expect(api.skipFlow).not.toHaveBeenCalled();
        expect(api.completeStep).not.toHaveBeenCalled();
        expect(api.skipStep).not.toHaveBeenCalled();
    });
});

describe('onboardingGuide — import guide start / suspend', () => {
    it('a pending import guide starts at whatever semantic step the caller asks for, not forced to the first', async () => {
        const {guide, controller} = await buildGuide({flows: [progressItem({flow: 'import_guide', status: 'pending'})]});

        const started = guide.startImportAt('import.analyze');

        expect(started).toBe(true);
        expect(guide.active).toMatchObject({flow: 'import_guide', stepId: 'import.analyze', mode: 'automatic'});
        expect(controller.replay?.stepId).toBe('import.analyze');
    });

    it('a terminal import guide with an existing stored replay resumes at the actual step passed in, not the first', async () => {
        const {guide, controller} = await buildGuide({flows: [progressItem({flow: 'import_guide', status: 'completed', version: 1, current_version: 1})]});
        // Simulates a replay left over from an earlier session, written directly
        // through the controller rather than through the guide.
        controller.startReplay('import_guide', 1, 'import.duplicates', undefined, ['import.duplicates'], 'replay');

        const started = guide.startImportAt('import.duplicates');

        expect(started).toBe(true);
        expect(guide.active).toMatchObject({flow: 'import_guide', stepId: 'import.duplicates', mode: 'replay'});
    });

    it('a terminal import guide without any stored replay refuses to start', async () => {
        const {guide} = await buildGuide({flows: [progressItem({flow: 'import_guide', status: 'completed'})]});

        expect(guide.startImportAt('import.analyze')).toBe(false);
        expect(guide.active).toBeNull();
    });

    it('an optional step omitted on the first encounter remains due and starts when a later import exposes it', async () => {
        const firstEncounter = progressItem({
            flow: 'import_guide',
            status: 'pending',
            steps: IMPORT_GUIDE_STEP_IDS.map((stepId) =>
                stepProgressItem(stepId, {
                    status: stepId === 'import.assets' ? 'pending' : 'completed',
                    completed_at: stepId === 'import.assets' ? null : '2026-01-02T00:00:00Z',
                }),
            ),
        });
        const {guide} = await buildGuide({flows: [firstEncounter]});

        expect(guide.startImportAt('import.review')).toBe(false);
        expect(guide.active).toBeNull();
        expect(guide.startImportAt('import.assets')).toBe(true);
        expect(guide.active).toMatchObject({
            flow: 'import_guide',
            stepId: 'import.assets',
            mode: 'automatic',
        });
    });

    it.each(['completed', 'skipped'] as const)('a terminal %s Import step never repeats without explicit replay', async (status) => {
        const flow = progressItem({
            flow: 'import_guide',
            status: 'pending',
            steps: IMPORT_GUIDE_STEP_IDS.map((stepId) =>
                stepProgressItem(stepId, {
                    status: stepId === 'import.assets' ? status : 'pending',
                    completed_at: stepId === 'import.assets' && status === 'completed' ? '2026-01-02T00:00:00Z' : null,
                    skipped_at: stepId === 'import.assets' && status === 'skipped' ? '2026-01-02T00:00:00Z' : null,
                }),
            ),
        });
        const {guide} = await buildGuide({flows: [flow]});

        expect(guide.startImportAt('import.assets')).toBe(false);
        expect(guide.active).toBeNull();
    });

    it('suspend({resetImport: true}) preserves the current step for a step-managed flow and calls no endpoint', async () => {
        const {guide, controller, api} = await buildGuide({flows: [progressItem({flow: 'import_guide', status: 'pending'})]});
        guide.startImportAt('import.review');
        expect(controller.replay?.stepId).toBe('import.review');

        guide.suspend({resetImport: true});

        expect(guide.active).toBeNull();
        expect(controller.replay?.stepId).toBe('import.review');
        expect(api.completeFlow).not.toHaveBeenCalled();
        expect(api.skipFlow).not.toHaveBeenCalled();
        expect(api.completeStep).not.toHaveBeenCalled();
        expect(api.skipStep).not.toHaveBeenCalled();
        expect(api.getProgress).toHaveBeenCalledTimes(1); // only buildGuide's initial load
    });

    it('suspend() without resetImport leaves the stored replay step untouched', async () => {
        const {guide, controller} = await buildGuide({flows: [progressItem({flow: 'import_guide', status: 'pending'})]});
        guide.startImportAt('import.review');

        guide.suspend();

        expect(guide.active).toBeNull();
        expect(controller.replay?.stepId).toBe('import.review');
    });
});

describe('onboardingGuide — finish/skip (automatic transitions and replay-local exits)', () => {
    it('keeps a replacement Analyze activation and replay token when Select completion succeeds late', async () => {
        const initial = progressItem({flow: 'import_guide', status: 'pending'});
        const {guide, controller, api, storage} = await buildGuide({flows: [initial]});
        const selectCompletion = deferred<OnboardingProgressItem>();
        api.completeStep.mockReturnValue(selectCompletion.promise);

        expect(guide.startImportAt('import.select')).toBe(true);
        const finishingSelect = guide.finish();
        expect(guide.actionPending).toBe(true);
        expect(api.completeStep).toHaveBeenCalledExactlyOnceWith('import_guide', 'import.select', {
            expected_version: 1,
        });

        // Import hosts may advance while persistence for the previous semantic
        // step is still in flight. The new activation writes its own replay
        // token without starting another backend transition.
        expect(guide.startImportAt('import.analyze')).toBe(true);
        expect(guide.active).toEqual({
            flow: 'import_guide',
            version: 1,
            stepId: 'import.analyze',
            mode: 'automatic',
        });
        const analyzeReplay = {
            flow: 'import_guide',
            version: 1,
            stepId: 'import.analyze',
            startedAt: 1000,
            mode: 'automatic' as const,
            remainingStepIds: ['import.analyze'],
        };
        expect(controller.replay).toEqual(analyzeReplay);
        expect(storage.getItem(replayKey('user-1', 'import_guide', 1))).toBe(JSON.stringify(analyzeReplay));

        selectCompletion.resolve(
            progressItem({
                flow: 'import_guide',
                status: 'pending',
                steps: initial.steps?.map((step) => (step.step_id === 'import.select' ? stepProgressItem(step.step_id, {status: 'completed', completed_at: '2026-01-02T00:00:00Z'}) : step)),
            }),
        );

        expect(await finishingSelect).toBeUndefined();
        expect(guide.active).toEqual({
            flow: 'import_guide',
            version: 1,
            stepId: 'import.analyze',
            mode: 'automatic',
        });
        expect(controller.replay).toEqual(analyzeReplay);
        expect(controller.findStep('import_guide', 'import.select')?.status).toBe('completed');
        expect(controller.findStep('import_guide', 'import.analyze')?.status).toBe('pending');
        expect(guide.error).toBeNull();
        expect(guide.actionPending).toBe(false);
    });

    it('does not leak a late Select completion error into a replacement Analyze activation', async () => {
        const {guide, controller, api} = await buildGuide({
            flows: [progressItem({flow: 'import_guide', status: 'pending'})],
        });
        const selectCompletion = deferred<OnboardingProgressItem>();
        api.completeStep.mockReturnValue(selectCompletion.promise);

        expect(guide.startImportAt('import.select')).toBe(true);
        const finishingSelect = guide.finish();
        expect(guide.actionPending).toBe(true);
        expect(guide.startImportAt('import.analyze')).toBe(true);

        selectCompletion.reject(new Error('late Select completion failed'));

        expect(await finishingSelect).toBeUndefined();
        expect(guide.active).toEqual({
            flow: 'import_guide',
            version: 1,
            stepId: 'import.analyze',
            mode: 'automatic',
        });
        expect(controller.replay).toEqual({
            flow: 'import_guide',
            version: 1,
            stepId: 'import.analyze',
            startedAt: 1000,
            mode: 'automatic',
            remainingStepIds: ['import.analyze'],
        });
        expect(controller.findStep('import_guide', 'import.select')?.status).toBe('pending');
        expect(guide.error).toBeNull();
        expect(guide.actionPending).toBe(false);
    });

    it('keeps a reopened Select generation pending when the dismissed generation skips successfully late', async () => {
        const initial = progressItem({flow: 'import_guide', status: 'pending'});
        const {guide, controller, api, storage} = await buildGuide({flows: [initial]});
        const oldSkip = deferred<OnboardingProgressItem>();
        const replacementCompletion = deferred<OnboardingProgressItem>();
        api.skipStep.mockReturnValue(oldSkip.promise);
        api.completeStep.mockReturnValue(replacementCompletion.promise);

        expect(guide.startImportAt('import.select')).toBe(true);
        const skippingOldGeneration = guide.skip();
        expect(guide.actionPending).toBe(true);

        guide.dismissHost();
        expect(guide.active).toBeNull();
        expect(guide.actionPending).toBe(false);

        const replacementReplay = {
            flow: 'import_guide',
            version: 1,
            stepId: 'import.select',
            startedAt: 1000,
            mode: 'automatic' as const,
            remainingStepIds: ['import.select'],
        };
        const replayWrite = vi.spyOn(storage, 'setItem');
        expect(guide.startImportAt('import.select')).toBe(true);
        expect(replayWrite).toHaveBeenCalledExactlyOnceWith(replayKey('user-1', 'import_guide', 1), JSON.stringify(replacementReplay));
        expect(guide.active).toEqual({
            flow: 'import_guide',
            version: 1,
            stepId: 'import.select',
            mode: 'automatic',
        });
        expect(controller.replay).toEqual(replacementReplay);

        oldSkip.resolve(
            progressItem({
                flow: 'import_guide',
                status: 'pending',
                steps: initial.steps?.map((step) => (step.step_id === 'import.select' ? stepProgressItem(step.step_id, {status: 'skipped', skipped_at: '2026-01-02T00:00:00Z'}) : step)),
            }),
        );

        expect(await skippingOldGeneration).toBe(true);
        expect(guide.active).toEqual({
            flow: 'import_guide',
            version: 1,
            stepId: 'import.select',
            mode: 'automatic',
        });
        expect(controller.replay).toEqual(replacementReplay);
        expect(guide.error).toBeNull();
        expect(guide.actionPending).toBe(false);

        const finishingReplacement = guide.finish();
        expect(guide.actionPending).toBe(true);

        replacementCompletion.resolve(
            progressItem({
                flow: 'import_guide',
                status: 'pending',
                steps: initial.steps?.map((step) => (step.step_id === 'import.select' ? stepProgressItem(step.step_id, {status: 'completed', completed_at: '2026-01-03T00:00:00Z'}) : step)),
            }),
        );

        expect(await finishingReplacement).toBeUndefined();
        expect(guide.active).toBeNull();
        expect(controller.replay).toBeNull();
        expect(guide.error).toBeNull();
        expect(guide.actionPending).toBe(false);
        expect(api.skipStep).toHaveBeenCalledExactlyOnceWith('import_guide', 'import.select', {
            expected_version: 1,
        });
        expect(api.completeStep).toHaveBeenCalledExactlyOnceWith('import_guide', 'import.select', {
            expected_version: 1,
        });
    });

    it('does not let a dismissed generation error or finally contaminate a pending reopened Select generation', async () => {
        const {guide, controller, api} = await buildGuide({
            flows: [progressItem({flow: 'import_guide', status: 'pending'})],
        });
        const oldSkip = deferred<OnboardingProgressItem>();
        const replacementCompletion = deferred<OnboardingProgressItem>();
        vi.spyOn(controller, 'skipStep').mockReturnValue(oldSkip.promise);
        api.completeStep.mockReturnValue(replacementCompletion.promise);

        expect(guide.startImportAt('import.select')).toBe(true);
        const skippingOldGeneration = guide.skip();
        guide.dismissHost();
        expect(guide.startImportAt('import.select')).toBe(true);
        const finishingReplacement = guide.finish();
        expect(guide.actionPending).toBe(true);

        oldSkip.reject(new Error('late dismissed Select skip failed'));

        expect(await skippingOldGeneration).toBe(false);
        expect(guide.active).toEqual({
            flow: 'import_guide',
            version: 1,
            stepId: 'import.select',
            mode: 'automatic',
        });
        expect(controller.replay).toEqual({
            flow: 'import_guide',
            version: 1,
            stepId: 'import.select',
            startedAt: 1000,
            mode: 'automatic',
            remainingStepIds: ['import.select'],
        });
        expect(guide.error).toBeNull();
        expect(guide.actionPending).toBe(true);

        replacementCompletion.reject(new Error('replacement Select completion failed'));

        expect(await finishingReplacement).toBeUndefined();
        expect(guide.active).toEqual({
            flow: 'import_guide',
            version: 1,
            stepId: 'import.select',
            mode: 'automatic',
        });
        expect(controller.replay).toEqual({
            flow: 'import_guide',
            version: 1,
            stepId: 'import.select',
            startedAt: 1000,
            mode: 'automatic',
            remainingStepIds: ['import.select'],
        });
        expect(guide.error).toBe('onboarding.errors.complete');
        expect(guide.actionPending).toBe(false);
    });

    it('does not clear a newer host step when the prior target-click completion resolves late', async () => {
        const initial = progressItem({flow: 'import_guide', status: 'pending'});
        const {guide, api} = await buildGuide({flows: [initial]});
        const request = deferred<OnboardingProgressItem>();
        api.completeStep.mockReturnValue(request.promise);

        expect(guide.startImportAt('import.upload')).toBe(true);
        const finishing = guide.finish();
        expect(guide.actionPending).toBe(true);

        // The same real wizard click can mount the next host step before the
        // persistence request for the previous one resolves.
        expect(guide.startImportAt('import.select')).toBe(true);
        expect(guide.active).toMatchObject({flow: 'import_guide', stepId: 'import.select'});
        request.resolve(
            progressItem({
                flow: 'import_guide',
                status: 'pending',
                steps: initial.steps?.map((step) => (step.step_id === 'import.upload' ? stepProgressItem(step.step_id, {status: 'completed', completed_at: '2026-01-02T00:00:00Z'}) : step)),
            }),
        );

        await finishing;
        expect(guide.active).toMatchObject({flow: 'import_guide', stepId: 'import.select'});
        expect(guide.actionPending).toBe(false);
    });

    it('does not clear a newly opened modal guide when the final page Add completion succeeds late', async () => {
        const pageFlow = progressItem({flow: 'broker_page_guide', status: 'pending'});
        const modalFlow = progressItem({flow: 'broker_guide', status: 'pending'});
        const {guide, controller, api} = await buildGuide({flows: [pageFlow, modalFlow]});
        const oldCompletion = deferred<OnboardingProgressItem>();
        api.completeFlow.mockReturnValue(oldCompletion.promise);

        expect(guide.maybeStartContextual('broker_page_guide')).toBe(true);
        for (let index = 1; index < guideSteps('broker_page_guide').length; index += 1) guide.next();
        expect(guide.active?.stepId).toBe('broker.page.add');

        const finishingPageGuide = guide.finish();
        expect(guide.actionPending).toBe(true);

        // This is the production Add-click order: capture starts completion,
        // then the page handler dismisses the page guide and opens its modal guide.
        guide.dismissHost();
        expect(guide.maybeStartContextual('broker_guide')).toBe(true);
        expect(guide.active).toMatchObject({flow: 'broker_guide', stepId: 'broker.overview'});
        expect(controller.replay).toMatchObject({flow: 'broker_guide', stepId: 'broker.overview'});

        oldCompletion.resolve(progressItem({flow: 'broker_page_guide', status: 'completed'}));
        await finishingPageGuide;

        expect(guide.active).toMatchObject({flow: 'broker_guide', stepId: 'broker.overview'});
        expect(controller.replay).toMatchObject({flow: 'broker_guide', stepId: 'broker.overview'});
        expect(guide.error).toBeNull();
    });

    it('merges the late Broker page Add completion after the overlapping modal skip has completed', async () => {
        const pageFlow = progressItem({flow: 'broker_page_guide', status: 'pending'});
        const modalFlow = progressItem({flow: 'broker_guide', status: 'pending'});
        const completedPageFlow = progressItem({flow: 'broker_page_guide', status: 'completed'});
        const skippedModalFlow = progressItem({flow: 'broker_guide', status: 'skipped'});
        const {guide, controller, api} = await buildGuide({flows: [pageFlow, modalFlow]});
        const pageCompletion = deferred<OnboardingProgressItem>();
        const modalSkip = deferred<OnboardingProgressItem>();
        api.completeFlow.mockReturnValue(pageCompletion.promise);
        api.skipFlow.mockReturnValue(modalSkip.promise);

        expect(guide.maybeStartContextual('broker_page_guide')).toBe(true);
        for (let index = 1; index < guideSteps('broker_page_guide').length; index += 1) guide.next();
        expect(guide.active?.stepId).toBe('broker.page.add');

        const finishingPageGuide = guide.finish();
        expect(guide.actionPending).toBe(true);
        expect(api.completeFlow).toHaveBeenCalledExactlyOnceWith('broker_page_guide', {
            expected_version: 1,
        });

        guide.dismissHost();
        expect(guide.maybeStartContextual('broker_guide')).toBe(true);
        const skippingModalGuide = guide.skip();
        expect(guide.actionPending).toBe(true);
        expect(api.skipFlow).toHaveBeenCalledExactlyOnceWith('broker_guide', {
            expected_version: 1,
        });

        modalSkip.resolve(skippedModalFlow);
        expect(await skippingModalGuide).toBe(true);
        expect(controller.findFlow('broker_page_guide')).toEqual(pageFlow);
        expect(controller.findFlow('broker_guide')).toEqual(skippedModalFlow);
        expect(guide.active).toBeNull();
        expect(guide.actionPending).toBe(false);

        pageCompletion.resolve(completedPageFlow);
        expect(await finishingPageGuide).toBeUndefined();

        expect(controller.findFlow('broker_page_guide')).toEqual(completedPageFlow);
        expect(controller.findFlow('broker_guide')).toEqual(skippedModalFlow);
        expect(guide.active).toBeNull();
        expect(guide.actionPending).toBe(false);
        expect(guide.error).toBeNull();
    });

    it('does not overwrite a new modal guide error when the final page Add completion fails late', async () => {
        const pageFlow = progressItem({flow: 'broker_page_guide', status: 'pending'});
        const modalFlow = progressItem({flow: 'broker_guide', status: 'pending'});
        const {guide, api} = await buildGuide({flows: [pageFlow, modalFlow]});
        const oldCompletion = deferred<OnboardingProgressItem>();
        api.completeFlow.mockReturnValue(oldCompletion.promise);
        api.skipFlow.mockRejectedValue(new Error('new modal skip failed'));

        expect(guide.maybeStartContextual('broker_page_guide')).toBe(true);
        for (let index = 1; index < guideSteps('broker_page_guide').length; index += 1) guide.next();
        expect(guide.active?.stepId).toBe('broker.page.add');
        const finishingPageGuide = guide.finish();

        guide.dismissHost();
        expect(guide.maybeStartContextual('broker_guide')).toBe(true);
        expect(await guide.skip()).toBe(false);
        expect(guide.active).toMatchObject({flow: 'broker_guide', stepId: 'broker.overview'});
        expect(guide.error).toBe('onboarding.errors.skip');

        oldCompletion.reject(new Error('old page completion failed'));
        await finishingPageGuide;

        expect(guide.active).toMatchObject({flow: 'broker_guide', stepId: 'broker.overview'});
        expect(guide.error).toBe('onboarding.errors.skip');
    });

    it('does not let the final page Add completion finally clear the new modal guide pending state', async () => {
        const pageFlow = progressItem({flow: 'broker_page_guide', status: 'pending'});
        const modalFlow = progressItem({flow: 'broker_guide', status: 'pending'});
        const {guide, api} = await buildGuide({flows: [pageFlow, modalFlow]});
        const oldCompletion = deferred<OnboardingProgressItem>();
        const modalCompletion = deferred<OnboardingProgressItem>();
        api.completeFlow.mockReturnValueOnce(oldCompletion.promise).mockReturnValueOnce(modalCompletion.promise);

        expect(guide.maybeStartContextual('broker_page_guide')).toBe(true);
        for (let index = 1; index < guideSteps('broker_page_guide').length; index += 1) guide.next();
        expect(guide.active?.stepId).toBe('broker.page.add');
        const finishingPageGuide = guide.finish();

        guide.dismissHost();
        expect(guide.maybeStartContextual('broker_guide')).toBe(true);
        const finishingModalGuide = guide.finish();
        expect(guide.actionPending).toBe(true);

        oldCompletion.resolve(progressItem({flow: 'broker_page_guide', status: 'completed'}));
        await finishingPageGuide;

        expect(guide.active).toMatchObject({flow: 'broker_guide', stepId: 'broker.overview'});
        expect(guide.actionPending).toBe(true);
        expect(guide.error).toBeNull();

        modalCompletion.resolve(progressItem({flow: 'broker_guide', status: 'completed'}));
        await finishingModalGuide;
        expect(guide.actionPending).toBe(false);
    });

    it('finish calls only completeFlow, clears the replay, and returns the preserved returnTo on success', async () => {
        const {guide, api, storage} = await buildGuide();
        api.completeFlow.mockResolvedValue(progressItem({flow: 'intro_tour', status: 'completed', version: 1, current_version: 1}));
        guide.maybeStartIntro('/transactions/9');
        const key = replayKey('user-1', 'intro_tour', 1);
        expect(storage.getItem(key)).not.toBeNull();

        const returnTo = await guide.finish();

        expect(returnTo).toBe('/transactions/9');
        expect(api.completeFlow).toHaveBeenCalledOnce();
        expect(api.completeFlow).toHaveBeenCalledWith('intro_tour', {expected_version: 1});
        expect(api.skipFlow).not.toHaveBeenCalled();
        expect(api.completeWelcome).not.toHaveBeenCalled();
        expect(guide.active).toBeNull();
        expect(storage.getItem(key)).toBeNull();
        expect(guide.error).toBeNull();
    });

    it('finish retains the active guide and surfaces the error, without clearing the replay, on failure', async () => {
        const {guide, api, storage} = await buildGuide();
        api.completeFlow.mockRejectedValue(new Error('network down'));
        guide.maybeStartIntro();
        const activeBefore = guide.active;
        const key = replayKey('user-1', 'intro_tour', 1);

        const returnTo = await guide.finish();

        expect(returnTo).toBeUndefined();
        expect(guide.active).toEqual(activeBefore);
        expect(guide.error).toBe('onboarding.errors.complete');
        expect(storage.getItem(key)).not.toBeNull();
        expect(guide.actionPending).toBe(false);
    });

    it('skip calls only skipFlow for a flow-managed guide, clears replay, and returns true', async () => {
        const {guide, api, storage} = await buildGuide({flows: [progressItem({flow: 'intro_tour', status: 'pending'})]});
        api.skipFlow.mockResolvedValue(progressItem({flow: 'intro_tour', status: 'skipped', version: 1, current_version: 1}));
        guide.maybeStartIntro();
        const key = replayKey('user-1', 'intro_tour', 1);

        const skipped = await guide.skip();

        expect(skipped).toBe(true);
        expect(api.skipFlow).toHaveBeenCalledOnce();
        expect(api.skipFlow).toHaveBeenCalledWith('intro_tour', {expected_version: 1});
        expect(api.skipStep).not.toHaveBeenCalled();
        expect(api.completeFlow).not.toHaveBeenCalled();
        expect(api.completeWelcome).not.toHaveBeenCalled();
        expect(guide.active).toBeNull();
        expect(storage.getItem(key)).toBeNull();
        expect(guide.error).toBeNull();
    });

    it('step skip retains the active guide and surfaces the error on failure', async () => {
        const {guide, api, storage} = await buildGuide({flows: [progressItem({flow: 'import_guide', status: 'pending'})]});
        api.skipStep.mockRejectedValue(new Error('server exploded'));
        guide.startImportAt('import.upload');
        const key = replayKey('user-1', 'import_guide', 1);

        const skipped = await guide.skip();

        expect(skipped).toBe(false);
        expect(guide.active).not.toBeNull();
        expect(guide.error).toBe('onboarding.errors.skip');
        expect(storage.getItem(key)).not.toBeNull();
        expect(api.skipStep).toHaveBeenCalledExactlyOnceWith('import_guide', 'import.upload', {
            expected_version: 1,
        });
        expect(api.skipFlow).not.toHaveBeenCalled();
    });

    it('terminal flow-managed replay Finish clears only session replay and preserves returnTo', async () => {
        const {guide, controller, api, storage} = await buildGuide({flows: [progressItem({flow: 'intro_tour', status: 'completed'})]});
        expect(guide.startIntroReplay('/transactions/9')).toBe(true);
        const key = replayKey('user-1', 'intro_tour', 1);
        expect(guide.active).toMatchObject({flow: 'intro_tour', mode: 'replay'});
        expect(guide.active?.returnTo).toBe('/transactions/9');
        expect(controller.replay?.returnTo).toBe('/transactions/9');
        expect(storage.getItem(key)).not.toBeNull();

        const returnTo = await guide.finish();

        expect(returnTo).toBe('/transactions/9');
        expect(controller.replay).toBeNull();
        expect(guide.active).toBeNull();
        expect(storage.getItem(key)).toBeNull();
        expect(controller.findFlow('intro_tour')?.status).toBe('completed');
        expect(api.completeFlow).not.toHaveBeenCalled();
        expect(api.skipFlow).not.toHaveBeenCalled();
        expect(api.completeStep).not.toHaveBeenCalled();
        expect(api.skipStep).not.toHaveBeenCalled();
        expect(api.completeWelcome).not.toHaveBeenCalled();
    });

    it('terminal flow-managed replay Skip clears only session replay and preserves returnTo until exit', async () => {
        const {guide, controller, api, storage} = await buildGuide({flows: [progressItem({flow: 'intro_tour', status: 'completed'})]});
        expect(guide.startIntroReplay('/transactions/9')).toBe(true);
        const key = replayKey('user-1', 'intro_tour', 1);
        expect(guide.active).toMatchObject({flow: 'intro_tour', mode: 'replay'});
        expect(guide.active?.returnTo).toBe('/transactions/9');
        expect(controller.replay?.returnTo).toBe('/transactions/9');
        expect(storage.getItem(key)).not.toBeNull();

        const skipped = await guide.skip();

        expect(skipped).toBe(true);
        expect(controller.replay).toBeNull();
        expect(guide.active).toBeNull();
        expect(storage.getItem(key)).toBeNull();
        expect(controller.findFlow('intro_tour')?.status).toBe('completed');
        expect(api.completeFlow).not.toHaveBeenCalled();
        expect(api.skipFlow).not.toHaveBeenCalled();
        expect(api.completeStep).not.toHaveBeenCalled();
        expect(api.skipStep).not.toHaveBeenCalled();
        expect(api.completeWelcome).not.toHaveBeenCalled();
    });
});

describe('onboardingGuide — navigateAfterFinish (returnTo safety net)', () => {
    it('falls back to /dashboard instead of navigating to a protocol-relative returnTo', async () => {
        const {guide, navigate} = await buildGuide();

        await guide.navigateAfterFinish('//evil.example.com');

        expect(navigate).toHaveBeenCalledOnce();
        expect(navigate).toHaveBeenCalledWith('/dashboard');
    });

    it('falls back to /dashboard instead of navigating to a backslash-bearing returnTo', async () => {
        const {guide, navigate} = await buildGuide();

        await guide.navigateAfterFinish('/ok\\evil');

        expect(navigate).toHaveBeenCalledOnce();
        expect(navigate).toHaveBeenCalledWith('/dashboard');
    });

    it('navigates to a genuinely safe internal returnTo unchanged', async () => {
        const {guide, navigate} = await buildGuide();

        await guide.navigateAfterFinish('/transactions/7');

        expect(navigate).toHaveBeenCalledOnce();
        expect(navigate).toHaveBeenCalledWith('/transactions/7');
    });

    it('falls back to /dashboard when returnTo is missing entirely', async () => {
        const {guide, navigate} = await buildGuide();

        await guide.navigateAfterFinish(undefined);

        expect(navigate).toHaveBeenCalledOnce();
        expect(navigate).toHaveBeenCalledWith('/dashboard');
    });
});

describe('onboardingGuide — missing progress fails visibly', () => {
    it('finish() surfaces a visible error and returns undefined, instead of a success-shaped result, once the flow row is gone', async () => {
        const {guide, controller, api} = await buildGuide();
        guide.maybeStartIntro();
        expect(guide.active).not.toBeNull();

        // Simulates the flow row disappearing from a freshly reloaded progress
        // snapshot (e.g. a stale account/version) while the guide is still active
        // on it — never by mutating the response object in place.
        api.getProgress.mockResolvedValue(progressResponse([progressItem({flow: 'welcome'})]));
        await controller.load(api);

        const returnTo = await guide.finish();

        expect(returnTo).toBeUndefined();
        expect(guide.error).toBe('onboarding.errors.progressUnavailable');
        // active is left in place: a caller gating navigation on `!guide.error`
        // (as OnboardingOverlayHost does) will not mistake this for success.
        expect(guide.active).not.toBeNull();
        expect(api.completeFlow).not.toHaveBeenCalled();
    });

    it('skip() surfaces the same visible error instead of a silent no-op success', async () => {
        const {guide, controller, api} = await buildGuide({flows: [progressItem({flow: 'import_guide', status: 'pending'})]});
        guide.startImportAt('import.upload');

        api.getProgress.mockResolvedValue(progressResponse([progressItem({flow: 'welcome'})]));
        await controller.load(api);

        const skipped = await guide.skip();

        expect(skipped).toBe(false);
        expect(guide.error).toBe('onboarding.errors.progressUnavailable');
        expect(api.skipFlow).not.toHaveBeenCalled();
    });
});
