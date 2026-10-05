/**
 * A share of the portfolio, worded so that a small one is never printed as zero
 * (developer's decision of 01/10/2026: «per le quote sotto l'1% metti un decimale o due»).
 *
 * A fixed number of decimals hides small shares: with none, 0.4 % of net worth in cash
 * reads «0 %», which is a claim the data does not make. The digits therefore follow the
 * size of the share, measured on its magnitude:
 * - from 1 % up, the caller's own format (`baseDigits`), so large figures do not change;
 * - below 1 %, at least one decimal; below 0.1 %, at least two;
 * - a share that two decimals would still round to zero reads «< 0.01%» («> -0.01%» when
 *   negative), so only a true zero prints as zero. The space after the sign is a no-break
 *   space: inside a sentence, «<» must not end a line alone.
 *
 * `fraction` is a share as the payload carries it (0.31 is 31 %). Anything that is not a
 * finite number prints the same placeholder as `formatPercent`. `baseDigits` stops at two:
 * with more, «at least two decimals» and «< 0.01%» would no longer describe one rule.
 */
import {formatPercent} from '$lib/utils/core/formatPercent';

const TINY_POSITIVE = '<\u00A00.01%';
const TINY_NEGATIVE = '>\u00A0-0.01%';

export function formatShare(fraction: number | null | undefined, baseDigits: 0 | 1 | 2): string {
    // `=== 0` holds for `-0` too, which `formatPercent` prints as a plain zero.
    if (fraction == null || !Number.isFinite(fraction) || fraction === 0) return formatPercent(fraction, {scale: 100, signed: false, digits: baseDigits});
    const percent = Math.abs(fraction * 100);
    if (percent >= 1) return formatPercent(fraction, {scale: 100, signed: false, digits: baseDigits});
    // Decided on the same `toFixed` that prints the figure, so «< 0.01%» appears exactly
    // when the two-decimal figure would read zero, never one ulp early or late.
    if (Number(percent.toFixed(2)) === 0) return fraction > 0 ? TINY_POSITIVE : TINY_NEGATIVE;
    return formatPercent(fraction, {scale: 100, signed: false, digits: Math.max(baseDigits, percent >= 0.1 ? 1 : 2)});
}
