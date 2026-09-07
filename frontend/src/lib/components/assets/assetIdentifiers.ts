/**
 * assetIdentifiers — pure conversion between an asset's stored identifier columns
 * and the editable "identifier rows" the AssetModal table binds to.
 *
 * Extracted out of `AssetModal.svelte` so every branch (the OTHER-is-a-JSON-list
 * special case, the defensive coercion of a non-string element, the "which type
 * is still free" pick) is unit-testable without mounting the modal.
 *
 * `generateUUID` is imported here so the call sites in the component stay
 * unchanged; row ids are opaque, so tests assert on `type`/`value` and on id
 * uniqueness, never on a specific id value.
 *
 * @module components/assets/assetIdentifiers
 */
import {IDENTIFIER_TYPES} from '$lib/utils/assetTypes';
import {generateUUID} from '$lib/utils/core/uuid';

export interface IdentifierRow {
    id: string;
    type: string;
    value: string;
    autoFilled?: boolean;
}

/**
 * The identifier-bearing subset of an asset payload. A full `AssetData` (from the
 * modal) is structurally assignable to this — we only read the identifier columns.
 */
export interface IdentifierColumns {
    identifier_isin?: string | null;
    identifier_ticker?: string | null;
    identifier_cusip?: string | null;
    identifier_sedol?: string | null;
    identifier_figi?: string | null;
    identifier_uuid?: string | null;
    identifier_other?: string | string[] | null;
}

/** DB column key for a single-valued identifier type, e.g. `ISIN` → `identifier_isin`. */
function columnKey(idType: string): keyof IdentifierColumns {
    return `identifier_${idType.toLowerCase()}` as keyof IdentifierColumns;
}

/**
 * Expand the stored identifier columns into editable rows, one row per value.
 *
 * - Single-valued types (ISIN, TICKER, …) yield at most one row, only when set.
 * - OTHER is a JSON list of soft identifiers → one row per element; a legacy
 *   scalar string is tolerated, and each element is coerced to a string so a
 *   non-string element from a prefill/metadata payload cannot throw on `.trim()`.
 */
export function columnsToIdentifierRows(data: IdentifierColumns): IdentifierRow[] {
    const rows: IdentifierRow[] = [];
    for (const idType of IDENTIFIER_TYPES) {
        if (idType === 'OTHER') {
            const raw = data.identifier_other;
            const values = Array.isArray(raw) ? raw : raw ? [raw] : [];
            for (const v of values) {
                const s = typeof v === 'string' ? v : String(v ?? '');
                if (s.trim()) rows.push({id: generateUUID(), type: 'OTHER', value: s});
            }
        } else {
            const value = (data[columnKey(idType)] as string) ?? '';
            if (value) rows.push({id: generateUUID(), type: idType, value});
        }
    }
    return rows;
}

/**
 * Collapse editable rows back into the column payload sent to the API.
 *
 * Every single-valued column is reset to `undefined` first (so a cleared row
 * clears the column), then filled from the first matching non-empty row. OTHER is
 * additive: every non-empty OTHER row is collected into a JSON list (or `undefined`
 * when none). Values are trimmed and coerced defensively.
 */
export function identifierRowsToColumns(rows: IdentifierRow[]): Record<string, string | string[] | undefined> {
    const result: Record<string, string | string[] | undefined> = {};
    for (const idType of IDENTIFIER_TYPES) {
        result[columnKey(idType)] = undefined;
    }
    const others: string[] = [];
    for (const row of rows) {
        const v = typeof row.value === 'string' ? row.value : String(row.value ?? '');
        if (!v.trim()) continue;
        if (row.type === 'OTHER') {
            others.push(v.trim());
        } else {
            result[`identifier_${row.type.toLowerCase()}`] = v.trim();
        }
    }
    result.identifier_other = others.length > 0 ? others : undefined;
    return result;
}

/**
 * The next single-valued identifier type not yet present in `rows`, or `null` when
 * every non-OTHER type is already used. OTHER is excluded — it is managed by the
 * tag input, not the fixed-type table.
 */
export function nextAvailableIdentifierType(rows: IdentifierRow[]): string | null {
    const used = new Set(rows.map((r) => r.type));
    return IDENTIFIER_TYPES.find((t) => t !== 'OTHER' && !used.has(t)) ?? null;
}

/** `identifier_isin` → `ISIN`. The inverse naming of {@link columnKey}. */
export function fieldToIdType(field: string): string {
    return field.replace('identifier_', '').toUpperCase();
}
