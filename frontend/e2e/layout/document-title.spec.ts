/**
 * The browser tab title never changes: every page shows the <title> of src/app.html (workstream K,
 * step 12c — the developer's rule of 2026-09-29).
 *
 * Svelte applies a page's `<svelte:head><title>` by assigning `document.title` after the page mounts
 * and never restores it, so a page title outlives its page on every client-side hop (workstream J:
 * after Files, every page kept "Files - LibreFolio"). The rule removes the cause — no page sets a
 * title — so there is nothing left to restore. Its static half is the unit guard
 * `src/routes/documentTitle.guard.test.ts` (no `<svelte:head><title>`, no `document.title` write in
 * src); this spec is the browser half and reads the title the running app shows, whatever wrote it:
 *
 *   1. direct landing on every main page, a tool page included;
 *   2. client-side navigation in ONE app runtime: landed on a tool page, out through its back link to
 *      the hub, then across every main page through the sidebar. Every hop proves the runtime
 *      survived it: a full load re-reads app.html and would hide a title left behind;
 *   3. a same-route query change (Files → Files?tab=brim), which remounts nothing.
 *
 * Every title assertion comes after the page's own readiness signal (its `data-busy`, the tool
 * host's `data-state`): a page writes its title once it has mounted, so an earlier assertion would
 * read the app.html title the page had not yet had the chance to overwrite. The expected title is
 * read from src/app.html, the single source — never a translated literal.
 *
 * Nothing is written server-side: TEST_USER only reads (the Files tab choice stays in the test's own
 * browser context), and is grandfathered completed on every onboarding flow (populate_mock_data),
 * which each test reads back over the API so no guide or tour overlay competes for the clicks. The
 * runner's desktop AND mobile projects run every case; on mobile the sidebar is off-canvas and is
 * opened through the header's burger.
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

/** A main page: where it lives, the sidebar link that reaches it, and the signal that says it is ready. */
interface MainPage {
    label: string;
    path: string;
    navTestId: string;
    ready: (page: Page) => Promise<void>;
}

/** Ready: the page root is visible and its `data-busy` says its first load is in. */
function settles(testId: string): MainPage['ready'] {
    return async (page) => {
        const root = page.getByTestId(testId);
        await expect(root).toBeVisible({timeout: PAGE_TIMEOUT_MS});
        await waitForSettled(root, PAGE_TIMEOUT_MS);
    };
}

const DASHBOARD: MainPage = {label: 'Dashboard', path: '/dashboard', navTestId: 'nav-dashboard', ready: settles('dashboard-page')};
const TRANSACTIONS: MainPage = {label: 'Transactions', path: '/transactions', navTestId: 'nav-transactions', ready: settles('transactions-page')};
const ASSETS: MainPage = {label: 'Assets', path: '/assets', navTestId: 'nav-assets', ready: settles('assets-page')};
const FILES: MainPage = {label: 'Files', path: '/files', navTestId: 'nav-files', ready: settles('files-page')};
const TOOLS: MainPage = {label: 'Tools', path: '/tools', navTestId: 'nav-tools', ready: settles('tools-hub')};
const BROKERS: MainPage = {label: 'Brokers', path: '/brokers', navTestId: 'nav-brokers', ready: settles('brokers-page')};
const FX: MainPage = {label: 'FX', path: '/fx', navTestId: 'nav-fx', ready: settles('fx-page')};
/**
 * Settings publishes no load state: its default tab renders from the session user. A page writes
 * its title when it mounts, so the mounted default tab is the barrier that matters here.
 */
const SETTINGS: MainPage = {
    label: 'Settings',
    path: '/settings',
    navTestId: 'nav-settings',
    ready: async (page) => {
        await expect(page.getByTestId('settings-page')).toBeVisible({timeout: PAGE_TIMEOUT_MS});
        await expect(page.getByTestId('profile-tab')).toBeVisible({timeout: PAGE_TIMEOUT_MS});
    },
};

const MAIN_PAGES: readonly MainPage[] = [DASHBOARD, TRANSACTIONS, ASSETS, FILES, TOOLS, BROKERS, FX, SETTINGS];

const escapeRegExp = (text: string): string => text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');

/** The URL of a page: its own path, a query or a hash allowed, nothing deeper. */
const urlOf = (path: string): RegExp => new RegExp(`${escapeRegExp(path)}(?:[?#]|$)`);

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

/** A client-side hop through the sidebar. On the mobile project the sidebar is off-canvas: the burger opens it, the link closes it again. */
async function followSidebar(page: Page, mobile: boolean, target: MainPage): Promise<void> {
    const header = page.getByTestId('app-header');
    if (mobile) {
        await expect(header).toHaveAttribute('data-sidebar-open', 'false');
        await page.getByTestId('mobile-menu-toggle').click();
        await expect(header).toHaveAttribute('data-sidebar-open', 'true');
    }
    await page.getByTestId(target.navTestId).click();
    await expect(page).toHaveURL(urlOf(target.path), {timeout: PAGE_TIMEOUT_MS});
    if (mobile) await expect(header).toHaveAttribute('data-sidebar-open', 'false');
}

/**
 * The page of a tool the backend catalogue lists. Discovered, not hard-coded: tools are plugins. Any
 * tool will do, and sorting makes the pick independent of the catalogue's order. The path is built
 * the way `toolRoute` (src/lib/features/tools/presentation.ts) builds it.
 */
async function catalogToolPath(page: Page): Promise<string> {
    const response = await page.request.get('/api/v1/tools/catalog');
    expect(response.ok(), `Tool catalogue read failed (HTTP ${response.status()})`).toBe(true);
    const codes = ((await response.json()) as {items: {tool_code: string}[]}).items.map((item) => item.tool_code).sort();
    expect(codes, 'The tool catalogue must list a tool: see backend/app/services/tool_plugins/').not.toEqual([]);
    return `/tools/${encodeURIComponent(codes[0])}`;
}

/**
 * A tool page is ready once its host has settled on its tool: the interface mounted (`ready`), or
 * the modelled `unavailable` state of a tool whose interface this build does not include
 * (`renderer_missing`, src/lib/features/tools/registry.ts). Either way the page has mounted, so a
 * title of its own would already show; a catalogue error is not a tool page and fails here.
 */
async function toolPageReady(page: Page): Promise<void> {
    const host = page.getByTestId('tool-host');
    await expect(host).toBeVisible({timeout: PAGE_TIMEOUT_MS});
    await expect(host, 'The tool page must settle on its tool').toHaveAttribute('data-state', /^(?:ready|unavailable)$/, {timeout: PAGE_TIMEOUT_MS});
}

test.describe('Browser tab title — no page changes it', () => {
    test.beforeEach(async ({page}) => {
        await login(page, TEST_USER);
        await expectNoOnboardingDue(page);
    });

    for (const target of MAIN_PAGES) {
        test(`direct landing on ${target.label} keeps the app.html title`, async ({page}) => {
            await page.goto(target.path);
            await target.ready(page);

            await expect(page, `${target.label} must not change the tab title`).toHaveTitle(DEFAULT_TITLE);
        });
    }

    test('direct landing on a tool page keeps the app.html title', async ({page}) => {
        const toolPath = await catalogToolPath(page);

        await page.goto(toolPath);
        await toolPageReady(page);

        await expect(page, `The tool page ${toolPath} must not change the tab title`).toHaveTitle(DEFAULT_TITLE);
    });

    test('client-side navigation across every main page keeps the app.html title in one app runtime', async ({page}, testInfo) => {
        // Ten page arrivals in one test, each waiting for its page's own first load.
        test.setTimeout(90_000);
        const mobile = testInfo.project.name === 'mobile';
        // Soft title checks, so one run names every page that breaks the rule instead of stopping at
        // the first; each hop and its readiness stay hard, since a title read on a page that never
        // arrived proves nothing.
        const hop = async (target: MainPage): Promise<void> => {
            await followSidebar(page, mobile, target);
            await target.ready(page);
            await expectSameAppRuntime(page);
            await expect.soft(page, `${target.label}, reached through the sidebar, must keep the app.html title`).toHaveTitle(DEFAULT_TITLE);
        };

        // A tool page is reached client-side only through a hub card whose interface is in the
        // build, and a build may include none (registry.ts). So the walk starts on a tool page — the
        // first and only full landing — and leaves it through its back link: what a title left
        // behind needs is a client-side hop away from the page that wrote it.
        const toolPath = await catalogToolPath(page);
        await page.goto(toolPath);
        await toolPageReady(page);
        await expect.soft(page, `The tool page ${toolPath}, landed on, must keep the app.html title`).toHaveTitle(DEFAULT_TITLE);
        await markAppRuntime(page);

        await page.getByTestId('tool-back').click();
        await expect(page).toHaveURL(urlOf(TOOLS.path), {timeout: PAGE_TIMEOUT_MS});
        await TOOLS.ready(page);
        await expectSameAppRuntime(page);
        await expect.soft(page, 'Tools, reached through the back link of the tool page, must keep the app.html title').toHaveTitle(DEFAULT_TITLE);

        // Every main page through the sidebar, the hops away from Files and Tools — the pages that
        // used to write a title of their own — included.
        for (const target of MAIN_PAGES) await hop(target);
    });

    test('a same-route query change on Files (?tab=brim) keeps the app.html title', async ({page}) => {
        await page.goto(FILES.path);
        // The tab bar rewrites `?tab=` only once the first load is in (`urlInitialized`, set in the
        // same task that turns `data-busy` false), so a click before that would change no URL.
        await FILES.ready(page);
        // Soft: the landing is case 1's subject, the query change is this one's.
        await expect.soft(page, 'Files, landed on, must keep the app.html title').toHaveTitle(DEFAULT_TITLE);
        await markAppRuntime(page);

        const brimTab = page.getByTestId('files-tab-brim');
        await brimTab.click();
        await expect(page).toHaveURL(/\/files\?(?:[^#]*&)?tab=brim(?:[&#]|$)/, {timeout: PAGE_TIMEOUT_MS});
        await expect(brimTab).toHaveAttribute('aria-selected', 'true');
        await waitForSettled(page.getByTestId('files-page'), PAGE_TIMEOUT_MS);
        await expectSameAppRuntime(page);

        await expect(page, 'A query change remounts nothing, and must change no title either').toHaveTitle(DEFAULT_TITLE);
    });
});
