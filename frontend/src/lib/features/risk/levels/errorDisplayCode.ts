/**
 * The code a risk error is worded by: the backend's own code, refined by the remedy of a size limit.
 *
 * Split out of `levelHelpers` for the reason `levelMetadata` and `warningSentence` are — that file
 * sits at its size ceiling — and re-exported from there, so every consumer keeps one door.
 *
 * Why a code alone is not enough here (D379): every size limit of the simulation is one backend
 * code, `resource_limit`, and «too large» does not say what to change. The cure differs from limit
 * to limit — fewer paths or a shorter horizon, a shorter period, Monte Carlo instead of Sobol
 * sampling, and nothing at all past 100 holdings — so the backend names it in `details.remedy`,
 * and each remedy has its own sentence under `risk.errors.<display code>`.
 */

/**
 * The display code of each remedy this build has a sentence for, keyed by `details.remedy`.
 *
 * Written out in full rather than built as `resource_limit_${remedy}`: the i18n audit proves a key
 * used only when its whole name is quoted in the file that builds it, or in a module that file
 * imports. A `Map` rather than an object literal, so a remedy named after an `Object.prototype`
 * member (`constructor`, `toString`) is not mistaken for a known one.
 */
const RESOURCE_LIMIT_DISPLAY_CODES: ReadonlyMap<string, string> = new Map([
    ['paths_or_horizon', 'resource_limit_paths_or_horizon'],
    ['horizon_or_sampling', 'resource_limit_horizon_or_sampling'],
    ['period', 'resource_limit_period'],
    ['positions', 'resource_limit_positions'],
]);

/** The remedies a size refusal can name and this build words, in the order of the table above. */
export const RESOURCE_LIMIT_REMEDIES: readonly string[] = [...RESOURCE_LIMIT_DISPLAY_CODES.keys()];

/**
 * The trimmed code of one error, or `null` when it carries none.
 *
 * Only `resource_limit` is refined, and only by a remedy listed above. Anything else — a remedy a
 * newer backend adds, malformed `details` — keeps the generic «too large» sentence. Reaching for a
 * key this build does not ship would fall back further, to «did not return a result»: a worse
 * sentence, and one that misstates what happened.
 */
export function errorDisplayCode(error: {code?: unknown; details?: unknown} | null | undefined): string | null {
    const code = typeof error?.code === 'string' ? error.code.trim() : '';
    if (code === '') return null;
    if (code !== 'resource_limit') return code;
    const details = error?.details;
    const remedy = details !== null && typeof details === 'object' && !Array.isArray(details) ? (details as {remedy?: unknown}).remedy : undefined;
    const refined = typeof remedy === 'string' ? RESOURCE_LIMIT_DISPLAY_CODES.get(remedy) : undefined;
    return refined ?? code;
}
