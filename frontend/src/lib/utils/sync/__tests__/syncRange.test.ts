/**
 * syncRange — the one-week margin around a sync, shared by assets and FX.
 *
 * `padSyncRange` is the asset rule of `buildComparisonSyncRange` lifted into a
 * neutral helper: a week before the first date, a week after the last one, never
 * past today, and the start never after the end. A week either side is what turns
 * a weekend or a bank holiday at the edge of the range into a covered day, because
 * the conversion backfills from the last rate available on or before the date.
 *
 * `buildMissingFxRatesSyncRequest` turns the dashboard's MISSING_FX_RATES issue
 * into the body of POST /fx/currencies/sync. The issue already carries the span of
 * the missing dates (`message_params.date_from/date_to`, the min and max over every
 * affected pair), so the request targets those dates instead of whatever period the
 * page happens to show — the dates that are missing all precede the first stored
 * rate, and a sync of the visible period never reaches them.
 *
 * Every case passes `today` explicitly: the answer must not depend on the day the
 * suite runs.
 */
import {describe, expect, it} from 'vitest';
import {buildMissingFxRatesSyncRequest, padSyncRange, SYNC_MARGIN_DAYS} from '../syncRange';

const TODAY = '2026-10-06';

describe('SYNC_MARGIN_DAYS', () => {
    it('is one week', () => {
        expect(SYNC_MARGIN_DAYS).toBe(7);
    });
});

describe('padSyncRange', () => {
    it('widens a past range by seven calendar days on each side', () => {
        expect(padSyncRange({start: '2022-11-03', end: '2023-06-27'}, {today: TODAY})).toEqual({start: '2022-10-27', end: '2023-07-04'});
    });

    it('caps an end whose margin would cross today at today', () => {
        expect(padSyncRange({start: '2026-09-01', end: '2026-10-02'}, {today: TODAY})).toEqual({start: '2026-08-25', end: TODAY});
    });

    it.each([
        {name: 'today itself', end: TODAY},
        {name: 'a future day', end: '2026-12-31'},
        {name: "the 'max' sentinel", end: 'max'},
    ])('ends today when the end is $name', ({end}) => {
        expect(padSyncRange({start: '2026-09-01', end}, {today: TODAY})).toEqual({start: '2026-08-25', end: TODAY});
    });

    it("passes the 'min' start through untouched", () => {
        expect(padSyncRange({start: 'min', end: '2023-06-27'}, {today: TODAY})).toEqual({start: 'min', end: '2023-07-04'});
    });

    it('never starts after it ends', () => {
        expect(padSyncRange({start: '2026-10-20', end: '2026-10-25'}, {today: TODAY})).toEqual({start: TODAY, end: TODAY});
    });

    it('crosses month, year and leap-day boundaries on the calendar', () => {
        expect(padSyncRange({start: '2023-01-03', end: '2023-12-28'}, {today: TODAY})).toEqual({start: '2022-12-27', end: '2024-01-04'});
        expect(padSyncRange({start: '2024-03-04', end: '2024-03-10'}, {today: TODAY})).toEqual({start: '2024-02-26', end: '2024-03-17'});
        expect(padSyncRange({start: '2024-02-01', end: '2024-02-25'}, {today: TODAY})).toEqual({start: '2024-01-25', end: '2024-03-03'});
    });

    it('honours a different margin', () => {
        expect(padSyncRange({start: '2022-11-03', end: '2023-06-27'}, {days: 3, today: TODAY})).toEqual({start: '2022-10-31', end: '2023-06-30'});
    });

    it('does not mutate the range it is given', () => {
        const range = Object.freeze({start: '2022-11-03', end: '2023-06-27'});

        padSyncRange(range, {today: TODAY});

        expect(range).toEqual({start: '2022-11-03', end: '2023-06-27'});
    });
});

describe('buildMissingFxRatesSyncRequest', () => {
    /** The issue as portfolio_engine emits it for a configured real-provider pair. */
    function issue(overrides: Record<string, unknown> = {}) {
        return {
            affected_fx_pairs: ['EUR-USD'],
            cta_target: 'EUR-USD',
            message_params: {count: 1, date_from: '2022-11-03', date_to: '2023-06-27', dates_count: 9},
            ...overrides,
        };
    }

    it('syncs the missing dates of the issue, a week either side', () => {
        const missing = {affected_fx_pairs: ['EUR-USD'], message_params: {date_from: '2022-11-03', date_to: '2023-06-27', dates_count: 9}};

        expect(buildMissingFxRatesSyncRequest(missing, {today: TODAY})).toEqual({pairs: ['EUR-USD'], start: '2022-10-27', end: '2023-07-04'});
    });

    it('caps the end at today when the last missing date is recent', () => {
        expect(buildMissingFxRatesSyncRequest(issue({message_params: {count: 1, date_from: '2026-09-06', date_to: '2026-10-04', dates_count: 2}}), {today: TODAY})).toEqual({
            pairs: ['EUR-USD'],
            start: '2026-08-30',
            end: TODAY,
        });
    });

    it('normalises every pair to an alphabetical upper-case slug, deduplicated in first-seen order', () => {
        const request = buildMissingFxRatesSyncRequest(issue({affected_fx_pairs: ['USD/EUR', 'EUR-USD', 'gbp-chf']}), {today: TODAY});

        expect(request?.pairs).toEqual(['EUR-USD', 'CHF-GBP']);
    });

    it.each([
        {name: 'an empty list', affected_fx_pairs: []},
        {name: 'null', affected_fx_pairs: null},
        {name: 'nothing', affected_fx_pairs: undefined},
    ])('falls back to the CTA target when the affected pairs are $name', ({affected_fx_pairs}) => {
        const request = buildMissingFxRatesSyncRequest(issue({affected_fx_pairs, cta_target: 'USD-JPY'}), {today: TODAY});

        expect(request).toEqual({pairs: ['JPY-USD'], start: '2022-10-27', end: '2023-07-04'});
    });

    it.each([
        {name: 'no field at all', input: {}},
        {name: 'an empty list and no target', input: {affected_fx_pairs: [], cta_target: null}},
        {name: 'null pairs and an empty target', input: {affected_fx_pairs: null, cta_target: ''}},
    ])('returns null when there is no pair to sync: $name', ({input}) => {
        expect(buildMissingFxRatesSyncRequest(input, {today: TODAY})).toBeNull();
    });

    it.each([
        {name: 'absent params', message_params: undefined},
        {name: 'null params', message_params: null},
        {name: 'params without dates', message_params: {count: 1}},
        {name: 'empty dates', message_params: {count: 1, date_from: '', date_to: ''}},
        {name: 'unparseable dates', message_params: {count: 1, date_from: 'not-a-date', date_to: 'not-a-date'}},
        {name: 'numeric dates', message_params: {count: 1, date_from: 20221103, date_to: 20230627}},
    ])('asks for the full history when the issue carries $name', ({message_params}) => {
        expect(buildMissingFxRatesSyncRequest(issue({message_params}), {today: TODAY})).toEqual({pairs: ['EUR-USD'], start: 'min', end: TODAY});
    });
});
