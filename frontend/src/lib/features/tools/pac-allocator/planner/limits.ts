/**
 * The minimum and the maximum of a target entry, as the user types them (F2 of project 67, contract 2.0.0 §5.2).
 *
 * One reading of the text, used by the request, the local problems, the cell's red state and the review count:
 * «500» is an amount in the valuation currency, «35%» a share of the plan's total, an empty field is no limit.
 * No calculation here: a share and an amount are compared only by the backend, which knows the Tool's reference.
 */
import {canonicalInput, compareDecimal, decimalSign} from '$lib/utils/core/exactDecimal';

export type LimitSide = 'minimum' | 'maximum';

/** The two fields of one entry, as typed. A missing side is an empty field. */
export interface DraftLimits {
    minimum: string;
    maximum: string;
}

/** `amount`: a decimal in the valuation currency. `share`: a percentage from 0 (the wire sends it as a fraction). */
type ParsedLimit = {kind: 'amount'; value: string} | {kind: 'share'; percent: string};

/** `null` for an empty field, `'invalid'` for text that is not a number from 0, with or without a final «%». */
export function parseLimit(text: string | undefined): ParsedLimit | null | 'invalid' {
    const trimmed = (text ?? '').trim();
    if (trimmed === '') return null;
    const share = trimmed.endsWith('%');
    const value = canonicalInput(share ? trimmed.slice(0, -1) : trimmed);
    if (value === null || decimalSign(value) === -1) return 'invalid';
    return share ? {kind: 'share', percent: value} : {kind: 'amount', value};
}

/** True for a share above 100%: a limit can never be more than the whole total. */
export function shareAboveHundred(limit: ParsedLimit | null | 'invalid'): boolean {
    return limit !== null && limit !== 'invalid' && limit.kind === 'share' && compareDecimal(limit.percent, '100') === 1;
}

/** True when both limits are in the same form and the minimum is above the maximum. Different forms: the backend decides. */
export function limitsConflict(limits: DraftLimits | undefined): boolean {
    const minimum = parseLimit(limits?.minimum);
    const maximum = parseLimit(limits?.maximum);
    if (minimum === null || maximum === null || minimum === 'invalid' || maximum === 'invalid' || minimum.kind !== maximum.kind) return false;
    const [low, high] = minimum.kind === 'share' ? [minimum.percent, (maximum as {percent: string}).percent] : [minimum.value, (maximum as {value: string}).value];
    return compareDecimal(low, high) === 1;
}

/** True when the entry has at least one limit typed. */
export function hasLimit(limits: DraftLimits | undefined): boolean {
    return (limits?.minimum ?? '').trim() !== '' || (limits?.maximum ?? '').trim() !== '';
}
