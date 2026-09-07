// @vitest-environment jsdom
/**
 * DataEditor — component test (Vitest + jsdom).
 *
 * DataEditor is the status-tracking layer over a DataTable: every row carries a
 * status (original / edited / deleted / appended), and the ONE thing the editor
 * promises its parent is `onchange(dirtyRows)` — the rows whose status is no
 * longer 'original'. So these tests never read a colour or a counter label; they
 * drive a toolbar button, a cell, or a row-action menu item, and assert the
 * *payload the parent receives*. That payload is the contract.
 *
 * What is deliberately left to the E2E suite: the date cell's embedded
 * SingleDatePicker (handleDateChange) and CSV import (handleImport needs a
 * caller-supplied modal snippet). Both are integration seams better exercised in
 * the browser than reconstructed in jsdom; see the note at the foot of the file.
 */
import {beforeAll, describe, expect, it, vi} from 'vitest';
import {render, screen, fireEvent, waitFor, within} from '$test/component';
import DataEditor from './DataEditor.svelte';
import type {ColumnDef, DataRow} from './DataEditorTypes';

const COLS: ColumnDef[] = [{key: 'rate', label: 'Rate', type: 'number', editable: true, required: false, step: 0.5}];

/** A row in its loaded 'original' state unless overridden. rowId = date, as price rows use. */
function row(date: string, rate: number | null = 1, extra: Partial<DataRow> = {}): DataRow {
    return {rowId: date, date, status: 'original', originalStatus: 'original', values: {rate}, selected: false, ...extra};
}

function mount(rows: DataRow[] = []) {
    const onchange = vi.fn();
    const {container} = render(DataEditor, {props: {columns: COLS, rows, onchange}});
    return {onchange, container};
}

/** The last dirty-row set the editor pushed to its parent. */
function lastDirty(onchange: ReturnType<typeof vi.fn>): DataRow[] {
    return onchange.mock.calls.at(-1)?.[0] as DataRow[];
}

/** The editable number <input> of one specific row, scoped by the row's data-row-id. */
function rateInput(container: HTMLElement, rowId: string): HTMLInputElement {
    const el = container.querySelector<HTMLInputElement>(`tr[data-row-id="${rowId}"] input.cell-editable-number`);
    if (!el) throw new Error(`no editable rate input for row ${rowId}`);
    return el;
}

/** Open a row's action menu and click one action by its stable id (delete / revert).
 *  The menu is opened via the row's right-click affordance rather than the ⋮ button:
 *  both open the identical ContextMenu, but the ⋮ path positions against an anchor via
 *  requestAnimationFrame, which jsdom does not drive — the right-click path is anchorless
 *  and renders immediately. The action handler under test is the same either way. */
async function runRowAction(rowId: string, actionId: 'delete' | 'revert') {
    const tr = screen.getByTestId('data-editor-root').querySelector<HTMLElement>(`tr[data-row-id="${rowId}"]`);
    if (!tr) throw new Error(`no row ${rowId}`);
    await fireEvent.contextMenu(tr, {clientX: 10, clientY: 10});
    await fireEvent.click(await screen.findByTestId(`context-menu-action-${actionId}`));
}

beforeAll(async () => {
    const {setupI18n} = await import('$test/component');
    await setupI18n();
});

describe('DataEditor — adding a row publishes it as an appended dirty row', () => {
    it('on an empty editor, the new row carries today and status appended', async () => {
        vi.useFakeTimers();
        vi.setSystemTime(new Date('2024-06-14T12:00:00Z'));
        try {
            const {onchange} = mount([]);
            await fireEvent.click(screen.getByTestId('fx-data-add-row-btn'));
            const dirty = lastDirty(onchange);
            expect(dirty).toHaveLength(1);
            expect(dirty[0].status).toBe('appended');
            expect(dirty[0].date).toBe('2024-06-14');
        } finally {
            vi.useRealTimers();
        }
    });

    it('with existing rows, the new date is the day after the latest', async () => {
        vi.useFakeTimers();
        vi.setSystemTime(new Date('2024-06-14T12:00:00Z'));
        try {
            const {onchange} = mount([row('2024-06-10'), row('2024-06-11')]);
            await fireEvent.click(screen.getByTestId('fx-data-add-row-btn'));
            const appended = lastDirty(onchange).find((r) => r.status === 'appended');
            expect(appended?.date).toBe('2024-06-12');
        } finally {
            vi.useRealTimers();
        }
    });

    it('never proposes a future date: it caps at today and steps back to a free day', async () => {
        // The latest row IS today, so "the day after" would be tomorrow — forbidden. The editor
        // caps at today, finds it taken, and walks back to the first free day (yesterday).
        vi.useFakeTimers();
        vi.setSystemTime(new Date('2024-06-14T12:00:00Z'));
        try {
            const {onchange} = mount([row('2024-06-14')]);
            await fireEvent.click(screen.getByTestId('fx-data-add-row-btn'));
            const appended = lastDirty(onchange).find((r) => r.status === 'appended');
            expect(appended?.date).toBe('2024-06-13');
        } finally {
            vi.useRealTimers();
        }
    });
});

describe('DataEditor — editing a cell flips the row to edited, and back', () => {
    it('a changed value publishes the row as edited with the new number', async () => {
        const {onchange, container} = mount([row('2024-06-10', 1.1)]);
        await fireEvent.input(rateInput(container, '2024-06-10'), {target: {value: '2.5'}});
        await waitFor(() => expect(onchange).toHaveBeenCalled());
        const dirty = lastDirty(onchange);
        expect(dirty).toHaveLength(1);
        expect(dirty[0].status).toBe('edited');
        expect(dirty[0].values.rate).toBe(2.5);
    });

    it('editing a value back to its original clears the dirty flag', async () => {
        const {onchange, container} = mount([row('2024-06-10', 1.1)]);
        const input = rateInput(container, '2024-06-10');
        await fireEvent.input(input, {target: {value: '2.5'}});
        await waitFor(() => expect(lastDirty(onchange)).toHaveLength(1));
        await fireEvent.input(input, {target: {value: '1.1'}});
        // Restoring the original value returns the row to 'original', so nothing is dirty.
        await waitFor(() => expect(lastDirty(onchange)).toHaveLength(0));
    });
});

describe('DataEditor — the delete / revert lifecycle through the row menu', () => {
    it('deleting an original row publishes it as deleted', async () => {
        const {onchange} = mount([row('2024-06-10')]);
        await runRowAction('2024-06-10', 'delete');
        const dirty = lastDirty(onchange);
        expect(dirty).toHaveLength(1);
        expect(dirty[0].status).toBe('deleted');
    });

    it('reverting a deleted original row restores it and clears the dirty set', async () => {
        const {onchange} = mount([row('2024-06-10')]);
        await runRowAction('2024-06-10', 'delete');
        await waitFor(() => expect(lastDirty(onchange)).toHaveLength(1));
        await runRowAction('2024-06-10', 'revert');
        await waitFor(() => expect(lastDirty(onchange)).toHaveLength(0));
    });

    it('reverting an appended row removes it entirely', async () => {
        const appended = row('2024-06-20', 1, {status: 'appended', originalStatus: 'appended'});
        const {onchange} = mount([row('2024-06-10'), appended]);
        await runRowAction('2024-06-20', 'revert');
        // The appended row is dropped, not merely reset — so it is gone from the table…
        await waitFor(() => expect(screen.queryByTestId('row-actions-2024-06-20')).toBeNull());
        // …and the last emission contains no appended row.
        expect(lastDirty(onchange).some((r) => r.date === '2024-06-20')).toBe(false);
    });
});

describe('DataEditor — bulk-selecting rows and deleting them in one action', () => {
    it('checking two rows then hitting bulk-delete publishes both as deleted', async () => {
        const {onchange, container} = mount([row('2024-06-10'), row('2024-06-11'), row('2024-06-12')]);
        // Selecting rows is a DataTable concern surfaced back through onSelectionChange; the
        // bulk-delete affordance only appears once something is selected.
        await fireEvent.click(container.querySelector<HTMLElement>('[data-testid="dt-row-checkbox-2024-06-10"]')!);
        await fireEvent.click(container.querySelector<HTMLElement>('[data-testid="dt-row-checkbox-2024-06-11"]')!);
        const bulkDelete = await screen.findByTestId('data-editor-bulk-delete');
        await fireEvent.click(bulkDelete);
        await waitFor(() => expect(onchange).toHaveBeenCalled());
        const dirty = lastDirty(onchange);
        expect(dirty.map((r) => r.date).sort()).toEqual(['2024-06-10', '2024-06-11']);
        expect(dirty.every((r) => r.status === 'deleted')).toBe(true);
    });
});

describe('DataEditor — the stale toggle hides backfilled rows without emitting', () => {
    it('flipping the toggle drops stale rows from the table but publishes nothing', async () => {
        const {onchange, container} = mount([row('2024-06-10'), row('2024-06-01', 1, {staleDays: 5})]);
        // The stale row is present, and the toggle only appears because a stale row exists.
        expect(container.querySelector('tr[data-row-id="2024-06-01"]')).not.toBeNull();
        const toggle = within(screen.getByTestId('data-editor-stale-toggle')).getByRole('switch');
        await fireEvent.click(toggle);
        await waitFor(() => expect(container.querySelector('tr[data-row-id="2024-06-01"]')).toBeNull());
        expect(container.querySelector('tr[data-row-id="2024-06-10"]')).not.toBeNull(); // fresh row stays
        expect(onchange).not.toHaveBeenCalled(); // a view filter is not an edit
    });
});
