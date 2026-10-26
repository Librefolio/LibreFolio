/**
 * Documentation search by language — DOC-2, route B (lot of workstream H). Written RED-FIRST on the contract the coordinator
 * approved (route B, the label in four languages, a line in `hooks:`, this E2E), and NOT run when it was written: it needs a
 * slot (a lane serving the built documentation), and the documentation built with the new hook and script.
 *
 * Material downloads one `search/search_index.json` for the four languages of the site, so a visitor searching in Italian
 * saw the Italian, English, French and Spanish page of the same topic together. Now:
 *
 *   - `hooks/search_language_split.py` writes `search/search_index.<lang>.json` after the build (en = the pages with no
 *     language folder), and
 *   - `javascripts/search-language.js`, loaded in the head before Material's bundle, wraps `fetch` so the page asks for the
 *     file of `<html lang>`; a checkbox in the search dialog (`data-testid="docs-search-all-languages"`) asks for the full
 *     index instead: it stores the preference in `localStorage`, keeps the typed query in `sessionStorage` and reloads, and
 *     after the reload the search opens again with the query in it.
 *
 * Covered, for each of the four languages' home pages (SL-01…04) and then on the Italian one:
 *
 *   SL-01…04  by default, a search finds results of the page's own language ONLY — `/mkdocs/it/…` for an Italian page,
 *             `/mkdocs/…` outside the language folders for the English one —; the lane answered
 *             `/mkdocs/search/search_index.<lang>.json` (200) and was never asked for the full `search_index.json`; the
 *             toggle is there, unchecked;
 *   SL-05     the toggle on the Italian page: the page reloads, the query is still in the field, the toggle is checked,
 *             results of ALL four languages show for the same query, and the lane answered the full index;
 *   SL-06     from that state the toggle off: the page reloads, the query is still there, results are Italian only again,
 *             the Italian index is what the lane answers last;
 *   SL-07     the preference holds on another page: with it stored, the French home page searches all four languages and
 *             its toggle is checked.
 *
 * The query is «sharpe»: a name the Sharpe-ratio pages carry untranslated in the four languages, so the same search has
 * results in each (measured on the built index: 3 English pages, 2 each in Italian, French and Spanish, and their
 * sections). Nothing here counts results — it reads which LANGUAGE each result link belongs to, by the first folder of its
 * path under `/mkdocs/`.
 *
 * Selectors: the toggle by `data-testid`. Material's own markup has no test ids, so, as in `layout/page-policy.spec.ts`:
 * `.md-search__input` (the field), `.md-header__button[for="__search"]` (opens it on a phone), `.md-search-result__item`
 * (a result), `.md-search-result__link` (a link of it), `.md-search__scrollwrap` (what scrolls the result list: Material
 * draws it in batches as it scrolls). Never the toggle's label text: it is translated, and `LABELS` is the script's.
 *
 * Waiting: on what the user sees — a result visible, the field's value, the toggle's state —, on the lane's answers recorded
 * from before the navigation (a response is an event), and on `expect.poll` for the languages of the results, which scrolls
 * the list so the next batch is drawn. The reload of the toggle is an event armed before the click (`waitForEvent('load')`).
 * Never on the clock. An absence («only Italian») is asserted behind its presence barriers: a result is on screen, and the
 * language file the page chose was answered.
 *
 * Read-only on the server, parallel by default: the documentation needs no sign-in and nothing is written. The state the
 * toggle changes (`localStorage`, `sessionStorage`) belongs to the test's own browser context, which dies with the test.
 *
 * Needs: `./dev.py mkdocs build` after the hook and the script are in (the lane's `dev.py server` rebuilds a site older
 * than a `.md`, not one older than a script or a hook alone: M-21). An unbuilt site answers «Documentation not generated»; a
 * site built before this lot answers 404 for `search_index.<lang>.json`: a red precondition here, never a skip.
 */
import {expect, test, type Page} from '../fixtures/playwright';

/** The site's root, as the backend serves it. */
const SITE_ROOT = '/mkdocs/';
const SEARCH_INDEX_FULL = `${SITE_ROOT}search/search_index.json`;
const PREFERENCE_KEY = 'lf-docs-search-all-languages';
const QUERY = 'sharpe';
const TOGGLE_ID = 'docs-search-all-languages';

type Language = 'en' | 'it' | 'fr' | 'es';
const ALL_LANGUAGES: Language[] = ['en', 'es', 'fr', 'it'];

/** The home page of each language, as the built site has them. */
const HOMES: Array<{id: string; lang: Language; path: string}> = [
    {id: 'SL-01', lang: 'it', path: `${SITE_ROOT}it/`},
    {id: 'SL-02', lang: 'fr', path: `${SITE_ROOT}fr/`},
    {id: 'SL-03', lang: 'es', path: `${SITE_ROOT}es/`},
    {id: 'SL-04', lang: 'en', path: SITE_ROOT},
];

/** A documentation page with its scripts and styles, on a loaded machine. */
const PAGE_TIMEOUT_MS = 30_000;
/** Material's search: an index fetched, read into its worker, a result drawn — on a loaded machine. */
const SEARCH_TIMEOUT_MS = 30_000;

test.setTimeout(90_000);

/** The documentation does not need the app's service worker, and its offline fallback must never answer a documentation page. */
test.use({serviceWorkers: 'block'});

function languageIndexPath(lang: Language): string {
    return `${SITE_ROOT}search/search_index.${lang}.json`;
}

/**
 * Every answer the lane gives to a request for a search index (the full one or a language's), `<status> <path>`, in order.
 * Armed before the navigation: a response is an event, and one that has gone by is not replayed.
 */
function recordIndexAnswers(page: Page): string[] {
    const answers: string[] = [];
    page.on('response', (response) => {
        const url = new URL(response.url());
        if (/\/search\/search_index(\.[a-z]{2})?\.json$/.test(url.pathname)) answers.push(`${response.status()} ${url.pathname}`);
    });
    return answers;
}

/** The documentation's language of a path under the site's root: the language folder it is in, `en` outside them. */
function languageOfPath(pathname: string): Language {
    const first = pathname.startsWith(SITE_ROOT) ? pathname.slice(SITE_ROOT.length).split('/')[0] : '';
    return first === 'it' || first === 'fr' || first === 'es' ? first : 'en';
}

/** Goes to `path` and checks it is a page of the built documentation, in the language the test thinks it is. */
async function openDocsPage(page: Page, path: string, lang: Language): Promise<void> {
    const response = await page.goto(path, {timeout: PAGE_TIMEOUT_MS});
    expect(response?.status(), `precondition: the lane serves ${path} (a 404 is a page that moved)`).toBe(200);
    await expect(page.locator('meta[name="generator"]'), `precondition: ${path} is a page of the built documentation — an unbuilt site answers «Documentation not generated»: build it, see this file's header`).toHaveAttribute('content', /\bmkdocs-/);
    await expect(page.locator('html'), `precondition: ${path} says lang=${lang}`).toHaveAttribute('lang', lang);
}

/** Material's own way in: the field itself on a desktop header; on a phone, the header's search button, which opens the field and focuses it. */
async function openSearch(page: Page, isMobile: boolean): Promise<void> {
    const query = page.locator('.md-search__input');
    await (isMobile ? page.locator('.md-header__button[for="__search"]') : query).click();
    await expect(query, 'Material opened its search: the field has the focus').toBeFocused();
}

/** Types the query key by key: Material reads it on keyup. */
async function typeQuery(page: Page): Promise<void> {
    await page.locator('.md-search__input').pressSequentially(QUERY);
    await expect(page.locator('.md-search-result__item').first(), `Material's search found «${QUERY}»: its index fetched, read by its worker, a result drawn`).toBeVisible({timeout: SEARCH_TIMEOUT_MS});
}

/** The languages of the results drawn so far, each once, sorted: by the first folder of every result link's path. */
async function resultLanguages(page: Page): Promise<Language[]> {
    const paths = await page.locator('.md-search-result__link').evaluateAll((links) => links.map((link) => new URL((link as HTMLAnchorElement).href).pathname));
    return [...new Set(paths.map(languageOfPath))].sort();
}

/** Scrolls the result list to its end, so that Material draws the next batch. */
async function scrollResults(page: Page): Promise<void> {
    await page.locator('.md-search__scrollwrap').evaluate((element) => {
        element.scrollTop = element.scrollHeight;
    });
}

/** Stores the «all languages» preference as the toggle does, then reloads, so that the page starts under it. */
async function storePreferenceAndReload(page: Page): Promise<void> {
    await page.evaluate((key) => window.localStorage.setItem(key, '1'), PREFERENCE_KEY);
    await page.reload({timeout: PAGE_TIMEOUT_MS});
}

/** Clicks the toggle and waits for the page it makes: the reload is armed before the click. */
async function clickToggleAndWaitForReload(page: Page): Promise<void> {
    const reloaded = page.waitForEvent('load', {timeout: PAGE_TIMEOUT_MS});
    await page.getByTestId(TOGGLE_ID).click();
    await reloaded;
}

test.describe('Documentation search by language (DOC-2, route B)', () => {
    for (const home of HOMES) {
        test(`${home.id}: on the ${home.lang} home page, the search finds ${home.lang} pages only, from ${home.lang}'s own index`, async ({page, isMobile}) => {
            const answers = recordIndexAnswers(page);
            await openDocsPage(page, home.path, home.lang);
            await openSearch(page, isMobile);

            const toggle = page.getByTestId(TOGGLE_ID);
            await expect(toggle, 'the toggle is in the search dialog').toBeVisible();
            await expect(toggle, 'and unchecked: no preference stored in a fresh context').not.toBeChecked();

            await typeQuery(page);

            await expect.poll(() => answers, {message: `the lane answered the ${home.lang} index: the page asked for its own language's file`, timeout: SEARCH_TIMEOUT_MS}).toContain(`200 ${languageIndexPath(home.lang)}`);
            expect(
                answers.filter((answer) => answer.endsWith(` ${SEARCH_INDEX_FULL}`)),
                'the full 10 MB index was never fetched: that is what this route saves',
            ).toEqual([]);
            expect(
                answers.filter((answer) => !answer.startsWith('200 ')),
                `no index request failed — a 404 for search_index.${home.lang}.json is a site built without the hook: ./dev.py mkdocs build`,
            ).toEqual([]);

            await expect.poll(() => resultLanguages(page), {message: `every result is a ${home.lang} page`, timeout: SEARCH_TIMEOUT_MS}).toEqual([home.lang]);
        });
    }

    test('SL-05: the toggle on the Italian page reloads it with the query kept, the toggle checked, results in all four languages and the full index', async ({page, isMobile}) => {
        const answers = recordIndexAnswers(page);
        await openDocsPage(page, `${SITE_ROOT}it/`, 'it');
        await openSearch(page, isMobile);
        await typeQuery(page);
        await expect.poll(() => resultLanguages(page), {message: 'before the toggle: Italian only (precondition of this test)', timeout: SEARCH_TIMEOUT_MS}).toEqual(['it']);

        await clickToggleAndWaitForReload(page);

        // The query is still there: the search opened again by itself, the typed word in the field.
        await expect(page.locator('.md-search__input'), 'the search opened again after the reload, with the typed query in it').toHaveValue(QUERY);
        await expect(page.getByTestId(TOGGLE_ID), 'the toggle shows the stored preference').toBeChecked();
        await expect(page.locator('.md-search-result__item').first(), 'the restored query was searched: a result is drawn').toBeVisible({timeout: SEARCH_TIMEOUT_MS});

        await expect.poll(() => answers, {message: 'the lane answered the full index, every language', timeout: SEARCH_TIMEOUT_MS}).toContain(`200 ${SEARCH_INDEX_FULL}`);
        await expect
            .poll(
                async () => {
                    await scrollResults(page);
                    return resultLanguages(page);
                },
                {message: 'results of all four languages are listed for the same query', timeout: SEARCH_TIMEOUT_MS},
            )
            .toEqual(ALL_LANGUAGES);
    });

    test('SL-06: the toggle off again: the page reloads with the query kept and the search is Italian only, from the Italian index', async ({page, isMobile}) => {
        const answers = recordIndexAnswers(page);
        await openDocsPage(page, `${SITE_ROOT}it/`, 'it');
        await storePreferenceAndReload(page);
        await openSearch(page, isMobile);
        await expect(page.getByTestId(TOGGLE_ID), 'precondition: the page starts under «all languages»').toBeChecked();
        await typeQuery(page);
        await expect.poll(() => answers, {message: 'precondition: under the preference the page fetched the full index', timeout: SEARCH_TIMEOUT_MS}).toContain(`200 ${SEARCH_INDEX_FULL}`);
        const before = answers.length;

        await clickToggleAndWaitForReload(page);

        await expect(page.locator('.md-search__input'), 'the search opened again after the reload, with the typed query in it').toHaveValue(QUERY);
        await expect(page.getByTestId(TOGGLE_ID), 'the preference is gone').not.toBeChecked();
        await expect(page.locator('.md-search-result__item').first(), 'the restored query was searched: a result is drawn').toBeVisible({timeout: SEARCH_TIMEOUT_MS});
        await expect.poll(() => answers.slice(before), {message: 'after the reload the lane answered the Italian index', timeout: SEARCH_TIMEOUT_MS}).toContain(`200 ${languageIndexPath('it')}`);
        expect(
            answers.slice(before).filter((answer) => answer.endsWith(` ${SEARCH_INDEX_FULL}`)),
            'and not the full one again',
        ).toEqual([]);
        await expect.poll(() => resultLanguages(page), {message: 'every result is an Italian page again', timeout: SEARCH_TIMEOUT_MS}).toEqual(['it']);
    });

    test('SL-07: the stored preference holds on another page: the French home page searches all four languages, its toggle checked', async ({page, isMobile}) => {
        const answers = recordIndexAnswers(page);
        await openDocsPage(page, `${SITE_ROOT}it/`, 'it');
        await storePreferenceAndReload(page);

        await openDocsPage(page, `${SITE_ROOT}fr/`, 'fr');
        await openSearch(page, isMobile);
        await expect(page.getByTestId(TOGGLE_ID), 'the preference of the Italian page is the French page’s too: same origin, same storage').toBeChecked();
        await typeQuery(page);

        await expect.poll(() => answers.filter((answer) => answer.endsWith(` ${SEARCH_INDEX_FULL}`)).length, {message: 'the French page fetched the full index', timeout: SEARCH_TIMEOUT_MS}).toBeGreaterThan(1);
        await expect
            .poll(
                async () => {
                    await scrollResults(page);
                    return resultLanguages(page);
                },
                {message: 'results of all four languages are listed on the French page', timeout: SEARCH_TIMEOUT_MS},
            )
            .toEqual(ALL_LANGUAGES);
    });
});
