/**
 * DataTable at phone width: the two pinned columns scroll with the table — workstream Y, lot Y7: C-38 (PAC defect 2,
 * and the selection column) and decision D-Y17 of 15/10.
 *
 * The contract: below 768 px the DataTable's multi-selection column (left) and its actions column (right) scroll with
 * the table, header and body cells alike, and the header row keeps sticking to the top of the table's scroll area.
 * Wider screens keep both columns pinned (not tested here).
 *
 * ## The code that keeps it (`components/table/DataTable.svelte`, line numbers of 15/10)
 *
 * The pins are `.th-fixed` and `.td-fixed`, `position: sticky` (:1357, :1603), with `left: 0` on the selection cells
 * (`.th-select`, `.td-select`, :1375, :1609) and `right: 0` on a sticky actions header (`.th-actions.th-fixed`, :1385)
 * and its cells (`.td-actions`, :1615). The phone block at the end of the styles (`@media (max-width: 768px)`, :1757)
 * undoes them: the body cells of both columns go `position: static`, and the two header cells lose only their
 * horizontal pin (`left: auto; right: auto`), keeping `position: sticky` and the `top: 0` of `thead.sticky-header th`
 * (:1341), so the header row still sticks.
 *
 * Was (C-38, PAC defect 2), what these tests were written red-first against: the selection column stayed pinned at
 * every width and, scrolled sideways on a phone, covered the start of the first data column. The phone block unpinned
 * the actions BODY cells only: the actions header also matched `thead.sticky-header th { position: sticky }`, whose
 * compiled selector (0,2,2) outranked the block's `.th-actions` (0,2,0), so with `stickyActions`, the default, it kept
 * `right: 0`: «Actions» stayed on the right edge while the ⋮ cells scrolled away.
 *
 * ## Two hosts, read-only on seeded data, each drawing the DataTable itself on a phone (no card view)
 *
 * - **Transactions** (`tx-table`): multi selection, and actions with `stickyActions={false}` (TransactionsTable.svelte:
 *   1010), so its actions header was never pinned horizontally: there the actions test is a guard, and the selection
 *   test is the one written against C-38.
 * - **Files, static list** (`files-table-static`): multi selection, and actions with the default `stickyActions` —
 *   the mechanism of PAC defect 2 (an «Actions» header over no ⋮), reached without building a PAC draft; both of its
 *   tests were written against C-38. List view is the page's default for a fresh browser profile;
 *   `populate_mock_data.py` seeds the default avatars and the preview samples, so the tab is never empty.
 * Each assertion is its own test: a red never hides another. Nothing is written: no row, no setting. The only state a
 * test changes is its own page's scroll position (and, in the stickiness guard, an inline height on its own page).
 *
 * ## Where the sideways scroll stops: half an actions cell short of the far right
 *
 * - More than the selection column's width from the start: a selection column carried by the table is then
 *   entirely out on the left, while a pinned one still sits on the scroll area's left edge.
 * - Not at the far right: there a header pinned with `right: 0` and a cell carried by the table coincide — `sticky`
 *   displaces the header only while its own place lies beyond the right edge — so the far right is the one position
 *   where a pinned actions header looks right. Half a cell short of it, half the row's ⋮ cell is in view, and a pinned
 *   header sits half a cell to the left of it.
 * The table must overflow its scroll area by at least the two pinned columns' width for that position to exist; a
 * precondition says so instead of letting a table that fits pass for one that scrolls.
 *
 * ## Vertical stickiness: what the guard reads
 *
 * `.table-wrapper` sets `overflow-x: auto; overflow-y: visible` (:1286-1288), and the CSS computes `overflow-y` to
 * `auto`: the wrapper is the scroll container a sticky header cell sticks within, in both axes. No consumer bounds its
 * height, so in use it does not scroll vertically: when the PAGE scrolls, the header leaves the screen with the table
 * (a reading of the CSS rules, not a measurement). The stickiness D-Y17 keeps is the header cells' own, inside their
 * scroll area (the coordinator's clarification of 15/10: page-level stickiness is out of its scope), and the phone
 * block is what could break it, e.g. with `position: static` on the two header cells. The guard bounds this page's
 * scroll area to the header and two rows, scrolls it to the bottom, and asserts every header cell, selection and
 * actions included, still sits on the area's top while the body passes under.
 *
 * ## Handles: published for these tests (Y7 prep, no behaviour change)
 *
 * A CSS class is no contract, so DataTable.svelte publishes the scroll area and the four pinned cells:
 *   - `dt-scroll` on `<div class="table-wrapper">` (:990);
 *   - `dt-select-header` on the selection `<th>` (:1002); `dt-actions-header` on the actions `<th>` (:1072);
 *   - `dt-select-cell-{rowId}` on the selection `<td>` (:1142); `dt-actions-cell-{rowId}` on the actions `<td>` (:1193).
 * None starts with a prefix other specs enumerate (`dt-header-`, `dt-row-checkbox-`, `row-actions-`, `dt-footer-`). A
 * handle that goes missing fails the precondition that reads it, by name.
 */
import {expect, test, type Locator, type Page} from '../fixtures/playwright';
import {login, navigateTo} from '../fixtures/auth-helpers';
import {waitForSettled} from '../fixtures/app-events';
import {readOnboardingProgress} from '../fixtures/onboarding-accounts';
import {TEST_USER} from '../fixtures/test-users';

/** A phone (iPhone 12–15), below the 768 px breakpoint of D-Y17 and of the media query. */
const PHONE = {width: 390, height: 844};
const PHONE_QUERY = '(max-width: 768px)';
/** Positions agree to the pixel: sub-pixel layout and border rounding, nothing more. */
const PX = 1;
/** A layout read settles within a frame; the deadline only absorbs a busy lane. */
const GEOMETRY_TIMEOUT_MS = 5_000;
/** A page's data round trip, on a loaded lane. A deadline, never a delay. */
const PAGE_TIMEOUT_MS = 20_000;

/** The handles of the prep step (see the header). */
const SCROLL_AREA = 'dt-scroll';
const SELECT_HEADER = 'dt-select-header';
const ACTIONS_HEADER = 'dt-actions-header';
const selectCellId = (rowId: string): string => `dt-select-cell-${rowId}`;
const actionsCellId = (rowId: string): string => `dt-actions-cell-${rowId}`;

test.use({viewport: PHONE});
// Login and a page's data share this budget with the geometry polls.
test.setTimeout(60_000);

interface Host {
    name: string;
    /** Navigate and wait until the page has loaded its rows. */
    open: (page: Page) => Promise<void>;
    /** The component wrapping exactly one DataTable. */
    table: (page: Page) => Locator;
}

const HOSTS: Host[] = [
    {
        name: 'Transactions page — TransactionsTable (stickyActions={false})',
        open: async (page) => {
            await navigateTo(page, '/transactions');
            await waitForSettled(page.getByTestId('transactions-page'), PAGE_TIMEOUT_MS);
            await expect(page.getByTestId('tx-table')).toBeVisible({timeout: PAGE_TIMEOUT_MS});
        },
        table: (page) => page.getByTestId('tx-table'),
    },
    {
        name: 'Files page, static list — FilesTable (sticky actions, the default)',
        open: async (page) => {
            await navigateTo(page, '/files?tab=static');
            await expect(page.getByTestId('files-tab-static')).toHaveAttribute('aria-selected', 'true', {timeout: PAGE_TIMEOUT_MS});
            await waitForSettled(page.getByTestId('files-page'), PAGE_TIMEOUT_MS);
            // The list, a DataTable, and not the grid of cards: the default of a fresh browser profile, read back.
            await expect(page.getByTestId('view-mode-list'), 'the static tab must start in list view').toHaveAttribute('aria-pressed', 'true');
            const table = page.getByTestId('files-table-static');
            await expect(table, 'no static files listed: populate_mock_data.py seeds the default avatars and the preview samples').toBeVisible();
            // The uploader column fills in after GET /users/search: `idle` precedes the request, `loading` is the request.
            await expect(table).toHaveAttribute('data-users-state', /^(ready|error)$/, {timeout: PAGE_TIMEOUT_MS});
        },
        table: (page) => page.getByTestId('files-table-static'),
    },
];

interface Edges {
    left: number;
    right: number;
    top: number;
    width: number;
}

interface PinnedGeometry {
    scrollLeft: number;
    maxScrollLeft: number;
    /** The scroll area inside its border, in viewport coordinates: what a sticky cell sticks to. */
    area: {left: number; right: number; top: number};
    table: Edges;
    selectHeader: Edges;
    selectCell: Edges;
    actionsHeader: Edges;
    actionsCell: Edges;
}

const px = (value: number): string => value.toFixed(1);

/** Precondition, read back rather than inferred: no onboarding flow is due, so no guide overlays the table. */
async function expectNoOnboardingDue(page: Page): Promise<void> {
    const due = (await readOnboardingProgress(page)).filter((item) => item.status === 'pending' || item.version < item.current_version).map((item) => item.flow);
    expect(due, `${TEST_USER.username} must be grandfathered completed on every onboarding flow (populate_mock_data _grandfather_onboarding_for_test_users)`).toEqual([]);
}

/** The page is drawn as a phone, and the host draws a DataTable with both pinned columns. */
async function expectPhoneDataTable(page: Page, table: Locator): Promise<void> {
    expect(await page.evaluate((query) => window.matchMedia(query).matches, PHONE_QUERY), `the page must be drawn under ${PHONE_QUERY}, the phone rules of DataTable`).toBe(true);
    for (const testId of [SCROLL_AREA, SELECT_HEADER, ACTIONS_HEADER]) {
        await expect(table.getByTestId(testId), `DataTable.svelte must publish data-testid="${testId}" (a Y7 handle)`).toHaveCount(1);
    }
    await expect(table.getByTestId(SCROLL_AREA), 'the host must draw its DataTable on a phone, not cards').toBeVisible();
    await expect(table.getByTestId(SELECT_HEADER), 'the host must draw the multi-selection column').toBeVisible();
    await expect(table.getByTestId(ACTIONS_HEADER), 'the host must draw the actions column').toBeVisible();
}

/**
 * A row carrying both pinned controls: a selection checkbox on the left, a ⋮ on the right.
 *
 * Filtered, then the first of the filtered rows: which one does not matter, every row shares the column geometry under
 * test and nothing is clicked. Its id is read once, and the row is addressed by id from then on.
 */
async function rowWithBothControls(table: Locator): Promise<string> {
    const page = table.page();
    const rows = table
        .locator('tbody tr[data-row-id]')
        .filter({has: page.locator('[data-testid^="dt-row-checkbox-"]')})
        .filter({has: page.locator('[data-testid^="row-actions-"]')});
    const row = rows.first();
    await expect(row, 'no row with both a selection checkbox and a ⋮: the seeded rows must be selectable and carry row actions (populate_mock_data.py)').toBeVisible({timeout: PAGE_TIMEOUT_MS});
    const rowId = await row.getAttribute('data-row-id');
    if (!rowId) throw new Error('The chosen row carries no data-row-id');
    for (const testId of [selectCellId(rowId), actionsCellId(rowId)]) {
        await expect(table.getByTestId(testId), `DataTable.svelte must publish data-testid="${testId}" on the row's pinned cell (a Y7 handle)`).toHaveCount(1);
    }
    return rowId;
}

/** One read of the pinned columns' boxes, the table's and its scroll area's. One read, not a retry: a caller polls it. */
async function readGeometry(table: Locator, rowId: string): Promise<PinnedGeometry> {
    const testIds = {scrollArea: SCROLL_AREA, selectHeader: SELECT_HEADER, selectCell: selectCellId(rowId), actionsHeader: ACTIONS_HEADER, actionsCell: actionsCellId(rowId)};
    return table.evaluate((root, ids) => {
        const byTestId = (testId: string): Element => {
            const found = Array.from(root.querySelectorAll('[data-testid]')).find((element) => element.getAttribute('data-testid') === testId);
            if (!found) throw new Error(`No data-testid="${testId}" in this table`);
            return found;
        };
        const edges = (element: Element): Edges => {
            const box = element.getBoundingClientRect();
            return {left: box.left, right: box.right, top: box.top, width: box.width};
        };
        const scroll = byTestId(ids.scrollArea);
        const grid = scroll.querySelector(':scope > table');
        if (!grid) throw new Error(`${ids.scrollArea} holds no table`);
        const box = scroll.getBoundingClientRect();
        const left = box.left + scroll.clientLeft;
        return {
            scrollLeft: scroll.scrollLeft,
            maxScrollLeft: scroll.scrollWidth - scroll.clientWidth,
            area: {left, right: left + scroll.clientWidth, top: box.top + scroll.clientTop},
            table: edges(grid),
            selectHeader: edges(byTestId(ids.selectHeader)),
            selectCell: edges(byTestId(ids.selectCell)),
            actionsHeader: edges(byTestId(ids.actionsHeader)),
            actionsCell: edges(byTestId(ids.actionsCell)),
        };
    }, testIds);
}

async function scrollSideways(table: Locator, left: number): Promise<void> {
    const scroll = table.getByTestId(SCROLL_AREA);
    await scroll.evaluate((element, x) => {
        element.scrollLeft = x;
    }, left);
    await expect.poll(() => scroll.evaluate((element) => element.scrollLeft), {message: `the table's scroll area must reach scrollLeft ${left}`, timeout: GEOMETRY_TIMEOUT_MS}).toBeCloseTo(left, 0);
}

/** Scroll to the probe position (see the header): half an actions cell short of the far right. */
async function scrollToProbe(table: Locator, rowId: string): Promise<void> {
    await scrollSideways(table, 0);
    const start = await readGeometry(table, rowId);
    const pinnedWidth = start.selectHeader.width + start.actionsHeader.width;
    expect(start.maxScrollLeft, `the table must overflow its phone-width scroll area by at least its two pinned columns (${px(pinnedWidth)} px) to put them to the test`).toBeGreaterThanOrEqual(Math.ceil(pinnedWidth));
    await scrollSideways(table, start.maxScrollLeft - Math.round(start.actionsHeader.width / 2));
}

/** What keeps the actions column from moving with the table. Empty when it moves with it. */
function actionsColumnHeld(geometry: PinnedGeometry, rowId: string): string[] {
    const {actionsHeader: header, actionsCell: cell, table, area} = geometry;
    const held: string[] = [];
    if (Math.abs(header.left - cell.left) > PX) held.push(`the actions header starts at x=${px(header.left)}, the actions cell of row ${rowId} at x=${px(cell.left)}: the header is not over its column`);
    for (const [name, box] of [
        ['header', header],
        [`cell of row ${rowId}`, cell],
    ] as const) {
        if (Math.abs(box.right - table.right) > PX) held.push(`the actions ${name} ends at x=${px(box.right)}, the table at x=${px(table.right)} (scroll area edge x=${px(area.right)}): it is held on screen instead of carried by the table`);
    }
    return held;
}

/** What keeps the selection column on screen once the table has scrolled past it. Empty when it scrolled out. */
function selectionColumnHeld(geometry: PinnedGeometry, rowId: string): string[] {
    const {selectHeader: header, selectCell: cell, area, scrollLeft} = geometry;
    const held: string[] = [];
    for (const [name, box] of [
        ['header', header],
        [`cell of row ${rowId}`, cell],
    ] as const) {
        if (box.right > area.left + PX) held.push(`after a ${px(scrollLeft)} px scroll the selection ${name} still reaches x=${px(box.right)}, ${px(box.right - area.left)} px into the scroll area (left edge x=${px(area.left)}): it covers the first data column`);
    }
    return held;
}

/** Bound the scroll area to the header and two body rows, and scroll it to the bottom. */
async function scrollTableDown(table: Locator): Promise<void> {
    const scroll = table.getByTestId(SCROLL_AREA);
    const room = await scroll.evaluate((element) => {
        const grid = element.querySelector(':scope > table');
        const headerRow = grid instanceof HTMLTableElement ? grid.tHead?.rows.item(0) : null;
        const firstRow = grid instanceof HTMLTableElement ? grid.tBodies.item(0)?.rows.item(0) : null;
        if (!headerRow || !firstRow) throw new Error('The table has no header row or no body row');
        const headerHeight = headerRow.getBoundingClientRect().height;
        // This page's own scroll area, inline: Svelte does not manage this element's style, and the page is discarded with the test.
        (element as HTMLElement).style.maxHeight = `${Math.ceil(headerHeight + 2 * firstRow.getBoundingClientRect().height)}px`;
        return {headerHeight, maxScrollTop: element.scrollHeight - element.clientHeight};
    });
    expect(room.maxScrollTop, 'the table needs more rows than the two it is bounded to, so that its first row can pass under the header').toBeGreaterThan(room.headerHeight + PX);
    await scroll.evaluate((element, top) => {
        element.scrollTop = top;
    }, room.maxScrollTop);
    await expect.poll(() => scroll.evaluate((element) => element.scrollTop), {message: `the table's scroll area must reach scrollTop ${room.maxScrollTop}`, timeout: GEOMETRY_TIMEOUT_MS}).toBeCloseTo(room.maxScrollTop, 0);
}

/**
 * Header cells that left the top of the scroll area. Empty when the whole header row is on it — and only then, if the
 * body really scrolled under it: the first body row, the first to pass under the header, must be above the area's top.
 */
async function headerOffTop(table: Locator): Promise<string[]> {
    return table.getByTestId(SCROLL_AREA).evaluate((element) => {
        const grid = element.querySelector(':scope > table');
        const headerRow = grid instanceof HTMLTableElement ? grid.tHead?.rows.item(0) : null;
        if (!(grid instanceof HTMLTableElement) || !headerRow) throw new Error('The scroll area holds no table with a header row');
        const top = element.getBoundingClientRect().top + element.clientTop;
        const off: string[] = [];
        Array.from(headerRow.cells).forEach((cell, index) => {
            const at = cell.getBoundingClientRect().top;
            if (Math.abs(at - top) > 1) off.push(`${cell.getAttribute('data-testid') ?? `header cell ${index + 1}`} is at y=${at.toFixed(1)}, the top of the scroll area at y=${top.toFixed(1)}`);
        });
        const firstRowTop = grid.tBodies.item(0)?.rows.item(0)?.getBoundingClientRect().top ?? Number.NaN;
        if (!(firstRowTop < top - 1)) off.push(`the body did not scroll under the header (scrollTop ${element.scrollTop}, first body row at y=${firstRowTop.toFixed(1)})`);
        return off;
    });
}

test.describe('DataTable at phone width: the selection and actions columns scroll with the table, the header still sticks (Y7, D-Y17)', () => {
    for (const host of HOSTS) {
        test.describe(host.name, () => {
            test.beforeEach(async ({page}) => {
                await login(page, TEST_USER);
                await expectNoOnboardingDue(page);
                await host.open(page);
                await expectPhoneDataTable(page, host.table(page));
            });

            test('the actions column, header and cells alike, scrolls with the table', async ({page}) => {
                const table = host.table(page);
                const rowId = await rowWithBothControls(table);
                await scrollToProbe(table, rowId);
                await expect
                    .poll(async () => actionsColumnHeld(await readGeometry(table, rowId), rowId), {
                        message: 'D-Y17: below 768 px the actions header and its cells scroll with the table, over the same column',
                        timeout: GEOMETRY_TIMEOUT_MS,
                    })
                    .toEqual([]);
            });

            test('the selection column, header and cells alike, scrolls out with the table instead of covering the first data column', async ({page}) => {
                const table = host.table(page);
                const rowId = await rowWithBothControls(table);
                await scrollToProbe(table, rowId);
                await expect
                    .poll(async () => selectionColumnHeld(await readGeometry(table, rowId), rowId), {
                        message: 'D-Y17: below 768 px the selection header and its cells scroll out with the table',
                        timeout: GEOMETRY_TIMEOUT_MS,
                    })
                    .toEqual([]);
            });

            test('guard: the header row, selection and actions headers included, still sticks to the top of the table scroll area', async ({page}) => {
                const table = host.table(page);
                await scrollTableDown(table);
                await expect
                    .poll(() => headerOffTop(table), {
                        message: 'D-Y17: the header row keeps sticking to the top while the body scrolls under it',
                        timeout: GEOMETRY_TIMEOUT_MS,
                    })
                    .toEqual([]);
            });
        });
    }
});
