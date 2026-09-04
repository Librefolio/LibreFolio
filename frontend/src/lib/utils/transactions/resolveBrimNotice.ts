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
