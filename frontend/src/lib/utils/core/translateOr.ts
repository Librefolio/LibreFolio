/**
 * translateOr — an i18n lookup that never shows the user a raw key.
 *
 * svelte-i18n's `$_(key)` returns the key itself when no message is registered
 * for the active locale, so a missing translation surfaces as literal
 * `brokers.lots.someKey` in the UI. Several chart and table components therefore
 * carried the exact same private helper (`tr`, `translatedOr`, `label`, …): take
 * a key, and if it did not resolve, show a plain-text fallback instead.
 *
 * Centralising it removes the risk the copies diverge — a real hazard, because a
 * divergence only shows up in whichever language happens to lack that one key.
 *
 * The translator is passed in rather than imported: `$_` is a component-level
 * reactive subscription (it re-resolves when the locale changes), and reading it
 * at the call site keeps that subscription where Svelte can see it. Passing the
 * function also makes this a pure, trivially testable unit.
 *
 * A translation is treated as "missing" when it is empty **or** equal to the key
 * — the guarded behaviour the callers relied on. Note this differs from the
 * un-guarded `translated === key ? fallback : translated` variant found
 * elsewhere, which returns an empty string when a key maps to `""`.
 */
export type Translate = (key: string) => string;

export function translateOr(translate: Translate, key: string, fallback: string): string {
    const translated = translate(key);
    return !translated || translated === key ? fallback : translated;
}
