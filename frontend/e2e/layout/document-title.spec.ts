/**
 * Window title across client-side route changes (workstream J — user-reported, also in v1.1.0).
 *
 * Svelte 5 applies a page's `<svelte:head><title>` by assigning `document.title` in an effect and
 * never restores it when the page unmounts. Only Files and Tools set a title of their own, so after
 * Files every page without one kept "Files - LibreFolio". The `(app)` layout resets the title to
 * the app.html default in `onNavigate`, which SvelteKit runs before the next page mounts: a page
 * with a title of its own sets it again right after, and a same-route navigation (a query change)
 * resets nothing, because nothing remounts to set the title again.
 *
 * Bug and fix exist only on CLIENT-SIDE navigation: a full load re-reads app.html. So `page.goto`
 * is used for the first landing only, every later hop goes through the sidebar (or the Files tab
 * bar), and each case proves the app runtime survived the hop.
 *
 *   1. Files → Dashboard: the default title is back (red before the fix).
 *   2. control — Files → Files?tab=brim: the title Files set is kept.
 *   3. control — Tools → Files → Tools: Tools sets its own title again, so the reset runs before
 *      the next page mounts and not after it (a reset in `afterNavigate` would leave the default).
 *
 * Titles are compared only with titles captured from the app itself, or with the untranslated
 * product name read from `src/app.html` — never with a translated literal. Nothing is written:
 * TEST_USER only reads, and is grandfathered completed on every onboarding flow
 * (populate_mock_data), which each test reads back over the API so no guide or tour overlay
 * competes for the clicks. The runner's desktop AND mobile projects run every case; on mobile the
 * sidebar is off-canvas and is opened through the header's burger.
 */
import {readFileSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import {expect, test, type Page} from '../fixtures/playwright';
import {login} from '../fixtures/auth-helpers';
import {waitForSettled} from '../fixtures/app-events';
import {readOnboardingProgress} from '../fixtures/onboarding-accounts';
import {TEST_USER} from '../fixtures/test-users';

/** The untranslated product name app.html ships as the window title — the only literal this spec compares with. */
function readAppHtmlTitle(): string {
    const appHtmlPath = fileURLToPath(new URL('../../src/app.html', import.meta.url));
    const title = /<title>([^<]*)<\/title>/.exec(readFileSync(appHtmlPath, 'utf8'))?.[1]?.trim();
    if (!title) throw new Error(`No <title> in ${appHtmlPath}: the default window title has no source of truth`);
    return title;
}

const DEFAULT_TITLE = readAppHtmlTitle();
/** Page arrival: a full landing, or a client-side hop that fetches the next page's data. */
const PAGE_TIMEOUT_MS = 15_000;

test.setTimeout(45_000);

type MarkedWindow = Window & {__lfDocumentTitleRuntimeMark?: true};

/** Mark the running app, so a later check can prove a hop stayed client-side. */
async function markAppRuntime(page: Page): Promise<void> {
    await page.evaluate(() => {
        (window as MarkedWindow).__lfDocumentTitleRuntimeMark = true;
    });
}

async function expectSameAppRuntime(page: Page): Promise<void> {
    const kept = await page.evaluate(() => (window as MarkedWindow).__lfDocumentTitleRuntimeMark === true);
    expect(kept, 'The hop must stay client-side: a full load re-reads app.html and would reset the title by itself').toBe(true);
}

/** Precondition, read back rather than inferred: no onboarding flow is due, so no guide or tour overlay competes for the clicks. */
async function expectNoOnboardingDue(page: Page): Promise<void> {
    const due = (await readOnboardingProgress(page)).filter((item) => item.status === 'pending' || item.version < item.current_version).map((item) => item.flow);
    expect(due, `${TEST_USER.username} must be grandfathered completed on every onboarding flow (populate_mock_data _grandfather_onboarding_for_test_users)`).toEqual([]);
}

/**
 * Wait until the current page has applied a title of its own — none of `excluded` — and return it.
 * A page sets its title in an effect after it mounts, so its test id alone is not that barrier.
 */
async function waitForOwnTitle(page: Page, excluded: readonly string[]): Promise<string> {
    let title = '';
    await expect
        .poll(
            async () => {
                title = await page.title();
                return title !== '' && !excluded.includes(title);
            },
            {message: `The page must apply a title of its own, none of ${JSON.stringify(excluded)}`, timeout: PAGE_TIMEOUT_MS},
        )
        .toBe(true);
    return title;
}

/** A client-side hop through the sidebar. On the mobile project the sidebar is off-canvas: the burger opens it, the link closes it again. */
async function followSidebar(page: Page, mobile: boolean, navTestId: string, url: RegExp): Promise<void> {
    const header = page.getByTestId('app-header');
    if (mobile) {
        await expect(header).toHaveAttribute('data-sidebar-open', 'false');
        await page.getByTestId('mobile-menu-toggle').click();
        await expect(header).toHaveAttribute('data-sidebar-open', 'true');
    }
    await page.getByTestId(navTestId).click();
    await expect(page).toHaveURL(url, {timeout: PAGE_TIMEOUT_MS});
    if (mobile) await expect(header).toHaveAttribute('data-sidebar-open', 'false');
}

/** The first and only full landing: Files has mounted and applied the title it sets itself, which is returned. */
async function landOnFiles(page: Page): Promise<string> {
    await page.goto('/files');
    await expect(page.getByTestId('files-tab-static')).toBeVisible({timeout: PAGE_TIMEOUT_MS});
    return waitForOwnTitle(page, [DEFAULT_TITLE]);
}

test.describe('Document title across client-side navigation', () => {
    test.beforeEach(async ({page}) => {
        await login(page, TEST_USER);
        await expectNoOnboardingDue(page);
    });

    test('leaving Files for a page without a title of its own restores the default title', async ({page}, testInfo) => {
        const filesTitle = await landOnFiles(page);
        await markAppRuntime(page);

        await followSidebar(page, testInfo.project.name === 'mobile', 'nav-dashboard', /\/dashboard(?:[/?#]|$)/);
        await expect(page.getByTestId('dashboard-page')).toBeVisible({timeout: PAGE_TIMEOUT_MS});
        await expectSameAppRuntime(page);

        await expect(page, `The title Files set (${JSON.stringify(filesTitle)}) must not outlive the Files page`).toHaveTitle(DEFAULT_TITLE);
    });

    test('control: a query change on Files keeps the title Files set', async ({page}) => {
        const filesTitle = await landOnFiles(page);
        // The tab bar rewrites `?tab=` only once the first load is in (`urlInitialized`, set in the
        // same task that turns `data-busy` false), so a click before that would change no URL.
        await waitForSettled(page.getByTestId('files-page'));
        await markAppRuntime(page);

        await page.getByTestId('files-tab-brim').click();
        await expect(page).toHaveURL(/\/files\?(?:[^#]*&)?tab=brim(?:[&#]|$)/, {timeout: PAGE_TIMEOUT_MS});
        await expectSameAppRuntime(page);

        // The router has run every onNavigate callback by the time the URL changed: a reset would already show.
        await expect(page, 'A same-route navigation remounts nothing that could set the title again').toHaveTitle(filesTitle);
    });

    test('control: a page with a title of its own still sets it after leaving Files', async ({page}, testInfo) => {
        const mobile = testInfo.project.name === 'mobile';
        // The title Tools sets, captured on a full landing: no client-side navigation has touched it.
        await page.goto('/tools');
        await expect(page.getByTestId('tools-hub')).toBeVisible({timeout: PAGE_TIMEOUT_MS});
        const toolsTitle = await waitForOwnTitle(page, [DEFAULT_TITLE]);
        await markAppRuntime(page);

        await followSidebar(page, mobile, 'nav-files', /\/files(?:[/?#]|$)/);
        await expect(page.getByTestId('files-tab-static')).toBeVisible({timeout: PAGE_TIMEOUT_MS});
        // The barrier with teeth: Files replaced the Tools title with its own, so the Tools title
        // asserted below can only come from Tools setting it again on its client-side mount.
        await waitForOwnTitle(page, [DEFAULT_TITLE, toolsTitle]);

        await followSidebar(page, mobile, 'nav-tools', /\/tools(?:[/?#]|$)/);
        await expect(page.getByTestId('tools-hub')).toBeVisible({timeout: PAGE_TIMEOUT_MS});
        await expectSameAppRuntime(page);

        await expect(page, 'Tools must set its own title after the reset, not be overwritten by it').toHaveTitle(toolsTitle);
    });
});
