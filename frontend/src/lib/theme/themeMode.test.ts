// @vitest-environment jsdom
/**
 * themeMode.test.ts — the two helpers the charts read the page theme with (colour workstream R, W8 — the developer's
 * decision D4).
 *
 * `isDarkTheme()` and `onThemeClassChange()` replaced what 18 components wrote inline — the charts under
 * `src/lib/components/{charts,dashboard,risk,brokers/lots}`, the spreadsheet preview of `files/FilePreviewModal.svelte`
 * and the result views of the PAC allocator: `document.documentElement.classList.contains('dark')`, and a
 * `MutationObserver` on `{attributes: true, attributeFilter: ['class']}` of `<html>`. Every copy behaved the same way and
 * the charts were tuned against that behaviour, so this file pins it, one property per test:
 *
 * - `isDarkTheme()` answers the class token `dark` of `<html>`, as it is at the moment of the call, and nothing else:
 *   not `dark` on `<body>`, not a class that merely contains the word;
 * - `onThemeClassChange(onChange)` calls `onChange` after every change of the class of `<html>` — `foo` as much as
 *   `dark`, whatever the way it is written. D4 keeps it so on purpose: the Designer Lab relies on the charts redrawing on
 *   every one of them;
 * - and after nothing else: not another attribute of `<html>` (the root layout writes `lang` and `data-i18n-ready`
 *   there), not a class change of `<body>` or of any element below it;
 * - with no arguments, so that a callback with an optional parameter can be passed by reference: handed the mutation
 *   records, `GrowthChart`'s `renderChart(forceFullXAxisRebuild = false)` would rebuild its axis on every theme change;
 * - once per batch: the writes one task makes — `applyTheme()` makes two, `remove('light', 'dark')` then
 *   `add(resolved)` — are one call, so one theme change is one redraw per chart;
 * - it returns the observer, already observing: a change made the instant it returns is on its record queue. Once that
 *   observer is disconnected no call follows, not even for a change made just before: that is how a destroyed chart
 *   stops redrawing.
 *
 * Delivery is awaited, never slept on. jsdom, like a browser, queues one microtask at the first mutation and hands every
 * observer its records in that one pass; `flush()` resumes the test behind it. Each negative is paired with a control
 * observer that is handed the very changes the helper must ignore, so "not called" can only mean "delivered, and
 * filtered out" — never "not delivered yet". And each one ends on a positive: the same observer, still alive, called
 * by the next change of the class of `<html>`.
 *
 * **The chart colours' signal (contract C4 with the Designer Lab, DV).** The Lab changes chart colours without a theme
 * switch — at every edit, and when it loads a state — and says so with `notifyChartColorsChange()`; a chart listens with
 * `onChartColorsChange(onChange)` and rebuilds its whole option. Pinned: the signal is the document event
 * `lf:chart-colors-change`, delivered synchronously, once per notification, to every listener, with no arguments; a
 * disconnected listener hears no more while the others do; a theme switch is not this signal. Every negative has a
 * control listener on the same event, so "not called" means "dispatched, and not delivered to it".
 *
 * Every test restores the attributes of `<html>` and `<body>`, removes what it added to the page, and disconnects every
 * observer and listener it created.
 *
 * Registered in `front_utility_unit` (`scripts/test_runner/_frontend_utility.py`, action `core-unit`).
 *
 * @module lib/theme/themeMode.test
 */
import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';

import {isDarkTheme, notifyChartColorsChange, onChartColorsChange, onThemeClassChange} from './themeMode';

const html = document.documentElement;
const body = document.body;

/**
 * Resumes the test behind the pending delivery. The first mutation queued it as one microtask, before this one: by the
 * time the awaiting test runs again, every observer has been called. No clock is involved.
 */
const flush = (): Promise<void> => Promise.resolve();

type Attributes = Array<[string, string]>;

const attributesOf = (element: Element): Attributes => element.getAttributeNames().map((name) => [name, element.getAttribute(name) ?? '']);

/** Puts back exactly the attributes an element had: every test writes the class or another attribute of `<html>`, some those of `<body>`. */
function restore(element: Element, attributes: Attributes): void {
    for (const name of element.getAttributeNames()) element.removeAttribute(name);
    for (const [name, value] of attributes) element.setAttribute(name, value);
}

let htmlBefore: Attributes;
let bodyBefore: Attributes;
/** Every observer a test creates — the helper's and the controls' — disconnected after it. */
let observers: MutationObserver[];
/** Every element a test adds to the page, removed after it. */
let added: Element[];
/** Every chart-colours listener a test creates — the helper's handles and the controls' removals — disconnected after it. */
let listeners: Array<{disconnect: () => void}>;

beforeEach(() => {
    htmlBefore = attributesOf(html);
    bodyBefore = attributesOf(body);
    observers = [];
    added = [];
    listeners = [];
});

afterEach(() => {
    // Disconnect first: the restore below is itself a change of the class of <html>.
    for (const observer of observers) observer.disconnect();
    for (const listener of listeners) listener.disconnect();
    for (const element of added) element.remove();
    restore(html, htmlBefore);
    restore(body, bodyBefore);
});

/** The helper's observer, kept for the cleanup. */
function watchTheme(onChange: () => void): MutationObserver {
    const observer = onThemeClassChange(onChange);
    observers.push(observer);
    return observer;
}

/** A `<div>` in `<body>`: an element below `<html>`, which `subtree: true` would reach. */
function elementBelow(): HTMLElement {
    const element = body.appendChild(document.createElement('div'));
    added.push(element);
    return element;
}

/** A change as a record shows it: `<element> <attribute>`. */
const describeRecord = (record: MutationRecord): string => `${(record.target as Element).localName} ${record.attributeName}`;

/**
 * A control: an observer of every attribute of every element of the page. It returns the deliveries it is handed, each
 * one the list of changes it carried. It is called in the same pass as the helper's observer, so once it has been handed
 * a change, the helper has been offered the same one.
 */
function control(): string[][] {
    const deliveries: string[][] = [];
    const observer = new MutationObserver((records) => {
        deliveries.push(records.map(describeRecord));
    });
    observer.observe(html, {attributes: true, subtree: true});
    observers.push(observer);
    return deliveries;
}

describe('isDarkTheme() — the dark class of <html>', () => {
    it('follows the dark class of <html>: added, then removed', () => {
        html.className = 'light';
        expect(isDarkTheme(), 'light').toBe(false);
        html.classList.add('dark');
        expect(isDarkTheme(), 'dark added').toBe(true);
        html.classList.remove('dark');
        expect(isDarkTheme(), 'dark removed').toBe(false);
    });

    it('answers the token dark of <html> and nothing else: not dark on <body> or below it, not a class that merely contains the word', () => {
        body.classList.add('dark');
        elementBelow().classList.add('dark');
        html.className = 'darker dark-mode not-dark';
        expect(isDarkTheme()).toBe(false);

        // The control: the same page, with the token itself on <html>.
        html.classList.add('dark');
        expect(isDarkTheme()).toBe(true);
    });
});

describe('onThemeClassChange() — one call after every change of the class of <html>', () => {
    /** What changes, the class `<html>` has before the observer exists, and the change itself. */
    const CLASS_CHANGES: Array<[string, string, () => void]> = [
        ['dark added', 'light', () => html.classList.add('dark')],
        ['dark removed', 'dark', () => html.classList.remove('dark')],
        ['dark toggled', 'light', () => html.classList.toggle('dark')],
        ['foo added, a class other than dark (D4)', 'dark', () => html.classList.add('foo')],
        ['foo removed', 'dark foo', () => html.classList.remove('foo')],
        ['the whole className assigned', 'light', () => (html.className = 'foo bar')],
        ['class written with setAttribute', 'light', () => html.setAttribute('class', 'dark')],
        ['the class attribute removed', 'dark', () => html.removeAttribute('class')],
    ];

    it.each(CLASS_CHANGES)('calls back after any change of the class of <html>: %s', async (_what, initial, change) => {
        html.className = initial;
        const onChange = vi.fn();
        watchTheme(onChange);
        change();
        await flush();
        expect(onChange).toHaveBeenCalledTimes(1);
    });

    /** What changes, the change, and the record the control sees of it. */
    const NOT_THE_CLASS_OF_HTML: Array<[string, (below: HTMLElement) => void, string]> = [
        ['a data-* attribute of <html>', () => html.setAttribute('data-x', '1'), 'html data-x'],
        ['the style of <html>', () => html.style.setProperty('color', 'red'), 'html style'],
        ['the lang of <html>, which the root layout writes', () => html.setAttribute('lang', 'it'), 'html lang'],
        ['the class of <body>', () => body.classList.add('dark'), 'body class'],
        ['the class of an element below <body>', (below) => below.classList.add('dark'), 'div class'],
    ];

    it.each(NOT_THE_CLASS_OF_HTML)('does not call back for %s', async (_what, change, record) => {
        const below = elementBelow();
        const onChange = vi.fn();
        watchTheme(onChange);
        const deliveries = control();

        change(below);
        await flush();
        expect(deliveries, 'the control was handed the change: the delivery the helper is judged on did happen').toEqual([[record]]);
        expect(onChange).not.toHaveBeenCalled();

        // The same observer is alive: the next change of the class of <html> reaches it.
        html.classList.add('foo');
        await flush();
        expect(onChange).toHaveBeenCalledTimes(1);
    });

    it('calls back with no arguments — a callback with an optional parameter can be passed by reference', async () => {
        const onChange = vi.fn();
        watchTheme(onChange);
        html.classList.add('dark');
        await flush();
        expect(onChange.mock.calls, 'one call, carrying nothing').toEqual([[]]);
    });

    it("delivers the changes of one task as one call: applyTheme()'s two writes, and one more, are one redraw", async () => {
        html.className = 'light';
        const onChange = vi.fn();
        watchTheme(onChange);
        const deliveries = control();

        // applyTheme('dark') in src/lib/stores/app/themeStore.ts, then one more class in the same task.
        html.classList.remove('light', 'dark');
        html.classList.add('dark');
        html.classList.add('foo');
        expect(onChange, 'never synchronously, inside the write').not.toHaveBeenCalled();

        await flush();
        expect(deliveries, 'three changes, handed over together').toEqual([['html class', 'html class', 'html class']]);
        expect(onChange).toHaveBeenCalledTimes(1);
    });

    it('returns the observer, already observing: a change made the instant it returns is on its record queue', () => {
        const observer = watchTheme(vi.fn());
        expect(observer).toBeInstanceOf(MutationObserver);

        // Synchronously, before any microtask could run: the record is already queued on the observer it returned.
        html.classList.add('dark');
        expect(observer.takeRecords().map(describeRecord)).toEqual(['html class']);
    });

    it('calls back no more once the observer it returned is disconnected — not even for a change made just before', async () => {
        const onChange = vi.fn();
        const observer = watchTheme(onChange);
        html.classList.add('dark');
        await flush();
        expect(onChange, 'connected, it calls back').toHaveBeenCalledTimes(1);

        const deliveries = control();
        html.classList.remove('dark');
        observer.disconnect();
        html.classList.add('foo');
        await flush();
        expect(deliveries, 'the control was handed both changes, the one made before disconnect() and the one after').toEqual([['html class', 'html class']]);
        expect(onChange, 'disconnected, it does not: the count is still the one from before').toHaveBeenCalledTimes(1);
    });
});

// =============================================================================
// C4 — the chart colours changed without a theme switch (the Designer Lab's signal)
// =============================================================================

/** The event of contract C4: what the Lab, or anyone, dispatches on `document` when chart colours change. */
const CHART_COLORS_EVENT = 'lf:chart-colors-change';

/** The helper's listener, kept for the cleanup. */
function watchChartColors(onChange: () => void): {disconnect: () => void} {
    const handle = onChartColorsChange(onChange);
    listeners.push(handle);
    return handle;
}

/** A control: a plain listener of the event on `document`, counting what is dispatched there. */
function chartColorsControl(): {count: () => number} {
    let count = 0;
    const listener = () => {
        count += 1;
    };
    document.addEventListener(CHART_COLORS_EVENT, listener);
    listeners.push({disconnect: () => document.removeEventListener(CHART_COLORS_EVENT, listener)});
    return {count: () => count};
}

describe('onChartColorsChange() and notifyChartColorsChange() — contract C4 with the Designer Lab', () => {
    it('calls back once per notification, synchronously, with no arguments', () => {
        const onChange = vi.fn();
        watchChartColors(onChange);

        notifyChartColorsChange();
        expect(onChange.mock.calls, 'one call, during the notification itself, carrying nothing — not the event').toEqual([[]]);
        notifyChartColorsChange();
        expect(onChange).toHaveBeenCalledTimes(2);
    });

    it(`is the document event ${CHART_COLORS_EVENT}: the notification reaches a plain listener of it, and the event, dispatched by anyone, reaches the helper`, () => {
        const onChange = vi.fn();
        watchChartColors(onChange);
        const control = chartColorsControl();

        notifyChartColorsChange();
        expect(control.count(), 'the notification is that event, on document').toBe(1);

        document.dispatchEvent(new Event(CHART_COLORS_EVENT));
        expect(onChange, 'the event itself, dispatched without the helper').toHaveBeenCalledTimes(2);
    });

    it('calls a disconnected listener no more, while the signal still goes out', () => {
        const onChange = vi.fn();
        const handle = watchChartColors(onChange);
        notifyChartColorsChange();
        expect(onChange, 'connected, it is called').toHaveBeenCalledTimes(1);

        const control = chartColorsControl();
        handle.disconnect();
        notifyChartColorsChange();
        expect(control.count(), 'the notification after disconnect() was dispatched').toBe(1);
        expect(onChange, 'disconnected, it is not called: the count is still the one from before').toHaveBeenCalledTimes(1);
    });

    it('calls every listener, and disconnecting one leaves the other listening', () => {
        const [first, second] = [vi.fn(), vi.fn()];
        const firstHandle = watchChartColors(first);
        watchChartColors(second);

        notifyChartColorsChange();
        expect([first.mock.calls.length, second.mock.calls.length], 'both are called').toEqual([1, 1]);

        firstHandle.disconnect();
        notifyChartColorsChange();
        expect([first.mock.calls.length, second.mock.calls.length], 'only the one still connected').toEqual([1, 2]);
    });

    it('does not answer a theme switch, nor another event: the theme has its own signal', async () => {
        const onChange = vi.fn();
        watchChartColors(onChange);
        const themeChanges = vi.fn();
        watchTheme(themeChanges);

        html.classList.toggle('dark');
        document.dispatchEvent(new Event('lf:something-else'));
        await flush();
        expect(themeChanges, 'barrier: the theme switch happened, and was delivered').toHaveBeenCalledTimes(1);
        expect(onChange).not.toHaveBeenCalled();

        notifyChartColorsChange();
        expect(onChange, 'the same listener, alive: the next notification reaches it').toHaveBeenCalledTimes(1);
    });
});
