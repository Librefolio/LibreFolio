/**
 * resolveProviderError — localized message for a failed provider operation (I3).
 *
 * The backend sends structured `error_code` + `error_details` next to the raw
 * English `error` text (see `BaseProbeOperationResult`). The pattern mirrors
 * `resolveValidationMessage.ts`: a stable code plus parameters on the wire,
 * the localized text owned by the frontend.
 *
 * Adoption is deliberately incremental (plan P6/I3, rescoped 2026-09-02): only
 * the codes a user actually meets on the "Test Configuration" surface are
 * mapped — everything else falls back to the raw English message, unchanged.
 */
import {uiLocale} from '$lib/stores/app/uiLocale';
import {formatDateTime} from '$lib/utils/core/formatDateTime';

export interface ProviderErrorLike {
    error?: string | null;
    error_code?: string | null;
    error_details?: Record<string, unknown> | null;
    /** With `RATE_LIMITED`: seconds until the provider may be called again (also in `error_details.retry_after`). */
    retry_after?: number | null;
}

type InterpolationValue = string | number | boolean | Date | null | undefined;

type TFn = (key: string, opts?: {values?: Record<string, InterpolationValue>}) => string;

/** Keep only interpolation-safe primitive values from the wire details. */
function interpolationValues(details: Record<string, unknown>): Record<string, InterpolationValue> {
    const out: Record<string, InterpolationValue> = {};
    for (const [key, value] of Object.entries(details)) {
        if (value === null || ['string', 'number', 'boolean'].includes(typeof value)) out[key] = value as InterpolationValue;
        else out[key] = String(value);
    }
    return out;
}

/** The wait of a `RATE_LIMITED` refusal, in seconds: `retry_after`, else `error_details.retry_after`; null when unknown. */
function retryAfterSeconds(op: ProviderErrorLike): number | null {
    const raw = op.retry_after ?? op.error_details?.retry_after;
    const seconds = typeof raw === 'string' ? Number(raw) : raw;
    return typeof seconds === 'number' && Number.isFinite(seconds) && seconds >= 0 ? seconds : null;
}

/** The moment a pause ends, `retryAfterSeconds` from `now`, rounded **up** to the minute so that nobody tries again before it. */
function resumeMoment(retryAfterSeconds: number, now: Date): Date {
    return new Date(Math.ceil((now.getTime() + retryAfterSeconds * 1000) / 60_000) * 60_000);
}

/** Whether a pause of `retryAfterSeconds` from `now` ends today, in local time (same rounding as `formatResumeTime`). */
export function resumesToday(retryAfterSeconds: number, now: Date = new Date()): boolean {
    return resumeMoment(retryAfterSeconds, now).toDateString() === now.toDateString();
}

/**
 * The local moment a pause ends, `retryAfterSeconds` from `now`, rounded **up** to the minute so that
 * nobody tries again before it: the time alone when it is today, the date and time otherwise.
 */
export function formatResumeTime(retryAfterSeconds: number, now: Date = new Date(), locale: string = uiLocale()): string {
    const until = resumeMoment(retryAfterSeconds, now);
    if (until.toDateString() === now.toDateString()) return until.toLocaleTimeString(locale, {hour: '2-digit', minute: '2-digit'});
    return formatDateTime(until, locale);
}

/**
 * `RATE_LIMITED` (X8): the provider is paused after «too many requests» — «paused until HH:MM» in
 * local time (`RATE_LIMITED`, or `RATE_LIMITED_DAY` with the date when the pause ends another day),
 * or a message without a time when the wait is unknown. The texts fit the 60 characters of the probe's
 * one-line summary, date included.
 */
function resolveRateLimited(op: ProviderErrorLike, t: TFn): string {
    const seconds = retryAfterSeconds(op);
    if (seconds !== null) {
        const now = new Date();
        const key = resumesToday(seconds, now) ? 'providerErrors.RATE_LIMITED' : 'providerErrors.RATE_LIMITED_DAY';
        const pausedUntil = t(key, {values: {time: formatResumeTime(seconds, now)}});
        if (pausedUntil !== key) return pausedUntil;
    }
    const noTime = t('providerErrors.RATE_LIMITED_NO_TIME');
    if (noTime !== 'providerErrors.RATE_LIMITED_NO_TIME') return noTime;
    return op.error || 'Unknown error';
}

/**
 * Resolve a failed probe operation to a localized message.
 * Falls back to the raw English `error` when the code is unknown — never hides
 * information the backend sent.
 */
export function resolveProviderError(op: ProviderErrorLike, t: TFn): string {
    const code = op.error_code?.toUpperCase();
    if (code === 'RATE_LIMITED') return resolveRateLimited(op, t);
    if (code) {
        const values = interpolationValues(op.error_details ?? {});
        // NO_DATA with a nav_date is the stale-fund-NAV case (borsa_italiana):
        // the more specific message explains WHY stale data is refused.
        if (code === 'NO_DATA' && values['nav_date']) {
            const stale = t('providerErrors.NO_DATA_STALE', {values});
            if (stale !== 'providerErrors.NO_DATA_STALE') return stale;
        }
        const key = `providerErrors.${code}`;
        const translated = t(key, {values});
        if (translated !== key) return translated;
    }
    return op.error || 'Unknown error';
}
