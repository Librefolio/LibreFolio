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
import {writable} from 'svelte/store';
import {cleanup, fireEvent, render, screen, setupI18n, waitFor, within} from '$test/component';
import {zodiosApi} from '$lib/api';
import {schemas} from '$lib/api/generated';

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
