// @vitest-environment jsdom
/**
 * DataTableToolbar — the selection bar, in its two variants (lane 65 UX, U8). Vitest + jsdom.
 *
 * Contract.
 * - `variant="inline"` (the default: the bar inside a modal, as it always was) renders where it is placed and draws the
 *   actions as icons.
 * - `variant="floating"` (the pages) is a `role="toolbar"` fixed at the bottom of the content: it exists only while at least one
 *   row is selected, shows the words of the actions (`toolbar-action-<id>-label`, the short label when an action has one),
 *   keeps a gap before the destructive action, and reserves room at the bottom of the page (`--lf-selbar-space` on the
 *   root element) so the last row is never hidden behind it.
 * - In both: `selection-toolbar` carries `data-selected-count`, the count button (`selection-toolbar-clear`) clears the
 *   selection, an action calls its `onClick`.
 * - `Esc` deselects only while the focus is inside the floating bar.
 * - No assertion reads a translated text.
 */
import {afterEach, beforeAll, describe, expect, it, vi} from 'vitest';
import {Pencil, Trash2} from 'lucide-svelte';
import {fireEvent, render, screen, setupI18n} from '$test/component';
import DataTableToolbar from './DataTableToolbar.svelte';

beforeAll(async () => {
    await setupI18n();
});

afterEach(() => {
    document.documentElement.style.removeProperty('--lf-selbar-space');
});

function actions() {
    const edit = vi.fn();
    const remove = vi.fn();
    return {
        edit,
        remove,
        list: [
            {id: 'edit', icon: Pencil, label: 'Edit selected (3)', shortLabel: 'Edit', primary: true, onClick: edit},
            {id: 'delete', icon: Trash2, label: 'Delete', variant: 'danger' as const, onClick: remove},
        ],
    };
}

describe('variant floating', () => {
    it('is a labelled toolbar that exists only with a selection', async () => {
        const {list} = actions();
        const view = render(DataTableToolbar, {selectedCount: 0, bulkActions: list, variant: 'floating'});
        expect(screen.queryByTestId('selection-toolbar')).toBeNull();

        await view.rerender({selectedCount: 3, bulkActions: list, variant: 'floating'});
        const bar = screen.getByTestId('selection-toolbar');
        expect(bar).toHaveAttribute('role', 'toolbar');
        expect(bar).toHaveAttribute('aria-label');
        expect(bar).toHaveAttribute('data-variant', 'floating');
        expect(bar).toHaveAttribute('data-selected-count', '3');

        await view.rerender({selectedCount: 0, bulkActions: list, variant: 'floating'});
        expect(screen.queryByTestId('selection-toolbar')).toBeNull();
    });

    it('shows the words of the actions, the short one where there is one, and the primary and destructive ones marked', () => {
        const {list} = actions();
        render(DataTableToolbar, {selectedCount: 3, bulkActions: list, variant: 'floating'});
        expect(screen.getByTestId('toolbar-action-edit-label')).toHaveTextContent('Edit');
        expect(screen.getByTestId('toolbar-action-edit-label')).not.toHaveTextContent('selected');
        expect(screen.getByTestId('toolbar-action-delete-label')).toHaveTextContent('Delete');
        expect(screen.getByTestId('toolbar-action-edit')).toHaveAttribute('data-primary', 'true');
        expect(screen.getByTestId('toolbar-action-delete')).toHaveAttribute('data-danger', 'true');
        // The full label stays the name of the button for the pointer and the readers.
        expect(screen.getByTestId('toolbar-action-edit')).toHaveAttribute('aria-label', 'Edit selected (3)');
    });

    it('reserves room at the bottom of the page while it shows, and gives it back', async () => {
        const {list} = actions();
        const view = render(DataTableToolbar, {selectedCount: 2, bulkActions: list, variant: 'floating'});
        expect(document.documentElement.style.getPropertyValue('--lf-selbar-space')).not.toBe('');
        await view.rerender({selectedCount: 0, bulkActions: list, variant: 'floating'});
        expect(document.documentElement.style.getPropertyValue('--lf-selbar-space')).toBe('');
    });

    it('the count button clears the selection and an action calls its handler', async () => {
        const {list, edit} = actions();
        const onClearSelection = vi.fn();
        render(DataTableToolbar, {selectedCount: 3, bulkActions: list, variant: 'floating', onClearSelection});
        await fireEvent.click(screen.getByTestId('toolbar-action-edit'));
        expect(edit).toHaveBeenCalledTimes(1);
        await fireEvent.click(screen.getByTestId('selection-toolbar-clear'));
        expect(onClearSelection).toHaveBeenCalledTimes(1);
    });

    it('Esc deselects only while the focus is inside the bar', async () => {
        const {list} = actions();
        const onClearSelection = vi.fn();
        render(DataTableToolbar, {selectedCount: 3, bulkActions: list, variant: 'floating', onClearSelection});

        await fireEvent.keyDown(document.body, {key: 'Escape'});
        expect(onClearSelection).not.toHaveBeenCalled();

        await fireEvent.keyDown(screen.getByTestId('toolbar-action-edit'), {key: 'Escape'});
        expect(onClearSelection).toHaveBeenCalledTimes(1);
    });
});

describe('variant inline (the default)', () => {
    it('keeps the bar as it was: in place, icons only, nothing reserved at the bottom of the page', async () => {
        const {list, remove} = actions();
        const onClearSelection = vi.fn();
        render(DataTableToolbar, {selectedCount: 3, bulkActions: list, onClearSelection});
        const bar = screen.getByTestId('selection-toolbar');
        expect(bar).toHaveAttribute('data-variant', 'inline');
        expect(bar).toHaveAttribute('data-selected-count', '3');
        expect(bar).not.toHaveAttribute('role', 'toolbar');
        expect(screen.queryByTestId('toolbar-action-edit-label')).toBeNull();
        expect(document.documentElement.style.getPropertyValue('--lf-selbar-space')).toBe('');

        await fireEvent.click(screen.getByTestId('toolbar-action-delete'));
        expect(remove).toHaveBeenCalledTimes(1);
        await fireEvent.click(screen.getByTestId('selection-toolbar-clear'));
        expect(onClearSelection).toHaveBeenCalledTimes(1);
    });

    it('Esc does nothing in the inline bar', async () => {
        const {list} = actions();
        const onClearSelection = vi.fn();
        render(DataTableToolbar, {selectedCount: 3, bulkActions: list, onClearSelection});
        await fireEvent.keyDown(screen.getByTestId('toolbar-action-edit'), {key: 'Escape'});
        expect(onClearSelection).not.toHaveBeenCalled();
    });
});

// ---------------------------------------------------------------------------
// 66 F6 — the reason of a disabled action: `hint` (its tooltip) and `reason` (`data-disabled-reason`)
// ---------------------------------------------------------------------------

/**
 * An action may carry `hint?: string | (() => string)` — what its tooltip says while it is disabled, instead of the label —
 * and `reason?: string`, published as `data-disabled-reason` on `toolbar-action-<id>` while it is disabled. Both are
 * optional and additive: an action without them renders exactly as before (the shared bar of every other page).
 *
 * The tooltip is asserted on the channel each case uses: an action that is not «disabled with a hint» keeps the floating
 * bar's `title` (its `aria-label` is the label, the button's name) and the inline bar's `Tooltip` (`tooltip-content`,
 * opened by a click on its trigger, the wrapper around the icon button). A disabled action with a hint shows the hint in
 * the shared `Tooltip` in both variants, opened by a click on the button itself, and has no native `title` (66 F7: the
 * block below pins that contract). The texts are the test's own: nothing here is translated.
 */
describe('hint and reason of an action (66 F6)', () => {
    const LABEL = 'Link the charges';
    const HINT = 'The charges are on another broker';
    const REASON = 'brokerMismatch';

    function linkAction(extra: Record<string, unknown>) {
        return {id: 'link-charges', icon: Pencil, label: LABEL, onClick: vi.fn(), ...extra};
    }

    /** The text of the inline bar's tooltip for an action: a click on its trigger opens it. */
    async function inlineTooltipText(id: string): Promise<string> {
        const trigger = screen.getByTestId(`toolbar-action-${id}`).parentElement;
        if (!trigger) throw new Error(`toolbar-action-${id} has no tooltip trigger around it`);
        await fireEvent.click(trigger);
        return (await screen.findByTestId('tooltip-content')).textContent?.trim() ?? '';
    }

    describe('variant floating', () => {
        it('backward compatibility: an action without hint or reason has its label as title and name, enabled or disabled, and no data-disabled-reason', () => {
            const {list} = actions();
            render(DataTableToolbar, {selectedCount: 3, bulkActions: [...list, linkAction({disabled: true})], variant: 'floating'});

            for (const [id, label] of [
                ['edit', 'Edit selected (3)'],
                ['delete', 'Delete'],
                ['link-charges', LABEL],
            ]) {
                const button = screen.getByTestId(`toolbar-action-${id}`);
                expect(button, `${id}: title`).toHaveAttribute('title', label);
                expect(button, `${id}: name`).toHaveAttribute('aria-label', label);
                expect(button, `${id}: no reason`).not.toHaveAttribute('data-disabled-reason');
            }
        });

        // 66 F7: was «the title is the hint» on a natively disabled button; the hint now goes through the shared Tooltip.
        it('a disabled action with a hint: aria-disabled, the name stays the label, no title, the reason is published', () => {
            render(DataTableToolbar, {selectedCount: 3, bulkActions: [linkAction({disabled: true, hint: HINT, reason: REASON})], variant: 'floating'});

            const button = screen.getByTestId('toolbar-action-link-charges');
            expect(button).toHaveAttribute('aria-disabled', 'true');
            expect(button).not.toHaveAttribute('disabled');
            expect(button).not.toHaveAttribute('title');
            expect(button).toHaveAttribute('aria-label', LABEL);
            expect(button).toHaveAttribute('data-disabled-reason', REASON);
        });

        it('a hint given as a function is read like a string', async () => {
            render(DataTableToolbar, {selectedCount: 3, bulkActions: [linkAction({disabled: true, hint: () => HINT, reason: REASON})], variant: 'floating'});

            await fireEvent.click(screen.getByTestId('toolbar-action-link-charges'));
            expect((await screen.findByTestId('tooltip-content')).textContent?.trim()).toBe(HINT);
        });

        it('an enabled action with a hint: the hint is not shown, the title is the label, no data-disabled-reason', () => {
            render(DataTableToolbar, {selectedCount: 3, bulkActions: [linkAction({disabled: false, hint: HINT, reason: REASON})], variant: 'floating'});

            const button = screen.getByTestId('toolbar-action-link-charges');
            expect(button).toBeEnabled();
            expect(button).toHaveAttribute('title', LABEL);
            expect(button).toHaveAttribute('aria-label', LABEL);
            expect(button).not.toHaveAttribute('data-disabled-reason');
        });
    });

    describe('variant inline', () => {
        it('backward compatibility: an action without hint or reason has its label as tooltip, no title, no data-disabled-reason', async () => {
            render(DataTableToolbar, {selectedCount: 3, bulkActions: [linkAction({disabled: true})]});

            const button = screen.getByTestId('toolbar-action-link-charges');
            expect(button).not.toHaveAttribute('title');
            expect(button).not.toHaveAttribute('data-disabled-reason');
            expect(await inlineTooltipText('link-charges')).toBe(LABEL);
        });

        it('backward compatibility: an enabled action without hint has its label as tooltip', async () => {
            const {list} = actions();
            render(DataTableToolbar, {selectedCount: 3, bulkActions: list});

            expect(screen.getByTestId('toolbar-action-delete')).not.toHaveAttribute('data-disabled-reason');
            expect(await inlineTooltipText('delete')).toBe('Delete');
        });

        // 66 F7: was `toBeDisabled()` (native `disabled`); a disabled action with a hint is now aria-disabled.
        it('a disabled action with a hint: the tooltip is the hint, the hint is not the name, the reason is published', async () => {
            render(DataTableToolbar, {selectedCount: 3, bulkActions: [linkAction({disabled: true, hint: () => HINT, reason: REASON})]});

            const button = screen.getByTestId('toolbar-action-link-charges');
            expect(button).toHaveAttribute('aria-disabled', 'true');
            expect(button).not.toHaveAttribute('disabled');
            expect(button).toHaveAttribute('data-disabled-reason', REASON);
            expect([null, LABEL], 'the name, if any, stays the label').toContain(button.getAttribute('aria-label'));
            expect(await inlineTooltipText('link-charges')).toBe(HINT);
        });

        it('an enabled action with a hint: the tooltip is the label, no data-disabled-reason', async () => {
            render(DataTableToolbar, {selectedCount: 3, bulkActions: [linkAction({disabled: false, hint: HINT, reason: REASON})]});

            const button = screen.getByTestId('toolbar-action-link-charges');
            expect(button).toBeEnabled();
            expect(button).not.toHaveAttribute('data-disabled-reason');
            expect(await inlineTooltipText('link-charges')).toBe(LABEL);
        });
    });
});

// ---------------------------------------------------------------------------
// 66 F7 — a disabled action with a reason stays reachable: aria-disabled, the shared Tooltip, no action
// ---------------------------------------------------------------------------

/**
 * A disabled action with a non-empty `hint`, in both variants:
 *  - the button is `aria-disabled="true"` and has no native `disabled` — a natively disabled button takes no focus and no
 *    click, so its reason would be out of reach on touch and from the keyboard (precedent: CorrelationHeatmap's
 *    unavailable orderings);
 *  - it sits in the shared `Tooltip` (`interactiveChild`), whose text is the hint: a click (or a tap) on the button opens
 *    it, and the action's `onClick` is NOT called;
 *  - Enter and Space on the focused button do not call `onClick` either;
 *  - `data-disabled-reason` is published as before; in the floating bar the name (`aria-label`) stays the label and there
 *    is no native `title` any more (the Tooltip replaces it).
 * Unchanged: a disabled action without a hint (or with an empty one) keeps the native `disabled`; an enabled action has
 * neither, runs its `onClick` on a click and ignores its hint.
 *
 * jsdom never turns a keydown into a click (a browser does, for Enter and Space on a focused button), so here the click
 * stands for the keyboard activation; the key events are a guard against a keydown handler that would run the action.
 * The real keyboard path is proved in the browser by `e2e/transactions/tx-charges-link-delete.spec.ts`.
 */
describe('a disabled action with a hint stays reachable (66 F7)', () => {
    const LABEL = 'Link the charges';
    const HINT = 'The charges are on another broker';
    const REASON = 'brokerMismatch';
    const ID = 'link-charges';

    function mount(floating: boolean, extra: Record<string, unknown>) {
        const onClick = vi.fn();
        render(DataTableToolbar, {
            selectedCount: 3,
            bulkActions: [{id: ID, icon: Pencil, label: LABEL, onClick, ...extra}],
            ...(floating ? {variant: 'floating' as const} : {}),
        });
        return {onClick, button: screen.getByTestId(`toolbar-action-${ID}`)};
    }

    /** The texts of the tooltips open right now (portaled to the body). */
    function openTooltipTexts(): string[] {
        return screen.queryAllByRole('tooltip').map((node) => node.textContent?.trim() ?? '');
    }

    for (const floating of [true, false]) {
        const variant = floating ? 'floating' : 'inline';

        describe(`variant ${variant}`, () => {
            it.each([
                {form: 'string', hint: HINT},
                {form: 'function', hint: () => HINT},
            ])('is aria-disabled, not natively disabled, focusable, and keeps its reason and name (hint as a $form)', ({hint}) => {
                const {button} = mount(floating, {disabled: true, hint, reason: REASON});

                expect(button).toHaveAttribute('aria-disabled', 'true');
                expect(button, 'a natively disabled button takes no focus and no click').not.toHaveAttribute('disabled');
                expect(button.tabIndex, 'the button is taken out of the tab order').not.toBe(-1);
                button.focus();
                expect(document.activeElement, 'the button cannot take the keyboard focus').toBe(button);
                expect(button).toHaveAttribute('data-disabled-reason', REASON);
                expect(button.getAttribute('title'), 'the hint is still a native title').not.toBe(HINT);
                if (floating) {
                    expect(button, 'the floating bar still has a native title: the Tooltip replaces it').not.toHaveAttribute('title');
                    expect(button).toHaveAttribute('aria-label', LABEL);
                } else {
                    expect([null, LABEL], 'the name, if any, stays the label').toContain(button.getAttribute('aria-label'));
                }
            });

            it.each([
                {form: 'string', hint: HINT},
                {form: 'function', hint: () => HINT},
            ])('a click on the button opens the shared Tooltip with the hint and does not run the action (hint as a $form)', async ({hint}) => {
                const {button, onClick} = mount(floating, {disabled: true, hint, reason: REASON});

                await fireEvent.click(button);
                const tooltip = await screen.findByRole('tooltip');
                expect(tooltip).toHaveAttribute('data-testid', 'tooltip-content');
                expect(tooltip.textContent?.trim()).toBe(HINT);
                expect(onClick, 'a click on a disabled action ran it').not.toHaveBeenCalled();
            });

            // A finger: touchstart and touchend on the button (they bubble to the Tooltip's wrapper, which opens and pins on
            // touchstart), then the click a browser derives from the tap. That click must neither close the reason nor run
            // the action.
            it('a tap (touchstart, touchend, then the derived click) opens the shared Tooltip with the hint and does not run the action', async () => {
                const {button, onClick} = mount(floating, {disabled: true, hint: HINT, reason: REASON});

                await fireEvent.touchStart(button);
                await fireEvent.touchEnd(button);
                expect(openTooltipTexts(), 'the touch did not open the reason').toEqual([HINT]);
                await fireEvent.click(button);
                const tooltip = await screen.findByRole('tooltip');
                expect(tooltip).toHaveAttribute('data-testid', 'tooltip-content');
                expect(openTooltipTexts(), 'the click derived from the tap closed the reason').toEqual([HINT]);
                expect(onClick, 'a tap on a disabled action ran it').not.toHaveBeenCalled();
            });

            it('Enter and Space on the focused button do not run the action', async () => {
                const {button, onClick} = mount(floating, {disabled: true, hint: HINT, reason: REASON});

                button.focus();
                expect(document.activeElement, 'the button cannot take the keyboard focus').toBe(button);
                for (const key of ['Enter', ' ']) {
                    await fireEvent.keyDown(button, {key});
                    await fireEvent.keyUp(button, {key});
                }
                expect(onClick, 'a key on a disabled action ran it').not.toHaveBeenCalled();
            });

            it.each([
                {form: 'no hint', extra: {}},
                {form: 'an empty hint', extra: {hint: ''}},
                {form: 'an empty hint function', extra: {hint: () => ''}},
            ])('unchanged: a disabled action with $form keeps the native disabled, not aria-disabled', ({extra}) => {
                const {button} = mount(floating, {disabled: true, reason: REASON, ...extra});

                // No click here: a browser dispatches no click to a natively disabled button, jsdom does (and Svelte's
                // delegated handler runs), so a click would test jsdom, not the bar.
                expect(button).toBeDisabled();
                expect(button).not.toHaveAttribute('aria-disabled');
            });

            it.each([
                {form: 'without a hint', extra: {}},
                {form: 'with a hint', extra: {hint: HINT, reason: REASON}},
            ])('unchanged: an enabled action $form is neither disabled nor aria-disabled, runs on a click and never shows the hint', async ({extra}) => {
                const {button, onClick} = mount(floating, {disabled: false, ...extra});

                expect(button).toBeEnabled();
                expect(button).not.toHaveAttribute('aria-disabled');
                expect(button).not.toHaveAttribute('data-disabled-reason');
                await fireEvent.click(button);
                expect(onClick).toHaveBeenCalledTimes(1);
                expect(button.getAttribute('title')).not.toBe(HINT);
                expect(openTooltipTexts()).not.toContain(HINT);
            });
        });
    }
});
