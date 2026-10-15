/**
 * Alpha for the colours the charts build at run time — the one home for it.
 *
 * Each helper keeps the exact output its callers drew with before it moved here, so moving changed no pixel:
 * `rgba(r,g,b,a)` for the line charts, `#rrggbbaa` and `hsla(…)` for the lot charts, a two-digit hex suffix for the
 * stacked areas. What changed is what they accept. The old code assumed one shape — a `#rrggbb` — and turned anything
 * else into `rgba(NaN,NaN,NaN,a)` or an invalid `#rgb88`. Now a colour gets its alpha in a notation that can carry it,
 * or comes back unchanged: better a fully opaque colour than a corrupted one.
 *
 * @module lib/theme/colorAlpha
 */

/** Channels of an sRGB colour, 0–255. */
export interface Rgb {
    r: number;
    g: number;
    b: number;
}

const HEX_LONG = /^#([0-9a-f]{6})(?:[0-9a-f]{2})?$/i;
const HEX_SHORT = /^#([0-9a-f]{3})[0-9a-f]?$/i;
const FUNCTIONAL = /^(rgba?|hsla?|oklch)\(\s*([^)]*)\)$/i;

/** The numbers of a functional colour, whatever its separators: `1, 2, 3`, `1 2 3`, `1 2 3 / 0.5`. */
function channelsOf(args: string): string[] {
    return args
        .split(/[\s,/]+/)
        .map((part) => part.trim())
        .filter((part) => part !== '');
}

function hslToRgb(h: number, s: number, l: number): Rgb {
    const sat = s / 100;
    const light = l / 100;
    const a = sat * Math.min(light, 1 - light);
    const channel = (n: number) => {
        const k = (n + h / 30) % 12;
        return Math.round(255 * (light - a * Math.max(Math.min(k - 3, 9 - k, 1), -1)));
    };
    return {r: channel(0), g: channel(8), b: channel(4)};
}

function finite(rgb: Rgb): Rgb | null {
    return [rgb.r, rgb.g, rgb.b].every(Number.isFinite) ? rgb : null;
}

/** The sRGB channels of a hex, `rgb()` or `hsl()` colour, or `null` for any other notation. */
export function parseRgb(color: string): Rgb | null {
    const text = color.trim();
    const long = HEX_LONG.exec(text);
    if (long) {
        const hex = long[1];
        return {r: parseInt(hex.slice(0, 2), 16), g: parseInt(hex.slice(2, 4), 16), b: parseInt(hex.slice(4, 6), 16)};
    }
    const short = HEX_SHORT.exec(text);
    if (short) {
        const [r, g, b] = short[1].split('').map((digit) => parseInt(digit + digit, 16));
        return {r, g, b};
    }
    const fn = FUNCTIONAL.exec(text);
    if (!fn) return null;
    const name = fn[1].toLowerCase();
    const [first, second, third] = channelsOf(fn[2]);
    if (third === undefined) return null;
    if (name.startsWith('rgb')) {
        const channel = (value: string) => Math.round(value.endsWith('%') ? (parseFloat(value) * 255) / 100 : parseFloat(value));
        return finite({r: channel(first), g: channel(second), b: channel(third)});
    }
    if (name.startsWith('hsl')) return finite(hslToRgb(parseFloat(first), parseFloat(second), parseFloat(third)));
    return null;
}

/** An sRGB colour with its opacity, 0–1. */
export interface Rgba extends Rgb {
    alpha: number;
}

/**
 * The sRGB channels of a colour and its opacity (0–1): the notations of {@link parseRgb}, with the alpha of an
 * eight- or four-digit hex and of the fourth number of `rgba()`/`hsla()` (or after `/`); `null` for any other notation.
 */
export function parseRgba(color: string): Rgba | null {
    const rgb = parseRgb(color);
    if (!rgb) return null;
    const text = color.trim();
    let alpha = 1;
    const long = /^#[0-9a-f]{6}([0-9a-f]{2})$/i.exec(text);
    const short = /^#[0-9a-f]{3}([0-9a-f])$/i.exec(text);
    const fn = FUNCTIONAL.exec(text);
    if (long) alpha = parseInt(long[1], 16) / 255;
    else if (short) alpha = parseInt(short[1] + short[1], 16) / 255;
    else if (fn) {
        const fourth = channelsOf(fn[2])[3];
        if (fourth !== undefined) alpha = fourth.endsWith('%') ? parseFloat(fourth) / 100 : parseFloat(fourth);
    }
    return Number.isFinite(alpha) ? {...rgb, alpha: Math.min(1, Math.max(0, alpha))} : null;
}

/**
 * The colour at opacity `alpha`, as `rgba(r,g,b,alpha)`.
 *
 * For a `#rrggbb` the output is the one the old `hexToRgba` produced, character for character. Hex in its other
 * lengths, `rgb()` and `hsl()` become `rgba()` too (an alpha they already carried is replaced). `oklch()` keeps its own
 * notation, `oklch(L C H / alpha)`, since leaving it for sRGB would change the colour. Anything else — a named colour,
 * `var()`, `color-mix()` — is returned unchanged.
 */
export function toRgba(color: string, alpha: number): string {
    const rgb = parseRgb(color);
    if (rgb) return `rgba(${rgb.r},${rgb.g},${rgb.b},${alpha})`;
    const fn = FUNCTIONAL.exec(color.trim());
    if (fn && fn[1].toLowerCase() === 'oklch') {
        const [l, c, h] = channelsOf(fn[2]);
        if (h !== undefined) return `oklch(${l} ${c} ${h} / ${alpha})`;
    }
    return color;
}

/**
 * Apply an alpha channel to a colour the charts already computed. Two shapes are rewritten, exactly as the lot charts
 * always did:
 *
 * - `hsl(...)` → `hsla(..., alpha)` — the alpha is inserted literally, so the caller owns its range.
 * - `#rrggbb` → `#rrggbbaa` — the alpha is clamped to `[0, 1]`, scaled to a byte and appended as two hex digits.
 *
 * Anything else (a named colour, an already-rgba string, an `#rgb` shorthand) is returned unchanged: better a fully
 * opaque colour than a corrupted one.
 */
export function withAlpha(color: string, alpha: number): string {
    const hslMatch = color.match(/^hsl\((.+)\)$/i);
    if (hslMatch) return `hsla(${hslMatch[1]}, ${alpha})`;
    const hexMatch = color.match(/^#([0-9a-f]{6})$/i);
    if (hexMatch)
        return `${color}${Math.round(Math.min(1, Math.max(0, alpha)) * 255)
            .toString(16)
            .padStart(2, '0')}`;
    return color;
}

/**
 * A colour with the two-digit hex alpha `alphaHex` — what `color + '88'` meant, without its trap.
 *
 * The concatenation was right only for a six-digit hex: on `#rgb`, `rgb()` or `hsl()` it produced a string the canvas
 * ignores. A `#rrggbb` still gets the two digits appended, identical to the old output; any other colour gets the same
 * opacity through {@link toRgba}.
 *
 * @param alphaHex  Two hex digits, `'00'`–`'ff'` (`'88'` ≈ 53 %).
 */
export function withHexAlpha(color: string, alphaHex: string): string {
    if (/^#[0-9a-f]{6}$/i.test(color)) return `${color}${alphaHex}`;
    return toRgba(color, parseInt(alphaHex, 16) / 255);
}
