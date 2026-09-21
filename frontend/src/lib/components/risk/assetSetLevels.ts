/**
 * The arithmetic of the asset-set levels, kept out of the components.
 *
 * L1° and L3° both answer "how do *these* compare", so both are tables of one
 * row per selected asset. That shape is the whole reason this file exists: the
 * singular levels take one scope and produce a fixed handful of figures, while
 * these take *n* assets and produce *n* rows. A row is assembled from up to
 * three separate analytics that each answer for every asset, so the joining —
 * "which asset is this, and what did each analytic say about it" — is real
 * logic with real edge cases, and it is testable without mounting anything.
 *
 * 🔑 THE RULE THIS FILE ENFORCES, AND IT IS NOT A FORMATTING CHOICE. An asset
 * set carries no weights, so nothing here computes, returns or accepts an
 * amount. Every figure is a fraction or a ratio. There is no `currency`
 * parameter to forget to pass.
 *
 * 🔴 AND THE SECOND RULE: A SELECTED ASSET ALWAYS GETS A ROW.
 * An analytic may answer for fewer assets than were asked about — a series too
 * short to measure is dropped by the backend rather than zero-filled, which is
 * the honest outcome. But dropping the *row* would be a different claim: the
 * reader chose that asset, and a missing row reads as "not selected", not as
 * "not measurable". So rows are built from the selection and the cells are
 * nullable, never the other way round.
 */
import {schemas} from '$lib/api';
import type {RiskAnalyticResult} from '$lib/stores/risk/riskStore.svelte';
import {riskOutput, singleValue} from '$lib/risk/riskTypes';

/** One row of the L1° comparison: what this asset did to whoever held it. */
export interface AssetSetHurtRow {
    assetId: number;
    name: string;
    /** CVaR 95% over one day, as a positive loss fraction. Null when unmeasured. */
    badDay: number | null;
    /** CVaR 95% compounded over ~1 month, as a positive loss fraction. */
    badMonth: number | null;
    /** Deepest peak-to-trough fall, as a negative fraction. */
    worstFall: number | null;
    /** Calendar days the deepest fall lasted. */
    worstFallDays: number | null;
    /** Whether the deepest fall has been recovered, and when. */
    recovery: string | null;
    /** How far below its own peak the asset sits today, as a negative fraction. */
    currentFall: number | null;
    /** The rise still needed to return to that peak, as a positive fraction. */
    toPeak: number | null;
}

/** One row of the L3° comparison: what this asset risked and what it paid. */
export interface AssetSetPaidRow {
    assetId: number;
    name: string;
    /** Annualised volatility, as a fraction. */
    volatility: number | null;
    /** Mean-variance expected annual return, as a fraction. */
    expectedReturn: number | null;
    sharpe: number | null;
    sortino: number | null;
    /** Sensitivity to the shared benchmark. Null when no benchmark applies. */
    beta: number | null;
    /** Correlation with that benchmark, over the same joint calendar. */
    correlation: number | null;
}

/** The benchmark's own coordinates, so a scatter can place it beside the rest. */
export interface AssetSetBenchmarkPoint {
    assetId: number;
    name: string;
    volatility: number;
    expectedReturn: number;
}

/**
 * Index a parsed item list by `asset_id`, so a row can look its own cells up.
 *
 * Generic over the item type on purpose: each analytic publishes a different
 * shape, and keeping the type through the index is what makes the compiler check
 * every field name below against the generated contract. A `Record<string,
 * unknown>` would have accepted `conditional_value_at_risk` on a drawdown item
 * and failed silently at runtime, which is the whole class of bug the zod client
 * exists to remove.
 */
function byAsset<T extends {asset_id: number}>(items: readonly T[] | undefined): Map<number, T> {
    const index = new Map<number, T>();
    for (const item of items ?? []) index.set(item.asset_id, item);
    return index;
}

/**
 * A finite number, or null — through the house unwrapper.
 *
 * ⚠️ The generated client widens every optional numeric field to
 * `((number | null) | Array<number | null>)`, because that is how the OpenAPI
 * `anyOf` round-trips — so `stats.sharpe` is *typed* as a value or a list of
 * them and will not compile without unwrapping.
 *
 * 📌 The widening is a TypeScript artefact, not a runtime one, and saying
 * otherwise would misdescribe the defence: the emitted **zod** schema for those
 * same fields is `z.union([z.number(), z.null()]).optional()`, which rejects a
 * list outright — so `riskOutput` discards the whole payload before a list could
 * reach here. `correlationHelpers.ts:28` records the same disagreement between
 * the two halves of the generated client. What `singleValue` actually earns is
 * the right to read the field without a cast, and a cast is how a future shape
 * change would arrive unannounced.
 */
function num(value: number | null | undefined | readonly (number | null)[]): number | null {
    const single = singleValue(value);
    return typeof single === 'number' && Number.isFinite(single) ? single : null;
}

/**
 * The display name of an asset, degrading to `#id` rather than to a blank.
 *
 * A blank row label is indistinguishable from a rendering fault; `#7` at least
 * says "this is asset 7 and nobody could name it", which the reader can act on.
 */
function label(assetId: number, names: ReadonlyMap<number, string>): string {
    return names.get(assetId) ?? `#${assetId}`;
}

/**
 * Build the L1° table.
 *
 * `dailyVar` and `monthlyVar` are two instances of the *same* analytic code at
 * two horizons, which is why they arrive as separate results rather than being
 * picked out of one list here: the caller resolves them by instance id, and a
 * function that took "the VaR result" could not tell the two apart.
 *
 * ⚠️ The two VaR figures arrive as **positive magnitudes** (`ge=0` on the
 * payload) while the drawdown figures arrive **negative** (`le=0`). That is the
 * backend's convention and it is not normalised here: normalising would hide
 * which contract a number came from, and the renderer has to know anyway,
 * because a loss and a fall are drawn with the same sign on screen but reach it
 * from opposite directions.
 */
export function buildAssetSetHurtRows(assetIds: readonly number[], names: ReadonlyMap<number, string>, dailyVar: RiskAnalyticResult | null, monthlyVar: RiskAnalyticResult | null, drawdown: RiskAnalyticResult | null): AssetSetHurtRow[] {
    const daily = byAsset(riskOutput(dailyVar, schemas.RiskAssetSetVarCvarOutput)?.items);
    const monthly = byAsset(riskOutput(monthlyVar, schemas.RiskAssetSetVarCvarOutput)?.items);
    const falls = byAsset(riskOutput(drawdown, schemas.RiskAssetSetDrawdownOutput)?.items);

    return assetIds.map((assetId) => {
        const fall = falls.get(assetId);
        return {
            assetId,
            name: label(assetId, names),
            badDay: num(daily.get(assetId)?.conditional_value_at_risk),
            badMonth: num(monthly.get(assetId)?.conditional_value_at_risk),
            worstFall: num(fall?.maximum_drawdown),
            worstFallDays: num(fall?.maximum_drawdown_duration_days),
            recovery: fall?.maximum_drawdown_recovery_status ?? null,
            currentFall: num(fall?.current_drawdown),
            toPeak: num(fall?.remaining_to_peak_ratio),
        };
    });
}

/**
 * Build the L3° table.
 *
 * Beta and correlation are present only when a benchmark applies, and their
 * absence is expressed as `null` on every row rather than by omitting the
 * columns here — which column set to draw is the renderer's decision, and it
 * has the benchmark to decide with.
 */
export function buildAssetSetPaidRows(assetIds: readonly number[], names: ReadonlyMap<number, string>, riskReturn: RiskAnalyticResult | null, kpi: RiskAnalyticResult | null, comparison: RiskAnalyticResult | null): AssetSetPaidRow[] {
    const points = byAsset(riskOutput(riskReturn, schemas.RiskAssetSetReturnOutput)?.items);
    const kpis = byAsset(riskOutput(kpi, schemas.RiskAssetSetKpiOutput)?.items);
    const versus = byAsset(riskOutput(comparison, schemas.RiskAssetSetComparisonOutput)?.items);

    return assetIds.map((assetId) => {
        const point = points.get(assetId);
        const stats = kpis.get(assetId);
        const against = versus.get(assetId);
        return {
            assetId,
            name: label(assetId, names),
            // Volatility is published by both analytics over the same joint
            // calendar, so either would do. The scatter's own figure is preferred
            // so the table cannot disagree with the dot beside it.
            volatility: num(point?.volatility) ?? num(stats?.volatility),
            expectedReturn: num(point?.expected_annual_return),
            sharpe: num(stats?.sharpe),
            sortino: num(stats?.sortino),
            beta: num(against?.beta),
            correlation: num(against?.correlation),
        };
    });
}

/**
 * The scatter's dots, one per asset that has both coordinates.
 *
 * 🔴 There is no portfolio dot and there cannot be one: `RiskAssetSetReturnOutput`
 * has no field for an aggregate. That absence is what keeps the Capital Market
 * Line off this chart — `capitalMarketLine()` draws only when a point whose role
 * is `portfolio` exists — and therefore what keeps the judgement "paid well for
 * the risk" off a surface whose design forbids it. The defence is a missing
 * shape, not a flag, so nothing here can switch it back on by mistake.
 */
export function buildAssetSetScatterPoints(rowsIn: readonly AssetSetPaidRow[]): {id: string; name: string; volatility: number; annualReturn: number; role: 'asset'}[] {
    const points: {id: string; name: string; volatility: number; annualReturn: number; role: 'asset'}[] = [];
    for (const row of rowsIn) {
        if (row.volatility === null || row.expectedReturn === null) continue;
        points.push({id: `asset-${row.assetId}`, name: row.name, volatility: row.volatility, annualReturn: row.expectedReturn, role: 'asset'});
    }
    return points;
}

/**
 * The benchmark's own coordinates, read from the comparison answer.
 *
 * Read from `asset_set_comparison` and never from a KPI measured on the
 * benchmark asset alone: the reference is prepared inside the same request as
 * the selection, so its volatility is measured over the same joint calendar as
 * every dot beside it. A figure prepared on the asset's own history would carry
 * a different observation count under the same reported window, and the dot
 * would land where no measurement puts it — on a chart that still looks right.
 */
export function buildAssetSetBenchmarkPoint(comparison: RiskAnalyticResult | null, names: ReadonlyMap<number, string>): AssetSetBenchmarkPoint | null {
    const output = riskOutput(comparison, schemas.RiskAssetSetComparisonOutput);
    if (!output) return null;
    const volatility = num(output.comparison_volatility);
    const expectedReturn = num(output.comparison_expected_annual_return);
    // Both coordinates or no dot: a benchmark plotted on one axis would sit at a
    // position half of which nobody measured.
    if (volatility === null || expectedReturn === null) return null;
    return {assetId: output.comparison_asset_id, name: label(output.comparison_asset_id, names), volatility, expectedReturn};
}
