// @vitest-environment jsdom
import {afterEach, beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';
import {tick, type ComponentProps} from 'svelte';
import {cleanup, fireEvent, render, screen, setupI18n, waitFor} from '$test/component';
import Harness from '$test/harness/ReviewSupportModalBaseHarness.svelte';
import ConfirmModal from './ConfirmModal.svelte';
import ModalBase from './ModalBase.svelte';

vi.mock('$app/environment', () => ({browser: true, dev: true, building: false, version: 'test'}));

beforeAll(async () => {
    await setupI18n();
});

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

type Tone = NonNullable<ComponentProps<typeof ModalBase>['tone']>;

/**
 * The frame's border is one ternary on `tone`. Each branch draws its own border and carries nothing of the other's: two
 * border colours on one element resolve not in the order a caller wrote them but in the order Tailwind emits them, by
 * name (rule 4 of the design system), so a danger frame that kept `border-lf-raised` would not be red. The same reason
 * makes a red frame `tone="danger"`, never a colour passed through `contentClass`.
 * Exact class tokens, never substrings: `border-2` and every `border-lf-…` role contain `border`.
 */
const FRAME_BORDER: Record<Tone, {drawn: string[]; absent: string[]}> = {
    default: {drawn: ['border', 'border-lf-raised'], absent: ['border-2', 'border-lf-danger-line']},
    danger: {drawn: ['border-2', 'border-lf-danger-line'], absent: ['border', 'border-lf-raised']},
};

/** The frame of an open ModalBase: the one element under the dialog that publishes its tone. */
function frameOf(dialog: HTMLElement): HTMLElement {
    const frames = dialog.querySelectorAll<HTMLElement>('[data-tone]');
    expect(frames, 'the dialog does not hold exactly one frame publishing its tone').toHaveLength(1);
    return frames[0];
}

/** The state first, then the classes that draw it; one negative per class, as `.not.toHaveClass(a, b)` passes with only one of them gone. */
function expectFrame(frame: HTMLElement, tone: Tone) {
    expect(frame, `the frame does not publish tone="${tone}"`).toHaveAttribute('data-tone', tone);
    expect(frame, `the ${tone} frame does not draw its own border`).toHaveClass(...FRAME_BORDER[tone].drawn);
    for (const className of FRAME_BORDER[tone].absent) {
        expect(frame, `the ${tone} frame also carries ${className}, a class of the other frame`).not.toHaveClass(className);
    }
}

// The markup exists twice, with and without transitions: both branches must draw the same frame.
describe.each([
    {path: 'without transitions', noTransition: true},
    {path: 'with transitions', noTransition: false},
])('ModalBase — the frame tone, rendered $path', ({noTransition}) => {
    function mountFrame(props: {tone?: Tone; contentClass?: string} = {}): HTMLElement {
        render(ModalBase, {open: true, noTransition, testId: 'modal-base-tone', ...props});
        return frameOf(screen.getByTestId('modal-base-tone'));
    }

    it('draws the 1 px neutral frame when no tone is given', () => {
        expectFrame(mountFrame(), 'default');
    });

    it('draws the 2 px danger frame for tone="danger", with nothing of the neutral one', () => {
        expectFrame(mountFrame({tone: 'danger'}), 'danger');
    });

    it.each(['default', 'danger'] as const)('still appends the caller contentClass to the %s frame', (tone) => {
        const frame = mountFrame({tone, contentClass: 'max-w-[95vw] w-[95vw]'});
        expectFrame(frame, tone);
        expect(frame, 'the caller contentClass did not reach the frame').toHaveClass('max-w-[95vw]', 'w-[95vw]');
    });
});

describe('ConfirmModal — typed result actions', () => {
    it('renders the typed safe action as a link and keeps backend HTML inert', () => {
        render(ConfirmModal, {
            open: true,
            title: 'Synthetic title',
            message: 'Synthetic message',
            onConfirm: vi.fn(),
            onCancel: vi.fn(),
            testId: 'confirm-safe-action',
            results: [
                {
                    label: 'Synthetic asset',
                    success: false,
                    detail: 'Blocked <a href="/backend-supplied">backend markup</a>',
                    action: {
                        href: '/transactions?asset_id=74001',
                        label: 'Synthetic action',
                        testId: 'confirm-safe-action-link',
                    },
                },
            ],
        });

        const action = screen.getByTestId('confirm-safe-action-link');
        expect(action.tagName).toBe('A');
        expect(action).toHaveAttribute('href', '/transactions?asset_id=74001');
        expect(screen.getByTestId('confirm-safe-action-link-detail')).toHaveTextContent('Blocked <a href="/backend-supplied">backend markup</a>');
    });
});

/**
 * Escape right after the open, before any animation frame.
 *
 * ModalBase handles Escape only through `onkeydown` on its backdrop, so a key event reaches it only when the focus is
 * inside the modal. The focus used to move in a `requestAnimationFrame` scheduled by the open effect: until that frame
 * ran, the focus stayed on the opener outside, and an Escape dispatched there never reached the backdrop. The modal
 * ignored it (E2E FSCH-004b on a loaded machine: the key landed between the open and the frame).
 *
 * The frames are held, not run: `requestAnimationFrame` only queues, and a test releases the queue when it wants the
 * frame to have happened. That makes the state «open, frame not yet run» a state the test builds, instead of a race it
 * hopes to win. The event goes where a browser delivers it: to `document.activeElement`, bubbling.
 */
describe('ModalBase — Escape before the first animation frame', () => {
    let queue: FrameRequestCallback[] = [];
    let opener: HTMLButtonElement;

    beforeEach(() => {
        queue = [];
        vi.stubGlobal('requestAnimationFrame', (callback: FrameRequestCallback) => queue.push(callback));
        vi.stubGlobal('cancelAnimationFrame', (id: number) => {
            // ids are 1-based queue positions; a cancelled slot is left as a no-op so the other ids stay valid
            if (queue[id - 1]) queue[id - 1] = () => {};
        });
        opener = document.createElement('button');
        opener.type = 'button';
        document.body.appendChild(opener);
        opener.focus();
        expect(opener, 'premise: the opener holds the focus').toHaveFocus();
    });

    afterEach(() => {
        vi.unstubAllGlobals();
        opener.remove();
    });

    /** Release every held frame, as the browser would have done by the next paint. */
    function runFrames() {
        const pending = queue;
        queue = [];
        for (const callback of pending) callback(performance.now());
    }

    /** The user opens the modal from the opener: closed first, then flipped to open. Frames stay held. */
    async function openFromOpener(props: Partial<{trapFocus: boolean; restoreFocus: boolean}> = {}) {
        const onRequestClose = vi.fn().mockName('onRequestClose');
        const base = {trapFocus: false, restoreFocus: false, onRequestClose, ...props};
        const view = render(Harness, {open: false, ...base});
        await view.rerender({open: true, ...base});
        await tick();
        const dialog = screen.getByTestId('review-support-modal-base');
        return {view, dialog, onRequestClose, base};
    }

    /** Press Escape where the browser sends it: the element that holds the focus right now. */
    async function pressEscapeOnFocused() {
        await fireEvent.keyDown(document.activeElement ?? document.body, {key: 'Escape'});
    }

    it('closes on an Escape pressed straight after the open, with no frame run', async () => {
        const {onRequestClose} = await openFromOpener();
        expect(queue.length, 'premise: the open scheduled its frame and the frame has not run').toBeGreaterThan(0);

        await pressEscapeOnFocused();

        expect(onRequestClose).toHaveBeenCalledTimes(1);
    });

    it('moves the focus into the modal as it opens, with no frame run', async () => {
        const {dialog} = await openFromOpener();
        expect(queue.length, 'premise: the open scheduled its frame and the frame has not run').toBeGreaterThan(0);

        expect(dialog.contains(document.activeElement), 'the focus is still outside the open modal').toBe(true);
        expect(opener).not.toHaveFocus();
    });

    it('closes on Escape once the frames have run (control)', async () => {
        const {onRequestClose} = await openFromOpener();
        runFrames();

        await pressEscapeOnFocused();

        expect(onRequestClose).toHaveBeenCalledTimes(1);
    });

    it('with trapFocus, gives the first control the focus once the frame has run', async () => {
        const {dialog} = await openFromOpener({trapFocus: true});
        runFrames();

        const first = screen.getByTestId('review-support-first');
        expect(dialog.contains(document.activeElement)).toBe(true);
        expect(first).toHaveFocus();
    });

    it('with restoreFocus, gives the focus back to the opener when the modal closes', async () => {
        const {view, base} = await openFromOpener({restoreFocus: true});
        runFrames();
        expect(opener, 'premise: the modal took the focus from the opener').not.toHaveFocus();

        await view.rerender({...base, open: false});
        await waitFor(() => expect(screen.queryByTestId('review-support-modal-base')).toBeNull());

        expect(opener).toHaveFocus();
    });
});
