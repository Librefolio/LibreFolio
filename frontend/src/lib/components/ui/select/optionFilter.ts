/**
 * Search filtering for the select family, section titles included.
 *
 * Extracted from `SearchSelect.svelte` because the interesting rules are not the matching — that
 * part is a substring test — but what happens to a **section title whose section the search just
 * emptied**, and **which match comes first**. A title left standing over nothing claims a category
 * the list no longer has; and it is invisible in the common case, so it is exactly the kind of
 * defect that ships.
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

/** Letters and digits of any script: a word starts after anything else — space, `_`, `-`, `/`, `.`, `(`. */
const WORD_CHARACTER = /[\p{L}\p{N}]/u;

/** Rank of a match that reached the option only through `searchText` or its icon. */
const RANK_ELSEWHERE = 3;

/** 0 = the field starts with the query, 1 = a word inside it does, 2 = it contains it, 3 = it does not. */
function fieldRank(field: string, query: string): number {
    const text = field.toLowerCase();
    let at = text.indexOf(query);
    if (at === -1) return RANK_ELSEWHERE;
    if (at === 0) return 0;
    // Every occurrence counts, not only the first: in "Xcsv then csv" the second one starts a word.
    while (at !== -1) {
        if (!WORD_CHARACTER.test(text[at - 1])) return 1;
        at = text.indexOf(query, at + 1);
    }
    return 2;
}

/**
 * How well an option matched: the better of what its value and its label say.
 *
 * The description is deliberately the weakest evidence. Descriptions share vocabulary — every one
 * of the 30 import plugins mentions CSV in its description, and 29 of them match "CSV" through
 * nothing else — so that query used to return the whole list in source order, and "CSV" buried
 * "Generic CSV" sixteenth, under the fold, with the highlight (the row Enter picks) on the first
 * plugin in the list (R13).
 */
function matchRank(option: SelectOption, query: string): number {
    return Math.min(fieldRank(option.value, query), fieldRank(option.label, query));
}

/**
 * Order every run of rows between two titles by match rank, stably. Titles never move, so a row
 * never leaves its section: the sections are structure the caller decided (contract K3 puts the
 * benchmarks first), the ranking only orders what is inside them.
 */
function rankWithinSections(options: SelectOption[], query: string): SelectOption[] {
    const out: SelectOption[] = [];
    let run: SelectOption[] = [];
    const flush = () => {
        const ranked = run.map((option, index) => ({option, index, rank: matchRank(option, query)}));
        ranked.sort((a, b) => a.rank - b.rank || a.index - b.index);
        for (const entry of ranked) out.push(entry.option);
        run = [];
    };
    for (const option of options) {
        if (option.header) {
            flush();
            out.push(option);
        } else {
            run.push(option);
        }
    }
    flush();
    return out;
}

/**
 * The options a query leaves standing, best match first, with orphaned section titles removed.
 *
 * Titles never match a query themselves — they are furniture, not content — so they are kept
 * unconditionally in the first pass and dropped in the second when nothing followed them. An
 * empty section leaves one of exactly two shapes behind: two titles in a row, or a title last.
 *
 * Only the order depends on how a row matched, never the set: whatever contains the query in its
 * value, label, `searchText` or emoji icon still survives. An empty query keeps the source order.
 * The caller's array is never reordered in place.
 */
export function filterOptions(options: readonly SelectOption[], rawQuery: string): SelectOption[] {
    const query = rawQuery.trim().toLowerCase();
    const kept = query === '' ? [...options] : options.filter((o) => o.header || matches(o, query, rawQuery));
    const standing = kept.filter((o, i) => !o.header || (kept[i + 1] !== undefined && !kept[i + 1].header));
    return query === '' ? standing : rankWithinSections(standing, query);
}

/** True when the user can land on this row: a title and a disabled row are both pass-through. */
export function isSelectable(option: SelectOption | undefined): boolean {
    return option !== undefined && !option.header && !option.disabled;
}

/** Index of the first row the user can land on, or -1 when the list holds none. */
export function firstSelectable(options: readonly SelectOption[]): number {
    return options.findIndex((o) => isSelectable(o));
}

/** Index of the last row the user can land on, or -1 when the list holds none. */
export function lastSelectable(options: readonly SelectOption[]): number {
    for (let i = options.length - 1; i >= 0; i--) {
        if (isSelectable(options[i])) return i;
    }
    return -1;
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
