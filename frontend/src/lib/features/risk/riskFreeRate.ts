/**
 * The reader's risk-free rate as numbers (RN-21): what a percent may be, the parameters it becomes, the rate an answer used and the key of a text that reads it. Pure, so the
 * request builder reads it without the store's state; the shared value lives in `riskFreeRateStore.svelte.ts`.
 */
/** The engine's bounds (`gt=-1`, `le=10` as an annual fraction), in percent. */
const MIN_EXCLUSIVE_PERCENT = -100;
const MAX_PERCENT = 1000;

/**
 * A percent the engine accepts, or null: finite, above -100 and up to 1000. A value outside would come back as a
 * 422 from every analytic of every page, so a corrupted entry or a wrong keystroke never reaches a request.
 */
export function parseRiskFreePercent(raw: string | number | null | undefined): number | null {
    if (raw === null || raw === undefined) return null;
    if (typeof raw === 'string' && raw.trim() === '') return null;
    const parsed = typeof raw === 'number' ? raw : Number(raw);
    if (!Number.isFinite(parsed) || parsed <= MIN_EXCLUSIVE_PERCENT || parsed > MAX_PERCENT) return null;
    return parsed;
}

/** The two parameters every analytic and rolling signal that declares them takes, from one percent: the one conversion. */
export function riskFreeParameters(percent: number): {risk_free_annual_rate: number; target_annual_return: number} {
    const annual = annualRiskFreeRate(percent);
    return {risk_free_annual_rate: annual, target_annual_return: annual};
}

/** A percent as the annual fraction the engine and the signal plugins take. */
export function annualRiskFreeRate(percent: number): number {
    return percent / 100;
}

/**
 * The annual rate an answer was charged, as the engine echoes it (`metadata.risk_free.annual_rate`), or null when it
 * names none. What a page writes or draws as «the rate used» comes from here, never from the field beside it: between
 * a change and the new answer, the two differ.
 */
export function usedRiskFreeRate(result: unknown): number | null {
    const rate = (result as {metadata?: {risk_free?: {annual_rate?: unknown} | null} | null} | null | undefined)?.metadata?.risk_free?.annual_rate;
    return typeof rate === 'number' && Number.isFinite(rate) ? rate : null;
}

/**
 * A text that reads the rate: its `…WithRate` sister when the answer was charged a rate, the text of today at 0 or
 * when the answer names none (the consultant, 17/11/2026: one family of keys, the same for all of them).
 */
export function withRateKey(key: string, rate: number | null | undefined): string {
    return rate ? `${key}WithRate` : key;
}
