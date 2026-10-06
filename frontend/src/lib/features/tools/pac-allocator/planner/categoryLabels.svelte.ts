/**
 * Readable names of exposure categories: the translated Asset type, the sector with its emoji,
 * the country with its flag. The Asset card, the Asset editor and the result report share them,
 * so one category never reads differently in two places. A value the reference data does not
 * know is shown as it is.
 */
import {ensureCountriesLoaded, getCountryInfo, type CountryInfo} from '$lib/stores/reference/countryStore';
import {ensureSectorsLoaded, getSectorEmoji} from '$lib/stores/reference/sectorStore';
import {sectorI18nKey} from '$lib/utils/assetTypes';
import type {ExposureDimension} from './draft.svelte';
import type {PlannerTranslate} from './modeText';

export function exposureCategoryLabel(tr: PlannerTranslate, dimension: ExposureDimension, value: string): string {
    const raw = value.trim();
    if (raw === '') return raw;
    if (dimension === 'asset_type') {
        const text = tr(`assets.types.${raw.toUpperCase()}`, {default: ''});
        return text === '' ? raw : text;
    }
    if (dimension === 'sector') {
        const text = tr(`sectors.${sectorI18nKey(raw)}`, {default: ''});
        return text === '' ? raw : `${getSectorEmoji(raw)} ${text}`;
    }
    // An unknown code comes back with an empty alpha-2 and a white flag: show the code instead.
    const country = findCountry(raw);
    return country.iso2 === '' ? raw : `${country.flag_emoji} ${country.name}`;
}

/** The ISO alpha-3 code in any case, or the catch-all «Other» the country list names as it is. */
function findCountry(raw: string): CountryInfo {
    const exact = getCountryInfo(raw);
    return exact.iso2 !== '' ? exact : getCountryInfo(raw.toUpperCase());
}

/** Loads the country and sector names once per language, then asks the labels to be read again. */
export class CategoryLabels {
    version = $state(0);
    #language: string | null = null;

    load(language: string): void {
        if (language === this.#language) return;
        this.#language = language;
        Promise.all([ensureCountriesLoaded(language), ensureSectorsLoaded()])
            .then(() => {
                this.version += 1;
            })
            .catch(() => {
                // The raw codes stay readable; the next language change tries again.
                this.#language = null;
            });
    }

    text(tr: PlannerTranslate, dimension: ExposureDimension, value: string): string {
        void this.version;
        return exposureCategoryLabel(tr, dimension, value);
    }
}
