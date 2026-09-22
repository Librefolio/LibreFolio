import {globalSettings} from '$lib/stores/app/globalSettings';
import {getClientSessionGeneration, getClientSessionUserId, isClientSessionCurrent, registerClientSessionReset} from '$lib/stores/app/clientSession';
import {onboarding} from '$lib/stores/app/onboarding.svelte';
import {userSettings} from '$lib/stores/app/settings';
import {isOnboardingProgressDue} from '$lib/types/onboarding';
import {onboardingApi} from './onboardingApi';

export type AppBootstrapState = 'idle' | 'loading' | 'ready' | 'degraded' | 'blocked';

interface AppBootstrapDependencies {
    getUserId?: () => string | null;
    getGeneration?: () => number;
    isCurrent?: (generation: number) => boolean;
    loadUserSettings?: () => Promise<boolean>;
    loadOnboarding?: () => Promise<unknown>;
    loadGlobalSettings?: () => Promise<unknown>;
    findWelcome?: () => ReturnType<typeof onboarding.findFlow>;
    checkWelcomeReplay?: (version: number) => boolean;
}

function errorMessage(error: unknown): string {
    return error instanceof Error ? error.message : 'Application bootstrap failed';
}

function safeInternalPath(value: string | null | undefined): string {
    if (!value || !value.startsWith('/') || value.startsWith('//') || value.includes('\\')) return '/dashboard';
    return value;
}

function isWelcomePath(path: string): boolean {
    return new URL(path, 'http://librefolio.local').pathname === '/welcome';
}

function returnToFromWelcome(path: string): string {
    const url = new URL(path, 'http://librefolio.local');
    return safeInternalPath(url.searchParams.get('returnTo'));
}

export function createAppBootstrap(dependencies: AppBootstrapDependencies = {}) {
    const getUserId = dependencies.getUserId ?? getClientSessionUserId;
    const getGeneration = dependencies.getGeneration ?? getClientSessionGeneration;
    const isCurrent = dependencies.isCurrent ?? isClientSessionCurrent;
    const loadUserSettings = dependencies.loadUserSettings ?? (() => userSettings.load());
    const loadOnboarding = dependencies.loadOnboarding ?? (() => onboarding.load(onboardingApi));
    const loadGlobalSettings = dependencies.loadGlobalSettings ?? (() => globalSettings.load());
    const findWelcome = dependencies.findWelcome ?? (() => onboarding.findFlow('welcome'));
    const checkWelcomeReplay = dependencies.checkWelcomeReplay ?? ((version: number) => onboarding.hasReplay('welcome', version));

    let state = $state<AppBootstrapState>('idle');
    let error = $state<string | null>(null);
    let loadedUserId = $state<string | null>(null);
    let sequence = 0;

    async function load(force = false): Promise<AppBootstrapState> {
        const userId = getUserId();
        if (!userId) {
            reset();
            return state;
        }
        if (!force && loadedUserId === userId && (state === 'ready' || state === 'degraded')) {
            return state;
        }

        const generation = getGeneration();
        const requestSequence = ++sequence;
        loadedUserId = userId;
        state = 'loading';
        error = null;

        const [settingsResult, onboardingResult] = await Promise.allSettled([loadUserSettings(), loadOnboarding(), loadGlobalSettings()]);
        if (requestSequence !== sequence || loadedUserId !== getUserId() || !isCurrent(generation)) {
            return state;
        }

        const settingsReady = settingsResult.status === 'fulfilled' && settingsResult.value;
        if (!settingsReady) {
            state = 'blocked';
            error = settingsResult.status === 'rejected' ? errorMessage(settingsResult.reason) : 'User settings could not be loaded';
            return state;
        }

        if (onboardingResult.status === 'rejected') {
            const cachedWelcome = findWelcome();
            if (cachedWelcome && cachedWelcome.status !== 'pending') {
                state = 'degraded';
                error = errorMessage(onboardingResult.reason);
            } else {
                state = 'blocked';
                error = errorMessage(onboardingResult.reason);
            }
            return state;
        }

        state = 'ready';
        return state;
    }

    function hasWelcomeReplay(): boolean {
        const welcome = findWelcome();
        if (!welcome) return false;
        return checkWelcomeReplay(welcome.current_version);
    }

    function resolveDestination(requestedPath: string): string {
        const requested = safeInternalPath(requestedPath);
        const welcome = findWelcome();
        if (!welcome) return requested;

        const replayingWelcome = hasWelcomeReplay();
        if (isOnboardingProgressDue(welcome) || replayingWelcome) {
            if (isWelcomePath(requested)) return requested;
            return `/welcome?returnTo=${encodeURIComponent(requested)}`;
        }
        if (isWelcomePath(requested)) return returnToFromWelcome(requested);
        return requested;
    }

    function reset(): void {
        sequence += 1;
        state = 'idle';
        error = null;
        loadedUserId = null;
    }

    return {
        get state() {
            return state;
        },
        get error() {
            return error;
        },
        get loadedUserId() {
            return loadedUserId;
        },
        get ready() {
            return state === 'ready' || state === 'degraded';
        },
        load,
        resolveDestination,
        reset,
    };
}

export const appBootstrap = createAppBootstrap();

registerClientSessionReset('appBootstrap', () => appBootstrap.reset());
