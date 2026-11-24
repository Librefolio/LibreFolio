// @vitest-environment jsdom
/**
 * ContextMenu — the row menu's blocked item and keyboard (plan 77, SEL-M; Q-SEL-11, Q-SEL-12).
 *
 * An item that makes sense but is blocked carries its reason. It is `aria-disabled`, not natively disabled, so it keeps
 * the focus, the tap and the click that open the reason; its click runs nothing and leaves the menu open. The keyboard
 * follows the WAI-ARIA menu: the first item takes the focus when the menu opens, ↑ ↓ Home End move through every item
 * (the blocked ones too, separators skipped), Escape and Tab close and give the focus back to the element that opened the
 * menu. An item is never off without a reason: there is no `disabled`. Driven through test ids and roles, never text.
 *
 * Registered in `front_component_unit` (`scripts/test_runner/_frontend_utility.py`, action `component-unit`).
 */
import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';
import {cleanup, fireEvent, render, screen, waitFor} from '$test/component';
import ContextMenu, {type ContextMenuItem} from './ContextMenu.svelte';
import {fingerMenuPosition} from './contextMenuPlacement';

afterEach(() => {
    cleanup();
    document.querySelector('[data-testid="probe-trigger"]')?.remove();
});

const ITEMS: ContextMenuItem[] = [{id: 'view', label: 'View'}, {type: 'separator'}, {id: 'sync', label: 'Sync', blocked: {hint: 'The Asset is inactive', reason: 'inactive'}}, {id: 'delete', label: 'Delete', variant: 'danger'}];

/** A ⋮ that has the focus, as after the keyboard opened the menu from it. */
function trigger(): HTMLButtonElement {
    const button = document.createElement('button');
    button.dataset.testid = 'probe-trigger';
    document.body.appendChild(button);
    button.focus();
    return button;
}

function open(anchorEl: HTMLElement | null = null) {
    const onAction = vi.fn();
    const onClose = vi.fn();
    render(ContextMenu, {props: {x: 10, y: 10, items: ITEMS, onAction, onClose, anchorEl}});
    return {onAction, onClose};
}

const item = (id: string) => screen.getByTestId(`context-menu-action-${id}`);

describe('ContextMenu — a blocked item says why (77 SEL-M)', () => {
    it('is reachable and off: aria-disabled, its reason code and its description, not natively disabled', () => {
        open();
        const sync = item('sync');
        expect(sync).toHaveAttribute('aria-disabled', 'true');
        expect(sync).not.toHaveAttribute('disabled');
        expect(sync).toHaveAttribute('data-disabled-reason', 'inactive');
        const described = document.getElementById(sync.getAttribute('aria-describedby') ?? '');
        expect(described?.textContent).toBe('The Asset is inactive');
    });

    it('a click runs nothing, keeps the menu open, and opens the reason', async () => {
        const {onAction, onClose} = open();
        await fireEvent.click(item('sync'));
        expect(onAction).not.toHaveBeenCalled();
        expect(onClose).not.toHaveBeenCalled();
        expect((await screen.findByTestId('tooltip-content')).textContent?.trim()).toBe('The Asset is inactive');
    });

    it('a press on the open reason does not close the menu', async () => {
        const {onClose} = open();
        await fireEvent.click(item('sync'));
        const tip = await screen.findByTestId('tooltip-content');
        await fireEvent.pointerDown(tip);
        expect(onClose).not.toHaveBeenCalled();
    });
});

describe('ContextMenu — the keyboard of a WAI-ARIA menu (77 SEL-M)', () => {
    it('the first item takes the focus when the menu opens', async () => {
        open();
        await waitFor(() => expect(item('view')).toHaveFocus());
    });

    it('↓ reaches the blocked item, skipping the separator; Home and End; it wraps', async () => {
        open();
        const menu = screen.getByTestId('context-menu');
        await waitFor(() => expect(item('view')).toHaveFocus());
        await fireEvent.keyDown(menu, {key: 'ArrowDown'});
        expect(item('sync')).toHaveFocus();
        await fireEvent.keyDown(menu, {key: 'ArrowDown'});
        expect(item('delete')).toHaveFocus();
        await fireEvent.keyDown(menu, {key: 'ArrowDown'});
        expect(item('view'), 'past the last item, the first').toHaveFocus();
        await fireEvent.keyDown(menu, {key: 'End'});
        expect(item('delete')).toHaveFocus();
        await fireEvent.keyDown(menu, {key: 'Home'});
        expect(item('view')).toHaveFocus();
        await fireEvent.keyDown(menu, {key: 'ArrowUp'});
        expect(item('delete'), 'before the first item, the last').toHaveFocus();
    });

    it('moved by the keyboard, the blocked item opens its reason on focus', async () => {
        open();
        const menu = screen.getByTestId('context-menu');
        await waitFor(() => expect(item('view')).toHaveFocus());
        await fireEvent.keyDown(menu, {key: 'ArrowDown'});
        expect((await screen.findByTestId('tooltip-content')).textContent?.trim()).toBe('The Asset is inactive');
    });

    it('Escape closes and gives the focus back to the ⋮ that opened the menu', async () => {
        const button = trigger();
        const {onClose} = open(button);
        await waitFor(() => expect(item('view')).toHaveFocus());
        await fireEvent.keyDown(window, {key: 'Escape'});
        expect(onClose).toHaveBeenCalled();
        expect(button).toHaveFocus();
    });

    it('running an item gives the focus back to the ⋮ first, then runs it', async () => {
        const button = trigger();
        const {onAction} = open(button);
        await waitFor(() => expect(item('view')).toHaveFocus());
        let focusedAtRun: Element | null = null;
        onAction.mockImplementation(() => (focusedAtRun = document.activeElement));
        await fireEvent.click(item('view'));
        expect(onAction).toHaveBeenCalledWith('view');
        expect(focusedAtRun, 'the focus is back on the ⋮ when the action runs').toBe(button);
    });

    it('the keys the menu handles do not reach what is under it', async () => {
        open();
        const under = vi.fn();
        document.body.addEventListener('keydown', under);
        await waitFor(() => expect(item('view')).toHaveFocus());
        for (const key of ['ArrowDown', 'ArrowUp', 'Home', 'End', 'Enter', ' ']) await fireEvent.keyDown(screen.getByTestId('context-menu'), {key});
        document.body.removeEventListener('keydown', under);
        expect(under).not.toHaveBeenCalled();
    });

    it('Tab closes and gives the focus back too', async () => {
        const button = trigger();
        const {onClose} = open(button);
        await waitFor(() => expect(item('view')).toHaveFocus());
        await fireEvent.keyDown(screen.getByTestId('context-menu'), {key: 'Tab'});
        expect(onClose).toHaveBeenCalled();
        expect(button).toHaveFocus();
    });
});

/**
 * Where the menu opens (85 BTN-0): `origin="pointer"` (the default, a mouse) keeps the classic placement and publishes
 * no `data-placement`; `origin="finger"` (a long press) goes to the left of the finger and above it, placed by
 * `fingerMenuPosition`, and publishes where it went. jsdom has no layout: the menu's box and the viewport are given.
 */
describe('ContextMenu — the origin of the menu (85 BTN-0)', () => {
    const VIEWPORT = {width: 430, height: 932};
    const MENU_BOX = {width: 200, height: 150};
    let saved: {width: number; height: number};

    beforeEach(() => {
        saved = {width: window.innerWidth, height: window.innerHeight};
        Object.defineProperty(window, 'innerWidth', {value: VIEWPORT.width, configurable: true, writable: true});
        Object.defineProperty(window, 'innerHeight', {value: VIEWPORT.height, configurable: true, writable: true});
        vi.spyOn(HTMLElement.prototype, 'getBoundingClientRect').mockImplementation(function (this: HTMLElement) {
            const box = this.dataset.testid === 'context-menu' ? MENU_BOX : {width: 0, height: 0};
            return {x: 0, y: 0, left: 0, top: 0, right: box.width, bottom: box.height, width: box.width, height: box.height, toJSON: () => ({})} as DOMRect;
        });
    });

    afterEach(() => {
        vi.restoreAllMocks();
        Object.defineProperty(window, 'innerWidth', {value: saved.width, configurable: true, writable: true});
        Object.defineProperty(window, 'innerHeight', {value: saved.height, configurable: true, writable: true});
    });

    function openAt(x: number, y: number, origin?: 'pointer' | 'finger') {
        render(ContextMenu, {props: {x, y, items: ITEMS, onAction: vi.fn(), onClose: vi.fn(), ...(origin ? {origin} : {})}});
        return screen.getByTestId('context-menu');
    }

    it('by default it is a pointer’s: data-origin="pointer", no data-placement, its top-left at the point', () => {
        const menu = openAt(100, 200);
        expect(menu).toHaveAttribute('data-origin', 'pointer');
        expect(menu.hasAttribute('data-placement')).toBe(false);
        expect(menu.style.left).toBe('100px');
        expect(menu.style.top).toBe('200px');
    });

    it('origin="finger": data-origin="finger", data-placement, and the left/top of fingerMenuPosition', () => {
        const menu = openAt(400, 600, 'finger');
        const expected = fingerMenuPosition({x: 400, y: 600}, MENU_BOX, VIEWPORT);
        // Barrier: the case is the left-above one, so a menu drawn at the point would fail below.
        expect(expected).toEqual({left: 188, top: 438, horizontal: 'left', vertical: 'above'});
        expect(menu).toHaveAttribute('data-origin', 'finger');
        expect(menu).toHaveAttribute('data-placement', 'left-above');
        expect(menu.style.left).toBe(`${expected.left}px`);
        expect(menu.style.top).toBe(`${expected.top}px`);
    });

    it('origin="finger" near the top-left corner: centred and below', () => {
        const menu = openAt(60, 40, 'finger');
        const expected = fingerMenuPosition({x: 60, y: 40}, MENU_BOX, VIEWPORT);
        expect(menu).toHaveAttribute('data-placement', `${expected.horizontal}-${expected.vertical}`);
        expect(menu).toHaveAttribute('data-placement', 'centre-below');
        expect(menu.style.left).toBe(`${expected.left}px`);
        expect(menu.style.top).toBe(`${expected.top}px`);
    });
});

/**
 * D13 (85 BTN-2·0): an item with a hint (`title`) carries it once, in the design system's Tooltip, and the reader gets
 * it as the item's description. No native `title` beside it: the browser's own tooltip would show the same text twice,
 * late and unstyled.
 */
describe('ContextMenu — an item’s hint is one, not a native title (85 BTN-2·0, D13)', () => {
    const HINTED: ContextMenuItem[] = [
        {id: 'plain', label: 'Plain'},
        {id: 'hinted', label: 'Hinted', title: 'probe: what this item does'},
    ];

    it('has no title attribute; aria-describedby points at the hint’s text', () => {
        render(ContextMenu, {props: {x: 10, y: 10, items: HINTED, onAction: vi.fn(), onClose: vi.fn()}});
        const hinted = item('hinted');
        expect(hinted.hasAttribute('title')).toBe(false);
        const describedBy = hinted.getAttribute('aria-describedby');
        expect(describedBy, 'the hint is the item’s description').toBeTruthy();
        expect(document.getElementById(describedBy!)?.textContent?.trim()).toBe('probe: what this item does');
        // The control: an item with no hint has neither.
        expect(item('plain').hasAttribute('title')).toBe(false);
        expect(item('plain').hasAttribute('aria-describedby')).toBe(false);
    });
});
