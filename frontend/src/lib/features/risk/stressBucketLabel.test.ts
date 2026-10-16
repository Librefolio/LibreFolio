// @vitest-environment node
/**
 * stressBucketLabel — the reader's name of a stress bucket (Vitest, node: a pure function, its words injected).
 *
 * The asset page's shock editor and the level-4 shock table name every bucket through this one function, so its rule
 * is pinned here, once, on stub words rather than through the stores and the catalogue:
 *
 * - **A sector** reads its emoji and its translated name: `🏥 Sanità`. Until the sector list arrives its emoji is `''`,
 *   and the name stands alone. It used to read ` Sanità`, with a leading space, in the shock table's rows, their
 *   `title` and the editor's `aria-label` (DV-6). A sector the catalogue does not name is shown as written, with no
 *   emoji, even the fallback `❓` the store answers for it once loaded.
 * - **The other buckets**, briefly: `Other` is `common.other` in every dimension, `european_union` the EU group's name,
 *   an asset class its translated type or the code as written, a country its flag and name or, unknown to the
 *   reference data, the code as written, never behind a white flag.
 *
 * The translator stub answers as svelte-i18n's `$t` does when no default is given: the message, or the key itself on a
 * miss. The country stub answers an unknown code as `getCountryInfo` does: an empty alpha-2 and a white flag.
 *
 * The module imports `sectorI18nKey` from `$lib/utils/assetTypes`, which loads the generated API schemas and the
 * sector store: loaded, never called.
 *
 * @module features/risk/stressBucketLabel.test
 */
import {describe, expect, it, vi} from 'vitest';

import type {RiskScenarioDimension} from '$lib/features/risk/riskRequest';

import {stressBucketLabel, type StressBucketVocabulary} from './stressBucketLabel';

/** The catalogue the translator stub reads, in Italian: one message per key a case names. */
const MESSAGES = new Map<string, string>([
    ['common.other', 'Altro'],
    ['risk.stress.europeanUnion', 'Unione europea'],
    ['assets.types.ETF_MONETARY', 'ETF monetario'],
    ['sectors.HealthCare', 'Sanità'],
]);

/** `$t` with no default, as svelte-i18n answers it: the message, or the key itself on a miss. */
const translate: StressBucketVocabulary['translate'] = (key) => MESSAGES.get(key) || key;

/** The reference data: ITA is known; any other code is answered as `getCountryInfo` answers one it does not know. */
const country: StressBucketVocabulary['country'] = (iso3) => (iso3 === 'ITA' ? {iso2: 'IT', flag_emoji: '🇮🇹', name: 'Italia'} : {iso2: '', flag_emoji: '🏳️', name: iso3});

/** The words of a call: the stub catalogue and countries, and a sector store answering `emoji` for every sector. */
function words(emoji: string) {
    const sectorEmoji = vi.fn<(sector: string) => string>(() => emoji);
    const vocabulary: StressBucketVocabulary = {translate, sectorEmoji, country};
    return {vocabulary, sectorEmoji};
}

const DIMENSIONS: readonly RiskScenarioDimension[] = ['asset_class', 'sector', 'geography'];

describe('stressBucketLabel — a sector: its emoji and its name, the name alone while it has no emoji (DV-6)', () => {
    it('reads the emoji and the translated name, the emoji asked for the sector as written', () => {
        const {vocabulary, sectorEmoji} = words('🏥');

        expect(stressBucketLabel('Health Care', 'sector', vocabulary)).toBe('🏥 Sanità');
        expect(sectorEmoji, 'the store is keyed by the backend key, not by the catalogue key').toHaveBeenCalledWith('Health Care');
    });

    it("reads the name alone, with no leading space, while the sector's emoji is '', before the sector list arrives", () => {
        const {vocabulary, sectorEmoji} = words('');

        const label = stressBucketLabel('Health Care', 'sector', vocabulary);
        expect(sectorEmoji, 'barrier: the emoji was asked for, and the store answered nothing').toHaveBeenCalledWith('Health Care');
        expect(label, 'the name alone: no emoji, and no space where it would go').toBe('Sanità');
    });

    it('shows a sector the catalogue does not name as written, with no emoji, even the fallback the store answers once loaded', () => {
        for (const emoji of ['', '❓']) {
            expect(stressBucketLabel('Quantum Computing', 'sector', words(emoji).vocabulary), `the store answering ${JSON.stringify(emoji)}`).toBe('Quantum Computing');
        }
    });
});

describe('stressBucketLabel — the other buckets', () => {
    it.each(DIMENSIONS)('names Other common.other in the %s dimension, with no emoji or flag', (dimension) => {
        expect(stressBucketLabel('Other', dimension, words('📦').vocabulary)).toBe('Altro');
    });

    it('names the EU group from the catalogue', () => {
        expect(stressBucketLabel('european_union', 'geography', words('').vocabulary)).toBe('Unione europea');
    });

    it('names an asset class by its translated type, and shows one the catalogue does not name as written, never its key', () => {
        const {vocabulary} = words('');

        expect(stressBucketLabel('ETF_MONETARY', 'asset_class', vocabulary)).toBe('ETF monetario');
        expect(stressBucketLabel('WARRANT', 'asset_class', vocabulary)).toBe('WARRANT');
    });

    it('names a known country by its flag and name, and shows a code the reference data does not know as written, never behind a white flag', () => {
        const {vocabulary} = words('');

        expect(stressBucketLabel('ITA', 'geography', vocabulary)).toBe('🇮🇹 Italia');
        expect(stressBucketLabel('XKX', 'geography', vocabulary)).toBe('XKX');
    });
});
