// @vitest-environment jsdom
/**
 * DataTable — a finger on a control of a row (85 D6).
 *
 * A long press on a row selects it (`enableTouchSelection`). A long press on a standard button inside the row shows the
 * button's name instead, so the row must leave that gesture alone:
 *   - `handleTouchStart` arms no selection timer when the finger is on a standard button (`ROW_TOUCH_CONTROLS`,
 *     `.lf-btn`): 500 ms on the button select nothing, 500 ms on a cell of the same table still select the row (the
 *     positive control);
 *   - a hand-written `<button>` has no long press of its own yet, so 500 ms on it still select the row, as before;
 *   - the row's `contextmenu` (Android's long press) is cancelled and opens no row menu while a touch is active and the
 *     target is a standard button; a mouse right click on the row still opens the row menu.
 *
 * Only `touchstart` is fired on the button, never a `pointerdown`: `pressable` stops a touch press's `contextmenu` at
 * the button by itself, and this file is about the row's own branch, which must hold for any standard button of a row.
 * The clock is faked and stepped; rows are addressed by `tr[data-row-id]`, never by position.
 */
import {afterEach, beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';
import {flushSync} from 'svelte';
import {Download, Pencil} from 'lucide-svelte';
import {cleanup, fireEvent, render, screen, setupI18n} from '$test/component';
import Button from '$lib/components/ui/button/Button.svelte';
import DataTable from './DataTable.svelte';
import type {ColumnDef, RowAction} from './types';

interface Row {
    id: string;
    name: string;
}

const ROWS: Row[] = [
    {id: 'r1', name: 'First'},
    {id: 'r2', name: 'Second'},
];

const COLUMNS: ColumnDef<Row>[] = [
    {id: 'name', header: 'Name', type: 'text', cell: (r) => r.name, getValue: (r) => r.name},
    {
        id: 'open',
        header: 'Open',
        type: 'custom',
        cell: (r) => ({type: 'custom', component: Button, props: {label: `Open ${r.name}`, icon: Download, display: 'icon', size: 'sm', variant: 'ghost', 'data-testid': `probe-open-${r.id}`}}),
    },
    {
        id: 'raw',
        header: 'Raw',
        type: 'custom',
        // A hand-written button, not yet migrated to the standard one.
        cell: (r) => ({type: 'html', html: `<button type="button" data-testid="probe-raw-${r.id}">Raw</button>`}),
    },
];

beforeAll(async () => {
    await setupI18n();
});

beforeEach(() => {
    vi.useFakeTimers();
});

afterEach(() => {
    vi.runOnlyPendingTimers();
    cleanup();
    vi.useRealTimers();
});

async function advance(ms: number) {
    await vi.advanceTimersByTimeAsync(ms);
    flushSync();
}

function row(id: string): HTMLElement {
    const el = document.querySelector<HTMLElement>(`tbody tr[data-row-id="${id}"]`);
    if (!el) throw new Error(`row ${id} is not rendered`);
    return el;
}

const nameCell = (id: string) => [...row(id).querySelectorAll<HTMLElement>('td')].find((td) => td.textContent?.trim() === ROWS.find((r) => r.id === id)?.name) ?? null;

function mount(key: string, props: Record<string, unknown> = {}) {
    const onSelectionChange = vi.fn();
    render(DataTable, {
        data: ROWS,
        columns: COLUMNS as ColumnDef<unknown>[],
        getRowId: ((r: Row) => r.id) as (row: unknown) => string,
        storageKey: key,
        enableSelection: true,
        enableTouchSelection: true,
        onSelectionChange,
        ...props,
    });
    return {onSelectionChange};
}

describe('DataTable — a long press on a row control is the control’s (85 D6)', () => {
    it('500 ms on a button of the row select nothing; 500 ms on a cell of the row select it', async () => {
        const {onSelectionChange} = mount('touch-controls-select');
        const button = screen.getByTestId('probe-open-r1');
        expect(row('r1').contains(button), 'barrier: the button sits inside the row').toBe(true);

        await fireEvent.touchStart(button);
        await advance(600);
        await fireEvent.touchEnd(button);
        expect(row('r1')).toHaveAttribute('data-selected', 'false');
        expect(onSelectionChange.mock.calls.filter(([ids]) => (ids as string[]).includes('r1'))).toEqual([]);

        const cell = nameCell('r1');
        expect(cell, 'the name cell of r1').not.toBeNull();
        await fireEvent.touchStart(cell!);
        await advance(500);
        await fireEvent.touchEnd(cell!);
        expect(row('r1')).toHaveAttribute('data-selected', 'true');
        expect(onSelectionChange).toHaveBeenLastCalledWith(['r1']);
    });

    it('500 ms on a hand-written button of the row still select it (no long press of its own yet)', async () => {
        const {onSelectionChange} = mount('touch-controls-raw');
        const raw = screen.getByTestId('probe-raw-r2');
        expect(row('r2').contains(raw), 'barrier: the button sits inside the row').toBe(true);
        await fireEvent.touchStart(raw);
        await advance(500);
        await fireEvent.touchEnd(raw);
        expect(row('r2')).toHaveAttribute('data-selected', 'true');
        expect(onSelectionChange).toHaveBeenLastCalledWith(['r2']);
    });

    it('a touch contextmenu on a button of the row opens no row menu and is cancelled; a mouse right click on the row opens it', async () => {
        const rowActions: RowAction<Row>[] = [{id: 'edit', label: 'Edit', icon: Pencil, onClick: vi.fn(), testid: 'act-edit'}];
        mount('touch-controls-menu', {enableContextMenu: true, rowActions});
        const button = screen.getByTestId('probe-open-r1');

        await fireEvent.touchStart(button);
        const notCancelled = await fireEvent.contextMenu(button);
        expect(notCancelled, 'neither the browser menu nor the row menu over the button’s name').toBe(false);
        expect(screen.queryByTestId('context-menu')).toBeNull();
        await fireEvent.touchEnd(button);

        // The touch flag clears shortly after the finger lifts; a mouse right click then is a mouse's.
        await advance(200);
        const cell = nameCell('r1');
        expect(cell).not.toBeNull();
        await fireEvent.contextMenu(cell!);
        expect(screen.getByTestId('context-menu')).toBeInTheDocument();
    });

    it('a touch contextmenu on a cell of the row still opens the row menu (only controls are excluded)', async () => {
        const rowActions: RowAction<Row>[] = [{id: 'edit', label: 'Edit', icon: Pencil, onClick: vi.fn(), testid: 'act-edit'}];
        mount('touch-controls-menu-cell', {enableContextMenu: true, rowActions});
        const cell = nameCell('r2');
        expect(cell).not.toBeNull();
        await fireEvent.touchStart(cell!);
        await fireEvent.contextMenu(cell!);
        expect(screen.getByTestId('context-menu')).toBeInTheDocument();
    });
});

/**
 * Where the row menu opens (85 BTN-0): a menu opened by a finger's long press (a `contextmenu` while a touch is active)
 * is the finger's (`ContextMenu` `origin="finger"`, to the left of the finger and above it); a mouse right click and the
 * ⋮ are a pointer's. The origin is taken when the menu opens: a finger's menu closed, the ⋮ opens a pointer's.
 */
describe('DataTable — the origin of the row menu (85 BTN-0)', () => {
    const rowActions: RowAction<Row>[] = [{id: 'edit', label: 'Edit', icon: Pencil, onClick: vi.fn(), testid: 'act-edit'}];

    it('a contextmenu during a touch on a cell opens a finger’s menu', async () => {
        mount('origin-finger', {enableContextMenu: true, rowActions});
        const cell = nameCell('r1');
        expect(cell).not.toBeNull();
        await fireEvent.touchStart(cell!);
        await fireEvent.contextMenu(cell!, {clientX: 200, clientY: 300});
        expect(screen.getByTestId('context-menu')).toHaveAttribute('data-origin', 'finger');
        expect(screen.getByTestId('context-menu').hasAttribute('data-placement')).toBe(true);
    });

    it('a mouse right click with no touch opens a pointer’s menu', async () => {
        mount('origin-pointer', {enableContextMenu: true, rowActions});
        const cell = nameCell('r1');
        expect(cell).not.toBeNull();
        await fireEvent.contextMenu(cell!, {clientX: 200, clientY: 300});
        const menu = screen.getByTestId('context-menu');
        expect(menu).toHaveAttribute('data-origin', 'pointer');
        expect(menu.hasAttribute('data-placement')).toBe(false);
    });

    it('the ⋮ opens a pointer’s menu, even right after a finger’s one', async () => {
        mount('origin-kebab', {enableContextMenu: true, rowActions});
        const cell = nameCell('r1');
        expect(cell).not.toBeNull();
        await fireEvent.touchStart(cell!);
        await fireEvent.contextMenu(cell!, {clientX: 200, clientY: 300});
        expect(screen.getByTestId('context-menu')).toHaveAttribute('data-origin', 'finger');
        await fireEvent.touchEnd(cell!);
        await fireEvent.keyDown(window, {key: 'Escape'});
        await advance(200);
        expect(screen.queryByTestId('context-menu')).toBeNull();

        const kebab = screen.getByTestId('row-actions-r1');
        // jsdom measures every box as zero, and an anchored menu closes itself on a zero box: give the ⋮ a real one.
        kebab.getBoundingClientRect = () => ({x: 10, y: 10, left: 10, top: 10, right: 30, bottom: 30, width: 20, height: 20, toJSON: () => ({})});
        await fireEvent.click(kebab);
        expect(screen.getByTestId('context-menu')).toHaveAttribute('data-origin', 'pointer');
    });
});

/**
 * The standard button inside a row keeps its own long press (85 D6 with BTN-0): the finger's touch marks the table
 * (`touchActive`, `dt-touching`), and that must not re-render the cell under the finger — a remounted button loses
 * the press it was timing and never shows its name.
 */
describe('DataTable — a Button in a row keeps its long press while the table marks the touch', () => {
    function touchPointer(element: Element, type: string): void {
        const event = new MouseEvent(type, {bubbles: true, cancelable: true, clientX: 10, clientY: 10});
        Object.defineProperty(event, 'pointerType', {value: 'touch'});
        element.dispatchEvent(event);
        flushSync();
    }

    it('the button under the finger stays the same node, and 500 ms show its name', async () => {
        mount('touch-controls-name');
        const button = screen.getByTestId('probe-open-r1');
        touchPointer(button, 'pointerdown');
        await fireEvent.touchStart(button);
        expect(screen.getByTestId('probe-open-r1'), 'the touch re-rendered the cell: a new button lost the press').toBe(button);
        expect(button.isConnected).toBe(true);
        await advance(500);
        expect(screen.getByTestId('probe-open-r1')).toBe(button);
        const tip = document.querySelector('[role="tooltip"]');
        expect(tip?.textContent?.trim()).toBe('Open First');
        touchPointer(button, 'pointerup');
        await fireEvent.touchEnd(button);
    });
});
