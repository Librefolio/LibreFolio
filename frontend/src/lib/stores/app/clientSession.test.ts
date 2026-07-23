import {describe, expect, it, vi} from 'vitest';

import {ClientSessionState} from './clientSession';

describe('ClientSessionState', () => {
    it('resets registered state only after the initial identity is resolved', () => {
        const state = new ClientSessionState();
        const reset = vi.fn();
        state.register('test-cache', reset);

        expect(state.transition(1)).toBe(true);
        expect(reset).not.toHaveBeenCalled();
        expect(state.getUserId()).toBe('1');

        expect(state.transition(1)).toBe(false);
        expect(reset).not.toHaveBeenCalled();

        expect(state.transition(null)).toBe(true);
        expect(reset).toHaveBeenCalledOnce();
        expect(reset).toHaveBeenLastCalledWith({
            previousUserId: '1',
            nextUserId: null,
            generation: 2,
        });

        expect(state.transition(2)).toBe(true);
        expect(reset).toHaveBeenCalledTimes(2);
        expect(state.getUserId()).toBe('2');
    });

    it('invalidates captured generations when the account changes', () => {
        const state = new ClientSessionState();
        state.transition(1);
        const generation = state.getGeneration();

        expect(state.isCurrent(generation)).toBe(true);
        state.transition(2);
        expect(state.isCurrent(generation)).toBe(false);
    });

    it('resets caches when login follows an initial anonymous auth check', () => {
        const state = new ClientSessionState();
        const reset = vi.fn();
        state.register('test-cache', reset);

        state.transition(null);
        expect(reset).not.toHaveBeenCalled();

        state.transition(7);
        expect(reset).toHaveBeenCalledOnce();
    });
});
