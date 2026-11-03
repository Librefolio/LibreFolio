/**
 * Y6-7 delivery 1 — the one place that says what a page asks the report routes.
 *
 * The Dashboard and a broker's page each built their own report, contribution and candles questions. FB-14 makes the
 * backend answer all of them from one engine run when their flags are the same, and MF6-3 adds the "whole broker"
 * flag: so one function builds the scope, and the three questions cannot drift apart.
 */
import {describe, expect, it} from 'vitest';
import {contributionCall, lightSummaryCall, mainReportCall, pnlCandlesCall, scopeKey, withLiveLastPoint, type PortfolioScope} from './portfolioDataScope';

const scope: PortfolioScope = {brokerIds: [3, 1], start: '2026-01-01', end: '2026-10-28', currency: 'EUR', fullShare: false};

describe('scopeKey — two scopes are the same question when this is equal', () => {
    it('carries the brokers, the period and the currency', () => {
        expect(scopeKey(scope)).toBe(scopeKey({...scope}));
        expect(scopeKey(scope)).not.toBe(scopeKey({...scope, brokerIds: [3]}));
        expect(scopeKey(scope)).not.toBe(scopeKey({...scope, start: '2026-02-01'}));
        expect(scopeKey(scope)).not.toBe(scopeKey({...scope, end: '2026-10-27'}));
        expect(scopeKey(scope)).not.toBe(scopeKey({...scope, currency: 'USD'}));
    });

    it('tells "min" (All, not resolved yet) from the day it resolves to', () => {
        expect(scopeKey({...scope, start: 'min'})).not.toBe(scopeKey({...scope, start: '1850-03-02'}));
    });

    it('tells the whole brokers from the owner’s share (MF6-3): the broker page and the dashboard are other questions', () => {
        expect(scopeKey({...scope, fullShare: true})).not.toBe(scopeKey(scope));
    });
});

describe('the three questions of one scope', () => {
    it('the main report asks the eager sections and none of the lazy ones', () => {
        const call = mainReportCall(scope, {wantsBrokerPnlHistory: true});
        expect(call).toMatchObject({includeContribution: false, includeBreakdown: false, includeHistory: true, includeAllocationHistory: true});
        expect(call.options).toMatchObject({includeBrokerPnlHistory: true, includeIncomeHistory: true, includeCostHistory: true, includeDepositHistory: true, includeAcquisitionFunding: true});
        expect(call.options?.includePnlCandles).toBeFalsy();
    });

    it('the broker overlay is asked only when the scope has two brokers or more', () => {
        expect(mainReportCall(scope, {wantsBrokerPnlHistory: false}).options?.includeBrokerPnlHistory).toBeFalsy();
    });

    it('the contribution asks only the contribution', () => {
        expect(contributionCall(scope)).toMatchObject({includeContribution: true, includeBreakdown: false, includeHistory: false, includeAllocationHistory: false});
    });

    it('the candles ask only the candles', () => {
        const call = pnlCandlesCall(scope);
        expect(call).toMatchObject({includeContribution: false, includeBreakdown: false, includeHistory: false, includeAllocationHistory: false});
        expect(call.options).toEqual({includePnlCandles: true});
    });

    it('all three carry the same brokers, period and currency, in the same order (FB-14: one engine run)', () => {
        const calls = [mainReportCall(scope, {wantsBrokerPnlHistory: false}), contributionCall(scope), pnlCandlesCall(scope)];
        for (const call of calls) {
            expect(call.brokerIds).toEqual([3, 1]);
            expect(call.start).toBe('2026-01-01');
            expect(call.end).toBe('2026-10-28');
            expect(call.currency).toBe('EUR');
        }
    });

    it('the whole-broker flag reaches all three, and is absent otherwise so the dashboard’s questions stay as they were', () => {
        for (const make of [() => mainReportCall(scope, {wantsBrokerPnlHistory: false}), () => contributionCall(scope), () => pnlCandlesCall(scope)]) {
            expect(make().options?.fullShare).toBeFalsy();
        }
        const whole = {...scope, fullShare: true};
        for (const call of [mainReportCall(whole, {wantsBrokerPnlHistory: false}), contributionCall(whole), pnlCandlesCall(whole)]) {
            expect(call.options?.fullShare).toBe(true);
        }
    });
});

describe('the live poll’s question (FB-28)', () => {
    it('asks the summary of the same scope and nothing else: history and allocation history, on by default, are off', () => {
        const call = lightSummaryCall(scope);
        expect(call).toMatchObject({brokerIds: [3, 1], start: '2026-01-01', end: '2026-10-28', currency: 'EUR', includeContribution: false, includeBreakdown: false, includeHistory: false, includeAllocationHistory: false});
        expect(call.options).toBeUndefined();
    });

    it('counts the brokers whole when the page does (MF6-3), like the question it follows', () => {
        expect(lightSummaryCall({...scope, fullShare: true}).options).toEqual({fullShare: true});
    });
});

describe('withLiveLastPoint — the last step of the history follows the summary’s state (FB-28)', () => {
    const money = (amount: string) => ({code: 'EUR', amount});
    const point = (date: string, nav: string) => ({date, through: date, nav_value: money(nav), market_value: money('1'), cash_value: money('2'), total_pnl: money('7')});
    const summary = {net_worth: money('150'), market_value: money('120'), cash_total: money('30')};

    it('replaces the value fields of the last point with the summary’s, in a new array and a new point', () => {
        const history = [point('2026-10-27', '100'), point('2026-10-28', '110')] as never;
        const next = withLiveLastPoint(history, summary as never);
        expect(next).not.toBe(history);
        expect(next[0]).toBe((history as unknown[])[0]);
        expect(next[1]).toMatchObject({date: '2026-10-28', nav_value: money('150'), market_value: money('120'), cash_value: money('30')});
        expect(next[1]).not.toBe((history as unknown[])[1]);
    });

    it('leaves what the summary does not state alone: the point’s own P&L is the engine’s', () => {
        const next = withLiveLastPoint([point('2026-10-28', '110')] as never, summary as never);
        expect(next[0]).toMatchObject({total_pnl: money('7'), through: '2026-10-28'});
    });

    it('does not touch the original point', () => {
        const history = [point('2026-10-28', '110')] as never;
        withLiveLastPoint(history, summary as never);
        expect((history as unknown as Array<{nav_value: unknown}>)[0].nav_value).toEqual(money('110'));
    });

    it('an empty history stays empty', () => {
        expect(withLiveLastPoint([], summary as never)).toEqual([]);
    });
});
