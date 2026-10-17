/**
 * The message of a save in the asset's data editor (O-8): what was saved, in the interface language.
 *
 * The editor saves prices (upserted, deleted, skipped as invalid) and events (saved, deleted) and tells the user in one
 * toast: «Asset data: 12 prices saved, 1 event deleted». Each part is an ICU plural of the catalogue, in the order of the
 * save; nothing to report gives null (a fully blocked delete already has its own warning).
 */

/** What one save did. */
export interface AssetDataSaveCounts {
    pricesSaved: number;
    /** Prices the server left out, each named in the save's warning (X-R46). */
    pricesRefused?: number;
    pricesDeleted: number;
    /** Price rows left out because invalid. */
    pricesSkipped: number;
    eventsDeleted: number;
    eventsSaved: number;
}

/** The catalogue lookup: `$t` (or `get(_)`) with ICU values. */
export type Translate = (key: string, options?: {values: Record<string, string | number>}) => string;

/**
 * The toast message of a save, or null when it did nothing to report. Parts, in this order and only when non-zero:
 * prices saved, prices refused, prices deleted, prices skipped, events deleted, events saved; joined by «, » inside
 * `assets.dataEditor.saved`.
 */
export function assetDataSaveSummary(counts: AssetDataSaveCounts, translate: Translate): string | null {
    const parts: string[] = [];
    if (counts.pricesSaved > 0) parts.push(translate('assets.dataEditor.pricesSaved', {values: {count: counts.pricesSaved}}));
    const refused = counts.pricesRefused ?? 0;
    if (refused > 0) parts.push(translate('assets.dataEditor.pricesRefused', {values: {count: refused}}));
    if (counts.pricesDeleted > 0) parts.push(translate('assets.dataEditor.pricesDeleted', {values: {count: counts.pricesDeleted}}));
    if (counts.pricesSkipped > 0) parts.push(translate('assets.dataEditor.pricesSkipped', {values: {count: counts.pricesSkipped}}));
    if (counts.eventsDeleted > 0) parts.push(translate('events.deleteSuccess', {values: {n: counts.eventsDeleted}}));
    if (counts.eventsSaved > 0) parts.push(translate('assets.dataEditor.eventsSaved', {values: {count: counts.eventsSaved}}));
    if (parts.length === 0) return null;
    return translate('assets.dataEditor.saved', {values: {details: parts.join(', ')}});
}
