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
import {fireEvent, render, screen, waitFor} from '$test/component';
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

describe('SingleDatePicker — optional clearing', () => {
    it('clears an optional value from its dedicated control and reports the empty value', async () => {
        const {input, root, onchange} = setup({clearable: true});

        await fireEvent.focus(input);
        expect(root).toHaveAttribute('data-open', 'true');
        await fireEvent.click(screen.getByTestId(`${TID}-clear`));

        expect(input).toHaveValue('');
        expect(root).toHaveAttribute('data-open', 'false');
        expect(onchange).toHaveBeenCalledExactlyOnceWith('');
    });

    it('commits a typed empty value only when the caller opted into clearing', async () => {
        const {input, onchange} = setup({clearable: true});

        await type(input, '');
        await fireEvent.blur(input);

        expect(input).toHaveValue('');
        expect(onchange).toHaveBeenCalledExactlyOnceWith('');
    });

    it('keeps the historical required/default behavior when clearable is omitted', async () => {
        const {input, onchange} = setup();

        expect(screen.queryByTestId(`${TID}-clear`)).toBeNull();
        await type(input, '');
        await fireEvent.blur(input);

        expect(input).toHaveValue(PAST);
        expect(onchange).not.toHaveBeenCalled();
    });

    it('does not let a disabled optional picker clear its value', async () => {
        const {input, onchange} = setup({clearable: true, disabled: true});
        const clear = screen.getByTestId(`${TID}-clear`);

        expect(clear).toBeDisabled();
        await fireEvent.click(clear);

        expect(input).toHaveValue(PAST);
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

describe('SingleDatePicker — the form it sits in', () => {
    /**
     * The refusal above is visible, but visibility is not a guarantee: the picker
     * lives inside `<form>`s whose submit button is one Tab away from the field.
     * While text the picker refuses is on screen, the *stored* value is still the
     * previous date — so a submit that goes through sends a date nobody typed,
     * behind text that says something else. `setCustomValidity` is what makes
     * that submit impossible, and this block asserts the native gate rather than
     * the red border: a class can be restyled, a blocked submit cannot.
     *
     * `submits` records both halves on purpose. Asserting only on `input.value`
     * would miss the entire hazard, which is precisely that the visible text and
     * the committed value have come apart.
     */
    function setupInForm(overrides: Record<string, unknown> = {}) {
        const form = document.createElement('form');
        document.body.appendChild(form);
        const submits: {visible: string; committed: string}[] = [];
        let committed = (overrides.value as string | undefined) ?? PAST;
        const onchange = vi.fn((next: string) => {
            committed = next;
        });
        // `target` is a Svelte mount option, so the form *is* the container the
        // testing library tears down after the test (see svelte-core setup.js:
        // a container whose parent is document.body is removed on cleanup).
        render(SingleDatePicker, {target: form, props: {value: PAST, onchange, testid: TID, ...overrides}});
        const input = screen.getByTestId(TID) as HTMLInputElement;
        form.addEventListener('submit', (event) => {
            event.preventDefault();
            submits.push({visible: input.value, committed});
        });
        return {form, submits, onchange, input, root: screen.getByTestId(`${TID}-root`)};
    }

    it('submits normally while the field holds the value it was given', () => {
        const {form, submits} = setupInForm();

        form.requestSubmit();

        expect(submits).toEqual([{visible: PAST, committed: PAST}]);
    });

    it.each([
        ['unreadable text', () => 'not a date', {}],
        ['a future date the caller disallows', () => TOMORROW, {}],
        ['a date the caller greyed out', () => isoOffset(-20), {disabledDates: new Set([isoOffset(-20)])}],
    ])('refuses to submit the stored date behind %s, and submits again once it is corrected', async (_name, refusedText, props) => {
        const refused = refusedText();
        const {form, input, root, submits, onchange} = setupInForm(props);

        await type(input, refused);
        form.requestSubmit();

        // The gate is native and it is about *this* control.
        expect(input.validity.customError).toBe(true);
        expect(input.checkValidity()).toBe(false);
        expect(form.checkValidity()).toBe(false);
        // Nothing left, so the stored PAST never went out behind the refused text.
        expect(submits).toEqual([]);
        expect(onchange).not.toHaveBeenCalled();
        expect(input.value).toBe(refused);
        // The native `invalid` event is also what arms the visible complaint, so
        // the user is not left guessing why the button did nothing.
        await waitFor(() => expect(root).toHaveAttribute('data-invalid', 'true'));

        const corrected = isoOffset(-33);
        await type(input, corrected);
        await fireEvent.blur(input);
        form.requestSubmit();

        expect(input.validity.customError).toBe(false);
        expect(form.checkValidity()).toBe(true);
        expect(root).toHaveAttribute('data-invalid', 'false');
        expect(submits).toEqual([{visible: corrected, committed: corrected}]);
    });

    it('keeps an emptied optional field submittable and sends the cleared value', () => {
        const {form, input, submits} = setupInForm({clearable: true});

        fireEvent.input(input, {target: {value: ''}});
        fireEvent.blur(input);
        form.requestSubmit();

        expect(input.validity.customError).toBe(false);
        expect(submits).toEqual([{visible: '', committed: ''}]);
    });

    it('keeps an emptied required field submittable with the value it restores', async () => {
        // An empty field is an abandoned edit, not a refusal: the picker puts the
        // stored date back, so there is nothing for the form to block. Blocking
        // here would make a required picker unsubmittable after a stray Backspace.
        const {form, input, submits, onchange} = setupInForm();

        await type(input, '');
        await fireEvent.blur(input);
        form.requestSubmit();

        expect(input.validity.customError).toBe(false);
        expect(onchange).not.toHaveBeenCalled();
        expect(submits).toEqual([{visible: PAST, committed: PAST}]);
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
