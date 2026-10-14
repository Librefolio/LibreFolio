// @vitest-environment jsdom
/**
 * DataTable — `onRowOrderChange` (workstream K, step 16 item 2), pinned red-first.
 *
 * The asset detail page gets `‹ n/N ›` buttons that follow "the list I left" (developer, 06/10). In
 * table view that list is what each panel's DataTable shows, so the table has to say which order it
 * shows. The contract:
 *   - the callback receives the row ids (through `getRowId`) in DISPLAY order: after "show selected
 *     only", the column filters and the sort, and BEFORE pagination — every page, not only the one
 *     on screen, because the next asset may sit on page 2;
 *   - it is called once after mount, and again whenever that order changes;
 *   - it is NOT called again while the order is unchanged: a new `data` array holding the same ids in
 *     the same order (the asset list rebuilds its rows on every price wave), a page change, a column
 *     resized (mirrored across the three panel tables) or added (the delta columns), a row ticked;
 *   - without the prop, the table behaves exactly as before.
 *
 * Every "not called again" assertion stands on two floors: the mount report arrived
 * (`mountReported`), so a table that never calls the callback cannot pass vacuously; and a presence
 * barrier proving the change really landed (the page moved, the new data rendered, the width
 * applied) before the call count is read.
 *
 * Kept out of `DataTable.test.ts` on purpose: another workstream edits that file. The patterns are
 * the same (rows addressed by `tr[data-row-id]`, never by position; no translated text).
 */
import {describe, expect, it, vi} from 'vitest';
import type {Mock} from 'vitest';
import {tick} from 'svelte';
import {fireEvent, render, screen, setupI18n, waitFor} from '$test/component';
import DataTable from './DataTable.svelte';
import type {ColumnDef} from './types';

interface Row {
    id: string;
    name: string;
    qty: number | null;
}

const COLUMNS: ColumnDef<Row>[] = [
    {id: 'name', header: 'Name', type: 'text', cell: (r) => r.name, getValue: (r) => r.name},
    {id: 'qty', header: 'Qty', type: 'number', cell: (r) => r.qty ?? '', getValue: (r) => r.qty},
];

/** A column the caller adds later, like the delta columns a wider date range brings. */
const NOTE_COLUMN: ColumnDef<Row> = {id: 'note', header: 'Note', type: 'text', cell: () => 'n'};

const getRowId = (r: Row) => r.id;

/** `n` rows named `Name 1…n` with ascending `qty`, ids `r1…rn`. */
function rows(n: number): Row[] {
    return Array.from({length: n}, (_, i) => ({id: `r${i + 1}`, name: `Name ${i + 1}`, qty: i + 1}));
}

/** The ids `r1…rn`, or `rn…r1` when `descending`. */
function ids(n: number, descending = false): string[] {
    const ascending = Array.from({length: n}, (_, i) => `r${i + 1}`);
    return descending ? ascending.reverse() : ascending;
}

/**
 * Mount with the props every case needs. `render` cannot carry the component generic, so `T`
 * widens to `unknown` at this call; the casts stay confined to that seam.
 */
function mount(key: string, props: Record<string, unknown> = {}) {
    const onRowOrderChange = vi.fn();
    return {
        onRowOrderChange,
        ...render(DataTable, {
            data: rows(3),
            columns: COLUMNS as ColumnDef<unknown>[],
            getRowId: getRowId as (row: unknown) => string,
            storageKey: key,
            onRowOrderChange,
            ...props,
        }),
    };
}

/** Every order the table reported so far, oldest first. Copied: Svelte may hand over a state proxy. */
function reported(spy: Mock): string[][] {
    return spy.mock.calls.map(([order]) => [...(order as string[])]);
}

/** Mount, flush, and prove the single mount report arrived: the floor of every "not again" case. */
async function mountReported(key: string, props: Record<string, unknown> = {}, expected: string[] = ids(3)) {
    const view = mount(key, props);
    await tick();
    expect(reported(view.onRowOrderChange), 'DataTable must report its row order once after mount (onRowOrderChange)').toEqual([expected]);
    return view;
}

/** The ids currently rendered in `<tbody>`, in DOM order. */
function pageIds(): string[] {
    return [...document.querySelectorAll('tbody tr[data-row-id]')].map((el) => el.getAttribute('data-row-id') ?? '');
}

function row(id: string): HTMLElement {
    const el = document.querySelector<HTMLElement>(`tbody tr[data-row-id="${id}"]`);
    if (!el) throw new Error(`row ${id} is not on the current page (page holds: ${pageIds().join(', ') || 'nothing'})`);
    return el;
}

/**
 * Commits a value into a bound field: `bind:value` listens on `input`, the filter's own handler on
 * `change` (same helper as `DataTableColumnFilter.test.ts`).
 */
async function commit(el: HTMLElement, value: string) {
    await fireEvent.input(el, {target: {value}});
    await fireEvent.change(el);
}

describe('DataTable — onRowOrderChange: what it reports', () => {
    it('reports every row id, through getRowId, once after mount', async () => {
        await setupI18n();
        // Ids that are not positions: a table reporting indexes would say 0, 1, 2.
        const data = [
            {id: 'tx-7', name: 'B', qty: 2},
            {id: 'ghost-7', name: 'A', qty: 1},
            {id: 'tx-1', name: 'C', qty: 3},
        ];
        const {onRowOrderChange} = mount('order-mount', {data});
        await tick();

        expect(pageIds()).toEqual(['tx-7', 'ghost-7', 'tx-1']);
        expect(reported(onRowOrderChange)).toEqual([['tx-7', 'ghost-7', 'tx-1']]);
    });

    it('reports the order each sort produces, and the caller order again when the sort is cleared', async () => {
        await setupI18n();
        const data = [
            {id: 'r1', name: 'B', qty: 2},
            {id: 'r2', name: 'A', qty: 1},
            {id: 'r3', name: 'C', qty: 3},
        ];
        const {onRowOrderChange} = await mountReported('order-sort', {data});

        await fireEvent.click(screen.getByTestId('dt-sort-name'));
        expect(screen.getByTestId('dt-header-name')).toHaveAttribute('data-sort', 'asc');
        await fireEvent.click(screen.getByTestId('dt-sort-name'));
        expect(screen.getByTestId('dt-header-name')).toHaveAttribute('data-sort', 'desc');
        await fireEvent.click(screen.getByTestId('dt-sort-name'));
        expect(screen.getByTestId('dt-header-name')).toHaveAttribute('data-sort', 'none');

        // One report per change, each the order on screen at that moment.
        expect(reported(onRowOrderChange)).toEqual([
            ['r1', 'r2', 'r3'],
            ['r2', 'r1', 'r3'],
            ['r3', 'r1', 'r2'],
            ['r1', 'r2', 'r3'],
        ]);
    });

    it('reports every page in display order, not only the page on screen', async () => {
        await setupI18n();
        const {onRowOrderChange} = await mountReported('order-pages', {data: rows(25), defaultPageSize: 10}, ids(25));
        // The table really pages: the report is wider than the screen.
        expect(pageIds()).toEqual(ids(10));

        await fireEvent.click(screen.getByTestId('dt-sort-qty'));
        expect(screen.getByTestId('dt-header-qty')).toHaveAttribute('data-sort', 'asc');
        await fireEvent.click(screen.getByTestId('dt-sort-qty'));
        expect(pageIds()).toEqual(ids(25, true).slice(0, 10));

        // Ascending by qty is the order the rows already had: nothing new until descending.
        expect(reported(onRowOrderChange)).toEqual([ids(25), ids(25, true)]);
    });

    it('reports only the ticked rows while "show selected only" is on, and every row once it is off', async () => {
        await setupI18n();
        const {onRowOrderChange} = await mountReported('order-selected-only', {data: rows(4)}, ids(4));

        await fireEvent.click(screen.getByTestId('dt-row-checkbox-r2'));
        await fireEvent.click(screen.getByTestId('dt-row-checkbox-r4'));
        expect(screen.getByTestId('dt-row-checkbox-r4')).toHaveAttribute('data-state', 'checked');
        // Ticking rows reorders nothing.
        expect(reported(onRowOrderChange)).toEqual([ids(4)]);

        await fireEvent.click(screen.getByTestId('dt-show-selected-only'));
        expect(pageIds()).toEqual(['r2', 'r4']);
        await fireEvent.click(screen.getByTestId('dt-show-selected-only'));
        expect(pageIds()).toEqual(ids(4));

        expect(reported(onRowOrderChange)).toEqual([ids(4), ['r2', 'r4'], ids(4)]);
    });

    it('reports what the column filters leave, in the order the sort gives it', async () => {
        await setupI18n();
        const {onRowOrderChange} = await mountReported('order-filter', {data: rows(5)}, ids(5));

        await fireEvent.click(screen.getByTestId('col-filter-trigger-qty'));
        // qty ≥ 3: the number filter applies on `change`, no debounce.
        await commit(await screen.findByTestId('filter-number-min'), '3');
        await waitFor(() => expect(pageIds()).toEqual(['r3', 'r4', 'r5']));
        expect(reported(onRowOrderChange)).toEqual([ids(5), ['r3', 'r4', 'r5']]);

        await fireEvent.click(screen.getByTestId('dt-sort-qty'));
        expect(screen.getByTestId('dt-header-qty')).toHaveAttribute('data-sort', 'asc');
        await fireEvent.click(screen.getByTestId('dt-sort-qty'));
        expect(pageIds()).toEqual(['r5', 'r4', 'r3']);

        // The filtered rows were already ascending: only descending is a new order.
        expect(reported(onRowOrderChange)).toEqual([ids(5), ['r3', 'r4', 'r5'], ['r5', 'r4', 'r3']]);
    });

    it('reports again when new data changes the order or the set of rows', async () => {
        await setupI18n();
        const {onRowOrderChange, rerender} = await mountReported('order-new-data');

        await rerender({data: rows(3).reverse()});
        await waitFor(() => expect(pageIds()).toEqual(['r3', 'r2', 'r1']));
        await rerender({data: rows(4)});
        await waitFor(() => expect(pageIds()).toEqual(ids(4)));
        await rerender({data: rows(4).filter((r) => r.id !== 'r2')});
        await waitFor(() => expect(pageIds()).toEqual(['r1', 'r3', 'r4']));

        expect(reported(onRowOrderChange)).toEqual([ids(3), ['r3', 'r2', 'r1'], ids(4), ['r1', 'r3', 'r4']]);
    });

    it('reports the rows once they arrive after an empty mount', async () => {
        await setupI18n();
        const {onRowOrderChange, rerender} = mount('order-late-data', {data: [], isLoading: true});
        await tick();

        await rerender({data: rows(2), isLoading: false});
        await waitFor(() => expect(pageIds()).toEqual(['r1', 'r2']));

        const reports = reported(onRowOrderChange);
        expect(reports.at(-1)).toEqual(['r1', 'r2']);
        // Exactly one report of the rows that arrived; whether the empty mount reported `[]` is not the point.
        expect(reports.filter((order) => order.join() === 'r1,r2')).toHaveLength(1);
    });
});

describe('DataTable — onRowOrderChange: what it does not report', () => {
    it('stays silent when new data holds the same ids in the same order', async () => {
        await setupI18n();
        const {onRowOrderChange, rerender} = await mountReported('order-same-data');

        // The asset list rebuilds its rows on every price wave: new objects, same ids, same order.
        await rerender({data: rows(3).map((r) => ({...r, name: `${r.name} (refreshed)`}))});
        await waitFor(() => expect(row('r1')).toHaveTextContent('Name 1 (refreshed)'));
        await tick();

        expect(reported(onRowOrderChange)).toEqual([ids(3)]);
    });

    it('stays silent on a page change', async () => {
        await setupI18n();
        const {onRowOrderChange} = await mountReported('order-page-change', {data: rows(25), defaultPageSize: 10}, ids(25));

        await fireEvent.click(screen.getByTestId('pagination-next'));
        await waitFor(() => expect(pageIds()).toEqual(ids(25).slice(10, 20)));
        await tick();

        expect(reported(onRowOrderChange)).toEqual([ids(25)]);
    });

    it('stays silent when a column is resized or added', async () => {
        await setupI18n();
        const {component, onRowOrderChange, rerender} = await mountReported('order-columns');
        const api = component as unknown as {setColumnWidth: (columnId: string, width: number) => void};

        // The asset list mirrors a resize across its three panel tables through setColumnWidth.
        api.setColumnWidth('name', 321);
        await waitFor(() => expect(screen.getByTestId('dt-header-name')).toHaveStyle({width: '321px'}));
        // A wider date range adds delta columns to the same table. Same seam as `mount()`: the
        // defs are checked against `Row` where declared, only the call into the generic widens.
        await rerender({columns: [...COLUMNS, NOTE_COLUMN] as ColumnDef<unknown>[]});
        await waitFor(() => expect(screen.getByTestId('dt-header-note')).toBeInTheDocument());
        await tick();

        expect(reported(onRowOrderChange)).toEqual([ids(3)]);
    });
});

describe('DataTable — without onRowOrderChange (characterization: green before and after)', () => {
    it('renders, sorts and pages exactly as before', async () => {
        await setupI18n();
        render(DataTable, {
            data: rows(25),
            columns: COLUMNS as ColumnDef<unknown>[],
            getRowId: getRowId as (row: unknown) => string,
            storageKey: 'order-absent',
            defaultPageSize: 10,
        });
        expect(pageIds()).toEqual(ids(10));

        await fireEvent.click(screen.getByTestId('dt-sort-qty'));
        await fireEvent.click(screen.getByTestId('dt-sort-qty'));
        expect(screen.getByTestId('dt-header-qty')).toHaveAttribute('data-sort', 'desc');
        expect(pageIds()).toEqual(ids(25, true).slice(0, 10));

        await fireEvent.click(screen.getByTestId('pagination-next'));
        await waitFor(() => expect(pageIds()).toEqual(ids(25, true).slice(10, 20)));
    });

    it('filters and shows the selection only, exactly as before', async () => {
        await setupI18n();
        render(DataTable, {
            data: rows(5),
            columns: COLUMNS as ColumnDef<unknown>[],
            getRowId: getRowId as (row: unknown) => string,
            storageKey: 'order-absent-filter',
        });

        await fireEvent.click(screen.getByTestId('col-filter-trigger-qty'));
        await commit(await screen.findByTestId('filter-number-min'), '3');
        await waitFor(() => expect(pageIds()).toEqual(['r3', 'r4', 'r5']));

        await fireEvent.click(screen.getByTestId('dt-row-checkbox-r4'));
        await fireEvent.click(screen.getByTestId('dt-show-selected-only'));
        expect(pageIds()).toEqual(['r4']);
    });
});
