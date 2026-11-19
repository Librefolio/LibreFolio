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
 * The tooltip is asserted on the channel each variant uses today: the floating bar's `title` (its `aria-label` is the
 * label, the button's name), the inline bar's `Tooltip` (`tooltip-content`, opened by a click on its trigger, the
 * wrapper around the icon button). The texts are the test's own: nothing here is translated.
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

        it('a disabled action with a hint: the title is the hint, the name stays the label, the reason is published', () => {
            render(DataTableToolbar, {selectedCount: 3, bulkActions: [linkAction({disabled: true, hint: HINT, reason: REASON})], variant: 'floating'});

            const button = screen.getByTestId('toolbar-action-link-charges');
            expect(button).toBeDisabled();
            expect(button).toHaveAttribute('title', HINT);
            expect(button).toHaveAttribute('aria-label', LABEL);
            expect(button).toHaveAttribute('data-disabled-reason', REASON);
        });

        it('a hint given as a function is read like a string', () => {
            render(DataTableToolbar, {selectedCount: 3, bulkActions: [linkAction({disabled: true, hint: () => HINT, reason: REASON})], variant: 'floating'});

            expect(screen.getByTestId('toolbar-action-link-charges')).toHaveAttribute('title', HINT);
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

        it('a disabled action with a hint: the tooltip is the hint, the hint is not the name, the reason is published', async () => {
            render(DataTableToolbar, {selectedCount: 3, bulkActions: [linkAction({disabled: true, hint: () => HINT, reason: REASON})]});

            const button = screen.getByTestId('toolbar-action-link-charges');
            expect(button).toBeDisabled();
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
