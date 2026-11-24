// @vitest-environment jsdom
/**
 * DataTable — the selection panel (plan 77, SEL-A; the developer's Q-SEL-6, Q-SEL-8, Q-SEL-13, Q-SEL-15 of 19/11/2026).
 *
 * With `selectionPanel`, a table draws its bulk actions (`bulkActions`) itself, through the rule of
 * `resolveSelectionAction` (hidden / off with its reason / on, always with the number):
 * - **the bar at the top** (`dt-selection-top`): the hint while nothing is selected, the actions with a selection;
 * - **the dock** at the bottom (`dt-dock`): the actions come down into it only while the top of the table is out of
 *   view, above the pagination when the table pages. The actions are in one place at a time, so their testids stay
 *   unique. The pagination is one instance throughout: it is never remounted when the actions come and go.
 * - Without `selectionPanel` nothing changes: `bulkActions` draws nothing (FilesTable and the Bulk pass it today).
 *
 * jsdom has no IntersectionObserver: a stub stands in, and the test says when the top leaves the view.
 * Kept in a file of its own, as `DataTable.opensPage.test.ts` is, because other workstreams edit `DataTable.test.ts`.
 */
import {afterEach, beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';
import {Link2, Plus, Trash2} from 'lucide-svelte';
import {fireEvent, render, screen, setupI18n, waitFor} from '$test/component';
import DataTable from './DataTable.svelte';
import ExternalPagerFixture from '$test/harness/DataTableExternalPagerHarness.svelte';
import SectionHeadFixture from '$test/harness/DataTableSectionHeadHarness.svelte';
import type {BulkAction, ColumnDef} from './types';

interface Row {
    id: string;
    kind: 'unique' | 'none';
}

const COLUMNS: ColumnDef<Row>[] = [{id: 'kind', header: 'Kind', type: 'text', cell: (r) => r.kind, getValue: (r) => r.kind}];
const rowsOf = (n: number): Row[] => Array.from({length: n}, (_, i) => ({id: `r${i + 1}`, kind: i % 2 === 0 ? 'unique' : 'none'}));

/** The stub: every observer the table creates, and a way to say whether its target is in view. */
const observers: Array<{callback: IntersectionObserverCallback; targets: Element[]; options?: IntersectionObserverInit}> = [];
function setTopInView(inView: boolean) {
    for (const observer of observers) {
        observer.callback(
            observer.targets.map((target) => ({isIntersecting: inView, target}) as IntersectionObserverEntry),
            {} as IntersectionObserver,
        );
    }
}

beforeAll(async () => {
    await setupI18n();
});

beforeEach(() => {
    observers.length = 0;
    vi.stubGlobal(
        'IntersectionObserver',
        class {
            private entry: {callback: IntersectionObserverCallback; targets: Element[]; options?: IntersectionObserverInit};
            constructor(callback: IntersectionObserverCallback, options?: IntersectionObserverInit) {
                this.entry = {callback, targets: [], options};
                observers.push(this.entry);
            }
            observe(target: Element) {
                this.entry.targets.push(target);
            }
            unobserve() {}
            disconnect() {
                this.entry.targets = [];
            }
            takeRecords() {
                return [];
            }
        },
    );
});

afterEach(() => {
    vi.unstubAllGlobals();
});

function actions() {
    const link = vi.fn();
    const create = vi.fn();
    const remove = vi.fn();
    const list: BulkAction<Row>[] = [
        {id: 'link', icon: Link2, label: 'Link', primary: true, appliesTo: (row) => row.kind === 'unique', onClick: link},
        {id: 'create', icon: Plus, label: 'Create', appliesTo: (row) => row.kind === 'none', onClick: create},
        {id: 'delete', icon: Trash2, label: 'Delete', variant: 'danger', requireConfirm: true, onClick: remove},
    ];
    return {link, create, remove, list};
}

function mount(rows: Row[], extra: Record<string, unknown> = {}) {
    const onSelectionChange = vi.fn();
    render(DataTable, {
        props: {data: rows, columns: COLUMNS, getRowId: (r: Row) => r.id, storageKey: `sel-panel-${Math.random()}`, enableActions: false, defaultPageSize: 10, onSelectionChange, ...extra} as never,
    });
    return {onSelectionChange};
}

const tick = (id: string) => fireEvent.click(screen.getByTestId(`dt-row-checkbox-${id}`));

describe('without selectionPanel nothing changes', () => {
    it('bulkActions draws no bar, no dock and no hint', async () => {
        const {list} = actions();
        mount(rowsOf(4), {bulkActions: list});
        await tick('r1');
        expect(screen.queryByTestId('dt-selection-top')).toBeNull();
        expect(screen.queryByTestId('dt-dock')).toBeNull();
        expect(screen.queryByTestId('selection-toolbar')).toBeNull();
    });
});

describe('the bar at the top', () => {
    it('holds the hint while nothing is selected, the caller’s own when given', () => {
        const {list} = actions();
        mount(rowsOf(4), {bulkActions: list, selectionPanel: true, selectionHint: 'Tick the rows'});
        const top = screen.getByTestId('dt-selection-top');
        expect(top.querySelector('[data-testid="selection-toolbar-hint"]')?.textContent?.trim()).toBe('Tick the rows');
        expect(screen.queryByTestId('toolbar-action-link')).toBeNull();
    });

    it('with a selection: each action the rule shows, with its number, and only those', async () => {
        const {list} = actions();
        mount(rowsOf(4), {bulkActions: list, selectionPanel: true});
        await tick('r1');
        await tick('r3');
        const bar = screen.getByTestId('selection-toolbar');
        expect(bar).toHaveAttribute('data-variant', 'top');
        expect(bar).toHaveAttribute('data-selected-count', '2');
        expect(screen.getByTestId('toolbar-action-link-count').textContent?.trim()).toBe('2');
        expect(screen.queryByTestId('toolbar-action-create')).toBeNull();
        expect(screen.getByTestId('toolbar-action-delete-count').textContent?.trim()).toBe('2');

        await tick('r2');
        expect(screen.getByTestId('toolbar-action-link-count').textContent?.trim()).toBe('2');
        expect(screen.getByTestId('toolbar-action-create-count').textContent?.trim()).toBe('1');
        expect(screen.getByTestId('toolbar-action-delete-count').textContent?.trim()).toBe('3');
    });

    it('an action acts on its own rows only', async () => {
        const {list, link, create} = actions();
        mount(rowsOf(4), {bulkActions: list, selectionPanel: true});
        await tick('r1');
        await tick('r2');
        await tick('r3');
        await fireEvent.click(screen.getByTestId('toolbar-action-link'));
        expect(link).toHaveBeenCalledWith([expect.objectContaining({id: 'r1'}), expect.objectContaining({id: 'r3'})]);
        await fireEvent.click(screen.getByTestId('toolbar-action-create'));
        expect(create).toHaveBeenCalledWith([expect.objectContaining({id: 'r2'})]);
    });

    it('an action that asks for a confirmation lists and acts on its own rows', async () => {
        const remove = vi.fn();
        const list: BulkAction<Row>[] = [{id: 'delete', icon: Trash2, label: 'Delete', variant: 'danger', requireConfirm: true, appliesTo: (row) => row.kind === 'none', onClick: remove}];
        mount(rowsOf(4), {bulkActions: list, selectionPanel: true});
        await tick('r1');
        await tick('r2');
        await fireEvent.click(screen.getByTestId('toolbar-action-delete'));
        await fireEvent.click(await screen.findByTestId('confirm-modal-confirm'));
        expect(remove).toHaveBeenCalledWith([expect.objectContaining({id: 'r2'})]);
    });

    it('the confirmation takes the action’s own button text (81 U21) and keeps «Confirm» without one', async () => {
        const list: BulkAction<Row>[] = [
            {id: 'fetch', icon: Trash2, label: 'Fetch', requireConfirm: true, confirmText: () => 'Fetch them', onClick: vi.fn()},
            {id: 'plain', icon: Trash2, label: 'Plain', requireConfirm: true, onClick: vi.fn()},
        ];
        mount(rowsOf(4), {bulkActions: list, selectionPanel: true});
        await tick('r1');
        await fireEvent.click(screen.getByTestId('toolbar-action-fetch'));
        expect(await screen.findByTestId('confirm-modal-confirm')).toHaveTextContent('Fetch them');
        await fireEvent.click(screen.getByTestId('confirm-modal-cancel'));
        await tick('r1');
        await tick('r1');
        await fireEvent.click(screen.getByTestId('toolbar-action-plain'));
        expect(await screen.findByTestId('confirm-modal-confirm')).not.toHaveTextContent('Fetch them');
    });

    it('the count button clears the whole table’s selection', async () => {
        const {list} = actions();
        const {onSelectionChange} = mount(rowsOf(4), {bulkActions: list, selectionPanel: true});
        await tick('r1');
        await fireEvent.click(screen.getByTestId('selection-toolbar-clear'));
        expect(onSelectionChange).toHaveBeenLastCalledWith([]);
        expect(screen.getByTestId('dt-row-checkbox-r1')).toHaveAttribute('data-state', 'unchecked');
    });
});

describe('the dock at the bottom', () => {
    it('the top in view: the dock holds no action, only the pagination when the table pages', async () => {
        const {list} = actions();
        mount(rowsOf(14), {bulkActions: list, selectionPanel: true});
        await tick('r1');
        setTopInView(true);
        await waitFor(() => expect(screen.getByTestId('dt-dock')).toHaveAttribute('data-actions', 'false'));
        expect(screen.getByTestId('data-table-pagination')).toBeInTheDocument();
        expect(screen.getAllByTestId('selection-toolbar')).toHaveLength(1);
    });

    it('the top out of view: the actions come down into the dock, above the same pagination', async () => {
        const {list} = actions();
        mount(rowsOf(14), {bulkActions: list, selectionPanel: true});
        await tick('r1');
        const pagination = screen.getByTestId('data-table-pagination');
        setTopInView(false);
        await waitFor(() => expect(screen.getByTestId('dt-dock')).toHaveAttribute('data-actions', 'true'));
        const bars = screen.getAllByTestId('selection-toolbar');
        expect(bars).toHaveLength(1);
        expect(bars[0]).toHaveAttribute('data-variant', 'dock');
        expect(screen.getAllByTestId('toolbar-action-link')).toHaveLength(1);
        expect(screen.getByTestId('data-table-pagination')).toBe(pagination);

        setTopInView(true);
        await waitFor(() => expect(screen.getByTestId('dt-dock')).toHaveAttribute('data-actions', 'false'));
        expect(screen.getByTestId('selection-toolbar')).toHaveAttribute('data-variant', 'top');
        expect(screen.getByTestId('data-table-pagination')).toBe(pagination);
    });

    it('no pagination and the top in view: no dock at all', async () => {
        const {list} = actions();
        mount(rowsOf(4), {bulkActions: list, selectionPanel: true});
        await tick('r1');
        setTopInView(true);
        await waitFor(() => expect(screen.queryByTestId('dt-dock')).toBeNull());
    });

    it('no pagination and the top out of view: the dock with the actions only', async () => {
        const {list} = actions();
        mount(rowsOf(4), {bulkActions: list, selectionPanel: true});
        await tick('r1');
        setTopInView(false);
        await waitFor(() => expect(screen.getByTestId('dt-dock')).toHaveAttribute('data-actions', 'true'));
        expect(screen.queryByTestId('data-table-pagination')).toBeNull();
    });

    it('nothing selected and the top out of view: no action comes down', async () => {
        const {list} = actions();
        mount(rowsOf(14), {bulkActions: list, selectionPanel: true});
        setTopInView(false);
        await waitFor(() => expect(screen.getByTestId('dt-dock')).toHaveAttribute('data-actions', 'false'));
        expect(screen.queryByTestId('toolbar-action-link')).toBeNull();
    });

    it('watches the top of the table', () => {
        const {list} = actions();
        mount(rowsOf(4), {bulkActions: list, selectionPanel: true});
        expect(observers.some((observer) => observer.targets.includes(screen.getByTestId('dt-selection-top')))).toBe(true);
    });
});

/**
 * 77 SEL-B: a table whose pages are cut outside it (the transactions grouped with their charges) hands its own pager to
 * the table, which hosts it where its pager would be: in the dock, under the actions, and the same instance throughout.
 */
describe('an external pager (77 SEL-B)', () => {
    it('sits where the table’s own pager would, and docks under the actions when they come down', async () => {
        const {list} = actions();
        render(ExternalPagerFixture, {props: {rows: rowsOf(4), bulkActions: list as never}});
        const pager = screen.getByTestId('data-table-pagination');
        expect(pager).toHaveAttribute('data-docked', 'false');
        await tick('r1');
        setTopInView(false);
        await waitFor(() => expect(screen.getByTestId('dt-dock')).toHaveAttribute('data-actions', 'true'));
        expect(screen.getByTestId('data-table-pagination')).toBe(pager);
        expect(pager).toHaveAttribute('data-docked', 'true');
    });
});

/**
 * 77 SEL-D (Q-SEL-8): a table inside a section (a form, a window) puts its bar in the section's head, beside the title
 * and the section's own buttons. The head is the caller's (`selectionHead`), drawn by the table even when the selection
 * is off, so the section keeps one head. While nothing is selected the head stays as it was: no hint, unless the caller
 * gives one. The table watches the whole head: when it leaves the view, the actions come down into the dock.
 */
describe('the bar in a section head (77 SEL-D)', () => {
    const within = (testId: string, inner: string) => screen.getByTestId(testId).querySelector(`[data-testid="${inner}"]`);

    it('with a selection the bar sits in the head, between the title and the section’s button', async () => {
        const {list} = actions();
        render(SectionHeadFixture, {props: {rows: rowsOf(4), bulkActions: list as never}});
        await tick('r1');
        const bar = within('section-head', 'selection-toolbar');
        expect(bar).not.toBeNull();
        expect(bar).toHaveAttribute('data-variant', 'top');
        expect(screen.getAllByTestId('selection-toolbar')).toHaveLength(1);
        const order = [...screen.getByTestId('section-head').querySelectorAll('[data-testid]')].map((el) => el.getAttribute('data-testid'));
        expect(order.indexOf('section-title')).toBeLessThan(order.indexOf('selection-toolbar'));
        expect(order.indexOf('selection-toolbar')).toBeLessThan(order.indexOf('section-add'));
    });

    it('nothing selected: the head as it was, with no hint', () => {
        const {list} = actions();
        render(SectionHeadFixture, {props: {rows: rowsOf(4), bulkActions: list as never}});
        expect(screen.getByTestId('section-title')).toBeInTheDocument();
        expect(screen.getByTestId('section-add')).toBeInTheDocument();
        expect(screen.queryByTestId('selection-toolbar-hint')).toBeNull();
        expect(screen.queryByTestId('selection-toolbar')).toBeNull();
    });

    it('nothing selected, with the caller’s hint: the hint sits in the head', () => {
        const {list} = actions();
        render(SectionHeadFixture, {props: {rows: rowsOf(4), bulkActions: list as never, selectionHint: 'Tick the rows'}});
        expect(within('section-head', 'selection-toolbar-hint')?.textContent?.trim()).toBe('Tick the rows');
    });

    it('the selection off (read only): the head is still drawn, without a bar', () => {
        const {list} = actions();
        render(SectionHeadFixture, {props: {rows: rowsOf(4), bulkActions: list as never, enableSelection: false}});
        expect(screen.getByTestId('section-title')).toBeInTheDocument();
        expect(screen.getByTestId('section-add')).toBeInTheDocument();
        expect(screen.queryByTestId('dt-row-checkbox-r1')).toBeNull();
        expect(screen.queryByTestId('dt-selection-top')).toBeNull();
    });

    it('the panel off: the head is still drawn', () => {
        const {list} = actions();
        render(SectionHeadFixture, {props: {rows: rowsOf(4), bulkActions: list as never, selectionPanel: false}});
        expect(screen.getByTestId('section-head')).toBeInTheDocument();
    });

    it('watches the whole head; out of view, the actions come down into the dock above the same pager', async () => {
        const {list} = actions();
        render(SectionHeadFixture, {props: {rows: rowsOf(8), bulkActions: list as never, enablePagination: true}});
        const top = screen.getByTestId('dt-selection-top');
        expect(top.contains(screen.getByTestId('section-head'))).toBe(true);
        expect(observers.some((observer) => observer.targets.includes(top))).toBe(true);
        await tick('r1');
        const pagination = screen.getByTestId('data-table-pagination');
        setTopInView(false);
        await waitFor(() => expect(screen.getByTestId('dt-dock')).toHaveAttribute('data-actions', 'true'));
        expect(screen.getAllByTestId('selection-toolbar')).toHaveLength(1);
        expect(screen.getByTestId('selection-toolbar')).toHaveAttribute('data-variant', 'dock');
        expect(within('section-head', 'selection-toolbar')).toBeNull();
        expect(screen.getByTestId('data-table-pagination')).toBe(pagination);
    });

    it('in a head the bar takes the compact form when the head is narrow; each action names its number and opens its name on focus (77 SEL-D2)', async () => {
        const {list} = actions();
        render(SectionHeadFixture, {props: {rows: rowsOf(4), bulkActions: list as never}});
        await tick('r1');
        // The compact form is a container query on the head (`dt-head`): only a browser measures it (e2e
        // `asset-profile-edit`, the head's height with and without a selection). Here, the bar says it is in a head.
        expect(within('section-head', 'selection-toolbar')).toHaveAttribute('data-in-head', 'true');
        const link = screen.getByTestId('toolbar-action-link');
        expect(link).toHaveAttribute('aria-label', 'Link, 1');
        expect(screen.queryByTestId('tooltip-content')).toBeNull();
        link.focus();
        expect((await screen.findByTestId('tooltip-content')).textContent?.trim()).toBe('Link');
        link.blur();
        await waitFor(() => expect(screen.queryByTestId('tooltip-content')).toBeNull());
    });

    it('a bar at the top of a table, not in a head, keeps its own form', async () => {
        const {list} = actions();
        mount(rowsOf(4), {bulkActions: list, selectionPanel: true});
        await tick('r1');
        expect(screen.getByTestId('selection-toolbar')).not.toHaveAttribute('data-in-head');
    });

    it('the count button in the head clears the ticks of the table', async () => {
        const {list} = actions();
        render(SectionHeadFixture, {props: {rows: rowsOf(4), bulkActions: list as never}});
        await tick('r1');
        await tick('r2');
        await fireEvent.click(screen.getByTestId('selection-toolbar-clear'));
        expect(screen.getByTestId('dt-row-checkbox-r1')).toHaveAttribute('data-state', 'unchecked');
        expect(screen.getByTestId('dt-row-checkbox-r2')).toHaveAttribute('data-state', 'unchecked');
        expect(screen.queryByTestId('selection-toolbar')).toBeNull();
    });
});
