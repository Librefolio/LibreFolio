/**
 * Y6-7 delivery 1 — the one place that says what a page asks the report routes.
 *
 * The Dashboard and a broker's page each built their own report, contribution and candles questions. FB-14 makes the
 * backend answer all of them from one engine run when their flags are the same, and MF6-3 adds the "whole broker"
 * flag: so one function builds the scope, and the three questions cannot drift apart.
 */
import {describe, expect, it} from 'vitest';
import {contributionCall, mainReportCall, pnlCandlesCall, scopeKey, type PortfolioScope} from './portfolioDataScope';

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
