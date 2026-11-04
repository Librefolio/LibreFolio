/**
 * Designer Lab — neutrality: a browser that never opened the Lab is left untouched.
 *
 * Every page of a debug build loads the Lab client, and the test server always serves a debug build: the E2E suite
 * and the gallery run with it. They must stay identical to a build without it while the Lab is unused, so with no
 * saved state the client may only listen. A fresh context has no `lf-designer-lab/*` key, gets no Alt+Shift+D
 * shortcut, no veil, no injected style, and its engines report nothing done.
 *
 * The shortcut's absence is read, not waited for: a `keydown` listener installed after the client's tells whether any
 * listener claimed Alt+Shift+D (`defaultPrevented`) for the very event the client would have seen. The same probe,
 * once the Lab has been opened in this browser, sees the client claim it — the positive control that gives the
 * negative its teeth.
 *
 * Nothing is written server-side: TEST_USER only reads, and the Lab keeps its state in this context's localStorage.
 */
import {expect, test, type Page} from '../fixtures/playwright';
import {login} from '../fixtures/auth-helpers';
import {TEST_USER} from '../fixtures/test-users';
import {CROSS_TAB, DESKTOP_ONLY, IDLE_STATS, LAB_KEY_PREFIX, LAB_NODE_IDS, labActive, labPicking, labStats, openDashboardGrowthChart, openLab, pickVeil, waitForLabClient} from './lab-helpers';

test.setTimeout(60_000);

type ShortcutProbe = {seen: boolean; claimed: boolean};
type ProbeWindow = Window & {__e2eLabShortcut?: ShortcutProbe};

/**
 * Press Alt+Shift+D and report what the page did with it: whether the event reached the window (`seen`, the presence
 * barrier) and whether a listener registered before the probe — the Lab client's — claimed it (`claimed`).
 */
async function pressLabShortcut(page: Page): Promise<ShortcutProbe> {
    await page.evaluate(() => {
        const w = window as ProbeWindow;
        w.__e2eLabShortcut = {seen: false, claimed: false};
        const probe = (event: KeyboardEvent) => {
            if (event.code !== 'KeyD' || !event.altKey || !event.shiftKey) return;
            w.__e2eLabShortcut = {seen: true, claimed: event.defaultPrevented};
            window.removeEventListener('keydown', probe);
        };
        window.addEventListener('keydown', probe);
    });
    await page.keyboard.press('Alt+Shift+KeyD');
    await expect.poll(() => page.evaluate(() => (window as ProbeWindow).__e2eLabShortcut?.seen ?? false), {message: 'the key press must reach the window'}).toBe(true);
    return page.evaluate(() => (window as ProbeWindow).__e2eLabShortcut as ShortcutProbe);
}

/** What the Lab left in the page: its localStorage keys, its injected nodes, and the colour-vision filter on `<html>`. */
async function labFootprint(page: Page): Promise<{keys: string[]; nodes: string[]; ownNodes: number; filter: string}> {
    return page.evaluate(
        ({prefix, ids}) => ({
            keys: Object.keys(localStorage).filter((key) => key.startsWith(prefix)),
            nodes: ids.filter((id) => document.getElementById(id) !== null),
            ownNodes: document.querySelectorAll('[data-lf-lab-own]').length,
            filter: getComputedStyle(document.documentElement).filter,
        }),
        {prefix: LAB_KEY_PREFIX, ids: LAB_NODE_IDS},
    );
}

test.describe('Designer Lab — an unused Lab leaves the app untouched', () => {
    test.beforeEach(async ({}, testInfo) => {
        test.skip(testInfo.project.name !== 'desktop', DESKTOP_ONLY);
    });

    test('a fresh context has no Lab state, no shortcut, no veil, no Lab style and idle engines', async ({page, context}) => {
        await login(page, TEST_USER);
        // A page with a chart on screen: the engines would have something to touch.
        await openDashboardGrowthChart(page);
        await waitForLabClient(page);

        expect(await labFootprint(page), 'an unused Lab writes no key, injects no node and filters nothing').toEqual({keys: [], nodes: [], ownNodes: 0, filter: 'none'});
        expect(await labActive(page)).toBe(false);
        expect(await labPicking(page)).toBe(false);
        expect(await labStats(page)).toEqual(IDLE_STATS);

        const fresh = await pressLabShortcut(page);
        expect(fresh, 'Alt+Shift+D reaches the window and nobody claims it: the shortcut exists only where the Lab has been opened').toEqual({seen: true, claimed: false});
        await expect(pickVeil(page)).toHaveCount(0);
        expect(await labPicking(page)).toBe(false);
        expect(await labFootprint(page), 'the key press left nothing behind').toEqual({keys: [], nodes: [], ownNodes: 0, filter: 'none'});
        expect(await labStats(page)).toEqual(IDLE_STATS);

        // Positive control: once this browser has opened the Lab, the same probe sees the client claim the shortcut.
        // The app page loads again after the Lab, so its client starts in a browser that has seen the Lab.
        const lab = await openLab(context);
        await openDashboardGrowthChart(page);
        await waitForLabClient(page);
        const seen = await pressLabShortcut(page);
        expect(seen, 'after the Lab was opened in this browser, the client claims Alt+Shift+D').toEqual({seen: true, claimed: true});
        await expect(pickVeil(page)).toBeVisible(CROSS_TAB);
        await page.keyboard.press('Escape');
        await expect(pickVeil(page)).toHaveCount(0);
        expect(await labPicking(page)).toBe(false);
        // Opening the Lab and picking nothing changed no colour: the engines are still idle.
        expect(await labActive(page)).toBe(false);
        expect(await labStats(page)).toEqual(IDLE_STATS);
        await lab.close();
    });
});
