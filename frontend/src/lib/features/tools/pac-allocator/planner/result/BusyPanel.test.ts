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

// V3 of project 67: the phase the calculation reports, by its position in the list the service declares (M11). The label
// is read through its attributes, never through its translated text.
const PHASES = ['validate', 'model', 'search', 'verify', 'report'];
const phase = () => screen.queryByTestId('pac-planner-busy-phase');

describe('BusyPanel phases', () => {
    it('busy panel shows the phase label and its position', () => {
        render(BusyPanel, {timeoutMs: 60_000, onstop: () => {}, progressPhases: PHASES, progressPhase: 'search'});
        const label = phase();
        expect(label).not.toBeNull();
        expect([label?.dataset.progressPhase, label?.dataset.progressIndex, label?.dataset.progressTotal]).toEqual(['search', '3', '5']);
        // The bar stays the bar of the time waited: no fill by phase (no percentage, M11).
        expect(bar().getAttribute('data-mode')).toBe('elapsed');
    });

    it("busy panel without phases is today's panel", () => {
        const today = render(BusyPanel, {timeoutMs: 60_000, onstop: () => {}});
        const html = today.container.innerHTML;
        expect(phase()).toBeNull();
        today.unmount();
        const empty = render(BusyPanel, {timeoutMs: 60_000, onstop: () => {}, progressPhases: [], progressPhase: null});
        expect(empty.container.innerHTML).toBe(html);
        empty.unmount();
        // A phase without a declared list (a Tool without phases) changes nothing either.
        const undeclared = render(BusyPanel, {timeoutMs: 60_000, onstop: () => {}, progressPhases: [], progressPhase: 'search'});
        expect(undeclared.container.innerHTML).toBe(html);
    });

    it('an unknown phase is ignored', async () => {
        const view = render(BusyPanel, {timeoutMs: 60_000, onstop: () => {}, progressPhases: PHASES, progressPhase: 'model'});
        expect(phase()?.dataset.progressIndex).toBe('2');
        await view.rerender({timeoutMs: 60_000, onstop: () => {}, progressPhases: PHASES, progressPhase: 'mystery'});
        flushSync();
        expect([phase()?.dataset.progressPhase, phase()?.dataset.progressIndex]).toEqual(['model', '2']);
        await view.rerender({timeoutMs: 60_000, onstop: () => {}, progressPhases: PHASES, progressPhase: 'report'});
        flushSync();
        expect([phase()?.dataset.progressPhase, phase()?.dataset.progressIndex]).toEqual(['report', '5']);
    });
});
