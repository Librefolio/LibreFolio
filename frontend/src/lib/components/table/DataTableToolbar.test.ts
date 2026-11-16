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
