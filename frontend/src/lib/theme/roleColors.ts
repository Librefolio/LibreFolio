/**
 * The colour roles of tokens.css, resolved for the charts — the sRGB bridge (D-T5).
 *
 * ECharts draws on a canvas from options built in TypeScript, so a role (`--lf-*`) reaches a chart only as a colour
 * string computed when the option is built. This module is that read: the GR4 shades take the card, the correlation
 * scale takes danger, panel and info, a readable text takes the primary and the inverse text (DV, the designer's round
 * 2), the PAC's ideal weights take the secondary text (TD-1), and the neutrals of every chart — axes, grids, labels,
 * tooltip boxes, pointers — take the texts, the borders, the card, the neutral surface and the text on a state fill
 * (`chartNeutrals` in `./chartTheme`, B4, DV). The colours drawn outside the charts, on a canvas or in an SVG data URL
 * (`drawnColors.ts`, AF), read the field and the hover surfaces, the focus, the selection, the checked control, the
 * primary button and its text, the warning and the mark. The category colours of the asset types and the cash are the
 * roles `--lf-cat-*` since DV-11, read by `categoryColor` (`./chartCategories`) through {@link pageRoles}. The parity
 * gate below keeps the stand-ins equal to tokens.css.
 *
 * - **Where it reads: the chart's own element.** tokens.css recomputes the roles in the `.light`/`.dark` subtrees, so a
 *   chart inside a forced subtree, or in the Lab's preview, reads its roles from its own element, not from `<html>`.
 *   {@link chartRoles} takes that element as `scope`, `<html>` when there is none.
 * - **One computed style per draw, never cached across draws.** A chart takes a {@link ChartRoles} when it builds its
 *   option; a theme switch or a Designer Lab edit shows at its next draw. Only the resolution of a raw value is
 *   memoised.
 * - **Any CSS colour, always back in sRGB.** A plain `#rrggbb` passes as it is; any other notation — a `color-mix()`,
 *   an `oklch()` — is resolved by the browser itself through a canvas `fillStyle`. The canvas keeps a colour in its own
 *   space (Chromium reports a `color-mix(in oklab, …)` as `oklab(…)`, one `in srgb` as `color(srgb …)`), so what it
 *   reports is brought back to sRGB here: `#rrggbb` when opaque, `rgba()` when translucent — what zrender, the HTML of
 *   a tooltip, `parseRgba` and `over()` read (never flattened here). A notation it cannot bring back stands in.
 * - **Never empty.** Where tokens.css is not loaded (unit tests, server rendering) a role reads empty and the value of
 *   tokens.css for the theme stands in: `dark` is read for that alone. The `roleColors.test.ts` parity gate keeps the
 *   stand-ins equal to tokens.css, theme by theme: `lib/theme/` is outside the colour ratchet, so nothing else would.
 *   A translucent role (`--lf-selected`) has an `rgba()` stand-in, as the canvas would resolve it.
 *
 * @module lib/theme/roleColors
 */

import {toRgba} from './colorAlpha';
import {readableOn} from './contrast';
import {isDarkTheme} from './themeMode';
import {themed, type ThemePair} from './themePair';

/** The roles the charts and the drawn colours read. */
export type ChartRole =
    | '--lf-surface-card'
    | '--lf-surface-panel'
    | '--lf-surface-neutral'
    | '--lf-surface-field'
    | '--lf-surface-hover'
    | '--lf-text-primary'
    | '--lf-text-secondary'
    | '--lf-text-muted'
    | '--lf-text-on-inverse'
    | '--lf-border-subtle'
    | '--lf-border-raised'
    | '--lf-border-input'
    | '--lf-focus'
    | '--lf-selected'
    | '--lf-checked'
    | '--lf-action'
    | '--lf-on-action'
    | '--lf-on-status'
    | '--lf-warning'
    | '--lf-danger'
    | '--lf-info'
    | '--lf-mark-bg'
    | '--lf-cat-stock'
    | '--lf-cat-etf'
    | '--lf-cat-bond'
    | '--lf-cat-crypto'
    | '--lf-cat-fund'
    | '--lf-cat-hold'
    | '--lf-cat-crowdfund'
    | '--lf-cat-commodity'
    | '--lf-cat-real-estate'
    | '--lf-cat-index'
    | '--lf-cat-other'
    | '--lf-cat-liquidity';

/** tokens.css, resolved per theme: what a role reads where the stylesheet is not loaded. Kept equal by the parity gate. */
const STAND_INS: Readonly<Record<ChartRole, ThemePair>> = {
    '--lf-surface-card': {light: '#fafbfa', dark: '#151b19'},
    '--lf-surface-panel': {light: '#e8ece9', dark: '#1b2421'},
    '--lf-surface-neutral': {light: '#d8e0dc', dark: '#222c28'},
    '--lf-surface-field': {light: '#ffffff', dark: '#0f1413'},
    '--lf-surface-hover': {light: '#e8ece9', dark: '#1b2421'},
    '--lf-text-primary': {light: '#1c2420', dark: '#edf2f0'},
    '--lf-text-secondary': {light: '#4a5550', dark: '#9ba8a2'},
    '--lf-text-muted': {light: '#616d67', dark: '#7f8c87'},
    '--lf-text-on-inverse': {light: '#fafbfa', dark: '#151b19'},
    '--lf-border-subtle': {light: '#d8e0dc', dark: '#222c28'},
    '--lf-border-raised': {light: '#d8e0dc', dark: '#2e3b36'},
    '--lf-border-input': {light: '#7e8984', dark: '#606f6a'},
    '--lf-focus': {light: '#236b4d', dark: '#429e79'},
    /** The focus green at 12 % (`color-mix(in oklab, var(--lf-focus) 12%, transparent)`): translucent, so an rgba(). */
    '--lf-selected': {light: 'rgba(35,107,77,0.12)', dark: 'rgba(66,158,121,0.12)'},
    '--lf-checked': {light: '#236b4d', dark: '#429e79'},
    '--lf-action': {light: '#1b4334', dark: '#215240'},
    '--lf-on-action': {light: '#fafbfa', dark: '#edf2f0'},
    '--lf-on-status': {light: '#fafbfa', dark: '#151b19'},
    '--lf-warning': {light: '#ae4e00', dark: '#f59e0b'},
    '--lf-danger': {light: '#c82838', dark: '#ff7a86'},
    '--lf-info': {light: '#155eef', dark: '#3f86fa'},
    '--lf-mark-bg': {light: '#fde68a', dark: '#78350f'},
    /** The asset types' colours and the cash's (round 3, §1.2 and §1.9), the charts' one source since DV-11. */
    '--lf-cat-stock': {light: '#7041c6', dark: '#b69af0'},
    '--lf-cat-etf': {light: '#2459b8', dark: '#82acf8'},
    '--lf-cat-bond': {light: '#536a9e', dark: '#9baed8'},
    '--lf-cat-crypto': {light: '#b87916', dark: '#e8bd69'},
    '--lf-cat-fund': {light: '#5147b8', dark: '#9280ff'},
    '--lf-cat-hold': {light: '#5d687b', dark: '#c6d0e0'},
    '--lf-cat-crowdfund': {light: '#8b547d', dark: '#d5a0c7'},
    '--lf-cat-commodity': {light: '#b85e45', dark: '#e99a82'},
    '--lf-cat-real-estate': {light: '#96602c', dark: '#d6a36c'},
    '--lf-cat-index': {light: '#a33d79', dark: '#e58bb9'},
    '--lf-cat-other': {light: '#727b87', dark: '#a9b0bb'},
    '--lf-cat-liquidity': {light: '#3f628c', dark: '#639bc0'},
};

/** How a role is read for an element, for tests: by default its computed style. `''` when it has no value. */
export type RoleReader = (role: ChartRole, scope: Element | null) => string;

/** The roles as a chart sees them, read once for one draw. */
export interface ChartRoles {
    /** The colour of `role` for the chart: `#rrggbb`, or `rgba()` when translucent. */
    color(role: ChartRole): string;
    /**
     * The text that reads best on `background` — a slice, a cell, an avatar's disc: the primary text or the inverse
     * one, whichever has the higher contrast (one is dark and one light in both themes). A translucent background is
     * measured over the card.
     */
    readableText(background: string): string;
}

const HEX = /^#[0-9a-f]{6}$/i;
/** A colour function the canvas reports outside sRGB: its name, then what is inside the parentheses. */
const OUTSIDE_SRGB = /^(oklab|oklch|color)\(\s*(.*?)\s*\)$/i;

/** A number of a CSS colour function: `none` is 0, a percentage a share of `full`, an angle unit ignored (degrees). */
function component(token: string, full: number): number {
    if (token.toLowerCase() === 'none') return 0;
    return token.endsWith('%') ? (parseFloat(token) / 100) * full : parseFloat(token);
}

/** OKLab to gamma-encoded sRGB channels, 0–1 and unclipped (Björn Ottosson's matrices, as CSS Color 4). */
function oklabToSrgb(lightness: number, a: number, b: number): number[] {
    const l = (lightness + 0.3963377774 * a + 0.2158037573 * b) ** 3;
    const m = (lightness - 0.1055613458 * a - 0.0638541728 * b) ** 3;
    const s = (lightness - 0.0894841775 * a - 1.291485548 * b) ** 3;
    const linear = [4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s, -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s, -0.0041960863 * l - 0.7034186147 * m + 1.707614701 * s];
    return linear.map((c) => (c <= 0.0031308 ? 12.92 * c : 1.055 * c ** (1 / 2.4) - 0.055));
}

/**
 * A colour as the canvas reported it, in sRGB: `#rrggbb` when opaque, `rgba()` when translucent. A hex or an `rgba()`
 * passes as it is; `oklab()`, `oklch()` and `color(srgb …)` are converted, clipped to the sRGB gamut as the canvas
 * paints them. Any other notation: `null`, and the stand-in answers.
 */
function toSrgb(painted: string): string | null {
    const text = painted.trim();
    if (HEX.test(text) || /^rgba\(/i.test(text)) return text;
    const fn = OUTSIDE_SRGB.exec(text);
    if (!fn) return null;
    const [channels, alphaPart] = fn[2].split('/').map((part) => part.trim());
    let tokens = channels.split(/\s+/);
    const name = fn[1].toLowerCase();
    let rgb: number[];
    if (name === 'color') {
        if (tokens[0]?.toLowerCase() !== 'srgb') return null;
        tokens = tokens.slice(1);
        if (tokens.length !== 3) return null;
        rgb = tokens.map((token) => component(token, 1));
    } else {
        if (tokens.length !== 3) return null;
        const lightness = component(tokens[0], 1);
        const chromaOrA = component(tokens[1], 0.4);
        if (name === 'oklab') rgb = oklabToSrgb(lightness, chromaOrA, component(tokens[2], 0.4));
        else {
            const hue = (component(tokens[2], 360) * Math.PI) / 180;
            rgb = oklabToSrgb(lightness, chromaOrA * Math.cos(hue), chromaOrA * Math.sin(hue));
        }
    }
    const alpha = alphaPart === undefined ? 1 : component(alphaPart, 1);
    if (![...rgb, alpha].every(Number.isFinite)) return null;
    const hex = `#${rgb
        .map((c) =>
            Math.round(Math.min(1, Math.max(0, c)) * 255)
                .toString(16)
                .padStart(2, '0'),
        )
        .join('')}`;
    return alpha >= 1 ? hex : toRgba(hex, Math.max(0, alpha));
}

let reader: RoleReader | null = null;
let probe: CanvasRenderingContext2D | null | undefined;
const resolutions = new Map<string, string | null>();

/**
 * A CSS colour as the canvas paints it, or `null` when it is not a colour. An invalid value leaves `fillStyle` as it
 * was, so it is written over two different colours: a valid one comes back the same both times.
 */
function resolve(raw: string): string | null {
    if (raw === '') return null;
    if (HEX.test(raw)) return raw;
    const known = resolutions.get(raw);
    if (known !== undefined) return known;
    probe ??= typeof document === 'undefined' ? null : document.createElement('canvas').getContext('2d');
    let result: string | null = null;
    if (probe) {
        probe.fillStyle = '#000000';
        probe.fillStyle = raw;
        const overBlack = String(probe.fillStyle);
        probe.fillStyle = '#ffffff';
        probe.fillStyle = raw;
        result = overBlack === String(probe.fillStyle) ? toSrgb(overBlack) : null;
    }
    resolutions.set(raw, result);
    return result;
}

/**
 * The roles as the chart drawn inside `scope` sees them: one computed style, taken at the first read, for one draw.
 * `scope` defaults to `<html>`; `dark` only picks the stand-in of a role that cannot be read.
 */
export function chartRoles(dark: boolean, scope?: Element | null): ChartRoles {
    return rolesOf(dark, scope ?? (typeof document === 'undefined' ? null : document.documentElement));
}

/**
 * The roles of the page in the theme `dark`: read on `<html>` when the page shows that theme, the stand-ins of `dark`
 * when it shows the other one (a colour asked for the theme not on screen, the Lab's both-theme views, a unit test) or
 * there is no page. For a caller that has no element of its own and may ask for either theme: the category colours
 * (`categoryColor` in `./chartCategories`, DV-11).
 */
export function pageRoles(dark: boolean): ChartRoles {
    const page = typeof document === 'undefined' ? null : document.documentElement;
    return rolesOf(dark, page && isDarkTheme() === dark ? page : null);
}

/** The roles as read on `element`, or the stand-ins of `dark` when there is none. */
function rolesOf(dark: boolean, element: Element | null): ChartRoles {
    let style: CSSStyleDeclaration | null | undefined;
    const raw = (role: ChartRole): string => {
        if (reader) return reader(role, element);
        if (!element) return '';
        style ??= getComputedStyle(element);
        return style.getPropertyValue(role).trim();
    };
    const color = (role: ChartRole): string => resolve(raw(role)) ?? themed(STAND_INS[role], dark);
    return {
        color,
        readableText: (background) => readableOn(background, [color('--lf-text-primary'), color('--lf-text-on-inverse')], color('--lf-surface-card')),
    };
}

/** Replace how roles are read, for tests; `null` restores the computed style. */
export function setRoleReader(next: RoleReader | null): void {
    reader = next;
}
