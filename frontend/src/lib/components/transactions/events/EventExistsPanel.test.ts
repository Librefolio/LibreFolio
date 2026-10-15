// @vitest-environment jsdom
/**
 * EventExistsPanel — component test (Vitest + jsdom). Release 1.3, decision 20 (workstream W, lot E1b).
 *
 * «+ New event» never overwrites: when the asset already holds an event of that type on that date,
 * the create is refused (409 EVENT_EXISTS) and this panel shows what is there. Per event, «Use this»
 * links it; «Edit this» opens it in the form — manual events only: a provider's event is rewritten
 * by every refresh, so it carries a note instead of the button. «Cancel» goes back to the form.
 *
 * The provider branch is also exercised end to end (tx-event-create-exists.spec.ts, through a
 * `scheduled_investment` assignment on an asset of the spec's own); here it is pinned without a
 * backend, with the callbacks — the component's whole contract — asserted directly.
 *
 * No translated text is asserted: items are found by `data-event-id`, actions by test id, and the
 * only text read is the amount, which is data. The amount reads as `existingAmountText` writes it
 * (pinned in eventSaveError.test.ts): the panel and the form «Edit this» opens show it the same way.
 *
 * Before E1b `EventExistsPanel.svelte` does not exist: this file fails to load.
 */
import {beforeAll, describe, expect, it, vi} from 'vitest';
import {fireEvent, render, screen, setupI18n, within} from '$test/component';
import EventExistsPanel from './EventExistsPanel.svelte';
import {existingAmountText, type ExistingEvent} from './eventSaveError';

const MANUAL: ExistingEvent = {id: 41, date: '2026-03-16', type: 'DIVIDEND', value: {code: 'USD', amount: '0.123456'}, notes: 'Q1 payout', is_auto: false, linked_transactions: 2};
const FROM_PROVIDER: ExistingEvent = {id: 42, date: '2026-03-16', type: 'DIVIDEND', value: {code: 'USD', amount: '1.500000'}, notes: null, is_auto: true, linked_transactions: 0};

function setup(events: ExistingEvent[]) {
    const onuse = vi.fn();
    const onedit = vi.fn();
    const oncancel = vi.fn();
    // Under `props`: the component's `events` prop is also a mount option name (Svelte's legacy
    // `events`), so a bare object would be read as mount options and its callbacks refused.
    render(EventExistsPanel, {props: {events, onuse, onedit, oncancel}});
    return {onuse, onedit, oncancel};
}

/** The item of one event, by the id it carries — never by its position in the list. */
function item(id: number): HTMLElement {
    const found = screen.getAllByTestId('event-exists-item').find((el) => el.getAttribute('data-event-id') === String(id));
    if (!found) throw new Error(`no event-exists-item carries data-event-id=${id}`);
    return found;
}

describe('EventExistsPanel', () => {
    beforeAll(async () => {
        await setupI18n();
    });

    it('lists one item per event, each carrying its id', () => {
        setup([MANUAL, FROM_PROVIDER]);

        expect(screen.getByTestId('event-exists-panel')).toBeInTheDocument();
        expect(
            screen
                .getAllByTestId('event-exists-item')
                .map((el) => el.getAttribute('data-event-id'))
                .sort(),
        ).toEqual(['41', '42']);
    });

    it('a manual event can be used or edited, and carries no provider note', () => {
        setup([MANUAL]);
        const manual = within(item(MANUAL.id));

        expect(manual.getByTestId('event-exists-use')).toBeInTheDocument();
        expect(manual.getByTestId('event-exists-edit')).toBeInTheDocument();
        expect(manual.queryByTestId('event-exists-provider-note')).toBeNull();
    });

    it('a provider event can only be used: no edit button, a note says why', () => {
        setup([MANUAL, FROM_PROVIDER]);
        const provider = within(item(FROM_PROVIDER.id));

        expect(provider.getByTestId('event-exists-use')).toBeInTheDocument();
        expect(provider.getByTestId('event-exists-provider-note')).toBeInTheDocument();
        expect(provider.queryByTestId('event-exists-edit')).toBeNull();
        // The manual item beside it still offers both: the rule is per event, not per panel.
        expect(within(item(MANUAL.id)).getByTestId('event-exists-edit')).toBeInTheDocument();
    });

    it('«Use this» hands back the event of its own item', async () => {
        const {onuse, onedit, oncancel} = setup([MANUAL, FROM_PROVIDER]);

        await fireEvent.click(within(item(FROM_PROVIDER.id)).getByTestId('event-exists-use'));

        expect(onuse).toHaveBeenCalledTimes(1);
        expect(onuse).toHaveBeenCalledWith(FROM_PROVIDER);
        expect(onedit).not.toHaveBeenCalled();
        expect(oncancel).not.toHaveBeenCalled();
    });

    it('«Edit this» hands back the event of its own item', async () => {
        const {onuse, onedit} = setup([MANUAL, FROM_PROVIDER]);

        await fireEvent.click(within(item(MANUAL.id)).getByTestId('event-exists-edit'));

        expect(onedit).toHaveBeenCalledTimes(1);
        expect(onedit).toHaveBeenCalledWith(MANUAL);
        expect(onuse).not.toHaveBeenCalled();
    });

    it('«Cancel» only calls back', async () => {
        const {onuse, onedit, oncancel} = setup([MANUAL]);

        await fireEvent.click(screen.getByTestId('event-exists-cancel'));

        expect(oncancel).toHaveBeenCalledTimes(1);
        expect(onuse).not.toHaveBeenCalled();
        expect(onedit).not.toHaveBeenCalled();
    });

    it('shows the stored amount with its own decimals, and at least two', () => {
        setup([MANUAL, FROM_PROVIDER]);

        // A per-share dividend can need six decimals: none is dropped.
        expect(within(item(MANUAL.id)).getByText('0.123456')).toBeInTheDocument();
        // Trailing zeros go, down to two.
        expect(within(item(FROM_PROVIDER.id)).getByText('1.50')).toBeInTheDocument();
    });

    it('reads every amount as existingAmountText writes it, never as stored', () => {
        const amounts = ['1.500000', '0.123456', '1', '2.000000', '1234.500000'];
        const events = amounts.map((amount, i): ExistingEvent => ({...MANUAL, id: 51 + i, value: {code: 'USD', amount}}));
        setup(events);

        for (const event of events) {
            const shown = existingAmountText(event.value.amount);
            expect(within(item(event.id)).getByText(shown), `${event.value.amount} reads ${shown}`).toBeInTheDocument();
            if (shown !== event.value.amount) expect(within(item(event.id)).queryByText(event.value.amount), `not ${event.value.amount} as stored`).toBeNull();
        }
    });
});
