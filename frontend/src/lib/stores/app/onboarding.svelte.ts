import {getClientSessionGeneration, getClientSessionUserId, isClientSessionCurrent, registerClientSessionReset} from '$lib/stores/app/clientSession';
import type {OnboardingApi, OnboardingFlow, OnboardingLoadState, OnboardingProgressItem, OnboardingProgressResponse, OnboardingReplayState} from '$lib/types/onboarding';

interface RequestTicket {
    userId: string;
    generation: number;
    sequence: number;
}

interface OnboardingControllerDependencies {
    getUserId?: () => string | null;
    getGeneration?: () => number;
    isCurrent?: (generation: number) => boolean;
    getSessionStorage?: () => Storage | null;
    now?: () => number;
}

function defaultSessionStorage(): Storage | null {
    return typeof window === 'undefined' ? null : window.sessionStorage;
}

function errorMessage(error: unknown): string {
    return error instanceof Error ? error.message : 'Onboarding request failed';
}

function isReplayState(value: unknown): value is OnboardingReplayState {
    if (!value || typeof value !== 'object') return false;
    const candidate = value as Partial<OnboardingReplayState>;
    return typeof candidate.flow === 'string' && typeof candidate.version === 'number' && Number.isInteger(candidate.version) && candidate.version >= 1 && typeof candidate.stepId === 'string' && typeof candidate.startedAt === 'number';
}

export function createOnboardingController(dependencies: OnboardingControllerDependencies = {}) {
    const getUserId = dependencies.getUserId ?? getClientSessionUserId;
    const getGeneration = dependencies.getGeneration ?? getClientSessionGeneration;
    const isCurrent = dependencies.isCurrent ?? isClientSessionCurrent;
    const getSessionStorage = dependencies.getSessionStorage ?? defaultSessionStorage;
    const now = dependencies.now ?? Date.now;

    let state = $state<OnboardingLoadState>('idle');
    let progress = $state<OnboardingProgressResponse | null>(null);
    let error = $state<string | null>(null);
    let transitioningFlow = $state<OnboardingFlow | null>(null);
    let replay = $state<OnboardingReplayState | null>(null);
    let replayStorageError = $state<string | null>(null);
    let sequence = 0;

    function captureRequest(): RequestTicket {
        const userId = getUserId();
        if (!userId) throw new Error('Onboarding requires an authenticated user');
        return {
            userId,
            generation: getGeneration(),
            sequence: ++sequence,
        };
    }

    function requestIsCurrent(ticket: RequestTicket): boolean {
        return ticket.sequence === sequence && ticket.userId === getUserId() && isCurrent(ticket.generation);
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
        const storage = getSessionStorage();
        if (!userId || !storage) {
            replayStorageError = 'Session storage is unavailable';
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

    function replaceFlow(updated: OnboardingProgressItem): void {
        if (!progress) return;
        progress = {
            flows: progress.flows.map((item) => (item.flow === updated.flow ? updated : item)),
        };
    }

    async function load(api: OnboardingApi): Promise<OnboardingProgressResponse | null> {
        const ticket = captureRequest();
        transitioningFlow = null;
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
        const ticket = captureRequest();
        transitioningFlow = flow;
        error = null;
        try {
            const request = {expected_version: expectedVersion};
            const updated = target === 'complete' ? await api.completeFlow(flow, request) : await api.skipFlow(flow, request);
            if (!requestIsCurrent(ticket)) return null;
            replaceFlow(updated);
            return updated;
        } catch (requestError) {
            if (!requestIsCurrent(ticket)) return null;
            error = errorMessage(requestError);
            throw requestError;
        } finally {
            if (requestIsCurrent(ticket)) transitioningFlow = null;
        }
    }

    function startReplay(flow: OnboardingFlow, version: number, stepId: string): boolean {
        return writeReplay({flow, version, stepId, startedAt: now()});
    }

    function resumeReplay(flow: OnboardingFlow, version: number, validStepIds: readonly string[], fallbackStepId: string): OnboardingReplayState | null {
        const userId = getUserId();
        const storage = getSessionStorage();
        if (!userId || !storage) {
            replayStorageError = 'Session storage is unavailable';
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

    function updateReplayStep(stepId: string): boolean {
        if (!replay) return false;
        return writeReplay({...replay, stepId});
    }

    function clearReplay(flow: OnboardingFlow, version: number): void {
        const userId = getUserId();
        const storage = getSessionStorage();
        if (!userId || !storage) {
            replayStorageError = 'Session storage is unavailable';
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

    function reset(): void {
        sequence += 1;
        state = 'idle';
        progress = null;
        error = null;
        transitioningFlow = null;
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
        requiresAutomaticFlow: (flow: OnboardingFlow) => findFlow(flow)?.status === 'pending',
        load,
        complete: (api: OnboardingApi, flow: OnboardingFlow, expectedVersion: number) => transition(api, flow, expectedVersion, 'complete'),
        skip: (api: OnboardingApi, flow: OnboardingFlow, expectedVersion: number) => transition(api, flow, expectedVersion, 'skip'),
        startReplay,
        resumeReplay,
        updateReplayStep,
        clearReplay,
        reset,
    };
}

export const onboarding = createOnboardingController();

registerClientSessionReset('onboarding', () => onboarding.reset());
