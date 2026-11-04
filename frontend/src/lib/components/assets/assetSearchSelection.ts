/**
 * assetSearchSelection — what choosing a provider search result writes into AssetModal, as pure functions.
 *
 * The modal applies the result and keeps the side effects (the "which code leads" chooser, the provider probe, the
 * metadata comparison, the reuse prompt): here only the decisions, so each branch is unit-testable without
 * mounting it.
 *
 * @module components/assets/assetSearchSelection
 */
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

/**
 * The outcome of a search result's identifier (`identifier_type` + `identifier`) on the form's rows. A row of the
 * same type that is empty, or holds the same code in another case, takes the result's code.
 */
export function searchResultIdentifier(rows: IdentifierRow[], identifierType: string | null | undefined, identifier: unknown): SearchIdentifierOutcome {
    const type = (identifierType ?? '').toUpperCase();
    if (!type || !identifier) return {kind: 'none'};
    const existing = rows.find((r) => r.type === type);
    const incoming = String(identifier).trim();
    const current = (existing?.value ?? '').trim();
    if (existing && current !== '' && current.toUpperCase() !== incoming.toUpperCase()) return {kind: 'conflict', type, incoming, current};
    if (existing) return {kind: 'rows', rows: rows.map((r) => (r.type === type ? {...r, value: incoming} : r))};
    return {kind: 'rows', rows: [...rows, {id: generateUUID(), type, value: incoming}]};
}

/**
 * The provider params of a search result (e.g. language, currency): the provider's own take priority, and the
 * result's currency is added only when the provider did not set one. `null` when nothing remains.
 */
export function searchResultProviderParams(params: Record<string, any> | null | undefined, currency: string | null | undefined): Record<string, any> | null {
    const merged: Record<string, any> = {...(params ?? {})};
    if (currency && !('currency' in merged)) merged.currency = currency;
    return Object.keys(merged).length > 0 ? merged : null;
}
