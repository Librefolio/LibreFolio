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
import {createRawSnippet, mount, unmount, flushSync} from 'svelte';
import {cleanup, fireEvent, render, screen, waitFor, within} from '$test/component';
import Tooltip from './Tooltip.svelte';
import TooltipInControlHarness from './__tests__/TooltipInControlHarness.svelte';

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

/**
 * An icon-only button names itself through its tooltip: the keyboard must reach that name as the pointer does (77
 * SEL-D2, the compact bar in a section head). `openOnFocus` opens the tooltip at once when the focus arrives from the
 * keyboard, and closes it when the focus leaves; without the prop nothing changes for the other callers.
 */
describe('Tooltip — opens on keyboard focus with openOnFocus (77 SEL-D2)', () => {
    const child = createRawSnippet(() => ({render: () => '<button type="button" data-testid="probe-btn">Go</button>'}));

    it('the focus on the child opens it at once; leaving closes it', async () => {
        render(Tooltip, {props: {text: 'Delete', interactiveChild: true, openOnFocus: true, children: child}});
        const button = screen.getByTestId('probe-btn');
        button.focus();
        expect((await screen.findByTestId('tooltip-content')).textContent?.trim()).toBe('Delete');
        button.blur();
        await waitFor(() => expect(screen.queryByTestId('tooltip-content')).toBeNull());
    });

    it('a press that moves no focus (Safari does not focus a clicked button) leaves the next keyboard focus free', async () => {
        render(Tooltip, {props: {text: 'Delete', interactiveChild: true, openOnFocus: true, children: child}});
        const button = screen.getByTestId('probe-btn');
        await fireEvent.pointerDown(button);
        await fireEvent.pointerUp(button);
        button.focus();
        expect((await screen.findByTestId('tooltip-content')).textContent?.trim()).toBe('Delete');
    });

    it('without the prop the focus opens nothing', async () => {
        render(Tooltip, {props: {text: 'Delete', interactiveChild: true, children: child}});
        screen.getByTestId('probe-btn').focus();
        await new Promise((resolve) => setTimeout(resolve, 0));
        expect(screen.queryByTestId('tooltip-content')).toBeNull();
    });
});

/**
 * `showIf` (77 SEL-D2): a tooltip that names an icon is noise once the name is in view beside it. The caller decides at
 * the moment of opening, from the trigger: `false` opens nothing, by any path; absent, nothing changes.
 */
describe('Tooltip — showIf decides at the moment of opening (77 SEL-D2)', () => {
    const child = createRawSnippet(() => ({render: () => '<button type="button" data-testid="probe-btn">Go</button>'}));

    it('false: neither the focus nor Enter opens it; true: they do', async () => {
        let allowed = false;
        const showIf = vi.fn<(trigger: HTMLElement) => boolean>(() => allowed);
        render(Tooltip, {props: {text: 'Delete', interactiveChild: true, openOnFocus: true, showIf, children: child}});
        const button = screen.getByTestId('probe-btn');
        button.focus();
        await new Promise((resolve) => setTimeout(resolve, 0));
        expect(screen.queryByTestId('tooltip-content')).toBeNull();
        expect(showIf).toHaveBeenCalled();
        expect(showIf.mock.calls[0][0]).toBeInstanceOf(HTMLElement);
        button.blur();
        allowed = true;
        button.focus();
        expect(await screen.findByTestId('tooltip-content')).toBeInTheDocument();
    });
});

/**
 * `anchor` (77 SEL-M): the reason of a disabled item of a row menu is placed against the whole menu, never over its
 * items. With an anchor the tooltip measures the anchor's box: beside it (right, then left), else above it, else below;
 * beside it, it stays level with its own trigger. jsdom has no layout: the boxes are given.
 */
describe('Tooltip — an anchor other than the trigger (77 SEL-M)', () => {
    const child = createRawSnippet(() => ({render: () => '<button type="button" data-testid="probe-btn">Sync</button>'}));
    type Box = {left: number; top: number; width: number; height: number};
    const rect = ({left, top, width, height}: Box) => ({left, top, width, height, right: left + width, bottom: top + height, x: left, y: top, toJSON: () => ({})}) as DOMRect;

    function place(trigger: Box, anchorBox: Box): HTMLElement {
        const anchor = document.createElement('div');
        anchor.dataset.testid = 'probe-anchor';
        document.body.appendChild(anchor);
        vi.spyOn(HTMLElement.prototype, 'getBoundingClientRect').mockImplementation(function (this: HTMLElement) {
            if (this.dataset.testid === 'probe-anchor') return rect(anchorBox);
            if (this.dataset.testid === 'probe-wrap') return rect(trigger);
            if (this.dataset.testid === 'tooltip-content') return rect({left: 0, top: 0, width: 150, height: 40});
            return rect({left: 0, top: 0, width: 0, height: 0});
        });
        return anchor;
    }

    afterEach(() => {
        vi.restoreAllMocks();
        document.querySelector('[data-testid="probe-anchor"]')?.remove();
    });

    it('no room on the right of the anchor: on its left, level with the trigger', async () => {
        // A 1024 × 768 page; the menu at 700–1000, its item at 710–990, 200–230
        const anchor = place({left: 710, top: 200, width: 280, height: 30}, {left: 700, top: 100, width: 300, height: 300});
        render(Tooltip, {props: {text: 'Inactive', position: 'right', interactiveChild: true, testId: 'probe-wrap', anchor, children: child}});
        await fireEvent.click(screen.getByTestId('probe-btn'));
        const tip = await screen.findByTestId('tooltip-content');
        // 700 − 8 − 150 = 542 (beside the menu, not beside the item at 552); 215 − 20 = 195
        await waitFor(() => expect(tip.style.left).toBe('542px'));
        expect(tip.style.top).toBe('195px');
    });

    it('no room on either side: above the anchor, never over it', async () => {
        const anchor = place({left: 20, top: 400, width: 980, height: 30}, {left: 10, top: 300, width: 1000, height: 200});
        render(Tooltip, {props: {text: 'Inactive', position: 'right', interactiveChild: true, testId: 'probe-wrap', anchor, children: child}});
        await fireEvent.click(screen.getByTestId('probe-btn'));
        const tip = await screen.findByTestId('tooltip-content');
        // 300 − 8 − 40 = 252, centred on the menu: 510 − 75 = 435
        await waitFor(() => expect(tip.style.top).toBe('252px'));
        expect(tip.style.left).toBe('435px');
    });
});

/**
 * External-target mode (85 BTN-0, the standard button): `trigger` names an element owned by someone else (`pressable`),
 * and `open` decides. No wrapper is rendered and no gesture is read here: a click or a touch elsewhere does not close
 * it, since the owner does that. The pointer over the body is reported to the owner (`onbodypointer`). The wrapper mode
 * is the positive control: the same click outside closes a pinned tooltip there.
 */
describe('Tooltip — external-target mode (85 BTN-0)', () => {
    function externalTrigger(): HTMLElement {
        const trigger = document.createElement('span');
        trigger.dataset.testid = 'probe-external-trigger';
        trigger.textContent = 'trigger';
        document.body.appendChild(trigger);
        return trigger;
    }

    afterEach(() => {
        document.querySelector('[data-testid="probe-external-trigger"]')?.remove();
    });

    it('renders no wrapper, and shows the content exactly while open', async () => {
        const trigger = externalTrigger();
        const view = render(Tooltip, {props: {trigger, open: false, html: '<strong>Edit</strong>'}});
        expect(view.container.querySelector('[role="button"]'), 'no wrapper: the trigger lives elsewhere').toBeNull();
        expect(view.container.children).toHaveLength(0);
        expect(screen.queryByTestId('tooltip-content')).toBeNull();

        await view.rerender({trigger, open: true, html: '<strong>Edit</strong>'});
        const content = await screen.findByTestId('tooltip-content');
        expect(content).toHaveAttribute('role', 'tooltip');
        expect(content.querySelector('strong')).toHaveTextContent('Edit');

        await view.rerender({trigger, open: false, html: '<strong>Edit</strong>'});
        await waitFor(() => expect(screen.queryByTestId('tooltip-content')).toBeNull());
    });

    it('open with a null trigger shows nothing', () => {
        render(Tooltip, {props: {trigger: null, open: true, text: 'Edit'}});
        expect(screen.queryByTestId('tooltip-content')).toBeNull();
    });

    it('a click or a touch elsewhere does not close it: the owner does', async () => {
        const trigger = externalTrigger();
        render(Tooltip, {props: {trigger, open: true, text: 'Edit'}});
        expect(await screen.findByTestId('tooltip-content')).toBeInTheDocument();
        await fireEvent.click(document.body);
        await fireEvent.touchStart(document.body);
        await fireEvent.click(trigger);
        expect(screen.getByTestId('tooltip-content')).toBeInTheDocument();
    });

    it('positive control: in the wrapper mode the same click elsewhere closes a pinned tooltip', async () => {
        render(Tooltip, {props: {text: 'Pinned'}});
        await fireEvent.click(screen.getByRole('button'));
        expect(await screen.findByTestId('tooltip-content')).toBeInTheDocument();
        await fireEvent.click(document.body);
        await waitFor(() => expect(screen.queryByTestId('tooltip-content')).toBeNull());
    });

    it('reports the pointer entering and leaving its body to the owner', async () => {
        const trigger = externalTrigger();
        const onbodypointer = vi.fn();
        render(Tooltip, {props: {trigger, open: true, text: 'Edit', onbodypointer}});
        const content = await screen.findByTestId('tooltip-content');
        await fireEvent.mouseEnter(content);
        await fireEvent.mouseLeave(content);
        expect(onbodypointer.mock.calls).toEqual([[true], [false]]);
    });
});

/**
 * `insideControl` (85 BTN-0c, D16): a tooltip that names a part of a larger control (a provider badge inside a route
 * row, a ⚠ inside an option) is only a hover. Its wrapper takes no click (it neither pins nor stops the click, so the
 * control acts), has no role and no tab stop (the control is the one stop), and opens on a mouse rest, closing on leave.
 * The control case: the same harness without the prop swallows the click — the defect D16 found in the route picker.
 */
describe('Tooltip — insideControl: a part of a larger control (85 BTN-0c, D16)', () => {
    afterEach(() => {
        vi.useRealTimers();
    });

    function harness(insideControl: boolean) {
        const onpress = vi.fn();
        render(TooltipInControlHarness, {props: {onpress, insideControl}});
        return {onpress, control: screen.getByTestId('probe-control'), part: screen.getByTestId('probe-part'), badge: screen.getByTestId('probe-badge')};
    }

    it('a click on the part reaches the control, once, and does not pin the tooltip', async () => {
        const {onpress, badge} = harness(true);
        await fireEvent.click(badge);
        expect(onpress).toHaveBeenCalledTimes(1);
        expect(screen.queryByTestId('tooltip-content'), 'a click opens nothing: it is the control’s').toBeNull();
    });

    it('control: the old wrapper (no insideControl) swallows the click, and the control never acts', async () => {
        const {onpress, badge} = harness(false);
        await fireEvent.click(badge);
        expect(onpress, 'the defect D16: the wrapper stopped the click').not.toHaveBeenCalled();
        expect(screen.getByTestId('tooltip-content'), 'and pinned its own tooltip instead').toBeInTheDocument();
    });

    it('the part is no tab stop: no role, no tabindex, nothing focusable between the control and the next element', () => {
        const {part, control} = harness(true);
        expect(part.hasAttribute('role')).toBe(false);
        expect(part.hasAttribute('tabindex')).toBe(false);
        expect(part.tagName).toBe('SPAN');
        const focusable = [...document.body.querySelectorAll<HTMLElement>('button, a[href], input, select, textarea, [tabindex]')].filter((el) => el.tabIndex >= 0);
        expect(focusable.map((el) => el.dataset.testid)).toEqual(['probe-control', 'probe-next']);
        expect(control.contains(part)).toBe(true);
    });

    it('control: the old wrapper is an extra tab stop inside the control', () => {
        const {part} = harness(false);
        expect(part).toHaveAttribute('role', 'button');
        expect(part).toHaveAttribute('tabindex', '0');
    });

    it('a mouse rest opens it after the delay, and leaving closes it', async () => {
        vi.useFakeTimers();
        const {part} = harness(true);
        await fireEvent.mouseEnter(part);
        await vi.advanceTimersByTimeAsync(499);
        expect(screen.queryByTestId('tooltip-content'), 'not before the delay').toBeNull();
        await vi.advanceTimersByTimeAsync(1);
        expect(screen.getByTestId('tooltip-content')).toHaveTextContent('European Central Bank');
        await fireEvent.mouseLeave(part);
        await vi.advanceTimersByTimeAsync(1_000);
        expect(screen.queryByTestId('tooltip-content')).toBeNull();
    });

    it('a click while it shows does not pin it: leaving still closes it', async () => {
        vi.useFakeTimers();
        const {part, badge, onpress} = harness(true);
        await fireEvent.mouseEnter(part);
        await vi.advanceTimersByTimeAsync(500);
        expect(screen.getByTestId('tooltip-content')).toBeInTheDocument();
        await fireEvent.click(badge);
        expect(onpress).toHaveBeenCalledTimes(1);
        await fireEvent.mouseLeave(part);
        await vi.advanceTimersByTimeAsync(1_000);
        expect(screen.queryByTestId('tooltip-content'), 'a pinned tooltip would wait thirty seconds').toBeNull();
    });
});
