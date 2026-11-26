/**
 * Asset Detail, «Risk and scenarios» tab — owned by the Risk workstream.
 *
 * Since RN-17 (lot b) the tab is an x-ray of the asset: `AssetRiskTab` mounts the Dashboard's levels panel
 * (`RiskLevelsPanel`, scope `{kind: 'asset'}`) inside the page's `asset-detail-risk-panel`, keeps only the levels that
 * have a meaning on one asset — L1, L3 «compared with a reference», L4 with its three tools; no L2 — and adds two
 * notes of its own: the value of your position the amounts are on (`asset-risk-position`, read once from the
 * portfolio report grouped by asset) and the «prices from the plan» note (`asset-risk-plan-prices`) on a scheduled
 * investment, a HOLD or a crowdfunding asset. The legacy `RiskAnalysisPanel` and its testids (`risk-comparison-*`,
 * `risk-stress-*`, `risk-replay-audit*`, the beta banner, «configure signals») are gone from this page, so the net this
 * file used to be — «Asset Detail left identical» (D8, D47, D82) — is superseded by this lot: the cases below pin what
 * the tab is now.
 *
 * Inputs every test fixes, never assertions:
 *   1. the live-price poll is held from `beforeEach`, before any page opens. The Assets page and Asset Detail poll
 *      `POST /assets/prices/current`, and an answered poll asks the real price providers and writes today's prices
 *      into the lane — moving the very prices the eligibility engine judges and dropping the risk cache under the
 *      requests these tests read. Held, the poll reaches nothing; «the net's flow» test pins it;
 *   2. the risk catalogue, the scenario catalogue and every risk query are the stub's (`installRiskMocks`); the
 *      scenario catalogue is widened here by a sector preset (`answerScenarioCatalog`), because the shared one only
 *      holds an `asset_class` shock, which one asset never offers;
 *   3. the eligibility engine is answered here (`answerEligibility`), every asked asset admitted unless a test says
 *      otherwise, so the picker's verdicts are this file's and not the lane's seed.
 *
 * Every subject is picked by property from `/api/v1/assets/query`, lowest id first: `populate_mock_data.py` creates
 * those before any spec runs, so a neighbour's freshly created asset is never the one picked. Nothing is written to
 * the database; the benchmark choice and the open L4 tools live in this context's `localStorage`.
 */
import {expect, test, type Locator, type Page, type Request} from '../fixtures/playwright';

import {login, navigateTo} from '../fixtures/auth-helpers';
import {TEST_USER} from '../fixtures/test-users';
import {goToAssetsPage} from '../assets/assets-helpers';
import {schemas} from '../../src/lib/api/generated';
import {installRiskMocks, type RiskRequest} from './risk-mocks';

/** Every live-price poll each page's hold has held, in order: what the net's hygiene pin compares with what the page sent. */
const heldLivePricePolls = new WeakMap<Page, Request[]>();

/**
 * Hold the live-price poll, unanswered, for the whole test: the page's own poll, which nothing else is inert against.
 * Held, never answered, and never unrouted:
 * removing the route would release what it holds. This copy also keeps what it held, for the hygiene pin to read.
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

// ─── Subjects, picked by property ───────────────────────────────────────────────────────────────────────────────────

interface CatalogueAsset {
    id: number;
    display_name: string;
    asset_type?: string | null;
    provider_code?: string | null;
    active?: boolean;
    is_benchmark?: boolean;
}

/** The provider whose series is generated from a plan (`parametric_generation`): the seed's scheduled investments. */
const PARAMETRIC_PROVIDER = 'scheduled_investment';
/** The asset types `pricesFromPlan` treats as priced by hand or by a plan (Q20). */
const PLAN_PRICED_TYPES: readonly string[] = ['HOLD', 'CROWDFUND', 'CROWDFUND_REAL_ESTATE'];

/** Every asset the app lists, lowest id first. */
async function listAssets(page: Page): Promise<CatalogueAsset[]> {
    const response = await page.request.get('/api/v1/assets/query');
    expect(response.ok(), 'the asset list must answer: the subjects are picked from it').toBe(true);
    return ((await response.json()) as CatalogueAsset[]).sort((left, right) => left.id - right.id);
}

/** An active stock or ETF priced by a market provider, and not a benchmark: an asset whose prices are observed. */
function isMarketAsset(asset: CatalogueAsset): boolean {
    return asset.active !== false && asset.is_benchmark !== true && ['STOCK', 'ETF'].includes((asset.asset_type ?? '').toUpperCase()) && !!asset.provider_code && asset.provider_code !== PARAMETRIC_PROVIDER;
}

async function marketSubject(page: Page): Promise<CatalogueAsset> {
    const subject = (await listAssets(page)).find(isMarketAsset);
    if (!subject) throw new Error('No active market-priced STOCK/ETF in the asset list. Check populate_mock_data.py seeding.');
    return subject;
}

// ─── The tab and its levels ─────────────────────────────────────────────────────────────────────────────────────────

/**
 * The levels panel inside this page's risk tab, once its capability catalogue has landed and its base wave is in:
 * every section is gated on the catalogue, so an absent section means "unsupported" or "not loaded yet" until the
 * panel says which. A copy of `waitForRiskLevels` in `risk-analysis.spec.ts` (a spec may not import another), scoped
 * to the tab.
 */
async function waitForRiskLevels(page: Page): Promise<Locator> {
    const panel = page.getByTestId('asset-detail-risk-panel').getByTestId('risk-levels-panel');
    await expect(panel).toHaveAttribute('data-catalog', 'ready', {timeout: 20_000});
    await expect(panel).toHaveAttribute('data-busy', 'false', {timeout: 20_000});
    return panel;
}

/** The asset's page, Risk tab, by a full document load; returns the levels panel once it is ready. */
async function openAssetRiskTab(page: Page, assetId: number): Promise<Locator> {
    await navigateTo(page, `/assets/${assetId}?tab=risk`);
    await expect(page.getByTestId('asset-detail-risk-panel')).toBeVisible({timeout: 15_000});
    await expect(page.getByTestId('asset-risk-tab')).toBeVisible();
    return waitForRiskLevels(page);
}

/**
 * Open L4's drawer and leave it demonstrably open, whichever state it was in: asked before clicking, and ended on
 * L4's body being on screen. A copy of `openLevel4Drawer` in `risk-analysis.spec.ts`.
 */
async function openLevel4Drawer(panel: Locator): Promise<Locator> {
    const level4 = panel.getByTestId('risk-level-4');
    await expect(level4).toBeVisible({timeout: 10_000});
    if ((await level4.getAttribute('data-open')) !== 'true') await panel.getByTestId('risk-level-4-toggle').click();
    await expect(level4).toHaveAttribute('data-open', 'true');
    await expect(panel.getByTestId('risk-l4')).toBeVisible({timeout: 8_000});
    return level4;
}

/** L4's tools, in the one order they are ever drawn in: observed, assumed, modelled. */
const L4_TOOLS = ['replay', 'shock', 'simulation'] as const;

/**
 * Open L4 with its three tools on screen, whichever of them were open before (D377: the reader picks them, and the
 * ones left open come back from storage). Each tool is first seen settled into exactly one of its two states — its box
 * or its add button — so the click is chosen on a selector that has rendered. A copy of `openLevel4` in
 * `risk-analysis.spec.ts`.
 */
async function openLevel4(panel: Locator): Promise<Locator> {
    const level4 = await openLevel4Drawer(panel);
    for (const tool of L4_TOOLS) {
        const box = level4.getByTestId(`risk-l4-${tool}`);
        const add = level4.getByTestId(`risk-l4-add-${tool}`);
        await expect(box.or(add), `L4 must show the ${tool} either open or offered, exactly once`).toHaveCount(1);
        if ((await add.count()) > 0) await add.click();
        await expect(box, `the ${tool} did not open`).toBeVisible({timeout: 8_000});
    }
    await expect(level4.locator('[data-testid^="risk-l4-add-"]'), 'a tool is still offered with all three open').toHaveCount(0);
    return level4;
}

/** The risk requests about this asset, in order. */
function aboutAsset(requests: readonly RiskRequest[], assetId: number): RiskRequest[] {
    return requests.filter((request) => request.scope.kind === 'asset' && request.scope.asset_id === assetId);
}

/** The parameters of the first analytic about this asset that `match` accepts, or undefined. */
function parametersAbout(requests: readonly RiskRequest[], assetId: number, match: (code: string, parameters: Record<string, unknown>) => boolean): Record<string, unknown> | undefined {
    return aboutAsset(requests, assetId)
        .flatMap((request) => request.analytics)
        .find((analytic) => match(analytic.analytic_code, analytic.parameters ?? {}))?.parameters;
}

// ─── The scenario catalogue, widened by a sector preset ─────────────────────────────────────────────────────────────

const SHOCK_LIMITS = {minimum_shock: -1, maximum_shock: 1, maximum_buckets: 100};
const SHOCK_EDITABLE = {dimension: false, bucket_shocks: true, manual_overrides: true};

/** A hypothetical shock as the backend's YAML declares one (`scenario_catalog/built_in/hypothetical/`). */
function shockScenario(id: string, dimension: 'asset_class' | 'sector', bucketShocks: Record<string, number>) {
    const words = {en: id, it: id, fr: id, es: id};
    return {
        source: 'built_in',
        source_file: `hypothetical/${id}.yml`,
        scenario: {schema_version: 1, id, kind: 'hypothetical_shock', tags: ['e2e'], name: words, description: words, allowed_dimensions: [dimension], defaults: {dimension, bucket_shocks: bucketShocks}, editable: SHOCK_EDITABLE, limits: SHOCK_LIMITS},
    };
}

/** The asset-class preset one asset must not offer, and the sector preset it runs (shaped like `banking_crisis.yml`). */
const TYPE_PRESET = 'global_risk_off';
const SECTOR_PRESET = 'banking_crisis';
const SECTOR_SHOCKS = {Financials: -0.4, Other: 0};

/**
 * Answer `GET /risk/scenario-catalog` with both kinds of shock: registered after `installRiskMocks`, so it wins over
 * the shared catalogue, which only holds the `asset_class` one. Without that preset beside the sector one, «no
 * asset-class preset» would be true of an empty list. Validated by the generated schema before it leaves.
 */
async function answerScenarioCatalog(page: Page): Promise<void> {
    const body = {
        items: [
            {
                source: 'built_in',
                source_file: 'historical/custom_period.yml',
                scenario: {
                    schema_version: 1,
                    id: 'custom_period',
                    kind: 'historical_replay',
                    tags: ['custom'],
                    name: {en: 'custom_period', it: 'custom_period', fr: 'custom_period', es: 'custom_period'},
                    description: {en: 'custom_period', it: 'custom_period', fr: 'custom_period', es: 'custom_period'},
                    defaults: {start: null, end: null, missing_history_policy: 'manual_proxy_or_exclude', composition_policy: 'current_buy_and_hold'},
                    editable: {dates: true, missing_history_policy: true, proxies: true, exclusions: true},
                    limits: {minimum_calendar_days: 1, maximum_calendar_days: null},
                },
            },
            shockScenario(TYPE_PRESET, 'asset_class', {STOCK: -0.2, ETF: -0.15, BOND: -0.05, OTHER: 0}),
            shockScenario(SECTOR_PRESET, 'sector', SECTOR_SHOCKS),
        ],
        geography_groups: [],
        status: {schema_version: 1, loaded_at: '2026-01-31T12:00:00Z', built_in_count: 3, host_count: 0, warning_count: 0},
        warnings: [],
    };
    schemas.RiskScenarioCatalogResponse.parse(body);
    await page.route('**/api/v1/risk/scenario-catalog', async (route) => {
        await route.fulfill({status: 200, contentType: 'application/json', body: JSON.stringify(body)});
    });
}

// ─── The eligibility engine and the stored benchmark ────────────────────────────────────────────────────────────────

type EligibilityLevel = 'eligible' | 'warning' | 'ineligible';
/** `RiskEligibilityReason` (`schemas/risk/vocabulary.py`): the codes the engine can give. */
type EligibilityReason = 'no_price_history' | 'no_prices' | 'too_few_quotes' | 'missing_fx' | 'starts_late' | 'stale_at_end';

/** One verdict of the engine: a level, and the codes behind it. */
interface Verdict {
    level: EligibilityLevel;
    reasons: readonly EligibilityReason[];
}

const ELIGIBLE: Verdict = {level: 'eligible', reasons: []};

/** The engine's thresholds, copied as `risk-lab.spec.ts` copies them: the picker quotes them, nothing asserts on them. */
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
 * Answer `POST /risk/eligibility` with this test's verdicts, and keep what the page asked: a copy of
 * `answerEligibility` in `risk-lab.spec.ts`. Every requested id gets a verdict, deduplicated and in request order, as
 * the engine answers; the body goes through the generated schema because the client validates every response.
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
                return {asset_id: assetId, level: verdict.level, reasons: [...verdict.reasons], first_quote: quoted ? start : null, last_quote: quoted ? lastDay : null, quotes_in_period: quoted ? AMPLE_QUOTES : 0};
            }),
            min_quotes: ENGINE_MIN_QUOTES,
            stale_days: ENGINE_STALE_DAYS,
        });
        await route.fulfill({status: 200, contentType: 'application/json', body: JSON.stringify(body)}).catch(() => undefined);
    });
    return calls;
}

// ─── The position the amounts are on ───────────────────────────────────────────────────────────────────────────────

/** The value the «owned» shape gives the subject's row: a figure no seeded holding has. */
const OWNED_VALUE = '12345.67';

type PositionShape = 'owned' | 'not_owned';

interface PositionReportHandle {
    /** Which shape the next answer takes. */
    shape: PositionShape;
    /** How many tab reads were answered, in each shape. */
    answered: PositionShape[];
    /** Why an answer could not be shaped: read by the test, never thrown inside the handler. */
    problems: string[];
}

/**
 * Answer the tab's own read of the portfolio report (`group_by: 'asset'`) with the subject owned or not owned.
 *
 * The real answer is fetched and patched rather than written by hand: the report and its holdings are strict schemas
 * with many required fields, and a hand-written body that drifted from them would fail the client's validation,
 * leave the tab with no value, and make «not owned» green for the wrong reason. Owned: the subject's row is a copy of
 * a real holding row, with the subject's id and `OWNED_VALUE`. Not owned: the subject's rows are taken out. Either
 * body passes the generated schema before it leaves. Every other report request goes on untouched. A read, never a
 * write: nothing to restore.
 */
async function answerPositionReport(page: Page, subject: CatalogueAsset, shape: PositionShape): Promise<PositionReportHandle> {
    const handle: PositionReportHandle = {shape, answered: [], problems: []};
    await page.route('**/api/v1/portfolio/report', async (route) => {
        const sent = (route.request().postDataJSON() ?? {}) as {group_by?: string};
        if (route.request().method() !== 'POST' || sent.group_by !== 'asset') {
            await route.fallback();
            return;
        }
        const current = handle.shape;
        const response = await route.fetch();
        const report = (await response.json()) as {summary?: {holdings?: Array<Record<string, unknown>>} | null};
        const holdings = report.summary?.holdings;
        if (!response.ok() || !report.summary || !Array.isArray(holdings)) {
            handle.problems.push(`the real report did not answer with a summary (HTTP ${response.status()})`);
            await route.fulfill({response});
            return;
        }
        const others = holdings.filter((row) => row.asset_id !== subject.id);
        if (current === 'owned') {
            const template = holdings[0];
            if (!template) {
                handle.problems.push('the real report holds no row to copy the owned row from: the test user owns nothing. Check populate_mock_data.py.');
                await route.fulfill({response});
                return;
            }
            report.summary.holdings = [...others, {...template, asset_id: subject.id, asset_name: subject.display_name, current_value: OWNED_VALUE}];
        } else {
            report.summary.holdings = others;
        }
        const parsed = schemas.PortfolioReportResponse.safeParse(report);
        if (!parsed.success) {
            handle.problems.push(`the ${current} report does not pass the generated schema: ${parsed.error.message.slice(0, 400)}`);
            await route.fulfill({response});
            return;
        }
        await route.fulfill({response, json: report});
        handle.answered.push(current);
    });
    return handle;
}

// Earned parallel: every block owns the data it touches (nothing written, choices in this context's storage) and
// waits on published state, so it shares the backend with its neighbours instead of queueing behind them.
test.describe.configure({mode: 'parallel'});

test.describe('Asset Detail Risk tab — the levels on one asset (RN-17)', () => {
    test.beforeEach(async ({page}) => {
        // Input 1 (header), not an assertion: held before any page opens.
        await holdLivePricePoll(page);
        await login(page, TEST_USER);
    });

    test('asset detail preserves Overview and mounts the levels on the asset through its dedicated tab', async ({page}) => {
        const requests = await installRiskMocks(page);
        await answerEligibility(page);
        const subject = await marketSubject(page);

        await navigateTo(page, `/assets/${subject.id}`);
        await expect(page.getByTestId('asset-detail-page')).toBeVisible({timeout: 15_000});
        await expect(page.getByTestId('asset-detail-signals-toggle')).toBeVisible({timeout: 8_000});
        await expect(page.getByTestId('asset-detail-risk-panel')).toHaveCount(0);

        await page.getByTestId('asset-detail-tab-risk').click();
        await expect(page).toHaveURL(/[?&]tab=risk(?:&|$)/);
        await expect(page.getByTestId('asset-detail-risk-panel')).toBeVisible({timeout: 12_000});
        await expect(page.getByTestId('asset-detail-risk-panel').getByTestId('asset-risk-tab')).toBeVisible();
        const panel = await waitForRiskLevels(page);
        await expect(panel).toHaveAttribute('data-scope', 'asset');

        // The levels that have a meaning on one asset — and, the barrier for the absence below, they are on screen.
        await expect(panel.getByTestId('risk-level-1')).toBeVisible();
        await expect(panel.getByTestId('risk-level-4')).toBeVisible();
        // 81 U29 (developer, P-12): no «Compared with a reference» on one asset — neither its picker nor its table. The rate
        // field stays under the period line (81 U25): L1's semi-deviation counts from it.
        await expect(panel.getByTestId('risk-level-3'), 'the benchmark level is drawn on one asset').toHaveCount(0);
        await expect(panel.getByTestId('risk-l3-benchmark')).toHaveCount(0);
        await expect(panel.getByTestId('risk-free-rate')).toBeVisible();
        await expect(panel.getByTestId('risk-level-2'), 'one asset has nothing to diversify: L2 is drawn').toHaveCount(0);
        await expect(page.getByTestId('asset-detail-signals-toggle')).toHaveCount(0);
        // No beta banner anywhere on the tab: the simulation left beta (RN-06, Q6), and nothing else here ever was.
        await expect(page.getByTestId('risk-beta-banner')).toHaveCount(0);

        // Every risk question the tab asked is about this asset, and nothing else.
        await expect.poll(() => aboutAsset(requests, subject.id).length, {timeout: 10_000, message: 'the tab never asked the risk endpoint about its asset'}).toBeGreaterThan(0);
        expect(
            requests.filter((request) => !(request.scope.kind === 'asset' && request.scope.asset_id === subject.id)).map((request) => JSON.stringify(request.scope)),
            'the asset tab asked a risk question about another scope',
        ).toEqual([]);

        // Back to Overview: the chart's signals return and the risk panel goes.
        await page.getByTestId('asset-detail-tab-overview').click();
        await expect(page.getByTestId('asset-detail-signals-toggle')).toBeVisible({timeout: 8_000});
        await expect(page.getByTestId('asset-detail-risk-panel')).toHaveCount(0);
    });

    /**
     * RN-18: «How does it move?» is the same block on one asset as on the Dashboard — right after L1, its four cards
     * filled from the answers L1 already reads (the stub's KPI, 30-day VaR and drawdown summary, all about this asset).
     * Four cards and no more: on one asset volatility, annual return, Sharpe and Sortino are L3's (the next test).
     */
    test('«How does it move?» follows L1 on one asset, with its four cards filled', async ({page}) => {
        const requests = await installRiskMocks(page);
        await answerEligibility(page);
        const subject = await marketSubject(page);
        const panel = await openAssetRiskTab(page, subject.id);

        // Right after L1; only the level sections publish `data-level` under a `risk-level-*` id.
        await expect
            .poll(() => panel.locator('section[data-testid^="risk-level-"][data-level]').evaluateAll((nodes) => nodes.slice(0, 2).map((node) => node.getAttribute('data-level'))), {
                timeout: 10_000,
                message: 'the first two levels on the asset are not L1 and «How does it move?»',
            })
            .toEqual(['1', 'move']);

        const move = panel.getByTestId('risk-level-move');
        const cards = move.getByTestId('risk-move-cards');
        await expect(cards).toBeVisible({timeout: 10_000});
        await expect(cards.locator('> div > [data-testid^="risk-move-card-"]'), 'the block on one asset is not exactly its four cards').toHaveCount(4);
        for (const card of ['bestDay', 'bestMonth', 'rally', 'days']) {
            await expect(move.getByTestId(`risk-move-card-${card}-value`), `the ${card} card carries no figure`).toHaveText(/\d/);
        }
        for (const card of ['bestDay', 'bestMonth', 'rally']) {
            await expect(move.getByTestId(`risk-move-card-${card}`), `the ${card} card is not a gain`).toHaveAttribute('data-sentiment', 'positive');
        }
        await expect(move.getByTestId('risk-move-rally-period')).toHaveAttribute('data-from', '2023-12-03');
        await expect(move.getByTestId('risk-move-rally-period')).toHaveAttribute('data-to', '2024-02-05');
        await expect(move.getByTestId('risk-move-best-month-period')).toHaveAttribute('data-from', '2024-01-05');
        await expect(move.getByTestId('risk-move-best-month-period')).toHaveAttribute('data-to', '2024-02-04');
        await expect(move.getByTestId('risk-move-empty')).toHaveCount(0);

        // The figures are this asset's: the drawdown summary they read was asked about it, on the historical wave.
        expect(
            aboutAsset(requests, subject.id)
                .filter((request) => request.mode === 'historical')
                .flatMap((request) => request.analytics.map((analytic) => analytic.analytic_code)),
            'the block read a drawdown summary nobody asked about this asset',
        ).toContain('drawdown_summary');
    });

    test('L4 on one asset: the shock offers no asset-class preset and runs a sector one, the replay says one sentence and draws no tornado, the simulation runs', async ({page}) => {
        const requests = await installRiskMocks(page);
        await answerScenarioCatalog(page);
        await answerEligibility(page);
        const subject = await marketSubject(page);
        const panel = await openAssetRiskTab(page, subject.id);
        const level4 = await openLevel4(panel);

        // --- The shock: by sector, never by asset class --------------------------------------------------------
        // One asset is one class: a shock by class would only restate the class's own figure. The sector preset is
        // the presence barrier that makes the missing class preset a statement about the filter, not a catalogue
        // still loading.
        const shock = level4.getByTestId('risk-shock');
        const sectorPreset = shock.locator(`[data-testid="risk-shock-preset"][data-preset-id="${SECTOR_PRESET}"]`);
        await expect(sectorPreset).toBeVisible({timeout: 10_000});
        await expect(shock.locator(`[data-testid="risk-shock-preset"][data-preset-id="${TYPE_PRESET}"]`), 'one asset is offered a shock by asset class').toHaveCount(0);

        await expect(shock.getByTestId('risk-shock-total')).toHaveCount(0);
        await sectorPreset.click();
        await expect(sectorPreset).toHaveAttribute('data-selected', 'true');
        await expect(shock.getByTestId('risk-shock-total')).toBeVisible({timeout: 10_000});
        // The rendered total means the answer arrived, so its request is already recorded: a one-shot read.
        expect(
            parametersAbout(requests, subject.id, (code, parameters) => code === 'stress' && parameters.method === 'hypothetical'),
            'the sector preset did not reach the server with its own defaults, on this asset',
        ).toMatchObject({method: 'hypothetical', dimension: 'sector', bucket_shocks: SECTOR_SHOCKS});

        // --- The replay: one sentence, no tornado --------------------------------------------------------------
        const replay = level4.getByTestId('risk-replay');
        await expect(replay.getByTestId('risk-replay-total')).toHaveCount(0);
        await replay.getByTestId('risk-replay-run').click();
        await expect(replay.getByTestId('risk-replay-total'), 'the replay on one asset does not say its sentence').toBeVisible({timeout: 10_000});
        // The total above is the barrier: the answer is on screen, so a tornado or a warning would be too.
        await expect(replay.getByTestId('risk-replay-tornado'), 'one asset is drawn a tornado of one bar').toHaveCount(0);
        // Nothing was left out of this replay: no exclusion block, no coverage warning, no «nothing left».
        await expect(replay.getByTestId('risk-replay-excluded')).toHaveCount(0);
        await expect(replay.getByTestId('risk-replay-coverage')).toHaveCount(0);
        await expect(replay.getByTestId('risk-replay-nothing')).toHaveCount(0);
        // The retired audit (D372) does not come back on the asset either.
        await expect(replay.locator('[data-testid^="risk-replay-audit"]')).toHaveCount(0);
        expect(
            parametersAbout(requests, subject.id, (code, parameters) => code === 'stress' && parameters.method === 'historical_replay'),
            'the replay was not asked about this asset, with nothing excluded by hand and no stand-in',
        ).toMatchObject({method: 'historical_replay', missing_history_policy: 'manual_proxy_or_exclude', proxy_assets: [], excluded_assets: []});

        // --- The simulation ------------------------------------------------------------------------------------
        const simulation = level4.getByTestId('risk-simulation');
        const simulationQuery = page.waitForRequest(
            (request) => {
                if (request.method() !== 'POST' || !request.url().includes('/api/v1/risk/query')) return false;
                const body = request.postDataJSON() as RiskRequest;
                return body.scope.kind === 'asset' && body.scope.asset_id === subject.id && body.analytics.some((analytic) => analytic.analytic_code === 'simulation');
            },
            {timeout: 10_000},
        );
        await expect(simulation.getByTestId('risk-simulation-run')).toBeEnabled();
        await simulation.getByTestId('risk-simulation-run').click();
        await simulationQuery;
        await expect(simulation.getByTestId('risk-simulation-terminal')).toBeVisible({timeout: 12_000});
        await expect(simulation.getByTestId('risk-simulation-band-range')).toBeVisible();
        await expect(simulation.getByTestId('risk-l4-provenance')).toBeVisible();
        // The defaults on screen are the defaults on the wire: the block bootstrap, 8192 paths over a year, its seed.
        expect(parametersAbout(requests, subject.id, (code) => code === 'simulation')).toMatchObject({process: 'block_bootstrap', sampling_method: 'mc', path_count: 8192, horizon_days: 365, bootstrap_seed: 123456});
    });

    /**
     * Testlist of 25/11: on a phone a period picker pushed its box out of the page, in the simulation's history (a fieldset is
     * as wide as its content by default) and in the replay (so is a flex item). Measured, not looked at, at 375 px, with the
     * three tools of L4 open.
     */
    test('the periods of L4 stay inside their boxes on a phone (TL 25/11)', async ({page}) => {
        await page.setViewportSize({width: 375, height: 812});
        await installRiskMocks(page);
        await answerEligibility(page);
        const subject = await marketSubject(page);
        const panel = await openAssetRiskTab(page, subject.id);
        const level4 = await openLevel4(panel);
        const history = level4.getByTestId('risk-simulation-history');
        await history.getByTestId('risk-simulation-history-chosen').click();
        const period = history.getByTestId('risk-simulation-history-period');
        await expect(period, 'the period picker did not appear').toBeVisible({timeout: 8_000});

        // The fieldset is as wide as its parent, and nothing in it spills out
        const sizes = await history.evaluate((fieldset) => {
            const parent = fieldset.parentElement!;
            const style = getComputedStyle(parent);
            const inner = parent.clientWidth - parseFloat(style.paddingLeft) - parseFloat(style.paddingRight);
            return {fieldset: fieldset.getBoundingClientRect().width, inner, spill: fieldset.scrollWidth - fieldset.clientWidth, page: document.documentElement.scrollWidth - document.documentElement.clientWidth};
        });
        expect(sizes.fieldset, 'the fieldset is wider than its box').toBeLessThanOrEqual(sizes.inner + 1);
        expect(sizes.spill, 'the period sticks out of the fieldset').toBeLessThanOrEqual(1);
        expect(sizes.page, 'the page scrolls sideways').toBeLessThanOrEqual(0);
        const replay = level4.getByTestId('risk-replay-period');
        const replaySizes = await replay.evaluate((box) => ({width: box.getBoundingClientRect().width, inner: box.parentElement!.clientWidth}));
        expect(replaySizes.width, 'the replay’s period is wider than its box').toBeLessThanOrEqual(replaySizes.inner + 1);
    });

    /**
     * The pin of input 1 (header). The flow walks Assets page → Asset Detail → Risk tab, and both pages poll the
     * current price. This compares what the page sent — every request to the poll's path, seen by the browser — with
     * what the hold held:
     *   - the page did poll, so the hold is in the flow's path and «none escaped» is not vacuous;
     *   - every poll it sent was held: none continued to the backend, which would have asked the providers.
     * It lives in this block because what it proves is this block's `beforeEach`. Nothing to restore.
     */
    test('the net’s flow reaches no price provider: it does poll, and every live-price poll it sends is held', async ({page}, testInfo) => {
        const sent: Request[] = [];
        page.on('request', (request) => {
            if (isLivePricePoll(request)) sent.push(request);
        });
        await installRiskMocks(page);
        await answerEligibility(page);
        const subject = await marketSubject(page);

        await goToAssetsPage(page);
        const card = page.getByTestId(`asset-card-${subject.id}`);
        await expect(card, `${subject.display_name} (#${subject.id}) has no card on the Assets page`).toBeVisible({timeout: 8_000});
        await card.click();
        await expect(page.getByTestId('asset-detail-page')).toBeVisible({timeout: 12_000});
        await page.getByTestId('asset-detail-tab-risk').click();
        await expect(page.getByTestId('asset-detail-risk-panel')).toBeVisible({timeout: 12_000});
        await waitForRiskLevels(page);

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
 * ─── The tab's own notes: the position the amounts are on, and prices that come from a plan ───
 *
 * `asset-risk-position` reads the value of your position once, from the portfolio report grouped by asset: shown only
 * when the asset is owned. Both shapes are this file's (`answerPositionReport`), patched over the real answer, so the
 * test says what the tab does with each, not what the seed owns today.
 *
 * `asset-risk-plan-prices` appears when the asset's «prices» are built from a plan: a parametric provider (the seed's
 * scheduled investment) or a type nobody quotes (HOLD, crowdfunding). A market asset carries no such note.
 */
test.describe('Asset Risk tab — the position the amounts are on, and prices from a plan (RN-17)', () => {
    test.beforeEach(async ({page}) => {
        await holdLivePricePoll(page);
        await login(page, TEST_USER);
    });

    test('says which position the amounts are on when the asset is owned, and says nothing when it is not', async ({page}) => {
        await installRiskMocks(page);
        await answerEligibility(page);
        const subject = await marketSubject(page);
        const report = await answerPositionReport(page, subject, 'owned');

        // Owned: the sentence, from the tab's read of the report, once the tab says that read has settled.
        await openAssetRiskTab(page, subject.id);
        const tab = page.getByTestId('asset-risk-tab');
        await expect(tab, 'the tab never said its read of the position settled').toHaveAttribute('data-position', 'ready', {timeout: 15_000});
        await expect(tab.getByTestId('asset-risk-position'), 'the owned asset’s position is not named').toBeVisible();
        expect(report.problems, 'the owned report could not be shaped').toEqual([]);
        expect(report.answered.length > 0 && report.answered.every((shape) => shape === 'owned'), `premise: the tab read the report grouped by asset in the owned shape, read ${JSON.stringify(report.answered)}`).toBe(true);
        const ownedReads = report.answered.length;

        // Not owned: the same asset, the same route, only the shape changes.
        report.shape = 'not_owned';
        await openAssetRiskTab(page, subject.id);
        // Barrier for the absence: the tab says its read of the position has settled (`data-position`), and that read
        // was answered in the not-owned shape.
        await expect(tab, 'the tab never said its read of the position settled').toHaveAttribute('data-position', 'ready', {timeout: 15_000});
        expect(report.problems, 'the not-owned report could not be shaped').toEqual([]);
        await expect.poll(() => report.answered.slice(ownedReads), {timeout: 5_000, message: 'premise: the reload read the report again, in the not-owned shape'}).toContain('not_owned');
        expect(
            report.answered.slice(ownedReads).every((shape) => shape === 'not_owned'),
            `the reload read the report in the owned shape too, read ${JSON.stringify(report.answered)}`,
        ).toBe(true);
        await expect(tab.getByTestId('asset-risk-position'), 'a position is named for an asset nobody owns').toHaveCount(0);
    });

    test('notes that the prices come from a plan on a scheduled investment and on a crowdfunding asset, and not on a market asset', async ({page}) => {
        await installRiskMocks(page);
        await answerEligibility(page);
        const all = await listAssets(page);
        const market = all.find(isMarketAsset);
        const parametric = all.find((asset) => asset.provider_code === PARAMETRIC_PROVIDER && !PLAN_PRICED_TYPES.includes((asset.asset_type ?? '').toUpperCase()));
        const typed = all.find((asset) => PLAN_PRICED_TYPES.includes((asset.asset_type ?? '').toUpperCase()) && asset.provider_code !== PARAMETRIC_PROVIDER) ?? all.find((asset) => PLAN_PRICED_TYPES.includes((asset.asset_type ?? '').toUpperCase()));
        if (!market || !parametric || !typed) throw new Error('A market asset, a scheduled investment and a HOLD/crowdfunding asset are all needed. Check populate_mock_data.py seeding.');

        for (const planned of [parametric, typed]) {
            await openAssetRiskTab(page, planned.id);
            await expect(page.getByTestId('asset-risk-tab').getByTestId('asset-risk-plan-prices'), `${planned.display_name} (#${planned.id}, ${planned.asset_type}, ${planned.provider_code ?? 'no provider'}) is not noted as priced from a plan`).toBeVisible({
                timeout: 10_000,
            });
        }

        // The market asset: the page has finished loading and the levels have landed, then no note.
        await openAssetRiskTab(page, market.id);
        await expect(page.getByTestId('asset-detail-page')).toHaveAttribute('data-busy', 'false', {timeout: 15_000});
        await expect(page.getByTestId('asset-risk-tab')).toBeVisible();
        await expect(page.getByTestId('asset-risk-tab').getByTestId('asset-risk-plan-prices'), `${market.display_name} (#${market.id}) is market-priced and noted as priced from a plan`).toHaveCount(0);
    });
});

/**
 * RN-25 — the rates scenario, on the real backend: the duration the seed puts in a bond's profile (`populate_mock_data.py`,
 * «BTP Italia 2028», 2.15 years from Borsa Italiana) travels through the risk engine to L4's «Rates» box. No risk mock
 * here: the mocked catalogue does not offer `rate_shock`, and what this block proves is the engine's answer on screen.
 */
test.describe('Asset Risk tab — the rates scenario from the profile’s duration (RN-25)', () => {
    test.beforeEach(async ({page}) => {
        await holdLivePricePoll(page);
        await login(page, TEST_USER);
    });

    /** The seeded asset of that name: the seed is the contract, so a missing one is a seeding error, never a skip. */
    async function seeded(page: Page, name: string): Promise<CatalogueAsset> {
        const asset = (await listAssets(page)).find((item) => item.display_name === name);
        if (!asset) throw new Error(`«${name}» is not in the asset list. Check populate_mock_data.py seeding.`);
        return asset;
    }

    /**
     * A test lane serves only `mockenrich` (`dev.py server --test`, plan 68 E8a): no suite reaches the real sites. So
     * `GET /assets/enrichers` does not list the seeded duration's source, and the box could only show its code. The real
     * answer, with that source added under the name it declares, lets the line be checked for the name; the rest of the
     * catalogue is untouched and the risk engine is not mocked.
     */
    async function nameTheSource(page: Page, code: string, name: string): Promise<void> {
        await page.route(/\/api\/v1\/assets\/enrichers(?:\?|$)/, async (route) => {
            const response = await route.fetch();
            const body = schemas.FAEnrichersCatalogue.parse(await response.json());
            if (!body.enrichers.some((enricher) => enricher.code === code)) {
                expect(body.enrichers.length, 'barrier: the lane serves at least one enricher to copy the shape of').toBeGreaterThan(0);
                body.enrichers.push({...body.enrichers[0], code, name});
            }
            await route.fulfill({response, json: body});
        });
    }

    /** L4's rates tool on screen, whether it was left open or is offered. */
    async function openRates(panel: Locator): Promise<Locator> {
        const level4 = await openLevel4Drawer(panel);
        const box = level4.getByTestId('risk-l4-rates');
        const add = level4.getByTestId('risk-l4-add-rates');
        await expect(box.or(add), 'L4 must show the rates tool either open or offered, exactly once').toHaveCount(1);
        if ((await add.count()) > 0) await add.click();
        await expect(box).toBeVisible({timeout: 8_000});
        await expect(box).toHaveAttribute('data-distance', 'assumed');
        return box;
    }

    test('a bond with a duration: the rates box says its source and moves the price both ways, by every step', async ({page}) => {
        const bond = await seeded(page, 'BTP Italia 2028');
        await nameTheSource(page, 'borsa_italiana', 'Borsa Italiana');
        const asked: Array<Record<string, unknown>> = [];
        page.on('request', (request) => {
            if (request.method() !== 'POST' || !request.url().includes('/api/v1/risk/query')) return;
            const body = request.postDataJSON() as RiskRequest;
            if (body.scope.kind !== 'asset' || body.scope.asset_id !== bond.id) return;
            for (const analytic of body.analytics) if (analytic.analytic_code === 'rate_shock') asked.push(analytic.parameters ?? {});
        });

        const panel = await openAssetRiskTab(page, bond.id);
        const box = await openRates(panel);
        const rates = box.getByTestId('risk-rates');
        await expect(rates, 'the engine gave no rates answer on a bond whose profile holds a duration').toBeVisible({timeout: 10_000});
        expect(asked.length, 'the base wave did not ask the rates scenario about this bond').toBeGreaterThan(0);
        expect(asked[asked.length - 1]).toMatchObject({yield_changes: [0.005, 0.01, 0.02, -0.005, -0.01, -0.02]});
        // The duration and its source as the engine sent them (stable handles, not the locale's digits), and the line
        // names the source by the enricher's name, never by its code.
        await expect(rates).toHaveAttribute('data-duration', '2.15');
        await expect(rates).toHaveAttribute('data-source', 'borsa_italiana');
        await expect(rates.getByTestId('risk-rates-source')).toContainText('Borsa Italiana');
        await expect(rates.getByTestId('risk-rates-source')).not.toHaveText(/borsa_italiana/);
        await expect(rates.getByTestId('risk-rates-caveat')).toBeVisible();

        // Opens on rates up by one point: −2.15 × 1 % = −2.15 %, the engine's figure (a float: compared within a hair).
        const result = rates.getByTestId('risk-rates-result');
        await expect(rates).toHaveAttribute('data-direction', 'up');
        await expect(rates).toHaveAttribute('data-step', '0.01');
        const priceChange = async () => Number(await result.getAttribute('data-price-change'));
        expect(await priceChange()).toBeCloseTo(-0.0215, 10);

        await rates.getByTestId('risk-rates-down').click();
        await expect(rates).toHaveAttribute('data-direction', 'down');
        expect(await priceChange()).toBeCloseTo(0.0215, 10);

        for (const [step, expected] of [
            ['0.02', 0.043],
            ['0.005', 0.01075],
        ] as const) {
            await rates.getByTestId(`risk-rates-step-${step}`).click();
            await expect(rates).toHaveAttribute('data-step', step);
            expect(await priceChange(), `rates down by ${step}`).toBeCloseTo(expected, 10);
        }
        await expect(panel.getByTestId('risk-l4-rates-missing'), 'a bond with a duration is told it has none').toHaveCount(0);
    });

    test('a bond without a duration: no rates tool, one line that leads to the Profile', async ({page}) => {
        const bond = await seeded(page, 'BTP Più Sc Fb33 EUR');
        const panel = await openAssetRiskTab(page, bond.id);
        const level4 = await openLevel4Drawer(panel);

        const missing = level4.getByTestId('risk-l4-rates-missing');
        await expect(missing, 'a bond without a duration is not told why it has no rates scenario').toBeVisible({timeout: 10_000});
        // The line is the barrier: the base wave answered, so a rates tool would be offered by now.
        await expect(level4.getByTestId('risk-l4-rates')).toHaveCount(0);
        await expect(level4.getByTestId('risk-l4-add-rates')).toHaveCount(0);

        await missing.getByTestId('risk-l4-rates-missing-profile').click();
        await expect(page).toHaveURL(/[?&]tab=profile(?:&|$)/);
    });
});
