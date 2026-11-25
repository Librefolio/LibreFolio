// @vitest-environment node
/**
 * The Rebalancer's result, exposures and cash movements: every text in Italian, French and Spanish (TL-7a of project 67).
 *
 * Why. The Italian walk of TL-7 step 0 found these texts in English on an Italian page: the source catalogues of the
 * Rebalancer held the English text in it, fr and es. The catalogue build fills a missing entry from English, so a copy of
 * English is the only trace an untranslated key leaves: this file reads the SOURCES,
 * `lib/features/tools/portfolio-rebalancer/i18n/<lang>.json`, directly.
 *
 * Contract. Each key of the lot exists, a non-empty string, in en, it, fr and es; its it, fr and es text differs from the
 * English one; and it keeps the English text's ICU placeholders (`{count}`), no more and no fewer.
 *
 * Control. The reader is proven on a neighbour translated before the lot, `exposure.mapAbove`: found in the four
 * languages and different from English in it, fr and es.
 *
 * Red before TL-7a: the 22 keys held the English text in it, fr and es. Registered in
 * `scripts/test_runner/_frontend_utility.py`, in the Vitest list of `front_utility_unit` (action `core-unit`), next to
 * `ownerEmailChangeChecks.test.ts`.
 */
import {readFileSync} from 'node:fs';
import {describe, expect, it} from 'vitest';

const LANGUAGES = ['en', 'it', 'fr', 'es'] as const;
type Lang = (typeof LANGUAGES)[number];
const TRANSLATIONS: readonly Lang[] = ['it', 'fr', 'es'];
const RESULT = 'tools.portfolioRebalancer.planner.result';

/** The keys of the lot, under `RESULT`: the exposures and the cash movements of the result. */
const LOT = [
    'exposure.title',
    'exposure.help',
    'exposure.scope',
    'exposure.legendNow',
    'exposure.legendAfter',
    'exposure.legendTarget',
    'exposure.now',
    'exposure.after',
    'exposure.target',
    'exposure.cash',
    'exposure.belowTarget',
    'exposure.aboveTarget',
    'exposure.onTarget',
    'exposure.showAll',
    'exposure.showFewer',
    'ledger.fields.transfer_in',
    'ledger.fields.transfer_out',
    'ledger.help.transfer_in',
    'ledger.help.transfer_out',
    'ledger.help.funding_in',
    'ledger.help.funding_out',
    'ledger.help.alwaysZeroInvestOnly',
] as const;

/** `lib/features/tools/portfolio-rebalancer/i18n/<lang>.json`, read from disk, never through the generated catalogue. */
function source(lang: Lang): unknown {
    return JSON.parse(readFileSync(new URL(`../features/tools/portfolio-rebalancer/i18n/${lang}.json`, import.meta.url), 'utf8'));
}

/** The value at a dotted key of a nested source; `undefined` when any step is missing or not an object. */
function valueAt(tree: unknown, key: string): unknown {
    let current: unknown = tree;
    for (const step of key.split('.')) {
        if (current === null || typeof current !== 'object') return undefined;
        current = (current as Record<string, unknown>)[step];
    }
    return current;
}

/** The ICU placeholders of a text, sorted: `{count}` → `count`. */
function placeholders(text: string): string[] {
    return [...text.matchAll(/\{(\w+)/g)].map((match) => match[1]).sort();
}

const SOURCES = Object.fromEntries(LANGUAGES.map((lang) => [lang, source(lang)])) as Record<Lang, unknown>;

function text(lang: Lang, key: string): string {
    const value = valueAt(SOURCES[lang], `${RESULT}.${key}`);
    expect(typeof value, `${lang} ${key}`).toBe('string');
    expect((value as string).trim(), `${lang} ${key}`).not.toBe('');
    return value as string;
}

describe('the Rebalancer result, translated (TL-7a)', () => {
    it('reads a neighbour translated before the lot, in the four languages', () => {
        const english = text('en', 'exposure.mapAbove');
        for (const lang of TRANSLATIONS) expect(text(lang, 'exposure.mapAbove'), lang).not.toBe(english);
    });

    it.each(LOT)('%s: in Italian, French and Spanish, not a copy of English, with the same placeholders', (key) => {
        const english = text('en', key);
        for (const lang of TRANSLATIONS) {
            const translated = text(lang, key);
            expect(translated, `${lang} ${key}`).not.toBe(english);
            expect(placeholders(translated), `${lang} ${key}`).toEqual(placeholders(english));
        }
    });
});
