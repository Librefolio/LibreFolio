// @vitest-environment jsdom
/**
 * SchedulerConfigModal — component test (Vitest + jsdom).
 *
 * The dialog that decides when the scheduler runs: a polling frequency, a set of
 * history-sync times, the weekdays it runs on, a lookback horizon, and the IANA
 * timezone the times are *displayed* in. Times are stored in UTC and converted
 * both ways, which is where nearly all of its branches live.
 *
 * Why a component test. The interesting half of this file is arithmetic —
 * midnight wrap in both directions, a duplicate that must be swallowed, a last
 * weekday that must refuse to switch off, and the `catch` that gives up on an
 * unparseable timezone. An E2E can reach the happy save; it cannot make the
 * clock cross midnight or the server fail on demand without changing global
 * settings that every other test in the suite reads.
 *
 * On not asserting translated text. `$lib/i18n` is mocked with an identity
 * translator, so `$_('settings.global.scheduler.historyDaysMon')` renders as
 * that literal key. Assertions name keys, never sentences.
 *
 * On not asserting CSS. A selected weekday is expressed *only* by a Tailwind
 * class — there is no `aria-pressed`, no `data-selected` (this is in the report
 * as a requested attribute). So day selection is never read off the button; it
 * is read off the two places the product does publish it: the `days` string in
 * the save payload, and whether Save is enabled at all, since `canSave` requires
 * at least one day. Both are contracts rather than styling.
 *
 * Timezones are pinned to fixed-offset zones — Asia/Kolkata (+05:30) and
 * America/Bogota (−05:00) never observe DST — so the expected values are
 * constants and not a function of the day the suite runs on. No clock stubbing
 * is needed for them, and none is done.
 *
 * One behaviour recorded here is a characterisation, not an endorsement, and it
 * says so in its own test: changing the timezone does not re-convert the times
 * already on screen, so the same digits silently come to mean a different
 * instant.
 */
import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';
import {readable} from 'svelte/store';
import {tick} from 'svelte';
import {cleanup, fireEvent, render, screen, waitFor, within} from '$test/component';

vi.mock('$lib/i18n', () => ({_: readable((key: string) => key)}));
vi.mock('$lib/api', () => ({zodiosApi: {axios: {patch: vi.fn()}}}));
vi.mock('$lib/stores/app/notify.svelte', () => ({notify: vi.fn()}));

import SchedulerConfigModal from './SchedulerConfigModal.svelte';
import {zodiosApi} from '$lib/api';
import {notify} from '$lib/stores/app/notify.svelte';

const patch = vi.mocked(zodiosApi.axios.patch);
const notified = vi.mocked(notify);

/**
 * +05:30 all year: no DST, so every expected value below is a constant. Used as
 * a *stored* zone only — ICU still lists it under its legacy alias
 * (`Asia/Calcutta`), so it is not a zone the picker can be asked to show.
 */
const KOLKATA = 'Asia/Kolkata';
/** −05:00 all year, and spelled the same in the picker's list as in ICU. */
const BOGOTA = 'America/Bogota';

const DEFAULTS = {
    frequency: 10,
    times: '09:00,17:30',
    days: 'mon,wed',
    horizon: 14,
};

interface Mounted {
    onsave: ReturnType<typeof vi.fn>;
    rerender: (props: Record<string, unknown>) => Promise<void>;
    container: HTMLElement;
}

function mount(overrides: Record<string, unknown> = {}): Mounted {
    const onsave = vi.fn();
    const result = render(SchedulerConfigModal, {
        open: true,
        serverTz: 'UTC',
        serverNowUtc: '2026-01-15 12:00:00',
        schedulerTimezone: 'UTC',
        currentValues: {...DEFAULTS},
        onsave,
        ...overrides,
    });
    return {onsave, rerender: result.rerender as Mounted['rerender'], container: result.container};
}

/** The time chips, in DOM order, read off the accessible name of their × button. */
function slots(): string[] {
    return screen.queryAllByRole('button', {name: /^Remove /}).map((b) => (b.getAttribute('aria-label') ?? '').replace('Remove ', ''));
}

function saveButton(): HTMLElement {
    return screen.getByTestId('scheduler-config-save');
}

function timeInput(): HTMLElement {
    return screen.getByTestId('scheduler-config-time-input');
}

function frequencyInput(): HTMLElement {
    return screen.getByLabelText('settings.global.scheduler.currentPriceFreqLabel');
}

function horizonInput(): HTMLElement {
    return within(screen.getByTestId('scheduler-config-horizon')).getByRole('spinbutton');
}

function tzSearchInput(): HTMLElement {
    return within(screen.getByTestId('scheduler-config-timezone')).getByRole('textbox');
}

function dayButton(day: string): HTMLElement {
    const label = `settings.global.scheduler.historyDays${day.charAt(0).toUpperCase()}${day.slice(1)}`;
    return screen.getByRole('button', {name: label});
}

/** The body of the single PATCH the modal sends, as a key → value map. */
function savedKeys(): Record<string, string> {
    expect(patch).toHaveBeenCalledOnce();
    const [url, body] = patch.mock.calls[0] as [string, {items: {key: string; value: string}[]}];
    expect(url).toBe('/api/v1/settings/global/bulk');
    return Object.fromEntries(body.items.map((i) => [i.key, i.value]));
}

/** Types into the `type="time"` field and lets Svelte's binding read it back. */
async function typeTime(value: string): Promise<void> {
    await fireEvent.input(timeInput(), {target: {value}});
}

beforeEach(() => {
    patch.mockReset();
    patch.mockResolvedValue({data: {}} as never);
    notified.mockReset();
});

afterEach(() => {
    cleanup();
    vi.useRealTimers();
});

describe('opening', () => {
    it('loads the values it was given', () => {
        mount();

        expect(slots()).toEqual(['09:00', '17:30']);
        expect(frequencyInput()).toHaveValue(10);
        expect(horizonInput()).toHaveValue(14);
        expect(tzSearchInput()).toHaveAttribute('placeholder', 'UTC');
    });

    it('leaves the form alone when the parent re-renders while it is already open', async () => {
        // `currentValues` is an inline object literal at the call site, so it is
        // a new reference on every parent render. `untrack` plus the `wasOpen`
        // latch is what stops that from wiping out what the user has typed.
        const m = mount();
        await fireEvent.input(frequencyInput(), {target: {value: '42'}});

        await m.rerender({currentValues: {frequency: 999, times: '01:00', days: 'sun', horizon: 7}});

        expect(frequencyInput()).toHaveValue(42);
        expect(slots()).toEqual(['09:00', '17:30']);
    });

    it('re-reads the values on the next open, so a cancelled edit does not survive', async () => {
        const m = mount();
        await fireEvent.input(frequencyInput(), {target: {value: '42'}});
        await fireEvent.click(screen.getByTestId('scheduler-config-cancel'));

        await m.rerender({open: true, currentValues: {frequency: 30, times: '06:15', days: 'fri', horizon: 90}});

        expect(frequencyInput()).toHaveValue(30);
        expect(slots()).toEqual(['06:15']);
        expect(horizonInput()).toHaveValue(90);
    });

    it('starts with no times and no days when the stored strings are empty', () => {
        mount({currentValues: {...DEFAULTS, times: '', days: ''}});

        expect(slots()).toEqual([]);
        expect(saveButton()).toBeDisabled();
    });

    it('drops the empty segments a trailing comma leaves behind', () => {
        mount({currentValues: {...DEFAULTS, times: '09:00,,17:30,'}});

        expect(slots()).toEqual(['09:00', '17:30']);
    });

    it('accepts the days in any case and with stray spaces', () => {
        mount({currentValues: {...DEFAULTS, days: ' MON , Tue '}});

        // Read through the payload, since selection has no accessible state.
        return fireEvent.click(saveButton()).then(async () => {
            await waitFor(() => expect(patch).toHaveBeenCalled());
            expect(savedKeys().scheduler_history_sync_days).toBe('mon,tue');
        });
    });

    it('falls back to the browser timezone when none is configured', () => {
        // The right-hand side of `schedulerTimezone || resolvedOptions().timeZone`.
        // The expectation reads the platform, not the component: this is what
        // `Intl` says in this process, independently of the code under test.
        const browserTz = Intl.DateTimeFormat().resolvedOptions().timeZone;
        mount({schedulerTimezone: ''});

        expect(tzSearchInput()).toHaveAttribute('placeholder', browserTz);
    });

    it('shows a dash instead of a blank when the server clock is unknown', () => {
        mount({serverNowUtc: ''});

        expect(screen.getByText(/Server UTC/)).toHaveTextContent('—');
    });
});

describe('time slots', () => {
    it('adds one, normalised to HH:MM, and clears the field', async () => {
        mount({currentValues: {...DEFAULTS, times: ''}});

        await typeTime('09:30:45');
        await fireEvent.click(screen.getByTestId('scheduler-config-time-add'));

        expect(slots()).toEqual(['09:30']);
        expect(timeInput()).toHaveValue('');
    });

    it('keeps the list in order however it is filled', async () => {
        mount({currentValues: {...DEFAULTS, times: ''}});

        for (const t of ['22:00', '06:00', '13:45']) {
            await typeTime(t);
            await fireEvent.click(screen.getByTestId('scheduler-config-time-add'));
        }

        expect(slots()).toEqual(['06:00', '13:45', '22:00']);
    });

    it('swallows a duplicate instead of listing it twice', async () => {
        mount();

        await typeTime('09:00');
        await fireEvent.click(screen.getByTestId('scheduler-config-time-add'));

        expect(slots()).toEqual(['09:00', '17:30']);
        // The field is cleared either way — the add is a no-op, not a refusal.
        expect(timeInput()).toHaveValue('');
    });

    it('will not add while the field is empty', async () => {
        mount();
        const add = screen.getByTestId('scheduler-config-time-add');

        expect(add).toBeDisabled();
        await fireEvent.click(add);

        expect(slots()).toEqual(['09:00', '17:30']);
    });

    it('adds on Enter', async () => {
        mount({currentValues: {...DEFAULTS, times: ''}});

        await typeTime('08:15');
        await fireEvent.keyDown(timeInput(), {key: 'Enter'});

        expect(slots()).toEqual(['08:15']);
    });

    it('ignores Enter on an empty field', async () => {
        // The keyboard is the only way to reach `addTimeSlot`'s own `!newTime`
        // guard: the button that would otherwise call it is disabled.
        mount();

        await fireEvent.keyDown(timeInput(), {key: 'Enter'});

        expect(slots()).toEqual(['09:00', '17:30']);
    });

    it('ignores any other key', async () => {
        mount({currentValues: {...DEFAULTS, times: ''}});

        await typeTime('08:15');
        await fireEvent.keyDown(timeInput(), {key: 'a'});

        expect(slots()).toEqual([]);
    });

    it('removes the slot the user pointed at', async () => {
        mount();

        await fireEvent.click(screen.getByRole('button', {name: 'Remove 09:00'}));

        expect(slots()).toEqual(['17:30']);
    });

    it('blocks the save once the last slot is gone', async () => {
        mount({currentValues: {...DEFAULTS, times: '09:00'}});

        await fireEvent.click(screen.getByRole('button', {name: 'Remove 09:00'}));

        expect(slots()).toEqual([]);
        expect(saveButton()).toBeDisabled();
    });
});

describe('weekdays', () => {
    async function saveAndRead(): Promise<Record<string, string>> {
        await fireEvent.click(saveButton());
        await waitFor(() => expect(patch).toHaveBeenCalled());
        return savedKeys();
    }

    it('adds a day the user switches on', async () => {
        mount();

        await fireEvent.click(dayButton('fri'));

        expect((await saveAndRead()).scheduler_history_sync_days).toBe('mon,wed,fri');
    });

    it('drops a day the user switches off', async () => {
        mount();

        await fireEvent.click(dayButton('mon'));

        expect((await saveAndRead()).scheduler_history_sync_days).toBe('wed');
    });

    it('refuses to switch off the last remaining day', async () => {
        // Without this guard the modal would let the user reach a state its own
        // `canSave` calls invalid — a dialog that disables its only exit.
        mount({currentValues: {...DEFAULTS, days: 'mon'}});

        await fireEvent.click(dayButton('mon'));

        expect(saveButton()).toBeEnabled();
        expect((await saveAndRead()).scheduler_history_sync_days).toBe('mon');
    });

    it('still lets the last day be switched off once a second one is on', async () => {
        // The presence barrier for the refusal above: it must be about being
        // last, not about that particular button never working.
        mount({currentValues: {...DEFAULTS, days: 'mon'}});

        await fireEvent.click(dayButton('sat'));
        await fireEvent.click(dayButton('mon'));

        expect((await saveAndRead()).scheduler_history_sync_days).toBe('sat');
    });

    it('keeps the days in the week order, not the order they were clicked', async () => {
        mount({currentValues: {...DEFAULTS, days: 'sun'}});

        await fireEvent.click(dayButton('tue'));

        expect((await saveAndRead()).scheduler_history_sync_days).toBe('tue,sun');
    });
});

describe('what makes the save button live', () => {
    const cases: [string, Record<string, unknown>, boolean][] = [
        ['the values it opened with', {}, true],
        ['frequency at its minimum', {frequency: '1'}, true],
        ['frequency below its minimum', {frequency: '0'}, false],
        ['frequency at its maximum', {frequency: '1440'}, true],
        ['frequency above its maximum', {frequency: '1441'}, false],
        ['horizon at its minimum', {horizon: '1'}, true],
        ['horizon below its minimum', {horizon: '0'}, false],
        ['horizon at its maximum', {horizon: '365'}, true],
        ['horizon above its maximum', {horizon: '366'}, false],
    ];

    it.each(cases)('%s → %o leaves it %s', async (_name, edit, enabled) => {
        mount();

        if ('frequency' in edit) await fireEvent.input(frequencyInput(), {target: {value: edit.frequency}});
        if ('horizon' in edit) await fireEvent.input(horizonInput(), {target: {value: edit.horizon}});

        if (enabled) expect(saveButton()).toBeEnabled();
        else expect(saveButton()).toBeDisabled();
    });

    it('goes dead when the number field is emptied altogether', async () => {
        mount();

        await fireEvent.input(frequencyInput(), {target: {value: ''}});

        expect(saveButton()).toBeDisabled();
    });

    it('needs a time as well as a day', () => {
        mount({currentValues: {...DEFAULTS, times: ''}});
        expect(saveButton()).toBeDisabled();

        cleanup();
        mount({currentValues: {...DEFAULTS, days: ''}});
        expect(saveButton()).toBeDisabled();
    });
});

describe('saving', () => {
    it('sends the five keys the backend expects, and nothing else', async () => {
        const m = mount();

        await fireEvent.click(saveButton());
        await waitFor(() => expect(patch).toHaveBeenCalled());

        expect(savedKeys()).toEqual({
            scheduler_current_price_frequency_minutes: '10',
            scheduler_history_sync_times: '09:00,17:30',
            scheduler_history_sync_days: 'mon,wed',
            scheduler_history_sync_horizon_days: '14',
            scheduler_timezone: 'UTC',
        });
        expect(m.onsave).toHaveBeenCalledOnce();
    });

    it('announces the save as a structured event, not only as a toast', async () => {
        mount();

        await fireEvent.click(saveButton());
        await waitFor(() => expect(notified).toHaveBeenCalled());

        const [event] = notified.mock.calls[0];
        expect(event.name).toBe('settings.scheduler.saved');
        expect(event.detail).toEqual({frequencyMinutes: 10, horizonDays: 14, timezone: 'UTC', times: 2});
        expect(event.toast?.variant).toBe('success');
    });

    it('closes itself on success', async () => {
        mount();

        await fireEvent.click(saveButton());

        await waitFor(() => expect(screen.queryByTestId('scheduler-config-modal')).toBeNull());
    });

    it('echoes the reason the backend gave and stays open', async () => {
        // The one place the component shows the server's own words: asserting
        // the sentence here is asserting that it was not swallowed.
        patch.mockRejectedValue({response: {data: {detail: 'scheduler_timezone is not a known zone'}}});
        mount();

        await fireEvent.click(saveButton());

        await waitFor(() => expect(screen.getByTestId('info-banner-error')).toBeInTheDocument());
        expect(screen.getByTestId('info-banner-error')).toHaveTextContent('scheduler_timezone is not a known zone');
        expect(screen.getByTestId('scheduler-config-modal')).toBeInTheDocument();
    });

    it('falls back to the transport error when the backend said nothing', async () => {
        patch.mockRejectedValue(new Error('Network Error'));
        mount();

        await fireEvent.click(saveButton());

        await waitFor(() => expect(screen.getByTestId('info-banner-error')).toHaveTextContent('Network Error'));
    });

    it('has something to say even for an error with no message at all', async () => {
        patch.mockRejectedValue({});
        mount();

        await fireEvent.click(saveButton());

        await waitFor(() => expect(screen.getByTestId('info-banner-error')).toHaveTextContent('Save failed'));
    });

    it('reports the failure as an event too', async () => {
        patch.mockRejectedValue(new Error('Network Error'));
        const m = mount();

        await fireEvent.click(saveButton());
        await waitFor(() => expect(notified).toHaveBeenCalled());

        const [event] = notified.mock.calls[0];
        expect(event.name).toBe('settings.scheduler.save.failed');
        expect(event.detail).toEqual({reason: 'Network Error'});
        expect(event.toast?.variant).toBe('error');
        expect(m.onsave).not.toHaveBeenCalled();
    });

    it('lets the user dismiss the error and try again', async () => {
        patch.mockRejectedValue(new Error('Network Error'));
        mount();
        await fireEvent.click(saveButton());
        await waitFor(() => expect(screen.getByTestId('info-banner-error')).toBeInTheDocument());

        await fireEvent.click(within(screen.getByTestId('info-banner-error')).getByLabelText('Dismiss'));

        expect(screen.queryByTestId('info-banner-error')).toBeNull();
    });

    it('clears a stale error when it is opened again', async () => {
        patch.mockRejectedValue(new Error('Network Error'));
        const m = mount();
        await fireEvent.click(saveButton());
        await waitFor(() => expect(screen.getByTestId('info-banner-error')).toBeInTheDocument());

        await fireEvent.click(screen.getByTestId('scheduler-config-cancel'));
        await m.rerender({open: true});

        expect(screen.queryByTestId('info-banner-error')).toBeNull();
    });

    it('holds the button down for the whole round trip', async () => {
        let release!: () => void;
        patch.mockReturnValue(new Promise<never>((_r, rej) => (release = () => rej(new Error('Network Error')))) as never);
        mount();

        await fireEvent.click(saveButton());
        await tick();
        expect(saveButton()).toBeDisabled();

        release();
        await waitFor(() => expect(saveButton()).toBeEnabled());
    });

    it('does nothing at all when the form is invalid', async () => {
        mount({currentValues: {...DEFAULTS, times: ''}});

        await fireEvent.click(saveButton());
        await tick();

        expect(patch).not.toHaveBeenCalled();
    });
});

describe('the timezone picker', () => {
    it('opens on focus and offers a bounded list', async () => {
        mount();

        await fireEvent.focus(tzSearchInput());

        const list = within(screen.getByTestId('scheduler-config-timezone')).getAllByRole('button');
        expect(list.length).toBeGreaterThan(0);
        expect(list.length).toBeLessThanOrEqual(30);
    });

    it('filters on what is typed, case-insensitively', async () => {
        mount();
        await fireEvent.focus(tzSearchInput());

        await fireEvent.input(tzSearchInput(), {target: {value: 'bOgOtA'}});

        const zone = screen.getByTestId('scheduler-config-timezone');
        expect(within(zone).getByRole('button', {name: BOGOTA})).toBeInTheDocument();
        expect(within(zone).getAllByRole('button')).toHaveLength(1);
    });

    it('offers nothing when nothing matches', async () => {
        mount();
        await fireEvent.focus(tzSearchInput());

        await fireEvent.input(tzSearchInput(), {target: {value: 'Not/AZone'}});

        expect(within(screen.getByTestId('scheduler-config-timezone')).queryAllByRole('button')).toHaveLength(0);
    });

    it('takes the pick, clears the search, and closes', async () => {
        mount();
        await fireEvent.focus(tzSearchInput());
        await fireEvent.input(tzSearchInput(), {target: {value: 'bogota'}});

        await fireEvent.click(screen.getByRole('button', {name: BOGOTA}));

        expect(tzSearchInput()).toHaveValue('');
        expect(tzSearchInput()).toHaveAttribute('placeholder', BOGOTA);
        expect(within(screen.getByTestId('scheduler-config-timezone')).queryAllByRole('button')).toHaveLength(0);
    });

    it('waits 150 ms after blur before closing, so a click on an option still lands', async () => {
        vi.useFakeTimers();
        mount();
        await fireEvent.focus(tzSearchInput());
        const zone = screen.getByTestId('scheduler-config-timezone');
        expect(within(zone).getAllByRole('button').length).toBeGreaterThan(0);

        await fireEvent.blur(tzSearchInput());
        await vi.advanceTimersByTimeAsync(140);
        expect(within(zone).getAllByRole('button').length).toBeGreaterThan(0);

        await vi.advanceTimersByTimeAsync(20);
        expect(within(zone).queryAllByRole('button')).toHaveLength(0);
    });
});

describe('UTC in, local out', () => {
    it('shows the stored UTC times in the chosen zone', () => {
        mount({schedulerTimezone: KOLKATA, currentValues: {...DEFAULTS, times: '09:00,17:30'}});

        expect(slots()).toEqual(['14:30', '23:00']);
    });

    it('gives back the same UTC it was given, untouched', async () => {
        mount({schedulerTimezone: KOLKATA});

        await fireEvent.click(saveButton());
        await waitFor(() => expect(patch).toHaveBeenCalled());

        expect(savedKeys().scheduler_history_sync_times).toBe('09:00,17:30');
        expect(savedKeys().scheduler_timezone).toBe(KOLKATA);
    });

    it('carries a time across midnight forwards', () => {
        // 23:00 UTC is 04:30 the next morning in Kolkata.
        mount({schedulerTimezone: KOLKATA, currentValues: {...DEFAULTS, times: '23:00'}});

        expect(slots()).toEqual(['04:30']);
    });

    it('carries it back across midnight on save', async () => {
        mount({schedulerTimezone: KOLKATA, currentValues: {...DEFAULTS, times: '23:00'}});

        await fireEvent.click(saveButton());
        await waitFor(() => expect(patch).toHaveBeenCalled());

        expect(savedKeys().scheduler_history_sync_times).toBe('23:00');
    });

    it('wraps the other way for a zone behind UTC', async () => {
        // 20:00 in Bogotá (−05:00) is 01:00 UTC the next day.
        mount({schedulerTimezone: BOGOTA, currentValues: {...DEFAULTS, times: ''}});
        await typeTime('20:00');
        await fireEvent.click(screen.getByTestId('scheduler-config-time-add'));

        await fireEvent.click(saveButton());
        await waitFor(() => expect(patch).toHaveBeenCalled());

        expect(savedKeys().scheduler_history_sync_times).toBe('01:00');
    });

    it('leaves the times alone when the zone is not a zone', async () => {
        // Both conversions are wrapped in a `catch` that returns the input. A
        // stored `scheduler_timezone` the browser does not know must not turn
        // the schedule into `NaN:NaN`.
        mount({schedulerTimezone: 'Not/AZone'});
        expect(slots()).toEqual(['09:00', '17:30']);

        await fireEvent.click(saveButton());
        await waitFor(() => expect(patch).toHaveBeenCalled());

        expect(savedKeys().scheduler_history_sync_times).toBe('09:00,17:30');
    });

    it('CHARACTERISATION: picking a zone reschedules the job without moving the times on screen', async () => {
        // The hint under the field says "times below are displayed in this
        // timezone", but `selectedTz` is only read on open and on save — the
        // chips are never re-converted. So a user who opens the dialog on UTC,
        // sees 09:00, and then sets their own zone to Bogotá saves a job that
        // now runs at 14:00 UTC, with 09:00 still on screen. Nothing warns them.
        //
        // This test passes today. It will go red when the times are re-converted
        // on a zone change, and that red is the fix landing.
        mount({schedulerTimezone: 'UTC', currentValues: {...DEFAULTS, times: '09:00'}});
        expect(slots()).toEqual(['09:00']);

        await fireEvent.focus(tzSearchInput());
        await fireEvent.input(tzSearchInput(), {target: {value: 'bogota'}});
        await fireEvent.click(screen.getByRole('button', {name: BOGOTA}));

        expect(slots()).toEqual(['09:00']);

        await fireEvent.click(saveButton());
        await waitFor(() => expect(patch).toHaveBeenCalled());

        expect(savedKeys().scheduler_history_sync_times).toBe('14:00');
    });
});

describe('dismissing', () => {
    it('closes on Cancel without writing anything', async () => {
        mount();

        await fireEvent.click(screen.getByTestId('scheduler-config-cancel'));

        expect(screen.queryByTestId('scheduler-config-modal')).toBeNull();
        expect(patch).not.toHaveBeenCalled();
    });

    it('closes on the header cross', async () => {
        const {container} = mount();
        const header = container.querySelector('[data-testid="scheduler-config-modal"] .border-b');
        const cross = within(header as HTMLElement)
            .getAllByRole('button')
            .at(-1) as HTMLElement;

        await fireEvent.click(cross);

        expect(screen.queryByTestId('scheduler-config-modal')).toBeNull();
    });

    it('renders nothing at all while closed', () => {
        mount({open: false});

        expect(screen.queryByTestId('scheduler-config-modal')).toBeNull();
    });
});
