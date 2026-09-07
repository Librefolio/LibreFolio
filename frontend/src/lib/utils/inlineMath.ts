import katex from 'katex';
import 'katex/dist/katex.min.css';

/**
 * Deliberately *not* `$lib/utils/core/escapeHtml`, and deliberately one
 * substitution short of it: the apostrophe must survive.
 *
 * This escape runs *before* `renderInlineMath`, so whatever it produces is what
 * KaTeX is asked to typeset. KaTeX reads `f'(x)` as prime notation; hand it
 * `f&#39;(x)` and it renders the entity as literal text, so every derivative in
 * a signal subtitle breaks. Swapping this for the shared version is therefore a
 * visible regression, not a hardening — keep the two apart.
 */
export function escapeHtml(value: string): string {
    return value.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

export function renderInlineMath(content: string): string {
    return content.replace(/\$([^$]+)\$/g, (_, formula: string) => {
        try {
            return katex.renderToString(formula, {throwOnError: false, displayMode: false});
        } catch {
            return formula;
        }
    });
}

export function renderInlineMathText(text: string): string {
    return renderInlineMath(escapeHtml(text));
}
