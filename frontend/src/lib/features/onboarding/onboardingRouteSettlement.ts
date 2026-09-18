export type BootstrapState = 'idle' | 'loading' | 'ready' | 'degraded' | 'blocked';

export interface OnboardingRouteSettlementInput {
    state: BootstrapState;
    currentPath: string;
    isWelcomeRoute: boolean;
    resolveDestination: (currentPath: string) => string;
    navigate: (destination: string, options: {replaceState: true}) => Promise<void>;
    startIntro: () => void;
}

export interface OnboardingRouteSnapshot {
    state: BootstrapState;
    currentPath: string;
    isWelcomeRoute: boolean;
    destination: string;
}

function snapshotFromInput({state, currentPath, isWelcomeRoute, resolveDestination}: OnboardingRouteSettlementInput): OnboardingRouteSnapshot {
    return {
        state,
        currentPath,
        isWelcomeRoute,
        destination: !isWelcomeRoute && (state === 'ready' || state === 'degraded') ? resolveDestination(currentPath) : currentPath,
    };
}

function snapshotSignature({state, currentPath, isWelcomeRoute, destination}: OnboardingRouteSnapshot): string {
    return JSON.stringify([state, currentPath, isWelcomeRoute, destination]);
}

async function applySnapshot({state, currentPath, isWelcomeRoute, destination}: OnboardingRouteSnapshot, {navigate, startIntro}: Pick<OnboardingRouteSettlementInput, 'navigate' | 'startIntro'>): Promise<void> {
    if ((state !== 'ready' && state !== 'degraded') || isWelcomeRoute) return;

    if (destination !== currentPath) {
        await navigate(destination, {replaceState: true});
        return;
    }

    startIntro();
}

export async function settleOnboardingRoute(input: OnboardingRouteSettlementInput): Promise<void> {
    await applySnapshot(snapshotFromInput(input), input);
}

export interface OnboardingRouteSettlementCoordinator {
    acquire: () => number;
    release: (owner: number) => void;
    settleOwned: (owner: number, input: OnboardingRouteSettlementInput) => Promise<void>;
    claimReactive: (snapshot: OnboardingRouteSnapshot) => boolean;
}

export function createOnboardingRouteSettlementCoordinator(): OnboardingRouteSettlementCoordinator {
    let activeOwner: number | null = null;
    let nextOwner = 0;
    let handledSignature: string | null = null;

    function assertOwner(owner: number): void {
        if (activeOwner !== owner) {
            throw new Error('Onboarding route settlement owner is no longer active');
        }
    }

    return {
        acquire(): number {
            if (activeOwner !== null) {
                throw new Error('Onboarding route settlement already has an active owner');
            }
            activeOwner = ++nextOwner;
            return activeOwner;
        },
        release(owner: number): void {
            assertOwner(owner);
            activeOwner = null;
        },
        async settleOwned(owner: number, input: OnboardingRouteSettlementInput): Promise<void> {
            assertOwner(owner);
            const snapshot = snapshotFromInput(input);
            const signature = snapshotSignature(snapshot);
            if (signature === handledSignature) return;

            handledSignature = signature;
            await applySnapshot(snapshot, input);
        },
        claimReactive(snapshot: OnboardingRouteSnapshot): boolean {
            if (activeOwner !== null || (snapshot.state !== 'ready' && snapshot.state !== 'degraded')) return false;

            const signature = snapshotSignature(snapshot);
            if (signature === handledSignature) return false;

            handledSignature = signature;
            return true;
        },
    };
}

interface OwnedOnboardingRouteSettlementInput {
    coordinator: OnboardingRouteSettlementCoordinator;
    loadBootstrap: () => Promise<BootstrapState>;
    readSettlementInput: (state: BootstrapState) => OnboardingRouteSettlementInput;
}

export async function runOwnedOnboardingRouteSettlement({coordinator, loadBootstrap, readSettlementInput}: OwnedOnboardingRouteSettlementInput): Promise<void> {
    const owner = coordinator.acquire();
    try {
        const state = await loadBootstrap();
        await coordinator.settleOwned(owner, readSettlementInput(state));
    } finally {
        coordinator.release(owner);
    }
}
