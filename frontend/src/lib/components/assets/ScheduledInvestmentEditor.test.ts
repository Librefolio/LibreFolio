// @vitest-environment jsdom
/**
 * ScheduledInvestmentEditor — component test (Vitest + jsdom).
 *
 * The editor for a fixed-income asset's interest schedule. Despite its size it
 * is a pure controlled component: it takes the provider's `provider_params`
 * JSON in through `value`, and every mutation leaves through `onchange` as a
 * complete replacement payload. There is no network call, no store and no
 * `onMount` in it, so the whole surface is reachable from props alone.
 *
 * That payload is the contract, and it is what these tests assert. Reaching the
 * same ground through Playwright means opening an asset modal, choosing the
 * scheduled-investment provider and driving a date picker per period — most of
 * the work is the setup, and the JSON that comes out is never visible.
 *
 * Periods get a fresh UUID on every deserialisation, so rows are never
 * addressed by id here. Where a specific row matters the fixture holds exactly
 * one candidate, and everything else is asserted on the emitted schedule, whose
 * order is itself the meaning: the periods are contiguous and sorted.
 *
 * What it deliberately does NOT assert:
 *     (The three date helpers used to parse local midnight and re-serialise
 *     through UTC, so east of Greenwich every result slipped back a day and this
 *     file avoided asserting anything that crossed them. They now live in
 *     `$lib/utils/dateOnly` and do the arithmetic in UTC end to end, so the last
 *     block below asserts the invariants that were unreachable before.)
 *   - the period date cells. Each one embeds a full `DateRangePicker`, which
 *     has its own component test; driving it from here would test that
 *     component through a second one.
 *   - the `⋮` row-actions button. It hands `ContextMenu` an anchor element, and
 *     `syncToAnchor()` closes the menu when the anchor measures zero — which in
 *     jsdom it always does. The right-click path reaches the same menu.
 *   - translated text. Every control is addressed by `data-testid`; the values
 *     compared are the ones the test itself passed in as `value`.
 */
import {describe, expect, it, vi} from 'vitest';
import type {Mock} from 'vitest';
import {fireEvent, render, screen, setupI18n, waitFor, within} from '$test/component';
import ScheduledInvestmentEditor from './ScheduledInvestmentEditor.svelte';
import {daysBetween} from '$lib/utils/dateOnly';

interface Period {
    start_date: string;
    end_date: string;
    annual_rate: string;
    maturation_frequency: string;
    generate_interest: boolean;
}

/** Two contiguous six-month periods at different rates — the shape the provider stores. */
function twoPeriods(): Record<string, unknown> {
    return {
        initial_value: {code: 'EUR', amount: '5000'},
        interest_type: 'COMPOUND',
        day_count: 'ACT/360',
        schedule: [
            {start_date: '2024-01-01', end_date: '2024-06-30', annual_rate: '0.0325', maturation_frequency: 'MONTHLY', generate_interest: true},
            {start_date: '2024-07-01', end_date: '2024-12-31', annual_rate: '0.0450', maturation_frequency: 'QUARTERLY', generate_interest: false},
        ],
        late_interest: null,
        asset_events: [],
    };
}

function onePeriod(): Record<string, unknown> {
    return {
        initial_value: {code: 'USD', amount: '1000'},
        schedule: [{start_date: '2024-01-01', end_date: '2024-12-31', annual_rate: '0.0500', maturation_frequency: 'MONTHLY', generate_interest: false}],
        late_interest: null,
        asset_events: [],
    };
}

function mount(value: Record<string, unknown>, props: Record<string, unknown> = {}) {
    const onchange = vi.fn();
    return {onchange, ...render(ScheduledInvestmentEditor, {value, onchange, ...props})};
}

/** The whole payload the parent was handed last. */
function lastPayload(spy: Mock): Record<string, any> | undefined {
    return spy.mock.calls.at(-1)?.[0];
}

/** Just the schedule array of the last payload. */
function lastSchedule(spy: Mock): Period[] {
    const p = lastPayload(spy);
    if (!p) throw new Error('onchange was never called');
    return p.schedule as Period[];
}

/** The period rows currently in the table (late interest included when enabled). */
function tableRows(): HTMLElement[] {
    return [...document.querySelectorAll<HTMLElement>('tbody tr[data-row-id]')];
}

describe('ScheduledInvestmentEditor — reading the provider payload', () => {
    it('turns each stored period into a row and keeps the late-interest row out until it exists', async () => {
        await setupI18n();
        mount(twoPeriods());

        expect(tableRows()).toHaveLength(2);
        // The late row is the only one with a fixed id; it is not in the table
        // while `late_interest` is null, but its toggle already is.
        expect(document.querySelector('tbody tr[data-row-id="late-interest"]')).toBeNull();
        expect(screen.getByTestId('schedule-late-toggle')).toHaveAttribute('data-state', 'off');
    });

    it('shows the empty state, and only the empty state, when there is no schedule', async () => {
        await setupI18n();
        mount({schedule: [], late_interest: null});

        expect(screen.getByTestId('schedule-empty')).toBeInTheDocument();
        expect(screen.getByTestId('schedule-add-first-period')).toBeInTheDocument();
        expect(tableRows()).toHaveLength(0);
        expect(screen.getByTestId('schedule-status')).toHaveAttribute('data-valid', 'false');
    });

    it('emits a complete payload immediately when the parent supplies nothing', async () => {
        await setupI18n();
        // The provider must never end up with a null `provider_params`, so an
        // empty value has to come straight back out as a filled-in default.
        const {onchange} = mount({});

        await waitFor(() => expect(onchange).toHaveBeenCalled());
        expect(lastPayload(onchange)).toEqual({
            initial_value: {code: 'EUR', amount: '10000'},
            interest_type: 'SIMPLE',
            day_count: 'ACT/365',
            schedule: [],
            late_interest: null,
            asset_events: [],
        });
    });

    it('stays quiet when the parent already supplied a payload', async () => {
        await setupI18n();
        const {onchange} = mount(twoPeriods());

        // Echoing the parent's own value back at it would make every consumer
        // look dirty the moment the editor mounts.
        await waitFor(() => expect(tableRows()).toHaveLength(2));
        expect(onchange).not.toHaveBeenCalled();
    });

    it('accepts initial_value as a Currency object', async () => {
        await setupI18n();
        const {onchange} = mount(twoPeriods());

        await fireEvent.click(screen.getByTestId('schedule-add-period'));
        expect(lastPayload(onchange)?.initial_value).toEqual({code: 'EUR', amount: '5000'});
    });

    it('accepts the legacy scalar initial_value and normalises it on the way out', async () => {
        await setupI18n();
        // Assets saved before initial_value became a Currency object still carry a
        // bare number with the code in a sibling field; both must round-trip.
        const {onchange} = mount({...onePeriod(), initial_value: 2500, currency: 'CHF'});

        await fireEvent.click(screen.getByTestId('schedule-add-period'));
        expect(lastPayload(onchange)?.initial_value).toEqual({code: 'CHF', amount: '2500'});
    });

    it('falls back to the provider defaults for the global fields', async () => {
        await setupI18n();
        const {onchange} = mount({schedule: [{start_date: '2024-01-01', end_date: '2024-12-31', annual_rate: '0.01', maturation_frequency: 'MONTHLY', generate_interest: false}]});

        await fireEvent.click(screen.getByTestId('schedule-add-period'));
        const payload = lastPayload(onchange);
        expect(payload?.interest_type).toBe('SIMPLE');
        expect(payload?.day_count).toBe('ACT/365');
        expect(payload?.initial_value).toEqual({code: 'EUR', amount: '10000'});
    });
});

describe('ScheduledInvestmentEditor — the rate round trip', () => {
    it('stores rates as fractions and edits them as percentages', async () => {
        await setupI18n();
        // 0.0325 in the JSON is 3.25% in the editor; the trip back has to land
        // on the same fraction, or every save would drift the asset's yield.
        const {onchange} = mount(twoPeriods());

        await fireEvent.click(screen.getByTestId('schedule-add-period'));
        const schedule = lastSchedule(onchange);
        expect(schedule[0].annual_rate).toBe('0.0325');
        expect(schedule[1].annual_rate).toBe('0.0450');
    });

    it('keeps four decimals, so a basis point survives the round trip', async () => {
        await setupI18n();
        const value = {...onePeriod(), schedule: [{...(onePeriod().schedule as Period[])[0], annual_rate: '0.0001'}]};
        const {onchange} = mount(value);

        await fireEvent.click(screen.getByTestId('schedule-add-period'));
        expect(lastSchedule(onchange)[0].annual_rate).toBe('0.0001');
    });
});

describe('ScheduledInvestmentEditor — adding periods', () => {
    it('appends a period that inherits the terms of the one before it', async () => {
        await setupI18n();
        const {onchange} = mount(twoPeriods());

        await fireEvent.click(screen.getByTestId('schedule-add-period'));

        const schedule = lastSchedule(onchange);
        expect(schedule).toHaveLength(3);
        // The first two are untouched — appending must not rewrite history.
        expect(schedule[0]).toMatchObject({start_date: '2024-01-01', end_date: '2024-06-30', annual_rate: '0.0325'});
        expect(schedule[1]).toMatchObject({start_date: '2024-07-01', end_date: '2024-12-31', annual_rate: '0.0450'});
        // The new one continues the previous terms rather than resetting them.
        expect(schedule[2].annual_rate).toBe('0.0450');
        expect(schedule[2].maturation_frequency).toBe('QUARTERLY');
        expect(schedule[2].generate_interest).toBe(false);
        expect(schedule[2].end_date > schedule[2].start_date).toBe(true);
        await waitFor(() => expect(tableRows()).toHaveLength(3));
    });

    it('starts the very first period with the provider defaults', async () => {
        await setupI18n();
        const {onchange} = mount({schedule: [], late_interest: null});

        await fireEvent.click(screen.getByTestId('schedule-add-first-period'));

        const schedule = lastSchedule(onchange);
        expect(schedule).toHaveLength(1);
        expect(schedule[0].annual_rate).toBe('0.0500');
        expect(schedule[0].maturation_frequency).toBe('MONTHLY');
        expect(schedule[0].generate_interest).toBe(false);
        // The empty state gives way to the table.
        await waitFor(() => expect(screen.queryByTestId('schedule-empty')).toBeNull());
        expect(tableRows()).toHaveLength(1);
    });
});

describe('ScheduledInvestmentEditor — splitting and merging', () => {
    /** Opens a period's action menu. Right-click is the path jsdom can measure. */
    async function openRowMenu(rowIndex: number) {
        const rows = tableRows();
        await fireEvent.contextMenu(rows[rowIndex]);
        return screen.getByTestId('context-menu');
    }

    it('splits one period into two that still span the original range', async () => {
        await setupI18n();
        const {onchange} = mount(onePeriod());

        const menu = await openRowMenu(0);
        await fireEvent.click(within(menu).getByTestId('schedule-action-split'));
        await waitFor(() => expect(screen.getByTestId('boundary-modal-confirm')).toBeEnabled());
        await fireEvent.click(screen.getByTestId('boundary-modal-confirm'));

        const schedule = lastSchedule(onchange);
        expect(schedule).toHaveLength(2);
        // The outer edges are the invariant: a split may move the seam, never the ends.
        expect(schedule[0].start_date).toBe('2024-01-01');
        expect(schedule[1].end_date).toBe('2024-12-31');
        // Both halves keep the original terms.
        expect(schedule[0].annual_rate).toBe('0.0500');
        expect(schedule[1].annual_rate).toBe('0.0500');
        await waitFor(() => expect(tableRows()).toHaveLength(2));
    });

    it('refuses to split a period too short to have an interior day', async () => {
        await setupI18n();
        const value = {...onePeriod(), schedule: [{...(onePeriod().schedule as Period[])[0], start_date: '2024-03-01', end_date: '2024-03-02'}]};
        mount(value);

        const menu = await openRowMenu(0);
        // Offered but unusable, so the user can see the action exists.
        expect(within(menu).getByTestId('schedule-action-split')).toBeDisabled();
        await fireEvent.click(within(menu).getByTestId('schedule-action-split'));
        expect(screen.queryByTestId('boundary-modal-confirm')).toBeNull();
    });

    it('leaves the schedule untouched when the boundary dialog is cancelled', async () => {
        await setupI18n();
        const {onchange} = mount(onePeriod());

        const menu = await openRowMenu(0);
        await fireEvent.click(within(menu).getByTestId('schedule-action-split'));
        await waitFor(() => expect(screen.getByTestId('boundary-modal-cancel')).toBeInTheDocument());
        await fireEvent.click(screen.getByTestId('boundary-modal-cancel'));

        expect(onchange).not.toHaveBeenCalled();
        expect(tableRows()).toHaveLength(1);
    });

    it('merges the selected periods into one that covers both, keeping the first terms', async () => {
        await setupI18n();
        const {onchange} = mount(twoPeriods());

        for (const row of tableRows()) {
            const id = row.getAttribute('data-row-id');
            await fireEvent.click(screen.getByTestId(`dt-row-checkbox-${id}`));
        }
        await fireEvent.click(screen.getByTestId('schedule-bulk-merge'));

        const schedule = lastSchedule(onchange);
        expect(schedule).toHaveLength(1);
        expect(schedule[0].start_date).toBe('2024-01-01');
        expect(schedule[0].end_date).toBe('2024-12-31');
        // The earlier period wins: merging is "extend the first", not "average".
        expect(schedule[0].annual_rate).toBe('0.0325');
        expect(schedule[0].maturation_frequency).toBe('MONTHLY');
        expect(schedule[0].generate_interest).toBe(true);
    });

    it('will not merge a selection that is not contiguous', async () => {
        await setupI18n();
        const value = {
            ...twoPeriods(),
            schedule: [
                {start_date: '2024-01-01', end_date: '2024-04-30', annual_rate: '0.0100', maturation_frequency: 'MONTHLY', generate_interest: false},
                {start_date: '2024-05-01', end_date: '2024-08-31', annual_rate: '0.0200', maturation_frequency: 'MONTHLY', generate_interest: false},
                {start_date: '2024-09-01', end_date: '2024-12-31', annual_rate: '0.0300', maturation_frequency: 'MONTHLY', generate_interest: false},
            ],
        };
        const {onchange} = mount(value);
        const rows = tableRows();

        // First and third: merging them would silently swallow the middle one.
        for (const idx of [0, 2]) {
            await fireEvent.click(screen.getByTestId(`dt-row-checkbox-${rows[idx].getAttribute('data-row-id')}`));
        }
        await waitFor(() => expect(screen.getByTestId('schedule-bulk-merge')).toBeDisabled());

        await fireEvent.click(screen.getByTestId('schedule-bulk-merge'));
        expect(onchange).not.toHaveBeenCalled();

        // Adding the middle one makes the block contiguous and the action usable.
        await fireEvent.click(screen.getByTestId(`dt-row-checkbox-${rows[1].getAttribute('data-row-id')}`));
        await waitFor(() => expect(screen.getByTestId('schedule-bulk-merge')).toBeEnabled());
    });

    it('does not offer merge for a single selected period', async () => {
        await setupI18n();
        mount(twoPeriods());

        const first = tableRows()[0].getAttribute('data-row-id');
        await fireEvent.click(screen.getByTestId(`dt-row-checkbox-${first}`));

        await waitFor(() => expect(screen.getByTestId('schedule-bulk-merge')).toBeDisabled());
    });
});

describe('ScheduledInvestmentEditor — deleting periods', () => {
    async function openRowMenu(rowIndex: number) {
        await fireEvent.contextMenu(tableRows()[rowIndex]);
        return screen.getByTestId('context-menu');
    }

    it('removes the only period without asking where to put the seam', async () => {
        await setupI18n();
        const {onchange} = mount(onePeriod());

        const menu = await openRowMenu(0);
        await fireEvent.click(within(menu).getByTestId('schedule-action-delete'));

        // Nothing to reflow into, so there is no boundary to choose.
        expect(screen.queryByTestId('boundary-modal-confirm')).toBeNull();
        expect(lastSchedule(onchange)).toEqual([]);
        await waitFor(() => expect(screen.getByTestId('schedule-empty')).toBeInTheDocument());
    });

    it('hands the last period back to its predecessor at the date the dialog defaults to', async () => {
        await setupI18n();
        const {onchange} = mount(twoPeriods());

        const menu = await openRowMenu(1);
        await fireEvent.click(within(menu).getByTestId('schedule-action-delete'));
        await waitFor(() => expect(screen.getByTestId('boundary-modal-confirm')).toBeEnabled());
        await fireEvent.click(screen.getByTestId('boundary-modal-confirm'));

        const schedule = lastSchedule(onchange);
        expect(schedule).toHaveLength(1);
        expect(schedule[0].start_date).toBe('2024-01-01');
        // Deleting the tail defaults the seam to the dead period's own start, so
        // the survivor absorbs exactly the range that was freed and no more.
        expect(schedule[0].end_date).toBe('2024-07-01');
    });

    it('keeps the overall span when a middle period is removed', async () => {
        await setupI18n();
        const value = {
            ...twoPeriods(),
            schedule: [
                {start_date: '2024-01-01', end_date: '2024-04-30', annual_rate: '0.0100', maturation_frequency: 'MONTHLY', generate_interest: false},
                {start_date: '2024-05-01', end_date: '2024-08-31', annual_rate: '0.0200', maturation_frequency: 'MONTHLY', generate_interest: false},
                {start_date: '2024-09-01', end_date: '2024-12-31', annual_rate: '0.0300', maturation_frequency: 'MONTHLY', generate_interest: false},
            ],
        };
        const {onchange} = mount(value);

        const menu = await openRowMenu(1);
        await fireEvent.click(within(menu).getByTestId('schedule-action-delete'));
        await waitFor(() => expect(screen.getByTestId('boundary-modal-confirm')).toBeEnabled());
        await fireEvent.click(screen.getByTestId('boundary-modal-confirm'));

        const schedule = lastSchedule(onchange);
        expect(schedule).toHaveLength(2);
        // The neighbours share out the gap; the ends of the schedule cannot move.
        expect(schedule[0].start_date).toBe('2024-01-01');
        expect(schedule[1].end_date).toBe('2024-12-31');
        expect(schedule[0].annual_rate).toBe('0.0100');
        expect(schedule[1].annual_rate).toBe('0.0300');
    });

    it('deletes every selected period in one go', async () => {
        await setupI18n();
        const {onchange} = mount(twoPeriods());

        for (const row of tableRows()) {
            await fireEvent.click(screen.getByTestId(`dt-row-checkbox-${row.getAttribute('data-row-id')}`));
        }
        await fireEvent.click(screen.getByTestId('schedule-bulk-delete'));

        await waitFor(() => expect(lastSchedule(onchange)).toEqual([]));
        expect(screen.getByTestId('schedule-empty')).toBeInTheDocument();
    });

    it('clears the selection without touching the schedule', async () => {
        await setupI18n();
        const {onchange} = mount(twoPeriods());

        const first = tableRows()[0].getAttribute('data-row-id');
        await fireEvent.click(screen.getByTestId(`dt-row-checkbox-${first}`));
        await waitFor(() => expect(screen.getByTestId('schedule-clear-selection')).toBeInTheDocument());

        await fireEvent.click(screen.getByTestId('schedule-clear-selection'));

        await waitFor(() => expect(screen.queryByTestId('schedule-bulk-merge')).toBeNull());
        expect(onchange).not.toHaveBeenCalled();
        expect(tableRows()).toHaveLength(2);
    });
});

describe('ScheduledInvestmentEditor — late interest', () => {
    it('creates the late-interest block on the first toggle and removes it on the second', async () => {
        await setupI18n();
        const {onchange} = mount(twoPeriods());
        expect(screen.getByTestId('schedule-late-toggle')).toHaveAttribute('data-state', 'off');

        await fireEvent.click(screen.getByTestId('schedule-late-toggle'));

        expect(lastPayload(onchange)?.late_interest).toEqual({
            annual_rate: '0.1200',
            grace_period_days: 0,
            interest_type: 'COMPOUND',
            maturation_frequency: 'MONTHLY',
            generate_interest: false,
        });
        await waitFor(() => expect(screen.getByTestId('schedule-late-toggle')).toHaveAttribute('data-state', 'on'));
        // It joins the table as an extra row, on top of the two real periods.
        expect(tableRows()).toHaveLength(3);
        expect(document.querySelector('tbody tr[data-row-id="late-interest"]')).not.toBeNull();

        await fireEvent.click(screen.getByTestId('schedule-late-toggle'));
        expect(lastPayload(onchange)?.late_interest).toBeNull();
        await waitFor(() => expect(tableRows()).toHaveLength(2));
    });

    it('reads back the stored late-interest terms rather than the defaults', async () => {
        await setupI18n();
        const value = {
            ...twoPeriods(),
            late_interest: {annual_rate: '0.0800', grace_period_days: 15, interest_type: 'SIMPLE', maturation_frequency: 'DAILY', generate_interest: true},
        };
        const {onchange} = mount(value);

        expect(screen.getByTestId('schedule-late-toggle')).toHaveAttribute('data-state', 'on');
        expect(tableRows()).toHaveLength(3);

        await fireEvent.click(screen.getByTestId('schedule-add-period'));
        expect(lastPayload(onchange)?.late_interest).toEqual({
            annual_rate: '0.0800',
            grace_period_days: 15,
            interest_type: 'SIMPLE',
            maturation_frequency: 'DAILY',
            generate_interest: true,
        });
    });

    it('never lets the late-interest row be selected for a bulk operation', async () => {
        await setupI18n();
        const value = {...twoPeriods(), late_interest: {annual_rate: '0.0800', grace_period_days: 0, interest_type: 'SIMPLE', maturation_frequency: 'MONTHLY', generate_interest: false}};
        mount(value);

        // Merging or deleting it alongside real periods would corrupt the schedule.
        expect(screen.queryByTestId('dt-row-checkbox-late-interest')).toBeNull();
        expect(screen.getByTestId('dt-select-all')).toBeInTheDocument();
    });
});

describe('ScheduledInvestmentEditor — asset events', () => {
    it('reads stored events back into the table with their currency and notes', async () => {
        await setupI18n();
        const value = {
            ...twoPeriods(),
            asset_events: [
                {date: '2024-03-31', type: 'INTEREST', value: {code: 'EUR', amount: '81.25'}, notes: 'Q1 coupon'},
                {date: '2024-12-31', type: 'MATURITY_SETTLEMENT', value: {code: 'EUR', amount: '5000'}},
            ],
        };
        const {onchange} = mount(value);

        expect(screen.getAllByTestId('schedule-event-row')).toHaveLength(2);
        expect(screen.getByTestId('schedule-event-value-0')).toHaveValue(81.25);
        expect(screen.getByTestId('schedule-event-notes-0')).toHaveValue('Q1 coupon');
        expect(screen.getByTestId('schedule-event-value-1')).toHaveValue(5000);

        await fireEvent.click(screen.getByTestId('schedule-add-period'));
        const events = lastPayload(onchange)?.asset_events;
        expect(events).toHaveLength(2);
        expect(events[0]).toEqual({date: '2024-03-31', type: 'INTEREST', value: {code: 'EUR', amount: '81.25'}, notes: 'Q1 coupon'});
        // An absent note must not become the string "undefined" in the payload.
        expect(events[1].notes).toBeUndefined();
    });

    it('adds an event and re-stamps it with the schedule currency', async () => {
        await setupI18n();
        const {onchange} = mount(onePeriod()); // USD

        await fireEvent.click(screen.getByTestId('schedule-add-event'));

        const events = lastPayload(onchange)?.asset_events;
        expect(events).toHaveLength(1);
        expect(events[0].type).toBe('INTEREST');
        expect(events[0].value).toEqual({code: 'USD', amount: '0'});
        expect(screen.getAllByTestId('schedule-event-row')).toHaveLength(1);
    });

    it('edits an event in place without disturbing its siblings', async () => {
        await setupI18n();
        const value = {
            ...twoPeriods(),
            asset_events: [
                {date: '2024-03-31', type: 'INTEREST', value: {code: 'EUR', amount: '10'}, notes: 'first'},
                {date: '2024-06-30', type: 'INTEREST', value: {code: 'EUR', amount: '20'}, notes: 'second'},
            ],
        };
        const {onchange} = mount(value);

        await fireEvent.input(screen.getByTestId('schedule-event-value-1'), {target: {value: '99.5'}});

        const events = lastPayload(onchange)?.asset_events;
        expect(events[0]).toMatchObject({notes: 'first', value: {amount: '10'}});
        expect(events[1]).toMatchObject({notes: 'second', value: {amount: '99.5'}});
    });

    it('deletes the event the user pointed at, not the one after it', async () => {
        await setupI18n();
        const value = {
            ...twoPeriods(),
            asset_events: [
                {date: '2024-03-31', type: 'INTEREST', value: {code: 'EUR', amount: '10'}, notes: 'first'},
                {date: '2024-06-30', type: 'INTEREST', value: {code: 'EUR', amount: '20'}, notes: 'second'},
                {date: '2024-09-30', type: 'INTEREST', value: {code: 'EUR', amount: '30'}, notes: 'third'},
            ],
        };
        const {onchange} = mount(value);

        await fireEvent.click(screen.getByTestId('schedule-event-delete-1'));

        const events = lastPayload(onchange)?.asset_events;
        expect(events.map((e: {notes?: string}) => e.notes)).toEqual(['first', 'third']);
        await waitFor(() => expect(screen.getAllByTestId('schedule-event-row')).toHaveLength(2));
    });
});

describe('ScheduledInvestmentEditor — validity and locked modes', () => {
    it('calls a schedule with a negative rate invalid', async () => {
        await setupI18n();
        const value = {...onePeriod(), schedule: [{...(onePeriod().schedule as Period[])[0], annual_rate: '-0.02'}]};
        mount(value);

        expect(screen.getByTestId('schedule-status')).toHaveAttribute('data-valid', 'false');
    });

    it('calls a schedule with a cleared maturation frequency invalid', async () => {
        await setupI18n();
        // An empty string is the state the editor itself writes when a date edit
        // makes the chosen frequency impossible for the new period length; the
        // banner must not then claim the schedule is ready to save.
        const value = {...onePeriod(), schedule: [{...(onePeriod().schedule as Period[])[0], maturation_frequency: ''}]};
        mount(value);

        expect(screen.getByTestId('schedule-status')).toHaveAttribute('data-valid', 'false');
    });

    it('substitutes the default frequency when the stored one is absent', async () => {
        await setupI18n();
        // A null is treated as "never set" and defaulted, which is what keeps
        // schedules written by older versions of the provider loadable.
        const {onchange} = mount({...onePeriod(), schedule: [{...(onePeriod().schedule as Period[])[0], maturation_frequency: null}]});

        expect(screen.getByTestId('schedule-status')).toHaveAttribute('data-valid', 'true');
        await fireEvent.click(screen.getByTestId('schedule-add-period'));
        expect(lastSchedule(onchange)[0].maturation_frequency).toBe('MONTHLY');
    });

    it('calls a well-formed schedule valid', async () => {
        await setupI18n();
        mount(twoPeriods());
        expect(screen.getByTestId('schedule-status')).toHaveAttribute('data-valid', 'true');
    });

    it('withdraws every mutating control in readonly mode', async () => {
        await setupI18n();
        mount(twoPeriods(), {readonly: true});

        expect(screen.queryByTestId('schedule-add-period')).toBeNull();
        expect(screen.queryByTestId('schedule-add-event')).toBeNull();
        expect(screen.getByTestId('schedule-late-toggle')).toBeDisabled();
        expect(screen.getByTestId('schedule-initial-value')).toBeDisabled();
        // With selection off there is no checkbox column to bulk-act from.
        expect(screen.queryByTestId('dt-select-all')).toBeNull();
    });

    it('withdraws them in disabled mode too, and still shows the schedule', async () => {
        await setupI18n();
        mount(twoPeriods(), {disabled: true});

        expect(screen.queryByTestId('schedule-add-period')).toBeNull();
        expect(screen.getByTestId('schedule-initial-value')).toBeDisabled();
        // Read-only is not blank: the user must still be able to see the terms.
        expect(tableRows()).toHaveLength(2);
    });

    it('shows the row actions but disables them when the editor is locked', async () => {
        await setupI18n();
        mount(twoPeriods(), {readonly: true});

        await fireEvent.contextMenu(tableRows()[0]);
        const menu = screen.getByTestId('context-menu');

        // Keeping them visible tells the user the operations exist; disabling
        // them is what stops a locked schedule from being edited.
        expect(within(menu).getByTestId('schedule-action-split')).toBeDisabled();
        expect(within(menu).getByTestId('schedule-action-delete')).toBeDisabled();
    });
});

describe('ScheduledInvestmentEditor — the calendar arithmetic these tests could not touch before', () => {
    // This block exists because the component's own addDays/addMonths/midpointDate
    // read a date at *local* midnight and wrote it back in UTC, so east of Greenwich
    // every answer was a day behind — under TZ=Europe/Rome even addDays(iso, +1)
    // returned the same day, never advancing. The spec above was therefore written to
    // avoid every assertion that crossed those functions.
    //
    // They now live in $lib/utils/dateOnly and do the arithmetic in UTC end to end, so
    // the invariants the component *claims* can finally be asserted. These are the
    // tests that would have caught the defect, expressed as what the user sees.

    it('starts a new period the day after the previous one ends, not on top of it', async () => {
        await setupI18n();
        const {onchange} = mount(twoPeriods());

        await fireEvent.click(screen.getByTestId('schedule-add-period'));

        const schedule = lastSchedule(onchange);
        expect(schedule.length).toBeGreaterThan(2);
        const previous = schedule[schedule.length - 2];
        const added = schedule[schedule.length - 1];
        // The overlap the old arithmetic produced: `added.start_date` came out equal to
        // `previous.end_date`, so the boundary day belonged to both periods and its
        // interest was counted twice.
        expect(added.start_date).not.toBe(previous.end_date);
        expect(added.start_date).toBe('2025-01-01');
    });

    it('leaves no gap and no overlap across the whole schedule', async () => {
        await setupI18n();
        const {onchange} = mount(twoPeriods());

        await fireEvent.click(screen.getByTestId('schedule-add-period'));

        // The invariant the component documents about itself, asserted over every
        // adjacent pair rather than just the one that was appended.
        const schedule = lastSchedule(onchange);
        for (let i = 1; i < schedule.length; i++) {
            const gapDays = daysBetween(schedule[i - 1].end_date, schedule[i].start_date);
            expect(gapDays, `periods ${i - 1} and ${i} must be adjacent, not ${gapDays} days apart`).toBe(1);
        }
    });

    it('splits a period into two halves that do not share a day', async () => {
        await setupI18n();
        const {onchange} = mount(onePeriod());

        // Right-click is the path jsdom can measure — the ⋮ button needs a layout box.
        await fireEvent.contextMenu(tableRows()[0]);
        const menu = screen.getByTestId('context-menu');
        await fireEvent.click(within(menu).getByTestId('schedule-action-split'));
        await fireEvent.click(screen.getByTestId('boundary-modal-confirm'));

        const schedule = lastSchedule(onchange);
        expect(schedule).toHaveLength(2);
        // A shared boundary day is a day of interest counted twice.
        expect(daysBetween(schedule[0].end_date, schedule[1].start_date)).toBe(1);
        // And the split must stay inside the original span.
        expect(schedule[0].start_date).toBe('2024-01-01');
        expect(schedule[1].end_date).toBe('2024-12-31');
    });
});

describe('ScheduledInvestmentEditor — telling an echo apart from a real update', () => {
    // The component skips the prop update that its own `onchange` caused, because
    // reloading from that echo would undo the edit that produced it. It used to do so
    // by counting — "skip the next update, whatever it is" — which cannot tell an echo
    // from a genuinely different value. When the two got out of step the guard ate the
    // wrong one, in silence, and the component went on showing the stale schedule.
    //
    // It now compares what arrived with what it sent.

    it('does not swallow the first real value after the empty-mount emission', async () => {
        await setupI18n();
        const onchange = vi.fn();
        // Mounting on an empty value makes the component emit on its own, from the
        // queueMicrotask in the sync effect — so the guard gets armed with no user edit
        // behind it, and nothing consumes it because the parent never sent anything.
        const {rerender} = render(ScheduledInvestmentEditor, {value: {}, onchange});
        await waitFor(() => expect(onchange).toHaveBeenCalled());

        // Now the real schedule arrives, a moment later, from a fetch. Under the
        // counting guard this was eaten and the editor stayed empty.
        await rerender({value: twoPeriods(), onchange});

        await waitFor(() => expect(tableRows()).toHaveLength(2));
    });

    it('applies an external update that differs from what it just emitted', async () => {
        await setupI18n();
        const {onchange, rerender} = mount(onePeriod());
        await waitFor(() => expect(tableRows()).toHaveLength(1));

        // An edit, so the guard is armed.
        await fireEvent.click(screen.getByTestId('schedule-add-period'));
        expect(onchange).toHaveBeenCalled();

        // The parent now hands back something *different* — a response the server
        // normalised, a change of asset, a form reset. Under the counting guard this
        // was swallowed and the two-period schedule never appeared.
        await rerender({value: twoPeriods(), onchange});

        await waitFor(() => expect(tableRows()).toHaveLength(2));
        const [first] = tableRows();
        expect(first).toBeInTheDocument();
    });

    it('still ignores the echo of its own payload', async () => {
        await setupI18n();
        const {onchange, rerender} = mount(onePeriod());

        await fireEvent.click(screen.getByTestId('schedule-add-period'));
        const emitted = lastPayload(onchange);
        const rowsAfterEdit = tableRows().length;

        // The parent doing what a parent does: storing what it received and handing it
        // straight back. Reloading from this would throw away the edit.
        await rerender({value: emitted, onchange});

        await waitFor(() => expect(tableRows()).toHaveLength(rowsAfterEdit));
    });
});

describe('ScheduledInvestmentEditor — bulk deleting periods (gap reflow)', () => {
    /** Three contiguous four-month periods, distinct rates so the survivors are identifiable. */
    function threePeriods(): Record<string, unknown> {
        return {
            initial_value: {code: 'EUR', amount: '5000'},
            interest_type: 'COMPOUND',
            day_count: 'ACT/360',
            schedule: [
                {start_date: '2024-01-01', end_date: '2024-04-30', annual_rate: '0.0100', maturation_frequency: 'MONTHLY', generate_interest: false},
                {start_date: '2024-05-01', end_date: '2024-08-31', annual_rate: '0.0200', maturation_frequency: 'MONTHLY', generate_interest: false},
                {start_date: '2024-09-01', end_date: '2024-12-31', annual_rate: '0.0300', maturation_frequency: 'MONTHLY', generate_interest: false},
            ],
            late_interest: null,
            asset_events: [],
        };
    }

    async function selectRow(rowIndex: number) {
        const id = tableRows()[rowIndex].getAttribute('data-row-id');
        await fireEvent.click(screen.getByTestId(`dt-row-checkbox-${id}`));
    }

    it('auto-resolves a head deletion by handing its range to the next survivor — no dialog', async () => {
        await setupI18n();
        const {onchange} = mount(threePeriods());

        await selectRow(0);
        await fireEvent.click(screen.getByTestId('schedule-bulk-delete'));

        // A head block has no predecessor to negotiate a seam with, so no modal.
        expect(screen.queryByTestId('boundary-modal-confirm')).toBeNull();
        const schedule = lastSchedule(onchange);
        expect(schedule).toHaveLength(2);
        // The freed range folds forward: the new first period still opens the schedule.
        expect(schedule[0].start_date).toBe('2024-01-01');
        expect(schedule[0].annual_rate).toBe('0.0200');
        expect(schedule[1].end_date).toBe('2024-12-31');
    });

    it('auto-resolves a tail deletion by extending the previous survivor — no dialog', async () => {
        await setupI18n();
        const {onchange} = mount(threePeriods());

        await selectRow(2);
        await fireEvent.click(screen.getByTestId('schedule-bulk-delete'));

        expect(screen.queryByTestId('boundary-modal-confirm')).toBeNull();
        const schedule = lastSchedule(onchange);
        expect(schedule).toHaveLength(2);
        // The freed range folds backward: the new last period still closes the schedule.
        expect(schedule[0].start_date).toBe('2024-01-01');
        expect(schedule[1].end_date).toBe('2024-12-31');
        expect(schedule[1].annual_rate).toBe('0.0200');
    });

    it('asks where to place the seam when a middle block is deleted, then reflows the gap', async () => {
        await setupI18n();
        const {onchange} = mount(threePeriods());

        await selectRow(1);
        await fireEvent.click(screen.getByTestId('schedule-bulk-delete'));

        // A middle block is bounded on both sides, so the user must place the seam.
        await waitFor(() => expect(screen.getByTestId('boundary-modal-confirm')).toBeEnabled());
        await fireEvent.click(screen.getByTestId('boundary-modal-confirm'));

        const schedule = lastSchedule(onchange);
        expect(schedule).toHaveLength(2);
        // The neighbours split the gap; the outer edges of the schedule cannot move.
        expect(schedule[0].start_date).toBe('2024-01-01');
        expect(schedule[0].annual_rate).toBe('0.0100');
        expect(schedule[1].end_date).toBe('2024-12-31');
        expect(schedule[1].annual_rate).toBe('0.0300');
    });

    it('leaves the schedule untouched when the middle-delete dialog is cancelled', async () => {
        await setupI18n();
        const {onchange} = mount(threePeriods());

        await selectRow(1);
        await fireEvent.click(screen.getByTestId('schedule-bulk-delete'));
        await waitFor(() => expect(screen.getByTestId('boundary-modal-cancel')).toBeInTheDocument());
        await fireEvent.click(screen.getByTestId('boundary-modal-cancel'));

        expect(onchange).not.toHaveBeenCalled();
        expect(tableRows()).toHaveLength(3);
    });
});

describe('ScheduledInvestmentEditor — editing an event note', () => {
    it('rewrites the note the user pointed at, leaving value and siblings alone', async () => {
        await setupI18n();
        const value = {
            ...twoPeriods(),
            asset_events: [
                {date: '2024-03-31', type: 'INTEREST', value: {code: 'EUR', amount: '10'}, notes: 'first'},
                {date: '2024-06-30', type: 'INTEREST', value: {code: 'EUR', amount: '20'}, notes: 'second'},
            ],
        };
        const {onchange} = mount(value);

        await fireEvent.input(screen.getByTestId('schedule-event-notes-1'), {target: {value: 'amended'}});

        const events = lastPayload(onchange)?.asset_events;
        expect(events[0]).toMatchObject({notes: 'first', value: {amount: '10'}});
        expect(events[1]).toMatchObject({notes: 'amended', value: {amount: '20'}});
    });
});
