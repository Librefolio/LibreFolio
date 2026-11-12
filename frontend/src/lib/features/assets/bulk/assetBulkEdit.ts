/**
 * assetBulkEdit.ts — The pure half of the bulk edit of assets (lane 65, mockup-AB-v5).
 *
 * The modal «Modifica N asset» shows what the selected assets hold now (counts per field), lets the user choose a
 * value per field («Lascia com'è» by default), and sends `PATCH /assets` (or `POST /assets/validate`) one item per
 * asset, carrying only what changes for that asset. This module has no catalogue, no DOM and no store: it turns the
 * selected rows and the user's draft into counts, the payload and the rows of the summary. The modal translates and
 * draws; the backend decides what is a block or a warning (`issues`, `warnings`).
 *
 * Fields, in the order of the zones: `icon_url` and `user_url` (Altri dettagli), `asset_type` (Classificazione),
 * `quote_base_quantity`, `active` and `is_benchmark` (Prezzo e stato).
 *
 * «Leave as is» is the default of every field: `null`, `undefined`, an empty or blank text, or a unit that is not a
 * whole number from 1. In bulk nothing is cleared: an empty URL or no icon never goes out as `null`; that is done from
 * the single asset's modal.
 */

/** The fields of the modal, in the order of its zones. */
export const FIELD_ORDER = ['icon_url', 'user_url', 'asset_type', 'quote_base_quantity', 'active', 'is_benchmark'] as const;

export type BulkFieldKey = (typeof FIELD_ORDER)[number];

/** The part of a list row the bulk edit reads (`AssetRow`, plus the benchmark flag and the user URL). */
export interface BulkAsset {
    id: number;
    display_name: string;
    asset_type?: string | null;
    active: boolean;
    is_benchmark?: boolean | null;
    quote_base_quantity?: number | null;
    icon_url?: string | null;
    user_url?: string | null;
}

/** What the user chose. A field not set, `null`, or blank is «leave as is». */
export interface BulkDraft {
    icon_url?: string | null;
    user_url?: string | null;
    asset_type?: string | null;
    quote_base_quantity?: number | null;
    active?: boolean | null;
    is_benchmark?: boolean | null;
}

/** One item of the `PATCH /assets` and `POST /assets/validate` payload: the asset and only the fields that change for it. */
export interface BulkPatchItem {
    asset_id: number;
    icon_url?: string;
    user_url?: string;
    asset_type?: string;
    quote_base_quantity?: number;
    active?: boolean;
    is_benchmark?: boolean;
}

/** The value of a field, as the summary shows it: a text, a number, a flag, or `null` (no icon, no URL). */
export type BulkValue = string | number | boolean | null;

// =============================================================================
// Normalised current values — as the backend reads them
// =============================================================================

/** The default type of an asset (`AssetType.OTHER`): a row without one reads as that. */
const DEFAULT_TYPE = 'OTHER';

function text(value: string | null | undefined): string {
    return typeof value === 'string' ? value.trim() : '';
}

function currentType(asset: BulkAsset): string {
    return text(asset.asset_type) || DEFAULT_TYPE;
}

/** A missing unit, or one below 1, reads 1 (the backend stores ≤ 0 as 1 and a NULL reads as 1). */
function currentUnit(asset: BulkAsset): number {
    const unit = asset.quote_base_quantity;
    return typeof unit === 'number' && Number.isInteger(unit) && unit >= 1 ? unit : 1;
}

/** The value an asset holds for a field, normalised: what the draft is compared with and what the summary says «before». */
function currentValue(asset: BulkAsset, field: BulkFieldKey): BulkValue {
    switch (field) {
        case 'icon_url':
            return text(asset.icon_url) || null;
        case 'user_url':
            return text(asset.user_url) || null;
        case 'asset_type':
            return currentType(asset);
        case 'quote_base_quantity':
            return currentUnit(asset);
        case 'active':
            return asset.active === true;
        case 'is_benchmark':
            return asset.is_benchmark === true;
    }
}

// =============================================================================
// The draft: what is touched
// =============================================================================

export type QuoteBaseCheck = 'empty' | 'notInteger' | 'belowOne' | 'ok';

/** What the user typed in «Unità per singolo prezzo»: empty is «leave as is», anything else must be a whole number from 1. */
export function validateQuoteBase(input: string | number | null | undefined): QuoteBaseCheck {
    if (input === null || input === undefined) return 'empty';
    if (typeof input === 'string') {
        const trimmed = input.trim();
        if (trimmed === '') return 'empty';
        if (!/^[+-]?\d+$/.test(trimmed)) return 'notInteger';
        return Number(trimmed) >= 1 ? 'ok' : 'belowOne';
    }
    if (!Number.isInteger(input)) return 'notInteger';
    return input >= 1 ? 'ok' : 'belowOne';
}

/** The value the draft holds for a field, or `undefined` when the field says «leave as is». */
function chosenValue(draft: BulkDraft, field: BulkFieldKey): BulkValue | undefined {
    switch (field) {
        case 'icon_url':
        case 'user_url': {
            const chosen = text(draft[field]);
            return chosen === '' ? undefined : chosen;
        }
        case 'asset_type': {
            const chosen = text(draft.asset_type);
            return chosen === '' ? undefined : chosen;
        }
        case 'quote_base_quantity':
            return typeof draft.quote_base_quantity === 'number' && validateQuoteBase(draft.quote_base_quantity) === 'ok' ? draft.quote_base_quantity : undefined;
        case 'active':
        case 'is_benchmark':
            return typeof draft[field] === 'boolean' ? draft[field] : undefined;
    }
}

/** The fields the user changed from «leave as is», in the order of the zones. */
export function touchedFields(draft: BulkDraft): BulkFieldKey[] {
    return FIELD_ORDER.filter((field) => chosenValue(draft, field) !== undefined);
}

/** True when saving would change at least one asset: what turns «Continua» on. */
export function hasChanges(assets: readonly BulkAsset[], draft: BulkDraft): boolean {
    return buildBulkPatch(assets, draft).length > 0;
}

// =============================================================================
// Counts of the current values
// =============================================================================

export interface ValueCount<T> {
    value: T;
    count: number;
}

export interface ValueCounts<T> {
    /** Every distinct value, the most frequent first, ties by first appearance. */
    groups: ValueCount<T>[];
    /** What the field shows: all of them up to 4 distinct values; beyond that, the first 3. */
    shown: ValueCount<T>[];
    /** How many distinct values `shown` leaves out («+N»). */
    more: number;
    distinct: number;
}

/** Up to this many distinct values are shown whole; beyond it, the first {@link SHOWN_WHEN_MANY} and «+N». */
export const MAX_WHOLE_VALUES = 4;
export const SHOWN_WHEN_MANY = 3;

/** The distinct values of a list with their counts. */
export function countValues<T>(values: readonly T[]): ValueCounts<T> {
    const counts = new Map<T, number>();
    for (const value of values) counts.set(value, (counts.get(value) ?? 0) + 1);
    // `Array.prototype.sort` is stable: equal counts keep the order of first appearance.
    const groups = [...counts].map(([value, count]) => ({value, count})).sort((a, b) => b.count - a.count);
    const whole = groups.length <= MAX_WHOLE_VALUES;
    return {groups, shown: whole ? groups : groups.slice(0, SHOWN_WHEN_MANY), more: whole ? 0 : groups.length - SHOWN_WHEN_MANY, distinct: groups.length};
}

export interface CurrentSummary {
    total: number;
    asset_type: ValueCounts<string>;
    active: ValueCounts<boolean>;
    is_benchmark: ValueCounts<boolean>;
    quote_base_quantity: ValueCounts<number>;
    /** «3 con icona, 2 senza». */
    icon: {with: number; without: number};
    /** «3 diversi · vuoto per 2»: distinct non-empty URLs, and how many assets have none. */
    user_url: {distinct: number; empty: number};
}

/** What the selected assets hold now, for the line «Ora: …» under each field. */
export function summarizeCurrent(assets: readonly BulkAsset[]): CurrentSummary {
    const icons = assets.map((asset) => currentValue(asset, 'icon_url'));
    const urls = assets.map((asset) => currentValue(asset, 'user_url'));
    return {
        total: assets.length,
        asset_type: countValues(assets.map(currentType)),
        active: countValues(assets.map((asset) => currentValue(asset, 'active') as boolean)),
        is_benchmark: countValues(assets.map((asset) => currentValue(asset, 'is_benchmark') as boolean)),
        quote_base_quantity: countValues(assets.map(currentUnit)),
        icon: {with: icons.filter((icon) => icon !== null).length, without: icons.filter((icon) => icon === null).length},
        user_url: {distinct: new Set(urls.filter((url) => url !== null)).size, empty: urls.filter((url) => url === null).length},
    };
}

// =============================================================================
// The payload
// =============================================================================

/**
 * The items of `PATCH /assets` and `POST /assets/validate`: one per asset that changes, in the order of the selection,
 * with `asset_id` and only the fields whose chosen value differs from that asset's own. An asset that already has every
 * chosen value does not go. Nothing is cleared: no `null` is ever sent.
 */
export function buildBulkPatch(assets: readonly BulkAsset[], draft: BulkDraft): BulkPatchItem[] {
    const touched = touchedFields(draft);
    const items: BulkPatchItem[] = [];
    for (const asset of assets) {
        const item: Record<string, BulkValue> = {};
        for (const field of touched) {
            const chosen = chosenValue(draft, field) as BulkValue;
            if (currentValue(asset, field) !== chosen) item[field] = chosen;
        }
        if (Object.keys(item).length > 0) items.push({asset_id: asset.id, ...item} as BulkPatchItem);
    }
    return items;
}

// =============================================================================
// The summary (prima → dopo)
// =============================================================================

export interface SummaryCell {
    field: BulkFieldKey;
    before: BulkValue;
    after: BulkValue;
    /** The asset already has the value: the table says «già …» and nothing is sent for this field. */
    unchanged: boolean;
}

export interface SummaryRow {
    id: number;
    name: string;
    /** One cell per touched field, in the order of the zones. */
    cells: SummaryCell[];
}

export interface FieldImpact {
    field: BulkFieldKey;
    after: BulkValue;
    /** How many selected assets change this field («Cambia per 4 su 5»). */
    changing: number;
    total: number;
    /** The ids of the assets that already have the chosen value («Boreal lo è già»). */
    alreadyIds: number[];
}

export interface ChangeSummary {
    selected: number;
    /** How many assets change at least one field: the assets of the payload. */
    changing: number;
    touched: BulkFieldKey[];
    fields: FieldImpact[];
    /** One row per changing asset, in the order of the selection. */
    rows: SummaryRow[];
}

/** What saving would do, for the sub-line of each touched field and for the summary table. */
export function summarizeChanges(assets: readonly BulkAsset[], draft: BulkDraft): ChangeSummary {
    const touched = touchedFields(draft);
    const fields: FieldImpact[] = touched.map((field) => {
        const after = chosenValue(draft, field) as BulkValue;
        const alreadyIds = assets.filter((asset) => currentValue(asset, field) === after).map((asset) => asset.id);
        return {field, after, changing: assets.length - alreadyIds.length, total: assets.length, alreadyIds};
    });
    const rows: SummaryRow[] = [];
    for (const asset of assets) {
        const cells: SummaryCell[] = touched.map((field) => {
            const before = currentValue(asset, field);
            const after = chosenValue(draft, field) as BulkValue;
            return {field, before, after, unchanged: before === after};
        });
        if (cells.some((cell) => !cell.unchanged)) rows.push({id: asset.id, name: asset.display_name, cells});
    }
    return {selected: assets.length, changing: rows.length, touched, fields, rows};
}
