import {describe, expect, it} from 'vitest';
import {fxIssueSentence, fxIssuesOf, isFxIssue, priceRateIssueOf} from './fxIssue';

const ISSUE = {code: 'rate_not_found', from_currency: 'USD', to_currency: 'EUR', first_date: '2026-02-02', last_date: '2026-02-02', count: 1};
const EVENT = {...ISSUE, code: 'event_rate_missing'};

describe('fxIssue: the missing exchange rates an endpoint reports as data (CP-11d)', () => {
    it('knows an issue by its shape, and nothing else', () => {
        expect(isFxIssue(ISSUE)).toBe(true);
        for (const other of [null, 'No FX rate found', 42, [ISSUE], {...ISSUE, count: '1'}, {code: 'rate_not_found'}]) expect(isFxIssue(other)).toBe(false);
    });

    it('reads the issues of an item, past entries that are not issues, and no text of `errors`', () => {
        expect(fxIssuesOf({fx_issues: [42, ISSUE, null, EVENT]})).toEqual([ISSUE, EVENT]);
        expect(fxIssuesOf({errors: ['No FX rate found for EUR/USD']})).toEqual([]);
        expect(fxIssuesOf({fx_issues: ISSUE})).toEqual([]);
        expect(fxIssuesOf(undefined)).toEqual([]);
    });

    it('takes the first price that failed, never an event', () => {
        expect(priceRateIssueOf({fx_issues: [EVENT, ISSUE]})).toEqual(ISSUE);
        expect(priceRateIssueOf({fx_issues: [EVENT]})).toBeUndefined();
    });

    it('words one day with its date and several days with their span, the pair in the direction of the conversion', () => {
        const one = fxIssueSentence(ISSUE);
        expect(one.key).toBe('chartSettings.fxRateNotFound');
        expect(one.values).toMatchObject({date: '2026-02-02'});
        expect(String(one.values.pair)).toMatch(/USD.*→.*EUR/);

        const many = fxIssueSentence({...ISSUE, last_date: '2026-02-09', count: 5});
        expect(many.key).toBe('chartSettings.fxRateNotFoundRange');
        expect(many.values).toMatchObject({first: '2026-02-02', last: '2026-02-09', count: 5});

        // the other way round reads the other way round
        expect(String(fxIssueSentence({...ISSUE, from_currency: 'EUR', to_currency: 'USD'}).values.pair)).toMatch(/EUR.*→.*USD/);
    });
});
