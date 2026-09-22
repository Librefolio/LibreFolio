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
import {optionsClosed} from '../fixtures/probe';
import {TEST_USER} from '../fixtures/test-users';
import {schemas} from '../../src/lib/api/generated';

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
 * (`risk/service.py`), so the replay plugin returns `impact_amount=None` on every
 * row (`stress.py:542`) and leaves `portfolio_return` null (`:480-494`), which
 * makes the top-level amount unreachable too (`:564`). So loading the page and
 * finding no `€` would prove nothing — it would stay green with the rule
 * deleted, because the data simply is not there.
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

/**
 * The composition return the stubbed replay claims.
 *
 * Chosen so no rendered percentage can collide with {@link MONEY_PATTERN}: the
 * tornado and the total print `(|value| * 100).toFixed(2)`, so this one reads
 * `−12.34%` and the per-asset spread below stays in the same two-digit range.
 */
const REPLAY_RETURN = -0.1234;

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

/** The one scope this page ever asks about, spelled once. */
const ASSET_SET_SCOPE = 'asset_set';

/**
 * The version string every stubbed answer wears, and no real one does.
 *
 * A sentinel rather than a plausible value: the catalogue-fidelity guard asserts
 * the live response does **not** carry it, which is how "this test talks to the
 * backend" stops being a convention about where `installRiskMocks` is called and
 * becomes something the test can fail on.
 */
const MOCK_ALGORITHM_VERSION = 'e2e-mock-v1';

/**
 * ═══════════════════════════════════════════════════════════════════════════
 * 🧪 EVERY FIGURE BELOW IS **INVENTED, NOT MEASURED**.
 * ═══════════════════════════════════════════════════════════════════════════
 *
 * None of these numbers was read off a running backend, a populated lane, or a
 * probe. They were chosen by hand so that:
 *
 *  - every one of them satisfies the payload contract in `schemas/risk.py` —
 *    the sign constraints (`ge=0` on the VaR pair, `le=0` on the drawdown pair),
 *    the tail orderings (`CVaR ≥ VaR`, `CDaR ≤ DaR`, `CDaR ≥ max_drawdown`) and
 *    the drawdown episode contract (`recovered` carries a recovery date, `open`
 *    must not) — because a stub that violates the contract is testing a state
 *    the backend cannot produce;
 *  - they differ per asset, so a transposition bug that repeated one row would
 *    be visible rather than plausible;
 *  - none of them can be mistaken for {@link MONEY_AMOUNT}: everything here is
 *    rendered as `X.Y%` or as a small ratio.
 *
 * ⚠️ DO NOT LABEL THEM AS MEASURED, and do not "restore them from the backend"
 * without saying so. This project has a recorded incident where a reconstructed
 * fixture was signed *"measured on the running backend"* and the arithmetic
 * check passed anyway — a check interrogates the number, never its provenance.
 * The provenance is this comment.
 */
const INVENTED = {
    /** VaR 95% over one day, as a positive loss fraction, per asset index. */
    badDayVar: (index: number) => 0.021 + index * 0.004,
    /** CVaR is the mean *beyond* the quantile, so it is wider — here by a flat 40%. */
    tailWidening: 1.4,
    /** A month is drawn wider than a day, but never as `day × √21`: that would be a model. */
    monthFactor: 4,
    /** Deepest peak-to-trough fall, negative as the contract requires. */
    maximumDrawdown: (index: number) => -(0.18 + index * 0.03),
    /** Annualised volatility. */
    volatility: (index: number) => 0.12 + index * 0.02,
    /** Mean-variance expected annual return; crosses zero so both signs get drawn. */
    expectedReturn: (index: number) => 0.045 - index * 0.015,
    sharpe: (index: number) => 0.35 + index * 0.1,
    beta: (index: number) => 0.8 + index * 0.15,
    /** Bounded to [-1, 1] by the contract; this ramp stays well inside it. */
    correlation: (index: number) => 0.55 + index * 0.04,
    trackingError: (index: number) => 0.04 + index * 0.01,
    /** Episode dates. Ordered peak ≤ trough ≤ recovery, which the validator checks. */
    peakDate: '2025-03-11',
    troughDate: '2025-07-08',
    recoveryDate: '2025-11-19',
    currentPeakDate: '2026-01-05',
    /** The benchmark's own coordinates, published by `asset_set_comparison`. */
    benchmarkVolatility: 0.104,
    benchmarkExpectedReturn: 0.058,
};

/**
 * How many distinct rows the ramps above produce before they repeat.
 *
 * 🔴 NOT a tidiness knob — a correctness one. Every function in {@link INVENTED}
 * is a straight line in the asset index, and an asset set may legitimately hold
 * up to {@link API_ASSET_CEILING} assets. Left unbounded, row 100 would claim a
 * −318% maximum drawdown, and `remaining_to_peak_ratio = −d / (1 + d)` would go
 * *negative* past d = −1 and be rejected by its own `ge=0` constraint. Wrapping
 * keeps every figure inside the band a real instrument could occupy, whatever
 * the page's selection happens to be, while neighbouring rows still differ —
 * which is all the transposition assertions need.
 */
const INVENTED_VARIANTS = 8;

/** Which of the {@link INVENTED_VARIANTS} ramps this row sits on. */
function variant(index: number): number {
    return index % INVENTED_VARIANTS;
}

/** Observations the stub reports on an ordinary window: above every `min_observations`. */
const AMPLE_OBSERVATIONS = 60;

/**
 * Observations the stub reports on a window too short for four of the five.
 *
 * Between `asset_set_drawdown`'s 2 and the other four's 20, so the split is the
 * backend's own rule rather than a number this file picked to force an outcome.
 */
const SHORT_OBSERVATIONS = 5;

/** What `service.py:234` answers with when a window is below `min_observations`. */
const INSUFFICIENT_HISTORY = 'insufficient_history';

/**
 * The warning `_build_context` appends when a requested asset could not be prepared.
 *
 * Copied from `service.py:604-610` verbatim, code and sentence both, because
 * `resultReasons` renders the backend's own string and deduplicates *by that
 * string*: a paraphrase here would still produce one entry and would still look
 * right, while testing a sentence the product never emits.
 */
const EXCLUDED_WARNING_CODE = 'assets_excluded';
const EXCLUDED_WARNING_MESSAGE = 'One or more scope assets were excluded from risk calculations.';

/**
 * The capability catalogue this file pretends the backend publishes.
 *
 * ⚠️ IT IS A HAND-MAINTAINED COPY, AND THAT IS ITS ONE DANGEROUS PROPERTY.
 * `hasRiskCapability` reads `supported_scopes` and `supported_modes` to decide
 * what the page may ask for, so a code missing here — or a mode narrower here
 * than in the real registry — does not fail: it makes the panel *request less*,
 * and every assertion about the section that would have rendered it goes green
 * against an empty frame. Three drifts of exactly that shape have already been
 * paid for, which is why `the mocked catalogue matches the backend's` below
 * compares this table against the live `/api/v1/risk/catalog` instead of trusting
 * whoever edited it last.
 *
 * `historical_kpi` carried one of those drifts until that test was written: it
 * was declared `['historical']` while `historical_kpi.py:119` advertises
 * `(HISTORICAL, CURRENT_COMPOSITION)`. Corrected here rather than tolerated in
 * the guard — a guard with an exemption list is a guard that stops guarding. The
 * correction is inert on this page (the code is `ASSET`/`PORTFOLIO`-scoped, so an
 * asset set never asks for it), which is precisely why it survived unnoticed.
 */
const CATALOG = {
    items: [
        definition('historical_kpi', 'kpi', ['asset', 'portfolio'], ['historical', 'current_composition'], 'historicalKpi', 20),
        definition('correlation', 'matrix', ['asset_set', 'portfolio'], ['historical', 'current_composition'], 'correlation', 2),
        definition('risk_contribution', 'contribution', ['portfolio'], ['current_composition'], 'riskContribution', 20),
        definition('stress', 'stress', ['asset', 'asset_set', 'portfolio'], ['current_composition'], 'stress', 1),
        definition('comparison', 'comparison', ['asset', 'portfolio'], ['historical', 'current_composition'], 'comparison', 20),
        definition('historical_var', 'var_cvar', ['asset', 'portfolio'], ['historical', 'current_composition'], 'historicalVar', 20),
        definition('simulation', 'simulation', ['asset', 'portfolio'], ['current_composition'], 'simulation', 30),
        // The weightless per-asset family: `ASSET_SET` × `HISTORICAL` only, which
        // is what makes `buildBaseAnalytics`'s block inert on every other scope.
        // `asset_set_drawdown` needs 2 observations where the other four need 20 —
        // not a typo, and the reason a short window returns one `ok` beside four
        // `unavailable` rather than five of anything.
        definition('asset_set_kpi', 'kpi_set', [ASSET_SET_SCOPE], ['historical'], 'assetSetKpi', 20),
        definition('asset_set_var', 'var_cvar_set', [ASSET_SET_SCOPE], ['historical'], 'assetSetVar', 20),
        definition('asset_set_drawdown', 'drawdown_set', [ASSET_SET_SCOPE], ['historical'], 'assetSetDrawdown', 2),
        definition('asset_set_risk_return', 'risk_return_set', [ASSET_SET_SCOPE], ['historical'], 'assetSetRiskReturn', 20),
        definition('asset_set_comparison', 'comparison_set', [ASSET_SET_SCOPE], ['historical'], 'assetSetComparison', 20),
        // Declared for fidelity, not because this page uses it. The backend
        // advertises `portfolio_optimization` for the asset-set scope, and the
        // catalogue-fidelity guard compares what the stub declares against what
        // the registry declares — omitting a real capability because no test
        // needs it is precisely the drift that guard exists to catch. Nothing
        // requests it: `buildBaseAnalytics` never adds the code.
        definition('portfolio_optimization', 'optimization', [ASSET_SET_SCOPE, 'portfolio'], ['historical'], 'portfolioOptimization', 30),
    ],
};

/** The five codes the laboratory's comparison levels put on the wire together. */
const ASSET_SET_LEVEL_CODES = ['asset_set_kpi', 'asset_set_var', 'asset_set_drawdown', 'asset_set_risk_return', 'asset_set_comparison'] as const;

/** The four that ride on every load; `asset_set_comparison` joins only with a benchmark. */
const ASSET_SET_UNCONDITIONAL_CODES = ASSET_SET_LEVEL_CODES.filter((code) => code !== 'asset_set_comparison');

/**
 * An empty but valid scenario catalog.
 *
 * Empty, not absent. The replay reads it — `replayOptions` turns it into the
 * preset list — and an empty list simply means "no presets", which leaves the
 * explicit date range the section was born with. What is not acceptable is a
 * call going to the real backend: a spec that lets one through depends on which
 * YAML files happen to be on disk.
 *
 * It is fetched on the rung's **first open** (`RiskLevelSection`'s `onfirstopen`
 * → `controller.loadScenarioCatalog()`), not on mount, so the route must be in
 * place before the toggle is clicked rather than before the page is opened.
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
        algorithm_version: MOCK_ALGORITHM_VERSION,
    };
}

/**
 * True when this request is the *historical replay*, not the hypothetical shock.
 *
 * Both ride the same analytic code. `L4Replay:95` asks for `stress` in
 * `current_composition` mode and distinguishes itself in the parameters
 * (`buildHistoricalReplayParameters` → `method: 'historical_replay'`), so the
 * code alone cannot tell the two apart and neither may this stub.
 */
function isHistoricalReplay(analytic: RiskAnalyticRequest): boolean {
    return analytic.analytic_code === 'stress' && analytic.parameters?.method === 'historical_replay';
}

/**
 * How this test wants the backend to behave, where "ordinary" is not the subject.
 *
 * Both knobs reproduce a state the **real** backend reaches on its own; neither
 * invents one. That distinction is the whole reason they are options rather than
 * separate hand-written payloads: a stub that can only produce the happy path
 * makes the unhappy paths unreachable, and a stub that produces an impossible
 * one tests a page against a world that does not exist.
 */
interface RiskStubOptions {
    /**
     * Answer for one fewer asset than the scope asked about.
     *
     * The backend does this whenever a requested asset has no usable series: it
     * is dropped from the prepared set (`service.py:590-598`), every analytic in
     * the request then answers about the survivors, the result's status becomes
     * `partial` rather than `ok` (`service.py:783`) and one `assets_excluded`
     * warning rides on all of them (`:604-610`). Reproduced in full here —
     * including on `correlation`, because the exclusion is a property of the
     * *prepared series set* and not of any one analytic, so hiding it from the
     * matrix would be a state the backend cannot produce.
     */
    dropLastAsset?: boolean;
    /**
     * A window shorter than four of the five analytics can measure.
     *
     * `asset_set_drawdown` declares `min_observations = 2` where the other four
     * declare 20, so the gate at `service.py:230-243` genuinely returns one `ok`
     * beside four `unavailable` — same request, same calendar, same window.
     */
    shortWindow?: boolean;
}

/** True when this analytic is one of the five the comparison levels read. */
function isAssetSetLevel(analytic: RiskAnalyticRequest): boolean {
    return (ASSET_SET_LEVEL_CODES as readonly string[]).includes(analytic.analytic_code);
}

/**
 * True when this analytic is gated out by a window of {@link SHORT_OBSERVATIONS}.
 *
 * Expressed as the backend expresses it — a comparison against the analytic's own
 * `min_observations`, read from the same {@link CATALOG} the page was gated on —
 * rather than as a hard-coded list of four codes. A list would still be "right"
 * today and would stop describing anything the moment a threshold moved.
 */
function belowMinimumObservations(analytic: RiskAnalyticRequest, observations: number): boolean {
    const definition = CATALOG.items.find((item) => item.analytic_code === analytic.analytic_code);
    return definition !== undefined && observations < definition.min_observations;
}

/** How many observations the stub claims this request was measured over. */
function observationCount(options: RiskStubOptions): number {
    return options.shortWindow ? SHORT_OBSERVATIONS : AMPLE_OBSERVATIONS;
}

/**
 * The scope ids the stub could prepare, and the ones it had to drop.
 *
 * The dropped id is taken from the **end** of the request's own array, which the
 * client canonicalises ascending (`riskRequest.ts:83`, `asset_ids:
 * sortedNumbers(...)`). A caller therefore recovers the omitted id by reading
 * the captured request rather than by assuming which asset the page happened to
 * seed — and the assertion stays true whatever the seed contains.
 */
function preparedAssetIds(request: RiskRequest, options: RiskStubOptions): {covered: number[]; excluded: number[]} {
    const all = request.scope.kind === ASSET_SET_SCOPE ? request.scope.asset_ids : [];
    if (!options.dropLastAsset || all.length < 2) return {covered: all, excluded: []};
    return {covered: all.slice(0, -1), excluded: all.slice(-1)};
}

/** The `assets_excluded` warning, verbatim, or nothing at all. */
function exclusionWarnings(excluded: readonly number[]) {
    if (excluded.length === 0) return [];
    return [
        {
            code: EXCLUDED_WARNING_CODE,
            message: EXCLUDED_WARNING_MESSAGE,
            details: {asset_ids: [...excluded]},
            degrades_result: true,
        },
    ];
}

/**
 * The provenance block every result carries, degraded together with the request.
 *
 * `n_observations` and `excluded_assets` are parameters rather than constants
 * because `RiskLevelSection` *renders* both — the first as the window under
 * `{testId}-metadata`, the second as the reason a row is blank — so a stub that
 * pinned them would make the two disclosures untestable while still filling the
 * frame. `levelMetadata` collapses identical rows, so every analytic of one
 * request agreeing here is what makes `data-rows="1"` mean "they agree" rather
 * than "there is one of them".
 */
function metadata(request: RiskRequest, analytic: RiskAnalyticRequest, options: RiskStubOptions = {}) {
    const observations = observationCount(options);
    // Scaled with the window, so the annualization factor stays a plausible
    // consequence of the two numbers beside it instead of contradicting them.
    const calendarDays = options.shortWindow ? 7 : 87;
    const {excluded} = preparedAssetIds(request, options);
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
        // `_build_context` names every requested asset it could not prepare, with
        // the reason the prepared set gave — `insufficient_history` is the default
        // that `service.py:594` falls back to.
        excluded_assets: isHistoricalReplay(analytic) ? [] : excluded.map((assetId) => ({asset_id: assetId, reason: INSUFFICIENT_HISTORY})),
        algorithm_version: MOCK_ALGORITHM_VERSION,
        computed_at: '2026-01-31T12:00:00Z',
        // `service.py:860` copies the plugin's audit into the metadata of every
        // replay, and `L4Replay` gates `risk-replay-audit` on it. Omitting it here
        // would leave one of the presence barriers below unsatisfiable — a barrier
        // that can never turn green is not stricter, it is broken.
        ...(isHistoricalReplay(analytic)
            ? {
                  historical_replay_audit: {
                      proxy_count: 0,
                      proxy_assets: [],
                      excluded_count: 0,
                      excluded_assets: [],
                      excluded_weight_total: 0,
                      missing_history_policy: 'manual_proxy_or_exclude',
                      composition_policy: 'current_buy_and_hold',
                      proxy_series_usage: 'returns_only',
                  },
              }
            : {}),
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
 *
 * An excluded asset never reaches the matrix: the exclusion happens while the
 * joint series are being prepared, one step before any analytic runs, so a matrix
 * that still carried the dropped id would describe a preparation that failed and
 * succeeded at the same time.
 */
function matrixAssetIds(request: RiskRequest, options: RiskStubOptions = {}): number[] {
    if (request.scope.kind !== ASSET_SET_SCOPE) return [];
    return preparedAssetIds(request, options).covered.slice(0, MATRIX_LIMIT);
}

/**
 * The ids the stubbed replay reports on: the whole scope, not the matrix slice.
 *
 * {@link MATRIX_LIMIT} exists to keep a *drawn* matrix cheap and to pin
 * `data-pairs-lead`; neither is a property of the replay, which returns one bar
 * per holding it could price. Reusing the matrix cap here would have been a
 * limit borrowed from another question.
 */
function replayAssetIds(request: RiskRequest): number[] {
    return request.scope.kind === 'asset_set' ? request.scope.asset_ids : [];
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

function correlationOutput(request: RiskRequest, options: RiskStubOptions = {}) {
    const assetIds = matrixAssetIds(request, options);
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
                observations: observationCount(options),
                coverage: rowIndex === columnIndex ? 1 : 0.88,
                status: 'ok',
            })),
        ),
    };
}

/**
 * ─── The weightless per-asset family ───────────────────────────────────────
 *
 * Five outputs, one row per prepared asset, and **not one amount between them**.
 * That is not restraint on this stub's part: `assetSetLevels.ts` has no
 * `currency` parameter and no field to put a sum in, and the payload models it
 * reads are `extra="forbid"`, so there is nowhere for money to enter. The five
 * builders below could not smuggle a euro onto this page if they tried — which
 * is what makes the money assertions in the first test still meaningful now that
 * two more sections render underneath them.
 *
 * Every figure comes from {@link INVENTED}. Read its banner before copying any
 * number out of here.
 */

/** Per-asset VaR/CVaR at one horizon. Positive magnitudes, CVaR ≥ VaR. */
function assetSetVarOutput(request: RiskRequest, analytic: RiskAnalyticRequest, options: RiskStubOptions) {
    const {covered} = preparedAssetIds(request, options);
    const horizonDays = Number(analytic.parameters?.horizon_days ?? 1);
    const horizonFactor = horizonDays > 1 ? INVENTED.monthFactor : 1;
    return {
        kind: 'var_cvar_set',
        confidence_level: Number(analytic.parameters?.confidence_level ?? 0.95),
        horizon_days: horizonDays,
        // Compounding to a multi-day horizon consumes observations, so the count
        // the tail was estimated from is `horizon_days - 1` fewer than the
        // window's — the backend says so in `RiskAssetSetVarCvarOutput`'s
        // docstring, and a flat copy of `n_observations` here would contradict it.
        observations: Math.max(1, observationCount(options) - (horizonDays - 1)),
        items: covered.map((assetId, index) => {
            const row = variant(index);
            const valueAtRisk = INVENTED.badDayVar(row) * horizonFactor;
            return {
                asset_id: assetId,
                value_at_risk: valueAtRisk,
                conditional_value_at_risk: valueAtRisk * INVENTED.tailWidening,
            };
        }),
    };
}

/** Per-asset dated drawdown episodes. Negative magnitudes; episode contract honoured. */
function assetSetDrawdownOutput(request: RiskRequest, options: RiskStubOptions) {
    const {covered} = preparedAssetIds(request, options);
    return {
        kind: 'drawdown_set',
        available_start: request.date_range.start,
        available_end: request.date_range.end ?? request.date_range.start,
        calculation_basis: 'daily_close',
        return_basis: 'price_only',
        items: covered.map((assetId, index) => {
            const row = variant(index);
            const maximumDrawdown = INVENTED.maximumDrawdown(row);
            const currentDrawdown = maximumDrawdown / 3;
            // Alternated so both halves of the episode contract get exercised: a
            // `recovered` episode must carry a recovery date, an `open` one must
            // not. A stub that only ever emitted one of them would satisfy the
            // validator by never reaching its other branch.
            const recovered = index % 2 === 0;
            return {
                asset_id: assetId,
                current_drawdown: currentDrawdown,
                current_peak_date: INVENTED.currentPeakDate,
                current_drawdown_duration_days: 30 + row * 5,
                maximum_drawdown: maximumDrawdown,
                maximum_drawdown_peak_date: INVENTED.peakDate,
                maximum_drawdown_trough_date: INVENTED.troughDate,
                maximum_drawdown_recovery_status: recovered ? 'recovered' : 'open',
                maximum_drawdown_recovery_date: recovered ? INVENTED.recoveryDate : null,
                maximum_drawdown_duration_days: 120 + row * 15,
                maximum_drawdown_recovered_ratio: recovered ? 1 : 0.45,
                // The asymmetry this column exists to teach: recovering a −6% fall
                // takes +6.4%, not +6%. Computed rather than tabulated so the
                // relationship stays true whatever the fall above becomes.
                remaining_to_peak_ratio: -currentDrawdown / (1 + currentDrawdown),
            };
        }),
    };
}

/** Per-asset historical KPIs. Tail ordering satisfied: CDaR ≤ DaR and CDaR ≥ max drawdown. */
function assetSetKpiOutput(request: RiskRequest, analytic: RiskAnalyticRequest, options: RiskStubOptions) {
    const {covered} = preparedAssetIds(request, options);
    return {
        kind: 'kpi_set',
        // An echo of the request parameter, which the page never overrides, so
        // the plugin's own default (`asset_set_kpi.py:59-60`) is what comes back.
        drawdown_confidence_level: Number(analytic.parameters?.drawdown_confidence_level ?? 0.95),
        items: covered.map((assetId, index) => {
            // The same figure `asset_set_drawdown` reports, because both are
            // measured on the one joint calendar this request prepared. Two
            // different maxima for one asset would be a seam the contract says
            // cannot exist.
            const row = variant(index);
            const maximumDrawdown = INVENTED.maximumDrawdown(row);
            const sharpe = INVENTED.sharpe(row);
            return {
                asset_id: assetId,
                volatility: INVENTED.volatility(row),
                max_drawdown: maximumDrawdown,
                max_drawdown_duration_days: 120 + row * 15,
                // Charged against the risk-free rate the request carries, which
                // this page always sets to 0: `AssetSetComparisonLevels` has no
                // control to set one and says so rather than inventing a rate.
                sharpe,
                sortino: sharpe * 1.3,
                worst_realization: -(0.03 + row * 0.005),
                worst_realization_date: INVENTED.troughDate,
                drawdown_at_risk: maximumDrawdown * 0.6,
                conditional_drawdown_at_risk: maximumDrawdown * 0.8,
                ulcer_index: 0.05 + row * 0.01,
            };
        }),
    };
}

/**
 * Per-asset risk and reward — and **no aggregate**, which is the point.
 *
 * There is deliberately no portfolio pair here and there is no field to put one
 * in: `RiskAssetSetReturnOutput` declares `kind` and `items` and nothing else.
 * That absence is what keeps `capitalMarketLine()` returning null, because the
 * line is drawn only when a point whose role is `portfolio` exists. So the
 * verdict "paid well for the risk" is not switched off on this page — it is
 * unexpressible, and making it expressible again would take an edit to
 * `schemas/risk.py`, visible in a diff.
 */
function assetSetRiskReturnOutput(request: RiskRequest, options: RiskStubOptions) {
    const {covered} = preparedAssetIds(request, options);
    return {
        kind: 'risk_return_set',
        items: covered.map((assetId, index) => ({
            asset_id: assetId,
            volatility: INVENTED.volatility(variant(index)),
            expected_annual_return: INVENTED.expectedReturn(variant(index)),
        })),
    };
}

/**
 * Per-asset comparison against one reference, plus the reference's own coordinates.
 *
 * 🔴 The reference is filtered out of `items` rather than merely assumed absent.
 * `RiskAssetSetComparisonOutput.validate_reference_is_not_a_subject` rejects a
 * payload where the yardstick is also one of the measured, so a stub that echoed
 * the whole scope back would be publishing a response the backend cannot emit —
 * and the page would then be tested against a payload no user can ever receive.
 * The panel already withholds a benchmark that is in the selection
 * (`AssetSetRiskPanel`'s `benchmarkId`), so this filter should never fire; it is
 * here so that the stub is *incapable* of breaking the invariant, not merely
 * unlikely to.
 */
function assetSetComparisonOutput(request: RiskRequest, analytic: RiskAnalyticRequest, options: RiskStubOptions) {
    const {covered} = preparedAssetIds(request, options);
    const comparisonAssetId = Number(analytic.parameters?.comparison_asset_id);
    return {
        kind: 'comparison_set',
        comparison_asset_id: comparisonAssetId,
        observations: observationCount(options),
        comparison_volatility: INVENTED.benchmarkVolatility,
        comparison_expected_annual_return: INVENTED.benchmarkExpectedReturn,
        items: covered
            .filter((assetId) => assetId !== comparisonAssetId)
            .map((assetId, index) => {
                const row = variant(index);
                const activeReturn = INVENTED.expectedReturn(row) - INVENTED.benchmarkExpectedReturn;
                const trackingError = INVENTED.trackingError(row);
                return {
                    asset_id: assetId,
                    active_return: activeReturn,
                    tracking_error: trackingError,
                    information_ratio: activeReturn / trackingError,
                    correlation: INVENTED.correlation(row),
                    beta: INVENTED.beta(row),
                };
            }),
    };
}

/** The per-asset output for whichever of the five this is, or null for the rest. */
function assetSetLevelOutput(request: RiskRequest, analytic: RiskAnalyticRequest, options: RiskStubOptions): Record<string, unknown> | null {
    if (analytic.analytic_code === 'asset_set_var') return assetSetVarOutput(request, analytic, options);
    if (analytic.analytic_code === 'asset_set_drawdown') return assetSetDrawdownOutput(request, options);
    if (analytic.analytic_code === 'asset_set_kpi') return assetSetKpiOutput(request, analytic, options);
    if (analytic.analytic_code === 'asset_set_risk_return') return assetSetRiskReturnOutput(request, options);
    if (analytic.analytic_code === 'asset_set_comparison') return assetSetComparisonOutput(request, analytic, options);
    return null;
}

/**
 * A historical replay carrying money the real backend never sends for this scope.
 *
 * `impact_amount` is populated at the top level *and* on every row, because those
 * are exactly the two places `L4Replay` would print it — `:213` inside the
 * composition sentence and `:147` in `rowAmount`, for every bar of the tornado.
 * That is the point: hand the page the data that does not exist today and see
 * whether it still refuses to show it.
 *
 * `portfolio_return` is the other half of the same bait, and it is deliberately
 * NOT what the backend does here: `stress.py:480-494` leaves it null on an
 * unweighted scope, and `L4Replay:207` therefore *withholds* the whole sentence
 * rather than degrading it. Reproduce that faithfully and `output.impact_amount`
 * becomes unreachable by construction — its absence would then prove nothing
 * about the guard, which is the precise failure {@link MONEY_AMOUNT} warns
 * about. Sending a return makes the sentence render, so `showMoney={false}` is
 * the only thing left between the payload and a euro on screen.
 *
 * Shape-faithful in every other respect: a replay carries no `dimension` and no
 * `configured_buckets` (`stress.py:561-567`), which is what makes `tornadoRows`
 * take its per-asset branch — the branch that reads `impact_amount`. A bucket
 * row carries `amount: null` and would have quietly disarmed the row half of
 * this test.
 */
function replayOutput(request: RiskRequest) {
    const assetIds = replayAssetIds(request);
    return {
        kind: 'stress',
        method: 'historical_replay',
        portfolio_return: REPLAY_RETURN,
        impact_amount: MONEY_AMOUNT,
        replay_range: {
            start: request.date_range.start,
            end: request.date_range.end ?? request.date_range.start,
        },
        impacts: assetIds.map((assetId, index) => ({
            asset_id: assetId,
            // Spread so the bars differ from each other; `contribution_return` is
            // omitted because an unweighted scope has no weights to contribute
            // with (`stress.py:541`), which sends `tornadoRows` to `shock_return`.
            shock_return: REPLAY_RETURN + index / 1000,
            impact_amount: MONEY_AMOUNT,
            metadata_fallback: false,
        })),
    };
}

function resultFor(request: RiskRequest, analytic: RiskAnalyticRequest, options: RiskStubOptions = {}): Record<string, unknown> {
    const {excluded} = preparedAssetIds(request, options);
    const base = {
        instance_id: analytic.instance_id,
        analytic_code: analytic.analytic_code,
        metadata: metadata(request, analytic, options),
        data_quality: dataQuality(),
        warnings: [],
    };

    // A window below this analytic's own `min_observations` never reaches the
    // plugin: `service.py:230-243` answers `unavailable` with the count it had
    // and the count it needed, carrying metadata and data quality but **no
    // warnings** — `_unavailable` does not take any. That asymmetry is what makes
    // `{testId}-errors` and `{testId}-reasons` two different disclosures rather
    // than two views of one, and reproducing it is what lets a test tell them
    // apart.
    if (isAssetSetLevel(analytic) && belowMinimumObservations(analytic, observationCount(options))) {
        const required = CATALOG.items.find((item) => item.analytic_code === analytic.analytic_code)?.min_observations;
        return {
            ...base,
            status: 'unavailable',
            output: null,
            error: {
                code: INSUFFICIENT_HISTORY,
                message: `Analytic '${analytic.analytic_code}' requires at least ${required} observations`,
                details: {observations: observationCount(options), required},
            },
        };
    }

    // An excluded asset degrades the whole request, not one analytic: the status
    // becomes `partial` and one `assets_excluded` warning rides on every result
    // (`service.py:766-783`). Both halves matter — `degradedResults` reads the
    // status, `resultReasons` reads the sentence — and a stub that sent one
    // without the other would leave whichever half it omitted untested.
    const degraded = excluded.length > 0;
    const answered = {
        ...base,
        status: degraded ? 'partial' : 'ok',
        warnings: exclusionWarnings(excluded),
    };

    if (analytic.analytic_code === 'correlation') return {...answered, output: correlationOutput(request, options)};
    if (isAssetSetLevel(analytic)) return {...answered, output: assetSetLevelOutput(request, analytic, options)};
    // The replay is prepared by itself (`_prepare_historical_replay` sets
    // `excluded_assets=()`), so it is answered from `base` and never degrades
    // with the historical wave.
    if (isHistoricalReplay(analytic)) return {...base, status: 'ok', output: replayOutput(request)};

    // Anything else reaching this page is a change in what the panel requests, and
    // should say so loudly rather than render an empty frame. The *hypothetical
    // shock* is deliberately in that set now: `03-mappa-livelli-pagine` §3.3
    // forbids it on a page with no weights, and `AssetSetReplaySection` supplies
    // `L4WhatIf` with the replay snippet only — so a `stress` request that is not
    // a replay means the forbidden rung came back.
    return {
        ...base,
        status: 'failed',
        output: null,
        error: {code: 'analytic_not_found', message: `Unexpected E2E analytic ${analytic.analytic_code}`},
    };
}

/** Stub the three risk endpoints and hand back the requests the page actually made. */
async function installRiskMocks(page: Page, options: RiskStubOptions = {}): Promise<RiskRequest[]> {
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
            body: JSON.stringify({items: request.analytics.map((analytic) => resultFor(request, analytic, options))}),
        });
    });

    return requests;
}

/** Every captured request that asked the joint-calendar question of an asset set. */
function assetSetHistoricalRequests(requests: readonly RiskRequest[]): RiskRequest[] {
    return requests.filter((request) => request.scope.kind === ASSET_SET_SCOPE && request.mode === 'historical');
}

/**
 * The requests carrying any of the five per-asset codes.
 *
 * Deliberately *not* "every asset-set historical request": the laboratory puts
 * more than one of those on the wire and always has. `AssetSetCorrelationSection`
 * and `AssetSetReplaySection` each build their own controller without
 * `includeAssetSetLevels`, so their wave is `[correlation]` — canonically equal
 * to each other, hence one network call between them — while
 * `AssetSetComparisonLevels` asks for `correlation` plus the five and is
 * therefore a second, differently-shaped request. Counting all asset-set
 * historical requests and expecting one would assert something false about the
 * page; what has to be true is that the **five travel together**.
 */
function assetSetLevelRequests(requests: readonly RiskRequest[]): RiskRequest[] {
    return assetSetHistoricalRequests(requests).filter((request) => request.analytics.some((analytic) => isAssetSetLevel(analytic)));
}

/** The analytic codes of one request, deduplicated — the two VaR horizons share one. */
function codesOf(request: RiskRequest): Set<string> {
    return new Set(request.analytics.map((analytic) => analytic.analytic_code));
}

/** An asset-set scope as a comparable string, in the ascending order the client sends. */
function scopeKey(assetIds: readonly number[]): string {
    return [...assetIds].sort((left, right) => left - right).join(',');
}

/**
 * The per-asset waves asked about exactly this selection.
 *
 * Filtered by scope and not merely counted, because a test that grows the
 * selection — `ensureSelectionAtLeast` does, when the seed is small — legitimately
 * produces a second wave for the second scope. Counting all of them and expecting
 * one would then be a test of the fixture's size rather than of the page, green on
 * a large seed and red on a small one with nothing wrong either time.
 */
function levelRequestsFor(requests: readonly RiskRequest[], selection: readonly number[]): RiskRequest[] {
    const wanted = scopeKey(selection);
    return assetSetLevelRequests(requests).filter((request) => request.scope.kind === ASSET_SET_SCOPE && scopeKey(request.scope.asset_ids) === wanted);
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
 * section means "unsupported" *or* "not loaded yet". The page publishes which
 * one; wait for the gate rather than for the gated.
 *
 * The attribute used to come from the legacy `RiskAnalysisPanel`, which no longer
 * mounts here — a gate on a component that left is a gate that waits forever.
 * `AssetSetCorrelationSection` publishes the same three-value vocabulary
 * (`ready` | `error` | `pending`) from its own controller, on the div that
 * already carried `data-busy`.
 *
 * It speaks for the replay below as well, and not by luck: `fetchRiskCatalog`
 * holds a module-level cache plus an in-flight promise (`riskStore:74-77`), so
 * the two sibling controllers await the *same* promise and both assign their
 * catalog in the same microtask drain — before any DOM flush could publish
 * `ready` here. Should that ever stop being true, the `expect.poll` on the
 * captured requests is what turns it into a named failure instead of a mystery.
 */
async function waitForRiskCatalog(page: Page): Promise<void> {
    await expect(page.getByTestId('asset-global-risk-panel').getByTestId('risk-correlation-content')).toHaveAttribute('data-catalog', 'ready', {timeout: 20_000});
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

/** The L1° section frame, and the table it wraps. Scoped: the page has two levels. */
const lossSection = (page: Page) => page.getByTestId('asset-global-risk-panel').getByTestId('risk-asset-set-loss');
const lossTable = (page: Page) => page.getByTestId('risk-asset-set-l1-table');
const paidSection = (page: Page) => page.getByTestId('asset-global-risk-panel').getByTestId('risk-asset-set-paid');

/** The five per-asset cells of the L1° transposition, in the order they are drawn. */
const L1_CELLS = ['badDay', 'badMonth', 'worstFall', 'currentFall', 'toPeak'] as const;

/**
 * The asset ids the L1° table drew a row for, read from the rows themselves.
 *
 * `data-asset-id` is on the row because the table is a *transposition*: the
 * reader compares instruments down the page, so the row is the identity and the
 * column is the measure. Reading it back is what lets an assertion be phrased
 * over the selection rather than over positions.
 */
async function lossRowAssetIds(page: Page): Promise<number[]> {
    return (
        await lossTable(page)
            .getByTestId('risk-asset-set-l1-row')
            .evaluateAll((nodes) => nodes.map((node) => Number(node.getAttribute('data-asset-id'))))
    ).filter((id) => Number.isInteger(id));
}

/** A single L1° cell, addressed by the asset it belongs to — never by position. */
function lossCell(page: Page, assetId: number, cell: (typeof L1_CELLS)[number]) {
    return lossTable(page).locator(`tr[data-asset-id="${assetId}"] [data-testid="risk-asset-set-l1-${cell}"]`);
}

/**
 * Wait until L1° has stopped being a skeleton and is showing its table.
 *
 * `AssetSetLossComparisonSection` draws the skeleton while `loading` and no
 * figure has arrived, so the table's presence *is* the "the wave landed" signal
 * for this level: it cannot appear before the controller has resolved. Which is
 * why this is a barrier and not a sleep — there is a state to wait for, and the
 * product already publishes it.
 */
async function waitForLossTable(page: Page): Promise<void> {
    await expect(lossTable(page)).toBeVisible({timeout: 20_000});
    await expect(page.getByTestId('risk-asset-set-l1-loading')).toHaveCount(0);
}

/** The user id the benchmark store will scope its storage key with. */
async function currentUserId(page: Page): Promise<number> {
    const response = await page.request.get('/api/v1/auth/me');
    expect(response.ok(), 'the shared benchmark is stored under a user-scoped key, so the test needs the id the app resolves').toBe(true);
    const body = (await response.json()) as {user?: {id?: number}};
    const id = body.user?.id;
    expect(Number.isInteger(id), `auth/me must publish an integer user id, read ${JSON.stringify(body.user)}`).toBe(true);
    return id as number;
}

/**
 * The key `riskBenchmarkStore` reads its choice from.
 *
 * Reproduced from `storageKey()` in that module rather than guessed: the prefix,
 * the user id and the base key are three separate decisions there, and the
 * user-scoped half exists precisely so one reader's benchmark is not handed to
 * the next account on the same browser. A test that wrote the un-scoped key
 * would be seeding a value the app never reads once someone is logged in.
 */
function benchmarkStorageKey(userId: number | 'anon'): string {
    return `lf_${userId}_risk_benchmark_asset`;
}

/**
 * An asset the picker offers but the selection does not hold.
 *
 * Both halves are required of an L3° benchmark: it has to be a real asset, and
 * it must not be one of the measured, because
 * `RiskAssetSetComparisonOutput.validate_reference_is_not_a_subject` rejects a
 * yardstick that is also a subject — and `AssetSetRiskPanel` withholds the
 * benchmark entirely rather than send a request the backend would refuse. The
 * picker's own filter (`pageAssetIds.has(id) && !selectedAssetIds.includes(id)`)
 * already guarantees both, so reading a candidate off it is the same decision the
 * product makes rather than an independent one that could disagree.
 *
 * Leaves the dropdown closed, which is not politeness: `search-select-option-*`
 * is a shared namespace, so an option list left open is indistinguishable from
 * the next one's.
 */
async function pickUnselectedAssetId(page: Page): Promise<number> {
    const picker = page.getByTestId('risk-asset-add-select');
    const combobox = picker.locator('[role="combobox"]');
    const options = picker.locator('[data-testid^="search-select-option-"]');
    await combobox.click();
    const option = options.first();
    await expect(option).toBeVisible({timeout: 10_000});
    const testId = await option.getAttribute('data-testid');
    const assetId = Number(testId?.replace('search-select-option-', ''));
    expect(Number.isInteger(assetId), `the asset picker must key its options by asset id, read "${testId}"`).toBe(true);

    // Pressed on the combobox rather than on the page: `AssetSelect` mounts
    // `SearchSelect` with `inlineSearch`, so there is no search field to receive
    // focus and the trigger keeps it — `handleTriggerKeydown` then forwards
    // Escape to `handleSearchKeydown`, which closes. Addressing the element makes
    // that a fact instead of an assumption about where focus drifted.
    await combobox.press('Escape');
    await optionsClosed(page);
    return assetId;
}

/** Two sets compared as sets, so declaration order can never be the subject. */
function sameMembers(left: readonly string[], right: readonly string[]): boolean {
    if (left.length !== right.length) return false;
    const rightSet = new Set(right);
    return left.every((entry) => rightSet.has(entry));
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
        // Two more sections now render inside the panel this test scans, and both
        // are asserted to be *populated* before the scan — a table of figures and
        // an ECharts canvas. That is real work added to an already long test, and
        // the budget is raised to pay for it rather than left to be discovered as
        // a timeout under four workers. It is not a hedge against slowness: every
        // wait below is a barrier on a published state, so a genuinely slow page
        // still fails here, just with the assertion's own message.
        test.setTimeout(45_000);
        const requests = await installRiskMocks(page);
        await openAssetGlobalRisk(page);
        // L3° draws its scatter only from two dots up: one point is a fact without
        // a comparison. Made a precondition rather than inherited from the seed, so
        // the chart assertion below cannot be quietly skipped by a small fixture.
        await ensureSelectionAtLeast(page, 2);
        await waitForRiskCatalog(page);

        const panel = page.getByTestId('asset-global-risk-panel');

        // ① and ② — the CAUSE, of which the money assertions at the end of this
        // test are the EFFECT. The legacy monolith contributed exactly two things
        // to this page: a *second* correlation matrix, which made every selector
        // inside it ambiguous under Playwright strict mode, and the hypothetical
        // shock, which `03-mappa-livelli-pagine` §3.3 forbids where there are no
        // weights. Both are structural facts, and a count is the right shape for
        // them: it is dimensional, so unlike a text scan it cannot fall silent.
        //
        // Neither pair can stand in for the other. If some other component started
        // printing euros here tomorrow, ① and ② would still be green; and a matrix
        // mounted twice prints no euros at all, so the money block would stay green
        // through the very regression ② exists for.
        //
        // The absence in ① is readable because `waitForRiskCatalog` above already
        // proved the analysis mounted and loaded: "not there" and "not yet" are
        // otherwise the same observation.
        await expect(panel.getByTestId('risk-analysis-panel'), 'the legacy monolith must not be mounted on the asset-set page').toHaveCount(0);
        // Document-level on purpose: strict-mode ambiguity is a property of the
        // page, not of a subtree, and the two ordering tests below reach for
        // `risk-correlation-heatmap` unscoped.
        await expect(page.getByTestId('risk-correlation-heatmap'), 'the heatmap must be mounted exactly once').toHaveCount(1);

        // ③ — the two comparison levels, mounted and POPULATED.
        //
        // This block exists so that the money assertions at the end of this test
        // keep *reaching* what they are supposed to reach. They scan
        // `asset-global-risk-panel`, which now contains L1° and L3° as well; an
        // unpopulated section contributes no text, so without these barriers the
        // scan would pass over two empty frames and the coverage of the rule would
        // silently have shrunk to the replay again. Extending the reach of the
        // existing net is the point — a second, parallel money test would prove the
        // same thing about a different page state and leave this one unguarded.
        //
        // The new sections cannot *introduce* an amount, and not because they
        // suppress one: `assetSetLevels.ts` takes no `currency` parameter, returns
        // no amount, and the five payload models it reads have no monetary field
        // at all (`RiskAssetSetReturnOutput` is `kind` plus `items`, and every model
        // in the family is `extra="forbid"`). So what follows is not a suspicion
        // about these components — it is the guarantee that the day someone adds a
        // currency-aware figure to this page, the scan below is already looking.
        const selectedForLevels = await chipIds(page);
        await waitForLossTable(page);
        await expect(lossTable(page)).toHaveAttribute('data-row-count', String(selectedForLevels.length));
        await expect(lossTable(page).locator('[data-testid="risk-asset-set-l1-badDay"][data-measured="true"]'), 'L1° must be showing figures, or the money scan below crosses an empty table').toHaveCount(selectedForLevels.length);

        const scatter = panel.getByTestId('risk-asset-set-l3-risk-return');
        await expect(scatter).toBeVisible({timeout: 20_000});
        await expectChartCanvas(page, 'risk-asset-set-l3-scatter', 20_000);
        // 🔴 One dot per measured asset, and NOT ONE MORE. There is no Capital
        // Market Line here and there cannot be: `capitalMarketLine()` draws only
        // when a point whose role is `portfolio` exists, and that point exists only
        // when the payload carries a portfolio volatility *and* expected return —
        // fields `RiskAssetSetReturnOutput` does not have. The line has no DOM
        // handle to assert on, so the count is the observable: a fabricated
        // aggregate would arrive as an extra dot before it could ever become a
        // line, and this number would move. With no benchmark chosen, there is no
        // reference dot either, so the expected count is exactly the selection.
        await expect(page.getByTestId('risk-asset-set-l3-scatter')).toHaveAttribute('data-point-count', String(selectedForLevels.length));
        await expect(page.getByTestId('risk-asset-set-l3-scatter')).toHaveAttribute('data-dropped-count', '0');

        // The replay is where the money now arrives. `AssetSetReplaySection` mounts
        // `RiskLevelSection` with `collapsible`, so the rung starts closed and loads
        // its scenario catalogue on first open only. The click below is a *toggle* —
        // the assertion above it is what makes "it is closed" a fact rather than an
        // assumption, which is the whole difference between opening a section and
        // shutting one.
        const replaySection = page.getByTestId('risk-replay-section');
        await expect(replaySection).toBeVisible({timeout: 15_000});
        await expect(replaySection, 'L4 opens closed: reopening a drawer is not a change of question').toHaveAttribute('data-open', 'false');
        await page.getByTestId('risk-replay-section-toggle').click();
        await expect(replaySection).toHaveAttribute('data-open', 'true');
        await expect(page.getByTestId('risk-replay-section-body')).toBeVisible();

        // Only the first rung is supplied, so this is the whole of L4 here.
        await expect(page.getByTestId('risk-l4-replay')).toBeVisible();
        const runReplay = page.getByTestId('risk-replay-run');
        await expect(runReplay).toBeEnabled();
        await runReplay.click();

        // Presence barriers first. "No € on the page" is also true of a page that
        // rendered nothing at all, so the money-bearing payload has to be proved to
        // have *reached the renderer* before its absence means anything. These three
        // are not decoration: each one is a place the stubbed amount would surface.
        // `risk-replay-total` interpolates the top-level `impact_amount`
        // (`L4Replay:213`), every tornado row runs `rowAmount` (`:147`), and
        // `risk-replay-audit` proves the answer is a *replay* — no other analytic
        // carries `historical_replay_audit`.
        await expect(page.getByTestId('risk-replay-total')).toBeVisible({timeout: 20_000});
        await expect(page.getByTestId('risk-l4-replay').getByTestId('risk-replay-tornado-row').first()).toBeVisible({timeout: 20_000});
        await expect(page.getByTestId('risk-replay-audit')).toBeVisible({timeout: 20_000});
        await expect
            .poll(() => requests.some((request) => request.scope.kind === 'asset_set' && request.mode === 'current_composition' && request.analytics.some((analytic) => isHistoricalReplay(analytic))), {
                timeout: 15_000,
                message: 'the replay must have run against an asset_set scope — that is the scope the no-money rule is about',
            })
            .toBe(true);

        const rendered = await panel.innerText();

        // The section is populated with the half it is allowed to show: a realised
        // return is a percentage, and percentages are what an unweighted set can
        // honestly say.
        //
        // Scoped to the rung, where the old assertion scanned the whole panel. It
        // had to change anyway — the shock it spoke for is gone — and a `%` printed
        // by the matrix above would have satisfied a panel-wide version while the
        // replay rendered nothing at all.
        const replayText = await page.getByTestId('risk-l4-replay').innerText();
        expect(replayText, 'the replay rendered without a single percentage — the barriers above are lying').toContain('%');

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

    /**
     * ═══════════════════════════════════════════════════════════════════════
     * THE GUARD. Everything above this line is stubbed; this is the one test
     * that talks to the real backend, and it exists because of the stubbing.
     * ═══════════════════════════════════════════════════════════════════════
     *
     * {@link CATALOG} is a hand-written copy of a table that lives in Python, with
     * no link between the two. Every drift is therefore invisible **by
     * construction**, and the drift is never loud: `hasRiskCapability` simply
     * returns false, `buildBaseAnalytics` silently omits the code, the section
     * renders its empty frame, and whatever test was watching that section goes
     * green having measured nothing. Three of those have been paid for already —
     * `asset_risk_return` missing from a mock catalogue, `historical_kpi` mocked
     * as one mode where the registry advertises two, and five `asset_set_*` codes
     * that no mock knew about at all.
     *
     * So this test closes the loop the only way it can be closed: it fetches the
     * live catalogue and compares it, code by code, against the copy.
     *
     * 🔴 IT DELIBERATELY DOES NOT CALL `installRiskMocks`. Routing
     * `/api/v1/risk/catalog` here would hand the stub back to itself and the
     * comparison would be `CATALOG === CATALOG` — green forever, which is the
     * exact failure mode the test was written to end. That is not left to a
     * convention either: {@link MOCK_ALGORITHM_VERSION} is a sentinel no real
     * definition carries, and the first assertion below is that none came back
     * wearing it. A future edit that adds the mocks to this test — or moves them
     * into the `beforeEach` — turns red here instead of turning vacuous.
     */
    test('the mocked risk catalogue declares what the backend declares', async ({page}) => {
        const response = await page.request.get('/api/v1/risk/catalog');
        expect(response.status(), 'the live risk catalogue must answer 200 to the logged-in session — the comparison below is worthless without it').toBe(200);

        // Parsed through the generated schema rather than cast: a 200 carrying
        // something that is not a catalogue would otherwise produce an empty map
        // and a vacuously passing comparison.
        const live = schemas.RiskCatalogResponse.parse(await response.json());
        const backend = new Map((live.items ?? []).map((definition) => [definition.analytic_code, definition]));
        expect(backend.size, 'the backend catalogue came back empty, so every comparison below would pass against nothing').toBeGreaterThan(0);
        expect(
            [...backend.values()].filter((definition) => definition.algorithm_version === MOCK_ALGORITHM_VERSION).map((definition) => definition.analytic_code),
            `this answer carries ${MOCK_ALGORITHM_VERSION}, so it came from this file's own stub and the comparison below would be the mock checked against itself`,
        ).toEqual([]);

        const drift: string[] = [];

        // Direction 1 — what the mock claims, the backend must confirm.
        // This is the direction that matters to every other test in this file:
        // a mock that advertises *more* than the backend makes the page request
        // an analytic the backend will refuse, and a mock that advertises *less*
        // makes the page not ask at all.
        for (const mocked of CATALOG.items) {
            const real = backend.get(mocked.analytic_code);
            if (!real) {
                drift.push(`${mocked.analytic_code}: mocked here but ABSENT from the backend catalogue (mock declares scopes=[${mocked.supported_scopes.join(', ')}] modes=[${mocked.supported_modes.join(', ')}])`);
                continue;
            }
            if (!sameMembers(mocked.supported_scopes, real.supported_scopes)) {
                drift.push(`${mocked.analytic_code}.supported_scopes: mock=[${mocked.supported_scopes.join(', ')}] backend=[${real.supported_scopes.join(', ')}]`);
            }
            if (!sameMembers(mocked.supported_modes, real.supported_modes)) {
                drift.push(`${mocked.analytic_code}.supported_modes: mock=[${mocked.supported_modes.join(', ')}] backend=[${real.supported_modes.join(', ')}]`);
            }
        }

        // Direction 2 — and narrowly, because a blanket reverse check is noise.
        // This spec drives the asset-set page, so every `asset_set`-capable code
        // the backend grows is a section this file may now be failing to
        // exercise; a portfolio-only code it grows is none of this file's
        // business. That is the shape the five new codes arrived in.
        const assetSetCodes = [...backend.values()].filter((definition) => definition.supported_scopes.includes(ASSET_SET_SCOPE)).map((definition) => definition.analytic_code);
        const mockedCodes = new Set(CATALOG.items.map((item) => item.analytic_code));
        for (const code of assetSetCodes) {
            if (!mockedCodes.has(code)) {
                drift.push(`${code}: the backend advertises it for the asset_set scope and this spec's CATALOG does not declare it, so the laboratory never requests it here`);
            }
        }

        // Compared as sets and reported as text, so a red names the code and both
        // tuples: the point of this test is that its failure message tells you
        // what drifted without opening either file.
        expect(drift, `The mocked risk catalogue has drifted from the backend registry:\n  - ${drift.join('\n  - ')}\nFix ${'`CATALOG`'} in this spec (or the registry, if the backend is the side that is wrong).`).toEqual([]);
    });

    /**
     * (a) + (b) — one request, and one row per selected asset.
     *
     * The two belong together because the second is only meaningful given the
     * first: L1° is a *transposition* of a joint measurement, so every row has to
     * come from the same prepared calendar. Split across requests the rows would
     * still line up on screen and would no longer be comparable.
     */
    test('the five per-asset analytics travel in one request, and L1° gives every selected asset a row', async ({page}) => {
        const requests = await installRiskMocks(page);
        await openAssetGlobalRisk(page);
        await ensureSelectionAtLeast(page, MINIMUM_SELECTION);
        await waitForRiskCatalog(page);
        await waitForLossTable(page);

        // ① ONE REQUEST. `service.py:170` prepares the joint series once per
        // request, before the analytic loop, so five separate requests would pay
        // for five preparations and — the part that reaches the reader — would put
        // dots from five calendars on one chart. `queryRisk` caches on the
        // canonical request, so "they were asked together" is observable exactly
        // here, on the wire, and nowhere else.
        //
        // Scoped to the selection the page is showing: the laboratory legitimately
        // puts more than one asset-set historical request on the wire — the
        // correlation and replay sections build their own controllers without
        // `includeAssetSetLevels`, so their wave is `[correlation]` — and growing
        // the selection above adds a second scope. What must be true is that the
        // five are never split, not that the page makes one call.
        const selected = await chipIds(page);
        expect(selected.length, 'the transposition needs more than one instrument to be a comparison').toBeGreaterThanOrEqual(MINIMUM_SELECTION);
        await expect.poll(() => levelRequestsFor(requests, selected).length, {timeout: 20_000, message: 'the per-asset wave must be asked for exactly once for the selection on screen'}).toBe(1);

        // …and no request anywhere carried a *part* of it. The assertion above
        // would still pass if a stray second request had smuggled one code out on
        // its own; this one is what forbids the split outright.
        for (const request of assetSetHistoricalRequests(requests)) {
            const carried = ASSET_SET_LEVEL_CODES.filter((code) => codesOf(request).has(code));
            if (carried.length === 0) continue;
            expect([...carried].sort(), 'a request may carry the whole per-asset wave or none of it, never a slice').toEqual([...ASSET_SET_UNCONDITIONAL_CODES].sort());
        }

        const levels = levelRequestsFor(requests, selected)[0];
        const codes = codesOf(levels);
        // Only four of the five ride unconditionally: `asset_set_comparison` needs
        // a benchmark, and this context has none. Asserting all five here would
        // fail for the right reason on the wrong page — the benchmark branch has
        // its own test below.
        for (const code of ASSET_SET_UNCONDITIONAL_CODES) {
            expect([...codes], `${code} must travel with the rest of the per-asset wave`).toContain(code);
        }
        expect([...codes], 'no benchmark is chosen in this context, so the comparison must not have been asked for').not.toContain('asset_set_comparison');

        // ② THE TWO HORIZONS ARE TWO INSTANCES, NOT TWO REQUESTS. They share an
        // analytic code, so only the instance id keeps the bad day and the bad
        // month apart; a stub that resolved by code would answer both with
        // whichever arrived first and the two columns would silently become one.
        const varInstances = levels.analytics.filter((analytic) => analytic.analytic_code === 'asset_set_var');
        expect(varInstances.map((analytic) => analytic.instance_id).sort()).toEqual(['base-historical-asset_set_var', 'base-historical-asset_set_var-monthly']);
        expect(
            varInstances.map((analytic) => Number(analytic.parameters?.horizon_days)).sort((left, right) => left - right),
            'the bad month is a second measurement over a compounded horizon, never the bad day scaled',
        ).toEqual([1, 21]);

        // ③ THE TRANSPOSITION. One row per *selected* asset — asserted against the
        // chips the page is actually showing, because the opening selection is
        // seed data this test does not own. A literal here would be a count of
        // somebody else's fixture.
        await expect(lossTable(page)).toHaveAttribute('data-row-count', String(selected.length));
        const rows = lossTable(page).getByTestId('risk-asset-set-l1-row');
        await expect(rows).toHaveCount(selected.length);
        expect(
            [...(await lossRowAssetIds(page))].sort((left, right) => left - right),
            'the rows must be the selection, not a slice of it and not a superset',
        ).toEqual([...selected].sort((left, right) => left - right));

        // ④ EVERY CELL OF EVERY ROW IS MEASURED, and says so. `data-measured` is
        // the contract that distinguishes "—" meaning *not measurable* from "—"
        // meaning *not loaded*; with a complete payload every cell must be on the
        // measured side of it, and a count is what makes that statement cover all
        // the rows instead of a sampled one.
        for (const cell of L1_CELLS) {
            await expect(lossTable(page).locator(`[data-testid="risk-asset-set-l1-${cell}"][data-measured="true"]`), `every ${cell} cell must be measured when the wave came back whole`).toHaveCount(selected.length);
        }

        // ⑤ The level came back whole, so it discloses nothing. Read after the
        // barriers above, which is what makes the absence mean "nothing to
        // disclose" rather than "not rendered yet".
        await expect(lossSection(page).getByTestId('risk-asset-set-loss-health')).toHaveCount(0);
        await expect(lossSection(page).getByTestId('risk-asset-set-loss-errors')).toHaveCount(0);
        await expect(lossSection(page).getByTestId('risk-asset-set-loss-reasons')).toHaveCount(0);
        // Provenance is always published, and one row means every analytic of the
        // level agrees about the window it measured. Two would mean they disagree,
        // which is the case the row count exists to make visible.
        await expect(lossSection(page).getByTestId('risk-asset-set-loss-metadata')).toHaveAttribute('data-rows', '1');
        await expect(lossSection(page).getByTestId('risk-asset-set-loss-metadata-observations')).toHaveText(String(AMPLE_OBSERVATIONS));
    });

    /**
     * (c) — the rule the component exists to enforce.
     *
     * A selected asset the backend could not measure keeps its row. Dropping it
     * would be a different claim: the reader *chose* that asset, and a missing row
     * reads as "not selected" rather than "not measurable". `assetSetLevels.ts`
     * says so in its own header — rows are built from the selection and the cells
     * are nullable, never the other way round — and this is where that survives
     * contact with a payload that is genuinely short of one asset.
     */
    test('a selected asset the backend could not measure keeps its row, with the reason on the section', async ({page}) => {
        const requests = await installRiskMocks(page, {dropLastAsset: true});
        await openAssetGlobalRisk(page);
        await ensureSelectionAtLeast(page, MINIMUM_SELECTION);
        await waitForRiskCatalog(page);
        await waitForLossTable(page);

        // Which asset went missing is read from the request the stub answered, not
        // assumed from the chips: the client canonicalises `asset_ids` ascending
        // before sending, and the chips render in name order, so guessing here
        // would be guessing at two orderings at once.
        const selected = await chipIds(page);
        await expect.poll(() => levelRequestsFor(requests, selected).length, {timeout: 20_000, message: 'the per-asset wave must have been requested for the selection on screen'}).toBe(1);
        const levels = levelRequestsFor(requests, selected)[0];
        const scope = levels.scope.kind === ASSET_SET_SCOPE ? levels.scope.asset_ids : [];
        expect(scope.length, 'dropping one asset needs at least two to have been asked about').toBeGreaterThanOrEqual(2);
        const unmeasured = scope[scope.length - 1];
        const measured = scope.slice(0, -1);

        // THE RULE. The row count follows the *selection*, which still holds every
        // asset — including the one no analytic answered for.
        expect(selected, 'the unmeasured asset is still selected; that is the whole premise').toContain(unmeasured);
        await expect(lossTable(page)).toHaveAttribute('data-row-count', String(selected.length));
        await expect(lossTable(page).getByTestId('risk-asset-set-l1-row')).toHaveCount(selected.length);
        await expect(lossTable(page).locator(`tr[data-asset-id="${unmeasured}"]`), 'the asset nobody could measure must still have a row of its own').toHaveCount(1);

        // …and every one of its cells declares itself unmeasured, rather than
        // printing a zero. `data-measured="false"` is the difference between "this
        // asset did not move" and "nobody could tell".
        for (const cell of L1_CELLS) {
            await expect(lossCell(page, unmeasured, cell), `${cell} of an unprepared asset must report data-measured="false", never a figure`).toHaveAttribute('data-measured', 'false');
        }

        // The control half: the assets that *were* prepared are measured, which is
        // what stops "every cell is blank" from satisfying the assertion above.
        for (const cell of L1_CELLS) {
            await expect(lossTable(page).locator(`[data-testid="risk-asset-set-l1-${cell}"][data-measured="true"]`)).toHaveCount(measured.length);
        }

        // AND THE PAGE SAYS WHY. An exclusion degrades every analytic of the
        // request (`service.py:783`), so all three of L1°'s results come back
        // `partial` and all three carry the one `assets_excluded` sentence —
        // deduplicated for the reader, counted in the attribute.
        const health = lossSection(page).getByTestId('risk-asset-set-loss-health');
        await expect(health).toBeVisible();
        await expect(health, 'L1° reads three results — the two VaR horizons and the drawdown — and an exclusion degrades all of them').toHaveAttribute('data-count', '3');

        const reasons = lossSection(page).getByTestId('risk-asset-set-loss-reasons');
        await expect(reasons).toBeVisible();
        await expect(reasons, 'one distinct sentence, however many results carried it').toHaveAttribute('data-count', '1');
        await expect(reasons.getByTestId('risk-asset-set-loss-reason'), 'its arity is published rather than drawn three times').toHaveAttribute('data-occurrences', '3');

        // Nothing *failed* — a degraded measurement is not an absent one, and the
        // two disclosures are deliberately separate lists. The barriers above make
        // this absence a statement instead of a race.
        await expect(lossSection(page).getByTestId('risk-asset-set-loss-errors')).toHaveCount(0);
    });

    /**
     * (d) — the mixed-status case, and it is real rather than contrived.
     *
     * `asset_set_drawdown` declares `min_observations = 2`; the other four declare
     * 20. So a window of five observations is not a construction — it is a window,
     * and the backend's own gate turns it into one `ok` beside four `unavailable`.
     * Without disclosure the reader sees four blanks and one table and cannot tell
     * a short window from a broken page, which is the whole reason
     * `RiskLevelSection` publishes health, errors, reasons and provenance
     * separately.
     */
    test('a window too short for four of the five analytics is disclosed, not blanked', async ({page}) => {
        await installRiskMocks(page, {shortWindow: true});
        await openAssetGlobalRisk(page);
        await ensureSelectionAtLeast(page, MINIMUM_SELECTION);
        await waitForRiskCatalog(page);
        // The table still renders: rows come from the selection, so a level with
        // nothing to say still says it about every asset the reader chose.
        await waitForLossTable(page);

        const selected = await chipIds(page);

        // THE SPLIT, on screen. The drawdown survived the window and its three
        // columns are measured; the two VaR horizons did not and theirs are not.
        // Asserted per column rather than per row, because the split is a property
        // of the analytic and every row is on the same side of it.
        for (const cell of ['worstFall', 'currentFall', 'toPeak'] as const) {
            await expect(lossTable(page).locator(`[data-testid="risk-asset-set-l1-${cell}"][data-measured="true"]`), `${cell} comes from asset_set_drawdown, which needs 2 observations and had ${SHORT_OBSERVATIONS}`).toHaveCount(selected.length);
        }
        for (const cell of ['badDay', 'badMonth'] as const) {
            await expect(lossTable(page).locator(`[data-testid="risk-asset-set-l1-${cell}"][data-measured="false"]`), `${cell} comes from asset_set_var, which needs 20 observations and had ${SHORT_OBSERVATIONS}`).toHaveCount(selected.length);
        }

        // THE DISCLOSURE. Two of L1°'s three results did not come back…
        const health = lossSection(page).getByTestId('risk-asset-set-loss-health');
        await expect(health).toBeVisible();
        await expect(health, 'the two VaR horizons are two entries: they share an analytic code, and a disclosure that deduped by code would show one and look plausible').toHaveAttribute('data-count', '2');

        // …and the page says what stopped them, by code rather than by sentence.
        const errors = lossSection(page).getByTestId('risk-asset-set-loss-errors');
        await expect(errors).toBeVisible();
        await expect(errors, 'both horizons failed the same gate, and the codes are deduplicated').toHaveAttribute('data-count', '1');
        await expect(errors.getByTestId('risk-asset-set-loss-error')).toHaveAttribute('data-code', INSUFFICIENT_HISTORY);

        // No *reasons*, and that is a fact about the backend rather than an
        // oversight: `service.py:_unavailable` builds a result with an error and no
        // warnings at all, so the verbatim-sentence list is legitimately empty here
        // where it was full in the exclusion case above. The two assertions that
        // precede this one are its presence barrier — without them "no reasons"
        // would also be true of a section that had not rendered.
        await expect(lossSection(page).getByTestId('risk-asset-set-loss-reasons')).toHaveCount(0);

        // AND THE WINDOW ITSELF, which is what makes the disclosure actionable: a
        // reader who can see "5 observations" can tell a short window from a broken
        // page without being told which it is.
        await expect(lossSection(page).getByTestId('risk-asset-set-loss-metadata')).toHaveAttribute('data-rows', '1');
        await expect(lossSection(page).getByTestId('risk-asset-set-loss-metadata-observations')).toHaveText(String(SHORT_OBSERVATIONS));

        // L3° is the other half of the same window: all three of its analytics need
        // 20, so it discloses two absences (the third, the comparison, was never
        // asked for without a benchmark) and draws no scatter — two dots being the
        // least that can show a relationship, and there are none.
        const paidHealth = paidSection(page).getByTestId('risk-asset-set-paid-health');
        await expect(paidHealth).toBeVisible();
        await expect(paidHealth).toHaveAttribute('data-count', '2');
        await expect(page.getByTestId('risk-asset-set-l3-risk-return'), 'a scatter with no measurable coordinate is not an empty chart, it is no chart').toHaveCount(0);
    });

    /**
     * (f) — the benchmark columns appear only when a benchmark applies.
     *
     * Both branches, because the absence is the ordinary state of this page and a
     * test that only proved the presence would leave the default unguarded.
     */
    test('L3° shows beta and correlation only when a benchmark applies', async ({page}) => {
        // The two navigations below (read the selection, then seed the shared
        // benchmark and come back) are the price of a module-scope store that
        // hydrates from a user-scoped key at mount.
        test.setTimeout(45_000);
        const requests = await installRiskMocks(page);
        await openAssetGlobalRisk(page);
        await ensureSelectionAtLeast(page, 2);
        await waitForRiskCatalog(page);
        await waitForLossTable(page);

        // ── The false branch, which is what this page shows by default ──────
        const paid = page.getByTestId('risk-asset-set-l3');
        await expect(paid).toHaveAttribute('data-benchmark', 'false');
        await expect(page.getByTestId('risk-asset-set-l3-no-benchmark'), 'two columns are missing and the reason is a choice made elsewhere; leaving that to be noticed reads as a limitation of the page').toBeVisible();
        await expect(paid.getByTestId('risk-asset-set-l3-beta')).toHaveCount(0);
        await expect(paid.getByTestId('risk-asset-set-l3-correlation')).toHaveCount(0);
        // The columns that do not depend on a benchmark are present throughout, so
        // "the beta cells are absent" cannot be satisfied by an unrendered table.
        const selected = await chipIds(page);
        await expect(paid.getByTestId('risk-asset-set-l3-volatility')).toHaveCount(selected.length);

        // ── The true branch ─────────────────────────────────────────────────
        // A benchmark that is not one of the measured, because
        // `validate_reference_is_not_a_subject` rejects a yardstick that is also a
        // subject and `AssetSetRiskPanel` withholds such a choice entirely. The
        // picker's filter already answers both halves, so the candidate is chosen
        // the way the product would choose it.
        const benchmarkId = await pickUnselectedAssetId(page);
        expect(selected, 'the reference may not also be one of the compared').not.toContain(benchmarkId);

        const userId = await currentUserId(page);
        // Seeded through `localStorage` under the store's own key rather than
        // through a picker, because this page deliberately has no benchmark picker:
        // the choice is shared with Dashboard and Broker Detail, and a second
        // control here would be a second way for the pages to disagree.
        // `addInitScript` runs before the app boots on the next navigation, so the
        // store hydrates with the value already in place and the first request
        // carries the comparison — no reload race to lose.
        //
        // ⚠️ BOTH SPELLINGS OF THE KEY, and this is not a shotgun. `hydrate()`
        // memoises on the key it last read, and the key it asks for is
        // `lf_${getClientSessionUserId() ?? 'anon'}_...` — so it depends on whether
        // `/auth/me` has resolved at the instant the panel first reads the store.
        // If it has not, the store reads the anon key, caches `null`, and nothing
        // re-reads it: `benchmarkId` is a `$derived` whose dependencies do not move
        // again, so the page would sit at `data-benchmark="false"` for the rest of
        // its life and this test would fail on a race rather than on a defect. Both
        // keys are spellings the app genuinely uses, and they are seeded with the
        // same value, so the reader's choice is the same whichever one it asks for.
        await page.addInitScript(
            ([scoped, anonymous, value]) => {
                try {
                    window.localStorage.setItem(scoped as string, value as string);
                    window.localStorage.setItem(anonymous as string, value as string);
                } catch {
                    /* storage disabled — the benchmark branch is then untestable and the assertions below will say so */
                }
            },
            [benchmarkStorageKey(userId), benchmarkStorageKey('anon'), String(benchmarkId)],
        );
        await openAssetGlobalRisk(page);
        await waitForRiskCatalog(page);
        await waitForLossTable(page);

        // The selection is restored from `localStorage` on this second visit, so it
        // is re-read rather than reused: the assertion has to be about the page in
        // front of it.
        const reselected = await chipIds(page);
        expect(reselected, 'the persisted selection must not have swallowed the benchmark, or the comparison is withheld by design').not.toContain(benchmarkId);

        // The comparison rides in the SAME request as the other four — not in one
        // of its own. `RiskAssetSetComparisonOutput` publishes the reference's own
        // volatility and expected return so a scatter can place it beside the
        // holdings, and that is only sound because the reference is prepared inside
        // the same request as the scope. Asked separately, the benchmark dot would
        // land on a chart whose other dots were measured over different dates.
        await expect.poll(() => levelRequestsFor(requests, reselected).some((request) => codesOf(request).has('asset_set_comparison')), {timeout: 20_000, message: 'the benchmark must have reached the wire'}).toBe(true);
        // Filtered by the comparison's *presence*, not merely by scope: the first
        // visit asked about this same selection without a benchmark, so its request
        // is in the capture too and a scope-only filter would count two.
        const withBenchmark = levelRequestsFor(requests, reselected).filter((request) => codesOf(request).has('asset_set_comparison'));
        expect(withBenchmark, 'the comparison must be asked for once, not once per section').toHaveLength(1);
        const codes = codesOf(withBenchmark[0]);
        for (const code of ASSET_SET_LEVEL_CODES) {
            expect([...codes], `${code} must share the request with the comparison — one preparation, one calendar`).toContain(code);
        }
        expect(withBenchmark[0].analytics.find((analytic) => analytic.analytic_code === 'asset_set_comparison')?.parameters?.comparison_asset_id, 'the request must carry the benchmark the shared store holds').toBe(benchmarkId);

        // …and the columns appear. `benchmarkApplies` is read from the *answer*,
        // not from the stored choice, so this also proves the comparison came back
        // `ok`: a requested benchmark that failed would leave two columns of
        // em-dashes looking like missing data rather than an inapplicable question.
        const paidAgain = page.getByTestId('risk-asset-set-l3');
        await expect(paidAgain).toHaveAttribute('data-benchmark', 'true', {timeout: 20_000});
        await expect(paidAgain.getByTestId('risk-asset-set-l3-beta')).toHaveCount(reselected.length);
        await expect(paidAgain.getByTestId('risk-asset-set-l3-correlation')).toHaveCount(reselected.length);
        await expect(page.getByTestId('risk-asset-set-l3-no-benchmark')).toHaveCount(0);

        // The reference gets its own dot and still no Capital Market Line: its role
        // is `benchmark`, which `capitalMarketLine()` does not search for. One dot
        // per asset plus one for the reference — any more would be an aggregate
        // nobody measured.
        await expectChartCanvas(page, 'risk-asset-set-l3-scatter', 20_000);
        await expect(page.getByTestId('risk-asset-set-l3-scatter')).toHaveAttribute('data-point-count', String(reselected.length + 1));

        // Nothing to restore: the benchmark and the selection both live in this
        // context's `localStorage`, which dies with the context, and no database
        // row was touched by any of the above.
    });
});
