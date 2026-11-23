/**
 * The «Allocazione» tab of the portfolio view (lane 80, issue #89, F2 + F3): Dashboard and broker page.
 *
 * Where am I exposed, looking at only a part? The tab asks `POST /portfolio/allocation` with the page's own scope, the dimension
 * and the user's filters; the backend answers with the base (the 100 % of the chart), what the class filter leaves out and what is
 * excluded, and `base + outside + excluded` is the net worth of the view's day. The frontend computes none of it, and neither does
 * this spec: it reads what the page sent and what the backend answered, and asserts the screen follows both.
 *
 * Read-only on the shared database: TEST_USER, nothing written but the browser's own localStorage — the filters the tab remembers
 * per page (`lf_<userId>_allocation-filters:dashboard`, `…:broker:<id>`) and the privacy flag (`librefolio-privacy`). Each test
 * starts from the first opening (its keys removed before the tab mounts) and removes what it wrote, so no other spec meets a
 * remembered filter. A Playwright context is fresh per test, so the removal is hygiene, not a dependency.
 *
 * What the data must hold is read from the answer, never assumed: the class to turn off is one the answer lists with an amount, the
 * bucket to exclude is one the answer has a slice for, the slice to open is one that really lists assets, the broker is an owned one
 * whose answer has two classes. A missing case is a thrown Error pointing at `populate_mock_data.py`, never a skip. Owned brokers come
 * from `GET /brokers` (`page.request`, which nothing intercepts), never hard-coded. Every allocation request the page sends is recorded
 * with `page.on('request')` together with the answer it got; nothing here counts a request it did not watch the page send.
 *
 * Both projects run it. The layout is read from the same media queries the product reads (`lg` 1024: the filter column or the
 * «Filters» button with chips; `md` 768: the side boxes of the tiles; `sm` 640: dimension buttons or a select), never from the
 * project's name.
 *
 * Settled states read: the tab root's `data-busy`, `T-tiles` and `T-results` visible, `T-results` `data-dimension` / `data-view`.
 */

import type {Request} from '@playwright/test';
import {expect, test, type Locator, type Page} from '../fixtures/playwright';
import {waitForSettled} from '../fixtures/app-events';
import {login, navigateTo} from '../fixtures/auth-helpers';
import {focusHeaderControlByKeyboard} from '../fixtures/headerKeyboardFocus';
import {TEST_USER} from '../fixtures/test-users';

const API = '/api/v1';
const ALLOCATION_PATH = `${API}/portfolio/allocation`;
const PAGE_TIMEOUT = 30_000;

const DASH = 'dashboard-allocation-tab';
const BROKER = 'broker-allocation-tab';

/** `PRIVACY_PLACEHOLDER` of `src/lib/utils/privacy/maskable.ts`, copied rather than imported: that module needs `$app/environment`, which Playwright's node cannot resolve (as `privacy-masking.spec.ts` does). */
const PRIVACY_PLACEHOLDER = '•••';
/** `PRIVACY_STORAGE_KEY` of `privacyStore.svelte.ts`: a bare key, device-local. */
const PRIVACY_STORAGE_KEY = 'librefolio-privacy';

/** What the first opening leaves out of the body: no class filter, no exclusion, no history. */
const FILTER_KEYS = ['classes', 'exclude_buckets', 'exclude_asset_ids', 'include_history'];

type AllocationBody = {
    broker_ids?: number[];
    date_range?: {start?: string; end?: string};
    target_currency?: string;
    apply_ownership_share?: boolean;
    dimension?: string;
    classes?: string[];
    exclude_buckets?: string[];
    exclude_asset_ids?: number[];
    include_history?: boolean;
};

type AllocationAnswer = {
    currency: string;
    dimension: string;
    applicable_buckets: string[];
    portfolio_total: string;
    base: string;
    base_share_of_portfolio: string | null;
    slices: Array<{key: string; asset_id: number | null; amount: string; assets: Array<{asset_id: number; amount: string}>}>;
    outside: {amount: string; by_class: Array<{asset_class: string; amount: string}>};
    excluded: {amount: string; by_bucket: Array<{key: string; amount: string}>; by_asset: Array<{asset_id: number; amount: string}>};
    classes: Array<{asset_class: string; amount: string}>;
    assets: Array<{asset_id: number; asset_class: string; amount: string; name: string}>;
    history: unknown[] | null;
};

/** One allocation request the page sent, and the answer it got (null until it lands, and for a request that failed). */
interface Allocation {
    body: AllocationBody;
    answer: AllocationAnswer | null;
}

type BrokerListItem = {id: number; name: string; user_role?: string | null; user_share_percentage?: string | number | null};
type StoredFilters = {classes: string[] | null; excludeBuckets: string[]; excludeAssetIds: number[]};

// ---------------------------------------------------------------------------------------------------------------------------------
// What the page asked, and what it was told
// ---------------------------------------------------------------------------------------------------------------------------------

/** Every `POST /portfolio/allocation` the page sends, in order, each with its answer once it lands. Armed before the navigation that opens the tab. */
function recordAllocations(page: Page): Allocation[] {
    const calls: Allocation[] = [];
    const byRequest = new Map<Request, Allocation>();
    page.on('request', (request) => {
        if (request.method() !== 'POST' || new URL(request.url()).pathname !== ALLOCATION_PATH) return;
        const call: Allocation = {body: (request.postDataJSON() ?? {}) as AllocationBody, answer: null};
        byRequest.set(request, call);
        calls.push(call);
    });
    page.on('response', async (response) => {
        const call = byRequest.get(response.request());
        if (!call || !response.ok()) return;
        try {
            call.answer = (await response.json()) as AllocationAnswer;
        } catch {
            // The page navigated away while the body was read: that request has no answer to keep.
        }
    });
    return calls;
}

/** The first request sent after `since` whose body `accept`s, once its answer has landed. */
async function answeredAfter(calls: readonly Allocation[], since: number, accept: (body: AllocationBody) => boolean, message: string): Promise<Allocation & {answer: AllocationAnswer}> {
    const find = () => calls.slice(since).find((call) => call.answer !== null && accept(call.body));
    await expect.poll(() => find() !== undefined, {message, timeout: PAGE_TIMEOUT}).toBe(true);
    const found = find();
    if (!found || found.answer === null) throw new Error(message);
    return {body: found.body, answer: found.answer};
}

/** The first opening: no class filter, no exclusion, no history, the sector dimension. */
function isFirstOpening(body: AllocationBody): boolean {
    return body.dimension === 'sector' && FILTER_KEYS.every((key) => !(key in body));
}

function sorted<T extends string | number>(values: readonly T[] | undefined): T[] {
    return [...(values ?? [])].sort();
}

function sameSet(actual: readonly string[] | undefined, expected: readonly string[]): boolean {
    return actual !== undefined && JSON.stringify(sorted(actual)) === JSON.stringify(sorted(expected));
}

/** `base + outside + excluded` is the net worth of the view's day: the backend's invariant, read on the strings it wrote. */
function expectNavIdentity(answer: AllocationAnswer, where: string): void {
    const sum = parseFloat(answer.base) + parseFloat(answer.outside.amount) + parseFloat(answer.excluded.amount);
    expect(Math.abs(sum - parseFloat(answer.portfolio_total)), `${where}: base + outside + excluded (${sum}) is not the net worth (${answer.portfolio_total})`).toBeLessThanOrEqual(0.01);
}

// ---------------------------------------------------------------------------------------------------------------------------------
// Owned brokers
// ---------------------------------------------------------------------------------------------------------------------------------

/** The brokers the Dashboard counts as the user's own: OWNER with a share unset or above zero, as `getOwnedBrokers()` keeps them. */
async function ownedBrokerIds(page: Page): Promise<number[]> {
    const response = await page.request.get(`${API}/brokers`);
    expect(response.ok(), `GET ${API}/brokers → HTTP ${response.status()}`).toBe(true);
    const items = ((await response.json()) as {items?: BrokerListItem[]}).items ?? [];
    return items
        .filter((broker) => broker.user_role === 'OWNER' && (broker.user_share_percentage == null || Number(broker.user_share_percentage) > 0))
        .map((broker) => broker.id)
        .sort((left, right) => left - right);
}

function requireOwned(owned: readonly number[]): void {
    if (owned.length === 0) throw new Error(`${TEST_USER.username} owns no broker: the Dashboard cannot ask the allocation. Check populate_mock_data.py.`);
}

/**
 * The Dashboard's scope is the brokers the user owns, never none (which the backend widens to every broker the user can see). `readings`
 * are the owned set as the backend listed it on both sides of the page's own read: a neighbour may create or delete a broker of this user
 * in between, so the body must equal one of them.
 */
function isOwnedScope(body: AllocationBody, readings: readonly (readonly number[])[]): boolean {
    const ids = body.broker_ids;
    return Array.isArray(ids) && ids.length > 0 && readings.some((owned) => JSON.stringify(sorted(owned)) === JSON.stringify(sorted(ids)));
}

/** An owned broker whose own answer (the broker page's: counted whole) holds two classes with an amount — a class filter needs one to turn off and one to keep. */
async function ownedBrokerWithTwoClasses(page: Page, owned: readonly number[]): Promise<number> {
    for (const id of owned) {
        const response = await page.request.post(ALLOCATION_PATH, {data: {broker_ids: [id], apply_ownership_share: false, dimension: 'sector'}, timeout: PAGE_TIMEOUT});
        expect(response.ok(), `POST ${ALLOCATION_PATH} for broker ${id} → HTTP ${response.status()}`).toBe(true);
        const answer = (await response.json()) as AllocationAnswer;
        if (answer.classes.filter((row) => parseFloat(row.amount) > 0).length >= 2) return id;
    }
    throw new Error(`None of ${TEST_USER.username}'s owned brokers (${owned.join(', ')}) holds two classes: a class filter on the broker page needs two. Check backend/test_scripts/test_db/populate_mock_data.py.`);
}

// ---------------------------------------------------------------------------------------------------------------------------------
// The browser's memory
// ---------------------------------------------------------------------------------------------------------------------------------

interface StorageKeys {
    dashboard: string;
    broker: (brokerId: number) => string;
}

/** The user-scoped keys the tab writes (`getUserStorageKey`: `lf_<userId>_<key>`), for the user this page is signed in as. */
async function userStorageKeys(page: Page): Promise<StorageKeys> {
    const response = await page.request.get(`${API}/auth/me`);
    expect(response.ok(), `GET ${API}/auth/me → HTTP ${response.status()}`).toBe(true);
    const id = ((await response.json()) as {user?: {id?: number | string}}).user?.id;
    if (id === undefined) throw new Error('GET /auth/me carries no user id: the storage key of the filters cannot be built');
    return {dashboard: `lf_${id}_allocation-filters:dashboard`, broker: (brokerId) => `lf_${id}_allocation-filters:broker:${brokerId}`};
}

async function readStored(page: Page, key: string): Promise<StoredFilters | null> {
    const raw = await page.evaluate((storageKey) => localStorage.getItem(storageKey), key);
    return raw === null ? null : (JSON.parse(raw) as StoredFilters);
}

async function forgetStored(page: Page, keys: readonly string[]): Promise<void> {
    await page.evaluate((storageKeys) => {
        for (const key of storageKeys) localStorage.removeItem(key);
    }, keys as string[]);
}

/** The `finally` half: what the test wrote is removed. It never throws, so it cannot hide the failure that brought the test here. */
async function cleanUp(page: Page, keys: readonly string[]): Promise<void> {
    await forgetStored(page, keys).catch(() => undefined);
}

// ---------------------------------------------------------------------------------------------------------------------------------
// Layout, as the product reads it
// ---------------------------------------------------------------------------------------------------------------------------------

async function matches(page: Page, query: string): Promise<boolean> {
    return page.evaluate((mediaQuery) => window.matchMedia(mediaQuery).matches, query);
}

/** `lg`: the filter panel is a column; below it, behind the «Filters» button, with the choices as chips. */
const isWide = (page: Page) => matches(page, '(min-width: 1024px)');
/** `sm`: the dimension is four buttons; below it, one select. */
const isRoomy = (page: Page) => matches(page, '(min-width: 640px)');
/** `md`: the «Outside the filter» and «Excluded» boxes of the tiles are drawn; below it, one line under the base. */
const hasSideBoxes = (page: Page) => matches(page, '(min-width: 768px)');

// ---------------------------------------------------------------------------------------------------------------------------------
// Opening the tab
// ---------------------------------------------------------------------------------------------------------------------------------

function dashboard(page: Page): Locator {
    return page.getByTestId('dashboard-page');
}

/** The tab has asked, been answered, and drawn: tiles and results on screen, no failure, `data-busy` ended `false`. */
async function tabReady(page: Page, tabId: string): Promise<Locator> {
    const tab = page.getByTestId(tabId);
    await expect(tab).toBeVisible({timeout: PAGE_TIMEOUT});
    await expect(page.getByTestId(`${tabId}-tiles`)).toBeVisible({timeout: PAGE_TIMEOUT});
    await expect(page.getByTestId(`${tabId}-results`)).toBeVisible({timeout: PAGE_TIMEOUT});
    await waitForSettled(tab, PAGE_TIMEOUT);
    await expect(page.getByTestId(`${tabId}-failed`)).toHaveCount(0);
    return tab;
}

/** The Dashboard, then its «Allocazione» tab through the tab bar. */
async function openDashboardTab(page: Page): Promise<Locator> {
    await navigateTo(page, '/dashboard');
    await waitForSettled(dashboard(page), PAGE_TIMEOUT);
    await page.getByTestId('dashboard-tab-allocazione').click();
    return tabReady(page, DASH);
}

// ---------------------------------------------------------------------------------------------------------------------------------
// The filters: a column on a wide screen, a popover below it
// ---------------------------------------------------------------------------------------------------------------------------------

/** The filter panel on screen, whichever way the layout shows it; a toggle is asked for its state and clicked only if it is not there. */
async function openFilters(page: Page, tabId: string): Promise<Locator> {
    if (!(await isWide(page))) {
        const button = page.getByTestId(`${tabId}-filters-button`);
        await expect(button).toBeVisible({timeout: PAGE_TIMEOUT});
        if ((await button.getAttribute('aria-expanded')) !== 'true') await button.click();
        await expect(button).toHaveAttribute('aria-expanded', 'true');
    }
    const panel = page.getByTestId(`${tabId}-filters`);
    await expect(panel).toBeVisible({timeout: PAGE_TIMEOUT});
    return panel;
}

/** Below `lg`, the popover closed (Escape), so what lies under it can be clicked; on a wide screen the column stays. */
async function closeFilters(page: Page, tabId: string): Promise<void> {
    if (await isWide(page)) return;
    const button = page.getByTestId(`${tabId}-filters-button`);
    if ((await button.getAttribute('aria-expanded')) === 'true') await page.keyboard.press('Escape');
    await expect(button).toHaveAttribute('aria-expanded', 'false');
    await expect(page.getByTestId(`${tabId}-filters`)).toBeHidden();
}

/** A class switch of the panel, asserted in the state it is expected to be in before it is pressed. */
async function pressClassSwitch(page: Page, tabId: string, assetClass: string, from: 'on' | 'off'): Promise<void> {
    const toggle = page.getByTestId(`${tabId}-filters-class-${assetClass}-switch`);
    await expect(toggle, `precondition: class ${assetClass} is ${from}`).toHaveAttribute('aria-checked', String(from === 'on'));
    await toggle.click();
}

// ---------------------------------------------------------------------------------------------------------------------------------
// Dimension and view
// ---------------------------------------------------------------------------------------------------------------------------------

/** The dimension the way a user picks it: a button from `sm` up, the select below. Ends on the choice made. */
async function chooseDimension(page: Page, tabId: string, dimension: 'sector' | 'geography' | 'type' | 'asset'): Promise<void> {
    if (await isRoomy(page)) {
        const button = page.getByTestId(`${tabId}-results-dimension-${dimension}`);
        await button.click();
        await expect(button).toHaveAttribute('aria-pressed', 'true');
        return;
    }
    await page.getByTestId(`${tabId}-results-dimension-select-button`).click();
    const option = page.getByTestId(`${tabId}-results-dimension-select-option-${dimension}`);
    await option.click();
    await expect(option).toBeHidden();
}

/** A CSS attribute-selector string value. */
function cssString(value: string): string {
    return `"${value.replace(/\\/g, '\\\\').replace(/"/g, '\\"')}"`;
}

/** A row of the results table by its `data-row-id` (`slice:<key>`, `detail:<key>:<assetId>`, `excluded:bucket:<key>`…). */
function tableRow(page: Page, tabId: string, rowId: string): Locator {
    return page.getByTestId(`${tabId}-results-table`).locator(`tr[data-row-id=${cssString(rowId)}]`);
}

// ---------------------------------------------------------------------------------------------------------------------------------
// Privacy
// ---------------------------------------------------------------------------------------------------------------------------------

/**
 * Flips privacy from the header, asserting the state before and after (`flipPrivacy` of `allocation-negative-cash.spec.ts`).
 * The header slides away on scroll: a header control reached by keyboard pins it, so the click lands on the toggle.
 */
async function flipPrivacy(page: Page, on: boolean): Promise<void> {
    const header = page.getByTestId('app-header');
    const toggle = header.getByTestId('privacy-toggle');
    await expect(toggle, `privacy starts ${on ? 'off' : 'on'}`).toHaveAttribute('aria-pressed', String(!on));
    await focusHeaderControlByKeyboard(page, 'privacy-toggle');
    await expect(header).toHaveAttribute('data-scroll-state', 'pinned');
    await toggle.click();
    await expect(toggle).toHaveAttribute('aria-pressed', String(on));
}

// ---------------------------------------------------------------------------------------------------------------------------------

test.describe('«Allocazione» tab (lane 80, #89)', () => {
    test('the Dashboard asks for the brokers the user owns with the first-opening body, and the base, the outside and the excluded add up to the net worth', async ({page}) => {
        test.setTimeout(120_000);
        const calls = recordAllocations(page);
        await login(page, TEST_USER);
        const keys = await userStorageKeys(page);
        const readings = [await ownedBrokerIds(page)];
        requireOwned(readings[0]);
        await forgetStored(page, [keys.dashboard]);
        try {
            await openDashboardTab(page);
            const first = await answeredAfter(calls, 0, isFirstOpening, 'the tab never asked the first-opening question (sector, no filter)');
            readings.push(await ownedBrokerIds(page));

            // The scope: the owned brokers (never none, which the backend widens), counted at the owner's share.
            expect(isOwnedScope(first.body, readings), `the first body is not over exactly the brokers the user owns (body: ${JSON.stringify(first.body.broker_ids)}; owned: ${readings.map((ids) => `[${ids.join(', ')}]`).join(' or ')})`).toBe(true);
            expect(first.body.apply_ownership_share, 'the Dashboard counts the owner’s share: no apply_ownership_share:false').toBeUndefined();

            // The identity, on the answer the page was given.
            expectNavIdentity(first.answer, 'first opening');
            await expect(page.getByTestId(`${DASH}-tiles-base`)).toBeVisible();
            await expect(page.getByTestId(`${DASH}-tiles-base-amount`)).toBeVisible();
            await expect(page.getByTestId(`${DASH}-tiles-base-bar`), 'the bar draws the share the backend sent').toHaveAttribute('data-share', String(first.answer.base_share_of_portfolio ?? ''));
            await expect(page.getByTestId(`${DASH}-results`)).toHaveAttribute('data-dimension', 'sector');
            await expect(page.getByTestId(`${DASH}-results`)).toHaveAttribute('data-view', 'now');
        } finally {
            await cleanUp(page, [keys.dashboard]);
        }
    });

    test('a class switched off narrows the question, is remembered, survives a reload, and «Rimuovi filtri» takes it away', async ({page}) => {
        test.setTimeout(120_000);
        const calls = recordAllocations(page);
        await login(page, TEST_USER);
        const keys = await userStorageKeys(page);
        const readings = [await ownedBrokerIds(page)];
        requireOwned(readings[0]);
        await forgetStored(page, [keys.dashboard]);
        try {
            const tab = await openDashboardTab(page);
            const first = await answeredAfter(calls, 0, isFirstOpening, 'the tab never asked the first-opening question');
            const held = first.answer.classes.filter((row) => parseFloat(row.amount) > 0).sort((left, right) => parseFloat(right.amount) - parseFloat(left.amount));
            const dropped = held[0]?.asset_class;
            if (first.answer.classes.length < 2 || dropped === undefined) {
                throw new Error(`The Dashboard answer lists ${first.answer.classes.length} class(es) (${first.answer.classes.map((row) => `${row.asset_class} ${row.amount}`).join(', ')}): a class filter needs two, one with an amount. Check backend/test_scripts/test_db/populate_mock_data.py.`);
            }
            const kept = first.answer.classes.map((row) => row.asset_class).filter((assetClass) => assetClass !== dropped);
            const baseAmount = page.getByTestId(`${DASH}-tiles-base-amount`);
            const baseBefore = (await baseAmount.innerText()).trim();

            // Turn the largest class off.
            await openFilters(page, DASH);
            const since = calls.length;
            await pressClassSwitch(page, DASH, dropped, 'on');
            const narrowed = await answeredAfter(calls, since, (body) => sameSet(body.classes, kept), `turning ${dropped} off never asked the question with the other classes (${kept.join(', ')})`);
            expect(narrowed.body.dimension, 'the filter keeps the dimension').toBe('sector');
            expect(isOwnedScope(narrowed.body, readings), 'the filtered question left the owned scope').toBe(true);
            expect(parseFloat(narrowed.answer.base), 'the base did not shrink with the class taken out').toBeLessThan(parseFloat(first.answer.base));
            expect(
                narrowed.answer.outside.by_class.map((row) => row.asset_class),
                'the class taken out is what the filter leaves out',
            ).toContain(dropped);
            expectNavIdentity(narrowed.answer, `without ${dropped}`);
            await waitForSettled(tab, PAGE_TIMEOUT);
            await expect(baseAmount, 'the base tile still shows the unfiltered base').not.toHaveText(baseBefore);
            await expect(page.getByTestId(`${DASH}-filters-class-${dropped}`)).toHaveAttribute('data-on', 'false');
            await expect(page.getByTestId(`${DASH}-filters-class-${dropped}-switch`)).toHaveAttribute('aria-checked', 'false');
            await closeFilters(page, DASH);
            if (!(await isWide(page))) {
                // Narrow: the choices are chips. One per class kept, none for the class taken out.
                const chip = (assetClass: string) => page.locator(`[data-testid="${DASH}-chips-chip"][data-kind="class"][data-value=${cssString(assetClass)}]`);
                for (const assetClass of kept) await expect(chip(assetClass), `no chip for the class kept: ${assetClass}`).toHaveCount(1);
                await expect(chip(dropped), 'a chip for the class taken out').toHaveCount(0);
            }

            // Remembered under the Dashboard's own key.
            await expect.poll(async () => sorted((await readStored(page, keys.dashboard))?.classes ?? []), {message: 'the class list was not stored under the Dashboard key', timeout: PAGE_TIMEOUT}).toEqual(sorted(kept));

            // A reload: the tab's first question already carries the filter.
            const beforeReload = calls.length;
            await navigateTo(page, '/dashboard?tab=allocazione');
            await expect.poll(() => calls.length, {message: 'the reopened tab asked nothing', timeout: PAGE_TIMEOUT}).toBeGreaterThan(beforeReload);
            const reopened = calls[beforeReload];
            if (!reopened) throw new Error('the reopened tab asked nothing');
            expect(sameSet(reopened.body.classes, kept), `the first question after the reload is not the remembered one (classes: ${JSON.stringify(reopened.body.classes)}; expected: ${kept.join(', ')})`).toBe(true);
            await tabReady(page, DASH);
            await openFilters(page, DASH);
            await expect(page.getByTestId(`${DASH}-filters-class-${dropped}`)).toHaveAttribute('data-on', 'false');

            // «Rimuovi filtri»: the first-opening body again, and the memory emptied.
            const sinceClear = calls.length;
            await page.getByTestId(`${DASH}-filters-clear`).click();
            await answeredAfter(calls, sinceClear, isFirstOpening, '«Rimuovi filtri» never asked the first-opening question again');
            await expect.poll(() => readStored(page, keys.dashboard), {message: 'the cleared filters were not stored as the first opening', timeout: PAGE_TIMEOUT}).toEqual({classes: null, excludeBuckets: [], excludeAssetIds: []});
            await expect(page.getByTestId(`${DASH}-filters-clear`), 'the link goes away with the last filter').toHaveCount(0);
            await expect(page.getByTestId(`${DASH}-filters-class-${dropped}`)).toHaveAttribute('data-on', 'true');
        } finally {
            await cleanUp(page, [keys.dashboard]);
        }
    });

    test('excluding a bucket the dimension has: the question carries it, the excluded box lists it, and switching it back restores the base', async ({page}) => {
        test.setTimeout(150_000);
        const calls = recordAllocations(page);
        await login(page, TEST_USER);
        const keys = await userStorageKeys(page);
        requireOwned(await ownedBrokerIds(page));
        await forgetStored(page, [keys.dashboard]);
        try {
            const tab = await openDashboardTab(page);
            await answeredAfter(calls, 0, isFirstOpening, 'the tab never asked the first-opening question');

            // A dimension with a bucket the user can exclude AND a slice for it: read from the answer, switching the dimension until one has it.
            let dimension: 'sector' | 'geography' | 'type' | null = null;
            let bucket = '';
            for (const candidate of ['sector', 'geography', 'type'] as const) {
                const since = calls.length;
                if (candidate !== 'sector') await chooseDimension(page, DASH, candidate);
                const answered = candidate === 'sector' ? await answeredAfter(calls, 0, isFirstOpening, 'no sector answer') : await answeredAfter(calls, since, (body) => body.dimension === candidate, `no ${candidate} answer`);
                const slice = answered.answer.slices.find((row) => answered.answer.applicable_buckets.includes(row.key) && parseFloat(row.amount) !== 0);
                if (slice) {
                    dimension = candidate;
                    bucket = slice.key;
                    break;
                }
            }
            if (dimension === null) {
                throw new Error('No dimension (sector, geography, type) has a slice in an excludable bucket (Unknown, Other): the exclusion needs one. Check backend/test_scripts/test_db/populate_mock_data.py (an asset with no sector or country profile).');
            }
            await expect(page.getByTestId(`${DASH}-results`)).toHaveAttribute('data-dimension', dimension);
            await waitForSettled(tab, PAGE_TIMEOUT);
            const bucketRow = page.locator(`[data-testid="${DASH}-tiles-excluded-bucket"][data-key=${cssString(bucket)}]`);
            await expect(bucketRow, 'precondition: the bucket is not excluded yet').toHaveCount(0);

            // Exclude it.
            await openFilters(page, DASH);
            const toggle = page.getByTestId(`${DASH}-filters-bucket-${bucket}-switch`);
            await expect(toggle, `precondition: ${bucket} is in the base`).toHaveAttribute('aria-checked', 'false');
            const since = calls.length;
            await toggle.click();
            const excluded = await answeredAfter(calls, since, (body) => body.dimension === dimension && sameSet(body.exclude_buckets, [bucket]), `excluding ${bucket} never asked with exclude_buckets`);
            expect(excluded.body.classes, 'an exclusion is no class filter').toBeUndefined();
            expect(
                excluded.answer.excluded.by_bucket.map((row) => row.key),
                'the answer does not list the excluded bucket',
            ).toContain(bucket);
            expect(
                excluded.answer.slices.map((row) => row.key),
                'the excluded bucket is still a slice of the base',
            ).not.toContain(bucket);
            expectNavIdentity(excluded.answer, `without ${bucket}`);
            await waitForSettled(tab, PAGE_TIMEOUT);
            // The excluded box: a row for the bucket in the DOM on every layout, drawn from `md` up (below it the boxes are one line).
            await expect(bucketRow).toHaveCount(1);
            if (await hasSideBoxes(page)) await expect(bucketRow).toBeVisible();
            await expect(tableRow(page, DASH, `excluded:bucket:${bucket}`)).toBeVisible();
            await expect.poll(async () => (await readStored(page, keys.dashboard))?.excludeBuckets ?? [], {message: 'the exclusion was not stored', timeout: PAGE_TIMEOUT}).toEqual([bucket]);

            // Back in.
            const sinceBack = calls.length;
            await toggle.click();
            const back = await answeredAfter(calls, sinceBack, (body) => body.dimension === dimension && !('exclude_buckets' in body), `switching ${bucket} back never asked without exclude_buckets`);
            expect(
                back.answer.excluded.by_bucket.map((row) => row.key),
                'the bucket is still excluded',
            ).not.toContain(bucket);
            await waitForSettled(tab, PAGE_TIMEOUT);
            await expect(bucketRow).toHaveCount(0);
        } finally {
            await cleanUp(page, [keys.dashboard]);
        }
    });

    test('each dimension asks again and the table follows; a slice opens its assets and closes them; History asks with include_history', async ({page}) => {
        test.setTimeout(180_000);
        const calls = recordAllocations(page);
        await login(page, TEST_USER);
        const keys = await userStorageKeys(page);
        requireOwned(await ownedBrokerIds(page));
        await forgetStored(page, [keys.dashboard]);
        try {
            const tab = await openDashboardTab(page);
            const sector = await answeredAfter(calls, 0, isFirstOpening, 'the tab never asked the first-opening question');
            const results = page.getByTestId(`${DASH}-results`);

            // A slice that really lists assets (the cash and the asset dimension list none): open, its assets under it, closed.
            const openable = sector.answer.slices.find((slice) => slice.key !== 'Liquidity' && slice.assets.length > 0);
            if (!openable) throw new Error('The sector answer has no slice that lists assets: the slice detail needs one. Check backend/test_scripts/test_db/populate_mock_data.py.');
            const sliceRow = tableRow(page, DASH, `slice:${openable.key}`);
            await expect(sliceRow).toBeVisible({timeout: PAGE_TIMEOUT});
            await sliceRow.click();
            for (const asset of openable.assets) await expect(tableRow(page, DASH, `detail:${openable.key}:${asset.asset_id}`), `the slice ${openable.key} does not show asset ${asset.asset_id} under it`).toBeVisible();
            await sliceRow.click();
            for (const asset of openable.assets) await expect(tableRow(page, DASH, `detail:${openable.key}:${asset.asset_id}`)).toHaveCount(0);

            // Area (geography): asks again with the dimension, the map and its caption, the slices in the table.
            const sinceGeography = calls.length;
            await chooseDimension(page, DASH, 'geography');
            const geography = await answeredAfter(calls, sinceGeography, (body) => body.dimension === 'geography' && !('include_history' in body), 'choosing Area never asked with dimension geography');
            await expect(results).toHaveAttribute('data-dimension', 'geography');
            await expect(page.getByTestId(`${DASH}-results-table`)).toHaveAttribute('data-dimension', 'geography');
            await expect(page.getByTestId(`${DASH}-results-chart`)).toBeVisible();
            await expect(page.getByTestId(`${DASH}-results-map-caption`)).toBeVisible();
            for (const slice of geography.answer.slices) await expect(tableRow(page, DASH, `slice:${slice.key}`), `the geography slice ${slice.key} is not in the table`).toBeVisible();

            // Asset: the pie with the base in its middle, one slice row per asset.
            const sinceAsset = calls.length;
            await chooseDimension(page, DASH, 'asset');
            const asset = await answeredAfter(calls, sinceAsset, (body) => body.dimension === 'asset' && !('include_history' in body), 'choosing Asset never asked with dimension asset');
            await expect(results).toHaveAttribute('data-dimension', 'asset');
            await expect(page.getByTestId(`${DASH}-results-center`)).toBeVisible();
            for (const slice of asset.answer.slices) await expect(tableRow(page, DASH, `slice:${slice.key}`), `the asset slice ${slice.key} is not in the table`).toBeVisible();
            await waitForSettled(tab, PAGE_TIMEOUT);

            // History: the same dimension asked with include_history, the history container (or its empty state) in place of the chart.
            const sinceHistory = calls.length;
            await page.getByTestId(`${DASH}-results-view-history`).click();
            const history = await answeredAfter(calls, sinceHistory, (body) => body.dimension === 'asset' && body.include_history === true, 'History never asked with include_history');
            expect(history.answer.history, 'the history answer carries no history').not.toBeNull();
            await expect(results).toHaveAttribute('data-view', 'history');
            await expect(page.getByTestId(`${DASH}-results-history`)).toBeVisible();
            await waitForSettled(tab, PAGE_TIMEOUT);

            // And back to «Now».
            const sinceNow = calls.length;
            await page.getByTestId(`${DASH}-results-view-now`).click();
            await answeredAfter(calls, sinceNow, (body) => body.dimension === 'asset' && !('include_history' in body), 'Now never asked without include_history');
            await expect(results).toHaveAttribute('data-view', 'now');
            await expect(page.getByTestId(`${DASH}-results-history`)).toBeHidden();
            await expect(page.getByTestId(`${DASH}-results-chart`)).toBeVisible();
        } finally {
            await cleanUp(page, [keys.dashboard]);
        }
    });

    test('the broker page asks for its own broker, whole, and keeps its filters apart from the Dashboard’s', async ({page}) => {
        test.setTimeout(150_000);
        const calls = recordAllocations(page);
        await login(page, TEST_USER);
        const keys = await userStorageKeys(page);
        const owned = await ownedBrokerIds(page);
        requireOwned(owned);
        const brokerId = await ownedBrokerWithTwoClasses(page, owned);
        const brokerKey = keys.broker(brokerId);
        await forgetStored(page, [keys.dashboard, brokerKey]);
        try {
            await navigateTo(page, `/brokers/${brokerId}?tab=allocazione`);
            await expect(page.getByTestId('broker-detail-page')).toBeVisible({timeout: PAGE_TIMEOUT});
            const tab = await tabReady(page, BROKER);
            const first = await answeredAfter(calls, 0, (body) => isFirstOpening(body) && sameSet(body.broker_ids?.map(String), [String(brokerId)]), `the broker page never asked the first-opening question for broker ${brokerId}`);
            expect(first.body.apply_ownership_share, 'a broker page counts its broker whole').toBe(false);
            expectNavIdentity(first.answer, `broker ${brokerId}`);

            // Turn a class off here.
            const held = first.answer.classes.filter((row) => parseFloat(row.amount) > 0).sort((left, right) => parseFloat(right.amount) - parseFloat(left.amount));
            const dropped = held[0]?.asset_class;
            if (dropped === undefined || first.answer.classes.length < 2) throw new Error(`Broker ${brokerId} answered ${first.answer.classes.length} class(es): a class filter needs two. Check backend/test_scripts/test_db/populate_mock_data.py.`);
            const kept = first.answer.classes.map((row) => row.asset_class).filter((assetClass) => assetClass !== dropped);
            await openFilters(page, BROKER);
            const since = calls.length;
            await pressClassSwitch(page, BROKER, dropped, 'on');
            const narrowed = await answeredAfter(calls, since, (body) => sameSet(body.classes, kept), `turning ${dropped} off never asked with the other classes`);
            expect(sameSet(narrowed.body.broker_ids?.map(String), [String(brokerId)]), 'the filtered question left the broker').toBe(true);
            expect(narrowed.body.apply_ownership_share).toBe(false);
            await waitForSettled(tab, PAGE_TIMEOUT);

            // Its own key; the Dashboard's untouched.
            await expect.poll(async () => sorted((await readStored(page, brokerKey))?.classes ?? []), {message: `the class list was not stored under the broker's key`, timeout: PAGE_TIMEOUT}).toEqual(sorted(kept));
            expect(await readStored(page, keys.dashboard), 'the broker’s filter was written under the Dashboard’s key').toBeNull();

            // Back on the Dashboard, in the same test: its first question has no filter.
            const beforeDashboard = calls.length;
            await navigateTo(page, '/dashboard?tab=allocazione');
            await expect.poll(() => calls.length, {message: 'the Dashboard tab asked nothing', timeout: PAGE_TIMEOUT}).toBeGreaterThan(beforeDashboard);
            const dashboardFirst = calls[beforeDashboard];
            if (!dashboardFirst) throw new Error('the Dashboard tab asked nothing');
            expect(
                FILTER_KEYS.filter((key) => key in dashboardFirst.body),
                'the Dashboard opened with the broker page’s filter',
            ).toEqual([]);
            expect(dashboardFirst.body.apply_ownership_share, 'the Dashboard counts the owner’s share').toBeUndefined();
            await tabReady(page, DASH);
            await expect(page.getByTestId(`${DASH}-filters-clear`), 'the Dashboard shows a filter it never had').toHaveCount(0);
        } finally {
            await cleanUp(page, [keys.dashboard, brokerKey]);
        }
    });

    test('privacy masks the base amount, and unmasks it, while the percentage stays readable', async ({page}) => {
        test.setTimeout(120_000);
        const calls = recordAllocations(page);
        await login(page, TEST_USER);
        const keys = await userStorageKeys(page);
        requireOwned(await ownedBrokerIds(page));
        await forgetStored(page, [keys.dashboard, PRIVACY_STORAGE_KEY]);
        let flipped = false;
        try {
            await openDashboardTab(page);
            const first = await answeredAfter(calls, 0, isFirstOpening, 'the tab never asked the first-opening question');
            if (first.answer.base_share_of_portfolio === null) throw new Error('The Dashboard answer has no base share (net worth at or below zero): the percentage cannot be compared. Check backend/test_scripts/test_db/populate_mock_data.py.');
            const amount = page.getByTestId(`${DASH}-tiles-base-amount`);
            const share = page.getByTestId(`${DASH}-tiles-base-share`);
            /** The share box reads «42.5 % of the portfolio (€ 1,000)»: the percentage and its words come before the amount, which is the part privacy masks. */
            const shareLead = async () => ((await share.innerText()).split('(')[0] ?? '').trim();

            const amountOpen = (await amount.innerText()).trim();
            expect(amountOpen, 'precondition: the base amount shows digits with privacy off').toMatch(/\d/);
            expect(amountOpen).not.toContain(PRIVACY_PLACEHOLDER);
            const leadOpen = await shareLead();
            expect(leadOpen, 'precondition: the base share shows a percentage').toMatch(/%/);
            expect(leadOpen).toMatch(/\d/);

            await flipPrivacy(page, true);
            flipped = true;
            await expect(amount, 'the base amount is not masked').toContainText(PRIVACY_PLACEHOLDER);
            await expect(amount, 'the masked base amount still shows digits').not.toHaveText(/\d/);
            await expect(share, 'the amount inside the share box is not masked').toContainText(PRIVACY_PLACEHOLDER);
            await expect.poll(shareLead, {message: 'the percentage changed with privacy: it is not an amount', timeout: PAGE_TIMEOUT}).toBe(leadOpen);

            await flipPrivacy(page, false);
            flipped = false;
            await expect(amount).not.toContainText(PRIVACY_PLACEHOLDER);
            await expect(amount, 'the base amount did not come back as it was').toHaveText(amountOpen);
            await expect.poll(shareLead).toBe(leadOpen);
        } finally {
            if (flipped) await flipPrivacy(page, false).catch(() => undefined);
            await cleanUp(page, [keys.dashboard, PRIVACY_STORAGE_KEY]);
        }
    });
});
