// @vitest-environment jsdom
import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';
import {cleanup, fireEvent, render, screen, waitFor, within} from '$test/component';
import {toasts} from '$lib/stores/app/toastStore.svelte';
import {entityDetailLinkHtml} from '$lib/utils/core/entityLink';
import ToastContainer from './ToastContainer.svelte';

/**
 * Real, file-isolated toast store, duration=0: these are interaction tests, not
 * countdown tests. No real/fake clock advances or browser navigation claims.
 *
 * The close-button cases require the production owner's additive
 * data-testid="toast-dismiss" hook, requested during source-only authoring.
 */
beforeEach(() => toasts.clear());
afterEach(() => {
    cleanup();
    toasts.clear();
});

function mountToast(message = '<span data-testid="toast-plain-body">Owned notification</span>') {
    const id = toasts.success(message, 0);
    render(ToastContainer);
    const root = screen.getByTestId('toast-success');
    expect(root).toBeVisible();
    const setPointerCapture = vi.fn<(pointerId: number) => void>();
    const releasePointerCapture = vi.fn<(pointerId: number) => void>();
    // jsdom has no pointer-capture implementation. Record calls on the actual
    // gesture owner; never install a silent no-op that would hide capture.
    Object.defineProperties(root, {
        setPointerCapture: {configurable: true, value: setPointerCapture},
        releasePointerCapture: {configurable: true, value: releasePointerCapture},
    });
    return {id, root, setPointerCapture, releasePointerCapture};
}

const POINTER_ID = 17;

async function pointer(target: HTMLElement, type: 'pointerdown' | 'pointermove' | 'pointerup', x = 100, y = 100, button = 0) {
    // MouseEvent supplies coordinates/button even on jsdom versions that do
    // not implement PointerEvent. Only the extra pointerId needs a fixture.
    const event = new MouseEvent(type, {bubbles: true, cancelable: true, clientX: x, clientY: y, button});
    Object.defineProperty(event, 'pointerId', {value: POINTER_ID});
    await fireEvent(target, event);
    return event;
}

async function clickWithoutNavigating(target: HTMLElement) {
    const preventionAtWindow = vi.fn<(prevented: boolean) => void>();
    const stopJsdomNavigation = (event: MouseEvent) => {
        // Observe after the event has crossed the component, then suppress only
        // jsdom's unsupported navigation. This is not a simulated route success.
        preventionAtWindow(event.defaultPrevented);
        event.preventDefault();
    };
    window.addEventListener('click', stopJsdomNavigation, {once: true});
    try {
        await fireEvent.click(target);
        expect(preventionAtWindow).toHaveBeenCalledTimes(1);
        expect(preventionAtWindow).toHaveBeenCalledWith(false);
    } finally {
        window.removeEventListener('click', stopJsdomNavigation);
    }
}

describe('ToastContainer — native links versus swipe capture', () => {
    it.each([
        {
            name: 'asset anchor',
            message: entityDetailLinkHtml({kind: 'asset', id: 42}, 'Owned asset'),
            anchorTestId: 'toast-asset-link',
            startTestId: 'toast-asset-link',
            href: '/assets/42',
        },
        {
            name: 'FX anchor',
            message: entityDetailLinkHtml({kind: 'fx', slug: 'JPY-RON'}, 'JPY / RON'),
            anchorTestId: 'toast-fx-link',
            startTestId: 'toast-fx-link',
            href: '/fx/JPY-RON',
        },
        {
            name: 'nested anchor target',
            // ToastContainer accepts HTML. This owned fixture proves closest()
            // sees an ancestor link; it does not pass raw HTML to the link helper.
            message: '<a href="/assets/42" data-testid="toast-asset-link"><span data-testid="toast-link-child">Owned asset</span></a>',
            anchorTestId: 'toast-asset-link',
            startTestId: 'toast-link-child',
            href: '/assets/42',
        },
    ])('leaves $name pointer and click events uncaptured and native', async ({message, anchorTestId, startTestId, href}) => {
        const {id, root, setPointerCapture, releasePointerCapture} = mountToast(message);
        const anchor = within(root).getByTestId(anchorTestId);
        const start = within(root).getByTestId(startTestId);
        expect(anchor).toBeVisible();
        expect(anchor).toBeInstanceOf(HTMLAnchorElement);
        expect(anchor).toHaveAttribute('href', href);
        expect(anchor.tabIndex).toBe(0);

        const down = await pointer(start, 'pointerdown');
        // A move beyond the swipe threshold must still not arm a dismissal.
        await pointer(root, 'pointermove', 190, 100);
        await pointer(root, 'pointerup', 190, 100);
        await clickWithoutNavigating(start);

        expect(down.defaultPrevented).toBe(false);
        expect(setPointerCapture).not.toHaveBeenCalled();
        expect(releasePointerCapture).not.toHaveBeenCalled();
        expect(toasts.items.some((toast) => toast.id === id)).toBe(true);
        expect(anchor).toBeVisible();
        expect(root.style.transform).toBe('');
    });

    it.each(['Enter', 'Tab'])('does not consume %s on a focused native anchor', async (key) => {
        const {id, root, setPointerCapture, releasePointerCapture} = mountToast(entityDetailLinkHtml({kind: 'asset', id: 42}, 'Owned asset'));
        const anchor = within(root).getByTestId('toast-asset-link');
        anchor.focus();
        expect(anchor).toHaveFocus();
        expect(anchor).toHaveAttribute('href', '/assets/42');
        const event = new KeyboardEvent('keydown', {key, bubbles: true, cancelable: true});

        await fireEvent(anchor, event);

        expect(event.defaultPrevented).toBe(false);
        expect(setPointerCapture).not.toHaveBeenCalled();
        expect(releasePointerCapture).not.toHaveBeenCalled();
        expect(toasts.items.some((toast) => toast.id === id)).toBe(true);
        // jsdom cannot prove Tab traversal or Enter navigation; E2E owns those.
    });
});

describe('ToastContainer — existing dismissal contracts', () => {
    it('keeps the dismiss button clickable without starting a swipe', async () => {
        const {id, root, setPointerCapture, releasePointerCapture} = mountToast();
        const dismiss = within(root).getByTestId('toast-dismiss');
        expect(dismiss).toBeVisible();
        expect(dismiss).toBeInstanceOf(HTMLButtonElement);
        expect(dismiss).toBeEnabled();

        await pointer(dismiss, 'pointerdown');
        await pointer(dismiss, 'pointerup');
        expect(setPointerCapture).not.toHaveBeenCalled();
        expect(releasePointerCapture).not.toHaveBeenCalled();
        expect(toasts.items.some((toast) => toast.id === id)).toBe(true);

        await fireEvent.click(dismiss);

        await waitFor(() => expect(root).not.toBeInTheDocument());
        expect(toasts.items.some((toast) => toast.id === id)).toBe(false);
    });

    it.each([
        {direction: 'right', dx: 80, dy: 0},
        {direction: 'left', dx: -80, dy: 0},
        {direction: 'up', dx: 10, dy: -80},
    ])('still captures and dismisses a plain-body drag $direction', async ({dx, dy}) => {
        const {id, root, setPointerCapture, releasePointerCapture} = mountToast();
        const body = within(root).getByTestId('toast-plain-body');

        await pointer(body, 'pointerdown');
        expect(setPointerCapture).toHaveBeenCalledTimes(1);
        expect(setPointerCapture).toHaveBeenCalledWith(POINTER_ID);
        await pointer(root, 'pointermove', 100 + dx, 100 + dy);
        await pointer(root, 'pointerup', 100 + dx, 100 + dy);

        expect(releasePointerCapture).toHaveBeenCalledTimes(1);
        expect(releasePointerCapture).toHaveBeenCalledWith(POINTER_ID);
        await waitFor(() => expect(root).not.toBeInTheDocument());
        expect(toasts.items.some((toast) => toast.id === id)).toBe(false);
    });

    it.each([
        {direction: 'short horizontal', dx: 30, dy: 0},
        {direction: 'short upward', dx: 0, dy: -30},
        {direction: 'downward', dx: 0, dy: 80},
    ])('releases a $direction body gesture without dismissing the toast', async ({dx, dy}) => {
        const {id, root, setPointerCapture, releasePointerCapture} = mountToast();

        await pointer(within(root).getByTestId('toast-plain-body'), 'pointerdown');
        await pointer(root, 'pointermove', 100 + dx, 100 + dy);
        await pointer(root, 'pointerup', 100 + dx, 100 + dy);

        expect(setPointerCapture).toHaveBeenCalledTimes(1);
        expect(setPointerCapture).toHaveBeenCalledWith(POINTER_ID);
        expect(releasePointerCapture).toHaveBeenCalledTimes(1);
        expect(releasePointerCapture).toHaveBeenCalledWith(POINTER_ID);
        expect(toasts.items.some((toast) => toast.id === id)).toBe(true);
        expect(root).toBeVisible();
        expect(root.style.transform).toBe('');
    });
});
