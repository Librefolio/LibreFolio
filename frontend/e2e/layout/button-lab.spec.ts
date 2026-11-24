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
 *   - a tap on a button off with a reason shows the reason and runs nothing.
 * Desktop project: a click acts and no name follows it for 700 ms; a mouse rest shows an icon's name.
 *
 * Absence of an action is read behind a barrier: after the gesture under test, a tap on another icon must land in the
 * log first, so «no `action: edit`» means it never came, not that it had not arrived yet.
 *
 * The texts asserted (`Edit`, `Sync prices`, the reason, the log events) are props the Lab passes in English, a
 * developer's bench never translated: none comes from the catalogue. No API is called, nothing is written.
 */
import {expect, test, type Locator, type Page} from '../fixtures/playwright';

const DEBUG_ONLY = 'the Button Lab is served by the debug build only';

async function openLab(page: Page): Promise<void> {
    await page.goto('/button-lab');
    await expect(page.getByTestId('button-lab'), `the test server must serve a debug build (dev.py server --test builds one): ${DEBUG_ONLY}`).toBeVisible({timeout: 30_000});
}

const logEntries = (page: Page, event: string) => page.locator(`[data-testid="lab-log-entry"][data-event="${event}"]`);
const tooltip = (page: Page) => page.getByTestId('tooltip-content');

async function centreOf(locator: Locator): Promise<{x: number; y: number}> {
    await expect(locator).toBeVisible();
    const box = await locator.boundingBox();
    if (!box) throw new Error('the element has no box');
    return {x: box.x + box.width / 2, y: box.y + box.height / 2};
}

/**
 * A finger rests on `locator` until `held` resolves (the condition the long press must produce), then lifts. Chromium's
 * own touch input: one finger, id 0; touchEnd carries no point, as the protocol requires.
 */
async function longPress(page: Page, locator: Locator, held: () => Promise<void>): Promise<void> {
    const {x, y} = await centreOf(locator);
    const cdp = await page.context().newCDPSession(page);
    try {
        await cdp.send('Input.dispatchTouchEvent', {type: 'touchStart', touchPoints: [{x, y, id: 0}]});
        await held();
        await cdp.send('Input.dispatchTouchEvent', {type: 'touchEnd', touchPoints: []});
    } finally {
        await cdp.detach();
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

        await longPress(page, page.getByTestId('lab-row-open-r1'), async () => {
            await expect(tooltip(page)).toBeVisible({timeout: 5_000});
            await expect(tooltip(page)).toHaveText('Open First row');
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
});
