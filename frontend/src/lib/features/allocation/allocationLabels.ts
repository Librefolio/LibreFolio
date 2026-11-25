/**
 * The words of the «Allocazione» tab that come from the data: a class, a bucket, an asset. Pure: the translator is a
 * parameter, so a component test can pass its own.
 *
 * A class is the asset type of what is held (`STOCK`, `BOND`, `ETF`…) or the cash, `Liquidity`: its words are the plural ones of
 * the tab (`allocation.classes.*`). An asset type says the app's own word (`assets.types.*`). What the catalogue does not know
 * shows as it came.
 *
 * @module features/allocation/allocationLabels
 */
import {getAssetTypeIconUrl, LIQUIDITY_KEY, sectorI18nKey} from '$lib/utils/assetTypes';
import type {AllocationChip, ExcludableBucket} from './allocationFilters';
import type {AllocationDimension} from './allocationQuery';

export type Translate = (key: string, options?: {values?: Record<string, string | number>; default?: string}) => string;

/** The key of the class in `assets.types.*` and in the icon map: the cash is `LIQUIDITY`. */
export function classKey(assetClass: string): string {
    return assetClass.toUpperCase();
}

/** A class, in the plural («Stocks»): it stands for everything it holds, so it never shares the name of its first type. */
export function classLabel(t: Translate, assetClass: string): string {
    return t(`allocation.classes.${classKey(assetClass)}`, {default: typeLabel(t, assetClass)});
}

/** An asset type, by the app's own word («Stock», «Stock ETF»). */
export function typeLabel(t: Translate, assetType: string): string {
    if (assetType === 'Unknown') return bucketLabel(t, assetType);
    return t(`assets.types.${classKey(assetType)}`, {default: assetType});
}

export function bucketLabel(t: Translate, bucket: string): string {
    return t(`allocation.bucket.${bucket}`, {default: bucket});
}

export function bucketHint(t: Translate, bucket: ExcludableBucket): string {
    return t(`allocation.bucket.${bucket}Hint`, {default: ''});
}

/** The name a chip stands for: a class, a type, a bucket, or an asset (its number until the answer that names it lands). */
export function chipName(t: Translate, chip: AllocationChip, assetNames: ReadonlyMap<number, string>): string {
    if (chip.kind === 'class') return classLabel(t, chip.value);
    if (chip.kind === 'type') return typeLabel(t, chip.value);
    if (chip.kind === 'bucket') return bucketLabel(t, chip.value);
    return assetNames.get(chip.value) ?? `#${chip.value}`;
}

/** What a chip says: a class or a type kept by its name, a bucket or an asset taken out as «Without …». */
export function chipText(t: Translate, chip: AllocationChip, assetNames: ReadonlyMap<number, string>): string {
    const name = chipName(t, chip, assetNames);
    return chip.kind === 'class' || chip.kind === 'type' ? name : t('allocation.chip.without', {values: {name}});
}

// ---------------------------------------------------------------------------
// Rows of the table and of the pie
// ---------------------------------------------------------------------------

export interface RowLabelDeps {
    t: Translate;
    /** The assets the answer lists, by id. */
    assetNames: ReadonlyMap<number, string>;
    /** The country of an ISO3 code, as the country store says it (its name in the interface language, its flag). */
    country: (iso3: string) => {name: string; flag_emoji: string};
    /** The emoji of a sector key, from the sector store. */
    sectorEmoji: (key: string) => string;
}

/** What a row or a legend entry says: a text and, before it, a glyph (a flag, an emoji) or an icon. */
export interface RowLabel {
    text: string;
    glyph?: string;
    iconUrl?: string;
}

const BUCKET_GLYPH: Record<string, string> = {Unknown: '❓', Other: '📦'};

/** A slice's label in the dimension it belongs to: a sector or an asset type translated, a country by its flag and name, an asset as sent. */
export function sliceLabel(deps: RowLabelDeps, dimension: AllocationDimension, key: string, assetId?: number | null): RowLabel {
    const {t} = deps;
    if (dimension === 'asset' && assetId != null) return {text: deps.assetNames.get(assetId) ?? `#${assetId}`};
    if (key === 'Unknown' || key === 'Other') return {text: bucketLabel(t, key), glyph: BUCKET_GLYPH[key]};
    if (key === 'Liquidity') return {text: typeLabel(t, key), iconUrl: getAssetTypeIconUrl(LIQUIDITY_KEY)};
    if (dimension === 'geography') {
        const info = deps.country(key);
        return {text: info.name, glyph: info.flag_emoji};
    }
    if (dimension === 'sector') {
        const i18nKey = `sectors.${sectorI18nKey(key)}`;
        return {text: t(i18nKey, {default: key.replace(/_/g, ' ')}), glyph: deps.sectorEmoji(key)};
    }
    if (dimension === 'type') return {text: typeLabel(t, key), iconUrl: getAssetTypeIconUrl(key)};
    return {text: key};
}

/** An asset of the detail or of the exclusions, by its name. */
export function assetLabel(deps: RowLabelDeps, assetId: number): RowLabel {
    return {text: deps.assetNames.get(assetId) ?? `#${assetId}`};
}

/**
 * Tailwind classes for a block that writes amounts through the money formatter (`1,234.00 € 🇪🇺 EUR`): hide, after an amount, its flag and
 * its code when the currency has a symbol. Every amount of the tab is in the one currency of the answer, so the flag and the code only
 * repeat themselves in a box or a table cell. A country flag in a label is not an amount's sibling and stays.
 */
export const COMPACT_MONEY = '[&_.currency-amount~.emoji-flag]:hidden [&:has(.currency-symbol)_.currency-amount~.currency-code]:hidden';
