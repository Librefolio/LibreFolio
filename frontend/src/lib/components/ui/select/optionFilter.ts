/**
 * Search filtering for the select family, section titles included.
 *
 * Extracted from `SearchSelect.svelte` because the interesting rule is not the matching — that
 * part is a substring test — but what happens to a **section title whose section the search just
 * emptied**. Left in, it stands over nothing and claims a category the list no longer has; and it
 * is invisible in the common case, so it is exactly the kind of defect that ships.
 *
 * @module components/ui/select/optionFilter
 */

import type {SelectOption} from './types';

/** True when the query appears anywhere the option offers for matching. */
function matches(option: SelectOption, query: string, rawQuery: string): boolean {
    return option.value.toLowerCase().includes(query) || option.label.toLowerCase().includes(query) || (!!option.searchText && option.searchText.toLowerCase().includes(query)) || iconMatches(option.icon, rawQuery);
}

/**
 * An icon is searchable only when it *is* the symbol — a flag emoji the user can paste into the
 * box. A URL or a file path is a resource locator: its characters are ours, not the user's, and
 * matching them meant a short query matched everything (`s` is in every `.svg`, `o` in every
 * `/icons/…`), which reads as a search that only starts working from the fourth letter.
 */
function iconMatches(icon: string | undefined, rawQuery: string): boolean {
    if (!icon || icon.includes('/') || icon.includes('.')) return false;
    return icon.includes(rawQuery);
}

/**
 * The options a query leaves standing, with orphaned section titles removed.
 *
 * Titles never match a query themselves — they are furniture, not content — so they are kept
 * unconditionally in the first pass and dropped in the second when nothing followed them. An
 * empty section leaves one of exactly two shapes behind: two titles in a row, or a title last.
 */
export function filterOptions(options: readonly SelectOption[], rawQuery: string): SelectOption[] {
    const query = rawQuery.trim().toLowerCase();
    const kept = query === '' ? [...options] : options.filter((o) => o.header || matches(o, query, rawQuery));
    return kept.filter((o, i) => !o.header || (kept[i + 1] !== undefined && !kept[i + 1].header));
}

/** True when the user can land on this row: a title and a disabled row are both pass-through. */
export function isSelectable(option: SelectOption | undefined): boolean {
    return option !== undefined && !option.header && !option.disabled;
}

/** Index of the first row the user can land on, or -1 when the list holds none. */
export function firstSelectable(options: readonly SelectOption[]): number {
    return options.findIndex((o) => isSelectable(o));
}

/**
 * The next selectable index in `dir`, or `from` when there is none.
 *
 * Staying put at the end of the list is deliberate: wrapping around would move the highlight to
 * the opposite end of a dropdown the user cannot see all of, which reads as a glitch.
 */
export function stepSelectable(options: readonly SelectOption[], from: number, dir: 1 | -1): number {
    for (let i = from + dir; i >= 0 && i < options.length; i += dir) {
        if (isSelectable(options[i])) return i;
    }
    return from;
}
