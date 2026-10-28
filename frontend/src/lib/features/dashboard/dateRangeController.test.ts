/**
 * FB-7 — "All" (MAX) means the whole history: from the first real movement, whatever its year.
 *
 * The defect (D-P4 slip): while "All" was pending the page asked the backend for `2000-01-01`, so a history that
 * starts in 1850 (or 1926, or 1998) lost everything before 2000. The backend already resolves the `"min"` sentinel
 * of the report routes to the user's first transaction; the pages must send `"min"` there, never a floor.
 */
import {describe, expect, it} from 'vitest';
import {historyStart, setDateRange} from '$lib/stores/dateRangeStore.svelte';
import {createDateRangeController} from './dateRangeController.svelte';

describe('historyStart — the start a report-like request carries', () => {
    it('is the "min" sentinel while "All" is pending: the backend resolves it to the first movement', () => {
        expect(historyStart(true, '2000-01-01')).toBe('min');
    });

    it('is the concrete start once "All" has resolved or for any other period', () => {
        expect(historyStart(false, '1850-03-02')).toBe('1850-03-02');
        expect(historyStart(false, '2026-07-28')).toBe('2026-07-28');
    });
});

describe('date range controller — "All" pending', () => {
    it('sends "min", not a 2000 floor', () => {
        setDateRange('min', '2026-10-28');
        const controller = createDateRangeController();
        expect(controller.isMaxPending).toBe(true);
        expect(controller.historyStart).toBe('min');
    });

    it('moves to the first real movement once the page has seen it, before the year 2000 too', () => {
        setDateRange('min', '2026-10-28');
        const controller = createDateRangeController();
        controller.markMaxResolved('1850-03-02');
        expect(controller.isMaxPending).toBe(false);
        expect(controller.historyStart).toBe('1850-03-02');
        expect(controller.start).toBe('1850-03-02');
    });

    it('picking "All" from another period asks for "min" again', () => {
        setDateRange('2026-07-28', '2026-10-28');
        const controller = createDateRangeController();
        expect(controller.historyStart).toBe('2026-07-28');
        controller.onDateRangeChange('min', '2026-10-28');
        expect(controller.historyStart).toBe('min');
    });

    it('a concrete period is sent as it is', () => {
        setDateRange('2026-01-01', '2026-10-28');
        const controller = createDateRangeController();
        expect(controller.isMaxPending).toBe(false);
        expect(controller.historyStart).toBe('2026-01-01');
    });
});
