/**
 * The filters of the «Allocazione» tab (lane 80, issue #89): what the user keeps in the selection and what leaves the 100 %.
 *
 * Pure: no store, no network, no component. The backend does every calculation (`POST /portfolio/allocation`); these
 * are the user's choices, how they are remembered per page, and how they read as chips.
 *
 * - `classes`: `null` = every class (the first opening: the whole portfolio); a list = those classes; `[]` = none.
 * - `excludeBuckets`: the buckets taken out of the 100 % (`Unknown`, `Other`), where the dimension has them.
 * - `excludeAssetIds`: assets taken out whole.
 *
 * What was saved is kept as it was: a class, a bucket or an asset that is not in the scope today stays in the list
 * (it may come back with another period or broker), and the backend ignores what it does not find.
 *
 * @module features/allocation/allocationFilters
 */

export type ExcludableBucket = 'Unknown' | 'Other';

export interface AllocationFilters {
    /** `null`: every class. */
    classes: string[] | null;
    excludeBuckets: ExcludableBucket[];
    excludeAssetIds: number[];
}

/** The first opening: the whole portfolio, nothing excluded. */
export const NO_FILTERS: AllocationFilters = Object.freeze({classes: null, excludeBuckets: [], excludeAssetIds: []}) as AllocationFilters;

export function emptyFilters(): AllocationFilters {
    return {classes: null, excludeBuckets: [], excludeAssetIds: []};
}

const EXCLUDABLE: readonly string[] = ['Unknown', 'Other'];

// ---------------------------------------------------------------------------
// Memory per page
// ---------------------------------------------------------------------------

/** The user key under which a page remembers its filters: `allocation-filters:dashboard` or `allocation-filters:broker:<id>`. */
export function filtersStorageKey(scope: {kind: 'portfolio'} | {kind: 'broker'; brokerId: number}): string {
    return scope.kind === 'broker' ? `allocation-filters:broker:${scope.brokerId}` : 'allocation-filters:dashboard';
}

/** What is stored: the three fields, nothing else. */
export function serializeFilters(filters: AllocationFilters): string {
    return JSON.stringify({classes: filters.classes, excludeBuckets: filters.excludeBuckets, excludeAssetIds: filters.excludeAssetIds});
}

/**
 * Reads what a page stored. Anything that is not of the right shape (a corrupted value, an older layout, a value another
 * version wrote) is the first-opening state: the tab never fails on its memory.
 */
export function parseFilters(raw: string | null | undefined): AllocationFilters {
    if (!raw) return emptyFilters();
    try {
        const value: unknown = JSON.parse(raw);
        if (value === null || typeof value !== 'object' || Array.isArray(value)) return emptyFilters();
        const record = value as Record<string, unknown>;
        const classes = Array.isArray(record.classes) && record.classes.every((item) => typeof item === 'string' && item.length > 0 && item.length <= 64) ? uniq(record.classes as string[]).slice(0, 64) : null;
        const excludeBuckets = Array.isArray(record.excludeBuckets) ? (uniq(record.excludeBuckets.filter((item): item is ExcludableBucket => typeof item === 'string' && EXCLUDABLE.includes(item))) as ExcludableBucket[]) : [];
        const excludeAssetIds = Array.isArray(record.excludeAssetIds) ? uniq(record.excludeAssetIds.filter((item): item is number => typeof item === 'number' && Number.isInteger(item))).slice(0, 1000) : [];
        return {classes, excludeBuckets, excludeAssetIds};
    } catch {
        return emptyFilters();
    }
}

function uniq<T>(items: readonly T[]): T[] {
    return [...new Set(items)];
}

// ---------------------------------------------------------------------------
// Choices
// ---------------------------------------------------------------------------

/** The classes switched on, among the ones the scope holds (`present`); a saved class that is not there stays in the list. */
export function classesOn(filters: AllocationFilters, present: readonly string[]): string[] {
    return filters.classes === null ? [...present] : [...filters.classes];
}

/** True when the class is in the selection. */
export function isClassOn(filters: AllocationFilters, assetClass: string): boolean {
    return filters.classes === null || filters.classes.includes(assetClass);
}

/** Turns one class on or off. Every present class on again is «every class» (`null`) when nothing saved is left over. */
export function setClass(filters: AllocationFilters, assetClass: string, on: boolean, present: readonly string[]): AllocationFilters {
    const current = classesOn(filters, present);
    const next = on ? uniq([...current, assetClass]) : current.filter((item) => item !== assetClass);
    const everyPresent = present.length > 0 && present.every((item) => next.includes(item)) && next.every((item) => present.includes(item));
    return {...filters, classes: everyPresent ? null : next};
}

/** Takes one class out of a chip: the last one gone is «every class» again, never an empty selection. */
export function removeClassChip(filters: AllocationFilters, assetClass: string): AllocationFilters {
    if (filters.classes === null) return filters;
    const next = filters.classes.filter((item) => item !== assetClass);
    return {...filters, classes: next.length === 0 ? null : next};
}

/** A click on a class of the matrix: the selection becomes that class alone; on the class that is already alone, every class again. */
export function focusClass(filters: AllocationFilters, assetClass: string): AllocationFilters {
    const alone = filters.classes !== null && filters.classes.length === 1 && filters.classes[0] === assetClass;
    return {...filters, classes: alone ? null : [assetClass]};
}

export function setBucketExcluded(filters: AllocationFilters, bucket: ExcludableBucket, excluded: boolean): AllocationFilters {
    const rest = filters.excludeBuckets.filter((item) => item !== bucket);
    return {...filters, excludeBuckets: excluded ? [...rest, bucket] : rest};
}

export function setAssetExcluded(filters: AllocationFilters, assetId: number, excluded: boolean): AllocationFilters {
    const rest = filters.excludeAssetIds.filter((item) => item !== assetId);
    return {...filters, excludeAssetIds: excluded ? [...rest, assetId] : rest};
}

/** Several assets at once (the search box's «all»/«none» on the rows it shows). */
export function setAssetsExcluded(filters: AllocationFilters, assetIds: readonly number[], excluded: boolean): AllocationFilters {
    const rest = filters.excludeAssetIds.filter((item) => !assetIds.includes(item));
    return {...filters, excludeAssetIds: excluded ? [...rest, ...assetIds] : rest};
}

/** True when any choice differs from the first opening. */
export function hasFilters(filters: AllocationFilters): boolean {
    return filters.classes !== null || filters.excludeBuckets.length > 0 || filters.excludeAssetIds.length > 0;
}

// ---------------------------------------------------------------------------
// Chips
// ---------------------------------------------------------------------------

export type AllocationChip = {kind: 'class'; value: string} | {kind: 'bucket'; value: ExcludableBucket} | {kind: 'asset'; value: number};

/** One chip per choice, in the order the panels list them: classes kept, buckets out, assets out. The filter button's number is their count. */
export function filterChips(filters: AllocationFilters): AllocationChip[] {
    return [...(filters.classes ?? []).map((value): AllocationChip => ({kind: 'class', value})), ...filters.excludeBuckets.map((value): AllocationChip => ({kind: 'bucket', value})), ...filters.excludeAssetIds.map((value): AllocationChip => ({kind: 'asset', value}))];
}

export function removeChip(filters: AllocationFilters, chip: AllocationChip): AllocationFilters {
    if (chip.kind === 'class') return removeClassChip(filters, chip.value);
    if (chip.kind === 'bucket') return setBucketExcluded(filters, chip.value, false);
    return setAssetExcluded(filters, chip.value, false);
}

/** Same choices (the controller's «did anything change» test). */
export function sameFilters(left: AllocationFilters, right: AllocationFilters): boolean {
    return serializeFilters(normalized(left)) === serializeFilters(normalized(right));
}

function normalized(filters: AllocationFilters): AllocationFilters {
    return {classes: filters.classes === null ? null : [...filters.classes].sort(), excludeBuckets: [...filters.excludeBuckets].sort(), excludeAssetIds: [...filters.excludeAssetIds].sort((a, b) => a - b)};
}
