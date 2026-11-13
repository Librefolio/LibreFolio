/**
 * The broker filter's reload debounce (K-18): the page is busy during the quiet period, not only after it.
 */
import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';
import {pageBusy} from '$lib/stores/app/pageBusy.svelte';
import {createScopeReloadDebounce} from './scopeReloadDebounce';

beforeEach(() => {
    vi.useFakeTimers();
    pageBusy.reset();
});
afterEach(() => {
    pageBusy.reset();
    vi.useRealTimers();
});

function make(reload: () => Promise<unknown> = vi.fn(async () => undefined)) {
    return {reload, debounce: createScopeReloadDebounce({delayMs: 2000, waitLabel: 'wait', reloadLabel: 'reload', reload})};
}

describe('createScopeReloadDebounce', () => {
    it('holds the page busy from the first click, and fires one reload after the last', async () => {
        const reload = vi.fn(async () => undefined);
        const {debounce} = make(reload);
        debounce.schedule();
        expect(pageBusy.busy).toBe(true);
        await vi.advanceTimersByTimeAsync(1500);
        debounce.schedule();
        await vi.advanceTimersByTimeAsync(1500);
        expect(reload).not.toHaveBeenCalled();
        expect(pageBusy.busy).toBe(true);

        await vi.advanceTimersByTimeAsync(600);
        expect(reload).toHaveBeenCalledTimes(1);
        expect(pageBusy.labels).toEqual([]);
    });

    it('never leaves the page idle between the wait and the reload', async () => {
        let release: () => void = () => undefined;
        const {debounce} = make(vi.fn(() => new Promise<void>((resolve) => (release = resolve))));
        debounce.schedule();
        await vi.advanceTimersByTimeAsync(2000);
        expect(pageBusy.labels).toEqual(['reload']);
        release();
        await vi.advanceTimersByTimeAsync(0);
        expect(pageBusy.busy).toBe(false);
    });

    it('dispose cancels the reload and returns the token', async () => {
        const reload = vi.fn(async () => undefined);
        const {debounce} = make(reload);
        debounce.schedule();
        debounce.dispose();
        expect(pageBusy.busy).toBe(false);
        await vi.advanceTimersByTimeAsync(5000);
        expect(reload).not.toHaveBeenCalled();
    });
});
