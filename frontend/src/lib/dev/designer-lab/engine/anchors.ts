/**
 * Designer Lab — specialisations (`element` changes): one colour property of the picked element, set in every
 * instance of its component, without touching the shared source.
 *
 * The rules live in the cascade layer `lf-designer-lab`, declared before any other layer by a statement prepended to
 * `<head>`. Among `!important` declarations the first layer wins over the later layers (Tailwind's `!` utilities)
 * and over the unlayered ones (the P1 overrides of `app.css`), so the preview shows whatever the app writes; only an
 * inline `!important` style would stay on top. The statement and the rules are removed when no specialisation is left.
 */

import {ELEMENT_PROPERTIES} from '../cssProps';
import type {LabChange} from '../types';
import {isSafeCssValue, isSafeSelector} from './targets';
import {OWN_ATTR} from './vars';

export const LAB_LAYER = 'lf-designer-lab';
export const ELEMENT_STYLE_ID = 'lf-designer-lab-elements';
const ORDER_STYLE_ID = 'lf-designer-lab-layer-order';

const THEME_PREFIX = {both: 'html', light: 'html:not(.dark)', dark: 'html.dark'} as const;

/** Whether the browser accepts the selector (an invalid one would silently match nothing). */
function parses(selector: string): boolean {
    try {
        document.createDocumentFragment().querySelector(selector);
        return true;
    } catch {
        return false;
    }
}

/** The CSS rule a specialisation writes, or null when it cannot be written safely. */
export function elementRule(change: LabChange): string | null {
    const property = change.property ?? '';
    if (change.layer !== 'element' || property === 'chart' || !ELEMENT_PROPERTIES.includes(property)) return null;
    if (!isSafeSelector(change.target) || !isSafeCssValue(change.to)) return null;
    return `${THEME_PREFIX[change.scope]} :is(${change.target}) { ${property}: ${change.to} !important; }`;
}

/** Write the rules of every CSS specialisation (all themes: the prefixes keep them apart). Returns how many. */
export function applyElementRules(changes: LabChange[]): number {
    const rules = changes
        .filter((c) => parses(c.target))
        .map(elementRule)
        .filter((r): r is string => r !== null);
    let style = document.getElementById(ELEMENT_STYLE_ID);
    if (!rules.length) {
        style?.remove();
        document.getElementById(ORDER_STYLE_ID)?.remove();
        return 0;
    }
    if (!document.getElementById(ORDER_STYLE_ID)) {
        const order = document.createElement('style');
        order.id = ORDER_STYLE_ID;
        order.setAttribute(OWN_ATTR, '');
        order.textContent = `@layer ${LAB_LAYER};`;
        document.head.prepend(order);
    }
    if (!style) {
        style = document.createElement('style');
        style.id = ELEMENT_STYLE_ID;
        style.setAttribute(OWN_ATTR, '');
        document.head.appendChild(style);
    }
    style.textContent = `@layer ${LAB_LAYER} {\n${rules.join('\n')}\n}`;
    return rules.length;
}
