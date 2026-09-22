/**
 * riskAnalysisHelpers — the pure decision logic behind RiskAnalysisPanel.
 *
 * RiskAnalysisPanel mounts ECharts and subscribes to reference stores, so it can
 * only be exercised end-to-end. Everything here is the part that runs *before*
 * any of that: it normalises the shapes the risk API returns (scalars that may
 * arrive as arrays, per-language text, bucket→shock maps), decides which stress
 * buckets and base analytics to request, and formats the leaf values.
 *
 * One deliberate exception to the "no store" rule: `formatCurrencyAmount` reads
 * the global privacy flag. It is the only currency formatter in the codebase
 * living outside `utils/currency/currencyFormat.ts`, so masking it at its caller
 * instead would place the decision at the *site* rather than in the channel —
 * and the whole point of deciding in a formatter is that it is decided once.
 * Every branch here stays unit-testable: the flag defaults to off, and the
 * masked branch is reached by turning it on.
 *
 * Nothing else touches a store, a canvas, or the DOM — which is exactly where an
 * off-by-one in a fallback chain would otherwise hide.
 *
 * Anything that needs a translation ($t) or an emoji/flag lookup stays in the
 * component: those are presentation, and asserting on translated output is
 * forbidden. What is extracted is the logic that decides *which* value to show,
 * never the localized string itself.
 */
import {buildRiskAnalyticRequest, type RiskAnalyticParameters, type RiskAnalyticRequest, type RiskMode, type RiskScenarioDimension} from '$lib/risk/riskRequest';
import {singleValue, type RiskDataQualityReport} from '$lib/risk/riskTypes';
import {PRIVACY_PLACEHOLDER, shouldMaskAmount} from '$lib/utils/privacy/maskable';
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
 * Find a result by its instance id.
 *
 * Needed as soon as one batch runs the *same* analytic twice with different
 * parameters — the daily and monthly VaR — where `resultByCode` would keep
 * returning whichever came first and quietly label a monthly loss as daily.
 */
export function resultByInstance(results: RiskAnalyticResult[], instanceId: string): RiskAnalyticResult | null {
    return results.find((result) => result.instance_id === instanceId) ?? null;
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
 *
 * The privacy check sits *after* the absence checks on purpose: an absent value
 * keeps its em-dash. Masking it would turn "there is no figure here" into "there
 * is a figure here and you may not see it", which is a different statement.
 */
export function formatCurrencyAmount(value: string | readonly (string | null)[] | null | undefined, currency: string, locale?: string): string {
    const scalar = singleValue(value);
    if (scalar == null) return '—';
    const amount = Number(scalar);
    if (!Number.isFinite(amount)) return '—';
    if (shouldMaskAmount()) return PRIVACY_PLACEHOLDER;
    return new Intl.NumberFormat(locale, {style: 'currency', currency, maximumFractionDigits: 2}).format(amount);
}

/**
 * A currency amount is only meaningful on a `portfolio` scope, where every
 * holding is a real position held in a real proportion. On an `asset` or
 * `asset_set` scope the weights are implicit — the reader never chose them — so
 * an impact in euros would be true arithmetic over a portfolio that does not
 * exist. An invented euro reads exactly like a measured one (D107).
 *
 * Today the backend sends `null` for those scopes, so this returns the same `—`
 * it would have returned anyway and no pixel moves. That is what makes the guard
 * safe to add, and also why it is easy to delete during a cleanup: it never
 * appears to fire. It exists for the day the backend starts sending a number,
 * which is the day nothing else would stop it from being printed.
 */
export function formatScopedCurrencyAmount(value: string | readonly (string | null)[] | null | undefined, currency: string, scopeKind: string, locale?: string): string {
    if (scopeKind !== 'portfolio') return '—';
    return formatCurrencyAmount(value, currency, locale);
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
    /**
     * Opt-in, per call site, never a default.
     *
     * Only the four-level composition asks for the drawdown summary, because it
     * is the only surface that renders it. Turning it on here for everyone would
     * silently change what Asset Detail puts on the wire — a parked surface —
     * from a shared helper three files away. The asset-detail E2E asserts an
     * exact set of requested analytic codes and would catch it, which is the
     * point: the net is right and the default would have been wrong.
     */
    includeDrawdownSummary?: boolean;
    /**
     * Adds a second historical VaR over a ~1-month horizon, alongside the daily one.
     *
     * L1 puts a bad day and a bad month on the same scale, and the month may not
     * be the day scaled by √21: that would be a model, and L1 states only what the
     * sample actually did. The backend compounds real overlapping windows
     * (`horizon_compounded_returns`), so this is a second observation, not an
     * extrapolation — which is why it costs a second request.
     */
    includeMonthlyVar?: boolean;
    /**
     * Adds the risk/return pair for the composition held today: the KPI wave a
     * second time on the backtest series, plus the per-asset scatter points.
     *
     * Opt-in for the same reason as the two above, and with a sharper edge. L3
     * asks "am I being paid for this risk" in the present tense, so it needs a
     * Sharpe, a Sortino and a beta that share one perimeter. The historical and
     * current-composition perimeters can disagree on those ratios by more than
     * half their own value, so mixing them is not untidy — it prints two
     * incompatible claims on one row.
     *
     * Only the level panel renders either, so only the level panel pays. Asset
     * Detail and the asset-set panel keep the wire they have.
     */
    includeCurrentCompositionRiskReturn?: boolean;
    /**
     * Adds the five per-asset analytics an asset set can answer.
     *
     * **Opt-in like the three above**, and for a sharper reason than tidiness:
     * the five codes are `ASSET_SET`-only, so on any other scope the capability
     * gate would drop them anyway and the flag would be decoration. It exists so
     * that the two comparison levels ask for the identical set and share one
     * flight — `queryRisk` caches and de-duplicates on the canonical request.
     *
     * 🔑 Clause ⓪ of the asset-set contract asks for *one preparation per
     * request*, and the backend's half of it is measured: `service.py:170`
     * prepares the joint series once per request, from the scope, window and
     * currency — never from the analytics list. So sections that ask different
     * questions over the same scope and window still get the same joint calendar,
     * and their figures stay commensurable even when they travel separately.
     */
    includeAssetSetLevels?: boolean;
    /**
     * The shared L3 benchmark, when one is chosen and it is not itself in the
     * selection. Drives `asset_set_comparison` inside the same request — see the
     * note where it is added.
     */
    assetSetBenchmarkId?: number | null;
}

/** Horizon, in observations, used for L1's "bad month" row. */
export const MONTHLY_VAR_HORIZON_DAYS = 21;

/** Instance id of the 1-day base VaR. */
export const DAILY_VAR_INSTANCE = 'base-historical-historical_var';

/** Instance id of the ~1-month base VaR, distinct so the two never get mixed up. */
export const MONTHLY_VAR_INSTANCE = 'base-historical-historical_var-monthly';

/** The two horizons of the per-asset VaR, kept apart for the same reason as the singular pair. */
export const ASSET_SET_DAILY_VAR_INSTANCE = 'base-historical-asset_set_var';
export const ASSET_SET_MONTHLY_VAR_INSTANCE = 'base-historical-asset_set_var-monthly';

/**
 * The base analytics the panel requests for a mode, keeping only those the
 * backend advertises for the current scope:
 * - `historical` → KPI (seeded with the applied risk-free rate), correlation,
 *   1-day 95% historical VaR, and — only when the call site opts in — the
 *   drawdown summary;
 * - `current_composition` → risk contribution.
 * A capability the catalog does not list is silently omitted, so the request
 * never asks for something the backend cannot compute — `drawdown_summary`, for
 * one, does not accept an asset set, because there is no single primary series
 * to draw down.
 */
export function buildBaseAnalytics(mode: RiskMode, ctx: BaseAnalyticsContext): RiskAnalyticRequest[] {
    const analytics: RiskAnalyticRequest[] = [];
    const add = (code: string, parameters: RiskAnalyticParameters = {}, instanceId?: string) => {
        if (ctx.hasCapability(code, mode)) {
            analytics.push(buildRiskAnalyticRequest(instanceId ?? `base-${mode}-${code}`, code, parameters));
        }
    };
    if (mode === 'historical') {
        add('historical_kpi', {
            risk_free_annual_rate: ctx.appliedRiskFreePercent / 100,
            target_annual_return: 0,
        });
        add('correlation');
        add('historical_var', {confidence_level: 0.95, horizon_days: 1}, DAILY_VAR_INSTANCE);
        if (ctx.includeMonthlyVar) {
            add('historical_var', {confidence_level: 0.95, horizon_days: MONTHLY_VAR_HORIZON_DAYS}, MONTHLY_VAR_INSTANCE);
        }
        if (ctx.includeDrawdownSummary) add('drawdown_summary');
        if (ctx.includeAssetSetLevels) {
            // The per-asset wave. Every code is `ASSET_SET`-only, so `add`'s
            // capability guard makes this block inert on every other scope.
            //
            // The risk-free rate is threaded into the KPI exactly as the singular
            // wave threads it: Sharpe and Sortino are charged against the reader's
            // setting, not against a constant this file chose.
            add('asset_set_kpi', {risk_free_annual_rate: ctx.appliedRiskFreePercent / 100, target_annual_return: 0});
            add('asset_set_var', {confidence_level: 0.95, horizon_days: 1}, ASSET_SET_DAILY_VAR_INSTANCE);
            // The bad month is compounded by the backend over real overlapping
            // windows, never scaled from the bad day — the same second observation
            // the singular L1 pays for, for the same reason.
            add('asset_set_var', {confidence_level: 0.95, horizon_days: MONTHLY_VAR_HORIZON_DAYS}, ASSET_SET_MONTHLY_VAR_INSTANCE);
            add('asset_set_drawdown');
            add('asset_set_risk_return');
            // 🔴 The benchmark rides in **this** request, not in one of its own.
            //
            // `RiskAssetSetComparisonOutput` publishes the reference's own
            // volatility and expected return so a scatter can place it beside the
            // holdings, and its docstring says why that is sound: "the reference
            // is prepared inside the same request as the scope". Asking for it
            // separately would prepare it against a joint calendar that does not
            // include the selection — the benchmark dot would then land on a
            // chart whose other dots were measured over different dates, which is
            // the failure `l3Helpers.buildRiskReturnPoints` already documents at
            // length for the singular case: "the dot would land in a place no
            // measurement puts it, on a chart that still looks right".
            //
            // The reference may not also be one of the measured — the payload
            // validator rejects that outright — so a benchmark that is itself in
            // the selection is not requested at all, and the section says so
            // rather than showing an error the reader cannot act on.
            if (ctx.assetSetBenchmarkId != null) add('asset_set_comparison', {comparison_asset_id: ctx.assetSetBenchmarkId});
        }
    } else {
        add('risk_contribution');
        if (ctx.includeCurrentCompositionRiskReturn) {
            // Same params as the historical wave: the risk-free rate is a property of
            // the reader's setting, not of the series it is charged against.
            add('historical_kpi', {
                risk_free_annual_rate: ctx.appliedRiskFreePercent / 100,
                target_annual_return: 0,
            });
            add('asset_risk_return');
        }
    }
    return analytics;
}
