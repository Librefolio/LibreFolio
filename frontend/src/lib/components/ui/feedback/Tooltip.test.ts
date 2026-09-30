// @vitest-environment jsdom
/**
 * Tooltip — a hostile `html` prop is sanitised before `{@html}` (workstream K, step 13, item 0).
 *
 * `Tooltip` renders its `html` prop — or `text`, escaped — as raw HTML, and callers hand it markup
 * assembled from names, notes and validation messages. The prop must come out without anything that
 * runs, and with the harmless markup the app itself uses (icons, emoji flags) intact.
 *
 * Registered in `front_component_unit` (`scripts/test_runner/_frontend_utility.py`, action
 * `component-unit`).
 */
import {afterEach, describe, expect, it} from 'vitest';
import {cleanup, fireEvent, render, screen} from '$test/component';
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
