/**
 * A conversion that failed for want of an exchange rate, as the endpoints say it (`fx_issues`, CP-11d): the pair in the direction
 * of the conversion and the days that failed, never a text to be read back with a pattern.
 *
 * @module features/signals/fxIssue
 */

import {formatCurrencyPairPlain} from '$lib/utils/currency/currencyFormat';

/** The part of the answer's `FxConversionIssue` the screens read. */
export interface FxIssueLike {
    code: string;
    from_currency: string;
    to_currency: string;
    first_date: string;
    last_date: string;
    count: number;
}

function isRecord(value: unknown): value is Record<string, unknown> {
    return typeof value === 'object' && value !== null && !Array.isArray(value);
}

/** Whether a value is an issue as the answer sends it. */
export function isFxIssue(value: unknown): value is FxIssueLike {
    return isRecord(value) && typeof value.code === 'string' && typeof value.from_currency === 'string' && typeof value.to_currency === 'string' && typeof value.first_date === 'string' && typeof value.last_date === 'string' && typeof value.count === 'number';
}

/** The issues of an answer item (`fx_issues`), the entries that have the shape and nothing else. */
export function fxIssuesOf(item: Record<string, unknown> | undefined): FxIssueLike[] {
    const raw = item && Array.isArray(item.fx_issues) ? item.fx_issues : [];
    return raw.filter(isFxIssue);
}

/** The first price that could not be converted for want of a rate, if the item has one: an event that could not be converted is not a price. */
export function priceRateIssueOf(item: Record<string, unknown> | undefined): FxIssueLike | undefined {
    return fxIssuesOf(item).find((issue) => issue.code === 'rate_not_found');
}

/** The catalogue key and the values of the sentence that says what an issue lost: one day, or the first and last of several. */
export function fxIssueSentence(issue: FxIssueLike): {key: string; values: Record<string, string | number>} {
    const pair = formatCurrencyPairPlain(issue.from_currency, issue.to_currency, 'conversion');
    return issue.count > 1 ? {key: 'chartSettings.fxRateNotFoundRange', values: {pair, first: issue.first_date, last: issue.last_date, count: issue.count}} : {key: 'chartSettings.fxRateNotFound', values: {pair, date: issue.first_date}};
}
