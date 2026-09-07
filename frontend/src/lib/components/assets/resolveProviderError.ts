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
export interface ProviderErrorLike {
    error?: string | null;
    error_code?: string | null;
    error_details?: Record<string, unknown> | null;
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

/**
 * Resolve a failed probe operation to a localized message.
 * Falls back to the raw English `error` when the code is unknown — never hides
 * information the backend sent.
 */
export function resolveProviderError(op: ProviderErrorLike, t: TFn): string {
    const code = op.error_code?.toUpperCase();
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
