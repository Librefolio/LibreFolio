/**
 * assetPayload — pure builders shared by the AssetModal create/edit save paths.
 *
 * Both `saveCreate` and `saveEdit` normalise the quote-base quantity the same way; pulling it out keeps the two save
 * paths from drifting apart. The request items themselves (create, patch, provider assignment) are built here too, from
 * a plain copy of the form (`AssetFormFields`).
 *
 * The description, the sectors and the countries are the profile's (plan 68, E9): they leave as `profile`, never as
 * `classification_params`.
 *
 * @module features/assets/assetPayload
 */
import type {EnricherBinding} from './enrichers/enrichersEditState';
import {identifierRowsToColumns, type IdentifierRow} from './assetIdentifiers';

/** A distribution map: `{Technology: 0.4, Health: 0.6}` etc. */
export type Distribution = Record<string, number>;

export function normalizeDistribution(values: Record<string, string | number>): Distribution {
    return Object.fromEntries(
        Object.entries(values).map(([key, value]): [string, number] => {
            const weight = Number(value);
            if ((typeof value !== 'string' && typeof value !== 'number') || String(value).trim() === '' || !Number.isFinite(weight)) throw new Error('Invalid distribution weight.');
            return [key, weight];
        }),
    );
}

/**
 * The quote-base quantity sent to the API: at least 1. A falsy value (0, NaN) or a
 * non-positive number collapses to 1; any other value passes through unchanged.
 * (The integer-truncation rule is enforced separately at the input, via
 * `quoteBaseQuantityInvalid`; this is only the non-positive floor the save applies.)
 */
export function normalizeQuoteBaseQuantity(qbq: number): number {
    return !qbq || qbq <= 0 ? 1 : qbq;
}

/** The form values the save requests are built from. */
export interface AssetFormFields {
    displayName: string;
    currency: string;
    assetType: string;
    iconUrl: string | null;
    quoteBaseQuantity: number;
    active: boolean;
    isBenchmark: boolean;
    /** The provider page the user linked (`user_url`). */
    userUrl: string;
    identifierRows: IdentifierRow[];
    /** The asset's enrichers (plan 68, E8a): code → binding, the order of the keys is the priority. */
    enrichers: Record<string, EnricherBinding>;
    /**
     * The profile's pending changes, as `PATCH /assets` takes them (`profilePatch`, plan 68 E8b): voice → a value, null
     * (left empty on purpose) or `{from, seen}` (a source's value). Absent or empty: nothing to write.
     */
    profile?: Record<string, unknown>;
}

function profileOf(form: AssetFormFields): {profile?: Record<string, unknown>} {
    return form.profile && Object.keys(form.profile).length > 0 ? {profile: form.profile} : {};
}

/** Two enricher lists are the same when they hold the same bindings in the same order: the order is the priority. */
export function sameEnrichers(left: Record<string, EnricherBinding>, right: Record<string, EnricherBinding>): boolean {
    return JSON.stringify(Object.entries(left)) === JSON.stringify(Object.entries(right));
}

/**
 * The item of the create request. An empty icon or user URL is omitted; the identifier columns come from the rows.
 */
export function buildCreateItem(form: AssetFormFields) {
    return {
        display_name: form.displayName.trim(),
        currency: form.currency,
        asset_type: form.assetType,
        icon_url: form.iconUrl || undefined,
        quote_base_quantity: normalizeQuoteBaseQuantity(form.quoteBaseQuantity),
        active: form.active,
        is_benchmark: form.isBenchmark,
        user_url: form.userUrl || undefined,
        ...identifierRowsToColumns(form.identifierRows),
        ...(Object.keys(form.enrichers).length > 0 ? {enrichers: form.enrichers} : {}),
        ...profileOf(form),
    };
}

/**
 * The item of the edit request. Unlike the create item, an empty user URL or identifier column is sent as `null` (a
 * deliberate clear) and the icon as it is; the OTHER identifiers always go as the whole list, `[]` when no row is left,
 * because the backend reads `null` there as "leave unchanged"; `enrichers` is present only when the list or its order
 * differs from the one the modal opened with (absent means unchanged, `{}` clears them).
 */
export function buildPatchItem(assetId: number, form: AssetFormFields, initialEnrichers: Record<string, EnricherBinding> = {}) {
    const idCols = identifierRowsToColumns(form.identifierRows);
    return {
        asset_id: assetId,
        display_name: form.displayName.trim(),
        currency: form.currency,
        asset_type: form.assetType,
        icon_url: form.iconUrl,
        quote_base_quantity: normalizeQuoteBaseQuantity(form.quoteBaseQuantity),
        active: form.active,
        is_benchmark: form.isBenchmark,
        user_url: form.userUrl || null,
        identifier_isin: idCols.identifier_isin || null,
        identifier_ticker: idCols.identifier_ticker || null,
        identifier_cusip: idCols.identifier_cusip || null,
        identifier_sedol: idCols.identifier_sedol || null,
        identifier_figi: idCols.identifier_figi || null,
        identifier_uuid: idCols.identifier_uuid || null,
        identifier_other: idCols.identifier_other ?? [],
        ...(sameEnrichers(form.enrichers, initialEnrichers) ? {} : {enrichers: form.enrichers}),
        ...profileOf(form),
    };
}

/** The provider the modal assigns to an asset. */
export interface ProviderAssignment {
    code: string;
    identifier: string;
    identifierType: string;
    params: Record<string, any> | null;
}

/** The item of the provider-assignment request. */
export function buildProviderAssignItem(assetId: number, provider: ProviderAssignment) {
    return {
        asset_id: assetId,
        provider_code: provider.code,
        identifier: provider.identifier,
        identifier_type: provider.identifierType,
        provider_params: provider.params,
    };
}
