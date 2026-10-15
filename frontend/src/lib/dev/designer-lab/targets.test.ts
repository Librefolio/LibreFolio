// @vitest-environment jsdom
/**
 * Designer Lab — the target of a change (`engine/targets.ts`) when it is a translucent mix,
 * `color-mix(in <space>, <base> p%, transparent)`: the form of the role tokens that carry an opacity.
 *
 * `resolveTarget` reads a variable on `<html>` through `getComputedStyle`. jsdom answers the custom properties set on
 * `<html>` (asserted below, so that a resolved target cannot be an accident) without substituting a `var()` inside
 * them, so a chain goes back through the lookup once per variable. A value whose colour comes from a variable stays a
 * target when the page cannot resolve it — the stylesheets still take it as written; a mix that names no variable and
 * does not resolve is no target at all, and neither is one CSS cannot read (a space it does not know), variable or not.
 *
 * Over a translucent occurrence the stylesheet form (`cssWithAlpha`) of a mix is one mix again, its share multiplied by
 * the occurrence's alpha: the base stays as written, so a role it names stays live, resolved or not. The canvas form
 * (`canvasString`) is concrete sRGB, the resolved alpha times the occurrence's.
 *
 * The role names are the real ones (`--lf-selected` is a tint of `--lf-focus`); their values are made up by the test,
 * and nothing reads `tokens.css`. `#0f1412` is (15, 20, 18), `#2a6f5b` is (42, 111, 91).
 */

import {afterEach, describe, expect, it} from 'vitest';
import type {Rgba} from './color.js';
import {canvasString, cssWithAlpha, resolveTarget, type Target} from './engine/targets';

const MIX = 'color-mix(in oklab, #0f1412 60%, transparent)';
/** A quarter of the base, written `transparent` first. */
const CLEAR_FIRST = 'color-mix(in srgb, transparent 75%, rgb(10, 20, 30))';
/** The form of `--lf-selected`: a tint of the focus role. */
const FOCUS_MIX = 'color-mix(in oklab, var(--lf-focus) 12%, transparent)';
const UNDEFINED_MIX = 'color-mix(in oklab, var(--lf-test-undefined) 40%, transparent)';

const html = () => document.documentElement;

afterEach(() => {
    html().removeAttribute('style');
});

/** A value that must be a target: the test fails here, with the value, rather than on a null later. */
function target(to: string): Target {
    const t = resolveTarget(to);
    if (!t) throw new Error(`not a target: ${to}`);
    return t;
}

/** Channel by channel, to six decimals, against 8-bit channels written by hand. */
function expectRgba(actual: Rgba | null, [r, g, b, alpha]: [number, number, number, number], label: string): void {
    expect(actual, `${label}: not resolved`).not.toBeNull();
    const rgba = actual as Rgba;
    expect(rgba.r, `${label} r`).toBeCloseTo(r / 255, 6);
    expect(rgba.g, `${label} g`).toBeCloseTo(g / 255, 6);
    expect(rgba.b, `${label} b`).toBeCloseTo(b / 255, 6);
    expect(rgba.alpha, `${label} alpha`).toBeCloseTo(alpha, 6);
}

/** Define the focus role on `<html>`, and prove the page answers it. */
function defineFocus(): void {
    html().style.setProperty('--lf-focus', '#2a6f5b');
    expect(getComputedStyle(html()).getPropertyValue('--lf-focus').trim()).toBe('#2a6f5b');
}

describe('resolveTarget — a translucent mix', () => {
    it('resolves a mix of a literal to the literal, its share as the alpha, and keeps the text as typed', () => {
        const t = target(`  ${MIX}  `);
        expect(t.css).toBe(MIX);
        expectRgba(t.rgba, [15, 20, 18, 0.6], 'a mix of a literal');
    });

    it('reads the variable of a mix on <html>, also when another variable holds the mix', () => {
        defineFocus();
        const t = target(FOCUS_MIX);
        expect(t.css).toBe(FOCUS_MIX);
        expectRgba(t.rgba, [42, 111, 91, 0.12], 'a mix of a variable');

        html().style.setProperty('--lf-selected', FOCUS_MIX);
        const held = target('var(--lf-selected)');
        expect(held.css).toBe('var(--lf-selected)');
        expectRgba(held.rgba, [42, 111, 91, 0.12], 'a variable holding the mix');
    });

    it('keeps a value whose variable the page cannot resolve as a target, unresolved', () => {
        expect(resolveTarget(UNDEFINED_MIX)).toEqual({css: UNDEFINED_MIX, rgba: null});
        expect(resolveTarget('var(--lf-test-undefined)')).toEqual({css: 'var(--lf-test-undefined)', rgba: null});
        // Defined, but not as a colour.
        html().style.setProperty('--lf-test-word', 'nonsense');
        const word = 'color-mix(in oklab, var(--lf-test-word) 40%, transparent)';
        expect(resolveTarget(word)).toEqual({css: word, rgba: null});
    });

    it.each([
        ['a base that is not a colour', 'color-mix(in oklab, nonsense 40%, transparent)'],
        ['percentages that do not add up to 100', 'color-mix(in oklab, #0f1412 60%, transparent 60%)'],
        ['no transparent side', 'color-mix(in oklab, #0f1412 50%, #ffffff)'],
        ['a variable with a fallback as the base', 'color-mix(in oklab, var(--lf-focus, #0f1412) 40%, transparent)'],
        ['a space CSS does not know', 'color-mix(in oklabb, #0f1412 60%, transparent)'],
        ['a hue method on a rectangular space', 'color-mix(in srgb longer hue, #0f1412 60%, transparent)'],
        ['a variable base, in a space CSS does not know', 'color-mix(in foo, var(--lf-focus) 12%, transparent)'],
        ['a second declaration after the mix', `${MIX}; color: red`],
    ])('refuses a mix with %s', (_label, to) => {
        defineFocus();
        expect(resolveTarget(to)).toBeNull();
    });
});

describe('cssWithAlpha — a mix target', () => {
    it('writes the mix as typed over an opaque occurrence, the role it names included', () => {
        expect(cssWithAlpha(target(MIX), 1)).toBe(MIX);
        expect(cssWithAlpha(target(MIX), 0.9995)).toBe(MIX);
        expect(cssWithAlpha(target(CLEAR_FIRST), 1)).toBe(CLEAR_FIRST);
        defineFocus();
        expect(cssWithAlpha(target(FOCUS_MIX), 1)).toBe(FOCUS_MIX);
        expect(cssWithAlpha(target(UNDEFINED_MIX), 1)).toBe(UNDEFINED_MIX);
    });

    it('multiplies the share by the alpha of a translucent occurrence: one mix, in its own space, base first', () => {
        expect(cssWithAlpha(target(MIX), 0.5)).toBe('color-mix(in oklab, #0f1412 30%, transparent)');
        expect(cssWithAlpha(target(MIX), 0)).toBe('color-mix(in oklab, #0f1412 0%, transparent)');
        expect(cssWithAlpha(target(CLEAR_FIRST), 0.5)).toBe('color-mix(in srgb, rgb(10, 20, 30) 12.5%, transparent)');
        expect(cssWithAlpha(target('color-mix(in oklch longer hue, oklch(62% 0.13 160) 40%, transparent)'), 0.5)).toBe('color-mix(in oklch longer hue, oklch(62% 0.13 160) 20%, transparent)');
        // To two decimals: 60% × 0.12345 is 7.407%.
        expect(cssWithAlpha(target(MIX), 0.12345)).toBe('color-mix(in oklab, #0f1412 7.41%, transparent)');
    });

    it('keeps the role a mix names live over a translucent occurrence, resolved or not', () => {
        defineFocus();
        expect(cssWithAlpha(target(FOCUS_MIX), 0.5)).toBe('color-mix(in oklab, var(--lf-focus) 6%, transparent)');
        expect(cssWithAlpha(target(UNDEFINED_MIX), 0.5)).toBe('color-mix(in oklab, var(--lf-test-undefined) 20%, transparent)');
        // A bare variable is no mix: it is wrapped in one of its own, at the occurrence alpha.
        expect(cssWithAlpha(target('var(--lf-focus)'), 0.5)).toBe('color-mix(in srgb, var(--lf-focus) 50%, transparent)');
    });

    it('writes a mix whose colour is the target’s at the product of the two alphas, a translucent base included', () => {
        defineFocus();
        for (const css of [MIX, CLEAR_FIRST, FOCUS_MIX, 'color-mix(in srgb, rgb(10 20 30 / 50%) 40%, transparent)']) {
            const t = target(css);
            expect(t.rgba, `${css}: not resolved`).not.toBeNull();
            const {r, g, b, alpha} = t.rgba as Rgba;
            for (const occurrence of [0.5, 0.25, 0.1]) {
                const out = cssWithAlpha(t, occurrence);
                expectRgba(target(out).rgba, [r * 255, g * 255, b * 255, alpha * occurrence], `${css} at ${occurrence}: ${out}`);
            }
        }
    });
});

describe('canvasString — a mix target', () => {
    it('writes sRGB rgba() with four alpha decimals: the share times the occurrence alpha', () => {
        expect(canvasString(target(MIX), 1)).toBe('rgba(15, 20, 18, 0.6000)');
        expect(canvasString(target(MIX), 0.5)).toBe('rgba(15, 20, 18, 0.3000)');
        defineFocus();
        expect(canvasString(target(FOCUS_MIX), 1)).toBe('rgba(42, 111, 91, 0.1200)');
        // A canvas cannot read a variable: where the stylesheets keep the role live, it gets the colour itself.
        expect(canvasString(target(FOCUS_MIX), 0.5)).toBe('rgba(42, 111, 91, 0.0600)');
    });

    it('has no canvas colour for a mix it cannot resolve', () => {
        expect(canvasString(target(UNDEFINED_MIX), 1)).toBeNull();
    });
});
