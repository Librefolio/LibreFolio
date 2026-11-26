/**
 * The standard button in a real browser (project 85, BTN-0), on the Button Lab: `/button-lab`, a debug-build page with
 * every case of the button and a log of what happened (`lab-log-entry`, its event in `data-event`). The test server
 * always serves a debug build, so the page is there; a release build answers it with a 404.
 *
 * Mobile project (Chromium with touch): a finger is Chromium's DevTools `Input.dispatchTouchEvent` — the browser's own
 * touch input, so the pointer events carry `pointerType` touch and the browser decides whether a click follows.
 *   - a long press on an icon shows its name and does not act; a tap acts;
 *   - a long press on a button inside a table row shows the button's name and does not select the row (85 D6), while a
 *     long press on a cell of the same row selects it (the positive control);
 *   - a tap on a button off with a reason shows the reason and runs nothing;
 *   - a button's name is a compact box (< 288 px, the phone width of an info tooltip); the widths of a name, a name
 *     with its reason and a help are annotated (`tooltip-widths`);
 *   - a finger's row menu opens to the left of the finger and above it near the row's right end, centred (or held at
 *     the viewport's edge) near its left end, and ends with «Copy cell» then «Copy row» after every row action.
 *     The `contextmenu` of the long press: Chromium is given the hold to fire its own (Android's path); when it does
 *     not, the one a phone fires is dispatched at the same point while the finger is still down, and the test says
 *     which in the annotation `contextmenu-source` (and on stdout). The placement and the items are the same either way.
 * Desktop project: a click acts and no name follows it for 700 ms; a mouse rest shows an icon's name; a right click
 * opens a pointer's menu at the click with no copy item; the auto buttons' words show in a 900 px box and hide in a
 * 240 px one (`data-labels`, the toolbar's own `showActionLabels`).
 *
 * The clipboard's content is never read (that needs a permission): «Copy row» is proved by its `table.row.copied` event.
 *
 * Absence of an action is read behind a barrier: after the gesture under test, a tap on another icon must land in the
 * log first, so «no `action: edit`» means it never came, not that it had not arrived yet.
 *
 * The texts asserted (`Edit`, `Sync prices`, the reason, the log events) are props the Lab passes in English, a
 * developer's bench never translated: none comes from the catalogue. No API is called, nothing is written.
 */
import {expect, test, type Locator, type Page} from '../fixtures/playwright';
import {eventSeq, waitForEvent} from '../fixtures/app-events';

const DEBUG_ONLY = 'the Button Lab is served by the debug build only';

async function openLab(page: Page): Promise<void> {
    await page.goto('/button-lab');
    await expect(page.getByTestId('button-lab'), `the test server must serve a debug build (dev.py server --test builds one): ${DEBUG_ONLY}`).toBeVisible({timeout: 30_000});
}

const logEntries = (page: Page, event: string) => page.locator(`[data-testid="lab-log-entry"][data-event="${event}"]`);
const tooltip = (page: Page) => page.getByTestId('tooltip-content');

/**
 * The viewport centre of `locator`, brought into the middle of the viewport first: a CDP touch goes to a viewport
 * point, and a point below the fold (or under the sticky log) touches nothing. The point is hit-tested before use.
 */
async function centreOf(locator: Locator): Promise<{x: number; y: number}> {
    await expect(locator).toBeVisible();
    await locator.evaluate((el) => el.scrollIntoView({block: 'center', inline: 'center'}));
    const box = await locator.boundingBox();
    if (!box) throw new Error('the element has no box');
    const point = {x: box.x + box.width / 2, y: box.y + box.height / 2};
    expect(await locator.evaluate((el, p) => el.contains(document.elementFromPoint(p.x, p.y)), point), `the point ${point.x},${point.y} must touch the element itself`).toBe(true);
    return point;
}

/**
 * A finger rests on `locator` until `held` resolves (the condition the long press must produce), then lifts. Chromium's
 * own touch input: one finger, id 0; touchEnd carries no point, as the protocol requires.
 */
async function longPress(page: Page, locator: Locator, held: () => Promise<void>): Promise<void> {
    await pressAt(page, await centreOf(locator), held);
}

/** {@link longPress} at an explicit viewport point. */
async function pressAt(page: Page, {x, y}: {x: number; y: number}, held: () => Promise<void>): Promise<void> {
    const cdp = await page.context().newCDPSession(page);
    try {
        await cdp.send('Input.dispatchTouchEvent', {type: 'touchStart', touchPoints: [{x, y, id: 0}]});
        await held();
        await cdp.send('Input.dispatchTouchEvent', {type: 'touchEnd', touchPoints: []});
    } finally {
        await cdp.detach();
    }
}

type ProbeWindow = Window & {__lfContextMenus?: number};

/**
 * A finger's long press at `point` that opens the row menu. Chromium is first given the chance to fire its own
 * `contextmenu` for the long press (the Android path); when it does not within the hold, the `contextmenu` a phone
 * would fire is dispatched at the same point while the finger is still down (the table reads a `contextmenu` during a
 * touch as a finger's). Which path served is returned, and annotated by the caller: the placement under test is the
 * same either way.
 */
async function fingerRowMenu(page: Page, point: {x: number; y: number}): Promise<'native' | 'synthetic'> {
    await page.evaluate(() => {
        const w = window as ProbeWindow;
        w.__lfContextMenus = 0;
        window.addEventListener('contextmenu', () => (w.__lfContextMenus = (w.__lfContextMenus ?? 0) + 1), {capture: true});
    });
    let source: 'native' | 'synthetic' = 'native';
    await pressAt(page, point, async () => {
        const native = await expect
            .poll(() => page.evaluate(() => (window as ProbeWindow).__lfContextMenus ?? 0), {timeout: 1_500})
            .toBeGreaterThan(0)
            .then(
                () => true,
                () => false,
            );
        if (!native) {
            source = 'synthetic';
            await page.evaluate(({x, y}) => {
                const target = document.elementFromPoint(x, y);
                if (!target) throw new Error(`nothing at ${x},${y}`);
                target.dispatchEvent(new MouseEvent('contextmenu', {bubbles: true, cancelable: true, clientX: x, clientY: y}));
            }, point);
        }
        await expect(page.getByTestId('context-menu')).toBeVisible();
    });
    return source;
}

/** The viewport box of `locator`, which must be on screen. */
async function boxOf(locator: Locator): Promise<{x: number; y: number; width: number; height: number}> {
    await expect(locator).toBeVisible();
    const box = await locator.boundingBox();
    if (!box) throw new Error('the element has no box');
    return box;
}

/** Scrolls the page so that `locator`'s centre sits at `fraction` of the viewport's height (as near as the page allows). */
async function scrollToFraction(locator: Locator, fraction: number): Promise<void> {
    await locator.evaluate((el, f) => {
        const rect = el.getBoundingClientRect();
        window.scrollBy(0, rect.top + rect.height / 2 - window.innerHeight * f);
    }, fraction);
}

/** The menu's entries in DOM order: each item's test id, a separator as `—`. */
async function menuOrder(page: Page): Promise<string[]> {
    return page.getByTestId('context-menu').evaluate((menu) => [...menu.querySelectorAll('[role="menuitem"], hr')].map((el) => (el.tagName === 'HR' ? '—' : (el.getAttribute('data-testid') ?? '?'))));
}

/** The name cell of a lab row, the press target of the row menu (never a control of the row). */
const nameCell = (page: Page, rowId: string) => page.locator(`tr[data-row-id="${rowId}"] td.td-data[data-column-id="name"]`);

const GAP = 12;
const PAD = 8;

type GestureWindow = Window & {__lfGesture?: string[]};

/**
 * Records what the browser sends `locator`'s element during a gesture (pointer, touch, contextmenu, click; with the
 * time since the first one) and marks the node, so a failed long press says why: a `pointercancel` from the browser,
 * or a node the table re-rendered under the finger.
 */
async function recordGesture(locator: Locator): Promise<void> {
    await locator.evaluate((el) => {
        const w = window as GestureWindow;
        w.__lfGesture = [];
        let start = 0;
        (el as HTMLElement & {__lfMark?: boolean}).__lfMark = true;
        for (const type of ['pointerdown', 'pointermove', 'pointerup', 'pointercancel', 'touchstart', 'touchend', 'touchcancel', 'contextmenu', 'click']) {
            el.addEventListener(
                type,
                (event) => {
                    if (!start) start = event.timeStamp;
                    const pointerType = (event as PointerEvent).pointerType ? `/${(event as PointerEvent).pointerType}` : '';
                    w.__lfGesture?.push(`${type}${pointerType}@${Math.round(event.timeStamp - start)}ms`);
                },
                {capture: true},
            );
        }
    });
}

/** Runs `check`; on failure, rethrows with the gesture {@link recordGesture} recorded and whether the node survived. */
async function withGestureReport(locator: Locator, check: () => Promise<void>): Promise<void> {
    try {
        await check();
    } catch (error) {
        const report = await locator.evaluate((el) => ({
            events: (window as GestureWindow).__lfGesture ?? [],
            sameNode: !!(el as HTMLElement & {__lfMark?: boolean}).__lfMark,
            classes: el.className,
        }));
        throw new Error(`${(error as Error).message}\n--- gesture on the element: ${report.events.join(', ') || 'nothing'}; same node: ${report.sameNode}; class: ${report.classes}`);
    }
}

/** Barrier: a tap on Sync lands in the log, so every event of the gesture before it has been written. */
async function syncBarrier(page: Page): Promise<void> {
    const before = await logEntries(page, 'action: sync').count();
    await page.getByTestId('lab-icon-sync').tap();
    await expect(logEntries(page, 'action: sync')).toHaveCount(before + 1);
}

test.describe('Button Lab — a finger (mobile)', () => {
    test.beforeEach(async ({}, testInfo) => {
        test.skip(testInfo.project.name !== 'mobile', 'touch gestures: the mobile project (Chromium with touch)');
    });

    test('a long press on an icon shows its name and does not act; a tap acts', async ({page}) => {
        await openLab(page);
        const edit = page.getByTestId('lab-icon-edit');
        await longPress(page, edit, async () => {
            // The name appears at 500 ms of rest: this is the wait, on the condition itself.
            await expect(tooltip(page)).toBeVisible({timeout: 5_000});
            await expect(tooltip(page)).toHaveText('Edit');
        });
        await syncBarrier(page);
        await expect(logEntries(page, 'action: edit'), 'a long press shows the name and never acts').toHaveCount(0);

        await edit.tap();
        await expect(logEntries(page, 'action: edit'), 'a tap acts').toHaveCount(1);
    });

    test('a long press on a button of a table row does not select the row; a long press on its cell does', async ({page}) => {
        await openLab(page);
        const selection = page.getByTestId('lab-selection');
        await expect(selection).toHaveText('selected: none');

        const open = page.getByTestId('lab-row-open-r1');
        await recordGesture(open);
        await longPress(page, open, async () => {
            await withGestureReport(open, async () => {
                await expect(tooltip(page)).toBeVisible({timeout: 5_000});
                await expect(tooltip(page)).toHaveText('Open First row');
            });
        });
        await syncBarrier(page);
        await expect(selection, 'the button’s long press is the button’s (85 D6)').toHaveText('selected: none');
        await expect(logEntries(page, 'action: open r1')).toHaveCount(0);

        // Positive control: the same gesture on a cell of the row selects it.
        const cell = page.locator('tr[data-row-id="r1"] td').filter({hasText: 'First row'});
        await expect(cell).toHaveCount(1);
        await longPress(page, cell, async () => {
            await expect(selection).toHaveText('selected: r1', {timeout: 5_000});
        });
    });

    test('a tap on a button off with a reason shows the reason and runs nothing', async ({page}) => {
        await openLab(page);
        const off = page.getByTestId('lab-reason');
        await expect(off).toHaveAttribute('aria-disabled', 'true');
        await expect(off).toHaveAttribute('data-disabled-reason', 'no_selection');
        await expect(off).toBeVisible();
        // Playwright's actionability counts aria-disabled as «not enabled» and would wait forever; a finger can tap this
        // button by design (it stays reachable to show its reason), so the check is skipped, the touch stays real.
        await off.tap({force: true});
        await expect(tooltip(page)).toBeVisible();
        await expect(tooltip(page)).toContainText('Select at least one row first.');
        await syncBarrier(page);
        await expect(page.locator('[data-testid="lab-log-entry"][data-event^="ERROR"]'), 'the action of an off button never runs').toHaveCount(0);
    });
});

test.describe('Button Lab — a finger: the name’s size and the row menu (mobile)', () => {
    test.beforeEach(async ({}, testInfo) => {
        test.skip(testInfo.project.name !== 'mobile', 'touch gestures: the mobile project (Chromium with touch)');
    });

    test('a button’s name is a compact box on a phone, not the 288 px of an info tooltip', async ({page}, testInfo) => {
        await openLab(page);
        const widths: Record<string, number> = {};

        await longPress(page, page.getByTestId('lab-icon-edit'), async () => {
            await expect(tooltip(page)).toHaveText('Edit', {timeout: 5_000});
        });
        widths.name = (await boxOf(tooltip(page))).width;

        await syncBarrier(page);
        const off = page.getByTestId('lab-reason');
        await expect(off).toBeVisible();
        // aria-disabled reads «not enabled» to Playwright's actionability; a finger can tap it by design.
        await off.tap({force: true});
        await expect(tooltip(page)).toContainText('Select at least one row first.');
        widths.nameAndReason = (await boxOf(tooltip(page))).width;

        await syncBarrier(page);
        await longPress(page, page.getByTestId('lab-help'), async () => {
            await expect(tooltip(page)).toContainText('Shows the two providers', {timeout: 5_000});
        });
        widths.help = (await boxOf(tooltip(page))).width;

        testInfo.annotations.push({type: 'tooltip-widths', description: JSON.stringify(widths)});
        console.log(`tooltip widths on ${testInfo.project.name}: ${JSON.stringify(widths)}`);
        expect(widths.name, 'a short name gets a box of its own size').toBeGreaterThan(0);
        expect(widths.name, 'the phone rule of info tooltips (min 18 rem = 288 px) does not apply to a button’s name').toBeLessThan(288);
    });

    test('a finger’s row menu near the right edge opens to the left of the finger and above it', async ({page}, testInfo) => {
        await openLab(page);
        const cell = nameCell(page, 'r2');
        await scrollToFraction(cell, 0.7);
        const box = await boxOf(cell);
        // The right end of the name cell: the cells further right hold controls (the Open button, the ⋮), whose long
        // press is theirs (D6). The room-on-the-left barrier below says whether this is far enough right.
        const point = {x: Math.round(box.x + box.width - 6), y: Math.round(box.y + box.height / 2)};
        expect(await cell.evaluate((el, p) => el.contains(document.elementFromPoint(p.x, p.y)), point), `the press at ${point.x},${point.y} lands on the name cell`).toBe(true);

        const source = await fingerRowMenu(page, point);
        testInfo.annotations.push({type: 'contextmenu-source', description: source});
        console.log(`row menu by finger, contextmenu ${source}`);

        const menu = page.getByTestId('context-menu');
        await expect(menu).toHaveAttribute('data-origin', 'finger');
        const m = await boxOf(menu);
        const viewport = page.viewportSize()!;
        // Barriers: there is room on the left of the finger and above it for this menu.
        expect(point.x - GAP - m.width, `room on the left (x ${point.x}, menu ${m.width} px)`).toBeGreaterThanOrEqual(PAD);
        expect(point.y - GAP - m.height, `room above (y ${point.y}, menu ${m.height} px, viewport ${viewport.height})`).toBeGreaterThanOrEqual(PAD);

        await expect(menu).toHaveAttribute('data-placement', 'left-above');
        expect(m.x + m.width, 'the right edge a gap short of the finger').toBeLessThanOrEqual(point.x - GAP + 1);
        expect(m.y + m.height, 'the bottom edge a gap short of the finger').toBeLessThanOrEqual(point.y - GAP + 1);
    });

    test('a finger’s row menu near the left edge is centred on the finger (or held at the edge)', async ({page}, testInfo) => {
        await openLab(page);
        const cell = nameCell(page, 'r2');
        await scrollToFraction(cell, 0.7);
        const box = await boxOf(cell);
        const point = {x: Math.round(box.x + 6), y: Math.round(box.y + box.height / 2)};
        expect(await cell.evaluate((el, p) => el.contains(document.elementFromPoint(p.x, p.y)), point), `the press at ${point.x},${point.y} lands on the name cell`).toBe(true);

        const source = await fingerRowMenu(page, point);
        testInfo.annotations.push({type: 'contextmenu-source', description: source});

        const menu = page.getByTestId('context-menu');
        const m = await boxOf(menu);
        // Barrier: on the left of the finger there is no room for this menu.
        expect(point.x - GAP - m.width, `no room on the left (x ${point.x}, menu ${m.width} px)`).toBeLessThan(PAD);
        await expect(menu).toHaveAttribute('data-placement', /^centre-/);
        const centred = point.x - m.width / 2;
        if (centred >= PAD) expect(Math.abs(m.x + m.width / 2 - point.x), 'centred on the finger').toBeLessThanOrEqual(1);
        else expect(Math.abs(m.x - PAD), 'held at the viewport’s edge').toBeLessThanOrEqual(1);
    });

    test('a finger’s row menu ends with copy-cell and copy-row, after every row action; copy-row copies', async ({page}) => {
        await openLab(page);
        const cell = nameCell(page, 'r1');
        await scrollToFraction(cell, 0.7);
        const box = await boxOf(cell);
        await fingerRowMenu(page, {x: Math.round(box.x + box.width / 2), y: Math.round(box.y + box.height / 2)});

        const order = await menuOrder(page);
        const copyCell = order.indexOf('context-menu-copy-cell');
        const copyRow = order.indexOf('context-menu-copy-row');
        expect(copyRow, `copy-row is the last item (${order.join(', ')})`).toBe(order.length - 1);
        expect(copyCell, 'copy-cell comes just before copy-row').toBe(copyRow - 1);
        const actions = order.filter((id) => id.startsWith('context-menu-action-'));
        expect(actions, 'the lab’s row action is in the menu').toContain('context-menu-action-menu-edit');
        for (const id of actions) expect(order.indexOf(id), `${id} comes before the copy items`).toBeLessThan(copyCell);

        const since = await eventSeq(page);
        await page.getByTestId('context-menu-copy-row').tap();
        const event = await waitForEvent(page, 'table.row.copied', {since});
        expect(Number(event.detail?.chars)).toBeGreaterThan(0);
        await expect(page.getByTestId('context-menu')).toBeHidden();
    });
});

test.describe('Button Lab — a mouse (desktop)', () => {
    test.beforeEach(async ({}, testInfo) => {
        test.skip(testInfo.project.name !== 'desktop', 'mouse gestures: the desktop project');
    });

    test('a click acts and no name follows it for 700 ms; leaving and coming back shows it again', async ({page}) => {
        await openLab(page);
        const edit = page.getByTestId('lab-icon-edit');
        await expect(edit).toBeVisible();
        // Armed before the click: records any tooltip that appears from now on, however briefly.
        await page.evaluate(() => {
            const w = window as Window & {__lfTipSeen?: boolean};
            w.__lfTipSeen = document.querySelector('[role="tooltip"]') !== null;
            new MutationObserver(() => {
                if (document.querySelector('[role="tooltip"]')) w.__lfTipSeen = true;
            }).observe(document.body, {childList: true, subtree: true});
        });
        await edit.click();
        await expect(logEntries(page, 'action: edit')).toHaveCount(1);
        // The window is the subject (the mouse rests 500 ms before a name): waited on the page's own clock.
        const seen = await page.evaluate(() => new Promise<boolean>((resolve) => setTimeout(() => resolve(!!(window as Window & {__lfTipSeen?: boolean}).__lfTipSeen), 700)));
        expect(seen, 'no name after a click while the pointer stays').toBe(false);

        // The negative's teeth: the same pointer, after leaving and coming back, does get the name.
        await page.mouse.move(1, 1);
        await edit.hover();
        await expect(tooltip(page)).toBeVisible({timeout: 3_000});
        await expect(tooltip(page)).toHaveText('Edit');
    });

    test('a mouse rest on an icon shows its name', async ({page}) => {
        await openLab(page);
        await page.getByTestId('lab-icon-sync').hover();
        await expect(tooltip(page)).toBeVisible({timeout: 3_000});
        await expect(tooltip(page)).toHaveText('Sync prices');
        await expect(logEntries(page, 'action: sync'), 'a rest never acts').toHaveCount(0);
    });
    test('a mouse right click on a row opens a pointer’s menu, its top-left at the click', async ({page}) => {
        await openLab(page);
        const cell = nameCell(page, 'r1');
        await scrollToFraction(cell, 0.3);
        const box = await boxOf(cell);
        const point = {x: Math.round(box.x + 20), y: Math.round(box.y + box.height / 2)};
        await cell.click({button: 'right', position: {x: point.x - box.x, y: point.y - box.y}});
        const menu = page.getByTestId('context-menu');
        await expect(menu).toHaveAttribute('data-origin', 'pointer');
        await expect(menu).not.toHaveAttribute('data-placement');
        const m = await boxOf(menu);
        const viewport = page.viewportSize()!;
        // Barrier: the menu fits to the right of and below the click, so no flip applies.
        expect(point.x + m.width, 'room on the right').toBeLessThanOrEqual(viewport.width);
        expect(point.y + m.height, 'room below').toBeLessThanOrEqual(viewport.height);
        expect(Math.abs(m.x - point.x), 'left at the click').toBeLessThanOrEqual(1);
        expect(Math.abs(m.y - point.y), 'top at the click').toBeLessThanOrEqual(1);
        // A mouse's menu has no copy items.
        await expect(page.getByTestId('context-menu-copy-row')).toHaveCount(0);
    });

    test('the words of the auto buttons follow the toolbar mechanism: shown at 900 px, hidden at 240 px', async ({page}) => {
        await openLab(page);
        const width = page.getByTestId('lab-width');
        const box = page.getByTestId('lab-auto-box');
        const word = page.getByTestId('lab-auto-add').locator('[data-lf-word]');

        await width.fill('900');
        await expect(box).toHaveAttribute('data-labels', 'shown');
        await expect(word).toBeVisible();

        await width.fill('240');
        await expect(box).toHaveAttribute('data-labels', 'hidden');
        await expect(word).toBeHidden();
        // The name stays the button's: an icon with its accessible name.
        await expect(page.getByTestId('lab-auto-add')).toHaveAttribute('aria-label', 'Add goal');

        await width.fill('900');
        await expect(box).toHaveAttribute('data-labels', 'shown');
        await expect(word).toBeVisible();
    });
    test('BTN-2·0: a cut name shows on a mouse rest; a chip and a coloured ghost act; a group segment and a disclosure toggle', async ({page}) => {
        await openLab(page);

        // C7: the word of «lab-truncate» is cut by its 10 rem box, so the name opens on a rest.
        const truncated = page.getByTestId('lab-truncate');
        const word = truncated.locator('[data-lf-word]');
        await expect(word).toBeVisible();
        expect(await word.evaluate((el) => el.scrollWidth > el.clientWidth), 'barrier: the word is cut by its box').toBe(true);
        await truncated.hover();
        await expect(tooltip(page)).toBeVisible({timeout: 3_000});
        await expect(tooltip(page)).toHaveText('A very long asset name that never fits');
        await page.mouse.move(1, 1);
        await expect(tooltip(page)).toBeHidden();

        // C4, C5: a chip and a ghost in a state's colour are live buttons.
        await page.getByTestId('lab-chip').click();
        await expect(logEntries(page, 'action: chip')).toHaveCount(1);
        await page.getByTestId('lab-tone-ghost').click();
        await expect(logEntries(page, 'action: retry')).toHaveCount(1);

        // C2: a segment of the group is a toggle.
        const grid = page.getByTestId('lab-group-grid');
        const list = page.getByTestId('lab-group-list');
        await expect(page.getByTestId('lab-group')).toHaveAttribute('role', 'group');
        await expect(grid).toHaveAttribute('aria-pressed', 'true');
        await expect(list).toHaveAttribute('aria-pressed', 'false');
        await list.click();
        await expect(list).toHaveAttribute('aria-pressed', 'true');
        await expect(grid).toHaveAttribute('aria-pressed', 'false');
        await grid.click();
        await expect(grid).toHaveAttribute('aria-pressed', 'true');

        // C6: a disclosure says it is open, and opens what it names.
        const disclosure = page.getByTestId('lab-expanded');
        await expect(disclosure).toHaveAttribute('aria-expanded', 'false');
        await expect(page.getByTestId('lab-details')).toHaveCount(0);
        await disclosure.click();
        await expect(disclosure).toHaveAttribute('aria-expanded', 'true');
        await expect(page.getByTestId('lab-details')).toBeVisible();
        await disclosure.click();
        await expect(disclosure).toHaveAttribute('aria-expanded', 'false');
        await expect(page.getByTestId('lab-details')).toHaveCount(0);
    });
});
