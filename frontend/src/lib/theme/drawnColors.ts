/**
 * Colours drawn outside CSS — handed to a canvas library or baked into an SVG data URL — where a `var(--lf-…)` cannot
 * reach. Each one is a colour role of tokens.css, read for the active theme through the {@link ChartRoles} of
 * `./roleColors`: the caller takes `chartRoles(dark, element)` once per drawing and passes it here, so a theme switch or
 * a Designer Lab edit shows at the next build.
 *
 * Provisional choices, in the designer's collection (point 35): the rows a caller points at on `mark`, the avatar
 * initial by `readableText`, and the light spreadsheet on cheetah-grid's `MATERIAL_DESIGN` with only its two borders on
 * roles.
 */

import {parseRgba} from './colorAlpha';
import {over} from './contrast';
import type {ChartRoles} from './roleColors';

/**
 * `top` composited over the opaque `bottom`, as an opaque `rgb()`: what CSS shows for a translucent role on its surface.
 * cheetah-grid fills a cell without clearing it, so a translucent fill would add up with whatever the canvas already
 * held. `roleColors` hands every role back in sRGB (`#rrggbb`, or `rgba()` when translucent); anything else passes as is.
 */
function flatten(top: string, bottom: string): string {
    const front = parseRgba(top);
    const back = parseRgba(bottom);
    if (!front || !back) return top;
    const {r, g, b} = over(front, back);
    return `rgb(${Math.round(r)}, ${Math.round(g)}, ${Math.round(b)})`;
}

/**
 * Spreadsheet preview (`FilePreviewModal`, cheetah-grid): the rows the caller points at, a highlighted result (Q7). The
 * same role in both themes, on the cell's field.
 */
export function spreadsheetTargetRowBg(roles: ChartRoles): string {
    return flatten(roles.color('--lf-mark-bg'), roles.color('--lf-surface-field'));
}

/**
 * Spreadsheet preview, light theme: firmer grid lines over cheetah-grid's `MATERIAL_DESIGN` theme — the dividers, and
 * under the header the edge of an input. The rest of the light theme is the library's.
 */
export function spreadsheetLightBorders(roles: ChartRoles): {borderColor: string; frozenRowsBorderColor: string} {
    return {borderColor: roles.color('--lf-border-subtle'), frozenRowsBorderColor: roles.color('--lf-border-input')};
}

/**
 * Spreadsheet preview, dark theme: a fresh cheetah-grid theme object at every call. The cells are a field and the
 * header a panel; the active cell is lifted to the hover surface with the focus edge, a range selection takes the
 * selected tint. Checkboxes, radios, buttons, trees and cell messages are not used by the preview: they follow the
 * same roles so that the theme stays whole.
 */
export function buildDarkSpreadsheetTheme(roles: ChartRoles) {
    const field = roles.color('--lf-surface-field');
    const subtle = roles.color('--lf-border-subtle');
    const input = roles.color('--lf-border-input');
    const checked = roles.color('--lf-checked');
    return {
        color: roles.color('--lf-text-primary'),
        frozenRowsColor: roles.color('--lf-text-secondary'),
        defaultBgColor: field,
        frozenRowsBgColor: roles.color('--lf-surface-panel'),
        selectionBgColor: flatten(roles.color('--lf-selected'), field),
        highlightBgColor: roles.color('--lf-surface-hover'),
        borderColor: subtle,
        frozenRowsBorderColor: input,
        highlightBorderColor: roles.color('--lf-focus'),
        checkbox: {
            uncheckBgColor: field,
            checkBgColor: checked,
            borderColor: input,
        },
        radioButton: {
            checkColor: checked,
            checkBorderColor: checked,
            uncheckBorderColor: input,
            uncheckBgColor: field,
            checkBgColor: field,
        },
        button: {
            color: roles.color('--lf-on-action'),
            bgColor: roles.color('--lf-action'),
        },
        tree: {
            lineColor: subtle,
        },
        header: {
            sortArrowColor: roles.color('--lf-text-muted'),
        },
        // A message box is filled with the state and draws its mark in the cell's own background.
        messages: {
            infoBgColor: roles.color('--lf-info'),
            errorBgColor: roles.color('--lf-danger'),
            warnBgColor: roles.color('--lf-warning'),
        },
        indicators: {
            topLeftColor: subtle,
        },
        underlayBackgroundColor: field,
    };
}

/** Placeholder images of `LazyImage` (SVG data URLs): a skeleton fill and its muted figure. */
export function imagePlaceholderColors(roles: ChartRoles): {background: string; shape: string} {
    return {background: roles.color('--lf-surface-neutral'), shape: roles.color('--lf-text-muted')};
}

/**
 * The initial of an uploader avatar in the files table (SVG data URL), drawn over a `getStringColor` disc: the primary
 * or the inverse text, whichever reads better on that disc.
 */
export function fileAvatarInitialColor(roles: ChartRoles, disc: string): string {
    return roles.readableText(disc);
}
