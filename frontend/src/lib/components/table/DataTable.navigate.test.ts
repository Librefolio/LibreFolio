// @vitest-environment jsdom
/**
 * DataTable — `navigateToRowId(rowId, {scroll, highlight})` (B8, pinned red-first).
 *
 * `navigateToRowId` takes a table to the page that holds a row, marks the row and scrolls it to the middle of the view with a
 * smooth `scrollIntoView`. Thirteen callers use it that way and none had a test pinning the scroll, so the default is pinned
 * here BEFORE the option that turns it off exists (developer, 31/10/2026, D-B8b): the risk table paginates, a click on a point of
 * the chart selects its row, and when the row is on another page the table must change page WITHOUT moving the view, which sits
 * on the chart under the table.
 *
 * - no options: the page changes, the row is highlighted and `scrollIntoView({behavior: 'smooth', block: 'center'})` is called on
 *   the row — exactly as before the option existed;
 * - `{scroll: false}`: the page changes and the row is highlighted, and nothing scrolls;
 * - `{highlight: false}`: the page changes and the view scrolls, and no row is highlighted (a caller that selects the row marks it
 *   already);
 * - the options are additive: an empty object is the default.
 *
 * Kept in a file of its own, as `DataTable.rowOrder.test.ts` is, because other workstreams edit `DataTable.test.ts`.
 */
import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';
import {render, screen, setupI18n, waitFor} from '$test/component';
import DataTable from './DataTable.svelte';
import type {ColumnDef} from './types';

interface Row {
    id: string;
    name: string;
}

const COLUMNS: ColumnDef<Row>[] = [{id: 'name', header: 'Name', type: 'text', cell: (r) => r.name, getValue: (r) => r.name}];

function rows(n: number): Row[] {
    return Array.from({length: n}, (_, i) => ({id: `r${i + 1}`, name: `Name ${i + 1}`}));
}

type Api = {navigateToRowId: (id: string, options?: {scroll?: boolean; highlight?: boolean}) => void};

function mount(key: string): Api {
    const {component} = render(DataTable, {
        data: rows(25),
        columns: COLUMNS as ColumnDef<unknown>[],
        getRowId: ((r: Row) => r.id) as (row: unknown) => string,
        storageKey: key,
        defaultPageSize: 10,
    });
    return component as unknown as Api;
}

const pageIds = () => Array.from(document.querySelectorAll('tbody tr[data-row-id]')).map((tr) => tr.getAttribute('data-row-id'));
const row = (id: string) => document.querySelector(`tbody tr[data-row-id="${id}"]`);

let scroll: ReturnType<typeof vi.fn>;

beforeEach(async () => {
    await setupI18n();
    scroll = vi.fn();
    Element.prototype.scrollIntoView = scroll as unknown as Element['scrollIntoView'];
});

afterEach(() => {
    document.body.innerHTML = '';
});

describe('DataTable.navigateToRowId — what it does by default (pinned before the options)', () => {
    it('changes page, highlights the row and scrolls it to the middle, smoothly', async () => {
        const api = mount('nav-default');
        expect(pageIds()).not.toContain('r23');

        api.navigateToRowId('r23');

        await waitFor(() => expect(pageIds()).toContain('r23'));
        expect(row('r23')).toHaveAttribute('data-highlighted', 'true');
        await waitFor(() => expect(scroll).toHaveBeenCalledTimes(1));
        expect(scroll).toHaveBeenCalledWith({behavior: 'smooth', block: 'center'});
        expect(scroll.mock.contexts[0], 'the scroll is asked of the row itself, not of another element').toBe(row('r23'));
    });

    it('an empty options object is the default', async () => {
        const api = mount('nav-empty-options');

        api.navigateToRowId('r23', {});

        await waitFor(() => expect(row('r23')).toHaveAttribute('data-highlighted', 'true'));
        await waitFor(() => expect(scroll).toHaveBeenCalledTimes(1));
    });
});

describe('DataTable.navigateToRowId — the options (D-B8b)', () => {
    it('{scroll: false} changes the page and highlights the row, and the view does not move', async () => {
        const api = mount('nav-no-scroll');

        api.navigateToRowId('r23', {scroll: false});

        await waitFor(() => expect(pageIds()).toContain('r23'));
        expect(row('r23')).toHaveAttribute('data-highlighted', 'true');
        // The scroll, when asked, is scheduled after the page is drawn, so an absence read now could be only "not yet". A default
        // navigation asked AFTER this one is the barrier: its scroll queues behind any scroll this one would have queued, so when
        // it has landed, a scroll of the first would have landed too.
        api.navigateToRowId('r5');
        await waitFor(() => expect(scroll).toHaveBeenCalled());
        expect(scroll, 'the scroll of {scroll: false} still happened').toHaveBeenCalledTimes(1);
        expect(scroll.mock.contexts[0], "the only scroll is the barrier navigation's").toBe(row('r5'));
    });

    it('{highlight: false} changes the page and scrolls, and marks nothing', async () => {
        const api = mount('nav-no-highlight');

        api.navigateToRowId('r23', {highlight: false});

        await waitFor(() => expect(pageIds()).toContain('r23'));
        await waitFor(() => expect(scroll).toHaveBeenCalledTimes(1));
        expect(document.querySelector('tbody tr[data-highlighted="true"]')).toBeNull();
    });
});
