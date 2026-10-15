/**
 * Designer Lab — colour values with an opacity: a literal, `var(--x)`, or the translucent form the role tokens use for
 * shadows and the backdrop, `color-mix(in <space>, <base> <p>%, transparent)`, which is the base at opacity p.
 *
 * Mixing with `transparent` keeps the base colour and scales its alpha, whatever the interpolation space (premultiplied
 * alpha). The editor shows that percentage as the opacity and changes it in place, so a role in the base
 * (`var(--lf-focus)`) survives the edit. Pure: a `var()` is resolved through the lookup the caller passes.
 */

import {formatOklch, inSrgbGamut, parseColor, rgbaToOklch, toHex, type Rgba} from './color.js';

/** `color-mix()` with `transparent`: the base (a colour literal or `var(--x)`), the base's share, the space as written. */
export interface TransparentMix {
    space: string;
    base: string;
    /** The share of the base, 0–100: the opacity the mix gives it. */
    percent: number;
}

const VAR_RE = /^var\(\s*(--[\w-]+)\s*\)$/;
const SPACE_RE = /^in\s+([a-z][a-z0-9-]*)(?:\s+(shorter|longer|increasing|decreasing)\s+hue)?$/i;
/** The interpolation spaces of CSS Color 5; only the polar ones take a hue method. */
const RECTANGULAR_SPACES = new Set(['srgb', 'srgb-linear', 'display-p3', 'a98-rgb', 'prophoto-rgb', 'rec2020', 'lab', 'oklab', 'xyz', 'xyz-d50', 'xyz-d65']);
const POLAR_SPACES = new Set(['hsl', 'hwb', 'lch', 'oklch']);
const MAX_DEPTH = 4;

/** The arguments of a function call, split at the commas outside parentheses; null when the parentheses do not pair. */
function splitTopLevel(text: string): string[] | null {
    const parts: string[] = [];
    let depth = 0;
    let start = 0;
    for (let i = 0; i < text.length; i++) {
        const ch = text[i];
        if (ch === '(') depth++;
        else if (ch === ')') {
            depth--;
            if (depth < 0) return null;
        } else if (ch === ',' && depth === 0) {
            parts.push(text.slice(start, i));
            start = i + 1;
        }
    }
    if (depth !== 0) return null;
    parts.push(text.slice(start));
    return parts;
}

/** One mix argument: a colour, with its percentage before or after it. */
function colorAndPercent(part: string): {color: string; percent: number | null} | null {
    const text = part.trim();
    if (!text) return null;
    const after = /^([\s\S]*?)\s+(\d+(?:\.\d+)?)%$/.exec(text);
    if (after && splitTopLevel(after[1]) !== null) return {color: after[1].trim(), percent: Number(after[2])};
    const before = /^(\d+(?:\.\d+)?)%\s+([\s\S]+)$/.exec(text);
    if (before) return {color: before[2].trim(), percent: Number(before[1])};
    return {color: text, percent: null};
}

const isTransparent = (color: string) => color.toLowerCase() === 'transparent';
const isBase = (color: string) => VAR_RE.test(color) || (!isTransparent(color) && parseColor(color) !== null);

/**
 * `color-mix(in <space>, <base> [p%], transparent [q%])`, in either order, the percentage before or after its colour.
 * The base's share follows CSS Color 5: p; else 100 − q; else 50. Null for any other `color-mix()`, for a space CSS
 * does not know (or a hue method on a rectangular one), for percentages that do not add up to 100 (they would scale the
 * alpha once more), and for anything that is not a `color-mix()`.
 */
export function parseTransparentMix(text: string): TransparentMix | null {
    const call = /^color-mix\(([\s\S]*)\)$/i.exec(text.trim());
    if (!call) return null;
    const args = splitTopLevel(call[1]);
    if (!args || args.length !== 3) return null;
    const space = SPACE_RE.exec(args[0].trim().replace(/\s+/g, ' '));
    const name = space?.[1].toLowerCase() ?? '';
    if (!space || !(RECTANGULAR_SPACES.has(name) || POLAR_SPACES.has(name)) || (space[2] && !POLAR_SPACES.has(name))) return null;
    const first = colorAndPercent(args[1]);
    const second = colorAndPercent(args[2]);
    if (!first || !second || isTransparent(first.color) === isTransparent(second.color)) return null;
    const [base, clear] = isTransparent(second.color) ? [first, second] : [second, first];
    if (!isBase(base.color)) return null;
    let percent = 50;
    if (base.percent !== null && clear.percent !== null) {
        if (Math.abs(base.percent + clear.percent - 100) > 1e-9) return null;
        percent = base.percent;
    } else if (base.percent !== null) percent = base.percent;
    else if (clear.percent !== null) percent = 100 - clear.percent;
    if (!(percent >= 0 && percent <= 100)) return null;
    return {space: space[2] ? `${name} ${space[2].toLowerCase()} hue` : name, base: base.color, percent};
}

const formatPercent = (percent: number) => String(Math.round(percent * 100) / 100);

/** The canonical text of a mix: the base first, its percentage after it, `transparent` last. */
export function joinTransparentMix(mix: TransparentMix): string {
    return `color-mix(in ${mix.space}, ${mix.base} ${formatPercent(mix.percent)}%, transparent)`;
}

/**
 * The colour a value stands for: a literal, a `var()` (through `lookup`, which may return another value), a mix with
 * `transparent` (the base at its share). Null when it cannot be resolved.
 */
export function resolveValue(text: string, lookup: (name: string) => string, depth = 0): Rgba | null {
    if (depth > MAX_DEPTH) return null;
    const value = text.trim();
    const ref = VAR_RE.exec(value);
    if (ref) return resolveValue(lookup(ref[1]), lookup, depth + 1);
    const mix = parseTransparentMix(value);
    if (mix) {
        const base = resolveValue(mix.base, lookup, depth + 1);
        return base ? {...base, alpha: base.alpha * (mix.percent / 100)} : null;
    }
    return parseColor(value);
}

/** The opacity the editor's A slider shows: a mix's share of its base, a literal's alpha, 1 for a `var()`. Null otherwise. */
export function valueOpacity(text: string): number | null {
    const value = text.trim();
    const mix = parseTransparentMix(value);
    if (mix) return mix.percent / 100;
    if (VAR_RE.test(value)) return 1;
    return parseColor(value)?.alpha ?? null;
}

/** A colour literal in the notation of `like`: OKLCH stays OKLCH, and so does a colour outside sRGB; else hex. */
function formatLike(like: string, rgba: Rgba): string {
    if (/^oklch\(/i.test(like.trim()) || !inSrgbGamut(rgba)) return formatOklch(rgbaToOklch(rgba));
    return toHex(rgba);
}

/**
 * The value at another opacity, 0–1. A mix keeps its base (a role stays referenced) and changes its share, back to the
 * bare base at 100%; a `var()` becomes a mix in `oklab`; a literal takes the alpha, as `oklch(… / a)` when it was
 * written in OKLCH or lies outside sRGB, else as `#rrggbbaa`. Null when the value is none of these.
 */
export function withOpacity(text: string, opacity: number): string | null {
    if (!Number.isFinite(opacity)) return null;
    const value = text.trim();
    // To 0.1%, for every form: just under 100% is opaque, and a literal does not end up `#…ff` or `/ 1`.
    const percent = Math.round(Math.min(1, Math.max(0, opacity)) * 1000) / 10;
    const mix = parseTransparentMix(value);
    if (mix) return percent >= 100 ? mix.base : joinTransparentMix({...mix, percent});
    if (VAR_RE.test(value)) return percent >= 100 ? value : joinTransparentMix({space: 'oklab', base: value, percent});
    const rgba = parseColor(value);
    return rgba ? formatLike(value, {...rgba, alpha: percent / 100}) : null;
}

/**
 * `base` (a colour literal or `var()`) at the opacity of `text`: what the colour controls of the editor write. A fully
 * transparent literal (`transparent`, `#…00`) holds no colour to keep the opacity of: the new colour comes in opaque. A
 * mix keeps its share, even 0%, which only the A slider sets.
 */
export function withBase(text: string, base: string): string {
    const next = base.trim();
    const mix = parseTransparentMix(text);
    if (mix) return joinTransparentMix({...mix, base: next});
    const opacity = valueOpacity(text);
    if (opacity === null || opacity >= 1 || opacity <= 0) return next;
    return withOpacity(next, opacity) ?? next;
}

/** The variable a value takes its colour from: `var(--x)`, or the base of a mix. */
export function baseVar(text: string): string | null {
    const value = text.trim();
    const mix = parseTransparentMix(value);
    return VAR_RE.exec(mix ? mix.base : value)?.[1] ?? null;
}
