/**
 * The filter menu of the settings pages follows the window (81 U38, developer's choice «A» of 24/11/2026).
 *
 * Plugins, Preferences and Global settings share `SettingsCategoryNav`. The Plugins page is 7 700 px long at 1440 and
 * 20 000 at 390: the menu used to leave the screen at the first scroll and the way back was a scroll to the top. Now:
 *
 *   - from 640 px up the column is `sticky`, 16 px under the app header, and follows it (the header hides on a scroll
 *     down and returns on a scroll up: the column's offset is the variable `--lf-header-offset` the header publishes,
 *     its height when it shows and 0 when it is hidden); a window too low for it makes the column scroll on its own;
 *   - on a phone the «Category» box is `sticky` under the header; stuck, it loses the label (which scrolls away on its
 *     own) and shows a border and a shadow (`data-stuck`), and the header must NOT come back by itself after the stick
 *     (a layout shift would make the browser correct the scroll upward and show it);
 *   - choosing a filter from the middle of the page brings the start of the list back under the header.
 *
 * `position: sticky` and the scroll are the subject, so this is a real browser (jsdom has neither). The runner's project
 * is `desktop` (1280×720); the phone tests set their own 430 px viewport, like `phone-no-hscroll`, and the `mobile`
 * project skips the file (it would only repeat the same tests). Geometry is read in ONE `evaluate` and
 * polled (`expect.poll`): the header and the column move for 200 ms after a scroll, and two awaited reads would
 * straddle it. Read-only: nothing is written. Assertions read geometry and `data-*`, never a translated text.
 *
 * Presence controls: the control element of every test (the page's tab bar) must have left the window, or the scroll
 * never happened and a «menu in view» would mean nothing.
 */
import {expect, test, type Page} from '../fixtures/playwright';
import {login, navigateTo} from '../fixtures/auth-helpers';
import {waitForSettled} from '../fixtures/app-events';
import {TEST_ADMIN, TEST_USER} from '../fixtures/test-users';

interface Geometry {
    top: number;
    bottom: number;
    viewport: number;
    headerBottom: number;
    headerHeight: number;
    headerState: string | null;
    offsetVar: string;
    scrollY: number;
    scrollable: number;
    stuck: string | null;
    clientHeight: number;
    scrollHeight: number;
}

/** Everything one assertion needs, read in one go. */
async function geometry(page: Page, testId: string): Promise<Geometry> {
    return page.evaluate((id) => {
        const el = document.querySelector(`[data-testid="${id}"]`);
        if (!el) throw new Error(`no element with data-testid ${id}`);
        const rect = el.getBoundingClientRect();
        const header = document.querySelector('[data-testid="app-header"]') as HTMLElement;
        const headerRect = header.getBoundingClientRect();
        return {
            top: Math.round(rect.top * 10) / 10,
            bottom: Math.round(rect.bottom * 10) / 10,
            viewport: window.innerHeight,
            headerBottom: Math.max(0, Math.round(headerRect.bottom * 10) / 10),
            headerHeight: header.offsetHeight,
            headerState: header.getAttribute('data-scroll-state'),
            offsetVar: getComputedStyle(document.documentElement).getPropertyValue('--lf-header-offset').trim(),
            scrollY: window.scrollY,
            scrollable: document.documentElement.scrollHeight - window.innerHeight,
            stuck: el.getAttribute('data-stuck'),
            clientHeight: (el as HTMLElement).clientHeight,
            scrollHeight: (el as HTMLElement).scrollHeight,
        };
    }, testId);
}

/** Three frames: long enough for a layout shift to show its scroll correction, no clock involved. */
async function frames(page: Page, count = 3): Promise<void> {
    await page.evaluate(
        (n) =>
            new Promise<void>((resolve) => {
                const step = (left: number) => (left <= 0 ? resolve() : requestAnimationFrame(() => step(left - 1)));
                step(n);
            }),
        count,
    );
}

async function openPlugins(page: Page): Promise<void> {
    await navigateTo(page, '/settings?tab=plugins');
    await expect(page.getByTestId('settings-tab-plugins')).toHaveAttribute('aria-selected', 'true', {timeout: 10_000});
    await waitForSettled(page.getByTestId('plugin-settings-tab'), 25_000);
}

/** Scroll the window far down in one jump (the header hides on a downward scroll) and wait for the header to say so. */
async function scrollDeep(page: Page, y = 2500): Promise<void> {
    const reachable = (await geometry(page, 'plugin-settings-tab')).scrollable;
    expect(reachable, 'premise: the Plugins page is long enough to scroll the menu out of the window').toBeGreaterThan(y);
    await page.evaluate((to) => window.scrollTo(0, to), y);
    await expect.poll(async () => (await geometry(page, 'plugin-settings-tab')).headerState, {timeout: 8_000}).toBe('hidden');
}

/** A short scroll up: the header comes back. */
async function scrollUpALittle(page: Page): Promise<void> {
    await page.evaluate(() => window.scrollBy(0, -60));
    await expect.poll(async () => (await geometry(page, 'plugin-settings-tab')).headerState, {timeout: 8_000}).toBe('visible');
}

test.describe('the filter menu on a wide screen', () => {
    test.beforeEach(async ({page}, testInfo) => {
        test.skip(testInfo.project.name !== 'desktop', 'one project is enough: the file sets the width it needs');
    });

    test('Plugins: the column stays in the window, under the header, hidden or shown', async ({page}) => {
        await login(page, TEST_USER);
        await openPlugins(page);
        await scrollDeep(page);

        // Control: the tab bar of the page is gone, so the scroll really took the top of the page away.
        await expect.poll(async () => (await geometry(page, 'settings-tab-plugins')).bottom, {timeout: 5_000}).toBeLessThan(0);

        // Header hidden: the column is in the window, 16 px from its top edge.
        await expect
            .poll(
                async () => {
                    const g = await geometry(page, 'plugin-settings-category-nav');
                    return {top: Math.round(g.top), inside: g.bottom <= g.viewport + 1, offset: g.offsetVar};
                },
                {timeout: 8_000},
            )
            .toEqual({top: 16, inside: true, offset: '0px'});

        // Header back after a scroll up: the column follows it down, 16 px under it.
        await scrollUpALittle(page);
        await expect
            .poll(
                async () => {
                    const g = await geometry(page, 'plugin-settings-category-nav');
                    return {gap: Math.round(g.top - g.headerBottom), inside: g.bottom <= g.viewport + 1, offset: g.offsetVar === `${g.headerHeight}px`};
                },
                {timeout: 8_000},
            )
            .toEqual({gap: 16, inside: true, offset: true});
    });

    test('Plugins: a window too low for the column (768×220) scrolls the column on its own', async ({page}) => {
        await login(page, TEST_USER);
        await page.setViewportSize({width: 768, height: 220});
        await openPlugins(page);
        await scrollDeep(page);
        await scrollUpALittle(page);
        await expect
            .poll(
                async () => {
                    const g = await geometry(page, 'plugin-settings-category-nav');
                    return {inside: g.bottom <= g.viewport + 1 && g.top >= g.headerBottom, overflows: g.scrollHeight > g.clientHeight};
                },
                {timeout: 8_000, message: 'premise: at 768×220 the menu is taller, header shown or hidden, than what the window leaves it, and it stays inside it'},
            )
            .toEqual({inside: true, overflows: true});
        // Read and written in one go: what the column is (a scroll area with a bounded height) and whether it moves.
        const scrolled = await page.getByTestId('plugin-settings-category-nav').evaluate((el) => {
            const style = getComputedStyle(el);
            el.scrollTop = 40;
            return {overflowY: style.overflowY, maxHeight: style.maxHeight, client: el.clientHeight, scrollHeight: el.scrollHeight, scrollTop: el.scrollTop};
        });
        expect(scrolled.overflowY, `the column is no scroll area: ${JSON.stringify(scrolled)}`).toBe('auto');
        expect(scrolled.scrollTop, `the column does not scroll by itself: ${JSON.stringify(scrolled)}`).toBeGreaterThan(0);
    });

    test('Plugins: choosing a filter from the middle of the page brings the top of the list back under the header', async ({page}) => {
        await login(page, TEST_USER);
        await openPlugins(page);
        await scrollDeep(page, 3000);
        const header = (await geometry(page, 'plugin-settings-tab')).headerHeight;
        await page.getByTestId('plugin-settings-category-all').click();
        // Smooth scroll: wait for it to arrive; the start of the page's content is 16 px under the (returning) header.
        await expect.poll(async () => Math.round((await geometry(page, 'plugin-settings-tab')).top), {timeout: 10_000, message: 'the list never came back to its start'}).toBeGreaterThanOrEqual(header + 14);
        const g = await geometry(page, 'plugin-settings-tab');
        expect(g.top, 'the list start went below the middle of the window').toBeLessThanOrEqual(header + 18);
    });

    test('Global settings (administrator): the column stays in the window as well', async ({page}) => {
        await login(page, TEST_ADMIN);
        await navigateTo(page, '/settings/admin/global');
        await expect(page.getByTestId('global-settings-tab')).toBeVisible({timeout: 15_000});
        await waitForSettled(page.getByTestId('global-settings-tab'), 25_000);
        const reachable = (await geometry(page, 'global-settings-tab')).scrollable;
        expect(reachable, 'premise: Global settings is long enough to scroll the menu out of the window').toBeGreaterThan(600);
        await page.evaluate(() => window.scrollTo(0, 600));
        await expect.poll(async () => (await geometry(page, 'global-settings-tab')).headerState, {timeout: 8_000}).toBe('hidden');
        await expect
            .poll(
                async () => {
                    const g = await geometry(page, 'global-settings-category-nav');
                    return {top: Math.round(g.top), inside: g.bottom <= g.viewport + 1};
                },
                {timeout: 8_000},
            )
            .toEqual({top: 16, inside: true});
    });
});

test.describe('the filter box on a phone', () => {
    test.use({viewport: {width: 430, height: 932}});
    test.beforeEach(async ({page}, testInfo) => {
        test.skip(testInfo.project.name !== 'desktop', 'one project is enough: the file sets the width it needs');
    });

    test('Plugins: the box stays under the header, loses its label, and the header does not come back by itself', async ({page}) => {
        await login(page, TEST_USER);
        await openPlugins(page);
        const rest = await geometry(page, 'plugin-settings-mobile-category-box');
        expect(rest.stuck, 'at the top of the page the box is not stuck').toBe('false');
        await expect(page.getByTestId('plugin-settings-mobile-category-label')).toBeVisible();

        await scrollDeep(page);
        await expect
            .poll(
                async () => {
                    const g = await geometry(page, 'plugin-settings-mobile-category-box');
                    return {top: Math.round(g.top), stuck: g.stuck, offset: g.offsetVar};
                },
                {timeout: 8_000},
            )
            .toEqual({top: 0, stuck: 'true', offset: '0px'});
        await expect(page.getByTestId('plugin-settings-mobile-category-label'), 'the label scrolls away; it is not carried along').not.toBeInViewport();

        // The stick must not move the content: the browser would answer a shift with a scroll correction that shows the header.
        const before = await geometry(page, 'plugin-settings-mobile-category-box');
        await frames(page, 4);
        const after = await geometry(page, 'plugin-settings-mobile-category-box');
        expect({state: after.headerState, scrollY: after.scrollY}, 'the header came back, or the page moved, by itself').toEqual({state: 'hidden', scrollY: before.scrollY});

        // A scroll up shows the header, and the box slides down under it.
        await scrollUpALittle(page);
        await expect
            .poll(
                async () => {
                    const g = await geometry(page, 'plugin-settings-mobile-category-box');
                    return {gap: Math.round(g.top - g.headerBottom), stuck: g.stuck};
                },
                {timeout: 8_000},
            )
            .toEqual({gap: 0, stuck: 'true'});

        // The menu still opens from the stuck box and the list is whole in the window.
        await page.getByTestId('plugin-settings-mobile-category-trigger').click();
        const menu = await geometry(page, 'plugin-settings-mobile-category-menu');
        expect({below: menu.top >= 0, inside: menu.bottom <= menu.viewport}, 'the open list is not whole in the window').toEqual({below: true, inside: true});
    });

    test('Plugins: choosing a filter from the middle of the page brings the top of the list back under the header', async ({page}) => {
        await login(page, TEST_USER);
        await openPlugins(page);
        await scrollDeep(page, 3000);
        const header = (await geometry(page, 'plugin-settings-tab')).headerHeight;
        // The box is stuck and reachable from where we are.
        await page.getByTestId('plugin-settings-mobile-category-trigger').click();
        await page.getByTestId('plugin-settings-mobile-category-all').click();
        await expect.poll(async () => Math.round((await geometry(page, 'plugin-settings-tab')).top), {timeout: 10_000, message: 'the list never came back to its start'}).toBeGreaterThanOrEqual(header + 14);
        const g = await geometry(page, 'plugin-settings-tab');
        expect(g.top, 'the list start went below the middle of the window').toBeLessThanOrEqual(header + 18);
    });

    test('Global settings (administrator): the box is stuck as well', async ({page}) => {
        await login(page, TEST_ADMIN);
        await navigateTo(page, '/settings/admin/global');
        await expect(page.getByTestId('global-settings-tab')).toBeVisible({timeout: 15_000});
        await waitForSettled(page.getByTestId('global-settings-tab'), 25_000);
        const reachable = (await geometry(page, 'global-settings-tab')).scrollable;
        expect(reachable, 'premise: Global settings is long enough to scroll the box out of the window').toBeGreaterThan(600);
        await page.evaluate(() => window.scrollTo(0, 600));
        await expect.poll(async () => (await geometry(page, 'global-settings-tab')).headerState, {timeout: 8_000}).toBe('hidden');
        await expect
            .poll(
                async () => {
                    const g = await geometry(page, 'global-settings-mobile-category-box');
                    return {top: Math.round(g.top), stuck: g.stuck};
                },
                {timeout: 8_000},
            )
            .toEqual({top: 0, stuck: 'true'});
    });
});
