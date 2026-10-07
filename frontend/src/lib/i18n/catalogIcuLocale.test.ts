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
 */
import {afterEach, describe, expect, it} from 'vitest';
import {getMessageFormatter, locale} from 'svelte-i18n';
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
