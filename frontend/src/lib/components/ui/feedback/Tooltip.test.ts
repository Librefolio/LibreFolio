// @vitest-environment jsdom
/**
 * Tooltip — two contracts of the shared primitive (workstream K).
 *
 * A hostile `html` prop is sanitised before `{@html}` (step 13, item 0). `Tooltip` renders its `html`
 * prop — or `text`, escaped — as raw HTML, and callers hand it markup assembled from names, notes and
 * validation messages. The prop must come out without anything that runs, and with the harmless markup
 * the app itself uses (icons, emoji flags) intact.
 *
 * No callback survives destroy (step 14, item 1). The tooltip arms its own callbacks — the hover-open
 * delay, the thirty-second grace of a pinned tooltip once the pointer leaves or the touch ends, the
 * animation frame that positions it — and an unmounted instance must take every one of them with it: a
 * callback that outlives its component runs against state nothing renders any more, and under Vitest it
 * can run after jsdom has been torn down. Driven on fake timers and read with `vi.getTimerCount()` right
 * after an explicit unmount.
 *
 * Registered in `front_component_unit` (`scripts/test_runner/_frontend_utility.py`, action
 * `component-unit`).
 */
import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';
import {mount, unmount, flushSync} from 'svelte';
import {cleanup, fireEvent, render, screen, within} from '$test/component';
import Tooltip from './Tooltip.svelte';

/**
 * Evaluate `expression` in the page's own realm — the one inline handlers run in — and return the
 * result as a string. Vitest's jsdom environment hands the test the Node global as `window` (even
 * `document.defaultView` answers it, measured), while jsdom compiles inline handlers against its own
 * window object: a global written by a payload is invisible from the test, and readable only from
 * another inline handler. This runs one on a probe element and reads back what it computed.
 */
function inPage(expression: string): string | null {
    const probe = document.createElement('i');
    probe.setAttribute('onclick', `this.setAttribute('data-result', String(${expression}))`);
    document.body.appendChild(probe);
    probe.click();
    const result = probe.getAttribute('data-result');
    probe.remove();
    return result;
}

/**
 * Fire on every image of `root` the `error` a browser fires for `src=x` — after re-arming the inline
 * handlers. jsdom leaves an `on*` attribute inert when its element was parsed inside a `<template>` and
 * then moved into the page, which is exactly how Svelte inserts `{@html}` (measured on jsdom 30: a
 * moved node runs nothing; the same node with its attribute set again runs it). A browser compiles the
 * attribute when the event fires instead — `e2e/assets/asset-name-xss.spec.ts` proves it in Chromium —
 * so setting it again reproduces the browser, it does not invent a handler: one the sanitiser removed
 * stays removed. No clock is involved; the handler, if any, has run when this returns.
 */
function fireImageErrors(root: Element): void {
    for (const el of root.querySelectorAll('*')) {
        for (const name of el.getAttributeNames()) if (name.toLowerCase().startsWith('on')) el.setAttribute(name, el.getAttribute(name) ?? '');
    }
    for (const img of root.querySelectorAll('img')) img.dispatchEvent(new Event('error'));
}

// The toast payload of the same report, with a probe of its own.
const HOSTILE = '<img src=x onerror="window.__k13Tooltip=1"><span class="emoji-flag">🇮🇹</span> Saved';

afterEach(() => {
    cleanup();
    inPage('delete window.__k13Tooltip');
});

describe('Tooltip — a hostile html prop is sanitised, not executed (K step 13, item 0)', () => {
    it('renders the content without its handler and keeps its harmless markup', async () => {
        // The probe must be able to see a handler run, or "nothing ran" below would mean nothing.
        expect(inPage('(window.__k13Probe = 7)')).toBe('7');
        expect(inPage('window.__k13Probe')).toBe('7');
        inPage('delete window.__k13Probe');

        render(Tooltip, {props: {html: HOSTILE}});
        // Enter on the trigger opens the tooltip at once: the keyboard path has no hover delay to wait out.
        await fireEvent.keyDown(screen.getByRole('button'), {key: 'Enter'});
        const content = await screen.findByTestId('tooltip-content');
        expect(content).toHaveTextContent('Saved');
        // The flag span is markup the app legitimately sends: the class is the subject here.
        const flag = content.querySelector('span.emoji-flag');
        expect(flag).not.toBeNull();
        expect(flag).toHaveTextContent('🇮🇹');

        expect
            .soft(
                [...content.querySelectorAll('[onerror]')].map((el) => el.outerHTML),
                'no element of the tooltip may carry an onerror attribute',
            )
            .toEqual([]);

        // Fire the image error a browser would fire: a handler that survived runs now.
        fireImageErrors(content);
        expect.soft(inPage('window.__k13Tooltip'), 'the payload ran as script in the tooltip').toBe('undefined');
    });
});

/**
 * Each case arms one callback through the interaction a user performs, proves it is on the clock, destroys
 * the tooltip at once and counts what is left. "At once" is the subject, not haste. For the timers, the
 * destroy teardown reads their handles, and a handle written since the last effect flush reads back as the
 * value it had before the write (Svelte keeps it in `old_values` until a flush clears it) — `null`, so the
 * live timer is never cleared. Anything that re-renders the tooltip in between, such as advancing the clock
 * over its position frame, flushes that record away and turns the case green for the wrong reason
 * (measured: the pinned case passes on the defective code that way).
 *
 * The position frame `show()` schedules is cancelled by another teardown, the listeners effect's, which
 * exists only once that effect has re-run with the tooltip open: a tooltip destroyed before its first
 * re-render after the open — a parent removing it in the batch that opened it — leaves the frame behind.
 * testing-library's `unmount()` cannot destroy a tooltip that early, so the last case mounts and unmounts
 * it through Svelte itself.
 */
describe('Tooltip — no callback survives destroy (K step 14, item 1)', () => {
    // Installed before the render: the handlers resolve `setTimeout` and `requestAnimationFrame` from the
    // global when they run, so the fake clock must be in place before the event that arms them — otherwise
    // they land on the real one, where `vi.getTimerCount()` cannot see them.
    beforeEach(() => {
        vi.useFakeTimers();
    });

    // Inner hooks run first: this one precedes the file-level `afterEach` and testing-library's own cleanup
    // (`await act(); cleanup()`, returned by its `beforeEach`, so it runs after every `afterEach`). A case
    // that failed before its `unmount()` leaves a tooltip mounted: unmount it while the clock that issued its
    // handles is still installed, then restore the real one. Whatever is left on the fake clock is discarded
    // with it and can never fire; the later cleanups find nothing to unmount and arm no timer.
    afterEach(() => {
        cleanup();
        vi.useRealTimers();
    });

    it('counts animation frames on the fake clock, so the zeros below cover the position frame too', () => {
        // Positive control of the count itself: every opening path schedules a position frame — the last case
        // is about nothing else — and a zero after unmount says nothing about frames unless this environment's
        // fake clock sees them.
        const before = vi.getTimerCount();
        const frame = requestAnimationFrame(() => {});
        expect(vi.getTimerCount(), 'a faked requestAnimationFrame must be on the clock').toBe(before + 1);
        cancelAnimationFrame(frame);
        expect(vi.getTimerCount()).toBe(before);
    });

    it('cancels a pending hover open', async () => {
        const {unmount} = render(Tooltip, {props: {text: 'Hover probe'}});
        const before = vi.getTimerCount();

        await fireEvent.mouseEnter(screen.getByRole('button'));
        // Positive control: the open delay is on the clock and has not elapsed, the tooltip is still closed.
        expect(vi.getTimerCount(), 'mouseenter must arm the hover-open delay').toBeGreaterThan(before);
        expect(screen.queryByTestId('tooltip-content')).toBeNull();

        unmount();
        expect(vi.getTimerCount(), 'callbacks still pending after unmount').toBe(0);
    });

    it('cancels the grace of a pinned tooltip once the pointer has left', async () => {
        const {unmount} = render(Tooltip, {props: {text: 'Pinned probe'}});
        const trigger = screen.getByRole('button');

        // A click opens the tooltip and pins it, so leaving arms the thirty-second grace.
        await fireEvent.click(trigger);
        expect(screen.getByTestId('tooltip-content')).toBeInTheDocument();
        const before = vi.getTimerCount();
        await fireEvent.mouseLeave(trigger);
        expect(vi.getTimerCount(), 'mouseleave must arm the pinned grace').toBeGreaterThan(before);

        unmount();
        expect(vi.getTimerCount(), 'callbacks still pending after unmount').toBe(0);
    });

    it('cancels the grace of a tooltip a touch has opened and released', async () => {
        const {unmount} = render(Tooltip, {props: {text: 'Touch probe'}});
        const trigger = screen.getByRole('button');

        // A touch opens the tooltip pinned; the grace starts only when the contact ends.
        await fireEvent.touchStart(trigger);
        expect(screen.getByTestId('tooltip-content')).toBeInTheDocument();
        const before = vi.getTimerCount();
        await fireEvent.touchEnd(trigger);
        expect(vi.getTimerCount(), 'touchend must arm the pinned grace').toBeGreaterThan(before);

        unmount();
        expect(vi.getTimerCount(), 'callbacks still pending after unmount').toBe(0);
    });

    it('cancels the position frame of a tooltip destroyed before its first re-render', () => {
        // Not `render().unmount()`: svelte-core's is `flushSync(() => unmount(component))`
        // (`@testing-library/svelte-core/src/mount.js`), and `flushSync` runs the pending effects first
        // (`svelte/src/internal/client/reactivity/batch.js`), so it cannot reach this path — measured green on
        // the defective code.
        const target = document.body.appendChild(document.createElement('div'));
        let component: ReturnType<typeof mount> | null = null;
        try {
            component = mount(Tooltip, {target, props: {text: 'Frame probe'}});
            // Steady state: every effect has run once, with the tooltip closed.
            flushSync();
            const before = vi.getTimerCount();

            // Opened in this task with no flush after it: the raw event, not `fireEvent`, which flushes.
            within(target)
                .getByRole('button')
                .dispatchEvent(new KeyboardEvent('keydown', {key: 'Enter', bubbles: true}));
            // Positive controls: the position frame is on the clock, and the tooltip has not re-rendered.
            expect(vi.getTimerCount(), 'Enter must schedule the position frame').toBeGreaterThan(before);
            expect(screen.queryByTestId('tooltip-content'), 'the tooltip must not have re-rendered yet').toBeNull();

            const tooltip = component;
            component = null;
            void unmount(tooltip);
            expect(vi.getTimerCount(), 'callbacks still pending after unmount').toBe(0);
        } finally {
            // A case that failed before its destroy leaves the tooltip mounted: take it down with its container.
            if (component) void unmount(component);
            target.remove();
        }
    });
});
