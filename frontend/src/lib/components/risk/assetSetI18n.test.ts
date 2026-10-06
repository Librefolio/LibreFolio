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
 * The text L3° actually puts on screen under its scatter, read from the component that draws it.
 *
 * Why this exists: `AssetSetRiskReturnSection` once borrowed the portfolio L3's note,
 * `risk.levels.l3.scatter.note`, which opened with "Above the line means better paid for the risk
 * taken". That sentence is right on Dashboard and Broker Detail, where the capital market line is
 * drawn. On this page the line cannot exist — `RiskAssetSetReturnOutput` has no field for a
 * portfolio aggregate, so `capitalMarketLine()` has no point to anchor on — and the borrowed note
 * put back, in words, the one judgement the payload's shape makes impossible. Every gate was green:
 * the key is present, valid ICU, and referenced.
 *
 * Since 06/10/2026 the notes are the shared `RiskReturnLevel`'s, one idea per line, each said only
 * where it applies (`riskReturnNotes`). So the guard takes every note a chart without a line can
 * carry — whatever the page declares, with or without anything left out of the plot, which covers
 * the lab's — and every catalogue key the component renders for each of them, read out of its
 * source rather than named here, so the test follows the component if a note changes its key.
 */
const RISK_RETURN_LEVEL_SOURCE = import.meta.glob('./RiskReturnLevel.svelte', {query: '?raw', import: 'default', eager: true})['./RiskReturnLevel.svelte'] as string;
const {riskReturnNotes} = await import('./riskReturnLevel');
const {capitalMarketLineAnchor} = await import('$lib/components/charts/scatterChartHelpers');
type RiskReturnNote = import('./riskReturnLevel').RiskReturnNote;
type RiskReturnCapabilities = import('./riskReturnLevel').RiskReturnCapabilities;

/** The catalogue keys the component renders for one note: every key quoted in that note's branch of the list. */
function renderedNoteKeys(note: RiskReturnNote): string[] {
    const branch = RISK_RETURN_LEVEL_SOURCE.split(/\{(?:#if|:else if) note === '/)
        .slice(1)
        .find((candidate) => candidate.startsWith(`${note}'}`));
    return branch === undefined ? [] : [...new Set([...branch.matchAll(/'(risk\.[A-Za-z0-9_.]+)'/g)].map((match) => match[1]))];
}

/** Every note a chart without a line can carry, whatever the page declares and whatever it leaves out of the plot. */
function notesWithoutALine(): RiskReturnNote[] {
    const declared: RiskReturnCapabilities[] = [{}, {ratios: true}, {ratios: true, benchmark: true}, {weight: true, ratios: true, benchmark: true}];
    const outsides = [null, {cash: 0.046, unpriced: 0.004}];
    return [...new Set(declared.flatMap((capabilities) => outsides.flatMap((outside) => riskReturnNotes({lineAnchor: null, capabilities, outside}))))];
}

/** Words that name a drawn line, in the four shipped languages. */
const LINE_WORDS: Record<SupportedLocale, RegExp> = {
    en: /\bline\b/i,
    it: /\bretta\b/i,
    fr: /\bdroite\b/i,
    es: /\brecta\b/i,
};

describe('asset-set i18n — L3° describes the line exactly when it draws one', () => {
    /*
     * Since the developer's review of 06/10/2026 («non compare la retta tra 0 e benchmark») the lab draws the
     * line once a benchmark is placed: the benchmark anchors it on a plot with no portfolio. So the guard is
     * no longer "never a line" but "a line in words exactly when one is drawn". Its premise is the real anchor
     * (`capitalMarketLineAnchor`) on the lab's real dots (`buildAssetSetChartPoints`, what
     * `AssetSetRiskReturnSection` hands the shared level), and its notes are the real ones (`riskReturnNotes`)
     * under what the lab declares: ratios always, a benchmark when one applies, never a weight, nothing left out
     * of the plot. The keys are read out of the component's source, as above, and the line's own sentence is
     * the side of the component's `lineAnchor === … ? … : …` that the anchor takes.
     */
    type AssetSetPaidRow = import('./assetSetLevels').AssetSetPaidRow;
    type LineAnchor = ReturnType<typeof capitalMarketLineAnchor>;
    /** No benchmark; one nobody selected, a dot of its own; or one of the selected assets, its row's dot (D371). */
    type LabBenchmark = 'none' | 'unselected' | 'selected';

    const LINE_KEY = 'risk.levels.l3.scatter.notes.line';
    const LINE_BENCHMARK_KEY = 'risk.levels.l3.scatter.notes.lineBenchmark';
    const ABOVE_KEY = 'risk.levels.l3.scatter.notes.above';

    /** Two selected assets, both measured; `referenceId` marks the one that is the benchmark itself. */
    function labRows(referenceId: number | null): AssetSetPaidRow[] {
        return [
            {assetId: 1, name: 'a', volatility: 0.2, expectedReturn: 0.1, sharpe: 0.4, sortino: 0.6, beta: null, correlation: null, isReference: referenceId === 1},
            {assetId: 2, name: 'b', volatility: 0.15, expectedReturn: 0.05, sharpe: 0.3, sortino: 0.5, beta: null, correlation: null, isReference: referenceId === 2},
        ];
    }

    /** The dots the lab draws for one state of its benchmark, built by the lab's own builder. */
    async function labDots(benchmark: LabBenchmark) {
        const {buildAssetSetChartPoints} = await import('./assetSetLevels');
        if (benchmark === 'none') return buildAssetSetChartPoints(labRows(null), null);
        if (benchmark === 'unselected') return buildAssetSetChartPoints(labRows(null), {assetId: 90, name: 'c', volatility: 0.18, expectedReturn: 0.07});
        return buildAssetSetChartPoints(labRows(2), {assetId: 2, name: 'b', volatility: 0.15, expectedReturn: 0.05});
    }

    /** The source of one note's branch of the list, split the way `renderedNoteKeys` splits it. */
    function noteBranch(note: RiskReturnNote): string {
        return (
            RISK_RETURN_LEVEL_SOURCE.split(/\{(?:#if|:else if) note === '/)
                .slice(1)
                .find((candidate) => candidate.startsWith(`${note}'}`)) ?? ''
        );
    }

    /** The keys one note renders under `lineAnchor`: every key of its branch but the side of each `lineAnchor === '…' ? … : …` the anchor does not take. */
    function keysFor(note: RiskReturnNote, lineAnchor: LineAnchor): string[] {
        const notTaken = [...noteBranch(note).matchAll(/lineAnchor\s*===\s*'(\w+)'\s*\?\s*'(risk\.[A-Za-z0-9_.]+)'\s*:\s*'(risk\.[A-Za-z0-9_.]+)'/g)].map(([, anchor, whenEqual, otherwise]) => (lineAnchor === anchor ? otherwise : whenEqual));
        return renderedNoteKeys(note).filter((key) => !notTaken.includes(key));
    }

    /** What the lab puts under its chart: the roles of its dots, the anchor they give, the notes it declares and the keys they render. */
    async function renderedByTheLab(benchmark: LabBenchmark) {
        const dots = await labDots(benchmark);
        const lineAnchor = capitalMarketLineAnchor(dots);
        const notes = riskReturnNotes({lineAnchor, capabilities: {ratios: true, benchmark: benchmark !== 'none'}, outside: null});
        return {roles: dots.map((dot) => dot.role), lineAnchor, notes, keys: [...new Set(notes.flatMap((note) => keysFor(note, lineAnchor)))]};
    }

    /** One line per key whose message, in `locale`, names a drawn line. */
    function namingALine(locale: SupportedLocale, keys: readonly string[]): string[] {
        return keys.flatMap((key) => {
            const message = at(CATALOGUES[locale], key);
            return typeof message === 'string' && LINE_WORDS[locale].test(message) ? [`${locale}: ${key} → ${JSON.stringify(message)}`] : [];
        });
    }

    it('reads the lab’s dots, the anchor they give and the keys each note renders for it, so the checks below are not reading nothing', async () => {
        expect(RISK_RETURN_LEVEL_SOURCE, 'the component source did not load').toContain('-scatter-note');

        // The real anchor on the lab's real dots: assets alone anchor nothing; a benchmark, selected or not,
        // anchors the line; and no dot is ever a portfolio.
        const bare = await renderedByTheLab('none');
        expect(bare.roles, 'premise: without a benchmark the lab draws its assets alone').toEqual(['asset', 'asset']);
        expect(bare.lineAnchor, "premise: a chart of the lab's assets anchors no line").toBeNull();
        const unselected = await renderedByTheLab('unselected');
        expect(unselected.roles, 'premise: a benchmark nobody selected is a dot of its own, last').toEqual(['asset', 'asset', 'benchmark']);
        expect(unselected.lineAnchor, "premise: the lab's benchmark anchors the line").toBe('benchmark');
        const selected = await renderedByTheLab('selected');
        expect(selected.roles, 'premise: a selected benchmark is its row’s dot, drawn as the benchmark').toEqual(['asset', 'benchmark']);
        expect(selected.lineAnchor, "premise: the lab's benchmark anchors the line, selected or not").toBe('benchmark');

        // The reader takes the anchor's side of the line's sentence, and the two sides are two keys.
        expect(keysFor('line', 'benchmark'), 'the reader lost the sentence for the line through the benchmark').toContain(LINE_BENCHMARK_KEY);
        expect(keysFor('line', 'benchmark'), 'the reader kept both sides of the anchor’s choice').not.toContain(LINE_KEY);
        expect(keysFor('line', 'portfolio'), 'the reader lost the sentence for the line through the portfolio').toContain(LINE_KEY);
        expect(keysFor('line', 'portfolio'), 'the reader kept both sides of the anchor’s choice').not.toContain(LINE_BENCHMARK_KEY);

        // Every key the lab renders, in each state, is in the catalogue the four languages are read from.
        for (const {keys} of [bare, unselected, selected]) {
            expect(keys, 'the lab renders no key: the checks below would read nothing').not.toEqual([]);
            for (const key of keys) expect(typeof at(en, key), `${key}, rendered by the lab, is not in en.json`).toBe('string');
        }
    });

    it('positive control: what being above the line means, and the line through the benchmark or through the portfolio, would each be caught in each language', () => {
        const misses = SUPPORTED_LOCALES.flatMap((locale) => [ABOVE_KEY, LINE_BENCHMARK_KEY, LINE_KEY].flatMap((key) => (namingALine(locale, [key]).length === 1 ? [] : [`${locale}: ${key} → ${JSON.stringify(at(CATALOGUES[locale], key))}`])));
        expect(misses, 'the detector no longer recognises the sentences about the line').toEqual([]);
    });

    it('without a benchmark the lab draws no line, and no note it renders — nor any a chart without a line carries — names one, in any of the four languages', async () => {
        const lab = await renderedByTheLab('none');
        expect(lab.lineAnchor, "premise: a chart of the lab's assets anchors no line").toBeNull();

        // Presence first: the notes every chart carries were rendered, so the absences are about the line.
        expect(lab.notes, 'the notes every chart carries were not found: the checks below would read nothing').toEqual(expect.arrayContaining(['return', 'priceOnly']));
        expect(
            lab.notes.filter((note) => note === 'above' || note === 'line'),
            'the lab draws no line and describes one',
        ).toEqual([]);
        expect(
            SUPPORTED_LOCALES.flatMap((locale) => namingALine(locale, lab.keys)),
            'the lab draws no line without a benchmark: a note that names one restores, in words, a verdict nothing on screen draws',
        ).toEqual([]);

        // And whatever a page declares, a chart without a line — the lab's among them — renders no note that names one.
        expect(notesWithoutALine(), "the lab's notes are among those a chart without a line can carry").toEqual(expect.arrayContaining(lab.notes));
        const offenders = notesWithoutALine().flatMap((note) => SUPPORTED_LOCALES.flatMap((locale) => namingALine(locale, renderedNoteKeys(note)).map((offence) => `${note} → ${offence}`)));
        expect(offenders, 'a chart with no line renders a note that describes one').toEqual([]);
    });

    it.each(['unselected', 'selected'] as const)('with a benchmark (%s), the lab draws the line through it and says what being above it means and that it runs through the benchmark — never through the portfolio — in all four languages', async (benchmark) => {
        const lab = await renderedByTheLab(benchmark);
        expect(lab.lineAnchor, "the lab's benchmark anchors the line").toBe('benchmark');

        expect(lab.notes, 'the lab draws a line: it says what being above it means, and where it comes from').toEqual(expect.arrayContaining(['above', 'line']));
        expect(lab.keys).toEqual(expect.arrayContaining([ABOVE_KEY, LINE_BENCHMARK_KEY]));
        expect(lab.keys, 'the lab has no portfolio: its line never runs through one').not.toContain(LINE_KEY);
        for (const locale of SUPPORTED_LOCALES) {
            const rendered = lab.keys.map((key) => at(CATALOGUES[locale], key));
            expect(
                rendered.filter((message) => typeof message !== 'string'),
                `${locale}: a key the lab renders has no message`,
            ).toEqual([]);
            expect(rendered, `${locale}: what being above the line means`).toContain(at(CATALOGUES[locale], ABOVE_KEY));
            expect(rendered, `${locale}: the line through the benchmark`).toContain(at(CATALOGUES[locale], LINE_BENCHMARK_KEY));
            expect(rendered, `${locale}: the line through the portfolio, which the lab does not have`).not.toContain(at(CATALOGUES[locale], LINE_KEY));
            expect(namingALine(locale, lab.keys), `${locale}: the lab draws a line and no note names it`).not.toEqual([]);
        }
    });
});
