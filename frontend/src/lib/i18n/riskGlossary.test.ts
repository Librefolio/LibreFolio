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
