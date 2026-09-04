// @vitest-environment jsdom
/**
 * CalendarMonth — component test (Vitest + jsdom).
 *
 * This is the reference spec for component tests in LibreFolio: it is the first
 * one, and the pattern it fixes is meant to be copied.
 *
 * Why a component test and not an E2E. `CalendarMonth` is a pure rendering
 * component — no fetch, no store, no navigation: the parent hands it a year, a
 * month, a set of highlights and five callbacks, and it draws a grid. Reaching
 * it through Playwright means booting a browser, logging in, navigating to a
 * page that happens to embed a date picker, and opening it — several seconds and
 * a dozen ways to fail, none of which are about the calendar. Here the same
 * surface is exercised in milliseconds, and a red can only mean the grid is
 * wrong.
 *
 * What it deliberately does NOT assert:
 *   - translated text. `weekdayLabels` and `monthLabels` are props, so the test
 *     supplies its own; the only i18n the component consumes is the "today"
 *     button's tooltip, which is never asserted on.
 *   - CSS classes. The visual state is published as `data-state`; matching on
 *     `bg-libre-green` would break at the next restyle while testing nothing.
 *
 * The grid contains out-of-month cells, so day numbers repeat (a "1" from the
 * previous month and the "1" of this one). Days are therefore addressed by their
 * ISO date, which is unique by construction, never by their label.
 */
import {beforeAll, describe, expect, it, vi} from 'vitest';
import {fireEvent, render, screen, setupI18n} from '$test/component';
import CalendarMonth from './CalendarMonth.svelte';
// The component reads today from the user's calendar (`todayIso`), so the test
// must ask the same question the same way. `toISOString().slice(0, 10)` was here
// before and answered in UTC: it agreed for 22 hours a day and turned this file
// red every night between midnight and 02:00 in Rome — which is exactly when it
// was found.
import {localIso} from '$lib/utils/dateOnly';

const WEEKDAYS = ['Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa', 'Su'];
const MONTHS = ['M0', 'M1', 'M2', 'M3', 'M4', 'M5', 'M6', 'M7', 'M8', 'M9', 'M10', 'M11'];

/**
 * A month safely in the past, so no cell is disabled by the future guard.
 *
 * March 2024 is chosen for its shape: 1 March 2024 is a Friday, so the grid
 * necessarily starts with out-of-month cells from February — which is exactly
 * the case that distinguishes "day 1" from "the first cell".
 */
const YEAR = 2024;
const MONTH = 2; // March (0-based)

function baseProps(overrides: Record<string, unknown> = {}) {
    return {
        year: YEAR,
        month: MONTH,
        weekdayLabels: WEEKDAYS,
        monthLabels: MONTHS,
        onDayClick: vi.fn(),
        onPrevMonth: vi.fn(),
        onNextMonth: vi.fn(),
        onSetMonth: vi.fn(),
        onSetYear: vi.fn(),
        ...overrides,
    };
}

/** The day button for an ISO date. Unique by construction, unlike its label. */
function day(iso: string): HTMLButtonElement {
    const el = document.querySelector<HTMLButtonElement>(`[data-testid="calendar-day"][data-iso="${iso}"]`);
    if (!el) throw new Error(`no day cell for ${iso} — the grid does not span that date`);
    return el;
}

describe('CalendarMonth', () => {
    beforeAll(async () => {
        await setupI18n();
    });

    it('renders the full grid of the requested month', () => {
        render(CalendarMonth, baseProps());

        const root = screen.getByTestId('calendar-month');
        expect(root).toHaveAttribute('data-year', String(YEAR));
        expect(root).toHaveAttribute('data-month', String(MONTH));

        // Every day of March 2024 is present, addressed by ISO date.
        for (let d = 1; d <= 31; d++) {
            const iso = `2024-03-${String(d).padStart(2, '0')}`;
            expect(day(iso)).toHaveAttribute('data-in-month', 'true');
        }
        // 1 March 2024 is a Friday: the grid opens with four February cells.
        expect(day('2024-02-26')).toHaveAttribute('data-in-month', 'false');

        // Weekday headers come from props, not from the catalogue.
        for (const label of WEEKDAYS) expect(screen.getByText(label)).toBeInTheDocument();
    });

    it('reports the clicked day to the parent as an ISO date', async () => {
        const onDayClick = vi.fn();
        render(CalendarMonth, baseProps({onDayClick}));

        await fireEvent.click(day('2024-03-15'));

        expect(onDayClick).toHaveBeenCalledTimes(1);
        expect(onDayClick).toHaveBeenCalledWith('2024-03-15');
    });

    it('publishes the semantic state of highlighted days', () => {
        render(
            CalendarMonth,
            baseProps({
                highlights: {rangeStart: '2024-03-10', rangeEnd: '2024-03-14'},
            }),
        );

        expect(day('2024-03-10')).toHaveAttribute('data-state', 'range-start');
        expect(day('2024-03-14')).toHaveAttribute('data-state', 'range-end');
        expect(day('2024-03-12')).toHaveAttribute('data-state', 'in-range');
        // A day outside the range keeps its neutral state — the assertion that
        // gives the three above their teeth.
        expect(day('2024-03-20')).toHaveAttribute('data-state', 'normal');
    });

    it('resolves a reversed pending/hover pair into a forward range', () => {
        // The user clicked the 20th, then dragged backwards to the 10th: the
        // component must not care about the order in which the two arrived.
        render(
            CalendarMonth,
            baseProps({
                highlights: {pending: '2024-03-20', hovered: '2024-03-10'},
            }),
        );

        expect(day('2024-03-10')).toHaveAttribute('data-state', 'range-start');
        expect(day('2024-03-20')).toHaveAttribute('data-state', 'range-end');
        expect(day('2024-03-15')).toHaveAttribute('data-state', 'in-range');
    });

    it('disables days the parent listed as unavailable, and reports no click', async () => {
        const onDayClick = vi.fn();
        render(
            CalendarMonth,
            baseProps({
                onDayClick,
                disabledDates: new Set(['2024-03-07']),
            }),
        );

        const blocked = day('2024-03-07');
        expect(blocked).toBeDisabled();
        await fireEvent.click(blocked);
        expect(onDayClick).not.toHaveBeenCalled();

        // A neighbour stays usable: without this, "nothing is clickable" would
        // also satisfy the assertion above.
        await fireEvent.click(day('2024-03-08'));
        expect(onDayClick).toHaveBeenCalledWith('2024-03-08');
    });

    it('greys out future days unless the parent allows them', () => {
        const future = new Date();
        future.setDate(future.getDate() + 1);
        const iso = localIso(future);

        const {unmount} = render(CalendarMonth, baseProps({year: future.getFullYear(), month: future.getMonth()}));
        expect(day(iso)).toBeDisabled();
        unmount();

        render(CalendarMonth, baseProps({year: future.getFullYear(), month: future.getMonth(), allowFuture: true}));
        expect(day(iso)).toBeEnabled();
    });

    it('marks today with its own state', () => {
        const today = new Date();
        const iso = localIso(today);

        render(CalendarMonth, baseProps({year: today.getFullYear(), month: today.getMonth()}));

        expect(day(iso)).toHaveAttribute('data-state', 'today');
    });

    it("marks the user's today, not UTC's, in the hours where the two disagree", () => {
        // The test above runs at whatever time the suite happens to run, and for
        // 22 hours a day the local calendar and `toISOString()` agree — so it is
        // green on a wrong implementation almost always. This one freezes the
        // clock inside the window where they differ.
        //
        // Not hypothetical: this file went red at 00:02 local time because its
        // assertions derived the expected date with `toISOString().slice(0, 10)`
        // while the component reads the local calendar. For those two hours every
        // user east of Greenwich saw the wrong day highlighted.
        //
        // The expected value is spelled out from the *rule* — "the year, month and
        // day fields of the local Date" — and deliberately not by calling the
        // helper under test. An oracle derived from the implementation is how the
        // DateRangePicker preset tests stayed green on broken arithmetic for
        // months: they replicated the component's own formula, so the two agreed
        // with each other and with nothing else.
        vi.useFakeTimers();
        try {
            // Cross midnight from whichever side this runner's zone sits on, so
            // the two readings differ wherever it runs. In UTC itself they never
            // differ, and the case says so rather than pretending otherwise.
            const offsetMinutes = -new Date('2024-06-14T12:00:00Z').getTimezoneOffset();
            if (offsetMinutes === 0) return;

            vi.setSystemTime(new Date(offsetMinutes > 0 ? '2024-06-14T23:30:00Z' : '2024-06-14T00:30:00Z'));
            const local = new Date();

            const pad = (n: number) => String(n).padStart(2, '0');
            const expected = `${local.getFullYear()}-${pad(local.getMonth() + 1)}-${pad(local.getDate())}`;
            expect(expected).not.toBe(local.toISOString().slice(0, 10)); // the premise of the case

            render(CalendarMonth, baseProps({year: local.getFullYear(), month: local.getMonth()}));

            expect(day(expected)).toHaveAttribute('data-state', 'today');
        } finally {
            vi.useRealTimers();
        }
    });

    it('delegates navigation to the parent instead of moving on its own', async () => {
        const onPrevMonth = vi.fn();
        const onNextMonth = vi.fn();
        const onGoToToday = vi.fn();
        const onSetYear = vi.fn();
        render(CalendarMonth, baseProps({onPrevMonth, onNextMonth, onGoToToday, onSetYear}));

        await fireEvent.click(screen.getByTestId('calendar-prev-month'));
        await fireEvent.click(screen.getByTestId('calendar-next-month'));
        await fireEvent.click(screen.getByTestId('calendar-go-today'));

        const yearInput = screen.getByTestId('calendar-year-input');
        await fireEvent.change(yearInput, {target: {value: '2020'}});

        expect(onPrevMonth).toHaveBeenCalledTimes(1);
        expect(onNextMonth).toHaveBeenCalledTimes(1);
        expect(onGoToToday).toHaveBeenCalledTimes(1);
        expect(onSetYear).toHaveBeenCalledWith(2020);

        // The grid itself has not moved: this component renders what it is told.
        expect(screen.getByTestId('calendar-month')).toHaveAttribute('data-month', String(MONTH));
    });

    it('hides the today shortcut when the parent offers no handler', () => {
        render(CalendarMonth, baseProps());
        expect(screen.queryByTestId('calendar-go-today')).toBeNull();
    });
});
