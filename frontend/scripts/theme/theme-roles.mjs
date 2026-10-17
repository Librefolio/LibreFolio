#!/usr/bin/env node
// @ts-check
/**
 * Theme roles — the scanner behind the colour gates of workstream T (colour programme, decision D-T8).
 *
 * The interface moves, component by component, from Tailwind palette classes and hand-written colours to the colour
 * roles of src/lib/theme/tokens.css (bg-lf-card, text-lf-muted…). This module measures what is left of the old way,
 * guards the new one and keeps the ratchet's baseline. The gates call it (src/themeRoles.gate.test.ts,
 * src/themeTokens.gate.test.ts), and so does the command line at the bottom.
 *
 * Measured in every production source of frontend/src (*.svelte, *.ts, *.js; not the tests, the generated API, the
 * Designer Lab — and never inside a comment):
 *   m1  legacy colour classes, counted: a palette colour with its shade (gray-200), white/black, libre-*, primary-*,
 *       surface-*, under any colour utility (bg, text, border, ring, divide, fill, stroke, from/via/to, placeholder…);
 *   m2  colour literals, as a multiset of normalized values: hex; rgb(), rgba(), hsl(), hsla(), oklch(), oklab(), lab(),
 *       lch(), hwb(); a CSS colour name in a style value or an SVG colour attribute; a colour name as a whole script
 *       string. A colour function built on var() or ${…} alone is not a literal. lib/theme/**, where colours live, is
 *       not measured, and LITERAL_EXCEPTIONS lists the literals that stay.
 *
 * The ratchet, against BASELINE (one line per file: formatBaseline):
 *   R1  the total of each metric never rises;
 *   R2  a file never rises: its m1 never grows and its m2 values stay among the recorded ones, so that swapping one
 *       colour for another is caught. The central tables of lib/theme/** may take in m1 classes moved there, R1
 *       holding;
 *   R3  a new file starts empty, unless it is under lib/theme/** or a declared split (--split) gave it a record;
 *   R4  a file that left the tree pairs with a new file of the same name: a move or a rename keeps its record;
 *   R5  a drop passes and is reported; --update tightens the baseline to it and never widens it.
 *
 * The grammar of the roles, in the same sources:
 *   G1  no `dark:` on a role utility: the role changes value with the theme;
 *   G2  every role utility is in the @theme inline table of tokens.css: Tailwind silently drops an unknown class;
 *   G3  no element and no class string mixes role utilities with legacy classes: app.css exempts from its legacy dark
 *       remap every element carrying a role utility, so a half-migrated element would keep half of its old colours;
 *   G4  no arbitrary colour value (bg-[#…], ring-[rgb(…)]) unless it reads roles only (var(--lf-…)) or its file is in
 *       ARBITRARY_ALLOWED;
 *   G5  one property, one ternary: no element sets one colour utility twice with the same variants (bg-lf-card and
 *       bg-lf-hover), one of the two always on. Tailwind 4 emits two such utilities by name, so the later name wins
 *       whatever the condition says: the idle colour and the state colour are the two branches of one ternary. Read
 *       through the element's `class`, its `{…}` and `${…}` (a branching one is a condition, `?`, `&&`, `||`, `??`), its
 *       `class:` directives and the UPPER_CASE string constants it names, the file's own and those it imports;
 *   G6  a native field on roles names its text: an <input> with a text of its own, a <textarea> and a <select> that
 *       carry a role utility write a base text role, and a placeholder role when they have a placeholder. app.css
 *       colours the text and the placeholder of native fields only while they carry no role utility (`-lf-`), so a
 *       migrated field would fall back to the preflight: the inherited colour, the placeholder at half of it.
 *
 * Command line, from any directory; files are named by their path under frontend/src:
 *   node frontend/scripts/theme/theme-roles.mjs --report                  what is left, and where; ratchet and grammar
 *   node frontend/scripts/theme/theme-roles.mjs --check                   the gates' verdict; exit 1 on a violation
 *   node frontend/scripts/theme/theme-roles.mjs --update                  tighten the baseline to what dropped
 *   node frontend/scripts/theme/theme-roles.mjs --split OLD:NEW1,NEW2     declare that OLD was split into NEW1, NEW2…
 *   node frontend/scripts/theme/theme-roles.mjs --resolve                 settle a merge conflict on the baseline
 *   node frontend/scripts/theme/theme-roles.mjs --accept FILE --reason R  take FILE as it is (colour coordinator only)
 *   node frontend/scripts/theme/theme-roles.mjs --init                    write the first baseline
 */

import {execFileSync} from 'node:child_process';
import {existsSync, readdirSync, readFileSync, writeFileSync} from 'node:fs';
import {basename, dirname, join, posix, relative, resolve, sep} from 'node:path';
import {fileURLToPath} from 'node:url';

/** `frontend/`. */
export const FRONTEND_DIR = resolve(dirname(fileURLToPath(import.meta.url)), '..', '..');
export const SRC_DIR = join(FRONTEND_DIR, 'src');
export const TOKENS_CSS = join(SRC_DIR, 'lib', 'theme', 'tokens.css');
export const APP_CSS = join(SRC_DIR, 'app.css');
export const BASELINE = join(SRC_DIR, 'themeRoles.baseline.tsv');

/** Where colours are defined rather than used: the central tables of the colour programme. */
export const CENTRAL_PREFIX = 'lib/theme/';

/** The Designer Lab (workstream L), a debug tool with colours of its own. */
export const LAB_PREFIXES = ['lib/dev/designer-lab/', 'routes/designer-lab/'];

/**
 * Colour literals that stay, and why: m2 does not count them. `value` is a normalized literal or a pattern of them.
 * @type {ReadonlyArray<{file: string, value: string | RegExp, reason: string}>}
 */
export const LITERAL_EXCEPTIONS = [
    {file: 'lib/features/brokers/lots/lotComparisonChartHelpers.ts', value: /^hsla?\(.*\$\{/, reason: "lotColor: an hsl() generated from the lot's id (R)"},
    {file: 'lib/utils/colors.ts', value: /^hsla?\(.*\$\{/, reason: 'hsl() and hsla() generators with a computed hue (R)'},
    {file: 'lib/components/charts/ChartSettingsModal.svelte', value: '#000000', reason: 'the colour of a demo signal, never drawn (R)'},
    {file: 'lib/components/assets/AssetDataEditorSection.svelte', value: '#a855f7', reason: 'the colour of the preview line (R-6)'},
    {file: 'lib/components/fx/FxDataEditorSection.svelte', value: '#a855f7', reason: 'the colour of the preview line (R-6)'},
    {file: 'lib/features/support/supportLinks.ts', value: /^#/, reason: 'the brand colours of Reddit, Facebook, Instagram and TikTok on their share buttons: not ours to theme'},
];

/**
 * Files whose arbitrary colour values (G4) are allowed, and why.
 * @type {Readonly<Record<string, string>>}
 */
export const ARBITRARY_ALLOWED = {
    'lib/features/support/supportLinks.ts': 'the brand colours of Reddit, Facebook, Instagram and TikTok on their share buttons: not ours to theme',
};

// ---------------------------------------------------------------------------------------------------------------------
// Class and colour patterns
// ---------------------------------------------------------------------------------------------------------------------

const FAMILIES = 'slate gray zinc neutral stone red orange amber yellow lime green emerald teal cyan sky blue indigo violet purple fuchsia pink rose';
const SHADES = '50 100 200 300 400 500 600 700 800 900 950';
const PREFIXES = 'bg text border border-t border-b border-l border-r border-x border-y border-s border-e ring ring-offset outline divide from via to fill stroke shadow inset-shadow inset-ring drop-shadow accent caret decoration placeholder';
const alt = (/** @type {string} */ list) => list.split(' ').join('|');
const PREFIX_ALT = PREFIXES.split(' ')
    .sort((a, b) => b.length - a.length)
    .join('|');
const VARIANTS = '(?:[a-z0-9_-]+:)*';
const OPACITY = '(?:/(?:\\d{1,3}|\\[[^\\]\\s]+\\]))?';
const LEGACY_COLOUR = `(?:(?:${alt(FAMILIES)})-(?:${alt(SHADES)})|white|black|libre-[a-z]+(?:-[a-z]+)*|primary-(?:50|[1-9]00)|surface-(?:50|[1-5]00))`;

/** A legacy colour class (m1), variants and opacity included: `dark:hover:bg-slate-700/50`. */
export const LEGACY_CLASS_RE = new RegExp(`(?<![\\w-])${VARIANTS}(?:${PREFIX_ALT})-${LEGACY_COLOUR}${OPACITY}(?![\\w-])`, 'g');
/** A role utility: group 1 the variants, group 2 the role name (`card` in `hover:bg-lf-card/90`). */
export const ROLE_CLASS_RE = new RegExp(`(?<![\\w-])(${VARIANTS})(?:${PREFIX_ALT})-lf-([a-z0-9]+(?:-[a-z0-9]+)*)${OPACITY}(?![\\w-])`, 'g');
/** An arbitrary value under a colour utility: group 1 the value (`#ff4500` in `bg-[#ff4500]`). */
export const ARBITRARY_VALUE_RE = new RegExp(`(?<![\\w-])${VARIANTS}(?:${PREFIX_ALT})-\\[([^\\]\\s]+)\\]`, 'g');
/** Tailwind v4's short form for a variable under a colour utility: group 1 the variable (`--x` in `bg-(--x)`). */
export const ARBITRARY_VARIABLE_RE = new RegExp(`(?<![\\w-])${VARIANTS}(?:${PREFIX_ALT})-\\((--[\\w-]+)\\)`, 'g');

// `_` stands for a space inside a Tailwind arbitrary value (`shadow-[0_0_4px_rgba(…)]`): it is a word character, so the
// boundaries below are written out instead of `\b`.
const HEX_RE = /(?<![A-Za-z0-9&])#(?:[0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{3,4})(?![0-9A-Za-z])/g;
const COLOUR_FN_RE = /(?<![A-Za-z0-9-])(?:rgba?|hsla?|oklch|oklab|lab|lch|hwb)\(/g;
const SVG_COLOUR_ATTRIBUTES = new Set(['fill', 'stroke', 'stop-color', 'color', 'flood-color', 'lighting-color']);

/** CSS named colours: `transparent`, `currentcolor` and the keywords are not colours to theme. */
export const NAMED_COLOURS = new Set(
    (
        'aliceblue antiquewhite aqua aquamarine azure beige bisque black blanchedalmond blue blueviolet brown burlywood ' +
        'cadetblue chartreuse chocolate coral cornflowerblue cornsilk crimson cyan darkblue darkcyan darkgoldenrod darkgray ' +
        'darkgreen darkgrey darkkhaki darkmagenta darkolivegreen darkorange darkorchid darkred darksalmon darkseagreen ' +
        'darkslateblue darkslategray darkslategrey darkturquoise darkviolet deeppink deepskyblue dimgray dimgrey dodgerblue ' +
        'firebrick floralwhite forestgreen fuchsia gainsboro ghostwhite gold goldenrod gray green greenyellow grey honeydew ' +
        'hotpink indianred indigo ivory khaki lavender lavenderblush lawngreen lemonchiffon lightblue lightcoral lightcyan ' +
        'lightgoldenrodyellow lightgray lightgreen lightgrey lightpink lightsalmon lightseagreen lightskyblue lightslategray ' +
        'lightslategrey lightsteelblue lightyellow lime limegreen linen magenta maroon mediumaquamarine mediumblue ' +
        'mediumorchid mediumpurple mediumseagreen mediumslateblue mediumspringgreen mediumturquoise mediumvioletred ' +
        'midnightblue mintcream mistyrose moccasin navajowhite navy oldlace olive olivedrab orange orangered orchid ' +
        'palegoldenrod palegreen paleturquoise palevioletred papayawhip peachpuff peru pink plum powderblue purple ' +
        'rebeccapurple red rosybrown royalblue saddlebrown salmon sandybrown seagreen seashell sienna silver skyblue slateblue ' +
        'slategray slategrey snow springgreen steelblue tan teal thistle tomato turquoise violet wheat white whitesmoke yellow ' +
        'yellowgreen'
    ).split(' '),
);

// ---------------------------------------------------------------------------------------------------------------------
// Sources and comments
// ---------------------------------------------------------------------------------------------------------------------

/** Whether a path under src is production code the gates read. */
export function isProductionSource(/** @type {string} */ rel) {
    if (!/\.(svelte|ts|js)$/.test(rel) || rel.endsWith('.d.ts')) return false;
    if (/\.(test|spec)\.(ts|js)$/.test(rel)) return false;
    if (rel.split('/').some((segment) => segment === '__tests__' || segment === '__mocks__' || segment === 'node_modules')) return false;
    if (LAB_PREFIXES.some((prefix) => rel.startsWith(prefix))) return false;
    const name = basename(rel);
    return !(name.startsWith('generated') || name.includes('openapi') || name.includes('tool-contract-map'));
}

/** The production sources under `srcDir`, as sorted POSIX paths relative to it. */
export function listSources(srcDir = SRC_DIR) {
    /** @type {string[]} */
    const out = [];
    /** @param {string} dir */
    const walk = (dir) => {
        for (const entry of readdirSync(dir, {withFileTypes: true})) {
            const full = join(dir, entry.name);
            if (entry.isDirectory()) walk(full);
            else {
                const rel = relative(srcDir, full).split(sep).join('/');
                if (isProductionSource(rel)) out.push(rel);
            }
        }
    };
    walk(srcDir);
    return out.sort(byText);
}

/** Byte order, the same on every machine. */
export function byText(/** @type {string} */ a, /** @type {string} */ b) {
    return a < b ? -1 : a > b ? 1 : 0;
}

/** Spaces over everything but newlines: offsets and line numbers survive. */
const spaces = (/** @type {string} */ text) => text.replace(/[^\n]/g, ' ');

/** CSS without its comments. */
export function blankCssComments(/** @type {string} */ css) {
    return css.replace(/\/\*[\s\S]*?\*\//g, spaces);
}

/** Script code without its comments; strings and template literals are kept as they are. */
export function blankScriptComments(/** @type {string} */ code) {
    let out = '';
    let i = 0;
    while (i < code.length) {
        const c = code[i];
        const next = code[i + 1];
        if (c === '/' && next === '/') {
            const end = code.indexOf('\n', i);
            const stop = end === -1 ? code.length : end;
            out += spaces(code.slice(i, stop));
            i = stop;
        } else if (c === '/' && next === '*') {
            const end = code.indexOf('*/', i + 2);
            const stop = end === -1 ? code.length : end + 2;
            out += spaces(code.slice(i, stop));
            i = stop;
        } else if (c === "'" || c === '"' || c === '`') {
            let j = i + 1;
            while (j < code.length && code[j] !== c && (c === '`' || code[j] !== '\n')) j += code[j] === '\\' ? 2 : 1;
            out += code.slice(i, j + 1);
            i = j + 1;
        } else {
            out += c;
            i += 1;
        }
    }
    return out;
}

const SCRIPT_RE = /(<script\b[^>]*>)([\s\S]*?)(<\/script\s*>)/gi;
const STYLE_RE = /(<style\b[^>]*>)([\s\S]*?)(<\/style\s*>)/gi;
/** A whole script or style block, kept as one part when the markup around it is split. */
const SCRIPT_OR_STYLE_RE = /(<script\b[^>]*>[\s\S]*?<\/script\s*>|<style\b[^>]*>[\s\S]*?<\/style\s*>)/gi;

/** A source without its comments, each part of a Svelte file by its own syntax: the markup's `{…}` expressions are script. */
export function codeOf(/** @type {string} */ rel, /** @type {string} */ text) {
    if (!rel.endsWith('.svelte')) return blankScriptComments(text);
    return text
        .replace(/<!--[\s\S]*?-->/g, spaces)
        .replace(SCRIPT_RE, (_m, open, body, close) => open + blankScriptComments(body) + close)
        .replace(STYLE_RE, (_m, open, body, close) => open + blankCssComments(body) + close)
        .split(SCRIPT_OR_STYLE_RE)
        .map((part, index) => (index % 2 === 1 ? part : blankExpressionComments(part)))
        .join('');
}

/**
 * Markup with the comments of its `{…}` expressions blanked. A line or block comment inside an attribute value or a text
 * expression is script: left in, an apostrophe or a backtick in it opened a string that swallowed the markup after it
 * (AF, lot 8: G3 on an `onfitperiod={…}` attribute that holds no class, and the swallowed elements never checked).
 */
function blankExpressionComments(/** @type {string} */ markup) {
    let out = '';
    let i = 0;
    while (i < markup.length) {
        const open = markup.indexOf('{', i);
        if (open === -1) {
            out += markup.slice(i);
            break;
        }
        const end = expressionEnd(markup, open);
        out += markup.slice(i, open + 1) + blankScriptComments(markup.slice(open + 1, end));
        i = end;
    }
    return out;
}

/** The index of the `}` closing the markup expression opened at `start`, its strings and comments skipped. */
function expressionEnd(/** @type {string} */ text, /** @type {number} */ start) {
    let depth = 0;
    for (let i = start; i < text.length; i++) {
        const c = text[i];
        if (c === '/' && text[i + 1] === '/') {
            const end = text.indexOf('\n', i);
            if (end === -1) return text.length;
            i = end;
        } else if (c === '/' && text[i + 1] === '*') {
            const end = text.indexOf('*/', i + 2);
            if (end === -1) return text.length;
            i = end + 1;
        } else if (c === "'" || c === '"' || c === '`') i = endOfString(text, i);
        else if (c === '{') depth += 1;
        else if (c === '}' && --depth === 0) return i;
    }
    return text.length;
}

/** The markup of a Svelte file: the bodies of its scripts and styles blanked. */
export function markupOf(/** @type {string} */ code) {
    return code.replace(SCRIPT_RE, (_m, open, body, close) => open + spaces(body) + close).replace(STYLE_RE, (_m, open, body, close) => open + spaces(body) + close);
}

/** The 1-based line of an offset. */
export function lineAt(/** @type {string} */ text, /** @type {number} */ offset) {
    let line = 1;
    for (let i = 0; i < offset && i < text.length; i++) if (text[i] === '\n') line++;
    return line;
}

// ---------------------------------------------------------------------------------------------------------------------
// Strings, brackets and markup
// ---------------------------------------------------------------------------------------------------------------------

/** The index of the quote closing the string opened at `start`; a template's `${…}` is skipped whole. */
function endOfString(/** @type {string} */ text, /** @type {number} */ start) {
    const quote = text[start];
    let i = start + 1;
    while (i < text.length && text[i] !== quote) {
        if (text[i] === '\\') i += 1;
        else if (quote === '`' && text[i] === '$' && text[i + 1] === '{') i = closing(text, i + 1);
        i += 1;
    }
    return i;
}

/** The index of the bracket closing the `(` or `{` at `start`, strings skipped; the end of `text` if none. */
function closing(/** @type {string} */ text, /** @type {number} */ start) {
    const open = text[start];
    const close = open === '(' ? ')' : '}';
    let depth = 0;
    for (let i = start; i < text.length; i++) {
        const c = text[i];
        if (c === "'" || c === '"' || c === '`') i = endOfString(text, i);
        else if (c === open) depth += 1;
        else if (c === close && --depth === 0) return i;
    }
    return text.length;
}

/** An HTML attribute value ends at the next quote of its kind: no escapes. */
function endOfAttribute(/** @type {string} */ text, /** @type {number} */ start) {
    const end = text.indexOf(text[start], start + 1);
    return end === -1 ? text.length : end;
}

/**
 * The string literals of script code: '…', "…" and whole templates `…` (their ${…} included).
 * @param {string} code
 * @returns {Generator<{value: string, index: number}>}
 */
export function* stringLiterals(code) {
    for (let i = 0; i < code.length; i++) {
        const c = code[i];
        if (c === "'" || c === '"' || c === '`') {
            const end = endOfString(code, i);
            yield {value: code.slice(i + 1, end), index: i};
            i = end;
        }
    }
}

/**
 * @typedef {{name: string, value: string | null, expression: boolean}} Attribute
 *   `name` is '' for a `{…}` shorthand or spread; `expression` tells a `{…}` value from a quoted or bare one.
 */

/** The attributes of a start tag, from the text between its name and its `>`. */
function parseAttributes(/** @type {string} */ body) {
    /** @type {Attribute[]} */
    const out = [];
    let i = 0;
    while (i < body.length) {
        while (i < body.length && /[\s/]/.test(body[i])) i += 1;
        if (i >= body.length) break;
        if (body[i] === '{') {
            const end = closing(body, i);
            out.push({name: '', value: body.slice(i + 1, end), expression: true});
            i = end + 1;
            continue;
        }
        let j = i;
        while (j < body.length && !/[\s=]/.test(body[j])) j += 1;
        const name = body.slice(i, j);
        i = j;
        while (i < body.length && /\s/.test(body[i])) i += 1;
        if (body[i] !== '=') {
            out.push({name, value: null, expression: false});
            continue;
        }
        i += 1;
        while (i < body.length && /\s/.test(body[i])) i += 1;
        if (body[i] === '"' || body[i] === "'") {
            const end = endOfAttribute(body, i);
            out.push({name, value: body.slice(i + 1, end), expression: false});
            i = end + 1;
        } else if (body[i] === '{') {
            const end = closing(body, i);
            out.push({name, value: body.slice(i + 1, end), expression: true});
            i = end + 1;
        } else {
            let k = i;
            while (k < body.length && !/\s/.test(body[k])) k += 1;
            out.push({name, value: body.slice(i, k), expression: false});
            i = k;
        }
    }
    return out;
}

/**
 * The start tags of Svelte markup (scripts and styles already blanked), with their attributes.
 * @param {string} markup
 * @returns {Generator<{tag: string, index: number, attributes: Attribute[]}>}
 */
export function* startTags(markup) {
    const re = /<([A-Za-z][\w:.-]*)/g;
    let m;
    while ((m = re.exec(markup))) {
        let i = re.lastIndex;
        while (i < markup.length && markup[i] !== '>') {
            const c = markup[i];
            if (c === '"' || c === "'") i = endOfAttribute(markup, i);
            else if (c === '{') i = closing(markup, i);
            i += 1;
        }
        yield {tag: m[1], index: m.index, attributes: parseAttributes(markup.slice(re.lastIndex, i))};
        re.lastIndex = Math.min(i + 1, markup.length);
    }
}

// ---------------------------------------------------------------------------------------------------------------------
// m1 and m2: what a source measures
// ---------------------------------------------------------------------------------------------------------------------

/** `#FFF` → `#ffffff`, `#abcd` → `#aabbccdd`. */
function normalizeHex(/** @type {string} */ hex) {
    const digits = hex.slice(1).toLowerCase();
    return '#' + (digits.length <= 4 ? [...digits].map((d) => d + d).join('') : digits);
}

/** Lower-case name, single spaces, none around commas, slashes and brackets. */
function normalizeFunction(/** @type {string} */ call) {
    const at = call.indexOf('(');
    return (
        call.slice(0, at).toLowerCase() +
        call
            .slice(at)
            .replace(/\s+/g, ' ')
            .replace(/\s*([(),/])\s*/g, '$1')
            .trim()
    );
}

/** A colour function is a literal when its arguments hold a number outside every var(…) and ${…}. */
function isLiteralCall(/** @type {string} */ call) {
    let args = call.slice(call.indexOf('(') + 1, -1);
    for (let at = args.search(/var\(|\$\{/); at !== -1; at = args.search(/var\(|\$\{/)) {
        const open = args[at] === '$' ? at + 1 : at + 3;
        args = args.slice(0, at) + args.slice(closing(args, open) + 1);
    }
    return /\d/.test(args);
}

/** The colour names of a CSS value, lower-case. */
function* colourNamesIn(/** @type {string} */ value) {
    for (const m of value.matchAll(/(?<![\w#.-])([a-zA-Z]+)(?![\w(-])/g)) {
        const word = m[1].toLowerCase();
        if (NAMED_COLOURS.has(word)) yield word;
    }
}

/** The values of a block of declarations: `color: white; border: 1px solid` gives `white`, `1px solid`. */
function* declarationValues(/** @type {string} */ block) {
    for (const declaration of block.split(';')) {
        const m = /^\s*-{0,2}[\w-]+\s*:([\s\S]*)$/.exec(declaration);
        if (m) yield m[1];
    }
}

/** A script string that is a colour name, lower-case: `'white'`, `"Black"`. */
function* colourNameStrings(/** @type {string} */ code) {
    for (const {value} of stringLiterals(code)) {
        const word = value.trim().toLowerCase();
        if (NAMED_COLOURS.has(word)) yield word;
    }
}

/** The colour names a source writes: in style values, SVG colour attributes and whole script strings. */
function* colourNames(/** @type {string} */ rel, /** @type {string} */ code) {
    if (!rel.endsWith('.svelte')) {
        yield* colourNameStrings(code);
        return;
    }
    for (const m of code.matchAll(SCRIPT_RE)) yield* colourNameStrings(m[2]);
    for (const m of code.matchAll(STYLE_RE)) for (const block of m[2].matchAll(/\{([^{}]*)\}/g)) for (const value of declarationValues(block[1])) yield* colourNamesIn(value);
    for (const {attributes} of startTags(markupOf(code))) {
        for (const attribute of attributes) {
            if (attribute.value === null) continue;
            if (attribute.expression) yield* colourNameStrings(attribute.value);
            else if (attribute.name === 'style') for (const value of declarationValues(attribute.value)) yield* colourNamesIn(value);
            else if (attribute.name.startsWith('style:')) yield* colourNamesIn(attribute.value);
            else if (SVG_COLOUR_ATTRIBUTES.has(attribute.name)) {
                const word = attribute.value.trim().toLowerCase();
                if (NAMED_COLOURS.has(word)) yield word;
            }
        }
    }
}

/** Whether LITERAL_EXCEPTIONS lets `value` stay in `rel`. */
export function isLiteralException(/** @type {string} */ rel, /** @type {string} */ value) {
    return LITERAL_EXCEPTIONS.some((e) => e.file === rel && (typeof e.value === 'string' ? e.value === value : e.value.test(value)));
}

/** The colour literals of a source (comments already blanked), normalized and sorted; exceptions left out. */
function colourLiterals(/** @type {string} */ rel, /** @type {string} */ code) {
    /** @type {string[]} */
    const found = [];
    for (const m of code.matchAll(HEX_RE)) found.push(normalizeHex(m[0]));
    for (const m of code.matchAll(COLOUR_FN_RE)) {
        const start = m.index ?? 0;
        const end = closing(code, start + m[0].length - 1);
        if (end >= code.length || end - start > 300) continue;
        const call = code.slice(start, end + 1);
        if (isLiteralCall(call)) found.push(normalizeFunction(call));
    }
    found.push(...colourNames(rel, code));
    return found.filter((value) => !isLiteralException(rel, value)).sort(byText);
}

/** @typedef {{m1: number, m2: string[]}} Measure  m1 the legacy classes; m2 the colour literals, sorted. */

/** What a production source measures. */
export function measureSource(/** @type {string} */ rel, /** @type {string} */ text) {
    return measureCode(rel, codeOf(rel, text));
}

/** What a source measures, from its code without comments. */
function measureCode(/** @type {string} */ rel, /** @type {string} */ code) {
    return {m1: [...code.matchAll(LEGACY_CLASS_RE)].length, m2: rel.startsWith(CENTRAL_PREFIX) ? [] : colourLiterals(rel, code)};
}

/** @type {Map<string, Map<string, string>>} the code without comments of each source, per source tree, read once. */
const CODE_CACHE = new Map();

/** A production source without its comments, read once per process: the scan, the grammar and C4 share it. */
function sourceCode(/** @type {string} */ srcDir, /** @type {string} */ rel) {
    let byFile = CODE_CACHE.get(srcDir);
    if (!byFile) {
        byFile = new Map();
        CODE_CACHE.set(srcDir, byFile);
    }
    let code = byFile.get(rel);
    if (code === undefined) {
        code = codeOf(rel, readFileSync(join(srcDir, rel), 'utf8'));
        byFile.set(rel, code);
    }
    return code;
}

/** @typedef {{sources: string[], files: Map<string, Measure>}} Scan  `files` holds the sources that measure anything. */

/** Measure every production source under `srcDir`. */
export function scanTree(srcDir = SRC_DIR) {
    const sources = listSources(srcDir);
    /** @type {Map<string, Measure>} */
    const files = new Map();
    for (const rel of sources) {
        const measure = measureCode(rel, sourceCode(srcDir, rel));
        if (measure.m1 || measure.m2.length) files.set(rel, measure);
    }
    return {sources, files};
}

/** The totals of a set of measures: R1 compares them. */
export function totalsOf(/** @type {Iterable<Measure>} */ measures) {
    let m1 = 0;
    let m2 = 0;
    for (const measure of measures) {
        m1 += measure.m1;
        m2 += measure.m2.length;
    }
    return {m1, m2};
}

// ---------------------------------------------------------------------------------------------------------------------
// The baseline: one line per file, merge-friendly
// ---------------------------------------------------------------------------------------------------------------------

/** @typedef {{files: Map<string, Measure>, declarations: string[]}} Baseline  declarations: the `~split` and `~accept` lines. */

const HEADER = [
    '# Colour ratchet baseline (workstream T): the legacy colours left in each production source of frontend/src.',
    '# One line per file: <path under src> TAB <m1: legacy colour classes> TAB <m2: colour literals, normalized; ×N repeats>. No totals: the gate computes them.',
    '# Written only by `node frontend/scripts/theme/theme-roles.mjs` (--init, --update, --split, --accept, --resolve).',
    "# Merge conflict: `--resolve` merges the three sides — a line one side left as it was takes the other side's; changed on both, an accepted file keeps its accepting side, otherwise the tighter side wins (the lower m1, the m2 values both sides have) — then the gate must pass on the merged tree. Never widen a line to pass.",
    '# Lines starting with ~ declare a split file (old, new files, its record then) or a file taken as it is (file, reason).',
];

/** `['#fff', '#fff', 'red']` → `['#fff×2', 'red']`. */
export function compactValues(/** @type {string[]} */ sorted) {
    /** @type {string[]} */
    const out = [];
    for (let i = 0; i < sorted.length; ) {
        let j = i;
        while (j < sorted.length && sorted[j] === sorted[i]) j += 1;
        out.push(j - i > 1 ? `${sorted[i]}×${j - i}` : sorted[i]);
        i = j;
    }
    return out;
}

/** The inverse of compactValues, sorted. */
function expandValues(/** @type {string[]} */ cells) {
    /** @type {string[]} */
    const out = [];
    for (const cell of cells) {
        const m = /^(.*)×(\d+)$/.exec(cell);
        if (m) for (let n = Number(m[2]); n > 0; n--) out.push(m[1]);
        else if (cell) out.push(cell);
    }
    return out.sort(byText);
}

/** The values of `a` beyond those of `b`, multisets as sorted arrays: what R2 rejects. */
export function excessValues(/** @type {string[]} */ a, /** @type {string[]} */ b) {
    /** @type {Map<string, number>} */
    const left = new Map();
    for (const value of b) left.set(value, (left.get(value) ?? 0) + 1);
    return a.filter((value) => {
        const n = left.get(value) ?? 0;
        if (n === 0) return true;
        left.set(value, n - 1);
        return false;
    });
}

/** The values both multisets hold: the tighter of two m2 records. */
export function commonValues(/** @type {string[]} */ a, /** @type {string[]} */ b) {
    const extra = excessValues(a, b);
    return excessValues(a, extra);
}

/** Read a baseline file's text. */
export function parseBaseline(/** @type {string} */ text) {
    /** @type {Baseline} */
    const baseline = {files: new Map(), declarations: []};
    for (const line of text.split(/\r?\n/)) {
        if (!line.trim() || line.startsWith('#')) continue;
        if (line.startsWith('~')) {
            baseline.declarations.push(line);
            continue;
        }
        const [file, m1, ...values] = line.split('\t');
        baseline.files.set(file, {m1: Number(m1), m2: expandValues(values)});
    }
    return baseline;
}

/** A baseline as text: header, then one sorted line per file that still measures anything, then the declarations. */
export function formatBaseline(/** @type {Baseline} */ baseline) {
    const lines = [...HEADER];
    for (const [file, measure] of [...baseline.files].sort(([a], [b]) => byText(a, b))) {
        if (measure.m1 || measure.m2.length) lines.push([file, String(measure.m1), ...compactValues(measure.m2)].join('\t'));
    }
    lines.push(...[...new Set(baseline.declarations)].sort(byText));
    return lines.join('\n') + '\n';
}

export function readBaseline(path = BASELINE) {
    return parseBaseline(readFileSync(path, 'utf8'));
}

export function writeBaseline(/** @type {Baseline} */ baseline, path = BASELINE) {
    writeFileSync(path, formatBaseline(baseline));
}

/** A baseline taken from a scan as it is: the first one (--init). */
export function baselineOf(/** @type {Scan} */ scan) {
    return {files: new Map([...scan.files].map(([rel, measure]) => [rel, {m1: measure.m1, m2: [...measure.m2]}])), declarations: []};
}

// ---------------------------------------------------------------------------------------------------------------------
// The ratchet
// ---------------------------------------------------------------------------------------------------------------------

/**
 * R4: each new file that measures something, paired with a file of the same name that left the tree.
 * @returns {Map<string, string>} new path → path in the baseline
 */
function pairMoves(/** @type {Scan} */ scan, /** @type {Baseline} */ baseline) {
    const present = new Set(scan.sources);
    /** @type {Map<string, string[]>} */
    const orphans = new Map();
    for (const rel of baseline.files.keys()) {
        if (present.has(rel)) continue;
        const list = orphans.get(basename(rel)) ?? [];
        list.push(rel);
        orphans.set(basename(rel), list);
    }
    /** @type {Map<string, string>} */
    const moves = new Map();
    for (const [rel, measure] of scan.files) {
        if (baseline.files.has(rel)) continue;
        const candidates = orphans.get(basename(rel));
        if (!candidates?.length) continue;
        const fits = (/** @type {string} */ c) => {
            const record = baseline.files.get(c);
            return !!record && measure.m1 <= record.m1 && excessValues(measure.m2, record.m2).length === 0;
        };
        const pick = candidates.find(fits) ?? candidates[0];
        candidates.splice(candidates.indexOf(pick), 1);
        moves.set(rel, pick);
    }
    return moves;
}

/**
 * @typedef {{rule: 'R1' | 'R2' | 'R3', metric: 'm1' | 'm2', file: string | null, from: string | null, detail: string}} Violation
 * @typedef {{file: string, m1: [number, number], m2Gone: string[]}} Drop
 */

/** The ratchet's verdict on a scan: violations (R1–R3), drops (R5) and the moves it recognized (R4). */
export function compareWithBaseline(/** @type {Scan} */ scan, /** @type {Baseline} */ baseline) {
    /** @type {Violation[]} */
    const violations = [];
    const moves = pairMoves(scan, baseline);
    const was = totalsOf(baseline.files.values());
    const now = totalsOf(scan.files.values());
    for (const metric of /** @type {const} */ (['m1', 'm2'])) {
        if (now[metric] > was[metric]) violations.push({rule: 'R1', metric, file: null, from: null, detail: `the total rose from ${was[metric]} to ${now[metric]}`});
    }
    for (const [rel, measure] of scan.files) {
        const from = baseline.files.has(rel) ? rel : (moves.get(rel) ?? null);
        const record = from ? baseline.files.get(from) : undefined;
        const rule = record ? 'R2' : 'R3';
        if (!rel.startsWith(CENTRAL_PREFIX) && measure.m1 > (record?.m1 ?? 0)) {
            violations.push({rule, metric: 'm1', file: rel, from, detail: `${record?.m1 ?? 0} → ${measure.m1} legacy colour classes`});
        }
        const extra = excessValues(measure.m2, record?.m2 ?? []);
        if (extra.length) violations.push({rule, metric: 'm2', file: rel, from, detail: `colour literals beyond its record: ${compactValues(extra).join(' ')}`});
    }
    const movedTo = new Map([...moves].map(([to, from]) => [from, to]));
    /** @type {Drop[]} */
    const drops = [];
    for (const [rel, record] of baseline.files) {
        const measure = scan.files.get(movedTo.get(rel) ?? rel) ?? {m1: 0, m2: []};
        const m2Gone = excessValues(record.m2, measure.m2);
        if (measure.m1 < record.m1 || m2Gone.length) drops.push({file: rel, m1: [record.m1, measure.m1], m2Gone});
    }
    return {violations, drops, moves: [...moves].map(([to, from]) => ({from, to}))};
}

/** --update: every line tightened to what the tree measures, moved files under their new name; never widened. */
export function tightenBaseline(/** @type {Scan} */ scan, /** @type {Baseline} */ baseline) {
    const moves = pairMoves(scan, baseline);
    /** @type {Map<string, Measure>} */
    const files = new Map();
    /** @type {string[]} */
    const refused = [];
    for (const [rel, measure] of scan.files) {
        if (rel.startsWith(CENTRAL_PREFIX)) {
            files.set(rel, {m1: measure.m1, m2: []});
            continue;
        }
        const from = baseline.files.has(rel) ? rel : moves.get(rel);
        const record = from ? baseline.files.get(from) : undefined;
        if (!record) refused.push(rel);
        else files.set(rel, {m1: Math.min(record.m1, measure.m1), m2: commonValues(record.m2, measure.m2)});
    }
    // A central table may take in classes only while the total holds (R1): if it would rise, its line keeps its record
    // and the table is refused, so that --update can never accept a tree the gate rejects.
    if (totalsOf(files.values()).m1 > totalsOf(baseline.files.values()).m1) {
        for (const [rel, line] of files) {
            const record = baseline.files.get(rel);
            if (!rel.startsWith(CENTRAL_PREFIX) || (record && line.m1 <= record.m1)) continue;
            refused.push(rel);
            if (record) files.set(rel, {m1: record.m1, m2: []});
            else files.delete(rel);
        }
    }
    return {baseline: {files, declarations: [...baseline.declarations]}, refused};
}

/**
 * --split: `from` was split into `into` (it may survive as one of the parts). Each part's record starts from what it
 * measures; together they may hold no more classes and no other literals than `from` and the parts' own records did.
 */
export function declareSplit(/** @type {Scan} */ scan, /** @type {Baseline} */ baseline, /** @type {string} */ from, /** @type {string[]} */ into) {
    const record = baseline.files.get(from);
    if (!record) throw new Error(`${from}: no record in the baseline, nothing to split`);
    const present = new Set(scan.sources);
    for (const rel of into) if (!present.has(rel)) throw new Error(`${rel}: not a production source under src`);
    const group = [...new Set([...(present.has(from) ? [from] : []), ...into])];
    let budget = record.m1;
    const budgetValues = [...record.m2];
    for (const rel of into) {
        const own = rel === from ? undefined : baseline.files.get(rel);
        if (own) {
            budget += own.m1;
            budgetValues.push(...own.m2);
        }
    }
    let m1 = 0;
    /** @type {string[]} */
    const values = [];
    for (const rel of group) {
        const measure = scan.files.get(rel);
        if (measure) {
            m1 += measure.m1;
            values.push(...measure.m2);
        }
    }
    if (m1 > budget) throw new Error(`the parts hold ${m1} legacy colour classes; ${from} and their records had ${budget}`);
    const extra = excessValues(values.sort(byText), budgetValues.sort(byText));
    if (extra.length) throw new Error(`the parts hold colour literals ${from} did not: ${compactValues(extra).join(' ')}`);
    const files = new Map(baseline.files);
    files.delete(from);
    for (const rel of group) {
        const measure = scan.files.get(rel);
        if (measure) files.set(rel, {m1: measure.m1, m2: [...measure.m2]});
        else files.delete(rel);
    }
    const declaration = ['~split', from, into.join(','), String(record.m1), ...compactValues(record.m2)].join('\t');
    return {files, declarations: [...baseline.declarations, declaration]};
}

/** --accept: take a file as it is, with the reason on record. Only with the colour coordinator's OK. */
export function acceptFile(/** @type {Scan} */ scan, /** @type {Baseline} */ baseline, /** @type {string} */ rel, /** @type {string} */ reason) {
    const why = reason.replace(/\s+/g, ' ').trim();
    if (!why) throw new Error('--accept needs --reason');
    const files = new Map(baseline.files);
    const measure = scan.files.get(rel);
    if (measure) files.set(rel, {m1: measure.m1, m2: [...measure.m2]});
    else files.delete(rel);
    return {files, declarations: [...baseline.declarations, ['~accept', rel, why].join('\t')]};
}

/**
 * Three-way merge of baselines (TC-7). Per file line: a side that left it as the base had it takes the other side's
 * line, removal and addition included. Changed on both sides: a side that accepted the file (a `~accept` the base does
 * not have) wins, both accepting is refused, otherwise the tighter side wins — the lower m1 and the m2 values both
 * hold — and a line removed on one side stays removed. Declarations: those of both sides, once.
 */
export function mergeBaselines(/** @type {Baseline} */ base, /** @type {Baseline} */ ours, /** @type {Baseline} */ theirs) {
    const baseDeclarations = new Set(base.declarations);
    const acceptedIn = (/** @type {Baseline} */ side) => new Set(side.declarations.filter((line) => line.startsWith('~accept\t') && !baseDeclarations.has(line)).map((line) => line.split('\t')[1]));
    const [acceptedOurs, acceptedTheirs] = [acceptedIn(ours), acceptedIn(theirs)];
    const same = (/** @type {Measure | undefined} */ a, /** @type {Measure | undefined} */ b) => (a && b ? a.m1 === b.m1 && excessValues(a.m2, b.m2).length === 0 && excessValues(b.m2, a.m2).length === 0 : a === b);
    /** @type {Map<string, Measure>} */
    const files = new Map();
    for (const key of new Set([...base.files.keys(), ...ours.files.keys(), ...theirs.files.keys()])) {
        const was = base.files.get(key);
        const mine = ours.files.get(key);
        const other = theirs.files.get(key);
        /** @type {Measure | undefined} */
        let merged;
        if (same(mine, was)) merged = other;
        else if (same(other, was)) merged = mine;
        else if (acceptedOurs.has(key) && acceptedTheirs.has(key)) throw new Error(`${key}: accepted on both sides of the merge — merge the sources, then --accept the file again on the merged tree`);
        else if (acceptedOurs.has(key)) merged = mine;
        else if (acceptedTheirs.has(key)) merged = other;
        else if (mine && other) merged = {m1: Math.min(mine.m1, other.m1), m2: commonValues(mine.m2, other.m2)};
        if (merged) files.set(key, merged);
    }
    return {files, declarations: [...new Set([...ours.declarations, ...theirs.declarations])]};
}

/** --resolve: the merge of the three index stages of a conflicted baseline (git show :1: :2: :3:). */
export function resolveConflict(repoRoot = dirname(FRONTEND_DIR)) {
    const path = relative(repoRoot, BASELINE).split(sep).join('/');
    const stage = (/** @type {number} */ n) => {
        try {
            return parseBaseline(execFileSync('git', ['-C', repoRoot, 'show', `:${n}:${path}`], {encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore']}));
        } catch {
            return null;
        }
    };
    const ours = stage(2);
    const theirs = stage(3);
    if (!ours || !theirs) throw new Error(`${path} is not in a merge conflict: nothing to resolve`);
    return mergeBaselines(stage(1) ?? {files: new Map(), declarations: []}, ours, theirs);
}

// ---------------------------------------------------------------------------------------------------------------------
// The grammar of the roles
// ---------------------------------------------------------------------------------------------------------------------

/**
 * The class strings of a source, each checked whole by G3. In markup, an element's `class`, its `class={…}` and its
 * `class:` directives make one string, and every other attribute value is its own; in scripts, every string literal.
 * @param {string} rel
 * @param {string} code
 * @returns {Generator<{value: string, index: number}>}
 */
function* classStrings(rel, code) {
    if (!rel.endsWith('.svelte')) {
        yield* stringLiterals(code);
        return;
    }
    for (const m of code.matchAll(SCRIPT_RE)) {
        const offset = (m.index ?? 0) + m[1].length;
        for (const literal of stringLiterals(m[2])) yield {value: literal.value, index: offset + literal.index};
    }
    for (const {index, attributes} of startTags(markupOf(code))) {
        /** @type {string[]} */
        const element = [];
        for (const attribute of attributes) {
            if (attribute.name === 'class' && attribute.value !== null) element.push(attribute.value);
            else if (attribute.name.startsWith('class:')) element.push(attribute.name.slice('class:'.length));
            else if (attribute.value !== null) yield {value: attribute.value, index};
        }
        if (element.length) yield {value: element.join(' '), index};
    }
}

const hasRoleClass = (/** @type {string} */ text) => new RegExp(ROLE_CLASS_RE.source).test(text);
const hasLegacyClass = (/** @type {string} */ text) => new RegExp(LEGACY_CLASS_RE.source).test(text);
const COLOUR_IN_VALUE_RE = /#[0-9a-fA-F]{3,8}(?![0-9A-Za-z])|(?<![A-Za-z0-9-])(?:rgba?|hsla?|oklch|oklab|lab|lch|hwb|color-mix)\(|var\(--/;
const LITERAL_IN_VALUE_RE = /#[0-9a-fA-F]{3,8}(?![0-9A-Za-z])|(?<![A-Za-z0-9-])(?:rgba?|hsla?|oklch|oklab|lab|lch|hwb)\(/;

/** A role utility, whole: group 1 its variants, group 2 its colour utility (`bg`, `border-t`, `placeholder`). */
const ROLE_TOKEN_RE = new RegExp(`^(${VARIANTS})(${PREFIX_ALT})-lf-[a-z0-9]+(?:-[a-z0-9]+)*${OPACITY}$`);

/** The words of a class string that can be class names: a `${…}` fragment is not one. */
const classWords = (/** @type {string} */ text) => text.split(/\s+/).filter((word) => word && !/[${}]/.test(word));

/** An UPPER_CASE name, of any length (`TH`, `INPUT`): a constant when the module declares one of that name. */
const UPPER_NAME_RE = /\b[A-Z][A-Z0-9_]*\b/g;

/** An expression with its strings blanked: an operator inside a string is not one. */
function withoutStrings(/** @type {string} */ expression) {
    let out = '';
    let last = 0;
    for (const {value, index} of stringLiterals(expression)) {
        out += expression.slice(last, index + 1) + spaces(value);
        last = index + 1 + value.length;
    }
    return out + expression.slice(last);
}

/** Whether an expression chooses its classes: a ternary, `&&`, `||` or `??` outside its strings (not `?.`). */
const branches = (/** @type {string} */ expression) => /\?(?!\.)|&&|\|\|/.test(withoutStrings(expression));

/** A template literal's body: its static text, each `${…}` blanked, and the expressions of its `${…}`. */
function templateParts(/** @type {string} */ body) {
    /** @type {string[]} */
    const expressions = [];
    let text = '';
    for (let i = 0; i < body.length; i++) {
        if (body[i] === '\\') {
            text += body.slice(i, i + 2);
            i += 1;
        } else if (body[i] === '$' && body[i + 1] === '{') {
            const end = closing(body, i + 1);
            expressions.push(body.slice(i + 2, end));
            text += ' ';
            i = end;
        } else text += body[i];
    }
    return {text, expressions};
}

/** The class names an expression can give: the words of its strings, a template's included, and the UPPER_CASE constants it names. */
function expressionClasses(/** @type {string} */ expression, /** @type {Map<string, string>} */ constants) {
    /** @type {string[]} */
    const out = [];
    for (const {value, index} of stringLiterals(expression)) {
        if (expression[index] !== '`') {
            out.push(...classWords(value));
            continue;
        }
        const parts = templateParts(value);
        out.push(...classWords(parts.text));
        for (const inner of parts.expressions) out.push(...expressionClasses(inner, constants));
    }
    for (const m of withoutStrings(expression).matchAll(UPPER_NAME_RE)) {
        const value = constants.get(m[0]);
        if (value !== undefined) out.push(...classWords(value));
    }
    return out;
}

/** The UPPER_CASE string constants a module declares, exported or not: `const BASE = 'px-2 bg-lf-card'`. */
function stringConstants(/** @type {string} */ code) {
    /** @type {Map<string, string>} */
    const out = new Map();
    for (const m of code.matchAll(/\bconst\s+([A-Z][A-Z0-9_]*)\s*=\s*(['"`])/g)) {
        const start = (m.index ?? 0) + m[0].length - 1;
        out.set(m[1], code.slice(start + 1, endOfString(code, start)));
    }
    return out;
}

/**
 * The UPPER_CASE string constants a source can name: its own, and those it imports by name from a module of src
 * (`$lib/…`, `./…`, `../…`), one level deep. `moduleConstants` gives a module's own, or null when src has no such module.
 * @param {string} rel
 * @param {string} code
 * @param {(rel: string) => Map<string, string> | null} moduleConstants
 */
function constantsOf(rel, code, moduleConstants) {
    const constants = stringConstants(code);
    for (const m of code.matchAll(/\bimport\s*\{([^}]*)\}\s*from\s*['"]((?:\.{1,2}\/|\$lib\/)[^'"]+)['"]/g)) {
        const base = m[2].startsWith('$lib/') ? `lib/${m[2].slice('$lib/'.length)}` : posix.join(posix.dirname(rel), m[2]);
        const candidates = [base, `${base}.ts`, `${base}.js`, `${base}/index.ts`, `${base}/index.js`, base.replace(/\.js$/, '.ts')];
        const theirs = candidates.map(moduleConstants).find(Boolean);
        if (!theirs) continue;
        for (const specifier of m[1].split(',')) {
            const [name, alias] = specifier
                .trim()
                .replace(/^type\s+/, '')
                .split(/\s+as\s+/);
            const value = theirs.get(name);
            if (value !== undefined) constants.set(alias ?? name, value);
        }
    }
    return constants;
}

/**
 * The classes of an element, as G5 and G6 read them. `always`: set in every state. `groups`: each a set chosen on a
 * condition — a `{…}` or a template's `${…}` that branches, a `class:` directive. An expression that does not branch is
 * read literal by literal: its strings are always on, and each `${…}` of its templates is judged on its own, whatever
 * follows the template (`` `…`.trim() ``). UPPER_CASE string constants are read as their value; any other variable, a
 * class prop, and the elements of an array of classes that branches anywhere, are not told apart.
 * @param {Attribute[]} attributes
 * @param {Map<string, string>} constants
 */
function elementClasses(attributes, constants) {
    /** @type {string[]} */
    const always = [];
    /** @type {string[][]} */
    const groups = [];
    const expression = (/** @type {string} */ code) => {
        if (branches(code)) {
            groups.push(expressionClasses(code, constants));
            return;
        }
        for (const {value, index} of stringLiterals(code)) {
            if (code[index] !== '`') {
                always.push(...classWords(value));
                continue;
            }
            const parts = templateParts(value);
            always.push(...classWords(parts.text));
            parts.expressions.forEach(expression);
        }
        for (const m of withoutStrings(code).matchAll(UPPER_NAME_RE)) {
            const value = constants.get(m[0]);
            if (value !== undefined) always.push(...classWords(value));
        }
    };
    for (const attribute of attributes) {
        if (attribute.name.startsWith('class:')) groups.push([attribute.name.slice('class:'.length)]);
        if (attribute.name !== 'class' || attribute.value === null) continue;
        const value = attribute.value;
        if (attribute.expression) {
            expression(value);
            continue;
        }
        let text = '';
        for (let i = 0; i < value.length; i++) {
            if (value[i] === '{') {
                const end = closing(value, i);
                expression(value.slice(i + 1, end));
                text += ' ';
                i = end;
            } else text += value[i];
        }
        always.push(...classWords(text));
    }
    return {always, groups};
}

/** G5 on an element's classes: two role utilities on one colour utility and the same variants, one of them always on. */
function oneTernaryViolations(/** @type {{always: string[], groups: string[][]}} */ classes) {
    const slot = (/** @type {string} */ token) => {
        const m = ROLE_TOKEN_RE.exec(token);
        return m ? m[1] + m[2] : null;
    };
    const always = [...new Set(classes.always)].filter((token) => slot(token) !== null);
    /** @type {string[]} */
    const out = [];
    const add = (/** @type {string} */ text) => {
        if (!out.includes(text)) out.push(text);
    };
    for (let i = 0; i < always.length; i++) {
        for (let j = i + 1; j < always.length; j++) {
            const [a, b] = [always[i], always[j]].sort(byText);
            if (slot(a) === slot(b)) add(`${a} always, ${b} always`);
        }
    }
    for (const group of classes.groups) {
        for (const token of new Set(group)) {
            const s = slot(token);
            if (s === null) continue;
            for (const a of always) if (a !== token && slot(a) === s) add(`${a} always, ${token} on a condition`);
        }
    }
    return out;
}

/** Input types with no text of their own: the field rules of app.css never coloured them either. */
export const FIELD_TYPES_WITHOUT_TEXT = ['checkbox', 'radio', 'range', 'file', 'hidden', 'color', 'submit', 'button', 'reset', 'image'];

/** G6 on a start tag: a native field on roles names its text role, and its placeholder role when it has a placeholder. */
function nativeFieldViolation(/** @type {string} */ tag, /** @type {Attribute[]} */ attributes, /** @type {{always: string[], groups: string[][]}} */ classes) {
    if (tag !== 'input' && tag !== 'textarea' && tag !== 'select') return null;
    const all = [...classes.always, ...classes.groups.flat()];
    if (!all.some((token) => token.includes('-lf-'))) return null;
    const type = attributes.find((attribute) => attribute.name === 'type');
    const typeValue = type?.value == null ? undefined : type.expression ? /^\s*(['"])(\w+)\1\s*$/.exec(type.value)?.[2] : type.value;
    if (tag === 'input' && typeValue && FIELD_TYPES_WITHOUT_TEXT.includes(typeValue.toLowerCase())) return null;
    /** @type {string[]} */
    const missing = [];
    if (!all.some((token) => token.startsWith('text-lf-'))) missing.push('no text role');
    const placeholder = attributes.some((attribute) => attribute.name === 'placeholder' || (attribute.name === '' && attribute.value?.trim() === 'placeholder'));
    if (tag !== 'select' && placeholder && !all.some((token) => /(?:^|:)placeholder:text-lf-/.test(token))) missing.push('no placeholder role');
    return missing.length ? `<${tag}> ${missing.join(', ')}` : null;
}

/** @typedef {{rule: 'G1' | 'G2' | 'G3' | 'G4' | 'G5' | 'G6', file: string, line: number, text: string}} GrammarViolation */

/**
 * G1–G6 on one source; `names` are the role names of tokens.css (roleNames). `modules` holds the sources it may import
 * constants from, by path under src: the tree reads them from disk.
 * @param {string} rel
 * @param {string} text
 * @param {Set<string>} names
 * @param {Record<string, string>} [modules]
 */
export function grammarOf(rel, text, names, modules = {}) {
    return grammarOfCode(rel, codeOf(rel, text), names, (path) => (path in modules ? stringConstants(codeOf(path, modules[path])) : null));
}

/**
 * G1–G6 on a source's code without comments.
 * @param {string} rel
 * @param {string} code
 * @param {Set<string>} names
 * @param {(rel: string) => Map<string, string> | null} moduleConstants
 */
function grammarOfCode(rel, code, names, moduleConstants) {
    /** @type {GrammarViolation[]} */
    const out = [];
    for (const m of code.matchAll(ROLE_CLASS_RE)) {
        const line = lineAt(code, m.index ?? 0);
        if (/(?:^|:)dark:/.test(m[1])) out.push({rule: 'G1', file: rel, line, text: m[0]});
        if (!names.has(m[2])) out.push({rule: 'G2', file: rel, line, text: m[0]});
    }
    for (const {value, index} of classStrings(rel, code)) {
        if (hasRoleClass(value) && hasLegacyClass(value)) out.push({rule: 'G3', file: rel, line: lineAt(code, index), text: value.replace(/\s+/g, ' ').trim().slice(0, 200)});
    }
    if (!(rel in ARBITRARY_ALLOWED)) {
        for (const m of code.matchAll(ARBITRARY_VALUE_RE)) {
            const value = m[1];
            const rolesOnly = !LITERAL_IN_VALUE_RE.test(value) && [...value.matchAll(/var\(--([\w-]+)/g)].every((v) => v[1].startsWith('lf-'));
            if (COLOUR_IN_VALUE_RE.test(value) && !rolesOnly) out.push({rule: 'G4', file: rel, line: lineAt(code, m.index ?? 0), text: m[0]});
        }
        for (const m of code.matchAll(ARBITRARY_VARIABLE_RE)) {
            if (!m[1].startsWith('--lf-')) out.push({rule: 'G4', file: rel, line: lineAt(code, m.index ?? 0), text: m[0]});
        }
    }
    if (rel.endsWith('.svelte')) {
        const constants = constantsOf(rel, code, moduleConstants);
        for (const {tag, index, attributes} of startTags(markupOf(code))) {
            const classes = elementClasses(attributes, constants);
            const line = lineAt(code, index);
            for (const text of oneTernaryViolations(classes)) out.push({rule: 'G5', file: rel, line, text});
            const field = nativeFieldViolation(tag, attributes, classes);
            if (field) out.push({rule: 'G6', file: rel, line, text: field});
        }
    }
    return out;
}

/** G1–G6 on every production source. */
export function grammarOfTree(srcDir = SRC_DIR, names = roleNames(readTokens())) {
    const sources = listSources(srcDir);
    const known = new Set(sources);
    /** @type {Map<string, Map<string, string>>} */
    const constants = new Map();
    const moduleConstants = (/** @type {string} */ rel) => {
        if (!known.has(rel)) return null;
        let own = constants.get(rel);
        if (!own) {
            own = stringConstants(sourceCode(srcDir, rel));
            constants.set(rel, own);
        }
        return own;
    };
    /** @type {GrammarViolation[]} */
    const out = [];
    for (const rel of sources) out.push(...grammarOfCode(rel, sourceCode(srcDir, rel), names, moduleConstants));
    return out;
}

// ---------------------------------------------------------------------------------------------------------------------
// tokens.css: the roles, their utilities, their colours
// ---------------------------------------------------------------------------------------------------------------------

/** The four blocks of tokens.css, by their exact selector. */
export const TOKEN_BLOCKS = {light: ':root, html.light, .light', derived: ':root, .light, .dark', dark: 'html.dark, .dark', utilities: '@theme inline'};

/** @typedef {{light: Map<string, string>, derived: Map<string, string>, dark: Map<string, string>, utilities: Map<string, string>}} Tokens */

/** The declarations of tokens.css, block by block. */
export function parseTokens(/** @type {string} */ css) {
    /** @type {Tokens} */
    const tokens = {light: new Map(), derived: new Map(), dark: new Map(), utilities: new Map()};
    for (const block of blankCssComments(css).matchAll(/([^{}]*)\{([^{}]*)\}/g)) {
        const prelude = block[1].trim().replace(/\s+/g, ' ');
        const entry = Object.entries(TOKEN_BLOCKS).find(([, selector]) => selector === prelude);
        if (!entry) throw new Error(`tokens.css: unexpected block «${prelude}»`);
        const map = tokens[/** @type {keyof Tokens} */ (entry[0])];
        for (const declaration of block[2].matchAll(/(--[\w-]+)\s*:\s*([^;]+);/g)) {
            if (map.has(declaration[1])) throw new Error(`tokens.css: ${declaration[1]} declared twice in «${prelude}»`);
            map.set(declaration[1], declaration[2].trim());
        }
    }
    return tokens;
}

export function readTokens(path = TOKENS_CSS) {
    return parseTokens(readFileSync(path, 'utf8'));
}

/** The role names the utilities accept: `card` for `bg-lf-card` (G2). */
export function roleNames(/** @type {Tokens} */ tokens) {
    return new Set([...tokens.utilities.keys()].map((key) => key.replace(/^--color-lf-/, '')));
}

/** A role's declared value for a theme, as `<html>` resolves it: the theme's own block beats the derived one. */
export function tokenValue(/** @type {Tokens} */ tokens, /** @type {string} */ name, /** @type {'light' | 'dark'} */ theme) {
    return (theme === 'dark' ? tokens.dark : tokens.light).get(name) ?? tokens.derived.get(name);
}

/** @typedef {{r: number, g: number, b: number, alpha: number}} Rgba  sRGB channels and alpha, 0–1 */

const toLinear = (/** @type {number} */ c) => (c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4);
const toGamma = (/** @type {number} */ c) => (c <= 0.0031308 ? 12.92 * c : 1.055 * c ** (1 / 2.4) - 0.055);

/** sRGB → OKLab (Björn Ottosson). */
function toOklab(/** @type {Rgba} */ {r, g, b}) {
    const [lr, lg, lb] = [r, g, b].map(toLinear);
    const l = Math.cbrt(0.4122214708 * lr + 0.5363325363 * lg + 0.0514459929 * lb);
    const m = Math.cbrt(0.2119034982 * lr + 0.6806995451 * lg + 0.1073969566 * lb);
    const s = Math.cbrt(0.0883024619 * lr + 0.2817188376 * lg + 0.6299787005 * lb);
    return [0.2104542553 * l + 0.793617785 * m - 0.0040720468 * s, 1.9779984951 * l - 2.428592205 * m + 0.4505937099 * s, 0.0259040371 * l + 0.7827717662 * m - 0.808675766 * s];
}

/** OKLab → sRGB, clipped to the gamut. */
function fromOklab(/** @type {number[]} */ [L, a, b], alpha = 1) {
    const l = (L + 0.3963377774 * a + 0.2158037573 * b) ** 3;
    const m = (L - 0.1055613458 * a - 0.0638541728 * b) ** 3;
    const s = (L - 0.0894841775 * a - 1.291485548 * b) ** 3;
    const clip = (/** @type {number} */ c) => Math.min(1, Math.max(0, toGamma(c)));
    return {r: clip(4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s), g: clip(-1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s), b: clip(-0.0041960863 * l - 0.7034186147 * m + 1.707614701 * s), alpha};
}

/** Split `a, b(c, d), e` at its top-level commas. */
function topLevelParts(/** @type {string} */ text) {
    /** @type {string[]} */
    const parts = [];
    let depth = 0;
    let start = 0;
    for (let i = 0; i < text.length; i++) {
        if (text[i] === '(') depth += 1;
        else if (text[i] === ')') depth -= 1;
        else if (text[i] === ',' && depth === 0) {
            parts.push(text.slice(start, i).trim());
            start = i + 1;
        }
    }
    parts.push(text.slice(start).trim());
    return parts;
}

/**
 * The colour of a token expression for a theme: a hex, `transparent`, `var(--x)` or `color-mix(in oklab, A p, B)`, or
 * `in srgb` — the forms tokens.css uses. Mixing follows CSS Color 5: premultiplied alpha, in OKLab, or in the
 * gamma-encoded sRGB channels for `in srgb` (round 3: the tints of the categories, as the designer computed them).
 * @param {Tokens} tokens
 * @param {string} expression
 * @param {'light' | 'dark'} theme
 * @returns {Rgba}
 */
export function resolveColour(tokens, expression, theme, depth = 0) {
    if (depth > 20) throw new Error(`tokens.css: «${expression}» refers to itself`);
    const text = expression.trim();
    const reference = /^var\((--[\w-]+)\)$/.exec(text);
    if (reference) {
        const value = tokenValue(tokens, reference[1], theme);
        if (value === undefined) throw new Error(`tokens.css: ${reference[1]} is not declared for the ${theme} theme`);
        return resolveColour(tokens, value, theme, depth + 1);
    }
    if (text === 'transparent') return {r: 0, g: 0, b: 0, alpha: 0};
    const hex = /^#([0-9a-f]{6}|[0-9a-f]{3})$/i.exec(text);
    if (hex) {
        const digits = normalizeHex(text).slice(1);
        return {r: parseInt(digits.slice(0, 2), 16) / 255, g: parseInt(digits.slice(2, 4), 16) / 255, b: parseInt(digits.slice(4, 6), 16) / 255, alpha: 1};
    }
    const mix = /^color-mix\(in (oklab|srgb),([\s\S]*)\)$/.exec(text);
    if (mix) {
        const parts = topLevelParts(mix[2]);
        if (parts.length !== 2) throw new Error(`tokens.css: «${text}» is not a two-colour mix`);
        const [[c1, p1], [c2, p2]] = parts.map((part) => {
            const m = /^(\S+(?:\([^)]*\))?)\s*(.*)$/.exec(part);
            if (!m) throw new Error(`tokens.css: cannot read «${part}»`);
            let share = m[2].trim();
            const shareReference = /^var\((--[\w-]+)\)$/.exec(share);
            if (shareReference) share = tokenValue(tokens, shareReference[1], theme) ?? '';
            return /** @type {[Rgba, number]} */ ([resolveColour(tokens, m[1], theme, depth + 1), share ? parseFloat(share) / 100 : NaN]);
        });
        const w1 = Number.isNaN(p1) ? (Number.isNaN(p2) ? 0.5 : 1 - p2) : p1;
        const w2 = Number.isNaN(p2) ? 1 - w1 : p2;
        const alpha = c1.alpha * w1 + c2.alpha * w2;
        if (alpha === 0) return {r: 0, g: 0, b: 0, alpha: 0};
        if (mix[1] === 'srgb') {
            const channel = (/** @type {'r' | 'g' | 'b'} */ key) => (c1[key] * c1.alpha * w1 + c2[key] * c2.alpha * w2) / alpha;
            return {r: channel('r'), g: channel('g'), b: channel('b'), alpha};
        }
        const [a, b] = [toOklab(c1), toOklab(c2)];
        return fromOklab(
            a.map((v, i) => (v * c1.alpha * w1 + b[i] * c2.alpha * w2) / alpha),
            alpha,
        );
    }
    throw new Error(`tokens.css: cannot resolve «${text}»`);
}

/** A colour over an opaque one, as the browser composites it. */
export function over(/** @type {Rgba} */ top, /** @type {Rgba} */ bottom) {
    const a = top.alpha;
    return {r: top.r * a + bottom.r * (1 - a), g: top.g * a + bottom.g * (1 - a), b: top.b * a + bottom.b * (1 - a), alpha: 1};
}

/** WCAG 2.2 contrast ratio; a translucent foreground is composited over the background first. */
export function contrastRatio(/** @type {Rgba} */ foreground, /** @type {Rgba} */ background) {
    const luminance = (/** @type {Rgba} */ c) => 0.2126 * toLinear(c.r) + 0.7152 * toLinear(c.g) + 0.0722 * toLinear(c.b);
    const fg = luminance(foreground.alpha < 1 ? over(foreground, background) : foreground);
    const bg = luminance(background);
    return (Math.max(fg, bg) + 0.05) / (Math.min(fg, bg) + 0.05);
}

/** `#rrggbb`, for messages. */
export function toHex(/** @type {Rgba} */ {r, g, b}) {
    return (
        '#' +
        [r, g, b]
            .map((c) =>
                Math.round(c * 255)
                    .toString(16)
                    .padStart(2, '0'),
            )
            .join('')
    );
}

// ---------------------------------------------------------------------------------------------------------------------
// app.css: the legacy dark remap
// ---------------------------------------------------------------------------------------------------------------------

/** The classes the legacy dark remap rewrites: `html.dark .hover\:bg-gray-100:hover` gives `hover:bg-gray-100`. */
export function p1Classes(css = readFileSync(APP_CSS, 'utf8')) {
    /** @type {Set<string>} */
    const out = new Set();
    for (const m of blankCssComments(css).matchAll(/html\.dark\s+\.((?:\\.|[\w-])+)/g)) out.add(m[1].replace(/\\(.)/g, '$1'));
    return [...out].sort(byText);
}

/** How many times production code writes the class `name` itself (not a variant of it); C4 retires dead rules. */
export function classUses(/** @type {string} */ name, srcDir = SRC_DIR) {
    const escaped = name.replace(/[.*+?^${}()|[\]\\/]/g, '\\$&');
    const re = new RegExp(`(?:(?<=class:)|(?<![\\w:/.\\[\\]-]))${escaped}(?![\\w:/.-])`, 'g');
    let uses = 0;
    for (const rel of listSources(srcDir)) uses += [...sourceCode(srcDir, rel).matchAll(re)].length;
    return uses;
}

// ---------------------------------------------------------------------------------------------------------------------
// Command line
// ---------------------------------------------------------------------------------------------------------------------

/** `frontend/src/lib/x.svelte`, `src/lib/x.svelte` and `lib/x.svelte` all name `lib/x.svelte`. */
function underSrc(/** @type {string} */ path) {
    return path
        .trim()
        .replace(/\\/g, '/')
        .replace(/^(?:\.\/)?(?:frontend\/)?(?:src\/)?/, '');
}

/** The area of a file, for the report: `lib/components/assets`, `routes/(app)/fx`, `lib/utils`. */
function areaOf(/** @type {string} */ rel) {
    const parts = rel.split('/');
    if ((parts[0] === 'lib' && (parts[1] === 'components' || parts[1] === 'features')) || (parts[0] === 'routes' && parts[1] === '(app)')) return parts.slice(0, 3).join('/');
    return parts.slice(0, Math.min(2, parts.length - 1) || 1).join('/');
}

/** @param {import('node:fs').PathLike} _ */
const shown = (_) => relative(process.cwd(), String(_)) || '.';

function printVerdict(/** @type {{violations: Violation[], drops: Drop[], moves: {from: string, to: string}[]}} */ verdict, /** @type {GrammarViolation[]} */ grammar) {
    for (const v of verdict.violations) console.log(`  ${v.rule} ${v.metric} ${v.file ?? '(total)'}${v.from && v.from !== v.file ? ` (was ${v.from})` : ''}: ${v.detail}`);
    for (const g of grammar) console.log(`  ${g.rule} ${g.file}:${g.line}  ${g.text}`);
}

function report(/** @type {Scan} */ scan, /** @type {Baseline} */ baseline) {
    const totals = totalsOf(scan.files.values());
    const was = totalsOf(baseline.files.values());
    console.log(`Legacy colours: m1 ${totals.m1} classes (baseline ${was.m1}), m2 ${totals.m2} literals (baseline ${was.m2}), in ${scan.files.size} files.`);
    /** @type {Map<string, {m1: number, m2: number, files: number}>} */
    const areas = new Map();
    for (const [rel, measure] of scan.files) {
        const area = areas.get(areaOf(rel)) ?? {m1: 0, m2: 0, files: 0};
        area.m1 += measure.m1;
        area.m2 += measure.m2.length;
        area.files += 1;
        areas.set(areaOf(rel), area);
    }
    console.log('\nBy area (m1, m2, files):');
    for (const [area, n] of [...areas].sort(([, a], [, b]) => b.m1 + b.m2 - (a.m1 + a.m2)).slice(0, 25)) console.log(`  ${String(n.m1).padStart(6)} ${String(n.m2).padStart(5)} ${String(n.files).padStart(4)}  ${area}`);
    console.log('\nThe 20 files with the most legacy classes:');
    for (const [rel, measure] of [...scan.files].sort(([, a], [, b]) => b.m1 - a.m1).slice(0, 20)) console.log(`  ${String(measure.m1).padStart(6)} ${String(measure.m2.length).padStart(5)}  ${rel}`);
}

/** @param {string[]} argv */
function main(argv) {
    const flag = (/** @type {string} */ name) => argv.includes(name);
    const option = (/** @type {string} */ name) => {
        const at = argv.indexOf(name);
        return at === -1 ? undefined : argv[at + 1];
    };
    try {
        if (flag('--init')) {
            if (existsSync(BASELINE) && !flag('--force')) throw new Error(`${shown(BASELINE)} exists: --init writes the first baseline only (--force to overwrite)`);
            const scan = scanTree();
            writeBaseline(baselineOf(scan));
            const totals = totalsOf(scan.files.values());
            console.log(`Wrote ${shown(BASELINE)}: ${scan.files.size} files, m1 ${totals.m1}, m2 ${totals.m2}.`);
            return 0;
        }
        if (flag('--resolve')) {
            writeBaseline(resolveConflict());
            console.log(`Resolved ${shown(BASELINE)}: a three-way merge, an accepting side keeping its file, otherwise the tighter side winning. Next: \`git add\` it, then --check on the merged tree.`);
            return 0;
        }
        const scan = scanTree();
        const baseline = readBaseline();
        if (flag('--update')) {
            const {baseline: next, refused} = tightenBaseline(scan, baseline);
            if (refused.length) {
                console.log('Not recorded: the baseline is never widened.');
                for (const rel of refused) {
                    console.log(rel.startsWith(CENTRAL_PREFIX) ? `  ${rel}: a central table that would lift the total (R1)` : `  ${rel}: a new file with legacy colours (move them to roles, or declare the split with --split)`);
                }
                return 1;
            }
            writeBaseline(next);
            const before = totalsOf(baseline.files.values());
            const after = totalsOf(next.files.values());
            console.log(`Tightened ${shown(BASELINE)}: m1 ${before.m1} → ${after.m1}, m2 ${before.m2} → ${after.m2}.`);
            return 0;
        }
        const split = option('--split');
        if (split !== undefined) {
            const colon = split.indexOf(':');
            if (colon <= 0) throw new Error('--split OLD:NEW1,NEW2 — paths under frontend/src');
            const from = underSrc(split.slice(0, colon));
            const into = split
                .slice(colon + 1)
                .split(',')
                .map(underSrc)
                .filter(Boolean);
            writeBaseline(declareSplit(scan, baseline, from, into));
            console.log(`Declared: ${from} split into ${into.join(', ')}. The new lines and the ~split line go in the same commit as the split.`);
            return 0;
        }
        const accepted = option('--accept');
        if (accepted !== undefined) {
            writeBaseline(acceptFile(scan, baseline, underSrc(accepted), option('--reason') ?? ''));
            console.log(`Accepted ${underSrc(accepted)} as it is; the reason is on record.`);
            return 0;
        }
        const verdict = compareWithBaseline(scan, baseline);
        const grammar = grammarOfTree();
        if (flag('--report')) {
            report(scan, baseline);
            console.log(`\nRatchet: ${verdict.violations.length} violations, ${verdict.drops.length} files dropped (--update tightens), ${verdict.moves.length} moves recognized. Grammar: ${grammar.length} violations.`);
            printVerdict(verdict, grammar);
            return 0;
        }
        if (verdict.violations.length || grammar.length) {
            console.log('Colour gates: violations');
            printVerdict(verdict, grammar);
            return 1;
        }
        console.log(`Colour gates: clean (${verdict.drops.length} files dropped below their record; --update tightens).`);
        return 0;
    } catch (error) {
        console.error(`theme-roles: ${error instanceof Error ? error.message : String(error)}`);
        return 2;
    }
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) process.exitCode = main(process.argv.slice(2));
