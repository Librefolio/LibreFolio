// @vitest-environment jsdom
/**
 * EventCreateMiniModal — component test (Vitest + jsdom). Lot C-97b, «the decimal places in input».
 *
 * An asset event keeps its value with six decimals (`AssetEvent.value` Numeric(18, 6), C-97a); over
 * that the backend refuses with EVENT_TOO_MANY_DIGITS and the maximum, and never rounds. The mini
 * modal must do neither of the two things it does today: on blur it `parseFloat`s the typed amount
 * and writes it back with `toFixed(min(max(2, typed decimals), 8))` — up to 8 decimals, past the
 * backend's 6, and rounded past 8 — and it prefills a suggested amount with `toFixed(2)`.
 *
 * The contract pinned: an amount stays as typed; over six decimals a message under the field says
 * why (`event-create-amount-digits-error`, `data-max="6"`, its text the cure's choice) and nothing
 * is sent; within six it is valid and sent with its decimals; a suggestion is prefilled whole.
 *
 * The network is the `$lib/api` Proxy the transaction component tests use: every endpoint a local
 * spy, the upsert answering one saved event. Nothing is owned in a database. Only `data-testid` /
 * `data-*` / values are asserted, never a translated text.
 */
import {afterEach, beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';
import {get, writable} from 'svelte/store';
import {cleanup, fireEvent, render, screen, setupI18n, waitFor, within} from '$test/component';
import {zodiosApi} from '$lib/api';
import {schemas} from '$lib/api/generated';
import {_} from '$lib/i18n';
import {getCurrencyInfo} from '$lib/stores/reference/currencyStore';

vi.mock('$lib/api', () => {
    const cache = new Map<string, ReturnType<typeof vi.fn>>();
    const zodiosApi = new Proxy(
        {},
        {
            get(_t, prop: string) {
                if (!cache.has(prop))
                    cache.set(
                        prop,
                        vi.fn(async () => undefined),
                    );
                return cache.get(prop);
            },
        },
    );
    return {zodiosApi, ApiError: class ApiError extends Error {}, axiosInstance: {}};
});
vi.mock('$lib/stores/app/toastStore.svelte', () => ({
    toasts: {success: vi.fn(), error: vi.fn(), warning: vi.fn(), info: vi.fn()},
}));
vi.mock('$lib/stores/app/language', () => ({currentLanguage: writable('en')}));

import EventCreateMiniModal from './EventCreateMiniModal.svelte';
import {toasts} from '$lib/stores/app/toastStore.svelte';
import {uiLocale} from '$lib/stores/app/uiLocale';

const ASSET_ID = 7;
const SAVED_EVENT_ID = 901;
const DEFAULT_DATE = '2024-03-10';
const SAVED = schemas.FABulkEventUpsertResponse.parse({
    results: [{asset_id: ASSET_ID, count: 1, message: 'ok', event_ids: [SAVED_EVENT_ID]}],
    success_count: 1,
});

const upsert = vi.mocked(zodiosApi.upsert_events_bulk_api_v1_assets_events_post);

function mount(props: Record<string, unknown> = {}) {
    const oncreated = vi.fn();
    const onclose = vi.fn();
    render(EventCreateMiniModal, {
        props: {open: true, assetId: ASSET_ID, assetName: 'PEPE', assetCurrency: 'USD', defaultDate: DEFAULT_DATE, defaultEventType: 'DIVIDEND', oncreated, onclose, ...props},
    });
    return {oncreated, onclose};
}

/**
 * The form is seeded by an effect when the modal opens. Its date is the presence barrier: once it
 * reads the default date, the amount has been seeded in the same run — before that, a value typed
 * could still be overwritten by the seed.
 */
async function seededAmount(): Promise<HTMLInputElement> {
    await screen.findByTestId('event-create-mini-modal');
    const date = within(screen.getByTestId('single-date-picker-root')).getByRole('textbox');
    await waitFor(() => expect(date, 'premise: the open effect has seeded the form').toHaveValue(DEFAULT_DATE));
    return screen.getByTestId('event-create-amount') as HTMLInputElement;
}

function digitsError(): HTMLElement | null {
    return screen.queryByTestId('event-create-amount-digits-error');
}

/** Within the budget: no message — absent, or rendered hidden. */
function expectNoDigitsError() {
    const message = digitsError();
    if (message) expect(message, 'event-create-amount-digits-error shows for an amount within six decimals').not.toBeVisible();
}

describe('EventCreateMiniModal — the amount keeps its decimals (C-97b)', () => {
    beforeAll(async () => {
        await setupI18n();
    });

    beforeEach(() => {
        vi.clearAllMocks();
        upsert.mockResolvedValue(SAVED);
    });

    afterEach(() => {
        cleanup();
    });

    // Red today, two ways. 0.1234567 survives the blur (toFixed(7) writes it back unchanged — that part
    // is green), but no message says why it is refused, and the create is sent for the backend to
    // refuse. 0.123456789 is also rounded on blur, to 0.12345679.
    it.each(['0.1234567', '0.123456789'])('%j stays as typed, is explained with data-max="6", and is never sent', async (typed) => {
        // Whether the create is SENT is the question, not what comes back: the server never answers
        // here, so nothing of the save runs on after the test.
        upsert.mockReturnValue(new Promise<never>(() => {}));
        mount();
        const amount = await seededAmount();

        await fireEvent.input(amount, {target: {value: typed}});
        await fireEvent.blur(amount);
        const message = digitsError();
        // The cure may disable the control or refuse on click: either way nothing reaches the API.
        const submit = screen.getByTestId('event-create-submit') as HTMLButtonElement;
        if (!submit.disabled) await fireEvent.click(submit);

        // One assertion over the three facts, so a red shows every disagreement at once.
        expect({
            value: amount.value,
            digitsMax: message?.getAttribute('data-max') ?? null,
            sent: upsert.mock.calls.length,
        }).toEqual({value: typed, digitsMax: '6', sent: 0});
        expect(message).toBeVisible();
    });

    // Guard: green today — six decimals survive the blur (toFixed(6)), nothing explains them, and the
    // create carries them. After the cure the same must hold: the refusal of seven is not a refusal of six.
    it('0.123456 stays as typed, is valid, and is sent with its six decimals', async () => {
        const {oncreated} = mount();
        const amount = await seededAmount();

        await fireEvent.input(amount, {target: {value: '0.123456'}});
        await fireEvent.blur(amount);

        expect(amount).toHaveValue('0.123456');
        expectNoDigitsError();
        const submit = screen.getByTestId('event-create-submit');
        expect(submit).toBeEnabled();
        await fireEvent.click(submit);

        await waitFor(() => expect(upsert).toHaveBeenCalledTimes(1));
        const items = upsert.mock.calls[0]?.[0];
        expect(items, 'one item, for the asset').toHaveLength(1);
        expect(items?.[0]).toMatchObject({asset_id: ASSET_ID, mode: 'create'});
        const point = items?.[0]?.events?.[0];
        expect(point?.value.code).toBe('USD');
        expect(String(point?.value.amount), 'the six decimals are sent as typed').toBe('0.123456');
        await waitFor(() => expect(oncreated).toHaveBeenCalledWith(SAVED_EVENT_ID));
    });

    // Red today: the open effect prefills parseFloat(suggestedAmount).toFixed(2), so 0.2345 reads 0.23.
    it('a suggested amount of 0.2345 is prefilled whole, not rounded to 0.23', async () => {
        mount({suggestedAmount: '0.2345'});
        const amount = await seededAmount();

        expect(amount, 'the suggestion keeps its four decimals').toHaveValue('0.2345');
        expectNoDigitsError();
    });
});

/**
 * C-97c-1 (decision D-C97c-1 of the coordinator, 17/10) — the toast of a save shows the value saved, exactly.
 *
 * After a save the modal raises a success toast describing the event: its type, its date and its value. The value is
 * written with `formatFixed(parseFloat(amount), 2)`, so an event of 0.123456 USD — six decimals, all of them kept by
 * `AssetEvent.value` and sent as typed — is announced as 0.12. The contract: the value as saved, at least two decimals
 * and up to six, never through a float. Red: 0.123456. Guard, green today and after: 1.5 is announced 1.50.
 *
 * The toast store is the spy above; the toast must be a success, raised once; its message is read for the value alone,
 * as a whole number token — no digit, decimal mark or separator glued to either side — never for the words around it,
 * which are translated. The language store is the `writable('en')` above, so on jsdom's en-US browser the value is
 * written en-US: the expected digits are typed.
 */
describe('EventCreateMiniModal — the save toast shows the value exactly, two to six decimals (C-97c-1)', () => {
    const success = vi.mocked(toasts.success);

    /** `digits` as a whole number in a text: no digit, decimal mark or group separator glued to either side. */
    function numberToken(digits: string): RegExp {
        return new RegExp(`(?<![\\d.,])${digits.replace(/\./g, '\\.')}(?![.,]?\\d)`);
    }

    /** Type `typed`, leave the field, save; the message of the one success toast the save raised. */
    async function savedToast(typed: string): Promise<string> {
        const {oncreated} = mount();
        const amount = await seededAmount();
        await fireEvent.input(amount, {target: {value: typed}});
        await fireEvent.blur(amount);
        const shown = amount.value;
        await fireEvent.click(screen.getByTestId('event-create-submit'));

        await waitFor(() => expect(oncreated, 'premise: the save went through').toHaveBeenCalledWith(SAVED_EVENT_ID));
        const sent = upsert.mock.calls[0]?.[0]?.[0]?.events?.[0]?.value.amount;
        expect(String(sent), 'control: the save sends the value the field shows').toBe(shown);
        expect(success, 'one success toast for the save').toHaveBeenCalledTimes(1);
        return String(success.mock.calls[0]?.[0]);
    }

    beforeAll(async () => {
        await setupI18n();
    });

    beforeEach(() => {
        vi.clearAllMocks();
        upsert.mockResolvedValue(SAVED);
    });

    afterEach(() => {
        cleanup();
    });

    it('0.123456 is announced 0.123456 — its six decimals, not 0.12', async () => {
        expect(uiLocale(), 'control: the English UI on jsdom’s en-US browser is written en-US').toBe('en-US');

        expect(await savedToast('0.123456')).toMatch(numberToken('0.123456'));
    });

    it('guard: 1.5 is announced 1.50 — two decimals at least', async () => {
        expect(uiLocale(), 'control: the English UI on jsdom’s en-US browser is written en-US').toBe('en-US');

        expect(await savedToast('1.5')).toMatch(numberToken('1.50'));
    });
});

/**
 * W-B87 — the mini modal for an ADJUSTMENT row (a stock split an importer flagged `possible_split`).
 *
 * For `defaultEventType="ADJUSTMENT"` the modal offers the types of `eventTypesForTx` (SPLIT, PRICE_ADJUSTMENT) and starts on
 * `defaultEventTypeForTx` (SPLIT). A SPLIT's amount is a RATIO — new shares per old share, `3` for a 3 for 1, `0.25` for a 1 for
 * 4 — not a sum of money, so for SPLIT:
 *
 *   - the label is the key `transactions.bulk.possibleSplit.ratioLabel`, not `transactions.fields.amount`;
 *   - the placeholder is `2`, and the asset's currency is not written next to the field;
 *   - a paragraph (`event-create-ratio-hint`, key `transactions.bulk.possibleSplit.ratioHint`) explains it, for SPLIT only;
 *   - the typed ratio is never reformatted at the blur (`3` stays `3`, not `3.00`), and a suggestion (`suggestedAmount`: the
 *     importer's rounded ratio) is written as given in the field, with no two decimals either; no suggestion: the field is empty;
 *   - the create sends `{mode: 'create', type: 'SPLIT', value: {code: <asset currency>, amount: <the ratio, its digits>}}`;
 *   - a ratio of 0, or one that is no number, is never sent (the message of `eventCreateAmountRequired`, as today).
 *
 * Every other type is untouched: the guards at the end are green today and must stay so.
 *
 * Text. The suite boots the real catalogue, so a label is compared with what `$_(key)` says for that very key, read in the test:
 * no English is typed. The label of a ratio must be `ratioLabel`'s, and not the amount label's. Controls are found by
 * `data-testid`; the type list is read through its `role="option"` entries, in the order the modal offers them.
 */
describe('EventCreateMiniModal — an ADJUSTMENT row creates a SPLIT whose amount is a ratio (W-B87)', () => {
    const textOf = (key: string): string => get(_)(key);

    beforeAll(async () => {
        await setupI18n();
    });

    beforeEach(() => {
        vi.clearAllMocks();
        upsert.mockResolvedValue(SAVED);
    });

    afterEach(() => {
        cleanup();
    });

    /** The modal for an ADJUSTMENT row, opened and seeded; returns the amount field. */
    async function mountForAdjustment(props: Record<string, unknown> = {}) {
        const handlers = mount({defaultEventType: 'ADJUSTMENT', ...props});
        const amount = await seededAmount();
        return {...handlers, amount};
    }

    /** The options of the type select, in the order offered: open it, read the `role="option"` entries. */
    async function typeOptions(): Promise<HTMLElement[]> {
        await fireEvent.click(screen.getByTestId('event-create-type-button'));
        const dropdown = await screen.findByTestId('event-create-type-dropdown');
        return within(dropdown).getAllByRole('option');
    }

    async function closeTypeSelect(): Promise<void> {
        const button = screen.getByTestId('event-create-type-button');
        if (button.getAttribute('aria-expanded') === 'true') await fireEvent.click(button);
    }

    function amountLabel(): HTMLElement {
        const label = document.querySelector<HTMLElement>('label[for="event-amount"]');
        if (!label) throw new Error('the amount field has no label[for="event-amount"]');
        return label;
    }

    it('offers the SPLIT and PRICE_ADJUSTMENT events, in that order, and starts on SPLIT', async () => {
        await mountForAdjustment();

        expect(screen.getByTestId('event-create-type-button'), 'the select starts on SPLIT').toHaveTextContent(textOf('assetDetail.eventType.SPLIT'));
        const options = await typeOptions();
        expect(options, 'two events on offer, not the three of a dividend').toHaveLength(2);
        expect(options[0]).toHaveTextContent(textOf('assetDetail.eventType.SPLIT'));
        expect(options[1]).toHaveTextContent(textOf('assetDetail.eventType.PRICE_ADJUSTMENT'));
    });

    it('for SPLIT the field is a ratio: its own label, the placeholder 2, the explanation, no currency beside it', async () => {
        const {amount} = await mountForAdjustment();

        expect(textOf('transactions.bulk.possibleSplit.ratioLabel'), 'premise: the ratio label is not the amount label').not.toBe(textOf('transactions.fields.amount'));
        expect(amountLabel()).toHaveTextContent(textOf('transactions.bulk.possibleSplit.ratioLabel'));
        expect(amountLabel(), 'the field is no longer called amount').not.toHaveTextContent(textOf('transactions.fields.amount'));
        expect(amount).toHaveAttribute('placeholder', '2');
        expect(screen.queryByTestId('event-create-ratio-hint'), 'SPLIT is explained').not.toBeNull();
        const beside = amount.parentElement as HTMLElement;
        expect(beside.textContent ?? '', 'a ratio has no currency: neither the code').not.toContain('USD');
        expect(beside.textContent ?? '', 'nor its symbol').not.toContain(getCurrencyInfo('USD').symbol);
    });

    it('the ratio opens empty when nothing is suggested, even if the other types would have been prefilled', async () => {
        const {amount} = await mountForAdjustment();

        expect(amount).toHaveValue('');
        expect(screen.getByTestId('event-create-submit'), 'nothing to send yet').toBeDisabled();
    });

    it.each([
        ['3', '3'],
        ['0.25', '0.25'],
        ['2.5', '2.5'],
    ])('a suggested ratio of %s opens as %s: written as given, never with two decimals', async (suggested, shown) => {
        const {amount} = await mountForAdjustment({suggestedAmount: suggested});

        expect(amount).toHaveValue(shown);
        expect(screen.getByTestId('event-create-submit')).toBeEnabled();
    });

    it.each([
        ['3', '3'],
        ['0.25', '0.25'],
        ['1.5', '1.5'],
    ])('a ratio of %s stays %s at the blur', async (typed, shown) => {
        const {amount} = await mountForAdjustment();

        await fireEvent.input(amount, {target: {value: typed}});
        await fireEvent.blur(amount);

        expect(amount, 'the blur must not write 3.00').toHaveValue(shown);
    });

    it('creates a SPLIT with the ratio as typed, in the asset currency, and hands back the saved event', async () => {
        const {amount, oncreated, onclose} = await mountForAdjustment();

        await fireEvent.input(amount, {target: {value: '3'}});
        await fireEvent.blur(amount);
        await fireEvent.click(screen.getByTestId('event-create-submit'));

        await waitFor(() => expect(upsert).toHaveBeenCalledTimes(1));
        const items = upsert.mock.calls[0]?.[0];
        expect(items, 'one item, for the asset').toHaveLength(1);
        expect(items?.[0]).toMatchObject({asset_id: ASSET_ID, mode: 'create'});
        const point = items?.[0]?.events?.[0];
        expect(point?.type).toBe('SPLIT');
        expect(point?.date).toBe(DEFAULT_DATE);
        expect(point?.value.code, 'the value carries the asset currency as its code').toBe('USD');
        expect(String(point?.value.amount), 'the ratio, its digits, no 3.00').toBe('3');
        await waitFor(() => expect(oncreated).toHaveBeenCalledWith(SAVED_EVENT_ID));
        expect(onclose).toHaveBeenCalled();
    });

    it('creates a 1 for 4 split as 0.25', async () => {
        const {amount} = await mountForAdjustment();

        await fireEvent.input(amount, {target: {value: '0.25'}});
        await fireEvent.blur(amount);
        await fireEvent.click(screen.getByTestId('event-create-submit'));

        await waitFor(() => expect(upsert).toHaveBeenCalledTimes(1));
        const point = upsert.mock.calls[0]?.[0]?.[0]?.events?.[0];
        expect(point?.type).toBe('SPLIT');
        expect(String(point?.value.amount)).toBe('0.25');
    });

    it('a suggested ratio is sent as the field shows it', async () => {
        await mountForAdjustment({suggestedAmount: '3'});

        await fireEvent.click(screen.getByTestId('event-create-submit'));

        await waitFor(() => expect(upsert).toHaveBeenCalledTimes(1));
        const point = upsert.mock.calls[0]?.[0]?.[0]?.events?.[0];
        expect(point?.type).toBe('SPLIT');
        expect(String(point?.value.amount)).toBe('3');
    });

    it.each(['0', '0.00', 'abc'])('a ratio of %j is never sent', async (typed) => {
        upsert.mockReturnValue(new Promise<never>(() => {}));
        const {amount} = await mountForAdjustment();

        await fireEvent.input(amount, {target: {value: typed}});
        await fireEvent.blur(amount);
        const submit = screen.getByTestId('event-create-submit') as HTMLButtonElement;
        // The cure may disable the button or refuse on click: either way nothing reaches the API, and a refusal says so.
        if (!submit.disabled) {
            await fireEvent.click(submit);
            expect(await screen.findByTestId('info-banner-error'), 'the refusal is announced').toBeVisible();
        }

        expect(upsert).not.toHaveBeenCalled();
    });

    it('PRICE_ADJUSTMENT on the same row is a money amount again: the amount label and the currency are back, no ratio explanation', async () => {
        const {amount} = await mountForAdjustment();

        const options = await typeOptions();
        const priceAdjustment = options.find((option) => (option.textContent ?? '').includes(textOf('assetDetail.eventType.PRICE_ADJUSTMENT')));
        if (!priceAdjustment) throw new Error('premise: the PRICE_ADJUSTMENT option is offered');
        await fireEvent.click(priceAdjustment);
        await closeTypeSelect();

        expect(screen.getByTestId('event-create-type-button'), 'premise: the row now creates a PRICE_ADJUSTMENT').toHaveTextContent(textOf('assetDetail.eventType.PRICE_ADJUSTMENT'));
        await waitFor(() => expect(screen.queryByTestId('event-create-ratio-hint')).toBeNull());
        expect(amountLabel()).toHaveTextContent(textOf('transactions.fields.amount'));
        expect((amount.parentElement as HTMLElement).textContent ?? '').toContain('USD');
    });

    // Guards, green today: every type that is not an ADJUSTMENT row keeps its form.
    describe('guards: a row that is not an ADJUSTMENT keeps its dividend form', () => {
        it('offers the three TX-compatible events and starts on DIVIDEND', async () => {
            mount({defaultEventType: 'DIVIDEND'});
            await seededAmount();

            expect(screen.getByTestId('event-create-type-button')).toHaveTextContent(textOf('assetDetail.eventType.DIVIDEND'));
            const options = await typeOptions();
            expect(options).toHaveLength(3);
            expect(options[0]).toHaveTextContent(textOf('assetDetail.eventType.DIVIDEND'));
            expect(options[1]).toHaveTextContent(textOf('assetDetail.eventType.INTEREST'));
            expect(options[2]).toHaveTextContent(textOf('assetDetail.eventType.PRICE_ADJUSTMENT'));
        });

        it('keeps the money amount: its label, the currency beside it, two decimals at the blur, the suggestion at two decimals, no ratio hint', async () => {
            mount({defaultEventType: 'DIVIDEND', suggestedAmount: '5'});
            const amount = await seededAmount();

            expect(amountLabel()).toHaveTextContent(textOf('transactions.fields.amount'));
            expect(amount).toHaveAttribute('placeholder', '0.00');
            expect((amount.parentElement as HTMLElement).textContent ?? '').toContain('USD');
            expect(screen.queryByTestId('event-create-ratio-hint')).toBeNull();
            expect(amount, 'the suggestion is prefilled with two decimals').toHaveValue('5.00');
            await fireEvent.input(amount, {target: {value: '1'}});
            await fireEvent.blur(amount);
            expect(amount).toHaveValue('1.00');
        });

        it('INTEREST starts on INTEREST', async () => {
            mount({defaultEventType: 'INTEREST'});
            await seededAmount();

            expect(screen.getByTestId('event-create-type-button')).toHaveTextContent(textOf('assetDetail.eventType.INTEREST'));
        });
    });
});
