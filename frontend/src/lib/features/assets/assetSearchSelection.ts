/**
 * assetSearchSelection — what choosing a provider search result writes into AssetModal, as pure functions.
 *
 * The modal applies the result and keeps the side effects (the "which code leads" chooser, the provider probe, the
 * metadata comparison, the reuse prompt): here only the decisions, so each branch is unit-testable without
 * mounting it.
 *
 * @module features/assets/assetSearchSelection
 */
import {schemas} from '$lib/api/generated';
import {ASSET_TYPES} from '$lib/utils/assetTypes';
import {generateUUID} from '$lib/utils/core/uuid';
import type {IdentifierRow} from './assetIdentifiers';

/** The asset type of a search result: a known type, upper-cased; anything else `OTHER`. */
export function searchResultAssetType(raw: string): string {
    const upper = raw.toUpperCase();
    return (ASSET_TYPES as readonly string[]).includes(upper) ? upper : 'OTHER';
}

/** What the result's identifier does to the form's rows. */
export type SearchIdentifierOutcome =
    /** The result carries no typed identifier. */
    | {kind: 'none'}
    /** Two different codes of the same type, both legitimate: the user chooses which one leads. */
    | {kind: 'conflict'; type: string; incoming: string; current: string}
    /** The rows with the result's code written in (its row updated, or a new row). */
    | {kind: 'rows'; rows: IdentifierRow[]};

/** The provider of a search result, as far as the selection needs it: its code and the input types it accepts. */
export interface SearchResultProvider {
    code: string;
    acceptedTypes: readonly string[];
}

/** A provider whose own code is an input type (PROVIDER_ID): its OTHER search rows carry that code (project 76, P3). */
function takesProviderId(provider: SearchResultProvider | null | undefined): provider is SearchResultProvider {
    return !!provider && provider.acceptedTypes.includes('PROVIDER_ID');
}

/**
 * The outcome of a search result's identifier (`identifier_type` + `identifier`) on the form's rows. A row of the
 * same type that is empty, or holds the same code in another case, takes the result's code.
 *
 * For a provider that accepts PROVIDER_ID (CoinGecko) only, an OTHER result is its own code, and OTHER is a list that
 * grows (project 76, P3, the consultant's rule): the code is written as `<provider>:<code>` (`coingecko:bitcoin`) into
 * an empty OTHER row or a new one, unless the list already holds it; never a conflict. Any other provider's OTHER row
 * behaves as before.
 */
export function searchResultIdentifier(rows: IdentifierRow[], identifierType: string | null | undefined, identifier: unknown, provider?: SearchResultProvider | null): SearchIdentifierOutcome {
    const type = (identifierType ?? '').toUpperCase();
    if (!type || !identifier) return {kind: 'none'};
    if (type === 'OTHER' && takesProviderId(provider)) return {kind: 'rows', rows: withOtherCode(rows, `${provider.code}:${String(identifier).trim()}`)};
    const existing = rows.find((r) => r.type === type);
    const incoming = String(identifier).trim();
    const current = (existing?.value ?? '').trim();
    if (existing && current !== '' && current.toUpperCase() !== incoming.toUpperCase()) return {kind: 'conflict', type, incoming, current};
    if (existing) return {kind: 'rows', rows: rows.map((r) => (r.type === type ? {...r, value: incoming} : r))};
    return {kind: 'rows', rows: [...rows, {id: generateUUID(), type, value: incoming}]};
}

/** `code` among the OTHER rows: already there (any case) → unchanged; else into the first empty one, or a new row. */
function withOtherCode(rows: IdentifierRow[], code: string): IdentifierRow[] {
    const others = rows.filter((r) => r.type === 'OTHER');
    if (others.some((r) => r.value.trim().toUpperCase() === code.toUpperCase())) return rows;
    const empty = others.find((r) => r.value.trim() === '');
    if (empty) return rows.map((r) => (r === empty ? {...r, value: code} : r));
    return [...rows, {id: generateUUID(), type: 'OTHER', value: code}];
}

/** The input types an assignment accepts (the generated `ProviderInputType`). */
const ASSIGNMENT_TYPES: readonly string[] = schemas.ProviderInputType.options;

/**
 * The assignment's type for a search result (project 76, P3): the result's type when an assignment accepts it (TICKER,
 * ISIN…); an OTHER result of a provider that accepts PROVIDER_ID (CoinGecko), PROVIDER_ID. Anything else as it is: the
 * server reads OTHER as URL, as it always has (Borsa Italiana's fallback rows).
 */
export function searchResultAssignmentType(identifierType: string | null | undefined, acceptedTypes: readonly string[]): string {
    const type = (identifierType ?? '').toUpperCase();
    if (ASSIGNMENT_TYPES.includes(type)) return type;
    if (type === 'OTHER' && acceptedTypes.includes('PROVIDER_ID')) return 'PROVIDER_ID';
    return type;
}

/**
 * The provider params of a search result (e.g. language, currency): the provider's own take priority, and the
 * result's currency is added only when the provider did not set one, and only for a provider whose params schema has a
 * `currency` field (justETF, the CSS scraper: never CoinGecko's `vs_currency` nor a provider with no params; project 76,
 * P3). `paramKeys` null: the schema is not known, the currency is added as before. `null` when nothing remains.
 */
export function searchResultProviderParams(params: Record<string, any> | null | undefined, currency: string | null | undefined, paramKeys: readonly string[] | null = null): Record<string, any> | null {
    const merged: Record<string, any> = {...(params ?? {})};
    if (currency && !('currency' in merged) && (paramKeys === null || paramKeys.includes('currency'))) merged.currency = currency;
    return Object.keys(merged).length > 0 ? merged : null;
}
