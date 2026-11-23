/**
 * The words of the «Allocazione» tab that come from the data: a class, a bucket, an asset. Pure: the translator is a
 * parameter, so a component test can pass its own.
 *
 * A class is the asset type of what is held (`STOCK`, `BOND`, `ETF`…) or the cash, `Liquidity`; its words are the app's
 * own (`assets.types.*`, `assets.typeHints.ETF`), and a class the catalogue does not know shows as it came.
 *
 * @module features/allocation/allocationLabels
 */
import type {AllocationChip, ExcludableBucket} from './allocationFilters';

export type Translate = (key: string, options?: {values?: Record<string, string | number>; default?: string}) => string;

/** The key of the class in `assets.types.*` and in the icon map: the cash is `LIQUIDITY`. */
export function classKey(assetClass: string): string {
    return assetClass.toUpperCase();
}

export function classLabel(t: Translate, assetClass: string): string {
    return t(`assets.types.${classKey(assetClass)}`, {default: assetClass});
}

/** What a class also holds: the ETFs of that content, or what an ETF with no content is; empty when there is nothing to say. */
export function classHint(t: Translate, assetClass: string): string {
    const key = classKey(assetClass);
    if (key === 'ETF') return t('assets.typeHints.ETF', {default: ''});
    return t(`allocation.classHint.${key}`, {default: ''});
}

export function bucketLabel(t: Translate, bucket: string): string {
    return t(`allocation.bucket.${bucket}`, {default: bucket});
}

export function bucketHint(t: Translate, bucket: ExcludableBucket): string {
    return t(`allocation.bucket.${bucket}Hint`, {default: ''});
}

/** The name a chip stands for: a class, a bucket, or an asset (its number until the answer that names it lands). */
export function chipName(t: Translate, chip: AllocationChip, assetNames: ReadonlyMap<number, string>): string {
    if (chip.kind === 'class') return classLabel(t, chip.value);
    if (chip.kind === 'bucket') return bucketLabel(t, chip.value);
    return assetNames.get(chip.value) ?? `#${chip.value}`;
}

/** What a chip says: a class kept by its name, a bucket or an asset taken out as «Without …». */
export function chipText(t: Translate, chip: AllocationChip, assetNames: ReadonlyMap<number, string>): string {
    const name = chipName(t, chip, assetNames);
    return chip.kind === 'class' ? name : t('allocation.chip.without', {values: {name}});
}
