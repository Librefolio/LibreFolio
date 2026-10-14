// @vitest-environment node
/**
 * text — the plural sites of the result sentences, and the catalogue behind them (Vitest, node).
 *
 * Subject (R7). Six catalogue keys, at seven call sites, put a noun after a quantity: `buyUnits`
 * (`instructionText`), `stepUnits` (`instructionStepText`), `pricePer` (`priceText`, when the quote
 * base is not one unit), `units` (`routeMinimumText` and `routeCapText`), and the two economic
 * quantities of an order, `quantityExact` and `quantityEstimated`. R7 moves those two from inline
 * `$t` calls of `OrderDetail.svelte` (:55-59) into `economicQuantityText`. Each message becomes
 * `{count, plural, one {…} other {…}}`, and each call passes, next to the figure it already
 * formats, the plural `count` of that same value: `plannerQuantityCount`, `exactQuantityCount` or
 * `plannerPlainDecimalCount`, the twins of the display functions (`format.test.ts` pins them).
 *
 * Wiring. A recording translator stands in for `$t`. Each site must make exactly one call, at its
 * key, carrying the values the formatter gives for the value it shows (the figure and its count,
 * nothing else), and return the translator's answer. The expected values come from the same
 * formatter functions, so literal anchors keep the check from being circular: `'1'` is shown as
 * `1` and counts 1, `'2'` counts 2, `'1.5'` counts 1.5. A quote base of one unit makes no call.
 *
 * Privacy. Quantities, route caps and route minimums are wealth (`personal`). With privacy on the
 * figure is the placeholder (`≈` stays outside it on an approximate ratio) and the count is NaN,
 * which ICU selects as `other`: a singular next to a masked figure would reveal a hidden 1. An
 * order step and a quote base are public: their figure and their count stay in the clear.
 *
 * Catalogue (P-d). Every EN fallback of these calls must equal the `en.json` message at its key,
 * and a key with no message is a failure, not a skip. The check compares two sources and never
 * spells a sentence itself.
 *
 * ICU. For the six keys, in the four catalogues, the message compiles with the runtime's own
 * compiler (`getMessageFormatter`, what `$t` calls) and holds exactly one cardinal plural, on
 * `count`, with the options `one` and `other` and no `#`: the count stands for the figure shown and
 * is never printed. It asks for the same arguments as EN. Selection is read through the rendered
 * text, never through its words: NaN and 1 000 000 render like 2 everywhere (the CLDR `many` of
 * fr/it/es falls back to `other`); 1.5, 0.5 and 0 render like 2 in en/it/es and like 1 in fr,
 * whose singular is an integer part of 0 or 1; and only EN must tell 1 from 2, since another
 * language may have an invariable noun.
 *
 * Locale. `getMessageFormatter(message, locale)` caches on the message alone: its memo forwards a
 * single argument, so the locale is dropped and the first compile of a text fixes its plural rules
 * for every later caller. Selection is therefore read from formatters built with the runtime's own
 * class (the constructor of what `getMessageFormatter` returns) and an explicit locale, controlled
 * through `resolvedOptions()`. For the app the same cache means that a message byte-identical in
 * two catalogues is compiled once, with the plural rules of whichever locale came first.
 *
 * Distribution dialog. The two Dashboard help texts of `DistributionDialog.svelte`
 * (`distribution.differs`, `distribution.source`) change in R7 too. Their fallbacks are read from
 * the component source, every `$t('<key>', {default: '…'})`, and must equal `en.json`.
 *
 * Environment. The formatter graph imports the currency catalogue store, which imports the API
 * client: the client is inert, so a price keeps its bare currency code. The shared
 * `$app/environment` mock reports `browser: false`, so the privacy flag never touches
 * `localStorage`.
 */
import {afterEach, describe, expect, it, vi} from 'vitest';

// The sentences format through the planner's formatter, which reads the currency catalogue store,
// which imports the API client. Nothing here loads the catalogue: every call resolves to nothing.
vi.mock('$lib/api', () => ({
    zodiosApi: new Proxy({}, {get: () => vi.fn(async () => undefined)}),
}));

import {getMessageFormatter} from 'svelte-i18n';
import {SUPPORTED_LOCALES, type SupportedLocale} from '$lib/i18n';
import en from '$lib/i18n/en.json';
import itCatalogue from '$lib/i18n/it.json';
import fr from '$lib/i18n/fr.json';
import es from '$lib/i18n/es.json';
import {isPrivacyEnabled, setPrivacyEnabled} from '$lib/stores/app/privacyStore.svelte';
import {PRIVACY_PLACEHOLDER} from '$lib/utils/privacy/maskable';
import {catalogCurrencyDigits, exactQuantityCount, formatExactPricePlain, formatExactQuantity, formatPlannerPlainDecimal, formatPlannerQuantity, plannerPlainDecimalCount, plannerQuantityCount} from '../format';
import type {PacExactNumber, PacExactPrice, PacOrderRow, PacResolvedOrderRoute} from '../types';
import {economicQuantityText, instructionStepText, instructionText, priceText, routeCapText, routeMinimumText, type Translator} from './text';

const KEY = 'tools.pacAllocator.planner.result.text';
const DETAIL_KEY = 'tools.pacAllocator.planner.result.detail';
const MASK = PRIVACY_PLACEHOLDER;

/** The six plural keys, each with the arguments it asks for, sorted: in EN and in every locale. */
const PLURAL_KEYS: Record<string, string[]> = {
    [`${KEY}.buyUnits`]: ['count', 'quantity'],
    [`${KEY}.stepUnits`]: ['count', 'step'],
    [`${KEY}.pricePer`]: ['count', 'price', 'quantity'],
    [`${KEY}.units`]: ['count', 'quantity'],
    [`${DETAIL_KEY}.quantityExact`]: ['count', 'quantity'],
    [`${DETAIL_KEY}.quantityEstimated`]: ['count', 'quantity'],
};

/** Typed on the app's locale list, so a fifth locale without a catalogue here fails `front check`. */
const CATALOGUES: Record<SupportedLocale, unknown> = {en, it: itCatalogue, fr, es};

const digits = catalogCurrencyDigits([{currency: 'EUR', minor_unit: '0.01'}]);

/** A 21st fraction digit: the display truncates it, so the user sees 1. */
const TWENTY_ONE_DIGIT_ONE = '1.' + '0'.repeat(20) + '1';

/** Moves the flag, and proves it moved. */
function privacy(on: boolean): void {
    setPrivacyEnabled(on);
    expect(isPrivacyEnabled(), 'control: the flag').toBe(on);
}

afterEach(() => {
    // The flag is module-level state shared by every test in this file.
    setPrivacyEnabled(false);
});

type ExactRatio = Extract<PacExactNumber, {kind: 'exact_ratio'}>;
type EconomicQuantity = PacOrderRow['economic_quantity'];
type RouteMinimum = PacResolvedOrderRoute['required_minimum'];
type RouteCap = PacResolvedOrderRoute['cap'];

function finite(value: string): PacExactNumber {
    return {kind: 'finite_decimal', value};
}

/** An exact ratio as the backend sends it. The display projection is not authoritative. */
function ratio(numerator: string, denominator: string, display_decimal: string, display_scale = 6): ExactRatio {
    return {kind: 'exact_ratio', numerator, denominator, display_decimal, display_scale, display_authority: 'non_authoritative'};
}

/** Only what the sentences read of an order: its instruction. */
function wholeQuantityOrder(quantity: string, quantity_step = '1'): PacOrderRow {
    const row: Pick<PacOrderRow, 'instruction'> = {instruction: {kind: 'whole_quantity', quantity, quantity_step, unit: 'asset_unit'}};
    return row as PacOrderRow;
}

/** A market price of 12.5 EUR for `quote_base_quantity` units. */
function price(quote_base_quantity: string): PacExactPrice {
    return {currency: 'EUR', quantity_unit: 'asset_unit', quote_base_quantity, value: finite('12.5')};
}

function wholeMinimum(quantity: string): RouteMinimum {
    return {kind: 'whole_quantity', quantity, unit: 'asset_unit'};
}

function quantityCap(quantity: string): RouteCap {
    return {kind: 'quantity', quantity, unit: 'asset_unit'};
}

function exactEconomic(value: PacExactNumber): EconomicQuantity {
    return {kind: 'exact', unit: 'asset_unit', value};
}

function estimatedEconomic(value: ExactRatio): EconomicQuantity {
    return {kind: 'estimated_exact_ratio', unit: 'asset_unit', value};
}

/** One call of the translator, as the site made it. */
interface TranslateCall {
    key: string;
    fallback: string | undefined;
    values: Record<string, unknown>;
}

/** What the recording translator answers: a sentence is the translator's answer, never a text built beside it. */
function answer(key: string): string {
    return `⟨${key}⟩`;
}

/** A translator that records every call and answers with the key it was asked for. */
function recorder(): {calls: TranslateCall[]; translate: Translator} {
    const calls: TranslateCall[] = [];
    const translate: Translator = (id, options) => {
        const message = typeof id === 'string' ? {id, ...options} : {...id, ...options};
        calls.push({key: message.id, fallback: message.default, values: {...message.values}});
        return answer(message.id);
    };
    return {calls, translate};
}

/** One site at one value: the call it must make. */
interface SiteCase {
    /** The call site, as reported. A site is met at several values. */
    site: string;
    key: string;
    sensitivity: 'personal' | 'public';
    /** The value that carries the figure: the quantity, or the step of an order step. */
    figure: 'quantity' | 'step';
    /** The value, as a title shows it. */
    input: string;
    /** Literal anchors, privacy off: the figure shown and its count. */
    shown: string;
    count: number;
    run(translate: Translator): string;
    /** The values the call must carry: the formatter's, for the value shown. Called only inside a test. */
    values(): Record<string, unknown>;
}

function buyUnits(quantity: string, shown: string, count: number): SiteCase {
    return {
        site: 'instructionText',
        key: `${KEY}.buyUnits`,
        sensitivity: 'personal',
        figure: 'quantity',
        input: quantity,
        shown,
        count,
        run: (translate) => instructionText(wholeQuantityOrder(quantity), translate, digits),
        values: () => ({quantity: formatPlannerQuantity(quantity), count: plannerQuantityCount(quantity)}),
    };
}

/** The order step is a Broker parameter, not wealth. */
function stepUnits(step: string, shown: string, count: number): SiteCase {
    return {
        site: 'instructionStepText',
        key: `${KEY}.stepUnits`,
        sensitivity: 'public',
        figure: 'step',
        input: step,
        shown,
        count,
        run: (translate) => instructionStepText(wholeQuantityOrder('3', step), translate, digits),
        values: () => ({step: formatPlannerPlainDecimal(step), count: plannerPlainDecimalCount(step)}),
    };
}

/** The quote base belongs to a market price: public. */
function pricePer(base: string, shown: string, count: number): SiteCase {
    return {
        site: 'priceText',
        key: `${KEY}.pricePer`,
        sensitivity: 'public',
        figure: 'quantity',
        input: base,
        shown,
        count,
        run: (translate) => priceText(price(base), translate, digits),
        values: () => ({price: formatExactPricePlain(price(base), digits), quantity: formatPlannerPlainDecimal(base), count: plannerPlainDecimalCount(base)}),
    };
}

function minimumUnits(quantity: string, shown: string, count: number): SiteCase {
    return {
        site: 'routeMinimumText',
        key: `${KEY}.units`,
        sensitivity: 'personal',
        figure: 'quantity',
        input: quantity,
        shown,
        count,
        run: (translate) => routeMinimumText(wholeMinimum(quantity), translate, digits),
        values: () => ({quantity: formatPlannerQuantity(quantity), count: plannerQuantityCount(quantity)}),
    };
}

function capUnits(quantity: string, shown: string, count: number): SiteCase {
    return {
        site: 'routeCapText',
        key: `${KEY}.units`,
        sensitivity: 'personal',
        figure: 'quantity',
        input: quantity,
        shown,
        count,
        run: (translate) => routeCapText(quantityCap(quantity), translate, digits),
        values: () => ({quantity: formatPlannerQuantity(quantity), count: plannerQuantityCount(quantity)}),
    };
}

/** An exact number as a title shows it: the decimal, or the ratio. */
function label(value: PacExactNumber): string {
    return value.kind === 'finite_decimal' ? value.value : `${value.numerator}/${value.denominator}`;
}

function quantityExact(value: PacExactNumber, shown: string, count: number): SiteCase {
    return {
        site: 'economicQuantityText, exact',
        key: `${DETAIL_KEY}.quantityExact`,
        sensitivity: 'personal',
        figure: 'quantity',
        input: label(value),
        shown,
        count,
        run: (translate) => economicQuantityText(exactEconomic(value), translate),
        values: () => ({quantity: formatExactQuantity(value), count: exactQuantityCount(value)}),
    };
}

function quantityEstimated(value: ExactRatio, shown: string, count: number): SiteCase {
    return {
        site: 'economicQuantityText, estimated',
        key: `${DETAIL_KEY}.quantityEstimated`,
        sensitivity: 'personal',
        figure: 'quantity',
        input: label(value),
        shown,
        count,
        run: (translate) => economicQuantityText(estimatedEconomic(value), translate),
        values: () => ({quantity: formatExactQuantity(value), count: exactQuantityCount(value)}),
    };
}

/**
 * Every site at 1, 2 and 1.5, each with the figure shown and its count, written out. A public site
 * also at 100, an exact economic quantity also as a ratio, and the estimated one only as ratios,
 * approximate (`≈`) or not. The 21st fraction digit of a quote base is not shown, so it is not
 * counted.
 */
const CASES: SiteCase[] = [
    buyUnits('1', '1', 1),
    buyUnits('2', '2', 2),
    buyUnits('1.5', '1.5', 1.5),
    stepUnits('1', '1', 1),
    stepUnits('2', '2', 2),
    stepUnits('1.5', '1.5', 1.5),
    stepUnits('100', '100', 100),
    pricePer('2', '2', 2),
    pricePer('1.5', '1.5', 1.5),
    pricePer('100', '100', 100),
    pricePer(TWENTY_ONE_DIGIT_ONE, '1', 1),
    minimumUnits('1', '1', 1),
    minimumUnits('2', '2', 2),
    minimumUnits('1.5', '1.5', 1.5),
    capUnits('1', '1', 1),
    capUnits('2', '2', 2),
    capUnits('1.5', '1.5', 1.5),
    quantityExact(finite('1'), '1', 1),
    quantityExact(finite('2'), '2', 2),
    quantityExact(finite('1.5'), '1.5', 1.5),
    quantityExact(ratio('3', '2', '1.5'), '1.5', 1.5),
    quantityEstimated(ratio('10000001', '10000000', '1'), '≈1', 1),
    quantityEstimated(ratio('2', '1', '2'), '2', 2),
    quantityEstimated(ratio('3', '2', '1.5'), '1.5', 1.5),
    quantityEstimated(ratio('1', '3', '0.333333'), '≈0.333333', 0.5),
];

/** The seven sites, in the order of the cases. */
const SITES = [...new Set(CASES.map((c) => c.site))];

describe('result text — each plural site passes the count of the figure it shows, privacy off', () => {
    for (const c of CASES) {
        it(`${c.site}: ${c.input} → ${c.shown}, count ${c.count}`, () => {
            privacy(false);
            const {calls, translate} = recorder();
            const sentence = c.run(translate);
            expect(
                calls.map((call) => call.key),
                'one call, at its key',
            ).toEqual([c.key]);
            expect(sentence, "the sentence is the translator's answer").toBe(answer(c.key));
            const {values} = calls[0];
            expect(values[c.figure], 'the figure, as shown').toBe(c.shown);
            expect(values.count, 'its count').toBe(c.count);
            expect(values, "the formatter's figure and its count, nothing else").toEqual(c.values());
        });
    }

    for (const base of ['1', '1.000']) {
        it(`priceText: a quote base of ${base} unit is the price alone, with no call`, () => {
            privacy(false);
            const {calls, translate} = recorder();
            expect(priceText(price(base), translate, digits)).toBe(formatExactPricePlain(price(base), digits));
            expect(calls).toEqual([]);
        });
    }
});

describe('result text — privacy on: a personal figure is masked and counts NaN, a public one stays in the clear', () => {
    for (const c of CASES) {
        it(`${c.site}: ${c.input}, ${c.sensitivity}`, () => {
            privacy(true);
            const {calls, translate} = recorder();
            expect(c.run(translate), "the sentence is the translator's answer").toBe(answer(c.key));
            expect(
                calls.map((call) => call.key),
                'one call, at its key',
            ).toEqual([c.key]);
            const {values} = calls[0];
            if (c.sensitivity === 'personal') {
                // The ≈ of an approximate ratio stays outside the mask; nothing else does.
                expect(values[c.figure], 'the figure is masked').toBe(c.shown.startsWith('≈') ? '≈' + MASK : MASK);
                expect(values.count, 'a masked figure counts NaN, never a hidden 1').toBeNaN();
            } else {
                expect(values[c.figure], 'a public figure stays in the clear').toBe(c.shown);
                expect(values.count, 'and so does its count').toBe(c.count);
                for (const [name, value] of Object.entries(values)) if (typeof value === 'string') expect(value, `${name} is in the clear`).toMatch(/\d/);
            }
            expect(values, "the formatter's figure and its count under privacy, nothing else").toEqual(c.values());
        });
    }
});

/** The message at a dotted key of a catalogue; undefined when the key is missing or names a subtree. */
function messageAt(catalogue: unknown, key: string): string | undefined {
    const node = key.split('.').reduce<unknown>((parent, part) => (parent !== null && typeof parent === 'object' ? (parent as Record<string, unknown>)[part] : undefined), catalogue);
    return typeof node === 'string' ? node : undefined;
}

/** The EN message at a dotted key; undefined when the key is missing or names a subtree. */
function catalogueMessage(key: string): string | undefined {
    return messageAt(en, key);
}

describe('result text — every plural fallback is the EN catalogue message at its key (P-d)', () => {
    it('reads a message at a key, and nothing at a missing key or at a subtree', () => {
        expect(catalogueMessage(`${KEY}.buyAmount`)).toEqual(expect.any(String));
        expect(catalogueMessage(`${KEY}.noSuchMessage`)).toBeUndefined();
        expect(catalogueMessage(KEY)).toBeUndefined();
    });

    it('the cases reach the six plural keys, at seven sites', () => {
        const keys = new Set(CASES.map((c) => c.key));
        expect(keys).toEqual(new Set(Object.keys(PLURAL_KEYS)));
        expect(SITES).toHaveLength(7);
    });

    for (const site of SITES) {
        it(`${site}: every call falls back to the en.json message at its key`, () => {
            privacy(false);
            const mismatches: string[] = [];
            let checked = 0;
            for (const c of CASES.filter((candidate) => candidate.site === site)) {
                const {calls, translate} = recorder();
                c.run(translate);
                for (const call of calls) {
                    checked += 1;
                    const message = catalogueMessage(call.key);
                    const where = `${site} at ${c.input}, ${call.key}`;
                    if (call.fallback === undefined) mismatches.push(`${where}: the call has no fallback`);
                    else if (message === undefined) mismatches.push(`${where}: en.json has no message there`);
                    else if (message !== call.fallback) mismatches.push(`${where}: the fallback says ${JSON.stringify(call.fallback)}, en.json says ${JSON.stringify(message)}`);
                }
            }
            // A site that made no call would check nothing and pass.
            expect(checked, 'calls checked').toBeGreaterThan(0);
            expect(mismatches).toEqual([]);
        });
    }
});

type RuntimeFormatter = ReturnType<typeof getMessageFormatter>;
type Ast = ReturnType<RuntimeFormatter['getAst']>;
type AstElement = Ast[number];
type PluralElement = Extract<AstElement, {pluralType: unknown}>;

/** The first element of a message, as the runtime parses it. */
function firstElement(message: string): AstElement | undefined {
    return getMessageFormatter(message).getAst()[0];
}

// Read off parses rather than imported: the `TYPE` enum lives in another transitive package.
const LITERAL_TYPE = firstElement('text')?.type;
const PLURAL_PROBE = firstElement('{n, plural, other {#}}');
const PLURAL_TYPE = PLURAL_PROBE?.type;
const POUND_TYPE = PLURAL_PROBE !== undefined && 'options' in PLURAL_PROBE ? PLURAL_PROBE.options.other?.value[0]?.type : undefined;
const SELECT_TYPE = firstElement('{g, select, other {x}}')?.type;

/** The class `getMessageFormatter` instantiates, read off one of its formatters rather than imported beside it. */
type RuntimeFormatterClass = new (message: string, locales?: string, overrideFormats?: undefined, options?: {ignoreTag?: boolean}) => RuntimeFormatter;
const RuntimeMessageFormat = getMessageFormatter('text').constructor as unknown as RuntimeFormatterClass;

/** The runtime's verdict on a message, or null when it compiles. */
function compileError(message: string, locale: SupportedLocale): string | null {
    try {
        getMessageFormatter(message, locale);
        return null;
    } catch (error) {
        return error instanceof Error ? error.message : String(error);
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

function isPlural(element: AstElement): element is PluralElement {
    return element.type === PLURAL_TYPE;
}

/** The plurals of an AST, at any depth. */
function pluralsOf(ast: Ast): PluralElement[] {
    return elementsOf(ast).filter(isPlural);
}

/** The `#` elements inside the options of a plural, at any depth. */
function poundsIn(plural: PluralElement): AstElement[] {
    const inside = Object.values(plural.options).flatMap((option) => elementsOf(option.value));
    return inside.filter((element) => element.type === POUND_TYPE);
}

/**
 * The argument names of an AST, sorted, walked structurally: never a regex over the text, which
 * would read the branch texts of a plural as names. Literal text, and a `#` (which has no `value`),
 * name nothing.
 */
function argumentNames(ast: Ast): string[] {
    const names = new Set<string>();
    for (const element of elementsOf(ast)) if (element.type !== LITERAL_TYPE && 'value' in element) names.add(element.value);
    return [...names].sort();
}

/**
 * A formatter with the plural rules of one locale: the runtime's class, the runtime's parse option
 * (`ignoreTag`), and the locale it is given, which `getMessageFormatter` would drop on a message it
 * has already compiled.
 */
function selector(message: string, locale: SupportedLocale): RuntimeFormatter {
    const formatter = new RuntimeMessageFormat(message, locale, undefined, {ignoreTag: true});
    expect(formatter.resolvedOptions().locale, 'control: the plural rules of the locale asked for').toBe(locale);
    return formatter;
}

/** What a formatter renders for a count, every other argument fixed: only the selection can change it. */
function render(formatter: RuntimeFormatter, count: number): string {
    const text = formatter.format({quantity: 'Q', step: 'S', price: 'P', count});
    if (typeof text !== 'string') throw new Error(`the message rendered ${JSON.stringify(text)}, not a string`);
    return text;
}

/** A catalogue message the test cannot do without: its absence is a failure, not a skip. */
function requiredMessage(locale: SupportedLocale, key: string): string {
    const message = messageAt(CATALOGUES[locale], key);
    if (message === undefined) throw new Error(`${locale}.json has no message at ${key}`);
    return message;
}

/** The counts the CLDR rules of each locale select as `one`, among the probes: French by its integer part, the others by 1 alone. */
const ONE_IN: Record<SupportedLocale, number[]> = {en: [1], it: [1], fr: [0, 0.5, 1, 1.5], es: [1]};
const PROBES = [0, 0.5, 1, 1.5, 2, 1_000_000, NaN];

describe('result text — the plural messages, in the four catalogues (ICU)', () => {
    it('control: the AST types are read off the runtime, four distinct ones', () => {
        const types = [LITERAL_TYPE, PLURAL_TYPE, POUND_TYPE, SELECT_TYPE];
        expect(types).not.toContain(undefined);
        expect(new Set(types).size).toBe(4);
    });

    it('control: the compile step is the runtime’s own, and it throws on a plural with no other', () => {
        expect(() => getMessageFormatter('{count, plural, one {ONE}}', 'en')).toThrow('MISSING_OTHER_CLAUSE');
        expect(compileError('{count, plural, one {ONE}}', 'en')).toBe('MISSING_OTHER_CLAUSE');
        expect(compileError('{count, plural, one {ONE} other {OTHER}}', 'en')).toBeNull();
    });

    it('control: the walkers find a plural, its offset, the # inside it and every argument name, at any depth', () => {
        const ast = getMessageFormatter('{quantity} {count, plural, one {ONE} other {# {kind, select, other {OTHER}}}}').getAst();
        const plurals = pluralsOf(ast);
        expect(plurals.map((plural) => [plural.value, plural.pluralType, plural.offset])).toEqual([['count', 'cardinal', 0]]);
        expect(poundsIn(plurals[0])).toHaveLength(1);
        expect(argumentNames(ast)).toEqual(['count', 'kind', 'quantity']);

        const plain = pluralsOf(getMessageFormatter('{count, plural, offset:1 one {ONE} other {OTHER}}').getAst());
        expect(plain.map((plural) => plural.offset)).toEqual([1]);
        expect(poundsIn(plain[0])).toEqual([]);
        const ordinal = pluralsOf(getMessageFormatter('{n, selectordinal, one {ONE} other {OTHER}}').getAst());
        expect(ordinal.map((plural) => plural.pluralType)).toEqual(['ordinal']);
        expect(pluralsOf(getMessageFormatter('{g, select, other {OTHER}}').getAst())).toEqual([]);
    });

    for (const locale of SUPPORTED_LOCALES) {
        it(`control: the ${locale} rules select one at ${ONE_IN[locale].join(', ')}, and other elsewhere, NaN and a million included`, () => {
            const probe = selector('{count, plural, one {ONE} other {OTHER}}', locale);
            const selected = PROBES.map((count) => [count, render(probe, count)]);
            const expected = PROBES.map((count) => [count, ONE_IN[locale].includes(count) ? 'ONE' : 'OTHER']);
            expect(selected).toEqual(expected);
        });
    }

    for (const key of Object.keys(PLURAL_KEYS)) {
        for (const locale of SUPPORTED_LOCALES) {
            it(`${key}, ${locale}: one cardinal plural on count, with one and other and no #, selected by the ${locale} rules`, () => {
                const message = requiredMessage(locale, key);
                expect(compileError(message, locale), 'it compiles with the runtime').toBeNull();
                const formatter = selector(message, locale);
                const ast = formatter.getAst();

                const plurals = pluralsOf(ast);
                const pluralArguments = plurals.map((plural) => plural.value);
                expect(pluralArguments, 'exactly one plural, on count').toEqual(['count']);
                const [plural] = plurals;
                expect(plural.pluralType, 'a cardinal plural').toBe('cardinal');
                expect(plural.offset, 'with no offset').toBe(0);
                expect(Object.keys(plural.options).sort(), 'its options, one and other').toEqual(['one', 'other']);
                expect(poundsIn(plural), 'no #: the count stands for the figure shown and is never printed').toEqual([]);

                const names = argumentNames(ast);
                expect(names, 'the arguments of the key').toEqual(PLURAL_KEYS[key]);
                expect(names, 'the arguments of EN').toEqual(argumentNames(selector(requiredMessage('en', key), 'en').getAst()));

                // Selection, read through the rendered text: every other argument is fixed, so only the plural can change it.
                const rendered = (count: number): string => render(formatter, count);
                expect(rendered(NaN), 'NaN, the count of a masked figure, renders like 2').toBe(rendered(2));
                expect(rendered(1_000_000), 'a million renders like 2: a CLDR many falls back to other').toBe(rendered(2));
                const like = locale === 'fr' ? 1 : 2;
                for (const count of [1.5, 0.5, 0]) expect(rendered(count), `${count} renders like ${like}`).toBe(rendered(like));
                if (locale === 'en') expect(rendered(1), 'the source language tells 1 from 2').not.toBe(rendered(2));
            });
        }
    }
});

// Read as text, as the bundler reads it: the glob argument must stay a literal.
const DIALOG_SOURCE = import.meta.glob('../steps/DistributionDialog.svelte', {query: '?raw', import: 'default', eager: true})['../steps/DistributionDialog.svelte'] as string;

/** The two Dashboard help texts R7 rewrites. */
const DISTRIBUTION_KEYS = ['tools.pacAllocator.planner.distribution.differs', 'tools.pacAllocator.planner.distribution.source'];

function escapeRegExp(text: string): string {
    return text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

/** A quoted string literal on one line, single or double quotes, escapes included. */
const QUOTED = String.raw`'(?:[^'\\\n]|\\.)*'|"(?:[^"\\\n]|\\.)*"`;

/** The text of a quoted string literal: its quotes dropped, its escapes read. */
function unquote(literal: string): string {
    return literal.slice(1, -1).replace(/\\(.)/g, (_, char: string) => (char === 'n' ? '\n' : char === 't' ? '\t' : char));
}

interface FallbackCall {
    line: number;
    fallback: string;
}

/** Every `$t('<key>', {default: '…'})` of a source, with its line and the text of its fallback. */
function fallbackCalls(source: string, key: string): FallbackCall[] {
    const escaped = escapeRegExp(key);
    const call = new RegExp(String.raw`\$t\(\s*(?:'${escaped}'|"${escaped}")\s*,\s*\{\s*default:\s*(${QUOTED})`, 'g');
    return [...source.matchAll(call)].map((match) => ({line: source.slice(0, match.index ?? 0).split('\n').length, fallback: unquote(match[1])}));
}

/** Every quoted occurrence of a key in a source, whatever surrounds it. */
function quotedOccurrences(source: string, key: string): number {
    const escaped = escapeRegExp(key);
    return [...source.matchAll(new RegExp(String.raw`'${escaped}'|"${escaped}"|\x60${escaped}\x60`, 'g'))].length;
}

describe('DistributionDialog — the two Dashboard help texts fall back to the en.json message', () => {
    it('control: the reader finds each call with its line and its text, escapes read, and counts every quoted key', () => {
        const source = [`$t('a.b', {default: 'It\\'s one'})`, `$t("a.b", {default: "two \\"quoted\\""})`, `const keys = ['a.b'];`, `$t('a.bc', {default: 'longer key'})`].join('\n');
        expect(fallbackCalls(source, 'a.b')).toEqual([
            {line: 1, fallback: "It's one"},
            {line: 2, fallback: 'two "quoted"'},
        ]);
        expect(quotedOccurrences(source, 'a.b')).toBe(3);
        expect(quotedOccurrences(source, 'a.bc')).toBe(1);
    });

    for (const key of DISTRIBUTION_KEYS) {
        it(`${key}: every fallback in the component is the en.json message`, () => {
            expect(DIALOG_SOURCE, 'the component source was read').toEqual(expect.any(String));
            const calls = fallbackCalls(DIALOG_SOURCE, key);
            expect(calls.length, 'the key is found, with a fallback').toBeGreaterThan(0);
            // A use of the key the reader cannot parse would otherwise go unchecked.
            expect(calls.length, 'every quoted use of the key is a call the reader parsed').toBe(quotedOccurrences(DIALOG_SOURCE, key));
            const message = catalogueMessage(key);
            expect(message, 'en.json has a message at the key').toEqual(expect.any(String));
            for (const {line, fallback} of calls) expect(fallback, `DistributionDialog.svelte:${line}`).toBe(message);
        });
    }
});
