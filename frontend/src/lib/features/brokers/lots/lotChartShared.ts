/**
 * Small pure helpers shared verbatim by the three lot charts.
 *
 * Each of these existed as an identical private copy in two or three of
 * `LotWacPriceChart`, `LotComparisonChart` and `LotGanttChart`. They are the
 * arithmetic and string plumbing the charts hand to ECharts — no canvas, no
 * component state — so they live here and are unit-tested in a plain node
 * environment, exactly where an off-by-one, a bad clamp or a swallowed `-0`
 * would otherwise hide behind a chart nobody can inspect in jsdom.
 *
 * The grid that decided what lands here (same one the Phase-1 dedup used):
 *
 * - `normalizeZero`, `clamp`, `withAlpha` were byte-identical copies → merged.
 *   `withAlpha` has since moved to `$lib/theme/colorAlpha`, the one home of the
 *   charts' alpha helpers (colour workstream R, R-4).
 * - `formatAxisNumber` was byte-identical in the WAC and Comparison charts →
 *   merged, with the machine locale made an explicit (defaulted) parameter so a
 *   test can pin the output; the charts still call it with no locale, so their
 *   behaviour is unchanged.
 * - `resolveBrokerName` had three copies that diverged only in the string shown
 *   for a broker that is present by id but has no name — a caller's choice, so
 *   it became a parameter rather than a reason for three functions.
 *
 * A fourth copy of `clamp` lives in `$lib/utils/layout/dropdownPosition.ts`; it
 * is outside this campaign's area and is left untouched (reported, not moved).
 *
 * `LOT_QUANTITY_FRACTION_DIGITS` is not a chart helper: it is the one number of
 * decimals every lot view writes a quantity with (C-97c), the table's
 * `formatLotQuantity` and the Gantt's `formatQuantity` alike, kept here because
 * both modules already read this light one.
 *
 * @module brokers/lots/lotChartShared
 */

import type {BrokerLike} from '$lib/utils/broker/brokerColors';
import {uiLocale} from '$lib/stores/app/uiLocale';

/**
 * The fraction digits a lot quantity shows: the 10 decimals its column keeps (C-97a), so no lot view drops a digit
 * the database holds (C-97c). The Gantt's plural count reads the same digits, so a tooltip's noun follows its figure.
 */
export const LOT_QUANTITY_FRACTION_DIGITS = 10;

/**
 * `-0` survives arithmetic and prints as "-0.00" / "-0%", which reads as a loss
 * that is not there. Collapse it to a plain `0`; every other value passes
 * through untouched (including `NaN`, which a caller may still want to detect).
 */
export function normalizeZero(value: number): number {
    return Object.is(value, -0) ? 0 : value;
}

/** Constrain `value` to the inclusive `[min, max]` range. */
export function clamp(value: number, min: number, max: number): number {
    return Math.min(max, Math.max(min, value));
}

/**
 * Whether a lot amount row must be shown: an unknown amount (`null`, an FX rate is
 * missing, shown as «—») or a non-zero one. Only a known zero is hidden; hiding an
 * unknown would read as zero. Used by the lot charts, the lots table and the custody modal.
 */
export function isUnknownOrNonZero(value: number | null | undefined): boolean {
    return value == null || value !== 0;
}

/** The sum of two lot amounts, or `null` (unknown) when either is. A known zero is a value. */
export function addOrNull(left: number | null, right: number | null): number | null {
    return left == null || right == null ? null : left + right;
}

/**
 * A compact numeric axis label. Magnitudes at or above 1000 use compact
 * notation ("1.2K"); smaller ones print with up to two decimals, and add a
 * second decimal only for the sub-10 fractional values where a single decimal
 * would read as a rounded-away difference. `-0` is normalized first so a tick
 * at zero never renders as "-0".
 *
 * `locale` defaults to the interface locale (`uiLocale()`, M-18): the figures
 * follow the interface language like the words around them, never the
 * browser's locale. Tests pass an explicit locale to stay deterministic.
 */
export function formatAxisNumber(value: number, locale: string | string[] = uiLocale()): string {
    const normalized = normalizeZero(value);
    const abs = Math.abs(normalized);
    if (abs >= 1000) {
        return new Intl.NumberFormat(locale, {notation: 'compact', maximumFractionDigits: 1}).format(normalized);
    }
    return normalized.toLocaleString(locale, {minimumFractionDigits: abs < 10 && abs % 1 !== 0 ? 2 : 0, maximumFractionDigits: 2});
}

/** How to render a broker id that has no usable name. */
export interface BrokerNameFallbacks {
    /** Shown when `brokerId` is `null` (no broker at all). Defaults to an em dash. */
    missing?: string;
    /** Shown when the id is present but not found, or found without a name.
     *  Defaults to `#<id>`; the WAC chart passes `Broker <id>`. */
    unknown?: (brokerId: number) => string;
}

/**
 * Resolve a broker id to a display name against the broker list, with explicit
 * fallbacks for the two "no name" cases. Pure: the broker list is passed in, so
 * this is testable without the component.
 */
export function resolveBrokerName(brokerId: number | null, brokers: ReadonlyArray<BrokerLike>, fallbacks: BrokerNameFallbacks = {}): string {
    const {missing = '—', unknown = (id: number) => `#${id}`} = fallbacks;
    if (brokerId == null) return missing;
    return brokers.find((broker) => broker.id === brokerId)?.name ?? unknown(brokerId);
}
