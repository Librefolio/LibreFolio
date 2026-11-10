// @vitest-environment jsdom
/**
 * BusyPanel — the waiting panel of the PAC allocator (P4a, lot P9).
 *
 * While the solver works the user sees a bar that fills with the time that passes against the timeout the client already knows
 * (`client_timeout_ms`): a measure of the wait, never of the work (the solver reports no progress). Without a known limit, or while the
 * copied data is read again, the bar only moves. The clock is faked: the bar is read through its ARIA values and its `data-mode`.
 */
import {flushSync} from 'svelte';
import {afterEach, beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';
import {cleanup, render, screen, setupI18n} from '$test/component';
import BusyPanel from './BusyPanel.svelte';

beforeAll(async () => {
    await setupI18n();
});

beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2026-11-07T10:00:00Z'));
});

afterEach(() => {
    cleanup();
    vi.useRealTimers();
});

const bar = () => screen.getByTestId('pac-planner-busy-bar');

describe('BusyPanel bar', () => {
    it('starts empty against the known timeout', () => {
        render(BusyPanel, {timeoutMs: 60_000, onstop: () => {}});
        expect(bar().getAttribute('data-mode')).toBe('elapsed');
        expect(bar().getAttribute('aria-valuemin')).toBe('0');
        expect(bar().getAttribute('aria-valuemax')).toBe('60');
        expect(bar().getAttribute('aria-valuenow')).toBe('0');
    });

    it('follows the time that passes', () => {
        render(BusyPanel, {timeoutMs: 60_000, onstop: () => {}});
        vi.advanceTimersByTime(15_000);
        flushSync();
        expect(bar().getAttribute('aria-valuenow')).toBe('15');
        expect((screen.getByTestId('pac-planner-busy-bar-fill') as HTMLElement).style.width).toBe('25%');
    });

    it('stops at the limit and never overflows', () => {
        render(BusyPanel, {timeoutMs: 10_000, onstop: () => {}});
        vi.advanceTimersByTime(40_000);
        flushSync();
        expect(bar().getAttribute('aria-valuenow')).toBe('10');
        expect((screen.getByTestId('pac-planner-busy-bar-fill') as HTMLElement).style.width).toBe('100%');
    });

    it('only moves when the limit is unknown', () => {
        render(BusyPanel, {timeoutMs: null, onstop: () => {}});
        expect(bar().getAttribute('data-mode')).toBe('indeterminate');
        expect(bar().hasAttribute('aria-valuenow')).toBe(false);
        expect(screen.queryByTestId('pac-planner-busy-elapsed')).toBeNull();
    });

    it('only moves while the copied data is read again, whatever the timeout', () => {
        render(BusyPanel, {phase: 'refresh', timeoutMs: 60_000, onstop: () => {}});
        expect(bar().getAttribute('data-mode')).toBe('indeterminate');
    });

    it('stops its timer when the panel goes away', () => {
        const {unmount} = render(BusyPanel, {timeoutMs: 60_000, onstop: () => {}});
        expect(vi.getTimerCount()).toBeGreaterThan(0);
        unmount();
        expect(vi.getTimerCount()).toBe(0);
    });
});
