/**
 * Shared entry point for Svelte component tests (Vitest + jsdom).
 *
 * Why this file exists at all: a component test needs three things that are easy
 * to get subtly wrong, and getting them wrong produces a green test that proves
 * nothing. Centralising them means each spec states its subject and nothing else.
 *
 *   1. jest-dom matchers (`toBeVisible`, `toBeDisabled`, …). Without them the
 *      only available assertion is on raw DOM properties, which drifts from what
 *      the user actually perceives.
 *   2. A real, initialised svelte-i18n. Components call `$_('some.key')`; with an
 *      uninitialised store that call throws, and the failure looks like a broken
 *      component instead of a broken harness.
 *   3. `@testing-library/svelte` re-exports, so a spec never reaches for the
 *      package directly and the harness stays swappable.
 *
 * This directory is excluded from coverage on purpose (see `mcr.shared.js`:
 * `__tests__` and `__mocks__` are skipped while collecting `ourSources`), so the
 * harness never inflates the numbers it exists to improve.
 *
 * Usage — the environment docblock is per-file and mandatory:
 *
 *     // @vitest-environment jsdom
 *     import {render, screen, setupI18n} from '$test/component';
 */
import '@testing-library/jest-dom/vitest';
import {init, waitLocale} from 'svelte-i18n';

/**
 * jsdom implements the DOM, not the layout engine, so anything that scrolls is
 * simply absent: `Element.prototype.scrollIntoView` is undefined and calling it
 * throws `TypeError: el?.scrollIntoView is not a function`.
 *
 * Stubbing it here rather than adding `?.` in the components is deliberate. A
 * defensive optional call in production code to satisfy a test environment reads
 * as "this might not exist in a browser", which is false, and it would hide the
 * day the call genuinely disappears. The gap belongs to the harness, so the
 * harness fills it.
 */
if (typeof Element !== 'undefined' && !Element.prototype.scrollIntoView) {
    Element.prototype.scrollIntoView = function scrollIntoView() {};
}

/**
 * Same gap, second instance: jsdom ships no Web Animations API, so
 * `Element.prototype.animate` is undefined and *any* Svelte `transition:` throws
 * `TypeError: element.animate is not a function` while mounting. A component
 * that merely fades in would therefore be untestable, which is a property of the
 * environment and not of the component.
 *
 * The stub behaves like an animation that has already finished: it reports
 * `playState: 'finished'` (so Svelte's tick loop exits at once) and fires
 * `onfinish` on the next microtask, which is when the handler has been attached.
 * The transition consequently resolves within the same `await` the test already
 * performs, instead of never resolving and leaving elements stuck mid-outro.
 */
if (typeof Element !== 'undefined' && !Element.prototype.animate) {
    Element.prototype.animate = function animate(): Animation {
        let settled = false;
        const animation = {
            onfinish: null as ((this: Animation) => void) | null,
            oncancel: null as ((this: Animation) => void) | null,
            currentTime: 0,
            playState: 'finished',
            effect: null,
            finished: Promise.resolve(),
            cancel() {
                settled = true;
            },
            finish() {},
            play() {},
            pause() {},
            addEventListener() {},
            removeEventListener() {},
        };
        queueMicrotask(() => {
            if (settled) return;
            settled = true;
            animation.onfinish?.call(animation as unknown as Animation);
        });
        return animation as unknown as Animation;
    } as typeof Element.prototype.animate;
}

/**
 * Third instance: `ResizeObserver` is a layout observer, so jsdom has none. The
 * `scrollOnOverflow` action instantiates one unconditionally, which makes every
 * component using an overflow-scrolling label (the whole table filter family)
 * blow up on mount.
 *
 * The stub is inert on purpose. It must never invent a callback: firing one with
 * a fabricated size would let a test assert on overflow behaviour that jsdom
 * cannot actually produce — a green that means nothing. Overflow is E2E
 * territory; here the observer just has to exist.
 */
if (typeof globalThis.ResizeObserver === 'undefined') {
    globalThis.ResizeObserver = class ResizeObserver {
        observe() {}
        unobserve() {}
        disconnect() {}
    } as unknown as typeof globalThis.ResizeObserver;
}

/**
 * Fourth instance: jsdom has no media-query engine, so `window.matchMedia` is
 * undefined — and `svelte/motion` builds a `(prefers-reduced-motion)` query at
 * import time, which makes every component that tweens a value (KPI cards,
 * metric bars) throw before its first render.
 *
 * The stub answers "no preference / no match" for everything. That is the
 * honest default for these tests: they assert the *value* a tween targets, not
 * the animation curve, and reduced-motion is a rendering preference jsdom has
 * no opinion about.
 */
if (typeof window !== 'undefined' && typeof window.matchMedia !== 'function') {
    window.matchMedia = (query: string): MediaQueryList =>
        ({
            matches: false,
            media: query,
            onchange: null,
            addListener() {},
            removeListener() {},
            addEventListener() {},
            removeEventListener() {},
            dispatchEvent: () => false,
        }) as MediaQueryList;
}

export {render, screen, fireEvent, within, waitFor, cleanup} from '@testing-library/svelte';

/**
 * Boot svelte-i18n once per test file.
 *
 * English is used because it is the fallback locale of the app, not because the
 * tests read English: a component test must never assert on a translated string
 * (the UI ships in EN/IT/FR/ES). Assert on `data-testid`, on ARIA roles, or on
 * values the test itself passed in as props.
 *
 * `waitLocale()` is what makes this deterministic: `register()` loads the
 * dictionaries through dynamic `import()`, so without awaiting it the first
 * render can land while the catalogue is still empty and every label renders as
 * its own key. That failure is intermittent by construction — exactly the class
 * of flake this suite refuses to ship.
 */
export async function setupI18n(locale = 'en'): Promise<void> {
    init({fallbackLocale: 'en', initialLocale: locale});
    await waitLocale(locale);
}
