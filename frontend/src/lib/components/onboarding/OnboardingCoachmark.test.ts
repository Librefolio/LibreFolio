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
import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';
import {tick} from 'svelte';
import {get} from 'svelte/store';

vi.mock('$app/environment', () => ({browser: true, dev: true, building: false, version: 'test'}));

/**
 * `onboardingGuide` (the module singleton `OnboardingOverlayHost` imports) is
 * replaced with a plain, test-owned object rather than driven through its real
 * factory: the overlay host only ever *reads* `.active`/`.error`/`.actionPending`
 * during this test's synchronous render, so a static snapshot is enough and
 * avoids reaching into the real controller/replay/storage machinery (already
 * covered end-to-end in `onboarding.test.ts`) just to prove a depth policy.
 * `INTRO_TOUR_STEP_IDS` and the rest of the module are left real via
 * `importOriginal`, so the semantic step ids stay the actual ones.
 */
const {fakeGuideState} = vi.hoisted(() => ({
    fakeGuideState: {
        active: null as {flow: 'intro_tour' | 'import_guide'; version: number; stepId: string; mode: 'automatic' | 'replay'} | null,
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
            setStep: vi.fn(),
            nextIntro: vi.fn(),
            previousIntro: vi.fn(),
            suspend: vi.fn(),
            finish: vi.fn(async () => undefined),
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
import {_} from '$lib/i18n';

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

function makeAnchor(): HTMLElement {
    const anchor = document.createElement('button');
    anchor.type = 'button';
    anchor.textContent = 'anchor target';
    document.body.appendChild(anchor);
    return anchor;
}

const DESCRIPTION_ID = 'onboarding-coachmark-description';
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
        expect(screen.queryByTestId('onboarding-coachmark-highlight')).toBeNull();
        expect(screen.getByText('BUSY_LABEL_TOKEN')).toBeInTheDocument();
    });

    it('is "anchored" once a connected anchor is supplied, and renders the highlight', () => {
        const anchor = makeAnchor();
        render(OnboardingCoachmark, {
            props: {
                open: true,
                anchor,
                stepId: 'step-1',
                title: 'Title',
                description: 'DESCRIPTION_TOKEN',
            },
        });

        const root = screen.getByTestId('onboarding-coachmark');
        expect(root).toHaveAttribute('data-guide-state', 'anchored');
        expect(screen.getByTestId('onboarding-coachmark-highlight')).toBeInTheDocument();
        expect(screen.getByText('DESCRIPTION_TOKEN')).toBeInTheDocument();
    });

    it('refreshes published highlight geometry when an ancestor navigation transition ends', async () => {
        const navigation = document.createElement('nav');
        const anchor = document.createElement('button');
        anchor.type = 'button';
        navigation.appendChild(anchor);
        document.body.appendChild(navigation);
        const rect = (left: number, top: number, width: number, height: number) =>
            ({
                x: left,
                y: top,
                left,
                top,
                right: left + width,
                bottom: top + height,
                width,
                height,
                toJSON: () => ({}),
            }) as DOMRect;
        let currentRect = rect(40, 50, 100, 40);
        vi.spyOn(anchor, 'getBoundingClientRect').mockImplementation(() => currentRect);

        render(OnboardingCoachmark, {
            props: {
                open: true,
                anchor,
                stepId: 'step-1',
                title: 'Title',
                description: 'Description',
                focusOnOpen: false,
            },
        });

        const highlight = screen.getByTestId('onboarding-coachmark-highlight');
        expect(highlight).toHaveStyle({left: '34px', top: '44px', width: '112px', height: '52px'});

        currentRect = rect(200, 160, 120, 50);
        navigation.dispatchEvent(new Event('transitionend'));
        await tick();

        expect(highlight).toHaveStyle({left: '194px', top: '154px', width: '132px', height: '62px'});
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

describe('OnboardingCoachmark — mobile placement', () => {
    it('renders as a bottom sheet (inline `bottom:` style) on a narrow viewport', () => {
        stubMatchMedia({mobile: true});
        render(OnboardingCoachmark, {
            props: {
                open: true,
                anchor: makeAnchor(),
                stepId: 'step-1',
                title: 'Title',
                description: 'Description',
            },
        });

        const panel = screen.getByTestId('onboarding-coachmark-panel');
        // Read the raw `style` attribute rather than `panel.style.bottom`: jsdom's CSSOM
        // does not understand `max()`/`env()`, so the parsed property can come back empty
        // even though the browser-facing attribute is exactly what the component wrote.
        const style = panel.getAttribute('style') ?? '';
        expect(style).toContain('bottom:');
        expect(style).not.toContain('left:');
        expect(style).not.toContain('top:');
    });

    it('positions relative to the anchor (no bottom-sheet style) off mobile', () => {
        stubMatchMedia({mobile: false});
        render(OnboardingCoachmark, {
            props: {
                open: true,
                anchor: makeAnchor(),
                stepId: 'step-1',
                title: 'Title',
                description: 'Description',
            },
        });

        const panel = screen.getByTestId('onboarding-coachmark-panel');
        const style = panel.getAttribute('style') ?? '';
        expect(style).not.toContain('bottom:');
    });
});

describe('OnboardingCoachmark — reduced motion', () => {
    it('scrolls the anchor into view instantly when the user prefers reduced motion', async () => {
        stubMatchMedia({reducedMotion: true});
        const scrollSpy = vi.spyOn(Element.prototype, 'scrollIntoView');
        render(OnboardingCoachmark, {
            props: {
                open: true,
                anchor: makeAnchor(),
                stepId: 'step-1',
                title: 'Title',
                description: 'Description',
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
                anchor: makeAnchor(),
                stepId: 'step-1',
                title: 'Title',
                description: 'Description',
            },
        });

        await waitFor(() => expect(scrollSpy).toHaveBeenCalled());
        const lastCall = scrollSpy.mock.calls.at(-1)?.[0] as ScrollIntoViewOptions;
        expect(lastCall.behavior).toBe('smooth');
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
 * `allowedModalDepth` is per-step, hard-coded in the component's own `steps`
 * table (0 for page anchors, 1 for the three tour-preview modals and import
 * bulk-apply, 2 for the deeper import-wizard steps): the host suspends its
 * coachmark — passes `open={false}` rather than unmounting the guide — once
 * `modalDepth` exceeds that budget. Each case below reads the live
 * `data-modal-scroll-lock-count` the real `Header`/modal stack maintains on
 * `document.body`, exactly as the component itself does, rather than asserting
 * against the allowance table by number.
 */
const MODAL_DEPTH_CASES = [
    {label: 'an intro-tour step is visible at its own baseline depth (0)', stepId: 'intro.transactions_import', flow: 'intro_tour', depth: 0, expectVisible: true, currentPath: '/transactions'},
    {label: 'an intro-tour step is suspended one modal deeper (depth 1)', stepId: 'intro.transactions_import', flow: 'intro_tour', depth: 1, expectVisible: false, currentPath: '/transactions'},
    {label: 'the broker currency preview remains visible inside its owned modal (depth 1)', stepId: 'intro.brokers_currency', flow: 'intro_tour', depth: 1, expectVisible: true, currentPath: '/brokers'},
    {label: 'the broker currency preview is suspended above its owned modal (depth 2)', stepId: 'intro.brokers_currency', flow: 'intro_tour', depth: 2, expectVisible: false, currentPath: '/brokers'},
    {label: 'the FX pair preview remains visible inside its owned modal (depth 1)', stepId: 'intro.fx_pair', flow: 'intro_tour', depth: 1, expectVisible: true, currentPath: '/fx'},
    {label: 'the asset configuration preview is suspended above its owned modal (depth 2)', stepId: 'intro.assets_config', flow: 'intro_tour', depth: 2, expectVisible: false, currentPath: '/assets'},
    {label: 'an import-wizard step stays visible through two nested modals (depth 2)', stepId: 'import.analyze', flow: 'import_guide', depth: 2, expectVisible: true, currentPath: '/transactions'},
    {label: 'an import-wizard step is suspended a third modal deeper (depth 3)', stepId: 'import.analyze', flow: 'import_guide', depth: 3, expectVisible: false, currentPath: '/transactions'},
    {label: 'the bulk-apply step is visible through one modal (depth 1)', stepId: 'import.bulk', flow: 'import_guide', depth: 1, expectVisible: true, currentPath: '/transactions'},
    {label: 'the bulk-apply step is suspended a second modal deeper (depth 2)', stepId: 'import.bulk', flow: 'import_guide', depth: 2, expectVisible: false, currentPath: '/transactions'},
] as const;

describe('OnboardingOverlayHost — modal-depth suspension policy', () => {
    afterEach(() => {
        document.body.removeAttribute('data-modal-scroll-lock-count');
    });

    it.each(MODAL_DEPTH_CASES)('$label', async ({stepId, flow, depth, expectVisible, currentPath}) => {
        fakeGuideState.active = {flow, version: 1, stepId, mode: 'automatic'};
        document.body.setAttribute('data-modal-scroll-lock-count', String(depth));

        render(OnboardingOverlayHost, {currentPath});
        await tick();

        if (expectVisible) {
            expect(screen.getByTestId('onboarding-coachmark-panel')).toBeInTheDocument();
        } else {
            expect(screen.queryByTestId('onboarding-coachmark-panel')).toBeNull();
        }
    });
});

describe('OnboardingOverlayHost — backdrop policy', () => {
    it('renders the intro-tour backdrop when the host requests interception', async () => {
        const anchor = makeAnchor();
        guideAnchors.register('transactions.import', anchor);
        fakeGuideState.active = {flow: 'intro_tour', version: 1, stepId: 'intro.transactions_import', mode: 'automatic'};

        render(OnboardingOverlayHost, {currentPath: '/transactions'});

        await waitFor(() => expect(anchor).toHaveAttribute('aria-describedby', DESCRIPTION_ID));
        expect(screen.getByTestId('onboarding-coachmark')).toHaveAttribute('data-step-id', 'intro.transactions_import');
        expect(screen.getByTestId('onboarding-coachmark-backdrop')).toBeInTheDocument();
    });

    it('keeps the Import guide interactive by rendering its coachmark without a backdrop', async () => {
        const anchor = makeAnchor();
        guideAnchors.register('import.upload', anchor);
        fakeGuideState.active = {flow: 'import_guide', version: 1, stepId: 'import.upload', mode: 'automatic'};

        render(OnboardingOverlayHost, {currentPath: '/transactions'});

        await waitFor(() => expect(anchor).toHaveAttribute('aria-describedby', DESCRIPTION_ID));
        expect(screen.getByTestId('onboarding-coachmark')).toHaveAttribute('data-step-id', 'import.upload');
        expect(screen.getByTestId('onboarding-coachmark-panel')).toBeInTheDocument();
        expect(screen.queryByTestId('onboarding-coachmark-backdrop')).toBeNull();
    });
});

describe('OnboardingOverlayHost — terminal action label', () => {
    it.each([
        {mode: 'replay', key: 'onboarding.actions.exitReplay'},
        {mode: 'automatic', key: 'onboarding.actions.skipPermanently'},
    ] as const)('passes the $key translation to the $mode top action', async ({mode, key}) => {
        const anchor = makeAnchor();
        guideAnchors.register('import.upload', anchor);
        fakeGuideState.active = {flow: 'import_guide', version: 1, stepId: 'import.upload', mode};

        render(OnboardingOverlayHost, {currentPath: '/transactions'});

        await waitFor(() => expect(anchor).toHaveAttribute('aria-describedby', DESCRIPTION_ID));
        const topActions = screen.getByTestId('onboarding-coachmark-top-actions');
        const skip = within(topActions).getByTestId('onboarding-coachmark-skip');
        expect(skip.textContent?.trim()).toBe(get(_)(key));
    });
});

describe('OnboardingOverlayHost — intro scene and responsive navigation anchor', () => {
    it('renders the intro scene instead of a coachmark and advances only from its Start action', async () => {
        fakeGuideState.active = {flow: 'intro_tour', version: 1, stepId: 'intro.scene', mode: 'automatic'};

        render(OnboardingOverlayHost, {currentPath: '/dashboard'});
        await tick();

        expect(screen.getByTestId('onboarding-intro-scene')).toBeInTheDocument();
        expect(screen.queryByTestId('onboarding-coachmark')).toBeNull();
        expect(onboardingGuide.nextIntro).not.toHaveBeenCalled();

        await fireEvent.click(screen.getByTestId('onboarding-intro-start'));

        expect(onboardingGuide.nextIntro).toHaveBeenCalledTimes(1);
        expect(onboardingGuide.skip).not.toHaveBeenCalled();
        expect(onboardingGuide.suspend).not.toHaveBeenCalled();
    });

    it('routes the intro scene close action through suspend, never through terminal skip', async () => {
        fakeGuideState.active = {flow: 'intro_tour', version: 1, stepId: 'intro.scene', mode: 'automatic'};

        render(OnboardingOverlayHost, {currentPath: '/dashboard'});
        await fireEvent.click(screen.getByTestId('onboarding-intro-close'));

        expect(onboardingGuide.suspend).toHaveBeenCalledExactlyOnceWith({resetImport: false});
        expect(onboardingGuide.skip).not.toHaveBeenCalled();
    });

    it('routes the intro scene permanent Skip through the terminal skip action, never suspend', async () => {
        fakeGuideState.active = {flow: 'intro_tour', version: 1, stepId: 'intro.scene', mode: 'automatic'};

        render(OnboardingOverlayHost, {currentPath: '/dashboard'});
        await fireEvent.click(screen.getByTestId('onboarding-intro-skip'));

        await waitFor(() => expect(onboardingGuide.skip).toHaveBeenCalledTimes(1));
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
    {stepId: 'intro.dashboard', anchorId: 'page.dashboard', currentPath: '/dashboard', opensSidebar: false},
    {stepId: 'intro.transactions_nav', anchorId: 'nav.transactions', currentPath: '/dashboard', opensSidebar: true},
    {stepId: 'intro.transactions_import', anchorId: 'transactions.import', currentPath: '/transactions', opensSidebar: false},
    {stepId: 'intro.brokers_add', anchorId: 'brokers.add', currentPath: '/brokers', opensSidebar: false},
    {stepId: 'intro.brokers_currency', anchorId: 'brokers.currency', currentPath: '/brokers', opensSidebar: false},
    {stepId: 'intro.fx_add', anchorId: 'fx.add', currentPath: '/fx', opensSidebar: false},
    {stepId: 'intro.fx_pair', anchorId: 'fx.pair', currentPath: '/fx', opensSidebar: false},
    {stepId: 'intro.assets_add', anchorId: 'assets.add', currentPath: '/assets', opensSidebar: false},
    {stepId: 'intro.assets_config', anchorId: 'assets.config', currentPath: '/assets', opensSidebar: false},
    {stepId: 'intro.tools', anchorId: 'tools.hub', currentPath: '/tools', opensSidebar: true},
    {stepId: 'intro.settings', anchorId: 'onboarding.settings', currentPath: '/settings', opensSidebar: true},
] as const;

describe('OnboardingOverlayHost — Round 1 step map', () => {
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
