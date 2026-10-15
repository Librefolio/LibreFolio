/**
 * The colour roles of tokens.css, resolved for the charts — the sRGB bridge (D-T5).
 *
 * ECharts draws on a canvas from options built in TypeScript, so a role (`--lf-*`) reaches a chart only as a colour
 * string computed when the option is built. This module is that read: the GR4 shades take the card, the correlation
 * scale takes danger, panel and info, a readable text takes the primary and the inverse text (DV, the designer's round
 * 2). T widens the list of roles to every chart neutral in B4, with the parity gate below it.
 *
 * - **Where it reads: the chart's own element.** tokens.css recomputes the roles in the `.light`/`.dark` subtrees, so a
 *   chart inside a forced subtree, or in the Lab's preview, reads its roles from its own element, not from `<html>`.
 *   {@link chartRoles} takes that element as `scope`, `<html>` when there is none.
 * - **One computed style per draw, never cached across draws.** A chart takes a {@link ChartRoles} when it builds its
 *   option; a theme switch or a Designer Lab edit shows at its next draw. Only the resolution of a raw value is
 *   memoised.
 * - **Any CSS colour.** A plain `#rrggbb` passes as it is; any other notation — a `color-mix()`, an `oklch()` — is
 *   resolved by the browser itself through a canvas `fillStyle`: `#rrggbb` when opaque, `rgba()` when translucent,
 *   which zrender reads as it is (never flattened here).
 * - **Never empty.** Where tokens.css is not loaded (unit tests, server rendering) a role reads empty and the value of
 *   tokens.css for the theme stands in: `dark` is read for that alone. The `roleColors.test.ts` parity gate keeps the
 *   stand-ins equal to tokens.css, theme by theme: `lib/theme/` is outside the colour ratchet, so nothing else would.
 *
 * @module lib/theme/roleColors
 */

import {readableOn} from './contrast';
import {themed, type ThemePair} from './themePair';

/** The roles the charts read. */
export type ChartRole = '--lf-surface-card' | '--lf-surface-panel' | '--lf-text-primary' | '--lf-text-on-inverse' | '--lf-danger' | '--lf-info';

/** tokens.css, resolved per theme: what a role reads where the stylesheet is not loaded. Kept equal by the parity gate. */
const STAND_INS: Readonly<Record<ChartRole, ThemePair>> = {
    '--lf-surface-card': {light: '#fbf8f1', dark: '#171f1c'},
    '--lf-surface-panel': {light: '#eee9de', dark: '#1e2824'},
    '--lf-text-primary': {light: '#292d27', dark: '#eae6df'},
    '--lf-text-on-inverse': {light: '#fbf8f1', dark: '#171f1c'},
    '--lf-danger': {light: '#b42332', dark: '#f25f5c'},
    '--lf-info': {light: '#145dee', dark: '#5899fa'},
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
        result = overBlack === String(probe.fillStyle) ? overBlack : null;
    }
    resolutions.set(raw, result);
    return result;
}

/**
 * The roles as the chart drawn inside `scope` sees them: one computed style, taken at the first read, for one draw.
 * `scope` defaults to `<html>`; `dark` only picks the stand-in of a role that cannot be read.
 */
export function chartRoles(dark: boolean, scope?: Element | null): ChartRoles {
    const element = scope ?? (typeof document === 'undefined' ? null : document.documentElement);
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
