// @vitest-environment jsdom
/**
 * ModalBase — one Escape closes one layer (Vitest + jsdom).
 *
 * Inside a modal, Escape has more than one thing it can close: a row menu opened over a table, a
 * select with its list dropped over the form. One Escape must close the top layer and stop there.
 * Today it does not. The inner layer handles the key and lets it go on — ContextMenu from a
 * capturing `keydown` listener on window, SearchSelect from the keydown of its search box, or of its
 * trigger when the search is inline — and the same keydown then bubbles from the focused element up
 * to ModalBase's backdrop, which closes on any Escape. Verified live: one Escape on an open row menu
 * inside the transactions BulkModal closed the menu and the modal with it.
 *
 * The approved cure is in the inner layers: each stops the propagation of the Escape it consumes.
 * ModalBase does not change, so the subject is what reaches it, read off its `onRequestClose`.
 *
 * Escape is delivered the way a browser delivers it: to the focused element inside the modal,
 * bubbling. jsdom builds the same event path, window included, so the menu's capturing window
 * listener sees the key first, as it does in a browser. Every case proves that the inner layer
 * really handled the key — the menu's own `onClose` ran and the menu is gone, the list is closed —
 * before it asserts on the modal, so a green can never come from a listener that never ran. Then
 * it presses Escape once more: with the layer gone, that one is the modal's, which proves the layer
 * let go of the key instead of swallowing every Escape after it.
 *
 * The controls guard the other direction and are green before and after the cure: an Escape that no
 * layer consumed — nothing open, a select whose list is closed — still closes the modal. The inline
 * search box is a guard as well: it already stops its own keydowns, so its Escape is safe today.
 *
 * Assertions read the `onRequestClose` and menu `onClose` spies, `aria-expanded`, and the listbox
 * inside each select's own container — never a class or a translated string.
 */
import {afterEach, beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';
import {cleanup, fireEvent, render, screen, setupI18n, waitFor, within} from '$test/component';
import Harness from '$test/harness/ModalEscapeLayersHarness.svelte';

// ModalBase manages focus only in a browser: there it focuses its backdrop as it opens, which is the
// state a user meets and the one every test here starts from.
vi.mock('$app/environment', () => ({browser: true, dev: true, building: false, version: 'test'}));

/** Both select layouts of the harness, as [label, testId]. */
const LAYOUTS: [string, string][] = [
    ['search box in the list', 'esc-select'],
    ['search inline in the trigger', 'esc-inline'],
];

beforeAll(async () => {
    await setupI18n();
});

beforeEach(() => {
    // Unmounting the modal restores the page scroll, and jsdom implements no scrolling. The focus trap
    // stays off, as in TransactionBulkModal, so ModalBase never measures a focusable element and
    // `getClientRects` needs no stub.
    vi.spyOn(window, 'scrollTo').mockImplementation(() => {});
});

afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
});

/** The harness, open, once the modal holds the focus. */
async function mountModal() {
    const onRequestClose = vi.fn().mockName('onRequestClose');
    const onMenuClose = vi.fn().mockName('onMenuClose');
    render(Harness, {onRequestClose, onMenuClose});
    const modal = screen.getByTestId('esc-modal');
    // ModalBase focuses its backdrop on the next animation frame, and a focus placed before that frame
    // would be stolen by it: the barrier is that state, not a delay.
    await waitFor(() => expect(modal, 'premise: the open modal takes the focus').toHaveFocus());
    return {modal, onRequestClose, onMenuClose};
}

/**
 * A select of the harness: its container — the barrier that keeps a lookup out of the other
 * select's list, since every SearchSelect shares the option testids — and its trigger.
 */
function searchSelect(testId: string) {
    const root = screen.getByTestId(testId);
    return {root, trigger: within(root).getByTestId(`${testId}-trigger`)};
}

/** Open means usable: the trigger says so, and this select's own list is there. */
function expectListOpen(root: HTMLElement, trigger: HTMLElement, why: string) {
    expect(trigger, why).toHaveAttribute('aria-expanded', 'true');
    expect(within(root).queryByRole('listbox'), why).not.toBeNull();
}

/** Closed means gone: the trigger says so, and this select has no list at all. */
function expectListClosed(root: HTMLElement, trigger: HTMLElement, why: string) {
    expect(trigger, why).toHaveAttribute('aria-expanded', 'false');
    expect(within(root).queryByRole('listbox'), why).toBeNull();
}

/** Opens a select with a click on its trigger, and returns once the select has handed the focus to its own search box. */
async function openList(testId: string) {
    const {root, trigger} = searchSelect(testId);
    await fireEvent.click(trigger);
    expectListOpen(root, trigger, 'premise: a click on the trigger opens the list');
    const search = within(root).getByTestId(`${testId}-search`);
    await waitFor(() => expect(search, 'premise: the open select focuses its search box').toHaveFocus());
    return {root, trigger, search};
}

/**
 * One Escape, the way a browser delivers it: to the focused element, bubbling from there. It checks
 * first that the focus is where the test means it to be, and that it is inside the modal.
 */
async function pressEscape(modal: HTMLElement, focused: HTMLElement) {
    expect(focused, 'premise: the Escape goes to the element holding the focus').toHaveFocus();
    expect(modal.contains(focused), 'premise: the focused element is inside the modal').toBe(true);
    await fireEvent.keyDown(document.activeElement as HTMLElement, {key: 'Escape'});
}

describe('ModalBase — one Escape closes the top layer only', () => {
    it('row menu: Escape closes the menu, not the modal, and the next Escape closes the modal', async () => {
        const {modal, onRequestClose, onMenuClose} = await mountModal();
        const opener = screen.getByTestId('esc-menu-opener');
        // The ⋮ path: the button that opens the menu holds the focus, as a click leaves it in a browser
        // (jsdom moves no focus on a click).
        opener.focus();
        await fireEvent.click(opener);
        expect(screen.queryByTestId('context-menu'), 'premise: the button opens the row menu').not.toBeNull();
        expect(onMenuClose, 'premise: nothing has closed the menu yet').not.toHaveBeenCalled();

        await pressEscape(modal, opener);

        // The menu's own listener ran — the capturing one on window, the first to see the key.
        expect(onMenuClose, 'the Escape must close the row menu').toHaveBeenCalledTimes(1);
        expect(screen.queryByTestId('context-menu'), 'the Escape must close the row menu').toBeNull();
        expect(onRequestClose, 'one Escape on an open row menu must close the menu only, not the modal under it').not.toHaveBeenCalled();

        // The menu took its listener with it: the next Escape is the modal's.
        await pressEscape(modal, opener);
        expect(onRequestClose, 'with the menu closed, the next Escape must close the modal').toHaveBeenCalledTimes(1);
        expect(onMenuClose, 'a menu already closed must not be closed again').toHaveBeenCalledTimes(1);
    });

    it('select, search box in the list: Escape there closes the list, not the modal, and the next Escape closes the modal', async () => {
        const {modal, onRequestClose} = await mountModal();
        const {root, trigger, search} = await openList('esc-select');

        await pressEscape(modal, search);

        expectListClosed(root, trigger, 'the Escape must close the list');
        expect(onRequestClose, 'one Escape in an open select must close its list only, not the modal under it').not.toHaveBeenCalled();

        // Closing hands the focus back to the trigger, and a closed select consumes no Escape: the next one is the modal's.
        await pressEscape(modal, trigger);
        expect(onRequestClose, 'with the list closed, the next Escape must close the modal').toHaveBeenCalledTimes(1);
    });

    it('select, search inline in the trigger: Escape on the trigger of the open list closes the list, not the modal, and the next Escape closes the modal', async () => {
        const {modal, onRequestClose} = await mountModal();
        const {root, trigger} = await openList('esc-inline');
        // Shift+Tab out of the inline search box lands on the trigger that holds it, and nothing closes the
        // list on the way. jsdom navigates no Tab, so the test puts the focus where Shift+Tab leaves it.
        trigger.focus();
        expectListOpen(root, trigger, 'premise: the list stays open with the focus on its trigger');

        await pressEscape(modal, trigger);

        expectListClosed(root, trigger, 'the Escape must close the list');
        expect(onRequestClose, 'one Escape on the trigger of an open select must close its list only, not the modal under it').not.toHaveBeenCalled();

        await pressEscape(modal, trigger);
        expect(onRequestClose, 'with the list closed, the next Escape must close the modal').toHaveBeenCalledTimes(1);
    });

    it('guard — select, search inline in the trigger: Escape in the inline search box closes the list, not the modal (safe today: the box stops its own keydowns)', async () => {
        const {modal, onRequestClose} = await mountModal();
        const {root, trigger, search} = await openList('esc-inline');

        await pressEscape(modal, search);

        expectListClosed(root, trigger, 'the Escape must close the list');
        expect(onRequestClose, 'one Escape in the inline search box must close the list only, not the modal under it').not.toHaveBeenCalled();

        await pressEscape(modal, trigger);
        expect(onRequestClose, 'with the list closed, the next Escape must close the modal').toHaveBeenCalledTimes(1);
    });
});

describe('ModalBase — an Escape that no layer consumed still closes the modal (controls)', () => {
    it('nothing open: Escape on a button inside the modal requests the close, once', async () => {
        const {modal, onRequestClose} = await mountModal();
        const button = screen.getByTestId('esc-menu-opener');
        button.focus();

        await pressEscape(modal, button);

        expect(onRequestClose, 'with nothing open over the modal, the Escape must close it').toHaveBeenCalledTimes(1);
    });

    it.each(LAYOUTS)('select with its list closed (%s): Escape on its trigger requests the close, once', async (_layout, testId) => {
        const {modal, onRequestClose} = await mountModal();
        const {root, trigger} = searchSelect(testId);
        trigger.focus();
        expectListClosed(root, trigger, 'premise: the list is closed');

        await pressEscape(modal, trigger);

        expect(onRequestClose, 'a select with its list closed consumed nothing, so the Escape must close the modal').toHaveBeenCalledTimes(1);
    });
});
