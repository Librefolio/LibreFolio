// @vitest-environment jsdom
/**
 * SingleDatePicker — component test (Vitest + jsdom).
 *
 * The picker is two inputs pretending to be one: a text field that accepts what
 * people actually type, and a calendar popover. The interesting behaviour is at
 * the seam — a typed date has to pass exactly the same gates the calendar
 * enforces on a day cell, otherwise the field is a way around the rule.
 *
 * Everything asserted here is either a value the test supplied or a state the
 * component publishes (`data-open`, `data-invalid`, `data-iso`, `data-state`).
 * Never a translated label, never a Tailwind class: the field turns red through
 * `border-red-400`, and matching on that would test the palette.
 *
 * Dates are computed relative to today rather than hardcoded. "Tomorrow is
 * refused unless `allowFuture`" is a rule about *now*, so a literal date would
 * quietly stop testing it the day it slipped into the past.
 */
import {beforeAll, describe, expect, it, vi} from 'vitest';
import {fireEvent, render, screen} from '$test/component';
import SingleDatePicker from './SingleDatePicker.svelte';

const TID = 'dp';

/** Local-date ISO, matching the component's own `todayIso()` — not `toISOString()`, which is UTC. */
function isoOffset(days: number): string {
    const d = new Date();
    d.setDate(d.getDate() + days);
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

const TODAY = isoOffset(0);
const TOMORROW = isoOffset(1);
/** Far enough back to be in another month whatever today is. */
const PAST = isoOffset(-60);

/** `YYYY-MM-DD` → `DD/MM/YYYY`, the order a European user types. */
function euro(iso: string, sep = '/'): string {
    const [y, m, d] = iso.split('-');
    return `${d}${sep}${m}${sep}${y}`;
}

function setup(overrides: Record<string, unknown> = {}) {
    const onchange = vi.fn();
    render(SingleDatePicker, {props: {value: PAST, onchange, testid: TID, ...overrides}});
    return {
        onchange,
        input: screen.getByTestId(TID) as HTMLInputElement,
        root: screen.getByTestId(`${TID}-root`),
        button: screen.getByTestId(`${TID}-calendar-button`),
    };
}

/** Types into the field without committing — commit is blur or Enter, deliberately. */
async function type(input: HTMLInputElement, text: string) {
    await fireEvent.input(input, {target: {value: text}});
}

beforeAll(async () => {
    const {setupI18n} = await import('$test/component');
    await setupI18n();
});

describe('SingleDatePicker — typing', () => {
    it('shows the value it was given', () => {
        const {input} = setup();
        expect(input.value).toBe(PAST);
    });

    it('commits an ISO date on blur', async () => {
        const {input, onchange} = setup();
        const target = isoOffset(-30);
        await type(input, target);
        await fireEvent.blur(input);
        expect(onchange).toHaveBeenCalledWith(target);
    });

    it.each([
        ['slashes', '/'],
        ['dashes', '-'],
        ['dots', '.'],
    ])('reads a day-first date written with %s', async (_name, sep) => {
        const {input, onchange} = setup();
        const target = isoOffset(-45);
        await type(input, euro(target, sep));
        await fireEvent.blur(input);
        expect(onchange).toHaveBeenCalledWith(target);
    });

    it('keeps unreadable text on screen and flags it, instead of silently reverting', async () => {
        const {input, root, onchange} = setup();
        await type(input, 'not a date');
        expect(input.value).toBe('not a date');
        // Still typing: no complaint yet.
        expect(root).toHaveAttribute('data-invalid', 'false');
        await fireEvent.blur(input);
        expect(onchange).not.toHaveBeenCalled();
        // The text survives the blur, which is what makes the refusal visible. It used
        // to be discarded here, putting PAST back with nothing to say why.
        expect(input.value).toBe('not a date');
        expect(root).toHaveAttribute('data-invalid', 'true');
    });

    it('reads an emptied field as an abandoned edit and restores the stored value', async () => {
        const {input, root, onchange} = setup();
        await type(input, '');
        await fireEvent.blur(input);
        expect(input.value).toBe(PAST);
        expect(root).toHaveAttribute('data-invalid', 'false');
        expect(onchange).not.toHaveBeenCalled();
    });

    it('does not fire onchange when the typed date equals the current one', async () => {
        const {input, onchange} = setup();
        await type(input, euro(PAST));
        await fireEvent.blur(input);
        expect(onchange).not.toHaveBeenCalled();
    });

    it('Escape abandons what was typed and puts the stored value back', async () => {
        const {input, onchange} = setup();
        await type(input, '1999-01-01');
        await fireEvent.keyDown(input, {key: 'Escape'});
        expect(input.value).toBe(PAST);
        expect(onchange).not.toHaveBeenCalled();
    });
});

describe('SingleDatePicker — the gates a typed date must pass', () => {
    it('marks a future date invalid — but only once the user leaves it there', async () => {
        const {input, root, onchange} = setup();
        await type(input, TOMORROW);
        expect(root).toHaveAttribute('data-invalid', 'false');
        await fireEvent.blur(input);
        expect(root).toHaveAttribute('data-invalid', 'true');
        expect(onchange).not.toHaveBeenCalled();
        expect(input.value).toBe(TOMORROW);
    });

    it('accepts the same future date once allowFuture is on', async () => {
        const {input, root, onchange} = setup({allowFuture: true});
        await type(input, TOMORROW);
        expect(root).toHaveAttribute('data-invalid', 'false');
        await fireEvent.blur(input);
        expect(root).toHaveAttribute('data-invalid', 'false');
        expect(onchange).toHaveBeenCalledWith(TOMORROW);
    });

    it('refuses a date the calendar greys out, and says so on the way out', async () => {
        const blocked = isoOffset(-20);
        const {input, root, onchange} = setup({disabledDates: new Set([blocked])});
        await type(input, blocked);
        expect(root).toHaveAttribute('data-invalid', 'false');
        await fireEvent.blur(input);
        expect(root).toHaveAttribute('data-invalid', 'true');
        expect(onchange).not.toHaveBeenCalled();
    });

    it('stays quiet while a date is half typed, and complains when the user walks away', async () => {
        // A date in progress is not a mistake: `2024-08-0` fails to parse for exactly as
        // long as it takes to press one more key. The field used to be red for that whole
        // time — from the first character to the last — which is the one moment the user
        // does not need to be told anything.
        const {input, root} = setup();
        await type(input, '2024-');
        expect(root).toHaveAttribute('data-invalid', 'false');
        await fireEvent.blur(input);
        expect(root).toHaveAttribute('data-invalid', 'true');
    });

    it('drops the complaint as soon as the user starts editing again', async () => {
        const {input, root} = setup();
        await type(input, '2024-');
        await fireEvent.blur(input);
        expect(root).toHaveAttribute('data-invalid', 'true');
        await fireEvent.focus(input);
        // Focus alone is not editing — the refusal still stands until something changes.
        expect(root).toHaveAttribute('data-invalid', 'true');
        await type(input, '2024-0');
        expect(root).toHaveAttribute('data-invalid', 'false');
    });

    it('Enter complains about an unreadable date without waiting for the user to leave', async () => {
        // Enter means "this is my answer", so it is the same moment as walking away.
        const {input, root} = setup();
        await fireEvent.focus(input);
        await type(input, '2024-');
        expect(root).toHaveAttribute('data-invalid', 'false');
        await fireEvent.keyDown(input, {key: 'Enter'});
        expect(root).toHaveAttribute('data-invalid', 'true');
    });
});

describe('SingleDatePicker — the calendar', () => {
    it('opens on focus and publishes that it is open', async () => {
        const {input, root} = setup();
        expect(root).toHaveAttribute('data-open', 'false');
        await fireEvent.focus(input);
        expect(root).toHaveAttribute('data-open', 'true');
        expect(screen.getByTestId(`${TID}-popover`)).toBeInTheDocument();
    });

    it('the icon toggles it both ways', async () => {
        const {root, button} = setup();
        await fireEvent.click(button);
        expect(root).toHaveAttribute('data-open', 'true');
        await fireEvent.click(button);
        expect(root).toHaveAttribute('data-open', 'false');
    });

    it('opens on the month of the current value, not on today', async () => {
        const {button} = setup();
        await fireEvent.click(button);
        const [y, m] = PAST.split('-').map(Number);
        const grid = screen.getByTestId('calendar-month');
        expect(grid).toHaveAttribute('data-year', String(y));
        expect(grid).toHaveAttribute('data-month', String(m - 1));
    });

    it('follows along while a date is typed, so a misreading is visible before it is committed', async () => {
        const {input} = setup();
        await fireEvent.focus(input);
        const target = isoOffset(-200);
        const [y, m] = target.split('-').map(Number);
        await type(input, euro(target));
        const grid = screen.getByTestId('calendar-month');
        expect(grid).toHaveAttribute('data-year', String(y));
        expect(grid).toHaveAttribute('data-month', String(m - 1));
    });

    it('picking a day commits it and closes', async () => {
        const {input, root, onchange} = setup();
        await fireEvent.focus(input);
        const target = `${PAST.slice(0, 8)}05`;
        const day = document.querySelector(`[data-testid="calendar-day"][data-iso="${target}"]`);
        expect(day, `the grid must contain ${target}`).not.toBeNull();
        await fireEvent.click(day!);
        expect(onchange).toHaveBeenCalledWith(target);
        expect(root).toHaveAttribute('data-open', 'false');
        expect(input.value).toBe(target);
    });

    it('highlights the date being typed rather than the stored one', async () => {
        const {input} = setup();
        await fireEvent.focus(input);
        const target = `${PAST.slice(0, 8)}11`;
        await type(input, target);
        const day = document.querySelector(`[data-testid="calendar-day"][data-iso="${target}"]`);
        expect(day).toHaveAttribute('data-state', 'selected');
    });

    it('Enter commits and closes; pressing it again asks the calendar back', async () => {
        const {input, root, onchange} = setup();
        await fireEvent.focus(input);
        expect(root).toHaveAttribute('data-open', 'true');
        const target = isoOffset(-15);
        await type(input, target);
        await fireEvent.keyDown(input, {key: 'Enter'});
        expect(onchange).toHaveBeenCalledWith(target);
        expect(root).toHaveAttribute('data-open', 'false');
        await fireEvent.keyDown(input, {key: 'Enter'});
        expect(root).toHaveAttribute('data-open', 'true');
    });

    it('stays shut when the picker is disabled', async () => {
        const {input, root, button} = setup({disabled: true});
        await fireEvent.click(button);
        await fireEvent.focus(input);
        expect(root).toHaveAttribute('data-open', 'false');
    });
});

describe('SingleDatePicker — arrow stepping', () => {
    it('ArrowDown moves back one day and opens the calendar on the result', async () => {
        const {input} = setup();
        const [y, m, d] = PAST.split('-').map(Number);
        const expected = new Date(y, m - 1, d - 1);
        const expectedIso = `${expected.getFullYear()}-${String(expected.getMonth() + 1).padStart(2, '0')}-${String(expected.getDate()).padStart(2, '0')}`;
        await fireEvent.keyDown(input, {key: 'ArrowDown'});
        await fireEvent.keyUp(input, {key: 'ArrowDown'});
        expect(input.value).toBe(expectedIso);
        expect(screen.getByTestId(`${TID}-root`)).toHaveAttribute('data-open', 'true');
    });

    it('stops at today instead of stepping into the future', async () => {
        const {input} = setup({value: TODAY});
        await fireEvent.keyDown(input, {key: 'ArrowUp'});
        await fireEvent.keyUp(input, {key: 'ArrowUp'});
        expect(input.value).toBe(TODAY);
    });

    it('steps past today when the future is allowed', async () => {
        const {input} = setup({value: TODAY, allowFuture: true});
        await fireEvent.keyDown(input, {key: 'ArrowUp'});
        await fireEvent.keyUp(input, {key: 'ArrowUp'});
        expect(input.value).toBe(TOMORROW);
    });
});
