/**
 * DataTable column resize — workstream Y, lot Y7: C-62 (a drag that did not resize the column) and decision D-Y18 of
 * 15/10 (a finger resizes too).
 *
 * The contract: a drag of a column's resize handle by Δ px, with the mouse or with a finger, on a table laid out
 * `fixed` or `auto`, on a wide screen or a narrow one, changes the width the column is drawn at by Δ ± 4 px.
 *
 * ## The code that keeps it (line numbers of 15/10)
 *
 * - The handle is the last 6 px of a data column's title cell (`span.resize-handle`, DataTableColumnHeader.svelte:175):
 *   `cursor: col-resize`, transparent until the cell is hovered, `touch-action: none` (:306). It answers `pointerdown`
 *   with pointer capture, so the mouse, a finger and a pen take one path (`startResize`, DataTable.svelte:695).
 * - The drag starts from the width the column is drawn at, and the width written is corrected on the cell until the
 *   drawn width matches the pointer (`handleResize` and `fitDrawnWidth`, :717 and :732), within [minWidth ?? 50,
 *   maxWidth ?? 600].
 * - A column whose width differs from its default keeps that width as its `min-width` too (`columnMinWidth`, :775).
 *
 * Was (C-62): the handle answered `mousedown` alone; the drag started from the width the column was GIVEN and wrote
 * only the cell's `width`, which a table laid out `auto` (`.layout-auto`, :1306) reads as a preference. Fitting its
 * box, such a table spread its spare width over the columns and moved the column by a share of the drag; wider than
 * its box, it drew every column at its minimum and moved nothing (the Risk Lab's finding, risk-lab.spec.ts). Only a
 * fixed table wider than its box moved by the drag, and a finger moved no table at all.
 *
 * ## Hosts, read-only on seeded data
 *
 * - **Files, static list** (`FilesTable`, `tableLayout="auto"`, FilesTable.svelte:649): resize is on by default there
 *   (`enableColumnResize`), and nothing has to be built — `populate_mock_data.py` seeds the default avatars and the
 *   preview samples, and list view is the page's default for a fresh browser profile. The import wizard's and the PAC
 *   planner's auto tables run the same DataTable code, behind an owned report or a PAC draft. The column is File name,
 *   250 px given, the widest; its body cells truncate with an ellipsis (`td { max-width: 0; … }`, :1575), so its
 *   minimum is its one-line title.
 * - **Transactions** (fixed layout): the Date column, 110 px given.
 * A dragged width lands in this browser context's localStorage only, discarded with it: nothing reaches the server.
 *
 * ## The tests
 *
 * - **Auto layout, 1280 px**: +80 then −40 px on File name. The table fits its box and shares its spare width; the
 *   −40 px step starts from where the +80 px step left the column, so neither its title nor [50, 600] can clamp it.
 * - **Auto layout, 390 px**: +60 px on File name, the table wider than its box and every column drawn at its minimum;
 *   the table's scroll width must grow with the column. The test's own comment says why this was impossible before.
 * - **The control, fixed layout, 1280 px**: the same two drags on Date, the table wider than its scroll area (a
 *   precondition), the regime where a given width was always drawn as given. It proves the instrument: the handle
 *   found by `cursor: col-resize` (a contract kept on purpose), the drag, the reading.
 * - **Touch, fixed layout, 390 px**: +60 px on Date, with a finger (below).
 *
 * ## Touch: a finger on the same handle, on a phone
 *
 * A phone context — 390 × 844, `isMobile`, `hasTouch` — and a finger: Chromium's DevTools `Input.dispatchTouchEvent`,
 * touchStart on the handle's centre, touchMove in steps, touchEnd. That is the browser's own touch input (touch events,
 * pointer events of type `touch`, the gesture recognition that turns a tap into a click), not `TouchEvent`s dispatched
 * on an element. The handle is in a phone's DOM too, transparent at rest (a finger hovers nothing), and is found as the
 * mouse finds it: `cursor: col-resize` under the title cell's right edge.
 *
 * It guards the input path alone, independent of the layout, so its host is the fixed table wider than its box: there
 * a column is drawn at the width it is given, and the first width `fitDrawnWidth` writes is already exact. A red here
 * is the finger's path (pointer events, capture, `touch-action`), never the layout, which the mouse tests guard. +60 px
 * takes Date from 110 to 170 px, inside [50, 600], and ends the finger about 230 px from the screen's left edge.
 *
 * Was (D-Y18): the handle answered `mousedown` alone, and a sliding finger sends none (Chromium derives compatibility
 * mouse events from a tap only, after the finger lifts), so the width did not move. A slide that starts in the table's
 * horizontal scroll area is also a pan candidate on a phone: a browser that takes the pan cancels the pointer stream
 * (`pointercancel`), and `touch-action` on the handle decides it. This test reads the outcome, not the declaration.
 */
import {expect, test, type Locator, type Page} from '../fixtures/playwright';
import {login, navigateTo} from '../fixtures/auth-helpers';
import {waitForSettled} from '../fixtures/app-events';
import {readOnboardingProgress} from '../fixtures/onboarding-accounts';
import {TEST_USER} from '../fixtures/test-users';

const DESKTOP = {width: 1280, height: 720};
/** A phone (iPhone 12–15), below DataTable's 768 px breakpoint: the screen of the narrow-screen and touch tests. */
const PHONE = {width: 390, height: 844};
/** D-Y18: +80 px, then −40 px, each within ±4 px. */
const GROW_PX = 80;
const SHRINK_PX = -40;
/** The narrow screen, auto layout: one +60 px drag, within the same ±4 px, for the column and for the table. */
const NARROW_GROW_PX = 60;
/** D-Y18, touch: one +60 px slide, within the same ±4 px (the header says why on the fixed table). */
const TOUCH_GROW_PX = 60;
const TOLERANCE_PX = 4;
/** The finger slides in 10 px steps, as a hand does. */
const TOUCH_STEPS = 6;
/** A layout read settles within a frame; the deadline only absorbs a busy lane. */
const GEOMETRY_TIMEOUT_MS = 5_000;
/** A page's data round trip, on a loaded lane. A deadline, never a delay. */
const PAGE_TIMEOUT_MS = 20_000;
const MOVED_BY_THE_DRAG = 'moved by the drag';
const GREW_WITH_THE_COLUMN = 'grew with the column';

test.use({viewport: DESKTOP});
// Login and a page's data share this budget with two drags and their polls.
test.setTimeout(60_000);

const signed = (value: number): string => `${value >= 0 ? '+' : '−'}${Math.abs(value).toFixed(1)}`;

/** Precondition, read back rather than inferred: no onboarding flow is due, so no guide overlay takes the pointer. */
async function expectNoOnboardingDue(page: Page): Promise<void> {
    const due = (await readOnboardingProgress(page)).filter((item) => item.status === 'pending' || item.version < item.current_version).map((item) => item.flow);
    expect(due, `${TEST_USER.username} must be grandfathered completed on every onboarding flow (populate_mock_data _grandfather_onboarding_for_test_users)`).toEqual([]);
}

async function openStaticFilesTable(page: Page): Promise<Locator> {
    await navigateTo(page, '/files?tab=static');
    await expect(page.getByTestId('files-tab-static')).toHaveAttribute('aria-selected', 'true', {timeout: PAGE_TIMEOUT_MS});
    await waitForSettled(page.getByTestId('files-page'), PAGE_TIMEOUT_MS);
    // The list, a DataTable, and not the grid of cards: the default of a fresh browser profile, read back.
    await expect(page.getByTestId('view-mode-list'), 'the static tab must start in list view').toHaveAttribute('aria-pressed', 'true');
    const table = page.getByTestId('files-table-static');
    await expect(table, 'no static files listed: populate_mock_data.py seeds the default avatars and the preview samples').toBeVisible();
    // The uploader column fills in after GET /users/search: `idle` precedes the request, `loading` is the request.
    await expect(table).toHaveAttribute('data-users-state', /^(ready|error)$/, {timeout: PAGE_TIMEOUT_MS});
    return table;
}

async function openTransactionsTable(page: Page): Promise<Locator> {
    await navigateTo(page, '/transactions');
    await waitForSettled(page.getByTestId('transactions-page'), PAGE_TIMEOUT_MS);
    const table = page.getByTestId('tx-table');
    await expect(table).toBeVisible({timeout: PAGE_TIMEOUT_MS});
    return table;
}

/** Text drawn in a font still loading would resize the titles, and with them an auto table's columns, under the drag. */
async function fontsLoaded(page: Page): Promise<void> {
    await page.evaluate(async () => {
        await document.fonts.ready;
    });
}

/** One read of a cell's drawn width. One read, not a retry: a caller polls it. */
async function drawnWidth(header: Locator): Promise<number> {
    return header.evaluate((cell) => cell.getBoundingClientRect().width);
}

/** The cell's width once two consecutive frames agree on it: a baseline read in the middle of a relayout would move. */
async function settledWidth(header: Locator, label: string): Promise<number> {
    let width = Number.NaN;
    await expect
        .poll(
            async () => {
                const [first, second] = await header.evaluate(
                    (cell) =>
                        new Promise<[number, number]>((resolve) => {
                            const before = cell.getBoundingClientRect().width;
                            requestAnimationFrame(() => requestAnimationFrame(() => resolve([before, cell.getBoundingClientRect().width])));
                        }),
                );
                width = second;
                return Math.abs(first - second);
            },
            {message: `${label} never held one width for two frames`, timeout: GEOMETRY_TIMEOUT_MS},
        )
        .toBeLessThan(0.01);
    return width;
}

interface Point {
    x: number;
    y: number;
}

/** How a drag is made: with the mouse, or with a finger. */
interface DragInput {
    name: 'mouse' | 'touch';
    drag: (page: Page, from: Point, dx: number) => Promise<void>;
}

/**
 * A column's resize handle, found by what it is to the pointer: the element under the title cell's right edge (DataTable
 * draws the handle over the cell's last 6 px), inside the cell, with `cursor: col-resize`, and never by a class (the
 * reading of risk-lab.spec.ts, kept as a contract). Returns the handle's centre, where the mouse and the finger press,
 * and why there is no handle to press, if there is none. The cell is scrolled into view first: the point is read off
 * the screen. One read, not a retry.
 */
async function resizeHandle(header: Locator): Promise<{centre: Point; problem: string | null}> {
    await header.scrollIntoViewIfNeeded();
    return header.evaluate((cell) => {
        const box = cell.getBoundingClientRect();
        const probe = {x: box.right - 3, y: box.top + box.height / 2};
        const hit = document.elementFromPoint(probe.x, probe.y);
        if (hit === null || hit === cell || !cell.contains(hit) || getComputedStyle(hit).cursor !== 'col-resize') {
            return {centre: probe, problem: `no element with cursor: col-resize under the title cell's right edge (found: ${hit === null ? 'nothing' : hit.tagName.toLowerCase()})`};
        }
        const own = hit.getBoundingClientRect();
        const centre = {x: own.left + own.width / 2, y: own.top + own.height / 2};
        // The press lands on the centre: the handle must be the element there too, not a neighbour drawn over it.
        if (document.elementFromPoint(centre.x, centre.y) !== hit) return {centre, problem: "the handle's centre is covered by another element"};
        return {centre, problem: null};
    });
}

/** The mouse presses `from`, travels `dx` px in small steps as a hand does, and lets go. */
async function mouseDragBy(page: Page, from: Point, dx: number): Promise<void> {
    await page.mouse.move(from.x, from.y);
    await page.mouse.down();
    await page.mouse.move(from.x + dx / 2, from.y, {steps: 4});
    await page.mouse.move(from.x + dx, from.y, {steps: 4});
    await page.mouse.up();
}

/**
 * A finger presses `from`, slides `dx` px in {@link TOUCH_STEPS} steps and lifts, through Chromium's DevTools
 * `Input.dispatchTouchEvent`: the browser's own touch input, not events dispatched on an element. One finger, id 0
 * throughout; touchEnd carries no point, as the protocol requires: the finger lifts where it last was.
 */
async function touchDragBy(page: Page, from: Point, dx: number): Promise<void> {
    const cdp = await page.context().newCDPSession(page);
    try {
        const finger = (x: number) => [{x, y: from.y, id: 0}];
        await cdp.send('Input.dispatchTouchEvent', {type: 'touchStart', touchPoints: finger(from.x)});
        for (let step = 1; step <= TOUCH_STEPS; step++) {
            await cdp.send('Input.dispatchTouchEvent', {type: 'touchMove', touchPoints: finger(from.x + (dx * step) / TOUCH_STEPS)});
        }
        await cdp.send('Input.dispatchTouchEvent', {type: 'touchEnd', touchPoints: []});
    } finally {
        await cdp.detach();
    }
}

const MOUSE: DragInput = {name: 'mouse', drag: mouseDragBy};
const TOUCH: DragInput = {name: 'touch', drag: touchDragBy};

interface DragStep {
    label: string;
    dx: number;
    input: DragInput;
    /** Soft when another assertion follows, so a red here still lets the next one report its own number. */
    soft: boolean;
}

/** Drag the column's handle by `dx` and assert its title cell's drawn width changed by `dx` ± {@link TOLERANCE_PX}. */
async function expectDragResizes(page: Page, header: Locator, {label, dx, input, soft}: DragStep): Promise<void> {
    const before = await settledWidth(header, label);
    const handle = await resizeHandle(header);
    expect(handle.problem, `${label}'s resize handle is missing`).toBeNull();
    await input.drag(page, handle.centre, dx);
    const verdict = async (): Promise<string> => {
        const after = await drawnWidth(header);
        const moved = after - before;
        return Math.abs(moved - dx) <= TOLERANCE_PX ? MOVED_BY_THE_DRAG : `changed by ${signed(moved)} px (${before.toFixed(1)} → ${after.toFixed(1)} px)`;
    };
    const message = `D-Y18: a ${signed(dx)} px ${input.name} drag of ${label}'s resize handle changes its width by ${signed(dx)} ± ${TOLERANCE_PX} px`;
    const check = soft ? expect.soft : expect;
    await check.poll(verdict, {message, timeout: GEOMETRY_TIMEOUT_MS}).toBe(MOVED_BY_THE_DRAG);
}

/**
 * The table wider than its scroll area (DataTable's `dt-scroll`): no spare room to spread over its columns. A fixed
 * table then draws every column at the width it is given; an auto table, at its minimum.
 */
async function expectWiderThanItsScrollArea(table: Locator, message: string): Promise<void> {
    const spare = await table.getByTestId('dt-scroll').evaluate((scroll) => {
        const grid = scroll.querySelector(':scope > table');
        if (!grid) throw new Error('dt-scroll holds no table');
        return scroll.clientWidth - grid.getBoundingClientRect().width;
    });
    expect(spare, message).toBeLessThan(0);
}

/** One read of the table's scroll width, its scroll area's. One read, not a retry: a caller polls it. */
async function scrollWidth(table: Locator): Promise<number> {
    return table.getByTestId('dt-scroll').evaluate((scroll) => scroll.scrollWidth);
}

/** The table's scroll width once two consecutive frames agree on it, as {@link settledWidth} reads a cell's width. */
async function settledScrollWidth(table: Locator, label: string): Promise<number> {
    const scroll = table.getByTestId('dt-scroll');
    let width = Number.NaN;
    await expect
        .poll(
            async () => {
                const [first, second] = await scroll.evaluate(
                    (element) =>
                        new Promise<[number, number]>((resolve) => {
                            const before = element.scrollWidth;
                            requestAnimationFrame(() => requestAnimationFrame(() => resolve([before, element.scrollWidth])));
                        }),
                );
                width = second;
                return Math.abs(first - second);
            },
            {message: `${label} never held one scroll width for two frames`, timeout: GEOMETRY_TIMEOUT_MS},
        )
        .toBeLessThan(0.01);
    return width;
}

test.describe('DataTable column resize: a drag on a column edge moves it by the drag (Y7, C-62, D-Y18)', () => {
    test.beforeEach(async ({page}) => {
        await login(page, TEST_USER);
        await expectNoOnboardingDue(page);
    });

    test('auto layout, Files static list: +80 px then −40 px on the File name edge change its width by as much', async ({page}) => {
        const table = await openStaticFilesTable(page);
        const header = table.getByTestId('dt-header-filename');
        await expect(header).toBeVisible();
        await expect(table.locator('table', {has: page.getByTestId('dt-header-filename')}), 'FilesTable is no longer laid out auto: this test would not be measuring C-62 any more').toHaveCSS('table-layout', 'auto');
        await fontsLoaded(page);

        await expectDragResizes(page, header, {label: 'the File name column', dx: GROW_PX, input: MOUSE, soft: true});
        await expectDragResizes(page, header, {label: 'the File name column', dx: SHRINK_PX, input: MOUSE, soft: false});
    });

    test('control, fixed layout, Transactions: the same two drags on the Date edge change its width by as much', async ({page}) => {
        const table = await openTransactionsTable(page);
        const header = table.getByTestId('dt-header-date');
        await expect(header).toBeVisible();
        await expect(table.locator('table', {has: page.getByTestId('dt-header-date')}), 'TransactionsTable is no longer laid out fixed: it cannot be the control').toHaveCSS('table-layout', 'fixed');
        await expectWiderThanItsScrollArea(table, 'the control needs the Transactions table wider than its scroll area at 1280 px');
        await fontsLoaded(page);

        await expectDragResizes(page, header, {label: 'the Date column', dx: GROW_PX, input: MOUSE, soft: true});
        await expectDragResizes(page, header, {label: 'the Date column', dx: SHRINK_PX, input: MOUSE, soft: false});
    });

    test.describe('on a narrow screen', () => {
        test.use({viewport: PHONE});

        /**
         * At 390 px the Files table is wider than its box (a precondition), and an auto table wider than its box draws
         * every column at its minimum. The File name column can then widen only through its `min-width`, which a resized
         * column keeps (`columnMinWidth`); the other columns stay at their minimums, so the table, and with it its scroll
         * width, grows by what the column gains. The mouse, not a finger: the input path is the touch test's business.
         *
         * Impossible before the cure (C-62): the drag wrote only the cell's `width`, which an auto table reads as the
         * column's maximum, and its `min-width` stayed `column.minWidth || 60`. In this regime the column was drawn as
         * wide as its title whatever the drag, and the table did not move.
         */
        test('auto layout, Files static list at 390 px, wider than its box: a +60 px drag on the File name edge widens the column by as much, and the table with it', async ({page}) => {
            const table = await openStaticFilesTable(page);
            const header = table.getByTestId('dt-header-filename');
            await expect(header).toBeVisible();
            await expect(table.locator('table', {has: page.getByTestId('dt-header-filename')}), 'FilesTable is no longer laid out auto: this test would no longer guard the auto layout').toHaveCSS('table-layout', 'auto');
            await expectWiderThanItsScrollArea(table, 'the Files table must be wider than its scroll area at 390 px: the regime where an auto table draws every column at its minimum');
            await fontsLoaded(page);

            const before = await settledScrollWidth(table, "the Files table's scroll area");
            await expectDragResizes(page, header, {label: 'the File name column', dx: NARROW_GROW_PX, input: MOUSE, soft: true});
            const verdict = async (): Promise<string> => {
                const after = await scrollWidth(table);
                const grown = after - before;
                return Math.abs(grown - NARROW_GROW_PX) <= TOLERANCE_PX ? GREW_WITH_THE_COLUMN : `changed by ${signed(grown)} px (${before} → ${after} px)`;
            };
            const message = `a column widened by ${signed(NARROW_GROW_PX)} px widens the table's scroll width by ${signed(NARROW_GROW_PX)} ± ${TOLERANCE_PX} px: the other columns are not squeezed back`;
            await expect.poll(verdict, {message, timeout: GEOMETRY_TIMEOUT_MS}).toBe(GREW_WITH_THE_COLUMN);
        });
    });

    test.describe('with a finger, on a phone', () => {
        test.use({viewport: PHONE, isMobile: true, hasTouch: true});
        // Infrastructure, not data: both projects of playwright.config.ts run Chromium, so this never skips there.
        test.skip(({browserName}) => browserName !== 'chromium', 'the finger is a Chromium DevTools command, Input.dispatchTouchEvent');

        test('touch, fixed layout, Transactions at 390 px: a finger drag of +60 px on the Date edge changes its width by as much', async ({page}) => {
            const table = await openTransactionsTable(page);
            const header = table.getByTestId('dt-header-date');
            await expect(header).toBeVisible();
            // The context is the phone the test is about: a touch screen, below DataTable's 768 px breakpoint.
            const device = await page.evaluate(() => ({touchPoints: navigator.maxTouchPoints, phone: window.matchMedia('(max-width: 768px)').matches}));
            expect(device.touchPoints, 'the page must see a touch screen (hasTouch)').toBeGreaterThan(0);
            expect(device.phone, 'the page must be drawn at phone width, below 768 px').toBe(true);
            await expect(table.locator('table', {has: page.getByTestId('dt-header-date')}), 'TransactionsTable is no longer laid out fixed: the touch test would measure the layout, not the finger').toHaveCSS('table-layout', 'fixed');
            await expectWiderThanItsScrollArea(table, 'the touch test needs the Transactions table wider than its scroll area at 390 px');
            await fontsLoaded(page);

            await expectDragResizes(page, header, {label: 'the Date column', dx: TOUCH_GROW_PX, input: TOUCH, soft: false});
        });
    });
});
