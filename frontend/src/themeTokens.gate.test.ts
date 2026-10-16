/**
 * Gate: the contract of the colour roles — `src/lib/theme/tokens.css` — and the retirement of the legacy dark remap
 * of `src/app.css` (colour programme, workstream T, decision D-T8: contract C1–C4).
 *
 * ## What this protects
 *
 * tokens.css is the one home of the interface colours. A role `--lf-<group>-<name>` takes its light value on
 * `:root, html.light, .light` and its dark value on `html.dark, .dark`; a derived role is one formula on
 * `:root, .light, .dark` that each theme computes from its own base values; the `@theme inline` table turns every
 * role a class can use into Tailwind utilities (`bg-lf-card`, `text-lf-muted`) — the login illustration (`--lf-art-*`)
 * has none, its one component reads it with `var()`. A migrated component trusts that table blindly: it
 * writes `text-lf-muted` once, with no `dark:` to correct it, and gets whatever the two themes say. So the table must
 * be whole in both themes, readable, and legible. Meanwhile the legacy dark remap of app.css (P1) keeps the
 * components not yet migrated as they are: it must leave the migrated ones alone, and shrink as they go.
 *
 * ## The contract, as this file checks it
 *
 * tokens.css holds the four blocks of `TOKEN_BLOCKS` and nothing else — the module's parser throws on any other
 * block — and none of them is empty.
 *   C1  the light and the dark block declare the same base roles. The dark block may also override a derived role
 *       (none does today: round 2 retired the designer's dark password box, which did), but never declares a role
 *       of its own; and no role is both base and derived;
 *   C2  every utility of the table is `--color-lf-<name>: var(--lf-…)` of a role declared in the light or the
 *       derived block; every name is distinct; every utility resolves to a colour in both themes — and so does every
 *       role of the light, derived and dark blocks, utility or not, with no exception: a role is a colour. The login
 *       illustration (`--lf-art-*`) has no utility: its one component reads it with var(), where nothing but this
 *       check would see a role that does not resolve;
 *   C3  the pairs of `CONTRAST_PAIRS` reach their minimum in both themes: 4.5:1 for text (WCAG 1.4.3) — a status on
 *       its own tint included — and for the mark of a selected control (D-T16); 3:1 for the border of a field at rest
 *       and under the pointer (D-T18), a focus ring, the fill of a selected control, the knob of a switch turned on
 *       and the marks the green sidebar draws (WCAG 1.4.11). The header is a neutral surface (D-T23), one of
 *       `SURFACES`; the green sidebar (D-T17) is none, and has pairs of its own, in the --lf-bar-* family, its alone. A
 *       pair under its minimum is red unless `KNOWN_EXCEPTIONS` holds it, and an entry there is the designer's
 *       decision, not ours. And the backdrop, --lf-surface-overlay, is one colour in both themes: the pairs of the
 *       text on it hold for every theme only then;
 *   C4  every class the legacy remap rewrites (`html.dark .bg-white` …) is still written by a production source: a
 *       rule whose class lost its last use is dead, and leaves app.css in the change that removed that use.
 * And app.css imports tokens.css, and every rule of the remap that targets a field (`input`, `select`, `textarea`),
 * its placeholder, an `option` or a rounded container (`.rounded-xl`, `.rounded-2xl`) carries the `:where(…)` that
 * exempts the elements with a role utility (`-lf-` in their classes).
 * And inside the inverted tooltip a role reads the other theme's colour (Q10, its rule extended by D-T27): every
 * `--lf-<X>-on-inverse` but the tooltip's own text, `--lf-text-on-inverse`, is in each theme the colour the other theme
 * gives `--lf-<X>`. The roles are found by their name, so a new one is checked the day it is declared.
 *
 * ## How it reads, and what it cannot see
 *
 * Colours come from the module's resolver, which reads the forms tokens.css uses — a hex, `transparent`, `var(--…)`,
 * `color-mix(in oklab, A p, B)` — and mixes as CSS Color 5 does (OKLab, premultiplied alpha). A new form fails C2
 * loudly before it could fail C3 in silence. Contrast is computed on the declared values, not on the page: an
 * opacity utility (`text-lf-muted/70`), a gradient or an image behind the text are invisible here. So is a
 * translucent layer, unless it is a role whose pair names the opaque role it lies on, `over`: then the ratio is
 * taken on the two composited as the browser draws them (the backdrop and the selected tint, over each surface they
 * lie on); with no `over`, a translucent background is refused. A pair missing from `CONTRAST_PAIRS` is not checked
 * at all — a new role that carries text or draws a control adds its pairs in the same change. Nor is a control told
 * apart by two colours at once, a fill and an edge: that is no pair (the knob of a switch turned off, see
 * `CONTRAST_PAIRS`). The pairs are the floor; the gallery and the designer's review do the rest. C4 counts the class
 * written whole in a production source (`classUses`): a class assembled at run time (`` `bg-gray-${n}` ``) is no use,
 * and a string that merely spells the class is one.
 *
 * Registered in `front_utility_unit` (`scripts/test_runner/_frontend_utility.py`, action `core-unit`).
 */

import {afterAll, beforeAll, describe, expect, it} from 'vitest';
import {mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {APP_CSS, TOKEN_BLOCKS, blankCssComments, classUses, contrastRatio, over, p1Classes, parseTokens, readTokens, resolveColour, roleNames, toHex} from '../scripts/theme/theme-roles.mjs';

type Tokens = ReturnType<typeof parseTokens>;
type Rgba = ReturnType<typeof resolveColour>;
type Theme = Parameters<typeof resolveColour>[2];

const THEMES: readonly Theme[] = ['light', 'dark'];

/** At or above this alpha a colour is opaque: a mix of two opaque colours sums its weights in floating point. */
const OPAQUE = 1 - 1e-9;

/** A token expression's colour in a theme, or the reason it cannot be read. */
function colourOf(tokens: Tokens, expression: string, theme: Theme): Rgba | string {
    try {
        return resolveColour(tokens, expression, theme);
    } catch (error) {
        return error instanceof Error ? error.message : String(error);
    }
}

/** `#rrggbb`, and its alpha when it has one. */
const shown = (colour: Rgba): string => (colour.alpha < OPAQUE ? `${toHex(colour)} at ${Math.round(colour.alpha * 100)}%` : toHex(colour));

/** A ratio rounded down, so that 4.4999 never reads as 4.50. */
const ratioText = (ratio: number): string => (Math.floor(ratio * 100) / 100).toFixed(2);

// ---------------------------------------------------------------------------
// C1 and C2: the table
// ---------------------------------------------------------------------------

/** Four blocks with one fault of every kind C1 and C2 look for. */
const FAULTY_TOKENS = `
:root,
html.light,
.light {
    --lf-a: #ffffff;
    --lf-b: #000000;
    --lf-art-a: color-mix(in oklab, var(--lf-brnad) 15%, transparent);
}

:root,
.light,
.dark {
    --lf-c: var(--lf-a);
    --lf-b: var(--lf-a);
}

html.dark,
.dark {
    --lf-a: #111111;
    --lf-c: #222222;
    --lf-z: #333333;
    --lf-art-a: #444444;
}

@theme inline {
    --color-lf-a: var(--lf-a);
    --color-lf-c: var(--lf-c);
    --color-lf-ghost: var(--lf-ghost);
    --color-lf-raw: #ffffff;
    --color-brand: var(--lf-a);
}
`;

/** C1: what keeps the two themes from declaring the same roles. */
function themeFindings(tokens: Tokens): string[] {
    const out: string[] = [];
    for (const name of tokens.light.keys()) if (!tokens.dark.has(name)) out.push(`${name}  missing from the dark block`);
    for (const name of tokens.dark.keys()) if (!tokens.light.has(name) && !tokens.derived.has(name)) out.push(`${name}  in the dark block only, and no derived role it could override`);
    for (const name of tokens.derived.keys()) if (tokens.light.has(name)) out.push(`${name}  in both the light and the derived block`);
    return out;
}

/** The name of a utility: lower-case words joined by hyphens, the only names the grammar (G2) can read. */
const UTILITY = /^--color-lf-[a-z0-9]+(?:-[a-z0-9]+)*$/;

/** C2: what keeps a utility from naming a declared role. */
function utilityFindings(tokens: Tokens): string[] {
    const out: string[] = [];
    for (const [key, value] of tokens.utilities) {
        if (!UTILITY.test(key)) out.push(`${key}  not a --color-lf-<name> utility`);
        const role = /^var\((--lf-[\w-]+)\)$/.exec(value)?.[1];
        if (role === undefined) out.push(`${key}  ${value} is not var(--lf-…): a utility names a role, nothing else`);
        else if (!tokens.light.has(role) && !tokens.derived.has(role)) out.push(`${key}  ${role} is declared neither in the light block nor in the derived block`);
    }
    return out;
}

/** Every role tokens.css declares, in the light, the derived or the dark block: once each, in the order of the file. */
const declaredRoles = (tokens: Tokens): string[] => [...new Set([...tokens.light.keys(), ...tokens.derived.keys(), ...tokens.dark.keys()])];

/** C2: what keeps a role — named by a utility or read by var() alone — from being a colour in a theme. */
function roleFindings(tokens: Tokens): string[] {
    const out: string[] = [];
    for (const theme of THEMES) {
        for (const name of declaredRoles(tokens)) {
            const colour = colourOf(tokens, `var(${name})`, theme);
            if (typeof colour === 'string') out.push(`${theme}  ${name}: ${colour}`);
        }
    }
    return out;
}

describe('tokens.css: the table of the roles (C1, C2)', () => {
    it('reads exactly the four blocks of TOKEN_BLOCKS, none of them empty, and refuses any other block', () => {
        const tokens = readTokens();
        expect(Object.keys(tokens).sort()).toEqual(Object.keys(TOKEN_BLOCKS).sort());
        expect(Object.fromEntries(Object.entries(tokens).map(([block, declarations]) => [block, declarations.size > 0])), 'every block declares something').toEqual({light: true, derived: true, dark: true, utilities: true});
        // The parser is the guard: a fifth block, a nested one or a repeated name would put a role out of the contract's sight.
        expect(() => parseTokens(`${FAULTY_TOKENS}\n.other {\n    --lf-q: #ffffff;\n}\n`)).toThrow(/unexpected block «\.other»/);
        expect(() => parseTokens(':root,\nhtml.light,\n.light {\n    --lf-a: #ffffff;\n    --lf-a: #000000;\n}\n')).toThrow(/--lf-a declared twice/);
    });

    it('finds every fault of C1 and C2 in a faulty table (positive control)', () => {
        const faulty = parseTokens(FAULTY_TOKENS);
        expect(themeFindings(faulty)).toEqual(['--lf-b  missing from the dark block', '--lf-z  in the dark block only, and no derived role it could override', '--lf-b  in both the light and the derived block']);
        expect(utilityFindings(faulty)).toEqual(['--color-lf-ghost  --lf-ghost is declared neither in the light block nor in the derived block', '--color-lf-raw  #ffffff is not var(--lf-…): a utility names a role, nothing else', '--color-brand  not a --color-lf-<name> utility']);
        expect(roleFindings(faulty), 'a role no utility names is read all the same: the typo of --lf-art-a').toEqual(['light  --lf-art-a: tokens.css: --lf-brnad is not declared for the light theme', 'light  --lf-z: tokens.css: --lf-z is not declared for the light theme']);
        expect(typeof colourOf(faulty, 'var(--lf-ghost)', 'dark'), 'an undeclared role cannot be read').toBe('string');
        expect(typeof colourOf(readTokens(), 'rgb(0 0 0)', 'light'), 'nor can a form the resolver does not know').toBe('string');
    });

    it('C1: the light and the dark block declare the same base roles; the dark block overrides only derived roles', () => {
        const findings = themeFindings(readTokens());
        expect(findings, ['', 'A role is declared for both themes, or derived once for both:', '', ...findings, ''].join('\n  ')).toEqual([]);
    });

    it('C2: every utility names a declared role, once', () => {
        const tokens = readTokens();
        const findings = utilityFindings(tokens);
        expect(findings, ['', 'Every utility of @theme inline is --color-lf-<name>: var(--lf-…) of a role of the light or the derived block:', '', ...findings, ''].join('\n  ')).toEqual([]);
        expect(roleNames(tokens).size, 'every utility names a distinct role').toBe(tokens.utilities.size);
    });

    it('C2: every utility resolves to a colour in both themes', () => {
        const tokens = readTokens();
        const unreadable: string[] = [];
        for (const theme of THEMES) {
            for (const [key, value] of tokens.utilities) {
                const colour = colourOf(tokens, value, theme);
                if (typeof colour === 'string') unreadable.push(`${theme}  ${key}: ${colour}`);
            }
        }
        expect(unreadable, ['', 'A utility the resolver cannot read is a utility C3 cannot check: use the forms tokens.css already uses, or teach resolveColour the new one.', '', ...unreadable, ''].join('\n  ')).toEqual([]);
    });

    it('C2: every role resolves to a colour in both themes, utility or not', () => {
        const tokens = readTokens();
        const named = new Set(tokens.utilities.values());
        const readByVarAlone = declaredRoles(tokens).filter((name) => !named.has(`var(${name})`));
        expect(readByVarAlone, 'positive control: the check reaches the roles no utility names — the login illustration among them').toEqual(expect.arrayContaining(['--lf-art-hill-1', '--lf-art-hill-2', '--lf-art-hill-3', '--lf-art-line']));
        const findings = roleFindings(tokens);
        const rule = 'Every role is a colour in both themes, whether a utility names it or var() reads it alone: one the resolver cannot read draws nothing, in silence. Fix the role, or teach resolveColour its form.';
        expect(findings, ['', rule, '', ...findings, ''].join('\n  ')).toEqual([]);
    });
});

// ---------------------------------------------------------------------------
// C3: contrast
// ---------------------------------------------------------------------------

const TEXT = 4.5;
const NON_TEXT = 3;
const STATUSES = ['success', 'warning', 'danger', 'info'];
/** A gain and a loss: the signed figures, as text and on their own tints (the sign badges). */
const SIGNS = ['gain', 'loss'];
/** The neutral surfaces text and controls are set on, the header's among them (D-T23); the green sidebar's pairs are its own. */
const SURFACES = ['surface-app', 'surface-page', 'surface-header', 'surface-card', 'surface-panel', 'surface-field'];

interface ContrastPair {
    foreground: string;
    background: string;
    /** The opaque role a translucent background lies on, composited under it before the ratio is taken (`measurePair`). */
    over?: string;
    min: number;
}

/** Every foreground on every background, as role variables: `--lf-text-muted` on `--lf-surface-panel`. */
const pairs = (foregrounds: string[], backgrounds: string[], min: number): ContrastPair[] => foregrounds.flatMap((foreground) => backgrounds.map((background) => ({foreground: `--lf-${foreground}`, background: `--lf-${background}`, min})));

/** Every foreground on a translucent background, once over each opaque role it lies on: `--lf-on-overlay` on `--lf-surface-overlay` over `--lf-surface-field`. */
const pairsOver = (foregrounds: string[], background: string, unders: string[], min: number): ContrastPair[] => foregrounds.flatMap((foreground) => unders.map((under) => ({foreground: `--lf-${foreground}`, background: `--lf-${background}`, over: `--lf-${under}`, min})));

/**
 * What the roles promise, in both themes: the designer's round 2, approved whole by the developer (D-T17, 15/10), with
 * the corrections of his review of the preview (D-T23).
 *
 * On the neutral surfaces, `SURFACES`, text reaches 4.5:1 (WCAG 1.4.3) wherever it is set; the border of a field
 * reaches 3:1 at rest and under the pointer — the hover border is the muted text colour (D-T18) — and so does the
 * focus ring (WCAG 1.4.11). The header is one of them since D-T23: a surface of its own, --lf-surface-header, a step
 * darker than the page in light and a step lighter in dark, its controls drawn in the page's roles, its focus ring the
 * page's --lf-focus; «Offrimi un caffè», --lf-donate, is text on it and, under the pointer, on --lf-surface-hover. A
 * status is legible as text on the surfaces — the danger dot of the mobile menu, ringed in the header's colour, among
 * them — and on its own tint, where its on-soft text, the muted and the primary text are held to the same minimum. A
 * gain and a loss are held like the statuses, as text on the surfaces and on their own tints, --lf-gain-soft and
 * --lf-loss-soft (the sign badges): roles apart from the state tints, so the designer can part them. Text on a solid
 * status is --lf-on-status, on the hover of a solid success, warning, info or donation button too (the success and
 * info hovers, --lf-success-hover and --lf-info-hover, provisional), and on a solid destructive button
 * --lf-on-danger-solid, at rest and hovered. A selected control (D-T16: checkbox, radio, switch on, selected day or
 * preset): its fill, --lf-checked, reaches 3:1 on every surface it sits on; its mark, --lf-on-checked, is held to the
 * text minimum on the fill, as the decision quotes it; and the knob of a switch turned on, --lf-switch-knob-on,
 * reaches 3:1 on it.
 *
 * The green sidebar is no neutral surface. It is green in both themes (D-T17, which supersedes the neutral sidebar of
 * D-T15), drawn from a family of roles of its own, --lf-bar-*: D-T19 shared the family with the header, and D-T23 gave
 * the header back a neutral surface, so the family is the sidebar's alone. On the sidebar, text: the bar text on the
 * bar, under the pointer, on the active fill (the icon of the default avatar) and on the logout button at rest and
 * hovered; the muted bar text (the version, the e-mail) on the bar and under the pointer; the active text on its fill
 * (the active item, its icon included), on the bar (the username) and under the pointer (the username hovered, the
 * docs link of the connection line); the logo block's --lf-on-brand on the bar, the block having no surface of its
 * own; the bright warning on the bar and under the pointer — the warning of the connection line to the administrators
 * sits on its details panel, drawn in the hover colour. And marks, at 3:1: the indicator of the active item, on the
 * bar beside it and on its fill; the sidebar's keyboard focus ring on every surface of it the ring surrounds — there
 * the page's --lf-focus would give 1.73:1 in light; and the connection-security icons, on the bar and on their toggle
 * hovered.
 *
 * And the rest of round 2: a warning inside the tooltip, --lf-warning-on-inverse on --lf-surface-inverse, and beside it
 * — the Q10 rule extended by D-T27, each the other theme's colour — a danger, an info and the muted text,
 * --lf-danger-on-inverse, --lf-info-on-inverse and --lf-text-muted-on-inverse; a highlighted search result; the
 * terminal box, its text, its prompt and its comments; the AI accent as text on its tint, on the card and on the panel,
 * and --lf-on-ai on its solid fill.
 *
 * And the text on the backdrop, --lf-on-overlay (provisional: a camera on an avatar, an icon on a scrim). The
 * backdrop, --lf-surface-overlay, is translucent, so each of its pairs names the surface it lies on, `over`, and the
 * ratio is taken on the two composited: once over each of `SURFACES`. That is sound because the backdrop is the same
 * in both themes — `backdropFindings` holds it — so its composite over the brightest surface, the light theme's white
 * field (--lf-surface-field, #ffffff), is the worst case of every theme, a white image under a dark-theme backdrop
 * included. Measured on 16/10: 4.98:1 over the field, 5.10–5.60:1 over the other light surfaces, 17.88:1 and more in
 * dark.
 *
 * And a selected row, option or chip, --lf-selected: a translucent tint of the focus green, so its pairs name the
 * surface under it, `over`, as the backdrop's do. The link green is held on it over the app, the page, the header, the
 * card and the field, never over a panel: 4.09:1 in dark. The primary and the secondary text are held over all six.
 * The muted text, the statuses and the signs reach only 3.84–4.48:1 on it over most surfaces, so they are not promised
 * there; a lighter tint would not cure it — at 6% the muted text still gives 4.17:1 — and it is an open item, TC-15.
 * Measured on 16/10: the link 4.53:1 at worst, over the dark card; the secondary text 5.45:1, over the dark panel.
 *
 * What C3 cannot express: a control told apart by two colours at once. The knob of a switch turned off,
 * --lf-switch-knob-off, is white on the light track of --lf-switch-off in light, and the control is recognised by the
 * --lf-border-input edge the knob is drawn with — an edge between two fills, which no pair holds. An item for the
 * designer's round 3. Nor a colour that is no role: the «insecure» tint behind the connection-security toggle is
 * `bg-lf-bar-danger/20`, composited over the bar — an opacity on a role, so no role of its own, and no background a
 * pair could name (`over` composites a role, never an opacity utility): the icon on it measures 3.41:1 and the focus
 * ring 3.94:1, checked by hand (15/10, after D-T25). Nor the hovered selection chip, `hover:bg-lf-checked/20`, an
 * opacity utility as well: by hand, the link on it measured 3.99–4.43:1, so the two chips (SelectionBar, DataEditor)
 * switch to `hover:text-lf-primary`, 10.09–12.86:1 (16/10).
 */
const CONTRAST_PAIRS: readonly ContrastPair[] = [
    ...pairs(['text-primary', 'text-secondary', 'text-muted', 'text-placeholder'], SURFACES, TEXT),
    ...pairs(['link'], ['surface-app', 'surface-page', 'surface-card', 'surface-panel'], TEXT),
    ...pairs(STATUSES, SURFACES, TEXT),
    ...pairs(SIGNS, SURFACES, TEXT),
    ...pairs(['donate'], ['surface-app', 'surface-page', 'surface-header', 'surface-hover'], TEXT),
    ...STATUSES.flatMap((status) => pairs([status, `${status}-on-soft`, 'text-muted', 'text-primary'], [`${status}-soft`], TEXT)),
    ...SIGNS.flatMap((sign) => pairs([sign, `${sign}-on-soft`, 'text-muted', 'text-primary'], [`${sign}-soft`], TEXT)),
    ...pairs(['on-brand'], ['brand'], TEXT),
    ...pairs(['on-action'], ['action', 'action-hover'], TEXT),
    ...pairs(['on-status'], [...STATUSES, 'success-hover', 'warning-hover', 'info-hover'], TEXT),
    ...pairs(['on-danger-solid'], ['danger-solid', 'danger-hover'], TEXT),
    ...pairs(['on-checked'], ['checked'], TEXT),
    ...pairs(['text-on-inverse', 'warning-on-inverse', 'danger-on-inverse', 'info-on-inverse', 'text-muted-on-inverse'], ['surface-inverse'], TEXT),
    ...pairs(['mark-text'], ['mark-bg'], TEXT),
    ...pairs(['terminal-text', 'terminal-prompt', 'terminal-comment'], ['terminal-bg'], TEXT),
    ...pairs(['ai'], ['ai-soft', 'surface-card', 'surface-panel'], TEXT),
    ...pairs(['on-ai'], ['ai'], TEXT),
    ...pairsOver(['on-overlay'], 'surface-overlay', SURFACES, TEXT),
    ...pairsOver(['link'], 'selected', ['surface-app', 'surface-page', 'surface-header', 'surface-card', 'surface-field'], TEXT),
    ...pairsOver(['text-primary', 'text-secondary'], 'selected', SURFACES, TEXT),
    ...pairs(['border-input', 'border-input-hover'], SURFACES, NON_TEXT),
    ...pairs(['focus'], ['surface-app', 'surface-header', 'surface-card', 'surface-panel', 'surface-field'], NON_TEXT),
    ...pairs(['checked'], ['surface-card', 'surface-panel', 'surface-field'], NON_TEXT),
    ...pairs(['switch-knob-on'], ['checked'], NON_TEXT),

    // The green sidebar (D-T17): the --lf-bar-* family, the sidebar's alone since D-T23
    ...pairs(['bar-text'], ['surface-bar', 'bar-hover', 'bar-active-bg', 'bar-logout-bg', 'bar-logout-hover'], TEXT),
    ...pairs(['bar-text-muted'], ['surface-bar', 'bar-hover'], TEXT),
    ...pairs(['bar-active-text'], ['bar-active-bg', 'surface-bar', 'bar-hover'], TEXT),
    ...pairs(['on-brand'], ['surface-bar'], TEXT),
    ...pairs(['bar-warning'], ['surface-bar', 'bar-hover'], TEXT),
    ...pairs(['bar-indicator'], ['surface-bar', 'bar-active-bg'], NON_TEXT),
    ...pairs(['bar-focus'], ['surface-bar', 'bar-hover', 'bar-active-bg', 'bar-logout-bg'], NON_TEXT),
    ...pairs(['bar-success', 'bar-danger'], ['surface-bar', 'bar-hover'], NON_TEXT),
];

interface KnownException {
    theme: Theme;
    foreground: string;
    background: string;
    /** The pair's `over`, when it names one: an exception names one exact pair. */
    over?: string;
    /** The designer's decision and its date: why the pair stays under its minimum. */
    reason: string;
}

/**
 * Pairs that stay under their minimum on purpose: NONE. An entry is the designer's decision, never a way to turn the
 * gate green — record her reason and the date. An entry whose pair reaches its minimum again is stale, and fails.
 */
const KNOWN_EXCEPTIONS: readonly KnownException[] = [];

/** A pair as the messages name it, `over` included: two pairs that differ only by their `over` are two pairs. */
const pairText = (pair: Pick<ContrastPair, 'foreground' | 'background' | 'over'>): string => `${pair.foreground} on ${pair.background}${pair.over === undefined ? '' : ` over ${pair.over}`}`;

const pairName = (theme: Theme, pair: Pick<ContrastPair, 'foreground' | 'background' | 'over'>): string => `${theme}  ${pairText(pair)}`;

/** A pair measured in a theme: the ratio, and the two colours it was taken on. */
interface Contrast {
    ratio: number;
    foreground: Rgba;
    /** Opaque: the background itself, or the background composited over the pair's `over`. */
    background: Rgba;
}

/**
 * A pair's contrast in a theme, or the reason it cannot be taken. A ratio needs an opaque background: a translucent one
 * is composited over the role its pair names, `over`, as the browser composites it, and with no `over` it is refused.
 * An `over` is read whenever a pair names one, and must be opaque itself.
 */
function measurePair(tokens: Tokens, pair: ContrastPair, theme: Theme): Contrast | string {
    const foreground = colourOf(tokens, `var(${pair.foreground})`, theme);
    if (typeof foreground === 'string') return foreground;
    let background = colourOf(tokens, `var(${pair.background})`, theme);
    if (typeof background === 'string') return background;
    if (pair.over !== undefined) {
        const under = colourOf(tokens, `var(${pair.over})`, theme);
        if (typeof under === 'string') return under;
        if (under.alpha < OPAQUE) return `${pair.over}, under the background, is translucent (${shown(under)}), and a composite needs an opaque one`;
        background = over(background, under);
    }
    if (background.alpha < OPAQUE) return `the background is translucent (${shown(background)}), and a ratio needs an opaque one`;
    return {ratio: contrastRatio(foreground, background), foreground, background};
}

describe('tokens.css: contrast in both themes (C3)', () => {
    it('measures contrast the WCAG way, composites a translucent colour and mixes in OKLab (positive control)', () => {
        const tokens = readTokens();
        const colour = (expression: string): Rgba => resolveColour(tokens, expression, 'light');
        expect(contrastRatio(colour('#000000'), colour('#ffffff'))).toBeCloseTo(21, 5);
        // The classic threshold: #767676 is the lightest grey that reaches 4.5:1 on white, #777777 already falls short.
        expect(contrastRatio(colour('#767676'), colour('#ffffff'))).toBeCloseTo(4.54, 2);
        expect(contrastRatio(colour('#777777'), colour('#ffffff'))).toBeLessThan(TEXT);
        expect(contrastRatio(colour('transparent'), colour('#ffffff')), 'transparent text on white is white').toBeCloseTo(1, 5);
        expect(toHex(colour('color-mix(in oklab, #000000 50%, #ffffff)')), 'the OKLab midpoint of black and white, not the sRGB #808080').toBe('#636363');
        const veil = colour('color-mix(in oklab, #ff0000 40%, transparent)');
        expect(toHex(veil), 'a mix with transparent keeps the colour').toBe('#ff0000');
        expect(veil.alpha, 'and scales its alpha').toBeCloseTo(0.4, 10);
    });

    it('composites a translucent background over the opaque role its pair names, and refuses one with none (positive control)', () => {
        const sample = parseTokens(':root,\nhtml.light,\n.light {\n    --lf-white: #ffffff;\n    --lf-veil: color-mix(in oklab, #000000 50%, transparent);\n}\n');
        const veiled: ContrastPair = {foreground: '--lf-white', background: '--lf-veil', min: TEXT};
        expect(measurePair(sample, {...veiled, over: '--lf-white'}, 'light'), 'half a black veil over white: the opaque mid grey #808080, composited in sRGB as the browser does — not the OKLab #636363 of a mix').toEqual({
            ratio: expect.closeTo(3.977, 3),
            foreground: {r: 1, g: 1, b: 1, alpha: 1},
            background: {r: 0.5, g: 0.5, b: 0.5, alpha: 1},
        });
        expect(measurePair(sample, veiled, 'light'), 'the same veil with nothing under it is refused, as before').toBe('the background is translucent (#000000 at 50%), and a ratio needs an opaque one');
        expect(measurePair(sample, {...veiled, over: '--lf-veil'}, 'light'), 'nor can it lie on another veil').toBe('--lf-veil, under the background, is translucent (#000000 at 50%), and a composite needs an opaque one');
        expect(measurePair(sample, {...veiled, over: '--lf-ghost'}, 'light'), 'nor on a role that does not exist').toBe('tokens.css: --lf-ghost is not declared for the light theme');
    });

    it('C3: every text pair reaches 4.5:1 and every non-text pair 3:1, in both themes', () => {
        const tokens = readTokens();
        const excepted = new Set(KNOWN_EXCEPTIONS.map((entry) => pairName(entry.theme, entry)));
        const failures: string[] = [];
        for (const theme of THEMES) {
            for (const pair of CONTRAST_PAIRS) {
                const name = pairName(theme, pair);
                const contrast = measurePair(tokens, pair, theme);
                if (typeof contrast === 'string') failures.push(`${name}: ${contrast}`);
                else if (contrast.ratio < pair.min && !excepted.has(name)) failures.push(`${name}: ${ratioText(contrast.ratio)}:1 < ${pair.min}:1  (${shown(contrast.foreground)} on ${shown(contrast.background)})`);
            }
        }
        const rule = 'Each pair is a promise of the roles: change the value of a role (the designer confirms it), never the pair list. A pair kept under its minimum is her decision, in KNOWN_EXCEPTIONS.';
        expect(failures, ['', rule, '', ...failures, ''].join('\n  ')).toEqual([]);
    });

    it('C3: CONTRAST_PAIRS lists each pair once', () => {
        const names = CONTRAST_PAIRS.map(pairText);
        const twice = names.filter((name, index) => names.indexOf(name) !== index);
        expect(twice, 'a pair listed twice makes two promises, possibly at two minimums, and KNOWN_EXCEPTIONS can only answer the first: keep the stricter one').toEqual([]);
    });

    it('C3: KNOWN_EXCEPTIONS holds only pairs still under their minimum, each with a reason', () => {
        const tokens = readTokens();
        const isStale = (entry: KnownException): boolean => {
            const pair = CONTRAST_PAIRS.find((candidate) => candidate.foreground === entry.foreground && candidate.background === entry.background && candidate.over === entry.over);
            if (pair === undefined) return true;
            const contrast = measurePair(tokens, pair, entry.theme);
            return typeof contrast === 'string' || contrast.ratio >= pair.min;
        };
        const stale = KNOWN_EXCEPTIONS.filter(isStale).map((entry) => pairName(entry.theme, entry));
        expect(stale, ['', 'These exceptions no longer match a pair under its minimum: delete them.', '', ...stale, ''].join('\n  ')).toEqual([]);
        expect(
            KNOWN_EXCEPTIONS.filter((entry) => entry.reason.trim().length < 20).map((entry) => pairName(entry.theme, entry)),
            'an exception carries the reason of the designer and its date',
        ).toEqual([]);
    });
});

// ---------------------------------------------------------------------------
// C3: the backdrop, one colour in both themes
// ---------------------------------------------------------------------------

/** The backdrop of the modals: the translucent role the text on it, --lf-on-overlay, is measured over. */
const BACKDROP = '--lf-surface-overlay';

/**
 * C3: what keeps the backdrop from being one colour in both themes — a theme that cannot read it, or two themes that
 * read two colours. The on-overlay pairs are sound only while it is one: a dark-theme backdrop may lie on a white
 * image, and the light theme's composite over its white field stands for that case only if the two backdrops are the
 * same. C1 lets the dark block override a derived role, and a derived role may read one that follows the theme: either
 * would part the two in silence. Colours are compared as this file shows them, `#rrggbb` and the alpha, after `var()`
 * and `color-mix()` are resolved: the same colour written two ways is one colour.
 */
function backdropFindings(tokens: Tokens): string[] {
    const out: string[] = [];
    const read: Partial<Record<Theme, Rgba>> = {};
    for (const theme of THEMES) {
        const colour = colourOf(tokens, `var(${BACKDROP})`, theme);
        if (typeof colour === 'string') out.push(`${theme}  ${BACKDROP}: ${colour}`);
        else read[theme] = colour;
    }
    const {light, dark} = read;
    if (light && dark && shown(light) !== shown(dark)) out.push(`${BACKDROP} is ${shown(light)} in light, ${shown(dark)} in dark`);
    return out;
}

/** Three blocks with a backdrop derived once for both themes, as tokens.css writes it, and what the dark block may add to it. */
const backdropTable = (derived: string, darkOverride?: string): string => `
:root,
html.light,
.light {
    --lf-surface-page: #f3f5f3;
}

:root,
.light,
.dark {
    --lf-surface-overlay: ${derived};
}

html.dark,
.dark {
    --lf-surface-page: #0d1110;${darkOverride === undefined ? '' : `\n    --lf-surface-overlay: ${darkOverride};`}
}
`;

describe('tokens.css: the backdrop is one colour in both themes (C3)', () => {
    it('finds a backdrop that parts the two themes, overridden by the dark block or derived from a role that follows the theme, and passes one colour written twice (positive control)', () => {
        const DERIVED = 'color-mix(in oklab, #0d1110 60%, transparent)';
        const findings = (derived: string, darkOverride?: string): string[] => backdropFindings(parseTokens(backdropTable(derived, darkOverride)));
        expect(findings(DERIVED), 'derived once for both themes').toEqual([]);
        expect(findings(DERIVED, 'color-mix(in oklab, #0D1110 60%, transparent)'), 'the dark block overrides it with the same colour, in upper case').toEqual([]);
        expect(findings(DERIVED, 'color-mix(in oklab, #000000 50%, transparent)'), 'the dark block overrides it with another colour, the likeliest slip').toEqual(['--lf-surface-overlay is #0d1110 at 60% in light, #000000 at 50% in dark']);
        expect(findings('color-mix(in oklab, var(--lf-surface-page) 60%, transparent)'), 'derived from a role that follows the theme').toEqual(['--lf-surface-overlay is #f3f5f3 at 60% in light, #0d1110 at 60% in dark']);
        expect(findings(DERIVED, 'rgb(0 0 0 / 60%)'), 'a form the resolver cannot read').toEqual(['dark  --lf-surface-overlay: tokens.css: cannot resolve «rgb(0 0 0 / 60%)»']);
    });

    it('C3: the backdrop, --lf-surface-overlay, is one colour in both themes: the pairs of the text on it rest on that', () => {
        expect(CONTRAST_PAIRS.filter((pair) => pair.background === BACKDROP).map(pairText), 'positive control: the pairs this premise holds up are in CONTRAST_PAIRS').toContain('--lf-on-overlay on --lf-surface-overlay over --lf-surface-field');
        const findings = backdropFindings(readTokens());
        const rule = 'The backdrop is one colour in both themes: a dark-theme backdrop may lie on a white image, and the light composite over the white field stands for that case only then. Change it in the derived block, for both themes at once; never in the dark block.';
        expect(findings, ['', rule, '', ...findings, ''].join('\n  ')).toEqual([]);
    });
});

// ---------------------------------------------------------------------------
// Q10: inside the inverted tooltip, the other theme's colour
// ---------------------------------------------------------------------------

/** A role of the inverted tooltip: `--lf-danger-on-inverse` names `danger`, and the rule pairs it with `--lf-danger`. */
const ON_INVERSE = /^--lf-([a-z0-9]+(?:-[a-z0-9]+)*)-on-inverse$/;

/** The tooltip's own text, the card colour on the inverted surface (`var(--lf-surface-card)`): no other theme's role, the one role of the family the rule leaves out. */
const INVERSE_TEXT = '--lf-text-on-inverse';

/** The base roles of the rule — `<X>` for every `--lf-<X>-on-inverse` the light, the derived or the dark block declares — once each, in the order of the file. */
function inverseBases(tokens: Tokens): string[] {
    const out: string[] = [];
    for (const name of declaredRoles(tokens)) {
        const base = ON_INVERSE.exec(name)?.[1];
        if (base !== undefined && name !== INVERSE_TEXT) out.push(base);
    }
    return out;
}

/**
 * Q10: what keeps a role of the inverted tooltip from being, in each theme, the colour the other theme gives its base
 * role. Colours are compared as this file shows them — `#rrggbb` in lower case, so `#F59E0B` is `#f59e0b`, and the alpha
 * when there is one — after `var()` and `color-mix()` are resolved, never as they are written.
 */
function inverseFindings(tokens: Tokens): string[] {
    const out: string[] = [];
    for (const theme of THEMES) {
        const other: Theme = theme === 'light' ? 'dark' : 'light';
        for (const base of inverseBases(tokens)) {
            const role = `--lf-${base}-on-inverse`;
            const inverse = colourOf(tokens, `var(${role})`, theme);
            const twin = colourOf(tokens, `var(--lf-${base})`, other);
            if (typeof inverse === 'string') out.push(`${theme}  ${role}: ${inverse}`);
            else if (typeof twin === 'string') out.push(`${theme}  ${role}: ${twin}`);
            else if (shown(inverse) !== shown(twin)) out.push(`${theme}  ${role} is ${shown(inverse)}, the ${other} --lf-${base} ${shown(twin)}`);
        }
    }
    return out;
}

/**
 * Three blocks with a role of the rule in every state the check tells apart: the warning right in both themes, once in
 * upper case; the danger left at its own theme's colour in light, the likeliest slip; the info wrong in dark alone; the
 * muted text derived from its own theme's base, wrong in both; a role whose base no block declares; and the tooltip
 * text, which the rule leaves out.
 */
const INVERSE_SAMPLE = `
:root,
html.light,
.light {
    --lf-surface-card: #fafbfa;
    --lf-text-muted: #616d67;
    --lf-warning: #ae4e00;
    --lf-warning-on-inverse: #F59E0B;
    --lf-danger: #c82838;
    --lf-danger-on-inverse: #c82838;
    --lf-info: #155eef;
    --lf-info-on-inverse: #3f86fa;
    --lf-ghost-on-inverse: #ffffff;
}

:root,
.light,
.dark {
    --lf-text-on-inverse: var(--lf-surface-card);
    --lf-text-muted-on-inverse: var(--lf-text-muted);
}

html.dark,
.dark {
    --lf-surface-card: #151b19;
    --lf-text-muted: #7f8c87;
    --lf-warning: #f59e0b;
    --lf-warning-on-inverse: #ae4e00;
    --lf-danger: #ff7a86;
    --lf-danger-on-inverse: #c82838;
    --lf-info: #3f86fa;
    --lf-info-on-inverse: #3f86fa;
    --lf-ghost-on-inverse: #000000;
}
`;

describe("tokens.css: inside the inverted tooltip, the other theme's colour (Q10)", () => {
    it("finds every -on-inverse role that is not the other theme's colour, and leaves the tooltip text out (positive control)", () => {
        const sample = parseTokens(INVERSE_SAMPLE);
        expect(inverseBases(sample), 'found by name in every block, the derived one included; --lf-text-on-inverse left out').toEqual(['warning', 'danger', 'info', 'ghost', 'text-muted']);
        expect(inverseFindings(sample), 'the warning, the dark danger and the light info are right: #F59E0B is #f59e0b').toEqual([
            'light  --lf-danger-on-inverse is #c82838, the dark --lf-danger #ff7a86',
            'light  --lf-ghost-on-inverse: tokens.css: --lf-ghost is not declared for the dark theme',
            'light  --lf-text-muted-on-inverse is #616d67, the dark --lf-text-muted #7f8c87',
            'dark  --lf-info-on-inverse is #3f86fa, the light --lf-info #155eef',
            'dark  --lf-ghost-on-inverse: tokens.css: --lf-ghost is not declared for the light theme',
            'dark  --lf-text-muted-on-inverse is #7f8c87, the light --lf-text-muted #616d67',
        ]);
    });

    it("Q10: every -on-inverse role but the tooltip text is, in each theme, the other theme's base role", () => {
        const tokens = readTokens();
        expect(inverseBases(tokens), 'positive control: the rule reaches the roles of the tooltip, found by their name').toEqual(expect.arrayContaining(['warning', 'danger', 'info', 'text-muted']));
        const findings = inverseFindings(tokens);
        const rule = "Inside the inverted tooltip a role reads the other theme's colour (Q10, D-T27): --lf-<X>-on-inverse is, in each theme, the other theme's --lf-<X>. Change a base role and the -on-inverse role of the other theme together.";
        expect(findings, ['', rule, '', ...findings, ''].join('\n  ')).toEqual([]);
    });
});

// ---------------------------------------------------------------------------
// app.css: the legacy dark remap
// ---------------------------------------------------------------------------

/** The comma-separated parts of a selector list, outside parentheses, brackets and quotes. */
function splitSelectors(list: string): string[] {
    const parts: string[] = [];
    let depth = 0;
    let quote: string | null = null;
    let start = 0;
    for (let i = 0; i < list.length; i++) {
        const c = list[i];
        if (quote) {
            if (c === '\\') i++;
            else if (c === quote) quote = null;
        } else if (c === '"' || c === "'") quote = c;
        else if (c === '(' || c === '[') depth++;
        else if (c === ')' || c === ']') depth--;
        else if (c === ',' && depth === 0) {
            parts.push(list.slice(start, i));
            start = i + 1;
        }
    }
    parts.push(list.slice(start));
    return parts.map((part) => part.trim().replace(/\s+/g, ' ')).filter(Boolean);
}

/** Every selector of a stylesheet, comments blanked: the parts of each prelude that opens a block, at-rules left out. */
function selectorsOf(css: string): string[] {
    return [...blankCssComments(css).matchAll(/([^{};]*)\{/g)]
        .map((match) => match[1].trim())
        .filter((prelude) => prelude !== '' && !prelude.startsWith('@'))
        .flatMap(splitSelectors);
}

/** A selector without what its parentheses and brackets hold: `option:where(…)` reads `option:where`. */
function bare(selector: string): string {
    let previous = '';
    let current = selector;
    while (current !== previous) {
        previous = current;
        current = current.replace(/\([^()]*\)/g, '').replace(/\[[^[\]]*\]/g, '');
    }
    return current;
}

/** What each `:where(…)` of a selector holds, nested parentheses included. */
function whereArguments(selector: string): string[] {
    const out: string[] = [];
    for (let at = selector.indexOf(':where('); at !== -1; at = selector.indexOf(':where(', at + 1)) {
        const open = at + ':where'.length;
        let depth = 0;
        for (let i = open; i < selector.length; i++) {
            if (selector[i] === '(') depth++;
            else if (selector[i] === ')' && --depth === 0) {
                out.push(selector.slice(open + 1, i));
                break;
            }
        }
    }
    return out;
}

/** A selector that targets a field, its placeholder, an option or a rounded container. */
const STRUCTURAL = /(?:^|[\s>+~])(?:input|select|textarea|option)(?![\w-])|\.rounded-(?:xl|2xl)(?![\w-])/;

/** The structural selectors of the legacy dark remap, and those among them that do not exempt an element with a role utility. */
function remapExemptions(css: string): {structural: string[]; unexempt: string[]} {
    const structural = selectorsOf(css).filter((selector) => /^html\.dark(?![\w-])/.test(selector) && STRUCTURAL.test(bare(selector)));
    return {structural, unexempt: structural.filter((selector) => !whereArguments(selector).some((argument) => argument.includes('-lf-')))};
}

/** A remap with one structural rule of every kind, exempt or not, and the rules the check must leave alone. */
const REMAP_SAMPLE = `
html.dark input,
html.dark select:where(:not([class*='-lf-'])) {
    border-color: #546175;
}

html.dark .rounded-xl {
    border-color: #334155;
}

html.dark option:where(:not(select[class*='-lf-'] option)) {
    color: #f8fafc;
}

html.dark textarea:where(.compact)::placeholder {
    color: #64748b;
}

html.dark .bg-white {
    background-color: #1e293b !important;
}

@media (max-width: 768px) {
    input:not(.zoom-guard-exempt) {
        font-size: 16px !important;
    }
}

/* html.dark select { color: red; } */
`;

describe('app.css: the legacy dark remap leaves the migrated elements alone', () => {
    const appCss = readFileSync(APP_CSS, 'utf8');

    it('finds the structural rules of a remap, and the ones that do not exempt a role utility (positive control)', () => {
        const {structural, unexempt} = remapExemptions(REMAP_SAMPLE);
        expect(structural).toEqual(['html.dark input', "html.dark select:where(:not([class*='-lf-']))", 'html.dark .rounded-xl', "html.dark option:where(:not(select[class*='-lf-'] option))", 'html.dark textarea:where(.compact)::placeholder']);
        expect(unexempt).toEqual(['html.dark input', 'html.dark .rounded-xl', 'html.dark textarea:where(.compact)::placeholder']);
    });

    it('every rule of the remap on a field, a placeholder, an option or a rounded container exempts the elements with a role utility', () => {
        const {structural, unexempt} = remapExemptions(appCss);
        expect(structural.length, 'positive control: the structural rules of the remap are found — when the clean-up (B6) removes them, this check goes with them').toBeGreaterThan(0);
        const rule = "A migrated element must escape the legacy remap whole: the selector carries :where(:not([class*='-lf-'])) — for an option, :where(:not(select[class*='-lf-'] option)) — which keeps its specificity unchanged.";
        expect(unexempt, ['', rule, '', ...unexempt, ''].join('\n  ')).toEqual([]);
    });

    it('app.css imports tokens.css', () => {
        expect(blankCssComments(appCss), "app.css must import './lib/theme/tokens.css': without it no role utility exists").toMatch(/@import\s+(['"])\.\/lib\/theme\/tokens\.css\1\s*;/);
    });
});

// ---------------------------------------------------------------------------
// C4: the dead rules of the remap
// ---------------------------------------------------------------------------

describe('app.css: every class the legacy remap rewrites is still in use (C4)', () => {
    let tree = '';

    // A tree of two files, for the positive control of classUses.
    beforeAll(() => {
        tree = mkdtempSync(join(tmpdir(), 'lf-theme-c4-'));
        mkdirSync(join(tree, 'lib', 'components'), {recursive: true});
        const component = `<script>
    const active = 'bg-white';
    // bg-white, in a comment
</script>

<div class="dark:bg-white hover:bg-white bg-white/90 md:bg-white"></div>
<div class:bg-white={active}></div>
<!-- <div class="bg-white bg-gray-50"></div> -->
`;
        writeFileSync(join(tree, 'lib', 'components', 'Sample.svelte'), component);
        writeFileSync(join(tree, 'lib', 'components', 'Sample.test.ts'), "export const ignored = 'bg-gray-50';\n");
    });

    afterAll(() => {
        if (tree) rmSync(tree, {recursive: true, force: true});
    });

    it('reads the classes of the remap, escapes decoded and comments ignored (positive control)', () => {
        const css = "html.dark .bg-white,\nhtml.dark .hover\\:bg-gray-100:hover,\nhtml.dark .bg-white\\/90 {\n    color: red;\n}\n\nhtml.dark input:where(:not([class*='-lf-'])) {\n    color: red;\n}\n\n/* html.dark .bg-dead { color: red; } */\n";
        expect(p1Classes(css)).toEqual(['bg-white', 'bg-white/90', 'hover:bg-gray-100']);
    });

    it('counts the class itself: not a variant of it, not a comment, not a test (positive control)', () => {
        const uses = Object.fromEntries(['bg-white', 'bg-white/90', 'hover:bg-white', 'bg-gray-50'].map((name) => [name, classUses(name, tree)]));
        expect(uses, 'bg-white: the script string and the class: directive; dark:, hover:, md: and /90 are other classes').toEqual({'bg-white': 2, 'bg-white/90': 1, 'hover:bg-white': 1, 'bg-gray-50': 0});
    });

    // classUses walks every production source once per class: about thirty walks of the tree.
    it('C4: every class the remap rewrites has a use left in the production sources', () => {
        const classes = p1Classes();
        expect(classes.length, 'positive control: the classes of the remap are read from src/app.css').toBeGreaterThan(0);
        const dead = classes.filter((name) => classUses(name) === 0);
        const rule = 'These classes have no use left: delete their rules from src/app.css in the change that removed the last use. The legacy remap only ever shrinks.';
        expect(dead, ['', rule, '', ...dead, ''].join('\n  ')).toEqual([]);
    }, 120_000);
});
