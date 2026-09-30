/**
 * The five top toolbars at every width — K step 13, item 5 (developer's note of 21/09, decision D5 of 30/09).
 *
 * Written RED-FIRST, before the fix, and meant to be read twice: as the regression guard, and — while it is
 * red — as the calibration instrument. Its failure message is the table the new thresholds are chosen from.
 *
 * The defect. The top toolbars are PageToolbar instances (`ui/toolbar/PageToolbar.svelte`). A ResizeObserver
 * on the bar's own row picks the tier from its content width (`utils/layout/responsiveLayout.svelte.ts`):
 * oneRow ≥ `oneRow` > denseRow ≥ `denseRow` > stackFilters ≥ `stackFilters` > oneColumn. Just above a
 * threshold the tier's content no longer fits and buttons stick out of the bar. Measured on 30/09 on the
 * developer's data, in Italian: up to 14 px on /assets, 25 px on /fx, the broker tab row 8 px, a page 11 px
 * wider than a 330 px viewport on an asset. D5 recalibrates every bar on its longest-label language, with a
 * margin. The calibration on the prod copy (30/09, all four languages) found Spanish the longest for most bars,
 * French next, and English dominated everywhere. So every bar runs in French, Italian (the developer's own) and
 * Spanish, one test per (bar, language): a red bar never hides another.
 *
 * The sweep. One page load, then the viewport narrows from 1700 to 320 px in 10 px steps at a fixed height of
 * 1000, like a window being dragged. The content column loses the sidebar below 1024 px, so the bar is
 * `vw − 66` px there and `vw − 338` above (headless: no scrollbar gutter; a headed run with classic scrollbars
 * shifts the viewport widths, never the bar widths): the same tiers are crossed twice, in two viewport ranges,
 * which is why the report groups by bar width. The widest bar is 1362 px, above every oneRow threshold; the
 * report says so if a recalibrated one ever lands out of reach.
 *
 * The measure, at each width, inside the page:
 *   - the bar is the PageToolbar card (`testId`), tab row included. Every visible descendant box, and every
 *     text run, is compared with its edges: over = max(right − bar.right, bar.left − left);
 *   - popups (listbox, dialog, tooltip, menu, anything `position: fixed`), invisible boxes, a spinning icon's
 *     rotated box and the content of scrolling or clipping containers are skipped: such a container is
 *     measured itself, and what it hides cannot stick out of it;
 *   - the page: documentElement.scrollWidth − clientWidth (clientWidth rather than innerWidth, so a visible
 *     scrollbar in a headed run is not counted as room). When it is positive, the outermost boxes past the
 *     viewport are named, inside the bar or not.
 * A violation is a box past the bar, or a page wider than the viewport, by more than 1 px; or a width whose
 * layout never settled. All of them are collected, and asserted once at the end. That assertion is an
 * absence, so it has two presence controls: before the sweep, a box the test hangs 200 px past the bar must
 * come back as the furthest offender, by name; and every settled width must have measured the bar's text.
 *
 * Settling, without a sleep. After a resize the bar goes through ResizeObserver callbacks (delivered only
 * inside a rendering update), Svelte's flush, `requestAnimationFrame` re-fits of the action and tab labels
 * (`labelShrink.ts`), and DateRangePicker re-measuring its preset badges from a 100 ms `setTimeout` debounce
 * after the last resize: a state nothing publishes. So the page's timers run on Playwright's clock, installed
 * once the page has loaded, and each settle round
 *   1. runs the clock 250 ms forward (`runFor`): the debounce and every re-fit fire now, in order;
 *   2. waits for two real rendering updates, through a native `requestAnimationFrame` captured before the
 *      clock replaced it, so every ResizeObserver notification the flush caused has been delivered;
 *   3. reads the state: the viewport is that wide, `window.__lfLayouts[name].width` equals the row's measured
 *      content box (the observer has caught up), no CSS transition runs on the bar or an ancestor (the
 *      content column's margin animates for 300 ms across 1024 px), the fonts are loaded, and a hash of
 *      every box.
 * A width is measured once two consecutive readings are ready and identical: a timer flush plus two
 * rendering updates changed nothing, so nothing is left to change. After 60 rounds it is reported as
 * unsettled instead, which is a defect of its own.
 *
 * Language. `setLanguage` goes through the header selector, which writes `librefolio-locale` in this
 * context's localStorage and nothing on the server; the account's saved language is applied only at login,
 * which happens before the switch. There is nothing to restore.
 *
 * Subjects. /assets, /dashboard and /fx need none. The detail pages choose theirs over the API, by property.
 * The asset is the header's worst case: its title is capped at 15ch inside two flex wrappers that cannot
 * shrink below it (the developer's data: a page wider than the viewport below ~341 px). So, among the active
 * assets priced by a market provider (not a parametric one) with at least two stored prices, the test takes the
 * one with the longest display name; when none reaches 25 characters it creates its own — a realistic ETF name
 * with a unique suffix, priced by mockprov under the identifier the mock refuses to quote, with a month of
 * daily closes up to today — and deletes it at the end. Rows this spec created are never borrowed: its other
 * languages run in parallel and delete theirs. The broker is the lowest-id active one the E2E user can edit
 * (so its bar carries all four actions) that holds a position. Each page then proves it: a price in the
 * summary, the plain and enabled Sync, the Edit action.
 *
 * Offline, and writing only its own rows. POST /assets/prices/current asks the live providers and writes
 * today's OHLC row on shared seeded assets, so it is answered empty and the summary shows the last stored
 * close. Every other origin is refused (seeded icon and portal URLs). The only row the test writes is the asset
 * it may create, deleted by id whatever happens; otherwise it reads, and runs in parallel with anything.
 *
 * Not covered: the list view of /assets and /fx, where ColumnVisibilityToggle replaces the Abs/% toggle — a
 * fresh context opens both in the grid view. The pixel widths are those of the fonts on the machine that
 * runs the sweep (Inter when installed, else system-ui).
 */
import {expect, test as base, type Page} from '../fixtures/playwright';
import {login, navigateTo, setLanguage} from '../fixtures/auth-helpers';
import {waitForSettled} from '../fixtures/app-events';
import {daysAgoIso} from '../fixtures/dates';
import {TEST_USER, type Language} from '../fixtures/test-users';
import {uniqueSuffix} from '../fixtures/unique';

const API = '/api/v1';
const SWEEP_FROM_PX = 1700;
const SWEEP_TO_PX = 320;
const STEP_PX = 10;
const VIEWPORT_HEIGHT_PX = 1000;
/** Layout boxes are fractional: up to 1 px past an edge is rounding, more is a control out of its bar. */
const TOLERANCE_PX = 1;
/** Clock time run per settle round: DateRangePicker's 100 ms resize debounce, and the frame re-fits behind it. */
const TIMER_FLUSH_MS = 250;
/** Settle rounds (a timer flush plus two rendering updates each) before a width is reported as unsettled. */
const MAX_SETTLE_ROUNDS = 60;
/** How many offenders a row of the report names. */
const MAX_NAMED = 3;
/** Wall-clock budget of the sweep itself, below the test timeout: a slow run still prints what it measured. */
const SWEEP_BUDGET_MS = 240_000;
const LANGUAGES: readonly Language[] = ['fr', 'it', 'es'];
const TIER_ORDER: readonly string[] = ['oneRow', 'denseRow', 'stackFilters', 'oneColumn'];
/** The positive control's box, hung this far past the bar's right edge: further than any real spill. */
const PROBE_ID = 'toolbar-sweep-probe';
const PROBE_PAST_PX = 200;
/**
 * The asset detail header is widest for a long name: its title is capped at 15ch but cannot shrink below
 * that cap. A realistic ETF name for the asset the test creates when no eligible one is long enough; it gets
 * a unique suffix (display_name is unique), and marks the rows this spec creates, which are never borrowed.
 */
const LONG_ASSET_NAME = 'Xtrackers MSCI World Industrials UCITS ETF 1C';
const LONG_NAME_MIN_CHARS = 25;
/** mockprov refuses a current price for exactly this identifier: a poll of the created asset writes nothing back. */
const OFFLINE_IDENTIFIER = 'INVALID_TICKER_12345';
/** Daily closes up to today for the created asset: at least two points in any window the page opens with. */
const OWN_PRICE_DAYS = 30;
const WIDTHS: readonly number[] = Array.from({length: Math.floor((SWEEP_FROM_PX - SWEEP_TO_PX) / STEP_PX) + 1}, (_, i) => SWEEP_FROM_PX - i * STEP_PX);

/** What the test created, by id, deleted at the end whatever happened. */
interface Owned {
    assetIds: number[];
}

/** The page a bar is swept on, and how the report names it. */
interface Subject {
    path: string;
    label: string;
}

interface Bar {
    /** PageToolbar `layoutDebugName`: the key of this instance on `window.__lfLayouts`. */
    name: string;
    /** PageToolbar `testId`: the card whose edges are the bar's edges, tab row included. */
    root: string;
    /** PageToolbar `filterRowTestId`: the row whose content box the ResizeObserver reports. */
    row: string;
    /** The page to open. The detail pages choose their subject over the API, the asset one may create it. */
    subject: (page: Page, owned: Owned) => Promise<Subject>;
    /** Resolves once everything the bar renders is final, and proves the subject shows what it was chosen for. */
    ready: (page: Page) => Promise<void>;
}

interface Offender {
    label: string;
    over: number;
}

/** One settle round's view of the page. Crosses `page.evaluate`, so plain data only. */
interface Reading {
    /** Every reason the page is not yet worth measuring. Empty when it is. */
    notReady: string[];
    /** Hash of every box of the bar (quarter pixels), its tier, its width and the page's scroll width. */
    signature: string;
    layoutMode: string;
    /** `window.__lfLayouts[name].width`: the ResizeObserver content width the thresholds are compared with. */
    barWidth: number;
    showActionLabels: boolean;
    showTabLabels: boolean;
    thresholds: Record<string, number>;
    /** How far the furthest box or text run reaches past the bar, px; 0 when everything is inside. */
    over: number;
    worst: string | null;
    /** The outermost offenders (their own parent box still fits), furthest first. */
    offenders: Offender[];
    /** Boxes and text runs compared with the bar's edges: a reader that stops descending measures no text. */
    measuredBoxes: number;
    measuredTexts: number;
    /** documentElement.scrollWidth − clientWidth, px. */
    pageOverflow: number;
    pageCulprits: Array<Offender & {inBar: boolean}>;
}

interface ReaderArgs {
    name: string;
    rootId: string;
    rowId: string;
    vw: number;
    tolerance: number;
    maxNamed: number;
}

interface Step {
    vw: number;
    settled: boolean;
    rounds: number;
    reading: Reading;
    /** Exceptions a page timer threw while the clock ran: reported, never measured. */
    timerErrors: string[];
}

// =============================================================================
// Subjects and readiness
// =============================================================================

type HttpResponse = {ok(): boolean; status(): number; text(): Promise<string>; json(): Promise<unknown>};

async function jsonFrom<T>(response: HttpResponse, purpose: string): Promise<T> {
    expect(response.ok(), `${purpose}: HTTP ${response.status()} ${await response.text()}`).toBe(true);
    return (await response.json()) as T;
}

async function getJson<T>(page: Page, url: string, purpose: string): Promise<T> {
    return jsonFrom<T>(await page.request.get(url), purpose);
}

function fixedPage(path: string): Bar['subject'] {
    return async () => ({path, label: path});
}

/**
 * The asset whose header is widest: among the active assets priced by a market provider (not a parametric one)
 * with at least two stored prices, the one with the longest display name — or, when none reaches
 * LONG_NAME_MIN_CHARS, one the test creates. Rows this spec created are never borrowed: its other languages
 * run in parallel and delete theirs at the end.
 */
async function longestNamedPricedAsset(page: Page, owned: Owned): Promise<Subject> {
    const providers = await getJson<Array<{code: string; kind?: string | null}>>(page, `${API}/assets/provider`, 'list the asset providers');
    const market = new Set(providers.filter((provider) => provider.kind !== 'parametric_generation').map((provider) => provider.code));
    const assets = await getJson<Array<{id: number; display_name: string; active: boolean; provider_code?: string | null}>>(page, `${API}/assets/query?active=true`, 'list the active assets');
    const candidates = assets
        .filter((asset) => asset.active && !!asset.provider_code && market.has(asset.provider_code) && asset.display_name.length >= LONG_NAME_MIN_CHARS && !asset.display_name.startsWith(LONG_ASSET_NAME))
        .sort((a, b) => b.display_name.length - a.display_name.length || a.id - b.id);
    for (const asset of candidates) {
        const stored = await getJson<{prices: number}>(page, `${API}/assets/${asset.id}/market-data/summary`, `count the stored prices of asset ${asset.id}`);
        if (stored.prices >= 2) return {path: `/assets/${asset.id}`, label: `/assets/${asset.id} "${asset.display_name}"`};
    }
    return createLongNamedPricedAsset(page, owned);
}

/** An eligible asset of the test's own: long name, mockprov (offline identifier), a month of daily closes. */
async function createLongNamedPricedAsset(page: Page, owned: Owned): Promise<Subject> {
    const displayName = `${LONG_ASSET_NAME} ${uniqueSuffix()}`;
    const created = await jsonFrom<{results: Array<{asset_id?: number | null; display_name: string; success: boolean}>}>(await page.request.post(`${API}/assets`, {data: [{display_name: displayName, currency: 'EUR', asset_type: 'ETF', active: true}]}), 'create the long-named asset');
    const row = created.results.find((result) => result.display_name === displayName);
    if (typeof row?.asset_id === 'number') owned.assetIds.push(row.asset_id);
    if (!row?.success || typeof row.asset_id !== 'number') throw new Error(`Asset creation failed: ${JSON.stringify(created)}`);
    const assetId = row.asset_id;

    const assigned = await jsonFrom<{results: Array<{asset_id: number; success: boolean}>}>(
        await page.request.post(`${API}/assets/provider`, {data: [{asset_id: assetId, provider_code: 'mockprov', identifier: OFFLINE_IDENTIFIER, identifier_type: 'TICKER', provider_params: null}]}),
        'assign the offline mock provider',
    );
    expect(assigned.results.find((result) => result.asset_id === assetId)?.success, `mockprov assigned: ${JSON.stringify(assigned)}`).toBe(true);

    const prices = Array.from({length: OWN_PRICE_DAYS}, (_, i) => ({date: daysAgoIso(OWN_PRICE_DAYS - 1 - i), close: Number((61.5 + i * 0.37).toFixed(2)), currency: 'EUR'}));
    const stored = await jsonFrom<{results: Array<{asset_id: number; count: number}>}>(await page.request.post(`${API}/assets/prices`, {data: [{asset_id: assetId, prices}]}), 'store a month of daily closes');
    expect(stored.results.find((result) => result.asset_id === assetId)?.count, 'every daily close is stored').toBe(prices.length);
    return {path: `/assets/${assetId}`, label: `/assets/${assetId} "${displayName}" (created by the test)`};
}

/** An active broker the E2E user can edit, holding a position: its bar then carries all four actions. */
async function editableBroker(page: Page): Promise<Subject> {
    const listed = await getJson<{items?: Array<{id: number; is_active: boolean; user_role?: string | null}>}>(page, `${API}/brokers`, 'list the brokers the E2E user can see');
    const editable = (listed.items ?? []).filter((broker) => broker.is_active && (broker.user_role === 'OWNER' || broker.user_role === 'EDITOR')).sort((a, b) => a.id - b.id);
    for (const broker of editable) {
        const summary = await getJson<{holdings?: unknown[] | null}>(page, `${API}/brokers/${broker.id}/summary`, `read the summary of broker ${broker.id}`);
        if ((summary.holdings ?? []).length > 0) return {path: `/brokers/${broker.id}`, label: `/brokers/${broker.id}`};
    }
    throw new Error(`None of ${editable.length} active brokers the E2E user can edit holds a position. Check populate_mock_data.py (populate_broker_user_access, populate_transactions).`);
}

/**
 * Deletes what the test created, by the ids it recorded. Routes and the page go first, so no poll or reload
 * reads the asset while it goes; `page.request` shares the browser's session.
 */
async function releaseOwned(page: Page, owned: Owned): Promise<void> {
    if (owned.assetIds.length === 0) return;
    const failures: string[] = [];
    const attempt = async (label: string, action: () => Promise<unknown>): Promise<void> => {
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
            const deleted = await jsonFrom<{results: Array<{asset_id: number; success: boolean}>}>(await page.request.delete(`${API}/assets?asset_ids=${assetId}`), 'delete the created asset, its prices and its provider assignment');
            expect(deleted.results.find((result) => result.asset_id === assetId)?.success, `asset ${assetId} deleted: ${JSON.stringify(deleted)}`).toBe(true);
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

// Login, the language switch, a full page load, 139 settled widths and the cleanup share the budget.
test.setTimeout(330_000);

/** The page's own busy flag: every load wave is in. */
function settles(pageTestId: string): (page: Page) => Promise<void> {
    return (page) => waitForSettled(page.getByTestId(pageTestId), 30_000);
}

async function assetDetailReady(page: Page): Promise<void> {
    await waitForSettled(page.getByTestId('asset-detail-page'), 30_000);
    await expect(page.getByTestId('asset-detail-live-price'), 'precondition: the price summary shows a price (the asset has a history in the default window)').toBeVisible({timeout: 15_000});
    await expect(page.getByTestId('asset-detail-sync-btn'), 'precondition: Sync is the plain, enabled button (the provider assignment is loaded)').toBeEnabled({timeout: 15_000});
    await expect(page.getByTestId('asset-detail-edit-btn'), 'precondition: Edit is enabled (the classification is loaded)').toBeEnabled({timeout: 15_000});
}

async function brokerDetailReady(page: Page): Promise<void> {
    await expect(page.getByTestId('broker-controls')).toBeVisible({timeout: 15_000});
    // The page publishes no data-busy. Refresh is disabled exactly while the broker or its report loads.
    await expect(page.getByTestId('broker-refresh'), 'the broker and its report finished loading (Refresh enabled again)').toBeEnabled({timeout: 30_000});
    await expect(page.getByTestId('broker-edit-button'), 'precondition: the E2E user can edit this broker, so the bar shows all four actions').toBeVisible();
}

const BARS: readonly Bar[] = [
    {name: 'assetsList', root: 'assets-controls', row: 'assets-filter-bar', subject: fixedPage('/assets'), ready: settles('assets-page')},
    {name: 'assetDetail', root: 'asset-detail-controls', row: 'asset-detail-filter-bar', subject: longestNamedPricedAsset, ready: assetDetailReady},
    {name: 'dashboard', root: 'dashboard-controls', row: 'dashboard-filter-bar', subject: fixedPage('/dashboard'), ready: settles('dashboard-page')},
    {name: 'brokerDetail', root: 'broker-controls', row: 'broker-overview-controls', subject: (page) => editableBroker(page), ready: brokerDetailReady},
    {name: 'fxList', root: 'fx-controls', row: 'fx-filter-bar', subject: fixedPage('/fx'), ready: settles('fx-page')},
];

async function keepOffline(page: Page, origin: string): Promise<void> {
    // Seeded icon and portal URLs point at the internet: refused, the icons fall back to their fixed-size placeholders.
    await page.route(
        (url) => (url.protocol === 'http:' || url.protocol === 'https:') && url.origin !== origin,
        (route) => route.abort('blockedbyclient'),
    );
    // /assets and /assets/{id} poll this on load and every 30 s. It asks the live providers and upserts today's
    // OHLC row on the shared seeded assets. Answered empty, the price summary shows the last stored close.
    await page.route('**/api/v1/assets/prices/current', (route) => route.fulfill({json: {results: [], success_count: 0, errors: []}}));
}

// =============================================================================
// Reading the page
// =============================================================================

/**
 * The frame barrier, captured before `page.clock.install()` replaces `requestAnimationFrame`: the clock's
 * version fires on a timer, while a ResizeObserver delivers only inside a real rendering update.
 */
async function installFrameHook(page: Page): Promise<void> {
    await page.evaluate(() => {
        const nativeFrame = window.requestAnimationFrame.bind(window);
        (window as unknown as {__lfToolbarSweep: {frame: () => Promise<void>}}).__lfToolbarSweep = {frame: () => new Promise<void>((resolve) => nativeFrame(() => resolve()))};
    });
}

/** Runs inside the page: serialised by `page.evaluate`, so it references nothing outside itself. */
async function readInPage({name, rootId, rowId, vw, tolerance, maxNamed}: ReaderArgs): Promise<Reading> {
    type LayoutProbe = {layoutMode?: unknown; width?: unknown; showActionLabels?: unknown; showTabLabels?: unknown; thresholds?: Record<string, unknown>};
    const scope = window as unknown as {__lfLayouts?: Record<string, LayoutProbe | undefined>; __lfToolbarSweep?: {frame: () => Promise<void>}};
    const hook = scope.__lfToolbarSweep;
    if (!hook) throw new Error('The frame hook is missing: installFrameHook() runs before the first reading');
    // Two real rendering updates: ResizeObserver notifications are delivered inside one, so the second proves
    // that whatever the last timer flush changed has been observed and reacted to.
    await hook.frame();
    await hook.frame();

    const notReady: string[] = [];
    const layout = scope.__lfLayouts?.[name];
    const root = document.querySelector<HTMLElement>(`[data-testid="${rootId}"]`);
    const row = document.querySelector<HTMLElement>(`[data-testid="${rowId}"]`);
    if (!layout) notReady.push(`window.__lfLayouts.${name} is not registered`);
    if (!root) notReady.push(`[data-testid="${rootId}"] is not in the page`);
    if (!row) notReady.push(`[data-testid="${rowId}"] is not in the page`);
    if (!layout || !root || !row) {
        return {notReady, signature: '', layoutMode: '?', barWidth: NaN, showActionLabels: false, showTabLabels: false, thresholds: {}, over: 0, worst: null, offenders: [], measuredBoxes: 0, measuredTexts: 0, pageOverflow: 0, pageCulprits: []};
    }

    if (window.innerWidth !== vw) notReady.push(`the viewport is ${window.innerWidth} px wide, not ${vw}`);
    if (document.fonts.status !== 'loaded') notReady.push('fonts are still loading');
    const rowStyle = getComputedStyle(row);
    const rowContent = row.getBoundingClientRect().width - parseFloat(rowStyle.paddingLeft) - parseFloat(rowStyle.paddingRight) - parseFloat(rowStyle.borderLeftWidth) - parseFloat(rowStyle.borderRightWidth);
    const barWidth = Number(layout.width);
    if (!(Math.abs(barWidth - rowContent) <= 0.5)) notReady.push(`the ResizeObserver still reports ${barWidth.toFixed(2)} px for a ${rowContent.toFixed(2)} px row`);

    // Motion. A CSS transition on the bar, inside it or on an ancestor is geometry still on its way: not ready.
    // A running keyframe animation that transforms a box (a spinner) turns it every frame without being
    // layout: that box is left out.
    const turning = new Set<Element>();
    let transitions = 0;
    for (const animation of document.getAnimations()) {
        if (animation.playState !== 'running') continue;
        const effect = animation.effect;
        if (!(effect instanceof KeyframeEffect) || !effect.target) continue;
        const target = effect.target;
        if (animation instanceof CSSTransition) {
            if (target === root || root.contains(target) || target.contains(root)) transitions++;
        } else if (root.contains(target) && effect.getKeyframes().some((keyframe) => 'transform' in keyframe)) {
            turning.add(target);
        }
    }
    if (transitions > 0) notReady.push(`${transitions} CSS transition(s) still running on the bar or an ancestor`);

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

    const POPUP = '[role="listbox"], [role="dialog"], [role="tooltip"], [role="menu"]';
    const CLIPPING = new Set(['auto', 'scroll', 'hidden', 'clip']);
    const barBox = root.getBoundingClientRect();
    const boxes: string[] = [String(layout.layoutMode), barWidth.toFixed(2), String(document.documentElement.scrollWidth)];
    const offenders: Offender[] = [];
    let over = 0;
    let worst: string | null = null;
    let measuredBoxes = 0;
    let measuredTexts = 0;
    const quarter = (value: number): number => Math.round(value * 4);

    /** Hashes the box, and when it may be measured, says whether it sticks out of the bar. */
    const record = (box: DOMRect, measurable: boolean, insideOffender: boolean, isText: boolean, label: () => string): boolean => {
        boxes.push(`${quarter(box.left)},${quarter(box.top)},${quarter(box.width)},${quarter(box.height)}`);
        if (!measurable) return insideOffender;
        if (isText) measuredTexts++;
        else measuredBoxes++;
        const past = Math.max(box.right - barBox.right, barBox.left - box.left);
        if (past <= tolerance) return false;
        const name = label();
        if (!insideOffender) offenders.push({label: name, over: past});
        if (past > over) {
            over = past;
            worst = name;
        }
        return true;
    };

    const visit = (element: Element, measurable: boolean, insideOffender: boolean): void => {
        if (element.matches(POPUP) || turning.has(element)) return;
        const style = getComputedStyle(element);
        if (style.display === 'none' || style.position === 'fixed' || style.visibility !== 'visible' || style.opacity === '0') return;
        if (style.clip === 'rect(0px, 0px, 0px, 0px)') return; // sr-only
        const box = element.getBoundingClientRect();
        let offends = insideOffender;
        if (style.display !== 'contents' && box.width > 0 && box.height > 0) offends = record(box, measurable, insideOffender, false, () => describe(element));
        if (element instanceof SVGElement) return;
        // Past a scrolling or clipping box nothing can stick out of it: the box itself was measured above.
        const inner = measurable && !CLIPPING.has(style.overflowX);
        for (const node of Array.from(element.childNodes)) {
            if (node instanceof Element) {
                visit(node, inner, offends);
            } else if (node.nodeType === Node.TEXT_NODE && node.textContent?.trim()) {
                const range = document.createRange();
                range.selectNodeContents(node);
                const textBox = range.getBoundingClientRect();
                if (textBox.width > 0 && textBox.height > 0) record(textBox, inner, offends, true, () => `${describe(element)} › text ${quote(node.textContent ?? '')}`);
            }
        }
    };
    for (const child of Array.from(root.children)) visit(child, true, false);
    offenders.sort((a, b) => b.over - a.over);
    offenders.splice(maxNamed);

    const all = boxes.join('|');
    let hash = 0x811c9dc5;
    for (let i = 0; i < all.length; i++) {
        hash ^= all.charCodeAt(i);
        hash = Math.imul(hash, 0x01000193);
    }

    // The page. Only boxes can widen it, visible or not; nothing inside a clipping box, nothing fixed.
    const documentElement = document.documentElement;
    const pageOverflow = documentElement.scrollWidth - documentElement.clientWidth;
    const pageCulprits: Array<Offender & {inBar: boolean}> = [];
    if (pageOverflow > tolerance) {
        const edge = documentElement.clientWidth;
        const scan = (element: Element, insideCulprit: boolean): void => {
            if (element.matches(POPUP)) return;
            const style = getComputedStyle(element);
            if (style.display === 'none' || style.position === 'fixed') return;
            const box = element.getBoundingClientRect();
            let culprit = insideCulprit;
            if (style.display !== 'contents' && box.width > 0 && box.height > 0) {
                const past = box.right - edge;
                culprit = past > tolerance;
                if (culprit && !insideCulprit) pageCulprits.push({label: describe(element), over: past, inBar: root.contains(element)});
            }
            if (element instanceof SVGElement || CLIPPING.has(style.overflowX)) return;
            for (const child of Array.from(element.children)) scan(child, culprit);
        };
        for (const child of Array.from(document.body.children)) scan(child, false);
        pageCulprits.sort((a, b) => b.over - a.over);
        pageCulprits.splice(maxNamed);
    }

    const thresholds: Record<string, number> = {};
    for (const [key, value] of Object.entries(layout.thresholds ?? {})) if (typeof value === 'number') thresholds[key] = value;

    return {
        notReady,
        signature: `${boxes.length}:${(hash >>> 0).toString(16)}`,
        layoutMode: String(layout.layoutMode),
        barWidth,
        showActionLabels: layout.showActionLabels === true,
        showTabLabels: layout.showTabLabels === true,
        thresholds,
        over,
        worst,
        offenders,
        measuredBoxes,
        measuredTexts,
        pageOverflow,
        pageCulprits,
    };
}

function read(page: Page, bar: Bar, vw: number): Promise<Reading> {
    return page.evaluate(readInPage, {name: bar.name, rootId: bar.root, rowId: bar.row, vw, tolerance: TOLERANCE_PX, maxNamed: MAX_NAMED});
}

/**
 * Positive control, before the sweep: a box hung past the bar's right edge must come back as the furthest
 * offender, by name — or a green sweep could mean a reader that sees nothing. The box is a last block child of
 * the card, so it moves no control of the bar; it is gone before the first width is measured.
 */
async function proveTheReaderSeesOverflow(page: Page, bar: Bar): Promise<void> {
    await page.evaluate(
        ({rootId, probeId, pastPx}) => {
            const root = document.querySelector(`[data-testid="${rootId}"]`);
            if (!root) throw new Error(`[data-testid="${rootId}"] is not in the page`);
            const probe = document.createElement('div');
            probe.dataset.testid = probeId;
            probe.style.cssText = `width: calc(100% + ${pastPx}px); height: 2px;`;
            root.append(probe);
        },
        {rootId: bar.root, probeId: PROBE_ID, pastPx: PROBE_PAST_PX},
    );
    try {
        const reading = await read(page, bar, SWEEP_FROM_PX);
        expect(reading.worst, `positive control: a box hung ${PROBE_PAST_PX} px past [data-testid="${bar.root}"] is reported as the furthest offender (${JSON.stringify(reading.offenders)})`).toBe(PROBE_ID);
        expect(reading.over, 'positive control: and by about how far it was hung (the card has a 1 px border)').toBeGreaterThan(PROBE_PAST_PX - 5);
    } finally {
        await page.evaluate((probeId) => document.querySelector(`[data-testid="${probeId}"]`)?.remove(), PROBE_ID);
    }
}

/** Resize, then read until a timer flush and two rendering updates change nothing. */
async function measureAt(page: Page, bar: Bar, vw: number): Promise<Step> {
    const timerErrors: string[] = [];
    await page.setViewportSize({width: vw, height: VIEWPORT_HEIGHT_PX});
    let previous = await read(page, bar, vw);
    for (let round = 1; round <= MAX_SETTLE_ROUNDS; round++) {
        try {
            await page.clock.runFor(TIMER_FLUSH_MS);
        } catch (error) {
            // The clock rethrows what a page timer threw. The layout is still worth measuring.
            const first = String(error).split('\n')[0];
            if (!timerErrors.includes(first)) timerErrors.push(first);
        }
        const reading = await read(page, bar, vw);
        if (reading.notReady.length === 0 && previous.notReady.length === 0 && reading.signature === previous.signature) return {vw, settled: true, rounds: round, reading, timerErrors};
        previous = reading;
    }
    return {vw, settled: false, rounds: MAX_SETTLE_ROUNDS, reading: previous, timerErrors};
}

async function sweep(page: Page, bar: Bar): Promise<{steps: Step[]; stoppedAt: number | null}> {
    const steps: Step[] = [];
    const deadline = Date.now() + SWEEP_BUDGET_MS;
    for (const vw of WIDTHS) {
        if (Date.now() > deadline) return {steps, stoppedAt: vw};
        steps.push(await measureAt(page, bar, vw));
    }
    return {steps, stoppedAt: null};
}

// =============================================================================
// The report
// =============================================================================

function violates(step: Step): boolean {
    return !step.settled || step.reading.over > TOLERANCE_PX || step.reading.pageOverflow > TOLERANCE_PX;
}

function px(value: number): string {
    return Number.isFinite(value) ? value.toFixed(1) : '?';
}

/** Sweep widths (descending) folded into runs: "1180→1100, 950→850". */
function runs(widths: number[]): string {
    const out: string[] = [];
    let start: number | null = null;
    let last: number | null = null;
    for (const vw of widths) {
        if (last !== null && last - vw === STEP_PX) {
            last = vw;
            continue;
        }
        if (start !== null && last !== null) out.push(start === last ? `${start}` : `${start}→${last}`);
        start = vw;
        last = vw;
    }
    if (start !== null && last !== null) out.push(start === last ? `${start}` : `${start}→${last}`);
    return out.join(', ');
}

function furthest(steps: Step[], metric: (step: Step) => number): Step {
    return steps.reduce((best, step) => (metric(step) > metric(best) ? step : best));
}

function table(steps: Step[]): string[] {
    const header = ['vw', 'mode', 'bar px', 'over px', 'page px', 'what'];
    const rows = steps.map((step) => {
        const reading = step.reading;
        const what: string[] = [];
        if (!step.settled) what.push(`never settled: ${reading.notReady.join('; ') || 'the boxes kept moving'}`);
        if (reading.over > TOLERANCE_PX) {
            const named = reading.offenders.map((offender) => `${offender.label} +${px(offender.over)}`).join(', ');
            const deeper = reading.worst && !reading.offenders.some((offender) => offender.label === reading.worst) ? ` (furthest: ${reading.worst} +${px(reading.over)})` : '';
            what.push(`${named}${deeper}`);
        }
        if (reading.pageOverflow > TOLERANCE_PX) {
            const culprits = reading.pageCulprits.map((culprit) => `${culprit.label}${culprit.inBar ? '' : ' [outside the bar]'} +${px(culprit.over)}`).join(', ');
            what.push(`page: ${culprits || 'no box past the viewport (a text run or a pseudo-element)'}`);
        }
        return [String(step.vw), reading.layoutMode, px(reading.barWidth), reading.over > TOLERANCE_PX ? `+${px(reading.over)}` : '-', reading.pageOverflow > TOLERANCE_PX ? `+${px(reading.pageOverflow)}` : '-', what.join(' | ')];
    });
    const widths = header.map((title, column) => Math.max(title.length, ...rows.map((row) => row[column].length)));
    const line = (cells: string[]): string => cells.map((cell, column) => (column === cells.length - 1 ? cell : column === 1 ? cell.padEnd(widths[column]) : cell.padStart(widths[column]))).join(' | ');
    return [line(header), widths.map((width, column) => '-'.repeat(column === widths.length - 1 ? 4 : width)).join('-+-'), ...rows.map(line)];
}

function report(bar: Bar, lang: Language, subject: Subject, steps: Step[], stoppedAt: number | null): string {
    const bad = steps.filter(violates);
    const thresholds = steps.find((step) => Object.keys(step.reading.thresholds).length > 0)?.reading.thresholds ?? {};
    const lines: string[] = [
        `${bar.name} · ${lang} — ${subject.label}, bar [data-testid="${bar.root}"]`,
        `thresholds (live, window.__lfLayouts.${bar.name}.thresholds): ${Object.entries(thresholds)
            .map(([key, value]) => `${key} ${value}`)
            .join(' · ')}`,
        `swept ${SWEEP_FROM_PX} → ${SWEEP_TO_PX} px every ${STEP_PX} px at height ${VIEWPORT_HEIGHT_PX}: ${steps.length} widths measured, ${bad.length} in violation (a box past the bar or a page wider than the viewport by more than ${TOLERANCE_PX} px, or a layout that never settled)`,
    ];
    if (stoppedAt !== null) lines.push(`INCOMPLETE: the ${SWEEP_BUDGET_MS / 1000} s sweep budget ran out before vw ${stoppedAt}`);
    const widest = Math.max(...steps.map((step) => step.reading.barWidth).filter(Number.isFinite));
    if (typeof thresholds.oneRow === 'number' && !steps.some((step) => step.reading.layoutMode === 'oneRow')) {
        lines.push(`note: oneRow (bar ≥ ${thresholds.oneRow} px) never reached; the widest bar measured is ${px(widest)} px`);
    }

    const spills = bad.filter((step) => step.reading.over > TOLERANCE_PX);
    if (spills.length > 0) {
        lines.push('', 'bar widths that do not fit, by tier (a threshold has to sit above the widest):');
        const modes = [...new Set(spills.map((step) => step.reading.layoutMode))].sort((a, b) => (TIER_ORDER.indexOf(a) + 1 || 99) - (TIER_ORDER.indexOf(b) + 1 || 99));
        for (const mode of modes) {
            const inTier = spills.filter((step) => step.reading.layoutMode === mode);
            const barWidths = inTier.map((step) => step.reading.barWidth);
            const top = furthest(inTier, (step) => step.reading.over);
            lines.push(`  ${mode.padEnd(12)} bar ${px(Math.min(...barWidths))}–${px(Math.max(...barWidths))} px, vw ${runs(inTier.map((step) => step.vw))}; furthest +${px(top.reading.over)} px at vw ${top.vw}: ${top.reading.worst}`);
        }
    }
    const wide = bad.filter((step) => step.reading.pageOverflow > TOLERANCE_PX);
    if (wide.length > 0) {
        const top = furthest(wide, (step) => step.reading.pageOverflow);
        lines.push('', `page wider than the viewport at vw ${runs(wide.map((step) => step.vw))}; furthest +${px(top.reading.pageOverflow)} px at vw ${top.vw}`);
    }
    const unsettled = bad.filter((step) => !step.settled);
    if (unsettled.length > 0) lines.push('', `never settled in ${MAX_SETTLE_ROUNDS} rounds at vw ${runs(unsettled.map((step) => step.vw))}`);
    const thrown = steps.filter((step) => step.timerErrors.length > 0);
    if (thrown.length > 0) lines.push('', `page timers threw at vw ${runs(thrown.map((step) => step.vw))} (not a violation by itself): ${thrown[0].timerErrors[0]}`);
    if (bad.length > 0) lines.push('', ...table(bad));
    return lines.join('\n');
}

// =============================================================================
// The sweep
// =============================================================================

test.describe('Top toolbars: every control inside its bar at every width (K step 13, item 5)', () => {
    for (const bar of BARS) {
        test.describe(bar.name, () => {
            for (const lang of LANGUAGES) {
                test(`${lang}: ${SWEEP_FROM_PX} → ${SWEEP_TO_PX} px, no box past the bar, no sideways page scroll`, async ({page, baseURL, owned}, testInfo) => {
                    if (!baseURL) throw new Error('The sweep needs the runner-provided baseURL');
                    await keepOffline(page, new URL(baseURL).origin);
                    await login(page, TEST_USER);
                    await setLanguage(page, lang);
                    const subject = await bar.subject(page, owned);

                    await page.setViewportSize({width: SWEEP_FROM_PX, height: VIEWPORT_HEIGHT_PX});
                    await navigateTo(page, subject.path);
                    // A page that never settles is usually a page that is not there: say where the app went instead.
                    await bar.ready(page).catch((error: unknown) => {
                        throw new Error(`precondition: ${subject.path} finished loading — the page is at ${new URL(page.url()).pathname} instead.\n${String(error)}`);
                    });
                    await expect(page.locator('html'), `precondition: ${subject.path} renders in ${lang}`).toHaveAttribute('lang', lang);
                    await expect(page.getByTestId(bar.root)).toBeVisible();
                    await expect
                        .poll(() => page.evaluate((name) => Boolean((window as unknown as {__lfLayouts?: Record<string, unknown>}).__lfLayouts?.[name]), bar.name), {
                            message: `precondition: PageToolbar registers window.__lfLayouts.${bar.name}`,
                        })
                        .toBe(true);
                    await page.evaluate(() => document.fonts.ready.then(() => undefined));
                    // The pointer is parked in the top-left corner, the header or the sidebar at every width: a control
                    // of the bar moving under a still pointer would start hover transitions and hover-delayed tooltips.
                    await page.mouse.move(1, 1);

                    await installFrameHook(page);
                    await proveTheReaderSeesOverflow(page, bar);
                    // From here the page is only resized and read: no locator action, whose waits would run on the page clock.
                    await page.clock.install();
                    const {steps, stoppedAt} = await sweep(page, bar);

                    await testInfo.attach(`${bar.name}-${lang}-sweep.json`, {body: JSON.stringify({bar: bar.name, lang, subject, stoppedAt, steps}, null, 1), contentType: 'application/json'});
                    const modes = steps.map((step) => step.reading.layoutMode);
                    expect.soft(new Set(modes).size, `positive control: the sweep crossed at least two tier boundaries (${[...new Set(modes)].join(' → ')})`).toBeGreaterThanOrEqual(3);
                    expect.soft(modes.at(-1), 'positive control: the sweep ends in the narrowest tier').toBe('oneColumn');
                    expect
                        .soft(
                            steps.filter((step) => step.settled && step.reading.measuredTexts === 0).map((step) => step.vw),
                            'positive control: every settled width measured the text of the bar',
                        )
                        .toEqual([]);
                    expect(steps.filter(violates).length + (stoppedAt === null ? 0 : 1), report(bar, lang, subject, steps, stoppedAt)).toBe(0);
                });
            }
        });
    }
});
