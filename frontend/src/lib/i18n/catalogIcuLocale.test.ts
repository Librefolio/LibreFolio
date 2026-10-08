// @vitest-environment node
/**
 * catalogIcuLocale — no locale-sensitive ICU message is byte-identical in two catalogues (Vitest, node).
 *
 * Why. svelte-i18n 4.0.1 compiles a message with `getMessageFormatter(message, locale)`, memoized by
 * `monadicMemoize` (`node_modules/svelte-i18n/dist/runtime.js`). The memo passes on only one
 * argument, so the cache key is the message text and the locale never reaches the cache. The first
 * compile of a text uses the locale current at that moment, and every later locale reuses that
 * formatter. The app switches locale in place (the language selector, the preferences tab, the
 * welcome page, the locale restored after login), so a text byte-identical in two catalogues is
 * rendered in the second language with the rules of the first. For a plain text, or one whose
 * arguments are only substituted (`{name}`, a `select`), the locale changes nothing. For a `plural`
 * or a `selectordinal` (the CLDR plural rules, and the number format of its `#`), a `number`, a
 * `date` or a `time`, the locale changes what the user reads: 0 and 1.5 select `one` in French and
 * `other` in English.
 *
 * Gate. The four catalogues are flattened to dotted keys, and their messages are grouped by exact
 * text across all keys, because the cache does not know keys. A text found in two or more locales
 * that holds a locale-sensitive element is an offender, listed with each key and its locales.
 * Sensitivity is read from the runtime's own parse, never from a regex over the text: the class
 * `getMessageFormatter` instantiates, with the svelte-i18n `ignoreTag`, walked at any depth for a
 * plural (cardinal or ordinal), a `#`, a number, a date or a time. The parser produces a `#` only
 * inside a plural; anywhere else it is literal text (`#{id}`). If the runtime cannot compile a text,
 * the gate fails with the reason instead of guessing a classification.
 *
 * Expected. Red today with three keys, each byte-identical in EN and FR:
 * `importWizard.reportSet.gapFix.positions`, `importWizard.reportSet.gapFix.corrections` and
 * `tools.pacAllocator.planner.review.sources`. The fix makes the FR texts differ (a CLDR `many`
 * branch), and the gate is green after it.
 *
 * Controls. The AST types are read from the runtime and are distinct. The selector is proved in both
 * halves on synthetic catalogues. These pass: a plain text, a brand name, a simple `{name}`, a
 * `select` and a literal `#` shared by every locale, and one plural at two keys of a single locale.
 * These are flagged, with their keys and locales: a plural, a `{n, number}`, a selectordinal, a date,
 * a time and a plural nested in a select shared by two locales, and one plural at two different
 * keys of two locales. On the real catalogues the walk is not vacuous: every catalogue holds
 * locale-sensitive messages, and the locales do share texts.
 *
 * Latch. A characterization test, green by design. Across the app's in-place switch,
 * `getMessageFormatter(m, 'en')` then `getMessageFormatter(m, 'fr')` return the same instance,
 * compiled for English. This pins the library behaviour the gate protects against. Its controls show
 * that a first compile does take the current locale, and that the cache does tell two messages
 * apart. When an upgrade adds the locale to the cache key, the latch turns red: that is the signal to
 * revisit the gate, which may then guard something the runtime already guarantees.
 *
 * Arguments. The last describe guards the calls rather than the catalogues. svelte-i18n formats a
 * message only when every argument it names has a value; otherwise `formatMessage` catches the
 * formatter's error and returns the raw text, so `count` passed to `{n} event(s) deleted` shows
 * «{n} event(s) deleted». The calls are read through `svelte/compiler`'s own parse, never a regex (a
 * regex scan had 23 false positives on 31 hits): every `.svelte` file under `src/`, listed at run
 * time with the harnesses of `src/__tests__/` aside, is walked whole, both scripts and every template
 * expression. Each `$t(...)` or `$_(...)` whose key is a string literal and whose `values` is an
 * object literal is recorded with its line and the names it passes. A spread or a computed key, in
 * the `values` or in the options around them, hides or may replace a name: that call is skipped and
 * counted, and the gate's message lists it. A key that is not a literal is not recorded. Each call is
 * checked against every catalogue that has its key as a string. A message needs the names of its
 * arguments, numbers, dates, times, selects and plurals, at any depth, read from the runtime parse
 * above: a `#` names nothing, and with `ignoreTag` a tag is text. It was written red with eight calls that
 * passed `count` where all four catalogues say `{n}`: `events.deleteSuccess`, `events.deleteBlocked`,
 * `fx.delete.resultDeleted`, `uploads.uploadBatchSucceeded`, `uploads.deleteFailedSome`,
 * `uploads.deleteBatchSucceeded`, `uploads.confirmBulkDelete.message` and
 * `assets.distribution.deleteConfirmMessage`. The fix passed the name the catalogues use, and the gate
 * has been green since. The controls run a synthetic component and synthetic catalogues through the same
 * walk and check. Flagged: `{count}` for `{n}`, a name needed only inside plural branches, a select
 * missing in one locale. Passing: exact names, extra names, a plural with its own argument, shorthand,
 * a multi-line call with template literals and nested calls. On the real tree every component parses,
 * hundreds of calls are recorded in `src/lib` and `src/routes`, and a known-good call passes. Not
 * read: a key or a `values` built at run time, a `default` text, a call through `get(t)` or `get(_)`,
 * and calls from `.ts` modules.
 */
import {afterEach, describe, expect, it} from 'vitest';
import {getMessageFormatter, locale} from 'svelte-i18n';
import {readdirSync, readFileSync} from 'node:fs';
import {join, relative} from 'node:path';
import {fileURLToPath} from 'node:url';
import {parse as parseSvelte} from 'svelte/compiler';
import type {SupportedLocale} from './index';
import en from './en.json';
import itCatalogue from './it.json';
import fr from './fr.json';
import es from './es.json';

/** Typed on the app's locale list, so a fifth locale without a catalogue here fails `front check`. */
const CATALOGUES: Record<SupportedLocale, unknown> = {en, it: itCatalogue, fr, es};

type RuntimeFormatter = ReturnType<typeof getMessageFormatter>;
type Ast = ReturnType<RuntimeFormatter['getAst']>;
type AstElement = Ast[number];

/** The class `getMessageFormatter` instantiates, read from one of its formatters rather than imported beside it. */
type RuntimeFormatterClass = new (message: string, locales?: string, overrideFormats?: undefined, options?: {ignoreTag?: boolean}) => RuntimeFormatter;
const RuntimeMessageFormat = getMessageFormatter('text').constructor as unknown as RuntimeFormatterClass;

/** A message as the runtime parses it: its class, with the svelte-i18n default `ignoreTag`, which the app keeps. */
function parse(message: string): Ast {
    try {
        return new RuntimeMessageFormat(message, 'en', undefined, {ignoreTag: true}).getAst();
    } catch (error) {
        throw new Error(`the runtime cannot compile ${JSON.stringify(message)}: ${error instanceof Error ? error.message : String(error)}`);
    }
}

/** Every element of an AST, at any depth: the options of a plural or a select, the children of a tag. */
function elementsOf(ast: Ast): AstElement[] {
    return ast.flatMap((element) => {
        const options = 'options' in element ? Object.values(element.options).flatMap((option) => elementsOf(option.value)) : [];
        const children = 'children' in element ? elementsOf(element.children) : [];
        return [element, ...options, ...children];
    });
}

/** The type of the first element of a message, as the runtime parses it. */
function firstType(message: string): AstElement['type'] | undefined {
    return parse(message)[0]?.type;
}

// Read from parses rather than imported: the `TYPE` enum lives in another transitive package.
const LITERAL_TYPE = firstType('text');
const ARGUMENT_TYPE = firstType('{name}');
const SELECT_TYPE = firstType('{g, select, other {x}}');
const PLURAL_PROBE = parse('{n, plural, other {#}}')[0];
const PLURAL_TYPE = PLURAL_PROBE?.type;
const POUND_TYPE = PLURAL_PROBE !== undefined && 'options' in PLURAL_PROBE ? PLURAL_PROBE.options.other?.value[0]?.type : undefined;
const NUMBER_TYPE = firstType('{n, number}');
const DATE_TYPE = firstType('{d, date}');
const TIME_TYPE = firstType('{t, time}');

/** What the locale of a compile changes: the plural rules (cardinal and ordinal) and the number format of `#`; number, date and time formats. */
const LOCALE_SENSITIVE = new Set([PLURAL_TYPE, POUND_TYPE, NUMBER_TYPE, DATE_TYPE, TIME_TYPE]);

/** Whether the locale of the compile changes what a message renders. */
function isLocaleSensitive(message: string): boolean {
    return elementsOf(parse(message)).some((element) => LOCALE_SENSITIVE.has(element.type));
}

/** Every message of a catalogue, by dotted key. A leaf that is neither a message nor a subtree is an error, never skipped. */
function messagesOf(node: unknown, prefix = ''): [string, string][] {
    if (typeof node === 'string') return [[prefix, node]];
    if (node === null || typeof node !== 'object' || Array.isArray(node)) throw new Error(`${prefix || 'the catalogue'}: neither a message nor a subtree`);
    return Object.entries(node).flatMap(([name, child]) => messagesOf(child, prefix === '' ? name : `${prefix}.${name}`));
}

/** One place of a text: the locale of its catalogue and its key there. */
interface Place {
    code: string;
    key: string;
}

/** The texts found in two or more locales, at any key, each with every place it is found. */
function sharedTexts(catalogues: Record<string, unknown>): Map<string, Place[]> {
    const places = new Map<string, Place[]>();
    for (const [code, catalogue] of Object.entries(catalogues)) {
        for (const [key, text] of messagesOf(catalogue)) {
            const found = places.get(text) ?? [];
            found.push({code, key});
            places.set(text, found);
        }
    }
    return new Map([...places].filter(([, found]) => new Set(found.map((place) => place.code)).size > 1));
}

/** One line per offending text, sorted: each key with its locales, then the text. */
function offenders(catalogues: Record<string, unknown>): string[] {
    const lines: string[] = [];
    for (const [text, found] of sharedTexts(catalogues)) {
        if (!isLocaleSensitive(text)) continue;
        const codesByKey = new Map<string, string[]>();
        for (const {code, key} of found) codesByKey.set(key, [...(codesByKey.get(key) ?? []), code]);
        lines.push(`${[...codesByKey].map(([key, codes]) => `${key} [${codes.join(', ')}]`).join(' = ')}: ${JSON.stringify(text)}`);
    }
    return lines.sort();
}

describe('catalogues — no locale-sensitive ICU message is byte-identical in two locales', () => {
    it('control: the AST types are read from the runtime, eight distinct ones, and a selectordinal is a plural', () => {
        const types = [LITERAL_TYPE, ARGUMENT_TYPE, SELECT_TYPE, PLURAL_TYPE, POUND_TYPE, NUMBER_TYPE, DATE_TYPE, TIME_TYPE];
        expect(types).not.toContain(undefined);
        expect(new Set(types).size).toBe(types.length);
        expect(firstType('{n, selectordinal, other {#}}'), 'an ordinal plural has the plural type').toBe(PLURAL_TYPE);
    });

    it('control: plain texts shared by every locale pass — a word, a brand name, simple arguments, a select, a literal #', () => {
        const plain = {ok: 'OK', brand: 'LibreFolio', name: '{name}', arguments: 'A {name} B {count}', choice: '{g, select, a {A} other {B}}', reference: '#{id}'};
        const catalogues = {en: plain, it: plain, fr: plain, es: plain};
        // They are shared, so passing is the selector's verdict and not a missed grouping.
        expect([...sharedTexts(catalogues).keys()].sort(), 'control: every text is shared').toEqual(Object.values(plain).sort());
        expect(offenders(catalogues)).toEqual([]);
    });

    it('control: one locale-sensitive text at two keys of a single locale passes — one locale, one set of rules', () => {
        const plural = '{n, plural, one {A} other {B}}';
        expect(offenders({en: {a: plural, b: plural}, fr: {a: 'A {n}', b: 'B {n}'}})).toEqual([]);
    });

    it('control: a locale-sensitive text shared by two locales is flagged, with its key and its locales', () => {
        const sensitive = {
            plural: '{n, plural, one {# A} other {# B}}',
            number: 'A {n, number}',
            ordinal: '{n, selectordinal, one {#A} other {#B}}',
            date: 'A {d, date, short}',
            time: 'A {t, time, short}',
            nested: '{g, select, other {{n, plural, one {A} other {B}}}}',
        };
        const expected = Object.entries(sensitive)
            .map(([key, text]) => `${key} [en, fr]: ${JSON.stringify(text)}`)
            .sort();
        // Italian has its own text at one of the keys, Spanish has none: neither is listed.
        expect(offenders({en: sensitive, it: {plural: 'IT'}, fr: sensitive, es: {}})).toEqual(expected);
    });

    it('control: the cache does not know keys — one text at two keys of two locales is flagged with both', () => {
        const plural = '{n, plural, one {A} other {B}}';
        expect(offenders({en: {a: {b: plural}}, es: {c: plural}})).toEqual([`a.b [en] = c [es]: ${JSON.stringify(plural)}`]);
    });

    it('control: the walk is not vacuous — every catalogue holds locale-sensitive messages, and the locales share texts', () => {
        for (const [code, catalogue] of Object.entries(CATALOGUES)) {
            const sensitive = messagesOf(catalogue).filter(([, text]) => isLocaleSensitive(text));
            expect(sensitive.length, `${code}: locale-sensitive messages`).toBeGreaterThan(0);
        }
        expect(sharedTexts(CATALOGUES).size, 'texts shared by two or more locales').toBeGreaterThan(0);
    });

    it('no locale-sensitive text is byte-identical in two locales', () => {
        expect(offenders(CATALOGUES), 'svelte-i18n compiles each of these once, with the locale of the first caller: make the texts differ').toEqual([]);
    });
});

/** A plural message that no other test compiles: the formatter cache lives as long as this file's module graph. */
function latchMessage(name: string): string {
    return `{n, plural, one {ONE} other {OTHER}} catalogIcuLocale:${name}`;
}

describe('svelte-i18n — getMessageFormatter caches on the message alone (characterization latch, green by design)', () => {
    afterEach(async () => {
        // The current locale is module-level state of the runtime.
        await locale.set(null);
    });

    it('a message compiled in English is returned unchanged after an in-place switch to French', async () => {
        const message = latchMessage('switch');
        await locale.set('en');
        const english = getMessageFormatter(message, 'en');
        await locale.set('fr');
        const french = getMessageFormatter(message, 'fr');
        expect(french, 'the same instance: the locale is not part of the cache key').toBe(english);
        expect(french.resolvedOptions().locale, 'so French formats with the locale of the first compile').toBe('en');
        expect(french.format({n: 0}), 'and 0 selects the EN other, where the FR rules select one').toBe('OTHER catalogIcuLocale:switch');
    });

    it('control: a first compile takes the current locale, so the English above comes from the cache, not from a runtime stuck in English', async () => {
        const message = latchMessage('first');
        await locale.set('fr');
        const french = getMessageFormatter(message, 'fr');
        expect(french.resolvedOptions().locale).toBe('fr');
        expect(french.format({n: 0}), 'the FR rules select one at 0').toBe('ONE catalogIcuLocale:first');
    });

    it('control: the cache tells two messages apart, so the same instance above is not one formatter for everything', async () => {
        await locale.set('en');
        expect(getMessageFormatter(latchMessage('a'), 'en')).not.toBe(getMessageFormatter(latchMessage('b'), 'en'));
    });
});

/** The element types that name a value the caller must pass. A `#` and a literal name none; with `ignoreTag`, a tag is text. */
const NAMED_TYPES = new Set([ARGUMENT_TYPE, NUMBER_TYPE, DATE_TYPE, TIME_TYPE, SELECT_TYPE, PLURAL_TYPE]);

/** The names a message needs a value for, at any depth, sorted. The formatter throws at the first one missing. */
function argumentsOf(message: string): string[] {
    const names = elementsOf(parse(message)).flatMap((element) => (NAMED_TYPES.has(element.type) && 'value' in element ? [element.value] : []));
    return [...new Set(names)].sort();
}

/** `frontend/`: the place of a call is reported from it, as `src/…`. */
const FRONTEND = fileURLToPath(new URL('../../../', import.meta.url));

/** The test harnesses: components written for tests, not product. */
const HARNESSES = join(FRONTEND, 'src', '__tests__');

/** Every `.svelte` file under `src/`, listed from the disk at each run, the harnesses aside. */
function svelteFiles(dir: string = join(FRONTEND, 'src')): string[] {
    return readdirSync(dir, {withFileTypes: true}).flatMap((entry) => {
        const path = join(dir, entry.name);
        if (entry.isDirectory()) return path === HARNESSES ? [] : svelteFiles(path);
        return entry.isFile() && entry.name.endsWith('.svelte') ? [path] : [];
    });
}

/** A node of the compiler's tree, Svelte's or ESTree, read without its types: only `type` and the fields named are used. */
type SourceNode = {type: string; [field: string]: unknown};

function isSourceNode(value: unknown): value is SourceNode {
    return value !== null && typeof value === 'object' && typeof (value as {type?: unknown}).type === 'string';
}

/** Every node of a tree, at any depth: an explicit stack and a visited set, so a shared reference is read once. */
function sourceNodes(root: unknown): SourceNode[] {
    const nodes: SourceNode[] = [];
    const visited = new Set<object>();
    const pending: unknown[] = [root];
    while (pending.length > 0) {
        const value = pending.pop();
        if (value === null || typeof value !== 'object' || visited.has(value)) continue;
        visited.add(value);
        if (isSourceNode(value)) nodes.push(value);
        for (const child of Array.isArray(value) ? value : Object.values(value)) pending.push(child);
    }
    return nodes;
}

/** The name a property of an object literal gives, as JavaScript reads it: an identifier, or a literal as text. None for a spread or a computed key. */
function propertyName(property: unknown): string | undefined {
    if (!isSourceNode(property) || property.type !== 'Property' || property.computed === true || !isSourceNode(property.key)) return undefined;
    const {type, name, value} = property.key;
    if (type === 'Identifier') return typeof name === 'string' ? name : undefined;
    return type === 'Literal' ? String(value) : undefined;
}

/** The names of an object literal, in source order; `null` when a spread or a computed key hides one. */
function namesOf(object: SourceNode): string[] | null {
    const names = (Array.isArray(object.properties) ? object.properties : []).map(propertyName);
    return names.every((name): name is string => name !== undefined) ? names : null;
}

/** A `$t(...)` or `$_(...)` with a literal key and a literal `values`: its place, its key, and the names it passes, in source order. */
interface IcuCall {
    file: string;
    line: number;
    key: string;
    names: string[];
}

/** The calls of one source: those recorded, and those whose names cannot be read, as `file:line key`. */
interface SourceCalls {
    recorded: IcuCall[];
    unverifiable: string[];
}

/**
 * The calls of one component, in source order. A function of its own, so that a control goes through
 * exactly the parse and the walk a real file goes through.
 */
function icuCallsIn(file: string, source: string): SourceCalls {
    const found: {start: number; key: string; names: string[] | null}[] = [];
    for (const node of sourceNodes(parseSvelte(source, {modern: true}))) {
        const {type, start, callee, arguments: args} = node;
        if (type !== 'CallExpression' || typeof start !== 'number' || !isSourceNode(callee) || callee.type !== 'Identifier' || (callee.name !== '$t' && callee.name !== '$_')) continue;
        const [key, options]: unknown[] = Array.isArray(args) ? args : [];
        if (!isSourceNode(key) || key.type !== 'Literal' || typeof key.value !== 'string' || !isSourceNode(options) || options.type !== 'ObjectExpression') continue;
        const values = (Array.isArray(options.properties) ? options.properties : []).find((property) => propertyName(property) === 'values');
        if (!isSourceNode(values) || !isSourceNode(values.value) || values.value.type !== 'ObjectExpression') continue;
        // A spread or a computed key among the options may replace `values`: its names are then unknown too.
        found.push({start, key: key.value, names: namesOf(options) === null ? null : namesOf(values.value)});
    }
    // In source order: the tree lists the markup before the scripts.
    found.sort((left, right) => left.start - right.start);
    const lineOf = (offset: number): number => source.slice(0, offset).split('\n').length;
    return {
        recorded: found.flatMap(({start, key, names}) => (names === null ? [] : [{file, line: lineOf(start), key, names}])),
        unverifiable: found.flatMap(({start, key, names}) => (names === null ? [`${file}:${lineOf(start)} ${key}`] : [])),
    };
}

/** What the walk read on the real tree: the components, the calls, and the files the compiler refused, with its reason. */
interface TreeScan {
    files: number;
    recorded: IcuCall[];
    unverifiable: string[];
    unreadable: string[];
}

/** Parsing every component takes seconds, so the tree is read once and shared by the tests that need it. */
let treeScan: TreeScan | undefined;

function scanTree(): TreeScan {
    if (treeScan !== undefined) return treeScan;
    const scan: TreeScan = {files: 0, recorded: [], unverifiable: [], unreadable: []};
    for (const path of svelteFiles().sort()) {
        const file = relative(FRONTEND, path).replaceAll('\\', '/');
        scan.files += 1;
        try {
            const calls = icuCallsIn(file, readFileSync(path, 'utf8'));
            scan.recorded.push(...calls.recorded);
            scan.unverifiable.push(...calls.unverifiable);
        } catch (error) {
            // Reported, never skipped: the calls of a file the compiler refuses would go unchecked.
            scan.unreadable.push(`${file}: ${error instanceof Error ? error.message : String(error)}`);
        }
    }
    treeScan = scan;
    return scan;
}

/** A ceiling, not a wait: the first test to read the tree parses every component, which can exceed the 5 s default on a busy runner. */
const SCAN_TIMEOUT = 60_000;

/**
 * One line per call that misses a name some catalogue's message needs: its place and key, the locales
 * grouped by the names they need, and the names the code passes. A catalogue without the key as a
 * string has nothing to say about the call.
 */
function argumentOffenders(calls: readonly IcuCall[], catalogues: Record<string, unknown>): string[] {
    const locales = Object.entries(catalogues).map(([code, catalogue]) => ({code, messages: new Map(messagesOf(catalogue))}));
    return calls.flatMap((call) => {
        const codesByNeed = new Map<string, string[]>();
        for (const {code, messages} of locales) {
            const message = messages.get(call.key);
            if (message === undefined) continue;
            const needed = argumentsOf(message);
            if (needed.every((name) => call.names.includes(name))) continue;
            const need = `{${needed.join(', ')}}`;
            codesByNeed.set(need, [...(codesByNeed.get(need) ?? []), code]);
        }
        const needs = [...codesByNeed].map(([need, codes]) => `${codes.join(', ')} ${codes.length > 1 ? 'need' : 'needs'} ${need}`);
        return needs.length === 0 ? [] : [`${call.file}:${call.line} ${call.key} — ${needs.join('; ')}, the code passes {${[...call.names].sort().join(', ')}}`];
    });
}

/**
 * A component written for the controls. Its module script could not read a store, but the parser
 * accepts the call there, and that proves the walk reads that script too.
 */
const SYNTHETIC_COMPONENT = [
    '<script module lang="ts">',
    "    export const heading = $t('items', {values: {count: 1}});",
    '</script>',
    '',
    '<script lang="ts">',
    '    let {rows, user, kind, name, rest, options} = $props();',
    '    const n = rows.length;',
    "    const branch = $t('branch', {values: {c: n}});",
    "    const choice = $_('choice', {values: {n}});",
    "    const exact = $t('items', {values: {n}});",
    "    const extra = $t('items', {values: {n, unused: n}});",
    "    const plural = $t('plural', {values: {count: n}});",
    "    const spread = $t('items', {values: {...rest}});",
    "    const computed = $t('items', {values: {[name]: n}});",
    "    const replaced = $t('items', {values: {n}, ...options});",
    '    const dynamic = $t(`items.${kind}`, {values: {count: n}});',
    '</script>',
    '',
    "<p title={$t('items', {values: {count: 2}})}>",
    "    {$t('summary', {",
    '        values: {',
    '            who: `${user.first} ${user.last}`,',
    "            what: $_('items', {values: {n: rows.filter((row) => row.ok).length}}),",
    '            total: sum(rows.map((row) => ({amount: row.amount}))),',
    '        },',
    '    })}',
    '</p>',
].join('\n');

/** Catalogues written for the controls: French needs a select that English does not, Spanish has a single key. */
const SYNTHETIC_EN = {
    items: '{n} items',
    branch: '{c, plural, one {{name} has #} other {{name} has #}}',
    choice: 'Sent {n}',
    plural: '{count, plural, one {# row} other {# rows}}',
    summary: '{who} bought {what} for {total}',
};
const SYNTHETIC_CATALOGUES = {en: SYNTHETIC_EN, fr: {...SYNTHETIC_EN, choice: '{g, select, female {Elle a} other {Il a}} envoyé {n}'}, es: {items: '{n} artículos'}};

describe('$t and $_ calls — every ICU argument a message uses is passed, in every catalogue', () => {
    it('control: a message needs the names of its arguments, numbers, dates, times, selects and plurals, at any depth; never of a #, a literal or a quoted brace', () => {
        expect(argumentsOf('{who} paid {sum, number} on {day, date, short} at {hour, time, short}, {place, selectordinal, one {#st} other {#th}}')).toEqual(['day', 'hour', 'place', 'sum', 'who']);
        expect(argumentsOf('{g, select, female {{n, plural, one {# {unit}} other {# {units}}}} other {{name}}}')).toEqual(['g', 'n', 'name', 'unit', 'units']);
        expect(argumentsOf("#{id}, <b>{name}</b>, '{quoted}' and 100%")).toEqual(['id', 'name']);
    });

    it('control: the walk records each call with a literal key and literal values, in the module script, the instance script and the markup, at its line, with the names it passes', () => {
        const {recorded} = icuCallsIn('Synthetic.svelte', SYNTHETIC_COMPONENT);
        expect(recorded.map(({line, key, names}) => ({line, key, names}))).toEqual([
            {line: 2, key: 'items', names: ['count']},
            {line: 8, key: 'branch', names: ['c']},
            {line: 9, key: 'choice', names: ['n']},
            {line: 10, key: 'items', names: ['n']},
            {line: 11, key: 'items', names: ['n', 'unused']},
            {line: 12, key: 'plural', names: ['count']},
            {line: 19, key: 'items', names: ['count']},
            {line: 20, key: 'summary', names: ['who', 'what', 'total']},
            {line: 23, key: 'items', names: ['n']},
        ]);
    });

    it('control: a spread or a computed key that hides the names is skipped and counted, never read as fewer names; a template-literal key is not recorded at all', () => {
        const {recorded, unverifiable} = icuCallsIn('Synthetic.svelte', SYNTHETIC_COMPONENT);
        expect(unverifiable).toEqual(['Synthetic.svelte:13 items', 'Synthetic.svelte:14 items', 'Synthetic.svelte:15 items']);
        expect(
            recorded.map((call) => call.line).filter((line) => line >= 13 && line <= 16),
            'neither the skipped calls nor the template-literal key',
        ).toEqual([]);
    });

    it('control: flagged, with the locales that need more — {count} for {n}, a name needed only inside plural branches, a select missing in one locale; in a script and in the markup', () => {
        expect(argumentOffenders(icuCallsIn('Synthetic.svelte', SYNTHETIC_COMPONENT).recorded, SYNTHETIC_CATALOGUES)).toEqual([
            'Synthetic.svelte:2 items — en, fr, es need {n}, the code passes {count}',
            'Synthetic.svelte:8 branch — en, fr need {c, name}, the code passes {c}',
            'Synthetic.svelte:9 choice — fr needs {g, n}, the code passes {n}',
            'Synthetic.svelte:19 items — en, fr, es need {n}, the code passes {count}',
        ]);
    });

    it('control: passing — exact names, extra names, a plural with its own argument, shorthand, a multi-line call with template literals and nested calls in its values', () => {
        const passing = icuCallsIn('Synthetic.svelte', SYNTHETIC_COMPONENT).recorded.filter((call) => [10, 11, 12, 20, 23].includes(call.line));
        // Recorded first, so passing is the check's verdict and not a call the walk missed.
        expect(passing.map(({line, key}) => `${line} ${key}`)).toEqual(['10 items', '11 items', '12 plural', '20 summary', '23 items']);
        expect(argumentOffenders(passing, SYNTHETIC_CATALOGUES)).toEqual([]);
    });

    it(
        'control: the walk is not vacuous — every component under src/ parses, hundreds of calls are recorded in src/lib and src/routes, and a known-good call passes',
        () => {
            const {files, recorded, unreadable} = scanTree();
            expect(files, 'components read: the walk reads the wrong directory').toBeGreaterThan(200);
            expect(unreadable, 'components the compiler refused: their calls would go unchecked').toEqual([]);
            // 347 when written, 136 in scripts and 211 in markup: a walk that loses either half falls below.
            expect(recorded.length, 'calls with a literal key and literal values').toBeGreaterThanOrEqual(250);
            expect([...new Set(recorded.map((call) => call.file.split('/').slice(0, 2).join('/')))], 'calls in the components and in the pages').toEqual(expect.arrayContaining(['src/lib', 'src/routes']));
            // Keyed by file and key, never by line. It passes `count`, the name its catalogues use: the gate is about names, not about `count`.
            const known = recorded.filter((call) => call.file === 'src/lib/components/risk/levels/l4/L4Replay.svelte' && call.key === 'risk.levels.l4.replaySuggested');
            expect(
                known.map((call) => [...call.names].sort()),
                'the known-good call is recorded with the names it passes',
            ).toEqual([['count', 'end', 'start']]);
            expect(argumentOffenders(known, CATALOGUES), 'and it passes in every catalogue').toEqual([]);
        },
        SCAN_TIMEOUT,
    );

    it(
        'every $t/$_ call with a literal key and literal values passes each name its message uses, in every catalogue',
        () => {
            const {recorded, unverifiable} = scanTree();
            const skipped = unverifiable.length === 0 ? 'none skipped' : `${unverifiable.length} skipped, a spread or a computed key hiding their names: ${unverifiable.join(', ')}`;
            expect(
                argumentOffenders(recorded, CATALOGUES),
                `svelte-i18n formats a message only when every argument it names has a value, and otherwise shows the raw text: pass the name the catalogues use, or change the catalogues with ./dev.py i18n update (${recorded.length} calls checked, ${skipped})`,
            ).toEqual([]);
        },
        SCAN_TIMEOUT,
    );
});
