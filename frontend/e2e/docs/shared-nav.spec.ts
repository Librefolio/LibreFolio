/**
 * The documentation's shared menu and the English-only developer manual — lane 84, lots D and E.
 *
 * After the build, a page of the documentation keeps in its menu only what Material draws for a pruned navigation (the
 * branch the page is in whole, every other group one link to its first page), and the whole menu of its language is one
 * file, `javascripts/nav/nav.<language>.<hash>.js` (`mkdocs_src/hooks/shared_nav.py`). A small script written next to the
 * menu (`javascripts/nav-enhance.js`) reads that file while the page is parsed, before Material's bundle, and puts back, in
 * place of each link, the group it stands for. The developer manual exists only in English: the pages of `/it/developer/…`
 * are redirects, every link of the other pages leads to `/developer/…`, and the language selector shows English, read
 * only, on its pages (`hooks/developer_english_only.py`, `javascripts/site-lang-selector.js`). The unit tests pin the hooks
 * on a synthetic site and on a copy of real pages; this is the browser's side, on the built site served by the lane.
 *
 * Covered, on an English page and an Italian one of the same place (`user/fx/`, which has groups to put back at several
 * depths and is itself the page of an open group):
 *
 *   SN-01/02  the page as the lane serves it is the shrunk one (it carries `data-lf-nav` and at least one link standing
 *             for a group), the lane answered the language's menu file (200, `immutable`: its name is its content's hash),
 *             and in the page the browser ends up with, no such link is left: each stands as the group it replaced, with
 *             that group's pages inside, the first of them the very page the link led to; the groups of the page's own
 *             branch are open and the current page is the active link of the menu;
 *   SN-03/04  a group put back is a group Material drives: it starts «indeterminate» (shown expanded, as `navigation.expand`
 *             draws a group outside the page's branch), a first click on its label folds it, a second opens it (its toggle
 *             checked, its first page on screen); on a phone, through the drawer, the first click opens it;
 *   SN-05     from the Italian page every link of the menu to the developer manual leads to `/developer/…`, never to
 *             `/it/developer/…`; following one lands on an English page whose language selector is read only (it does not
 *             open), and the visitor's stored language is still Italian;
 *   SN-06     an old address of the developer manual in Italian (`/it/developer/…`, a bookmark, an outside link) ends on the
 *             English page, with its query and its anchor.
 *
 * Selectors: Material's own markup has no test ids, so, as in the sibling specs, the markup is the contract under test:
 * `.md-sidebar--primary`, `li.md-nav__item--nested`, `.md-nav__item--pruned`, `.md-nav__toggle`, `a.md-nav__link--active`,
 * `.site-lang-selector`. No text of a label is read: it is translated.
 *
 * Waiting: on conditions — the page's own load, Playwright's retrying assertions. Never on the clock. Read-only: the documentation
 * needs no sign-in and nothing is written; the only state is the browser context's own `localStorage`.
 *
 * Needs: the docs site built after the hooks and the script are in (`./dev.py mkdocs build`; the lane's server rebuilds a
 * site older than a `.md`, not one older than a hook or a script alone). A site built before them is a red precondition (no
 * `data-lf-nav`), never a skip.
 */
import {expect, test, type Locator, type Page} from '../fixtures/playwright';

/** The site's root, as the backend serves it. */
const SITE_ROOT = '/mkdocs/';
/** One place, two languages: a page of an open group, with groups to put back at several depths. */
const PAGES = [
    {id: 'SN-01', openId: 'SN-03', lang: 'en', path: `${SITE_ROOT}user/fx/`},
    {id: 'SN-02', openId: 'SN-04', lang: 'it', path: `${SITE_ROOT}it/user/fx/`},
] as const;
/** The Italian page whose menu leads to the developer manual. */
const ITALIAN_PATH = `${SITE_ROOT}it/user/fx/`;
/** A page of the developer manual that the Italian site no longer holds (a redirect), and what it points to. */
const OLD_ITALIAN_DEVELOPER = `${SITE_ROOT}it/developer/architecture/overview/`;
const ENGLISH_DEVELOPER = `${SITE_ROOT}developer/architecture/overview/`;

const PAGE_TIMEOUT_MS = 30_000;
/** The language selector stores the visitor's language here (`site-lang-selector.js`). */
const STORED_LANGUAGE_KEY = 'gallery-lang';

test.use({serviceWorkers: 'block'});
test.setTimeout(90_000);

interface Diagnostics {
    refused: string[];
    consoleErrors: string[];
    pageErrors: string[];
    laneFailures: string[];
    /** The lane's answers for the shared menu file: `<status> <path> <cache-control>`. */
    menuAnswers: string[];
}

/**
 * The screenshots of the gallery (`gallery/<viewport>/<lang>/<theme>/…`): the pages of `user/` ask for them, and a lane's site
 * need not hold them (they are generated apart: `dev.py mkdocs gallery`). Their 404 says nothing about the menu.
 */
function isGalleryImage(url: URL): boolean {
    return /\/mkdocs\/gallery\/.*\.(webp|png)$/.test(url.pathname);
}

/** Refuses every origin but the lane's, as a machine without internet would, and records what the page does. Armed before the navigation. */
async function watch(page: Page, origin: string): Promise<Diagnostics> {
    const diag: Diagnostics = {refused: [], consoleErrors: [], pageErrors: [], laneFailures: [], menuAnswers: []};
    await page.route(
        (url) => (url.protocol === 'http:' || url.protocol === 'https:') && url.origin !== origin,
        (route) => {
            diag.refused.push(route.request().url());
            return route.abort('blockedbyclient');
        },
    );
    page.on('console', (message) => {
        if (message.type() !== 'error' || isGalleryImage(new URL(message.location().url || 'http://none/'))) return;
        diag.consoleErrors.push(`${message.text()} (${message.location().url})`);
    });
    page.on('pageerror', (error) => diag.pageErrors.push(error.message));
    page.on('response', (response) => {
        const url = new URL(response.url());
        if (url.origin !== origin) return;
        if (response.status() >= 400 && !isGalleryImage(url)) diag.laneFailures.push(`${response.status()} ${url.pathname}`);
        if (/\/javascripts\/nav\/nav\.[a-z]{2}\.[0-9a-f]{10}\.js$/.test(url.pathname)) {
            diag.menuAnswers.push(`${response.status()} ${url.pathname} ${response.headers()['cache-control'] ?? ''}`);
        }
    });
    page.on('requestfailed', (request) => {
        const url = new URL(request.url());
        if (url.origin === origin) diag.laneFailures.push(`failed ${url.pathname}: ${request.failure()?.errorText ?? ''}`);
    });
    return diag;
}

/** What every test ends with: nothing uncaught, nothing of the lane failed, and the only console errors are the echoes of the refusals. */
function expectClean(diag: Diagnostics): void {
    expect(diag.pageErrors, 'no uncaught error on the page').toEqual([]);
    expect(diag.laneFailures, 'no request to the lane failed or was answered 4xx/5xx').toEqual([]);
    const strangers = diag.consoleErrors.filter((text) => !(/net::ERR_BLOCKED_BY_CLIENT/.test(text) && diag.refused.some((url) => text.includes(url))));
    expect(strangers, 'no console error but the echo of a refused request (fonts, GitHub, the donation button)').toEqual([]);
}

function laneOrigin(baseURL: string | undefined): string {
    if (!baseURL) throw new Error('This spec needs the runner-provided baseURL');
    return new URL(baseURL).origin;
}

/** The stubs of a served page: the pathname each link standing for a group leads to (the group's first page). */
function stubTargets(servedHtml: string, pageUrl: string): string[] {
    const targets = [...servedHtml.matchAll(/<li class="md-nav__item md-nav__item--pruned md-nav__item--nested">\s*<a href="([^"]*)"/g)];
    return targets.map((match) => new URL(match[1], pageUrl).pathname);
}

/** Goes to `path`, reads the page as the lane serves it, and checks it is the shrunk page of the built documentation. */
async function openShrunkPage(page: Page, path: string, lang: string): Promise<string[]> {
    const served = await page.request.get(path);
    expect(served.status(), `precondition: the lane serves ${path}`).toBe(200);
    const html = await served.text();
    expect(html, `precondition: ${path} is the page the shared-menu hook wrote (data-lf-nav): build the docs after the hook is in`).toContain(`data-lf-nav="${lang}"`);
    const targets = stubTargets(html, new URL(path, 'http://lane').href);
    expect(targets.length, `precondition: ${path} left links standing for groups in its menu`).toBeGreaterThan(0);
    const response = await page.goto(path, {timeout: PAGE_TIMEOUT_MS});
    expect(response?.status()).toBe(200);
    await expect(page.locator('html'), `${path} says lang=${lang}`).toHaveAttribute('lang', lang);
    return targets;
}

/** On a phone the menu lives in the drawer: opens it. On a desktop it is already there. */
async function showMenu(page: Page, isMobile: boolean): Promise<void> {
    if (isMobile) await page.locator('.md-header__button[for="__drawer"]').click();
    await expect(page.locator('.md-sidebar--primary'), 'the menu is on screen').toBeVisible();
}

/**
 * The group of the menu that stands for `target` (its first page is the pathname `target`): a nested item of the page's
 * primary menu, not pruned, whose first link leads there. Returns the id of its toggle, which is also the `for` of its label.
 */
async function groupToggleId(page: Page, target: string): Promise<string | null> {
    return page.evaluate((wanted) => {
        const nav = document.querySelector('.md-sidebar--primary nav.md-nav--primary');
        if (!nav) return null;
        const groups = [...nav.querySelectorAll('li.md-nav__item--nested')];
        const group = groups.find((li) => !li.classList.contains('md-nav__item--pruned') && new URL((li.querySelector('a[href]') as HTMLAnchorElement).href).pathname === wanted);
        return group?.querySelector(':scope > input.md-nav__toggle')?.id ?? null;
    }, target);
}

for (const {id, lang, path} of PAGES) {
    test(`${id}: the menu of the ${lang} page is put back from the shared file`, async ({page, baseURL}) => {
        const diag = await watch(page, laneOrigin(baseURL));

        const targets = await openShrunkPage(page, path, lang);

        const menu = page.locator('.md-sidebar--primary nav.md-nav--primary');
        await expect(menu).toHaveAttribute('data-lf-nav', lang);
        // The lane answered the language's file, and said it can be kept: its name is the hash of its content.
        expect(diag.menuAnswers, 'the lane answered the shared menu file of the language, once, immutable').toEqual([expect.stringMatching(new RegExp(`^200 ${SITE_ROOT}javascripts/nav/nav\\.${lang}\\.[0-9a-f]{10}\\.js .*\\bimmutable\\b`))]);
        // No link standing for a group is left…
        await expect(menu.locator('.md-nav__item--pruned'), 'no link standing for a group is left in the menu').toHaveCount(0);
        // …each is the group it stood for: a nested item whose pages are inside and whose first page is the one it led to.
        for (const target of targets) {
            const toggleId = await groupToggleId(page, target);
            expect(toggleId, `the group of ${target} is back in the menu`).not.toBeNull();
            const group = menu.locator(`li.md-nav__item--nested:has(> input#${toggleId})`);
            expect(await group.locator(':scope > nav a[href]').count(), `the group of ${target} holds its pages`).toBeGreaterThan(0);
            const first = await group
                .locator('a[href]')
                .first()
                .evaluate((a) => new URL((a as HTMLAnchorElement).href).pathname);
            expect(first, `the first page of the group is the page its link led to`).toBe(target);
        }
        // The page's own branch is open, and the current page is the active link of the menu.
        const open = menu.locator('li.md-nav__item--nested.md-nav__item--active > input.md-nav__toggle');
        expect(await open.count(), 'the page is inside at least one group').toBeGreaterThan(0);
        for (const toggle of await open.all()) await expect(toggle, 'every group of the page’s own branch is open').toBeChecked();
        // (The table of contents of the page sits in the menu too, with its own active links: the menu's pages only.)
        const activePages = await menu.locator('a.md-nav__link--active').evaluateAll((links) => links.filter((a) => !a.closest('.md-nav--secondary')).map((a) => new URL((a as HTMLAnchorElement).href).pathname));
        expect(activePages, 'the current page is the one active link of the menu').toEqual([path]);

        expectClean(diag);
    });
}

for (const {openId, lang, path} of PAGES) {
    test(`${openId}: a group put back opens with a click on its label (${lang})`, async ({page, baseURL, isMobile}) => {
        const diag = await watch(page, laneOrigin(baseURL));
        const targets = await openShrunkPage(page, path, lang);
        await showMenu(page, isMobile);

        // A group the visitor can reach: one whose own parents are all open (the groups of other branches sit inside closed ones).
        let label: Locator | null = null;
        let toggleId: string | null = null;
        for (const target of targets) {
            const candidate = await groupToggleId(page, target);
            if (!candidate) continue;
            const item = page.locator(`.md-sidebar--primary li.md-nav__item--nested:has(> input#${candidate})`);
            const reachable = await item.evaluate((li) => {
                const parent = li.parentElement?.closest('li.md-nav__item--nested');
                return !parent || parent.classList.contains('md-nav__item--active');
            });
            if (reachable && (await item.locator(':scope > label.md-nav__link').isVisible())) {
                label = item.locator(':scope > label.md-nav__link');
                toggleId = candidate;
                break;
            }
        }
        expect(toggleId, 'precondition: the menu offers a group put back that can be reached').not.toBeNull();
        const toggle = page.locator(`input#${toggleId}`);
        const state = () => toggle.evaluate((input: HTMLInputElement) => ({checked: input.checked, indeterminate: input.indeterminate}));

        // The state Material gives a group outside the page's branch when `navigation.expand` is on: «indeterminate» (shown
        // expanded, a first click folds it). It comes from the markup the script put back (`md-toggle--indeterminate`) and
        // Material's bundle; a group put back without it would start folded or never fold.
        await expect(toggle).toHaveClass(/\bmd-toggle--indeterminate\b/);
        expect(await state(), 'a group put back starts indeterminate, as Material draws it').toEqual({checked: false, indeterminate: true});

        const pagesOfGroup = page.locator(`.md-sidebar--primary li.md-nav__item--nested:has(> input#${toggleId}) > nav a[href]`).first();
        await label!.click();
        if (isMobile) {
            // In the drawer a group is a panel that slides in: the first click opens it, whatever «indeterminate» said.
            await expect.poll(state, {message: 'the click opened the group'}).toEqual({checked: true, indeterminate: false});
            await expect(pagesOfGroup, 'its first page is on screen').toBeVisible();
        } else {
            // On a desktop the first click folds a group shown expanded, the second opens it again.
            await expect.poll(state, {message: 'the first click folds it: Material took the toggle over'}).toEqual({checked: false, indeterminate: false});
            await label!.click();
            await expect.poll(state, {message: 'the second click opens it'}).toEqual({checked: true, indeterminate: false});
            await expect(pagesOfGroup, 'its first page is on screen').toBeVisible();
        }
        expectClean(diag);
    });
}

test('SN-05: the developer manual is reached in English, and its language selector is read only', async ({page, baseURL, isMobile}) => {
    const diag = await watch(page, laneOrigin(baseURL));
    await openShrunkPage(page, ITALIAN_PATH, 'it');
    await showMenu(page, isMobile);

    // Every link of the Italian menu to the developer manual leads to the English pages.
    const hrefs = await page.locator('.md-sidebar--primary nav.md-nav--primary a[href]').evaluateAll((links) => links.map((a) => new URL((a as HTMLAnchorElement).href).pathname));
    const toDeveloper = hrefs.filter((pathname) => pathname.includes('/developer/'));
    expect(toDeveloper.length, 'precondition: the menu leads to the developer manual').toBeGreaterThan(0);
    expect(
        toDeveloper.filter((pathname) => !pathname.startsWith(`${SITE_ROOT}developer/`)),
        'no link leads to /it/developer/…',
    ).toEqual([]);
    expect(await page.evaluate((key) => localStorage.getItem(key), STORED_LANGUAGE_KEY), 'precondition: the visitor’s language is Italian').toBe('it');

    // Follow one: an English page, whose selector shows English, read only.
    await page.goto(toDeveloper[0], {timeout: PAGE_TIMEOUT_MS});
    await expect(page.locator('html')).toHaveAttribute('lang', 'en');
    const selector = page.locator('.site-lang-selector');
    await expect(selector, 'the language selector of a developer page is read only').toHaveClass(/\blang-readonly\b/);
    await expect(selector).toHaveAttribute('title', /\S/);
    await selector.locator('.site-lang-btn').click();
    await expect(selector, 'a click does not open it').not.toHaveClass(/\bopen\b/);
    expect(await page.evaluate((key) => localStorage.getItem(key), STORED_LANGUAGE_KEY), 'the visitor’s language is untouched').toBe('it');

    expectClean(diag);
});

test('SN-06: an old Italian address of the developer manual ends on the English page, with its query and its anchor', async ({page, baseURL}) => {
    const diag = await watch(page, laneOrigin(baseURL));

    await page.goto(`${OLD_ITALIAN_DEVELOPER}?from=bookmark#overview`, {timeout: PAGE_TIMEOUT_MS, waitUntil: 'commit'});

    await page.waitForURL((url) => url.pathname === ENGLISH_DEVELOPER, {timeout: PAGE_TIMEOUT_MS});
    const url = new URL(page.url());
    expect(url.search, 'the query is kept').toBe('?from=bookmark');
    expect(url.hash, 'the anchor is kept').toBe('#overview');
    await expect(page.locator('html')).toHaveAttribute('lang', 'en');
    await expect(page.locator('meta[name="generator"]')).toHaveAttribute('content', /\bmkdocs-/);
    expectClean(diag);
});
