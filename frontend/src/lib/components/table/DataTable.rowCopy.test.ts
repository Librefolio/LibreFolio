// @vitest-environment jsdom
/**
 * DataTable — «Copy cell» and «Copy row» of a finger's row menu (85 BTN-0, the developer's phone test).
 *
 * A long press on a row opens the row menu and never the text selection, so the copy lives in the menu:
 *   - only on a menu a finger opened (a `contextmenu` while a touch is active): the row actions first, then a
 *     separator, then «Copy cell» (only when the press was on a data cell), then «Copy row», last; a mouse right click
 *     and the ⋮ get no copy item;
 *   - the copied text is what the screen shows (`rowCopyText.ts`): a row is its data cells joined by tabs, and a value
 *     the privacy mode masks stays masked;
 *   - a copy publishes `table.cell.copied` / `table.row.copied` with `{chars}`, a refused write `table.copy.failed`
 *     with `{kind}` — read from the app's event ring (`window.__lf`), never from the toast text;
 *   - while a finger is on the table its body carries `dt-touching` (no text selection on rows), gone 100 ms after
 *     the finger lifts.
 * The clipboard is mocked: the subject is what is handed to it. Rows are addressed by `tr[data-row-id]`.
 */
import {afterEach, beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';
import {Pencil, Trash2} from 'lucide-svelte';
import {cleanup, fireEvent, render, screen, setupI18n, waitFor, within} from '$test/component';
import {setPrivacyEnabled} from '$lib/stores/app/privacyStore.svelte';
import {PRIVACY_PLACEHOLDER} from '$lib/utils/privacy/maskable';
import {formatCurrencyAmountPlain} from '$lib/utils/currency/currencyFormat';
import DataTable from './DataTable.svelte';
import type {ColumnDef, RowAction} from './types';

const clipboard = vi.hoisted(() => ({writeTextToClipboard: vi.fn<(text: string) => Promise<void>>()}));
vi.mock('$lib/utils/clipboard', async (importOriginal) => ({...(await importOriginal<object>()), writeTextToClipboard: clipboard.writeTextToClipboard}));

interface Row {
    id: string;
    name: string;
    value: number;
}

const ROWS: Row[] = [
    {id: 'r1', name: 'First asset', value: 1234.5},
    {id: 'r2', name: 'Second asset', value: 98.25},
];

const COLUMNS: ColumnDef<Row>[] = [
    {id: 'name', header: 'Name', type: 'text', cell: (r) => r.name, getValue: (r) => r.name},
    // The real formatter, wealth-sensitive: masked while the privacy mode is on.
    {id: 'value', header: 'Value', type: 'number', cell: (r) => formatCurrencyAmountPlain(r.value, 'EUR', {sensitivity: 'personal'}), getValue: (r) => r.value},
];

const ROW_ACTIONS: RowAction<Row>[] = [
    {id: 'edit', label: 'Edit', icon: Pencil, onClick: vi.fn(), testid: 'act-edit'},
    {id: 'delete', label: 'Delete', icon: Trash2, onClick: vi.fn(), testid: 'act-delete'},
];

interface AppEventLike {
    seq: number;
    name: string;
    detail?: Record<string, unknown>;
}

function appEvents(): {events: AppEventLike[]; seq: () => number} {
    return (window as unknown as {__lf: {events: AppEventLike[]; seq: () => number}}).__lf;
}

beforeAll(async () => {
    await setupI18n();
});

beforeEach(() => {
    clipboard.writeTextToClipboard.mockReset();
    clipboard.writeTextToClipboard.mockResolvedValue(undefined);
});

afterEach(() => {
    cleanup();
    setPrivacyEnabled(false);
});

function mount(key: string, props: Record<string, unknown> = {}) {
    render(DataTable, {
        data: ROWS,
        columns: COLUMNS as ColumnDef<unknown>[],
        getRowId: ((r: Row) => r.id) as (row: unknown) => string,
        storageKey: key,
        enableContextMenu: true,
        rowActions: ROW_ACTIONS as RowAction<unknown>[],
        ...props,
    });
}

function row(id: string): HTMLElement {
    const el = document.querySelector<HTMLElement>(`tbody tr[data-row-id="${id}"]`);
    if (!el) throw new Error(`row ${id} is not rendered`);
    return el;
}

function dataCell(id: string, columnId: string): HTMLElement {
    const el = row(id).querySelector<HTMLElement>(`td.td-data[data-column-id="${columnId}"]`) ?? [...row(id).querySelectorAll<HTMLElement>('td.td-data')][COLUMNS.findIndex((c) => c.id === columnId)];
    if (!el) throw new Error(`no ${columnId} data cell in ${id}`);
    return el;
}

/** The menu's entries in DOM order: each item's test id, a separator as `—`. */
function menuOrder(): string[] {
    return [...screen.getByTestId('context-menu').querySelectorAll('[role="menuitem"], hr')].map((el) => (el.tagName === 'HR' ? '—' : (el.getAttribute('data-testid') ?? '?')));
}

async function fingerMenu(target: HTMLElement) {
    await fireEvent.touchStart(target);
    await fireEvent.contextMenu(target, {clientX: 120, clientY: 300});
    expect(screen.getByTestId('context-menu')).toHaveAttribute('data-origin', 'finger');
}

async function eventAfter(since: number, name: string): Promise<AppEventLike> {
    let found: AppEventLike | undefined;
    await waitFor(() => {
        found = appEvents().events.find((event) => event.seq > since && event.name === name);
        expect(found, `the event ${name}`).toBeDefined();
    });
    return found!;
}

describe('DataTable — the copy items of a finger’s row menu', () => {
    it('a finger on a data cell: the row actions, a separator, copy-cell, copy-row last', async () => {
        mount('copy-order');
        await fingerMenu(dataCell('r1', 'name'));
        expect(menuOrder()).toEqual(['act-edit', 'act-delete', '—', 'context-menu-copy-cell', 'context-menu-copy-row']);
    });

    it('a mouse right click: no copy item', async () => {
        mount('copy-mouse');
        await fireEvent.contextMenu(dataCell('r1', 'name'), {clientX: 120, clientY: 300});
        const menu = screen.getByTestId('context-menu');
        expect(menu).toHaveAttribute('data-origin', 'pointer');
        expect(within(menu).getByTestId('act-edit')).toBeInTheDocument();
        expect(within(menu).queryByTestId('context-menu-copy-cell')).toBeNull();
        expect(within(menu).queryByTestId('context-menu-copy-row')).toBeNull();
    });

    it('the ⋮: no copy item', async () => {
        mount('copy-kebab');
        const kebab = screen.getByTestId('row-actions-r1');
        // jsdom measures every box as zero, and an anchored menu closes itself on a zero box: give the ⋮ a real one.
        kebab.getBoundingClientRect = () => ({x: 10, y: 10, left: 10, top: 10, right: 30, bottom: 30, width: 20, height: 20, toJSON: () => ({})});
        await fireEvent.click(kebab);
        const menu = screen.getByTestId('context-menu');
        expect(within(menu).getByTestId('act-edit')).toBeInTheDocument();
        expect(within(menu).queryByTestId('context-menu-copy-cell')).toBeNull();
        expect(within(menu).queryByTestId('context-menu-copy-row')).toBeNull();
    });

    it('a finger on a cell that is not a data cell (the selection cell): copy-row only', async () => {
        mount('copy-select-cell', {enableSelection: true});
        const selectCell = screen.getByTestId('dt-select-cell-r1');
        expect(selectCell.classList.contains('td-data'), 'barrier: the selection cell is not a data cell').toBe(false);
        await fingerMenu(selectCell);
        const order = menuOrder();
        expect(order).not.toContain('context-menu-copy-cell');
        expect(order.at(-1)).toBe('context-menu-copy-row');
    });

    it('copy-cell hands the clipboard the cell as shown and publishes table.cell.copied', async () => {
        mount('copy-cell-text');
        await fingerMenu(dataCell('r1', 'name'));
        const since = appEvents().seq();
        await fireEvent.click(screen.getByTestId('context-menu-copy-cell'));
        expect(clipboard.writeTextToClipboard).toHaveBeenCalledExactlyOnceWith('First asset');
        const event = await eventAfter(since, 'table.cell.copied');
        expect(event.detail).toEqual({chars: 'First asset'.length});
        await waitFor(() => expect(screen.queryByTestId('context-menu')).toBeNull());
    });

    it('copy-row hands the clipboard the data cells joined by tabs and publishes table.row.copied', async () => {
        mount('copy-row-text', {enableSelection: true});
        const expectedValue = dataCell('r2', 'value').textContent?.replace(/\s+/g, ' ').trim() ?? '';
        expect(expectedValue, 'barrier: the value cell shows something').not.toBe('');
        await fingerMenu(dataCell('r2', 'value'));
        const since = appEvents().seq();
        await fireEvent.click(screen.getByTestId('context-menu-copy-row'));
        const expected = `Second asset\t${expectedValue}`;
        expect(clipboard.writeTextToClipboard).toHaveBeenCalledExactlyOnceWith(expected);
        expect((await eventAfter(since, 'table.row.copied')).detail).toEqual({chars: expected.length});
    });

    it('a refused write publishes table.copy.failed with its kind', async () => {
        clipboard.writeTextToClipboard.mockRejectedValue(new Error('denied'));
        mount('copy-refused');
        await fingerMenu(dataCell('r1', 'name'));
        const since = appEvents().seq();
        await fireEvent.click(screen.getByTestId('context-menu-copy-row'));
        expect((await eventAfter(since, 'table.copy.failed')).detail).toEqual({kind: 'row'});
        expect(appEvents().events.some((event) => event.seq > since && event.name === 'table.row.copied')).toBe(false);
    });

    it('a write that throws at once publishes table.copy.failed too', async () => {
        clipboard.writeTextToClipboard.mockImplementation(() => {
            throw new Error('no clipboard');
        });
        mount('copy-throws');
        await fingerMenu(dataCell('r1', 'name'));
        const since = appEvents().seq();
        await fireEvent.click(screen.getByTestId('context-menu-copy-cell'));
        expect((await eventAfter(since, 'table.copy.failed')).detail).toEqual({kind: 'cell'});
    });

    it('with the privacy mode on, the copied value is the mask, never the number', async () => {
        setPrivacyEnabled(true);
        mount('copy-privacy');
        const shown = dataCell('r1', 'value').textContent ?? '';
        expect(shown, 'barrier: the cell shows the mask').toContain(PRIVACY_PLACEHOLDER);
        await fingerMenu(dataCell('r1', 'value'));
        await fireEvent.click(screen.getByTestId('context-menu-copy-cell'));
        const [copiedCell] = clipboard.writeTextToClipboard.mock.calls[0];
        expect(copiedCell).toContain(PRIVACY_PLACEHOLDER);
        expect(copiedCell).not.toMatch(/1[.,\s]?234/);

        await fingerMenu(dataCell('r1', 'name'));
        await fireEvent.click(screen.getByTestId('context-menu-copy-row'));
        const [copiedRow] = clipboard.writeTextToClipboard.mock.calls[1];
        expect(copiedRow.split('\t')).toEqual(['First asset', copiedCell]);
        expect(copiedRow).not.toMatch(/1[.,\s]?234/);
    });
});

describe('DataTable — no text selection on rows while a finger is on the table', () => {
    it('the body carries dt-touching from touchstart until 100 ms after touchend', async () => {
        mount('touching');
        const tbody = row('r1').closest('tbody')!;
        expect(tbody.classList.contains('dt-touching')).toBe(false);
        await fireEvent.touchStart(dataCell('r1', 'name'));
        expect(tbody.classList.contains('dt-touching')).toBe(true);
        await fireEvent.touchEnd(dataCell('r1', 'name'));
        expect(tbody.classList.contains('dt-touching'), 'still there right after the lift: a late contextmenu is a finger’s').toBe(true);
        await waitFor(() => expect(tbody.classList.contains('dt-touching')).toBe(false), {timeout: 1_000});
    });

    async function touchLeavesSelection(key: string, props: Record<string, unknown>, rowId = 'r1') {
        mount(key, props);
        const tbody = row(rowId).closest('tbody')!;
        await fireEvent.touchStart(dataCell(rowId, 'name'));
        expect(tbody.classList.contains('dt-touching'), 'a row with no menu keeps the browser’s text selection').toBe(false);
        await fireEvent.touchEnd(dataCell(rowId, 'name'));
    }

    it('a table without a row menu (enableContextMenu false) keeps the text selection', async () => {
        await touchLeavesSelection('touching-no-menu', {enableContextMenu: false});
    });

    it('a table without row actions keeps the text selection', async () => {
        await touchLeavesSelection('touching-no-actions', {rowActions: []});
    });

    it('a row whose actions are all hidden keeps the text selection; a row with a menu does not', async () => {
        const onlyFirst: RowAction<Row>[] = ROW_ACTIONS.map((action) => ({...action, visible: (r: Row) => r.id === 'r1'}));
        mount('touching-per-row', {rowActions: onlyFirst});
        const tbody = row('r1').closest('tbody')!;
        // Positive control: the row with a menu marks the touch.
        await fireEvent.touchStart(dataCell('r1', 'name'));
        expect(tbody.classList.contains('dt-touching')).toBe(true);
        await fireEvent.touchEnd(dataCell('r1', 'name'));
        await waitFor(() => expect(tbody.classList.contains('dt-touching')).toBe(false), {timeout: 1_000});

        await fireEvent.touchStart(dataCell('r2', 'name'));
        expect(tbody.classList.contains('dt-touching'), 'r2 has no visible action, so no menu').toBe(false);
        await fireEvent.touchEnd(dataCell('r2', 'name'));
    });
});

describe('DataTable — an item that would copy nothing is not offered', () => {
    const NOTE: ColumnDef<Row> = {id: 'note', header: 'Note', type: 'text', cell: () => '', getValue: () => ''};

    it('a cell with no text: no copy-cell, copy-row still there and last', async () => {
        mount('copy-empty-cell', {columns: [...COLUMNS, NOTE] as ColumnDef<unknown>[]});
        const empty = dataCell('r1', 'note');
        expect(empty.textContent?.trim(), 'barrier: the note cell is empty').toBe('');
        await fingerMenu(empty);
        const order = menuOrder();
        expect(order).not.toContain('context-menu-copy-cell');
        expect(order.at(-1)).toBe('context-menu-copy-row');
    });
});

describe('DataTable — copying an editable cell', () => {
    const TICKER: ColumnDef<Row> = {id: 'ticker', header: 'Ticker', type: 'text', cell: (r) => ({type: 'editable-text', value: `${r.id.toUpperCase()}-T`, onchange: vi.fn()}), getValue: (r) => r.id};

    it('copy-cell copies the field’s current value, and copy-row carries it in its place', async () => {
        mount('copy-editable', {columns: [...COLUMNS, TICKER] as ColumnDef<unknown>[]});
        const cell = dataCell('r1', 'ticker');
        const input = within(cell).getByTestId('cell-editable-text') as HTMLInputElement;
        expect(input.value, 'barrier: the field shows its value').toBe('R1-T');
        // What the user typed and has not committed yet: the screen shows it, so the copy does.
        input.value = 'TYPED';

        // The press is on the cell around the field: a press on the field itself keeps the browser's own menu (81 U15).
        await fingerMenu(cell);
        await fireEvent.click(screen.getByTestId('context-menu-copy-cell'));
        expect(clipboard.writeTextToClipboard).toHaveBeenLastCalledWith('TYPED');

        await fingerMenu(dataCell('r1', 'name'));
        await fireEvent.click(screen.getByTestId('context-menu-copy-row'));
        const [copiedRow] = clipboard.writeTextToClipboard.mock.calls.at(-1)!;
        expect(copiedRow.split('\t')[0]).toBe('First asset');
        expect(copiedRow.split('\t').at(-1)).toBe('TYPED');
    });
});
