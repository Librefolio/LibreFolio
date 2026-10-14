/**
 * Types of the two-level `TreeSelect` (see `TreeSelect.svelte`).
 *
 * Kept in a plain module so that data builders — `utils/assetTypes.ts`, the signals panel — can
 * describe a tree without importing a component.
 *
 * @module components/ui/select/treeSelect
 */

/** A selectable row. `searchText` is matched as given, so callers pass it lower-cased. */
export interface TreeSelectItem {
    value: string;
    searchText: string;
}

/** A family of rows. Groups themselves are never selectable. */
export interface TreeSelectGroup<T extends TreeSelectItem = TreeSelectItem> {
    key: string;
    label: string;
    subtitle: string;
    items: T[];
    /** Render the items at the root: no group row, always visible, nothing to open or close. */
    inline?: boolean;
    /** Optional picture for a custom `groupLabel` snippet; the default group row ignores it. */
    icon?: string;
}
