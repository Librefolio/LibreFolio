/**
 * eligibility — Risk's verdict on each asset of the laboratory's catalogue, and
 * how the laboratory words it.
 *
 * The verdict comes from Risk's eligibility engine (`POST /api/v1/risk/eligibility`)
 * and is never computed here: whether an asset has enough prices in the period is
 * a calculation, and calculations live in the backend. This module only reads the
 * answer and turns it into sentences.
 *
 * An asset with **no** verdict — not asked yet, or the engine failed — is
 * selectable. A missing answer never locks an asset out.
 */
import type {z} from 'zod';
import type {schemas} from '$lib/api';

export type EligibilityLevel = z.infer<typeof schemas.RiskEligibilityLevel>;
export type EligibilityReason = z.infer<typeof schemas.RiskEligibilityReason>;
export type AssetEligibilityItem = z.infer<typeof schemas.RiskAssetEligibility>;

/** One answer of the engine, for the whole catalogue and one period. */
export interface EligibilityVerdicts {
    items: ReadonlyMap<number, AssetEligibilityItem>;
    /** The engine's thresholds, sent with the answer: the sentences quote them rather than copy them. */
    minQuotes: number;
    staleDays: number;
}

export const EMPTY_VERDICTS: EligibilityVerdicts = {items: new Map(), minQuotes: 0, staleDays: 0};

/** How many assets the engine accepts in one request. */
export const ELIGIBILITY_BATCH = 500;

/** A verdict as the laboratory shows it: the level, the engine's codes and one sentence per code. */
export interface EligibilityView {
    level: EligibilityLevel;
    codes: readonly string[];
    texts: readonly string[];
}

type Translate = (key: string, options?: {values?: Record<string, string | number>}) => string;

/** Whether an asset may enter the analysis. No verdict means yes. */
export function isSelectable(verdicts: EligibilityVerdicts, assetId: number): boolean {
    return verdicts.items.get(assetId)?.level !== 'ineligible';
}

/** Split ids into requests the engine accepts. An empty list yields no request at all: the engine rejects it. */
export function eligibilityBatches(assetIds: readonly number[], size: number = ELIGIBILITY_BATCH): number[][] {
    // A size below one, or not a number at all, would never advance the loop or would ask for nothing.
    const step = Math.max(1, Math.floor(size) || 1);
    const batches: number[][] = [];
    for (let start = 0; start < assetIds.length; start += step) batches.push(assetIds.slice(start, start + step));
    return batches;
}

/** Merge the answers of several batches into one verdict. */
export function mergeEligibilityAnswers(answers: readonly {items: readonly AssetEligibilityItem[]; min_quotes: number; stale_days: number}[]): EligibilityVerdicts {
    if (answers.length === 0) return EMPTY_VERDICTS;
    const items = new Map<number, AssetEligibilityItem>();
    for (const answer of answers) for (const item of answer.items) items.set(item.asset_id, item);
    return {items, minQuotes: answers[0].min_quotes, staleDays: answers[0].stale_days};
}

/**
 * A calendar day in the reader's language. The engine's dates are plain days,
 * so they are read as UTC: a local midnight would move them by one in some zones.
 */
export function dayFormatter(locale: string | undefined): (isoDay: string) => string {
    const format = new Intl.DateTimeFormat(locale, {day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC'});
    return (isoDay) => {
        const day = new Date(`${isoDay}T00:00:00Z`);
        // The parser rolls an impossible day over ("2024-02-30" → 1 March): a day that does not
        // survive the round trip is echoed as it came, never shown as a different real one.
        if (Number.isNaN(day.getTime()) || day.toISOString().slice(0, 10) !== isoDay) return isoDay;
        return format.format(day);
    };
}

/** A translation the catalogue does not have comes back as its own key: that must never reach the screen. */
function worded(text: string): string | null {
    return text && !text.startsWith('risk.eligibility.') ? text : null;
}

/**
 * One reason as a sentence, or `null` when it cannot be worded.
 *
 * Every key is written out in full, so the i18n audit sees it. The switch is
 * exhaustive over the generated enum: a reason the engine adds later fails
 * `front check` right here until someone words it.
 */
export function reasonText(reason: EligibilityReason, item: AssetEligibilityItem, verdicts: EligibilityVerdicts, currency: string, t: Translate, formatDay: (isoDay: string) => string): string | null {
    const firstQuote = typeof item.first_quote === 'string' ? formatDay(item.first_quote) : '—';
    const lastQuote = typeof item.last_quote === 'string' ? formatDay(item.last_quote) : '—';
    switch (reason) {
        case 'no_price_history':
            return worded(t('risk.eligibility.reasons.no_price_history'));
        case 'no_prices':
            return worded(t('risk.eligibility.reasons.no_prices'));
        case 'too_few_quotes':
            return worded(t('risk.eligibility.reasons.too_few_quotes', {values: {minQuotes: verdicts.minQuotes, count: item.quotes_in_period}}));
        case 'missing_fx':
            return worded(t('risk.eligibility.reasons.missing_fx', {values: {currency}}));
        case 'starts_late':
            return worded(t('risk.eligibility.reasons.starts_late', {values: {date: firstQuote}}));
        case 'stale_at_end':
            return worded(t('risk.eligibility.reasons.stale_at_end', {values: {date: lastQuote, days: verdicts.staleDays}}));
        default: {
            // Unreachable while the switch covers the generated enum; at runtime a code the
            // client does not know yet is not worded here, and the level's label stands in.
            const unworded: never = reason;
            void unworded;
            return null;
        }
    }
}

/**
 * A verdict ready for the screen. A code the frontend does not know (the engine
 * moved ahead of the generated client) or a sentence the catalogue lacks falls
 * back to the level's own label: never a raw key, never an empty tooltip.
 */
export function describeEligibility(item: AssetEligibilityItem, verdicts: EligibilityVerdicts, currency: string, t: Translate, formatDay: (isoDay: string) => string): EligibilityView {
    const codes = item.reasons ?? [];
    const texts = codes.map((code) => reasonText(code, item, verdicts, currency, t, formatDay)).filter((text): text is string => text !== null);
    if (texts.length === 0 && item.level !== 'eligible') {
        const fallback = item.level === 'ineligible' ? worded(t('risk.eligibility.levels.ineligible')) : worded(t('risk.eligibility.levels.warning'));
        if (fallback) texts.push(fallback);
    }
    return {level: item.level, codes, texts};
}
