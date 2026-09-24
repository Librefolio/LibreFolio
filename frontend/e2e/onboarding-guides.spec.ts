/**
 * Onboarding round 8, checkpoint C4 — every contextual guide against its real page.
 *
 * T11  Each of the nine contextual flows (broker, FX, asset × page, Add modal,
 *      detail) is reached through its real trigger and walked with Next. At every
 *      step the coachmark (OnboardingCoachmark.svelte) must publish the catalog
 *      step (onboardingGuideCatalog.ts, catalog order), `data-guide-state="anchored"`
 *      and `data-geometry-state="stable"` in one atomic reading, while exactly one
 *      element other than its own panel names `onboarding-coachmark-description`:
 *      the target the host presentation (OnboardingOverlayHost.svelte) resolves
 *      that step's anchor to. After the last step the coachmark closes and the
 *      server records the flow completed for this account.
 * OB-9 Leaving a guide's host route pauses it on its step and coming back resumes
 *      there (host route-mismatch branch → `dismissHost()`); closing an Add modal
 *      still restarts that modal's guide (`handleModalClose` →
 *      `dismissHost({restartAtFirst: true})`).
 * OB-8 Guide positions and armed replays live in localStorage, per account
 *      (onboarding.svelte.ts): an armed replay reaches a new tab, logging out
 *      deletes it, and a guide finished in one tab closes the same step in another
 *      (onboardingGuide.svelte.ts `storage` listener → `dismissHost()`).
 *
 * Isolation: every test owns a disposable account (fixtures/onboarding-accounts.ts)
 * and, where the flow needs one, a broker it creates and deletes. The FX and asset
 * guides run on seeded, globally readable rows and only read them. Steps advance
 * with Next only — some cursor targets perform real actions (`fx.page.sync`,
 * `asset.page.sync` open real syncs) — and every walk asserts that the only write
 * it caused is its own completion.
 */

import {expect, test, type Locator, type Page, type Request} from './fixtures/playwright';
import {login, navigateTo} from './fixtures/auth-helpers';
import {eventSeq, waitForEvent, waitForSettled} from './fixtures/app-events';
import {createOwnedBroker, deleteDisposableUser, prepareOnboardingAccount, readFlowProgress, registerDisposableUser} from './fixtures/onboarding-accounts';

test.setTimeout(120_000);

const DESCRIPTION_ID = 'onboarding-coachmark-description';
/** First step of a walk: also covers the page load and whatever data its trigger awaits. */
const ARRIVAL_TIMEOUT_MS = 30_000;
const STEP_TIMEOUT_MS = 10_000;

type GuideStep = {stepId: string; target: string; pointer: 'none' | 'cursor'; highlight: 'none' | 'pulse'};

/** An area step (`areaPresentation`): pulse highlight, no cursor. */
function area(stepId: string, target: string): GuideStep {
    return {stepId, target, pointer: 'none', highlight: 'pulse'};
}

/** A control step (`pointer: 'cursor'`): cursor over the target, no highlight. Its target is never clicked here. */
function cursor(stepId: string, target: string): GuideStep {
    return {stepId, target, pointer: 'cursor', highlight: 'none'};
}

// Step ids in catalog order (onboardingGuideCatalog.ts), each paired with the
// data-testid of the element that registers the step's anchor id on the real page.
const BROKER_PAGE_STEPS = [area('broker.page.overview', 'broker-page-overview-guide-target'), area('broker.page.currency', 'broker-page-currency'), area('broker.page.views', 'broker-page-views'), cursor('broker.page.add', 'add-broker-button')];
const BROKER_MODAL_STEPS = [area('broker.overview', 'broker-modal-title'), area('broker.plugin', 'broker-default-plugin'), cursor('broker.icon', 'broker-icon-trigger')];
const BROKER_DETAIL_STEPS = [
    area('broker.detail.header', 'broker-detail-header'),
    cursor('broker.detail.overview', 'broker-tab-panoramica'),
    cursor('broker.detail.positions', 'broker-tab-posizioni'),
    cursor('broker.detail.transactions', 'broker-tab-transazioni'),
    cursor('broker.detail.info', 'broker-tab-info'),
];
const FX_PAGE_STEPS = [area('fx.page.overview', 'fx-page-overview-guide-target'), area('fx.page.filters', 'fx-page-filters'), cursor('fx.page.sync', 'fx-sync-all-button'), cursor('fx.page.add', 'fx-add-pair-button')];
const FX_MODAL_STEPS = [area('fx.currencies', 'fx-tour-pair-selectors'), area('fx.providers', 'fx-tour-providers')];
const FX_DETAIL_STEPS = [area('fx.detail.header', 'fx-detail-header'), cursor('fx.detail.provider', 'fx-detail-provider-btn'), area('fx.detail.chart', 'fx-detail-chart'), cursor('fx.detail.editor', 'fx-detail-edit-btn')];
const ASSET_PAGE_STEPS = [area('asset.page.overview', 'asset-page-overview-guide-target'), area('asset.page.filters', 'asset-page-filters'), cursor('asset.page.sync', 'assets-sync-all-button'), cursor('asset.page.add', 'assets-add-button')];
const ASSET_MODAL_STEPS = [area('asset.search', 'asset-tour-search'), area('asset.identity', 'asset-tour-identity'), area('asset.provider', 'asset-tour-provider')];
const ASSET_DETAIL_STEPS = [
    area('asset.detail.header', 'asset-detail-header'),
    area('asset.detail.chart', 'asset-detail-chart'),
    cursor('asset.detail.editor', 'asset-detail-editdata-btn'),
    cursor('asset.detail.metadata', 'asset-detail-metadata-toggle'),
    cursor('asset.detail.risk', 'asset-detail-tab-risk'),
];

/** Seeded, globally readable rows (populate_mock_data) the detail guides are walked on. */
const SEEDED_FX_PAIR = {base: 'EUR', quote: 'USD', slug: 'EUR-USD'};
const SEEDED_PRICED_ASSET = {displayName: 'Apple Inc.', providerCode: 'yfinance'};

type GuideSample = {
    coachmarks: number;
    stepId: string | null;
    guideState: string | null;
    geometryState: string | null;
    hidden: string | null;
    pointer: string | null;
    highlight: string | null;
    described: string[];
};

function accountTag(prefix: string, project: string): string {
    return `${prefix}${project === 'mobile' ? 'm' : 'd'}`;
}

/**
 * One atomic reading of the overlay: the coachmark's published state, and every
 * element other than its panel that names the coachmark description. Taken in a
 * single evaluate, so "step X, anchored, stable, describing only Y" is proved to
 * hold at one instant rather than assembled from reads taken at different moments.
 */
async function sampleGuide(page: Page): Promise<GuideSample | {unreadable: string}> {
    try {
        return await page.evaluate((descriptionId) => {
            const coachmarks = Array.from(document.querySelectorAll<HTMLElement>('[data-testid="onboarding-coachmark"]'));
            const coachmark = coachmarks.length === 1 ? coachmarks[0] : null;
            const described = Array.from(document.querySelectorAll<HTMLElement>(`[aria-describedby="${descriptionId}"]`))
                .filter((element) => element.dataset.testid !== 'onboarding-coachmark-panel')
                .map((element) => element.dataset.testid ?? `<${element.tagName.toLowerCase()} without data-testid>`);
            return {
                coachmarks: coachmarks.length,
                stepId: coachmark?.dataset.stepId ?? null,
                guideState: coachmark?.dataset.guideState ?? null,
                geometryState: coachmark?.dataset.geometryState ?? null,
                hidden: coachmark?.getAttribute('aria-hidden') ?? null,
                pointer: coachmark?.dataset.pointer ?? null,
                highlight: coachmark?.dataset.highlight ?? null,
                described,
            };
        }, DESCRIPTION_ID);
    } catch (error) {
        // A navigation can replace the execution context between two readings:
        // that means "not on screen yet", and the poll keeps asking.
        return {unreadable: String(error)};
    }
}

async function expectGuideStep(page: Page, step: GuideStep, timeout = STEP_TIMEOUT_MS): Promise<void> {
    await expect
        .poll(() => sampleGuide(page), {
            timeout,
            message: `The guide never presented ${step.stepId} anchored, with stable geometry, describing only ${step.target}`,
        })
        .toEqual({
            coachmarks: 1,
            stepId: step.stepId,
            guideState: 'anchored',
            geometryState: 'stable',
            hidden: 'false',
            pointer: step.pointer,
            highlight: step.highlight,
            described: [step.target],
        });
    await expect(page.getByTestId(step.target), `${step.stepId} must describe a target the user can see`).toBeVisible();
}

async function pressNext(page: Page): Promise<void> {
    const next = page.getByTestId('onboarding-coachmark-next');
    await expect(next).toBeEnabled();
    await next.click();
}

/** Assert `steps[from]` is on screen, then advance with Next through the remaining steps, asserting each. */
async function walkSteps(page: Page, steps: readonly GuideStep[], from = 0): Promise<void> {
    await expectGuideStep(page, steps[from], ARRIVAL_TIMEOUT_MS);
    for (const step of steps.slice(from + 1)) {
        await pressNext(page);
        await expectGuideStep(page, step);
    }
}

/** Next on the last step: the guide finishes and takes its coachmark off screen. */
async function finishGuide(page: Page, flow: string): Promise<void> {
    await pressNext(page);
    await expect(page.getByTestId('onboarding-coachmark'), `${flow} must close after its last step`).toHaveCount(0, {timeout: 10_000});
}

async function expectFlowStatus(page: Page, flow: string, status: 'pending' | 'completed' | 'skipped'): Promise<void> {
    const item = await readFlowProgress(page, flow);
    expect(item.status, `${flow} must be recorded ${status} for this account`).toBe(status);
    expect(item.version, `${flow} must be recorded at its current content version`).toBe(item.current_version);
}

/** The POSTs a guide walk can cause: onboarding progress (legitimate) and syncs (never). */
function recordGuideWrites(page: Page): {paths: string[]; stop: () => void} {
    const paths: string[] = [];
    const record = (request: Request) => {
        if (request.method() !== 'POST') return;
        const path = new URL(request.url()).pathname;
        if (path.startsWith('/api/v1/settings/onboarding/') || path.endsWith('/sync')) paths.push(path);
    };
    page.on('request', record);
    return {paths, stop: () => page.off('request', record)};
}

/**
 * Walk a due guide from its first step with Next only, then prove that it closed
 * and that the server recorded it completed — through exactly one write, its own
 * completion: no sync fired from a cursor target, no skip, no other flow touched.
 */
async function walkToCompletion(page: Page, flow: string, steps: readonly GuideStep[]): Promise<void> {
    await expectFlowStatus(page, flow, 'pending');
    const writes = recordGuideWrites(page);
    try {
        await walkSteps(page, steps);
        await finishGuide(page, flow);
    } finally {
        writes.stop();
    }
    expect(writes.paths, `Walking ${flow} with Next may write only its own completion`).toEqual([`/api/v1/settings/onboarding/${flow}/complete`]);
    await expectFlowStatus(page, flow, 'completed');
}

/**
 * Activate a control from the keyboard. The coachmark panel floats above the page
 * (z-index 80+) and on the narrow mobile viewport can sit over the header or a
 * modal's own header, where a pointer click would land on the panel. Focus + Enter
 * is the control's own keyboard contract and bypasses no actionability check.
 */
async function pressControl(control: Locator): Promise<void> {
    await expect(control).toBeVisible();
    await control.focus();
    await expect(control).toBeFocused();
    await control.press('Enter');
}

type MarkedWindow = Window & {__lfGuidesRuntimeMark?: true};

/**
 * Mark the running app so a later check can prove a navigation stayed client-side.
 * A full page load rebuilds the runtime and never runs the host's route-change
 * branch: the resume would then come from storage alone, and OB-9 would pass even
 * with the old restart-at-first behaviour.
 */
async function markAppRuntime(page: Page): Promise<void> {
    await page.evaluate(() => {
        (window as MarkedWindow).__lfGuidesRuntimeMark = true;
    });
}

async function expectSameAppRuntime(page: Page): Promise<void> {
    const kept = await page.evaluate(() => (window as MarkedWindow).__lfGuidesRuntimeMark === true);
    expect(kept, 'The navigation must stay client-side: a full load would bypass the host route-change branch under test').toBe(true);
}

/** Client-side navigation through the sidebar, the way a user leaves and comes back; `page.goto` would reload the app instead. */
async function navigateWithSidebar(page: Page, mobile: boolean, navTestId: string, url: RegExp): Promise<void> {
    if (mobile) {
        await pressControl(page.getByTestId('mobile-menu-toggle'));
        await expect(page.getByTestId('app-header')).toHaveAttribute('data-sidebar-open', 'true');
    }
    await pressControl(page.getByTestId(navTestId));
    await expect(page).toHaveURL(url, {timeout: 15_000});
}

async function openOnboardingGroup(page: Page, group: 'broker'): Promise<void> {
    await navigateTo(page, '/settings?tab=preferences');
    const section = page.getByTestId('onboarding-replay-section');
    await expect(section).toBeVisible({timeout: 15_000});
    await expect(section.getByTestId('onboarding-flow-welcome')).toBeVisible({timeout: 10_000});
    const details = section.getByTestId(`onboarding-group-${group}`);
    // Rendered closed (only the setup and core groups start open): open it through
    // its own summary, and only when it is not open already.
    if ((await details.getAttribute('open')) === null) await details.locator(':scope > summary').click();
    await expect(details).toHaveAttribute('open', '');
}

async function armReplay(page: Page, flow: string): Promise<void> {
    await expect(page.getByTestId(`onboarding-flow-${flow}`)).toBeVisible();
    const armed = page.getByTestId(`onboarding-flow-${flow}-armed`);
    await expect(armed, `${flow} must start with no armed replay`).toHaveCount(0);
    const since = await eventSeq(page);
    await page.getByTestId(`onboarding-replay-${flow}`).click();
    const event = await waitForEvent(page, 'onboarding.replay.armed', {since});
    expect(event.detail?.flow).toBe(flow);
    await expect(armed).toBeVisible({timeout: 5_000});
}

async function logoutThroughUi(page: Page, mobile: boolean): Promise<void> {
    if (mobile) {
        await page.getByTestId('mobile-menu-toggle').click();
        await expect(page.getByTestId('app-header')).toHaveAttribute('data-sidebar-open', 'true');
    }
    await page.getByTestId('logout-button').click();
    await expect(page.getByTestId('login-page')).toBeVisible({timeout: 15_000});
}

async function seededPricedAssetId(page: Page): Promise<number> {
    const response = await page.request.get(`/api/v1/assets/query?search=${encodeURIComponent(SEEDED_PRICED_ASSET.displayName)}`);
    expect(response.ok(), `Asset lookup failed (HTTP ${response.status()})`).toBe(true);
    const matches = ((await response.json()) as Array<{id: number; display_name: string; provider_code: string | null}>).filter((asset) => asset.display_name === SEEDED_PRICED_ASSET.displayName && asset.provider_code === SEEDED_PRICED_ASSET.providerCode);
    expect(matches, `${SEEDED_PRICED_ASSET.displayName} (${SEEDED_PRICED_ASSET.providerCode}) must be one seeded asset a fresh account can read — populate_mock_data.populate_assets`).toHaveLength(1);
    return matches[0].id;
}

test.beforeEach(async ({context}) => {
    // /assets and /assets/{id} poll POST /assets/prices/current, which asks the live
    // providers (yfinance, justetf, ...) and upserts today's OHLC row on the shared
    // seeded assets. No guide reads a live price, so the poll is answered with an
    // empty result: no test reaches a third party or writes a shared price.
    await context.route('**/api/v1/assets/prices/current', (route) => route.fulfill({json: {results: [], success_count: 0, errors: []}}));
});

test.describe('T11 — every contextual guide walked against its real page', () => {
    test('T11 broker_page_guide on /brokers, then broker_guide in the Add Broker modal, walk every catalog step and complete on desktop/mobile', async ({page, request}, testInfo) => {
        const user = await registerDisposableUser(request, accountTag('t11b', testInfo.project.name));
        try {
            await prepareOnboardingAccount(page, user, ['broker_page_guide', 'broker_guide']);
            await navigateTo(page, '/brokers');
            await expect(page.getByTestId('brokers-page')).toBeVisible({timeout: 15_000});
            await walkToCompletion(page, 'broker_page_guide', BROKER_PAGE_STEPS);

            // The page guide is completed: the modal is opened through the page's own control.
            await page.getByTestId('add-broker-button').click();
            await expect(page.getByTestId('broker-modal')).toBeVisible({timeout: 10_000});
            await walkToCompletion(page, 'broker_guide', BROKER_MODAL_STEPS);
        } finally {
            await deleteDisposableUser(request, user);
        }
    });

    test('T11 broker_detail_guide on a broker the account owns walks every catalog step and completes on desktop/mobile', async ({page, request}, testInfo) => {
        const user = await registerDisposableUser(request, accountTag('t11bd', testInfo.project.name));
        const ownedBrokerIds: number[] = [];
        try {
            await prepareOnboardingAccount(page, user, ['broker_detail_guide']);
            const broker = await createOwnedBroker(page, 't11', ownedBrokerIds);
            await navigateTo(page, `/brokers/${broker.id}`);
            await expect(page.getByTestId('broker-detail-page')).toBeVisible({timeout: 15_000});
            await walkToCompletion(page, 'broker_detail_guide', BROKER_DETAIL_STEPS);
        } finally {
            await deleteDisposableUser(request, user, ownedBrokerIds);
        }
    });

    test('T11 fx_page_guide on /fx, then fx_guide in the Add Pair modal, walk every catalog step and complete on desktop/mobile', async ({page, request}, testInfo) => {
        const user = await registerDisposableUser(request, accountTag('t11f', testInfo.project.name));
        try {
            await prepareOnboardingAccount(page, user, ['fx_page_guide', 'fx_guide']);
            await navigateTo(page, '/fx');
            await expect(page.getByTestId('fx-page')).toBeVisible({timeout: 15_000});
            await walkToCompletion(page, 'fx_page_guide', FX_PAGE_STEPS);

            await page.getByTestId('fx-add-pair-button').click();
            await expect(page.getByTestId('fx-add-pair-modal')).toBeVisible({timeout: 10_000});
            await walkToCompletion(page, 'fx_guide', FX_MODAL_STEPS);
        } finally {
            await deleteDisposableUser(request, user);
        }
    });

    test('T11 fx_detail_guide on the seeded EUR/USD pair walks every catalog step and completes on desktop/mobile', async ({page, request}, testInfo) => {
        const user = await registerDisposableUser(request, accountTag('t11fd', testInfo.project.name));
        try {
            await prepareOnboardingAccount(page, user, ['fx_detail_guide']);
            const routes = await page.request.get('/api/v1/fx/providers/routes');
            expect(routes.ok(), `FX route lookup failed (HTTP ${routes.status()})`).toBe(true);
            const items = ((await routes.json()) as {items: Array<{base: string; quote: string}>}).items;
            expect(
                items.some((route) => route.base === SEEDED_FX_PAIR.base && route.quote === SEEDED_FX_PAIR.quote),
                `${SEEDED_FX_PAIR.slug} must be a seeded route a fresh account can read — populate_mock_data.populate_fx_currency_pair_sources`,
            ).toBe(true);

            await navigateTo(page, `/fx/${SEEDED_FX_PAIR.slug}`);
            await expect(page.getByTestId('fx-detail-page')).toHaveAttribute('data-chart-pair', SEEDED_FX_PAIR.slug, {timeout: 15_000});
            await walkToCompletion(page, 'fx_detail_guide', FX_DETAIL_STEPS);
        } finally {
            await deleteDisposableUser(request, user);
        }
    });

    test('T11 asset_page_guide on /assets, then asset_guide in the Add Asset modal, walk every catalog step and complete on desktop/mobile', async ({page, request}, testInfo) => {
        const user = await registerDisposableUser(request, accountTag('t11a', testInfo.project.name));
        try {
            await prepareOnboardingAccount(page, user, ['asset_page_guide', 'asset_guide']);
            await navigateTo(page, '/assets');
            await expect(page.getByTestId('assets-page')).toBeVisible({timeout: 15_000});
            await walkToCompletion(page, 'asset_page_guide', ASSET_PAGE_STEPS);

            await page.getByTestId('assets-add-button').click();
            await expect(page.getByTestId('asset-modal')).toBeVisible({timeout: 10_000});
            await walkToCompletion(page, 'asset_guide', ASSET_MODAL_STEPS);
        } finally {
            await deleteDisposableUser(request, user);
        }
    });

    test('T11 asset_detail_guide on the seeded, priced Apple asset walks every catalog step and completes on desktop/mobile', async ({page, request}, testInfo) => {
        const user = await registerDisposableUser(request, accountTag('t11ad', testInfo.project.name));
        try {
            await prepareOnboardingAccount(page, user, ['asset_detail_guide']);
            const assetId = await seededPricedAssetId(page);
            await navigateTo(page, `/assets/${assetId}`);
            await expect(page.getByTestId('asset-detail-page')).toBeVisible({timeout: 15_000});
            // `asset.detail.editor` exists only once the chart holds prices, which is why a priced asset is required.
            await walkToCompletion(page, 'asset_detail_guide', ASSET_DETAIL_STEPS);
        } finally {
            await deleteDisposableUser(request, user);
        }
    });
});

test.describe('OB-9 — leaving a host route pauses a guide, an Add modal still restarts', () => {
    test('OB-9 leaving /brokers mid-guide pauses broker_page_guide on its 3rd step and coming back resumes it there on desktop/mobile', async ({page, request}, testInfo) => {
        const mobile = testInfo.project.name === 'mobile';
        const user = await registerDisposableUser(request, accountTag('ob9p', testInfo.project.name));
        try {
            await prepareOnboardingAccount(page, user, ['broker_page_guide']);
            await navigateTo(page, '/brokers');
            await expect(page.getByTestId('brokers-page')).toBeVisible({timeout: 15_000});
            await walkSteps(page, BROKER_PAGE_STEPS.slice(0, 3));
            await markAppRuntime(page);

            await navigateWithSidebar(page, mobile, 'nav-dashboard', /\/dashboard(?:[/?#]|$)/);
            await expect(page.getByTestId('dashboard-page')).toBeVisible({timeout: 15_000});
            await expectSameAppRuntime(page);
            await expect(page.getByTestId('onboarding-coachmark'), 'Leaving the host route must take the step off screen').toHaveCount(0, {timeout: 10_000});
            await expectFlowStatus(page, 'broker_page_guide', 'pending');

            await navigateWithSidebar(page, mobile, 'nav-brokers', /\/brokers(?:[?#]|$)/);
            await expect(page.getByTestId('brokers-page')).toBeVisible({timeout: 15_000});
            await expectGuideStep(page, BROKER_PAGE_STEPS[2], ARRIVAL_TIMEOUT_MS);
            await expectSameAppRuntime(page);

            // The resumed guide is the same walk, not a restart: it continues to its end.
            await pressNext(page);
            await expectGuideStep(page, BROKER_PAGE_STEPS[3]);
            await finishGuide(page, 'broker_page_guide');
            await expectFlowStatus(page, 'broker_page_guide', 'completed');
        } finally {
            await deleteDisposableUser(request, user);
        }
    });

    test('OB-9 leaving a broker detail mid-guide pauses broker_detail_guide on its 2nd step and returning to the same broker resumes it there on desktop/mobile', async ({page, request}, testInfo) => {
        const mobile = testInfo.project.name === 'mobile';
        const user = await registerDisposableUser(request, accountTag('ob9d', testInfo.project.name));
        const ownedBrokerIds: number[] = [];
        try {
            // broker_page_guide is skipped with the rest, so /brokers has no guide of its own to start.
            await prepareOnboardingAccount(page, user, ['broker_detail_guide']);
            const broker = await createOwnedBroker(page, 'ob9', ownedBrokerIds);
            await navigateTo(page, `/brokers/${broker.id}`);
            await expect(page.getByTestId('broker-detail-page')).toBeVisible({timeout: 15_000});
            await walkSteps(page, BROKER_DETAIL_STEPS.slice(0, 2));
            await markAppRuntime(page);

            await navigateWithSidebar(page, mobile, 'nav-brokers', /\/brokers(?:[?#]|$)/);
            const brokersPage = page.getByTestId('brokers-page');
            await expect(brokersPage).toBeVisible({timeout: 15_000});
            await waitForSettled(brokersPage, 20_000);
            await expectSameAppRuntime(page);
            await expect(page.getByTestId('onboarding-coachmark'), 'Leaving the detail host route must take the step off screen').toHaveCount(0);
            await expectFlowStatus(page, 'broker_detail_guide', 'pending');

            const card = page.getByTestId(`broker-card-${broker.id}`);
            await expect(card).toBeVisible();
            await card.click();
            await expect(page).toHaveURL(new RegExp(`/brokers/${broker.id}(?:[?#]|$)`), {timeout: 15_000});
            await expect(page.getByTestId('broker-detail-page')).toBeVisible({timeout: 15_000});
            await expectGuideStep(page, BROKER_DETAIL_STEPS[1], ARRIVAL_TIMEOUT_MS);
            await expectSameAppRuntime(page);
        } finally {
            await deleteDisposableUser(request, user, ownedBrokerIds);
        }
    });

    test('OB-9 contrast: closing the Add Broker modal mid-guide restarts broker_guide at its first step on desktop/mobile', async ({page, request}, testInfo) => {
        const user = await registerDisposableUser(request, accountTag('ob9m', testInfo.project.name));
        try {
            await prepareOnboardingAccount(page, user, ['broker_guide']);
            await navigateTo(page, '/brokers');
            const brokersPage = page.getByTestId('brokers-page');
            await expect(brokersPage).toBeVisible({timeout: 15_000});
            await waitForSettled(brokersPage, 20_000);
            await expect(page.getByTestId('onboarding-coachmark'), 'broker_page_guide is skipped: no guide is on screen before the modal opens').toHaveCount(0);

            const modal = page.getByTestId('broker-modal');
            await page.getByTestId('add-broker-button').click();
            await expect(modal).toBeVisible({timeout: 10_000});
            await walkSteps(page, BROKER_MODAL_STEPS.slice(0, 2));

            await pressControl(page.getByTestId('broker-modal-close'));
            await expect(modal).toHaveCount(0, {timeout: 10_000});
            await expect(page.getByTestId('onboarding-coachmark'), 'Closing the modal must take its guide off screen').toHaveCount(0);
            await expectFlowStatus(page, 'broker_guide', 'pending');

            await page.getByTestId('add-broker-button').click();
            await expect(modal).toBeVisible({timeout: 10_000});
            await expectGuideStep(page, BROKER_MODAL_STEPS[0], ARRIVAL_TIMEOUT_MS);
        } finally {
            await deleteDisposableUser(request, user);
        }
    });
});

test.describe('OB-8 — guide positions and replays persist per account across tabs', () => {
    test('OB-8 a replay armed in Settings survives into a new tab of the same browser and starts there at broker.page.overview on desktop/mobile', async ({page, request}, testInfo) => {
        const user = await registerDisposableUser(request, accountTag('ob8t', testInfo.project.name));
        try {
            // Every flow terminal: broker_page_guide can only come back as a replay.
            await prepareOnboardingAccount(page, user, []);
            await expectFlowStatus(page, 'broker_page_guide', 'skipped');
            await openOnboardingGroup(page, 'broker');
            await armReplay(page, 'broker_page_guide');

            // A new tab shares cookies and localStorage, but not the app runtime or
            // sessionStorage. The arming tab is closed first, so only what was
            // persisted can reach the new one.
            const tab = await page.context().newPage();
            await page.close();
            const writes = recordGuideWrites(tab);
            try {
                await navigateTo(tab, '/brokers');
                await expect(tab.getByTestId('brokers-page')).toBeVisible({timeout: 15_000});
                await walkSteps(tab, BROKER_PAGE_STEPS);
                await finishGuide(tab, 'broker_page_guide');
            } finally {
                writes.stop();
            }
            expect(writes.paths, 'A replay is client-side: walking it writes no onboarding progress').toEqual([]);
            await expectFlowStatus(tab, 'broker_page_guide', 'skipped');
        } finally {
            await deleteDisposableUser(request, user);
        }
    });

    test('OB-8 logging out through the UI clears the account armed replay, so it is gone after logging back in on desktop/mobile', async ({page, request}, testInfo) => {
        const mobile = testInfo.project.name === 'mobile';
        const user = await registerDisposableUser(request, accountTag('ob8l', testInfo.project.name));
        try {
            await prepareOnboardingAccount(page, user, []);
            await openOnboardingGroup(page, 'broker');
            await armReplay(page, 'broker_page_guide');
            // Positive control: after a full reload the badge still shows, so it
            // reflects the stored replay and not component memory.
            await openOnboardingGroup(page, 'broker');
            await expect(page.getByTestId('onboarding-flow-broker_page_guide-armed')).toBeVisible();

            await logoutThroughUi(page, mobile);
            await login(page, user);
            await expect(page).toHaveURL(/\/dashboard(?:[/?#]|$)/, {timeout: 15_000});

            await openOnboardingGroup(page, 'broker');
            await expect(page.getByTestId('onboarding-flow-broker_page_guide')).toHaveAttribute('data-status', 'skipped');
            await expect(page.getByTestId('onboarding-replay-broker_page_guide')).toBeEnabled();
            await expect(page.getByTestId('onboarding-flow-broker_page_guide-armed'), 'Logging out must delete the replay stored for this account').toHaveCount(0);

            // The trigger agrees: /brokers settles without starting the cleared replay.
            // Its guide starts in the same task that clears `data-busy`, so a settled
            // page with no coachmark is a real absence, not an early look.
            await navigateTo(page, '/brokers');
            const brokersPage = page.getByTestId('brokers-page');
            await expect(brokersPage).toBeVisible({timeout: 15_000});
            await waitForSettled(brokersPage, 20_000);
            await expect(page.getByTestId('onboarding-coachmark')).toHaveCount(0);
        } finally {
            await deleteDisposableUser(request, user);
        }
    });

    test('OB-8 finishing a guide in one tab closes the same step in another tab of the same browser on desktop/mobile', async ({page, request}, testInfo) => {
        const user = await registerDisposableUser(request, accountTag('ob8x', testInfo.project.name));
        try {
            await prepareOnboardingAccount(page, user, ['broker_page_guide']);
            await navigateTo(page, '/brokers');
            await expect(page.getByTestId('brokers-page')).toBeVisible({timeout: 15_000});
            await expectGuideStep(page, BROKER_PAGE_STEPS[0], ARRIVAL_TIMEOUT_MS);

            // Tab B resumes the guide tab A started, at the same step, from the shared key.
            const other = await page.context().newPage();
            await navigateTo(other, '/brokers');
            await expect(other.getByTestId('brokers-page')).toBeVisible({timeout: 15_000});
            await expectGuideStep(other, BROKER_PAGE_STEPS[0], ARRIVAL_TIMEOUT_MS);

            // From here on tab B is only observed, never acted on.
            for (const step of BROKER_PAGE_STEPS.slice(1)) {
                await pressNext(page);
                await expectGuideStep(page, step);
            }
            // A's moves rewrote the shared key without removing it: B keeps its step.
            await expectGuideStep(other, BROKER_PAGE_STEPS[0]);

            await finishGuide(page, 'broker_page_guide');
            await expectFlowStatus(page, 'broker_page_guide', 'completed');
            await expect(other.getByTestId('onboarding-coachmark'), 'Removing the shared key in tab A must close the same step in tab B').toHaveCount(0, {timeout: 10_000});
            await expect(other).toHaveURL(/\/brokers(?:[?#]|$)/);
            await expect(other.getByTestId('brokers-page')).toBeVisible();
        } finally {
            await deleteDisposableUser(request, user);
        }
    });
});
