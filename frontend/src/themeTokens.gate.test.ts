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
 *       (today the designer's password box: `--lf-success-soft`, `--lf-success-line`, `--lf-success-on-soft`), but
 *       never declares a role of its own; and no role is both base and derived;
 *   C2  every utility of the table is `--color-lf-<name>: var(--lf-…)` of a role declared in the light or the
 *       derived block; every name is distinct; every utility resolves to a colour in both themes — and so does every
 *       role of the light, derived and dark blocks, utility or not, the tint recipe excepted (`--lf-tint-*`, the
 *       shares of a mix: `8%`). The login illustration (`--lf-art-*`) has no utility: its one component reads it
 *       with var(), where nothing but this check would see a role that does not resolve;
 *   C3  the pairs of `CONTRAST_PAIRS` reach their minimum in both themes: 4.5:1 for text (WCAG 1.4.3), 3:1 for the
 *       border of a field, the focus ring and a status mark on its own tint (WCAG 1.4.11). A pair under its minimum
 *       is red unless `KNOWN_EXCEPTIONS` holds it, and an entry there is the designer's decision, not ours;
 *   C4  every class the legacy remap rewrites (`html.dark .bg-white` …) is still written by a production source: a
 *       rule whose class lost its last use is dead, and leaves app.css in the change that removed that use.
 * And app.css imports tokens.css, and every rule of the remap that targets a field (`input`, `select`, `textarea`),
 * its placeholder, an `option` or a rounded container (`.rounded-xl`, `.rounded-2xl`) carries the `:where(…)` that
 * exempts the elements with a role utility (`-lf-` in their classes).
 *
 * ## How it reads, and what it cannot see
 *
 * Colours come from the module's resolver, which reads the forms tokens.css uses — a hex, `transparent`, `var(--…)`,
 * `color-mix(in oklab, A p, B)` — and mixes as CSS Color 5 does (OKLab, premultiplied alpha). A new form fails C2
 * loudly before it could fail C3 in silence. Contrast is computed on the declared values, not on the page: an
 * opacity utility (`text-lf-muted/70`), a translucent layer, a gradient or an image behind the text are invisible
 * here, and a pair missing from `CONTRAST_PAIRS` is not checked at all — a new role that carries text or draws a
 * control adds its pairs in the same change. The pairs are the floor; the gallery and the designer's review do the
 * rest. C4 counts the class written whole in a production source (`classUses`): a class assembled at run time
 * (`` `bg-gray-${n}` ``) is no use, and a string that merely spells the class is one.
 *
 * Registered in `front_utility_unit` (`scripts/test_runner/_frontend_utility.py`, action `core-unit`).
 */

import {afterAll, beforeAll, describe, expect, it} from 'vitest';
import {mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {APP_CSS, TOKEN_BLOCKS, blankCssComments, classUses, contrastRatio, p1Classes, parseTokens, readTokens, resolveColour, roleNames, toHex} from '../scripts/theme/theme-roles.mjs';

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

/** Four blocks with one fault of every kind C1 and C2 look for — and a tint share, which is no colour and no fault. */
const FAULTY_TOKENS = `
:root,
html.light,
.light {
    --lf-a: #ffffff;
    --lf-b: #000000;
    --lf-tint-a: 8%;
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
    --lf-tint-a: 6%;
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

/** The tint recipe: `--lf-tint-*` are the shares the status tints are mixed with (`8%`), the one family of roles that is no colour. */
const TINT_RECIPE = '--lf-tint-';

/** Every role tokens.css declares, in the light, the derived or the dark block: once each, in the order of the file. */
const declaredRoles = (tokens: Tokens): string[] => [...new Set([...tokens.light.keys(), ...tokens.derived.keys(), ...tokens.dark.keys()])];

/** C2: what keeps a role — named by a utility or read by var() alone, the tint recipe excepted — from being a colour in a theme. */
function roleFindings(tokens: Tokens): string[] {
    const out: string[] = [];
    for (const theme of THEMES) {
        for (const name of declaredRoles(tokens)) {
            if (name.startsWith(TINT_RECIPE)) continue;
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
        expect(roleFindings(faulty), 'a role no utility names is read all the same (the typo of --lf-art-a), and the tint share is left out').toEqual([
            'light  --lf-art-a: tokens.css: --lf-brnad is not declared for the light theme',
            'light  --lf-z: tokens.css: --lf-z is not declared for the light theme',
        ]);
        expect(typeof colourOf(faulty, 'var(--lf-tint-a)', 'light'), 'a tint share is not a colour: TINT_RECIPE alone keeps it out of the findings').toBe('string');
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

    it('C2: every role resolves to a colour in both themes, utility or not — the tint recipe excepted', () => {
        const tokens = readTokens();
        const named = new Set(tokens.utilities.values());
        const readByVarAlone = declaredRoles(tokens).filter((name) => !named.has(`var(${name})`) && !name.startsWith(TINT_RECIPE));
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
const SURFACES = ['surface-app', 'surface-page', 'surface-card', 'surface-panel', 'surface-field'];

interface ContrastPair {
    foreground: string;
    background: string;
    min: number;
}

/** Every foreground on every background, as role variables: `--lf-text-muted` on `--lf-surface-panel`. */
const pairs = (foregrounds: string[], backgrounds: string[], min: number): ContrastPair[] => foregrounds.flatMap((foreground) => backgrounds.map((background) => ({foreground: `--lf-${foreground}`, background: `--lf-${background}`, min})));

/**
 * What the roles promise, in both themes. Text reaches 4.5:1 (WCAG 1.4.3) on every surface it is set on; the border
 * of a field, the focus ring and a status mark on its own tint reach 3:1 (WCAG 1.4.11).
 */
const CONTRAST_PAIRS: readonly ContrastPair[] = [
    ...pairs(['text-primary', 'text-secondary', 'text-muted', 'text-placeholder'], SURFACES, TEXT),
    ...pairs(['link'], ['surface-app', 'surface-page', 'surface-card', 'surface-panel'], TEXT),
    ...pairs(STATUSES, SURFACES, TEXT),
    ...pairs(['donate'], ['surface-app', 'surface-page'], TEXT),
    ...STATUSES.flatMap((status) => pairs([`${status}-on-soft`, 'text-muted', 'text-primary'], [`${status}-soft`], TEXT)),
    ...pairs(['on-brand'], ['brand'], TEXT),
    ...pairs(['on-action'], ['action', 'action-hover'], TEXT),
    ...pairs(['on-status'], STATUSES, TEXT),
    ...pairs(['text-on-inverse'], ['surface-inverse'], TEXT),
    ...pairs(['border-input'], SURFACES, NON_TEXT),
    ...pairs(['focus'], ['surface-app', 'surface-card', 'surface-panel', 'surface-field'], NON_TEXT),
    ...STATUSES.flatMap((status) => pairs([status], [`${status}-soft`], NON_TEXT)),
];

interface KnownException {
    theme: Theme;
    foreground: string;
    background: string;
    /** The designer's decision and its date: why the pair stays under its minimum. */
    reason: string;
}

/**
 * Pairs that stay under their minimum on purpose: NONE. An entry is the designer's decision, never a way to turn the
 * gate green — record her reason and the date. An entry whose pair reaches its minimum again is stale, and fails.
 */
const KNOWN_EXCEPTIONS: readonly KnownException[] = [];

const pairName = (theme: Theme, pair: {foreground: string; background: string}): string => `${theme}  ${pair.foreground} on ${pair.background}`;

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

    it('C3: every text pair reaches 4.5:1 and every non-text pair 3:1, in both themes', () => {
        const tokens = readTokens();
        const excepted = new Set(KNOWN_EXCEPTIONS.map((entry) => pairName(entry.theme, entry)));
        const failures: string[] = [];
        for (const theme of THEMES) {
            for (const pair of CONTRAST_PAIRS) {
                const name = pairName(theme, pair);
                const foreground = colourOf(tokens, `var(${pair.foreground})`, theme);
                const background = colourOf(tokens, `var(${pair.background})`, theme);
                if (typeof foreground === 'string') {
                    failures.push(`${name}: ${foreground}`);
                    continue;
                }
                if (typeof background === 'string') {
                    failures.push(`${name}: ${background}`);
                    continue;
                }
                if (background.alpha < OPAQUE) {
                    failures.push(`${name}: the background is translucent (${shown(background)}), and a ratio needs an opaque one`);
                    continue;
                }
                const ratio = contrastRatio(foreground, background);
                if (ratio < pair.min && !excepted.has(name)) failures.push(`${name}: ${ratioText(ratio)}:1 < ${pair.min}:1  (${shown(foreground)} on ${shown(background)})`);
            }
        }
        const rule = 'Each pair is a promise of the roles: change the value of a role (the designer confirms it), never the pair list. A pair kept under its minimum is her decision, in KNOWN_EXCEPTIONS.';
        expect(failures, ['', rule, '', ...failures, ''].join('\n  ')).toEqual([]);
    });

    it('C3: KNOWN_EXCEPTIONS holds only pairs still under their minimum, each with a reason', () => {
        const tokens = readTokens();
        const isStale = (entry: KnownException): boolean => {
            const pair = CONTRAST_PAIRS.find((candidate) => candidate.foreground === entry.foreground && candidate.background === entry.background);
            const foreground = colourOf(tokens, `var(${entry.foreground})`, entry.theme);
            const background = colourOf(tokens, `var(${entry.background})`, entry.theme);
            return pair === undefined || typeof foreground === 'string' || typeof background === 'string' || contrastRatio(foreground, background) >= pair.min;
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
