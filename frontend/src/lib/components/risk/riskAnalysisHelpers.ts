/**
 * riskAnalysisHelpers — the pure decision logic behind RiskAnalysisPanel.
 *
 * RiskAnalysisPanel mounts ECharts and subscribes to reference stores, so it can
 * only be exercised end-to-end. Everything here is the part that runs *before*
 * any of that: it normalises the shapes the risk API returns (scalars that may
 * arrive as arrays, per-language text, bucket→shock maps), decides which stress
 * buckets and base analytics to request, and formats the leaf values. None of it
 * touches a store, a canvas, or the DOM, so every branch is unit-testable here —
 * which is exactly where an off-by-one in a fallback chain would otherwise hide.
 *
 * Anything that needs a translation ($t) or an emoji/flag lookup stays in the
 * component: those are presentation, and asserting on translated output is
 * forbidden. What is extracted is the logic that decides *which* value to show,
 * never the localized string itself.
 */
import {buildRiskAnalyticRequest, type RiskAnalyticParameters, type RiskAnalyticRequest, type RiskMode, type RiskScenarioDimension} from '$lib/risk/riskRequest';
import {singleValue, type RiskDataQualityReport} from '$lib/risk/riskTypes';
import type {RiskAnalyticResult} from '$lib/stores/risk/riskStore.svelte';
import type {DataQualityIssue} from '$lib/components/ui/feedback/DataQualityBanner.svelte';

/**
 * The scenario description in the user's current language. A scenario carries a
 * `{lang: text}` map; we prefer the requested language, then English, then
 * Italian, then any string present, and finally the empty string when the value
 * is not a usable translation object at all (null, array, or a scalar).
 */
export function localizedScenarioText(value: unknown, language: string): string {
    if (value === null || typeof value !== 'object' || Array.isArray(value)) return '';
    const translations = value as Record<string, unknown>;
    const requested = translations[language];
    if (typeof requested === 'string') return requested;
    if (typeof translations.en === 'string') return translations.en;
    if (typeof translations.it === 'string') return translations.it;
    return Object.values(translations).find((candidate): candidate is string => typeof candidate === 'string') ?? '';
}

/**
 * Reduce a field that may arrive as a string, or as an array of them, to a
 * single string — the first string in an array, or null when there is none.
 * The risk API sometimes widens scalars to arrays; this narrows them back.
 */
export function scalarString(value: unknown): string | null {
    if (typeof value === 'string') return value;
    if (Array.isArray(value)) return value.find((candidate): candidate is string => typeof candidate === 'string') ?? null;
    return null;
}

/**
 * Keep only the numeric entries of a `{bucket: shock}` object, dropping anything
 * non-numeric (and yielding `{}` for a value that is not a plain object). Used
 * to sanitise a scenario preset's bucket shocks before they seed the editor.
 */
export function numberRecord(value: unknown): Record<string, number> {
    if (value === null || typeof value !== 'object' || Array.isArray(value)) return {};
    return Object.fromEntries(Object.entries(value).filter((entry): entry is [string, number] => typeof entry[1] === 'number'));
}

/** The exposure context `presentStressBuckets` reads to decide its buckets. */
export interface StressBucketContext {
    assetClass?: string | null;
    sectorExposure?: Record<string, number> | null;
    geographyExposure?: Record<string, number> | null;
}

/**
 * Which buckets to show shock editors for, given the stress dimension:
 * - `asset_class` → the single asset class (upper-cased, or `OTHER` when blank);
 * - `sector`/`geography` → every exposure bucket with a finite positive weight,
 *   or the sentinel `['Other']` when the portfolio has no usable exposure there.
 */
export function presentStressBuckets(dimension: RiskScenarioDimension, ctx: StressBucketContext): string[] {
    if (dimension === 'asset_class') return [(ctx.assetClass?.trim().toUpperCase() || 'OTHER') as string];
    const exposure = dimension === 'sector' ? ctx.sectorExposure : ctx.geographyExposure;
    const buckets = Object.entries(exposure ?? {})
        .filter(([, weight]) => Number.isFinite(weight) && weight > 0)
        .map(([bucket]) => bucket.trim())
        .filter(Boolean);
    return buckets.length > 0 ? buckets : ['Other'];
}

/**
 * The dimension the backend actually stressed, echoed in the impact row. A valid
 * echoed dimension is trusted; anything else falls back to the dimension the UI
 * currently has selected, so a malformed echo never blanks the row's labels.
 */
export function stressImpactDimension(value: unknown, fallback: RiskScenarioDimension): RiskScenarioDimension {
    const dimension = singleValue(value);
    return dimension === 'asset_class' || dimension === 'sector' || dimension === 'geography' ? dimension : fallback;
}

/** Find the analytic result for a code, or null when the batch did not run it. */
export function resultByCode(results: RiskAnalyticResult[], analyticCode: string): RiskAnalyticResult | null {
    return results.find((result) => result.analytic_code === analyticCode) ?? null;
}

/**
 * Flatten a raw data-quality issue into the typed shape the banner consumes:
 * every scalar field the API may widen to an array (`count`, the CTA fields,
 * `group_key`) is narrowed back with `singleValue`; the list fields pass through.
 */
export function normalizeQualityIssue(issue: NonNullable<RiskDataQualityReport['issues']>[number]): DataQualityIssue {
    return {
        domain: issue.domain,
        code: issue.code,
        severity: issue.severity,
        message_i18n_key: issue.message_i18n_key,
        message_params: issue.message_params as Record<string, string | number | boolean | null | undefined> | undefined,
        count: singleValue(issue.count),
        affected_asset_ids: issue.affected_asset_ids,
        affected_asset_names: issue.affected_asset_names,
        affected_fx_pairs: issue.affected_fx_pairs,
        cta_action: singleValue(issue.cta_action),
        cta_target: singleValue(issue.cta_target),
        group_key: singleValue(issue.group_key),
    };
}

/** A ratio metric to two decimals, or an em-dash when the value is absent. */
export function formatRatio(value: number | null | undefined): string {
    return value == null ? '—' : value.toFixed(2);
}

/**
 * A currency amount, or an em-dash when the value is absent or not finite. The
 * value may arrive as a string or an array of them (`singleValue` narrows it).
 * `locale` is optional so callers get the process default in the app but tests
 * can pin it — `Intl.NumberFormat` output otherwise depends on the host locale.
 */
export function formatCurrencyAmount(value: string | readonly (string | null)[] | null | undefined, currency: string, locale?: string): string {
    const scalar = singleValue(value);
    if (scalar == null) return '—';
    const amount = Number(scalar);
    if (!Number.isFinite(amount)) return '—';
    return new Intl.NumberFormat(locale, {style: 'currency', currency, maximumFractionDigits: 2}).format(amount);
}

/**
 * Shift an ISO `YYYY-MM-DD` date by `days` (UTC-anchored so it never drifts
 * across a timezone boundary), used to label the simulation horizon axis. An
 * unparseable base date degrades to a stable `day-N` label rather than throwing.
 */
export function addDays(baseDate: string, days: number): string {
    const parsed = new Date(`${baseDate}T00:00:00Z`);
    if (Number.isNaN(parsed.getTime())) return `day-${days}`;
    parsed.setUTCDate(parsed.getUTCDate() + days);
    return parsed.toISOString().slice(0, 10);
}

/** The state `buildBaseAnalytics` needs, decoupled from the store and catalog. */
export interface BaseAnalyticsContext {
    appliedRiskFreePercent: number;
    /** True when the backend advertises `code` for the current scope in `mode`. */
    hasCapability: (code: string, mode: RiskMode) => boolean;
}

/**
 * The base analytics the panel requests for a mode, keeping only those the
 * backend advertises for the current scope:
 * - `historical` → KPI (seeded with the applied risk-free rate), correlation,
 *   and 1-day 95% historical VaR;
 * - `current_composition` → risk contribution.
 * A capability the catalog does not list is silently omitted, so the request
 * never asks for something the backend cannot compute.
 */
export function buildBaseAnalytics(mode: RiskMode, ctx: BaseAnalyticsContext): RiskAnalyticRequest[] {
    const analytics: RiskAnalyticRequest[] = [];
    const add = (code: string, parameters: RiskAnalyticParameters = {}) => {
        if (ctx.hasCapability(code, mode)) {
            analytics.push(buildRiskAnalyticRequest(`base-${mode}-${code}`, code, parameters));
        }
    };
    if (mode === 'historical') {
        add('historical_kpi', {
            risk_free_annual_rate: ctx.appliedRiskFreePercent / 100,
            target_annual_return: 0,
        });
        add('correlation');
        add('historical_var', {confidence_level: 0.95, horizon_days: 1});
    } else {
        add('risk_contribution');
    }
    return analytics;
}
