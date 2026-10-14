import {getClientSessionGeneration, getClientSessionUserId, isClientSessionCurrent, registerClientSessionReset, type ClientSessionResetter} from '$lib/stores/app/clientSession';
import type {OnboardingApi, OnboardingFlow, OnboardingLoadState, OnboardingProgressItem, OnboardingProgressResponse, OnboardingReplayState, OnboardingStepProgressItem, OnboardingWelcomeCompleteRequest} from '$lib/types/onboarding';

/**
 * Guide positions (automatic or armed replay) persist in `localStorage`, keyed
 * `lf_{userId}_onboarding_replay_{flow}_v{version}`: they survive a closed tab, a
 * browser restart, and logging out and back in on this browser (developer decision,
 * 2026-09-24); they stay per account, and a version bump drops the old key on the
 * next read or write. A session change resets only the in-memory state. When
 * another tab deletes the key of this tab's replay, the in-memory copy is dropped,
 * so this tab cannot write it back; the guide module wires that `storage` listener
 * and closes its active step.
 */
const REPLAY_STORAGE_UNAVAILABLE = 'Browser storage is unavailable';

interface RequestTicket {
    userId: string;
    generation: number;
    epoch: number;
    owner: string;
    sequence: number;
    loadSequence: number;
}

interface OnboardingControllerDependencies {
    getUserId?: () => string | null;
    getGeneration?: () => number;
    isCurrent?: (generation: number) => boolean;
    getReplayStorage?: () => Storage | null;
    now?: () => number;
}

function defaultReplayStorage(): Storage | null {
    if (typeof window === 'undefined') return null;
    try {
        return window.localStorage;
    } catch {
        return null;
    }
}

function errorMessage(error: unknown): string {
    return error instanceof Error ? error.message : 'Onboarding request failed';
}

function isReplayState(value: unknown): value is OnboardingReplayState {
    if (!value || typeof value !== 'object') return false;
    const candidate = value as Partial<OnboardingReplayState>;
    return (
        typeof candidate.flow === 'string' &&
        typeof candidate.version === 'number' &&
        Number.isInteger(candidate.version) &&
        candidate.version >= 1 &&
        typeof candidate.stepId === 'string' &&
        typeof candidate.startedAt === 'number' &&
        (candidate.mode === undefined || candidate.mode === 'automatic' || candidate.mode === 'replay') &&
        (candidate.remainingStepIds === undefined || (Array.isArray(candidate.remainingStepIds) && candidate.remainingStepIds.every((stepId) => typeof stepId === 'string'))) &&
        (candidate.returnTo === undefined || typeof candidate.returnTo === 'string')
    );
}

export function createOnboardingController(dependencies: OnboardingControllerDependencies = {}) {
    const getUserId = dependencies.getUserId ?? getClientSessionUserId;
    const getGeneration = dependencies.getGeneration ?? getClientSessionGeneration;
    const isCurrent = dependencies.isCurrent ?? isClientSessionCurrent;
    const getReplayStorage = dependencies.getReplayStorage ?? defaultReplayStorage;
    const now = dependencies.now ?? Date.now;

    let state = $state<OnboardingLoadState>('idle');
    let progress = $state<OnboardingProgressResponse | null>(null);
    let error = $state<string | null>(null);
    let transitioningFlow = $state<OnboardingFlow | null>(null);
    let transitioningTicket: RequestTicket | null = null;
    let replay = $state<OnboardingReplayState | null>(null);
    let replayStorageError = $state<string | null>(null);
    let requestEpoch = 0;
    const requestSequences = new Map<string, number>();

    function captureRequest(owner: string): RequestTicket {
        const userId = getUserId();
        if (!userId) throw new Error('Onboarding requires an authenticated user');
        const sequence = (requestSequences.get(owner) ?? 0) + 1;
        requestSequences.set(owner, sequence);
        return {
            userId,
            generation: getGeneration(),
            epoch: requestEpoch,
            owner,
            sequence,
            loadSequence: requestSequences.get('load') ?? 0,
        };
    }

    function requestIsCurrent(ticket: RequestTicket): boolean {
        return ticket.epoch === requestEpoch && requestSequences.get(ticket.owner) === ticket.sequence && ticket.loadSequence === (requestSequences.get('load') ?? 0) && ticket.userId === getUserId() && isCurrent(ticket.generation);
    }

    function replayPrefix(userId: string, flow: OnboardingFlow): string {
        return `lf_${userId}_onboarding_replay_${flow}_v`;
    }

    function replayKey(userId: string, flow: OnboardingFlow, version: number): string {
        return `${replayPrefix(userId, flow)}${version}`;
    }

    function removeReplayVersions(storage: Storage, userId: string, flow: OnboardingFlow, keepVersion?: number): void {
        const prefix = replayPrefix(userId, flow);
        const keepKey = keepVersion === undefined ? null : replayKey(userId, flow, keepVersion);
        const keysToRemove: string[] = [];
        for (let index = 0; index < storage.length; index += 1) {
            const key = storage.key(index);
            if (key?.startsWith(prefix) && key !== keepKey) keysToRemove.push(key);
        }
        for (const key of keysToRemove) storage.removeItem(key);
    }

    function writeReplay(nextReplay: OnboardingReplayState): boolean {
        const userId = getUserId();
        const storage = getReplayStorage();
        if (!userId || !storage) {
            replayStorageError = REPLAY_STORAGE_UNAVAILABLE;
            return false;
        }
        try {
            removeReplayVersions(storage, userId, nextReplay.flow, nextReplay.version);
            storage.setItem(replayKey(userId, nextReplay.flow, nextReplay.version), JSON.stringify(nextReplay));
            replay = nextReplay;
            replayStorageError = null;
            return true;
        } catch (storageError) {
            replayStorageError = errorMessage(storageError);
            return false;
        }
    }

    function findFlow(flow: OnboardingFlow): OnboardingProgressItem | null {
        return progress?.flows.find((item) => item.flow === flow) ?? null;
    }

    function findStep(flow: OnboardingFlow, stepId: string): OnboardingStepProgressItem | null {
        return findFlow(flow)?.steps?.find((item) => item.step_id === stepId) ?? null;
    }

    function replaceFlow(updated: OnboardingProgressItem): void {
        if (!progress) return;
        progress = {
            flows: progress.flows.map((item) => (item.flow === updated.flow ? updated : item)),
        };
    }

    async function load(api: OnboardingApi): Promise<OnboardingProgressResponse | null> {
        const ticket = captureRequest('load');
        transitioningFlow = null;
        transitioningTicket = null;
        state = 'loading';
        error = null;
        try {
            const response = await api.getProgress();
            if (!requestIsCurrent(ticket)) return null;
            progress = response;
            state = 'ready';
            return response;
        } catch (requestError) {
            if (!requestIsCurrent(ticket)) return null;
            error = errorMessage(requestError);
            state = 'error';
            throw requestError;
        }
    }

    async function transition(api: OnboardingApi, flow: OnboardingFlow, expectedVersion: number, target: 'complete' | 'skip'): Promise<OnboardingProgressItem | null> {
        const ticket = captureRequest(`flow:${flow}`);
        transitioningFlow = flow;
        transitioningTicket = ticket;
        error = null;
        try {
            const request = {expected_version: expectedVersion};
            const updated = target === 'complete' ? await api.completeFlow(flow, request) : await api.skipFlow(flow, request);
            if (!requestIsCurrent(ticket)) return null;
            replaceFlow(updated);
            return updated;
        } catch (requestError) {
            if (!requestIsCurrent(ticket)) return null;
            if (transitioningTicket === ticket) error = errorMessage(requestError);
            throw requestError;
        } finally {
            if (transitioningTicket === ticket) {
                transitioningFlow = null;
                transitioningTicket = null;
            }
        }
    }

    async function completeWelcome(api: OnboardingApi, request: OnboardingWelcomeCompleteRequest): Promise<OnboardingProgressItem | null> {
        const ticket = captureRequest('flow:welcome');
        transitioningFlow = 'welcome';
        transitioningTicket = ticket;
        error = null;
        try {
            const updated = await api.completeWelcome(request);
            if (!requestIsCurrent(ticket)) return null;
            replaceFlow(updated);
            return updated;
        } catch (requestError) {
            if (!requestIsCurrent(ticket)) return null;
            if (transitioningTicket === ticket) error = errorMessage(requestError);
            throw requestError;
        } finally {
            if (transitioningTicket === ticket) {
                transitioningFlow = null;
                transitioningTicket = null;
            }
        }
    }

    async function transitionStep(api: OnboardingApi, flow: OnboardingFlow, stepId: string, expectedVersion: number, target: 'complete' | 'skip'): Promise<OnboardingProgressItem | null> {
        const ticket = captureRequest(`flow:${flow}`);
        transitioningFlow = flow;
        transitioningTicket = ticket;
        error = null;
        try {
            const request = {expected_version: expectedVersion};
            const updated = target === 'complete' ? await api.completeStep(flow, stepId, request) : await api.skipStep(flow, stepId, request);
            if (!requestIsCurrent(ticket)) return null;
            replaceFlow(updated);
            return updated;
        } catch (requestError) {
            if (!requestIsCurrent(ticket)) return null;
            if (transitioningTicket === ticket) error = errorMessage(requestError);
            throw requestError;
        } finally {
            if (transitioningTicket === ticket) {
                transitioningFlow = null;
                transitioningTicket = null;
            }
        }
    }

    function startReplay(flow: OnboardingFlow, version: number, stepId: string, returnTo?: string, remainingStepIds?: string[], mode?: OnboardingReplayState['mode']): boolean {
        return writeReplay({
            flow,
            version,
            stepId,
            startedAt: now(),
            ...(mode ? {mode} : {}),
            ...(remainingStepIds ? {remainingStepIds} : {}),
            ...(returnTo ? {returnTo} : {}),
        });
    }

    function resumeReplay(flow: OnboardingFlow, version: number, validStepIds: readonly string[], fallbackStepId: string): OnboardingReplayState | null {
        const userId = getUserId();
        const storage = getReplayStorage();
        if (!userId || !storage) {
            replayStorageError = REPLAY_STORAGE_UNAVAILABLE;
            return null;
        }
        try {
            removeReplayVersions(storage, userId, flow, version);
            const key = replayKey(userId, flow, version);
            const raw = storage.getItem(key);
            if (!raw) {
                replay = null;
                replayStorageError = null;
                return null;
            }
            let parsed: unknown;
            try {
                parsed = JSON.parse(raw);
            } catch (parseError) {
                storage.removeItem(key);
                replay = null;
                replayStorageError = errorMessage(parseError);
                return null;
            }
            if (!isReplayState(parsed) || parsed.flow !== flow || parsed.version !== version) {
                storage.removeItem(key);
                replay = null;
                replayStorageError = 'Saved onboarding replay state was invalid';
                return null;
            }
            if (!validStepIds.includes(parsed.stepId)) {
                const recovered = {...parsed, stepId: fallbackStepId};
                return writeReplay(recovered) ? recovered : null;
            }
            replay = parsed;
            replayStorageError = null;
            return parsed;
        } catch (storageError) {
            replay = null;
            replayStorageError = errorMessage(storageError);
            return null;
        }
    }

    function hasReplay(flow: OnboardingFlow, version: number): boolean {
        const userId = getUserId();
        const storage = getReplayStorage();
        if (!userId || !storage) return false;
        try {
            removeReplayVersions(storage, userId, flow, version);
            const raw = storage.getItem(replayKey(userId, flow, version));
            if (!raw) return false;
            const parsed: unknown = JSON.parse(raw);
            if (!isReplayState(parsed) || parsed.flow !== flow || parsed.version !== version) {
                storage.removeItem(replayKey(userId, flow, version));
                return false;
            }
            return true;
        } catch (storageError) {
            replayStorageError = errorMessage(storageError);
            return false;
        }
    }

    function updateReplayStep(stepId: string): boolean {
        if (!replay) return false;
        return writeReplay({...replay, stepId});
    }

    function clearReplay(flow: OnboardingFlow, version: number): void {
        const userId = getUserId();
        const storage = getReplayStorage();
        if (!userId || !storage) {
            replayStorageError = REPLAY_STORAGE_UNAVAILABLE;
            return;
        }
        try {
            storage.removeItem(replayKey(userId, flow, version));
            if (replay?.flow === flow && replay.version === version) replay = null;
            replayStorageError = null;
        } catch (storageError) {
            replayStorageError = errorMessage(storageError);
        }
    }

    function handleExternalReplayChange(key: string | null, newValue: string | null): boolean {
        if (!replay || newValue !== null) return false;
        const userId = getUserId();
        if (key === null || (userId !== null && key === replayKey(userId, replay.flow, replay.version))) {
            replay = null;
            return true;
        }
        return false;
    }

    function reset(): void {
        requestEpoch += 1;
        requestSequences.clear();
        state = 'idle';
        progress = null;
        error = null;
        transitioningFlow = null;
        transitioningTicket = null;
        replay = null;
        replayStorageError = null;
    }

    return {
        get state() {
            return state;
        },
        get progress() {
            return progress;
        },
        get error() {
            return error;
        },
        get transitioningFlow() {
            return transitioningFlow;
        },
        get replay() {
            return replay;
        },
        get replayStorageError() {
            return replayStorageError;
        },
        findFlow,
        findStep,
        requiresAutomaticFlow: (flow: OnboardingFlow) => findFlow(flow)?.status === 'pending',
        load,
        complete: (api: OnboardingApi, flow: OnboardingFlow, expectedVersion: number) => transition(api, flow, expectedVersion, 'complete'),
        completeWelcome,
        skip: (api: OnboardingApi, flow: OnboardingFlow, expectedVersion: number) => transition(api, flow, expectedVersion, 'skip'),
        completeStep: (api: OnboardingApi, flow: OnboardingFlow, stepId: string, expectedVersion: number) => transitionStep(api, flow, stepId, expectedVersion, 'complete'),
        skipStep: (api: OnboardingApi, flow: OnboardingFlow, stepId: string, expectedVersion: number) => transitionStep(api, flow, stepId, expectedVersion, 'skip'),
        startReplay,
        resumeReplay,
        hasReplay,
        updateReplayStep,
        clearReplay,
        handleExternalReplayChange,
        reset,
    };
}

type OnboardingController = ReturnType<typeof createOnboardingController>;

/** Session resetter: forget the in-memory state only. Stored positions are per account and survive logout. */
export function createOnboardingSessionResetter(controller: Pick<OnboardingController, 'reset'>): ClientSessionResetter {
    return () => {
        controller.reset();
    };
}

/** `storage` event handler: react only to `localStorage` changes made by another tab; `onDropped` runs when this tab's replay was removed there. */
export function createReplayStorageListener(controller: Pick<OnboardingController, 'handleExternalReplayChange'>, getStorage: () => Storage | null = defaultReplayStorage, onDropped?: () => void): (event: StorageEvent) => void {
    return (event) => {
        if (event.storageArea !== null && event.storageArea !== getStorage()) return;
        if (controller.handleExternalReplayChange(event.key, event.newValue)) onDropped?.();
    };
}

export const onboarding = createOnboardingController();

registerClientSessionReset('onboarding', createOnboardingSessionResetter(onboarding));
