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
 * @module brokers/lots/lotChartShared
 */

import type {BrokerLike} from '$lib/utils/broker/brokerColors';

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
 * Apply an alpha channel to a color the charts already computed. Two shapes are
 * understood:
 *
 * - `hsl(...)` → `hsla(..., alpha)` — the alpha is inserted literally, so the
 *   caller owns its range.
 * - `#rrggbb` → `#rrggbbaa` — the alpha is clamped to `[0, 1]`, scaled to a byte
 *   and appended as two hex digits.
 *
 * Anything else (a named color, an already-rgba string, an `#rgb` shorthand) is
 * returned unchanged: better a fully opaque color than a corrupted one.
 */
export function withAlpha(color: string, alpha: number): string {
    const hslMatch = color.match(/^hsl\((.+)\)$/i);
    if (hslMatch) return `hsla(${hslMatch[1]}, ${alpha})`;
    const hexMatch = color.match(/^#([0-9a-f]{6})$/i);
    if (hexMatch)
        return `${color}${Math.round(clamp(alpha, 0, 1) * 255)
            .toString(16)
            .padStart(2, '0')}`;
    return color;
}

/**
 * A compact numeric axis label. Magnitudes at or above 1000 use compact
 * notation ("1.2K"); smaller ones print with up to two decimals, and add a
 * second decimal only for the sub-10 fractional values where a single decimal
 * would read as a rounded-away difference. `-0` is normalized first so a tick
 * at zero never renders as "-0".
 *
 * `locale` defaults to `undefined` — the machine locale, which is what both
 * charts deliberately use for numbers (as opposed to `$currentLanguage`, which
 * they use for words). Tests pass an explicit locale to stay deterministic.
 */
export function formatAxisNumber(value: number, locale?: string | string[]): string {
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
