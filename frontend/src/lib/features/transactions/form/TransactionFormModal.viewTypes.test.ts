// @vitest-environment jsdom
/**
 * TransactionFormModal — a saved row opened before the transaction types have arrived (project 66, lot TL-1d).
 * RED FIRST.
 *
 * The developer saw, on a phone, the read-only view of a saved BUY showing the amount as the raw signed value
 * («-1234.56», with the danger border of a wrong sign) where the edit form shows the magnitude. Cause: `fromTx` builds the
 * draft once, at open, from `getTypeRule(type)`. A cold page opens the form before `GET /transactions/types` answers, so
 * the rule is the permissive FALLBACK_RULE (`cashSign: 'free'`): the BUY's negative amount is kept as it is, and nothing
 * rebuilds the draft when the types arrive (`typesVersion` re-derives the rule, not the draft).
 *
 *   A. Types pending at open (the first describe of the file: the type store has no reset, and Vitest isolates each file,
 *      so the store is cold only here). Three forms open on the same saved BUY (10 units, -1234.56 EUR), each in its own
 *      container, while the types request is held by hand; then the request answers.
 *        A1  mode 'view'   → after the types: the amount shows 1234.56 (no minus), the quantity 10, no invalid mark.
 *        A2  mode 'edit' (outside the Bulk, committing itself) → the same.
 *        A3  guard, mode 'edit': the user typed an amount (50) before the types arrived → it is kept, never rebuilt
 *            over the user's typing.
 *   B. A quantity as an import gives it (many decimals, the server's zero padding), in view: shown as the number, not
 *      empty, with no digits error and no invalid mark.
 *   C. Regression guard for the coordinator's P-18 change (sign hints hidden in read-only): the cash sign hint of a
 *      DEPOSIT (the cash-only branch of `TxFormSingleSection`, where the hint has no testid) is found by the text the
 *      product itself renders for `signHintKey('positive')` — read through the same translation function, never written
 *      here — present in edit (the barrier), absent in view. And a BUY in view has no `tx-form-cash-hint`.
 *
 * Mount and mocks as `TransactionFormModal.groupSync.test.ts`. data-testid, ARIA and input values only.
 */
import {afterEach, beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';
import {get, writable} from 'svelte/store';
import {cleanup, fireEvent, render, screen, setupI18n, waitFor, within} from '$test/component';
import {zodiosApi} from '$lib/api';
import {schemas} from '$lib/api/generated';
import {_} from '$lib/i18n';
import {isTypesLoaded} from '$lib/features/transactions/transactionTypeStore';
import {signHintKey} from './txFormFields';
import {exceedsSignificantDigits, REAL_SIGNIFICANT_DIGITS} from '$lib/utils/core/parseDecimalInput';
import {guideAnchors} from '$lib/features/onboarding/guideAnchors.svelte';

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
vi.mock('$lib/stores/reference/brokerStore', async (importOriginal) => ({
    ...(await importOriginal<typeof import('$lib/stores/reference/brokerStore')>()),
    ensureBrokersLoaded: vi.fn().mockResolvedValue(undefined),
    refreshAllBrokers: vi.fn().mockResolvedValue(undefined),
}));
vi.mock('$lib/stores/reference/currencyStore', async (importOriginal) => ({
    ...(await importOriginal<typeof import('$lib/stores/reference/currencyStore')>()),
    ensureCurrenciesLoaded: vi.fn().mockResolvedValue(undefined),
}));
vi.mock('$lib/stores/reference/assetStore', async (importOriginal) => ({
    ...(await importOriginal<typeof import('$lib/stores/reference/assetStore')>()),
    ensureAssetsLoaded: vi.fn().mockResolvedValue(undefined),
    refreshAllAssets: vi.fn().mockResolvedValue(undefined),
}));
vi.mock('$lib/stores/app/toastStore.svelte', () => ({
    toasts: {success: vi.fn(), error: vi.fn(), warning: vi.fn(), info: vi.fn()},
}));
vi.mock('$lib/stores/app/language', () => ({currentLanguage: writable('en')}));
vi.mock('$lib/stores/reference/fxRoutesStore', () => ({
    fxRoutesVersion: writable(0),
    ensureFxRoutesLoaded: vi.fn(async () => undefined),
    getConfiguredCurrencySet: vi.fn(() => new Set(['EUR', 'USD'])),
}));
vi.mock('$lib/features/transactions/txCommitApi', () => ({
    commitTransactions: vi.fn(async () => ({committed: true, results: [], issues: []})),
    validateTransactions: vi.fn(async () => ({committed: true, issues: [], rawResponse: {wac_results: []}})),
}));
// The guide only starts in create mode; a neutral stub keeps the real controller out.
vi.mock('$lib/features/onboarding/onboardingGuide.svelte', async (importOriginal) => ({
    ...(await importOriginal<typeof import('$lib/features/onboarding/onboardingGuide.svelte')>()),
    onboardingGuide: {
        active: null,
        queuedFlow: null,
        queuedFlows: [],
        queuedGuides: [],
        maybeStartContextual: vi.fn(() => false),
        queueContextual: vi.fn(),
        clearQueued: vi.fn(),
        maybeStartQueued: vi.fn(() => false),
        dismissHost: vi.fn(),
    },
}));

import TransactionFormModal from './TransactionFormModal.svelte';

const baseType = {doc_slug: 'x', requires_link: false, event_compatible: false, cost_basis_mode: 'forbidden'} as const;

/** The rules of the backend's table (`type_metadata.py`) for the types used here. */
const TYPES = schemas.TXTypesResponse.parse({
    transaction_types: [
        {...baseType, code: 'BUY', name: 'Buy', description: 'Buy', icon_slug: 'buy', asset_mode: 'required', cash_mode: 'required', quantity_mode: 'required', quantity_sign: 'positive', cash_sign: 'negative', charge_role: 'parent'},
        {...baseType, code: 'DEPOSIT', name: 'Deposit', description: 'Deposit', icon_slug: 'deposit', asset_mode: 'forbidden', cash_mode: 'required', quantity_mode: 'forbidden', quantity_sign: 'zero', cash_sign: 'positive', charge_role: null},
        {...baseType, code: 'FEE', name: 'Fee', description: 'Fee', icon_slug: 'fee', asset_mode: 'optional', cash_mode: 'required', quantity_mode: 'forbidden', quantity_sign: 'zero', cash_sign: 'negative', charge_role: 'charge'},
    ],
    event_types: [],
});

/** A BUY like the one in the report: 10 units for 1234.56 EUR, as the server stores it (the amount signed). */
const QUANTITY = '10';
const MAGNITUDE = '1234.56';

const typesApi = () => vi.mocked(zodiosApi.get_transaction_types_api_v1_transactions_types_get);
const queryApi = () => vi.mocked(zodiosApi.query_transactions_api_v1_transactions_get);

function txRow(overrides: Record<string, unknown> = {}) {
    return {
        id: 10,
        broker_id: 17,
        asset_id: 42,
        type: 'BUY',
        date: '2024-03-10',
        quantity: QUANTITY,
        cash: {code: 'EUR', amount: `-${MAGNITUDE}`},
        related_transaction_id: null,
        partner_broker_id: null,
        parent_transaction_id: null,
        charges_count: 0,
        tags: [],
        description: '',
        cost_basis_override: null,
        cost_basis_mode: null,
        asset_event_id: null,
        created_at: '2024-03-10T00:00:00Z',
        updated_at: '2024-03-10T00:00:00Z',
        ...overrides,
    };
}

function mount(props: Record<string, unknown>) {
    return render(TransactionFormModal, {open: true, mode: 'view', items: null, onClose: vi.fn(), ...props});
}

/** A promise settled by hand. */
function deferred<T>() {
    let resolve!: (value: T) => void;
    const promise = new Promise<T>((res) => {
        resolve = res;
    });
    return {promise, resolve};
}

/** The quantity and amount inputs of one form, once on screen (the presence barrier). */
async function fieldsOf(container: HTMLElement): Promise<{quantity: HTMLInputElement; cash: HTMLInputElement}> {
    const scope = within(container);
    const quantity = (await scope.findByTestId('tx-form-quantity')) as HTMLInputElement;
    const cash = (await scope.findByTestId('tx-form-cash-amount')) as HTMLInputElement;
    return {quantity, cash};
}

/** Every invalid mark a form carries: on its inputs and on its cells. */
function invalidMarks(container: HTMLElement): string[] {
    const marks = [...container.querySelectorAll('[aria-invalid="true"]')].map((el) => `aria-invalid:${el.getAttribute('data-testid') ?? el.tagName}`);
    marks.push(...[...container.querySelectorAll('[data-cell-invalid]')].map((el) => `cell:${el.getAttribute('data-cell')}=${el.getAttribute('data-cell-invalid')}`));
    marks.push(...[...container.querySelectorAll('[data-testid$="-digits-error"], [data-testid$="-significant-error"]')].map((el) => `error:${el.getAttribute('data-testid')}`));
    return marks;
}

describe('TransactionFormModal — a saved BUY opened while the types are still loading (66 TL-1d)', () => {
    afterEach(() => {
        cleanup();
        guideAnchors.clear();
    });

    // One test for the three forms: the type store loads once per file and has no reset, and the harness unmounts
    // every form after each test. Each verdict is a soft assertion of its own, named A1, A2, A3.
    it('A1 view, A2 edit outside the Bulk: the magnitude 1234.56 and 10 once the types are in, no invalid mark; A3 guard: a typed amount is kept', async () => {
        await setupI18n();
        expect(isTypesLoaded(), 'premise: the type store is cold in this file').toBe(false);
        const types = deferred<typeof TYPES>();
        typesApi().mockImplementation(() => types.promise as never);
        queryApi().mockImplementation(async () => []);

        // Three forms on the same saved BUY, opened while GET /transactions/types is held.
        const forms = {
            view: mount({mode: 'view', items: [txRow()]}).container,
            edit: mount({mode: 'edit', items: [txRow()]}).container,
            typed: mount({mode: 'edit', items: [txRow()]}).container,
        };
        for (const container of Object.values(forms)) await fieldsOf(container);
        expect(typesApi(), 'premise: the forms asked for the types').toHaveBeenCalled();
        expect(isTypesLoaded(), 'premise: the types are still pending').toBe(false);

        // A3: the user types an amount before the types arrive.
        const typedCash = (await fieldsOf(forms.typed)).cash;
        await fireEvent.input(typedCash, {target: {value: '50'}});
        await waitFor(() => expect(typedCash.value).toBe('50'));

        // The types arrive.
        types.resolve(TYPES);
        await waitFor(() => expect(isTypesLoaded(), 'the types are loaded').toBe(true));

        const seen: Record<string, unknown> = {};
        for (const [label, container] of [
            ['A1 view', forms.view],
            ['A2 edit', forms.edit],
        ] as const) {
            const {quantity, cash} = await fieldsOf(container);
            // Give a rebuild its chance: the amount turning positive is what is waited for.
            await waitFor(() => expect(cash.value).toBe(MAGNITUDE), {timeout: 1_500}).catch(() => undefined);
            seen[label] = {quantity: quantity.value, cash: cash.value, marks: invalidMarks(container)};
            expect.soft(cash.value, `${label}: the amount shows the magnitude — ${JSON.stringify(seen[label])}`).toBe(MAGNITUDE);
            expect.soft(quantity.value, `${label}: the quantity shows 10 — ${JSON.stringify(seen[label])}`).toBe(QUANTITY);
            expect.soft(invalidMarks(container), `${label}: no invalid mark — ${JSON.stringify(seen[label])}`).toEqual([]);
        }
        const typed = await fieldsOf(forms.typed);
        expect.soft(typed.cash.value, `A3 guard: the amount typed before the types arrived is kept — ${JSON.stringify(seen)}`).toBe('50');
    });
});

describe('TransactionFormModal — a quantity as an import gives it, in view (66 TL-1d)', () => {
    beforeAll(async () => {
        await setupI18n();
        typesApi().mockResolvedValue(TYPES);
    });

    beforeEach(() => {
        queryApi().mockReset();
        queryApi().mockImplementation(async () => []);
        guideAnchors.clear();
    });

    afterEach(() => {
        cleanup();
        guideAnchors.clear();
    });

    it.each([
        ['12.345678901', '12.345678901'],
        ['12.345678901000000000', '12.345678901'],
        ['0.123456789012', '0.123456789012'],
    ])('quantity "%s" from the server is shown as %s, with no error and no invalid mark', async (stored, shown) => {
        const {container} = mount({mode: 'view', items: [txRow({quantity: stored})]});
        await waitFor(() => expect(isTypesLoaded()).toBe(true));
        const {quantity} = await fieldsOf(container);
        await waitFor(() => expect(quantity.value).not.toBe(''));
        expect(Number(quantity.value), `shown "${quantity.value}"`).toBe(Number(shown));
        expect(quantity.value).toBe(shown);
        expect(invalidMarks(container)).toEqual([]);
    });
});

describe('TransactionFormModal — a quantity past the significant digits, in view and in edit (66 TL-1d, P-18)', () => {
    beforeAll(async () => {
        await setupI18n();
        typesApi().mockResolvedValue(TYPES);
    });

    beforeEach(() => {
        queryApi().mockReset();
        queryApi().mockImplementation(async () => []);
        guideAnchors.clear();
    });

    afterEach(() => {
        cleanup();
        guideAnchors.clear();
    });

    // 16 significant digits, past REAL_SIGNIFICANT_DIGITS; 7 integer and 9 decimal digits, inside the field's own budget
    // (15 + 10), so the only error is the significant-digits one.
    const OVER_SIGNIFICANT = '1234567.123456789';

    it("premise: the quantity is past the significant-digits budget and inside the field's digit budget", () => {
        expect(exceedsSignificantDigits(OVER_SIGNIFICANT, REAL_SIGNIFICANT_DIGITS)).toBe(true);
    });

    it('view: the quantity is shown as stored, no significant-digits error under it, no invalid mark', async () => {
        const {container} = mount({mode: 'view', items: [txRow({quantity: OVER_SIGNIFICANT})]});
        await waitFor(() => expect(isTypesLoaded()).toBe(true));
        const {quantity} = await fieldsOf(container);
        await waitFor(() => expect(quantity.value).toBe(OVER_SIGNIFICANT));
        expect(within(container).queryByTestId('tx-form-quantity-significant-error')).toBeNull();
        expect(invalidMarks(container)).toEqual([]);
    });

    it('guard, edit: the same quantity shows the significant-digits error and marks the input', async () => {
        const {container} = mount({mode: 'edit', items: [txRow({quantity: OVER_SIGNIFICANT})]});
        await waitFor(() => expect(isTypesLoaded()).toBe(true));
        const {quantity} = await fieldsOf(container);
        await waitFor(() => expect(quantity.value).toBe(OVER_SIGNIFICANT));
        expect(await within(container).findByTestId('tx-form-quantity-significant-error')).toBeInTheDocument();
        expect(quantity).toHaveAttribute('aria-invalid', 'true');
    });
});

describe('TransactionFormModal — no sign hint under the amount in view (66 TL-1d, regression guard of P-18)', () => {
    beforeAll(async () => {
        await setupI18n();
        typesApi().mockResolvedValue(TYPES);
    });

    beforeEach(() => {
        queryApi().mockReset();
        queryApi().mockImplementation(async () => []);
        guideAnchors.clear();
    });

    afterEach(() => {
        cleanup();
        guideAnchors.clear();
    });

    const DEPOSIT = () => txRow({type: 'DEPOSIT', asset_id: null, quantity: '0', cash: {code: 'EUR', amount: '500'}});

    /** The hint the product renders for the DEPOSIT's cash sign, read through its own translation function. */
    function depositHint(): string {
        const key = signHintKey('positive');
        expect(key, 'premise: a positive cash sign has a hint').not.toBeNull();
        const text = get(_)(key!);
        expect(text, 'premise: the hint key is translated').not.toBe(key);
        return text;
    }

    it('barrier: a DEPOSIT in edit shows its cash sign hint under the amount', async () => {
        const {container} = mount({mode: 'edit', items: [DEPOSIT()]});
        await waitFor(() => expect(isTypesLoaded()).toBe(true));
        const wrap = await within(container).findByTestId('tx-form-cash-wrap');
        await within(container).findByTestId('tx-form-cash-amount');
        await waitFor(() => expect(wrap.textContent ?? '').toContain(depositHint()));
        expect(within(container).getByTestId('tx-form-cash-hint'), 'the cash-only branch publishes the hint by testid too').toBeInTheDocument();
    });

    it('a DEPOSIT in view: the amount shows 500, and the cash sign hint is not there', async () => {
        const {container} = mount({mode: 'view', items: [DEPOSIT()]});
        await waitFor(() => expect(isTypesLoaded()).toBe(true));
        const wrap = await within(container).findByTestId('tx-form-cash-wrap');
        const cash = (await within(container).findByTestId('tx-form-cash-amount')) as HTMLInputElement;
        await waitFor(() => expect(cash.value).toBe('500'));
        expect(wrap.textContent ?? '').not.toContain(depositHint());
        expect(within(container).queryByTestId('tx-form-cash-hint')).toBeNull();
    });

    it('a BUY in view: no tx-form-cash-hint and no quantity hint referenced by the quantity input', async () => {
        const {container} = mount({mode: 'view', items: [txRow()]});
        await waitFor(() => expect(isTypesLoaded()).toBe(true));
        const {quantity, cash} = await fieldsOf(container);
        await waitFor(() => expect(cash.value).toBe(MAGNITUDE));
        expect(within(container).queryByTestId('tx-form-cash-hint')).toBeNull();
        expect(quantity.getAttribute('aria-describedby'), 'no hint for the quantity in view').toBeNull();
    });
});
