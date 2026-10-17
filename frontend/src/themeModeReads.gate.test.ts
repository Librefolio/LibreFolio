/**
 * Gate: the page theme is read and watched in one place, `$lib/theme/themeMode` (colour workstream R, W8 — the
 * developer's decision D4).
 *
 * ## What this protects
 *
 * The theme is the `dark` class of `<html>`: the anti-FOUC script of `src/app.html` writes it before any bundle loads,
 * `applyTheme()` in `src/lib/stores/app/themeStore.ts` on every switch. Until W8, 18 components read it inline — the
 * charts under `src/lib/components/{charts,dashboard,risk,brokers/lots}`, the spreadsheet preview of
 * `files/FilePreviewModal.svelte` and the result views of the PAC allocator — and 16 of them watched it inline too, each
 * with its own copy of two forms:
 *
 *     document.documentElement.classList.contains('dark')
 *     observer.observe(document.documentElement, {attributes: true, attributeFilter: ['class']})
 *
 * W8 moved both into `src/lib/theme/themeMode.ts`: `isDarkTheme()`, and `onThemeClassChange(onChange)`, which returns
 * the observer, already observing, for the component to `disconnect()` when it goes away. D4 settled what the helper
 * watches: every change of the class of `<html>`, not only of `dark` — the Designer Lab relies on the charts redrawing
 * on each one. `src/lib/theme/themeMode.test.ts` pins that behaviour; this gate keeps it the only one there is. Every
 * way back is silent:
 *
 *   - a new inline read works, and is one more place to find the day the theme stops being a class of `<html>` — the
 *     one nobody remembers;
 *   - a new inline observer works too, and can quietly differ: a filter on `dark` alone (the Lab's redraws stop), no
 *     filter at all (a redraw for every `lang` or `data-*` written on `<html>`), `subtree` (a redraw for every class
 *     change in the page);
 *   - an observer nobody keeps, or keeps and never disconnects, outlives its component: it goes on redrawing a destroyed
 *     chart on every theme change, for the rest of the session — no error, no console line, only work and memory.
 *
 * ## The rule, as this file checks it
 *
 *   (a) No direct read of the theme class: no `classList.contains('dark')` — whatever the receiver, in any quote (`'`,
 *       `"`, a backtick), with spaces or line breaks between its tokens, through `?.` too. Writes are legal:
 *       `classList.add`, `remove` and `toggle` are how `app.html` and the theme store set the class. Read it with
 *       `isDarkTheme()`.
 *   (b) No MutationObserver on the class of `<html>`: no `.observe(<…>documentElement, <options>)` whose options can see
 *       a change of `class`. The options are read as the DOM reads them, across lines: attributes are observed when
 *       `attributes` is `true`, or absent beside an `attributeFilter` or an `attributeOldValue: true`; then every
 *       attribute, or those the filter lists. Options the gate cannot evaluate — a variable, a spread, a computed key,
 *       a flag or a filter entry that is not a literal — fail too: write them inline, or, for the theme, use
 *       `onThemeClassChange()`. Watching `<html>` for anything else is legal: its children, another attribute, its size
 *       (a ResizeObserver: one argument — `MutationObserver.observe(target)` with no options throws).
 *   (c) Every call of `onThemeClassChange(` is assigned to a name — `observer = onThemeClassChange(…)`, or
 *       `const observer = onThemeClassChange(…)`, a type annotation allowed — and that name is `.disconnect()`ed, or
 *       `?.disconnect()`ed, in the same file.
 *   (d) The scan reads something: `themeMode.ts` exists and the scanner finds there exactly the one read (a) looks for
 *       and the one observation (b) looks for; at least one file imports `$lib/theme/themeMode`; (c) finds calls to
 *       check, in every file that imports `onThemeClassChange`; the walk reaches the components. Every check above also
 *       passes on a scanner that reads the wrong directory, or whose patterns match nothing.
 *
 * Every check is a pure function of a `{path: text}` tree, read as the walk reads `src`: a path the walk would not open
 * is dropped from a synthetic tree too. The scanner is first run on synthetic trees that break each rule once — the
 * proof that each check can fail — and then on the files of `src`. Comments are blanked before anything is matched: a
 * comment that quotes the old forms reads nothing. Everything is found by content, never by line: line numbers appear
 * in the messages only.
 *
 * ## What it cannot see
 *
 * It reads source text, not a running page, and its forms are a floor:
 *
 *   - `<html>` under another name. (b) knows the target only as an expression ending in `documentElement`, written in
 *     the call: an alias (`const html = document.documentElement; observer.observe(html, …)`),
 *     `document.querySelector('html')`, `document.firstElementChild`, or `document` itself with `subtree: true`, all
 *     pass. `AllocationHistoryChart.svelte` is a live case, and a legal one: its visibility observers climb the chart's
 *     ancestors up to `<html>` with `attributeFilter: ['class', 'style', 'hidden']`, so they are handed every theme
 *     change too — and ignore it, unless the chart was shown or hidden.
 *   - The theme read another way: `matches('.dark')`, `closest('.dark')`, `className.includes('dark')`,
 *     `getAttribute('class')`, `document.querySelector('.dark')` — or not read from the DOM at all: the theme store's
 *     value, or `matchMedia('(prefers-color-scheme: dark)')`, which is the system's preference, not the page's theme.
 *     (a) does not ask whose `classList` it reads, so an alias does not hide a read.
 *   - (c) matches names in the file, not in their scope: another variable of the same name, disconnected elsewhere in
 *     the file, satisfies it; and that the disconnect runs — that it sits in the cleanup the component's destruction
 *     calls — is not checked. An observer created inside a larger expression (a ternary, an array, a `return`) is
 *     reported as unassigned, conservatively. A call under another name — `onThemeClassChange` imported with `as`, or
 *     kept in a variable and called through it — is not seen by (c); (d) fails a file that imports it and never calls
 *     it by its name, which catches the first, and the second when it is the file's only use.
 *   - Comment blanking is a floor: a `//` inside a string swallows the rest of its line, a `/*` inside a regular
 *     expression literal everything up to the next comment end. Blanking only removes text, so it can hide a read,
 *     never invent one; a string that spells a read or an observation out, though, is reported as one.
 *
 * The walk reads every `.svelte`, `.ts`, `.js` and `.html` under `src` but two groups, which it does not even open —
 * nor does it enter `node_modules`:
 *
 *   - the tests: every `*.test.ts` — this file among them, its synthetic trees made of the very forms it rejects, and
 *     `themeMode.test.ts`, which toggles the class and observes it on purpose — and everything under a `__tests__/` or
 *     `__mocks__/` directory, harnesses and fixtures included;
 *   - the Designer Lab, `src/lib/dev/designer-lab/` and `src/routes/designer-lab/`, matched as path prefixes (absent
 *     from some checkouts). D7, a developer decision of R, exempts the paths of L, the Lab's workstream, entirely: the
 *     Lab drives the theme of the page live, as its job. Its third path, `frontend/scripts/designer-lab/`, lies outside
 *     `src` and is not read anyway.
 *
 * And one file it opens for (d) alone: `src/lib/theme/themeMode.ts`, the one allowed reader, to which (a)–(c) do not
 * apply.
 *
 * Registered in `front_utility_unit` (`scripts/test_runner/_frontend_utility.py`, action `core-unit`).
 */

import {describe, expect, it} from 'vitest';
import {readdirSync, readFileSync} from 'node:fs';
import {dirname, join, posix, resolve} from 'node:path';
import {fileURLToPath} from 'node:url';

/** `frontend/`: every path is read, and reported, relative to it. */
const FRONTEND = resolve(dirname(fileURLToPath(import.meta.url)), '..');

/** The one reader of the theme: exempt from (a)–(c), and the positive control of (a) and (b). */
const THEME_MODE = 'src/lib/theme/themeMode.ts';

/** The specifier the components import it by. */
const THEME_MODE_SPECIFIER = '$lib/theme/themeMode';

/** The Designer Lab (D7), matched as path prefixes: the walk does not read it at all. It drives the theme of the page live — its job, and every form (a)–(c) reject. */
const DESIGNER_LAB = ['src/lib/dev/designer-lab/', 'src/routes/designer-lab/'];

/** The types the walk reads: every one that can hold a script. */
const SCANNED = /\.(svelte|ts|js|html)$/;

/** Files by path, relative to `frontend/`: the files of `src`, or a synthetic tree. */
type Tree = Record<string, string>;

// ---------------------------------------------------------------------------
// Reading
// ---------------------------------------------------------------------------

const lineAt = (text: string, offset: number): number => text.slice(0, offset).split('\n').length;
const collapse = (s: string): string => s.trim().replace(/\s+/g, ' ');
const isMarkup = (file: string): boolean => file.endsWith('.html') || file.endsWith('.svelte');

/** Replace every match with spaces, keeping newlines: offsets and line numbers survive the blanking. */
function blank(text: string, pattern: RegExp): string {
    return text.replace(pattern, (found) => found.replace(/[^\n]/g, ' '));
}

const blankCssComments = (css: string): string => blank(css, /\/\*[\s\S]*?\*\//g);
/** `//` counts as a comment only when it does not follow `:` — `https://` stays code. */
const blankJsComments = (js: string): string => blank(blank(js, /\/\*[\s\S]*?\*\//g), /(?<![:\\])\/\/[^\n]*/g);

/** A file with its comments blanked the way its type means them: a script as JS, markup as HTML — and the scripts and styles of markup each by their own syntax. */
function codeOf(file: string, text: string): string {
    if (!isMarkup(file)) return blankJsComments(text);
    let out = blank(text, /<!--[\s\S]*?-->/g);
    out = out.replace(/(<script\b[^>]*>)([\s\S]*?)(<\/script\s*>)/gi, (_m, open: string, body: string, close: string) => open + blankJsComments(body) + close);
    out = out.replace(/(<style\b[^>]*>)([\s\S]*?)(<\/style\s*>)/gi, (_m, open: string, body: string, close: string) => open + blankCssComments(body) + close);
    return out;
}

/** The code around an offset, on its own line, for a message: enough to recognise the statement, never a whole minified line. */
function excerptAt(code: string, offset: number): string {
    const start = code.lastIndexOf('\n', offset - 1) + 1;
    const newline = code.indexOf('\n', offset);
    const end = newline === -1 ? code.length : newline;
    const from = Math.max(start, offset - 60);
    const to = Math.min(end, offset + 90);
    return `${from > start ? '…' : ''}${collapse(code.slice(from, to))}${to < end ? '…' : ''}`;
}

/** A call that may span lines, from the start of its first line up to `end`, collapsed onto one line for a message. */
function excerptOfCall(code: string, offset: number, end: number): string {
    const start = code.lastIndexOf('\n', offset - 1) + 1;
    const from = Math.max(start, offset - 60);
    const text = collapse(code.slice(from, end));
    return `${from > start ? '…' : ''}${text.length > 200 ? `${text.slice(0, 199)}…` : text}`;
}

const isQuote = (c: string): boolean => c === "'" || c === '"' || c === '`';

/** The offset of the quote that closes the string literal opening at `open`, backslash escapes honoured; -1 when it never closes. */
function endOfString(code: string, open: number): number {
    for (let i = open + 1; i < code.length; i++) {
        if (code[i] === '\\') i++;
        else if (code[i] === code[open]) return i;
    }
    return -1;
}

/** The offset of the bracket that closes the one at `open` — `(`, `[` or `{` — string literals skipped whole; -1 when it never closes. */
function closingOf(code: string, open: number): number {
    let depth = 0;
    for (let i = open; i < code.length; i++) {
        const c = code[i];
        if (isQuote(c)) {
            i = endOfString(code, i);
            if (i === -1) return -1;
        } else if (c === '(' || c === '[' || c === '{') depth++;
        else if (c === ')' || c === ']' || c === '}') {
            depth--;
            if (depth === 0) return i;
        }
    }
    return -1;
}

/** A list split at its top-level commas — not those inside brackets, parentheses or string literals — each item trimmed, a trailing empty one dropped; `null` when a string never closes. */
function splitTopLevel(text: string): string[] | null {
    const items: string[] = [];
    let depth = 0;
    let start = 0;
    for (let i = 0; i < text.length; i++) {
        const c = text[i];
        if (isQuote(c)) {
            i = endOfString(text, i);
            if (i === -1) return null;
        } else if (c === '(' || c === '[' || c === '{') depth++;
        else if (c === ')' || c === ']' || c === '}') depth--;
        else if (c === ',' && depth === 0) {
            items.push(text.slice(start, i).trim());
            start = i + 1;
        }
    }
    items.push(text.slice(start).trim());
    if (items[items.length - 1] === '') items.pop();
    return items;
}

// ---------------------------------------------------------------------------
// What the scanner reads
// ---------------------------------------------------------------------------

interface Finding {
    file: string;
    line: number;
    /** Where it starts in the code of its file: the mutations of the last test splice there. */
    offset: number;
    excerpt: string;
}

/** (a) `classList.contains('dark')`: any receiver, any quote, spaces and line breaks between the tokens, `?.` too. */
const CLASS_READ = /\bclassList\s*\??\.\s*contains\s*\(\s*(['"`])dark\1\s*[,)]/g;

/** (a) Every read of the theme class in the code of a file. */
function readsIn(file: string, code: string): Finding[] {
    return [...code.matchAll(CLASS_READ)].map((match) => ({file, line: lineAt(code, match.index), offset: match.index, excerpt: excerptAt(code, match.index)}));
}

/** (b) A call of a method named `observe` — `.observe(` or `?.observe(` — whatever the receiver: a MutationObserver's, a ResizeObserver's, any other. */
const OBSERVE_CALL = /\.\s*observe\s*\(/g;

/** (b) `<html>` as a call names it: an expression ending in `documentElement` — `document.documentElement`, `window.document.documentElement`, `node.ownerDocument.documentElement`, a `documentElement` destructured from `document`. */
const HTML_TARGET = /^(?:[\w$]+\s*\??\.\s*)*documentElement$/;

/** (b) A string literal with its text in group 1, 2 or 3 — no escape, no interpolation: the only filter entry the gate reads. */
const STRING_LITERAL = /^(?:'([^'\\]*)'|"([^"\\]*)"|`([^`\\$]*)`)$/;

/** What the options of an `observe()` call can see of the class of its target: its changes, none of them, or — the gate cannot tell — `unreadable`. */
type Sight = 'class' | 'not-class' | 'unreadable';

/**
 * (b) Options read as the DOM reads them: attributes are observed when `attributes` is `true`, or absent beside an
 * `attributeFilter` or an `attributeOldValue: true`; then every attribute, or those the filter lists. No options at all is
 * no MutationObserver that observes anything — `observe(target)` throws — but a ResizeObserver or an IntersectionObserver.
 */
function sightOf(options: string | undefined): Sight {
    if (options === undefined) return 'not-class';
    const literal = /^\{([\s\S]*)\}$/.exec(options);
    const properties = literal ? splitTopLevel(literal[1]) : null;
    if (!properties) return 'unreadable';
    const values = new Map<string, string>();
    for (const property of properties) {
        const keyed = /^(?:(['"])([\w$]+)\1|([\w$]+))\s*:([\s\S]*)$/.exec(property);
        if (keyed) values.set(keyed[2] ?? keyed[3], keyed[4].trim());
        // A shorthand property: its value is the variable of that name.
        else if (/^[\w$]+$/.test(property)) values.set(property, property);
        // A spread, a computed key, a method: any key may hide behind it.
        else return 'unreadable';
    }
    const flag = (key: string): boolean | null | undefined => {
        const value = values.get(key);
        if (value === undefined) return undefined;
        return value === 'true' ? true : value === 'false' ? false : null;
    };
    const attributes = flag('attributes');
    const oldValue = flag('attributeOldValue');
    if (attributes === null || oldValue === null) return 'unreadable';
    let filter: string[] | undefined;
    const filterValue = values.get('attributeFilter');
    if (filterValue !== undefined) {
        const list = /^\[([\s\S]*)\]$/.exec(filterValue);
        const entries = list ? splitTopLevel(list[1]) : null;
        if (!entries) return 'unreadable';
        const names = entries.map((entry) => {
            const string = STRING_LITERAL.exec(entry);
            return string ? (string[1] ?? string[2] ?? string[3]) : undefined;
        });
        // An entry the gate cannot read may be 'class' — unless a readable one already is.
        if (names.includes(undefined) && !names.includes('class')) return 'unreadable';
        filter = names.filter((name): name is string => name !== undefined);
    }
    const observesAttributes = attributes === true || (attributes === undefined && (filter !== undefined || oldValue === true));
    if (!observesAttributes) return 'not-class';
    return filter === undefined || filter.includes('class') ? 'class' : 'not-class';
}

interface Observation extends Finding {
    /** The first argument, as written. */
    target: string;
    /** Whether the target is `<html>`, as (b) knows it. */
    html: boolean;
    sight: Sight;
}

/** (b) Every `observe()` call in the code of a file, with its target and what its options can see of the target's class. Arguments the gate cannot even delimit are `unreadable`. */
function observationsIn(file: string, code: string): Observation[] {
    return [...code.matchAll(OBSERVE_CALL)].map((match) => {
        const open = match.index + match[0].length - 1;
        const close = closingOf(code, open);
        const args = close === -1 ? null : splitTopLevel(code.slice(open + 1, close));
        const target = (args ? (args[0] ?? '') : (/^[^,)]*/.exec(code.slice(open + 1))?.[0] ?? '')).trim();
        const lineEnd = code.indexOf('\n', open);
        const end = close !== -1 ? close + 1 : lineEnd === -1 ? code.length : lineEnd;
        return {file, line: lineAt(code, match.index), offset: match.index, excerpt: excerptOfCall(code, match.index, end), target, html: HTML_TARGET.test(target), sight: args ? sightOf(args[1]) : 'unreadable'};
    });
}

/** (c) A call of `onThemeClassChange`, by its name or through a namespace (`themeMode.onThemeClassChange(`). */
const OBSERVER_CALL = /(?<![\w$])onThemeClassChange\s*\(/g;

/** (c) The declaration a call initialises — `const name = `, `let name: Type = ` — and the namespace of the call, if any. */
const DECLARED = /\b(?:const|let|var)\s+([\w$]+)\s*(?::[^=;]*)?=\s*(?:[\w$]+\s*\.\s*)?$/;

/** (c) The assignment a call is the value of — `name = `, `this.name = `, `name ??= ` — and the namespace of the call, if any. A name after a `:` or a `|` is a type, never the target. */
const ASSIGNED = /(?<![\w$])(?<![:|]\s*)([\w$]+)\s*(?:\?\?|\|\||&&)?=\s*(?:[\w$]+\s*\.\s*)?$/;

interface ObserverCall extends Finding {
    /** The name the observer is kept in; `null` when the call is not the value of an assignment. */
    name: string | null;
    /** Whether `<name>.disconnect(` or `<name>?.disconnect(` is called anywhere in the code of the file. */
    disconnected: boolean;
}

/** `<name>.disconnect(` or `<name>?.disconnect(`, on that very name and not on a longer one ending with it. */
const disconnectOf = (name: string): RegExp => new RegExp(`(?<![\\w$])${name.replace(/\$/g, '\\$')}\\s*\\??\\.\\s*disconnect\\s*\\(`);

/** (c) Every call of `onThemeClassChange` in the code of a file — its declaration aside — with the name it is kept in, and whether that name is disconnected. */
function observerCallsIn(file: string, code: string): ObserverCall[] {
    return [...code.matchAll(OBSERVER_CALL)].flatMap((match) => {
        const before = code.slice(Math.max(0, match.index - 200), match.index);
        if (/\bfunction\s*\*?\s*$/.test(before)) return [];
        const name = (DECLARED.exec(before) ?? ASSIGNED.exec(before))?.[1] ?? null;
        return [{file, line: lineAt(code, match.index), offset: match.index, excerpt: excerptAt(code, match.index), name, disconnected: name !== null && disconnectOf(name).test(code)}];
    });
}

/** (d) `import <clause> from '<specifier>'`. A clause holds no quote and no `;`, so one statement is never read into the next. */
const IMPORT = /\bimport\s+([^;'"]*?)\s*\bfrom\s*(['"])([^'"\n]+)\2/g;

/** (d) Whether an import specifier, written in `file`, names `themeMode.ts`: `$lib/theme/themeMode`, or a relative path to it, with or without its extension. */
function namesThemeMode(file: string, specifier: string): boolean {
    const path = specifier.startsWith('$lib/') ? `src/lib/${specifier.slice('$lib/'.length)}` : specifier.startsWith('.') ? posix.join(posix.dirname(file), specifier) : specifier;
    return path.replace(/\.[jt]s$/, '') === THEME_MODE.replace(/\.ts$/, '');
}

/** (d) The names a file imports from `themeMode.ts`, as it exports them (`onThemeClassChange as watch` is `onThemeClassChange`); `*` for a namespace. */
function themeModeImportsIn(file: string, code: string): string[] {
    const names: string[] = [];
    for (const match of code.matchAll(IMPORT)) {
        if (!namesThemeMode(file, match[3])) continue;
        if (/\*\s*as\b/.test(match[1])) names.push('*');
        for (const entry of /\{([^}]*)\}/.exec(match[1])?.[1].split(',') ?? []) {
            const name = /^\s*(?:type\s+)?([\w$]+)/.exec(entry)?.[1];
            if (name) names.push(name);
        }
    }
    return names;
}

// ---------------------------------------------------------------------------
// The checks: pure functions of a tree
// ---------------------------------------------------------------------------

const isDesignerLab = (file: string): boolean => DESIGNER_LAB.some((prefix) => file.startsWith(prefix));

/** Whether a path (relative to `frontend/`) is code this gate reads: a type that can hold a script, and neither a test (`*.test.ts`, anything under `__tests__/` or `__mocks__/`), a dependency, nor the Designer Lab. The walk opens nothing else, and `audit` drops anything else from a synthetic tree. */
function isScanned(path: string): boolean {
    if (!SCANNED.test(path) || path.endsWith('.test.ts')) return false;
    if (path.split('/').some((segment) => segment === '__tests__' || segment === '__mocks__' || segment === 'node_modules')) return false;
    return !isDesignerLab(path);
}

interface Audit {
    /** Every file of the tree the scan reads (`isScanned`), sorted — `themeMode.ts` among them. */
    files: string[];
    /** (a) Every read of the theme class, `themeMode.ts`'s included. */
    reads: Finding[];
    /** (b) Every `observe()` call, whatever its target, `themeMode.ts`'s included. */
    observations: Observation[];
    /** (c) Every call of `onThemeClassChange`, outside `themeMode.ts`. */
    calls: ObserverCall[];
    /** (d) The names each file imports from `themeMode.ts`, for the files that import it. */
    imports: Map<string, string[]>;
}

/** What a tree holds, read as the walk reads `src`: a path `isScanned` refuses is dropped first, so a synthetic tree is judged as the files of `src` are. */
function audit(tree: Tree): Audit {
    const files = Object.keys(tree).filter(isScanned).sort();
    const result: Audit = {files, reads: [], observations: [], calls: [], imports: new Map()};
    for (const file of files) {
        const code = codeOf(file, tree[file]);
        result.reads.push(...readsIn(file, code));
        result.observations.push(...observationsIn(file, code));
        if (file === THEME_MODE) continue;
        result.calls.push(...observerCallsIn(file, code));
        const names = themeModeImportsIn(file, code);
        if (names.length > 0) result.imports.set(file, names);
    }
    return result;
}

const placeOf = (finding: Finding): string => `${finding.file}:${finding.line}`;
const outsideThemeMode = (finding: Finding): boolean => finding.file !== THEME_MODE;

/** (a) Every read of the theme class outside `themeMode.ts`. */
function directReads({reads}: Audit): string[] {
    return reads.filter(outsideThemeMode).map((read) => `${placeOf(read)}  ${read.excerpt}  → a direct read of the theme class: use isDarkTheme() from ${THEME_MODE_SPECIFIER}`);
}

/** (b) Every observation of `<html>` outside `themeMode.ts` that can see its class, or may. */
function htmlClassObservers({observations}: Audit): string[] {
    return observations
        .filter((observation) => outsideThemeMode(observation) && observation.html && observation.sight !== 'not-class')
        .map((observation) =>
            observation.sight === 'class'
                ? `${placeOf(observation)}  ${observation.excerpt}  → a MutationObserver on the class of <html>: use onThemeClassChange() from ${THEME_MODE_SPECIFIER}, and disconnect() the observer it returns`
                : `${placeOf(observation)}  ${observation.excerpt}  → an observation of <html> whose options this gate cannot read: write them inline, as an object literal — and if it watches the theme, use onThemeClassChange() from ${THEME_MODE_SPECIFIER}`,
        );
}

/** (c) Every observer `onThemeClassChange()` returns that nobody keeps, or that is kept and never disconnected. */
function leakingObservers({calls}: Audit): string[] {
    return calls.flatMap((call) => {
        if (call.name === null) return [`${placeOf(call)}  ${call.excerpt}  → the observer it returns is not kept: assign it (const observer = onThemeClassChange(…)) and call observer.disconnect() when the component is destroyed — an observer nobody keeps goes on redrawing a destroyed chart`];
        if (!call.disconnected) return [`${placeOf(call)}  ${call.excerpt}  → ${call.name} is never disconnected in this file: call ${call.name}.disconnect() in the cleanup of the effect or onMount that creates it — or it goes on redrawing a destroyed chart`];
        return [];
    });
}

/** (d) Whatever would let (a)–(c) pass by reading nothing. */
function emptyScans({files, reads, observations, calls, imports}: Audit): string[] {
    const problems: string[] = [];
    if (!files.includes(THEME_MODE)) problems.push(`${THEME_MODE}  not found: the one reader of the theme, and the control of (a) and (b)`);
    else {
        const ownReads = reads.filter((read) => !outsideThemeMode(read)).length;
        const ownObservations = observations.filter((observation) => !outsideThemeMode(observation) && observation.html && observation.sight === 'class').length;
        if (ownReads !== 1) problems.push(`${THEME_MODE}  the scanner finds ${ownReads} reads of the theme class there, expected exactly 1 — if isDarkTheme() now reads it another way, teach (a) the new form`);
        if (ownObservations !== 1) problems.push(`${THEME_MODE}  the scanner finds ${ownObservations} observations of the class of <html> there, expected exactly 1 — if onThemeClassChange() now observes it another way, teach (b) the new form`);
    }
    if (imports.size === 0) problems.push(`no file imports ${THEME_MODE_SPECIFIER}`);
    if (calls.length === 0) problems.push('no call of onThemeClassChange(): (c) checks nothing');
    for (const [file, names] of imports) {
        if (names.includes('onThemeClassChange') && !calls.some((call) => call.file === file)) problems.push(`${file}  imports onThemeClassChange, and (c) sees no call of it: call it by that name — under another one, (c) cannot check that its observer is kept and disconnected`);
    }
    if (!files.some((file) => file.endsWith('.svelte'))) problems.push('no .svelte file: the walk does not reach the components');
    return problems;
}

type Verdict = Record<'a' | 'b' | 'c' | 'd', string[]>;

/** What each check says about a tree: one list per check, all four empty when the tree keeps the rule. */
function verdictOf(tree: Tree): Verdict {
    const result = audit(tree);
    return {a: directReads(result), b: htmlClassObservers(result), c: leakingObservers(result), d: emptyScans(result)};
}

const CLEAN: Verdict = {a: [], b: [], c: [], d: []};

// ---------------------------------------------------------------------------
// The files of src
// ---------------------------------------------------------------------------

/** Every file under `dir` the scan reads (`isScanned`): no other file is opened, and `node_modules` is not even entered. */
function walk(dir: string, acc: string[] = []): string[] {
    for (const entry of readdirSync(join(FRONTEND, dir), {withFileTypes: true})) {
        const path = `${dir}/${entry.name}`;
        if (entry.isDirectory()) {
            if (entry.name !== 'node_modules') walk(path, acc);
        } else if (isScanned(path)) acc.push(path);
    }
    return acc;
}

let srcTreeCache: Tree | undefined;
let srcAuditCache: Audit | undefined;

/** The files of `src`, read once for every test below. */
function srcTree(): Tree {
    srcTreeCache ??= Object.fromEntries(walk('src').map((file) => [file, readFileSync(join(FRONTEND, file), 'utf8')]));
    return srcTreeCache;
}

/** The audit of the files of `src`, computed once. */
function srcAudit(): Audit {
    srcAuditCache ??= audit(srcTree());
    return srcAuditCache;
}

// ---------------------------------------------------------------------------
// Synthetic trees: one clean, then each rule broken once
// ---------------------------------------------------------------------------

const LINE_CHART = 'src/lib/components/charts/LineChart.svelte';
const GROWTH_CHART = 'src/lib/features/dashboard/GrowthChart.svelte';
const ALLOCATION_HISTORY = 'src/lib/features/dashboard/AllocationHistoryChart.svelte';
const OTHER_EFFECTS = 'src/lib/features/dashboard/OtherPeriodEffectsTable.svelte';
const HEADER = 'src/lib/components/layout/Header.svelte';
const RISK_CARD_GRID = 'src/lib/components/ui/display/RiskCardGrid.svelte';
const DEFERRED_POPUPS = 'src/lib/features/onboarding/components/DeferredAppPopups.svelte';
const SCROLL_ON_OVERFLOW = 'src/lib/actions/scrollOnOverflow.ts';
const VIEWPORT = 'src/lib/utils/layout/viewport.ts';
const APP_HTML = 'src/app.html';
const THEME_STORE = 'src/lib/stores/app/themeStore.ts';

/** `themeMode.ts` as W8 wrote it: one read, one observation — and a comment quoting the old read, which reads nothing. */
const THEME_MODE_TEXT = [
    '/**',
    " * The page theme: the `dark` class of `<html>`. Until W8, 18 components wrote `classList.contains('dark')` inline.",
    ' */',
    'export function isDarkTheme(): boolean {',
    "    return document.documentElement.classList.contains('dark');",
    '}',
    '',
    'export function onThemeClassChange(onChange: () => void): MutationObserver {',
    '    const observer = new MutationObserver(() => onChange());',
    "    observer.observe(document.documentElement, {attributes: true, attributeFilter: ['class']});",
    '    return observer;',
    '}',
    '',
].join('\n');

/** A chart after W8: a `const` observer disconnected by the cleanup it returns — and both old forms quoted, in a script comment and in a markup one. */
const LINE_CHART_TEXT = [
    '<script lang="ts">',
    "    import {onMount} from 'svelte';",
    "    import {isDarkTheme, onThemeClassChange} from '$lib/theme/themeMode';",
    '',
    '    let dark = $state(isDarkTheme());',
    '',
    '    onMount(() => {',
    "        // Was: dark = document.documentElement.classList.contains('dark');",
    "        /* and: new MutationObserver(redraw).observe(document.documentElement, {attributes: true, attributeFilter: ['class']}); */",
    '        const observer = onThemeClassChange(() => {',
    '            dark = isDarkTheme();',
    '        });',
    '        return () => observer.disconnect();',
    '    });',
    '</script>',
    '',
    "<!-- {#if document.documentElement.classList.contains('dark')} -->",
    "<div class:dark data-theme={isDarkTheme() ? 'dark' : 'light'}></div>",
    '',
].join('\n');

/** A chart after W8, the other shape: an observer declared at the top of the script, assigned in `onMount`, `?.disconnect()`ed — and a comment that names a bare call. */
const GROWTH_CHART_TEXT = [
    '<script lang="ts">',
    "    import {onMount} from 'svelte';",
    "    import {isDarkTheme, onThemeClassChange} from '$lib/theme/themeMode';",
    '',
    '    let darkModeObserver: MutationObserver | null = null;',
    '',
    '    function renderChart(forceFullXAxisRebuild = false): void {',
    '        void forceFullXAxisRebuild;',
    '        void isDarkTheme();',
    '    }',
    '',
    '    onMount(() => {',
    '        // Never a bare onThemeClassChange(renderChart): nobody could disconnect it.',
    '        darkModeObserver = onThemeClassChange(() => renderChart());',
    '        return () => {',
    '            darkModeObserver?.disconnect();',
    '        };',
    '    });',
    '</script>',
    '',
].join('\n');

/** The visibility observers of `AllocationHistoryChart`: the class of every ancestor of the chart, legal — and the theme through the helper. */
const ALLOCATION_HISTORY_TEXT = [
    '<script lang="ts">',
    "    import {onMount} from 'svelte';",
    "    import {onThemeClassChange} from '$lib/theme/themeMode';",
    '',
    '    let chartContainer: HTMLDivElement | undefined = $state(undefined);',
    '    let darkModeObserver: MutationObserver | null = null;',
    '    let visibilityObservers: MutationObserver[] = [];',
    '',
    '    /** The visibility of every ancestor of the chart, up to <html>: a class, a style, a hidden. */',
    '    function setupVisibilityObservers(): void {',
    '        let ancestor = chartContainer?.parentElement;',
    '        while (ancestor) {',
    '            const observer = new MutationObserver(() => syncVisibilityState());',
    "            observer.observe(ancestor, {attributes: true, attributeFilter: ['class', 'style', 'hidden']});",
    '            visibilityObservers.push(observer);',
    '            ancestor = ancestor.parentElement;',
    '        }',
    '    }',
    '',
    '    onMount(() => {',
    '        darkModeObserver = onThemeClassChange(() => renderChart());',
    '        return () => {',
    '            for (const observer of visibilityObservers) observer.disconnect();',
    '            darkModeObserver?.disconnect();',
    '        };',
    '    });',
    '</script>',
    '',
    '<div bind:this={chartContainer}></div>',
    '',
].join('\n');

/** `OtherPeriodEffectsTable`: an attribute of the rows of a table, across lines. */
const OTHER_EFFECTS_TEXT = [
    '<script lang="ts">',
    '    let tableShell: HTMLDivElement | undefined = $state();',
    '',
    '    $effect(() => {',
    '        if (!tableShell) return;',
    '        const observer = new MutationObserver(() => syncRowTestIds());',
    '        observer.observe(tableShell, {',
    '            subtree: true,',
    '            childList: true,',
    '            attributes: true,',
    "            attributeFilter: ['data-row-id'],",
    '        });',
    '        return () => observer.disconnect();',
    '    });',
    '</script>',
    '',
].join('\n');

/** `Header`: the modal counter on `<body>`, through a variable. */
const HEADER_TEXT = [
    '<script lang="ts">',
    '    let modalObserver: MutationObserver | null = null;',
    '',
    '    $effect(() => {',
    '        const body = document.body;',
    '        modalObserver = new MutationObserver(updateModalScrollLockCount);',
    '        modalObserver.observe(body, {',
    '            attributes: true,',
    "            attributeFilter: ['data-modal-scroll-lock-count'],",
    '        });',
    '        return () => modalObserver?.disconnect();',
    '    });',
    '</script>',
    '',
].join('\n');

/** `RiskCardGrid`: the size of a grid, and its children. */
const RISK_CARD_GRID_TEXT = [
    '<script lang="ts">',
    '    let grid: HTMLDivElement;',
    '',
    '    $effect(() => {',
    '        const resizeObserver = new ResizeObserver(() => measure());',
    '        const childObserver = new MutationObserver(() => measure());',
    '        resizeObserver?.observe(grid);',
    '        childObserver.observe(grid, {childList: true});',
    '        return () => {',
    '            resizeObserver.disconnect();',
    '            childObserver.disconnect();',
    '        };',
    '    });',
    '</script>',
    '',
    '<div bind:this={grid}></div>',
    '',
].join('\n');

/** The onboarding: the modal counter on `document.body`, across lines. */
const DEFERRED_POPUPS_TEXT = [
    '<script lang="ts">',
    "    import {onMount} from 'svelte';",
    '',
    '    onMount(() => {',
    '        const observer = new MutationObserver(updateModalDepth);',
    '        observer.observe(document.body, {',
    '            attributes: true,',
    "            attributeFilter: ['data-modal-scroll-lock-count'],",
    '        });',
    '        return () => observer.disconnect();',
    '    });',
    '</script>',
    '',
].join('\n');

/** `scrollOnOverflow`: the size of a node, its text, the children of a container. */
const SCROLL_ON_OVERFLOW_TEXT = [
    '/** Scrolls a label that overflows its box: watches the box, and what is written in it. */',
    'export function scrollOnOverflow(node: HTMLElement, container: HTMLElement): {destroy: () => void} {',
    '    const resizeObserver = new ResizeObserver(sync);',
    '    const mutationObserver = new MutationObserver(sync);',
    '    resizeObserver.observe(node);',
    '    mutationObserver.observe(node, {characterData: true, childList: true, subtree: true});',
    '    mutationObserver.observe(container, {childList: true, subtree: true});',
    '    return {destroy: () => (resizeObserver.disconnect(), mutationObserver.disconnect())};',
    '}',
    '',
].join('\n');

/** `<html>` itself, observed for anything but its class — its size, its children, its lang: all legal. Not a file of the app: the forms are. */
const VIEWPORT_TEXT = [
    '/** <html> observed for anything but its class. */',
    'export function watchDocument(onResize: () => void, onChildren: () => void, onLang: () => void): () => void {',
    '    const size = new ResizeObserver(onResize);',
    '    size.observe(document.documentElement);',
    "    size.observe(document.documentElement, {box: 'border-box'});",
    '    const children = new MutationObserver(onChildren);',
    '    children.observe(document.documentElement, {childList: true, subtree: true});',
    '    const lang = new MutationObserver(onLang);',
    "    lang.observe(document.documentElement, {attributes: true, attributeFilter: ['lang', 'data-i18n-ready']});",
    '    lang.observe(document.documentElement, {attributeFilter: []});',
    '    lang.observe(document.documentElement, {attributes: false, characterData: true});',
    '    return () => [size, children, lang].forEach((observer) => observer.disconnect());',
    '}',
    '',
].join('\n');

/** The anti-FOUC script: it writes the class, and reads nothing but the system preference. */
const APP_HTML_TEXT = [
    '<!doctype html>',
    '<html lang="en">',
    '    <head>',
    '        <script>',
    "            // Anti-FOUC: the class is written before the first paint — classList.contains('dark') is never asked here.",
    '            (function () {',
    "                var theme = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';",
    '                document.documentElement.classList.add(theme);',
    '            })();',
    '        </script>',
    '    </head>',
    '    <body>',
    "        <!-- document.documentElement.classList.contains('dark') -->",
    '        %sveltekit.body%',
    '    </body>',
    '</html>',
    '',
].join('\n');

/** The theme store: it writes the class, in all three forms. */
const THEME_STORE_TEXT = [
    "/** Applies a theme: writes the class of <html>. Reading it — classList.contains('dark') — is isDarkTheme()'s job. */",
    "export function applyTheme(resolved: 'light' | 'dark'): void {",
    "    document.documentElement.classList.remove('light', 'dark');",
    '    document.documentElement.classList.add(resolved);',
    "    document.documentElement.classList.toggle('dark', resolved === 'dark');",
    '}',
    '',
].join('\n');

/** The one reader, three charts in both shapes, every legal observer of the app, `<html>` observed for anything but its class, and the two writers of the class. */
function cleanTree(): Tree {
    return {
        [THEME_MODE]: THEME_MODE_TEXT,
        [LINE_CHART]: LINE_CHART_TEXT,
        [GROWTH_CHART]: GROWTH_CHART_TEXT,
        [ALLOCATION_HISTORY]: ALLOCATION_HISTORY_TEXT,
        [OTHER_EFFECTS]: OTHER_EFFECTS_TEXT,
        [HEADER]: HEADER_TEXT,
        [RISK_CARD_GRID]: RISK_CARD_GRID_TEXT,
        [DEFERRED_POPUPS]: DEFERRED_POPUPS_TEXT,
        [SCROLL_ON_OVERFLOW]: SCROLL_ON_OVERFLOW_TEXT,
        [VIEWPORT]: VIEWPORT_TEXT,
        [APP_HTML]: APP_HTML_TEXT,
        [THEME_STORE]: THEME_STORE_TEXT,
    };
}

/** The clean tree with edits to one file; an edit that does not apply is a broken case, and throws. */
function withEdits(path: string, ...edits: Array<[string, string]>): Tree {
    const tree = cleanTree();
    for (const [from, to] of edits) {
        if (!tree[path].includes(from)) throw new Error(`synthetic edit: ${path} has no \`${from}\``);
        tree[path] = tree[path].replace(from, to);
    }
    return tree;
}

/** The clean tree with one file replaced, or added. */
const withFile = (path: string, text: string): Tree => ({...cleanTree(), [path]: text});

/** A chart that observes `<html>` itself, as 16 did before W8: the `observe()` call as written, on line 6. */
const LEGACY = 'src/lib/components/charts/LegacyChart.svelte';
const legacyChart = (call: string): string =>
    [
        '<script lang="ts">',
        "    import {onMount} from 'svelte';",
        '',
        '    onMount(() => {',
        '        const observer = new MutationObserver(() => renderChart());',
        // Line 6: the call under test.
        `        ${call};`,
        '        return () => observer.disconnect();',
        '    });',
        '</script>',
        '',
    ].join('\n');

/** A component reading, observing and leaking the theme in the forms (a), (b) and (c) reject — as a harness or the Designer Lab may. */
const ANY_FORM_SVELTE = [
    '<script lang="ts">',
    "    import {onMount} from 'svelte';",
    "    import {onThemeClassChange} from '$lib/theme/themeMode';",
    '',
    "    let dark = $state(document.documentElement.classList.contains('dark'));",
    '',
    '    onMount(() => {',
    '        new MutationObserver(() => (dark = !dark)).observe(document.documentElement, {attributes: true});',
    '        onThemeClassChange(() => (dark = !dark));',
    '    });',
    '</script>',
    '',
].join('\n');

/** The same forms in a script, as a test writes them. */
const ANY_FORM_TS = [
    "import {expect, it} from 'vitest';",
    "import {onThemeClassChange} from '$lib/theme/themeMode';",
    '',
    "it('follows the theme', () => {",
    '    const observer = new MutationObserver(() => {});',
    "    observer.observe(document.documentElement, {attributes: true, attributeFilter: ['class']});",
    '    onThemeClassChange(() => {});',
    "    document.documentElement.classList.add('dark');",
    "    expect(document.documentElement.classList.contains('dark')).toBe(true);",
    '});',
    '',
].join('\n');

/** Where a message of (a), (b) or (c) points: its `file:line`, everything before the two spaces that follow it. */
const placeIn = (entry: string): string => entry.slice(0, entry.indexOf('  '));

// ---------------------------------------------------------------------------
// The gate
// ---------------------------------------------------------------------------

describe('The page theme — read and watched only through $lib/theme/themeMode (R, W8 — D4 gate)', () => {
    describe('the scanner, on synthetic trees', () => {
        it('passes a clean tree, and reads in it every observe() call, every call of the helper and the one read — and no comment', () => {
            const tree = cleanTree();
            expect(verdictOf(tree)).toEqual(CLEAN);
            const {reads, observations, calls, imports} = audit(tree);
            expect(reads.map(placeOf), "the one read, themeMode.ts's: the five quoted in comments read nothing").toEqual([`${THEME_MODE}:5`]);
            expect(
                observations.map((observation) => `${placeOf(observation)} ${observation.target} ${observation.html ? '<html>' : '-'} ${observation.sight}`),
                'every observe() call is read and judged, the legal ones too: their green is a verdict, not a miss',
            ).toEqual([
                `${SCROLL_ON_OVERFLOW}:5 node - not-class`,
                `${SCROLL_ON_OVERFLOW}:6 node - not-class`,
                `${SCROLL_ON_OVERFLOW}:7 container - not-class`,
                `${HEADER}:7 body - not-class`,
                `${RISK_CARD_GRID}:7 grid - not-class`,
                `${RISK_CARD_GRID}:8 grid - not-class`,
                `${ALLOCATION_HISTORY}:14 ancestor - class`,
                `${OTHER_EFFECTS}:7 tableShell - not-class`,
                `${DEFERRED_POPUPS}:6 document.body - not-class`,
                `${THEME_MODE}:10 document.documentElement <html> class`,
                `${VIEWPORT}:4 document.documentElement <html> not-class`,
                `${VIEWPORT}:5 document.documentElement <html> not-class`,
                `${VIEWPORT}:7 document.documentElement <html> not-class`,
                `${VIEWPORT}:9 document.documentElement <html> not-class`,
                `${VIEWPORT}:10 document.documentElement <html> not-class`,
                `${VIEWPORT}:11 document.documentElement <html> not-class`,
            ]);
            expect(calls.map((call) => `${placeOf(call)} ${call.name} ${call.disconnected ? 'disconnected' : 'leaks'}`)).toEqual([`${LINE_CHART}:10 observer disconnected`, `${ALLOCATION_HISTORY}:21 darkModeObserver disconnected`, `${GROWTH_CHART}:14 darkModeObserver disconnected`]);
            expect(Object.fromEntries(imports)).toEqual({[LINE_CHART]: ['isDarkTheme', 'onThemeClassChange'], [ALLOCATION_HISTORY]: ['onThemeClassChange'], [GROWTH_CHART]: ['isDarkTheme', 'onThemeClassChange']});
        });

        it('(a) fails a direct read of the theme class: the form W8 replaced, in any quote or spacing, on any element', () => {
            const reading = (expression: string): string[] => verdictOf(withEdits(LINE_CHART, ['$state(isDarkTheme())', `$state(${expression})`])).a;
            expect(reading("document.documentElement.classList.contains('dark')")).toEqual([`${LINE_CHART}:5  let dark = $state(document.documentElement.classList.contains('dark'));  → a direct read of the theme class: use isDarkTheme() from $lib/theme/themeMode`]);

            const variants = [
                'document.documentElement.classList.contains("dark")',
                'document.documentElement.classList.contains(`dark`)',
                "document.documentElement?.classList?.contains('dark')",
                "document.documentElement.classList.contains( 'dark' )",
                "document.documentElement.classList\n        .contains('dark')",
                // Whose classList it is does not matter: an alias of <html>, or the wrong element, still reads the theme class.
                "html.classList.contains('dark')",
                "document.body.classList.contains('dark')",
            ];
            for (const expression of variants) {
                const found = reading(expression);
                expect(found.map(placeIn), expression).toEqual([`${LINE_CHART}:5`]);
                expect(found[0], expression).toMatch(/ → a direct read of the theme class: use isDarkTheme\(\) from \$lib\/theme\/themeMode$/);
            }
        });

        it('(a) fails it wherever code runs: a template expression, the inline script of app.html, a script module', () => {
            const template = withEdits(LINE_CHART, ['<div class:dark', "{#if document.documentElement.classList.contains('dark')}<span></span>{/if}\n<div class:dark"]);
            expect(verdictOf(template).a.map(placeIn)).toEqual([`${LINE_CHART}:18`]);

            const page = withEdits(APP_HTML, ['document.documentElement.classList.add(theme);', "document.documentElement.classList.add(theme);\n                if (document.documentElement.classList.contains('dark')) document.body.dataset.dark = '';"]);
            expect(verdictOf(page).a.map(placeIn)).toEqual([`${APP_HTML}:9`]);

            const store = withEdits(THEME_STORE, ['    document.documentElement.classList.add(resolved);', "    document.documentElement.classList.add(resolved);\n    const wasDark = document.documentElement.classList.contains('dark');"]);
            expect(verdictOf(store).a.map(placeIn)).toEqual([`${THEME_STORE}:5`]);
        });

        it('(a) passes the writes, and what only resembles the read: another class, a variable, a comment', () => {
            const lookalikes = 'src/lib/utils/themeLookalikes.ts';
            const tree = withFile(
                lookalikes,
                [
                    "/** Writes the theme class: classList.contains('dark') is isDarkTheme()'s alone. */",
                    'export function lookalikes(el: HTMLElement, theme: string): boolean[] {',
                    "    el.classList.add('dark');",
                    "    el.classList.remove('dark');",
                    "    el.classList.toggle('dark');",
                    "    el.classList.replace('light', 'dark');",
                    "    // return [el.classList.contains('dark')];",
                    "    return [el.classList.contains('darker'), el.classList.contains('dark-mode'), el.classList.contains('not-dark'), el.classList.contains(theme)];",
                    '}',
                    '',
                ].join('\n'),
            );
            expect(verdictOf(tree)).toEqual(CLEAN);
            expect(audit(tree).files, 'the file is read: its green is a verdict').toContain(lookalikes);
        });

        it('(b) fails a MutationObserver that can see the class of <html>: the form W8 replaced, on one line or several, and every option set the DOM reads the same way', () => {
            const observing = (call: string): string[] => verdictOf(withFile(LEGACY, legacyChart(call))).b;
            expect(observing("observer.observe(document.documentElement, {attributes: true, attributeFilter: ['class']})")).toEqual([
                `${LEGACY}:6  observer.observe(document.documentElement, {attributes: true, attributeFilter: ['class']})  → a MutationObserver on the class of <html>: use onThemeClassChange() from $lib/theme/themeMode, and disconnect() the observer it returns`,
            ]);

            const seeing = [
                // The same across lines, as CandlestickChart and LineChart wrote it before W8.
                "observer.observe(document.documentElement, {\n            attributes: true,\n            attributeFilter: ['class'],\n        })",
                // Every attribute, the class among them.
                'observer.observe(document.documentElement, {attributes: true})',
                'observer.observe(document.documentElement, {attributes: true, subtree: true})',
                // Attributes implied: by the filter, by the old value.
                "observer.observe(document.documentElement, {attributeFilter: ['class']})",
                'observer.observe(document.documentElement, {attributeOldValue: true})',
                // Other quotes, other keys beside it, an entry the gate cannot read beside a 'class' it can.
                'observer.observe(document.documentElement, {attributes: true, attributeFilter: ["style", "class"]})',
                "observer.observe(document.documentElement, {'attributes': true, childList: true})",
                'observer.observe(document.documentElement, {attributes: true, attributeFilter: [`class`]})',
                "observer.observe(document.documentElement, {attributes: true, attributeFilter: ['class', THEME_ATTRIBUTE]})",
                // <html> through other objects, through ?.observe(), destructured, on an observer never named.
                "observer?.observe(window.document.documentElement, {attributes: true, attributeFilter: ['class']})",
                "observer.observe(chartContainer.ownerDocument.documentElement, {attributes: true, attributeFilter: ['class']})",
                "observer.observe(documentElement, {attributes: true, attributeFilter: ['class']})",
                "new MutationObserver(() => renderChart()).observe(document.documentElement, {attributes: true, attributeFilter: ['class']})",
            ];
            for (const call of seeing) {
                const found = observing(call);
                expect(found.map(placeIn), call).toEqual([`${LEGACY}:6`]);
                expect(found[0], call).toMatch(/ → a MutationObserver on the class of <html>: use onThemeClassChange\(\) from \$lib\/theme\/themeMode, and disconnect\(\) the observer it returns$/);
            }
        });

        it('(b) fails options it cannot read, on an observation of <html>: a variable, a spread, a computed filter, flag or key', () => {
            const unreadable = [
                'observer.observe(document.documentElement, OPTIONS)',
                'observer.observe(document.documentElement, {...THEME_OPTIONS})',
                'observer.observe(document.documentElement, {childList: true, ...THEME_OPTIONS})',
                'observer.observe(document.documentElement, {attributes: true, attributeFilter: FILTER})',
                'observer.observe(document.documentElement, {attributes: true, attributeFilter: [THEME_ATTRIBUTE]})',
                'observer.observe(document.documentElement, {attributes: watchAttributes})',
                'observer.observe(document.documentElement, {attributes})',
                'observer.observe(document.documentElement, {[key]: true})',
            ];
            for (const call of unreadable) {
                const found = verdictOf(withFile(LEGACY, legacyChart(call))).b;
                expect(found.map(placeIn), call).toEqual([`${LEGACY}:6`]);
                expect(found[0], call).toMatch(/ → an observation of <html> whose options this gate cannot read: write them inline, as an object literal — and if it watches the theme, use onThemeClassChange\(\) from \$lib\/theme\/themeMode$/);
            }
        });

        it('(b) passes every other observation: another element, even for its class, and <html> watched for anything but its class', () => {
            const legal = [
                // The class of <body>, of an ancestor of the chart: not the theme.
                "observer.observe(document.body, {attributes: true, attributeFilter: ['class']})",
                "observer.observe(ancestor, {attributes: true, attributeFilter: ['class', 'style', 'hidden']})",
                // <html> for its children, another attribute, its text, its size.
                'observer.observe(document.documentElement, {childList: true, subtree: true})',
                "observer.observe(document.documentElement, {attributes: true, attributeFilter: ['lang']})",
                "observer.observe(document.documentElement, {attributeOldValue: false, attributeFilter: ['data-theme-ready']})",
                'observer.observe(document.documentElement, {attributes: false, childList: true})',
                'observer.observe(document.documentElement, {characterData: true, subtree: true})',
                'resizeObserver.observe(document.documentElement)',
                "resizeObserver.observe(document.documentElement, {box: 'border-box'})",
            ];
            for (const call of legal) {
                const tree = withFile(LEGACY, legacyChart(call));
                expect(verdictOf(tree), call).toEqual(CLEAN);
                const judged = audit(tree).observations.filter((observation) => observation.file === LEGACY);
                expect(
                    judged.map((observation) => !observation.html || observation.sight === 'not-class'),
                    `${call}: read, and judged legal`,
                ).toEqual([true]);
            }
        });

        it('(c) fails an observer nobody keeps', () => {
            const call = 'darkModeObserver = onThemeClassChange(() => renderChart());';
            expect(verdictOf(withEdits(GROWTH_CHART, [call, 'onThemeClassChange(() => renderChart());'])).c).toEqual([
                `${GROWTH_CHART}:14  onThemeClassChange(() => renderChart());  → the observer it returns is not kept: assign it (const observer = onThemeClassChange(…)) and call observer.disconnect() when the component is destroyed — an observer nobody keeps goes on redrawing a destroyed chart`,
            ]);

            const unkept = [
                'void onThemeClassChange(() => renderChart());',
                'observers.push(onThemeClassChange(() => renderChart()));',
                'const {disconnect} = onThemeClassChange(() => renderChart());',
                'return onThemeClassChange(() => renderChart());',
                // Conservatively: an observer created inside a larger expression.
                'const observer = dark ? onThemeClassChange(() => renderChart()) : null;',
            ];
            for (const statement of unkept) {
                const found = verdictOf(withEdits(GROWTH_CHART, [call, statement])).c;
                expect(found.map(placeIn), statement).toEqual([`${GROWTH_CHART}:14`]);
                expect(found[0], statement).toContain('→ the observer it returns is not kept');
            }
        });

        it('(c) fails an observer kept and never disconnected: the disconnect deleted, commented out, never called, or on another name', () => {
            const notDisconnecting = ['', '// darkModeObserver?.disconnect();', '/* darkModeObserver?.disconnect(); */', 'darkModeObserver?.disconnect;', 'observer?.disconnect();', '_darkModeObserver?.disconnect();'];
            for (const line of notDisconnecting) {
                expect(verdictOf(withEdits(GROWTH_CHART, ['darkModeObserver?.disconnect();', line])).c, line || '(deleted)').toEqual([
                    `${GROWTH_CHART}:14  darkModeObserver = onThemeClassChange(() => renderChart());  → darkModeObserver is never disconnected in this file: call darkModeObserver.disconnect() in the cleanup of the effect or onMount that creates it — or it goes on redrawing a destroyed chart`,
                ]);
            }

            const local = verdictOf(withEdits(LINE_CHART, ['        return () => observer.disconnect();\n', ''])).c;
            expect(local.map(placeIn)).toEqual([`${LINE_CHART}:10`]);
            expect(local[0]).toContain('→ observer is never disconnected in this file');
        });

        it('(c) passes the shapes a chart keeps and disconnects its observer in', () => {
            const call = 'darkModeObserver = onThemeClassChange(() => renderChart());';
            const disconnect = 'darkModeObserver?.disconnect();';
            const shapes: Array<[string, string, string]> = [
                // The call, its disconnect, and the name (c) reads.
                ['const observer = onThemeClassChange(() => renderChart());', 'observer.disconnect();', 'observer'],
                ['let darkObserver: MutationObserver | null = onThemeClassChange(() => renderChart());', 'darkObserver?.disconnect();', 'darkObserver'],
                ['darkModeObserver ??= onThemeClassChange(() => renderChart());', disconnect, 'darkModeObserver'],
                ['this.observer = onThemeClassChange(() => this.render());', 'this.observer.disconnect();', 'observer'],
                ['const observer = onThemeClassChange(\n            () => renderChart(),\n        );', 'observer?.disconnect();', 'observer'],
                ['const observer =\n            onThemeClassChange(() => renderChart());', 'observer.disconnect();', 'observer'],
            ];
            for (const [statement, release, name] of shapes) {
                const tree = withEdits(GROWTH_CHART, [call, statement], [disconnect, release]);
                expect(verdictOf(tree), statement).toEqual(CLEAN);
                expect(
                    audit(tree)
                        .calls.filter((found) => found.file === GROWTH_CHART)
                        .map((found) => found.name),
                    statement,
                ).toEqual([name]);
            }

            const namespaced = withEdits(GROWTH_CHART, ["import {isDarkTheme, onThemeClassChange} from '$lib/theme/themeMode';", "import * as themeMode from '$lib/theme/themeMode';"], [call, 'darkModeObserver = themeMode.onThemeClassChange(() => renderChart());']);
            expect(verdictOf(namespaced)).toEqual(CLEAN);
            expect(
                audit(namespaced)
                    .calls.filter((found) => found.file === GROWTH_CHART)
                    .map((found) => found.name),
            ).toEqual(['darkModeObserver']);
        });

        it('(d) fails a scan that reads nothing — on which every other check passes', () => {
            expect(verdictOf({})).toEqual({
                ...CLEAN,
                d: [`${THEME_MODE}  not found: the one reader of the theme, and the control of (a) and (b)`, 'no file imports $lib/theme/themeMode', 'no call of onThemeClassChange(): (c) checks nothing', 'no .svelte file: the walk does not reach the components'],
            });
        });

        it('(d) fails a themeMode.ts in which the scanner does not find exactly the one read and the one observation', () => {
            const rewritten = withEdits(THEME_MODE, ["document.documentElement.classList.contains('dark')", "document.documentElement.matches('.dark')"], ["{attributes: true, attributeFilter: ['class']}", 'CLASS_ONLY']);
            expect(verdictOf(rewritten)).toEqual({
                ...CLEAN,
                d: [
                    `${THEME_MODE}  the scanner finds 0 reads of the theme class there, expected exactly 1 — if isDarkTheme() now reads it another way, teach (a) the new form`,
                    `${THEME_MODE}  the scanner finds 0 observations of the class of <html> there, expected exactly 1 — if onThemeClassChange() now observes it another way, teach (b) the new form`,
                ],
            });

            const twice = withEdits(THEME_MODE, ['export function onThemeClassChange', "export const isDarkToo = (): boolean => document.documentElement.classList.contains('dark');\n\nexport function onThemeClassChange"]);
            expect(verdictOf(twice)).toEqual({...CLEAN, d: [`${THEME_MODE}  the scanner finds 2 reads of the theme class there, expected exactly 1 — if isDarkTheme() now reads it another way, teach (a) the new form`]});

            const gone = cleanTree();
            delete gone[THEME_MODE];
            expect(verdictOf(gone)).toEqual({...CLEAN, d: [`${THEME_MODE}  not found: the one reader of the theme, and the control of (a) and (b)`]});
        });

        it('(d) fails a file that imports onThemeClassChange and calls it under another name: (c) would not see the call', () => {
            const aliased = withEdits(GROWTH_CHART, ["import {isDarkTheme, onThemeClassChange} from '$lib/theme/themeMode';", "import {isDarkTheme, onThemeClassChange as watchTheme} from '$lib/theme/themeMode';"], ['darkModeObserver = onThemeClassChange(', 'darkModeObserver = watchTheme(']);
            expect(verdictOf(aliased)).toEqual({...CLEAN, d: [`${GROWTH_CHART}  imports onThemeClassChange, and (c) sees no call of it: call it by that name — under another one, (c) cannot check that its observer is kept and disconnected`]});
        });

        it('(d) reads an import of themeMode.ts by $lib, by a relative path, with its extension, across lines — and no other module', () => {
            const imported = (statement: string): string[] => themeModeImportsIn(LINE_CHART, statement);
            const both = ['isDarkTheme', 'onThemeClassChange'];
            expect(imported("import {isDarkTheme, onThemeClassChange} from '$lib/theme/themeMode';")).toEqual(both);
            expect(imported("import {isDarkTheme, onThemeClassChange} from '../../theme/themeMode';")).toEqual(both);
            expect(imported('import {isDarkTheme, onThemeClassChange} from "$lib/theme/themeMode.ts";')).toEqual(both);
            expect(imported("import {\n    isDarkTheme,\n    onThemeClassChange as watchTheme,\n} from '$lib/theme/themeMode';")).toEqual(both);
            expect(imported("import * as themeMode from '$lib/theme/themeMode';")).toEqual(['*']);
            expect(imported("import {themed} from '$lib/theme/themePair';")).toEqual([]);
            expect(imported("import {isDarkTheme} from '../theme/themeMode';"), 'from charts/, that is src/lib/components/theme/themeMode: another file').toEqual([]);
        });

        it('themeMode.ts is the one reader: its read and its observation, written anywhere else, fail (a) and (b)', () => {
            const copy = 'src/lib/theme/themeModeCopy.ts';
            expect(verdictOf(withFile(copy, THEME_MODE_TEXT))).toEqual({
                ...CLEAN,
                a: [`${copy}:5  return document.documentElement.classList.contains('dark');  → a direct read of the theme class: use isDarkTheme() from $lib/theme/themeMode`],
                b: [`${copy}:10  observer.observe(document.documentElement, {attributes: true, attributeFilter: ['class']})  → a MutationObserver on the class of <html>: use onThemeClassChange() from $lib/theme/themeMode, and disconnect() the observer it returns`],
            });
        });

        it('skips by path every test, mock and Designer Lab file — and nothing that merely resembles one', () => {
            const expected: Record<string, boolean> = {
                // Tests, mocks and the Lab: never opened.
                'src/themeModeReads.gate.test.ts': false,
                'src/lib/theme/themeMode.test.ts': false,
                'src/lib/features/dashboard/GrowthChart.test.ts': false,
                'src/lib/utils/core/__tests__/resizeWatcher.test.ts': false,
                'src/__tests__/component.ts': false,
                'src/__tests__/harness/ThemeProbe.svelte': false,
                'src/__mocks__/$app/environment.ts': false,
                'src/routes/designer-lab/+page.svelte': false,
                'src/lib/dev/designer-lab/ThemeSwitcher.svelte': false,
                'src/lib/dev/designer-lab/liveTheme.ts': false,
                // Not a type that holds a script.
                'src/app.css': false,
                'src/lib/i18n/en.json': false,
                // The app — the one reader among it, opened for (d) — and the near misses of the Lab's prefixes: a sibling directory, the parent, the name elsewhere.
                [THEME_MODE]: true,
                [LINE_CHART]: true,
                [APP_HTML]: true,
                [THEME_STORE]: true,
                'src/lib/stores/app/notify.svelte.ts': true,
                'src/routes/designer-lab-old/+page.svelte': true,
                'src/lib/dev/ThemeSwitcher.svelte': true,
                'src/lib/designer-lab/ThemeSwitcher.svelte': true,
            };
            expect(Object.fromEntries(Object.keys(expected).map((path) => [path, isScanned(path)]))).toEqual(expected);
        });

        it('a test or a Designer Lab file may read, watch and leak the theme in any form, and every check stays green — the same text anywhere else turns red', () => {
            const exempt: Tree = {
                'src/routes/designer-lab/+page.svelte': ANY_FORM_SVELTE,
                'src/lib/dev/designer-lab/liveTheme.ts': ANY_FORM_TS,
                'src/lib/theme/themeMode.test.ts': ANY_FORM_TS,
                'src/__tests__/harness/ThemeProbe.svelte': ANY_FORM_SVELTE,
                'src/__mocks__/$app/environment.ts': ANY_FORM_TS,
            };
            for (const [path, text] of Object.entries(exempt)) expect(verdictOf(withFile(path, text)), path).toEqual(CLEAN);
            expect(audit({...cleanTree(), ...exempt}).files, 'not one of them is read, and every other file is').toEqual(Object.keys(cleanTree()).sort());

            // The control: the same text where the scan reads it, red on (a), (b) and (c) — one line each.
            const component = 'src/lib/components/charts/ThemeProbe.svelte';
            const script = 'src/lib/theme/themeProbe.ts';
            const places = (verdict: Verdict) => ({a: verdict.a.map(placeIn), b: verdict.b.map(placeIn), c: verdict.c.map(placeIn), d: verdict.d});
            expect(places(verdictOf(withFile(component, ANY_FORM_SVELTE)))).toEqual({a: [`${component}:5`], b: [`${component}:8`], c: [`${component}:9`], d: []});
            expect(places(verdictOf(withFile(script, ANY_FORM_TS)))).toEqual({a: [`${script}:9`], b: [`${script}:6`], c: [`${script}:7`], d: []});
        });

        it('the floor «What it cannot see» documents: <html> under another name, the theme read another way — all pass', () => {
            const floor = 'src/lib/utils/themeFloor.ts';
            const tree = withFile(
                floor,
                [
                    '/** Forms the gate does not read. Should one turn red, the scanner has learnt it: update «What it cannot see». */',
                    'export function floor(redraw: () => void): boolean {',
                    '    const html = document.documentElement;',
                    "    new MutationObserver(redraw).observe(html, {attributes: true, attributeFilter: ['class']});",
                    "    new MutationObserver(redraw).observe(document.querySelector('html')!, {attributes: true});",
                    '    new MutationObserver(redraw).observe(document, {attributes: true, subtree: true});',
                    "    return html.matches('.dark') || html.className.includes('dark') || document.querySelector('.dark') !== null;",
                    '}',
                    '',
                ].join('\n'),
            );
            expect(verdictOf(tree)).toEqual(CLEAN);
            expect(
                audit(tree)
                    .observations.filter((observation) => observation.file === floor)
                    .map((observation) => `${observation.target} ${observation.html ? '<html>' : '-'}`),
                'read, and not recognised as <html>',
            ).toEqual(['html -', "document.querySelector('html')! -", 'document -']);
        });
    });

    describe('the files of src', () => {
        it('the walk reads every component, script and document of src — and no test, mock or Designer Lab file', () => {
            // The files the walk opened: srcAudit().files could not tell, since audit drops these paths again.
            const files = Object.keys(srcTree());
            expect(files.filter((file) => file.endsWith('.svelte')).length, 'the walk reaches the components').toBeGreaterThan(100);
            expect(files, 'the one reader, and the two writers of the class').toEqual(expect.arrayContaining([THEME_MODE, APP_HTML, THEME_STORE]));
            const unwanted = files.filter((file) => file.endsWith('.test.ts') || file.includes('/__tests__/') || file.includes('/__mocks__/') || isDesignerLab(file));
            expect(unwanted, 'tests, mocks and the Designer Lab are not opened at all: they may read and watch the theme in any form, and none of them is the app').toEqual([]);
        });

        it('(d) the scan finds the one reader, the files importing it, and calls of the helper to check', () => {
            expect(emptyScans(srcAudit()), 'the scan reads nothing (a)–(c) need: fix the walk or the patterns — never relax this, every other check passes on an empty scan').toEqual([]);
        });

        it('(a) nothing but themeMode.ts reads the theme class', () => {
            expect(directReads(srcAudit()), 'read the theme with isDarkTheme() from $lib/theme/themeMode: the one place that knows the theme is the dark class of <html>').toEqual([]);
        });

        it('(b) nothing but themeMode.ts observes the class of <html>', () => {
            expect(htmlClassObservers(srcAudit()), 'watch the theme with onThemeClassChange() from $lib/theme/themeMode — every change of the class of <html>, as D4 settled — and disconnect() the observer it returns').toEqual([]);
        });

        it('(c) every observer onThemeClassChange() returns is kept, and disconnected', () => {
            expect(leakingObservers(srcAudit()), 'keep the observer onThemeClassChange() returns in a name, and disconnect() it when the component is destroyed: otherwise it goes on redrawing a destroyed chart').toEqual([]);
        });

        it('every check bites on these very files: one mutation each, in memory, turns it red', () => {
            const {calls, imports} = srcAudit();
            const kept = calls.find((call) => call.name !== null && call.disconnected);
            if (!kept?.name) throw new Error('no observer kept and disconnected in src — see (d)');
            const name = kept.name;

            // The one reader, its importers and the two writers of the class: every other file the walk reads neither reads nor watches the theme (the tests above), so it cannot change a verdict — re-reading it for each mutation would only cost time.
            const tree: Tree = Object.fromEntries(Object.entries(srcTree()).filter(([path]) => path === THEME_MODE || path === APP_HTML || path === THEME_STORE || imports.has(path)));
            expect(verdictOf(tree), 'the files the mutations start from keep the rule on their own').toEqual(CLEAN);
            const mutated = (path: string, text: string): Verdict => {
                expect(text, `the mutation of ${path} applies`).not.toBe(tree[path]);
                return verdictOf({...tree, [path]: text});
            };
            // The text of a file with `[from, to)` replaced: blanking keeps offsets, so an offset in the code is one in the text.
            const splice = (file: string, from: number, to: number, by: string): string => tree[file].slice(0, from) + by + tree[file].slice(to);

            // (a) An importer reading the class inline again, as before W8.
            const CALL_OF_READER = /(?<![\w$])isDarkTheme\(\)/;
            const reader = Object.keys(tree).find((path) => path !== THEME_MODE && CALL_OF_READER.test(codeOf(path, tree[path])));
            if (!reader) throw new Error('no importer calls isDarkTheme()');
            const readAt = codeOf(reader, tree[reader]).search(CALL_OF_READER);
            const inlined = mutated(reader, splice(reader, readAt, readAt + 'isDarkTheme()'.length, "document.documentElement.classList.contains('dark')"));
            expect(inlined.a.map(placeIn), '(a) isDarkTheme() inlined back').toEqual([`${reader}:${lineAt(tree[reader], readAt)}`]);

            // (a) and (b) The one reader, copied anywhere else.
            const copy = mutated('src/lib/theme/themeModeCopy.ts', tree[THEME_MODE]);
            expect({a: copy.a.length, b: copy.b.length}, '(a) and (b) the forms of themeMode.ts, outside it').toEqual({a: 1, b: 1});

            // (b) A chart observing <html> itself again, as before W8: its call of the helper turned back into the inline observer.
            const code = codeOf(kept.file, tree[kept.file]);
            const open = code.indexOf('(', kept.offset);
            const close = closingOf(code, open);
            const inline = `new MutationObserver${tree[kept.file].slice(open, close + 1)}; ${name}.observe(document.documentElement, {attributes: true, attributeFilter: ['class']})`;
            const reverted = mutated(kept.file, splice(kept.file, kept.offset, close + 1, inline));
            expect(reverted.b.map(placeIn), '(b) onThemeClassChange() inlined back').toEqual([`${kept.file}:${lineAt(tree[kept.file], close)}`]);

            // (c) Its disconnect deleted.
            const undisconnected = mutated(kept.file, tree[kept.file].replace(new RegExp(`${disconnectOf(name).source}\\s*\\)`, 'g'), 'void 0'));
            expect(
                undisconnected.c.filter((entry) => placeIn(entry) === placeOf(kept) && entry.includes(`→ ${name} is never disconnected in this file`)),
                '(c) the disconnect deleted',
            ).toHaveLength(1);

            // (c) Its name deleted: the observer is no longer kept.
            const before = code.slice(Math.max(0, kept.offset - 200), kept.offset);
            const assignment = DECLARED.exec(before) ?? ASSIGNED.exec(before);
            if (!assignment) throw new Error(`${placeOf(kept)}: (c) read the name ${name}, and no assignment is found before the call`);
            const assignedAt = kept.offset - before.length + assignment.index;
            const unkeptText = splice(kept.file, assignedAt, kept.offset, '');
            const unkept = mutated(kept.file, unkeptText);
            expect(
                unkept.c.filter((entry) => placeIn(entry) === `${kept.file}:${lineAt(unkeptText, assignedAt)}` && entry.includes('→ the observer it returns is not kept')),
                '(c) the name deleted',
            ).toHaveLength(1);
        });
    });
});
