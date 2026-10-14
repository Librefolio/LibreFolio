/**
 * One backend risk warning as a sentence.
 *
 * Its own module for the reason `levelMetadata` has one — `levelHelpers.ts` is at
 * its size ceiling — and re-exported from there, so consumers keep a single door
 * onto the level helpers.
 */
import type {RiskAnalyticResult} from '$lib/stores/risk/riskStore.svelte';
import {singleValue} from '$lib/risk/riskTypes';

export type RiskResultWarning = NonNullable<RiskAnalyticResult['warnings']>[number];

/** A value an ICU sentence can take. */
type InterpolationValue = string | number | boolean | null | undefined;

/** The translator a warning's sentence goes through; svelte-i18n's `$_` / `$t` fits it. */
export type WarningTranslator = (id: string, options?: {values?: Record<string, InterpolationValue>}) => string;

/** The backend's parameters as ICU values: lists joined, anything that is not a value left out. */
function interpolationValues(params: unknown): Record<string, InterpolationValue> {
    const values: Record<string, InterpolationValue> = {};
    if (!params || typeof params !== 'object' || Array.isArray(params)) return values;
    for (const [name, value] of Object.entries(params as Record<string, unknown>)) {
        if (value === null || typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean') values[name] = value;
        else if (Array.isArray(value)) values[name] = value.map(String).join(', ');
    }
    return values;
}

/**
 * The sentence of one warning: its key with its parameters, or the backend's own words.
 *
 * The backend names the key and supplies the values — names, counts, days
 * (developer's decision of 24/09/2026: the standard wording lives in the
 * catalogues, names and numbers come from the backend) — so no key is built here
 * from a code. Two ways the translation can fail are caught rather than shown: a
 * key the catalogue lacks (svelte-i18n echoes the id back) and a format that
 * failed (svelte-i18n returns the raw ICU source, braces included, when a value
 * is missing). Both fall back to the backend's English sentence: never a key,
 * never a placeholder. A name that itself contains a brace falls back too — the
 * price of catching every failed format with one rule.
 */
export function warningSentence(warning: RiskResultWarning | null | undefined, translate?: WarningTranslator): string {
    if (!warning) return '';
    const message = typeof warning.message === 'string' ? warning.message.trim() : '';
    const rawKey = singleValue(warning.message_i18n_key);
    const key = typeof rawKey === 'string' ? rawKey.trim() : '';
    if (translate && key) {
        const translated = translate(key, {values: interpolationValues(warning.message_params)});
        if (typeof translated === 'string') {
            const sentence = translated.trim();
            if (sentence !== '' && sentence !== key && !sentence.includes('{')) return sentence;
        }
    }
    return message;
}

/** A warning's `details` as a plain record: `{}` when it has none, or none that is a record. */
function detailsOf(warning: RiskResultWarning | null | undefined): Record<string, unknown> {
    const details: unknown = warning?.details;
    return details !== null && typeof details === 'object' && !Array.isArray(details) ? (details as Record<string, unknown>) : {};
}

/** The cause a warning states in `details.reason` (for an exclusion, `no_price_source`, `missing_price`, …), when it states one. */
export function warningReason(warning: RiskResultWarning | null | undefined): string | undefined {
    const reason = detailsOf(warning).reason;
    return typeof reason === 'string' && reason.trim() !== '' ? reason.trim() : undefined;
}

/**
 * The assets a warning is about, read as the backend reads them to name them in the sentence
 * (`_warning_asset_ids`): `details.asset_ids`, or else a single `details.asset_id`.
 *
 * All or nothing, where the backend filters: a list with anything but integers is not taken at
 * all, so a badge drawn from it can never silently leave an asset out.
 */
export function warningAssetIds(warning: RiskResultWarning | null | undefined): number[] | undefined {
    const details = detailsOf(warning);
    const ids = details.asset_ids ?? (details.asset_id === undefined ? undefined : [details.asset_id]);
    return Array.isArray(ids) && ids.length > 0 && ids.every((id) => Number.isInteger(id)) ? (ids as number[]) : undefined;
}
