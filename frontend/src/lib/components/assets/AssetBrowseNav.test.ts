// @vitest-environment jsdom
/**
 * AssetBrowseNav — the `‹ n/N ›` buttons in the asset detail header (workstream K, step 16 item 2),
 * pinned red-first.
 *
 * Decisions (developer, 06/10): buttons only, no keyboard shortcut. They follow "the list I left";
 * with no list to follow (direct link, Dashboard, Transactions, reload, or an asset missing from the
 * published list) they follow ALL assets in the list page's default order. Prev/next REPLACE the
 * current history entry, so "Back" returns to the list. Disabled at the edges (no wrap-around),
 * hidden under 2 assets.
 *
 * The contract:
 *   - root `asset-browse` publishes `data-state="pending|ready|none"` and `data-source="list|default"`
 *     (absent or empty until decided);
 *   - the order is decided in an `afterNavigate` callback: coming from another asset
 *     (`/(app)/assets/[id]`) with an order already chosen that holds the new asset → keep it; coming
 *     from the list (`/(app)/assets`) with the asset in `getAssetListOrder()` → that order (`list`);
 *     anything else (a sideways move off the kept order included) → `defaultAssetBrowseOrder` over
 *     `list_assets_api_v1_assets_query_get({queries: {}})` (`default`). A failed fetch, a position
 *     not found or a total under 2 → `none`, no nav;
 *   - a component that mounts after its navigation ended (`$navigating` null on mount: a direct
 *     entry, whose page the `(app)` layout shows late) gets no callback, so it follows the default
 *     order on mount; a `from: null` call arriving after that decision fetches nothing more;
 *   - `ready` renders `asset-browse-nav` (a `<nav>` with an aria-label) holding the buttons
 *     `asset-browse-prev` / `asset-browse-next` (aria-label and title, disabled at the edges) and
 *     `asset-browse-position` (`{index+1}/{total}`);
 *   - a click calls `expectReplaceNavigation(url)` and THEN `goto(url, {replaceState: true,
 *     keepFocus: true})`, where `url = '/assets/' + targetId + window.location.search`: the live
 *     query, not `$page.url`'s, because the page rewrites its dates with `history.replaceState`.
 *
 * The harness plays SvelteKit 2.50.1: `afterNavigate` is a spy that keeps the component's callback.
 * `showPage()` puts `$page` and jsdom's live URL on the same page, as any SvelteKit navigation does.
 * `mountOn()` mounts during a client-side navigation (`$navigating` set, `$page` and the props
 * already on the destination); `arrive()` then runs the callback with a navigation shaped like
 * SvelteKit's and clears `$navigating`, in SvelteKit's order. `mountLate()` mounts after the
 * navigation ended: `$navigating` null, and no callback unless a test calls `arrive()`.
 * `./assetBrowse` is the real module: the list order is published the way the list page publishes it.
 *
 * Nothing reads translated text: the labels (`assetDetail.browse.*`) are only required non-empty,
 * and the position is digits and a slash, read with its whitespace removed.
 */
import {afterEach, beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';
import {tick} from 'svelte';
import {get} from 'svelte/store';

const mocks = await vi.hoisted(async () => {
    const {writable} = await import('svelte/store');
    return {
        goto: vi.fn(() => Promise.resolve()),
        afterNavigate: vi.fn(),
        expectReplaceNavigation: vi.fn(),
        listAssets: vi.fn(),
        page: writable<Record<string, unknown>>({}),
        /** `$navigating`: non-null while a client-side navigation is in flight, null otherwise. */
        navigating: writable<Record<string, unknown> | null>(null),
    };
});

// The aliased no-op mocks keep every other export; only what the component drives is replaced.
vi.mock('$app/navigation', async (importOriginal) => ({
    ...(await importOriginal<typeof import('$app/navigation')>()),
    goto: mocks.goto,
    afterNavigate: mocks.afterNavigate,
}));
vi.mock('$app/stores', async (importOriginal) => ({
    ...(await importOriginal<typeof import('$app/stores')>()),
    page: mocks.page,
    navigating: mocks.navigating,
}));
vi.mock('$lib/api', () => ({
    zodiosApi: {list_assets_api_v1_assets_query_get: mocks.listAssets},
    ApiError: class ApiError extends Error {},
}));
vi.mock('$lib/stores/app/navigationStore', async (importOriginal) => ({
    ...(await importOriginal<typeof import('$lib/stores/app/navigationStore')>()),
    expectReplaceNavigation: mocks.expectReplaceNavigation,
}));

import {cleanup, fireEvent, render, screen, setupI18n, waitFor, within} from '$test/component';
import {publishAssetListOrder, resetAssetBrowse} from './assetBrowse';
import AssetBrowseNav from './AssetBrowseNav.svelte';

const ORIGIN = 'http://librefolio.test';
/** The detail page's own query: the date range must survive every step. */
const QUERY = '?start=2026-01-01&end=2026-03-31';
const DETAIL_ROUTE = '/(app)/assets/[id]';
const REPLACE = {replaceState: true, keepFocus: true};

/**
 * What `list_assets_api_v1_assets_query_get` answers, in API order. The list page's default view
 * shows the actives by panel — own [3], others [4], analysis [1, 5] — so the default order is
 * [3, 4, 1, 5]; with the inactive 2 open it is [3, 2, 4, 1, 5].
 */
const API_ASSETS = [
    {id: 1, display_name: 'Synthetic analysis A', currency: 'EUR', active: true, tx_count: 0, tx_count_own: 0},
    {id: 2, display_name: 'Synthetic own, inactive', currency: 'EUR', active: false, tx_count: 3, tx_count_own: 3},
    {id: 3, display_name: 'Synthetic own', currency: 'EUR', active: true, tx_count: 5, tx_count_own: 2},
    {id: 4, display_name: 'Synthetic others', currency: 'EUR', active: true, tx_count: 4, tx_count_own: 0},
    {id: 5, display_name: 'Synthetic analysis B', currency: 'USD', active: true},
];

/** Where the navigation came from: a route id and its URL, or `null` for a direct link / reload. */
type Origin = {route: string; url: string} | null;
const FROM_LIST: Origin = {route: '/(app)/assets', url: `/assets${QUERY}`};
const FROM_DASHBOARD: Origin = {route: '/(app)/dashboard', url: '/dashboard'};
const DIRECT: Origin = null;
const fromAsset = (id: number): Origin => ({route: DETAIL_ROUTE, url: `/assets/${id}${QUERY}`});

/** The `$page` value of the detail page showing `assetId`. */
function detailPage(assetId: number, search = QUERY): Record<string, unknown> {
    return {url: new URL(`/assets/${assetId}${search}`, ORIGIN), params: {id: String(assetId)}, route: {id: DETAIL_ROUTE}, status: 200, error: null, data: {assetId}, form: null, state: {}};
}

/**
 * Show the detail page of `assetId` as both SvelteKit and the browser see it after a SvelteKit
 * navigation: `$page` and jsdom's live URL agree. They part ways only when the page rewrites its
 * dates with `history.replaceState` (`replaceHistoryDateRange`), which SvelteKit does not track.
 */
function showPage(assetId: number, search = QUERY): void {
    mocks.page.set(detailPage(assetId, search));
    window.history.replaceState(null, '', `/assets/${assetId}${search}`);
}

/**
 * What `$navigating` holds while SvelteKit mounts the page of a client-side navigation: it is set
 * when the navigation starts and reset to null only after the afterNavigate callbacks ran
 * (`@sveltejs/kit` 2.50.1, `runtime/client/client.js` :1565 and :1815). Only its being non-null is
 * read here: the page being left reaches the component through `arrive()`.
 */
function inFlightTo(assetId: number, search = QUERY): Record<string, unknown> {
    return {
        from: {route: {id: null}, url: new URL('/', ORIGIN), params: {}},
        to: {route: {id: DETAIL_ROUTE}, url: new URL(`/assets/${assetId}${search}`, ORIGIN), params: {id: String(assetId)}},
        type: 'goto',
        willUnload: false,
        complete: Promise.resolve(),
    };
}

/**
 * Mount the buttons on the detail page of `assetId` during a client-side navigation, as SvelteKit
 * does: `$page` already shows it and `$navigating` is still set. The callback comes with `arrive()`.
 */
function mountOn(assetId: number, search = QUERY) {
    showPage(assetId, search);
    mocks.navigating.set(inFlightTo(assetId, search));
    return render(AssetBrowseNav, {assetId});
}

/**
 * Mount the buttons after their navigation ended, as on a direct entry (page load, reload): the
 * `(app)` layout shows the page only once i18n, the session and the bootstrap are ready, so SvelteKit
 * already ran the afterNavigate callbacks (hydration, `client.js` :615) before this one was
 * registered. `$navigating` is null and nothing will call the callback.
 */
function mountLate(assetId: number) {
    showPage(assetId);
    mocks.navigating.set(null);
    return render(AssetBrowseNav, {assetId});
}

/**
 * Run the `afterNavigate` callback the component registered, as SvelteKit does once the navigation
 * that shows `assetId` has completed, then clear `$navigating` as SvelteKit does right after. A list
 * → detail click is a `goto`, so is prev/next; a Dashboard link is a `link`; a direct link or a
 * reload is `enter`, with no `from`.
 */
async function arrive(origin: Origin, assetId: number, type: 'enter' | 'link' | 'goto' = origin ? 'goto' : 'enter'): Promise<void> {
    const callback = mocks.afterNavigate.mock.calls.at(-1)?.[0];
    if (typeof callback !== 'function') throw new Error('AssetBrowseNav registered no afterNavigate callback: it would never decide which order to follow');
    callback({
        from: origin ? {route: {id: origin.route}, url: new URL(origin.url, ORIGIN), params: {}} : null,
        to: {route: {id: DETAIL_ROUTE}, url: new URL(`/assets/${assetId}${QUERY}`, ORIGIN), params: {id: String(assetId)}},
        type,
        willUnload: false,
        complete: Promise.resolve(),
    });
    mocks.navigating.set(null);
    await tick();
}

const root = () => screen.getByTestId('asset-browse');

/** `asset-browse-position` as digits and a slash: whitespace is formatting, not contract. */
function position(): string {
    return (screen.getByTestId('asset-browse-position').textContent ?? '').replace(/\s+/g, '');
}

async function ready(): Promise<void> {
    await waitFor(() => expect(root()).toHaveAttribute('data-state', 'ready'));
}

beforeAll(async () => {
    await setupI18n();
});

beforeEach(() => {
    resetAssetBrowse();
    mocks.navigating.set(null);
    window.history.replaceState(null, '', '/');
    mocks.goto.mockClear();
    mocks.afterNavigate.mockReset();
    mocks.expectReplaceNavigation.mockReset();
    mocks.listAssets.mockReset();
    mocks.listAssets.mockResolvedValue(API_ASSETS);
});

afterEach(() => {
    cleanup();
});

describe('AssetBrowseNav — before it knows where the user came from', () => {
    it('is pending, with no source and no buttons, until its afterNavigate callback runs', async () => {
        publishAssetListOrder('grid', [{id: 'own', ids: [10, 20, 30]}]);
        mountOn(20);
        await tick();

        expect(mocks.afterNavigate).toHaveBeenCalledWith(expect.any(Function));
        expect(root()).toHaveAttribute('data-state', 'pending');
        expect(root().getAttribute('data-source') ?? '').toBe('');
        expect(screen.queryByTestId('asset-browse-nav')).toBeNull();
        expect(mocks.listAssets).not.toHaveBeenCalled();
    });
});

describe('AssetBrowseNav — arriving from the list', () => {
    beforeEach(() => {
        // Two grid panels, concatenated by the module: [10, 20, 30].
        publishAssetListOrder('grid', [
            {id: 'own', ids: [10, 20]},
            {id: 'analysis', ids: [30]},
        ]);
    });

    it('follows the published order: n/N, both directions open in the middle, nothing fetched', async () => {
        mountOn(20);
        await arrive(FROM_LIST, 20);
        await ready();

        expect(root()).toHaveAttribute('data-source', 'list');
        const nav = screen.getByTestId('asset-browse-nav');
        expect(nav.tagName).toBe('NAV');
        expect(nav).toHaveAttribute('aria-label', expect.stringMatching(/\S/));
        expect(within(nav).getByTestId('asset-browse-position')).toBeInTheDocument();
        expect(position()).toBe('2/3');
        for (const testId of ['asset-browse-prev', 'asset-browse-next']) {
            const button = within(nav).getByTestId(testId);
            expect(button.tagName).toBe('BUTTON');
            expect(button).toBeEnabled();
            expect(button).toHaveAttribute('aria-label', expect.stringMatching(/\S/));
            expect(button).toHaveAttribute('title', expect.stringMatching(/\S/));
        }
        expect(mocks.listAssets).not.toHaveBeenCalled();
    });

    it('next replaces the history entry with the following asset, keeping the query', async () => {
        mountOn(20);
        await arrive(FROM_LIST, 20);
        await ready();

        await fireEvent.click(screen.getByTestId('asset-browse-next'));

        const url = `/assets/30${QUERY}`;
        expect(mocks.expectReplaceNavigation).toHaveBeenCalledTimes(1);
        expect(mocks.expectReplaceNavigation).toHaveBeenCalledWith(url);
        expect(mocks.goto).toHaveBeenCalledTimes(1);
        expect(mocks.goto).toHaveBeenCalledWith(url, REPLACE);
        // Armed first: the back stack must already expect the replace when the navigation is tracked.
        expect(mocks.expectReplaceNavigation.mock.invocationCallOrder[0]).toBeLessThan(mocks.goto.mock.invocationCallOrder[0]);
    });

    it('previous goes to the asset before, the same way', async () => {
        mountOn(20);
        await arrive(FROM_LIST, 20);
        await ready();

        await fireEvent.click(screen.getByTestId('asset-browse-prev'));

        expect(mocks.expectReplaceNavigation).toHaveBeenCalledWith(`/assets/10${QUERY}`);
        expect(mocks.goto).toHaveBeenCalledWith(`/assets/10${QUERY}`, REPLACE);
        expect(mocks.expectReplaceNavigation.mock.invocationCallOrder[0]).toBeLessThan(mocks.goto.mock.invocationCallOrder[0]);
    });

    it('builds the bare asset path when the page has no query', async () => {
        mountOn(20, '');
        await arrive(FROM_LIST, 20);
        await ready();

        await fireEvent.click(screen.getByTestId('asset-browse-next'));

        expect(mocks.goto).toHaveBeenCalledWith('/assets/30', REPLACE);
    });

    it('disables previous on the first asset: no wrap-around', async () => {
        mountOn(10);
        await arrive(FROM_LIST, 10);
        await ready();

        expect(position()).toBe('1/3');
        expect(screen.getByTestId('asset-browse-prev')).toBeDisabled();
        expect(screen.getByTestId('asset-browse-next')).toBeEnabled();
    });

    it('disables next on the last asset: no wrap-around', async () => {
        mountOn(30);
        await arrive(FROM_LIST, 30);
        await ready();

        expect(position()).toBe('3/3');
        expect(screen.getByTestId('asset-browse-next')).toBeDisabled();
        expect(screen.getByTestId('asset-browse-prev')).toBeEnabled();
    });
});

describe('AssetBrowseNav — a move carries the live query', () => {
    // The detail page rewrites `?start&end` with `history.replaceState` (`replaceHistoryDateRange`,
    // `src/lib/utils/url/dateRangeUrl.ts`), which SvelteKit does not track: `$page.url` keeps the
    // query of the last SvelteKit navigation. A move built from it puts the OLD dates back in the
    // address bar, and a reload then seeds the date store with them.
    beforeEach(() => {
        publishAssetListOrder('grid', [{id: 'own', ids: [10, 20, 30]}]);
    });

    it('a move carries the query the page rewrote with history.replaceState, not the one $page still holds', async () => {
        mountOn(20);
        await arrive(FROM_LIST, 20);
        await ready();

        // As `replaceHistoryDateRange` does after a date-range change.
        window.history.replaceState(null, '', '/assets/20?start=2025-01-01&end=2026-06-30');
        // Precondition: the two have parted, $page still holds the old dates.
        expect((get(mocks.page).url as URL).search).toBe(QUERY);

        await fireEvent.click(screen.getByTestId('asset-browse-next'));

        const url = '/assets/30?start=2025-01-01&end=2026-06-30';
        expect(mocks.goto).toHaveBeenCalledWith(url, REPLACE);
        expect(mocks.expectReplaceNavigation).toHaveBeenCalledWith(url);
    });

    it('carries every parameter of the live query, not only the dates', async () => {
        // The Risk tab was opened through SvelteKit (`tab=risk` in both), then the dates changed.
        mountOn(20, `${QUERY}&tab=risk`);
        await arrive(FROM_LIST, 20);
        await ready();
        window.history.replaceState(null, '', '/assets/20?start=2025-01-01&end=2026-06-30&tab=risk');

        await fireEvent.click(screen.getByTestId('asset-browse-prev'));

        const url = '/assets/10?start=2025-01-01&end=2026-06-30&tab=risk';
        expect(mocks.goto).toHaveBeenCalledWith(url, REPLACE);
        expect(mocks.expectReplaceNavigation).toHaveBeenCalledWith(url);
    });
});

describe('AssetBrowseNav — no list to follow: the default order', () => {
    it('follows the default order fetched from the API after a direct link or a reload', async () => {
        mountOn(1);
        await arrive(DIRECT, 1);
        await ready();

        expect(mocks.listAssets).toHaveBeenCalledTimes(1);
        expect(mocks.listAssets).toHaveBeenCalledWith({queries: {}});
        expect(root()).toHaveAttribute('data-source', 'default');
        // [3, 4, 1, 5]: 1 is third, between 4 and 5.
        expect(position()).toBe('3/4');

        await fireEvent.click(screen.getByTestId('asset-browse-next'));
        await fireEvent.click(screen.getByTestId('asset-browse-prev'));
        expect(mocks.goto.mock.calls).toEqual([
            [`/assets/5${QUERY}`, REPLACE],
            [`/assets/4${QUERY}`, REPLACE],
        ]);
    });

    it('does the same from the Dashboard, with the inactive assets when the open one is inactive', async () => {
        mountOn(2);
        await arrive(FROM_DASHBOARD, 2, 'link');
        await ready();

        expect(root()).toHaveAttribute('data-source', 'default');
        // [3, 2, 4, 1, 5]: the list with its "inactive" toggle on.
        expect(position()).toBe('2/5');

        await fireEvent.click(screen.getByTestId('asset-browse-next'));
        await fireEvent.click(screen.getByTestId('asset-browse-prev'));
        expect(mocks.goto.mock.calls).toEqual([
            [`/assets/4${QUERY}`, REPLACE],
            [`/assets/3${QUERY}`, REPLACE],
        ]);
    });

    it('falls back to it when the asset is missing from the list it came from', async () => {
        publishAssetListOrder('grid', [{id: 'own', ids: [10, 20, 30]}]);
        mountOn(4);
        await arrive(FROM_LIST, 4);
        await ready();

        expect(mocks.listAssets).toHaveBeenCalledTimes(1);
        expect(root()).toHaveAttribute('data-source', 'default');
        expect(position()).toBe('2/4');
    });

    it('stays pending, with no buttons, while the default order is loading', async () => {
        let answer: (items: unknown) => void = () => {};
        mocks.listAssets.mockReturnValue(new Promise((resolve) => (answer = resolve)));
        mountOn(1);
        await arrive(FROM_DASHBOARD, 1, 'link');

        // Barrier: the fetch is in flight, so "pending" is a state, not a component that never started.
        expect(mocks.listAssets).toHaveBeenCalledTimes(1);
        expect(root()).toHaveAttribute('data-state', 'pending');
        expect(screen.queryByTestId('asset-browse-nav')).toBeNull();

        answer(API_ASSETS);
        await ready();
        expect(position()).toBe('3/4');
    });

    it('shows no buttons when the default order cannot be fetched', async () => {
        mocks.listAssets.mockRejectedValue(new Error('synthetic: network down'));
        mountOn(1);
        await arrive(DIRECT, 1);

        await waitFor(() => expect(root()).toHaveAttribute('data-state', 'none'));
        expect(mocks.listAssets).toHaveBeenCalledTimes(1);
        expect(screen.queryByTestId('asset-browse-nav')).toBeNull();
    });
});

describe('AssetBrowseNav — fewer than two assets to browse', () => {
    it('shows no buttons for a published list of one', async () => {
        publishAssetListOrder('grid', [{id: 'own', ids: [20]}]);
        mountOn(20);
        await arrive(FROM_LIST, 20);

        await waitFor(() => expect(root()).toHaveAttribute('data-state', 'none'));
        expect(screen.queryByTestId('asset-browse-nav')).toBeNull();
    });

    it('shows no buttons when the default order holds only the open asset', async () => {
        mocks.listAssets.mockResolvedValue([{id: 7, display_name: 'Synthetic only asset', currency: 'EUR', active: true, tx_count: 0, tx_count_own: 0}]);
        mountOn(7);
        await arrive(DIRECT, 7);

        await waitFor(() => expect(root()).toHaveAttribute('data-state', 'none'));
        expect(mocks.listAssets).toHaveBeenCalledTimes(1);
        expect(screen.queryByTestId('asset-browse-nav')).toBeNull();
    });

    it('shows no buttons for an asset the default order does not hold', async () => {
        mountOn(99);
        await arrive(DIRECT, 99);

        await waitFor(() => expect(root()).toHaveAttribute('data-state', 'none'));
        expect(mocks.listAssets).toHaveBeenCalledTimes(1);
        expect(screen.queryByTestId('asset-browse-nav')).toBeNull();
    });
});

describe('AssetBrowseNav — moving between assets', () => {
    it('keeps the list order on a sideways move, without fetching', async () => {
        publishAssetListOrder('grid', [
            {id: 'own', ids: [10, 20]},
            {id: 'analysis', ids: [30]},
        ]);
        const {rerender} = mountOn(20);
        await arrive(FROM_LIST, 20);
        await ready();
        expect(position()).toBe('2/3');

        // Next was clicked. SvelteKit keeps the page component on a same-route move: the navigation
        // starts, the page store and the props change, then afterNavigate runs, coming from the
        // previous asset.
        mocks.navigating.set(inFlightTo(30));
        showPage(30);
        await rerender({assetId: 30});
        await arrive(fromAsset(20), 30);

        await waitFor(() => expect(position()).toBe('3/3'));
        expect(root()).toHaveAttribute('data-state', 'ready');
        expect(root()).toHaveAttribute('data-source', 'list');
        expect(screen.getByTestId('asset-browse-next')).toBeDisabled();
        expect(mocks.listAssets).not.toHaveBeenCalled();

        await fireEvent.click(screen.getByTestId('asset-browse-prev'));
        expect(mocks.goto).toHaveBeenLastCalledWith(`/assets/20${QUERY}`, REPLACE);
    });

    it('follows the default order when a sideways move lands on an asset the kept order does not hold', async () => {
        publishAssetListOrder('grid', [{id: 'own', ids: [10, 20, 30]}]);
        const {rerender} = mountOn(20);
        await arrive(FROM_LIST, 20);
        await ready();
        expect(root()).toHaveAttribute('data-source', 'list');

        // Not prev/next: another link of the detail page (the Risk tab's `navigate_asset`, a goto that
        // pushes) opens asset 4, which the list the user left does not hold.
        mocks.navigating.set(inFlightTo(4));
        showPage(4);
        await rerender({assetId: 4});
        await arrive(fromAsset(20), 4);

        await ready();
        expect(root()).toHaveAttribute('data-source', 'default');
        // The default order [3, 4, 1, 5]: 4 is second.
        expect(position()).toBe('2/4');
        expect(mocks.listAssets).toHaveBeenCalledTimes(1);
    });

    it('keeps the default order on a sideways move, without fetching it again', async () => {
        const {rerender} = mountOn(1);
        await arrive(FROM_DASHBOARD, 1, 'link');
        await ready();
        expect(position()).toBe('3/4');

        mocks.navigating.set(inFlightTo(5));
        showPage(5);
        await rerender({assetId: 5});
        await arrive(fromAsset(1), 5);

        await waitFor(() => expect(position()).toBe('4/4'));
        expect(root()).toHaveAttribute('data-source', 'default');
        expect(mocks.listAssets).toHaveBeenCalledTimes(1);
    });
});

describe('AssetBrowseNav — mounted after its navigation ended (direct entry)', () => {
    // The E2E defect: on a page load or a reload of /assets/{id} the buttons stayed `pending` for
    // ever. SvelteKit only REGISTERS an afterNavigate callback on mount and CALLS the registered ones
    // when a navigation ends or at hydration; the (app) layout mounts the detail page after both, so
    // nothing calls this one. `$navigating` is null then, while during a client-side navigation it is
    // set throughout the mount (see `mountOn` / `mountLate`).

    it('decides on mount when it appears after its navigation ended (the app layout shows the page once the session is checked)', async () => {
        mountLate(1);

        await ready();
        expect(root()).toHaveAttribute('data-source', 'default');
        expect(mocks.listAssets).toHaveBeenCalledTimes(1);
        expect(mocks.listAssets).toHaveBeenCalledWith({queries: {}});
        // The default order [3, 4, 1, 5]: 1 is third.
        expect(position()).toBe('3/4');
    });

    it('a late hydration call does not fetch twice', async () => {
        mountLate(1);
        // A page that mounts in time still gets SvelteKit's hydration call (`from: null`, `enter`),
        // right after its mount: by then the order is being fetched, and must not be fetched again.
        await arrive(DIRECT, 1, 'enter');

        await ready();
        expect(root()).toHaveAttribute('data-source', 'default');
        expect(mocks.listAssets).toHaveBeenCalledTimes(1);
        expect(position()).toBe('3/4');
    });

    it('shows no buttons when the late-mount fetch fails', async () => {
        mocks.listAssets.mockRejectedValue(new Error('synthetic: network down'));
        mountLate(1);

        await waitFor(() => expect(root()).toHaveAttribute('data-state', 'none'));
        expect(mocks.listAssets).toHaveBeenCalledTimes(1);
        expect(screen.queryByTestId('asset-browse-nav')).toBeNull();
    });
});
