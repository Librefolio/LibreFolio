// @vitest-environment jsdom
/**
 * DataTable — `opensPage` (66 F7-c1, contract 66-F7 §14.4; red first).
 *
 * The Bulk's grid shows a parent's linked charges right after it, and a charge must never open a page: the group stays
 * on one page, overflowing it, as the transactions table does (F5). `DataTable` takes an optional prop
 * `opensPage?: (row: T) => boolean`:
 *
 * - with it, the pages come from `paginateFlat` (`dataTableLogic.ts`): fixed size, but a row for which `opensPage` is
 *   false never starts a page;
 * - `navigateToRowId` goes to the page that holds the row, and scrolls that row (not the row at `index % pageSize`);
 * - the pager gets the real page count (`DataTablePagination`'s `pageCount`);
 * - without it, everything is as today (the guard cases, green now).
 *
 * Kept in a file of its own, as `DataTable.navigate.test.ts` is, because other workstreams edit `DataTable.test.ts`.
 * The prop does not exist yet, so the props are handed through a cast.
 *
 * The rows: r1..r4, the parent p with its two followers p1 and p2, then r5..r9 — 12 rows at 5 per page. With
 * `opensPage` the pages are [r1 r2 r3 r4 p p1 p2] [r5 r6 r7 r8 r9]; without it [r1 r2 r3 r4 p] [p1 p2 r5 r6 r7] [r8 r9].
 */
import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';
import {fireEvent, render, screen, setupI18n, waitFor} from '$test/component';
import DataTable from './DataTable.svelte';
import type {ColumnDef} from './types';

interface Row {
    id: string;
    name: string;
    follows: boolean;
}

const COLUMNS: ColumnDef<Row>[] = [{id: 'name', header: 'Name', type: 'text', cell: (r) => r.name, getValue: (r) => r.name}];

const ROWS: Row[] = [...['r1', 'r2', 'r3', 'r4', 'p'].map((id) => ({id, name: `Name ${id}`, follows: false})), ...['p1', 'p2'].map((id) => ({id, name: `Name ${id}`, follows: true})), ...['r5', 'r6', 'r7', 'r8', 'r9'].map((id) => ({id, name: `Name ${id}`, follows: false}))];

type Api = {navigateToRowId: (id: string, options?: {scroll?: boolean; highlight?: boolean}) => void; getPageRowIds: () => string[]};

function mount(key: string, withOpensPage: boolean): Api {
    const props: Record<string, unknown> = {
        data: ROWS,
        columns: COLUMNS as ColumnDef<unknown>[],
        getRowId: ((r: Row) => r.id) as (row: unknown) => string,
        storageKey: key,
        defaultPageSize: 5,
        pageSizeOptions: [5, 10, 25, 50, 0],
        alwaysShowPagination: true,
    };
    if (withOpensPage) props.opensPage = (r: Row) => !r.follows;
    const {component} = render(DataTable, props as never);
    return component as unknown as Api;
}

const pageIds = () => Array.from(document.querySelectorAll('tbody tr[data-row-id]')).map((tr) => tr.getAttribute('data-row-id'));
const row = (id: string) => document.querySelector(`tbody tr[data-row-id="${id}"]`);
/** The page-number buttons of the pager (the current page is its input, not a button). */
const pageButtons = () => [...document.querySelectorAll('[data-testid="data-table-pagination"] button.page-btn')].map((b) => b.textContent?.trim() ?? '');

let scroll: ReturnType<typeof vi.fn>;

beforeEach(async () => {
    await setupI18n();
    scroll = vi.fn();
    Element.prototype.scrollIntoView = scroll as unknown as Element['scrollIntoView'];
});

afterEach(() => {
    document.body.innerHTML = '';
});

describe('DataTable — opensPage: a row that does not open a page never starts one', () => {
    it('the first page holds the parent and both its followers, overflowing the size of 5', async () => {
        mount('opens-first-page', true);
        await waitFor(() => expect(pageIds()).toEqual(['r1', 'r2', 'r3', 'r4', 'p', 'p1', 'p2']));
    });

    it('the pager counts the real pages: two, not three', async () => {
        mount('opens-pager', true);
        await waitFor(() => expect(pageIds()).toContain('r1'));
        expect(pageButtons(), '[1] 2 — the second page is the last').toEqual(['2']);
    });

    it('«next» goes to the second page, which holds the rest, and is then the last', async () => {
        mount('opens-next', true);
        await waitFor(() => expect(pageIds()).toContain('r1'));

        await fireEvent.click(screen.getByTestId('pagination-next'));

        await waitFor(() => expect(pageIds()).toEqual(['r5', 'r6', 'r7', 'r8', 'r9']));
        expect(screen.getByTestId('pagination-next')).toBeDisabled();
    });

    it('navigateToRowId goes to the page that holds the row: p2 sits on page 1, not on page floor(6 / 5) + 1 = 2', async () => {
        const api = mount('opens-nav-back', true);
        await waitFor(() => expect(pageIds()).toContain('r1'));
        await fireEvent.click(screen.getByTestId('pagination-next'));
        await waitFor(() => expect(pageIds()).toContain('r5'));

        api.navigateToRowId('p2');

        // Today's fixed slicing also has a page holding p2 ([p1 p2 r5 r6 r7]): the page asked for is the whole first one.
        await waitFor(() => expect(pageIds()).toEqual(['r1', 'r2', 'r3', 'r4', 'p', 'p1', 'p2']));
        expect(row('p2')).toHaveAttribute('data-highlighted', 'true');
        await waitFor(() => expect(scroll).toHaveBeenCalledTimes(1));
        expect(scroll.mock.contexts[0], 'the scroll is asked of p2 itself, not of the row at index % pageSize').toBe(row('p2'));
    });

    it('navigateToRowId to the last row lands on page 2 (there is no page 3) and scrolls that row', async () => {
        const api = mount('opens-nav-last', true);
        await waitFor(() => expect(pageIds()).toContain('r1'));

        api.navigateToRowId('r9');

        await waitFor(() => expect(pageIds()).toEqual(['r5', 'r6', 'r7', 'r8', 'r9']));
        await waitFor(() => expect(scroll).toHaveBeenCalledTimes(1));
        expect(scroll.mock.contexts[0]).toBe(row('r9'));
    });

    it('getPageRowIds names the rows of the page as drawn', async () => {
        const api = mount('opens-page-ids', true);
        await waitFor(() => expect(pageIds()).toContain('r1'));
        expect(api.getPageRowIds()).toEqual(['r1', 'r2', 'r3', 'r4', 'p', 'p1', 'p2']);
    });
});

describe('DataTable — without opensPage nothing changes (guard)', () => {
    it('fixed pages of 5: the followers are split from their parent, three pages', async () => {
        mount('plain-pages', false);
        await waitFor(() => expect(pageIds()).toEqual(['r1', 'r2', 'r3', 'r4', 'p']));
        expect(pageButtons()).toEqual(['2', '3']);
    });

    it('navigateToRowId uses floor(index / pageSize): p2 is on page 2', async () => {
        const api = mount('plain-nav', false);
        await waitFor(() => expect(pageIds()).toContain('r1'));

        api.navigateToRowId('p2');

        await waitFor(() => expect(pageIds()).toEqual(['p1', 'p2', 'r5', 'r6', 'r7']));
        await waitFor(() => expect(scroll).toHaveBeenCalledTimes(1));
        expect(scroll.mock.contexts[0]).toBe(row('p2'));
    });
});
