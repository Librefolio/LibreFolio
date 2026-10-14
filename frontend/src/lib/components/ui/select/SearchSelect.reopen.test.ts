// @vitest-environment jsdom
/**
 * SearchSelect — reopening right after a close (Vitest + jsdom).
 *
 * `openDropdown()` refuses to open for 200 ms after the last close. The guard exists for one
 * gesture: on a touch screen the tap that chooses an option is followed by the click the browser
 * synthesises for it — the ghost click — and if that click lands on the trigger once the list has
 * gone, opening on it throws the user straight back into the list they just left (f9e79d580).
 * But every close arms the guard: a mouse choice, an Enter, an Escape. So a mouse or keyboard
 * user — or a program — who reopens within 200 ms is ignored in silence: the click lands, nothing
 * opens, and nothing on screen says why. `e2e/transactions/tx-import-asset-inspector.spec.ts`
 * tripped on exactly that (E2-001), reopening the currency select about 190 ms after choosing USD;
 * the measurements are in the Danske Bank step-4 plan, §16.
 *
 * The contract pinned here — the developer's decision, §16.4:
 *   1. mouse: after a mouse choice, a mouse click on the trigger at the same instant opens the list;
 *   2. keyboard: after an Enter choice, ArrowDown on the trigger at the same instant opens it;
 *   3. touch and pen: after a tap choice, a click on the trigger within 200 ms — the ghost click —
 *      is ignored, and a new tap after the window opens the list. That is the guard doing its job,
 *      and the mobile fix it was written for must survive the correction of the other cases;
 *   4. a close with no pointerdown behind it (a synthetic click) is not a touch close: a click at
 *      the same instant opens the list.
 * Mixed sequences, such as a touch close followed by a mouse click within the window, are
 * deliberately left unspecified and are not tested.
 *
 * Time is the subject, so this file owns it: every test runs on fake timers frozen at T0, and only
 * the test moves the clock. "The same instant" is therefore literal — 0 ms between the close and
 * the reopen — and asserted rather than assumed. The touch cases double as the positive control of
 * that clock: refusing the ghost clicks at +0 and +150 ms and accepting the tap at +250 ms is only
 * possible if the component reads the clock the test moves.
 *
 * Every pointer press proves its premise before it clicks: a listener on the pressed element reads
 * `pointerType` back. A harness that dropped the field would make a tap and a mouse click the same
 * gesture, and the tests would then agree with any implementation.
 *
 * Assertions read `aria-expanded` on the trigger, the listbox inside this instance's own container
 * and the `onchange` payload — never a Tailwind class or a translated string. Both layouts run: the
 * search box in the dropdown, and the inline search in the trigger used by CurrencySearchSelect,
 * the select E2-001 reopens.
 */
import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';
import {fireEvent, render, screen, setupI18n, within} from '$test/component';
import type {SelectOption} from './types';
import SearchSelect from './SearchSelect.svelte';

type Device = 'mouse' | 'touch' | 'pen';

/** A plain list: the subject is when the list opens, not what is in it. */
const OPTS: SelectOption[] = [
    {value: 'EUR', label: 'Euro'},
    {value: 'USD', label: 'US Dollar'},
    {value: 'JPY', label: 'Japanese Yen'},
];

/** The frozen instant every test starts at — and, since nothing moves the clock before it, the instant of the choice. */
const T0 = Date.UTC(2026, 9, 6, 8, 0, 0);

/** Both trigger layouts, as [label, inlineSearch]. */
const LAYOUTS: [string, boolean][] = [
    ['search box in the dropdown', false],
    ['inline search in the trigger', true],
];

/** The devices whose tap the browser follows with a ghost click. */
const TAP_DEVICES: Device[] = ['touch', 'pen'];

function mount(inlineSearch: boolean) {
    const onchange = vi.fn();
    render(SearchSelect, {value: 'EUR', options: OPTS, testId: 'ccy', inlineSearch, onchange});
    return {onchange, root: screen.getByTestId('ccy'), trigger: screen.getByTestId('ccy-trigger')};
}

/**
 * This instance's listbox, looked up inside its own container. The option testid
 * `search-select-option-{value}` is shared by every SearchSelect on a page, so the container is
 * the barrier that keeps a lookup from fishing in a neighbour's list.
 */
function listbox(root: HTMLElement): HTMLElement | null {
    return within(root).queryByRole('listbox');
}

/** An option of this instance's open list. */
function option(root: HTMLElement, value: string): HTMLElement {
    return within(within(root).getByRole('listbox')).getByTestId(`search-select-option-${value}`);
}

/** Open means usable: the trigger says so, and this instance's list is there with every option in it. */
function expectOpen(root: HTMLElement, trigger: HTMLElement, why: string) {
    expect(trigger, why).toHaveAttribute('aria-expanded', 'true');
    const list = within(root).getByRole('listbox');
    for (const {value} of OPTS) {
        expect(within(list).queryByTestId(`search-select-option-${value}`), why).not.toBeNull();
    }
}

/** Closed means gone: the trigger says so, and this instance has no list at all. */
function expectClosed(root: HTMLElement, trigger: HTMLElement, why: string) {
    expect(trigger, why).toHaveAttribute('aria-expanded', 'false');
    expect(listbox(root), why).toBeNull();
}

/**
 * One press of a pointing device: the `pointerdown` that names the device, then the `click` it ends
 * in. Before the click, the press checks what a listener on the target actually read, and fails
 * right there if it is not the device asked for.
 */
async function press(target: HTMLElement, device: Device) {
    const read: string[] = [];
    const listener = (event: Event) => read.push((event as PointerEvent).pointerType);
    target.addEventListener('pointerdown', listener);
    try {
        await fireEvent.pointerDown(target, {pointerType: device});
    } finally {
        target.removeEventListener('pointerdown', listener);
    }
    expect(read, `premise: the pointerdown reached its target as a ${device}`).toEqual([device]);
    await fireEvent.click(target);
}

describe('SearchSelect reopen after close', () => {
    beforeEach(async () => {
        // On the real clock: the dictionaries load through dynamic imports.
        await setupI18n();
        vi.useFakeTimers();
        vi.setSystemTime(T0);
    });

    afterEach(() => {
        // What is still pending (the 10 ms focus of the search box, the 20 ms focus hand-off of an
        // Enter choice) is dropped with the fake clock, never fired at an unmounted component.
        vi.useRealTimers();
    });

    describe.each(LAYOUTS)('%s', (_layout, inlineSearch) => {
        it('mouse: a mouse click on the trigger at the very instant of a mouse choice opens the list again', async () => {
            const {onchange, root, trigger} = mount(inlineSearch);
            await press(trigger, 'mouse');
            expectOpen(root, trigger, 'premise: a mouse click on the trigger opens the list');

            await press(option(root, 'USD'), 'mouse');
            expect(onchange).toHaveBeenCalledExactlyOnceWith('USD');
            expectClosed(root, trigger, 'premise: a mouse choice closes the list');
            expect(Date.now(), 'premise: the clock has not moved since the choice').toBe(T0);

            await press(trigger, 'mouse');

            expectOpen(root, trigger, 'a mouse click on the trigger 0 ms after a mouse choice must open the list');
        });

        it('keyboard: ArrowDown on the trigger at the very instant of an Enter choice opens the list again', async () => {
            const {onchange, root, trigger} = mount(inlineSearch);
            await fireEvent.keyDown(trigger, {key: 'ArrowDown'});
            expectOpen(root, trigger, 'premise: ArrowDown on the trigger opens the list');

            // The highlight opens on EUR; ArrowDown moves it to USD, and Enter chooses it.
            const search = within(root).getByTestId('ccy-search');
            await fireEvent.keyDown(search, {key: 'ArrowDown'});
            await fireEvent.keyDown(search, {key: 'Enter'});
            expect(onchange).toHaveBeenCalledExactlyOnceWith('USD');
            expectClosed(root, trigger, 'premise: an Enter choice closes the list');
            expect(Date.now(), 'premise: the clock has not moved since the choice').toBe(T0);

            // ArrowDown, not Enter: a separate guard, unchanged and not under test here, ignores Enter
            // for 200 ms after the trigger takes focus, and the close has just focused it. The key goes
            // to the trigger directly, because an Enter choice hands focus onward on a 20 ms timer.
            await fireEvent.keyDown(trigger, {key: 'ArrowDown'});

            expectOpen(root, trigger, 'ArrowDown on the trigger 0 ms after an Enter choice must open the list');
        });

        it.each(TAP_DEVICES)('%s: the ghost click within 200 ms of a tap choice is ignored, and a new tap after the window opens the list', async (device) => {
            const {onchange, root, trigger} = mount(inlineSearch);
            await press(trigger, device);
            expectOpen(root, trigger, `premise: a ${device} tap on the trigger opens the list`);

            await press(option(root, 'USD'), device);
            expect(onchange).toHaveBeenCalledExactlyOnceWith('USD');
            expectClosed(root, trigger, `premise: a ${device} choice closes the list`);
            expect(Date.now(), 'premise: the clock has not moved since the choice').toBe(T0);

            // The ghost click: the click the browser synthesises for the tap, hitting the trigger once
            // the list has gone. It brings no pointerdown of its own — that one went to the option.
            await fireEvent.click(trigger);
            expectClosed(root, trigger, `the ghost click 0 ms after a ${device} choice must be ignored`);

            await vi.advanceTimersByTimeAsync(150);
            expect(Date.now() - T0, 'premise: the clock reads 150 ms after the choice').toBe(150);
            await fireEvent.click(trigger);
            expectClosed(root, trigger, `the ghost click 150 ms after a ${device} choice must be ignored`);

            await vi.advanceTimersByTimeAsync(100);
            expect(Date.now() - T0, 'premise: the clock reads 250 ms after the choice').toBe(250);
            await press(trigger, device);
            expectOpen(root, trigger, `a new ${device} tap 250 ms after the choice, past the window, must open the list`);
        });

        it('no pointer: a close with no pointerdown behind it is not a touch close, so a click at the very instant opens the list again', async () => {
            const pointerdowns = vi.fn();
            document.addEventListener('pointerdown', pointerdowns, true);
            try {
                const {onchange, root, trigger} = mount(inlineSearch);
                await fireEvent.click(trigger);
                expectOpen(root, trigger, 'premise: a click on the trigger opens the list');

                await fireEvent.click(option(root, 'USD'));
                expect(onchange).toHaveBeenCalledExactlyOnceWith('USD');
                expectClosed(root, trigger, 'premise: a click on an option closes the list');
                expect(pointerdowns, 'premise: no pointerdown led to the close').not.toHaveBeenCalled();
                expect(Date.now(), 'premise: the clock has not moved since the choice').toBe(T0);

                await fireEvent.click(trigger);

                expectOpen(root, trigger, 'a click on the trigger 0 ms after a close with no pointerdown behind it must open the list');
            } finally {
                document.removeEventListener('pointerdown', pointerdowns, true);
            }
        });
    });
});
