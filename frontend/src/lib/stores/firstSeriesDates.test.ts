/**
 * firstSeriesDates — unit tests (Vitest, node). Lot FB-7b, frontend.
 *
 * «All» on an asset or an FX pair page asks its series from the sentinel `min` and adopts the first date the answer holds. That date is
 * remembered for the session, per asset and per pair, so that a later visit with «All» starts from the real day (and from the cache)
 * instead of asking the whole history again. A catch-up, a sync, a save and a change of user make it untrue: it is forgotten.
 *
 * Contract:
 * - `rememberFirstDate(kind, id, date)` then `firstDateOf(kind, id)` give it back; an asset and a pair never share a key, nor two ids;
 * - the earliest date a series was seen on wins: a later, higher date does not replace it, an earlier one does;
 * - `forgetFirstDate(kind, id)` forgets one; `forgetAllFirstDates()` all;
 * - a prices catch-up (`notifyPricesCaughtUp`) and a change of user forget all.
 *
 * Red first: the module does not exist.
 */
import {beforeEach, describe, expect, it} from 'vitest';
import {firstDateOf, forgetAllFirstDates, forgetFirstDate, isFirstDateKnown, rememberFirstDate, rememberNoSeries} from './firstSeriesDates';
import {notifyPricesCaughtUp} from './portfolio/portfolioMutation';
import {transitionClientSession} from './app/clientSession';

beforeEach(() => {
    forgetAllFirstDates();
});

describe('firstSeriesDates', () => {
    it('gives back what was remembered, per kind and per id', () => {
        rememberFirstDate('asset', 7, '1985-03-01');
        rememberFirstDate('fx', 'EUR-USD', '1999-01-04');

        expect(firstDateOf('asset', 7)).toBe('1985-03-01');
        expect(firstDateOf('fx', 'EUR-USD')).toBe('1999-01-04');
        expect(firstDateOf('asset', 8)).toBeUndefined();
        expect(firstDateOf('fx', 'EUR-GBP')).toBeUndefined();
        expect(firstDateOf('asset', 'EUR-USD'), 'an asset id and a pair slug never share a key').toBeUndefined();
    });

    it('keeps the earliest date a series was seen on', () => {
        rememberFirstDate('asset', 7, '1990-01-02');
        rememberFirstDate('asset', 7, '2001-05-05');
        expect(firstDateOf('asset', 7), 'a later date does not replace it').toBe('1990-01-02');

        rememberFirstDate('asset', 7, '1985-03-01');
        expect(firstDateOf('asset', 7), 'an earlier one does').toBe('1985-03-01');
    });

    it('forgets one series, or all', () => {
        rememberFirstDate('asset', 7, '1985-03-01');
        rememberFirstDate('asset', 8, '1990-01-02');
        rememberFirstDate('fx', 'EUR-USD', '1999-01-04');

        forgetFirstDate('asset', 7);
        expect(firstDateOf('asset', 7)).toBeUndefined();
        expect(firstDateOf('asset', 8)).toBe('1990-01-02');

        forgetAllFirstDates();
        expect(firstDateOf('asset', 8)).toBeUndefined();
        expect(firstDateOf('fx', 'EUR-USD')).toBeUndefined();
    });

    it('a prices catch-up on the server makes every remembered date untrue: forgotten', () => {
        rememberFirstDate('asset', 7, '1985-03-01');
        rememberFirstDate('fx', 'EUR-USD', '1999-01-04');

        notifyPricesCaughtUp();

        expect(firstDateOf('asset', 7)).toBeUndefined();
        expect(firstDateOf('fx', 'EUR-USD')).toBeUndefined();
    });

    it('a change of user forgets them too', () => {
        transitionClientSession('first-user');
        rememberFirstDate('asset', 7, '1985-03-01');

        transitionClientSession('second-user');

        expect(firstDateOf('asset', 7)).toBeUndefined();
    });
});

describe('a series with no point (FB-7b, lists)', () => {
    it('is known, with no first day', () => {
        rememberNoSeries('asset', 9);

        expect(isFirstDateKnown('asset', 9)).toBe(true);
        expect(firstDateOf('asset', 9)).toBeUndefined();
        expect(isFirstDateKnown('asset', 10), 'another series is not known').toBe(false);
    });

    it('gives way to a first day, and a first day is not taken back by it', () => {
        rememberNoSeries('fx', 'EUR-XAF');
        rememberFirstDate('fx', 'EUR-XAF', '1999-01-04');
        expect(firstDateOf('fx', 'EUR-XAF'), 'a series that gets points has its first day').toBe('1999-01-04');

        rememberNoSeries('fx', 'EUR-XAF');
        expect(firstDateOf('fx', 'EUR-XAF'), 'no-series never replaces a first day').toBe('1999-01-04');
    });

    it('is forgotten as a first day is: one series, a catch-up, all', () => {
        rememberNoSeries('asset', 9);
        forgetFirstDate('asset', 9);
        expect(isFirstDateKnown('asset', 9)).toBe(false);

        rememberNoSeries('asset', 9);
        notifyPricesCaughtUp();
        expect(isFirstDateKnown('asset', 9)).toBe(false);
    });
});
