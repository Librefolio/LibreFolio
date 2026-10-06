/**
 * Asset pages at phone width — K step 13, items 4 + 6a, 6b and 7 (developer's notes, 30/09).
 *
 * Written RED-FIRST, before the fixes. One describe block per defect, each with a control that
 * must stay green through the fix:
 *
 *   4 + 6a  AssetModal's footer is a single `justify-between` row that never wraps. Since the
 *           benchmark switch (18/09) it is wider than a phone: at 390 px Save sat at x 434–531
 *           (edit) and 434–503 (create), outside the viewport. Approved fix: the footer wraps —
 *           switches on one row, buttons right-aligned on the next — only when it has to.
 *           Control: at 1280 px the switches and the buttons still share one row.
 *   6b      The detail page derives "manual only" from `!providerAssignment`, and the assignment is
 *           null until GET /assets/provider/assignments answers: while it loads, every asset shows
 *           the blocked Sync (struck label, wrapped in a Tooltip), and PageToolbar's `*:w-full`
 *           widens the Tooltip wrapper instead of the button (107 px against 159 at 390). Approved
 *           fix: a "loaded" flag (disabled but plain while loading), the blocked look only for a
 *           manual asset once that is known, and the blocked button filling its cell.
 *   7       The detail tabs have no icon, and below `labelHideTabs` (370 px of bar) TabBar hides
 *           every label: two empty tabs. Approved fix (D6): lucide `LineChart` and `Shield` icons
 *           on the page, and a TabBar that never hides an icon-less label and names the button
 *           with `aria-label` when it does hide one (both pinned in `ui/tabs/TabBar.test.ts`).
 *           Note: TabBar already sets `title={tab.label}`, which accname uses as a last resort,
 *           so the accessible-name assertion below is expected green today; the icon is the red.
 *   16.1    (K step 16, item 1 — 06/10.) The price chart's tooltip at phone width: with a long asset
 *           name ECharts' tooltip box is wider than the chart, and the value is cut at the screen
 *           edge. Approved fix: truncate, never wrap — the label ellipsizes, the currency suffix and
 *           the value stay whole. Control: at 1280 px nothing is truncated. Last section of the file.
 *
 * Widths are set with `page.setViewportSize` inside each test, as the dashboard's F1 guard does,
 * so the spec means the same thing whichever project runs it; the runner runs `desktop`.
 *
 * Layout preconditions are read, not inferred. PageToolbar publishes its responsive state on
 * `window.__lfLayouts.assetDetail` (`layoutMode`, `showActionLabels`, `showTabLabels`): each phone
 * test first waits for the tier it is about — `oneColumn` with action labels for 6b, hidden tab
 * labels for 7 — so a threshold change fails here, by name, instead of quietly testing another
 * layout.
 *
 * Ownership. Every asset is created by the test that uses it, under a unique name, and deleted by
 * the `owned` fixture by id, once the routes are detached and the page has left it. Assets are
 * global rows: nothing here reads, counts or touches anyone else's. The create-mode form is filled
 * and never saved.
 *
 * Offline. The provider-priced asset of 6b is assigned `mockprov` with `INVALID_TICKER_12345`, the
 * one identifier the mock refuses for a current price, so the page's live-price poll — and any
 * neighbour polling /assets — writes nothing back. No test here presses Sync.
 *
 * Deliberately not asserted:
 *   - translated text: only test ids, roles, attributes, geometry and computed style;
 *   - that the manual-only tooltip does not open while loading. It opens on hover after a delay,
 *     so "it did not open" has no presence barrier; the plain, unstruck button stands in for it.
 */

import {expect, test as base, type Locator, type Page} from '../fixtures/playwright';
import {login, navigateTo} from '../fixtures/auth-helpers';
import {daysAgoIso} from '../fixtures/dates';
import {TEST_USER} from '../fixtures/test-users';
import {uniqueSuffix} from '../fixtures/unique';
import {schemas} from '../../src/lib/api/generated';
import {goToAssetDetailPage, goToAssetsPage, openCreateAssetModal, openEditAssetModal} from './assets-helpers';

const API = '/api/v1';
const ASSIGNMENTS_PATH = `${API}/assets/provider/assignments`;
/** mockprov.get_current_value raises NOT_FOUND for exactly this identifier: nothing is written back. */
const OFFLINE_IDENTIFIER = 'INVALID_TICKER_12345';

type Viewport = {width: number; height: number};
const PHONE_390: Viewport = {width: 390, height: 844};
const PHONE_360: Viewport = {width: 360, height: 800};
const PHONES: readonly Viewport[] = [PHONE_390, PHONE_360];
const DESKTOP: Viewport = {width: 1280, height: 720};

/** Layout boxes are fractional: "inside the viewport" allows half a pixel of rounding. */
const EDGE_TOLERANCE_PX = 0.5;
/** "As wide as its sibling", ±1 px. */
const WIDTH_TOLERANCE_PX = 1;

/** Left to right as rendered today: the two switches, then Cancel and Save. */
const FOOTER_CONTROLS = ['asset-active-toggle', 'asset-benchmark-toggle', 'asset-modal-cancel', 'asset-modal-save'] as const;
const DETAIL_TABS = ['asset-detail-tab-overview', 'asset-detail-tab-risk'] as const;

type Mode = 'create' | 'edit';
const MODES: readonly Mode[] = ['create', 'edit'];

type Owned = {assetIds: number[]};
type Box = {x: number; y: number; width: number; height: number};
type HttpResponse = {ok(): boolean; status(): number; text(): Promise<string>; json(): Promise<unknown>};
type LayoutState = {layoutMode: string; showActionLabels: boolean; showTabLabels: boolean};

async function jsonFrom<T>(response: HttpResponse, purpose: string): Promise<T> {
    expect(response.ok(), `${purpose}: HTTP ${response.status()} ${await response.text()}`).toBeTruthy();
    return (await response.json()) as T;
}

/**
 * Delete what the test created, each step scoped to an id it recorded.
 *
 * Routes go first: a test that fails while the assignment is held never resumes that handler,
 * and `ignoreErrors` detaches it instead of waiting on it. The page then leaves the asset, so no
 * poll or reload reads it while it goes. `page.request` shares the browser's session.
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
            const body = await jsonFrom<{results: Array<{asset_id: number; success: boolean; message?: string | null}>}>(await page.request.delete(`${API}/assets?asset_ids=${assetId}`), 'delete the owned asset');
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

// Login, API seeding, a full page load at phone width and the fixture's cleanup share the budget.
test.setTimeout(60_000);

test.beforeEach(async ({page}) => {
    await login(page, TEST_USER);
});

// =============================================================================
// Seeding
// =============================================================================

/** A plain EUR stock with no provider — "manual" until a test assigns one. */
async function createOwnedAsset(page: Page, owned: Owned, label: string): Promise<number> {
    const displayName = `${label} ${uniqueSuffix()}`;
    const item = schemas.FAAssetCreateItem.parse({display_name: displayName, currency: 'EUR', asset_type: 'STOCK', active: true});
    const body = await jsonFrom<{results: Array<{asset_id?: number | null; display_name: string; success: boolean; message?: string}>}>(await page.request.post(`${API}/assets`, {data: [item]}), 'create the owned asset');
    const created = body.results.find((result) => result.display_name === displayName);
    if (typeof created?.asset_id === 'number') owned.assetIds.push(created.asset_id);
    if (!created?.success || typeof created.asset_id !== 'number') throw new Error(`Asset creation failed: ${JSON.stringify(body)}`);
    return created.asset_id;
}

/** The provider codes the backend holds for this asset, read straight from the API. */
async function assignedProviders(page: Page, assetId: number): Promise<string[]> {
    const items = await jsonFrom<Array<{asset_id: number; provider_code: string}>>(await page.request.get(`${ASSIGNMENTS_PATH}?asset_ids=${assetId}`), 'read the provider assignment back');
    return items.filter((item) => item.asset_id === assetId).map((item) => item.provider_code);
}

async function assignOfflineMockProvider(page: Page, assetId: number): Promise<void> {
    const item = schemas.FAProviderAssignmentItem.parse({asset_id: assetId, provider_code: 'mockprov', identifier: OFFLINE_IDENTIFIER, identifier_type: 'TICKER', provider_params: null});
    const body = await jsonFrom<{results: Array<{asset_id: number; success: boolean; message?: string}>}>(await page.request.post(`${API}/assets/provider`, {data: [item]}), 'assign the offline mock provider');
    expect(body.results.find((result) => result.asset_id === assetId)?.success, `mockprov assigned: ${JSON.stringify(body)}`).toBe(true);
}

// =============================================================================
// Probes
// =============================================================================

/** PageToolbar's responsive state for the asset detail page, or null before it registers. */
async function assetDetailLayout(page: Page): Promise<LayoutState | null> {
    return page.evaluate(() => {
        const registry = (window as unknown as {__lfLayouts?: Record<string, {layoutMode?: unknown; showActionLabels?: unknown; showTabLabels?: unknown} | undefined>}).__lfLayouts;
        const layout = registry?.assetDetail;
        if (!layout) return null;
        return {layoutMode: String(layout.layoutMode), showActionLabels: layout.showActionLabels === true, showTabLabels: layout.showTabLabels === true};
    });
}

/** Precondition of 6b: the compact tier, where the actions are a labelled 2×2 grid under the filters. */
async function expectCompactActionGrid(page: Page): Promise<void> {
    await expect
        .poll(
            async () => {
                const layout = await assetDetailLayout(page);
                return layout && {layoutMode: layout.layoutMode, showActionLabels: layout.showActionLabels};
            },
            {message: 'precondition: at 390 px the asset detail toolbar is in its `oneColumn` tier — the 2×2 action grid under the filters — with action labels shown (window.__lfLayouts.assetDetail)', timeout: 10_000},
        )
        .toEqual({layoutMode: 'oneColumn', showActionLabels: true});
}

/** Precondition of 7: which side of `labelHideTabs` this width is on. */
async function expectTabLabelsShown(page: Page, shown: boolean): Promise<void> {
    await expect
        .poll(async () => (await assetDetailLayout(page))?.showTabLabels, {
            message: `precondition: PageToolbar ${shown ? 'shows' : 'hides'} the tab labels at this width (labelHideTabs, window.__lfLayouts.assetDetail)`,
            timeout: 10_000,
        })
        .toBe(shown);
}

/** Whether the element, or anything inside it, is drawn struck through — computed style, not a class name. */
async function isStruckThrough(target: Locator): Promise<boolean> {
    return target.evaluate((root) => [root, ...Array.from(root.querySelectorAll('*'))].some((node) => getComputedStyle(node).textDecorationLine.includes('line-through')));
}

/** A retryable check that Sync is as wide as Refresh, naming both widths when it is not. */
function sameWidth(sync: Locator, refresh: Locator, why: string): () => Promise<void> {
    return async () => {
        const [a, b] = await Promise.all([sync.boundingBox(), refresh.boundingBox()]);
        if (!a || !b) throw new Error(`${why}: both buttons must be laid out to be compared`);
        expect(Math.abs(a.width - b.width), `${why} — Sync ${a.width.toFixed(1)} px, Refresh ${b.width.toFixed(1)} px`).toBeLessThanOrEqual(WIDTH_TOLERANCE_PX);
    };
}

/** The text a user can actually see: `innerText` skips `display: none`, `textContent` does not. */
async function visibleText(target: Locator): Promise<string> {
    return target.evaluate((element) => (element as HTMLElement).innerText.trim());
}

/** Horizontal scroll of the page and of every ancestor of `target`, summed. */
async function sidewaysScroll(target: Locator): Promise<number> {
    return target.evaluate((element) => {
        let total = Math.abs(window.scrollX);
        for (let node = element.parentElement; node; node = node.parentElement) total += Math.abs(node.scrollLeft);
        return total;
    });
}

// =============================================================================
// Items 4 + 6a — AssetModal footer
// =============================================================================

/**
 * Open the modal in `mode` and bring it to the state where Save is enabled.
 *
 * Create: the assets page's own add-asset flow. Save stays disabled on an empty form and a trial
 * click refuses a disabled control, so a display name — the minimum that enables Save — is filled.
 * It is never saved. Edit: an asset this test owns, from its detail page.
 */
async function openAssetModal(page: Page, owned: Owned, mode: Mode): Promise<void> {
    if (mode === 'create') {
        await goToAssetsPage(page);
        await openCreateAssetModal(page);
    } else {
        const assetId = await createOwnedAsset(page, owned, 'E2E mobile footer');
        await goToAssetDetailPage(page, String(assetId));
        await openEditAssetModal(page);
    }
    await expect(page.getByTestId('asset-modal-form'), 'the modal has populated its form and taken its opening snapshot').toHaveAttribute('data-snapshot-ready', 'true');
    const name = page.getByTestId('asset-modal-display-name');
    if (mode === 'create') {
        const draft = `E2E mobile footer draft ${uniqueSuffix()}`;
        await name.fill(draft);
        await expect(name).toHaveValue(draft);
    } else {
        await expect(name, 'the edit form carries the owned asset').not.toHaveValue('');
    }
    await expect(page.getByTestId('asset-modal-save')).toBeEnabled();
}

/**
 * Every footer control is inside the viewport, got there without a sideways scroll, and is not
 * covered by anything.
 */
async function expectFooterReachable(page: Page): Promise<void> {
    const viewport = page.viewportSize();
    if (!viewport) throw new Error('setViewportSize() must run before the footer is measured');
    const modal = page.getByTestId('asset-modal');
    const controls = FOOTER_CONTROLS.map((testId) => ({testId, locator: modal.getByTestId(testId)}));

    for (const {locator} of controls) {
        await expect(locator).toBeVisible();
        await locator.scrollIntoViewIfNeeded({timeout: 5_000});
    }

    // 1. Inside the viewport, horizontally: every offender named with its edges, not just the first.
    await expect(async () => {
        const offenders: string[] = [];
        for (const {testId, locator} of controls) {
            const box = await locator.boundingBox();
            if (!box) {
                offenders.push(`${testId}: not laid out`);
                continue;
            }
            const left = box.x;
            const right = box.x + box.width;
            if (left < -EDGE_TOLERANCE_PX || right > viewport.width + EDGE_TOLERANCE_PX) offenders.push(`${testId}: x ${left.toFixed(0)}–${right.toFixed(0)} px`);
        }
        expect(offenders, `footer controls outside the ${viewport.width} px viewport`).toEqual([]);
    }).toPass({timeout: 5_000});

    // 2. Not bought with a sideways scroll: scrollIntoViewIfNeeded() scrolls any scroll container
    //    it meets, and a footer that only fits once something slides sideways does not fit.
    for (const {testId, locator} of controls) {
        expect(await sidewaysScroll(locator), `${testId}: reached without scrolling anything sideways`).toBe(0);
    }

    // 3. Not covered: a trial click runs every actionability check — visible, stable, enabled, and
    //    the hit target at its centre is the control itself — and clicks nothing.
    for (const {locator} of controls) {
        await locator.click({trial: true, timeout: 5_000});
    }
}

/** Control: at desktop width the switches and the buttons still share one line, buttons on the right. */
async function expectFooterOnOneRow(page: Page): Promise<void> {
    const modal = page.getByTestId('asset-modal');
    const [active, benchmark, cancel, save] = FOOTER_CONTROLS.map((testId) => modal.getByTestId(testId));
    const shareLine = (a: Box, b: Box) => a.y < b.y + b.height && b.y < a.y + a.height;
    await expect(async () => {
        const [a, b, c, s] = await Promise.all([active, benchmark, cancel, save].map((locator) => locator.boundingBox()));
        if (!a || !b || !c || !s) throw new Error('every footer control must be laid out');
        expect(shareLine(a, s) && shareLine(b, c), `one row: Active switch y ${a.y.toFixed(0)}–${(a.y + a.height).toFixed(0)}, Save y ${s.y.toFixed(0)}–${(s.y + s.height).toFixed(0)}`).toBe(true);
        expect(c.x, 'the buttons stay to the right of the switches').toBeGreaterThan(b.x + b.width);
    }).toPass({timeout: 5_000});
}

test.describe('Asset modal footer at phone width — Save, Cancel and the switches stay reachable (items 4 + 6a)', () => {
    for (const mode of MODES) {
        for (const viewport of PHONES) {
            test(`${mode} mode at ${viewport.width}×${viewport.height}: switches, Cancel and Save are inside the viewport and not covered`, async ({page, owned}) => {
                await page.setViewportSize(viewport);
                await openAssetModal(page, owned, mode);
                await expectFooterReachable(page);
            });
        }

        test(`${mode} mode at ${DESKTOP.width}×${DESKTOP.height} (control): the footer stays on one row — the fix wraps only when it has to`, async ({page, owned}) => {
            await page.setViewportSize(DESKTOP);
            await openAssetModal(page, owned, mode);
            await expectFooterOnOneRow(page);
            await expectFooterReachable(page);
        });
    }
});

// =============================================================================
// Item 6b — Sync while the provider assignment loads
// =============================================================================

type HeldRoute = {release: () => void};

/**
 * Hold every GET /assets/provider/assignments until `release()`: the window in which the page
 * knows the asset but not yet its provider. The held request then goes to the real backend
 * (`route.continue`), so what the page finally receives is the genuine assignment.
 */
async function holdProviderAssignments(page: Page): Promise<HeldRoute> {
    let open: () => void = () => undefined;
    const gate = new Promise<void>((resolve) => {
        open = resolve;
    });
    await page.route('**/api/v1/assets/provider/assignments**', async (route) => {
        await gate;
        await route.continue();
    });
    return {release: () => open()};
}

test.describe('Asset detail at 390 px — Sync while the provider assignment loads (item 6b)', () => {
    test('provider-priced asset: while the assignment is pending Sync is disabled but plain — not struck, as wide as Refresh — and enabled once it lands', async ({page, owned}) => {
        const assetId = await createOwnedAsset(page, owned, 'E2E sync while loading');
        await assignOfflineMockProvider(page, assetId);
        expect(await assignedProviders(page, assetId), 'precondition: the asset HAS a provider assignment').toEqual(['mockprov']);

        await page.setViewportSize(PHONE_390);
        const held = await holdProviderAssignments(page);
        const requested = page.waitForRequest((request) => new URL(request.url()).pathname === ASSIGNMENTS_PATH, {timeout: 15_000});
        await navigateTo(page, `/assets/${assetId}`);
        await requested;

        await expect(page.getByTestId('asset-detail-page'), 'precondition: still loading — the assignment is held').toHaveAttribute('data-busy', 'true');
        await expectCompactActionGrid(page);
        const toolbar = page.getByTestId('asset-detail-controls');
        const sync = toolbar.getByTestId('asset-detail-sync-btn');
        const refresh = toolbar.getByTestId('asset-detail-refresh-btn');
        await expect(sync).toBeVisible();
        await expect(refresh).toBeVisible();

        // Accepted by the developer: Sync cannot run before the page knows the provider.
        await expect(sync, 'Sync waits for the provider assignment').toBeDisabled();
        // Presence barrier for the strike check below: Sync shows a label, so "not struck" is
        // about a real label rather than an empty button.
        await expect.poll(() => visibleText(sync), {message: 'while loading, Sync keeps its label'}).not.toBe('');
        // The two defects, reported together: loading is not "manual only".
        expect.soft(await isStruckThrough(sync), 'while loading, Sync must not wear the manual-only strike-through').toBe(false);
        await expect.soft(sameWidth(sync, refresh, 'while loading, Sync fills its toolbar cell like Refresh')).toPass({timeout: 5_000});

        held.release();
        await expect(sync, 'the assignment has landed and names a provider: Sync is usable').toBeEnabled({timeout: 20_000});
        // Positive controls for both probes: the plain, loaded button is neither struck nor narrow.
        expect(await isStruckThrough(sync), 'loaded, provider-priced: no strike-through').toBe(false);
        await expect(sameWidth(sync, refresh, 'loaded, provider-priced: Sync fills its cell')).toPass({timeout: 5_000});
    });

    test("manual asset: once loaded, Sync keeps today's blocked look — disabled, struck through — and fills its cell like Refresh", async ({page, owned}) => {
        const assetId = await createOwnedAsset(page, owned, 'E2E sync manual');
        expect(await assignedProviders(page, assetId), 'precondition: the asset has NO provider assignment').toEqual([]);

        await page.setViewportSize(PHONE_390);
        // `data-busy="false"` is the barrier: the (empty) assignment answer is in.
        await goToAssetDetailPage(page, String(assetId));
        await expectCompactActionGrid(page);
        const toolbar = page.getByTestId('asset-detail-controls');
        const sync = toolbar.getByTestId('asset-detail-sync-btn');
        const refresh = toolbar.getByTestId('asset-detail-refresh-btn');
        await expect(sync).toBeVisible();
        await expect(refresh).toBeVisible();

        await expect(sync, 'a manual asset has nothing to sync').toBeDisabled();
        // Kept on purpose — and the positive control proving the strike probe can see a strike.
        expect(await isStruckThrough(sync), 'manual only, now known: the struck-through label stays').toBe(true);
        await expect(sameWidth(sync, refresh, 'the blocked Sync fills its toolbar cell like Refresh — the button, not only the Tooltip around it')).toPass({timeout: 5_000});
    });
});

// =============================================================================
// Item 7 — asset detail tabs at phone width
// =============================================================================

test.describe('Asset detail tabs at phone width — never an empty tab (item 7)', () => {
    for (const viewport of PHONES) {
        test(`${viewport.width}×${viewport.height}: with the labels hidden, each tab shows its icon and keeps a non-empty accessible name`, async ({page, owned}) => {
            const assetId = await createOwnedAsset(page, owned, 'E2E mobile tabs');
            await page.setViewportSize(viewport);
            await goToAssetDetailPage(page, String(assetId));
            await expectTabLabelsShown(page, false);

            const controls = page.getByTestId('asset-detail-controls');
            for (const testId of DETAIL_TABS) {
                const tab = controls.getByTestId(testId);
                await expect(tab).toBeVisible();
                await expect.soft(tab, `${testId}: a tab without its visible label still needs a name`).toHaveAccessibleName(/\S/);
                await expect.soft(tab.locator('svg'), `${testId}: with the label hidden, the icon is all there is to see`).toBeVisible();
            }
        });
    }

    test(`${DESKTOP.width}×${DESKTOP.height} (control): both tab labels are visible`, async ({page, owned}) => {
        const assetId = await createOwnedAsset(page, owned, 'E2E desktop tabs');
        await page.setViewportSize(DESKTOP);
        await goToAssetDetailPage(page, String(assetId));
        await expectTabLabelsShown(page, true);

        const controls = page.getByTestId('asset-detail-controls');
        for (const testId of DETAIL_TABS) {
            const tab = controls.getByTestId(testId);
            await expect(tab).toBeVisible();
            await expect.poll(() => visibleText(tab), {message: `${testId}: its label is on screen`}).not.toBe('');
            await expect(tab).toHaveAccessibleName(/\S/);
        }
    });
});

// =============================================================================
// Step 16, item 1 — the price chart's tooltip at phone width
// =============================================================================

/*
 * The defect (measured by K on 06/10). The asset detail's price chart — PriceChartFull, line mode — shows an
 * ECharts tooltip: `trigger: 'axis'`, `confine: true`, placed by `tooltipPositionSide`. Each series is one line,
 * `label: value`; the main series' label is 👑, the type icon, the name cut at 30 characters (`truncateName`) and
 * `(flag CUR)`, and the delta from the first visible point follows on the same line. ECharts' box is
 * `white-space: nowrap`, so it is as wide as that line: with 55–58-character names, 362–386 px on a chart 309 px
 * wide at a 390 px viewport (279 at 360). `confine` pins it to the chart's left edge and it runs 20–44 px past the
 * screen at 390, 50–74 at 360, the value cut at the edge. Candles and Rolling Return stay inside: not in scope.
 *
 * Approved cure (developer, 06/10): truncate, never wrap. The tooltip is capped at the chart's width
 * (`fitTooltipToWidth`), each row's label shrinks with an ellipsis, and the currency suffix and the value always
 * stay whole (`buildFittedTooltipRow`); the two helpers' contract is pinned in `echartsTooltipHelpers.test.ts`.
 * Control: at 1280 px nothing is truncated — the cure cuts only when there is no room. It asks every box that
 * clips around the name — the row's label span, and the name span `signalLabelToHtml` builds inside it, which
 * carries its own ellipsis — since the user cannot tell one ellipsis from the other.
 *
 * The subject is the test's own ETF: a realistic name padded to 58 characters by a unique tail, priced by
 * mockprov under the identifier the mock refuses to quote, with a month of daily closes up to today. POST
 * /assets/prices/current is answered empty, so nothing live is written and the summary shows the last stored
 * close. The `owned` fixture deletes the asset by id — its prices and its provider assignment go with it.
 *
 * The measure. The mouse rests on the middle of the plot; the tooltip is the visible box ECharts appends to the
 * chart host, the one whose inline style carries `z-index: 9999999`. ECharts slides it to each position with a CSS
 * transform transition, so it is read once its box is the same over two animation frames and nothing animates
 * on it. Then, inside the page:
 *   - the box against the layout: left ≥ −1 and right ≤ the right of <html>'s box + 1. Not clientWidth: headless
 *     Chromium hides the scrollbar but keeps its gutter (`scrollbar-gutter: stable`, 15 px on the developer's
 *     Mac), and clientWidth counts the hidden gutter as room;
 *   - text runs, through a DOM Range on the text nodes. The main row is found by the asset's name; the first
 *     `(… EUR)` after it is its currency suffix, and the first `-?\d+\.\d{4}` after it its value — with the `%`
 *     glued to it, since the page opens in its percentage view (`6.6179%`), and a value whose unit is cut is not
 *     whole. A run is whole when it lies inside the tooltip box, the layout and the padding box of every ancestor
 *     that clips horizontally (overflow other than visible): a Range measures the text an ellipsis hides, so a
 *     suffix eaten by one counts as cut, wherever the box is.
 * Every number goes into the failure message. The absence assertions have a positive control: a row-shaped box
 * hung 40 px past the layout's right edge — the value at its end, the suffix inside a 20 px ellipsis — which the
 * same reader must report as all three, and which is removed whatever happens. The phone assertions are soft, so
 * one run reports the box, the value and the suffix together.
 */

const TOOLTIP_PHONES: readonly Viewport[] = [
    {width: 390, height: 844},
    {width: 360, height: 780},
];
const TOOLTIP_DESKTOP: Viewport = {width: 1280, height: 900};
/** A realistic ETF name; a unique tail pads it to exactly TOOLTIP_NAME_CHARS (display_name is unique). */
const TOOLTIP_NAME_HEAD = 'Xtrackers MSCI World Industrials UCITS ETF 1C';
const TOOLTIP_NAME_CHARS = 58;
/** truncateName keeps a label's first 29 characters: the main row is found by fewer than that. */
const TOOLTIP_NAME_KEY_CHARS = 20;
const TOOLTIP_CURRENCY = 'EUR';
/** Daily closes up to today: at least two points in any window the page opens with. */
const TOOLTIP_PRICE_DAYS = 30;
/** ECharts' HTML tooltip box writes this z-index into its inline style; Chromium serialises it with a space. */
const ECHARTS_TOOLTIP = 'div[style*="z-index: 9999999"], div[style*="z-index:9999999"]';
/** Box and text edges are fractional and ECharts rounds its translate: within 1 px is inside. */
const TOOLTIP_EDGE_PX = 1;
/** The positive control: a row-shaped box hung this far past the layout's right edge… */
const TOOLTIP_PROBE_ID = 'lf-k16-tooltip-probe';
const TOOLTIP_PROBE_PAST_PX = 40;
/** …with its currency suffix inside an ellipsizing span narrower than the suffix. */
const TOOLTIP_PROBE_CLIP_PX = 20;

type HorizontalSpan = {left: number; right: number; width: number};

/** One text run of a tooltip. Crosses `evaluate`: plain data only. */
interface TextRun {
    text: string;
    left: number;
    right: number;
    /** Where the run can be seen: the tooltip box ∩ the layout ∩ the padding box of every ancestor that clips horizontally. */
    seenLeft: number;
    seenRight: number;
    /** What sets each edge of that span. */
    leftEdge: string;
    rightEdge: string;
}

/** An element between the name's text and the tooltip box that clips its content horizontally. */
interface Clipper {
    element: string;
    scrollWidth: number;
    clientWidth: number;
    textOverflow: string;
}

interface TooltipReading {
    box: HorizontalSpan;
    /** What the tooltip is laid out in: ECharts' host, the chart (the body, for the probe). */
    host: HorizontalSpan;
    /** <html>'s box — the layout. Its right edge is the page's: a hidden scrollbar gutter is not room. */
    layout: HorizontalSpan;
    windowWidth: number;
    /** The chart's view (`data-view-mode` on the card): `percentage` writes the value with a `%`. Null for the probe. */
    view: string | null;
    text: string;
    /** The main row: the asset's name, then the first `(… CUR)` and the first `-?\d+\.\d{4}%?` after it. */
    name: TextRun | null;
    nameClippers: Clipper[];
    suffix: TextRun | null;
    value: TextRun | null;
}

interface TooltipKeys {
    namePrefix: string;
    currency: string;
}

interface PriceChart {
    /** `asset-detail-chart`: the card the chart and its tooltip live in. */
    card: Locator;
    /** The line chart's ECharts root: the element ECharts appends its tooltip box to. */
    host: Locator;
    displayName: string;
}

/** `Xtrackers MSCI World Industrials UCITS ETF 1C 0001234567ab` — 58 characters, the tail unique. */
function longEtfName(): string {
    const tail = uniqueSuffix().padStart(TOOLTIP_NAME_CHARS - TOOLTIP_NAME_HEAD.length - 1, '0');
    return `${TOOLTIP_NAME_HEAD} ${tail}`;
}

function tooltipKeys(displayName: string): TooltipKeys {
    return {namePrefix: displayName.slice(0, TOOLTIP_NAME_KEY_CHARS), currency: TOOLTIP_CURRENCY};
}

/** An EUR ETF of the test's own: the long name, mockprov under the offline identifier, a month of daily closes up to today. */
async function createLongNamedPricedEtf(page: Page, owned: Owned): Promise<{assetId: number; displayName: string}> {
    const displayName = longEtfName();
    expect(displayName.length, `the name is ${TOOLTIP_NAME_CHARS} characters, unique tail included: "${displayName}"`).toBe(TOOLTIP_NAME_CHARS);
    const item = schemas.FAAssetCreateItem.parse({display_name: displayName, currency: TOOLTIP_CURRENCY, asset_type: 'ETF', active: true});
    const body = await jsonFrom<{results: Array<{asset_id?: number | null; display_name: string; success: boolean; message?: string}>}>(await page.request.post(`${API}/assets`, {data: [item]}), 'create the long-named ETF');
    const created = body.results.find((result) => result.display_name === displayName);
    if (typeof created?.asset_id === 'number') owned.assetIds.push(created.asset_id);
    if (!created?.success || typeof created.asset_id !== 'number') throw new Error(`Asset creation failed: ${JSON.stringify(body)}`);
    const assetId = created.asset_id;

    await assignOfflineMockProvider(page, assetId);
    const prices = Array.from({length: TOOLTIP_PRICE_DAYS}, (_, i) => ({date: daysAgoIso(TOOLTIP_PRICE_DAYS - 1 - i), close: Number((61.5 + i * 0.37).toFixed(2)), currency: TOOLTIP_CURRENCY}));
    const upsert = schemas.FAUpsert.parse({asset_id: assetId, prices});
    const stored = await jsonFrom<{results: Array<{asset_id: number; count: number}>}>(await page.request.post(`${API}/assets/prices`, {data: [upsert]}), 'store a month of daily closes');
    expect(stored.results.find((result) => result.asset_id === assetId)?.count, 'every daily close is stored').toBe(prices.length);
    return {assetId, displayName};
}

/** The kinds of series the chart draws for this asset: line mode draws its own series as a line, candles mode as candles. */
async function seriesKinds(host: Locator, displayName: string): Promise<{line: boolean; candlestick: boolean}> {
    return host.evaluate((element, name) => {
        const option = (element as unknown as {__lfChart?: {getOption?: () => {series?: unknown}}}).__lfChart?.getOption?.();
        const series = option?.series;
        const list = Array.isArray(series) ? (series as Array<{type?: unknown; name?: unknown} | null>) : [];
        return {line: list.some((item) => item?.type === 'line' && item?.name === name), candlestick: list.some((item) => item?.type === 'candlestick')};
    }, displayName);
}

/** The asset's detail page at `viewport`, its price chart rendered in line mode, offline. */
async function openLongNamedPriceChart(page: Page, owned: Owned, viewport: Viewport): Promise<PriceChart> {
    const {assetId, displayName} = await createLongNamedPricedEtf(page, owned);
    // The page posts this on load and every 30 s: it asks the live providers and writes today's row. Answered
    // empty, nothing is written and the summary shows the last stored close. The fixture detaches the route.
    await page.route('**/api/v1/assets/prices/current', (route) => route.fulfill({json: {results: [], success_count: 0, errors: []}}));
    await page.setViewportSize(viewport);
    await goToAssetDetailPage(page, String(assetId));
    await expect(page.getByTestId('asset-detail-live-price'), 'precondition: the price summary shows a price — the stored closes are in the window').toBeVisible({timeout: 15_000});

    const card = page.getByTestId('asset-detail-chart');
    await expect(card, 'precondition: the price chart, not Rolling Return').toHaveAttribute('data-primary-mode', 'price');
    await expect(card, 'precondition: the chart has its series').toHaveAttribute('data-series-state', 'ready', {timeout: 15_000});
    // ECharts marks its root `_echarts_instance_`; chartReady adds `data-chart-ready` once a render has finished.
    const host = card.locator('[_echarts_instance_][data-chart-ready="true"]');
    await expect(host, 'precondition: one chart in the card, rendered').toHaveCount(1, {timeout: 15_000});
    await expect.poll(() => seriesKinds(host, displayName), {message: "precondition: line mode — the asset's own series is a line, and no candles are drawn", timeout: 10_000}).toEqual({line: true, candlestick: false});
    return {card, host, displayName};
}

/**
 * Resolves once the tooltip box has stopped moving — ECharts slides it with a CSS transform transition: the same
 * box over two animation frames, no animation running on it, every font loaded. Read frame by frame, no clock.
 */
async function waitForStableTooltip(tooltip: Locator, budgetMs: number): Promise<void> {
    const verdict = await tooltip.evaluate(
        (element, budget) =>
            new Promise<string>((resolve) => {
                const started = performance.now();
                let last = '';
                let same = 0;
                const frame = () => {
                    const rect = element.getBoundingClientRect();
                    const box = `${rect.left},${rect.top},${rect.width},${rect.height}`;
                    const animations = element.getAnimations().length;
                    same = animations === 0 && document.fonts.status === 'loaded' && box === last ? same + 1 : 0;
                    last = box;
                    if (same >= 2) {
                        resolve('');
                    } else if (performance.now() - started > budget) {
                        resolve(`still moving after ${Math.round(performance.now() - started)} ms: box ${box}, ${animations} animation(s) running, fonts ${document.fonts.status}`);
                    } else {
                        requestAnimationFrame(frame);
                    }
                };
                requestAnimationFrame(frame);
            }),
        budgetMs,
    );
    expect(verdict, 'the tooltip box settles: the same over two animation frames, no transition running').toBe('');
}

/** Rests the mouse on the middle of the plot and returns ECharts' tooltip box once it has settled there. */
async function showTooltip(chart: PriceChart): Promise<Locator> {
    const tooltip = chart.card.locator(ECHARTS_TOOLTIP).filter({visible: true});
    let nudge = 0;
    await expect(async () => {
        const box = await chart.host.boundingBox();
        if (!box) throw new Error('the chart host is not laid out');
        // `hover` scrolls the host into view and checks that the middle of the plot is the chart itself, not
        // something drawn over it. A retry moves one pixel, so that ECharts receives a fresh mousemove.
        await chart.host.hover({position: {x: box.width / 2 + (nudge++ % 2), y: box.height / 2}, timeout: 5_000});
        await expect(tooltip, 'one ECharts tooltip box is shown in the chart card').toHaveCount(1, {timeout: 2_000});
    }).toPass({timeout: 15_000});
    await waitForStableTooltip(tooltip, 5_000);
    return tooltip;
}

/**
 * Reads a tooltip-shaped box inside the page — ECharts' tooltip, or the positive control's probe, through the same
 * code. Serialised by `evaluate`, so it references nothing outside itself.
 */
function readTooltipInPage(root: Element, {namePrefix, currency}: TooltipKeys): TooltipReading {
    const span = (rect: DOMRect) => ({left: rect.left, right: rect.right, width: rect.width});
    const markup = (element: Element) => {
        const style = (element.getAttribute('style') ?? '').trim();
        return `<${element.tagName.toLowerCase()} style="${style.length > 80 ? `${style.slice(0, 80)}…` : style}">`;
    };
    const rootBox = root.getBoundingClientRect();
    const layoutBox = document.documentElement.getBoundingClientRect();

    // Every text node in document order, concatenated: a run is found in the text, then mapped back to its nodes.
    const segments: Array<{node: Text; start: number}> = [];
    let text = '';
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    for (let node = walker.nextNode(); node; node = walker.nextNode()) {
        segments.push({node: node as Text, start: text.length});
        text += (node as Text).data;
    }
    // The node a run starts in (the last one starting at or before it) and the one it ends in (the last one starting before it).
    const startingAt = (offset: number) => segments.filter((segment) => segment.start <= offset).at(-1) ?? segments[0];
    const endingAt = (offset: number) => segments.filter((segment) => segment.start < offset).at(-1) ?? segments[0];
    // Every element from `node` up to the body that clips horizontally: overflow other than visible, on a box it applies to.
    const clippersOf = (node: Node): Element[] => {
        const found: Element[] = [];
        for (let element = node.parentElement; element && element !== document.body && element !== document.documentElement; element = element.parentElement) {
            const style = getComputedStyle(element);
            if (style.overflowX !== 'visible' && style.display !== 'inline' && style.display !== 'contents') found.push(element);
        }
        return found;
    };
    const run = (start: number, end: number): TextRun => {
        const first = startingAt(start);
        const last = endingAt(end);
        const range = document.createRange();
        range.setStart(first.node, start - first.start);
        range.setEnd(last.node, end - last.start);
        const box = range.getBoundingClientRect();
        let seenLeft = rootBox.left;
        let leftEdge = 'the tooltip box';
        let seenRight = rootBox.right;
        let rightEdge = 'the tooltip box';
        if (Math.max(layoutBox.left, 0) > seenLeft) {
            seenLeft = Math.max(layoutBox.left, 0);
            leftEdge = "the layout's left edge";
        }
        if (layoutBox.right < seenRight) {
            seenRight = layoutBox.right;
            rightEdge = "the layout's right edge (<html>'s box)";
        }
        for (const element of new Set([...clippersOf(first.node), ...clippersOf(last.node)])) {
            const clip = element.getBoundingClientRect();
            const paddingLeft = clip.left + element.clientLeft;
            const paddingRight = paddingLeft + element.clientWidth;
            if (paddingLeft > seenLeft) {
                seenLeft = paddingLeft;
                leftEdge = `the clipping ${markup(element)}`;
            }
            if (paddingRight < seenRight) {
                seenRight = paddingRight;
                rightEdge = `the clipping ${markup(element)}`;
            }
        }
        return {text: text.slice(start, end), left: box.left, right: box.right, seenLeft, seenRight, leftEdge, rightEdge};
    };

    const reading: TooltipReading = {
        box: span(rootBox),
        host: span((root.parentElement ?? document.body).getBoundingClientRect()),
        layout: span(layoutBox),
        windowWidth: window.innerWidth,
        view: root.closest('[data-view-mode]')?.getAttribute('data-view-mode') ?? null,
        text,
        name: null,
        nameClippers: [],
        suffix: null,
        value: null,
    };
    const nameAt = text.indexOf(namePrefix);
    if (nameAt < 0) return reading;
    // From the name to the end of its text node: what the label shows, cut at 30 characters or not.
    const nameNode = startingAt(nameAt);
    reading.name = run(nameAt, nameNode.start + nameNode.node.data.length);
    reading.nameClippers = clippersOf(nameNode.node)
        .filter((element) => root.contains(element))
        .map((element) => ({element: markup(element), scrollWidth: element.scrollWidth, clientWidth: element.clientWidth, textOverflow: getComputedStyle(element).textOverflow}));
    const after = nameAt + namePrefix.length;
    const rest = text.slice(after);
    const suffix = new RegExp(`\\([^()]*\\b${currency}\\)`).exec(rest);
    if (suffix) reading.suffix = run(after + suffix.index, after + suffix.index + suffix[0].length);
    const value = /-?\d+\.\d{4}%?/.exec(rest);
    if (value) reading.value = run(after + value.index, after + value.index + value[0].length);
    return reading;
}

function px(value: number): string {
    return `${value.toFixed(1)} px`;
}

/** How much of a run cannot be seen, px: what sticks out of its visible span, on either side. */
function hiddenPx(run: TextRun): number {
    return Math.max(run.seenLeft - run.left, run.right - run.seenRight, 0);
}

function boxReport(reading: TooltipReading): string {
    const {box, host, layout} = reading;
    return `tooltip box x ${px(box.left)} → ${px(box.right)} (${px(box.width)} wide), laid out in x ${px(host.left)} → ${px(host.right)} (${px(host.width)} wide); the layout — <html>'s box — x ${px(layout.left)} → ${px(layout.right)}, window ${reading.windowWidth} px; view ${reading.view ?? 'n/a'}`;
}

function runReport(what: string, run: TextRun): string {
    return `${what} "${run.text}" at x ${px(run.left)} → ${px(run.right)}, visible within x ${px(run.seenLeft)} → ${px(run.seenRight)} (left edge: ${run.leftEdge}; right edge: ${run.rightEdge}): ${px(hiddenPx(run))} of it cannot be seen`;
}

function clipperReport(clipper: Clipper): string {
    return `${clipper.element} scrollWidth ${clipper.scrollWidth} / clientWidth ${clipper.clientWidth} (text-overflow: ${clipper.textOverflow})`;
}

/** The presence barrier of every assertion on the main row: the reader found its name, its currency suffix and its value. */
function mainRow(reading: TooltipReading, where: string): {name: TextRun; suffix: TextRun; value: TextRun} {
    const {name, suffix, value} = reading;
    if (!name || !suffix || !value) {
        throw new Error(`${where}: the main row was not found — name ${name ? 'found' : 'missing'}, (… ${TOOLTIP_CURRENCY}) ${suffix ? 'found' : 'missing'}, value ${value ? 'found' : 'missing'}. Text: "${reading.text}"`);
    }
    return {name, suffix, value};
}

async function readTooltip(tooltip: Locator, displayName: string): Promise<TooltipReading> {
    return tooltip.evaluate(readTooltipInPage, tooltipKeys(displayName));
}

/**
 * The positive control of the absence assertions: a box shaped like the main row — the name, `(🇪🇺 EUR)` inside a
 * TOOLTIP_PROBE_CLIP_PX ellipsis, the value at its end — hung TOOLTIP_PROBE_PAST_PX past the layout's right edge. The
 * same reader must report the box past the layout, the value cut by the layout's edge and the suffix cut by its
 * ellipsis. Removed whatever happens.
 */
async function proveTheReaderSeesCuts(page: Page, displayName: string): Promise<void> {
    const keys = tooltipKeys(displayName);
    try {
        await page.evaluate(
            ({id, name, currency, past, clip}) => {
                const probe = document.createElement('div');
                probe.id = id;
                probe.style.cssText = 'position:fixed;top:0;left:0;z-index:2147483647;white-space:nowrap;padding:4px;font:12px sans-serif;background:#fff';
                const label = document.createElement('span');
                label.textContent = `${name} probe…`;
                const suffix = document.createElement('span');
                suffix.style.cssText = `display:inline-block;max-width:${clip}px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;vertical-align:bottom`;
                suffix.textContent = `(🇪🇺 ${currency})`;
                probe.append(label, ' ', suffix, ': 12.3456');
                document.body.append(probe);
                const layoutRight = document.documentElement.getBoundingClientRect().right;
                probe.style.left = `${layoutRight + past - probe.getBoundingClientRect().width}px`;
            },
            {id: TOOLTIP_PROBE_ID, name: keys.namePrefix, currency: keys.currency, past: TOOLTIP_PROBE_PAST_PX, clip: TOOLTIP_PROBE_CLIP_PX},
        );
        const probe = await page.locator(`#${TOOLTIP_PROBE_ID}`).evaluate(readTooltipInPage, keys);
        const {suffix, value} = mainRow(probe, 'positive control');
        expect(Math.abs(probe.box.right - probe.layout.right - TOOLTIP_PROBE_PAST_PX), `positive control: the reader sees the probe box ${TOOLTIP_PROBE_PAST_PX} px past the layout's right edge — ${boxReport(probe)}`).toBeLessThanOrEqual(TOOLTIP_EDGE_PX);
        expect(hiddenPx(value), `positive control: the probe's value, past the layout, is reported cut — ${runReport('value', value)}`).toBeGreaterThan(TOOLTIP_EDGE_PX);
        expect(hiddenPx(suffix), `positive control: the probe's suffix, inside a ${TOOLTIP_PROBE_CLIP_PX} px ellipsis, is reported cut — ${runReport('suffix', suffix)}`).toBeGreaterThan(TOOLTIP_EDGE_PX);
    } finally {
        await page.evaluate((id) => document.getElementById(id)?.remove(), TOOLTIP_PROBE_ID);
    }
}

test.describe('Price chart tooltip at phone width — the asset name never pushes the value off-screen (K step 16, item 1)', () => {
    for (const viewport of TOOLTIP_PHONES) {
        test(`${viewport.width}×${viewport.height}: the tooltip box stays inside the layout, and the main row's value and currency suffix stay whole`, async ({page, owned}) => {
            const chart = await openLongNamedPriceChart(page, owned, viewport);
            const reading = await readTooltip(await showTooltip(chart), chart.displayName);
            const {suffix, value} = mainRow(reading, `the tooltip at ${viewport.width} px`);

            // 1. The box, against the layout's edges.
            expect.soft(-reading.box.left, `the tooltip box starts at x ${px(reading.box.left)}, left of the viewport — ${boxReport(reading)}`).toBeLessThanOrEqual(TOOLTIP_EDGE_PX);
            expect.soft(reading.box.right - reading.layout.right, `the tooltip box ends ${px(reading.box.right - reading.layout.right)} past the layout's right edge — ${boxReport(reading)}`).toBeLessThanOrEqual(TOOLTIP_EDGE_PX);
            // 2. The main series' value, whole and on screen.
            expect.soft(hiddenPx(value), runReport("the main row's value", value)).toBeLessThanOrEqual(TOOLTIP_EDGE_PX);
            // 3. Its currency suffix, whole and on screen.
            expect.soft(hiddenPx(suffix), runReport("the main row's currency suffix", suffix)).toBeLessThanOrEqual(TOOLTIP_EDGE_PX);
            // 4. The same reader reports a row the test pushes past the layout: the three absences above can fail.
            await proveTheReaderSeesCuts(page, chart.displayName);
        });
    }

    test(`${TOOLTIP_DESKTOP.width}×${TOOLTIP_DESKTOP.height} (control): the tooltip opens inside the layout and nothing clips the main label — the cure truncates only when there is no room`, async ({page, owned}) => {
        const chart = await openLongNamedPriceChart(page, owned, TOOLTIP_DESKTOP);
        const reading = await readTooltip(await showTooltip(chart), chart.displayName);
        const {suffix, value} = mainRow(reading, `the tooltip at ${TOOLTIP_DESKTOP.width} px`);

        expect(-reading.box.left, `the tooltip box starts inside the viewport — ${boxReport(reading)}`).toBeLessThanOrEqual(TOOLTIP_EDGE_PX);
        expect(reading.box.right - reading.layout.right, `the tooltip box ends inside the layout — ${boxReport(reading)}`).toBeLessThanOrEqual(TOOLTIP_EDGE_PX);
        // Every ellipsizing box around the name — the label's own, and any inside it — shows all of its content.
        const clipped = reading.nameClippers.filter((clipper) => clipper.scrollWidth > clipper.clientWidth + TOOLTIP_EDGE_PX);
        expect(clipped.map(clipperReport), `with room to spare nothing truncates the name "${reading.name?.text}": ${reading.nameClippers.length} clipping box(es) around it — ${reading.nameClippers.map(clipperReport).join('; ') || 'none'}`).toEqual([]);
        expect(hiddenPx(value), runReport("the main row's value", value)).toBeLessThanOrEqual(TOOLTIP_EDGE_PX);
        expect(hiddenPx(suffix), runReport("the main row's currency suffix", suffix)).toBeLessThanOrEqual(TOOLTIP_EDGE_PX);
    });
});
