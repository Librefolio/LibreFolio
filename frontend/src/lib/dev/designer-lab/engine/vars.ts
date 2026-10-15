/**
 * Designer Lab — L1: CSS custom properties defined for the whole page (Tailwind's `--color-*` in `@layer theme`,
 * `--theme-*`, the brand, future `--lf-*` roles), overridden on `<html>` with `!important`.
 *
 * An important declaration beats every normal one, layered or not, so the override wins without touching the rules
 * that define the variable; everything that reads the variable follows, `color-mix()` transparencies included.
 * Variables defined inside a component are scoped to its elements and are rewritten by the stylesheet engine instead.
 */

import type {LabChange} from '../types';
import {isSafeCssValue} from './targets';

export const OWN_ATTR = 'data-lf-lab-own';
const STYLE_ID = 'lf-designer-lab-vars';

const SELECTOR = {both: 'html', light: 'html:not(.dark)', dark: 'html.dark'} as const;

/** Write the overrides of every `css-var` change (all themes: the selectors keep them apart). Returns how many. */
export function applyVars(changes: LabChange[]): number {
    const rules = changes.filter((c) => /^--[\w-]+$/.test(c.target) && isSafeCssValue(c.to)).map((c) => `${SELECTOR[c.scope]} { ${c.target}: ${c.to} !important; }`);
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
