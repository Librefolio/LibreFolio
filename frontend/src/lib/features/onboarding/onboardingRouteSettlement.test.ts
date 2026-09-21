import {describe, expect, it, vi} from 'vitest';

import {createOnboardingRouteSettlementCoordinator, runOwnedOnboardingRouteSettlement, settleOnboardingRoute as plannedSettleOnboardingRoute, type OnboardingRouteSnapshot} from './onboardingRouteSettlement';

type BootstrapState = 'idle' | 'loading' | 'ready' | 'degraded' | 'blocked';

type RouteSettlementInput = {
    state: BootstrapState;
    currentPath: string;
    isWelcomeRoute: boolean;
    resolveDestination: (currentPath: string) => string;
    navigate: (destination: string, options: {replaceState: true}) => Promise<void>;
    startIntro: () => void;
};

type SettleOnboardingRoute = (input: RouteSettlementInput) => Promise<void>;
type RouteStateInput = Pick<RouteSettlementInput, 'state' | 'currentPath' | 'isWelcomeRoute'>;

const settleOnboardingRoute: SettleOnboardingRoute = plannedSettleOnboardingRoute;

function deferred<T>(): {promise: Promise<T>; resolve: (value: T) => void} {
    let resolve!: (value: T) => void;
    const promise = new Promise<T>((done) => {
        resolve = done;
    });
    return {promise, resolve};
}

function harness(destination: string) {
    const resolveDestination = vi.fn<(currentPath: string) => string>().mockReturnValue(destination);
    const navigate = vi.fn<RouteSettlementInput['navigate']>().mockResolvedValue(undefined);
    const startIntro = vi.fn<() => void>();
    const settle = (input: RouteStateInput) => settleOnboardingRoute({...input, resolveDestination, navigate, startIntro});

    return {navigate, resolveDestination, settle, startIntro};
}

describe('onboarding route settlement', () => {
    it.each(['idle', 'loading', 'blocked'] as const)('keeps %s inert', async (state) => {
        const {navigate, resolveDestination, settle, startIntro} = harness('/welcome?returnTo=%2Fdashboard');

        await settle({state, currentPath: '/dashboard', isWelcomeRoute: false});

        expect(resolveDestination).not.toHaveBeenCalled();
        expect(navigate).not.toHaveBeenCalled();
        expect(startIntro).not.toHaveBeenCalled();
    });

    it('awaits one encoded Welcome redirect from a ready dashboard', async () => {
        const destination = '/welcome?returnTo=%2Fdashboard';
        const navigation = deferred<void>();
        const {navigate, resolveDestination, settle, startIntro} = harness(destination);
        navigate.mockReturnValue(navigation.promise);

        const settlement = settle({state: 'ready', currentPath: '/dashboard', isWelcomeRoute: false});
        const completed = vi.fn<() => void>();
        void settlement.then(completed);
        await Promise.resolve();

        expect(resolveDestination).toHaveBeenCalledExactlyOnceWith('/dashboard');
        expect(navigate).toHaveBeenCalledExactlyOnceWith(destination, {replaceState: true});
        expect(completed).not.toHaveBeenCalled();
        expect(startIntro).not.toHaveBeenCalled();

        navigation.resolve(undefined);
        await settlement;

        expect(completed).toHaveBeenCalledTimes(1);
        expect(navigate).toHaveBeenCalledTimes(1);
    });

    it('redirects exactly once when a blocked attempt is retried ready', async () => {
        const destination = '/welcome?returnTo=%2Fdashboard';
        const {navigate, resolveDestination, settle, startIntro} = harness(destination);
        const input = {currentPath: '/dashboard', isWelcomeRoute: false} as const;

        await settle({state: 'blocked', ...input});
        await settle({state: 'ready', ...input});

        expect(resolveDestination).toHaveBeenCalledExactlyOnceWith('/dashboard');
        expect(navigate).toHaveBeenCalledExactlyOnceWith(destination, {replaceState: true});
        expect(startIntro).not.toHaveBeenCalled();
    });

    it('starts the intro in degraded mode when Welcome is not due and the non-Welcome destination is unchanged', async () => {
        const currentPath = '/dashboard?view=performance';
        const {navigate, resolveDestination, settle, startIntro} = harness(currentPath);

        await settle({state: 'degraded', currentPath, isWelcomeRoute: false});

        expect(resolveDestination).toHaveBeenCalledExactlyOnceWith(currentPath);
        expect(navigate).not.toHaveBeenCalled();
        expect(startIntro).toHaveBeenCalledTimes(1);
    });

    it('does not start the old-route intro or navigate again after its pending redirect completes', async () => {
        const currentPath = '/transactions?broker=17&mode=compact';
        const destination = '/welcome?returnTo=%2Ftransactions%3Fbroker%3D17%26mode%3Dcompact';
        const navigation = deferred<void>();
        const {navigate, settle, startIntro} = harness(destination);
        navigate.mockReturnValue(navigation.promise);
        const input = {state: 'ready', currentPath, isWelcomeRoute: false} as const;

        const settlement = settle(input);
        await Promise.resolve();

        expect(navigate).toHaveBeenCalledExactlyOnceWith(destination, {replaceState: true});
        expect(startIntro).not.toHaveBeenCalled();

        navigation.resolve(undefined);
        await settlement;

        expect(navigate).toHaveBeenCalledTimes(1);
        expect(startIntro).not.toHaveBeenCalled();
    });

    it('does nothing when the Welcome route is unchanged', async () => {
        const {navigate, settle, startIntro} = harness('/welcome');

        await settle({state: 'ready', currentPath: '/welcome', isWelcomeRoute: true});

        expect(navigate).not.toHaveBeenCalled();
        expect(startIntro).not.toHaveBeenCalled();
    });

    it('leaves terminal-flow navigation to Welcome when its ready destination differs', async () => {
        const currentPath = '/welcome?returnTo=%2Fdashboard';
        const {navigate, resolveDestination, settle, startIntro} = harness('/dashboard');

        await settle({state: 'ready', currentPath, isWelcomeRoute: true});

        expect(resolveDestination).not.toHaveBeenCalled();
        expect(navigate).not.toHaveBeenCalled();
        expect(startIntro).not.toHaveBeenCalled();
    });

    it('keeps bootstrap ownership through the ready reactive race', async () => {
        const readyPath = '/dashboard?view=performance';
        const destination = '/welcome?returnTo=%2Fdashboard%3Fview%3Dperformance';
        const bootstrap = deferred<BootstrapState>();
        const {navigate, resolveDestination, startIntro} = harness(destination);
        const coordinator = createOnboardingRouteSettlementCoordinator();
        const acquire = vi.spyOn(coordinator, 'acquire');
        const release = vi.spyOn(coordinator, 'release');
        const loadBootstrap = vi.fn<() => Promise<BootstrapState>>().mockReturnValue(bootstrap.promise);
        let currentPath = '/transactions?broker=17';
        const readSettlementInput = vi.fn<(state: BootstrapState) => RouteSettlementInput>((state) => ({
            state,
            currentPath,
            isWelcomeRoute: false,
            resolveDestination,
            navigate,
            startIntro,
        }));
        const readySnapshot: OnboardingRouteSnapshot = {
            state: 'ready',
            currentPath: readyPath,
            isWelcomeRoute: false,
            destination,
        };
        const reactiveAction = vi.fn<(snapshot: OnboardingRouteSnapshot) => void>();
        const claimAndReact = (snapshot: OnboardingRouteSnapshot) => {
            const claimed = coordinator.claimReactive(snapshot);
            if (claimed) {
                reactiveAction(snapshot);
            }
            return claimed;
        };
        const settlement = runOwnedOnboardingRouteSettlement({
            coordinator,
            loadBootstrap,
            readSettlementInput,
        });
        const completed = vi.fn<() => void>();
        void settlement.then(completed);

        expect(acquire).toHaveBeenCalledTimes(1);
        expect(loadBootstrap).toHaveBeenCalledTimes(1);
        expect(acquire.mock.invocationCallOrder[0]).toBeLessThan(loadBootstrap.mock.invocationCallOrder[0]);
        expect(readSettlementInput).not.toHaveBeenCalled();
        expect(release).not.toHaveBeenCalled();
        expect(completed).not.toHaveBeenCalled();

        currentPath = readyPath;
        bootstrap.resolve('ready');

        expect(readSettlementInput).not.toHaveBeenCalled();
        expect(claimAndReact(readySnapshot)).toBe(false);
        expect(navigate).not.toHaveBeenCalled();
        expect(startIntro).not.toHaveBeenCalled();
        expect(reactiveAction).not.toHaveBeenCalled();

        await settlement;

        expect(completed).toHaveBeenCalledTimes(1);
        expect(readSettlementInput).toHaveBeenCalledExactlyOnceWith('ready');
        expect(readSettlementInput).toHaveReturnedWith({
            state: 'ready',
            currentPath: readyPath,
            isWelcomeRoute: false,
            resolveDestination,
            navigate,
            startIntro,
        });
        expect(resolveDestination).toHaveBeenCalledExactlyOnceWith(readyPath);
        expect(navigate).toHaveBeenCalledExactlyOnceWith(destination, {replaceState: true});
        expect(startIntro).not.toHaveBeenCalled();
        expect(release).toHaveBeenCalledExactlyOnceWith(acquire.mock.results[0]?.value);
        expect(loadBootstrap.mock.invocationCallOrder[0]).toBeLessThan(readSettlementInput.mock.invocationCallOrder[0]);
        expect(readSettlementInput.mock.invocationCallOrder[0]).toBeLessThan(resolveDestination.mock.invocationCallOrder[0]);
        expect(resolveDestination.mock.invocationCallOrder[0]).toBeLessThan(navigate.mock.invocationCallOrder[0]);
        expect(navigate.mock.invocationCallOrder[0]).toBeLessThan(release.mock.invocationCallOrder[0]);

        expect(claimAndReact(readySnapshot)).toBe(false);
        expect(navigate).toHaveBeenCalledTimes(1);
        expect(startIntro).not.toHaveBeenCalled();
        expect(reactiveAction).not.toHaveBeenCalled();

        const laterSnapshot: OnboardingRouteSnapshot = {
            state: 'ready',
            currentPath: '/portfolio?view=allocation',
            isWelcomeRoute: false,
            destination: '/portfolio?view=allocation',
        };

        expect(claimAndReact(laterSnapshot)).toBe(true);
        expect(claimAndReact(laterSnapshot)).toBe(false);
        expect(reactiveAction).toHaveBeenCalledExactlyOnceWith(laterSnapshot);
    });
});
