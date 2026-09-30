/**
 * riskAnalysisHelpers — pure unit tests (node env, no jsdom).
 *
 * These are the decisions RiskAnalysisPanel makes *before* it touches ECharts or
 * a store: normalising the shapes the risk API returns (scalars widened to
 * arrays, per-language text, bucket→shock maps), choosing which stress buckets
 * and base analytics to request, and formatting leaf values. The panel itself
 * mounts a canvas and subscribes to stores, so none of this is reachable in
 * jsdom — which is exactly why the branch-dense fallback chains live here.
 *
 * formatCurrencyAmount is asserted with an explicit locale ('en-US') so the
 * expected string is deterministic regardless of the host process locale.
 *
 * It is also the one function here that reads a store — the global privacy flag
 * — so this file resets that flag around every test. The reset is not optional:
 * the store is module level and shared with every other suite in the run, and a
 * leftover `true` would turn each `'$1,234.50'` below into a placeholder.
 */
import {readFileSync} from 'node:fs';
import {afterEach, beforeEach, describe, expect, it} from 'vitest';

import type {RiskDataQualityReport} from '$lib/risk/riskTypes';
import type {RiskAnalyticResult} from '$lib/stores/risk/riskStore.svelte';
import {setPrivacyEnabled} from '$lib/stores/app/privacyStore.svelte';
import {
    addDays,
    ASSET_SET_DAILY_VAR_INSTANCE,
    ASSET_SET_MONTHLY_VAR_INSTANCE,
    buildBaseAnalytics,
    DAILY_VAR_INSTANCE,
    formatCurrencyAmount,
    formatRatio,
    formatScopedCurrencyAmount,
    localizedScenarioText,
    MONTHLY_VAR_HORIZON_DAYS,
    MONTHLY_VAR_INSTANCE,
    normalizeQualityIssue,
    numberRecord,
    presentStressBuckets,
    resultByCode,
    scalarString,
    stressImpactDimension,
    type BaseAnalyticsContext,
} from './riskAnalysisHelpers';

type Issue = NonNullable<RiskDataQualityReport['issues']>[number];

const riskAnalysisPanelSource = readFileSync(new URL('./RiskAnalysisPanel.svelte', import.meta.url), 'utf8');
const assetRiskScenariosViewSource = readFileSync(new URL('./AssetRiskScenariosView.svelte', import.meta.url), 'utf8');

beforeEach(() => setPrivacyEnabled(false));
afterEach(() => setPrivacyEnabled(false));

/** A result whose only field the code under test reads is `analytic_code`. */
function result(code: string): RiskAnalyticResult {
    return {analytic_code: code} as unknown as RiskAnalyticResult;
}

describe('localizedScenarioText', () => {
    it('prefers the requested language when present', () => {
        expect(localizedScenarioText({en: 'crash', it: 'crollo', fr: 'krach'}, 'fr')).toBe('krach');
    });

    it('falls back to English when the requested language is absent', () => {
        expect(localizedScenarioText({en: 'crash', it: 'crollo'}, 'es')).toBe('crash');
    });

    it('falls back to Italian when neither requested nor English is present', () => {
        expect(localizedScenarioText({it: 'crollo', de: 'absturz'}, 'es')).toBe('crollo');
    });

    it('falls back to any string value when requested/en/it are all absent', () => {
        expect(localizedScenarioText({de: 'absturz'}, 'es')).toBe('absturz');
    });

    it('returns empty string when the object has no string values', () => {
        expect(localizedScenarioText({en: 42, it: null}, 'en')).toBe('');
    });

    it('returns empty string for a null value', () => {
        expect(localizedScenarioText(null, 'en')).toBe('');
    });

    it('returns empty string for an array (not a translation map)', () => {
        expect(localizedScenarioText(['crash'], 'en')).toBe('');
    });

    it('returns empty string for a scalar value', () => {
        expect(localizedScenarioText('crash', 'en')).toBe('');
    });

    it('treats a non-string requested value as absent and keeps searching', () => {
        // requested (fr) is a number → skip to en
        expect(localizedScenarioText({fr: 7, en: 'crash'}, 'fr')).toBe('crash');
    });
});

describe('scalarString', () => {
    it('returns a plain string unchanged', () => {
        expect(scalarString('sector')).toBe('sector');
    });

    it('returns the first string in an array', () => {
        expect(scalarString([null, 'sector', 'geography'])).toBe('sector');
    });

    it('returns null for an array with no string', () => {
        expect(scalarString([null, 3, false])).toBeNull();
    });

    it('returns null for a non-string, non-array value', () => {
        expect(scalarString(42)).toBeNull();
    });

    it('returns null for null/undefined', () => {
        expect(scalarString(null)).toBeNull();
        expect(scalarString(undefined)).toBeNull();
    });
});

describe('numberRecord', () => {
    it('keeps only numeric entries', () => {
        expect(numberRecord({a: 1, b: 'x', c: 2, d: null})).toEqual({a: 1, c: 2});
    });

    it('returns an empty object when nothing is numeric', () => {
        expect(numberRecord({a: 'x', b: null})).toEqual({});
    });

    it('returns an empty object for a non-object', () => {
        expect(numberRecord(42)).toEqual({});
        expect(numberRecord(null)).toEqual({});
        expect(numberRecord('x')).toEqual({});
    });

    it('returns an empty object for an array', () => {
        // an array is typeof "object" but must not be treated as a record
        expect(numberRecord([1, 2, 3])).toEqual({});
    });
});

describe('presentStressBuckets', () => {
    it('asset_class: upper-cases the single class', () => {
        expect(presentStressBuckets('asset_class', {assetClass: 'equity'})).toEqual(['EQUITY']);
    });

    it('asset_class: trims before upper-casing', () => {
        expect(presentStressBuckets('asset_class', {assetClass: '  bond '})).toEqual(['BOND']);
    });

    it('asset_class: OTHER when the class is blank', () => {
        expect(presentStressBuckets('asset_class', {assetClass: '   '})).toEqual(['OTHER']);
    });

    it('asset_class: OTHER when the class is null/undefined', () => {
        expect(presentStressBuckets('asset_class', {assetClass: null})).toEqual(['OTHER']);
        expect(presentStressBuckets('asset_class', {})).toEqual(['OTHER']);
    });

    it('sector: keeps buckets with a finite positive weight', () => {
        const buckets = presentStressBuckets('sector', {sectorExposure: {Tech: 0.4, Energy: 0.6}});
        expect(buckets).toEqual(['Tech', 'Energy']);
    });

    it('sector: drops zero, negative and non-finite weights', () => {
        const buckets = presentStressBuckets('sector', {
            sectorExposure: {Tech: 0.5, Zero: 0, Neg: -0.1, Nan: Number.NaN, Inf: Number.POSITIVE_INFINITY},
        });
        expect(buckets).toEqual(['Tech']);
    });

    it('sector: trims bucket names and drops the ones that trim to empty', () => {
        const buckets = presentStressBuckets('sector', {sectorExposure: {'  Tech ': 0.5, '   ': 0.5}});
        expect(buckets).toEqual(['Tech']);
    });

    it('sector: sentinel [Other] when nothing has positive weight', () => {
        expect(presentStressBuckets('sector', {sectorExposure: {Tech: 0}})).toEqual(['Other']);
    });

    it('sector: sentinel [Other] when the exposure map is null/absent', () => {
        expect(presentStressBuckets('sector', {sectorExposure: null})).toEqual(['Other']);
        expect(presentStressBuckets('sector', {})).toEqual(['Other']);
    });

    it('geography: reads the geography exposure, not the sector one', () => {
        const buckets = presentStressBuckets('geography', {
            sectorExposure: {Tech: 0.9},
            geographyExposure: {US: 0.7, EU: 0.3},
        });
        expect(buckets).toEqual(['US', 'EU']);
    });
});

describe('stressImpactDimension', () => {
    it('trusts a valid echoed dimension', () => {
        expect(stressImpactDimension('sector', 'asset_class')).toBe('sector');
        expect(stressImpactDimension('geography', 'asset_class')).toBe('geography');
        expect(stressImpactDimension('asset_class', 'sector')).toBe('asset_class');
    });

    it('narrows an array echo to its first element', () => {
        expect(stressImpactDimension(['geography', 'sector'], 'asset_class')).toBe('geography');
    });

    it('falls back for an unknown string', () => {
        expect(stressImpactDimension('currency', 'sector')).toBe('sector');
    });

    it('falls back for null/undefined/non-string', () => {
        expect(stressImpactDimension(null, 'geography')).toBe('geography');
        expect(stressImpactDimension(undefined, 'asset_class')).toBe('asset_class');
        expect(stressImpactDimension(42, 'sector')).toBe('sector');
    });
});

describe('resultByCode', () => {
    it('returns the result whose analytic_code matches', () => {
        const results = [result('correlation'), result('historical_var')];
        expect(resultByCode(results, 'historical_var')).toBe(results[1]);
    });

    it('returns null when no result matches', () => {
        expect(resultByCode([result('correlation')], 'historical_var')).toBeNull();
    });

    it('returns null for an empty batch', () => {
        expect(resultByCode([], 'correlation')).toBeNull();
    });
});

describe('normalizeQualityIssue', () => {
    it('passes list fields through and keeps scalar fields', () => {
        const issue: Issue = {
            domain: 'asset',
            code: 'MISSING_PRICE',
            severity: 'warning',
            message_i18n_key: 'risk.dq.missing_prices',
            message_params: {count: 3},
            count: 3,
            affected_asset_ids: [1, 2],
            affected_asset_names: ['A', 'B'],
            affected_fx_pairs: ['EURUSD'],
            cta_action: 'open',
            cta_target: 'asset:1',
            group_key: 'g1',
        };
        expect(normalizeQualityIssue(issue)).toEqual({
            domain: 'asset',
            code: 'MISSING_PRICE',
            severity: 'warning',
            message_i18n_key: 'risk.dq.missing_prices',
            message_params: {count: 3},
            count: 3,
            affected_asset_ids: [1, 2],
            affected_asset_names: ['A', 'B'],
            affected_fx_pairs: ['EURUSD'],
            cta_action: 'open',
            cta_target: 'asset:1',
            group_key: 'g1',
        });
    });

    it('narrows scalar fields that arrived widened to arrays', () => {
        // The API may widen scalars to arrays; normalizeQualityIssue narrows them.
        const issue = {
            domain: 'asset',
            code: 'MISSING_PRICE',
            severity: 'warning',
            message_i18n_key: 'risk.dq.missing_prices',
            count: [3, 4],
            cta_action: ['open', 'ignore'],
            cta_target: ['asset:1'],
            group_key: ['g1', 'g2'],
        } as unknown as Issue;
        const normalized = normalizeQualityIssue(issue);
        expect(normalized.count).toBe(3);
        expect(normalized.cta_action).toBe('open');
        expect(normalized.cta_target).toBe('asset:1');
        expect(normalized.group_key).toBe('g1');
    });

    it('maps absent optional scalars to null', () => {
        const issue: Issue = {
            domain: 'asset',
            code: 'MISSING_PRICE',
            severity: 'info',
            message_i18n_key: 'risk.dq.missing_prices',
        };
        const normalized = normalizeQualityIssue(issue);
        expect(normalized.count).toBeNull();
        expect(normalized.cta_action).toBeNull();
        expect(normalized.cta_target).toBeNull();
        expect(normalized.group_key).toBeNull();
    });
});

describe('formatRatio', () => {
    it('em-dash for null/undefined', () => {
        expect(formatRatio(null)).toBe('—');
        expect(formatRatio(undefined)).toBe('—');
    });

    it('two decimals for a number', () => {
        expect(formatRatio(1.2)).toBe('1.20');
        expect(formatRatio(-0.5)).toBe('-0.50');
    });

    it('formats zero (not treated as absent)', () => {
        expect(formatRatio(0)).toBe('0.00');
    });
});

describe('formatCurrencyAmount', () => {
    it('formats a finite scalar with the pinned locale', () => {
        expect(formatCurrencyAmount('1234.5', 'USD', 'en-US')).toBe('$1,234.50');
    });

    it('narrows an array to its first string before formatting', () => {
        expect(formatCurrencyAmount(['1234.5', '99'], 'USD', 'en-US')).toBe('$1,234.50');
    });

    it('em-dash when the value is null/undefined', () => {
        expect(formatCurrencyAmount(null, 'USD', 'en-US')).toBe('—');
        expect(formatCurrencyAmount(undefined, 'USD', 'en-US')).toBe('—');
    });

    it('em-dash when the array has no usable scalar', () => {
        expect(formatCurrencyAmount([null], 'USD', 'en-US')).toBe('—');
    });

    it('em-dash when the scalar is not a finite number', () => {
        expect(formatCurrencyAmount('not-a-number', 'USD', 'en-US')).toBe('—');
    });

    it('respects the currency argument', () => {
        expect(formatCurrencyAmount('1000', 'EUR', 'en-US')).toBe('€1,000.00');
    });

    describe('with global privacy on', () => {
        it('masks the digits of a formattable amount and keeps its currency', () => {
            // Control: the same call, one line earlier in time, with the flag
            // off. It is what makes the next assertion a substitution rather
            // than a function that has always returned `$•••`.
            expect(formatCurrencyAmount('1234.5', 'USD', 'en-US')).toBe('$1,234.50');

            setPrivacyEnabled(true);
            expect(formatCurrencyAmount('1234.5', 'USD', 'en-US')).toBe('$•••');
            expect(formatCurrencyAmount(['1234.5', '99'], 'USD', 'en-US')).toBe('$•••');
        });

        it('still says em-dash for an absent value', () => {
            setPrivacyEnabled(true);

            // Masking an absence would promote "there is no figure here" into
            // "there is a figure here and you may not see it" — a number the
            // portfolio does not have.
            expect(formatCurrencyAmount(null, 'USD', 'en-US')).toBe('—');
            expect(formatCurrencyAmount(undefined, 'USD', 'en-US')).toBe('—');
            expect(formatCurrencyAmount([null], 'USD', 'en-US')).toBe('—');
            expect(formatCurrencyAmount([], 'USD', 'en-US')).toBe('—');

            // Positive control for the flag: in this exact state a *present*
            // value comes back masked. Without it every line above would also
            // hold on a run where privacy never turned on, which is the one way
            // this test could pass while testing nothing.
            expect(formatCurrencyAmount('0', 'USD', 'en-US')).toBe('$•••');
        });

        it('still says em-dash for a value that is not a finite number', () => {
            setPrivacyEnabled(true);

            expect(formatCurrencyAmount('not-a-number', 'USD', 'en-US')).toBe('—');
            expect(formatCurrencyAmount('Infinity', 'USD', 'en-US')).toBe('—');
            // Control: a parseable neighbour of the same shape is masked, so the
            // two em-dashes above are the absence check and not a masked branch
            // that happens to look like one.
            expect(formatCurrencyAmount('12', 'USD', 'en-US')).toBe('$•••');
        });

        it('gives two very different magnitudes the identical placeholder', () => {
            // Control: unmasked they differ, and by length, and the digit check
            // below is able to see a digit when there is one.
            const small = formatCurrencyAmount('1000', 'USD', 'en-US');
            const large = formatCurrencyAmount('9999999', 'USD', 'en-US');
            expect(small).not.toBe(large);
            expect(small.length).not.toBe(large.length);
            expect(large).toMatch(/\d/);

            setPrivacyEnabled(true);
            const maskedSmall = formatCurrencyAmount('1000', 'USD', 'en-US');
            const maskedLarge = formatCurrencyAmount('9999999', 'USD', 'en-US');

            expect(maskedSmall).toBe(maskedLarge);
            expect(maskedSmall).toBe('$•••');
            expect(maskedSmall).not.toMatch(/\d/);
            // Width is the leak that survives an equality check on content in a
            // padded formatter, so it is asserted in its own right.
            expect(maskedSmall.length).toBe(maskedLarge.length);
        });

        it('keeps the sign of a loss, as the shared formatters do (D8)', () => {
            expect(formatCurrencyAmount('-1234.5', 'USD', 'en-US')).toBe('-$1,234.50');

            setPrivacyEnabled(true);
            // The sign stays outside the mask by decision D8 of the product
            // owner, as the shared currency formatters keep it (see
            // `maskable`). This formatter used to hide it, with no recorded
            // reason for departing from D8.
            expect(formatCurrencyAmount('-1234.5', 'USD', 'en-US')).toBe('-$•••');
            expect(formatCurrencyAmount('1234.5', 'USD', 'en-US')).toBe('$•••');
            expect(formatCurrencyAmount('-1234.5', 'USD', 'en-US')).not.toBe(formatCurrencyAmount('1234.5', 'USD', 'en-US'));
        });

        it('keeps the currency marker, like the shared currency formatter', () => {
            // Control: the currency is visible in the clear.
            expect(formatCurrencyAmount('1000', 'USD', 'en-US')).toContain('$');
            expect(formatCurrencyAmount('1000', 'EUR', 'en-US')).toContain('€');
            expect(formatCurrencyAmount('1000', 'USD', 'en-US')).toMatch(/\d/);

            setPrivacyEnabled(true);
            // Product owner, 2026-09-22: privacy hides the number, not the
            // currency. This formatter used to return the bare placeholder, on
            // the argument that the currency labels the column rather than the
            // cell; that argument was overruled, and it now keeps its currency
            // as formatCurrencyAmountPlain keeps `••• $ 🇺🇸 USD`. A marker that
            // is present proves nothing on its own — an unmasked string has it
            // too — so each is paired with the absence of the digits.
            const maskedUsd = formatCurrencyAmount('1000', 'USD', 'en-US');
            const maskedEur = formatCurrencyAmount('1000', 'EUR', 'en-US');
            expect(maskedUsd).not.toBe(maskedEur);
            expect(maskedUsd).toContain('$');
            expect(maskedEur).toContain('€');
            expect(maskedUsd).not.toMatch(/\d/);
            expect(maskedEur).not.toMatch(/\d/);
            expect(maskedEur).toBe('€•••');
        });

        it('comes back unmasked as soon as the flag goes off', () => {
            setPrivacyEnabled(true);
            expect(formatCurrencyAmount('1234.5', 'USD', 'en-US')).toBe('$•••');

            setPrivacyEnabled(false);
            // The formatter reads the flag per call: nothing is memoised, so a
            // toggle is visible on the next render without an invalidation.
            expect(formatCurrencyAmount('1234.5', 'USD', 'en-US')).toBe('$1,234.50');
        });
    });
});

describe('formatScopedCurrencyAmount', () => {
    it('formats normally on a portfolio scope', () => {
        expect(formatScopedCurrencyAmount('1234.5', 'USD', 'portfolio', 'en-US')).toBe('$1,234.50');
    });

    // The mutation-sensitive pair. The backend sends null on these scopes today,
    // so both would read '—' with or without the guard; passing a real amount is
    // the only way to make the assertion capable of failing.
    it('suppresses a real amount on an asset scope', () => {
        expect(formatScopedCurrencyAmount('1234.5', 'USD', 'asset', 'en-US')).toBe('—');
    });

    it('suppresses a real amount on an asset_set scope', () => {
        expect(formatScopedCurrencyAmount('1234.5', 'USD', 'asset_set', 'en-US')).toBe('—');
    });

    // Guards the other direction: a guard that blanked every scope would also
    // pass the two above, and would silently empty the dashboard's amounts on
    // the day the backend starts computing them.
    it('still em-dashes a missing amount on a portfolio scope', () => {
        expect(formatScopedCurrencyAmount(null, 'USD', 'portfolio', 'en-US')).toBe('—');
    });
});

describe('addDays', () => {
    it('shifts a valid ISO date forward', () => {
        expect(addDays('2024-01-01', 5)).toBe('2024-01-06');
    });

    it('shifts backward with negative days', () => {
        expect(addDays('2024-01-06', -5)).toBe('2024-01-01');
    });

    it('crosses a month boundary', () => {
        expect(addDays('2024-01-31', 1)).toBe('2024-02-01');
    });

    it('crosses a year boundary', () => {
        expect(addDays('2023-12-31', 1)).toBe('2024-01-01');
    });

    it('respects the UTC leap day', () => {
        expect(addDays('2024-02-28', 1)).toBe('2024-02-29');
    });

    it('degrades to a stable day-N label for an unparseable base date', () => {
        expect(addDays('not-a-date', 4)).toBe('day-4');
    });
});

describe('buildBaseAnalytics', () => {
    /** A context whose capability predicate allows exactly `allowed`. */
    function ctx(allowed: string[], appliedRiskFreePercent = 2): BaseAnalyticsContext {
        const set = new Set(allowed);
        return {appliedRiskFreePercent, hasCapability: (code) => set.has(code)};
    }

    it('historical: requests KPI, correlation and VaR when all are advertised', () => {
        const analytics = buildBaseAnalytics('historical', ctx(['historical_kpi', 'correlation', 'historical_var']));
        expect(analytics.map((a) => a.analytic_code)).toEqual(['historical_kpi', 'correlation', 'historical_var']);
        expect(analytics.map((a) => a.instance_id)).toEqual(['base-historical-historical_kpi', 'base-historical-correlation', 'base-historical-historical_var']);
    });

    it('historical: omits the drawdown summary unless the call site opts in, even when advertised', () => {
        // The guard that keeps the parked Asset Detail surface off the wire.
        // If this ever defaults to on, Asset Detail starts requesting an analytic
        // nobody added to Asset Detail.
        const advertised = ['historical_kpi', 'correlation', 'historical_var', 'drawdown_summary'];
        expect(buildBaseAnalytics('historical', ctx(advertised)).map((a) => a.analytic_code)).not.toContain('drawdown_summary');
    });

    it('historical: appends the drawdown summary when the call site opts in', () => {
        const advertised = ['historical_kpi', 'correlation', 'historical_var', 'drawdown_summary'];
        const analytics = buildBaseAnalytics('historical', {...ctx(advertised), includeDrawdownSummary: true});
        expect(analytics.map((a) => a.analytic_code)).toEqual(['historical_kpi', 'correlation', 'historical_var', 'drawdown_summary']);
    });

    it('historical: opting in cannot conjure a capability the catalog withholds', () => {
        // `drawdown_summary` does not accept an asset set; an opt-in must not
        // turn that into a request the backend will reject.
        const analytics = buildBaseAnalytics('historical', {...ctx(['historical_kpi']), includeDrawdownSummary: true});
        expect(analytics.map((a) => a.analytic_code)).toEqual(['historical_kpi']);
    });

    it('historical: seeds KPI with the applied risk-free rate as a fraction', () => {
        const analytics = buildBaseAnalytics('historical', ctx(['historical_kpi'], 2));
        expect(analytics[0].parameters).toEqual({risk_free_annual_rate: 0.02, target_annual_return: 0});
    });

    it('historical: VaR carries a 1-day 95% window', () => {
        const analytics = buildBaseAnalytics('historical', ctx(['historical_var']));
        expect(analytics[0].parameters).toEqual({confidence_level: 0.95, horizon_days: 1});
    });

    // The bad month is a calendar month: the backend turns calendar days into the observations the
    // series holds (21 for a weekday series, 30 for one quoted every day — developer's decision of
    // 30/09/2026), so the request says 30, not the 21 trading days it used to assume.
    it('historical: the monthly VaR asks for a calendar month, 30 days, beside the 1-day one', () => {
        const analytics = buildBaseAnalytics('historical', {...ctx(['historical_var']), includeMonthlyVar: true});
        expect(MONTHLY_VAR_HORIZON_DAYS).toBe(30);
        expect(analytics.map((a) => [a.instance_id, a.parameters])).toEqual([
            [DAILY_VAR_INSTANCE, {confidence_level: 0.95, horizon_days: 1}],
            [MONTHLY_VAR_INSTANCE, {confidence_level: 0.95, horizon_days: 30}],
        ]);
    });

    it('asset set: the monthly per-asset VaR asks for the same calendar month', () => {
        const analytics = buildBaseAnalytics('historical', {...ctx(['asset_set_var']), includeAssetSetLevels: true});
        expect(analytics.map((a) => [a.instance_id, a.parameters])).toEqual([
            [ASSET_SET_DAILY_VAR_INSTANCE, {confidence_level: 0.95, horizon_days: 1}],
            [ASSET_SET_MONTHLY_VAR_INSTANCE, {confidence_level: 0.95, horizon_days: 30}],
        ]);
    });

    it('historical: omits any capability the catalog does not advertise', () => {
        const analytics = buildBaseAnalytics('historical', ctx(['correlation']));
        expect(analytics.map((a) => a.analytic_code)).toEqual(['correlation']);
    });

    it('historical: empty when nothing is advertised', () => {
        expect(buildBaseAnalytics('historical', ctx([]))).toEqual([]);
    });

    it('current_composition: requests risk_contribution when advertised', () => {
        const analytics = buildBaseAnalytics('current_composition', ctx(['risk_contribution']));
        expect(analytics.map((a) => a.analytic_code)).toEqual(['risk_contribution']);
        expect(analytics[0].instance_id).toBe('base-current_composition-risk_contribution');
    });

    it('current_composition: never requests the historical analytics', () => {
        // even if the historical capabilities are advertised, this mode ignores them
        const analytics = buildBaseAnalytics('current_composition', ctx(['historical_kpi', 'correlation', 'historical_var']));
        expect(analytics).toEqual([]);
    });

    it('current_composition: empty when risk_contribution is not advertised', () => {
        expect(buildBaseAnalytics('current_composition', ctx([]))).toEqual([]);
    });

    it('passes the mode through to the capability predicate', () => {
        const seen: Array<[string, string]> = [];
        buildBaseAnalytics('historical', {
            appliedRiskFreePercent: 0,
            hasCapability: (code, mode) => {
                seen.push([code, mode]);
                return false;
            },
        });
        expect(seen).toEqual([
            ['historical_kpi', 'historical'],
            ['correlation', 'historical'],
            ['historical_var', 'historical'],
        ]);
    });
});

describe('sync completion source contracts', () => {
    it('forwards PageSyncModal completion detail through RiskAnalysisPanel unchanged', () => {
        const modalTag = riskAnalysisPanelSource.match(/<PageSyncModal\b[\s\S]*?\/>/)?.at(0) ?? '';
        expect(modalTag).not.toBe('');
        expect(modalTag).toMatch(/\bonsynced\s*=\s*\{handleSynced\}/);

        const handlerMatch = riskAnalysisPanelSource.match(/async\s+function\s+handleSynced\(\s*detail\s*:\s*\{\s*accepted\s*:\s*boolean\s*\}\s*\)\s*:\s*Promise<void>\s*\{([\s\S]*?)\n\s{4}\}/);
        expect(handlerMatch).not.toBeNull();
        const handlerBody = handlerMatch?.at(1)?.replace(/\s+/g, ' ').trim() ?? '';
        expect(handlerBody).toMatch(/\bawait\s+onsynced\?\.\(\s*detail\s*\)\s*;/);
        expect(handlerBody).not.toMatch(/\bonsynced\?\.\(\s*\)/);
        expect(handlerBody).not.toMatch(/\bonsynced\?\.\(\s*\{/);
    });

    it('types and forwards AssetRiskScenariosView completion callbacks unchanged', () => {
        expect(assetRiskScenariosViewSource).toMatch(/\bonsynced\?\s*:\s*\(\s*detail\s*:\s*\{\s*accepted\s*:\s*boolean\s*\}\s*\)\s*=>\s*void\s*\|\s*Promise<void>\s*;/);

        const propsBinding = assetRiskScenariosViewSource.match(/let\s*\{([\s\S]*?)\}\s*:\s*Props\s*=\s*\$props\(\)\s*;/)?.at(1) ?? '';
        expect(propsBinding).toMatch(/(?:^|,)\s*onsynced\s*(?:,|$)/);

        const riskPanelTag = assetRiskScenariosViewSource.match(/<RiskAnalysisPanel\b[\s\S]*?\/>/)?.at(0) ?? '';
        expect(riskPanelTag).not.toBe('');
        expect(riskPanelTag).toContain('{onsynced}');
        expect(riskPanelTag).not.toMatch(/\bonsynced\s*=/);
    });
});
