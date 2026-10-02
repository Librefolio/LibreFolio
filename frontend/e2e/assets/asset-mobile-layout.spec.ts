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
