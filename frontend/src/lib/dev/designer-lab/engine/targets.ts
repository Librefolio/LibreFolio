/**
 * Designer Lab — the colour a change writes, in the form each consumer accepts.
 *
 * Stylesheets take any CSS colour, so a target keeps the text the designer typed (OKLCH stays OKLCH). Canvas
 * libraries need concrete sRGB, so chart targets are resolved and clamped. A translucent occurrence keeps its alpha.
 */

import {clampToSrgb, formatOklch, inSrgbGamut, rgbaToOklch, type Rgba} from '../color.js';
import {baseVar, joinTransparentMix, parseTransparentMix, resolveValue} from '../colorValue';

export interface Target {
    /** The CSS text of the target, as typed (`oklch(…)`, `#…`, `var(--…)`, `color-mix(in …, <base> p%, transparent)`). */
    css: string;
    /** The resolved colour, when it can be resolved (a `var()` is read from the page). */
    rgba: Rgba | null;
}

/** Characters a colour never contains: refusing them keeps a typo from breaking out of a style rule. */
const UNSAFE = /[;{}<>"'`\\]|\/\*/;

export function isSafeCssValue(value: string): boolean {
    return value.length > 0 && value.length <= 200 && !UNSAFE.test(value);
}

/** A selector the Lab may write into a rule: one line, no block, comment or tag delimiter (escapes like `\:` are fine). */
export function isSafeSelector(selector: string): boolean {
    return typeof selector === 'string' && selector.length > 0 && selector.length <= 600 && !/[{};<]|\/\*|[\r\n]/.test(selector);
}

export function resolveTarget(to: string): Target | null {
    const css = to.trim();
    if (!isSafeCssValue(css)) return null;
    const lookup = (name: string) => (typeof document === 'undefined' ? '' : getComputedStyle(document.documentElement).getPropertyValue(name).trim());
    const rgba = resolveValue(css, lookup);
    // A value that names a variable stays valid CSS when the page cannot resolve it now: the stylesheets still take it.
    if (baseVar(css)) return {css, rgba};
    return rgba ? {css, rgba} : null;
}

const round = (v: number, digits: number) => Math.round(v * 10 ** digits) / 10 ** digits;

/** The target as a CSS value, carrying the alpha of the occurrence it replaces. */
export function cssWithAlpha(target: Target, alpha: number): string {
    if (alpha >= 0.9995) return target.css;
    // A translucent mix takes the occurrence's alpha into its share: its base stays live, a `var()` still one.
    const mix = parseTransparentMix(target.css);
    if (mix) return joinTransparentMix({...mix, percent: round(mix.percent * alpha, 2)});
    if (target.rgba && !target.css.startsWith('var(')) {
        const a = round(target.rgba.alpha * alpha, 4);
        if (inSrgbGamut(target.rgba)) {
            const c = clampToSrgb(target.rgba);
            return `rgba(${Math.round(c.r * 255)}, ${Math.round(c.g * 255)}, ${Math.round(c.b * 255)}, ${a})`;
        }
        return formatOklch({...rgbaToOklch(target.rgba), alpha: a});
    }
    return `color-mix(in srgb, ${target.css} ${round(alpha * 100, 2)}%, transparent)`;
}

/**
 * The target as a canvas colour: sRGB `rgba()` with a four-decimal alpha. The fixed form is deliberate: no colour the
 * app writes looks like it, so the chart engine can tell its own output from the app's when it reads an option back
 * (the chart engine may add decimals, to give two different originals two spellings of one colour).
 */
export function canvasString(target: Target, alpha: number): string | null {
    if (!target.rgba) return null;
    const c = clampToSrgb(target.rgba);
    const a = Math.min(1, Math.max(0, target.rgba.alpha * alpha));
    return `rgba(${Math.round(c.r * 255)}, ${Math.round(c.g * 255)}, ${Math.round(c.b * 255)}, ${a.toFixed(4)})`;
}
