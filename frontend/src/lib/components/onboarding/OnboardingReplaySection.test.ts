// @vitest-environment jsdom
/**
 * OnboardingReplaySection — component test (Vitest + jsdom).
 *
 * The Preferences "onboarding" panel: one row per `OnboardingProgressItem`
 * (welcome / intro_tour / import_guide), a per-row "Replay" button and a
 * "Replay all" button. The component is a thin orchestrator around three
 * module singletons it imports directly (not as props), so all three are
 * replaced here:
 *
 *  - `onboarding` (`$lib/stores/app/onboarding.svelte`) — the progress/replay
 *    controller. Its `progress`, `state`, `error` and `replayStorageError`
 *    become plain mutable fields on a hoisted fake, and `hasReplay` /
 *    `startReplay` / `clearReplay` become spies this file programs per test.
 *    `complete`/`skip` are also spied even though the component never calls
 *    them — that absence is exactly what "replay is display-only" asserts.
 *  - `onboardingGuide` (`$lib/features/onboarding/onboardingGuide.svelte`) —
 *    replaced with `importOriginal` + override, the same pattern
 *    `OnboardingCoachmark.test.ts` uses, so the real internals (e.g. the
 *    `INTRO_TOUR_STEP_IDS` / `IMPORT_GUIDE_STEP_IDS` constants `replayAll`
 *    uses internally to compute the first step id per flow) stay genuine
 *    while `startIntroReplay` / `prepareIntroReplay` / `startImportReplay`
 *    become spies. The per-row intro replay still goes through
 *    `startIntroReplay`; `replayAll` arms intro through `prepareIntroReplay`
 *    instead — a three-way contract (welcome via `onboarding.startReplay`,
 *    intro via `onboardingGuide.prepareIntroReplay`, import via
 *    `onboardingGuide.startImportReplay`) where only `prepareIntroReplay`
 *    does not itself activate the tour.
 *  - `appBootstrap` (`$lib/features/onboarding/appBootstrap.svelte`) — only
 *    `load` is used, by the load-error retry path.
 *  - `$app/navigation` — `goto` becomes a spy so "did it navigate to
 *    /welcome" is a call assertion, never a real route change.
 *
 * Real `svelte-i18n` is booted via `setupI18n()` (as `WelcomePage.test.ts` /
 * `OnboardingCoachmark.test.ts` do) so every `$_()` call resolves instead of
 * throwing, but no assertion below reads translated text: statuses, update
 * and "armed" badges are identified by their `data-testid`, never by the copy
 * inside them, and the one free-text assertion in this file
 * (`replayStorageError` / the load error) is a token this file itself
 * supplied through the mocked controller, not a catalogue string.
 */
import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';
import type {OnboardingFlow, OnboardingProgressItem} from '$lib/types/onboarding';

const {onboardingState, onboardingMocks, guideState, guideMocks, appBootstrapMocks} = vi.hoisted(() => ({
    onboardingState: {
        state: 'ready' as 'idle' | 'loading' | 'ready' | 'error',
        progress: null as {flows: OnboardingProgressItem[]} | null,
        error: null as string | null,
        replayStorageError: null as string | null,
    },
    onboardingMocks: {
        hasReplay: vi.fn<(flow: OnboardingFlow, version: number) => boolean>(() => false),
        startReplay: vi.fn<(flow: OnboardingFlow, version: number, stepId: string) => boolean>(() => true),
        clearReplay: vi.fn<(flow: OnboardingFlow, version: number) => void>(),
        complete: vi.fn(),
        skip: vi.fn(),
    },
    guideState: {
        error: null as string | null,
    },
    guideMocks: {
        startIntroReplay: vi.fn<() => boolean>(() => true),
        prepareIntroReplay: vi.fn<() => boolean>(() => true),
        startImportReplay: vi.fn<() => boolean>(() => true),
    },
    appBootstrapMocks: {
        load: vi.fn(async () => 'ready' as const),
    },
}));

vi.mock('$app/navigation', () => ({goto: vi.fn()}));

vi.mock('$lib/stores/app/onboarding.svelte', () => ({
    onboarding: {
        get state() {
            return onboardingState.state;
        },
        get progress() {
            return onboardingState.progress;
        },
        get error() {
            return onboardingState.error;
        },
        get replayStorageError() {
            return onboardingState.replayStorageError;
        },
        hasReplay: (...args: Parameters<typeof onboardingMocks.hasReplay>) => onboardingMocks.hasReplay(...args),
        startReplay: (...args: Parameters<typeof onboardingMocks.startReplay>) => onboardingMocks.startReplay(...args),
        clearReplay: (...args: Parameters<typeof onboardingMocks.clearReplay>) => onboardingMocks.clearReplay(...args),
        complete: (...args: unknown[]) => onboardingMocks.complete(...args),
        skip: (...args: unknown[]) => onboardingMocks.skip(...args),
    },
}));

vi.mock('$lib/features/onboarding/onboardingGuide.svelte', async (importOriginal) => {
    const actual = await importOriginal<typeof import('$lib/features/onboarding/onboardingGuide.svelte')>();
    return {
        ...actual,
        onboardingGuide: {
            get error() {
                return guideState.error;
            },
            startIntroReplay: (...args: Parameters<typeof guideMocks.startIntroReplay>) => guideMocks.startIntroReplay(...args),
            prepareIntroReplay: (...args: Parameters<typeof guideMocks.prepareIntroReplay>) => guideMocks.prepareIntroReplay(...args),
            startImportReplay: (...args: Parameters<typeof guideMocks.startImportReplay>) => guideMocks.startImportReplay(...args),
        },
    };
});

vi.mock('$lib/features/onboarding/appBootstrap.svelte', () => ({
    appBootstrap: {
        load: (...args: Parameters<typeof appBootstrapMocks.load>) => appBootstrapMocks.load(...args),
    },
}));

import {cleanup, fireEvent, render, screen, setupI18n, waitFor} from '$test/component';
import {goto} from '$app/navigation';
import OnboardingReplaySection from './OnboardingReplaySection.svelte';

const gotoMock = vi.mocked(goto);

// --- Fixtures -------------------------------------------------------------

function progressItem(over: Partial<OnboardingProgressItem> & {flow: OnboardingFlow}): OnboardingProgressItem {
    return {
        status: 'pending',
        version: 1,
        current_version: 1,
        update_available: false,
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z',
        completed_at: null,
        skipped_at: null,
        ...over,
    };
}

/** Three pending, up-to-date flows — the neutral case most tests mount with. */
function defaultFlows(): OnboardingProgressItem[] {
    return [progressItem({flow: 'welcome'}), progressItem({flow: 'intro_tour'}), progressItem({flow: 'import_guide'})];
}

function mountSection(flows: OnboardingProgressItem[] = defaultFlows()) {
    onboardingState.progress = {flows};
    return render(OnboardingReplaySection);
}

/** A promise this test resolves by hand, so "in flight" is a state it controls. */
function deferred<T>(): {promise: Promise<T>; resolve: (value: T) => void} {
    let resolve!: (value: T) => void;
    const promise = new Promise<T>((res) => {
        resolve = res;
    });
    return {promise, resolve};
}

beforeEach(async () => {
    await setupI18n();

    onboardingState.state = 'ready';
    onboardingState.progress = null;
    onboardingState.error = null;
    onboardingState.replayStorageError = null;
    guideState.error = null;

    onboardingMocks.hasReplay.mockReset().mockReturnValue(false);
    onboardingMocks.startReplay.mockReset().mockReturnValue(true);
    onboardingMocks.clearReplay.mockReset();
    onboardingMocks.complete.mockReset();
    onboardingMocks.skip.mockReset();
    guideMocks.startIntroReplay.mockReset().mockReturnValue(true);
    guideMocks.prepareIntroReplay.mockReset().mockReturnValue(true);
    guideMocks.startImportReplay.mockReset().mockReturnValue(true);
    appBootstrapMocks.load.mockReset().mockResolvedValue('ready');
    gotoMock.mockReset().mockResolvedValue(undefined);
});

afterEach(() => {
    cleanup();
});

// =========================================================================
describe('OnboardingReplaySection — rendering flows', () => {
    it('renders each provided flow with its status, version, current version and an update badge only when one is due', () => {
        mountSection([
            progressItem({flow: 'welcome', status: 'pending', version: 1, current_version: 1, update_available: false}),
            progressItem({flow: 'intro_tour', status: 'completed', version: 2, current_version: 3, update_available: true}),
            progressItem({flow: 'import_guide', status: 'skipped', version: 1, current_version: 1, update_available: false}),
        ]);

        const welcomeRow = screen.getByTestId('onboarding-flow-welcome');
        expect(welcomeRow).toHaveAttribute('data-status', 'pending');
        expect(welcomeRow).toHaveAttribute('data-version', '1');
        expect(welcomeRow).toHaveAttribute('data-current-version', '1');
        expect(screen.getByTestId('onboarding-flow-welcome-status')).toBeInTheDocument();
        expect(screen.queryByTestId('onboarding-flow-welcome-update')).toBeNull();

        const introRow = screen.getByTestId('onboarding-flow-intro_tour');
        expect(introRow).toHaveAttribute('data-status', 'completed');
        expect(introRow).toHaveAttribute('data-version', '2');
        expect(introRow).toHaveAttribute('data-current-version', '3');
        expect(screen.getByTestId('onboarding-flow-intro_tour-status')).toBeInTheDocument();
        expect(screen.getByTestId('onboarding-flow-intro_tour-update')).toBeInTheDocument();

        const importRow = screen.getByTestId('onboarding-flow-import_guide');
        expect(importRow).toHaveAttribute('data-status', 'skipped');
        expect(screen.getByTestId('onboarding-flow-import_guide-status')).toBeInTheDocument();
        expect(screen.queryByTestId('onboarding-flow-import_guide-update')).toBeNull();
    });
});

// =========================================================================
describe('OnboardingReplaySection — statuses are display-only', () => {
    it('never calls onboarding.complete/skip, and leaves the rendered status untouched, whatever the flow status is when Replay is pressed', async () => {
        mountSection([progressItem({flow: 'welcome', status: 'pending'}), progressItem({flow: 'intro_tour', status: 'completed', version: 2, current_version: 2}), progressItem({flow: 'import_guide', status: 'skipped'})]);

        await fireEvent.click(screen.getByTestId('onboarding-replay-welcome'));
        await fireEvent.click(screen.getByTestId('onboarding-replay-intro_tour'));
        await fireEvent.click(screen.getByTestId('onboarding-replay-import_guide'));

        expect(onboardingMocks.complete).not.toHaveBeenCalled();
        expect(onboardingMocks.skip).not.toHaveBeenCalled();
        expect(screen.getByTestId('onboarding-flow-welcome')).toHaveAttribute('data-status', 'pending');
        expect(screen.getByTestId('onboarding-flow-intro_tour')).toHaveAttribute('data-status', 'completed');
        expect(screen.getByTestId('onboarding-flow-import_guide')).toHaveAttribute('data-status', 'skipped');
    });
});

// =========================================================================
describe('OnboardingReplaySection — welcome replay', () => {
    it('stores a welcome replay token and navigates to /welcome', async () => {
        mountSection();

        await fireEvent.click(screen.getByTestId('onboarding-replay-welcome'));

        expect(onboardingMocks.startReplay).toHaveBeenCalledWith('welcome', 1, 'welcome');
        await waitFor(() => expect(gotoMock).toHaveBeenCalledWith('/welcome'));
    });

    it('surfaces the storage failure and never navigates when the token could not be written', async () => {
        onboardingMocks.startReplay.mockReturnValue(false);
        onboardingState.replayStorageError = 'WELCOME_STORAGE_FAILED_TOKEN';
        mountSection();

        await fireEvent.click(screen.getByTestId('onboarding-replay-welcome'));

        await waitFor(() => expect(screen.getByTestId('onboarding-replay-error')).toHaveTextContent('WELCOME_STORAGE_FAILED_TOKEN'));
        expect(gotoMock).not.toHaveBeenCalled();
    });
});

// =========================================================================
describe('OnboardingReplaySection — intro / import replay', () => {
    it('delegates intro replay to onboardingGuide.startIntroReplay and never navigates', async () => {
        mountSection();

        await fireEvent.click(screen.getByTestId('onboarding-replay-intro_tour'));

        expect(guideMocks.startIntroReplay).toHaveBeenCalledTimes(1);
        expect(onboardingMocks.startReplay).not.toHaveBeenCalled();
        expect(gotoMock).not.toHaveBeenCalled();
    });

    it('surfaces the guide error when intro replay fails to arm', async () => {
        guideMocks.startIntroReplay.mockReturnValue(false);
        guideState.error = 'INTRO_GUIDE_ERROR_TOKEN';
        mountSection();

        await fireEvent.click(screen.getByTestId('onboarding-replay-intro_tour'));

        await waitFor(() => expect(screen.getByTestId('onboarding-replay-error')).toHaveTextContent('INTRO_GUIDE_ERROR_TOKEN'));
    });

    it('arms the next import without navigating, and the armed badge appears once it succeeds', async () => {
        let importArmed = false;
        onboardingMocks.hasReplay.mockImplementation((flow) => flow === 'import_guide' && importArmed);
        guideMocks.startImportReplay.mockImplementation(() => {
            importArmed = true;
            return true;
        });
        mountSection();
        expect(screen.queryByTestId('onboarding-flow-import_guide-armed')).toBeNull();

        await fireEvent.click(screen.getByTestId('onboarding-replay-import_guide'));

        expect(guideMocks.startImportReplay).toHaveBeenCalledTimes(1);
        expect(onboardingMocks.startReplay).not.toHaveBeenCalled();
        expect(gotoMock).not.toHaveBeenCalled();
        await waitFor(() => expect(screen.getByTestId('onboarding-flow-import_guide-armed')).toBeInTheDocument());
    });
});

// =========================================================================
describe('OnboardingReplaySection — replay all', () => {
    it('arms welcome via onboarding.startReplay, intro via onboardingGuide.prepareIntroReplay, and import via onboardingGuide.startImportReplay, in that order, before navigating to /welcome', async () => {
        mountSection();

        await fireEvent.click(screen.getByTestId('onboarding-replay-all'));

        // Welcome still goes through the generic controller; intro is armed
        // (not activated) through the guide's dedicated replay-prep entry
        // point, and import through its own guide method — startIntroReplay
        // (the per-row path) is never involved in "replay all".
        expect(onboardingMocks.startReplay).toHaveBeenCalledTimes(1);
        expect(onboardingMocks.startReplay).toHaveBeenNthCalledWith(1, 'welcome', 1, 'welcome');
        expect(guideMocks.prepareIntroReplay).toHaveBeenCalledTimes(1);
        expect(guideMocks.startImportReplay).toHaveBeenCalledTimes(1);
        expect(guideMocks.startIntroReplay).not.toHaveBeenCalled();

        await waitFor(() => expect(gotoMock).toHaveBeenCalledWith('/welcome'));
        expect(guideMocks.prepareIntroReplay.mock.invocationCallOrder[0]).toBeGreaterThan(onboardingMocks.startReplay.mock.invocationCallOrder[0]);
        expect(guideMocks.startImportReplay.mock.invocationCallOrder[0]).toBeGreaterThan(guideMocks.prepareIntroReplay.mock.invocationCallOrder[0]);
        expect(gotoMock.mock.invocationCallOrder[0]).toBeGreaterThan(guideMocks.startImportReplay.mock.invocationCallOrder[0]);
    });

    it('rolls back the tokens already written when import fails to arm, and surfaces the failure', async () => {
        // Welcome and intro_tour arm successfully; import_guide's own guide
        // method is the one that fails, so it never made it into `started`.
        guideMocks.startImportReplay.mockImplementation(() => {
            onboardingState.replayStorageError = 'STORAGE_FULL_TOKEN';
            return false;
        });
        mountSection();

        await fireEvent.click(screen.getByTestId('onboarding-replay-all'));

        await waitFor(() => expect(screen.getByTestId('onboarding-replay-error')).toHaveTextContent('STORAGE_FULL_TOKEN'));
        // Rollback always goes through onboarding.clearReplay, even for the
        // intro_tour token that was actually armed via onboardingGuide —
        // the component tracks "started" by flow/version, not by which arm
        // method wrote it.
        expect(onboardingMocks.clearReplay).toHaveBeenCalledTimes(2);
        expect(onboardingMocks.clearReplay).toHaveBeenNthCalledWith(1, 'welcome', 1);
        expect(onboardingMocks.clearReplay).toHaveBeenNthCalledWith(2, 'intro_tour', 1);
        expect(onboardingMocks.startReplay).toHaveBeenCalledTimes(1);
        expect(guideMocks.prepareIntroReplay).toHaveBeenCalledTimes(1);
        expect(gotoMock).not.toHaveBeenCalled();
    });
});

// =========================================================================
describe('OnboardingReplaySection — busy state', () => {
    it('disables every replay control while a replay is in flight, and re-enables them once it settles', async () => {
        const nav = deferred<void>();
        gotoMock.mockReturnValue(nav.promise as ReturnType<typeof goto>);
        mountSection();

        const replayAllButton = screen.getByTestId('onboarding-replay-all');
        await fireEvent.click(replayAllButton);

        await waitFor(() => expect(screen.getByTestId('onboarding-replay-section')).toHaveAttribute('data-busy', 'true'));
        expect(screen.getByTestId('onboarding-replay-section')).toHaveAttribute('aria-busy', 'true');
        expect(replayAllButton).toBeDisabled();
        expect(screen.getByTestId('onboarding-replay-welcome')).toBeDisabled();
        expect(screen.getByTestId('onboarding-replay-intro_tour')).toBeDisabled();
        expect(screen.getByTestId('onboarding-replay-import_guide')).toBeDisabled();

        nav.resolve();
        await waitFor(() => expect(screen.getByTestId('onboarding-replay-section')).toHaveAttribute('data-busy', 'false'));
        expect(replayAllButton).toBeEnabled();
        expect(screen.getByTestId('onboarding-replay-welcome')).toBeEnabled();
    });

    it('disables "Replay all" when there is nothing to replay', () => {
        mountSection([]);

        expect(screen.getByTestId('onboarding-replay-all')).toBeDisabled();
    });
});

// =========================================================================
describe('OnboardingReplaySection — onboarding load failure', () => {
    it('shows a retry control instead of the flow list when onboarding failed to load with nothing cached', () => {
        onboardingState.state = 'error';
        onboardingState.error = 'LOAD_FAILED_TOKEN';
        onboardingState.progress = null;
        render(OnboardingReplaySection);

        expect(screen.getByTestId('onboarding-replay-load-error')).toHaveTextContent('LOAD_FAILED_TOKEN');
        expect(screen.getByTestId('onboarding-replay-retry')).toBeInTheDocument();
        expect(screen.queryByTestId('onboarding-flow-welcome')).toBeNull();
        expect(screen.queryByTestId('onboarding-flow-intro_tour')).toBeNull();
        expect(screen.queryByTestId('onboarding-flow-import_guide')).toBeNull();
    });

    it('calls appBootstrap.load(true) on retry, disabling the control while the reload is pending', async () => {
        const boot = deferred<'ready'>();
        appBootstrapMocks.load.mockReturnValue(boot.promise);
        onboardingState.state = 'error';
        onboardingState.progress = null;
        render(OnboardingReplaySection);

        const retry = screen.getByTestId('onboarding-replay-retry');
        await fireEvent.click(retry);

        expect(appBootstrapMocks.load).toHaveBeenCalledWith(true);
        await waitFor(() => expect(retry).toBeDisabled());

        boot.resolve('ready');
        await waitFor(() => expect(retry).toBeEnabled());
    });
});

// =========================================================================
describe('OnboardingReplaySection — armed badges', () => {
    it('shows the armed badge only for the flow(s) where onboarding.hasReplay reports a stored token', () => {
        onboardingMocks.hasReplay.mockImplementation((flow) => flow === 'welcome');
        mountSection();

        expect(onboardingMocks.hasReplay).toHaveBeenCalledWith('welcome', 1);
        expect(screen.getByTestId('onboarding-flow-welcome-armed')).toBeInTheDocument();
        expect(screen.queryByTestId('onboarding-flow-intro_tour-armed')).toBeNull();
        expect(screen.queryByTestId('onboarding-flow-import_guide-armed')).toBeNull();
    });
});
