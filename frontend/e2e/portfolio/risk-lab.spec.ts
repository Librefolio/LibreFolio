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
 *  3. The mass actions act on the candidates the eligibility engine admits —
 *     never past them — and are reversible.
 *  4. A filter never eats the option that applies it.
 *  5. The pair lists name the redundant pair and the offsetting one.
 *  6. Reordering the matrix loses nothing.
 *
 * Two properties of this file worth knowing before editing it:
 *
 * - **It writes nothing to the database.** Every risk call is stubbed — the
 *   eligibility engine's included (see `answerEligibility`) — and so is every
 *   sync the page's modal can start: a real run would write prices and reach
 *   external providers. The page's live-price poll is held unanswered for the
 *   same reason, since every answered poll writes today's prices (see
 *   `holdLivePricePoll`). The only state it mutates is the selection, which
 *   lives in this browser context's `localStorage` and dies with it. There is
 *   nothing to clean up, and nothing here can disturb a neighbouring spec's rows.
 * - **No selector is positional.** Pair testids are keyed by asset-id pair,
 *   because the matrix reorders itself by similarity; chips, rows of the "+"
 *   and filter options are found by what they are, not by where they sit.
 */

import {expect, test, type Locator, type Page, type Request} from '../fixtures/playwright';

import {login, navigateTo} from '../fixtures/auth-helpers';
import {expectChartCanvas} from '../fixtures/charts';
import {t as catalogueText} from '../fixtures/i18n-data';
import {TEST_USER} from '../fixtures/test-users';
import {schemas} from '../../src/lib/api/generated';
import {OVERFLOW_MARQUEE_SELECTOR} from '../../src/lib/actions/scrollOnOverflow';

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
 * Any figure shaped like money in the four shipped locales: at least one
 * thousands group, then two decimals — `12,345.67`, `12.345,67`, `12 345,67`.
 *
 * {@link MONEY_PATTERN} knows the bait, and the bait rides only the replay. The
 * broker preset brings a different payload in — the portfolio report — whose
 * amounts are real and whatever the seed makes them, so the net for that path
 * has to recognise the *shape* of an amount rather than one magnitude. The group
 * plus the two decimals is what keeps it off every legitimate number on this
 * page: percentages and coefficients carry no group, counts carry no decimals.
 */
const GROUPED_AMOUNT_PATTERN = /\d{1,3}(?:[.,\u00a0\u202f\u2009 ]\d{3})+[.,]\d{2}(?!\d)/;

/**
 * What a masked amount reads under global privacy: `PRIVACY_PLACEHOLDER` of
 * `utils/privacy/maskable.ts`, copied because the spec cannot import a module
 * that reads the privacy store.
 *
 * Only money formatters produce it — `formatPercent` masks nothing — so on this
 * page, where no amount may exist, the placeholder is an amount that reached the
 * renderer with its number hidden.
 */
const MASKED_AMOUNT = '•••';

/**
 * A figure with a currency beside it, in either order, masked or in clear:
 * `€12,345.67`, `12.345,67 €`, `−€•••`, `••• €`, `EUR •••`.
 *
 * Symbols count beside a digit or the mask; a code counts only beside the mask,
 * because a code beside a digit is also how asset names read ("… EUR 2-10Y …").
 * A currency on its own is not matched: a bare code, or `formatCurrencyCodeHtml`'s
 * `€ 🇪🇺 EUR`, names a currency and quotes no sum. "Beside" means on the same line:
 * the separator is horizontal space only, or a figure ending one line would pair
 * with a currency label starting the next.
 */
const CURRENCY_BESIDE_FIGURE = /[€$£¥][ \t\u00a0\u202f\u2009]*[-−+]?[ \t\u00a0\u202f\u2009]*[\d•]|[\d•][ \t\u00a0\u202f\u2009]*[€$£¥]|\b[A-Z]{3}[ \t\u00a0\u202f\u2009]*[-−+]?[ \t\u00a0\u202f\u2009]*•|•[ \t\u00a0\u202f\u2009]*[A-Z]{3}\b/;

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

/**
 * The base of the key the selection is remembered under — not the key itself.
 *
 * Since F-2 the memory is per user (`lf_<id>_` + this, see `selectionStorageKey`),
 * and this string on its own is only the pre-scoping key, which the module
 * removes on every read and never adopts. Clearing it alone clears nothing the
 * page reads.
 */
const SELECTION_STORAGE_BASE_KEY = 'assetGlobal.riskSelection.v1';

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
    /**
     * The one-day VaR the sort test plants instead (`zigzagBadDay`), per *rank* rather than
     * per index: a gentler ramp of its own, so that ranks run as far as the selection does
     * without leaving the band a real instrument occupies as fast as `badDayVar` would.
     */
    zigzagBadDayVar: (rank: number) => 0.012 + rank * 0.0015,
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
    /**
     * The average annual return the L3° sort test plants instead (`zigzagExpectedReturn`), per *rank*
     * rather than per index: it starts below zero and crosses it by the third rank, so any selection
     * the test can stand on draws both signs, and a sort by magnitude or by the printed text lands in
     * an order a sort by value does not.
     */
    zigzagExpectedReturn: (rank: number) => -0.021 + rank * 0.012,
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
 * The warning `_assets_excluded_warnings` (`service.py`) sends for the assets a request
 * could not prepare, one per reason.
 *
 * Each carries the catalogue key of its reason, and the backend's English `message`
 * only as the fallback `warningSentence` shows when the key cannot be worded. The
 * sentence is the same for every reason, and copied verbatim, because a test proves
 * the key was worded by showing that *this* string is not the one on screen.
 */
const EXCLUDED_WARNING_CODE = 'assets_excluded';
const EXCLUDED_WARNING_MESSAGE = 'One or more scope assets were excluded from risk calculations.';

/**
 * The key of each exclusion reason, as `_assets_excluded_warnings` writes them out
 * branch by branch. Any other reason — `insufficient_history`, the default the
 * prepared set falls back to — takes the last key.
 */
const EXCLUDED_WARNING_KEYS: Readonly<Record<string, string>> = {
    missing_price: 'risk.warnings.assets_excluded_missing_price',
    missing_fx: 'risk.warnings.assets_excluded_missing_fx',
    invalid_currency: 'risk.warnings.assets_excluded_invalid_currency',
};
const EXCLUDED_WARNING_OTHER_KEY = 'risk.warnings.assets_excluded_insufficient_history';

/**
 * How the backend names an asset it has no display name for (`_with_warning_asset_names`:
 * `names.get(asset_id, f"#{asset_id}")`).
 *
 * The stub knows no names, so it names every asset this way. That is also what makes
 * the name a proof: it reaches the screen only through the formatter, never through
 * the English fallback.
 */
function unnamedAsset(assetId: number): string {
    return `#${assetId}`;
}

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

/** The five codes the laboratory's two comparison levels put on the wire between them — each level its own share, in a request of its own. */
const ASSET_SET_LEVEL_CODES = ['asset_set_kpi', 'asset_set_var', 'asset_set_drawdown', 'asset_set_risk_return', 'asset_set_comparison'] as const;

/**
 * L1°'s share (`risk-asset-set-loss`): the bad day and the bad month — two instances of
 * `asset_set_var` — and the drawdown. Never `asset_set_comparison`, whatever the benchmark: the
 * engine prepares a request's comparison asset together with its scope (`risk/service.py:183-196`),
 * so a benchmark riding with L1° would move L1°'s window. The developer saw L1° turn «Partial»
 * because of one, and split the levels' request in two (02/10/2026).
 */
const LOSS_LEVEL_CODES = ['asset_set_var', 'asset_set_drawdown'] as const;

/** L3°'s share (`risk-asset-set-paid`); `asset_set_comparison` joins it only when a benchmark applies. */
const PAID_LEVEL_CODES = ['asset_set_kpi', 'asset_set_risk_return', 'asset_set_comparison'] as const;

/** The L3° codes that ride on every load: all of its share but the comparison. */
const PAID_UNCONDITIONAL_CODES = PAID_LEVEL_CODES.filter((code) => code !== 'asset_set_comparison');

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
 * The first two knobs reproduce a state the **real** backend reaches on its own;
 * neither invents one. That distinction is the whole reason they are options rather
 * than separate hand-written payloads: a stub that can only produce the happy path
 * makes the unhappy paths unreachable, and a stub that produces an impossible
 * one tests a page against a world that does not exist. The two after them are not
 * states at all: the same ordinary answer, with one column's figures in another order.
 * The last one plants what the backend attaches to an asset set's reports since D373:
 * the data-quality banner's issues.
 */
interface RiskStubOptions {
    /**
     * Answer for one fewer asset than the scope asked about.
     *
     * The backend does this whenever a requested asset has no usable series: it
     * is dropped from the prepared set, every analytic in the request then answers
     * about the survivors, the result's status becomes `partial` rather than `ok`,
     * and the same `assets_excluded` warnings — one per reason — ride on all of them.
     * Reproduced in full here — including on `correlation`, because the exclusion is
     * a property of the *prepared series set* and not of any one analytic, so hiding
     * it from the matrix would be a state the backend cannot produce.
     */
    dropLastAsset?: boolean;
    /**
     * A window shorter than four of the five analytics can measure.
     *
     * `asset_set_drawdown` declares `min_observations = 2` where the other four
     * declare 20, so the gate at `service.py:230-243` genuinely returns one `ok`
     * beside four `unavailable` — same selection, same period, same window, in
     * whichever level's request each of the five rides.
     */
    shortWindow?: boolean;
    /**
     * Plant the one-day VaR as a zig-zag in id order instead of the ramp.
     *
     * For the test that sorts L1°'s bad day. The ramp climbs with the request's
     * ascending ids, and the selection often opens in that same order, so a column
     * sorted by the ramp comes out in the selection's order or in its reverse — and
     * "sorted" and "cleared" could then draw the same rows. {@link zigzagRank} gives
     * every position a distinct rank, even positions below odd ones: a straight line
     * in value, a zig-zag in id order. The month keeps the ramp.
     */
    zigzagBadDay?: boolean;
    /**
     * Plant L3°'s average annual return as the same zig-zag, crossing zero.
     *
     * For the test that sorts L3°'s return column, for L1°'s reason — the ramp would sort into the
     * selection's order or its reverse — and one of its own: the column sorts by the value with
     * its sign, so the planted figures must hold both signs, and a loss of 2.1% must sort below a
     * gain of 0.3% although it is larger. The benchmark's active return follows the same figure.
     */
    zigzagExpectedReturn?: boolean;
    /**
     * Data-quality issues to plant in the answers to one section's requests (decision B).
     *
     * Since D373 `service.py::_with_asset_set_quality_issues` gives every result of an asset-set
     * request that carries a report the banner's issues, one per category. So what this returns
     * rides on every result of the request {@link labSectionsOf} attributes to `section`, built from
     * that request — its own scope, never the page's. The controllers read a report where they read
     * any (`allResults`): a base wave's `correlation`, the one asset-set analytic they know, and
     * their on-demand answers, the replay's among them.
     */
    qualityIssues?: (section: LabSection, request: RiskRequest) => readonly QualityIssue[];
}

/** A data-quality issue as the API sends it, read off the generated contract the client validates every answer with. */
type QualityIssue = ReturnType<typeof schemas.DataQualityIssue.parse>;

/**
 * The lab's sections, as their requests are told apart on the wire: the correlation section, L1°,
 * L3°, and the replay's own runs. The replay section's *base wave* is not a fifth: it asks the
 * correlation section's question, `[correlation]`, and `queryRisk` serves the two from one flight
 * (see {@link assetSetLevelRequests}).
 */
type LabSection = 'correlation' | 'loss' | 'paid' | 'replay';

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

/** One asset the request could not prepare, and why — the shape of `metadata.excluded_assets`. */
interface ExcludedAsset {
    asset_id: number;
    reason: string;
}

/**
 * The assets the stub could not prepare, with the reason `_build_context` gives:
 * `insufficient_history`, the default the prepared set falls back to.
 *
 * One source for the two places the backend reports them — the metadata's
 * `excluded_assets` and the warnings built from it — so they cannot disagree.
 */
function excludedAssets(request: RiskRequest, options: RiskStubOptions): ExcludedAsset[] {
    return preparedAssetIds(request, options).excluded.map((assetId) => ({asset_id: assetId, reason: INSUFFICIENT_HISTORY}));
}

/**
 * The `assets_excluded` warnings as the response carries them, or none.
 *
 * Built the way `_assets_excluded_warnings` builds them: one warning per reason, in
 * reason order, with that reason's key and `details: {asset_ids, reason}`. The
 * `names` and `count` in `message_params` are what `_with_warning_asset_names` adds
 * before the response leaves, and what the catalogue sentences interpolate. Without
 * them the key cannot be worded, and the English fallback shows instead.
 */
function exclusionWarnings(excluded: readonly ExcludedAsset[]) {
    const byReason = new Map<string, number[]>();
    for (const {asset_id, reason} of excluded) byReason.set(reason, [...(byReason.get(reason) ?? []), asset_id]);
    return [...byReason.entries()]
        .sort(([left], [right]) => (left < right ? -1 : left > right ? 1 : 0))
        .map(([reason, assetIds]) => ({
            code: EXCLUDED_WARNING_CODE,
            message: EXCLUDED_WARNING_MESSAGE,
            details: {asset_ids: assetIds, reason},
            degrades_result: true,
            message_i18n_key: EXCLUDED_WARNING_KEYS[reason] ?? EXCLUDED_WARNING_OTHER_KEY,
            message_params: {names: assetIds.map(unnamedAsset).join(', '), count: assetIds.length},
        }));
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
        // the reason the prepared set gave — the same list the warnings are built
        // from (`excludedAssets`).
        excluded_assets: isHistoricalReplay(analytic) ? [] : excludedAssets(request, options),
        algorithm_version: MOCK_ALGORITHM_VERSION,
        computed_at: '2026-01-31T12:00:00Z',
        // `service.py:860` copies the plugin's audit into the metadata of every
        // replay, and `L4Replay` lists what the replay left out from it
        // (`risk-replay-excluded`) — the presence barrier the no-money tests stand
        // on since D372 retired the one-line audit. Omitting it here would leave
        // that barrier unsatisfiable — a barrier that can never turn green is not
        // stricter, it is broken.
        ...(isHistoricalReplay(analytic) ? {historical_replay_audit: replayAudit(request)} : {}),
    };
}

/**
 * The data-quality report every result carries: clean, unless a test plants issues in it
 * ({@link RiskStubOptions.qualityIssues}). A report with issues does not call itself `ok`: a missing
 * price leaves it `partial`, a stale one `carried_forward`. Nothing on this page reads the status;
 * it is set so the report stays one the backend could send.
 */
function dataQuality(issues: readonly QualityIssue[] = []) {
    return {
        issues: [...issues],
        carried_forward_price_points: 0,
        carried_forward_fx_points: 0,
        carried_forward_price_asset_ids: [],
        carried_forward_fx_pairs: [],
        data_quality_status: issues.length === 0 ? 'ok' : issues.some((issue) => issue.severity === 'error') ? 'partial' : 'carried_forward',
    };
}

/** What {@link RiskStubOptions.qualityIssues} plants in the answers to `request`: for each section that asked it, in page order. */
function plantedQualityIssues(request: RiskRequest, options: RiskStubOptions): QualityIssue[] {
    const plant = options.qualityIssues;
    if (plant === undefined) return [];
    return labSectionsOf(request).flatMap((section) => [...plant(section, request)]);
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

/**
 * The rank {@link RiskStubOptions.zigzagBadDay} gives the asset at `position` of `count`.
 *
 * Even positions take the low ranks in order, odd positions the ranks above them, so
 * every rank from 0 to `count - 1` is used exactly once — no two rows tie — and for
 * three or more assets the order by value is neither the order of the ids nor its
 * reverse: `[0, 1, 2]` ranks as `[0, 2, 1]`.
 */
function zigzagRank(position: number, count: number): number {
    return position % 2 === 0 ? position / 2 : Math.ceil(count / 2) + (position - 1) / 2;
}

/**
 * The average annual return the stub answers for the asset at `position` of the `count` it could
 * prepare: the ramp, or — with {@link RiskStubOptions.zigzagExpectedReturn} — the zig-zag that
 * crosses zero. One function for the two outputs that carry it, so the risk/return point and the
 * benchmark's active return cannot disagree about an asset.
 */
function plantedExpectedReturn(position: number, count: number, options: RiskStubOptions): number {
    return options.zigzagExpectedReturn ? INVENTED.zigzagExpectedReturn(zigzagRank(position, count)) : INVENTED.expectedReturn(variant(position));
}

/** Per-asset VaR/CVaR at one horizon. Positive magnitudes, CVaR ≥ VaR. */
function assetSetVarOutput(request: RiskRequest, analytic: RiskAnalyticRequest, options: RiskStubOptions) {
    const {covered} = preparedAssetIds(request, options);
    const horizonDays = Number(analytic.parameters?.horizon_days ?? 1);
    const horizonObservations = Math.max(1, Math.round((horizonDays * 252) / 365));
    const horizonFactor = horizonDays > 1 ? INVENTED.monthFactor : 1;
    return {
        kind: 'var_cvar_set',
        confidence_level: Number(analytic.parameters?.confidence_level ?? 0.95),
        horizon_days: horizonDays,
        horizon_observations: horizonObservations,
        // Compounding to a multi-day horizon consumes observations, so the count
        // the tail was estimated from is `horizon_observations - 1` fewer than the
        // window's — the backend says so in `RiskAssetSetVarCvarOutput`'s
        // docstring, and a flat copy of `n_observations` here would contradict it.
        observations: Math.max(1, observationCount(options) - (horizonObservations - 1)),
        items: covered.map((assetId, index) => {
            const row = variant(index);
            const valueAtRisk = options.zigzagBadDay && horizonDays === 1 ? INVENTED.zigzagBadDayVar(zigzagRank(index, covered.length)) : INVENTED.badDayVar(row) * horizonFactor;
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
            expected_annual_return: plantedExpectedReturn(index, covered.length, options),
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
 *
 * And it fires whenever the benchmark is one of the selected (D371, 02/10/2026):
 * the lab applies such a choice, and `asset_set_comparison` 1.1.0 keeps the
 * reference in the selection, measures it like the others — so `asset_set_kpi`
 * and `asset_set_risk_return` still give it a row, here as in the backend — and
 * skips it in `items`, since a beta and a correlation with itself would be 1 by
 * construction. Its row's two blanks are the page's to explain. One
 * simplification stays: a selected reference keeps the invented benchmark's
 * coordinates below, where the backend would report its row's own (one series,
 * one calendar); no case here reads where a dot lands, only how many are drawn.
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
                const activeReturn = plantedExpectedReturn(index, covered.length, options) - INVENTED.benchmarkExpectedReturn;
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
 * this test. And the holding the replay left out ({@link replayLeftOutAssetId})
 * has no bar: on an unweighted scope it is omitted from the replay, not carried.
 */
function replayOutput(request: RiskRequest) {
    const leftOut = replayLeftOutAssetId(request);
    const assetIds = replayAssetIds(request).filter((assetId) => assetId !== leftOut);
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

/**
 * The holding the stubbed replay leaves out: the last of the scope, which the client
 * canonicalises ascending — read off the request, never assumed.
 *
 * Since 24/09 the engine leaves out, on its own, every holding whose quotes do not
 * cover the window, and on an unweighted scope it is *omitted* from the replay, with
 * no weight (`stress.py::_historical`). Leaving one out of every replay is what gives
 * the no-money tests their presence barrier since D372 retired the one-line audit:
 * `risk-replay-excluded` is drawn from `historical_replay_audit` alone, which no other
 * analytic carries — and it is one more place a weight, a share of a portfolio that
 * does not exist, could surface. A selection of one is left whole: leaving out its
 * only holding would leave nothing to replay.
 */
function replayLeftOutAssetId(request: RiskRequest): number | null {
    const assetIds = replayAssetIds(request);
    return assetIds.length >= 2 ? assetIds[assetIds.length - 1] : null;
}

/** The audit `stress.py` attaches to the replay: the holding it left out, omitted and unweighted, and a total pinned at 0.0 on an unweighted scope. */
function replayAudit(request: RiskRequest) {
    const leftOut = replayLeftOutAssetId(request);
    const excluded = leftOut === null ? [] : [{asset_id: leftOut, reason: 'no_prices_in_window', weight: null, treatment: 'omitted_from_replay'}];
    return {
        proxy_count: 0,
        proxy_assets: [],
        excluded_count: excluded.length,
        excluded_assets: excluded,
        excluded_weight_total: 0,
        missing_history_policy: 'manual_proxy_or_exclude',
        composition_policy: 'current_buy_and_hold',
        proxy_series_usage: 'returns_only',
    };
}

/**
 * The exclusion warning `_replay_exclusion_warning` sends for that holding, one per reason,
 * named the way `service.py` names an asset it has no display name for. The section leaves
 * it to the block since D372; nothing here reads it, it is sent because the engine sends it.
 */
function replayExclusionWarnings(request: RiskRequest) {
    const leftOut = replayLeftOutAssetId(request);
    if (leftOut === null) return [];
    return [
        {
            code: 'historical_replay_assets_excluded',
            message: 'Historical replay excluded assets with no prices in the replay window.',
            details: {asset_ids: [leftOut], treatment: 'omitted_from_replay', reason: 'no_prices_in_window'},
            degrades_result: true,
            message_i18n_key: 'risk.warnings.historical_replay_excluded_no_prices',
            message_params: {treatment: 'omitted_from_replay', names: unnamedAsset(leftOut), count: 1},
        },
    ];
}

/**
 * The presence barrier of the no-money tests, on the replay: what it left out is listed,
 * as a selection must list it — omitted, with no total weight and no weight per holding,
 * since a weight here would be a share of a portfolio the reader never described.
 */
async function expectReplayLeftOutWithoutWeight(page: Page): Promise<void> {
    const leftOut = page.getByTestId('risk-replay-excluded');
    await expect(leftOut, 'the replay answer never listed what it left out: the answer is not on screen, or is not a replay').toBeVisible({timeout: 20_000});
    await expect(leftOut).toHaveAttribute('data-treatment', 'omitted_from_replay');
    await expect(leftOut, 'a total weight was published for a selection, which carries no weights').not.toHaveAttribute('data-weight-total');
    await expect(leftOut.getByTestId('risk-replay-excluded-asset')).toHaveCount(1);
    await expect(leftOut.locator('[data-testid="risk-replay-excluded-asset"][data-weight]'), 'a holding of a selection was listed with a weight').toHaveCount(0);
}

function resultFor(request: RiskRequest, analytic: RiskAnalyticRequest, options: RiskStubOptions = {}): Record<string, unknown> {
    const {excluded} = preparedAssetIds(request, options);
    const base = {
        instance_id: analytic.instance_id,
        analytic_code: analytic.analytic_code,
        metadata: metadata(request, analytic, options),
        data_quality: dataQuality(plantedQualityIssues(request, options)),
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
    // becomes `partial` and the same `assets_excluded` warnings, one per reason,
    // ride on every result. Both halves matter — `degradedResults` reads the
    // status, `resultReasons` reads the sentence — and a stub that sent one
    // without the other would leave whichever half it omitted untested.
    const degraded = excluded.length > 0;
    const answered = {
        ...base,
        status: degraded ? 'partial' : 'ok',
        warnings: exclusionWarnings(excludedAssets(request, options)),
    };

    if (analytic.analytic_code === 'correlation') return {...answered, output: correlationOutput(request, options)};
    if (isAssetSetLevel(analytic)) return {...answered, output: assetSetLevelOutput(request, analytic, options)};
    // The replay is prepared by itself (`_prepare_historical_replay` sets
    // `excluded_assets=()`), so it never degrades with the historical wave; what
    // its own window leaves out degrades it instead — `partial`, with the
    // exclusion warning beside the audit that lists it.
    if (isHistoricalReplay(analytic)) {
        const warnings = replayExclusionWarnings(request);
        return {...base, status: warnings.length > 0 ? 'partial' : 'ok', warnings, output: replayOutput(request)};
    }

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

/**
 * Hold the page's live-price poll, unanswered, for the whole test.
 *
 * When the window ends today, `+page.svelte` polls `POST /assets/prices/current`:
 * on load, again whenever its asset list is reassigned, and every 30 s after. Each
 * answered call is a portfolio mutation twice over. The backend writes today's
 * prices into the shared database, and `zodios-client`'s response interceptor
 * calls `notifyPortfolioMutation`, which drops the report and risk caches and
 * discards every answer still in flight. It is a background actor these tests do
 * not control, racing the very requests they measure.
 *
 * Held, never answered, because nothing else is inert: a stubbed answer, even an
 * empty one, still passes through that interceptor and still invalidates. An
 * unanswered call does nothing at all. `fetchLivePrices` awaits it; after axios's
 * 30 s timeout it catches the error and logs one non-critical warning, with no
 * toast and no busy flag. The handler calls no route method, so nothing can
 * throw when the context closes, and Playwright waits for a running handler only
 * when explicitly told to (`unrouteAll({behavior: 'wait'})`, which nothing here
 * calls). Nothing here unroutes at teardown either: removing a route releases
 * what it holds, and in a run that did, the held poll reached the backend and
 * wrote today's prices.
 *
 * 🔴 This isolates the tests; it fixes nothing. The race exposed two product
 * defects, and this hold repairs neither: a discarded report read as "no
 * holdings" by the broker preset (repaired separately, in the panel), and a
 * discarded replay read as "no answer" by `runGuarded` (still open). Outside this
 * file the poll still writes on every visit. All this does is stop these tests
 * from depending on a race nobody controls.
 */
async function holdLivePricePoll(page: Page): Promise<void> {
    await page.route(/\/api\/v1\/assets\/prices\/current(?:\?|$)/, () => {
        // Deliberately neither fulfilled nor continued: see above.
    });
}

/**
 * The engine's thresholds, copied rather than chosen: `RISK_MIN_OBSERVATIONS` and
 * `STALE_PRICE_THRESHOLD_DAYS` (`data_quality_thresholds.py`), which
 * `RiskService.asset_eligibility` sends with every answer. The lab quotes them in
 * its sentences; nothing here asserts on them.
 */
const ENGINE_MIN_QUOTES = 20;
const ENGINE_STALE_DAYS = 7;

type EligibilityLevel = 'eligible' | 'warning' | 'ineligible';
type EligibilityReason = 'no_prices' | 'too_few_quotes' | 'missing_fx' | 'starts_late' | 'stale_at_end';

/** One verdict of the engine: a level, and the codes behind it. */
interface Verdict {
    level: EligibilityLevel;
    reasons: readonly EligibilityReason[];
}

/** Admitted, with nothing to say: the answer every test gets unless eligibility is its subject. */
const ELIGIBLE: Verdict = {level: 'eligible', reasons: []};

/** Ruled out for the period: not one quote in it, the first reason the engine knows. */
const NO_PRICES: Verdict = {level: 'ineligible', reasons: ['no_prices']};

/** One question the page put to the engine, as it put it. */
interface EligibilityCall {
    assetIds: number[];
    dateRange: {start: string; end: string | null};
    targetCurrency: string;
}

/**
 * Answer `POST /risk/eligibility` with this test's verdicts, and keep what the page asked.
 *
 * 🔴 Why it is answered here and not left to the lane. The lab asks the engine about
 * its whole catalogue and leaves what it rules out out of every request
 * (`analysedIds`), so a verdict decides what each section is asked about — while the
 * chips still show every selected asset. Let through, the call reaches the lane's
 * real engine, whose verdicts follow the seed's price history and today's date: on
 * the populated lane of 24/09 it admitted 9 assets and parked one of the user's eight
 * holdings (`data-total="9"`, `data-parked="1"`), and every test comparing chips with
 * sections went green or red by when that answer happened to land.
 *
 * Answered, never failed: a failed call leaves no verdict, which makes everything
 * selectable too, but it raises `risk-eligibility-failed` — a state these tests would
 * pass through without saying so. `waitForSelection` refuses it.
 *
 * Every requested id gets a verdict, deduplicated and in request order, the way the
 * engine answers. The body goes through the generated schema because the client
 * validates every response (`validate: 'response'`): a stub that drifted from the
 * contract would otherwise surface as that same "failed" state, with nothing
 * pointing here.
 *
 * Registered after `installRiskMocks`, a call with its own verdicts wins over the
 * default one: Playwright runs the most recently registered matching handler first.
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
                    quotes_in_period: quoted ? AMPLE_OBSERVATIONS : 0,
                };
            }),
            min_quotes: ENGINE_MIN_QUOTES,
            stale_days: ENGINE_STALE_DAYS,
        });
        await route.fulfill({status: 200, contentType: 'application/json', body: JSON.stringify(body)});
    });
    return calls;
}

/**
 * The page's asset list, read off the last question it put to the engine.
 *
 * The lab asks about its whole catalogue (`catalogueKey`), so this is the list the
 * page itself holds — the one the holdings command restricts its answer to — rather
 * than a probe taken beside it that a neighbour could move.
 */
function pageCatalogue(calls: readonly EligibilityCall[]): Set<number> {
    const last = calls[calls.length - 1];
    if (!last) throw new Error('The page never asked the eligibility engine, so its asset list is unknown to this test.');
    return new Set(last.assetIds);
}

/**
 * ─── The period in which every selected asset has prices ───────────────────
 *
 * The panel asks the engine twice: about the whole catalogue (the chips' verdicts)
 * and about the selection alone. When the selection's answer carries a
 * `suggested_range`, and the suggestion brings back at least one selected asset the
 * requested period leaves out or warns about, a strip at the top of the controls
 * offers that period (`risk-fit-period-banner`), and its button hands it to the
 * page's toolbar.
 */

/** A span of calendar days, both ends included: `common_range` and `suggested_range` as the panel reads them. */
interface DayRange {
    start: string;
    end: string;
}

/** A plain day moved by `days`, counted in UTC so no timezone moves it. */
function shiftDay(isoDay: string, days: number): string {
    const [year, month, day] = isoDay.split('-').map(Number);
    return new Date(Date.UTC(year, month - 1, day + days)).toISOString().slice(0, 10);
}

/** The calendar days from one plain day to another, negative when `to` comes first: {@link shiftDay}'s inverse, counted in UTC the same way. */
function daysBetween(from: string, to: string): number {
    const utc = (isoDay: string) => {
        const [year, month, day] = isoDay.split('-').map(Number);
        return Date.UTC(year, month - 1, day);
    };
    return Math.round((utc(to) - utc(from)) / 86_400_000);
}

/**
 * How the scripted engine answers a period it has not suggested itself.
 *
 *  - `plain`: every asset eligible and no range, like {@link answerEligibility}.
 *  - `late`: the `late` assets were first quoted 90 days into the period, so they
 *    start late (a warning); every quote ends the day before the period does. The
 *    engine suggests what the backend's schema describes: the day after the latest
 *    first quote, to the earliest last quote.
 *  - `trimmedEnd`: every asset quoted from before the period to the day before its
 *    end — all eligible, since one day is not stale — and the engine still suggests
 *    the period trimmed at that end ("the requested period trimmed to the common
 *    span"). A suggestion that brings nobody back.
 *
 * A period the engine has suggested is answered as the backend would: everyone
 * eligible, no suggestion. That is what makes following the offer end it.
 */
type EngineMode = {kind: 'plain'} | {kind: 'late'; late: ReadonlySet<number>} | {kind: 'trimmedEnd'};

/** One question the page put to the scripted engine, and what it said about it. */
interface EngineExchange {
    assetIds: number[];
    period: DayRange;
    /** The period asked was one this engine had suggested. */
    fitted: boolean;
    suggested: DayRange | null;
    /** The ids this answer did not call eligible. */
    notEligible: number[];
}

function rangeKey(range: DayRange): string {
    return `${range.start}/${range.end}`;
}

/**
 * Answer `POST /risk/eligibility` for exactly the ids each request asks about, as
 * `mode` says, and keep every exchange.
 *
 * Registered after `installRiskMocks`, so it wins over {@link answerEligibility}. The
 * suggestion is a function of the period asked, never of the test's clock, so
 * whoever reads the log can tell which answer went with which period. The body
 * passes the generated schema before it leaves, because the client validates every
 * response.
 */
async function scriptEligibility(page: Page): Promise<{exchanges: EngineExchange[]; setMode: (mode: EngineMode) => void}> {
    const exchanges: EngineExchange[] = [];
    const offered = new Set<string>();
    let mode: EngineMode = {kind: 'plain'};
    await page.route('**/api/v1/risk/eligibility', async (route) => {
        const sent = (route.request().postDataJSON() ?? {}) as {asset_ids?: number[]; date_range?: {start?: string; end?: string | null}};
        const assetIds = [...new Set(sent.asset_ids ?? [])];
        const start = sent.date_range?.start ?? '';
        const period: DayRange = {start, end: sent.date_range?.end ?? start};
        const fitted = offered.has(rangeKey(period));
        const quote = (assetId: number, overrides: Record<string, unknown> = {}) => ({
            asset_id: assetId,
            level: 'eligible',
            reasons: [],
            first_quote: shiftDay(period.start, -30),
            last_quote: period.end,
            quotes_in_period: AMPLE_OBSERVATIONS,
            ...overrides,
        });

        let items = assetIds.map((assetId) => quote(assetId));
        let commonRange: DayRange | null = null;
        let suggested: DayRange | null = null;
        if (fitted) {
            commonRange = {start: shiftDay(period.start, -1), end: period.end};
        } else if (mode.kind === 'late') {
            const late = mode.late;
            const firstQuote = shiftDay(period.start, 90);
            const lastQuote = shiftDay(period.end, -1);
            items = assetIds.map((assetId) => (late.has(assetId) ? quote(assetId, {level: 'warning', reasons: ['starts_late'], first_quote: firstQuote, last_quote: lastQuote, quotes_in_period: 40}) : quote(assetId, {last_quote: lastQuote})));
            commonRange = {start: firstQuote, end: lastQuote};
            suggested = {start: shiftDay(firstQuote, 1), end: lastQuote};
        } else if (mode.kind === 'trimmedEnd') {
            const lastQuote = shiftDay(period.end, -1);
            items = assetIds.map((assetId) => quote(assetId, {last_quote: lastQuote}));
            commonRange = {start: shiftDay(period.start, -30), end: lastQuote};
            suggested = {start: period.start, end: lastQuote};
        }
        if (suggested) offered.add(rangeKey(suggested));

        const body = schemas.RiskEligibilityResponse.parse({
            items,
            min_quotes: ENGINE_MIN_QUOTES,
            stale_days: ENGINE_STALE_DAYS,
            ...(commonRange ? {common_range: commonRange} : {}),
            ...(suggested ? {suggested_range: suggested} : {}),
        });
        await route.fulfill({status: 200, contentType: 'application/json', body: JSON.stringify(body)});
        exchanges.push({assetIds, period, fitted, suggested, notEligible: items.filter((item) => item.level !== 'eligible').map((item) => item.asset_id)});
    });
    return {
        exchanges,
        setMode: (next) => {
            mode = next;
        },
    };
}

/** The last exchange about exactly `assetIds` for `period`, if the page has asked it. */
function exchangeFor(exchanges: readonly EngineExchange[], assetIds: readonly number[], period: DayRange): EngineExchange | undefined {
    return [...exchanges].reverse().find((exchange) => scopeKey(exchange.assetIds) === scopeKey(assetIds) && rangeKey(exchange.period) === rangeKey(period));
}

/** The period the page's URL carries (`gotoDateRange` writes it as ISO days), or `null` before it carries one. */
function urlPeriod(page: Page): DayRange | null {
    const url = new URL(page.url());
    const start = url.searchParams.get('start');
    const end = url.searchParams.get('end');
    return start && end ? {start, end} : null;
}

/**
 * Press a preset of the toolbar's period picker, and end on its period being the
 * page's: the badge lit and the URL carrying the dates. Returns that period.
 *
 * The badge must not be lit before: pressing a preset already in force asks the
 * engine nothing new, and every exchange a caller then waits for would never come.
 */
async function pressPeriodPreset(page: Page, key: string): Promise<DayRange> {
    const badge = page.getByTestId(`date-preset-${key}`);
    await expect(badge).toBeVisible({timeout: 10_000});
    await expect(badge, `the ${key} preset is already in force: pressing it would ask the engine nothing new`).toHaveAttribute('data-active', 'false');
    const before = urlPeriod(page);
    await badge.click();
    await expect(badge).toHaveAttribute('data-active', 'true');
    await expect.poll(() => urlPeriod(page), {message: `the ${key} preset did not move the page's period`}).not.toEqual(before);
    const period = urlPeriod(page);
    if (!period) throw new Error(`the ${key} preset left the URL without a period`);
    return period;
}

/**
 * Stub the risk endpoints — the eligibility engine admitting everything — hold the
 * live-price poll, and hand back the analytics requests the page actually made.
 */
async function installRiskMocks(page: Page, options: RiskStubOptions = {}): Promise<RiskRequest[]> {
    const requests: RiskRequest[] = [];

    await holdLivePricePoll(page);
    await answerEligibility(page);

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
 * The requests carrying any of the five per-asset codes — both levels' requests.
 *
 * Deliberately *not* "every asset-set historical request": the laboratory puts
 * more than one of those on the wire and always has. `AssetSetCorrelationSection`
 * and `AssetSetReplaySection` each build their own controller without
 * `includeAssetSetLevels`, so their wave is `[correlation]` — canonically equal
 * to each other, hence one network call between them — while the comparison
 * levels ask for `correlation` plus their per-asset codes, differently-shaped
 * requests again. Counting all asset-set historical requests and expecting one
 * would assert something false about the page; what has to be true is that
 * **each level's codes travel together** — L1°'s in one request, L3°'s in
 * another, since the developer's split of 02/10/2026 ({@link LOSS_LEVEL_CODES}).
 */
function assetSetLevelRequests(requests: readonly RiskRequest[]): RiskRequest[] {
    return assetSetHistoricalRequests(requests).filter((request) => request.analytics.some((analytic) => isAssetSetLevel(analytic)));
}

/** The analytic codes of one request, deduplicated — the two VaR horizons share one. */
function codesOf(request: RiskRequest): Set<string> {
    return new Set(request.analytics.map((analytic) => analytic.analytic_code));
}

/** True when `request` carries any of `codes`. */
function carriesAny(request: RiskRequest, codes: readonly string[]): boolean {
    const carried = codesOf(request);
    return codes.some((code) => carried.has(code));
}

/** An asset-set scope as a comparable string, in the ascending order the client sends. */
function scopeKey(assetIds: readonly number[]): string {
    return [...assetIds].sort((left, right) => left - right).join(',');
}

/**
 * The per-asset waves asked about exactly this selection, both levels' together, in
 * the order they left.
 *
 * Filtered by scope and not merely counted, because a test that grows the
 * selection — `ensureSelectionAtLeast` does, when the seed is small — legitimately
 * produces a second wave for the second scope. Counting all of them and expecting
 * one would then be a test of the fixture's size rather than of the page, green on
 * a large seed and red on a small one with nothing wrong either time.
 *
 * Both levels' because L1° and L3° ask apart: a caller that reads an analytic, a
 * scope or a window off a request says whose request it reads, through
 * {@link lossRequestsFor} or {@link paidRequestsFor}.
 */
function levelRequestsFor(requests: readonly RiskRequest[], selection: readonly number[]): RiskRequest[] {
    const wanted = scopeKey(selection);
    return assetSetLevelRequests(requests).filter((request) => request.scope.kind === ASSET_SET_SCOPE && scopeKey(request.scope.asset_ids) === wanted);
}

/**
 * L1°'s requests about exactly this selection, in the order they left: those carrying any of
 * {@link LOSS_LEVEL_CODES}.
 *
 * Told apart by what they carry — the one thing that distinguishes the two levels' requests on the
 * wire — never by position or by count. So a request carrying both levels' codes, the one request
 * the levels shared before the split, is L1°'s *and* L3°'s here: a case that needs them apart turns
 * red on it instead of reading whichever happened to leave first.
 */
function lossRequestsFor(requests: readonly RiskRequest[], selection: readonly number[]): RiskRequest[] {
    return levelRequestsFor(requests, selection).filter((request) => carriesAny(request, LOSS_LEVEL_CODES));
}

/** L3°'s requests about exactly this selection, in the order they left: those carrying any of {@link PAID_LEVEL_CODES}, told apart the same way. */
function paidRequestsFor(requests: readonly RiskRequest[], selection: readonly number[]): RiskRequest[] {
    return levelRequestsFor(requests, selection).filter((request) => carriesAny(request, PAID_LEVEL_CODES));
}

/**
 * The correlation section's requests about exactly this selection, in the order they left: the
 * asset-set historical waves carrying `correlation` and none of the five per-asset codes. The replay
 * section asks the same `[correlation]` wave — one network call between the two, see
 * {@link assetSetLevelRequests} — and the stub answers it the same whoever asked.
 */
function correlationRequestsFor(requests: readonly RiskRequest[], selection: readonly number[]): RiskRequest[] {
    const wanted = scopeKey(selection);
    return assetSetHistoricalRequests(requests).filter((request) => request.scope.kind === ASSET_SET_SCOPE && scopeKey(request.scope.asset_ids) === wanted && codesOf(request).has('correlation') && !request.analytics.some((analytic) => isAssetSetLevel(analytic)));
}

/** The replay's own runs about exactly this selection, in the order they left: a `stress` asked as a historical replay. */
function replayRequestsFor(requests: readonly RiskRequest[], selection: readonly number[]): RiskRequest[] {
    const wanted = scopeKey(selection);
    return requests.filter((request) => request.scope.kind === ASSET_SET_SCOPE && scopeKey(request.scope.asset_ids) === wanted && request.analytics.some((analytic) => isHistoricalReplay(analytic)));
}

/**
 * Which of the lab's sections asked `request`, told apart by the analytics it carries — through the
 * classifiers the assertions read the captured requests with, applied to this one request about its
 * own scope, so the stub and its oracle cannot disagree about whose request is whose. Normally one
 * section; a request carrying both levels' codes — the one the levels shared before their split — is
 * L1°'s and L3°'s at once, as {@link lossRequestsFor} says; anything else on the wire is none.
 */
function labSectionsOf(request: RiskRequest): LabSection[] {
    if (request.scope.kind !== ASSET_SET_SCOPE) return [];
    const scope = request.scope.asset_ids;
    const sections: Array<[LabSection, (requests: readonly RiskRequest[], selection: readonly number[]) => RiskRequest[]]> = [
        ['correlation', correlationRequestsFor],
        ['loss', lossRequestsFor],
        ['paid', paidRequestsFor],
        ['replay', replayRequestsFor],
    ];
    return sections.filter(([, requestsFor]) => requestsFor([request], scope).length > 0).map(([section]) => section);
}

/**
 * An asset issue as `service.py::_asset_issue` builds it (D373): the backend's own key, action and
 * group for its code, one entry per asset in the order given, named the way the backend names an
 * asset it has no display name for ({@link unnamedAsset}) — the stub knows no names. Parsed through
 * the generated contract the client validates every answer with, so an issue it would refuse fails
 * here, by field, and not as a section that silently failed to load.
 */
function assetQualityIssue(code: 'STALE_PRICE' | 'MISSING_PRICE', assetIds: readonly number[]): QualityIssue {
    const stale = code === 'STALE_PRICE';
    return schemas.DataQualityIssue.parse({
        domain: 'asset',
        code,
        severity: stale ? 'warning' : 'error',
        message_i18n_key: stale ? 'dataQuality.stalePrice' : 'risk.quality.missingPrice',
        message_params: {count: assetIds.length},
        count: assetIds.length,
        affected_asset_ids: [...assetIds],
        affected_asset_names: assetIds.map(unnamedAsset),
        cta_action: stale ? 'sync_asset_prices' : 'navigate_asset',
        cta_target: String(assetIds[0]),
        group_key: stale ? 'stale_price' : 'missing_price',
    });
}

/** A pair with no exchange-rate route, as `service.py::_fx_issue` builds `MISSING_FX_MARKET`: it asks for one (`add_fx_pair`) and names no target. */
function unroutedPairIssue(pairs: readonly string[]): QualityIssue {
    return schemas.DataQualityIssue.parse({
        domain: 'forex',
        code: 'MISSING_FX_MARKET',
        severity: 'warning',
        message_i18n_key: 'risk.quality.missingFx',
        message_params: {count: pairs.length},
        count: pairs.length,
        affected_fx_pairs: [...pairs],
        cta_action: 'add_fx_pair',
        cta_target: null,
        group_key: 'missing_fx',
    });
}

/** ISO 4217's code reserved for testing: no route can exist for it, which is what an unrouted pair says. */
const UNROUTED_CURRENCY = 'XTS';

/** The three selected assets the data-quality case names. */
interface QualityCast {
    a: number;
    b: number;
    c: number;
}

/**
 * The data-quality case's cast, from a scope: its three lowest ids, with **A the highest of the
 * three and C the lowest**. So the order the banner must draw them in — first appearance across the
 * sections — runs against id order, and a banner that sorted its links by id, or read L3° before
 * L1°, would draw them in an order the case refuses. `null` under three assets.
 */
function qualityCast(assetIds: readonly number[]): QualityCast | null {
    const lowest = [...new Set(assetIds)].sort((left, right) => left - right).slice(0, 3);
    if (lowest.length < 3) return null;
    const [c, b, a] = lowest;
    return {a, b, c};
}

/**
 * What the data-quality case plants, per section, from the scope the request asks about
 * ({@link RiskStubOptions.qualityIssues}):
 *
 * - stale prices naming [A, B] in the correlation section's answer and [B, C] in L3°'s — two
 *   windows that would, in real life, find different assets stale;
 * - a missing price naming [A] in L1°'s answer and [C] in L3°'s;
 * - in the replay's own answer, a pair with no route: a code no other section sends.
 *
 * 📌 The correlation section's request is the replay section's base wave too (one flight, see
 * {@link LabSection}), so its stale prices reach both controllers. The panel meets the second copy
 * last — the replay comes after L3° — and it names no asset the first did not, so it adds no item,
 * no asset and moves nothing. The missing price rides only on the levels' requests, which nothing
 * shares.
 */
function labQualityIssues(section: LabSection, request: RiskRequest): QualityIssue[] {
    const cast = qualityCast(request.scope.kind === ASSET_SET_SCOPE ? request.scope.asset_ids : []);
    if (cast === null) return [];
    if (section === 'correlation') return [assetQualityIssue('STALE_PRICE', [cast.a, cast.b])];
    if (section === 'loss') return [assetQualityIssue('MISSING_PRICE', [cast.a])];
    if (section === 'paid') return [assetQualityIssue('STALE_PRICE', [cast.b, cast.c]), assetQualityIssue('MISSING_PRICE', [cast.c])];
    return [unroutedPairIssue([pairSlug(UNROUTED_CURRENCY, request.target_currency)])];
}

/** The ids the issues of one code name, merged the way `mergeQualityIssues` merges asset ids: their union, by first appearance. */
function idsByFirstAppearance(issues: readonly QualityIssue[], code: string): number[] {
    const ids: number[] = [];
    for (const issue of issues) {
        if (issue.code !== code) continue;
        for (const assetId of issue.affected_asset_ids ?? []) if (!ids.includes(assetId)) ids.push(assetId);
    }
    return ids;
}

/** The request each section feeding the lab's notice last sent about one selection. */
interface NoticeRequests {
    correlation: RiskRequest;
    loss: RiskRequest;
    paid: RiskRequest;
}

/**
 * Wait until the correlation section, L1° and L3° have each asked about `selection`, and hand back the
 * last request of each: the one whose answer is on screen. The stub answers a request from its scope,
 * window and analytics alone, so two requests of one section about one selection get one answer.
 */
async function noticeRequestsFor(requests: readonly RiskRequest[], selection: readonly number[]): Promise<NoticeRequests> {
    await expect.poll(() => correlationRequestsFor(requests, selection).length, {timeout: 20_000, message: 'the correlation section never asked about the selection on screen'}).toBeGreaterThan(0);
    await expect.poll(() => lossRequestsFor(requests, selection).length, {timeout: 20_000, message: 'L1° never asked about the selection on screen'}).toBeGreaterThan(0);
    await expect.poll(() => paidRequestsFor(requests, selection).length, {timeout: 20_000, message: 'L3° never asked about the selection on screen'}).toBeGreaterThan(0);
    return {
        correlation: correlationRequestsFor(requests, selection).at(-1) as RiskRequest,
        loss: lossRequestsFor(requests, selection).at(-1) as RiskRequest,
        paid: paidRequestsFor(requests, selection).at(-1) as RiskRequest,
    };
}

/** What the lab's one notice (`risk-partial-notice`) must publish. */
interface LabNotice {
    /** The results that came back `partial`: the notice's `data-partial-count`, and its measurements' `data-count`. */
    partial: number;
    /** The distinct sentences their warnings make — a key with its values: the reasons' `data-count`. */
    sentences: number;
    /** The results carrying the `assets_excluded` warning: that sentence's `data-occurrences`. */
    excluded: number;
}

/**
 * What the lab's notice must say, worked out from the answers the stub sent the three sections that
 * feed it — rebuilt through {@link resultFor}, the function `installRiskMocks` fulfilled them with, from
 * the requests it recorded, so the oracle cannot drift from the stub.
 *
 * The notice reads what those sections *render* (the developer's decision of 05/10/2026, the
 * Dashboard's pattern), and nothing else: the correlation section's `correlation`; L1°'s two VaR
 * horizons and its drawdown; L3°'s KPI, risk/return and — with a benchmark — comparison. Not the
 * `correlation` that rides in each level's own request, which no level draws; not the replay, which
 * keeps its own disclosure, as the Dashboard's L4 does.
 */
function labNoticeFor(sent: NoticeRequests, options: RiskStubOptions): LabNotice {
    const rendered = (request: RiskRequest, codes: readonly string[]) => request.analytics.filter((analytic) => codes.includes(analytic.analytic_code)).map((analytic) => resultFor(request, analytic, options));
    const results = [...rendered(sent.correlation, ['correlation']), ...rendered(sent.loss, LOSS_LEVEL_CODES), ...rendered(sent.paid, PAID_LEVEL_CODES)];
    const warningsOf = (result: Record<string, unknown>) => (result.warnings ?? []) as ReturnType<typeof exclusionWarnings>;
    return {
        partial: results.filter((result) => result.status === 'partial').length,
        sentences: new Set(results.flatMap((result) => warningsOf(result).map((warning) => `${warning.message_i18n_key}|${JSON.stringify(warning.message_params)}`))).size,
        excluded: results.filter((result) => warningsOf(result).some((warning) => warning.code === EXCLUDED_WARNING_CODE)).length,
    };
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

/** The counter, which publishes its numbers as attributes beside its sentence. */
const selectionCounter = (page: Page) => page.getByTestId('risk-selected-count');

/**
 * Two of the numbers behind `risk-selected-count`, read from `data-selected` and
 * `data-total` — never from the sentence next to them. `data-selected` counts the
 * assets in the analysis (the selection without what the engine rules out),
 * `data-total` the candidates (the catalogue without it); `data-parked`, the third,
 * counts the selected assets left out, and is asserted where it is the subject.
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

/** The lab's frame: the panel and its selection card. */
async function waitForLabFrame(page: Page): Promise<void> {
    await expect(page.getByTestId('asset-global-risk-panel')).toBeVisible({timeout: 20_000});
    await expect(page.getByTestId('risk-asset-set-controls')).toBeVisible({timeout: 15_000});
}

/**
 * Wait until the opening selection is on screen and every chip carries the engine's
 * verdict.
 *
 * The seed lands after the asset list — and, on a first visit, after the holdings
 * report — not with the panel frame: `count()` does not retry, so sampling it once
 * would read whatever had rendered by that instant.
 *
 * The verdict is the second barrier, and the reason is what it decides. Until the
 * engine answers, every asset is selectable (`isSelectable`: no verdict means yes);
 * once it has, what it rules out leaves the analysis while its chip stays. A test
 * that starts reading before the answer lands compares chips with sections across
 * that change. A chip reads `data-level="unknown"` exactly while it has no verdict,
 * so none left in that state means the answer is in — this file's own, from
 * `answerEligibility` — and a call that failed instead would keep them unknown
 * forever and turn red here rather than pass through the "failed" state unseen.
 */
async function waitForSelection(page: Page): Promise<void> {
    await expect
        .poll(() => page.getByTestId(/^risk-selected-asset-\d+$/).count(), {
            timeout: 15_000,
            message: 'the panel opened on an empty selection — it needs at least one seeded asset to analyse',
        })
        .toBeGreaterThan(0);
    await expect(page.locator('[data-testid^="risk-selected-asset-"][data-level="unknown"]'), 'every chip must carry the eligibility verdict before the test reads the selection').toHaveCount(0, {timeout: 15_000});
    await expect(page.getByTestId('risk-eligibility-failed')).toHaveCount(0);
}

async function openAssetGlobalRisk(page: Page): Promise<void> {
    await navigateTo(page, '/assets?tab=correlation');
    await waitForLabFrame(page);
    await waitForSelection(page);
}

/**
 * Open the lab while `gateReports` holds every report, and let the opening one through.
 *
 * On a first visit the opening selection *is* a report (rung 2 of the D19 ladder:
 * what is held on `dateEnd`, asked through the same light report the holdings
 * command uses), so a test that holds every report holds the seed too, and the page
 * would wait on it for ever. It is recognised by what it asks — no broker, every
 * holding the user can see — and the card must be saying that it is waiting on it
 * before it is released: `risk-asset-set-seeding` in place of the empty state.
 */
async function openAssetGlobalRiskReleasingSeed(page: Page, reports: readonly HeldReport[]): Promise<void> {
    await navigateTo(page, '/assets?tab=correlation');
    await waitForLabFrame(page);
    const seeds = () => reports.filter((report) => report.brokerIds === null);
    await expect.poll(() => seeds().length, {timeout: 15_000, message: 'a first visit must ask for what is held, across every broker'}).toBe(1);
    await expect(page.getByTestId('risk-asset-set-seeding'), 'while the holdings are out the card must say it is loading, not that nothing is selected').toBeVisible();
    await expect(page.getByTestId('risk-asset-set-empty')).toHaveCount(0);
    await seeds()[0].release();
    await waitForSelection(page);
}

/**
 * Pin global privacy off through the control a user has, and prove it took.
 *
 * The first no-money net reads digits. `L4Replay` formats every amount it may
 * print with `formatCurrencyAmount` (`riskAnalysisHelpers.ts`), which under
 * privacy masks the number and keeps the currency and the sign
 * (`maskCurrencyParts`): with privacy on, the stubbed magnitude never reaches the
 * page, and the digit assertion would pass about a figure it cannot see. The
 * masked form has a net of its own, in the privacy-ON variant, pinned by
 * {@link pinPrivacyOn}; each test pins the state its net needs. (`.currency-symbol`
 * never guarded that formatter anyway: only the HTML formatters of
 * `currencyFormat.ts` emit it.)
 *
 * Off is today's default only by implication: the key is absent in a fresh
 * browser context, and absent means off (`privacyStore.svelte.ts`, D3). Pinning
 * it makes that dependency explicit, so the net cannot lose its teeth in silence
 * the day the default changes.
 *
 * Driven through the header button, whose `aria-pressed` is its public state —
 * never through the storage key, which is the store's own business. The one-shot
 * read cannot be early: the store hydrates synchronously at module init, so the
 * button is born with its final state. The closing assertion is unconditional
 * because it is the positive control that the pin took effect, whichever branch
 * ran.
 */
async function pinPrivacyOff(page: Page): Promise<void> {
    const toggle = page.getByTestId('privacy-toggle');
    await expect(toggle).toBeVisible({timeout: 10_000});
    if ((await toggle.getAttribute('aria-pressed')) === 'true') await toggle.click();
    await expect(toggle, 'global privacy must be off, or the no-money net cannot see an amount').toHaveAttribute('aria-pressed', 'false');
}

/**
 * Pin global privacy on, through the same control: the inverse of
 * {@link pinPrivacyOff}, for the variant of the net that reads masked amounts.
 *
 * The flag lives in this browser context's `localStorage` (`privacyStore.svelte.ts`)
 * and nowhere else, so pinning it reaches no neighbouring test and no row of the
 * shared database.
 */
async function pinPrivacyOn(page: Page): Promise<void> {
    const toggle = page.getByTestId('privacy-toggle');
    await expect(toggle).toBeVisible({timeout: 10_000});
    if ((await toggle.getAttribute('aria-pressed')) !== 'true') await toggle.click();
    await expect(toggle, 'global privacy must be on, or this variant repeats the first net instead of testing the masked one').toHaveAttribute('aria-pressed', 'true');
}

/** The glyph `Intl` writes for a currency, `€` for EUR, as the formatters under test write it. */
function currencySymbol(code: string): string {
    return new Intl.NumberFormat('en', {style: 'currency', currency: code}).formatToParts(0).find((part) => part.type === 'currency')?.value ?? code;
}

/**
 * Every visible `glyph` under `root` that is not part of a bare currency label, as
 * the markup around it (for the failure message).
 *
 * `.currency-symbol` has two sources in `currencyFormat.ts`. `formatCurrencyAmountHtml`
 * puts it beside an amount (`.currency-amount`). `formatCurrencyCodeHtml` renders a
 * currency on its own — symbol, flag and code, `€ 🇪🇺 EUR` — for labels and filters,
 * and a page may show one: it names a currency and quotes no sum. So a glyph inside a
 * `.currency-symbol` whose parent holds no `.currency-amount` is left out; every other
 * one is money, or a currency's glyph with nothing to label.
 */
async function strayCurrencySymbols(root: Locator, glyph: string): Promise<string[]> {
    return root.evaluate((element, symbol) => {
        const stray: string[] = [];
        const walker = document.createTreeWalker(element, NodeFilter.SHOW_TEXT);
        for (let node = walker.nextNode(); node; node = walker.nextNode()) {
            if (!node.textContent?.includes(symbol)) continue;
            const holder = node.parentElement;
            if (!holder) continue;
            const visible = typeof holder.checkVisibility === 'function' ? holder.checkVisibility() : holder.getClientRects().length > 0;
            if (!visible) continue;
            const label = holder.closest('.currency-symbol');
            if (label && !label.parentElement?.querySelector('.currency-amount')) continue;
            stray.push(holder.outerHTML.slice(0, 200));
        }
        return stray;
    }, glyph);
}

/**
 * The no-money net over the lab's panel, shared by the privacy-off test and its
 * privacy-on variant so that the two cannot drift apart.
 *
 * Four ways an amount shows: the planted magnitude in clear, a figure with a
 * currency beside it, a currency glyph anywhere but in a bare currency label, and
 * the amount half of the HTML money formatter. A bare currency label passes:
 * `.currency-symbol` has two sources, and `formatCurrencyCodeHtml`'s (`€ 🇪🇺 EUR`)
 * names a currency and quotes no sum, which the page may do. So the net counts
 * `.currency-amount`, the part only an amount has, rather than the symbol both have.
 */
async function expectNoMoneyOnPanel(panel: Locator, rendered: string, requests: readonly RiskRequest[]): Promise<void> {
    expect(rendered, `the panel printed the stubbed monetary magnitude. Panel text was:\n${rendered}`).not.toMatch(MONEY_PATTERN);
    expect(rendered, `the panel printed a figure with a currency beside it. Panel text was:\n${rendered}`).not.toMatch(CURRENCY_BESIDE_FIGURE);
    for (const glyph of new Set(['€', currencySymbol(await answerCurrency(requests))])) {
        expect(await strayCurrencySymbols(panel, glyph), `the panel printed "${glyph}" outside a bare currency label — no amount of money belongs on an unweighted asset set`).toEqual([]);
    }
    await expect(panel.locator('.currency-amount'), 'the panel holds an amount of the HTML money formatter').toHaveCount(0);
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
 * ─── The "+" ───────────────────────────────────────────────────────────────
 *
 * The one way to add an asset by hand. It lists the page's own assets that are
 * not selected yet, stays open while rows are checked, and adds them all on one
 * press. What the engine rules out is listed too, read-only, under
 * `risk-asset-add-blocked`, with the same row testid on an `<li>` that carries
 * `data-level="ineligible"`. Its panel is mounted only while it is open
 * (`SelectPopover`), so the panel's absence *is* "closed".
 */
const addPanel = (page: Page) => page.getByTestId('risk-asset-add-panel');

/** Every row the "+" lists, checkable or not. Scoped to the panel, so no chip and no menu option can be counted with them. */
const pickerRows = (page: Page) => addPanel(page).getByTestId(/^risk-asset-add-option-\d+$/);

/** The rows that can be checked: every one the engine did not rule out. */
const checkableRows = (page: Page) => addPanel(page).locator('[data-testid^="risk-asset-add-option-"]:not([data-level="ineligible"])');

/** Open the "+" — asked, never toggled blind — and end on its list, or its empty state, being drawn. */
async function openPicker(page: Page): Promise<void> {
    const panel = addPanel(page);
    if (!(await panel.isVisible())) await page.getByTestId('risk-asset-add-button').click();
    await expect(panel).toBeVisible();
    await expect(pickerRows(page).or(panel.getByTestId('risk-asset-add-empty')).first()).toBeVisible();
}

/** Close the "+" through its own trigger, ending on the panel being gone. */
async function closePicker(page: Page): Promise<void> {
    if (await addPanel(page).isVisible()) await page.getByTestId('risk-asset-add-button').click();
    await expect(addPanel(page)).toHaveCount(0);
}

/** The asset ids the open "+" would let the user check, in the order it lists them. */
async function checkableAssetIds(page: Page): Promise<number[]> {
    const ids = await checkableRows(page).evaluateAll((nodes) => nodes.map((node) => Number(node.getAttribute('data-testid')?.replace('risk-asset-add-option-', ''))));
    return ids.filter((id) => Number.isInteger(id));
}

/**
 * Check these rows of the "+" and add them on one press, ending on their chips
 * being on screen and the panel closed. A row the engine ruled out is not a
 * button, so asking for one fails at its `aria-selected` rather than in silence.
 */
async function addThroughPicker(page: Page, assetIds: readonly number[]): Promise<void> {
    await openPicker(page);
    for (const assetId of assetIds) {
        const row = addPanel(page).getByTestId(`risk-asset-add-option-${assetId}`);
        await row.click();
        await expect(row, `the "+" must let asset ${assetId} be checked`).toHaveAttribute('aria-selected', 'true');
    }
    await addPanel(page).getByTestId('risk-asset-add-confirm').click();
    await expect(addPanel(page), 'confirming closes the "+"').toHaveCount(0);
    for (const assetId of assetIds) await expect(page.getByTestId(`risk-selected-asset-${assetId}`)).toBeVisible();
}

/**
 * Grow the selection until the matrix has enough assets to carry both findings.
 *
 * Three is the minimum for a *correlated* pair and an *offsetting* one to exist
 * at the same time. How many the page opens with is seed data, so the precondition
 * is checked and satisfied rather than assumed — and never silently skipped.
 *
 * Which assets get added is irrelevant: their ids are read off the rows that were
 * checked, so nothing downstream depends on the choice. `waitForSelection` has
 * already proved the seed landed, so the count it starts from is final.
 */
async function ensureSelectionAtLeast(page: Page, minimum: number): Promise<void> {
    const missing = minimum - (await chipIds(page)).length;
    if (missing <= 0) return;
    await openPicker(page);
    const offered = await checkableAssetIds(page);
    if (offered.length < missing) {
        await closePicker(page);
        throw new Error(`The selection needs ${missing} more asset(s) and the "+" offers ${offered.length}. Check populate_mock_data.py.`);
    }
    await addThroughPicker(page, offered.slice(0, missing));
}

/** One of the two filter menus of the "+". */
type FilterMenu = 'type' | 'currency';

/**
 * Open a filter menu of the "+" — asked, never toggled blind — with one press on
 * its own button, and end on it open and on its sibling closed.
 *
 * The sibling is not closed first. The press on this button is a click outside the
 * open sibling, and `SelectPopover` closes a menu on exactly that: a completed click,
 * not the press that starts it. When it closed on the press, the page got shorter
 * mid-press, the release landed on whatever slid under the pointer, and moving
 * from one menu to the other took two presses — `one press on the currency menu
 * opens it…` is the regression test for that. Ending on the sibling closed makes
 * every call made while it is open a check of the same path.
 */
async function openFilterMenu(page: Page, kind: FilterMenu): Promise<Locator> {
    const menu = page.getByTestId(`risk-asset-add-filter-${kind}-panel`);
    const button = addPanel(page).getByTestId(`risk-asset-add-filter-${kind}-button`);
    if (!(await menu.isVisible())) await button.click();
    await expect(menu).toBeVisible();
    await expect(button).toHaveAttribute('aria-expanded', 'true');
    const sibling: FilterMenu = kind === 'type' ? 'currency' : 'type';
    await expect(page.getByTestId(`risk-asset-add-filter-${sibling}-panel`), `opening the ${kind} menu must close the ${sibling} one by itself`).toHaveCount(0);
    return menu;
}

/**
 * A menu's options: what carries a pressed state. Its own "clear" shares the
 * testid prefix and has none, and so do the menu's button and panel — which is
 * what an unscoped `risk-asset-add-filter-type-*` used to catch.
 */
const filterOptions = (page: Page, kind: FilterMenu) => page.getByTestId(`risk-asset-add-filter-${kind}-panel`).locator(`[data-testid^="risk-asset-add-filter-${kind}-"][aria-pressed]`);

/**
 * A type filter that leaves a workable set of rows in the "+".
 *
 * Which asset types the seed contains is not this test's business, so the filter
 * is chosen by *property* — the smallest set of rows with at least two members —
 * instead of by position in the menu. The rows are what a filter narrows now: it
 * lives in the "+", above the list it filters, and no longer touches the quick
 * actions or the counter.
 *
 * Expects the "+" open; leaves the type menu open and every filter switched off,
 * exactly as it found them.
 */
async function chooseTypeFilter(page: Page): Promise<{testId: string; candidates: number; partitionSum: number; options: number}> {
    await openFilterMenu(page, 'type');
    const options = filterOptions(page, 'type');
    await expect(options.first()).toBeVisible();
    const testIds = (await options.evaluateAll((nodes) => nodes.map((node) => node.getAttribute('data-testid') ?? ''))).filter(Boolean);

    let best: {testId: string; candidates: number} | null = null;
    let partitionSum = 0;
    for (const testId of testIds) {
        const option = page.getByTestId(testId);
        await option.click();
        // `aria-pressed` and the rows are both driven by the picker's `filters`, so
        // they land in the same flush: once the option reports pressed, the list is
        // the filtered one and the one-shot count below cannot be early.
        await expect(option).toHaveAttribute('aria-pressed', 'true');
        const listed = await pickerRows(page).count();
        await option.click();
        await expect(option).toHaveAttribute('aria-pressed', 'false');
        partitionSum += listed;
        if (listed >= 2 && (best === null || listed < best.candidates)) best = {testId, candidates: listed};
    }

    if (!best) throw new Error(`No asset-type filter leaves at least two rows in the "+" (tried: ${testIds.join(', ')}).`);
    return {...best, partitionSum, options: testIds.length};
}

/**
 * A viewport too short for the Type menu to fit under its button, so that reaching
 * its lower options means scrolling the page. Set per page, so it dies with the test.
 */
const SHORT_VIEWPORT = {width: 1280, height: 480};

/** A search no asset answers to: the one way to shorten the "+" list whatever the seed holds. */
const NO_ASSET_QUERY = 'zz-no-asset-is-called-this-zz';

/**
 * How far the bottom of the viewport lies below everything on the page except the
 * open Type menu — the page's own content, and the "+" panel the menu hangs from.
 *
 * Positive means the page is scrolled into a strip that only the open menu makes.
 * Closing the menu takes the strip away, the page then ends above the bottom of the
 * viewport, and the browser scrolls it back by exactly this much.
 *
 * `document.body` stands for the page's own content: a panel positioned absolutely
 * lengthens the scrollable page, never the box of an ancestor, so the body ends
 * where the content in flow ends. Read once, after a scroll that is instant — this
 * app sets no `scroll-behavior` — and with no transition on the menus.
 */
async function typeMenuOverhang(page: Page): Promise<{overhang: number; scrollY: number}> {
    return page.evaluate(() => {
        const bottomOf = (testId: string) => document.querySelector(`[data-testid="${testId}"]`)?.getBoundingClientRect().bottom ?? Number.NaN;
        const rest = Math.max(bottomOf('risk-asset-add-panel'), document.body.getBoundingClientRect().bottom);
        return {overhang: Math.round(document.documentElement.clientHeight - rest), scrollY: Math.round(window.scrollY)};
    });
}

/**
 * Record where the next press starts and where it ends, and where the page stood at
 * each step — for the message of an assertion about that press, never for an
 * assertion of its own.
 *
 * A press that starts on one element and ends on another clicks neither: Chromium
 * sends the `click` to their closest common ancestor. That is the only trace a lost
 * click leaves, so it is what a red should show. Installed right before the press it
 * describes; the listeners only read.
 */
async function recordNextPress(page: Page): Promise<() => Promise<string>> {
    await page.evaluate(() => {
        const log: string[] = [`scrollY ${Math.round(window.scrollY)}`];
        const named = (target: EventTarget | null) => (target instanceof Element ? (target.closest('[data-testid]')?.getAttribute('data-testid') ?? target.tagName.toLowerCase()) : 'nothing');
        for (const type of ['mousedown', 'mouseup', 'click']) {
            window.addEventListener(type, (event) => log.push(`${type} on ${named(event.target)} at scrollY ${Math.round(window.scrollY)}`), {capture: true});
        }
        Object.assign(window, {__e2ePressLog: log});
    });
    return () => page.evaluate(() => ((window as unknown as {__e2ePressLog?: string[]}).__e2ePressLog ?? []).join(' → '));
}

/** The L1° section frame, and the table it wraps. Scoped: the page has two levels. */
const lossSection = (page: Page) => page.getByTestId('asset-global-risk-panel').getByTestId('risk-asset-set-loss');
const lossTable = (page: Page) => page.getByTestId('risk-asset-set-l1-table');
const paidSection = (page: Page) => page.getByTestId('asset-global-risk-panel').getByTestId('risk-asset-set-paid');

/**
 * The lab's one notice: what came back partial, and why, said once above the frames — the Dashboard's
 * `RiskPartialNotice`, adopted by the lab (the developer's decision of 05/10/2026). Scoped to the lab.
 */
const labNotice = (page: Page) => page.getByTestId('asset-global-risk-panel').getByTestId('risk-partial-notice');

/** The frames whose results the notice reads. The replay keeps its own disclosure, as the Dashboard's L4 does. */
const NOTICE_FRAMES = ['risk-correlation-section', 'risk-asset-set-loss', 'risk-asset-set-paid'] as const;

/**
 * Every frame the notice reads has drawn its answer: its provenance block is on screen, and
 * `RiskLevelSection` draws that block from the same results as its health and its reasons. So an
 * absence read after this — of the notice, or of a frame's disclosure — is about where a disclosure
 * lives, not about an answer that had not landed yet.
 */
async function waitForNoticeFrames(page: Page): Promise<void> {
    for (const frame of NOTICE_FRAMES) {
        await expect(page.getByTestId('asset-global-risk-panel').getByTestId(frame).getByTestId(`${frame}-metadata`), `${frame} never drew its answer's provenance`).toBeVisible({timeout: 20_000});
    }
}

/**
 * Where the lab's notice sits, as one verdict: `'between'` when it follows the selection card and
 * precedes the correlation section, inside neither — above every frame it speaks for, as the
 * Dashboard's sits above its levels; otherwise what is wrong.
 *
 * Document order, not pixels. One read, not a retry: a caller polls it, or fronts it with barriers.
 */
async function partialNoticePlacement(page: Page): Promise<string> {
    return page.getByTestId('asset-global-risk-panel').evaluate((panel) => {
        const find = (testId: string) => panel.querySelector(`[data-testid="${testId}"]`);
        const card = find('risk-asset-set-controls');
        const notice = find('risk-partial-notice');
        const correlation = find('risk-correlation-section');
        if (!card || !notice || !correlation) return `missing: card=${card !== null} notice=${notice !== null} correlation=${correlation !== null}`;
        if (card.contains(notice)) return 'inside the selection card';
        if (correlation.contains(notice)) return 'inside the correlation section';
        const precedes = (first: Element, second: Element) => !first.contains(second) && !second.contains(first) && (first.compareDocumentPosition(second) & Node.DOCUMENT_POSITION_FOLLOWING) !== 0;
        if (!precedes(card, notice)) return 'above the selection card';
        if (!precedes(notice, correlation)) return 'below the correlation section';
        return 'between';
    });
}

/**
 * The lab's data-quality banner (decision B, the developer, 05/10/2026): one `DataQualityBanner`,
 * `mode="grouped"`, over the issues of every section, drawn above the one notice. Scoped to the lab;
 * born folded, its rows drawn only once its toggle says it is open.
 */
const labBanner = (page: Page) => page.getByTestId('asset-global-risk-panel').getByTestId('data-quality-banner');

/**
 * Where the lab's data-quality banner sits, as one verdict: `'between'` when it follows the selection
 * card and precedes the notice — when one is drawn — and the correlation section, inside none of them:
 * at the top of what the sections say, above the one notice; otherwise what is wrong.
 *
 * The notice is optional *here* because it is drawn only when something came back partial or warned;
 * a caller that means to check the banner's place above it makes the notice a premise first. Document
 * order, not pixels. One read, not a retry: a caller polls it, or fronts it with barriers.
 */
async function qualityBannerPlacement(page: Page): Promise<string> {
    return page.getByTestId('asset-global-risk-panel').evaluate((panel) => {
        const find = (testId: string) => panel.querySelector(`[data-testid="${testId}"]`);
        const card = find('risk-asset-set-controls');
        const banner = find('data-quality-banner');
        const notice = find('risk-partial-notice');
        const correlation = find('risk-correlation-section');
        if (!card || !banner || !correlation) return `missing: card=${card !== null} banner=${banner !== null} correlation=${correlation !== null}`;
        const others: Array<[string, Element | null]> = [
            ['the selection card', card],
            ['the notice', notice],
            ['the correlation section', correlation],
        ];
        for (const [name, other] of others) {
            if (other?.contains(banner)) return `inside ${name}`;
            if (other && banner.contains(other)) return `wrapping ${name}`;
        }
        const precedes = (first: Element, second: Element) => (first.compareDocumentPosition(second) & Node.DOCUMENT_POSITION_FOLLOWING) !== 0;
        if (!precedes(card, banner)) return 'above the selection card';
        if (notice && !precedes(banner, notice)) return 'below the notice';
        if (!precedes(banner, correlation)) return 'below the correlation section';
        return 'between';
    });
}

/** The five per-asset cells of the L1° transposition, in the order they are drawn. */
const L1_CELLS = ['badDay', 'badMonth', 'worstFall', 'currentFall', 'toPeak'] as const;

/**
 * The L1° rows, top to bottom.
 *
 * L1° is the project's DataTable, which writes the row's identity as `data-row-id`
 * — here the asset id, because the table is a *transposition*: the reader compares
 * instruments down the page, so the row is the identity and the column is the
 * measure. Scoped to `tbody`: the header row is a row too, and carries no asset.
 */
const lossRows = (page: Page) => lossTable(page).locator('tbody tr[data-row-id]');

/** One asset's L1° row, by the id DataTable writes on it — never by position. */
const lossRow = (page: Page, assetId: number) => lossTable(page).locator(`tbody tr[data-row-id="${assetId}"]`);

/**
 * The asset ids the L1° table drew a row for, in the order it drew them, read from
 * the rows themselves. Reading them back is what lets an assertion be phrased over
 * the selection rather than over positions — and, once the reader sorts, over the
 * order the sort produced.
 *
 * One read, not a retry: a caller that expects an order polls it.
 */
async function lossRowAssetIds(page: Page): Promise<number[]> {
    return (await lossRows(page).evaluateAll((nodes) => nodes.map((node) => Number(node.getAttribute('data-row-id'))))).filter((id) => Number.isInteger(id));
}

/** A single L1° cell, addressed by the asset it belongs to — never by position. */
function lossCell(page: Page, assetId: number, cell: (typeof L1_CELLS)[number]) {
    return lossRow(page, assetId).locator(`[data-testid="risk-asset-set-l1-${cell}"]`);
}

/** One asset's name cell: its type icon and its name, carrying the asset's id. */
function lossNameCell(page: Page, assetId: number) {
    return lossTable(page).locator(`[data-testid="risk-asset-set-l1-name"][data-asset-id="${assetId}"]`);
}

/**
 * The L1° column ids, in the order the header draws them, read off DataTable's own
 * `dt-header-<id>` titles — so a hidden column is simply absent from the list.
 *
 * One read, not a retry: a caller that expects an order polls it.
 */
async function lossHeaderIds(page: Page): Promise<string[]> {
    return lossTable(page)
        .locator('thead th[data-testid^="dt-header-"]')
        .evaluateAll((nodes) => nodes.map((node) => (node.getAttribute('data-testid') ?? '').slice('dt-header-'.length)));
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

/**
 * ─── L3° — "what did each of these pay for its risk?" ──────────────────────
 *
 * Since the developer's review of 30/09 L3°'s table is the project's DataTable, as L1°'s is, and
 * its locators mirror L1°'s one for one: the wrapper publishes `data-row-count`, DataTable writes
 * each row's asset as `data-row-id`, the asset cell carries `data-asset-id`, and the header draws
 * one `dt-header-<id>` per visible column. `paidSection` above is the level's frame.
 */
const paidTable = (page: Page) => page.getByTestId('risk-asset-set-l3-table');

/** The four value cells every L3° table draws, in their order; a benchmark adds beta and correlation after them. */
const L3_CELLS = ['volatility', 'expectedReturn', 'sortino', 'sharpe'] as const;

/** The two a benchmark adds, in their order: drawn only while one applies, blank in the reference's own row when it is one of the selected (D371). */
const L3_BENCHMARK_CELLS = ['beta', 'correlation'] as const;

/** The L3° rows, top to bottom. Scoped to `tbody`: the header row carries no asset. */
const paidRows = (page: Page) => paidTable(page).locator('tbody tr[data-row-id]');

/** One asset's L3° row, by the id DataTable writes on it — never by position. */
const paidRow = (page: Page, assetId: number) => paidTable(page).locator(`tbody tr[data-row-id="${assetId}"]`);

/** The asset ids of the L3° rows, in the order drawn. One read, not a retry: a caller that expects an order polls it. */
async function paidRowAssetIds(page: Page): Promise<number[]> {
    return (await paidRows(page).evaluateAll((nodes) => nodes.map((node) => Number(node.getAttribute('data-row-id'))))).filter((id) => Number.isInteger(id));
}

/** A single L3° cell, addressed by the asset it belongs to — never by position. */
function paidCell(page: Page, assetId: number, cell: (typeof L3_CELLS)[number] | (typeof L3_BENCHMARK_CELLS)[number]) {
    return paidRow(page, assetId).locator(`[data-testid="risk-asset-set-l3-${cell}"]`);
}

/** One asset's L3° name cell: its type icon and its name, carrying the asset's id. */
function paidNameCell(page: Page, assetId: number) {
    return paidTable(page).locator(`[data-testid="risk-asset-set-l3-name"][data-asset-id="${assetId}"]`);
}

/** The L3° column ids, in the order the header draws them; a hidden column is absent. One read, not a retry. */
async function paidHeaderIds(page: Page): Promise<string[]> {
    return paidTable(page)
        .locator('thead th[data-testid^="dt-header-"]')
        .evaluateAll((nodes) => nodes.map((node) => (node.getAttribute('data-testid') ?? '').slice('dt-header-'.length)));
}

/**
 * Wait until L3° has stopped being a skeleton and is showing its table — the same barrier as
 * {@link waitForLossTable}: the section draws its skeleton while `loading` and no figure has
 * arrived, so the table's presence is the "the wave landed" signal for this level too.
 */
async function waitForPaidTable(page: Page): Promise<void> {
    await expect(paidTable(page)).toBeVisible({timeout: 20_000});
    await expect(page.getByTestId('risk-asset-set-l3-loading')).toHaveCount(0);
}

/**
 * ─── The blanks, and L3°'s period (the developer's review, round 4) ────────
 *
 * Neither table carries a fixed note under it any more. A value nobody could measure is an em dash,
 * and the dash explains itself: DataTable draws the cell — an `HtmlCell` with a `tooltip` — inside the
 * project's Tooltip, whose trigger is the component's own `div.tooltip-wrapper` with `role="button"`.
 * It carries no testid, so its class and its role are the contract read here; a measured cell is
 * drawn without a tooltip and has no such wrapper at all.
 *
 * Found by the cell it wraps, inside one row: the cell's testid names a column, the row the asset.
 */
function cellTooltip(row: Locator, cellTestId: string): Locator {
    return row.locator('div.tooltip-wrapper[role="button"]', {has: row.page().locator(`[data-testid="${cellTestId}"]`)});
}

/** The key of the sentence a dash explains itself with: what its help would print if the catalogue had no message for it. */
const BLANK_NOTE_KEY = 'risk.assetSet.levels.blankNote';

/** The window L3°'s period note publishes beside its sentence, as `data-start`, `data-end`, `data-days` and `data-narrowed`. */
interface L3Period {
    start: string;
    end: string;
    days: number;
    narrowed: boolean;
}

/** How far the analysed window may fall short of the toolbar's period, at either end, before the note calls it narrowed. */
const L3_PERIOD_TOLERANCE_DAYS = 7;

/**
 * What L3°'s period note must publish for the answer the stub sent to `request`, worked out from that
 * answer's `asset_set_risk_return` metadata as the engine defines it: `calendar_days` runs from the
 * baseline price — the one the first return is measured from — to `analyzed_range.end`, so the window
 * ends on `analyzed_range.end`, opens on the day after the baseline (`calendar_days − 1` days before
 * that end: the first day whose price movement the figures capture) and holds `calendar_days` days,
 * both ends counted. It is narrowed when it starts more than a week after the toolbar's period does,
 * or ends more than a week before it.
 *
 * The toolbar's period is the one the request carried: the page asks for the period its toolbar
 * shows, and the fit-period cases at the end of this file read the same dates off the URL. Rebuilt
 * through {@link metadata}, the function that answered, so the oracle cannot drift from the stub.
 *
 * `request` is L3°'s ({@link paidRequestsFor}): since the levels ask apart, L1°'s request carries
 * no `asset_set_risk_return`, and handing it here fails by name rather than reading another level.
 */
function l3PeriodFor(request: RiskRequest, options: RiskStubOptions = {}): L3Period {
    const analytic = request.analytics.find((candidate) => candidate.analytic_code === 'asset_set_risk_return');
    if (!analytic) throw new Error(`This request carries no asset_set_risk_return, so it is not L3°'s and has no window for L3° to publish — it carried ${JSON.stringify([...codesOf(request)])}.`);
    const served = metadata(request, analytic, options);
    const end = served.analyzed_range.end;
    const start = shiftDay(end, -served.calendar_days + 1);
    const toolbar: DayRange = {start: request.date_range.start, end: request.date_range.end ?? request.date_range.start};
    const narrowed = daysBetween(toolbar.start, start) > L3_PERIOD_TOLERANCE_DAYS || daysBetween(end, toolbar.end) > L3_PERIOD_TOLERANCE_DAYS;
    return {start, end, days: served.calendar_days, narrowed};
}

/**
 * End on L3°'s period note publishing exactly `expected`. Every read retries, so a caller that has
 * moved the toolbar waits here for the note to follow; the sentence is translated, and is only
 * required to say something.
 */
async function expectL3Period(page: Page, expected: L3Period, timeout: number): Promise<void> {
    const note = page.getByTestId('risk-asset-set-l3-period');
    await expect(note, 'L3° must say which period its figures cover').toBeVisible({timeout});
    await expect(note, "data-end must be the answer's analyzed_range.end").toHaveAttribute('data-end', expected.end, {timeout});
    await expect(note, 'data-start must be the day after the baseline price: that end less calendar_days, plus one').toHaveAttribute('data-start', expected.start, {timeout});
    await expect(note, 'data-days must be calendar_days: the days from data-start to data-end, both counted').toHaveAttribute('data-days', String(expected.days), {timeout});
    await expect(note, "data-narrowed must say whether the window falls more than a week short of the toolbar's period").toHaveAttribute('data-narrowed', String(expected.narrowed), {timeout});
    await expect(note, 'the note publishes a period but says nothing').not.toHaveText(/^\s*$/);
}

/**
 * Where L3°'s period note sits, in document order: `between` when it follows the table and precedes
 * the scatter, inside neither; otherwise what is wrong. One read, not a retry: a caller fronts it with
 * barriers on all three.
 */
async function l3PeriodPlacement(page: Page): Promise<string> {
    return page.getByTestId('risk-asset-set-l3').evaluate((level) => {
        const tables = level.querySelectorAll('[data-testid="risk-asset-set-l3-table"] table');
        const table = tables.length > 0 ? tables[tables.length - 1] : null;
        const note = level.querySelector('[data-testid="risk-asset-set-l3-period"]');
        const scatter = level.querySelector('[data-testid="risk-asset-set-l3-scatter"]');
        if (!table || !note || !scatter) return `missing: table=${table !== null} note=${note !== null} scatter=${scatter !== null}`;
        const precedes = (first: Element, second: Element) => !first.contains(second) && !second.contains(first) && (first.compareDocumentPosition(second) & Node.DOCUMENT_POSITION_FOLLOWING) !== 0;
        if (!precedes(table, note)) return 'before or inside the table';
        if (!precedes(note, scatter)) return 'after or inside the scatter';
        return 'between';
    });
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
 * The key one user's Asset Global selection is remembered under.
 *
 * Reproduced from `storageKey()` in `assetSetSelection.ts`, the way
 * `benchmarkStorageKey` reproduces the benchmark store's: the same `lf_<id>_`
 * shape. There is no `anon` spelling to go with it, because without an identity
 * the module keeps no memory at all.
 */
function selectionStorageKey(userId: number): string {
    return `lf_${userId}_${SELECTION_STORAGE_BASE_KEY}`;
}

/**
 * An asset the picker offers but the selection does not hold.
 *
 * Both halves are what the case reading it needs of its benchmark: it has to be
 * a real asset, and it must not be one of the measured — no longer because a
 * selected benchmark is refused (since D371 the lab applies it, the backend skips
 * it among the compared, and its own row's beta and correlation are blank), but
 * because that case counts a dot of the reference's own beside one per selected
 * asset, and a selected reference is drawn once. The "+" already guarantees
 * both — it lists the page's own assets that are not selected yet, and only the
 * ones the engine admits can be checked — so reading a candidate off it is the
 * same decision the product makes rather than an independent one that could
 * disagree.
 *
 * Leaves the "+" closed: it opens with an empty search and nothing checked, but a
 * panel left open would sit over the page the rest of the test reads.
 */
async function pickUnselectedAssetId(page: Page): Promise<number> {
    await openPicker(page);
    const offered = await checkableAssetIds(page);
    await closePicker(page);
    expect(offered.length, 'the "+" must offer at least one asset the selection does not hold').toBeGreaterThan(0);
    return offered[0];
}

/**
 * ─── The lab's benchmark picker ────────────────────────────────────────────
 *
 * Developer decision, 01/10/2026: wherever a page measures against a benchmark there is a
 * picker, it opens on the current benchmark, and it is empty only when nothing is set. The lab
 * mounts Risk's one primitive for it, `BenchmarkSelect`, under the testid below, in a row of its
 * own — the label, an ⓘ help, the picker — and mounts the levels only once the picker is no
 * longer `pending`. Since 02/10/2026 that row is the selection card's last, below the chips and
 * their «+»: a parameter common to the whole lab sits beside the choice of what to analyse.
 *
 * Every case reads what the primitive publishes on its root, `<testid>-control`:
 * `data-benchmark-id` (`''` when there is none), `data-benchmark-state`
 * (`none|pending|set|unknown`) and `data-measured`. Never the trigger's label, which is an
 * asset's name inside a translated frame.
 *
 * Since D371 (02/10/2026) a selected asset may be the benchmark, and becomes the reference of the
 * others: the lab's picker lists the selected assets too, publishes `data-measured="false"` whatever
 * the choice and draws no ⚠, and applies such a choice like any other — L3° leaves the reference's
 * own beta and correlation blank, each dash saying why, and draws it once (benchmark picker (c), (f)).
 *
 * The choice lives under the user-scoped key {@link benchmarkStorageKey} reproduces, shared by
 * every Risk page. The cases seed it, and the selection beside it, in this context's
 * `localStorage`, which dies with the context: there is nothing to restore.
 */
const LAB_BENCHMARK = 'risk-asset-set-benchmark';

/** The primitive's root: where the lab's picker publishes its state. */
const benchmarkControl = (page: Page) => page.getByTestId(`${LAB_BENCHMARK}-control`);

/** How many assets a benchmark case selects: a table and a scatter of their own, and a count "one dot more" is read against. */
const BENCHMARK_CASE_SELECTION = 3;

/** One full document load, then two levels and a chart to wait on, in a lane running tests in parallel: past the default budget. */
const BENCHMARK_CASE_BUDGET = 45_000;

/**
 * How far above the highest id on the list the "matches no asset" id is taken.
 *
 * Not `max + 1`: `assets.id` has no AUTOINCREMENT, so SQLite hands the next asset exactly that
 * id, and a neighbour creating one between this read and the page's own would turn the unknown
 * id into a real asset. The id is still derived from the list it must be absent from — never a
 * number assumed to be free.
 */
const ABSENT_ID_MARGIN = 100_000;

/** An asset as the picker offers it: the id it is chosen by, and the name a reader types to find it. */
interface NamedAsset {
    id: number;
    display_name: string;
}

/** What a benchmark case works with, all read off the asset list. */
interface BenchmarkCast {
    /** Written as the lab's last selection, so the opening is this test's own (rung 1 of D19). */
    selection: number[];
    /** The same assets in the same order, each with the name a reader types to find it in the picker, which offers them too since D371. */
    selected: NamedAsset[];
    /** A flagged benchmark the selection does not hold: what a reader would compare against. */
    reference: NamedAsset;
    /** An id the asset list does not hold, {@link ABSENT_ID_MARGIN} above its highest. */
    absentId: number;
}

/**
 * Read the assets a benchmark case needs off the list the page, the asset store and the picker
 * are all built from — `/assets/query` with the empty query — through `page.request`, which
 * `page.route` does not intercept.
 *
 * Picked by property, never by place, and the lowest id within a property: the reference is the
 * first asset flagged `is_benchmark` and the selection the first ones that are not, so the
 * reference is outside the selection by construction. `populate_mock_data.py` creates those
 * before any spec runs, so a neighbour's freshly created asset — which may be deleted under us —
 * is never one of them; `risk-benchmark-shared.spec.ts` picks the same way.
 *
 * Outside it on purpose, no longer by necessity: since D371 a selected benchmark is applied too —
 * benchmark picker (c) and (f) take theirs from the selection — but drawn once, as its own row's dot,
 * so the cases that count a dot more than the selection need a reference the selection does not hold.
 */
async function castBenchmark(page: Page): Promise<BenchmarkCast> {
    const response = await page.request.get('/api/v1/assets/query');
    expect(response.ok(), 'the asset list must answer: it is exactly what the picker offers and confirms a stored id against').toBe(true);
    const items = (await response.json()) as Array<Record<string, unknown>>;
    // Flattened the way `assetCatalogue` flattens: the generated union types let a scalar arrive wrapped.
    const flat = (value: unknown): unknown => (Array.isArray(value) ? value[0] : value);
    const listed = items.map((item) => ({id: Number(item.id), display_name: String(flat(item.display_name) ?? ''), benchmark: flat(item.is_benchmark) === true})).sort((left, right) => left.id - right.id);

    const reference = listed.find((asset) => asset.benchmark && asset.display_name !== '');
    if (!reference) throw new Error('No asset is flagged is_benchmark. populate_mock_data.py flags its INDEX assets as benchmarks.');
    const candidates = listed.filter((asset) => !asset.benchmark);
    if (candidates.length < BENCHMARK_CASE_SELECTION) throw new Error(`The benchmark cases select ${BENCHMARK_CASE_SELECTION} assets besides the benchmark, and the list holds ${candidates.length}. Check populate_mock_data.py.`);
    const selected = candidates.slice(0, BENCHMARK_CASE_SELECTION).map((asset) => ({id: asset.id, display_name: asset.display_name}));

    return {
        selection: selected.map((asset) => asset.id),
        selected,
        reference: {id: reference.id, display_name: reference.display_name},
        absentId: Math.max(0, ...listed.map((asset) => asset.id)) + ABSENT_ID_MARGIN,
    };
}

/** One entry of this origin's `localStorage`, as the app reads it. A one-shot read: a caller that expects a change polls it. */
async function readStorage(page: Page, key: string): Promise<string | null> {
    return page.evaluate((storageKey) => window.localStorage.getItem(storageKey), key);
}

/**
 * Write the lab's opening into this context's storage — the selection, and the shared
 * benchmark or its absence — and return the benchmark's key.
 *
 * Written from the page the login left open, on the app's origin, and read by a runtime that
 * starts afterwards: both stores keep their value at module scope and read storage once per
 * account, so only the full document load of {@link openLabOn} is sure to see the seed — the
 * pattern of `storeBenchmark` in `risk-benchmark-shared.spec.ts`. Only the user-scoped spelling
 * of each key is written, on purpose: the `(app)` layout renders after `/auth/me` has resolved,
 * so that is the key the picker must read, and a picker that opened on any other would be the
 * defect. "Nothing stored" is written too — as a removal — so it is a fact of the test rather
 * than an inheritance from a fresh context.
 */
async function storeLabOpening(page: Page, selection: readonly number[], benchmarkId: number | null): Promise<string> {
    const userId = await currentUserId(page);
    const selectionKey = selectionStorageKey(userId);
    const benchmarkKey = benchmarkStorageKey(userId);
    const selectionValue = JSON.stringify(selection);
    const benchmarkValue = benchmarkId === null ? null : String(benchmarkId);
    await page.evaluate(
        ([selectionAt, selectionStored, benchmarkAt, benchmarkStored]) => {
            window.localStorage.setItem(selectionAt, selectionStored);
            if (benchmarkStored === null) window.localStorage.removeItem(benchmarkAt);
            else window.localStorage.setItem(benchmarkAt, benchmarkStored);
        },
        [selectionKey, selectionValue, benchmarkKey, benchmarkValue] as const,
    );
    expect(await readStorage(page, selectionKey), 'the selection seed did not land in storage').toBe(selectionValue);
    expect(await readStorage(page, benchmarkKey), 'the benchmark seed did not land in storage').toBe(benchmarkValue);
    return benchmarkKey;
}

/**
 * Open the lab by a full document load, and prove the opening is the one
 * {@link storeLabOpening} wrote: restored from storage rather than seeded from the holdings,
 * and holding exactly the stored assets.
 */
async function openLabOn(page: Page, selection: readonly number[]): Promise<void> {
    await openAssetGlobalRisk(page);
    await expect(page.getByTestId('risk-asset-set-controls'), 'the opening must be the selection this test stored').toHaveAttribute('data-selection-source', 'persisted');
    await expect.poll(async () => scopeKey(await chipIds(page)), {message: 'the chips must be exactly the selection this test stored'}).toBe(scopeKey(selection));
}

/**
 * Open the lab's benchmark picker and end with it open.
 *
 * Copied from `risk-benchmark-shared.spec.ts` and pointed at this page's testid.
 * `SearchSelect.openDropdown()` ignores a click landing within 200 ms of its last close (a guard
 * against touch double-fire), and nothing on the page says the guard is armed: so this asks for
 * the end state and clicks only while it is not there, retrying until the list is open — never a
 * blind second click, which on an open list would close it again.
 */
async function openBenchmarkPicker(page: Page): Promise<void> {
    const trigger = page.getByTestId(`${LAB_BENCHMARK}-trigger`);
    await expect(async () => {
        if ((await trigger.getAttribute('aria-expanded')) !== 'true') await trigger.click();
        await expect(trigger).toHaveAttribute('aria-expanded', 'true', {timeout: 1_000});
    }, "the lab's benchmark picker never opened").toPass({timeout: 8_000});
}

/** Choose `asset` in the lab's picker the way a reader does — open, type its name, click it — and end with the list closed. */
async function chooseBenchmark(page: Page, asset: NamedAsset): Promise<void> {
    const trigger = page.getByTestId(`${LAB_BENCHMARK}-trigger`);
    await openBenchmarkPicker(page);
    await page.getByTestId(`${LAB_BENCHMARK}-search`).fill(asset.display_name);
    // Scoped to this picker: `search-select-option-*` is shared by every select on the page.
    const option = page.getByTestId(LAB_BENCHMARK).getByTestId(`search-select-option-${asset.id}`);
    await expect(option, `${asset.display_name} (#${asset.id}) is not on offer in the lab's benchmark picker`).toBeVisible({timeout: 8_000});
    await option.click();
    await expect(trigger).toHaveAttribute('aria-expanded', 'false');
}

/**
 * What each L3° request about this selection compared against, in the order they left: the
 * `comparison_asset_id` of its `asset_set_comparison`, or `null` for one that carried none. One entry
 * per request, so "every L3° request carried this benchmark" and "none carried any" are both read off
 * the same list. L3°'s requests only ({@link paidRequestsFor}): the comparison is L3°'s analytic, and
 * L1°'s requests — which must never carry one — are {@link expectLossWithoutComparison}'s to read.
 * One read, not a retry: a caller polls it.
 */
function waveBenchmarks(requests: readonly RiskRequest[], selection: readonly number[]): Array<number | null> {
    return paidRequestsFor(requests, selection).map((request) => {
        const comparison = request.analytics.find((analytic) => analytic.analytic_code === 'asset_set_comparison');
        return comparison ? Number(comparison.parameters?.comparison_asset_id) : null;
    });
}

/**
 * L3° drawn against `referenceId`: an L3° request about the selection carried it, its answer is
 * the one drawn, beta and correlation fill a cell per selected asset, and the scatter holds one
 * dot per asset plus the reference's own — unless the selection holds the reference (D371), which
 * is then one of those dots already and is drawn once.
 */
async function expectComparisonWith(page: Page, requests: readonly RiskRequest[], selection: readonly number[], referenceId: number): Promise<void> {
    await expect.poll(() => waveBenchmarks(requests, selection), {timeout: 20_000, message: `no L3° request about the selection carried benchmark ${referenceId}`}).toContain(referenceId);
    const paid = page.getByTestId('risk-asset-set-l3');
    await expect(paid, 'the comparison must come back and be the answer drawn').toHaveAttribute('data-benchmark', 'true', {timeout: 20_000});
    await expect(paid.getByTestId('risk-asset-set-l3-beta')).toHaveCount(selection.length);
    await expect(paid.getByTestId('risk-asset-set-l3-correlation')).toHaveCount(selection.length);
    await expectChartCanvas(page, 'risk-asset-set-l3-scatter', 20_000);
    const referenceSelected = selection.includes(referenceId);
    const dots = referenceSelected ? 'one dot per selected asset, the benchmark among them drawn once, never beside itself' : 'one dot per selected asset, and one for the benchmark';
    await expect(page.getByTestId('risk-asset-set-l3-scatter'), dots).toHaveAttribute('data-point-count', String(referenceSelected ? selection.length : selection.length + 1), {timeout: 20_000});
}

/**
 * L3° drawn with no comparison: a row per selected asset without beta or correlation, one dot
 * per asset and none for a reference, and no L3° request about the selection carrying a
 * comparison. Every absence is read behind a presence — the volatility cells, the drawn chart,
 * an L3° request on the wire — so none of them can be satisfied by a level that is still loading.
 */
async function expectNoComparison(page: Page, requests: readonly RiskRequest[], selection: readonly number[]): Promise<void> {
    await waitForPaidTable(page);
    const paid = page.getByTestId('risk-asset-set-l3');
    await expect(paid.getByTestId('risk-asset-set-l3-volatility'), 'L3° must draw a row per selected asset before its missing columns mean anything').toHaveCount(selection.length);
    await expect(paid).toHaveAttribute('data-benchmark', 'false');
    await expect(paid.getByTestId('risk-asset-set-l3-beta')).toHaveCount(0);
    await expect(paid.getByTestId('risk-asset-set-l3-correlation')).toHaveCount(0);
    await expectChartCanvas(page, 'risk-asset-set-l3-scatter', 20_000);
    await expect(page.getByTestId('risk-asset-set-l3-scatter'), 'one dot per selected asset, and none for a benchmark that does not apply').toHaveAttribute('data-point-count', String(selection.length), {timeout: 20_000});
    await expect.poll(() => waveBenchmarks(requests, selection).length, {timeout: 20_000, message: 'no L3° request about the selection reached the wire, so "no comparison" would prove nothing'}).toBeGreaterThan(0);
    const waves = waveBenchmarks(requests, selection);
    const unwarranted = `an L3° request carried a comparison this benchmark does not warrant — L3°'s benchmarks, in the order its requests left: ${JSON.stringify(waves)}`;
    expect(
        waves.filter((id) => id !== null),
        unwarranted,
    ).toEqual([]);
}

/**
 * L1° measured without a benchmark, whatever the benchmark: its table drawn, its request about the
 * selection on the wire, and no L1° request in this page's capture — about any scope, at any point —
 * carrying `asset_set_comparison`. The absence is read behind both presences, so a level that has not
 * asked yet cannot satisfy it.
 *
 * Read off the wire because the wire is the one place this spec can see a benchmark reach L1°. The
 * engine prepares a request's comparison asset together with its scope (`risk/service.py:183-196`),
 * so a benchmark joins the prepared set of everything in its request and can move its window — what
 * turned L1° «Partial» for the developer. The stub answers every analytic on its own and reproduces
 * none of that, so L1°'s figures and provenance would be drawn the same with or without a benchmark
 * riding along: on screen, "unaffected" would hold for the wrong reason. The request L1° sent cannot
 * hide what rode with it.
 */
async function expectLossWithoutComparison(page: Page, requests: readonly RiskRequest[], selection: readonly number[]): Promise<void> {
    await waitForLossTable(page);
    await expect.poll(() => lossRequestsFor(requests, selection).length, {timeout: 20_000, message: 'no L1° request about the selection reached the wire, so "L1° carries no comparison" would prove nothing'}).toBeGreaterThan(0);
    const carrying = assetSetLevelRequests(requests).filter((request) => carriesAny(request, LOSS_LEVEL_CODES) && codesOf(request).has('asset_set_comparison'));
    const shapes = carrying.map((request) => ({assets: request.scope.kind === ASSET_SET_SCOPE ? scopeKey(request.scope.asset_ids) : '', analytics: [...codesOf(request)].sort()}));
    const reached = `a benchmark reached L1°: an L1° request carried asset_set_comparison, which is L3°'s alone and would move L1°'s window — the L1° requests that carried one: ${JSON.stringify(shapes)}`;
    expect(shapes, reached).toEqual([]);
}

/**
 * Where the lab's benchmark row sits, as one verdict: `'in the selection card'` when its help and
 * its picker sit inside the selection card, after its row of chips and «+» and outside that row,
 * and come before the correlation section and both comparison levels, inside none of those three
 * frames, the help before the picker.
 *
 * Document order, not pixels: the row may wrap on a narrow screen, and what the developer
 * decided is the order a reader meets things in. One read, not a retry: a caller polls it.
 */
async function benchmarkRowPlacement(page: Page): Promise<string> {
    return page.getByTestId('asset-global-risk-panel').evaluate((panel) => {
        const find = (testId: string) => panel.querySelector(`[data-testid="${testId}"]`);
        const card = find('risk-asset-set-controls');
        const chips = find('risk-selected-assets');
        const control = find('risk-asset-set-benchmark-control');
        const help = find('risk-asset-set-benchmark-help');
        const correlation = find('risk-correlation-section');
        const loss = find('risk-asset-set-loss');
        const paid = find('risk-asset-set-paid');
        if (!card || !chips || !control || !help || !correlation || !loss || !paid) return `missing: card=${card !== null} chips=${chips !== null} picker=${control !== null} help=${help !== null} correlation=${correlation !== null} L1°=${loss !== null} L3°=${paid !== null}`;
        if (!card.contains(control)) return 'the picker is outside the selection card';
        if (!card.contains(help)) return 'the help is outside the selection card';
        const frames: Array<[string, Element]> = [
            ['the chips row', chips],
            ['the correlation section', correlation],
            ['L1°', loss],
            ['L3°', paid],
        ];
        for (const [name, frame] of frames) {
            if (frame.contains(control)) return `the picker is inside ${name}`;
            if (frame.contains(help)) return `the help is inside ${name}`;
        }
        const precedes = (first: Element, second: Element) => !first.contains(second) && !second.contains(first) && (first.compareDocumentPosition(second) & Node.DOCUMENT_POSITION_FOLLOWING) !== 0;
        if (!precedes(chips, help)) return 'the help is above the chips row';
        if (!precedes(help, control)) return 'the help comes after the picker';
        if (!precedes(control, correlation)) return 'the picker is below the correlation section';
        if (!precedes(control, loss)) return 'the picker is below L1°';
        if (!precedes(control, paid)) return 'the picker is below L3°';
        return 'in the selection card';
    });
}

/**
 * The catalogue's sentence for `key`, in the language the page is drawn in.
 *
 * Read from `<html lang>`, which the root layout keeps on the language actually shown, so a case
 * can tell the lab's own sentence from the primitive's generic one without holding on to any one
 * language's words. A key the catalogue lacks fails here, by name.
 */
async function catalogueSentence(page: Page, key: string): Promise<string> {
    const lang = ((await page.locator('html').getAttribute('lang')) ?? '').split('-')[0];
    const sentence = catalogueText(lang, key);
    expect(sentence, `the "${lang}" catalogue has no message for ${key}`).not.toBe(key);
    return sentence;
}

/**
 * A broker the user can see that holds something now, and what it holds.
 *
 * Replicated from `risk-analysis.spec.ts` rather than imported: a spec does not
 * reach into another spec's helpers. Read through `page.request`, which
 * `page.route` does not intercept, so this probe never lands among the reports
 * `captureReports` records for the page.
 */
async function brokerWithHoldings(page: Page): Promise<{brokerId: number; assetIds: number[]}> {
    const brokersResponse = await page.request.get('/api/v1/brokers');
    expect(brokersResponse.ok(), 'the preset offers the brokers this user can see, so the test must be able to list them').toBe(true);
    const brokersPayload = (await brokersResponse.json()) as {items?: Array<{id: number}>};

    for (const broker of brokersPayload.items ?? []) {
        const reportResponse = await page.request.post('/api/v1/portfolio/report', {
            data: {
                broker_ids: [broker.id],
                include_summary: true,
                include_history: false,
                include_allocation_history: false,
                include_breakdown: false,
                include_positions_contribution: false,
            },
        });
        if (!reportResponse.ok()) continue;
        const report = (await reportResponse.json()) as {summary?: {holdings?: Array<{asset_id: number}>} | null};
        const assetIds = [...new Set((report.summary?.holdings ?? []).map((holding) => holding.asset_id))].sort((left, right) => left - right);
        if (assetIds.length > 0) return {brokerId: broker.id, assetIds};
    }

    throw new Error('No broker this user can see holds anything. Check populate_mock_data.py.');
}

/** The body the page sent to `/portfolio/report`, reduced to what this file reads. */
interface ReportBody {
    broker_ids?: number[];
    include_summary?: boolean;
    include_history?: boolean;
    include_allocation_history?: boolean;
}

/** One `/portfolio/report` answer, reduced to what the preset reads and what it must not show — and to how it was asked. */
interface CapturedReport {
    brokerIds: number[] | null;
    /** Asked for the summary alone, without the daily history and the allocation history. */
    light: boolean;
    holdings: Array<{asset_id: number; current_value?: string | null}>;
}

/** Reduce one report answer the way the panel reads it (`singleValue(report?.summary)`), beside how it was asked. */
function capturedReport(sent: ReportBody, answer: {summary?: unknown}): CapturedReport {
    const summary = (Array.isArray(answer.summary) ? answer.summary[0] : answer.summary) as {holdings?: CapturedReport['holdings']} | null | undefined;
    return {
        brokerIds: sent.broker_ids ?? null,
        light: sent.include_summary === true && sent.include_history === false && sent.include_allocation_history === false,
        holdings: summary?.holdings ?? [],
    };
}

/**
 * What the preset loads from one answer: its holdings on the page's own list,
 * deduplicated, ascending, capped — `heldAssetIds`' reading, restriction included,
 * since a holding with no chip to remove it by must never reach the analysis.
 */
function presetIdsOf(report: CapturedReport, onPage: ReadonlySet<number>): number[] {
    return [...new Set(report.holdings.map((holding) => holding.asset_id))]
        .filter((assetId) => onPage.has(assetId))
        .sort((left, right) => left - right)
        .slice(0, API_ASSET_CEILING);
}

/**
 * A report answer with every holding taken out: the one field the holdings command
 * reads, set to what a broker that holds nothing on the period's last day answers
 * with. Everything else is left as the backend sent it, and nothing else is read.
 */
function withNothingHeld(answer: Record<string, unknown>): Record<string, unknown> {
    const summary = answer.summary;
    return summary && typeof summary === 'object' && !Array.isArray(summary) ? {...answer, summary: {...(summary as Record<string, unknown>), holdings: []}} : answer;
}

/**
 * `page.route`, with a callback that absorbs its own failure: whatever `handler`
 * throws stops it where it stands, leaves the request unanswered, and goes to
 * stderr rather than up.
 *
 * Nothing awaits a route callback, so what it throws is an unhandled rejection,
 * which Playwright pins on whatever the worker is doing at that moment — the case
 * it is running, not necessarily the one that installed the route, or between
 * cases the run itself — and stops the worker. A full run once ended «38 passed, 1
 * did not run, 1 error was not a part of any test»: `captureReports` was
 * forwarding a report the Dashboard had sent before the case left it, a slow
 * backend kept `route.fetch()` waiting past the case's end, and closing the
 * context rejected it («route.fetch: Test ended»). `sentByLab` removed that cause;
 * this removes the class. Closing the context disposes what a forward works with,
 * so the fetch, the answer's `json()` and a `fulfill` with that answer can each
 * reject once the case is over.
 *
 * Absorbed, not hidden. A failed callback hands the page nothing, so what the case
 * waits for behind that request never comes, and the case fails on its own barrier
 * — the capture it polls for, the state the answer would have produced. Unanswered
 * rather than aborted: the preset reads a failed report as it reads a discarded
 * one and asks again (`gateReports`), so a re-ask forwarded fine would let the
 * case pass over the failure; an unanswered one is given up only at axios's 30 s
 * timeout, later than any barrier here waits for a report. Nothing unroutes at
 * teardown either: see `holdLivePricePoll`.
 */
async function routeQuietly(page: Page, url: string, handler: Parameters<Page['route']>[1]): Promise<void> {
    await page.route(url, async (route, request) => {
        try {
            await handler(route, request);
        } catch (error) {
            console.warn(`[risk-lab] left ${request.method()} ${request.url()} unanswered: its route callback failed with ${String(error)}`);
        }
    });
}

/**
 * Whether the lab sent this request: its `Referer` path is `/assets`, whatever the query.
 *
 * The browser stamps the referer when the request leaves, so it names the page that
 * sent it even after that page is gone. `request.frame().url()` would not: it is the
 * frame's URL when the handler runs, so a Dashboard report whose route event is
 * handled after `page.goto` has committed the lab could read as the lab's. The app
 * sets no `Referrer-Policy`, so under the browser's default a same-origin request
 * carries the full path (the run that motivated this logged `referer: …/dashboard`).
 * Should that change, nothing would be kept, and the preset's first poll goes red.
 */
function sentByLab(request: Request): boolean {
    return /^https?:\/\/[^/]+\/assets(?:[?#]|$)/.test(request.headers().referer ?? '');
}

/**
 * Let `/portfolio/report` reach the real backend, and keep what the lab was told.
 *
 * The preset's oracle is the page's **own** answer rather than a probe taken
 * before the page loaded: a neighbour writing to the shared broker in between
 * would make the two disagree, and no timeout fixes a comparison against data the
 * page never saw. Recorded as a state, read at leisure — not an edge that has to
 * be armed before the click.
 *
 * Only what the lab sends goes through here, and only that is kept (`sentByLab`).
 * `login` lands on the Dashboard, which asks for its own report once its brokers
 * have loaded — often after this route is in place. That report is no oracle of
 * the lab's, and forwarding it outlived its page: the test navigated away, the
 * browser dropped the request, and `route.fetch()` went on waiting for a slow
 * backend until the context closed under it. It is continued untouched instead.
 * `continue`, not `fallback`: this route has always had the last word on a
 * report, so no route registered before it has ever seen one (none matches one
 * here), and the routes registered after it have already run.
 *
 * Registered quietly (`routeQuietly`): a forward that fails anyway leaves the page
 * unanswered, and the case fails on the capture it polls for, or on the selection
 * that answer would have set.
 */
async function captureReports(page: Page): Promise<CapturedReport[]> {
    const captured: CapturedReport[] = [];
    await routeQuietly(page, '**/api/v1/portfolio/report', async (route) => {
        if (route.request().method() !== 'POST' || !sentByLab(route.request())) return route.continue();
        const sent = (route.request().postDataJSON() ?? {}) as ReportBody;
        const response = await route.fetch();
        const answer = (response.ok() ? await response.json() : {}) as {summary?: unknown};
        captured.push(capturedReport(sent, answer));
        await route.fulfill({response});
    });
    return captured;
}

/** One `/portfolio/report` the page sent, held until the test lets it through. */
interface HeldReport {
    brokerIds: number[] | null;
    /** Send it to the backend and hand the answer to the page. Idempotent. */
    release(): Promise<CapturedReport>;
}

/**
 * Hold every `/portfolio/report` the page sends until the test lets it through.
 *
 * A discard is a comparison across time: `fetchReport` reads the report cache's
 * generation when it *sends*, and compares it when the answer *lands*. Holding
 * the answer is what lets a test put a portfolio mutation, and the page's proof
 * that it processed it, strictly in between. The handler returns without
 * handling the route, so the request stays paused until `release`, and each
 * entry is one request in the order the page sent them — the opening seed's
 * among them (see `openAssetGlobalRiskReleasingSeed`).
 *
 * `release` insists on a 2xx. `fetchReport` turns a *throw* into `null` too
 * (`promise.catch(() => null)`), so a re-ask after a failed answer would look
 * exactly like a re-ask after a discarded one. Only a successful answer makes the
 * `null` attributable to the discard.
 *
 * Only the callback is quiet (`routeQuietly`). `release` stays loud on purpose:
 * the case that calls it awaits it, so what it throws — a failed forward, a
 * non-2xx, an unreadable answer — fails that case, while it runs. A case that
 * times out awaiting it leaves the rejection to an await the runner still holds.
 */
async function gateReports(page: Page): Promise<HeldReport[]> {
    const held: HeldReport[] = [];
    await routeQuietly(page, '**/api/v1/portfolio/report', async (route) => {
        if (route.request().method() !== 'POST') return route.continue();
        const sent = (route.request().postDataJSON() ?? {}) as ReportBody;
        let released: Promise<CapturedReport> | undefined;
        held.push({
            brokerIds: sent.broker_ids ?? null,
            release: () =>
                (released ??= (async () => {
                    const response = await route.fetch();
                    expect(response.ok(), 'a held report must be answered by the backend, or a null would be an error rather than a discard').toBe(true);
                    const answer = (await response.json()) as {summary?: unknown};
                    await route.fulfill({response});
                    return capturedReport(sent, answer);
                })()),
        });
    });
    return held;
}

/** Open the holdings command and run one of its options, ending with the list closed. */
async function chooseBrokerPreset(page: Page, optionTestId: string): Promise<void> {
    await page.getByTestId('risk-broker-filter-button').click();
    const option = page.getByTestId(optionTestId);
    await expect(option).toBeVisible();
    await option.click();
    await expect(page.getByTestId('risk-broker-filter-dropdown')).toHaveCount(0);
}

/**
 * Run the page-sync modal to completion and close it: a portfolio mutation whose
 * end the page publishes.
 *
 * Both sync POSTs are portfolio mutations (`isPortfolioAffectingMutation`), so
 * `zodios-client`'s interceptor drops the report cache the moment each answer
 * lands. That happens before `doSyncFn` returns, and so before the modal can merge
 * a single row. The modal's end state is therefore proof, not a guess about time,
 * that the invalidation has run: results on screen and a body that is no longer
 * busy mean every section's answer has passed through the interceptor. This is
 * the barrier the live-price poll cannot offer, since nothing on this tab renders
 * what the poll returns.
 *
 * Opened from the page toolbar, where the lab's sync lives since F-3b: one sync per
 * page (V1), reaching the lab's own modal through `openSync`.
 */
async function runSyncToCompletion(page: Page): Promise<void> {
    const modal = page.getByTestId('page-sync-modal');
    await page.getByTestId('risk-sync-button').click();
    await expect(modal).toBeVisible();
    await modal.getByTestId('sync-modal-start').click();
    const results = modal.getByTestId('sync-modal-results');
    await expect(results).toBeVisible({timeout: 15_000});
    await expect(modal.getByTestId('sync-modal-body'), 'every section must have answered, not only the first one to merge').toHaveAttribute('data-busy', 'false');
    await expect(results, 'every stubbed item answers ok').toHaveAttribute('data-failed', '0');
    await modal.getByTestId('sync-modal-close').click();
    await expect(modal).toBeHidden();
}

/** What the page-sync modal asked the two sync endpoints for, call by call. */
interface SyncCalls {
    assets: number[][];
    fxPairs: string[][];
}

/**
 * Answer both endpoints the page-sync modal calls, and record what it asked.
 *
 * 🔴 Neither may get through. `PageSyncModal` posts prices to
 * `/assets/prices/sync` and rates to `/fx/currencies/sync`; for real, both reach
 * external providers and write to the shared database. Matched by regular
 * expression, so a query string cannot slip a call past the stub.
 *
 * Every item answers `ok`, which is what makes a run *accepted*
 * (`PageSyncModal.recordAccepted`: any `ok` or `partial`). The bodies go through
 * the generated schemas before they leave, because the client validates every
 * response (`validate: 'response'`): a stub that drifted from the contract would
 * otherwise surface as a failed sync with nothing pointing here.
 */
async function installSyncMocks(page: Page): Promise<SyncCalls> {
    const calls: SyncCalls = {assets: [], fxPairs: []};

    await page.route(/\/api\/v1\/assets\/prices\/sync(?:\?|$)/, async (route) => {
        const items = (route.request().postDataJSON() ?? []) as Array<{asset_id: number; date_range?: {start: string; end: string}}>;
        calls.assets.push(items.map((item) => item.asset_id));
        const body = schemas.FABulkRefreshResponse.parse({
            results: items.map((item) => ({asset_id: item.asset_id, status: 'ok', provider_used: 'E2E_MOCK', points_fetched: 1, points_changed: 0})),
            success_count: items.length,
            date_range: items[0]?.date_range ?? null,
        });
        await route.fulfill({status: 200, contentType: 'application/json', body: JSON.stringify(body)});
    });

    await page.route(/\/api\/v1\/fx\/currencies\/sync(?:\?|$)/, async (route) => {
        const sent = (route.request().postDataJSON() ?? {}) as {pairs?: string[]; start?: string; end?: string};
        const pairs = sent.pairs ?? [];
        calls.fxPairs.push([...pairs]);
        const body = schemas.FXSyncBulkResponse.parse({
            results: pairs.map((pair) => ({pair, status: 'ok', provider_used: 'E2E_MOCK', points_fetched: 1, points_changed: 0})),
            success_count: pairs.length,
            date_range: {start: sent.start ?? '', end: sent.end ?? ''},
        });
        await route.fulfill({status: 200, contentType: 'application/json', body: JSON.stringify(body)});
    });

    return calls;
}

/** An asset as the sync rule reads it: the currency it is quoted in, and whether a provider prices it. */
interface CatalogueAsset {
    currency: string;
    priced: boolean;
}

/**
 * The asset list the page and the asset store are both built from.
 *
 * The same endpoint with the same empty query that `+page.svelte` and
 * `assetStore` send, so "quoted in" and "has a provider" are read from the source
 * the modal's targets are derived from rather than assumed about the seed.
 * Flattened the way `assetStore.normalize` flattens, since the generated union
 * types let a scalar arrive wrapped.
 */
async function assetCatalogue(page: Page): Promise<Map<number, CatalogueAsset>> {
    const response = await page.request.get('/api/v1/assets/query');
    expect(response.ok(), 'the asset list the page is built from must be readable').toBe(true);
    const items = (await response.json()) as Array<Record<string, unknown>>;
    const flat = (value: unknown): unknown => (Array.isArray(value) ? value[0] : value);
    return new Map(items.map((item) => [Number(item.id), {currency: String(flat(item.currency) ?? ''), priced: Boolean(flat(item.provider_code))}]));
}

/** `EUR-USD`, never `USD-EUR`: a pair is named by its sorted slug, as `createPairSlug` builds it. */
function pairSlug(left: string, right: string): string {
    return [left.toUpperCase(), right.toUpperCase()].sort().join('-');
}

/**
 * The pair slugs the backend holds a route for — "configured", in the sync rule's sense.
 *
 * Read from `/fx/providers/routes`, the endpoint `fxRoutesStore` loads, so the
 * expectation stands on the same truth the modal is supposed to be built on.
 */
async function configuredPairSlugs(page: Page): Promise<Set<string>> {
    const response = await page.request.get('/api/v1/fx/providers/routes');
    expect(response.ok(), 'the configured exchange-rate routes must be readable').toBe(true);
    const payload = (await response.json()) as {items?: Array<{base?: string | null; quote?: string | null}>};
    return new Set((payload.items ?? []).filter((item) => item.base && item.quote).map((item) => pairSlug(item.base as string, item.quote as string)));
}

/** The one currency every section of this page answers in, read off the page's own requests. */
async function answerCurrency(requests: readonly RiskRequest[]): Promise<string> {
    await expect.poll(() => assetSetHistoricalRequests(requests).length, {timeout: 15_000, message: 'the page must have asked its first question'}).toBeGreaterThan(0);
    const currencies = [...new Set(assetSetHistoricalRequests(requests).map((request) => request.target_currency))];
    expect(currencies, 'one page, one target currency').toHaveLength(1);
    return currencies[0];
}

/**
 * Make sure the selection holds at least one asset `wanted` accepts, adding one
 * through the "+" when it does not.
 *
 * A precondition checked and satisfied, never inherited from the seed: an
 * assertion about "the pairs the modal lists" is an assertion about an empty list
 * when nothing selected is quoted elsewhere. Candidates are read off the "+"
 * itself, which offers exactly the page's assets not yet selected.
 */
async function ensureSelectedWhere(page: Page, wanted: (assetId: number) => boolean, what: string): Promise<void> {
    if ((await chipIds(page)).some(wanted)) return;
    await openPicker(page);
    const candidate = (await checkableAssetIds(page)).find(wanted);
    if (candidate === undefined) {
        await closePicker(page);
        throw new Error(`The selection holds no ${what}, and the "+" offers none to add. Check populate_mock_data.py.`);
    }
    await addThroughPicker(page, [candidate]);
}

/**
 * Open the L4 rung and run the replay, ending on its answer being on screen.
 *
 * The rung is `collapsible` and born closed, so it is opened only if it is not
 * already open — asked, never clicked blind — and the helper ends on the
 * post-condition it promises: the bars and the total of an answer.
 */
async function openAndRunReplay(page: Page): Promise<void> {
    const section = page.getByTestId('risk-replay-section');
    await expect(section).toBeVisible({timeout: 15_000});
    if ((await section.getAttribute('data-open')) !== 'true') await page.getByTestId('risk-replay-section-toggle').click();
    await expect(section).toHaveAttribute('data-open', 'true');
    const run = page.getByTestId('risk-replay-run');
    await expect(run).toBeEnabled();
    await run.click();
    await expect(page.getByTestId('risk-l4-replay').getByTestId('risk-replay-tornado-row').first()).toBeVisible({timeout: 20_000});
    await expect(page.getByTestId('risk-replay-total')).toBeVisible();
}

/** Two sets compared as sets, so declaration order can never be the subject. */
function sameMembers(left: readonly string[], right: readonly string[]): boolean {
    if (left.length !== right.length) return false;
    const rightSet = new Set(right);
    return left.every((entry) => rightSet.has(entry));
}

/**
 * ─── The matrix's grouping inputs ──────────────────────────────────────────
 *
 * Beyond similarity and name, the heatmap offers three orderings, and each one
 * exists only while the lab hands it a map to group by: by type (the page's own
 * asset list carries the types), by dominant sector and by dominant area (both
 * from one bulk read of the assets' stored metadata,
 * `GET /api/v1/assets?asset_ids=…`). That read is answered here and never
 * inherited from the seed: a test built on what the seed happens to classify
 * would be measuring the seed.
 *
 * The planted classification is keyed by an asset's rank among the ids the read
 * asked about — the ids the lab analyses, sorted — so a test can rebuild each
 * asset's group from its own selection. Sectors alternate with the rank and areas
 * change every second rank, so the two partitions cross: with four assets or
 * more, no order is grouped by both. That is what lets one click on "by sector"
 * prove the sector map is the one behind it: had the lab handed the heatmap its
 * area map there, the blocks drawn would be areas, and those are never sector
 * blocks. The sector partition also interleaves the similarity order this file's
 * stub produces (`[0, 3, 2, 1, 4, …]` in rank terms); the test checks that
 * rather than trusting it.
 *
 * Each distribution names its group well above `DOMINANT_SHARE` of its classified
 * weight, so `dominant` is the key `dominantExposure` picks. The weights are
 * Decimal strings, as the backend stores them and as the response schema demands
 * (`FASectorArea_Output`): the client validates every response, and a number here
 * would be refused and look exactly like a failed read.
 */
const PLANTED_SECTORS = [
    {dominant: 'Technology', distribution: {Technology: '0.7000', 'Health Care': '0.2000', Other: '0.1000'}},
    {dominant: 'Financials', distribution: {Financials: '0.6000', Energy: '0.3000', Other: '0.1000'}},
] as const;
const PLANTED_AREAS = [
    {dominant: 'USA', distribution: {USA: '0.8000', Other: '0.2000'}},
    {dominant: 'DEU', distribution: {DEU: '0.6500', FRA: '0.3500'}},
] as const;

function plantedSector(rank: number): (typeof PLANTED_SECTORS)[number] {
    return PLANTED_SECTORS[rank % PLANTED_SECTORS.length];
}

function plantedArea(rank: number): (typeof PLANTED_AREAS)[number] {
    return PLANTED_AREAS[Math.floor(rank / 2) % PLANTED_AREAS.length];
}

/** One bulk metadata read, as the page asked it and as this file answered it. */
interface MetadataRead {
    /** The ids of the query string, as sent. */
    assetIds: number[];
    /** `planted`: the lane's rows with their classification replaced. `failed`: a 500. */
    answer: 'planted' | 'failed';
    /** The ids of the rows handed back; empty for a failed read. */
    rowIds: number[];
    /** Why the answer is not the one intended — the real read failed, the schema refuses the body — or `null`. */
    problem: string | null;
}

/**
 * Answer the lab's bulk metadata read with the planted classification, until
 * `failFromNow` turns every later read into a 500 — and `answerFromNow` back.
 *
 * Only that read is routed: a `GET /api/v1/assets` carrying `asset_ids`. The
 * page's other calls under `/api/v1/assets…` — its list (`/assets/query`), the
 * held live-price poll (`/assets/prices/current`) — have other paths and never
 * reach this handler, and anything but a GET falls through to the network.
 *
 * The lane's own rows are fetched and only `sector_area` and `geographic_area`
 * are replaced, so the rest of each row — name, currency, type — is what the lane
 * stores. It is a GET: nothing is written. The planted body is checked against
 * the generated schema before it leaves, and a refusal is recorded rather than
 * thrown, so the test can name it instead of timing out on buttons that never
 * came. The route dies with the test's page; there is nothing else to undo.
 */
async function plantAssetMetadata(page: Page): Promise<{reads: MetadataRead[]; failFromNow: () => void; answerFromNow: () => void}> {
    const reads: MetadataRead[] = [];
    let failing = false;
    await page.route(
        (url) => url.pathname === '/api/v1/assets' && url.searchParams.has('asset_ids'),
        async (route) => {
            const request = route.request();
            if (request.method() !== 'GET') {
                await route.fallback();
                return;
            }
            const assetIds = new URL(request.url()).searchParams.getAll('asset_ids').map(Number);
            if (failing) {
                await route.fulfill({status: 500, json: {detail: 'metadata read failed on purpose by risk-lab.spec.ts'}});
                reads.push({assetIds, answer: 'failed', rowIds: [], problem: null});
                return;
            }
            try {
                const response = await route.fetch();
                if (!response.ok()) {
                    await route.fulfill({response});
                    reads.push({assetIds, answer: 'planted', rowIds: [], problem: `the lane answered the real read with ${response.status()}`});
                    return;
                }
                const rows = (await response.json()) as Array<Record<string, unknown>>;
                const ranked = [...new Set(assetIds)].sort((left, right) => left - right);
                const planted: Array<Record<string, unknown>> = rows.map((row) => {
                    const rank = ranked.indexOf(Number(row.asset_id));
                    const stored = row.classification_params;
                    const kept = stored !== null && typeof stored === 'object' && !Array.isArray(stored) ? stored : {};
                    return {
                        ...row,
                        classification_params: {...kept, sector_area: {distribution: {...plantedSector(rank).distribution}}, geographic_area: {distribution: {...plantedArea(rank).distribution}}},
                    };
                });
                const verdict = schemas.FAAssetMetadataResponse.array().safeParse(planted);
                await route.fulfill({response, json: planted});
                reads.push({
                    assetIds,
                    answer: 'planted',
                    rowIds: planted.map((row) => Number(row.asset_id)),
                    problem: verdict.success ? null : `the planted rows fail FAAssetMetadataResponse: ${verdict.error.issues.map((issue) => `${issue.path.join('.')}: ${issue.message}`).join('; ')}`,
                });
            } catch (error) {
                reads.push({assetIds, answer: 'planted', rowIds: [], problem: `the read could not be answered: ${String(error)}`});
                await route.abort().catch(() => undefined);
            }
        },
    );
    return {
        reads,
        failFromNow: () => {
            failing = true;
        },
        answerFromNow: () => {
            failing = false;
        },
    };
}

/**
 * The order the heatmap draws, off `data-asset-order`. A one-shot read, like every
 * `getAttribute`: callers poll it or front it with a barrier that retries.
 */
async function drawnAssetOrder(page: Page): Promise<number[]> {
    const raw = await page.getByTestId('asset-global-risk-panel').getByTestId('risk-correlation-heatmap').getAttribute('data-asset-order');
    return (raw ?? '')
        .split(',')
        .filter((entry) => entry !== '')
        .map(Number);
}

/**
 * True when every group of `groupOf` forms one unbroken block of `order` — the
 * shape a grouped ordering promises. Which group comes first is left out on
 * purpose: groups are sorted by their translated names, and the language is not
 * this file's subject.
 */
function groupedBy(order: readonly number[], groupOf: (assetId: number) => string): boolean {
    const closed = new Set<string>();
    let current: string | undefined;
    for (const assetId of order) {
        const group = groupOf(assetId);
        if (group === current) continue;
        if (current !== undefined) closed.add(current);
        if (closed.has(group)) return false;
        current = group;
    }
    return true;
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
        // Before anything money-bearing renders: under global privacy the digit
        // assertions at the end of this test are blind, because the risk formatter
        // masks the number (see `pinPrivacyOff`). The masked form has its own net,
        // in the privacy-ON variant below.
        await pinPrivacyOff(page);
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
        // `risk-replay-excluded` proves the answer is a *replay* — it is drawn from
        // `historical_replay_audit`, which no other analytic carries — while listing
        // what the replay left out without a single weight.
        await expect(page.getByTestId('risk-replay-total')).toBeVisible({timeout: 20_000});
        await expect(page.getByTestId('risk-l4-replay').getByTestId('risk-replay-tornado-row').first()).toBeVisible({timeout: 20_000});
        await expectReplayLeftOutWithoutWeight(page);
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
        //
        // The currency *glyph* is looked for as money, not as a character: a bare
        // currency label (`formatCurrencyCodeHtml`, `€ 🇪🇺 EUR`) names a currency the
        // same way the code does, and passes (see `expectNoMoneyOnPanel`).
        await expectNoMoneyOnPanel(panel, rendered, requests);
    });

    /**
     * C1b — the same net, with privacy on.
     *
     * The first test pins privacy off because its net reads digits. With privacy on,
     * `formatCurrencyAmount` masks the number and keeps the currency and the sign
     * (`maskCurrencyParts`: privacy hides the number, not the currency). So an amount
     * that reached this page would still show, as `€ •••`, `−€•••` or `••• €`
     * depending on the locale. This variant looks for that form, with the same bait,
     * behind the same barriers, over the same panel. The panel and not the page: the
     * header may show masked amounts of its own, and those belong to the reader's
     * portfolio, not to this page.
     *
     * Both nets share `expectNoMoneyOnPanel`, which looks for the amount itself and lets a
     * bare currency label through; this one adds the mask, the form an amount takes here.
     */
    test('prints no money with privacy on either, masked or in clear', async ({page}) => {
        // The first test's budget, for the first test's work: the same barriers on the same sections.
        test.setTimeout(45_000);
        const requests = await installRiskMocks(page);
        await openAssetGlobalRisk(page);
        // Before anything money-bearing renders, as in the first test, but on.
        await pinPrivacyOn(page);
        await ensureSelectionAtLeast(page, 2);
        await waitForRiskCatalog(page);

        const panel = page.getByTestId('asset-global-risk-panel');

        // The same reach as the first test (its ③): the two comparison levels populated and
        // the scatter drawn, so the scan below crosses figures rather than empty frames.
        const selected = await chipIds(page);
        await waitForLossTable(page);
        await expect(lossTable(page).locator('[data-testid="risk-asset-set-l1-badDay"][data-measured="true"]'), 'L1° must be showing figures, or the money scan below crosses an empty table').toHaveCount(selected.length);
        await expect(panel.getByTestId('risk-asset-set-l3-risk-return')).toBeVisible({timeout: 20_000});
        await expectChartCanvas(page, 'risk-asset-set-l3-scatter', 20_000);

        // The bait: the replay, where the stubbed amounts arrive, run behind the same
        // presence barriers — the total, a tornado row, and the list of what it left
        // out that proves the answer is a replay, without a weight.
        await openAndRunReplay(page);
        await expectReplayLeftOutWithoutWeight(page);
        await expect
            .poll(() => requests.some((request) => request.scope.kind === 'asset_set' && request.mode === 'current_composition' && request.analytics.some((analytic) => isHistoricalReplay(analytic))), {
                timeout: 15_000,
                message: 'the replay must have run against an asset_set scope — that is the scope the no-money rule is about',
            })
            .toBe(true);
        // The premise, still true at the end: nothing along the way turned privacy off.
        await expect(page.getByTestId('privacy-toggle')).toHaveAttribute('aria-pressed', 'true');

        // Populated with the half it is allowed to show: percentages, which privacy does not mask.
        const replayText = await page.getByTestId('risk-l4-replay').innerText();
        expect(replayText, 'the replay rendered without a single percentage — the barriers above are lying').toContain('%');

        const rendered = await panel.innerText();
        // THE RULE, masked. An amount on this page is a claim about a portfolio the
        // reader never described, and hiding its number does not make it true.
        expect(rendered, `the panel printed a masked amount — privacy hid the number of an amount that must not exist here. Panel text was:\n${rendered}`).not.toContain(MASKED_AMOUNT);
        await expectNoMoneyOnPanel(panel, rendered, requests);
    });

    test('opens on a small selection, never on the API ceiling', async ({page}) => {
        const requests = await installRiskMocks(page);

        // D19 is a statement about the *first* visit, so the absence of a stored
        // preference is made a fact of this test rather than an assumption about
        // how the fixture isolates contexts. The per-user key is the one that
        // matters: since F-2 it is the only one the page reads. The bare legacy key
        // goes too, harmlessly — the module never adopts it, it only removes it.
        const userId = await currentUserId(page);
        await page.addInitScript(
            (keys) => {
                for (const key of keys) {
                    try {
                        window.localStorage.removeItem(key);
                    } catch {
                        /* storage disabled — there is nothing to clear */
                    }
                }
            },
            [selectionStorageKey(userId), SELECTION_STORAGE_BASE_KEY],
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
        // tests of `resolveInitialSelectionWithSource`. What is asserted here is the wiring:
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
        // The filter the mass actions obey is no longer a chip row the user may have
        // forgotten was on — those moved into the "+", where they narrow a list, not a
        // button. It is the eligibility engine: the candidates are the catalogue
        // without what it rules out for the period (`AssetSetRiskPanel`'s
        // `candidates`). So this test writes the verdicts itself — three assets
        // admitted, every other one ruled out — which makes "never past the filter" a
        // statement about assets that exist and are refused, not about an empty set.
        //
        // Which three is irrelevant, so they are the three smallest ids of the list
        // the page is built from, and the fourth is the one parked below: seed rows,
        // which a neighbour's transient asset — always a newer, larger id — cannot
        // displace. An id this probe never saw is ruled out like the rest, so the
        // candidates stay exactly these.
        const catalogue = [...(await assetCatalogue(page)).keys()].sort((left, right) => left - right);
        expect(catalogue.length, 'the round trip needs three admitted assets and at least two ruled out').toBeGreaterThanOrEqual(5);
        const admitted = catalogue.slice(0, 3);
        const parked = catalogue[3];
        await installRiskMocks(page);
        await answerEligibility(page, (assetId) => (admitted.includes(assetId) ? ELIGIBLE : NO_PRICES));

        // Start from a state this test owns, and one the mass actions cannot reach by
        // themselves: a ruled-out asset *in* the selection. The UI puts one there only
        // through holdings, which are seed data, so the opening is written where the
        // page remembers its last selection — rung 1 of the ladder, under the per-user
        // key — as one admitted asset beside one ruled out. Written from the page the
        // login left open, before the page that reads it is loaded.
        const userId = await currentUserId(page);
        await page.evaluate(([key, value]) => window.localStorage.setItem(key, value), [selectionStorageKey(userId), JSON.stringify([admitted[0], parked])]);
        await openAssetGlobalRisk(page);

        const chips = page.getByTestId(/^risk-selected-asset-\d+$/);
        const counter = selectionCounter(page);
        const selection = async () => scopeKey(await chipIds(page));
        const everything = scopeKey([...admitted, parked]);

        // The opening is the stored one, and the engine's word reached it: the
        // ruled-out asset is parked — on screen, out of the analysis.
        await expect(page.getByTestId('risk-asset-set-controls'), 'the opening must be the selection this test stored').toHaveAttribute('data-selection-source', 'persisted');
        await expect.poll(selection).toBe(scopeKey([admitted[0], parked]));
        await expect(page.getByTestId(`risk-selected-asset-${parked}`)).toHaveAttribute('data-level', 'ineligible');
        await expect(page.getByTestId(`risk-selected-asset-${parked}`)).toHaveAttribute('data-reasons', 'no_prices');
        await expect(page.getByTestId(`risk-selected-asset-${admitted[0]}`)).toHaveAttribute('data-level', 'eligible');
        await expect(page.getByTestId('risk-parked-note')).toBeVisible();
        await expect(counter, 'the candidates are the catalogue without what the engine rules out').toHaveAttribute('data-total', String(admitted.length));
        await expect(counter).toHaveAttribute('data-selected', '1');
        await expect(counter).toHaveAttribute('data-parked', '1');

        // `all` reaches exactly the candidates, never past them: a button that brought
        // in an asset the engine refused would fill the selection with chips the
        // analysis cannot use. What was already selected stays.
        await page.getByTestId('risk-bulk-all').click();
        await expect.poll(selection, {message: '`all` must add every candidate and nothing the engine ruled out'}).toBe(everything);
        await expect(counter).toHaveAttribute('data-selected', String(admitted.length));
        await expect(counter).toHaveAttribute('data-parked', '1');

        // `invert` flips those same candidates, and leaves the parked asset where it
        // is: it was never one of them. Every candidate is selected, so inverting takes
        // them all out and leaves the analysis with nothing…
        await page.getByTestId('risk-bulk-invert').click();
        await expect.poll(selection, {message: '`invert` must flip the candidates and leave the parked asset in place'}).toBe(scopeKey([parked]));
        await expect(counter).toHaveAttribute('data-selected', '0');
        await expect(counter).toHaveAttribute('data-parked', '1');
        await expect(page.getByTestId('risk-asset-set-empty')).toBeVisible();

        // …and inverting again brings exactly them back.
        await page.getByTestId('risk-bulk-invert').click();
        await expect.poll(selection, {message: 'a second `invert` must restore exactly what the first took out'}).toBe(everything);
        await expect(counter).toHaveAttribute('data-selected', String(admitted.length));

        // `none` is total: it empties the selection, the parked asset included —
        // "deselect all" leaving a chip behind would be a button that lies.
        await page.getByTestId('risk-bulk-none').click();
        await expect(chips).toHaveCount(0);
        await expect(counter).toHaveAttribute('data-selected', '0');
        await expect(counter).toHaveAttribute('data-parked', '0');
        await expect(page.getByTestId('risk-parked-note')).toHaveCount(0);
        await expect(page.getByTestId('risk-asset-set-empty')).toBeVisible();

        // Nothing to restore: the verdicts are this test's own routes, and the
        // selection is per-context `localStorage`. No database row was touched.
    });

    test('a filter keeps its own option clickable and clears back', async ({page}) => {
        await installRiskMocks(page);
        await openAssetGlobalRisk(page);

        // The filters live in the "+" now, and narrow its list: the page's assets not
        // selected yet. Emptied first, so the list is the whole catalogue — which,
        // with every asset admitted, is exactly the candidate set the counter
        // publishes: two sources agreeing on the unfiltered size before any filter is
        // touched.
        await page.getByTestId('risk-bulk-none').click();
        await expect(page.getByTestId(/^risk-selected-asset-\d+$/)).toHaveCount(0);
        const unfiltered = (await selectionCounts(page)).total;
        await openPicker(page);
        const rows = pickerRows(page);
        await expect(rows, 'with nothing selected and nothing ruled out, the "+" must list every candidate').toHaveCount(unfiltered);

        await openFilterMenu(page, 'currency');
        const currencyOptions = filterOptions(page, 'currency');
        await expect(currencyOptions.first()).toBeVisible();
        const currencyCount = await currencyOptions.count();

        const {testId: typeFilter, candidates, partitionSum, options} = await chooseTypeFilter(page);
        const typeOptions = filterOptions(page, 'type');
        const option = page.getByTestId(typeFilter);

        // An inequality is the wrong oracle here. `candidates` is read back from the
        // same list the assertion then checks, so a filter wired to nothing gives
        // `candidates === unfiltered`, satisfies "narrowed or equal", and is green.
        //
        // An asset has exactly one type, and the options are derived from the whole
        // catalogue, so the type filters *partition* the list: applied one at a time
        // their rows must sum back to the unfiltered list. A dead filter returns the
        // full list every time and sums to `options × unfiltered` instead.
        expect(partitionSum, 'type filters must partition the list, not each return everything').toBe(unfiltered);
        expect(options, 'with a single type present the partition check cannot discriminate').toBeGreaterThan(1);
        expect(candidates, 'the chosen filter must be a strict subset for the checks below to mean anything').toBeLessThan(unfiltered);

        await option.click();
        await expect(option).toHaveAttribute('aria-pressed', 'true');

        // The guard against `problems/datatable-filter-options-disappear`: deriving
        // the options from the *filtered* result is how the option that applies a
        // filter vanishes the moment it is applied, leaving a filter with no way
        // back. Every option must survive, the pressed one above all.
        await expect(typeOptions).toHaveCount(options);
        await expect(option).toBeVisible();
        await expect(option).toBeEnabled();

        // Exact, and retried: counting one flush early would return the *unfiltered*
        // list, which satisfies a "narrowed" inequality and turns a dead filter into
        // a green.
        await expect(rows).toHaveCount(candidates);

        // The other menu keeps every value too — and opening it, which closes this one
        // by itself, keeps this one's filter.
        await openFilterMenu(page, 'currency');
        await expect(currencyOptions).toHaveCount(currencyCount);
        await expect(rows).toHaveCount(candidates);

        // Switched off by the very same control…
        await openFilterMenu(page, 'type');
        await option.click();
        await expect(option).toHaveAttribute('aria-pressed', 'false');
        await expect(rows).toHaveCount(unfiltered);

        // …by its menu's own "clear", which only exists while one of its values is on…
        const menuClear = page.getByTestId('risk-asset-add-filter-type-clear');
        const clear = addPanel(page).getByTestId('risk-asset-add-filters-clear');
        await expect(menuClear).toHaveCount(0);
        await expect(clear).toHaveCount(0);
        await option.click();
        await expect(option).toHaveAttribute('aria-pressed', 'true');
        await expect(menuClear).toBeVisible();
        await menuClear.click();
        await expect(menuClear).toHaveCount(0);
        await expect(option).toHaveAttribute('aria-pressed', 'false');
        await expect(rows).toHaveCount(unfiltered);

        // …and by "clear filters", which only exists while a filter is on. It sits
        // beside the menus and is pressed with the Type menu still open, the way a
        // user reaches it: one press has to do it.
        await option.click();
        await expect(option).toHaveAttribute('aria-pressed', 'true');
        await expect(clear).toBeVisible();
        await clear.click();
        await expect(clear).toHaveCount(0);
        await expect(rows).toHaveCount(unfiltered);
        await openFilterMenu(page, 'type');
        await expect(option).toHaveAttribute('aria-pressed', 'false');
    });

    test('one press on the currency menu opens it, even with the type menu hanging below the fold and the page scrolled into it', async ({page}) => {
        // The lost click, as it was measured: the Type menu open and reaching below
        // the viewport, the page scrolled to one of its options, one press on the
        // Currency button. `LabPopover` (now `SelectPopover`) used to close a menu on the `pointerdown` of
        // a press outside it, so the Type menu went before the press was over; the
        // page, now shorter, scrolled back; the `pointerup` of the same press landed
        // on whatever slid under the pointer, and no click reached the Currency
        // button. It closes on the completed click now, and this test keeps it there.
        // The press is made here rather than through `openFilterMenu`, so that a red
        // can say where it landed.
        await page.setViewportSize(SHORT_VIEWPORT);
        await installRiskMocks(page);
        await openAssetGlobalRisk(page);

        // Closing the menu shortens the page only if the page ends where the menu
        // does. Two things reach lower otherwise, and each is moved out of the way
        // through the UI: the sections, which an empty selection unmounts, and the
        // "+" list, which a search matching nothing reduces to its empty state. How
        // the list got short is not the defect — a type filter on a small type does
        // it too — but only the search does it whatever the seed holds.
        await page.getByTestId('risk-bulk-none').click();
        await expect(page.getByTestId(/^risk-selected-asset-\d+$/)).toHaveCount(0);
        await expect(page.getByTestId('risk-asset-set-empty')).toBeVisible();
        await openPicker(page);
        const panel = addPanel(page);
        const search = panel.getByTestId('risk-asset-add-search');
        await search.fill(NO_ASSET_QUERY);
        await expect(search).toHaveValue(NO_ASSET_QUERY);
        await expect(pickerRows(page), 'no asset may answer the search, or the "+" list stays long').toHaveCount(0);
        await expect(panel.getByTestId('risk-asset-add-empty')).toBeVisible();

        const typeButton = panel.getByTestId('risk-asset-add-filter-type-button');
        const typeMenu = page.getByTestId('risk-asset-add-filter-type-panel');
        const currencyButton = panel.getByTestId('risk-asset-add-filter-currency-button');
        const currencyMenu = page.getByTestId('risk-asset-add-filter-currency-panel');

        // The Type menu, opened through its own button…
        await typeButton.click();
        await expect(typeMenu).toBeVisible();
        await expect(typeButton).toHaveAttribute('aria-expanded', 'true');
        await expect(currencyButton).toHaveAttribute('aria-expanded', 'false');
        await expect(currencyMenu).toHaveCount(0);
        const typeOptions = filterOptions(page, 'type');
        await expect(typeOptions.first()).toBeVisible();

        // …reaching below the viewport…
        const menuBox = await typeMenu.boundingBox();
        expect(menuBox, 'the open Type menu must have a box').not.toBeNull();
        expect(menuBox!.y + menuBox!.height, `the Type menu must reach below the ${SHORT_VIEWPORT.height}px viewport`).toBeGreaterThan(SHORT_VIEWPORT.height);

        // …and the page scrolled to its lowest option, which is how a user reaches it.
        // Chosen by where it is drawn, the one property this step needs.
        const lowest = await typeOptions.evaluateAll((nodes) => nodes.map((node) => ({testId: node.getAttribute('data-testid') ?? '', bottom: node.getBoundingClientRect().bottom})).reduce((low, entry) => (entry.bottom > low.bottom ? entry : low)));
        const option = page.getByTestId(lowest.testId);
        await option.scrollIntoViewIfNeeded();
        await expect(option).toBeInViewport({ratio: 1});
        // The press is made where the button is drawn, so it has to be on screen in
        // full: a click that first scrolled to it would undo the scroll above.
        await expect(currencyButton).toBeInViewport({ratio: 1});

        // The strip only the open menu makes, which closing it takes away. It must be
        // taller than the button the press lands on, or the page could scroll back and
        // still leave the button under the pointer — a press that proved nothing.
        const {overhang, scrollY} = await typeMenuOverhang(page);
        const buttonBox = await currencyButton.boundingBox();
        expect(buttonBox, 'the Currency button must have a box').not.toBeNull();
        expect(scrollY, 'reaching the option must have scrolled the page').toBeGreaterThan(0);
        expect(overhang, `the page must be scrolled into the strip only the open Type menu makes, by more than the ${Math.round(buttonBox!.height)}px the Currency button is tall`).toBeGreaterThan(buttonBox!.height);

        // One real press on the Currency button — the pointer moved over it, pressed
        // and released through the browser's input pipeline, not a dispatched event.
        const pressed = await recordNextPress(page);
        await currencyButton.click();
        const evidence = await pressed();

        await expect(currencyMenu, `one press on the Currency button must open its menu (${evidence})`).toBeVisible();
        await expect(currencyButton, `the Currency button must report its menu open (${evidence})`).toHaveAttribute('aria-expanded', 'true');
        await expect(typeMenu, 'the same press closes the Type menu').toHaveCount(0);
        await expect(typeButton).toHaveAttribute('aria-expanded', 'false');

        // Nothing to restore: the viewport, the routes and the emptied selection all
        // belong to this browser context. No database row was touched.
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
        const byName = page.getByTestId('risk-correlation-ordering-name');

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
        expect(adjacentInOrder(matrix, twins), 'the twins are deliberately apart in the payload').toBe(false);
        expect(adjacentInOrder(clustered, twins), 'similarity must put the twin beside its partner').toBe(true);

        // "By name" promises the order of the names on screen, so the expectation is
        // built from what the page shows. Each chip carries the display name the
        // heatmap labels the same asset with — both read the page's asset list — and
        // they are collated as the product promises (letters regardless of case and
        // accent, numbers as numbers, ties by id) in the page's own locale.
        const shownNames = new Map<number, string>();
        for (const assetId of matrix) shownNames.set(assetId, (await page.getByTestId(`risk-selected-asset-${assetId}`).innerText()).trim());
        const pageLocale = await page.evaluate(() => new Intl.Collator().resolvedOptions().locale);
        const collator = new Intl.Collator(pageLocale, {sensitivity: 'base', numeric: true});
        const alphabetical = [...matrix].sort((left, right) => collator.compare(shownNames.get(left) ?? '', shownNames.get(right) ?? '') || left - right);
        // 🔴 The precondition that gives the assertion below its teeth. The button
        // used to order by id — the canonical payload order — while saying "by name".
        // A selection whose names happen to be alphabetical in id order draws the
        // same matrix both ways, and this test would stay green through the very
        // defect it exists to catch.
        expect(alphabetical, `the names on screen must not already be in id order, or by-name and by-id are the same picture: ${matrix.map((assetId) => `${assetId}=${shownNames.get(assetId)}`).join(', ')}`).not.toEqual(matrix);

        await byName.click();
        await expect(byName).toHaveAttribute('aria-pressed', 'true');
        await expect(similarity).toHaveAttribute('aria-pressed', 'false');
        const named = await drawnOrder();
        expect(named, 'by name must order the matrix by the names on screen, not by id').toEqual(alphabetical);
        // Reordering is a view choice: it may move rows, never invent or drop one.
        expect([...named].sort((left, right) => left - right)).toEqual([...clustered].sort((left, right) => left - right));
        for (const testId of findings) await expect(page.getByTestId(testId)).toBeVisible();
        await expectChartCanvas(page, 'risk-correlation-heatmap', 20_000);

        await similarity.click();
        await expect(similarity).toHaveAttribute('aria-pressed', 'true');
        await expect(byName).toHaveAttribute('aria-pressed', 'false');
        expect(await drawnOrder(), 'going back must restore the clustered order, not a third one').toEqual(clustered);
        for (const testId of findings) await expect(page.getByTestId(testId)).toBeVisible();
        await expectChartCanvas(page, 'risk-correlation-heatmap', 20_000);
    });

    /**
     * The three grouping orderings are inputs the lab loads, not features the
     * heatmap has: types from the page's asset list, sectors and areas from one
     * read of the assets' stored metadata (see {@link plantAssetMetadata}). This
     * test pins where each comes from — the behaviour the extraction of that
     * loading (K11) must leave exactly as it is.
     *
     * The failure is provoked on a *changed* selection, after a read that
     * succeeded, rather than on a fresh page. A fresh page starts with empty maps,
     * so a failed read that forgot to clear them would pass there unseen; here the
     * sector and area orderings are on screen when the read fails, and they must
     * go. The type ordering must stay, because its map never came from that read.
     *
     * And "by sector" is the ordering in use when it goes. An ordering that is no
     * longer offered cannot stay in charge behind a row of unpressed buttons: the
     * matrix falls back to its initial ordering — similarity — presses it and draws
     * it, the very order it drew for the same assets at the start. The fallback
     * only stands in: the moment "by sector" is offered again, the user's choice
     * applies again.
     */
    test("the matrix offers type, sector and area orderings from the assets' stored metadata, and loses only those when the metadata read fails", async ({page}) => {
        // Four selections, each read and drawn, and the "+" once or twice in one
        // page: more than the default budget, no more than the neighbours' 45 s.
        test.setTimeout(45_000);
        await installRiskMocks(page);
        const metadata = await plantAssetMetadata(page);
        await openAssetGlobalRisk(page);
        await ensureSelectionAtLeast(page, MINIMUM_SELECTION);

        // Every chip is analysed — the stubbed engine admits them all — so these are
        // the ids the read asks about, in the rank order the planted groups follow.
        const selection = [...(await chipIds(page))].sort((left, right) => left - right);
        const matrix = selection.slice(0, MATRIX_LIMIT);
        expect(matrix.length, 'the two planted partitions only cross from four assets up').toBeGreaterThanOrEqual(MINIMUM_SELECTION);
        const sectorOf = (assetId: number): string => {
            const rank = selection.indexOf(assetId);
            return rank < 0 ? `unselected #${assetId}` : plantedSector(rank).dominant;
        };
        expect(new Set(matrix.map(sectorOf)).size, 'the matrix must hold both planted sectors, or "grouped" is one block and proves nothing').toBe(PLANTED_SECTORS.length);

        const panel = page.getByTestId('asset-global-risk-panel');
        const ordering = (mode: string) => panel.getByTestId(`risk-correlation-ordering-${mode}`);
        /** The first read answered `answer` for exactly `assetIds` among those after the `since`-th: sample the length before acting. */
        const readAfter = (since: number, answer: MetadataRead['answer'], assetIds: readonly number[]) => metadata.reads.slice(since).find((read) => read.answer === answer && scopeKey(read.assetIds) === scopeKey(assetIds));
        const readOf = (answer: MetadataRead['answer'], assetIds: readonly number[]) => readAfter(0, answer, assetIds);
        /** Exactly one ordering button is pressed, and it is `mode`'s. Both halves retry. */
        const expectOnlyPressed = async (mode: string, why: string) => {
            const pressed = panel.locator('[data-testid^="risk-correlation-ordering-"][aria-pressed="true"]');
            await expect(pressed, why).toHaveCount(1);
            await expect(pressed, why).toHaveAttribute('data-testid', `risk-correlation-ordering-${mode}`);
        };

        await waitForRiskCatalog(page);
        await expect.poll(() => readOf('planted', selection) !== undefined, {timeout: 15_000, message: 'the lab must read the stored metadata of exactly the assets it analyses'}).toBe(true);
        const answered = readOf('planted', selection);
        expect(answered?.problem ?? null, 'the planted answer must be one the client accepts, or the maps stay empty for a reason this test did not choose').toBeNull();
        expect(scopeKey(answered?.rowIds ?? []), 'every selected asset must come back with its planted classification').toBe(scopeKey(selection));

        // The two orderings the heatmap always has, then the three the inputs open.
        await expect(ordering('similarity')).toBeVisible({timeout: 20_000});
        await expect(ordering('similarity')).toHaveAttribute('aria-pressed', 'true');
        await expect(ordering('name')).toBeVisible();
        await expect(ordering('type')).toBeVisible();
        await expect(ordering('sector')).toBeVisible({timeout: 10_000});
        await expect(ordering('region')).toBeVisible();
        // The composition rows read the same two maps, whatever the ordering.
        await expect(panel.getByTestId('risk-correlation-groups-sector')).toBeVisible();
        await expect(panel.getByTestId('risk-correlation-groups-region')).toBeVisible();

        // 🔴 The precondition that gives the click its teeth: were similarity to draw
        // the planted sectors as blocks already, a button that only toggled its own
        // pressed state would pass the grouping assertion below.
        await expect.poll(async () => scopeKey(await drawnAssetOrder(page)), {timeout: 20_000, message: 'the heatmap must draw the selection this test holds'}).toBe(scopeKey(matrix));
        const clustered = await drawnAssetOrder(page);
        expect(groupedBy(clustered, sectorOf), `similarity must not already draw the planted sectors as blocks: ${clustered.map((assetId) => `${assetId}=${sectorOf(assetId)}`).join(', ')}`).toBe(false);

        await ordering('sector').click();
        await expect(ordering('sector')).toHaveAttribute('aria-pressed', 'true');
        await expect(ordering('similarity')).toHaveAttribute('aria-pressed', 'false');
        await expect.poll(async () => groupedBy(await drawnAssetOrder(page), sectorOf), {message: 'by sector must draw each planted sector as one block — the map keyed by asset id, and the sector one, not the area one'}).toBe(true);
        expect(scopeKey(await drawnAssetOrder(page)), 'grouping is a view choice: it may move rows, never drop one').toBe(scopeKey(matrix));

        // ── The read fails. Every read from here on is a 500; a smaller selection
        // makes the lab ask again. The largest id of the matrix goes, so the matrix
        // itself changes and its redraw is something to wait for.
        const beforeFailure = metadata.reads.length;
        metadata.failFromNow();
        const removed = Math.max(...matrix);
        const remaining = selection.filter((assetId) => assetId !== removed);
        await page.getByTestId(`risk-remove-asset-${removed}`).click();
        await expect(page.getByTestId(`risk-selected-asset-${removed}`)).toHaveCount(0);
        await expect.poll(() => readAfter(beforeFailure, 'failed', remaining) !== undefined, {timeout: 15_000, message: 'a changed selection must be read again'}).toBe(true);
        await expect.poll(async () => scopeKey(await drawnAssetOrder(page)), {timeout: 20_000, message: 'the heatmap must redraw for the smaller selection'}).toBe(scopeKey(remaining.slice(0, MATRIX_LIMIT)));

        // Presence before absence: the orderings the page supplies are on screen, so
        // the two missing ones are missing from a rendered heatmap, not from one
        // that has not drawn yet.
        await expect(ordering('similarity')).toBeVisible();
        await expect(ordering('name')).toBeVisible();
        await expect(ordering('type')).toBeVisible();
        await expect(ordering('sector')).toHaveCount(0);
        await expect(ordering('region')).toHaveCount(0);
        await expect(panel.getByTestId('risk-correlation-groups')).toHaveCount(0);

        // 🔴 "By sector" was the ordering in use, and it is no longer offered. The
        // matrix must not keep ordering by it behind a row of unpressed buttons.
        await expectOnlyPressed('similarity', 'with "by sector" gone, the matrix falls back to similarity and presses it');

        // ── The same assets as phase 1, the read still failing: the fallback must
        // draw the very order similarity drew for them at the start. A pressed
        // button over some other order would be the same defect, better hidden.
        const beforeReAdd = metadata.reads.length;
        await addThroughPicker(page, [removed]);
        await expect.poll(() => readAfter(beforeReAdd, 'failed', selection) !== undefined, {timeout: 15_000, message: 'the restored selection must be read again'}).toBe(true);
        await expect.poll(async () => scopeKey(await drawnAssetOrder(page)), {timeout: 20_000, message: 'the heatmap must redraw for the restored selection'}).toBe(scopeKey(matrix));
        await expect(ordering('sector')).toHaveCount(0);
        await expectOnlyPressed('similarity', 'the fallback holds while "by sector" stays unavailable');
        await expect.poll(() => drawnAssetOrder(page), {message: 'the fallback must draw the similarity order phase 1 drew for these very assets'}).toEqual(clustered);

        // ── The read answers again: "by sector" is back, and the user's choice with
        // it. The fallback stood in for the choice; it did not take it away.
        const beforeRecovery = metadata.reads.length;
        metadata.answerFromNow();
        await page.getByTestId(`risk-remove-asset-${removed}`).click();
        await expect(page.getByTestId(`risk-selected-asset-${removed}`)).toHaveCount(0);
        await expect.poll(() => readAfter(beforeRecovery, 'planted', remaining) !== undefined, {timeout: 15_000, message: 'a changed selection must be read again'}).toBe(true);
        await expect(ordering('sector')).toBeVisible({timeout: 10_000});
        await expectOnlyPressed('sector', 'once "by sector" is offered again, the choice the user made applies again');
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
     * (a) + (b) — one request per level, and one row per selected asset.
     *
     * The two belong together because the second is only meaningful given the
     * first: L1° is a *transposition* of a joint measurement, so every row has to
     * come from the same prepared calendar. Split across requests the rows would
     * still line up on screen and would no longer be comparable.
     *
     * One request per *level*, never one for both (the developer's decision of
     * 02/10/2026): L1° asks for {@link LOSS_LEVEL_CODES} and L3° for
     * {@link PAID_LEVEL_CODES}, each in a request of its own, so that a benchmark —
     * which the engine prepares with the scope of whichever request carries it —
     * can never move L1°'s window.
     *
     * Red until the levels ask apart: today one request carries both levels'
     * analytics, and the shape check of ① names it.
     */
    test('L1° and L3° each ask for their per-asset analytics in one request of their own, never mixed, and L1° gives every selected asset a row', async ({page}) => {
        const requests = await installRiskMocks(page);
        await openAssetGlobalRisk(page);
        await ensureSelectionAtLeast(page, MINIMUM_SELECTION);
        await waitForRiskCatalog(page);
        await waitForLossTable(page);

        // ① ONE REQUEST PER LEVEL. `service.py:170` prepares the joint series once
        // per request, before the analytic loop, so a level split across requests
        // would pay for one preparation per piece and — the part that reaches the
        // reader — would draw one table, or one chart, from several calendars.
        // `queryRisk` caches on the canonical request, so "they were asked
        // together" is observable exactly here, on the wire, and nowhere else.
        //
        // And never one request for both levels: the engine prepares a request's
        // comparison asset with its scope (`service.py:183-196`), so a level riding
        // with L3°'s benchmark would be measured on the benchmark's calendar too —
        // the «Partial» the developer saw on L1°.
        //
        // Scoped to the selection the page is showing: the laboratory legitimately
        // puts more than one asset-set historical request on the wire — the
        // correlation and replay sections build their own controllers without
        // `includeAssetSetLevels`, so their wave is `[correlation]` — and growing
        // the selection above adds a second scope. What must be true is that no
        // level is ever split or mixed, not that the page makes a number of calls.
        const selected = await chipIds(page);
        expect(selected.length, 'the transposition needs more than one instrument to be a comparison').toBeGreaterThanOrEqual(MINIMUM_SELECTION);
        await expect.poll(() => lossRequestsFor(requests, selected).length, {timeout: 20_000, message: "L1°'s request must be asked for exactly once for the selection on screen"}).toBe(1);
        await expect.poll(() => paidRequestsFor(requests, selected).length, {timeout: 20_000, message: "L3°'s request must be asked for exactly once for the selection on screen"}).toBe(1);

        // …and no request anywhere carried a *part* of a level, or parts of both.
        // The counts above would still pass if a stray request had smuggled one
        // code out on its own, or if one request answered for both levels — it
        // counts as each level's; this is what forbids both outright.
        const levelShapes = [[...LOSS_LEVEL_CODES].sort(), [...PAID_UNCONDITIONAL_CODES].sort()];
        for (const request of assetSetHistoricalRequests(requests)) {
            const carried = ASSET_SET_LEVEL_CODES.filter((code) => codesOf(request).has(code));
            if (carried.length === 0) continue;
            const sliced = `a request may carry one level's whole wave or none of it — never a slice, never both levels — and this one carried ${JSON.stringify(carried)}`;
            expect(levelShapes, sliced).toContainEqual([...carried].sort());
        }

        const loss = lossRequestsFor(requests, selected)[0];
        const paid = paidRequestsFor(requests, selected)[0];
        for (const code of LOSS_LEVEL_CODES) {
            expect([...codesOf(loss)], `${code} must travel with the rest of L1°'s wave`).toContain(code);
        }
        // Only two of L3°'s three ride unconditionally: `asset_set_comparison`
        // needs a benchmark, and this context has none. Asserting all three here
        // would fail for the right reason on the wrong page — the benchmark branch
        // has its own tests below.
        for (const code of PAID_UNCONDITIONAL_CODES) {
            expect([...codesOf(paid)], `${code} must travel with the rest of L3°'s wave`).toContain(code);
        }
        expect([...codesOf(paid)], 'no benchmark is chosen in this context, so the comparison must not have been asked for').not.toContain('asset_set_comparison');

        // ② THE TWO HORIZONS ARE TWO INSTANCES, NOT TWO REQUESTS. They share an
        // analytic code, so only the instance id keeps the bad day and the bad
        // month apart; a stub that resolved by code would answer both with
        // whichever arrived first and the two columns would silently become one.
        const varInstances = loss.analytics.filter((analytic) => analytic.analytic_code === 'asset_set_var');
        expect(varInstances.map((analytic) => analytic.instance_id).sort()).toEqual(['base-historical-asset_set_var', 'base-historical-asset_set_var-monthly']);
        expect(
            varInstances.map((analytic) => Number(analytic.parameters?.horizon_days)).sort((left, right) => left - right),
            'the bad month is a second measurement over a compounded horizon, never the bad day scaled',
        ).toEqual([1, 30]);

        // ③ THE TRANSPOSITION. One row per *selected* asset — asserted against the
        // chips the page is actually showing, because the opening selection is
        // seed data this test does not own. A literal here would be a count of
        // somebody else's fixture.
        await expect(lossTable(page)).toHaveAttribute('data-row-count', String(selected.length));
        await expect(lossRows(page)).toHaveCount(selected.length);
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

        // ⑥ …and neither does the lab. Its one notice reads the correlation section's
        // answer and L3°'s as well as L1°'s, so all three frames must have drawn theirs
        // before its absence means "nothing came back partial, nothing carries a
        // warning" rather than "not every answer has landed".
        await waitForNoticeFrames(page);
        await expect(labNotice(page), 'the wave came back whole and the lab still shows a notice: it calls something partial when nothing is').toHaveCount(0);
        // Nor its data-quality banner (decision B), behind the same barriers: no answer the stub
        // sent carries an issue (`dataQuality()` is clean unless a test plants one), and the banner
        // draws nothing without issues. Its positive control is (e) below, which plants issues and
        // demands the banner: that is what keeps this absence from passing about a banner that was
        // never built.
        await expect(labBanner(page), 'no answer carries a data-quality issue and the lab still draws a banner: it reports a problem nobody sent').toHaveCount(0);
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
     *
     * Why it is blank is said once, above the frames (the developer's decision of
     * 05/10/2026, the Dashboard's pattern): the exclusion degrades every result of
     * every request, so the correlation section, L1° and L3° all draw `partial`
     * results carrying the same warning, and the lab's one notice — after the
     * selection card, before the matrix — names them and words the warning once.
     * The frames keep only what did not come back at all, and here nothing did.
     */
    test("a selected asset the backend could not measure keeps its row, with the reason in the lab's notice", async ({page}) => {
        const options: RiskStubOptions = {dropLastAsset: true};
        const requests = await installRiskMocks(page, options);
        await openAssetGlobalRisk(page);
        await ensureSelectionAtLeast(page, MINIMUM_SELECTION);
        await waitForRiskCatalog(page);
        await waitForLossTable(page);

        // Which asset went missing is read from the request the stub answered —
        // L1°'s, the one this table is drawn from — not assumed from the chips: the
        // client canonicalises `asset_ids` ascending before sending, and the chips
        // render in name order, so guessing here would be guessing at two orderings
        // at once.
        const selected = await chipIds(page);
        await expect.poll(() => lossRequestsFor(requests, selected).length, {timeout: 20_000, message: "L1°'s request must have been asked for the selection on screen, exactly once"}).toBe(1);
        const loss = lossRequestsFor(requests, selected)[0];
        const scope = loss.scope.kind === ASSET_SET_SCOPE ? loss.scope.asset_ids : [];
        expect(scope.length, 'dropping one asset needs at least two to have been asked about').toBeGreaterThanOrEqual(2);
        const unmeasured = scope[scope.length - 1];
        const measured = scope.slice(0, -1);

        // THE RULE. The row count follows the *selection*, which still holds every
        // asset — including the one no analytic answered for.
        expect(selected, 'the unmeasured asset is still selected; that is the whole premise').toContain(unmeasured);
        await expect(lossTable(page)).toHaveAttribute('data-row-count', String(selected.length));
        await expect(lossRows(page)).toHaveCount(selected.length);
        await expect(lossRow(page, unmeasured), 'the asset nobody could measure must still have a row of its own').toHaveCount(1);

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

        // AND THE PAGE SAYS WHY — ONCE, ABOVE THE FRAMES. An exclusion degrades every
        // analytic of every request: each result the correlation section, L1° and L3°
        // draw comes back `partial` under the same `assets_excluded` warning — one
        // excluded asset, one reason, one sentence. How many is read off the answers
        // the stub sent for the selection on screen, never counted here by hand.
        const expected = labNoticeFor(await noticeRequestsFor(requests, selected), options);
        expect(expected.partial, 'premise: dropLastAsset answered none of the results the notice reads partial').toBeGreaterThan(0);
        expect(expected.excluded, 'premise: dropLastAsset planted the exclusion warning on none of the results the notice reads').toBeGreaterThan(0);
        expect(expected.sentences, 'premise: one excluded asset, one reason, the same scope in all three requests — the warnings make one sentence').toBe(1);
        await waitForNoticeFrames(page);

        const notice = labNotice(page);
        await expect(notice, 'the lab draws partial results and says nothing of them: its one notice is missing').toBeVisible();
        await expect.poll(() => partialNoticePlacement(page), {message: 'the notice must sit after the selection card and before the correlation section, inside neither: above every frame it speaks for'}).toBe('between');
        await expect(notice, `the notice names every partial result the three frames draw: ${expected.partial} in the stub's answers`).toHaveAttribute('data-partial-count', String(expected.partial));
        await expect(notice.getByTestId('risk-partial-measurements'), 'one entry per partial measurement, by instance: the two VaR horizons are two').toHaveAttribute('data-count', String(expected.partial));

        const reasons = notice.getByTestId('risk-partial-reasons');
        await expect(reasons, 'one distinct sentence, however many results carried it').toHaveAttribute('data-count', String(expected.sentences));
        const reason = reasons.getByTestId('risk-partial-reason');
        await expect(reason).toHaveCount(expected.sentences);
        await expect(reason, `its arity is published rather than drawn ${expected.excluded} times: every result carrying the exclusion counts once`).toHaveAttribute('data-occurrences', String(expected.excluded));

        // …in the reader's language. The warning arrives as its reason's key and
        // values, with the backend's English `message` only as the fallback. So the
        // sentence on screen must be the one worded from the key. That is proved by
        // shape, never by wording: it names the asset the warning planted, a name
        // only the formatter can have put there; it is not the fallback; and no ICU
        // brace was left unformatted.
        await expect(reason, "the warning's names never reached the formatter: the reason was not worded from its key").toContainText(unnamedAsset(unmeasured));
        const sentence = ((await reason.textContent()) ?? '').trim();
        expect(sentence, "the reason is the backend's English fallback, not the sentence of its key").not.toBe(EXCLUDED_WARNING_MESSAGE);
        expect(sentence, 'the reason carries an unformatted ICU placeholder').not.toContain('{');

        // …AND NOWHERE ELSE. Every frame has drawn its answer (the barrier above) and
        // the notice says it all, so these absences say the disclosure moved, not that
        // a frame was slow: L1°'s frame (`risk-asset-set-loss`) lists no partial
        // measurement and repeats no sentence — nor do the correlation section's and
        // L3°'s, or the reader would meet one exclusion four times: in the notice,
        // then once per frame.
        for (const frame of NOTICE_FRAMES) {
            const section = page.getByTestId('asset-global-risk-panel').getByTestId(frame);
            await expect(section.getByTestId(`${frame}-health`), `${frame} still lists the partial results in its frame: the notice above names them, once`).toHaveCount(0);
            await expect(section.getByTestId(`${frame}-reasons`), `${frame} still repeats the exclusion's sentence in its frame: the notice above says it, once`).toHaveCount(0);
        }

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
     *
     * What did not come back at all stays in its frame — `levelErrorHealth` keeps
     * `unavailable` under the level, as the Dashboard keeps it — and the lab's one
     * notice, which speaks for partial results and warnings, has nothing to say.
     */
    test('a window too short for four of the five analytics is disclosed, not blanked', async ({page}) => {
        const options: RiskStubOptions = {shortWindow: true};
        const requests = await installRiskMocks(page, options);
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
        // warnings at all, so there is no sentence to word anywhere — not in this
        // frame, which words none since the lab's notice took them over, and not in
        // that notice either (below). The two assertions that precede this one are
        // its presence barrier — without them "no reasons" would also be true of a
        // section that had not rendered.
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

        // AND NO NOTICE, as the stub makes it. The gate answers the four it stops
        // `unavailable` with no warning (`_unavailable` takes none), and lets the
        // drawdown and the matrix through `ok`, unwarned: nothing the lab draws is
        // partial or carries a sentence. Read off the answers the stub sent rather
        // than assumed — a short window that one day came back warned would turn the
        // premise red, by name, instead of leaving the absence below to go stale.
        const expected = labNoticeFor(await noticeRequestsFor(requests, selected), options);
        expect(expected.partial, 'premise: a short window answered a result the notice reads partial').toBe(0);
        expect(expected.sentences, 'premise: a short window planted a warning on a result the notice reads').toBe(0);
        await waitForNoticeFrames(page);
        await expect(labNotice(page), "nothing the lab draws is partial or warned, and the lab shows a notice anyway: what did not come back at all is its frame's to say").toHaveCount(0);
    });

    /**
     * (e) — the lab's data-quality banner (decision B, the developer, 05/10/2026).
     *
     * Since D373 the backend gives an asset set's reports the banner's issues, one per category
     * (`service.py::_data_quality_issues`): stale prices offer a sync, a missing price opens the
     * asset, a pair with no route asks for one. Each section holds its own controllers, each
     * controller merges the issues of every answer it holds (`mergeQualityIssues`), and the panel
     * merges the sections' in page order — the correlation section, L1°, L3°, the replay — by the
     * same rule into one `DataQualityBanner`, drawn above its one notice. So the reader meets one item
     * per code and group, naming every asset any section named, in the order they first appeared;
     * and the banner's actions are the lab's (`labQualityAction`): a sync opens the lab's own sync,
     * the rest navigate.
     *
     * What is planted, and why there, is {@link labQualityIssues}; the cast is {@link qualityCast},
     * read off the selection on screen. `dropLastAsset` draws the notice, so the banner's place above
     * it is checked, not skipped.
     *
     * Red until the panel draws the banner: today it draws none, and the first assertion on it fails.
     */
    test("the lab's data-quality banner: one item per code and group across the sections, above the notice, its Sync opening the lab's own sync", async ({page}) => {
        // One replay, a modal cycle and a navigation: the budget pays for the work, and every wait
        // below is still a barrier on a published state.
        test.setTimeout(60_000);
        const options: RiskStubOptions = {dropLastAsset: true, qualityIssues: labQualityIssues};
        const requests = await installRiskMocks(page, options);
        // Nothing here runs a sync. Should something, no provider is reached, and the calls are counted.
        const syncCalls = await installSyncMocks(page);
        await openAssetGlobalRisk(page);
        // Three assets for the cast, and a fourth for `dropLastAsset` to leave out — the highest id, so
        // never one of the cast, which takes the three lowest.
        await ensureSelectionAtLeast(page, MINIMUM_SELECTION);
        await waitForRiskCatalog(page);

        // The cast, from the selection on screen: the scope every section asks about, so the very ids
        // the stub planted — it reads them off each request's own scope, through the same function.
        const selected = await chipIds(page);
        const cast = qualityCast(selected);
        if (cast === null) throw new Error(`The data-quality case needs three selected assets and the selection holds ${selected.length}. Check populate_mock_data.py.`);

        // Every section feeding the notice has asked about this selection and drawn its answer, and the
        // notice the banner must precede is on screen: what follows is about the banner, not about an
        // answer still on its way.
        const sent = await noticeRequestsFor(requests, selected);
        await waitForLossTable(page);
        await waitForNoticeFrames(page);
        await expect(labNotice(page), 'premise: dropLastAsset answered partial results and the lab draws no notice, so the banner would have nothing to be above').toBeVisible();

        // ── one item per code and group, across the sections ─────────────────
        const banner = labBanner(page);
        await expect(banner, 'the sections hold data-quality issues and the lab draws no banner: the reader is never told').toBeVisible({timeout: 10_000});
        const toggle = banner.getByTestId('data-quality-toggle');
        // Asked, never pressed blind: the banner is born folded, and a press on an open one folds it.
        if ((await toggle.getAttribute('aria-expanded')) !== 'true') await toggle.click();
        await expect(toggle).toHaveAttribute('aria-expanded', 'true');

        const issueRow = (code: string) => banner.getByTestId(`data-quality-issue-${code}`);
        await expect(issueRow('STALE_PRICE'), "stale prices planted in the correlation section's answer and in L3°'s must be one item").toHaveCount(1, {timeout: 10_000});
        await expect(issueRow('MISSING_PRICE'), "a missing price planted in L1°'s answer and in L3°'s must be one item").toHaveCount(1);
        // Nobody has run the replay, so the code only its own answer carries is not listed yet. Read
        // behind the two rows above, which are its presence barrier.
        await expect(issueRow('MISSING_FX_MARKET'), 'the replay has not run, and the banner already lists what only its answer carries').toHaveCount(0);

        // ── above the notice ──────────────────────────────────────────────────
        await expect.poll(() => qualityBannerPlacement(page), {message: 'the banner must follow the selection card and precede the notice and the correlation section, inside none of them'}).toBe('between');

        // ── the replay's own answer reaches it too ────────────────────────────
        await openAndRunReplay(page);
        await expect(issueRow('MISSING_FX_MARKET'), "the replay's answer carries a pair with no route and the banner does not list it: the panel does not read the replay section").toHaveCount(1, {timeout: 10_000});
        await expect(issueRow('STALE_PRICE'), "the replay's controller holds the correlation section's stale prices too (one flight): still one item").toHaveCount(1);
        await expect(issueRow('MISSING_PRICE')).toHaveCount(1);

        // ── the missing price's links: the union, by first appearance ─────────
        await expect.poll(() => replayRequestsFor(requests, selected).length, {message: 'the replay never asked about the selection on screen'}).toBeGreaterThan(0);
        const replayRun = replayRequestsFor(requests, selected).at(-1) as RiskRequest;
        // Derived from the stub's own planting, in the order the panel merges the sections: the
        // correlation section, L1°, L3°, then the replay — whose controller holds the correlation
        // section's answer as its base wave (one flight), then its own run's.
        const inPanelOrder = [...labQualityIssues('correlation', sent.correlation), ...labQualityIssues('loss', sent.loss), ...labQualityIssues('paid', sent.paid), ...labQualityIssues('correlation', sent.correlation), ...labQualityIssues('replay', replayRun)];
        const missingInOrder = idsByFirstAppearance(inPanelOrder, 'MISSING_PRICE');
        expect(missingInOrder, "premise: the planting names A in L1°'s answer and C in L3°'s, and nothing else").toEqual([cast.a, cast.c]);
        expect(cast.a, 'premise: A is the higher id, so the order below is first appearance and not id order').toBeGreaterThan(cast.c);

        const missingLinks = banner.getByTestId('data-quality-nav-assets-MISSING_PRICE');
        await expect(missingLinks).toBeVisible();
        const linkIds = () => missingLinks.getByTestId(/^data-quality-nav-asset-\d+$/).evaluateAll((nodes) => nodes.map((node) => Number((node.getAttribute('data-testid') ?? '').slice('data-quality-nav-asset-'.length))));
        await expect.poll(linkIds, {timeout: 15_000, message: `the missing price must link exactly [${missingInOrder.join(', ')}], each once: L1°'s asset, then L3°'s — by first appearance, not by id, and not L3° first`}).toEqual(missingInOrder);

        // ── its Sync: the lab's own ───────────────────────────────────────────
        // `openSync` opens only while the selection has something to sync; the toolbar's sync, which
        // reaches the same modal, is enabled exactly then — the precondition, published.
        await expect(page.getByTestId('assets-controls').getByTestId('risk-sync-button')).toBeEnabled();
        const before = page.url();
        await banner.getByTestId('data-quality-cta-STALE_PRICE').click();
        // On this page the only `page-sync-modal` is the lab's (the grid's prices-only sync is
        // `asset-sync-modal`), and the page stayed where it was: the lab's own sync, opened in place.
        const modal = page.getByTestId('page-sync-modal');
        await expect(modal, "the banner's Sync opened no sync").toBeVisible();
        expect(page.url(), "the banner's Sync left the page instead of opening the lab's own sync").toBe(before);
        await expect(page.getByTestId('asset-sync-modal'), "the banner's Sync opened the grid's prices-only sync, not the lab's").toHaveCount(0);
        // Closed as it was opened, without a run: no provider may have been asked for anything.
        await modal.getByTestId('sync-modal-close').click();
        await expect(modal).toBeHidden();
        expect(syncCalls.assets.length + syncCalls.fxPairs.length, 'the sync was opened and closed, never run, and still reached a sync endpoint').toBe(0);

        // ── a link opens its asset — last, since it leaves the page ───────────
        await missingLinks.getByTestId(`data-quality-nav-asset-${cast.a}`).click();
        await page.waitForURL((url) => url.pathname === `/assets/${cast.a}`, {timeout: 15_000});

        // Nothing to restore: every route is this page's own, and the sync stubs and the held price
        // poll stay in place on the asset page the case ends on.
    });

    /**
     * L1°'s headers explain; they do not link.
     *
     * Each value column carries its help as the tooltip of its own title — DataTable's
     * `headerTooltip` with no URL — so there is no ⓘ beside a title and no anchor in the
     * header row. The documentation lives on the section frame's manual icon, one for the
     * whole level. The previous design put a link to a theory page beside every title:
     * five anchors whose paths were assembled at runtime, which the link gate could not
     * even read.
     *
     * The tooltip's words are not read: they are translated, and the component test
     * already proves each title shows its own key's message. What only a browser can
     * prove is that resting the pointer on the title opens it.
     */
    test("L1°'s value columns carry their help as a tooltip on the title, and its header row carries no link", async ({page}) => {
        await installRiskMocks(page);
        await openAssetGlobalRisk(page);
        await waitForRiskCatalog(page);
        await waitForLossTable(page);

        // Presence first: every title is drawn, so the absences below are about a header
        // that exists rather than one that has not rendered yet.
        for (const column of ['name', ...L1_CELLS]) {
            await expect(lossTable(page).getByTestId(`dt-header-${column}`), `the ${column} title is missing from L1°'s header`).toBeVisible();
        }
        await expect(lossTable(page).locator('thead a'), "a link in L1°'s header row: the documentation belongs to the frame's manual icon").toHaveCount(0);
        await expect(lossTable(page).locator('[data-testid^="dt-header-tooltip-"]'), 'an ⓘ beside a title: the help is the title itself').toHaveCount(0);
        await expect(page.locator('[data-testid^="risk-asset-set-l1-docs-"]')).toHaveCount(0);

        // The help itself, where the pointer rests. The Tooltip opens after its own hover
        // delay, which the retrying assertion absorbs: nothing here waits on a clock.
        await lossTable(page).getByTestId('dt-sort-badDay').hover();
        const help = page.getByTestId('tooltip-content');
        await expect(help, 'resting on the bad-day title must open its help').toBeVisible();
        await expect(help, 'the help opened empty').not.toHaveText(/^\s*$/);
        await expect(help, 'the help printed its own key: the catalogue has no message for it').not.toHaveText('risk.assetSet.levels.l1.columnHelp.badDay');
        // Resting is not pressing: the column is still unsorted.
        await expect(lossTable(page).getByTestId('dt-header-badDay')).toHaveAttribute('data-sort', 'none');
    });

    /**
     * L1° sorts a column by the figure it draws.
     *
     * A loss is drawn negative, so ascending puts the largest loss first; an asset nobody
     * could measure is a blank, not a zero, and goes last whichever way the column points;
     * the third press clears the sort and gives the rows back in the selection's order —
     * the only order the system ever chooses, since the level compares and never ranks.
     *
     * The figures are this file's own ({@link INVENTED}), re-planted as a zig-zag
     * (`zigzagBadDay`) so that ascending, descending and the opening order are three
     * different orders; the blank is the asset `dropLastAsset` excludes, the state the
     * backend leaves when it cannot prepare a series. The expected orders are worked out
     * from the answer the stub sent, rebuilt through the same function that sent it.
     */
    test('L1° sorts a column by the loss it draws: the largest first, the unmeasured last both ways, and a third press restores the selection order', async ({page}) => {
        const options: RiskStubOptions = {dropLastAsset: true, zigzagBadDay: true};
        const requests = await installRiskMocks(page, options);
        await openAssetGlobalRisk(page);
        await ensureSelectionAtLeast(page, MINIMUM_SELECTION);
        await waitForRiskCatalog(page);
        await waitForLossTable(page);

        // The answer the page was given for the selection on screen, rebuilt from the
        // request it answered — L1°'s: the bad day of every measured asset, and the one left blank.
        const selected = await chipIds(page);
        await expect.poll(() => lossRequestsFor(requests, selected).length, {timeout: 20_000, message: "L1°'s request must have been asked for the selection on screen"}).toBeGreaterThan(0);
        const loss = lossRequestsFor(requests, selected)[0];
        const daily = loss.analytics.find((analytic) => analytic.analytic_code === 'asset_set_var' && Number(analytic.parameters?.horizon_days ?? 1) === 1);
        if (!daily) throw new Error("L1°'s request carries no one-day asset_set_var, so the bad day has nothing to sort.");
        const badDay = new Map(assetSetVarOutput(loss, daily, options).items.map((item): [number, number] => [item.asset_id, item.conditional_value_at_risk]));
        const {excluded} = preparedAssetIds(loss, options);
        expect(excluded, 'dropLastAsset must leave exactly one selected asset unmeasured').toHaveLength(1);
        const unmeasured = excluded[0];

        // Barrier: the answer is on screen — every row drawn, the measured ones measured and
        // the excluded one blank — before any order is read.
        await expect(lossRows(page)).toHaveCount(selected.length);
        await expect(lossTable(page).locator('[data-testid="risk-asset-set-l1-badDay"][data-measured="true"]')).toHaveCount(badDay.size);
        await expect(lossCell(page, unmeasured, 'badDay')).toHaveAttribute('data-measured', 'false');

        const opening = await lossRowAssetIds(page);
        expect(
            [...opening].sort((left, right) => left - right),
            'the rows must be the selection',
        ).toEqual([...selected].sort((left, right) => left - right));

        // The oracle, stated as the rule: the figure drawn is the loss with its sign, −CVaR,
        // so ascending is the largest CVaR first, and a blank goes last either way. Every
        // figure is distinct (`zigzagRank`), so no tie is left to the table to settle.
        const drawn = (assetId: number): number | null => {
            const cvar = badDay.get(assetId);
            return cvar === undefined ? null : -cvar;
        };
        const orderedBy = (direction: 'asc' | 'desc'): number[] =>
            [...opening].sort((left, right) => {
                const a = drawn(left);
                const b = drawn(right);
                if (a === null || b === null) return a === null ? (b === null ? 0 : 1) : -1;
                return direction === 'asc' ? a - b : b - a;
            });
        const ascending = orderedBy('asc');
        const descending = orderedBy('desc');
        const largestLoss = [...badDay.entries()].sort(([, left], [, right]) => right - left)[0][0];
        expect(ascending[0], 'the oracle itself: ascending opens on the largest loss').toBe(largestLoss);
        expect([ascending[ascending.length - 1], descending[descending.length - 1]], 'the oracle itself: the blank closes both orders').toEqual([unmeasured, unmeasured]);
        // Premise: every press must move a row, or the order read after it proves nothing.
        expect(ascending, 'premise: ascending must differ from the opening order').not.toEqual(opening);
        expect(descending, 'premise: descending must differ from the opening order, or "cleared" and "descending" would draw the same rows').not.toEqual(opening);

        const header = lossTable(page).getByTestId('dt-header-badDay');
        const title = lossTable(page).getByTestId('dt-sort-badDay');
        await expect(header, 'L1° opens unsorted').toHaveAttribute('data-sort', 'none');

        await title.click();
        await expect(header).toHaveAttribute('data-sort', 'asc');
        await expect.poll(() => lossRowAssetIds(page), {message: 'ascending: the largest loss first, the unmeasured asset last'}).toEqual(ascending);

        await title.click();
        await expect(header).toHaveAttribute('data-sort', 'desc');
        await expect.poll(() => lossRowAssetIds(page), {message: 'descending: the smallest loss first, the unmeasured asset still last'}).toEqual(descending);

        await title.click();
        await expect(header).toHaveAttribute('data-sort', 'none');
        await expect.poll(() => lossRowAssetIds(page), {message: "the third press must give the rows back in the selection's order"}).toEqual(opening);
    });

    /**
     * L1°'s asset cell is the Assets list's: the type icon, then the name on one line.
     *
     * The panel resolves each icon as `icon_url || getAssetTypeIconUrl(asset_type)`, and
     * the second half never comes back empty, so every asset on this page has one. The
     * name sits in the span the marquee attaches to — found by the marquee's own selector,
     * a hook rather than a style — and does not wrap: a long name scrolls instead of
     * pushing its row onto two lines, which is the point of the pattern.
     */
    test('L1° names each asset with its type icon and a name that stays on one line', async ({page}) => {
        await installRiskMocks(page);
        await openAssetGlobalRisk(page);
        await waitForRiskCatalog(page);
        await waitForLossTable(page);

        const selected = await chipIds(page);
        await expect(lossRows(page)).toHaveCount(selected.length);
        for (const assetId of selected) {
            const cell = lossNameCell(page, assetId);
            await expect(cell, `asset ${assetId} has no name cell of its own`).toHaveCount(1);
            await expect(lossRow(page, assetId).getByTestId('risk-asset-set-l1-name'), `asset ${assetId}: its name cell sits in another row`).toHaveAttribute('data-asset-id', String(assetId));

            const icon = cell.getByTestId('risk-asset-set-l1-icon');
            await expect(icon, `asset ${assetId}: no type icon beside the name`).toHaveCount(1);
            await expect(icon, `asset ${assetId}: the icon has no source`).toHaveAttribute('src', /\S/);

            const name = cell.locator(OVERFLOW_MARQUEE_SELECTOR);
            await expect(name, `asset ${assetId}: the name is not in the marquee's span`).toHaveCount(1);
            await expect(name, `asset ${assetId}: the name is empty`).not.toHaveText(/^\s*$/);
            await expect(name, `asset ${assetId}: the name wraps instead of scrolling`).toHaveCSS('white-space', 'nowrap');
        }
    });

    /**
     * L1°'s columns are chosen from its frame, right before the manual icon.
     *
     * The toggle is the project's `ColumnVisibilityToggle`, placed in the frame's header
     * (`RiskLevelSection`'s `actions`) rather than above the table: the header row is where
     * the level's own controls live. The component tests pin its place in the markup and its
     * wiring; what only a browser can show is what the reader sees — the toggle on the icon's
     * line, right before it rather than spread across the header — and that a column really
     * goes and really comes back.
     *
     * `badMonth` is the column switched off because it sits between two others: the rest must
     * close up in their order, and it must come back where it was. The choice is kept in this
     * context's `localStorage`, under the table's storage key, and dies with the context; the
     * test switches it back all the same, and ends on the table it found. Reordering by drag
     * is left out on purpose.
     */
    test("L1°'s frame offers the column toggle right before its manual icon, and bad month switched off and on goes and comes back alone", async ({page}) => {
        await installRiskMocks(page);
        await openAssetGlobalRisk(page);
        await waitForRiskCatalog(page);
        await waitForLossTable(page);

        const frame = lossSection(page);
        const toggle = frame.getByTestId('column-visibility-toggle');
        const docs = frame.getByTestId('risk-asset-set-loss-docs');
        await expect(toggle, "L1°'s frame offers no column toggle").toBeVisible();
        await expect(docs).toBeVisible();
        await expect(frame.getByTestId('risk-asset-set-loss-body').getByTestId('column-visibility-toggle'), "the toggle sits in L1°'s body: it belongs to the header, beside the manual icon").toHaveCount(0);

        // Order and geometry in one read, after the barriers above: both boxes come from the
        // same layout, so a section above that finishes loading and pushes the frame down
        // cannot land between two measurements.
        const head = await frame.evaluate((section) => {
            const toggleNode = section.querySelector('[data-testid="column-visibility-toggle"]');
            const docsNode = section.querySelector('[data-testid="risk-asset-set-loss-docs"]');
            if (toggleNode === null || docsNode === null) return null;
            const box = (node: Element) => {
                const {left, right, top, bottom, width} = node.getBoundingClientRect();
                return {left, right, top, bottom, width};
            };
            return {togglePrecedesDocs: !toggleNode.contains(docsNode) && (toggleNode.compareDocumentPosition(docsNode) & Node.DOCUMENT_POSITION_FOLLOWING) !== 0, toggle: box(toggleNode), docs: box(docsNode)};
        });
        if (head === null) throw new Error('The toggle and the manual icon were visible a moment ago and are gone from the frame.');
        expect(head.togglePrecedesDocs, 'the toggle must come before the manual icon').toBe(true);

        // As the reader sees it: on the icon's line, to its left, and beside it — not spread
        // across the header, which is where a third child of the title row's `justify-between`
        // would land. "Beside" is measured against the toggle itself: less than its own width away.
        expect(head.toggle.top < head.docs.bottom && head.docs.top < head.toggle.bottom, "the toggle is not on the manual icon's line").toBe(true);
        const gap = head.docs.left - head.toggle.right;
        expect(gap, 'the toggle is not to the left of the manual icon').toBeGreaterThanOrEqual(0);
        expect(gap, 'the toggle floats away from the manual icon').toBeLessThan(head.toggle.width);

        // One toggle in L1°'s frame, its own table's. L3°'s frame has one of its own since L3° became a
        // table too; the L3° test below proves it, and that it reads L3°'s columns rather than these.
        await expect(frame.getByTestId('column-visibility-toggle'), "L1°'s frame carries one toggle, its own table's").toHaveCount(1);

        // Every column drawn, and a row per selected asset, before any column is touched.
        const selected = await chipIds(page);
        await expect(lossRows(page)).toHaveCount(selected.length);
        const opening = ['name', ...L1_CELLS];
        await expect.poll(() => lossHeaderIds(page), {message: 'L1° must open on every column, in its order'}).toEqual(opening);

        await toggle.click();
        const menu = frame.getByTestId('column-visibility-dropdown');
        await expect(menu).toBeVisible();
        const badMonth = menu.getByTestId('column-visibility-item-badMonth');

        await badMonth.click();
        await expect(lossTable(page).getByTestId('dt-header-badMonth'), 'bad month is still drawn after switching it off').toHaveCount(0);
        await expect(lossTable(page).getByTestId('risk-asset-set-l1-badMonth'), "bad month's cells outlived its title").toHaveCount(0);
        await expect.poll(() => lossHeaderIds(page), {message: 'the other columns must stay, closed up in their order'}).toEqual(opening.filter((column) => column !== 'badMonth'));
        for (const cell of L1_CELLS.filter((column) => column !== 'badMonth')) {
            await expect(lossTable(page).getByTestId(`risk-asset-set-l1-${cell}`), `${cell} lost cells when bad month was hidden`).toHaveCount(selected.length);
        }

        // Back on: the column returns where it was, with a cell in every row.
        await badMonth.click();
        await expect.poll(() => lossHeaderIds(page), {message: 'bad month must come back where it was'}).toEqual(opening);
        await expect(lossTable(page).getByTestId('risk-asset-set-l1-badMonth'), 'bad month came back without its cells').toHaveCount(selected.length);
    });

    /**
     * L3°'s headers explain; they do not link — L1°'s rule, on the table that now has L1°'s shape
     * (the developer's review, 30/09).
     *
     * Each value column carries its help as the tooltip of its own title (`headerTooltip`, no URL),
     * so there is no ⓘ beside a title and no anchor in the header row: the documentation is the
     * frame's manual icon, one for the whole level. The return column's help is the one the
     * developer asked for by name — how the average annual return is computed — so it is the one
     * rested on. Its words are not read: the component test proves each title shows its own key's
     * message; what only a browser can prove is that resting the pointer on the title opens it.
     *
     * And the titles fit: the table is laid out `fixed`, so a width the reader drags holds, and every
     * figure column opens exactly as wide as its own title in the reader's language, and no narrower
     * (`headerWidth`). DataTable draws its titles upper-case on one line, and a fixed layout sized
     * for Italian let a French title spill out of its column on L1°.
     */
    test("L3°'s value columns carry their help as a tooltip on the title, and its header row carries no link", async ({page}) => {
        await installRiskMocks(page);
        await openAssetGlobalRisk(page);
        await waitForRiskCatalog(page);
        await waitForPaidTable(page);

        // Presence first: every title is drawn, so the absences below are about a header that exists
        // rather than one that has not rendered yet.
        for (const column of ['name', ...L3_CELLS]) {
            await expect(paidTable(page).getByTestId(`dt-header-${column}`), `the ${column} title is missing from L3°'s header`).toBeVisible();
        }
        await expect(paidTable(page).locator('thead a'), "a link in L3°'s header row: the documentation belongs to the frame's manual icon").toHaveCount(0);
        await expect(paidTable(page).locator('[data-testid^="dt-header-tooltip-"]'), 'an ⓘ beside a title: the help is the title itself').toHaveCount(0);
        await expect(page.locator('[data-testid^="risk-asset-set-l3-docs-"]')).toHaveCount(0);
        // Laid out `fixed` since the developer's review of 06/10/2026, the only layout in which a dragged width holds:
        // under `auto` a drag wrote a width the column ignored. What `auto` used to give still holds, because each figure
        // column opens as wide as its own title in the reader's language (`headerWidth`): every title fits inside its th,
        // as drawn, and at the column's own width — the one it is drawn at when the table has no room to spare.
        await expect(paidTable(page).locator('table', {has: page.getByTestId('dt-header-name')}), "L3°'s table is not laid out fixed: a dragged width would not hold").toHaveCSS('table-layout', 'fixed');
        await expect
            .poll(
                () =>
                    paidTable(page).evaluate(
                        (root, columns) =>
                            columns.filter((column) => {
                                const cell = root.querySelector<HTMLElement>(`thead th[data-testid="dt-header-${column}"]`);
                                const title = cell?.querySelector<HTMLElement>(`[data-testid="dt-sort-${column}"]`);
                                if (!cell || !title) return true;
                                const style = getComputedStyle(cell);
                                const box = cell.getBoundingClientRect();
                                const drawn = title.getBoundingClientRect();
                                const inside = drawn.left >= box.left + parseFloat(style.paddingLeft) - 0.5 && drawn.right <= box.right - parseFloat(style.paddingRight) + 0.5;
                                const own = parseFloat(cell.style.width) - parseFloat(style.paddingLeft) - parseFloat(style.paddingRight);
                                return !inside || Math.max(title.scrollWidth, drawn.width) > own + 0.5;
                            }),
                        [...L3_CELLS],
                    ),
                {message: 'a title spills out of its th: its column opened narrower than its title'},
            )
            .toEqual([]);
        // And the reader sizes the columns: a drag on a figure column's edge changes its width. The edge is DataTable's
        // resize handle, the last 6 px of the title cell, found by what it is to the pointer — `col-resize` — not by a class.
        const volatility = paidTable(page).getByTestId('dt-header-volatility');
        const volatilityWidth = () => volatility.evaluate((cell) => cell.getBoundingClientRect().width);
        const widthBefore = await volatilityWidth();
        await volatility.scrollIntoViewIfNeeded();
        const edge = await volatility.evaluate((cell) => {
            const box = cell.getBoundingClientRect();
            const hit = document.elementFromPoint(box.right - 3, box.top + box.height / 2);
            return {x: box.right - 3, y: box.top + box.height / 2, handle: hit !== null && hit !== cell && cell.contains(hit) && getComputedStyle(hit).cursor === 'col-resize'};
        });
        expect(edge.handle, 'no resize handle under the right edge of the volatility title').toBe(true);
        await page.mouse.move(edge.x, edge.y);
        await page.mouse.down();
        await page.mouse.move(edge.x + 60, edge.y, {steps: 8});
        await page.mouse.up();
        await expect.poll(volatilityWidth, {message: "a drag on the volatility column's edge did not change its width"}).toBeGreaterThan(widthBefore + 30);
        // The pointer rested on the edge it dragged, beside no title: no help is open before the one below is read.
        await expect(page.getByTestId('tooltip-content')).toHaveCount(0);

        // The help itself, where the pointer rests. The Tooltip opens after its own hover delay,
        // which the retrying assertion absorbs: nothing here waits on a clock.
        await paidTable(page).getByTestId('dt-sort-expectedReturn').hover();
        const help = page.getByTestId('tooltip-content');
        await expect(help, 'resting on the return title must open its help').toBeVisible();
        await expect(help, 'the help opened empty').not.toHaveText(/^\s*$/);
        await expect(help, 'the help printed its own key: the catalogue has no message for it').not.toHaveText('risk.assetSet.levels.l3.columnHelp.expectedReturn');
        // Resting is not pressing: the column is still unsorted.
        await expect(paidTable(page).getByTestId('dt-header-expectedReturn')).toHaveAttribute('data-sort', 'none');
    });

    /**
     * L3° sorts a column by the figure it draws, with its sign.
     *
     * The average annual return is the column where the sign decides: a loss of 2.1% is larger than
     * a gain of 0.3% and must still sort below it, so neither a sort by magnitude nor one by the
     * printed text passes. An asset nobody could measure is a blank, not a zero, and goes last
     * whichever way the column points; the third press clears the sort and gives the rows back in
     * the selection's order — the only order the system ever chooses, since the level compares and
     * never ranks.
     *
     * The figures are this file's own ({@link INVENTED}), re-planted as a zig-zag that crosses zero
     * (`zigzagExpectedReturn`) so that ascending, descending and the opening order are three
     * different orders; the blank is the asset `dropLastAsset` excludes. The expected orders are
     * worked out from the answer the stub sent, rebuilt through the same function that sent it.
     */
    test('L3° sorts the average annual return by its value with its sign, the unmeasured last both ways, and a third press restores the selection order', async ({page}) => {
        const options: RiskStubOptions = {dropLastAsset: true, zigzagExpectedReturn: true};
        const requests = await installRiskMocks(page, options);
        await openAssetGlobalRisk(page);
        await ensureSelectionAtLeast(page, MINIMUM_SELECTION);
        await waitForRiskCatalog(page);
        await waitForPaidTable(page);

        // The answer the page was given for the selection on screen, rebuilt from the request it
        // answered — L3°'s: the average return of every measured asset, and the one left blank.
        const selected = await chipIds(page);
        await expect.poll(() => paidRequestsFor(requests, selected).length, {timeout: 20_000, message: "L3°'s request must have been asked for the selection on screen"}).toBeGreaterThan(0);
        const paid = paidRequestsFor(requests, selected)[0];
        const averageReturn = new Map(assetSetRiskReturnOutput(paid, options).items.map((item): [number, number] => [item.asset_id, item.expected_annual_return]));
        const {excluded} = preparedAssetIds(paid, options);
        expect(excluded, 'dropLastAsset must leave exactly one selected asset unmeasured').toHaveLength(1);
        const unmeasured = excluded[0];
        const losing = [...averageReturn.entries()].filter(([, value]) => value < 0).map(([assetId]) => assetId);
        const gaining = [...averageReturn.entries()].filter(([, value]) => value > 0).map(([assetId]) => assetId);
        expect([losing.length > 0, gaining.length > 0], `premise: the planted returns must cross zero, or the sign goes untested — read ${JSON.stringify([...averageReturn.values()])}`).toEqual([true, true]);

        // Barrier: the answer is on screen — every row drawn, the measured ones measured and the
        // excluded one blank — before any order is read.
        await expect(paidRows(page)).toHaveCount(selected.length);
        await expect(paidTable(page).locator('[data-testid="risk-asset-set-l3-expectedReturn"][data-measured="true"]')).toHaveCount(averageReturn.size);
        await expect(paidCell(page, unmeasured, 'expectedReturn')).toHaveAttribute('data-measured', 'false');
        // …and each sign is drawn as its own glyph: a loss with U+2212, a gain with +.
        await expect(paidCell(page, losing[0], 'expectedReturn'), 'a negative average return must be drawn with U+2212').toHaveText(/^\s*\u2212/);
        await expect(paidCell(page, gaining[0], 'expectedReturn'), 'a positive average return must be drawn with +').toHaveText(/^\s*\+/);

        const opening = await paidRowAssetIds(page);
        expect(
            [...opening].sort((left, right) => left - right),
            'the rows must be the selection',
        ).toEqual([...selected].sort((left, right) => left - right));

        // The oracle, stated as the rule: by the value with its sign, and a blank last either way.
        // Every figure is distinct (`zigzagRank`), so no tie is left to the table to settle.
        const orderedBy = (figure: (assetId: number) => number | undefined, direction: 'asc' | 'desc'): number[] =>
            [...opening].sort((left, right) => {
                const a = figure(left);
                const b = figure(right);
                if (a === undefined || b === undefined) return a === undefined ? (b === undefined ? 0 : 1) : -1;
                return direction === 'asc' ? a - b : b - a;
            });
        const ascending = orderedBy((assetId) => averageReturn.get(assetId), 'asc');
        const descending = orderedBy((assetId) => averageReturn.get(assetId), 'desc');
        const byMagnitude = orderedBy((assetId) => (averageReturn.has(assetId) ? Math.abs(averageReturn.get(assetId) as number) : undefined), 'asc');
        expect([ascending[ascending.length - 1], descending[descending.length - 1]], 'the oracle itself: the blank closes both orders').toEqual([unmeasured, unmeasured]);
        // Premises: every press must move a row, and the order by value must not be the order by size.
        expect(ascending, 'premise: ascending must differ from the opening order').not.toEqual(opening);
        expect(descending, 'premise: descending must differ from the opening order, or "cleared" and "descending" would draw the same rows').not.toEqual(opening);
        expect(ascending, 'premise: by value must differ from by magnitude, or a sort that dropped the sign would pass').not.toEqual(byMagnitude);

        const header = paidTable(page).getByTestId('dt-header-expectedReturn');
        const title = paidTable(page).getByTestId('dt-sort-expectedReturn');
        await expect(header, 'L3° opens unsorted').toHaveAttribute('data-sort', 'none');

        await title.click();
        await expect(header).toHaveAttribute('data-sort', 'asc');
        await expect.poll(() => paidRowAssetIds(page), {message: 'ascending: the lowest return first — a loss before a gain, whatever its size — and the unmeasured asset last'}).toEqual(ascending);

        await title.click();
        await expect(header).toHaveAttribute('data-sort', 'desc');
        await expect.poll(() => paidRowAssetIds(page), {message: 'descending: the highest return first, the unmeasured asset still last'}).toEqual(descending);

        await title.click();
        await expect(header).toHaveAttribute('data-sort', 'none');
        await expect.poll(() => paidRowAssetIds(page), {message: "the third press must give the rows back in the selection's order"}).toEqual(opening);
    });

    /**
     * L3°'s asset cell is L1°'s: the same helper, the same icons, under L3°'s testids.
     *
     * The panel resolves each icon as `icon_url || getAssetTypeIconUrl(asset_type)`, and the second
     * half never comes back empty, so every asset on this page has one; the levels hand the same map
     * to both tables, so an asset's icon and name are the same in both. The name sits in the span the
     * marquee attaches to — found by the marquee's own selector, a hook rather than a style — and does
     * not wrap: a long name scrolls instead of pushing its row onto two lines.
     */
    test('L3° names each asset with the type icon and the one-line name L1° gives it', async ({page}) => {
        await installRiskMocks(page);
        await openAssetGlobalRisk(page);
        await waitForRiskCatalog(page);
        await waitForLossTable(page);
        await waitForPaidTable(page);

        const selected = await chipIds(page);
        await expect(lossRows(page)).toHaveCount(selected.length);
        await expect(paidRows(page)).toHaveCount(selected.length);
        for (const assetId of selected) {
            const cell = paidNameCell(page, assetId);
            await expect(cell, `asset ${assetId} has no L3° name cell of its own`).toHaveCount(1);
            await expect(paidRow(page, assetId).getByTestId('risk-asset-set-l3-name'), `asset ${assetId}: its L3° name cell sits in another row`).toHaveAttribute('data-asset-id', String(assetId));

            const icon = cell.getByTestId('risk-asset-set-l3-icon');
            await expect(icon, `asset ${assetId}: no type icon beside the name`).toHaveCount(1);
            await expect(icon, `asset ${assetId}: the icon has no source`).toHaveAttribute('src', /\S/);

            const name = cell.locator(OVERFLOW_MARQUEE_SELECTOR);
            await expect(name, `asset ${assetId}: the name is not in the marquee's span`).toHaveCount(1);
            await expect(name, `asset ${assetId}: the name is empty`).not.toHaveText(/^\s*$/);
            await expect(name, `asset ${assetId}: the name wraps instead of scrolling`).toHaveCSS('white-space', 'nowrap');

            // The same asset, drawn the same in both tables: read off L1°'s cell, behind the barriers above.
            const l1Cell = lossNameCell(page, assetId);
            const l1Icon = await l1Cell.getByTestId('risk-asset-set-l1-icon').getAttribute('src');
            const l1Name = ((await l1Cell.locator(OVERFLOW_MARQUEE_SELECTOR).textContent()) ?? '').trim();
            await expect(icon, `asset ${assetId}: L3° draws another icon than L1° — the levels did not hand both tables the same map`).toHaveAttribute('src', l1Icon ?? '');
            await expect(name, `asset ${assetId}: L3° names it otherwise than L1°`).toHaveText(l1Name);
        }
    });

    /**
     * L3°'s columns are chosen from its frame, right before its manual icon — L1°'s arrangement.
     *
     * One toggle per level table, each in its own frame's header (`RiskLevelSection`'s `actions`),
     * each reading its own table: the component tests pin the markup and the wiring; this shows what
     * the reader sees — the toggle on the icon's line, right before it — and that a column of L3°
     * really goes and really comes back, and that L1° is not touched by it.
     *
     * `sortino` is the column switched off because it sits between two others: the rest must close
     * up in their order, and it must come back where it was. The choice is kept in this context's
     * `localStorage`, under the table's own storage key, and dies with the context; the test switches
     * it back all the same, and ends on the table it found.
     */
    test("L3°'s frame offers the column toggle right before its manual icon, and Sortino switched off and on goes and comes back alone", async ({page}) => {
        await installRiskMocks(page);
        await openAssetGlobalRisk(page);
        await waitForRiskCatalog(page);
        await waitForLossTable(page);
        await waitForPaidTable(page);

        const frame = paidSection(page);
        const toggle = frame.getByTestId('column-visibility-toggle');
        const docs = frame.getByTestId('risk-asset-set-paid-docs');
        await expect(toggle, "L3°'s frame offers no column toggle").toBeVisible();
        await expect(docs).toBeVisible();
        await expect(frame.getByTestId('risk-asset-set-paid-body').getByTestId('column-visibility-toggle'), "the toggle sits in L3°'s body: it belongs to the header, beside the manual icon").toHaveCount(0);
        await expect(page.getByTestId('asset-global-risk-panel').getByTestId('column-visibility-toggle'), 'one column toggle per level table: L1° and L3°').toHaveCount(2);

        // Order and geometry in one read, after the barriers above: both boxes come from the same
        // layout, so a section above that finishes loading and pushes the frame down cannot land
        // between two measurements.
        const head = await frame.evaluate((section) => {
            const toggleNode = section.querySelector('[data-testid="column-visibility-toggle"]');
            const docsNode = section.querySelector('[data-testid="risk-asset-set-paid-docs"]');
            if (toggleNode === null || docsNode === null) return null;
            const box = (node: Element) => {
                const {left, right, top, bottom, width} = node.getBoundingClientRect();
                return {left, right, top, bottom, width};
            };
            return {togglePrecedesDocs: !toggleNode.contains(docsNode) && (toggleNode.compareDocumentPosition(docsNode) & Node.DOCUMENT_POSITION_FOLLOWING) !== 0, toggle: box(toggleNode), docs: box(docsNode)};
        });
        if (head === null) throw new Error('The toggle and the manual icon were visible a moment ago and are gone from the frame.');
        expect(head.togglePrecedesDocs, 'the toggle must come before the manual icon').toBe(true);
        expect(head.toggle.top < head.docs.bottom && head.docs.top < head.toggle.bottom, "the toggle is not on the manual icon's line").toBe(true);
        const gap = head.docs.left - head.toggle.right;
        expect(gap, 'the toggle is not to the left of the manual icon').toBeGreaterThanOrEqual(0);
        expect(gap, 'the toggle floats away from the manual icon').toBeLessThan(head.toggle.width);

        // Every column drawn, and a row per selected asset, before any column is touched.
        const selected = await chipIds(page);
        await expect(paidRows(page)).toHaveCount(selected.length);
        const opening = ['name', ...L3_CELLS];
        await expect.poll(() => paidHeaderIds(page), {message: 'L3° must open on every column, in its order'}).toEqual(opening);
        await expect.poll(() => lossHeaderIds(page), {message: 'L1° must open on every column, in its order'}).toEqual(['name', ...L1_CELLS]);

        await toggle.click();
        const menu = frame.getByTestId('column-visibility-dropdown');
        await expect(menu).toBeVisible();
        // The menu reads L3°'s table: its columns, none of L1°'s.
        await expect(menu.getByTestId('column-visibility-item-expectedReturn')).toBeVisible();
        await expect(menu.getByTestId('column-visibility-item-badMonth'), "L3°'s menu lists L1°'s columns: it reads the wrong table").toHaveCount(0);
        const sortino = menu.getByTestId('column-visibility-item-sortino');

        await sortino.click();
        await expect(paidTable(page).getByTestId('dt-header-sortino'), 'Sortino is still drawn after switching it off').toHaveCount(0);
        await expect(paidTable(page).getByTestId('risk-asset-set-l3-sortino'), "Sortino's cells outlived its title").toHaveCount(0);
        await expect.poll(() => paidHeaderIds(page), {message: 'the other columns must stay, closed up in their order'}).toEqual(opening.filter((column) => column !== 'sortino'));
        for (const cell of L3_CELLS.filter((column) => column !== 'sortino')) {
            await expect(paidTable(page).getByTestId(`risk-asset-set-l3-${cell}`), `${cell} lost cells when Sortino was hidden`).toHaveCount(selected.length);
        }
        // L1° is another table with another storage key: hiding a column of L3° hides nothing of it.
        expect(await lossHeaderIds(page), "switching off L3°'s Sortino changed L1°'s columns").toEqual(['name', ...L1_CELLS]);

        // Back on: the column returns where it was, with a cell in every row.
        await sortino.click();
        await expect.poll(() => paidHeaderIds(page), {message: 'Sortino must come back where it was'}).toEqual(opening);
        await expect(paidTable(page).getByTestId('risk-asset-set-l3-sortino'), 'Sortino came back without its cells').toHaveCount(selected.length);
    });

    /**
     * (f) — the benchmark columns appear only when a benchmark applies.
     *
     * Both branches, because the absence is the ordinary state of this page and a
     * test that only proved the presence would leave the default unguarded.
     *
     * And no sentence explains the missing columns: the note that sent the reader to
     * the Dashboard for a benchmark is gone (the developer's second review, 30/09 —
     * "fuori luogo qui"), in either branch.
     *
     * Nor does a fixed note sit under either table any more (round 4): the blank note
     * that explained every dash at once is gone from L1° and L3° alike, because each
     * dash now explains itself — see the two dash cases below, which check the same
     * absence on tables that do hold a blank.
     *
     * The request half of the true branch is red until the levels ask apart (the
     * developer's split, 02/10/2026): today the comparison rides in the one request
     * both levels share, beside L1°'s `asset_set_var` and `asset_set_drawdown`.
     */
    test('L3° shows beta and correlation only when a benchmark applies, with no note about the benchmark either way', async ({page}) => {
        // The two navigations below (read the selection, then seed the shared
        // benchmark and come back) are the price of a module-scope store that
        // hydrates from a user-scoped key at mount.
        test.setTimeout(45_000);
        const requests = await installRiskMocks(page);
        await openAssetGlobalRisk(page);
        await ensureSelectionAtLeast(page, 2);
        await waitForRiskCatalog(page);
        await waitForLossTable(page);
        await waitForPaidTable(page);

        // ── The false branch, which is what this page shows by default ──────
        const paid = page.getByTestId('risk-asset-set-l3');
        await expect(paid).toHaveAttribute('data-benchmark', 'false');
        // The columns that do not depend on a benchmark are present throughout, so
        // "the beta cells are absent" cannot be satisfied by an unrendered table.
        const selected = await chipIds(page);
        await expect(paid.getByTestId('risk-asset-set-l3-volatility')).toHaveCount(selected.length);
        await expect(paid.getByTestId('risk-asset-set-l3-beta')).toHaveCount(0);
        await expect(paid.getByTestId('risk-asset-set-l3-correlation')).toHaveCount(0);
        // No fixed note under either table (round 4): each dash explains itself now. The
        // bodies the notes sat under are on screen — L1°'s table by `waitForLossTable`,
        // L3°'s volatility cells just above — so these absences, and the no-benchmark
        // note's below, are about tables that exist rather than ones still loading.
        await expect(page.getByTestId('risk-asset-set-l1-blank-note'), "L1°'s fixed blank note is back: each dash explains itself now").toHaveCount(0);
        await expect(page.getByTestId('risk-asset-set-l3-blank-note'), "L3°'s fixed blank note is back: each dash explains itself now").toHaveCount(0);
        await expect(page.getByTestId('risk-asset-set-l3-no-benchmark'), 'the no-benchmark note is back: the developer took it out of this page').toHaveCount(0);

        // ── The true branch ─────────────────────────────────────────────────
        // A benchmark that is not one of the measured. No longer because a
        // selected one is refused — since D371 the lab applies it, leaving its own
        // row's beta and correlation blank (Benchmark picker (c)) — but because
        // this branch counts a dot of the reference's own beside one per selected
        // asset, and a selected reference is drawn once. The "+" offers exactly
        // the assets the selection does not hold, so the candidate is read off it.
        const benchmarkId = await pickUnselectedAssetId(page);
        expect(selected, 'this branch needs a reference outside the compared: a selected one is drawn once, with no dot of its own').not.toContain(benchmarkId);

        const userId = await currentUserId(page);
        // Seeded through `localStorage` under the store's own key rather than
        // through the lab's picker — Risk's shared `BenchmarkSelect`, mounted
        // above L1° and L3° as `risk-asset-set-benchmark` — because that picker
        // opens on the choice this key holds, the one shared with Dashboard and
        // Broker Detail, and this case is about the columns rather than about
        // choosing: the benchmark picker cases below drive the control itself.
        // `addInitScript` runs before the app boots on the next navigation, so the
        // store hydrates with the value already in place and the first request
        // carries the comparison — no reload race to lose.
        //
        // ⚠️ BOTH SPELLINGS OF THE KEY, though only the user-scoped one is still
        // needed. The panel no longer reads the store: it binds `benchmarkValue`
        // and `benchmarkState` from `BenchmarkSelect`, derives `benchmarkId` from
        // them (`labBenchmarkId`) — the confirmed choice, whether or not the
        // selection holds it (D371), or null — and mounts the levels only
        // once the state is no longer `pending`. The picker is the store's one
        // reader here: `riskBenchmark.assetId` synchronously for its opening state,
        // then `resolveRiskBenchmark()` on mount, which confirms the id against the
        // asset list before saying `set`. Each read goes through `hydrate()`, which
        // asks storage for one spelling only, the session's at that instant:
        // `lf_${getClientSessionUserId() ?? 'anon'}_...`. And the picker mounts
        // inside the page, which the `(app)` layout renders only once `auth.ts` has
        // published the user — after `transitionClientSession(response.user.id)` —
        // so its first read is already the scoped spelling, and the anon one is
        // never read on this page. Seeding it is therefore no longer needed: the
        // scoped key alone is enough, as in the picker cases below. It is still
        // written only because this case's code is left as it was, and a key
        // nobody here reads changes nothing.
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
        expect(reselected, "the persisted selection must not have swallowed the benchmark: a selected one is drawn once, and this branch counts a dot of the reference's own").not.toContain(benchmarkId);

        // The comparison rides in L3°'s request — beside the figures it is drawn
        // with, not in one of its own. `RiskAssetSetComparisonOutput` publishes the
        // reference's own volatility and expected return so a scatter can place it
        // beside the holdings, and that is only sound because the reference is
        // prepared inside the same request as the `asset_set_risk_return` that
        // places them. Asked separately, the benchmark dot would land on a chart
        // whose other dots were measured over different dates.
        //
        // And never in L1°'s (the developer's split, 02/10/2026): the engine
        // prepares the reference with the scope of the request carrying it, so
        // whatever shares that request shares the benchmark's calendar — and L1°'s
        // window must not depend on a benchmark.
        await expect.poll(() => paidRequestsFor(requests, reselected).some((request) => codesOf(request).has('asset_set_comparison')), {timeout: 20_000, message: 'the benchmark must have reached the wire'}).toBe(true);
        // Filtered by the comparison's *presence*, not merely by scope: the first
        // visit asked about this same selection without a benchmark, so its request
        // is in the capture too and a scope-only filter would count two.
        const withBenchmark = paidRequestsFor(requests, reselected).filter((request) => codesOf(request).has('asset_set_comparison'));
        expect(withBenchmark, 'the comparison must be asked for once, not once per section').toHaveLength(1);
        const codes = codesOf(withBenchmark[0]);
        for (const code of PAID_LEVEL_CODES) {
            expect([...codes], `${code} must share the request with the comparison — one preparation, one calendar for everything L3° draws`).toContain(code);
        }
        for (const code of LOSS_LEVEL_CODES) {
            expect([...codes], `${code} is L1°'s and must not share the comparison's request: whatever rides with the benchmark is measured on its calendar`).not.toContain(code);
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

    /**
     * Benchmark picker (a) — where it sits, and what it opens on.
     *
     * The developer's decision of 01/10/2026: wherever a page measures against a benchmark there
     * is a picker, it opens on the current benchmark, and it is empty only when nothing is set. In
     * the lab it is a row of its own — label, ⓘ help, picker — and, revised on 02/10/2026, it sits
     * beside the choice of the assets to analyse, a parameter common to the whole lab: the
     * selection card's last row, below the chips and their «+», outside that row. So it comes
     * before the correlation section and both comparison levels, inside none of them.
     *
     * Opened on a stored benchmark the asset list confirms, one the selection does not hold (a
     * selected one is (c)'s): the root says `set`, with that id and nothing measured; an L3° request
     * carries it, and no L1° request does (the developer's split, 02/10/2026: a benchmark must never
     * move L1°'s window); L3° draws beta, correlation and the reference's own dot. The ⓘ's words are not
     * held on to — they are translated — but they must be the lab's own sentence, read from the
     * catalogue in the language the page is drawn in.
     *
     * Red until the row moves into the selection card: today it sits after the card, between the
     * correlation section and the two levels. Its L1° half is red until the levels ask apart: today
     * the comparison rides in the one request both levels share.
     */
    test('the benchmark picker sits in the selection card, before the correlation section and both comparison levels, with its help, and opens on the stored benchmark', async ({page}) => {
        test.setTimeout(BENCHMARK_CASE_BUDGET);
        const requests = await installRiskMocks(page);
        const {selection, reference} = await castBenchmark(page);
        await storeLabOpening(page, selection, reference.id);
        await openLabOn(page, selection);

        // It opens on the stored choice, once the asset list has confirmed it.
        const control = benchmarkControl(page);
        await expect(control, 'the lab must have a benchmark picker, and it must open on the stored benchmark').toHaveAttribute('data-benchmark-state', 'set', {timeout: 15_000});
        await expect(control).toHaveAttribute('data-benchmark-id', String(reference.id));
        await expect(control).toHaveAttribute('data-measured', 'false');
        // Nothing to warn about — in the lab not even a selected benchmark is, since D371 — an absence asserted behind the presence above.
        await expect(page.getByTestId(`${LAB_BENCHMARK}-measured`)).toHaveCount(0);

        // Where it sits, read once both levels are drawn to be placed against.
        await waitForLossTable(page);
        await waitForPaidTable(page);
        await expect.poll(() => benchmarkRowPlacement(page), {message: 'the benchmark row must sit in the selection card, after the chips row, before the correlation section, L1° and L3°, inside none of them, its help before its picker'}).toBe('in the selection card');

        await expectComparisonWith(page, requests, selection, reference.id);
        // …in L3° alone: L1° is measured without it, read once L3°'s answer with the benchmark is drawn.
        await expectLossWithoutComparison(page, requests, selection);

        // Its help, last, so the open tooltip covers nothing read above. From a clean slate: the
        // pointer first rests on a measured figure, which has no tooltip to open, so nothing left
        // open by wherever the pointer happened to be can pass for the ⓘ's help. The Tooltip's own
        // hover delay is absorbed by the retrying assertions, not waited out on a clock.
        const sentence = await catalogueSentence(page, 'risk.assetSet.benchmark.help');
        const tooltip = page.getByTestId('tooltip-content');
        const figure = paidCell(page, selection[0], 'volatility');
        await expect(figure, 'the clean slate needs a measured figure to rest on').toHaveAttribute('data-measured', 'true');
        await figure.hover();
        await expect(tooltip, 'a tooltip is still open with the pointer on a measured figure, so the one the ⓘ opens could not be told apart').toHaveCount(0);
        await page.getByTestId(`${LAB_BENCHMARK}-help`).hover();
        await expect(tooltip, 'resting on the ⓘ must open its help').toBeVisible();
        await expect(tooltip, "the ⓘ must say what the benchmark does here, in the lab's own sentence").toHaveText(sentence);
    });

    /**
     * Benchmark picker (b) — a choice made in the lab is the shared choice, and only L3° asks again.
     *
     * Opened with nothing stored, so the picker says `none` and L3° has no comparison to draw.
     * Choosing a flagged benchmark the selection does not hold — typed and clicked the way a reader
     * does — must write the store's user-scoped key, which every Risk page reads, and L3° must ask
     * again with it: beta and correlation appear, and the scatter gains the reference's dot. "Gains"
     * is read as a change: the opening is asserted to lack all three first.
     *
     * L1° must not ask again (the developer's split, 02/10/2026): the benchmark is none of its
     * business, so the choice leaves its question — and its window — where they were. Read as a delta
     * of this page's own L1° requests about the selection: sampled once L1°'s opening is drawn and on
     * the wire, so a late opening cannot pass for a re-ask; read again once L3°'s answer with the
     * benchmark is drawn, the state the choice produces — a re-ask the choice set off would leave with
     * L3°'s, so it is in the capture by then. The delta counts the wire: a re-ask the client's cache
     * serves is the same question, and cannot move L1°'s window either.
     *
     * Red until the lab mounts the picker. Past that, its L1° half is red until the levels ask apart:
     * today the choice re-sends the one request both levels share, now with `asset_set_comparison`,
     * and that request carries L1°'s analytics — one new L1° request where none is allowed.
     */
    test('choosing a benchmark in the lab writes the shared choice, and only L3° asks again with it and draws beta, correlation and its dot', async ({page}) => {
        test.setTimeout(BENCHMARK_CASE_BUDGET);
        const requests = await installRiskMocks(page);
        const {selection, reference} = await castBenchmark(page);
        const key = await storeLabOpening(page, selection, null);
        await openLabOn(page, selection);

        const control = benchmarkControl(page);
        await expect(control, 'with nothing stored the lab must open its picker empty').toHaveAttribute('data-benchmark-state', 'none', {timeout: 15_000});
        await expect(control).toHaveAttribute('data-benchmark-id', '');
        await expectNoComparison(page, requests, selection);
        // L1°'s opening — drawn, on the wire, without a comparison — is the baseline the choice is measured against.
        await expectLossWithoutComparison(page, requests, selection);
        const lossBefore = lossRequestsFor(requests, selection).length;

        await chooseBenchmark(page, reference);

        // Published by the picker, and shared: the user-scoped key holds the id every Risk page reads.
        await expect(control).toHaveAttribute('data-benchmark-state', 'set');
        await expect(control).toHaveAttribute('data-benchmark-id', String(reference.id));
        await expect(control).toHaveAttribute('data-measured', 'false');
        await expect.poll(() => readStorage(page, key), {message: 'the choice made in the lab did not reach the shared key'}).toBe(String(reference.id));

        await expectComparisonWith(page, requests, selection, reference.id);

        // …and L3° alone asked: no new L1° request about the selection, read behind L3°'s answer drawn above.
        const lossAfter = lossRequestsFor(requests, selection);
        const reasked = `choosing a benchmark re-asked L1° about the selection: ${lossAfter.length - lossBefore} new L1° request(s), carrying ${JSON.stringify(lossAfter.slice(lossBefore).map((request) => [...codesOf(request)].sort()))}`;
        expect(lossAfter.length - lossBefore, reasked).toBe(0);
        await expectLossWithoutComparison(page, requests, selection);
    });

    /**
     * Benchmark picker (c) — a stored benchmark that is one of the selected assets (D371).
     *
     * The developer's decision of 02/10/2026: in the lab a selected asset may be the benchmark, and it
     * becomes the reference of the others. So a stored choice the selection holds is applied like any
     * other. The picker opens on it — `set`, that id — publishing nothing measured and drawing no ⚠: a
     * selected benchmark is no mistake to warn about any more. An L3° request carries the comparison
     * with it, and no L1° request does (the developer's split, 02/10/2026).
     *
     * `asset_set_comparison` 1.1.0 keeps the reference in the selection, measures it like the others
     * and skips it among the compared: a beta and a correlation with itself would be 1 by
     * construction. So its own row is a row of figures but for those two, which are dashes flagged
     * `data-reference="true"`, each explaining itself as the developer asked — «un trattino e un
     * tooltip che spiega che non è applicabile perché sé stesso è già il benchmark» — in the
     * catalogue's `risk.assetSet.levels.l3.referenceItself` rather than the generic blank note; the
     * other rows are measured against it. And the chart draws it once, as its own row's dot with no
     * second one beside it, so the scatter holds one dot per selected asset. Which dot plays the
     * reference, and in what colour, is drawn inside the canvas and not read here.
     *
     * The tooltip's words are not held on to — they are translated — but they must be the catalogue's
     * sentence for that key, in the language the page is drawn in, as (a) reads its ⓘ.
     *
     * Red until the lab applies a selected benchmark. Today it hands the picker its selection as what
     * the page measures, so the picker publishes `data-measured="true"` and draws the ⚠ — the first
     * assertion to fail — and past that the panel withholds the choice (`labBenchmarkId`), so no
     * request carries a comparison and L3° draws neither column.
     */
    test('a stored benchmark that is one of the selected assets is applied: its own row explains its blank beta and correlation, and the chart draws it once', async ({page}) => {
        test.setTimeout(BENCHMARK_CASE_BUDGET);
        const requests = await installRiskMocks(page);
        const {selection} = await castBenchmark(page);
        // One of the assets this test selects: an entry of the array it stores, not a place on the page.
        const reference = selection[0];
        const others = selection.filter((assetId) => assetId !== reference);
        await storeLabOpening(page, selection, reference);
        await openLabOn(page, selection);

        // The picker opens on it as on any confirmed choice, and warns about nothing.
        const control = benchmarkControl(page);
        await expect(control, 'a benchmark that is also selected must stay the current choice, not be dropped').toHaveAttribute('data-benchmark-id', String(reference), {timeout: 15_000});
        await expect(control).toHaveAttribute('data-benchmark-state', 'set');
        await expect(control, 'in the lab a selected asset may be the benchmark (D371): the picker must not publish it as measured').toHaveAttribute('data-measured', 'false');
        // An absence asserted behind the presence above: the picker is drawn, on this very choice.
        await expect(page.getByTestId(`${LAB_BENCHMARK}-measured`), 'a selected benchmark is no mistake any more: no ⚠ may flag it').toHaveCount(0);

        // Applied: L3° compares against it and draws it once — one dot per selected asset — and L1° is measured without it.
        await expectComparisonWith(page, requests, selection, reference);
        await expectLossWithoutComparison(page, requests, selection);

        // Its own row is measured like the others but for beta and correlation: two dashes, flagged as the reference's, each with a tooltip of its own.
        for (const cell of L3_CELLS) {
            await expect(paidCell(page, reference, cell), `the reference is measured like the others: its own ${cell} must be a figure`).toHaveAttribute('data-measured', 'true');
        }
        for (const cell of L3_BENCHMARK_CELLS) {
            const own = paidCell(page, reference, cell);
            await expect(own, `the reference's own ${cell} must be blank: against itself it would be 1 by construction`).toHaveAttribute('data-measured', 'false');
            await expect(own, `the reference's own ${cell} must be flagged as the reference's, not left as an ordinary blank`).toHaveAttribute('data-reference', 'true');
            // The dash every blank of the table is drawn with: «un trattino», not a word.
            await expect(own, `the reference's own ${cell} must be drawn as a dash`).toHaveText('\u2014');
            await expect(cellTooltip(paidRow(page, reference), `risk-asset-set-l3-${cell}`), `the reference's ${cell} dash has no tooltip to say why it is blank`).toHaveCount(1);
        }
        // The other rows are measured against it, and none of them is flagged as the reference.
        for (const assetId of others) {
            for (const cell of L3_BENCHMARK_CELLS) {
                await expect(paidCell(page, assetId, cell), `asset ${assetId} must be measured against the reference: its ${cell} must be a figure`).toHaveAttribute('data-measured', 'true');
                await expect(paidCell(page, assetId, cell), `asset ${assetId} is not the reference: its ${cell} must not be flagged as one`).not.toHaveAttribute('data-reference', 'true');
            }
        }

        // The two dashes explain themselves — last, so an open tooltip covers nothing read above, and
        // each from a clean slate: the pointer first rests on the reference's own volatility, a figure
        // with no tooltip to open, so the explanation that opens next is the dash's. A resting place in
        // the dashes' own row, because a cell's help opens above or below its row: the one left open by
        // the first dash may sit over the next row, never over this one. The Tooltip's own hover delay
        // is absorbed by the retrying assertions, not waited out on a clock.
        const sentence = await catalogueSentence(page, 'risk.assetSet.levels.l3.referenceItself');
        const tooltip = page.getByTestId('tooltip-content');
        const figure = paidCell(page, reference, 'volatility');
        for (const cell of L3_BENCHMARK_CELLS) {
            await figure.hover();
            await expect(tooltip, `a tooltip is still open with the pointer on a measured figure, so the one the reference's ${cell} dash opens could not be told apart`).toHaveCount(0);
            await cellTooltip(paidRow(page, reference), `risk-asset-set-l3-${cell}`).hover();
            await expect(tooltip, `resting on the reference's ${cell} dash must open its explanation`).toBeVisible();
            await expect(tooltip, `the reference's ${cell} dash must say it is the benchmark itself, in the catalogue's sentence rather than the generic blank note`).toHaveText(sentence);
        }
    });

    /**
     * Benchmark picker (d) — a stored id no asset matches.
     *
     * Read as `unknown`: the placeholder, an empty `data-benchmark-id`, nothing measured, no ⚠ —
     * and nothing compared, since a reference nobody can name is no reference. The key keeps the
     * id: the store reads and never corrects, because a list that failed to arrive and a deleted
     * asset look the same from the browser. The id is derived from the list it must be absent from,
     * far above its highest ({@link ABSENT_ID_MARGIN}), never assumed free.
     *
     * Red until the lab mounts the picker — and red past it on today's code too, which sends
     * whatever id the store holds: the comparison goes out and the two columns appear.
     */
    test('a stored benchmark no asset matches leaves the picker on its placeholder, as unknown, and compares nothing', async ({page}) => {
        test.setTimeout(BENCHMARK_CASE_BUDGET);
        const requests = await installRiskMocks(page);
        const {selection, absentId} = await castBenchmark(page);
        const key = await storeLabOpening(page, selection, absentId);
        await openLabOn(page, selection);

        const control = benchmarkControl(page);
        await expect(control, 'a stored id no asset matches must read as unknown').toHaveAttribute('data-benchmark-state', 'unknown', {timeout: 15_000});
        await expect(control, 'an unknown benchmark leaves the picker on its placeholder, holding no value').toHaveAttribute('data-benchmark-id', '');
        await expect(control).toHaveAttribute('data-measured', 'false');
        await expect(page.getByTestId(`${LAB_BENCHMARK}-measured`)).toHaveCount(0);

        await expectNoComparison(page, requests, selection);
        expect(await readStorage(page, key), 'the store must keep an id it cannot confirm: it reads, it never corrects').toBe(String(absentId));
    });

    /**
     * Benchmark picker (e) — one wave, not two, and the benchmark in L3°'s alone.
     *
     * With a benchmark stored, the picker starts `pending` while the asset list confirms it, and L3°
     * must not ask in the meantime: a request asked then would leave without the benchmark, and a
     * second one would follow with it — two preparations, and a table drawn twice. So every L3°
     * request about the opening selection must carry the stored benchmark.
     *
     * And no L1° request may ever carry it (the developer's split, 02/10/2026). L1° asks for
     * `asset_set_var` ×2 and `asset_set_drawdown` in a request of its own, whatever the benchmark:
     * the engine prepares a request's comparison asset with its scope, so a benchmark riding with L1°
     * would move L1°'s window — the developer saw L1° turn «Partial» because of one.
     *
     * No wait of its own is needed for an earlier L3° request: it would leave before the one that
     * carries the benchmark, so once that one is in the capture, an earlier one is too. L1°'s absence
     * is read behind its own presence ({@link expectLossWithoutComparison}). It reads only the wire —
     * the picker's state is (a)'s.
     *
     * Red until the levels ask apart. Requests are told apart by the analytics they carry
     * ({@link lossRequestsFor}, {@link paidRequestsFor}), and today's one request carries both
     * levels' analytics and, the benchmark being stored, `asset_set_comparison` with it. So it is
     * L3°'s — and the L3° half passes: every L3° request carries the benchmark — and it is L1°'s too,
     * as the request carrying `asset_set_var` and `asset_set_drawdown`: "no L1° request carries the
     * comparison" finds it there, and fails naming it.
     */
    test('with a benchmark stored, every L3° request about the opening selection carries it and no L1° request ever does: one wave, never one without it first', async ({page}) => {
        test.setTimeout(BENCHMARK_CASE_BUDGET);
        const requests = await installRiskMocks(page);
        const {selection, reference} = await castBenchmark(page);
        await storeLabOpening(page, selection, reference.id);
        await openLabOn(page, selection);

        await expect.poll(() => waveBenchmarks(requests, selection), {timeout: 20_000, message: "the stored benchmark never reached L3°'s request"}).toContain(reference.id);
        await expect(page.getByTestId('risk-asset-set-l3'), 'the L3° request carrying the benchmark must be the answer drawn').toHaveAttribute('data-benchmark', 'true', {timeout: 20_000});
        const waves = waveBenchmarks(requests, selection);
        const leftWithout = `an L3° request about the opening selection left without the stored benchmark — L3°'s benchmarks, in the order its requests left: ${JSON.stringify(waves)}`;
        expect(
            waves.filter((id) => id !== reference.id),
            leftWithout,
        ).toEqual([]);

        // …and L1°, measured all the same, never with it.
        await expectLossWithoutComparison(page, requests, selection);
    });

    /**
     * Benchmark picker (f) — the selected assets are on offer too (D371).
     *
     * Since the developer's decision of 02/10/2026 a selected asset may be the benchmark, the
     * reference of the others, so the lab's picker leaves nothing the page measures out of its list.
     * Opened with nothing stored, so no asset is kept on offer for being the current choice: what the
     * list holds is what it offers anyone. Every selected asset must be on it, found the way a reader
     * finds one — by typing its name — and the one chosen is applied like any other: `set` on its id,
     * nothing measured and no ⚠; an L3° request about the selection carries it and no L1° request
     * does; L3° draws it once, one dot per selected asset. Its row is (c)'s subject and the shared
     * key (b)'s: neither depends on how the benchmark was chosen.
     *
     * The opening is drawn without a comparison first, so the one that follows is the choice's doing.
     *
     * Red until the list keeps the selected assets: today the lab hands the picker its selection as
     * what the page measures, and the picker leaves those out of its list (`offered`) unless one is
     * the current choice — with nothing stored none is, so the first selected asset typed is not on
     * offer. Past the list it is red as (c) is, until the panel applies a selected benchmark.
     */
    test('the benchmark picker offers the selected assets too, and one chosen among them is applied: L3° compares the others against it and draws it once, L1° never asks with it', async ({page}) => {
        test.setTimeout(BENCHMARK_CASE_BUDGET);
        const requests = await installRiskMocks(page);
        const {selection, selected} = await castBenchmark(page);
        await storeLabOpening(page, selection, null);
        await openLabOn(page, selection);

        const control = benchmarkControl(page);
        await expect(control, 'with nothing stored the lab must open its picker empty').toHaveAttribute('data-benchmark-state', 'none', {timeout: 15_000});
        await expectNoComparison(page, requests, selection);

        // Every selected asset is on offer, typed the way a reader types it. Scoped to this picker:
        // `search-select-option-*` is shared by every select on the page.
        await openBenchmarkPicker(page);
        const search = page.getByTestId(`${LAB_BENCHMARK}-search`);
        for (const asset of selected) {
            expect(asset.display_name, `selected asset #${asset.id} has no name a reader could type. Check populate_mock_data.py.`).not.toBe('');
            await search.fill(asset.display_name);
            await expect(search).toHaveValue(asset.display_name);
            const option = page.getByTestId(LAB_BENCHMARK).getByTestId(`search-select-option-${asset.id}`);
            await expect(option, `selected asset ${asset.display_name} (#${asset.id}) is not on offer in the lab's benchmark picker: since D371 a selected asset may be the benchmark`).toBeVisible({timeout: 8_000});
        }

        // One of them, chosen as (b) chooses: the last the test stores — an entry of its own array, not a place on the page.
        const chosen = selected[selected.length - 1];
        await chooseBenchmark(page, chosen);
        await expect(control).toHaveAttribute('data-benchmark-state', 'set');
        await expect(control).toHaveAttribute('data-benchmark-id', String(chosen.id));
        await expect(control, 'in the lab a selected asset may be the benchmark (D371): the picker must not publish it as measured').toHaveAttribute('data-measured', 'false');
        await expect(page.getByTestId(`${LAB_BENCHMARK}-measured`), 'a selected benchmark is no mistake any more: no ⚠ may flag it').toHaveCount(0);

        // Applied like any other: L3° asks with it and draws it once, L1° is measured without it.
        await expectComparisonWith(page, requests, selection, chosen.id);
        await expectLossWithoutComparison(page, requests, selection);
    });

    /**
     * Every dash in L1° explains itself (the developer's review, round 4).
     *
     * A figure nobody could measure is drawn as an em dash, and the fixed note that sat under the
     * table to explain every dash at once is gone: the explanation now rides on each dash, as the
     * project's Tooltip around the cell ({@link cellTooltip}). A measured figure owes the reader no
     * explanation and carries none — no wrapper at all, so resting on a number opens nothing.
     *
     * The blank is the asset `dropLastAsset` excludes, the state the backend leaves when it cannot
     * prepare a series, so the table holds measured rows and a blank one side by side. The note's
     * absence is checked here too, on a table that does hold a blank: a note drawn only when
     * something is blank would slip past the benchmark case, whose tables hold none. The help's words
     * are not read — they are translated; what only a browser can prove is that resting on the dash
     * opens a help that says something, and that the catalogue had a message for it, not its key.
     */
    test('every dash in L1° explains itself in a tooltip of its own, and a measured figure carries none', async ({page}) => {
        const options: RiskStubOptions = {dropLastAsset: true};
        const requests = await installRiskMocks(page, options);
        await openAssetGlobalRisk(page);
        await ensureSelectionAtLeast(page, 2);
        await waitForRiskCatalog(page);
        await waitForLossTable(page);

        // Which asset is blank is read from the request the stub answered — L1°'s, the one this table
        // is drawn from; it drops the last id of the scope it was asked about — never guessed from the chips.
        const selected = await chipIds(page);
        await expect.poll(() => lossRequestsFor(requests, selected).length, {timeout: 20_000, message: "L1°'s request must have been asked for the selection on screen"}).toBeGreaterThan(0);
        const {covered, excluded} = preparedAssetIds(lossRequestsFor(requests, selected)[0], options);
        expect(excluded, 'dropLastAsset must leave exactly one selected asset unmeasured').toHaveLength(1);
        const unmeasured = excluded[0];
        // Any measured asset will do: none of them may carry a tooltip.
        const measured = covered[0];

        // Presence first — every measured figure drawn, every cell of the blank row blank — so the
        // absences below are about a table showing its answer, not one still loading.
        for (const cell of L1_CELLS) {
            await expect(lossTable(page).locator(`[data-testid="risk-asset-set-l1-${cell}"][data-measured="true"]`)).toHaveCount(covered.length);
            await expect(lossCell(page, unmeasured, cell)).toHaveAttribute('data-measured', 'false');
        }

        // THE RULE: every dash is wrapped in its own explanation…
        for (const cell of L1_CELLS) {
            await expect(cellTooltip(lossRow(page, unmeasured), `risk-asset-set-l1-${cell}`), `the ${cell} dash of an unmeasured asset has no tooltip to say why it is blank`).toHaveCount(1);
        }
        // …and no figure is: not one wrapper around anything measured, anywhere in the table.
        await expect(lossTable(page).locator('.tooltip-wrapper', {has: page.locator('[data-measured="true"]')}), 'a measured figure carries a tooltip: only a dash owes the reader an explanation').toHaveCount(0);
        await expect(page.getByTestId('risk-asset-set-l1-blank-note'), 'the fixed blank note is back under L1°, on the very table whose dashes explain themselves').toHaveCount(0);

        // A clean slate: the pointer rests on a figure, which has no tooltip to open, so whatever
        // help opens next is the dash's.
        await lossCell(page, measured, 'badDay').hover();
        const help = page.getByTestId('tooltip-content');
        await expect(help, 'a help is still open with the pointer resting on a measured figure').toHaveCount(0);

        // Resting on the dash opens its help. The Tooltip opens after its own hover delay, which the
        // retrying assertion absorbs: nothing here waits on a clock.
        await cellTooltip(lossRow(page, unmeasured), 'risk-asset-set-l1-badDay').hover();
        await expect(help, 'resting on a dash must open its explanation').toBeVisible();
        await expect(help, 'the explanation opened empty').not.toHaveText(/^\s*$/);
        await expect(help, 'the explanation printed its own key: the catalogue has no message for it').not.toHaveText(BLANK_NOTE_KEY);
    });

    /**
     * Every dash in L3° explains itself — L1°'s rule, on the table that has L1°'s shape (the
     * developer's review, round 4).
     *
     * The same blank, the same wrapper and the same absences as the L1° case above, read through
     * L3°'s own locators. Resting is all this case does: a press on the dash opens the same help and
     * selects no row, which the developer accepted as it is and asked not to pin.
     */
    test('every dash in L3° explains itself in a tooltip of its own, and a measured figure carries none', async ({page}) => {
        const options: RiskStubOptions = {dropLastAsset: true};
        const requests = await installRiskMocks(page, options);
        await openAssetGlobalRisk(page);
        await ensureSelectionAtLeast(page, 2);
        await waitForRiskCatalog(page);
        await waitForPaidTable(page);

        // Read, as in L1°, from the request the stub answered — L3°'s, the one this table is drawn from.
        const selected = await chipIds(page);
        await expect.poll(() => paidRequestsFor(requests, selected).length, {timeout: 20_000, message: "L3°'s request must have been asked for the selection on screen"}).toBeGreaterThan(0);
        const {covered, excluded} = preparedAssetIds(paidRequestsFor(requests, selected)[0], options);
        expect(excluded, 'dropLastAsset must leave exactly one selected asset unmeasured').toHaveLength(1);
        const unmeasured = excluded[0];
        // Any measured asset will do: none of them may carry a tooltip.
        const measured = covered[0];

        // Presence first, as in L1°.
        for (const cell of L3_CELLS) {
            await expect(paidTable(page).locator(`[data-testid="risk-asset-set-l3-${cell}"][data-measured="true"]`)).toHaveCount(covered.length);
            await expect(paidCell(page, unmeasured, cell)).toHaveAttribute('data-measured', 'false');
        }

        // THE RULE: every dash is wrapped in its own explanation, and no figure is.
        for (const cell of L3_CELLS) {
            await expect(cellTooltip(paidRow(page, unmeasured), `risk-asset-set-l3-${cell}`), `the ${cell} dash of an unmeasured asset has no tooltip to say why it is blank`).toHaveCount(1);
        }
        await expect(paidTable(page).locator('.tooltip-wrapper', {has: page.locator('[data-measured="true"]')}), 'a measured figure carries a tooltip: only a dash owes the reader an explanation').toHaveCount(0);
        await expect(page.getByTestId('risk-asset-set-l3-blank-note'), 'the fixed blank note is back under L3°, on the very table whose dashes explain themselves').toHaveCount(0);

        // A clean slate, then the dash of the column whose help the developer asked for by name.
        await paidCell(page, measured, 'expectedReturn').hover();
        const help = page.getByTestId('tooltip-content');
        await expect(help, 'a help is still open with the pointer resting on a measured figure').toHaveCount(0);

        await cellTooltip(paidRow(page, unmeasured), 'risk-asset-set-l3-expectedReturn').hover();
        await expect(help, 'resting on a dash must open its explanation').toBeVisible();
        await expect(help, 'the explanation opened empty').not.toHaveText(/^\s*$/);
        await expect(help, 'the explanation printed its own key: the catalogue has no message for it').not.toHaveText(BLANK_NOTE_KEY);
    });

    /**
     * L3° says which period its figures cover (the developer's review, round 4).
     *
     * Between the table and the scatter, a note publishes the window the figures were measured over
     * as attributes beside its sentence ({@link expectL3Period}), worked out from the
     * `asset_set_risk_return` result's own metadata ({@link l3PeriodFor}), read off L3°'s own request
     * ({@link paidRequestsFor}). The sentence is translated and not read.
     *
     * The stub measures a fixed 87 days ending on the period's last day — a window opening 86 days
     * before it — and echoes the period's own start in `analyzed_range.start`: a note that took its
     * start from there instead of from `calendar_days` would publish another day, which is the
     * difference this case pins. The toolbar opens on three months, 89 to 92 days, which 87 fill to
     * within the week — the window opens three to six days after the toolbar — so the note opens not
     * narrowed; a year in the toolbar leaves the same 87 days far short of it, and the note must say so.
     */
    test("L3° publishes the period its figures cover between its table and its scatter, and says when it is narrower than the toolbar's", async ({page}) => {
        // Two answers to wait for, the opening period's and a year's, the first one drawn as a
        // chart as well. Every wait below is a barrier on a published state; the budget pays for
        // the second wave, it does not hedge against a slow one.
        test.setTimeout(45_000);
        const requests = await installRiskMocks(page);
        await openAssetGlobalRisk(page);
        await ensureSelectionAtLeast(page, 2);
        await waitForRiskCatalog(page);
        await waitForPaidTable(page);
        await expectChartCanvas(page, 'risk-asset-set-l3-scatter', 20_000);

        // The opening answer, rebuilt from the request it answered — L3°'s own: L1°'s carries no
        // `asset_set_risk_return`, and the two levels' requests leave in no promised order.
        const selected = await chipIds(page);
        await expect.poll(() => paidRequestsFor(requests, selected).length, {timeout: 20_000, message: "L3°'s request must have been asked for the selection on screen"}).toBeGreaterThan(0);
        const openingRequest = paidRequestsFor(requests, selected).at(-1) as RiskRequest;
        const opening = l3PeriodFor(openingRequest);
        expect(opening.start, "premise: the stub's analyzed_range.start (the period's own start) must differ from the window's start, end − calendar_days + 1, or a note reading the wrong one would pass").not.toBe(openingRequest.date_range.start);
        expect(opening.narrowed, `premise: the toolbar's opening three months hold the stub's 87 days to within a week — read ${JSON.stringify(opening)}`).toBe(false);
        await expectL3Period(page, opening, 10_000);

        // …where the developer put it: after the table, before the chart that draws the same figures.
        expect(await l3PeriodPlacement(page), "the period note must sit after L3°'s table and before its scatter").toBe('between');

        // ── A year in the toolbar: the same 87 days now fall far short of it ──
        const year = await pressPeriodPreset(page, '1y');
        const askedFor = (period: DayRange) => paidRequestsFor(requests, selected).filter((request) => rangeKey({start: request.date_range.start, end: request.date_range.end ?? request.date_range.start}) === rangeKey(period));
        await expect.poll(() => askedFor(year).length, {timeout: 20_000, message: "the year's L3° request must have been asked for the same selection"}).toBeGreaterThan(0);
        const widened = l3PeriodFor(askedFor(year).at(-1) as RiskRequest);
        expect(widened.narrowed, `premise: a year in the toolbar leaves the stub's 87 days more than a week short of it — read ${JSON.stringify(widened)}`).toBe(true);
        await waitForPaidTable(page);
        await expectL3Period(page, widened, 10_000);
    });

    /**
     * L3°'s rows select, one at a time, and the scatter follows — the one selection L3° shares
     * between its table and its scatter (the developer's second review, 30/09).
     *
     * The table is DataTable in single selection, so there is no checkbox to find: a click on a
     * row selects it, a second click on the same row clears it, and a click on another row moves
     * the selection there. Nothing is selected on opening, and every row says so. The state is
     * read where DataTable publishes it, `data-selected` on the row — never a class, never a
     * colour.
     *
     * The row → dot half is read where the chart publishes it: `data-selected-id` on the
     * scatter's container, the selection the chart was handed — `asset-<id>`, `""` for none —
     * because the dot's own green is inside a canvas (`scatterChartHelpers.test.ts` pins how it
     * is drawn). The dot → row half is not driven here: a click on a dot would need the canvas's
     * pixel coordinates, which this suite does not compute. `AssetSetRiskReturnSection.test.ts`
     * pins it with the real section — a dot's click selects its row through the table, a second
     * click clears it, the benchmark's dot selects nothing — and `ScatterChart.test.ts` pins that
     * a click on a dot comes back as that dot's id.
     *
     * Nothing to restore: the selection is the table's own state and dies with the page.
     */
    test('L3° selects one row at a time: a click selects it, a second click clears it, a click on another row moves it there, and the scatter follows', async ({page}) => {
        await installRiskMocks(page);
        await openAssetGlobalRisk(page);
        await ensureSelectionAtLeast(page, 2);
        await waitForRiskCatalog(page);
        await waitForPaidTable(page);

        // Barrier: a row per selected asset, so every count below is about a table that is drawn.
        const selected = await chipIds(page);
        expect(selected.length, 'premise: two rows at least, or the selection has nowhere to move').toBeGreaterThanOrEqual(2);
        await expect(paidRows(page)).toHaveCount(selected.length);
        const selectedRows = paidTable(page).locator('tbody tr[data-row-id][data-selected="true"]');

        // The chart half is read off the scatter, which is drawn only from two placeable dots up: a
        // premise stated here, so a missing chart fails as one rather than as a selection nobody
        // marked. One dot per row — no benchmark on this page by default — so each row clicked below
        // has its dot; a selection grown above gets its last dots with its own wave, hence the wait.
        const scatter = page.getByTestId('risk-asset-set-l3-scatter');
        await expect(scatter, 'premise: the scatter is drawn — two placeable dots at least — or there is no dot to mark').toBeVisible({timeout: 20_000});
        await expectChartCanvas(page, 'risk-asset-set-l3-scatter', 20_000);
        await expect(scatter, 'premise: one dot per row, so each row clicked below has a dot to mark').toHaveAttribute('data-point-count', String(selected.length), {timeout: 20_000});

        // Nothing is selected on opening — and every row states it, rather than carrying no state at all.
        await expect(paidTable(page).locator('tbody tr[data-row-id][data-selected="false"]'), 'nothing may be selected before the reader clicks').toHaveCount(selected.length);
        await expect(selectedRows).toHaveCount(0);
        await expect(scatter, 'nothing selected on opening: the chart is handed no dot to mark').toHaveAttribute('data-selected-id', '');

        // Any two rows of this context's own selection: which two is irrelevant, they are told apart by id.
        const [first, second] = selected;

        await paidRow(page, first).click();
        await expect(paidRow(page, first), 'a click on a row must select it').toHaveAttribute('data-selected', 'true');
        await expect(selectedRows, 'one row selected: the one clicked').toHaveCount(1);
        await expect(scatter, "the chart must be handed the selected row's asset, to mark its dot").toHaveAttribute('data-selected-id', `asset-${first}`);
        // Single selection is the click itself: no checkbox column appeared to hold it.
        await expect(paidTable(page).locator('[data-testid^="dt-row-checkbox-"], [data-testid="dt-select-all"]'), 'selecting a row drew checkboxes').toHaveCount(0);

        await paidRow(page, first).click();
        await expect(paidRow(page, first), 'a second click on the selected row must clear it').toHaveAttribute('data-selected', 'false');
        await expect(selectedRows).toHaveCount(0);
        await expect(scatter, 'a cleared selection must leave the chart no dot to mark').toHaveAttribute('data-selected-id', '');

        await paidRow(page, first).click();
        await expect(paidRow(page, first), 'premise: the row is selected again before the selection moves').toHaveAttribute('data-selected', 'true');
        await paidRow(page, second).click();
        await expect(paidRow(page, second), 'a click on another row must move the selection there').toHaveAttribute('data-selected', 'true');
        await expect(paidRow(page, first), 'the row selected before must let go').toHaveAttribute('data-selected', 'false');
        await expect(selectedRows, 'one row at most').toHaveCount(1);
        await expect(scatter, "the chart's mark must move with the selection, to the new row's dot").toHaveAttribute('data-selected-id', `asset-${second}`);
    });

    test("broker preset: loads exactly that broker's holdings and lets no amount through, a broker holding nothing keeps the selection, and a chip removed by hand comes back through the picker", async ({page}) => {
        // Three report round trips — the opening seed, the preset, the broker that
        // holds nothing — beside two trips through the "+". The budget pays for that
        // work; every wait below is still a barrier on a published state, so a
        // genuinely slow page fails with its own message.
        test.setTimeout(60_000);
        const requests = await installRiskMocks(page);
        const eligibility = await answerEligibility(page);
        const reports = await captureReports(page);
        const broker = await brokerWithHoldings(page);

        await openAssetGlobalRisk(page);
        // The preset is the one path by which a money-bearing payload enters this
        // page, and the net at (c) only has teeth while values are shown.
        await pinPrivacyOff(page);
        await ensureSelectionAtLeast(page, 2);
        await waitForRiskCatalog(page);

        // ── (e) the two side assertions this test inherits ───────────────────────
        // The canvas first, because it is the presence barrier that gives the zero
        // after it a meaning. Asset Global carries no beta notice at all:
        // `AssetSetReplaySection` hands `L4WhatIf` the replay rung alone, and the
        // banner lives in the simulation branch — structural, not a convention.
        await expectChartCanvas(page, 'risk-correlation-heatmap', 20_000);
        await expect(page.getByTestId('risk-beta-banner')).toHaveCount(0);

        // ── (a) a chip removed by hand, and added back through the "+" ──────────
        const counter = selectionCounter(page);
        const opening = await chipIds(page);
        await expect(counter).toHaveAttribute('data-selected', String(opening.length));
        // Any chip will do: the round trip puts back whichever it took.
        const removedId = opening[0];
        const remaining = opening.filter((assetId) => assetId !== removedId);
        await page.getByTestId(`risk-remove-asset-${removedId}`).click();
        await expect(page.getByTestId(`risk-selected-asset-${removedId}`)).toHaveCount(0);
        await expect(counter).toHaveAttribute('data-selected', String(remaining.length));
        // Not cosmetic: the analysis follows the chips. Read off the table rather
        // than the wire, because this scope may already sit in `queryRisk`'s cache,
        // and a cached answer sends nothing to wait for.
        await expect(lossTable(page)).toHaveAttribute('data-row-count', String(remaining.length), {timeout: 15_000});
        await expect(lossRow(page, removedId)).toHaveCount(0);

        await openPicker(page);
        await expect(addPanel(page).getByTestId(`risk-asset-add-option-${removedId}`), 'a removed asset must be offered back by the "+"').toBeVisible();
        await addThroughPicker(page, [removedId]);
        await expect(counter).toHaveAttribute('data-selected', String(opening.length));
        await expect(lossTable(page)).toHaveAttribute('data-row-count', String(opening.length), {timeout: 15_000});

        // ── (b) the preset loads exactly that broker's holdings ────────────────
        // Started from an empty selection, so the set the preset loads cannot
        // coincide with the one already on screen: a broker holding exactly the
        // user's own assets would otherwise make "the preset loaded them" and "the
        // preset did nothing" the same picture.
        await page.getByTestId('risk-bulk-none').click();
        await expect(counter).toHaveAttribute('data-selected', '0');
        await expect(page.getByTestId('risk-asset-set-empty')).toBeVisible();

        const brokerButton = page.getByTestId('risk-broker-filter-button');
        const dropdown = page.getByTestId('risk-broker-filter-dropdown');
        await brokerButton.click();
        const brokerOption = dropdown.getByTestId(`risk-broker-option-${broker.brokerId}`);
        await expect(brokerOption, 'the preset must offer every broker the user can see').toBeVisible();
        await brokerOption.click();
        await expect(dropdown, 'a command closes its menu when it runs').toHaveCount(0);

        // EXACT: the page's own answer is the oracle. The request names exactly
        // this broker, and the selection is exactly the holdings that answer
        // listed on the page's own list — deduplicated, ascending and capped, as the
        // panel reads them.
        const forBroker = () => reports.filter((report) => sameMembers((report.brokerIds ?? []).map(String), [String(broker.brokerId)]));
        await expect.poll(() => forBroker().length, {timeout: 20_000, message: 'the preset must ask the portfolio report about exactly that broker'}).toBeGreaterThan(0);
        const [report] = forBroker();
        // Only the holdings' ids are read, so the two daily series — what used to
        // make the command wait — are not asked for.
        expect(report.light, 'the preset must ask for the summary without the history and the allocation history').toBe(true);
        const expected = presetIdsOf(report, pageCatalogue(eligibility));
        expect(expected.length, 'the broker held something when probed, so the report the page read must list it too').toBeGreaterThan(0);

        await expect(counter).toHaveAttribute('data-selected', String(expected.length), {timeout: 15_000});
        await expect.poll(async () => scopeKey(await chipIds(page)), {timeout: 15_000, message: 'the chips must be exactly the holdings the page was told about'}).toBe(scopeKey(expected));
        await expect
            .poll(() => requests.some((request) => request.scope.kind === ASSET_SET_SCOPE && scopeKey(request.scope.asset_ids) === scopeKey(expected)), {
                timeout: 15_000,
                message: 'the analysis must be asked about exactly the set the preset loaded',
            })
            .toBe(true);
        await expect(page.getByTestId('risk-broker-filter-error')).toHaveCount(0);

        // TOLERANT, and for a reason: the probe was taken through the API before the
        // page loaded, and `Transaction` has no user_id — a neighbour writing to this
        // shared broker in between moves one side only, so equality with the probe
        // is not assertable. A non-empty overlap survives that drift and still fails
        // if the preset loaded some other broker's assets.
        expect(
            expected.some((assetId) => broker.assetIds.includes(assetId)),
            `the preset must load broker ${broker.brokerId}'s holdings: page saw [${expected.join(', ')}], probe saw [${broker.assetIds.join(', ')}]`,
        ).toBe(true);

        // ── (c) no amount crosses ─────────────────────────────────────────────
        // Two controls first, or the absence below would prove nothing: the payload
        // the preset read really carried money, and the net really recognises money
        // as each shipped locale prints it.
        const valued = report.holdings.filter((holding) => {
            const value = Number(holding.current_value);
            return Number.isFinite(value) && value !== 0;
        });
        expect(valued.length, 'the report the preset read must carry position values, or "no amount crossed" would hold of a payload with nothing to carry').toBeGreaterThan(0);
        for (const locale of ['en-US', 'it-IT', 'fr-FR', 'es-ES']) {
            expect(new Intl.NumberFormat(locale, {style: 'currency', currency: 'EUR'}).format(12345.67), `the amount net must recognise money as ${locale} prints it`).toMatch(GROUPED_AMOUNT_PATTERN);
        }
        // And a presence barrier: the scan must cross a populated analysis of the
        // loaded set, not an empty frame between two renders.
        await waitForLossTable(page);
        await expect(lossTable(page).locator('[data-testid="risk-asset-set-l1-badDay"][data-measured="true"]'), 'L1° must be showing figures for the loaded set').toHaveCount(expected.length);

        const panel = page.getByTestId('asset-global-risk-panel');
        const rendered = await panel.innerText();
        expect(rendered, `the panel printed an amount after the broker preset. Panel text was:\n${rendered}`).not.toMatch(GROUPED_AMOUNT_PATTERN);
        expect(rendered, `the panel printed the stubbed monetary magnitude. Panel text was:\n${rendered}`).not.toMatch(MONEY_PATTERN);
        expect(rendered, 'the panel printed a euro glyph — no amount of money belongs on an unweighted asset set').not.toContain('€');
        await expect(panel.locator('.currency-symbol')).toHaveCount(0);

        // ── (d) a broker holding nothing keeps the selection ────────────────────
        // The preset used to be a select, and its empty option reset the selection
        // to the first hundred assets. It is a command now, with no null state to
        // choose — but a silent wipe of the same kind can still come in through an
        // answer: a discarded one (the next two tests), or one that holds nothing.
        // Nothing held is an answer, not an instruction: the command says so and
        // leaves the selection as it was.
        //
        // Which broker holds nothing on the period's last day is seed data this test
        // does not own, so the state is produced here: the backend's own report for
        // another broker, with its holdings — the one field the command reads — taken
        // out (`withNothingHeld`). Another broker, because the one above is now in
        // the report cache: a cached answer would send nothing to answer. The
        // smallest other id, so a seed broker rather than a neighbour's transient one.
        const kept = await chipIds(page);
        await brokerButton.click();
        await expect(dropdown).toBeVisible();
        const offeredBrokers = (await dropdown.getByTestId(/^risk-broker-option-\d+$/).evaluateAll((nodes) => nodes.map((node) => Number(node.getAttribute('data-testid')?.replace('risk-broker-option-', ''))))).filter((brokerId) => Number.isInteger(brokerId));
        const otherBrokers = offeredBrokers.filter((brokerId) => brokerId !== broker.brokerId).sort((left, right) => left - right);
        if (otherBrokers.length === 0) throw new Error(`The preset offers no broker besides ${broker.brokerId}, so no uncached report can be asked for. Check populate_mock_data.py.`);
        const idleBrokerId = otherBrokers[0];
        const idleReports: CapturedReport[] = [];
        // Quiet (`routeQuietly`): a forward that fails leaves the preset waiting,
        // and the empty state below never comes.
        await routeQuietly(page, '**/api/v1/portfolio/report', async (route) => {
            const sent = (route.request().postDataJSON() ?? {}) as ReportBody;
            if (route.request().method() !== 'POST' || !sameMembers((sent.broker_ids ?? []).map(String), [String(idleBrokerId)])) return route.fallback();
            const response = await route.fetch();
            if (!response.ok()) return route.fulfill({response});
            const answer = withNothingHeld((await response.json()) as Record<string, unknown>);
            idleReports.push(capturedReport(sent, answer));
            await route.fulfill({status: 200, contentType: 'application/json', body: JSON.stringify(answer)});
        });

        await dropdown.getByTestId(`risk-broker-option-${idleBrokerId}`).click();
        await expect(dropdown).toHaveCount(0);
        await expect(page.getByTestId('risk-broker-filter-empty'), 'an answer that holds nothing must be said, not applied').toBeVisible({timeout: 15_000});
        await expect(page.getByTestId('risk-broker-filter-loading')).toHaveCount(0);
        await expect(page.getByTestId('risk-broker-filter-error'), 'nothing held is an answer, not a failure').toHaveCount(0);
        // Read once the command has spoken: it applies — or refuses — in the flush
        // that shows the message, and asks again only after a `null`.
        expect(idleReports, 'the command must ask about that broker once, and take its answer as it came').toHaveLength(1);
        expect(idleReports[0].holdings, 'the answer the command read held nothing').toEqual([]);
        expect(scopeKey(await chipIds(page)), 'a broker holding nothing must leave the selection as it was').toBe(scopeKey(kept));
        await expect(counter).toHaveAttribute('data-selected', String(kept.length));
    });

    test('broker preset: a report discarded by a portfolio mutation in flight is asked for once more, and that answer is the one applied', async ({page}) => {
        // Two presets and two sync runs, each a barrier on a published state; the
        // budget pays for the work, never for a wait on the clock.
        test.setTimeout(60_000);
        await installRiskMocks(page);
        const eligibility = await answerEligibility(page);
        await installSyncMocks(page);
        const reports = await gateReports(page);
        const broker = await brokerWithHoldings(page);

        await openAssetGlobalRiskReleasingSeed(page, reports);
        await waitForRiskCatalog(page);
        const catalogue = await assetCatalogue(page);
        const priced = (assetId: number) => catalogue.get(assetId)?.priced === true;
        // The mutation below is a sync run, and a run needs an item to answer about.
        await ensureSelectedWhere(page, priced, 'asset a provider prices');

        const counter = selectionCounter(page);
        const onPage = pageCatalogue(eligibility);
        const forBroker = () => reports.filter((report) => sameMembers((report.brokerIds ?? []).map(String), [String(broker.brokerId)]));

        // ── The control: nothing moves the cache, so the preset asks once ────────
        await chooseBrokerPreset(page, `risk-broker-option-${broker.brokerId}`);
        await expect.poll(() => forBroker().length, {timeout: 15_000, message: 'the preset must ask for the report'}).toBe(1);
        const undisturbed = presetIdsOf(await forBroker()[0].release(), onPage);
        expect(undisturbed.length, 'the broker held something when probed, so the report the page read must list it too').toBeGreaterThan(0);
        await expect(counter).toHaveAttribute('data-selected', String(undisturbed.length), {timeout: 15_000});
        // Applied, therefore never re-asked: the re-ask replaces the apply, it cannot follow it.
        expect(forBroker(), 'an answer nothing discarded is applied as it is, after one request').toHaveLength(1);

        // A sync to empty the report cache. The preset is a command, so running it
        // again needs no way back to a null state first — but the answer it read is
        // cached now, and a cached answer puts nothing in flight to discard: the next
        // run must reach the wire.
        await ensureSelectedWhere(page, priced, 'asset a provider prices');
        await runSyncToCompletion(page);

        // ── The race, made deterministic ────────────────────────────────────
        await chooseBrokerPreset(page, `risk-broker-option-${broker.brokerId}`);
        await expect.poll(() => forBroker().length, {timeout: 15_000, message: 'with the cache emptied, the preset must ask again'}).toBe(2);
        // The request is out, so the page has read the cache generation; its answer
        // is held. Now the mutation, run to its published end…
        await runSyncToCompletion(page);
        // …and only then the answer, which therefore lands after the invalidation.
        // This is ordering by causality: the answer does not exist until released.
        await forBroker()[1].release();
        await expect.poll(() => forBroker().length, {timeout: 15_000, message: 'a discarded answer must be asked for once more'}).toBe(3);
        const expected = presetIdsOf(await forBroker()[2].release(), onPage);

        await expect(counter).toHaveAttribute('data-selected', String(expected.length), {timeout: 15_000});
        await expect.poll(async () => scopeKey(await chipIds(page)), {timeout: 15_000, message: 'the selection must be exactly the holdings of the answer that was applied'}).toBe(scopeKey(expected));
        await expect(page.getByTestId('risk-broker-filter-loading')).toHaveCount(0);
        await expect(page.getByTestId('risk-broker-filter-error'), 'one discard is recovered, not reported').toHaveCount(0);
        expect(forBroker(), 'one discard costs one re-ask, and the applied answer ends the preset').toHaveLength(3);
    });

    test('broker preset: when the re-asked report is discarded too, the control reports the failure and the selection stays as it was', async ({page}) => {
        test.setTimeout(60_000);
        await installRiskMocks(page);
        await installSyncMocks(page);
        const reports = await gateReports(page);
        const broker = await brokerWithHoldings(page);

        await openAssetGlobalRiskReleasingSeed(page, reports);
        await waitForRiskCatalog(page);
        const catalogue = await assetCatalogue(page);
        await ensureSelectedWhere(page, (assetId) => catalogue.get(assetId)?.priced === true, 'asset a provider prices');

        // Recorded before the preset: the failure must leave exactly this behind.
        const counter = selectionCounter(page);
        const before = await chipIds(page);
        await expect(counter).toHaveAttribute('data-selected', String(before.length));
        const forBroker = () => reports.filter((report) => sameMembers((report.brokerIds ?? []).map(String), [String(broker.brokerId)]));

        await chooseBrokerPreset(page, `risk-broker-option-${broker.brokerId}`);
        await expect.poll(() => forBroker().length, {timeout: 15_000, message: 'the preset must ask for the report'}).toBe(1);
        // First discard: the mutation completes while the first answer is held.
        await runSyncToCompletion(page);
        await forBroker()[0].release();
        await expect.poll(() => forBroker().length, {timeout: 15_000, message: 'the first discard must be asked for once more'}).toBe(2);
        // Second discard: the re-ask is out and held, and a second mutation lands first.
        await runSyncToCompletion(page);
        await forBroker()[1].release();

        await expect(page.getByTestId('risk-broker-filter-error'), 'two discarded answers must end in a visible failure, not in a silent empty selection').toBeVisible({timeout: 15_000});
        await expect(page.getByTestId('risk-broker-filter-loading')).toHaveCount(0);
        expect(scopeKey(await chipIds(page)), 'a failed preset must leave the selection exactly as it found it').toBe(scopeKey(before));
        await expect(counter).toHaveAttribute('data-selected', String(before.length));
        // Read after the failure is on screen, and the failure is the end of the
        // path: `heldAssetIds` gives up after the second null, without asking again.
        expect(forBroker(), 'the second discard is the last word: no third report request').toHaveLength(2);
    });

    test("the toolbar's sync targets the selection's priced assets and every configured pair that converts them into the target currency", async ({page}) => {
        test.setTimeout(45_000);
        const requests = await installRiskMocks(page);
        const syncCalls = await installSyncMocks(page);
        await openAssetGlobalRisk(page);
        await waitForRiskCatalog(page);

        // One sync per page (V1). The lab's — prices *and* the rates that convert
        // them, the capability R2-128 recorded as lost — sits in the page toolbar and
        // opens the lab's own modal; the card carries none of its own, and the grid's
        // prices-only sync does not stand beside it on this tab. Exactly one on the
        // page: a second would mean another surface came back with its own. The
        // visible toolbar button is the presence barrier the two absences lean on.
        const syncButton = page.getByTestId('risk-sync-button');
        await expect(syncButton, 'one price and exchange-rate sync on the page, not one per surface').toHaveCount(1);
        await expect(page.getByTestId('assets-controls').getByTestId('risk-sync-button'), 'the price and exchange-rate sync lives in the page toolbar (R2-128, V1)').toBeVisible();
        await expect(page.getByTestId('risk-asset-set-controls').getByTestId('risk-sync-button'), 'the lab card carries no sync of its own').toHaveCount(0);
        await expect(page.getByTestId('assets-sync-all-button'), "the grid's prices-only sync must not stand beside it on this tab").toBeHidden();

        // The expectation is derived, not assumed: currencies and providers from the
        // list the page is built from, configured pairs from the backend's routes,
        // the target from the page's own requests.
        const catalogue = await assetCatalogue(page);
        const configured = await configuredPairSlugs(page);
        const target = await answerCurrency(requests);
        const priced = (assetId: number) => catalogue.get(assetId)?.priced === true;
        const pairFor = (assetId: number): string | null => {
            const asset = catalogue.get(assetId);
            return asset === undefined || asset.currency === target ? null : pairSlug(asset.currency, target);
        };
        const convertible = (assetId: number) => {
            const pair = pairFor(assetId);
            return pair !== null && configured.has(pair);
        };

        // Both halves must have something to list, or their assertions are about empty lists.
        await ensureSelectedWhere(page, convertible, `asset quoted outside ${target} whose pair to it is configured`);
        await ensureSelectedWhere(page, priced, 'asset a provider prices');

        const selection = await chipIds(page);
        expect(
            selection.filter((assetId) => !catalogue.has(assetId)),
            'every selected asset must be in the list the sync targets are derived from',
        ).toEqual([]);
        const expectedAssets = selection.filter(priced).sort((left, right) => left - right);
        const expectedPairs = [...new Set(selection.filter(convertible).map((assetId) => pairFor(assetId) as string))].sort();
        const expectedCount = expectedAssets.length + expectedPairs.length;
        const expectation = `assets [${expectedAssets.join(', ')}] and pairs [${expectedPairs.join(', ')}] for target ${target}`;

        await expect(syncButton).toBeEnabled();
        await syncButton.click();
        const modal = page.getByTestId('page-sync-modal');
        await expect(modal).toBeVisible();

        // Before a run the modal lists nothing item by item — only its tally, which
        // it republishes as numbers because the sentence around them is translated.
        const tally = modal.getByTestId('sync-modal-count');
        await expect(tally, `the modal must target ${expectation}`).toHaveAttribute('data-item-count', String(expectedCount));
        await expect(tally, 'prices and exchange rates are two sections').toHaveAttribute('data-section-count', '2');

        await modal.getByTestId('sync-modal-start').click();
        const results = modal.getByTestId('sync-modal-results');
        await expect(results).toBeVisible({timeout: 15_000});
        await expect(results).toHaveAttribute('data-total', String(expectedCount));
        await expect(results).toHaveAttribute('data-success', String(expectedCount));

        // The lists, exactly, where they are exact: in what the modal asked for, and
        // in the row it keeps for every item it asked about.
        expect(
            syncCalls.assets.flat().sort((left, right) => left - right),
            `the price sync must be asked about ${expectation}`,
        ).toEqual(expectedAssets);
        expect(syncCalls.fxPairs.flat().sort(), `the rate sync must be asked about ${expectation}`).toEqual(expectedPairs);
        for (const assetId of expectedAssets) {
            await expect(modal.locator(`[data-testid="sync-section"][data-section-id="assets"] [data-testid="sync-result-row"][data-row-id="${assetId}"]`)).toHaveAttribute('data-status', 'ok');
        }
        for (const pair of expectedPairs) {
            await expect(modal.locator(`[data-testid="sync-section"][data-section-id="fx"] [data-testid="sync-result-row"][data-row-id="${pair}"]`)).toHaveAttribute('data-status', 'ok');
        }

        await modal.getByTestId('sync-modal-close').click();
        await expect(modal).toBeHidden();

        // Enabled by a selection, not always: with nothing selected there is nothing to sync.
        await page.getByTestId('risk-bulk-none').click();
        await expect(selectionCounter(page)).toHaveAttribute('data-selected', '0');
        await expect(syncButton).toBeDisabled();
    });

    test('an accepted sync makes every section re-read its base and the replay forget its answer, while a sync closed without running changes nothing', async ({page}) => {
        // Two modal cycles, one replay and one refresh wave: the budget pays for the
        // work, and every wait below is still a barrier on a published state.
        test.setTimeout(60_000);
        const requests = await installRiskMocks(page);
        const syncCalls = await installSyncMocks(page);
        await openAssetGlobalRisk(page);
        await waitForRiskCatalog(page);

        // An accepted run needs one item to answer `ok`; a priced asset is the one
        // the page can always offer, whatever the exchange-rate routes say.
        const catalogue = await assetCatalogue(page);
        await ensureSelectedWhere(page, (assetId) => catalogue.get(assetId)?.priced === true, 'asset a provider prices');
        const selection = await chipIds(page);
        const scope = scopeKey(selection);
        await waitForLossTable(page);
        await expect(lossTable(page)).toHaveAttribute('data-row-count', String(selection.length));
        await openAndRunReplay(page);
        const replayAnswer = page.getByTestId('risk-l4-replay').getByTestId('risk-replay-tornado-row');

        // Each section's own question about this scope, told apart by its shape and
        // counted among this test's captured requests only. The correlation section
        // and the replay section build identical `[correlation]` waves, which
        // `queryRisk` serves from one flight — so that count speaks for both, and the
        // replay's own part of a refresh is its answer, asserted further down. L1° and
        // L3° ask apart (the developer's split, 02/10/2026), so each level is counted
        // on its own: one level re-reading must not pass for both, nor one level's
        // late opening for a refresh.
        const correlationWaves = () => assetSetHistoricalRequests(requests).filter((request) => request.scope.kind === ASSET_SET_SCOPE && scopeKey(request.scope.asset_ids) === scope && sameMembers([...codesOf(request)], ['correlation'])).length;
        const lossWaves = () => lossRequestsFor(requests, selection).length;
        const paidWaves = () => paidRequestsFor(requests, selection).length;
        const replayRuns = () => requests.filter((request) => request.scope.kind === ASSET_SET_SCOPE && scopeKey(request.scope.asset_ids) === scope && request.analytics.some((analytic) => isHistoricalReplay(analytic))).length;
        // Sampled once every base wave is in, so the baseline is not a snapshot of
        // a page still loading.
        await expect.poll(correlationWaves, {timeout: 15_000, message: 'the correlation wave must have been asked'}).toBeGreaterThan(0);
        await expect.poll(lossWaves, {timeout: 15_000, message: 'L1° must have been asked'}).toBeGreaterThan(0);
        await expect.poll(paidWaves, {timeout: 15_000, message: 'L3° must have been asked'}).toBeGreaterThan(0);
        const before = {correlation: correlationWaves(), loss: lossWaves(), paid: paidWaves(), replay: replayRuns()};
        expect(before.replay, 'the replay above must have reached the wire').toBeGreaterThan(0);

        // The page toolbar's sync, which reaches this panel's modal through `openSync`.
        const syncButton = page.getByTestId('risk-sync-button');
        const modal = page.getByTestId('page-sync-modal');

        // ── closed without running ───────────────────────────────────────────
        await syncButton.click();
        await expect(modal).toBeVisible();
        await modal.getByTestId('sync-modal-close').click();
        await expect(modal).toBeHidden();
        // The barrier that makes the absence below readable, and it is a
        // deterministic one: an accepted sync bumps the panel's generation and the
        // replay section forgets its answer in that same flush, before the modal's
        // fade has even started. An answer still on screen once the modal is gone
        // is therefore proof that no refresh was triggered — not a guess about time.
        await expect(replayAnswer.first()).toBeVisible();
        expect(syncCalls.assets.length + syncCalls.fxPairs.length, 'closing the modal must ask no provider for anything').toBe(0);
        expect({correlation: correlationWaves(), loss: lossWaves(), paid: paidWaves(), replay: replayRuns()}, 'a sync that never ran must re-read nothing').toEqual(before);

        // ── an accepted run ──────────────────────────────────────────────────
        await syncButton.click();
        await expect(modal).toBeVisible();
        await modal.getByTestId('sync-modal-start').click();
        const results = modal.getByTestId('sync-modal-results');
        await expect(results).toBeVisible({timeout: 15_000});
        await expect(results, 'every stubbed item answers ok, so the run is accepted').toHaveAttribute('data-failed', '0');
        expect(syncCalls.assets.flat().length, 'the accepted run must have gone through the price-sync stub').toBeGreaterThan(0);

        // Every base is re-read, section by section. `>`, not `=== before + 1`: how
        // many flights one refresh costs is the store's business — the two stubbed
        // sync POSTs are themselves portfolio mutations (`zodios-client` →
        // `notifyPortfolioMutation` → `invalidateRisk`), in-flight sharing merges
        // identical waves, a discarded answer is re-asked, up to three attempts in all —
        // and not this test's subject. That each section re-read its base is.
        await expect.poll(correlationWaves, {timeout: 15_000, message: 'the correlation section must re-read its base after an accepted sync'}).toBeGreaterThan(before.correlation);
        await expect.poll(lossWaves, {timeout: 15_000, message: 'L1° must re-read its base after an accepted sync'}).toBeGreaterThan(before.loss);
        await expect.poll(paidWaves, {timeout: 15_000, message: 'L3° must re-read its base after an accepted sync'}).toBeGreaterThan(before.paid);
        // The replay was computed on the prices just replaced, so it is forgotten —
        // the rung stays, only the answer goes…
        await expect(replayAnswer, 'the replay on screen was computed on the prices the sync replaced').toHaveCount(0);
        await expect(page.getByTestId('risk-replay-total')).toHaveCount(0);
        await expect(page.getByTestId('risk-replay-run')).toBeVisible();
        // …and nothing re-ran it for the reader. Read after the base waves on
        // purpose: a relaunch would be issued in the flush that reset the answer,
        // before the catalogue round trip those waves wait behind.
        expect(replayRuns(), 'the replay is the reader’s to re-run, not the sync’s').toBe(before.replay);

        await modal.getByTestId('sync-modal-close').click();
        await expect(modal).toBeHidden();
        // Still a working page: the re-read landed rather than failed.
        await waitForLossTable(page);
        await expect(lossTable(page)).toHaveAttribute('data-row-count', String(selection.length));
        await expect(page.getByTestId('risk-correlation-error')).toHaveCount(0);
    });

    test("the toolbar's reload makes every section re-read its base, and neither syncs, refreshes the page's prices nor opens the sync modal", async ({page}) => {
        // One opening and one refresh wave: the budget pays for the work, and every
        // wait below is still a barrier on a published state.
        test.setTimeout(45_000);
        const requests = await installRiskMocks(page);

        // Any sync the page could send, recorded and refused: a real one writes
        // prices and reaches external providers, and this file writes nothing. The
        // pattern is wider than the two endpoints `PageSyncModal` calls
        // (`/assets/prices/sync`, `/fx/currencies/sync`), so a sync reached by some
        // other road is caught too.
        const syncCalls: string[] = [];
        await page.route(/\/api\/v1\/(?:assets|fx)\/[^?#]*sync/, async (route) => {
            syncCalls.push(`${route.request().method()} ${new URL(route.request().url()).pathname}`);
            await route.abort();
        });

        // The page's own price series (`fetchAllPriceData`), counted and let through:
        // a read, and exactly what a page price refresh sends again. The live-price
        // poll is held by `installRiskMocks` and not counted — its 30 s timer is not
        // the reload's to answer for.
        let priceQueries = 0;
        await page.route(/\/api\/v1\/assets\/prices\/query(?:\?|$)/, async (route) => {
            priceQueries += 1;
            await route.fallback();
        });

        await openAssetGlobalRisk(page);
        await waitForRiskCatalog(page);
        const selection = await chipIds(page);
        const scope = scopeKey(selection);
        await waitForLossTable(page);
        await expect(lossTable(page)).toHaveAttribute('data-row-count', String(selection.length));
        // Both waves of the page are in — the list, then its prices — so the price
        // count sampled below is not a snapshot of a page still loading.
        await expect(page.getByTestId('assets-page')).toHaveAttribute('data-busy', 'false', {timeout: 15_000});

        // Each section's own question about this scope, counted the way the sync test
        // counts them: the correlation section and the replay section build the same
        // `[correlation]` wave, which `queryRisk` serves from one flight, so that count
        // speaks for both; L1° and L3° ask apart, so each level is counted on its own.
        const correlationWaves = () => assetSetHistoricalRequests(requests).filter((request) => request.scope.kind === ASSET_SET_SCOPE && scopeKey(request.scope.asset_ids) === scope && sameMembers([...codesOf(request)], ['correlation'])).length;
        const lossWaves = () => lossRequestsFor(requests, selection).length;
        const paidWaves = () => paidRequestsFor(requests, selection).length;
        await expect.poll(correlationWaves, {timeout: 15_000, message: 'the correlation wave must have been asked'}).toBeGreaterThan(0);
        await expect.poll(lossWaves, {timeout: 15_000, message: 'L1° must have been asked'}).toBeGreaterThan(0);
        await expect.poll(paidWaves, {timeout: 15_000, message: 'L3° must have been asked'}).toBeGreaterThan(0);
        expect(priceQueries, 'the page must have loaded its price series').toBeGreaterThan(0);
        const before = {correlation: correlationWaves(), loss: lossWaves(), paid: paidWaves(), prices: priceQueries};

        // The reload sits in the page toolbar on this tab, beside the sync.
        const toolbar = page.getByTestId('assets-controls');
        const reload = toolbar.getByTestId('risk-reload-button');
        await expect(reload).toBeVisible();
        await expect(reload).toBeEnabled();
        await reload.click();

        // Every base is re-read, section by section. `>`, as in the sync test: how many
        // flights one refresh costs is the store's business; that each section asked
        // again is this test's.
        await expect.poll(correlationWaves, {timeout: 15_000, message: 'the correlation section, and the replay section with it, must re-read its base after a reload'}).toBeGreaterThan(before.correlation);
        await expect.poll(lossWaves, {timeout: 15_000, message: 'L1° must re-read its base after a reload'}).toBeGreaterThan(before.loss);
        await expect.poll(paidWaves, {timeout: 15_000, message: 'L3° must re-read its base after a reload'}).toBeGreaterThan(before.paid);

        // Still a working page: the re-read landed rather than failed. It is also the
        // barrier the absences below are read behind.
        await waitForLossTable(page);
        await expect(lossTable(page)).toHaveAttribute('data-row-count', String(selection.length));
        await expect(page.getByTestId('risk-correlation-error')).toHaveCount(0);

        // No sync modal — while the sync beside the reload is there and usable, so its
        // modal's absence is the reload's doing, not the page's inability.
        await expect(toolbar.getByTestId('risk-sync-button')).toBeEnabled();
        await expect(page.getByTestId('page-sync-modal'), 'a reload is not a sync: it opens no modal').toHaveCount(0);
        // No sync request and no page price refresh. The one path that sends them
        // sends them before the sections ask again — the modal's run first, then the
        // page's prices, then the sections (`handleSynced`) — so reading them after the
        // re-read is not early.
        expect(syncCalls, 'a reload asks no provider for anything').toEqual([]);
        expect(priceQueries, "a reload re-reads the lab's analysis, never the page's price series").toBe(before.prices);

        // Nothing to restore: every route is this page's own, and nothing but reads
        // reached the database.
    });

    /**
     * The strip that offers the period in which every selected asset has prices.
     *
     * The panel's half is built: a second question to the engine about the selection
     * alone, the strip when that answer suggests a period bringing a selected asset
     * back, and a button that hands the period to the page (`onfitperiod`). The page's
     * half — moving the toolbar to that period and letting go of the preset in force —
     * is what this test waits for. Until it is wired the button does nothing, and the
     * test is red at the period.
     *
     * The engine is scripted (`scriptEligibility`), and nothing is written anywhere:
     * the period lives in this context's URL and store, and the selection in its
     * `localStorage`.
     */
    test('the fit-period strip moves the toolbar to the period in which every selected asset has prices, and lights no preset', async ({page}) => {
        await installRiskMocks(page);
        const engine = await scriptEligibility(page);
        await openAssetGlobalRisk(page);

        // The asset the period will leave behind: picked by value from this test's own selection.
        const selection = await chipIds(page);
        const late = Math.min(...selection);
        engine.setMode({kind: 'late', late: new Set([late])});

        // A preset in force first, so that following the offer has one to let go of.
        const period = await pressPeriodPreset(page, '1y');
        await expect.poll(() => exchangeFor(engine.exchanges, selection, period)?.suggested ?? null, {timeout: 15_000, message: "the selection's own question was not asked for the preset's period, or came back with no suggestion"}).not.toBeNull();
        const asked = exchangeFor(engine.exchanges, selection, period) as EngineExchange;
        expect(asked.notEligible, 'the premise: the period leaves exactly the late asset behind').toEqual([late]);
        const suggested = asked.suggested as DayRange;

        const banner = page.getByTestId('risk-asset-set-controls').getByTestId('risk-fit-period-banner');
        const offer = banner.getByTestId('risk-fit-period-button');
        await expect(banner, 'a selected asset starts after the period does, and the engine suggests a period that brings it back').toBeVisible({timeout: 10_000});
        await expect(banner, 'the strip counts the selected assets the suggestion brings back').toHaveAttribute('data-recoverable', '1');
        await expect(offer).toHaveAttribute('data-start', suggested.start);
        await expect(offer).toHaveAttribute('data-end', suggested.end);

        await offer.click();

        // 🔴 The page takes the period: its dates are the suggested ones…
        await expect.poll(() => urlPeriod(page), {timeout: 10_000, message: "pressing the offer did not move the page's period to the one it offers"}).toEqual(suggested);
        // …no preset claims a period the reader did not pick from the badges…
        await expect(page.getByTestId('date-preset-1y')).toBeVisible();
        await expect(page.locator('[data-testid^="date-preset-"][data-active="true"]'), 'a preset stays lit over a period it does not describe').toHaveCount(0);
        // …and once the new period's answer is in, nobody is left out, so the strip goes.
        await expect.poll(() => exchangeFor(engine.exchanges, selection, suggested)?.fitted ?? false, {timeout: 15_000, message: 'the selection was not asked about the new period'}).toBe(true);
        await expect(banner, 'the strip outlives the problem it offered to fix').toHaveCount(0);
    });

    /**
     * The complement: a suggestion that brings nobody back is not an offer.
     *
     * The engine suggests a period whenever the requested one misses the common span,
     * and a period that merely ends after the last common quote does, with every asset
     * eligible. Shown on its own, the strip's absence would also be true of an answer
     * not applied yet; so the strip is brought on screen first, by a period that leaves
     * an asset behind, and its going is what proves the new answer was read. The panel
     * keeps the previous verdicts until the new ones land.
     */
    test('the fit-period strip stays away when the suggested period would bring no selected asset back', async ({page}) => {
        await installRiskMocks(page);
        const engine = await scriptEligibility(page);
        await openAssetGlobalRisk(page);
        const selection = await chipIds(page);

        // The positive control: a period that leaves an asset behind brings the strip.
        engine.setMode({kind: 'late', late: new Set([Math.min(...selection)])});
        await pressPeriodPreset(page, '1y');
        const banner = page.getByTestId('risk-asset-set-controls').getByTestId('risk-fit-period-banner');
        await expect(banner, 'the positive control: a period that leaves an asset behind must bring the strip').toBeVisible({timeout: 15_000});

        // A period in which every selected asset is eligible, and the engine suggests one all the same.
        engine.setMode({kind: 'trimmedEnd'});
        const period = await pressPeriodPreset(page, '2y');
        await expect.poll(() => exchangeFor(engine.exchanges, selection, period)?.suggested ?? null, {timeout: 15_000, message: "the selection's own question was not asked for the new period, or came back with no suggestion"}).not.toBeNull();
        expect(exchangeFor(engine.exchanges, selection, period)?.notEligible, 'the premise: every selected asset is eligible in the new period').toEqual([]);

        await expect(banner, 'the engine suggests a period, but it brings no selected asset back: there is nothing to offer').toHaveCount(0);
    });
});
