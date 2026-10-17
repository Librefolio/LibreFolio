// @vitest-environment node
/**
 * exposureCategoryLabel — the readable name of an exposure category in the PAC planner (Vitest, node). The Asset
 * card, the Asset editor and the result report share it, so one category never reads differently in two places.
 *
 * - **A sector** reads its emoji and its translated name: `🏥 Sanità`. Until the sector list arrives its emoji is `''`,
 *   and the name stands alone, with no leading space (DV-6, the rule of `stressBucketLabel` in the risk panels). A
 *   sector the catalogue does not name is shown as written, with no emoji even when the store has one.
 * - **The value is trimmed** before anything is looked up, and an empty one is no category: `''`, in every dimension.
 * - **An asset type** reads its translated name, whatever the case it is written in, or the value as written.
 * - **A country** reads its flag and name, found by its alpha-3 code in any case, or the value as written when the
 *   reference data does not know it, never behind a white flag.
 *
 * Both reference stores are mocked: `getSectorEmoji` and `getCountryInfo` answer what each case sets, and every other
 * export is a stub that loads nothing, so no case reaches the API client. The translator stub answers as svelte-i18n's
 * `$t` does: the message, or on a miss the `default` it is given (the planner gives `''`), else the key. The module
 * imports `sectorI18nKey` from `$lib/utils/assetTypes`, which loads the generated API schemas: loaded, never called.
 *
 * @module features/tools/pac-allocator/planner/categoryLabels.test
 */
import {beforeEach, describe, expect, it, vi} from 'vitest';

import type {CountryInfo} from '$lib/stores/reference/countryStore';

const {sectorEmoji, countryInfo} = vi.hoisted(() => ({
    sectorEmoji: vi.fn<(key: string) => string>(),
    countryInfo: vi.fn<(iso3: string) => CountryInfo>(),
}));

vi.mock('$lib/stores/reference/sectorStore', () => ({
    getSectorEmoji: sectorEmoji,
    getSectorKeys: () => [],
    sectorEmojiVersion: () => 0,
    ensureSectorsLoaded: async () => {},
}));

vi.mock('$lib/stores/reference/countryStore', () => ({
    getCountryInfo: countryInfo,
    ensureCountriesLoaded: async () => {},
}));

import {exposureCategoryLabel} from './categoryLabels.svelte';
import type {ExposureDimension} from './draft.svelte';
import type {PlannerTranslate} from './modeText';

/** The catalogue the translator stub reads, in Italian: one message per key a case names. */
const MESSAGES = new Map<string, string>([
    ['assets.types.STOCK', 'Azioni'],
    ['sectors.HealthCare', 'Sanità'],
]);

/** `$t` as svelte-i18n answers it: the message, or on a miss the `default` it is given, else the key itself. */
const tr: PlannerTranslate = (key, options) => MESSAGES.get(key) || (options?.default ?? key);

/** The reference data: ITA is known; any other code is answered as `getCountryInfo` answers one it does not know. */
function countryOf(iso3: string): CountryInfo {
    return iso3 === 'ITA' ? {iso3: 'ITA', iso2: 'IT', name: 'Italia', flag_emoji: '🇮🇹'} : {iso3, iso2: '', name: iso3, flag_emoji: '🏳️'};
}

/** The sector store once the list has arrived: Health Care has its emoji. */
const loadedEmoji = (key: string): string => (key === 'Health Care' ? '🏥' : '');

const DIMENSIONS: readonly ExposureDimension[] = ['asset_type', 'sector', 'geography'];

beforeEach(() => {
    // The sector store before the list arrives: no emoji for any key.
    sectorEmoji.mockReset().mockReturnValue('');
    countryInfo.mockReset().mockImplementation(countryOf);
});

describe('exposureCategoryLabel — a sector: its emoji and its name, the name alone while it has no emoji (DV-6)', () => {
    it('reads the emoji and the translated name, the emoji asked for the value as written', () => {
        sectorEmoji.mockImplementation(loadedEmoji);

        expect(exposureCategoryLabel(tr, 'sector', 'Health Care')).toBe('🏥 Sanità');
        expect(sectorEmoji, 'the store is keyed by the backend key, not by the catalogue key').toHaveBeenCalledWith('Health Care');
    });

    it("reads the name alone, with no leading space, while the sector's emoji is '', before the sector list arrives", () => {
        const label = exposureCategoryLabel(tr, 'sector', 'Health Care');

        expect(sectorEmoji, 'barrier: the emoji was asked for, and the store answered nothing').toHaveBeenCalledWith('Health Care');
        expect(label, 'the name alone: no emoji, and no space where it would go').toBe('Sanità');
    });

    it('shows a sector the catalogue does not name as written, with no emoji even when the store has one for it', () => {
        sectorEmoji.mockReturnValue('❓');

        expect(exposureCategoryLabel(tr, 'sector', 'Quantum Computing')).toBe('Quantum Computing');
    });
});

describe('exposureCategoryLabel — the value as written', () => {
    it('trims it before anything is looked up, in every dimension', () => {
        sectorEmoji.mockImplementation(loadedEmoji);

        expect(exposureCategoryLabel(tr, 'sector', '  Health Care \t')).toBe('🏥 Sanità');
        expect(sectorEmoji, 'the emoji is asked for the trimmed value').toHaveBeenLastCalledWith('Health Care');
        expect(exposureCategoryLabel(tr, 'sector', ' Quantum Computing '), 'an untranslated value comes back trimmed').toBe('Quantum Computing');
        expect(exposureCategoryLabel(tr, 'asset_type', ' stock ')).toBe('Azioni');
        expect(exposureCategoryLabel(tr, 'geography', ' ITA ')).toBe('🇮🇹 Italia');
    });

    it.each(DIMENSIONS)("answers an empty value, or one of spaces, with '' in the %s dimension", (dimension) => {
        expect(exposureCategoryLabel(tr, dimension, '')).toBe('');
        expect(exposureCategoryLabel(tr, dimension, '   ')).toBe('');
    });
});

describe('exposureCategoryLabel — an asset type, a country', () => {
    it('names an asset type by its translated name, whatever the case it is written in, and shows one the catalogue does not name as written', () => {
        expect(exposureCategoryLabel(tr, 'asset_type', 'STOCK')).toBe('Azioni');
        expect(exposureCategoryLabel(tr, 'asset_type', 'stock')).toBe('Azioni');
        expect(exposureCategoryLabel(tr, 'asset_type', 'warrant'), 'as written, not upper-cased').toBe('warrant');
    });

    it('names a known country by its flag and name, found by its code in any case, and shows a code the reference data does not know as written, never behind a white flag', () => {
        expect(exposureCategoryLabel(tr, 'geography', 'ITA')).toBe('🇮🇹 Italia');
        expect(exposureCategoryLabel(tr, 'geography', 'ita')).toBe('🇮🇹 Italia');
        expect(exposureCategoryLabel(tr, 'geography', 'XKX')).toBe('XKX');
    });
});
