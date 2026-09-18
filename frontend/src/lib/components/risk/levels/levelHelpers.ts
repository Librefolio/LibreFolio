/**
 * Pure logic for the four risk levels.
 *
 * Everything here is a plain function over plain data: no runes, no stores, no
 * components. That is deliberate — it is the part of the four levels that can be
 * asserted without mounting anything, and it keeps each level component down to
 * markup plus a handful of `$derived` reads.
 */
import type {RiskAnalyticResult} from '$lib/stores/risk/riskStore.svelte';
import {singleValue} from '$lib/risk/riskTypes';

import {DAILY_VAR_INSTANCE, MONTHLY_VAR_INSTANCE, resultByCode, resultByInstance} from '../riskAnalysisHelpers';

// Provenance lives in its own module — this file is at its size ceiling and the
// subject is a separate one — but consumers keep a single door onto the level
// helpers, so it is re-exported rather than imported from two places.
export type {LevelMetadataRow} from './levelMetadata';
export {levelMetadata, translateOrRaw} from './levelMetadata';

/**
 * View a value as a plain record without discarding anything.
 *
 * Deliberately not `numberRecord`, which keeps only numeric entries: L1 reads a
 * peak *date* and L2 reads an *array* of items, and both would silently vanish.
 */
export function record(value: unknown): Record<string, unknown> {
    if (value === null || typeof value !== 'object' || Array.isArray(value)) return {};
    return value as Record<string, unknown>;
}

/** A finite number, or null for anything else — including `NaN` and `Infinity`. */
export function finite(value: unknown): number | null {
    return typeof value === 'number' && Number.isFinite(value) ? value : null;
}

/**
 * The output of a result that produced one, `ok` or `partial` alike.
 *
 * `partial` is not an exotic state: the server returns it whenever a degrading
 * warning fired, an asset was excluded for want of a usable series, or the data
 * quality was anything but clean (`service.py:736`). A portfolio with one
 * unpriceable holding is `partial`. Refusing it would blank every level for a
 * reader whose answer is merely incomplete — and it would blank L2 exactly in
 * the case L2 exists to explain, since `cash_weight` is where those excluded
 * assets go.
 *
 * So the numbers are read, and `degradedResults` says out loud that they are
 * partial. Showing less than everything is fine; showing nothing, or showing
 * everything as if it were whole, is not.
 */
export function okOutput(result: RiskAnalyticResult | null): Record<string, unknown> | null {
    if (!result || !result.output) return null;
    if (result.status !== 'ok' && result.status !== 'partial') return null;
    return record(result.output);
}

/** A measurement that did not come back whole, and which way it fell short. */
export interface ResultHealth {
    /**
     * Identity of the measurement, and the only field unique per entry.
     *
     * `analytic_code` is **not** unique: L1 asks for `historical_var` twice, at
     * one day and at one month, and the two are told apart solely by instance.
     * Keying a list by the code would therefore collide precisely when both
     * horizons fail — the case the disclosure exists for.
     */
    instanceId: string;
    code: string;
    status: 'partial' | 'unavailable' | 'failed';
    /**
     * i18n key naming this measurement, when the analytic name would be ambiguous.
     *
     * Two `historical_var` instances both render as "Historical VaR", which tells
     * the reader that a VaR is missing but not *which* — and the whole point of
     * L1's scale is that a day and a month are not interchangeable.
     */
    label?: string;
}

/**
 * Every result in a wave that is not whole.
 *
 * Exists because omission is not disclosure. A level that simply leaves out the
 * rung it could not compute shows a shorter list, and a shorter list is
 * indistinguishable from a portfolio that has less to say. The reader cannot
 * tell "not computed" from "not applicable" — and of the two, only one is worth
 * retrying.
 *
 * Callers pass **only the results their level actually renders**: disclosing a
 * fault under a question that never consulted it is not transparency, it is a
 * false accusation the reader has no way to check.
 */
export function degradedResults(results: ReadonlyArray<RiskAnalyticResult | null | undefined>, labels: Readonly<Record<string, string>> = {}): ResultHealth[] {
    const health: ResultHealth[] = [];
    for (const result of results) {
        if (!result) continue;
        const status = result.status;
        if (status === 'partial' || status === 'unavailable' || status === 'failed') {
            const label = labels[result.instance_id];
            health.push(label ? {instanceId: result.instance_id, code: result.analytic_code, status, label} : {instanceId: result.instance_id, code: result.analytic_code, status});
        }
    }
    return health;
}

/** One reason a wave did not come back whole, in the backend's own words. */
export interface ResultReason {
    /** Stable identity for keying; the message may repeat across analytics. */
    key: string;
    /** The backend's sentence, rendered verbatim. */
    message: string;
    /** How many results carried this same sentence. */
    occurrences: number;
}

/**
 * The reasons behind a degraded wave, deduplicated but counted.
 *
 * `degradedResults` says *that* a measurement fell short; this says *why*. Status
 * without cause leaves the reader's real question — "can I trust this number?" —
 * open while appearing to have answered it.
 *
 * Two deliberate choices:
 *
 * **Nothing is filtered on `degrades_result`.** That flag decides the *status*,
 * which is already on screen, and it is not a synonym for "worth reading": the
 * one warning in the tree that sets it to `false` reports that an asset's sector
 * metadata was missing and it was treated as "Other" at 100%. The number is not
 * degraded — the *meaning* of a sector shock computed that way is. Hiding it
 * would withhold exactly the sentence that explains the shape on screen.
 *
 * **Nothing is translated.** These are backend strings. Mapping them onto i18n
 * keys built at runtime is the defect already found at `RiskResultFrame:108`,
 * where an unseen value printed its own key on screen. Verbatim, or nothing.
 *
 * Note that a `partial` with **no** warnings at all is ordinary, not a bug:
 * `service.py:736` also turns a wave partial for context exclusions, excluded
 * assets, or data quality — each disclosed by its own surface.
 */
export function resultReasons(results: ReadonlyArray<RiskAnalyticResult | null | undefined>): ResultReason[] {
    const byMessage = new Map<string, ResultReason>();
    for (const result of results) {
        if (!result) continue;
        for (const warning of result.warnings ?? []) {
            const message = typeof warning?.message === 'string' ? warning.message.trim() : '';
            if (!message) continue;
            const existing = byMessage.get(message);
            // Deduplicated by the sentence rather than by `code`, because the
            // sentence *is* what is shown: printing it twice would read as a
            // rendering fault, not as "two assets". The arity is kept in
            // `occurrences` so it is published instead of lost.
            if (existing) existing.occurrences += 1;
            else byMessage.set(message, {key: `${warning?.code ?? 'warning'}:${message}`, message, occurrences: 1});
        }
    }
    return [...byMessage.values()];
}

/**
 * The error codes of results that failed outright, deduplicated, in arrival order.
 *
 * **Codes, never sentences, and never translations.** `resultReasons` above
 * carries backend prose verbatim, and mixing a translated string into that list
 * would make the list's own contract unreadable: a caller could no longer tell
 * which entries it may show to a user in another language. So the two travel
 * separately, and this one carries the *identifier* while the rendering layer
 * owns the wording.
 *
 * ⚠️ Read through `singleValue`, exactly as `RiskResultFrame:23` does. The field
 * is typed as a value *or a list* by the generated client, so `result.error.code`
 * happens to work on today's payload and returns `undefined` the day one arrives
 * wrapped — disclosing nothing, silently.
 *
 * Why this exists at all: the levels decide their empty state from the *shape of
 * the derived rows*, so "out of scope", "not enough history", "no result" and
 * "the answer has not arrived yet" all render one sentence — and that sentence
 * blames the user's data for a limit of the analytic. The legacy frame told the
 * truth here, and the redesign lost it.
 */
export function resultErrorCodes(results: ReadonlyArray<RiskAnalyticResult | null | undefined>): string[] {
    const codes: string[] = [];
    for (const result of results) {
        if (!result) continue;
        const code = singleValue(result.error)?.code;
        if (typeof code !== 'string') continue;
        const trimmed = code.trim();
        if (trimmed === '' || codes.includes(trimmed)) continue;
        codes.push(trimmed);
    }
    return codes;
}

/**
 * One backend error code as a sentence, falling back rather than leaking the key.
 *
 * ⚠️ `translated === key` is the whole mechanism, and it is not a precaution:
 * `svelte-i18n` returns the key itself when no message exists, so without this
 * comparison an error code the backend gains tomorrow prints `risk.errors.foo`
 * on screen. That is the defect recorded at `RiskResultFrame:108`, which is why
 * this is a function with tests rather than three lines inlined in a component.
 *
 * The translator is **passed in** rather than imported. `$t` is a store, and a
 * module reading it through `get()` computes the sentence once, at derivation
 * time: the text would then survive a language change unchanged until the data
 * happened to move. Taking it as an argument keeps the call inside the caller's
 * reactive scope, where switching locale re-runs it.
 */
export function translateErrorCode(code: string | null | undefined, translate: (key: string) => string, fallbackKey: string): string {
    if (!code) return translate(fallbackKey);
    const key = `risk.errors.${code}`;
    const translated = translate(key);
    return translated === key ? translate(fallbackKey) : translated;
}

/**
 * Which asset the comparison figures were actually computed against.
 *
 * Read from the **answer**, never from the picker. The two disagree for as long
 * as a run is in flight, and during that window a label taken from the picker
 * would put the newly chosen benchmark's name under a beta still measured
 * against the previous one — a mislabelled number, which reads as a right answer
 * rather than as a missing one.
 */
export function comparedAssetId(result: RiskAnalyticResult | null | undefined): number | null {
    const output = okOutput(result ?? null);
    return finite(output?.comparison_asset_id);
}

/**
 * The value `return_basis` carries when the series is a backtest, not a report.
 *
 * Compared as a **literal string**, never as an enum member: C's
 * `RiskReturnBasis.CURRENT_COMPOSITION_BACKTEST` does not exist in this tree yet,
 * so importing it would not compile — while the wire has always carried a plain
 * string. The comparison is therefore correct *before* the integration, where it
 * simply never matches and nothing appears, and correct *after* it, with nobody
 * having to come back and change it.
 */
export const BACKTEST_RETURN_BASIS = 'current_composition_backtest';

/**
 * Whether the historical series stopped being a record of what happened.
 *
 * With a slice active, the backend cannot use the report's TWRR — that filters by
 * broker only — so it recomposes the series from **today's weights**. The two
 * answer different questions: TWRR says *how it actually went*, a weighted
 * recomposition says *how today's composition would have gone*. The second is a
 * backtest, and a backtest presented as a report is a wrong answer that reads as
 * a right one.
 *
 * Read across the whole wave rather than from one result, because the basis is a
 * property of the series every historical analytic consumed — so the notice
 * belongs above all of them, not inside the one that happened to be inspected.
 */
export function backtestDeclared(results: ReadonlyArray<RiskAnalyticResult | null | undefined>): boolean {
    for (const result of results) {
        if (!result) continue;
        const metadata = record(result.metadata);
        if (metadata.return_basis === BACKTEST_RETURN_BASIS) return true;
    }
    return false;
}

/**
 * Which side of zero a field states its losses on.
 *
 * The backend carries **two opposite conventions**, each self-consistent and
 * mutually contradictory: `RiskKpiOutput.max_drawdown` is constrained `le=0`,
 * `RiskVarCvarOutput.value_at_risk` is constrained `ge=0`. Neither is wrong —
 * but L1 stacks them in one column, so it must pick one and convert at the read.
 */
export type LossSign = 'negative' | 'positive';

/**
 * Read a loss as a positive magnitude, honouring the field's declared convention.
 *
 * The convention is **declared per field, never sniffed from the value**. A bare
 * `Math.abs` would look equivalent and is not: it silently rescues a number that
 * contradicts its own contract, so a `le=0` field arriving positive would render
 * as a plausible loss instead of as a fault. The server validates its side, but a
 * *fixture* is not validated by Pydantic — and a mock that drifts from the schema
 * does not fail, it reassures.
 *
 * A contradiction therefore reads as **absent**, which L1 already knows how to
 * render, rather than as a number nobody can distinguish from a real one.
 */
export function lossMagnitude(value: unknown, sign: LossSign): number | null {
    const raw = finite(value);
    if (raw === null) return null;
    if (raw === 0) return 0;
    return raw < 0 === (sign === 'negative') ? Math.abs(raw) : null;
}

/* ------------------------------------------------------------------ L1 --- */

/**
 * One rung of L1's scale of harm.
 *
 * `loss` and `secondaryLoss` are **positive magnitudes** — the sign lives in the
 * presentation, not in the datum, because the whole section is about losses and
 * a column of minus signs carries no information.
 */
export interface HurtRow {
    /** Stable id, used for the test id, the i18n key and the doc link. */
    id: 'day' | 'month' | 'worst';
    /** The headline loss as a positive fraction, e.g. `0.018` for −1,8%. */
    loss: number;
    /** The quieter companion figure, when the row has one. */
    secondaryLoss: number | null;
    /** Days the worst fall lasted; only the `worst` row has it. */
    durationDays: number | null;
    /** Gain needed to get back to the prior peak, as a positive fraction. */
    requiredRecovery: number | null;
}

/**
 * The gain required to undo a loss.
 *
 * The asymmetry that makes drawdowns expensive: −10% needs +11,1%, −50% needs
 * +100%. Losing everything can never be undone, so a total loss returns null
 * rather than Infinity — there is no number to show.
 */
export function requiredRecovery(lossFraction: number): number | null {
    if (!Number.isFinite(lossFraction) || lossFraction <= 0) return null;
    if (lossFraction >= 1) return null;
    return 1 / (1 - lossFraction) - 1;
}

/**
 * Build L1's rows from the base wave.
 *
 * Rules that are not negotiable, and why:
 * - the **CVaR leads** and the VaR follows: a VaR states a threshold and then
 *   says nothing whatsoever about how bad things are beyond it, which is the
 *   half the reader actually cares about;
 * - a rung whose analytic failed or never ran is **omitted**, never zero-filled:
 *   an absent measurement and a measurement of zero are different claims;
 * - the order is fixed day → month → worst, because the point of the section is
 *   that the three are on *different scales* and the scale must be legible.
 */
export function buildHurtRows(historicalResults: RiskAnalyticResult[]): HurtRow[] {
    const rows: HurtRow[] = [];

    const varRow = (id: 'day' | 'month', instanceId: string): void => {
        const output = okOutput(resultByInstance(historicalResults, instanceId));
        if (!output) return;
        const cvar = lossMagnitude(output.conditional_value_at_risk, 'positive');
        const value = lossMagnitude(output.value_at_risk, 'positive');
        // Both are positive magnitudes in the API. The CVaR leads; the VaR is
        // only worth printing when it actually differs from it.
        const loss = cvar ?? value;
        if (loss === null) return;
        rows.push({
            id,
            loss,
            secondaryLoss: cvar !== null && value !== null && value !== cvar ? value : null,
            durationDays: null,
            requiredRecovery: null,
        });
    };

    varRow('day', DAILY_VAR_INSTANCE);
    varRow('month', MONTHLY_VAR_INSTANCE);

    // The worst fall prefers the drawdown summary, which carries the dates and
    // the duration, and falls back to the KPI, which carries the depth alone.
    const drawdown = okOutput(resultByCode(historicalResults, 'drawdown_summary'));
    const kpi = okOutput(resultByCode(historicalResults, 'historical_kpi'));
    const depth = lossMagnitude(drawdown?.maximum_drawdown, 'negative') ?? lossMagnitude(kpi?.max_drawdown, 'negative');
    if (depth !== null) {
        // Already a magnitude: the sign was consumed by its declared convention.
        const loss = depth;
        rows.push({
            id: 'worst',
            loss,
            secondaryLoss: null,
            durationDays: finite(drawdown?.maximum_drawdown_duration_days) ?? finite(kpi?.max_drawdown_duration_days),
            requiredRecovery: requiredRecovery(loss),
        });
    }

    return rows;
}

/** The live fall from the last peak, which is a different question from the worst one. */
export interface CurrentDrawdown {
    loss: number;
    peakDate: string | null;
    durationDays: number | null;
    requiredRecovery: number | null;
}

/**
 * The drawdown the portfolio is in *right now*, or null when it sits at a peak.
 *
 * Kept apart from {@link buildHurtRows} on purpose: the rows answer "how bad has
 * it been", this answers "where am I now", and merging them would invite the
 * reader to add a historical worst case to a present position.
 */
export function buildCurrentDrawdown(historicalResults: RiskAnalyticResult[]): CurrentDrawdown | null {
    const output = okOutput(resultByCode(historicalResults, 'drawdown_summary'));
    if (!output) return null;
    const current = finite(output.current_drawdown);
    if (current === null || current >= 0) return null;
    const loss = Math.abs(current);
    const peak = output.current_peak_date;
    return {
        loss,
        peakDate: typeof peak === 'string' ? peak : null,
        durationDays: finite(output.current_drawdown_duration_days),
        requiredRecovery: requiredRecovery(loss),
    };
}

/* ------------------------------------------------------------------ L2 --- */

/**
 * One asset's answer to "am I diversified like I think I am".
 *
 * `divergence` is the whole point: the gap between what a holding *weighs* and
 * how much risk it *produces*. Weight alone flatters a concentrated book; risk
 * contribution alone does not say whether that contribution is surprising.
 */
export interface DivergenceRow {
    assetId: number;
    weight: number;
    contribution: number;
    divergence: number;
}

/**
 * Weight against risk contribution, ordered by the gap between them.
 *
 * Sorted by **signed** divergence descending, so the assets that risk more than
 * they weigh come first — that is the row the reader came for. Risk-reducing
 * assets have a negative contribution and land at the bottom, which is also why
 * the chart must be a diverging bar and never a pie or a treemap: neither can
 * draw a negative slice.
 *
 * Rows whose contribution the backend could not compute are dropped rather than
 * treated as zero, which would frame an unknown as "produces no risk".
 */
export function buildDivergenceRows(contributionResult: RiskAnalyticResult | null): DivergenceRow[] {
    const output = okOutput(contributionResult);
    const items = Array.isArray(output?.items) ? output.items : [];
    const rows: DivergenceRow[] = [];
    for (const raw of items) {
        const item = record(raw);
        const assetId = finite(item.asset_id);
        const weight = finite(item.weight);
        const percentage = finite(item.percentage_contribution);
        if (assetId === null || weight === null || percentage === null) continue;
        // Both arrive as **fractions**. `percentage_contribution` is named for the
        // question it answers, not for its scale: the backend computes it as
        // `component / portfolio_volatility` (services/risk/metrics.py:487), and
        // its own API test asserts the items sum to 1,0 — not to 100. Dividing by
        // a hundred here made every contribution a hundredth of itself, so every
        // holding read as a risk *reducer* and the diverging bars pointed the
        // wrong way: a 60% weight producing 65% of the risk rendered as −59,4pp.
        const contribution = percentage;
        rows.push({assetId, weight, contribution, divergence: contribution - weight});
    }
    rows.sort((a, b) => b.divergence - a.divergence || a.assetId - b.assetId);
    return rows;
}

/**
 * The single sentence L2 leads with, as data rather than prose.
 *
 * Returns the most divergent row only when the gap is worth a headline; below
 * that the honest answer is that nothing stands out, and inventing a headline
 * out of noise would be worse than staying quiet.
 */
export function leadDivergence(rows: DivergenceRow[], minimumGap = 0.05): DivergenceRow | null {
    const top = rows[0];
    if (!top || top.divergence < minimumGap) return null;
    return top;
}

/**
 * How many *independent* bets the portfolio really holds.
 *
 * The two numbers are returned **together or not at all**, and that is the whole
 * point of the type. The effective number of assets is blind to correlation:
 * ten equally weighted holdings score 10,00 whether their pairwise correlation
 * is 0 or 0,95. Shown alone it congratulates a portfolio that is one bet wearing
 * ten names — precisely the illusion L2 exists to break. The diversification
 * ratio is what notices: for those ten holdings it is `1/√(0,1 + 0,9ρ)`, so it
 * reads 3,16 at ρ = 0, about 1,35 at ρ = 0,5, and 1,02 at ρ = 0,95 — collapsing
 * to "no benefit" exactly where the other number still says ten.
 *
 * Making the pair a single nullable value means a caller *cannot* render one
 * without the other by accident. It is not a guideline if the type enforces it.
 */
export interface Concentration {
    /**
     * Concentration index, **not** a count of holdings, despite the name.
     *
     * `1/Σw²` over weights that are fractions of NAV, with cash in the
     * denominator but never a term of its own. So whenever cash is a large
     * share of NAV the positions' own weights are small, their squares smaller
     * still, and the index rises **far above the number of holdings** — it can
     * read in double figures over a mere handful of positions. The arithmetic is
     * right and the parity with AI Export (`broker_concentration_context.py:97`)
     * depends on it; the word "count" is what would be wrong. An index promises
     * no maximum, a count does — and a card whose "effective number of assets"
     * plainly exceeds the holdings listed beneath it tells the reader the
     * software is broken.
     *
     * The case is described in shape and not in figures on purpose: the mock
     * seeds its RNG per `(asset, date)` (`populate_mock_data.py:2162`) while the
     * window ends at `date.today()`, so a single date's price is stable forever
     * but **anything integrating over the window moves every day**. A measured
     * aggregate written here would be false tomorrow, and nothing would fail.
     *
     * Never alone, and never without the cash weight beside it.
     */
    effectiveNumberOfAssets: number;
    /** Weighted average volatility over portfolio volatility; 1,0 = no benefit. */
    diversificationRatio: number;
}

export function buildConcentration(contributionResult: RiskAnalyticResult | null): Concentration | null {
    const output = okOutput(contributionResult);
    if (!output) return null;
    const effectiveNumberOfAssets = finite(output.effective_number_of_assets);
    const diversificationRatio = finite(output.diversification_ratio);
    // Both are constrained `gt=0`; a non-positive value is a contract fault, not
    // a portfolio with zero independent bets, so it reads as absent.
    if (effectiveNumberOfAssets === null || effectiveNumberOfAssets <= 0) return null;
    if (diversificationRatio === null || diversificationRatio <= 0) return null;
    return {effectiveNumberOfAssets, diversificationRatio};
}

/**
 * The share of the portfolio the risk model does **not** speak for.
 *
 * `cash_weight` is a residual — `max(0, 1 − Σ usable weights)` — so it absorbs
 * genuine cash *and* every holding dropped for want of a usable price series.
 * Calling it "cash" on screen is false the moment one asset cannot be priced,
 * and the reader would take a modelling gap for a deliberate allocation.
 */
export function uncoveredWeight(contributionResult: RiskAnalyticResult | null): number | null {
    const output = okOutput(contributionResult);
    if (!output) return null;
    const weight = finite(output.cash_weight);
    if (weight === null || weight < 0) return null;
    return weight;
}

/* ------------------------------------------------------------------ L3 --- */

/** The risk-adjusted view: is the risk being paid for, and against what. */
export interface RiskAdjusted {
    sortino: number | null;
    sharpe: number | null;
    volatility: number | null;
    beta: number | null;
}

/**
 * Collect L3's figures.
 *
 * Sortino comes first everywhere it is shown: Sharpe divides by total
 * volatility, so it penalises violent *rises* exactly as it penalises falls,
 * which flatters a flat portfolio over a lumpy but rewarding one. Sharpe still
 * appears, quietly, because it is the number most readers have seen elsewhere
 * and omitting it would read as hiding it. Neither is rendered as a grade.
 */
export function buildRiskAdjusted(historicalResults: RiskAnalyticResult[], comparisonResult: RiskAnalyticResult | null): RiskAdjusted {
    const kpi = okOutput(resultByCode(historicalResults, 'historical_kpi'));
    const comparison = okOutput(comparisonResult);
    return {
        sortino: finite(kpi?.sortino),
        sharpe: finite(kpi?.sharpe),
        volatility: finite(kpi?.volatility),
        beta: finite(comparison?.beta),
    };
}
