/**
 * drawnColors — the colours drawn where a `var(--lf-…)` cannot reach (the cheetah-grid theme of the spreadsheet
 * preview, the SVG data URLs of the image placeholders and of the uploader avatars), each one a colour role of
 * tokens.css read through `chartRoles` (D-T5). In both themes:
 *
 * - **Which role every colour reads.** Each opaque role the module reads is stubbed with a `#rrggbb` of its own, so a
 *   colour handed out names the role it came from. The dark spreadsheet theme is walked whole, nested keys included,
 *   and compared key path by key path with the approved mapping (its provisional choices are the designer's, point
 *   35): a swapped role, a literal left behind, a key added or dropped is a red that names it. The light theme's two
 *   borders and the placeholder colours likewise.
 * - **The selection** is `--lf-selected`, translucent, flattened over the cell's field into an opaque `rgb()`. A node
 *   run has no canvas to resolve a translucent value, so the role reads its stand-in; the expectation is built from the
 *   two roles as read, with `over` of `./contrast`, never with copied numbers.
 * - **The rows a caller points at** take `--lf-mark-bg` over the field: an opaque role comes out as its own channels,
 *   written `rgb()`.
 * - **A fresh theme at every build**: one build, mutated at any depth, leaks into no later one, and a later build
 *   writes nothing into it — no part is shared between two grids.
 * - **The avatar initial** is `readableText` of its disc: the lighter text on a very dark disc, the darker on a very
 *   light one — whichever role that is in the theme, measured with `contrastRatio`.
 *
 * That every role the module reads is a `ChartRole` is the type-check's: `color()` takes nothing else.
 *
 * Node env: no DOM, no canvas.
 *
 * @module lib/theme/drawnColors.test
 */
import {afterEach, describe, expect, it} from 'vitest';

import {parseRgba, type Rgb, type Rgba} from './colorAlpha';
import {contrastRatio, over} from './contrast';
import {buildDarkSpreadsheetTheme, fileAvatarInitialColor, imagePlaceholderColors, spreadsheetLightBorders, spreadsheetTargetRowBg} from './drawnColors';
import {chartRoles, type ChartRole, type ChartRoles, setRoleReader} from './roleColors';

const THEMES = ['light', 'dark'] as const;

/** The opaque roles the module reads, each with a `#rrggbb` of its own, its three channels apart. `--lf-selected` is left to its stand-in. */
const STUBS = {
    '--lf-text-primary': '#012141',
    '--lf-text-secondary': '#022242',
    '--lf-text-muted': '#032343',
    '--lf-surface-field': '#042444',
    '--lf-surface-panel': '#052545',
    '--lf-surface-hover': '#062646',
    '--lf-surface-neutral': '#072747',
    '--lf-border-subtle': '#082848',
    '--lf-border-input': '#092949',
    '--lf-focus': '#0a2a4a',
    '--lf-checked': '#0b2b4b',
    '--lf-action': '#0c2c4c',
    '--lf-on-action': '#0d2d4d',
    '--lf-info': '#0e2e4e',
    '--lf-danger': '#0f2f4f',
    '--lf-warning': '#103050',
    '--lf-mark-bg': '#113151',
} satisfies Partial<Record<ChartRole, string>>;

/** A stub back to its role: a colour handed out names the role it was read from. */
const ROLE_OF = new Map<unknown, string>(Object.entries(STUBS).map(([role, stub]) => [stub, role]));

/** The dark spreadsheet theme, key path by key path: the role each colour reads. */
const DARK_SPREADSHEET: Record<string, ChartRole> = {
    color: '--lf-text-primary',
    frozenRowsColor: '--lf-text-secondary',
    defaultBgColor: '--lf-surface-field',
    frozenRowsBgColor: '--lf-surface-panel',
    highlightBgColor: '--lf-surface-hover',
    borderColor: '--lf-border-subtle',
    frozenRowsBorderColor: '--lf-border-input',
    highlightBorderColor: '--lf-focus',
    'checkbox.uncheckBgColor': '--lf-surface-field',
    'checkbox.checkBgColor': '--lf-checked',
    'checkbox.borderColor': '--lf-border-input',
    'radioButton.checkColor': '--lf-checked',
    'radioButton.checkBorderColor': '--lf-checked',
    'radioButton.uncheckBorderColor': '--lf-border-input',
    'radioButton.uncheckBgColor': '--lf-surface-field',
    'radioButton.checkBgColor': '--lf-surface-field',
    'button.color': '--lf-on-action',
    'button.bgColor': '--lf-action',
    'tree.lineColor': '--lf-border-subtle',
    'header.sortArrowColor': '--lf-text-muted',
    'messages.infoBgColor': '--lf-info',
    'messages.errorBgColor': '--lf-danger',
    'messages.warnBgColor': '--lf-warning',
    'indicators.topLeftColor': '--lf-border-subtle',
    underlayBackgroundColor: '--lf-surface-field',
};

/** A very dark disc, a very light one, and one as `FilesTable` draws it (`getStringColor(seed).text`, 30 % lightness). */
const DISCS = {veryDark: '#050505', veryLight: '#fafafa', drawn: 'hsl(237.5, 50%, 30%)'};

afterEach(() => {
    setRoleReader(null);
});

/** The roles of the theme as a drawing reads them: each role of STUBS its stub, any other its stand-in. */
function stubbedRoles(dark: boolean): ChartRoles {
    setRoleReader((role) => (STUBS as Partial<Record<ChartRole, string>>)[role] ?? '');
    return chartRoles(dark, null);
}

/** Every leaf of `tree` by its dotted key path (`checkbox.borderColor`): a stub named by its role, anything else as it is. */
function rolesOf(tree: object, prefix = ''): Record<string, unknown> {
    const leaves: Record<string, unknown> = {};
    for (const [key, value] of Object.entries(tree)) {
        if (value !== null && typeof value === 'object') Object.assign(leaves, rolesOf(value, `${prefix}${key}.`));
        else leaves[`${prefix}${key}`] = ROLE_OF.get(value) ?? value;
    }
    return leaves;
}

/** Every leaf of `tree`, at any depth, overwritten with `value`. */
function overwrite(tree: Record<string, unknown>, value: string): void {
    for (const [key, child] of Object.entries(tree)) {
        if (child !== null && typeof child === 'object') overwrite(child as Record<string, unknown>, value);
        else tree[key] = value;
    }
}

/** The channels of a colour known to be one: a premise, so its failure says so. */
function rgbaOf(colour: string): Rgba {
    const parsed = parseRgba(colour);
    if (!parsed) throw new Error(`premise: parseRgba reads ${JSON.stringify(colour)}`);
    return parsed;
}

/** Channels as the module writes a flattened colour: `rgb(r, g, b)`, rounded. */
const rgb = ({r, g, b}: Rgb): string => `rgb(${Math.round(r)}, ${Math.round(g)}, ${Math.round(b)})`;

it('premise: every stub is a #rrggbb of its own, handed back as it is in both themes', () => {
    const roles = Object.keys(STUBS) as ChartRole[];
    expect(new Set(Object.values(STUBS)).size, 'two roles share a stub: a swap between them would not show').toBe(roles.length);
    for (const theme of THEMES) {
        const read = stubbedRoles(theme === 'dark');
        for (const role of roles) expect(read.color(role), `${role}, ${theme} theme`).toBe((STUBS as Partial<Record<ChartRole, string>>)[role]);
    }
});

describe.each(THEMES)('%s theme', (theme) => {
    const dark = theme === 'dark';

    it('reads its role at every key path of the dark spreadsheet theme, nested ones included, and has no key without one', () => {
        // The selection is composed, not read: its value is the next tests'.
        expect(rolesOf(buildDarkSpreadsheetTheme(stubbedRoles(dark)))).toStrictEqual({...DARK_SPREADSHEET, selectionBgColor: expect.any(String)});
    });

    it("reads its role for the light theme's two borders and for the placeholder images", () => {
        const roles = stubbedRoles(dark);
        expect(rolesOf(spreadsheetLightBorders(roles))).toStrictEqual({borderColor: '--lf-border-subtle', frozenRowsBorderColor: '--lf-border-input'});
        expect(rolesOf(imagePlaceholderColors(roles))).toStrictEqual({background: '--lf-surface-neutral', shape: '--lf-text-muted'});
    });

    it('flattens the translucent --lf-selected over the field into an opaque rgb(), tinted', () => {
        const roles = stubbedRoles(dark);
        const selected = rgbaOf(roles.color('--lf-selected'));
        const field = rgbaOf(roles.color('--lf-surface-field'));
        expect(selected.alpha, 'barrier: the selected role is translucent, so there is something to flatten').toBeLessThan(1);

        const selection = buildDarkSpreadsheetTheme(roles).selectionBgColor;
        expect(selection, 'opaque, whole channels').toMatch(/^rgb\(\d+, \d+, \d+\)$/);
        expect(selection).toBe(rgb(over(selected, field)));
        expect(rgbaOf(selection), 'tinted: not the bare field').not.toStrictEqual(field);
    });

    it('tints the rows a caller points at with --lf-mark-bg over the field: an opaque role, so its own channels, as rgb()', () => {
        expect(spreadsheetTargetRowBg(stubbedRoles(dark))).toBe(rgb(rgbaOf(STUBS['--lf-mark-bg'])));
    });

    it('builds a fresh theme at every call: one build, mutated at any depth, and the next leave each other alone', () => {
        const roles = stubbedRoles(dark);
        const first = buildDarkSpreadsheetTheme(roles);
        const pristine = structuredClone(first);
        overwrite(first, 'mutated');
        const mutated = structuredClone(first);
        expect(mutated.checkbox.borderColor, 'barrier: the mutation reached a nested key').toBe('mutated');

        const next = buildDarkSpreadsheetTheme(roles);
        expect(next).not.toBe(first);
        expect(next, 'the mutation leaked into the next build').toStrictEqual(pristine);
        expect(first, 'the next build wrote into the first: a part is shared').toStrictEqual(mutated);
    });

    it('writes the avatar initial in readableText of its disc: the lighter text on a very dark disc, the darker on a very light one', () => {
        setRoleReader(() => '');
        const roles = chartRoles(dark, null);
        const texts = [roles.color('--lf-text-primary'), roles.color('--lf-text-on-inverse')];
        expect(texts[0], 'barrier: two different texts to choose from').not.toBe(texts[1]);
        // Which role is the lighter depends on the theme: measured against black, never assumed.
        const [darker, lighter] = [...texts].sort((a, b) => contrastRatio(a, '#000000') - contrastRatio(b, '#000000'));

        for (const disc of Object.values(DISCS)) expect(fileAvatarInitialColor(roles, disc), disc).toBe(roles.readableText(disc));
        expect(fileAvatarInitialColor(roles, DISCS.veryDark)).toBe(lighter);
        expect(fileAvatarInitialColor(roles, DISCS.veryLight)).toBe(darker);
    });
});
