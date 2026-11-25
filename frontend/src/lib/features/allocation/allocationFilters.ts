/**
 * The filters of the «Allocazione» tab (lane 80, issue #89): what the user keeps in the selection and what leaves the 100 %.
 *
 * Pure: no store, no network, no component. The backend does every calculation (`POST /portfolio/allocation`); these
 * are the user's choices, how they are remembered per page, and how they read as chips.
 *
 * - `classes`: `null` = every class (the first opening: the whole portfolio); a list = those classes; `[]` = none.
 * - `types`: asset types kept on their own, beside `classes`: a class kept in part is not in `classes`, its kept types are here
 *   (86, D-13). A whole class takes every type it holds, today's and the ones to come. Nothing with `classes` null.
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
    /** Asset types kept on their own (the classes kept in part). */
    types: string[];
    excludeBuckets: ExcludableBucket[];
    excludeAssetIds: number[];
}

/** The first opening: the whole portfolio, nothing excluded. */
export const NO_FILTERS: AllocationFilters = Object.freeze({classes: null, types: [], excludeBuckets: [], excludeAssetIds: []}) as AllocationFilters;

export function emptyFilters(): AllocationFilters {
    return {classes: null, types: [], excludeBuckets: [], excludeAssetIds: []};
}

const EXCLUDABLE: readonly string[] = ['Unknown', 'Other'];

// ---------------------------------------------------------------------------
// Memory per page
// ---------------------------------------------------------------------------

/** The user key under which a page remembers its filters: `allocation-filters:dashboard` or `allocation-filters:broker:<id>`. */
export function filtersStorageKey(scope: {kind: 'portfolio'} | {kind: 'broker'; brokerId: number}): string {
    return scope.kind === 'broker' ? `allocation-filters:broker:${scope.brokerId}` : 'allocation-filters:dashboard';
}

/** What is stored: the four fields, nothing else. */
export function serializeFilters(filters: AllocationFilters): string {
    return JSON.stringify({classes: filters.classes, types: filters.types, excludeBuckets: filters.excludeBuckets, excludeAssetIds: filters.excludeAssetIds});
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
        const names = (item: unknown): item is string => typeof item === 'string' && item.length > 0 && item.length <= 64;
        const classes = Array.isArray(record.classes) && record.classes.every(names) ? uniq(record.classes as string[]).slice(0, 64) : null;
        // Absent in what a version before the two levels stored: no class was kept in part.
        const types = classes !== null && Array.isArray(record.types) ? uniq(record.types.filter(names)).slice(0, 64) : [];
        const excludeBuckets = Array.isArray(record.excludeBuckets) ? (uniq(record.excludeBuckets.filter((item): item is ExcludableBucket => typeof item === 'string' && EXCLUDABLE.includes(item))) as ExcludableBucket[]) : [];
        const excludeAssetIds = Array.isArray(record.excludeAssetIds) ? uniq(record.excludeAssetIds.filter((item): item is number => typeof item === 'number' && Number.isInteger(item))).slice(0, 1000) : [];
        return {classes, types, excludeBuckets, excludeAssetIds};
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

/** A class the scope holds, and the types that make it up today (the cash has none). */
export interface PresentClass {
    asset_class: string;
    types: ReadonlyArray<{asset_type: string}>;
}

/** How much of a set of choices is on. */
export type ChoiceState = 'on' | 'off' | 'mixed';

export function choiceState(on: number, total: number): ChoiceState {
    return on === 0 ? 'off' : on === total ? 'on' : 'mixed';
}

/** True when the whole class is in the selection. */
export function isClassOn(filters: AllocationFilters, assetClass: string): boolean {
    return filters.classes === null || filters.classes.includes(assetClass);
}

/** True when the type is in the selection: its whole class is, or it is kept on its own. */
export function isTypeOn(filters: AllocationFilters, assetClass: string, assetType: string): boolean {
    return isClassOn(filters, assetClass) || filters.types.includes(assetType);
}

/** Whether a class is kept whole, in part or not at all. */
export function classState(filters: AllocationFilters, item: PresentClass): ChoiceState {
    if (isClassOn(filters, item.asset_class)) return 'on';
    return choiceState(item.types.filter((type) => filters.types.includes(type.asset_type)).length, Math.max(1, item.types.length));
}

const typeNames = (item: PresentClass): string[] => item.types.map((type) => type.asset_type);

/** The same choices; «every class» (`null`) when every present class is whole and nothing saved is left over. */
function withClasses(filters: AllocationFilters, classes: string[], types: string[], present: readonly PresentClass[]): AllocationFilters {
    const names = present.map((item) => item.asset_class);
    const every = names.length > 0 && names.every((item) => classes.includes(item)) && classes.every((item) => names.includes(item)) && types.length === 0;
    return {...filters, classes: every ? null : classes, types: every ? [] : types};
}

/** Turns one class on or off, whole: the types kept on their own in it are gone. */
export function setClass(filters: AllocationFilters, assetClass: string, on: boolean, present: readonly PresentClass[]): AllocationFilters {
    const current = classesOn(
        filters,
        present.map((item) => item.asset_class),
    );
    const own = new Set(present.filter((item) => item.asset_class === assetClass).flatMap(typeNames));
    const types = filters.types.filter((type) => !own.has(type));
    return withClasses(filters, on ? uniq([...current, assetClass]) : current.filter((item) => item !== assetClass), types, present);
}

/** Turns one type of a class on or off: every type on is the whole class again, some leave the class and stay on their own. */
export function setType(filters: AllocationFilters, assetClass: string, assetType: string, on: boolean, present: readonly PresentClass[]): AllocationFilters {
    const item = present.find((candidate) => candidate.asset_class === assetClass);
    const all = item ? typeNames(item) : [assetType];
    const kept = all.filter((type) => (type === assetType ? on : isTypeOn(filters, assetClass, type)));
    if (kept.length === all.length) return setClass(filters, assetClass, true, present);
    const classes = classesOn(
        filters,
        present.map((candidate) => candidate.asset_class),
    ).filter((candidate) => candidate !== assetClass);
    return withClasses(filters, classes, uniq([...filters.types.filter((type) => !all.includes(type)), ...kept]), present);
}

/** Every class whole, or none. */
export function setEveryClass(filters: AllocationFilters, on: boolean): AllocationFilters {
    return {...filters, classes: on ? null : [], types: []};
}

/** Takes one class out of a chip: the last choice gone is «every class» again, never an empty selection. */
export function removeClassChip(filters: AllocationFilters, assetClass: string): AllocationFilters {
    if (filters.classes === null) return filters;
    const next = filters.classes.filter((item) => item !== assetClass);
    return {...filters, classes: next.length === 0 && filters.types.length === 0 ? null : next};
}

/** Takes one type out of a chip, as `removeClassChip`. */
export function removeTypeChip(filters: AllocationFilters, assetType: string): AllocationFilters {
    const types = filters.types.filter((item) => item !== assetType);
    return {...filters, types, classes: types.length === 0 && filters.classes?.length === 0 ? null : filters.classes};
}

/** A click on a class of the matrix: the selection becomes that class alone; on the class that is already alone, every class again. */
export function focusClass(filters: AllocationFilters, assetClass: string): AllocationFilters {
    const alone = filters.classes !== null && filters.classes.length === 1 && filters.classes[0] === assetClass && filters.types.length === 0;
    return {...filters, classes: alone ? null : [assetClass], types: []};
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

export type AllocationChip = {kind: 'class'; value: string} | {kind: 'type'; value: string} | {kind: 'bucket'; value: ExcludableBucket} | {kind: 'asset'; value: number};

/** One chip per choice, in the order the panels list them: classes kept, types kept on their own, buckets out, assets out. The filter button's number is their count. */
export function filterChips(filters: AllocationFilters): AllocationChip[] {
    return [
        ...(filters.classes ?? []).map((value): AllocationChip => ({kind: 'class', value})),
        ...filters.types.map((value): AllocationChip => ({kind: 'type', value})),
        ...filters.excludeBuckets.map((value): AllocationChip => ({kind: 'bucket', value})),
        ...filters.excludeAssetIds.map((value): AllocationChip => ({kind: 'asset', value})),
    ];
}

export function removeChip(filters: AllocationFilters, chip: AllocationChip): AllocationFilters {
    if (chip.kind === 'class') return removeClassChip(filters, chip.value);
    if (chip.kind === 'type') return removeTypeChip(filters, chip.value);
    if (chip.kind === 'bucket') return setBucketExcluded(filters, chip.value, false);
    return setAssetExcluded(filters, chip.value, false);
}

/** Same choices (the controller's «did anything change» test). */
export function sameFilters(left: AllocationFilters, right: AllocationFilters): boolean {
    return serializeFilters(normalized(left)) === serializeFilters(normalized(right));
}

function normalized(filters: AllocationFilters): AllocationFilters {
    return {classes: filters.classes === null ? null : [...filters.classes].sort(), types: [...filters.types].sort(), excludeBuckets: [...filters.excludeBuckets].sort(), excludeAssetIds: [...filters.excludeAssetIds].sort((a, b) => a - b)};
}
