/**
 * The notices of a BRIM parse, counted and split by severity (B-51).
 *
 * A plugin's notice is a **note** when its severity is `info` (blue: the plugin explains a choice it made) and a
 * **warning** otherwise (amber: something needs the user's attention) — the rule of `BrimNoticeList`. The surfaces of
 * the wizard's analysis step read it here: the results column, the stats tile, the parse detail and the confirmation.
 * Until B-51 the column and the tile counted every notice as a warning, so a Fineco file whose only notice is a note
 * showed «⚠️ 1».
 */
import type {CustomCell} from '$lib/components/table/types';
import NoticeCounts from '$lib/features/transactions/import/NoticeCounts.svelte';

export type NoticeSeverity = 'info' | 'warning';

/** How many warnings and how many notes. A type, not an interface: it is a table cell's props. */
export type NoticeTally = {warnings: number; notes: number};

type SeverityCarrier = {severity?: string | null};

/** The severity a notice is read with: exactly `info` is a note, any other severity — or none — a warning. */
export function noticeSeverity(notice: SeverityCarrier): NoticeSeverity {
    return notice.severity === 'info' ? 'info' : 'warning';
}

/** The warnings and the notes of a list; an absent list has none. */
export function noticeCounts(notices: readonly SeverityCarrier[] | null | undefined): NoticeTally {
    const {warnings, notes} = splitNotices(notices);
    return {warnings: warnings.length, notes: notes.length};
}

/** The warnings and the notes: the same objects, each list in its original order. */
export function splitNotices<N extends SeverityCarrier>(notices: readonly N[] | null | undefined): {warnings: N[]; notes: N[]} {
    const warnings: N[] = [];
    const notes: N[] = [];
    for (const notice of notices ?? []) (noticeSeverity(notice) === 'info' ? notes : warnings).push(notice);
    return {warnings, notes};
}

/**
 * The results column's sort key: the warnings first, the notes breaking the ties. `notes / (notes + 1)` stays below 1,
 * so one more warning outranks any number of notes. An unparsed row has no key (`null`): the table sorts it last.
 */
export function noticeSortValue(notices: readonly SeverityCarrier[] | null | undefined): number | null {
    if (notices == null) return null;
    const {warnings, notes} = noticeCounts(notices);
    return warnings + notes / (notes + 1);
}

/** The results column's cell: the two counts, or a dash while the row has no parse. */
export function noticeCountsCell(notices: readonly SeverityCarrier[] | null | undefined): CustomCell | '—' {
    if (notices == null) return '—';
    return {type: 'custom', component: NoticeCounts, props: noticeCounts(notices)};
}
