/**
 * Asset detail ‹ n/N › — browse to the previous or next asset from the detail page (K step 16, item 2; developer's
 * decisions, 06/10).
 *
 * Written RED-FIRST, before the feature: none of the DOM below exists yet, so every test stops at its first browse
 * assertion — `asset-browse` never appears. Everything before it (the assets created, the list searched and read, the
 * detail page opened from it) is setup that must already work today.
 *
 * The decisions, as tested:
 *   - two buttons `‹ n/N ›` in the detail header — buttons only, no keyboard: nothing here presses a key;
 *   - they follow "the list I left": its filters, its view (grid or table) and, in the table, its column sort. The
 *     expected order is read from the list's DOM — the cards of the grid, the rows of the table — never assumed;
 *   - with no list to follow (direct link, Dashboard, Transactions, reload, an asset not in that list) they follow
 *     all assets in the list's default order. Exercised here by a direct `page.goto`;
 *   - a move replaces the current history entry: ONE Back — the header's `asset-detail-back-btn` or the browser's —
 *     returns to the list, however many moves were made;
 *   - disabled at the edges, no wrap-around; the URL query (`?start&end`, the list's dates) is kept across moves.
 *
 * The DOM contract K implements after this red run:
 *   [data-testid="asset-browse"]          data-state="pending|ready|none", data-source="list|default"
 *     [data-testid="asset-browse-nav"]    rendered once ready, holding
 *       asset-browse-prev, asset-browse-next    buttons, disabled at the edges
 *       asset-browse-position                   `{index}/{total}`, 1-based
 * A move lands on /assets/{otherId} and the page reloads its data. Each move therefore waits for the URL, for the h2
 * inside `asset-detail-info` to name the asset (the names are the test's own data, not translations) and for
 * `asset-detail-page` to publish data-busy="false".
 *
 * Phone widths (390×844 and 360×780, set per test with `setViewportSize`, so the spec means the same thing whichever
 * project runs it; the runner runs `desktop`): the nav's buttons and counter lie inside the layout, and the page does
 * not scroll sideways. The layout's edge is the right of <html>'s box, not clientWidth: `html { scrollbar-gutter:
 * stable }` reserves the scrollbar's width, headless Chromium hides the bar but keeps the gutter (15 px on the
 * developer's Mac), and clientWidth counts that hidden gutter as room. The page check is the toolbar sweep's
 * (`layout/toolbar-width-sweep.spec.ts`): every box and text run of the page against that edge, except popups,
 * anything fixed, empty boxes and what a scrolling or clipping container hides; the furthest past it is the overflow,
 * and the outermost culprits are named in the message. Positive control: a box the test hangs past the edge — inside
 * the window when there is a gutter — must come back from the same reader, as a part and as page overflow.
 *
 * Ownership. Each test creates its own three EUR stocks over the API, in one list payload, named
 * `E2E Browse <unique token> Alpha|Beta|Gamma`: searching the list for the token shows those three and nothing else,
 * and with no transactions they share one usage panel. The `owned` fixture deletes them by id whatever the outcome,
 * once the routes are detached and the page has left them. No price is needed and none is written.
 *
 * Offline. Every request to another origin is refused (seeded icon URLs point at the internet), and POST
 * /assets/prices/current — polled by the list and the detail page, it asks the live providers and writes today's row —
 * is answered empty.
 *
 * Review defects (06/10), pinned RED-FIRST after AB-001..AB-006 went green on K's implementation — both about the
 * date range a move carries:
 *   AB-007  "All" (MAX) does not re-resolve per asset. Choosing it resolves the start from the chart's first point
 *           (`resolveMaxStartFromChartData`); a same-route move reloads the data without re-arming that, so the next
 *           asset keeps the previous one's earliest date. Two assets of the test's own carry stored daily closes over
 *           different spans — Alpha the last 30 days, Beta the last 200 — and the backend starts a series at the first
 *           stored close, so each one's "All" start is known exactly: after Next, the picker's start must be Beta's
 *           earliest close, not Alpha's, with "All" still the active preset.
 *   AB-008  A move must carry the range the page shows. The detail page writes a new range into the address bar with
 *           `history.replaceState`, which SvelteKit does not track, and a URL built from SvelteKit's copy carries the
 *           range the page was opened with. After 1Y on the detail page, Next must carry the range the address bar
 *           showed before the click, and a reload must bring that range back.
 * The picker is read as it is shown: in the detail page's compact picker the two fields hold ISO dates. While "All" is
 * pending, the start field holds a translated placeholder, which nothing here reads: the wait is for the date.
 *
 * Deliberately not asserted:
 *   - translated text: only test ids, attributes, URLs, geometry and the names the test created;
 *   - the default order's neighbours and total: the database is shared with parallel tests, so AB-004 asserts only
 *     relations — a total of at least four (more than the filtered three), and Next one step forward;
 *   - `data-state="none"` (fewer than two assets) and an asset missing from the list left behind: outside this
 *     step's test list.
 *
 * Registration: `front_asset_browse` in `scripts/test_runner/_frontend_asset.py`, action `asset-browse`
 * (`./dev.py test front-asset asset-browse`).
 *
 * Test IDs: AB-001..AB-008
 */

import {expect, test as base, type Locator, type Page} from '../fixtures/playwright';
import {login} from '../fixtures/auth-helpers';
import {waitForSettled} from '../fixtures/app-events';
import {daysAgoIso} from '../fixtures/dates';
import {TEST_USER} from '../fixtures/test-users';
import {uniqueSuffix} from '../fixtures/unique';
import {schemas} from '../../src/lib/api/generated';
import {API_BASE, goToAssetDetailPage, goToAssetsPage} from './assets-helpers';

type Viewport = {id: string; width: number; height: number};
const PHONES: readonly Viewport[] = [
    {id: 'AB-005', width: 390, height: 844},
    {id: 'AB-006', width: 360, height: 780},
];

/** The last word of each name, after the shared token. */
const WORDS = ['Alpha', 'Beta', 'Gamma'] as const;
/** The default order holds every active asset: at least one more than the three a search for the token leaves. */
const DEFAULT_TOTAL_AT_LEAST = 4;

/** `asset-browse` goes from pending to ready once it knows the list it follows. */
const BROWSE_READY_MS = 10_000;
/** Opening an asset, or moving to another one, reloads the detail page's data. */
const NAVIGATION_MS = 15_000;
/** The list loads every asset before the search narrows it to the test's three. */
const LIST_MS = 15_000;
/** Layout boxes are fractional: within half a pixel of an edge is inside it. */
const EDGE_TOLERANCE_PX = 0.5;
/** How many page-overflow culprits a failure message names. */
const MAX_NAMED = 6;
/** The positive control's box, hung past the layout's right edge by half the scrollbar gutter plus this. */
const PROBE_ID = 'lf-k16-browse-probe';
const PROBE_PAST_PX = 8;
/** The nav's parts that must lie inside the layout at phone width. */
const NAV_PARTS = ['asset-browse-prev', 'asset-browse-position', 'asset-browse-next'] as const;

type Owned = {assetIds: number[]};
type OwnedAsset = {id: number; name: string};
/** The test's three assets in creation order (Alpha, Beta, Gamma), and the token their names share. */
type Trio = {token: string; assets: OwnedAsset[]};
type Source = 'list' | 'default';
type Direction = 'prev' | 'next';
type HttpResponse = {ok(): boolean; status(): number; text(): Promise<string>; json(): Promise<unknown>};

interface BrowseControl {
    /** `asset-browse`: the wrapper, carrying `data-state` and `data-source`. */
    root: Locator;
    /** `asset-browse-nav`: the ‹ n/N › nav, rendered once ready. */
    nav: Locator;
    prev: Locator;
    next: Locator;
    position: Locator;
}

async function jsonFrom<T>(response: HttpResponse, purpose: string): Promise<T> {
    expect(response.ok(), `${purpose}: HTTP ${response.status()} ${await response.text()}`).toBeTruthy();
    return (await response.json()) as T;
}

/**
 * Delete what the test created, each step scoped to an id it recorded.
 *
 * Routes go first, then the page leaves the assets, so no poll or reload reads one while it goes. `page.request`
 * shares the browser's session.
 */
async function releaseOwned(page: Page, owned: Owned): Promise<void> {
    const failures: string[] = [];
    const attempt = async (label: string, action: () => Promise<unknown>) => {
        try {
            await action();
        } catch (error) {
            failures.push(`${label}: ${String(error)}`);
        }
    };
    await attempt('detach routes', () => page.unrouteAll({behavior: 'ignoreErrors'}));
    await attempt('leave the page', () => page.goto('about:blank'));
    for (const assetId of owned.assetIds) {
        await attempt(`asset ${assetId}`, async () => {
            const body = await jsonFrom<{results: Array<{asset_id: number; success: boolean; message?: string | null}>}>(await page.request.delete(`${API_BASE}/assets?asset_ids=${assetId}`), 'delete the owned asset');
            expect(body.results.find((result) => result.asset_id === assetId)?.success, `asset ${assetId} deleted: ${JSON.stringify(body)}`).toBe(true);
        });
    }
    expect(failures, 'every cleanup step is scoped to rows this test created').toEqual([]);
}

const test = base.extend<{owned: Owned}>({
    owned: async ({page}, use) => {
        const owned: Owned = {assetIds: []};
        try {
            await use(owned);
        } finally {
            await releaseOwned(page, owned);
        }
    },
});

// Login, API seeding, the list, three or four detail loads and the fixture's cleanup share the budget.
test.setTimeout(60_000);

test.beforeEach(async ({page}) => {
    await login(page, TEST_USER);
});

// =============================================================================
// Seeding and the network
// =============================================================================

/** Three plain EUR stocks, one list payload: `E2E Browse <token> Alpha|Beta|Gamma`. */
async function createTrio(page: Page, owned: Owned): Promise<Trio> {
    const token = uniqueSuffix();
    const names: string[] = WORDS.map((word) => `E2E Browse ${token} ${word}`);
    const items = names.map((name) => schemas.FAAssetCreateItem.parse({display_name: name, currency: 'EUR', asset_type: 'STOCK', active: true}));
    const response = await page.request.post(`${API_BASE}/assets`, {data: items});
    const body = (await response.json().catch(() => null)) as {results?: Array<{asset_id?: number | null; display_name: string; success: boolean; message?: string}>} | null;
    const results = body?.results ?? [];
    // Recorded before any assertion can throw: whatever was created gets deleted.
    for (const result of results) if (typeof result.asset_id === 'number' && names.includes(result.display_name)) owned.assetIds.push(result.asset_id);
    expect(response.status(), `POST ${API_BASE}/assets answers 201 to the three-item list: ${JSON.stringify(body)}`).toBe(201);
    const assets = names.map((name) => {
        const result = results.find((candidate) => candidate.display_name === name);
        if (!result?.success || typeof result.asset_id !== 'number') throw new Error(`"${name}" was not created: ${JSON.stringify(body)}`);
        return {id: result.asset_id, name};
    });
    return {token, assets};
}

/** Other origins refused; the live-price poll answered empty, so nothing is written back. Detached by the fixture. */
async function keepOffline(page: Page, baseURL: string | undefined): Promise<void> {
    if (!baseURL) throw new Error('the project sets baseURL: the app origin is the one that stays reachable');
    const origin = new URL(baseURL).origin;
    await page.route(
        (url) => (url.protocol === 'http:' || url.protocol === 'https:') && url.origin !== origin,
        (route) => route.abort('blockedbyclient'),
    );
    await page.route('**/api/v1/assets/prices/current', (route) => route.fulfill({json: {results: [], success_count: 0, errors: []}}));
}

/** How many active assets the backend holds right now — the precondition of AB-004, read over the API. */
async function activeAssetCount(page: Page): Promise<number> {
    const items = await jsonFrom<unknown[]>(await page.request.get(`${API_BASE}/assets/query?active=true`), 'list the active assets');
    return items.length;
}

/** The display name of an asset the test did not create (AB-004's neighbour), read over the API. */
async function displayNameOf(page: Page, assetId: number): Promise<string> {
    const items = await jsonFrom<Array<{asset_id: number; display_name: string}>>(await page.request.get(`${API_BASE}/assets?asset_ids=${assetId}`), `read asset ${assetId}`);
    const name = items.find((item) => item.asset_id === assetId)?.display_name;
    if (!name) throw new Error(`asset ${assetId} is not readable over the API: ${JSON.stringify(items)}`);
    return name;
}

// =============================================================================
// The list: what the user leaves behind
// =============================================================================

async function searchList(page: Page, token: string): Promise<void> {
    const search = page.getByTestId('assets-search-input');
    await search.fill(token);
    await expect(search).toHaveValue(token);
}

/** The ids as the list shows them, mapped onto the trio: exactly its three assets, each once — or a failure that says what was shown. */
function inListOrder(trio: Trio, ids: number[], where: string): OwnedAsset[] {
    const mine = new Map(trio.assets.map((asset) => [asset.id, asset]));
    const listed = ids.map((id) => mine.get(id)).filter((asset): asset is OwnedAsset => asset !== undefined);
    const exact = ids.length === trio.assets.length && listed.length === ids.length && new Set(ids).size === ids.length;
    expect(exact, `${where}: searched for the token, the list shows exactly this test's assets (${trio.assets.map((asset) => asset.id).join(', ')}) — it shows ${ids.join(', ') || 'nothing'}`).toBe(true);
    return listed;
}

/** /assets in the grid view, searched for the trio's token: the trio in the order of its cards in the DOM. */
async function gridOrderOf(page: Page, trio: Trio): Promise<OwnedAsset[]> {
    await goToAssetsPage(page);
    await page.getByTestId('view-mode-grid').click();
    await searchList(page, trio.token);
    for (const asset of trio.assets) await expect(page.getByTestId(`asset-card-${asset.id}`)).toBeVisible({timeout: LIST_MS});
    // The cards carry `data-lifecycle`; the controls inside a card share the `asset-card-` prefix and do not.
    const cards = page.locator('[data-testid^="asset-card-"][data-lifecycle]');
    // The token is the test's own: once the grid holds three cards, the search has been applied.
    await expect(cards, 'searched for its token, the grid holds the three cards of this test and nothing else').toHaveCount(trio.assets.length, {timeout: LIST_MS});
    const ids = await cards.evaluateAll((elements) => elements.map((element) => Number((element.getAttribute('data-testid') ?? '').slice('asset-card-'.length))));
    return inListOrder(trio, ids, 'the searched grid');
}

/** /assets in the table view, searched for the trio's token: the usage panel whose table holds the three rows. */
async function tableOf(page: Page, trio: Trio): Promise<Locator> {
    await goToAssetsPage(page);
    await page.getByTestId('view-mode-list').click();
    await searchList(page, trio.token);
    const tables = page.locator('[data-testid^="assets-table-panel-"]');
    for (const asset of trio.assets) await expect(tables.locator(`tr[data-row-id="${asset.id}"]`)).toBeVisible({timeout: LIST_MS});
    const rows = tables.locator('tr[data-row-id]');
    await expect(rows, 'searched for its token, the tables hold the three rows of this test and nothing else').toHaveCount(trio.assets.length, {timeout: LIST_MS});
    const panels = await rows.evaluateAll((elements) => [...new Set(elements.map((row) => row.closest('[data-testid^="assets-table-panel-"]')?.getAttribute('data-testid') ?? '(no panel)'))]);
    expect(panels, 'precondition: with no transactions the three assets share one usage panel, so one table orders them').toHaveLength(1);
    return page.getByTestId(panels[0]);
}

async function rowIds(table: Locator): Promise<number[]> {
    return table.locator('tr[data-row-id]').evaluateAll((rows) => rows.map((row) => Number(row.getAttribute('data-row-id'))));
}

/** The query of the current URL, as sorted `key=value` pairs: the same query whatever the order of its parameters. */
function queryOf(page: Page): string[] {
    return [...new URL(page.url()).searchParams.entries()].map(([key, value]) => `${key}=${value}`).sort();
}

// =============================================================================
// The detail page and its ‹ n/N ›
// =============================================================================

function headerName(page: Page): Locator {
    return page.getByTestId('asset-detail-info').locator('h2');
}

/** On /assets/{id}, the header naming the asset, every load wave in. */
async function expectDetailOf(page: Page, asset: OwnedAsset, why: string): Promise<void> {
    await expect(page, `${why}: the URL is /assets/${asset.id}`).toHaveURL((url) => url.pathname === `/assets/${asset.id}`, {timeout: NAVIGATION_MS});
    await expect(headerName(page), `${why}: the header names "${asset.name}"`).toHaveText(asset.name, {timeout: NAVIGATION_MS});
    await waitForSettled(page.getByTestId('asset-detail-page'), NAVIGATION_MS);
}

async function openCard(page: Page, asset: OwnedAsset): Promise<void> {
    await page.getByTestId(`asset-card-${asset.id}`).click();
    await expectDetailOf(page, asset, 'opened from its card');
}

async function openRow(page: Page, table: Locator, asset: OwnedAsset): Promise<void> {
    await table.locator(`tr[data-row-id="${asset.id}"]`).getByText(asset.name, {exact: true}).click();
    await expectDetailOf(page, asset, 'opened from its row');
}

function browseControl(page: Page): BrowseControl {
    const root = page.getByTestId('asset-browse');
    const nav = root.getByTestId('asset-browse-nav');
    return {root, nav, prev: nav.getByTestId('asset-browse-prev'), next: nav.getByTestId('asset-browse-next'), position: nav.getByTestId('asset-browse-position')};
}

/** The presence barrier of every browse assertion — and, until the feature lands, the first red of every test. */
async function expectBrowseReady(page: Page, source: Source): Promise<BrowseControl> {
    const browse = browseControl(page);
    await expect(browse.root, 'the detail header carries the browse control, settled on the list it follows: [data-testid="asset-browse"][data-state="ready"]').toHaveAttribute('data-state', 'ready', {timeout: BROWSE_READY_MS});
    await expect(browse.root, source === 'list' ? 'it follows the list the user left' : "with no list to follow, it follows the list's default order").toHaveAttribute('data-source', source);
    await expect(browse.nav, 'ready: the ‹ n/N › nav is shown').toBeVisible();
    return browse;
}

/** `{index}/{total}`, spaces around the slash tolerated; any total when `total` is null. */
function positionPattern(index: number | null, total: number | null): RegExp {
    return new RegExp(`^\\s*${index ?? '\\d+'}\\s*/\\s*${total ?? '\\d+'}\\s*$`);
}

/** The counter, and the buttons it implies: no wrap-around, so the first has no Previous and the last no Next. */
async function expectPosition(browse: BrowseControl, index: number, total: number): Promise<void> {
    await expect(browse.position, `the counter reads ${index}/${total}`).toHaveText(positionPattern(index, total));
    if (index === 1) await expect(browse.prev, 'first of the list: Previous is disabled — no wrap-around').toBeDisabled();
    else await expect(browse.prev, `${index}/${total}: Previous is enabled`).toBeEnabled();
    if (index === total) await expect(browse.next, 'last of the list: Next is disabled — no wrap-around').toBeDisabled();
    else await expect(browse.next, `${index}/${total}: Next is enabled`).toBeEnabled();
}

async function readPosition(browse: BrowseControl): Promise<{index: number; total: number}> {
    await expect(browse.position, 'the counter reads {index}/{total}').toHaveText(positionPattern(null, null));
    const text = (await browse.position.textContent()) ?? '';
    const match = /^\s*(\d+)\s*\/\s*(\d+)\s*$/.exec(text);
    if (!match) throw new Error(`asset-browse-position reads "${text}", not {index}/{total}`);
    return {index: Number(match[1]), total: Number(match[2])};
}

/** Press Previous or Next and land on `target`: its URL, its name in the header, its data loaded, the control ready on the same list. */
async function move(page: Page, browse: BrowseControl, direction: Direction, target: OwnedAsset, source: Source): Promise<void> {
    await browse[direction].click();
    await expectDetailOf(page, target, `${direction === 'next' ? 'Next' : 'Previous'} → "${target.name}"`);
    await expect(browse.root, 'after the move the control has settled again').toHaveAttribute('data-state', 'ready', {timeout: BROWSE_READY_MS});
    await expect(browse.root, 'and it still follows the same list').toHaveAttribute('data-source', source);
}

// =============================================================================
// Geometry at phone width
// =============================================================================

interface EdgeReaderArgs {
    parts: string[];
    tolerance: number;
    maxNamed: number;
}

interface PartBox {
    testId: string;
    /** Elements carrying the test id in the page: the box means something only when there is exactly one. */
    count: number;
    left: number | null;
    right: number | null;
}

interface Culprit {
    label: string;
    over: number;
}

interface EdgeReading {
    /** <html>'s box: the layout. Its right edge is the page's — a hidden scrollbar gutter is not room. */
    layoutLeft: number;
    layoutRight: number;
    windowWidth: number;
    parts: PartBox[];
    /** How far the furthest box or text run of the page reaches past the layout's right edge, px (0 when none does). */
    pageOverflow: number;
    /** The outermost boxes past that edge, furthest first. */
    culprits: Culprit[];
    /** Boxes and text runs compared with the edge. */
    measured: number;
}

/**
 * Runs inside the page: serialised by `page.evaluate`, so it references nothing outside itself. The page check is the
 * toolbar sweep's: every box and text run, visible or not (a hidden box widens the page all the same), compared with
 * the right of <html>'s box — except popups, anything fixed, empty boxes and the content of scrolling or clipping
 * containers, which are measured themselves.
 */
function readEdgesInPage({parts, tolerance, maxNamed}: EdgeReaderArgs): EdgeReading {
    const html = document.documentElement.getBoundingClientRect();
    const quote = (value: string): string => {
        const text = value.replace(/\s+/g, ' ').trim();
        return text.length > 24 ? `"${text.slice(0, 23)}…"` : `"${text}"`;
    };
    const describe = (element: Element): string => {
        const own = element.getAttribute('data-testid');
        if (own) return own;
        const owner = element.parentElement?.closest('[data-testid]')?.getAttribute('data-testid');
        const classes = Array.from(element.classList)
            .filter((name) => /^[a-z][a-z0-9-]*$/i.test(name))
            .slice(0, 3);
        const text = element instanceof HTMLElement ? element.innerText.replace(/\s+/g, ' ').trim() : '';
        return `${owner ? `${owner} › ` : ''}${element.tagName.toLowerCase()}${classes.map((name) => `.${name}`).join('')}${text ? ` ${quote(text)}` : ''}`;
    };

    const partBoxes = parts.map((testId): PartBox => {
        const matches = document.querySelectorAll(`[data-testid="${testId}"]`);
        const box = matches.length === 1 ? matches[0].getBoundingClientRect() : null;
        const laidOut = box !== null && box.width > 0 && box.height > 0;
        return {testId, count: matches.length, left: laidOut ? box.left : null, right: laidOut ? box.right : null};
    });

    const POPUP = '[role="listbox"], [role="dialog"], [role="tooltip"], [role="menu"]';
    const CLIPPING = new Set(['auto', 'scroll', 'hidden', 'clip']);
    const textRange = document.createRange();
    const culprits: Culprit[] = [];
    let pageOverflow = 0;
    let measured = 0;
    /** Says whether the box reaches past the layout's right edge, and names it unless an ancestor past the edge already is. */
    const pastThePage = (box: DOMRect, insideCulprit: boolean, label: () => string): boolean => {
        measured++;
        const past = box.right - html.right;
        pageOverflow = Math.max(pageOverflow, past);
        if (past <= tolerance) return false;
        if (!insideCulprit) culprits.push({label: label(), over: past});
        return true;
    };
    const scan = (element: Element, insideCulprit: boolean): void => {
        if (element.matches(POPUP)) return;
        const style = getComputedStyle(element);
        if (style.display === 'none' || style.position === 'fixed') return;
        const box = element.getBoundingClientRect();
        let culprit = insideCulprit;
        if (style.display !== 'contents' && box.width > 0 && box.height > 0) culprit = pastThePage(box, insideCulprit, () => describe(element));
        // Past a scrolling or clipping box nothing widens the page: the box itself was measured above.
        if (element instanceof SVGElement || CLIPPING.has(style.overflowX)) return;
        for (const node of Array.from(element.childNodes)) {
            if (node instanceof Element) {
                scan(node, culprit);
            } else if (node.nodeType === Node.TEXT_NODE && node.textContent?.trim()) {
                textRange.selectNodeContents(node);
                const textBox = textRange.getBoundingClientRect();
                if (textBox.width > 0 && textBox.height > 0) pastThePage(textBox, culprit, () => `${describe(element)} › text ${quote(node.textContent ?? '')}`);
            }
        }
    };
    for (const child of Array.from(document.body.children)) scan(child, false);
    culprits.sort((a, b) => b.over - a.over);
    return {layoutLeft: html.left, layoutRight: html.right, windowWidth: window.innerWidth, parts: partBoxes, pageOverflow, culprits: culprits.slice(0, maxNamed), measured};
}

function readEdges(page: Page, parts: readonly string[]): Promise<EdgeReading> {
    return page.evaluate(readEdgesInPage, {parts: [...parts], tolerance: EDGE_TOLERANCE_PX, maxNamed: MAX_NAMED});
}

function px(value: number): string {
    return `${value.toFixed(1)} px`;
}

function gutterOf(reading: EdgeReading): number {
    return reading.windowWidth - (reading.layoutRight - reading.layoutLeft);
}

function layoutReport(reading: EdgeReading): string {
    return `the layout — <html>'s box — x ${px(reading.layoutLeft)} → ${px(reading.layoutRight)}, window ${reading.windowWidth} px, scrollbar gutter ${px(gutterOf(reading))}`;
}

function partsReport(reading: EdgeReading): string {
    return reading.parts.map((part) => (part.left === null || part.right === null ? `${part.testId}: ${part.count} in the page, no box` : `${part.testId} x ${px(part.left)} → ${px(part.right)}`)).join('; ');
}

function culpritsReport(reading: EdgeReading): string {
    return reading.culprits.length === 0 ? 'nothing' : reading.culprits.map((culprit) => `${culprit.label} +${px(culprit.over)}`).join('; ');
}

/** Every part that is not exactly once in the page, laid out and inside the layout — with its edges, and by how much. */
function partsOutside(reading: EdgeReading): string[] {
    const outside: string[] = [];
    for (const part of reading.parts) {
        if (part.count !== 1) {
            outside.push(`${part.testId}: ${part.count} in the page, expected 1`);
        } else if (part.left === null || part.right === null) {
            outside.push(`${part.testId}: not laid out`);
        } else {
            if (part.left < reading.layoutLeft - EDGE_TOLERANCE_PX) outside.push(`${part.testId}: starts ${px(reading.layoutLeft - part.left)} left of the layout (x ${px(part.left)})`);
            if (part.right > reading.layoutRight + EDGE_TOLERANCE_PX) outside.push(`${part.testId}: ends ${px(part.right - reading.layoutRight)} past the layout's right edge (x ${px(part.right)})`);
        }
    }
    return outside;
}

/**
 * The positive control of both absences: a 20 px box hung past the layout's right edge by half the gutter plus
 * PROBE_PAST_PX — behind a gutter it still ends inside the window, where clientWidth sees nothing — must come back from
 * the same reader as a part outside the layout and, by name, as page overflow. Removed whatever happens.
 */
async function proveTheReaderSeesOverflow(page: Page): Promise<void> {
    const pastPx = gutterOf(await readEdges(page, [])) / 2 + PROBE_PAST_PX;
    await page.evaluate(
        ({probeId, past}) => {
            const probe = document.createElement('div');
            probe.dataset.testid = probeId;
            probe.style.cssText = `position: absolute; top: 0; right: ${-past}px; width: 20px; height: 2px;`;
            document.body.append(probe);
        },
        {probeId: PROBE_ID, past: pastPx},
    );
    try {
        const reading = await readEdges(page, [PROBE_ID]);
        expect(partsOutside(reading), `positive control: a box hung ${px(pastPx)} past the layout's right edge is reported outside it — ${layoutReport(reading)}; ${partsReport(reading)}`).toEqual([expect.stringContaining(`${PROBE_ID}: ends`)]);
        const probe = reading.culprits.find((culprit) => culprit.label === PROBE_ID);
        expect(probe?.over, `positive control: the page check names that box as page overflow, by how far it was hung — page +${px(reading.pageOverflow)}: ${culpritsReport(reading)}`).toBeCloseTo(pastPx, 0);
    } finally {
        await page.evaluate((probeId) => document.querySelector(`[data-testid="${probeId}"]`)?.remove(), PROBE_ID);
    }
}

// =============================================================================
// AB-001..AB-003 — the list the user left
// =============================================================================

test.describe('Asset detail ‹ n/N › follows the list the user left — filters, view, sort (K step 16, item 2)', () => {
    test('AB-001 grid, searched: from the middle card Next and Previous walk the cards in DOM order, disabled at the edges, the query kept; one header Back returns to /assets', async ({page, owned, baseURL}) => {
        const trio = await createTrio(page, owned);
        await keepOffline(page, baseURL);
        const order = await gridOrderOf(page, trio);

        await openCard(page, order[1]);
        const query = queryOf(page);
        expect(query.some((pair) => pair.startsWith('start=')) && query.some((pair) => pair.startsWith('end=')), `precondition: the card opens the detail with the list's dates (?start&end) — ${page.url()}`).toBe(true);

        const browse = await expectBrowseReady(page, 'list');
        await expectPosition(browse, 2, 3);

        await move(page, browse, 'next', order[2], 'list');
        await expectPosition(browse, 3, 3);
        expect(queryOf(page), 'Next keeps the URL query').toEqual(query);

        await move(page, browse, 'prev', order[1], 'list');
        await expectPosition(browse, 2, 3);
        expect(queryOf(page), 'Previous keeps the URL query').toEqual(query);

        await move(page, browse, 'prev', order[0], 'list');
        await expectPosition(browse, 1, 3);
        expect(queryOf(page), 'Previous keeps the URL query').toEqual(query);

        // Three moves replaced the detail's history entry three times: ONE click goes back to the list.
        await page.getByTestId('asset-detail-back-btn').click();
        await expect(page, 'one click on the header Back returns to the list, not to an asset visited on the way').toHaveURL((url) => url.pathname === '/assets', {timeout: NAVIGATION_MS});
        await expect(page.getByTestId('assets-page')).toBeVisible();
    });

    test('AB-002 browser Back after a move returns to /assets, not to the previous asset', async ({page, owned, baseURL}) => {
        const trio = await createTrio(page, owned);
        await keepOffline(page, baseURL);
        const order = await gridOrderOf(page, trio);

        await openCard(page, order[0]);
        const browse = await expectBrowseReady(page, 'list');
        await expectPosition(browse, 1, 3);
        await move(page, browse, 'next', order[1], 'list');

        await page.goBack();
        await expect(page, `the browser's Back returns to the list: the move replaced the history entry of /assets/${order[0].id} instead of adding one`).toHaveURL((url) => url.pathname === '/assets', {timeout: NAVIGATION_MS});
        await expect(page.getByTestId('assets-page')).toBeVisible();
    });

    test('AB-003 table sorted by name: from the first row Next and Previous walk the sorted rows, total 3', async ({page, owned, baseURL}) => {
        const trio = await createTrio(page, owned);
        await keepOffline(page, baseURL);
        const table = await tableOf(page, trio);
        const unsorted = inListOrder(trio, await rowIds(table), 'the searched table, unsorted');

        // The list arrives sorted by name, so ascending changes nothing: the second click, descending, is the one
        // that moves the rows away from the grid's order — and only then does following the sort mean anything.
        const nameHeader = table.getByTestId('dt-header-name');
        const sortByName = table.getByTestId('dt-sort-name');
        await expect(nameHeader, 'precondition: the table opens unsorted').toHaveAttribute('data-sort', 'none');
        await sortByName.click();
        await expect(nameHeader).toHaveAttribute('data-sort', 'asc');
        await sortByName.click();
        await expect(nameHeader).toHaveAttribute('data-sort', 'desc');
        await expect.poll(() => rowIds(table), {message: `precondition: sorted by name, descending, the rows leave the unsorted order (${unsorted.map((asset) => asset.id).join(', ')})`}).not.toEqual(unsorted.map((asset) => asset.id));
        const sorted = inListOrder(trio, await rowIds(table), 'the searched table, sorted by name');

        await openRow(page, table, sorted[0]);
        const browse = await expectBrowseReady(page, 'list');
        await expectPosition(browse, 1, 3);

        await move(page, browse, 'next', sorted[1], 'list');
        await expectPosition(browse, 2, 3);
        await move(page, browse, 'next', sorted[2], 'list');
        await expectPosition(browse, 3, 3);
        await move(page, browse, 'prev', sorted[1], 'list');
        await expectPosition(browse, 2, 3);
        await move(page, browse, 'prev', sorted[0], 'list');
        await expectPosition(browse, 1, 3);
    });
});

// =============================================================================
// AB-004 — no list to follow
// =============================================================================

test.describe("Asset detail ‹ n/N › with no list to follow — the list's default order (K step 16, item 2)", () => {
    test('AB-004 direct entry: the default order — a total of at least 4, not the filtered 3 — and Next one step forward', async ({page, owned, baseURL}) => {
        const trio = await createTrio(page, owned);
        await keepOffline(page, baseURL);
        const active = await activeAssetCount(page);
        expect(active, `precondition: at least ${DEFAULT_TOTAL_AT_LEAST} active assets exist (GET ${API_BASE}/assets/query?active=true)`).toBeGreaterThanOrEqual(DEFAULT_TOTAL_AT_LEAST);

        // Alpha: in the default order (by name) its own Beta and Gamma come after it, so it is never the last.
        const [alpha] = trio.assets;
        await goToAssetDetailPage(page, String(alpha.id));
        await expect(headerName(page), 'entered by URL, not from the list: the header names the asset').toHaveText(alpha.name);

        const browse = await expectBrowseReady(page, 'default');
        const before = await readPosition(browse);
        expect(before.total, `the default order holds every active asset, not the three of a search: ${before.index}/${before.total}`).toBeGreaterThanOrEqual(DEFAULT_TOTAL_AT_LEAST);
        expect(before.index, `"${alpha.name}" precedes its own Beta and Gamma, so it is not the last: ${before.index}/${before.total}`).toBeLessThan(before.total);
        await expect(browse.next, `${before.index}/${before.total}: Next is enabled`).toBeEnabled();

        await browse.next.click();
        await expect(page, 'Next goes to another asset').toHaveURL((url) => /^\/assets\/\d+$/.test(url.pathname) && url.pathname !== `/assets/${alpha.id}`, {timeout: NAVIGATION_MS});
        const nextId = Number(new URL(page.url()).pathname.split('/').pop());
        const nextName = await displayNameOf(page, nextId);
        await expect(headerName(page), `Next → asset ${nextId}: the header names it`).toHaveText(nextName, {timeout: NAVIGATION_MS});
        await waitForSettled(page.getByTestId('asset-detail-page'), NAVIGATION_MS);
        await expect(browse.root, 'after the move the control has settled again').toHaveAttribute('data-state', 'ready', {timeout: BROWSE_READY_MS});
        await expect(browse.root, 'and it still follows the default order').toHaveAttribute('data-source', 'default');
        await expect(browse.position, `Next moves one step forward: ${before.index}/${before.total} → ${before.index + 1}/…`).toHaveText(positionPattern(before.index + 1, null));
        expect((await readPosition(browse)).total, 'still the whole default order').toBeGreaterThanOrEqual(DEFAULT_TOTAL_AT_LEAST);
    });
});

// =============================================================================
// AB-005..AB-006 — phone widths
// =============================================================================

test.describe('Asset detail ‹ n/N › at phone width — the nav fits and the page does not scroll sideways (K step 16, item 2)', () => {
    for (const viewport of PHONES) {
        test(`${viewport.id} ${viewport.width}×${viewport.height}: opened from the searched grid, the nav's buttons and counter lie inside the layout and the page does not scroll sideways`, async ({page, owned, baseURL}) => {
            const trio = await createTrio(page, owned);
            await keepOffline(page, baseURL);
            await page.setViewportSize({width: viewport.width, height: viewport.height});
            const order = await gridOrderOf(page, trio);

            await openCard(page, order[1]);
            const browse = await expectBrowseReady(page, 'list');
            await expectPosition(browse, 2, 3);
            for (const part of [browse.prev, browse.position, browse.next]) await expect(part).toBeVisible();

            // 1. The nav's parts, against the layout's edges: every offender named with its edges.
            await expect
                .soft(async () => {
                    const reading = await readEdges(page, NAV_PARTS);
                    expect(partsOutside(reading), `at ${viewport.width} px the nav's buttons and counter lie inside the layout — ${layoutReport(reading)}; ${partsReport(reading)}`).toEqual([]);
                })
                .toPass({timeout: 5_000});
            // 2. The page: nothing reaches past the layout's right edge.
            await expect
                .soft(async () => {
                    const reading = await readEdges(page, []);
                    expect(reading.pageOverflow, `at ${viewport.width} px the page does not scroll sideways: its furthest box ends ${px(reading.pageOverflow)} past the layout's right edge — ${layoutReport(reading)}; past it: ${culpritsReport(reading)}`).toBeLessThanOrEqual(EDGE_TOLERANCE_PX);
                })
                .toPass({timeout: 5_000});
            // 3. The same reader reports a box the test hangs past that edge: the two absences above can fail.
            await proveTheReaderSeesOverflow(page);
        });
    }
});

// =============================================================================
// AB-007..AB-008 — the date range a move carries (review defects, 06/10)
// =============================================================================

/** Stored daily closes, today included: Alpha's span and Beta's, far enough apart that their "All" starts differ. */
const ALPHA_PRICE_DAYS = 30;
const BETA_PRICE_DAYS = 200;
/** After a move, the time the page has to resolve "All" again from the new asset's chart data. */
const RESOLVE_MS = 10_000;

/** An owned asset with stored daily closes: `earliest` is its first one, the start "All" must resolve to. */
type PricedAsset = OwnedAsset & {earliest: string};
type DateRange = {start: string | null; end: string | null};

interface RangePicker {
    start: Locator;
    end: Locator;
    preset: (key: string) => Locator;
}

/** `days` daily closes ending today, oldest first. */
function dailyCloses(days: number): Array<{date: string; close: number; currency: string}> {
    return Array.from({length: days}, (_, i) => ({date: daysAgoIso(days - 1 - i), close: Number((48 + i * 0.25).toFixed(2)), currency: 'EUR'}));
}

/**
 * Two plain EUR stocks in one list payload, `E2E Browse <token> Alpha|Beta`, then their closes in one upsert: Alpha the
 * last ALPHA_PRICE_DAYS days, Beta the last BETA_PRICE_DAYS. Each `earliest` is taken here, from the closes stored.
 */
async function createPricedPair(page: Page, owned: Owned): Promise<{token: string; assets: PricedAsset[]}> {
    const token = uniqueSuffix();
    const spans = [
        {name: `E2E Browse ${token} Alpha`, closes: dailyCloses(ALPHA_PRICE_DAYS)},
        {name: `E2E Browse ${token} Beta`, closes: dailyCloses(BETA_PRICE_DAYS)},
    ];
    const names = spans.map((span) => span.name);
    const items = names.map((name) => schemas.FAAssetCreateItem.parse({display_name: name, currency: 'EUR', asset_type: 'STOCK', active: true}));
    const response = await page.request.post(`${API_BASE}/assets`, {data: items});
    const body = (await response.json().catch(() => null)) as {results?: Array<{asset_id?: number | null; display_name: string; success: boolean; message?: string}>} | null;
    const results = body?.results ?? [];
    // Recorded before any assertion can throw: whatever was created gets deleted, and its closes with it.
    for (const result of results) if (typeof result.asset_id === 'number' && names.includes(result.display_name)) owned.assetIds.push(result.asset_id);
    expect(response.status(), `POST ${API_BASE}/assets answers 201 to the two-item list: ${JSON.stringify(body)}`).toBe(201);
    const created = spans.map((span) => {
        const result = results.find((candidate) => candidate.display_name === span.name);
        if (!result?.success || typeof result.asset_id !== 'number') throw new Error(`"${span.name}" was not created: ${JSON.stringify(body)}`);
        return {id: result.asset_id, ...span};
    });
    const upserts = created.map((asset) => schemas.FAUpsert.parse({asset_id: asset.id, prices: asset.closes}));
    const stored = await jsonFrom<{results: Array<{asset_id: number; count: number}>}>(await page.request.post(`${API_BASE}/assets/prices`, {data: upserts}), 'store the daily closes');
    for (const asset of created) expect(stored.results.find((result) => result.asset_id === asset.id)?.count, `every daily close of "${asset.name}" is stored`).toBe(asset.closes.length);
    return {token, assets: created.map((asset) => ({id: asset.id, name: asset.name, earliest: asset.closes[0].date}))};
}

/** /assets in the grid view, searched for `token`: `assets` in the order of their cards in the DOM — exactly those. */
async function searchedGridOrder<T extends OwnedAsset>(page: Page, token: string, assets: T[]): Promise<T[]> {
    await goToAssetsPage(page);
    await page.getByTestId('view-mode-grid').click();
    await searchList(page, token);
    for (const asset of assets) await expect(page.getByTestId(`asset-card-${asset.id}`)).toBeVisible({timeout: LIST_MS});
    // The cards carry `data-lifecycle`; the controls inside a card share the `asset-card-` prefix and do not.
    const cards = page.locator('[data-testid^="asset-card-"][data-lifecycle]');
    await expect(cards, `searched for its token, the grid holds the ${assets.length} cards of this test and nothing else`).toHaveCount(assets.length, {timeout: LIST_MS});
    const ids = await cards.evaluateAll((elements) => elements.map((element) => Number((element.getAttribute('data-testid') ?? '').slice('asset-card-'.length))));
    return inListOrder({token, assets}, ids, 'the searched grid').map((listed) => assets.find((asset) => asset.id === listed.id) as T);
}

/** The detail page's date range picker, in its toolbar's filter bar. Compact, so both fields show ISO dates. */
function detailRangePicker(page: Page): RangePicker {
    const root = page.getByTestId('asset-detail-controls').getByTestId('asset-detail-filter-bar').getByTestId('date-range-picker-root');
    return {start: root.getByTestId('date-range-input-start'), end: root.getByTestId('date-range-input-end'), preset: (key) => root.getByTestId(`date-preset-${key}`)};
}

/** `start` and `end` of a URL's query. */
function rangeOf(href: string): DateRange {
    const url = new URL(href);
    return {start: url.searchParams.get('start'), end: url.searchParams.get('end')};
}

test.describe('Asset detail ‹ n/N › — a move carries the date range the page shows (K step 16, item 2: review defects, 06/10)', () => {
    test('AB-007 "All" chosen on one asset, then Next: the start resolves again, to the earliest stored close of the next asset, and "All" stays active', async ({page, owned, baseURL}) => {
        const pair = await createPricedPair(page, owned);
        const [alpha, beta] = pair.assets;
        await keepOffline(page, baseURL);
        const order = await searchedGridOrder(page, pair.token, pair.assets);
        expect(
            order.map((asset) => asset.name),
            'precondition: Alpha is the first card, so Next goes from Alpha to Beta',
        ).toEqual([alpha.name, beta.name]);

        await openCard(page, alpha);
        const browse = await expectBrowseReady(page, 'list');
        await expectPosition(browse, 1, 2);

        const picker = detailRangePicker(page);
        const all = picker.preset('max');
        await all.click();
        await expect(all, 'precondition: "All" is the active preset').toHaveAttribute('data-active', 'true');
        await expect(picker.start, `precondition: "All" resolves the start from the chart's first point — Alpha's earliest stored close, ${alpha.earliest}`).toHaveValue(alpha.earliest, {timeout: RESOLVE_MS});
        await waitForSettled(page.getByTestId('asset-detail-page'), NAVIGATION_MS);

        await move(page, browse, 'next', beta, 'list');
        await expect(all, '"All" is still the active preset after the move').toHaveAttribute('data-active', 'true');
        await expect(picker.start, `after Next, "All" resolves again for Beta: its earliest stored close is ${beta.earliest} (${alpha.earliest} is Alpha's)`).toHaveValue(beta.earliest, {timeout: RESOLVE_MS});
    });

    test('AB-008 a range chosen on the detail page (1Y) travels with Next, and a reload brings it back', async ({page, owned, baseURL}) => {
        const trio = await createTrio(page, owned);
        await keepOffline(page, baseURL);
        const order = await gridOrderOf(page, trio);

        await openCard(page, order[0]);
        const browse = await expectBrowseReady(page, 'list');
        await expectPosition(browse, 1, 3);
        const opened = rangeOf(page.url());
        expect(opened.start !== null && opened.end !== null, `precondition: the card opens the detail with the list's dates (?start&end) — ${page.url()}`).toBe(true);

        const picker = detailRangePicker(page);
        const oneYear = picker.preset('1y');
        await expect(oneYear, 'precondition: the range is not 1Y yet, so choosing 1Y changes it').toHaveAttribute('data-active', 'false');
        await oneYear.click();
        await expect(oneYear, 'precondition: 1Y is the active preset').toHaveAttribute('data-active', 'true');
        await expect(page, 'precondition: the detail page writes the new range into the address bar').toHaveURL((url) => url.searchParams.get('start') !== opened.start);
        // Read before the click: the range the address bar shows is the one the move must carry.
        const chosen = rangeOf(page.url());
        expect(chosen.start, `precondition: the address bar holds a concrete start — ${page.url()}`).toMatch(/^\d{4}-\d{2}-\d{2}$/);
        await expect(picker.start, 'precondition: the address bar and the picker agree on the chosen start').toHaveValue(chosen.start ?? '');
        await expect(picker.end, 'precondition: and on the chosen end').toHaveValue(chosen.end ?? '');
        await waitForSettled(page.getByTestId('asset-detail-page'), NAVIGATION_MS);

        await move(page, browse, 'next', order[1], 'list');
        // Control: the page itself keeps the chosen range across the move — what the URL carries is the question.
        await expect(picker.start, 'after the move the page still shows the chosen range').toHaveValue(chosen.start ?? '');
        expect.soft(rangeOf(page.url()), `Next carries the range the address bar showed before the click (${chosen.start} → ${chosen.end}), not the one the page was opened with (${opened.start} → ${opened.end})`).toEqual(chosen);

        await page.reload();
        await expect(headerName(page), 'reloaded: the header names the asset').toHaveText(order[1].name, {timeout: NAVIGATION_MS});
        await waitForSettled(page.getByTestId('asset-detail-page'), NAVIGATION_MS);
        await expect(picker.start, `after a reload the picker shows the chosen start, ${chosen.start} (${opened.start} is the one the page was opened with)`).toHaveValue(chosen.start ?? '');
        await expect(picker.end, `and the chosen end, ${chosen.end}`).toHaveValue(chosen.end ?? '');
    });
});
