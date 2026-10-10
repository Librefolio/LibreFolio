/**
 * Gallery, inventory group 3 — Danske Bank report sets: the accounts the shots run as, the data
 * those accounts own, and the walk through the import wizard the shots stand on. Also the gallery-wide
 * filter that keeps those temporary data out of every other shot ({@link hideGalleryTempData}).
 *
 * ## Isolation
 *
 * The gallery runs `mode: 'parallel'` and photographs whole pages, so nothing a group-3 shot needs
 * may show up in another shot. So each test signs up its own account ({@link registerGalleryAccount}),
 * takes it through the welcome with every guide skipped ({@link onboardGalleryAccount}), and lets it
 * own its broker and its uploads; afterEach deletes the account with everything it owns
 * ({@link cleanupGalleryAccount}): its BRIM files, its brokers (forced), itself.
 *
 * Owning is not enough on two surfaces, which are wider than one account by design: a superuser's
 * Files page lists every BRIM file of the lane (`GET /brokers/import/files` with no `broker_ids`), and
 * every session caches every broker's name (`GET /brokers?include_inaccessible=true`), which /brokers
 * shows under "Other existing brokers". So every broker the gallery creates carries a mark in its name
 * ({@link galleryBrokerName}), and every gallery test, from its outer beforeEach, filters out of those
 * two responses the marked brokers its session cannot reach and their files. Seeded data carries no
 * mark and is never touched; an account's own broker is reachable, so its own shots keep it.
 *
 * Nothing is ever committed. The wizard stops on its own steps — the review's Import only asks
 * `POST /brokers/import/gap-fix`, which writes nothing (brim_gap_fix.py) — and the bulk editor is
 * closed through its discard guard. A parse writes no transaction either: it moves the file and
 * caches its result in the file's own metadata, which goes with the file.
 *
 * Data: the repository's synthetic Danske Bank samples (invented values), one statement written
 * under the test's output folder (the savings statement of the todo-banner shot), and nothing else.
 * Copied, not imported, from transactions/tx-import-report-set.spec.ts and
 * transactions/tx-bulk-import-handoff.spec.ts.
 *
 * ## Offline, gallery-wide
 *
 * The same outer beforeEach installs {@link guardGalleryOffline} on every page: no gallery scenario reaches a real
 * price or exchange-rate provider, or writes a price. The section of that name below lists every endpoint of the API
 * client that would, and what the gallery answers instead (galleryOfflineData.ts). Nor does any scenario reach a
 * third-party host — the PDF viewer's CDN, Google Fonts —: the gallery must work without the network.
 *
 * ## Favicon images, gallery-wide
 *
 * Those routes have a side effect in Playwright: with any route registered, an image whose URL ends in `/favicon.ico`
 * is aborted before a handler runs — every broker logo drawn from its portal, most import plugins' icons, the FED and
 * SNB icons. So the same beforeEach also installs {@link keepFaviconImagesLoading}, which keeps them loading.
 */

import type {APIResponse, Route, TestInfo} from '@playwright/test';
import {expect, type APIRequestContext, type Locator, type Page} from './playwright';
import {waitForParseVerdict, waitForSettled} from './app-events';
import {OFFLINE_CURRENT_PRICES, OFFLINE_FX_PROVIDERS, type OfflineCurrentPrice} from './galleryOfflineData';
import {deleteDisposableUser, prepareOnboardingAccount, type DisposableUser} from './onboarding-accounts';
import {uniqueToken} from './unique';
import {randomUUID} from 'crypto';
import {mkdirSync, readFileSync, writeFileSync} from 'fs';
import path from 'path';
import {fileURLToPath} from 'url';

const API = '/api/v1';
const BROKERS_PATH = `${API}/brokers`;
const UPLOAD_PATH = `${API}/brokers/import/upload`;
const FILES_PATH = `${API}/brokers/import/files`;
const PREVIEW_PATH = `${API}/brokers/import/sets/preview`;
const COMBINE_PATH = `${API}/brokers/import/sets/combine`;
/** Every parse the wizard asks for: a single file's, or a set's combined file's. */
const PARSE_PATH = /^\/api\/v1\/brokers\/import\/files\/[^/]+\/parse$/;
const SAMPLES = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../../backend/app/services/brim_providers/sample_reports');

export const DANSKE = 'broker_danske_bank';
export const GENERIC = 'broker_generic_csv';

/** The repository's synthetic Danske Bank exports: the main set, and the set with a gap. */
export const DANSKE_SAMPLES = {
    custody: path.join(SAMPLES, 'danske_bank-custody.xlsx'),
    cash: path.join(SAMPLES, 'danske_bank-cash.csv'),
    gapCustody1: path.join(SAMPLES, 'danske_bank-gap-custody-1.xlsx'),
    gapCustody2: path.join(SAMPLES, 'danske_bank-gap-custody-2.xlsx'),
    gapCash: path.join(SAMPLES, 'danske_bank-gap-cash.csv'),
} as const;

/**
 * The truth points of the gap set (backend test_brim_danske_bank.py, TestGapSampleFacts): the
 * starting point on the eve of the first custody export, the point after the gap on the eve of the
 * second, and the end-of-period check on the last day of the second.
 */
export const GAP_POINTS = {opening: '2020-08-31', gap: '2021-01-04', verification: '2021-02-26'} as const;

// ---------------------------------------------------------------------------
// Shapes
// ---------------------------------------------------------------------------

/** A disposable account and what it owns: the brokers are recorded as soon as they exist. */
export type GalleryAccount = {user: DisposableUser; token: string; brokerIds: number[]};

/** A BRIM file as the upload, the list and the combine answer it (`BRIMFileInfo`), reduced to what is read here. */
export type StoredFile = {
    file_id: string;
    filename: string;
    uploaded_at: string;
    target_broker_id: number | null;
    batch_id?: string | null;
    compatible_plugins?: string[] | null;
    kind?: string | null;
    combined_into?: string[] | null;
};

/** A parse response (`BRIMParseResponse`), reduced to what is read here. */
export type ParsedFile = {
    file_id: string;
    plugin_code: string;
    transactions: Array<{description?: string | null}>;
    warnings?: unknown[];
    field_todos?: Array<{tx_index: number; field: string; severity: string; reason_code: string; message: string}>;
};

/** A todo added to the parse of the row whose description is `description`. */
export type InjectedTodo = {description: string; field: string; severity: 'warning' | 'blocker'; reason_code: string; message: string};

/** What a statement writer needs of the test: its output folder. */
type OutputFolder = Pick<TestInfo, 'outputPath'>;

// ---------------------------------------------------------------------------
// The account
// ---------------------------------------------------------------------------

/**
 * Sign up a fresh account. Its name is visible in the shots — the sidebar, the "Uploaded by"
 * column — so it is short and neutral: `demo_` and a random token. Randomness, not time, is what
 * keeps two workers apart; six base-36 characters are ~2·10⁹ names.
 */
export async function registerGalleryAccount(request: APIRequestContext): Promise<GalleryAccount> {
    const token = uniqueToken(6);
    const username = `demo_${token.toLowerCase()}`;
    const user = {username, email: `${username}@example.com`, password: `Demo9!_${token}${uniqueToken(4)}`};
    const response = await request.post(`${API}/auth/register`, {data: user});
    expect(response.status(), `the gallery signs up a disposable account, so registration must be enabled (HTTP ${response.status()} ${await response.text()})`).toBe(201);
    const created = (await response.json()) as {user: {id: number}};
    return {user: {...user, id: created.user.id}, token, brokerIds: []};
}

/**
 * Sign in, finish the welcome with its defaults, close the intro scene, and skip every guide: no
 * Welcome page and no overlay can sit over a shot. Read back by `skipDueFlowsExcept`, not assumed.
 */
export async function onboardGalleryAccount(page: Page, account: GalleryAccount): Promise<void> {
    await prepareOnboardingAccount(page, account.user, []);
}

/** The mark of a broker the gallery creates: ` · ` (U+00B7) and the owning account's token, six of A–Z 0–9. */
const GALLERY_BROKER_NAME = /^.+ \u00B7 [A-Z0-9]{6}$/;

/**
 * The name of every broker a gallery test creates: `‹label› · ‹TOKEN›`. The token is the owning
 * account's ({@link registerGalleryAccount}), which also keeps the name unique — `brokers.name` is
 * uniquely indexed. The mark is what {@link hideGalleryTempData} hides from other sessions: no seeded
 * broker has a `·` in its name.
 */
export function galleryBrokerName(label: string, token: string): string {
    const name = `${label} \u00B7 ${token}`;
    if (!isGalleryTempBrokerName(name)) throw new Error(`"${name}" would not carry the gallery's broker mark: the label must not be empty, the token must be six of A-Z 0-9`);
    return name;
}

/** Whether `name` is the name of a broker the gallery created ({@link galleryBrokerName}). */
export function isGalleryTempBrokerName(name: unknown): boolean {
    return typeof name === 'string' && GALLERY_BROKER_NAME.test(name);
}

/**
 * A broker of the account, named {@link galleryBrokerName}`(label, token)` and recorded for cleanup
 * before anything is checked.
 *
 * Precondition, read rather than assumed: a new broker carries no BRIM file. The lane's files
 * outlive a database repopulate made without `--clean`, so a broker id reused from an earlier run
 * could bring that run's leftovers along — and they would be in every shot of this broker.
 */
export async function createGalleryBroker(api: APIRequestContext, account: GalleryAccount, label: string, extra: Record<string, unknown> = {}): Promise<number> {
    const name = galleryBrokerName(label, account.token);
    const response = await api.post(`${API}/brokers`, {data: [{name, allow_cash_overdraft: true, ...extra}]});
    expect(response.ok(), `create the broker "${name}": HTTP ${response.status()} ${await response.text()}`).toBe(true);
    const {results} = (await response.json()) as {results: Array<{name: string; success: boolean; broker_id: number | null; message?: string}>};
    const created = results.find((result) => result.name === name);
    if (!created?.success || typeof created.broker_id !== 'number') throw new Error(`The broker "${name}" was not created: ${JSON.stringify(results)}`);
    account.brokerIds.push(created.broker_id);
    const leftovers = await brimFilesOn(api, created.broker_id);
    expect(
        leftovers.map((file) => file.filename),
        `broker ${created.broker_id} is new and must hold no BRIM file: these belong to an earlier run on a reused broker id (the gallery's populate --clean removes them)`,
    ).toEqual([]);
    return created.broker_id;
}

/**
 * Delete what the account owns, then the account: its BRIM files (uploads and combined files —
 * every file of a broker the test created, which held none when it was created, so all of them are
 * the test's; the forced broker delete would drop them anyway), its brokers, forced, and itself.
 *
 * The page leaves first, so the wizard does not react while its files go away. The request
 * context signs in as the account: it has its own cookie jar, so the page's session is untouched.
 */
export async function cleanupGalleryAccount(page: Page, request: APIRequestContext, account: GalleryAccount): Promise<void> {
    if (!page.isClosed()) {
        await page.unrouteAll({behavior: 'ignoreErrors'}).catch(() => undefined);
        await page.goto('about:blank').catch(() => undefined);
    }
    const failures: string[] = [];
    try {
        const signedIn = await request.post(`${API}/auth/login`, {data: {username: account.user.username, password: account.user.password}});
        if (!signedIn.ok()) {
            failures.push(`sign in as ${account.user.username}: HTTP ${signedIn.status()}`);
        } else {
            for (const brokerId of account.brokerIds) {
                for (const file of await brimFilesOn(request, brokerId)) {
                    const deleted = await request.delete(`${FILES_PATH}/${file.file_id}`);
                    if (!deleted.ok()) failures.push(`BRIM file ${file.filename} (${file.file_id}): HTTP ${deleted.status()}`);
                }
            }
        }
    } catch (error) {
        failures.push(String(error));
    }
    // The brokers (a forced delete also drops any file still on them), then the account itself.
    await deleteDisposableUser(request, account.user, account.brokerIds);
    expect(failures, `cleanup deletes every BRIM file of ${account.user.username}'s brokers`).toEqual([]);
}

/**
 * Hide, from this page's session, the brokers the gallery created that the session cannot reach, and
 * their files. Two `page.route` handlers, on the exact paths and for GET only — anything else falls
 * back untouched:
 *
 * - `GET /api/v1/brokers` (any query): the marked items of `inaccessible` are dropped. That list feeds
 *   every session's broker cache, hence "Other existing brokers" on /brokers.
 * - `GET /api/v1/brokers/import/files` (any query): the files of the marked brokers the session cannot
 *   reach are dropped — a superuser lists every file of the lane when it names no broker. The marked
 *   ids come from the session's own unfiltered `GET /brokers?include_inaccessible=true`, asked through
 *   `page.request` (same cookies; API requests are not routed).
 *
 * Only marked names are hidden, and only out of reach: seeded data is never touched, and an account
 * keeps its own broker and files. When nothing is hidden the original answer goes on as it came;
 * otherwise only the list changes — status, headers and every other field are passed on.
 *
 * Installed by the gallery's outer beforeEach, before any sign-in; routes registered later by a test
 * run first, and take precedence only on the URLs they match.
 */
export async function hideGalleryTempData(page: Page): Promise<void> {
    await page.route(
        (url) => url.pathname === BROKERS_PATH,
        async (route) => {
            if (route.request().method() !== 'GET') return route.fallback();
            const response = await route.fetch();
            const body = await jsonOf(response);
            if (!response.ok() || body === null || typeof body !== 'object' || !Array.isArray((body as {inaccessible?: unknown}).inaccessible)) return route.fulfill({response});
            const listing = body as {inaccessible: Array<{name?: unknown}>};
            const kept = listing.inaccessible.filter((item) => !isGalleryTempBrokerName(item?.name));
            if (kept.length === listing.inaccessible.length) return route.fulfill({response});
            await fulfillWith(route, response, {...listing, inaccessible: kept});
        },
    );
    await page.route(
        (url) => url.pathname === FILES_PATH,
        async (route) => {
            if (route.request().method() !== 'GET') return route.fallback();
            const response = await route.fetch();
            const files = await jsonOf(response);
            if (!response.ok() || !Array.isArray(files) || files.length === 0) return route.fulfill({response});
            const hidden = await galleryBrokersOutOfReach(page);
            const kept = files.filter((file: {target_broker_id?: unknown}) => !hidden.has(file?.target_broker_id as number));
            if (kept.length === files.length) return route.fulfill({response});
            await fulfillWith(route, response, kept);
        },
    );
}

/** The ids of the brokers the gallery created that this page's session cannot reach. */
async function galleryBrokersOutOfReach(page: Page): Promise<Set<number>> {
    const response = await page.request.get(`${BROKERS_PATH}?include_inaccessible=true`);
    const body = await jsonOf(response);
    if (!response.ok() || body === null || typeof body !== 'object') return new Set();
    const inaccessible = (body as {inaccessible?: Array<{id?: unknown; name?: unknown}>}).inaccessible ?? [];
    return new Set(inaccessible.filter((item) => isGalleryTempBrokerName(item?.name) && typeof item?.id === 'number').map((item) => item.id as number));
}

/** A response's JSON body, or null when it has none. */
async function jsonOf(response: APIResponse): Promise<unknown> {
    try {
        return await response.json();
    } catch {
        return null;
    }
}

/**
 * Answer `route` with the status and headers of `response` and a new JSON body. The headers that
 * described the original body — its length, its compression (the backend gzips bodies from 1 KiB),
 * its chunking — no longer describe this one, so they are left for the new body to set.
 */
async function fulfillWith(route: Route, response: APIResponse, json: unknown): Promise<void> {
    const stale = new Set(['content-length', 'content-encoding', 'transfer-encoding']);
    const headers = Object.fromEntries(Object.entries(response.headers()).filter(([name]) => !stale.has(name.toLowerCase())));
    await route.fulfill({response, headers, json});
}

/**
 * Keep {@link hideGalleryTempData} working for a page served under another name of the lane: a name Chromium maps onto the
 * loopback (`--host-resolver-rules`), where the lane's backend answers — the connection-security shot's LAN name.
 *
 * The gallery's routes match a path or a third-party host, never the baseURL's origin, so such a page is guarded and
 * filtered as on the baseURL. But the two listings hideGalleryTempData filters are fetched in Node (`route.fetch()`), and
 * Node resolves names without Chromium's rules: under the other name the fetch fails (`getaddrinfo ENOTFOUND`), and the
 * page's request with it. So a GET of either listing under `alias` goes on to hideGalleryTempData with the same path and
 * query under `lane`, the baseURL's origin, which Node reaches; the page receives the filtered listing under its own name.
 * Node sends the cookies of `lane`, and the gallery's own reads (`page.request`) go to the baseURL too: the same user must
 * be signed in there first — read back here. Nothing else under `alias` is touched.
 *
 * Registered by the test, after the outer beforeEach: it runs before hideGalleryTempData.
 */
export async function keepTempDataHiddenUnder(page: Page, alias: string, lane: string): Promise<void> {
    const aliasOrigin = new URL(alias).origin;
    const laneOrigin = new URL(lane).origin;
    const me = await page.request.get(`${laneOrigin}${API}/auth/me`);
    expect(me.ok(), `precondition: the reads made in Node go to ${laneOrigin}, where this page's user must be signed in (GET ${API}/auth/me answered HTTP ${me.status()})`).toBe(true);
    await page.route(
        (url) => url.origin === aliasOrigin && (url.pathname === BROKERS_PATH || url.pathname === FILES_PATH),
        async (route) => {
            if (route.request().method() !== 'GET') return route.fallback();
            const {pathname, search} = new URL(route.request().url());
            await route.fallback({url: `${laneOrigin}${pathname}${search}`});
        },
    );
}

// ---------------------------------------------------------------------------
// Offline: no scenario reaches a real provider
// ---------------------------------------------------------------------------

/**
 * Every endpoint of the API client (src/lib/api/generated.ts) whose backend reaches a provider, as the gallery
 * answers it. The backend's providers fetch over the network — yfinance, JustETF, the CSS scraper, ECB, SNB, FED,
 * BOE — and most of these calls also write what they fetched into the test database.
 *
 * Pressed on purpose only — aborted, recorded in `syncs`, and a red at the end of the test (no scenario presses one):
 * - `POST /api/v1/assets/prices/sync` — a price history sync: fetches, and writes prices and events;
 * - `POST /api/v1/assets/provider/refresh` — a metadata refresh: fetches, and writes the asset's classification;
 * - `POST /api/v1/assets/provider/probe` — a provider dry run (Test configuration, Ask the provider): fetches;
 * - `POST /api/v1/fx/currencies/sync` — an exchange-rate sync: fetches, and writes rates.
 *
 * Asked by a page on its own — answered here, never by the backend:
 * - `POST /api/v1/assets/prices/current` — the Assets pages' live-price poll (on load, then every 30 s while the
 *   period ends today; the detail page also merges a tick into its chart): it asks each asset's provider, and writes
 *   today's candle. Answered from {@link OFFLINE_CURRENT_PRICES}, dated today, only for the requested assets the
 *   fixture names; aborted instead while `livePrices` is `'abort'` (the risk lab, galleryRiskLab.ts).
 * - `GET /api/v1/fx/providers` — the exchange-rate provider catalogue: the backend asks ECB and SNB for their
 *   currencies. The FX page, its Add pair and provider modals and the About tab show it, so it is answered from
 *   {@link OFFLINE_FX_PROVIDERS} (the `providers` filter applied as the backend applies it).
 * - `GET /api/v1/assets/provider/search` and `…/search/stream` — a search across the providers (and the web link
 *   finder), which the asset modal runs by itself when the import wizard opens it pre-filled. Answered as the backend
 *   answers when no provider can be reached: one error per provider asked, no result.
 *
 * And outside the backend: an admin's browser asks GitHub for the latest release on load (updateCheck.ts) — aborted,
 * so no update prompt can depend on the day the gallery runs.
 *
 * And third-party hosts the gallery must never need ({@link THIRD_PARTY_HOSTS}) — aborted, recorded in `thirdParty`,
 * and a red at the end of the test: the gallery must work without the network, PDF preview included. The PDF viewer
 * (EmbedPDF) asks jsDelivr for its engine, its stamps and its fallback fonts, and Google Fonts for its UI fonts, unless
 * the app serves them itself (developer's decision, release 2 batch 7: it must). Its engine runs in a worker, whose
 * requests the page's routes see and abort as well.
 */
export interface GalleryOfflineGuard {
    /** How the live-price poll is answered: from the fixture (the default), or aborted. */
    livePrices: 'fixture' | 'abort';
    /** Live-price polls the page sent, answered or aborted. */
    livePolls: number;
    /** Live-price polls answered from the fixture: the counter {@link expectOfflinePricesDrawn} reads as a delta. */
    pricedPolls: number;
    /** The fixture's prices by asset id, once the first poll has matched them to the database (empty until then). */
    pricedAssets: ReadonlyMap<number, OfflineCurrentPrice>;
    /** Provider catalogue reads, answered from the fixture. */
    catalogueReads: number;
    /** Searches across the providers, answered as offline. */
    searches: number;
    /** GitHub requests (the admin's release probe), aborted. */
    releaseProbes: number;
    /** Syncs, metadata refreshes and provider probes attempted, by method and path: aborted, each one a red. */
    syncs: string[];
    /** Requests to a third-party host the gallery must never need ({@link THIRD_PARTY_HOSTS}), by method and URL: aborted, each one a red. */
    thirdParty: string[];
    /** What the guard could not answer as designed (a fixture asset not in the database, a request it cannot read): each one a red. */
    problems: string[];
}

const LIVE_PRICES = `${API}/assets/prices/current`;
const PROVIDER_CATALOGUE = `${API}/fx/providers`;
const PROVIDER_SEARCH = `${API}/assets/provider/search`;
const PROVIDER_SEARCH_STREAM = `${API}/assets/provider/search/stream`;
const PROVIDER_CALLS = new Set([`${API}/assets/prices/sync`, `${API}/assets/provider/refresh`, `${API}/assets/provider/probe`, `${API}/fx/currencies/sync`]);
/** What each provider reports, as the search stream does for a provider that raised (asset_sources/search.py). */
const OFFLINE_SEARCH_ERROR = 'provider not reached: the gallery runs offline';

/**
 * Hosts no gallery page may reach: jsDelivr (the PDF viewer's engine — pdfium's WASM —, its stamps, its fallback fonts)
 * and Google Fonts (fonts.googleapis.com, the stylesheets of the viewer's UI and signature fonts; fonts.gstatic.com,
 * their files). Nothing else in the app asks them (checked on the built bundle, b7). Exact names, never a suffix: the
 * favicons the gallery shows come from each broker's own site, and Google's favicon service — one import plugin's icon —
 * answers from www.google.com and t*.gstatic.com, not fonts.gstatic.com.
 */
const THIRD_PARTY_HOSTS = new Set(['cdn.jsdelivr.net', 'fonts.googleapis.com', 'fonts.gstatic.com']);

const offlineGuards = new WeakMap<Page, GalleryOfflineGuard>();

/** Today, in the runner's local time — the day the backend dates a fresh quote (`date.today()`). */
function localDay(now = new Date()): string {
    return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;
}

/** The provider codes a search names, as the backend reads them: repeated or comma-separated. */
function searchedProviders(url: URL): string[] {
    return url.searchParams
        .getAll('providers')
        .flatMap((value) => value.split(','))
        .map((code) => code.trim())
        .filter((code) => code !== '');
}

/**
 * The fixture's prices by asset id. The ids are looked up by display name in the database the page reads
 * (`GET /assets/query`, through the page's own session), never assumed; a name that does not match exactly one asset
 * is a problem, and its price is not served.
 */
async function offlinePricesById(page: Page, guard: GalleryOfflineGuard): Promise<Map<number, OfflineCurrentPrice>> {
    const byId = new Map<number, OfflineCurrentPrice>();
    const response = await page.request.get(`${API}/assets/query`);
    const assets = await jsonOf(response);
    if (!response.ok() || !Array.isArray(assets)) {
        guard.problems.push(`GET ${API}/assets/query answered HTTP ${response.status()}: no fixture price can be matched to its asset`);
        return byId;
    }
    for (const price of OFFLINE_CURRENT_PRICES) {
        const matches = assets.filter((asset: {display_name?: unknown}) => asset?.display_name === price.displayName);
        const id = matches.length === 1 ? (matches[0] as {id?: unknown}).id : null;
        if (typeof id !== 'number') {
            guard.problems.push(`the fixture's "${price.displayName}" names ${matches.length} assets, expected one: check populate_mock_data.py`);
            continue;
        }
        byId.set(id, price);
    }
    return byId;
}

/**
 * Keep every page of the test from reaching a provider ({@link GalleryOfflineGuard} says what is answered, and how).
 * Installed by the gallery's outer beforeEach, before any sign-in; a test reads it with {@link galleryOfflineGuard},
 * and the outer afterEach fails the test on any sync or problem it recorded ({@link expectGalleryOffline}).
 */
export async function guardGalleryOffline(page: Page): Promise<GalleryOfflineGuard> {
    const guard: GalleryOfflineGuard = {livePrices: 'fixture', livePolls: 0, pricedPolls: 0, pricedAssets: new Map(), catalogueReads: 0, searches: 0, releaseProbes: 0, syncs: [], thirdParty: [], problems: []};
    offlineGuards.set(page, guard);
    let pricesById: Promise<Map<number, OfflineCurrentPrice>> | null = null;

    await page.route(
        (url) => PROVIDER_CALLS.has(url.pathname),
        async (route) => {
            guard.syncs.push(`${route.request().method()} ${new URL(route.request().url()).pathname}`);
            await route.abort();
        },
    );
    await page.route(
        (url) => url.pathname === LIVE_PRICES,
        async (route) => {
            if (route.request().method() !== 'POST') return route.fallback();
            guard.livePolls += 1;
            if (guard.livePrices === 'abort') return route.abort();
            let requested: unknown = null;
            try {
                requested = route.request().postDataJSON();
            } catch {
                /* not JSON: told apart below */
            }
            if (!Array.isArray(requested) || !requested.every((id) => Number.isInteger(id))) {
                guard.problems.push(`a live-price poll asked ${JSON.stringify(requested)}, not a list of asset ids: aborted`);
                return route.abort();
            }
            pricesById ??= offlinePricesById(page, guard);
            let known: Map<number, OfflineCurrentPrice>;
            try {
                known = await pricesById;
            } catch (error) {
                guard.problems.push(`the fixture prices could not be matched to their assets (${String(error)}): the poll was aborted`);
                return route.abort();
            }
            guard.pricedAssets = known;
            const asOf = localDay();
            const results = (requested as number[]).flatMap((assetId) => {
                const price = known.get(assetId);
                return price ? [{asset_id: assetId, value: price.value, currency: price.currency, as_of_date: asOf, source: price.source, error: null}] : [];
            });
            await route.fulfill({json: {results, success_count: results.length, errors: []}});
            guard.pricedPolls += 1;
        },
    );
    await page.route(
        (url) => url.pathname === PROVIDER_CATALOGUE,
        async (route) => {
            if (route.request().method() !== 'GET') return route.fallback();
            guard.catalogueReads += 1;
            const filter = new Set(searchedProviders(new URL(route.request().url())).map((code) => code.toUpperCase()));
            await route.fulfill({json: OFFLINE_FX_PROVIDERS.filter((provider) => filter.size === 0 || filter.has(provider.code.toUpperCase()))});
        },
    );
    await page.route(
        (url) => url.pathname === PROVIDER_SEARCH || url.pathname === PROVIDER_SEARCH_STREAM,
        async (route) => {
            if (route.request().method() !== 'GET') return route.fallback();
            guard.searches += 1;
            const url = new URL(route.request().url());
            const codes = searchedProviders(url);
            if (url.pathname === PROVIDER_SEARCH) {
                await route.fulfill({json: {query: url.searchParams.get('q') ?? '', total_results: 0, results: [], providers_queried: codes, providers_with_errors: codes}});
                return;
            }
            const events = [...codes.map((code) => ({event: 'provider_error', provider_code: code, error: OFFLINE_SEARCH_ERROR})), {event: 'done', total_results: 0, providers_queried: codes, providers_with_errors: codes}];
            await route.fulfill({status: 200, contentType: 'text/event-stream', body: events.map((event) => `data: ${JSON.stringify(event)}\n\n`).join('')});
        },
    );
    await page.route(
        (url) => url.hostname === 'api.github.com',
        async (route) => {
            guard.releaseProbes += 1;
            await route.abort();
        },
    );
    // The gallery must work without the network, PDF preview included: a request to a third-party host is aborted, and
    // fails the test at its end (expectGalleryOffline). A worker's requests too — the PDF viewer's engine runs in a module
    // worker made from a blob, and page.route sees and aborts what such a worker asks (checked in Playwright 1.61).
    await page.route(
        (url) => THIRD_PARTY_HOSTS.has(url.hostname),
        async (route) => {
            guard.thirdParty.push(`${route.request().method()} ${route.request().url()}`);
            await route.abort();
        },
    );
    return guard;
}

/** The offline guard of `page`, installed by the gallery's outer beforeEach. */
export function galleryOfflineGuard(page: Page): GalleryOfflineGuard {
    const guard = offlineGuards.get(page);
    if (!guard) throw new Error("the gallery's offline guard is not installed on this page: the outer beforeEach installs it (guardGalleryOffline)");
    return guard;
}

/**
 * The Assets list's live prices for its latest load, answered from the fixture and drawn. The poll is outside the page's
 * `data-busy` — it never holds the list back — so a list settled on `data-busy="false"` may still show the fixture's
 * assets without a price. Waits for a poll answered after `since` (`pricedPolls`, read before the load), then for every
 * card of a fixture asset on the page to show its figure, which the card prints with two decimals. Call it while the
 * cards stand still — before a search filters some away; in the table view, where no card is drawn, only the poll is
 * waited for (the rows print the figure in the language's format).
 */
export async function expectOfflinePricesDrawn(page: Page, since: number): Promise<void> {
    const guard = galleryOfflineGuard(page);
    await expect.poll(() => guard.pricedPolls, {message: 'no live-price poll of this load of the Assets page was answered from the fixture', timeout: 20_000}).toBeGreaterThan(since);
    for (const [assetId, price] of guard.pricedAssets) {
        const card = page.getByTestId(`asset-card-${assetId}`);
        // The cards are drawn before the poll leaves (it asks for the ids of the loaded list): absent now is absent from this view.
        if ((await card.count()) === 0) continue;
        await expect(card, `the card of "${price.displayName}" does not show its fixture price`).toContainText(Number(price.value).toFixed(2));
    }
}

/** Nothing tried to sync, refresh or probe, nothing asked a third-party host, and every call the guard answered was answered as designed. */
export function expectGalleryOffline(page: Page): void {
    const guard = galleryOfflineGuard(page);
    expect(guard.syncs, 'a sync, a metadata refresh or a provider probe was started: the gallery never presses one (it was aborted, nothing reached a provider)').toEqual([]);
    expect(guard.thirdParty, 'a page asked a third-party host (it was aborted): the gallery must work without the network, PDF preview included').toEqual([]);
    expect(guard.problems, "the gallery's offline guard could not answer as designed").toEqual([]);
}

// ---------------------------------------------------------------------------
// Favicon images: kept loading while routes are installed
// ---------------------------------------------------------------------------

/** The query the gallery gives an image URL that ends in `/favicon.ico`. */
const FAVICON_MARK = 'lf-gallery';

/**
 * Keep every image whose URL ends in `/favicon.ico` loading, although the gallery has routes installed.
 *
 * Playwright 1.61 takes any request whose URL ends in `/favicon.ico` for the page's own favicon (playwright-core,
 * `coreBundle.js`: `_isFavicon`), and once a route is registered — on the page or its context, whatever it matches —
 * it aborts that request before a single handler runs (`requestStarted`). The outer beforeEach registers routes on every
 * gallery page (hideGalleryTempData, guardGalleryOffline), so every such <img> failed and drew its fallback: the
 * brokers' logos — `BrokerIcon` falls back to the portal's origin + /favicon.ico (brokerIconChain.svelte.ts,
 * brokerHelpers.ts) — most import plugins' icons, and the FED and SNB provider icons. The published 1.1 gallery,
 * taken with no route installed, shows the logos.
 *
 * So the page writes those URLs with a query, `…/favicon.ico?lf-gallery`: Playwright no longer takes it for the
 * favicon, and every host involved answers it with the same bytes. Only the URL written into an image changes — through
 * the `src` property, `setAttribute('src', …)`, and the `src` attributes of HTML set through `innerHTML` (`{@html}`,
 * raw-HTML table cells, Svelte's own templates) — so each is the same live image from the same host, and no product code
 * is touched. A URL that does not end in /favicon.ico (BOE's `favicon.svg?ver=…`) is left alone; the fragment, if any,
 * stays last, and a URL whose query ends in /favicon.ico gets `&lf-gallery` instead.
 *
 * An init script applies from the next document on, so the outer beforeEach installs it before the first navigation.
 * {@link expectFaviconImagesLoading} checks it is in force at the end of each test.
 */
export async function keepFaviconImagesLoading(page: Page): Promise<void> {
    await page.addInitScript((mark: string) => {
        const marked = (url: string): string => {
            const hash = url.indexOf('#');
            const head = hash < 0 ? url : url.slice(0, hash);
            if (!/\/favicon\.ico$/i.test(head)) return url;
            return `${head}${head.includes('?') ? '&' : '?'}${mark}${url.slice(head.length)}`;
        };
        const src = Object.getOwnPropertyDescriptor(HTMLImageElement.prototype, 'src');
        if (src?.get && src.set) {
            const {get, set} = src;
            Object.defineProperty(HTMLImageElement.prototype, 'src', {
                configurable: true,
                enumerable: src.enumerable,
                get() {
                    return get.call(this);
                },
                set(value: unknown) {
                    set.call(this, marked(String(value)));
                },
            });
        }
        const setAttribute = Element.prototype.setAttribute;
        Element.prototype.setAttribute = function (name: string, value: string): void {
            setAttribute.call(this, name, this instanceof HTMLImageElement && String(name).toLowerCase() === 'src' ? marked(String(value)) : value);
        };
        // Only the value of a `src` attribute: a text, or a link, that names /favicon.ico is not an image the page loads.
        const SRC_ATTRIBUTE = /(\bsrc\s*=\s*)(?:"([^"]*)"|'([^']*)'|([^\s"'>]+))/gi;
        const innerHTML = Object.getOwnPropertyDescriptor(Element.prototype, 'innerHTML');
        if (innerHTML?.get && innerHTML.set) {
            const {get, set} = innerHTML;
            Object.defineProperty(Element.prototype, 'innerHTML', {
                configurable: true,
                enumerable: innerHTML.enumerable,
                get() {
                    return get.call(this);
                },
                set(value: unknown) {
                    const html =
                        typeof value === 'string'
                            ? value.replace(SRC_ATTRIBUTE, (_all: string, lead: string, double?: string, single?: string, bare?: string) => (double !== undefined ? `${lead}"${marked(double)}"` : single !== undefined ? `${lead}'${marked(single)}'` : `${lead}${marked(bare ?? '')}`))
                            : value;
                    set.call(this, html);
                },
            });
        }
    }, FAVICON_MARK);
}

/**
 * {@link keepFaviconImagesLoading} is in force in the page's current document: an image given a URL ending in
 * /favicon.ico holds it with the gallery's query, set through `setAttribute` and through the `src` property. The
 * images belong to a document of their own, which has no window, so nothing loads. A page still on about:blank never
 * loaded a document for the script to run in; a closed page has none.
 */
export async function expectFaviconImagesLoading(page: Page): Promise<void> {
    if (page.isClosed() || page.url() === 'about:blank') return;
    const probe = 'https://x.test/favicon.ico';
    await expect
        .poll(
            // A document being replaced has no context to evaluate in: read again, the poll does not retry a throw.
            () =>
                page
                    .evaluate((url) => {
                        const inert = document.implementation.createHTMLDocument('');
                        const byAttribute = inert.createElement('img');
                        byAttribute.setAttribute('src', url);
                        const byProperty = inert.createElement('img');
                        byProperty.src = url;
                        return [byAttribute.getAttribute('src'), byProperty.getAttribute('src')];
                    }, probe)
                    .catch((error: Error) => [`unreadable: ${error.message}`]),
            {message: 'the favicon images fix is not in force on this page: keepFaviconImagesLoading must run before the first navigation', timeout: 5_000},
        )
        .toEqual([`${probe}?${FAVICON_MARK}`, `${probe}?${FAVICON_MARK}`]);
}

// ---------------------------------------------------------------------------
// The files
// ---------------------------------------------------------------------------

/** The BRIM files stored on one broker; the list also returns legacy files with no broker, so the target is filtered. */
export async function brimFilesOn(api: APIRequestContext, brokerId: number): Promise<StoredFile[]> {
    const response = await api.get(`${FILES_PATH}?broker_ids=${brokerId}`);
    expect(response.ok(), `list the BRIM files of broker ${brokerId}: HTTP ${response.status()}`).toBe(true);
    return ((await response.json()) as StoredFile[]).filter((file) => file.target_broker_id === brokerId);
}

/** The BRIM files the account's Files page lists: the same request, with no `broker_ids` — legacy files with no broker included. */
export async function brimFilesListed(api: APIRequestContext): Promise<StoredFile[]> {
    const response = await api.get(FILES_PATH);
    expect(response.ok(), `list the BRIM files as the Files page does: HTTP ${response.status()}`).toBe(true);
    return (await response.json()) as StoredFile[];
}

/** Upload one file, as the wizard sends it (multipart); in `batchId` when given — the files of one batch are one report set. */
export async function uploadFile(api: APIRequestContext, brokerId: number, filePath: string, batchId?: string): Promise<StoredFile> {
    const name = path.basename(filePath);
    const mimeType = name.endsWith('.xlsx') ? 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' : 'text/csv';
    const multipart: Record<string, string | {name: string; mimeType: string; buffer: Buffer}> = {broker_id: String(brokerId), file: {name, mimeType, buffer: readFileSync(filePath)}};
    if (batchId) multipart.batch_id = batchId;
    const response = await api.post(UPLOAD_PATH, {multipart});
    const body = await response.text();
    expect(response.status(), `upload ${name} to broker ${brokerId}: ${body}`).toBe(200);
    const stored = JSON.parse(body) as StoredFile;
    expect(stored, `${name} is stored on broker ${brokerId}`).toMatchObject({filename: name, target_broker_id: brokerId, ...(batchId ? {batch_id: batchId} : {})});
    return stored;
}

/** Upload `files` together, in the order given: one upload batch, which is one report set. */
export async function uploadSet(api: APIRequestContext, brokerId: number, files: readonly string[]): Promise<{batchId: string; files: StoredFile[]}> {
    const batchId = randomUUID();
    const stored: StoredFile[] = [];
    for (const file of files) stored.push(await uploadFile(api, brokerId, file, batchId));
    return {batchId, files: stored};
}

/** The preview of one Danske set (read-only): its members, what it misses and for which period. */
export async function previewSet(api: APIRequestContext, brokerId: number, batchId: string): Promise<{complete: boolean; missing: Array<{role: string; start?: string | null; end?: string | null}>}> {
    const response = await api.post(PREVIEW_PATH, {data: {broker_id: brokerId, plugin_code: DANSKE, batch_id: batchId}});
    const body = await response.text();
    expect(response.status(), `preview batch ${batchId}: ${body}`).toBe(200);
    return JSON.parse(body) as {complete: boolean; missing: Array<{role: string; start?: string | null; end?: string | null}>};
}

/** Combine one complete Danske set into its combined file, as the analysis does first. */
export async function combineSet(api: APIRequestContext, brokerId: number, batchId: string): Promise<StoredFile> {
    const response = await api.post(COMBINE_PATH, {data: {broker_id: brokerId, plugin_code: DANSKE, batch_id: batchId}});
    const body = await response.text();
    expect(response.status(), `combine batch ${batchId}: ${body}`).toBe(200);
    const combined = (JSON.parse(body) as {combined: StoredFile}).combined;
    expect(combined.kind, 'the combine answers with the combined file').toBe('combined');
    return combined;
}

/** The savings statement of the todo-banner shot: cash movements only (no asset, nothing to resolve), invented. */
export const SAVINGS_ROWS = [
    {date: '2024-01-05', type: 'DEPOSIT', amount: '1500.00', description: 'Savings plan January'},
    {date: '2024-02-05', type: 'DEPOSIT', amount: '1500.00', description: 'Savings plan February'},
    {date: '2024-02-20', type: 'WITHDRAWAL', amount: '-400.00', description: 'Transfer to current account'},
    {date: '2024-03-05', type: 'DEPOSIT', amount: '1500.00', description: 'Savings plan March'},
    {date: '2024-04-05', type: 'DEPOSIT', amount: '1500.00', description: 'Savings plan April'},
    {date: '2024-04-18', type: 'WITHDRAWAL', amount: '-650.00', description: 'Transfer to holiday account'},
] as const;

/**
 * Two fields to verify, added to the parse of the savings statement. The generic CSV raises no todo on
 * plain cash rows, so they are injected (the recipe of F1-D4, tx-bulk-import-handoff.spec.ts). Both
 * are warnings on fields the corrections step does not own (fixRowLifecycle.ts: no dup-relevant
 * blocker, no `asset_id`, no `split_hint`), so they travel to the bulk editor untouched. Messages are
 * a plugin's text, shown as they are in every language.
 */
export const SAVINGS_TODOS: readonly InjectedTodo[] = [
    {description: 'Transfer to current account', field: 'cash', severity: 'warning', reason_code: 'gallery_amount_sign', message: 'Amount sign inferred from the movement type: check it against your statement.'},
    {description: 'Savings plan April', field: 'date', severity: 'warning', reason_code: 'gallery_value_date', message: 'No value date in the file: the booking date was used.'},
];

/** Write the savings statement in the generic CSV's format, under a fixed name (the output folder is per test). */
export function writeSavingsStatement(testInfo: OutputFolder): string {
    const filePath = testInfo.outputPath('savings-account-2024.csv');
    mkdirSync(path.dirname(filePath), {recursive: true});
    writeFileSync(filePath, 'date,type,quantity,amount,currency,asset,description\n' + SAVINGS_ROWS.map((row) => `${row.date},${row.type},0,${row.amount},EUR,,${row.description}`).join('\n') + '\n');
    return filePath;
}

/**
 * Add `todos` to every parse response of this page, each on the row its description names, from now
 * until `stop()`. Returns the descriptions that found their row, so the premise can be read back.
 */
export async function injectTodosIntoParses(page: Page, todos: readonly InjectedTodo[]): Promise<{injected: Set<string>; stop: () => Promise<void>}> {
    const injected = new Set<string>();
    const matches = (url: URL) => PARSE_PATH.test(url.pathname);
    const handler = async (route: Route) => {
        const response = await route.fetch();
        if (!response.ok()) {
            await route.fulfill({response});
            return;
        }
        const body = (await response.json()) as ParsedFile;
        const added = todos.flatMap(({description, ...todo}) => {
            const txIndex = body.transactions.findIndex((tx) => tx.description === description);
            if (txIndex < 0) return [];
            injected.add(description);
            return [{tx_index: txIndex, ...todo}];
        });
        // A new body, so not the original headers: their content-length is the old body's.
        await route.fulfill({status: response.status(), contentType: 'application/json', body: JSON.stringify({...body, field_todos: [...(body.field_todos ?? []), ...added]})});
    };
    await page.route(matches, handler);
    return {injected, stop: () => page.unroute(matches, handler)};
}

// ---------------------------------------------------------------------------
// The wizard
// ---------------------------------------------------------------------------

export function currentStep(page: Page): Locator {
    return page.getByTestId('import-wizard-stepper').locator('[aria-current="step"]');
}

/**
 * Open the wizard from the Transactions toolbar and go on to Select Files with nothing to upload:
 * step 2 reads the account's files again, as a user who uploaded earlier sees them. Ends settled —
 * the files listed and every set's preview in (`data-busy`).
 */
export async function openWizardOnSelectFiles(page: Page): Promise<Locator> {
    await page.getByTestId('tx-import-button').click();
    await expect(page.getByTestId('import-wizard-stepper')).toBeVisible({timeout: 10_000});
    const step1 = page.getByTestId('import-wizard-step1');
    await expect(step1).toBeVisible({timeout: 10_000});
    await waitForSettled(step1, 15_000);
    await page.getByTestId('import-wizard-next').click();
    const step2 = page.getByTestId('import-wizard-step2');
    await expect(step2, 'Next with nothing to upload goes on to Select Files').toBeVisible({timeout: 15_000});
    await waitForSettled(step2, 30_000);
    return step2;
}

/** The broker's panel in Select Files, open: asked first, the end state asserted (a toggle). */
export async function openBrokerPanel(page: Page, brokerId: number): Promise<Locator> {
    const panel = page.getByTestId(`import-wizard-broker-files-${brokerId}`);
    await expect(panel, `broker ${brokerId} has files listed in Select Files`).toBeVisible({timeout: 15_000});
    const toggle = panel.getByTestId(`import-wizard-broker-toggle-${brokerId}`);
    if ((await toggle.getAttribute('aria-expanded')) !== 'true') await toggle.click();
    await expect(toggle).toHaveAttribute('aria-expanded', 'true');
    return panel;
}

/** The card of one Danske set, by its key: broker, plugin and upload batch (`reportSetKey`). */
export function reportSetCard(page: Page, brokerId: number, batchId: string): Locator {
    return page.getByTestId('import-wizard-step2').locator(`[data-testid="report-set-card"][data-set-key="set:${brokerId}:${DANSKE}:${batchId}"]`);
}

/** The row of one file in the table of its role, inside a set's card. */
export function roleRow(card: Locator, role: string, fileId: string): Locator {
    return card.locator(`[data-testid="report-set-role-table"][data-role="${role}"] tbody tr[data-row-id="${fileId}"]`);
}

/**
 * Tick a set whole, as it is right after its upload. A reopened wizard ticks nothing, and nothing
 * else here touches a tick: from 'none' one click ticks every member. The state is asked first and
 * the end state asserted (a toggle); 'some' would mean another hand ticked part of it.
 */
export async function tickWholeSet(card: Locator): Promise<void> {
    await expect(card, 'the set has its preview').toHaveAttribute('data-set-status', /^(complete|incomplete)$/, {timeout: 20_000});
    await expect(card, 'a reopened wizard selects nothing, and nothing else ticks the set').toHaveAttribute('data-selected', /^(none|all)$/);
    if ((await card.getAttribute('data-selected')) !== 'all') await card.getByTestId('report-set-select').click();
    await expect(card, 'the set is ticked whole').toHaveAttribute('data-selected', 'all', {timeout: 5_000});
}

/**
 * Open a set's card: whether it is open is asked, never assumed (a toggle), and the end state asserted.
 * The toggle is clicked, as a user taps it, on every viewport: a toggle the header leaves no box to
 * click is a product defect, and it fails here, loudly, rather than being opened some other way.
 */
export async function unfoldCard(card: Locator): Promise<void> {
    const toggle = card.getByTestId('report-set-toggle');
    if ((await toggle.getAttribute('aria-expanded')) !== 'true') await toggle.click();
    await expect(toggle).toHaveAttribute('aria-expanded', 'true');
}

/** Scroll the wizard's content (or the page) so `target` starts at the top of what is shown. */
export async function scrollToTop(target: Locator): Promise<void> {
    await target.evaluate((element) => element.scrollIntoView({block: 'start', inline: 'nearest'}));
}

/**
 * Click Parse and return the parse response, captured on the wire as it goes out: a single file's,
 * or — for a set — its combined file's, after the combine. Ends on a usable verdict: every row of
 * the analysis read (`data-parse-state="ok"`).
 */
export async function parseSelection(page: Page): Promise<ParsedFile> {
    const parse = page.getByTestId('import-wizard-parse');
    await expect(parse, 'the selection can be analysed').toBeEnabled({timeout: 10_000});
    const [response] = await Promise.all([page.waitForResponse((candidate) => candidate.request().method() === 'POST' && PARSE_PATH.test(new URL(candidate.url()).pathname), {timeout: 60_000}), parse.click()]);
    const body = await response.text();
    expect(response.status(), `parse: ${body}`).toBe(200);
    const step3 = page.getByTestId('import-wizard-step3');
    await expect(step3).toBeVisible({timeout: 15_000});
    await waitForParseVerdict(page, 60_000);
    await expect(step3, 'the analysis read every row of the selection').toHaveAttribute('data-parse-state', 'ok');
    return JSON.parse(body) as ParsedFile;
}

/** The steps the wizard may cross between the analysis and the review. */
const LATER_STEP = /^(assets|fix|duplicates|review)$/;

/**
 * From the analysis to the review, through whichever conditional steps the wizard opens. The parse
 * response says whether leaving the analysis asks to confirm its notices; the stepper says where the
 * wizard is. Open unification proposals are confirmed and the corrections kept as read — the
 * plugin's own reading, the one decision always available. Nothing of it is saved anywhere.
 */
export async function walkToReview(page: Page, parsed: ParsedFile): Promise<Locator> {
    const marker = currentStep(page);
    await expect(marker, 'the walk starts on the analysis').toHaveAttribute('data-step-id', 'analyze');
    await page.getByTestId('import-wizard-continue').click();
    if ((parsed.warnings ?? []).length > 0) {
        const confirm = page.getByTestId('import-wizard-warning-confirm');
        await expect(confirm, 'the parse raised notices: leaving the analysis asks to confirm them').toBeVisible({timeout: 10_000});
        await confirm.click();
        await expect(confirm).toBeHidden({timeout: 10_000});
    }
    for (let hop = 0; hop < 4; hop++) {
        await expect(marker, 'the wizard goes on to a step after the analysis').toHaveAttribute('data-step-id', LATER_STEP, {timeout: 30_000});
        const stepId = (await marker.getAttribute('data-step-id')) ?? '';
        if (stepId === 'review') break;
        if (stepId === 'assets') {
            const assets = page.getByTestId('import-wizard-step-assets');
            await expect(assets.getByTestId('asset-group-step')).toBeVisible({timeout: 10_000});
            // The cards render together with the step, so the count read here is final.
            const proposed = assets.locator('[data-testid^="asset-group-grp-"][data-state="proposed"]');
            const open = await proposed.count();
            if (open >= 2) await assets.getByTestId('asset-group-confirm-all').click();
            else if (open === 1) await proposed.getByTestId(/^asset-group-confirm-grp-/).click();
            await expect(proposed, 'every unification proposal is settled').toHaveCount(0, {timeout: 10_000});
        }
        if (stepId === 'fix') {
            const fix = page.getByTestId('import-wizard-step-fix');
            await fix.getByTestId('fix-step-accept-all').click();
            await expect(fix.locator('[data-testid="fix-step-row"][data-decision="pending"]'), 'every flagged row is kept as read').toHaveCount(0, {timeout: 10_000});
        }
        const advance = page.getByTestId(`import-wizard-${stepId}-continue`);
        await expect(advance, `the ${stepId} step lets the import go on`).toBeEnabled({timeout: 30_000});
        await advance.click();
        await expect(marker, `the wizard leaves the ${stepId} step`).not.toHaveAttribute('data-step-id', stepId, {timeout: 30_000});
    }
    await expect(marker, 'the wizard reaches the review').toHaveAttribute('data-step-id', 'review', {timeout: 30_000});
    const step4 = page.getByTestId('import-wizard-step4');
    await waitForSettled(step4, 30_000);
    return step4;
}

/**
 * Keep selected only the review rows that carry no asset — the cash movements — through the review's
 * own controls: deselect all, the asset column filter on "no asset", select the rows shown. Import
 * stays disabled while a selected row points at an unresolved asset, and the synthetic securities
 * resolve against nothing that may be created here (an asset is a global row every shot would see).
 * Import enabled is the proof that only cash rows are selected. Returns how many are.
 */
export async function keepOnlyCashRows(page: Page, step4: Locator): Promise<number> {
    await page.getByTestId('import-wizard-deselect-all').click();
    await expect(step4).toHaveAttribute('data-selected-count', '0', {timeout: 5_000});
    const trigger = step4.getByTestId('col-filter-trigger-asset');
    await trigger.click();
    const filter = step4.getByTestId('dt-header-asset').getByTestId('column-filter');
    await expect(filter).toBeVisible({timeout: 5_000});
    const noAsset = filter.getByTestId('filter-enum-option-__null__');
    await expect(noAsset).toHaveAttribute('data-checked', 'false');
    await noAsset.click();
    await expect(noAsset).toHaveAttribute('data-checked', 'true');
    await trigger.click();
    await expect(filter).toBeHidden({timeout: 5_000});
    await expect(step4.locator('tbody tr[data-row-id]').first(), 'the review lists cash movements').toBeVisible({timeout: 5_000});
    await page.getByTestId('import-wizard-select-visible').click();
    await expect(step4, 'the cash movements are selected').not.toHaveAttribute('data-selected-count', '0', {timeout: 5_000});
    await expect(page.getByTestId('import-wizard-import'), 'no selected row waits for an asset').toBeEnabled({timeout: 15_000});
    return Number(await step4.getAttribute('data-selected-count'));
}

/** The wizard handed over and closed: the bulk editor underneath, settled. */
export async function editorAfterHandoff(page: Page): Promise<Locator> {
    await expect(page.getByTestId('import-wizard-stepper')).toHaveCount(0, {timeout: 15_000});
    const root = page.getByTestId('tx-bulk-modal-root');
    await expect(root).toBeVisible({timeout: 10_000});
    await waitForSettled(root, 30_000);
    return root;
}

/** Never Save All: close the editor through its unsaved-changes guard and discard. */
export async function closeEditorWithoutSaving(page: Page, root: Locator): Promise<void> {
    await page.getByTestId('tx-bulk-close').click();
    const discard = page.getByTestId('confirm-modal-confirm');
    await expect(discard, 'the editor holds the imported rows: closing it asks to discard them').toBeVisible({timeout: 5_000});
    await discard.click();
    await expect(root).toHaveCount(0, {timeout: 10_000});
}

// ---------------------------------------------------------------------------
// Before a shot
// ---------------------------------------------------------------------------

/**
 * `target` has stopped moving: two readings of its position in a row agree. A smooth scroll or a
 * popover that follows its anchor runs on no animation the gallery can pause, and the browser
 * publishes no end for it — this reads the position itself, the way Playwright's own actionability
 * check does before a click.
 */
export async function waitForStillness(target: Locator, what: string): Promise<void> {
    let previous = '';
    await expect
        .poll(
            async () => {
                const box = await target.boundingBox();
                const now = box ? `${Math.round(box.x)},${Math.round(box.y)},${Math.round(box.width)},${Math.round(box.height)}` : 'none';
                const still = now !== 'none' && now === previous;
                previous = now;
                return still;
            },
            {message: `${what} is still moving`, timeout: 10_000, intervals: [100, 150, 250]},
        )
        .toBe(true);
}

/** `target` is on screen and on top: nothing (a popover, a menu) covers its centre. */
export async function expectUncovered(target: Locator, what: string): Promise<void> {
    await expect(target, `${what} is in the viewport`).toBeInViewport();
    await expect
        .poll(
            () =>
                target.evaluate((element) => {
                    const box = element.getBoundingClientRect();
                    const hit = document.elementFromPoint(box.left + box.width / 2, box.top + box.height / 2);
                    return hit !== null && (hit === element || element.contains(hit));
                }),
            {message: `${what} is covered by another element`, timeout: 5_000},
        )
        .toBe(true);
}

/** Every kind of toast the app shows: ToastContainer renders each as `toast-{variant}`. */
const ANY_TOAST = ['success', 'error', 'warning', 'info'].map((variant) => `[data-testid="toast-${variant}"]`).join(', ');

/**
 * Close the success toasts on screen through their own ✕, and wait until they have slid out. A success
 * toast also leaves on its own timer (8 s, toastStore), so the ✕ is pressed by its handler, all toasts in
 * one page task: a toast that leaves meanwhile costs nothing, and no pointer can land on the page
 * underneath it — the editor's backdrop, which would ask to discard. No pointer moves either, so nothing
 * here touches the grid. Errors and warnings are left alone: they are news, for `expectNoToast` to fail on.
 */
export async function closeSuccessToasts(page: Page): Promise<void> {
    const shown = page.getByTestId('toast-success');
    await shown.evaluateAll((toasts) => {
        for (const toast of toasts) toast.querySelector<HTMLElement>('[data-testid="toast-dismiss"]')?.click();
    });
    await expect(shown, 'the success toasts have slid out').toHaveCount(0, {timeout: 5_000});
}

/** Nothing lies over the shot: no toast of any kind on screen, not even one sliding out. */
export async function expectNoToast(page: Page): Promise<void> {
    await expect(page.locator(ANY_TOAST), 'no toast lies over the shot').toHaveCount(0);
}

/** The report-set badge kinds of one Files row, in the order they are shown. */
export function badgeKinds(row: Locator): Promise<string[]> {
    return row.locator('[data-testid="file-set-badge"]').evaluateAll((badges) => badges.map((badge) => badge.getAttribute('data-kind') ?? ''));
}
