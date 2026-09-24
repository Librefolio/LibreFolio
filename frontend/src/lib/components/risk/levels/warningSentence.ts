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
