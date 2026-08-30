// @vitest-environment jsdom
/**
 * DateRangePicker — component test (Vitest + jsdom).
 *
 * The range picker is the two-headed cousin of SingleDatePicker: a pair of typed
 * fields over a dual calendar, plus a row of "backwards from today" presets. The
 * interesting behaviour is where those three surfaces meet — a typed date has to
 * pass the same ceiling a calendar cell does, driving one field past the other
 * has to *swap* the pair rather than accept an impossible range, and a preset can
 * never reach past today while the future is forbidden.
 *
 * Everything asserted here is either a value the test supplied (`start`, `end`,
 * the onchange payload) or a state the component publishes (`data-open`,
 * `data-invalid`, `data-active`, the `calendar-day` grid's `data-iso`). Never a
 * translated label — the row shows "1W/1M…" but the section headings, the
 * From/To captions and the formatted dates are i18n/locale output — and never a
 * Tailwind class: the field turns red through `text-red-600`, and matching on
 * that would test the palette.
 *
 * Dates that must be "in the past whatever today is" are hardcoded in 2024;
 * anything about *now* (preset windows, the future guard) is computed relative to
 * today from the **local** calendar fields, so a literal date can never quietly stop
 * testing the rule the day it slips by — and the oracle cannot agree with the
 * component by making the same mistake.
 */
import {beforeAll, describe, expect, it, vi} from 'vitest';
import {tick} from 'svelte';
import {fireEvent, render, screen, waitFor} from '$test/component';
import DateRangePicker from './DateRangePicker.svelte';

/** A date safely in the past, so no cell is disabled by the future guard. */
const DEF_START = '2024-01-15';
const DEF_END = '2024-02-20';

/**
 * Today, and an offset from it, on the **user's** calendar.
 *
 * These used to be written "exactly like the component does" — `new Date()` read at
 * local time and re-serialised through `toISOString()`, which is UTC. That made the
 * oracle share the component's bug: east of Greenwich both were a day early, they
 * agreed, and the preset tests passed while every preset started on the wrong day.
 * Verified: reverting `1W` to the old arithmetic left all 17 tests green.
 *
 * An oracle has to come from the rule, not from the implementation. `todayIso` is the
 * shared helper the component now uses; `offsetISO` is deliberately written out here
 * rather than calling the shared `addDays`, so a mistake in that helper cannot hide
 * itself by being on both sides of the assertion.
 */
function todayISO(): string {
    const d = new Date();
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}
function offsetISO(days: number): string {
    const d = new Date();
    d.setDate(d.getDate() + days);
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

function setup(overrides: Record<string, unknown> = {}) {
    const onchange = vi.fn();
    render(DateRangePicker, {props: {start: DEF_START, end: DEF_END, onchange, ...overrides}});
    return {
        onchange,
        startInput: screen.getByTestId('date-range-input-start') as HTMLInputElement,
        endInput: screen.getByTestId('date-range-input-end') as HTMLInputElement,
        root: screen.getByTestId('date-range-picker-root'),
    };
}

/** Types into a field without committing — commit is blur, Enter or an arrow, deliberately. */
async function type(input: HTMLInputElement, text: string) {
    await fireEvent.input(input, {target: {value: text}});
}

/** The two calendar grids (left, right) once the popover is open. */
function grids(): HTMLElement[] {
    return screen.getAllByTestId('calendar-month');
}

/** A specific day cell inside one of the two grids, addressed by ISO (unique per grid). */
function dayIn(gridIndex: number, iso: string): HTMLButtonElement {
    const el = grids()[gridIndex].querySelector<HTMLButtonElement>(`[data-testid="calendar-day"][data-iso="${iso}"]`);
    if (!el) throw new Error(`no day cell for ${iso} in grid ${gridIndex}`);
    return el;
}

beforeAll(async () => {
    const {setupI18n} = await import('$test/component');
    await setupI18n();
});

describe('DateRangePicker — presets', () => {
    it('a preset sets the end to today and the start a window before it', () => {
        const {onchange} = setup();
        fireEvent.click(screen.getByTestId('date-preset-1w'));
        // 1W is "seven days back to today" — end is today, start is exactly a week earlier.
        expect(onchange).toHaveBeenCalledWith(offsetISO(-7), todayISO());
    });

    it('computes a preset from the calendar day the user is on, not from UTC', () => {
        // 22:30 UTC on 14 June is 00:30 on the 15th in Rome. That two-hour window after
        // midnight is the *only* time the two readings disagree, which is why this test
        // freezes the clock: run at any other hour it passes whatever the component does,
        // and means nothing. Verified — reverting `1W` to the old `toISOString()` form
        // left all 17 tests green until this one existed.
        //
        // The expected values are derived from the frozen instant's LOCAL fields, so the
        // assertion states the rule ("a preset counts from the user's today") in every
        // timezone, rather than hardcoding what Rome happens to see.
        vi.useFakeTimers();
        vi.setSystemTime(new Date('2024-06-14T22:30:00Z'));
        try {
            const {onchange} = setup();
            fireEvent.click(screen.getByTestId('date-preset-1w'));
            expect(onchange).toHaveBeenCalledWith(offsetISO(-7), todayISO());
        } finally {
            vi.useRealTimers();
        }
    });

    it('marks the chosen preset active and no other', async () => {
        setup();
        await fireEvent.click(screen.getByTestId('date-preset-1m'));
        expect(screen.getByTestId('date-preset-1m')).toHaveAttribute('data-active', 'true');
        expect(screen.getByTestId('date-preset-1w')).toHaveAttribute('data-active', 'false');
        expect(screen.getByTestId('date-preset-1y')).toHaveAttribute('data-active', 'false');
    });

    it('never lets a preset reach past today while the future is forbidden', () => {
        const {onchange} = setup();
        const today = todayISO();
        // Every "backwards from today" preset: end pinned to today, start no later than today.
        for (const key of ['1w', '1m', '3m', '6m', '1y', '2y', 'ytd']) {
            onchange.mockClear();
            fireEvent.click(screen.getByTestId(`date-preset-${key}`));
            expect(onchange, `preset ${key} must fire onchange`).toHaveBeenCalledTimes(1);
            const [gotStart, gotEnd] = onchange.mock.calls[0];
            expect(gotEnd, `preset ${key} end must be today`).toBe(today);
            expect(gotStart <= today, `preset ${key} start must not be in the future`).toBe(true);
        }
    });

    it('MAX resolves to the min/max sentinels the controller expands later', () => {
        const {onchange} = setup();
        fireEvent.click(screen.getByTestId('date-preset-max'));
        expect(onchange).toHaveBeenCalledWith('min', 'max');
        expect(screen.getByTestId('date-preset-max')).toHaveAttribute('data-active', 'true');
    });
});

describe('DateRangePicker — the range invariant is a swap, never an impossible range', () => {
    it('typing a start past the end swaps the pair instead of refusing it', async () => {
        const {startInput, onchange} = setup({start: '2024-02-01', end: '2024-02-10'});
        await fireEvent.focus(startInput);
        // The user drives "start" to a date after the current end. That is not a range;
        // the picker reads it as "I want that date" and swaps, so it becomes the end.
        await type(startInput, '2024-02-20');
        await fireEvent.blur(startInput);
        await waitFor(() => expect(onchange).toHaveBeenCalledWith('2024-02-10', '2024-02-20'));
    });

    it('clicking a later day then an earlier one yields start=earlier, end=later', async () => {
        const {startInput, onchange, root} = setup({start: '2024-01-15', end: '2024-02-20'});
        await fireEvent.focus(startInput); // opens the dual calendar (left=Jan, right=Feb)
        await fireEvent.click(dayIn(1, '2024-02-25')); // first click, the later date
        await fireEvent.click(dayIn(0, '2024-01-10')); // second click, the earlier date
        expect(onchange).toHaveBeenCalledWith('2024-01-10', '2024-02-25');
        expect(root).toHaveAttribute('data-open', 'false'); // a completed pick closes it
    });
});

describe('DateRangePicker — the two fields are independent', () => {
    it('editing the end field leaves the start value untouched', async () => {
        const {startInput, endInput, onchange} = setup({start: '2024-02-05', end: '2024-02-20'});
        await fireEvent.focus(endInput);
        await type(endInput, '2024-02-15');
        await fireEvent.blur(endInput);
        // The published range keeps the original start; only the end moved.
        await waitFor(() => expect(onchange).toHaveBeenCalledWith('2024-02-05', '2024-02-15'));
    });
});

describe('DateRangePicker — arrow stepping', () => {
    it('ArrowDown steps the focused field back one day and opens the calendar', async () => {
        const {startInput, root} = setup({start: '2024-01-15', end: '2024-02-20'});
        await fireEvent.focus(startInput);
        await fireEvent.keyDown(startInput, {key: 'ArrowDown'});
        await fireEvent.keyUp(startInput, {key: 'ArrowDown'});
        await tick();
        expect(startInput).toHaveValue('2024-01-14');
        expect(root).toHaveAttribute('data-open', 'true');
    });
});

describe('DateRangePicker — opening, closing and what each commits', () => {
    it('focusing a field opens the calendar and publishes that it is open', async () => {
        const {startInput, root} = setup();
        expect(root).toHaveAttribute('data-open', 'false');
        await fireEvent.focus(startInput);
        expect(root).toHaveAttribute('data-open', 'true');
        expect(screen.getByTestId('date-range-popover')).toBeInTheDocument();
    });

    it('Escape closes the calendar and abandons the typed edit, publishing nothing', async () => {
        const {startInput, root, onchange} = setup();
        await fireEvent.focus(startInput);
        await type(startInput, '2024-01-10');
        await fireEvent.keyDown(startInput, {key: 'Escape'});
        expect(root).toHaveAttribute('data-open', 'false');
        expect(onchange).not.toHaveBeenCalled();
    });

    it('clicking outside closes the calendar', async () => {
        const {startInput, root} = setup();
        await fireEvent.focus(startInput);
        expect(root).toHaveAttribute('data-open', 'true');
        await fireEvent.click(document.body);
        expect(root).toHaveAttribute('data-open', 'false');
    });

    it('Enter commits the typed date and closes the calendar', async () => {
        const {startInput, root, onchange} = setup({start: '2024-01-15', end: '2024-02-20'});
        await fireEvent.focus(startInput);
        await type(startInput, '2024-01-10');
        await fireEvent.keyDown(startInput, {key: 'Enter'});
        await waitFor(() => expect(onchange).toHaveBeenCalledWith('2024-01-10', '2024-02-20'));
        expect(root).toHaveAttribute('data-open', 'false');
    });
});

/**
 * The typed-field seam. These four encode the two decisions already taken for
 * SingleDatePicker and — since this picker carried the very same pre-fix logic
 * (continuous validation; refused text discarded on blur) — brought here to keep
 * the two pickers answering a mistyped date the same way.
 */
describe('DateRangePicker — a mistyped date is armed, and stays on screen', () => {
    it('stays quiet while a date is half typed, and complains only on the way out', async () => {
        const {startInput} = setup();
        await fireEvent.focus(startInput);
        // `2024-` fails to parse for exactly as long as it takes to press one more key.
        // Mid-edit is not a mistake, so the field must not be red yet.
        await type(startInput, '2024-');
        expect(startInput).toHaveAttribute('data-invalid', 'false');
        await fireEvent.blur(startInput);
        expect(startInput).toHaveAttribute('data-invalid', 'true');
    });

    it('keeps unreadable text on screen after blur instead of silently reverting', async () => {
        const {startInput, onchange} = setup();
        await fireEvent.focus(startInput);
        await type(startInput, 'not a date');
        expect(startInput).toHaveValue('not a date');
        await fireEvent.blur(startInput);
        // The text survives the blur — that is what makes the refusal visible. It used to
        // be thrown away here, putting the previous value back with nothing to explain why.
        expect(startInput).toHaveValue('not a date');
        expect(startInput).toHaveAttribute('data-invalid', 'true');
        expect(onchange).not.toHaveBeenCalled();
    });

    it('drops the complaint as soon as the user resumes editing', async () => {
        const {startInput} = setup();
        await fireEvent.focus(startInput);
        await type(startInput, '2024-');
        await fireEvent.blur(startInput);
        expect(startInput).toHaveAttribute('data-invalid', 'true');
        await type(startInput, '2024-0'); // still in progress, but editing again
        expect(startInput).toHaveAttribute('data-invalid', 'false');
    });

    it('reads an emptied field as an abandoned edit and publishes nothing', async () => {
        const {startInput, onchange} = setup();
        await fireEvent.focus(startInput);
        await type(startInput, '');
        await fireEvent.blur(startInput);
        expect(startInput.value).not.toBe(''); // the stored value came back
        expect(startInput).toHaveAttribute('data-invalid', 'false');
        expect(onchange).not.toHaveBeenCalled();
    });

    it('arms each field independently — a bad start does not light up the end', async () => {
        const {startInput, endInput} = setup();
        await fireEvent.focus(startInput);
        await type(startInput, 'nonsense');
        await fireEvent.blur(startInput);
        expect(startInput).toHaveAttribute('data-invalid', 'true');
        expect(endInput).toHaveAttribute('data-invalid', 'false');
    });
});

// ---------------------------------------------------------------------------
// The two calendar columns. Each has its own prev/next/year/today controls, but
// neither may cross the other: driving one past its neighbour SWAPS the pair so
// the left month is never after the right. jsdom has no layout, so nothing here
// touches position — only the data-year/data-month the grids publish. There are
// two of every control (one per column); getAll…[0] is the left, [1] the right.
// ---------------------------------------------------------------------------

/** A calendar nav control on the given side (0 = left column, 1 = right column). */
function navBtn(testid: string, side: 0 | 1): HTMLButtonElement {
    return screen.getAllByTestId(testid)[side] as HTMLButtonElement;
}
/** The year <input> of the given column. */
function yearField(side: 0 | 1): HTMLInputElement {
    return screen.getAllByTestId('calendar-year-input')[side] as HTMLInputElement;
}
/** What a grid publishes about the month it is showing — a state, never a label. */
function ym(gridIndex: 0 | 1): {year: string | null; month: string | null} {
    const g = grids()[gridIndex];
    return {year: g.getAttribute('data-year'), month: g.getAttribute('data-month')};
}

describe('DateRangePicker — the two calendar columns step without crossing', () => {
    it('the left column steps back across a year boundary', async () => {
        const {startInput} = setup({start: '2024-01-15', end: '2024-02-20'});
        await fireEvent.focus(startInput); // left = Jan 2024, right = Feb 2024
        await fireEvent.click(navBtn('calendar-prev-month', 0));
        await tick();
        // January rolls back to the previous December, pulling the year with it.
        expect(ym(0)).toEqual({year: '2023', month: '11'});
    });

    it('the right column steps forward across a year boundary', async () => {
        const {startInput} = setup({start: '2024-11-10', end: '2024-12-20'});
        await fireEvent.focus(startInput); // left = Nov, right = Dec 2024
        await fireEvent.click(navBtn('calendar-next-month', 1));
        await tick();
        expect(ym(1)).toEqual({year: '2025', month: '0'});
    });

    it('advancing the left column past the right swaps the pair', async () => {
        const {startInput} = setup({start: '2024-01-15', end: '2024-02-20'});
        await fireEvent.focus(startInput); // left = Jan (0), right = Feb (1)
        await fireEvent.click(navBtn('calendar-next-month', 0)); // left → Feb, ties the right, no swap
        await fireEvent.click(navBtn('calendar-next-month', 0)); // left → Mar, past the right → swap
        await tick();
        // The swap keeps left ≤ right, so the columns read Feb then Mar — not Mar then Feb.
        expect(ym(0)).toEqual({year: '2024', month: '1'});
        expect(ym(1)).toEqual({year: '2024', month: '2'});
    });

    it('moving the right column before the left swaps the pair', async () => {
        const {startInput} = setup({start: '2024-01-15', end: '2024-02-20'});
        await fireEvent.focus(startInput); // left = Jan (0), right = Feb (1)
        await fireEvent.click(navBtn('calendar-prev-month', 1)); // right → Jan, ties the left, no swap
        await fireEvent.click(navBtn('calendar-prev-month', 1)); // right → Dec 2023, before the left → swap
        await tick();
        expect(ym(0)).toEqual({year: '2023', month: '11'});
        expect(ym(1)).toEqual({year: '2024', month: '0'});
    });

    it('typing a left year past the right swaps the pair', async () => {
        const {startInput} = setup({start: '2024-01-15', end: '2024-02-20'});
        await fireEvent.focus(startInput);
        await fireEvent.change(yearField(0), {target: {value: '2025'}});
        await tick();
        // Left jumped to Jan 2025, past the right's Feb 2024 → swap restores left ≤ right.
        expect(ym(0)).toEqual({year: '2024', month: '1'});
        expect(ym(1)).toEqual({year: '2025', month: '0'});
    });

    it('typing a right year before the left swaps the pair', async () => {
        const {startInput} = setup({start: '2024-06-10', end: '2024-07-20'});
        await fireEvent.focus(startInput); // left = Jun (5), right = Jul (6)
        await fireEvent.change(yearField(1), {target: {value: '2020'}});
        await tick();
        expect(ym(0)).toEqual({year: '2020', month: '6'});
        expect(ym(1)).toEqual({year: '2024', month: '5'});
    });

    it('the today button snaps a column to the current month, each side on its own', async () => {
        // Noon UTC on the 14th is the 14th in every test timezone, so the expected month is
        // stable wherever this runs; the frozen clock also makes goToToday deterministic.
        vi.useFakeTimers();
        vi.setSystemTime(new Date('2024-06-14T12:00:00Z'));
        try {
            const {startInput} = setup({start: '2024-01-15', end: '2024-02-20'});
            await fireEvent.focus(startInput);
            await fireEvent.click(navBtn('calendar-go-today', 0));
            await tick();
            expect(ym(0)).toEqual({year: '2024', month: '5'}); // June, from the left button alone
            await fireEvent.click(navBtn('calendar-go-today', 1));
            await tick();
            expect(ym(1)).toEqual({year: '2024', month: '5'});
        } finally {
            vi.useRealTimers();
        }
    });
});

// ---------------------------------------------------------------------------
// Preset auto-detection. When the range wasn't chosen through the row but the
// props happen to match a "N back from today" window (end === today), the picker
// lights that preset on its own. The detection loop walks EVERY preset — the six
// hidden jolly windows included — so a range matching none is the one case that
// exercises all of computeStartDate's arms.
// ---------------------------------------------------------------------------

describe('DateRangePicker — a range that matches a preset window lights it up', () => {
    it('a week-wide range back from today activates 1W without a click', () => {
        vi.useFakeTimers();
        vi.setSystemTime(new Date('2024-06-14T12:00:00Z'));
        try {
            setup({start: offsetISO(-7), end: todayISO()});
            expect(screen.getByTestId('date-preset-1w')).toHaveAttribute('data-active', 'true');
        } finally {
            vi.useRealTimers();
        }
    });

    it('a range matching no window leaves every preset inactive', () => {
        // 2020-03-03 is not a whole number of weeks/months/years before the frozen today, and
        // none of YTD/MTD/QTD/WTD reach that far — so the detection loop runs to the end,
        // computing (and rejecting) every arm of computeStartDate, and settles on none.
        vi.useFakeTimers();
        vi.setSystemTime(new Date('2024-06-14T12:00:00Z'));
        try {
            setup({start: '2020-03-03', end: todayISO()});
            for (const key of ['1w', '1m', '3m', '6m', '1y', '2y', 'ytd', 'max', 'custom']) {
                expect(screen.getByTestId(`date-preset-${key}`), `preset ${key}`).toHaveAttribute('data-active', 'false');
            }
        } finally {
            vi.useRealTimers();
        }
    });
});

// ---------------------------------------------------------------------------
// The custom "N units back" window. Opening it applies a range immediately, and
// the range is the contract: it always ends today and starts strictly before —
// asserting the shared date arithmetic to the day here would just re-run the
// implementation, so the rule is what's checked.
// ---------------------------------------------------------------------------

describe('DateRangePicker — the custom "N units back" window', () => {
    it('opening the custom window publishes a range that ends today and starts in the past', async () => {
        const {onchange} = setup();
        await fireEvent.click(screen.getByTestId('date-preset-custom'));
        const today = todayISO();
        expect(onchange).toHaveBeenCalledTimes(1);
        const [gotStart, gotEnd] = onchange.mock.calls[0];
        expect(gotEnd).toBe(today);
        expect(gotStart < today).toBe(true);
        // The plain button is gone, replaced by the amount editor — the state changed, visibly.
        expect(screen.queryByTestId('date-preset-custom')).toBeNull();
        expect(screen.getByTestId('date-range-custom-amount')).toBeInTheDocument();
    });

    it('changing the amount republishes a fresh window without leaving edit mode', async () => {
        const {onchange} = setup();
        await fireEvent.click(screen.getByTestId('date-preset-custom'));
        onchange.mockClear();
        const amount = screen.getByTestId('date-range-custom-amount') as HTMLInputElement;
        await fireEvent.input(amount, {target: {value: '5'}});
        // The amount effect re-applies on a microtask; whatever the number, the window ends today.
        await waitFor(() => expect(onchange).toHaveBeenCalled());
        const [gotStart, gotEnd] = onchange.mock.calls.at(-1)!;
        expect(gotEnd).toBe(todayISO());
        expect(gotStart < todayISO()).toBe(true);
        expect(screen.getByTestId('date-range-custom-amount')).toBeInTheDocument(); // still editing
    });

    it('Escape leaves the custom editor and restores the plain button', async () => {
        setup();
        await fireEvent.click(screen.getByTestId('date-preset-custom'));
        await fireEvent.keyDown(screen.getByTestId('date-range-custom-amount'), {key: 'Escape'});
        await tick();
        expect(screen.queryByTestId('date-range-custom-amount')).toBeNull();
        expect(screen.getByTestId('date-preset-custom')).toBeInTheDocument();
    });
});

describe('DateRangePicker — compact fields show the raw ISO', () => {
    it('renders the stored dates as YYYY-MM-DD when compact, not a localised label', () => {
        // compact is the narrow-cell variant: the field text is the ISO the test supplied,
        // which is exactly what makes it safe to assert on (a wide field would be i18n output).
        const {startInput, endInput} = setup({compact: true, start: '2024-01-15', end: '2024-02-20'});
        expect(startInput).toHaveValue('2024-01-15');
        expect(endInput).toHaveValue('2024-02-20');
    });
});
