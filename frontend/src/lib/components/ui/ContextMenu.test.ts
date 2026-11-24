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
import {afterEach, describe, expect, it, vi} from 'vitest';
import {cleanup, fireEvent, render, screen, waitFor} from '$test/component';
import ContextMenu, {type ContextMenuItem} from './ContextMenu.svelte';

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
