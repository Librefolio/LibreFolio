/**
 * l3Helpers — the two decisions L3 makes before it draws anything.
 *
 * Kept out of the component for the house reason: arithmetic and choice get a
 * spec, drawing does not. There are exactly two things here, and both are
 * decisions rather than formatting.
 *
 * ⚠️ WHY A PERIMETER HAS TO BE CHOSEN AT ALL, AND WHY THE CARD MUST NAME IT.
 * The backend can measure this portfolio two ways. In `historical` the series is
 * what the portfolio actually did — which, for a portfolio that was mostly cash
 * for most of the window, is dominated by deposits rather than by markets. In
 * `current_composition` it is today's weights replayed over past asset returns.
 *
 * On such a portfolio the first can correlate with a stock index at essentially
 * zero, and a beta computed there is not an imprecise estimate: with no
 * covariance there is nothing to estimate. The same portfolio, the same
 * benchmark and the same days can correlate strongly under the second. The
 * ratios move too: Sharpe and Sortino can differ between the perimeters by more
 * than half their own value.
 *
 * L3 asks "am I being paid for this risk" in the present tense, so it wants the
 * second. But a gap that size may not be left implicit: a Sortino from one
 * perimeter beside a beta from the other is two incompatible claims printed on
 * one row, and nothing on screen would say so. Hence `selectKpiWave`, which
 * returns the perimeter it picked so the card can state it, read from the
 * payload's own `metadata` rather than assumed by the caller.
 *
 * The measured case that settled this — with its fixture, its lane and the day
 * it was taken — is recorded in the journal, under
 * `Release_2/Phase_0/02_riskfolioIntegration/implementation_2/progress/`. The
 * figures are deliberately not copied here: the mock dataset moves, and a number
 * quoted without its dataset turns into a claim about the product.
 */
import {finite, okOutput, record} from './levelHelpers';
import type {RiskAnalyticResult} from '$lib/stores/risk/riskStore.svelte';
import {resultByCode} from '../riskAnalysisHelpers';
import type {RiskReturnPoint} from '$lib/components/charts/scatterChartHelpers';

/** Which series the figures on screen were measured on. */
export type KpiPerimeter = 'current_composition' | 'historical';

export interface KpiWave {
    /** The wave to read `historical_kpi` out of. Empty when neither has it. */
    results: RiskAnalyticResult[];
    /** What that wave measured, or `null` when there is nothing to declare. */
    perimeter: KpiPerimeter | null;
}

/**
 * Prefer the current composition, fall back to the historical wave.
 *
 * The fallback is not defensive padding: a backend that does not advertise
 * `historical_kpi` for `current_composition` never receives the request, so on
 * an older install — and on any scope where the mode does not apply — the
 * current wave simply has no KPI. Showing em-dashes there would be a regression
 * caused by an improvement.
 *
 * The perimeter is taken from the chosen result's own `metadata.mode`, never
 * from which array it came out of. The two agree today; if they ever stop
 * agreeing, the payload is right and the caller's bookkeeping is wrong.
 */
export function selectKpiWave(currentResults: RiskAnalyticResult[], historicalResults: RiskAnalyticResult[]): KpiWave {
    for (const candidate of [currentResults, historicalResults]) {
        const result = resultByCode(candidate, 'historical_kpi');
        if (!okOutput(result)) continue;
        const mode = record(result?.metadata).mode;
        return {
            results: candidate,
            perimeter: mode === 'current_composition' || mode === 'historical' ? mode : null,
        };
    }
    return {results: historicalResults, perimeter: null};
}

export interface RiskReturnInput {
    /** `asset_risk_return`, from the current-composition wave. */
    riskReturnResult: RiskAnalyticResult | null;
    /** `comparison`, which carries the benchmark's own risk and reward. */
    comparisonResult: RiskAnalyticResult | null;
    /** Display names, resolved by the panel where every other name already is. */
    assetNames: Record<number, string>;
    /** The benchmark's name, or null when none is chosen. */
    benchmarkName: string | null;
    /** Label for the portfolio's own dot, already translated. */
    portfolioLabel: string;
}

/**
 * Assemble the scatter's points: every holding, the portfolio, the benchmark.
 *
 * ⚠️ THE BUBBLE IS PROPORTIONAL TO WEIGHT ONLY FOR THE ASSETS, and the weights
 * are the real ones — share of net worth, exactly as the backend states them,
 * **not** renormalised to the invested part. So the asset bubbles do not add up
 * to the portfolio's: the missing area is the cash, and that is a fact about the
 * portfolio rather than a gap in the chart. The portfolio carries weight 1
 * because it is the whole of itself; sizing it by anything else would encode a
 * quantity that does not exist.
 *
 * ⚠️ CASH IS NOT A POINT. It would sit at (0, 0) with roughly half the weight,
 * and under the backtest's model that is exactly right — which is the problem.
 * A zero return for cash is a modelling assumption, and drawing it as a dot
 * would publish an assumption in the same ink as seven measurements. The card
 * states the cash share in words instead.
 *
 * Both coordinates are fractions, as `ScatterChart` requires, and the return is
 * the arithmetic expected one: paired with the volatility it makes the line's
 * slope identically the Sharpe ratio, which is what licenses reading "above the
 * line" as "better paid for the risk taken".
 */
export function buildRiskReturnPoints({riskReturnResult, comparisonResult, assetNames, benchmarkName, portfolioLabel}: RiskReturnInput): RiskReturnPoint[] {
    const output = okOutput(riskReturnResult);
    if (!output) return [];

    const points: RiskReturnPoint[] = [];
    const portfolioVolatility = finite(output.portfolio_volatility);
    const portfolioReturn = finite(output.portfolio_expected_annual_return);
    if (portfolioVolatility !== null && portfolioReturn !== null) {
        points.push({
            id: 'portfolio',
            name: portfolioLabel,
            volatility: portfolioVolatility,
            annualReturn: portfolioReturn,
            weight: 1,
            role: 'portfolio',
        });
    }

    const items = Array.isArray(output.items) ? output.items : [];
    for (const raw of items) {
        const item = record(raw);
        const assetId = finite(item.asset_id);
        const volatility = finite(item.volatility);
        const annualReturn = finite(item.expected_annual_return);
        if (assetId === null || volatility === null || annualReturn === null) continue;
        const weight = finite(item.weight);
        points.push({
            id: `asset-${assetId}`,
            name: assetNames[assetId] ?? `#${assetId}`,
            volatility,
            annualReturn,
            weight: weight === null ? undefined : weight,
            role: 'asset',
        });
    }

    // The benchmark rides on the comparison answer, so it appears only once that
    // answer exists — and it is measured on the same common days as the beta above
    // it, never on the reference's full history.
    //
    // ⚠️ AND IT MUST NOT BE TAKEN FROM `historical_kpi` ON THE BENCHMARK ASSET, even
    // though that analytic publishes a volatility for it and the request would look
    // tidier. That figure is prepared differently: asset scope, historical mode, its
    // own joint calendar — a different number of observations over the *same*
    // reported `analyzed_range`. Mixing it with a beta from this wave breaks the
    // textbook identity `sigma_b = rho * sigma_p / beta` by roughly a fifth, and
    // nothing on screen would show why, because `n_observations` is the only field
    // that differs and no card displays it. The dot would land in a place no
    // measurement puts it, on a chart that still looks right.
    //
    // Read from `comparison` instead, and the identity closes to machine precision —
    // structurally, not by luck of the dataset: the service folds the comparison
    // asset into the joint preparation, so the primary series and the reference are
    // born on the same dates. Measured on both seeded benchmarks; the figures, the
    // lane and the window are in the journal, under
    // `Release_2/Phase_0/02_riskfolioIntegration/implementation_2/progress/`.
    const comparison = okOutput(comparisonResult);
    const benchmarkVolatility = finite(comparison?.comparison_volatility);
    const benchmarkReturn = finite(comparison?.comparison_expected_annual_return);
    const benchmarkId = finite(comparison?.comparison_asset_id);
    if (benchmarkVolatility !== null && benchmarkReturn !== null) {
        points.push({
            id: 'benchmark',
            name: benchmarkName ?? (benchmarkId === null ? '' : (assetNames[benchmarkId] ?? `#${benchmarkId}`)),
            volatility: benchmarkVolatility,
            annualReturn: benchmarkReturn,
            role: 'benchmark',
        });
    }

    return points;
}

/** The cash share the scatter deliberately does not draw, or null when unknown. */
export function cashWeight(riskReturnResult: RiskAnalyticResult | null): number | null {
    return finite(okOutput(riskReturnResult)?.cash_weight);
}
