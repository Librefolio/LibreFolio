/**
 * Gallery, inventory group 4 — the risk lab and the What if…? simulation.
 *
 * The lab is the Assets page on its Correlation tab (`AssetSetRiskPanel`); the simulation is the last
 * step of the Dashboard's What if…? level (`L4WhatIf`, `L4Simulation`). This module holds what their
 * shots stand on: the assets they open on, the guards that keep them read-only, the waits that make a
 * shot follow the data, and the two answers edited where the gallery's data cannot show the state.
 *
 * ## Read-only
 *
 * What the lab remembers lives in the browser, under the user's key: the selection
 * (`lf_<user>_assetGlobal.riskSelection.v1`, assetSetSelection.ts), the benchmark
 * (`lf_<user>_risk_benchmark_asset`, riskBenchmarkStore.svelte.ts) and, on the Dashboard, the What
 * if…? tools left open (`lf_<user>_risk.l4.openTools`, L4WhatIf.svelte). Each test writes them into
 * its own browser context before every page load, so every combination opens on the same state and
 * nothing reaches the database.
 *
 * The page writes on its own in one place: while the period ends today, the Assets page polls
 * `POST /assets/prices/current` (on load, then every 30 s), which asks each asset's price provider for
 * today's quote and stores it (assets.py, `get_current_prices_bulk`). The gallery-wide offline guard
 * (galleryReportSets.ts, `guardGalleryOffline`) keeps every page from reaching a provider — it aborts the
 * syncs a mistaken click would start and answers the provider catalogue from a fixture — and answers that
 * poll from fixed prices. In the lab {@link guardReadOnly} has it abort the poll instead: the poll catches
 * the failure and logs one warning, with no toast; and an aborted call, unlike an answered one, marks no risk
 * answer stale (portfolioMutation.ts). Held unanswered instead, as risk-lab.spec.ts holds it, it would keep
 * the page from ever going network-idle, which every gallery shot waits for.
 *
 * ## What is injected, and why
 *
 * The gallery's prices are clean: every asset the lab can analyse is priced from the same first day
 * to the populate day. So no real answer carries a stale price, and no replay leaves one asset out
 * while it replays the others — a window covers all of them or none. Two shots need those states, and
 * edit the real answer on its way (fetch, edit, fulfil): every figure on screen is the engine's, only
 * the fields named below change, in the shapes the backend builds, and the page's generated Zod
 * schemas check them — an edit they refused would fail its section, and the shot with it.
 *
 * - `risk/lab-notice` ({@link injectStalePrice}): one selected asset's last price is older than the
 *   7-day threshold, as `RiskService._success` reports it on every result of the lab's base waves:
 *   status `partial`, a `data_quality_degraded` warning naming the asset, a `carried_forward` report
 *   carrying the STALE_PRICE issue. And the matrix's own answer does not come back (`unavailable`,
 *   `insufficient_history`), so the section right under the notice shows its banner. That second edit
 *   is not what a stale price causes — the engine drops a matrix only when its window holds fewer than
 *   two observations, which the lab's eligibility check never lets through — but the matrix is the one
 *   section whose banner fits on the same screen as the notice. The eligibility answers about that asset
 *   carry the matching stale-end verdict (`warning`, `stale_at_end`), so its chip shows the warning while
 *   it stays in the analysis.
 * - `risk/lab-replay` ({@link injectReplayLeftOut}): a replay over the page's period in which one
 *   selected asset is left out, for a first quote 60 days after the window began (invented), with the
 *   part of the window that would bring it back. The other assets' rows are the engine's own.
 *
 * ## Screens taller than the desktop's
 *
 * On the desktop only, the simulation and the four Dashboard Risk blocks (`dashboard/risk-*`) are taller than the
 * project's 720 px, and their pages want each of them whole in one image: the Simulation box is about 1,100 px high (1090
 * measured). {@link fitViewportToBlock} gives each of those shots a screen as tall as its box or block plus the frame's
 * margins, its width and scale unchanged (coordinator's decision, provisional). The mobile project keeps its phone.
 *
 * The Dashboard's own Risk tab shots stand on this module too: galleryRiskDashboard.ts.
 */

import type {APIResponse, Route} from '@playwright/test';
import {expect, type Locator, type Page} from './playwright';
import {navigateTo} from './auth-helpers';
import {galleryOfflineGuard, type GalleryOfflineGuard, waitForStillness} from './galleryReportSets';

/** The lab: the Assets page on its Correlation tab. */
export const LAB_URL = '/assets?tab=correlation';

export const RISK_QUERY = '**/api/v1/risk/query';
const RISK_ELIGIBILITY = '**/api/v1/risk/eligibility';
/** A risk answer is computed on the shared backend: under load it takes seconds, never this long. */
export const ANSWER_TIMEOUT = 120_000;

/** What a shot says when the clean gallery data turns out not to be clean. */
const STALE_DATA_HINT = 'the lab reports a data problem on the clean gallery data: the lane database is probably older than the 7-day threshold — re-populate it (./dev.py db populate --force)';

// ---------------------------------------------------------------------------
// The assets
// ---------------------------------------------------------------------------

/** The seeded assets the shots name, by display name (populate_mock_data.py). */
export const LAB_ASSET_NAMES = {
    apple: 'Apple Inc.',
    microsoft: 'Microsoft Corporation',
    tesla: 'Tesla, Inc.',
    milano: 'RE Loan Milano',
    roma: 'RE Loan Roma',
    bitcoin: 'Bitcoin',
    ethereum: 'Ethereum',
    sp500: 'S&P 500',
    nvidia: 'NVIDIA Corporation',
    krw: 'Test KRW Stock',
} as const;

export type LabAssetKey = keyof typeof LAB_ASSET_NAMES;
export type LabIds = Record<LabAssetKey, number> & {userId: number};

/** The id the app keys the user's storage by, from the session this page is signed in with. */
export async function currentUserId(page: Page): Promise<number> {
    const response = await page.request.get('/api/v1/auth/me');
    expect(response.ok(), `GET /api/v1/auth/me answered HTTP ${response.status()}`).toBe(true);
    const id = ((await response.json()) as {user?: {id?: unknown}}).user?.id;
    if (typeof id !== 'number' || !Number.isInteger(id)) throw new Error(`auth/me published no integer user id: ${JSON.stringify(id)}`);
    return id;
}

/** The ids of the assets the shots name, found by display name — never assumed from the populate order. */
export async function resolveLabIds(page: Page): Promise<LabIds> {
    const userId = await currentUserId(page);
    const response = await page.request.get('/api/v1/assets/query');
    expect(response.ok(), `GET /api/v1/assets/query answered HTTP ${response.status()}`).toBe(true);
    const assets = (await response.json()) as Array<{id: number; display_name: string}>;
    const ids = {userId} as LabIds;
    for (const [key, name] of Object.entries(LAB_ASSET_NAMES) as Array<[LabAssetKey, string]>) {
        const matches = assets.filter((asset) => asset.display_name === name);
        if (matches.length !== 1) throw new Error(`Asset "${name}" found ${matches.length} times, expected once. Check populate_mock_data.py seeding.`);
        ids[key] = matches[0].id;
    }
    return ids;
}

/**
 * The selection every lab shot opens on: five assets priced over the whole year, of three kinds and two
 * currencies — a stock, the two real-estate loans and the two crypto assets the seed correlates on
 * purpose (populate_mock_data.py, `correlation_plan`). Two «most alike» pairs for the matrix, and a
 * risk/return table short enough to share one desktop screen with its chart. Sorted, as the panel
 * sorts what it adds.
 */
export function labSelection(ids: LabIds): number[] {
    return [ids.apple, ids.milano, ids.roma, ids.bitcoin, ids.ethereum].sort((left, right) => left - right);
}

/** A pair of the correlation rankings, in whichever orientation the matrix's lower triangle names it. */
export function pairTestId(left: number, right: number): RegExp {
    return new RegExp(`^risk-correlation-pair-(${left}-${right}|${right}-${left})$`);
}

/** The ids of a comma-separated attribute (`data-asset-order`), sorted: the set the matrix draws. */
export function idSet(attribute: string | null): number[] {
    return (attribute ?? '')
        .split(',')
        .filter((entry) => entry !== '')
        .map(Number)
        .sort((left, right) => left - right);
}

// ---------------------------------------------------------------------------
// Read-only: the browser's own memory, and the calls that would write
// ---------------------------------------------------------------------------

/**
 * Write the lab's memory before every page load: the selection, and the benchmark (`null` forgets
 * it). An init script runs ahead of the app on each navigation, so every combination opens on this
 * state, whatever the previous one left.
 */
export async function seedLabStorage(page: Page, userId: number, state: {selection: readonly number[]; benchmark: number | null}): Promise<void> {
    await page.addInitScript(
        ({prefix, selection, benchmark}) => {
            try {
                window.localStorage.setItem(`${prefix}assetGlobal.riskSelection.v1`, JSON.stringify(selection));
                if (benchmark === null) window.localStorage.removeItem(`${prefix}risk_benchmark_asset`);
                else window.localStorage.setItem(`${prefix}risk_benchmark_asset`, String(benchmark));
            } catch {
                /* storage disabled: the opening assertions say so */
            }
        },
        {prefix: `lf_${userId}_`, selection: [...state.selection], benchmark: state.benchmark},
    );
}

/**
 * Forget, before every page load, the What if…? tools the Dashboard remembers left open: each load starts
 * with none. The key is the signed-in user's; the `anon` one too, in case the level mounted before the
 * session's user was known.
 */
export async function forgetWhatIfTools(page: Page, userId: number): Promise<void> {
    await page.addInitScript(
        (keys) => {
            for (const key of keys) {
                try {
                    window.localStorage.removeItem(key);
                } catch {
                    /* storage disabled: nothing is remembered either */
                }
            }
        },
        [`lf_${userId}_risk.l4.openTools`, 'lf_anon_risk.l4.openTools'],
    );
}

/** The part of the gallery's offline guard a lab shot reads: the polls it aborted, and the syncs a stray click started. */
export type ReadOnlyGuard = Pick<GalleryOfflineGuard, 'livePolls' | 'syncs'>;

/**
 * The lab's read-only switch on the gallery-wide offline guard (galleryReportSets.ts), which is the one owner of the
 * routes: it already aborts the price and exchange-rate syncs (the toolbar's Sync selection, a banner's Sync prices
 * or Sync rates) and records them, failing the test at its end. Here it also aborts the Assets page's live-price
 * poll, which it answers from fixed prices elsewhere: an answered poll marks every risk answer stale. Returns the
 * guard itself, so `syncs` lists what the whole test attempted.
 */
export async function guardReadOnly(page: Page): Promise<ReadOnlyGuard> {
    const guard = galleryOfflineGuard(page);
    guard.livePrices = 'abort';
    return guard;
}

// ---------------------------------------------------------------------------
// The lab
// ---------------------------------------------------------------------------

/** The toolbar's 1Y preset — the page's own period, never the replay's, which has a picker of its own. */
function pagePreset(page: Page): Locator {
    return page.getByTestId('assets-date-range').getByTestId('date-preset-1y');
}

/**
 * Put the page on the 1Y period. The Assets page opens on 3M, and the period persists in the session,
 * so this is done once, before the combinations: each later load opens on 1Y. A preset is a toggle —
 * pressed only when it is not lit, and the end state asserted.
 */
export async function chooseLabYear(page: Page): Promise<void> {
    await navigateTo(page, LAB_URL);
    const oneYear = pagePreset(page);
    await expect(oneYear).toBeVisible({timeout: 15_000});
    if ((await oneYear.getAttribute('data-active')) !== 'true') await oneYear.click();
    await expect(oneYear).toHaveAttribute('data-active', 'true');
}

/**
 * Load the lab and end on the selection being analysed and the matrix's answer being in: the period,
 * every chip with the engine's verdict and none parked, then the correlation section past its catalog
 * gate and its base wave. Each section's own readiness is the caller's.
 */
export async function openLab(page: Page, selection: readonly number[]): Promise<void> {
    await navigateTo(page, LAB_URL);
    await expect(page.getByTestId('asset-global-risk-panel')).toBeVisible({timeout: 20_000});
    await expect(pagePreset(page), 'the lab opened on another period than 1Y').toHaveAttribute('data-active', 'true', {timeout: 10_000});
    for (const assetId of selection) await expect(page.getByTestId(`risk-selected-asset-${assetId}`), `asset ${assetId} of the seeded selection has no chip`).toBeVisible({timeout: 15_000});
    await expect(page.locator('[data-testid^="risk-selected-asset-"][data-level="unknown"]'), 'a chip is still waiting for the eligibility verdict').toHaveCount(0, {timeout: 15_000});
    await expect(page.getByTestId('risk-eligibility-failed')).toHaveCount(0);
    const counter = page.getByTestId('risk-selected-count');
    await expect(counter, 'every selected asset is analysed').toHaveAttribute('data-selected', String(selection.length));
    await expect(counter, 'no selected asset is parked').toHaveAttribute('data-parked', '0');
    const matrix = page.getByTestId('risk-correlation-content');
    await expect(matrix).toHaveAttribute('data-catalog', 'ready', {timeout: 30_000});
    await expect(matrix).toHaveAttribute('data-busy', 'false', {timeout: 60_000});
}

/**
 * The real answers came back whole: with both levels' tables on the page — so every result the notice
 * reads is in — there is no notice, no data-quality banner, no period offer and no section banner. A
 * red here means the gallery data went stale, and the shot would document a problem it never meant to.
 */
export async function expectLabClean(page: Page, selection: readonly number[]): Promise<void> {
    const panel = page.getByTestId('asset-global-risk-panel');
    await expect(panel.getByTestId('risk-asset-set-l1-table')).toHaveAttribute('data-row-count', String(selection.length), {timeout: 30_000});
    await expect(panel.getByTestId('risk-asset-set-l3-table')).toHaveAttribute('data-row-count', String(selection.length), {timeout: 30_000});
    await expect(panel.getByTestId('risk-partial-notice'), STALE_DATA_HINT).toHaveCount(0);
    await expect(panel.getByTestId('data-quality-banner'), STALE_DATA_HINT).toHaveCount(0);
    await expect(panel.getByTestId('risk-fit-period-banner'), STALE_DATA_HINT).toHaveCount(0);
    for (const section of ['risk-correlation-section', 'risk-asset-set-loss', 'risk-asset-set-paid']) await expect(panel.getByTestId(`${section}-alert`), STALE_DATA_HINT).toHaveCount(0);
}

// ---------------------------------------------------------------------------
// Framing a shot
// ---------------------------------------------------------------------------

/** The app header has slid away, as it does on any scroll down: no bar lies over the framed content. */
async function headerOutOfShot(page: Page): Promise<void> {
    const header = page.getByTestId('app-header');
    await expect(header, 'the app header slides away on a scroll down').toHaveAttribute('data-scroll-state', 'hidden');
    await expect.poll(() => header.evaluate((element) => element.getBoundingClientRect().bottom), {message: 'the app header is still sliding away'}).toBeLessThanOrEqual(1);
}

/** Two animation frames rendered in the page: a scroll made before them is dispatched, and every frame callback it scheduled has run. */
export async function renderedFrames(page: Page): Promise<void> {
    await page.evaluate(() => new Promise<void>((resolve) => requestAnimationFrame(() => requestAnimationFrame(() => resolve()))));
}

/**
 * Resize the screen and end once the page has handled it: its `resize` dispatched at the new height. `setViewportSize`
 * returns before that, and the app header resets itself on the event (Header.svelte, `syncScrollContext`: visible again,
 * its scroll baseline where the page stands): dispatched after a later scroll down, it leaves the header over the shot. The
 * app's listeners, added at mount, have run when the one armed here does. A no-op when the screen has that size already.
 */
export async function resizeViewport(page: Page, size: {width: number; height: number}): Promise<void> {
    const screen = page.viewportSize();
    if (screen?.width === size.width && screen.height === size.height) return;
    await page.evaluate(() => {
        const marker = window as unknown as {__galleryResizedTo?: number};
        marker.__galleryResizedTo = -1;
        window.addEventListener(
            'resize',
            () => {
                marker.__galleryResizedTo = window.innerHeight;
            },
            {once: true},
        );
    });
    await page.setViewportSize(size);
    await expect.poll(() => page.evaluate(() => (window as unknown as {__galleryResizedTo?: number}).__galleryResizedTo), {message: 'the page never handled the screen resize'}).toBe(size.height);
}

/**
 * Scroll the page so `target` starts `margin` px under the top of the screen — or as near as the page's
 * end allows — and end on the header gone and the target still.
 *
 * Always down from the top: the header slides away only on a scroll down, and a scroll up — after a
 * click Playwright scrolled into view further down, say — would bring it back over the target. So the
 * top is reached first, and seen by the header, then the page scrolls down to the target. Seen means
 * rendered: the header measures a scroll from where it last saw the page, so a header reset where the
 * page stood — a resize resets it — reads a way up and back down inside one frame as no movement, and stays.
 */
export async function frameFromTop(page: Page, target: Locator, margin = 8): Promise<void> {
    await expect(target).toBeVisible();
    await page.evaluate(() => window.scrollTo({top: 0, behavior: 'instant'}));
    await renderedFrames(page);
    await expect(page.getByTestId('app-header'), 'the app header is back at the top').toHaveAttribute('data-scroll-state', 'visible');
    await target.evaluate((element, offset) => {
        window.scrollTo({top: Math.max(0, element.getBoundingClientRect().top + window.scrollY - offset), behavior: 'instant'});
    }, margin);
    await headerOutOfShot(page);
    await waitForStillness(target, 'the framed section');
}

/**
 * Frame a block from `first` to `last` when it fits on the screen, and from `fallback` when it does not:
 * a measured layout decides, so each viewport always takes the same branch.
 */
export async function frameBlock(page: Page, block: {first: Locator; last: Locator; fallback: Locator}, margin = 8): Promise<void> {
    const viewport = page.viewportSize();
    if (!viewport) throw new Error('the page has no viewport');
    const top = await block.first.evaluate((element) => element.getBoundingClientRect().top + window.scrollY);
    const bottom = await block.last.evaluate((element) => element.getBoundingClientRect().bottom + window.scrollY);
    await frameFromTop(page, bottom - top + 2 * margin <= viewport.height ? block.first : block.fallback, margin);
}

/**
 * Make the screen as tall as `block` plus `margin` above and below it — never shorter than `minimumHeight`, the project's
 * own — keeping its width and its scale (`setViewportSize` leaves the device scale factor alone). For the shots whose
 * subject is taller than the desktop's screen: the simulation (`risk/whatif-simulation`) and the four Dashboard Risk
 * blocks (`dashboard/risk-*`), desktop only. Measured on the page as it stands, every time: the block's sentences wrap
 * differently in each language. The block must not move while it is measured, and nothing in it depends on the screen's
 * height, so the resize changes no layout inside it — a chart may still redraw, which the caller's settle waits out.
 * A resize ends with the page having handled it ({@link resizeViewport}): the header is shown again where the page stands,
 * so the caller frames the block again, from the top ({@link frameFromTop}). Returns the height measured and the screen's.
 */
export async function fitViewportToBlock(page: Page, block: Locator, margin: number, minimumHeight: number): Promise<{blockHeight: number; viewportHeight: number}> {
    const viewport = page.viewportSize();
    if (!viewport) throw new Error('the page has no viewport');
    await waitForStillness(block, 'the block the screen is fitted to');
    const blockHeight = await block.evaluate((element) => element.getBoundingClientRect().height);
    const viewportHeight = Math.max(minimumHeight, Math.ceil(blockHeight) + 2 * margin);
    await resizeViewport(page, {width: viewport.width, height: viewportHeight});
    return {blockHeight: Math.ceil(blockHeight), viewportHeight};
}

/** Back to the top, where the header — and the language and theme controls — are on screen again. */
export async function scrollBackToHeader(page: Page): Promise<void> {
    await page.evaluate(() => window.scrollTo({top: 0, behavior: 'instant'}));
    await expect(page.getByTestId('app-header')).toHaveAttribute('data-scroll-state', 'visible');
}

/**
 * Rest the pointer where nothing reacts to it — the right edge of the screen, mid-height, inside the
 * main area's padding — and end on no tooltip being shown: the last click or hover leaves none behind.
 */
export async function parkPointer(page: Page): Promise<void> {
    const viewport = page.viewportSize();
    if (!viewport) throw new Error('the page has no viewport');
    await page.mouse.move(viewport.width - 2, Math.round(viewport.height / 2));
    await expect(page.getByTestId('tooltip-content'), 'a tooltip lies over the shot').toHaveCount(0);
}

/** Every image inside `scope` has finished loading (or failed): no icon is caught half-drawn. */
export async function imagesSettled(scope: Locator): Promise<void> {
    await expect.poll(() => scope.evaluate((root) => Array.from(root.querySelectorAll('img')).filter((image) => !image.complete).length), {message: 'an image in the shot is still loading', timeout: 15_000}).toBe(0);
}

/**
 * Scroll the list that holds `section` — its parent — so the section's top, where its header is, meets the top of
 * what the list shows, with its first entries under it. A section that fits in the list from there stops at the
 * list's end instead, where the browser clamps the scroll, and is then on show whole. Only the list scrolls; the
 * end state asserted is the header not above what the list shows.
 */
export async function revealListSection(section: Locator): Promise<void> {
    await section.evaluate((element) => {
        const list = element.parentElement;
        if (!list) throw new Error('the section sits in no list');
        list.scrollTop += element.getBoundingClientRect().top - list.getBoundingClientRect().top - parseFloat(getComputedStyle(list).paddingTop);
    });
    await expect
        .poll(
            () =>
                section.evaluate((element) => {
                    const list = element.parentElement;
                    return list ? Math.round(element.getBoundingClientRect().top - list.getBoundingClientRect().top) : -1;
                }),
            {message: "the section's header is above what its list shows"},
        )
        .toBeGreaterThanOrEqual(0);
}

// ---------------------------------------------------------------------------
// The answers edited on their way
// ---------------------------------------------------------------------------

export type Json = Record<string, unknown>;

interface RiskRequest {
    scope?: {kind?: string};
    date_range?: {start?: string; end?: string | null};
    mode?: string;
    analytics?: Array<{analytic_code?: string; parameters?: Json}>;
}

export interface RiskItem extends Json {
    instance_id: string;
    analytic_code: string;
    status: string;
    output?: Json | null;
    metadata?: Json | null;
    data_quality?: Json | null;
    warnings?: Json[];
}

export interface Injection {
    /** Answers edited so far. */
    edited: number;
    /** Answers that went through unedited, and why. */
    problems: string[];
}

export interface StaleInjection extends Injection {
    /** Eligibility answers in which the stale asset's verdict was edited. */
    verdictsEdited: number;
}

interface EligibilityRequest {
    asset_ids: unknown[];
    date_range?: {start?: string; end?: string | null};
}

export function isRecord(value: unknown): value is Json {
    return value !== null && typeof value === 'object' && !Array.isArray(value);
}

/** The eligibility question a route carries, or null when its body is not one. */
function eligibilityRequestOf(route: Route): EligibilityRequest | null {
    try {
        const body: unknown = route.request().postDataJSON();
        return isRecord(body) && Array.isArray(body.asset_ids) ? (body as unknown as EligibilityRequest) : null;
    } catch {
        return null;
    }
}

/** The risk question a route carries, or null when its body is not one. */
function riskRequestOf(route: Route): RiskRequest | null {
    try {
        const body: unknown = route.request().postDataJSON();
        return isRecord(body) ? (body as RiskRequest) : null;
    } catch {
        return null;
    }
}

/** A response's JSON body, or null when it has none. */
export async function jsonOf(response: APIResponse): Promise<unknown> {
    try {
        return await response.json();
    } catch {
        return null;
    }
}

/** The results of a risk answer, or null when the body is not a `RiskQueryResponse`. */
export function riskItemsOf(body: unknown): RiskItem[] | null {
    if (!isRecord(body) || !Array.isArray(body.items)) return null;
    return body.items.every((item) => isRecord(item) && typeof item.instance_id === 'string' && typeof item.analytic_code === 'string' && typeof item.status === 'string') ? (body.items as RiskItem[]) : null;
}

/**
 * Answer `route` with the status and headers of `response` and a new JSON body. The headers that
 * described the original body — its length, its compression, its chunking — no longer describe this
 * one, so they are left for the new body to set (as galleryReportSets.ts does).
 */
async function fulfillWith(route: Route, response: APIResponse, json: unknown): Promise<void> {
    const stale = new Set(['content-length', 'content-encoding', 'transfer-encoding']);
    const headers = Object.fromEntries(Object.entries(response.headers()).filter(([name]) => !stale.has(name.toLowerCase())));
    await route.fulfill({response, headers, json});
}

/** An ISO day, `YYYY-MM-DD`: the only shape {@link shiftDay} is given. */
export const ISO_DAY = /^\d{4}-\d{2}-\d{2}$/;

/** An ISO day moved by `days`, in UTC so the day never shifts. */
function shiftDay(isoDay: string, days: number): string {
    const date = new Date(`${isoDay}T00:00:00Z`);
    date.setUTCDate(date.getUTCDate() + days);
    return date.toISOString().slice(0, 10);
}

/** How far before the period's end the stale price is: past the 7-day threshold (data_quality_thresholds.py). */
const STALE_DAYS = 12;
/** The weekday prices carried over those days. */
const CARRIED_POINTS = 8;

/**
 * A result as `RiskService._success` reports it when one asset's price is stale: `partial`, with the
 * `data_quality_degraded` warning `_data_quality_warnings` builds (its names and count added as
 * `_with_warning_asset_names` adds them) and a `carried_forward` report carrying the STALE_PRICE issue
 * `_data_quality_issues` builds. A result that produced no answer keeps its own status.
 */
function withStalePrice(item: RiskItem, asset: {id: number; name: string}, periodEnd: string): RiskItem {
    if (item.status !== 'ok' && item.status !== 'partial') return item;
    const report = isRecord(item.data_quality) ? item.data_quality : {};
    const issues = Array.isArray(report.issues) ? report.issues : [];
    return {
        ...item,
        status: 'partial',
        warnings: [
            ...(item.warnings ?? []),
            {
                code: 'data_quality_degraded',
                message: 'Risk result uses incomplete or carried-forward source data.',
                details: {status: 'carried_forward', cause: 'stale_prices', asset_ids: [asset.id]},
                degrades_result: true,
                message_i18n_key: 'risk.warnings.data_quality_stale_prices',
                message_params: {days: 7, names: asset.name, count: 1},
            },
        ],
        data_quality: {
            ...report,
            data_quality_status: 'carried_forward',
            stale_prices: [{asset_id: asset.id, name: asset.name, last_price_date: shiftDay(periodEnd, -STALE_DAYS), stale_days: STALE_DAYS}],
            carried_forward_price_points: CARRIED_POINTS,
            carried_forward_price_asset_ids: [asset.id],
            issues: [
                ...issues,
                {
                    domain: 'asset',
                    code: 'STALE_PRICE',
                    severity: 'warning',
                    message_i18n_key: 'dataQuality.stalePrice',
                    message_params: {count: 1},
                    count: 1,
                    affected_asset_ids: [asset.id],
                    affected_asset_names: [asset.name],
                    cta_action: 'sync_asset_prices',
                    cta_target: String(asset.id),
                    group_key: 'stale_price',
                },
            ],
        },
    };
}

/** The matrix as `RiskService._unavailable` returns it below its minimum: no output, no warning, the window's report kept. */
function withoutMatrix(item: RiskItem): RiskItem {
    return {
        instance_id: item.instance_id,
        analytic_code: item.analytic_code,
        status: 'unavailable',
        output: null,
        metadata: item.metadata ?? null,
        data_quality: item.data_quality ?? null,
        warnings: [],
        error: {code: 'insufficient_history', message: "Analytic 'correlation' requires at least 2 observations", details: {observations: 1, required: 2}},
    };
}

/**
 * The verdict `analysis_eligibility` (risk/eligibility.py) gives an asset whose last quote is more than the
 * 7-day threshold before the period's end: `warning`, `stale_at_end` — a warning keeps the asset in the
 * analysis — with that last quote (the same day the stale results name), and the period's quotes less those
 * it missed. First quote and the rest of the item are the engine's.
 */
function staleVerdict(item: Json, periodEnd: string): Json {
    const quotes = typeof item.quotes_in_period === 'number' ? item.quotes_in_period : 0;
    return {...item, level: 'warning', reasons: ['stale_at_end'], last_quote: shiftDay(periodEnd, -STALE_DAYS), quotes_in_period: Math.max(0, quotes - CARRIED_POINTS)};
}

/**
 * `risk/lab-notice`: edit every base wave of the lab (asset set, historical) as if `asset`'s last price
 * were 12 days old, and the matrix's own wave — the one that asks for the correlation alone, shared by
 * the correlation section and the replay section — as if the matrix had not come back. The notice then
 * reads five partial measurements (both levels', the matrix's answer being gone) and one cause; the
 * banner, the STALE_PRICE issue; the correlation section, its banner.
 *
 * Every eligibility answer the lab receives about `asset` — the catalogue's, behind the chips, and the
 * selection's — carries the matching stale-end verdict, so the asset's chip shows the warning while the asset
 * stays in the analysis (five selected, none parked). The rest of each answer is the engine's: its
 * `suggested_range` is left as answered (none, on fresh prices), so the card shows no fit-the-period strip,
 * which the engine would offer for a stale end. Install before the lab loads.
 */
export async function injectStalePrice(page: Page, asset: {id: number; name: string}): Promise<StaleInjection> {
    const log: StaleInjection = {edited: 0, verdictsEdited: 0, problems: []};
    await page.route(RISK_QUERY, async (route) => {
        const request = riskRequestOf(route);
        if (request?.scope?.kind !== 'asset_set' || request.mode !== 'historical' || !Array.isArray(request.analytics)) return route.fallback();
        const response = await route.fetch({timeout: ANSWER_TIMEOUT});
        const body = await jsonOf(response);
        const items = riskItemsOf(body);
        if (!response.ok() || items === null) {
            log.problems.push(`a lab base wave answered HTTP ${response.status()} without a readable list of results: it went through unedited`);
            return route.fulfill({response});
        }
        const periodEnd = request.date_range?.end || request.date_range?.start || '';
        if (!ISO_DAY.test(periodEnd)) {
            log.problems.push(`a lab base wave asked a period without an end day (${JSON.stringify(request.date_range)}): it went through unedited`);
            return route.fulfill({response});
        }
        const matrixOnly = request.analytics.length === 1 && request.analytics[0]?.analytic_code === 'correlation';
        const edited = items.map((item) => {
            const stale = withStalePrice(item, asset, periodEnd);
            return matrixOnly && item.analytic_code === 'correlation' ? withoutMatrix(stale) : stale;
        });
        log.edited += 1;
        await fulfillWith(route, response, {...(body as Json), items: edited});
    });
    await page.route(RISK_ELIGIBILITY, async (route) => {
        const request = eligibilityRequestOf(route);
        if (!request?.asset_ids.includes(asset.id)) return route.fallback();
        const response = await route.fetch({timeout: ANSWER_TIMEOUT});
        const body = await jsonOf(response);
        const items = isRecord(body) && Array.isArray(body.items) ? (body.items as unknown[]) : null;
        const verdict = items?.find((item) => isRecord(item) && item.asset_id === asset.id);
        const periodEnd = request.date_range?.end || request.date_range?.start || '';
        // Only a verdict that keeps the asset in the analysis is turned into a stale one: an ineligible asset stays out.
        if (!response.ok() || !items || !isRecord(verdict) || (verdict.level !== 'eligible' && verdict.level !== 'warning') || !ISO_DAY.test(periodEnd)) {
            log.problems.push(`an eligibility answer about asset ${asset.id} could not be edited (HTTP ${response.status()}, verdict ${JSON.stringify(isRecord(verdict) ? verdict.level : verdict)}): it went through unedited`);
            return route.fulfill({response});
        }
        log.verdictsEdited += 1;
        await fulfillWith(route, response, {...(body as Json), items: items.map((item) => (item === verdict ? staleVerdict(verdict, periodEnd) : item))});
    });
    return log;
}

/** How far into the replay window the left-out asset's (invented) first quote falls. */
const LATE_LISTING_DAYS = 60;

export interface ReplayInjection extends Injection {
    /** The common period the last edited answer offers. */
    suggested: {start: string; end: string} | null;
}

/** Why a replay answer cannot be edited into one that left `assetId` out, or null when it can. */
function replayProblem(response: APIResponse, item: RiskItem | undefined, assetId: number, window: {start: string; end: string}): string | null {
    if (!response.ok()) return `the replay answered HTTP ${response.status()}`;
    if (!ISO_DAY.test(window.start) || !ISO_DAY.test(window.end)) return `the replay window ${JSON.stringify(window)} is not a pair of days`;
    if (!item) return 'the replay answered without a result';
    if (item.status !== 'ok' && item.status !== 'partial') return `the real replay came back ${item.status}: every selected asset should cover the page's period`;
    const output = item.output;
    if (!isRecord(output) || output.kind !== 'stress' || !Array.isArray(output.impacts)) return 'the replay answer carries no impacts';
    if (!output.impacts.some((impact) => isRecord(impact) && impact.asset_id === assetId)) return `asset ${assetId} has no row in the real replay`;
    const audit = isRecord(item.metadata) ? item.metadata.historical_replay_audit : null;
    if (!isRecord(audit) || audit.excluded_count !== 0) return 'the real replay carries no audit, or already left an asset out';
    if (shiftDay(window.start, LATE_LISTING_DAYS + 1) >= window.end) return `the replay window ${window.start}…${window.end} is too short to place a late listing in`;
    return null;
}

/**
 * `risk/lab-replay`: edit the lab's historical replay so that `asset` is left out of it, as
 * `stress.py::_historical` and `RiskService._verified_replay_range` report an asset whose first quote
 * came 60 days into the window: no impact row, the audit listing it (`starts_after_window_start`,
 * omitted from the replay, as on any selection without weights) with the common period that brings it
 * back, the result's own exclusion and the block's warning, the result `partial`. The other rows, the
 * window and the figures are the engine's. Install before the replay runs.
 */
export async function injectReplayLeftOut(page: Page, asset: {id: number; name: string}): Promise<ReplayInjection> {
    const log: ReplayInjection = {edited: 0, problems: [], suggested: null};
    await page.route(RISK_QUERY, async (route) => {
        const request = riskRequestOf(route);
        const analytic = request?.analytics?.length === 1 ? request.analytics[0] : undefined;
        const parameters = analytic?.parameters;
        const range = isRecord(parameters) ? parameters.replay_range : null;
        if (request?.scope?.kind !== 'asset_set' || analytic?.analytic_code !== 'stress' || parameters?.method !== 'historical_replay' || !isRecord(range) || typeof range.start !== 'string') return route.fallback();
        const window = {start: range.start, end: typeof range.end === 'string' && range.end !== '' ? range.end : range.start};
        const response = await route.fetch({timeout: ANSWER_TIMEOUT});
        const body = await jsonOf(response);
        const item = riskItemsOf(body)?.[0];
        const problem = replayProblem(response, item, asset.id, window);
        if (problem !== null || !item) {
            log.problems.push(`${problem ?? 'no result'}: the replay went through unedited`);
            return route.fulfill({response});
        }
        const output = item.output as Json;
        const metadata = item.metadata as Json;
        const suggested = {start: shiftDay(window.start, LATE_LISTING_DAYS + 1), end: window.end};
        const edited: RiskItem = {
            ...item,
            status: 'partial',
            output: {...output, impacts: (output.impacts as unknown[]).filter((impact) => !isRecord(impact) || impact.asset_id !== asset.id)},
            metadata: {
                ...metadata,
                excluded_assets: [...(Array.isArray(metadata.excluded_assets) ? metadata.excluded_assets : []), {asset_id: asset.id, reason: 'historical_replay_starts_after_window_start'}],
                historical_replay_audit: {
                    ...(metadata.historical_replay_audit as Json),
                    excluded_count: 1,
                    excluded_assets: [{asset_id: asset.id, reason: 'starts_after_window_start', weight: null, treatment: 'omitted_from_replay'}],
                    excluded_weight_total: 0,
                    suggested_range: suggested,
                    suggested_range_recovers: [asset.id],
                },
            },
            warnings: [
                ...(item.warnings ?? []),
                {
                    code: 'historical_replay_assets_excluded',
                    message: 'Historical replay excluded assets that start quoting after the replay window begins.',
                    details: {asset_ids: [asset.id], treatment: 'omitted_from_replay', reason: 'starts_after_window_start'},
                    degrades_result: true,
                    message_i18n_key: 'risk.warnings.historical_replay_excluded_starts_late',
                    message_params: {treatment: 'omitted_from_replay', names: asset.name, count: 1},
                },
            ],
        };
        log.edited += 1;
        log.suggested = suggested;
        await fulfillWith(route, response, {...(body as Json), items: [edited]});
    });
    return log;
}
