/**
 * The Asset Detail's risk tab: two rules the tab applies before it mounts the levels (RN-17).
 *
 *  - **The money (Q17 A1)**: when you own the asset, the amounts are on your position today — the value the backend's
 *    portfolio report gives for that asset, summed over your brokers (`group_by: "asset"`, `current_value`, your share,
 *    the page's currency). Not owned, unvalued or worth nothing: no amount anywhere. The browser computes no value.
 *  - **Prices from the plan (Q20 a)**: a scheduled investment (a parametric provider), a HOLD or a crowdfunding asset has
 *    prices built from its plan, not observed on a market: its volatility and VaR only say the plan is regular, so the
 *    tab says so.
 */
import {describe, expect, it} from 'vitest';

import {positionValueFromHoldings, pricesFromPlan} from './assetRiskTabRules';

const holding = (assetId: number, currentValue: string | null) => ({asset_id: assetId, current_value: currentValue});

describe('positionValueFromHoldings — the value the money is on (Q17 A1)', () => {
    it('reads the asset’s own row, summed over the brokers by the backend', () => {
        expect(positionValueFromHoldings([holding(3, '500.00'), holding(7, '12400.50')], 7)).toBe(12400.5);
    });

    it('gives null when the asset is not held, has no value, or is worth nothing: then no amount is shown', () => {
        expect(positionValueFromHoldings([holding(3, '500.00')], 7)).toBeNull();
        expect(positionValueFromHoldings([holding(7, null)], 7)).toBeNull();
        expect(positionValueFromHoldings([holding(7, '0')], 7)).toBeNull();
        expect(positionValueFromHoldings([holding(7, '-3')], 7)).toBeNull();
        expect(positionValueFromHoldings(undefined, 7)).toBeNull();
    });
});

describe('pricesFromPlan — prices built from a plan, not observed (Q20)', () => {
    it('is true for a parametric provider (a scheduled investment), a HOLD and a crowdfunding asset', () => {
        expect(pricesFromPlan('BOND', true)).toBe(true);
        expect(pricesFromPlan('HOLD', false)).toBe(true);
        expect(pricesFromPlan('CROWDFUND', false)).toBe(true);
        expect(pricesFromPlan('CROWDFUND_REAL_ESTATE', false)).toBe(true);
    });

    it('is false for an asset priced on a market', () => {
        for (const type of ['STOCK', 'ETF', 'ETF_STOCK', 'BOND', 'CRYPTO', 'FUND']) expect(pricesFromPlan(type, false), type).toBe(false);
        expect(pricesFromPlan(null, false)).toBe(false);
    });
});
