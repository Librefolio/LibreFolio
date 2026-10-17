/**
 * The reader's name of a stress bucket.
 *
 * A hypothetical shock moves buckets, and a bucket is a code: an asset type (`ETF_MONETARY`), a
 * sector (`Financials`), a country (`ITA`), the EU group or the catch-all `Other`. The shock
 * editor of the asset page and the level-4 shock table name them the same way, so one bucket never
 * reads differently in two places: the translated asset type, the sector with its emoji, the
 * country with its flag.
 *
 * The words and the reference data are injected, so the function stays pure: the caller reads the
 * catalogue and the reference stores where Svelte tracks them, and reloads them per language.
 */
import type {RiskScenarioDimension} from '$lib/features/risk/riskRequest';
import {sectorI18nKey} from '$lib/utils/assetTypes';
import {translateOr} from '$lib/utils/core/translateOr';

/** What a bucket's name is made of. */
export interface StressBucketVocabulary {
    /** The catalogue, as `$t` reads it. */
    translate: (key: string) => string;
    /** A sector's emoji (`getSectorEmoji`): `''` until the sector list arrives, and the name then stands alone. */
    sectorEmoji: (sector: string) => string;
    /** A country by its ISO alpha-3 code (`getCountryInfo`): an unknown code has an empty `iso2`. */
    country: (iso3: string) => {iso2: string; flag_emoji: string; name: string};
}

/**
 * A code the catalogue or the reference data does not know is shown as written — never as a
 * catalogue key, never behind a white flag — as the PAC planner's category labels do.
 */
export function stressBucketLabel(bucket: string, dimension: RiskScenarioDimension, words: StressBucketVocabulary): string {
    if (bucket === 'Other') return words.translate('common.other');
    if (bucket === 'european_union') return words.translate('risk.stress.europeanUnion');
    if (dimension === 'asset_class') return translateOr(words.translate, `assets.types.${bucket}`, bucket);
    if (dimension === 'sector') {
        const name = translateOr(words.translate, `sectors.${sectorI18nKey(bucket)}`, '');
        if (name === '') return bucket;
        const emoji = words.sectorEmoji(bucket);
        return emoji ? `${emoji} ${name}` : name;
    }
    const country = words.country(bucket);
    return country.iso2 === '' ? bucket : `${country.flag_emoji} ${country.name}`;
}
