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
 * today with the component's own UTC-based `toISOString().slice(0,10)`, so a
 * literal date can never quietly stop testing the rule the day it slips by.
 */
import {beforeAll, describe, expect, it, vi} from 'vitest';
import {tick} from 'svelte';
import {fireEvent, render, screen, waitFor} from '$test/component';
import DateRangePicker from './DateRangePicker.svelte';

/** A date safely in the past, so no cell is disabled by the future guard. */
const DEF_START = '2024-01-15';
const DEF_END = '2024-02-20';

/** ISO for today / an offset from it, computed exactly like the component does. */
function todayISO(): string {
    return new Date().toISOString().slice(0, 10);
}
function offsetISO(days: number): string {
    const d = new Date();
    d.setDate(d.getDate() + days);
    return d.toISOString().slice(0, 10);
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
