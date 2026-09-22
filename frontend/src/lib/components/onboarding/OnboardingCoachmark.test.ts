// @vitest-environment jsdom
/**
 * OnboardingCoachmark — accessible/responsive coachmark panel.
 *
 * `$app/environment`'s `browser` is aliased to `false` for the whole test suite
 * (see `vitest.config.ts`), which is correct for the ~190 node-environment tests
 * but would make every effect in this component a no-op here — it would never
 * compute `anchorRect`, never link `aria-describedby`, never focus the panel.
 * Overriding it to `true` for this file is the same pattern already used by
 * `chartSettingsStore.test.ts` and `ModalBase.test.ts`.
 */
import {afterAll, afterEach, beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';
import {tick} from 'svelte';
import {isCheckpointFlow, type GuideStepId, type GuidedOnboardingFlow} from '$lib/features/onboarding/onboardingGuideCatalog';

vi.mock('$app/environment', () => ({browser: true, dev: true, building: false, version: 'test'}));

const {translateKey} = vi.hoisted(() => ({
    translateKey: vi.fn((key: string, _options?: unknown) => `i18n:${key}`),
}));

vi.mock('$lib/i18n', async (importOriginal) => {
    const actual = await importOriginal<typeof import('$lib/i18n')>();
    const {derived, writable} = await import('svelte/store');
    const locale = writable('en');
    const translator = (key: string, options?: unknown) => translateKey(key, options);
    const messages = derived(locale, () => translator);
    return {...actual, locale, _: messages, t: messages};
});

/**
 * `onboardingGuide` (the module singleton `OnboardingOverlayHost` imports) is
 * replaced with a plain, test-owned object rather than driven through its real
 * factory: state is a mutable snapshot and host actions are spies. This avoids
 * reaching into controller/replay/storage machinery (covered in
 * `onboarding.test.ts`) while this file verifies presentation and depth policy.
 * `INTRO_TOUR_STEP_IDS` and the rest of the module are left real via
 * `importOriginal`, so the semantic step ids stay the actual ones.
 */
const {fakeGuideState} = vi.hoisted(() => ({
    fakeGuideState: {
        active: null as {
            flow: GuidedOnboardingFlow;
            version: number;
            stepId: GuideStepId;
            mode: 'automatic' | 'replay';
            progress?: {current: number; total: number};
        } | null,
        error: null as string | null,
        actionPending: false,
    },
}));

vi.mock('$lib/features/onboarding/onboardingGuide.svelte', async (importOriginal) => {
    const actual = await importOriginal<typeof import('$lib/features/onboarding/onboardingGuide.svelte')>();
    return {
        ...actual,
        onboardingGuide: {
            get active() {
                return fakeGuideState.active;
            },
            get error() {
                return fakeGuideState.error;
            },
            get actionPending() {
                return fakeGuideState.actionPending;
            },
            maybeStartIntro: vi.fn(() => false),
            startIntroReplay: vi.fn(() => false),
            startImportAt: vi.fn(() => false),
            startImportReplay: vi.fn(() => false),
            armReplay: vi.fn(() => false),
            setStep: vi.fn(),
            next: vi.fn(),
            previous: vi.fn(),
            nextIntro: vi.fn(),
            previousIntro: vi.fn(),
            queueContextual: vi.fn(),
            maybeStartQueued: vi.fn(() => false),
            clearQueued: vi.fn(),
            dismissHost: vi.fn(),
            suspend: vi.fn(),
            finish: vi.fn(async () => undefined),
            exit: vi.fn(async () => true),
            skip: vi.fn(async () => false),
            navigateAfterFinish: vi.fn(async () => {}),
            reset: vi.fn(),
        },
    };
});

import {cleanup, fireEvent, render, screen, setupI18n, waitFor, within} from '$test/component';
import OnboardingCoachmark from './OnboardingCoachmark.svelte';
import OnboardingOverlayHost from './OnboardingOverlayHost.svelte';
import DeferredAppPopups from './DeferredAppPopups.svelte';
import {donationPopup} from '$lib/stores/app/donationPopupStore.svelte';
import {updateAvailable} from '$lib/features/update-check/updateCheckStore.svelte';
import {guideAnchors} from '$lib/features/onboarding/guideAnchors.svelte';
import {onboardingTourSurfaces} from '$lib/features/onboarding/onboardingTourSurfaces.svelte';
import {onboardingGuide} from '$lib/features/onboarding/onboardingGuide.svelte';

interface MatchMediaOptions {
    mobile?: boolean;
    reducedMotion?: boolean;
}

/** Routes `window.matchMedia` by query, the only signal the component reads for
 *  both the mobile bottom-sheet layout and the reduced-motion scroll behaviour. */
function stubMatchMedia({mobile = false, reducedMotion = false}: MatchMediaOptions = {}) {
    window.matchMedia = ((query: string) => ({
        matches: query.includes('max-width') ? mobile : query.includes('prefers-reduced-motion') ? reducedMotion : false,
        media: query,
        onchange: null,
        addListener() {},
        removeListener() {},
        addEventListener() {},
        removeEventListener() {},
        dispatchEvent: () => false,
    })) as typeof window.matchMedia;
}

function makeAnchor(bounds: DOMRect = rect(96, 96, 120, 44)): HTMLElement {
    const anchor = document.createElement('button');
    anchor.type = 'button';
    anchor.textContent = 'anchor target';
    vi.spyOn(anchor, 'getBoundingClientRect').mockReturnValue(bounds);
    document.body.appendChild(anchor);
    return anchor;
}

/**
 * The same anchor, still out of the document.
 *
 * `refreshPosition` treats a disconnected element exactly like a missing one,
 * so the panel stalls with the prop already in place, and `appendChild` alone
 * then heals it — no prop change, no re-render. That matters: the host hands
 * the anchor over through a `$derived`, and the effect that owns
 * `onstall`/`onstallend` never reads `anchor`, so in production its only trigger
 * is the geometry settling. Driving recovery through `rerender` instead would
 * replace the whole props object and re-run that effect a couple of frames
 * *before* anything settled — a test-harness artifact, not something the host
 * can produce.
 */
function makeUnmountedAnchor(bounds: DOMRect = rect(96, 96, 120, 44)): HTMLElement {
    const anchor = document.createElement('button');
    anchor.type = 'button';
    anchor.textContent = 'anchor target';
    vi.spyOn(anchor, 'getBoundingClientRect').mockReturnValue(bounds);
    return anchor;
}

function rect(left: number, top: number, width: number, height: number): DOMRect {
    return {
        x: left,
        y: top,
        left,
        top,
        right: left + width,
        bottom: top + height,
        width,
        height,
        toJSON: () => ({}),
    } as DOMRect;
}

async function expectAnchored(): Promise<HTMLElement> {
    const root = screen.getByTestId('onboarding-coachmark');
    await waitFor(() => expect(root).toHaveAttribute('data-guide-state', 'anchored'));
    await waitFor(() => expect(root).toHaveAttribute('data-target-stable', 'true'));
    return root;
}

async function expectStableGeometry(): Promise<HTMLElement> {
    const root = await expectAnchored();
    await waitFor(() => expect(root).toHaveAttribute('data-geometry-state', 'stable'));
    return root;
}

async function advanceCoachmarkFrames(count = 6): Promise<void> {
    await tick();
    for (let frame = 0; frame < count; frame += 1) {
        vi.advanceTimersToNextFrame();
        await tick();
    }
}

/**
 * Brings a mounted coachmark to the *settled, healthy* step — the only state in
 * which the panel-fade deadline is the single thing on the clock.
 *
 * `targetStable` is reachable only through two matching `requestAnimationFrame`
 * measurements (`measureUntilStable`), so a fake-timer block that wants a healthy
 * step has to fake `requestAnimationFrame` as well and step it; `vi.useFakeTimers()`
 * with no `toFake` list does exactly that. Those steps move the very clock the
 * fade is armed on, which is why callers anchor their deadline assertions to an
 * absolute instant (`advanceFakeClockTo`) rather than to a delta.
 *
 * The three attributes are asserted, not assumed: a step that silently failed to
 * settle parks in `waiting`, arms the *stall* deadline instead of the fade, and
 * would quietly turn a fade test into a stall test.
 */
async function settleCoachmarkGeometry(): Promise<HTMLElement> {
    await advanceCoachmarkFrames();
    const root = screen.getByTestId('onboarding-coachmark');
    expect(root).toHaveAttribute('data-guide-state', 'anchored');
    expect(root).toHaveAttribute('data-target-stable', 'true');
    expect(root).toHaveAttribute('data-geometry-state', 'stable');
    return root;
}

/**
 * Advances one frame at a time until an unanchored panel reports itself anchored
 * again, and returns the exact instant on the fake clock at which that happened.
 *
 * `settleCoachmarkGeometry` advances a fixed number of frames, so the clock it
 * leaves behind sits *after* the recovery instant by however many frames were
 * spare. That is harmless when asserting a deadline has already passed and fatal
 * when asserting one has not: the panel fade is re-armed by the recovery itself,
 * so its 2,999ms boundary can only be named from the instant the recovery
 * happened, not from a frame budget that overshot it.
 *
 * The condition is `anchored` + `data-target-stable`, and deliberately *not*
 * `data-geometry-state === 'stable'`. The component clears `stalled` — and
 * therefore re-arms the fade — on `Boolean(anchorRect) && targetStable`, while
 * `stable` is a later and re-entrant condition: `scheduleStableMeasurement`
 * pushes geometry back to `revalidating` and re-counts two matching frames, so
 * it is reached two frames after the panel is already anchored (measured: the
 * step anchors at +3,024ms and geometry reports `stable` at +3,056ms). Naming
 * the geometry instant would put the deadline 32ms late and turn the 2,999ms
 * assertion into an off-by-two-frames red that says nothing about the fade.
 *
 * The opening guard is what makes the returned instant a *transition*: this
 * helper may only be used on a panel that is currently not anchored.
 */
async function advanceToRecoveryInstant(maxFrames = 10): Promise<number> {
    const root = screen.getByTestId('onboarding-coachmark');
    expect(root).not.toHaveAttribute('data-guide-state', 'anchored');
    for (let frame = 0; frame < maxFrames; frame += 1) {
        vi.advanceTimersToNextFrame();
        await tick();
        const anchored = root.getAttribute('data-guide-state') === 'anchored' && root.getAttribute('data-target-stable') === 'true';
        if (anchored) return Date.now();
    }
    throw new Error(`coachmark never re-anchored within ${maxFrames} frames`);
}

/**
 * Advances the fake clock *to* an absolute instant on it, never *by* a duration.
 *
 * A deadline assertion can then name the instant the component actually promises
 * ("2,999ms after this panel opened") no matter how much of that same budget the
 * test already spent settling geometry. The guard turns an overrun into a red
 * instead of a silently meaningless zero-length advance.
 */
async function advanceFakeClockTo(instant: number): Promise<void> {
    const remaining = instant - Date.now();
    expect(remaining).toBeGreaterThanOrEqual(0);
    await vi.advanceTimersByTimeAsync(remaining);
}

const DESCRIPTION_ID = 'onboarding-coachmark-description';

/** The single message line, addressed by the id the panel publishes through
 *  `aria-describedby` — never by "some text somewhere on screen". */
function coachmarkMessage(): HTMLElement {
    const message = document.getElementById(DESCRIPTION_ID);
    expect(message).not.toBeNull();
    return message as HTMLElement;
}

const originalMatchMedia = window.matchMedia;

beforeEach(async () => {
    await setupI18n();
    vi.clearAllMocks();
    stubMatchMedia();
});

afterEach(() => {
    cleanup();
    guideAnchors.clear();
    onboardingTourSurfaces.closeAll();
    fakeGuideState.active = null;
    fakeGuideState.error = null;
    fakeGuideState.actionPending = false;
    window.matchMedia = originalMatchMedia;
    vi.restoreAllMocks();
    document.body.innerHTML = '';
});

describe('OnboardingCoachmark — guide state', () => {
    it('is "waiting" (and shows the busy label) when there is no anchor yet', () => {
        render(OnboardingCoachmark, {
            props: {
                open: true,
                anchor: null,
                stepId: 'step-1',
                title: 'Title',
                description: 'Description',
                busyLabel: 'BUSY_LABEL_TOKEN',
            },
        });

        const root = screen.getByTestId('onboarding-coachmark');
        expect(root).toHaveAttribute('data-guide-state', 'waiting');
        expect(root).toHaveAttribute('data-geometry-state', 'waiting');
        expect(screen.queryByTestId('onboarding-coachmark-highlight')).toBeNull();
        expect(screen.getByText('BUSY_LABEL_TOKEN')).toBeInTheDocument();
    });

    it('is "anchored" only after a connected target is stable, and renders an explicitly requested highlight', async () => {
        const anchor = makeAnchor();
        render(OnboardingCoachmark, {
            props: {
                open: true,
                anchor,
                stepId: 'step-1',
                title: 'Title',
                description: 'DESCRIPTION_TOKEN',
                highlight: 'pulse',
            },
        });

        const root = await expectStableGeometry();
        expect(screen.getByTestId('onboarding-coachmark-highlight')).toBeInTheDocument();
        expect(screen.getByText('DESCRIPTION_TOKEN')).toBeInTheDocument();
        expect(root).toHaveAttribute('data-highlight', 'pulse');
    });

    it('keeps the last valid geometry visible while revalidating an ancestor transition', async () => {
        const navigation = document.createElement('nav');
        const anchor = document.createElement('button');
        anchor.type = 'button';
        navigation.appendChild(anchor);
        document.body.appendChild(navigation);
        let playState: AnimationPlayState = 'finished';
        Object.defineProperty(navigation, 'getAnimations', {
            configurable: true,
            value: () => [{playState}] as unknown as Animation[],
        });
        let currentRect = rect(40, 50, 100, 40);
        vi.spyOn(anchor, 'getBoundingClientRect').mockImplementation(() => currentRect);

        render(OnboardingCoachmark, {
            props: {
                open: true,
                anchor,
                stepId: 'step-1',
                title: 'Title',
                description: 'STABLE_DESCRIPTION_TOKEN',
                busyLabel: 'WAITING_LABEL_TOKEN',
                focusOnOpen: false,
                highlight: 'pulse',
            },
        });

        await expectStableGeometry();
        const highlight = screen.getByTestId('onboarding-coachmark-highlight');
        expect(highlight).toHaveStyle({left: '34px', top: '44px', width: '112px', height: '52px'});

        currentRect = rect(200, 160, 120, 50);
        playState = 'running';
        navigation.dispatchEvent(new Event('transitionrun'));
        await waitFor(() => expect(screen.getByTestId('onboarding-coachmark')).toHaveAttribute('data-geometry-state', 'revalidating'));
        expect(screen.getByTestId('onboarding-coachmark')).toHaveAttribute('data-guide-state', 'anchored');
        expect(screen.getByTestId('onboarding-coachmark')).toHaveAttribute('data-target-stable', 'true');
        expect(screen.getByTestId('onboarding-coachmark-highlight')).toBeInTheDocument();
        expect(screen.getByText('STABLE_DESCRIPTION_TOKEN')).toBeInTheDocument();
        expect(screen.queryByText('WAITING_LABEL_TOKEN')).toBeNull();

        playState = 'finished';
        navigation.dispatchEvent(new Event('transitionend'));

        await waitFor(() => expect(screen.getByTestId('onboarding-coachmark-highlight')).toHaveStyle({left: '194px', top: '154px', width: '132px', height: '62px'}));
        await waitFor(() => expect(screen.getByTestId('onboarding-coachmark')).toHaveAttribute('data-geometry-state', 'stable'));
    });

    it('ignores unrelated modal-content scroll without a waiting-label flash or rect change', async () => {
        const scrollRoot = document.createElement('div');
        scrollRoot.dataset.guideScrollRoot = '';
        const anchor = document.createElement('button');
        const unrelatedModalContent = document.createElement('div');
        unrelatedModalContent.className = 'modal-content';
        vi.spyOn(anchor, 'getBoundingClientRect').mockReturnValue(rect(120, 180, 140, 48));
        scrollRoot.appendChild(anchor);
        document.body.append(scrollRoot, unrelatedModalContent);

        render(OnboardingCoachmark, {
            props: {
                open: true,
                anchor,
                stepId: 'step-scroll',
                title: 'Title',
                description: 'STABLE_DESCRIPTION_TOKEN',
                busyLabel: 'WAITING_LABEL_TOKEN',
                pointer: 'cursor',
                highlight: 'pulse',
            },
        });

        const root = await expectStableGeometry();
        const before = screen.getByTestId('onboarding-coachmark-highlight').getAttribute('style');
        unrelatedModalContent.dispatchEvent(new Event('scroll'));
        await tick();

        expect(root).toHaveAttribute('data-geometry-state', 'stable');
        expect(root).toHaveAttribute('data-target-stable', 'true');
        expect(screen.getByTestId('onboarding-coachmark-highlight').getAttribute('style')).toBe(before);
        expect(screen.getByTestId('onboarding-coachmark-pointer')).toBeInTheDocument();
        expect(screen.getByText('STABLE_DESCRIPTION_TOKEN')).toBeInTheDocument();
        expect(screen.queryByText('WAITING_LABEL_TOKEN')).toBeNull();
    });

    it('tracks the explicit Transaction Form body scroll root and updates the highlight without a waiting-state flash', async () => {
        vi.useFakeTimers();
        try {
            const modal = document.createElement('div');
            const formBody = document.createElement('div');
            formBody.dataset.testid = 'tx-form-body';
            formBody.dataset.guideScrollRoot = '';
            const anchor = document.createElement('button');
            let currentRect = rect(120, 180, 140, 48);
            vi.spyOn(anchor, 'getBoundingClientRect').mockImplementation(() => currentRect);
            formBody.appendChild(anchor);
            modal.appendChild(formBody);
            document.body.appendChild(modal);

            render(OnboardingCoachmark, {
                props: {
                    open: true,
                    anchor,
                    stepId: 'transaction.create.details',
                    title: 'Title',
                    description: 'STABLE_DESCRIPTION_TOKEN',
                    busyLabel: 'WAITING_LABEL_TOKEN',
                    focusOnOpen: false,
                    highlight: 'pulse',
                },
            });

            await advanceCoachmarkFrames();
            const root = screen.getByTestId('onboarding-coachmark');
            const highlight = screen.getByTestId('onboarding-coachmark-highlight');
            expect(screen.getByTestId('tx-form-body')).toBe(formBody);
            expect(root).toHaveAttribute('data-guide-state', 'anchored');
            expect(root).toHaveAttribute('data-geometry-state', 'stable');
            expect(highlight).toHaveStyle({left: '114px', top: '174px', width: '152px', height: '60px'});

            currentRect = rect(120, 104, 140, 48);
            formBody.dispatchEvent(new Event('scroll'));
            await tick();

            expect(root).toHaveAttribute('data-guide-state', 'anchored');
            expect(root).toHaveAttribute('data-geometry-state', 'revalidating');
            expect(root).toHaveAttribute('data-target-stable', 'true');
            expect(highlight).toHaveStyle({left: '114px', top: '98px', width: '152px', height: '60px'});
            expect(screen.getByText('STABLE_DESCRIPTION_TOKEN')).toBeInTheDocument();
            expect(screen.queryByText('WAITING_LABEL_TOKEN')).toBeNull();

            await advanceCoachmarkFrames(2);
            expect(root).toHaveAttribute('data-geometry-state', 'stable');
        } finally {
            cleanup();
            vi.useRealTimers();
        }
    });

    it('tracks the nearest computed-overflow ancestor instead of a farther scroll container, without hiding stable geometry', async () => {
        vi.useFakeTimers();
        try {
            const outerScroll = document.createElement('div');
            outerScroll.style.overflowY = 'auto';
            const nearestScroll = document.createElement('div');
            nearestScroll.style.overflowY = 'scroll';
            const anchor = document.createElement('button');
            let currentRect = rect(260, 300, 100, 40);
            vi.spyOn(anchor, 'getBoundingClientRect').mockImplementation(() => currentRect);
            nearestScroll.appendChild(anchor);
            outerScroll.appendChild(nearestScroll);
            document.body.appendChild(outerScroll);

            render(OnboardingCoachmark, {
                props: {
                    open: true,
                    anchor,
                    stepId: 'transaction.create.save',
                    title: 'Title',
                    description: 'STABLE_DESCRIPTION_TOKEN',
                    busyLabel: 'WAITING_LABEL_TOKEN',
                    focusOnOpen: false,
                    highlight: 'pulse',
                },
            });

            await advanceCoachmarkFrames();
            const root = screen.getByTestId('onboarding-coachmark');
            const highlight = screen.getByTestId('onboarding-coachmark-highlight');
            expect(root).toHaveAttribute('data-geometry-state', 'stable');
            expect(highlight).toHaveStyle({left: '254px', top: '294px', width: '112px', height: '52px'});

            currentRect = rect(210, 190, 100, 40);
            outerScroll.dispatchEvent(new Event('scroll'));
            await tick();
            expect(highlight).toHaveStyle({left: '254px', top: '294px', width: '112px', height: '52px'});

            nearestScroll.dispatchEvent(new Event('scroll'));
            await tick();
            expect(root).toHaveAttribute('data-guide-state', 'anchored');
            expect(root).toHaveAttribute('data-geometry-state', 'revalidating');
            expect(root).toHaveAttribute('data-target-stable', 'true');
            expect(highlight).toHaveStyle({left: '204px', top: '184px', width: '112px', height: '52px'});
            expect(screen.queryByText('WAITING_LABEL_TOKEN')).toBeNull();

            await advanceCoachmarkFrames(2);
            expect(root).toHaveAttribute('data-geometry-state', 'stable');
        } finally {
            cleanup();
            vi.useRealTimers();
        }
    });

    it('keeps cursor and highlight waiting while the nearest modal ancestor is animating', async () => {
        const modal = document.createElement('div');
        modal.className = 'modal-content';
        const anchor = document.createElement('button');
        let playState: AnimationPlayState = 'running';
        let movingLeft = 140;
        vi.spyOn(anchor, 'getBoundingClientRect').mockImplementation(() => rect(playState === 'running' ? movingLeft++ : 200, 120, 100, 40));
        Object.defineProperty(modal, 'getAnimations', {
            configurable: true,
            value: () => [{playState}] as unknown as Animation[],
        });
        modal.appendChild(anchor);
        document.body.appendChild(modal);

        render(OnboardingCoachmark, {
            props: {
                open: true,
                anchor,
                stepId: 'step-1',
                title: 'Title',
                description: 'Description',
                pointer: 'cursor',
                highlight: 'pulse',
            },
        });

        expect(screen.getByTestId('onboarding-coachmark')).toHaveAttribute('data-guide-state', 'waiting');
        expect(screen.getByTestId('onboarding-coachmark')).toHaveAttribute('data-target-stable', 'false');
        expect(screen.queryByTestId('onboarding-coachmark-pointer')).toBeNull();
        expect(screen.queryByTestId('onboarding-coachmark-highlight')).toBeNull();
        await new Promise<void>((resolve) => requestAnimationFrame(() => requestAnimationFrame(() => resolve())));
        expect(screen.getByTestId('onboarding-coachmark')).toHaveAttribute('data-target-stable', 'false');

        playState = 'finished';
        modal.dispatchEvent(new Event('transitionend'));
        await expectStableGeometry();
        expect(screen.getByTestId('onboarding-coachmark-pointer')).toBeInTheDocument();
        expect(screen.getByTestId('onboarding-coachmark-highlight')).toBeInTheDocument();
    });

    it('is "error" whenever an error is supplied, overriding both waiting and anchored', () => {
        const anchor = makeAnchor();
        render(OnboardingCoachmark, {
            props: {
                open: true,
                anchor,
                stepId: 'step-1',
                title: 'Title',
                description: 'DESCRIPTION_TOKEN',
                error: 'ERROR_TOKEN',
            },
        });

        const root = screen.getByTestId('onboarding-coachmark');
        expect(root).toHaveAttribute('data-guide-state', 'error');
        expect(screen.getByText('ERROR_TOKEN')).toBeInTheDocument();
        expect(screen.queryByText('DESCRIPTION_TOKEN')).toBeNull();
    });

    it('an anchor that disconnects reports no rect at all (closed, not merely empty)', () => {
        const anchor = document.createElement('div'); // never appended to document.body
        render(OnboardingCoachmark, {
            props: {
                open: true,
                anchor,
                stepId: 'step-1',
                title: 'Title',
                description: 'Description',
            },
        });

        expect(screen.getByTestId('onboarding-coachmark')).toHaveAttribute('data-guide-state', 'waiting');
    });
});

describe('OnboardingCoachmark — ARIA linkage and restoration', () => {
    it('links the anchor to the panel description while open, and unlinks it when it closes', async () => {
        const anchor = makeAnchor();
        const view = render(OnboardingCoachmark, {
            props: {
                open: true,
                anchor,
                stepId: 'step-1',
                title: 'Title',
                description: 'Description',
            },
        });

        expect(anchor.getAttribute('aria-describedby')).toBe(DESCRIPTION_ID);

        await view.rerender({
            open: false,
            anchor,
            stepId: 'step-1',
            title: 'Title',
            description: 'Description',
        });

        expect(anchor.getAttribute('aria-describedby')).toBeNull();
    });

    it('the panel exposes the standard dialog wiring to the title and description', () => {
        const anchor = makeAnchor();
        render(OnboardingCoachmark, {
            props: {
                open: true,
                anchor,
                stepId: 'step-1',
                title: 'Title',
                description: 'Description',
            },
        });

        const panel = screen.getByTestId('onboarding-coachmark-panel');
        expect(panel).toHaveAttribute('role', 'dialog');
        expect(panel).toHaveAttribute('aria-describedby', DESCRIPTION_ID);
        expect(panel.getAttribute('aria-labelledby')).toBe('onboarding-coachmark-title');
    });
});

describe('OnboardingCoachmark — close controls suspend, never skip', () => {
    it('Escape calls onclose and never onskip while open', async () => {
        const onclose = vi.fn();
        const onskip = vi.fn();
        render(OnboardingCoachmark, {
            props: {
                open: true,
                anchor: makeAnchor(),
                stepId: 'step-1',
                title: 'Title',
                description: 'Description',
                onclose,
                onskip,
            },
        });

        await fireEvent.keyDown(window, {key: 'Escape'});

        expect(onclose).toHaveBeenCalledTimes(1);
        expect(onskip).not.toHaveBeenCalled();
    });

    it('ignores Escape entirely while closed', async () => {
        const onclose = vi.fn();
        render(OnboardingCoachmark, {
            props: {
                open: false,
                anchor: null,
                stepId: 'step-1',
                title: 'Title',
                description: 'Description',
                onclose,
            },
        });

        await fireEvent.keyDown(window, {key: 'Escape'});

        expect(onclose).not.toHaveBeenCalled();
    });

    it('a different key while open calls neither onclose nor onskip', async () => {
        const onclose = vi.fn();
        const onskip = vi.fn();
        render(OnboardingCoachmark, {
            props: {
                open: true,
                anchor: makeAnchor(),
                stepId: 'step-1',
                title: 'Title',
                description: 'Description',
                onclose,
                onskip,
            },
        });

        await fireEvent.keyDown(window, {key: 'Enter'});

        expect(onclose).not.toHaveBeenCalled();
        expect(onskip).not.toHaveBeenCalled();
    });
});

describe('OnboardingCoachmark — action placement and callbacks', () => {
    it('fires exactly the callback for the button clicked, and only that one', async () => {
        const onnext = vi.fn();
        const onback = vi.fn();
        const onskip = vi.fn();
        const onclose = vi.fn();
        render(OnboardingCoachmark, {
            props: {
                open: true,
                anchor: makeAnchor(),
                stepId: 'step-1',
                title: 'Title',
                description: 'Description',
                onnext,
                onback,
                onskip,
                onclose,
            },
        });

        await fireEvent.click(screen.getByTestId('onboarding-coachmark-next'));
        expect(onnext).toHaveBeenCalledTimes(1);
        expect(onback).not.toHaveBeenCalled();
        expect(onskip).not.toHaveBeenCalled();
        expect(onclose).not.toHaveBeenCalled();

        await fireEvent.click(screen.getByTestId('onboarding-coachmark-back'));
        expect(onback).toHaveBeenCalledTimes(1);

        await fireEvent.click(screen.getByTestId('onboarding-coachmark-skip'));
        expect(onskip).toHaveBeenCalledTimes(1);

        await fireEvent.click(screen.getByTestId('onboarding-coachmark-close'));
        expect(onclose).toHaveBeenCalledTimes(1);

        // Closing only suspends the guide; it must never also count as the
        // permanent backend skip, and vice versa.
        expect(onskip).toHaveBeenCalledTimes(1);
    });

    it('omits a control entirely (not just visually) when its show flag is false', () => {
        render(OnboardingCoachmark, {
            props: {
                open: true,
                anchor: makeAnchor(),
                stepId: 'step-1',
                title: 'Title',
                description: 'Description',
                showBack: false,
                showSkip: false,
                showClose: false,
            },
        });

        expect(screen.queryByTestId('onboarding-coachmark-back')).toBeNull();
        expect(screen.queryByTestId('onboarding-coachmark-skip')).toBeNull();
        expect(screen.queryByTestId('onboarding-coachmark-close')).toBeNull();
        expect(screen.getByTestId('onboarding-coachmark-next')).toBeInTheDocument();
    });

    it('keeps permanent Skip and close in the top action row, with Skip before close', () => {
        render(OnboardingCoachmark, {
            props: {
                open: true,
                anchor: makeAnchor(),
                stepId: 'step-1',
                title: 'Title',
                description: 'Description',
            },
        });

        const topActions = screen.getByTestId('onboarding-coachmark-top-actions');
        const skip = within(topActions).getByTestId('onboarding-coachmark-skip');
        const close = within(topActions).getByTestId('onboarding-coachmark-close');
        expect(within(topActions).getAllByRole('button')).toEqual([skip, close]);
        expect(skip.querySelector('svg')).not.toBeNull();
        expect(close.querySelector('svg')).not.toBeNull();
    });

    it('keeps Back on the left and Next on the right in footer DOM order', () => {
        render(OnboardingCoachmark, {
            props: {
                open: true,
                anchor: makeAnchor(),
                stepId: 'step-1',
                title: 'Title',
                description: 'Description',
            },
        });

        const navigation = screen.getByTestId('onboarding-coachmark-navigation');
        const back = within(navigation).getByTestId('onboarding-coachmark-back');
        const next = within(navigation).getByTestId('onboarding-coachmark-next');
        expect(within(navigation).getAllByRole('button')).toEqual([back, next]);
        expect(back.querySelector('svg')).not.toBeNull();
        expect(next.querySelector('svg')).not.toBeNull();
    });
});

describe('OnboardingCoachmark — real target activation', () => {
    it('observes one real target click in capture only when advanceOnTarget is enabled', async () => {
        const anchor = makeAnchor();
        const ontargetactivate = vi.fn();
        const view = render(OnboardingCoachmark, {
            props: {
                open: true,
                anchor,
                stepId: 'contextual-action',
                title: 'Title',
                description: 'Description',
                advanceOnTarget: true,
                ontargetactivate,
            },
        });

        await expectAnchored();
        await fireEvent.click(anchor);
        expect(ontargetactivate).toHaveBeenCalledTimes(1);

        await view.rerender({
            open: true,
            anchor,
            stepId: 'contextual-action',
            title: 'Title',
            description: 'Description',
            advanceOnTarget: false,
            ontargetactivate,
        });
        await tick();
        await fireEvent.click(anchor);
        expect(ontargetactivate).toHaveBeenCalledTimes(1);
    });
});

/**
 * OnboardingCoachmark — message opacity lifecycle.
 *
 * The subject here is `PANEL_FADE_MS`: the *aesthetic* 3-second dimming that runs
 * on every step. It is deliberately exercised on a **settled, healthy** step,
 * because that is the only situation in which the fade is what the panel is
 * waiting for. A step whose anchor never resolves arms `GUIDE_STALL_MS` on the
 * same deadline and the fade is then suppressed on purpose — a failure message is
 * never dimmed. That case belongs to the stall block below, not here.
 *
 * Settling therefore has to happen before the clock is advanced, and it costs
 * part of the budget under test (two animation frames minimum), so every deadline
 * assertion is anchored to an absolute instant on the fake clock.
 */
describe('OnboardingCoachmark — message opacity lifecycle', () => {
    it('keeps the base panel fresh through 2,999ms and subdues it at 3,000ms', async () => {
        vi.useFakeTimers();
        try {
            const openedAt = Date.now();
            render(OnboardingCoachmark, {
                props: {
                    open: true,
                    anchor: makeAnchor(),
                    stepId: 'opacity-step-1',
                    title: 'Title',
                    description: 'Description',
                },
            });
            const panel = screen.getByTestId('onboarding-coachmark-panel');
            expect(panel).toHaveAttribute('data-subdued', 'false');

            await settleCoachmarkGeometry();
            expect(panel).toHaveAttribute('data-subdued', 'false');

            await advanceFakeClockTo(openedAt + 2_999);
            expect(panel).toHaveAttribute('data-subdued', 'false');

            await advanceFakeClockTo(openedAt + 3_000);
            expect(panel).toHaveAttribute('data-subdued', 'true');
        } finally {
            cleanup();
            vi.useRealTimers();
        }
    });

    it('restores opacity for hover/focus, then immediately re-subdues on leave/blur without another timer', async () => {
        vi.useFakeTimers();
        try {
            const openedAt = Date.now();
            render(OnboardingCoachmark, {
                props: {
                    open: true,
                    anchor: makeAnchor(),
                    stepId: 'opacity-step-1',
                    title: 'Title',
                    description: 'Description',
                },
            });
            const panel = screen.getByTestId('onboarding-coachmark-panel');
            await settleCoachmarkGeometry();
            await advanceFakeClockTo(openedAt + 3_000);
            expect(panel).toHaveAttribute('data-subdued', 'true');
            const timersAtBase = vi.getTimerCount();

            await fireEvent.mouseEnter(panel);
            expect(panel).toHaveAttribute('data-subdued', 'false');
            await fireEvent.mouseLeave(panel);
            await tick();
            expect(panel).toHaveAttribute('data-subdued', 'true');
            expect(vi.getTimerCount()).toBe(timersAtBase);

            const close = screen.getByTestId('onboarding-coachmark-close');
            await fireEvent.focusIn(close);
            expect(panel).toHaveAttribute('data-subdued', 'false');
            await fireEvent.focusOut(close, {relatedTarget: document.body});
            await tick();
            expect(panel).toHaveAttribute('data-subdued', 'true');
            expect(vi.getTimerCount()).toBe(timersAtBase);
        } finally {
            cleanup();
            vi.useRealTimers();
        }
    });

    it('resets the base state and the full 3-second deadline when the step or error changes', async () => {
        vi.useFakeTimers();
        try {
            const anchor = makeAnchor();
            const openedAt = Date.now();
            const view = render(OnboardingCoachmark, {
                props: {
                    open: true,
                    anchor,
                    stepId: 'opacity-step-1',
                    title: 'Title',
                    description: 'Description',
                },
            });
            await settleCoachmarkGeometry();
            await advanceFakeClockTo(openedAt + 3_000);
            expect(screen.getByTestId('onboarding-coachmark-panel')).toHaveAttribute('data-subdued', 'true');

            await view.rerender({
                open: true,
                anchor,
                stepId: 'opacity-step-2',
                title: 'Title',
                description: 'Description',
            });
            const steppedAt = Date.now();
            expect(screen.getByTestId('onboarding-coachmark-panel')).toHaveAttribute('data-subdued', 'false');
            // The new step inherits the geometry that is already settled (the
            // measurement effect keys on the anchor, not on the step id), so the
            // only deadline left on the clock is still the fade's.
            expect(screen.getByTestId('onboarding-coachmark')).toHaveAttribute('data-guide-state', 'anchored');

            await advanceFakeClockTo(steppedAt + 2_999);
            expect(screen.getByTestId('onboarding-coachmark-panel')).toHaveAttribute('data-subdued', 'false');
            await advanceFakeClockTo(steppedAt + 3_000);
            expect(screen.getByTestId('onboarding-coachmark-panel')).toHaveAttribute('data-subdued', 'true');

            await view.rerender({
                open: true,
                anchor,
                stepId: 'opacity-step-2',
                title: 'Title',
                description: 'Description',
                error: 'OWNED_ERROR_TOKEN',
            });
            const erroredAt = Date.now();
            expect(screen.getByTestId('onboarding-coachmark-panel')).toHaveAttribute('data-subdued', 'false');

            await advanceFakeClockTo(erroredAt + 3_000);
            expect(screen.getByTestId('onboarding-coachmark-panel')).toHaveAttribute('data-subdued', 'true');
        } finally {
            cleanup();
            vi.useRealTimers();
        }
    });

    it('keeps the same timer and interaction state under reduced motion', async () => {
        vi.useFakeTimers();
        try {
            stubMatchMedia({reducedMotion: true});
            const openedAt = Date.now();
            render(OnboardingCoachmark, {
                props: {
                    open: true,
                    anchor: makeAnchor(),
                    stepId: 'opacity-reduced-motion',
                    title: 'Title',
                    description: 'Description',
                },
            });
            const panel = screen.getByTestId('onboarding-coachmark-panel');
            expect(panel).toHaveAttribute('data-subdued', 'false');

            await settleCoachmarkGeometry();
            await advanceFakeClockTo(openedAt + 2_999);
            expect(panel).toHaveAttribute('data-subdued', 'false');

            await advanceFakeClockTo(openedAt + 3_000);
            expect(panel).toHaveAttribute('data-subdued', 'true');

            await fireEvent.mouseEnter(panel);
            expect(panel).toHaveAttribute('data-subdued', 'false');
            await fireEvent.mouseLeave(panel);
            expect(panel).toHaveAttribute('data-subdued', 'true');
        } finally {
            cleanup();
            vi.useRealTimers();
        }
    });
});

/**
 * OnboardingCoachmark — anchor stall (Round 7).
 *
 * The failure this block exists for could not be seen before: a step whose anchor
 * never resolved sat in `waiting` forever, showing the busy label, while the
 * aesthetic fade dimmed it after 3s and made the dead end look like loading. The
 * user had nothing to wait for and, on `import_guide`, not even a forward control.
 *
 * `GUIDE_STALL_MS` and `PANEL_FADE_MS` are both 3,000ms and deliberately distinct:
 * the fade is cosmetic and runs on every step, the stall is diagnostic and runs
 * only while the step is unsettled. They land on the same instant, which is why
 * every assertion below is on `data-guide-state` / `data-subdued` / the message
 * element rather than on "what the panel looks like at 3 seconds".
 *
 * Every test fakes the full timer set, because reaching *or leaving* the stalled
 * state means driving `requestAnimationFrame` as well, and anchors its deadline
 * assertions to an absolute instant on that one clock.
 */
describe('OnboardingCoachmark — anchor stall', () => {
    const STALL_PROPS = {
        open: true,
        anchor: null,
        stepId: 'stall-step-1',
        title: 'Title',
        description: 'DESCRIPTION_TOKEN',
        busyLabel: 'BUSY_LABEL_TOKEN',
        stalledLabel: 'STALLED_LABEL_TOKEN',
    } as const;

    it('stays "waiting" through 2,999ms and turns "stalled" at 3,000ms when the anchor never resolves', async () => {
        vi.useFakeTimers();
        try {
            const openedAt = Date.now();
            render(OnboardingCoachmark, {props: {...STALL_PROPS}});
            await tick();

            const root = screen.getByTestId('onboarding-coachmark');
            expect(root).toHaveAttribute('data-guide-state', 'waiting');
            // The precondition, not an inference: the target really never resolved.
            expect(root).toHaveAttribute('data-target-stable', 'false');

            await advanceFakeClockTo(openedAt + 2_999);
            expect(root).toHaveAttribute('data-guide-state', 'waiting');

            await advanceFakeClockTo(openedAt + 3_000);
            expect(root).toHaveAttribute('data-guide-state', 'stalled');
            expect(root).toHaveAttribute('data-target-stable', 'false');
        } finally {
            cleanup();
            vi.useRealTimers();
        }
    });

    it('never dims the stalled message, at the fade deadline or long after it', async () => {
        vi.useFakeTimers();
        try {
            const openedAt = Date.now();
            render(OnboardingCoachmark, {props: {...STALL_PROPS, stepId: 'stall-step-subdued'}});
            await tick();
            const panel = screen.getByTestId('onboarding-coachmark-panel');

            await advanceFakeClockTo(openedAt + 3_000);
            expect(screen.getByTestId('onboarding-coachmark')).toHaveAttribute('data-guide-state', 'stalled');
            expect(panel).toHaveAttribute('data-subdued', 'false');

            // The fade must not reclaim the panel later either: a failure message
            // that fades out is the illusion Round 7 removed.
            await advanceFakeClockTo(openedAt + 12_000);
            expect(screen.getByTestId('onboarding-coachmark')).toHaveAttribute('data-guide-state', 'stalled');
            expect(panel).toHaveAttribute('data-subdued', 'false');
        } finally {
            cleanup();
            vi.useRealTimers();
        }
    });

    it('replaces both the busy label and the description with the stalled label', async () => {
        vi.useFakeTimers();
        try {
            const openedAt = Date.now();
            render(OnboardingCoachmark, {props: {...STALL_PROPS, stepId: 'stall-step-message'}});
            await tick();
            expect(coachmarkMessage()).toHaveTextContent('BUSY_LABEL_TOKEN');

            await advanceFakeClockTo(openedAt + 3_000);

            expect(coachmarkMessage()).toHaveTextContent('STALLED_LABEL_TOKEN');
            expect(screen.queryByText('BUSY_LABEL_TOKEN')).toBeNull();
            expect(screen.queryByText('DESCRIPTION_TOKEN')).toBeNull();
        } finally {
            cleanup();
            vi.useRealTimers();
        }
    });

    it('calls onstall once for a stalled step and never again while it stays stalled', async () => {
        vi.useFakeTimers();
        try {
            const onstall = vi.fn();
            const openedAt = Date.now();
            render(OnboardingCoachmark, {props: {...STALL_PROPS, stepId: 'stall-step-callback', onstall}});
            await tick();
            expect(onstall).not.toHaveBeenCalled();

            await advanceFakeClockTo(openedAt + 3_000);
            expect(onstall).toHaveBeenCalledTimes(1);

            await advanceFakeClockTo(openedAt + 15_000);
            expect(onstall).toHaveBeenCalledTimes(1);
            expect(screen.getByTestId('onboarding-coachmark')).toHaveAttribute('data-guide-state', 'stalled');
        } finally {
            cleanup();
            vi.useRealTimers();
        }
    });

    it('self-heals when the anchor arrives late, and hands the panel back to the fade', async () => {
        vi.useFakeTimers();
        try {
            const onstall = vi.fn();
            const openedAt = Date.now();
            const view = render(OnboardingCoachmark, {props: {...STALL_PROPS, stepId: 'stall-step-heal', onstall}});
            await tick();

            await advanceFakeClockTo(openedAt + 3_000);
            const root = screen.getByTestId('onboarding-coachmark');
            const panel = screen.getByTestId('onboarding-coachmark-panel');
            expect(root).toHaveAttribute('data-guide-state', 'stalled');
            expect(onstall).toHaveBeenCalledTimes(1);

            // The anchor finally mounts. `guideState` checks `anchored` before
            // `stalled`, so a late target wins over the diagnosis it caused.
            await view.rerender({...STALL_PROPS, stepId: 'stall-step-heal', anchor: makeAnchor(), onstall});
            await settleCoachmarkGeometry();

            expect(coachmarkMessage()).toHaveTextContent('DESCRIPTION_TOKEN');
            expect(screen.queryByText('STALLED_LABEL_TOKEN')).toBeNull();
            expect(onstall).toHaveBeenCalledTimes(1);

            // `stalled` no longer suppresses the fade: the healed step dims like
            // any other healthy step, on a deadline armed at the moment it healed.
            expect(panel).toHaveAttribute('data-subdued', 'false');
            const healedAt = Date.now();
            await advanceFakeClockTo(healedAt + 3_000);
            expect(panel).toHaveAttribute('data-subdued', 'true');
            expect(root).toHaveAttribute('data-guide-state', 'anchored');
        } finally {
            cleanup();
            vi.useRealTimers();
        }
    });

    it('never stalls a settled step, which still dims at its own 3,000ms', async () => {
        vi.useFakeTimers();
        try {
            const onstall = vi.fn();
            const openedAt = Date.now();
            render(OnboardingCoachmark, {
                props: {...STALL_PROPS, stepId: 'stall-step-healthy', anchor: makeAnchor(), onstall},
            });
            const root = await settleCoachmarkGeometry();
            const panel = screen.getByTestId('onboarding-coachmark-panel');

            await advanceFakeClockTo(openedAt + 3_000);
            expect(root).toHaveAttribute('data-guide-state', 'anchored');
            expect(panel).toHaveAttribute('data-subdued', 'true');
            expect(coachmarkMessage()).toHaveTextContent('DESCRIPTION_TOKEN');
            expect(onstall).not.toHaveBeenCalled();

            await advanceFakeClockTo(openedAt + 12_000);
            expect(root).toHaveAttribute('data-guide-state', 'anchored');
            expect(onstall).not.toHaveBeenCalled();
        } finally {
            cleanup();
            vi.useRealTimers();
        }
    });

    it('holds the stall deadline while suspended and restarts it on resume', async () => {
        vi.useFakeTimers();
        try {
            const onstall = vi.fn();
            const openedAt = Date.now();
            const view = render(OnboardingCoachmark, {
                props: {...STALL_PROPS, stepId: 'stall-step-suspended', suspended: true, onstall},
            });
            await tick();
            const root = screen.getByTestId('onboarding-coachmark');

            // A modal is over the guide: the step is not failing, it is parked.
            await advanceFakeClockTo(openedAt + 12_000);
            expect(root).toHaveAttribute('data-guide-state', 'waiting');
            expect(onstall).not.toHaveBeenCalled();

            await view.rerender({...STALL_PROPS, stepId: 'stall-step-suspended', suspended: false, onstall});
            const resumedAt = Date.now();

            await advanceFakeClockTo(resumedAt + 2_999);
            expect(root).toHaveAttribute('data-guide-state', 'waiting');
            expect(onstall).not.toHaveBeenCalled();

            await advanceFakeClockTo(resumedAt + 3_000);
            expect(root).toHaveAttribute('data-guide-state', 'stalled');
            expect(onstall).toHaveBeenCalledTimes(1);
        } finally {
            cleanup();
            vi.useRealTimers();
        }
    });

    it('never arms the stall deadline while an error is displayed', async () => {
        vi.useFakeTimers();
        try {
            const onstall = vi.fn();
            const openedAt = Date.now();
            render(OnboardingCoachmark, {
                props: {...STALL_PROPS, stepId: 'stall-step-error-first', error: 'ERROR_TOKEN', onstall},
            });
            await tick();

            await advanceFakeClockTo(openedAt + 12_000);
            expect(screen.getByTestId('onboarding-coachmark')).toHaveAttribute('data-guide-state', 'error');
            expect(coachmarkMessage()).toHaveTextContent('ERROR_TOKEN');
            expect(onstall).not.toHaveBeenCalled();
        } finally {
            cleanup();
            vi.useRealTimers();
        }
    });

    it('lets an error arriving after a stall take precedence over the stalled message', async () => {
        vi.useFakeTimers();
        try {
            const onstall = vi.fn();
            const openedAt = Date.now();
            const view = render(OnboardingCoachmark, {props: {...STALL_PROPS, stepId: 'stall-step-error-later', onstall}});
            await tick();

            await advanceFakeClockTo(openedAt + 3_000);
            expect(screen.getByTestId('onboarding-coachmark')).toHaveAttribute('data-guide-state', 'stalled');
            expect(onstall).toHaveBeenCalledTimes(1);

            await view.rerender({...STALL_PROPS, stepId: 'stall-step-error-later', error: 'ERROR_TOKEN', onstall});
            const erroredAt = Date.now();
            expect(screen.getByTestId('onboarding-coachmark')).toHaveAttribute('data-guide-state', 'error');
            expect(coachmarkMessage()).toHaveTextContent('ERROR_TOKEN');
            expect(screen.queryByText('STALLED_LABEL_TOKEN')).toBeNull();

            await advanceFakeClockTo(erroredAt + 12_000);
            expect(screen.getByTestId('onboarding-coachmark')).toHaveAttribute('data-guide-state', 'error');
            expect(onstall).toHaveBeenCalledTimes(1);
        } finally {
            cleanup();
            vi.useRealTimers();
        }
    });

    it('clears a previous stall when the step changes and gives the new step a fresh deadline', async () => {
        vi.useFakeTimers();
        try {
            const onstall = vi.fn();
            const openedAt = Date.now();
            const view = render(OnboardingCoachmark, {props: {...STALL_PROPS, stepId: 'stall-step-first', onstall}});
            await tick();

            await advanceFakeClockTo(openedAt + 3_000);
            const root = screen.getByTestId('onboarding-coachmark');
            expect(root).toHaveAttribute('data-guide-state', 'stalled');
            expect(onstall).toHaveBeenCalledTimes(1);

            await view.rerender({...STALL_PROPS, stepId: 'stall-step-second', onstall});
            const steppedAt = Date.now();
            expect(root).toHaveAttribute('data-guide-state', 'waiting');
            expect(coachmarkMessage()).toHaveTextContent('BUSY_LABEL_TOKEN');

            await advanceFakeClockTo(steppedAt + 2_999);
            expect(root).toHaveAttribute('data-guide-state', 'waiting');
            expect(onstall).toHaveBeenCalledTimes(1);

            await advanceFakeClockTo(steppedAt + 3_000);
            expect(root).toHaveAttribute('data-guide-state', 'stalled');
            expect(onstall).toHaveBeenCalledTimes(2);
        } finally {
            cleanup();
            vi.useRealTimers();
        }
    });

    it('hides the action hint while stalled and restores it once the target resolves', async () => {
        vi.useFakeTimers();
        try {
            const openedAt = Date.now();
            const view = render(OnboardingCoachmark, {
                props: {...STALL_PROPS, stepId: 'stall-step-hint', actionHint: 'ACTION_HINT_TOKEN'},
            });
            await tick();
            expect(screen.queryByTestId('onboarding-coachmark-action-hint')).toBeNull();

            await advanceFakeClockTo(openedAt + 3_000);
            expect(screen.getByTestId('onboarding-coachmark')).toHaveAttribute('data-guide-state', 'stalled');
            expect(screen.queryByTestId('onboarding-coachmark-action-hint')).toBeNull();

            // The absence above means "not while stalled", not "this panel never
            // renders a hint" — the same props produce one as soon as it anchors.
            await view.rerender({...STALL_PROPS, stepId: 'stall-step-hint', actionHint: 'ACTION_HINT_TOKEN', anchor: makeAnchor()});
            await settleCoachmarkGeometry();
            expect(screen.getByTestId('onboarding-coachmark-action-hint')).toHaveTextContent('ACTION_HINT_TOKEN');
        } finally {
            cleanup();
            vi.useRealTimers();
        }
    });
});

/**
 * OnboardingCoachmark — stall end protocol (Round 7 follow-up).
 *
 * The coachmark always cleared its own `stalled` once the geometry settled, but
 * nothing told the host, which kept `stalledStepId` set for the rest of the
 * step's life. A recovered step therefore read "use the wizard action" in its
 * message while its own button still said "continue anyway" — and, worse, that
 * button still routed through `skip()`, persisting as *skipped* a step the user
 * could by then actually perform. `onstallend` is the missing edge.
 *
 * The decision this block encodes is "return fully to normal": label, arrow and
 * the ordinary forward action all come back, because recovery is already a
 * visible transition (the description returns, the highlight and pointer
 * appear) and a control that disagreed with the text would be the contradiction
 * the fix exists to remove.
 *
 * Every test here asserts `onstallend` is *transition*-driven rather than
 * state-driven, and that the transition it reports is **the end of the stalled
 * state, whatever ended it** — settled, suspended, step changed, error raised,
 * component destroyed. It is deliberately not "the anchor became available":
 * gating the edge on settlement leaves the stall able to end silently (a modal
 * parks the step, the panel drops its own `stalled`, and the later settle finds
 * nothing left to report), which is the original defect displaced by one step.
 * So the positives below include ends that are not good news, and the single
 * negative is the one case where no stall ever existed — nothing to report.
 *
 * The edge is fired from the effect's **teardown**, which is what puts destroy
 * on the list: the body never runs on unmount, the cleanup always does. The
 * counts below are the check on that move — the cleanup runs before the body on
 * every re-run, so each of these ends must still be reported exactly once and
 * in the same place as when the body announced them.
 */
describe('OnboardingCoachmark — stall end protocol', () => {
    const RECOVERY_PROPS = {
        open: true,
        anchor: null,
        stepId: 'recover-step-1',
        title: 'Title',
        description: 'DESCRIPTION_TOKEN',
        busyLabel: 'BUSY_LABEL_TOKEN',
        stalledLabel: 'STALLED_LABEL_TOKEN',
    } as const;

    it('calls onstallend exactly once when a late target settles a stalled step, and never stalls again', async () => {
        vi.useFakeTimers();
        try {
            const onstall = vi.fn();
            const onstallend = vi.fn();
            const openedAt = Date.now();
            const anchor = makeUnmountedAnchor();
            render(OnboardingCoachmark, {props: {...RECOVERY_PROPS, stepId: 'recover-step-once', anchor, onstall, onstallend}});
            await tick();

            await advanceFakeClockTo(openedAt + 3_000);
            const root = screen.getByTestId('onboarding-coachmark');
            expect(root).toHaveAttribute('data-guide-state', 'stalled');
            expect(onstall).toHaveBeenCalledTimes(1);
            expect(onstallend).not.toHaveBeenCalled();

            // The target finally lands in the document. Nothing else changes:
            // the measurement loop is still running because the geometry never
            // stabilised, so it picks the element up on its own.
            document.body.appendChild(anchor);
            await settleCoachmarkGeometry();

            expect(onstallend).toHaveBeenCalledTimes(1);
            expect(onstall).toHaveBeenCalledTimes(1);

            // The effect that owns both callbacks keeps re-running on ordinary
            // geometry churn for the rest of the step's life. A target that
            // really moves — the published centre is the proof it moved, not an
            // assumption that the resize did something — must not read as a
            // second recovery: clearing `stalled` before the callback is what
            // makes this an edge rather than a repeated "still settled" report.
            expect(root).toHaveAttribute('data-target-center-x', '156');
            vi.spyOn(anchor, 'getBoundingClientRect').mockReturnValue(rect(300, 200, 100, 40));
            window.dispatchEvent(new Event('resize'));
            await advanceCoachmarkFrames();
            expect(root).toHaveAttribute('data-target-center-x', '350');

            const settledAt = Date.now();
            await advanceFakeClockTo(settledAt + 12_000);
            expect(onstallend).toHaveBeenCalledTimes(1);
            expect(onstall).toHaveBeenCalledTimes(1);
            expect(root).toHaveAttribute('data-guide-state', 'anchored');
        } finally {
            cleanup();
            vi.useRealTimers();
        }
    });

    it('settles twice but recovers once: the settle no stall preceded is silent', async () => {
        vi.useFakeTimers();
        try {
            const onstall = vi.fn();
            const onstallend = vi.fn();
            const openedAt = Date.now();
            const anchor = makeAnchor();
            render(OnboardingCoachmark, {props: {...RECOVERY_PROPS, stepId: 'recover-step-transition', anchor, onstall, onstallend}});
            const root = await settleCoachmarkGeometry();
            const panel = screen.getByTestId('onboarding-coachmark-panel');

            // First settle: healthy from the first frame. Both deadlines are
            // allowed to pass and the fade actually fires, which is what proves
            // the clock ran and the effects executed — without it "onstallend was
            // not called" would be just as true of a component doing nothing.
            await advanceFakeClockTo(openedAt + 3_000);
            expect(panel).toHaveAttribute('data-subdued', 'true');
            await advanceFakeClockTo(openedAt + 9_000);
            expect(root).toHaveAttribute('data-guide-state', 'anchored');
            expect(onstall).not.toHaveBeenCalled();
            expect(onstallend).not.toHaveBeenCalled();

            // The target leaves the document, the way a wizard CTA unmounts
            // under a step that is still on screen.
            anchor.remove();
            window.dispatchEvent(new Event('resize'));
            await advanceCoachmarkFrames();
            expect(root).toHaveAttribute('data-guide-state', 'waiting');
            expect(root).toHaveAttribute('data-target-stable', 'false');
            expect(onstallend).not.toHaveBeenCalled();

            const unanchoredAt = Date.now();
            await advanceFakeClockTo(unanchoredAt + 3_000);
            expect(root).toHaveAttribute('data-guide-state', 'stalled');
            expect(onstall).toHaveBeenCalledTimes(1);
            expect(onstallend).not.toHaveBeenCalled();

            // Second settle, this one *after* a stall: same instance, same
            // callback, same settled condition — and now it fires. That is the
            // whole difference between a transition and a state, and the first
            // half of the test is what stops the negative passing vacuously.
            document.body.appendChild(anchor);
            await settleCoachmarkGeometry();
            expect(onstallend).toHaveBeenCalledTimes(1);
            expect(onstall).toHaveBeenCalledTimes(1);
        } finally {
            cleanup();
            vi.useRealTimers();
        }
    });

    it('hands the recovered step back to the normal panel, fade deadline included', async () => {
        vi.useFakeTimers();
        try {
            const onstallend = vi.fn();
            const openedAt = Date.now();
            const anchor = makeUnmountedAnchor();
            render(OnboardingCoachmark, {
                props: {...RECOVERY_PROPS, stepId: 'recover-step-panel', actionHint: 'ACTION_HINT_TOKEN', highlight: 'pulse', pointer: 'cursor', anchor, onstallend},
            });
            await tick();
            const root = screen.getByTestId('onboarding-coachmark');
            const panel = screen.getByTestId('onboarding-coachmark-panel');

            await advanceFakeClockTo(openedAt + 3_000);
            expect(root).toHaveAttribute('data-guide-state', 'stalled');
            expect(coachmarkMessage()).toHaveTextContent('STALLED_LABEL_TOKEN');
            expect(screen.queryByTestId('onboarding-coachmark-action-hint')).toBeNull();
            expect(screen.queryByTestId('onboarding-coachmark-highlight')).toBeNull();
            expect(screen.queryByTestId('onboarding-coachmark-pointer')).toBeNull();
            expect(panel).toHaveAttribute('data-subdued', 'false');

            document.body.appendChild(anchor);
            const healedAt = await advanceToRecoveryInstant();

            // Everything the stall took away comes back together: the step's own
            // description instead of the stalled label, the action hint, and the
            // two things that tell the user *where* to act. The highlight and the
            // pointer are asserted because "return fully to normal" is a claim
            // about what the user sees, not about an attribute.
            expect(onstallend).toHaveBeenCalledTimes(1);
            expect(root).toHaveAttribute('data-guide-state', 'anchored');
            expect(coachmarkMessage()).toHaveTextContent('DESCRIPTION_TOKEN');
            expect(screen.queryByText('STALLED_LABEL_TOKEN')).toBeNull();
            expect(screen.getByTestId('onboarding-coachmark-action-hint')).toHaveTextContent('ACTION_HINT_TOKEN');
            expect(screen.getByTestId('onboarding-coachmark-highlight')).toBeVisible();
            expect(screen.getByTestId('onboarding-coachmark-pointer')).toBeVisible();

            // The fade is armed by the recovery itself, not left over from the
            // open: 2,999ms after the step re-anchored the panel is still at full
            // strength, and it dims one millisecond later. Naming the instant is
            // what separates "the stall stopped suppressing the fade" from "the
            // fade happened to have fired at some point".
            expect(panel).toHaveAttribute('data-subdued', 'false');
            await advanceFakeClockTo(healedAt + 2_999);
            expect(panel).toHaveAttribute('data-subdued', 'false');
            await advanceFakeClockTo(healedAt + 3_000);
            expect(panel).toHaveAttribute('data-subdued', 'true');
            expect(root).toHaveAttribute('data-guide-state', 'anchored');
        } finally {
            cleanup();
            vi.useRealTimers();
        }
    });

    it('reports the end of a stall the step change caused, with nothing settled anywhere', async () => {
        vi.useFakeTimers();
        try {
            const onstall = vi.fn();
            const onstallend = vi.fn();
            const openedAt = Date.now();
            const view = render(OnboardingCoachmark, {props: {...RECOVERY_PROPS, stepId: 'recover-step-before', onstall, onstallend}});
            await tick();
            const root = screen.getByTestId('onboarding-coachmark');

            await advanceFakeClockTo(openedAt + 3_000);
            expect(root).toHaveAttribute('data-guide-state', 'stalled');
            expect(onstall).toHaveBeenCalledTimes(1);
            expect(onstallend).not.toHaveBeenCalled();

            // The flow moves on while the target is still nowhere: no anchor, no
            // settlement, no good news. The callback fires anyway, and it is
            // right to — the fact the host mirrors is "this step is stalled",
            // and that fact has just stopped being true. The panel agrees, which
            // is why the state is asserted next to the count: an edge nobody can
            // see in the DOM would be an edge nobody can trust.
            await view.rerender({...RECOVERY_PROPS, stepId: 'recover-step-after', onstall, onstallend});
            const changedAt = Date.now();
            expect(root).toHaveAttribute('data-guide-state', 'waiting');
            expect(onstallend).toHaveBeenCalledTimes(1);
            expect(onstall).toHaveBeenCalledTimes(1);

            // The new step gets a full fresh deadline, and re-stalling is not a
            // second recovery: one edge per stall that ends, never one per
            // effect run. `rerender` replaces the whole props object, so the
            // effect re-runs whichever prop changed — that is not a distortion
            // here, because the contract is deliberately reason-agnostic and the
            // claim under test is the count of ends, not their cause.
            await advanceFakeClockTo(changedAt + 2_999);
            expect(root).toHaveAttribute('data-guide-state', 'waiting');
            expect(onstall).toHaveBeenCalledTimes(1);

            await advanceFakeClockTo(changedAt + 3_000);
            expect(root).toHaveAttribute('data-guide-state', 'stalled');
            expect(onstall).toHaveBeenCalledTimes(2);
            expect(onstallend).toHaveBeenCalledTimes(1);
        } finally {
            cleanup();
            vi.useRealTimers();
        }
    });

    it('reports the end of a stall a modal caused, so the step that works on resume cannot inherit the hatch', async () => {
        vi.useFakeTimers();
        try {
            const onstall = vi.fn();
            const onstallend = vi.fn();
            const openedAt = Date.now();
            const anchor = makeUnmountedAnchor();
            const view = render(OnboardingCoachmark, {props: {...RECOVERY_PROPS, stepId: 'recover-step-parked', anchor, onstall, onstallend}});
            await tick();
            const root = screen.getByTestId('onboarding-coachmark');

            await advanceFakeClockTo(openedAt + 3_000);
            expect(root).toHaveAttribute('data-guide-state', 'stalled');
            expect(onstall).toHaveBeenCalledTimes(1);
            expect(onstallend).not.toHaveBeenCalled();

            // A modal parks the guide. The panel drops its own stalled state
            // here whether anyone is told or not — this is the exact instant at
            // which two owners of one fact would begin to drift, and the only
            // instant at which the host can still be told about this stall.
            await view.rerender({...RECOVERY_PROPS, stepId: 'recover-step-parked', anchor, suspended: true, onstall, onstallend});
            expect(root).toHaveAttribute('data-guide-state', 'waiting');
            expect(onstallend).toHaveBeenCalledTimes(1);

            // The modal closes and only *then* does the target appear. Under a
            // settlement-gated edge this order was unreachable: the stall had
            // already been cleared by the suspend, so the settle found nothing
            // to report and the hatch outlived the failure that justified it.
            await view.rerender({...RECOVERY_PROPS, stepId: 'recover-step-parked', anchor, suspended: false, onstall, onstallend});
            const resumedAt = Date.now();
            document.body.appendChild(anchor);
            await settleCoachmarkGeometry();

            expect(root).toHaveAttribute('data-guide-state', 'anchored');
            expect(coachmarkMessage()).toHaveTextContent('DESCRIPTION_TOKEN');
            expect(screen.queryByText('STALLED_LABEL_TOKEN')).toBeNull();
            expect(onstallend).toHaveBeenCalledTimes(1);

            // The step now works and stays working: no second stall to re-raise
            // a hatch on it, and no second recovery papering over a missing one.
            await advanceFakeClockTo(resumedAt + 12_000);
            expect(root).toHaveAttribute('data-guide-state', 'anchored');
            expect(onstall).toHaveBeenCalledTimes(1);
            expect(onstallend).toHaveBeenCalledTimes(1);
        } finally {
            cleanup();
            vi.useRealTimers();
        }
    });

    it('reports the end of a stall an error caused, and arms a fresh deadline only once the error clears', async () => {
        vi.useFakeTimers();
        try {
            const onstall = vi.fn();
            const onstallend = vi.fn();
            const openedAt = Date.now();
            const view = render(OnboardingCoachmark, {props: {...RECOVERY_PROPS, stepId: 'recover-step-errored', onstall, onstallend}});
            await tick();
            const root = screen.getByTestId('onboarding-coachmark');

            await advanceFakeClockTo(openedAt + 3_000);
            expect(root).toHaveAttribute('data-guide-state', 'stalled');
            expect(onstall).toHaveBeenCalledTimes(1);
            expect(onstallend).not.toHaveBeenCalled();

            // The fourth way a stall can end, and the only one that is worse
            // news than the stall: an error takes the panel over. The stalled
            // state really has ended — the message is the error now — so the
            // edge fires, and the host clears `stalledStepId` on it. What the
            // host should *do* about that is a product question (the escape
            // hatch is withdrawn for as long as the error shows, on the one
            // step whose forward control exists only while stalled); this test
            // pins the coachmark half so any answer to it stays deliberate.
            await view.rerender({...RECOVERY_PROPS, stepId: 'recover-step-errored', error: 'ERROR_TOKEN', onstall, onstallend});
            const erroredAt = Date.now();
            expect(root).toHaveAttribute('data-guide-state', 'error');
            expect(coachmarkMessage()).toHaveTextContent('ERROR_TOKEN');
            expect(onstallend).toHaveBeenCalledTimes(1);

            // No deadline runs under an error, so nothing re-stalls while it is
            // displayed, however long that is.
            await advanceFakeClockTo(erroredAt + 12_000);
            expect(onstall).toHaveBeenCalledTimes(1);
            expect(onstallend).toHaveBeenCalledTimes(1);

            // Once it clears, the still-anchorless step starts over from a full
            // deadline rather than snapping back to stalled. The `null` is
            // explicit because `rerender` merges: a prop left out of the object
            // keeps its previous value, so an omitted `error` would have cleared
            // nothing and the rest of this test would have asserted an error
            // panel sitting still.
            await view.rerender({...RECOVERY_PROPS, stepId: 'recover-step-errored', error: null, onstall, onstallend});
            const clearedAt = Date.now();
            expect(root).toHaveAttribute('data-guide-state', 'waiting');

            await advanceFakeClockTo(clearedAt + 2_999);
            expect(root).toHaveAttribute('data-guide-state', 'waiting');
            expect(onstall).toHaveBeenCalledTimes(1);

            await advanceFakeClockTo(clearedAt + 3_000);
            expect(root).toHaveAttribute('data-guide-state', 'stalled');
            expect(onstall).toHaveBeenCalledTimes(2);
            expect(onstallend).toHaveBeenCalledTimes(1);
        } finally {
            cleanup();
            vi.useRealTimers();
        }
    });

    it('reports the end of a stall the unmount caused, so replaying the same step presents it normally', async () => {
        vi.useFakeTimers();
        try {
            const onstall = vi.fn();
            const onstallend = vi.fn();
            const openedAt = Date.now();
            const view = render(OnboardingCoachmark, {props: {...RECOVERY_PROPS, stepId: 'recover-step-replayed', onstall, onstallend}});
            await tick();
            expect(screen.getByTestId('onboarding-coachmark')).toHaveAttribute('data-guide-state', 'waiting');

            await advanceFakeClockTo(openedAt + 3_000);
            expect(screen.getByTestId('onboarding-coachmark')).toHaveAttribute('data-guide-state', 'stalled');
            expect(onstall).toHaveBeenCalledTimes(1);
            expect(onstallend).not.toHaveBeenCalled();

            // The user exits the guide: the host's `active` goes null and this
            // component is destroyed with its stall still on. A real unmount,
            // not a `rerender` — `rerender` merges props into the *same*
            // instance, so it would keep the very effect whose teardown is the
            // subject here, and the test would prove nothing about destroy.
            //
            // This edge is the whole fix. The host outlives the coachmark (it
            // is mounted for the entire authenticated session), so a stall that
            // is never reported as ended leaves `stalledStepId` set across exit
            // and replay.
            view.unmount();
            await tick();
            expect(screen.queryByTestId('onboarding-coachmark')).toBeNull();
            expect(onstallend).toHaveBeenCalledTimes(1);
            expect(onstall).toHaveBeenCalledTimes(1);

            // Replay from Settings, same step id, fresh instance: it must open
            // as an ordinary step, not wearing the previous run's failure.
            const replayedAt = Date.now();
            render(OnboardingCoachmark, {props: {...RECOVERY_PROPS, stepId: 'recover-step-replayed', onstall, onstallend}});
            await tick();
            const replayed = screen.getByTestId('onboarding-coachmark');
            expect(replayed).toHaveAttribute('data-guide-state', 'waiting');
            // The ordinary first-open message for a step whose target has not
            // resolved yet is the *waiting* label. The claim here is precisely
            // that it is that one and not `stalledLabel`: same step, same
            // missing anchor, but this run has not failed anything yet, so it
            // must not open wearing the load-problem wording.
            expect(coachmarkMessage()).toHaveTextContent('BUSY_LABEL_TOKEN');
            expect(screen.queryByText('STALLED_LABEL_TOKEN')).toBeNull();

            // And it gets a *full* deadline of its own, not the remainder of
            // anything: the replayed step is still unanchored, so it stalls
            // again, 3,000ms after the replay started rather than instantly.
            await advanceFakeClockTo(replayedAt + 2_999);
            expect(replayed).toHaveAttribute('data-guide-state', 'waiting');
            expect(onstall).toHaveBeenCalledTimes(1);

            await advanceFakeClockTo(replayedAt + 3_000);
            expect(replayed).toHaveAttribute('data-guide-state', 'stalled');
            expect(onstall).toHaveBeenCalledTimes(2);
            expect(onstallend).toHaveBeenCalledTimes(1);
        } finally {
            cleanup();
            vi.useRealTimers();
        }
    });

    it('stays silent on the unmount of a step that never stalled', async () => {
        vi.useFakeTimers();
        try {
            const onstall = vi.fn();
            const onstallend = vi.fn();
            const openedAt = Date.now();
            const view = render(OnboardingCoachmark, {props: {...RECOVERY_PROPS, stepId: 'recover-step-quiet', anchor: makeAnchor(), onstall, onstallend}});
            await tick();
            await settleCoachmarkGeometry();

            // The presence barrier for the negative: this instance lived long
            // enough to pass its own stall deadline twice over, anchored, so a
            // silent teardown is a decision and not a component that never ran.
            await advanceFakeClockTo(openedAt + 6_000);
            expect(screen.getByTestId('onboarding-coachmark')).toHaveAttribute('data-guide-state', 'anchored');
            expect(onstall).not.toHaveBeenCalled();

            view.unmount();
            await tick();
            expect(screen.queryByTestId('onboarding-coachmark')).toBeNull();
            expect(onstallend).not.toHaveBeenCalled();
        } finally {
            cleanup();
            vi.useRealTimers();
        }
    });
});

describe('OnboardingCoachmark — focus policy', () => {
    it('moves focus to the panel once per step when focusOnOpen is true', async () => {
        render(OnboardingCoachmark, {
            props: {
                open: true,
                anchor: makeAnchor(),
                stepId: 'step-1',
                title: 'Title',
                description: 'Description',
                focusOnOpen: true,
            },
        });

        const panel = screen.getByTestId('onboarding-coachmark-panel');
        await waitFor(() => expect(panel).toHaveFocus());
    });

    it('never moves focus when focusOnOpen is false', async () => {
        render(OnboardingCoachmark, {
            props: {
                open: true,
                anchor: makeAnchor(),
                stepId: 'step-1',
                title: 'Title',
                description: 'Description',
                focusOnOpen: false,
            },
        });

        // Flush a frame — long enough for the focus-on-open effect to have run if it
        // were going to — and confirm the panel still never took focus.
        await new Promise<void>((resolve) => requestAnimationFrame(() => resolve()));
        const panel = screen.getByTestId('onboarding-coachmark-panel');
        expect(panel).not.toHaveFocus();
    });

    it('re-focuses the panel on reopen for the same stepId (closing must clear the "already focused this step" guard)', async () => {
        const anchor = makeAnchor();
        const view = render(OnboardingCoachmark, {
            props: {
                open: true,
                anchor,
                stepId: 'step-1',
                title: 'Title',
                description: 'Description',
                focusOnOpen: true,
            },
        });

        const panel = screen.getByTestId('onboarding-coachmark-panel');
        await waitFor(() => expect(panel).toHaveFocus());

        // Close: the component renders nothing while closed, so the panel itself is gone.
        await view.rerender({
            open: false,
            anchor,
            stepId: 'step-1',
            title: 'Title',
            description: 'Description',
            focusOnOpen: true,
        });
        expect(screen.queryByTestId('onboarding-coachmark-panel')).toBeNull();

        // Reopen on the *same* stepId. If the once-per-step guard survived the close,
        // this would never re-focus, because the guard already equals this stepId.
        await view.rerender({
            open: true,
            anchor,
            stepId: 'step-1',
            title: 'Title',
            description: 'Description',
            focusOnOpen: true,
        });

        const reopenedPanel = screen.getByTestId('onboarding-coachmark-panel');
        await waitFor(() => expect(reopenedPanel).toHaveFocus());
    });
});

describe('OnboardingCoachmark — independent presentation axes', () => {
    it('mounts the compact pointer only for cursor mode and publishes its hotspot inside the real target', async () => {
        const target = rect(280, 180, 140, 64);
        const view = render(OnboardingCoachmark, {
            props: {
                open: true,
                anchor: makeAnchor(target),
                stepId: 'step-1',
                title: 'Title',
                description: 'Description',
                pointer: 'none',
                highlight: 'pulse',
                backdrop: false,
            },
        });

        let root = await expectAnchored();
        expect(root).toHaveAttribute('data-pointer', 'none');
        expect(root).toHaveAttribute('data-highlight', 'pulse');
        expect(root).toHaveAttribute('data-target-center-x', '350');
        expect(root).toHaveAttribute('data-target-center-y', '212');
        expect(root).toHaveAttribute('data-pointer-hotspot-x', '');
        expect(root).toHaveAttribute('data-pointer-hotspot-y', '');
        expect(screen.queryByTestId('onboarding-coachmark-pointer')).toBeNull();
        expect(screen.getByTestId('onboarding-coachmark-highlight')).toBeInTheDocument();
        expect(screen.queryByTestId('onboarding-spotlight-top')).toBeNull();

        view.unmount();
        render(OnboardingCoachmark, {
            props: {
                open: true,
                anchor: makeAnchor(target),
                stepId: 'step-1',
                title: 'Title',
                description: 'Description',
                pointer: 'cursor',
                highlight: 'none',
                backdrop: true,
            },
        });

        root = await expectAnchored();
        const pointer = screen.getByTestId('onboarding-coachmark-pointer');
        expect(root).toHaveAttribute('data-pointer', 'cursor');
        expect(root).toHaveAttribute('data-highlight', 'none');
        expect(Number(root.dataset.pointerHotspotX)).toBeGreaterThanOrEqual(target.left - 2);
        expect(Number(root.dataset.pointerHotspotX)).toBeLessThanOrEqual(target.right + 2);
        expect(Number(root.dataset.pointerHotspotY)).toBeGreaterThanOrEqual(target.top - 2);
        expect(Number(root.dataset.pointerHotspotY)).toBeLessThanOrEqual(target.bottom + 2);
        expect(pointer.querySelectorAll('svg')).toHaveLength(1);
        expect(Array.from(root.children).some((child) => child.tagName.toLowerCase() === 'svg')).toBe(false);
        expect(screen.queryByTestId('onboarding-coachmark-highlight')).toBeNull();
        expect(screen.getByTestId('onboarding-spotlight-top')).toBeInTheDocument();
        expect(screen.queryByTestId('onboarding-coachmark-backdrop')).toBeNull();
    });

    it('renders pulse without an intercepting backdrop', async () => {
        render(OnboardingCoachmark, {
            props: {
                open: true,
                anchor: makeAnchor(),
                stepId: 'step-1',
                title: 'Title',
                description: 'Description',
                pointer: 'none',
                highlight: 'pulse',
                backdrop: false,
            },
        });

        const root = await expectAnchored();
        expect(root).toHaveAttribute('data-pointer', 'none');
        expect(root).toHaveAttribute('data-highlight', 'pulse');
        expect(screen.getByTestId('onboarding-coachmark-highlight')).toBeInTheDocument();
        expect(screen.queryByTestId('onboarding-coachmark-pointer')).toBeNull();
        expect(screen.queryByTestId('onboarding-spotlight-top')).toBeNull();
        expect(screen.queryByTestId('onboarding-coachmark-backdrop')).toBeNull();
    });
});

const PLACEMENT_CASES = [
    {requested: 'right', expected: 'right', target: rect(80, 280, 100, 40)},
    {requested: 'left', expected: 'left', target: rect(820, 280, 100, 40)},
    {requested: 'top', expected: 'top', target: rect(450, 500, 100, 40)},
    {requested: 'bottom', expected: 'bottom', target: rect(450, 80, 100, 40)},
    {requested: 'center', expected: 'center', target: rect(20, 20, 40, 30)},
    {requested: 'auto', expected: 'right', target: rect(80, 280, 100, 40)},
] as const;

describe('OnboardingCoachmark — collision-safe geometry', () => {
    it.each(PLACEMENT_CASES)('resolves $requested to $expected inside the viewport without intersecting the target', async ({requested, expected, target}) => {
        const anchor = makeAnchor(target);
        render(OnboardingCoachmark, {
            props: {
                open: true,
                anchor,
                stepId: `placement-${requested}`,
                title: 'Title',
                description: 'Description',
                panelPlacement: requested,
            },
        });
        const panel = screen.getByTestId('onboarding-coachmark-panel');
        vi.spyOn(panel, 'getBoundingClientRect').mockReturnValue(rect(0, 0, 320, 180));

        const root = await expectAnchored();
        await waitFor(() => expect(root).toHaveAttribute('data-panel-placement', expected));
        const left = Number.parseFloat(panel.style.left);
        const top = Number.parseFloat(panel.style.top);
        const width = Number.parseFloat(panel.style.width);
        const height = 180;
        const right = left + width;
        const bottom = top + height;

        expect(left).toBeGreaterThanOrEqual(16);
        expect(top).toBeGreaterThanOrEqual(16);
        expect(right).toBeLessThanOrEqual(window.innerWidth - 16);
        expect(bottom).toBeLessThanOrEqual(window.innerHeight - 16);
        const overlapWidth = Math.max(0, Math.min(right, target.right) - Math.max(left, target.left));
        const overlapHeight = Math.max(0, Math.min(bottom, target.bottom) - Math.max(top, target.top));
        expect(overlapWidth * overlapHeight).toBe(0);
    });
});

describe('OnboardingCoachmark — reduced motion', () => {
    it('scrolls the anchor into view instantly when the user prefers reduced motion', async () => {
        stubMatchMedia({reducedMotion: true});
        const scrollSpy = vi.spyOn(Element.prototype, 'scrollIntoView');
        render(OnboardingCoachmark, {
            props: {
                open: true,
                anchor: makeAnchor(rect(80, window.innerHeight + 80, 120, 44)),
                stepId: 'step-1',
                title: 'Title',
                description: 'Description',
                scrollPolicy: 'nearest-if-hidden',
            },
        });

        await waitFor(() => expect(scrollSpy).toHaveBeenCalled());
        const lastCall = scrollSpy.mock.calls.at(-1)?.[0] as ScrollIntoViewOptions;
        expect(lastCall.behavior).toBe('auto');
    });

    it('scrolls smoothly when there is no reduced-motion preference', async () => {
        stubMatchMedia({reducedMotion: false});
        const scrollSpy = vi.spyOn(Element.prototype, 'scrollIntoView');
        render(OnboardingCoachmark, {
            props: {
                open: true,
                anchor: makeAnchor(rect(80, window.innerHeight + 80, 120, 44)),
                stepId: 'step-1',
                title: 'Title',
                description: 'Description',
                scrollPolicy: 'nearest-if-hidden',
            },
        });

        await waitFor(() => expect(scrollSpy).toHaveBeenCalled());
        const lastCall = scrollSpy.mock.calls.at(-1)?.[0] as ScrollIntoViewOptions;
        expect(lastCall.behavior).toBe('smooth');
    });

    it.each([
        {edge: 'left', target: rect(-60, 80, 120, 44)},
        {edge: 'right', target: rect(window.innerWidth - 60, 80, 120, 44)},
        {edge: 'bottom', target: rect(80, window.innerHeight - 20, 120, 44)},
    ])('keeps a generic partially visible target visible without either scroll mechanism at the $edge edge', async ({target}) => {
        vi.useFakeTimers();
        try {
            const scrollIntoViewSpy = vi.spyOn(Element.prototype, 'scrollIntoView');
            const scrollBySpy = vi.spyOn(window, 'scrollBy').mockImplementation(() => {});
            const anchor = makeAnchor(target);
            render(OnboardingCoachmark, {
                props: {
                    open: true,
                    anchor,
                    stepId: 'partially-visible',
                    title: 'Title',
                    description: 'Description',
                    scrollPolicy: 'nearest-if-hidden',
                },
            });

            await advanceCoachmarkFrames();
            expect(screen.getByTestId('onboarding-coachmark')).toHaveAttribute('data-guide-state', 'anchored');
            expect(anchor).toBeVisible();
            expect(scrollIntoViewSpy).not.toHaveBeenCalled();
            expect(scrollBySpy).not.toHaveBeenCalled();
        } finally {
            cleanup();
            vi.useRealTimers();
        }
    });

    it('uses only the precise window scroll needed to clear a sticky app header from Broker Add', async () => {
        vi.useFakeTimers();
        try {
            stubMatchMedia({reducedMotion: true});
            const scrollIntoViewSpy = vi.spyOn(Element.prototype, 'scrollIntoView');
            const scrollBySpy = vi.spyOn(window, 'scrollBy').mockImplementation(() => {});
            const header = document.createElement('header');
            header.dataset.testid = 'app-header';
            vi.spyOn(header, 'getBoundingClientRect').mockReturnValue(rect(0, 0, window.innerWidth, 64));
            document.body.appendChild(header);
            const anchor = makeAnchor(rect(80, 52, 120, 44));

            render(OnboardingCoachmark, {
                props: {
                    open: true,
                    anchor,
                    stepId: 'broker.page.add',
                    title: 'Title',
                    description: 'Description',
                    scrollPolicy: 'nearest-if-hidden',
                },
            });

            await advanceCoachmarkFrames();
            expect(screen.getByTestId('onboarding-coachmark')).toHaveAttribute('data-guide-state', 'anchored');
            expect(scrollIntoViewSpy).not.toHaveBeenCalled();
            expect(scrollBySpy).toHaveBeenCalledTimes(1);
            expect(scrollBySpy).toHaveBeenCalledWith({top: -20, behavior: 'auto'});
        } finally {
            cleanup();
            vi.useRealTimers();
        }
    });

    it('uses a direct header-safe window scroll for a target fully above the viewport, without a waiting-state flash', async () => {
        vi.useFakeTimers();
        try {
            stubMatchMedia({reducedMotion: true});
            const scrollIntoViewSpy = vi.spyOn(Element.prototype, 'scrollIntoView');
            const scrollBySpy = vi.spyOn(window, 'scrollBy').mockImplementation(() => {});
            const header = document.createElement('header');
            header.dataset.testid = 'app-header';
            vi.spyOn(header, 'getBoundingClientRect').mockReturnValue(rect(0, 0, window.innerWidth, 64));
            document.body.appendChild(header);
            const anchor = makeAnchor(rect(80, -80, 120, 44));

            render(OnboardingCoachmark, {
                props: {
                    open: true,
                    anchor,
                    stepId: 'broker.page.add',
                    title: 'Title',
                    description: 'STABLE_DESCRIPTION_TOKEN',
                    busyLabel: 'WAITING_LABEL_TOKEN',
                    scrollPolicy: 'nearest-if-hidden',
                },
            });

            await advanceCoachmarkFrames(2);
            const root = screen.getByTestId('onboarding-coachmark');
            expect(root).toHaveAttribute('data-guide-state', 'anchored');
            expect(root).toHaveAttribute('data-target-stable', 'true');
            expect(screen.getByText('STABLE_DESCRIPTION_TOKEN')).toBeInTheDocument();
            expect(screen.queryByText('WAITING_LABEL_TOKEN')).toBeNull();
            expect(scrollIntoViewSpy).not.toHaveBeenCalled();
            expect(scrollBySpy).not.toHaveBeenCalled();

            await advanceCoachmarkFrames(1);
            expect(root).toHaveAttribute('data-guide-state', 'anchored');
            expect(root).toHaveAttribute('data-target-stable', 'true');
            expect(screen.getByText('STABLE_DESCRIPTION_TOKEN')).toBeInTheDocument();
            expect(screen.queryByText('WAITING_LABEL_TOKEN')).toBeNull();
            expect(scrollIntoViewSpy).not.toHaveBeenCalled();
            expect(scrollBySpy).toHaveBeenCalledTimes(1);
            expect(scrollBySpy).toHaveBeenCalledWith({top: -152, behavior: 'auto'});
        } finally {
            cleanup();
            vi.useRealTimers();
        }
    });

    it('never scrolls an offscreen target when scrollPolicy is none', async () => {
        const scrollSpy = vi.spyOn(Element.prototype, 'scrollIntoView');
        render(OnboardingCoachmark, {
            props: {
                open: true,
                anchor: makeAnchor(rect(80, window.innerHeight + 80, 120, 44)),
                stepId: 'step-1',
                title: 'Title',
                description: 'Description',
                scrollPolicy: 'none',
            },
        });

        await expectAnchored();
        await new Promise<void>((resolve) => requestAnimationFrame(() => resolve()));
        expect(scrollSpy).not.toHaveBeenCalled();
    });
});

describe('OnboardingCoachmark — closed', () => {
    it('renders nothing at all when open is false', () => {
        render(OnboardingCoachmark, {
            props: {
                open: false,
                anchor: null,
                stepId: 'step-1',
                title: 'Title',
                description: 'Description',
            },
        });

        expect(screen.queryByTestId('onboarding-coachmark')).toBeNull();
    });
});

describe('OnboardingCoachmark — busy state', () => {
    it('publishes aria-busy and disables every rendered action while busy', async () => {
        const onnext = vi.fn();
        const onback = vi.fn();
        const onskip = vi.fn();
        const onclose = vi.fn();
        render(OnboardingCoachmark, {
            props: {
                open: true,
                anchor: makeAnchor(),
                stepId: 'step-1',
                title: 'Title',
                description: 'Description',
                busy: true,
                onnext,
                onback,
                onskip,
                onclose,
            },
        });

        expect(screen.getByTestId('onboarding-coachmark-panel')).toHaveAttribute('aria-busy', 'true');
        expect(screen.getByTestId('onboarding-coachmark-next')).toBeDisabled();
        expect(screen.getByTestId('onboarding-coachmark-back')).toBeDisabled();
        expect(screen.getByTestId('onboarding-coachmark-skip')).toBeDisabled();
        expect(screen.getByTestId('onboarding-coachmark-close')).toBeDisabled();

        await fireEvent.keyDown(window, {key: 'Escape'});
        expect(onclose).not.toHaveBeenCalled();
    });

    it('leaves every rendered action enabled, with callbacks intact, while not busy', async () => {
        const onnext = vi.fn();
        const onback = vi.fn();
        const onskip = vi.fn();
        const onclose = vi.fn();
        render(OnboardingCoachmark, {
            props: {
                open: true,
                anchor: makeAnchor(),
                stepId: 'step-1',
                title: 'Title',
                description: 'Description',
                busy: false,
                onnext,
                onback,
                onskip,
                onclose,
            },
        });

        expect(screen.getByTestId('onboarding-coachmark-panel')).toHaveAttribute('aria-busy', 'false');
        for (const testId of ['onboarding-coachmark-next', 'onboarding-coachmark-back', 'onboarding-coachmark-skip', 'onboarding-coachmark-close']) {
            expect(screen.getByTestId(testId)).toBeEnabled();
        }

        await fireEvent.click(screen.getByTestId('onboarding-coachmark-next'));
        expect(onnext).toHaveBeenCalledTimes(1);
        await fireEvent.click(screen.getByTestId('onboarding-coachmark-back'));
        expect(onback).toHaveBeenCalledTimes(1);
        await fireEvent.click(screen.getByTestId('onboarding-coachmark-skip'));
        expect(onskip).toHaveBeenCalledTimes(1);
        await fireEvent.click(screen.getByTestId('onboarding-coachmark-close'));
        expect(onclose).toHaveBeenCalledTimes(1);
    });
});

/**
 * OnboardingOverlayHost — modal-depth suspension policy.
 *
 * Page/Core anchors allow depth 0, Bulk owns depth 1, Import wizard actions own
 * depth 2, and the Import → Bulk handoff drops back to depth 1. The host keeps
 * the guide state but closes its coachmark whenever another modal rises above
 * the owning surface.
 */
const MODAL_DEPTH_CASES = [
    {label: 'a Core step is visible at depth 0', stepId: 'intro.transactions_nav', flow: 'intro_tour', depth: 0, expectVisible: true},
    {label: 'a Core step is suspended at depth 1', stepId: 'intro.transactions_nav', flow: 'intro_tour', depth: 1, expectVisible: false},
    {label: 'Bulk overview is visible in its own modal at depth 1', stepId: 'transaction.bulk.workspace', flow: 'transaction_bulk_guide', depth: 1, expectVisible: true},
    {label: 'Bulk overview is suspended by a nested modal at depth 2', stepId: 'transaction.bulk.workspace', flow: 'transaction_bulk_guide', depth: 2, expectVisible: false},
    {label: 'an Import wizard action stays visible at depth 2', stepId: 'import.analyze', flow: 'import_guide', depth: 2, expectVisible: true},
    {label: 'an Import wizard action is suspended at depth 3', stepId: 'import.analyze', flow: 'import_guide', depth: 3, expectVisible: false},
    {label: 'the Import Bulk handoff is visible at depth 1', stepId: 'import.bulk', flow: 'import_guide', depth: 1, expectVisible: true},
    {label: 'the Import Bulk handoff is suspended at depth 2', stepId: 'import.bulk', flow: 'import_guide', depth: 2, expectVisible: false},
] as const;

describe('OnboardingOverlayHost — modal-depth suspension policy', () => {
    let tailwindVisibilityRule: HTMLStyleElement;

    beforeAll(() => {
        // Component tests do not load Tailwind. Install the production utility
        // used by `class:invisible` so jest-dom can evaluate computed visibility;
        // assertions remain on the ARIA contract and actual visibility, not CSS.
        tailwindVisibilityRule = document.createElement('style');
        tailwindVisibilityRule.textContent = '.invisible { visibility: hidden; }';
        document.head.append(tailwindVisibilityRule);
    });

    afterAll(() => {
        tailwindVisibilityRule.remove();
    });

    afterEach(() => {
        document.body.removeAttribute('data-modal-scroll-lock-count');
    });

    it.each(MODAL_DEPTH_CASES)('$label', async ({stepId, flow, depth, expectVisible}) => {
        fakeGuideState.active = {flow, version: 1, stepId, mode: 'automatic'};
        document.body.setAttribute('data-modal-scroll-lock-count', String(depth));

        render(OnboardingOverlayHost, {currentPath: flow === 'intro_tour' ? '/dashboard' : '/transactions'});
        await tick();

        const root = screen.getByTestId('onboarding-coachmark');
        if (expectVisible) {
            expect(root).toHaveAttribute('aria-hidden', 'false');
            expect(root).toBeVisible();
        } else {
            expect(root).toBeInTheDocument();
            expect(root).toHaveAttribute('aria-hidden', 'true');
            expect(root).not.toBeVisible();
            expect(root).toHaveAttribute('data-step-id', stepId);
        }
    });
});

const ROUND5_PRESENTATION_CASES = [
    {label: 'Core navigation', flow: 'intro_tour', stepId: 'intro.navigation', anchorId: 'nav.toggle.desktop', path: '/dashboard', target: rect(80, 280, 100, 40), pointer: 'cursor', highlight: 'pulse', backdrop: true, placement: 'right'},
    {label: 'Core Dashboard', flow: 'intro_tour', stepId: 'intro.dashboard', anchorId: 'nav.dashboard', path: '/dashboard', target: rect(80, 280, 100, 40), pointer: 'cursor', highlight: 'pulse', backdrop: true, placement: 'right'},
    {label: 'Core Transactions', flow: 'intro_tour', stepId: 'intro.transactions_nav', anchorId: 'nav.transactions', path: '/dashboard', target: rect(80, 280, 100, 40), pointer: 'cursor', highlight: 'pulse', backdrop: true, placement: 'right'},
    {label: 'Core Brokers', flow: 'intro_tour', stepId: 'intro.brokers_nav', anchorId: 'nav.brokers', path: '/dashboard', target: rect(80, 280, 100, 40), pointer: 'cursor', highlight: 'pulse', backdrop: true, placement: 'right'},
    {label: 'Core FX', flow: 'intro_tour', stepId: 'intro.fx_nav', anchorId: 'nav.fx', path: '/dashboard', target: rect(80, 280, 100, 40), pointer: 'cursor', highlight: 'pulse', backdrop: true, placement: 'right'},
    {label: 'Core Assets', flow: 'intro_tour', stepId: 'intro.assets_nav', anchorId: 'nav.assets', path: '/dashboard', target: rect(80, 280, 100, 40), pointer: 'cursor', highlight: 'pulse', backdrop: true, placement: 'right'},
    {label: 'Core Tools', flow: 'intro_tour', stepId: 'intro.tools_nav', anchorId: 'nav.tools', path: '/dashboard', target: rect(80, 280, 100, 40), pointer: 'cursor', highlight: 'pulse', backdrop: true, placement: 'right'},
    {label: 'Core Settings', flow: 'intro_tour', stepId: 'intro.settings_nav', anchorId: 'nav.settings', path: '/dashboard', target: rect(80, 280, 100, 40), pointer: 'cursor', highlight: 'pulse', backdrop: true, placement: 'right'},
    {label: 'Transactions overview', flow: 'transactions_page_guide', stepId: 'transactions.page.overview', anchorId: 'transactions.page.overview', path: '/transactions', target: rect(420, 80, 120, 40), pointer: 'none', highlight: 'pulse', backdrop: false, placement: 'bottom'},
    {label: 'Transactions Add', flow: 'transactions_page_guide', stepId: 'transactions.page.add', anchorId: 'transactions.page.add', path: '/transactions', target: rect(80, 280, 100, 40), pointer: 'cursor', highlight: 'none', backdrop: false, placement: 'right'},
    {label: 'Transactions Import', flow: 'transactions_page_guide', stepId: 'transactions.page.import', anchorId: 'transactions.page.import', path: '/transactions', target: rect(80, 280, 100, 40), pointer: 'cursor', highlight: 'none', backdrop: false, placement: 'right'},
    {label: 'Transactions columns', flow: 'transactions_page_guide', stepId: 'transactions.page.columns', anchorId: 'transactions.page.columns', path: '/transactions', target: rect(80, 280, 100, 40), pointer: 'none', highlight: 'pulse', backdrop: false, placement: 'right'},
    {label: 'Transaction form basics', flow: 'transaction_create_guide', stepId: 'transaction.create.basics', anchorId: 'transaction.create.basics', path: '/transactions', target: rect(80, 280, 100, 40), pointer: 'none', highlight: 'pulse', backdrop: false, placement: 'right'},
    {label: 'Transaction form amounts', flow: 'transaction_create_guide', stepId: 'transaction.create.amounts', anchorId: 'transaction.create.amounts', path: '/transactions', target: rect(80, 280, 100, 40), pointer: 'none', highlight: 'pulse', backdrop: false, placement: 'right'},
    {label: 'Transaction form details', flow: 'transaction_create_guide', stepId: 'transaction.create.details', anchorId: 'transaction.create.details', path: '/transactions', target: rect(80, 280, 100, 40), pointer: 'none', highlight: 'pulse', backdrop: false, placement: 'right'},
    {label: 'Transaction form Save', flow: 'transaction_create_guide', stepId: 'transaction.create.save', anchorId: 'transaction.create.save', path: '/transactions', target: rect(420, 500, 120, 40), pointer: 'cursor', highlight: 'none', backdrop: false, placement: 'top'},
    {label: 'Bulk overview', flow: 'transaction_bulk_guide', stepId: 'transaction.bulk.workspace', anchorId: 'transaction.bulk.workspace', path: '/transactions', target: rect(80, 280, 100, 40), pointer: 'none', highlight: 'pulse', backdrop: false, placement: 'right'},
    {label: 'Bulk validation', flow: 'transaction_bulk_guide', stepId: 'transaction.bulk.validation', anchorId: 'transaction.bulk.validation', path: '/transactions', target: rect(80, 280, 100, 40), pointer: 'none', highlight: 'pulse', backdrop: false, placement: 'right'},
    {label: 'Bulk selection', flow: 'transaction_bulk_guide', stepId: 'transaction.bulk.selection', anchorId: 'transaction.bulk.selection', path: '/transactions', target: rect(80, 280, 100, 40), pointer: 'none', highlight: 'pulse', backdrop: false, placement: 'right'},
    {label: 'Bulk Save', flow: 'transaction_bulk_guide', stepId: 'transaction.bulk.save', anchorId: 'transaction.bulk.save', path: '/transactions', target: rect(420, 500, 120, 40), pointer: 'cursor', highlight: 'none', backdrop: false, placement: 'top'},
    {label: 'Import first CTA', flow: 'import_guide', stepId: 'import.upload', anchorId: 'import.action.upload', path: '/transactions', target: rect(420, 500, 120, 40), pointer: 'cursor', highlight: 'none', backdrop: false, placement: 'top'},
    {label: 'Import Select CTA', flow: 'import_guide', stepId: 'import.select', anchorId: 'import.action.select', path: '/transactions', target: rect(420, 500, 120, 40), pointer: 'cursor', highlight: 'none', backdrop: false, placement: 'top'},
    {label: 'Import Analyze CTA', flow: 'import_guide', stepId: 'import.analyze', anchorId: 'import.action.analyze', path: '/transactions', target: rect(420, 500, 120, 40), pointer: 'cursor', highlight: 'none', backdrop: false, placement: 'top'},
    {label: 'Import Assets CTA', flow: 'import_guide', stepId: 'import.assets', anchorId: 'import.action.assets', path: '/transactions', target: rect(420, 500, 120, 40), pointer: 'cursor', highlight: 'none', backdrop: false, placement: 'top'},
    {label: 'Import Fix CTA', flow: 'import_guide', stepId: 'import.fix', anchorId: 'import.action.fix', path: '/transactions', target: rect(420, 500, 120, 40), pointer: 'cursor', highlight: 'none', backdrop: false, placement: 'top'},
    {label: 'Import Duplicates CTA', flow: 'import_guide', stepId: 'import.duplicates', anchorId: 'import.action.duplicates', path: '/transactions', target: rect(420, 500, 120, 40), pointer: 'cursor', highlight: 'none', backdrop: false, placement: 'top'},
    {label: 'Import Review CTA', flow: 'import_guide', stepId: 'import.review', anchorId: 'import.action.review', path: '/transactions', target: rect(420, 500, 120, 40), pointer: 'cursor', highlight: 'none', backdrop: false, placement: 'top'},
    {label: 'Import Bulk CTA', flow: 'import_guide', stepId: 'import.bulk', anchorId: 'import.bulk.save-all', path: '/transactions', target: rect(420, 500, 120, 40), pointer: 'cursor', highlight: 'none', backdrop: false, placement: 'top'},
    {label: 'Broker page overview', flow: 'broker_page_guide', stepId: 'broker.page.overview', anchorId: 'broker.page.overview', path: '/brokers', target: rect(80, 280, 100, 40), pointer: 'none', highlight: 'pulse', backdrop: false, placement: 'right'},
    {label: 'Broker page currency', flow: 'broker_page_guide', stepId: 'broker.page.currency', anchorId: 'broker.page.currency', path: '/brokers', target: rect(80, 280, 100, 40), pointer: 'none', highlight: 'pulse', backdrop: false, placement: 'right'},
    {label: 'Broker page views', flow: 'broker_page_guide', stepId: 'broker.page.views', anchorId: 'broker.page.views', path: '/brokers', target: rect(80, 280, 100, 40), pointer: 'none', highlight: 'pulse', backdrop: false, placement: 'right'},
    {label: 'Broker page Add', flow: 'broker_page_guide', stepId: 'broker.page.add', anchorId: 'broker.page.add', path: '/brokers', target: rect(80, 280, 100, 40), pointer: 'cursor', highlight: 'none', backdrop: false, placement: 'right'},
    {label: 'Broker overview audit', flow: 'broker_guide', stepId: 'broker.overview', anchorId: 'broker.modal', path: '/brokers', target: rect(80, 280, 100, 40), pointer: 'none', highlight: 'pulse', backdrop: false, placement: 'right'},
    {label: 'Broker plugin audit', flow: 'broker_guide', stepId: 'broker.plugin', anchorId: 'broker.plugin', path: '/brokers', target: rect(80, 280, 100, 40), pointer: 'none', highlight: 'pulse', backdrop: false, placement: 'right'},
    {label: 'Broker icon action', flow: 'broker_guide', stepId: 'broker.icon', anchorId: 'broker.icon', path: '/brokers', target: rect(80, 280, 100, 40), pointer: 'cursor', highlight: 'none', backdrop: false, placement: 'right'},
    {label: 'Broker detail header', flow: 'broker_detail_guide', stepId: 'broker.detail.header', anchorId: 'broker.detail.header', path: '/brokers/42', target: rect(80, 280, 100, 40), pointer: 'none', highlight: 'pulse', backdrop: false, placement: 'right'},
    {label: 'FX page overview', flow: 'fx_page_guide', stepId: 'fx.page.overview', anchorId: 'fx.page.overview', path: '/fx', target: rect(80, 280, 100, 40), pointer: 'none', highlight: 'pulse', backdrop: false, placement: 'right'},
    {label: 'FX page filters', flow: 'fx_page_guide', stepId: 'fx.page.filters', anchorId: 'fx.page.filters', path: '/fx', target: rect(80, 280, 100, 40), pointer: 'none', highlight: 'pulse', backdrop: false, placement: 'right'},
    {label: 'FX page Sync', flow: 'fx_page_guide', stepId: 'fx.page.sync', anchorId: 'fx.page.sync', path: '/fx', target: rect(80, 280, 100, 40), pointer: 'cursor', highlight: 'none', backdrop: false, placement: 'right'},
    {label: 'FX page Add', flow: 'fx_page_guide', stepId: 'fx.page.add', anchorId: 'fx.page.add', path: '/fx', target: rect(80, 280, 100, 40), pointer: 'cursor', highlight: 'none', backdrop: false, placement: 'right'},
    {label: 'FX currencies audit', flow: 'fx_guide', stepId: 'fx.currencies', anchorId: 'fx.currencies', path: '/fx', target: rect(80, 280, 100, 40), pointer: 'none', highlight: 'pulse', backdrop: false, placement: 'right'},
    {label: 'FX providers audit', flow: 'fx_guide', stepId: 'fx.providers', anchorId: 'fx.providers', path: '/fx', target: rect(80, 280, 100, 40), pointer: 'none', highlight: 'pulse', backdrop: false, placement: 'right'},
    {label: 'FX detail header', flow: 'fx_detail_guide', stepId: 'fx.detail.header', anchorId: 'fx.detail.header', path: '/fx/EUR-USD', target: rect(80, 280, 100, 40), pointer: 'none', highlight: 'pulse', backdrop: false, placement: 'right'},
    {label: 'FX detail provider action', flow: 'fx_detail_guide', stepId: 'fx.detail.provider', anchorId: 'fx.detail.provider', path: '/fx/EUR-USD', target: rect(80, 280, 100, 40), pointer: 'cursor', highlight: 'none', backdrop: false, placement: 'right'},
    {label: 'FX detail chart', flow: 'fx_detail_guide', stepId: 'fx.detail.chart', anchorId: 'fx.detail.chart', path: '/fx/EUR-USD', target: rect(80, 280, 100, 40), pointer: 'none', highlight: 'pulse', backdrop: false, placement: 'right'},
    {label: 'FX detail editor action', flow: 'fx_detail_guide', stepId: 'fx.detail.editor', anchorId: 'fx.detail.editor', path: '/fx/EUR-USD', target: rect(80, 280, 100, 40), pointer: 'cursor', highlight: 'none', backdrop: false, placement: 'right'},
    {label: 'Asset page overview', flow: 'asset_page_guide', stepId: 'asset.page.overview', anchorId: 'asset.page.overview', path: '/assets', target: rect(80, 280, 100, 40), pointer: 'none', highlight: 'pulse', backdrop: false, placement: 'right'},
    {label: 'Asset page filters', flow: 'asset_page_guide', stepId: 'asset.page.filters', anchorId: 'asset.page.filters', path: '/assets', target: rect(80, 280, 100, 40), pointer: 'none', highlight: 'pulse', backdrop: false, placement: 'right'},
    {label: 'Asset page Sync', flow: 'asset_page_guide', stepId: 'asset.page.sync', anchorId: 'asset.page.sync', path: '/assets', target: rect(80, 280, 100, 40), pointer: 'cursor', highlight: 'none', backdrop: false, placement: 'right'},
    {label: 'Asset page Add', flow: 'asset_page_guide', stepId: 'asset.page.add', anchorId: 'asset.page.add', path: '/assets', target: rect(80, 280, 100, 40), pointer: 'cursor', highlight: 'none', backdrop: false, placement: 'right'},
    {label: 'Asset Add search', flow: 'asset_guide', stepId: 'asset.search', anchorId: 'asset.search', path: '/assets', target: rect(80, 280, 100, 40), pointer: 'none', highlight: 'pulse', backdrop: false, placement: 'right'},
    {label: 'Asset Add identity', flow: 'asset_guide', stepId: 'asset.identity', anchorId: 'asset.identity', path: '/assets', target: rect(80, 280, 100, 40), pointer: 'none', highlight: 'pulse', backdrop: false, placement: 'right'},
    {label: 'Asset Add provider', flow: 'asset_guide', stepId: 'asset.provider', anchorId: 'asset.provider', path: '/assets', target: rect(80, 280, 100, 40), pointer: 'none', highlight: 'pulse', backdrop: false, placement: 'right'},
    {label: 'Asset detail header', flow: 'asset_detail_guide', stepId: 'asset.detail.header', anchorId: 'asset.detail.header', path: '/assets/42', target: rect(80, 280, 100, 40), pointer: 'none', highlight: 'pulse', backdrop: false, placement: 'right'},
    {label: 'Asset detail chart', flow: 'asset_detail_guide', stepId: 'asset.detail.chart', anchorId: 'asset.detail.chart', path: '/assets/42', target: rect(80, 280, 100, 40), pointer: 'none', highlight: 'pulse', backdrop: false, placement: 'right'},
    {label: 'Asset detail editor action', flow: 'asset_detail_guide', stepId: 'asset.detail.editor', anchorId: 'asset.detail.editor', path: '/assets/42', target: rect(80, 280, 100, 40), pointer: 'cursor', highlight: 'none', backdrop: false, placement: 'right'},
    {label: 'Asset detail metadata action', flow: 'asset_detail_guide', stepId: 'asset.detail.metadata', anchorId: 'asset.detail.metadata', path: '/assets/42', target: rect(80, 280, 100, 40), pointer: 'cursor', highlight: 'none', backdrop: false, placement: 'right'},
    {label: 'Asset detail risk action', flow: 'asset_detail_guide', stepId: 'asset.detail.risk', anchorId: 'asset.detail.risk', path: '/assets/42', target: rect(80, 280, 100, 40), pointer: 'cursor', highlight: 'none', backdrop: false, placement: 'right'},
] as const;

describe('OnboardingOverlayHost — Round 5 presentation matrix', () => {
    it.each(ROUND5_PRESENTATION_CASES)('$label keeps pointer, highlight, backdrop, and placement independent', async ({flow, stepId, anchorId, path, target, pointer, highlight, backdrop, placement}) => {
        const anchor = makeAnchor(target);
        guideAnchors.register(anchorId, anchor);
        fakeGuideState.active = {flow, version: 1, stepId, mode: 'automatic'};

        render(OnboardingOverlayHost, {currentPath: path});

        await waitFor(() => expect(anchor).toHaveAttribute('aria-describedby', DESCRIPTION_ID));
        const coachmark = await expectAnchored();
        expect(coachmark).toHaveAttribute('data-step-id', stepId);
        expect(coachmark).toHaveAttribute('data-pointer', pointer);
        expect(coachmark).toHaveAttribute('data-highlight', highlight);
        expect(coachmark).toHaveAttribute('data-panel-placement', placement);
        if (pointer === 'cursor') {
            expect(screen.getByTestId('onboarding-coachmark-pointer')).toBeInTheDocument();
        } else {
            expect(screen.queryByTestId('onboarding-coachmark-pointer')).toBeNull();
        }
        if (highlight === 'pulse') {
            expect(screen.getByTestId('onboarding-coachmark-highlight')).toBeInTheDocument();
        } else {
            expect(screen.queryByTestId('onboarding-coachmark-highlight')).toBeNull();
        }
        if (backdrop) {
            expect(screen.getByTestId('onboarding-spotlight-top')).toBeInTheDocument();
        } else {
            expect(screen.queryByTestId('onboarding-spotlight-top')).toBeNull();
            expect(screen.queryByTestId('onboarding-coachmark-backdrop')).toBeNull();
        }
    });

    it.each([
        {flow: 'intro_tour', stepId: 'intro.dashboard', anchorId: 'nav.dashboard', path: '/dashboard', scrolls: true},
        {flow: 'transactions_page_guide', stepId: 'transactions.page.overview', anchorId: 'transactions.page.overview', path: '/transactions', scrolls: true},
        {flow: 'transaction_bulk_guide', stepId: 'transaction.bulk.save', anchorId: 'transaction.bulk.save', path: '/transactions', scrolls: true},
        {flow: 'import_guide', stepId: 'import.upload', anchorId: 'import.action.upload', path: '/transactions', scrolls: false},
        {flow: 'import_guide', stepId: 'import.analyze', anchorId: 'import.action.analyze', path: '/transactions', scrolls: false},
        {flow: 'broker_page_guide', stepId: 'broker.page.views', anchorId: 'broker.page.views', path: '/brokers', scrolls: false},
        {flow: 'broker_page_guide', stepId: 'broker.page.add', anchorId: 'broker.page.add', path: '/brokers', scrolls: true},
    ] as const)('$stepId applies its scroll policy', async ({flow, stepId, anchorId, path, scrolls}) => {
        const scrollIntoViewSpy = vi.spyOn(Element.prototype, 'scrollIntoView');
        const scrollBySpy = vi.spyOn(window, 'scrollBy').mockImplementation(() => {});
        const anchor = makeAnchor(rect(80, window.innerHeight + 80, 120, 44));
        guideAnchors.register(anchorId, anchor);
        fakeGuideState.active = {flow, version: 1, stepId, mode: 'automatic'};

        render(OnboardingOverlayHost, {currentPath: path});
        await expectAnchored();
        if (scrolls) {
            await waitFor(() => expect(scrollIntoViewSpy).toHaveBeenCalled());
            expect(scrollBySpy).not.toHaveBeenCalled();
        } else {
            await new Promise<void>((resolve) => requestAnimationFrame(() => resolve()));
            expect(scrollIntoViewSpy).not.toHaveBeenCalled();
            expect(scrollBySpy).not.toHaveBeenCalled();
        }
    });

    it.each([
        {stepId: 'intro.fx_nav', anchorId: 'nav.fx', target: rect(140, 80, 120, 40), placement: 'bottom'},
        {stepId: 'intro.settings_nav', anchorId: 'nav.settings', target: rect(140, 500, 120, 40), placement: 'top'},
    ] as const)('uses the mobile override for $stepId', async ({stepId, anchorId, target, placement}) => {
        stubMatchMedia({mobile: true});
        const anchor = makeAnchor(target);
        guideAnchors.register(anchorId, anchor);
        fakeGuideState.active = {flow: 'intro_tour', version: 1, stepId, mode: 'automatic'};

        render(OnboardingOverlayHost, {currentPath: '/dashboard'});

        await expectAnchored();
        expect(screen.getByTestId('onboarding-coachmark')).toHaveAttribute('data-panel-placement', placement);
    });
});

describe('OnboardingOverlayHost — checkpoint versus sequence navigation', () => {
    it('explicitly classifies transaction_bulk_guide as checkpoint navigation and Import as the default sequence', () => {
        expect(isCheckpointFlow('transaction_bulk_guide')).toBe(true);
        expect(isCheckpointFlow('import_guide')).toBe(false);
    });

    it('renders Bulk without progress, Back, or ArrowRight and completes only the active checkpoint', async () => {
        const anchor = makeAnchor();
        guideAnchors.register('transaction.bulk.workspace', anchor);
        fakeGuideState.active = {
            flow: 'transaction_bulk_guide',
            version: 1,
            stepId: 'transaction.bulk.workspace',
            mode: 'automatic',
            progress: {current: 1, total: 4},
        };

        render(OnboardingOverlayHost, {currentPath: '/transactions'});

        await waitFor(() => expect(anchor).toHaveAttribute('aria-describedby', DESCRIPTION_ID));
        expect(screen.queryByTestId('onboarding-coachmark-progress')).toBeNull();
        expect(screen.queryByTestId('onboarding-coachmark-back')).toBeNull();
        const primary = screen.getByTestId('onboarding-coachmark-next');
        expect(primary).toHaveTextContent('i18n:onboarding.actions.gotIt');
        expect(primary.querySelectorAll('svg')).toHaveLength(0);
        expect(translateKey.mock.calls.some(([key]) => key === 'onboarding.actions.gotIt')).toBe(true);
        expect(translateKey.mock.calls.some(([key]) => key === 'onboarding.actions.finish')).toBe(false);

        await fireEvent.click(primary);

        await waitFor(() => expect(onboardingGuide.finish).toHaveBeenCalledTimes(1));
        expect(onboardingGuide.next).not.toHaveBeenCalled();
        expect(onboardingGuide.previous).not.toHaveBeenCalled();
        expect(fakeGuideState.active).toMatchObject({
            flow: 'transaction_bulk_guide',
            stepId: 'transaction.bulk.workspace',
        });
    });

    it('keeps Import dynamic progress and sequence chrome through the Bulk handoff', async () => {
        const anchor = makeAnchor();
        guideAnchors.register('import.bulk.save-all', anchor);
        fakeGuideState.active = {
            flow: 'import_guide',
            version: 1,
            stepId: 'import.bulk',
            mode: 'automatic',
            progress: {current: 7, total: 8},
        };

        render(OnboardingOverlayHost, {currentPath: '/transactions'});

        await waitFor(() => expect(anchor).toHaveAttribute('aria-describedby', DESCRIPTION_ID));
        expect(screen.getByTestId('onboarding-coachmark-progress')).toBeInTheDocument();
        expect(screen.queryByTestId('onboarding-coachmark-back')).toBeNull();
        expect(screen.getByTestId('onboarding-coachmark-next').querySelectorAll('svg')).toHaveLength(1);
        expect(translateKey.mock.calls.some(([key, options]) => key === 'onboarding.tour.progress' && JSON.stringify(options) === JSON.stringify({values: {current: 7, total: 8}}))).toBe(true);
        expect(translateKey.mock.calls.some(([key]) => key === 'onboarding.actions.finish')).toBe(true);
        expect(translateKey.mock.calls.some(([key]) => key === 'onboarding.actions.gotIt')).toBe(false);
    });
});

describe('OnboardingOverlayHost — target-click progression policy', () => {
    it('advances a flow-managed contextual guide from the real target click', async () => {
        const anchor = makeAnchor();
        guideAnchors.register('transactions.page.add', anchor);
        fakeGuideState.active = {
            flow: 'transactions_page_guide',
            version: 1,
            stepId: 'transactions.page.add',
            mode: 'automatic',
        };

        render(OnboardingOverlayHost, {currentPath: '/transactions'});
        await waitFor(() => expect(anchor).toHaveAttribute('aria-describedby', DESCRIPTION_ID));
        await waitFor(() => expect(screen.getByTestId('onboarding-coachmark-action-hint')).toBeInTheDocument());

        await fireEvent.click(anchor);

        await waitFor(() => expect(onboardingGuide.next).toHaveBeenCalledTimes(1));
        expect(onboardingGuide.finish).not.toHaveBeenCalled();
    });

    it('completes only the active step-managed milestone from the real target click', async () => {
        const anchor = makeAnchor();
        guideAnchors.register('transaction.bulk.save', anchor);
        fakeGuideState.active = {
            flow: 'transaction_bulk_guide',
            version: 1,
            stepId: 'transaction.bulk.save',
            mode: 'automatic',
        };

        render(OnboardingOverlayHost, {currentPath: '/transactions'});
        await waitFor(() => expect(anchor).toHaveAttribute('aria-describedby', DESCRIPTION_ID));

        await fireEvent.click(anchor);

        await waitFor(() => expect(onboardingGuide.finish).toHaveBeenCalledTimes(1));
        expect(onboardingGuide.next).not.toHaveBeenCalled();
    });

    it('never auto-advances Core or renders the contextual action hint', async () => {
        const anchor = makeAnchor();
        guideAnchors.register('nav.dashboard', anchor);
        fakeGuideState.active = {
            flow: 'intro_tour',
            version: 1,
            stepId: 'intro.dashboard',
            mode: 'automatic',
        };

        render(OnboardingOverlayHost, {currentPath: '/dashboard'});
        await waitFor(() => expect(anchor).toHaveAttribute('aria-describedby', DESCRIPTION_ID));
        expect(screen.queryByTestId('onboarding-coachmark-action-hint')).toBeNull();

        await fireEvent.click(anchor);

        expect(onboardingGuide.next).not.toHaveBeenCalled();
        expect(onboardingGuide.finish).not.toHaveBeenCalled();
    });
});

describe('OnboardingOverlayHost — terminal action', () => {
    it.each(['automatic', 'replay'] as const)('uses the single close control to exit an %s contextual guide', async (mode) => {
        const anchor = makeAnchor();
        guideAnchors.register('import.action.upload', anchor);
        fakeGuideState.active = {flow: 'import_guide', version: 1, stepId: 'import.upload', mode};

        render(OnboardingOverlayHost, {currentPath: '/transactions'});

        await waitFor(() => expect(anchor).toHaveAttribute('aria-describedby', DESCRIPTION_ID));
        expect(screen.queryByTestId('onboarding-coachmark-skip')).toBeNull();
        await fireEvent.click(screen.getByTestId('onboarding-coachmark-close'));
        await waitFor(() => expect(onboardingGuide.exit).toHaveBeenCalledTimes(1));
        expect(onboardingGuide.skip).not.toHaveBeenCalled();
        expect(onboardingGuide.dismissHost).not.toHaveBeenCalled();
    });
});

describe('OnboardingOverlayHost — stalled step escape hatch', () => {
    it('gives a stalled Import step its first forward control and persists it as skipped', async () => {
        vi.useFakeTimers();
        try {
            // No anchor is registered for `import.analyze` on purpose: this is the
            // hang Round 7 is about — the wizard never published its target, and
            // before this change an `import_guide` step offered no forward control
            // at all, so the user was left with a busy label and no way out.
            fakeGuideState.active = {flow: 'import_guide', version: 1, stepId: 'import.analyze', mode: 'automatic'};

            render(OnboardingOverlayHost, {currentPath: '/transactions'});
            await tick();

            const root = screen.getByTestId('onboarding-coachmark');
            expect(root).toHaveAttribute('data-guide-state', 'waiting');
            expect(coachmarkMessage()).toHaveTextContent('i18n:onboarding.guide.waiting');
            expect(screen.queryByTestId('onboarding-coachmark-navigation')).toBeNull();

            await vi.advanceTimersByTimeAsync(3_000);
            await tick();

            expect(root).toHaveAttribute('data-guide-state', 'stalled');
            expect(coachmarkMessage()).toHaveTextContent('i18n:onboarding.guide.loadProblem');
            const next = screen.getByTestId('onboarding-coachmark-next');
            expect(next).toHaveTextContent('i18n:onboarding.actions.continueAnyway');
            expect(next.querySelectorAll('svg')).toHaveLength(0);

            await fireEvent.click(next);

            // `import_guide` is step-managed, so continuing from a step the user
            // could never perform has to persist as *skipped*, never as completed.
            expect(onboardingGuide.skip).toHaveBeenCalledTimes(1);
            expect(onboardingGuide.finish).not.toHaveBeenCalled();
            expect(onboardingGuide.next).not.toHaveBeenCalled();
        } finally {
            cleanup();
            vi.useRealTimers();
        }
    });

    it('keeps a stalled flow-managed guide on its own navigation instead of skipping the step', async () => {
        vi.useFakeTimers();
        try {
            fakeGuideState.active = {flow: 'transactions_page_guide', version: 1, stepId: 'transactions.page.overview', mode: 'automatic'};

            render(OnboardingOverlayHost, {currentPath: '/transactions'});
            await tick();

            const next = screen.getByTestId('onboarding-coachmark-next');
            expect(next).toHaveTextContent('i18n:onboarding.actions.next');

            await vi.advanceTimersByTimeAsync(3_000);
            await tick();

            expect(screen.getByTestId('onboarding-coachmark')).toHaveAttribute('data-guide-state', 'stalled');
            expect(next).toHaveTextContent('i18n:onboarding.actions.continueAnyway');

            await fireEvent.click(next);

            // Not step-managed: there is no per-step record to skip, so the
            // stalled label changes the wording and nothing else.
            expect(onboardingGuide.next).toHaveBeenCalledTimes(1);
            expect(onboardingGuide.skip).not.toHaveBeenCalled();
            expect(onboardingGuide.finish).not.toHaveBeenCalled();
        } finally {
            cleanup();
            vi.useRealTimers();
        }
    });

    it('leaves an anchored Import step with no forward control and no continue-anyway wording', async () => {
        vi.useFakeTimers();
        try {
            const anchor = makeAnchor();
            guideAnchors.register('import.action.analyze', anchor);
            fakeGuideState.active = {flow: 'import_guide', version: 1, stepId: 'import.analyze', mode: 'automatic'};

            render(OnboardingOverlayHost, {currentPath: '/transactions'});
            const root = await settleCoachmarkGeometry();

            // Same step, same 3 seconds — the only difference is that its target
            // exists, which is what must decide whether the escape hatch appears.
            await vi.advanceTimersByTimeAsync(3_000);
            await tick();

            expect(root).toHaveAttribute('data-guide-state', 'anchored');
            expect(screen.queryByTestId('onboarding-coachmark-next')).toBeNull();
            expect(screen.queryByTestId('onboarding-coachmark-navigation')).toBeNull();
            expect(translateKey.mock.calls.some(([key]) => key === 'onboarding.actions.continueAnyway')).toBe(false);
        } finally {
            cleanup();
            vi.useRealTimers();
        }
    });

    it('retracts the escape hatch when a stalled Import step finally gets its target', async () => {
        vi.useFakeTimers();
        try {
            fakeGuideState.active = {flow: 'import_guide', version: 1, stepId: 'import.analyze', mode: 'automatic'};

            render(OnboardingOverlayHost, {currentPath: '/transactions'});
            await tick();
            await vi.advanceTimersByTimeAsync(3_000);
            await tick();

            const root = screen.getByTestId('onboarding-coachmark');
            expect(root).toHaveAttribute('data-guide-state', 'stalled');
            expect(screen.getByTestId('onboarding-coachmark-next')).toHaveTextContent('i18n:onboarding.actions.continueAnyway');

            // The wizard publishes its target late. The host clears
            // `stalledStepId` only because the coachmark reports the recovery:
            // without that edge the panel below reads "use the wizard action"
            // while the button above it still says "continue anyway" and still
            // persists the step as skipped.
            guideAnchors.register('import.action.analyze', makeAnchor());
            await settleCoachmarkGeometry();

            expect(root).toHaveAttribute('data-guide-state', 'anchored');
            expect(coachmarkMessage()).toHaveTextContent('i18n:onboarding.importGuide.steps.analyze.description');
            expect(screen.getByTestId('onboarding-coachmark-action-hint')).toHaveTextContent('i18n:onboarding.guide.useWizardAction');

            // An anchored `import.analyze` normally has no forward control at
            // all — the user performs the wizard action — so on this step the
            // skip path is not relabelled, it becomes unreachable.
            expect(screen.queryByTestId('onboarding-coachmark-next')).toBeNull();
            expect(screen.queryByTestId('onboarding-coachmark-navigation')).toBeNull();
            expect(onboardingGuide.skip).not.toHaveBeenCalled();
        } finally {
            cleanup();
            vi.useRealTimers();
        }
    });

    it('records the action a recovered step-managed step actually offers, never a skip', async () => {
        vi.useFakeTimers();
        try {
            // `import.bulk` is the one Import step that keeps a forward control
            // when anchored, so recovery is visible here as the control changing
            // back rather than disappearing: label, arrow and recorded outcome.
            fakeGuideState.active = {flow: 'import_guide', version: 1, stepId: 'import.bulk', mode: 'automatic'};

            render(OnboardingOverlayHost, {currentPath: '/transactions'});
            await tick();
            await vi.advanceTimersByTimeAsync(3_000);
            await tick();

            const root = screen.getByTestId('onboarding-coachmark');
            const stalledNext = screen.getByTestId('onboarding-coachmark-next');
            expect(root).toHaveAttribute('data-guide-state', 'stalled');
            expect(stalledNext).toHaveTextContent('i18n:onboarding.actions.continueAnyway');
            expect(stalledNext.querySelectorAll('svg')).toHaveLength(0);

            guideAnchors.register('import.bulk.save-all', makeAnchor());
            await settleCoachmarkGeometry();

            const recoveredNext = screen.getByTestId('onboarding-coachmark-next');
            expect(root).toHaveAttribute('data-guide-state', 'anchored');
            expect(recoveredNext).toHaveTextContent('i18n:onboarding.actions.finish');
            expect(recoveredNext.querySelectorAll('svg')).toHaveLength(1);

            await fireEvent.click(recoveredNext);

            // The persisted outcome has to follow the real action: recording
            // `skipped` for a step the user can now perform is the same untruth
            // as recording `completed` for one never offered.
            expect(onboardingGuide.finish).toHaveBeenCalledTimes(1);
            expect(onboardingGuide.skip).not.toHaveBeenCalled();
        } finally {
            cleanup();
            vi.useRealTimers();
        }
    });
});

describe('OnboardingOverlayHost — intro scene and responsive navigation anchor', () => {
    it('renders the intro scene instead of a coachmark and advances only from its Start action', async () => {
        fakeGuideState.active = {flow: 'intro_tour', version: 1, stepId: 'intro.scene', mode: 'automatic'};

        render(OnboardingOverlayHost, {currentPath: '/dashboard'});
        await tick();

        expect(screen.getByTestId('onboarding-intro-scene')).toBeInTheDocument();
        expect(screen.queryByTestId('onboarding-coachmark')).toBeNull();
        expect(onboardingGuide.next).not.toHaveBeenCalled();

        await fireEvent.click(screen.getByTestId('onboarding-intro-start'));

        expect(onboardingGuide.next).toHaveBeenCalledTimes(1);
        expect(onboardingGuide.exit).not.toHaveBeenCalled();
    });

    it.each(['automatic', 'replay'] as const)('routes the intro scene X through the guide exit policy in %s mode', async (mode) => {
        fakeGuideState.active = {flow: 'intro_tour', version: 1, stepId: 'intro.scene', mode};

        render(OnboardingOverlayHost, {currentPath: '/dashboard'});
        await fireEvent.click(screen.getByTestId('onboarding-intro-close'));

        await waitFor(() => expect(onboardingGuide.exit).toHaveBeenCalledTimes(1));
        expect(onboardingGuide.skip).not.toHaveBeenCalled();
        expect(onboardingGuide.suspend).not.toHaveBeenCalled();
    });

    it.each([
        {viewport: 'desktop', mobile: false, selectedId: 'nav.toggle.desktop', rejectedId: 'nav.toggle.mobile'},
        {viewport: 'mobile', mobile: true, selectedId: 'nav.toggle.mobile', rejectedId: 'nav.toggle.desktop'},
    ])('anchors the navigation step to the $viewport toggle', async ({mobile, selectedId, rejectedId}) => {
        stubMatchMedia({mobile});
        const desktop = makeAnchor();
        const mobileToggle = makeAnchor();
        guideAnchors.register('nav.toggle.desktop', desktop);
        guideAnchors.register('nav.toggle.mobile', mobileToggle);
        fakeGuideState.active = {flow: 'intro_tour', version: 1, stepId: 'intro.navigation', mode: 'automatic'};

        render(OnboardingOverlayHost, {currentPath: '/dashboard'});

        const selected = guideAnchors.get(selectedId);
        const rejected = guideAnchors.get(rejectedId);
        if (!selected || !rejected) throw new Error('Responsive navigation anchor fixture was not registered');
        await waitFor(() => expect(selected).toHaveAttribute('aria-describedby', DESCRIPTION_ID));
        await waitFor(() => expect(rejected).not.toHaveAttribute('aria-describedby'));
        expect(screen.getByTestId('onboarding-coachmark')).toHaveAttribute('data-step-id', 'intro.navigation');
    });
});

const INTRO_STEP_ANCHORS = [
    {stepId: 'intro.dashboard', anchorId: 'nav.dashboard', currentPath: '/dashboard', opensSidebar: true},
    {stepId: 'intro.transactions_nav', anchorId: 'nav.transactions', currentPath: '/dashboard', opensSidebar: true},
    {stepId: 'intro.brokers_nav', anchorId: 'nav.brokers', currentPath: '/dashboard', opensSidebar: true},
    {stepId: 'intro.fx_nav', anchorId: 'nav.fx', currentPath: '/dashboard', opensSidebar: true},
    {stepId: 'intro.assets_nav', anchorId: 'nav.assets', currentPath: '/dashboard', opensSidebar: true},
    {stepId: 'intro.tools_nav', anchorId: 'nav.tools', currentPath: '/dashboard', opensSidebar: true},
    {stepId: 'intro.settings_nav', anchorId: 'nav.settings', currentPath: '/dashboard', opensSidebar: true},
] as const;

describe('OnboardingOverlayHost — Core step map', () => {
    it.each(INTRO_STEP_ANCHORS)('$stepId resolves to $anchorId', async ({stepId, anchorId, currentPath, opensSidebar}) => {
        const anchor = makeAnchor();
        guideAnchors.register(anchorId, anchor);
        fakeGuideState.active = {flow: 'intro_tour', version: 1, stepId, mode: 'automatic'};
        const onrequestsidebar = vi.fn();

        render(OnboardingOverlayHost, {currentPath, onrequestsidebar});

        await waitFor(() => expect(anchor).toHaveAttribute('aria-describedby', DESCRIPTION_ID));
        expect(screen.getByTestId('onboarding-coachmark')).toHaveAttribute('data-step-id', stepId);
        expect(onrequestsidebar).toHaveBeenCalledWith(opensSidebar);
    });
});

/**
 * DeferredAppPopups — priority arbiter.
 *
 * `DonationPopupModal` and `UpdateAvailableModal` are mounted for real here
 * (not stand-ins): the behaviour under test is specifically what happens once
 * one of them opens its *own* `ModalBase`, which increments the very
 * `data-modal-scroll-lock-count` this component watches to defer around
 * *other* modals — a mock of either popup would sidestep exactly the
 * feedback-loop risk the last case exists to lock down. Both real popups are
 * driven through their genuine module-level stores (`donationPopup`,
 * `updateAvailable`), the same seam `DonationPopupModal.test.ts` /
 * `UpdateAvailableModal.test.ts` use, so no network or auth flow is needed to
 * arm them. `window.scrollTo` / `Element.prototype.getClientRects` and
 * `localStorage` are stubbed for the same reason those two files stub them:
 * real `ModalBase` scroll-locking and `UpdateAvailableModal`'s
 * `updatingGuideUrl()` touch jsdom APIs that either log or throw when
 * unstubbed, and none of that plumbing is what this suite is about.
 *
 * Assertions are all on `deferred-app-popups`'s own `data-active-popup` /
 * `data-modal-depth` attributes and on the two modals' `data-testid`s
 * (`donation-popup-modal`, `update-available-modal`) — never on copy, so the
 * cases hold in every shipped locale.
 */
const RELEASE = {version: '9.9.9', tag: 'v9.9.9', url: 'https://example.com/release-9.9.9', name: 'Test release'};

describe('DeferredAppPopups — priority arbiter', () => {
    const host = () => screen.getByTestId('deferred-app-popups');
    const storage = new Map<string, string>();

    beforeEach(() => {
        vi.spyOn(window, 'scrollTo').mockImplementation(() => {});
        vi.spyOn(Element.prototype, 'getClientRects').mockImplementation(() => [{x: 0, y: 0, width: 1, height: 1, top: 0, right: 1, bottom: 1, left: 0}] as unknown as DOMRectList);
        storage.clear();
        vi.stubGlobal('localStorage', {
            getItem: (k: string) => storage.get(k) ?? null,
            setItem: (k: string, v: string) => void storage.set(k, v),
            removeItem: (k: string) => void storage.delete(k),
        });
    });

    afterEach(() => {
        donationPopup.dismiss();
        updateAvailable.close();
        document.body.removeAttribute('data-modal-scroll-lock-count');
        vi.unstubAllGlobals();
    });

    it('shows neither popup while the onboarding guide is active, even though both are pending', async () => {
        donationPopup.trigger();
        updateAvailable.show(RELEASE);
        // Precondition check: both stores genuinely armed, so an absent popup
        // below is the guide suppressing them, not the trigger having failed.
        expect(donationPopup.shouldShow).toBe(true);
        expect(updateAvailable.release).not.toBeNull();

        render(DeferredAppPopups, {guideActive: true, currentVersion: '1.0.0'});
        await tick();

        await waitFor(() => expect(host()).toHaveAttribute('data-active-popup', 'none'));
        expect(screen.queryByTestId('donation-popup-modal')).toBeNull();
        expect(screen.queryByTestId('update-available-modal')).toBeNull();
    });

    it('defers both popups while an unrelated modal already holds the shared lock (nonzero modal depth)', async () => {
        document.body.setAttribute('data-modal-scroll-lock-count', '1');
        donationPopup.trigger();
        expect(donationPopup.shouldShow).toBe(true);

        render(DeferredAppPopups, {currentVersion: '1.0.0'});
        await tick();

        await waitFor(() => expect(host()).toHaveAttribute('data-active-popup', 'none'));
        expect(host()).toHaveAttribute('data-modal-depth', '1');
        expect(screen.queryByTestId('donation-popup-modal')).toBeNull();
    });

    it('picks the donation popup over a pending update when both are due at depth 0', async () => {
        updateAvailable.show(RELEASE);
        donationPopup.trigger();

        render(DeferredAppPopups, {currentVersion: '1.0.0'});

        await waitFor(() => expect(host()).toHaveAttribute('data-active-popup', 'donation'));
        expect(screen.getByTestId('donation-popup-modal')).toBeInTheDocument();
        expect(screen.queryByTestId('update-available-modal')).toBeNull();
    });

    it('shows the pending update once the donation popup is dismissed', async () => {
        updateAvailable.show(RELEASE);
        donationPopup.trigger();
        render(DeferredAppPopups, {currentVersion: '1.0.0'});
        await waitFor(() => expect(host()).toHaveAttribute('data-active-popup', 'donation'));

        await fireEvent.click(screen.getByTestId('donation-popup-later'));

        await waitFor(() => expect(host()).toHaveAttribute('data-active-popup', 'update'));
        expect(screen.getByTestId('update-available-modal')).toBeInTheDocument();
        expect(screen.queryByTestId('donation-popup-modal')).toBeNull();
    });

    it('keeps the active popup mounted once its own ModalBase locks the shared count, instead of reading its own lock as a reason to close (no feedback loop)', async () => {
        donationPopup.trigger();
        render(DeferredAppPopups, {currentVersion: '1.0.0'});
        await waitFor(() => expect(host()).toHaveAttribute('data-active-popup', 'donation'));

        // The donation modal's own ModalBase locks body scroll on mount, which
        // is what pushes data-modal-scroll-lock-count (and this host's mirrored
        // data-modal-depth) from 0 to 1 — observed asynchronously through the
        // MutationObserver, hence waitFor rather than a single tick.
        await waitFor(() => expect(host()).toHaveAttribute('data-modal-depth', '1'));
        expect(host()).toHaveAttribute('data-active-popup', 'donation');
        expect(screen.getByTestId('donation-popup-modal')).toBeInTheDocument();
    });
});
