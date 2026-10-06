/**
 * Asset Detail, Risk tab — owned by the Risk workstream (stage 2, 06/10/2026, D378).
 *
 * The file had no owner on purpose: Asset Detail is parked (D8, D47) and had to come
 * out of the risk redesign IDENTICAL, and the first two tests are what PROVES it (D82).
 * Stage 2 changed this tab on purpose — its comparison picker now asks the eligibility
 * engine about the page's period — so Risk owns the file, and the net with it.
 *
 * The net's rule stands: do not adapt those two tests to make them pass. Adapting them
 * deletes the very evidence they exist to produce. If one of them goes red, the page
 * changed — that is a finding, not a maintenance chore. The edits they took fix two
 * inputs, never an assertion:
 *   1. the second answers the eligibility question itself, every asked asset admitted,
 *      because the lane's engine judges the seed's prices against today's date, and its
 *      verdicts — and when they land — would decide whether the option that test picks
 *      can be compared against at all;
 *   2. both hold the live-price poll (06/10/2026), from their `beforeEach`, before any
 *      page opens. The Assets page and Asset Detail poll `POST /assets/prices/current`,
 *      and an answered poll asks the real price providers — JustETF's live quote feed,
 *      Yahoo, the scheduled-investment provider, the page scrapers — and writes today's
 *      prices into the lane. So the net depended on the market and on the network, moved
 *      the very prices the eligibility engine judges, and dropped the risk cache under the
 *      requests it reads: every answer is a portfolio mutation. Held, the poll reaches nothing.
 * The third test of their block is not part of the net: it pins input 2 — the net's flow
 * does poll, and every poll it sends is held. The stage-2 tests below pin the rest.
 *
 * `openFirstAssetDetail` lives here rather than in `risk-mocks.ts` because this
 * file is its only consumer: it keeps the surface shared with the redesign as
 * small as it can honestly be.
 */
import {expect, test, type Page, type Request} from '../fixtures/playwright';

import {login, navigateTo} from '../fixtures/auth-helpers';
import {expectChartCanvas} from '../fixtures/charts';
import {TEST_USER} from '../fixtures/test-users';
import {goToAssetsPage} from '../assets/assets-helpers';
import {schemas} from '../../src/lib/api/generated';
import {installRiskMocks, waitForRiskCatalog, type RiskRequest} from './risk-mocks';

async function openFirstAssetDetail(page: Page): Promise<number> {
    await goToAssetsPage(page);
    const firstCard = page.getByTestId(/^asset-card-\d+$/).first();
    await expect(firstCard).toBeVisible({timeout: 8_000});
    const testId = await firstCard.getAttribute('data-testid');
    const assetId = Number(testId?.replace('asset-card-', ''));
    if (!Number.isInteger(assetId) || assetId <= 0) throw new Error('Seeded asset card must expose a numeric data-testid.');
    await firstCard.click();
    await expect(page.getByTestId('asset-detail-page')).toBeVisible({timeout: 12_000});
    await expect(page.getByTestId('asset-detail-tab-overview')).toBeVisible({timeout: 12_000});
    return assetId;
}

/** Every live-price poll each page's hold has held, in order: what the net's hygiene pin compares with what the page sent. */
const heldLivePricePolls = new WeakMap<Page, Request[]>();

/**
 * Hold the live-price poll, unanswered, for the whole test: a copy, with the same behaviour, of
 * `holdLivePricePoll` in `risk-benchmark-shared.spec.ts`, which says why. In short: an answered
 * poll asks the real price providers, writes today's price into the lane's database and, through
 * `zodios-client`, invalidates the risk cache — eligibility answers included — while these tests
 * read them. Held, never answered, and never unrouted: removing the route would release what it
 * holds. Unlike its siblings this copy also keeps what it held, for the net's hygiene pin to read.
 */
async function holdLivePricePoll(page: Page): Promise<void> {
    const held: Request[] = [];
    heldLivePricePolls.set(page, held);
    await page.route(/\/api\/v1\/assets\/prices\/current(?:\?|$)/, (route) => {
        // Deliberately neither fulfilled nor continued: only kept.
        held.push(route.request());
    });
}

/** A live-price poll, told by its path alone — not by the hold's pattern, so the pin also sees a poll that pattern would miss. */
function isLivePricePoll(request: Request): boolean {
    return new URL(request.url()).pathname.replace(/\/+$/, '') === '/api/v1/assets/prices/current';
}

/** One poll as the pin reports it: method, path, and the asset ids it asked about. */
function describePoll(request: Request): string {
    return `${request.method()} ${new URL(request.url()).pathname} ${request.postData() ?? ''}`;
}

// Earned parallel: this file's blocks own the data they touch and wait on published
// state, so they share the backend with their neighbours instead of queueing behind
// them. Verified by a green run of the whole category at 4 workers.
test.describe.configure({mode: 'parallel'});

test.describe('Risk analysis functional integration', () => {
    test.beforeEach(async ({page}) => {
        // Input 2 (header), not an assertion: held before any page opens, or the Assets page and
        // Asset Detail ask the real providers and write today's prices into the lane.
        await holdLivePricePoll(page);
        await login(page, TEST_USER);
    });

    test('asset detail preserves Overview and exposes Risk through its dedicated tab', async ({page}) => {
        await installRiskMocks(page);
        await openFirstAssetDetail(page);

        await expect(page.getByTestId('asset-detail-signals-toggle')).toBeVisible({timeout: 8_000});
        await expect(page.getByTestId('risk-beta-banner')).toHaveCount(0);
        await expect(page.getByTestId('asset-detail-risk-panel')).toHaveCount(0);

        await page.getByTestId('asset-detail-tab-risk').click();
        await expect(page).toHaveURL(/[?&]tab=risk(?:&|$)/);
        await expect(page.getByTestId('asset-detail-risk-panel')).toBeVisible({timeout: 12_000});
        await expect(page.getByTestId('risk-beta-banner')).toBeVisible();
        await expect(page.getByTestId('risk-beta-banner')).toHaveCount(1);
        await expect(page.getByTestId('asset-detail-signals-toggle')).toHaveCount(0);

        await page.getByTestId('asset-risk-configure-signals').click();
        await expect(page.getByTestId('asset-detail-signals-toggle')).toBeVisible({timeout: 8_000});
        await expect(page.getByTestId('asset-detail-signals-toggle')).toHaveAttribute('aria-expanded', 'true');
        await expect(page.getByTestId('asset-detail-risk-panel')).toHaveCount(0);
    });

    test('asset Risk runs typed scenarios, exposes replay audit and switches simulation view', async ({page}) => {
        const requests = await installRiskMocks(page);
        // The page hands its period to the comparison picker, which asks the engine about it
        // (D378): answered here, every asked asset admitted — an input, not an assertion (header).
        await answerEligibility(page);
        const assetId = await openFirstAssetDetail(page);
        await page.getByTestId('asset-detail-tab-risk').click();
        await expect(page.getByTestId('asset-detail-risk-panel')).toBeVisible({timeout: 12_000});

        // The comparison section renders only once the capability catalog has landed:
        // wait for the panel to say so, rather than for the section to appear — an
        // absent section is otherwise indistinguishable from an unsupported one.
        await waitForRiskCatalog(page);
        await expect(page.getByTestId('risk-comparison-controls')).toBeVisible({timeout: 12_000});
        await page.getByTestId('risk-comparison-asset-select-trigger').click();
        const comparisonOption = page.getByTestId(/^search-select-option-\d+$/).first();
        await expect(comparisonOption).toBeVisible({timeout: 5_000});
        await comparisonOption.click();
        await page.getByTestId('risk-comparison-run').click();
        await expectChartCanvas(page, 'risk-comparison-chart', 8_000);

        const stressBucketInputs = page.getByTestId(/^risk-stress-bucket-input-/);
        await expect(stressBucketInputs).toHaveCount(1, {timeout: 8_000});
        await page.getByTestId('risk-stress-show-all').check();
        await expect.poll(() => stressBucketInputs.count(), {timeout: 8_000}).toBeGreaterThan(1);
        const stressBucketInput = stressBucketInputs.first();
        await expect(stressBucketInput).toBeVisible({timeout: 8_000});
        const stressBucketTestId = await stressBucketInput.getAttribute('data-testid');
        const stressBucketId = stressBucketTestId?.replace('risk-stress-bucket-input-', '');
        if (!stressBucketId) throw new Error('Stress bucket input must expose its canonical bucket ID.');
        await stressBucketInput.fill('-25');
        await page.getByTestId('risk-stress-run').click();
        await expect(page.getByTestId('risk-stress-impacts')).toBeVisible({timeout: 8_000});
        await expect(page.getByTestId('risk-stress-audit')).toBeVisible();
        await expect(page.getByTestId(`risk-stress-audit-asset-${assetId}`)).toBeVisible();

        await page.getByTestId('risk-replay-proxy-select-trigger').click();
        const proxyOption = page.getByTestId(/^search-select-option-\d+$/).first();
        await expect(proxyOption).toBeVisible({timeout: 5_000});
        const proxyOptionTestId = await proxyOption.getAttribute('data-testid');
        const proxyAssetId = Number(proxyOptionTestId?.replace('search-select-option-', ''));
        if (!Number.isInteger(proxyAssetId) || proxyAssetId <= 0) throw new Error('Replay proxy option must expose a numeric asset ID.');
        await proxyOption.click();
        await page.getByTestId('risk-replay-run').click();
        await expect(page.getByTestId('risk-replay-audit')).toBeVisible({timeout: 8_000});
        await expect(page.getByTestId(`risk-replay-audit-proxy-${assetId}`)).toBeVisible();
        await expect(page.getByTestId('risk-replay-audit-missing-history-policy')).toBeVisible();
        await expect(page.getByTestId('risk-replay-audit-composition-policy')).toBeVisible();
        await expect(page.getByTestId('risk-replay-audit-proxy-series-usage')).toBeVisible();

        const simulationQuery = page.waitForRequest(
            (request) => {
                if (request.method() !== 'POST' || !request.url().includes('/api/v1/risk/query')) return false;
                const body = request.postDataJSON() as RiskRequest;
                return body.analytics.some((analytic) => analytic.analytic_code === 'simulation');
            },
            {timeout: 10_000},
        );
        await expect(page.getByTestId('risk-simulation-run')).toBeEnabled();
        await page.getByTestId('risk-simulation-run').click();
        await simulationQuery;
        await expect(page.getByTestId('risk-simulation-chart')).toBeVisible({timeout: 12_000});
        await expect(page.getByTestId('risk-simulation-assumptions')).toBeVisible();
        await page.getByTestId('risk-simulation-view-terminal').click();
        await expect(page.getByTestId('risk-simulation-terminal-distribution')).toBeVisible({timeout: 5_000});

        await expect
            .poll(
                () => {
                    const assetRequests = requests.filter((request) => request.scope.kind === 'asset' && request.scope.asset_id === assetId);
                    return new Set(assetRequests.flatMap((request) => request.analytics.map((analytic) => analytic.analytic_code)));
                },
                {timeout: 15_000},
            )
            .toEqual(new Set(['comparison', 'historical_kpi', 'historical_var', 'simulation', 'stress']));

        const hypotheticalRequest = requests.flatMap((request) => request.analytics).find((analytic) => analytic.analytic_code === 'stress' && analytic.parameters?.method === 'hypothetical');
        expect(hypotheticalRequest?.parameters).toMatchObject({
            method: 'hypothetical',
            dimension: 'asset_class',
            bucket_shocks: {
                [stressBucketId]: -0.25,
            },
        });

        const replayRequest = requests.flatMap((request) => request.analytics).find((analytic) => analytic.analytic_code === 'stress' && analytic.parameters?.method === 'historical_replay');
        expect(replayRequest?.parameters).toMatchObject({
            method: 'historical_replay',
            missing_history_policy: 'manual_proxy_or_exclude',
            proxy_assets: [{asset_id: assetId, proxy_asset_id: proxyAssetId}],
            excluded_assets: [],
        });

        const simulationRequest = requests.flatMap((request) => request.analytics).find((analytic) => analytic.analytic_code === 'simulation');
        expect(simulationRequest?.parameters).toMatchObject({
            sampling_method: 'mc',
            path_count: 8192,
            random_seed: 123456,
        });
        expect(simulationRequest?.parameters).not.toHaveProperty('seed');
    });

    /**
     * Not part of the net: the pin of its input 2 (header). The net walks Assets page → Asset Detail
     * → Risk tab, and both pages poll the current price. This walks the same flow under the same
     * `beforeEach` and compares what the page sent — every request to the poll's path, seen by the
     * browser — with what the hold held:
     *   - the page did poll, so the hold is in the flow's path and «none escaped» is not vacuous;
     *   - every poll it sent was held: none continued to the backend, which would have asked the
     *     providers, and none was answered by anything else.
     * It lives in this block, not in its own, because what it proves is this block's `beforeEach`.
     * Nothing to restore: nothing is written.
     */
    test('the net’s flow reaches no price provider: it does poll, and every live-price poll it sends is held', async ({page}, testInfo) => {
        const sent: Request[] = [];
        page.on('request', (request) => {
            if (isLivePricePoll(request)) sent.push(request);
        });
        await installRiskMocks(page);
        await openFirstAssetDetail(page);
        await page.getByTestId('asset-detail-tab-risk').click();
        await expect(page.getByTestId('asset-detail-risk-panel')).toBeVisible({timeout: 12_000});
        await waitForRiskCatalog(page);

        await expect.poll(() => sent.length, {timeout: 10_000, message: 'the flow sent no live-price poll, so «every poll was held» would be true of nothing'}).toBeGreaterThan(0);
        const held = heldLivePricePolls.get(page) ?? [];
        await expect
            .poll(() => sent.filter((request) => !held.includes(request)).map(describePoll), {
                timeout: 5_000,
                message: 'a live-price poll the page sent was not held: it reached the backend, which asks the real providers and writes today’s prices into the lane',
            })
            .toEqual([]);
        testInfo.annotations.push({type: 'held live-price polls', description: `${sent.length} sent, all held: ${sent.map(describePoll).join(' · ')}`});
    });
});

/**
 * ─── Stage 2 (D378): the comparison's benchmark picker knows what the engine can measure ───
 *
 * Owner: the Risk workstream, 06/10/2026. **Not part of the net above**: the net's two tests
 * keep every assertion they had (two of their inputs are fixed, not their checks: see the
 * header), and what follows pins what stage 2 adds to this tab. The page hands its window
 * and target currency to its `BenchmarkSelect` (`period`, `currency`), so the picker asks the
 * eligibility engine itself, and:
 *
 *   1. an asset the engine rules out for the page's period is listed apart —
 *      `risk-comparison-asset-select-blocked`, disabled, the engine's codes in `data-reasons` —
 *      while an admitted benchmark can still be chosen; the question carried the page's own
 *      period and currency, read off the risk requests the panel itself sent for this asset;
 *   2. a stored benchmark the engine rules out is `blocked` (D378): the picker keeps it — on its
 *      root, in its blocked section and in storage — and «Compare» stays disabled, so nothing
 *      is compared against it.
 *
 * Every state is read off the picker's root (`-control`: `data-eligibility`,
 * `data-benchmark-state`, `data-benchmark-id`) and off what reaches the wire; never off a label.
 * The engine is answered here, by a copy of `risk-lab.spec.ts`'s `answerEligibility` (a spec may
 * not import another), so its verdicts are this file's and not the lane's seed. The live-price
 * poll is held for the whole test, as in `risk-benchmark-shared.spec.ts` and for its reasons: an
 * answered poll writes prices into the lane's database and invalidates the risk cache under the
 * requests these tests read. Nothing to restore: the choice lives in this context's
 * `localStorage`, and no row is written.
 */

/** The picker's test id on this page: `-control`, `-trigger`, `-search` and `-blocked` hang off it. */
const COMPARISON_PICKER = 'risk-comparison-asset-select';

type EligibilityLevel = 'eligible' | 'warning' | 'ineligible';
/** `RiskEligibilityReason` (`schemas/risk.py`): the codes the engine can give. */
type EligibilityReason = 'no_price_history' | 'no_prices' | 'too_few_quotes' | 'missing_fx' | 'starts_late' | 'stale_at_end';

/** One verdict of the engine: a level, and the codes behind it. */
interface Verdict {
    level: EligibilityLevel;
    reasons: readonly EligibilityReason[];
}

const ELIGIBLE: Verdict = {level: 'eligible', reasons: []};
/** Ruled out for the period: not one quote in it. */
const NO_PRICES: Verdict = {level: 'ineligible', reasons: ['no_prices']};

/**
 * The engine's thresholds, copied as `risk-lab.spec.ts` copies them (`RISK_MIN_OBSERVATIONS`,
 * `STALE_PRICE_THRESHOLD_DAYS`): the picker quotes them in its sentences, nothing here asserts on them.
 */
const ENGINE_MIN_QUOTES = 20;
const ENGINE_STALE_DAYS = 7;
/** Quotes in the period of an admitted asset: comfortably above the threshold. */
const AMPLE_QUOTES = 60;

/** One question the page put to the engine, as it put it. */
interface EligibilityCall {
    assetIds: number[];
    dateRange: {start: string; end: string | null};
    targetCurrency: string;
}

/**
 * Answer `POST /risk/eligibility` with this test's verdicts, and keep what the page asked: a copy
 * of `answerEligibility` in `risk-lab.spec.ts`, with its behaviour. Every requested id gets a
 * verdict, deduplicated and in request order, as the engine answers; the body goes through the
 * generated schema because the client validates every response, and a stub that drifted from the
 * contract would otherwise surface as a failed call with nothing pointing here.
 */
async function answerEligibility(page: Page, verdictFor: (assetId: number) => Verdict = () => ELIGIBLE): Promise<EligibilityCall[]> {
    const calls: EligibilityCall[] = [];
    await page.route('**/api/v1/risk/eligibility', async (route) => {
        const sent = (route.request().postDataJSON() ?? {}) as {asset_ids?: number[]; date_range?: {start?: string; end?: string | null}; target_currency?: string};
        const assetIds = [...new Set(sent.asset_ids ?? [])];
        const start = sent.date_range?.start ?? '';
        const end = sent.date_range?.end ?? null;
        const lastDay = end ?? start;
        calls.push({assetIds, dateRange: {start, end}, targetCurrency: sent.target_currency ?? ''});
        const body = schemas.RiskEligibilityResponse.parse({
            items: assetIds.map((assetId) => {
                const verdict = verdictFor(assetId);
                // An asset with no quote in the period has no first or last one to report either.
                const quoted = !verdict.reasons.includes('no_prices');
                return {
                    asset_id: assetId,
                    level: verdict.level,
                    reasons: [...verdict.reasons],
                    first_quote: quoted ? start : null,
                    last_quote: quoted ? lastDay : null,
                    quotes_in_period: quoted ? AMPLE_QUOTES : 0,
                };
            }),
            min_quotes: ENGINE_MIN_QUOTES,
            stale_days: ENGINE_STALE_DAYS,
        });
        await route.fulfill({status: 200, contentType: 'application/json', body: JSON.stringify(body)});
    });
    return calls;
}

interface CatalogueAsset {
    id: number;
    display_name: string;
    is_benchmark?: boolean;
}

/**
 * Three distinct assets, each picked for the property its case needs and, within it, the lowest
 * id: `populate_mock_data.py` creates those before any spec runs, so a neighbour's freshly created
 * asset is never the one picked. The asset whose page is opened, a benchmark the engine will rule
 * out, and a benchmark it admits.
 */
async function castForEligibility(page: Page): Promise<{subject: CatalogueAsset; ruledOut: CatalogueAsset; admitted: CatalogueAsset}> {
    const response = await page.request.get('/api/v1/assets/query');
    expect(response.ok(), 'the asset list must answer: it is what the picker offers').toBe(true);
    const all = ((await response.json()) as CatalogueAsset[]).sort((left, right) => left.id - right.id);
    const benchmarks = all.filter((asset) => asset.is_benchmark === true);
    if (benchmarks.length < 2) throw new Error('Two benchmarks are needed, one ruled out and one admitted. populate_mock_data.py flags its INDEX assets as benchmarks.');
    const subject = all.find((asset) => asset.is_benchmark !== true);
    if (!subject) throw new Error('No asset besides the benchmarks whose page could be opened. Check populate_mock_data.py seeding.');
    return {subject, ruledOut: benchmarks[0], admitted: benchmarks[1]};
}

/** The user id the benchmark store scopes its key with, asked of the endpoint the app asks. */
async function currentUserId(page: Page): Promise<number> {
    const response = await page.request.get('/api/v1/auth/me');
    expect(response.ok(), 'the shared benchmark lives under a user-scoped key, so the test needs the id the app resolves').toBe(true);
    const body = (await response.json()) as {user?: {id?: number}};
    const id = body.user?.id;
    expect(Number.isInteger(id), `auth/me must publish an integer user id, read ${JSON.stringify(body.user)}`).toBe(true);
    return id as number;
}

async function readKey(page: Page, key: string): Promise<string | null> {
    return page.evaluate((storageKey) => window.localStorage.getItem(storageKey), key);
}

/**
 * Put the reader's shared choice in storage, or take it out, and return its key
 * (`riskBenchmarkStore`'s `storageKey()`, reproduced). Read by the runtime that the full document
 * load in `openAssetRiskTab` starts afterwards, as in `risk-benchmark-shared.spec.ts`.
 */
async function storeBenchmark(page: Page, assetId: number | null): Promise<string> {
    const key = `lf_${await currentUserId(page)}_risk_benchmark_asset`;
    const value = assetId === null ? null : String(assetId);
    await page.evaluate(
        ([storageKey, stored]) => {
            if (stored === null) window.localStorage.removeItem(storageKey);
            else window.localStorage.setItem(storageKey, stored);
        },
        [key, value] as const,
    );
    expect(await readKey(page, key), 'the seed did not land in storage').toBe(value);
    return key;
}

/** The asset's page, Risk tab, by a full document load; returns once the comparison controls are up. */
async function openAssetRiskTab(page: Page, assetId: number): Promise<void> {
    await navigateTo(page, `/assets/${assetId}?tab=risk`);
    await expect(page.getByTestId('asset-detail-risk-panel')).toBeVisible({timeout: 15_000});
    // Every section is gated on the capability catalog: wait for the gate, then for what is behind it.
    await waitForRiskCatalog(page);
    await expect(page.getByTestId('risk-comparison-controls')).toBeVisible();
}

/**
 * Open the comparison picker and end with it open: asked for the end state, clicked only while it
 * is not there, because a click within 200 ms of a close is swallowed and a blind second click on
 * an open list would close it again.
 */
async function openComparisonPicker(page: Page): Promise<void> {
    const trigger = page.getByTestId(`${COMPARISON_PICKER}-trigger`);
    await expect(async () => {
        if ((await trigger.getAttribute('aria-expanded')) !== 'true') await trigger.click();
        await expect(trigger).toHaveAttribute('aria-expanded', 'true', {timeout: 1_000});
    }, 'the comparison picker never opened').toPass({timeout: 8_000});
}

/** The page's own window and currency, as the panel sent them in its latest risk request about this asset. */
function pageQuestion(requests: RiskRequest[], assetId: number): {start: string; end: string | null; currency: string} | null {
    const own = requests.filter((request) => request.scope.kind === 'asset' && request.scope.asset_id === assetId);
    const latest = own[own.length - 1];
    return latest ? {start: latest.date_range.start, end: latest.date_range.end ?? null, currency: latest.target_currency} : null;
}

/** The `comparison_asset_id` of every comparison the panel asked about this asset, in order. */
function comparisonIdsFor(requests: RiskRequest[], assetId: number): number[] {
    return requests
        .filter((request) => request.scope.kind === 'asset' && request.scope.asset_id === assetId)
        .flatMap((request) => request.analytics)
        .filter((analytic) => analytic.analytic_code === 'comparison')
        .map((analytic) => Number(analytic.parameters?.comparison_asset_id));
}

test.describe('Asset Risk tab — the benchmark picker knows what the engine can measure (stage 2, D378)', () => {
    test.beforeEach(async ({page}) => {
        await holdLivePricePoll(page);
        await login(page, TEST_USER);
    });

    test('lists apart the benchmark the engine rules out for the page’s period, keeps an admitted one choosable, and asks with the page’s period and currency', async ({page}) => {
        const requests = await installRiskMocks(page);
        const {subject, ruledOut, admitted} = await castForEligibility(page);
        // `installRiskMocks` leaves eligibility to the lane's engine: this stub answers it instead.
        const eligibility = await answerEligibility(page, (assetId) => (assetId === ruledOut.id ? NO_PRICES : ELIGIBLE));
        await storeBenchmark(page, null);

        await openAssetRiskTab(page, subject.id);
        const control = page.getByTestId(`${COMPARISON_PICKER}-control`);
        await expect(control, 'the picker never had the engine’s verdicts: it did not ask, or its answer never landed').toHaveAttribute('data-eligibility', 'ready', {timeout: 10_000});

        // The question carried the page's own window and currency: those its risk requests about this asset carry.
        await expect(page.getByTestId('asset-detail-risk-panel').getByTestId('risk-analysis-panel')).toHaveAttribute('data-busy', 'false', {timeout: 15_000});
        const asked = pageQuestion(requests, subject.id);
        if (!asked) throw new Error('The panel sent no risk request about this asset, so the page’s period is unknown to this test.');
        await expect
            .poll(
                () => {
                    const latest = eligibility[eligibility.length - 1];
                    return latest ? {start: latest.dateRange.start, end: latest.dateRange.end, currency: latest.targetCurrency} : null;
                },
                {timeout: 5_000, message: 'the eligibility question did not carry the page’s period and currency'},
            )
            .toEqual(asked);
        expect(eligibility[eligibility.length - 1]?.assetIds, 'the question did not judge the benchmark the engine rules out').toContain(ruledOut.id);

        await openComparisonPicker(page);
        const blocked = page.getByTestId(`${COMPARISON_PICKER}-blocked`);
        const ruledOutOption = blocked.getByTestId(`search-select-option-${ruledOut.id}`);
        await expect(ruledOutOption, `${ruledOut.display_name} (#${ruledOut.id}) is not listed apart`).toBeVisible();
        await expect(ruledOutOption).toBeDisabled();
        await expect(ruledOutOption).toHaveAttribute('data-level', 'ineligible');
        await expect(ruledOutOption).toHaveAttribute('data-reasons', 'no_prices');

        // Scoped to this picker: `search-select-option-*` is shared by every select on the page.
        const admittedOption = page.getByTestId(COMPARISON_PICKER).getByTestId(`search-select-option-${admitted.id}`);
        await expect(admittedOption, `${admitted.display_name} (#${admitted.id}) is admitted and must be on offer`).toBeEnabled();
        await expect(blocked.getByTestId(`search-select-option-${admitted.id}`)).toHaveCount(0);
        await admittedOption.click();
        await expect(control).toHaveAttribute('data-benchmark-id', String(admitted.id));
        await expect(control).toHaveAttribute('data-benchmark-state', 'set');
        await expect(page.getByTestId('risk-comparison-run')).toBeEnabled();
    });

    test('keeps a stored benchmark the engine rules out as blocked: shown and stored, «Compare» disabled, nothing compared', async ({page}) => {
        const requests = await installRiskMocks(page);
        const {subject, ruledOut} = await castForEligibility(page);
        const eligibility = await answerEligibility(page, (assetId) => (assetId === ruledOut.id ? NO_PRICES : ELIGIBLE));
        const key = await storeBenchmark(page, ruledOut.id);

        await openAssetRiskTab(page, subject.id);
        const control = page.getByTestId(`${COMPARISON_PICKER}-control`);
        await expect(control, 'a stored benchmark the engine rules out for the period must read blocked').toHaveAttribute('data-benchmark-state', 'blocked', {timeout: 10_000});
        await expect(control, 'a blocked benchmark stays the current choice').toHaveAttribute('data-benchmark-id', String(ruledOut.id));
        await expect(page.getByTestId('risk-comparison-run'), '«Compare» must stay disabled on a blocked benchmark').toBeDisabled();
        expect(
            eligibility.some((call) => call.assetIds.includes(ruledOut.id)),
            'premise: the engine was asked about the stored benchmark',
        ).toBe(true);

        // Shown where the picker marks it: current, in the section apart.
        await openComparisonPicker(page);
        const ruledOutOption = page.getByTestId(`${COMPARISON_PICKER}-blocked`).getByTestId(`search-select-option-${ruledOut.id}`);
        await expect(ruledOutOption).toHaveAttribute('aria-selected', 'true');
        await expect(ruledOutOption).toBeDisabled();

        // Presence barrier for the absence below: the panel finished its own load and talked to the
        // risk endpoint about this asset, so it had every chance to ask for a comparison.
        await expect(page.getByTestId('asset-detail-risk-panel').getByTestId('risk-analysis-panel')).toHaveAttribute('data-busy', 'false', {timeout: 15_000});
        await expect
            .poll(() => requests.some((request) => request.scope.kind === 'asset' && request.scope.asset_id === subject.id), {
                timeout: 10_000,
                message: 'the panel never asked the risk endpoint about this asset, so "no comparison" would prove nothing',
            })
            .toBe(true);
        expect(comparisonIdsFor(requests, subject.id), 'a comparison went out against a benchmark the engine rules out').toEqual([]);
        expect(await readKey(page, key), 'the stored benchmark was cleared: D378 keeps the choice').toBe(String(ruledOut.id));
    });
});
