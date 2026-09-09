// @vitest-environment jsdom
import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';
import {cleanup, fireEvent, render, screen, waitFor} from '$test/component';
import Harness from '$test/harness/ReviewSupportModalBaseHarness.svelte';

vi.mock('$app/environment', () => ({browser: true, dev: true, building: false, version: 'test'}));

function mount(props: Partial<{open: boolean; trapFocus: boolean; restoreFocus: boolean; onRequestClose: () => void}> = {}) {
    const onRequestClose = vi.fn();
    return {
        onRequestClose,
        ...render(Harness, {open: true, trapFocus: false, restoreFocus: false, onRequestClose, ...props}),
    };
}

beforeEach(() => {
    vi.spyOn(window, 'scrollTo').mockImplementation(() => {});
    vi.spyOn(Element.prototype, 'getClientRects').mockImplementation(
        () =>
            [
                {
                    x: 0,
                    y: 0,
                    width: 1,
                    height: 1,
                    top: 0,
                    right: 1,
                    bottom: 1,
                    left: 0,
                },
            ] as unknown as DOMRectList,
    );
});

afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
});

describe('ModalBase — optional focus management', () => {
    it('keeps focus on the backdrop and does not restore the opener unless focus handling is opted in', async () => {
        const opener = document.createElement('button');
        opener.type = 'button';
        document.body.appendChild(opener);
        opener.focus();

        const view = mount();
        const dialog = screen.getByTestId('review-support-modal-base');

        await waitFor(() => expect(dialog).toHaveFocus());
        expect(screen.getByTestId('review-support-first')).not.toHaveFocus();

        await view.rerender({open: false, trapFocus: false, restoreFocus: false, onRequestClose: view.onRequestClose});
        await waitFor(() => expect(screen.queryByTestId('review-support-modal-base')).toBeNull());
        expect(opener).not.toHaveFocus();
        opener.remove();
    });

    it('focuses the first visible enabled control, wraps focus, closes on Escape and restores the opener when opted in', async () => {
        const opener = document.createElement('button');
        opener.type = 'button';
        document.body.appendChild(opener);
        opener.focus();

        const view = mount({trapFocus: true, restoreFocus: true});
        const dialog = screen.getByTestId('review-support-modal-base');
        const first = screen.getByTestId('review-support-first');
        const last = screen.getByTestId('review-support-last');

        await waitFor(() => expect(first).toHaveFocus());

        last.focus();
        await fireEvent.keyDown(dialog, {key: 'Tab'});
        expect(first).toHaveFocus();

        first.focus();
        await fireEvent.keyDown(dialog, {key: 'Tab', shiftKey: true});
        expect(last).toHaveFocus();

        await fireEvent.keyDown(dialog, {key: 'Escape'});
        expect(view.onRequestClose).toHaveBeenCalledTimes(1);

        await view.rerender({open: false, trapFocus: true, restoreFocus: true, onRequestClose: view.onRequestClose});
        await waitFor(() => expect(opener).toHaveFocus());
        opener.remove();
    });
});
