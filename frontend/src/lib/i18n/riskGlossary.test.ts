// @vitest-environment node
/**
 * riskGlossary — one measure, one name, wherever the Risk surfaces name it (Vitest, node). T-CL, D8, 13/10/2026.
 *
 * Why. The maximum drawdown is named twice in the catalogues: by the legacy panel's KPI card
 * (`risk.metrics.maxDrawdown`, `RiskAnalysisPanel.svelte`) and by the technical name under L1's card
 * (`risk.levels.l1.technical.worst`, `L1HowMuchItHurts.svelte`). A reader who meets both on the same
 * Dashboard reads two words for one figure and has to wonder whether they are two figures. Today the two
 * agree in English and Spanish, and not in Italian («Drawdown massimo» against «Massimo drawdown») nor in
 * French («Repli maximal» against «Perte maximale»).
 *
 * Gate. Each pair of keys that name one measure must read byte for byte the same in every catalogue. The
 * gate does not choose the word — the glossary does, and the cure writes it into the catalogue sources
 * with `dev.py i18n update` — it only refuses two words for one measure.
 *
 * Expected. Red today, naming `it` and `fr`; green once the two keys agree in all four languages.
 *
 * Controls. A pair missing from a catalogue is reported as missing rather than compared, because two
 * absent keys are equal and would pass. The comparison is proved in both directions on synthetic
 * catalogues: an agreeing pair passes, a disagreeing one is listed, a missing one is listed as missing.
 *
 * Read like `catalogIcuLocale.test.ts` reads them: the four generated catalogues (`src/lib/i18n/<lang>.json`,
 * built from their sources by Vitest's global setup), typed on the app's locale list, so a fifth locale
 * without a catalogue here fails `front check`.
 *
 * Second gate, same catalogues — «Other» in the stress rules (T-ISO + T-FB lot, 13/10/2026). After T-SHK the
 * shock names its fallback bucket with `common.other` («Altro», «Autre», «Otro»), but three texts of the stress
 * audit still name it in English in Italian, French and Spanish: `risk.stress.rules.other` («Fallback Other»),
 * `risk.stress.rules.missing_metadata_other` («… → Other») and the sentence `risk.stress.missingMetadataOther`
 * («… trattato come Other al 100%»). Expected: none of the three contains the English word «Other» outside the
 * English catalogue, and each contains its catalogue's own `common.other`, written as that key writes it. Red
 * today in it, fr and es; English names the bucket «Other», its own `common.other`, and stays (guard). Its
 * controls are synthetic catalogues, like the first gate's.
 *
 * Registered in `scripts/test_runner/_frontend_utility.py`, in the Vitest list of `front_utility_unit`
 * (action `core-unit`), next to `catalogIcuLocale.test.ts`.
 */
import {describe, expect, it} from 'vitest';
import type {SupportedLocale} from './index';
import en from './en.json';
import itCatalogue from './it.json';
import fr from './fr.json';
import es from './es.json';

/** Typed on the app's locale list, so a fifth locale without a catalogue here fails `front check`. */
const CATALOGUES: Record<SupportedLocale, unknown> = {en, it: itCatalogue, fr, es};

/** One measure, and the keys that name it on the Risk surfaces. */
interface GlossaryEntry {
    measure: string;
    keys: readonly string[];
}

const GLOSSARY: readonly GlossaryEntry[] = [
    {
        measure: 'maximum drawdown',
        // The legacy panel's KPI card, and the technical name under L1's card (D8).
        keys: ['risk.metrics.maxDrawdown', 'risk.levels.l1.technical.worst'],
    },
];

function at(catalogue: unknown, key: string): unknown {
    return key.split('.').reduce<unknown>((node, part) => (node !== null && typeof node === 'object' ? (node as Record<string, unknown>)[part] : undefined), catalogue);
}

/** Every key of the glossary that a catalogue lacks, or holds as something other than a non-empty sentence. */
function missingNames(catalogues: Readonly<Record<string, unknown>>, glossary: readonly GlossaryEntry[]): string[] {
    return Object.entries(catalogues).flatMap(([code, catalogue]) =>
        glossary.flatMap((entry) =>
            entry.keys
                .filter((key) => {
                    const sentence = at(catalogue, key);
                    return typeof sentence !== 'string' || sentence.trim() === '';
                })
                .map((key) => `${code}: ${key}`),
        ),
    );
}

/** Every measure a catalogue names in more than one way, with the words, one line per catalogue and measure. */
function disagreements(catalogues: Readonly<Record<string, unknown>>, glossary: readonly GlossaryEntry[]): string[] {
    return Object.entries(catalogues).flatMap(([code, catalogue]) =>
        glossary.flatMap((entry) => {
            const names = entry.keys.map((key) => at(catalogue, key));
            // A missing key is missingNames's to report: two absent keys would "agree".
            if (names.some((name) => typeof name !== 'string')) return [];
            return new Set(names).size === 1 ? [] : [`${code}: the ${entry.measure} is named ${entry.keys.map((key, index) => `«${String(names[index])}» (${key})`).join(' and ')}`];
        }),
    );
}

describe('riskGlossary — the gate’s own controls', () => {
    const PAIR: readonly GlossaryEntry[] = [{measure: 'synthetic measure', keys: ['a.first', 'b.second']}];

    it('passes a pair that agrees, and lists one that does not, with its catalogue and both words', () => {
        expect(disagreements({xx: {a: {first: 'Same'}, b: {second: 'Same'}}}, PAIR)).toEqual([]);
        expect(disagreements({xx: {a: {first: 'One'}, b: {second: 'Other'}}}, PAIR)).toEqual(['xx: the synthetic measure is named «One» (a.first) and «Other» (b.second)']);
    });

    it('lists a missing or empty name as missing instead of comparing it: two absent keys are equal', () => {
        const catalogues = {xx: {a: {first: 'Same'}}, yy: {a: {first: ''}, b: {second: ''}}, zz: {}};
        expect(missingNames(catalogues, PAIR)).toEqual(['xx: b.second', 'yy: a.first', 'yy: b.second', 'zz: a.first', 'zz: b.second']);
        expect(disagreements(catalogues, PAIR), 'a pair with a missing name was compared').toEqual([]);
    });
});

describe('riskGlossary — one measure, one name, in every catalogue (T-CL, D8)', () => {
    it('has every name of the glossary in every catalogue', () => {
        expect(missingNames(CATALOGUES, GLOSSARY), 'a name of the glossary is missing from a catalogue: the comparison below would not be about it').toEqual([]);
    });

    it('names the maximum drawdown alike on the legacy panel’s KPI card and under L1’s card, in every language', () => {
        expect(disagreements(CATALOGUES, GLOSSARY), 'risk.metrics.maxDrawdown and risk.levels.l1.technical.worst name one measure in two ways: align them on the glossary term in the catalogue sources (dev.py i18n update)').toEqual([]);
    });
});

/** The texts of the stress audit that name the fallback bucket: the two rules and the sentence under an asset without metadata. */
const OTHER_TEXTS = ['risk.stress.rules.other', 'risk.stress.rules.missing_metadata_other', 'risk.stress.missingMetadataOther'] as const;

/** The English word for the bucket, as a word: «Otro» or «Autre» do not contain it, «Other» and «Other fallback» do. */
const ENGLISH_OTHER = /\bOther\b/;

/**
 * Every text of `keys` that does not name the bucket in its catalogue's language, one line per catalogue and key:
 * missing (or empty), still saying the English «Other» outside English, or not containing the catalogue's own
 * `common.other` as that key writes it.
 */
function bucketNameProblems(catalogues: Readonly<Record<string, unknown>>, keys: readonly string[]): string[] {
    return Object.entries(catalogues).flatMap(([code, catalogue]) => {
        const other = at(catalogue, 'common.other');
        return keys.flatMap((key) => {
            const text = at(catalogue, key);
            if (typeof text !== 'string' || text.trim() === '') return [`${code}: ${key} is missing`];
            const problems: string[] = [];
            if (code !== 'en' && ENGLISH_OTHER.test(text)) problems.push('says the English «Other»');
            if (typeof other !== 'string' || !text.includes(other)) problems.push(`does not name the bucket «${String(other)}» (common.other)`);
            return problems.length === 0 ? [] : [`${code}: ${key} «${text}» ${problems.join(' and ')}`];
        });
    });
}

describe('riskGlossary — the «Other» gate’s own controls', () => {
    const KEYS = ['r.rule'] as const;

    it('passes a text naming the bucket with common.other, and lists one in English, one naming nothing, one missing', () => {
        expect(bucketNameProblems({xx: {common: {other: 'Altro'}, r: {rule: 'Ripiego su Altro'}}, en: {common: {other: 'Other'}, r: {rule: 'Other fallback'}}}, KEYS)).toEqual([]);
        expect(bucketNameProblems({xx: {common: {other: 'Altro'}, r: {rule: 'Fallback Other'}}, yy: {common: {other: 'Autre'}, r: {rule: 'Repli'}}, zz: {common: {other: 'Otro'}}}, KEYS)).toEqual([
            'xx: r.rule «Fallback Other» says the English «Other» and does not name the bucket «Altro» (common.other)',
            'yy: r.rule «Repli» does not name the bucket «Autre» (common.other)',
            'zz: r.rule is missing',
        ]);
    });
});

describe('riskGlossary — the stress rules name the «Other» bucket in the language of each catalogue', () => {
    it('has common.other in every catalogue, the English word only in English (premise)', () => {
        const others = Object.fromEntries(Object.entries(CATALOGUES).map(([code, catalogue]) => [code, at(catalogue, 'common.other')]));
        expect(
            Object.entries(others).filter(([code, other]) => typeof other !== 'string' || other.trim() === '' || (code !== 'en' && ENGLISH_OTHER.test(other))),
            'common.other is missing, or English outside English: the gate below would not be about the bucket’s name',
        ).toEqual([]);
    });

    it('names the bucket with the catalogue’s own common.other — «Altro», «Autre», «Otro» — never with the English «Other», in it, fr and es', () => {
        const translated = Object.fromEntries(Object.entries(CATALOGUES).filter(([code]) => code !== 'en'));
        expect(bucketNameProblems(translated, OTHER_TEXTS), 'a stress text still names the bucket «Other» in English: write the catalogue’s common.other in its place (dev.py i18n update)').toEqual([]);
    });

    it('English names it «Other», its own common.other, in the three texts (guard)', () => {
        expect(bucketNameProblems({en: CATALOGUES.en}, OTHER_TEXTS), 'an English stress text no longer names the bucket').toEqual([]);
    });
});
