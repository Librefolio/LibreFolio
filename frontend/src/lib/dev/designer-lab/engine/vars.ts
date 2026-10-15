/**
 * Designer Lab — L1: CSS custom properties defined for the whole page (Tailwind's `--color-*` in `@layer theme`,
 * `--theme-*`, the brand, the `--lf-*` roles of workstream T), overridden with `!important`.
 *
 * An important declaration beats every normal one, layered or not, so the override wins without touching the rules
 * that define the variable; everything that reads the variable follows, `color-mix()` transparencies included. The
 * override goes on `<html>` and on the theme subtrees the role tokens are built for (`.light`, `.dark`): an element
 * forced into a theme redefines the roles itself, and would otherwise keep its own value.
 * Variables defined inside a component are scoped to its elements and are rewritten by the stylesheet engine instead.
 */

import type {LabChange} from '../types';
import {isSafeCssValue} from './targets';

export const OWN_ATTR = 'data-lf-lab-own';
const STYLE_ID = 'lf-designer-lab-vars';

/** Where each scope writes its overrides: the selectors of the token blocks of `lib/theme/tokens.css`. */
export const VAR_SELECTOR = {both: 'html, .light, .dark', light: 'html:not(.dark), .light', dark: 'html.dark, .dark'} as const;

/**
 * On a theme island, `.dark` gives a `dark` rule the specificity of a `both` rule: written after it, the theme's own
 * value wins there too, as it does on `<html>` (`html.dark` beats `.dark`).
 */
const SCOPE_ORDER = {both: 0, light: 1, dark: 1} as const;

/** Write the overrides of every `css-var` change (all themes: the selectors keep them apart). Returns how many. */
export function applyVars(changes: LabChange[]): number {
    const rules = changes
        .filter((c) => /^--[\w-]+$/.test(c.target) && isSafeCssValue(c.to))
        .sort((a, b) => SCOPE_ORDER[a.scope] - SCOPE_ORDER[b.scope])
        .map((c) => `${VAR_SELECTOR[c.scope]} { ${c.target}: ${c.to} !important; }`);
    let el = document.getElementById(STYLE_ID);
    if (!rules.length) {
        el?.remove();
        return 0;
    }
    if (!el) {
        el = document.createElement('style');
        el.id = STYLE_ID;
        el.setAttribute(OWN_ATTR, '');
        document.head.appendChild(el);
    }
    el.textContent = rules.join('\n');
    return rules.length;
}
