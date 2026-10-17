/**
 * Pure helpers extracted from UnifiedLotsTable.svelte.
 *
 * The table itself is markup plus a `DataTable` wiring; the parts that are pure
 * functions of their input — deriving a lot's primary/secondary state, formatting
 * a quantity, resolving a broker, and the footer's numeric aggregation
 * (sum-ignoring-holes and value-weighted average) — are lifted here so they can be
 * unit tested without a DOM or the `DataTable` component.
 *
 * The cell renderers that emit HTML with Tailwind classes are deliberately left in
 * the component: their output is styling, not logic, and asserting on it would
 * couple the tests to the theme.
 *
 * Two formatters are not pure: `formatLotQuantityMasked` and `formatLotQuantityCell`
 * read the privacy flag (decision D5′), so their output follows the toggle. They are
 * here anyway, because the rule they carry — partial lots keep their open share under
 * privacy — is logic worth a unit test.
 *
 * @financial-math-exception The lots table footer (D-MF6(b)): sums, value-weighted averages and the total and net
 * return over the summed opening value, of the rows the user selects, else of every row the filters keep (on every
 * page). It aggregates what the user chooses, which no backend field can hold; the fixed total of every lot is the
 * backend's (`LotSummarySchema`).
 *
 * @module brokers/lots/unifiedLotsTableHelpers
 */

import type {BrokerLike} from '$lib/utils/broker/brokerColors';
import {formatPercent} from '$lib/utils/core/formatPercent';
import {maskableQuantity, PRIVACY_PLACEHOLDER, shouldMaskAmount} from '$lib/utils/privacy/maskable';
import {uiLocale} from '$lib/stores/app/uiLocale';
import {LOT_QUANTITY_FRACTION_DIGITS} from './lotChartShared';

/** Every state a FIFO lot can carry. */
export type LotState = 'OPEN' | 'PARTIALLY_CLOSED' | 'CLOSED' | 'DISTRIBUTED' | 'IN_TRANSIT' | 'DEGRADED';

/** The single headline state shown as the row's primary badge. */
export type PrimaryLotState = 'OPEN' | 'PARTIALLY_CLOSED' | 'CLOSED' | 'DEGRADED';

/** Secondary states shown as smaller badges, in display order. */
const SECONDARY_STATE_ORDER: LotState[] = ['DISTRIBUTED', 'IN_TRANSIT', 'DEGRADED'];

/**
 * The headline state: partially-closed wins over open, which wins over closed;
 * a lot carrying none of those three is degraded.
 */
export function primaryState(stateList: readonly string[]): PrimaryLotState {
    if (stateList.includes('PARTIALLY_CLOSED')) return 'PARTIALLY_CLOSED';
    if (stateList.includes('OPEN')) return 'OPEN';
    if (stateList.includes('CLOSED')) return 'CLOSED';
    return 'DEGRADED';
}

/** The secondary states present, in fixed display order. */
export function secondaryStates(stateList: readonly string[]): LotState[] {
    return SECONDARY_STATE_ORDER.filter((state) => stateList.includes(state));
}

/** The distinct filter values a row matches: its primary state plus any secondary states. */
export function filterStates(stateList: readonly string[]): LotState[] {
    const normalized = [primaryState(stateList), ...secondaryStates(stateList)];
    return Array.from(new Set(normalized));
}

/**
 * Format a quantity with up to ten fraction digits, the ten a quantity keeps (C-97a, C-97c), or an em dash when absent.
 * Through Intl on the number, so a 10-satoshi lot reads `0.0000001`, never `1e-7`: every lot view writes its
 * quantities here (the table, the WAC chart, the custody modal).
 * `locale` is exposed for deterministic tests; it defaults to the interface locale
 * (`uiLocale()`, M-18), so the table, which passes none, follows the interface.
 */
export function formatLotQuantity(value: number | null, locale: string = uiLocale()): string {
    return value == null ? '—' : value.toLocaleString(locale, {minimumFractionDigits: 0, maximumFractionDigits: LOT_QUANTITY_FRACTION_DIGITS});
}

/**
 * A lot quantity as the table renders it: masked under privacy (decision D5′ — a quantity
 * next to a price is what the user owns), and still an em dash when absent, because masking
 * an absence would claim a quantity the lot does not have.
 */
export function formatLotQuantityMasked(value: number | null, locale: string = uiLocale()): string {
    return value == null ? '—' : maskableQuantity(formatLotQuantity(value, locale));
}

/**
 * The quantity cell of a lot row: the open quantity, or `open / original` for a partially
 * closed lot.
 *
 * Under privacy a partially closed lot keeps its reading key as the open share — `••• (60%)`
 * (decision Q8). Telling a partial lot from a whole one was the reason D5 kept quantities
 * visible; the share discloses no quantity, and percentages stay visible by D6. Without an
 * original to divide by, the cell is the placeholder alone.
 */
export function formatLotQuantityCell(open: number | null, original: number | null, partial: boolean, locale: string = uiLocale()): string {
    if (!partial) return formatLotQuantityMasked(open, locale);
    if (!shouldMaskAmount()) return `${formatLotQuantity(open, locale)} / ${formatLotQuantity(original, locale)}`;
    const share = ratioOrNull(open, original);
    return share == null ? PRIVACY_PLACEHOLDER : `${PRIVACY_PLACEHOLDER} (${formatPercent(share, {scale: 100, signed: false, digits: 0})})`;
}

/** Find a broker by id, or `null` when the id is absent or not in the list. */
export function findBroker(brokerId: number | null | undefined, brokers: ReadonlyArray<BrokerLike>): BrokerLike | null {
    if (brokerId == null) return null;
    return brokers.find((broker) => broker.id === brokerId) ?? null;
}

/** Whether two id lists hold the same set (order-independent, no duplicates assumed). */
export function sameIdSet(left: readonly string[], right: readonly string[]): boolean {
    if (left.length !== right.length) return false;
    const rightSet = new Set(right);
    return left.every((value) => rightSet.has(value));
}

/**
 * Sum a numeric column across rows, skipping missing/non-finite cells. Returns
 * `null` when no row contributed a value (so the footer shows a dash rather than a
 * misleading zero).
 */
export function sumNumeric<T>(footerRows: readonly T[], getValue: (row: T) => number | null): number | null {
    let total = 0;
    let count = 0;
    for (const row of footerRows) {
        const value = getValue(row);
        if (value == null || !Number.isFinite(value)) continue;
        total += value;
        count += 1;
    }
    return count > 0 ? total : null;
}

/**
 * Sum a column only when every row has a finite value; `null` (shown as «—") as soon
 * as one is unknown, or for no rows. A footer total that skipped an unknown lot (a
 * missing FX rate) would read as complete.
 */
export function sumCompleteOrNull<T>(footerRows: readonly T[], getValue: (row: T) => number | null): number | null {
    if (footerRows.length === 0) return null;
    let total = 0;
    for (const row of footerRows) {
        const value = getValue(row);
        if (value == null || !Number.isFinite(value)) return null;
        total += value;
    }
    return total;
}

/**
 * Value-weighted average of a column, weighting by the absolute value of a second
 * column. Rows with a missing/non-finite value or weight, or a zero weight, are
 * skipped. Returns `null` when the total weight is zero.
 */
export function weightedAverage<T>(footerRows: readonly T[], getValue: (row: T) => number | null, getWeight: (row: T) => number | null): number | null {
    let numerator = 0;
    let denominator = 0;
    for (const row of footerRows) {
        const value = getValue(row);
        const weight = getWeight(row);
        if (value == null || weight == null || !Number.isFinite(value) || !Number.isFinite(weight) || weight === 0) continue;
        const absWeight = Math.abs(weight);
        numerator += value * absWeight;
        denominator += absWeight;
    }
    return denominator > 0 ? numerator / denominator : null;
}

/**
 * {@link weightedAverage}, but `null` (shown as «—») as soon as a row that takes part in
 * the average — a finite, non-zero weight — has an unknown or non-finite value. An
 * average that silently dropped a weighted lot (a missing FX rate) would read as complete.
 */
export function weightedAverageCompleteOrNull<T>(footerRows: readonly T[], getValue: (row: T) => number | null, getWeight: (row: T) => number | null): number | null {
    let numerator = 0;
    let denominator = 0;
    for (const row of footerRows) {
        const weight = getWeight(row);
        if (weight == null || !Number.isFinite(weight) || weight === 0) continue;
        const value = getValue(row);
        if (value == null || !Number.isFinite(value)) return null;
        const absWeight = Math.abs(weight);
        numerator += value * absWeight;
        denominator += absWeight;
    }
    return denominator > 0 ? numerator / denominator : null;
}

/**
 * The footer's return ratio: `numerator / denominator`, but only when both are
 * present and the denominator is non-zero; otherwise `null`. Used for total-return
 * and net-total-return over the summed opening value.
 */
export function ratioOrNull(numerator: number | null, denominator: number | null): number | null {
    return numerator != null && denominator != null && denominator !== 0 ? numerator / denominator : null;
}
