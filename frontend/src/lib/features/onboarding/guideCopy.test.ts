/**
 * Gate on the copy of the tours and guides (workstream J, round 8, C7).
 *
 * ## What this protects
 *
 * A rule the developer set twice — R19 of the usage review of 2026-09-22, then point 12 of the
 * live review of 2026-09-24, *apply it to every text, without having to remember it*: a step of
 * the intro tour or of a contextual guide DESCRIBES ITS SECTION OR CONTROL. It never announces
 * that another guide will start. C7 removed five sentences that did, in four languages, all of
 * the same shape — among them:
 *
 *     «A short guide starts when you choose Add Broker.»
 *     «A dedicated guide follows the form.»
 *     «Its dedicated guide starts on first use.»
 *
 * Saying what a section does stays fine even when what it does involves guides: Settings can
 * replay them, and saying so describes Settings.
 *
 * ## What it does, and what it deliberately does not
 *
 * It enumerates the step texts the overlay host renders — the `titleKey` and `descriptionKey`
 * literals of the `steps` table in `OnboardingOverlayHost.svelte`, which holds the intro tour and
 * every contextual guide — and fails when one of them names a guide or a tour, in any language.
 * It does not decide whether a mention is an announcement: that means reading the sentence, and a
 * gate that is wrong about intent in the annoying direction gets switched off, after which it
 * protects nothing. A mention that describes rather than announces is registered below, once,
 * with its reason, by a person.
 *
 * It reads translated text on purpose. The rule against asserting on translated text is about
 * using copy as a handle on the UI; here the copy is the subject.
 *
 * ## Why exceptions are keyed by catalogue key
 *
 * Not by the position of a step in the host's table nor by a line of a JSON file: an unrelated
 * edit shifts both and would turn the gate red for reasons that have nothing to do with the copy,
 * which trains people to update a registry without reading it. A key names the text itself, in
 * all four languages at once.
 *
 * ## Completeness, stated honestly
 *
 * The scan knows nouns — per language, read off the catalogues on 2026-09-24, see NOUN — and is
 * deterministic about those words and nothing else.
 *
 * - An announcement without one of them is not seen («A short walkthrough starts…»). The page
 *   guides are named "…overview" / "Panoramica…" / "Vue d'ensemble…" / "Resumen…" in
 *   `onboarding.flows`, but the same words name real tabs (`brokerDetailGuide.steps.overview`),
 *   so they are not patterns.
 * - The nouns have verb homographs: en «guides», it «guida», fr «guide», es «guía» also mean
 *   "(it) guides". The gate flags them and cannot tell them apart; a verb is reworded or
 *   registered, never absolved by the scanner.
 * - Only what the host renders is read. The intro scene (`onboarding.intro.*`), the replay section
 *   in Settings and the status toasts are other surfaces, and the retired `onboarding.tour.steps.*`
 *   texts the host no longer uses are not read either.
 * - An exception covers its key in every language and for its whole text: a sentence appended
 *   later to a registered text is not seen. Whoever edits one re-reads its reason.
 */

import {describe, expect, it} from 'vitest';
import {readFileSync} from 'node:fs';
import {resolve} from 'node:path';

const SRC = resolve(process.cwd(), 'src');
const HOST = 'lib/components/onboarding/OnboardingOverlayHost.svelte';
const LOCALES = ['en', 'it', 'fr', 'es'] as const;

type Locale = (typeof LOCALES)[number];
type Catalog = Record<string, unknown>;

/**
 * The only place a catalogue is read. Replaying the gate against another revision — the red-first
 * run of C7 read `git show HEAD:frontend/src/lib/i18n/<locale>.json` at `8347f8d6c` — swaps this
 * function and nothing else, so what runs is the gate and not a copy of it.
 */
function readCatalog(locale: Locale): Catalog {
    return JSON.parse(readFileSync(resolve(SRC, `lib/i18n/${locale}.json`), 'utf8')) as Catalog;
}

/** The node at a dotted key, walked the way the catalogues nest it. */
function nodeAt(catalog: Catalog, key: string): unknown {
    return key.split('.').reduce<unknown>((node, part) => (node !== null && typeof node === 'object' ? (node as Catalog)[part] : undefined), catalog);
}

function textAt(catalog: Catalog, key: string): string {
    const node = nodeAt(catalog, key);
    return typeof node === 'string' ? node : '';
}

function childrenAt(catalog: Catalog, key: string): string[] {
    const node = nodeAt(catalog, key);
    return node !== null && typeof node === 'object' ? Object.keys(node) : [];
}

/** Every `titleKey:` and `descriptionKey:` property of the host, with whatever follows the colon. */
const STEP_TEXT_PROPERTY = /\b(?:titleKey|descriptionKey)\s*:\s*([^,\n]*)/g;
const STRING_LITERAL = /^(['"])([^'"]+)\1$/;

/**
 * The text keys of the host's `steps` table. A value that is not a string literal is returned
 * apart instead of skipped: a key computed at runtime is a text this gate cannot read, and
 * reading only the others would make its silence look like a pass.
 */
function readStepKeys(source: string): {keys: string[]; unreadable: string[]} {
    const keys: string[] = [];
    const unreadable: string[] = [];
    for (const [, raw] of source.matchAll(STEP_TEXT_PROPERTY)) {
        const value = raw.trim();
        if (value === 'string;') continue; // the field declared by `interface StepPresentation`
        const literal = STRING_LITERAL.exec(value);
        if (literal) keys.push(literal[2]);
        else unreadable.push(value);
    }
    return {keys, unreadable};
}

/** A letter, a combining mark or a digit. JavaScript's `\b` knows only ASCII: to it «é» and «í» end a word. */
const LETTER = String.raw`[\p{L}\p{M}\p{N}_]`;
const nouns = (alternatives: string): RegExp => new RegExp(String.raw`(?<!${LETTER})(?:${alternatives})(?!${LETTER})`, 'giu');

/**
 * What each language calls a guide or a tour, read off the four catalogues on 2026-09-24: the
 * names in `onboarding.flows` and the labels of the guide controls in `onboarding.actions` and
 * `onboarding.settings`.
 *
 * - en «guide(s)», «tour(s)».
 * - it «guida», plural «guide», and «tour».
 * - fr «guide(s)». The tour is «visite» in `flows.intro_tour` and «parcours» in `actions.exitTour`,
 *   `actions.skipCurrentTour` and `settings.groups.core`: both are here.
 * - es «guía(s)», also unaccented — a lost accent must not hide the noun — and «recorrido(s)».
 *
 * «tour(s)» is in every language: it is the word the code uses, and the likeliest to leak into a
 * translation. The adjectives stay out by construction: «guided», «guidato» and «guiado» continue
 * with a letter where the pattern demands a boundary, and «guidé» has «é» where it demands «e».
 * FORMS pins all of this word by word.
 */
const NOUN: Record<Locale, RegExp> = {
    en: nouns('guides?|tours?'),
    it: nouns('guid[ae]|tours?'),
    fr: nouns('guides?|visites?|parcours|tours?'),
    es: nouns('gu[ií]as?|recorridos?|tours?'),
};

/** The guide and tour nouns a text names in its language. Catalogue values and the fixtures below go through this same function. */
function mentions(locale: Locale, text: string): string[] {
    return [...text.normalize('NFC').matchAll(NOUN[locale])].map((match) => match[0]);
}

interface Exception {
    /** A step text key the host renders. Exempt in every language, for its whole text. */
    key: string;
    why: string;
}

/**
 * Step texts that name a guide or a tour and are right to. Adding one is the act of deciding;
 * the gate only notices that a decision is missing.
 */
const REGISTRY: Exception[] = [
    {
        key: 'onboarding.tour.steps.settingsNav.description',
        why: 'Describes what the Settings section does: it holds the preferences and can replay any guide. It does not announce that a guide will start.',
    },
];

/**
 * The scanner's contract word by word, in each language: the nouns it must flag and the neighbours
 * it must not. Fixtures and not catalogue values, because a control whose subject can be edited
 * away is not a control.
 */
const FORMS: Record<Locale, {nouns: string[]; notNouns: string[]}> = {
    en: {nouns: ['guide', 'Guides', 'tour', 'tours'], notNouns: ['guided', 'guidelines', 'tourist', 'detour']},
    it: {nouns: ['guida', 'Guide', 'tour'], notNouns: ['guidato', 'guidata', 'guidare']},
    fr: {nouns: ['guide', 'guides', 'visite', 'visites', 'parcours', 'tour'], notNouns: ['guidé', 'guidée', 'visité', 'parcourir', 'détour']},
    es: {nouns: ['guía', 'guías', 'guia', 'recorrido', 'recorridos', 'tour'], notNouns: ['guiado', 'guiada', 'guiar']},
};

describe('tour and guide steps describe their subject, never another guide (C7 gate)', () => {
    const {keys: stepKeys, unreadable} = readStepKeys(readFileSync(resolve(SRC, HOST), 'utf8'));
    const catalogs = Object.fromEntries(LOCALES.map((locale) => [locale, readCatalog(locale)])) as Record<Locale, Catalog>;
    const text = (locale: Locale, key: string): string => textAt(catalogs[locale], key);
    const line = (locale: Locale, key: string): string => `${locale}.${key}: ${text(locale, key)}`;

    it('reads every step text the overlay host renders', () => {
        // The positive control of the enumeration. "No step names a guide" is also true when the
        // regex collects nothing, the host moves, or the keys stop resolving — the one failure this
        // gate could not otherwise see.
        expect(unreadable, 'A step text key that is not a string literal: extend readStepKeys before trusting this gate.').toEqual([]);
        expect(stepKeys).toContain('onboarding.tour.steps.brokersNav.description');

        const guides = childrenAt(catalogs.en, 'onboarding').filter((name) => childrenAt(catalogs.en, `onboarding.${name}.steps`).length > 0);
        expect(guides).toEqual(expect.arrayContaining(['tour', 'transactionsPageGuide', 'brokerPageGuide', 'fxPageGuide', 'assetPageGuide']));
        const unread = guides.filter((name) => !stepKeys.some((key) => key.startsWith(`onboarding.${name}.steps.`)));
        expect(unread, 'Guides the catalogue declares and the host renders no step of: they are shown somewhere this gate does not read, or they are dead.').toEqual([]);

        const unresolved = stepKeys.flatMap((key) => LOCALES.filter((locale) => text(locale, key).trim() === '').map((locale) => `${locale}.${key}`));
        expect(unresolved, 'Step texts the host renders and a catalogue does not define: the gate cannot read them.').toEqual([]);
    });

    it('knows what each language calls its tour and its guides', () => {
        // The live half of the vocabulary control. `onboarding.flows` is where the product names its
        // flows: wherever English calls one a guide or a tour, every language's pattern must find the
        // noun in that language's name for it. A translator who picks a new word turns this red
        // instead of blinding the scan in silence.
        const named = childrenAt(catalogs.en, 'onboarding.flows').filter((flow) => mentions('en', text('en', `onboarding.flows.${flow}`)).length > 0);
        expect(named).toEqual(expect.arrayContaining(['intro_tour', 'import_guide']));

        const unknown = LOCALES.flatMap((locale) => named.filter((flow) => mentions(locale, text(locale, `onboarding.flows.${flow}`)).length === 0).map((flow) => line(locale, `onboarding.flows.${flow}`)));
        expect(unknown, 'A language names a guide or the tour with a word its pattern does not know: add the word to NOUN.').toEqual([]);
    });

    it('flags the registered Settings mention in every language', () => {
        // The exception doubles as a live positive control: its text names the guides in all four
        // languages, so each pattern has to find its own language's noun in it. If the text stops
        // naming them, move this control to another registered text — FORMS alone is not live.
        const key = 'onboarding.tour.steps.settingsNav.description';
        expect(REGISTRY.map((exception) => exception.key)).toContain(key);
        expect(LOCALES.filter((locale) => mentions(locale, text(locale, key)).length === 0).map((locale) => line(locale, key))).toEqual([]);
    });

    it('lets no step text announce another guide', () => {
        const exempt = new Set(REGISTRY.map((exception) => exception.key));
        const violations = stepKeys.filter((key) => !exempt.has(key)).flatMap((key) => LOCALES.filter((locale) => mentions(locale, text(locale, key)).length > 0).map((locale) => line(locale, key)));

        expect(
            violations,
            violations.length === 0
                ? ''
                : [
                      '',
                      'A tour or guide step names a guide or a tour, and its key is not in the registry in this file.',
                      '',
                      'The rule (R19, and the live review of 2026-09-24): a step DESCRIBES ITS SECTION OR CONTROL;',
                      'it never announces that another guide will start. «A short guide starts when you choose',
                      'Add Broker.» and «A dedicated guide follows the form.» were removed for this reason.',
                      '',
                      'Rewrite the text to say what the section or control does. If the mention is legitimate —',
                      'it describes the control instead of announcing a guide, as «Settings … lets you replay any',
                      'guide» does — add the key to REGISTRY with the reason: an exception without a reason is',
                      'indistinguishable from an oversight.',
                      '',
                      ...violations,
                      '',
                  ].join('\n  '),
        ).toEqual([]);
    });

    it('keeps the registry from rotting', () => {
        // An exception for a text the host no longer renders, or that no longer names a guide in any
        // language, is dead. A registry that keeps dead entries grows into a list nobody trusts, and
        // an untrusted list makes the next real entry look like more of the same.
        const stale = REGISTRY.flatMap(({key}) => {
            if (!stepKeys.includes(key)) return [`${key}: the overlay host no longer renders it`];
            if (LOCALES.every((locale) => mentions(locale, text(locale, key)).length === 0)) return [`${key}: no language names a guide or a tour in it any more`];
            return [];
        });
        expect(stale, stale.length === 0 ? '' : `\n  Registered exceptions that no longer apply — delete them:\n  ${stale.join('\n  ')}\n`).toEqual([]);
    });

    it('matches the nouns and not the words around them', () => {
        // A regression test for the scanner, not for the product. The fixtures go through `mentions`,
        // the function every catalogue value goes through, so this tests the gate and not a copy of
        // it. Narrowing a pattern, or trading the Unicode-aware boundaries back for `\b`, must fail
        // here instead of going quiet.
        const wrong = LOCALES.flatMap((locale) => [
            ...FORMS[locale].nouns.filter((word) => mentions(locale, word).length === 0).map((word) => `${locale}: misses the noun «${word}»`),
            ...FORMS[locale].notNouns.filter((word) => mentions(locale, word).length > 0).map((word) => `${locale}: flags «${word}», which is not the noun`),
        ]);
        expect(wrong).toEqual([]);
    });

    it('gives every registered exception a reason', () => {
        expect(REGISTRY.filter((exception) => exception.why.trim().length < 20).map((exception) => exception.key)).toEqual([]);
    });
});
