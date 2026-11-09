// @vitest-environment jsdom
/**
 * forgotCooldown — the wait of «forgot password» by email between two requests (lot UA1), its pure helpers.
 *
 * The contract under test:
 *   - `FORGOT_RESEND_WAIT_S` is the server's `RESET_EMAIL_MIN_INTERVAL`, 5 minutes;
 *   - `startForgotCooldown(now)` returns `now + 300 000` and stores it under `FORGOT_COOLDOWN_KEY`; storage that throws
 *     loses the stored copy only, the deadline is still returned;
 *   - `readForgotCooldown(now)` gives back a stored deadline in `(now, now + 300 000]`, `null` for anything else — none,
 *     past, now itself, not a number, further than the wait — and `null` when the storage throws;
 *   - `secondsLeft` rounds up to whole seconds and never goes below 0; `formatWait` writes `m:ss`, never negative.
 *
 * jsdom for its `sessionStorage`, cleared before every test; a storage that fails is a stand-in whose every call throws
 * (`vi.stubGlobal`; a spy on `Storage.prototype` does not reach jsdom's `sessionStorage`), removed after each test.
 */
import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';
import {FORGOT_COOLDOWN_KEY, FORGOT_RESEND_WAIT_S, formatWait, readForgotCooldown, secondsLeft, startForgotCooldown} from './forgotCooldown';

const T0 = Date.UTC(2026, 10, 9, 10, 0, 0);
const WAIT_MS = 300_000;

function blocked(): never {
    throw new DOMException('The operation is insecure.', 'SecurityError');
}

beforeEach(() => {
    sessionStorage.clear();
});

afterEach(() => {
    vi.unstubAllGlobals();
});

describe('forgotCooldown — the wait', () => {
    it('FCD-01: the wait is the server’s minimum interval, 5 minutes', () => {
        expect(FORGOT_RESEND_WAIT_S).toBe(300);
    });

    it('FCD-02: start returns now plus the wait and stores it; read gives it back', () => {
        expect(startForgotCooldown(T0)).toBe(T0 + WAIT_MS);
        expect(sessionStorage.getItem(FORGOT_COOLDOWN_KEY)).toBe(String(T0 + WAIT_MS));
        expect(readForgotCooldown(T0)).toBe(T0 + WAIT_MS);
        expect(readForgotCooldown(T0 + WAIT_MS - 1)).toBe(T0 + WAIT_MS);
    });

    it.each([
        {label: 'nothing stored', stored: null, now: T0},
        {label: 'past', stored: String(T0 - 1), now: T0},
        {label: 'exactly now', stored: String(T0), now: T0},
        {label: 'not a number', stored: 'soon', now: T0},
        {label: 'empty', stored: '', now: T0},
        {label: 'infinite', stored: 'Infinity', now: T0},
        {label: 'further than the wait', stored: String(T0 + WAIT_MS + 1), now: T0},
    ])('FCD-03: read ignores a deadline $label', ({stored, now}) => {
        if (stored !== null) sessionStorage.setItem(FORGOT_COOLDOWN_KEY, stored);
        expect(readForgotCooldown(now)).toBeNull();
    });

    it('FCD-04: storage that throws — start still returns the deadline, read answers null', () => {
        const setItem = vi.fn(blocked);
        const getItem = vi.fn(blocked);
        vi.stubGlobal('sessionStorage', {getItem, setItem, removeItem: blocked, clear: blocked, key: blocked, length: 0});

        expect(startForgotCooldown(T0)).toBe(T0 + WAIT_MS);
        expect(readForgotCooldown(T0)).toBeNull();
        expect(setItem).toHaveBeenCalledTimes(1);
        expect(getItem).toHaveBeenCalledTimes(1);
    });
});

describe('forgotCooldown — the countdown', () => {
    it.each([
        {deadline: T0 + WAIT_MS, now: T0, left: 300},
        {deadline: T0 + 1_000, now: T0 + 1, left: 1},
        {deadline: T0 + 1_500, now: T0, left: 2},
        {deadline: T0, now: T0, left: 0},
        {deadline: T0, now: T0 + 5_000, left: 0},
    ])('FCD-05: secondsLeft($deadline - $now ms) = $left — rounded up, never below 0', ({deadline, now, left}) => {
        expect(secondsLeft(deadline, now)).toBe(left);
    });

    it.each([
        {seconds: 300, shown: '5:00'},
        {seconds: 299, shown: '4:59'},
        {seconds: 61, shown: '1:01'},
        {seconds: 60, shown: '1:00'},
        {seconds: 9, shown: '0:09'},
        {seconds: 0, shown: '0:00'},
        {seconds: -4, shown: '0:00'},
        {seconds: 12.7, shown: '0:12'},
    ])('FCD-06: formatWait($seconds) = $shown', ({seconds, shown}) => {
        expect(formatWait(seconds)).toBe(shown);
    });
});
