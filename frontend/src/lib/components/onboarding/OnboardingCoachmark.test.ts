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

vi.mock('$app/environment', () => ({browser: true, dev: true, building: false, version: 'test'}));

import {cleanup, fireEvent, render, screen, setupI18n, waitFor} from '$test/component';
import OnboardingCoachmark from './OnboardingCoachmark.svelte';

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

beforeEach(async () => {
    await setupI18n();
    stubMatchMedia();
});

afterEach(() => {
    cleanup();
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

describe('OnboardingCoachmark — keyboard: Escape pauses, never skips', () => {
    it('Escape calls onpause and never onskip while open', async () => {
        const onpause = vi.fn();
        const onskip = vi.fn();
        render(OnboardingCoachmark, {
            props: {
                open: true,
                anchor: makeAnchor(),
                stepId: 'step-1',
                title: 'Title',
                description: 'Description',
                onpause,
                onskip,
            },
        });

        await fireEvent.keyDown(window, {key: 'Escape'});

        expect(onpause).toHaveBeenCalledTimes(1);
        expect(onskip).not.toHaveBeenCalled();
    });

    it('ignores Escape entirely while closed', async () => {
        const onpause = vi.fn();
        render(OnboardingCoachmark, {
            props: {
                open: false,
                anchor: null,
                stepId: 'step-1',
                title: 'Title',
                description: 'Description',
                onpause,
            },
        });

        await fireEvent.keyDown(window, {key: 'Escape'});

        expect(onpause).not.toHaveBeenCalled();
    });

    it('a different key while open calls neither onpause nor onskip', async () => {
        const onpause = vi.fn();
        const onskip = vi.fn();
        render(OnboardingCoachmark, {
            props: {
                open: true,
                anchor: makeAnchor(),
                stepId: 'step-1',
                title: 'Title',
                description: 'Description',
                onpause,
                onskip,
            },
        });

        await fireEvent.keyDown(window, {key: 'Enter'});

        expect(onpause).not.toHaveBeenCalled();
        expect(onskip).not.toHaveBeenCalled();
    });
});

describe('OnboardingCoachmark — next/back/skip/pause callbacks', () => {
    it('fires exactly the callback for the button clicked, and only that one', async () => {
        const onnext = vi.fn();
        const onback = vi.fn();
        const onskip = vi.fn();
        const onpause = vi.fn();
        render(OnboardingCoachmark, {
            props: {
                open: true,
                anchor: makeAnchor(),
                stepId: 'step-1',
                title: 'Title',
                description: 'Description',
                showPause: true,
                onnext,
                onback,
                onskip,
                onpause,
            },
        });

        await fireEvent.click(screen.getByTestId('onboarding-coachmark-next'));
        expect(onnext).toHaveBeenCalledTimes(1);
        expect(onback).not.toHaveBeenCalled();
        expect(onskip).not.toHaveBeenCalled();
        expect(onpause).not.toHaveBeenCalled();

        await fireEvent.click(screen.getByTestId('onboarding-coachmark-back'));
        expect(onback).toHaveBeenCalledTimes(1);

        await fireEvent.click(screen.getByTestId('onboarding-coachmark-skip'));
        expect(onskip).toHaveBeenCalledTimes(1);

        await fireEvent.click(screen.getByTestId('onboarding-coachmark-pause'));
        expect(onpause).toHaveBeenCalledTimes(1);

        // Clicking pause must never also count as a skip, and vice versa.
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
                showPause: false,
            },
        });

        expect(screen.queryByTestId('onboarding-coachmark-back')).toBeNull();
        expect(screen.queryByTestId('onboarding-coachmark-skip')).toBeNull();
        expect(screen.queryByTestId('onboarding-coachmark-pause')).toBeNull();
        expect(screen.getByTestId('onboarding-coachmark-next')).toBeInTheDocument();
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
