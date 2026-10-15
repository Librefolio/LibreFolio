/**
 * Designer Lab — colour values with an opacity (`colorValue.ts`): what the editor's A slider reads and writes.
 *
 * The role tokens that carry an opacity are written `color-mix(in <space>, <base> p%, transparent)` — the backdrop, the
 * shadow roles, the selected tint over the focus role — and the slider changes that percentage in place, so a role named
 * in the base survives the edit. A mix is read only in an interpolation space of CSS Color 5, and a hue method only on a
 * polar one: anything else is a value the browser would drop. A bare `var()` becomes such a mix; a literal takes the
 * alpha in its own notation; every form rounds the opacity to a tenth of a percent, and an opacity that is no finite
 * number changes nothing. The colour controls (`withBase`) change the colour and keep the opacity — except over a fully
 * transparent literal, which holds no colour to keep it for: the new colour comes in opaque.
 *
 * Every colour and variable below is made up by the test: nothing reads `tokens.css`, whose role values workstream T is
 * changing. Texts are compared exactly where the module defines them; resolved colours channel by channel, with a
 * tolerance, against byte values written by hand (`#0f1412` is 15, 20, 18; `#2a6f5b` is 42, 111, 91).
 */

import {describe, expect, it} from 'vitest';
import {inSrgbGamut, parseColor, type Rgba} from './color.js';
import {baseVar, joinTransparentMix, parseTransparentMix, resolveValue, valueOpacity, withBase, withOpacity} from './colorValue';

/** A translucent backdrop: the base at 60%. */
const MIX = 'color-mix(in oklab, #0f1412 60%, transparent)';
/** A tint of a role: the variable at 12%. */
const VAR_MIX = 'color-mix(in oklab, var(--focus) 12%, transparent)';

/** A colour from 8-bit channels and an alpha in 0–1. */
const rgb = (r: number, g: number, b: number, alpha = 1): Rgba => ({r: r / 255, g: g / 255, b: b / 255, alpha});

/** Channel by channel, to `digits` decimals (6 by default: far below one 8-bit step, 0.0039). */
function expectColor(actual: Rgba | null, expected: Rgba, label: string, digits = 6): void {
    expect(actual, `${label}: not resolved`).not.toBeNull();
    const rgba = actual as Rgba;
    expect(rgba.r, `${label} r`).toBeCloseTo(expected.r, digits);
    expect(rgba.g, `${label} g`).toBeCloseTo(expected.g, digits);
    expect(rgba.b, `${label} b`).toBeCloseTo(expected.b, digits);
    expect(rgba.alpha, `${label} alpha`).toBeCloseTo(expected.alpha, digits);
}

/** A page whose variables are `vars`, as `getComputedStyle(…).getPropertyValue()` answers: '' for an unknown one. */
function page(vars: Record<string, string>): (name: string) => string {
    return (name) => vars[name] ?? '';
}

/** Values whose opacity the module cannot edit: not a colour, or a form it does not read. */
const UNREADABLE: [string, string][] = [
    ['a word that is no colour', 'nonsense'],
    ['nothing', ''],
    ['a variable with a fallback', 'var(--focus, #0f1412)'],
    ['a mix whose percentages do not add up to 100', 'color-mix(in oklab, #0f1412 60%, transparent 60%)'],
    ['a mix of two colours', 'color-mix(in oklab, #0f1412 50%, #ffffff)'],
    ['a mix in a space CSS does not know', 'color-mix(in oklabb, #0f1412 60%, transparent)'],
];

/** The interpolation spaces of CSS Color 5, written out by the test: only the polar ones take a hue method. */
const RECTANGULAR = ['srgb', 'srgb-linear', 'display-p3', 'a98-rgb', 'prophoto-rgb', 'rec2020', 'lab', 'oklab', 'xyz', 'xyz-d50', 'xyz-d65'];
const POLAR = ['hsl', 'hwb', 'lch', 'oklch'];
const HUE_METHODS = ['shorter', 'longer', 'increasing', 'decreasing'];

describe('parseTransparentMix', () => {
    it('reads the base, its share and the space, with the percentage after or before its colour', () => {
        const expected = {space: 'oklab', base: '#0f1412', percent: 60};
        expect(parseTransparentMix(MIX)).toEqual(expected);
        expect(parseTransparentMix('color-mix(in oklab, 60% #0f1412, transparent)')).toEqual(expected);
    });

    it('takes `transparent` on either side, and keeps the base as it is written', () => {
        expect(parseTransparentMix('color-mix(in oklab, transparent, #0f1412 60%)')).toEqual({space: 'oklab', base: '#0f1412', percent: 60});
        expect(parseTransparentMix('color-mix(in srgb, transparent 75%, rgb(10, 20, 30))')).toEqual({space: 'srgb', base: 'rgb(10, 20, 30)', percent: 25});
        expect(parseTransparentMix('color-mix(in oklab, 40% transparent, 60% #0F1412)')).toEqual({space: 'oklab', base: '#0F1412', percent: 60});
    });

    it('gives the base the share CSS gives it: its own percentage, else 100 minus transparent’s, else half', () => {
        const share = (text: string) => parseTransparentMix(text)?.percent;
        expect(share('color-mix(in oklab, #0f1412 30%, transparent 70%)')).toBe(30);
        expect(share('color-mix(in oklab, #0f1412, transparent 70%)')).toBe(30);
        expect(share('color-mix(in oklab, transparent 70%, #0f1412)')).toBe(30);
        expect(share('color-mix(in oklab, #0f1412, transparent)')).toBe(50);
        expect(share('color-mix(in oklab, #0f1412 12.5%, transparent)')).toBe(12.5);
        expect(share('color-mix(in oklab, #0f1412, transparent 87.5%)')).toBe(12.5);
        expect(share('color-mix(in oklab, #0f1412 0%, transparent)')).toBe(0);
        expect(share('color-mix(in oklab, #0f1412 100%, transparent)')).toBe(100);
    });

    it('ignores case in the function name, the space and `transparent`, and writes the space in lower case with single spaces', () => {
        expect(parseTransparentMix('COLOR-MIX(IN OKLAB, #0f1412 60%, TRANSPARENT)')).toEqual({space: 'oklab', base: '#0f1412', percent: 60});
        expect(parseTransparentMix('color-mix(in OKLCH Longer Hue, #0f1412 60%, transparent)')).toEqual({space: 'oklch longer hue', base: '#0f1412', percent: 60});
        expect(parseTransparentMix('  color-mix(  in   OKLCH   Longer   Hue ,  #0f1412   60% ,  Transparent  )  ')).toEqual({space: 'oklch longer hue', base: '#0f1412', percent: 60});
        expect(parseTransparentMix('color-mix(in Display-P3, #0f1412 60%, transparent)')).toEqual({space: 'display-p3', base: '#0f1412', percent: 60});
    });

    it.each([...RECTANGULAR, ...POLAR])('reads a mix in the space %s', (space) => {
        expect(parseTransparentMix(`color-mix(in ${space}, #0f1412 60%, transparent)`)).toEqual({space, base: '#0f1412', percent: 60});
    });

    it('keeps a hue interpolation method on each polar space', () => {
        for (const space of POLAR) {
            for (const method of HUE_METHODS) {
                expect(parseTransparentMix(`color-mix(in ${space} ${method} hue, oklch(62% 0.13 160) 40%, transparent)`), `${space} ${method}`).toEqual({space: `${space} ${method} hue`, base: 'oklch(62% 0.13 160)', percent: 40});
            }
        }
    });

    it('refuses a hue method on each rectangular space', () => {
        for (const space of RECTANGULAR) {
            for (const method of HUE_METHODS) expect(parseTransparentMix(`color-mix(in ${space} ${method} hue, #0f1412 60%, transparent)`), `${space} ${method}`).toBeNull();
        }
    });

    it('reads a base with commas and parentheses of its own, and never takes a percentage inside it for the share', () => {
        expect(parseTransparentMix('color-mix(in srgb, rgba(10, 20, 30, 0.5) 40%, transparent)')).toEqual({space: 'srgb', base: 'rgba(10, 20, 30, 0.5)', percent: 40});
        expect(parseTransparentMix('color-mix(in srgb, hsl(120, 50%, 40%) 25%, transparent)')).toEqual({space: 'srgb', base: 'hsl(120, 50%, 40%)', percent: 25});
        expect(parseTransparentMix('color-mix(in srgb, rgb(10 20 30 / 50%), transparent)')).toEqual({space: 'srgb', base: 'rgb(10 20 30 / 50%)', percent: 50});
        expect(parseTransparentMix('color-mix(in srgb, 25% rgb(10 20 30 / 50%), transparent)')).toEqual({space: 'srgb', base: 'rgb(10 20 30 / 50%)', percent: 25});
    });

    it('takes a bare `var()` as the base', () => {
        expect(parseTransparentMix(VAR_MIX)).toEqual({space: 'oklab', base: 'var(--focus)', percent: 12});
        expect(parseTransparentMix('color-mix(in oklab, transparent, var( --focus ))')).toEqual({space: 'oklab', base: 'var( --focus )', percent: 50});
    });

    it.each([
        ['percentages that do not add up to 100', 'color-mix(in oklab, #0f1412 60%, transparent 60%)'],
        ['percentages that add up to less than 100', 'color-mix(in oklab, #0f1412 30%, transparent 30%)'],
        ['a share above 100%', 'color-mix(in oklab, #0f1412 150%, transparent)'],
        ['a transparent share above 100%', 'color-mix(in oklab, #0f1412, transparent 150%)'],
        ['two transparent sides', 'color-mix(in oklab, transparent 50%, transparent)'],
        ['two transparent sides in upper case', 'color-mix(in oklab, TRANSPARENT, transparent 50%)'],
        ['no transparent side', 'color-mix(in oklab, #0f1412 50%, #ffffff)'],
        ['a variable with a fallback as the base', 'color-mix(in oklab, var(--focus, #0f1412) 50%, transparent)'],
        ['a base that is not a colour', 'color-mix(in oklab, nonsense 50%, transparent)'],
        ['another mix as the base', `color-mix(in oklab, ${MIX} 50%, transparent)`],
        ['no `in` before the space', 'color-mix(oklab, #0f1412 50%, transparent)'],
        ['no space at all', 'color-mix(#0f1412 50%, transparent)'],
        ['a space CSS does not know', 'color-mix(in foo, #0f1412 50%, transparent)'],
        ['a misspelt space', 'color-mix(in oklabb, #0f1412 50%, transparent)'],
        ['a colour function for a space', 'color-mix(in rgb, #0f1412 50%, transparent)'],
        ['a hue method on a rectangular space', 'color-mix(in srgb longer hue, #0f1412 50%, transparent)'],
        ['a hue method without `hue`', 'color-mix(in oklch longer, #0f1412 50%, transparent)'],
        ['`hue` without a method', 'color-mix(in oklch hue, #0f1412 50%, transparent)'],
        ['two arguments', 'color-mix(in oklab, #0f1412 60%)'],
        ['four arguments', 'color-mix(in oklab, #0f1412 60%, transparent, #ffffff)'],
        ['an empty argument', 'color-mix(in oklab, , transparent)'],
        ['unbalanced parentheses', 'color-mix(in oklab, rgb(10, 20, 30 60%, transparent)'],
        ['text after the call', `${MIX} 50%`],
        ['a colour literal', '#0f1412'],
        ['a bare variable', 'var(--focus)'],
        ['nothing', ''],
    ])('refuses %s', (_label, text) => {
        expect(parseTransparentMix(text)).toBeNull();
    });
});

describe('joinTransparentMix', () => {
    it('writes the base first, its percentage after it, `transparent` last', () => {
        expect(joinTransparentMix({space: 'srgb', base: 'rgb(10, 20, 30)', percent: 25})).toBe('color-mix(in srgb, rgb(10, 20, 30) 25%, transparent)');
        expect(joinTransparentMix({space: 'oklch longer hue', base: 'var(--focus)', percent: 12})).toBe('color-mix(in oklch longer hue, var(--focus) 12%, transparent)');
    });

    it('rounds the percentage to two decimals and writes no trailing zero', () => {
        const at = (percent: number) => joinTransparentMix({space: 'oklab', base: '#0f1412', percent});
        expect(at(12.3456)).toBe('color-mix(in oklab, #0f1412 12.35%, transparent)');
        expect(at(33.333333)).toBe('color-mix(in oklab, #0f1412 33.33%, transparent)');
        expect(at(50.5)).toBe('color-mix(in oklab, #0f1412 50.5%, transparent)');
        expect(at(25.1)).toBe('color-mix(in oklab, #0f1412 25.1%, transparent)');
        expect(at(60)).toBe('color-mix(in oklab, #0f1412 60%, transparent)');
        expect(at(0)).toBe('color-mix(in oklab, #0f1412 0%, transparent)');
    });

    it('writes what parseTransparentMix reads back', () => {
        const mixes = [
            {space: 'oklab', base: '#0f1412', percent: 60},
            {space: 'srgb', base: 'rgb(10, 20, 30)', percent: 12.5},
            {space: 'oklch longer hue', base: 'var(--focus)', percent: 0},
        ];
        for (const mix of mixes) expect(parseTransparentMix(joinTransparentMix(mix))).toEqual(mix);
    });
});

describe('resolveValue', () => {
    const none = page({});

    it('resolves a literal, and a mix as its base with the alpha scaled by the share', () => {
        expectColor(resolveValue('#0f1412', none), rgb(15, 20, 18), 'a literal');
        expectColor(resolveValue(MIX, none), rgb(15, 20, 18, 0.6), 'a mix at 60%');
        expectColor(resolveValue('color-mix(in srgb, transparent 75%, rgb(10, 20, 30))', none), rgb(10, 20, 30, 0.25), 'transparent first');
        // A translucent base: the two alphas multiply.
        expectColor(resolveValue('color-mix(in srgb, rgb(10 20 30 / 50%) 40%, transparent)', none), rgb(10, 20, 30, 0.2), 'a translucent base');
    });

    it('reads a `var()` through the lookup, which may answer a literal, another variable or a mix', () => {
        const vars = page({
            '--brand': '#2a6f5b',
            '--focus': 'var(--brand)',
            '--overlay': MIX,
            '--selected': VAR_MIX,
            '--shade': '#00000080',
        });
        expectColor(resolveValue('var(--brand)', vars), rgb(42, 111, 91), 'a literal');
        expectColor(resolveValue('  var( --brand )  ', vars), rgb(42, 111, 91), 'spaces inside and around');
        expectColor(resolveValue('var(--focus)', vars), rgb(42, 111, 91), 'another variable');
        expectColor(resolveValue('var(--overlay)', vars), rgb(15, 20, 18, 0.6), 'a mix');
        expectColor(resolveValue(VAR_MIX, vars), rgb(42, 111, 91, 0.12), 'a mix of a variable');
        // var → mix → var → var → literal: the depth of a tint over a role that aliases another.
        expectColor(resolveValue('var(--selected)', vars), rgb(42, 111, 91, 0.12), 'a variable holding a mix of a variable');
        expectColor(resolveValue('color-mix(in oklab, var(--shade) 50%, transparent)', vars), rgb(0, 0, 0, (128 / 255) * 0.5), 'a mix of a translucent variable');
    });

    it('follows at most four references', () => {
        /** `--v1` → `--v2` → … → `--v<hops>` = a literal. */
        const chain = (hops: number) => {
            const vars: Record<string, string> = {};
            for (let i = 1; i < hops; i++) vars[`--v${i}`] = `var(--v${i + 1})`;
            vars[`--v${hops}`] = '#2a6f5b';
            return page(vars);
        };
        expectColor(resolveValue('var(--v1)', chain(4)), rgb(42, 111, 91), 'four references');
        expect(resolveValue('var(--v1)', chain(5))).toBeNull();
    });

    it('gives up on a variable that refers to itself, after a few reads and without overflowing the stack', () => {
        const cycles: Record<string, string> = {
            '--loop': 'var(--loop)',
            '--ping': 'var(--pong)',
            '--pong': 'var(--ping)',
            '--tint': 'color-mix(in oklab, var(--tint) 50%, transparent)',
        };
        for (const name of Object.keys(cycles)) {
            const asked: string[] = [];
            const lookup = (n: string) => {
                asked.push(n);
                return cycles[n] ?? '';
            };
            expect(resolveValue(`var(${name})`, lookup), name).toBeNull();
            expect(asked.length, `${name}: reads`).toBeLessThan(10);
        }
    });

    it('resolves nothing it cannot read: an unknown variable, or what is not a colour', () => {
        expect(resolveValue('var(--unknown)', none)).toBeNull();
        expect(resolveValue('color-mix(in oklab, var(--unknown) 40%, transparent)', none)).toBeNull();
        // The fallback form is not read, even when the variable is defined.
        expect(resolveValue('var(--brand, #2a6f5b)', page({'--brand': '#2a6f5b'}))).toBeNull();
        for (const [label, text] of UNREADABLE) expect(resolveValue(text, none), label).toBeNull();
    });
});

describe('valueOpacity', () => {
    it('is the share of a mix, 1 for a `var()`, the alpha of a literal', () => {
        expect(valueOpacity(MIX)).toBe(0.6);
        expect(valueOpacity('color-mix(in oklab, transparent 87.5%, var(--focus))')).toBe(0.125);
        expect(valueOpacity('var(--focus)')).toBe(1);
        expect(valueOpacity('#64748b')).toBe(1);
        expect(valueOpacity('  #64748b  ')).toBe(1);
        expect(valueOpacity('#64748b80')).toBeCloseTo(128 / 255, 9);
        expect(valueOpacity('oklch(62% 0.13 160 / 0.5)')).toBe(0.5);
        expect(valueOpacity('rgba(10, 20, 30, 0.25)')).toBe(0.25);
        expect(valueOpacity('transparent')).toBe(0);
    });

    it.each(UNREADABLE)('is null for %s', (_label, text) => {
        expect(valueOpacity(text)).toBeNull();
    });
});

describe('withOpacity', () => {
    it('changes the share of a mix in place, keeping its base, its space and the role it names', () => {
        expect(withOpacity(MIX, 0.25)).toBe('color-mix(in oklab, #0f1412 25%, transparent)');
        expect(withOpacity(MIX, 0)).toBe('color-mix(in oklab, #0f1412 0%, transparent)');
        expect(withOpacity(VAR_MIX, 0.3)).toBe('color-mix(in oklab, var(--focus) 30%, transparent)');
        expect(withOpacity('color-mix(in oklch longer hue, oklch(62% 0.13 160) 40%, transparent)', 0.5)).toBe('color-mix(in oklch longer hue, oklch(62% 0.13 160) 50%, transparent)');
        // Written back in the canonical order: the base first, `transparent` last.
        expect(withOpacity('color-mix(in srgb, transparent 75%, rgb(10, 20, 30))', 0.5)).toBe('color-mix(in srgb, rgb(10, 20, 30) 50%, transparent)');
    });

    it('gives back the bare base of a mix at 100%', () => {
        expect(withOpacity(MIX, 1)).toBe('#0f1412');
        expect(withOpacity(VAR_MIX, 1)).toBe('var(--focus)');
    });

    it('turns a `var()` into a mix in oklab, and leaves it as it is at 100%', () => {
        expect(withOpacity('var(--focus)', 0.25)).toBe('color-mix(in oklab, var(--focus) 25%, transparent)');
        expect(withOpacity('  var(--focus)  ', 0.5)).toBe('color-mix(in oklab, var(--focus) 50%, transparent)');
        expect(withOpacity('var(--focus)', 1)).toBe('var(--focus)');
    });

    it('clamps the opacity to 0–1', () => {
        expect(withOpacity(MIX, -1)).toBe('color-mix(in oklab, #0f1412 0%, transparent)');
        expect(withOpacity(MIX, 2)).toBe('#0f1412');
        expect(withOpacity('var(--focus)', -1)).toBe('color-mix(in oklab, var(--focus) 0%, transparent)');
        expect(withOpacity('var(--focus)', 2)).toBe('var(--focus)');
        expect(withOpacity('#64748b', -1)).toBe('#64748b00');
        expect(withOpacity('#64748b80', 2)).toBe('#64748b');
    });

    it('is null for an opacity that is not a finite number, whatever the value', () => {
        for (const opacity of [NaN, Infinity, -Infinity]) {
            for (const value of [MIX, VAR_MIX, 'var(--focus)', '#64748b', 'oklch(62% 0.13 160 / 0.5)', 'transparent']) expect(withOpacity(value, opacity), `${value} at ${opacity}`).toBeNull();
        }
    });

    it('rounds the share to a tenth of a percent, so that just under 100% is the bare base', () => {
        const focusAt = (opacity: number) => withOpacity('var(--focus)', opacity);
        expect(focusAt(0.12349)).toBe('color-mix(in oklab, var(--focus) 12.3%, transparent)');
        expect(focusAt(0.1236)).toBe('color-mix(in oklab, var(--focus) 12.4%, transparent)');
        expect(focusAt(0.999)).toBe('color-mix(in oklab, var(--focus) 99.9%, transparent)');
        expect(focusAt(0.9996)).toBe('var(--focus)');
        expect(withOpacity(MIX, 0.9996)).toBe('#0f1412');
        expect(withOpacity(MIX, 0.0004)).toBe('color-mix(in oklab, #0f1412 0%, transparent)');
    });

    it('rounds a literal’s alpha to a tenth of a percent too: just under 100% is opaque, with no `ff` byte and no `/ 1`', () => {
        expect(withOpacity('#64748b', 0.9996)).toBe('#64748b');
        expect(withOpacity('#64748b80', 0.9996)).toBe('#64748b');
        expect(withOpacity('#64748b', 0.0004)).toBe('#64748b00');
        expect(withOpacity('oklch(62% 0.13 160)', 0.9996)).toBe('oklch(62% 0.13 160)');
        expect(withOpacity('oklch(62% 0.13 160 / 0.5)', 0.9996)).toBe('oklch(62% 0.13 160)');
        expect(withOpacity('oklch(62% 0.13 160)', 0.0004)).toBe('oklch(62% 0.13 160 / 0)');
        expect(withOpacity('oklch(62% 0.13 160)', 0.12349)).toBe('oklch(62% 0.13 160 / 0.123)');
        expect(withOpacity('color(display-p3 1 0 0)', 0.9996)).toMatch(/^oklch\([\d.]+% [\d.]+ [\d.]+\)$/);
    });

    it('writes a hex or functional sRGB literal as `#rrggbbaa`, and `#rrggbb` when opaque', () => {
        expect(withOpacity('#64748b', 0.25)).toBe('#64748b40');
        expect(withOpacity('#64748b', 0.5)).toBe('#64748b80');
        expect(withOpacity('  #64748b  ', 0.25)).toBe('#64748b40');
        expect(withOpacity('#64748b80', 1)).toBe('#64748b');
        expect(withOpacity('#64748b80', 0)).toBe('#64748b00');
        expect(withOpacity('rgb(10, 20, 30)', 0.5)).toBe('#0a141e80');
    });

    it('keeps an OKLCH literal in OKLCH, with `/ alpha` unless opaque', () => {
        expect(withOpacity('oklch(62% 0.13 160 / 0.5)', 0.25)).toBe('oklch(62% 0.13 160 / 0.25)');
        expect(withOpacity('oklch(62% 0.13 160)', 0.5)).toBe('oklch(62% 0.13 160 / 0.5)');
        expect(withOpacity('OKLCH(62% 0.13 160)', 0.5)).toBe('oklch(62% 0.13 160 / 0.5)');
        expect(withOpacity('oklch(62% 0.13 160 / 0.5)', 1)).toBe('oklch(62% 0.13 160)');
    });

    it('writes a colour outside sRGB in OKLCH with its alpha, never clamped into hex', () => {
        const p3Red = 'color(display-p3 1 0 0)';
        const out = withOpacity(p3Red, 0.5);
        expect(out).toMatch(/^oklch\([\d.]+% [\d.]+ [\d.]+ \/ 0\.5\)$/);
        const back = parseColor(out ?? '');
        expect(back && inSrgbGamut(back), 'still outside sRGB').toBe(false);
        // OKLCH written to 2, 4 and 2 decimals: the channels come back to within a few 1e-5.
        expectColor(back, {...(parseColor(p3Red) as Rgba), alpha: 0.5}, 'display-p3 red at 50%', 3);
    });

    it('gives `transparent`, black at no opacity, the alpha as hex', () => {
        expect(withOpacity('transparent', 0.5)).toBe('#00000080');
        expect(withOpacity('transparent', 0)).toBe('#00000000');
        expect(withOpacity('transparent', 1)).toBe('#000000');
    });

    it.each(UNREADABLE)('is null for %s', (_label, text) => {
        expect(withOpacity(text, 0.5)).toBeNull();
    });
});

describe('withBase', () => {
    it('puts the new base into a mix, keeping its share and its space', () => {
        expect(withBase(MIX, '#ff00aa')).toBe('color-mix(in oklab, #ff00aa 60%, transparent)');
        expect(withBase(MIX, '  #ff00aa  ')).toBe('color-mix(in oklab, #ff00aa 60%, transparent)');
        expect(withBase(MIX, 'var(--accent)')).toBe('color-mix(in oklab, var(--accent) 60%, transparent)');
        expect(withBase(VAR_MIX, 'oklch(70% 0.1 250)')).toBe('color-mix(in oklab, oklch(70% 0.1 250) 12%, transparent)');
        expect(withBase('color-mix(in srgb, transparent 75%, rgb(10, 20, 30))', '#ff00aa')).toBe('color-mix(in srgb, #ff00aa 25%, transparent)');
    });

    it('gives the base the alpha of a translucent literal, a `var()` base as a mix', () => {
        expect(withBase('#64748b80', '#ff00aa')).toBe('#ff00aa80');
        expect(withBase('rgba(10, 20, 30, 0.25)', '#ff00aa')).toBe('#ff00aa40');
        expect(withBase('oklch(62% 0.13 160 / 0.5)', 'oklch(70% 0.1 250)')).toBe('oklch(70% 0.1 250 / 0.5)');
        // 0x80 is 128/255: 50.2% once rounded to a tenth.
        expect(withBase('#64748b80', 'var(--x)')).toBe('color-mix(in oklab, var(--x) 50.2%, transparent)');
    });

    it('gives back the base itself over an opaque literal, a `var()`, or a value it cannot read', () => {
        expect(withBase('#64748b', '#ff00aa')).toBe('#ff00aa');
        expect(withBase('oklch(62% 0.13 160)', 'var(--accent)')).toBe('var(--accent)');
        expect(withBase('var(--focus)', '#ff00aa')).toBe('#ff00aa');
        expect(withBase('var(--focus)', 'var(--accent)')).toBe('var(--accent)');
        expect(withBase('nonsense', '#ff00aa')).toBe('#ff00aa');
        expect(withBase('color-mix(in oklabb, #0f1412 60%, transparent)', '#ff00aa')).toBe('#ff00aa');
        expect(withBase('', '  var(--accent)  ')).toBe('var(--accent)');
    });

    it('gives the new colour opaque over a fully transparent literal, which holds no colour to keep the opacity of', () => {
        expect(withBase('transparent', '#ff00aa')).toBe('#ff00aa');
        expect(withBase('#64748b00', '#ff00aa')).toBe('#ff00aa');
        expect(withBase('rgba(10, 20, 30, 0)', 'oklch(70% 0.1 250)')).toBe('oklch(70% 0.1 250)');
        expect(withBase('oklch(62% 0.13 160 / 0)', '  var(--accent)  ')).toBe('var(--accent)');
    });

    it('keeps a mix at 0%, whose share only the A slider sets', () => {
        expect(withBase('color-mix(in oklab, #0f1412 0%, transparent)', '#ff00aa')).toBe('color-mix(in oklab, #ff00aa 0%, transparent)');
        expect(withBase('color-mix(in oklab, #0f1412, transparent 100%)', '#ff00aa')).toBe('color-mix(in oklab, #ff00aa 0%, transparent)');
        expect(withBase('color-mix(in oklab, var(--focus) 0%, transparent)', 'var(--accent)')).toBe('color-mix(in oklab, var(--accent) 0%, transparent)');
    });

    it('keeps the opacity whatever the new base, a mix at 0% included, except over a fully transparent literal: the contract the colour controls rely on', () => {
        const kept = [MIX, VAR_MIX, 'color-mix(in oklab, #0f1412 0%, transparent)', '#64748b80', 'oklch(62% 0.13 160 / 0.5)', 'rgba(10, 20, 30, 0.25)', '#64748b', 'var(--focus)'];
        const clear = ['transparent', '#64748b00', 'oklch(62% 0.13 160 / 0)'];
        const bases = ['#ff00aa', 'oklch(70% 0.1 250)', 'var(--accent)'];
        for (const base of bases) {
            for (const value of kept) {
                const out = withBase(value, base);
                // A hex alpha is one byte (1/255): within that, the opacity is the one the value had.
                expect(valueOpacity(out), `${value} with ${base}: ${out}`).toBeCloseTo(valueOpacity(value) as number, 2);
            }
            // Nothing to keep: the base comes in as it is, opaque.
            for (const value of clear) expect(withBase(value, base), `${value} with ${base}`).toBe(base);
        }
    });
});

describe('baseVar', () => {
    it('names the variable of a `var()`, or of the base of a mix', () => {
        expect(baseVar('var(--focus)')).toBe('--focus');
        expect(baseVar('  var( --focus )  ')).toBe('--focus');
        expect(baseVar(VAR_MIX)).toBe('--focus');
        expect(baseVar('color-mix(in srgb, transparent 88%, var(--focus))')).toBe('--focus');
    });

    it.each([
        ['a literal', '#0f1412'],
        ['a mix of a literal', MIX],
        ['a variable with a fallback', 'var(--focus, #0f1412)'],
        ['a mix of a variable with a fallback', 'color-mix(in oklab, var(--focus, #0f1412) 12%, transparent)'],
        ['a mix of a variable in a space CSS does not know', 'color-mix(in foo, var(--focus) 12%, transparent)'],
        ['a word that is no colour', 'nonsense'],
        ['nothing', ''],
    ])('is null for %s', (_label, text) => {
        expect(baseVar(text)).toBeNull();
    });
});
