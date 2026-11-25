// @vitest-environment jsdom
/**
 * Button — the standard button (project 85, BTN-0): the recipe and the behaviour (`pressable`) together.
 *
 * The behaviour table is the header of `pressable.svelte.ts`; this file drives it with synthetic pointer sequences.
 * jsdom has no `PointerEvent`, so a pointer event is a `MouseEvent` of the pointer type's name with `pointerType`
 * defined on it — `pressable` reads nothing else. The clock is faked: the long press (500 ms), the mouse rest (500 ms)
 * and the click window after a long press (400 ms) are stepped exactly, never slept.
 *
 * - Touch: a tap acts on the click and shows nothing; a long press shows the name, marks the press (`lf-pressing`)
 *   while it lasts, and drops the click that follows inside the window; a move over 10 px is a scroll; a
 *   `pointercancel` ends the press like a release.
 * - Mouse: a rest shows the name when the word is not in view (or a help); a click hides it and keeps it quiet until
 *   the pointer leaves and comes back; a right click goes up as always.
 * - Keyboard: a focus brought by Tab shows the name, a programmatic one does not; Esc closes it.
 * - Off: with a `reason` (or an icon `disabled`, or `busy`) the button stays reachable (`aria-disabled`, never the
 *   native attribute) and drops the click — a `submit` included; a text button `disabled` is natively disabled.
 * - ARIA: `aria-pressed`, `aria-haspopup`/`aria-expanded`, `aria-busy`, `aria-label` only when the word is not the label.
 *
 * Every text asserted here is a prop the test passed: no catalogue string is read.
 */
import {afterEach, beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';
import {createRawSnippet, flushSync} from 'svelte';
import {Pencil, Trash2} from 'lucide-svelte';
import {cleanup, fireEvent, render, screen, setupI18n, within} from '$test/component';
import Button from './Button.svelte';
import LegacyButtonHost from './__tests__/LegacyButtonHost.svelte';
import ButtonGroupHarness from './__tests__/ButtonGroupHarness.svelte';
import CloseButton from './CloseButton.svelte';
import {buttonClasses} from './buttonClasses';
import {HOVER_DELAY_MS, LONG_PRESS_CLICK_WINDOW_MS, LONG_PRESS_MS, MOVE_TOLERANCE_PX} from './pressable.svelte';

beforeAll(async () => {
    await setupI18n();
});

beforeEach(() => {
    vi.useFakeTimers();
});

afterEach(async () => {
    // The Tab flag of pressable is module state reset by a 0 ms timer: run what is pending on this clock before it goes.
    vi.runOnlyPendingTimers();
    cleanup();
    vi.useRealTimers();
});

type Pointer = 'touch' | 'mouse' | 'pen';

/** A pointer event as pressable reads it: a MouseEvent of that name, with `pointerType`. */
function pointer(element: Element, type: string, pointerType: Pointer, x = 10, y = 10): MouseEvent {
    const bubbles = type !== 'pointerenter' && type !== 'pointerleave';
    const event = new MouseEvent(type, {bubbles, cancelable: true, clientX: x, clientY: y});
    Object.defineProperty(event, 'pointerType', {value: pointerType});
    element.dispatchEvent(event);
    flushSync();
    return event;
}

/** The browser's click that follows a release (or a mouse button). `false` when a listener cancelled it. */
function click(element: Element): boolean {
    const event = new MouseEvent('click', {bubbles: true, cancelable: true, clientX: 10, clientY: 10});
    const notCancelled = element.dispatchEvent(event);
    flushSync();
    return notCancelled;
}

async function advance(ms: number) {
    await vi.advanceTimersByTimeAsync(ms);
    flushSync();
}

const tooltips = () => document.querySelectorAll('[role="tooltip"]');
const tooltip = () => document.querySelector<HTMLElement>('[role="tooltip"]');

/** Every caller passes `label` (mandatory): `props` stays open so each case names only what it is about. */
function renderButton(props: {label: string} & Record<string, unknown>) {
    const onclick = vi.fn();
    const view = render(Button, {props: {onclick, 'data-testid': 'probe-btn', ...props}});
    return {onclick, button: screen.getByTestId('probe-btn'), ...view};
}

const iconButton = (props: Record<string, unknown> = {}) => renderButton({label: 'Edit row', icon: Pencil, display: 'icon', ...props});

describe('Button — a plain click', () => {
    it('acts once on a click with no pointer sequence (a test, a screen reader, element.click())', async () => {
        const {onclick, button} = iconButton();
        await fireEvent.click(button);
        expect(onclick).toHaveBeenCalledTimes(1);
        expect(tooltip()).toBeNull();
    });
});

describe('Button — touch', () => {
    it('a tap (released before 500 ms) acts on the click and shows no name', async () => {
        const {onclick, button} = iconButton();
        pointer(button, 'pointerdown', 'touch');
        await advance(LONG_PRESS_MS - 200);
        pointer(button, 'pointerup', 'touch');
        expect(click(button)).toBe(true);
        expect(onclick).toHaveBeenCalledTimes(1);
        await advance(LONG_PRESS_MS + 100);
        expect(tooltip(), 'a tap never opens the name, even later').toBeNull();
    });

    it('a long press shows the name, marks the press while it lasts, and drops the click that follows', async () => {
        const {onclick, button} = iconButton();
        pointer(button, 'pointerdown', 'touch');
        expect(button.classList.contains('lf-pressing'), 'the press is marked while the finger rests').toBe(true);
        await advance(LONG_PRESS_MS - 1);
        expect(tooltip(), 'not before 500 ms').toBeNull();
        await advance(1);
        expect(tooltip()).not.toBeNull();
        expect(tooltip()?.textContent?.trim()).toBe('Edit row');
        expect(tooltip()?.querySelector('strong')?.textContent).toBe('Edit row');
        expect(button.classList.contains('lf-pressing'), 'the mark ends with the long press').toBe(false);

        pointer(button, 'pointerup', 'touch');
        await advance(LONG_PRESS_CLICK_WINDOW_MS - 100);
        expect(click(button), 'the click of the release is cancelled').toBe(false);
        expect(onclick).not.toHaveBeenCalled();
        expect(tooltip(), 'the name stays after the release').not.toBeNull();
    });

    it('a click after the window acts', async () => {
        const {onclick, button} = iconButton();
        pointer(button, 'pointerdown', 'touch');
        await advance(LONG_PRESS_MS);
        expect(tooltip()).not.toBeNull();
        pointer(button, 'pointerup', 'touch');
        await advance(LONG_PRESS_CLICK_WINDOW_MS + 1);
        expect(click(button)).toBe(true);
        expect(onclick).toHaveBeenCalledTimes(1);
    });

    it(`a finger that moves more than ${MOVE_TOLERANCE_PX} px is a scroll: no name, and a later click acts`, async () => {
        const {onclick, button} = iconButton();
        pointer(button, 'pointerdown', 'touch', 10, 10);
        pointer(button, 'pointermove', 'touch', 10 + MOVE_TOLERANCE_PX + 5, 10);
        expect(button.classList.contains('lf-pressing')).toBe(false);
        await advance(LONG_PRESS_MS + 100);
        expect(tooltip()).toBeNull();
        pointer(button, 'pointerup', 'touch', 10 + MOVE_TOLERANCE_PX + 5, 10);
        expect(click(button)).toBe(true);
        expect(onclick).toHaveBeenCalledTimes(1);
    });

    it('a move within the tolerance keeps the long press', async () => {
        const {button} = iconButton();
        pointer(button, 'pointerdown', 'touch', 10, 10);
        pointer(button, 'pointermove', 'touch', 10 + MOVE_TOLERANCE_PX - 2, 10);
        await advance(LONG_PRESS_MS);
        expect(tooltip()).not.toBeNull();
    });

    it('a pointercancel after the long press fired keeps the window: a late click is still dropped', async () => {
        const {onclick, button} = iconButton();
        pointer(button, 'pointerdown', 'touch');
        await advance(LONG_PRESS_MS);
        expect(tooltip()).not.toBeNull();
        pointer(button, 'pointercancel', 'touch');
        await advance(LONG_PRESS_CLICK_WINDOW_MS - 100);
        expect(click(button)).toBe(false);
        expect(onclick).not.toHaveBeenCalled();
    });

    it('a pointercancel before 500 ms (the browser took a scroll) clears the press: no name, a later click acts', async () => {
        const {onclick, button} = iconButton();
        pointer(button, 'pointerdown', 'touch');
        await advance(200);
        pointer(button, 'pointercancel', 'touch');
        expect(button.classList.contains('lf-pressing')).toBe(false);
        await advance(LONG_PRESS_MS);
        expect(tooltip()).toBeNull();
        expect(click(button)).toBe(true);
        expect(onclick).toHaveBeenCalledTimes(1);
    });

    it('a pen behaves as a finger', async () => {
        const {onclick, button} = iconButton();
        pointer(button, 'pointerdown', 'pen');
        await advance(LONG_PRESS_MS);
        expect(tooltip()).not.toBeNull();
        pointer(button, 'pointerup', 'pen');
        expect(click(button)).toBe(false);
        expect(onclick).not.toHaveBeenCalled();
    });

    it('the contextmenu of a touch press is cancelled and stops at the button; a mouse right click goes up', async () => {
        const {button, container} = iconButton();
        const parent = vi.fn();
        container.addEventListener('contextmenu', parent);

        pointer(button, 'pointerdown', 'touch');
        const touchMenu = new MouseEvent('contextmenu', {bubbles: true, cancelable: true});
        button.dispatchEvent(touchMenu);
        expect(touchMenu.defaultPrevented, 'no browser menu over the name').toBe(true);
        expect(parent, 'a row around the button must not open its menu').not.toHaveBeenCalled();
        pointer(button, 'pointerup', 'touch');
        click(button);

        pointer(button, 'pointerdown', 'mouse');
        const mouseMenu = new MouseEvent('contextmenu', {bubbles: true, cancelable: true});
        button.dispatchEvent(mouseMenu);
        expect(mouseMenu.defaultPrevented).toBe(false);
        expect(parent).toHaveBeenCalledTimes(1);
    });
});

describe('Button — mouse', () => {
    it(`a rest of ${HOVER_DELAY_MS} ms on an icon button shows its name`, async () => {
        const {button} = iconButton();
        pointer(button, 'pointerenter', 'mouse');
        await advance(HOVER_DELAY_MS - 1);
        expect(tooltip()).toBeNull();
        await advance(1);
        expect(tooltip()?.textContent?.trim()).toBe('Edit row');
    });

    it('a rest on a text button with no help shows nothing: the word is the name', async () => {
        const {button} = renderButton({label: 'Save', display: 'text'});
        pointer(button, 'pointerenter', 'mouse');
        await advance(HOVER_DELAY_MS + 200);
        expect(tooltip()).toBeNull();
    });

    it('a rest on a text button with a help shows the help', async () => {
        const {button} = renderButton({label: 'Compare', display: 'text', help: 'Shows both providers side by side.'});
        pointer(button, 'pointerenter', 'mouse');
        await advance(HOVER_DELAY_MS);
        expect(tooltip()?.textContent).toContain('Shows both providers side by side.');
    });

    it('a click hides the name, and none shows on hover until the pointer leaves and comes back', async () => {
        const {onclick, button} = iconButton();
        pointer(button, 'pointerenter', 'mouse');
        await advance(HOVER_DELAY_MS);
        expect(tooltip()).not.toBeNull();

        pointer(button, 'pointerdown', 'mouse');
        pointer(button, 'pointerup', 'mouse');
        expect(click(button)).toBe(true);
        expect(onclick).toHaveBeenCalledTimes(1);
        expect(tooltip(), 'the click closes the name').toBeNull();

        pointer(button, 'pointerenter', 'mouse');
        await advance(HOVER_DELAY_MS + 200);
        expect(tooltip(), 'quiet until the pointer leaves').toBeNull();

        pointer(button, 'pointerleave', 'mouse');
        pointer(button, 'pointerenter', 'mouse');
        await advance(HOVER_DELAY_MS);
        expect(tooltip(), 'back after a leave and an enter').not.toBeNull();
    });

    it('a mouse pointerdown never marks a long press', async () => {
        const {onclick, button} = iconButton();
        pointer(button, 'pointerdown', 'mouse');
        expect(button.classList.contains('lf-pressing')).toBe(false);
        await advance(LONG_PRESS_MS + 100);
        expect(tooltip()).toBeNull();
        pointer(button, 'pointerup', 'mouse');
        expect(click(button)).toBe(true);
        expect(onclick).toHaveBeenCalledTimes(1);
    });
});

describe('Button — keyboard', () => {
    it('a focus brought by Tab shows the name at once; Esc closes it', async () => {
        const {button} = iconButton();
        await fireEvent.keyDown(document, {key: 'Tab'});
        button.focus();
        flushSync();
        expect(tooltip()?.textContent?.trim()).toBe('Edit row');
        await fireEvent.keyDown(document, {key: 'Escape'});
        expect(tooltip()).toBeNull();
    });

    it('a programmatic focus (a dialog giving it back) shows nothing', async () => {
        const {button} = iconButton();
        // Positive control in the same file: the Tab case above opens it. Here no Tab, and any earlier Tab has expired.
        await advance(1);
        button.focus();
        flushSync();
        expect(document.activeElement).toBe(button);
        expect(tooltip()).toBeNull();
    });
});

describe('Button — off with a reason', () => {
    const REASON = 'Select at least one row first.';

    it('is reachable: aria-disabled, never natively disabled, the reason code published', () => {
        const {button} = renderButton({label: 'Delete selected', icon: Trash2, reason: REASON, reasonCode: 'no_selection'});
        expect(button).toHaveAttribute('aria-disabled', 'true');
        expect(button.hasAttribute('disabled')).toBe(false);
        expect(button.tabIndex).toBe(0);
        expect(button).toHaveAttribute('data-disabled-reason', 'no_selection');
        expect(button).toBeDisabled();
    });

    it('a click does not act, is cancelled, and shows the reason with the name', () => {
        const {onclick, button} = renderButton({label: 'Delete selected', icon: Trash2, reason: REASON, reasonCode: 'no_selection'});
        expect(click(button)).toBe(false);
        expect(onclick).not.toHaveBeenCalled();
        expect(tooltip()?.querySelector('strong')?.textContent).toBe('Delete selected');
        expect(tooltip()?.textContent).toContain(REASON);
    });

    it('a touch tap shows the reason too, and does not act', async () => {
        const {onclick, button} = renderButton({label: 'Delete selected', icon: Trash2, reason: REASON});
        pointer(button, 'pointerdown', 'touch');
        await advance(100);
        pointer(button, 'pointerup', 'touch');
        expect(click(button)).toBe(false);
        expect(onclick).not.toHaveBeenCalled();
        expect(tooltip()?.textContent).toContain(REASON);
    });

    it('a Tab focus shows the reason', async () => {
        const {button} = renderButton({label: 'Delete selected', reason: REASON});
        await fireEvent.keyDown(document, {key: 'Tab'});
        button.focus();
        flushSync();
        expect(tooltip()?.textContent).toContain(REASON);
    });

    it('a submit button with a reason inside a form does not submit; a live one does (positive control)', () => {
        const form = document.body.appendChild(document.createElement('form'));
        const submitted = vi.fn((event: Event) => event.preventDefault());
        form.addEventListener('submit', submitted);
        try {
            const blocked = vi.fn();
            render(Button, {target: form, props: {label: 'Send', type: 'submit', reason: REASON, onclick: blocked, 'data-testid': 'probe-off-submit'}});
            render(Button, {target: form, props: {label: 'Send now', type: 'submit', 'data-testid': 'probe-live-submit'}});

            screen.getByTestId('probe-live-submit').click();
            flushSync();
            expect(submitted, 'barrier: a live submit button submits this form in jsdom').toHaveBeenCalledTimes(1);

            expect(click(screen.getByTestId('probe-off-submit'))).toBe(false);
            expect(submitted, 'the off button does not submit').toHaveBeenCalledTimes(1);
            expect(blocked).not.toHaveBeenCalled();
        } finally {
            cleanup();
            form.remove();
        }
    });
});

describe('Button — disabled without a reason', () => {
    it('a text button is natively disabled', () => {
        const {onclick, button} = renderButton({label: 'Save', disabled: true});
        expect(button).toHaveAttribute('disabled');
        expect(button.hasAttribute('aria-disabled')).toBe(false);
        expect(button).toBeDisabled();
        button.click();
        expect(onclick).not.toHaveBeenCalled();
    });

    it.each(['icon', 'auto'] as const)('a display="%s" button stays reachable (aria-disabled, tab order) and shows its name instead of acting', async (display) => {
        const {onclick, button} = renderButton({label: 'Edit row', icon: Pencil, display, disabled: true});
        expect(button).toHaveAttribute('aria-disabled', 'true');
        expect(button.hasAttribute('disabled')).toBe(false);
        expect(button.tabIndex).toBe(0);
        expect(button).toBeDisabled();
        expect(click(button), 'the click is cancelled').toBe(false);
        expect(onclick).not.toHaveBeenCalled();
        expect(tooltip()?.querySelector('strong')?.textContent).toBe('Edit row');
    });

    it('an off icon shows its name to a Tab focus', async () => {
        const {button} = iconButton({disabled: true});
        await fireEvent.keyDown(document, {key: 'Tab'});
        button.focus();
        flushSync();
        expect(tooltip()?.textContent?.trim()).toBe('Edit row');
    });
});

describe('Button — busy', () => {
    it('is aria-busy and aria-disabled, never natively disabled, spins, shows the busy word and drops clicks', () => {
        const {onclick, button} = renderButton({label: 'Save', icon: Pencil, busy: true, busyLabel: 'Saving…'});
        expect(button).toHaveAttribute('aria-busy', 'true');
        expect(button).toHaveAttribute('aria-disabled', 'true');
        expect(button.hasAttribute('disabled')).toBe(false);
        // `lf-btn-spin` is the recipe's own contract (button.css): the busy icon that turns in place.
        expect(button.querySelector('.lf-btn-spin')).not.toBeNull();
        expect(button.textContent).toContain('Saving…');
        expect(click(button)).toBe(false);
        expect(onclick).not.toHaveBeenCalled();
    });

    it('the same button idle has no spinner and acts', async () => {
        const {onclick, button} = renderButton({label: 'Save', icon: Pencil, busy: false, busyLabel: 'Saving…'});
        expect(button.hasAttribute('aria-busy')).toBe(false);
        expect(button.querySelector('.lf-btn-spin')).toBeNull();
        expect(button.textContent).toContain('Save');
        expect(button.textContent).not.toContain('Saving…');
        await fireEvent.click(button);
        expect(onclick).toHaveBeenCalledTimes(1);
    });

    it('a busy submit button inside a form does not submit (the implicit submission clicks it)', () => {
        const form = document.body.appendChild(document.createElement('form'));
        const submitted = vi.fn((event: Event) => event.preventDefault());
        form.addEventListener('submit', submitted);
        try {
            render(Button, {target: form, props: {label: 'Save', type: 'submit', busy: true, 'data-testid': 'probe-busy-submit'}});
            const button = screen.getByTestId('probe-busy-submit');
            // Enter in a field of the form fires a click on the default button: the click is what must be stopped.
            expect(click(button)).toBe(false);
            button.click();
            flushSync();
            expect(submitted).not.toHaveBeenCalled();
        } finally {
            cleanup();
            form.remove();
        }
    });
});

describe('Button — ARIA and markup', () => {
    it('pressed → aria-pressed true or false; absent otherwise', async () => {
        const {button, rerender} = renderButton({label: 'Favourite', pressed: true});
        expect(button).toHaveAttribute('aria-pressed', 'true');
        await rerender({label: 'Favourite', pressed: false, 'data-testid': 'probe-btn'});
        expect(screen.getByTestId('probe-btn')).toHaveAttribute('aria-pressed', 'false');
        cleanup();
        const plain = renderButton({label: 'Favourite'});
        expect(plain.button.hasAttribute('aria-pressed')).toBe(false);
    });

    it('a menu → aria-haspopup="menu", and aria-expanded toggles with the click, the menu rendered while open', async () => {
        const menu = createRawSnippet(() => ({render: () => '<div data-testid="probe-menu">menu</div>'}));
        const {onclick, button} = renderButton({label: 'More', menu});
        expect(button).toHaveAttribute('aria-haspopup', 'menu');
        expect(button).toHaveAttribute('aria-expanded', 'false');
        expect(screen.queryByTestId('probe-menu')).toBeNull();
        await fireEvent.click(button);
        expect(button).toHaveAttribute('aria-expanded', 'true');
        expect(screen.getByTestId('probe-menu')).toBeInTheDocument();
        expect(onclick).toHaveBeenCalledTimes(1);
        await fireEvent.click(button);
        expect(button).toHaveAttribute('aria-expanded', 'false');
        expect(screen.queryByTestId('probe-menu')).toBeNull();
    });

    it('href → an <a> with the same test id, no <button>', () => {
        render(Button, {props: {label: 'Docs', href: '#docs', variant: 'link', 'data-testid': 'probe-link'}});
        const link = screen.getByTestId('probe-link');
        expect(link.tagName).toBe('A');
        expect(link).toHaveAttribute('href', '#docs');
        expect(document.querySelector('button')).toBeNull();
    });

    it('data-testid and every data-* land on the <button> itself', () => {
        render(Button, {props: {label: 'Go', 'data-testid': 'probe-btn', 'data-row': 'r1'}});
        const button = screen.getByTestId('probe-btn');
        expect(button.tagName).toBe('BUTTON');
        expect(button).toHaveAttribute('data-row', 'r1');
    });

    it('aria-label is the label for an icon button, absent for a text button whose word is the label', () => {
        const icon = iconButton();
        expect(icon.button).toHaveAttribute('aria-label', 'Edit row');
        cleanup();
        const text = renderButton({label: 'Save', display: 'text'});
        expect(text.button.hasAttribute('aria-label')).toBe(false);
        expect(text.button.textContent?.trim()).toBe('Save');
        cleanup();
        const short = renderButton({label: 'Edit selected (3)', shortLabel: 'Edit', icon: Pencil});
        expect(short.button, 'a short word is not the name: the label is').toHaveAttribute('aria-label', 'Edit selected (3)');
    });
});

describe('Button — one name at a time', () => {
    it('opening the name of a second button closes the first', async () => {
        render(Button, {props: {label: 'First', icon: Pencil, display: 'icon', 'data-testid': 'probe-a'}});
        render(Button, {props: {label: 'Second', icon: Trash2, display: 'icon', 'data-testid': 'probe-b'}});
        pointer(screen.getByTestId('probe-a'), 'pointerenter', 'mouse');
        await advance(HOVER_DELAY_MS);
        expect(tooltips()).toHaveLength(1);
        expect(tooltip()?.textContent?.trim()).toBe('First');

        await fireEvent.keyDown(document, {key: 'Tab'});
        screen.getByTestId('probe-b').focus();
        flushSync();
        expect(tooltips()).toHaveLength(1);
        expect(tooltip()?.textContent?.trim()).toBe('Second');
    });
});

describe('Button — inside a legacy (non-runes) parent', () => {
    it('the onclick a Svelte 4 component passes fires once', async () => {
        const onpress = vi.fn();
        render(LegacyButtonHost, {props: {onpress}});
        await fireEvent.click(screen.getByTestId('legacy-host-button'));
        expect(onpress).toHaveBeenCalledTimes(1);
    });
});

describe('Button — a disclosure and a menu: aria-expanded and the turning chevron (BTN-2·0, C6)', () => {
    const chevron = (button: HTMLElement) => button.querySelector('[data-lf-chevron]');

    it('expanded false/true → aria-expanded, and the chevron turns while open', async () => {
        const {button, rerender} = renderButton({label: 'Details', expanded: false});
        expect(button).toHaveAttribute('aria-expanded', 'false');
        expect(chevron(button)).not.toBeNull();
        expect(chevron(button)?.classList.contains('rotate-180')).toBe(false);
        await rerender({label: 'Details', expanded: true, 'data-testid': 'probe-btn'});
        expect(screen.getByTestId('probe-btn')).toHaveAttribute('aria-expanded', 'true');
        expect(chevron(screen.getByTestId('probe-btn'))?.classList.contains('rotate-180')).toBe(true);
    });

    it('without expanded or menu there is no aria-expanded and no chevron', () => {
        const {button} = renderButton({label: 'Save'});
        expect(button.hasAttribute('aria-expanded')).toBe(false);
        expect(chevron(button)).toBeNull();
    });

    it('a menu: the chevron turns with open', async () => {
        const menu = createRawSnippet(() => ({render: () => '<div data-testid="probe-menu">menu</div>'}));
        const {button} = renderButton({label: 'More', menu});
        expect(chevron(button)?.classList.contains('rotate-180')).toBe(false);
        await fireEvent.click(button);
        expect(button).toHaveAttribute('aria-expanded', 'true');
        expect(chevron(button)?.classList.contains('rotate-180')).toBe(true);
    });

    it('wrap and truncate together: mounting throws (C17)', () => {
        expect(() => render(Button, {props: {label: 'Both', wrap: true, truncate: true}})).toThrow(/wrap/);
    });

    it('menu and expanded together: mounting throws', () => {
        const menu = createRawSnippet(() => ({render: () => '<div>menu</div>'}));
        expect(() => render(Button, {props: {label: 'Both', menu, expanded: false}})).toThrow(/expanded/);
    });
});

describe('Button — leading and children (BTN-2·0)', () => {
    const leading = createRawSnippet(() => ({render: () => '<span data-testid="probe-flag">🇮🇹</span>'}));
    const rich = createRawSnippet(() => ({render: () => '<span data-testid="probe-rich"><b>12</b> rows</span>'}));

    it('leading replaces the icon, hidden from readers', () => {
        const {button} = renderButton({label: 'Italy', icon: Pencil, leading});
        const box = button.querySelector('[data-lf-leading]');
        expect(box).not.toBeNull();
        expect(box).toHaveAttribute('aria-hidden', 'true');
        expect(within(box as HTMLElement).getByTestId('probe-flag')).toBeInTheDocument();
        expect(button.querySelectorAll('svg'), 'the icon is replaced').toHaveLength(0);
    });

    it('busy: the spinner takes the leading’s place', () => {
        const {button} = renderButton({label: 'Italy', leading, busy: true});
        expect(button.querySelector('[data-lf-leading]')).toBeNull();
        expect(button.querySelector('.lf-btn-spin')).not.toBeNull();
    });

    it('children replace the word, and the label stays the name (aria-label)', () => {
        const {button} = renderButton({label: 'Show 12 rows', children: rich});
        expect(within(button).getByTestId('probe-rich')).toBeInTheDocument();
        expect(button).toHaveAttribute('aria-label', 'Show 12 rows');
        expect(button.querySelector('[data-lf-word]')?.textContent?.trim()).toBe('12 rows');
    });

    it('busy with a busy word: the busy word, not the children', () => {
        const {button} = renderButton({label: 'Show 12 rows', children: rich, busy: true, busyLabel: 'Loading…'});
        expect(within(button).queryByTestId('probe-rich')).toBeNull();
        expect(button.textContent).toContain('Loading…');
    });
});

describe('Button — inside a ButtonGroup: a segment (BTN-2·0, C2)', () => {
    it('the group is a named group; its buttons are segments, toggles with aria-pressed; one outside is not', () => {
        render(ButtonGroupHarness, {props: {mode: 'list'}});
        const group = screen.getByTestId('probe-group');
        expect(group).toHaveAttribute('role', 'group');
        expect(group).toHaveAttribute('aria-label', 'View');
        for (const id of ['probe-grid', 'probe-list']) {
            const segment = screen.getByTestId(id);
            expect(group.contains(segment)).toBe(true);
            expect(segment.className).toBe(buttonClasses({segment: true, joined: true, pressed: id === 'probe-list'}));
            expect(segment.classList.contains('lf-btn-segment')).toBe(true);
        }
        expect(screen.getByTestId('probe-list')).toHaveAttribute('aria-pressed', 'true');
        expect(screen.getByTestId('probe-grid')).toHaveAttribute('aria-pressed', 'false');
        expect(screen.getByTestId('probe-outside').classList.contains('lf-btn-segment'), 'the context stops at the group').toBe(false);
    });
});

describe('CloseButton — variant and tint (BTN-2·0)', () => {
    it('variant="bar-ghost" draws the bar’s ✕; tint="warning" the ✕ on a warning fill', () => {
        render(CloseButton, {props: {variant: 'bar-ghost', 'data-testid': 'probe-bar-close'}});
        expect(screen.getByTestId('probe-bar-close').className).toBe(buttonClasses({variant: 'bar-ghost', size: 'md', shape: 'icon'}));
        render(CloseButton, {props: {tint: 'warning', 'data-testid': 'probe-tint-close'}});
        expect(screen.getByTestId('probe-tint-close').className).toBe(buttonClasses({variant: 'ghost', size: 'md', shape: 'icon', tint: 'warning'}));
    });
});

describe('Button — a cut word shows the name (BTN-2·0, C7)', () => {
    function cutWord(button: HTMLElement, scroll: number, client: number) {
        const word = button.querySelector<HTMLElement>('[data-lf-word]')!;
        expect(word.classList.contains('truncate'), 'truncate cuts the word').toBe(true);
        Object.defineProperty(word, 'scrollWidth', {configurable: true, value: scroll});
        Object.defineProperty(word, 'clientWidth', {configurable: true, value: client});
    }

    it('a word wider than its box: a mouse rest shows the name', async () => {
        const {button} = renderButton({label: 'A rather long portfolio name', truncate: true});
        cutWord(button, 240, 120);
        pointer(button, 'pointerenter', 'mouse');
        await advance(HOVER_DELAY_MS);
        expect(tooltip()?.textContent?.trim()).toBe('A rather long portfolio name');
    });

    it('a word that fits: nothing, the word is the name', async () => {
        const {button} = renderButton({label: 'A rather long portfolio name', truncate: true});
        cutWord(button, 120, 120);
        pointer(button, 'pointerenter', 'mouse');
        await advance(HOVER_DELAY_MS + 200);
        expect(tooltip()).toBeNull();
    });
});

describe('Button — hideWord, compact and a segment alone (BTN-2d, C16)', () => {
    const word = (button: HTMLElement) => button.querySelector('[data-lf-word]');

    it('hideWord hides the word of display="auto" (the parent measured its room); the name stays', async () => {
        const {button, rerender} = renderButton({label: 'Export', icon: Pencil, display: 'auto', hideWord: false});
        expect(word(button)?.classList.contains('hidden')).toBe(false);
        await rerender({label: 'Export', icon: Pencil, display: 'auto', hideWord: true, 'data-testid': 'probe-btn'});
        const hidden = screen.getByTestId('probe-btn');
        expect(word(hidden)?.classList.contains('hidden')).toBe(true);
        expect(hidden).toHaveAttribute('aria-label', 'Export');
    });

    it('a hidden word leaves the name to the tooltip: a rest shows it', async () => {
        const {button} = renderButton({label: 'Export', icon: Pencil, display: 'auto', hideWord: true});
        pointer(button, 'pointerenter', 'mouse');
        await advance(HOVER_DELAY_MS);
        expect(tooltip()?.textContent?.trim()).toBe('Export');
    });

    it('hideWord does nothing to a word that is not auto', () => {
        const {button} = renderButton({label: 'Export', icon: Pencil, display: 'icon-text', hideWord: true});
        expect(word(button)?.classList.contains('hidden')).toBe(false);
    });

    it('compact is height, not the word: the recipe’s compact, the word still in view', () => {
        const {button} = renderButton({label: 'Export', size: 'sm', compact: true, display: 'auto', icon: Pencil});
        expect(button.className).toBe(buttonClasses({size: 'sm', compact: true}));
        expect(button.className, 'one step lower than the plain one').not.toBe(buttonClasses({size: 'sm'}));
        expect(word(button)?.classList.contains('hidden')).toBe(false);
    });

    it.each([true, false])('a segment alone, pressed %s: the recipe’s segment, not joined, a toggle', (pressed) => {
        const {button} = renderButton({label: '1Y', size: 'sm', compact: true, segment: true, pressed});
        expect(button.className).toBe(buttonClasses({size: 'sm', compact: true, segment: true, pressed}));
        expect(button.classList.contains('lf-btn-segment'), 'only a group joins it').toBe(false);
        expect(button).toHaveAttribute('aria-pressed', String(pressed));
    });
});
