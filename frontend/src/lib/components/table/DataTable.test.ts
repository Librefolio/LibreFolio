// @vitest-environment jsdom
/**
 * DataTable — component test (Vitest + jsdom).
 *
 * Half the application is a DataTable: assets, transactions, files, brokers, FX,
 * the import wizard and the schedule editor all mount this one component. Its
 * E2E coverage is therefore wide but incidental — every spec drives it through
 * whatever the page under test happens to configure, so the props that only one
 * caller sets (`isRowSelectable`, `footerCells`, `hiddenByDefault`,
 * `selectionMode: 'single'`) are exercised by accident or not at all.
 *
 * Here every one of them is a prop, and the contract is observable in three
 * places: the rows in the DOM, the callbacks the parent is handed
 * (`onSelectionChange`, `onSortChange`, `onRowClick`, `onShowSelectedOnlyChange`)
 * and the imperative API the component exports (`navigateToRowId`,
 * `toggleRowSelectionById`, `clearSelection`, `getPageRowIds`,
 * `getColumnsForVisibility`, `toggleColumnVisibilityById`, `resetColumnLayout`).
 *
 * Rows are always addressed by `tr[data-row-id="…"]`, never by position: the
 * table sorts and paginates, so an index means nothing here.
 *
 * What it deliberately does NOT assert:
 *   - the `⋮` row-actions button. It opens the same ContextMenu the right-click
 *     path opens, but it passes the button as `anchorEl`, and ContextMenu's
 *     `syncToAnchor()` closes itself when the anchor measures zero — which in
 *     jsdom it always does. The menu's own logic is reached below through the
 *     right-click path, which passes `anchorEl = null`.
 *   - column resizing, drag-to-reorder and the sticky/pinned columns. All three
 *     are arithmetic on `getBoundingClientRect` and `offsetWidth`, which jsdom
 *     reports as zero; asserting on them would measure the absence of a layout
 *     engine, not the component.
 *   - localStorage persistence of page size, widths, order and visibility
 *     overrides. This jsdom build exposes no `localStorage` at all, so
 *     `loadFromStorage`/`saveToStorage` silently no-op behind their try/catch.
 *     (This is also why no test here needs to clear storage between cases.)
 *   - the `bulkActions` prop. `handleBulkAction` is defined but never called
 *     from the template: the bulk toolbar is a separate component that callers
 *     mount themselves. Nothing in the public surface can reach it.
 *   - translated text. `emptyMessage` is asserted because the test supplies it;
 *     the fallback label comes from the catalogue in four languages.
 */
import {describe, expect, it, vi} from 'vitest';
import type {Mock} from 'vitest';
import {Trash2} from 'lucide-svelte';
import {fireEvent, render, screen, setupI18n, waitFor, within} from '$test/component';
import DataTable from './DataTable.svelte';
import type {ColumnDef, RowAction} from './types';

interface Row {
    id: string;
    name: string;
    qty: number | null;
}

const COLUMNS: ColumnDef<Row>[] = [
    {id: 'name', header: 'Name', type: 'text', cell: (r) => r.name, getValue: (r) => r.name},
    {id: 'qty', header: 'Qty', type: 'number', cell: (r) => r.qty ?? '', getValue: (r) => r.qty},
];

/** A column hidden until the user asks for it — only one caller in the app sets this. */
const NOTE_COLUMN: ColumnDef<Row> = {id: 'note', header: 'Note', type: 'text', cell: () => 'n', hiddenByDefault: true};

const getRowId = (r: Row) => r.id;

/** `n` rows named `Name 1…n` with ascending `qty`, ids `r1…rn`. */
function rows(n: number): Row[] {
    return Array.from({length: n}, (_, i) => ({id: `r${i + 1}`, name: `Name ${i + 1}`, qty: i + 1}));
}

/**
 * Mount with the props every case needs. `storageKey` is distinct per test so
 * that if this jsdom ever gains a real `localStorage`, the cases stay isolated.
 *
 * DataTable is generic over the row type, but `render` cannot carry a
 * component generic, so `T` widens to `unknown` at this call. The two casts
 * below are confined to that seam: the column defs themselves stay checked
 * against `Row`.
 */
function mount(key: string, props: Record<string, unknown> = {}) {
    const onSelectionChange = vi.fn();
    const onSortChange = vi.fn();
    const onRowClick = vi.fn();
    return {
        onSelectionChange,
        onSortChange,
        onRowClick,
        ...render(DataTable, {
            data: rows(3),
            columns: COLUMNS as ColumnDef<unknown>[],
            getRowId: getRowId as (row: unknown) => string,
            storageKey: key,
            onSelectionChange,
            onSortChange,
            onRowClick,
            ...props,
        }),
    };
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

/** The ids the parent was handed last. `undefined` means it was never called. */
function lastSelection(spy: Mock): string[] | undefined {
    return spy.mock.calls.at(-1)?.[0];
}

/** Svelte 5 hands callbacks a state proxy, so compare structurally. */
function lastSort(spy: Mock): {columnId: string; direction: string} | null | undefined {
    const arg = spy.mock.calls.at(-1)?.[0];
    return arg == null ? arg : {columnId: arg.columnId, direction: arg.direction};
}

describe('DataTable — rows and identity', () => {
    it('keys rows by getRowId, not by array position', async () => {
        await setupI18n();
        // The transactions table prefixes real ids with `tx-` and draft ids with
        // `ghost-` so the two id spaces cannot collide in the selection map.
        const data = [
            {id: 'tx-7', name: 'Real', qty: 1},
            {id: 'ghost-7', name: 'Draft', qty: 2},
        ];
        mount('identity', {data});

        expect(pageIds()).toEqual(['tx-7', 'ghost-7']);

        await fireEvent.click(screen.getByTestId('dt-row-checkbox-tx-7'));
        expect(screen.getByTestId('dt-row-checkbox-tx-7')).toHaveAttribute('data-state', 'checked');
        // Same numeric suffix, different id space: it must stay untouched.
        expect(screen.getByTestId('dt-row-checkbox-ghost-7')).toHaveAttribute('data-state', 'unchecked');
    });

    it('publishes the empty state and shows the caller-supplied message', async () => {
        await setupI18n();
        const {rerender} = mount('empty', {data: [], emptyMessage: 'NOTHING-HERE'});

        expect(screen.getByTestId('dt-empty')).toHaveTextContent('NOTHING-HERE');
        expect(screen.queryByTestId('dt-loading')).toBeNull();

        await rerender({isLoading: true});
        // Loading wins over empty: the table must not claim "no data" while it is fetching.
        expect(screen.getByTestId('dt-loading')).toBeInTheDocument();
        expect(screen.queryByTestId('dt-empty')).toBeNull();
    });

    it('hides the loading row as soon as data arrives', async () => {
        await setupI18n();
        const {rerender} = mount('loading-to-data', {data: [], isLoading: true});
        expect(screen.getByTestId('dt-loading')).toBeInTheDocument();

        await rerender({data: rows(2), isLoading: false});
        expect(screen.queryByTestId('dt-loading')).toBeNull();
        expect(pageIds()).toEqual(['r1', 'r2']);
    });
});

describe('DataTable — sorting', () => {
    it('cycles a column through ascending, descending and unsorted', async () => {
        await setupI18n();
        const {onSortChange} = mount('sort-cycle', {
            data: [
                {id: 'r1', name: 'B', qty: 2},
                {id: 'r2', name: 'A', qty: 1},
                {id: 'r3', name: 'C', qty: 3},
            ],
        });
        const original = pageIds();

        await fireEvent.click(screen.getByTestId('dt-sort-name'));
        expect(pageIds()).toEqual(['r2', 'r1', 'r3']);
        expect(screen.getByTestId('dt-header-name')).toHaveAttribute('data-sort', 'asc');
        expect(lastSort(onSortChange)).toEqual({columnId: 'name', direction: 'asc'});

        await fireEvent.click(screen.getByTestId('dt-sort-name'));
        expect(pageIds()).toEqual(['r3', 'r1', 'r2']);
        expect(screen.getByTestId('dt-header-name')).toHaveAttribute('data-sort', 'desc');
        expect(lastSort(onSortChange)).toEqual({columnId: 'name', direction: 'desc'});

        // Third click clears the sort and restores the caller's order — the state
        // the table started in, which a two-state toggle could never get back to.
        await fireEvent.click(screen.getByTestId('dt-sort-name'));
        expect(pageIds()).toEqual(original);
        expect(screen.getByTestId('dt-header-name')).toHaveAttribute('data-sort', 'none');
        expect(lastSort(onSortChange)).toBeNull();
    });

    it('sends empty cells to the bottom in both directions', async () => {
        await setupI18n();
        // `sortedData` used to have no branch for a missing value: it fell through to
        // String(aRaw) and compared the literal "null" with localeCompare, so
        // descending put the empty cells *above* the largest number — and whether they
        // led or trailed depended on whether the placeholder stringified as 'null',
        // 'undefined' or ''. A missing value is not a value; it belongs last.
        mount('sort-nulls', {
            data: [
                {id: 'r1', name: 'A', qty: 2},
                {id: 'r2', name: 'B', qty: null},
                {id: 'r3', name: 'C', qty: 9},
                {id: 'r4', name: 'D', qty: 5},
            ],
        });

        await fireEvent.click(screen.getByTestId('dt-sort-qty'));
        expect(pageIds()).toEqual(['r1', 'r4', 'r3', 'r2']);

        await fireEvent.click(screen.getByTestId('dt-sort-qty'));
        // The row with no quantity stays at the bottom instead of leapfrogging 9.
        expect(pageIds()).toEqual(['r3', 'r4', 'r1', 'r2']);
    });

    it('keeps two empty cells in the order the caller gave them', async () => {
        await setupI18n();
        mount('sort-nulls-stable', {
            data: [
                {id: 'r1', name: 'A', qty: null},
                {id: 'r2', name: 'B', qty: 4},
                {id: 'r3', name: 'C', qty: null},
            ],
        });

        await fireEvent.click(screen.getByTestId('dt-sort-qty'));
        expect(pageIds()).toEqual(['r2', 'r1', 'r3']);
    });

    it('sorts numbers by magnitude, not lexicographically', async () => {
        await setupI18n();
        // '2' > '10' as strings; the point of the numeric branch is that it isn't.
        mount('sort-number', {
            data: [
                {id: 'r1', name: 'a', qty: 2},
                {id: 'r2', name: 'b', qty: 10},
                {id: 'r3', name: 'c', qty: 1},
            ],
        });

        await fireEvent.click(screen.getByTestId('dt-sort-qty'));
        expect(pageIds()).toEqual(['r3', 'r1', 'r2']);
    });

    it('sorts Date values chronologically, not by their printed form', async () => {
        await setupI18n();
        // Locale date strings sort wrongly as text ('01/12' before '02/01'), so the
        // Date branch of the comparator is the only thing keeping this column honest.
        const columns: ColumnDef<Row>[] = [COLUMNS[0], {id: 'when', header: 'When', type: 'date', cell: (r) => r.name, getValue: (r) => new Date(`2024-0${r.qty}-01`)}];
        mount('sort-date', {
            columns,
            data: [
                {id: 'r1', name: 'a', qty: 3},
                {id: 'r2', name: 'b', qty: 1},
                {id: 'r3', name: 'c', qty: 2},
            ],
        });

        await fireEvent.click(screen.getByTestId('dt-sort-when'));
        expect(pageIds()).toEqual(['r2', 'r3', 'r1']);

        await fireEvent.click(screen.getByTestId('dt-sort-when'));
        expect(pageIds()).toEqual(['r1', 'r3', 'r2']);
    });

    it('keeps rows with equal keys in their original order', async () => {
        await setupI18n();
        mount('sort-stable', {
            data: [
                {id: 'r1', name: 'same', qty: 1},
                {id: 'r2', name: 'same', qty: 2},
                {id: 'r3', name: 'aaa', qty: 3},
                {id: 'r4', name: 'same', qty: 4},
            ],
        });

        await fireEvent.click(screen.getByTestId('dt-sort-name'));
        expect(pageIds()).toEqual(['r3', 'r1', 'r2', 'r4']);
    });

    it('does not offer sorting on a column that opted out', async () => {
        await setupI18n();
        const columns: ColumnDef<Row>[] = [COLUMNS[0], {...COLUMNS[1], sortable: false}];
        const {onSortChange} = mount('sort-optout', {columns});

        expect(screen.getByTestId('dt-sort-qty')).toBeDisabled();
        expect(screen.getByTestId('dt-sort-name')).toBeEnabled();
        expect(onSortChange).not.toHaveBeenCalled();
    });
});

describe('DataTable — multi selection', () => {
    it('reports every id the user checked', async () => {
        await setupI18n();
        const {onSelectionChange} = mount('multi-basic');

        await fireEvent.click(screen.getByTestId('dt-row-checkbox-r1'));
        expect(lastSelection(onSelectionChange)).toEqual(['r1']);

        await fireEvent.click(screen.getByTestId('dt-row-checkbox-r3'));
        expect(lastSelection(onSelectionChange)?.sort()).toEqual(['r1', 'r3']);

        await fireEvent.click(screen.getByTestId('dt-row-checkbox-r1'));
        expect(lastSelection(onSelectionChange)).toEqual(['r3']);
        expect(screen.getByTestId('dt-row-checkbox-r1')).toHaveAttribute('data-state', 'unchecked');
    });

    it('publishes the header checkbox as unchecked, partial and checked', async () => {
        await setupI18n();
        mount('multi-tristate');
        expect(screen.getByTestId('dt-select-all')).toHaveAttribute('data-state', 'unchecked');

        await fireEvent.click(screen.getByTestId('dt-row-checkbox-r2'));
        expect(screen.getByTestId('dt-select-all')).toHaveAttribute('data-state', 'partial');

        await fireEvent.click(screen.getByTestId('dt-select-all'));
        expect(screen.getByTestId('dt-select-all')).toHaveAttribute('data-state', 'checked');

        await fireEvent.click(screen.getByTestId('dt-select-all'));
        expect(screen.getByTestId('dt-select-all')).toHaveAttribute('data-state', 'unchecked');
    });

    it('select-all replaces the selection with the current page, deselect-all only drops it', async () => {
        await setupI18n();
        // Documented as intentional at DataTable.svelte:713 — the asymmetry is the
        // contract, so it is pinned here rather than reported.
        const {component, onSelectionChange} = mount('multi-pages', {data: rows(6), defaultPageSize: 3, alwaysShowPagination: true});
        const api = component as unknown as {toggleRowSelectionById: (id: string) => void};

        api.toggleRowSelectionById('r5'); // lives on page 2
        await waitFor(() => expect(lastSelection(onSelectionChange)).toEqual(['r5']));

        await fireEvent.click(screen.getByTestId('dt-select-all'));
        // Page 1 replaces: the off-page id is gone.
        expect(lastSelection(onSelectionChange)?.sort()).toEqual(['r1', 'r2', 'r3']);

        await fireEvent.click(screen.getByTestId('pagination-next'));
        await waitFor(() => expect(pageIds()).toEqual(['r4', 'r5', 'r6']));
        await fireEvent.click(screen.getByTestId('dt-row-checkbox-r4'));
        expect(lastSelection(onSelectionChange)?.sort()).toEqual(['r1', 'r2', 'r3', 'r4']);

        await fireEvent.click(screen.getByTestId('dt-select-all'));
        // Not all of page 2 was selected, so this is a select — it replaces again.
        expect(lastSelection(onSelectionChange)?.sort()).toEqual(['r4', 'r5', 'r6']);

        await fireEvent.click(screen.getByTestId('dt-select-all'));
        // Now it is a deselect, and it only removes this page's rows.
        expect(lastSelection(onSelectionChange)).toEqual([]);
    });

    it('toggleRowSelectionById and clearSelection reach rows through the public API', async () => {
        await setupI18n();
        const {component, onSelectionChange} = mount('multi-api');
        const api = component as unknown as {toggleRowSelectionById: (id: string) => void; clearSelection: () => void};

        api.toggleRowSelectionById('r2');
        await waitFor(() => expect(screen.getByTestId('dt-row-checkbox-r2')).toHaveAttribute('data-state', 'checked'));
        expect(lastSelection(onSelectionChange)).toEqual(['r2']);

        api.toggleRowSelectionById('r2');
        await waitFor(() => expect(screen.getByTestId('dt-row-checkbox-r2')).toHaveAttribute('data-state', 'unchecked'));

        api.toggleRowSelectionById('r1');
        api.toggleRowSelectionById('r3');
        await waitFor(() => expect(lastSelection(onSelectionChange)?.sort()).toEqual(['r1', 'r3']));

        api.clearSelection();
        await waitFor(() => expect(lastSelection(onSelectionChange)).toEqual([]));
        expect(screen.getByTestId('dt-row-checkbox-r1')).toHaveAttribute('data-state', 'unchecked');
    });

    it('marks the selected row on the element itself, not only through a CSS class', async () => {
        await setupI18n();
        mount('multi-attr');
        expect(row('r2')).toHaveAttribute('data-selected', 'false');

        await fireEvent.click(screen.getByTestId('dt-row-checkbox-r2'));
        expect(row('r2')).toHaveAttribute('data-selected', 'true');
        expect(row('r1')).toHaveAttribute('data-selected', 'false');
    });
});

describe('DataTable — non-selectable rows', () => {
    it('offers no checkbox and swallows the click on a row the caller refuses', async () => {
        await setupI18n();
        const {onRowClick, onSelectionChange} = mount('locked', {isRowSelectable: (r: Row) => r.id !== 'r2'});

        expect(screen.queryByTestId('dt-row-checkbox-r2')).toBeNull();
        expect(screen.getByTestId('dt-row-checkbox-r1')).toBeInTheDocument();

        await fireEvent.click(row('r2'));
        expect(onRowClick).not.toHaveBeenCalled();
        expect(onSelectionChange).not.toHaveBeenCalled();

        await fireEvent.click(row('r1'));
        expect(onRowClick).toHaveBeenCalledTimes(1);
        expect(onRowClick.mock.calls[0][0]).toMatchObject({id: 'r1'});
    });

    it('never lets a double click through on a locked row', async () => {
        await setupI18n();
        const onRowDoubleClick = vi.fn();
        mount('locked-dbl', {isRowSelectable: (r: Row) => r.id !== 'r2', onRowDoubleClick});

        await fireEvent.dblClick(row('r2'));
        expect(onRowDoubleClick).not.toHaveBeenCalled();

        await fireEvent.dblClick(row('r1'));
        expect(onRowDoubleClick).toHaveBeenCalledTimes(1);
    });
});

describe('DataTable — single selection', () => {
    it('replaces the selection on each row click and mirrors the selectedRowId prop', async () => {
        await setupI18n();
        const {onSelectionChange, onRowClick, rerender} = mount('single', {selectionMode: 'single'});

        // Single mode has no checkbox column at all.
        expect(screen.queryByTestId('dt-select-all')).toBeNull();
        expect(screen.queryByTestId('dt-row-checkbox-r1')).toBeNull();

        await fireEvent.click(row('r1'));
        expect(lastSelection(onSelectionChange)).toEqual(['r1']);
        expect(onRowClick).toHaveBeenCalledTimes(1);

        await fireEvent.click(row('r3'));
        // Replaced, not added: single means single.
        expect(lastSelection(onSelectionChange)).toEqual(['r3']);
        expect(row('r1')).toHaveAttribute('data-selected', 'false');
        expect(row('r3')).toHaveAttribute('data-selected', 'true');

        // The parent can drive the selection from outside too.
        await rerender({selectedRowId: 'r2'});
        await waitFor(() => expect(row('r2')).toHaveAttribute('data-selected', 'true'));
        expect(row('r3')).toHaveAttribute('data-selected', 'false');
    });
});

describe('DataTable — show-selected-only', () => {
    it('narrows the table to the selection and switches itself off when it empties', async () => {
        await setupI18n();
        const onShowSelectedOnlyChange = vi.fn();
        mount('selected-only', {data: rows(4), onShowSelectedOnlyChange});

        await fireEvent.click(screen.getByTestId('dt-row-checkbox-r2'));
        await fireEvent.click(screen.getByTestId('dt-show-selected-only'));

        expect(screen.getByTestId('dt-show-selected-only')).toHaveAttribute('data-state', 'on');
        expect(pageIds()).toEqual(['r2']);
        expect(onShowSelectedOnlyChange).toHaveBeenLastCalledWith(true);

        // Unchecking the last row would otherwise leave the user staring at an
        // empty table with no visible way back — the filter has to release itself.
        await fireEvent.click(screen.getByTestId('dt-row-checkbox-r2'));
        await waitFor(() => expect(onShowSelectedOnlyChange).toHaveBeenLastCalledWith(false));
        expect(screen.getByTestId('dt-show-selected-only')).toHaveAttribute('data-state', 'off');
        expect(pageIds()).toEqual(['r1', 'r2', 'r3', 'r4']);
    });
});

describe('DataTable — pagination', () => {
    it('stays out of the way until there is more than one page of rows', async () => {
        await setupI18n();
        const {rerender} = mount('pg-visibility', {data: rows(3), defaultPageSize: 10});
        expect(screen.queryByTestId('data-table-pagination')).toBeNull();

        await rerender({data: rows(25)});
        await waitFor(() => expect(screen.getByTestId('data-table-pagination')).toBeInTheDocument());
    });

    it('walks pages and reports the page contents through getPageRowIds', async () => {
        await setupI18n();
        const {component} = mount('pg-walk', {data: rows(25), defaultPageSize: 10});
        const api = component as unknown as {getPageRowIds: () => string[]};

        expect(pageIds()).toEqual(['r1', 'r2', 'r3', 'r4', 'r5', 'r6', 'r7', 'r8', 'r9', 'r10']);
        expect(api.getPageRowIds()).toEqual(pageIds());

        await fireEvent.click(screen.getByTestId('pagination-next'));
        await waitFor(() => expect(pageIds()).toContain('r11'));
        expect(api.getPageRowIds()).toEqual(pageIds());

        await fireEvent.click(screen.getByTestId('pagination-prev'));
        await waitFor(() => expect(pageIds()).toContain('r1'));
    });

    it('jumps to the page holding the requested row and marks it', async () => {
        await setupI18n();
        const {component} = mount('pg-navigate', {data: rows(25), defaultPageSize: 10});
        const api = component as unknown as {navigateToRowId: (id: string) => void};

        expect(pageIds()).not.toContain('r23');
        api.navigateToRowId('r23');

        await waitFor(() => expect(pageIds()).toContain('r23'));
        expect(row('r23')).toHaveAttribute('data-highlighted', 'true');
        expect(row('r21')).toHaveAttribute('data-highlighted', 'false');
    });

    it('accounts for the active sort when working out which page a row is on', async () => {
        await setupI18n();
        const {component} = mount('pg-navigate-sorted', {data: rows(25), defaultPageSize: 10});
        const api = component as unknown as {navigateToRowId: (id: string) => void};

        // Descending by qty puts r1 last, so navigating to it must land on page 3
        // and not on the page it occupied before the sort.
        await fireEvent.click(screen.getByTestId('dt-sort-qty'));
        await fireEvent.click(screen.getByTestId('dt-sort-qty'));
        await waitFor(() => expect(pageIds()[0]).toBe('r25'));

        api.navigateToRowId('r1');
        await waitFor(() => expect(pageIds()).toContain('r1'));
        expect(row('r1')).toHaveAttribute('data-highlighted', 'true');
    });

    it('ignores a navigation request for an id it does not hold', async () => {
        await setupI18n();
        const {component} = mount('pg-navigate-missing', {data: rows(25), defaultPageSize: 10});
        const api = component as unknown as {navigateToRowId: (id: string) => void};

        api.navigateToRowId('does-not-exist');
        await waitFor(() => expect(pageIds()).toContain('r1'));
        // Still on page one, and nothing is pretending to be the target.
        expect(document.querySelector('tbody tr[data-highlighted="true"]')).toBeNull();
    });
});

describe('DataTable — column visibility', () => {
    it('keeps a hiddenByDefault column out of the header until it is asked for', async () => {
        await setupI18n();
        const {component} = mount('cols', {columns: [...COLUMNS, NOTE_COLUMN]});
        const api = component as unknown as {
            getColumnsForVisibility: () => {id: string; visible: boolean}[];
            toggleColumnVisibilityById: (id: string) => void;
            resetColumnLayout: () => void;
        };

        expect(screen.getByTestId('dt-header-name')).toBeInTheDocument();
        expect(screen.queryByTestId('dt-header-note')).toBeNull();

        const listed = api.getColumnsForVisibility();
        expect(listed.map((c) => c.id)).toEqual(['name', 'qty', 'note']);
        expect(listed.find((c) => c.id === 'note')?.visible).toBe(false);
        expect(listed.find((c) => c.id === 'name')?.visible).toBe(true);

        api.toggleColumnVisibilityById('note');
        await waitFor(() => expect(screen.getByTestId('dt-header-note')).toBeInTheDocument());

        api.toggleColumnVisibilityById('qty');
        await waitFor(() => expect(screen.queryByTestId('dt-header-qty')).toBeNull());
        expect(screen.getByTestId('dt-header-name')).toBeInTheDocument();

        api.resetColumnLayout();
        await waitFor(() => expect(screen.getByTestId('dt-header-qty')).toBeInTheDocument());
        // Reset means back to the caller's declaration, so `note` hides again.
        expect(screen.queryByTestId('dt-header-note')).toBeNull();
    });

    it('drops the hidden column from every body row, not just from the header', async () => {
        await setupI18n();
        const {component} = mount('cols-body');
        const api = component as unknown as {toggleColumnVisibilityById: (id: string) => void};

        const cellsBefore = row('r1').querySelectorAll('td.td-data').length;
        api.toggleColumnVisibilityById('qty');

        await waitFor(() => expect(row('r1').querySelectorAll('td.td-data')).toHaveLength(cellsBefore - 1));
    });
});

describe('DataTable — footer', () => {
    it('summarises the filtered rows, then the selection once there is one', async () => {
        await setupI18n();
        const footerCells = vi.fn((src: Row[]) => ({qty: `SUM ${src.reduce((a, b) => a + (b.qty ?? 0), 0)}`}));
        mount('footer', {data: rows(4), footerCells});

        // 1+2+3+4 with nothing selected.
        expect(screen.getByTestId('dt-footer-qty')).toHaveTextContent('SUM 10');

        await fireEvent.click(screen.getByTestId('dt-row-checkbox-r1'));
        await fireEvent.click(screen.getByTestId('dt-row-checkbox-r3'));
        // The footer follows the selection: 1+3.
        await waitFor(() => expect(screen.getByTestId('dt-footer-qty')).toHaveTextContent('SUM 4'));

        const [sourceRows, selected] = footerCells.mock.calls.at(-1) as unknown as [Row[], Row[]];
        expect(sourceRows.map((r) => r.id).sort()).toEqual(['r1', 'r3']);
        expect(selected.map((r) => r.id).sort()).toEqual(['r1', 'r3']);
    });

    it('renders a column with no footer entry as an empty cell rather than dropping it', async () => {
        await setupI18n();
        mount('footer-partial', {footerCells: {qty: 'TOTAL'}});

        expect(screen.getByTestId('dt-footer-qty')).toHaveTextContent('TOTAL');
        expect(screen.getByTestId('dt-footer-name')).toHaveTextContent('');
    });
});

describe('DataTable — row actions', () => {
    /** Opens the row context menu; the right-click path is the one jsdom can measure. */
    async function openMenu(rowId: string) {
        await fireEvent.contextMenu(row(rowId));
        return screen.getByTestId('context-menu');
    }

    const actions = (onEdit: Mock, onDelete: Mock): RowAction<Row>[] => [
        {id: 'edit', label: 'Edit', icon: Trash2, onClick: onEdit, testid: 'act-edit'},
        {
            id: 'delete',
            label: 'Delete',
            icon: Trash2,
            onClick: onDelete,
            testid: 'act-delete',
            requireConfirm: true,
            visible: (r) => r.id !== 'r3',
            disabled: (r) => r.id === 'r2',
        },
    ];

    it('offers an action only on the rows its visible predicate accepts', async () => {
        await setupI18n();
        const onEdit = vi.fn();
        const onDelete = vi.fn();
        mount('actions-visible', {rowActions: actions(onEdit, onDelete)});

        const menu1 = await openMenu('r1');
        expect(within(menu1).getByTestId('act-edit')).toBeInTheDocument();
        expect(within(menu1).getByTestId('act-delete')).toBeInTheDocument();
        await fireEvent.keyDown(window, {key: 'Escape'});

        const menu3 = await openMenu('r3');
        expect(within(menu3).getByTestId('act-edit')).toBeInTheDocument();
        expect(within(menu3).queryByTestId('act-delete')).toBeNull();
    });

    it('renders a disabled action as unusable rather than hiding it', async () => {
        await setupI18n();
        const onEdit = vi.fn();
        const onDelete = vi.fn();
        mount('actions-disabled', {rowActions: actions(onEdit, onDelete)});

        const menu = await openMenu('r2');
        const del = within(menu).getByTestId('act-delete');
        expect(del).toBeDisabled();

        await fireEvent.click(del);
        expect(onDelete).not.toHaveBeenCalled();
    });

    it('runs an unguarded action immediately and hands it the row', async () => {
        await setupI18n();
        const onEdit = vi.fn();
        const onDelete = vi.fn();
        mount('actions-run', {rowActions: actions(onEdit, onDelete)});

        const menu = await openMenu('r1');
        await fireEvent.click(within(menu).getByTestId('act-edit'));

        expect(onEdit).toHaveBeenCalledTimes(1);
        expect(onEdit.mock.calls[0][0]).toMatchObject({id: 'r1'});
        await waitFor(() => expect(screen.queryByTestId('context-menu')).toBeNull());
    });

    it('holds a requireConfirm action behind the modal and runs it only on confirm', async () => {
        await setupI18n();
        const onEdit = vi.fn();
        const onDelete = vi.fn();
        mount('actions-confirm', {rowActions: actions(onEdit, onDelete)});

        const menu = await openMenu('r1');
        await fireEvent.click(within(menu).getByTestId('act-delete'));

        expect(onDelete).not.toHaveBeenCalled();
        await waitFor(() => expect(screen.getByTestId('confirm-modal-confirm')).toBeInTheDocument());

        await fireEvent.click(screen.getByTestId('confirm-modal-confirm'));
        expect(onDelete).toHaveBeenCalledTimes(1);
        expect(onDelete.mock.calls[0][0]).toMatchObject({id: 'r1'});
    });

    it('drops the pending action when the modal is cancelled', async () => {
        await setupI18n();
        const onEdit = vi.fn();
        const onDelete = vi.fn();
        mount('actions-cancel', {rowActions: actions(onEdit, onDelete)});

        const menu = await openMenu('r1');
        await fireEvent.click(within(menu).getByTestId('act-delete'));
        await waitFor(() => expect(screen.getByTestId('confirm-modal-cancel')).toBeInTheDocument());

        await fireEvent.click(screen.getByTestId('confirm-modal-cancel'));
        expect(onDelete).not.toHaveBeenCalled();

        // And the dismissal must not leave the action armed for the next confirm.
        const menu2 = await openMenu('r1');
        await fireEvent.click(within(menu2).getByTestId('act-edit'));
        expect(onDelete).not.toHaveBeenCalled();
        expect(onEdit).toHaveBeenCalledTimes(1);
    });

    it('opens no menu at all on a row where every action is hidden', async () => {
        await setupI18n();
        const onDelete = vi.fn();
        mount('actions-none', {
            rowActions: [{id: 'delete', label: 'Delete', icon: Trash2, onClick: onDelete, testid: 'act-delete', visible: (r: Row) => r.id === 'r1'}],
        });

        await fireEvent.contextMenu(row('r2'));
        expect(screen.queryByTestId('context-menu')).toBeNull();

        await fireEvent.contextMenu(row('r1'));
        expect(screen.getByTestId('context-menu')).toBeInTheDocument();
    });
});
