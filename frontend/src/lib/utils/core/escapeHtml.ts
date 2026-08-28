/**
 * HTML escaping for strings that are interpolated into markup we build by hand.
 *
 * Most of the callers are ECharts tooltip formatters and `CellContent` of type
 * `html`, both of which are rendered as real HTML (`{@html}` for the latter).
 * Anything user- or provider-supplied that reaches them — asset names, broker
 * names, file names, currency codes, icon URLs — has to be escaped first, or a
 * name containing markup becomes markup.
 *
 * This used to be copy-pasted into thirteen places, in two variants that
 * differed on the apostrophe. The single-quote substitution is kept here
 * because it is the one that makes the result safe in a single-quoted
 * attribute too: without it, `title='...'` is an injection point, and whether
 * a given call site quotes with `"` or `'` is not something this function can
 * see. Escaping it costs nothing — the parser decodes `&#39;` back to `'`, so
 * the rendered text, the attribute value and even an inline `onerror` script
 * are byte-identical to the unescaped input.
 *
 * Note for anyone tempted to reuse this before a templating step: `escapeHtml`
 * in `$lib/utils/inlineMath` deliberately does *not* escape the apostrophe,
 * because its output is fed to KaTeX, where `f'(x)` is prime notation. See the
 * comment there before merging the two.
 */
export function escapeHtml(value: string): string {
    return value.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}
