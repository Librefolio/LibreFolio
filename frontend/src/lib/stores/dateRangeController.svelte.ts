/**
 * Date Range Controller — generalizes the per-page boilerplate around the
 * global dateRangeStore (see dateRangeStore.svelte.ts).
 *
 * Every page (dashboard, assets list/detail, fx list/detail, broker detail)
 * repeated the same ~15 lines: a local mirror of start/end (always concrete,
 * used for API calls), a "display" start that shows the literal "min"
 * sentinel while pending, an `isMaxPending` flag, and an onchange handler that
 * resolves sentinels + writes back to the global store.
 *
 * IMPORTANT — what this controller does NOT do: resolve the "MAX" ("All")
 * sentinel into a real earliest date. That resolution is inherently
 * page-specific (it depends on whatever data that page loads — portfolio
 * history, asset price history, fx rate history, broker transactions — there
 * is no single generic "earliest date" endpoint). Call `markMaxResolved(...)`
 * from your own load function once your data reveals the real start date
 * (e.g. `history[0].date`), same as the pattern this replaces.
 *
 * @module stores/dateRangeController
 */

import type {QuickPreset} from '$lib/components/ui/date/DateRangePicker.svelte';
import {getEnd, getStart, isMaxSentinel, resolveDateSentinel, setDateRange} from './dateRangeStore.svelte';

export type DateRangeActivePreset = QuickPreset | 'custom' | null;

export interface DateRangeController {
    /** Concrete, resolved start date — safe to use in API calls. */
    readonly start: string;
    /**
     * Concrete, resolved end date — safe to use in API calls. Also bindable:
     * DateRangePicker writes its bindable `end` prop directly on preset click
     * (before `onchange` fires), same double-write pattern as the original
     * per-page code — the subsequent `onDateRangeChange` write is authoritative.
     */
    end: string;
    /** Bind to DateRangePicker's `start` prop — shows "min" while MAX is pending resolution. Bindable for the same reason as `end` above. */
    displayStart: string;
    /** True while "All" (MAX) is selected but not yet resolved to a concrete date. */
    readonly isMaxPending: boolean;
    /** Bind to DateRangePicker's `activePreset` prop. */
    activePreset: DateRangeActivePreset;
    /** Pass as DateRangePicker's `onchange` handler. */
    onDateRangeChange: (newStart: string, newEnd: string) => void;
    /**
     * Call once your own loaded data reveals the real earliest date (e.g.
     * `history[0].date`). No-op if not currently pending, or if called with
     * no data yet (empty/undefined/null).
     */
    markMaxResolved: (realEarliestDate: string | undefined | null) => void;
}

/**
 * Create a page-local date range controller, seeded from the global store.
 *
 * @param onchange Called after internal state + the global store are updated,
 *   with the RAW start/end (sentinels preserved, e.g. for URL sync via
 *   `replaceHistoryDateRange`/`gotoDateRange`). Use the controller's own
 *   `.start`/`.end` getters (already resolved) to trigger a data reload.
 */
export function createDateRangeController(onchange?: (rawStart: string, rawEnd: string) => void): DateRangeController {
    const initialStart = getStart();
    const initialIsMaxPending = isMaxSentinel(initialStart);

    let start = $state(resolveDateSentinel(initialStart));
    let end = $state(resolveDateSentinel(getEnd()));
    let isMaxPending = $state(initialIsMaxPending);
    // Seeded from the plain `initialIsMaxPending`/`initialStart` (not from the
    // start/isMaxPending $state above) to avoid a state_referenced_locally warning —
    // displayStart is manually resynced elsewhere and bound bidirectionally to
    // DateRangePicker, so it's intentionally NOT a pure $derived of start/isMaxPending.
    let displayStart = $state(initialIsMaxPending ? 'min' : resolveDateSentinel(initialStart));
    let activePreset: DateRangeActivePreset = $state(initialIsMaxPending ? 'MAX' : null);

    function onDateRangeChange(newStart: string, newEnd: string) {
        isMaxPending = isMaxSentinel(newStart);
        start = resolveDateSentinel(newStart);
        end = resolveDateSentinel(newEnd);
        displayStart = isMaxPending ? 'min' : start;
        setDateRange(newStart, newEnd);
        onchange?.(newStart, newEnd);
    }

    function markMaxResolved(realEarliestDate: string | undefined | null) {
        if (!isMaxPending || !realEarliestDate) return;
        start = realEarliestDate;
        displayStart = start;
        isMaxPending = false;
    }

    return {
        get start() {
            return start;
        },
        get end() {
            return end;
        },
        set end(v: string) {
            end = v;
        },
        get displayStart() {
            return displayStart;
        },
        set displayStart(v: string) {
            displayStart = v;
        },
        get isMaxPending() {
            return isMaxPending;
        },
        get activePreset() {
            return activePreset;
        },
        set activePreset(v: DateRangeActivePreset) {
            activePreset = v;
        },
        onDateRangeChange,
        markMaxResolved,
    };
}
