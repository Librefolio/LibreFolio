/**
 * The locale every figure is written in: the interface language.
 *
 * One rule for numbers, amounts, percentages and dates (M-18, decision of the developer, 2026-10-12):
 * the interface language decides how a figure is written, so a percentage never sits next to an
 * amount written another way. The browser contributes only its region, and only when its primary
 * language is the interface language: an English interface on an `en-GB` browser stays British, on
 * an `en-US` browser American, and an Italian one on `it-CH` keeps the Swiss decimal point. Any
 * other combination — a browser in another language, or one naming no region (`en`) — takes the
 * language's own default: `en-GB` for English (12/10/2026, 12 Oct 2026, 14:05), the bare language
 * for Italian, French and Spanish.
 *
 * Only `navigator.language`, the primary tag, is read. Browsers list `en-US` among the secondary
 * languages of most users, so reading the list would give an Italian who chose English American
 * dates.
 *
 * The value comes in two forms:
 * - `uiLocale()`, for runes code and as the default of every formatter: read in a template, a
 *   `$derived` or an `$effect` — even inside a helper — it is tracked, so a language switch
 *   re-renders the figure in place.
 * - `uiLocaleStore`, for legacy components (`export let`), which must read it in the template
 *   expression itself (`locale: $uiLocaleStore`): there a read inside a helper compiles into an
 *   untracked one (devWiki `problems/legacy-component-language-untracked`).
 */
import {derived, fromStore} from 'svelte/store';
import {currentLanguage} from './language';
import {resolveUiLocale} from './uiLocaleRule';

// The rule lives in a module that imports nothing, so the E2E specs can import it too.
export {resolveUiLocale};

function browserPrimaryTag(): string | undefined {
    return typeof navigator === 'undefined' ? undefined : navigator.language;
}

/** The interface locale as a store, for legacy components: read it as `$uiLocaleStore` in the template. */
export const uiLocaleStore = derived(currentLanguage, (language) => resolveUiLocale(language, browserPrimaryTag()));

const tracked = fromStore(uiLocaleStore);

/** The interface locale, tracked wherever runes code reads it; the default of every figure formatter. */
export function uiLocale(): string {
    return tracked.current;
}
