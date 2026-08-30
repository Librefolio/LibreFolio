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
 */
import {describe, expect, it} from 'vitest';

import type {RiskDataQualityReport} from '$lib/risk/riskTypes';
import type {RiskAnalyticResult} from '$lib/stores/risk/riskStore.svelte';
import {addDays, buildBaseAnalytics, formatCurrencyAmount, formatRatio, localizedScenarioText, normalizeQualityIssue, numberRecord, presentStressBuckets, resultByCode, scalarString, stressImpactDimension, type BaseAnalyticsContext} from './riskAnalysisHelpers';

type Issue = NonNullable<RiskDataQualityReport['issues']>[number];

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

    it('historical: seeds KPI with the applied risk-free rate as a fraction', () => {
        const analytics = buildBaseAnalytics('historical', ctx(['historical_kpi'], 2));
        expect(analytics[0].parameters).toEqual({risk_free_annual_rate: 0.02, target_annual_return: 0});
    });

    it('historical: VaR carries a 1-day 95% window', () => {
        const analytics = buildBaseAnalytics('historical', ctx(['historical_var']));
        expect(analytics[0].parameters).toEqual({confidence_level: 0.95, horizon_days: 1});
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
