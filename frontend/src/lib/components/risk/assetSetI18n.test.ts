/**
 * @vitest-environment node
 *
 * Asset-set i18n — every message this workstream owns must compile as ICU MessageFormat.
 *
 * Why this file exists: `risk.assetSet.levels.l1.lastedDays` shipped as `lasted {{days}} d` in all
 * four catalogues. Double braces are i18next/Mustache; svelte-i18n speaks ICU, where a top-level
 * `{{days}}` is MALFORMED_ARGUMENT. Nothing failed: `$_()` catches the parse error, logs it on
 * `console.warn` and renders the raw template. `i18n audit` checks presence, `front check` checks
 * types, the E2E checked `data-measured` — each was green about a page that printed `{{days}}`.
 *
 * **The compile step is the runtime's own.** `getMessageFormatter` is the constructor `$_()` calls;
 * `intl-messageformat` is only a transitive dependency, and importing it directly could test a copy
 * the app does not run. It needs no `init()`/`addMessages()`, and on a malformed message it *throws*
 * — the logging happens one level up, in `$_()`. The first control pins that, because a checker
 * built on a try/catch is blind to a compile path that logs and carries on.
 *
 * **Stricter than the runtime, on purpose.** `$_()` only compiles a message when it is given values,
 * so a malformed message rendered without values shows its braces and logs nothing. Every owned leaf
 * is compiled here regardless: it is one call site away from breaking.
 *
 * **"0 malformed" means nothing on its own** — it is also what a checker that reads nothing reports.
 * The controls prove, through the same functions, that the i18next form is reported with its locale
 * and key, that the ICU form is not, that a missing owned key is reported rather than skipped, and
 * that the walk over the real catalogues reaches the key that broke.
 *
 * Scope: the whole `risk.assetSet` subtree, plus the ten `risk.analytics.assetSet*.{name,description}`
 * keys the backend plugins publish as `name_i18n_key` / `description_i18n_key`.
 */
import {afterEach, describe, expect, it, vi} from 'vitest';
import {getMessageFormatter} from 'svelte-i18n';

import {SUPPORTED_LOCALES, type SupportedLocale} from '$lib/i18n';
import en from '$lib/i18n/en.json';
import itCatalogue from '$lib/i18n/it.json';
import fr from '$lib/i18n/fr.json';
import es from '$lib/i18n/es.json';

/** Typed on the app's locale list, so a fifth locale without a catalogue here fails `front check`. */
const CATALOGUES: Record<SupportedLocale, unknown> = {en, it: itCatalogue, fr, es};

const OWNED_SUBTREE = 'risk.assetSet';
const BACKEND_ANALYTICS = ['assetSetKpi', 'assetSetVar', 'assetSetDrawdown', 'assetSetRiskReturn', 'assetSetComparison'] as const;
const OWNED_KEYS = BACKEND_ANALYTICS.flatMap((code) => [`risk.analytics.${code}.name`, `risk.analytics.${code}.description`]);
/** The key `AssetSetLossComparisonSection` formats with a value — the one that broke. */
const DURATION_KEY = 'risk.assetSet.levels.l1.lastedDays';

interface OwnedMessage {
    key: string;
    message: unknown;
}

function at(catalogue: unknown, key: string): unknown {
    return key.split('.').reduce<unknown>((node, part) => (node !== null && typeof node === 'object' ? (node as Record<string, unknown>)[part] : undefined), catalogue);
}

function leaves(node: unknown, key: string): OwnedMessage[] {
    if (node === null || typeof node !== 'object') return [{key, message: node}];
    return Object.entries(node).flatMap(([part, child]) => leaves(child, `${key}.${part}`));
}

function ownedMessages(catalogue: unknown): OwnedMessage[] {
    return [...leaves(at(catalogue, OWNED_SUBTREE), OWNED_SUBTREE), ...OWNED_KEYS.map((key) => ({key, message: at(catalogue, key)}))];
}

/** The parser's verdict on one message, or null when it compiles. */
function icuError(message: string): string | null {
    try {
        getMessageFormatter(message);
        return null;
    } catch (error) {
        return error instanceof Error ? error.message : String(error);
    }
}

/** One line per owned message that would not reach the screen intact, naming its locale and key. */
function audit(locale: string, catalogue: unknown): string[] {
    return ownedMessages(catalogue).flatMap(({key, message}) => {
        if (typeof message !== 'string') return [`${locale}: ${key} is ${message === undefined ? 'missing' : `${message === null ? 'null' : typeof message}, not a message`}`];
        const error = icuError(message);
        return error === null ? [] : [`${locale}: ${key} → ${error} in ${JSON.stringify(message)}`];
    });
}

type Ast = ReturnType<ReturnType<typeof getMessageFormatter>['getAst']>;

/** Read off a parse rather than imported: the `TYPE` enum lives in another transitive package. */
const LITERAL_TYPE = getMessageFormatter('text').getAst()[0]?.type;

/**
 * Argument names, walked structurally. Never a regex over the source: one read the branch texts of
 * `{count, plural, one {…} other {…}}` as argument names and produced 21 false positives.
 */
function argumentNames(ast: Ast, names = new Set<string>()): Set<string> {
    for (const element of ast) {
        // Literal text, and the `#` of a plural (which has no `value`), name nothing.
        if (element.type === LITERAL_TYPE || !('value' in element)) continue;
        names.add(element.value);
        if ('options' in element) for (const option of Object.values(element.options)) argumentNames(option.value, names);
        if ('children' in element) argumentNames(element.children, names);
    }
    return names;
}

function argumentsOf(message: string): string[] {
    return [...argumentNames(getMessageFormatter(message).getAst())].sort();
}

function parityFailures(key: string, messages: Record<SupportedLocale, string>): string[] {
    const reference = argumentsOf(messages.en).join(', ');
    return SUPPORTED_LOCALES.flatMap((locale) => {
        const own = argumentsOf(messages[locale]).join(', ');
        return own === reference ? [] : [`${locale}: ${key} asks for {${own}}, en for {${reference}}`];
    });
}

describe('asset-set i18n — the checker itself', () => {
    afterEach(() => {
        vi.restoreAllMocks();
    });

    it('reports the i18next form as MALFORMED_ARGUMENT and compiles the ICU form — by throwing, never by logging', () => {
        const warn = vi.spyOn(console, 'warn').mockImplementation(() => {});
        const error = vi.spyOn(console, 'error').mockImplementation(() => {});

        expect(() => getMessageFormatter('lasted {{days}} d')).toThrow('MALFORMED_ARGUMENT');
        expect(icuError('lasted {{days}} d')).toBe('MALFORMED_ARGUMENT');
        expect(icuError('lasted {days} d')).toBeNull();
        expect(getMessageFormatter('lasted {days} d').format({days: 438})).toBe('lasted 438 d');

        expect(warn, 'getMessageFormatter logged instead of throwing: the try/catch in icuError would miss it').not.toHaveBeenCalled();
        expect(error, 'getMessageFormatter logged instead of throwing: the try/catch in icuError would miss it').not.toHaveBeenCalled();
    });

    it('names the locale and the key of every owned message it cannot compile or cannot find', () => {
        const analytics: Record<string, Record<string, string>> = Object.fromEntries(BACKEND_ANALYTICS.map((code) => [code, {name: 'Name', description: 'Description'}]));
        const synthetic = {
            risk: {
                analytics: {...analytics, assetSetVar: {name: 'Name'}},
                assetSet: {selectedCount: '{selected} selected of {total}', levels: {l1: {lastedDays: 'lasted {{days}} d'}}},
            },
        };

        expect(audit('xx', synthetic)).toEqual(['xx: risk.assetSet.levels.l1.lastedDays → MALFORMED_ARGUMENT in "lasted {{days}} d"', 'xx: risk.analytics.assetSetVar.description is missing']);
        expect(audit('xx', {}), 'a catalogue without the subtree must be reported, not read as clean').toContain('xx: risk.assetSet is missing');
    });

    it('reads argument names off the parsed AST, never out of the text of a plural branch', () => {
        expect(LITERAL_TYPE, 'the literal discriminant could not be read off the parser').toBeDefined();
        expect(argumentsOf('{selected} selected of {total}')).toEqual(['selected', 'total']);
        expect(argumentsOf('{count, plural, one {# day} other {# days}}')).toEqual(['count']);
        // `{{who}` is legitimate ICU inside a branch — why "no double braces" would be the wrong rule.
        expect(argumentsOf('{count, plural, one {{who} lost # day} other {{who} lost # days}}')).toEqual(['count', 'who']);
        expect(argumentsOf('{state, select, open {since {since}} other {closed}}')).toEqual(['since', 'state']);

        expect(parityFailures('k', {en: 'lasted {days} d', it: 'durata {giorni} g', fr: 'durée {days} j', es: 'duró {days} d'})).toEqual(['it: k asks for {giorni}, en for {days}']);
    });
});

describe('asset-set i18n — every owned message compiles as ICU MessageFormat', () => {
    it.each([...SUPPORTED_LOCALES])('%s.json', (locale) => {
        const catalogue = CATALOGUES[locale];

        // Barrier: the walk reached the depth of the key that broke; otherwise "no failures" is about nothing.
        expect(
            ownedMessages(catalogue).map(({key}) => key),
            `${locale}.json: the walk over ${OWNED_SUBTREE} never reached ${DURATION_KEY}`,
        ).toContain(DURATION_KEY);

        expect(audit(locale, catalogue), `${locale}.json: these owned messages would reach the screen as raw templates — svelte-i18n logs "has syntax error" and renders the source`).toEqual([]);
    });
});

describe('asset-set i18n — the four locales ask for the same arguments', () => {
    it('every owned message that compiles everywhere names the arguments en names', () => {
        // Keys that fail to compile are the previous block's report, and a key missing from a
        // locale is `i18n audit`'s: parity is only asked of what every locale can parse.
        const byKey = new Map<string, Partial<Record<SupportedLocale, string>>>();
        for (const locale of SUPPORTED_LOCALES) {
            for (const {key, message} of ownedMessages(CATALOGUES[locale])) {
                if (typeof message === 'string' && icuError(message) === null) byKey.set(key, {...byKey.get(key), [locale]: message});
            }
        }
        const comparable = [...byKey].flatMap(([key, messages]) => (SUPPORTED_LOCALES.every((locale) => messages[locale] !== undefined) ? [{key, messages: messages as Record<SupportedLocale, string>}] : []));

        expect(
            comparable.filter(({messages}) => argumentsOf(messages.en).length > 0).map(({key}) => key),
            'no owned message with arguments was compared: the parity check below would be vacuous',
        ).not.toEqual([]);
        expect(comparable.flatMap(({key, messages}) => parityFailures(key, messages))).toEqual([]);
    });
});

/**
 * The text L3° actually puts on screen under its scatter, read from the component itself.
 *
 * Why this exists: `AssetSetRiskReturnSection` borrowed the portfolio L3's note,
 * `risk.levels.l3.scatter.note`, which opens with "Above the line means better paid for the risk
 * taken". That sentence is right on Dashboard and Broker Detail, where the capital market line is
 * drawn. On this page the line cannot exist — `RiskAssetSetReturnOutput` has no field for a
 * portfolio aggregate, so `capitalMarketLine()` has no point to anchor on — and the borrowed note
 * put back, in words, the one judgement the payload's shape makes impossible. Every gate was green:
 * the key is present, valid ICU, and referenced.
 *
 * The key is read out of the component source rather than named here, so the test follows the
 * component if it ever switches to a different key.
 */
const RISK_RETURN_SECTION_SOURCE = import.meta.glob('./AssetSetRiskReturnSection.svelte', {query: '?raw', import: 'default', eager: true})['./AssetSetRiskReturnSection.svelte'] as string;

function renderedNoteKey(): string | null {
    const block = /data-testid="risk-asset-set-l3-scatter-note"[^>]*>\s*\{\$t\('([^']+)'\)/.exec(RISK_RETURN_SECTION_SOURCE);
    return block?.[1] ?? null;
}

/** Words that name a drawn line, in the four shipped languages. */
const LINE_WORDS: Record<SupportedLocale, RegExp> = {
    en: /\bline\b/i,
    it: /\bretta\b/i,
    fr: /\bdroite\b/i,
    es: /\brecta\b/i,
};

describe('asset-set i18n — L3° never describes a line it cannot draw', () => {
    it('finds the note the section renders, so the check below is not reading nothing', () => {
        expect(RISK_RETURN_SECTION_SOURCE, 'the component source did not load').toContain('risk-asset-set-l3-scatter-note');
        expect(renderedNoteKey(), 'could not read which key the scatter note renders — the check below would be vacuous').not.toBeNull();
    });

    it('positive control: the portfolio note, which is right where the line is drawn, would be caught', () => {
        const portfolioNote = at(en, 'risk.levels.l3.scatter.note');
        expect(typeof portfolioNote).toBe('string');
        expect(LINE_WORDS.en.test(portfolioNote as string), 'the detector no longer recognises the sentence it was written for').toBe(true);
    });

    it('renders a note that mentions no line, in any of the four languages', () => {
        const key = renderedNoteKey() as string;
        const offenders = SUPPORTED_LOCALES.flatMap((locale) => {
            const message = at(CATALOGUES[locale], key);
            return typeof message === 'string' && LINE_WORDS[locale].test(message) ? [`${locale}: ${key} → ${JSON.stringify(message)}`] : [];
        });
        expect(offenders, 'the scatter on Asset Global draws no line: a note that describes one restores, in words, the verdict the payload makes impossible').toEqual([]);
    });
});
