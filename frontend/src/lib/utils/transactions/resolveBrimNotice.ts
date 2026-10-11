/**
 * Localisation of BRIM parser notices.
 *
 * A BRIM plugin runs backend-side and has no access to the user's locale, so
 * `BRIMNotice.message` is always a raw string in the plugin author's language.
 * Every notice however carries a stable `code` plus a `context` dict, which is
 * enough to look up a translated wording — exactly the same trick already used
 * for validation issues (`resolveIssueMessage`).
 *
 * Contract:
 *   - key    `importWizard.brimNotice.<code>`
 *   - values `notice.context` (so `{n}`, `{row_count}`, … interpolate)
 *   - miss   → fall back to the plugin's own `message`, never to the raw code.
 *   - the comment under an evidence table follows the same contract with
 *     `importWizard.brimEvidence.<code>` (`resolveBrimEvidenceComment`).
 *
 * Only notices worth polishing need a key; everything else keeps working.
 */
import type {BrimNotice} from '$lib/types';

type TranslateFn = (key: string, opts?: {values?: Record<string, any>}) => string;

export function resolveBrimNoticeMessage(notice: BrimNotice, t: TranslateFn): string {
    const code = notice.code;
    if (!code) return notice.message;

    const values: Record<string, any> = {...(notice.context ?? {})};
    // `n` is the conventional count placeholder across the i18n catalogue.
    if (values.n === undefined && typeof values.row_count === 'number') values.n = values.row_count;

    const key = `importWizard.brimNotice.${code}`;
    const translated = t(key, {values});
    return translated === key ? notice.message : translated;
}

/**
 * Localisation of the comment under a notice's evidence table, on the notices' contract: the key
 * `importWizard.brimEvidence.<code>` (with `notice.context` as values) replaces the plugin's own
 * comment when it exists. Without a key, or without a comment, the plugin's text is kept as written.
 * Generic over the comment's type: the generated client types an optional string with an impossible
 * array branch, so anything but a non-empty string is handed back untouched.
 */
export function resolveBrimEvidenceComment<C>(notice: BrimNotice, comment: C, t: TranslateFn): C | string {
    if (typeof comment !== 'string' || !comment || !notice.code) return comment;
    const key = `importWizard.brimEvidence.${notice.code}`;
    const translated = t(key, {values: {...(notice.context ?? {})}});
    return translated === key ? comment : translated;
}

/** What the wording of a BRIM field todo depends on: `ImportTodo` fits, and so does the raw schema once mapped. */
export interface BrimTodoText {
    reasonCode: string;
    message: string;
    context?: Record<string, unknown> | null;
}

/**
 * Localisation of BRIM field todos, on the notices' contract: a todo carries a stable
 * `reason_code`, so `importWizard.brimNotice.<reasonCode>` (with `context` as values)
 * replaces the plugin's wording in the UI language when that key exists. Without a key
 * the plugin's own message is shown as written — the language of the parsed file —
 * never the raw code. Every surface that lists todos goes through here.
 */
export function resolveBrimTodoMessage(todo: BrimTodoText, t: TranslateFn): string {
    if (!todo.reasonCode) return todo.message;
    const key = `importWizard.brimNotice.${todo.reasonCode}`;
    const translated = t(key, {values: {...(todo.context ?? {})}});
    return translated === key ? todo.message : translated;
}
