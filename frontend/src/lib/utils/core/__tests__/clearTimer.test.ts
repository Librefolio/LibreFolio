/**
 * clearTimer.test.ts — cancel-and-forget a timeout handle.
 *
 * Fake timers let us prove the two things that matter: the armed callback never
 * fires after a clear, and the call returns null so the caller's handle is
 * emptied in the same expression. A null/elapsed handle must be a safe no-op.
 */
import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';
import {clearTimer} from '../clearTimer';

describe('clearTimer', () => {
    beforeEach(() => vi.useFakeTimers());
    afterEach(() => vi.useRealTimers());

    it('cancels a pending timeout so its callback never runs', () => {
        const cb = vi.fn();
        // Runtime handle type differs between node (test env) and DOM (app);
        // clearTimer treats it opaquely, so cast to its parameter type.
        const handle = setTimeout(cb, 500) as unknown as ReturnType<typeof setTimeout>;
        const cleared = clearTimer(handle);
        vi.advanceTimersByTime(1000);
        expect(cb).not.toHaveBeenCalled();
        expect(cleared).toBeNull();
    });

    it('returns null for a null handle without throwing', () => {
        expect(clearTimer(null)).toBeNull();
    });

    it('is a no-op for an already-elapsed handle', () => {
        const cb = vi.fn();
        const handle = setTimeout(cb, 10) as unknown as ReturnType<typeof setTimeout>;
        vi.advanceTimersByTime(50);
        expect(cb).toHaveBeenCalledTimes(1);
        // Clearing after it fired must not throw and still yields null.
        expect(clearTimer(handle)).toBeNull();
    });
});
