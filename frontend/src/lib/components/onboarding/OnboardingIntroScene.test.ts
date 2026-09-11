// @vitest-environment jsdom
/**
 * OnboardingIntroScene — timed three-phase introduction.
 *
 * Time is entirely test-owned: fake timers advance the component's three
 * scheduled transitions without sleeping. The i18n store is a tiny reactive
 * probe so locale changes can be asserted as translator calls rather than by
 * pinning this test to any shipped language's prose.
 */
import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';

const {translate} = vi.hoisted(() => ({
    translate: vi.fn((activeLocale: string, key: string) => `${activeLocale}:${key}`),
}));

vi.mock('$lib/i18n', async () => {
    const {derived, writable} = await import('svelte/store');
    const locale = writable('en');
    return {
        locale,
        _: derived(locale, (activeLocale) => (key: string) => translate(activeLocale, key)),
    };
});

import {tick} from 'svelte';
import {locale} from '$lib/i18n';
import {cleanup, fireEvent, render, screen} from '$test/component';
import OnboardingIntroScene from './OnboardingIntroScene.svelte';

interface MediaFixture {
    addEventListener: ReturnType<typeof vi.fn>;
    removeEventListener: ReturnType<typeof vi.fn>;
}

function stubReducedMotion(matches = false): MediaFixture {
    const addEventListener = vi.fn();
    const removeEventListener = vi.fn();
    vi.stubGlobal(
        'matchMedia',
        vi.fn(
            (query: string) =>
                ({
                    matches: query === '(prefers-reduced-motion: reduce)' ? matches : false,
                    media: query,
                    onchange: null,
                    addListener: vi.fn(),
                    removeListener: vi.fn(),
                    addEventListener,
                    removeEventListener,
                    dispatchEvent: () => false,
                }) as MediaQueryList,
        ),
    );
    return {addEventListener, removeEventListener};
}

async function mount(overrides: Record<string, unknown> = {}) {
    const onstart = vi.fn();
    const onskip = vi.fn();
    const onclose = vi.fn();
    const view = render(OnboardingIntroScene, {
        open: true,
        onstart,
        onskip,
        onclose,
        ...overrides,
    });
    await tick();
    return {onstart, onskip, onclose, ...view};
}

beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(1_000);
    locale.set('en');
    translate.mockClear();
});

afterEach(() => {
    cleanup();
    expect(vi.getTimerCount()).toBe(0);
    vi.useRealTimers();
    vi.unstubAllGlobals();
});

describe('OnboardingIntroScene — phases and start timing', () => {
    it('publishes the three automatic phases at 33% and 66% of the default duration', async () => {
        stubReducedMotion();
        const {onstart} = await mount();
        const scene = screen.getByTestId('onboarding-intro-scene');

        expect(scene).toHaveAttribute('data-state', 'intro-scene');
        expect(scene).toHaveAttribute('data-phase', 'welcome');

        await vi.advanceTimersByTimeAsync(3_299);
        expect(scene).toHaveAttribute('data-phase', 'welcome');
        await vi.advanceTimersByTimeAsync(1);
        await tick();
        expect(scene).toHaveAttribute('data-phase', 'aboard');

        await vi.advanceTimersByTimeAsync(3_299);
        expect(scene).toHaveAttribute('data-phase', 'aboard');
        await vi.advanceTimersByTimeAsync(1);
        await tick();
        expect(scene).toHaveAttribute('data-phase', 'tour');
        expect(onstart).not.toHaveBeenCalled();
    });

    it('starts immediately from the manual Start action and invalidates the pending automatic start', async () => {
        stubReducedMotion();
        const {onstart} = await mount();

        await fireEvent.click(screen.getByTestId('onboarding-intro-start'));

        expect(onstart).toHaveBeenCalledTimes(1);
        await vi.advanceTimersByTimeAsync(10_000);
        expect(onstart).toHaveBeenCalledTimes(1);
    });

    it('auto-starts exactly once at the published default 10-second deadline', async () => {
        stubReducedMotion();
        const {onstart} = await mount();
        const scene = screen.getByTestId('onboarding-intro-scene');

        expect(scene).toHaveAttribute('data-auto-start-at', '11000');
        await vi.advanceTimersByTimeAsync(9_999);
        expect(onstart).not.toHaveBeenCalled();

        await vi.advanceTimersByTimeAsync(1);
        expect(onstart).toHaveBeenCalledTimes(1);

        await vi.advanceTimersByTimeAsync(10_000);
        expect(onstart).toHaveBeenCalledTimes(1);
    });

    it('resolves a click immediately before the deadline as one start, not a timer race duplicate', async () => {
        stubReducedMotion();
        const {onstart} = await mount();

        await vi.advanceTimersByTimeAsync(9_999);
        await fireEvent.click(screen.getByTestId('onboarding-intro-start'));
        await vi.advanceTimersByTimeAsync(1);

        expect(onstart).toHaveBeenCalledTimes(1);
    });
});

describe('OnboardingIntroScene — terminal and suspend controls', () => {
    it('renders a supplied guide error as an alert while the scene is open', async () => {
        stubReducedMotion();
        await mount({error: 'OWNED_SKIP_ERROR_TOKEN'});

        expect(screen.getByTestId('onboarding-intro-scene')).toBeInTheDocument();
        const error = screen.getByTestId('onboarding-intro-error');
        expect(error).toHaveAttribute('role', 'alert');
        expect(error).toHaveTextContent('OWNED_SKIP_ERROR_TOKEN');
    });

    it('renders the supplied skip label', async () => {
        stubReducedMotion();
        await mount({skipLabel: 'OWNED_SKIP_LABEL_TOKEN'});

        expect(screen.getByTestId('onboarding-intro-skip')).toHaveTextContent('OWNED_SKIP_LABEL_TOKEN');
    });

    it('routes X only to the close callback', async () => {
        stubReducedMotion();
        const {onstart, onskip, onclose} = await mount();

        await fireEvent.click(screen.getByTestId('onboarding-intro-close'));

        expect(onclose).toHaveBeenCalledTimes(1);
        expect(onskip).not.toHaveBeenCalled();
        expect(onstart).not.toHaveBeenCalled();
    });

    it('routes Escape only to the close callback', async () => {
        stubReducedMotion();
        const {onstart, onskip, onclose} = await mount();

        await fireEvent.keyDown(window, {key: 'Escape'});

        expect(onclose).toHaveBeenCalledTimes(1);
        expect(onskip).not.toHaveBeenCalled();
        expect(onstart).not.toHaveBeenCalled();
    });

    it('routes permanent Skip only to the skip callback', async () => {
        stubReducedMotion();
        const {onstart, onskip, onclose} = await mount();

        await fireEvent.click(screen.getByTestId('onboarding-intro-skip'));
        await vi.advanceTimersByTimeAsync(10_000);

        expect(onskip).toHaveBeenCalledTimes(1);
        expect(onclose).not.toHaveBeenCalled();
        expect(onstart).not.toHaveBeenCalled();
    });
});

describe('OnboardingIntroScene — reduced motion, locale, and teardown', () => {
    it('keeps one static phase and composes all three phrase keys under reduced motion', async () => {
        stubReducedMotion(true);
        await mount();
        const scene = screen.getByTestId('onboarding-intro-scene');

        const phraseKeys = new Set(translate.mock.calls.filter(([, key]) => key.startsWith('onboarding.intro.line')).map(([, key]) => key));
        expect(phraseKeys).toEqual(new Set(['onboarding.intro.line1', 'onboarding.intro.line2', 'onboarding.intro.line3']));

        await vi.advanceTimersByTimeAsync(6_600);
        expect(scene).toHaveAttribute('data-phase', 'welcome');
    });

    it('re-evaluates the open phrase when the locale changes', async () => {
        stubReducedMotion();
        await mount();
        translate.mockClear();

        locale.set('it');
        await tick();

        expect(translate).toHaveBeenCalledWith('it', 'onboarding.intro.line1');
        expect(screen.getByTestId('onboarding-intro-scene')).toHaveAttribute('data-phase', 'welcome');
    });

    it('clears all scheduled work and removes the media listener on unmount', async () => {
        const media = stubReducedMotion();
        const view = await mount();

        expect(vi.getTimerCount()).toBe(3);
        expect(media.addEventListener).toHaveBeenCalledWith('change', expect.any(Function));

        view.unmount();

        expect(vi.getTimerCount()).toBe(0);
        expect(media.removeEventListener).toHaveBeenCalledWith('change', expect.any(Function));
    });
});
