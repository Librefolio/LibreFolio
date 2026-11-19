/**
 * riskFreeRateStore — the reader's risk-free rate, one value for every risk page (RN-21, Q9 b + Q9 bis a).
 *
 * What is pinned:
 *   1. **One value, 0 % by default**, kept at module level: every page reads the same.
 *   2. **Per user, in the browser**: a user-scoped key, re-read when the account changes, reset with the session.
 *   3. **Only what the engine accepts** (`gt=-1`, `le=10` as a fraction): a stored or offered value outside it, or not
 *      a finite number, is refused — a corrupted entry would otherwise send a 422 from every analytic of every page.
 *   4. **One conversion**: `riskFreeParameters` hands the same rate to the Sharpe and to the threshold of Sortino,
 *      Omega and the semi-deviation (Q9 bis: one threshold for every «excess» measure).
 */
import {beforeEach, describe, expect, it, vi} from 'vitest';

vi.mock('$app/environment', () => ({browser: true}));

import {transitionClientSession} from '$lib/stores/app/clientSession';

import {parseRiskFreePercent, riskFreeParameters} from './riskFreeRate';
import {riskFreeRate} from './riskFreeRateStore.svelte';

let backing = new Map<string, string>();
let userSeq = 0;

const keyFor = (userId: string): string => `lf_${userId}_risk_free_rate_percent`;

function freshUser(): string {
    const userId = `risk-free-u${++userSeq}`;
    transitionClientSession(userId);
    return userId;
}

beforeEach(() => {
    backing = new Map();
    Object.defineProperty(globalThis, 'localStorage', {
        configurable: true,
        writable: true,
        value: {
            getItem: (key: string) => backing.get(key) ?? null,
            setItem: (key: string, value: string) => void backing.set(key, value),
            removeItem: (key: string) => void backing.delete(key),
            clear: () => backing.clear(),
        },
    });
});

describe('riskFreeRate — the shared value', () => {
    it('starts at 0 % for a reader who never set one', () => {
        freshUser();
        expect(riskFreeRate.percent).toBe(0);
    });

    it('keeps a set value, per user, and reads it back for that user only', () => {
        const first = freshUser();
        expect(riskFreeRate.set(2.5)).toBe(true);
        expect(riskFreeRate.percent).toBe(2.5);
        expect(backing.get(keyFor(first))).toBe('2.5');

        freshUser();
        expect(riskFreeRate.percent).toBe(0);

        transitionClientSession(first);
        expect(riskFreeRate.percent).toBe(2.5);
    });

    it('refuses what the engine would refuse, and keeps the value it had', () => {
        const user = freshUser();
        riskFreeRate.set(3);
        for (const bad of [Number.NaN, Number.POSITIVE_INFINITY, -100, -150, 1000.5]) {
            expect(riskFreeRate.set(bad), String(bad)).toBe(false);
            expect(riskFreeRate.percent, String(bad)).toBe(3);
        }
        expect(backing.get(keyFor(user))).toBe('3');
    });

    it('reads a corrupted stored entry as 0 % and leaves it alone', () => {
        const user = `risk-free-u${++userSeq}`;
        backing.set(keyFor(user), 'banana');
        transitionClientSession(user);
        expect(riskFreeRate.percent).toBe(0);
        expect(backing.get(keyFor(user))).toBe('banana');
    });

    it('stores 0 as the absence of a choice', () => {
        const user = freshUser();
        riskFreeRate.set(1.2);
        riskFreeRate.set(0);
        expect(riskFreeRate.percent).toBe(0);
        expect(backing.has(keyFor(user))).toBe(false);
    });
});

describe('parseRiskFreePercent — what a stored value or a typed one may be', () => {
    it('accepts a finite percent above -100 and up to 1000', () => {
        expect(parseRiskFreePercent('2.5')).toBe(2.5);
        expect(parseRiskFreePercent('-0.5')).toBe(-0.5);
        expect(parseRiskFreePercent('1000')).toBe(1000);
        expect(parseRiskFreePercent(0)).toBe(0);
    });

    it('refuses anything else', () => {
        for (const bad of [null, '', ' ', 'abc', '-100', '1000.01', 'Infinity', Number.NaN]) expect(parseRiskFreePercent(bad), String(bad)).toBeNull();
    });
});

describe('riskFreeParameters — one rate, both parameters', () => {
    it('hands the same annual fraction to the Sharpe and to the threshold', () => {
        expect(riskFreeParameters(2.5)).toEqual({risk_free_annual_rate: 0.025, target_annual_return: 0.025});
        expect(riskFreeParameters(0)).toEqual({risk_free_annual_rate: 0, target_annual_return: 0});
    });
});
