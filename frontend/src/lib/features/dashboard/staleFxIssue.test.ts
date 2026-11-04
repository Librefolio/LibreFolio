/**
 * The «old exchange rate» banner: `data_quality.stale_fx_pairs` of the report becomes one banner row, like the old prices.
 */
import {describe, expect, it} from 'vitest';
import {buildMissingFxRatesSyncRequest} from '$lib/utils/sync/syncRange';
import {pairsStillStale, staleFxIssue} from './staleFxIssue';

const TODAY = '2026-10-28';

describe('staleFxIssue', () => {
    it('gives no row when no pair is stale', () => {
        expect(staleFxIssue(undefined, TODAY)).toBeNull();
        expect(staleFxIssue(null, TODAY)).toBeNull();
        expect(staleFxIssue([], TODAY)).toBeNull();
    });

    it('is one warning row for all the stale pairs, oldest first as the report orders them', () => {
        const issue = staleFxIssue(
            [
                {pair: 'USD/EUR', last_rate_date: '2026-08-01', stale_days: 88},
                {pair: 'CHF/EUR', last_rate_date: '2026-09-20', stale_days: 38},
            ],
            TODAY,
        );
        expect(issue).toMatchObject({
            domain: 'portfolio',
            code: 'STALE_FX',
            severity: 'warning',
            message_i18n_key: 'dataQuality.staleFx',
            count: 2,
            affected_fx_pairs: ['USD/EUR', 'CHF/EUR'],
            cta_action: 'sync_stale_fx',
            group_key: 'stale_fx',
        });
        expect(issue?.message_params).toMatchObject({count: 2, days: 88});
    });

    it('asks the sync for every stale pair, from the oldest stored rate to today', () => {
        const issue = staleFxIssue(
            [
                {pair: 'USD/EUR', last_rate_date: '2026-08-01', stale_days: 88},
                {pair: 'CHF/EUR', last_rate_date: '2026-09-20', stale_days: 38},
            ],
            TODAY,
        );
        expect(issue).not.toBeNull();
        expect(buildMissingFxRatesSyncRequest(issue!, {today: TODAY})).toEqual({pairs: ['EUR-USD', 'CHF-EUR'], start: '2026-07-25', end: TODAY});
    });

    it('takes the oldest rate whatever the order of the pairs', () => {
        const issue = staleFxIssue(
            [
                {pair: 'CHF/EUR', last_rate_date: '2026-09-20', stale_days: 38},
                {pair: 'USD/EUR', last_rate_date: '2026-08-01', stale_days: 88},
            ],
            TODAY,
        );
        expect(issue?.message_params).toMatchObject({days: 88, date_from: '2026-08-01', date_to: TODAY});
    });
});

describe('pairsStillStale — the sync worked, the rate is still old: the provider has no newer one (Y6-6)', () => {
    const stale = (pair: string) => ({pair, last_rate_date: '2026-08-01', stale_days: 88});

    it('is the requested pairs that the report still lists as stale, in the order requested', () => {
        expect(pairsStillStale(['EUR-USD', 'CHF-EUR'], [stale('CHF/EUR'), stale('USD/EUR')])).toEqual(['EUR-USD', 'CHF-EUR']);
    });

    it('reads the same pair in either spelling and either order of its two codes', () => {
        expect(pairsStillStale(['EUR-USD'], [stale('usd/eur')])).toEqual(['EUR-USD']);
        expect(pairsStillStale(['USD-EUR'], [stale('EUR/USD')])).toEqual(['USD-EUR']);
    });

    it('leaves out a pair that is no longer stale: its sync found a newer rate', () => {
        expect(pairsStillStale(['EUR-USD', 'CHF-EUR'], [stale('CHF/EUR')])).toEqual(['CHF-EUR']);
        expect(pairsStillStale(['EUR-USD'], [])).toEqual([]);
        expect(pairsStillStale(['EUR-USD'], null)).toEqual([]);
        expect(pairsStillStale(['EUR-USD'], undefined)).toEqual([]);
    });

    it('ignores a stale pair that was not requested', () => {
        expect(pairsStillStale(['EUR-USD'], [stale('GBP/EUR')])).toEqual([]);
    });
});
