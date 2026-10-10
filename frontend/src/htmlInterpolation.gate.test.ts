/**
 * Gate: no user- or provider-supplied text is interpolated into hand-built HTML without escaping
 * (workstream K, step 13, item 0).
 *
 * ## What this protects
 *
 * A stored XSS shipped in v1.1.0: the Name column of `AssetTable` returned an `html` cell whose template
 * interpolated `${row.display_name}` raw, and `DataTable` renders `html` cells with `{@html}`. The
 * backend stores any string as an asset name, and assets are global, so a name written by one user ran
 * as script in the browser of every user who opened the asset list — the administrator included. The
 * cure is one call (`escapeHtml`, `$lib/utils/core/escapeHtml.ts`); what this file guards is that the
 * next template built the same way gets the same call. `e2e/assets/asset-name-xss.spec.ts` is the other
 * half: it creates the hostile name through the API and proves, in a real browser, that it stays text.
 *
 * ## What it reads
 *
 * Every non-test `.svelte` and `.ts` file under `src`, except tests (`*.test.ts`, `__tests__/`), test
 * mocks (`__mocks__/`), declaration files (`*.d.ts`) and the API clients generated from the backend
 * contracts (`src/lib/api/generated*`, `*.generated.ts`): those are gitignored and never written by
 * hand, so scanning them would make the verdict depend on the checkout.
 *
 * Nothing is matched line by line. `.ts` files are parsed by the TypeScript parser; `.svelte` files are
 * parsed by Svelte's own parser, which locates the `<script>` blocks and every expression of the markup,
 * and each of those is then parsed by TypeScript. So a comment or a string that merely *looks* like a
 * template is never mistaken for one, a template spread over several lines keeps the line of each
 * interpolation, and a template nested inside another one is seen. A file that does not parse fails
 * the gate: a file it cannot read is a file it cannot vouch for.
 *
 * It reads the UI catalogs too, every `*.json` in `src/lib/i18n`, as JSON: the text of a translation
 * is checked where it is written, not where it is used — see "Translations", below.
 *
 * ## The rule, as this file checks it
 *
 * An interpolation `${expr}` is in an **HTML context** when it belongs to a template literal that is
 * HTML — its static text contains a tag (`<span`, `</b>`, `<br/>`, `<img`, `<a `, …), or one of its
 * interpolations is an HTML fragment by name: an identifier or a property ending in `Html`, `Icon`,
 * `icon`, `Badge` or `badge` (`${brokerIcon}${broker.name}`, `${iconHtml}${name}`) — or when it belongs
 * to a template nested, unescaped, inside such an interpolation, since its output lands in the same
 * HTML.
 *
 * In an HTML context, the interpolation is a **violation** when a user/provider text field reaches its
 * value without passing through `escapeHtml(…)`, the one accepted escape. A text field is a name that
 * ends — case-insensitively — with one of `TEXT_SUFFIXES` (`name`, `notes`, `url`, `src`, `currency`, …)
 * or starts with `identifier`, matched as a property leaf (`row.display_name`, `x?.notes`, `x['tags']`)
 * or as a bare identifier (`rName`, `origName`, `iconUrl`, a shorthand `{name}`); URL-ish suffixes
 * (`src`, `href`, `url`) are in it because those values end up inside attribute values. Anything inside
 * `escapeHtml(…)` is escaped, so `${escapeHtml(row.display_name)}` is accepted, and so is
 * `${cond ? escapeHtml(a.name) : '—'}`. The local escapers `esc(…)` and `escHtml(…)` are not accepted:
 * they leave `"` alone — and some of them `>` — so a value they escape can still close the attribute
 * it sits in. A call to one of them in an HTML context is a violation whatever it escapes.
 *
 * A value read through a **computed key** — `r.values[col.key]`, `labels[code]`, `cells[i]` — is a
 * violation too, whatever the names around it: the key is known only at run time, so the gate cannot
 * tell a note from a number, and such a value is escaped or reported. Two kinds of read are let
 * through, both because they render a number: a read that is itself the value of a number format
 * (`upper[i].toFixed(4)`, `(totals[i] ?? 0).toLocaleString(…)`: `NUMERIC_FORMATS`), and a read the
 * flow rules below already discard (`Number(x[k])`, `String(x[k]).length`, `x[k].length`, the test of
 * a ternary). A literal key names its field, so `x['tags']` and `x[0]` stay under the name rule.
 *
 * Some helpers take HTML in their **first parameter**: `buildTooltipRow(label, …)`,
 * `buildTooltipHeader(title, …)`, `buildFittedTooltipRow(labelHtml, …)` and `fitTooltipToWidth(html, …)`
 * (`echartsTooltipHelpers.ts`, and the local copies some charts keep under the same names), and
 * GrowthChart's `pnlRow(label, …)`, which is handed `<b>…</b>` on purpose —
 * `HTML_FIRST_ARGUMENT`. The first argument of a call to one of them is checked as an interpolation
 * is, wherever the call stands: `pnlRow(broker.brokerName, …)` is the finding `${broker.brokerName}`
 * would be. Translations stay allowed there as everywhere: an i18n call, and a property of a label
 * bundle (`labels.*`, `pnlLabels.*`, `eurLabels.*` — `LABEL_BUNDLE`), which holds a translated label
 * whatever the property is called, in a helper's argument and in a template alike. That allowance rests
 * on a check of the catalogs, not on trust in their texts: see "Translations", below.
 *
 * "Reaches its value" is decided on the syntax tree, by rules that are mechanical, not judgements:
 *   - the test of `a ? b : c`, the left side of `a && b`, the operands of a comparison, of arithmetic
 *     other than `+`, of `!`, `typeof` and friends, produce no text of the field: they do not reach;
 *   - `x.name.length` is a number, not the name: a member access reaches only through its own leaf;
 *     `x.tags[0]` is an item of the field, and an item of a text field is text: it reaches;
 *   - `.includes()`, `.startsWith()`, `.some()`, `.indexOf()`, … return numbers and booleans: they do
 *     not reach; `.trim()`, `.slice()`, `.join()`, `.filter()`, … keep the receiver's text: they do;
 *   - `.map(cb)`: what reaches is what `cb` returns, not the receiver — and iterating a text field
 *     renames its items, so the parameters of a callback over it (`row.tags.map((t) => …)`,
 *     `.forEach`, …) and the variable of a `for…of` over it count as the field itself;
 *   - the first argument of an i18n call (`$t`, `$_`) is a message key, not text; its other arguments
 *     are interpolated into the message, so they reach;
 *   - every other call is opaque, and its arguments are assumed to reach its result.
 *
 * ## The allow-list
 *
 * `REVIEWED_EXCEPTIONS` holds interpolations reviewed and kept on purpose, keyed by file and by the
 * whitespace-collapsed expression — never by line, so an unrelated edit above a site cannot turn the
 * gate red. It starts EMPTY. An entry needs a reason a reviewer can check; an entry that no longer
 * matches a violation is stale and fails the gate, so the list cannot rot into one nobody trusts.
 *
 * ## Translations
 *
 * A translation reaches hand-built HTML unescaped wherever the rule above allows it, and its text comes
 * from the catalogs whatever path it takes — `$t`, an alias, a label bundle, a local with any name. So
 * the catalogs are checked instead of the sites, by the last `describe` of this file: every value must
 * read as plain text once parsed as HTML, which is all escaping it would change there. No "<" anywhere,
 * and no "&" that the parser decodes (`&lt;`, `&#60;`, `&amp;`, or a legacy name without ";" such as
 * `&copy`); a lone "&", as in "P&L", reads the same raw or escaped. The parser is jsdom's, with the
 * browser's own rules, not a pattern. A translation that carries markup on purpose is listed, with its
 * reason, in `SANITIZED_MARKUP_KEYS`, and reaches the page only through `sanitizeHtml`; an entry that no
 * catalog marks up any more is stale and fails, as an allow-list entry does. What a message
 * interpolates — the arguments after its key — is not the catalog's: the rule above checks it, within
 * the limits stated next.
 *
 * ## Completeness, stated honestly
 *
 * The forms are a floor, not a proof. The gate does not see:
 *   - a field whose name ends with none of the suffixes (`label`, `title`, `text`, `value`, …): grow
 *     `TEXT_SUFFIXES` with the rule. A suffix matches by spelling, not meaning, so `className`,
 *     `tagName` or an `iconTag` holding markup are reported too — rename a fragment `…Html`, or escape;
 *   - an icon *URL* held in a variable named like a fragment (`rIcon` in `src="${rIcon}"`): `…Icon`
 *     marks HTML, not text — name URL-valued icons `…Url`/`…Src`;
 *   - a field renamed by an assignment (`const n = row.display_name`, `const label =
 *     String(r.values[col.key])`, a destructured local with another name): beyond the iteration
 *     rename above, it matches names and reads, it does not trace data.
 *     The converse holds too: a local that already holds escaped text must not reuse a field's name
 *     (`const name = escapeHtml(…)` is reported) — name it `nameHtml`, or escape at the interpolation;
 *   - HTML assembled by concatenation (`'<b>' + name + '</b>'`), or a sink fed with no template at
 *     all (`{@html value}`, `innerHTML = value`): the sinks are `htmlSink.gate.test.ts`'s subject;
 *   - a fragment that is not named like one (`` `${prefix}${name}` `` where `prefix` holds markup), or
 *     that is interpolated as a call (`${typeBadgeHtml(t)}`) — the helper's own template is checked,
 *     the composition is not;
 *   - the other parameters of the helpers in `HTML_FIRST_ARGUMENT`: `buildTooltipRow(label, valueHtml,
 *     …)` takes HTML in its second one too, and only the first is checked — as is any other helper
 *     that takes HTML, until it is added to the list;
 *   - an escape that is right for text but wrong for its place: `escapeHtml` escapes quotes, so it is
 *     right in both, but a hand-rolled chain of `.replace()` calls is not recognised as an escape at
 *     all — it is reported, and replacing it with `escapeHtml` is the fix;
 *   - a translation inside an attribute value (`title="${$t(…)}"`): the catalog check reads a value as
 *     text content, where a '"' changes nothing, while in an attribute a '"' ends the value. Catalog
 *     values do hold '"', but neither translation interpolated into a `title` today does: keep it so,
 *     or escape the site;
 *   - the fallback of `translateOr(translate, key, fallback)`: a literal of the code, in no catalog, so
 *     the catalog check never reads it;
 *   - a label bundle is known by its name, not by its content: a `…Labels` object that also carried
 *     user text would be let through — keep bundles to translations.
 * When the rule grows, grow the forms in the same change.
 *
 * Registered in `front_utility_unit` (`scripts/test_runner/_frontend_utility.py`, action `core-unit`).
 */

import {describe, expect, it} from 'vitest';
import {readdirSync, readFileSync} from 'node:fs';
import {createRequire} from 'node:module';
import {dirname, join, relative, resolve} from 'node:path';
import {fileURLToPath} from 'node:url';
import ts from 'typescript';
import {parse as parseSvelte} from 'svelte/compiler';

/** `frontend/`: paths are reported relative to it, the directory the runner and `vitest run` start from. */
const FRONTEND = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const SRC = join(FRONTEND, 'src');

/**
 * User- or provider-supplied text: names, notes, tags, file names, codes read from a file or a
 * provider — and the URL-ish values that end up inside `src="…"`, `href="…"`, `title="…"`.
 *
 * Matched as a case-insensitive SUFFIX of the leaf name, because the same value travels under many
 * names: `rName`, `origName`, `brokerName`, `displayName`, `display_name`, `iconUrl`, `imgSrc`,
 * `docsUrl` — an exact list missed every variant it did not spell out. `identifier` is a prefix
 * instead (`identifier_isin`, `identifierPromptValues`). There is deliberately no `icon` suffix:
 * `brokerIcon`, `assetIcon` and `iconHtml` hold HTML fragments — they are what makes a template HTML
 * (see `FRAGMENT_NAME`) — so a variable holding an icon *URL* is named `…Url` or `…Src`.
 */
const TEXT_SUFFIXES = ['name', 'notes', 'note', 'description', 'tags', 'tag', 'filename', 'url', 'src', 'href', 'symbol', 'currency', 'comment', 'tooltip'] as const;
const TEXT_PREFIX = 'identifier';
const isTextField = (name: string): boolean => {
    const lower = name.toLowerCase();
    return lower.startsWith(TEXT_PREFIX) || TEXT_SUFFIXES.some((suffix) => lower.endsWith(suffix));
};

/** The one accepted escape: `$lib/utils/core/escapeHtml`, which escapes `& < > " '`. */
const ESCAPE = 'escapeHtml';
/**
 * Local escapers that leave `"` alone (and some of them `>`): rejected wherever they feed HTML, whatever
 * they escape — inside an attribute value they do not stop a breakout. The fix is `escapeHtml`.
 */
const REJECTED_ESCAPES = new Set(['esc', 'escHtml']);

/** An interpolation named like an HTML fragment makes its template HTML, tag or no tag. */
const FRAGMENT_NAME = /(?:Html|Icon|icon|Badge|badge)$/;

/**
 * Number formats. A read through a computed key that is itself the value formatted — `x[k].toFixed(2)`,
 * or through a fallback, `(x[k] ?? 0).toFixed(2)` — renders a number, so the computed-key rule lets it
 * through. Only that rule, and only that shape: `toLocaleString` also exists on strings and arrays, so
 * `row.display_name.toLocaleString()` is still reported by the name rule, and `String(x[k])
 * .toLocaleString()` — text made into text — by the computed-key rule. A read formatted this way is
 * trusted to be a number; formatting text with `toLocaleString` would hand it back unchanged.
 */
const NUMERIC_FORMATS = new Set(['toFixed', 'toLocaleString']);

/**
 * Helpers whose FIRST parameter is HTML by contract. `buildTooltipRow(label, …)`,
 * `buildTooltipHeader(title, …)`, `buildFittedTooltipRow(labelHtml, …)` and `fitTooltipToWidth(html, …)`
 * come from `echartsTooltipHelpers.ts` — some charts keep local copies under the same names — and
 * GrowthChart's `pnlRow(label, …)` is handed `<b>…</b>` on purpose. The
 * first argument of a call to one of them is checked as an interpolation into HTML.
 */
const HTML_FIRST_ARGUMENT = new Set(['buildTooltipRow', 'buildTooltipHeader', 'buildFittedTooltipRow', 'fitTooltipToWidth', 'pnlRow']);

/** A bundle of translated labels — `labels`, `pnlLabels`, `eurLabels`: its properties are i18n text, whatever they are called. */
const LABEL_BUNDLE = /^(?:labels|[a-z][A-Za-z0-9]*Labels)$/;

interface ReviewedException {
    file: string;
    /** The interpolated expression, whitespace collapsed, exactly as the failure message prints it. */
    expr: string;
    why: string;
}

/**
 * Interpolations reviewed and kept on purpose: NONE yet. Add one only with a reason a reviewer can
 * check ("the value is a validated ISO code" is a reason; "it is fine" is not).
 */
const REVIEWED_EXCEPTIONS: readonly ReviewedException[] = [];

/** An HTML tag in the static text of a template: `<span`, `</b>`, `<br/>`, `<img `, `<b${attrs}`. */
const MARKUP = /<\/?[A-Za-z][A-Za-z0-9-]*(?=[\s/>]|$)/;

/** Calls whose result carries none of their arguments' text. */
const NO_TEXT_CALLS = new Set(['Number', 'Boolean', 'parseInt', 'parseFloat', 'isNaN', 'isFinite']);
/** i18n calls: the first argument is a message key, the others are interpolated into the message. */
const I18N_CALLS = new Set(['$t', '$_']);
/** Methods returning numbers, booleans or nothing: the receiver's text does not reach the result. */
const NO_TEXT_METHODS = new Set(['includes', 'startsWith', 'endsWith', 'indexOf', 'lastIndexOf', 'some', 'every', 'findIndex', 'findLastIndex', 'has', 'test', 'localeCompare', 'charCodeAt', 'codePointAt', 'forEach']);
/** Methods whose result is built from what the callback returns, not from the receiver. */
const MAP_METHODS = new Set(['map', 'flatMap', 'reduce', 'reduceRight']);
/** Methods that keep the receiver's items but whose callback is a predicate or a comparator. */
const PREDICATE_METHODS = new Set(['filter', 'find', 'findLast', 'sort', 'toSorted']);
/** Methods whose result is still (some of) the receiver's items: a text field's items stay text through them. */
const ITEM_KEEPING_METHODS = new Set(['filter', 'find', 'findLast', 'sort', 'toSorted', 'slice', 'concat', 'reverse', 'toReversed', 'flat', 'split', 'at']);

interface Violation {
    file: string;
    line: number;
    /** Offset in the file: orders the violations of one line as the source does. */
    offset: number;
    /** The interpolated expression, whitespace collapsed. The allow-list key, together with `file`. */
    expr: string;
    /** The text fields that reach the HTML through it unescaped. */
    refs: string[];
}

interface TemplateSite {
    file: string;
    line: number;
    markup: boolean;
}

interface Scan {
    violations: Violation[];
    templates: TemplateSite[];
    parseErrors: string[];
}

interface Region {
    /** Offset of `text` in the file. */
    offset: number;
    text: string;
    /** A `<script>` body or a whole `.ts` file is a program; a markup expression is parsed as `(text)`. */
    kind: 'program' | 'expression';
}

const collapse = (s: string): string => s.trim().replace(/\s+/g, ' ');

/** Whether a path (relative to `frontend/`) is source this gate reads. */
function isScanned(path: string): boolean {
    if (!/\.(svelte|ts)$/.test(path) || /\.(test|d)\.ts$/.test(path)) return false;
    if (path.split('/').some((segment) => segment === '__tests__' || segment === '__mocks__' || segment === 'node_modules')) return false;
    return !path.startsWith('src/lib/api/generated') && !path.endsWith('.generated.ts');
}

function sourceFiles(dir: string = SRC, acc: string[] = []): string[] {
    for (const entry of readdirSync(dir, {withFileTypes: true})) {
        const full = join(dir, entry.name);
        if (entry.isDirectory()) {
            sourceFiles(full, acc);
        } else {
            const path = relative(FRONTEND, full).replaceAll('\\', '/');
            if (isScanned(path)) acc.push(path);
        }
    }
    return acc.sort();
}

/** Keys of a Svelte template node that hold a JS expression, and keys that hold child template nodes. */
const EXPRESSION_KEYS = ['expression', 'test', 'key', 'declaration', 'tag'] as const;
const CHILD_KEYS = ['fragment', 'nodes', 'attributes', 'value', 'consequent', 'alternate', 'body', 'fallback', 'pending', 'then', 'catch'] as const;

type SvelteNode = {type?: unknown; start?: unknown; end?: unknown; [key: string]: unknown};

/** Any node of the tree. A `Fragment` has no position, so traversal must not ask for one. */
const isNode = (value: unknown): value is SvelteNode & {type: string} => {
    const node = value as SvelteNode | null;
    return !!node && typeof node === 'object' && typeof node.type === 'string';
};

/** A node with a source range: what an expression must have to be read back from the text. */
const isPlaced = (value: unknown): value is SvelteNode & {type: string; start: number; end: number} => isNode(value) && typeof value.start === 'number' && typeof value.end === 'number';

/** The code regions of a `.svelte` file: its `<script>` bodies and every expression of its markup. */
function svelteRegions(text: string): Region[] {
    const ast = parseSvelte(text, {modern: true});
    const regions: Region[] = [];
    for (const script of [ast.module, ast.instance]) {
        if (!script) continue;
        // acorn positions every node it builds; the ESTree `Program` type just does not declare it.
        const {start, end} = script.content as unknown as {start: number; end: number};
        regions.push({offset: start, text: text.slice(start, end), kind: 'program'});
    }
    const visit = (node: SvelteNode): void => {
        for (const key of EXPRESSION_KEYS) {
            const expression = node[key];
            if (!isPlaced(expression)) continue;
            // `{@const x = …}` is a declaration, everything else an expression.
            const kind = expression.type === 'VariableDeclaration' ? 'program' : 'expression';
            regions.push({offset: expression.start, text: text.slice(expression.start, expression.end), kind});
        }
        for (const key of CHILD_KEYS) {
            const child = node[key];
            for (const item of Array.isArray(child) ? child : [child]) if (isNode(item)) visit(item);
        }
    };
    visit(ast.fragment as unknown as SvelteNode);
    return regions;
}

/** Line starts of a text, for offset → line in O(log n). */
function lineIndex(text: string): (offset: number) => number {
    const starts = [0];
    for (let i = 0; i < text.length; i++) if (text.charCodeAt(i) === 10) starts.push(i + 1);
    return (offset) => {
        let lo = 0;
        let hi = starts.length - 1;
        while (lo < hi) {
            const mid = (lo + hi + 1) >> 1;
            if (starts[mid] <= offset) lo = mid;
            else hi = mid - 1;
        }
        return lo + 1;
    };
}

/**
 * The violations, templates and parse errors of one source file. A function of its own so that a
 * synthetic source goes through exactly the code a real file goes through: a positive control run on
 * a copy of this logic would test the copy.
 */
function scanSource(file: string, text: string): Scan {
    const scan: Scan = {violations: [], templates: [], parseErrors: []};
    const lineAt = lineIndex(text);
    let regions: Region[];
    try {
        regions = file.endsWith('.svelte') ? svelteRegions(text) : [{offset: 0, text, kind: 'program'}];
    } catch (error) {
        scan.parseErrors.push(`${file}  ${(error as Error).message}`);
        return scan;
    }
    for (const region of regions) {
        // A markup expression without a backtick holds no template literal: nothing to parse.
        if (region.kind === 'expression' && !region.text.includes('`')) continue;
        const source = region.kind === 'expression' ? `(${region.text})` : region.text;
        const shift = region.offset - (region.kind === 'expression' ? 1 : 0);
        const sf = ts.createSourceFile(`${file}.ts`, source, ts.ScriptTarget.Latest, true, ts.ScriptKind.TS);
        const diagnostics = (sf as unknown as {parseDiagnostics?: readonly ts.Diagnostic[]}).parseDiagnostics ?? [];
        for (const diagnostic of diagnostics) scan.parseErrors.push(`${file}:${lineAt(shift + (diagnostic.start ?? 0))}  ${ts.flattenDiagnosticMessageText(diagnostic.messageText, ' ')}`);
        scanTree(sf, (node) => shift + node.getStart(sf), lineAt, file, scan);
    }
    scan.violations.sort((a, b) => a.offset - b.offset);
    return scan;
}

/** Names bound by a parameter or a declaration, destructuring included. */
function boundNames(name: ts.BindingName): string[] {
    if (ts.isIdentifier(name)) return [name.text];
    return name.elements.flatMap((element) => (ts.isOmittedExpression(element) ? [] : boundNames(element.name)));
}

const parameterNames = (fn: ts.SignatureDeclaration): string[] => fn.parameters.flatMap((parameter) => boundNames(parameter.name));

/** Walk one parsed region. `code` looks for templates; `reach` follows a value that ends up in HTML. */
function scanTree(sf: ts.SourceFile, offsetOf: (node: ts.Node) => number, lineAt: (offset: number) => number, file: string, scan: Scan): void {
    const isEscapeCall = (node: ts.Node): boolean => ts.isCallExpression(node) && ts.isIdentifier(node.expression) && node.expression.text === ESCAPE;

    /** The expression under parentheses, `!`, `as`, `satisfies` and `<T>`: the value, spelled plainly. */
    const unwrap = (node: ts.Expression): ts.Expression => {
        let inner = node;
        while (ts.isParenthesizedExpression(inner) || ts.isNonNullExpression(inner) || ts.isAsExpression(inner) || ts.isSatisfiesExpression(inner) || ts.isTypeAssertionExpression(inner)) inner = inner.expression;
        return inner;
    };

    /** An interpolation named like an HTML fragment: `iconHtml`, `brokerIcon`, `row.typeBadge`, `(icon)`. */
    const isFragment = (node: ts.Expression): boolean => {
        const inner = unwrap(node);
        if (ts.isIdentifier(inner)) return FRAGMENT_NAME.test(inner.text);
        if (ts.isPropertyAccessExpression(inner)) return FRAGMENT_NAME.test(inner.name.text);
        return false;
    };

    /** A bundle of translated labels (`LABEL_BUNDLE`): `eurLabels`, `labels`. */
    const isLabelBundle = (node: ts.Expression): boolean => {
        const inner = unwrap(node);
        return ts.isIdentifier(inner) && LABEL_BUNDLE.test(inner.text);
    };

    /** Computed reads that are the value of a number format (`NUMERIC_FORMATS`): they render a number. */
    const numericReads = new Set<ts.Node>();

    /** The computed reads a formatted value is made of: itself, or the sides of a fallback. */
    const formattedReads = (node: ts.Expression): ts.Expression[] => {
        const inner = unwrap(node);
        if (ts.isElementAccessExpression(inner)) return [inner];
        if (ts.isBinaryExpression(inner) && (inner.operatorToken.kind === ts.SyntaxKind.QuestionQuestionToken || inner.operatorToken.kind === ts.SyntaxKind.BarBarToken)) return [...formattedReads(inner.left), ...formattedReads(inner.right)];
        if (ts.isConditionalExpression(inner)) return [...formattedReads(inner.whenTrue), ...formattedReads(inner.whenFalse)];
        return [];
    };

    /**
     * Names bound to the items of a text field — the parameter of a callback iterating it, the
     * variable of a `for…of` over it — mapped to the field. Iterating renames every item, so without
     * this `row.tags.map((t) => `<b>${t}</b>`)` would lose the tags at the first step.
     */
    const items = new Map<string, string>();

    /** Run `walk` with `names` bound to the items of `origin` — or shadowed, when `origin` is null. */
    const binding = (names: string[], origin: string | null, walk: () => void): void => {
        const saved = names.map((name) => [name, items.get(name)] as const);
        for (const name of names) {
            if (origin) items.set(name, origin);
            else items.delete(name);
        }
        walk();
        for (const [name, previous] of saved) {
            if (previous === undefined) items.delete(name);
            else items.set(name, previous);
        }
    };

    const identifierRef = (name: string): string | null => (isTextField(name) ? name : items.has(name) ? `${name} (item of ${items.get(name)})` : null);

    /** Whether a value is a text field or a collection of its items: what a callback over it would see. */
    const carriesText = (node: ts.Node): boolean => {
        if (ts.isIdentifier(node)) return identifierRef(node.text) !== null;
        if (ts.isPropertyAccessExpression(node)) return isTextField(node.name.text);
        if (ts.isElementAccessExpression(node)) {
            const key = node.argumentExpression;
            return ts.isStringLiteral(key) || ts.isNoSubstitutionTemplateLiteral(key) ? isTextField(key.text) : carriesText(node.expression);
        }
        if (ts.isParenthesizedExpression(node) || ts.isAsExpression(node) || ts.isNonNullExpression(node) || ts.isSatisfiesExpression(node) || ts.isTypeAssertionExpression(node)) return carriesText(node.expression);
        if (ts.isBinaryExpression(node)) return (node.operatorToken.kind === ts.SyntaxKind.QuestionQuestionToken || node.operatorToken.kind === ts.SyntaxKind.BarBarToken) && (carriesText(node.left) || carriesText(node.right));
        if (ts.isConditionalExpression(node)) return carriesText(node.whenTrue) || carriesText(node.whenFalse);
        if (ts.isCallExpression(node) && ts.isPropertyAccessExpression(node.expression)) return ITEM_KEEPING_METHODS.has(node.expression.name.text) && carriesText(node.expression.expression);
        if (ts.isArrayLiteralExpression(node)) return node.elements.some((element) => carriesText(ts.isSpreadElement(element) ? element.expression : element));
        return false;
    };

    /**
     * A function passed as an argument. Its parameters are bound to `origin`'s items, or shadowed;
     * what it returns reaches `refs` when the caller's result is built from it.
     */
    const callback = (fn: ts.ArrowFunction | ts.FunctionExpression, origin: string | null, refs: string[] | null): void => {
        binding(parameterNames(fn), origin, () => {
            for (const parameter of fn.parameters) code(parameter, null);
            if (ts.isBlock(fn.body)) code(fn.body, refs);
            else if (refs) reach(fn.body, refs);
            else code(fn.body, null);
        });
    };

    const template = (node: ts.TemplateExpression, inHtml: boolean): void => {
        const markup = [node.head, ...node.templateSpans.map((span) => span.literal)].some((part) => MARKUP.test(part.text)) || node.templateSpans.some((span) => isFragment(span.expression));
        scan.templates.push({file, line: lineAt(offsetOf(node)), markup});
        for (const span of node.templateSpans) {
            if (!markup && !inHtml) {
                code(span.expression, null);
                continue;
            }
            const refs: string[] = [];
            reach(span.expression, refs);
            if (refs.length === 0) continue;
            const offset = offsetOf(span.expression);
            scan.violations.push({file, line: lineAt(offset), offset, expr: collapse(span.expression.getText(sf)), refs: [...new Set(refs)]});
        }
    };

    /** The first argument of a helper that takes HTML there (`HTML_FIRST_ARGUMENT`), checked as an interpolation. */
    const htmlArgument = (argument: ts.Expression, helper: string): void => {
        const refs: string[] = [];
        reach(argument, refs);
        if (refs.length === 0) return;
        const offset = offsetOf(argument);
        scan.violations.push({file, line: lineAt(offset), offset, expr: collapse(argument.getText(sf)), refs: [...new Set(refs)].map((ref) => `${ref} (into ${helper}())`)});
    };

    /**
     * Code whose value is not rendered: only templates are looked for. `ret` collects what the
     * enclosing function returns, when that function's result is itself being rendered.
     */
    const code = (node: ts.Node, ret: string[] | null): void => {
        if (isEscapeCall(node)) return;
        if (ts.isTemplateExpression(node)) return template(node, false);
        if (ts.isReturnStatement(node)) {
            if (node.expression) {
                if (ret) reach(node.expression, ret);
                else code(node.expression, null);
            }
            return;
        }
        if (ts.isForOfStatement(node)) {
            code(node.expression, null);
            const origin = carriesText(node.expression) ? collapse(node.expression.getText(sf)) : null;
            const names = ts.isVariableDeclarationList(node.initializer) ? node.initializer.declarations.flatMap((declaration) => boundNames(declaration.name)) : [];
            binding(names, origin, () => code(node.statement, ret));
            return;
        }
        if (ts.isCallExpression(node) && ts.isIdentifier(node.expression) && HTML_FIRST_ARGUMENT.has(node.expression.text) && node.arguments.length > 0) {
            // Rendered or not, the call puts its first argument into HTML.
            const [first, ...rest] = node.arguments;
            htmlArgument(first, node.expression.text);
            for (const arg of rest) code(arg, null);
            return;
        }
        if (ts.isCallExpression(node) && ts.isPropertyAccessExpression(node.expression)) {
            // A result nobody renders — but a callback over a text field still sees its items.
            const receiver = node.expression.expression;
            const origin = carriesText(receiver) ? collapse(receiver.getText(sf)) : null;
            code(receiver, null);
            for (const arg of node.arguments) {
                if (ts.isArrowFunction(arg) || ts.isFunctionExpression(arg)) callback(arg, origin, null);
                else code(arg, null);
            }
            return;
        }
        if (ts.isFunctionLike(node)) {
            binding(parameterNames(node), null, () => ts.forEachChild(node, (child) => code(child, null)));
            return;
        }
        ts.forEachChild(node, (child) => code(child, ret));
    };

    /** A value rendered into HTML: collect the text fields that reach it unescaped into `refs`. */
    const reach = (node: ts.Node, refs: string[]): void => {
        if (isEscapeCall(node)) return;
        if (ts.isTemplateExpression(node)) return template(node, true);
        if (ts.isTaggedTemplateExpression(node)) {
            code(node.tag, null);
            if (ts.isTemplateExpression(node.template)) template(node.template, true);
            return;
        }
        if (ts.isIdentifier(node)) {
            const ref = identifierRef(node.text);
            if (ref) refs.push(ref);
            return;
        }
        if (ts.isPropertyAccessExpression(node)) {
            // A label bundle's property is a translation, whatever it is called (`eurLabels.…Tooltip`).
            if (isTextField(node.name.text) && !isLabelBundle(node.expression)) refs.push(collapse(node.getText(sf)));
            code(node.expression, null);
            return;
        }
        if (ts.isElementAccessExpression(node)) {
            const key = node.argumentExpression;
            if (ts.isStringLiteral(key) || ts.isNoSubstitutionTemplateLiteral(key)) {
                // `x['name']` is a member access spelled differently.
                if (isTextField(key.text)) refs.push(collapse(node.getText(sf)));
                code(node.expression, null);
            } else {
                // A computed key hides which field is read (`r.values[col.key]`): the read is reported
                // whatever its name, unless it renders a number. `x[0]` names its item: the rule below alone.
                if (!ts.isNumericLiteral(key) && !numericReads.has(node)) refs.push(`${collapse(node.getText(sf))} (computed key)`);
                // `x[i]` is an item of `x`, and an item of a text field is text.
                reach(node.expression, refs);
                code(key, null);
            }
            return;
        }
        if (ts.isCallExpression(node) || ts.isNewExpression(node)) return call(node, refs);
        if (ts.isConditionalExpression(node)) {
            code(node.condition, null);
            reach(node.whenTrue, refs);
            reach(node.whenFalse, refs);
            return;
        }
        if (ts.isBinaryExpression(node)) return binary(node, refs);
        if (ts.isPrefixUnaryExpression(node) || ts.isPostfixUnaryExpression(node)) return code(node.operand, null);
        if (ts.isTypeOfExpression(node) || ts.isVoidExpression(node) || ts.isDeleteExpression(node)) return code(node.expression, null);
        if (ts.isParenthesizedExpression(node) || ts.isAsExpression(node) || ts.isNonNullExpression(node) || ts.isTypeAssertionExpression(node) || ts.isSatisfiesExpression(node) || ts.isAwaitExpression(node) || ts.isSpreadElement(node)) return reach(node.expression, refs);
        if (ts.isArrowFunction(node) || ts.isFunctionExpression(node)) return callback(node, null, refs);
        if (ts.isObjectLiteralExpression(node)) {
            for (const property of node.properties) {
                if (ts.isPropertyAssignment(property)) {
                    code(property.name, null);
                    reach(property.initializer, refs);
                } else if (ts.isShorthandPropertyAssignment(property)) {
                    const ref = identifierRef(property.name.text);
                    if (ref) refs.push(ref);
                } else if (ts.isSpreadAssignment(property)) {
                    reach(property.expression, refs);
                } else {
                    code(property, null);
                }
            }
            return;
        }
        if (ts.isArrayLiteralExpression(node)) {
            for (const element of node.elements) reach(element, refs);
            return;
        }
        if (ts.isLiteralExpression(node) || node.kind === ts.SyntaxKind.TrueKeyword || node.kind === ts.SyntaxKind.FalseKeyword || node.kind === ts.SyntaxKind.NullKeyword || node.kind === ts.SyntaxKind.ThisKeyword) return;
        // Anything else: assume its parts reach its value.
        ts.forEachChild(node, (child) => reach(child, refs));
    };

    const call = (node: ts.CallExpression | ts.NewExpression, refs: string[]): void => {
        const callee = node.expression;
        const args = node.arguments ?? [];
        if (ts.isPropertyAccessExpression(callee)) {
            const method = callee.name.text;
            const receiver = callee.expression;
            // `.includes()`, `.some()`, `.forEach()`: nothing of the receiver or of a callback reaches the result.
            // `.map(cb)`: the callbacks build the result, the receiver does not.
            // `.filter(cb)`: the receiver's items do, the predicate does not.
            // `.join()`, `.trim()`, `.replace()`, anything unknown: both may.
            const receiverReaches = !NO_TEXT_METHODS.has(method) && !MAP_METHODS.has(method);
            const argumentsReach = !NO_TEXT_METHODS.has(method) && !PREDICATE_METHODS.has(method);
            const origin = carriesText(receiver) ? collapse(receiver.getText(sf)) : null;
            // `x[k].toFixed(2)`: the computed read is the number being formatted.
            if (NUMERIC_FORMATS.has(method)) for (const read of formattedReads(receiver)) numericReads.add(read);
            if (receiverReaches) reach(receiver, refs);
            else code(receiver, null);
            for (const arg of args) {
                if (ts.isArrowFunction(arg) || ts.isFunctionExpression(arg)) callback(arg, origin, argumentsReach ? refs : null);
                else if (argumentsReach) reach(arg, refs);
                else code(arg, null);
            }
            return;
        }
        if (ts.isIdentifier(callee)) {
            if (NO_TEXT_CALLS.has(callee.text)) {
                for (const arg of args) code(arg, null);
            } else if (I18N_CALLS.has(callee.text)) {
                args.forEach((arg, index) => (index === 0 ? code(arg, null) : reach(arg, refs)));
            } else {
                // A rejected escaper is itself the finding: what it lets through is `"`, not a field.
                if (REJECTED_ESCAPES.has(callee.text)) refs.push(`${callee.text}() leaves quotes unescaped`);
                for (const arg of args) reach(arg, refs);
            }
            return;
        }
        code(callee, null);
        for (const arg of args) reach(arg, refs);
    };

    const binary = (node: ts.BinaryExpression, refs: string[]): void => {
        switch (node.operatorToken.kind) {
            case ts.SyntaxKind.PlusToken:
            case ts.SyntaxKind.PlusEqualsToken:
            case ts.SyntaxKind.BarBarToken:
            case ts.SyntaxKind.BarBarEqualsToken:
            case ts.SyntaxKind.QuestionQuestionToken:
            case ts.SyntaxKind.QuestionQuestionEqualsToken:
                reach(node.left, refs);
                reach(node.right, refs);
                return;
            // `a && b` renders `a` only when it is falsy: an empty string, never markup.
            case ts.SyntaxKind.AmpersandAmpersandToken:
            case ts.SyntaxKind.AmpersandAmpersandEqualsToken:
            case ts.SyntaxKind.EqualsToken:
            case ts.SyntaxKind.CommaToken:
                code(node.left, null);
                reach(node.right, refs);
                return;
            default:
                // Comparisons, arithmetic, bitwise, `in`, `instanceof`: numbers and booleans.
                code(node.left, null);
                code(node.right, null);
        }
    };

    code(sf, null);
}

const key = (site: {file: string; expr: string}): string => `${site.file}\u0000${site.expr}`;
/** `file:line  expr` for every violation of a synthetic source. */
const caught = (file: string, text: string): string[] => scanSource(file, text).violations.map((v) => `${v.line}  ${v.expr}`);

describe('HTML built by hand escapes user and provider text (K step 13, item 0 gate)', () => {
    const files = sourceFiles();
    const scans = files.map((file) => scanSource(file, readFileSync(join(FRONTEND, file), 'utf8')));
    const violations = scans.flatMap((scan) => scan.violations);
    const templates = scans.flatMap((scan) => scan.templates);
    const parseErrors = scans.flatMap((scan) => scan.parseErrors);

    it('finds a raw text field in a markup template, in a .ts file and in both halves of a .svelte file', () => {
        // The positive control of the verdict below: "no violation" is also what a scanner whose
        // parser reads nothing would report.
        expect(caught('a.ts', 'const html = `<span class="x">${row.display_name}</span>`;')).toEqual(['1  row.display_name']);
        expect(caught('a.ts', 'export function badge(name: string, iconUrl: string) {\n    return `<img src="${iconUrl}" alt="" /><b>${name}</b>`;\n}')).toEqual(['2  iconUrl', '2  name']);
        expect(caught('a.svelte', '<script lang="ts">\n    const cell = (row: Row) => ({type: \'html\', html: `<div>${row.display_name}</div>`});\n</script>')).toEqual(['2  row.display_name']);
        expect(caught('a.svelte', '<div>\n    {@html `<b>${asset.name}</b>`}\n</div>\n<Tooltip html={`<i>${x?.notes}</i>`} />')).toEqual(['2  asset.name', '4  x?.notes']);
        expect(caught('a.ts', "const t = `<td>${row['tags']}</td><td>${row.identifier_isin}</td><td>${row.currency}</td>`;")).toEqual(["1  row['tags']", '1  row.identifier_isin', '1  row.currency']);
    });

    it('reaches the markup inside every kind of Svelte block', () => {
        // A `Fragment` carries no source position: a traversal that asked every node for one
        // stopped at the first element and reported the whole markup clean.
        const markup = [
            '{#if a}',
            '    {#each items as item (item.id)}',
            '        {@const badge = `<em>${item.comment}</em>`}',
            '        <td title={`<b>${item.name}</b>`}>{@html `<i>${item.notes}</i>`}</td>',
            '    {:else}',
            '        {#await p}<i title={`<b>${w.note}</b>`}></i>{:then v}<span class="{`<b>${v.tags}</b>`}"></span>{:catch e}{@html `<i>${e.description}</i>`}{/await}',
            '    {/each}',
            '{:else if b}',
            '    {#key k}<Comp html={`<u>${x.description}</u>`} onclick={() => show(`<b>${x.fileName}</b>`)} />{/key}',
            '{/if}',
            '{#snippet cell(r)}<svelte:element this={tag}><p>{@html `<s>${r.symbol}</s>`}</p></svelte:element>{/snippet}',
        ].join('\n');
        expect(caught('a.svelte', markup)).toEqual(['3  item.comment', '4  item.name', '4  item.notes', '6  w.note', '6  v.tags', '6  e.description', '9  x.description', '9  x.fileName', '11  r.symbol']);
    });

    it('keeps the line of an interpolation inside a multi-line template', () => {
        expect(caught('a.ts', 'const html = `\n    <div>\n        ${row.display_name}\n    </div>`;')).toEqual(['3  row.display_name']);
        expect(caught('a.svelte', '<p>x</p>\n\n{@html `<ul>\n    <li>${item.description}</li>\n</ul>`}')).toEqual(['4  item.description']);
    });

    it('follows a value into a nested template and through the calls that keep its text', () => {
        expect(caught('a.ts', "const h = `<div>${items.map((i) => `${i.name}`).join('')}</div>`;")).toEqual(['1  i.name']);
        expect(caught('a.ts', "const h = `<div>${items.map((i) => i.name).join(', ')}</div>`;")).toEqual(["1  items.map((i) => i.name).join(', ')"]);
        expect(caught('a.ts', "const h = `<b>${(row.notes ?? '').trim().slice(0, 20)}</b>`;")).toEqual(["1  (row.notes ?? '').trim().slice(0, 20)"]);
        expect(caught('a.ts', "const h = `<b>${$t('x.label', {values: {name: row.display_name}})}</b>`;")).toEqual(["1  $t('x.label', {values: {name: row.display_name}})"]);
        expect(caught('a.ts', 'const h = `<b>${truncate(fileName, 30)}</b>`;')).toEqual(['1  truncate(fileName, 30)']);
        expect(caught('a.ts', "const h = `<b>${ok ? row.name : '—'}</b>`;")).toEqual(["1  ok ? row.name : '—'"]);
        expect(caught('a.ts', 'const h = `<b>${list.map((x) => {\n    return x.symbol;\n})}</b>`;')).toEqual(['1  list.map((x) => { return x.symbol; })']);
        expect(caught('a.ts', 'const h = `<b>${row.tags[0]}</b>`;')).toEqual(['1  row.tags[0]']);
    });

    it('keeps the taint of a text field through the rename that iterating it forces', () => {
        // `.map()` builds its result from the callback, not from the receiver: without binding the
        // parameter to the receiver's items, `t` would be an unknown name and the tags would pass.
        expect(caught('a.ts', "const h = `<div>${row.tags.map((t) => `<span>${t}</span>`).join('')}</div>`;")).toEqual(['1  t']);
        expect(caught('a.ts', "let h = '';\nrow.tags.forEach((t) => {\n    h += `<b>${t.trim()}</b>`;\n});")).toEqual(['3  t.trim()']);
        expect(caught('a.ts', "let h = '';\nfor (const line of (row.notes ?? '').split('\\n')) h += `<p>${line}</p>`;")).toEqual(['2  line']);
        expect(caught('a.ts', "const h = row.tags.map(({0: first}) => `<i>${first}</i>`).join('');")).toEqual(['1  first']);
        // Escaped, measured, or shadowed by a callback over something that is not text: not a violation.
        expect(caught('a.ts', "const h = `<div>${row.tags.map((t) => `<span>${escapeHtml(t)}</span>`).join('')}</div>`;")).toEqual([]);
        expect(caught('a.ts', "const h = row.tags.map((t) => `<i>${t.length}</i>`).join('');")).toEqual([]);
        expect(caught('a.ts', "const h = row.tags.map((t) => [1, 2].map((t) => `<b>${t}</b>`).join('')).join('');")).toEqual([]);
        expect(caught('a.ts', "const h = rows.map((t) => `<b>${t.id}</b>`).join('');\nfor (const t of rows) out += `<i>${t}</i>`;")).toEqual([]);
    });

    it('accepts every value that passes through escapeHtml', () => {
        expect(caught('a.ts', 'const h = `<span>${escapeHtml(row.display_name)}</span>`;')).toEqual([]);
        expect(caught('a.ts', "const h = `<span>${cond ? escapeHtml(a.name) : '—'}</span><i>${escapeHtml(`${a.name} (${a.currency})`)}</i>`;")).toEqual([]);
        expect(caught('a.ts', "const h = `<div>${items.map((i) => `<b>${escapeHtml(i.name)}</b>`).join('')}</div>`;")).toEqual([]);
        expect(caught('a.ts', 'const h = `<img src="${escapeHtml(iconUrl)}" alt="" />${escapeHtml(name)}`;')).toEqual([]);
    });

    it('rejects the local escapers that leave quotes alone, whatever they escape', () => {
        // `esc` and `escHtml` stop `<` but not `"`: in `title="${esc(raw)}"` a quote still closes the
        // attribute. So the call is the finding even when its argument is no text field at all.
        expect(caught('src/lib/utils/transactions/importCompare.ts', 'const h = `<span>${escHtml(label)}</span>`;')).toEqual(['1  escHtml(label)']);
        expect(caught('src/lib/components/transactions/modals/ImportWizardModal.svelte', '<script lang="ts">\n    const h = `<b title="${esc(raw)}">${esc(file.name)}</b>`;\n</script>')).toEqual(['2  esc(raw)', '2  esc(file.name)']);
        // The same call on a value no HTML ever sees is not a finding.
        expect(caught('a.ts', 'const plain = `${esc(raw)} (${count})`;')).toEqual([]);
    });

    it('treats a template as HTML when it composes a fragment named like one', () => {
        // No tag in the static text, but `brokerIcon` is an <img>: what follows it lands in the same HTML.
        expect(caught('a.ts', 'const label = broker ? `${brokerIcon}${broker.name}` : `Broker #${id}`;')).toEqual(['1  broker.name']);
        expect(caught('a.ts', 'const a = `${iconHtml}${name}`;\nconst b = `${row.typeBadge} ${row.display_name}`;\nconst c = `${(icon)!}${asset.description}`;\nconst d = `${badge}: ${x.notes}`;')).toEqual(['1  name', '2  row.display_name', '3  asset.description', '4  x.notes']);
        // A prefix not named like a fragment does not make HTML by itself.
        expect(caught('a.ts', 'const a = `${prefix}${row.name}`;\nconst b = `${iconUrl}: ${row.name}`;\nconst c = `${iconSize}px ${row.name}`;')).toEqual([]);
    });

    it('treats URL-ish values as text: they end up inside attribute values', () => {
        expect(caught('a.ts', 'const a = `<img src="${src}" alt=""><img src="${iconSrc}"><img src="${imgSrc}">`;')).toEqual(['1  src', '1  iconSrc', '1  imgSrc']);
        expect(caught('a.ts', 'const a = `<a href="${link.href}" title="${tooltip}">${label}</a><a href="${row.url}">x</a>`;')).toEqual(['1  link.href', '1  tooltip', '1  row.url']);
    });

    it('matches a text field by suffix, whatever the name in front of it', () => {
        // The real case: ImportWizardModal carries asset names as `rName`/`origName`, which an exact
        // list of field names never saw.
        expect(caught('a.ts', 'const a = `<b>${rName}</b><i>${origName}</i><img src="${iconUrl}">`;')).toEqual(['1  rName', '1  origName', '1  iconUrl']);
        // Case-insensitive, camelCase and snake_case, a property leaf, and the `identifier` prefix.
        expect(caught('a.ts', 'const b = `<td>${row.brokerName}</td><td>${row.display_name}</td><td>${ASSET_NAME}</td><a href="${docsUrl}"><img src="${imgSrc}"></a><s>${identifierPromptValues[0]}</s>`;')).toEqual([
            '1  row.brokerName',
            '1  row.display_name',
            '1  ASSET_NAME',
            '1  docsUrl',
            '1  imgSrc',
            '1  identifierPromptValues[0]',
        ]);
        // A fragment is not text: `brokerIcon` makes the template HTML and is not itself a finding.
        expect(caught('a.ts', 'const c = `<span>${brokerIcon}</span>`;\nconst d = `${assetIcon}${count}`;\nconst e = `${iconHtml}`;')).toEqual([]);
    });

    it('reports a value read through a computed key, unless it renders a number', () => {
        // The DataEditor shape: a column key known only at run time hides the field's name, so no
        // name rule can tell a note from a number — the read itself is the finding.
        expect(caught('a.svelte', '<script lang="ts">\n    const cell = (r: Row) => ({type: \'html\', html: `<span class="x">${r.values[col.key] ?? \'—\'}</span>`});\n</script>')).toEqual(["2  r.values[col.key] ?? '—'"]);
        // Whatever the names around it: a lookup keyed by a text field, an index, a fragment-made template.
        expect(caught('a.ts', 'const h = `<i>${labels[row.currency]}</i><b>${row.cells[i]}</b>`;\nconst f = `${iconHtml}${names[id]}`;')).toEqual(['1  labels[row.currency]', '1  row.cells[i]', '2  names[id]']);
        // The value of a number format, directly or through a fallback: a number, not a finding.
        expect(caught('a.ts', 'const h = `<span>${band.upper[dataIdx].toFixed(4)}</span><b>${(totals[i]!).toLocaleString(undefined, {maximumFractionDigits: 2})}</b><i>${(r.values[k] ?? 0).toFixed(2)}</i>`;')).toEqual([]);
        // Discarded by the flow rules — a number, a length, a ternary test — or escaped, or not HTML.
        expect(caught('a.ts', 'const h = `<b>${Number(r.values[k])}</b><i>${String(r.values[k]).length}</i><u>${r.values[k].length}</u><s>${flags[k] ? 1 : 0}</s>`;')).toEqual([]);
        expect(caught('a.ts', "const h = `<b>${escapeHtml(String(r.values[col.key] ?? '—'))}</b>`;\nconst p = `${r.values[col.key]} (${n})`;")).toEqual([]);
        // A literal key names its field, so the name rule alone decides: `id` and an item of a plain list are not text.
        expect(caught('a.ts', "const h = `<b>${row['id']}</b><i>${parts[0]}</i><u>${row['notes']}</u>`;")).toEqual(["1  row['notes']"]);
        // Only the formatted read itself is let through: text made into text keeps its finding, and a
        // named text field formatted with `toLocaleString` keeps the name rule's.
        expect(caught('a.ts', 'const h = `<b>${String(labels[k]).toLocaleString()}</b><i>${row.display_name.toLocaleString()}</i>`;')).toEqual(['1  String(labels[k]).toLocaleString()', '1  row.display_name.toLocaleString()']);
    });

    it('checks the first argument of a helper that takes HTML there, as it checks an interpolation', () => {
        // GrowthChart's shapes: the helper is called for its return value, inside a callback, and is
        // never itself interpolated — the call is the finding, wherever it stands.
        const shapes = [
            "let html = '';",
            'brokers.forEach((broker, index) => {',
            '    html += pnlRow(broker.brokerName, broker.metric.values[idx], color);',
            '});',
            'html += items.map((p) => {',
            '    return buildTooltipRow(p.seriesName, `${p.value}%`, p.color);',
            "}).join('');",
            'const header = buildTooltipHeader(meta.broker_name, theme.textColor);',
        ].join('\n');
        expect(caught('a.ts', shapes)).toEqual(['3  broker.brokerName', '6  p.seriesName', '8  meta.broker_name']);
        // Escaped, a translation, a label bundle's entry, markup made of translations, a date: allowed.
        const allowed = "h += buildTooltipRow(escapeHtml(p.seriesName), v);\nh += buildTooltipRow($_('common.asset'), v);\nh += buildTooltipRow(eurLabels.capitalBaselineTooltip, v);\nh += pnlRow(`<b>${pnlLabels.total}</b>`, v, c);\nh += buildTooltipHeader(bucket.bucketEnd, color);";
        expect(caught('a.ts', allowed)).toEqual([]);
        // Only the first parameter is the helper's HTML: the others are values, colours, numbers.
        expect(caught('a.ts', 'h += pnlRow(label, broker.metric.values[idx], broker.colorName);')).toEqual([]);
        // A label bundle holds translations in a template too; another object's text field does not.
        expect(caught('a.ts', 'const t = `<b>${eurLabels.bookAssetLikeTooltip}</b><i>${labels.brokerName}</i><u>${row.tooltip}</u>`;')).toEqual(['1  row.tooltip']);
    });

    it('ignores values that render no text of the field', () => {
        expect(caught('a.ts', 'const h = `<b>${row.name.length}</b><i>${row.tags.includes(t) ? 1 : 0}</i><u>${row.name === x}</u>`;')).toEqual([]);
        expect(caught('a.ts', "const h = `<b>${row.notes ? 'yes' : 'no'}</b><i>${row.currency && escapeHtml(row.currency)}</i><s>${getCurrencyInfo(row.currency).flag_emoji}</s>`;")).toEqual([]);
        expect(caught('a.ts', 'const h = `<b>${$t(`assets.types.${type}`)}</b><i>${Number(row.symbol)}</i><u>${!row.description}</u>`;')).toEqual([]);
        expect(caught('a.ts', 'const h = `<b>${items.filter((i) => i.name === q).length}</b>`;')).toEqual([]);
    });

    it('ignores templates without markup, strings, and comments', () => {
        expect(caught('a.ts', 'const label = `${row.display_name} (${row.currency})`;\nconst key = `asset-${row.name}`;')).toEqual([]);
        expect(caught('a.ts', 'const s = \'<b>${row.name}</b>\';\nconst d = "<i>${row.notes}</i>";')).toEqual([]);
        expect(caught('a.ts', '// const h = `<b>${row.display_name}</b>`;\n/* const h = `<b>${row.display_name}</b>`; */\n/** e.g. `<b>${row.name}</b>` */')).toEqual([]);
        expect(caught('a.svelte', '<script lang="ts">\n    // `<b>${row.name}</b>`\n</script>\n<!-- {@html `<b>${row.display_name}</b>`} -->\n<p>`<b>${row.name}</b>`</p>')).toEqual([]);
        // `<` that opens no tag: a comparison, a generic, a lone `<` before an interpolation.
        expect(caught('a.ts', 'const s = `a < ${b.name}`;\nconst g = `Map<string, ${x.name}>`;\nconst c = `${lo.name}<${hi.name}`;')).toEqual([]);
    });

    it('reads every source file of the app, and no test, mock or generated client', () => {
        expect(isScanned('src/lib/components/assets/AssetTable.svelte')).toBe(true);
        expect(isScanned('src/lib/utils/providerHelpers.ts')).toBe(true);
        expect(isScanned('src/lib/stores/app/notify.svelte.ts')).toBe(true);
        expect(isScanned('src/lib/utils/core/__tests__/escapeHtml.test.ts')).toBe(false);
        expect(isScanned('src/htmlInterpolation.gate.test.ts')).toBe(false);
        expect(isScanned('src/__mocks__/$app/navigation.ts')).toBe(false);
        expect(isScanned('src/app.d.ts')).toBe(false);
        expect(isScanned('src/lib/api/generated.ts')).toBe(false);
        expect(isScanned('src/lib/api/generated-tools.ts')).toBe(false);
        expect(isScanned('src/lib/api/tool-contract-map.generated.ts')).toBe(false);

        // The walk reaches the files that build HTML by hand: a scan of the wrong directory, or a
        // parser that silently reads nothing, would report them clean too.
        expect(files).toEqual(expect.arrayContaining(['src/lib/components/assets/AssetTable.svelte', 'src/lib/components/table/DataTable.svelte', 'src/lib/utils/providerHelpers.ts', 'src/lib/components/transactions/modals/ImportWizardModal.svelte']));
        const markupTemplatesIn = (file: string): number => templates.filter((t) => t.file === file && t.markup).length;
        expect(markupTemplatesIn('src/lib/components/assets/AssetTable.svelte')).toBeGreaterThan(0);
        expect(markupTemplatesIn('src/lib/utils/providerHelpers.ts')).toBeGreaterThan(0);
        // 321 markup templates in 46 files when this gate was written: a parser that silently reads
        // nothing, or a walk that reaches the wrong directory, finds none — or far fewer.
        expect(templates.filter((t) => t.markup).length).toBeGreaterThan(200);
        expect(new Set(templates.filter((t) => t.markup).map((t) => t.file)).size).toBeGreaterThan(30);
    });

    it('parses every file it reads', () => {
        expect(parseErrors, ['', 'These files could not be parsed, so the gate cannot vouch for them:', '', ...parseErrors, ''].join('\n  ')).toEqual([]);
    });

    it('finds no user or provider text interpolated into hand-built HTML without escaping', () => {
        const reviewed = new Set(REVIEWED_EXCEPTIONS.map(key));
        const offenders = violations.filter((v) => !reviewed.has(key(v))).map((v) => `${v.file}:${v.line}  ${v.expr}${v.refs.length === 1 && v.refs[0] === v.expr ? '' : `   ← ${v.refs.join(', ')}`}`);
        const rule = 'User or provider text — or a value read through a computed key — interpolated into hand-built HTML, or handed to a helper that takes HTML, must go through escapeHtml() ($lib/utils/core/escapeHtml.ts) — K step 13, item 0.';

        expect(offenders, ['', rule, `${offenders.length} unescaped interpolation(s):`, '', ...offenders, ''].join('\n  ')).toEqual([]);
    });

    it('keeps the reviewed exceptions current and explained', () => {
        const found = new Set(violations.map(key));
        const stale = REVIEWED_EXCEPTIONS.filter((entry) => !found.has(key(entry))).map((entry) => `${entry.file}  ${entry.expr}`);
        expect(stale, ['', 'Reviewed exceptions that no longer match a violation — delete them:', '', ...stale, ''].join('\n  ')).toEqual([]);
        expect(REVIEWED_EXCEPTIONS.filter((entry) => entry.why.trim().length < 20).map((entry) => `${entry.file}  ${entry.expr}`)).toEqual([]);
    });
});

/*
 * Item 10: the catalog check behind the i18n allowance.
 *
 * The gate above lets translations into hand-built HTML unescaped: an i18n call, whose interpolated
 * arguments it still checks, and a property of a label bundle. The text of a translation comes from the
 * catalogs, and chart tooltips, among other sites, interpolate it raw. That is sound only while every
 * catalog value reads as plain text once parsed as HTML: in text content, escaping changes what is shown
 * only where a "<" opens markup or an "&" starts a character reference. So the catalogs are checked
 * instead of the sites: no "<" anywhere — stricter than the parser, which shows `a < b` as text, so that
 * the rule stays simple — and no "&" the parser decodes, with or without ";". A lone "&", as in "P&L",
 * reads the same raw or escaped. A key that carries markup on purpose is listed, with its reason, in
 * `SANITIZED_MARKUP_KEYS`. The check reads a value as text content, not as an attribute value, where a
 * '"' would matter too.
 */

interface ReviewedMarkup {
    /** Dotted catalog key, as the catalog check prints it. */
    key: string;
    why: string;
}

/**
 * Translations that carry markup on purpose (item 10). All three are validation errors produced only by
 * `resolveIssueMessage()` in `src/lib/utils/transactions/resolveValidationMessage.ts`, as
 * `transactions.errors.<code>`, and every caller of `resolveIssueMessage` renders its result through
 * `{@html sanitizeHtml(…)}`: TransactionFormModal, TransactionBulkModal, ParseDetailModal. Never in a
 * tooltip. Add a key only with such a consumer.
 */
const SANITIZED_MARKUP_KEYS: readonly ReviewedMarkup[] = [
    {key: 'transactions.errors.balanceAssetNegative', why: '<strong> highlights the asset, the negative holding and the broker of a validation error rendered through sanitizeHtml.'},
    {key: 'transactions.errors.balanceCashNegative', why: '<strong> highlights the currency, the negative cash balance and the broker of a validation error rendered through sanitizeHtml.'},
    {key: 'transactions.errors.costBasisRequired', why: '<b> highlights the transaction type and the Auto and manual cost-basis modes of a validation error rendered through sanitizeHtml.'},
];

const CATALOG_DIR = join(SRC, 'lib', 'i18n');

/**
 * The UI catalogs by file name, in name order: every `*.json` in `src/lib/i18n`. Read inside the tests,
 * so a broken catalog fails these tests and not the collection of the whole gate.
 */
function readCatalogs(): Record<string, unknown> {
    return Object.fromEntries(
        readdirSync(CATALOG_DIR)
            .filter((name) => name.endsWith('.json'))
            .sort()
            .map((name) => [name, JSON.parse(readFileSync(join(CATALOG_DIR, name), 'utf8')) as unknown]),
    );
}

let htmlReader: HTMLElement | undefined;

/**
 * The text a browser shows for `html` set as the content of an element: the HTML parser of jsdom, with
 * the full table of named references and the legacy names that need no ";". Loaded on first use, so the
 * code gate above never pays for it.
 */
function textOfHtml(html: string): string {
    if (htmlReader === undefined) {
        // jsdom ships no type declarations, and @types/jsdom is not a dependency: type the one constructor used.
        const {JSDOM} = createRequire(import.meta.url)('jsdom') as {JSDOM: new () => {window: Window}};
        htmlReader = new JSDOM().window.document.createElement('div');
    }
    htmlReader.innerHTML = html;
    return htmlReader.textContent ?? '';
}

/**
 * Why a translation would not read as plain text once interpolated into HTML, or null when it would: the
 * reason is `contains "<"` for any "<", or `renders as «…»` with the text the HTML parser makes of it.
 */
function translationMarkup(value: string): string | null {
    if (value.includes('<')) return 'contains "<"';
    // In text content only "<" and "&" make the parser read anything but text, and "<" is already out.
    if (!value.includes('&')) return null;
    const text = textOfHtml(value);
    return text === value ? null : `renders as «${text}»`;
}

/**
 * Walks every string of the catalogs. `offenders`: each value `translationMarkup` flags whose dotted key
 * is not reviewed, as `${file}  ${key}  ${reason}`, in catalog order then document order. `stale`: the
 * reviewed keys that no catalog flags, in set order.
 */
function catalogMarkupFindings(catalogs: Readonly<Record<string, unknown>>, reviewed: ReadonlySet<string>): {offenders: string[]; stale: string[]} {
    const offenders: string[] = [];
    const marked = new Set<string>();
    const visit = (file: string, node: unknown, key: string): void => {
        if (typeof node === 'string') {
            const reason = translationMarkup(node);
            if (reason === null) return;
            if (reviewed.has(key)) marked.add(key);
            else offenders.push(`${file}  ${key}  ${reason}`);
        } else if (typeof node === 'object' && node !== null) {
            for (const [name, child] of Object.entries(node)) visit(file, child, key === '' ? name : `${key}.${name}`);
        }
    };
    for (const [file, catalog] of Object.entries(catalogs)) visit(file, catalog, '');
    return {offenders, stale: [...reviewed].filter((key) => !marked.has(key))};
}

describe('Translations interpolated into HTML read as plain text (item 10: the catalog check behind the i18n allowance)', () => {
    it('flags any "<" in a translation, even one the parser would show as text', () => {
        // `a < b` would show as text: the rule is stricter than the parser, so that it stays simple.
        expect(translationMarkup('Totale <b>P&L</b>')).toBe('contains "<"');
        expect(translationMarkup('a < b')).toBe('contains "<"');
    });

    it('flags every character reference the parser decodes, with or without ";"', () => {
        const decoded: [string, string][] = [
            ['1 &lt; 2', 'renders as «1 < 2»'],
            ['&#60;b&#62;', 'renders as «<b>»'],
            ['&#x3C;', 'renders as «<»'],
            ['Profit &amp; loss', 'renders as «Profit & loss»'],
            ['&eacute;t&eacute;', 'renders as «été»'],
            ['&copy 2026', 'renders as «© 2026»'], // a legacy name needs no ";"…
            ['R&notes', 'renders as «R¬es»'], // …and decodes even inside a word…
            ['P&LT', 'renders as «P<»'], // …so P&L is fine, but P&LT is not
        ];
        for (const [input, expected] of decoded) expect(translationMarkup(input), input).toBe(expected);
    });

    it('lets a lone "&" through: P&L stays P&L', () => {
        // None of these "&" starts a reference the parser decodes, and ">" and quotes read the same raw or escaped.
        for (const value of ['P&L', 'P&L, R&D, M&A, AT&T', 'S&P500', 'P&L; Q&A', '&#', '&;', 'a > b', `l'utile "netto"`, 'Plain text', '']) expect(translationMarkup(value), value).toBeNull();
    });

    it('walks every string of nested catalogs by dotted key, arrays included, in catalog order then document order', () => {
        // `n: 3` is not a string, so not a translation: the walk skips it.
        expect(catalogMarkupFindings({'en.json': {a: {b: 'x <y>', c: 'P&L'}, d: '1 &lt; 2', list: ['ok', 'R&notes'], n: 3}, 'it.json': {a: {b: 'ok', c: {d: {e: '&not'}}}, d: 'P&L;'}}, new Set())).toEqual({
            offenders: ['en.json  a.b  contains "<"', 'en.json  d  renders as «1 < 2»', 'en.json  list.1  renders as «R¬es»', 'it.json  a.c.d.e  renders as «¬»'],
            stale: [],
        });
    });

    it('keeps a reviewed key while any language marks it up, and reports a reviewed key nobody marks up as stale', () => {
        const catalogs = {'en.json': {e: {r: 'Balance <strong>negative</strong>'}, s: 'plain'}, 'it.json': {e: {r: 'Saldo negativo'}, s: 'semplice'}};
        // Markup in one language keeps the review needed; without the review, that markup is an offender…
        expect(catalogMarkupFindings(catalogs, new Set(['e.r']))).toEqual({offenders: [], stale: []});
        expect(catalogMarkupFindings(catalogs, new Set())).toEqual({offenders: ['en.json  e.r  contains "<"'], stale: []});
        // …and a reviewed key that no language marks up, or that no catalog has, is stale.
        expect(catalogMarkupFindings(catalogs, new Set(['e.r', 's', 'gone']))).toEqual({offenders: [], stale: ['s', 'gone']});
    });

    it('reads every UI catalog: en, it, fr and es', () => {
        const catalogs = readCatalogs();
        const names = ['en.json', 'it.json', 'fr.json', 'es.json'];
        expect(Object.keys(catalogs)).toEqual(expect.arrayContaining(names));
        for (const name of names) {
            expect(typeof catalogs[name], name).toBe('object');
            expect(catalogs[name], name).not.toBeNull();
        }
    });

    it('finds no markup in any translation outside the reviewed sanitized keys', () => {
        // An empty walk is green here too: the next test is the positive control on these same catalogs,
        // since the walk must still find the three reviewed keys there, or they read as stale.
        const {offenders} = catalogMarkupFindings(readCatalogs(), new Set(SANITIZED_MARKUP_KEYS.map((entry) => entry.key)));
        const rule =
            'Translations are interpolated into hand-built HTML without escapeHtml — the allowance of the gate above — so every catalog value must read as plain text: no "<" anywhere, and no "&" that starts a character reference ("&lt;", "&#60;", "&amp;", or a legacy name without ";" such as "&copy"). A lone "&", as in "P&L", is fine. A translation that needs markup must be rendered only through sanitizeHtml() and listed in SANITIZED_MARKUP_KEYS — item 10.';

        expect(offenders, ['', rule, `${offenders.length} translation(s) with markup:`, '', ...offenders, ''].join('\n  ')).toEqual([]);
    });

    it('keeps the reviewed sanitized keys current and explained', () => {
        const {stale} = catalogMarkupFindings(readCatalogs(), new Set(SANITIZED_MARKUP_KEYS.map((entry) => entry.key)));
        expect(stale, ['', 'Reviewed sanitized keys that no catalog marks up any more — delete them:', '', ...stale, ''].join('\n  ')).toEqual([]);
        expect(SANITIZED_MARKUP_KEYS.filter((entry) => entry.why.trim().length < 20).map((entry) => entry.key)).toEqual([]);
    });
});
