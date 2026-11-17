/**
 * The Asset Detail's risk tab (RN-17): the two rules it applies before mounting the levels on the asset.
 *
 * The browser computes no value here: the position's value is the backend portfolio report's, and the rule for «prices
 * from the plan» reads fields the page already holds.
 */
import {zodiosApi} from '$lib/api';
import {safeScalar} from '$lib/types/common';

/** The asset types whose prices are not observed on a market (Q20): kept by hand or built from a plan. */
const PLAN_PRICED_TYPES: ReadonlySet<string> = new Set(['HOLD', 'CROWDFUND', 'CROWDFUND_REAL_ESTATE']);

/**
 * Whether the asset's prices come from its plan rather than a market (Q20 a): a parametric provider (a scheduled
 * investment generates its series from its schedule), or a type nobody quotes. Its volatility and VaR then only say
 * the plan is regular, and the tab says so.
 */
export function pricesFromPlan(assetType: string | null | undefined, parametricProvider: boolean): boolean {
    return parametricProvider || PLAN_PRICED_TYPES.has((assetType ?? '').toUpperCase());
}

/** A row of the report's holdings, as far as this tab reads it. */
interface HoldingRow {
    asset_id: number;
    current_value?: string | number | null;
}

/**
 * The value the tab's amounts are on (Q17 A1): the asset's own row of the report grouped by asset — the backend's sum
 * over your brokers, at your share, in the page's currency. `null` when the asset is not held, not valued or worth
 * nothing: then no amount is shown in any level.
 */
export function positionValueFromHoldings(holdings: readonly HoldingRow[] | null | undefined, assetId: number): number | null {
    const row = (holdings ?? []).find((holding) => holding.asset_id === assetId);
    const value = row?.current_value == null ? Number.NaN : Number(row.current_value);
    return Number.isFinite(value) && value > 0 ? value : null;
}

/**
 * Read the position's value once: the portfolio report, summary only, grouped by asset, in the page's currency, with no
 * period — so the summary is today's, «your position today» (Q17), never the end of a past period the page shows. All
 * your brokers at your share, as the Dashboard's net worth. A failed read gives `null` — no amounts — never a guess.
 */
export async function loadAssetPositionValue(assetId: number, currency: string): Promise<number | null> {
    const report = await zodiosApi.get_portfolio_report_api_v1_portfolio_report_post({
        include_summary: true,
        include_history: false,
        include_allocation_history: false,
        group_by: 'asset',
        target_currency: currency,
    });
    // The generated client types a scalar field as «a value or a list of values»: read through `safeScalar`.
    return positionValueFromHoldings(safeScalar(report.summary)?.holdings as readonly HoldingRow[] | undefined, assetId);
}
