/**
 * Asset Global — the laboratory.
 *
 * `/assets?tab=correlation` mounts `AssetSetRiskPanel`, a page whose whole point
 * is that the user *composes* a set and the matrix answers a question about it.
 * Six things have to stay true, and each test below is one of them:
 *
 *  1. **No money.** With weights → euros → "me"; without weights → percentages →
 *     "these". An asset set has no weights, so no amount of money may appear.
 *  2. The page opens on something small (D19), never on the API's ceiling.
 *  3. The mass actions act on what the user can see, and are reversible.
 *  4. A filter never eats the option that applies it.
 *  5. The pair lists name the redundant pair and the offsetting one.
 *  6. Reordering the matrix loses nothing.
 *
 * Two properties of this file worth knowing before editing it:
 *
 * - **It writes nothing to the database.** Every risk call is stubbed, and the
 *   only state it mutates is the selection, which lives in this browser
 *   context's `localStorage` and dies with it. There is nothing to clean up, and
 *   nothing here can disturb a neighbouring spec's rows.
 * - **No selector is positional.** Pair testids are keyed by asset-id pair,
 *   because the matrix reorders itself by similarity; chips and filters are
 *   found by what they are, not by where they sit.
 */

import {expect, test, type Page} from '../fixtures/playwright';

import {login, navigateTo} from '../fixtures/auth-helpers';
import {expectChartCanvas} from '../fixtures/charts';
import {TEST_USER} from '../fixtures/test-users';

type RiskScope = {kind: 'asset'; asset_id: number} | {kind: 'asset_set'; asset_ids: number[]} | {kind: 'portfolio'; broker_ids?: number[] | null};

interface RiskAnalyticRequest {
    instance_id: string;
    analytic_code: string;
    parameters?: Record<string, unknown>;
}

interface RiskRequest {
    scope: RiskScope;
    date_range: {start: string; end?: string | null};
    target_currency: string;
    mode: 'historical' | 'current_composition';
    composition_policy?: 'current_buy_and_hold' | null;
    analytics: RiskAnalyticRequest[];
}

/**
 * The bait for the no-money net.
 *
 * Today the euro on this page is *latent*, not present: for an `AssetSetRiskScope`
 * the backend builds `asset_values={}` and `scope_value=None`
 * (`risk/service.py`), the stress plugin therefore returns `impact_amount=None`,
 * and the frontend prints an em-dash. So loading the page and finding no `€`
 * would prove nothing — it would stay green with the rule deleted, because the
 * data simply is not there.
 *
 * This magnitude is what the API is *not* allowed to talk the page into printing.
 * It cannot be produced by anything legitimate on this page: correlations live in
 * [-1, 1], percentages are small, observation counts are integers.
 */
const MONEY_AMOUNT = '12345.67';

/**
 * `12345.67` as any of the four shipped locales would group it, plus ungrouped.
 *
 * `Intl.NumberFormat` groups with `,` (en), `.` (it/es) or a narrow no-break
 * space (fr), so the separator is a character class rather than four spellings.
 * Deliberately currency-agnostic: it catches `€12,345.67`, `12.345,67 €` and
 * `$12,345.67` alike, because the offence is the amount, not the symbol.
 */
const MONEY_PATTERN = /12[.,\u00a0\u202f\u2009 ]?345[.,]67/;

/** ρ of the pair the stub makes deliberately redundant (≥ `NEAR_IDENTICAL`). */
const REDUNDANT_RHO = 0.97;
/** ρ of the pair the stub makes deliberately offsetting. */
const OFFSETTING_RHO = -0.82;
/** Everything else: positive, unremarkable, and never a finding. */
const BACKGROUND_RHO = 0.12;

/**
 * Where the planted pairs sit in payload order.
 *
 * The redundant twin is three slots from its partner so that "order by
 * similarity" has to actually move it. `MINIMUM_SELECTION` guarantees the slot
 * exists; `correlationHelpers.test.ts` proves the clustering closes the gap for
 * every size between that floor and `MATRIX_LIMIT`.
 */
const OFFSETTING_INDEX = 2;
const REDUNDANT_INDEX = 3;

/** Enough assets for both planted pairs to exist, with the twin still distant. */
const MINIMUM_SELECTION = REDUNDANT_INDEX + 1;

/**
 * How many of the requested assets the stubbed matrix covers.
 *
 * Small on purpose: it keeps the drawn matrix cheap and — since it is below
 * `PAIR_LIST_THRESHOLD` (20) — pins `data-pairs-lead` to `false` deterministically.
 */
const MATRIX_LIMIT = 8;

/** The API's ceiling on an asset-set scope (`assetSetSelection.ts`): a limit, never a default. */
const API_ASSET_CEILING = 100;

/** Written by `assetSetSelection.ts`; cleared where a test needs "first visit" to be a fact. */
const SELECTION_STORAGE_KEY = 'assetGlobal.riskSelection.v1';

const CATALOG = {
    items: [
        definition('historical_kpi', 'kpi', ['asset', 'portfolio'], ['historical'], 'historicalKpi', 20),
        definition('correlation', 'matrix', ['asset_set', 'portfolio'], ['historical', 'current_composition'], 'correlation', 2),
        definition('risk_contribution', 'contribution', ['portfolio'], ['current_composition'], 'riskContribution', 20),
        definition('stress', 'stress', ['asset', 'asset_set', 'portfolio'], ['current_composition'], 'stress', 1),
        definition('comparison', 'comparison', ['asset', 'portfolio'], ['historical', 'current_composition'], 'comparison', 20),
        definition('historical_var', 'var_cvar', ['asset', 'portfolio'], ['historical', 'current_composition'], 'historicalVar', 20),
        definition('simulation', 'simulation', ['asset', 'portfolio'], ['current_composition'], 'simulation', 30),
    ],
};

/**
 * An empty but valid scenario catalog.
 *
 * The scenario UI is gated on `scope.kind === 'asset'`, so this page never reads
 * it — but the panel still fetches it on mount, and a spec that leaves one call
 * going to the real backend is a spec that depends on which YAML files happen to
 * be on disk.
 */
const SCENARIO_CATALOG = {
    items: [],
    geography_groups: [],
    status: {
        schema_version: 1,
        loaded_at: '2026-01-31T12:00:00Z',
        built_in_count: 0,
        host_count: 0,
        warning_count: 0,
    },
    warnings: [],
};

function definition(analyticCode: string, outputKind: string, supportedScopes: string[], supportedModes: string[], translationKey: string, minObservations: number) {
    return {
        analytic_code: analyticCode,
        name_i18n_key: `risk.analytics.${translationKey}.name`,
        description_i18n_key: `risk.analytics.${translationKey}.description`,
        output_kind: outputKind,
        supported_scopes: supportedScopes,
        supported_modes: supportedModes,
        parameters_schema: {},
        min_observations: minObservations,
        algorithm_version: 'e2e-mock-v1',
    };
}

function metadata(request: RiskRequest, analytic: RiskAnalyticRequest) {
    const observations = 60;
    const calendarDays = 87;
    return {
        analyzed_range: {
            start: request.date_range.start,
            end: request.date_range.end ?? request.date_range.start,
        },
        frequency: 'daily',
        n_observations: observations,
        calendar_days: calendarDays,
        annualization_factor: (observations * 365) / calendarDays,
        coverage: 0.92,
        currency: request.target_currency,
        scope: request.scope.kind,
        scope_reference: request.scope.kind,
        method: analytic.analytic_code,
        params: analytic.parameters ?? {},
        mode: request.mode,
        ...(request.composition_policy ? {composition_policy: request.composition_policy} : {}),
        return_basis: 'price_only',
        excluded_assets: [],
        algorithm_version: 'e2e-mock-v1',
        computed_at: '2026-01-31T12:00:00Z',
    };
}

/** Clean data quality: this file is about what the panel prints, not about its banners. */
function dataQuality() {
    return {
        issues: [],
        carried_forward_price_points: 0,
        carried_forward_fx_points: 0,
        carried_forward_price_asset_ids: [],
        carried_forward_fx_pairs: [],
        data_quality_status: 'ok',
    };
}

/**
 * The asset ids the stub answers about, in the order it received them.
 *
 * The panel sends `selectedAssetIds`, and renders one chip per entry in that same
 * order, so a test can read this array off the DOM instead of guessing it — which
 * is what makes the id-keyed pair testids predictable without a single index into
 * the rendered list.
 */
function matrixAssetIds(request: RiskRequest): number[] {
    if (request.scope.kind === 'asset_set') return request.scope.asset_ids.slice(0, MATRIX_LIMIT);
    return [];
}

/**
 * A matrix with two planted findings: position 0 and {@link REDUNDANT_INDEX} are
 * the same bet, positions 0–{@link OFFSETTING_INDEX} pull against each other.
 * Every other pair is deliberately unremarkable, so the two that matter are the
 * two the lists must surface.
 *
 * The redundant twin sits at index 3 rather than 1 *on purpose*. Adjacent on
 * input it would already be clustered, `clusterOrder` would return the payload
 * order unchanged, and the ordering test would compare a value with itself —
 * which is exactly what it used to do. Three apart, the similarity ordering has
 * to move something to satisfy it. `correlationHelpers.test.ts` pins that.
 */
function correlationValue(rowIndex: number, columnIndex: number): number {
    if (rowIndex === columnIndex) return 1;
    const [low, high] = rowIndex < columnIndex ? [rowIndex, columnIndex] : [columnIndex, rowIndex];
    if (low === 0 && high === REDUNDANT_INDEX) return REDUNDANT_RHO;
    if (low === 0 && high === OFFSETTING_INDEX) return OFFSETTING_RHO;
    return BACKGROUND_RHO;
}

function correlationOutput(request: RiskRequest) {
    const assetIds = matrixAssetIds(request);
    return {
        kind: 'matrix',
        asset_ids: assetIds,
        // The backend emits the full N×N matrix, diagonal included; the frontend
        // is the thing that keeps half of it. Emitting less here would test the
        // stub's arithmetic rather than the component's.
        cells: assetIds.flatMap((rowAssetId, rowIndex) =>
            assetIds.map((columnAssetId, columnIndex) => ({
                row_asset_id: rowAssetId,
                column_asset_id: columnAssetId,
                value: correlationValue(rowIndex, columnIndex),
                observations: 60,
                coverage: rowIndex === columnIndex ? 1 : 0.88,
                status: 'ok',
            })),
        ),
    };
}

/**
 * A stress result carrying money the real backend never sends for this scope.
 *
 * `impact_amount` is populated at the top level *and* on every row, because those
 * are exactly the two places `RiskAnalysisPanel` would print it. That is the
 * point: hand the page the data that does not exist today and see whether it
 * still refuses to show it.
 */
function stressOutput(request: RiskRequest) {
    const assetIds = matrixAssetIds(request);
    const shock = -0.1;
    return {
        kind: 'stress',
        method: 'hypothetical',
        dimension: 'asset_class',
        portfolio_return: shock,
        impact_amount: MONEY_AMOUNT,
        classification_coverage: 1,
        impacts: assetIds.map((assetId) => ({
            asset_id: assetId,
            weight: 1 / assetIds.length,
            shock_return: shock,
            contribution_return: shock / assetIds.length,
            impact_amount: MONEY_AMOUNT,
            dimension: 'asset_class',
            metadata_fallback: false,
            bucket_audit: [
                {
                    exposure_bucket_id: 'ETF',
                    exposure: 1,
                    candidate_bucket_ids: ['ETF'],
                    applied_bucket_id: 'ETF',
                    bucket_shock: shock,
                    shock_contribution: shock,
                    rule: 'direct',
                },
            ],
        })),
        configured_buckets: [
            {
                bucket_id: 'ETF',
                shock,
                applied_asset_count: assetIds.length,
                asset_exposure_total: assetIds.length,
                contribution_return: shock,
            },
        ],
    };
}

function resultFor(request: RiskRequest, analytic: RiskAnalyticRequest): Record<string, unknown> {
    const base = {
        instance_id: analytic.instance_id,
        analytic_code: analytic.analytic_code,
        metadata: metadata(request, analytic),
        data_quality: dataQuality(),
        warnings: [],
    };

    if (analytic.analytic_code === 'correlation') return {...base, status: 'ok', output: correlationOutput(request)};
    if (analytic.analytic_code === 'stress') return {...base, status: 'ok', output: stressOutput(request)};

    // Anything else reaching this page is a change in what the panel requests, and
    // should say so loudly rather than render an empty frame.
    return {
        ...base,
        status: 'failed',
        output: null,
        error: {code: 'analytic_not_found', message: `Unexpected E2E analytic ${analytic.analytic_code}`},
    };
}

/** Stub the three risk endpoints and hand back the requests the page actually made. */
async function installRiskMocks(page: Page): Promise<RiskRequest[]> {
    const requests: RiskRequest[] = [];

    await page.route('**/api/v1/risk/catalog', async (route) => {
        await route.fulfill({status: 200, contentType: 'application/json', body: JSON.stringify(CATALOG)});
    });

    await page.route('**/api/v1/risk/scenario-catalog', async (route) => {
        await route.fulfill({status: 200, contentType: 'application/json', body: JSON.stringify(SCENARIO_CATALOG)});
    });

    await page.route('**/api/v1/risk/query', async (route) => {
        const request = route.request().postDataJSON() as RiskRequest;
        requests.push(request);
        await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({items: request.analytics.map((analytic) => resultFor(request, analytic))}),
        });
    });

    return requests;
}

/**
 * True when the two ids sit side by side in `order`.
 *
 * Deliberately a *relation* between ids, never a pair of indices: the whole point
 * of the ordering toggle is that positions move, so any assertion phrased in
 * positions would be asserting the thing it is supposed to measure.
 */
function adjacentInOrder(order: readonly number[], pair: readonly number[]): boolean {
    const positions = pair.map((id) => order.indexOf(id));
    if (positions.some((position) => position < 0)) return false;
    return Math.abs(positions[0] - positions[1]) === 1;
}

/** The selected chips, as asset ids, in the order the panel renders them. */
async function chipIds(page: Page): Promise<number[]> {
    const ids = await page.getByTestId(/^risk-selected-asset-\d+$/).evaluateAll((nodes) => nodes.map((node) => Number(node.getAttribute('data-testid')?.replace('risk-selected-asset-', ''))));
    return ids.filter((id) => Number.isInteger(id));
}

/** The counter, which publishes its two numbers as attributes beside its sentence. */
const selectionCounter = (page: Page) => page.getByTestId('risk-selected-count');

/**
 * The two numbers behind `risk-selected-count`, read from `data-selected` and
 * `data-total` — never from the sentence next to them.
 *
 * The label is translated (EN/IT/FR/ES) and locale-formats its integers, so
 * neither its words nor its digit grouping are a contract a test may hold on to.
 * The attributes are.
 *
 * `getAttribute` does not retry, so a caller either fronts this read with a
 * barrier that does, or asserts the number through `toHaveAttribute` instead of
 * reading it. Where a chip count is available it is cross-checked against these
 * numbers: two independent sources agreeing is the point, since the counter and
 * the rendered chips can still drift apart — and that drift deserves a red.
 */
async function selectionCounts(page: Page): Promise<{selected: number; total: number}> {
    const counter = selectionCounter(page);
    const [selected, total] = await Promise.all([counter.getAttribute('data-selected'), counter.getAttribute('data-total')]);
    const numbers = {selected: Number(selected), total: Number(total)};
    if (!Number.isInteger(numbers.selected) || !Number.isInteger(numbers.total)) {
        throw new Error(`risk-selected-count must publish integer data-selected/data-total, read selected="${selected}" total="${total}".`);
    }
    return numbers;
}

async function openAssetGlobalRisk(page: Page): Promise<void> {
    await navigateTo(page, '/assets?tab=correlation');
    await expect(page.getByTestId('asset-global-risk-panel')).toBeVisible({timeout: 20_000});
    await expect(page.getByTestId('risk-asset-set-controls')).toBeVisible({timeout: 15_000});
    // The seed lands with the asset list, not with the panel frame: `count()` does
    // not retry, so sampling it once here would read whatever had rendered by that
    // instant.
    await expect
        .poll(() => page.getByTestId(/^risk-selected-asset-\d+$/).count(), {
            timeout: 15_000,
            message: 'the panel opened on an empty selection — it needs at least one seeded asset to analyse',
        })
        .toBeGreaterThan(0);
}

/**
 * Every section of the analysis is gated on the capability catalog, so an absent
 * section means "unsupported" *or* "not loaded yet". The panel publishes which
 * one; wait for the gate rather than for the gated.
 */
async function waitForRiskCatalog(page: Page): Promise<void> {
    await expect(page.getByTestId('asset-global-risk-panel').getByTestId('risk-analysis-panel')).toHaveAttribute('data-catalog', 'ready', {timeout: 20_000});
}

/**
 * Grow the selection until the matrix has enough assets to carry both findings.
 *
 * Three is the minimum for a *correlated* pair and an *offsetting* one to exist
 * at the same time. How many the page opens with is seed data, so the precondition
 * is checked and satisfied rather than assumed — and never silently skipped.
 *
 * Which asset gets added is irrelevant: the id is read off whichever option was
 * picked, so nothing downstream depends on the choice.
 */
async function ensureSelectionAtLeast(page: Page, minimum: number): Promise<void> {
    const chips = page.getByTestId(/^risk-selected-asset-\d+$/);
    const picker = page.getByTestId('risk-asset-add-select');
    const options = picker.locator('[data-testid^="search-select-option-"]');

    while ((await chips.count()) < minimum) {
        await picker.locator('[role="combobox"]').click();
        const option = options.first();
        await expect(option).toBeVisible({timeout: 10_000});
        const testId = await option.getAttribute('data-testid');
        const assetId = Number(testId?.replace('search-select-option-', ''));
        expect(Number.isInteger(assetId), `the asset picker must key its options by asset id, read "${testId}"`).toBe(true);

        await option.click();
        await expect(page.getByTestId(`risk-selected-asset-${assetId}`)).toBeVisible();
        // The option list is a shared `search-select-option-*` namespace: the next
        // iteration must not be able to read this one's leftovers.
        await expect(options).toHaveCount(0);
    }
}

/**
 * A type filter that leaves a workable candidate set behind.
 *
 * Which asset types the seed contains is not this test's business, so the filter
 * is chosen by *property* — the smallest candidate set with at least two members
 * — instead of by position in the chip row. Two, because a mass action over a
 * single row proves nothing about "all"; smallest, because every selected asset
 * ends up drawn in the matrix.
 *
 * Leaves every filter switched off, exactly as it found them.
 */
async function chooseTypeFilter(page: Page): Promise<{testId: string; candidates: number; partitionSum: number; options: number}> {
    const chips = page.getByTestId(/^risk-filter-type-.+$/);
    await expect(chips.first()).toBeVisible({timeout: 15_000});
    const testIds = (await chips.evaluateAll((nodes) => nodes.map((node) => node.getAttribute('data-testid') ?? ''))).filter(Boolean);

    let best: {testId: string; candidates: number} | null = null;
    let partitionSum = 0;
    for (const testId of testIds) {
        const chip = page.getByTestId(testId);
        await chip.click();
        // `aria-pressed` and `data-total` are both driven by `filters`, so they land
        // in the same flush: once the chip reports pressed, the counter reports the
        // filtered candidate set and the one-shot read below cannot be early.
        await expect(chip).toHaveAttribute('aria-pressed', 'true');
        const {total} = await selectionCounts(page);
        await chip.click();
        await expect(chip).toHaveAttribute('aria-pressed', 'false');
        partitionSum += total;
        if (total >= 2 && (best === null || total < best.candidates)) best = {testId, candidates: total};
    }

    if (!best) throw new Error(`No asset-type filter leaves at least two candidates (tried: ${testIds.join(', ')}).`);
    return {...best, partitionSum, options: testIds.length};
}

// Earned parallel: every block below stubs its own API, owns its selection (which
// lives in its own browser context) and writes nothing to the shared database, so
// it can run beside a stranger instead of queueing behind one.
test.describe.configure({mode: 'parallel'});

test.describe('Asset Global risk laboratory', () => {
    test.beforeEach(async ({page}) => {
        await login(page, TEST_USER);
    });

    test('prints no money, even when the API hands it some', async ({page}) => {
        const requests = await installRiskMocks(page);
        await openAssetGlobalRisk(page);
        await waitForRiskCatalog(page);

        const panel = page.getByTestId('asset-global-risk-panel');

        // The scenario section is gated on the catalog, which is already `ready`.
        await expect(page.getByTestId('risk-stress-controls')).toBeVisible({timeout: 15_000});
        const runScenario = page.getByTestId('risk-stress-run');
        await expect(runScenario).toBeEnabled();
        await runScenario.click();

        // Presence barriers first. "No € on the page" is also true of a page that
        // rendered nothing at all, so the money-bearing payload has to be proved to
        // have *reached the renderer* before its absence means anything.
        await expect(page.getByTestId('risk-stress-section')).toBeVisible({timeout: 20_000});
        await expect(page.getByTestId('risk-stress-impacts')).toBeVisible({timeout: 20_000});
        await expect(page.getByTestId('risk-stress-impacts').locator('tbody tr').first()).toBeVisible();
        await expect
            .poll(() => requests.some((request) => request.scope.kind === 'asset_set' && request.analytics.some((analytic) => analytic.analytic_code === 'stress')), {
                timeout: 15_000,
                message: 'the scenario must have run against an asset_set scope — that is the scope the no-money rule is about',
            })
            .toBe(true);

        const rendered = await panel.innerText();

        // The section is populated with the half it is allowed to show: a shock is
        // a percentage, and percentages are what an unweighted set can honestly say.
        expect(rendered, 'the scenario section rendered without a single percentage — the barriers above are lying').toContain('%');

        // THE RULE. With weights → euros → "me". Without weights → percentages →
        // "these". An asset set carries no weights, so any euro figure here would be
        // an arithmetic claim about a portfolio the user never described.
        //
        // READ THIS BEFORE "FIXING" THE ASSERTION BELOW:
        //
        // What is forbidden is an AMOUNT standing for a position, an exposure or a
        // portfolio impact. The currency *code* is not forbidden — "EUR" appears as
        // a target-currency label, and naming a currency is not quoting a sum — so
        // do NOT turn this into a grep for the string 'EUR'. That version would fail
        // on a legitimate label and still miss `$12,345.67`.
        //
        // The test is deliberately hostile: the stub above sends monetary fields the
        // real backend never sends for this scope (`service.py` builds
        // `asset_values={}` and `scope_value=None` for an `AssetSetRiskScope`). It
        // therefore fails the day someone wires those amounts through to the view —
        // which is its entire purpose.
        expect(rendered, `the panel printed the stubbed monetary magnitude. Panel text was:\n${rendered}`).not.toMatch(MONEY_PATTERN);
        expect(rendered, 'the panel printed a euro glyph — no amount of money belongs on an unweighted asset set').not.toContain('€');
        // `.currency-symbol` is what `formatCurrencyAmountHtml` emits around a sum.
        await expect(panel.locator('.currency-symbol')).toHaveCount(0);
    });

    test('opens on a small selection, never on the API ceiling', async ({page}) => {
        const requests = await installRiskMocks(page);

        // D19 is a statement about the *first* visit, so the absence of a stored
        // preference is made a fact of this test rather than an assumption about
        // how the fixture isolates contexts.
        await page.addInitScript(
            ([key]) => {
                try {
                    window.localStorage.removeItem(key);
                } catch {
                    /* storage disabled — there is nothing to clear */
                }
            },
            [SELECTION_STORAGE_KEY],
        );

        await openAssetGlobalRisk(page);

        // THE oracle of this test. The opening *size* cannot distinguish D19 from
        // what came before it: on a seed of ~50 assets the old "first hundred from
        // the array" behaviour produced a small set too, so a test that only counted
        // chips would have passed under the very regression it exists to catch.
        // The branch is what carries the meaning — `mine` can only be reached by
        // consulting ownership, which the old code never did.
        //
        // A red here reads as: `fallback` → the seeded user holds nothing, so the
        // fixture, not the panel, is what changed; `persisted` → this context began
        // with a stored preference and the init script above did not clear it;
        // absent → the seed effect never ran.
        const controls = page.getByTestId('risk-asset-set-controls');
        await expect(controls, 'a first visit by a user who holds assets must open on the assets they hold (D19)').toHaveAttribute('data-selection-source', 'mine', {timeout: 15_000});

        const opening = await chipIds(page);
        const {selected, total} = await selectionCounts(page);

        // The corollaries. The exact membership of the opening set is data this test
        // does not control, and it is pinned where it is cheap and exact — the unit
        // tests of `resolveInitialSelection`. What is asserted here is the wiring:
        // the branch reached the screen, and the ceiling is not what the user gets.
        expect(opening.length, 'the page must open on a non-empty selection').toBeGreaterThan(0);
        expect(opening.length, 'the page must not open on the API ceiling of 100 assets (D19)').toBeLessThan(API_ASSET_CEILING);
        expect(selected, 'the counter and the chips must describe the same selection').toBe(opening.length);
        expect(selected).toBeLessThanOrEqual(total);

        // What the user sees is what gets analysed: the chips are the scope.
        await expect
            .poll(
                () => {
                    const wanted = [...opening].sort((left, right) => left - right).join(',');
                    return requests.some((request) => request.scope.kind === 'asset_set' && [...request.scope.asset_ids].sort((left, right) => left - right).join(',') === wanted);
                },
                {timeout: 15_000, message: 'the analysed asset set must be exactly the set the chips show'},
            )
            .toBe(true);
    });

    test('bulk actions round-trip against the filtered candidates', async ({page}) => {
        await installRiskMocks(page);
        await openAssetGlobalRisk(page);

        const chips = page.getByTestId(/^risk-selected-asset-\d+$/);
        const {testId: typeFilter, candidates} = await chooseTypeFilter(page);
        expect(candidates, 'the round-trip needs a candidate set below the API ceiling, since `all` truncates at it').toBeLessThan(API_ASSET_CEILING);

        // Start from a state this test owns. Unfiltered, "deselect all" is the one
        // mass action that is total by definition, so it is a reachable zero rather
        // than an assumption about what the page opened with.
        await page.getByTestId('risk-bulk-none').click();
        await expect(chips).toHaveCount(0);
        await expect(page.getByTestId('risk-asset-set-empty')).toBeVisible();
        await expect(selectionCounter(page)).toHaveAttribute('data-selected', '0');

        const chip = page.getByTestId(typeFilter);
        await chip.click();
        await expect(chip).toHaveAttribute('aria-pressed', 'true');
        await expect(selectionCounter(page)).toHaveAttribute('data-total', String(candidates));

        // `all` reaches exactly what the filter shows, never past it: a button that
        // silently crossed the active filter would undo it without saying so.
        await page.getByTestId('risk-bulk-all').click();
        await expect(chips).toHaveCount(candidates);
        await expect(selectionCounter(page)).toHaveAttribute('data-selected', String(candidates));

        // `invert` flips those same candidates. Everything visible is selected, so
        // inverting empties the selection…
        await page.getByTestId('risk-bulk-invert').click();
        await expect(chips).toHaveCount(0);
        await expect(selectionCounter(page)).toHaveAttribute('data-selected', '0');

        // …and inverting again brings exactly them back.
        await page.getByTestId('risk-bulk-invert').click();
        await expect(chips).toHaveCount(candidates);
        await expect(selectionCounter(page)).toHaveAttribute('data-selected', String(candidates));

        // `none` under a filter mirrors `all`: it removes what is visible, which here
        // is all of it.
        await page.getByTestId('risk-bulk-none').click();
        await expect(chips).toHaveCount(0);

        // Leave the filter row as it was found. (The selection itself is per-context
        // `localStorage`; no database row was touched by any of the above.)
        await page.getByTestId('risk-filters-clear').click();
        await expect(page.getByTestId('risk-filters-clear')).toHaveCount(0);
    });

    test('a filter keeps its own option clickable and clears back', async ({page}) => {
        await installRiskMocks(page);
        await openAssetGlobalRisk(page);

        const typeChips = page.getByTestId(/^risk-filter-type-.+$/);
        const currencyChips = page.getByTestId(/^risk-filter-currency-.+$/);
        await expect(typeChips.first()).toBeVisible({timeout: 15_000});
        await expect(currencyChips.first()).toBeVisible({timeout: 15_000});
        const typeOptions = await typeChips.count();
        const currencyOptions = await currencyChips.count();

        const unfiltered = (await selectionCounts(page)).total;
        const {testId: typeFilter, candidates, partitionSum, options} = await chooseTypeFilter(page);
        const chip = page.getByTestId(typeFilter);

        // An inequality is the wrong oracle here. `candidates` is read back from the
        // same counter the assertion then checks, so a filter wired to nothing gives
        // `candidates === unfiltered`, satisfies "narrowed or equal", and is green.
        //
        // An asset has exactly one type, and the chips are derived from the whole
        // candidate set, so the type filters *partition* it: applied one at a time
        // their totals must sum back to the unfiltered total. A dead filter returns
        // the full set every time and sums to `options × unfiltered` instead.
        expect(partitionSum, 'type filters must partition the candidates, not each return everything').toBe(unfiltered);
        expect(options, 'with a single type present the partition check cannot discriminate').toBeGreaterThan(1);
        expect(candidates, 'the chosen filter must be a strict subset for the checks below to mean anything').toBeLessThan(unfiltered);

        await chip.click();
        await expect(chip).toHaveAttribute('aria-pressed', 'true');

        // The guard against `problems/datatable-filter-options-disappear`: deriving
        // the options from the *filtered* result is how the option that applies a
        // filter vanishes the moment it is applied, leaving a filter with no way
        // back. Every option must survive, the pressed one above all.
        await expect(typeChips).toHaveCount(typeOptions);
        await expect(currencyChips).toHaveCount(currencyOptions);
        await expect(chip).toBeVisible();
        await expect(chip).toBeEnabled();

        // Exact, and retried: reading the number one flush early would return the
        // *unfiltered* total, which satisfies a "narrowed" inequality and turns a
        // dead filter into a green.
        await expect(selectionCounter(page)).toHaveAttribute('data-total', String(candidates));

        // Switched off by the very same control…
        await chip.click();
        await expect(chip).toHaveAttribute('aria-pressed', 'false');
        await expect(selectionCounter(page)).toHaveAttribute('data-total', String(unfiltered));

        // …and by "clear filters", which only exists while a filter is on.
        await expect(page.getByTestId('risk-filters-clear')).toHaveCount(0);
        await chip.click();
        await expect(chip).toHaveAttribute('aria-pressed', 'true');
        const clear = page.getByTestId('risk-filters-clear');
        await expect(clear).toBeVisible();
        await clear.click();
        await expect(clear).toHaveCount(0);
        await expect(chip).toHaveAttribute('aria-pressed', 'false');
        await expect(selectionCounter(page)).toHaveAttribute('data-total', String(unfiltered));
    });

    test('the matrix names the redundant pair and the offsetting one', async ({page}) => {
        await installRiskMocks(page);
        await openAssetGlobalRisk(page);
        await ensureSelectionAtLeast(page, MINIMUM_SELECTION);

        // The stub plants its findings at *positions in the payload it receives*.
        // That payload is NOT in chip order: `riskRequest.ts` canonicalises the
        // scope with `asset_ids: sortedNumbers(...)` so a cache key is stable
        // regardless of selection order, while the chips render in name order.
        // Sorting here is therefore reproducing the request's own normalisation,
        // not sidestepping a flake — drop it and the ids point at other assets.
        //
        // Note what is NOT used: an index into the rendered list. The matrix reorders
        // itself by similarity, so a positional selector here would be testing the
        // clustering rather than the finding.
        const matrix = [...(await chipIds(page))].sort((left, right) => left - right).slice(0, MATRIX_LIMIT);
        expect(matrix.length, 'both planted pairs need the twin slot to exist').toBeGreaterThanOrEqual(MINIMUM_SELECTION);
        const redundantPair = `risk-correlation-pair-${matrix[REDUNDANT_INDEX]}-${matrix[0]}`;
        const offsettingPair = `risk-correlation-pair-${matrix[OFFSETTING_INDEX]}-${matrix[0]}`;

        await waitForRiskCatalog(page);
        await expect(page.getByTestId('risk-correlation-pairs')).toBeVisible({timeout: 20_000});

        // "What am I holding twice?" — the pair at ρ = 0.97, flagged as near-identical.
        const correlated = page.getByTestId('risk-correlation-pairs-correlated');
        await expect(correlated.getByTestId(redundantPair)).toBeVisible({timeout: 20_000});
        await expect(correlated.getByTestId(`risk-correlation-pair-near-identical-${matrix[REDUNDANT_INDEX]}-${matrix[0]}`)).toBeVisible();
        await expect(page.getByTestId('risk-correlation-pairs-correlated-empty')).toHaveCount(0);

        // "Is anything actually pulling the other way?" — the pair at ρ = -0.82.
        const offsetting = page.getByTestId('risk-correlation-pairs-offsetting');
        await expect(offsetting.getByTestId(offsettingPair)).toBeVisible({timeout: 20_000});
        await expect(page.getByTestId('risk-correlation-pairs-offsetting-empty')).toHaveCount(0);

        // A set this small is still readable as a picture, so the matrix keeps the lead.
        await expect(page.getByTestId('risk-correlation-layout')).toHaveAttribute('data-pairs-lead', 'false');
        await expectChartCanvas(page, 'risk-correlation-heatmap', 20_000);
    });

    test('the ordering toggle reorders the matrix and loses no finding', async ({page}) => {
        await installRiskMocks(page);
        await openAssetGlobalRisk(page);
        await ensureSelectionAtLeast(page, MINIMUM_SELECTION);

        // Sorted for the same reason as in the previous test: the request
        // canonicalises `asset_ids` ascending, so payload position is id order.
        const matrix = [...(await chipIds(page))].sort((left, right) => left - right).slice(0, MATRIX_LIMIT);
        expect(matrix.length, 'the twin has to be distant, so its slot must exist').toBeGreaterThanOrEqual(MINIMUM_SELECTION);
        const findings = [`risk-correlation-pair-${matrix[REDUNDANT_INDEX]}-${matrix[0]}`, `risk-correlation-pair-${matrix[OFFSETTING_INDEX]}-${matrix[0]}`];
        const twins = [matrix[0], matrix[REDUNDANT_INDEX]];

        const heatmap = page.getByTestId('risk-correlation-heatmap');
        const similarity = page.getByTestId('risk-correlation-ordering-similarity');
        const original = page.getByTestId('risk-correlation-ordering-original');

        /** The order the chart is actually built from, not the order of the chips. */
        const drawnOrder = async (): Promise<number[]> => {
            const raw = await heatmap.getAttribute('data-asset-order');
            expect(raw, 'the heatmap must publish the order it draws').toBeTruthy();
            return (raw ?? '').split(',').map(Number);
        };

        await waitForRiskCatalog(page);
        await expect(similarity).toBeVisible({timeout: 20_000});
        await expect(similarity).toHaveAttribute('aria-pressed', 'true');
        for (const testId of findings) await expect(page.getByTestId(testId)).toBeVisible({timeout: 20_000});
        await expectChartCanvas(page, 'risk-correlation-heatmap', 20_000);

        // What "order by similarity" promises is not "something changed": it is that
        // assets which move together end up next to each other. The stub plants a
        // twin three slots away from its partner precisely so that the promise has
        // observable consequences — asserting the button's pressed state would pass
        // against a toggle wired to nothing.
        const clustered = await drawnOrder();
        expect(clustered, 'similarity must not simply echo the payload order').not.toEqual(matrix);
        expect(adjacentInOrder(clustered, twins), 'similarity must put the twin beside its partner').toBe(true);

        await original.click();
        await expect(original).toHaveAttribute('aria-pressed', 'true');
        await expect(similarity).toHaveAttribute('aria-pressed', 'false');
        const payload = await drawnOrder();
        expect(payload, 'the original ordering is the payload order, ascending by id').toEqual(matrix);
        expect(adjacentInOrder(payload, twins), 'the twins are deliberately apart on input').toBe(false);
        // Reordering is a view choice: it may move rows, never invent or drop one.
        expect([...payload].sort((left, right) => left - right)).toEqual([...clustered].sort((left, right) => left - right));
        for (const testId of findings) await expect(page.getByTestId(testId)).toBeVisible();
        await expectChartCanvas(page, 'risk-correlation-heatmap', 20_000);

        await similarity.click();
        await expect(similarity).toHaveAttribute('aria-pressed', 'true');
        await expect(original).toHaveAttribute('aria-pressed', 'false');
        expect(await drawnOrder(), 'going back must restore the clustered order, not a third one').toEqual(clustered);
        for (const testId of findings) await expect(page.getByTestId(testId)).toBeVisible();
        await expectChartCanvas(page, 'risk-correlation-heatmap', 20_000);
    });
});
