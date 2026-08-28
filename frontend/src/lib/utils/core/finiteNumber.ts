/**
 * finiteNumber — narrow an unknown to a *finite* number, else null.
 *
 * A guard for values that are meant to be plotted or measured: it accepts a
 * value only when it is genuinely a finite `number`, rejecting `NaN`,
 * `Infinity`, strings, arrays and everything else. Chart code used this to keep
 * non-finite y-values out of a series (a `NaN` breaks the line, an `Infinity`
 * blows up the axis), under the two names `finiteNumber` and `finiteChartNumber`.
 *
 * ⚠️ Deliberately NOT the same as `safeNumber` (src/lib/types/common.ts), and the
 * two must not be swapped:
 *   - `safeNumber(NaN)` → `NaN`, `safeNumber(Infinity)` → `Infinity` (it only
 *     checks `typeof === 'number'`), and it *unwraps arrays* (`safeNumber([5])`
 *     → `5`). It answers "give me the scalar number in this widened API union".
 *   - `finiteNumber(NaN)` → `null`, `finiteNumber(Infinity)` → `null`,
 *     `finiteNumber([5])` → `null`. It answers "is this a plottable number?".
 * Folding one into the other silently changes behaviour on exactly the edge
 * cases each was written to handle.
 */
export function finiteNumber(value: unknown): number | null {
    return typeof value === 'number' && Number.isFinite(value) ? value : null;
}
